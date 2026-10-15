"""One finite product decision; original CC0 grants and revision audits stay intact.

This supplement authorizes the exact reviewed 406-drawing/12-scene collection.
It does not change an owner's grant, accept later artwork, or replace scientific
schema, geometry, provenance, predecessor, or editable-region validation.
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


def validate(root: Path, *, required: bool = False) -> dict | None:
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
    inventory = asset_inventory(root)
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
