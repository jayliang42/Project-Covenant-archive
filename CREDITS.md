# Credits and Licenses | 资料来源与授权

> Status: Draft (AI draft; not human reviewed) | 状态：Draft（AI 草稿，未人工审阅）

<a id="credits-index"></a>
## Contents | 目录

- [Map data | 地图数据](#map-data)
- [Public-domain artworks | 公有领域画作](#artworks)
- [Preparation and rights boundary | 处理与权利边界](#preparation)

<a id="map-data"></a>
## Map Data | 地图数据

Official license pages and all three artwork file pages were opened and checked on 2026-10-17. Only the sources listed here are used in this pilot. / 已于 2026-10-17 打开并核查官方授权页及三张作品文件页；本试点只使用下列来源。

| Source / 来源 | License and official page / 授权及官方页面 | Attribution and modifications / 署名及修改 |
| --- | --- | --- |
| Natural Earth, 1:10m land 5.1.1 and lakes 5.0.0 / 陆地与湖泊 | Public domain / 公有领域; [official terms / 官方条款](https://www.naturalearthdata.com/about/terms-of-use/); [land / 陆地](https://www.naturalearthdata.com/downloads/10m-physical-vectors/10m-land/), [lakes / 湖泊](https://www.naturalearthdata.com/downloads/10m-physical-vectors/10m-lakes/) | Attribution is not required; voluntarily credited as “Made with Natural Earth.” Clipped to 11–38.5°E, 30–43.5°N, topology-preserving simplification at 0.008°, rounded to five decimals. / 无强制署名要求，仍自愿署名；已裁切、保拓扑简化并保留五位小数。 |
| OpenBible.info, Bible Geocoding legacy merged dataset / 圣经地理旧版合并数据 | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/); [official permission section / 官方授权说明](https://www.openbible.info/geo/); [legacy coordinate export / 旧版坐标导出](https://www.openbible.info/geo/data/merged.txt) | Credit OpenBible.info, link the license, and identify changes. Selected coordinate records were rounded to six decimals; English/Chinese labels, schematic regions, and itinerary connections were added. Only point records from this legacy export are used, not its photos or modern polygon datasets. / 按要求署名、链接许可证并说明修改；选定点坐标保留六位小数，新增双语标注、区域与行程示意，不使用照片或现代多边形数据。 |

The two generated map layouts are original compositions released under CC BY 4.0. Natural Earth data remain public domain; coordinate attribution remains attached. The generator is repository software under the MIT License. No ESV, Logos, BibleProject, or other published map was copied or traced. / 两幅生成地图的原创版面采用 CC BY 4.0；Natural Earth 数据保留公有领域状态，坐标署名随图保留；生成脚本遵循仓库软件的 MIT License。未复制或描摹任何出版地图。

<a id="artworks"></a>
## Public-Domain Artworks | 公有领域画作

These are faithful reproductions of two-dimensional artworks. Each linked Commons page marks the artwork public domain by expired copyright (life plus 100 years and expired U.S. publication copyright), and the reproduction as PD-Art; [Public Domain Mark 1.0](https://creativecommons.org/publicdomain/mark/1.0/) describes that status rather than granting a new copyright license. Credit is supplied for provenance. / 这些是二维作品的忠实复制。各文件页标明原作因著作权期满属于公有领域，复制件标为 PD-Art；公有领域标记描述权利状态，不是重新授予版权许可。这里保留署名以说明来源。

| Local file / 本地文件 | Artist / 作者 | Work / 作品 | Year / 年份 | Source / 来源 | Status / 权利状态 |
| --- | --- | --- | --- | --- | --- |
| [dore-creation.jpg](./assets/illustrations/dore-creation.jpg) | Gustave Doré | *The Creation of Light* / 《创造之光》 | 1866 | [Commons file page / 文件页](https://commons.wikimedia.org/wiki/File:001.The_Creation_of_Light.jpg) | Public domain: PD-old-100-expired; PD-Art / 公有领域 |
| [dore-moses.jpg](./assets/illustrations/dore-moses.jpg) | Gustave Doré | *Moses Comes Down from Mount Sinai* / 《摩西从西乃山下来》 | 1866 | [Commons file page / 文件页](https://commons.wikimedia.org/wiki/File:039.Moses_Comes_Down_from_Mount_Sinai.jpg) | Public domain: PD-old-100-expired; PD-Art / 公有领域 |
| [tissot-resurrection.jpg](./assets/illustrations/tissot-resurrection.jpg) | James Tissot | *The Resurrection* / 《复活》 | 1886–1894 | [Commons file page / 文件页](https://commons.wikimedia.org/wiki/File:Brooklyn_Museum_-_The_Resurrection_(La_R%C3%A9surrection)_-_James_Tissot.jpg) | Public domain: PD-old-100-expired; PD-Art / 公有领域 |

<a id="preparation"></a>
## Preparation and Rights Boundary | 处理与权利边界

The images were resized without cropping and re-encoded as baseline JPEG; EXIF, ICC, IPTC, comments, and original filenames were removed from image metadata. The local files are 275,148, 295,887, and 94,078 bytes respectively, each below 300,000 bytes. They are loaded locally with bilingual captions; no AI-generated images, remote image requests, or tracking scripts are used. / 图片未裁剪，只缩放并重新编码为基线 JPEG；图像元数据中的 EXIF、ICC、IPTC、注释及原文件名已清除。三张分别为 275,148、295,887、94,078 字节，均低于 300,000 字节；本地加载并配双语图注，不使用 AI 图片、远程图片请求或跟踪脚本。

Check media with `python3 scripts/prepare_illustrations.py --check`. To repeat compression, install the optional preparation dependency from the repository's media requirements and run `python3 scripts/prepare_illustrations.py --source-dir DIRECTORY_OF_REVIEWED_ORIGINALS`. The source catalog is local maintenance data; only approved JPEG/SVG outputs and this credit page enter the website. / 可用上述命令检查图片；重做压缩时安装仓库可选媒体准备依赖，并提供已审查原图所在目录。来源目录记录属于本地维护数据，网站只收录获准 JPEG、SVG 与本署名页。

Art illustrates a reading theme and is not historical or archaeological evidence. These third-party works and datasets are not relicensed under the library's original-text license; preserve the source-specific notices when reusing them. / 画作只说明阅读主题，不是历史或考古证据；这些第三方作品与数据不按资料库原创文字许可证重新授权，再利用时须保留各来源说明。

[Maps | 地图](./Maps/README.md) · [Licensing | 授权说明](./LICENSE.md) · [Home | 首页](./README.md)
