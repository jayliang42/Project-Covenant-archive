# Privacy and Publication Policy | 隐私与发布政策

> Status: Draft (AI draft; not human reviewed) | 状态：Draft（AI 草稿，未人工审阅）

## Purpose | 目的

Project Covenant is a public reading library. Public pages may explain Scripture, historical research, archaeology, Christian books, and teaching themes. Page content does not include the maintainer's personal experiences, testimony, church attendance records, or contact information.<br>
Project Covenant 是一个供公众阅读的资料库。公开页面可以整理圣经、历史研究、考古、基督教书籍和讲道主题。页面内容不包含维护者的个人经历、见证、聚会出席记录和联系方式。

## What May Be Published | 可以发布什么

- Biblical people, historical people, published authors, and other people already identified by a cited public source may be named when the name is necessary to understand the material.
  为理解资料所必需时，可以写出圣经人物、历史人物、已出版作者，以及由所引公开来源明确识别的其他人物。
- A church name may remain when it is relevant to the source. It must not be combined with a private person's role, attendance, home-group location, contact details, pastoral-care information, or other facts that could identify that person.
  教会名称与来源有关时可以保留，但不得与私人个人的职分、出席情况、家庭小组地点、联系方式、牧养关怀信息或其他可重新识别个人的事实组合出现。
- Teaching dates are source-session dates. They describe the material being summarized and do not state that the maintainer attended the session.
  讲道日期是来源聚会的日期，只用于说明所整理的材料，不表示维护者参加过该聚会。

## What Must Stay Private | 不得公开什么

- Private participants' real names, and anyone's personal username, email address, phone number, social-media profile, street address, school, employer, family details, or contact route.
  私人参与者的真实姓名，以及任何人的个人用户名、电子邮箱、电话号码、社交媒体主页、街道地址、学校、雇主、家庭信息或联系入口。
- Personal immigration or asylum information, legal case information, document numbers, medical or mental-health history, conversion or baptism story, testimony, discipleship history, attendance history, or other autobiographical experience.
  个人移民或庇护信息、法律案件信息、证件号码、医疗或心理健康经历、信主或受洗经历、个人见证、门徒训练经历、聚会出席记录，以及其他自传性经历。
- Raw transcripts, recordings, private downloads, meeting invitations, access codes, credentials, private keys, environment files, and unreviewed attachments.
  原始逐字稿、录音录像、私人下载文件、会议邀请、访问码、凭证、私钥、环境文件及未经审核的附件。
- A private anecdote must be removed or generalized into a non-identifying teaching point. Changing only the person's name is not sufficient when the remaining details can still identify the person.
  私人轶事必须删除，或改写成无法识别个人的一般教学要点。若其余细节仍能识别人，仅删除姓名并不够。

## Publication Review | 发布审核

Every tracked file is scanned for common personal identifiers, secrets, local paths, contact routes, and autobiographical disclosures. Automated checks are necessary safeguards, not proof of anonymity: a reviewer must also inspect the rendered public pages because a scanner cannot reliably reconstruct every Markdown rendering or distinguish a general illustration from a recognizable personal story.<br>
所有 Git 跟踪文件都要扫描常见个人识别信息、密钥、本机路径、联系入口和自传性披露。自动检查是必要防线，不是匿名保证；审核者还必须查看公开页面的实际渲染结果，因为扫描器无法可靠重建每一种 Markdown 渲染，也无法可靠区分一般例证和可识别的个人故事。

## Licensing Boundary | 授权边界

Publication approval and reuse permission are separate questions. A page may pass the privacy allowlist while still containing quotations or other third-party material that Project Covenant cannot relicense. The repository's dual-license terms apply only to original material for which contributors hold the necessary rights; see [Licensing | 授权说明](./LICENSE.md).

通过发布审核与获得再利用授权是两个不同问题。某个页面即使通过隐私白名单，仍可能包含 Project Covenant 无权重新授权的引文或其他第三方材料。仓库的双许可证只适用于贡献者确实拥有相应权利的原创材料；详见[授权说明](./LICENSE.md)。

Before copying or adapting a page, users must preserve third-party notices and independently check the status of Bible translations, books, quotations, images, and linked resources. Inclusion in a public or offline package does not expand the rights granted by their original owners.
<br>
复制或改编页面前，使用者必须保留第三方权利说明，并自行核对圣经译本、书籍、引文、图片和链接资源的授权状态。材料被列入公开网站或离线包，并不会扩大原权利人授予的权利。

Run these checks before publishing:<br>
发布前运行以下检查：

```bash
python3 scripts/audit_markdown.py
python3 scripts/audit_publication.py
python3 scripts/audit_publication.py --history-content
git diff --check
```

Use `python3 scripts/audit_publication.py --history` for the stricter audit that also checks redacted Git author, email, tagger, and remote-owner metadata. The command audits the repository containing the script. Because the generated neutral mirror intentionally omits scripts, verify that mirror from its own clone with a separately reviewed, temporary untracked copy of this audit tool—or perform equivalent external checks—and pass its reviewed public account with `--approved-remote-owner OWNER`. Never commit the temporary tool to the reading mirror. The audit is expected to pass only after neutral ownership and sanitized history have been established.<br>
使用 `python3 scripts/audit_publication.py --history` 运行更严格的检查；它还会以脱敏形式检查 Git 作者、邮箱、标签作者和远端所有者元数据。该命令审核的是脚本所在仓库。由于生成的中性镜像会有意省略脚本，应在该镜像自己的 clone 中使用另行复核、临时且不跟踪的审计工具副本进行检查，或执行等效的外部检查，并用 `--approved-remote-owner OWNER` 传入其经过复核的公开账号。不得把临时工具提交到阅读镜像。只有中性账号归属和脱敏历史都已经建立之后，这项检查才应通过。

## Clean Publication Snapshot | 干净发布快照

Local media are limited to allowlisted, validated SVG maps and baseline JPEG illustrations with source-specific notices in `CREDITS.md`. SVG must have accessible titles and descriptions and contain no active or remote content. JPEG must be under 300,000 bytes with EXIF, ICC, IPTC, and comments removed. Other binary formats remain prohibited.<br>
本地素材仅限白名单内、经过验证的 SVG 地图和基线 JPEG 插画，并须在 `CREDITS.md` 保留各来源授权。SVG 必须有可访问的标题与说明，不得包含活动或远程内容；JPEG 必须小于 300,000 字节，清除 EXIF、ICC、IPTC 和注释。其他二进制格式仍被禁止。

The publication exporter resolves the checked-out Git commit, reads the allowlist and every approved Markdown file and local asset from that same commit, and writes an outside-repository directory with deterministic content, paths, modes, and checked modification times. It does not copy `.git`, commit metadata, the remote URL, working-tree changes, untracked files, or files outside the allowlist. UID/GID ownership, ctime, ACLs, and extended attributes are not part of the content-set digest and must not be treated as verified identity metadata.<br>
发布导出器会锁定当前 checkout 对应的 Git 提交，从同一提交中读取白名单及全部获准 Markdown 文件与本地素材，再在仓库外写出内容、路径、模式和受检修改时间均确定的目录。它不会复制 `.git`、提交元数据、远端地址、工作区修改、未跟踪文件或白名单外文件。UID/GID 所有权、ctime、ACL 和扩展属性不属于内容集摘要的保护范围，不能被视为已经验证的身份元数据。

Commit every intended public change before exporting, and run the release only from a fresh, reviewed, clean checkout or equivalent trusted CI checkout. Content blobs come from the selected commit, but the exporter and imported audit code come from the checkout that executes them. The exporter is POSIX-only and fails closed on symlinks, gitlinks, Git LFS pointers, unapproved binary or non-UTF-8 input, unsafe or out-of-scope links, remote or unapproved Markdown images, unapproved raw HTML, GitHub-hosted URLs, and privacy-audit findings. It prints a content-set SHA-256 digest; preserve that digest through a trusted channel and supply it during independent verification.<br>
导出前必须先提交全部预定公开修改，并且只能从全新、经过复核且干净的 checkout 或同等可信的 CI checkout 执行正式发布。内容 blob 来自所选提交，但实际执行的导出器及其导入的审计代码来自当前 checkout。导出器仅支持 POSIX 系统；遇到符号链接、gitlink、Git LFS 指针、未经批准的二进制或非 UTF-8 内容、不安全或超出白名单的链接、远程或未经批准的 Markdown 图片、未批准原始 HTML、GitHub 托管地址或隐私审计问题时，都会拒绝导出。它会输出内容集 SHA-256 摘要；应通过可信渠道另行保存该摘要，并在独立复核时传入。

```bash
python3 scripts/export_publication.py export \
  --ref HEAD \
  --output /tmp/project-covenant-public

python3 scripts/export_publication.py verify \
  --input /tmp/project-covenant-public \
  --expected-content-set-sha256 DIGEST_FROM_EXPORT
```

The static-site builder consumes the immutable bytes returned by snapshot verification; it does not reread Markdown paths after validation. It produces exactly one HTML page per approved Markdown page plus one local stylesheet and approved local assets, then compares the complete output against a deterministic reconstruction. The site omits the source allowlist, integrity manifests, checksums, scripts, tests, workflows, Git data, and source digest.<br>
静态站点构建器只使用快照验证返回的不可变字节，不会在验证后重新读取 Markdown 路径。它为每份获准 Markdown 生成一个 HTML 页面及一份本地样式表与获准本地素材，再把完整输出与确定性重建结果逐字节比较。站点不会包含源白名单、完整性清单、校验和、脚本、测试、workflow、Git 数据或源摘要。

Snapshot and site directories, the ZIP output parent, and the final archive path must be under the exclusive control of the trusted build job while they are checked. Do not verify in a shared writable directory or publish by recursively copying a directory that may have changed afterward. Upload the just-built, just-verified site files, or create the offline ZIP directly from the same verified snapshot and retained digest, in the same trusted job. A filesystem verifier cannot prevent another process from changing a mutable path after verification returns.<br>
快照目录、站点目录、ZIP 输出父目录及最终压缩包路径在检查期间都必须由可信构建任务独占控制。不得在多方可写目录中验证，也不得递归复制可能在验证后已变化的目录进行发布。应在同一个可信任务中上传刚构建、刚验证的站点文件，或直接从同一份已验证快照及另行保存的摘要创建离线 ZIP。文件系统验证器无法阻止其他进程在验证返回后再修改一个可变路径。

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

The offline packager regenerates the expected static site directly from the verified snapshot and writes a deterministic, uncompressed ZIP with fixed paths, timestamps, and file modes. Verification requires the ZIP to match those expected bytes exactly, so added files, removed pages, changed HTML, path traversal entries, or altered metadata fail closed. Generate it outside the repository and distribute the printed SHA-256 digest through a trusted channel.<br>
离线打包器会直接从已验证快照重新生成预期静态站点，并写出路径、时间戳和文件模式均固定的确定性未压缩 ZIP。验证要求 ZIP 与预期字节完全一致，因此增加文件、删除页面、修改 HTML、路径穿越条目或改动元数据都会被拒绝。离线包必须在仓库外生成，并应通过可信渠道另行提供脚本输出的 SHA-256 摘要。

These commands verify static files only. At deployment, separately require HTTPS and review response headers such as `Content-Security-Policy` with `frame-ancestors 'none'`, `X-Content-Type-Options: nosniff`, and `Referrer-Policy: no-referrer`; `frame-ancestors` cannot be enforced by an HTML meta tag. Do not describe hosting security as verified until the live response headers have been tested.<br>
以上命令只验证静态文件。部署时还必须单独要求 HTTPS，并复核响应头，例如带有 `frame-ancestors 'none'` 的 `Content-Security-Policy`、`X-Content-Type-Options: nosniff` 和 `Referrer-Policy: no-referrer`；HTML meta 标签无法强制执行 `frame-ancestors`。在实际响应头经过测试前，不得把托管安全写成已验证。

The current export, build, package, and verification workflow is POSIX-only. For the provider-neutral deployment sequence and live acceptance boundary, see [Static Mirror Deployment | 静态镜像部署](./STATIC_MIRROR_DEPLOYMENT.md).

当前的导出、构建、打包与验证流程仅支持 POSIX 系统。与托管商无关的部署顺序及线上验收边界见[静态镜像部署](./STATIC_MIRROR_DEPLOYMENT.md)。

The clean snapshot removes Git history from the files being transferred; it does **not** anonymize the account that uploads it. An identity-minimized public release requires a reviewed neutral owner, a new non-fork repository, and one clean import made with neutral Git author **and committer** metadata. Do not mirror, fork, merge, or push this repository's existing history into that destination. After import, inspect both identities with `git log --format='%an <%ae> | %cn <%ce>'`, and push only from the neutral hosting account.<br>
干净快照会从待转移文件中去掉 Git 历史，但**不会**把上传它的账号变成匿名账号。若要尽量降低身份关联，公开版必须使用经过复核的中性所有者、全新且非 fork 的仓库，并以中性的 Git author 与 committer 元数据做一次干净导入。不得向该目标镜像、fork、合并或推送本仓库的旧历史。导入后要用 `git log --format='%an <%ae> | %cn <%ce>'` 同时检查两种身份，并且只能由中性托管账号推送。

Identical public text can still be linked back to an older repository by distinctive phrases or content hashes. If unlinkability from the current owner is required, do not publish the neutral snapshot while this source repository and its old history remain public; make the source private before release and assume that earlier public copies, caches, or forks may persist. A clean mirror reduces exposed metadata but cannot guarantee anonymity.<br>
相同的公开文字仍可能通过独特句子或内容哈希关联回旧仓库。若目标还包括切断与当前所有者的关联，就不能在本源仓库及旧历史仍公开时发布中性快照；正式发布前应先把源仓库设为私有，并假定此前的公开副本、缓存或 fork 仍可能留存。干净镜像只能减少暴露的元数据，不能保证匿名。

The neutral destination is a generated reading mirror, not the maintenance source. Do not edit it directly. Export, audit, test, and deployment commands run in the reviewed maintenance checkout or in separately reviewed infrastructure; the Markdown snapshot intentionally contains no scripts, tests, or workflow files. A later contributor-facing repository requires a separate privacy design rather than recursively copying this source repository.<br>
中性目标是生成的阅读镜像，不是维护源仓库，不得直接编辑。导出、审计、测试和部署命令应在经过复核的维护工作区或单独审核的基础设施中运行；Markdown 快照会有意不包含脚本、测试和 workflow 文件。若以后要建立面向贡献者的仓库，需要另行设计隐私边界，不得递归复制本源仓库。

## Future Website Boundary | 未来网站的发布边界

The future website must read only the exact files listed in `publication/site-content.txt`. It must never copy the repository recursively. Files not on the list are excluded from the website by default; if they are tracked in this public repository, they are still readable on GitHub.<br>
未来网站只能读取 `publication/site-content.txt` 明确列出的文件，绝不能递归复制整个仓库。未列入清单的文件默认不进入网站；若这些文件已被公开仓库跟踪，它们仍可在 GitHub 上阅读。

Inclusion in the list means that a page has passed the privacy and link-boundary review; it does not by itself mean that full bilingual migration is complete. The website must show the language status stated by the library hubs and must never label a Chinese-body research dossier as fully bilingual.<br>
列入清单表示页面已经通过隐私与链接边界复核，并不表示完整双语迁移已经完成。网站必须显示资料导航页标注的语言状态，也不得把中文正文研究专题标成“完整双语”。

Generated pages must be scanned again before deployment. Source maps, image metadata, build logs, hidden drafts, and machine-specific or identifying local filesystem paths must not enter the deployed artifact.<br>
生成的网站页面必须在部署前再次扫描。Source map、图片元数据、构建日志、隐藏草稿，以及机器特定或可识别身份的本机文件路径都不得进入部署产物。

The initial renderer must disable executable or template-like Markdown features such as MDX, Liquid, untrusted front matter, diagram scripting, and arbitrary raw HTML. Audit the final HTML, outbound links, resource requests, and deployed file set—not only the source Markdown.<br>
初版渲染器必须关闭 MDX、Liquid、不可信 front matter、图表脚本和任意原始 HTML 等可执行或模板化 Markdown 功能。审核对象不能只有 Markdown 源文件，还必须包括最终 HTML、外链、资源请求和实际部署文件集。

The initial website should avoid analytics, comments, forms, remote fonts, remote images, source maps, and links back to an identifying source repository. Those features may be added only after a separate privacy review of the data they transmit and the metadata they expose.<br>
网站初版应避免分析跟踪、评论、表单、远程字体、远程图片、source map，以及指回可识别源仓库的链接。只有在单独复核这些功能传输的数据和暴露的元数据后，才可以添加。

## Git Hosting Metadata | Git 托管元数据

Content review does not hide repository ownership, commit author names, commit email addresses, forks, pull requests, or other hosting metadata. The page-content rule does not promise anonymity for the repository or its hosting account; optional identity-minimized mirrors follow the separate guidance above.<br>
内容审核不会隐藏仓库所有权、提交作者姓名、提交邮箱、fork、pull request 或其他托管平台元数据。页面内容规则不承诺仓库或托管账号匿名；可选的身份关联最小化镜像遵循上文的单独说明。
