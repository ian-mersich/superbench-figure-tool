#!/usr/bin/env python3
"""Focused correction-selection and historical-artwork preservation checks."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("style4_correction", ROOT / "scripts/import-style4-correction.py")
CORRECTION = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CORRECTION)
STYLE = ROOT / "assets/scientific-packs/style-4"


class CorrectionTests(unittest.TestCase):
    def test_committed_selection_preserves_all_retained_records_and_source_recoveries(self):
        result = CORRECTION.validate_overlay(STYLE)
        self.assertEqual((243, 243, 249), (result["corrected_asset_count"], result["retained_asset_count"], result["file_count"]))
        previous, _ = CORRECTION.prior_assets(STYLE)
        manifest = json.loads((STYLE / CORRECTION.MANIFEST).read_bytes())
        selected = {item["asset_id"]: item for item in manifest["assets"]}
        retained_recoveries = [item for item in previous["assets"] if "source_provenance" in item and item == selected[item["asset_id"]]]
        self.assertEqual(8, len(retained_recoveries))
        self.assertEqual(6, sum(region.get("no_rendered_paint", False) for item in manifest["assets"] for region in item["editable_color_regions"]))

    def test_overlay_writer_cannot_change_a_historical_svg_or_manifest(self):
        with self.assertRaisesRegex(ValueError, "cannot overwrite a historical path"):
            CORRECTION.write_import({"manifest.json": b"wrong"}, STYLE)
        with self.assertRaisesRegex(ValueError, "cannot overwrite a historical path"):
            CORRECTION.write_import({"svg/existing.svg": b"wrong"}, STYLE)

    def test_retained_entry_cannot_silently_regress_to_downloaded_final_copy(self):
        original_read = Path.read_bytes
        manifest = json.loads((STYLE / CORRECTION.MANIFEST).read_bytes())
        target = next(item for item in manifest["assets"] if "source_provenance" in item and "prior_style4_record" not in item)
        target["sha256"] = "0" * 64
        changed = CORRECTION.IMPORT.json_bytes(manifest)
        with mock.patch.object(Path, "read_bytes", lambda path: changed if path == STYLE / CORRECTION.MANIFEST else original_read(path)):
            with self.assertRaisesRegex(ValueError, "Retained current Style 4 entry changed"):
                CORRECTION.validate_overlay(STYLE)

    def test_archive_inspects_even_unimported_members_for_path_traversal(self):
        generated = ROOT / "qa_artifacts/style4-corrected-20261017/import-tests"
        generated.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=generated) as temporary:
            archive_path = Path(temporary) / "unsafe.zip"
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr("../unimported-audit.txt", b"unsafe")
            with mock.patch.object(CORRECTION, "SOURCE_SHA256", CORRECTION.IMPORT.sha256(archive_path.read_bytes())):
                with self.assertRaisesRegex(ValueError, "Unsafe relative path"):
                    CORRECTION.read_archive(archive_path)


if __name__ == "__main__":
    unittest.main(verbosity=2)
