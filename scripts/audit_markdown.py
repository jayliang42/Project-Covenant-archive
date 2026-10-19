#!/usr/bin/env python3
"""Audit bilingual titles and local Markdown navigation for Project Covenant."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

if __package__:
    from .export_publication import (
        MANIFEST_PATH,
        PublicationExportError,
        parse_manifest,
    )
else:
    from export_publication import (
        MANIFEST_PATH,
        PublicationExportError,
        parse_manifest,
    )


ROOT = Path(__file__).resolve().parents[1]
CHINESE = re.compile(r"[\u4e00-\u9fff]")
LATIN = re.compile(r"[A-Za-z]")
H1 = re.compile(r"^# (.+)$", re.MULTILINE)
HEADING = re.compile(r"^#{1,6} (.+)$", re.MULTILINE)
ANCHOR = re.compile(r'<a\s+id=["\']([^"\']+)["\']\s*></a>', re.IGNORECASE)
LINK = re.compile(r"(?<!!)\[([^\]]+)\]\(([^)\n]+)\)")
LIST_ITEM = re.compile(r"^\s*(?:[-*+] |\d+[.)] )")
CODE_FILE_REFERENCE = re.compile(r"`[^`*\n]+\.(?:md|txt|pdf|json)`", re.IGNORECASE)
INDEX_MARKERS = (
    "README.md",
    "INDEX",
    "总索引",
    "路线图",
    "导航",
    "总表",
    "Cheat_Sheet",
    "Summary",
)
BILINGUAL_BASELINE_PATH = "publication/bilingual-baseline.json"
BILINGUAL_BASELINE_SCHEMA = 1
BILINGUAL_ALGORITHM = "adjacent-latin-v1"
NUMBERED_TABLE_ROW = re.compile(r"^\|\s*(\d+)\s*\|\s*([^|]+?)\s*\|", re.MULTILINE)
NUMBERED_ENTRY_HEADING = re.compile(r"^###\s+(\d+)\.\s+(.+?)\s*$", re.MULTILINE)
EVIDENCE_ANCHOR = re.compile(
    r'^<a id="evidence-(\d{3})"></a>$', re.MULTILINE
)
EVIDENCE_CROSSWALK_LINK = re.compile(
    r"^\|\s*\[(\d+)\]\(\./史料与考古旁证索引\.md#evidence-(\d{3})\)\s*\|",
    re.MULTILINE,
)
H2 = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)
CANONICAL_BOOKS_PATH = "Bible_Timeline/66卷承上启下总表.md"
SELECTED_BOOKS_PATH = "Bible_Timeline/52卷圣经故事主线_精选与14卷桥接版.md"
EVIDENCE_INDEX_PATH = "Bible_Timeline/史料与考古旁证索引.md"
EVIDENCE_CROSSWALK_PATH = "Bible_Timeline/旁证锚点_52周与66卷对应表.md"
PROTECTED_GLOSSARY_NAMES = {
    "福音书", "四福音", "四福音书", "喜乐于三一神", "十二先知", "约书亚诗篇", "大诗篇卷",
    "北美基督之家", "赎罪日", "五旬节运动", "圣殿山", "第一圣殿",
    "第二圣殿", "大先知", "小先知", "智慧书", "大祭司", "祭司长",
    "基督论", "圣灵洗", "新出埃及", "救赎主", "三一神",
    "Gospels", "Delighting in the Trinity", "Psalms of Joshua",
    "Great Psalms Scroll", "Home of Christ", "Day of Atonement",
    "Pentecostal movement", "Temple Mount", "First Temple", "Second Temple",
    "Major Prophets", "Minor Prophets", "Wisdom Books", "High Priest",
    "High Priests", "Chief Priest", "Chief Priests", "Christology",
    "Baptism in the Holy Spirit", "New Exodus",
}
PROTECTED_GLOSSARY_NAMES.update(
    f"{name}{possessive} Gospel"
    for name in ("Matthew", "Mark", "Luke", "John") for possessive in ("'s", "’s")
)
PROTECTED_GLOSSARY_NAMES.update(
    f"Gospel of {name}" for name in ("Matthew", "Mark", "Luke", "John")
)


class MarkdownAuditError(ValueError):
    """Invalid audit input or configuration."""


def canonical_book_names(text: str) -> set[str]:
    """Reuse the numbered 66-book table's Chinese and English names."""
    rows = extract_numbered_table_rows(text)
    english: list[str] = []
    for line in text.splitlines():
        if NUMBERED_TABLE_ROW.match(line):
            heading = re.match(r"\s*\*\*([^*]+)\*\*", line.split("|")[-2])
            if heading is None:
                raise MarkdownAuditError("canonical_english_book_name_missing")
            english.append(LINK.sub(lambda match: match[1], heading[1]).strip())
    chinese = [name for _, name in rows]
    if (len(rows) != 66 or len(set(chinese)) != 66 or len(set(english)) != 66
            or any(not name for name in chinese + english)):
        raise MarkdownAuditError("canonical_book_names_invalid")
    return set(chinese + english)


def partial_glossary_links(
    text: str, names: set[str], *, glossary_page: bool = False,
) -> list[tuple[int, int, str, str]]:
    """Reject links covering only part of a book title, name, or English word.

    Project Markdown links to their visible labels before comparing spans, so
    a preceding link or emphasis does not move the protected-name boundary.
    Whole-name glossary links and links to study pages remain valid.
    """
    findings: list[tuple[int, int, str, str]] = []
    patterns: list[tuple[str, re.Pattern[str]]] = []
    for name in sorted(names, key=lambda value: (-len(value), value)):
        before = r"(?<![A-Za-z0-9])" if name[0].isascii() else ""
        after = r"(?![A-Za-z0-9])" if name[-1].isascii() else ""
        patterns.append((name, re.compile(before + re.escape(name) + after, re.I)))

    def visible(value: str) -> str:
        return re.sub(r"[*_`]", "", value)

    for number, line in enumerate(text.splitlines(), 1):
        plain = ""
        cursor = 0
        spans: list[tuple[int, int, str, int]] = []
        for match in LINK.finditer(line):
            plain += visible(line[cursor:match.start()])
            label = visible(match[1])
            start = len(plain)
            plain += label
            target = urlsplit(match[2].strip())
            if unquote(target.path).endswith("Glossary/README.md") or (
                glossary_page and not target.path and target.fragment
            ):
                spans.append((start, len(plain), label, match.start()))
            cursor = match.end()
        if not spans:
            continue
        plain += visible(line[cursor:])
        protected = [
            (match.start(), match.end(), name)
            for name, pattern in patterns for match in pattern.finditer(plain)
        ]
        protected.extend(
            (match.start(1), match.end(1), match[1])
            for match in re.finditer(r"《([^》\n]+)》", plain)
        )
        for start, end, label, column in spans:
            split = next((
                name for left, right, name in protected
                if start < right and left < end and not (start <= left and end >= right)
            ), None)
            if split is None and label and (
                (start > 0 and re.fullmatch(r"[A-Za-z]", plain[start-1])
                 and re.match(r"[A-Za-z]", label))
                or (end < len(plain) and re.fullmatch(r"[A-Za-z]", plain[end])
                    and re.search(r"[A-Za-z]$", label))
            ):
                split = "English word"
            if split is not None:
                findings.append((number, column + 1, label, split))
    return findings


def adjacent_latin_v1(text: str) -> tuple[int, list[tuple[int, str]]]:
    """Return paired-line count and unpaired Chinese-only lines.

    A non-empty Chinese line counts as paired only when it already contains
    Latin text or an immediately adjacent non-empty line contains Latin text.
    The same algorithm drives the legacy report and the public baseline gate.
    """

    paired = 0
    unpaired: list[tuple[int, str]] = []
    lines = text.splitlines()
    for index, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or not CHINESE.search(stripped) or LATIN.search(stripped):
            continue
        nearby_latin = any(
            0 <= neighbor_index < len(lines)
            and bool(lines[neighbor_index].strip())
            and bool(LATIN.search(lines[neighbor_index].strip()))
            for neighbor_index in (index - 1, index + 1)
        )
        if nearby_latin:
            paired += 1
        else:
            unpaired.append((index + 1, stripped))
    return paired, unpaired


def _unique_json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise MarkdownAuditError(f"baseline_duplicate_key:{key}")
        result[key] = value
    return result


def parse_bilingual_baseline(data: bytes) -> dict[str, int]:
    """Parse and validate the versioned bilingual-debt baseline."""

    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as error:
        raise MarkdownAuditError("baseline_not_utf8") from error
    try:
        payload = json.loads(text, object_pairs_hook=_unique_json_object)
    except (json.JSONDecodeError, MarkdownAuditError) as error:
        if isinstance(error, MarkdownAuditError):
            raise
        raise MarkdownAuditError("baseline_invalid_json") from error
    if not isinstance(payload, dict):
        raise MarkdownAuditError("baseline_root_not_object")
    if set(payload) != {"schema", "algorithm", "files"}:
        raise MarkdownAuditError("baseline_top_level_keys_invalid")
    if (
        isinstance(payload.get("schema"), bool)
        or payload.get("schema") != BILINGUAL_BASELINE_SCHEMA
    ):
        raise MarkdownAuditError("baseline_schema_invalid")
    if payload.get("algorithm") != BILINGUAL_ALGORITHM:
        raise MarkdownAuditError("baseline_algorithm_invalid")

    raw_files = payload.get("files")
    if not isinstance(raw_files, dict):
        raise MarkdownAuditError("baseline_files_not_object")
    files: dict[str, int] = {}
    for raw_path, raw_count in raw_files.items():
        if not isinstance(raw_path, str) or not raw_path.endswith(".md"):
            raise MarkdownAuditError("baseline_path_invalid")
        if isinstance(raw_count, bool) or not isinstance(raw_count, int) or raw_count < 0:
            raise MarkdownAuditError(f"baseline_count_invalid:{raw_path}")
        files[raw_path] = raw_count
    return files


def public_markdown_counts(root: Path) -> dict[str, int]:
    """Count bilingual debt for the manifest-approved Markdown corpus."""

    manifest = (root / MANIFEST_PATH).read_bytes()
    entries = parse_manifest(manifest)
    public_markdown = [entry for entry in entries if entry.endswith(".md")]
    counts: dict[str, int] = {}
    for entry in public_markdown:
        path = root / entry
        if not path.is_file():
            raise MarkdownAuditError(f"public_markdown_missing:{entry}")
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError as error:
            raise MarkdownAuditError(f"public_markdown_not_utf8:{entry}") from error
        _, unpaired = adjacent_latin_v1(text)
        counts[entry] = len(unpaired)
    return counts


def compare_bilingual_baseline(
    current: dict[str, int], baseline: dict[str, int]
) -> tuple[list[str], int]:
    """Return regressions and the number of unpaired lines removed."""

    regressions: list[str] = []
    current_paths = set(current)
    baseline_paths = set(baseline)
    for path in sorted(current_paths - baseline_paths):
        regressions.append(f"baseline_missing_file:{path}")
    for path in sorted(baseline_paths - current_paths):
        regressions.append(f"baseline_extra_file:{path}")

    improvements = 0
    for path in sorted(current_paths & baseline_paths):
        current_count = current[path]
        baseline_count = baseline[path]
        if current_count > baseline_count:
            regressions.append(
                f"bilingual_regression:{path}:current={current_count}:baseline={baseline_count}"
            )
        else:
            improvements += baseline_count - current_count
    return regressions, improvements


def extract_numbered_table_rows(text: str) -> list[tuple[int, str]]:
    """Extract the first two cells from Markdown table rows with numeric IDs."""

    return [
        (int(number), name.strip())
        for number, name in NUMBERED_TABLE_ROW.findall(text)
    ]


def extract_h2_section(text: str, title_prefix: str) -> str | None:
    """Return an H2 section body, located by a stable title prefix."""

    headings = list(H2.finditer(text))
    for index, heading in enumerate(headings):
        if heading.group(1).strip().startswith(title_prefix):
            end = headings[index + 1].start() if index + 1 < len(headings) else len(text)
            return text[heading.end() : end]
    return None


def validate_numbered_book_rows(
    rows: list[tuple[int, str]], expected_count: int, label: str
) -> list[str]:
    """Validate exact numbering and unique, non-empty book names."""

    errors: list[str] = []
    numbers = [number for number, _ in rows]
    expected = list(range(1, expected_count + 1))
    if numbers != expected:
        errors.append(
            f"{label}_numbers_invalid:expected=1..{expected_count}:found="
            + ",".join(str(number) for number in numbers)
        )

    names = [name for _, name in rows]
    if any(not name for name in names):
        errors.append(f"{label}_empty_book_name")
    duplicates = sorted({name for name in names if names.count(name) > 1})
    for name in duplicates:
        errors.append(f"{label}_duplicate_book:{name}")
    return errors


def validate_book_selection(
    canonical_rows: list[tuple[int, str]],
    main_rows: list[tuple[int, str]],
    bridge_rows: list[tuple[int, str]],
    *,
    canonical_count: int = 66,
    main_count: int = 52,
    bridge_count: int = 14,
) -> list[str]:
    """Validate the canonical list and its 52-book plus 14-book partition."""

    errors = validate_numbered_book_rows(
        canonical_rows, canonical_count, "canonical_books"
    )
    errors.extend(validate_numbered_book_rows(main_rows, main_count, "main_books"))
    errors.extend(
        validate_numbered_book_rows(bridge_rows, bridge_count, "bridge_books")
    )

    canonical_names = {name for _, name in canonical_rows}
    main_names = {name for _, name in main_rows}
    bridge_names = {name for _, name in bridge_rows}
    overlap = sorted(main_names & bridge_names)
    if overlap:
        errors.append("selection_overlap:" + ",".join(overlap))

    selected_names = main_names | bridge_names
    missing = sorted(canonical_names - selected_names)
    extra = sorted(selected_names - canonical_names)
    if missing:
        errors.append("selection_union_missing:" + ",".join(missing))
    if extra:
        errors.append("selection_union_extra:" + ",".join(extra))
    return errors


def extract_numbered_entry_headings(text: str) -> list[tuple[int, str]]:
    """Extract numbered level-three entry headings from an evidence index."""

    return [
        (int(number), title.strip())
        for number, title in NUMBERED_ENTRY_HEADING.findall(text)
    ]


def validate_numbered_entries(
    rows: list[tuple[int, str]], expected_count: int, label: str = "evidence_entries"
) -> list[str]:
    """Validate exact ordered numbering and non-empty entry titles."""

    numbers = [number for number, _ in rows]
    expected = list(range(1, expected_count + 1))
    errors: list[str] = []
    if numbers != expected:
        errors.append(
            f"{label}_numbers_invalid:expected=1..{expected_count}:found="
            + ",".join(str(number) for number in numbers)
        )
    if any(not title for _, title in rows):
        errors.append(f"{label}_empty_title")
    return errors


def extract_evidence_anchors(text: str) -> list[int]:
    """Extract three-digit stable evidence anchors in document order."""

    return [int(number) for number in EVIDENCE_ANCHOR.findall(text)]


def extract_evidence_crosswalk_links(text: str) -> list[tuple[int, int]]:
    """Extract displayed evidence numbers and their linked anchor numbers."""

    return [
        (int(displayed), int(target))
        for displayed, target in EVIDENCE_CROSSWALK_LINK.findall(text)
    ]


def validate_evidence_navigation(
    anchors: list[int], links: list[tuple[int, int]], expected_count: int = 205
) -> list[str]:
    """Require one stable anchor and one matching crosswalk link per entry."""

    expected = list(range(1, expected_count + 1))
    errors: list[str] = []
    if anchors != expected:
        errors.append(
            f"evidence_anchor_sequence_invalid:expected=1..{expected_count}:found="
            + ",".join(str(number) for number in anchors)
        )
    displayed = [number for number, _ in links]
    targets = [target for _, target in links]
    if displayed != expected:
        errors.append(
            f"evidence_crosswalk_numbers_invalid:expected=1..{expected_count}:found="
            + ",".join(str(number) for number in displayed)
        )
    mismatches = [
        f"{displayed_number}->{target_number}"
        for displayed_number, target_number in links
        if displayed_number != target_number
    ]
    if mismatches:
        errors.append("evidence_crosswalk_targets_invalid:" + ",".join(mismatches))
    if targets != expected:
        errors.append(
            f"evidence_crosswalk_target_sequence_invalid:expected=1..{expected_count}:found="
            + ",".join(str(number) for number in targets)
        )
    return errors


def audit_corpus_integrity(root: Path) -> list[str]:
    """Check the numbered Bible-book partition and evidence-entry sequence."""

    corpus_paths = (
        CANONICAL_BOOKS_PATH,
        SELECTED_BOOKS_PATH,
        EVIDENCE_INDEX_PATH,
        EVIDENCE_CROSSWALK_PATH,
    )
    texts: dict[str, str] = {}
    errors: list[str] = []
    for relative in corpus_paths:
        try:
            texts[relative] = (root / relative).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as error:
            errors.append(f"corpus_file_unreadable:{relative}:{type(error).__name__}")
    if errors:
        return errors

    selected_text = texts[SELECTED_BOOKS_PATH]
    main_section = extract_h2_section(selected_text, "Book-by-Book Handoffs for the 52-Book Core | 二、52 卷逐卷接力")
    bridge_section = extract_h2_section(selected_text, "Reconnecting the 14 Companion Books | 三、14 卷怎样挂回主线")
    if main_section is None:
        errors.append("main_books_section_missing")
    if bridge_section is None:
        errors.append("bridge_books_section_missing")
    if errors:
        return errors

    canonical_rows = extract_numbered_table_rows(texts[CANONICAL_BOOKS_PATH])
    main_rows = extract_numbered_table_rows(main_section)
    bridge_rows = extract_numbered_table_rows(bridge_section)
    errors.extend(validate_book_selection(canonical_rows, main_rows, bridge_rows))

    evidence_rows = extract_numbered_entry_headings(texts[EVIDENCE_INDEX_PATH])
    errors.extend(validate_numbered_entries(evidence_rows, 205))
    crosswalk_section = extract_h2_section(
        texts[EVIDENCE_CROSSWALK_PATH], "Reverse Lookup: 205 Evidence Anchors, Weeks, and Books | 三、按 205 个锚点反查周次与书卷"
    )
    if crosswalk_section is None:
        errors.append("evidence_crosswalk_section_missing")
    else:
        errors.extend(
            validate_evidence_navigation(
                extract_evidence_anchors(texts[EVIDENCE_INDEX_PATH]),
                extract_evidence_crosswalk_links(crosswalk_section),
            )
        )
    return errors


def tracked_markdown() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "-z", "--", "*.md"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    return [ROOT / Path(item) for item in result.stdout.decode("utf-8").split("\0") if item]


def local_target(current: Path, raw_target: str) -> tuple[Path | None, str | None]:
    target = raw_target.strip()
    if target.startswith("<") and ">" in target:
        target = target[1 : target.index(">")]
    else:
        target = target.split(maxsplit=1)[0]

    parsed = urlsplit(target)
    if parsed.scheme or parsed.netloc:
        return None, None

    fragment = unquote(parsed.fragment) or None
    relative = unquote(parsed.path)
    target_path = (current.parent / relative).resolve() if relative else current
    return target_path, fragment


def index_like(path: Path) -> bool:
    return any(marker in path.name for marker in INDEX_MARKERS)


def main() -> int:
    files = tracked_markdown()
    missing_h1: list[str] = []
    duplicate_anchors: list[str] = []
    broken_links: list[str] = []
    unverified_fragments: list[str] = []
    unlinked_index_items: list[str] = []
    unpaired_chinese_lines: list[str] = []
    unpaired_by_file: dict[str, int] = {}
    paired_bilingual_lines = 0
    bilingual_body = 0
    h1_total = 0
    glossary_errors: list[str] = []
    protected_names = set(PROTECTED_GLOSSARY_NAMES)
    try:
        protected_names.update(canonical_book_names(
            (ROOT / CANONICAL_BOOKS_PATH).read_text(encoding="utf-8")
        ))
    except (OSError, MarkdownAuditError) as error:
        glossary_errors.append(f"canonical_glossary_names_invalid:{error}")

    for path in files:
        text = path.read_text(encoding="utf-8")
        relative = path.relative_to(ROOT).as_posix()
        glossary_errors.extend(
            f"{relative}:{number}:{column}: [{label}] splits {name}"
            for number, column, label, name in partial_glossary_links(
                text, protected_names, glossary_page=relative == "Glossary/README.md",
            )
        )
        if CHINESE.search(text) and LATIN.search(text):
            bilingual_body += 1

        # A mixed-script file is not enough: a Chinese paragraph should have
        # a nearby English counterpart.  We accept either ordering so that
        # existing notes can be migrated incrementally, while still exposing
        # isolated Chinese prose and table rows for follow-up translation.
        file_paired, file_unpaired = adjacent_latin_v1(text)
        paired_bilingual_lines += file_paired
        for line_number, stripped in file_unpaired:
            unpaired_chinese_lines.append(f"{relative}:{line_number}: {stripped}")
            unpaired_by_file[relative] = unpaired_by_file.get(relative, 0) + 1

        h1s = H1.findall(text)
        h1_total += len(h1s)
        if h1s and any("|" not in title for title in h1s):
            missing_h1.append(relative)

        anchors = ANCHOR.findall(text)
        seen: set[str] = set()
        for anchor in anchors:
            if anchor in seen:
                duplicate_anchors.append(f"{relative}#{anchor}")
            seen.add(anchor)

        for label, raw_target in LINK.findall(text):
            target_path, fragment = local_target(path, raw_target)
            if target_path is None:
                continue
            if not target_path.is_file():
                broken_links.append(f"{relative}: [{label}]({raw_target.strip()})")
                continue
            if fragment:
                target_text = target_path.read_text(encoding="utf-8")
                target_anchors = set(ANCHOR.findall(target_text))
                if fragment not in target_anchors:
                    unverified_fragments.append(
                        f"{relative}: [{label}] -> {target_path.relative_to(ROOT)}#{fragment}"
                    )

        if index_like(path):
            for line_number, line in enumerate(text.splitlines(), start=1):
                # Only flag list entries that appear to name a concrete file.
                # Explanatory bullets and checklists are not index rows.
                if (
                    LIST_ITEM.match(line)
                    and "[" not in line
                    and CODE_FILE_REFERENCE.search(line)
                ):
                    unlinked_index_items.append(f"{relative}:{line_number}: {line.strip()}")

    public_counts: dict[str, int] = {}
    baseline_regressions: list[str] = []
    baseline_improvements = 0
    try:
        public_counts = public_markdown_counts(ROOT)
    except PublicationExportError as error:
        baseline_regressions.append(f"publication_manifest_invalid:{error.code}")
    except (OSError, MarkdownAuditError) as error:
        baseline_regressions.append(f"public_markdown_audit_failed:{error}")
    else:
        try:
            baseline_data = (ROOT / BILINGUAL_BASELINE_PATH).read_bytes()
            baseline_counts = parse_bilingual_baseline(baseline_data)
        except (OSError, MarkdownAuditError) as error:
            baseline_regressions.append(f"bilingual_baseline_invalid:{error}")
        else:
            baseline_regressions, baseline_improvements = compare_bilingual_baseline(
                public_counts, baseline_counts
            )

    corpus_errors = audit_corpus_integrity(ROOT)

    print(f"markdown_files={len(files)}")
    print(f"bilingual_body_files={bilingual_body}/{len(files)}")
    print(f"bilingual_h1={h1_total - len(missing_h1)}/{h1_total}")
    print(f"broken_local_links={len(broken_links)}")
    print(f"duplicate_explicit_anchors={len(duplicate_anchors)}")
    print(f"fragments_needing_github_slug_review={len(unverified_fragments)}")
    print(f"unlinked_file_items_in_indexes={len(unlinked_index_items)}")
    print(f"paired_bilingual_lines={paired_bilingual_lines}")
    print(f"unpaired_chinese_lines={len(unpaired_chinese_lines)}")
    print("largest_unpaired_files=" + ", ".join(
        f"{path}:{count}" for path, count in sorted(
            unpaired_by_file.items(), key=lambda item: (-item[1], item[0])
        )[:12]
    ))
    print(f"public_markdown_files={len(public_counts)}")
    print(f"public_unpaired_chinese_lines={sum(public_counts.values())}")
    print(f"bilingual_baseline_regressions={len(baseline_regressions)}")
    print(f"bilingual_baseline_improvements={baseline_improvements}")
    print(f"corpus_integrity_errors={len(corpus_errors)}")
    print(f"partial_glossary_links={len(glossary_errors)}")

    for heading, entries in (
        ("missing_h1", missing_h1),
        ("broken_links", broken_links),
        ("duplicate_explicit_anchors", duplicate_anchors),
        ("fragments_needing_github_slug_review", unverified_fragments),
        ("unlinked_file_items_in_indexes", unlinked_index_items),
        ("unpaired_chinese_lines_sample", unpaired_chinese_lines[:80]),
        ("bilingual_baseline_regressions", baseline_regressions),
        ("corpus_integrity_errors", corpus_errors),
        ("partial_glossary_links", glossary_errors),
    ):
        if entries:
            print(f"\n[{heading}]")
            print("\n".join(entries))

    return 1 if (
        missing_h1
        or broken_links
        or duplicate_anchors
        or baseline_regressions
        or corpus_errors
        or glossary_errors
    ) else 0


if __name__ == "__main__":
    sys.exit(main())
