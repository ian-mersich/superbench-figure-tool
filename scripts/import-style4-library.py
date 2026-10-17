#!/usr/bin/env python3
"""Import the owner's complete Style 4 archive without rewriting its artwork.

This is intentionally separate from historical pack approvals. The import is
additive: existing asset IDs, catalogs, licenses and SVGs are read, never edited.
"""
from __future__ import annotations

import argparse
import collections
import copy
import hashlib
import json
import re
import stat
import sys
import zipfile
from pathlib import Path, PurePosixPath
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
LIBRARY = ROOT / "assets/scientific-packs/library.json"
SOURCE_SHA256 = "7e4d6f1bb5de5d87ce4dd8a43f190e308c57046313500cab6920a1d9f9fa7ea0"
RECOVERY_SHA256 = "50ef7848520126461ac82f7df0c9fd4682c5211b3d2c98d286067573aa00717f"
RECOVERY_SELECTION_SHA256 = "b8464b29afed4a68bffd2a96ea26e05d1853de135a8e7184aae3188ab76bb6ad"
RECOVERY_SELECTION = ROOT / "assets/scientific-packs/style-4/recovery-selection.json"
RECOVERY_METADATA_FILES = {"README.txt", "asset_id_to_style4_filename.json", "asset_id_to_style4_filename.tsv", "validation.json"}
RECOVERY_IDS = {
    "analysis.heatmap.clustered", "analysis.heatmap.matrix", "analysis.volcano_plot.feature_labels", "analysis.volcano_plot.overview",
    "cellstress.cell.pyroptotic_cell.lytic", "cellstress.cell.pyroptotic_cell.pore_bearing",
    "cellstress.membrane_signaling.clathrin_coated_vesicle.cage_view", "cellstress.membrane_signaling.clathrin_coated_vesicle.section",
    "cellstress.organelle.nucleolus.nuclear_context", "cellstress.organelle.nucleolus.subcompartments",
    "cellstress.organelle.primary_cilium.bent", "cellstress.organelle.primary_cilium.straight",
    "tme.cancer_associated_fibroblast.matrix", "tme.cancer_associated_fibroblast.spindle",
    "tme.hypoxia_gradient.perivascular", "tme.hypoxia_gradient.spheroid",
}
METADATA_FILES = {"README.txt", "asset_id_to_filename.json", "asset_id_to_filename.tsv", "final_manifest.json", "final_audit.txt"}
ALLOWED_TAGS = {"svg", "title", "desc", "metadata", "g", "path", "ellipse", "rect", "circle", "text", "line", "polyline", "polygon", "tspan"}
DRAWABLE_TAGS = {"path", "ellipse", "rect", "circle", "text", "line", "polyline", "polygon", "tspan"}
ID_RE = re.compile(rb"(?<![\w:.-])id\s*=\s*([\"'])([^\"']+)\1")
GEOMETRY_ATTRS = {"d", "points", "x", "y", "x1", "y1", "x2", "y2", "cx", "cy", "r", "rx", "ry", "width", "height", "transform", "viewBox", "dx", "dy", "rotate", "textLength", "lengthAdjust"}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def json_bytes(value) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def safe_relative_path(value: str) -> str:
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value or ":" in value:
        raise ValueError(f"Unsafe relative path: {value!r}")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in ("..", ".") for part in value.split("/")) or "//" in value:
        raise ValueError(f"Unsafe relative path: {value!r}")
    return path.as_posix()


def read_archive(path: Path) -> dict[str, bytes]:
    files = {}
    seen = set()
    with zipfile.ZipFile(path) as archive:
        if len(archive.infolist()) > 600:
            raise ValueError("Archive contains too many entries")
        if sum(entry.file_size for entry in archive.infolist()) > 16 * 1024 * 1024:
            raise ValueError("Archive exceeds the 16 MiB unpacked limit")
        for entry in archive.infolist():
            name = safe_relative_path(entry.filename.rstrip("/"))
            folded = name.casefold()
            if folded in seen:
                raise ValueError(f"Duplicate archive path: {name}")
            seen.add(folded)
            mode = entry.external_attr >> 16
            if stat.S_ISLNK(mode):
                raise ValueError(f"Archive symlink is forbidden: {name}")
            if entry.flag_bits & 1:
                raise ValueError("Encrypted archive entries are unsupported")
            if entry.is_dir():
                continue
            if entry.file_size > 512 * 1024 or entry.file_size > max(entry.compress_size, 1) * 1000:
                raise ValueError(f"Unreasonable archive entry size: {name}")
            files[name] = archive.read(entry)
    return files


def load_catalog(library: Path) -> dict[str, dict]:
    catalog = {}
    descriptor = json.loads(library.read_text(encoding="utf-8"))
    for pack_ref in descriptor["packs"]:
        relative = safe_relative_path(pack_ref["path"])
        pack_path = library.parent / relative
        pack = json.loads(pack_path.read_text(encoding="utf-8"))
        for asset in pack["assets"]:
            if asset["id"] in catalog:
                raise ValueError(f"Duplicate source asset ID: {asset['id']}")
            original = (pack_path.parent / safe_relative_path(asset["file"])).read_bytes()
            catalog[asset["id"]] = {"asset": asset, "pack_id": pack_ref["id"], "original": original}
    return catalog


def local_name(name: str) -> str:
    return name.rsplit("}", 1)[-1]


def parse_svg(data: bytes, *, unique_ids: bool = False) -> ET.Element:
    if re.search(rb"<!\s*(?:DOCTYPE|ENTITY)", data, re.I):
        raise ValueError("DTD/entity declarations are forbidden")
    root = ET.fromstring(data)
    if local_name(root.tag) != "svg" or root.tag != "{http://www.w3.org/2000/svg}svg":
        raise ValueError("Expected an SVG namespace root")
    ids = set()
    drawable_count = 0
    for element in root.iter():
        tag = local_name(element.tag)
        if tag not in ALLOWED_TAGS:
            raise ValueError(f"Disallowed SVG tag: {tag}")
        drawable_count += tag in DRAWABLE_TAGS
        for key, value in element.attrib.items():
            attribute = local_name(key).lower()
            if attribute.startswith("on") or attribute in {"href", "src", "style", "filter"}:
                raise ValueError(f"Disallowed SVG attribute: {attribute}")
            if re.search(r"url\s*\(|(?:https?|data|javascript|file):", value, re.I):
                raise ValueError(f"SVG external/reference value is forbidden: {attribute}")
        identifier = element.get("id")
        if identifier and identifier in ids and unique_ids:
            raise ValueError(f"Duplicate SVG element ID: {identifier}")
        if identifier:
            ids.add(identifier)
    if not drawable_count:
        raise ValueError("SVG contains no vector artwork")
    return root


def normalize_duplicate_ids(data: bytes) -> tuple[bytes, list[dict]]:
    root = parse_svg(data)
    all_ids = {element.get("id") for element in root.iter() if element.get("id")}
    # No SVG references are allowed by parse_svg. Accessibility references may
    # retain the first occurrence; subsequent duplicates were never addressable.
    seen = collections.Counter()
    changes = []

    def replace(match):
        identifier = match.group(2).decode("utf-8")
        seen[identifier] += 1
        if seen[identifier] == 1:
            return match.group(0)
        suffix = seen[identifier]
        replacement = f"{identifier}--style4-{suffix}"
        while replacement in all_ids:
            suffix += 1
            replacement = f"{identifier}--style4-{suffix}"
        all_ids.add(replacement)
        changes.append({"original_id": identifier, "normalized_id": replacement, "occurrence": seen[identifier]})
        return match.group(0).replace(match.group(2), replacement.encode("utf-8"), 1)

    # Match opening tags only: source metadata JSON and text are never rewritten.
    normalized = re.sub(rb"<(?![!?/])[^>]+>", lambda match: ID_RE.sub(replace, match.group(0)), data)
    parse_svg(normalized, unique_ids=True)
    return normalized, changes


def restore_source_ids(data: bytes, changes: list[dict]) -> bytes:
    replacements = {entry["normalized_id"].encode("utf-8"): entry["original_id"].encode("utf-8") for entry in changes}
    return re.sub(rb"<(?![!?/])[^>]+>", lambda tag: ID_RE.sub(lambda match: match.group(0).replace(match.group(2), replacements.get(match.group(2), match.group(2)), 1), tag.group(0)), data)


def geometry_signature(root: ET.Element) -> str:
    values = []
    for element in root.iter():
        tag = local_name(element.tag)
        if tag in {"metadata", "title", "desc"}:
            continue
        values.append([tag, sorted((key, value) for key, value in element.attrib.items() if local_name(key) in GEOMETRY_ATTRS), element.text if tag in {"text", "tspan"} else None])
    return sha256(json.dumps(values, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))


def derive_regions(root: ET.Element, originals: list[dict]) -> list[dict]:
    observed: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    present = set()

    def visit(element: ET.Element, inherited: dict, region: str | None):
        paint = dict(inherited)
        for channel in ("fill", "stroke"):
            if channel in element.attrib:
                paint[channel] = element.attrib[channel]
        owner = element.get("data-region", region)
        if element.get("data-region"):
            present.add(owner)
        if local_name(element.tag) in DRAWABLE_TAGS and owner:
            for channel in ("fill", "stroke"):
                color = paint.get(channel, "#000000" if channel == "fill" else "none")
                if color.lower() not in {"none", "transparent"}:
                    if not re.fullmatch(r"#[0-9a-fA-F]{6}", color):
                        raise ValueError(f"Unsupported {channel} paint {color!r} in {owner}")
                    observed[owner][(channel, color.upper())] += 1
        for child in element:
            if local_name(child.tag) not in {"metadata", "title", "desc"}:
                visit(child, paint, owner)

    visit(root, {}, None)
    expected = {region["id"] for region in originals}
    if present != expected:
        raise ValueError(f"Semantic region coverage differs: missing={sorted(expected-present)}, extra={sorted(present-expected)}")
    result = []
    for original in originals:
        region = copy.deepcopy(original)
        paints = observed[region["id"]]
        if not paints:
            raise ValueError(f"Semantic region has no rendered paint: {region['id']}")
        requested = region.get("paint")
        available = {channel for channel, color in paints}
        requested_channels = {requested} if requested in {"fill", "stroke"} else {"fill", "stroke"}
        channels = requested_channels & available
        if not channels:
            channels = available
        # A supplied restyle can turn a filled accent into a stroked line.
        # Retain the original paint choice when present (a fixed contour must
        # not become a fill override), otherwise bind to the actual channel.
        region["paint"] = next(iter(channels)) if len(channels) == 1 else "both"
        preferred = [region["paint"]] if region["paint"] in {"fill", "stroke"} else (["stroke", "fill"] if region["id"] == "outline" else ["fill", "stroke"])
        selected = None
        for channel in preferred:
            candidates = [(color, count) for (paint, color), count in paints.items() if paint == channel and color != "#FFFFFF"]
            if not candidates:
                candidates = [(color, count) for (paint, color), count in paints.items() if paint == channel]
            if candidates:
                selected = max(candidates, key=lambda entry: entry[1])[0]
                break
        if selected is None:
            selected = paints.most_common(1)[0][0][1]
        region["default"] = selected
        region["default_paints"] = [{"paint": channel, "color": color} for channel, color in paints]
        result.append(region)
    return result


def load_recovery_selection(path: Path = RECOVERY_SELECTION) -> tuple[dict, bytes]:
    data = path.read_bytes()
    selection = json.loads(data.decode("utf-8"))
    entries = selection.get("assets", [])
    ids = [entry["asset_id"] for entry in entries]
    if len(ids) != 16 or set(ids) != RECOVERY_IDS or selection.get("asset_count") != 16:
        raise ValueError("Recovery selection must contain exactly the 16 reviewed asset IDs")
    if selection.get("source_archive") != {"filename": "style4_completed_16.zip", "sha256": RECOVERY_SHA256}:
        raise ValueError("Recovery selection source archive identity differs")
    for entry in entries:
        safe_relative_path(entry["member"])
        safe_relative_path(entry["final_archive_member"])
        if not entry["member"].startswith("svg/") or not entry["member"].endswith(".svg"):
            raise ValueError("Recovery selection member must be an SVG")
        for field in ("source_sha256", "final_replaced_sha256"):
            if not re.fullmatch(r"[a-f0-9]{64}", entry[field]):
                raise ValueError("Recovery selection source hashes are invalid")
    if sha256(data) != RECOVERY_SELECTION_SHA256:
        raise ValueError("Recovery selection SHA-256 differs from the reviewed finite decision")
    return selection, data


def apply_corrections(data: bytes, corrections: list[dict], *, reverse: bool = False) -> bytes:
    """Apply finite, recorded source-native patches; never guess at a node."""
    ordered = list(reversed(corrections)) if reverse else corrections
    for correction in ordered:
        patches = list(reversed(correction["patches"])) if reverse else correction["patches"]
        for patch in patches:
            before = patch["after" if reverse else "before"].encode("utf-8")
            after = patch["before" if reverse else "after"].encode("utf-8")
            if not before or data.count(before) != 1:
                raise ValueError(f"SVG correction must match exactly one source node: {correction['id']}")
            data = data.replace(before, after, 1)
    return data


def svg_live_labels(root: ET.Element) -> list[str]:
    return sorted("".join(element.itertext()) for element in root.iter() if local_name(element.tag) == "text")


def read_recovery_archive(path: Path, selection: dict) -> dict[str, bytes]:
    if not path.is_file():
        raise ValueError("The exact style4_completed_16.zip recovery archive is required")
    if sha256(path.read_bytes()) != RECOVERY_SHA256:
        raise ValueError("Recovery archive SHA-256 differs from the reviewed original")
    files = read_archive(path)
    if not RECOVERY_METADATA_FILES <= files.keys():
        raise ValueError("Recovery archive is missing its original metadata")
    mapping = json.loads(files["asset_id_to_style4_filename.json"].decode("utf-8"))
    entries = {entry["asset_id"]: entry for entry in selection["assets"]}
    if set(mapping) != RECOVERY_IDS or set(p for p in files if p.endswith(".svg")) != {entry["member"] for entry in entries.values()}:
        raise ValueError("Recovery archive must contain exactly the reviewed 16 mapped SVGs")
    for identifier, entry in entries.items():
        if mapping[identifier] != entry["member"] or sha256(files[entry["member"]]) != entry["source_sha256"]:
            raise ValueError(f"Recovery source mapping or member SHA-256 differs: {identifier}")
    return files


def build_import(archive_path: Path, library: Path = LIBRARY, *, expected_count: int = 486, expected_archive_sha: str | None = SOURCE_SHA256,
                 recovery_archive: Path | None = None, recovery_selection: Path | None = None) -> dict[str, bytes]:
    archive_data = archive_path.read_bytes()
    archive_hash = sha256(archive_data)
    if expected_archive_sha and archive_hash != expected_archive_sha:
        raise ValueError("Source archive SHA-256 does not match the reviewed complete package")
    files = read_archive(archive_path)
    if not METADATA_FILES <= files.keys():
        raise ValueError("Archive is missing its source mapping/manifest metadata")
    mapping = json.loads(files["asset_id_to_filename.json"].decode("utf-8"))
    source_records = json.loads(files["final_manifest.json"].decode("utf-8"))
    source_manifest = {}
    for record in source_records:
        if record["asset_id"] in source_manifest:
            raise ValueError(f"Duplicate source manifest ID: {record['asset_id']}")
        source_manifest[record["asset_id"]] = record
    catalog = load_catalog(library)
    if len(catalog) != expected_count or set(mapping) != set(catalog) or set(source_manifest) != set(catalog):
        raise ValueError(f"Expected exact {expected_count}-asset mapping/catalog/source-manifest coverage")
    expected_svg = set()
    for identifier, filename in mapping.items():
        if safe_relative_path(filename) != Path(filename).name or not filename.endswith(".svg"):
            raise ValueError(f"Unsafe source SVG filename: {filename}")
        if source_manifest[identifier]["filename"] != filename:
            raise ValueError(f"Source mapping/manifest filename differs: {identifier}")
        expected_svg.add("svg/" + filename)
    if len(expected_svg) != expected_count or set(files) != expected_svg | METADATA_FILES:
        raise ValueError("Archive SVG coverage is not exact, unique and complete")
    recovery = None
    recovery_data = None
    selected = {}
    recovery_files = {}
    if expected_count == 486 or recovery_selection is not None:
        recovery, recovery_data = load_recovery_selection(recovery_selection or RECOVERY_SELECTION)
        recovery_archive = recovery_archive or archive_path.parent / recovery["source_archive"]["filename"]
        # This archive contains preview PNGs, which are read as inert bytes for
        # inventory safety only. Only selected SVGs and metadata are imported.
        recovery_files = read_recovery_archive(recovery_archive, recovery)
        selected = {entry["asset_id"]: entry for entry in recovery["assets"]}
        for identifier, entry in selected.items():
            if entry["final_archive_member"] != "svg/" + mapping[identifier]:
                raise ValueError(f"Recovery member mapping differs: {identifier}")
            if sha256(recovery_files[entry["member"]]) != entry["source_sha256"] or sha256(files[entry["final_archive_member"]]) != entry["final_replaced_sha256"]:
                raise ValueError(f"Recovery or replaced final source SHA-256 differs: {identifier}")
    output = {}
    assets = []
    for identifier in sorted(catalog):
        original = catalog[identifier]["asset"]
        filename = "svg/" + mapping[identifier]
        recovery_entry = selected.get(identifier)
        source = recovery_files[recovery_entry["member"]] if recovery_entry else files[filename]
        source_root = parse_svg(source)
        original_root = ET.fromstring(catalog[identifier]["original"])
        if source_root.get("viewBox") != original_root.get("viewBox"):
            raise ValueError(f"Style 4/source viewBox differs: {identifier}")
        if recovery_entry and svg_live_labels(source_root) != svg_live_labels(original_root):
            raise ValueError(f"Recovered live scientific labels differ: {identifier}")
        corrections = recovery_entry.get("corrections", []) if recovery_entry else []
        corrected = apply_corrections(source, corrections)
        corrected_root = parse_svg(corrected)
        imported, id_changes = normalize_duplicate_ids(corrected)
        imported_root = parse_svg(imported, unique_ids=True)
        if geometry_signature(corrected_root) != geometry_signature(imported_root):
            raise ValueError(f"Import changed artwork geometry: {identifier}")
        if apply_corrections(restore_source_ids(imported, id_changes), corrections, reverse=True) != source:
            raise ValueError(f"ID normalization was not byte-reversible: {identifier}")
        record = {
            "asset_id": identifier, "name": original["name"], "file": filename,
            "sha256": sha256(imported), "source_sha256": sha256(source),
            "source_filename": mapping[identifier], "source_pack_id": catalog[identifier]["pack_id"],
            "source_record": source_manifest[identifier],
            "geometry_sha256": geometry_signature(imported_root), "viewBox": source_root.get("viewBox"),
            "editable_color_regions": derive_regions(imported_root, original["editable_color_regions"]),
            "id_normalizations": id_changes,
        }
        if recovery_entry:
            record["source_provenance"] = {"archive_filename": recovery["source_archive"]["filename"], "archive_sha256": RECOVERY_SHA256,
                "member": recovery_entry["member"], "source_sha256": recovery_entry["source_sha256"],
                "final_archive_member": recovery_entry["final_archive_member"], "final_replaced_sha256": recovery_entry["final_replaced_sha256"],
                "reason": recovery_entry["reason"], "corrections": corrections}
        assets.append(record)
        output[filename] = imported
    source_metadata = []
    for filename in sorted(METADATA_FILES):
        output["source/" + filename] = files[filename]
        source_metadata.append({"file": "source/" + filename, "sha256": sha256(files[filename])})
    if recovery:
        output["recovery-selection.json"] = recovery_data
        for filename in sorted(RECOVERY_METADATA_FILES):
            output["source/recovery/" + filename] = recovery_files[filename]
            source_metadata.append({"file": "source/recovery/" + filename, "sha256": sha256(recovery_files[filename])})
    manifest = {
        "schema_version": "1.0.0", "id": "style-4", "name": "Style 4", "asset_count": len(assets),
        "source_archive": {"filename": archive_path.name, "sha256": archive_hash},
        "source_metadata": source_metadata,
        "provenance": "Owner-provided ChatGPT-generated Style 4 derivatives of the existing Superbench scientific asset library, requested for additive Library integration on 2026-10-17. Original archive and embedded source metadata are retained; this record does not invent a new license or historical product approval.",
        "import_transformations": "Only duplicate SVG element IDs are made unique. Per-file changes are byte-reversible and recorded below. Supplied geometry, labels, paint, white details and fixed decorations are unchanged.",
        "color_defaults": "Derived from actual inherited SVG paint within the nearest semantic region. default_paints records all authored channel colors; full original SVG restoration preserves multicolor regions.",
        "assets": assets,
    }
    if recovery:
        manifest["recovery_archive"] = {**recovery["source_archive"], "selection_file": "recovery-selection.json", "selection_sha256": sha256(recovery_data), "asset_count": 16}
        manifest["import_transformations"] = "Sixteen explicitly selected earlier supplied redraws are restored with per-file archive/member provenance. Four narrow decorative path corrections and duplicate SVG element-ID repairs are byte-reversible and recorded in the finite recovery selection/per-file records. Biological outlines, live labels, semantic identities, viewBoxes and all other supplied artwork bytes are unchanged."
    output["manifest.json"] = json_bytes(manifest)
    output["README.md"] = ("# Style 4\n\nOwner-provided alternate drawings for all 486 existing Library asset IDs. Select Style 4 to preview and insert this supplied artwork; the original drawings and Styles 1–3 remain available.\n\nThe complete archive is the source; earlier batch downloads are unnecessary. `manifest.json` binds its SHA-256, all 486 source/imported SVG hashes, exact ID mapping, geometry, semantic color regions and any duplicate-ID repairs. `source/` retains all five original package metadata files. Embedded SVG source metadata is left intact; its Style 1 reset defaults are historical source records, so the manifest derives Style 4 defaults from actual artwork paint. Full SVG restoration preserves multicolor shading, white details and fixed decorations.\n\nIndependent comparison of the supplied archive against the existing Style 1 drawings found 243 of 486 pairs pixel-identical when rendered at 256 × 256 in Chromium. This is complete supplied-asset coverage, not a claim of 486 visibly different redraws. No substitute artwork is invented for unchanged inputs. The bounded comparison is recorded in the 17 October Style 4 archive audit.\n\nThese are user-provided derivatives of the existing original vectors. Existing source-pack license terms remain recorded in those packs and the SVG metadata; this import does not assert a new blanket license or rewrite previous release approvals. Scientific labels, geometry and limitations are preserved from the supplied artwork. Analytical graphics are illustrative templates, not measured results.\n\nReproduce with `python scripts/import-style4-library.py --source-archive <original ZIP>`. Verify committed files with `python scripts/validate-style4-library.py`; add `--source-archive <original ZIP>` to verify exact reproducibility against the download.\n").encode("utf-8")
    if recovery:
        readme = output["README.md"].decode("utf-8")
        readme = readme.replace("The complete archive is the source; earlier batch downloads are unnecessary.",
            "The complete final archive supplies the stable mapping and 470 drawings; 16 independently reviewed earlier redraws come from `style4_completed_16.zip`. `recovery-selection.json` records the exact finite recovery decision, both source hashes and any narrowly scoped decorative corrections.")
        readme = readme.replace("all five original package metadata files", "all five final-package metadata files and four original recovery-package metadata files")
        readme = readme.replace("No substitute artwork is invented for unchanged inputs.",
            "The full Downloads history audit found 16 usable earlier redraws in the owner's completed package; those earlier redraws replace eight final drawings that were pixel-identical to Style 1 and eight other final drawings with only modest restyling. After recovery, 235 drawings remain pixel-identical to Style 1 and 16 have only small differences at that audit scale. No substitute artwork is invented for the remaining unchanged inputs.")
        readme = readme.replace("Scientific labels, geometry and limitations are preserved from the supplied artwork.",
            "Scientific labels, biological outlines and limitations are preserved from the supplied artwork.")
        readme += "\nRecovery preserves every source live label, semantic region and viewBox. Four recorded path-only corrections keep decorative depth/highlight shapes or an internal filament inside unchanged cell/nuclear contours; they do not change biological outlines. Import checks can reverse these corrections and duplicate-ID repairs to recover the exact original member bytes. Pass `--recovery-archive <style4_completed_16.zip>` explicitly, or keep that exact archive beside the final ZIP for automatic discovery. Both full archive SHA-256 values must match. CI validation of committed files does not require Downloads.\n"
        output["README.md"] = readme.encode("utf-8")
    return output


def write_import(files: dict[str, bytes], output_dir: Path, *, check: bool = False):
    if output_dir.is_symlink() or (hasattr(output_dir, "is_junction") and output_dir.is_junction()):
        raise ValueError("Output directory must not be a symlink or junction")
    output_dir = output_dir.resolve()
    if output_dir.exists():
        existing = {file.relative_to(output_dir).as_posix() for file in output_dir.rglob("*") if file.is_file()}
        unexpected = existing - set(files)
        if unexpected:
            raise ValueError(f"Output contains unexpected files; nothing changed: {sorted(unexpected)}")
    targets = []
    for relative, data in files.items():
        target = output_dir / safe_relative_path(relative)
        if any(parent.is_symlink() or (hasattr(parent, "is_junction") and parent.is_junction()) for parent in [target, *target.parents] if parent != output_dir.parent):
            raise ValueError(f"Output path includes a symlink or junction: {relative}")
        targets.append((relative, target, data))
    for relative, target, data in targets:
        if check:
            if not target.is_file() or target.read_bytes() != data:
                raise ValueError(f"Imported output differs from reproducible source: {relative}")
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-archive", type=Path, required=True)
    parser.add_argument("--recovery-archive", type=Path, help="Exact original style4_completed_16.zip; otherwise discovered beside the final archive with strict SHA verification")
    parser.add_argument("--library", type=Path, default=LIBRARY)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "assets/scientific-packs/style-4")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        files = build_import(args.source_archive, args.library, recovery_archive=args.recovery_archive)
        write_import(files, args.output_dir, check=args.check)
    except (ValueError, OSError, KeyError, ET.ParseError, zipfile.BadZipFile, json.JSONDecodeError) as error:
        print(f"Style 4 import failed: {error}", file=sys.stderr)
        return 1
    print(f"Style 4 {'verified' if args.check else 'imported'}: 486 SVGs, {len(files)} files; exact source provenance verified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
