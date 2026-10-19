#!/usr/bin/env python3
"""Add the supplied Style 4 corrections without replacing retained artwork."""
from __future__ import annotations

import argparse
import collections
import copy
import importlib.util
import json
from pathlib import Path
import stat
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("style4_import", ROOT / "scripts/import-style4-library.py")
IMPORT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(IMPORT)
SOURCE_SHA256 = "2df0cd5e62cb1a78f02709b8f3befbfc01475acdb001d9bf795766bb5c540448"
PRIOR_SHA256 = "e6edeeac68a85db6a4256344ddeb125d156655a4d7c1c58f4a50c0cab6ed96fb"
OVERLAY = "corrected-20261017"
MANIFEST = "manifest-corrected-20261017.json"
METADATA = {"README.txt", "asset_id_to_filename.json", "asset_id_to_filename.tsv", "asset_manifest.json"}
EMPTY_OUTLINE_IDS = {
    "exp.nucleic_acid.replication_fork", "exp.nucleic_acid.chromatin_state.open",
    "exp.nucleic_acid.chromatin_state.condensed", "exp.nucleic_acid.trna",
    "exp.nucleic_acid.mirna", "exp.nucleic_acid.cdna_library",
}


def read_archive(path: Path) -> dict[str, bytes]:
    """Inspect every ZIP member; read only SVGs and the four import records."""
    if IMPORT.sha256(path.read_bytes()) != SOURCE_SHA256:
        raise ValueError("Corrected source archive SHA-256 differs")
    files, seen = {}, set()
    with zipfile.ZipFile(path) as archive:
        entries = archive.infolist()
        if len(entries) > 600 or sum(entry.file_size for entry in entries) > 20 * 1024 * 1024:
            raise ValueError("Corrected archive exceeds bounded inventory limits")
        for entry in entries:
            name = IMPORT.safe_relative_path(entry.filename.rstrip("/"))
            if name.casefold() in seen:
                raise ValueError(f"Duplicate corrected archive path: {name}")
            seen.add(name.casefold())
            if stat.S_ISLNK(entry.external_attr >> 16) or entry.flag_bits & 1:
                raise ValueError("Archive links and encrypted entries are forbidden")
            if entry.is_dir():
                continue
            limit = 12 * 1024 * 1024 if name == "contact_sheet.html" else 2 * 1024 * 1024
            if entry.file_size > limit or entry.file_size > max(entry.compress_size, 1) * 1000:
                raise ValueError(f"Corrected archive member exceeds size limit: {name}")
            if name in METADATA or name.endswith(".svg"):
                files[name] = archive.read(entry)
    if not METADATA <= files.keys():
        raise ValueError("Corrected archive metadata is incomplete")
    return files


def regions_for(identifier: str, root, originals: list[dict]) -> list[dict]:
    """Keep supplied empty outline roles explicit; do not invent a drawable."""
    if identifier not in EMPTY_OUTLINE_IDS:
        return IMPORT.derive_regions(root, originals)
    filtered = copy.deepcopy(root)
    empty = []
    for parent in filtered.iter():
        for element in list(parent):
            if element.get("data-region") == "outline" and not list(element) and IMPORT.local_name(element.tag) == "g":
                empty.append(element)
                parent.remove(element)
    if len(empty) != 1:
        raise ValueError(f"Expected exact supplied empty outline role: {identifier}")
    active = IMPORT.derive_regions(filtered, [item for item in originals if item["id"] != "outline"])
    outline = copy.deepcopy(next(item for item in originals if item["id"] == "outline"))
    outline.update(paint="stroke", default=empty[0].get("stroke"), default_paints=[], no_rendered_paint=True)
    if not outline["default"] or empty[0].get("fill") != "none":
        raise ValueError(f"Unexpected empty outline paint: {identifier}")
    by_id = {item["id"]: item for item in active + [outline]}
    return [by_id[item["id"]] for item in originals]


def validate_source(files: dict[str, bytes], catalog: dict, prior: dict) -> tuple[dict, dict]:
    mapping = json.loads(files["asset_id_to_filename.json"])
    supplied = json.loads(files["asset_manifest.json"])
    records = {record["asset_id"]: record for record in supplied}
    if len(records) != len(supplied) or len(records) != 486 or set(records) != set(mapping) or set(records) != set(catalog):
        raise ValueError("Corrected source must map exactly all 486 existing asset IDs")
    if collections.Counter(record["correction_status"] for record in supplied) != {"corrected_flagged_artwork": 243, "retained_artwork": 243}:
        raise ValueError("Expected exactly 243 corrected and 243 retained source entries")
    expected = set()
    for identifier, record in records.items():
        filename = IMPORT.safe_relative_path(mapping[identifier])
        if Path(filename).name != filename or not filename.endswith(".svg") or filename != record["filename"]:
            raise ValueError(f"Invalid corrected filename mapping: {identifier}")
        relative = "svg/" + filename
        if relative.casefold() in expected:
            raise ValueError("Corrected filenames are not unique")
        expected.add(relative.casefold())
        data = files[relative]
        root = IMPORT.parse_svg(data, unique_ids=True)
        original = IMPORT.parse_svg(catalog[identifier]["original"])
        if IMPORT.sha256(data) != record["svg_sha256"]:
            raise ValueError(f"Corrected source SVG SHA-256 differs: {identifier}")
        if root.get("viewBox") != record["viewBox"] or root.get("viewBox") != original.get("viewBox"):
            raise ValueError(f"Corrected source viewBox differs: {identifier}")
        regions = {element.get("data-region") for element in root.iter() if element.get("data-region")}
        if regions != set(record["data_regions"]) or regions != {item["id"] for item in catalog[identifier]["asset"]["editable_color_regions"]}:
            raise ValueError(f"Corrected source semantic regions differ: {identifier}")
        # An earlier supplied Style 4 phosphorylation redraw added the explicit P
        # mark. Preserve the current Style 4 labels rather than an older Style 1.
        prior_root = IMPORT.parse_svg(prior[identifier]["_bytes"], unique_ids=True)
        if IMPORT.svg_live_labels(root) != IMPORT.svg_live_labels(prior_root):
            raise ValueError(f"Corrected source live scientific labels differ: {identifier}")
        regions_for(identifier, root, catalog[identifier]["asset"]["editable_color_regions"])
    if {name.casefold() for name in files if name.endswith(".svg")} != expected:
        raise ValueError("Corrected source SVG coverage differs")
    return mapping, records


def prior_assets(style_dir: Path) -> tuple[dict, dict]:
    data = (style_dir / "manifest.json").read_bytes()
    if IMPORT.sha256(data) != PRIOR_SHA256:
        raise ValueError("Prior Style 4 manifest changed")
    manifest = json.loads(data)
    records = {record["asset_id"]: copy.deepcopy(record) for record in manifest["assets"]}
    for record in records.values():
        data = (style_dir / IMPORT.safe_relative_path(record["file"])).read_bytes()
        if IMPORT.sha256(data) != record["sha256"]:
            raise ValueError(f"Prior Style 4 artwork changed: {record['asset_id']}")
        record["_bytes"] = data
    return manifest, records


def build_import(archive_path: Path, style_dir: Path, library: Path = IMPORT.LIBRARY) -> dict[str, bytes]:
    files = read_archive(archive_path)
    catalog = IMPORT.load_catalog(library)
    previous, prior = prior_assets(style_dir)
    mapping, supplied = validate_source(files, catalog, prior)
    output, assets = {}, []
    for identifier in sorted(catalog):
        before = copy.deepcopy(prior[identifier])
        before.pop("_bytes")
        record = supplied[identifier]
        if record["correction_status"] == "retained_artwork":
            assets.append(before)
            continue
        source = files["svg/" + mapping[identifier]]
        root = IMPORT.parse_svg(source, unique_ids=True)
        relative = f"{OVERLAY}/svg/{mapping[identifier]}"
        replacement = {**copy.deepcopy(before), "file": relative, "sha256": IMPORT.sha256(source),
            "source_sha256": IMPORT.sha256(source), "source_filename": mapping[identifier], "source_record": record,
            "geometry_sha256": IMPORT.geometry_signature(root), "viewBox": root.get("viewBox"),
            "editable_color_regions": regions_for(identifier, root, catalog[identifier]["asset"]["editable_color_regions"]),
            "id_normalizations": [], "prior_style4_record": before,
            "source_provenance": {"archive_filename": "style4_corrected_486.zip", "archive_sha256": SOURCE_SHA256,
                "member": "svg/" + mapping[identifier], "source_sha256": IMPORT.sha256(source)}}
        assets.append(replacement)
        output[relative] = source
    source_metadata = []
    for filename in sorted(METADATA):
        relative = f"{OVERLAY}/source/{filename}"
        output[relative] = files[filename]
        source_metadata.append({"file": relative, "sha256": IMPORT.sha256(files[filename])})
    manifest = {**previous, "assets": assets,
        "prior_manifest": {"file": "manifest.json", "sha256": PRIOR_SHA256},
        "correction_archive": {"filename": "style4_corrected_486.zip", "sha256": SOURCE_SHA256},
        "corrected_asset_count": 243, "retained_asset_count": 243,
        "source_metadata": source_metadata,
        "provenance": "The owner's corrected Style 4 package supplies 243 exact-byte artwork replacements. The other 243 current Style 4 entries, including earlier recovered drawings, remain selected unchanged. Per-entry source provenance identifies the selected SVG rather than the unselected archive copy.",
        "import_transformations": "No corrected SVG bytes are rewritten. Six supplied empty outline groups retain their semantic IDs and authored stroke defaults with no_rendered_paint=true; their visible ribbon contours remain in the supplied nucleic-acid region. Previous manifest and artwork are retained byte-exact."}
    output[MANIFEST] = IMPORT.json_bytes(manifest)
    output[f"{OVERLAY}/README.md"] = ("# Corrected Style 4 drawings\n\nThe owner's `style4_corrected_486.zip` supplies 243 corrected drawings. This overlay selects those exact SVG bytes and keeps the other 243 current Style 4 entries, including earlier recovered artwork. It does not replace Style 1, Style 2, or Style 3.\n\n`../manifest-corrected-20261017.json` records the complete 486-ID selection, per-file source hashes, the unchanged previous entries and the corrected archive identity. Four supplied mapping/documentation files are retained in `source/`; the large contact sheet and source audits remain in the original download rather than the runtime.\n\nSix supplied nucleic-acid drawings have an empty outline group: their contours belong to the nucleic-acid region. These empty roles are recorded explicitly, without inventing geometry or changing supplied SVG bytes. All current Style 4 live scientific text, viewBoxes and semantic region identities are preserved. Illustrative analytical templates remain examples, not measured results.\n\nReproduce with `python scripts/import-style4-correction.py --source-archive <ZIP>`. Add `--check` to compare exact generated files; `python scripts/validate-style4-library.py` validates the complete committed selection without Downloads.\n").encode("utf-8")
    return output


def write_import(files: dict[str, bytes], style_dir: Path, *, check: bool = False):
    """Write only this overlay's exact paths; never modify historical files."""
    targets = []
    for relative, data in files.items():
        relative = IMPORT.safe_relative_path(relative)
        if relative != MANIFEST and not relative.startswith(OVERLAY + "/"):
            raise ValueError(f"Correction cannot overwrite a historical path: {relative}")
        target = style_dir / relative
        for path in [target, *target.parents]:
            if path.is_symlink() or (hasattr(path, "is_junction") and path.is_junction()):
                raise ValueError("Correction output links/junctions are forbidden")
        targets.append((target, data))
    overlay_dir = style_dir / OVERLAY
    expected = set(files) - {MANIFEST}
    actual = {path.relative_to(style_dir).as_posix() for path in overlay_dir.rglob("*") if path.is_file()} if overlay_dir.exists() else set()
    if actual - expected:
        raise ValueError(f"Unexpected correction output files: {sorted(actual - expected)}")
    for target, data in targets:
        if check:
            if not target.is_file() or target.read_bytes() != data:
                raise ValueError(f"Correction differs from exact reproducible output: {target.name}")
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)


def validate_overlay(style_dir: Path, library: Path = IMPORT.LIBRARY) -> dict:
    previous, prior = prior_assets(style_dir)
    manifest = json.loads((style_dir / MANIFEST).read_bytes())
    if manifest.get("prior_manifest") != {"file": "manifest.json", "sha256": PRIOR_SHA256} or manifest.get("correction_archive") != {"filename": "style4_corrected_486.zip", "sha256": SOURCE_SHA256}:
        raise ValueError("Corrected overlay source identity differs")
    catalog = IMPORT.load_catalog(library)
    supplied = json.loads((style_dir / OVERLAY / "source/asset_manifest.json").read_bytes())
    mapping = json.loads((style_dir / OVERLAY / "source/asset_id_to_filename.json").read_bytes())
    source_records = {item["asset_id"]: item for item in supplied}
    assets = manifest.get("assets", [])
    if len(assets) != 486 or len(source_records) != 486 or set(source_records) != set(catalog) or set(mapping) != set(catalog) or len({item["asset_id"] for item in assets}) != 486:
        raise ValueError("Corrected overlay must cover exactly all 486 IDs")
    owned = {MANIFEST, f"{OVERLAY}/README.md"}
    corrected = retained = 0
    for item in assets:
        identifier = item["asset_id"]
        before = copy.deepcopy(prior[identifier]); before.pop("_bytes")
        supplied_record = source_records[identifier]
        if supplied_record["correction_status"] == "retained_artwork":
            retained += 1
            if item != before:
                raise ValueError(f"Retained current Style 4 entry changed: {identifier}")
            continue
        if supplied_record["correction_status"] != "corrected_flagged_artwork":
            raise ValueError("Unknown correction status")
        corrected += 1
        relative = f"{OVERLAY}/svg/{IMPORT.safe_relative_path(mapping[identifier])}"
        if item["file"] != relative or supplied_record["filename"] != mapping[identifier]:
            raise ValueError(f"Corrected selection path differs: {identifier}")
        data = (style_dir / relative).read_bytes()
        root = IMPORT.parse_svg(data, unique_ids=True)
        digest = IMPORT.sha256(data)
        if digest != item["sha256"] or digest != item["source_sha256"] or digest != supplied_record["svg_sha256"]:
            raise ValueError(f"Corrected SVG SHA-256 differs: {identifier}")
        if item["prior_style4_record"] != before or item["source_record"] != supplied_record or item["id_normalizations"] != []:
            raise ValueError(f"Corrected per-entry provenance differs: {identifier}")
        provenance = {"archive_filename": "style4_corrected_486.zip", "archive_sha256": SOURCE_SHA256, "member": "svg/" + mapping[identifier], "source_sha256": digest}
        if item["source_provenance"] != provenance or item["source_filename"] != mapping[identifier] or item["source_pack_id"] != before["source_pack_id"] or item["name"] != before["name"]:
            raise ValueError(f"Corrected source identity differs: {identifier}")
        if root.get("viewBox") != before["viewBox"] or root.get("viewBox") != item["viewBox"] or root.get("viewBox") != supplied_record["viewBox"] or IMPORT.geometry_signature(root) != item["geometry_sha256"]:
            raise ValueError(f"Corrected SVG geometry binding differs: {identifier}")
        if IMPORT.svg_live_labels(root) != IMPORT.svg_live_labels(IMPORT.parse_svg(prior[identifier]["_bytes"])):
            raise ValueError(f"Corrected live scientific text differs: {identifier}")
        if item["editable_color_regions"] != regions_for(identifier, root, catalog[identifier]["asset"]["editable_color_regions"]):
            raise ValueError(f"Corrected actual color regions differ: {identifier}")
        owned.add(relative)
    if (corrected, retained, manifest.get("corrected_asset_count"), manifest.get("retained_asset_count"), manifest.get("asset_count")) != (243, 243, 243, 243, 486):
        raise ValueError("Corrected/retained overlay counts differ")
    metadata = manifest.get("source_metadata", [])
    expected_metadata = {f"{OVERLAY}/source/{filename}" for filename in METADATA}
    if len(metadata) != 4 or {item["file"] for item in metadata} != expected_metadata:
        raise ValueError("Corrected metadata coverage differs")
    for item in metadata:
        if IMPORT.sha256((style_dir / item["file"]).read_bytes()) != item["sha256"]:
            raise ValueError("Corrected metadata hash differs")
        owned.add(item["file"])
    actual = {path.relative_to(style_dir).as_posix() for path in (style_dir / OVERLAY).rglob("*") if path.is_file()} | {MANIFEST}
    if actual != owned:
        raise ValueError(f"Unexpected/missing correction files: {sorted(actual ^ owned)}")
    return {"status": "PASS", "asset_count": 486, "corrected_asset_count": corrected, "retained_asset_count": retained,
        "file_count": len(owned), "empty_outline_role_count": len(EMPTY_OUTLINE_IDS), "owned_files": sorted(owned)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-archive", type=Path, required=True)
    parser.add_argument("--style-dir", type=Path, default=ROOT / "assets/scientific-packs/style-4")
    parser.add_argument("--library", type=Path, default=IMPORT.LIBRARY)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        files = build_import(args.source_archive, args.style_dir, args.library)
        write_import(files, args.style_dir, check=args.check)
        result = validate_overlay(args.style_dir, args.library)
        result.pop("owned_files")
        print(json.dumps(result, indent=2))
    except (ValueError, OSError, KeyError, IMPORT.ET.ParseError, zipfile.BadZipFile, json.JSONDecodeError) as error:
        print(f"Style 4 correction failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
