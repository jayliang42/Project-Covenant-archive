#!/usr/bin/env python3
"""Audit public content, site scope, and optional Git-history privacy risks."""

from __future__ import annotations

import argparse
import hashlib
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlsplit

if __package__:
    from . import publication_assets
else:
    import publication_assets


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "publication" / "site-content.txt"
INLINE_LINK = re.compile(r"!?\[[^\]]*\]\(([^)\n]+)\)")
REFERENCE_LINK = re.compile(r"^\s*\[[^\]]+\]:\s*(<[^>]+>|\S+)")
HTML_LINK = re.compile(r"(?i)(?:href|src)\s*=\s*[\"']([^\"']+)[\"']")
RAW_SITE_RESOURCE = re.compile(
    r"(?is)<(?:script|iframe|form|input|style)\b|"
    r"<(?:a|img|link|video|audio|source)\b[^>]*\b"
    r"(?:href|src|srcset|style)\s*=|\bstyle\s*=|\burl\s*\("
)
CHINESE_ID_CANDIDATE = re.compile(r"(?<!\d)[1-9]\d{16}[\dXx](?!\d)")
FORBIDDEN_SITE_PREFIXES = (
    ".git/",
    ".github/",
    "Teaching_Memo/",
    "Bible_Translations/Private_Downloads/",
    "attachments/private/",
    "drafts/private/",
    "private/",
    "scripts/",
    "tests/",
)


@dataclass(frozen=True)
class Finding:
    rule_id: str
    location: str
    line: int


def _private_key_pattern() -> re.Pattern[str]:
    marker = "-----" + "BEGIN "
    return re.compile(re.escape(marker) + r"(?:RSA |EC |OPENSSH )?PRIVATE KEY-----")


def _github_token_pattern() -> re.Pattern[str]:
    prefix = "gh" + "p_"
    modern_prefix = "github" + "_pat_"
    return re.compile(
        rf"\b(?:{re.escape(prefix)}[A-Za-z0-9]{{30,}}|"
        rf"{re.escape(modern_prefix)}[A-Za-z0-9_]{{20,}})\b"
    )


def _aws_key_pattern() -> re.Pattern[str]:
    prefix = "AK" + "IA"
    return re.compile(rf"\b{prefix}[0-9A-Z]{{16}}\b")


def _api_token_pattern() -> re.Pattern[str]:
    generic_prefix = "sk" + "-"
    project_prefix = "sk" + "-proj-"
    return re.compile(
        rf"\b(?:{re.escape(project_prefix)}[A-Za-z0-9_-]{{20,}}|"
        rf"{re.escape(generic_prefix)}[A-Za-z0-9]{{20,}})\b"
    )


def _home_path_pattern() -> re.Pattern[str]:
    mac_prefix = "/" + "Users/"
    linux_prefix = "/" + "home/"
    windows_prefix = "C:" + r"\\Users\\"
    return re.compile(
        rf"(?:{re.escape(mac_prefix)}[^/\s]+/|"
        rf"{re.escape(linux_prefix)}[^/\s]+/|"
        rf"{re.escape(windows_prefix)}[^\\\s]+\\)",
        re.IGNORECASE,
    )


def _social_profile_pattern() -> re.Pattern[str]:
    return re.compile(
        r"(?i)https?://(?:www\.)?(?:"
        r"linkedin\.com/in/[^/\s)]+|"
        r"instagram\.com/[^/\s)]+|"
        r"facebook\.com/[^/\s)]+|"
        r"(?:x|twitter)\.com/[^/\s)]+|"
        r"github\.com/[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})/?"
        r"(?:\?[^\s)]*)?(?=$|[\s)#]))"
    )


def _plain_social_handle_pattern() -> re.Pattern[str]:
    context = r"(?:contact|follow|username|handle|social|联系|账号|用户名|社交媒体)"
    handle = r"@[A-Za-z0-9_][A-Za-z0-9_.-]{2,}"
    return re.compile(
        rf"(?i)(?:{context}.{{0,40}}{handle}|{handle}.{{0,40}}{context})"
    )


def _personal_immigration_en_pattern() -> re.Pattern[str]:
    subjects = r"\b(?:" + "|".join(("I", "my", "me")) + r")\b"
    form_number = "I" + r"[- ]?589"
    topics = r"\b(?:" + "|".join(
        ("asylum", "immigration case", "refugee status", form_number, "USCIS", "EOIR")
    ) + r")\b"
    return re.compile(
        rf"(?i)(?:{subjects}.{{0,100}}{topics}|{topics}.{{0,100}}{subjects})"
    )


def _personal_immigration_zh_pattern() -> re.Pattern[str]:
    subjects = "(?:" + "|".join(("本人", "我的", "我(?!们)")) + ")"
    topics = "(?:" + "|".join(
        ("政治庇护", "庇护申请", "移民案件", "难民身份", "移民法庭")
    ) + ")"
    return re.compile(rf"(?:{subjects}.{{0,80}}{topics}|{topics}.{{0,80}}{subjects})")


def _personal_health_en_pattern() -> re.Pattern[str]:
    actions = r"\bI\s+(?:" + "|".join(
        ("have", "had", "was diagnosed with", "received treatment for", "survived", "attempted")
    ) + r")\b"
    topics = r"\b(?:" + "|".join(
        (
            "depression",
            "anxiety disorder",
            "eating disorder",
            r"suicid(?:e|al)",
            "self-harm",
            "trauma",
            "cancer",
            "disability",
        )
    ) + r")\b"
    return re.compile(rf"(?i){actions}.{{0,100}}{topics}")


def _personal_health_zh_pattern() -> re.Pattern[str]:
    actions = "我(?:" + "|".join(
        ("曾", "被诊断为", "患有", r"接受过.{0,20}治疗", "有过")
    ) + ")"
    topics = "(?:" + "|".join(
        ("抑郁", "焦虑症", "饮食失调", "自杀", "自伤", "创伤", "癌症", "残疾")
    ) + ")"
    return re.compile(rf"{actions}.{{0,80}}{topics}")


CONTENT_RULES: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("SECRET_PRIVATE_KEY", _private_key_pattern()),
    ("SECRET_GITHUB_TOKEN", _github_token_pattern()),
    ("SECRET_AWS_ACCESS_KEY", _aws_key_pattern()),
    ("SECRET_API_TOKEN", _api_token_pattern()),
    (
        "DIRECT_EMAIL_ADDRESS",
        re.compile(
            r"(?i)(?<![\w.+-])[\w.+-]+@[\w.-]+\.[a-z]{2,}(?![\w.-])"
        ),
    ),
    (
        "DIRECT_PHONE_NUMBER",
        re.compile(
            r"(?<!\d)(?:\+?1[ .-])?(?:\(\d{3}\)|\d{3})[ .-]"
            r"\d{3}[ .-]\d{4}(?!\d)"
        ),
    ),
    (
        "CHINESE_MOBILE_NUMBER",
        re.compile(
            r"(?<!\d)(?:\+?86[ .-]?)?"
            r"(?:1[3-9]\d{9}|1[3-9]\d[ .-]\d{4}[ .-]\d{4})(?!\d)"
        ),
    ),
    (
        "INTERNATIONAL_PHONE_NUMBER",
        re.compile(r"(?<!\w)\+\d{1,3}(?:[ .-]?\d){7,14}(?!\d)"),
    ),
    (
        "US_SOCIAL_SECURITY_NUMBER",
        re.compile(r"(?<!\d)\d{3}-\d{2}-\d{4}(?!\d)"),
    ),
    ("LOCAL_HOME_PATH", _home_path_pattern()),
    ("PRIVATE_SOCIAL_PROFILE", _social_profile_pattern()),
    (
        "PLAIN_SOCIAL_HANDLE",
        _plain_social_handle_pattern(),
    ),
    (
        "PRIVATE_CONTACT_HANDLE",
        re.compile(
            r"(?i)(?:\b(?:wechat|telegram|whatsapp|signal)\b\s*[:：]\s*|"
            r"(?:微信号?|QQ号?|手机号|联系电话|联系方式)"
            r"(?:\s*[:：]\s*|\s+))[A-Za-z0-9_+.-]{5,}"
        ),
    ),
    (
        "CHINESE_LABELED_LANDLINE",
        re.compile(
            r"(?:电话|座机|联系电话)\s*[:：]?\s*"
            r"(?:\+?86[ .-]?)?(?:0\d{2,3}[ .-]?)?\d{7,8}"
        ),
    ),
    (
        "PRIVATE_STREET_ADDRESS",
        re.compile(
            r"(?i)(?<!\d)\d{1,6}\s+(?:[A-Z][\w.'-]*\s+){1,5}"
            r"(?:street|st\.?|road|rd\.?|avenue|ave\.?|lane|ln\.?|"
            r"drive|dr\.?|boulevard|blvd\.?|court|ct\.?)\b"
        ),
    ),
    (
        "PRIVATE_ADDRESS_LABEL",
        re.compile(
            r"(?i)(?:home address|street address|住址|家庭地址|家庭住址|"
            r"联系地址|现居地址)"
            r"\s*[:：]\s*[A-Za-z0-9\u4e00-\u9fff]\S*"
        ),
    ),
    (
        "PRIVATE_MEETING_INVITE",
        re.compile(
            r"(?i)https?://(?:[\w.-]+\.)?(?:zoom\.us/(?:j|my)/|"
            r"meet\.google\.com/|teams\.microsoft\.com/l/meetup-join/|"
            r"[^/]*webex\.com/[^\s)]+/j\.php)"
        ),
    ),
    (
        "PERSONAL_PROFILE_LABEL",
        re.compile(
            r"(?im)^(?:maintainer|repository owner|contact person|"
            r"维护者|仓库所有者|联系人)\s*[:：]\s*\S+"
        ),
    ),
    (
        "AUTOBIOGRAPHICAL_HEADING",
        re.compile(
            r"(?im)^#{1,6}\s+(?:about me|my (?:story|testimony|journey|experience)|"
            r"个人(?:简介|经历)|我的(?:故事|见证|经历)|作者自述)\s*$"
        ),
    ),
    (
        "AUTOBIOGRAPHICAL_STATEMENT_EN",
        re.compile(
            r"(?i)\bI\s+(?:am from|live(?:d)? in|moved to|work(?:ed)? (?:at|for|in)|"
            r"studied at|graduated from|attend(?:ed)? (?:a|the|this) church|"
            r"joined (?:a|the|this) church|was baptized|converted|"
            r"became a Christian|accepted Jesus|came to faith|"
            r"put my faith in Jesus)\b"
        ),
    ),
    (
        "AUTOBIOGRAPHICAL_STATEMENT_ZH",
        re.compile(
            r"我(?:来自|住在|曾住在|搬到|任职于|工作于|毕业于|就读于|"
            r"参加了.{0,20}(?:教会|聚会|团契|门训)|加入了.{0,20}教会|"
            r"受洗于|信主于)|我\d{4}年(?:开始)?信主|"
            r"我(?:在|于).{0,20}(?:信主|受洗|决志|归信)|"
            r"我(?:开始信主|信了主|成为基督徒|接受了?耶稣|归信|受洗)"
        ),
    ),
    (
        "PERSONAL_IMMIGRATION_OR_ASYLUM_EN",
        _personal_immigration_en_pattern(),
    ),
    (
        "PERSONAL_IMMIGRATION_OR_ASYLUM_ZH",
        _personal_immigration_zh_pattern(),
    ),
    (
        "PERSONAL_HEALTH_HISTORY_EN",
        _personal_health_en_pattern(),
    ),
    (
        "PERSONAL_HEALTH_HISTORY_ZH",
        _personal_health_zh_pattern(),
    ),
)


def git_paths() -> list[Path]:
    result = subprocess.run(
        [
            "git",
            "ls-files",
            "-z",
            "--cached",
            "--others",
            "--exclude-standard",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    return sorted(
        (Path(item) for item in result.stdout.decode("utf-8").split("\0") if item),
        key=lambda path: path.as_posix(),
    )


def scan_text(location: str, text: str) -> list[Finding]:
    findings: list[Finding] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        for rule_id, pattern in CONTENT_RULES:
            if pattern.search(line):
                findings.append(Finding(rule_id, location, line_number))
        for match in CHINESE_ID_CANDIDATE.finditer(line):
            if valid_chinese_resident_id(match.group(0)):
                findings.append(
                    Finding("CHINESE_RESIDENT_ID_NUMBER", location, line_number)
                )
    return findings


def valid_chinese_resident_id(value: str) -> bool:
    if len(value) != 18 or not value[:17].isdigit():
        return False
    try:
        date.fromisoformat(f"{value[6:10]}-{value[10:12]}-{value[12:14]}")
    except ValueError:
        return False
    weights = (7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2)
    check_codes = "10X98765432"
    checksum = sum(int(digit) * weight for digit, weight in zip(value[:17], weights))
    return value[-1].upper() == check_codes[checksum % 11]


def read_text(path: Path) -> str | None:
    try:
        raw = path.read_bytes()
    except OSError:
        return None
    if b"\0" in raw:
        return None
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return None


def scan_worktree(paths: list[Path]) -> tuple[int, list[Finding]]:
    scanned = 0
    findings: list[Finding] = []
    for relative in paths:
        relative_text = relative.as_posix()
        findings.extend(
            scan_text(f"path-sha256:{short_hash(relative_text)}", relative_text)
        )
        absolute = ROOT / relative
        if absolute.is_symlink():
            findings.append(
                Finding(
                    "WORKTREE_SYMLINK_UNREVIEWED",
                    f"path-sha256:{short_hash(relative_text)}",
                    0,
                )
            )
            continue
        if publication_assets.is_asset_path(relative_text):
            try:
                data = absolute.read_bytes()
                publication_assets.validate_asset(relative_text, data)
            except (OSError, publication_assets.AssetError):
                findings.append(Finding("WORKTREE_ASSET_INVALID", relative_text, 0))
                continue
            scanned += 1
            if relative_text.endswith(".svg"):
                findings.extend(scan_text(relative_text, data.decode("utf-8")))
            continue
        text = read_text(absolute)
        if text is None:
            findings.append(
                Finding(
                    "WORKTREE_BINARY_OR_NON_UTF8_UNREVIEWED",
                    f"path-sha256:{short_hash(relative_text)}",
                    0,
                )
            )
            continue
        scanned += 1
        findings.extend(scan_text(relative_text, text))
    return scanned, findings


def normalize_manifest_entry(raw_entry: str) -> str | None:
    entry = raw_entry.strip()
    if not entry or entry.startswith("#"):
        return None
    pure = PurePosixPath(entry)
    if pure.is_absolute() or ".." in pure.parts or entry != pure.as_posix():
        raise ValueError(f"unsafe manifest path: {entry}")
    return entry


def load_manifest(path: Path) -> tuple[list[str], list[Finding]]:
    findings: list[Finding] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return [], [Finding("MANIFEST_MISSING", path.relative_to(ROOT).as_posix(), 0)]

    entries: list[str] = []
    seen: set[str] = set()
    for line_number, raw_entry in enumerate(lines, start=1):
        try:
            entry = normalize_manifest_entry(raw_entry)
        except ValueError:
            findings.append(
                Finding("MANIFEST_UNSAFE_PATH", path.relative_to(ROOT).as_posix(), line_number)
            )
            continue
        if entry is None:
            continue
        if entry in seen:
            findings.append(
                Finding("MANIFEST_DUPLICATE", path.relative_to(ROOT).as_posix(), line_number)
            )
            continue
        seen.add(entry)
        entries.append(entry)
    return entries, findings


def markdown_target(current: Path, raw_target: str) -> Path | None:
    target = raw_target.strip()
    if target.startswith("<") and ">" in target:
        target = target[1 : target.index(">")]
    else:
        target = target.split(maxsplit=1)[0]
    parsed = urlsplit(target)
    if parsed.scheme or parsed.netloc or not parsed.path:
        return None
    decoded = unquote(parsed.path)
    return (current.parent / decoded).resolve()


def local_targets(line: str) -> list[str]:
    targets = INLINE_LINK.findall(line)
    targets.extend(REFERENCE_LINK.findall(line))
    targets.extend(HTML_LINK.findall(line))
    return list(dict.fromkeys(targets))


def audit_manifest(
    manifest_path: Path,
    entries: list[str],
    available_paths: set[str],
) -> list[Finding]:
    findings: list[Finding] = []
    allowed = set(entries)
    manifest_label = manifest_path.relative_to(ROOT).as_posix()
    for entry in entries:
        path = ROOT / entry
        if any(
            entry == prefix.rstrip("/") or entry.startswith(prefix)
            for prefix in FORBIDDEN_SITE_PREFIXES
        ):
            findings.append(Finding("SITE_FORBIDDEN_PATH", manifest_label, 0))
            continue
        if Path(entry).suffix.lower() != ".md" and entry != manifest_label and not publication_assets.is_asset_path(entry):
            findings.append(Finding("SITE_NON_MARKDOWN_INPUT", manifest_label, 0))
        if entry not in available_paths or not path.is_file():
            findings.append(Finding("SITE_FILE_MISSING", entry, 0))
            continue
        if path.is_symlink():
            findings.append(Finding("SITE_SYMLINK_FORBIDDEN", entry, 0))
            continue
        try:
            path.resolve().relative_to(ROOT)
        except ValueError:
            findings.append(Finding("SITE_PATH_ESCAPES_REPOSITORY", entry, 0))
            continue

        if publication_assets.is_asset_path(entry):
            try:
                publication_assets.validate_asset(entry, path.read_bytes())
            except (OSError, publication_assets.AssetError):
                findings.append(Finding("SITE_ASSET_INVALID", entry, 0))
            if "CREDITS.md" not in allowed:
                findings.append(Finding("SITE_ASSET_CREDITS_REQUIRED", entry, 0))
            continue
        text = read_text(path)
        if text is None:
            findings.append(Finding("SITE_INPUT_NOT_UTF8_TEXT", entry, 0))
            continue
        for match in RAW_SITE_RESOURCE.finditer(text):
            line_number = text.count("\n", 0, match.start()) + 1
            findings.append(Finding("SITE_RAW_RESOURCE_FORBIDDEN", entry, line_number))
        for line_number, line in enumerate(text.splitlines(), start=1):
            for raw_target in local_targets(line):
                target = markdown_target(path, raw_target)
                if target is None:
                    continue
                try:
                    target_relative = target.relative_to(ROOT).as_posix()
                except ValueError:
                    findings.append(Finding("SITE_LINK_ESCAPES_REPOSITORY", entry, line_number))
                    continue
                if target_relative not in allowed:
                    findings.append(Finding("SITE_LINK_OUTSIDE_ALLOWLIST", entry, line_number))
    return findings


def short_hash(value: str) -> str:
    return hashlib.sha256(value.casefold().encode("utf-8")).hexdigest()[:12]


def history_findings(
    approved_remote_owner: str | None = None,
) -> tuple[int, list[Finding], list[Finding]]:
    commits_result = subprocess.run(
        ["git", "rev-list", "--all"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    commits = [line for line in commits_result.stdout.splitlines() if line]
    blobs: dict[str, set[str]] = {}
    for commit in commits:
        tree = subprocess.run(
            ["git", "ls-tree", "-r", "-z", "--full-tree", commit],
            cwd=ROOT,
            check=True,
            capture_output=True,
        ).stdout
        for record in tree.split(b"\0"):
            if not record or b"\t" not in record:
                continue
            metadata, raw_path = record.split(b"\t", 1)
            fields = metadata.split()
            if len(fields) == 3 and fields[1] == b"blob":
                object_id = fields[2].decode("ascii")
                path = raw_path.decode("utf-8", "replace")
                blobs.setdefault(object_id, set()).add(path)

    content_findings: list[Finding] = []
    scanned_blobs = 0
    for object_id, paths in sorted(
        blobs.items(), key=lambda item: (min(item[1]), item[0])
    ):
        for path in sorted(paths):
            content_findings.extend(
                scan_text(f"history-path-sha256:{short_hash(path)}", path)
            )
        raw = subprocess.run(
            ["git", "cat-file", "blob", object_id],
            cwd=ROOT,
            check=True,
            capture_output=True,
        ).stdout
        asset_paths = [path for path in paths if publication_assets.is_asset_path(path)]
        if len(asset_paths) == len(paths):
            try:
                for path in asset_paths:
                    publication_assets.validate_asset(path, raw)
            except publication_assets.AssetError:
                content_findings.append(Finding("HISTORICAL_ASSET_INVALID", f"history-blob:{object_id[:12]}", 0))
                continue
            scanned_blobs += 1
            if asset_paths[0].endswith(".svg"):
                content_findings.extend(scan_text(f"history-blob:{object_id[:12]}", raw.decode("utf-8")))
            continue
        if b"\0" in raw:
            content_findings.append(
                Finding(
                    "HISTORICAL_BINARY_OR_NON_UTF8_UNREVIEWED",
                    f"history-blob:{object_id[:12]}",
                    0,
                )
            )
            continue
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            content_findings.append(
                Finding(
                    "HISTORICAL_BINARY_OR_NON_UTF8_UNREVIEWED",
                    f"history-blob:{object_id[:12]}",
                    0,
                )
            )
            continue
        scanned_blobs += 1
        label = f"history-blob:{object_id[:12]}"
        content_findings.extend(scan_text(label, text))

    for commit in commits:
        message = subprocess.run(
            ["git", "show", "-s", "--format=%B", commit],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        content_findings.extend(
            scan_text(f"history-commit-message:{commit[:12]}", message)
        )

    log = subprocess.run(
        ["git", "log", "--all", "--format=%an%x1f%ae%x1f%cn%x1f%ce%x1e"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    names: set[str] = set()
    emails: set[str] = set()
    for raw_record in log.split("\x1e"):
        fields = [field.strip() for field in raw_record.strip().split("\x1f")]
        if len(fields) != 4:
            continue
        names.update(value for value in (fields[0], fields[2]) if value)
        emails.update(value for value in (fields[1], fields[3]) if value)

    tags = subprocess.run(
        ["git", "tag", "--list"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    for tag_name in tags:
        content_findings.extend(
            scan_text(f"history-tag-name-sha256:{short_hash(tag_name)}", tag_name)
        )
        tag_type = subprocess.run(
            ["git", "cat-file", "-t", f"refs/tags/{tag_name}"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        if tag_type != "tag":
            continue
        tag_object = subprocess.run(
            ["git", "cat-file", "-p", f"refs/tags/{tag_name}"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        header, _, message = tag_object.partition("\n\n")
        content_findings.extend(
            scan_text(f"history-tag-message-sha256:{short_hash(tag_name)}", message)
        )
        for line in header.splitlines():
            if not line.startswith("tagger "):
                continue
            match = re.match(r"tagger (.+) <([^>]+)> ", line)
            if match:
                names.add(match.group(1))
                emails.add(match.group(2))

    safe_names = {"Project Covenant Maintainer", "Project Covenant Automation", "GitHub"}
    metadata_findings = [
        Finding("GIT_IDENTITY_NAME", f"git-name-sha256:{short_hash(name)}", 0)
        for name in sorted(names, key=str.casefold)
        if name not in safe_names
    ]
    metadata_findings.extend(
        Finding("GIT_IDENTITY_EMAIL", f"git-email-sha256:{short_hash(email)}", 0)
        for email in sorted(emails, key=str.casefold)
        if not email.casefold().endswith(".invalid")
    )
    remote = subprocess.run(
        ["git", "remote", "get-url", "origin"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    ).stdout.strip()
    remote_owner = re.search(r"github\.com(?::|/)([^/]+)/", remote, re.IGNORECASE)
    if remote_owner and (
        approved_remote_owner is None
        or remote_owner.group(1).casefold() != approved_remote_owner.casefold()
    ):
        metadata_findings.append(
            Finding(
                "GIT_REMOTE_OWNER",
                f"git-owner-sha256:{short_hash(remote_owner.group(1))}",
                0,
            )
        )
    return scanned_blobs, content_findings, metadata_findings


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit Project Covenant's public content and publication boundary."
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_MANIFEST,
        help="Exact site-content allowlist (default: publication/site-content.txt).",
    )
    parser.add_argument(
        "--history",
        action="store_true",
        help="Scan reachable historical content and anonymized Git identity metadata.",
    )
    parser.add_argument(
        "--history-content",
        action="store_true",
        help="Scan reachable historical content without enforcing Git identity metadata.",
    )
    parser.add_argument(
        "--approved-remote-owner",
        help="Neutral GitHub owner explicitly approved for a strict --history audit.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest_path = args.manifest
    if not manifest_path.is_absolute():
        manifest_path = (ROOT / manifest_path).resolve()
    try:
        manifest_path.relative_to(ROOT)
    except ValueError:
        print("manifest_findings=1")
        print("FAIL MANIFEST_OUTSIDE_REPOSITORY manifest:0")
        print("publication_audit=FAIL")
        return 1

    paths = git_paths()
    scanned_files, content_findings = scan_worktree(paths)
    entries, manifest_parse_findings = load_manifest(manifest_path)
    manifest_findings = manifest_parse_findings + audit_manifest(
        manifest_path,
        entries,
        {path.as_posix() for path in paths},
    )

    scanned_blobs = 0
    historical_findings: list[Finding] = []
    metadata_findings: list[Finding] = []
    if args.history or args.history_content:
        scanned_blobs, historical_findings, metadata_findings = history_findings(
            args.approved_remote_owner
        )
        if not args.history:
            metadata_findings = []

    all_findings = (
        content_findings + manifest_findings + historical_findings + metadata_findings
    )
    print(f"worktree_text_files_scanned={scanned_files}")
    print(f"site_manifest_files={len(entries)}")
    print(f"worktree_content_findings={len(content_findings)}")
    print(f"manifest_findings={len(manifest_findings)}")
    if args.history or args.history_content:
        print(f"historical_text_blobs_scanned={scanned_blobs}")
        print(f"historical_content_findings={len(historical_findings)}")
    if args.history:
        print(f"git_metadata_findings={len(metadata_findings)}")

    for finding in all_findings[:200]:
        print(f"FAIL {finding.rule_id} {finding.location}:{finding.line}")
    if len(all_findings) > 200:
        print(f"additional_findings_not_listed={len(all_findings) - 200}")

    status = "FAIL" if all_findings else "PASS"
    print(f"publication_audit={status}")
    return 1 if all_findings else 0


if __name__ == "__main__":
    sys.exit(main())
