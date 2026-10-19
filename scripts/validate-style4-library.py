#!/usr/bin/env python3
"""Validate all imported Style 4 artwork, provenance and semantic colors."""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("style4_import", ROOT / "scripts/import-style4-library.py")
IMPORT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(IMPORT)


def validate(style_dir: Path, library: Path = IMPORT.LIBRARY, *, expected_count: int = 486, source_archive: Path | None = None,
             recovery_archive: Path | None = None) -> dict:
    # Validate topology before reading any manifest or asset bytes. In
    # particular, a matching hash must not make an out-of-tree link acceptable.
    for path in [style_dir, *style_dir.rglob("*")]:
        if path.is_symlink() or (hasattr(path, "is_junction") and path.is_junction()):
            raise ValueError(f"Style 4 filesystem symlink/junction is forbidden: {path}")
        if not path.is_file() and not path.is_dir():
            raise ValueError(f"Unsupported Style 4 filesystem entry: {path}")
    manifest = json.loads((style_dir / "manifest.json").read_text(encoding="utf-8"))
    if (manifest.get("schema_version"), manifest.get("id"), manifest.get("name")) != ("1.0.0", "style-4", "Style 4"):
        raise ValueError("Invalid Style 4 manifest identity")
    if manifest.get("source_archive", {}).get("sha256") != IMPORT.SOURCE_SHA256 and expected_count == 486:
        raise ValueError("Style 4 source archive is not the reviewed complete package")
    recovery = None
    selected = {}
    if expected_count == 486:
        recovery, selection_bytes = IMPORT.load_recovery_selection(style_dir / "recovery-selection.json")
        expected_recovery = {**recovery["source_archive"], "selection_file": "recovery-selection.json", "selection_sha256": IMPORT.sha256(selection_bytes), "asset_count": 16}
        if manifest.get("recovery_archive") != expected_recovery:
            raise ValueError("Style 4 recovery archive or finite selection binding differs")
        selected = {entry["asset_id"]: entry for entry in recovery["assets"]}
    catalog = IMPORT.load_catalog(library)
    assets = manifest["assets"]
    identifiers = [asset["asset_id"] for asset in assets]
    if len(assets) != expected_count or manifest.get("asset_count") != expected_count or len(set(identifiers)) != expected_count or set(identifiers) != set(catalog):
        raise ValueError(f"Expected exact {expected_count}-asset Style 4 coverage")
    paths = set()
    id_repairs = 0
    multicolor_regions = 0
    for record in assets:
        identifier = record["asset_id"]
        relative = IMPORT.safe_relative_path(record["file"])
        if not relative.startswith("svg/") or not relative.endswith(".svg") or relative.casefold() in paths:
            raise ValueError(f"Invalid or duplicate Style 4 SVG path: {relative}")
        paths.add(relative.casefold())
        data = (style_dir / relative).read_bytes()
        if IMPORT.sha256(data) != record["sha256"]:
            raise ValueError(f"Imported SVG SHA-256 differs: {identifier}")
        root = IMPORT.parse_svg(data, unique_ids=True)
        corrected = IMPORT.restore_source_ids(data, record["id_normalizations"])
        entry = selected.get(identifier)
        corrections = entry.get("corrections", []) if entry else []
        restored = IMPORT.apply_corrections(corrected, corrections, reverse=True)
        if IMPORT.sha256(restored) != record["source_sha256"]:
            raise ValueError(f"Original SVG cannot be byte-restored: {identifier}")
        source_root = IMPORT.parse_svg(restored)
        reimported, changes = IMPORT.normalize_duplicate_ids(IMPORT.apply_corrections(restored, corrections))
        if reimported != data or changes != record["id_normalizations"]:
            raise ValueError(f"Duplicate-ID normalization differs from deterministic import: {identifier}")
        signature = IMPORT.geometry_signature(root)
        if signature != record["geometry_sha256"] or signature != IMPORT.geometry_signature(IMPORT.parse_svg(corrected)):
            raise ValueError(f"Style 4 geometry changed: {identifier}")
        original = catalog[identifier]
        original_root = IMPORT.ET.fromstring(original["original"])
        if root.get("viewBox") != record["viewBox"] or root.get("viewBox") != original_root.get("viewBox"):
            raise ValueError(f"Style 4/source viewBox differs: {identifier}")
        if record["source_pack_id"] != original["pack_id"] or record["name"] != original["asset"]["name"]:
            raise ValueError(f"Style 4/source identity differs: {identifier}")
        if entry:
            provenance = {"archive_filename": recovery["source_archive"]["filename"], "archive_sha256": IMPORT.RECOVERY_SHA256,
                "member": entry["member"], "source_sha256": entry["source_sha256"], "final_archive_member": entry["final_archive_member"],
                "final_replaced_sha256": entry["final_replaced_sha256"], "reason": entry["reason"], "corrections": corrections}
            if record.get("source_provenance") != provenance or record["source_sha256"] != entry["source_sha256"]:
                raise ValueError(f"Recovered source provenance differs: {identifier}")
            if IMPORT.svg_live_labels(source_root) != IMPORT.svg_live_labels(original_root):
                raise ValueError(f"Recovered scientific labels differ: {identifier}")
        elif "source_provenance" in record:
            raise ValueError(f"Unexpected source substitution outside the reviewed recovery selection: {identifier}")
        expected_regions = IMPORT.derive_regions(root, original["asset"]["editable_color_regions"])
        if record["editable_color_regions"] != expected_regions:
            raise ValueError(f"Style 4 color defaults or region metadata differ: {identifier}")
        id_repairs += len(changes)
        multicolor_regions += sum(len(region["default_paints"]) > 1 for region in expected_regions)
    metadata_paths = set()
    for metadata in manifest["source_metadata"]:
        relative = IMPORT.safe_relative_path(metadata["file"])
        if not relative.startswith("source/") or relative in metadata_paths:
            raise ValueError("Invalid source metadata path")
        metadata_paths.add(relative)
        if IMPORT.sha256((style_dir / relative).read_bytes()) != metadata["sha256"]:
            raise ValueError(f"Source metadata SHA-256 differs: {relative}")
    expected_metadata = {"source/" + filename for filename in IMPORT.METADATA_FILES}
    if recovery:
        expected_metadata |= {"source/recovery/" + filename for filename in IMPORT.RECOVERY_METADATA_FILES}
    if metadata_paths != expected_metadata:
        raise ValueError("Source metadata file coverage differs")
    mapping = json.loads((style_dir / "source/asset_id_to_filename.json").read_text(encoding="utf-8"))
    supplied = json.loads((style_dir / "source/final_manifest.json").read_text(encoding="utf-8"))
    records = {record["asset_id"]: record for record in supplied}
    if len(records) != len(supplied) or set(records) != set(catalog) or set(mapping) != set(catalog):
        raise ValueError("Original package metadata ID coverage differs")
    for record in assets:
        identifier = record["asset_id"]
        if record["file"] != "svg/" + mapping[identifier] or record["source_filename"] != mapping[identifier] or record["source_record"] != records[identifier]:
            raise ValueError(f"Original package metadata differs: {identifier}")
    expected_files = {record["file"] for record in assets} | metadata_paths | {"manifest.json", "README.md"}
    if recovery:
        expected_files.add("recovery-selection.json")
    actual_files = {path.relative_to(style_dir).as_posix() for path in style_dir.rglob("*") if path.is_file()}
    correction = None
    correction_manifest = "manifest-corrected-20261017.json"
    descriptor = json.loads(library.read_text(encoding="utf-8"))
    selected_correction = any(item.get("path") == "style-4/" + correction_manifest for item in descriptor.get("art_styles", []))
    if (style_dir / correction_manifest).is_file() or selected_correction:
        correction_spec = importlib.util.spec_from_file_location("style4_correction", ROOT / "scripts/import-style4-correction.py")
        correction_import = importlib.util.module_from_spec(correction_spec)
        correction_spec.loader.exec_module(correction_import)
        correction = correction_import.validate_overlay(style_dir, library)
        # Ignore only the exact files whose identity and selection were just
        # validated. Historical manifests, source records and SVGs still pass
        # every original check above without exemptions.
        actual_files -= set(correction.pop("owned_files"))
    if actual_files != expected_files:
        raise ValueError(f"Unexpected or missing Style 4 files: {sorted(actual_files ^ expected_files)}")
    if source_archive is not None:
        files = IMPORT.build_import(source_archive, library, expected_count=expected_count, recovery_archive=recovery_archive)
        for relative, data in files.items():
            if (style_dir / relative).read_bytes() != data:
                raise ValueError(f"Imported output differs from reproducible source: {relative}")
    result = {"status": "PASS", "asset_count": len(assets), "file_count": len(actual_files), "duplicate_id_repairs": id_repairs, "regions_with_multiple_paints": multicolor_regions, "recovered_asset_count": len(selected), "corrected_asset_count": sum(bool(entry.get("corrections")) for entry in selected.values()), "source_archive_verified": source_archive is not None}
    if correction:
        result["correction_overlay"] = correction
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--style-dir", type=Path, default=ROOT / "assets/scientific-packs/style-4")
    parser.add_argument("--library", type=Path, default=IMPORT.LIBRARY)
    parser.add_argument("--source-archive", type=Path)
    parser.add_argument("--recovery-archive", type=Path)
    args = parser.parse_args()
    try:
        result = validate(args.style_dir, args.library, source_archive=args.source_archive, recovery_archive=args.recovery_archive)
    except (ValueError, OSError, KeyError, IMPORT.ET.ParseError, json.JSONDecodeError) as error:
        print(f"Style 4 validation failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
