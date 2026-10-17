#!/usr/bin/env python3
"""Focused Style 4 archive security, paint and reproducibility checks."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import stat
import tempfile
import unittest
from unittest import mock
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("style4_import", ROOT / "scripts/import-style4-library.py")
IMPORT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(IMPORT)
VALIDATE_SPEC = importlib.util.spec_from_file_location("style4_validate", ROOT / "scripts/validate-style4-library.py")
VALIDATE = importlib.util.module_from_spec(VALIDATE_SPEC)
VALIDATE_SPEC.loader.exec_module(VALIDATE)
SVG = b'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 128"><title id="title">Test</title><metadata>{"id":"repeat"}</metadata><g data-region="body" fill="#DCEFE7" stroke="none"><path id="repeat" d="M1 1H5V5Z"/><circle id="repeat" fill="#FFFFFF" cx="2" cy="2" r="1"/><g data-region="accent" fill="none" stroke="#E3A16A"><path id="repeat" d="M2 2L3 3"/></g><path fill="#BFE7DE" d="M5 5H8V8Z"/></g></svg>'''


class Style4ImportTests(unittest.TestCase):
    def setUp(self):
        generated = ROOT / "qa_artifacts/style4-import-tests"
        generated.mkdir(parents=True, exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(prefix="case-", dir=generated)
        self.root = Path(self.temporary.name)
        self.library = self.root / "library.json"
        self.library.write_text(json.dumps({"packs": [{"id": "test", "path": "test/asset-pack.json"}]}), encoding="utf-8")
        pack = self.root / "test"
        pack.mkdir()
        (pack / "original.svg").write_bytes(SVG)
        self.regions = [{"id": "body", "label": "Body", "default": "#C7F2EC", "paint": "fill"}, {"id": "accent", "label": "Accent", "default": "#F4A261", "paint": "stroke"}]
        (pack / "asset-pack.json").write_text(json.dumps({"assets": [{"id": "test.asset", "name": "Test asset", "file": "original.svg", "editable_color_regions": self.regions}]}), encoding="utf-8")
        self.archive = self.root / "fixture.zip"

    def tearDown(self):
        self.temporary.cleanup()

    def make_archive(self, svg=SVG, *, additional=None, mapping=None):
        mapping = mapping or {"test.asset": "test_style4.svg"}
        metadata = {
            "README.txt": b"Original package metadata",
            "asset_id_to_filename.json": json.dumps(mapping).encode(),
            "asset_id_to_filename.tsv": b"asset_id\tfilename\ntest.asset\ttest_style4.svg\n",
            "final_manifest.json": json.dumps([{"asset_id": "test.asset", "filename": "test_style4.svg", "source_package": "fixture"}]).encode(),
            "final_audit.txt": b"Expected 1, final 1",
        }
        with zipfile.ZipFile(self.archive, "w", zipfile.ZIP_DEFLATED) as archive:
            for filename, data in metadata.items():
                archive.writestr(filename, data)
            archive.writestr("svg/test_style4.svg", svg)
            for filename, data in additional or []:
                archive.writestr(filename, data)

    def build(self):
        return IMPORT.build_import(self.archive, self.library, expected_count=1, expected_archive_sha=None)

    def test_reproducibility_and_byte_reversible_id_repairs(self):
        self.make_archive()
        first = self.build()
        self.assertEqual(first, self.build())
        manifest = json.loads(first["manifest.json"])
        record = manifest["assets"][0]
        self.assertEqual(2, len(record["id_normalizations"]))
        self.assertEqual(SVG, IMPORT.restore_source_ids(first[record["file"]], record["id_normalizations"]))
        self.assertIn(b'{"id":"repeat"}', first[record["file"]])
        output = self.root / "output"
        IMPORT.write_import(first, output)
        IMPORT.write_import(first, output, check=True)
        result = VALIDATE.validate(output, self.library, expected_count=1)
        self.assertEqual("PASS", result["status"])

    def test_inherited_paints_nested_regions_and_fixed_white_are_preserved(self):
        regions = IMPORT.derive_regions(IMPORT.parse_svg(SVG), self.regions)
        self.assertEqual("#DCEFE7", regions[0]["default"])
        self.assertEqual("#E3A16A", regions[1]["default"])
        self.assertEqual([{"paint": "fill", "color": "#DCEFE7"}, {"paint": "fill", "color": "#FFFFFF"}, {"paint": "fill", "color": "#BFE7DE"}], regions[0]["default_paints"])
        self.assertEqual([{"paint": "stroke", "color": "#E3A16A"}], regions[1]["default_paints"])
        self.assertEqual("#C7F2EC", self.regions[0]["default"])

    def test_duplicate_ids_do_not_collide_with_preexisting_suffixes(self):
        source = SVG.replace(b'<title id="title">', b'<title id="repeat--style4-2">')
        normalized, changes = IMPORT.normalize_duplicate_ids(source)
        self.assertEqual("repeat--style4-3", changes[0]["normalized_id"])
        self.assertEqual("repeat--style4-4", changes[1]["normalized_id"])
        self.assertEqual(source, IMPORT.restore_source_ids(normalized, changes))

    def test_archive_traversal_absolute_windows_and_backslash_paths_rejected(self):
        for path in ("../outside.svg", "/absolute.svg", "C:/outside.svg", "svg\\outside.svg", "svg/../outside.svg"):
            with self.subTest(path=path):
                with self.assertRaisesRegex(ValueError, "Unsafe relative path"):
                    IMPORT.safe_relative_path(path)
                self.make_archive(additional=[(path, b"bad")])
                # Python's Windows ZipInfo writer normalizes backslashes;
                # either unsafe-path rejection or exact-coverage rejection
                # must prevent the archive from producing output.
                with self.assertRaises(ValueError):
                    self.build()

    def test_duplicate_zip_names_and_symlink_rejected(self):
        self.make_archive(additional=[("SVG/TEST_STYLE4.SVG", SVG)])
        with self.assertRaisesRegex(ValueError, "Duplicate archive path"):
            self.build()
        self.make_archive()
        with zipfile.ZipFile(self.archive, "a") as archive:
            symlink = zipfile.ZipInfo("svg/link.svg")
            symlink.create_system = 3
            symlink.external_attr = (stat.S_IFLNK | 0o777) << 16
            archive.writestr(symlink, "../../outside.svg")
        with self.assertRaisesRegex(ValueError, "symlink"):
            self.build()

    def test_script_image_external_reference_and_entity_rejected(self):
        payloads = [SVG.replace(b"</svg>", b"<script>alert(1)</script></svg>"), SVG.replace(b"</svg>", b'<image href="data:image/png;base64,abc"/></svg>'), SVG.replace(b'fill="#DCEFE7"', b'fill="url(#gradient)"'), SVG.replace(b'<svg ', b'<!DOCTYPE svg [<!ENTITY ext SYSTEM "file:///secret">]><svg '), SVG.replace(b'fill="#DCEFE7"', b'onload="alert(1)"')]
        for payload in payloads:
            with self.subTest(payload=payload[:80]):
                self.make_archive(svg=payload)
                with self.assertRaises(ValueError):
                    self.build()

    def test_exact_asset_and_file_coverage_required(self):
        self.make_archive(mapping={"unexpected.asset": "test_style4.svg"})
        with self.assertRaisesRegex(ValueError, "exact 1-asset"):
            self.build()
        self.make_archive(additional=[("svg/extra.svg", SVG)])
        with self.assertRaisesRegex(ValueError, "coverage is not exact"):
            self.build()

    def test_manifest_tampering_and_svg_paint_tampering_fail(self):
        self.make_archive()
        files = self.build()
        output = self.root / "output"
        IMPORT.write_import(files, output)
        manifest_path = output / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["assets"][0]["editable_color_regions"][0]["default"] = "#FF0000"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "color defaults"):
            VALIDATE.validate(output, self.library, expected_count=1)
        IMPORT.write_import(files, output)
        artwork = output / "svg/test_style4.svg"
        artwork.write_bytes(artwork.read_bytes().replace(b"#DCEFE7", b"#FF0000"))
        with self.assertRaisesRegex(ValueError, "SHA-256 differs"):
            VALIDATE.validate(output, self.library, expected_count=1)

    def test_write_preflights_paths_and_preserves_unknown_files(self):
        output = self.root / "output"
        with self.assertRaisesRegex(ValueError, "Unsafe relative path"):
            IMPORT.write_import({"valid.txt": b"safe", "../escape.txt": b"bad"}, output)
        self.assertFalse(output.exists())
        output.mkdir()
        original = output / "user-file.txt"
        original.write_text("keep", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "unexpected files"):
            IMPORT.write_import({"valid.txt": b"safe"}, output)
        self.assertEqual("keep", original.read_text(encoding="utf-8"))
        self.assertFalse((output / "valid.txt").exists())

    def test_restyled_region_binds_actual_paint_channel_without_recoloring_fixed_contours(self):
        import xml.etree.ElementTree as ET
        svg = ET.fromstring('<svg xmlns="http://www.w3.org/2000/svg"><path data-region="accent" fill="none" stroke="#9BD5C8" d="M1 1L9 9"/><path data-region="body" fill="#DCEFE7" stroke="#5B6F6A" d="M1 1h8v8z"/></svg>')
        regions = IMPORT.derive_regions(svg, [{'id':'accent','paint':'fill','default':'#F4A261'}, {'id':'body','paint':'fill','default':'#C7F2EC'}])
        self.assertEqual(regions[0]['paint'], 'stroke')
        self.assertEqual(regions[0]['default'], '#9BD5C8')
        self.assertEqual(regions[1]['paint'], 'fill')
        self.assertEqual(regions[1]['default'], '#DCEFE7')

    def test_complete_source_archive_hash_is_bound(self):
        self.make_archive()
        with self.assertRaisesRegex(ValueError, "Source archive SHA-256"):
            IMPORT.build_import(self.archive, self.library, expected_count=1)

    def test_validator_rejects_link_topology_before_reading_bytes(self):
        self.make_archive()
        output = self.root / "output"
        IMPORT.write_import(self.build(), output)
        original = Path.is_symlink
        # The same topology predicate covers Windows junctions. Simulate a
        # linked SVG to test the refusal even on accounts without link rights.
        with mock.patch.object(Path, "is_symlink", lambda path: path.name == "test_style4.svg" or original(path)):
            with self.assertRaisesRegex(ValueError, "filesystem symlink/junction"):
                VALIDATE.validate(output, self.library, expected_count=1)

    def test_recovery_requires_the_exact_source_archive(self):
        selection, _ = IMPORT.load_recovery_selection()
        with self.assertRaisesRegex(ValueError, "recovery archive is required"):
            IMPORT.read_recovery_archive(self.root / "missing.zip", selection)
        self.make_archive()
        with self.assertRaisesRegex(ValueError, "Recovery archive SHA-256"):
            IMPORT.read_recovery_archive(self.archive, selection)

    def test_recovery_selection_rejects_missing_or_wrong_ids(self):
        original, _ = IMPORT.load_recovery_selection()
        for missing in (True, False):
            selection = json.loads(json.dumps(original))
            if missing:
                selection["assets"].pop()
            else:
                selection["assets"][0]["asset_id"] = "core.cell.generic"
            path = self.root / "selection.json"
            path.write_text(json.dumps(selection), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "exactly the 16 reviewed asset IDs"):
                IMPORT.load_recovery_selection(path)

    def test_recovery_selection_hash_binds_correction_and_archive_choices(self):
        selection, _ = IMPORT.load_recovery_selection()
        path = self.root / "selection.json"
        selection["source_archive"]["sha256"] = "0" * 64
        path.write_text(json.dumps(selection), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "archive identity differs"):
            IMPORT.load_recovery_selection(path)
        selection, _ = IMPORT.load_recovery_selection()
        next(row for row in selection["assets"] if row["corrections"])["corrections"][0]["patches"][0]["after"] = 'd="M0 0Z"'
        path.write_text(json.dumps(selection), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "selection SHA-256 differs"):
            IMPORT.load_recovery_selection(path)

    def test_literal_svg_corrections_are_exact_and_reversible(self):
        source = b'<path d="M1 1L2 2"/><metadata>unmodified</metadata>'
        corrections = [{"id": "test", "patches": [{"before": 'd="M1 1L2 2"', "after": 'd="M1 1L1.5 1.5"'}]}]
        corrected = IMPORT.apply_corrections(source, corrections)
        self.assertIn(b'<metadata>unmodified</metadata>', corrected)
        self.assertEqual(source, IMPORT.apply_corrections(corrected, corrections, reverse=True))
        for invalid in (source * 2, b'<path d="M9 9"/>'):
            with self.assertRaisesRegex(ValueError, "match exactly one source node"):
                IMPORT.apply_corrections(invalid, corrections)

    def test_committed_recovery_is_valid_without_downloads(self):
        result = VALIDATE.validate(ROOT / "assets/scientific-packs/style-4")
        self.assertEqual(16, result["recovered_asset_count"])
        self.assertEqual(4, result["corrected_asset_count"])
        self.assertFalse(result["source_archive_verified"])

    def test_unreviewed_source_substitution_is_rejected(self):
        self.make_archive()
        files = self.build()
        manifest = json.loads(files["manifest.json"])
        manifest["assets"][0]["source_provenance"] = {"archive_filename": "unreviewed.zip"}
        files["manifest.json"] = IMPORT.json_bytes(manifest)
        output = self.root / "output"
        IMPORT.write_import(files, output)
        with self.assertRaisesRegex(ValueError, "Unexpected source substitution"):
            VALIDATE.validate(output, self.library, expected_count=1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
