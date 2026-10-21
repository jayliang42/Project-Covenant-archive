#!/usr/bin/env python3
"""Generate offline Bible maps and a storyline SVG from committed open-data subsets.

No network, image, font, or mapping-library dependency is needed. Use --check
to reject drift between the reviewed inputs and the committed SVG files.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import TypedDict, cast
import xml.etree.ElementTree as ET

if __package__:
    from .publication_assets import validate_svg
else:
    from publication_assets import validate_svg

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/maps"
OUTPUT = ROOT / "assets/maps"
ET.register_namespace("", "http://www.w3.org/2000/svg")
NS = "{http://www.w3.org/2000/svg}"
Point = tuple[float, float]
FONT_FAMILY = '"PingFang SC", "Microsoft YaHei", "Noto Sans CJK SC", sans-serif'


class Place(TypedDict):
    en: str
    zh: str
    lon: float
    lat: float
    source_key: str


class Route(TypedDict):
    id: str
    en: str
    zh: str
    references: str
    color: str
    dash: str
    extent: list[float]
    stops: list[str]


class Geography(TypedDict):
    places: dict[str, Place]
    routes: list[Route]


class Basemap(TypedDict):
    land: list[list[list[list[float]]]]
    lakes: list[list[list[list[float]]]]


def element(parent: ET.Element, tag: str, **attributes: object) -> ET.Element:
    return ET.SubElement(parent, NS + tag, {key.replace("_", "-"): str(value) for key, value in attributes.items()})


def label(parent: ET.Element, x: float, y: float, text: str, size: int = 18, **attributes: object) -> ET.Element:
    attributes.setdefault("fill", "#263b38")
    node = element(parent, "text", x=f"{x:.2f}", y=f"{y:.2f}", font_size=size, **attributes)
    node.text = text
    return node


class Frame:
    def __init__(self, extent: list[float], x: float, y: float, width: float, height: float):
        self.west, self.south, self.east, self.north = extent
        self.width, self.height = width, height
        self.cosine = math.cos(math.radians((self.north + self.south) / 2))
        self.scale = min(width / ((self.east - self.west) * self.cosine), height / (self.north - self.south))
        self.x = x + (width - (self.east - self.west) * self.cosine * self.scale) / 2
        self.y = y + (height - (self.north - self.south) * self.scale) / 2

    def point(self, lon: float, lat: float) -> Point:
        return self.x + (lon - self.west) * self.cosine * self.scale, self.y + (self.north - lat) * self.scale

    def contains(self, lon: float, lat: float) -> bool:
        return self.west <= lon <= self.east and self.south <= lat <= self.north


def clip_polygon(points: list[list[float]], frame: Frame) -> list[Point]:
    """Sutherland–Hodgman clipping against the geographic frame."""
    result = [(point[0], point[1]) for point in points]
    for axis, boundary, keep_larger in ((0, frame.west, True), (0, frame.east, False), (1, frame.south, True), (1, frame.north, False)):
        source, result = result, []
        if not source:
            break
        previous = source[-1]
        previous_inside = previous[axis] >= boundary if keep_larger else previous[axis] <= boundary
        for current in source:
            inside = current[axis] >= boundary if keep_larger else current[axis] <= boundary
            if inside != previous_inside:
                fraction = (boundary - previous[axis]) / (current[axis] - previous[axis])
                crossing = (previous[0] + fraction * (current[0] - previous[0]), previous[1] + fraction * (current[1] - previous[1]))
                result.append(crossing)
            if inside:
                result.append(current)
            previous, previous_inside = current, inside
    return [frame.point(*point) for point in result]


def draw_base(parent: ET.Element, frame: Frame, data: Basemap) -> None:
    for layer, fill in (("land", "#f2eee1"), ("lakes", "#dfedf0")):
        polygons = data["land"] if layer == "land" else data["lakes"]
        for polygon in polygons:
            paths: list[str] = []
            for ring in polygon:
                points = clip_polygon(ring, frame)
                if len(points) >= 3:
                    paths.append("M" + " L".join(f"{x:.2f},{y:.2f}" for x, y in points) + " Z")
            if paths:
                element(parent, "path", d=" ".join(paths), fill=fill, stroke="#718077", stroke_width="0.7", fill_rule="evenodd")


def compass_and_scale(parent: ET.Element, frame: Frame, x: float, y: float, km: float) -> None:
    length = km / 111.195 * frame.scale
    element(parent, "line", x1=x, y1=y, x2=x + length, y2=y, stroke="#263b38", stroke_width=3)
    for endpoint in (x, x + length):
        element(parent, "line", x1=endpoint, y1=y - 5, x2=endpoint, y2=y + 5, stroke="#263b38", stroke_width=2)
    latitude = (frame.north + frame.south) / 2
    label(parent, x, y + 24, f"{km} km · at {latitude:.1f}°N / 按中纬度", 15)
    arrow_x = x + length + 75
    element(parent, "line", x1=arrow_x, y1=y + 6, x2=arrow_x, y2=y - 28, stroke="#263b38", stroke_width=2)
    element(parent, "polygon", points=f"{arrow_x},{y-40} {arrow_x-6},{y-26} {arrow_x+6},{y-26}", fill="#263b38")
    label(parent, arrow_x + 10, y - 24, "N 北", 17)


def root_svg(title: str, description: str, width: int, height: int) -> ET.Element:
    root = ET.Element(NS + "svg", {"viewBox": f"0 0 {width} {height}", "width": str(width), "height": str(height), "role": "img", "aria-labelledby": "map-title map-description", "font-family": FONT_FAMILY})
    element(root, "title", id="map-title").text = title
    element(root, "desc", id="map-description").text = description
    element(root, "rect", width=width, height=height, fill="#fbfaf6")
    label(root, 40, 43, title, 27, font_weight="bold")
    label(root, 40, 77, "Draft · Approximate / 草稿 · 示意", 18)
    return root


def draw_places(parent: ET.Element, frame: Frame, places: dict[str, Place], names: list[str], font: int = 17, reserved: list[tuple[float, float, float, float]] | None = None) -> None:
    """Place labels on a collision-checked teaching diagram, with leader lines."""
    boxes = list(reserved or [])
    ordered = sorted(dict.fromkeys(names), key=lambda name: -max(len(places[name]["en"]) * 0.55, len(places[name]["zh"])))
    for name in ordered:
        place = places[name]
        x, y = frame.point(place["lon"], place["lat"])
        element(parent, "circle", cx=f"{x:.2f}", cy=f"{y:.2f}", r=4, fill="#263b38", stroke="#ffffff", stroke_width=1.4)
        width = max(len(place["en"]) * font * 0.55, len(place["zh"]) * font) + 5
        height = font * 2 + 8
        selected: tuple[float, float] | None = None
        for radius in (10, 25, 45, 65, 95, 125, 175):
            for dx, dy in ((radius, -height / 2), (-radius - width, -height / 2), (radius, -height - radius), (radius, radius), (-radius - width, radius), (-radius-width, -height-radius), (-width/2, -height-radius), (-width/2, radius)):
                left, top = x + dx, y + dy
                box = (left, top, left + width, top + height)
                if left < frame.x - 45 or top < frame.y - 8 or box[2] > frame.x + (frame.east-frame.west)*frame.cosine*frame.scale + 45 or box[3] > frame.y + (frame.north-frame.south)*frame.scale + 20:
                    continue
                if all(box[2] + 4 < b[0] or box[0] > b[2] + 4 or box[3] + 4 < b[1] or box[1] > b[3] + 4 for b in boxes):
                    selected = left, top
                    boxes.append(box)
                    break
            if selected is not None:
                break
        if selected is None:
            raise ValueError(f"Map label needs a larger frame: {name}")
        left, top = selected
        element(parent, "line", x1=f"{x:.2f}", y1=f"{y:.2f}", x2=f"{left:.2f}", y2=f"{top+font:.2f}", stroke="#7b8880", stroke_width=0.8)
        label(parent, left, top + font, place["en"], font, stroke="#fbfaf6", stroke_width=3, paint_order="stroke")
        label(parent, left, top + font * 2 + 3, place["zh"], font, stroke="#fbfaf6", stroke_width=3, paint_order="stroke")


def palestine(data: Basemap, geography: Geography) -> bytes:
    root = root_svg("Palestine in the Time of Jesus | 耶稣时代的巴勒斯坦", "Bilingual schematic of Galilee, Samaria, Judaea, Perea, the Decapolis area, and selected Gospel places; modern Natural Earth physical outlines. / 古代区域及福音书地点示意，采用现代自然地理轮廓。", 1000, 1240)
    frame = Frame([34.3, 31.1, 36.5, 33.45], 50, 120, 900, 880)
    x, y = frame.point(frame.west, frame.north)
    element(root, "rect", x=x, y=y, width=(frame.east-frame.west)*frame.cosine*frame.scale, height=(frame.north-frame.south)*frame.scale, fill="#dfedf0")
    draw_base(root, frame, data)
    regions = [
        ("Galilee", "加利利", "#c9d5aa", [(35.02,32.55),(35.6,32.55),(35.7,33.3),(35.25,33.34),(35.03,32.95)], (35.15,33.13)),
        ("Samaria", "撒玛利亚", "#e5c58d", [(34.85,32.05),(35.52,32.05),(35.55,32.55),(34.97,32.55)], (34.98,32.28)),
        ("Judaea", "犹太", "#d6b5aa", [(34.75,31.2),(35.5,31.2),(35.5,32.05),(34.85,32.05)], (34.9,31.5)),
        ("Perea", "比利亚", "#bfc1df", [(35.55,31.55),(35.95,31.55),(35.88,32.35),(35.55,32.4)], (35.72,31.93)),
        ("Decapolis area", "低加波利区域", "#c0d8d2", [(35.61,32.35),(36.35,32.35),(36.4,33.3),(35.7,33.3)], (35.98,32.98)),
    ]
    reserved: list[tuple[float, float, float, float]] = []
    for en, zh, fill, polygon, location in regions:
        points = [frame.point(*point) for point in polygon]
        element(root, "polygon", points=" ".join(f"{px:.2f},{py:.2f}" for px,py in points), fill=fill, fill_opacity=0.55, stroke="#5c5b50", stroke_width=1.5, stroke_dasharray="7 5")
        px, py = frame.point(*location)
        label(root, px, py, en, 23, text_anchor="middle", font_weight="bold")
        label(root, px, py+28, zh, 23, text_anchor="middle")
        region_width = max(len(en) * 13, len(zh) * 23)
        reserved.append((px-region_width/2-4, py-25, px+region_width/2+4, py+32))
    draw_places(root, frame, geography["places"], ["Nazareth","Bethlehem 1","Capernaum","Jerusalem","Jericho","Cana","Samaria","Beth-shan","Caesarea"], 19, reserved)
    compass_and_scale(root, frame, 85, 1050, 50)
    label(root, 40, 1130, "Regions are teaching envelopes, not surveyed administrative borders. / 区域是教学示意范围。", 18)
    label(root, 40, 1162, "Cana is disputed; Decapolis was a city network. / 迦拿位置有争议；低加波利是城邦网络。", 18)
    label(root, 40, 1194, "Made with Natural Earth · Place coordinates: OpenBible.info (CC BY 4.0)", 16)
    return ET.tostring(root, encoding="utf-8") + b"\n"


def paul(data: Basemap, geography: Geography) -> bytes:
    root = root_svg("Paul's Missionary Journeys | 保罗的宣教旅程", "Four schematic panels: three missionary journeys and the voyage to Rome, differentiated by solid, dashed, dotted, and dash-dot routes; locations approximate. / 四个分图以实线、虚线、点线及点划线区分三次宣教及前往罗马的路线。", 1480, 1540)
    for index, route in enumerate(geography["routes"]):
        x, y = 35 + (index % 2) * 730, 115 + (index // 2) * 680
        label(root, x, y, f"{route['en']} | {route['zh']}", 23, font_weight="bold")
        label(root, x, y + 29, route["references"], 17)
        frame = Frame(route["extent"], x+5, y+55, 680, 470)
        fx, fy = frame.point(frame.west, frame.north)
        element(root, "rect", x=fx, y=fy, width=(frame.east-frame.west)*frame.cosine*frame.scale, height=(frame.north-frame.south)*frame.scale, fill="#dfedf0", stroke="#b9c5be")
        draw_base(root, frame, data)
        points = [frame.point(geography["places"][name]["lon"], geography["places"][name]["lat"]) for name in route["stops"]]
        element(root, "polyline", points=" ".join(f"{px:.2f},{py:.2f}" for px,py in points), fill="none", stroke=route["color"], stroke_width=3, stroke_dasharray=route["dash"], stroke_linecap="round", stroke_linejoin="round")
        for a,b in zip(points, points[1:]):
            dx,dy=b[0]-a[0],b[1]-a[1]; length=math.hypot(dx,dy)
            if length < 22:
                continue
            ux,uy=dx/length,dy/length; mx,my=a[0]+dx*0.6,a[1]+dy*0.6
            triangle=[(mx+ux*5,my+uy*5),(mx-ux*5-uy*4,my-uy*5+ux*4),(mx-ux*5+uy*4,my-uy*5-ux*4)]
            element(root,"polygon",points=" ".join(f"{px:.2f},{py:.2f}" for px,py in triangle),fill=route["color"])
        draw_places(root, frame, geography["places"], route["stops"], 17)
        compass_and_scale(root, frame, x+25, y+575, 100 if index==0 else 300)
        label(root, x+25, y+635, "Routes approximate / 路线示意", 18, fill=route["color"])
    label(root, 40, 1490, "Regional travel and sea tracks are reconstructed schematically; no exact road or shipwreck is claimed. / 陆路与海路仅为示意。", 18)
    label(root, 40, 1520, "Made with Natural Earth · Place coordinates: OpenBible.info (CC BY 4.0) · Draft / 草稿", 17)
    return ET.tostring(root, encoding="utf-8") + b"\n"



def batch2_maps() -> dict[str, bytes]:
    """Original teaching diagrams from the separately credited point extract."""
    record = json.loads((DATA / "batch2-places.json").read_text(encoding="utf-8"))
    places = cast(dict[str, Place], record["places"])
    base = cast(Basemap, json.loads((DATA / "natural-earth-batch2.json").read_text(encoding="utf-8")))
    for place in places.values():
        if not (-180 <= place["lon"] <= 180 and -90 <= place["lat"] <= 90):
            raise ValueError("Invalid batch-two coordinate")
    results: dict[str, bytes] = {}

    def line(parent: ET.Element, frame: Frame, coords: list[Point], color: str, dash: str = "none") -> None:
        projected = [frame.point(*p) for p in coords]
        element(parent, "polyline", points=" ".join(f"{x:.2f},{y:.2f}" for x, y in projected), fill="none", stroke=color, stroke_width=4, stroke_dasharray=dash, stroke_linecap="round", stroke_linejoin="round")

    def coords(names: list[str]) -> list[Point]:
        return [(places[n]["lon"], places[n]["lat"]) for n in names]

    def panel(root: ET.Element, extent: list[float], x: float, y: float, width: float, height: float) -> Frame:
        frame = Frame(extent, x, y, width, height)
        fx, fy = frame.point(frame.west, frame.north)
        element(root, "rect", x=fx, y=fy, width=(frame.east-frame.west)*frame.cosine*frame.scale, height=(frame.north-frame.south)*frame.scale, fill="#dfedf0", stroke="#718077")
        draw_base(root, frame, base)
        return frame

    def finish(root: ET.Element, name: str, y: int, notes: list[str], modern: bool = False) -> None:
        for i, note in enumerate(notes):
            label(root, 40, y+i*30, note, 18)
        label(root, 40, y+len(notes)*30+4, "Made with Natural Earth · OpenBible.info (CC BY 4.0) · Draft / 草稿", 16)
        if modern:
            label(root, 40, y+len(notes)*30+30, "© OpenStreetMap contributors · ODbL 1.0 · https://www.openstreetmap.org/copyright", 16)
        results[name] = ET.tostring(root, encoding="utf-8") + b"\n"

    root = root_svg("Jerusalem in the Time of Jesus | 耶稣时代的耶路撒冷", "Schematic city locations, Kidron valley, and disputed crucifixion/burial proposals A, B and C. No first-century wall reconstruction. / 城内地点与受难、墓葬候选点示意，不重建一世纪城墙。", 1400, 1210)
    frame = panel(root, [35.222,31.767,35.253,31.789], 80,140,1240,760)
    temple = [frame.point(*p) for p in [(35.2337,31.7757),(35.2375,31.7757),(35.2375,31.7803),(35.2337,31.7803)]]
    element(root,"polygon",points=" ".join(f"{x:.2f},{y:.2f}" for x,y in temple),fill="#c9d5aa",fill_opacity=.6,stroke="#536b30",stroke_dasharray="8 5")
    line(root,frame,[(35.238,31.787),(35.2382,31.782),(35.2374,31.777),(35.236596,31.772134),(35.2373,31.768)],"#245d7a","7 5")
    draw_places(root, frame, places, ["Moriah","Mount of Olives","Gethsemane","Kidron","Siloam","Sepulchre","Garden","Taylor"], 22)
    compass_and_scale(root,frame,90,950,.2)
    finish(root,"jerusalem-jesus.svg",1030,["A: Holy Sepulchre tradition; B: Garden Tomb vicinity; C: Taylor proposal. / 三种提议。","Traditional locations / disputed · 传统位置／有争议；溪谷与圣殿范围仅示意。","A plotted point is not proof of a crucifixion site or tomb. / 坐标不能证明受难点或墓穴。"],True)

    root=root_svg("Abraham's Journey | 亚伯拉罕的旅程", "Genesis 11–13: southern Ur, Haran, Canaan and Egypt, with a Canaan detail panel. Routes and patriarchal chronology uncertain. / 创世记十一至十三章地点示意；道路、吾珥认定与族长年代未定。",1600,1160)
    label(root,40,115,"Regional connections | 区域联系",24,font_weight="bold")
    label(root,850,115,"Canaan detail | 迦南局部",24,font_weight="bold")
    frame=panel(root,[29,29,48,38],50,155,720,640)
    line(root,frame,[(46.103742,30.962052),(44.4,32.5),(42,35),(39.032197,36.863864),(35.281799,32.213691),(35.221033,31.930539),(31.338220,30.108086),(35.221033,31.930539),(35.094100,31.535774)],"#8a3324")
    draw_places(root,frame,places,["Ur","Haran","Egypt"],23)
    compass_and_scale(root,frame,70,855,300)
    frame=panel(root,[34.7,31.25,35.65,32.55],850,155,670,640)
    line(root,frame,coords(["Shechem","Bethel 1","Hebron"]),"#8a3324","10 6")
    draw_places(root,frame,places,["Shechem","Bethel 1","Hebron"],23)
    compass_and_scale(root,frame,870,855,25)
    finish(root,"abraham-journey.svg",955,["Genesis 11:31–13:18 / 创世记 11:31–13:18 · Connections approximate / 连线示意。","Southern Ur is one identification; Egypt is a regional marker, not a known campsite. / 吾珥认定、埃及停留点未定。","Lines are reading aids, not excavated roads. / 连线辅助阅读，不代表已发掘的道路。"])

    root=root_svg("Exodus: Two Route Models | 出埃及：两种路线模型", "Southern Sinai/Jebel Musa tradition alongside Anati's Har Karkom proposal. Both routes and locations disputed; not equal claims of archaeological proof. / 南部西奈传统与 Anati 的 Har Karkom 提议并列；路线和地点均有争议。",1600,1220)
    label(root,40,115,"A · Southern tradition / 南部传统",24,font_weight="bold",fill="#8a3324")
    label(root,840,115,"B · Har Karkom proposal / 另一提议",24,font_weight="bold",fill="#6c3c78")
    for i in range(2):
        x=50+i*790
        frame=panel(root,[31.3,27.9,35.5,31.2],x,165,710,640)
        if i==0:
            line(root,frame,[(31.834217,30.799370),(32.5,30.0),(32.8,29.6),(33.973333,28.539722),(34.494796,30.687713)],"#8a3324")
            names=["Rameses","Musa","Kadesh-barnea"]
        else:
            line(root,frame,[(31.834217,30.799370),(32.8,30.6),(33.8,30.4),(34.75,30.283333),(34.494796,30.687713)],"#6c3c78","12 7")
            names=["Rameses","Karkom","Kadesh-barnea"]
        draw_places(root,frame,places,names,22)
        compass_and_scale(root,frame,x+25,865,100)
    finish(root,"exodus-models.svg",970,["Routes AND locations disputed / 路线和地点均有争议 · Sea crossing location unresolved / 渡海地点未定。","A: southern Sinai tradition; B: Anati's published site hypothesis, not an established identification. / 两者均非定论。","Har Karkom's proposed chronology differs from 15th/13th-century models. / 该提议的年代与前十五／十三世纪模型不同。","Connections are original teaching sketches, not copied published itineraries. / 连线为自绘示意，不描摹出版路线。"],True)

    root=root_svg("The Divided Kingdoms | 王国分裂：北国与南国", "Illustrative Israel and Judah areas around the ninth century BCE, with major cities. Borders changed; no precise frontier claimed. / 前九世纪北国、南国与主要城市示意；边界会变动。",1400,1180)
    frame=panel(root,[34.3,30.9,36.1,33.55],70,140,1260,730)
    areas=[("#c9d5aa",[(34.85,31.9),(35.12,31.83),(35.55,31.87),(35.8,32.7),(35.6,33.4),(35.03,33.1),(34.85,32.3)]),("#d6b5aa",[(34.45,31.0),(35.55,31.0),(35.55,31.85),(35.15,31.83),(34.9,31.9),(34.5,31.5)])]
    for fill,polygon in areas:
        points=[frame.point(*p) for p in polygon]
        element(root,"polygon",points=" ".join(f"{x:.2f},{y:.2f}" for x,y in points),fill=fill,fill_opacity=.55,stroke="#5c5b50",stroke_width=2,stroke_dasharray="8 5")
    draw_places(root,frame,places,["Dan","Samaria","Tirzah","Megiddo","Shechem","Bethel 1","Jerusalem","Hebron","Beersheba","Lachish"],22)
    label(root,60,920,"Green: Israel / 绿色：北国以色列 · Rose: Judah / 玫色：南国犹大",23,font_weight="bold")
    compass_and_scale(root,frame,80,970,50)
    finish(root,"divided-kingdoms.svg",1050,["Ninth-century teaching areas; not the borders at the moment of division. / 前九世纪示意，不是分裂当刻的边界。","Samaria became a capital later; Tirzah marks an earlier center. / 撒玛利亚为后期都城，得撒为较早中心。"])

    root=root_svg("Empires in the Exile Story | 被掳时期的帝国", "Three separate period panels: Neo-Assyrian, Neo-Babylonian and Achaemenid Persian illustrative extents. Not simultaneous borders or exact frontiers. / 亚述、巴比伦、波斯分时段示意，不是同时存在的精确国界。",1400,1990)
    empires=[("Neo-Assyrian · c.650 BCE / 新亚述 · 约前650年","#c9d5aa",[(34,31),(36,30.5),(47,30),(48,35),(43,39),(37,38),(34,36)]), ("Neo-Babylonian · c.600 BCE / 新巴比伦 · 约前600年","#e5c58d",[(34,30),(36,29),(46,29),(48,33),(43,37),(36,36),(34,34)]), ("Achaemenid Persian · c.500 BCE / 波斯 · 约前500年","#bfc1df",[(24,24),(34,24),(36,29),(47,30),(49,24),(58,24),(69,25),(73,32),(68,39),(50,42),(37,42),(26,39),(28,33),(32,31),(24,31)])]
    for i,(title,color,polygon) in enumerate(empires):
        y=125+i*565
        label(root,45,y,title,26,font_weight="bold")
        frame=panel(root,[23,21.5,74,43.7],70,y+40,1260,380)
        points=[frame.point(*p) for p in polygon]
        element(root,"polygon",points=" ".join(f"{x:.2f},{y:.2f}" for x,y in points),fill=color,fill_opacity=.48,stroke="#5c5b50",stroke_width=2,stroke_dasharray="8 6")
        draw_places(root,frame,places,["Nineveh","Babylon","Susa","Jerusalem"],21)
        compass_and_scale(root,frame,90,y+435,500)
    finish(root,"exile-empires.svg",1850,["Shading shows broad teaching extents, not surveyed boundaries or continuous control. / 色块为大致范围，不表示精确边界或持续控制。","Periods are separate; modern coastlines are only a reference. / 各图时段不同；现代岸线仅供定位。"])

    root=root_svg("The Seven Churches of Revelation | 启示录七教会", "The seven cities named in Revelation 1:11, with a dashed reading-order connection. No claim about an exact ancient road. / 启示录一章十一节七城，虚线按书信次序连接，不表示精确古道。",1400,1170)
    frame=panel(root,[25.8,37.2,29.8,39.8],70,140,1260,720)
    names=["Ephesus","Smyrna","Pergamum","Thyatira","Sardis","Philadelphia","Laodicea"]
    line(root,frame,coords(names),"#245d7a","10 7")
    draw_places(root,frame,places,names,23)
    compass_and_scale(root,frame,90,930,50)
    finish(root,"seven-churches.svg",1020,["Revelation 1:11; 2–3 / 启示录 1:11；2–3章 · Locations approximate / 地点示意。","The line follows letter order, not an excavated mail route. / 虚线按书信次序，不是已发掘的邮路。"])

    stages = cast(list[dict[str, str]], json.loads((DATA / "storyline.json").read_text(encoding="utf-8"))["stages"])
    root=root_svg("The Bible Story in One Page | 一页圣经故事线", "Ten bilingual story stages with approximate narrative periods, disputed ranges and undated beginning/future hope. Vertical order is narrative, not a proportional timescale. / 十站双语故事线；区分叙事年代、争议区间与不可定年的开端和盼望。",1100,1600)
    label(root,40,110,"Narrative order, not a proportional timescale / 叙事顺序，不按时间比例",20)
    element(root,"line",x1=77,y1=170,x2=77,y2=1420,stroke="#456346",stroke_width=4)
    for i,stage in enumerate(stages):
        y=150+i*128
        element(root,"circle",cx=77,cy=y+40,r=24,fill="#456346")
        label(root,77,y+48,str(i+1),22,text_anchor="middle",fill="#ffffff",font_weight="bold")
        element(root,"rect",x=125,y=y,width=925,height=111,rx=10,fill="#eaf0e5",stroke="#c4cebd")
        label(root,145,y+31,stage["en"]+" | "+stage["zh"],24,font_weight="bold")
        label(root,145,y+62,stage["date_en"],18)
        label(root,145,y+91,stage["date_zh"],18)
    label(root,40,1490,"Dates summarize this library's draft guides; early periods are not independently fixed. / 年代为草稿导读概览，早期无法独立定年。",17)
    label(root,40,1522,"Creation/fall and new creation are not assigned calendar dates. / 创造、堕落与新创造不设公历日期。",18)
    label(root,40,1554,"Read passages before summaries; see First Steps and the source notes. / 先读经文，再读概览与来源说明。",18)
    results["bible-storyline.svg"]=ET.tostring(root,encoding="utf-8")+b"\n"
    return results

def generated_maps() -> dict[str, bytes]:
    basemap = cast(Basemap, json.loads((DATA / "natural-earth-subset.json").read_text(encoding="utf-8")))
    geography = cast(Geography, json.loads((DATA / "places-and-routes.json").read_text(encoding="utf-8")))
    for place in geography["places"].values():
        if not (-180 <= place["lon"] <= 180 and -90 <= place["lat"] <= 90) or not place["en"] or not place["zh"]:
            raise ValueError("Invalid source coordinate or bilingual label")
    for route in geography["routes"]:
        if len(route["stops"]) < 2 or any(name not in geography["places"] for name in route["stops"]):
            raise ValueError("Invalid route input")
    result = {"palestine-jesus.svg": palestine(basemap, geography), "paul-journeys.svg": paul(basemap, geography), **batch2_maps()}
    for data in result.values():
        validate_svg(data)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Check committed outputs without writing")
    args = parser.parse_args()
    for name, data in generated_maps().items():
        path = OUTPUT / name
        if args.check:
            if not path.is_file() or path.read_bytes() != data:
                raise SystemExit(f"map_drift={name}")
        else:
            OUTPUT.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        print(f"map_ok={name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
