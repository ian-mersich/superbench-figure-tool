"""Finite Library successor projection and pending release gate."""
from pathlib import Path
import importlib.util
import json
import sys
import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("scientific_product_release", ROOT / "scripts/scientific_product_release.py")
validator = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = validator
SPEC.loader.exec_module(validator)

def v5_inputs():
    """Exercise the unchanged v5 decision against its exact reconstructed input."""
    successor = ROOT / validator.ENDOCRINE_RECORD
    if successor.exists():
        return validator.endocrine_predecessor(ROOT, json.loads(successor.read_text(encoding="utf-8")))
    return (validator.asset_inventory(ROOT),
            json.loads((ROOT / "assets/scientific-packs/library.json").read_text(encoding="utf-8")),
            json.loads((ROOT / "assets/scientific-scenes/library.v1.json").read_text(encoding="utf-8")))

def test_successor_projects_exact_v4_registry_and_respects_approval_state():
    record = json.loads((ROOT / validator.LIBRARY_EXPANSION_RECORD).read_text(encoding="utf-8"))
    predecessor = validator._style_four_correction_record(ROOT)
    inventory, registry, scenes = v5_inputs()
    projected = validator.project_library_predecessor_registry(registry, record, predecessor)
    assert validator.canonical(projected) == predecessor["registry_sha256"]
    assert set(record["packs"]) == set(predecessor["packs"]) | {"neurobiology", "tissue-vascular"}
    assert set(record["scenes"]) == set(predecessor["scenes"]) | set(record["current"]["new_template_ids"]) | {"immunoblot-assay-workflow"}
    assert validator.active_record_path(record) == validator.LIBRARY_EXPANSION_RECORD
    approved = validator._validate_library_expansion(ROOT, required=False, inventory_override=inventory,
        registry_override=registry, scene_library_override=scenes)
    if approved is None:
        assert record["decision"] == "pending_native_editor_acceptance"
        with pytest.raises(ValueError, match="native editor and independent release acceptance remain pending"):
            validator._validate_library_expansion(ROOT, required=True, inventory_override=inventory,
                registry_override=registry, scene_library_override=scenes)
    else:
        assert record["decision"] == "approved_for_matching_public_web_and_superbench_packages"
        assert validator._validate_library_expansion(ROOT, required=True, inventory_override=inventory,
            registry_override=registry, scene_library_override=scenes) == approved

def test_predecessor_projection_rejects_an_unreviewed_extra_pack():
    record = json.loads((ROOT / validator.LIBRARY_EXPANSION_RECORD).read_text(encoding="utf-8"))
    predecessor = validator._style_four_correction_record(ROOT)
    _, registry, _ = v5_inputs()
    registry["packs"].append({"id": "unreviewed-extra"})
    with pytest.raises(ValueError, match="does not reconstruct the approved record"):
        validator.project_library_predecessor_registry(registry, record, predecessor)

def test_predecessor_projection_rejects_changed_historical_style_scope():
    record = json.loads((ROOT / validator.LIBRARY_EXPANSION_RECORD).read_text(encoding="utf-8"))
    predecessor = validator._style_four_correction_record(ROOT)
    _, registry, _ = v5_inputs()
    record["predecessor_registry_projection"]["restore_fields"]["art_style_notes"] += " altered"
    with pytest.raises(ValueError, match="does not reconstruct the approved record"):
        validator.project_library_predecessor_registry(registry, record, predecessor)
