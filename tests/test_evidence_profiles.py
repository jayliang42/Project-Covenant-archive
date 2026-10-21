from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / "Bible_Timeline/52卷主读_逐卷旁证类型画像.md"


class EvidenceProfileTests(unittest.TestCase):
    def test_ms_without_ev_prose_matches_both_tables_in_both_languages(self) -> None:
        text = PROFILE.read_text(encoding="utf-8")
        rows = [line for line in text.splitlines() if re.match(r"^\|\s*\d+\s*\|", line)]
        self.assertEqual(66, len(rows))
        block = text.split('### 1. MS without Contemporary EV for the Book |', 1)[1].split('### 2.', 1)[0]
        lists = re.findall(r"\n([A-Za-z0-9 ,]+)\.<br>\n([\u3400-\u9fff、]+)。", block)
        self.assertEqual(2, len(lists))
        for table, (english, chinese), expected_count in zip((rows[:52], rows[52:]), lists, (26, 9), strict=True):
            expected_en: set[str] = set()
            expected_zh: set[str] = set()
            for row in table:
                cells = [cell.strip() for cell in row.strip('|').split('|')]
                kinds = set(cells[3].split('／'))
                if 'MS' in kinds and 'EV' not in kinds:
                    expected_zh.add(cells[1])
                    expected_en.add(cells[-1].split(';', 1)[0].removeprefix('**'))
            self.assertEqual(expected_count, len(expected_en))
            actual_en = english.split(', ')
            actual_zh = chinese.split('、')
            self.assertEqual(len(actual_en), len(set(actual_en)))
            self.assertEqual(len(actual_zh), len(set(actual_zh)))
            self.assertEqual(expected_en, set(actual_en))
            self.assertEqual(expected_zh, set(actual_zh))
        self.assertIn('**35 books with MS and no contemporary EV**', block)
        self.assertIn('**35 卷有 MS 而无本卷同期 EV**', block)


if __name__ == '__main__':
    unittest.main()
