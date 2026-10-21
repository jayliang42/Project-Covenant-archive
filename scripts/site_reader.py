"""Script-free reading chrome for already-rendered, approved site pages.

This module never loads repository files or fetches remote content. Every link
is selected from the verified page map supplied by the static-site builder.
"""
from __future__ import annotations

import html
import math
import posixpath
import re
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import PurePosixPath
from urllib.parse import quote


CSP = (
    "default-src 'none'; style-src 'self'; img-src 'self'; font-src 'none'; "
    "script-src 'none'; connect-src 'none'; object-src 'none'; frame-src 'none'; "
    "form-action 'none'; base-uri 'none'"
)

# A reading route, not a claim that the library is a complete Bible translation.
STORY_ROUTE = (
    "Bible_Timeline/README.md",
    "Bible_Timeline/First_Steps_Bilingual.md",
    "Bible_Timeline/Bible_Timeline_Bilingual.md",
    "Bible_Timeline/Old_Testament_Timeline_Bilingual.md",
    "Bible_Timeline/New_Testament_Timeline_Bilingual.md",
    "Bible_Timeline/Bible_By_Book_Bilingual.md",
    "Bible_Timeline/52周圣经故事线_查经与史料阅读计划.md",
    "Bible_Timeline/Bible_Timeline_Cheat_Sheet.md",
)
COLLECTIONS = (
    ("Bible_Timeline", "Storyline | 圣经故事线", "Follow the story, then explore its context. | 先读故事线，再深入背景。"),
    ("Bilingual_Notes", "Notes | 讲道与团契笔记", "Read draft sermon and fellowship notes. | 阅读讲道与团契笔记草稿。"),
    ("Book_Studies", "Book studies | 书籍研读", "Read with guides and source boundaries. | 带着导读和来源边界阅读。"),
    ("Christian_Traditions", "Traditions | 基督教传统", "Explore historical traditions and their differences. | 了解历史传统及其差异。"),
    ("Bible_Translations", "Translations | 圣经译本", "Find access guides and reading notes. | 查找获取指南与阅读说明。"),
    ("Maps", "Maps | 地图", "Read offline maps with bilingual labels. | 阅读带双语地名的离线地图。"),
    ("Glossary", "Glossary | 词汇表", "Look up common words in plain language. | 用白话查找常见词语。"),
)


@dataclass(frozen=True)
class Heading:
    identifier: str
    title: str
    level: int


class _OutlineParser(HTMLParser):
    """Read actual renderer IDs; never invent a second Markdown slug algorithm."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.headings: list[Heading] = []
        self.ids: set[str] = set()
        self.pending_anchor = ""
        self.active: tuple[str, str, int] | None = None
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        identifier = values.get("id") or ""
        if identifier:
            self.ids.add(identifier)
        if tag == "a" and identifier and self.active is None:
            self.pending_anchor = identifier
        elif tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            self.active = (tag, identifier or self.pending_anchor, int(tag[1]))
            self.parts = []
            self.pending_anchor = ""
        elif self.active is None:
            self.pending_anchor = ""
        if tag == "br" and self.active:
            self.parts.append(" ")

    def handle_endtag(self, tag: str) -> None:
        if self.active and tag == self.active[0]:
            _, identifier, level = self.active
            title = " ".join("".join(self.parts).split())
            if identifier and title and level in {2, 3}:
                self.headings.append(Heading(identifier, title, level))
            self.active = None
            self.parts = []

    def handle_data(self, data: str) -> None:
        if self.active:
            self.parts.append(data)
        elif data.strip():
            self.pending_anchor = ""


def outline(body: str) -> list[Heading]:
    parser = _OutlineParser()
    parser.feed(body)
    parser.close()
    # Long research pages can have hundreds of subheadings. Prefer their main
    # sections without truncating them; use third-level headings only as fallback.
    major = [heading for heading in parser.headings if heading.level == 2]
    return major or parser.headings


def _href(current: str, target: str) -> str:
    start = PurePosixPath(current).parent.as_posix()
    return quote(posixpath.relpath(target, start=start), safe="/-._~")


def _link(href: str, label: str, *, css: str = "", current: bool = False) -> str:
    attributes = f' class="{html.escape(css, quote=True)}"' if css else ""
    if current:
        attributes += ' aria-current="page"'
    return f'<a href="{html.escape(href, quote=True)}"{attributes}>{html.escape(label)}</a>'


def collection_order(source: str, page_map: dict[str, str]) -> list[str]:
    parent = PurePosixPath(source).parent
    if parent.as_posix() == ".":
        return []
    members = [path for path in page_map if PurePosixPath(path).parent == parent]
    priorities = {path: index for index, path in enumerate(STORY_ROUTE)}
    return sorted(members, key=lambda path: (
        PurePosixPath(path).name != "README.md",
        priorities.get(path, len(priorities)),
        path,
    ))


def _title(source: str, titles: dict[str, str]) -> str:
    return titles.get(source, PurePosixPath(source).stem.replace("_", " "))


def _toc(body: str) -> str:
    headings = outline(body)
    if not headings:
        return ""
    links = "\n".join(
        "<li>" + _link("#" + quote(item.identifier, safe="-._~:"), item.title) + "</li>"
        for item in headings
    )
    return '<nav class="reader-toc" aria-label="On this page | 本页目录"><ul>' + links + "</ul></nav>"


def _library_nav(source: str, output: str, page_map: dict[str, str]) -> str:
    links = ["<li>" + _link(_href(output, page_map["README.md"]), "Home | 首页", current=source == "README.md") + "</li>"]
    for directory, label, _ in COLLECTIONS:
        hub = directory + "/README.md"
        if hub in page_map:
            links.append("<li>" + _link(_href(output, page_map[hub]), label, current=source == hub) + "</li>")
    return '<nav class="library-nav" aria-label="Library | 资料导航"><ul>' + "\n".join(links) + "</ul></nav>"


def _chapter_nav(source: str, output: str, page_map: dict[str, str], titles: dict[str, str]) -> str:
    ordered = collection_order(source, page_map)
    if not ordered:
        return ""
    links = "\n".join(
        "<li>" + _link(_href(output, page_map[path]), _title(path, titles), current=source == path) + "</li>"
        for path in ordered
    )
    return '<div class="sidebar-label">In this collection | 本栏篇目</div><nav class="chapter-nav" aria-label="Collection contents | 栏目目录"><ol>' + links + "</ol></nav>"


def _pager(source: str, output: str, page_map: dict[str, str], titles: dict[str, str]) -> str:
    ordered = collection_order(source, page_map)
    if source not in ordered or len(ordered) < 2:
        return ""
    index = ordered.index(source)
    links: list[str] = []
    for offset, label, css in ((-1, "Previous | 上一篇", "previous"), (1, "Next | 下一篇", "next")):
        position = index + offset
        if 0 <= position < len(ordered):
            target = ordered[position]
            href = html.escape(_href(output, page_map[target]), quote=True)
            links.append(f'<a class="{css}" href="{href}"><span class="pager-label">{label}</span><strong>{html.escape(_title(target, titles))}</strong></a>')
    return '<nav class="reading-pager" aria-label="Continue reading | 继续阅读">' + "\n".join(links) + "</nav>"


def _home_intro(output: str, page_map: dict[str, str]) -> str:
    first = next((path for path in STORY_ROUTE[1:] if path in page_map), None)
    start = _link(_href(output, page_map[first]), "Start reading | 开始阅读 →", css="start-reading") if first else ""
    cards = []
    for index, (directory, label, description) in enumerate(COLLECTIONS, start=1):
        hub = directory + "/README.md"
        if hub not in page_map:
            continue
        href = html.escape(_href(output, page_map[hub]), quote=True)
        cards.append(f'<a class="collection-card" href="{href}"><span class="collection-number">{index:02d}</span><strong>{html.escape(label)}</strong><span class="collection-description">{html.escape(description)}</span></a>')
    return ('<div class="book-intro"><div class="eyebrow">A READING LIBRARY · 阅读资料库</div>'
            '<div class="book-tagline">One story. Many ways to explore.<br>一条故事线，多种研读路径。</div>'
            '<p>Begin with a short guide, follow a reading plan, or return to a topic. English coverage varies by page; each guide retains its language and source notes.</p>'
            '<p>从短篇导读开始，跟随阅读计划，或回到感兴趣的专题。各页英文覆盖程度不同，原有语言状态与来源说明均予保留。</p>'
            + start + '</div><nav class="collection-grid" aria-label="Choose a collection | 选择栏目">' + "\n".join(cards) + '</nav>')


def reading_time(body: str) -> str:
    """A declared reading aid, estimating one language rather than adding both."""
    text = html.unescape(re.sub(r"<[^>]*>", " ", body))
    english_words = len(re.findall(r"[A-Za-z]+(?:['’][A-Za-z]+)*", text))
    chinese_characters = len(re.findall(r"[\u3400-\u9fff]", text))
    minutes = max(english_words / 200, chinese_characters / 350)
    if minutes < 3:
        return ""
    low, high = math.ceil(minutes), math.ceil(minutes * 1.35)
    return (f"Reading: about {low}–{high} min in one language; excludes Bible passages and reflection. "
            f"| 阅读约 {low}–{high} 分钟（按一种语言，不含经文与思考）。")


def render_page(source: str, output: str, title: str, body: str,
                page_map: dict[str, str], titles: dict[str, str], css_path: str) -> bytes:
    """Compose reading navigation around untouched, trusted renderer output."""
    if "README.md" not in page_map or page_map.get(source) != output:
        raise ValueError("READER_PAGE_MAP_INVALID")
    library = _library_nav(source, output, page_map)
    chapter_nav = _chapter_nav(source, output, page_map, titles)
    toc = _toc(body)
    home = _href(output, page_map["README.md"])
    ordered = collection_order(source, page_map)
    position = f'{ordered.index(source) + 1:02d} / {len(ordered):02d}' if source in ordered else ""
    collection_label = next((label for folder, label, _ in COLLECTIONS if PurePosixPath(source).parent.as_posix() == folder), "Reading library | 阅读资料库")
    metadata = f'<div class="reading-meta"><span class="reading-collection">{html.escape(collection_label)}</span><span class="reading-position">{position}</span></div>'
    estimate = reading_time(body)
    if estimate:
        metadata += '<p class="reading-time">' + html.escape(estimate) + '</p>'
    intro = _home_intro(output, page_map) if source == "README.md" else ""
    mobile_toc = '<details class="mobile-toc"><summary>On this page | 本页目录</summary>' + toc + '</details>' if toc else ""
    right_toc = '<aside class="outline-sidebar"><div class="sidebar-label">On this page | 本页目录</div>' + toc + '</aside>' if toc else '<div class="outline-sidebar"></div>'
    policy_links = []
    for path, label in (("PUBLICATION_POLICY.md", "Privacy | 隐私与发布"), ("LICENSE.md", "Licensing | 授权说明")):
        if path in page_map:
            policy_links.append(_link(_href(output, page_map[path]), label))
    document = f'''<!doctype html>
<html lang="zh-Hans">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="referrer" content="no-referrer">
<meta http-equiv="Content-Security-Policy" content="{CSP}">
<title>{html.escape(title)} · Project Covenant</title>
<link rel="stylesheet" href="{html.escape(_href(output, css_path), quote=True)}">
</head>
<body>
<a class="skip-link" href="#main-content">Skip to content | 跳到正文</a>
<header class="site-header"><div class="header-inner">
<a class="site-title" href="{html.escape(home, quote=True)}"><span class="site-mark" aria-hidden="true">C</span>Project Covenant <span class="site-subtitle">圣约计划</span></a>
<span class="header-note">Read at your own pace | 按自己的节奏阅读</span>
</div></header>
<div class="mobile-navigation"><details><summary>Library &amp; chapters | 资料与篇目</summary>{library}{chapter_nav}</details></div>
<div class="reading-layout">
<aside class="library-sidebar"><div class="sidebar-label">Explore | 浏览资料</div>{library}{chapter_nav}<div class="sidebar-note">No account. No tracking.<br>无需账号，不记录阅读行为。</div></aside>
<main id="main-content" class="content" tabindex="-1">
{metadata}
{intro}
{mobile_toc}
<article class="reading-body">
{body}
</article>
{_pager(source, output, page_map, titles)}
<div class="reading-end"><a href="#main-content">Back to top | 返回页首 ↑</a></div>
</main>
{right_toc}
</div>
<footer class="site-footer"><div class="footer-inner"><p>Read carefully. Keep the sources close. | 细读正文，保留来源。</p><p>No analytics, forms, comments, or remote assets. | 不使用分析追踪、表单、评论或远程资源。</p><nav aria-label="Publication information | 发布说明">{' · '.join(policy_links)}</nav></div></footer>
</body>
</html>
'''
    return document.encode("utf-8")


SITE_CSS = """\
:root {
  color-scheme: light dark;
  --background: #f7f6f2; --surface: #fffefa; --text: #292e29;
  --muted: #656d62; --line: #dfE2d8; --accent: #456346;
  --accent-soft: #eaf0e5; --code: #eeeee7; --max: 88rem;
  --serif: Georgia, "Noto Serif CJK SC", "Songti SC", SimSun, serif;
}
@media (prefers-color-scheme: dark) {
  :root { --background: #191c19; --surface: #20251f; --text: #e5e9df;
    --muted: #aab6a4; --line: #374134; --accent: #b7d1a5;
    --accent-soft: #2c3b28; --code: #2b3229; }
}
* { box-sizing: border-box; }
html { scroll-behavior: smooth; scroll-padding-top: 5.5rem; }
body { margin: 0; background: var(--background); color: var(--text);
  font-family: system-ui, -apple-system, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
  font-size: 1rem; line-height: 1.8; }
a { color: var(--accent); text-underline-offset: .2em; overflow-wrap: anywhere; }
a:hover { text-decoration-thickness: .13em; }
a:focus-visible, summary:focus-visible { outline: 2px solid var(--accent); outline-offset: 4px; border-radius: 3px; }
.skip-link { position: absolute; left: -9999px; top: .5rem; z-index: 30; background: var(--surface); padding: .6rem 1rem; }
.skip-link:focus { left: 1rem; }
.site-header { position: sticky; top: 0; z-index: 10; background: var(--surface); border-bottom: 1px solid var(--line); }
.header-inner { max-width: var(--max); margin: auto; padding: .9rem 1.5rem; display: flex; align-items: center; justify-content: space-between; gap: 1rem; }
.site-title { display: flex; align-items: center; gap: .7rem; font-weight: 650; color: var(--text); text-decoration: none; letter-spacing: -.02em; }
.site-mark { display: inline-grid; place-items: center; width: 2.1rem; height: 2.4rem; border: 1px solid var(--accent); border-radius: 2px 6px 6px 2px; color: var(--accent); font: 1.5rem var(--serif); }
.site-subtitle { padding-left: .7rem; border-left: 1px solid var(--line); color: var(--muted); font-weight: 400; font-size: .9rem; }
.header-note { color: var(--muted); font-size: .75rem; }
.reading-layout { display: grid; grid-template-columns: 14rem minmax(0, 44rem) minmax(10rem, 14rem); gap: 2.25rem; max-width: var(--max); margin: 0 auto; padding: 2.25rem 1.5rem 4rem; align-items: start; }
.library-sidebar, .outline-sidebar { position: sticky; top: 6.25rem; max-height: calc(100dvh - 8rem); overflow-y: auto; scrollbar-width: thin; padding: 0 .65rem .8rem 0; }
.sidebar-label { color: var(--muted); font-size: .7rem; letter-spacing: .06em; margin: .3rem 0 .85rem; font-weight: 650; }
.library-nav ul, .chapter-nav ol, .reader-toc ul { padding: 0; list-style: none; margin: 0; }
.library-nav a { display: block; padding: .5rem .65rem; text-decoration: none; color: var(--text); font-size: .83rem; border-radius: .3rem; }
.library-nav li + li { margin-top: .15rem; }
.library-nav a:hover, .chapter-nav a:hover { background: var(--accent-soft); }
.library-nav a[aria-current="page"], .chapter-nav a[aria-current="page"] { background: var(--accent-soft); color: var(--accent); font-weight: 650; border-left: 2px solid var(--accent); }
.chapter-nav { margin-top: .5rem; }
.library-nav + .sidebar-label { border-top: 1px solid var(--line); padding-top: 1.5rem; margin-top: 1.5rem; }
.chapter-nav a { display: block; font-size: .75rem; padding: .5rem .65rem; text-decoration: none; color: var(--muted); border-left: 2px solid transparent; line-height: 1.65; }
.chapter-nav li + li { margin-top: .15rem; }
.sidebar-note { margin-top: 1.8rem; color: var(--muted); font-size: .7rem; border-top: 1px solid var(--line); padding-top: 1rem; }
.reader-toc a { display: block; padding: .45rem .65rem; color: var(--muted); font-size: .74rem; line-height: 1.6; text-decoration: none; border-left: 1px solid var(--line); }
.reader-toc a:hover { color: var(--accent); border-left-color: var(--accent); }
.content { min-width: 0; padding: 0 0 2rem; outline: none; overflow-wrap: anywhere; }
.reading-meta { display: flex; gap: 1rem; justify-content: space-between; align-items: center; color: var(--muted); font-size: .72rem; padding: .3rem 0 1.3rem; border-bottom: 1px solid var(--line); margin-bottom: 2rem; }
.reading-position { font-variant-numeric: tabular-nums; white-space: nowrap; letter-spacing: .1em; }
.reading-time { color: var(--muted); font-size: .82rem; line-height: 1.7; margin: -.7rem 0 1.5rem; }
.reading-body { font-size: 1.0625rem; line-height: 1.95; }
.reading-body h1 { font-family: var(--serif); font-size: clamp(1.8rem, 3.2vw, 2.65rem); line-height: 1.35; font-weight: 600; margin: 0 0 1.7rem; letter-spacing: -.035em; }
h2, h3, h4, h5, h6 { line-height: 1.45; scroll-margin-top: 5.5rem; }
.reading-body h2 { font-size: 1.45rem; margin-top: 3rem; padding-bottom: .65rem; border-bottom: 1px solid var(--line); letter-spacing: -.015em; }
.reading-body h3 { font-size: 1.15rem; margin-top: 2.1rem; }
.reading-body p { margin: 1rem 0; }
.reading-body li + li { margin-top: .4rem; }
.reading-body ul, .reading-body ol { padding-left: 1.6rem; }
.reading-body strong { font-weight: 650; }
blockquote { margin: 1.5rem 0; padding: .3rem 1.15rem; border-left: 3px solid var(--accent); background: var(--accent-soft); color: var(--muted); font-size: .96em; }
code { background: var(--code); padding: .12em .32em; border-radius: .2rem; font-family: ui-monospace, SFMono-Regular, Consolas, monospace; font-size: .85em; }
pre { padding: 1.15rem; overflow-x: auto; background: var(--code); border: 1px solid var(--line); border-radius: .35rem; line-height: 1.65; }
pre code { padding: 0; background: transparent; }
.table-scroll { max-width: 100%; overflow-x: auto; margin: 1.5rem 0; border: 1px solid var(--line); border-radius: .3rem; }
table { border-collapse: collapse; width: 100%; min-width: 34rem; font-size: .9375rem; line-height: 1.8; }
th, td { border-bottom: 1px solid var(--line); padding: .75rem .8rem; vertical-align: top; }
th { text-align: left; font-weight: 650; background: var(--accent-soft); }
tr:last-child td { border-bottom: 0; }
.align-right { text-align: right; }
.task-marker { display: inline-block; min-width: 1.35em; }
hr { border: 0; border-top: 1px solid var(--line); margin: 2.5rem 0; }
.anchor { display: block; position: relative; top: -5.5rem; visibility: hidden; }
.book-intro { padding: .7rem 0 2.1rem; }
.eyebrow { color: var(--accent); font-size: .7rem; letter-spacing: .15em; font-weight: 650; }
.book-tagline { line-height: 1.45; font-family: var(--serif); font-size: clamp(1.8rem, 3.2vw, 2.6rem); margin: 1rem 0; font-weight: 500; letter-spacing: -.025em; }
.book-intro p { color: var(--muted); font-size: .92rem; line-height: 1.8; max-width: 38rem; }
.start-reading { display: inline-block; margin-top: 1rem; padding: .65rem 1.15rem; background: var(--accent); color: var(--surface); border-radius: .25rem; text-decoration: none; font-size: .9rem; font-weight: 600; }
.collection-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: .8rem; margin-bottom: 3rem; }
.collection-card { display: grid; gap: .4rem; align-content: start; padding: 1.05rem; background: var(--surface); border: 1px solid var(--line); border-radius: .3rem; text-decoration: none; color: var(--text); }
.collection-card:hover { border-color: var(--accent); }
.collection-number { color: var(--muted); font-size: .7rem; letter-spacing: .1em; }
.collection-card strong { font-size: .9rem; font-weight: 600; }
.collection-description { color: var(--muted); font-size: .77rem; line-height: 1.7; }
.reading-pager { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; border-top: 1px solid var(--line); padding-top: 1.5rem; margin-top: 3rem; }
.reading-pager a { display: flex; flex-direction: column; gap: .45rem; padding: 1rem; border: 1px solid var(--line); border-radius: .3rem; background: var(--surface); text-decoration: none; font-size: .9rem; }
.reading-pager a:hover { border-color: var(--accent); }
.reading-pager .next { grid-column: 2; text-align: right; }
.pager-label { color: var(--muted); font-size: .72rem; }
.reading-pager strong { font-weight: 550; }
.reading-end { text-align: center; margin-top: 1.7rem; font-size: .75rem; }
.site-footer { border-top: 1px solid var(--line); }
.footer-inner { max-width: 48rem; padding: 1.5rem; margin: auto; text-align: center; color: var(--muted); font-size: .73rem; }
.footer-inner p { margin: .25rem 0; }
.footer-inner nav { margin-top: .75rem; }
.mobile-navigation, .mobile-toc { display: none; }
summary { cursor: pointer; padding: .75rem .9rem; font-size: .8rem; color: var(--accent); font-weight: 550; }
@media (max-width: 76rem) {
  .reading-layout { grid-template-columns: 13rem minmax(0, 44rem); gap: 2rem; max-width: 67rem; }
  .outline-sidebar { display: none; }
  .mobile-toc { display: block; margin-bottom: 1.6rem; border: 1px solid var(--line); border-radius: .3rem; background: var(--surface); }
  .mobile-toc .reader-toc { padding: 0 .9rem .9rem; max-height: 20rem; overflow-y: auto; }
}
@media (max-width: 50rem) {
  .header-inner { padding: .7rem 1rem; }
  .header-note { display: none; }
  .site-title { gap: .5rem; font-size: .94rem; }
  .site-subtitle { font-size: .78rem; }
  .site-mark { width: 1.8rem; height: 2rem; font-size: 1.25rem; }
  .reading-layout { display: block; padding: 1.25rem 1.15rem 2.5rem; }
  .library-sidebar { display: none; }
  .mobile-navigation { display: block; background: var(--surface); border-bottom: 1px solid var(--line); }
  .mobile-navigation details { padding: 0 .3rem; }
  .mobile-navigation .library-nav, .mobile-navigation .chapter-nav { padding: .5rem .75rem; }
  .mobile-navigation .chapter-nav { max-height: 45vh; overflow-y: auto; }
  .mobile-navigation .sidebar-label { padding-left: 1rem; }
  .reading-meta { margin-bottom: 1.4rem; padding-bottom: .85rem; }
  .reading-body { font-size: 1.0625rem; line-height: 1.95; }
  .reading-body h1 { font-size: 1.85rem; }
  .reading-body h2 { font-size: 1.3rem; }
  .reading-pager { gap: .6rem; }
  .reading-pager a { padding: .75rem; font-size: .8rem; }
}
@media (max-width: 26rem) {
  .collection-grid { grid-template-columns: 1fr; }
  .reading-collection { max-width: 75%; }
}
@media (prefers-reduced-motion: reduce) { html { scroll-behavior: auto; } }
@media print {
  :root { color-scheme: light; --background: white; --surface: white; --text: black; --muted: #333; --line: #aaa; --accent: #222; --accent-soft: #eee; --code: #eee; }
  .site-header, .library-sidebar, .outline-sidebar, .mobile-navigation, .mobile-toc, .reading-pager, .reading-end, .site-footer, .skip-link { display: none; }
  .reading-layout { display: block; padding: 0; }
  .content { max-width: none; }
  .reading-body { font-size: 10.5pt; }
  .table-scroll, pre { overflow: visible; }
  blockquote, .study-illustration { break-inside: avoid; }
  .reading-meta, .book-intro, .collection-grid { display: none; }
  table { min-width: 0; font-size: 8.5pt; }
  a { color: black; }
}
""".encode("utf-8")


SITE_CSS += b"""
.study-illustration { display: block; max-width: 100%; width: auto; max-height: 36rem; height: auto; margin: 1.25rem auto; }
.map-viewport { display: block; width: 100%; max-width: 100%; overflow-x: auto; border: 1px solid var(--line); background: #fff; margin: 1.25rem 0; }
.map-viewport:focus-visible { outline: 3px solid var(--accent); outline-offset: 2px; }
.study-map { display: block; min-width: 1100px; width: 100%; height: auto; max-width: none; }
@media print { .study-map { min-width: 0; width: 100%; max-height: 240mm; object-fit: contain; } .map-viewport { overflow: visible; border: 0; break-inside: avoid; } .study-illustration { max-height: 100mm; } }
"""
