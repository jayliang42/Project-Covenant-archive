from __future__ import annotations

import hashlib
from pathlib import Path
import unittest

from scripts import export_publication, generate_maps
from scripts.publication_assets import AssetError, is_asset_path, validate_asset, validate_jpeg, validate_svg

ROOT = Path(__file__).resolve().parents[1]
SAFE_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" '
    'role="img" aria-labelledby="title description">'
    '<title id="title">Map | 地图</title><desc id="description">Draft | 草稿</desc>'
    '<path d="M0,0 L100,100" fill="none" stroke="#123456"/></svg>'
).encode()


class AssetBoundaryTests(unittest.TestCase):
    def test_accepts_committed_media_and_exact_map_regeneration(self) -> None:
        maps = generate_maps.generated_maps()
        self.assertEqual(11, len(maps))
        self.assertEqual(maps, generate_maps.generated_maps())
        for name, data in maps.items():
            self.assertEqual(data, (ROOT / "assets/maps" / name).read_bytes())
            validate_asset("assets/maps/" + name, data)
        for path in (ROOT / "assets/illustrations").glob("*.jpg"):
            validate_asset(path.relative_to(ROOT).as_posix(), path.read_bytes())

    def test_rejects_svg_active_content_external_resources_and_entities(self) -> None:
        attacks = (
            '<script>alert(1)</script>',
            '<foreignObject><p>HTML</p></foreignObject>',
            '<image href="https://tracker.invalid/pixel"/>',
            '<path onclick="alert(1)"/>',
            '<path fill="url(https://tracker.invalid/paint)"/>',
            '<style>@import "https://tracker.invalid/font";</style>',
        )
        for attack in attacks:
            with self.subTest(attack=attack), self.assertRaises(AssetError):
                validate_svg(SAFE_SVG.replace(b"</svg>", attack.encode() + b"</svg>"))
        with self.assertRaises(AssetError):
            validate_svg(b'<!DOCTYPE svg [<!ENTITY x "payload">]>' + SAFE_SVG)

    def test_requires_accessibility_and_a_finite_viewbox(self) -> None:
        for invalid in (
            SAFE_SVG.replace(b'role="img"', b'role="presentation"'),
            SAFE_SVG.replace(b'<desc id="description">Draft | ', b'<desc id="missing">Draft | '),
            SAFE_SVG.replace(b'0 0 100 100', b'0 0 inf 100'),
        ):
            with self.assertRaises(AssetError):
                validate_svg(invalid)

    def test_rejects_jpeg_metadata_trailing_data_and_oversize(self) -> None:
        data = (ROOT / "assets/illustrations/tissot-resurrection.jpg").read_bytes()
        validate_jpeg(data)
        for marker, payload in ((0xE1, b'Exif\0\0private'), (0xED, b'IPTC private'), (0xFE, b'private comment')):
            segment = b'\xff' + bytes([marker]) + (len(payload) + 2).to_bytes(2, "big") + payload
            with self.assertRaises(AssetError):
                validate_jpeg(data[:2] + segment + data[2:])
        for invalid in (data + b"extra", data + b"x" * 300_000, b"not a JPEG"):
            with self.assertRaises(AssetError):
                validate_jpeg(invalid)

    def test_asset_paths_are_narrow_and_credits_are_required(self) -> None:
        for path in ("images/map.svg", "assets/maps/script.js", "assets/illustrations/photo.png", "assets/maps/../private.svg"):
            self.assertFalse(is_asset_path(path))
        asset = export_publication.SnapshotFile("assets/maps/example.svg", SAFE_SVG, hashlib.sha256(SAFE_SVG).hexdigest())
        with self.assertRaises(export_publication.PublicationExportError) as context:
            export_publication.validate_snapshot([asset])
        self.assertEqual("SNAPSHOT_ASSET_CREDITS_REQUIRED", context.exception.code)

    def test_snapshot_accepts_local_media_but_rejects_unapproved_targets(self) -> None:
        def file(path: str, data: bytes) -> export_publication.SnapshotFile:
            return export_publication.SnapshotFile(path, data, hashlib.sha256(data).hexdigest())

        asset = file("assets/maps/example.svg", SAFE_SVG)
        credits = file("CREDITS.md", b"# Credits | Sources\n")
        page = file("README.md", b"# Library | Sources\n\n![Accessible map](assets/maps/example.svg)\n")
        export_publication.validate_snapshot([page, credits, asset])
        for target in ("https://tracker.invalid/pixel.jpg", "assets/maps/missing.svg", "../private.svg", "assets/maps/example.svg?remote=1", "assets/maps/example.svg#fragment"):
            unapproved = file("README.md", f"# Library | Sources\n\n![Map]({target})\n".encode())
            with self.assertRaises(export_publication.PublicationExportError):
                export_publication.validate_snapshot([unapproved, credits, asset])


if __name__ == "__main__":
    unittest.main()
