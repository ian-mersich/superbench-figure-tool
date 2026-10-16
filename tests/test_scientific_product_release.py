"""The publication decision accepts one exact collection, not later edits."""
from __future__ import annotations

import json
from pathlib import Path
import shutil

import pytest

from scripts import scientific_product_release as release

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def candidate(tmp_path):
    # Historical approval remains testable against its exact eight-pack source.
    packs = tmp_path / "assets/scientific-packs"
    packs.mkdir(parents=True)
    for name in release.BASELINE_PACK_IDS:
        shutil.copytree(ROOT / "assets/scientific-packs" / name, packs / name)
    registry = json.loads((ROOT / "assets/scientific-packs/library.json").read_text(encoding="utf-8"))
    registry["packs"] = [row for row in registry["packs"] if row["id"] in release.BASELINE_PACK_IDS]
    (packs / "library.json").write_text(json.dumps(registry), encoding="utf-8")
    shutil.copytree(ROOT / "assets/scientific-scenes", tmp_path / "assets/scientific-scenes")
    (tmp_path / "config").mkdir()
    shutil.copy2(ROOT / release.RECORD, tmp_path / release.RECORD)
    record = json.loads((tmp_path / release.RECORD).read_text(encoding="utf-8"))
    document = record["review"]["acceptance_document"]
    (tmp_path / document).parent.mkdir(parents=True)
    shutil.copy2(ROOT / document, tmp_path / document)
    assert release.validate(tmp_path)["library"]["drawing_count"] == 406
    return tmp_path


def test_exact_current_product_decision_and_original_pending_audits_are_compatible():
    record = release._validate_baseline(ROOT, required=True, inventory_override=release.baseline_inventory(ROOT))
    assert set(record["packs"]) == release.PACK_IDS
    for pack_id in release.PACK_IDS:
        catalog = json.loads((ROOT / "assets/scientific-packs" / pack_id / "asset-pack.json").read_text(encoding="utf-8"))
        assert catalog["release_audit"]["product_release_status"] == "pending_quality_and_product_review"
        assert catalog["rights_records"][0]["effective_date"] == "2026-10-10"


def test_unqualified_source_has_no_supplemental_approval(tmp_path):
    assert release.validate(tmp_path) is None
    with pytest.raises(ValueError, match="decision is missing"):
        release.validate(tmp_path, required=True)


@pytest.mark.parametrize("mutation", ["approval", "unknown_pack", "evidence", "license_date", "artwork", "extra_asset", "scene", "scene_preview", "revision_receipt"])
def test_product_approval_rejects_each_exact_source_or_decision_mutation(candidate, mutation):
    if mutation in {"approval", "unknown_pack", "evidence"}:
        path = candidate / release.RECORD
        document = json.loads(path.read_text(encoding="utf-8"))
        if mutation == "approval":
            document["decision"] = "pending"
        elif mutation == "unknown_pack":
            document["packs"]["unreviewed-pack"] = document["packs"]["rna-methods"]
        else:
            document["review"]["evidence"] = []
        path.write_text(json.dumps(document), encoding="utf-8")
        expected = "decision exact identity"
    else:
        base = candidate / "assets/scientific-packs/rna-methods"
        if mutation == "license_date":
            path = base / "asset-pack.json"
            document = json.loads(path.read_text(encoding="utf-8"))
            document["rights_records"][0]["effective_date"] = "2026-10-15"
            path.write_text(json.dumps(document), encoding="utf-8")
        elif mutation == "artwork":
            path = next((base / "svg").glob("*.svg"))
            path.write_bytes(path.read_bytes().replace(b"<svg", b'<svg opacity="0.5"', 1))
        elif mutation == "extra_asset":
            (base / "svg/unreviewed.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg"/>', encoding="utf-8")
        elif mutation in {"scene", "scene_preview"}:
            path = candidate / "assets/scientific-scenes" / ("scenes/single-cell-rna-workflow.scene.json" if mutation == "scene" else "previews/single-cell-rna-workflow.svg")
            path.write_bytes(path.read_bytes() + (b" " if mutation == "scene_preview" else b"\n"))
            if mutation == "scene":
                document = json.loads(path.read_text(encoding="utf-8"))
                document["summary"] += " changed"
                path.write_text(json.dumps(document), encoding="utf-8")
        else:
            path = base / "artwork-revision-2026-10-13.json"
            document = json.loads(path.read_text(encoding="utf-8"))
            document["review"]["scientific_review"] = "pending"
            path.write_text(json.dumps(document), encoding="utf-8")
        expected = "asset inventory mismatch"
    with pytest.raises(ValueError, match=expected):
        release.validate(candidate, required=True)


def test_new_contributions_do_not_inherit_the_predecessor_product_decision(candidate):
    (candidate / "assets/scientific-packs/cell-structure-stress").mkdir()
    assert release.validate(candidate) is None
    with pytest.raises(ValueError, match="expanded collection decision is missing"):
        release.validate(candidate, required=True)


@pytest.fixture
def expanded(tmp_path):
    if not (ROOT / release.EXPANSION_RECORD).exists():
        pytest.skip("The exact successor is intentionally pending independent qualification")
    for name in ("scientific-packs", "scientific-scenes"):
        shutil.copytree(ROOT / "assets" / name, tmp_path / "assets" / name)
    for relative in (release.RECORD, release.EXPANSION_RECORD, "LICENSE_POLICY.md",
                     "assets/LICENSE-CELL-STRESS-TME-ANALYSIS-CC0-1.0.md"):
        target = tmp_path / relative; target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, target)
    for relative in (release.RECORD, release.EXPANSION_RECORD):
        document = json.loads((ROOT / relative).read_text(encoding="utf-8"))["review"]["acceptance_document"]
        target = tmp_path / document; target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / document, target)
    return tmp_path


def test_exact_successor_keeps_old_grants_and_new_prospective_policy_distinct(expanded):
    record = release.validate(expanded, required=True)
    assert record["library"] == {"drawing_count":486,"concept_count":386,"pack_count":11,"scene_count":12}
    assert set(record["new_packs"]) == set(release.EXPANSION_PACK_COUNTS)
    for name in release.PACK_IDS:
        pack = json.loads((expanded / "assets/scientific-packs" / name / "asset-pack.json").read_text(encoding="utf-8"))
        assert pack["rights_records"][0]["effective_date"] == "2026-10-10"
    for name in release.EXPANSION_PACK_COUNTS:
        pack = json.loads((expanded / "assets/scientific-packs" / name / "asset-pack.json").read_text(encoding="utf-8"))
        rights = pack["rights_records"][0]
        assert rights["kind"] == "repository_policy_license"
        assert rights["rights_basis"] == "repository_policy_original_output" and rights["effective_date"] == "2026-10-15"
        assert pack["release_audit"]["release_effective_date"] is None
        assert pack["release_audit"]["product_release_status"] == "pending_quality_and_product_review"


@pytest.mark.parametrize("mutation", ["successor_approval","unreviewed_pack","new_artwork","old_artwork","new_grant","old_grant","registry","policy","notice","predecessor"])
def test_successor_rejects_each_unreviewed_change(expanded, mutation):
    if mutation in {"successor_approval","unreviewed_pack"}:
        p = expanded / release.EXPANSION_RECORD; data = json.loads(p.read_text(encoding="utf-8"))
        if mutation == "successor_approval": data["decision"] = "pending"
        else: data["new_packs"]["unreviewed-pack"] = {}
        p.write_text(json.dumps(data), encoding="utf-8")
    elif mutation in {"new_artwork","old_artwork"}:
        base = expanded / "assets/scientific-packs" / ("cell-structure-stress" if mutation == "new_artwork" else "core-biology")
        p = next((base / "svg").glob("*.svg")); p.write_bytes(p.read_bytes().replace(b"<svg",b'<svg opacity="0.5"',1))
    elif mutation in {"new_grant","old_grant"}:
        p = expanded / "assets/scientific-packs" / ("cell-structure-stress" if mutation == "new_grant" else "rna-methods") / "asset-pack.json"
        data = json.loads(p.read_text(encoding="utf-8")); data["rights_records"][0]["effective_date"] = "2026-10-11";p.write_text(json.dumps(data),encoding="utf-8")
    elif mutation == "registry":
        p = expanded / "assets/scientific-packs/library.json";data=json.loads(p.read_text(encoding="utf-8"));data["packs"].reverse();p.write_text(json.dumps(data),encoding="utf-8")
    elif mutation == "predecessor":
        p=expanded/release.RECORD;data=json.loads(p.read_text(encoding="utf-8"));data["decision"]="pending";p.write_text(json.dumps(data),encoding="utf-8")
    else:
        p=expanded/("LICENSE_POLICY.md" if mutation=="policy" else "assets/LICENSE-CELL-STRESS-TME-ANALYSIS-CC0-1.0.md");p.write_bytes(p.read_bytes()+b"changed")
    with pytest.raises(ValueError): release.validate(expanded,required=True)
