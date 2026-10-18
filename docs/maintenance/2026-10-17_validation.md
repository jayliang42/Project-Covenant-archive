# Cleanup Validation | 整理后验证记录

> Status: Draft (AI-assisted; not human reviewed) | 状态：Draft（AI 辅助草稿，未人工审阅）

<a id="validation-index"></a>
## Contents | 目录

- [Scope | 范围](#scope)
- [Results | 结果](#results)
- [Remaining decisions | 待决定事项](#remaining-decisions)

<a id="scope"></a>
## Scope | 范围

The source baseline is `snapshot-2026-10-17` at `73a6c65571ad3d1cd355da1278fc4232906fa992`. Study content changed in `d575ccc`; the final reader-copy correction and regression assertion are in `67d6eb7`. Later maintenance-record edits do not change the website allowlist, study pages, scripts, or tests. / 研读内容改于 `d575ccc`，最终阅读器文案纠正及回归断言位于 `67d6eb7`；之后维护记录的编辑不改变网站清单、研读页、脚本或测试。

The [snapshot](./2026-10-17_snapshot.md) records 104 original files, directory sizes, and all 50 reachable commits. The [review](./2026-10-17_review.md) records findings against that original tree. Both were created and committed before study content changed. / 快照记录原有 104 个文件、目录大小及全部 50 个可达提交；审查报告针对原始文件树，二者均在研读内容改动前形成并提交。

Five files were relocated intact to the [archive](../../archive/README.md#archive-index), with only Draft labels and relative-link repairs. The active manifest lost exactly those five entries; the bilingual baseline lost only their matching keys and was not relaxed for retained pages. / 五份专题保留正文迁入归档，只增加 Draft 与修复相对链接；活动白名单恰好移出这五项，双语基线只移除对应键，没有放宽保留页面的限制。

There are 81 Draft-labelled library and archive Markdown pages: 75 active entry/study pages, five archived dossiers, and the archive index. Governance files keep their existing roles. Six pending-verification notices cover A1, A2, and A7–A10; no historical conclusion was rewritten. / 资料库与归档共 81 页标注 Draft：75 个活动入口及研读页、五份归档专题与归档索引；治理文件保留原有用途。六处待核实标注覆盖 A1、A2、A7–A10，没有改写历史结论。

<a id="results"></a>
## Results | 结果

| Check / 检查 | Evidence / 证据 |
| --- | --- |
| Full unit suite / 全部单元测试 | PASS: `python3 -m unittest discover -s tests -v`; 113 tests, 25.147 seconds, after the final reader-copy correction. / 最后一次阅读器文案纠正后，113 项测试通过。 |
| Markdown audit / Markdown 审计 | PASS: zero broken local links, unresolved fragments, duplicate explicit anchors, unlinked index filenames, baseline regressions, and corpus-integrity errors. / 所列结构错误均为零。 |
| Language debt / 双语欠缺 | 8,242 unpaired Chinese lines remain in 79 site-approved Markdown pages; the gate reports three improved lines and no regression. Draft status does not imply translation completion. / 79 个网站 Markdown 页仍有 8,242 行中文缺邻近英文，门槛记录改善三行、无退步；Draft 不代表翻译完成。 |
| Current privacy audit / 当前隐私审计 | PASS with 108 text files, 80 manifest entries, zero current-content or manifest findings. / 108 个文本文件、80 项清单，内容与清单发现均为零。 |
| Historical content audit / 历史内容审计 | PASS with zero historical-content findings; existing history was preserved. / 历史内容发现为零，旧历史保持不变。 |
| Export and snapshot verify / 导出及快照验证 | PASS from a fresh, clean local clone of the committed content ref; 80 allowlist entries, comprising 79 Markdown pages and the manifest. / 从内容提交的全新干净本地 clone 导出并验证通过，含 79 个 Markdown 页和清单，共 80 项。 |
| Static-site build and verify / 静态站点构建及验证 | PASS: 79 HTML pages and one local CSS file; 4,450,541 bytes. / 79 页 HTML 加一份本地 CSS，共 4,450,541 字节，通过验证。 |
| Offline package create and verify / 离线包生成及验证 | PASS: 80 site files; 4,469,823-byte ZIP, generated outside the repository. / 80 个站点文件，仓库外生成的 ZIP 为 4,469,823 字节，通过验证。 |
| Reader module / 阅读器模块 | Exercised by unit tests and the full-site build; it has no standalone CLI. / 已由单元测试和全站构建执行，没有独立 CLI。 |
| Chromium regression / Chromium 回归 | PASS: Chromium 143.0.7499.4, Playwright 1.57.0; all 79 pages over file and loopback HTTP at widths 320, 390, 768, 1024, and 1440; 790 layout checks, zero request errors. Homepage and mobile screenshots visually inspected, including the corrected Draft wording. / 两种访问方式、五种宽度、全部 79 页共 790 次布局检查通过，请求错误为零；已查看首页及手机截图，确认草稿文案。 |
| Archive preservation / 归档保留 | Direct before/after text comparison passed for all five moved files after removing the status line and reversing navigation repair; no substantive text differences. / 去掉状态行并还原导航修复后，五份迁移文件与原文逐份比较通过，没有实质文字差异。 |
| Status coverage / 状态覆盖 | All 81 content/archive pages have Draft in the opening five lines; the integration test checks active source and rendered labels. / 81 页前五行都有 Draft，集成测试同时检查活动源文件与渲染标签。 |
| Git and whitespace / Git 与空白 | `git diff --check` passes; no deleted files after rename detection. Only repository-local commit identity was configured. / 空白检查通过，按重命名检测没有文件被删除；提交身份仅配置在本仓库。 |

Artifact verification used the existing tools' required content-set digest, retained separately outside the checkout. Generated snapshots, browser dependencies, site files, screenshots, and ZIP files were kept outside the repository. / 产物验证使用现有工具要求的内容集摘要，并在 checkout 外另行保存；生成快照、浏览器依赖、站点、截图与 ZIP 均放在仓库外。

These checks establish local tooling and static-file behavior. They do not establish human content review, source permissions, the correctness of every historical claim, or a deployed website. / 这些检查证明本地工具及静态文件行为，不证明内容已获人工审阅、来源已获许可、每项历史说法都正确或网站已经部署。

<a id="remaining-decisions"></a>
## Remaining Decisions | 待决定事项

- Decide whether to keep, split, or delete any archived topic; no deletion is included. / 决定归档专题最终保留、拆分还是删除，本次没有删除。
- Review Draft pages as a human before assigning Reviewed; verify the six flagged items and any quotation permission needed. / 由人工阅读后再标 Reviewed，核实六处疑点及所需引文许可。
- Resolve the snapshot author-name conflict. The public report currently uses stable aliases; the complete no-email export with original author names remains local outside this repository. / 解决快照作者名与隐私规则的冲突：公开报告暂用稳定代号，含原作者名且不含邮箱的完整导出留在仓库外本地。
- Review the PR; merging remains an owner action. / 审核 PR，合并由用户决定。
