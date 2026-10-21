# Maps | 地图

> Status: Draft (AI draft; not human reviewed) | 状态：Draft（AI 草稿，未人工审阅）

<a id="maps-index"></a>
## Map Index | 地图索引

These locally generated maps support reading the Gospels and Acts. They work without internet access, map tiles, scripts, or downloaded fonts. On a narrow screen, scroll inside the map or open its SVG link at full size. / 本地生成的地图辅助福音书与使徒行传阅读，不需要网络、地图瓦片、脚本或下载字体。窄屏可在图内横向滚动，或打开完整 SVG。

| Map / 地图 | Read alongside / 配套阅读 |
| --- | --- |
| [Palestine in the Time of Jesus / 耶稣时代的巴勒斯坦](../assets/maps/palestine-jesus.svg) | [New Testament Timeline / 新约时间线](../Bible_Timeline/New_Testament_Timeline_Bilingual.md#gospel-map) |
| [Paul's Missionary Journeys / 保罗的宣教旅程](../assets/maps/paul-journeys.svg) | [Acts and Paul / 使徒行传与保罗书信](../Bible_Timeline/使徒行传与保罗书信_旅程年代与城市史料对照.md#journey-map) |

<a id="gospel-geography"></a>
## Gospel Geography | 福音书地理

![Palestine in the Time of Jesus, with bilingual regions and places / 耶稣时代的巴勒斯坦，附双语区域与地名](../assets/maps/palestine-jesus.svg)

Galilee / 加利利; Samaria / 撒玛利亚; Judaea / 犹太; Perea / 比利亚; Decapolis area / 低加波利区域. Selected places include Nazareth / 拿撒勒, Bethlehem / 伯利恒, Capernaum / 迦百农, Jerusalem / 耶路撒冷, and Jericho / 耶利哥.

**Approximate / 示意:** Colored envelopes are teaching sketches, not surveyed administrative borders. The Decapolis was a network of cities, including Scythopolis west of the Jordan, rather than one continuous province. Cana has competing identifications; the plotted point follows the selected legacy dataset and is not a verdict on that debate. Modern lake and coastal outlines do not reconstruct first-century shorelines. / 色块是教学示意范围，不是测绘的行政边界。低加波利是包括约旦河西斯基泰城在内的城邦网络，并非连续行省。迦拿有不同候选位置，图中采用所选旧数据的代表点，不裁定争议。现代湖岸及海岸轮廓不重建一世纪岸线。

<a id="paul-geography"></a>
## Paul's Journeys | 保罗的旅程

![Paul's three missionary journeys and voyage to Rome, in four bilingual panels / 保罗三次宣教与赴罗马路线，四个双语分图](../assets/maps/paul-journeys.svg)

| Route / 路线 | Line style / 线型 | Text / 经文 |
| --- | --- | --- |
| First journey / 第一次 | Solid / 实线 | Acts 13–14 / 使徒行传 13–14 |
| Second journey / 第二次 | Dashed / 虚线 | Acts 15:36–18:22 / 徒 15:36–18:22 |
| Third journey / 第三次 | Dotted / 点线 | Acts 18:23–21:16 / 徒 18:23–21:16 |
| Voyage to Rome / 前往罗马 | Dash-dot / 点划线 | Acts 27–28 / 使徒行传 27–28 |

**Approximate / 示意:** Lines connect selected named places rather than reconstructing ancient roads or exact sea tracks. The route through Phrygia and Galatia and the identification of Derbe remain debated; omitted intermediate stops are not claims that Paul bypassed them. The Malta point represents the island, not an identified shipwreck site; its landing bay and the exact storm-driven track are uncertain. / 连线连接选定地点，不重建古道或精确航迹。弗吕家与加拉太的经过路线、特庇的遗址认定仍有争议；省略中途地点不代表保罗未曾经过。马耳他点只代表岛屿，不是已确认的沉船点；登陆湾及风暴中的精确航迹仍不确定。

<a id="map-sources"></a>
## Sources and Reproduction | 来源与重现

Made with Natural Earth (public domain) and selected OpenBible.info coordinates (CC BY 4.0). Labels, teaching envelopes, routes, and layout were assembled for this library without copying or tracing a published map. See [Credits and Licenses](../CREDITS.md#map-data) for source links, changes, and attribution. / 底图为公有领域 Natural Earth，选用 OpenBible.info 的 CC BY 4.0 坐标。双语标注、教学范围、路线与版面为本资料库自行组合，没有复制或描摹出版地图；来源、修改及署名见[资料与授权](../CREDITS.md#map-data)。

Regenerate with the standard-library command `python3 scripts/generate_maps.py`; verify with `python3 scripts/generate_maps.py --check`. The committed geographic subsets make this repeatable offline. / 用上述标准库命令重新生成或检查；已提交的地理子集让重现过程可以完全离线。

[Back to Project Covenant | 返回首页](../README.md)
