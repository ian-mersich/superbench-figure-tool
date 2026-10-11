#!/usr/bin/env python3
"""Validate Figure Tool scientific asset packs and the installed library.

Pack validation remains backwards-compatible with the historical Core Biology
release.  Library validation adds registry, cross-pack identity, search-term,
rights-record, and exact-vector duplicate checks for independently released
packs.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from datetime import date
import hashlib
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path, PurePosixPath


REPO_ROOT = Path(__file__).resolve().parents[1]
PACKS_ROOT = REPO_ROOT / "assets" / "scientific-packs"
DEFAULT_PACK = PACKS_ROOT / "core-biology" / "asset-pack.json"
DEFAULT_LIBRARY = PACKS_ROOT / "library.json"
CORE_PACK_ID = "core-biology"
EXPANSION_PACK_ID = "core-experimental-biology"
IMMUNOLOGY_ONCOLOGY_PACK_ID = "immunology-oncology"
CORE_ASSET_COUNT = 108
EXPANSION_ASSET_COUNT = 111
EXPANSION_CONCEPT_COUNT = 103
CORE_AUDIT_ID = "core-biology.provenance-license-release.2026-07-20"
CORE_AUDIT_DATE = "2026-07-20"
CORE_CATALOG_SHA256 = "f1c3ba520939b1a204ff528d702a71571ae1256d5c0206f793d107893487b9bc"
CORE_AUDIT_SHA256 = "0248f1092c1f476aa7d69b0f9cd45baa5f96785f5b82b1c61aca804cab94dcd7"
HEX_COLOR = re.compile(r"^#[0-9A-Fa-f]{6}$")
ASSET_ID = re.compile(r"^[a-z0-9]+(\.[a-z0-9_]+)+$")
RECORD_ID = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
DISALLOWED_SVG_TAGS = {
    "script",
    "style",
    "foreignObject",
    "image",
    "iframe",
    "object",
    "embed",
}
ALLOWED_CATEGORIES = {
    "cell",
    "organelle",
    "nucleic-acid",
    "protein",
    "membrane-signaling",
    "lab-equipment",
    "pathway-symbol",
    "model-system",
    "clinical-sample",
    "assay-workflow",
}

SUPPORTED_CONNECTOR_ROLES = {
    "input",
    "output",
    "bidirectional",
    "attachment",
}

MODERN_ASSET_REQUIRED_FIELDS = {
    "scientific_name",
    "synonyms",
    "subcategory",
    "source_record_id",
    "rights_record_id",
}

LIBRARY_REQUIRED_FIELDS = {"schema_version", "id", "packs"}
LIBRARY_PACK_REQUIRED_FIELDS = {
    "id",
    "path",
    "asset_count",
    "concept_count",
    "enabled",
    "modes",
}

PACK_REQUIRED_FIELDS = {
    "schema_version",
    "id",
    "name",
    "description",
    "style_family",
    "qa_status",
    "release_audit",
    "style_tokens",
    "source_policy",
    "license_definitions",
    "assets",
}

ASSET_REQUIRED_FIELDS = {
    "id",
    "name",
    "category",
    "tags",
    "file",
    "source_type",
    "license",
    "provenance",
    "style_family",
    "review_status",
    "style_status",
    "reviewer_notes",
    "mvp_quality",
    "editable_region_count",
    "editable_color_regions",
}

REGION_REQUIRED_FIELDS = {"id", "label", "default"}
RELEASE_AUDIT_REFERENCE_FIELDS = {
    "file",
    "audit_id",
    "status",
    "asset_count",
    "public_distribution_authorized",
    "selected_public_license",
    "license_notice",
}
RELEASE_AUDIT_REQUIRED_FIELDS = {
    "schema_id",
    "audit_id",
    "audit_date",
    "pack_id",
    "status",
    "release_effective_date",
    "asset_count",
    "rights_cleared_count",
    "third_party_component_count",
    "license_selection_pending_count",
    "public_distribution_authorized",
    "selected_public_license",
    "license_notice",
    "rights_basis",
    "source_records",
    "license_candidates",
    "release_blocker",
    "assets",
}
RELEASE_ASSET_REQUIRED_FIELDS = {
    "asset_id",
    "file",
    "sha256",
    "provenance_sha256",
    "source_type",
    "lineage",
    "current_license",
    "rights_basis",
    "third_party_material",
    "provenance_status",
    "release_disposition",
}


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def fail(message: str) -> None:
    raise ValueError(message)


def canonical_relative_file(value: object, *, label: str, suffix: str) -> PurePosixPath:
    if not isinstance(value, str) or not value or value != value.strip():
        fail(f"{label} must be a non-empty canonical relative path")
    if "\\" in value:
        fail(f"{label} must use forward slashes")
    relative = PurePosixPath(value)
    if relative.is_absolute() or any(part in {"", ".", ".."} for part in relative.parts):
        fail(f"{label} must be a canonical relative path")
    if relative.suffix.lower() != suffix:
        fail(f"{label} must end in {suffix}")
    return relative


def exact_pack_file(pack_dir: Path, relative: PurePosixPath, *, label: str) -> Path:
    current = pack_dir
    for part in relative.parts:
        if current.is_symlink():
            fail(f"{label} must not traverse a symlink: {relative.as_posix()}")
        if not current.is_dir():
            fail(f"{label} parent is not a directory: {relative.as_posix()}")
        names = {child.name for child in current.iterdir()}
        if part not in names:
            if any(name.casefold() == part.casefold() for name in names):
                fail(f"{label} has case drift: {relative.as_posix()}")
            fail(f"{label} is missing: {relative.as_posix()}")
        current = current / part
    if current.is_symlink():
        fail(f"{label} must not be a symlink: {relative.as_posix()}")
    if not current.is_file():
        fail(f"{label} is not a regular file: {relative.as_posix()}")
    return current


def load_pack(path: Path) -> dict:
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except json.JSONDecodeError as error:
        fail(f"{path}: invalid JSON: {error}")


def require_non_empty_string(value: object, *, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        fail(f"{label} must be a non-empty trimmed string")
    return value


def normalize_search_term(value: str) -> str:
    """Normalize a scientific search term for duplicate detection only."""

    return " ".join(re.findall(r"[a-z0-9]+", value.casefold()))


def validate_record_table(pack: dict, field_name: str, *, required: bool) -> set[str]:
    records = pack.get(field_name)
    if records is None and not required:
        return set()
    if not isinstance(records, list) or not records:
        fail(f"{field_name} must be a non-empty list")
    record_ids: set[str] = set()
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            fail(f"{field_name}[{index}] must be an object")
        record_id = require_non_empty_string(
            record.get("id"), label=f"{field_name}[{index}].id"
        )
        if not RECORD_ID.fullmatch(record_id):
            fail(f"{field_name}[{index}].id must use lowercase stable-id characters")
        if record_id in record_ids:
            fail(f"{field_name} contains duplicate id {record_id!r}")
        record_ids.add(record_id)
    return record_ids


def validate_modern_release_records(pack: dict) -> None:
    pack_id = str(pack.get("id") or "")
    release_reference = pack.get("release_audit") or {}
    source_records = pack.get("source_records") or []
    rights_records = pack.get("rights_records") or []
    if len(source_records) != 1 or len(rights_records) != 1:
        fail("modern pack must use one pack-scoped source record and one rights record")
    source = source_records[0]
    rights = rights_records[0]
    expected_source = {
        "kind": "clean_room_generation_record",
        "pack_id": pack_id,
        "scope": "all_assets_in_pack",
        "third_party_material": "none_declared",
    }
    expected_rights = {
        "kind": "owner_release_authorization",
        "pack_id": pack_id,
        "scope": "all_assets_in_pack",
        "status": "released",
        "public_distribution_authorized": True,
        "selected_public_license": "CC0-1.0",
        "rights_basis": "owner_attested_original_output",
        "third_party_material": "none_declared",
        "effective_date": release_reference.get("release_effective_date"),
    }
    if release_reference.get("status") == "draft_review_pending":
        expected_rights.update({
            "kind": "draft_rights_review",
            "status": "draft_review_pending",
            "public_distribution_authorized": False,
            "selected_public_license": None,
            "rights_basis": "original_output_pending_owner_review",
            "effective_date": None,
        })
    elif release_reference.get("status") == "rights_cleared_quality_pending":
        expected_rights.update({
            "kind": "owner_license_grant",
            "status": "rights_cleared",
            "public_distribution_authorized": True,
            "selected_public_license": "CC0-1.0",
            "rights_basis": "owner_attested_original_output",
            "effective_date": release_reference.get("rights_grant_effective_date"),
        })
    for label, record, expected in (
        ("source record", source, expected_source),
        ("rights record", rights, expected_rights),
    ):
        for key, expected_value in expected.items():
            if record.get(key) != expected_value:
                fail(
                    f"modern-pack {label} {key} must be {expected_value!r}; "
                    f"found {record.get(key)!r}"
                )
    source_date = validate_iso_date(source.get("created_on"), label="modern-pack source created_on")
    audit_date = validate_iso_date(
        release_reference.get("audit_date"), label="modern-pack release audit_date"
    )
    if source_date > audit_date:
        fail("modern-pack source created_on cannot be later than its release audit_date")
    require_non_empty_string(
        source.get("generated_by"), label="modern-pack source record generated_by"
    )
    for label, value in (
        ("source record statement", source.get("statement")),
        ("rights record statement", rights.get("statement")),
        ("rights record qualification", rights.get("qualification")),
    ):
        if not isinstance(value, str) or len(value.strip()) < 40:
            fail(f"modern-pack {label} must be a substantive string")
    if re.search(r"[A-Za-z]:\\", json.dumps([source, rights])):
        fail("modern-pack source and rights records must not expose absolute local Windows paths")


# Retained for tests and downstream callers written against the first modern pack.
validate_expansion_release_records = validate_modern_release_records


def validate_connector_hints(asset_id: str, asset: dict) -> None:
    hints = asset.get("connector_hints")
    if hints is None:
        return
    if not isinstance(hints, list) or not hints:
        fail(f"{asset_id}: connector_hints must be a non-empty list when declared")
    seen_ids: set[str] = set()
    for index, hint in enumerate(hints):
        if not isinstance(hint, dict):
            fail(f"{asset_id}: connector_hints[{index}] must be an object")
        missing = {"id", "role", "x", "y"} - hint.keys()
        if missing:
            fail(f"{asset_id}: connector hint missing fields: {sorted(missing)}")
        hint_id = require_non_empty_string(
            hint.get("id"), label=f"{asset_id}: connector_hints[{index}].id"
        )
        if not RECORD_ID.fullmatch(hint_id):
            fail(f"{asset_id}: connector hint id must use lowercase stable-id characters")
        if hint_id in seen_ids:
            fail(f"{asset_id}: duplicate connector hint id {hint_id!r}")
        seen_ids.add(hint_id)
        role = hint.get("role")
        if role not in SUPPORTED_CONNECTOR_ROLES:
            fail(
                f"{asset_id}: connector hint {hint_id!r} role {role!r} is unsupported; "
                f"expected one of {sorted(SUPPORTED_CONNECTOR_ROLES)}"
            )
        for axis in ("x", "y"):
            coordinate = hint.get(axis)
            if (
                isinstance(coordinate, bool)
                or not isinstance(coordinate, (int, float))
                or not 0 <= coordinate <= 1
            ):
                fail(
                    f"{asset_id}: connector hint {hint_id!r} {axis} must be a normalized number from 0 to 1"
                )


def validate_modern_asset_metadata(
    asset: dict,
    source_record_ids: set[str],
    rights_record_ids: set[str],
) -> None:
    asset_id = asset.get("id", "<missing id>")
    missing = MODERN_ASSET_REQUIRED_FIELDS - asset.keys()
    if missing:
        fail(f"{asset_id}: modern asset missing fields: {sorted(missing)}")

    scientific_name = require_non_empty_string(
        asset.get("scientific_name"), label=f"{asset_id}: scientific_name"
    )
    subcategory = require_non_empty_string(
        asset.get("subcategory"), label=f"{asset_id}: subcategory"
    )
    if normalize_search_term(scientific_name) == "":
        fail(f"{asset_id}: scientific_name must contain searchable letters or numbers")
    if normalize_search_term(subcategory) == "":
        fail(f"{asset_id}: subcategory must contain searchable letters or numbers")

    synonyms = asset.get("synonyms")
    if not isinstance(synonyms, list) or not synonyms:
        fail(f"{asset_id}: synonyms must be a non-empty list")
    normalized_terms = {normalize_search_term(scientific_name)}
    for index, synonym in enumerate(synonyms):
        value = require_non_empty_string(
            synonym, label=f"{asset_id}: synonyms[{index}]"
        )
        normalized = normalize_search_term(value)
        if not normalized:
            fail(f"{asset_id}: synonyms[{index}] must contain searchable letters or numbers")
        if normalized in normalized_terms:
            fail(f"{asset_id}: scientific_name and synonyms must be unique after normalization")
        normalized_terms.add(normalized)

    source_record_id = require_non_empty_string(
        asset.get("source_record_id"), label=f"{asset_id}: source_record_id"
    )
    rights_record_id = require_non_empty_string(
        asset.get("rights_record_id"), label=f"{asset_id}: rights_record_id"
    )
    if source_record_id not in source_record_ids:
        fail(f"{asset_id}: source_record_id {source_record_id!r} is not present in source_records")
    if rights_record_id not in rights_record_ids:
        fail(f"{asset_id}: rights_record_id {rights_record_id!r} is not present in rights_records")

    concept_id = require_non_empty_string(
        asset.get("concept_id"), label=f"{asset_id}: concept_id"
    )
    if not ASSET_ID.fullmatch(concept_id):
        fail(f"{asset_id}: concept_id must use dot-delimited lowercase tokens")
    validate_connector_hints(str(asset_id), asset)


# Retained for tests and downstream callers written against the first modern pack.
validate_expansion_asset_metadata = validate_modern_asset_metadata


def validate_region_schema(asset_id: str, regions: list[dict]) -> set[str]:
    if not isinstance(regions, list) or not regions:
        fail(f"{asset_id}: editable_color_regions must be a non-empty list")

    seen: set[str] = set()
    for index, region in enumerate(regions):
        if not isinstance(region, dict):
            fail(f"{asset_id}: editable_color_regions[{index}] must be an object")
        missing = REGION_REQUIRED_FIELDS - region.keys()
        if missing:
            fail(f"{asset_id}: color region missing fields: {sorted(missing)}")
        region_id = region["id"]
        if not isinstance(region_id, str) or not region_id:
            fail(f"{asset_id}: color region id must be a non-empty string")
        if region_id in seen:
            fail(f"{asset_id}: duplicate color region id {region_id!r}")
        if not isinstance(region["label"], str) or not region["label"].strip():
            fail(f"{asset_id}: region {region_id!r} label must be a non-empty string")
        if not isinstance(region["default"], str) or not HEX_COLOR.fullmatch(
            region["default"]
        ):
            fail(f"{asset_id}: region {region_id!r} default must be a 6-digit hex color")
        seen.add(region_id)
    return seen


def parse_viewbox(asset_id: str, svg_path: Path, viewbox: str) -> tuple[float, float, float, float]:
    parts = viewbox.replace(",", " ").split()
    if len(parts) != 4:
        fail(f"{asset_id}: {svg_path}: viewBox must contain four numbers")
    try:
        return tuple(float(part) for part in parts)  # type: ignore[return-value]
    except ValueError:
        fail(f"{asset_id}: {svg_path}: viewBox contains a non-numeric value")


def validate_svg(
    asset_id: str,
    svg_path: Path,
    metadata_regions: set[str],
    expected_viewbox: str | None,
) -> None:
    try:
        root = ET.parse(svg_path).getroot()
    except ET.ParseError as error:
        fail(f"{asset_id}: {svg_path}: invalid SVG XML: {error}")

    if local_name(root.tag) != "svg":
        fail(f"{asset_id}: {svg_path}: root element must be <svg>")
    viewbox = root.attrib.get("viewBox")
    if not viewbox:
        fail(f"{asset_id}: {svg_path}: missing viewBox")
    if expected_viewbox and viewbox != expected_viewbox:
        fail(f"{asset_id}: {svg_path}: viewBox {viewbox!r} must match pack style token {expected_viewbox!r}")
    min_x, min_y, width, height = parse_viewbox(asset_id, svg_path, viewbox)
    if width <= 0 or height <= 0:
        fail(f"{asset_id}: {svg_path}: viewBox width and height must be positive")
    if min_x != 0 or min_y != 0:
        fail(f"{asset_id}: {svg_path}: viewBox should start at 0 0 for predictable insertion")

    svg_regions: set[str] = set()
    element_ids: set[str] = set()
    local_hrefs: list[str] = []
    titles = 0
    descriptions = 0
    for element in root.iter():
        tag = local_name(element.tag)
        if tag in DISALLOWED_SVG_TAGS:
            fail(f"{asset_id}: {svg_path}: disallowed SVG tag <{tag}>; embedded rasters and unsafe SVG containers are not allowed in scientific assets")
        if tag == "title":
            if not "".join(element.itertext()).strip():
                fail(f"{asset_id}: {svg_path}: SVG title must not be empty")
            titles += 1
        if tag == "desc":
            if not "".join(element.itertext()).strip():
                fail(f"{asset_id}: {svg_path}: SVG desc must not be empty")
            descriptions += 1

        region = element.attrib.get("data-region")
        if region:
            svg_regions.add(region)

        element_id = element.attrib.get("id")
        if element_id:
            if element_id in element_ids:
                fail(f"{asset_id}: {svg_path}: duplicate SVG element id {element_id!r}")
            element_ids.add(element_id)

        for attr_name, value in element.attrib.items():
            attribute = local_name(attr_name)
            if attribute.casefold().startswith("on"):
                fail(f"{asset_id}: {svg_path}: SVG event-handler attributes are not allowed")
            if attribute == "href":
                href = value.strip()
                if not href.startswith("#") or len(href) == 1:
                    fail(
                        f"{asset_id}: {svg_path}: external or embedded href {value!r} is not allowed; "
                        "only verified in-document #id references are permitted"
                    )
                local_hrefs.append(href[1:])
            if "url(" in value.lower():
                fail(f"{asset_id}: {svg_path}: paint/server url() references are not allowed in seed assets")

    missing_local_references = sorted(set(local_hrefs) - element_ids)
    if missing_local_references:
        fail(
            f"{asset_id}: {svg_path}: href references missing in-document ids "
            f"{missing_local_references}"
        )

    if titles == 0 or descriptions == 0:
        fail(f"{asset_id}: {svg_path}: SVG should include title and desc for accessible previews")
    if not svg_regions:
        fail(
            f"{asset_id}: {svg_path}: metadata declares editable regions {sorted(metadata_regions)} "
            "but the SVG has no data-region annotations; add matching SVG data-region attributes or update asset metadata"
        )
    missing_in_svg = metadata_regions - svg_regions
    missing_in_metadata = svg_regions - metadata_regions
    if missing_in_svg or missing_in_metadata:
        details = []
        if missing_in_svg:
            details.append(f"metadata editable_color_regions missing from SVG data-region annotations: {sorted(missing_in_svg)}")
        if missing_in_metadata:
            details.append(f"SVG data-region values missing from metadata editable_color_regions: {sorted(missing_in_metadata)}")
        fail(
            f"{asset_id}: {svg_path}: region mismatch between SVG data-region annotations and metadata; "
            f"{'; '.join(details)}. Fix the SVG data-region values or update editable_color_regions so they match exactly."
        )
    if "outline" not in svg_regions:
        fail(f"{asset_id}: {svg_path}: SVG must include an outline data-region")


def validate_asset(
    asset: dict,
    pack: dict,
    pack_dir: Path,
    license_definitions: dict,
    expected_viewbox: str | None,
    seen_ids: set[str],
    seen_files: dict[str, str],
    *,
    require_modern_metadata: bool = False,
    source_record_ids: set[str] | None = None,
    rights_record_ids: set[str] | None = None,
) -> None:
    if not isinstance(asset, dict):
        fail("asset entries must be objects")
    missing = ASSET_REQUIRED_FIELDS - asset.keys()
    asset_id = asset.get("id", "<missing id>")
    if missing:
        fail(f"{asset_id}: asset missing fields: {sorted(missing)}")
    if not isinstance(asset_id, str) or not ASSET_ID.fullmatch(asset_id):
        fail(f"{asset_id}: id must use dot-delimited lowercase tokens")
    if asset_id in seen_ids:
        fail(f"{asset_id}: duplicate asset id")
    seen_ids.add(asset_id)

    for field in ("name", "category", "source_type", "license", "review_status", "style_status", "reviewer_notes", "mvp_quality"):
        if not isinstance(asset[field], str) or not asset[field].strip():
            fail(f"{asset_id}: {field} must be a non-empty string")
    if asset["category"] not in ALLOWED_CATEGORIES:
        fail(f"{asset_id}: category {asset['category']!r} is not in the allowed MVP category set")
    allowed_style_families = pack.get("style_families") or [pack["style_family"]]
    if asset["style_family"] not in allowed_style_families:
        fail(f"{asset_id}: style_family must be declared by pack style_family or style_families")
    if asset["license"] not in license_definitions:
        fail(f"{asset_id}: license {asset['license']!r} is not defined in license_definitions")
    if (
        not isinstance(asset["tags"], list)
        or not asset["tags"]
        or not all(isinstance(tag, str) and tag.strip() and tag == tag.strip() for tag in asset["tags"])
    ):
        fail(f"{asset_id}: tags must be a non-empty list of strings")
    if not isinstance(asset["provenance"], str) or len(asset["provenance"].strip()) < 40:
        fail(f"{asset_id}: provenance must be a meaningful string")

    relative_svg = canonical_relative_file(asset["file"], label=f"{asset_id}: file", suffix=".svg")
    canonical_file = relative_svg.as_posix()
    prior_file = seen_files.get(canonical_file.casefold())
    if prior_file is not None:
        fail(f"{asset_id}: duplicate or case-equivalent SVG path {canonical_file!r}; already used by {prior_file}")
    seen_files[canonical_file.casefold()] = asset_id
    svg_path = exact_pack_file(pack_dir, relative_svg, label=f"{asset_id}: SVG file")

    metadata_regions = validate_region_schema(asset_id, asset["editable_color_regions"])
    if asset["editable_region_count"] != len(metadata_regions):
        fail(f"{asset_id}: editable_region_count must match editable_color_regions length")
    validate_svg(asset_id, svg_path, metadata_regions, expected_viewbox)
    validate_connector_hints(asset_id, asset)
    if require_modern_metadata:
        validate_modern_asset_metadata(
            asset,
            source_record_ids or set(),
            rights_record_ids or set(),
        )


def validate_concept_variants(assets: list[dict]) -> None:
    groups: dict[str, list[dict]] = {}
    for asset in assets:
        asset_id = asset.get("id", "<missing id>")
        concept_id = asset.get("concept_id")
        style_variant = asset.get("style_variant")
        if bool(concept_id) != bool(style_variant):
            fail(f"{asset_id}: concept_id and style_variant must be declared together")
        if not concept_id:
            continue
        if not isinstance(concept_id, str) or not ASSET_ID.match(concept_id):
            fail(f"{asset_id}: concept_id must use dot-delimited lowercase tokens")
        if not isinstance(style_variant, str) or not style_variant.strip():
            fail(f"{asset_id}: style_variant must be a non-empty string")
        groups.setdefault(concept_id, []).append(asset)

    for concept_id, variants in groups.items():
        if len(variants) < 2:
            continue
        variant_names = [asset["style_variant"] for asset in variants]
        normalized_variant_names = [
            normalize_search_term(str(value)) for value in variant_names
        ]
        if (
            any(not value for value in normalized_variant_names)
            or len(normalized_variant_names) != len(set(normalized_variant_names))
        ):
            fail(
                f"{concept_id}: style_variant values must be normalized-unique within a concept"
            )
        categories = {asset.get("category") for asset in variants}
        if len(categories) != 1:
            fail(f"{concept_id}: all style variants must share one category")
        region_sets = {
            tuple(sorted(region.get("id") for region in asset.get("editable_color_regions", []) if region.get("id")))
            for asset in variants
        }
        if len(region_sets) != 1:
            fail(f"{concept_id}: all style variants must share the same semantic color-region ids")
        if all(asset.get("scientific_name") for asset in variants):
            scientific_names = {
                normalize_search_term(str(asset["scientific_name"])) for asset in variants
            }
            if len(scientific_names) != 1:
                fail(f"{concept_id}: all style variants must share one scientific_name")
            subcategories = {
                normalize_search_term(str(asset.get("subcategory") or ""))
                for asset in variants
            }
            if len(subcategories) != 1:
                fail(f"{concept_id}: all style variants must share one subcategory")
            source_record_ids = {asset.get("source_record_id") for asset in variants}
            rights_record_ids = {asset.get("rights_record_id") for asset in variants}
            if len(source_record_ids) != 1 or len(rights_record_ids) != 1:
                fail(
                    f"{concept_id}: all style variants must share source and rights records"
                )


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_svg_bytes(value: bytes) -> str:
    """Hash SVG text independent of whether a checkout uses LF or CRLF."""

    return sha256_bytes(value.replace(b"\r\n", b"\n"))


def sha256_text(value: str) -> str:
    return sha256_bytes(value.encode("utf-8"))


def canonical_json_sha256(value: object) -> str:
    rendered = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return sha256_text(rendered)


def validate_iso_date(value: object, *, label: str) -> date:
    if not isinstance(value, str) or not ISO_DATE.fullmatch(value):
        fail(f"{label} must use YYYY-MM-DD")
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        fail(f"{label} is not a valid calendar date")
    if parsed > date.today():
        fail(f"{label} cannot be in the future")
    return parsed


def validate_draft_audit(pack: dict, pack_dir: Path, assets: list[dict]) -> str:
    """Validate local draft inclusion without inventing a public release decision."""
    reference = pack["release_audit"]
    missing = RELEASE_AUDIT_REFERENCE_FIELDS - reference.keys()
    if missing:
        fail(f"draft audit reference missing fields: {sorted(missing)}")
    audit_path = exact_pack_file(pack_dir, canonical_relative_file(
        reference["file"], label="draft audit file", suffix=".json"), label="draft audit file")
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    missing = RELEASE_AUDIT_REQUIRED_FIELDS - audit.keys()
    if missing:
        fail(f"draft audit missing fields: {sorted(missing)}")
    expected = {
        "schema_id": "figureStudio.scientificAssetLicenseReleaseAudit.v1",
        "pack_id": pack["id"], "status": "draft_review_pending",
        "asset_count": len(assets), "concept_count": pack["concept_count"],
        "rights_cleared_count": 0, "license_selection_pending_count": len(assets),
        "public_distribution_authorized": False, "selected_public_license": None,
        "release_effective_date": None, "third_party_component_count": 0,
    }
    for key, value in expected.items():
        if audit.get(key) != value:
            fail(f"draft audit {key} must be {value!r}")
    if audit["public_distribution_authorized"] is not False or reference.get("public_distribution_authorized") is not False:
        fail("draft public_distribution_authorized must be boolean false")
    for key in ("audit_id", "audit_date", "status", "asset_count", "concept_count",
                "public_distribution_authorized", "selected_public_license",
                "release_effective_date", "license_notice"):
        if reference.get(key) != audit.get(key):
            fail(f"draft audit {key} does not match pack reference")
    if not str(audit["audit_id"]).startswith(pack["id"] + "."):
        fail("draft audit identity must be scoped to its pack")
    validate_iso_date(audit["audit_date"], label="draft audit date")
    exact_pack_file(pack_dir, canonical_relative_file(
        audit["license_notice"], label="draft notice", suffix=".md"), label="draft notice")
    if audit.get("source_records") != pack["source_records"] or audit.get("rights_records") != pack["rights_records"]:
        fail("draft audit source and rights records must match the pack")
    basis = audit.get("rights_basis") or {}
    if (basis.get("status") != "original_output_pending_owner_review"
            or basis.get("pack_id") != pack["id"]
            or basis.get("authorization_record_id") != pack["rights_records"][0]["id"]):
        fail("draft audit rights basis must retain pending owner review")
    if not isinstance(audit.get("release_blocker"), str) or not audit["release_blocker"].strip():
        fail("draft audit must explain the pending public-release decision")
    candidates = audit.get("license_candidates")
    if not isinstance(candidates, list) or any(item.get("selected") for item in candidates):
        fail("draft audit cannot select a public license")
    rows = audit.get("assets")
    if not isinstance(rows, list) or len(rows) != len(assets):
        fail("draft audit must cover every asset exactly once")
    by_id = {row.get("asset_id"): row for row in rows if isinstance(row, dict)}
    if len(by_id) != len(rows) or set(by_id) != {asset["id"] for asset in assets}:
        fail("draft audit identities must match the pack exactly")
    for asset in assets:
        row = by_id[asset["id"]]
        if RELEASE_ASSET_REQUIRED_FIELDS - row.keys():
            fail(f"{asset['id']}: draft audit entry is incomplete")
        draft_lineages = {"original_vector_draft": "workspace_generated_original",
                          "clean_room_original_vector": "workspace_generated_clean_room_original"}
        if asset["source_type"] not in draft_lineages or row.get("lineage") != draft_lineages[asset["source_type"]]:
            fail(f"{asset['id']}: local draft inclusion supports declared original vectors only")
        expected_row = {
            "file": asset["file"], "source_type": asset["source_type"],
            "source_record_id": asset["source_record_id"], "rights_record_id": asset["rights_record_id"],
            "current_license": "FS-ORIGINAL-DRAFT", "third_party_material": "none_declared",
            "rights_basis": "original_output_pending_owner_review",
            "provenance_status": "original_draft_review_pending",
            "release_disposition": "draft_not_authorized_for_public_distribution",
            "sha256": sha256_bytes((pack_dir / asset["file"]).read_bytes()),
            "provenance_sha256": sha256_text(asset["provenance"]),
        }
        if asset["license"] != "FS-ORIGINAL-DRAFT":
            fail(f"{asset['id']}: draft asset cannot claim a released license")
        for key, value in expected_row.items():
            if row.get(key) != value:
                fail(f"{asset['id']}: draft audit {key} does not match current source / draft rights")
    return "draft_review_pending"


def validate_rights_cleared_quality_pending_audit(
    pack: dict, pack_dir: Path, assets: list[dict]
) -> str:
    """Validate an owner CC0 grant while keeping product-release approval pending."""
    reference = pack["release_audit"]
    audit_path = exact_pack_file(
        pack_dir,
        canonical_relative_file(
            reference["file"], label="rights-cleared audit file", suffix=".json"
        ),
        label="rights-cleared audit file",
    )
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    expected = {
        "schema_id": "figureStudio.scientificAssetLicenseReleaseAudit.v1",
        "pack_id": pack["id"],
        "status": "rights_cleared_quality_pending",
        "asset_count": len(assets),
        "concept_count": pack["concept_count"],
        "rights_cleared_count": len(assets),
        "license_selection_pending_count": 0,
        "public_distribution_authorized": True,
        "selected_public_license": "CC0-1.0",
        "release_effective_date": None,
        "product_release_status": "pending_quality_and_product_review",
        "third_party_component_count": 0,
    }
    for key, value in expected.items():
        if audit.get(key) != value:
            fail(f"rights-cleared audit {key} must be {value!r}")
    if (
        reference.get("status") != audit.get("status")
        or reference.get("public_distribution_authorized") is not True
        or reference.get("selected_public_license") != "CC0-1.0"
        or reference.get("product_release_status") != "pending_quality_and_product_review"
        or reference.get("rights_grant_effective_date")
        != audit.get("rights_grant_effective_date")
    ):
        fail("pack rights grant and product-release states must match the audit")
    validate_iso_date(
        audit.get("rights_grant_effective_date"), label="rights grant effective date"
    )
    audit_date = validate_iso_date(audit.get("audit_date"), label="rights-cleared audit date")
    if validate_iso_date(
        pack["source_records"][0].get("created_on"), label="source record created_on"
    ) > audit_date:
        fail("rights-cleared audit cannot predate its source record")
    exact_pack_file(
        pack_dir,
        canonical_relative_file(
            audit.get("license_notice"), label="CC0 license notice", suffix=".md"
        ),
        label="CC0 license notice",
    )
    if audit.get("source_records") != pack.get("source_records"):
        fail("rights-cleared audit source records must match the pack")
    if audit.get("rights_records") != pack.get("rights_records"):
        fail("rights-cleared audit rights records must match the pack")
    rights = pack.get("rights_records") or []
    basis = audit.get("rights_basis") or {}
    if (
        len(rights) != 1
        or basis.get("status") != "owner_attested_original_output"
        or basis.get("pack_id") != pack["id"]
        or basis.get("authorization_record_id") != rights[0].get("id")
        or basis.get("qualification") != rights[0].get("qualification")
    ):
        fail("rights-cleared audit must bind the owner grant to this pack")
    if not isinstance(audit.get("release_blocker"), str) or "Product-level release approval remains pending" not in audit["release_blocker"]:
        fail("rights-cleared audit must retain the separate product-release blocker")
    candidates = audit.get("license_candidates")
    if (
        not isinstance(candidates, list)
        or len(candidates) != 1
        or candidates[0].get("id") != "CC0-1.0"
        or candidates[0].get("selected") is not True
    ):
        fail("rights-cleared audit must identify the single selected CC0 grant")
    rows = audit.get("assets")
    if not isinstance(rows, list) or len(rows) != len(assets):
        fail("rights-cleared audit must cover every asset exactly once")
    by_id = {row.get("asset_id"): row for row in rows if isinstance(row, dict)}
    if len(by_id) != len(rows) or set(by_id) != {asset["id"] for asset in assets}:
        fail("rights-cleared audit identities must match the pack exactly")
    for asset in assets:
        row = by_id[asset["id"]]
        expected_row = {
            "file": asset["file"],
            "source_type": asset["source_type"],
            "source_record_id": asset["source_record_id"],
            "rights_record_id": asset["rights_record_id"],
            "current_license": "CC0-1.0",
            "third_party_material": "none_declared",
            "rights_basis": "owner_attested_original_output",
            "provenance_status": "owner_attested",
            "release_disposition": "licensed_under_cc0_1_0_product_release_pending",
            "sha256": sha256_bytes((pack_dir / asset["file"]).read_bytes()),
            "provenance_sha256": sha256_text(asset["provenance"]),
        }
        if asset["license"] != "CC0-1.0":
            fail(f"{asset['id']}: rights-cleared asset must use CC0-1.0")
        for key, value in expected_row.items():
            if row.get(key) != value:
                fail(f"{asset['id']}: rights-cleared audit {key} does not match the pack")
    return "rights_cleared_quality_pending"


def validate_release_audit(pack: dict, pack_dir: Path, assets: list[dict]) -> str:
    if pack.get("release_audit", {}).get("status") == "draft_review_pending":
        if pack.get("id") in {CORE_PACK_ID, EXPANSION_PACK_ID, IMMUNOLOGY_ONCOLOGY_PACK_ID}:
            fail("historical released packs cannot be downgraded to draft")
        return validate_draft_audit(pack, pack_dir, assets)
    if pack.get("release_audit", {}).get("status") == "rights_cleared_quality_pending":
        if pack.get("id") in {CORE_PACK_ID, EXPANSION_PACK_ID, IMMUNOLOGY_ONCOLOGY_PACK_ID}:
            fail("historical released packs cannot be downgraded to pending quality release")
        return validate_rights_cleared_quality_pending_audit(pack, pack_dir, assets)
    reference = pack.get("release_audit")
    if not isinstance(reference, dict):
        fail("release_audit must be an object")
    missing_reference = RELEASE_AUDIT_REFERENCE_FIELDS - reference.keys()
    if missing_reference:
        fail(f"release_audit reference missing fields: {sorted(missing_reference)}")

    relative_audit = canonical_relative_file(reference["file"], label="release_audit.file", suffix=".json")
    audit_path = exact_pack_file(pack_dir, relative_audit, label="release audit file")
    try:
        audit = json.loads(audit_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        fail(f"{audit_path}: invalid release-audit JSON: {error}")

    missing = RELEASE_AUDIT_REQUIRED_FIELDS - audit.keys()
    if missing:
        fail(f"release audit missing fields: {sorted(missing)}")
    if audit.get("schema_id") != "figureStudio.scientificAssetLicenseReleaseAudit.v1":
        fail("release audit has an unsupported schema_id")
    if pack.get("id") == CORE_PACK_ID and (
        audit.get("audit_id") != CORE_AUDIT_ID
        or audit.get("audit_date") != CORE_AUDIT_DATE
        or audit.get("release_effective_date") != CORE_AUDIT_DATE
        or audit.get("asset_count") != CORE_ASSET_COUNT
    ):
        fail("historical Core Biology release-audit identity and date are immutable")
    if audit.get("audit_id") != reference.get("audit_id"):
        fail("release audit audit_id does not match the pack reference")
    if not str(audit.get("audit_id") or "").startswith(f"{pack.get('id')}."):
        fail("release audit audit_id must be scoped to its own pack id")
    if audit.get("pack_id") != pack.get("id"):
        fail("release audit pack_id does not match the asset pack")
    if audit.get("status") != reference.get("status"):
        fail("release audit status does not match the pack reference")
    if audit.get("asset_count") != reference.get("asset_count") or audit.get("asset_count") != len(assets):
        fail("release audit asset_count does not match the pack")
    if audit.get("public_distribution_authorized") is not reference.get("public_distribution_authorized"):
        fail("release audit public-distribution state does not match the pack reference")
    if audit.get("status") != "released":
        fail("release audit must record released after the explicit owner CC0 decision")
    audit_date = validate_iso_date(audit.get("audit_date"), label="release audit audit_date")
    effective_date = validate_iso_date(
        audit.get("release_effective_date"), label="release audit release_effective_date"
    )
    if effective_date > audit_date:
        fail("release audit release_effective_date cannot be later than audit_date")
    if reference.get("audit_date") is not None and reference.get("audit_date") != audit.get("audit_date"):
        fail("release audit audit_date does not match the pack reference")
    if (
        reference.get("release_effective_date") is not None
        and reference.get("release_effective_date") != audit.get("release_effective_date")
    ):
        fail("release audit release_effective_date does not match the pack reference")
    if audit.get("public_distribution_authorized") is not True or audit.get("selected_public_license") != "CC0-1.0":
        fail("released audit must authorize distribution under CC0-1.0")
    if reference.get("selected_public_license") != "CC0-1.0":
        fail("pack release_audit reference must select CC0-1.0")
    if audit.get("license_notice") != reference.get("license_notice"):
        fail("release audit license notice does not match the pack reference")
    relative_license = canonical_relative_file(audit.get("license_notice"), label="release audit license_notice", suffix=".md")
    exact_pack_file(pack_dir, relative_license, label="release audit CC0 license notice")
    if audit.get("rights_cleared_count") != len(assets):
        fail("release audit rights_cleared_count must cover every asset")
    if audit.get("license_selection_pending_count") != 0:
        fail("released audit cannot retain pending license selections")
    if audit.get("third_party_component_count") != 0:
        fail("release audit currently expects zero declared third-party components")
    rights_basis = audit.get("rights_basis")
    if not isinstance(rights_basis, dict) or rights_basis.get("status") != "owner_attested_original_output":
        fail("release audit rights_basis must record owner_attested_original_output")
    is_modern_pack = pack.get("id") != CORE_PACK_ID
    if is_modern_pack:
        concept_count = len(
            {str(asset.get("concept_id") or asset.get("id")) for asset in assets}
        )
        if audit.get("concept_count") != concept_count:
            fail("modern-pack release audit concept_count does not match the pack")
        if (
            reference.get("concept_count") is not None
            and reference.get("concept_count") != concept_count
        ):
            fail("modern-pack release-audit reference concept_count does not match the pack")
        if rights_basis.get("pack_id") != pack.get("id"):
            fail("modern-pack release audit rights_basis must be scoped to its own pack")
        pack_rights_records = pack.get("rights_records") or []
        if (
            len(pack_rights_records) != 1
            or rights_basis.get("authorization_record_id")
            != pack_rights_records[0].get("id")
            or rights_basis.get("qualification")
            != pack_rights_records[0].get("qualification")
        ):
            fail(
                "modern-pack release audit rights_basis must reference its pack-scoped authorization"
            )

    source_records = audit.get("source_records")
    if not isinstance(source_records, list) or not source_records:
        fail("release audit source_records must be a non-empty list")
    source_record_ids = {record.get("id") for record in source_records if isinstance(record, dict)}
    if pack.get("id") == CORE_PACK_ID:
        required_source_records = {
            "owner-attestation-2026-07-19",
            "owner-cc0-selection-2026-07-19",
            "model-organism-promotion-review-2026-07-20",
            "openai-terms-output-ownership-2026-01-01",
            "openai-services-agreement-output-ownership-2026-01-01",
        }
        if not required_source_records.issubset(source_record_ids):
            fail("Core Biology release audit is missing its historical owner-attestation or OpenAI ownership records")
    elif str(audit.get("audit_id") or "").startswith("core-biology."):
        fail("a non-Core Biology pack must use its own release-audit identity")
    if re.search(r"[A-Za-z]:\\", json.dumps(source_records)):
        fail("release audit source records must not expose absolute local Windows paths")
    if is_modern_pack:
        pack_source_record_ids = validate_record_table(
            pack, "source_records", required=True
        )
        if source_record_ids != pack_source_record_ids:
            fail("modern-pack release-audit source_records do not match pack source_records")
        audit_source_by_id = {
            record["id"]: record for record in source_records if isinstance(record, dict)
        }
        pack_source_by_id = {
            record["id"]: record
            for record in pack.get("source_records", [])
            if isinstance(record, dict)
        }
        if audit_source_by_id != pack_source_by_id:
            fail(
                "modern-pack release-audit source record content does not match pack source_records"
            )
        audit_rights_record_ids = validate_record_table(
            audit, "rights_records", required=True
        )
        pack_rights_record_ids = validate_record_table(
            pack, "rights_records", required=True
        )
        if audit_rights_record_ids != pack_rights_record_ids:
            fail("modern-pack release-audit rights_records do not match pack rights_records")
        audit_rights_by_id = {
            record["id"]: record
            for record in audit.get("rights_records", [])
            if isinstance(record, dict)
        }
        pack_rights_by_id = {
            record["id"]: record
            for record in pack.get("rights_records", [])
            if isinstance(record, dict)
        }
        if audit_rights_by_id != pack_rights_by_id:
            fail(
                "modern-pack release-audit rights record content does not match pack rights_records"
            )

    candidates = audit.get("license_candidates")
    if not isinstance(candidates, list) or not candidates or not all(isinstance(item, dict) for item in candidates):
        fail("release audit license_candidates must be a non-empty list of objects")
    candidate_ids = {candidate.get("id") for candidate in candidates}
    if len(candidate_ids) != len(candidates) or None in candidate_ids:
        fail("release audit license_candidates must use unique non-empty ids")
    if pack.get("id") == CORE_PACK_ID and candidate_ids != {
        "CC0-1.0",
        "CC-BY-4.0",
        "BSD-STUDIO-ASSET-USE-1.0-PROPOSED",
    }:
        fail("Core Biology release audit must retain its reviewed license-candidate set")
    if pack.get("id") == CORE_PACK_ID and not all(
        candidate.get("owner_action_required") is True for candidate in candidates
    ):
        fail("Core Biology license candidates must retain explicit owner-action records")
    selected_candidates = [candidate.get("id") for candidate in candidates if candidate.get("selected") is True]
    if selected_candidates != [audit.get("selected_public_license")]:
        fail("release audit must mark only selected_public_license as selected")
    blocker = audit.get("release_blocker")
    if blocker is not None:
        fail("released audit cannot retain a release blocker")

    audit_assets = audit.get("assets")
    if not isinstance(audit_assets, list):
        fail("release audit assets must be a list")
    audit_by_id: dict[str, dict] = {}
    audit_files: dict[str, str] = {}
    for entry in audit_assets:
        if not isinstance(entry, dict):
            fail("release audit asset entries must be objects")
        missing_entry = RELEASE_ASSET_REQUIRED_FIELDS - entry.keys()
        if is_modern_pack:
            missing_entry |= {"source_record_id", "rights_record_id"} - entry.keys()
        if missing_entry:
            fail(f"release audit asset entry missing fields: {sorted(missing_entry)}")
        asset_id = entry.get("asset_id")
        if asset_id in audit_by_id:
            fail(f"release audit contains duplicate asset_id {asset_id!r}")
        audit_file = canonical_relative_file(entry.get("file"), label=f"{asset_id}: release audit file", suffix=".svg").as_posix()
        prior_file = audit_files.get(audit_file.casefold())
        if prior_file is not None:
            fail(f"release audit contains duplicate or case-equivalent SVG paths for {prior_file} and {asset_id}")
        audit_files[audit_file.casefold()] = str(asset_id)
        audit_by_id[asset_id] = entry

    pack_by_id = {asset["id"]: asset for asset in assets}
    if set(audit_by_id) != set(pack_by_id):
        fail("release audit asset ids do not exactly match the pack")

    identity_mismatches: list[str] = []
    for asset_id, asset in pack_by_id.items():
        entry = audit_by_id[asset_id]
        svg_path = exact_pack_file(
            pack_dir,
            canonical_relative_file(asset["file"], label=f"{asset_id}: file", suffix=".svg"),
            label=f"{asset_id}: SVG file",
        )
        actual_svg_sha256 = sha256_svg_bytes(svg_path.read_bytes())
        expected_svg_sha256 = entry.get("sha256")
        if expected_svg_sha256 != actual_svg_sha256:
            identity_mismatches.append(
                f"{asset_id}: SVG expected {expected_svg_sha256}, actual {actual_svg_sha256}"
            )
        actual_provenance_sha256 = sha256_text(asset["provenance"])
        expected_provenance_sha256 = entry.get("provenance_sha256")
        if expected_provenance_sha256 != actual_provenance_sha256:
            identity_mismatches.append(
                f"{asset_id}: provenance expected {expected_provenance_sha256}, actual {actual_provenance_sha256}"
            )
    if identity_mismatches:
        fail(
            f"release audit exact-identity mismatch set ({len(identity_mismatches)}):\n  "
            + "\n  ".join(identity_mismatches)
        )

    for asset_id, asset in pack_by_id.items():
        entry = audit_by_id[asset_id]
        if entry.get("file") != asset["file"]:
            fail(f"{asset_id}: release audit file does not match asset metadata")
        if entry.get("source_type") != asset["source_type"]:
            fail(f"{asset_id}: release audit source_type does not match asset metadata")
        if entry.get("current_license") != asset["license"]:
            fail(f"{asset_id}: release audit current_license does not match asset metadata")
        if is_modern_pack:
            if entry.get("source_record_id") != asset.get("source_record_id"):
                fail(f"{asset_id}: release audit source_record_id does not match asset metadata")
            if entry.get("rights_record_id") != asset.get("rights_record_id"):
                fail(f"{asset_id}: release audit rights_record_id does not match asset metadata")
        if entry.get("lineage") == "unclassified":
            fail(f"{asset_id}: release audit lineage is unclassified")
        expected_asset_rights_basis = (
            "owner_attested_openai_output"
            if pack.get("id") == CORE_PACK_ID
            else "owner_attested_original_output"
        )
        if entry.get("rights_basis") != expected_asset_rights_basis:
            fail(
                f"{asset_id}: release audit rights_basis must be "
                f"{expected_asset_rights_basis}"
            )
        if entry.get("third_party_material") != "none_declared":
            fail(f"{asset_id}: release audit declares third-party material and requires separate disposition")
        if entry.get("provenance_status") != "owner_attested":
            fail(f"{asset_id}: release audit provenance_status must be owner_attested")
        if entry.get("current_license") != "CC0-1.0":
            fail(f"{asset_id}: released asset must use CC0-1.0")
        if entry.get("release_disposition") != "released_under_cc0_1_0":
            fail(f"{asset_id}: release audit disposition is not released_under_cc0_1_0")

    if pack.get("id") == CORE_PACK_ID:
        actual_audit_hash = canonical_json_sha256(audit)
        if actual_audit_hash != CORE_AUDIT_SHA256:
            fail(
                "historical Core Biology release-audit identity is immutable; "
                f"expected {CORE_AUDIT_SHA256}, found {actual_audit_hash}"
            )

    return str(audit["status"])


def validate_pack(pack_path: Path) -> tuple[str, int, str]:
    if pack_path.is_symlink():
        fail(f"{pack_path}: asset-pack.json must not be a symlink")
    if not pack_path.is_file():
        fail(f"{pack_path}: asset-pack.json is missing or not a regular file")
    pack = load_pack(pack_path)
    if not isinstance(pack, dict):
        fail(f"{pack_path}: asset-pack.json must contain a JSON object")
    missing = PACK_REQUIRED_FIELDS - pack.keys()
    if missing:
        fail(f"{pack_path}: pack missing fields: {sorted(missing)}")

    pack_id = require_non_empty_string(pack.get("id"), label=f"{pack_path}: id")
    if not RECORD_ID.fullmatch(pack_id):
        fail(f"{pack_path}: id must use lowercase stable-id characters")
    if pack_id == IMMUNOLOGY_ONCOLOGY_PACK_ID and pack.get("version") != "1.0.0":
        fail(f"{pack_path}: Immunology & Oncology version must remain 1.0.0")

    assets = pack["assets"]
    if not isinstance(assets, list) or not assets:
        fail(f"{pack_path}: assets must be a non-empty list")
    for index, asset in enumerate(assets):
        if not isinstance(asset, dict):
            fail(f"{pack_path}: assets[{index}] must be an object")
    if pack_id == CORE_PACK_ID:
        if pack.get("schema_version") != "0.2.0":
            fail(f"{pack_path}: historical Core Biology schema_version must remain 0.2.0")
        if len(assets) != CORE_ASSET_COUNT:
            fail(
                f"{pack_path}: historical Core Biology catalog must remain exactly {CORE_ASSET_COUNT} assets"
            )
        core_release_reference = pack.get("release_audit") or {}
        if (
            core_release_reference.get("file") != "license-release-audit.json"
            or core_release_reference.get("audit_id") != CORE_AUDIT_ID
            or core_release_reference.get("asset_count") != CORE_ASSET_COUNT
        ):
            fail(f"{pack_path}: historical Core Biology release reference is immutable")
    if not isinstance(pack["style_tokens"], dict):
        fail(f"{pack_path}: style_tokens must be an object")
    style_families = pack.get("style_families") or [pack["style_family"]]
    if not isinstance(style_families, list) or not style_families or not all(isinstance(value, str) and value.strip() for value in style_families):
        fail(f"{pack_path}: style_families must be a non-empty list of strings when provided")
    if pack["style_family"] not in style_families:
        fail(f"{pack_path}: primary style_family must also appear in style_families")
    license_definitions = pack["license_definitions"]
    if not isinstance(license_definitions, dict) or not license_definitions:
        fail(f"{pack_path}: license_definitions must be a non-empty object")

    is_modern_pack = pack_id != CORE_PACK_ID
    is_core_experimental = pack_id == EXPANSION_PACK_ID
    source_record_ids = validate_record_table(
        pack, "source_records", required=is_modern_pack
    )
    rights_record_ids = validate_record_table(
        pack, "rights_records", required=is_modern_pack
    )
    if is_modern_pack:
        if pack.get("schema_version") != "0.3.0":
            fail(f"{pack_path}: modern scientific pack schema_version must be 0.3.0")
        if pack["style_tokens"].get("viewBox") != "0 0 128 128":
            fail(
                f"{pack_path}: modern scientific pack style_tokens.viewBox must be '0 0 128 128'"
            )
        modern_release_reference = pack.get("release_audit")
        if not isinstance(modern_release_reference, dict):
            fail(f"{pack_path}: modern-pack release_audit must be an object")
        missing_release_fields = {
            "audit_date",
            "release_effective_date",
            "concept_count",
        } - modern_release_reference.keys()
        if missing_release_fields:
            fail(
                f"{pack_path}: modern-pack release_audit missing fields: {sorted(missing_release_fields)}"
            )
        if modern_release_reference.get("file") != "rights-release-record.json":
            fail(
                f"{pack_path}: modern-pack release_audit must use its own rights-release-record.json"
            )
        validate_modern_release_records(pack)
        derived_concept_count = len(
            {
                str(asset.get("concept_id") or asset.get("id"))
                for asset in assets
                if isinstance(asset, dict)
            }
        )
        if pack.get("asset_count") != len(assets):
            fail(f"{pack_path}: modern-pack asset_count must match its SVG style rows")
        if pack.get("concept_count") != derived_concept_count:
            fail(f"{pack_path}: modern-pack concept_count must match its stable concepts")

    if is_core_experimental:
        if pack.get("asset_count") != EXPANSION_ASSET_COUNT:
            fail(
                f"{pack_path}: expansion asset_count must remain {EXPANSION_ASSET_COUNT}"
            )
        if pack.get("concept_count") != EXPANSION_CONCEPT_COUNT:
            fail(
                f"{pack_path}: expansion concept_count must remain {EXPANSION_CONCEPT_COUNT}"
            )
        if len(assets) != EXPANSION_ASSET_COUNT:
            fail(
                f"{pack_path}: expansion catalog must contain exactly {EXPANSION_ASSET_COUNT} SVG styles"
            )

    pack_dir = pack_path.parent.resolve()
    expected_viewbox = pack["style_tokens"].get("viewBox")
    seen_ids: set[str] = set()
    seen_files: dict[str, str] = {}
    errors: list[str] = []

    for asset in assets:
        try:
            validate_asset(
                asset,
                pack,
                pack_dir,
                license_definitions,
                expected_viewbox,
                seen_ids,
                seen_files,
                require_modern_metadata=is_modern_pack,
                source_record_ids=source_record_ids,
                rights_record_ids=rights_record_ids,
            )
        except ValueError as error:
            errors.append(str(error))

    try:
        validate_concept_variants(assets)
    except ValueError as error:
        errors.append(str(error))

    if is_modern_pack:
        try:
            concept_ids = {
                asset.get("concept_id")
                for asset in assets
                if isinstance(asset, dict) and isinstance(asset.get("concept_id"), str)
            }
            if len(concept_ids) != pack.get("concept_count"):
                fail("modern catalog stable concept count must match concept_count")
            derived_category_styles: dict[str, int] = {}
            derived_category_concepts: dict[str, set[str]] = {}
            for asset in assets:
                category = asset.get("category") if isinstance(asset, dict) else None
                if isinstance(category, str):
                    derived_category_styles[category] = (
                        derived_category_styles.get(category, 0) + 1
                    )
                    derived_category_concepts.setdefault(category, set()).add(
                        str(asset.get("concept_id") or asset.get("id"))
                    )
            if is_core_experimental and derived_category_styles.get("assay-workflow", 0) < 1:
                fail("expansion catalog must include the assay-workflow category")
            expected_category_counts = {
                category: {
                    "concept_count": len(derived_category_concepts[category]),
                    "style_count": style_count,
                }
                for category, style_count in derived_category_styles.items()
            }
            if pack.get("category_counts") != expected_category_counts:
                fail(
                    "modern-pack category_counts must exactly match catalog concept and style counts"
                )
            referenced_sources = {
                asset.get("source_record_id") for asset in assets if isinstance(asset, dict)
            }
            referenced_rights = {
                asset.get("rights_record_id") for asset in assets if isinstance(asset, dict)
            }
            if referenced_sources != source_record_ids:
                fail("modern-pack source_records must exactly match asset source_record_id references")
            if referenced_rights != rights_record_ids:
                fail("modern-pack rights_records must exactly match asset rights_record_id references")
        except (KeyError, TypeError, ValueError) as error:
            errors.append(str(error))

    try:
        for path in pack_dir.rglob("*"):
            if path.is_symlink():
                fail(f"scientific asset pack contains a symlink: {path.relative_to(pack_dir).as_posix()}")
        release_reference = pack.get("release_audit") if isinstance(pack.get("release_audit"), dict) else {}
        audit_file = canonical_relative_file(release_reference.get("file"), label="release_audit.file", suffix=".json").as_posix()
        license_notice = canonical_relative_file(
            release_reference.get("license_notice"), label="release_audit.license_notice", suffix=".md"
        ).as_posix()
        declared_files = {"asset-pack.json", audit_file, license_notice, *(asset["file"] for asset in assets if isinstance(asset, dict) and isinstance(asset.get("file"), str))}
        if len(declared_files) != len(assets) + 3:
            fail("scientific asset pack declared-file inventory contains duplicate paths")
        casefolded = [path.casefold() for path in declared_files]
        if len(casefolded) != len(set(casefolded)):
            fail("scientific asset pack declared-file inventory contains case-equivalent duplicate paths")
        actual_files = {path.relative_to(pack_dir).as_posix() for path in pack_dir.rglob("*") if path.is_file()}
        missing = sorted(declared_files - actual_files)
        extra = sorted(actual_files - declared_files)
        if missing or extra:
            details = []
            if missing:
                details.append(f"missing={missing}")
            if extra:
                details.append(f"extra={extra}")
            fail("scientific asset pack inventory does not exactly match its receipts: " + "; ".join(details))
    except (KeyError, TypeError, ValueError) as error:
        errors.append(str(error))

    release_status = "unvalidated"
    try:
        release_status = validate_release_audit(pack, pack_dir, assets)
    except ValueError as error:
        errors.append(str(error))

    if errors:
        fail(f"{pack_path}: {len(errors)} asset validation error(s):\n- " + "\n- ".join(errors))

    if pack_id == CORE_PACK_ID:
        actual_catalog_hash = canonical_json_sha256(pack)
        if actual_catalog_hash != CORE_CATALOG_SHA256:
            fail(
                f"{pack_path}: historical Core Biology catalog identity is immutable; "
                f"expected {CORE_CATALOG_SHA256}, found {actual_catalog_hash}"
            )

    return pack_id, len(assets), release_status


@dataclass
class LibraryIdentityState:
    asset_ids: dict[str, str] = field(default_factory=dict)
    concept_ids: dict[str, str] = field(default_factory=dict)
    svg_hashes: dict[str, tuple[str, str]] = field(default_factory=dict)
    scientific_names: dict[str, tuple[str, str]] = field(default_factory=dict)
    scoped_search_terms: dict[
        tuple[str, str, str], tuple[str, str, bool]
    ] = field(default_factory=dict)


def _concept_identity(pack_id: str, asset: dict) -> str:
    concept_id = asset.get("concept_id")
    if isinstance(concept_id, str) and concept_id:
        return f"{pack_id}:{concept_id}"
    return f"{pack_id}:{asset.get('id')}"


def _register_library_asset(
    state: LibraryIdentityState,
    *,
    pack_id: str,
    pack_dir: Path,
    asset: dict,
) -> None:
    asset_id = str(asset["id"])
    prior_pack = state.asset_ids.get(asset_id)
    if prior_pack is not None:
        fail(
            f"library asset id {asset_id!r} is duplicated across packs {prior_pack!r} and {pack_id!r}"
        )
    state.asset_ids[asset_id] = pack_id

    raw_concept_id = str(asset.get("concept_id") or asset_id)
    concept_owner = state.concept_ids.get(raw_concept_id)
    if concept_owner is not None and concept_owner != pack_id:
        fail(
            f"library concept_id {raw_concept_id!r} is duplicated across packs "
            f"{concept_owner!r} and {pack_id!r}"
        )
    state.concept_ids[raw_concept_id] = pack_id

    relative_svg = canonical_relative_file(
        asset["file"], label=f"{asset_id}: file", suffix=".svg"
    )
    svg_path = exact_pack_file(pack_dir, relative_svg, label=f"{asset_id}: SVG file")
    svg_hash = sha256_svg_bytes(svg_path.read_bytes())
    prior_svg = state.svg_hashes.get(svg_hash)
    if prior_svg is not None:
        fail(
            f"exact duplicate SVG content for {asset_id!r} in {pack_id!r}; "
            f"already used by {prior_svg[1]!r} in {prior_svg[0]!r}"
        )
    state.svg_hashes[svg_hash] = (pack_id, asset_id)

    concept = _concept_identity(pack_id, asset)
    scientific_name = str(asset.get("scientific_name") or asset.get("name") or "")
    normalized_name = normalize_search_term(scientific_name)
    prior_name = state.scientific_names.get(normalized_name)
    if prior_name is not None and prior_name[0] != concept:
        fail(
            f"normalized scientific name {scientific_name!r} for {asset_id!r} duplicates "
            f"the distinct concept {prior_name[1]!r}"
        )
    state.scientific_names[normalized_name] = (concept, asset_id)

    category = normalize_search_term(str(asset.get("category") or ""))
    subcategory = normalize_search_term(str(asset.get("subcategory") or ""))
    terms = [(scientific_name, True)] + [
        (str(value), False) for value in asset.get("synonyms", []) if isinstance(value, str)
    ]
    for raw_term, is_primary in terms:
        normalized = normalize_search_term(raw_term)
        scope = (category, subcategory, normalized)
        prior = state.scoped_search_terms.get(scope)
        if prior is not None and prior[0] != concept and (prior[2] or is_primary):
            fail(
                f"ambiguous normalized scientific search term {raw_term!r} in "
                f"{category or '<uncategorized>'}/{subcategory or '<general>'}: "
                f"{asset_id!r} conflicts with {prior[1]!r}"
            )
        if prior is None or is_primary:
            state.scoped_search_terms[scope] = (concept, asset_id, is_primary)


def validate_library(library_path: Path = DEFAULT_LIBRARY) -> dict[str, object]:
    """Validate the installed scientific-library registry and every pack it declares."""

    if library_path.is_symlink():
        fail(f"{library_path}: library registry must not be a symlink")
    if not library_path.is_file():
        fail(f"{library_path}: library registry is missing or not a regular file")
    if library_path.name != "library.json":
        fail(f"{library_path}: scientific-library registry must be named library.json")
    try:
        library = json.loads(library_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        fail(f"{library_path}: invalid JSON: {error}")
    if not isinstance(library, dict):
        fail(f"{library_path}: library registry must be an object")
    missing = LIBRARY_REQUIRED_FIELDS - library.keys()
    if missing:
        fail(f"{library_path}: library registry missing fields: {sorted(missing)}")
    if library.get("schema_version") != "1.0.0":
        fail(f"{library_path}: unsupported library schema_version")
    if library.get("id") != "figure-studio-scientific-library":
        fail(f"{library_path}: unsupported library id")
    rows = library.get("packs")
    if not isinstance(rows, list) or not rows:
        fail(f"{library_path}: packs must be a non-empty list")

    packs_root = library_path.parent.resolve()
    seen_pack_ids: set[str] = set()
    seen_paths: set[str] = set()
    state = LibraryIdentityState()
    pack_summaries: list[dict[str, object]] = []
    total_assets = 0
    total_concepts = 0

    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            fail(f"{library_path}: packs[{index}] must be an object")
        missing_row = LIBRARY_PACK_REQUIRED_FIELDS - row.keys()
        if missing_row:
            fail(
                f"{library_path}: packs[{index}] missing fields: {sorted(missing_row)}"
            )
        pack_id = require_non_empty_string(
            row.get("id"), label=f"{library_path}: packs[{index}].id"
        )
        if not RECORD_ID.fullmatch(pack_id):
            fail(f"{library_path}: packs[{index}].id must be a stable lowercase id")
        if pack_id in seen_pack_ids:
            fail(f"{library_path}: duplicate pack id {pack_id!r}")
        seen_pack_ids.add(pack_id)
        require_non_empty_string(
            row.get("name"), label=f"{library_path}: packs[{index}].name"
        )
        require_non_empty_string(
            row.get("description"), label=f"{library_path}: packs[{index}].description"
        )
        if row.get("enabled") is not True:
            fail(f"{library_path}: bundled pack {pack_id!r} must be enabled")
        if (
            pack_id == IMMUNOLOGY_ONCOLOGY_PACK_ID
            and row.get("version") != "1.0.0"
        ):
            fail(
                f"{library_path}: bundled Immunology & Oncology registry version must remain 1.0.0"
            )
        modes = row.get("modes")
        if not isinstance(modes, list) or set(modes) != {"figure", "presentation"} or len(modes) != 2:
            fail(
                f"{library_path}: bundled pack {pack_id!r} must declare figure and presentation modes exactly once"
            )

        relative_catalog = canonical_relative_file(
            row.get("path"), label=f"{library_path}: {pack_id} path", suffix=".json"
        )
        catalog_path_value = relative_catalog.as_posix()
        if catalog_path_value.casefold() in seen_paths:
            fail(f"{library_path}: duplicate or case-equivalent pack path {catalog_path_value!r}")
        seen_paths.add(catalog_path_value.casefold())
        pack_path = exact_pack_file(
            packs_root, relative_catalog, label=f"{library_path}: {pack_id} catalog"
        )
        if pack_path.name != "asset-pack.json" or pack_path.parent.name != pack_id:
            fail(
                f"{library_path}: pack {pack_id!r} path must be {pack_id}/asset-pack.json"
            )
        validated_id, asset_count, release_status = validate_pack(pack_path)
        if validated_id != pack_id:
            fail(
                f"{library_path}: registry id {pack_id!r} does not match catalog id {validated_id!r}"
            )
        pack = load_pack(pack_path)
        concept_count = len(
            {
                str(asset.get("concept_id") or asset.get("id"))
                for asset in pack["assets"]
                if isinstance(asset, dict)
            }
        )
        if row.get("asset_count") != asset_count:
            fail(f"{library_path}: {pack_id} asset_count does not match its catalog")
        if row.get("concept_count") != concept_count:
            fail(f"{library_path}: {pack_id} concept_count does not match its catalog")
        for asset in pack["assets"]:
            _register_library_asset(
                state,
                pack_id=pack_id,
                pack_dir=pack_path.parent.resolve(),
                asset=asset,
            )
        total_assets += asset_count
        total_concepts += concept_count
        pack_summaries.append(
            {
                "pack_id": pack_id,
                "asset_count": asset_count,
                "concept_count": concept_count,
                "release_status": release_status,
            }
        )

    required_packs = {
        CORE_PACK_ID,
        EXPANSION_PACK_ID,
        IMMUNOLOGY_ONCOLOGY_PACK_ID,
    }
    if not required_packs.issubset(seen_pack_ids):
        fail(
            f"{library_path}: bundled library is missing required packs {sorted(required_packs - seen_pack_ids)}"
        )
    catalog_paths = {
        path.relative_to(packs_root).as_posix().casefold()
        for path in packs_root.glob("*/asset-pack.json")
        if path.is_file()
    }
    if catalog_paths != seen_paths:
        missing_registry = sorted(catalog_paths - seen_paths)
        missing_catalog = sorted(seen_paths - catalog_paths)
        fail(
            "library registry and on-disk pack catalogs disagree: "
            f"unregistered={missing_registry}; missing={missing_catalog}"
        )
    top_level_files: set[str] = set()
    top_level_directories: set[str] = set()
    for child in packs_root.iterdir():
        if child.is_symlink() or getattr(child, "is_junction", lambda: False)():
            fail(f"library root contains a link or junction: {child.name}")
        if child.is_file():
            top_level_files.add(child.name)
        elif child.is_dir():
            top_level_directories.add(child.name)
        else:
            fail(f"library root contains an unsupported entry: {child.name}")
    if top_level_files != {"library.json"}:
        fail(
            "library root contains loose or missing files; "
            f"expected ['library.json'], found {sorted(top_level_files)}"
        )
    if top_level_directories != seen_pack_ids:
        fail(
            "library root directories must exactly match registered pack ids; "
            f"expected {sorted(seen_pack_ids)}, found {sorted(top_level_directories)}"
        )

    return {
        "library_id": library["id"],
        "pack_count": len(pack_summaries),
        "asset_count": total_assets,
        "concept_count": total_concepts,
        "packs": pack_summaries,
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate Figure Tool scientific asset pack metadata and SVG files.")
    parser.add_argument("pack_path", nargs="?", help="Optional asset-pack.json path. Defaults to the production core-biology pack.")
    parser.add_argument("--pack", dest="pack_option", help="Asset-pack.json path to validate.")
    parser.add_argument(
        "--library",
        nargs="?",
        const=str(DEFAULT_LIBRARY),
        help="Validate the whole installed library; optionally provide a library.json path.",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Alias for --library using the production library.json registry.",
    )
    parser.add_argument("--expect-fail", action="store_true", help="Exit successfully only when validation fails. Intended for negative test fixtures.")
    parser.add_argument("--require-public-release", action="store_true",
                        help="Reject locally valid drafts when qualifying assets for public distribution.")
    return parser.parse_args(argv)


def main() -> int:
    args = parse_args(sys.argv[1:])
    if args.pack_path and args.pack_option:
        print("Use either positional pack_path or --pack, not both.", file=sys.stderr)
        return 2
    if (args.library or args.all) and (args.pack_path or args.pack_option):
        print("Use pack validation or whole-library validation, not both.", file=sys.stderr)
        return 2

    try:
        if args.library or args.all:
            library_path = Path(args.library).resolve() if args.library else DEFAULT_LIBRARY
            summary = validate_library(library_path)
            if args.require_public_release:
                pending = [str(pack["pack_id"]) for pack in summary["packs"] if pack["release_status"] != "released"]
                if pending:
                    fail("Public release is pending for scientific packs: " + ", ".join(pending))
            success_message = (
                f"Validated {summary['asset_count']} SVG styles across "
                f"{summary['concept_count']} concepts in {summary['pack_count']} packs."
            )
        else:
            pack_arg = args.pack_option or args.pack_path
            pack_path = Path(pack_arg).resolve() if pack_arg else DEFAULT_PACK
            pack_id, asset_count, release_status = validate_pack(pack_path)
            if args.require_public_release and release_status != "released":
                fail("Public release is pending for scientific pack: " + pack_id)
            success_message = (
                f"Validated {asset_count} assets in pack {pack_id!r}; "
                f"release audit status={release_status}."
            )
    except ValueError as error:
        if args.expect_fail:
            print(f"Asset validation failed as expected: {error}")
            return 0
        print(f"Asset validation failed: {error}", file=sys.stderr)
        return 1

    if args.expect_fail:
        print(f"Expected validation to fail, but validation succeeded: {success_message}", file=sys.stderr)
        return 1

    print(success_message)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
