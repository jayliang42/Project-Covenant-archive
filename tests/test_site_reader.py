from __future__ import annotations

import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlsplit

from scripts import site_reader


class ParsedPage(HTMLParser):
    def __init__(self, document: str):
        super().__init__(convert_charrefs=True)
        self.ids: set[str] = set()
        self.links: list[str] = []
        self.tags: list[tuple[str, dict[str, str | None]]] = []
        self.feed(document)
        self.close()

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        self.tags.append((tag, values))
        if values.get("id"):
            self.ids.add(values["id"])
        if tag == "a" and "href" in values:
            self.links.append(values["href"])


class ReaderTests(unittest.TestCase):
    def setUp(self):
        self.sources = {
            "README.md": "Home | 首页",
            "Bible_Timeline/README.md": "Storyline | 故事线",
            "Bible_Timeline/First_Steps_Bilingual.md": "First Steps | 第一步",
            "Bible_Timeline/Bible_Timeline_Bilingual.md": "Overview | 总览",
            "Bible_Timeline/研究 甲.md": "Research A | 研究甲",
            "Bible_Timeline/研究 乙.md": "Research B | 研究乙",
            "Book_Studies/README.md": "Book studies | 书籍研读",
            "Book_Studies/guide.md": "Guide | 指南",
            "LICENSE.md": "Licensing | 授权",
        }
        self.mapping = {
            source: str(PurePosixPath(source).with_name("index.html"))
            if source.endswith("README.md") else str(PurePosixPath(source).with_suffix(".html"))
            for source in self.sources
        }
        self.body = '<h1 id="guide">Guide | 指南</h1>\n<h2 id="start-开始">Start | 开始</h2><p>Body &amp; sources. | 正文与来源。</p>'

    def render(self, source="Bible_Timeline/First_Steps_Bilingual.md", body=None, mapping=None, titles=None):
        mapping = self.mapping if mapping is None else mapping
        titles = self.sources if titles is None else titles
        return site_reader.render_page(source, mapping[source], titles[source], self.body if body is None else body, mapping, titles, "assets/site.css").decode()

    def test_outline_uses_real_ids_and_nested_inline_text(self):
        headings = site_reader.outline('<h2 id="stable"><strong>One</strong> &amp; <em>Two</em><br>中文</h2>')
        self.assertEqual([site_reader.Heading("stable", "One & Two 中文", 2)], headings)

    def test_outline_supports_explicit_anchor_without_heading_id(self):
        headings = site_reader.outline('<a id="explicit"></a>\n<h2>Title | 标题</h2>')
        self.assertEqual("explicit", headings[0].identifier)

    def test_outline_prefers_heading_id_to_preceding_anchor(self):
        headings = site_reader.outline('<a id="alias"></a><h2 id="actual">Title</h2>')
        self.assertEqual("actual", headings[0].identifier)

    def test_outline_does_not_reuse_stale_anchor(self):
        self.assertEqual([], site_reader.outline('<a id="old"></a><p>Text</p><h2>No ID</h2>'))

    def test_outline_prefers_major_sections_without_truncation(self):
        body = ''.join(f'<h2 id="s{i}">Section {i}</h2><h3 id="x{i}">Subsection</h3>' for i in range(120))
        headings = site_reader.outline(body)
        self.assertEqual(120, len(headings))
        self.assertTrue(all(item.level == 2 for item in headings))

    def test_outline_falls_back_to_h3_and_ignores_code(self):
        self.assertEqual([site_reader.Heading("sub", "Subsection", 3)], site_reader.outline('<pre>&lt;h2 id="fake"&gt;Code&lt;/h2&gt;</pre><h3 id="sub">Subsection</h3>'))

    def test_no_toc_when_document_has_no_linkable_sections(self):
        page = self.render(body='<h1>Guide</h1><p>Text</p>')
        self.assertNotIn('class="reader-toc"', page)
        self.assertNotIn('class="mobile-toc"', page)

    def test_body_is_preserved_byte_for_byte(self):
        self.assertIn('<article class="reading-body">\n' + self.body + '\n</article>', self.render())

    def test_reading_time_counts_one_language_and_omits_short_pages(self):
        self.assertEqual("", site_reader.reading_time("<p>A short page.</p>"))
        bilingual = "<p>" + "word " * 600 + "</p><p>" + "字" * 1050 + "</p>"
        estimate = site_reader.reading_time(bilingual)
        self.assertIn("3–5 min", estimate)
        self.assertIn("按一种语言", estimate)
        rendered = self.render(body=bilingual)
        self.assertIn('class="reading-time"', rendered)
        self.assertIn("excludes Bible passages and reflection", rendered)

    def test_minimal_allowlist_never_invents_missing_collections(self):
        page = self.render(source="README.md", mapping={"README.md": "index.html"}, titles={"README.md": "Home"})
        parsed = ParsedPage(page)
        self.assertTrue(all(link in {"index.html", "#main-content", "#start-%E5%BC%80%E5%A7%8B"} for link in parsed.links))
        self.assertNotIn('class="start-reading"', page)
        self.assertNotIn('class="collection-card"', page)

    def test_collection_order_is_deterministic_and_curated(self):
        source = "Bible_Timeline/First_Steps_Bilingual.md"
        normal = site_reader.collection_order(source, self.mapping)
        reverse = site_reader.collection_order(source, dict(reversed(list(self.mapping.items()))))
        self.assertEqual(normal, reverse)
        self.assertEqual(list(site_reader.STORY_ROUTE[:3]), normal[:3])
        self.assertEqual(normal[-2:], ["Bible_Timeline/研究 乙.md", "Bible_Timeline/研究 甲.md"])

    def test_pagination_is_collection_local_and_not_a_reading_history(self):
        page = self.render()
        self.assertIn('02 / 05', page)
        self.assertIn('class="previous" href="index.html"', page)
        self.assertIn('class="next" href="Bible_Timeline_Bilingual.html"', page)
        self.assertNotIn('class="reading-pager"', self.render(source="LICENSE.md"))
        self.assertNotIn('class="reading-pager"', self.render(source="README.md"))

    def test_first_and_last_pages_do_not_wrap(self):
        order = site_reader.collection_order("Bible_Timeline/README.md", self.mapping)
        self.assertNotIn('class="previous"', self.render(source=order[0]))
        self.assertNotIn('class="next"', self.render(source=order[-1]))

    def test_home_has_only_existing_start_and_collection_links(self):
        page = self.render(source="README.md")
        self.assertIn('href="Bible_Timeline/First_Steps_Bilingual.html" class="start-reading"', page)
        self.assertEqual(2, page.count('class="collection-card"'))
        self.assertIn('English coverage varies by page', page)

    def test_markup_escapes_titles_and_encodes_unicode_paths(self):
        titles = dict(self.sources)
        titles["Bible_Timeline/研究 甲.md"] = '<script>unsafe</script> & "quotes"'
        page = self.render(titles=titles)
        self.assertNotIn('<script>', page)
        self.assertIn('&lt;script&gt;unsafe&lt;/script&gt;', page)
        self.assertIn('%E7%A0%94%E7%A9%B6%20%E7%94%B2.html', page)

    def test_active_page_mobile_navigation_and_keyboard_skip(self):
        page = self.render()
        self.assertIn('aria-current="page"', page)
        self.assertIn('<details><summary>', page)
        self.assertIn('<details class="mobile-toc">', page)
        self.assertIn('id="main-content" class="content" tabindex="-1"', page)

    def test_generated_local_links_and_fragments_resolve(self):
        rendered = {self.mapping[source]: ParsedPage(self.render(source=source)) for source in self.sources}
        for current, page in rendered.items():
            for link in page.links:
                with self.subTest(current=current, link=link):
                    parsed = urlsplit(link)
                    self.assertFalse(parsed.scheme or parsed.netloc or parsed.query)
                    parts = list(PurePosixPath(current).parent.parts)
                    for part in unquote(parsed.path).split('/') if parsed.path else []:
                        if part == '..':
                            parts.pop()
                        elif part and part != '.':
                            parts.append(part)
                    target = '/'.join(parts) if parsed.path else current
                    self.assertIn(target, rendered)
                    if parsed.fragment:
                        self.assertIn(unquote(parsed.fragment), rendered[target].ids)

    def test_static_privacy_and_accessibility_styles(self):
        page = self.render()
        tags = ParsedPage(page).tags
        self.assertFalse(any(tag in {'script', 'form', 'iframe', 'img', 'input'} for tag, _ in tags))
        self.assertFalse(any(name.startswith('on') for _, attrs in tags for name in attrs))
        self.assertIn("script-src 'none'", page)
        self.assertIn('name="referrer" content="no-referrer"', page)
        css = site_reader.SITE_CSS.lower()
        for token in [b'url(', b'@import', b'@font-face', b'http://', b'https://']:
            self.assertNotIn(token, css)
        for token in [b'prefers-reduced-motion', b'prefers-color-scheme', b'@media print', b':focus-visible']:
            self.assertIn(token, css)

    def test_rejects_inconsistent_page_map(self):
        with self.assertRaises(ValueError):
            site_reader.render_page('README.md', 'other.html', 'Home', '', self.mapping, self.sources, 'assets/site.css')


class ReaderIntegrationTests(unittest.TestCase):
    def test_existing_builder_and_verifier_accept_reader_output(self):
        from scripts import build_static_site
        from test_build_static_site import create_snapshot
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            snapshot = root / 'snapshot'
            snapshot.mkdir()
            digest = create_snapshot(snapshot)
            first = build_static_site.build_site(snapshot, digest, root / 'site')
            second = build_static_site.verify_site(snapshot, digest, root / 'site')
            self.assertEqual(first, second)
            self.assertIn('class="reading-body"', (root / 'site/docs/guide.html').read_text())
            self.assertEqual(first.page_count + 1, first.file_count)

    def test_new_native_tags_do_not_allow_event_handlers(self):
        from scripts import build_static_site
        for markup in ['<details ontoggle="alert(1)">', '<summary onclick="alert(1)">', '<aside style="color:red">', '<article onmouseover="alert(1)">']:
            with self.subTest(markup=markup), self.assertRaises(build_static_site.SiteBuildError):
                build_static_site._HTMLPolicyParser('index.html').feed(markup)


if __name__ == '__main__':
    unittest.main()
