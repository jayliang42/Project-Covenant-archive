#!/usr/bin/env python3
"""Build and verify a deterministic, privacy-limited static reading site."""

from __future__ import annotations

import argparse
import hashlib
import html
import os
import posixpath
import re
import shutil
import stat
import string
import sys
import unicodedata
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING
from urllib.parse import quote, unquote, urlsplit

if TYPE_CHECKING:
    from scripts import audit_publication as publication_audit
    from scripts import export_publication as publication_export
    from scripts import site_reader
    from scripts import publication_assets
elif __package__:
    from . import audit_publication as publication_audit
    from . import export_publication as publication_export
    from . import site_reader
    from . import publication_assets
else:
    import audit_publication as publication_audit
    import export_publication as publication_export
    import site_reader
    import publication_assets


SITE_FORMAT = "project-covenant-static-site/v1"
SITE_CSS_PATH = "assets/site.css"
MAX_SITE_FILES = publication_export.MAX_FILES
MAX_SITE_FILE_BYTES = 8 * 1024 * 1024
MAX_SITE_TOTAL_BYTES = 100 * 1024 * 1024
MAX_SITE_ENTRIES = MAX_SITE_FILES * 4
MAX_MARKDOWN_LINE_BYTES = 128 * 1024
MAX_RENDER_DEPTH = 32
MAX_INLINE_DEPTH = 64

HEADING = re.compile(r"^( {0,3})(#{1,6})[ \t]+(.+?)\s*$")
STABLE_ANCHOR = re.compile(r'^<a id="([A-Za-z0-9][A-Za-z0-9._:-]*)"></a>$')
LINE_BREAK = re.compile(r"(?i)^<br\s*/?>")
FENCE = re.compile(r"^( {0,3})(`{3,}|~{3,})(.*)$")
LIST_ITEM = re.compile(r"^( *)(-|(\d+)\.)[ \t]+(.*)$")
TABLE_SEPARATOR_CELL = re.compile(r"^:?-{3,}:?$")
THEMATIC_BREAK = re.compile(r"^ {0,3}(?:-{3,}|\*{3,}|_{3,})\s*$")
CONTROL = re.compile(r"[\x00-\x1f\x7f]")
GIT_HOST = re.compile(
    r"(?i)(?:[A-Za-z0-9-]+\.)*"
    r"(?:github\.com|githubusercontent\.com|github\.io)"
    r"\.*(?=$|[^A-Za-z0-9.-])"
)

NAVIGATION = (
    ("README.md", "Home | 首页"),
    ("Bible_Timeline/README.md", "Storyline | 故事线"),
    (
        "Bible_Timeline/52周圣经故事线_查经与史料阅读计划.md",
        "52-Week Plan | 52 周计划",
    ),
    ("Bible_Timeline/Bible_By_Book_Bilingual.md", "Books | 逐卷"),
    ("Bible_Timeline/史料与考古旁证索引.md", "Evidence | 旁证"),
    ("Bilingual_Notes/README.md", "Notes | 笔记"),
    ("Book_Studies/README.md", "Library | 图书馆"),
    ("Christian_Traditions/README.md", "Traditions | 宗派"),
    ("Bible_Translations/README.md", "Translations | 译本"),
)

SITE_CSS = site_reader.SITE_CSS


class SiteBuildError(RuntimeError):
    """A fail-closed site error whose code contains no private path or data."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class SiteReport:
    page_count: int
    file_count: int
    total_bytes: int
    site_set_sha256: str


@dataclass
class _ListEntry:
    indent: int
    ordered: bool
    number: int
    lines: list[str]
    children: list["_ListGroup"] = field(default_factory=list)


@dataclass
class _ListGroup:
    ordered: bool
    start: int
    items: list[_ListEntry] = field(default_factory=list)


@dataclass(frozen=True)
class _Page:
    source_path: str
    output_path: str
    title: str
    body: str


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _portable_key(path: str) -> str:
    return unicodedata.normalize("NFC", path).casefold()


def source_path_to_output(source_path: str) -> str:
    source = PurePosixPath(source_path)
    if source.suffix != ".md" or not source.parts:
        raise SiteBuildError("SITE_SOURCE_NOT_MARKDOWN")
    if source.name == "README.md":
        output = source.parent / "index.html"
    else:
        output = source.with_suffix(".html")
    return output.as_posix()


def _page_map(source_paths: list[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    portable: dict[str, str] = {}
    all_output_paths: set[str] = {SITE_CSS_PATH}
    for source in sorted(source_paths):
        output = source_path_to_output(source)
        key = _portable_key(output)
        if key in portable:
            raise SiteBuildError("SITE_OUTPUT_PATH_COLLISION")
        portable[key] = output
        result[source] = output
        all_output_paths.add(output)

    file_keys = {_portable_key(path) for path in all_output_paths}
    for path in all_output_paths:
        parent = PurePosixPath(path).parent
        while parent.as_posix() != ".":
            if _portable_key(parent.as_posix()) in file_keys:
                raise SiteBuildError("SITE_FILE_DIRECTORY_COLLISION")
            parent = parent.parent
    return result


def _is_escaped(text: str, index: int) -> bool:
    slashes = 0
    cursor = index - 1
    while cursor >= 0 and text[cursor] == "\\":
        slashes += 1
        cursor -= 1
    return slashes % 2 == 1


def _matching_bracket(text: str, opening: int) -> int | None:
    depth = 1
    cursor = opening + 1
    while cursor < len(text):
        if _is_escaped(text, cursor):
            cursor += 2
            continue
        if text[cursor] == "[":
            depth += 1
        elif text[cursor] == "]":
            depth -= 1
            if depth == 0:
                return cursor
        cursor += 1
    return None


def _matching_parenthesis(text: str, opening: int) -> int | None:
    depth = 1
    cursor = opening + 1
    while cursor < len(text):
        if _is_escaped(text, cursor):
            cursor += 2
            continue
        if text[cursor] == "(":
            depth += 1
        elif text[cursor] == ")":
            depth -= 1
            if depth == 0:
                return cursor
        cursor += 1
    return None


def _destination_token(raw_target: str) -> str:
    target = raw_target.strip()
    if not target:
        raise SiteBuildError("SITE_LINK_TARGET_EMPTY")
    if target.startswith("<"):
        end = target.find(">")
        if end <= 1:
            raise SiteBuildError("SITE_LINK_TARGET_INVALID")
        token = target[1:end]
    else:
        cursor = 0
        while cursor < len(target) and not target[cursor].isspace():
            cursor += 1
        token = target[:cursor]
    token = re.sub(
        rf"\\([{re.escape(string.punctuation)}])", r"\1", html.unescape(token)
    )
    if not token or CONTROL.search(token):
        raise SiteBuildError("SITE_LINK_TARGET_INVALID")
    return token


def _relative_href(current_output: str, target_output: str) -> str:
    current_parent = PurePosixPath(current_output).parent.as_posix()
    start = current_parent if current_parent != "." else ""
    relative = posixpath.relpath(target_output, start=start or ".")
    return quote(relative, safe="/-._~")


def _render_link(
    label: str,
    raw_target: str,
    current_source: str,
    current_output: str,
    page_map: dict[str, str],
    depth: int,
) -> str:
    token = _destination_token(raw_target)
    try:
        parsed = urlsplit(token)
    except ValueError as error:
        raise SiteBuildError("SITE_LINK_URL_INVALID") from error
    try:
        resolved_target = publication_export.resolved_local_target(
            current_source, raw_target
        )
    except publication_export.PublicationExportError as error:
        raise SiteBuildError(f"SITE_LINK_{error.code}") from error
    is_local = not parsed.scheme and not parsed.netloc
    local_target = current_source if is_local and not parsed.path else resolved_target
    rendered_label = _render_inline(
        label, current_source, current_output, page_map, depth=depth + 1
    )
    if not is_local:
        if parsed.scheme.casefold() != "https" or not parsed.netloc:
            raise SiteBuildError("SITE_EXTERNAL_LINK_FORBIDDEN")
        if parsed.username or parsed.password or GIT_HOST.search(parsed.hostname or ""):
            raise SiteBuildError("SITE_EXTERNAL_LINK_FORBIDDEN")
        href = html.escape(token, quote=True)
        return (
            f'<a href="{href}" rel="external noopener noreferrer" '
            f'referrerpolicy="no-referrer">{rendered_label}</a>'
        )

    if local_target is None:
        raise SiteBuildError("SITE_LOCAL_LINK_PATH_INVALID")
    if parsed.query:
        raise SiteBuildError("SITE_LOCAL_LINK_QUERY_FORBIDDEN")
    if local_target not in page_map:
        raise SiteBuildError("SITE_LOCAL_LINK_NOT_PAGE")
    if not parsed.path and parsed.fragment:
        href = ""
    else:
        href = _relative_href(current_output, page_map[local_target])
    if parsed.fragment:
        href += "#" + quote(unquote(parsed.fragment), safe="-._~:")
    return f'<a href="{html.escape(href, quote=True)}">{rendered_label}</a>'


def _find_unescaped(text: str, token: str, start: int) -> int:
    cursor = start
    while True:
        found = text.find(token, cursor)
        if found < 0:
            return -1
        if not _is_escaped(text, found):
            return found
        cursor = found + len(token)


def _underscore_can_open(text: str, index: int) -> bool:
    if index + 1 >= len(text) or text[index + 1] in "_ \t\r\n":
        return False
    return index == 0 or not text[index - 1].isalnum()


def _underscore_can_close(text: str, index: int) -> bool:
    if index == 0 or text[index - 1].isspace():
        return False
    return index + 1 == len(text) or not text[index + 1].isalnum()


def _render_inline(
    text: str,
    current_source: str,
    current_output: str,
    page_map: dict[str, str],
    *,
    depth: int = 0,
) -> str:
    if depth > MAX_INLINE_DEPTH:
        raise SiteBuildError("SITE_INLINE_NESTING_FORBIDDEN")
    output: list[str] = []
    literal: list[str] = []

    def flush_literal() -> None:
        if literal:
            output.append(html.escape(html.unescape("".join(literal))))
            literal.clear()

    cursor = 0
    while cursor < len(text):
        line_break = LINE_BREAK.match(text[cursor:])
        if line_break:
            flush_literal()
            output.append("<br>")
            cursor += line_break.end()
            continue

        if text[cursor] == "\\" and cursor + 1 < len(text):
            next_character = text[cursor + 1]
            if next_character in string.punctuation:
                literal.append(next_character)
                cursor += 2
                continue

        if text[cursor] == "`" and not _is_escaped(text, cursor):
            run = 1
            while cursor + run < len(text) and text[cursor + run] == "`":
                run += 1
            marker = "`" * run
            closing = _find_unescaped(text, marker, cursor + run)
            if closing >= 0:
                flush_literal()
                code = text[cursor + run : closing].replace("\n", " ")
                if code.startswith(" ") and code.endswith(" ") and code.strip():
                    code = code[1:-1]
                output.append(f"<code>{html.escape(code)}</code>")
                cursor = closing + run
                continue

        if text.startswith("![", cursor) and not _is_escaped(text, cursor):
            bracket_end = _matching_bracket(text, cursor + 1)
            if bracket_end is None or text[bracket_end + 1:bracket_end + 2] != "(":
                raise SiteBuildError("SITE_IMAGE_MALFORMED")
            destination_end = _matching_parenthesis(text, bracket_end + 1)
            if destination_end is None:
                raise SiteBuildError("SITE_IMAGE_MALFORMED")
            raw_target = text[bracket_end + 2:destination_end]
            try:
                target = publication_export.resolved_local_target(current_source, raw_target)
            except publication_export.PublicationExportError as error:
                raise SiteBuildError("SITE_IMAGE_TARGET_FORBIDDEN") from error
            parsed_image = urlsplit(_destination_token(raw_target))
            if target is None or not publication_assets.is_asset_path(target) or target not in page_map or parsed_image.query or parsed_image.fragment:
                raise SiteBuildError("SITE_IMAGE_TARGET_FORBIDDEN")
            alt = text[cursor + 2:bracket_end].strip()
            if not alt:
                raise SiteBuildError("SITE_IMAGE_ALT_REQUIRED")
            source = html.escape(_relative_href(current_output, page_map[target]), quote=True)
            image_class = "study-map" if target.endswith(".svg") else "study-illustration"
            rendered_image = f'<img class="{image_class}" src="{source}" alt="{html.escape(alt, quote=True)}">'
            if image_class == "study-map":
                rendered_image = '<span class="map-viewport" role="region" tabindex="0" aria-label="Map, scroll horizontally | 地图，可横向滚动">' + rendered_image + '</span>'
            flush_literal()
            output.append(rendered_image)
            cursor = destination_end + 1
            continue

        if text[cursor] == "[" and not _is_escaped(text, cursor):
            bracket_end = _matching_bracket(text, cursor)
            if (
                bracket_end is not None
                and bracket_end + 1 < len(text)
                and text[bracket_end + 1] == "("
            ):
                destination_end = _matching_parenthesis(text, bracket_end + 1)
                if destination_end is None:
                    raise SiteBuildError("SITE_LINK_MALFORMED")
                flush_literal()
                output.append(
                    _render_link(
                        text[cursor + 1 : bracket_end],
                        text[bracket_end + 2 : destination_end],
                        current_source,
                        current_output,
                        page_map,
                        depth,
                    )
                )
                cursor = destination_end + 1
                continue

        if text.startswith("**", cursor) and not _is_escaped(text, cursor):
            closing = _find_unescaped(text, "**", cursor + 2)
            if closing > cursor + 2:
                flush_literal()
                inner = _render_inline(
                    text[cursor + 2 : closing],
                    current_source,
                    current_output,
                    page_map,
                    depth=depth + 1,
                )
                output.append(f"<strong>{inner}</strong>")
                cursor = closing + 2
                continue

        if text[cursor] == "*" and not _is_escaped(text, cursor):
            closing = _find_unescaped(text, "*", cursor + 1)
            if closing > cursor + 1:
                flush_literal()
                inner = _render_inline(
                    text[cursor + 1 : closing],
                    current_source,
                    current_output,
                    page_map,
                    depth=depth + 1,
                )
                output.append(f"<em>{inner}</em>")
                cursor = closing + 1
                continue

        if (
            text[cursor] == "_"
            and not _is_escaped(text, cursor)
            and _underscore_can_open(text, cursor)
        ):
            closing = _find_unescaped(text, "_", cursor + 1)
            if closing > cursor + 1 and _underscore_can_close(text, closing):
                flush_literal()
                inner = _render_inline(
                    text[cursor + 1 : closing],
                    current_source,
                    current_output,
                    page_map,
                    depth=depth + 1,
                )
                output.append(f"<em>{inner}</em>")
                cursor = closing + 1
                continue

        literal.append(text[cursor])
        cursor += 1

    flush_literal()
    return "".join(output)


def _plain_heading(text: str) -> str:
    value = text.strip()
    value = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", value)
    value = re.sub(r"`+([^`]*)`+", r"\1", value)
    value = value.replace("**", "").replace("*", "").replace("_", "")
    value = html.unescape(value).strip()
    if not value:
        raise SiteBuildError("SITE_HEADING_EMPTY")
    return value


def _heading_slug(text: str) -> str:
    value = _plain_heading(text).casefold()
    output: list[str] = []
    previous_dash = False
    for character in value:
        category = unicodedata.category(character)
        if character.isspace() or character == "-":
            if output and not previous_dash:
                output.append("-")
                previous_dash = True
        elif category[0] in {"L", "N"} or character in "._:":
            output.append(character)
            previous_dash = False
    slug = "".join(output).strip("-")
    return slug or "section"


def _split_table_row(line: str) -> list[str]:
    stripped = line.strip()
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|"):
        stripped = stripped[:-1]
    return [cell.strip() for cell in stripped.split("|")]


def _table_separator(line: str) -> list[str] | None:
    cells = _split_table_row(line)
    if not cells or any(not TABLE_SEPARATOR_CELL.fullmatch(cell) for cell in cells):
        return None
    return cells


def _parse_list_group(
    lines: list[str], start: int, indent: int, depth: int
) -> tuple[_ListGroup, int]:
    if depth > MAX_RENDER_DEPTH:
        raise SiteBuildError("SITE_LIST_NESTING_FORBIDDEN")
    first = LIST_ITEM.match(lines[start])
    if first is None or len(first.group(1)) != indent:
        raise SiteBuildError("SITE_LIST_INVALID")
    ordered = first.group(3) is not None
    group = _ListGroup(ordered=ordered, start=_ordered_list_number(first.group(3)))
    cursor = start
    current: _ListEntry | None = None

    while cursor < len(lines):
        line = lines[cursor]
        match = LIST_ITEM.match(line)
        if match is not None:
            item_indent = len(match.group(1))
            item_ordered = match.group(3) is not None
            if item_indent < indent:
                break
            if item_indent > indent:
                if current is None:
                    break
                child, cursor = _parse_list_group(lines, cursor, item_indent, depth + 1)
                current.children.append(child)
                continue
            if item_ordered != ordered:
                break
            current = _ListEntry(
                indent=item_indent,
                ordered=item_ordered,
                number=_ordered_list_number(match.group(3)),
                lines=[match.group(4)],
            )
            group.items.append(current)
            cursor += 1
            continue

        if not line.strip():
            lookahead = cursor + 1
            while lookahead < len(lines) and not lines[lookahead].strip():
                lookahead += 1
            if lookahead < len(lines):
                following = LIST_ITEM.match(lines[lookahead])
                if following is not None and len(following.group(1)) >= indent:
                    cursor = lookahead
                    continue
            break

        leading = len(line) - len(line.lstrip(" "))
        if current is not None and leading > indent:
            current.lines.append(line.strip())
            cursor += 1
            continue
        break

    return group, cursor


def _ordered_list_number(value: str | None) -> int:
    if value is None:
        return 1
    try:
        return int(value)
    except ValueError as error:
        raise SiteBuildError("SITE_ORDERED_LIST_NUMBER_INVALID") from error


def _is_closing_fence(line: str, marker: str) -> bool:
    stripped = line.lstrip(" ")
    if len(line) - len(stripped) > 3:
        return False
    marker_character = marker[0]
    run_length = len(stripped) - len(stripped.lstrip(marker_character))
    return run_length >= len(marker) and not stripped[run_length:].strip()


class _MarkdownRenderer:
    def __init__(
        self,
        source_path: str,
        output_path: str,
        page_map: dict[str, str],
        text: str,
    ):
        self.source_path = source_path
        self.output_path = output_path
        self.page_map = page_map
        self.text = text
        self.explicit_ids = set(STABLE_ANCHOR.findall(text))
        self.used_ids = set(self.explicit_ids)
        self.slug_counts: dict[str, int] = {}

    def inline(self, text: str) -> str:
        return _render_inline(text, self.source_path, self.output_path, self.page_map)

    def heading_id(self, heading: str) -> str | None:
        base = _heading_slug(heading)
        if base in self.explicit_ids:
            return None
        count = self.slug_counts.get(base, 0)
        candidate = base if count == 0 else f"{base}-{count}"
        while candidate in self.used_ids:
            count += 1
            candidate = f"{base}-{count}"
        self.slug_counts[base] = count + 1
        self.used_ids.add(candidate)
        return candidate

    def render_list(self, group: _ListGroup) -> str:
        tag = "ol" if group.ordered else "ul"
        start_attribute = ""
        if group.ordered and group.start != 1:
            start_attribute = f' start="{group.start}"'
        output = [f"<{tag}{start_attribute}>"]
        for item in group.items:
            first = item.lines[0] if item.lines else ""
            task = re.match(r"^\[([ xX])\][ \t]+(.*)$", first)
            if task:
                marker = "☑" if task.group(1).casefold() == "x" else "☐"
                item.lines[0] = task.group(2)
                prefix = f'<span class="task-marker" aria-hidden="true">{marker}</span>'
            else:
                prefix = ""
            rendered_lines = [self.inline(line) for line in item.lines]
            content = "<br>".join(rendered_lines)
            output.append(f"<li>{prefix}{content}")
            for child in item.children:
                output.append(self.render_list(child))
            output.append("</li>")
        output.append(f"</{tag}>")
        return "\n".join(output)

    def render_blocks(self, lines: list[str], depth: int = 0) -> str:
        if depth > MAX_RENDER_DEPTH:
            raise SiteBuildError("SITE_BLOCK_NESTING_FORBIDDEN")
        output: list[str] = []
        cursor = 0
        while cursor < len(lines):
            line = lines[cursor]
            stripped = line.strip()
            if not stripped:
                cursor += 1
                continue

            anchor = STABLE_ANCHOR.fullmatch(stripped)
            if anchor:
                output.append(
                    f'<a id="{anchor.group(1)}" class="anchor" aria-hidden="true"></a>'
                )
                cursor += 1
                continue

            fence = FENCE.match(line)
            if fence:
                marker = fence.group(2)
                code_lines: list[str] = []
                cursor += 1
                while cursor < len(lines):
                    if _is_closing_fence(lines[cursor], marker):
                        cursor += 1
                        break
                    code_lines.append(lines[cursor])
                    cursor += 1
                code = "\n".join(code_lines)
                if code_lines:
                    code += "\n"
                output.append(f"<pre><code>{html.escape(code)}</code></pre>")
                continue

            heading = HEADING.match(line)
            if heading:
                level = len(heading.group(2))
                heading_text = heading.group(3).rstrip("#").rstrip()
                identifier = self.heading_id(heading_text)
                attribute = (
                    f' id="{html.escape(identifier, quote=True)}"' if identifier else ""
                )
                output.append(
                    f"<h{level}{attribute}>{self.inline(heading_text)}</h{level}>"
                )
                cursor += 1
                continue

            if THEMATIC_BREAK.fullmatch(line):
                output.append("<hr>")
                cursor += 1
                continue

            if stripped.startswith(">"):
                quote_lines: list[str] = []
                while cursor < len(lines) and lines[cursor].lstrip().startswith(">"):
                    quote_line = lines[cursor].lstrip()[1:]
                    if quote_line.startswith(" "):
                        quote_line = quote_line[1:]
                    quote_lines.append(quote_line)
                    cursor += 1
                inner = self.render_blocks(quote_lines, depth + 1)
                output.append(f"<blockquote>\n{inner}\n</blockquote>")
                continue

            if cursor + 1 < len(lines) and "|" in line:
                separator = _table_separator(lines[cursor + 1])
                if separator is not None:
                    headers = _split_table_row(line)
                    if len(headers) != len(separator):
                        raise SiteBuildError("SITE_TABLE_COLUMN_MISMATCH")
                    aligns = [
                        "align-right" if cell.endswith(":") else ""
                        for cell in separator
                    ]
                    rows: list[list[str]] = []
                    cursor += 2
                    while (
                        cursor < len(lines)
                        and "|" in lines[cursor]
                        and lines[cursor].strip()
                    ):
                        row = _split_table_row(lines[cursor])
                        if len(row) != len(headers):
                            raise SiteBuildError("SITE_TABLE_COLUMN_MISMATCH")
                        rows.append(row)
                        cursor += 1
                    table = ['<div class="table-scroll">', "<table>", "<thead>", "<tr>"]
                    for index, cell in enumerate(headers):
                        class_attribute = (
                            f' class="{aligns[index]}"' if aligns[index] else ""
                        )
                        table.append(
                            f'<th scope="col"{class_attribute}>{self.inline(cell)}</th>'
                        )
                    table.extend(["</tr>", "</thead>", "<tbody>"])
                    for row in rows:
                        table.append("<tr>")
                        for index, cell in enumerate(row):
                            class_attribute = (
                                f' class="{aligns[index]}"' if aligns[index] else ""
                            )
                            table.append(
                                f"<td{class_attribute}>{self.inline(cell)}</td>"
                            )
                        table.append("</tr>")
                    table.extend(["</tbody>", "</table>", "</div>"])
                    output.append("\n".join(table))
                    continue

            list_match = LIST_ITEM.match(line)
            if list_match:
                group, cursor = _parse_list_group(
                    lines, cursor, len(list_match.group(1)), depth
                )
                output.append(self.render_list(group))
                continue

            paragraph_lines = [stripped]
            cursor += 1
            while cursor < len(lines) and lines[cursor].strip():
                next_line = lines[cursor]
                next_stripped = next_line.strip()
                if (
                    STABLE_ANCHOR.fullmatch(next_stripped)
                    or FENCE.match(next_line)
                    or HEADING.match(next_line)
                    or THEMATIC_BREAK.fullmatch(next_line)
                    or next_stripped.startswith(">")
                    or LIST_ITEM.match(next_line)
                    or (
                        cursor + 1 < len(lines)
                        and "|" in next_line
                        and _table_separator(lines[cursor + 1]) is not None
                    )
                ):
                    break
                paragraph_lines.append(next_stripped)
                cursor += 1
            output.append(f"<p>{self.inline(' '.join(paragraph_lines))}</p>")

        return "\n".join(output)

    def render(self) -> str:
        return self.render_blocks(self.text.splitlines())


def render_markdown_body(source_path: str, text: str, page_map: dict[str, str]) -> str:
    if source_path not in page_map:
        raise SiteBuildError("SITE_SOURCE_PAGE_MISSING")
    return _MarkdownRenderer(
        source_path, page_map[source_path], page_map, text
    ).render()


def _first_h1(text: str) -> str:
    for line in text.splitlines():
        match = HEADING.match(line)
        if match and len(match.group(2)) == 1:
            return _plain_heading(match.group(3).rstrip("#").rstrip())
    raise SiteBuildError("SITE_PAGE_H1_MISSING")


def _nav_html(current_output: str, page_map: dict[str, str]) -> str:
    links: list[str] = []
    for source, label in NAVIGATION:
        if source not in page_map:
            continue
        href = _relative_href(current_output, page_map[source])
        links.append(
            f'<a href="{html.escape(href, quote=True)}">{html.escape(label)}</a>'
        )
    return "\n".join(links)


def _page_html(
    page: _Page, page_map: dict[str, str],
    page_titles: dict[str, str] | None = None,
) -> bytes:
    if "README.md" not in page_map:
        raise SiteBuildError("SITE_ROOT_PAGE_MISSING")
    return site_reader.render_page(
        page.source_path, page.output_path, page.title, page.body,
        page_map, page_titles or {page.source_path: page.title}, SITE_CSS_PATH,
    )


def _site_digest(files: dict[str, bytes]) -> str:
    digest = hashlib.sha256()
    digest.update(SITE_FORMAT.encode("ascii") + b"\0")
    for path, data in sorted(files.items()):
        path_bytes = path.encode("utf-8")
        digest.update(len(path_bytes).to_bytes(4, "big"))
        digest.update(path_bytes)
        digest.update(len(data).to_bytes(8, "big"))
        digest.update(data)
    return digest.hexdigest()


def _load_expected_site(
    snapshot_dir: Path, expected_content_set_sha256: str
) -> tuple[dict[str, bytes], int]:
    try:
        verified = publication_export.load_verified_snapshot(
            snapshot_dir, expected_content_set_sha256
        )
    except publication_export.PublicationExportError as error:
        raise SiteBuildError(f"SOURCE_{error.code}") from error

    markdown_files = [file for file in verified.files if file.path.endswith(".md")]
    other_content = [
        file.path
        for file in verified.files
        if not file.path.endswith(".md")
        and file.path != publication_export.MANIFEST_PATH
        and not publication_assets.is_asset_path(file.path)
    ]
    if other_content:
        raise SiteBuildError("SITE_NON_MARKDOWN_CONTENT_FORBIDDEN")
    page_map = _page_map([file.path for file in markdown_files])
    if "README.md" not in page_map:
        raise SiteBuildError("SITE_ROOT_PAGE_MISSING")

    asset_files = {file.path: file.data for file in verified.files if publication_assets.is_asset_path(file.path)}
    render_map = {**page_map, **{path: path for path in asset_files}}
    pages: list[_Page] = []
    for file in markdown_files:
        try:
            text = file.data.decode("utf-8")
        except UnicodeDecodeError as error:
            raise SiteBuildError("SITE_SOURCE_NOT_UTF8") from error
        if any(
            len(line.encode("utf-8")) > MAX_MARKDOWN_LINE_BYTES
            for line in text.splitlines()
        ):
            raise SiteBuildError("SITE_MARKDOWN_LINE_TOO_LARGE")
        pages.append(
            _Page(
                source_path=file.path,
                output_path=page_map[file.path],
                title=_first_h1(text),
                body=render_markdown_body(file.path, text, render_map),
            )
        )

    page_titles = {page.source_path: page.title for page in pages}
    expected: dict[str, bytes] = {SITE_CSS_PATH: SITE_CSS, **asset_files}
    for page in pages:
        expected[page.output_path] = _page_html(page, page_map, page_titles)
    if len(expected) > MAX_SITE_FILES:
        raise SiteBuildError("SITE_FILE_LIMIT_EXCEEDED")
    if any(len(data) > MAX_SITE_FILE_BYTES for data in expected.values()):
        raise SiteBuildError("SITE_FILE_TOO_LARGE")
    if sum(map(len, expected.values())) > MAX_SITE_TOTAL_BYTES:
        raise SiteBuildError("SITE_TOTAL_TOO_LARGE")
    _validate_generated_site(expected)
    return expected, len(pages)


ALLOWED_TAG_ATTRIBUTES: dict[str, set[str]] = {
    "html": {"lang"},
    "head": set(),
    "meta": {"charset", "name", "content", "http-equiv"},
    "title": set(),
    "link": {"rel", "href"},
    "body": set(),
    "a": {"href", "id", "class", "rel", "referrerpolicy", "aria-hidden", "aria-current"},
    "header": {"class"},
    "nav": {"class", "aria-label"},
    "main": {"id", "class", "tabindex"},
    "aside": {"class"},
    "article": {"class"},
    "details": {"class"},
    "summary": set(),
    "footer": {"class"},
    "div": {"class"},
    "p": set(),
    "h1": {"id"},
    "h2": {"id"},
    "h3": {"id"},
    "h4": {"id"},
    "h5": {"id"},
    "h6": {"id"},
    "ul": set(),
    "ol": {"start"},
    "li": set(),
    "strong": set(),
    "em": set(),
    "code": set(),
    "pre": set(),
    "blockquote": set(),
    "table": set(),
    "thead": set(),
    "tbody": set(),
    "tr": set(),
    "th": {"scope", "class"},
    "td": {"class"},
    "hr": set(),
    "br": set(),
    "span": {"class", "aria-hidden", "role", "tabindex", "aria-label"},
    "img": {"src", "alt", "class"},
}


class _HTMLPolicyParser(HTMLParser):
    def __init__(self, page_path: str):
        super().__init__(convert_charrefs=True)
        self.page_path = page_path
        self.ids: set[str] = set()
        self.links: list[tuple[str, dict[str, str]]] = []
        self.stylesheets: list[str] = []
        self.images: list[dict[str, str]] = []
        self.declarations = 0
        self.csp_values: list[str] = []
        self.referrer_values: list[str] = []
        self.element_counts: dict[str, int] = {}

    def handle_decl(self, decl: str) -> None:
        if decl.casefold() != "doctype html":
            raise SiteBuildError("SITE_HTML_DECLARATION_FORBIDDEN")
        self.declarations += 1

    def handle_comment(self, data: str) -> None:
        raise SiteBuildError("SITE_HTML_COMMENT_FORBIDDEN")

    def handle_pi(self, data: str) -> None:
        raise SiteBuildError("SITE_HTML_PROCESSING_INSTRUCTION_FORBIDDEN")

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.casefold()
        if tag not in ALLOWED_TAG_ATTRIBUTES:
            raise SiteBuildError("SITE_HTML_TAG_FORBIDDEN")
        self.element_counts[tag] = self.element_counts.get(tag, 0) + 1
        values: dict[str, str] = {}
        for raw_name, raw_value in attrs:
            name = raw_name.casefold()
            if (
                name in values
                or name not in ALLOWED_TAG_ATTRIBUTES[tag]
                or name.startswith("on")
            ):
                raise SiteBuildError("SITE_HTML_ATTRIBUTE_FORBIDDEN")
            if raw_value is None or CONTROL.search(raw_value):
                raise SiteBuildError("SITE_HTML_ATTRIBUTE_INVALID")
            values[name] = raw_value

        identifier = values.get("id")
        if identifier is not None:
            if (
                not identifier
                or len(identifier.encode("utf-8")) > 512
                or any(
                    character.isspace()
                    or unicodedata.category(character).startswith("C")
                    or character in "\"'<>"
                    for character in identifier
                )
                or identifier in self.ids
            ):
                raise SiteBuildError("SITE_HTML_ID_INVALID")
            self.ids.add(identifier)

        if tag == "a" and "href" in values:
            self.links.append((values["href"], values))
        if tag == "img":
            if not values.get("src") or not values.get("alt", "").strip():
                raise SiteBuildError("SITE_IMAGE_ALT_OR_SOURCE_REQUIRED")
            self.images.append(values)
        if tag == "link":
            if values.get("rel") != "stylesheet" or "href" not in values:
                raise SiteBuildError("SITE_STYLESHEET_LINK_INVALID")
            self.stylesheets.append(values["href"])
        if tag == "meta":
            if values.get("http-equiv", "").casefold() == "content-security-policy":
                self.csp_values.append(values.get("content", ""))
            if values.get("name", "").casefold() == "referrer":
                self.referrer_values.append(values.get("content", ""))
            if values.get("http-equiv", "").casefold() == "refresh":
                raise SiteBuildError("SITE_META_REFRESH_FORBIDDEN")


def _normalize_site_path(current_path: str, href_path: str) -> str:
    decoded = unquote(href_path)
    if decoded.startswith("/") or "\\" in decoded or CONTROL.search(decoded):
        raise SiteBuildError("SITE_LINK_PATH_FORBIDDEN")
    parts = list(PurePosixPath(current_path).parent.parts)
    for part in decoded.split("/"):
        if not part or part == ".":
            continue
        if part == "..":
            if not parts:
                raise SiteBuildError("SITE_LINK_ESCAPES_ROOT")
            parts.pop()
            continue
        parts.append(part)
    if not parts:
        raise SiteBuildError("SITE_LINK_PATH_FORBIDDEN")
    return PurePosixPath(*parts).as_posix()


def _validate_generated_site(files: dict[str, bytes]) -> None:
    if SITE_CSS_PATH not in files or not files:
        raise SiteBuildError("SITE_CSS_MISSING")
    css = files[SITE_CSS_PATH]
    css_lower = css.lower()
    if any(
        token in css_lower
        for token in (b"url(", b"@import", b"@font-face", b"http://", b"https://")
    ):
        raise SiteBuildError("SITE_CSS_REMOTE_RESOURCE_FORBIDDEN")

    html_paths = {path for path in files if path.endswith(".html")}
    page_ids: dict[str, set[str]] = {}
    page_links: dict[str, list[tuple[str, dict[str, str]]]] = {}
    expected_csp_parts = (
        "default-src 'none'",
        "style-src 'self'",
        "img-src 'self'",
        "script-src 'none'",
        "connect-src 'none'",
        "object-src 'none'",
        "form-action 'none'",
        "base-uri 'none'",
    )
    for asset_path, data in files.items():
        if publication_assets.is_asset_path(asset_path):
            try:
                publication_assets.validate_asset(asset_path, data)
            except publication_assets.AssetError as error:
                raise SiteBuildError(str(error)) from error
    for path in sorted(html_paths):
        try:
            text = files[path].decode("utf-8")
        except UnicodeDecodeError as error:
            raise SiteBuildError("SITE_HTML_NOT_UTF8") from error
        if "<!--" in text or "-->" in text:
            raise SiteBuildError("SITE_HTML_COMMENT_FORBIDDEN")
        findings = publication_audit.scan_text(
            f"site-file-sha256:{publication_audit.short_hash(path)}", text
        )
        if findings:
            raise SiteBuildError(f"SITE_{findings[0].rule_id}")
        if GIT_HOST.search(text):
            raise SiteBuildError("SITE_GIT_HOST_FORBIDDEN")
        parser = _HTMLPolicyParser(path)
        try:
            parser.feed(text)
            parser.close()
        except SiteBuildError:
            raise
        except Exception as error:
            raise SiteBuildError("SITE_HTML_PARSE_FAILED") from error
        if parser.declarations != 1:
            raise SiteBuildError("SITE_HTML_DOCTYPE_INVALID")
        for required in ("html", "head", "title", "body", "main"):
            if parser.element_counts.get(required) != 1:
                raise SiteBuildError("SITE_HTML_STRUCTURE_INVALID")
        if len(parser.csp_values) != 1 or any(
            part not in parser.csp_values[0] for part in expected_csp_parts
        ):
            raise SiteBuildError("SITE_CSP_INVALID")
        if parser.referrer_values != ["no-referrer"]:
            raise SiteBuildError("SITE_REFERRER_POLICY_INVALID")
        if len(parser.stylesheets) != 1:
            raise SiteBuildError("SITE_STYLESHEET_LINK_INVALID")
        stylesheet = _normalize_site_path(path, parser.stylesheets[0])
        if stylesheet != SITE_CSS_PATH:
            raise SiteBuildError("SITE_STYLESHEET_LINK_INVALID")
        for image in parser.images:
            parsed_image = urlsplit(image["src"])
            if parsed_image.scheme or parsed_image.netloc or parsed_image.query or parsed_image.fragment:
                raise SiteBuildError("SITE_REMOTE_IMAGE_FORBIDDEN")
            target_image = _normalize_site_path(path, parsed_image.path)
            if not publication_assets.is_asset_path(target_image) or target_image not in files:
                raise SiteBuildError("SITE_IMAGE_MISSING")
        page_ids[path] = parser.ids
        page_links[path] = parser.links

    for current, links in page_links.items():
        for href, attributes in links:
            try:
                parsed = urlsplit(href)
            except ValueError as error:
                raise SiteBuildError("SITE_LINK_URL_INVALID") from error
            if parsed.scheme or parsed.netloc:
                try:
                    local_result = publication_export.resolved_local_target(
                        "README.md", href
                    )
                except publication_export.PublicationExportError as error:
                    raise SiteBuildError("SITE_EXTERNAL_LINK_FORBIDDEN") from error
                if local_result is not None:
                    raise SiteBuildError("SITE_EXTERNAL_LINK_FORBIDDEN")
                if attributes.get("rel") != "external noopener noreferrer":
                    raise SiteBuildError("SITE_EXTERNAL_LINK_REL_INVALID")
                if attributes.get("referrerpolicy") != "no-referrer":
                    raise SiteBuildError("SITE_EXTERNAL_LINK_REFERRER_INVALID")
                continue
            if parsed.query:
                raise SiteBuildError("SITE_LOCAL_LINK_QUERY_FORBIDDEN")
            target = (
                current
                if not parsed.path
                else _normalize_site_path(current, parsed.path)
            )
            if target not in html_paths:
                if publication_assets.is_asset_path(target) and target in files and not parsed.fragment:
                    continue
                raise SiteBuildError("SITE_LOCAL_LINK_MISSING")
            fragment = unquote(parsed.fragment)
            if fragment and fragment not in page_ids[target]:
                raise SiteBuildError("SITE_LINK_FRAGMENT_MISSING")


def _expected_directories(file_paths: set[str]) -> set[str]:
    directories: set[str] = set()
    for path in file_paths:
        parent = PurePosixPath(path).parent
        while parent.as_posix() != ".":
            directories.add(parent.as_posix())
            parent = parent.parent
    return directories


def _enumerate_site(root: Path) -> tuple[set[str], set[str]]:
    try:
        root_details = root.lstat()
    except OSError as error:
        raise SiteBuildError("SITE_INPUT_INVALID") from error
    if not stat.S_ISDIR(root_details.st_mode) or root.is_symlink():
        raise SiteBuildError("SITE_INPUT_INVALID")
    files: set[str] = set()
    directories: set[str] = set()
    pending = [root]
    entries = 0
    while pending:
        directory = pending.pop()
        try:
            with os.scandir(directory) as iterator:
                for child in iterator:
                    entries += 1
                    if entries > MAX_SITE_ENTRIES:
                        raise SiteBuildError("SITE_ENTRY_LIMIT_EXCEEDED")
                    try:
                        details = child.stat(follow_symlinks=False)
                    except OSError as error:
                        raise SiteBuildError("SITE_ENTRY_STAT_FAILED") from error
                    relative = Path(child.path).relative_to(root).as_posix()
                    if child.is_symlink():
                        raise SiteBuildError("SITE_SYMLINK_FORBIDDEN")
                    if stat.S_ISDIR(details.st_mode):
                        directories.add(relative)
                        pending.append(Path(child.path))
                    elif stat.S_ISREG(details.st_mode):
                        if details.st_nlink != 1:
                            raise SiteBuildError("SITE_HARDLINK_FORBIDDEN")
                        files.add(relative)
                    else:
                        raise SiteBuildError("SITE_SPECIAL_FILE_FORBIDDEN")
        except OSError as error:
            raise SiteBuildError("SITE_DIRECTORY_READ_FAILED") from error
    return files, directories


DirectoryIdentity = tuple[int, int, int, int, int, int]


def _site_directory_identity(root: Path, error_code: str) -> DirectoryIdentity:
    try:
        details = root.lstat()
    except OSError as error:
        raise SiteBuildError(error_code) from error
    if stat.S_ISLNK(details.st_mode) or not stat.S_ISDIR(details.st_mode):
        raise SiteBuildError(error_code)
    return (
        details.st_dev,
        details.st_ino,
        details.st_nlink,
        details.st_mode,
        details.st_mtime_ns,
        details.st_ctime_ns,
    )


def _site_directory_identities(
    root: Path, directory_paths: set[str], error_code: str
) -> dict[str, DirectoryIdentity]:
    identities = {"": _site_directory_identity(root, error_code)}
    for path in sorted(directory_paths):
        identities[path] = _site_directory_identity(root / path, error_code)
    return identities


def _assert_site_root_unchanged(
    root: Path, expected_identity: DirectoryIdentity
) -> None:
    if (
        _site_directory_identity(root, "SITE_ROOT_CHANGED_DURING_VERIFICATION")
        != expected_identity
    ):
        raise SiteBuildError("SITE_ROOT_CHANGED_DURING_VERIFICATION")


def _validate_metadata(path: Path, *, directory: bool) -> None:
    try:
        details = path.lstat()
    except OSError as error:
        raise SiteBuildError("SITE_ENTRY_STAT_FAILED") from error
    expected_mode = 0o755 if directory else 0o644
    if stat.S_IMODE(details.st_mode) != expected_mode:
        raise SiteBuildError("SITE_MODE_INVALID")
    if details.st_mtime_ns != publication_export.SOURCE_DATE_EPOCH_NS:
        raise SiteBuildError("SITE_MTIME_INVALID")


def _read_site_file(root: Path, relative: str) -> bytes:
    path = root / relative
    descriptor: int | None = None
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
            raise SiteBuildError("SITE_FILE_TYPE_INVALID")
        if before.st_size > MAX_SITE_FILE_BYTES:
            raise SiteBuildError("SITE_FILE_TOO_LARGE")
        chunks: list[bytes] = []
        remaining = before.st_size
        while remaining:
            chunk = os.read(descriptor, min(remaining, 1024 * 1024))
            if not chunk:
                raise SiteBuildError("SITE_FILE_CHANGED_DURING_READ")
            chunks.append(chunk)
            remaining -= len(chunk)
        if os.read(descriptor, 1):
            raise SiteBuildError("SITE_FILE_CHANGED_DURING_READ")
        after = os.fstat(descriptor)
        if (
            before.st_dev,
            before.st_ino,
            before.st_mode,
            before.st_size,
            before.st_mtime_ns,
        ) != (
            after.st_dev,
            after.st_ino,
            after.st_mode,
            after.st_size,
            after.st_mtime_ns,
        ):
            raise SiteBuildError("SITE_FILE_CHANGED_DURING_READ")
        return b"".join(chunks)
    except SiteBuildError:
        raise
    except OSError as error:
        raise SiteBuildError("SITE_FILE_READ_FAILED") from error
    finally:
        if descriptor is not None:
            os.close(descriptor)


def _verify_site_files(
    expected: dict[str, bytes], page_count: int, input_dir: Path
) -> SiteReport:
    root_identity = _site_directory_identity(input_dir, "SITE_INPUT_INVALID")
    actual_files, actual_directories = _enumerate_site(input_dir)
    _assert_site_root_unchanged(input_dir, root_identity)
    expected_paths = set(expected)
    if actual_files != expected_paths:
        raise SiteBuildError("SITE_FILE_SET_MISMATCH")
    expected_directories = _expected_directories(expected_paths)
    if actual_directories != expected_directories:
        raise SiteBuildError("SITE_DIRECTORY_SET_MISMATCH")
    _validate_metadata(input_dir, directory=True)
    for directory in expected_directories:
        _validate_metadata(input_dir / directory, directory=True)
    directory_identities = _site_directory_identities(
        input_dir,
        expected_directories,
        "SITE_DIRECTORY_CHANGED_DURING_VERIFICATION",
    )
    total_bytes = 0
    actual: dict[str, bytes] = {}
    for path in sorted(expected_paths):
        _validate_metadata(input_dir / path, directory=False)
        data = _read_site_file(input_dir, path)
        total_bytes += len(data)
        if total_bytes > MAX_SITE_TOTAL_BYTES:
            raise SiteBuildError("SITE_TOTAL_TOO_LARGE")
        if data != expected[path]:
            raise SiteBuildError("SITE_FILE_CONTENT_MISMATCH")
        actual[path] = data
    _validate_generated_site(actual)
    _assert_site_root_unchanged(input_dir, root_identity)
    final_files, final_directories = _enumerate_site(input_dir)
    _assert_site_root_unchanged(input_dir, root_identity)
    if final_files != actual_files:
        raise SiteBuildError("SITE_FILE_SET_MISMATCH")
    if final_directories != actual_directories:
        raise SiteBuildError("SITE_DIRECTORY_SET_MISMATCH")
    if (
        _site_directory_identities(
            input_dir,
            expected_directories,
            "SITE_DIRECTORY_CHANGED_DURING_VERIFICATION",
        )
        != directory_identities
    ):
        raise SiteBuildError("SITE_DIRECTORY_CHANGED_DURING_VERIFICATION")
    _assert_site_root_unchanged(input_dir, root_identity)
    return SiteReport(
        page_count=page_count,
        file_count=len(actual),
        total_bytes=total_bytes,
        site_set_sha256=_site_digest(actual),
    )


def _verify_site(
    snapshot_dir: Path, expected_content_set_sha256: str, input_dir: Path
) -> SiteReport:
    expected, page_count = _load_expected_site(
        snapshot_dir, expected_content_set_sha256
    )
    return _verify_site_files(expected, page_count, input_dir)


def verify_site(
    snapshot_dir: Path, expected_content_set_sha256: str, input_dir: Path
) -> SiteReport:
    """Verify a quiescent site directory; callers must exclude concurrent writers."""

    if os.name != "posix":
        raise SiteBuildError("SITE_PLATFORM_UNSUPPORTED")
    try:
        return _verify_site(snapshot_dir, expected_content_set_sha256, input_dir)
    except SiteBuildError:
        raise
    except OSError as error:
        raise SiteBuildError("SITE_IO_FAILED") from error


def _write_site_file(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(data)
    path.chmod(0o644)
    os.utime(
        path,
        (publication_export.SOURCE_DATE_EPOCH, publication_export.SOURCE_DATE_EPOCH),
    )


def _fix_site_directory_metadata(root: Path) -> None:
    directories = [root]
    directories.extend(path for path in root.rglob("*") if path.is_dir())
    for directory in sorted(
        directories, key=lambda item: len(item.parts), reverse=True
    ):
        directory.chmod(0o755)
        os.utime(
            directory,
            (
                publication_export.SOURCE_DATE_EPOCH,
                publication_export.SOURCE_DATE_EPOCH,
            ),
        )


def _assert_output_location(snapshot_dir: Path, output_dir: Path) -> None:
    if output_dir.exists() or output_dir.is_symlink():
        raise SiteBuildError("SITE_OUTPUT_ALREADY_EXISTS")
    if (
        not output_dir.name
        or output_dir.name.casefold() == ".git"
        or CONTROL.search(output_dir.name)
    ):
        raise SiteBuildError("SITE_OUTPUT_NAME_INVALID")
    parent = output_dir.parent
    if not parent.exists() or not parent.is_dir() or parent.is_symlink():
        raise SiteBuildError("SITE_OUTPUT_PARENT_INVALID")
    resolved_snapshot = snapshot_dir.resolve()
    resolved_output = output_dir.resolve(strict=False)
    try:
        resolved_output.relative_to(resolved_snapshot)
    except ValueError:
        return
    raise SiteBuildError("SITE_OUTPUT_INSIDE_SNAPSHOT")


def build_site(
    snapshot_dir: Path, expected_content_set_sha256: str, output_dir: Path
) -> SiteReport:
    if os.name != "posix":
        raise SiteBuildError("SITE_PLATFORM_UNSUPPORTED")
    created = False
    try:
        _assert_output_location(snapshot_dir, output_dir)
        expected, page_count = _load_expected_site(
            snapshot_dir, expected_content_set_sha256
        )
        output_dir.mkdir(mode=0o700)
        created = True
        for path, data in sorted(expected.items()):
            _write_site_file(output_dir / path, data)
        _fix_site_directory_metadata(output_dir)
        return _verify_site_files(expected, page_count, output_dir)
    except SiteBuildError:
        if created:
            try:
                shutil.rmtree(output_dir)
            except OSError as cleanup_error:
                raise SiteBuildError("SITE_OUTPUT_CLEANUP_FAILED") from cleanup_error
        raise
    except OSError as error:
        if created:
            try:
                shutil.rmtree(output_dir)
            except OSError as cleanup_error:
                raise SiteBuildError("SITE_OUTPUT_CLEANUP_FAILED") from cleanup_error
        raise SiteBuildError("SITE_OUTPUT_IO_FAILED") from error


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build or verify the Project Covenant static reading site."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    build_parser = subparsers.add_parser(
        "build", help="Build a deterministic site from a verified snapshot."
    )
    build_parser.add_argument("--snapshot", required=True, type=Path)
    build_parser.add_argument("--expected-content-set-sha256", required=True)
    build_parser.add_argument("--output", required=True, type=Path)
    verify_parser = subparsers.add_parser(
        "verify", help="Verify a site against a trusted source snapshot."
    )
    verify_parser.add_argument("--snapshot", required=True, type=Path)
    verify_parser.add_argument("--expected-content-set-sha256", required=True)
    verify_parser.add_argument("--input", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        if args.command == "build":
            report = build_site(
                args.snapshot, args.expected_content_set_sha256, args.output
            )
            action = "build"
        elif args.command == "verify":
            report = verify_site(
                args.snapshot, args.expected_content_set_sha256, args.input
            )
            action = "verify"
        else:
            raise SiteBuildError("SITE_COMMAND_UNSUPPORTED")
    except SiteBuildError as error:
        print(f"error_code={error.code}")
        print(f"site_{args.command}=FAIL")
        return 1
    except Exception:
        print("error_code=INTERNAL_ERROR")
        print(f"site_{args.command}=FAIL")
        return 1
    print(f"site_pages={report.page_count}")
    print(f"site_files={report.file_count}")
    print(f"site_bytes={report.total_bytes}")
    print(f"site_set_sha256={report.site_set_sha256}")
    print(f"site_{action}=PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
