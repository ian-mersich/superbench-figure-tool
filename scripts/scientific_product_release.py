"""Finite product decisions preserve historical grants and bind exact reviewed art.

The successor adds 80 original drawings without extending old owner grants or
approving later artwork. Scientific schemas, geometry, provenance and native
editing remain separately validated.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath

RECORD = "config/scientific-product-release-2026-10-15.json"
RECORD_SHA256 = "947cf4bcf7f5c3b9826e1c1a58dee27becf2954e024640e252065ce2318b29e0"
PACK_IDS = frozenset({"rna-methods", "cell-architecture-transport", "culture-models-assays", "microbial-biology"})
SCENE_IDS = frozenset({"single-cell-rna-workflow", "spatial-rna-methods"})


def canonical(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()


def file_identity(path: Path) -> str:
    data = path.read_bytes()
    return canonical(json.loads(data)) if path.suffix == ".json" else hashlib.sha256(data.replace(b"\r\n", b"\n")).hexdigest()


def asset_inventory(root: Path) -> list[dict[str, str]]:
    result = []
    for relative in ("assets/scientific-packs", "assets/scientific-scenes"):
        for path in sorted((root / relative).rglob("*")):
            if path.is_symlink() or getattr(path, "is_junction", lambda: False)():
                raise ValueError("Scientific product release: asset links are forbidden")
            if path.is_file():
                result.append({"path": path.relative_to(root).as_posix(), "sha256": file_identity(path)})
            elif not path.is_dir():
                raise ValueError("Scientific product release: unsupported asset entry")
    return sorted(result, key=lambda row: row["path"])


def _validate_baseline(root: Path, *, required: bool = False, inventory_override: list | None = None) -> dict | None:
    root = Path(root)
    path = root / RECORD
    if not path.exists():
        if required:
            raise ValueError("Scientific product release: reviewed product decision is missing")
        return None
    if path.is_symlink() or not path.is_file():
        raise ValueError("Scientific product release: record must be an ordinary file")
    record = json.loads(path.read_text(encoding="utf-8"))
    def need(condition: bool, message: str) -> None:
        if not condition:
            raise ValueError("Scientific product release: " + message)
    need(canonical(record) == RECORD_SHA256, "reviewed decision exact identity mismatch")
    need(record.get("schema") == "figureStudio.scientificProductRelease.v1"
         and record.get("release_id") == "reviewed-library-and-rna-scenes.2026-10-15"
         and record.get("release_date") == "2026-10-15", "decision schema/date mismatch")
    need(record.get("decision") == "approved_for_matching_public_web_and_superbench_packages", "product approval is absent")
    need(record.get("library") == {"drawing_count": 406, "concept_count": 346, "pack_count": 8, "scene_count": 12}, "finite collection count mismatch")
    inventory = asset_inventory(root) if inventory_override is None else inventory_override
    need(record.get("asset_inventory_sha256") == canonical(inventory)
         and record.get("asset_file_count") == len(inventory), "exact reviewed asset inventory mismatch")
    need(set(record.get("packs", {})) == PACK_IDS and set(record.get("scenes", {})) == SCENE_IDS, "finite approval cohort mismatch")
    for pack_id, binding in record["packs"].items():
        base = root / "assets/scientific-packs" / pack_id
        pack = json.loads((base / "asset-pack.json").read_text(encoding="utf-8"))
        need(file_identity(base / "asset-pack.json") == binding["catalog_sha256"], pack_id + ": catalog mismatch")
        need(file_identity(base / pack["release_audit"]["file"]) == binding["audit_sha256"], pack_id + ": historical audit mismatch")
        need(canonical(pack["rights_records"]) == binding["original_rights_records_sha256"], pack_id + ": original owner grant mismatch")
        review = json.loads((base / binding["revision_receipt"]).read_text(encoding="utf-8"))
        need(canonical(review) == binding["revision_receipt_sha256"], pack_id + ": accepted revision receipt mismatch")
        need(all(review["review"].get(key) == value for key, value in {
            "status": "accepted", "scientific_review": "pass", "visual_review": "pass", "editor_checks": "pass"}.items()),
            pack_id + ": accepted scientific, visual and native editor review required")
        need(all(row.get("selected_public_license") == "CC0-1.0" and row.get("public_distribution_authorized") is True
                 and row.get("effective_date") == "2026-10-10" for row in pack["rights_records"]),
             pack_id + ": existing CC0 permission required")
    scene_root = root / "assets/scientific-scenes"
    need(file_identity(scene_root / "release-rights.v1.json") == record["scene_rights_sha256"], "original scene rights mismatch")
    for scene_id, binding in record["scenes"].items():
        need(file_identity(scene_root / "scenes" / (scene_id + ".scene.json")) == binding["scene_sha256"]
             and file_identity(scene_root / "previews" / (scene_id + ".svg")) == binding["preview_sha256"],
             scene_id + ": reviewed scene identity mismatch")
    reviews = record.get("review", {})
    need(all(reviews.get(key) == "pass" for key in ("scientific_review", "visual_review", "editor_checks")), "completed reviews required")
    need(bool(record.get("user_authorization", {}).get("instruction")) and len(reviews.get("evidence", [])) >= 6,
         "user instruction and concrete review evidence required")
    need(file_identity(root / reviews["acceptance_document"]) == reviews["acceptance_document_sha256"],
         "tracked acceptance document mismatch")
    return record


# A successor binds the complete collection while preserving the original exact
# decision and every historical grant. Unknown additions never inherit approval.
EXPANSION_RECORD = "config/scientific-product-release-2026-10-15-expansion.json"
EXPANSION_RECORD_SHA256 = "3a0ed4c18cb7f8f2824d6fe7c5298437bc329e71bcb999a00e80f7ab41d25cca"
EXPANSION_PACK_COUNTS = {"cell-structure-stress": (40, 20), "tumor-microenvironment": (20, 10), "analysis-graphics": (20, 10)}
BASELINE_PACK_IDS = frozenset({"core-biology", "core-experimental-biology", "immunology-oncology", "protein-homeostasis", *PACK_IDS})


def active_record_path(record: dict | None) -> str | None:
    if record is None:
        return None
    if record.get("schema") == "figureStudio.scientificProductRelease.v3":
        return STYLE_FOUR_RECORD
    return EXPANSION_RECORD if record.get("schema") == "figureStudio.scientificProductRelease.v2" else RECORD


def baseline_inventory(root: Path, *, inventory_override: list | None = None) -> list[dict[str, str]]:
    """Reconstruct only the immutable predecessor, never a future approval."""
    if inventory_override is None and (root / STYLE_FOUR_RECORD).exists():
        inventory_override = style_four_predecessor_inventory(root, _style_four_record(root))
    inventory = asset_inventory(root) if inventory_override is None else inventory_override
    registry_path = root / "assets/scientific-packs/library.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    registry["packs"] = [row for row in registry["packs"] if row["id"] in BASELINE_PACK_IDS]
    # These two additive fields belong only to the finite Style 4 successor.
    # Their removal reconstructs historical source; it never grants approval.
    registry.pop("art_styles", None)
    registry.pop("art_style_notes", None)
    prefixes = tuple("assets/scientific-packs/" + name + "/" for name in EXPANSION_PACK_COUNTS)
    result = [dict(row) for row in inventory if not row["path"].startswith(prefixes)]
    for row in result:
        if row["path"] == "assets/scientific-packs/library.json":
            row["sha256"] = canonical(registry)
    return result


def _validate_expansion(root: Path, *, required: bool = False, inventory_override: list | None = None) -> dict | None:
    root = Path(root)
    path = root / EXPANSION_RECORD
    additions = any((root / "assets/scientific-packs" / name).exists() for name in EXPANSION_PACK_COUNTS)
    if not path.exists():
        if additions:
            if required:
                raise ValueError("Scientific product release: expanded collection decision is missing")
            return None  # valid private work in progress has no public approval
        return _validate_baseline(root, required=required)
    def need(condition: bool, message: str) -> None:
        if not condition:
            raise ValueError("Scientific product release expansion: " + message)
    need(path.is_file() and not path.is_symlink(), "decision must be an ordinary file")
    record = json.loads(path.read_text(encoding="utf-8"))
    need(canonical(record) == EXPANSION_RECORD_SHA256, "reviewed decision exact identity mismatch")
    need(record.get("schema") == "figureStudio.scientificProductRelease.v2"
         and record.get("release_id") == "cell-stress-tme-analysis.2026-10-15"
         and record.get("release_date") == "2026-10-15", "decision schema/date mismatch")
    need(record.get("decision") == "approved_for_matching_public_web_and_superbench_packages", "product approval is absent")
    need(record.get("library") == {"drawing_count":486,"concept_count":386,"pack_count":11,"scene_count":12}, "finite expanded collection count mismatch")
    need(record.get("predecessor") == {"record":RECORD,"sha256":RECORD_SHA256}, "predecessor decision differs")
    baseline = _validate_baseline(root, required=True, inventory_override=baseline_inventory(root, inventory_override=inventory_override))
    need(set(record.get("new_packs", {})) == set(EXPANSION_PACK_COUNTS), "finite new pack set differs")
    need(set(record.get("packs", {})) == PACK_IDS | set(EXPANSION_PACK_COUNTS), "effective pack approval set differs")
    need(all(record["packs"].get(name) == binding for name,binding in baseline["packs"].items())
         and record.get("scenes") == baseline["scenes"], "historical approvals changed")
    inventory = asset_inventory(root) if inventory_override is None else inventory_override
    need(record.get("asset_inventory_sha256") == canonical(inventory)
         and record.get("asset_file_count") == len(inventory), "exact reviewed asset inventory mismatch")
    registry = json.loads((root / "assets/scientific-packs/library.json").read_text(encoding="utf-8"))
    need({r["id"] for r in registry["packs"]} == BASELINE_PACK_IDS | set(EXPANSION_PACK_COUNTS)
         and len(registry["packs"]) == 11, "registered collection differs")
    for name,(drawings,concepts) in EXPANSION_PACK_COUNTS.items():
        base = root / "assets/scientific-packs" / name
        pack = json.loads((base / "asset-pack.json").read_text(encoding="utf-8"))
        binding = record["new_packs"][name]
        need(record["packs"][name] == binding, name + ": effective approval differs")
        need(len(pack["assets"]) == pack["asset_count"] == drawings
             and len({a["concept_id"] for a in pack["assets"]}) == pack["concept_count"] == concepts,
             name + ": authored counts differ")
        need(file_identity(base / "asset-pack.json") == binding["catalog_sha256"]
             and file_identity(base / pack["release_audit"]["file"]) == binding["audit_sha256"], name + ": catalog/audit mismatch")
        need(all(a.get("license") == "CC0-1.0" and a.get("source_type") == "clean_room_original_vector"
                 for a in pack["assets"]), name + ": original CC0 contribution required")
        need(canonical(pack["rights_records"]) == binding["rights_records_sha256"], name + ": contribution license record mismatch")
        need(pack.get("contribution_license_policy") == "original-vectors.cc0.repository-policy.2026-10-15"
             and all(row.get("kind") == "repository_policy_license" and row.get("rights_basis") == "repository_policy_original_output"
                     and row.get("effective_date") == "2026-10-15" and row.get("selected_public_license") == "CC0-1.0"
                     and row.get("public_distribution_authorized") is True for row in pack["rights_records"]),
             name + ": prospective repository license policy required, not an inherited owner grant")

    notice = record.get("contribution_notice", {})
    need(notice.get("file") == "assets/LICENSE-CELL-STRESS-TME-ANALYSIS-CC0-1.0.md"
         and file_identity(root / notice["file"]) == notice.get("sha256")
         and file_identity(root / "LICENSE_POLICY.md") == record.get("license_policy_sha256"), "prospective contribution notice/policy mismatch")
    review = record.get("review", {})
    need(all(review.get(key) == "pass" for key in ("scientific_review","visual_review","editor_checks")), "completed independent reviews required")
    need(bool(record.get("user_authorization", {}).get("instruction")) and len(review.get("evidence", [])) >= 6,
         "user instruction and concrete review evidence required")
    need(file_identity(root / review["acceptance_document"]) == review["acceptance_document_sha256"], "acceptance document mismatch")
    return record


# This third finite decision adds a treatment of the existing drawings. It does
# not modify the 2026-10-10 grants, the 2026-10-15 contribution records, or their
# independently accepted product decisions. A pending record is not approval.
STYLE_FOUR_RECORD = "config/scientific-product-release-2026-10-17-style4.json"
STYLE_FOUR_RECORD_SHA256 = "209bee13006174034ca1616e5f6cfec3d38f86b4db9f725de8db38bbb83fea40"
STYLE_FOUR_MANIFEST = "assets/scientific-packs/style-4/manifest.json"
STYLE_FOUR_PREFIX = "assets/scientific-packs/style-4/"
STYLE_FOUR_ARCHIVE_SHA256 = "7e4d6f1bb5de5d87ce4dd8a43f190e308c57046313500cab6920a1d9f9fa7ea0"
STYLE_FOUR_RECOVERY_ARCHIVE_SHA256 = "50ef7848520126461ac82f7df0c9fd4682c5211b3d2c98d286067573aa00717f"
STYLE_FOUR_LIBRARY = {"drawing_count":486,"concept_count":386,"pack_count":11,"scene_count":12,
                      "drawing_style_count":4,"style_4_variant_count":486}


def _style_four_need(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError("Scientific product release Style 4: " + message)


def _style_four_record(root: Path) -> dict:
    path = root / STYLE_FOUR_RECORD
    _style_four_need(path.is_file() and not path.is_symlink(), "decision must be an ordinary file")
    record = json.loads(path.read_text(encoding="utf-8"))
    _style_four_need(canonical(record) == STYLE_FOUR_RECORD_SHA256, "decision exact identity mismatch")
    return record


def style_four_predecessor_inventory(root: Path, record: dict) -> list[dict[str, str]]:
    """Remove only this decision's declared additions, never unknown art."""
    inventory = asset_inventory(root)
    additions = record.get("added_asset_files", [])
    _style_four_need(isinstance(additions, list) and bool(additions), "finite added file list is missing")
    paths = [row.get("path", "") for row in additions if isinstance(row, dict)]
    _style_four_need(len(paths) == len(additions) == len(set(paths))
                     and all(path.startswith(STYLE_FOUR_PREFIX)
                             and not PurePosixPath(path).is_absolute()
                             and ".." not in PurePosixPath(path).parts for path in paths),
                     "added file list contains an unsafe, duplicate or out-of-scope path")
    actual = [row for row in inventory if row["path"].startswith(STYLE_FOUR_PREFIX)]
    _style_four_need(actual == additions, "exact finite Style 4 file inventory mismatch")
    excluded = set(paths)
    result = [dict(row) for row in inventory if row["path"] not in excluded]
    registry = json.loads((root / "assets/scientific-packs/library.json").read_text(encoding="utf-8"))
    registry.pop("art_styles", None)
    registry.pop("art_style_notes", None)
    for row in result:
        if row["path"] == "assets/scientific-packs/library.json":
            row["sha256"] = canonical(registry)
    return result


def _validate_style_four(root: Path, *, required: bool = False) -> dict | None:
    record = _style_four_record(root)
    need = _style_four_need
    need(record.get("schema") == "figureStudio.scientificProductRelease.v3"
         and record.get("release_id") == "user-supplied-style-4.2026-10-17"
         and record.get("release_date") == "2026-10-17", "decision schema/date mismatch")
    need(record.get("library") == STYLE_FOUR_LIBRARY, "finite collection count mismatch")
    need(record.get("predecessor") == {"record":EXPANSION_RECORD,"sha256":EXPANSION_RECORD_SHA256},
         "predecessor decision differs")
    inventory = asset_inventory(root)
    predecessor_inventory = style_four_predecessor_inventory(root, record)
    predecessor = _validate_expansion(root, required=True, inventory_override=predecessor_inventory)
    need(record.get("packs") == predecessor["packs"] and record.get("scenes") == predecessor["scenes"],
         "historical product approvals changed")
    need(record.get("asset_inventory_sha256") == canonical(inventory)
         and record.get("asset_file_count") == len(inventory), "complete reviewed asset inventory mismatch")
    registry_path = root / "assets/scientific-packs/library.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    need(record.get("registry_sha256") == file_identity(registry_path), "registered drawing styles differ")
    need(registry.get("art_styles") == [{"id":"style-4","name":"Style 4",
         "path":"style-4/manifest.json","asset_count":486}], "finite registered style differs")
    manifest_path = root / STYLE_FOUR_MANIFEST
    binding = record.get("style_4", {})
    need(binding.get("manifest") == STYLE_FOUR_MANIFEST
         and binding.get("manifest_sha256") == file_identity(manifest_path), "Style 4 manifest differs")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    need(manifest.get("schema_version") == "1.0.0" and manifest.get("id") == "style-4", "style manifest schema differs")
    source_ids = set()
    for pack in registry["packs"]:
        catalog = json.loads((root / "assets/scientific-packs" / pack["path"]).read_text(encoding="utf-8"))
        source_ids.update(asset["id"] for asset in catalog["assets"])
    variants = manifest.get("assets", [])
    need(len(variants) == 486 and len({row.get("asset_id") for row in variants}) == 486
         and {row.get("asset_id") for row in variants} == source_ids, "exact 486 source-to-style mappings required")
    registered_files = {row["path"]:row["sha256"] for row in record["added_asset_files"]}
    for variant in variants:
        file = str(variant.get("file", ""))
        need(file.startswith("svg/") and file.endswith(".svg") and "\\" not in file
             and ":" not in file and ".." not in PurePosixPath(file).parts,
             "variant path is unsafe")
        need(registered_files.get(STYLE_FOUR_PREFIX + file) == variant.get("sha256"),
             "variant bytes do not match the finite file list")
    need(record.get("source_archive", {}).get("sha256") == STYLE_FOUR_ARCHIVE_SHA256
         and record["source_archive"].get("svg_count") == 486, "supplied archive identity differs")
    recovery = record.get("recovery_archive", {})
    selection = root / "assets/scientific-packs/style-4/recovery-selection.json"
    need(recovery.get("filename") == "style4_completed_16.zip"
         and recovery.get("sha256") == STYLE_FOUR_RECOVERY_ARCHIVE_SHA256
         and recovery.get("selected_svg_count") == 16
         and recovery.get("selection_file") == "assets/scientific-packs/style-4/recovery-selection.json"
         and recovery.get("selection_sha256") == file_identity(selection), "finite earlier-art recovery differs")
    selected = json.loads(selection.read_text(encoding="utf-8"))
    recovered_ids = {row["asset_id"] for row in selected["assets"]}
    need(len(recovered_ids) == selected.get("asset_count") == 16
         and selected.get("source_archive", {}).get("sha256") == STYLE_FOUR_RECOVERY_ARCHIVE_SHA256
         and {row["asset_id"] for row in variants if "source_provenance" in row} == recovered_ids,
         "only the exact selected 16 earlier variants may replace final ZIP artwork")
    need(manifest.get("recovery_archive", {}).get("sha256") == STYLE_FOUR_RECOVERY_ARCHIVE_SHA256
         and manifest["recovery_archive"].get("selection_sha256") == hashlib.sha256(selection.read_bytes()).hexdigest(),
         "manifest recovery source/selection identity differs")
    contribution = record.get("contribution_notice", {})
    need(contribution.get("file") == "assets/LICENSE-STYLE-4-CC0-1.0.md"
         and contribution.get("package_copy") == "app/legal/assets/LICENSE-STYLE-4-CC0-1.0.md"
         and contribution.get("rights_basis") == "repository_policy_user_supplied_derivative"
         and contribution.get("selected_public_license") == "CC0-1.0"
         and contribution.get("effective_date") == "2026-10-17",
         "prospective contribution basis differs")
    for relative in (contribution["file"],contribution["package_copy"]):
        path = root / relative
        need(path.is_file() and not path.is_symlink() and file_identity(path) == contribution.get("sha256"),
             "prospective contribution notice or packaged copy differs")
    authorization = record.get("user_authorization", {})
    need(bool(authorization.get("instruction")) and authorization.get("new_personal_attestation") is False,
         "actual user instruction and non-attestation boundary required")
    comparison = record.get("supplied_artwork_comparison", {})
    need(comparison.get("rendered_svg_count") == 486 and comparison.get("unchanged_pixel_count") == 243
         and comparison.get("near_unchanged_count") == 20 and comparison.get("comparison_size_pixels") == 256,
         "supplied artwork comparison must preserve measured limitations")
    effective = record.get("effective_selection_comparison", {})
    need(effective.get("rendered_svg_count") == 486 and effective.get("unchanged_pixel_count") == 235
         and effective.get("near_unchanged_count") == 16 and effective.get("recovered_svg_count") == 16
         and effective.get("corrected_path_count") == 4,
         "effective recovered artwork comparison must preserve measured limitations")
    review = record.get("review", {})
    acceptance = review.get("acceptance_document", "")
    need(acceptance == "docs/scientific-assets/STYLE_4_LIBRARY_2026_10_17.md"
         and file_identity(root / acceptance) == review.get("acceptance_document_sha256"),
         "tracked acceptance document differs")
    decision = record.get("decision")
    need(decision in {"pending_editor_and_release_review", "approved_for_matching_public_web_and_superbench_packages"},
         "unsupported product decision")
    if decision != "approved_for_matching_public_web_and_superbench_packages":
        if required:
            need(False, "product approval remains pending")
        return None
    need(all(review.get(key) == "pass" for key in ("input_integrity","scientific_source_comparison",
         "independent_visual_review","native_editor_checks","save_cold_open","host_parity")),
         "completed scientific, visual, editor and persistence reviews required")
    evidence = review.get("evidence", [])
    need(len(evidence) >= 6 and len({row.get("file") for row in evidence}) == len(evidence)
         and all(row.get("file") and len(row.get("sha256", "")) == 64
                 and all(char in "0123456789abcdef" for char in row["sha256"]) for row in evidence),
         "concrete source-bound review evidence required")
    return record


def validate(root: Path, *, required: bool = False) -> dict | None:
    root = Path(root)
    if (root / STYLE_FOUR_RECORD).exists():
        return _validate_style_four(root, required=required)
    registry_path = root / "assets/scientific-packs/library.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8")) if registry_path.exists() else {}
    if registry.get("art_styles") or (root / STYLE_FOUR_PREFIX).exists():
        if required:
            _style_four_need(False, "drawing-style product decision is missing")
        return None
    return _validate_expansion(root, required=required)
