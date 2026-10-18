# Reading Interface | 阅读界面

The static site now presents the approved study library as a book-style reading interface. The existing export, build, verification, and offline-package commands remain unchanged.

静态站点现在以读书式界面呈现经过审核的研读资料库。现有导出、构建、验证和离线打包命令保持不变。

## Reading Features | 阅读功能

The home page offers a short starting route and collection entrances. Reading pages include collection navigation, an outline derived from actual rendered heading IDs, previous/next documents, and a back-to-top link. On small screens, native expandable menus replace the desktop sidebars.

首页提供简短入门路线和分类入口。阅读页包括栏目导航、根据正文真实标题锚点生成的页内目录、上一篇与下一篇，以及返回页首链接。小屏幕使用浏览器原生折叠菜单替代桌面侧栏。

The design includes system-following dark mode, keyboard focus indicators, a skip-to-content link, reduced-motion support, horizontally scrollable tables, and print styles. Credited maps and public-domain illustrations are local files; no remote fonts, images, or runtime dependencies are added.

界面提供跟随系统的深色模式、键盘焦点标识、跳到正文链接、减少动态效果支持、可横向滚动的表格，以及打印样式。地图与公有领域插画以本地文件加载并保留署名；不增加远程字体、图片或运行时依赖。

The number above a document is its position in the current collection, not a record of what the reader has finished. The site does not store progress or bookmarks. Browser bookmarks can retain a document or heading URL.

文章上方的数字表示它在当前栏目中的位置，不是读者已经完成的进度。站点不保存阅读进度或书签；浏览器书签可以保存文章或小节网址。

## Content and Safety | 内容与安全

Original Markdown, body text, citations, language-status notes, filenames, and publication permissions are unchanged. Navigation can only target pages present in the verified allowlist. Major headings are preferred for long-page outlines; third-level headings are used when there are no major headings.

原有 Markdown、正文、引文、语言状态说明、文件名及发布权限均不改变。导航只能指向已验证白名单中存在的页面。长文目录优先显示二级标题；没有二级标题时使用三级标题。

The output still contains exactly one HTML file per approved Markdown page and one local stylesheet plus approved local maps and illustrations. Scripts, tracking, forms, comments, remote assets, and source-repository links remain prohibited. The layout does not imply that untranslated source material is fully bilingual.

输出仍然严格对应为每份获准 Markdown 一个 HTML 文件，以及一份本地样式表及获准本地地图与插画。继续禁止脚本、追踪、表单、评论、远程资源及源仓库链接。界面不会把尚未翻译的来源材料标成完整双语。

## Verification and Preview | 验证与预览

Run the full regression suite and repository audits before export:

导出前运行完整回归测试和仓库审计：

```bash
python3 -m unittest discover -s tests -v
python3 scripts/audit_markdown.py
python3 scripts/audit_publication.py
python3 scripts/audit_publication.py --history-content
git diff --check
```

Use the existing commands in the [build instructions](./README.md) and the [deployment checklist](./STATIC_MIRROR_DEPLOYMENT.md). Export from a reviewed committed ref, retain the content-set digest, and verify both the site and offline ZIP against that same snapshot.

使用现有[构建说明](./README.md)与[部署清单](./STATIC_MIRROR_DEPLOYMENT.md)中的命令。从复核后的已提交版本导出，另行保留内容集摘要，并对照同一快照验证站点和离线 ZIP。

A successful Publication Guard run attaches the verified offline ZIP as a short-lived reading preview. Download and extract the artifact, then extract the inner ZIP and open its index page. This is a review artifact, not an automatically deployed public website.

Publication Guard 成功运行后，会附上经过验证的离线 ZIP，作为短期保留的阅读预览。下载并解压构件后，再解压内部 ZIP，打开其首页即可。这是审核用构件，不是自动部署的公开网站。

## Browser Regression Checks | 浏览器回归检查

The publication workflow also runs Chromium against the unchanged verified site through actual file URLs and a temporary loopback HTTP server. Every page is checked at 320, 390, 768, 1024, and 1440 pixel widths for stylesheet loading, document overflow, and reader structure. Mobile menus are opened and closed by keyboard on every page that contains them.

发布验证流程还会使用 Chromium，通过真实文件网址和临时本机 HTTP 服务检查未经修改的已验证站点。每页均检查 320、390、768、1024 和 1440 像素宽度下的样式加载、页面溢出和阅读结构；每页存在的手机目录都会通过键盘展开与收起。

Representative interactions cover starting a reading route, previous/next round trips, heading links, back-to-top, keyboard skip links, system dark mode, reduced motion, and print navigation hiding. Screenshots and a JSON result are retained separately from the reading package. These checks are not an assertion that every external source is reachable or that a public host has been deployed and reviewed.

代表性交互检查包括开始阅读、前后篇往返、小节链接、返回页首、键盘跳到正文、系统深色模式、减少动态效果和打印时隐藏导航。截图与 JSON 结果独立于阅读包保存。这些检查不表示每个外部来源都可访问，也不表示已经部署并复核公开托管网站。

Playwright is pinned as a development-only dependency; it is not shipped in the generated site. The browser check leaves the site files and its strict content security policy unchanged and rejects unexpected remote requests. It serves only the generated output, not the maintenance repository.

Playwright 固定版本且仅作为开发验证依赖，不会随生成站点发布。浏览器检查不修改站点文件或严格内容安全策略，并拒绝意外的远程请求。临时服务只提供生成产物，不提供维护仓库。

[Back to project entry | 返回项目入口](./README.md)
