#!/usr/bin/env python3
"""Export a deterministic, history-free snapshot of approved public content."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import shutil
import stat
import string
import subprocess
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING
from urllib.parse import unquote, urlsplit

if TYPE_CHECKING:
    from scripts import audit_publication as publication_audit
    from scripts import publication_assets
elif __package__:
    from . import audit_publication as publication_audit
    from . import publication_assets
else:
    import audit_publication as publication_audit
    import publication_assets


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = "publication/site-content.txt"
GENERATED_MANIFEST = "PUBLICATION-MANIFEST.json"
CHECKSUMS_FILE = "SHA256SUMS"
FORMAT_VERSION = "project-covenant-publication/v1"
SOURCE_DATE_EPOCH = 0
SOURCE_DATE_EPOCH_NS = SOURCE_DATE_EPOCH * 1_000_000_000
MAX_FILES = 1_000
MAX_FILE_BYTES = 5 * 1024 * 1024
MAX_TOTAL_BYTES = 50 * 1024 * 1024
MAX_ARTIFACT_ENTRIES = MAX_FILES * 4 + 2
MAX_MARKDOWN_LINK_NESTING = 64
MAX_PUBLIC_PATH_BYTES = 4_096
MAX_GIT_PATHS_PER_BATCH = 128
MAX_GIT_PATHSPEC_BATCH_BYTES = 64 * 1024
OID = re.compile(r"[0-9a-f]{40,64}")
WINDOWS_DRIVE = re.compile(r"^[A-Za-z]:")
WINDOWS_RESERVED_NAMES = {
    "aux",
    "con",
    "nul",
    "prn",
    *(f"com{number}" for number in range(1, 10)),
    *(f"lpt{number}" for number in range(1, 10)),
}
WINDOWS_FORBIDDEN_CHARACTERS = set('<>:"|?*')
GIT_HOST_TEXT = re.compile(
    r"(?i)(?:[A-Za-z0-9-]+\.)*"
    r"(?:github\.com|githubusercontent\.com|github\.io)"
    r"\.*(?=$|[^A-Za-z0-9.-])"
)
ALLOWED_STABLE_ANCHOR = re.compile(r'<a id="[A-Za-z0-9][A-Za-z0-9._:-]*"></a>')
ALLOWED_LINE_BREAK = re.compile(r"(?i)<br\s*/?>")
FENCE = re.compile(r"^( {0,3})(`{3,}|~{3,})")
MATH_FENCE_INFO_TOKEN = re.compile(r"(?i)(?:^|[^a-z0-9])math(?:$|[^a-z0-9])")
COMMONMARK_BACKSLASH_ESCAPE = re.compile(rf"\\([{re.escape(string.punctuation)}])")
COMMONMARK_FORMATTING_DELIMITER = re.compile(r"[*_~`$]")
LFS_POINTER_PREFIX = ("version https://git-lfs." + "github.com/spec/v1\n").encode(
    "ascii"
)


class PublicationExportError(RuntimeError):
    """A fail-closed publication export error with a non-sensitive code."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def _contains_control_character(value: str) -> bool:
    return any(unicodedata.category(character).startswith("C") for character in value)


def _portable_path_is_invalid(parts: tuple[str, ...]) -> bool:
    for part in parts:
        if part.endswith((" ", ".")):
            return True
        if any(character in WINDOWS_FORBIDDEN_CHARACTERS for character in part):
            return True
        if part.split(".", 1)[0].casefold() in WINDOWS_RESERVED_NAMES:
            return True
    return False


@dataclass(frozen=True)
class GitTreeEntry:
    mode: str
    object_type: str
    object_id: str


@dataclass(frozen=True)
class SnapshotFile:
    path: str
    data: bytes
    sha256: str

    @property
    def size(self) -> int:
        return len(self.data)


@dataclass(frozen=True)
class ExportReport:
    content_count: int
    total_bytes: int
    content_set_sha256: str


@dataclass(frozen=True)
class VerifiedSnapshot:
    """One verified report plus the exact immutable bytes that produced it."""

    report: ExportReport
    files: tuple[SnapshotFile, ...]


@dataclass(frozen=True)
class MarkdownLink:
    target: str
    is_image: bool


def git_output(repo_root: Path, args: list[str]) -> bytes:
    environment = {
        key: value for key, value in os.environ.items() if not key.startswith("GIT_")
    }
    environment.update(
        {
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_NO_LAZY_FETCH": "1",
            "GIT_TERMINAL_PROMPT": "0",
        }
    )
    try:
        process = subprocess.run(
            ["git", "--no-replace-objects", *args],
            cwd=repo_root,
            env=environment,
            stdin=subprocess.DEVNULL,
            check=False,
            capture_output=True,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise PublicationExportError("GIT_COMMAND_FAILED") from error
    if process.returncode != 0:
        raise PublicationExportError("GIT_COMMAND_FAILED")
    return process.stdout


def resolve_commit(repo_root: Path, source_ref: str) -> str:
    raw = git_output(
        repo_root,
        ["rev-parse", "--verify", "--end-of-options", f"{source_ref}^{{commit}}"],
    )
    try:
        commit = raw.decode("ascii").strip()
    except UnicodeDecodeError as error:
        raise PublicationExportError("GIT_COMMIT_ID_INVALID") from error
    if not OID.fullmatch(commit):
        raise PublicationExportError("GIT_COMMIT_ID_INVALID")
    return commit


def _git_path_batches(paths: list[str]) -> list[list[str]]:
    batches: list[list[str]] = []
    current: list[str] = []
    current_bytes = 0
    for path in paths:
        path_bytes = len(path.encode("utf-8")) + 1
        if current and (
            len(current) >= MAX_GIT_PATHS_PER_BATCH
            or current_bytes + path_bytes > MAX_GIT_PATHSPEC_BATCH_BYTES
        ):
            batches.append(current)
            current = []
            current_bytes = 0
        current.append(path)
        current_bytes += path_bytes
    if current:
        batches.append(current)
    return batches


def read_git_tree(
    repo_root: Path, commit: str, requested_paths: list[str]
) -> dict[str, GitTreeEntry]:
    entries: dict[str, GitTreeEntry] = {}
    requested = set(requested_paths)
    for batch in _git_path_batches(requested_paths):
        raw_tree = git_output(
            repo_root,
            [
                "--literal-pathspecs",
                "ls-tree",
                "-z",
                "--full-tree",
                commit,
                "--",
                *batch,
            ],
        )
        for record in raw_tree.split(b"\0"):
            if not record:
                continue
            if b"\t" not in record:
                raise PublicationExportError("GIT_TREE_RECORD_INVALID")
            raw_metadata, raw_path = record.split(b"\t", 1)
            fields = raw_metadata.split()
            if len(fields) != 3:
                raise PublicationExportError("GIT_TREE_RECORD_INVALID")
            try:
                mode, object_type, object_id = (
                    field.decode("ascii") for field in fields
                )
                path = raw_path.decode("utf-8")
            except UnicodeDecodeError as error:
                raise PublicationExportError("GIT_TREE_ENCODING_INVALID") from error
            if path not in requested:
                raise PublicationExportError("GIT_TREE_UNREQUESTED_PATH")
            if path in entries:
                raise PublicationExportError("GIT_TREE_DUPLICATE_PATH")
            entries[path] = GitTreeEntry(mode, object_type, object_id)
    return entries


def normalize_public_path(raw_entry: str) -> str:
    if raw_entry != raw_entry.strip() or not raw_entry:
        raise PublicationExportError("MANIFEST_PATH_NOT_CANONICAL")
    if _contains_control_character(raw_entry):
        raise PublicationExportError("MANIFEST_PATH_CONTROL_CHARACTER")
    if len(raw_entry.encode("utf-8")) > MAX_PUBLIC_PATH_BYTES:
        raise PublicationExportError("MANIFEST_PATH_TOO_LONG")
    if "\\" in raw_entry or WINDOWS_DRIVE.match(raw_entry):
        raise PublicationExportError("MANIFEST_PATH_PLATFORM_ESCAPE")
    if unicodedata.normalize("NFC", raw_entry) != raw_entry:
        raise PublicationExportError("MANIFEST_PATH_NOT_NFC")

    pure = PurePosixPath(raw_entry)
    if pure.is_absolute() or ".." in pure.parts or raw_entry != pure.as_posix():
        raise PublicationExportError("MANIFEST_PATH_NOT_CANONICAL")
    if _portable_path_is_invalid(pure.parts):
        raise PublicationExportError("MANIFEST_PATH_PLATFORM_ESCAPE")
    folded_parts = tuple(part.casefold() for part in pure.parts)
    if ".git" in folded_parts or any(part.startswith(".env") for part in folded_parts):
        raise PublicationExportError("MANIFEST_PATH_PRIVATE")
    if any(part in {"private", "credentials", "secrets"} for part in folded_parts):
        raise PublicationExportError("MANIFEST_PATH_PRIVATE")
    folded_entry = raw_entry.casefold()
    if any(
        folded_entry == prefix.casefold().rstrip("/")
        or folded_entry.startswith(prefix.casefold())
        for prefix in publication_audit.FORBIDDEN_SITE_PREFIXES
    ):
        raise PublicationExportError("MANIFEST_PATH_FORBIDDEN")
    if pure.suffix.casefold() != ".md" and raw_entry != MANIFEST_PATH and not publication_assets.is_asset_path(raw_entry):
        raise PublicationExportError("MANIFEST_NON_MARKDOWN_INPUT")
    return raw_entry


def parse_manifest(data: bytes) -> list[str]:
    if b"\0" in data:
        raise PublicationExportError("MANIFEST_BINARY")
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as error:
        raise PublicationExportError("MANIFEST_NOT_UTF8") from error

    entries: list[str] = []
    folded: set[str] = set()
    for raw_line in text.splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        entry = normalize_public_path(raw_line)
        collision_key = unicodedata.normalize("NFC", entry).casefold()
        if collision_key in folded:
            raise PublicationExportError("MANIFEST_DUPLICATE_OR_CASE_COLLISION")
        folded.add(collision_key)
        entries.append(entry)

    if not entries or len(entries) > MAX_FILES:
        raise PublicationExportError("MANIFEST_FILE_COUNT_INVALID")
    if entries != sorted(entries):
        raise PublicationExportError("MANIFEST_NOT_SORTED")
    if MANIFEST_PATH not in entries:
        raise PublicationExportError("MANIFEST_SELF_ENTRY_MISSING")
    return entries


def read_blob(repo_root: Path, entry: GitTreeEntry, path: str) -> bytes:
    if entry.mode != "100644" or entry.object_type != "blob":
        raise PublicationExportError("SNAPSHOT_SPECIAL_FILE_FORBIDDEN")
    raw_size = git_output(repo_root, ["cat-file", "-s", entry.object_id])
    try:
        declared_size = int(raw_size.decode("ascii").strip())
    except (UnicodeDecodeError, ValueError) as error:
        raise PublicationExportError("SNAPSHOT_BLOB_SIZE_INVALID") from error
    if declared_size < 0 or declared_size > MAX_FILE_BYTES:
        raise PublicationExportError("SNAPSHOT_FILE_TOO_LARGE")
    data = git_output(repo_root, ["cat-file", "blob", entry.object_id])
    if len(data) != declared_size:
        raise PublicationExportError("SNAPSHOT_BLOB_SIZE_INVALID")
    if data.startswith(LFS_POINTER_PREFIX):
        raise PublicationExportError("SNAPSHOT_LFS_POINTER_FORBIDDEN")
    if publication_assets.is_asset_path(path):
        try:
            publication_assets.validate_asset(path, data)
        except publication_assets.AssetError as error:
            raise PublicationExportError(str(error)) from error
        return data
    if b"\0" in data:
        raise PublicationExportError("SNAPSHOT_BINARY_FORBIDDEN")
    try:
        data.decode("utf-8")
    except UnicodeDecodeError as error:
        raise PublicationExportError("SNAPSHOT_NOT_UTF8") from error
    return data


def _target_value(raw_target: str) -> str:
    target = _decode_commonmark_escapes(raw_target).strip()
    if not target:
        raise PublicationExportError("SNAPSHOT_EMPTY_LINK_TARGET_FORBIDDEN")
    if target.startswith("<") and ">" in target:
        return target[1 : target.index(">")]
    return target.split(maxsplit=1)[0]


def _decode_html_entities(value: str) -> str:
    decoded = value
    for _ in range(4):
        next_value = html.unescape(decoded)
        if next_value == decoded:
            break
        decoded = next_value
    return decoded


def _decode_commonmark_escapes(value: str) -> str:
    """Decode the character references and punctuation escapes CommonMark renders."""

    return COMMONMARK_BACKSLASH_ESCAPE.sub(r"\1", _decode_html_entities(value))


def _remove_invisible_format_characters(value: str) -> str:
    return "".join(
        character for character in value if unicodedata.category(character) != "Cf"
    )


def _contains_unicode_format_character(value: str) -> bool:
    return any(unicodedata.category(character) == "Cf" for character in value)


def _formatting_projection_variants(value: str) -> tuple[str, str]:
    projected = COMMONMARK_BACKSLASH_ESCAPE.sub(r"\1", value)
    projected = _remove_invisible_format_characters(projected)
    projected = COMMONMARK_FORMATTING_DELIMITER.sub("", projected)
    with_spaces = ALLOWED_STABLE_ANCHOR.sub(" ", projected)
    with_spaces = ALLOWED_LINE_BREAK.sub(" ", with_spaces)
    without_markup = ALLOWED_STABLE_ANCHOR.sub("", projected)
    without_markup = ALLOWED_LINE_BREAK.sub("", without_markup)
    return with_spaces, without_markup


def _rendered_text_projection(text: str) -> str:
    """Build a conservative projection for privacy scans of rendered Markdown."""

    entity_decoded = _decode_html_entities(text)
    label_only = _inline_link_label_projection(entity_decoded)
    source_variants = _formatting_projection_variants(entity_decoded)
    label_variants = _formatting_projection_variants(label_only)
    return "\n".join((*source_variants, *label_variants))


def _fully_unquote(value: str) -> str:
    decoded = value
    for _ in range(3):
        next_value = unquote(decoded)
        if next_value == decoded:
            return decoded
        decoded = next_value
    return decoded


def _is_escaped(text: str, index: int) -> bool:
    backslashes = 0
    cursor = index - 1
    while cursor >= 0 and text[cursor] == "\\":
        backslashes += 1
        cursor -= 1
    return backslashes % 2 == 1


def _contains_unescaped_dollar(value: str) -> bool:
    return any(
        character == "$" and not _is_escaped(value, index)
        for index, character in enumerate(value)
    )


def _contains_math_fence(value: str) -> bool:
    for line in value.splitlines():
        match = FENCE.match(line)
        if match is None:
            continue
        info_string = line[match.end(2) :].strip()
        if MATH_FENCE_INFO_TOKEN.search(info_string):
            return True
    return False


def _mask_inline_code(line: str) -> str:
    masked = list(line)
    cursor = 0
    while cursor < len(line):
        if line[cursor] != "`" or _is_escaped(line, cursor):
            cursor += 1
            continue
        opening_end = cursor
        while opening_end < len(line) and line[opening_end] == "`":
            opening_end += 1
        opening_length = opening_end - cursor
        search = opening_end
        closing_start: int | None = None
        closing_end = search
        while search < len(line):
            if line[search] != "`" or _is_escaped(line, search):
                search += 1
                continue
            run_end = search
            while run_end < len(line) and line[run_end] == "`":
                run_end += 1
            if run_end - search == opening_length:
                closing_start = search
                closing_end = run_end
                break
            search = run_end
        if closing_start is None:
            cursor = opening_end
            continue
        for index in range(cursor, closing_end):
            if masked[index] not in "\r\n":
                masked[index] = " "
        cursor = closing_end
    return "".join(masked)


def _mask_code_regions(text: str) -> str:
    output: list[str] = []
    fence_character: str | None = None
    fence_length = 0
    for line in text.splitlines(keepends=True):
        match = FENCE.match(line)
        if fence_character is None and match is not None:
            marker = match.group(2)
            fence_character = marker[0]
            fence_length = len(marker)
            output.append(
                "".join(
                    "\n" if char == "\n" else "\r" if char == "\r" else " "
                    for char in line
                )
            )
            continue
        if fence_character is not None:
            stripped = line.lstrip(" ")
            run_length = len(stripped) - len(stripped.lstrip(fence_character))
            is_close = (
                len(line) - len(stripped) <= 3
                and run_length >= fence_length
                and not stripped[run_length:].strip()
            )
            output.append(
                "".join(
                    "\n" if char == "\n" else "\r" if char == "\r" else " "
                    for char in line
                )
            )
            if is_close:
                fence_character = None
                fence_length = 0
            continue
        output.append(_mask_inline_code(line))
    return "".join(output)


def _validate_raw_html(text: str) -> None:
    visible = _mask_code_regions(text)
    without_allowed_anchors = ALLOWED_STABLE_ANCHOR.sub("", visible)
    without_allowed_markup = ALLOWED_LINE_BREAK.sub("", without_allowed_anchors)
    if "<" in without_allowed_markup:
        raise PublicationExportError("SNAPSHOT_RAW_HTML_FORBIDDEN")


def _matching_bracket(text: str, opening: int) -> tuple[int, bool] | None:
    depth = 1
    nested = False
    cursor = opening + 1
    while cursor < len(text):
        if _is_escaped(text, cursor):
            cursor += 1
            continue
        if text[cursor] == "[":
            depth += 1
            nested = True
        elif text[cursor] == "]":
            depth -= 1
            if depth == 0:
                return cursor, nested
        cursor += 1
    return None


def _matching_parenthesis(text: str, opening: int) -> int:
    depth = 1
    cursor = opening + 1
    while cursor < len(text):
        character = text[cursor]
        if character in "\r\n":
            raise PublicationExportError("SNAPSHOT_MULTILINE_LINK_FORBIDDEN")
        if _is_escaped(text, cursor):
            cursor += 1
            continue
        if character == "(":
            depth += 1
        elif character == ")":
            depth -= 1
            if depth == 0:
                return cursor
        cursor += 1
    raise PublicationExportError("SNAPSHOT_MALFORMED_LINK_FORBIDDEN")


def _inline_link_label_projection(text: str, *, _depth: int = 0) -> str:
    """Project inline links to their rendered labels while dropping destinations."""

    if _depth > MAX_MARKDOWN_LINK_NESTING:
        raise PublicationExportError("SNAPSHOT_LINK_NESTING_FORBIDDEN")
    output: list[str] = []
    cursor = 0
    literal_start = 0
    while cursor < len(text):
        is_image = (
            text[cursor] == "!"
            and not _is_escaped(text, cursor)
            and cursor + 1 < len(text)
            and text[cursor + 1] == "["
        )
        if is_image:
            bracket = cursor + 1
        elif text[cursor] == "[" and not _is_escaped(text, cursor):
            bracket = cursor
        else:
            cursor += 1
            continue
        matched = _matching_bracket(text, bracket)
        if matched is None:
            if is_image:
                raise PublicationExportError("SNAPSHOT_MALFORMED_IMAGE_FORBIDDEN")
            raise PublicationExportError("SNAPSHOT_MALFORMED_LINK_FORBIDDEN")
        closing, nested = matched
        following = closing + 1
        if following < len(text) and text[following] == "(":
            if "\n" in text[bracket:closing] or "\r" in text[bracket:closing]:
                raise PublicationExportError("SNAPSHOT_MULTILINE_LINK_FORBIDDEN")
            destination_end = _matching_parenthesis(text, following)
            label = text[bracket + 1 : closing]
            if nested:
                if _depth >= MAX_MARKDOWN_LINK_NESTING:
                    raise PublicationExportError("SNAPSHOT_LINK_NESTING_FORBIDDEN")
                label = _inline_link_label_projection(label, _depth=_depth + 1)
            output.append(text[literal_start:cursor])
            output.append(label)
            cursor = destination_end + 1
            literal_start = cursor
            continue
        if following < len(text) and text[following] == "[":
            raise PublicationExportError("SNAPSHOT_REFERENCE_LINK_FORBIDDEN")
        line_start = text.rfind("\n", 0, bracket) + 1
        if (
            following < len(text)
            and text[following] == ":"
            and not text[line_start:bracket].strip()
        ):
            raise PublicationExportError("SNAPSHOT_REFERENCE_DEFINITION_FORBIDDEN")
        if is_image:
            raise PublicationExportError("SNAPSHOT_REFERENCE_IMAGE_FORBIDDEN")
        cursor = closing + 1
    output.append(text[literal_start:])
    return "".join(output)


def markdown_links(text: str, *, _depth: int = 0) -> list[MarkdownLink]:
    if _depth > MAX_MARKDOWN_LINK_NESTING:
        raise PublicationExportError("SNAPSHOT_LINK_NESTING_FORBIDDEN")
    visible = _mask_code_regions(text)
    links: list[MarkdownLink] = []
    cursor = 0
    while cursor < len(visible):
        is_image = (
            visible[cursor] == "!"
            and not _is_escaped(visible, cursor)
            and cursor + 1 < len(visible)
            and visible[cursor + 1] == "["
        )
        if is_image:
            bracket = cursor + 1
        elif visible[cursor] == "[" and not _is_escaped(visible, cursor):
            bracket = cursor
        else:
            cursor += 1
            continue
        if _is_escaped(visible, bracket):
            cursor = bracket + 1
            continue
        matched = _matching_bracket(visible, bracket)
        if matched is None:
            if is_image:
                raise PublicationExportError("SNAPSHOT_MALFORMED_IMAGE_FORBIDDEN")
            raise PublicationExportError("SNAPSHOT_MALFORMED_LINK_FORBIDDEN")
        closing, _nested = matched
        following = closing + 1
        if following < len(visible) and visible[following] == "(":
            if "\n" in visible[bracket:closing] or "\r" in visible[bracket:closing]:
                raise PublicationExportError("SNAPSHOT_MULTILINE_LINK_FORBIDDEN")
            if _nested:
                if _depth >= MAX_MARKDOWN_LINK_NESTING:
                    raise PublicationExportError("SNAPSHOT_LINK_NESTING_FORBIDDEN")
                links.extend(
                    markdown_links(visible[bracket + 1 : closing], _depth=_depth + 1)
                )
            destination_end = _matching_parenthesis(visible, following)
            links.append(
                MarkdownLink(visible[following + 1 : destination_end], is_image)
            )
            cursor = destination_end + 1
            continue
        if following < len(visible) and visible[following] == "[":
            raise PublicationExportError("SNAPSHOT_REFERENCE_LINK_FORBIDDEN")
        line_start = visible.rfind("\n", 0, bracket) + 1
        if (
            following < len(visible)
            and visible[following] == ":"
            and not visible[line_start:bracket].strip()
        ):
            raise PublicationExportError("SNAPSHOT_REFERENCE_DEFINITION_FORBIDDEN")
        if is_image:
            raise PublicationExportError("SNAPSHOT_REFERENCE_IMAGE_FORBIDDEN")
        cursor = closing + 1
    return links


def _host_is_forbidden(hostname: str) -> bool:
    return (
        hostname == "github.com"
        or hostname.endswith(".github.com")
        or hostname == "githubusercontent.com"
        or hostname.endswith(".githubusercontent.com")
        or hostname == "github.io"
        or hostname.endswith(".github.io")
    )


def resolved_local_target(current_path: str, raw_target: str) -> str | None:
    target = _target_value(raw_target)
    if "\\" in target or _contains_control_character(target):
        raise PublicationExportError("SNAPSHOT_LINK_URL_INVALID")
    try:
        parsed = urlsplit(target)
    except ValueError as error:
        raise PublicationExportError("SNAPSHOT_LINK_URL_INVALID") from error
    if parsed.scheme:
        if parsed.scheme.casefold() != "https":
            raise PublicationExportError("SNAPSHOT_LINK_SCHEME_FORBIDDEN")
        if not target.casefold().startswith("https://") or not parsed.netloc:
            raise PublicationExportError("SNAPSHOT_LINK_URL_INVALID")
        try:
            hostname = parsed.hostname
            _port = parsed.port
        except ValueError as error:
            raise PublicationExportError("SNAPSHOT_LINK_URL_INVALID") from error
        if not hostname or parsed.username is not None or parsed.password is not None:
            raise PublicationExportError("SNAPSHOT_LINK_URL_INVALID")
        raw_hostname = hostname.casefold().rstrip(".")
        decoded_hostname = _fully_unquote(raw_hostname)
        if _host_is_forbidden(decoded_hostname):
            raise PublicationExportError("SNAPSHOT_GIT_HOST_LINK_FORBIDDEN")
        if decoded_hostname != raw_hostname or "%" in raw_hostname:
            raise PublicationExportError("SNAPSHOT_LINK_URL_INVALID")
        try:
            canonical_hostname = decoded_hostname.encode("idna").decode("ascii")
        except UnicodeError as error:
            raise PublicationExportError("SNAPSHOT_LINK_URL_INVALID") from error
        if _host_is_forbidden(canonical_hostname):
            raise PublicationExportError("SNAPSHOT_GIT_HOST_LINK_FORBIDDEN")
        return None
    if parsed.netloc:
        raise PublicationExportError("SNAPSHOT_PROTOCOL_RELATIVE_LINK_FORBIDDEN")
    if not parsed.path:
        return None

    decoded = _fully_unquote(parsed.path)
    if "\\" in decoded or decoded.startswith("/"):
        raise PublicationExportError("SNAPSHOT_LINK_PATH_FORBIDDEN")
    if any(ord(character) < 32 or ord(character) == 127 for character in decoded):
        raise PublicationExportError("SNAPSHOT_LINK_PATH_FORBIDDEN")

    parts = list(PurePosixPath(current_path).parent.parts)
    for part in decoded.split("/"):
        if not part or part == ".":
            continue
        if part == "..":
            if not parts:
                raise PublicationExportError("SNAPSHOT_LINK_ESCAPES_ROOT")
            parts.pop()
            continue
        parts.append(part)
    if not parts:
        raise PublicationExportError("SNAPSHOT_LINK_PATH_FORBIDDEN")
    resolved = PurePosixPath(*parts).as_posix()
    return normalize_public_path(resolved)


def validate_snapshot(files: list[SnapshotFile]) -> None:
    allowed = {file.path for file in files}
    if any(publication_assets.is_asset_path(path) for path in allowed) and "CREDITS.md" not in allowed:
        raise PublicationExportError("SNAPSHOT_ASSET_CREDITS_REQUIRED")
    for file in files:
        label = f"snapshot-file-sha256:{publication_audit.short_hash(file.path)}"
        path_findings = publication_audit.scan_text(label, file.path)
        if path_findings:
            raise PublicationExportError(f"SNAPSHOT_{path_findings[0].rule_id}")
        if publication_assets.is_asset_path(file.path):
            try:
                publication_assets.validate_asset(file.path, file.data)
            except publication_assets.AssetError as error:
                raise PublicationExportError(str(error)) from error
            if file.path.endswith(".svg"):
                findings = publication_audit.scan_text(label, file.data.decode("utf-8"))
                if findings:
                    raise PublicationExportError(f"SNAPSHOT_{findings[0].rule_id}")
            continue
        if b"\0" in file.data:
            raise PublicationExportError("SNAPSHOT_BINARY_FORBIDDEN")
        if file.data.startswith(LFS_POINTER_PREFIX):
            raise PublicationExportError("SNAPSHOT_LFS_POINTER_FORBIDDEN")
        try:
            text = file.data.decode("utf-8")
        except UnicodeDecodeError as error:
            raise PublicationExportError("SNAPSHOT_NOT_UTF8") from error
        privacy_candidates: list[str] = []
        semantic_text = text
        for _ in range(4):
            if _contains_unescaped_dollar(semantic_text):
                raise PublicationExportError("SNAPSHOT_UNESCAPED_DOLLAR_FORBIDDEN")
            if _contains_math_fence(semantic_text):
                raise PublicationExportError("SNAPSHOT_MATH_FENCE_FORBIDDEN")
            if _contains_unicode_format_character(semantic_text):
                raise PublicationExportError(
                    "SNAPSHOT_UNICODE_FORMAT_CHARACTER_FORBIDDEN"
                )
            privacy_candidates.append(semantic_text)
            privacy_candidates.append(_rendered_text_projection(semantic_text))
            next_semantic_text = _fully_unquote(_decode_html_entities(semantic_text))
            if next_semantic_text == semantic_text:
                break
            semantic_text = next_semantic_text
        for candidate in privacy_candidates:
            content_findings = publication_audit.scan_text(label, candidate)
            if content_findings:
                raise PublicationExportError(f"SNAPSHOT_{content_findings[0].rule_id}")
        _validate_raw_html(text)
        if any(GIT_HOST_TEXT.search(candidate) for candidate in privacy_candidates):
            raise PublicationExportError("SNAPSHOT_GIT_HOST_LINK_FORBIDDEN")
        for link in markdown_links(text):
            if link.is_image and not link.target.strip():
                raise PublicationExportError("SNAPSHOT_MARKDOWN_IMAGE_FORBIDDEN")
            target = resolved_local_target(file.path, link.target)
            if link.is_image:
                parsed = urlsplit(link.target)
                if target is None or not publication_assets.is_asset_path(target) or parsed.query or parsed.fragment:
                    raise PublicationExportError("SNAPSHOT_MARKDOWN_IMAGE_FORBIDDEN")
            if target is not None and target not in allowed:
                raise PublicationExportError("SNAPSHOT_LINK_OUTSIDE_ALLOWLIST")


def assert_release_checkout(repo_root: Path, commit: str) -> None:
    if resolve_commit(repo_root, "HEAD") != commit:
        raise PublicationExportError("SOURCE_REF_NOT_CHECKED_OUT")
    status = git_output(
        repo_root,
        ["status", "--porcelain=v1", "-z", "--untracked-files=all"],
    )
    if status:
        raise PublicationExportError("SOURCE_CHECKOUT_NOT_CLEAN")


def snapshot_from_commit(
    repo_root: Path,
    source_ref: str = "HEAD",
) -> list[SnapshotFile]:
    commit = resolve_commit(repo_root, source_ref)
    assert_release_checkout(repo_root, commit)
    manifest_tree = read_git_tree(repo_root, commit, [MANIFEST_PATH])
    manifest_entry = manifest_tree.get(MANIFEST_PATH)
    if manifest_entry is None:
        raise PublicationExportError("MANIFEST_MISSING_FROM_COMMIT")
    manifest_data = read_blob(repo_root, manifest_entry, MANIFEST_PATH)
    entries = parse_manifest(manifest_data)
    tree = read_git_tree(repo_root, commit, entries)

    files: list[SnapshotFile] = []
    total_bytes = 0
    for path in entries:
        tree_entry = tree.get(path)
        if tree_entry is None:
            raise PublicationExportError("SNAPSHOT_FILE_MISSING")
        data = read_blob(repo_root, tree_entry, path)
        total_bytes += len(data)
        if total_bytes > MAX_TOTAL_BYTES:
            raise PublicationExportError("SNAPSHOT_TOTAL_TOO_LARGE")
        files.append(SnapshotFile(path, data, hashlib.sha256(data).hexdigest()))
    validate_snapshot(files)
    return files


def content_set_sha256(files: list[SnapshotFile]) -> str:
    digest = hashlib.sha256()
    for file in sorted(files, key=lambda item: item.path):
        digest.update(file.path.encode("utf-8"))
        digest.update(b"\0")
        digest.update(file.sha256.encode("ascii"))
        digest.update(b"\0")
        digest.update(str(file.size).encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


def generated_metadata(files: list[SnapshotFile]) -> tuple[bytes, bytes, str]:
    set_digest = content_set_sha256(files)
    payload = {
        "content_count": len(files),
        "content_set_sha256": set_digest,
        "files": [
            {"bytes": file.size, "path": file.path, "sha256": file.sha256}
            for file in sorted(files, key=lambda item: item.path)
        ],
        "format": FORMAT_VERSION,
    }
    manifest_bytes = (
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")

    checksums: dict[str, str] = {file.path: file.sha256 for file in files}
    checksums[GENERATED_MANIFEST] = hashlib.sha256(manifest_bytes).hexdigest()
    checksum_bytes = "".join(
        f"{digest}  {path}\n" for path, digest in sorted(checksums.items())
    ).encode("utf-8")
    return manifest_bytes, checksum_bytes, set_digest


def _artifact_relative_path(root: Path, path: Path) -> str:
    try:
        relative = path.relative_to(root).as_posix()
    except ValueError as error:
        raise PublicationExportError("ARTIFACT_PATH_ESCAPES_ROOT") from error
    if not relative or relative == ".":
        raise PublicationExportError("ARTIFACT_PATH_INVALID")
    if _contains_control_character(relative):
        raise PublicationExportError("ARTIFACT_PATH_INVALID")
    if "\\" in relative or unicodedata.normalize("NFC", relative) != relative:
        raise PublicationExportError("ARTIFACT_PATH_INVALID")
    pure = PurePosixPath(relative)
    if pure.is_absolute() or ".." in pure.parts or relative != pure.as_posix():
        raise PublicationExportError("ARTIFACT_PATH_INVALID")
    if _portable_path_is_invalid(pure.parts):
        raise PublicationExportError("ARTIFACT_PATH_INVALID")
    if any(part.casefold() == ".git" for part in pure.parts):
        raise PublicationExportError("ARTIFACT_GIT_METADATA_FORBIDDEN")
    return relative


def enumerate_artifact(input_dir: Path) -> tuple[set[str], set[str]]:
    try:
        root_details = input_dir.lstat()
    except OSError as error:
        raise PublicationExportError("ARTIFACT_ROOT_INVALID") from error
    if stat.S_ISLNK(root_details.st_mode) or not stat.S_ISDIR(root_details.st_mode):
        raise PublicationExportError("ARTIFACT_ROOT_INVALID")
    if stat.S_IMODE(root_details.st_mode) != 0o755:
        raise PublicationExportError("ARTIFACT_DIRECTORY_MODE_INVALID")
    file_paths: set[str] = set()
    directory_paths: set[str] = set()
    collision_keys: set[str] = set()
    pending = [input_dir]
    entry_count = 0
    while pending:
        directory = pending.pop()
        try:
            with os.scandir(directory) as scanner:
                for raw_entry in scanner:
                    entry_count += 1
                    if entry_count > MAX_ARTIFACT_ENTRIES:
                        raise PublicationExportError("ARTIFACT_ENTRY_COUNT_INVALID")
                    child = Path(raw_entry.path)
                    relative = _artifact_relative_path(input_dir, child)
                    key = unicodedata.normalize("NFC", relative).casefold()
                    if key in collision_keys:
                        raise PublicationExportError("ARTIFACT_PATH_COLLISION")
                    collision_keys.add(key)
                    details = raw_entry.stat(follow_symlinks=False)
                    if stat.S_ISLNK(details.st_mode):
                        raise PublicationExportError("ARTIFACT_SYMLINK_FORBIDDEN")
                    if stat.S_ISDIR(details.st_mode):
                        if stat.S_IMODE(details.st_mode) != 0o755:
                            raise PublicationExportError(
                                "ARTIFACT_DIRECTORY_MODE_INVALID"
                            )
                        directory_paths.add(relative)
                        pending.append(child)
                        continue
                    if not stat.S_ISREG(details.st_mode) or details.st_nlink != 1:
                        raise PublicationExportError("ARTIFACT_SPECIAL_FILE_FORBIDDEN")
                    if stat.S_IMODE(details.st_mode) != 0o644:
                        raise PublicationExportError("ARTIFACT_FILE_MODE_INVALID")
                    file_paths.add(relative)
        except PublicationExportError:
            raise
        except OSError as error:
            raise PublicationExportError("ARTIFACT_DIRECTORY_READ_FAILED") from error
    return file_paths, directory_paths


DirectoryIdentity = tuple[int, int, int, int, int, int]


def _artifact_directory_identity(directory: Path, error_code: str) -> DirectoryIdentity:
    try:
        details = directory.lstat()
    except OSError as error:
        raise PublicationExportError(error_code) from error
    if stat.S_ISLNK(details.st_mode) or not stat.S_ISDIR(details.st_mode):
        raise PublicationExportError(error_code)
    return (
        details.st_dev,
        details.st_ino,
        details.st_nlink,
        details.st_mode,
        details.st_mtime_ns,
        details.st_ctime_ns,
    )


def _artifact_directory_identities(
    input_dir: Path, directory_paths: set[str], error_code: str
) -> dict[str, DirectoryIdentity]:
    identities = {"": _artifact_directory_identity(input_dir, error_code)}
    for path in sorted(directory_paths):
        identities[path] = _artifact_directory_identity(input_dir / path, error_code)
    return identities


def _assert_artifact_root_unchanged(
    input_dir: Path, expected_identity: DirectoryIdentity
) -> None:
    if (
        _artifact_directory_identity(
            input_dir, "ARTIFACT_ROOT_CHANGED_DURING_VERIFICATION"
        )
        != expected_identity
    ):
        raise PublicationExportError("ARTIFACT_ROOT_CHANGED_DURING_VERIFICATION")


def _validate_artifact_mtime(path: Path, error_code: str) -> None:
    try:
        details = path.lstat()
    except OSError as error:
        raise PublicationExportError("ARTIFACT_MTIME_READ_FAILED") from error
    if details.st_mtime_ns != SOURCE_DATE_EPOCH_NS:
        raise PublicationExportError(error_code)


def _read_artifact_file(input_dir: Path, path: str) -> bytes:
    target = input_dir / path
    descriptor: int | None = None
    try:
        flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(target, flags)
        details = os.fstat(descriptor)
        if not stat.S_ISREG(details.st_mode) or details.st_nlink != 1:
            raise PublicationExportError("ARTIFACT_SPECIAL_FILE_FORBIDDEN")
        if stat.S_IMODE(details.st_mode) != 0o644:
            raise PublicationExportError("ARTIFACT_FILE_MODE_INVALID")
        if details.st_mtime_ns != SOURCE_DATE_EPOCH_NS:
            raise PublicationExportError("ARTIFACT_FILE_MTIME_INVALID")
        if details.st_size > MAX_FILE_BYTES:
            raise PublicationExportError("ARTIFACT_FILE_TOO_LARGE")
        with os.fdopen(descriptor, "rb", closefd=False) as handle:
            data = handle.read(MAX_FILE_BYTES + 1)
        if len(data) > MAX_FILE_BYTES:
            raise PublicationExportError("ARTIFACT_FILE_TOO_LARGE")
        if len(data) != details.st_size:
            raise PublicationExportError("ARTIFACT_FILE_CHANGED_DURING_READ")
    except OSError as error:
        raise PublicationExportError("ARTIFACT_FILE_READ_FAILED") from error
    finally:
        if descriptor is not None:
            os.close(descriptor)
    return data


def _load_verified_snapshot(
    input_dir: Path, expected_content_set_sha256: str
) -> VerifiedSnapshot:
    if not re.fullmatch(r"[0-9a-f]{64}", expected_content_set_sha256):
        raise PublicationExportError("EXPECTED_CONTENT_SET_DIGEST_INVALID")
    root_identity = _artifact_directory_identity(input_dir, "ARTIFACT_ROOT_INVALID")
    file_paths, directory_paths = enumerate_artifact(input_dir)
    _assert_artifact_root_unchanged(input_dir, root_identity)
    if not {MANIFEST_PATH, GENERATED_MANIFEST, CHECKSUMS_FILE}.issubset(file_paths):
        raise PublicationExportError("ARTIFACT_GENERATED_FILES_MISSING")
    source_manifest_bytes = _read_artifact_file(input_dir, MANIFEST_PATH)
    content_paths = parse_manifest(source_manifest_bytes)
    expected_files = set(content_paths) | {GENERATED_MANIFEST, CHECKSUMS_FILE}
    if file_paths != expected_files:
        raise PublicationExportError("ARTIFACT_FILE_SET_MISMATCH")

    expected_directories: set[str] = set()
    for path in expected_files:
        parent = PurePosixPath(path).parent
        while parent.as_posix() != ".":
            expected_directories.add(parent.as_posix())
            parent = parent.parent
    if directory_paths != expected_directories:
        raise PublicationExportError("ARTIFACT_DIRECTORY_SET_MISMATCH")

    _validate_artifact_mtime(input_dir, "ARTIFACT_DIRECTORY_MTIME_INVALID")
    for path in sorted(expected_directories):
        _validate_artifact_mtime(input_dir / path, "ARTIFACT_DIRECTORY_MTIME_INVALID")
    for path in sorted(expected_files):
        _validate_artifact_mtime(input_dir / path, "ARTIFACT_FILE_MTIME_INVALID")
    directory_identities = _artifact_directory_identities(
        input_dir,
        expected_directories,
        "ARTIFACT_DIRECTORY_CHANGED_DURING_VERIFICATION",
    )

    actual_files: list[SnapshotFile] = []
    total_bytes = 0
    for path in content_paths:
        data = _read_artifact_file(input_dir, path)
        total_bytes += len(data)
        if total_bytes > MAX_TOTAL_BYTES:
            raise PublicationExportError("ARTIFACT_TOTAL_TOO_LARGE")
        digest = hashlib.sha256(data).hexdigest()
        actual_files.append(SnapshotFile(path, data, digest))

    validate_snapshot(actual_files)
    expected_manifest, expected_checksums, actual_set_digest = generated_metadata(
        actual_files
    )
    if actual_set_digest != expected_content_set_sha256:
        raise PublicationExportError("ARTIFACT_EXPECTED_DIGEST_MISMATCH")
    if _read_artifact_file(input_dir, GENERATED_MANIFEST) != expected_manifest:
        raise PublicationExportError("ARTIFACT_GENERATED_MANIFEST_MISMATCH")
    if _read_artifact_file(input_dir, CHECKSUMS_FILE) != expected_checksums:
        raise PublicationExportError("ARTIFACT_CHECKSUMS_MISMATCH")

    _assert_artifact_root_unchanged(input_dir, root_identity)
    final_file_paths, final_directory_paths = enumerate_artifact(input_dir)
    _assert_artifact_root_unchanged(input_dir, root_identity)
    if final_file_paths != file_paths:
        raise PublicationExportError("ARTIFACT_FILE_SET_MISMATCH")
    if final_directory_paths != directory_paths:
        raise PublicationExportError("ARTIFACT_DIRECTORY_SET_MISMATCH")
    if (
        _artifact_directory_identities(
            input_dir,
            expected_directories,
            "ARTIFACT_DIRECTORY_CHANGED_DURING_VERIFICATION",
        )
        != directory_identities
    ):
        raise PublicationExportError("ARTIFACT_DIRECTORY_CHANGED_DURING_VERIFICATION")
    _assert_artifact_root_unchanged(input_dir, root_identity)

    return VerifiedSnapshot(
        report=ExportReport(
            content_count=len(actual_files),
            total_bytes=total_bytes,
            content_set_sha256=actual_set_digest,
        ),
        files=tuple(actual_files),
    )


def load_verified_snapshot(
    input_dir: Path, expected_content_set_sha256: str
) -> VerifiedSnapshot:
    """Verify a snapshot and return only the bytes used by that verification."""

    if os.name != "posix":
        raise PublicationExportError("PLATFORM_UNSUPPORTED")
    try:
        return _load_verified_snapshot(input_dir, expected_content_set_sha256)
    except PublicationExportError:
        raise
    except OSError as error:
        raise PublicationExportError("ARTIFACT_IO_FAILED") from error


def verify_snapshot(input_dir: Path, expected_content_set_sha256: str) -> ExportReport:
    """Verify a quiescent snapshot directory and return its immutable report."""

    return load_verified_snapshot(input_dir, expected_content_set_sha256).report


def _write_regular_file(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(data)
    path.chmod(0o644)
    os.utime(path, (SOURCE_DATE_EPOCH, SOURCE_DATE_EPOCH))


def _fix_directory_metadata(root: Path) -> None:
    directories = [root]
    directories.extend(path for path in root.rglob("*") if path.is_dir())
    for directory in sorted(
        directories, key=lambda path: len(path.parts), reverse=True
    ):
        directory.chmod(0o755)
        os.utime(directory, (SOURCE_DATE_EPOCH, SOURCE_DATE_EPOCH))


def _assert_output_location(repo_root: Path, output_dir: Path) -> None:
    if output_dir.exists() or output_dir.is_symlink():
        raise PublicationExportError("OUTPUT_ALREADY_EXISTS")
    if output_dir.name.casefold() == ".git" or _contains_control_character(
        output_dir.name
    ):
        raise PublicationExportError("OUTPUT_NAME_INVALID")
    parent = output_dir.parent
    if not parent.exists() or not parent.is_dir() or parent.is_symlink():
        raise PublicationExportError("OUTPUT_PARENT_INVALID")
    resolved_repo = repo_root.resolve()
    resolved_output = output_dir.resolve(strict=False)
    try:
        resolved_output.relative_to(resolved_repo)
    except ValueError:
        return
    raise PublicationExportError("OUTPUT_INSIDE_SOURCE_REPOSITORY")


def export_snapshot(
    repo_root: Path,
    output_dir: Path,
    source_ref: str = "HEAD",
) -> ExportReport:
    if os.name != "posix":
        raise PublicationExportError("PLATFORM_UNSUPPORTED")
    output_created = False
    try:
        _assert_output_location(repo_root, output_dir)
        files = snapshot_from_commit(repo_root, source_ref)
        manifest_bytes, checksum_bytes, set_digest = generated_metadata(files)
        output_dir.mkdir(mode=0o700)
        output_created = True
        for file in files:
            _write_regular_file(output_dir / file.path, file.data)
        _write_regular_file(output_dir / GENERATED_MANIFEST, manifest_bytes)
        _write_regular_file(output_dir / CHECKSUMS_FILE, checksum_bytes)
        _fix_directory_metadata(output_dir)
        verified = verify_snapshot(output_dir, set_digest)
        if verified.content_set_sha256 != set_digest:
            raise PublicationExportError("OUTPUT_POST_WRITE_VERIFY_FAILED")
    except PublicationExportError:
        if output_created:
            try:
                shutil.rmtree(output_dir)
            except OSError as cleanup_error:
                raise PublicationExportError("OUTPUT_CLEANUP_FAILED") from cleanup_error
        raise
    except OSError as error:
        if output_created:
            try:
                shutil.rmtree(output_dir)
            except OSError as cleanup_error:
                raise PublicationExportError("OUTPUT_CLEANUP_FAILED") from cleanup_error
        raise PublicationExportError("OUTPUT_IO_FAILED") from error

    return ExportReport(
        content_count=len(files),
        total_bytes=sum(file.size for file in files),
        content_set_sha256=set_digest,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export a deterministic Project Covenant public snapshot."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    export_parser = subparsers.add_parser(
        "export", help="Export approved files from one resolved Git commit."
    )
    export_parser.add_argument("--ref", default="HEAD", help="Git commit or ref.")
    export_parser.add_argument(
        "--output",
        required=True,
        type=Path,
        help="New output directory outside the repo.",
    )
    verify_parser = subparsers.add_parser(
        "verify", help="Verify an exported snapshot without reading Git metadata."
    )
    verify_parser.add_argument(
        "--input", required=True, type=Path, help="Exported snapshot directory."
    )
    verify_parser.add_argument(
        "--expected-content-set-sha256",
        required=True,
        help="Trusted digest printed by the export command.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        if args.command == "export":
            report = export_snapshot(ROOT, args.output, args.ref)
            action = "export"
        elif args.command == "verify":
            report = verify_snapshot(args.input, args.expected_content_set_sha256)
            action = "verify"
        else:
            raise PublicationExportError("COMMAND_UNSUPPORTED")
    except PublicationExportError as error:
        print(f"error_code={error.code}")
        print(f"publication_{args.command}=FAIL")
        return 1
    except Exception:
        print("error_code=INTERNAL_ERROR")
        print(f"publication_{args.command}=FAIL")
        return 1
    print(f"publication_content_files={report.content_count}")
    print(f"publication_content_bytes={report.total_bytes}")
    print(f"publication_content_set_sha256={report.content_set_sha256}")
    print(f"publication_{action}=PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
