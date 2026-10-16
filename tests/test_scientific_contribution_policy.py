"""The finite new CC0 contribution never inherits old attestations or product approval."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import shutil
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("contribution_asset_validator", ROOT / "scripts/validate-scientific-assets.py")
validator = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = validator
SPEC.loader.exec_module(validator)
COUNTS = {"cell-structure-stress": (40, 20), "tumor-microenvironment": (20, 10), "analysis-graphics": (20, 10)}
POLICY = "original-vectors.cc0.repository-policy.2026-10-15"
REVIEW = "independent_scientific_and_visual_review_passed_2026_10_15"


def read(path):
    return json.loads(path.read_text(encoding="utf8"))


@pytest.mark.parametrize("pack_id,counts", COUNTS.items())
def test_original_drawings_have_current_policy_and_separate_reviewed_artwork(pack_id, counts):
    path = ROOT / "assets/scientific-packs" / pack_id / "asset-pack.json"
    pack = read(path)
    audit = read(path.parent / pack["release_audit"]["file"])
    assert validator.validate_pack(path) == (pack_id, counts[0], "rights_cleared_quality_pending")
    assert (pack["asset_count"], pack["concept_count"]) == counts
    assert pack["contribution_license_policy"] == POLICY
    assert pack["qa_status"] == REVIEW
    assert pack["rights_records"] == audit["rights_records"]
    assert pack["source_records"] == audit["source_records"]
    rights = pack["rights_records"][0]
    assert rights["kind"] == "repository_policy_license"
    assert rights["rights_basis"] == "repository_policy_original_output"
    assert rights["effective_date"] == "2026-10-15"
    for ref in (pack["release_audit"], audit):
        assert ref["release_effective_date"] is None
        assert ref["product_release_status"] == "pending_quality_and_product_review"
    for asset in pack["assets"]:
        assert asset["review_status"] == REVIEW
        assert asset["quality_tier"] == "reviewed"
        assert asset["mvp_quality"] == "reviewed_original_vector"
        assert asset["source_type"] == "clean_room_original_vector"
        assert asset["license"] == "CC0-1.0"
        assert asset["rights_record_id"] == rights["id"]


def test_prospective_terms_are_mirrored_and_preserve_previous_scope_notice():
    for relative in ("LICENSE_POLICY.md", "assets/LICENSE-CELL-STRESS-TME-ANALYSIS-CC0-1.0.md",
                     "assets/LICENSE-ORIGINAL-ASSETS-CC0-1.0.md", "assets/CC0-1.0.txt"):
        assert (ROOT / relative).read_bytes() == (ROOT / "app/legal" / relative).read_bytes()
    current = (ROOT / "assets/LICENSE-CELL-STRESS-TME-ANALYSIS-CC0-1.0.md").read_text(encoding="utf8")
    assert POLICY in current and "2026-10-15" in current
    assert all(pack_id in current for pack_id in COUNTS)
    assert "neither copies\nnor extends" in current
    assert "remain pending" in current


def mutate(case, pack, audit, base):
    rights = pack["rights_records"][0]
    if case == "missing_policy":
        del pack["contribution_license_policy"]
    elif case == "unknown_policy":
        pack["contribution_license_policy"] = "original-vectors.future-unknown"
    elif case == "owner_attestation":
        rights["kind"] = "owner_license_grant"
    elif case == "old_rights_basis":
        rights["rights_basis"] = "owner_attested_original_output"
    elif case == "old_grant_date":
        rights["effective_date"] = "2026-10-10"
    elif case == "public_integer":
        rights["public_distribution_authorized"] = 1
    elif case == "unscoped_rights":
        rights["scope"] = "all_future_original_assets"
    elif case == "third_party_material":
        rights["third_party_material"] = "copied_artwork"
    elif case == "audit_old_date":
        audit["rights_grant_effective_date"] = "2026-10-10"
    elif case == "audit_earlier_date":
        audit["audit_date"] = "2026-10-14"
    elif case == "product_approved":
        audit["product_release_status"] = pack["release_audit"]["product_release_status"] = "released"
    elif case == "product_date":
        audit["release_effective_date"] = pack["release_audit"]["release_effective_date"] = "2026-10-15"
    elif case == "product_status":
        audit["status"] = pack["release_audit"]["status"] = "released"
    elif case == "empty_product_pending_reason":
        audit["product_release_blocker"] = ""
    elif case == "hidden_product_approval":
        audit["product_release"] = {"status": "approved"}
    elif case == "non_original_source":
        pack["assets"][0]["source_type"] = "copied_vector"
    elif case == "historical_audit_basis":
        audit["rights_basis"]["status"] = "owner_attested_original_output"
    elif case == "historical_provenance":
        audit["assets"][0]["provenance_status"] = "owner_attested"
    elif case == "premature_disposition":
        audit["assets"][0]["release_disposition"] = "released_under_cc0_1_0"
    elif case == "svg_identity_drift":
        svg = base / pack["assets"][0]["file"]
        svg.write_bytes(svg.read_bytes() + b"\n<!-- changed after independent review -->\n")
    elif case == "different_audit_rights_record":
        audit["rights_records"][0]["statement"] += " This differs from the catalog record."
    else:
        raise AssertionError(case)


@pytest.mark.parametrize("case,message", [
    ("missing_policy", "requires its repository license policy"),
    ("unknown_policy", "out-of-scope repository-policy"),
    ("owner_attestation", "rights record kind"),
    ("old_rights_basis", "rights record rights_basis"),
    ("old_grant_date", "rights record effective_date"),
    ("public_integer", "rights record public_distribution_authorized"),
    ("unscoped_rights", "rights record scope"),
    ("third_party_material", "rights record third_party_material"),
    ("audit_old_date", "current 2026-10-15 date"),
    ("audit_earlier_date", "current 2026-10-15 date"),
    ("product_approved", "separate pending product approval"),
    ("product_date", "separate pending product approval"),
    ("product_status", "separate pending product approval"),
    ("empty_product_pending_reason", "separate pending product qualification"),
    ("hidden_product_approval", "separate pending product qualification"),
    ("non_original_source", "only its newly constructed original vectors"),
    ("historical_audit_basis", "rights_basis must record repository_policy_original_output"),
    ("historical_provenance", "provenance_status must be original_construction_recorded"),
    ("premature_disposition", "licensed_under_cc0_1_0_product_release_pending"),
    ("svg_identity_drift", "exact-identity mismatch set"),
    ("different_audit_rights_record", "rights record content does not match"),
])
def test_prospective_contribution_rejects_false_scope_attestation_and_product_approval(tmp_path, case, message):
    source = ROOT / "assets/scientific-packs/analysis-graphics"
    base = tmp_path / "analysis-graphics"
    shutil.copytree(source, base)
    pack_path = base / "asset-pack.json"
    audit_path = base / "rights-release-record.json"
    pack, audit = read(pack_path), read(audit_path)
    mutate(case, pack, audit, base)
    pack_path.write_text(json.dumps(pack, ensure_ascii=False), encoding="utf8")
    audit_path.write_text(json.dumps(audit, ensure_ascii=False), encoding="utf8")
    with pytest.raises(ValueError, match=message):
        validator.validate_pack(pack_path)
