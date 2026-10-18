from __future__ import annotations

import os
import re
import shutil
import io
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from html.parser import HTMLParser
from pathlib import Path
from unittest.mock import patch

from scripts import build_static_site, export_publication
from scripts.build_static_site import (
    SiteBuildError,
    build_site,
    source_path_to_output,
    verify_site,
)
from scripts.export_publication import (
    CHECKSUMS_FILE,
    GENERATED_MANIFEST,
    MANIFEST_PATH,
    SOURCE_DATE_EPOCH,
    SnapshotFile,
    generated_metadata,
    parse_manifest,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


def _write_epoch_file(root: Path, relative: str, data: bytes) -> None:
    target = root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    target.chmod(0o644)
    os.utime(target, (SOURCE_DATE_EPOCH, SOURCE_DATE_EPOCH))


def _fix_directory_times(root: Path) -> None:
    directories = [root]
    directories.extend(path for path in root.rglob("*") if path.is_dir())
    for directory in sorted(
        directories, key=lambda path: len(path.parts), reverse=True
    ):
        directory.chmod(0o755)
        os.utime(directory, (SOURCE_DATE_EPOCH, SOURCE_DATE_EPOCH))


def create_snapshot(root: Path, pages: dict[str, str] | None = None) -> str:
    page_text = pages or {
        "README.md": (
            "# Project Covenant | 圣约计划\n\n" "[Guide | 指南](docs/guide.md#start)\n"
        ),
        "docs/guide.md": (
            "# Guide | 指南\n\n"
            '<a id="start"></a>\n\n'
            "## Start Here | 从这里开始\n\n"
            "Read **carefully** and return [home | 首页](../README.md).\n\n"
            "谨慎阅读，然后返回首页。\n"
        ),
    }
    manifest_paths = sorted([*page_text, MANIFEST_PATH])
    manifest = "".join(f"{path}\n" for path in manifest_paths).encode("utf-8")
    content: dict[str, bytes] = {
        **{path: text.encode("utf-8") for path, text in page_text.items()},
        MANIFEST_PATH: manifest,
    }
    files = [
        SnapshotFile(path, data, build_static_site.sha256_bytes(data))
        for path, data in sorted(content.items())
    ]
    generated_manifest, checksums, digest = generated_metadata(files)
    for path, data in content.items():
        _write_epoch_file(root, path, data)
    _write_epoch_file(root, GENERATED_MANIFEST, generated_manifest)
    _write_epoch_file(root, CHECKSUMS_FILE, checksums)
    _fix_directory_times(root)
    return digest


def create_current_worktree_snapshot(root: Path) -> str:
    manifest = (REPO_ROOT / MANIFEST_PATH).read_bytes()
    content: dict[str, bytes] = {
        path: (REPO_ROOT / path).read_bytes() for path in parse_manifest(manifest)
    }
    files = [
        SnapshotFile(path, data, build_static_site.sha256_bytes(data))
        for path, data in sorted(content.items())
    ]
    generated_manifest, checksums, digest = generated_metadata(files)
    for path, data in content.items():
        _write_epoch_file(root, path, data)
    _write_epoch_file(root, GENERATED_MANIFEST, generated_manifest)
    _write_epoch_file(root, CHECKSUMS_FILE, checksums)
    _fix_directory_times(root)
    return digest


class _VisibleText(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)

    def text(self) -> str:
        return " ".join(" ".join(self.parts).split())


class PathMappingTests(unittest.TestCase):
    def test_maps_readmes_and_regular_markdown_without_collisions(self) -> None:
        self.assertEqual("index.html", source_path_to_output("README.md"))
        self.assertEqual(
            "Bible_Timeline/index.html",
            source_path_to_output("Bible_Timeline/README.md"),
        )
        self.assertEqual(
            "Bible_Timeline/guide.html",
            source_path_to_output("Bible_Timeline/guide.md"),
        )

    def test_rejects_output_and_file_directory_collisions(self) -> None:
        cases = (
            {
                "README.md": "# Home | 首页\n",
                "index.md": "# Other | 其他\n",
            },
            {
                "README.md": "# Home | 首页\n",
                "topic.md": "# Topic | 主题\n",
                "topic.html/README.md": "# Nested | 嵌套\n",
            },
        )
        for pages in cases:
            with (
                self.subTest(paths=sorted(pages)),
                tempfile.TemporaryDirectory() as temporary,
            ):
                root = Path(temporary)
                snapshot = root / "snapshot"
                snapshot.mkdir()
                digest = create_snapshot(snapshot, pages)
                with self.assertRaises(SiteBuildError):
                    build_site(snapshot, digest, root / "site")


class SafeMarkdownRenderingTests(unittest.TestCase):
    def test_preserves_required_project_markdown_without_executable_html(self) -> None:
        pages = {
            "README.md": "# Home | 首页\n",
            "资料/指南.md": "# Guide | 指南\n",
        }
        mapping = build_static_site._page_map(list(pages))
        source = """\
<a id="start"></a>

## **Start** | 开始

1. Parent item
  - Child item
    中文续行
2. [x] Finished

> First line
>
> 第二行

| Name | Count |
| --- | ---: |
| `Marduka` | 2 |

```text
<script>alert(1)</script>
```

Literal <script>alert(2)</script> and ____ / ____.

_No transcripts. | 没有逐字稿。_

[RS 2.[005] *source*](https://example.org/wiki/Item_(edition))

[Unicode guide | 中文指南](资料/指南.md#part)

---
"""
        rendered = build_static_site.render_markdown_body("README.md", source, mapping)

        self.assertIn('<a id="start"', rendered)
        self.assertIn("<strong>Start</strong>", rendered)
        self.assertIn("<ol>", rendered)
        self.assertIn("<ul>", rendered)
        self.assertIn("Child item<br>中文续行", rendered)
        self.assertIn("☑", rendered)
        self.assertIn("<blockquote>", rendered)
        self.assertIn('<th scope="col" class="align-right">Count</th>', rendered)
        self.assertIn("<pre><code>&lt;script&gt;", rendered)
        self.assertNotIn("<script>", rendered)
        self.assertIn("____ / ____", rendered)
        self.assertIn("<em>No transcripts. | 没有逐字稿。</em>", rendered)
        self.assertIn("RS 2.[005] <em>source</em>", rendered)
        self.assertIn("Item_(edition)", rendered)
        self.assertIn("%E8%B5%84%E6%96%99/%E6%8C%87%E5%8D%97.html#part", rendered)
        self.assertIn("<hr>", rendered)

    def test_tilde_fence_escapes_markup_without_rendering_links(self) -> None:
        source = """\
# Safe | 安全

~~~text
[Fenced link](private.md)
<script>alert(1)</script>
~~~
"""
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            snapshot = root / "snapshot"
            output = root / "site"
            snapshot.mkdir()
            digest = create_snapshot(snapshot, {"README.md": source})

            build_site(snapshot, digest, output)
            rendered = (output / "index.html").read_text(encoding="utf-8")

            self.assertIn("<pre><code>", rendered)
            self.assertIn("[Fenced link](private.md)", rendered)
            self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", rendered)
            self.assertNotIn('href="private.md"', rendered)
            self.assertNotIn("<script>", rendered)

    def test_oversized_ordered_list_number_has_fixed_error(self) -> None:
        previous_limit = sys.get_int_max_str_digits()
        try:
            sys.set_int_max_str_digits(640)
            source = f"{'9' * 641}. item\n"
            with self.assertRaises(SiteBuildError) as context:
                build_static_site.render_markdown_body(
                    "README.md", source, {"README.md": "index.html"}
                )
        finally:
            sys.set_int_max_str_digits(previous_limit)

        self.assertEqual("SITE_ORDERED_LIST_NUMBER_INVALID", context.exception.code)


class HtmlPolicyTests(unittest.TestCase):
    def test_rejects_active_markup_unsafe_links_and_hidden_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            snapshot = root / "snapshot"
            snapshot.mkdir()
            digest = create_snapshot(snapshot)
            expected, _page_count = build_static_site._load_expected_site(
                snapshot, digest
            )
            original = expected["index.html"].decode("utf-8")
            mutations = (
                original.replace(
                    "<main ", '<img src="https://example.org/x"><main ', 1
                ),
                original.replace(
                    'href="docs/guide.html#start"', 'href="javascript:alert(1)"', 1
                ),
                original.replace(
                    'href="docs/guide.html#start"',
                    'href="https://%67ithub.com/example/project"',
                    1,
                ),
                original.replace("<body>", "<body><!-- hidden -->", 1),
                original.replace("<body>", "<body><?private data?>", 1),
                original.replace("<body>", "<body><p>github.com.</p>", 1),
                original.replace(
                    '<main id="main-content"', '<main style="display:none"', 1
                ),
            )
            for mutated in mutations:
                with self.subTest(marker=mutated[:80]):
                    candidate = dict(expected)
                    candidate["index.html"] = mutated.encode("utf-8")
                    with self.assertRaises(SiteBuildError):
                        build_static_site._validate_generated_site(candidate)


class StaticSiteIntegrationTests(unittest.TestCase):
    def test_rejects_invalid_source_and_unsafe_output_without_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            snapshot = root / "snapshot"
            snapshot.mkdir()
            digest = create_snapshot(snapshot)

            invalid_output = root / "invalid-site"
            with self.assertRaises(SiteBuildError):
                build_site(snapshot, "0" * 64, invalid_output)
            self.assertFalse(invalid_output.exists())

            inside_snapshot = snapshot / "site"
            with self.assertRaises(SiteBuildError):
                build_site(snapshot, digest, inside_snapshot)
            self.assertFalse(inside_snapshot.exists())

            existing = root / "existing"
            existing.mkdir()
            sentinel = existing / "keep.txt"
            sentinel.write_text("keep", encoding="utf-8")
            with self.assertRaises(SiteBuildError):
                build_site(snapshot, digest, existing)
            self.assertEqual("keep", sentinel.read_text(encoding="utf-8"))

    def test_bounds_source_line_and_output_enumeration(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            oversized_snapshot = root / "oversized-snapshot"
            oversized_snapshot.mkdir()
            oversized_digest = create_snapshot(
                oversized_snapshot,
                {"README.md": ("# Home | 首页\n\n" + "a" * 65 + "\n")},
            )
            with (
                patch.object(build_static_site, "MAX_MARKDOWN_LINE_BYTES", 64),
                self.assertRaises(SiteBuildError) as context,
            ):
                build_site(
                    oversized_snapshot, oversized_digest, root / "oversized-site"
                )
            self.assertEqual("SITE_MARKDOWN_LINE_TOO_LARGE", context.exception.code)

            snapshot = root / "snapshot"
            output = root / "site"
            snapshot.mkdir()
            digest = create_snapshot(snapshot)
            build_site(snapshot, digest, output)
            with (
                patch.object(build_static_site, "MAX_SITE_ENTRIES", 1),
                self.assertRaises(SiteBuildError) as context,
            ):
                verify_site(snapshot, digest, output)
            self.assertEqual("SITE_ENTRY_LIMIT_EXCEEDED", context.exception.code)

    def test_builds_only_html_and_local_css_from_verified_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            snapshot = root / "snapshot"
            output = root / "site"
            snapshot.mkdir()
            digest = create_snapshot(snapshot)

            report = build_site(snapshot, digest, output)

            self.assertEqual(2, report.page_count)
            self.assertEqual(3, report.file_count)
            self.assertEqual(
                {"assets/site.css", "docs/guide.html", "index.html"},
                {
                    path.relative_to(output).as_posix()
                    for path in output.rglob("*")
                    if path.is_file()
                },
            )
            home = (output / "index.html").read_text(encoding="utf-8")
            guide = (output / "docs/guide.html").read_text(encoding="utf-8")
            self.assertIn('href="docs/guide.html#start"', home)
            self.assertIn('href="../index.html"', guide)
            self.assertIn('href="../assets/site.css"', guide)
            self.assertIn('id="start"', guide)
            self.assertNotIn("publication/site-content.txt", home + guide)
            self.assertNotIn("github.com", (home + guide).lower())
            self.assertNotIn("<script", (home + guide).lower())
            self.assertNotIn("http://", (home + guide).lower())
            all_output = b"".join(
                path.read_bytes() for path in output.rglob("*") if path.is_file()
            )
            self.assertNotIn(digest.encode("ascii"), all_output)
            self.assertNotIn(str(snapshot).encode("utf-8"), all_output)
            self.assertNotIn(GENERATED_MANIFEST.encode("ascii"), all_output)
            self.assertNotIn(CHECKSUMS_FILE.encode("ascii"), all_output)

            verified = verify_site(snapshot, digest, output)
            self.assertEqual(report.site_set_sha256, verified.site_set_sha256)

    def test_escapes_raw_markup_and_hardens_external_links(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            snapshot = root / "snapshot"
            output = root / "site"
            snapshot.mkdir()
            digest = create_snapshot(
                snapshot,
                {
                    "README.md": (
                        "# Safe | 安全\n\n"
                        "Literal &lt;script&gt;alert(1)&lt;/script&gt; text.\n\n"
                        "`<script>alert(2)</script>`\n\n"
                        "[Outside | 外部](https://example.org/source)\n"
                    )
                },
            )

            build_site(snapshot, digest, output)
            html = (output / "index.html").read_text(encoding="utf-8")

            self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", html)
            self.assertNotIn("<script", html.lower())
            self.assertIn('rel="external noopener noreferrer"', html)
            self.assertIn('referrerpolicy="no-referrer"', html)
            for directive in (
                "default-src 'none'",
                "style-src 'self'",
                "form-action 'none'",
                "base-uri 'none'",
            ):
                self.assertIn(directive, html)

    def test_rejects_extra_tampered_symlink_mode_and_mtime(self) -> None:
        mutations = (
            "extra",
            "extra_directory",
            "missing",
            "tamper",
            "symlink",
            "hardlink",
            "fifo",
            "file_mode",
            "file_mtime",
            "directory_mode",
            "directory_mtime",
            "root_mode",
            "root_mtime",
        )
        for mutation in mutations:
            with (
                self.subTest(mutation=mutation),
                tempfile.TemporaryDirectory() as temporary,
            ):
                root = Path(temporary)
                snapshot = root / "snapshot"
                output = root / "site"
                snapshot.mkdir()
                digest = create_snapshot(snapshot)
                build_site(snapshot, digest, output)

                if mutation == "extra":
                    (output / "private.txt").write_text("private", encoding="utf-8")
                elif mutation == "extra_directory":
                    (output / "private").mkdir()
                elif mutation == "missing":
                    (output / "assets/site.css").unlink()
                elif mutation == "tamper":
                    (output / "index.html").write_text("changed", encoding="utf-8")
                elif mutation == "symlink":
                    (output / "assets/site.css").unlink()
                    (output / "assets/site.css").symlink_to(output / "index.html")
                elif mutation == "hardlink":
                    (output / "assets/site.css").unlink()
                    os.link(output / "index.html", output / "assets/site.css")
                elif mutation == "fifo":
                    (output / "assets/site.css").unlink()
                    os.mkfifo(output / "assets/site.css")
                elif mutation == "file_mode":
                    (output / "index.html").chmod(0o600)
                elif mutation == "file_mtime":
                    os.utime(output / "index.html", (1, 1))
                elif mutation == "directory_mode":
                    (output / "assets").chmod(0o700)
                elif mutation == "directory_mtime":
                    os.utime(output / "assets", (1, 1))
                elif mutation == "root_mode":
                    output.chmod(0o700)
                else:
                    os.utime(output, (1, 1))

                with self.assertRaises(SiteBuildError):
                    verify_site(snapshot, digest, output)

    def test_same_snapshot_produces_identical_site_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            snapshot = root / "snapshot"
            first = root / "site-one"
            second = root / "site-two"
            snapshot.mkdir()
            digest = create_snapshot(snapshot)

            previous_umask = os.umask(0o077)
            try:
                first_report = build_site(snapshot, digest, first)
            finally:
                os.umask(previous_umask)
            previous_umask = os.umask(0o022)
            try:
                second_report = build_site(snapshot, digest, second)
            finally:
                os.umask(previous_umask)

            self.assertEqual(
                first_report.site_set_sha256, second_report.site_set_sha256
            )
            for relative in ("assets/site.css", "docs/guide.html", "index.html"):
                self.assertEqual(
                    (first / relative).read_bytes(), (second / relative).read_bytes()
                )

    def test_verification_rejects_root_replacement_after_first_enumeration(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            snapshot = root / "snapshot"
            output = root / "site"
            replacement = root / "replacement"
            displaced = root / "displaced"
            snapshot.mkdir()
            digest = create_snapshot(snapshot)
            build_site(snapshot, digest, output)
            shutil.copytree(output, replacement)
            _write_epoch_file(replacement, "private.txt", b"must not be ignored\n")
            _fix_directory_times(replacement)
            real_enumerate = build_static_site._enumerate_site
            replaced = False

            def enumerate_then_replace(path: Path) -> tuple[set[str], set[str]]:
                nonlocal replaced
                result = real_enumerate(path)
                if not replaced:
                    replaced = True
                    path.rename(displaced)
                    replacement.rename(path)
                return result

            with (
                patch.object(
                    build_static_site,
                    "_enumerate_site",
                    side_effect=enumerate_then_replace,
                ),
                self.assertRaises(SiteBuildError) as context,
            ):
                verify_site(snapshot, digest, output)

            self.assertEqual(
                "SITE_ROOT_CHANGED_DURING_VERIFICATION", context.exception.code
            )
            self.assertTrue((output / "private.txt").is_file())

    def test_verification_rejects_extra_added_after_final_enumeration(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            snapshot = root / "snapshot"
            output = root / "site"
            snapshot.mkdir()
            digest = create_snapshot(snapshot)
            build_site(snapshot, digest, output)
            real_enumerate = build_static_site._enumerate_site
            enumerate_count = 0

            def enumerate_then_add(path: Path) -> tuple[set[str], set[str]]:
                nonlocal enumerate_count
                result = real_enumerate(path)
                enumerate_count += 1
                if enumerate_count == 2:
                    _write_epoch_file(path, "private.txt", b"must not be ignored\n")
                    os.utime(
                        path,
                        (
                            export_publication.SOURCE_DATE_EPOCH,
                            export_publication.SOURCE_DATE_EPOCH,
                        ),
                    )
                return result

            with (
                patch.object(
                    build_static_site,
                    "_enumerate_site",
                    side_effect=enumerate_then_add,
                ),
                self.assertRaises(SiteBuildError) as context,
            ):
                verify_site(snapshot, digest, output)

            self.assertEqual(
                "SITE_ROOT_CHANGED_DURING_VERIFICATION", context.exception.code
            )
            self.assertTrue((output / "private.txt").is_file())

    def test_builder_uses_verified_bytes_after_snapshot_path_changes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            snapshot = root / "snapshot"
            output = root / "site"
            snapshot.mkdir()
            digest = create_snapshot(snapshot)
            real_loader = export_publication.load_verified_snapshot

            def load_then_change(
                input_dir: Path, expected_digest: str
            ) -> export_publication.VerifiedSnapshot:
                verified = real_loader(input_dir, expected_digest)
                (snapshot / "README.md").write_text(
                    "# Changed | 已改变\n\n<script>bad</script>\n", encoding="utf-8"
                )
                return verified

            with patch.object(
                export_publication,
                "load_verified_snapshot",
                side_effect=load_then_change,
            ):
                report = build_site(snapshot, digest, output)

            self.assertEqual(2, report.page_count)
            home = (output / "index.html").read_text(encoding="utf-8")
            self.assertIn("Project Covenant | 圣约计划", home)
            self.assertNotIn("Changed", home)
            self.assertNotIn("<script", home.lower())


class CurrentPublicationCorpusTests(unittest.TestCase):
    def test_current_allowlist_builds_closed_site_without_archived_topics(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            snapshot = root / "snapshot"
            output = root / "site"
            snapshot.mkdir()
            digest = create_current_worktree_snapshot(snapshot)

            report = build_site(snapshot, digest, output)

            self.assertEqual(82, report.page_count)
            self.assertEqual(103, report.file_count)
            file_paths = {
                path.relative_to(output).as_posix()
                for path in output.rglob("*")
                if path.is_file()
            }
            self.assertEqual(82, sum(path.endswith(".html") for path in file_paths))
            self.assertEqual(
                {build_static_site.SITE_CSS_PATH},
                {path for path in file_paths if path.endswith(".css")},
            )
            self.assertFalse(
                any(path.endswith((".md", ".txt", ".json")) for path in file_paths)
            )

            html_texts = [
                (output / path).read_text(encoding="utf-8")
                for path in sorted(file_paths)
                if path.endswith(".html")
            ]
            # One source heading-shaped line is inside a fenced Markdown example.
            self.assertEqual(
                2306,
                sum(len(re.findall(r"<h[1-6](?: |>)", text)) for text in html_texts),
            )
            self.assertEqual(244, sum(text.count("<table>") for text in html_texts))
            self.assertEqual(24, sum(text.count("<pre><code>") for text in html_texts))
            self.assertGreaterEqual(sum(text.count("<a ") for text in html_texts), 1850)

            traditions_hub_output = "Christian_Traditions/index.html"
            traditions_hub = (output / traditions_hub_output).read_text(encoding="utf-8")
            terms_output = "Christian_Traditions/01_How_to_Name_the_Groups.html"
            home = (output / "index.html").read_text(encoding="utf-8")
            self.assertIn('href="Christian_Traditions/index.html"', home)
            self.assertIn('href="01_How_to_Name_the_Groups.html"', traditions_hub)
            manifest_paths = parse_manifest((REPO_ROOT / MANIFEST_PATH).read_bytes())
            archived_names = {
                path.name for path in (REPO_ROOT / "archive/Christian_Traditions").glob("*.md")
            }
            self.assertEqual(5, len(archived_names))
            self.assertFalse(any(path.startswith("archive/") for path in manifest_paths))
            self.assertFalse(any(path.startswith("docs/maintenance/") for path in manifest_paths))
            for name in archived_names:
                old_path = f"Christian_Traditions/{name}"
                self.assertNotIn(old_path, manifest_paths)
                self.assertNotIn(source_path_to_output(old_path), file_paths)
                self.assertNotIn(name.removesuffix(".md") + ".html", traditions_hub)
                self.assertNotIn(name.removesuffix(".md") + ".html", home)
            terms_page = (output / terms_output).read_text(encoding="utf-8")
            self.assertIn('href="index.html#column-index"', terms_page)
            self.assertIn("Evangelical | 福音派", terms_page)
            self.assertIn("How This Library Is Made | 资料库如何编写", home)
            self.assertNotIn("reviewed study notes", home)
            for source_path in manifest_paths:
                if source_path in {"README.md", "CREDITS.md"} or source_path.startswith((
                    "Bible_Timeline/", "Bible_Translations/", "Bilingual_Notes/",
                    "Book_Studies/", "Christian_Traditions/", "Maps/",
                )):
                    source = (REPO_ROOT / source_path).read_text(encoding="utf-8")
                    self.assertIn("Status: Draft (AI draft; not human reviewed)",
                                  "\n".join(source.splitlines()[:5]))
                    rendered_page = (output / source_path_to_output(source_path)).read_text(
                        encoding="utf-8"
                    )
                    self.assertIn("Status: Draft (AI draft; not human reviewed)", rendered_page)

            core_sources = [
                path for path in manifest_paths
                if path.endswith(".md") and Path(path).parent.as_posix() in {
                    "Bible_Timeline", "Bible_Translations", "Bilingual_Notes",
                    "Book_Studies", "Christian_Traditions",
                } and Path(path).name not in {
                    "README.md", "INDEX_Chronological.md", "研究维护日志.md",
                    "00_研究总索引与路线图.md",
                }
            ]
            self.assertEqual(66, len(core_sources))
            for source_path in core_sources:
                page = (output / source_path_to_output(source_path)).read_text(encoding="utf-8")
                with self.subTest(core_page=source_path):
                    self.assertIn('id="in-three-sentences"', page)
                    self.assertIn("In Three Sentences | 三句话读懂本篇", page)
                    self.assertIn('class="reading-time"', page)

            media_paths = {path for path in file_paths if path.endswith((".jpg", ".svg"))}
            self.assertEqual(20, len(media_paths))
            for media_path in media_paths:
                self.assertEqual((REPO_ROOT / media_path).read_bytes(), (output / media_path).read_bytes())
            self.assertIn('href="Maps/index.html"', home)
            maps_page = (output / "Maps/index.html").read_text(encoding="utf-8")
            self.assertEqual(9, maps_page.count('class="map-viewport"'))
            first_steps = (output / "Bible_Timeline/First_Steps_Bilingual.html").read_text(encoding="utf-8")
            self.assertEqual(10, first_steps.count('class="study-illustration"'))
            year_plan = (output / "Bible_Timeline/52周圣经故事线_查经与史料阅读计划.html").read_text(encoding="utf-8")
            self.assertEqual(10, year_plan.count('class="study-illustration"'))

            book_hub_output = "Book_Studies/index.html"
            book_hub = (output / book_hub_output).read_text(encoding="utf-8")
            self.assertEqual(3, book_hub.count("Why recommended | 推荐理由"))
            book_guides = {
                "Book_Studies/游子吟_永恒在召唤_全书解读与阅读指南.md": "《游子吟",
                "Book_Studies/求真寻道_约翰福音研经问答_使用指南.md": "《求真寻道",
                "Book_Studies/铁证待判_版本辨析与全书研读指南.md": "《铁证待判",
            }
            for source_path, title_marker in book_guides.items():
                guide_output = source_path_to_output(source_path)
                guide_href = (
                    build_static_site._relative_href(book_hub_output, guide_output)
                    + "#book-index"
                )
                self.assertIn(f'href="{guide_href}"', book_hub)
                self.assertIn(title_marker, book_hub)
                guide = (output / guide_output).read_text(encoding="utf-8")
                self.assertIn('href="index.html#library-index"', guide)
                self.assertIn('href="#book-index"', guide)

            license_page = (output / "LICENSE.html").read_text(encoding="utf-8")
            self.assertIn('href="LICENSE.html">Licensing | 授权说明</a>', home)
            self.assertIn(
                'href="STATIC_MIRROR_DEPLOYMENT.html">Static Mirror Deployment / '
                "静态镜像部署</a>",
                home,
            )
            self.assertIn("CC BY-NC-SA 4.0", license_page)
            self.assertIn("MIT License", license_page)
            self.assertIn("Material Not Relicensed Here | 本项目没有重新授权的材料", license_page)

            mirror_page = (output / "STATIC_MIRROR_DEPLOYMENT.html").read_text(
                encoding="utf-8"
            )
            self.assertIn('href="index.html">Back to Project Home | 返回项目首页</a>', mirror_page)
            self.assertIn(
                'href="PUBLICATION_POLICY.html"><code>PUBLICATION_POLICY.md</code></a>',
                mirror_page,
            )
            self.assertIn("Content-Security-Policy", mirror_page)
            self.assertIn("X-Content-Type-Options", mirror_page)
            self.assertIn("Referrer-Policy", mirror_page)
            self.assertIn("Permissions-Policy", mirror_page)
            self.assertIn('href="#mainland-china-access-boundary"', mirror_page)
            self.assertIn('id="mainland-china-access-boundary"', mirror_page)
            self.assertIn(
                "No external hosting provider, domain, account, or live mirror is configured",
                mirror_page,
            )

            evidence_index = (
                output / "Bible_Timeline" / "史料与考古旁证索引.html"
            ).read_text(encoding="utf-8")
            self.assertIn('href="#batch-11"', evidence_index)
            self.assertIn('id="batch-11"', evidence_index)
            self.assertIn('href="#top"', evidence_index)
            self.assertIn(
                'href="index.html">Back to the Bible Timeline Research Hub | '
                "返回圣经时间线研究中心</a>",
                evidence_index,
            )

            visible = _VisibleText()
            visible.feed("\n".join(html_texts))
            corpus_text = visible.text()
            for sentinel in (
                "└──",
                "昆兰 11Q5",
                "腓立比是罗马殖民城",
                "Marduka",
                "RS 2.[005]",
            ):
                self.assertIn(sentinel, corpus_text)

            verified = verify_site(snapshot, digest, output)
            self.assertEqual(report.site_set_sha256, verified.site_set_sha256)


class StaticSiteCliTests(unittest.TestCase):
    def test_cli_reports_fixed_error_without_traceback_or_local_path(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            snapshot = root / "snapshot"
            output = root / "site"
            snapshot.mkdir()
            create_snapshot(snapshot)
            stream = io.StringIO()
            arguments = [
                "build_static_site.py",
                "build",
                "--snapshot",
                str(snapshot),
                "--expected-content-set-sha256",
                "invalid",
                "--output",
                str(output),
            ]

            with patch.object(sys, "argv", arguments), redirect_stdout(stream):
                result = build_static_site.main()

            text = stream.getvalue()
            self.assertEqual(1, result)
            self.assertIn("site_build=FAIL", text)
            self.assertIn("error_code=SOURCE_EXPECTED_CONTENT_SET_DIGEST_INVALID", text)
            self.assertNotIn(str(root), text)
            self.assertNotIn("Traceback", text)

    def test_cli_redacts_unexpected_internal_error(self) -> None:
        stream = io.StringIO()
        arguments = [
            "build_static_site.py",
            "build",
            "--snapshot",
            "/not/reported/snapshot",
            "--expected-content-set-sha256",
            "0" * 64,
            "--output",
            "/not/reported/site",
        ]
        with (
            patch.object(sys, "argv", arguments),
            patch.object(
                build_static_site, "build_site", side_effect=RuntimeError("private")
            ),
            redirect_stdout(stream),
        ):
            result = build_static_site.main()

        text = stream.getvalue()
        self.assertEqual(1, result)
        self.assertEqual("error_code=INTERNAL_ERROR\nsite_build=FAIL\n", text)
        self.assertNotIn("private", text)
        self.assertNotIn("Traceback", text)


if __name__ == "__main__":
    unittest.main()
