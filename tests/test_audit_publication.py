from __future__ import annotations

import unittest
from pathlib import Path

from scripts.audit_publication import (
    RAW_SITE_RESOURCE,
    local_targets,
    normalize_manifest_entry,
    scan_text,
)


class ContentRuleTests(unittest.TestCase):
    def rule_ids(self, text: str) -> set[str]:
        return {finding.rule_id for finding in scan_text("example.md", text)}

    def test_detects_direct_contact_and_local_path(self) -> None:
        email = "reader" + "@" + "example.org"
        phone = "312" + "-" + "555" + "-" + "0198"
        home_path = "/" + "Users/" + "example/Downloads/note.txt"
        rules = self.rule_ids(
            f"Reach me at {email} or {phone}.\n"
            f"Private source: {home_path}"
        )
        self.assertIn("DIRECT_EMAIL_ADDRESS", rules)
        self.assertIn("DIRECT_PHONE_NUMBER", rules)
        self.assertIn("LOCAL_HOME_PATH", rules)

    def test_detects_autobiographical_and_sensitive_history(self) -> None:
        attendance = "I " + "attended this church for three years."
        possessive = "M" + "y "
        immigration_topic = "asy" + "lum case was filed last year."
        asylum = possessive + immigration_topic
        health = "I was " + "diagnosed with depression in college."
        rules = self.rule_ids(
            f"{attendance}\n{asylum}\n{health}"
        )
        self.assertIn("AUTOBIOGRAPHICAL_STATEMENT_EN", rules)
        self.assertIn("PERSONAL_IMMIGRATION_OR_ASYLUM_EN", rules)
        self.assertIn("PERSONAL_HEALTH_HISTORY_EN", rules)

    def test_detects_secret_material(self) -> None:
        private_key = "-----" + "BEGIN PRIVATE KEY-----"
        github_token = "gh" + "p_" + ("A" * 36)
        aws_key = "AK" + "IA" + ("B" * 16)
        api_token = "sk" + "-proj-" + ("C" * 32)
        rules = self.rule_ids(
            f"{private_key}\n{github_token}\n{aws_key}\n{api_token}"
        )
        self.assertIn("SECRET_PRIVATE_KEY", rules)
        self.assertIn("SECRET_GITHUB_TOKEN", rules)
        self.assertIn("SECRET_AWS_ACCESS_KEY", rules)
        self.assertIn("SECRET_API_TOKEN", rules)

    def test_detects_identity_numbers_and_social_profiles(self) -> None:
        identity_number = "123" + "-" + "45" + "-" + "6789"
        profile = "https://" + "linkedin.com/in/example-person"
        github_profile = "https://" + "github.com/example-person"
        rules = self.rule_ids(f"{identity_number}\n{profile}\n{github_profile}")
        self.assertIn("US_SOCIAL_SECURITY_NUMBER", rules)
        self.assertIn("PRIVATE_SOCIAL_PROFILE", rules)

    def test_allows_github_repository_link(self) -> None:
        repository = "https://" + "github.com/example-org/example-project"
        self.assertNotIn("PRIVATE_SOCIAL_PROFILE", self.rule_ids(repository))

    def test_detects_chinese_contact_details(self) -> None:
        mobile = "138" + " 0013" + " 8000"
        landline_label = "联系" + "电话："
        landline = "010" + "-" + "12345678"
        wechat_label = "微" + "信号 "
        address_label = "家庭" + "住址："
        handle = "@" + "reader_88"
        handle_line = "contact: " + handle
        rules = self.rule_ids(
            f"{mobile}\n{landline_label}{landline}\n{wechat_label}reader_88\n"
            f"{address_label}北京市示例路一号\n{handle_line}"
        )
        self.assertIn("CHINESE_MOBILE_NUMBER", rules)
        self.assertIn("CHINESE_LABELED_LANDLINE", rules)
        self.assertIn("PRIVATE_CONTACT_HANDLE", rules)
        self.assertIn("PRIVATE_ADDRESS_LABEL", rules)
        self.assertIn("PLAIN_SOCIAL_HANDLE", rules)

    def test_distinguishes_signal_app_from_generic_signal_word(self) -> None:
        generic = "Treat this as a review signal rather than a fatal error."
        app_label = "Sig" + "nal: "
        contact = app_label + "reader_88"
        self.assertNotIn("PRIVATE_CONTACT_HANDLE", self.rule_ids(generic))
        self.assertIn("PRIVATE_CONTACT_HANDLE", self.rule_ids(contact))

    def test_detects_chinese_resident_id_and_conversion_history(self) -> None:
        body = "110105" + "19900101" + "001"
        weights = (7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2)
        check_codes = "10X98765432"
        checksum = sum(int(digit) * weight for digit, weight in zip(body, weights))
        resident_id = body + check_codes[checksum % 11]
        conversion_zh = "我" + "2021年开始信主"
        conversion_en = "I " + "became a Christian in college."
        rules = self.rule_ids(f"{resident_id}\n{conversion_zh}\n{conversion_en}")
        self.assertIn("CHINESE_RESIDENT_ID_NUMBER", rules)
        self.assertIn("AUTOBIOGRAPHICAL_STATEMENT_ZH", rules)
        self.assertIn("AUTOBIOGRAPHICAL_STATEMENT_EN", rules)

    def test_allows_biblical_reflection_and_historical_migration(self) -> None:
        rules = self.rule_ids(
            "How can my church welcome neighbors faithfully?\n"
            "Ancient migration into Egypt is relevant historical background.\n"
            "Reference: ISBN 978-1-4028-9462-6; session date 2026-01-21."
        )
        self.assertEqual(set(), rules)


class PublicationWordingTests(unittest.TestCase):
    def test_entry_and_governance_files_agree_on_page_content_scope(self) -> None:
        root = Path(__file__).resolve().parents[1]
        english = (
            "Page content does not include the maintainer's personal experiences, "
            "testimony, church attendance records, or contact information."
        )
        chinese = "页面内容不包含维护者的个人经历、见证、聚会出席记录和联系方式。"
        for name in ("PUBLICATION_POLICY.md", "README.md", "CONTRIBUTING.md", "AGENTS.md"):
            with self.subTest(file=name):
                text = (root / name).read_text(encoding="utf-8")
                self.assertIn(english, text)
                self.assertIn(chinese, text)
                self.assertEqual([], scan_text(name, text))


class ManifestPathTests(unittest.TestCase):
    def test_normalizes_safe_relative_path(self) -> None:
        self.assertEqual(
            "Bible_Timeline/README.md",
            normalize_manifest_entry("Bible_Timeline/README.md"),
        )

    def test_rejects_parent_traversal(self) -> None:
        with self.assertRaises(ValueError):
            normalize_manifest_entry("../private.md")

    def test_extracts_images_references_and_html_targets(self) -> None:
        self.assertEqual(["photo.jpg"], local_targets("![alt](photo.jpg)"))
        self.assertEqual(["notes.md"], local_targets("[notes]: notes.md"))
        self.assertEqual(["asset.png"], local_targets('<img src="asset.png">'))

    def test_forbids_raw_resource_html_but_allows_stable_anchor(self) -> None:
        self.assertIsNotNone(RAW_SITE_RESOURCE.search("<img src=private.jpg>"))
        self.assertIsNotNone(RAW_SITE_RESOURCE.search("<source srcset='a.jpg 1x'>"))
        self.assertIsNotNone(RAW_SITE_RESOURCE.search("style='background:url(a.jpg)'"))
        self.assertIsNone(RAW_SITE_RESOURCE.search('<a id="stable-anchor"></a>'))


if __name__ == "__main__":
    unittest.main()
