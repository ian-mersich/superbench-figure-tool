"""A supplied correction cannot rewrite or inherit the old finite approval."""
from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from scripts import scientific_product_release as release

ROOT = Path(__file__).resolve().parents[1]


def test_current_correction_keeps_all_three_historical_decisions_exact():
    record = release._style_four_correction_record(ROOT)
    inventory, registry = release.style_four_correction_predecessor(ROOT, record)
    previous = release._validate_style_four(ROOT, required=True,
        inventory_override=inventory, registry_override=registry)
    assert previous["release_id"] == "user-supplied-style-4.2026-10-17"
    assert release._validate_baseline(ROOT, required=True,
        inventory_override=release.baseline_inventory(ROOT))["library"]["drawing_count"] == 406
    assert len(record["added_asset_files"]) == 249
    assert release.active_record_path(record) == release.STYLE_FOUR_CORRECTION_RECORD


def test_current_correction_has_only_its_actual_review_status():
    record = release._style_four_correction_record(ROOT)
    if record["decision"] == "pending_input_and_editor_review":
        assert release.validate(ROOT) is None
        with pytest.raises(ValueError, match="correction approval remains pending"):
            release.validate(ROOT, required=True)
    else:
        assert release.validate(ROOT, required=True) == record


def test_overlay_without_its_own_record_cannot_inherit_approval(tmp_path):
    manifest = tmp_path / release.STYLE_FOUR_CORRECTION_MANIFEST
    manifest.parent.mkdir(parents=True)
    manifest.write_text("{}", encoding="utf-8")
    assert release.validate(tmp_path) is None
    with pytest.raises(ValueError, match="correction product decision is missing"):
        release.validate(tmp_path, required=True)


def test_altered_correction_record_is_rejected(tmp_path):
    record = json.loads((ROOT / release.STYLE_FOUR_CORRECTION_RECORD).read_text(encoding="utf-8"))
    record["decision"] = "approved_without_review"
    path = tmp_path / release.STYLE_FOUR_CORRECTION_RECORD
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(record), encoding="utf-8")
    with pytest.raises(ValueError, match="decision exact identity mismatch"):
        release._style_four_correction_record(tmp_path)


@pytest.mark.parametrize("mutation", ["corrected_svg", "old_style_svg", "old_biology_svg", "unknown_file"])
def test_correction_does_not_mask_changed_or_unknown_artwork(monkeypatch, mutation):
    inventory = copy.deepcopy(release.asset_inventory(ROOT))
    if mutation == "unknown_file":
        inventory.append({"path": "assets/scientific-packs/unreviewed.svg", "sha256": "0" * 64})
        inventory.sort(key=lambda row: row["path"])
    else:
        prefix = {"corrected_svg": release.STYLE_FOUR_CORRECTION_PREFIX + "svg/",
                  "old_style_svg": release.STYLE_FOUR_PREFIX + "svg/",
                  "old_biology_svg": "assets/scientific-packs/core-biology/svg/"}[mutation]
        next(row for row in inventory if row["path"].startswith(prefix))["sha256"] = "0" * 64
    monkeypatch.setattr(release, "asset_inventory", lambda root: copy.deepcopy(inventory))
    with pytest.raises(ValueError, match="inventory mismatch"):
        release.validate(ROOT, required=True)


def test_correction_cannot_declare_an_old_file_as_a_new_addition():
    record = release._style_four_correction_record(ROOT)
    record["added_asset_files"].append({"path": release.STYLE_FOUR_MANIFEST, "sha256": "0" * 64})
    with pytest.raises(ValueError, match="outside this correction"):
        release.style_four_correction_predecessor(ROOT, record)


def test_bound_correction_still_needs_completed_reviews(monkeypatch):
    record = release._style_four_correction_record(ROOT)
    record["decision"] = "approved_for_matching_public_web_and_superbench_packages"
    record["review"]["native_editor_smoke"] = "pending"
    monkeypatch.setattr(release, "_style_four_correction_record", lambda root: copy.deepcopy(record))
    with pytest.raises(ValueError, match="completed input, independent visual and editor smoke reviews required"):
        release.validate(ROOT, required=True)
