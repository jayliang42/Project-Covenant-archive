from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.audit_markdown import (
    BILINGUAL_ALGORITHM,
    CANONICAL_BOOKS_PATH,
    PROTECTED_GLOSSARY_NAMES,
    MarkdownAuditError,
    adjacent_latin_v1,
    audit_corpus_integrity,
    canonical_book_names,
    compare_bilingual_baseline,
    extract_evidence_anchors,
    extract_evidence_crosswalk_links,
    extract_h2_section,
    extract_numbered_entry_headings,
    extract_numbered_table_rows,
    parse_bilingual_baseline,
    partial_glossary_links,
    public_markdown_counts,
    tracked_markdown,
    validate_book_selection,
    validate_evidence_navigation,
    validate_numbered_entries,
)
from scripts.export_publication import MANIFEST_PATH


REPO_ROOT = Path(__file__).resolve().parents[1]


class GlossaryBoundaryTests(unittest.TestCase):
    def test_all_66_bilingual_book_names_reject_partial_links(self) -> None:
        names = canonical_book_names((REPO_ROOT / CANONICAL_BOOKS_PATH).read_text())
        self.assertEqual(132, len(names))
        for name in names:
            for cut in range(1, len(name)):
                with self.subTest(book=name, cut=cut):
                    text = f"[{name[:cut]}](../Glossary/README.md#term){name[cut:]}"
                    self.assertTrue(partial_glossary_links(text, names))

    def test_whole_terms_and_study_navigation_remain_valid(self) -> None:
        names = {"使徒行传", "福音书", "Matthew"}
        text = (
            "[使徒](../Glossary/README.md#apostle)受差遣；"
            "[福音书](../Glossary/README.md#gospels)；"
            "[马太福音](../Bible_Timeline/Bible_By_Book_Bilingual.md#matthew)；"
            "[Gospel / 福音](../Glossary/README.md#gospel)"
        )
        self.assertEqual([], partial_glossary_links(text, names))
        self.assertEqual([], partial_glossary_links(
            "[福音书 / Gospels](#gospels)", names, glossary_page=True,
        ))

    def test_names_titles_emphasis_and_english_words_are_protected(self) -> None:
        samples = (
            "[普通链接](guide.md) **[使徒](../Glossary/README.md#apostle)**行传",
            "《喜乐于[三一](../Glossary/README.md#trinity)神》",
            "《优西比乌[教会](../Glossary/README.md#church)史》",
            "北美[基督](../Glossary/README.md#christ)之家",
            "Day of [Atonement](../Glossary/README.md#atonement)",
            "[Christ](../Glossary/README.md#christ)ology",
            "John’s [Gospel](../Glossary/README.md#gospel)",
            "四[福音](../Glossary/README.md#gospel)",
        )
        names = PROTECTED_GLOSSARY_NAMES | {"使徒行传"}
        for sample in samples:
            with self.subTest(sample=sample):
                self.assertTrue(partial_glossary_links(sample, names))

    def test_current_tracked_markdown_has_no_partial_glossary_links(self) -> None:
        names = PROTECTED_GLOSSARY_NAMES | canonical_book_names(
            (REPO_ROOT / CANONICAL_BOOKS_PATH).read_text()
        )
        for path in tracked_markdown():
            with self.subTest(page=path.relative_to(REPO_ROOT).as_posix()):
                self.assertEqual([], partial_glossary_links(
                    path.read_text(), names,
                    glossary_page=path == REPO_ROOT / "Glossary/README.md",
                ))

    def test_gospels_entry_distinguishes_the_four_books(self) -> None:
        glossary = (REPO_ROOT / "Glossary/README.md").read_text()
        section = glossary.split('<a id="gospels"></a>', 1)[1].split('<a id=', 1)[0]
        for name in ("Matthew", "Mark", "Luke", "John", "马太福音", "马可福音", "路加福音", "约翰福音"):
            self.assertIn(name, section)
        self.assertIn("First_Steps_Bilingual.md#stop-between", section)


class AdjacentLatinTests(unittest.TestCase):
    def test_counts_only_immediately_adjacent_translation(self) -> None:
        text = "中文第一行\nEnglish first line\n\n中文第二行\n\n中英 mixed\n"

        paired, unpaired = adjacent_latin_v1(text)

        self.assertEqual(1, paired)
        self.assertEqual([(4, "中文第二行")], unpaired)

    def test_english_before_chinese_also_pairs(self) -> None:
        paired, unpaired = adjacent_latin_v1("English first\n中文在后\n")

        self.assertEqual(1, paired)
        self.assertEqual([], unpaired)


class BilingualBaselineTests(unittest.TestCase):
    @staticmethod
    def baseline(files: dict[str, int]) -> bytes:
        return json.dumps(
            {"schema": 1, "algorithm": BILINGUAL_ALGORITHM, "files": files}
        ).encode("utf-8")

    def test_parses_valid_baseline_including_zero(self) -> None:
        self.assertEqual(
            {"README.md": 0, "guide.md": 3},
            parse_bilingual_baseline(
                self.baseline({"README.md": 0, "guide.md": 3})
            ),
        )

    def test_rejects_wrong_schema_and_algorithm(self) -> None:
        invalid_payloads = (
            {"schema": 2, "algorithm": BILINGUAL_ALGORITHM, "files": {}},
            {"schema": True, "algorithm": BILINGUAL_ALGORITHM, "files": {}},
            {"schema": 1, "algorithm": "different-v1", "files": {}},
        )
        for payload in invalid_payloads:
            with self.subTest(payload=payload), self.assertRaises(MarkdownAuditError):
                parse_bilingual_baseline(json.dumps(payload).encode("utf-8"))

    def test_rejects_missing_file_map_and_invalid_counts(self) -> None:
        payloads = (
            {"schema": 1, "algorithm": BILINGUAL_ALGORITHM},
            {
                "schema": 1,
                "algorithm": BILINGUAL_ALGORITHM,
                "files": {"README.md": -1},
            },
            {
                "schema": 1,
                "algorithm": BILINGUAL_ALGORITHM,
                "files": {"README.md": True},
            },
        )
        for payload in payloads:
            with self.subTest(payload=payload), self.assertRaises(MarkdownAuditError):
                parse_bilingual_baseline(json.dumps(payload).encode("utf-8"))

    def test_detects_regression_and_manifest_set_mismatch(self) -> None:
        regressions, improvements = compare_bilingual_baseline(
            {"added.md": 0, "kept.md": 4},
            {"kept.md": 3, "removed.md": 1},
        )

        self.assertEqual(
            [
                "baseline_missing_file:added.md",
                "baseline_extra_file:removed.md",
                "bilingual_regression:kept.md:current=4:baseline=3",
            ],
            regressions,
        )
        self.assertEqual(0, improvements)

    def test_allows_and_counts_improvement(self) -> None:
        regressions, improvements = compare_bilingual_baseline(
            {"README.md": 1, "guide.md": 0},
            {"README.md": 4, "guide.md": 2},
        )

        self.assertEqual([], regressions)
        self.assertEqual(5, improvements)

    def test_public_counts_use_only_manifest_markdown(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "publication").mkdir()
            (root / "README.md").write_text(
                "# Home | 首页\n\n中文未翻译\n", encoding="utf-8"
            )
            (root / "private.md").write_text("中文私有内容\n", encoding="utf-8")
            (root / MANIFEST_PATH).write_text(
                f"README.md\n{MANIFEST_PATH}\n", encoding="utf-8"
            )

            self.assertEqual({"README.md": 1}, public_markdown_counts(root))


class CorpusIntegrityFunctionTests(unittest.TestCase):
    def test_extracts_table_rows_and_h2_section(self) -> None:
        text = (
            "## Main route\n\n"
            "| 1 | 创世记 | note |\n"
            "| 2 | 出埃及记 | note |\n\n"
            "## Other\n\n| 1 | 不应读取 | note |\n"
        )

        section = extract_h2_section(text, "Main route")

        self.assertIsNotNone(section)
        self.assertEqual(
            [(1, "创世记"), (2, "出埃及记")],
            extract_numbered_table_rows(section or ""),
        )

    def test_accepts_valid_book_partition(self) -> None:
        errors = validate_book_selection(
            [(1, "A"), (2, "B"), (3, "C")],
            [(1, "A"), (2, "B")],
            [(1, "C")],
            canonical_count=3,
            main_count=2,
            bridge_count=1,
        )

        self.assertEqual([], errors)

    def test_rejects_number_gaps_duplicates_overlap_and_wrong_union(self) -> None:
        errors = validate_book_selection(
            [(1, "A"), (3, "A"), (2, "C")],
            [(1, "A"), (2, "X")],
            [(1, "A")],
            canonical_count=3,
            main_count=2,
            bridge_count=1,
        )

        self.assertTrue(
            any(
                error.startswith("canonical_books_numbers_invalid")
                for error in errors
            )
        )
        self.assertIn("canonical_books_duplicate_book:A", errors)
        self.assertIn("selection_overlap:A", errors)
        self.assertIn("selection_union_missing:C", errors)
        self.assertIn("selection_union_extra:X", errors)

    def test_evidence_heading_sequence_positive_and_negative(self) -> None:
        rows = extract_numbered_entry_headings(
            "### 1. First\ntext\n### 2. Second\n### 3. Third\n"
        )
        self.assertEqual([], validate_numbered_entries(rows, 3))

        errors = validate_numbered_entries([(1, "First"), (3, "Third")], 3)
        self.assertEqual(1, len(errors))
        self.assertTrue(errors[0].startswith("evidence_entries_numbers_invalid"))

    def test_evidence_navigation_requires_ordered_matching_deep_links(self) -> None:
        index_text = (
            '<a id="evidence-001"></a>\n\n### 1. First\n'
            '<a id="evidence-002"></a>\n\n### 2. Second\n'
        )
        crosswalk_text = (
            "| [1](./史料与考古旁证索引.md#evidence-001) | First |\n"
            "| [2](./史料与考古旁证索引.md#evidence-002) | Second |\n"
        )

        anchors = extract_evidence_anchors(index_text)
        links = extract_evidence_crosswalk_links(crosswalk_text)

        self.assertEqual([1, 2], anchors)
        self.assertEqual([(1, 1), (2, 2)], links)
        self.assertEqual([], validate_evidence_navigation(anchors, links, 2))

    def test_evidence_navigation_rejects_missing_and_misdirected_links(self) -> None:
        errors = validate_evidence_navigation([1, 2], [(1, 2)], 2)

        self.assertTrue(
            any(error.startswith("evidence_crosswalk_numbers_invalid") for error in errors)
        )
        self.assertIn("evidence_crosswalk_targets_invalid:1->2", errors)
        self.assertTrue(
            any(
                error.startswith("evidence_crosswalk_target_sequence_invalid")
                for error in errors
            )
        )


class CurrentCorpusIntegrityTests(unittest.TestCase):
    def test_current_public_corpus_is_internally_consistent(self) -> None:
        self.assertEqual([], audit_corpus_integrity(REPO_ROOT))


if __name__ == "__main__":
    unittest.main()
