# Project Covenant | 圣约计划

> Status: Draft (AI draft; not human reviewed) | 状态：Draft（AI 草稿，未人工审阅）

> A bilingual study library for spiritual growth, sermon learning, and the Bible’s unified storyline.
> 一个用于灵命成长、讲道学习与整本圣经故事线研读的中英双语资料库。

## Start Here | 从这里开始

| I want to… | 我想… | Start with / 从这里开始 |
| --- | --- | --- |
| Start with a short, low-pressure route | 用短而轻松的路线第一次读圣经 | [First Steps in the Bible Story / 圣经故事线第一步](./Bible_Timeline/First_Steps_Bilingual.md) |
| See the Bible’s whole storyline | 先看整本圣经的大故事 | [Bible Timeline Overview / 圣经时间线总览](./Bible_Timeline/Bible_Timeline_Bilingual.md) |
| Read book by book | 按书卷串读 | [Bible by Book / 按书卷梳理圣经](./Bible_Timeline/Bible_By_Book_Bilingual.md) |
| Follow a one-year plan | 用一年读完故事线 | [52-Week Storyline Plan / 52 周故事线计划](./Bible_Timeline/52周圣经故事线_查经与史料阅读计划.md) |
| Read ISV as an English learner | 用 ISV 辅助英语读经 | [ISV Access and ESL Guide / ISV 获取与 ESL 指南](./Bible_Translations/ISV_International_Standard_Version_Access_and_ESL_Guide.md) |
| Find sermon and fellowship notes | 查找讲道与团契笔记 | [Notes Hub / 笔记中心](./Bilingual_Notes/README.md) |
| Study Christian books carefully | 系统研读基督教书籍 | [Christian Book Studies / 基督教书籍研读](./Book_Studies/README.md) |
| Understand denominations and theological terms | 了解宗派与神学术语 | [Christian Traditions / 基督教传统](./Christian_Traditions/README.md) |
| Read offline maps with bilingual place names | 阅读带双语地名的离线地图 | [Maps / 地图](./Maps/README.md) |
| Explore history and archaeology carefully | 查看史料、考古与证据边界 | [Bible Timeline Research Hub / 时间线研究中心](./Bible_Timeline/README.md) |
| Understand the public-content boundary | 了解公开内容边界 | [Privacy and Publication Policy / 隐私与发布政策](./PUBLICATION_POLICY.md) |
| Prepare a GitHub-independent mirror | 准备可脱离 GitHub 的阅读镜像 | [Static Mirror Deployment / 静态镜像部署](./STATIC_MIRROR_DEPLOYMENT.md) |
| Reuse original guides or software | 合法转载原创导读或使用项目代码 | [Licensing / 授权说明](./LICENSE.md) |

## What This Library Does | 这个资料库在做什么

### English

Project Covenant reads Scripture as one connected story: creation, fall, covenant, kingdom, exile, promise, Christ, church, and new creation. It combines biblical theology, historical context, manuscripts, and archaeology while distinguishing what each kind of evidence can—and cannot—show.

### 中文

Project Covenant 把圣经读成一条连贯的故事线：创造、堕落、圣约、国度、被掳、应许、基督、教会与新创造。资料库同时使用圣经神学、历史语境、抄本和考古材料，并清楚区分每类证据能支持什么、不能支持什么。

<a id="how-this-library-is-made"></a>
## How This Library Is Made | 资料库如何编写

AI assists with drafting, organizing, and translating this library. Sermon notes are summaries based on sermon content; supplemental studies and editorial inferences must be identified as such. Each major content page begins with a review status. AI assistance and automated checks do not establish historical accuracy, quotation permission, or human review.

本资料库由 AI 辅助起草、整理和翻译。讲道笔记依据讲道内容整理；补充查考与编辑推论须明确说明。每个主要内容页开头标注审阅状态。AI 辅助与自动检查不能证明史料准确、引文已获许可或内容已经人工审阅。

| Status / 状态 | Meaning / 含义 |
| --- | --- |
| Draft | AI draft; not human reviewed. / AI 草稿，未人工审阅。 |
| Reviewed | Human reviewed; assigned only after an actual human review. / 已人工审阅，仅在完成人工审阅后标注。 |

All major content pages in this cleanup remain Draft. Language coverage and technical privacy checks are separate from this content-review status. Historical statements marked “Pending verification / 待核实” remain unresolved.

本次整理的主要内容页全部保留 Draft。语言覆盖程度、技术隐私检查与内容审阅状态分别记录。标为“待核实”的历史说法仍未解决。

## Bilingual Reading Status | 双语阅读状态

| Content / 内容 | English status / 英文状态 | Chinese status / 中文状态 |
| --- | --- | --- |
| Main entry points and core timeline guides / 主要入口与核心时间线导读 | Substantial bilingual coverage; heading, link, and paragraph alignment continues | 已有较多双语覆盖；标题、链接与段落对应仍在补齐 |
| Sermon and fellowship notes / 讲道与团契笔记 | Bilingual titles and selected bilingual notes | 双语标题及部分双语笔记 |
| Historical, archaeological, and manuscript research dossiers / 历史、考古与抄本研究专题 | English navigation and summaries; most full research texts are currently Chinese | 英文导航与摘要；多数完整研究正文目前为中文 |

The goal is not to label an untranslated document as bilingual. New English summaries and full translations will be added progressively, beginning with the most-used study routes.

目标不是把未翻译的资料误标为“双语”。英文摘要和完整翻译会逐步补齐，并优先覆盖最常使用的研读路线。

## Library Map | 资料结构

```text
Project-Covenant/
├── README.md                  # Bilingual project entry | 双语项目入口
├── LICENSE.md                 # Content and software license map | 内容与软件授权总览
├── LICENSE-CODE               # Canonical MIT software license | MIT 软件许可标准文本
├── CONTRIBUTING.md            # Bilingual writing and source rules | 双语写作与来源规则
├── PUBLICATION_POLICY.md       # Privacy and publication boundary | 隐私与发布边界
├── STATIC_MIRROR_DEPLOYMENT.md # Provider-neutral mirror checklist | 与托管商无关的镜像清单
├── publication/
│   └── site-content.txt        # Exact future-site allowlist | 未来网站精确白名单
├── Bilingual_Notes/
│   ├── README.md              # Notes hub | 笔记中心
│   ├── INDEX_Chronological.md # Chronological note index | 时间索引
│   └── *.md                   # Sermon and fellowship notes | 讲道与团契笔记
├── Book_Studies/
│   ├── README.md              # Christian book-study hub | 基督教书籍研读导航
│   └── *.md                   # Book guides and critical reading maps | 书籍导读与批判性阅读地图
├── Christian_Traditions/
│   ├── README.md              # Christian terminology hub | 基督教术语导航
│   └── *.md                   # Denominations and theological terms | 宗派与神学术语
├── archive/                   # Unmaintained historical topics | 不再维护的旧专题
├── docs/maintenance/          # Snapshot, review, and validation records | 存档、审查及验证记录
├── Bible_Translations/
│   ├── README.md              # Translation-access hub | 圣经译本获取导航
│   └── *.md                   # Access guides and reading profiles | 获取指南与阅读定位
└── Bible_Timeline/
    ├── README.md              # Research hub | 研究导航
    ├── *_Bilingual.md         # Fully bilingual core guides | 核心双语导读
    ├── 52周_*.md / 52卷_*.md   # One-year route and book profiles | 年度路线与逐卷画像
    ├── 史料与考古旁证索引.md    # Evidence index | 史料与考古索引
    └── *_背景与证据边界.md      # Chinese research dossiers with English navigation | 中文研究专题及英文导航
```

## Main Paths | 主要路线

### Bible Timeline | 圣经时间线

- [First Steps in the Bible Story | 圣经故事线第一步](./Bible_Timeline/First_Steps_Bilingual.md)
- [Research Hub | 研究导航](./Bible_Timeline/README.md)
- [One-page Cheat Sheet | 一页式速查表](./Bible_Timeline/Bible_Timeline_Cheat_Sheet.md)
- [Old Testament Timeline | 旧约时间线](./Bible_Timeline/Old_Testament_Timeline_Bilingual.md)
- [New Testament Timeline | 新约时间线](./Bible_Timeline/New_Testament_Timeline_Bilingual.md)
- [52-Book Core + 14-Book Bridge | 52 卷主读＋14 卷桥接](./Bible_Timeline/52卷圣经故事主线_精选与14卷桥接版.md)

### Bible Translations | 圣经译本

- [Translation Hub | 译本导航](./Bible_Translations/README.md)
- [International Standard Version: Access and ESL Guide | ISV 获取与 ESL 阅读指南](./Bible_Translations/ISV_International_Standard_Version_Access_and_ESL_Guide.md)

### Sermon and Fellowship Notes | 讲道与团契笔记

- [Notes Hub | 笔记中心](./Bilingual_Notes/README.md)
- [Chronological Index | 时间索引](./Bilingual_Notes/INDEX_Chronological.md)
- [Teaching Summary | 全部 Teaching 总结](./Bilingual_Notes/All_Notes_Summary_Chronological.md)

### Christian Book Studies | 基督教书籍研读

- [Book-Study Hub | 书籍研读导航](./Book_Studies/README.md)
- [Song of a Wanderer: An Eternal Call — Whole-Book Guide | 《游子吟：永恒在召唤》全书解读](./Book_Studies/游子吟_永恒在召唤_全书解读与阅读指南.md)
- [Seek the Truth, Find the Way — Study Guide | 《求真寻道：约翰福音研经问答》使用指南](./Book_Studies/求真寻道_约翰福音研经问答_使用指南.md)
- [Evidence That Demands a Verdict — Edition-Aware Whole-Book Guide | 《铁证待判》版本辨析与全书研读指南](./Book_Studies/铁证待判_版本辨析与全书研读指南.md)

### Christian Traditions | 基督教传统

- [Column Hub | 专栏导航](./Christian_Traditions/README.md)
- [How to Name Christian Groups | 怎样给基督教群体命名](./Christian_Traditions/01_How_to_Name_the_Groups.md)

<a id="maps"></a>
### Maps | 地图

- [Offline Bible Maps | 离线圣经地图](./Maps/README.md)
- [Credits and Licenses | 资料来源与授权](./CREDITS.md)

## Research Boundaries | 研究边界

Historical and archaeological materials can illuminate people, places, institutions, texts, and historical settings. They do not automatically prove every narrative detail, authorial claim, miracle, or theological conclusion. Each research file therefore records both **what a source can support** and **where interpretation must stop**.

史料与考古可以照明人物、地点、制度、文本与历史处境，却不会自动证明每一项叙事细节、作者传统、神迹或神学结论。因此每份研究稿都同时记录“材料能支持什么”与“解释必须停在哪里”。

## Privacy and Publication | 隐私与发布

Public pages must not contain the maintainer's personal profile, contact route, private experience, immigration or asylum information, or identifiable participation history. Church names may remain when relevant, but they must not be combined with private personal details. Raw transcripts and private downloads are not public reading material.

公开页面不得包含维护者的个人简介、联系入口、私人经历、移民或庇护信息，或可识别的参与记录。教会名称在有关时可以保留，但不得与私人个人细节组合出现。原始逐字稿和私人下载文件不属于公开阅读内容。

See [Privacy and Publication Policy | 隐私与发布政策](./PUBLICATION_POLICY.md) for the review rules and the future website boundary.

审核规则与未来网站的发布边界，见 [Privacy and Publication Policy | 隐私与发布政策](./PUBLICATION_POLICY.md)。

A deterministic, Git-history-free content snapshot can be generated for a future site or clean repository import. This removes repository history from the transferred files, but it does not anonymize the GitHub account that publishes them.

项目可为未来网站或干净仓库导入生成可重现、不带 Git 历史的内容快照。这会去掉待转移文件中的仓库历史，但不会匿名化发布它们的 GitHub 账号。

The reviewed snapshot can also be rendered as a deterministic static reading site: one HTML page for every approved Markdown page and one local stylesheet plus approved local maps and illustrations. The generated site contains no JavaScript, analytics, forms, comments, remote images, remote fonts, source maps, Git history, or publication manifests. Building the files does not deploy them or make the hosting account anonymous.

经过复核的快照还可以生成可重现的静态阅读网站：每份获准 Markdown 对应一个 HTML 页面，另加一份本地样式表及获准的本地地图与插画。生成站点不包含 JavaScript、分析追踪、表单、评论、远程图片、远程字体、source map、Git 历史或发布清单。生成文件不等于已经部署，也不会自动匿名化托管账号。

## Build and Offline Reading | 构建与离线阅读

After creating and verifying a clean publication snapshot, build the static site and then create a byte-verifiable offline ZIP from that same snapshot. Do not ZIP the repository or an independently edited site directory.

先生成并验证干净发布快照，再从同一份快照构建静态站点和可逐字节验证的离线 ZIP。不要直接压缩整个仓库，也不要压缩另行编辑过的站点目录。

```bash
python3 scripts/build_static_site.py build \
  --snapshot /tmp/project-covenant-public \
  --expected-content-set-sha256 DIGEST_FROM_EXPORT \
  --output /tmp/project-covenant-site

python3 scripts/build_static_site.py verify \
  --snapshot /tmp/project-covenant-public \
  --expected-content-set-sha256 DIGEST_FROM_EXPORT \
  --input /tmp/project-covenant-site

python3 scripts/package_offline_site.py create \
  --snapshot /tmp/project-covenant-public \
  --expected-content-set-sha256 DIGEST_FROM_EXPORT \
  --output /tmp/project-covenant-offline.zip

python3 scripts/package_offline_site.py verify \
  --snapshot /tmp/project-covenant-public \
  --expected-content-set-sha256 DIGEST_FROM_EXPORT \
  --input /tmp/project-covenant-offline.zip
```

To read without GitHub or a web server, extract the ZIP and open `project-covenant-offline/index.html` in a browser. The package contains only the approved HTML pages, local CSS, maps, and illustrations; it contains no Git history, scripts, analytics, forms, remote assets, source manifest, or build metadata.

若要脱离 GitHub 和网页服务器阅读，请解压 ZIP，然后在浏览器中打开 `project-covenant-offline/index.html`。离线包只包含获准的 HTML 页面、本地 CSS、地图和插画，不包含 Git 历史、脚本、分析追踪、表单、远程资源、源白名单或构建元数据。

The current release tools require a POSIX system. Before placing the files on any public host, follow [Static Mirror Deployment | 静态镜像部署](./STATIC_MIRROR_DEPLOYMENT.md); the repository is deployment-ready but does not claim that an external mirror is already live.

当前发布工具要求 POSIX 系统。把文件放到任何公开托管服务之前，请遵循[静态镜像部署](./STATIC_MIRROR_DEPLOYMENT.md)；本仓库已经具备部署条件，但不声称外部镜像已经上线。

## Licensing | 授权说明

Original study guides and explanatory content are available under `CC BY-NC-SA 4.0`; repository scripts, tests, and workflow code use the MIT License. These licenses do not cover third-party Bible translations, published books, quotations, images, transcripts, or other material that Project Covenant contributors do not own. See [Licensing | 授权说明](./LICENSE.md) for the exact scope.

原创研读指南和解释性内容采用 `CC BY-NC-SA 4.0`；仓库脚本、测试和工作流代码采用 MIT License。上述许可证不涵盖第三方圣经译本、已出版书籍、引文、图片、逐字稿或其他 Project Covenant 贡献者并不拥有权利的材料。准确范围见[授权说明](./LICENSE.md)。

## Contributing | 参与整理

Please read [CONTRIBUTING.md](./CONTRIBUTING.md) before adding or translating material. It explains the bilingual format, source discipline, naming conventions, and how to avoid overstating historical evidence.

新增、翻译或修订资料前，请阅读[CONTRIBUTING.md](./CONTRIBUTING.md)。其中说明双语格式、来源纪律、命名方式，以及如何避免夸大历史证据。
