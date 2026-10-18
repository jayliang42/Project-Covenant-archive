# Credits and Licenses | 资料来源与授权

> Status: Draft (AI draft; not human reviewed) | 状态：Draft（AI 草稿，未人工审阅）

<a id="credits-index"></a>
## Contents | 目录

- [Map data | 地图数据](#map-data)
- [Public-domain artworks | 公有领域画作](#artworks)
- [52-week artwork uses | 52周计划配图](#year-plan-artworks)
- [Second-batch map data | 第二批地图数据](#batch2-map-data)
- [Preparation and rights boundary | 处理与权利边界](#preparation)

<a id="map-data"></a>
## Map Data | 地图数据

Official license pages and the first three artwork file pages were opened and checked on 2026-10-17. Only the sources listed here are used in this pilot. / 已于 2026-10-17 打开并核查官方授权页及三张作品文件页；本试点只使用下列来源。

| Source / 来源 | License and official page / 授权及官方页面 | Attribution and modifications / 署名及修改 |
| --- | --- | --- |
| Natural Earth, 1:10m land 5.1.1 and lakes 5.0.0 / 陆地与湖泊 | Public domain / 公有领域; [official terms / 官方条款](https://www.naturalearthdata.com/about/terms-of-use/); [land / 陆地](https://www.naturalearthdata.com/downloads/10m-physical-vectors/10m-land/), [lakes / 湖泊](https://www.naturalearthdata.com/downloads/10m-physical-vectors/10m-lakes/) | Attribution is not required; voluntarily credited as “Made with Natural Earth.” Clipped to 11–38.5°E, 30–43.5°N, topology-preserving simplification at 0.008°, rounded to five decimals. / 无强制署名要求，仍自愿署名；已裁切、保拓扑简化并保留五位小数。 |
| OpenBible.info, Bible Geocoding legacy merged dataset / 圣经地理旧版合并数据 | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/); [official permission section / 官方授权说明](https://www.openbible.info/geo/); [legacy coordinate export / 旧版坐标导出](https://www.openbible.info/geo/data/merged.txt) | Credit OpenBible.info, link the license, and identify changes. Selected coordinate records were rounded to six decimals; English/Chinese labels, schematic regions, and itinerary connections were added. Only point records from this legacy export are used, not its photos or modern polygon datasets. / 按要求署名、链接许可证并说明修改；选定点坐标保留六位小数，新增双语标注、区域与行程示意，不使用照片或现代多边形数据。 |

The two generated map layouts are original compositions released under CC BY 4.0. Natural Earth data remain public domain; coordinate attribution remains attached. The generator is repository software under the MIT License. No ESV, Logos, BibleProject, or other published map was copied or traced. / 两幅生成地图的原创版面采用 CC BY 4.0；Natural Earth 数据保留公有领域状态，坐标署名随图保留；生成脚本遵循仓库软件的 MIT License。未复制或描摹任何出版地图。

<a id="batch2-map-data"></a>
## Second-Batch Map Data | 第二批地图数据

The official Natural Earth, OpenBible, CC BY 4.0, OpenStreetMap copyright, and ODbL 1.0 pages were opened before use on 2026-10-17. The new Natural Earth land/lake subset covers 23–74°E, 21–44°N, simplified at 0.02° and rounded to five decimals; the first pilot subset is unchanged. / 已于2026-10-17在使用前打开上述官方授权页。新增Natural Earth陆地与湖泊子集为东经23–74°、北纬21–44°，按0.02°简化并保留五位小数；第一批子集未改。

Selected legacy OpenBible records retain CC BY 4.0 attribution. Seven modern candidate POINT records come from the officially linked Matthew, John and Exodus KML exports, with OpenBible.info attribution; no KML scripture, photographs, polygon buffers, hillshading, maps or tiles are copied. Some coordinate sources include OpenStreetMap, so the modern-point extract below and its database rights retain [ODbL 1.0](https://opendatacommons.org/licenses/odbl/1-0/), with **© OpenStreetMap contributors** and the [official copyright link](https://www.openstreetmap.org/copyright). / 旧版点记录保留CC BY 4.0署名。七个现代候选点来自官方链接的马太、约翰与出埃及记KML，仅提取Point坐标并署名OpenBible.info；不复制经文、照片、多边形缓冲区、晕渲、地图或瓦片。部分坐标来源包含OpenStreetMap，因此下列现代点提取及其数据库权利保留ODbL 1.0、贡献者署名和官方版权链接。

The complete modified modern-point extract is provided in this table, freely available under ODbL 1.0; OpenBible’s source attribution and CC BY 4.0 notice remain attached. English/Chinese labels, six-decimal rounding, teaching areas, and route connections are modifications. The original SVG composition is CC BY 4.0 as a produced map; database rights remain source-specific. / 本表给出完整现代点提取，可按ODbL 1.0免费取得；同时保留OpenBible来源署名与CC BY 4.0说明。双语标注、六位小数取整、教学范围和路线连接属于修改。原创SVG版面作为制图作品采用CC BY 4.0，数据库权利仍按来源保留。

| Point / 地点 | Latitude / 纬度 | Longitude / 经度 | Official source / 官方来源 |
| --- | --- | --- | --- |
| Gethsemane / 客西马尼（传统地点） | 31.779419 | 35.239425 | [OpenBible KML](https://a.openbible.info/geo/kmls/matt.kml) — Gethsemane |
| Pool of Siloam / 西罗亚池 | 31.770556 | 35.235000 | [OpenBible KML](https://a.openbible.info/geo/kmls/john.kml) — Siloam / Pool of Siloam |
| Holy Sepulchre (A) / 圣墓教堂 A（传统／有争议） | 31.778444 | 35.229750 | [OpenBible KML](https://a.openbible.info/geo/kmls/john.kml) — Golgotha / Church of the Holy Sepulchre |
| Skull Hill / Garden Tomb (B) / 髑髅山／花园墓附近 B（有争议） | 31.783957 | 35.230147 | [OpenBible KML](https://a.openbible.info/geo/kmls/john.kml) — Golgotha / Gordon’s Calvary |
| Taylor proposal (C) / Taylor 提议 C（有争议） | 31.776629 | 35.230688 | [OpenBible KML](https://a.openbible.info/geo/kmls/john.kml) — Golgotha / Taylor Golgotha |
| Jebel Musa? / 穆萨山？（传统认定） | 28.539722 | 33.973333 | [OpenBible KML](https://a.openbible.info/geo/kmls/exod.kml) — Mount Sinai / Jebel Musa |
| Har Karkom? / 哈尔卡尔科姆山？（另一假说） | 30.283333 | 34.750000 | [OpenBible KML](https://a.openbible.info/geo/kmls/exod.kml) — Mount Sinai / Har Karkom |

Empire and kingdom envelopes, the Kidron course, the Temple Mount sketch and journey connections are original editorial approximations, not licensed claims of precise ancient borders or roads. Historical explanations are linked from the map index. The storyline graphic uses the library’s draft timelines and marks unresolved or undated stages; it is not a proportional timescale. / 帝国与王国色块、汲沦溪谷、圣殿山范围和行程连接是原创教学示意，不表示掌握精确古代边界或道路；历史说明见地图索引。故事线图依据本库草稿时间线，标出未定年及争议阶段，不按时间比例。

<a id="artworks"></a>
## Public-Domain Artworks | 公有领域画作

These are faithful reproductions of two-dimensional artworks. The first three linked Commons pages mark the artwork public domain by expired copyright (life plus 100 years and expired U.S. publication copyright), and the reproduction as PD-Art; [Public Domain Mark 1.0](https://creativecommons.org/publicdomain/mark/1.0/) describes that status rather than granting a new copyright license. Credit is supplied for provenance. / 这些是二维作品的忠实复制。第一批三张文件页标明原作因著作权期满属于公有领域，复制件标为 PD-Art；公有领域标记描述权利状态，不是重新授予版权许可。这里保留署名以说明来源。

| Local file / 本地文件 | Artist / 作者 | Work / 作品 | Year / 年份 | Source / 来源 | Status / 权利状态 |
| --- | --- | --- | --- | --- | --- |
| [dore-creation.jpg](./assets/illustrations/dore-creation.jpg) | Gustave Doré | *The Creation of Light* / 《创造之光》 | 1866 | [Commons file page / 文件页](https://commons.wikimedia.org/wiki/File:001.The_Creation_of_Light.jpg) | Public domain: PD-old-100-expired; PD-Art / 公有领域 |
| [dore-moses.jpg](./assets/illustrations/dore-moses.jpg) | Gustave Doré | *Moses Comes Down from Mount Sinai* / 《摩西从西乃山下来》 | 1866 | [Commons file page / 文件页](https://commons.wikimedia.org/wiki/File:039.Moses_Comes_Down_from_Mount_Sinai.jpg) | Public domain: PD-old-100-expired; PD-Art / 公有领域 |
| [tissot-resurrection.jpg](./assets/illustrations/tissot-resurrection.jpg) | James Tissot | *The Resurrection* / 《复活》 | 1886–1894 | [Commons file page / 文件页](https://commons.wikimedia.org/wiki/File:Brooklyn_Museum_-_The_Resurrection_(La_R%C3%A9surrection)_-_James_Tissot.jpg) | Public domain: PD-old-100-expired; PD-Art / 公有领域 |


Second-batch file pages were individually opened on 2026-10-17. Five Doré files and Tissot’s *Journey of the Magi* are marked PD-old-100-expired; the Paul and New Jerusalem files are marked PD-old-70-expired, with expired U.S. publication copyright. Candidates marked only “no known copyright restrictions,” or with disputed licensing, were not used. / 第二批文件页已于2026-10-17逐张打开；五幅Doré及Tissot的《博士的旅程》标为PD-old-100-expired，保罗和新耶路撒冷两幅标为PD-old-70-expired，均标明美国出版版权期满。仅标“未发现版权限制”或授权有争议的候选图未使用。

| Local file / 本地文件 | Artist / 作者 | Work / 作品 | Year / 年份 | Source and status / 来源与状态 | Bytes / 字节 |
| --- | --- | --- | --- | --- | --- |
| [dore-fall.jpg](./assets/illustrations/dore-fall.jpg) | Gustave Doré | Adam and Eve Are Driven out of Eden / 亚当和夏娃离开伊甸园 | 1866 | [Commons](https://commons.wikimedia.org/wiki/File:003.Adam_and_Eve_Are_Driven_out_of_Eden.jpg); Public domain; PD-old-100-expired; PD-Art | 291,934 |
| [dore-abraham.jpg](./assets/illustrations/dore-abraham.jpg) | Gustave Doré | Abraham Goes to the Land of Canaan / 亚伯拉罕前往迦南 | 1866 | [Commons](https://commons.wikimedia.org/wiki/File:011.Abraham_Goes_to_the_Land_of_Canaan.jpg); Public domain; PD-old-100-expired; PD-Art | 290,033 |
| [dore-kingdom.jpg](./assets/illustrations/dore-kingdom.jpg) | Gustave Doré | Cedars Are Cut Down for the Jerusalem Temple / 为耶路撒冷圣殿砍伐香柏木 | 1866 | [Commons](https://commons.wikimedia.org/wiki/File:085.Cedars_Are_Cut_Down_for_the_Jerusalem_Temple.jpg); Public domain; PD-old-100-expired; PD-Art | 284,557 |
| [dore-return.jpg](./assets/illustrations/dore-return.jpg) | Gustave Doré | The Rebuilding of the Temple Is Begun / 开始重建圣殿 | 1866 | [Commons](https://commons.wikimedia.org/wiki/File:105.The_Rebuilding_of_the_Temple_Is_Begun.jpg); Public domain; PD-old-100-expired; PD-Art | 283,016 |
| [dore-between-testaments.jpg](./assets/illustrations/dore-between-testaments.jpg) | Gustave Doré | Mattathias Appeals to the Jewish Refugees / 玛他提亚向犹太避难者讲话 | 1866 | [Commons](https://commons.wikimedia.org/wiki/File:142.Matthias_Appealing_to_Jewish_Refugees.jpg); Public domain; PD-old-100-expired; PD-Art | 289,495 |
| [tissot-magi.jpg](./assets/illustrations/tissot-magi.jpg) | James Tissot | Journey of the Magi / 博士的旅程 | c. 1894 | [Commons](https://commons.wikimedia.org/wiki/File:James_Tissot_-_Journey_of_the_Magi_-_70.21_-_Minneapolis_Institute_of_Arts.jpg); Public domain; PD-old-100-expired; PD-Art | 289,152 |
| [dore-church.jpg](./assets/illustrations/dore-church.jpg) | Gustave Doré | Paul Preaching to the Thessalonians / 保罗向帖撒罗尼迦人传讲 | 1866 | [Commons](https://commons.wikimedia.org/wiki/File:DoreStPaulPreachingtotheThessalonians.jpg); Public domain; PD-old-70-expired | 169,291 |
| [dore-new-creation.jpg](./assets/illustrations/dore-new-creation.jpg) | Gustave Doré | The New Jerusalem / 新耶路撒冷 | 1866 series; file-page copy date 1890 | [Commons](https://commons.wikimedia.org/wiki/File:Dore_nwe_jeruzalem_grt.jpg); Public domain; PD-old-70-expired | 160,393 |

*The New Jerusalem* belongs to Doré’s Bible illustration series, but its file page dates the reproduction 1890, after the artist’s death; that metadata is not treated as the engraving’s creation date and is flagged for human review. The ten-stop sequence reuses the first pilot’s creation and Moses engravings, adds seven Doré works and one Tissot work, and avoids a frontal portrait of Jesus. / 《新耶路撒冷》属于Doré圣经插图系列，但文件页把复制件记为作者去世后的1890年；此元数据不作为原版画创作日期，并列入人工核查。十站沿用第一批创造与摩西两幅，新增七幅Doré与一幅Tissot，不选择以耶稣正面面容为主体的作品。

All eight additions are baseline JPEGs below 300,000 bytes, at most 1,200 pixels on the long edge; dense engravings may be reduced to 1,000 or 800 pixels to meet the cap. EXIF, ICC, IPTC and comments are removed. No original is cropped, and no AI image is used. / 八张新增图片均为低于300,000字节的基线JPEG，长边不超过1200像素；细密版画可缩至1000或800像素以符合上限。已清除EXIF、ICC、IPTC与注释，未裁剪原图，也未使用AI图片。

<a id="year-plan-artworks"></a>
## Artwork Uses in the 52-Week Plan | 52周计划配图记录

These ten existing files were individually rechecked on their Wikimedia Commons file pages on 2026-10-18. The author, work, year, source and public-domain tags remain in the artwork tables above; this table records their additional uses. Nine works are by Doré and one by Tissot. No new image binary was added or modified.<br>
这十个既有文件的Wikimedia Commons文件页已于2026年10月18日逐张重新核对。作者、作品、年份、来源及公有领域标签见上方逐图记录；下表补充新增使用位置。九幅为Doré，一幅为Tissot；没有新增或修改图像文件。

| Week / 周次 | Scene / 场景 | Local file / 本地文件 | Rechecked file page / 复核文件页 |
| --- | --- | --- | --- |
| [1](./Bible_Timeline/52周圣经故事线_查经与史料阅读计划.md#week-01) | Creation / 创造 | [dore-creation.jpg](./assets/illustrations/dore-creation.jpg) | [Commons](https://commons.wikimedia.org/wiki/File:001.The_Creation_of_Light.jpg); Public domain; PD-old-100-expired; faithful 2D reproduction (PD-Art) |
| [2](./Bible_Timeline/52周圣经故事线_查经与史料阅读计划.md#week-02) | Leaving Eden / 离开伊甸 | [dore-fall.jpg](./assets/illustrations/dore-fall.jpg) | [Commons](https://commons.wikimedia.org/wiki/File:003.Adam_and_Eve_Are_Driven_out_of_Eden.jpg); Public domain; PD-old-100-expired; PD-Art |
| [3](./Bible_Timeline/52周圣经故事线_查经与史料阅读计划.md#week-03) | Abraham’s call and journey / 亚伯拉罕蒙召与迁行 | [dore-abraham.jpg](./assets/illustrations/dore-abraham.jpg) | [Commons](https://commons.wikimedia.org/wiki/File:011.Abraham_Goes_to_the_Land_of_Canaan.jpg); Public domain; PD-old-100-expired; PD-Art |
| [7](./Bible_Timeline/52周圣经故事线_查经与史料阅读计划.md#week-07) | Sinai and the law / 西奈与律法 | [dore-moses.jpg](./assets/illustrations/dore-moses.jpg) | [Commons](https://commons.wikimedia.org/wiki/File:039.Moses_Comes_Down_from_Mount_Sinai.jpg); Public domain; PD-old-100-expired; faithful 2D reproduction (PD-Art) |
| [15](./Bible_Timeline/52周圣经故事线_查经与史料阅读计划.md#week-15) | Preparing the temple / 预备建殿 | [dore-kingdom.jpg](./assets/illustrations/dore-kingdom.jpg) | [Commons](https://commons.wikimedia.org/wiki/File:085.Cedars_Are_Cut_Down_for_the_Jerusalem_Temple.jpg); Public domain; PD-old-100-expired; PD-Art |
| [27](./Bible_Timeline/52周圣经故事线_查经与史料阅读计划.md#week-27) | Return and rebuilding / 归回与重建 | [dore-return.jpg](./assets/illustrations/dore-return.jpg) | [Commons](https://commons.wikimedia.org/wiki/File:105.The_Rebuilding_of_the_Temple_Is_Begun.jpg); Public domain; PD-old-100-expired; PD-Art |
| [34](./Bible_Timeline/52周圣经故事线_查经与史料阅读计划.md#week-34) | The intertestamental setting / 两约之间的背景 | [dore-between-testaments.jpg](./assets/illustrations/dore-between-testaments.jpg) | [Commons](https://commons.wikimedia.org/wiki/File:142.Matthias_Appealing_to_Jewish_Refugees.jpg); Public domain; PD-old-100-expired; PD-Art |
| [35](./Bible_Timeline/52周圣经故事线_查经与史料阅读计划.md#week-35) | The Magi’s journey / 博士的旅程 | [tissot-magi.jpg](./assets/illustrations/tissot-magi.jpg) | [Commons](https://commons.wikimedia.org/wiki/File:James_Tissot_-_Journey_of_the_Magi_-_70.21_-_Minneapolis_Institute_of_Arts.jpg); Public domain; PD-old-100-expired; PD-Art |
| [45](./Bible_Timeline/52周圣经故事线_查经与史料阅读计划.md#week-45) | Witness in Thessalonica / 帖撒罗尼迦的见证 | [dore-church.jpg](./assets/illustrations/dore-church.jpg) | [Commons](https://commons.wikimedia.org/wiki/File:DoreStPaulPreachingtotheThessalonians.jpg); Public domain; PD-old-70-expired |
| [52](./Bible_Timeline/52周圣经故事线_查经与史料阅读计划.md#week-52) | New Jerusalem / 新耶路撒冷 | [dore-new-creation.jpg](./assets/illustrations/dore-new-creation.jpg) | [Commons](https://commons.wikimedia.org/wiki/File:Dore_nwe_jeruzalem_grt.jpg); Public domain; PD-old-70-expired |

The cedar-cutting file’s English description cites 2 Samuel 5, while its title and this plan’s temple-preparation use are associated here with the assigned 1 Kings 5 reading. That reference-tag difference remains for human review. The New Jerusalem file’s 1890 metadata remains a reproduction date rather than an established creation date. Neither picture is an archaeological reconstruction.<br>
香柏木文件的英文描述标注撒母耳记下五章；本计划按画题与建殿预备主题，将它配在包含列王纪上五章的指定阅读中。这个经文标签差异保留人工核对。《新耶路撒冷》的1890元数据仍按复制件日期处理，不当作已核定的创作年。两幅都不是考古复原图。

<a id="preparation"></a>
## Preparation and Rights Boundary | 处理与权利边界

The images were resized without cropping and re-encoded as baseline JPEG; EXIF, ICC, IPTC, comments, and original filenames were removed from image metadata. The first three pilot files are 275,148, 295,887, and 94,078 bytes respectively, each below 300,000 bytes. They are loaded locally with bilingual captions; no AI-generated images, remote image requests, or tracking scripts are used. / 图片未裁剪，只缩放并重新编码为基线 JPEG；图像元数据中的 EXIF、ICC、IPTC、注释及原文件名已清除。第一批三张分别为 275,148、295,887、94,078 字节，均低于 300,000 字节；本地加载并配双语图注，不使用 AI 图片、远程图片请求或跟踪脚本。

Check media with `python3 scripts/prepare_illustrations.py --check`. To repeat compression, install the optional preparation dependency from the repository's media requirements and run `python3 scripts/prepare_illustrations.py --source-dir DIRECTORY_OF_REVIEWED_ORIGINALS`. The source catalog is local maintenance data; only approved JPEG/SVG outputs and this credit page enter the website. / 可用上述命令检查图片；重做压缩时安装仓库可选媒体准备依赖，并提供已审查原图所在目录。来源目录记录属于本地维护数据，网站只收录获准 JPEG、SVG 与本署名页。

Art illustrates a reading theme and is not historical or archaeological evidence. These third-party works and datasets are not relicensed under the library's original-text license; preserve the source-specific notices when reusing them. / 画作只说明阅读主题，不是历史或考古证据；这些第三方作品与数据不按资料库原创文字许可证重新授权，再利用时须保留各来源说明。

[Maps | 地图](./Maps/README.md) · [Licensing | 授权说明](./LICENSE.md) · [Home | 首页](./README.md)
