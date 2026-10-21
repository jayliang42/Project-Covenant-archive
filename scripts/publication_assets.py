"""Validate the narrow, local SVG/JPEG publication boundary (stdlib only)."""

from __future__ import annotations

import re
import math
import xml.etree.ElementTree as ET


ASSET_PATH = re.compile(r"assets/(?:maps/[a-z0-9][a-z0-9_-]*\.svg|illustrations/[a-z0-9][a-z0-9_-]*\.jpg)\Z")
SVG_NS = "http://www.w3.org/2000/svg"
MAX_SVG_BYTES = 1_000_000
MAX_JPEG_BYTES = 300_000
SVG_TAGS = {"svg", "g", "title", "desc", "path", "rect", "line", "polyline", "polygon", "circle", "text", "tspan"}
SVG_ATTRIBUTES = {
    "id", "viewBox", "width", "height", "role", "aria-labelledby", "x", "y",
    "x1", "x2", "y1", "y2", "cx", "cy", "r", "rx", "ry", "d", "points",
    "fill", "fill-opacity", "fill-rule", "stroke", "stroke-width", "stroke-opacity",
    "stroke-dasharray", "stroke-linecap", "stroke-linejoin", "font-family",
    "font-size", "font-weight", "text-anchor", "paint-order", "transform", "dy",
}


class AssetError(ValueError):
    """A fixed error code, without source bytes or machine paths."""


def is_asset_path(path: str) -> bool:
    return ASSET_PATH.fullmatch(path) is not None


def validate_svg(data: bytes) -> None:
    if not data or len(data) > MAX_SVG_BYTES:
        raise AssetError("SVG_SIZE_INVALID")
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as error:
        raise AssetError("SVG_NOT_UTF8") from error
    if any(token in text.casefold() for token in ("<!", "<?", "url(", "@import")):
        raise AssetError("SVG_ACTIVE_CONTENT_FORBIDDEN")
    try:
        root = ET.fromstring(text)
    except ET.ParseError as error:
        raise AssetError("SVG_XML_INVALID") from error
    if root.tag != f"{{{SVG_NS}}}svg":
        raise AssetError("SVG_ROOT_INVALID")
    ids: dict[str, ET.Element] = {}
    count = 0
    for element in root.iter():
        count += 1
        if count > 20_000 or element.tag not in {f"{{{SVG_NS}}}{tag}" for tag in SVG_TAGS}:
            raise AssetError("SVG_ELEMENT_FORBIDDEN")
        for name, value in element.attrib.items():
            if name not in SVG_ATTRIBUTES or any(token in value.casefold() for token in ("url(", "http:", "https:", "data:", "javascript:")):
                raise AssetError("SVG_ATTRIBUTE_FORBIDDEN")
        identifier = element.get("id")
        if identifier is not None:
            if not re.fullmatch(r"[a-zA-Z][a-zA-Z0-9_-]*", identifier) or identifier in ids:
                raise AssetError("SVG_ID_INVALID")
            ids[identifier] = element
    labels = root.get("aria-labelledby", "").split()
    if root.get("role") != "img" or len(labels) != 2:
        raise AssetError("SVG_ACCESSIBILITY_REQUIRED")
    for identifier, tag in zip(labels, ("title", "desc")):
        element = ids.get(identifier)
        if element is None or element.tag != f"{{{SVG_NS}}}{tag}" or not "".join(element.itertext()).strip():
            raise AssetError("SVG_ACCESSIBILITY_REQUIRED")
    viewbox = root.get("viewBox", "").split()
    try:
        valid_box = len(viewbox) == 4 and all(math.isfinite(float(n)) for n in viewbox) and float(viewbox[2]) > 0 and float(viewbox[3]) > 0
    except ValueError:
        valid_box = False
    if not valid_box:
        raise AssetError("SVG_VIEWBOX_REQUIRED")


def validate_jpeg(data: bytes) -> None:
    """Accept baseline JPEG only; reject EXIF, comments, ICC/IPTC, and trailing bytes."""
    if not data or len(data) > MAX_JPEG_BYTES or not data.startswith(b"\xff\xd8"):
        raise AssetError("JPEG_SIZE_OR_SIGNATURE_INVALID")
    cursor = 2
    dimensions = False
    while cursor < len(data):
        if cursor + 4 > len(data) or data[cursor] != 0xFF:
            raise AssetError("JPEG_STRUCTURE_INVALID")
        marker = data[cursor + 1]
        if marker not in {0xE0, 0xDB, 0xC0, 0xC4, 0xDD, 0xDA}:
            raise AssetError("JPEG_METADATA_OR_MARKER_FORBIDDEN")
        length = int.from_bytes(data[cursor + 2:cursor + 4], "big")
        end = cursor + 2 + length
        if length < 2 or end > len(data):
            raise AssetError("JPEG_STRUCTURE_INVALID")
        payload = data[cursor + 4:end]
        if marker == 0xE0 and (len(payload) != 14 or not payload.startswith(b"JFIF\0")):
            raise AssetError("JPEG_METADATA_FORBIDDEN")
        if marker == 0xC0:
            if len(payload) < 6 or payload[0] != 8:
                raise AssetError("JPEG_DIMENSIONS_INVALID")
            height = int.from_bytes(payload[1:3], "big")
            width = int.from_bytes(payload[3:5], "big")
            if not (0 < width <= 1600 and 0 < height <= 1600):
                raise AssetError("JPEG_DIMENSIONS_INVALID")
            dimensions = True
        cursor = end
        if marker == 0xDA:
            if not dimensions:
                raise AssetError("JPEG_DIMENSIONS_INVALID")
            while cursor < len(data):
                if data[cursor] != 0xFF:
                    cursor += 1
                    continue
                if cursor + 1 >= len(data):
                    break
                next_marker = data[cursor + 1]
                if next_marker == 0 or 0xD0 <= next_marker <= 0xD7:
                    cursor += 2
                    continue
                if next_marker == 0xD9 and cursor + 2 == len(data):
                    return
                raise AssetError("JPEG_STRUCTURE_INVALID")
            raise AssetError("JPEG_END_MISSING")
    raise AssetError("JPEG_SCAN_MISSING")


def validate_asset(path: str, data: bytes) -> None:
    if not is_asset_path(path):
        raise AssetError("ASSET_PATH_FORBIDDEN")
    if path.endswith(".svg"):
        validate_svg(data)
    else:
        validate_jpeg(data)
