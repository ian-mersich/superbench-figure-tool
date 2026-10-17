"""The publication decision accepts one exact collection, not later edits."""
from __future__ import annotations

import json
import importlib.util
from pathlib import Path
import shutil
import sys

import pytest

from scripts import scientific_product_release as release

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def candidate(tmp_path_factory):
    # Historical approval remains testable against its exact eight-pack source.
    # Short fixture directories keep historical nested SVG paths usable on
    # Windows even when pytest's base lives in the repository QA output root.
    tmp_path = tmp_path_factory.mktemp("p")
    packs = tmp_path / "assets/scientific-packs"
    packs.mkdir(parents=True)
    for name in release.BASELINE_PACK_IDS:
        shutil.copytree(ROOT / "assets/scientific-packs" / name, packs / name)
    registry = json.loads((ROOT / "assets/scientific-packs/library.json").read_text(encoding="utf-8"))
    registry["packs"] = [row for row in registry["packs"] if row["id"] in release.BASELINE_PACK_IDS]
    registry.pop("art_styles", None)
    registry.pop("art_style_notes", None)
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
def expanded(tmp_path_factory):
    tmp_path = tmp_path_factory.mktemp("e")
    if not (ROOT / release.EXPANSION_RECORD).exists():
        pytest.skip("The exact successor is intentionally pending independent qualification")
    for name in ("scientific-packs", "scientific-scenes"):
        shutil.copytree(ROOT / "assets" / name, tmp_path / "assets" / name,
                        ignore=shutil.ignore_patterns("style-4"))
    registry_path = tmp_path / "assets/scientific-packs/library.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    registry.pop("art_styles", None)
    registry.pop("art_style_notes", None)
    registry_path.write_text(json.dumps(registry), encoding="utf-8")
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


@pytest.fixture
def style_four(expanded):
    """Use the real finite addition while keeping old-decision fixtures exact."""
    shutil.copytree(ROOT / "assets/scientific-packs/style-4", expanded / "assets/scientific-packs/style-4")
    for relative in (release.STYLE_FOUR_RECORD, "assets/scientific-packs/library.json",
                     "assets/LICENSE-STYLE-4-CC0-1.0.md", "app/legal/assets/LICENSE-STYLE-4-CC0-1.0.md",
                     "docs/scientific-assets/STYLE_4_LIBRARY_2026_10_17.md"):
        target = expanded / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, target)
    return expanded


def test_style_four_preserves_exact_predecessor_decisions(style_four):
    record = release._style_four_record(style_four)
    predecessor = release._validate_expansion(style_four, required=True,
        inventory_override=release.style_four_predecessor_inventory(style_four, record))
    assert predecessor["release_id"] == "cell-stress-tme-analysis.2026-10-15"
    assert release._validate_baseline(style_four, required=True,
        inventory_override=release.baseline_inventory(style_four))["library"]["drawing_count"] == 406
    if record["decision"] == "pending_editor_and_release_review":
        assert release.validate(style_four) is None
        with pytest.raises(ValueError, match="product approval remains pending"):
            release.validate(style_four, required=True)
    else:
        assert release.validate(style_four, required=True)["library"]["style_4_variant_count"] == 486


@pytest.mark.parametrize("mutation", ["svg", "source_metadata", "manifest", "extra_style_file", "extra_elsewhere",
                                    "old_artwork", "registry_notes", "notice", "packaged_notice", "decision"])
def test_style_four_rejects_undeclared_changes_and_does_not_hide_old_mutations(style_four, mutation):
    style = style_four / "assets/scientific-packs/style-4"
    if mutation == "svg":
        path = next((style / "svg").glob("*.svg"))
        path.write_bytes(path.read_bytes().replace(b"<svg", b'<svg opacity="0.5"', 1))
    elif mutation == "source_metadata":
        path = style / "source/README.txt"
        path.write_bytes(path.read_bytes() + b"unreviewed addition")
    elif mutation == "manifest":
        path = style / "manifest.json"
        data = json.loads(path.read_text(encoding="utf-8")); data["assets"][0]["sha256"] = "0" * 64
        path.write_text(json.dumps(data), encoding="utf-8")
    elif mutation == "extra_style_file":
        (style / "svg/unreviewed.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg"/>', encoding="utf-8")
    elif mutation == "extra_elsewhere":
        (style_four / "assets/scientific-packs/unreviewed.json").write_text("{}", encoding="utf-8")
    elif mutation == "old_artwork":
        path = next((style_four / "assets/scientific-packs/core-biology/svg").glob("*.svg"))
        path.write_bytes(path.read_bytes().replace(b"<svg", b'<svg opacity="0.5"', 1))
    elif mutation == "registry_notes":
        path = style_four / "assets/scientific-packs/library.json"
        data = json.loads(path.read_text(encoding="utf-8")); data["art_style_notes"] = "486 new biological concepts"
        path.write_text(json.dumps(data), encoding="utf-8")
    elif mutation in {"notice", "packaged_notice"}:
        path = style_four / ("assets/LICENSE-STYLE-4-CC0-1.0.md" if mutation == "notice" else "app/legal/assets/LICENSE-STYLE-4-CC0-1.0.md")
        path.write_bytes(path.read_bytes() + b"changed")
    else:
        path = style_four / release.STYLE_FOUR_RECORD
        data = json.loads(path.read_text(encoding="utf-8")); data["decision"] = "unreviewed_product_approval"
        path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError):
        release.validate(style_four, required=True)


def test_pending_style_four_is_valid_input_but_not_public_product_approval(style_four, monkeypatch):
    path = style_four / release.STYLE_FOUR_RECORD
    data = json.loads(path.read_text(encoding="utf-8"))
    data["decision"] = "pending_editor_and_release_review"
    path.write_text(json.dumps(data), encoding="utf-8")
    monkeypatch.setattr(release, "STYLE_FOUR_RECORD_SHA256", release.canonical(data))
    assert release.validate(style_four) is None
    with pytest.raises(ValueError, match="product approval remains pending"):
        release.validate(style_four, required=True)


def test_style_four_approval_requires_completed_reviews_even_with_bound_record(style_four, monkeypatch):
    path = style_four / release.STYLE_FOUR_RECORD
    data = json.loads(path.read_text(encoding="utf-8"))
    data["decision"] = "approved_for_matching_public_web_and_superbench_packages"
    data["review"]["native_editor_checks"] = "pending"
    path.write_text(json.dumps(data), encoding="utf-8")
    monkeypatch.setattr(release, "STYLE_FOUR_RECORD_SHA256", release.canonical(data))
    with pytest.raises(ValueError, match="completed scientific, visual, editor and persistence reviews required"):
        release.validate(style_four, required=True)


def test_style_four_missing_decision_cannot_inherit_old_approval(style_four):
    (style_four / release.STYLE_FOUR_RECORD).unlink()
    assert release.validate(style_four) is None
    with pytest.raises(ValueError, match="drawing-style product decision is missing"):
        release.validate(style_four, required=True)


def test_completed_bound_style_four_fixture_selects_only_its_own_finite_record(style_four, monkeypatch):
    """Synthetic positive control exercises the final branch, not source approval."""
    path = style_four / release.STYLE_FOUR_RECORD
    data = json.loads(path.read_text(encoding="utf-8"))
    data["decision"] = "approved_for_matching_public_web_and_superbench_packages"
    for key in ("input_integrity","scientific_source_comparison","independent_visual_review",
                "native_editor_checks","save_cold_open","host_parity"):
        data["review"][key] = "pass"
    data["review"]["evidence"] = [{"file":f"tests/synthetic-review-{index}.json",
                                   "sha256":release.canonical({"testFixture":index})} for index in range(6)]
    path.write_text(json.dumps(data), encoding="utf-8")
    monkeypatch.setattr(release, "STYLE_FOUR_RECORD_SHA256", release.canonical(data))
    approved = release.validate(style_four, required=True)
    assert approved["library"]["style_4_variant_count"] == 486
    assert release.active_record_path(approved) == release.STYLE_FOUR_RECORD
    assert approved["packs"] == json.loads((style_four/release.EXPANSION_RECORD).read_text())["packs"]


@pytest.fixture
def asset_validator():
    name = "style4_test_scientific_asset_validator"
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts/validate-scientific-assets.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_registered_style_four_runs_the_full_separate_artwork_validator(asset_validator):
    path = ROOT / "assets/scientific-packs/library.json"
    styles = asset_validator.validate_registered_art_styles(path,json.loads(path.read_text(encoding="utf-8")))
    assert styles == [{"id":"style-4","directory":"style-4","asset_count":486,"file_count":498}]


@pytest.mark.parametrize("mutation", ["unknown_style", "traversal", "duplicate", "coverage", "missing_note"])
def test_drawing_style_registration_is_finite_and_never_loosens_directory_checks(asset_validator, mutation):
    path = ROOT / "assets/scientific-packs/library.json"
    registry = json.loads(path.read_text(encoding="utf-8"))
    if mutation == "unknown_style": registry["art_styles"][0]["id"] = "style-5"
    elif mutation == "traversal": registry["art_styles"][0]["path"] = "../style-4/manifest.json"
    elif mutation == "duplicate": registry["art_styles"].append(registry["art_styles"][0])
    elif mutation == "coverage": registry["art_styles"][0]["asset_count"] = 485
    else: registry.pop("art_style_notes")
    with pytest.raises(ValueError):
        asset_validator.validate_registered_art_styles(path, registry)
