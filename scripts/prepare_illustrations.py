#!/usr/bin/env python3
"""Compress the reviewed public-domain originals, or check the local outputs.

--check needs only Python's standard library. Compression requires the optional
Pillow version in requirements-media.txt and an explicit directory of originals.
This tool never downloads media and never preserves source EXIF/ICC/comments.
"""

from __future__ import annotations

import argparse
import io
import json
from pathlib import Path
from typing import TypedDict, cast

if __package__:
    from .publication_assets import MAX_JPEG_BYTES, validate_asset
else:
    from publication_assets import MAX_JPEG_BYTES, validate_asset

ROOT = Path(__file__).resolve().parents[1]


class Illustration(TypedDict):
    file: str
    output: str
    source: str
    artist: str
    title: str
    year: str
    license: str


def catalog() -> list[Illustration]:
    return cast(list[Illustration], json.loads((ROOT / "data/illustrations.json").read_text(encoding="utf-8")))


def compress(source: Path) -> bytes:
    from PIL import Image, ImageOps

    with Image.open(source) as original:
        image = ImageOps.exif_transpose(original).convert("RGB")
        image.thumbnail((1200, 1200), Image.Resampling.LANCZOS)
        clean = Image.frombytes("RGB", image.size, image.tobytes())
    for max_edge in (1200, 1000, 800):
        resized = clean.copy()
        resized.thumbnail((max_edge, max_edge), Image.Resampling.LANCZOS)
        for quality in (88, 82, 76, 70, 64, 58):
            output = io.BytesIO()
            resized.save(output, format="JPEG", quality=quality, optimize=True, progressive=False)
            data = output.getvalue()
            if len(data) <= MAX_JPEG_BYTES:
                return data
    raise ValueError("Illustration exceeds the 300,000-byte limit")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check", action="store_true")
    group.add_argument("--source-dir", type=Path)
    args = parser.parse_args()
    for item in catalog():
        destination = ROOT / item["output"]
        if args.check:
            data = destination.read_bytes()
        else:
            data = compress(args.source_dir / item["file"])
        validate_asset(item["output"], data)
        if not args.check:
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(data)
        print(f"illustration_ok={destination.name}; bytes={len(data)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
