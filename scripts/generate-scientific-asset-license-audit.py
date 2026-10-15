#!/usr/bin/env python3
"""Generate a deterministic scientific-pack provenance/license-release audit.

The historical Core Biology evidence remains immutable.  New packs provide
their own audit identity, dates, source records, and rights records in pack
metadata; this generator never extends the Core Biology audit to new assets.
"""

from __future__ import annotations

import argparse
from datetime import date
import hashlib
import importlib.util
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PACK = REPO_ROOT / "assets" / "scientific-packs" / "core-biology" / "asset-pack.json"
CORE_PACK_ID = "core-biology"
PROTEIN_PACK_ID = "protein-homeostasis"


def qualified_protein_release_validator():
    """Use the source validator's finite, pinned product-qualification branch."""
    name = "figure_asset_product_release_validator"
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, REPO_ROOT / "scripts/validate-scientific-assets.py")
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    return sys.modules[name]

SOURCE_RECORDS = [
    {
        "id": "owner-attestation-2026-07-19",
        "kind": "owner_attestation",
        "scope": "all_assets",
        "statement": "The workspace owner states that every production asset in the Core Biology pack was produced in this Figure Studio/Codex workspace.",
    },
    {
        "id": "owner-cc0-selection-2026-07-19",
        "kind": "owner_license_selection",
        "scope": "all_assets",
        "statement": "The workspace owner explicitly selected CC0 for maximum-frictionless reuse of the Core Biology production asset pack.",
        "selected_license": "CC0-1.0",
        "effective_date": "2026-07-19",
    },
    {
        "id": "rel-asset-01-independent-exact-identity-review-2026-07-22",
        "kind": "independent_engineering_visual_provenance_review",
        "scope": "exact_asset_ids",
        "asset_ids": [
            "core.protein.kinase",
            "core.protein.transcription_factor",
            "core.protein.enzyme",
            "core.ligand.generic",
            "core.antibody.drug_conjugate",
            "core.rna.strand",
            "core.mrna.transcript",
            "core.rna.sirna",
            "core.gene.promoter",
            "core.symbol.transcription_flow",
            "core.dna.protein_binding",
            "core.symbol.dashed_arrow",
            "core.symbol.bidirectional_arrow",
            "core.symbol.secretion_arrow",
            "core.symbol.translocation_arrow",
            "core.symbol.phosphorylation",
            "core.symbol.cleavage",
            "core.symbol.drug_inhibition_badge",
            "core.symbol.interaction_cue",
            "core.lab.microcentrifuge_tube",
            "core.lab.conical_tube",
            "core.lab.syringe",
            "core.lab.microscope",
            "core.lab.tissue_culture_flask",
            "core.lab.plate_96_well",
            "core.lab.plate_reader",
        ],
        "reviewer": "/root/core_biology_independent_review",
        "reviewed_on": "2026-07-22",
        "accepted_count": 26,
        "rejected_count": 0,
        "evidence": "docs/release/assets/REL-ASSET-01/CORE_BIOLOGY_INDEPENDENT_REVIEW.md",
        "statement": "An independent reviewer accepted the 26 exact current SVG identities for biological legibility, self-contained vector structure, and continuity with the existing owner-attested workspace-output scope. This engineering review does not establish legal ownership, non-infringement, or authority to make the CC0 dedication.",
    },
    {
        "id": "model-organism-promotion-review-2026-07-20",
        "kind": "production_promotion_review",
        "scope": "model_organism_batch_1",
        "statement": "Five original Figure Studio/Codex model-organism vectors were reviewed and promoted into the owner-selected CC0 production pack.",
        "asset_ids": [
            "core.model.yeast_budding",
            "core.model.bacterium_rod",
            "core.model.zebrafish",
            "core.model.fruit_fly",
            "core.model.nematode",
        ],
        "effective_date": "2026-07-20",
    },
    {
        "id": "openai-terms-output-ownership-2026-01-01",
        "kind": "terms_reference",
        "scope": "openai_output",
        "url": "https://openai.com/policies/terms-of-use/",
        "section": "Content — Ownership of content",
        "note": "As between the user and OpenAI, and to the extent permitted by applicable law, the user owns Output and OpenAI assigns its interest, if any, in Output.",
    },
    {
        "id": "openai-services-agreement-output-ownership-2026-01-01",
        "kind": "terms_reference",
        "scope": "openai_business_output",
        "url": "https://openai.com/policies/services-agreement/",
        "section": "4.1 Customer Content — Generally",
        "note": "For business/API use, as between the customer and OpenAI and to the extent permitted by applicable law, the customer owns Output and OpenAI assigns its interest, if any, in Output.",
    },
    {
        "id": "owner-figure-abstract-source-01",
        "kind": "owner_workspace_source_hash",
        "scope": "owner_workspace_redraws",
        "format": "Adobe Illustrator document",
        "local_path_redacted": True,
        "byte_length": 602950,
        "sha256": "b66abbb26db4e0123ec7a01309ab385133b2778a90b00f220103e97d6f7da56c",
    },
    {
        "id": "owner-figure-abstract-source-02",
        "kind": "owner_workspace_source_hash",
        "scope": "owner_workspace_redraws",
        "format": "Adobe Illustrator document",
        "local_path_redacted": True,
        "byte_length": 570983,
        "sha256": "fa418822fd35f9ea0faacbe0a2a38814c8662b0735bb2e4ffd34f4e1d207a66e",
    },
]

LICENSE_CANDIDATES = [
    {
        "id": "CC0-1.0",
        "label": "CC0 1.0 Universal",
        "canonical_url": "https://creativecommons.org/publicdomain/zero/1.0/",
        "attribution_required": False,
        "owner_action_required": True,
        "effect": "Permanent public-domain dedication where possible, with an irrevocable permissive-license fallback.",
    },
    {
        "id": "CC-BY-4.0",
        "label": "Creative Commons Attribution 4.0 International",
        "canonical_url": "https://creativecommons.org/licenses/by/4.0/",
        "attribution_required": True,
        "owner_action_required": True,
        "effect": "Irrevocable worldwide permission to reuse and adapt with attribution and modification notice requirements.",
    },
    {
        "id": "BSD-STUDIO-ASSET-USE-1.0-PROPOSED",
        "label": "BSD Studio Asset Use License (proposed; text not yet approved)",
        "canonical_url": None,
        "attribution_required": None,
        "owner_action_required": True,
        "status": "requires_license_text_and_legal_review",
        "effect": "Could permit end-user use and modification in exported scientific figures while reserving separately defined restrictions on standalone asset-pack redistribution.",
    },
]


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_text(value: str) -> str:
    return sha256_bytes(value.encode("utf-8"))


def lineage_for(source_type: str) -> str:
    return {
        "original_vector_draft": "workspace_generated_original",
        "original_vector_redraw": "workspace_generated_companion_or_redraw",
        "clean_room_original_vector": "workspace_generated_clean_room_original",
        "owner_workspace_original_vector_redraw": "workspace_output_redraw_from_owner_figure",
    }.get(source_type, "unclassified")


def load_pack(pack_path: Path) -> dict:
    pack = json.loads(pack_path.read_text(encoding="utf-8"))
    if not isinstance(pack, dict):
        raise ValueError("asset-pack.json must contain a JSON object")
    return pack


def require_new_pack_release_authorization(pack: dict, release_reference: dict, pack_dir: Path | None = None) -> None:
    pack_id = pack.get("id")
    rights_records = pack.get("rights_records")
    source_records = pack.get("source_records")
    if not isinstance(rights_records, list) or not rights_records:
        raise ValueError("New packs require an explicit rights_records release authorization")
    if not isinstance(source_records, list) or not source_records:
        raise ValueError("New packs require an explicit source_records generation record")
    rights_by_id = {
        record.get("id"): record for record in rights_records if isinstance(record, dict)
    }
    source_by_id = {
        record.get("id"): record for record in source_records if isinstance(record, dict)
    }
    referenced_rights = {
        asset.get("rights_record_id")
        for asset in pack.get("assets", [])
        if isinstance(asset, dict)
    }
    referenced_sources = {
        asset.get("source_record_id")
        for asset in pack.get("assets", [])
        if isinstance(asset, dict)
    }
    qualified_product = pack_id == PROTEIN_PACK_ID and release_reference.get("status") == "released"
    if len(referenced_rights) != 1 or referenced_rights - rights_by_id.keys():
        raise ValueError("Every new-pack asset must reference one declared rights authorization")
    if not qualified_product and (len(referenced_sources) != 1 or referenced_sources - source_by_id.keys()):
        raise ValueError("Every new-pack asset must reference one declared source record")
    rights = rights_by_id[next(iter(referenced_rights))]
    if qualified_product:
        if pack_dir is None:
            raise ValueError("Qualified Protein release requires its exact source-pack directory")
        validator = qualified_protein_release_validator()
        validator.validate_protein_product_release(pack, pack_dir)
        source = source_by_id[validator.PROTEIN_SOURCE_RECORD_ID]
    elif "product_release_receipt" in pack:
        raise ValueError("Unknown scientific product-release receipt requires a reviewed implementation")
    else:
        source = source_by_id[next(iter(referenced_sources))]
    required_rights = {
        "kind": "owner_release_authorization",
        "pack_id": pack_id,
        "scope": "all_assets_in_pack",
        "status": "released",
        "public_distribution_authorized": True,
        "selected_public_license": "CC0-1.0",
        "rights_basis": "owner_attested_original_output",
        "third_party_material": "none_declared",
        "effective_date": release_reference.get("release_effective_date"),
    }
    if qualified_product:
        required_rights.update({
            "kind": "owner_license_grant", "status": "rights_cleared",
            "effective_date": "2026-10-10",
        })
    for key, expected in required_rights.items():
        if rights.get(key) != expected:
            raise ValueError(
                f"New-pack rights authorization {key} must be {expected!r}; "
                f"found {rights.get(key)!r}"
            )
    for field in ("statement", "qualification"):
        if not isinstance(rights.get(field), str) or len(rights[field].strip()) < 40:
            raise ValueError(f"New-pack rights authorization {field} must be substantive")
    required_source = {
        "kind": "clean_room_generation_record",
        "pack_id": pack_id,
        "scope": "all_assets_in_pack",
        "third_party_material": "none_declared",
    }
    for key, expected in required_source.items():
        if source.get(key) != expected:
            raise ValueError(
                f"New-pack source record {key} must be {expected!r}; found {source.get(key)!r}"
            )
    if not isinstance(source.get("statement"), str) or len(source["statement"].strip()) < 40:
        raise ValueError("New-pack source record statement must be substantive")
    if qualified_product:
        # The source was created before later product qualification. Its exact
        # historical record is verified above rather than rewritten to a new date.
        if date.fromisoformat(source["created_on"]) > date.fromisoformat(release_reference["audit_date"]):
            raise ValueError("Qualified source created_on cannot be later than release audit_date")
    elif source.get("created_on") != release_reference.get("audit_date"):
        raise ValueError("New-pack source record created_on must match release audit_date")
    required_reference = {
        "status": "released",
        "public_distribution_authorized": True,
        "selected_public_license": "CC0-1.0",
        "asset_count": len(pack.get("assets", [])),
        "concept_count": len(
            {
                str(asset.get("concept_id") or asset.get("id"))
                for asset in pack.get("assets", [])
                if isinstance(asset, dict)
            }
        ),
    }
    for key, expected in required_reference.items():
        if release_reference.get(key) != expected:
            raise ValueError(
                f"New-pack release_audit.{key} must match the explicit authorization and catalog"
            )


def build_audit(pack_path: Path) -> dict:
    pack = load_pack(pack_path)
    pack_dir = pack_path.parent
    release_reference = pack.get("release_audit")
    if not isinstance(release_reference, dict):
        raise ValueError("Pack release_audit must be an object")
    audit_id = release_reference.get("audit_id")
    audit_date = release_reference.get("audit_date")
    release_effective_date = release_reference.get("release_effective_date") or audit_date
    if not isinstance(audit_id, str) or not audit_id.startswith(f"{pack['id']}."):
        raise ValueError("Pack release_audit.audit_id must be scoped to the pack id")
    if not isinstance(audit_date, str):
        if pack.get("id") == CORE_PACK_ID:
            audit_date = "2026-07-20"
            release_effective_date = "2026-07-20"
        else:
            raise ValueError("New packs must declare release_audit.audit_date")

    if pack.get("id") == CORE_PACK_ID:
        source_records = [*SOURCE_RECORDS, *pack.get("source_records", [])]
        rights_records = []
        license_candidates = LICENSE_CANDIDATES
    else:
        source_records = pack.get("source_records")
        rights_records = pack.get("rights_records")
        if not isinstance(source_records, list) or not source_records:
            raise ValueError("New packs must declare non-empty source_records")
        if not isinstance(rights_records, list) or not rights_records:
            raise ValueError("New packs must declare non-empty rights_records")
        require_new_pack_release_authorization(pack, release_reference, pack_dir)
        license_candidates = release_reference.get("license_candidates") or [
            {
                "id": release_reference.get("selected_public_license"),
                "label": "Selected public asset license",
                "owner_action_required": True,
            }
        ]

    assets = []
    for asset in pack.get("assets", []):
        svg_path = pack_dir / asset["file"]
        # SVG audit identity is text-based and stable across LF/CRLF checkouts.
        svg_bytes = svg_path.read_bytes().replace(b"\r\n", b"\n")
        per_asset_rights_basis = (
            "owner_attested_openai_output"
            if pack.get("id") == CORE_PACK_ID
            else "owner_attested_original_output"
        )
        entry = {
            "asset_id": asset["id"],
            "file": asset["file"],
            "sha256": sha256_bytes(svg_bytes),
            "provenance_sha256": sha256_text(asset["provenance"]),
            "source_type": asset["source_type"],
            "lineage": lineage_for(asset["source_type"]),
            "current_license": asset["license"],
            "rights_basis": per_asset_rights_basis,
            "third_party_material": "none_declared",
            "provenance_status": "owner_attested",
            "release_disposition": "released_under_cc0_1_0",
        }
        if pack.get("id") != CORE_PACK_ID:
            entry["source_record_id"] = asset.get("source_record_id")
            entry["rights_record_id"] = asset.get("rights_record_id")
        assets.append(entry)

    unclassified = [entry["asset_id"] for entry in assets if entry["lineage"] == "unclassified"]
    if unclassified:
        raise ValueError(f"Unclassified source_type for: {', '.join(unclassified)}")
    non_cc0 = [entry["asset_id"] for entry in assets if entry["current_license"] != "CC0-1.0"]
    if non_cc0:
        raise ValueError(f"CC0 release contains non-CC0 asset licenses: {', '.join(non_cc0)}")

    result = {
        "schema_id": "figureStudio.scientificAssetLicenseReleaseAudit.v1",
        "audit_id": audit_id,
        "audit_date": audit_date,
        "pack_id": pack["id"],
        "status": "released",
        "release_effective_date": release_effective_date,
        "asset_count": len(assets),
        "rights_cleared_count": len(assets),
        "third_party_component_count": 0,
        "license_selection_pending_count": 0,
        "public_distribution_authorized": True,
        "selected_public_license": "CC0-1.0",
        "license_notice": release_reference.get("license_notice"),
        "rights_basis": {
            "status": "owner_attested_original_output",
            "scope": "all_assets" if pack.get("id") == CORE_PACK_ID else "all_assets_in_pack",
            "qualification": (
                "Ownership references describe rights as between the owner/customer and OpenAI and to the extent permitted by applicable law; output may not be unique and the references do not provide a non-infringement warranty."
                if pack.get("id") == CORE_PACK_ID
                else rights_records[0]["qualification"]
            ),
        },
        "source_records": source_records,
        "license_candidates": [
            {**candidate, "selected": candidate["id"] == "CC0-1.0"}
            for candidate in license_candidates
        ],
        "release_blocker": None,
        "assets": assets,
    }
    if pack.get("id") != CORE_PACK_ID:
        result["concept_count"] = len(
            {str(asset.get("concept_id") or asset["id"]) for asset in pack.get("assets", [])}
        )
        result["rights_basis"]["pack_id"] = pack["id"]
        result["rights_basis"]["authorization_record_id"] = rights_records[0]["id"]
        result["rights_records"] = rights_records
        if pack["id"] == PROTEIN_PACK_ID:
            validator = qualified_protein_release_validator()
            receipt = json.loads((pack_dir / pack["product_release_receipt"]).read_text(encoding="utf-8"))
            result["rights_grant_effective_date"] = "2026-10-10"
            result["product_release_status"] = "released"
            result["supersedes_audit_id"] = validator.PROTEIN_PREDECESSOR_AUDIT_ID
            result["product_release"] = validator.protein_product_release_audit_binding(receipt)
    elif pack.get("revision") in {"2026-10-11-nucleic-acid-redraw", "2026-10-11-rna-redraw", "2026-10-13-broad-library"}:
        # Carry the original rights/source records forward. Each separately pinned
        # receipt binds a bounded redraw set to its exact approved predecessor.
        expected_receipt = {
            "2026-10-11-nucleic-acid-redraw": "revision-2026-10-11.json",
            "2026-10-11-rna-redraw": "revision-2026-10-11-rna.json",
            "2026-10-13-broad-library": "revision-2026-10-13-broad-library.json",
        }[pack["revision"]]
        if pack.get("revision_receipt") != expected_receipt:
            raise ValueError("Core Biology revision must use its exact reviewed receipt path")
        receipt = json.loads((pack_dir / pack["revision_receipt"]).read_text(encoding="utf-8"))
        result["asset_revision"] = {
            "revision_id": pack["revision"],
            "receipt": pack["revision_receipt"],
            "receipt_sha256": sha256_text(json.dumps(receipt, sort_keys=True, separators=(",", ":"), ensure_ascii=False)),
            "predecessor": receipt["predecessor"],
            "changed_asset_ids": [entry["asset_id"] for entry in receipt["changed_assets"]],
        }
        if pack["revision"] == "2026-10-13-broad-library":
            result["asset_revision"]["added_asset_ids"] = [entry["asset_id"] for entry in receipt["added_assets"]]
    elif pack.get("id") == CORE_PACK_ID and pack.get("revision") is not None:
        raise ValueError("Unknown Core Biology revision requires an explicit reviewed generator implementation")
    return result


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a scientific-pack provenance/license-release audit.")
    parser.add_argument("--pack", type=Path, default=DEFAULT_PACK, help="Path to asset-pack.json")
    parser.add_argument(
        "--output",
        type=Path,
        help="Audit JSON output path. Defaults to the pack release_audit.file.",
    )
    parser.add_argument("--check", action="store_true", help="Fail if the existing audit differs from generated output")
    return parser.parse_args(argv)


def main() -> int:
    args = parse_args(sys.argv[1:])
    pack_path = args.pack.resolve()
    pack = load_pack(pack_path)
    if args.output is not None:
        output_path = args.output.resolve()
    else:
        output_path = (pack_path.parent / str(pack["release_audit"]["file"])).resolve()
    audit = build_audit(pack_path)
    rendered = json.dumps(audit, indent=2, ensure_ascii=False) + "\n"
    if args.check:
        if not output_path.exists():
            print(f"License-release audit is missing: {output_path}", file=sys.stderr)
            return 1
        if output_path.read_text(encoding="utf-8") != rendered:
            print(f"License-release audit is stale: {output_path}", file=sys.stderr)
            return 1
        print(
            f"License-release audit is current for {audit['asset_count']} assets; "
            f"status={audit['status']}."
        )
        return 0

    if audit["pack_id"] == CORE_PACK_ID:
        if output_path.exists() and output_path.read_text(encoding="utf-8") == rendered:
            print(
                "The historical Core Biology audit is immutable and already current; "
                "no file was rewritten."
            )
            return 0
        print(
            "The historical Core Biology audit is immutable and differs from generated content; "
            "restore the released pack instead of rewriting its evidence.",
            file=sys.stderr,
        )
        return 2

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(rendered, encoding="utf-8", newline="\n")
    print(
        f"Wrote {output_path} for {audit['asset_count']} assets; "
        f"status={audit['status']}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
