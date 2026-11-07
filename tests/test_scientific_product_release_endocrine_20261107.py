"""The endocrine successor never extends approval to an unreviewed inventory."""
from pathlib import Path
import json

import pytest

from scripts import scientific_product_release as release
from scripts import figure_tool_package_producer as producer

ROOT = Path(__file__).resolve().parents[1]


def record():
    return json.loads((ROOT / release.ENDOCRINE_RECORD).read_text(encoding="utf-8"))


def replace_json(monkeypatch, relative, value):
    original = Path.read_text
    target = ROOT / relative
    def read(path, *args, **kwargs):
        return json.dumps(value) if path == target else original(path, *args, **kwargs)
    monkeypatch.setattr(Path, "read_text", read)


def bound_record(monkeypatch, value):
    # A synthetic decision identity lets negative controls reach policy checks.
    replace_json(monkeypatch, release.ENDOCRINE_RECORD, value)
    monkeypatch.setattr(release, "ENDOCRINE_RECORD_SHA256", release.canonical(value))


def test_exact_endocrine_successor_reconstructs_and_validates_approved_v5():
    approved = release.validate(ROOT, required=True)
    assert release.active_record_path(approved) == release.ENDOCRINE_RECORD
    inventory, registry, scenes = release.endocrine_predecessor(ROOT, approved)
    prior = release._validate_library_expansion(ROOT, required=True, inventory_override=inventory,
        registry_override=registry, scene_library_override=scenes)
    assert len(inventory) == 1513
    assert release.canonical(inventory) == prior["current"]["asset_inventory_sha256"]
    assert len(approved["added_asset_files"]) == 63
    assert approved["packs"].keys() == prior["packs"].keys() | {"endocrine-tissue"}
    assert approved["scenes"].keys() == prior["scenes"].keys() | release.ENDOCRINE_TEMPLATE_IDS
    assert producer.validate_scene_release(ROOT / "assets/scientific-scenes", distribution_scope="public-release")["pending_scene_ids"] == []


@pytest.mark.parametrize("group", ["new_art", "old_art", "old_grant", "new_rights", "template", "style4", "extra_file", "missing_file"])
def test_exact_inventory_rejects_old_and_new_mutations(monkeypatch, group):
    inventory = release.asset_inventory(ROOT)
    prefixes = dict(new_art="assets/scientific-packs/endocrine-tissue/svg/",
        old_art="assets/scientific-packs/core-biology/svg/",
        old_grant="assets/scientific-packs/rna-methods/rights-release-record.json",
        new_rights="assets/scientific-packs/endocrine-tissue/rights-release-record.json",
        template="assets/scientific-scenes/scenes/hypothalamic-pituitary-thyroid-axis.scene.json",
        style4="assets/scientific-packs/style-4/expansion-20261107/svg/")
    if group == "extra_file":
        inventory.append(dict(path="assets/scientific-packs/unreviewed.svg", sha256="0" * 64))
        inventory.sort(key=lambda row: row["path"])
    elif group == "missing_file":
        inventory = [row for row in inventory if row["path"] != release.ENDOCRINE_AGGREGATE]
    else:
        next(row for row in inventory if row["path"].startswith(prefixes[group]))["sha256"] = "0" * 64
    monkeypatch.setattr(release, "asset_inventory", lambda root: inventory)
    with pytest.raises(ValueError):
        release.validate(ROOT, required=True)


@pytest.mark.parametrize("mutation", ["predecessor", "old_pack", "old_scene", "duplicate", "unsafe", "counts", "review", "attestation"])
def test_bound_decision_still_rejects_changed_scope_or_incomplete_acceptance(monkeypatch, mutation):
    value = record()
    if mutation == "predecessor": value["predecessor"]["sha256"] = "0" * 64
    elif mutation == "old_pack": value["packs"]["rna-methods"]["catalog_sha256"] = "0" * 64
    elif mutation == "old_scene": value["scenes"]["single-cell-rna-workflow"]["scene_sha256"] = "0" * 64
    elif mutation == "duplicate": value["added_asset_files"].append(value["added_asset_files"][0])
    elif mutation == "unsafe": value["added_asset_files"][0]["path"] = "assets/scientific-packs/endocrine-tissue/../secret.svg"
    elif mutation == "counts": value["current"]["library"]["drawing_count"] += 1
    elif mutation == "review": value["review"]["native_editor_acceptance"] = "pending"
    else: value["user_authorization"]["new_personal_attestation"] = True
    bound_record(monkeypatch, value)
    with pytest.raises(ValueError):
        release.validate(ROOT, required=True)


@pytest.mark.parametrize("relative,field", [("assets/scientific-packs/library.json", "packs"),
                                           ("assets/scientific-scenes/library.v1.json", "scenes")])
def test_predecessor_projection_does_not_erase_an_unknown_pack_or_scene(monkeypatch, relative, field):
    value = json.loads((ROOT / relative).read_text(encoding="utf-8"))
    value[field].append({"id": "unreviewed-extra"})
    replace_json(monkeypatch, relative, value)
    with pytest.raises(ValueError, match="predecessor cannot be reconstructed"):
        release.validate(ROOT, required=True)


def test_pending_scoped_decision_remains_blocked_for_public_admission(monkeypatch):
    value = record(); value["decision"] = "pending_native_editor_acceptance"
    bound_record(monkeypatch, value)
    assert release.validate(ROOT) is None
    with pytest.raises(ValueError, match="acceptance remain pending"):
        release.validate(ROOT, required=True)
    with pytest.raises(producer.ReleaseBuildError, match="pending scene product release approval"):
        producer.validate_scene_release(ROOT / "assets/scientific-scenes", distribution_scope="public-release")


def test_missing_successor_cannot_inherit_v5_approval(monkeypatch):
    original = Path.exists
    monkeypatch.setattr(Path, "exists", lambda path: False if path == ROOT / release.ENDOCRINE_RECORD else original(path))
    assert release.validate(ROOT) is None
    with pytest.raises(ValueError, match="decision is missing"):
        release.validate(ROOT, required=True)


def test_historical_record_mutation_is_rejected_even_with_current_endocrine_inventory(monkeypatch):
    value = json.loads((ROOT / release.LIBRARY_EXPANSION_RECORD).read_text(encoding="utf-8"))
    value["decision"] = "pending_native_editor_acceptance"
    replace_json(monkeypatch, release.LIBRARY_EXPANSION_RECORD, value)
    with pytest.raises(ValueError, match="exact decision identity mismatch"):
        release.validate(ROOT, required=True)
