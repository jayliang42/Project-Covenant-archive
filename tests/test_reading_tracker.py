from __future__ import annotations

from collections import Counter
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
TRACKER = ROOT / "Bible_Timeline/52周圣经故事线_精读通读双档打卡版.md"
CHAPTERS = {
    "创": 50, "出": 40, "利": 27, "民": 36, "申": 34, "书": 24,
    "士": 21, "得": 4, "撒上": 31, "撒下": 24, "王上": 22, "王下": 25,
    "代上": 29, "代下": 36, "拉": 10, "尼": 13, "斯": 10, "伯": 42,
    "诗": 150, "箴": 31, "传": 12, "歌": 8, "赛": 66, "耶": 52,
    "哀": 5, "结": 48, "但": 12, "何": 14, "珥": 3, "摩": 9,
    "俄": 1, "拿": 4, "弥": 7, "鸿": 3, "哈": 3, "番": 3,
    "该": 2, "亚": 14, "玛": 4, "太": 28, "可": 16, "路": 24,
    "约": 21, "徒": 28, "罗": 16, "林前": 16, "林后": 13, "加": 6,
    "弗": 6, "腓": 4, "西": 4, "帖前": 5, "帖后": 3, "提前": 6,
    "提后": 4, "多": 3, "门": 1, "来": 13, "雅": 5, "彼前": 5,
    "彼后": 3, "约一": 5, "约二": 1, "约三": 1, "犹": 1, "启": 22,
}
ENGLISH_BOOKS = dict(zip(
    ("Genesis|Exodus|Leviticus|Numbers|Deuteronomy|Joshua|Judges|Ruth|"
     "1 Samuel|2 Samuel|1 Kings|2 Kings|1 Chronicles|2 Chronicles|Ezra|Nehemiah|"
     "Esther|Job|Psalms|Proverbs|Ecclesiastes|Song of Songs|Isaiah|Jeremiah|"
     "Lamentations|Ezekiel|Daniel|Hosea|Joel|Amos|Obadiah|Jonah|Micah|Nahum|"
     "Habakkuk|Zephaniah|Haggai|Zechariah|Malachi|Matthew|Mark|Luke|John|Acts|"
     "Romans|1 Corinthians|2 Corinthians|Galatians|Ephesians|Philippians|Colossians|"
     "1 Thessalonians|2 Thessalonians|1 Timothy|2 Timothy|Titus|Philemon|Hebrews|"
     "James|1 Peter|2 Peter|1 John|2 John|3 John|Jude|Revelation").split("|"),
    CHAPTERS,
    strict=True,
))


class ReadingTrackerTests(unittest.TestCase):
    def test_english_and_chinese_through_reading_references_match(self) -> None:
        rows = [line for line in TRACKER.read_text(encoding="utf-8").splitlines()
                if re.match(r"^\|\s*\d+\s*\|", line)]
        self.assertEqual(52, len(rows))
        for row in rows:
            cells = [cell.strip() for cell in row.strip("|").split("|")]
            english, chinese = cells[3].split("<br>")
            references_en = re.sub(r"\(\d+ chapters\)$", "", english).strip()
            references_zh = re.sub(r"（\d+\s*章）$", "", chinese).strip()
            normalized: list[str] = []
            for reference in references_en.split(";"):
                match = re.fullmatch(r"(.+?)\s+(\d+(?:[–—-]\d+)?)", reference.strip())
                self.assertIsNotNone(match)
                assert match is not None
                book, chapters = match.groups()
                self.assertIn(book, ENGLISH_BOOKS)
                normalized.append(ENGLISH_BOOKS[book] + " " + chapters)
            self.assertEqual(references_zh, "；".join(normalized), f"week {cells[0]}")

    def test_through_reading_covers_each_chapter_once_with_correct_week_totals(self) -> None:
        seen: Counter[tuple[str, int]] = Counter()
        weeks: list[int] = []
        for line in TRACKER.read_text(encoding="utf-8").splitlines():
            if not re.match(r"^\|\s*\d+\s*\|", line):
                continue
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            self.assertEqual(6, len(cells))
            week = int(cells[0])
            weeks.append(week)
            # A bilingual cell keeps the unchanged Chinese reference last.
            through = cells[3].rsplit("<br>", 1)[-1].strip()
            declared = re.search(r"（(\d+)\s*章）$", through)
            self.assertIsNotNone(declared, f"week {week}: chapter total missing")
            assert declared is not None
            references = through[:declared.start()]
            week_count = 0
            for reference in references.split("；"):
                match = re.fullmatch(r"([\u4e00-\u9fff]+)\s+(\d+)(?:[–—-](\d+))?", reference.strip())
                self.assertIsNotNone(match, f"week {week}: invalid reference {reference}")
                assert match is not None
                book, start_text, end_text = match.groups()
                self.assertIn(book, CHAPTERS)
                start = int(start_text)
                end = int(end_text) if end_text else start
                self.assertTrue(1 <= start <= end <= CHAPTERS[book])
                for chapter in range(start, end + 1):
                    seen[book, chapter] += 1
                    week_count += 1
            self.assertEqual(int(declared.group(1)), week_count, f"week {week}")
        self.assertEqual(list(range(1, 53)), weeks)
        expected = {(book, chapter) for book, count in CHAPTERS.items() for chapter in range(1, count + 1)}
        self.assertEqual(1189, len(expected))
        self.assertEqual(expected, set(seen))
        self.assertTrue(all(count == 1 for count in seen.values()))


if __name__ == "__main__":
    unittest.main()
