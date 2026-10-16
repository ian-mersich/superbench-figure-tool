"""Finite product decisions preserve historical grants and bind exact reviewed art.

The successor adds 80 original drawings without extending old owner grants or
approving later artwork. Scientific schemas, geometry, provenance and native
editing remain separately validated.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

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
    return EXPANSION_RECORD if record.get("schema") == "figureStudio.scientificProductRelease.v2" else RECORD


def baseline_inventory(root: Path) -> list[dict[str, str]]:
    """Reconstruct only the immutable predecessor, never a future approval."""
    inventory = asset_inventory(root)
    registry_path = root / "assets/scientific-packs/library.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    registry["packs"] = [row for row in registry["packs"] if row["id"] in BASELINE_PACK_IDS]
    prefixes = tuple("assets/scientific-packs/" + name + "/" for name in EXPANSION_PACK_COUNTS)
    result = [dict(row) for row in inventory if not row["path"].startswith(prefixes)]
    for row in result:
        if row["path"] == "assets/scientific-packs/library.json":
            row["sha256"] = canonical(registry)
    return result


def validate(root: Path, *, required: bool = False) -> dict | None:
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
    baseline = _validate_baseline(root, required=True, inventory_override=baseline_inventory(root))
    need(set(record.get("new_packs", {})) == set(EXPANSION_PACK_COUNTS), "finite new pack set differs")
    need(set(record.get("packs", {})) == PACK_IDS | set(EXPANSION_PACK_COUNTS), "effective pack approval set differs")
    need(all(record["packs"].get(name) == binding for name,binding in baseline["packs"].items())
         and record.get("scenes") == baseline["scenes"], "historical approvals changed")
    inventory = asset_inventory(root)
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
