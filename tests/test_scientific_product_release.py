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
    for name in ("scientific-packs", "scientific-scenes"):
        shutil.copytree(ROOT / "assets" / name, tmp_path / "assets" / name)
    (tmp_path / "config").mkdir()
    shutil.copy2(ROOT / release.RECORD, tmp_path / release.RECORD)
    record = json.loads((tmp_path / release.RECORD).read_text(encoding="utf-8"))
    document = record["review"]["acceptance_document"]
    (tmp_path / document).parent.mkdir(parents=True)
    shutil.copy2(ROOT / document, tmp_path / document)
    assert release.validate(tmp_path)["library"]["drawing_count"] == 406
    return tmp_path


def test_exact_current_product_decision_and_original_pending_audits_are_compatible():
    record = release.validate(ROOT, required=True)
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
