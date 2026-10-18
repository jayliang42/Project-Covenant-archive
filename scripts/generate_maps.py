#!/usr/bin/env python3
"""Generate the two offline SVG pilots from committed open-data subsets.

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
                element(parent, "path", d=" ".join(paths), fill=fill, stroke="#a9b4ac", stroke_width="0.7", fill_rule="evenodd")


def compass_and_scale(parent: ET.Element, frame: Frame, x: float, y: float, km: int) -> None:
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
    root = ET.Element(NS + "svg", {"viewBox": f"0 0 {width} {height}", "width": str(width), "height": str(height), "role": "img", "aria-labelledby": "map-title map-description", "font-family": "sans-serif"})
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
        element(root, "polygon", points=" ".join(f"{px:.2f},{py:.2f}" for px,py in points), fill=fill, fill_opacity=0.55, stroke="#7a7568", stroke_width=1.5, stroke_dasharray="7 5")
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


def generated_maps() -> dict[str, bytes]:
    basemap = cast(Basemap, json.loads((DATA / "natural-earth-subset.json").read_text(encoding="utf-8")))
    geography = cast(Geography, json.loads((DATA / "places-and-routes.json").read_text(encoding="utf-8")))
    for place in geography["places"].values():
        if not (-180 <= place["lon"] <= 180 and -90 <= place["lat"] <= 90) or not place["en"] or not place["zh"]:
            raise ValueError("Invalid source coordinate or bilingual label")
    for route in geography["routes"]:
        if len(route["stops"]) < 2 or any(name not in geography["places"] for name in route["stops"]):
            raise ValueError("Invalid route input")
    result = {"palestine-jesus.svg": palestine(basemap, geography), "paul-journeys.svg": paul(basemap, geography)}
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
