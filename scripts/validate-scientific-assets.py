#!/usr/bin/env python3
"""Validate Figure Tool scientific asset packs and the installed library.

Pack validation retains the exact historical Core Biology release and supports
explicitly pinned revisions. Library validation adds registry, cross-pack identity, search-term,
rights-record, and exact-vector duplicate checks for independently released
packs.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from datetime import date
import hashlib
import importlib.util
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path, PurePosixPath


REPO_ROOT = Path(__file__).resolve().parents[1]
PACKS_ROOT = REPO_ROOT / "assets" / "scientific-packs"
DEFAULT_PACK = PACKS_ROOT / "core-biology" / "asset-pack.json"
DEFAULT_LIBRARY = PACKS_ROOT / "library.json"
CORE_PACK_ID = "core-biology"
EXPANSION_PACK_ID = "core-experimental-biology"
IMMUNOLOGY_ONCOLOGY_PACK_ID = "immunology-oncology"
CORE_ASSET_COUNT = 108
EXPANSION_ASSET_COUNT = 111
EXPANSION_CONCEPT_COUNT = 103
CORE_AUDIT_ID = "core-biology.provenance-license-release.2026-07-20"
CORE_AUDIT_DATE = "2026-07-20"
CORE_CATALOG_SHA256 = "f1c3ba520939b1a204ff528d702a71571ae1256d5c0206f793d107893487b9bc"
CORE_AUDIT_SHA256 = "0248f1092c1f476aa7d69b0f9cd45baa5f96785f5b82b1c61aca804cab94dcd7"
CORE_NUCLEIC_REVISION = "2026-10-11-nucleic-acid-redraw"
CORE_NUCLEIC_AUDIT_ID = "core-biology.provenance-license-release.2026-10-11.nucleic-acid-redraw"
CORE_NUCLEIC_DATE = "2026-10-11"
# Each approved revision has its own exact identity; dates and hash sets cannot
# be mixed. These pins are updated only after the bounded revision is reviewed.
CORE_NUCLEIC_CATALOG_SHA256 = "14fedf450572c49a5aca903ee9e505dc87407dfd9c900e32eaf013c736e8a725"
CORE_NUCLEIC_AUDIT_SHA256 = "669a9ddfcfd46d9086b3320fd1015ff80f6646f8e71bb4cd3c051241f32196e6"
CORE_NUCLEIC_RECEIPT_SHA256 = "1245db83903e47dd5e5b6aba1b6d161fe56c1fb398720ced0b44aa3b86055073"
CORE_LICENSE_SHA256 = "2920cc0c3a5986b9b4c3dbab144d6e421a4f572a8140c4fbf3596afd783887e6"
CORE_PREDECESSOR_PREFIX = "revisions/2026-07-20"
CORE_REVISION_RECEIPT = "revision-2026-10-11.json"
CORE_REDRAW_FILES = {
    "core.dna.double_helix": "svg/dna_double_helix.svg",
    "core.dna.double_helix_manuscript": "svg/dna_double_helix_manuscript.svg",
    "core.chromatin.loop": "svg/chromatin_loop.svg",
}
CORE_PREDECESSOR_FILES = {
    f"{CORE_PREDECESSOR_PREFIX}/{name}"
    for name in ("asset-pack.json", "license-release-audit.json", "LICENSE-ASSETS-CC0-1.0.md", *CORE_REDRAW_FILES.values())
}
CORE_RNA_REVISION = "2026-10-11-rna-redraw"
CORE_RNA_AUDIT_ID = "core-biology.provenance-license-release.2026-10-11.rna-redraw"
CORE_RNA_DATE = "2026-10-11"
CORE_RNA_CATALOG_SHA256 = "a941c12a4955d55854832328f612d3190d59f57ab86f58388efaec6416cf5cc1"
CORE_RNA_AUDIT_SHA256 = "19e75365f22c683d4112e83646f4cd4aae928ca91ab097487dfaabe2a1f17a05"
CORE_RNA_RECEIPT_SHA256 = "f4d3ac0423b230f33535003cf95392fa30b5c1f69745c61c7ac6cebb495e0e9b"
CORE_RNA_PREDECESSOR_PREFIX = "revisions/2026-10-11-nucleic-acid-redraw"
CORE_RNA_REVISION_RECEIPT = "revision-2026-10-11-rna.json"
CORE_RNA_REDRAW_FILES = {
    "core.rna.strand": "svg/rna_strand.svg",
    "core.rna.strand_linear": "svg/rna_strand_linear.svg",
    "core.mrna.transcript": "svg/mrna_transcript.svg",
    "core.rna.sirna": "svg/sirna_duplex.svg",
}
CORE_RNA_PREDECESSOR_FILES = {
    f"{CORE_RNA_PREDECESSOR_PREFIX}/{name}"
    for name in ("asset-pack.json", "license-release-audit.json", "LICENSE-ASSETS-CC0-1.0.md",
                 CORE_REVISION_RECEIPT, *CORE_RNA_REDRAW_FILES.values())
}
# Deliberately bounded to the reviewed changes; unknown region changes fail.
CORE_RNA_PAINT_CHANGES: dict[str, list[dict[str, str]]] = {
    asset_id: [] for asset_id in CORE_RNA_REDRAW_FILES
}
CORE_RNA_REGION_LABEL_CHANGES: dict[str, list[dict[str, str]]] = {
    asset_id: ([{"region_id": "coding_region", "before": "Segmented coding sequence", "after": "Coding sequence"}]
               if asset_id == "core.mrna.transcript" else [])
    for asset_id in CORE_RNA_REDRAW_FILES
}
CORE_BROAD_REVISION = "2026-10-13-broad-library"
CORE_BROAD_AUDIT_ID = "core-biology.provenance-license-release.2026-10-13.broad-library"
CORE_BROAD_DATE = "2026-10-13"
CORE_BROAD_RECEIPT = "revision-2026-10-13-broad-library.json"
CORE_BROAD_PREDECESSOR = "revisions/2026-10-13-broad-library-predecessor"
# Final pins are assigned only after the bounded artwork and native reviews pass.
CORE_BROAD_CATALOG_SHA256 = "3d9478cb34924522f74a74855be178e3821123472d939e18dde61a1e8177e918"
CORE_BROAD_AUDIT_SHA256 = "b8850cc7fcc42d6150c509593dec3572049167fc68f7c6df553427cfedfdecc5"
CORE_BROAD_RECEIPT_SHA256 = "d7d9187829854e0d2f540fe7c2e4ead84372aebff0d0eaf314e6324292c65b17"
CORE_BROAD_CHANGED_FILES = {
    "core.cell.generic": "svg/cell_generic.svg",
    "core.cell.epithelial": "svg/cell_epithelial.svg",
    "core.cell.neuron_like": "svg/cell_neuron_like.svg",
    "core.nucleus.round": "svg/nucleus_round.svg",
    "core.mitochondrion.basic": "svg/mitochondrion_basic.svg",
    "core.mitochondrion.basic_manuscript": "svg/mitochondrion_basic_manuscript.svg",
    "core.golgi.basic": "svg/golgi_apparatus.svg",
    "core.er.rough": "svg/rough_endoplasmic_reticulum.svg",
    "core.lysosome.basic": "svg/lysosome.svg",
    "core.antibody.igg": "svg/antibody_igg.svg",
    "core.antibody.igg_manuscript": "svg/antibody_igg_manuscript.svg",
    "core.receptor.membrane": "svg/membrane_receptor.svg",
    "core.protein.enzyme": "svg/catalytic_enzyme.svg",
    "core.protein.kinase": "svg/protein_kinase.svg",
}
CORE_BROAD_NEW_FILES = {
    "core.cell.generic_spread": "svg/cell_generic_spread.svg",
    "core.cell.generic_cutaway": "svg/cell_generic_cutaway.svg",
    "core.cell.epithelial_apical": "svg/cell_epithelial_apical.svg",
    "core.cell.epithelial_cuboidal": "svg/cell_epithelial_cuboidal.svg",
    "core.cell.neuron_bipolar": "svg/cell_neuron_bipolar.svg",
    "core.cell.neuron_pseudounipolar": "svg/cell_neuron_pseudounipolar.svg",
    "core.nucleus.oval_cutaway": "svg/nucleus_oval_cutaway.svg",
    "core.nucleus.envelope_detail": "svg/nucleus_envelope_detail.svg",
    "core.mitochondrion.tubular": "svg/mitochondrion_tubular.svg",
    "core.mitochondrion.network": "svg/mitochondrion_network.svg",
    "core.golgi.oblique": "svg/golgi_oblique.svg",
    "core.golgi.ribbon": "svg/golgi_ribbon.svg",
    "core.er.rough_network": "svg/rough_er_network.svg",
    "core.er.smooth": "svg/smooth_er.svg",
    "core.antibody.fab_fragment": "svg/antibody_fab_fragment.svg",
    "core.antibody.fc_fragment": "svg/antibody_fc_fragment.svg",
    "core.receptor.single_pass_unliganded": "svg/receptor_single_pass_unliganded.svg",
    "core.receptor.extracellular_domain": "svg/receptor_extracellular_domain.svg",
    "core.ligand.peptide": "svg/ligand_peptide.svg",
    "core.ligand.small_molecule": "svg/ligand_small_molecule.svg",
    "core.lysosome.cutaway": "svg/lysosome_cutaway.svg",
    "core.autolysosome": "svg/autolysosome.svg",
    "core.protein.homotrimer": "svg/protein_homotrimer.svg",
    "core.protein.heterotetramer": "svg/protein_heterotetramer.svg",
}
CORE_BROAD_SOURCE = "broad-library-original-vectors-2026-10-13"
CORE_BROAD_PREDECESSOR_FILES = {
    f"{CORE_BROAD_PREDECESSOR}/{name}"
    for name in ("asset-pack.json", "license-release-audit.json", "LICENSE-ASSETS-CC0-1.0.md",
                 CORE_RNA_REVISION_RECEIPT, "snapshot.json", *CORE_BROAD_CHANGED_FILES.values())
}

PROTEIN_PACK_ID = "protein-homeostasis"
PROTEIN_PRODUCT_RELEASE_ID = "protein-homeostasis.qualified-release.2026-10-11"
PROTEIN_PRODUCT_RELEASE_DATE = "2026-10-11"
PROTEIN_PRODUCT_RELEASE_RECEIPT = "product-release-2026-10-11.json"
PROTEIN_PREDECESSOR_PREFIX = "releases/2026-10-10-rights-cleared"
PROTEIN_PREDECESSOR_AUDIT_ID = "protein-homeostasis.rights-cleared-quality-pending.2026-10-10"
PROTEIN_PREDECESSOR_CATALOG_SHA256 = "eb83fdea352334fe94d51a3abd24ee1285ee49e317b200255222cee2e61b60d3"
PROTEIN_PREDECESSOR_AUDIT_SHA256 = "44fbdf7d0ccb16cb6abee8db27cb1d676c6b949764e658893a5a5dfbae72b31f"
PROTEIN_PREDECESSOR_NOTICE_SHA256 = "2a384f66ac943cf1022a42479dfa2b93eddefaf04fe40befc4373bece58f9360"
PROTEIN_PRODUCT_CATALOG_SHA256 = "69d033d292aeafeabae8ca9a5dc4ccde69a030618fe7704e8f49d54475c8e6ab"
PROTEIN_PRODUCT_AUDIT_SHA256 = "700f5cb5287c1ba45dc6f81d4a7f7627661d64cb762100c93d97d4007b06306b"
PROTEIN_PRODUCT_RECEIPT_SHA256 = "f4a1d7bae027eac2fcf2157cc8febeda389158830497576a2108c5a154e43cdf"
PROTEIN_SOURCE_RECORD_ID = "source.protein-homeostasis.2026-10-07"
PROTEIN_CONTOUR_REFINEMENT_RECORD_ID = "source.protein-homeostasis.contour-refinement.2026-10-11"
PROTEIN_OWNER_GRANT_RECORD_ID = "rights.protein-homeostasis.owner-cc0.2026-10-10"
PROTEIN_QUALIFIED_QA_STATUS = "independent_scientific_visual_and_native_editor_review_passed_2026_10_11"
PROTEIN_CONTOUR_FILES = {
    "proteostasis.protein.unfolded_polypeptide": "svg/unfolded_polypeptide.svg",
    "proteostasis.protein.misfolded_protein": "svg/misfolded_protein.svg",
    "proteostasis.protein.hsp70_client_complex": "svg/hsp70_client_complex.svg",
    "proteostasis.protein.hsp90_client_complex": "svg/hsp90_client_complex.svg",
    "proteostasis.protein.ring_e3_ubiquitination_complex": "svg/ring_e3_ubiquitination_complex.svg",
    "proteostasis.protein.deubiquitinase_substrate_complex": "svg/deubiquitinase_substrate_complex.svg",
    "proteostasis.protein.proteasomal_substrate_processing": "svg/proteasomal_substrate_processing.svg",
    "proteostasis.protein.amorphous_protein_aggregate": "svg/amorphous_protein_aggregate.svg",
}
PROTEIN_PREDECESSOR_FILES = {
    f"{PROTEIN_PREDECESSOR_PREFIX}/{name}"
    for name in ("asset-pack.json", "rights-release-record.json", "LICENSE-ASSETS-CC0-1.0.md",
                 *PROTEIN_CONTOUR_FILES.values())
}
PROTEIN_LIFECYCLE_FIELDS = {
    "provenance", "review_status", "style_status", "reviewer_notes", "mvp_quality", "quality_tier",
}
PROTEIN_RELEASE_ASSET_FIELDS = PROTEIN_LIFECYCLE_FIELDS | {"source_record_id"}
PROTEIN_CATALOG_RELEASE_FIELDS = {
    "qa_status", "release_audit", "license_definitions", "product_release_receipt", "assets", "source_records",
}
RNA_METHOD_PACK_ID = "rna-methods"
RNA_METHOD_ARTWORK_REVISION = "2026-10-13-rna-method-refinement"
RNA_METHOD_ARTWORK_DATE = "2026-10-13"
RNA_METHOD_ARTWORK_RECEIPT = "artwork-revision-2026-10-13.json"
RNA_METHOD_ARTWORK_AUDIT_ID = "rna-methods.rights-cleared-quality-pending.2026-10-13"
RNA_METHOD_ARTWORK_QA_STATUS = "independent_scientific_and_visual_review_passed_2026_10_13"
RNA_METHOD_ARTWORK_PREDECESSOR = "revisions/2026-10-13-broad-library-predecessor"
RNA_METHOD_PREDECESSOR_CATALOG_SHA256 = "c65608c0ff7e3828aff4844301f3567e738579f2a7245277b44b14e16f6d4e23"
RNA_METHOD_PREDECESSOR_AUDIT_SHA256 = "2bdaa1fb1dfbdce8bb96d87c7bab640c6692711b80f948e7c8a96b025ba2182f"
RNA_METHOD_PREDECESSOR_SNAPSHOT_SHA256 = "c0c6b883604ec251d8889275f08356caf172377b09e0a332d1c39261ea4020d6"
# Qualification assigns these exact identities only after the final reviews pass.
RNA_METHOD_ARTWORK_CATALOG_SHA256 = "6e77577795470401190cd0f1bed83578ec277cc39f32de79a4f09ba6e0ac908f"
RNA_METHOD_ARTWORK_AUDIT_SHA256 = "9db4e5bae0f9c1a99fe619e41f342efd01ee723b36300d8fdb8fc701cafc4a84"
RNA_METHOD_ARTWORK_RECEIPT_SHA256 = "406d859d9678010169cefb0006131c438276ab65f26972bda228822e2a5b1029"
RNA_METHOD_ARTWORK_FILES = {
    "rna.lab_equipment.microfluidic_cell_partition": "svg/microfluidic_cell_partition.svg",
    "rna.nucleic_acid.barcoded_capture_bead": "svg/barcoded_capture_bead.svg",
    "rna.assay_workflow.spatial_capture_array": "svg/spatial_capture_array.svg",
    "rna.assay_workflow.in_situ_rna_puncta": "svg/in_situ_rna_puncta.svg",
}
RNA_METHOD_PREDECESSOR_BYTE_PINS = {
    "asset-pack.json": "551d9dff3bedfec67c04e902ecbbc7a2a0599a55fdeb96ab1021d88f1d4d6b43",
    "rights-release-record.json": "f4dbf378f88335407f4ac27e1ce21d2a9b0bad06b93218de460e33e058e8a5e6",
    "LICENSE-ASSETS-CC0-1.0.md": "e0ba46f20d4358a4836b371dc8f38ead2135c2b9b0cb61a0cb0edbdfc65767d1",
    "svg/microfluidic_cell_partition.svg": "35f074edeef9a027484522d9c80f7d09e01e5003787fd6455461ff0a022fdc7f",
    "svg/barcoded_capture_bead.svg": "cff4c76a06c860d286d9b3eccf9d2232879a0d0b4c2dc10f844b134cbbf157da",
    "svg/spatial_capture_array.svg": "950e8a5f7992e9a5e56355c79be6eb8dcb3458dae7597cbf505e7110721358b4",
    "svg/in_situ_rna_puncta.svg": "70c113627c0faef82d105b88a981a50022e410244174e1e6fcf47e6e8beb2074",
}
RNA_METHOD_ARTWORK_PREDECESSOR_FILES = {
    f"{RNA_METHOD_ARTWORK_PREDECESSOR}/{name}"
    for name in (*RNA_METHOD_PREDECESSOR_BYTE_PINS, "snapshot.json")
}
RNA_METHOD_ARTWORK_ASSET_FIELDS = {
    "name", "scientific_name", "synonyms", "tags", "description", "connector_hints",
    "scientific_references", "scientific_limitations", "provenance", "review_status",
    "style_status", "reviewer_notes", "mvp_quality", "quality_tier",
}
HEX_COLOR = re.compile(r"^#[0-9A-Fa-f]{6}$")
ASSET_ID = re.compile(r"^[a-z0-9]+(\.[a-z0-9_]+)+$")
RECORD_ID = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
DISALLOWED_SVG_TAGS = {
    "script",
    "style",
    "foreignObject",
    "image",
    "iframe",
    "object",
    "embed",
}
ALLOWED_CATEGORIES = {
    "cell",
    "organelle",
    "nucleic-acid",
    "protein",
    "membrane-signaling",
    "lab-equipment",
    "pathway-symbol",
    "model-system",
    "clinical-sample",
    "assay-workflow",
}

SUPPORTED_CONNECTOR_ROLES = {
    "input",
    "output",
    "bidirectional",
    "attachment",
}

MODERN_ASSET_REQUIRED_FIELDS = {
    "scientific_name",
    "synonyms",
    "subcategory",
    "source_record_id",
    "rights_record_id",
}

LIBRARY_REQUIRED_FIELDS = {"schema_version", "id", "packs"}
LIBRARY_PACK_REQUIRED_FIELDS = {
    "id",
    "path",
    "asset_count",
    "concept_count",
    "enabled",
    "modes",
}

PACK_REQUIRED_FIELDS = {
    "schema_version",
    "id",
    "name",
    "description",
    "style_family",
    "qa_status",
    "release_audit",
    "style_tokens",
    "source_policy",
    "license_definitions",
    "assets",
}

ASSET_REQUIRED_FIELDS = {
    "id",
    "name",
    "category",
    "tags",
    "file",
    "source_type",
    "license",
    "provenance",
    "style_family",
    "review_status",
    "style_status",
    "reviewer_notes",
    "mvp_quality",
    "editable_region_count",
    "editable_color_regions",
}

REGION_REQUIRED_FIELDS = {"id", "label", "default"}
RELEASE_AUDIT_REFERENCE_FIELDS = {
    "file",
    "audit_id",
    "status",
    "asset_count",
    "public_distribution_authorized",
    "selected_public_license",
    "license_notice",
}
RELEASE_AUDIT_REQUIRED_FIELDS = {
    "schema_id",
    "audit_id",
    "audit_date",
    "pack_id",
    "status",
    "release_effective_date",
    "asset_count",
    "rights_cleared_count",
    "third_party_component_count",
    "license_selection_pending_count",
    "public_distribution_authorized",
    "selected_public_license",
    "license_notice",
    "rights_basis",
    "source_records",
    "license_candidates",
    "release_blocker",
    "assets",
}
RELEASE_ASSET_REQUIRED_FIELDS = {
    "asset_id",
    "file",
    "sha256",
    "provenance_sha256",
    "source_type",
    "lineage",
    "current_license",
    "rights_basis",
    "third_party_material",
    "provenance_status",
    "release_disposition",
}


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def fail(message: str) -> None:
    raise ValueError(message)


def canonical_relative_file(value: object, *, label: str, suffix: str) -> PurePosixPath:
    if not isinstance(value, str) or not value or value != value.strip():
        fail(f"{label} must be a non-empty canonical relative path")
    if "\\" in value:
        fail(f"{label} must use forward slashes")
    relative = PurePosixPath(value)
    if relative.is_absolute() or any(part in {"", ".", ".."} for part in relative.parts):
        fail(f"{label} must be a canonical relative path")
    if relative.suffix.lower() != suffix:
        fail(f"{label} must end in {suffix}")
    return relative


def exact_pack_file(pack_dir: Path, relative: PurePosixPath, *, label: str) -> Path:
    current = pack_dir
    for part in relative.parts:
        if current.is_symlink():
            fail(f"{label} must not traverse a symlink: {relative.as_posix()}")
        if not current.is_dir():
            fail(f"{label} parent is not a directory: {relative.as_posix()}")
        names = {child.name for child in current.iterdir()}
        if part not in names:
            if any(name.casefold() == part.casefold() for name in names):
                fail(f"{label} has case drift: {relative.as_posix()}")
            fail(f"{label} is missing: {relative.as_posix()}")
        current = current / part
    if current.is_symlink():
        fail(f"{label} must not be a symlink: {relative.as_posix()}")
    if not current.is_file():
        fail(f"{label} is not a regular file: {relative.as_posix()}")
    return current


def load_pack(path: Path) -> dict:
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except json.JSONDecodeError as error:
        fail(f"{path}: invalid JSON: {error}")


def require_non_empty_string(value: object, *, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        fail(f"{label} must be a non-empty trimmed string")
    return value


def normalize_search_term(value: str) -> str:
    """Normalize a scientific search term for duplicate detection only."""

    return " ".join(re.findall(r"[a-z0-9]+", value.casefold()))


def validate_record_table(pack: dict, field_name: str, *, required: bool) -> set[str]:
    records = pack.get(field_name)
    if records is None and not required:
        return set()
    if not isinstance(records, list) or not records:
        fail(f"{field_name} must be a non-empty list")
    record_ids: set[str] = set()
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            fail(f"{field_name}[{index}] must be an object")
        record_id = require_non_empty_string(
            record.get("id"), label=f"{field_name}[{index}].id"
        )
        if not RECORD_ID.fullmatch(record_id):
            fail(f"{field_name}[{index}].id must use lowercase stable-id characters")
        if record_id in record_ids:
            fail(f"{field_name} contains duplicate id {record_id!r}")
        record_ids.add(record_id)
    return record_ids


POLICY_CONTRIBUTION_ID = "original-vectors.cc0.repository-policy.2026-10-15"
POLICY_CONTRIBUTION_COUNTS = {"cell-structure-stress":40,"tumor-microenvironment":20,"analysis-graphics":20}


def policy_contribution(pack: dict) -> bool:
    """Prospective original contributions under the adopted repository license.

    This does not reinterpret or backdate any historical owner attestation.
    Exact product inclusion still requires the independent finite successor.
    """
    marker = pack.get("contribution_license_policy")
    if marker is None:
        if (pack.get("id") in POLICY_CONTRIBUTION_COUNTS
                and pack.get("release_audit", {}).get("status") != "draft_review_pending"):
            fail("Prospective contribution requires its repository license policy; no inherited owner grant")
        return False
    if (marker != POLICY_CONTRIBUTION_ID or pack.get("id") not in POLICY_CONTRIBUTION_COUNTS
            or len(pack.get("assets", [])) != POLICY_CONTRIBUTION_COUNTS[pack["id"]]):
        fail("Unknown or out-of-scope repository-policy contribution")
    if pack.get("release_audit", {}).get("status") != "rights_cleared_quality_pending":
        fail("Prospective contribution license clearance must preserve separate pending product approval")
    if any(asset.get("source_type") != "clean_room_original_vector" for asset in pack.get("assets", [])):
        fail("Repository-policy contribution covers only its newly constructed original vectors")
    return True


def validate_modern_release_records(pack: dict) -> None:
    pack_id = str(pack.get("id") or "")
    release_reference = pack.get("release_audit") or {}
    source_records = pack.get("source_records") or []
    rights_records = pack.get("rights_records") or []
    qualified_product = protein_product_release_selected(pack)
    if len(source_records) != (2 if qualified_product else 1) or len(rights_records) != 1:
        fail("qualified Protein pack must retain one original source, one refinement source and one rights record"
             if qualified_product else "modern pack must use one pack-scoped source record and one rights record")
    source = source_records[0]
    rights = rights_records[0]
    if qualified_product:
        protein_product_release_identity(pack)
    expected_source = {
        "kind": "clean_room_generation_record",
        "pack_id": pack_id,
        "scope": "all_assets_in_pack",
        "third_party_material": "none_declared",
    }
    expected_rights = {
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
    if release_reference.get("status") == "draft_review_pending":
        expected_rights.update({
            "kind": "draft_rights_review",
            "status": "draft_review_pending",
            "public_distribution_authorized": False,
            "selected_public_license": None,
            "rights_basis": "original_output_pending_owner_review",
            "effective_date": None,
        })
    elif release_reference.get("status") == "rights_cleared_quality_pending" or qualified_product:
        expected_rights.update({
            "kind": "owner_license_grant",
            "status": "rights_cleared",
            "public_distribution_authorized": True,
            "selected_public_license": "CC0-1.0",
            "rights_basis": "owner_attested_original_output",
            "effective_date": release_reference.get("rights_grant_effective_date"),
        })
    if policy_contribution(pack) and release_reference.get("status") == "rights_cleared_quality_pending":
        expected_rights.update(kind="repository_policy_license", status="rights_cleared",
            rights_basis="repository_policy_original_output", effective_date="2026-10-15")
        if (rights.get("license_policy") != POLICY_CONTRIBUTION_ID
                or release_reference.get("rights_grant_effective_date") != "2026-10-15"):
            fail("Prospective contribution must bind its current repository license policy; no inherited owner grant")
    for label, record, expected in (
        ("source record", source, expected_source),
        ("rights record", rights, expected_rights),
    ):
        for key, expected_value in expected.items():
            matches = (record.get(key) is expected_value if isinstance(expected_value, bool)
                       else record.get(key) == expected_value)
            if not matches:
                fail(
                    f"modern-pack {label} {key} must be {expected_value!r}; "
                    f"found {record.get(key)!r}"
                )
    source_date = validate_iso_date(source.get("created_on"), label="modern-pack source created_on")
    audit_date = validate_iso_date(
        release_reference.get("audit_date"), label="modern-pack release audit_date"
    )
    if source_date > audit_date:
        fail("modern-pack source created_on cannot be later than its release audit_date")
    require_non_empty_string(
        source.get("generated_by"), label="modern-pack source record generated_by"
    )
    for label, value in (
        ("source record statement", source.get("statement")),
        ("rights record statement", rights.get("statement")),
        ("rights record qualification", rights.get("qualification")),
    ):
        if not isinstance(value, str) or len(value.strip()) < 40:
            fail(f"modern-pack {label} must be a substantive string")
    if re.search(r"[A-Za-z]:\\", json.dumps([source, rights])):
        fail("modern-pack source and rights records must not expose absolute local Windows paths")


# Retained for tests and downstream callers written against the first modern pack.
validate_expansion_release_records = validate_modern_release_records


def validate_connector_hints(asset_id: str, asset: dict) -> None:
    hints = asset.get("connector_hints")
    if hints is None:
        return
    if not isinstance(hints, list) or not hints:
        fail(f"{asset_id}: connector_hints must be a non-empty list when declared")
    seen_ids: set[str] = set()
    for index, hint in enumerate(hints):
        if not isinstance(hint, dict):
            fail(f"{asset_id}: connector_hints[{index}] must be an object")
        missing = {"id", "role", "x", "y"} - hint.keys()
        if missing:
            fail(f"{asset_id}: connector hint missing fields: {sorted(missing)}")
        hint_id = require_non_empty_string(
            hint.get("id"), label=f"{asset_id}: connector_hints[{index}].id"
        )
        if not RECORD_ID.fullmatch(hint_id):
            fail(f"{asset_id}: connector hint id must use lowercase stable-id characters")
        if hint_id in seen_ids:
            fail(f"{asset_id}: duplicate connector hint id {hint_id!r}")
        seen_ids.add(hint_id)
        role = hint.get("role")
        if role not in SUPPORTED_CONNECTOR_ROLES:
            fail(
                f"{asset_id}: connector hint {hint_id!r} role {role!r} is unsupported; "
                f"expected one of {sorted(SUPPORTED_CONNECTOR_ROLES)}"
            )
        for axis in ("x", "y"):
            coordinate = hint.get(axis)
            if (
                isinstance(coordinate, bool)
                or not isinstance(coordinate, (int, float))
                or not 0 <= coordinate <= 1
            ):
                fail(
                    f"{asset_id}: connector hint {hint_id!r} {axis} must be a normalized number from 0 to 1"
                )


def validate_modern_asset_metadata(
    asset: dict,
    source_record_ids: set[str],
    rights_record_ids: set[str],
) -> None:
    asset_id = asset.get("id", "<missing id>")
    missing = MODERN_ASSET_REQUIRED_FIELDS - asset.keys()
    if missing:
        fail(f"{asset_id}: modern asset missing fields: {sorted(missing)}")

    scientific_name = require_non_empty_string(
        asset.get("scientific_name"), label=f"{asset_id}: scientific_name"
    )
    subcategory = require_non_empty_string(
        asset.get("subcategory"), label=f"{asset_id}: subcategory"
    )
    if normalize_search_term(scientific_name) == "":
        fail(f"{asset_id}: scientific_name must contain searchable letters or numbers")
    if normalize_search_term(subcategory) == "":
        fail(f"{asset_id}: subcategory must contain searchable letters or numbers")

    synonyms = asset.get("synonyms")
    if not isinstance(synonyms, list) or not synonyms:
        fail(f"{asset_id}: synonyms must be a non-empty list")
    normalized_terms = {normalize_search_term(scientific_name)}
    for index, synonym in enumerate(synonyms):
        value = require_non_empty_string(
            synonym, label=f"{asset_id}: synonyms[{index}]"
        )
        normalized = normalize_search_term(value)
        if not normalized:
            fail(f"{asset_id}: synonyms[{index}] must contain searchable letters or numbers")
        if normalized in normalized_terms:
            fail(f"{asset_id}: scientific_name and synonyms must be unique after normalization")
        normalized_terms.add(normalized)

    source_record_id = require_non_empty_string(
        asset.get("source_record_id"), label=f"{asset_id}: source_record_id"
    )
    rights_record_id = require_non_empty_string(
        asset.get("rights_record_id"), label=f"{asset_id}: rights_record_id"
    )
    if source_record_id not in source_record_ids:
        fail(f"{asset_id}: source_record_id {source_record_id!r} is not present in source_records")
    if rights_record_id not in rights_record_ids:
        fail(f"{asset_id}: rights_record_id {rights_record_id!r} is not present in rights_records")

    concept_id = require_non_empty_string(
        asset.get("concept_id"), label=f"{asset_id}: concept_id"
    )
    if not ASSET_ID.fullmatch(concept_id):
        fail(f"{asset_id}: concept_id must use dot-delimited lowercase tokens")
    validate_connector_hints(str(asset_id), asset)


# Retained for tests and downstream callers written against the first modern pack.
validate_expansion_asset_metadata = validate_modern_asset_metadata


def validate_region_schema(asset_id: str, regions: list[dict]) -> set[str]:
    if not isinstance(regions, list) or not regions:
        fail(f"{asset_id}: editable_color_regions must be a non-empty list")

    seen: set[str] = set()
    for index, region in enumerate(regions):
        if not isinstance(region, dict):
            fail(f"{asset_id}: editable_color_regions[{index}] must be an object")
        missing = REGION_REQUIRED_FIELDS - region.keys()
        if missing:
            fail(f"{asset_id}: color region missing fields: {sorted(missing)}")
        region_id = region["id"]
        if not isinstance(region_id, str) or not region_id:
            fail(f"{asset_id}: color region id must be a non-empty string")
        if region_id in seen:
            fail(f"{asset_id}: duplicate color region id {region_id!r}")
        if not isinstance(region["label"], str) or not region["label"].strip():
            fail(f"{asset_id}: region {region_id!r} label must be a non-empty string")
        if not isinstance(region["default"], str) or not HEX_COLOR.fullmatch(
            region["default"]
        ):
            fail(f"{asset_id}: region {region_id!r} default must be a 6-digit hex color")
        seen.add(region_id)
    return seen


def parse_viewbox(asset_id: str, svg_path: Path, viewbox: str) -> tuple[float, float, float, float]:
    parts = viewbox.replace(",", " ").split()
    if len(parts) != 4:
        fail(f"{asset_id}: {svg_path}: viewBox must contain four numbers")
    try:
        return tuple(float(part) for part in parts)  # type: ignore[return-value]
    except ValueError:
        fail(f"{asset_id}: {svg_path}: viewBox contains a non-numeric value")


def validate_svg(
    asset_id: str,
    svg_path: Path,
    metadata_regions: set[str],
    expected_viewbox: str | None,
) -> None:
    try:
        root = ET.parse(svg_path).getroot()
    except ET.ParseError as error:
        fail(f"{asset_id}: {svg_path}: invalid SVG XML: {error}")

    if local_name(root.tag) != "svg":
        fail(f"{asset_id}: {svg_path}: root element must be <svg>")
    viewbox = root.attrib.get("viewBox")
    if not viewbox:
        fail(f"{asset_id}: {svg_path}: missing viewBox")
    if expected_viewbox and viewbox != expected_viewbox:
        fail(f"{asset_id}: {svg_path}: viewBox {viewbox!r} must match pack style token {expected_viewbox!r}")
    min_x, min_y, width, height = parse_viewbox(asset_id, svg_path, viewbox)
    if width <= 0 or height <= 0:
        fail(f"{asset_id}: {svg_path}: viewBox width and height must be positive")
    if min_x != 0 or min_y != 0:
        fail(f"{asset_id}: {svg_path}: viewBox should start at 0 0 for predictable insertion")

    svg_regions: set[str] = set()
    element_ids: set[str] = set()
    local_hrefs: list[str] = []
    titles = 0
    descriptions = 0
    for element in root.iter():
        tag = local_name(element.tag)
        if tag in DISALLOWED_SVG_TAGS:
            fail(f"{asset_id}: {svg_path}: disallowed SVG tag <{tag}>; embedded rasters and unsafe SVG containers are not allowed in scientific assets")
        if tag == "title":
            if not "".join(element.itertext()).strip():
                fail(f"{asset_id}: {svg_path}: SVG title must not be empty")
            titles += 1
        if tag == "desc":
            if not "".join(element.itertext()).strip():
                fail(f"{asset_id}: {svg_path}: SVG desc must not be empty")
            descriptions += 1

        region = element.attrib.get("data-region")
        if region:
            svg_regions.add(region)

        element_id = element.attrib.get("id")
        if element_id:
            if element_id in element_ids:
                fail(f"{asset_id}: {svg_path}: duplicate SVG element id {element_id!r}")
            element_ids.add(element_id)

        for attr_name, value in element.attrib.items():
            attribute = local_name(attr_name)
            if attribute.casefold().startswith("on"):
                fail(f"{asset_id}: {svg_path}: SVG event-handler attributes are not allowed")
            if attribute == "href":
                href = value.strip()
                if not href.startswith("#") or len(href) == 1:
                    fail(
                        f"{asset_id}: {svg_path}: external or embedded href {value!r} is not allowed; "
                        "only verified in-document #id references are permitted"
                    )
                local_hrefs.append(href[1:])
            if "url(" in value.lower():
                fail(f"{asset_id}: {svg_path}: paint/server url() references are not allowed in seed assets")

    missing_local_references = sorted(set(local_hrefs) - element_ids)
    if missing_local_references:
        fail(
            f"{asset_id}: {svg_path}: href references missing in-document ids "
            f"{missing_local_references}"
        )

    if titles == 0 or descriptions == 0:
        fail(f"{asset_id}: {svg_path}: SVG should include title and desc for accessible previews")
    if not svg_regions:
        fail(
            f"{asset_id}: {svg_path}: metadata declares editable regions {sorted(metadata_regions)} "
            "but the SVG has no data-region annotations; add matching SVG data-region attributes or update asset metadata"
        )
    missing_in_svg = metadata_regions - svg_regions
    missing_in_metadata = svg_regions - metadata_regions
    if missing_in_svg or missing_in_metadata:
        details = []
        if missing_in_svg:
            details.append(f"metadata editable_color_regions missing from SVG data-region annotations: {sorted(missing_in_svg)}")
        if missing_in_metadata:
            details.append(f"SVG data-region values missing from metadata editable_color_regions: {sorted(missing_in_metadata)}")
        fail(
            f"{asset_id}: {svg_path}: region mismatch between SVG data-region annotations and metadata; "
            f"{'; '.join(details)}. Fix the SVG data-region values or update editable_color_regions so they match exactly."
        )
    if "outline" not in svg_regions:
        fail(f"{asset_id}: {svg_path}: SVG must include an outline data-region")


def validate_asset(
    asset: dict,
    pack: dict,
    pack_dir: Path,
    license_definitions: dict,
    expected_viewbox: str | None,
    seen_ids: set[str],
    seen_files: dict[str, str],
    *,
    require_modern_metadata: bool = False,
    source_record_ids: set[str] | None = None,
    rights_record_ids: set[str] | None = None,
) -> None:
    if not isinstance(asset, dict):
        fail("asset entries must be objects")
    missing = ASSET_REQUIRED_FIELDS - asset.keys()
    asset_id = asset.get("id", "<missing id>")
    if missing:
        fail(f"{asset_id}: asset missing fields: {sorted(missing)}")
    if not isinstance(asset_id, str) or not ASSET_ID.fullmatch(asset_id):
        fail(f"{asset_id}: id must use dot-delimited lowercase tokens")
    if asset_id in seen_ids:
        fail(f"{asset_id}: duplicate asset id")
    seen_ids.add(asset_id)

    for field in ("name", "category", "source_type", "license", "review_status", "style_status", "reviewer_notes", "mvp_quality"):
        if not isinstance(asset[field], str) or not asset[field].strip():
            fail(f"{asset_id}: {field} must be a non-empty string")
    if asset["category"] not in ALLOWED_CATEGORIES:
        fail(f"{asset_id}: category {asset['category']!r} is not in the allowed MVP category set")
    allowed_style_families = pack.get("style_families") or [pack["style_family"]]
    if asset["style_family"] not in allowed_style_families:
        fail(f"{asset_id}: style_family must be declared by pack style_family or style_families")
    if asset["license"] not in license_definitions:
        fail(f"{asset_id}: license {asset['license']!r} is not defined in license_definitions")
    if (
        not isinstance(asset["tags"], list)
        or not asset["tags"]
        or not all(isinstance(tag, str) and tag.strip() and tag == tag.strip() for tag in asset["tags"])
    ):
        fail(f"{asset_id}: tags must be a non-empty list of strings")
    if not isinstance(asset["provenance"], str) or len(asset["provenance"].strip()) < 40:
        fail(f"{asset_id}: provenance must be a meaningful string")

    relative_svg = canonical_relative_file(asset["file"], label=f"{asset_id}: file", suffix=".svg")
    canonical_file = relative_svg.as_posix()
    prior_file = seen_files.get(canonical_file.casefold())
    if prior_file is not None:
        fail(f"{asset_id}: duplicate or case-equivalent SVG path {canonical_file!r}; already used by {prior_file}")
    seen_files[canonical_file.casefold()] = asset_id
    svg_path = exact_pack_file(pack_dir, relative_svg, label=f"{asset_id}: SVG file")

    metadata_regions = validate_region_schema(asset_id, asset["editable_color_regions"])
    if asset["editable_region_count"] != len(metadata_regions):
        fail(f"{asset_id}: editable_region_count must match editable_color_regions length")
    validate_svg(asset_id, svg_path, metadata_regions, expected_viewbox)
    validate_connector_hints(asset_id, asset)
    if require_modern_metadata:
        validate_modern_asset_metadata(
            asset,
            source_record_ids or set(),
            rights_record_ids or set(),
        )


def validate_concept_variants(assets: list[dict]) -> None:
    groups: dict[str, list[dict]] = {}
    for asset in assets:
        asset_id = asset.get("id", "<missing id>")
        concept_id = asset.get("concept_id")
        style_variant = asset.get("style_variant")
        form_id, form_label = asset.get("form_id"), asset.get("form_label")
        if "form_id" in asset or "form_label" in asset:
            if not all(isinstance(value, str) and value.strip() for value in (form_id, form_label)):
                fail(f"{asset_id}: form_id and form_label must be non-empty strings declared together")
            if not concept_id or not style_variant:
                fail(f"{asset_id}: explicit forms require concept_id and style_variant")
        if bool(concept_id) != bool(style_variant):
            fail(f"{asset_id}: concept_id and style_variant must be declared together")
        if not concept_id:
            continue
        if not isinstance(concept_id, str) or not ASSET_ID.match(concept_id):
            fail(f"{asset_id}: concept_id must use dot-delimited lowercase tokens")
        if not isinstance(style_variant, str) or not style_variant.strip():
            fail(f"{asset_id}: style_variant must be a non-empty string")
        groups.setdefault(concept_id, []).append(asset)

    for concept_id, variants in groups.items():
        if len(variants) < 2:
            continue
        has_forms = any(asset.get("form_id") for asset in variants)
        normalized_variant_names = [
            (normalize_search_term(str(asset.get("form_id") or "default")),
             normalize_search_term(str(asset["style_variant"]))) if has_forms
            else normalize_search_term(str(asset["style_variant"]))
            for asset in variants
        ]
        if (
            any(not value or (has_forms and not all(value)) for value in normalized_variant_names)
            or len(normalized_variant_names) != len(set(normalized_variant_names))
        ):
            fail(
                f"{concept_id}: {'(form_id, style_variant) pairs' if has_forms else 'style_variant values'} must be normalized-unique within a concept"
            )
        categories = {asset.get("category") for asset in variants}
        if len(categories) != 1:
            fail(f"{concept_id}: all style variants must share one category")
        cosmetic_groups = {}
        for asset in variants:
            key = normalize_search_term(str(asset.get("form_id") or "default")) if has_forms else "legacy"
            cosmetic_groups.setdefault(key, []).append(asset)
        for form_id, companions in cosmetic_groups.items():
            label = f"{concept_id}/{form_id}" if has_forms else concept_id
            region_sets = {
                tuple(sorted(region.get("id") for region in asset.get("editable_color_regions", []) if region.get("id")))
                for asset in companions
            }
            if len(region_sets) != 1:
                fail(f"{label}: all style variants must share the same semantic color-region ids")
            if has_forms and len({normalize_search_term(str(asset.get("form_label") or "")) for asset in companions}) != 1:
                fail(f"{label}: cosmetic companions must share one form_label")
            if not (has_forms or all(asset.get("scientific_name") for asset in companions)):
                continue
            scientific_names = {
                normalize_search_term(str(asset.get("scientific_name") or "")) for asset in companions
            }
            if len(scientific_names) != 1:
                fail(f"{label}: all style variants must share one scientific_name")
            subcategories = {
                normalize_search_term(str(asset.get("subcategory") or ""))
                for asset in companions
            }
            if len(subcategories) != 1:
                fail(f"{label}: all style variants must share one subcategory")
            source_record_ids = {asset.get("source_record_id") for asset in companions}
            rights_record_ids = {asset.get("rights_record_id") for asset in companions}
            if len(source_record_ids) != 1 or len(rights_record_ids) != 1:
                fail(
                    f"{label}: all style variants must share source and rights records"
                )


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_svg_bytes(value: bytes) -> str:
    """Hash SVG text independent of whether a checkout uses LF or CRLF."""

    return sha256_bytes(value.replace(b"\r\n", b"\n"))


def sha256_text(value: str) -> str:
    return sha256_bytes(value.encode("utf-8"))


def canonical_json_sha256(value: object) -> str:
    rendered = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return sha256_text(rendered)


def core_release_pin(pack: dict) -> dict[str, str]:
    """Select one exact approved release, never a free-form set of hashes."""
    reference = pack.get("release_audit") or {}
    identity = reference.get("audit_id")
    if identity == CORE_AUDIT_ID and "revision" not in pack and "revision_receipt" not in pack:
        return {"id": CORE_AUDIT_ID, "date": CORE_AUDIT_DATE,
                "catalog": CORE_CATALOG_SHA256, "audit": CORE_AUDIT_SHA256}
    if (identity == CORE_NUCLEIC_AUDIT_ID and pack.get("revision") == CORE_NUCLEIC_REVISION
            and pack.get("revision_receipt") == CORE_REVISION_RECEIPT
            and reference.get("audit_date") == CORE_NUCLEIC_DATE
            and reference.get("release_effective_date") == CORE_NUCLEIC_DATE):
        return {"id": CORE_NUCLEIC_AUDIT_ID, "date": CORE_NUCLEIC_DATE,
                "catalog": CORE_NUCLEIC_CATALOG_SHA256, "audit": CORE_NUCLEIC_AUDIT_SHA256}
    if (identity == CORE_RNA_AUDIT_ID and pack.get("revision") == CORE_RNA_REVISION
            and pack.get("revision_receipt") == CORE_RNA_REVISION_RECEIPT
            and reference.get("audit_date") == CORE_RNA_DATE
            and reference.get("release_effective_date") == CORE_RNA_DATE):
        return {"id": CORE_RNA_AUDIT_ID, "date": CORE_RNA_DATE,
                "catalog": CORE_RNA_CATALOG_SHA256, "audit": CORE_RNA_AUDIT_SHA256}
    if (identity == CORE_BROAD_AUDIT_ID and pack.get("revision") == CORE_BROAD_REVISION
            and pack.get("revision_receipt") == CORE_BROAD_RECEIPT
            and reference.get("audit_date") == CORE_BROAD_DATE
            and reference.get("release_effective_date") == CORE_BROAD_DATE):
        return {"id": CORE_BROAD_AUDIT_ID, "date": CORE_BROAD_DATE,
                "catalog": CORE_BROAD_CATALOG_SHA256, "audit": CORE_BROAD_AUDIT_SHA256, "count": 132}
    fail("Core Biology release must select an exact approved revision identity and date")


def validate_core_revision(pack: dict, pack_dir: Path) -> set[str]:
    if core_release_pin(pack)["id"] == CORE_BROAD_AUDIT_ID:
        return validate_core_broad_revision(pack, pack_dir)
    if core_release_pin(pack)["id"] == CORE_RNA_AUDIT_ID:
        return validate_core_rna_revision(pack, pack_dir)
    return _validate_core_nucleic_revision(pack, pack_dir)


def _validate_core_nucleic_revision(
    pack: dict, pack_dir: Path, *, restored_rna_from_snapshot: bool = False
) -> set[str]:
    """Verify the finite predecessor inventory and three-asset redraw chain."""
    if core_release_pin(pack)["id"] != CORE_NUCLEIC_AUDIT_ID:
        return set()
    receipt_path = exact_pack_file(pack_dir, PurePosixPath(CORE_REVISION_RECEIPT), label="Core Biology revision receipt")
    receipt = load_pack(receipt_path)
    if canonical_json_sha256(receipt) != CORE_NUCLEIC_RECEIPT_SHA256:
        fail("Core Biology revision receipt exact identity mismatch")
    if (receipt.get("schema_id") != "superbench.scientificAssetRevision.v1"
            or receipt.get("revision_id") != CORE_NUCLEIC_REVISION
            or receipt.get("revision_date") != CORE_NUCLEIC_DATE
            or receipt.get("pack_id") != CORE_PACK_ID):
        fail("Core Biology revision receipt identity or date mismatch")
    if (receipt.get("review", {}).get("status") != "accepted"
            or receipt.get("review", {}).get("visual_review") != "pass"
            or receipt.get("review", {}).get("editor_checks") != "pass"):
        fail("Core Biology revision requires accepted visual and editor reviews")
    archived_catalog_path = exact_pack_file(pack_dir, PurePosixPath(f"{CORE_PREDECESSOR_PREFIX}/asset-pack.json"), label="Core Biology predecessor catalog")
    archived_audit_path = exact_pack_file(pack_dir, PurePosixPath(f"{CORE_PREDECESSOR_PREFIX}/license-release-audit.json"), label="Core Biology predecessor audit")
    original = load_pack(archived_catalog_path)
    original_audit = load_pack(archived_audit_path)
    if canonical_json_sha256(original) != CORE_CATALOG_SHA256:
        fail("Core Biology predecessor catalog exact identity mismatch")
    if canonical_json_sha256(original_audit) != CORE_AUDIT_SHA256:
        fail("Core Biology predecessor audit exact identity mismatch")
    old_by_id = {asset["id"]: asset for asset in original["assets"]}
    old_audit_by_id = {entry["asset_id"]: entry for entry in original_audit["assets"]}
    current_by_id = {asset["id"]: asset for asset in pack["assets"]}
    if set(current_by_id) != set(old_by_id):
        fail("Core Biology revision must preserve every stable asset id")
    expected_predecessor = {"audit_id": CORE_AUDIT_ID, "catalog_sha256": CORE_CATALOG_SHA256,
                            "audit_sha256": CORE_AUDIT_SHA256, "snapshot": CORE_PREDECESSOR_PREFIX}
    if receipt.get("predecessor") != expected_predecessor:
        fail("Core Biology revision receipt predecessor mismatch")
    if receipt.get("current_catalog_sha256") != canonical_json_sha256(pack):
        fail("Core Biology revision receipt does not bind its current catalog")
    notice = exact_pack_file(pack_dir, PurePosixPath(f"{CORE_PREDECESSOR_PREFIX}/LICENSE-ASSETS-CC0-1.0.md"), label="Core Biology predecessor CC0 notice")
    current_notice = exact_pack_file(pack_dir, PurePosixPath("LICENSE-ASSETS-CC0-1.0.md"), label="Core Biology CC0 notice")
    if any(sha256_svg_bytes(path.read_bytes()) != CORE_LICENSE_SHA256 for path in (notice, current_notice)):
        fail("Core Biology original CC0 notice exact identity mismatch")
    changed = receipt.get("changed_assets")
    if not isinstance(changed, list) or len(changed) != len(CORE_REDRAW_FILES):
        fail("Core Biology revision receipt must name exactly three redraws")
    changed_by_id = {entry.get("asset_id"): entry for entry in changed if isinstance(entry, dict)}
    if set(changed_by_id) != set(CORE_REDRAW_FILES):
        fail("Core Biology revision receipt redraw ids mismatch")
    for asset_id, previous in old_by_id.items():
        current = current_by_id[asset_id]
        old_entry = old_audit_by_id[asset_id]
        if asset_id not in CORE_REDRAW_FILES:
            if current != previous:
                fail(f"{asset_id}: unrelated Core Biology metadata changed in nucleic-acid revision")
            previous_path = previous["file"]
            if restored_rna_from_snapshot and asset_id in CORE_RNA_REDRAW_FILES:
                previous_path = f"{CORE_RNA_PREDECESSOR_PREFIX}/{previous_path}"
            unchanged_svg = exact_pack_file(pack_dir, PurePosixPath(previous_path), label=f"{asset_id}: unchanged SVG")
            if sha256_svg_bytes(unchanged_svg.read_bytes()) != old_entry["sha256"]:
                fail(f"{asset_id}: unrelated Core Biology SVG changed in nucleic-acid revision")
            continue
        redraw_file = CORE_REDRAW_FILES[asset_id]
        if current["file"] != redraw_file or previous["file"] != redraw_file:
            fail(f"{asset_id}: redraw must preserve its stable SVG path")
        archived_svg = exact_pack_file(pack_dir, PurePosixPath(f"{CORE_PREDECESSOR_PREFIX}/{redraw_file}"), label=f"{asset_id}: predecessor SVG")
        current_svg = exact_pack_file(pack_dir, PurePosixPath(redraw_file), label=f"{asset_id}: redraw SVG")
        if sha256_svg_bytes(archived_svg.read_bytes()) != old_entry["sha256"]:
            fail(f"{asset_id}: predecessor SVG exact identity mismatch")
        row = changed_by_id[asset_id]
        identity = {"file": redraw_file, "before_svg_sha256": old_entry["sha256"],
                    "after_svg_sha256": sha256_svg_bytes(current_svg.read_bytes()),
                    "before_metadata_sha256": canonical_json_sha256(previous),
                    "after_metadata_sha256": canonical_json_sha256(current)}
        if any(row.get(key) != value for key, value in identity.items()):
            fail(f"{asset_id}: revision receipt redraw identity mismatch")
        if row["before_svg_sha256"] == row["after_svg_sha256"]:
            fail(f"{asset_id}: revision receipt claims a redraw without an SVG change")
        allowed_fields = {"name", "description", "provenance", "source_type", "review_status", "style_status", "reviewer_notes", "editable_color_regions"}
        if any(current.get(key) != previous.get(key) for key in (set(current) | set(previous)) - allowed_fields):
            fail(f"{asset_id}: redraw changed stable scientific or style metadata")
        expected_regions = json.loads(json.dumps(previous["editable_color_regions"]))
        expected_channel_changes = []
        if asset_id.startswith("core.dna.double_helix"):
            next(region for region in expected_regions if region["id"] == "backbone")["paint"] = "fill"
            expected_channel_changes = [{"region_id": "backbone", "before": "stroke", "after": "fill"}]
        elif asset_id == "core.chromatin.loop":
            next(region for region in expected_regions if region["id"] == "histone")["paint"] = "fill"
            expected_channel_changes = [{"region_id": "histone", "before": "fill+stroke (implicit default)", "after": "fill"}]
        if current["editable_color_regions"] != expected_regions or row.get("paint_channel_changes") != expected_channel_changes:
            fail(f"{asset_id}: redraw region compatibility or declared paint-channel change mismatch")
        if current.get("license") != "CC0-1.0" or row.get("license") != "CC0-1.0":
            fail(f"{asset_id}: redraw must retain CC0-1.0")
    return {*CORE_PREDECESSOR_FILES, CORE_REVISION_RECEIPT}


def validate_core_rna_revision(pack: dict, pack_dir: Path) -> set[str]:
    """Verify a four-asset second revision without weakening its prior chain."""
    receipt = load_pack(exact_pack_file(
        pack_dir, PurePosixPath(CORE_RNA_REVISION_RECEIPT), label="Core Biology RNA revision receipt"))
    if canonical_json_sha256(receipt) != CORE_RNA_RECEIPT_SHA256:
        fail("Core Biology RNA revision receipt exact identity mismatch")
    if (receipt.get("schema_id") != "superbench.scientificAssetRevision.v1"
            or receipt.get("revision_id") != CORE_RNA_REVISION
            or receipt.get("revision_date") != CORE_RNA_DATE
            or receipt.get("pack_id") != CORE_PACK_ID):
        fail("Core Biology RNA revision receipt identity or date mismatch")
    if (receipt.get("review", {}).get("status") != "accepted"
            or receipt.get("review", {}).get("visual_review") != "pass"
            or receipt.get("review", {}).get("editor_checks") != "pass"):
        fail("Core Biology RNA revision requires accepted visual and editor reviews")
    prior = load_pack(exact_pack_file(pack_dir,
        PurePosixPath(f"{CORE_RNA_PREDECESSOR_PREFIX}/asset-pack.json"), label="Core Biology RNA predecessor catalog"))
    prior_audit = load_pack(exact_pack_file(pack_dir,
        PurePosixPath(f"{CORE_RNA_PREDECESSOR_PREFIX}/license-release-audit.json"), label="Core Biology RNA predecessor audit"))
    if canonical_json_sha256(prior) != CORE_NUCLEIC_CATALOG_SHA256:
        fail("Core Biology RNA predecessor catalog exact identity mismatch")
    if canonical_json_sha256(prior_audit) != CORE_NUCLEIC_AUDIT_SHA256:
        fail("Core Biology RNA predecessor audit exact identity mismatch")
    prior_receipt = load_pack(exact_pack_file(pack_dir,
        PurePosixPath(f"{CORE_RNA_PREDECESSOR_PREFIX}/{CORE_REVISION_RECEIPT}"), label="Core Biology RNA predecessor receipt"))
    if canonical_json_sha256(prior_receipt) != CORE_NUCLEIC_RECEIPT_SHA256:
        fail("Core Biology RNA predecessor receipt exact identity mismatch")
    notice = exact_pack_file(pack_dir,
        PurePosixPath(f"{CORE_RNA_PREDECESSOR_PREFIX}/LICENSE-ASSETS-CC0-1.0.md"), label="Core Biology RNA predecessor CC0 notice")
    if sha256_svg_bytes(notice.read_bytes()) != CORE_LICENSE_SHA256:
        fail("Core Biology RNA predecessor CC0 notice exact identity mismatch")
    # Reconstruct the previous source from its four archived RNA originals and
    # the 104 retained current files, each checked exactly. The earlier checks still
    # validate the July archive and the original approved receipt unchanged.
    earlier_files = _validate_core_nucleic_revision(prior, pack_dir, restored_rna_from_snapshot=True)
    expected_predecessor = {
        "audit_id": CORE_NUCLEIC_AUDIT_ID, "catalog_sha256": CORE_NUCLEIC_CATALOG_SHA256,
        "audit_sha256": CORE_NUCLEIC_AUDIT_SHA256, "receipt_sha256": CORE_NUCLEIC_RECEIPT_SHA256,
        "snapshot": CORE_RNA_PREDECESSOR_PREFIX,
    }
    if receipt.get("predecessor") != expected_predecessor:
        fail("Core Biology RNA revision receipt predecessor mismatch")
    if receipt.get("current_catalog_sha256") != canonical_json_sha256(pack):
        fail("Core Biology RNA revision receipt does not bind its current catalog")
    before_by_id = {asset["id"]: asset for asset in prior["assets"]}
    audit_by_id = {asset["asset_id"]: asset for asset in prior_audit["assets"]}
    current_by_id = {asset["id"]: asset for asset in pack["assets"]}
    if set(current_by_id) != set(before_by_id):
        fail("Core Biology RNA revision must preserve every stable asset id")
    changed = receipt.get("changed_assets")
    if not isinstance(changed, list) or len(changed) != len(CORE_RNA_REDRAW_FILES):
        fail("Core Biology RNA revision receipt must name exactly four redraws")
    changed_by_id = {row.get("asset_id"): row for row in changed if isinstance(row, dict)}
    if set(changed_by_id) != set(CORE_RNA_REDRAW_FILES):
        fail("Core Biology RNA revision receipt redraw ids mismatch")
    allowed_fields = {"name", "description", "provenance", "source_type", "review_status",
                      "style_status", "reviewer_notes", "editable_color_regions"}
    for asset_id, before in before_by_id.items():
        current = current_by_id[asset_id]
        if asset_id not in CORE_RNA_REDRAW_FILES:
            if current != before:
                fail(f"{asset_id}: unrelated Core Biology metadata changed in RNA revision")
            retained = exact_pack_file(pack_dir, PurePosixPath(before["file"]), label=f"{asset_id}: retained SVG")
            if sha256_svg_bytes(retained.read_bytes()) != audit_by_id[asset_id]["sha256"]:
                fail(f"{asset_id}: unrelated Core Biology SVG changed in RNA revision")
            continue
        redraw_file = CORE_RNA_REDRAW_FILES[asset_id]
        if before["file"] != redraw_file or current["file"] != redraw_file:
            fail(f"{asset_id}: RNA redraw must preserve its stable SVG path")
        before_svg = exact_pack_file(pack_dir,
            PurePosixPath(f"{CORE_RNA_PREDECESSOR_PREFIX}/{redraw_file}"), label=f"{asset_id}: RNA predecessor SVG")
        after_svg = exact_pack_file(pack_dir, PurePosixPath(redraw_file), label=f"{asset_id}: RNA redraw SVG")
        before_hash = sha256_svg_bytes(before_svg.read_bytes())
        after_hash = sha256_svg_bytes(after_svg.read_bytes())
        if before_hash != audit_by_id[asset_id]["sha256"]:
            fail(f"{asset_id}: RNA predecessor SVG exact identity mismatch")
        row = changed_by_id[asset_id]
        expected = {
            "file": redraw_file, "before_svg_sha256": before_hash, "after_svg_sha256": after_hash,
            "before_metadata_sha256": canonical_json_sha256(before),
            "after_metadata_sha256": canonical_json_sha256(current),
            "license": "CC0-1.0", "lineage": "original_redraw_of_released_workspace_vector",
            "paint_channel_changes": CORE_RNA_PAINT_CHANGES[asset_id],
            "region_label_changes": CORE_RNA_REGION_LABEL_CHANGES[asset_id],
        }
        if any(row.get(key) != value for key, value in expected.items()):
            fail(f"{asset_id}: RNA revision receipt redraw identity mismatch")
        if before_hash == after_hash:
            fail(f"{asset_id}: RNA revision claims a redraw without an SVG change")
        if any(current.get(key) != before.get(key) for key in (set(current) | set(before)) - allowed_fields):
            fail(f"{asset_id}: RNA redraw changed stable scientific or style metadata")
        expected_regions = json.loads(json.dumps(before["editable_color_regions"]))
        for change in CORE_RNA_PAINT_CHANGES[asset_id]:
            next(region for region in expected_regions if region["id"] == change["region_id"])["paint"] = change["after"]
        for change in CORE_RNA_REGION_LABEL_CHANGES[asset_id]:
            next(region for region in expected_regions if region["id"] == change["region_id"])["label"] = change["after"]
        if current["editable_color_regions"] != expected_regions or current.get("license") != "CC0-1.0":
            fail(f"{asset_id}: RNA redraw region compatibility mismatch")
    return {*earlier_files, *CORE_RNA_PREDECESSOR_FILES, CORE_RNA_REVISION_RECEIPT}


def validate_core_broad_revision(pack: dict, pack_dir: Path) -> set[str]:
    """Bind the finite expansion to the unchanged, approved RNA predecessor."""
    receipt = load_pack(exact_pack_file(pack_dir, PurePosixPath(CORE_BROAD_RECEIPT), label="Broad Library receipt"))
    if canonical_json_sha256(receipt) != CORE_BROAD_RECEIPT_SHA256:
        fail("Core Biology broad revision receipt exact identity mismatch")
    if (receipt.get("schema_id") != "superbench.scientificAssetRevision.v1"
            or receipt.get("revision_id") != CORE_BROAD_REVISION
            or receipt.get("revision_date") != CORE_BROAD_DATE
            or receipt.get("pack_id") != CORE_PACK_ID):
        fail("Core Biology broad revision receipt identity mismatch")
    review = receipt.get("review", {})
    if any(review.get(key) != expected for key, expected in
           {"status": "accepted", "scientific_review": "pass", "visual_review": "pass", "editor_checks": "pass"}.items()):
        fail("Core Biology broad revision requires scientific, visual and native editor acceptance")
    prefix = CORE_BROAD_PREDECESSOR
    prior = load_pack(exact_pack_file(pack_dir, PurePosixPath(f"{prefix}/asset-pack.json"), label="Broad predecessor catalog"))
    prior_audit = load_pack(exact_pack_file(pack_dir, PurePosixPath(f"{prefix}/license-release-audit.json"), label="Broad predecessor audit"))
    expected_predecessor = {"audit_id": CORE_RNA_AUDIT_ID, "catalog_sha256": CORE_RNA_CATALOG_SHA256,
                            "audit_sha256": CORE_RNA_AUDIT_SHA256, "receipt_sha256": CORE_RNA_RECEIPT_SHA256,
                            "snapshot": prefix}
    if receipt.get("predecessor") != expected_predecessor:
        fail("Core Biology broad revision predecessor mismatch")
    if canonical_json_sha256(prior) != CORE_RNA_CATALOG_SHA256 or canonical_json_sha256(prior_audit) != CORE_RNA_AUDIT_SHA256:
        fail("Core Biology broad predecessor exact identity mismatch")
    if receipt.get("current_catalog_sha256") != canonical_json_sha256(pack):
        fail("Core Biology broad receipt does not bind its current catalog")
    # Earlier accepted records stay immutable, including the separate RNA redraw.
    historical_json = {
        f"{CORE_PREDECESSOR_PREFIX}/asset-pack.json": CORE_CATALOG_SHA256,
        f"{CORE_PREDECESSOR_PREFIX}/license-release-audit.json": CORE_AUDIT_SHA256,
        f"{CORE_RNA_PREDECESSOR_PREFIX}/asset-pack.json": CORE_NUCLEIC_CATALOG_SHA256,
        f"{CORE_RNA_PREDECESSOR_PREFIX}/license-release-audit.json": CORE_NUCLEIC_AUDIT_SHA256,
        CORE_REVISION_RECEIPT: CORE_NUCLEIC_RECEIPT_SHA256,
        f"{CORE_RNA_PREDECESSOR_PREFIX}/{CORE_REVISION_RECEIPT}": CORE_NUCLEIC_RECEIPT_SHA256,
        CORE_RNA_REVISION_RECEIPT: CORE_RNA_RECEIPT_SHA256,
        f"{prefix}/{CORE_RNA_REVISION_RECEIPT}": CORE_RNA_RECEIPT_SHA256,
    }
    for relative, digest in historical_json.items():
        value = load_pack(exact_pack_file(pack_dir, PurePosixPath(relative), label="Historical Core Biology record"))
        if canonical_json_sha256(value) != digest:
            fail(f"{relative}: historical Core Biology record exact identity mismatch")
    # Verify every earlier archived vector, rather than accepting its directory
    # merely because the corresponding historical catalog is pinned.
    for archive_prefix, file_map in [(CORE_PREDECESSOR_PREFIX, CORE_REDRAW_FILES),
                                     (CORE_RNA_PREDECESSOR_PREFIX, CORE_RNA_REDRAW_FILES)]:
        archived_audit = load_pack(pack_dir / archive_prefix / "license-release-audit.json")
        archived_rows = {row["asset_id"]: row for row in archived_audit["assets"]}
        for asset_id, relative in file_map.items():
            archived_svg = exact_pack_file(pack_dir, PurePosixPath(f"{archive_prefix}/{relative}"), label="Historical archived SVG")
            if sha256_svg_bytes(archived_svg.read_bytes()) != archived_rows[asset_id]["sha256"]:
                fail(f"{asset_id}: historical archived SVG exact identity mismatch")
    for relative in ("LICENSE-ASSETS-CC0-1.0.md", f"{prefix}/LICENSE-ASSETS-CC0-1.0.md",
                     f"{CORE_PREDECESSOR_PREFIX}/LICENSE-ASSETS-CC0-1.0.md",
                     f"{CORE_RNA_PREDECESSOR_PREFIX}/LICENSE-ASSETS-CC0-1.0.md"):
        if sha256_svg_bytes(exact_pack_file(pack_dir, PurePosixPath(relative), label="Core CC0 notice").read_bytes()) != CORE_LICENSE_SHA256:
            fail("Core Biology CC0 notice exact identity mismatch")
    before = {a["id"]: a for a in prior["assets"]}
    current = {a["id"]: a for a in pack["assets"]}
    prior_rows = {a["asset_id"]: a for a in prior_audit["assets"]}
    if set(current) != set(before) | set(CORE_BROAD_NEW_FILES):
        fail("Core Biology broad revision must preserve108 stable ids and add exactly24 reviewed drawings")
    changed = {row.get("asset_id"): row for row in receipt.get("changed_assets", [])}
    added = {row.get("asset_id"): row for row in receipt.get("added_assets", [])}
    if set(changed) != set(CORE_BROAD_CHANGED_FILES) or set(added) != set(CORE_BROAD_NEW_FILES):
        fail("Core Biology broad receipt finite SVG cohort mismatch")
    metadata_changed = {row.get("asset_id"): row for row in receipt.get("metadata_changes", [])}
    actual_metadata_changed = {key for key in before if before[key] != current[key]}
    if set(metadata_changed) != actual_metadata_changed:
        fail("Core Biology broad receipt metadata cohort mismatch")
    redraw_fields = {"name", "description", "provenance", "source_type", "source_record_id", "review_status",
                     "style_status", "reviewer_notes", "editable_color_regions", "editable_region_count", "scientific_name",
                     "synonyms", "scientific_references", "scientific_limitations", "tags", "concept_id", "style_variant",
                     "form_id", "form_label"}
    form_fields = {"form_id", "form_label", "concept_id", "style_variant"}
    for asset_id, previous in before.items():
        now = current[asset_id]
        allowed = redraw_fields if asset_id in CORE_BROAD_CHANGED_FILES else form_fields
        if asset_id == "core.mrna.transcript":
            allowed = allowed | {"tags", "scientific_name", "synonyms"}
        if any(previous.get(key) != now.get(key) for key in (set(previous) | set(now)) - allowed):
            fail(f"{asset_id}: broad revision changed unrelated stable metadata")
        if previous != now:
            row = metadata_changed[asset_id]
            if row != {"asset_id": asset_id, "before_metadata_sha256": canonical_json_sha256(previous),
                       "after_metadata_sha256": canonical_json_sha256(now)}:
                fail(f"{asset_id}: broad revision metadata identity mismatch")
        current_svg = exact_pack_file(pack_dir, PurePosixPath(now["file"]), label=f"{asset_id}: current SVG")
        after_hash = sha256_svg_bytes(current_svg.read_bytes())
        if asset_id not in CORE_BROAD_CHANGED_FILES:
            if after_hash != prior_rows[asset_id]["sha256"]:
                fail(f"{asset_id}: unrelated Core Biology SVG changed in broad revision")
            continue
        relative = CORE_BROAD_CHANGED_FILES[asset_id]
        if previous["file"] != relative or now["file"] != relative:
            fail(f"{asset_id}: broad revision must preserve the stable SVG path")
        before_hash = sha256_svg_bytes(exact_pack_file(pack_dir, PurePosixPath(f"{prefix}/{relative}"), label="Predecessor SVG").read_bytes())
        if before_hash != prior_rows[asset_id]["sha256"] or before_hash == after_hash:
            fail(f"{asset_id}: broad SVG predecessor identity or claimed change mismatch")
        if changed[asset_id] != {"asset_id": asset_id, "file": relative, "before_svg_sha256": before_hash,
                                 "after_svg_sha256": after_hash, "license": "CC0-1.0"}:
            fail(f"{asset_id}: broad SVG receipt identity mismatch")
        regions = json.loads(json.dumps(previous["editable_color_regions"]))
        if asset_id in {"core.antibody.igg", "core.antibody.igg_manuscript"}:
            regions[0]["label"] = "Heavy chains"
            regions.insert(1, {"id": "light_chain", "label": "Light chains", "default": "#B8B5FF", "paint": "stroke"})
        if now["editable_color_regions"] != regions:
            fail(f"{asset_id}: broad redraw semantic region compatibility mismatch")
        previous_paints = rna_method_svg_paints(pack_dir / prefix / relative)
        current_paints = rna_method_svg_paints(current_svg)
        if any(current_paints.get(region) != paints for region, paints in previous_paints.items()):
            fail(f"{asset_id}: broad redraw changed an existing effective semantic paint")
        expected_added = ({"light_chain"} if asset_id in {"core.antibody.igg", "core.antibody.igg_manuscript"} else set())
        if set(current_paints) - set(previous_paints) != expected_added:
            fail(f"{asset_id}: broad redraw added an unreviewed semantic paint region")
        if expected_added and current_paints.get("light_chain") != {("none", "#b8b5ff")}:
            fail(f"{asset_id}: broad redraw light-chain paint mismatch")
        if now.get("source_record_id") != CORE_BROAD_SOURCE:
            fail(f"{asset_id}: broad redraw source record mismatch")
    for asset_id, relative in CORE_BROAD_NEW_FILES.items():
        now = current[asset_id]
        if now["file"] != relative or now.get("license") != "CC0-1.0" or now.get("source_record_id") != CORE_BROAD_SOURCE:
            fail(f"{asset_id}: added drawing identity or source mismatch")
        if added[asset_id] != {"asset_id": asset_id, "file": relative,
                              "svg_sha256": sha256_svg_bytes((pack_dir / relative).read_bytes()),
                              "metadata_sha256": canonical_json_sha256(now), "license": "CC0-1.0"}:
            fail(f"{asset_id}: added drawing receipt identity mismatch")
    return {*CORE_PREDECESSOR_FILES, CORE_REVISION_RECEIPT, *CORE_RNA_PREDECESSOR_FILES,
            CORE_RNA_REVISION_RECEIPT, *CORE_BROAD_PREDECESSOR_FILES, CORE_BROAD_RECEIPT}


def rna_method_artwork_revision_selected(pack: dict) -> bool:
    """Select one finite artwork revision without granting product release."""
    fields = {"artwork_revision", "artwork_revision_receipt"}
    if not fields.intersection(pack):
        return False
    if (pack.get("id") != RNA_METHOD_PACK_ID
            or pack.get("artwork_revision") != RNA_METHOD_ARTWORK_REVISION
            or pack.get("artwork_revision_receipt") != RNA_METHOD_ARTWORK_RECEIPT):
        fail("RNA Methods artwork revision must select its exact approved identity and receipt")
    return True


def rna_method_svg_paints(path: Path) -> dict[str, set[tuple[str, str]]]:
    """Compare effective semantic paints while allowing new original geometry."""
    paints: dict[str, set[tuple[str, str]]] = {}
    geometry = {"path", "circle", "ellipse", "rect", "polygon", "polyline", "line"}

    def visit(element: ET.Element, inherited: dict[str, str], region: str | None) -> None:
        attrs = {**inherited, **{key: element.attrib[key] for key in ("fill", "stroke") if key in element.attrib}}
        region = element.attrib.get("data-region", region)
        if "style" in element.attrib:
            fail("RNA Methods artwork refinement cannot add inline paint styles")
        if region and local_name(element.tag) in geometry:
            signature = tuple(attrs.get(key, "black" if key == "fill" else "none").lower()
                              for key in ("fill", "stroke"))
            paints.setdefault(region, set()).add(signature)
        for child in element:
            visit(child, attrs, region)

    visit(ET.fromstring(path.read_bytes()), {}, None)
    return paints


def validate_rna_method_artwork_source(pack: dict, prior: dict) -> None:
    sources = pack.get("source_records")
    before_sources = prior.get("source_records")
    if (not isinstance(sources, list) or len(sources) != 1
            or not isinstance(sources[0], dict) or not isinstance(before_sources, list)
            or len(before_sources) != 1):
        fail("RNA Methods refinement must enrich its single original source record")
    source = sources[0]
    if {key: value for key, value in source.items() if key != "artwork_refinement"} != before_sources[0]:
        fail("RNA Methods refinement must preserve every original source-record field")
    refinement = source.get("artwork_refinement")
    expected = {
        "revision_id": RNA_METHOD_ARTWORK_REVISION,
        "revision_date": RNA_METHOD_ARTWORK_DATE,
        "asset_ids": list(RNA_METHOD_ARTWORK_FILES),
        "third_party_material": "none_declared",
    }
    if (not isinstance(refinement, dict)
            or set(refinement) != {*expected, "generated_by", "statement", "scientific_references"}
            or any(refinement.get(key) != value for key, value in expected.items())):
        fail("RNA Methods nested artwork-refinement identity, date or scope mismatch")
    for field, minimum in (("generated_by", 10), ("statement", 80)):
        if not isinstance(refinement.get(field), str) or len(refinement[field].strip()) < minimum:
            fail(f"RNA Methods artwork refinement {field} must be substantive")
    references = refinement.get("scientific_references")
    if not isinstance(references, list) or not references:
        fail("RNA Methods artwork refinement scientific_references must be a non-empty array")
    from urllib.parse import urlsplit
    for reference in references:
        if not isinstance(reference, dict) or set(reference) != {"citation", "doi", "url", "figure", "design_decision"}:
            fail("RNA Methods refinement scientific references must record citation, doi, url, figure and design_decision")
        for field, minimum in (("citation", 10), ("figure", 10), ("design_decision", 40)):
            value = reference.get(field)
            if not isinstance(value, str) or value != value.strip() or len(value) < minimum:
                fail(f"RNA Methods refinement scientific reference {field} must identify its source and bounded design use")
        doi = reference.get("doi")
        if not isinstance(doi, str) or not re.fullmatch(r"10\.\d{4,9}/\S+", doi):
            fail("RNA Methods refinement scientific reference doi must identify a primary publication")
        url = reference.get("url")
        if not isinstance(url, str) or url != url.strip() or re.search(r"\s", url):
            fail("RNA Methods refinement scientific reference url must be a canonical HTTPS source link")
        parsed_url = urlsplit(url)
        if parsed_url.scheme != "https" or not parsed_url.netloc or parsed_url.username or parsed_url.password:
            fail("RNA Methods refinement scientific reference url must be a canonical HTTPS source link")
    if re.search(r"[A-Za-z]:\\", json.dumps(refinement)):
        fail("RNA Methods refinement must not expose absolute local Windows paths")


def build_rna_method_artwork_audit(pack: dict, pack_dir: Path) -> dict:
    """Prepare the four current byte bindings without modifying the existing grant."""
    if not rna_method_artwork_revision_selected(pack):
        fail("RNA Methods artwork audit requires the exact refinement identity")
    prefix = RNA_METHOD_ARTWORK_PREDECESSOR
    prior = load_pack(exact_pack_file(pack_dir, PurePosixPath(f"{prefix}/asset-pack.json"),
                                     label="RNA Methods predecessor catalog"))
    audit = load_pack(exact_pack_file(pack_dir, PurePosixPath(f"{prefix}/rights-release-record.json"),
                                     label="RNA Methods predecessor rights audit"))
    if (canonical_json_sha256(prior) != RNA_METHOD_PREDECESSOR_CATALOG_SHA256
            or canonical_json_sha256(audit) != RNA_METHOD_PREDECESSOR_AUDIT_SHA256):
        fail("RNA Methods artwork audit requires the exact predecessor identities")
    if (pack.get("rights_records") != prior.get("rights_records")
            or pack.get("release_audit") != {**prior["release_audit"],
                "audit_id": RNA_METHOD_ARTWORK_AUDIT_ID, "audit_date": RNA_METHOD_ARTWORK_DATE}):
        fail("RNA Methods artwork audit must preserve the original grant and pending product-release state")
    validate_rna_method_artwork_source(pack, prior)
    assets = pack.get("assets")
    if (not isinstance(assets, list) or len(assets) != 4 or not all(isinstance(asset, dict) for asset in assets)
            or {asset.get("id"): asset.get("file") for asset in assets} != RNA_METHOD_ARTWORK_FILES
            or [asset.get("id") for asset in assets] != list(RNA_METHOD_ARTWORK_FILES)):
        fail("RNA Methods artwork audit requires the four ordered stable asset identities")
    for before, current in zip(prior["assets"], assets):
        if any(before.get(key) != current.get(key) for key in (set(before) | set(current)) - RNA_METHOD_ARTWORK_ASSET_FIELDS):
            fail(f"{before['id']}: RNA Methods artwork audit cannot change stable scientific or editable-region metadata")
    audit["audit_id"] = RNA_METHOD_ARTWORK_AUDIT_ID
    audit["audit_date"] = RNA_METHOD_ARTWORK_DATE
    audit["source_records"] = json.loads(json.dumps(pack["source_records"]))
    audit["rights_records"] = json.loads(json.dumps(pack["rights_records"]))
    by_id = {asset["id"]: asset for asset in assets}
    for row in audit["assets"]:
        current = by_id[row["asset_id"]]
        svg = exact_pack_file(pack_dir, PurePosixPath(current["file"]), label="RNA Methods current SVG")
        row["sha256"] = sha256_bytes(svg.read_bytes())
        row["provenance_sha256"] = sha256_text(current["provenance"])
    return audit


def validate_rna_method_artwork_revision(pack: dict, pack_dir: Path) -> set[str]:
    """Bind four reviewed drawings to exact snapshots, science and the prior grant."""
    if not rna_method_artwork_revision_selected(pack):
        return set()
    prefix = RNA_METHOD_ARTWORK_PREDECESSOR
    snapshot = load_pack(exact_pack_file(pack_dir, PurePosixPath(f"{prefix}/snapshot.json"),
                                         label="RNA Methods predecessor snapshot"))
    if canonical_json_sha256(snapshot) != RNA_METHOD_PREDECESSOR_SNAPSHOT_SHA256:
        fail("RNA Methods predecessor snapshot exact identity mismatch")
    expected_snapshot_files = [{"file": name, "sha256": digest}
                               for name, digest in RNA_METHOD_PREDECESSOR_BYTE_PINS.items()]
    if (snapshot.get("schema_id") != "superbench.scientificAssetPredecessorSnapshot.v1"
            or snapshot.get("snapshot_date") != RNA_METHOD_ARTWORK_DATE
            or snapshot.get("files") != expected_snapshot_files):
        fail("RNA Methods predecessor snapshot finite file inventory mismatch")
    for name, digest in RNA_METHOD_PREDECESSOR_BYTE_PINS.items():
        path = exact_pack_file(pack_dir, PurePosixPath(f"{prefix}/{name}"), label="RNA Methods predecessor file")
        if sha256_bytes(path.read_bytes()) != digest:
            fail(f"{name}: RNA Methods predecessor exact byte identity mismatch")
    prior = load_pack(pack_dir / prefix / "asset-pack.json")
    prior_audit = load_pack(pack_dir / prefix / "rights-release-record.json")
    if (canonical_json_sha256(prior) != RNA_METHOD_PREDECESSOR_CATALOG_SHA256
            or canonical_json_sha256(prior_audit) != RNA_METHOD_PREDECESSOR_AUDIT_SHA256):
        fail("RNA Methods predecessor catalog or rights-audit canonical identity mismatch")
    receipt = load_pack(exact_pack_file(pack_dir, PurePosixPath(RNA_METHOD_ARTWORK_RECEIPT),
                                      label="RNA Methods artwork revision receipt"))
    if canonical_json_sha256(receipt) != RNA_METHOD_ARTWORK_RECEIPT_SHA256:
        fail("RNA Methods artwork revision receipt exact identity mismatch")
    expected_identity = {
        "schema_id": "superbench.scientificAssetArtworkRevision.v1",
        "revision_id": RNA_METHOD_ARTWORK_REVISION,
        "revision_date": RNA_METHOD_ARTWORK_DATE,
        "pack_id": RNA_METHOD_PACK_ID,
    }
    if (set(receipt) != {*expected_identity, "predecessor", "current_catalog_sha256", "review", "changed_assets"}
            or any(receipt.get(key) != value for key, value in expected_identity.items())):
        fail("RNA Methods artwork revision receipt identity or schema mismatch")
    if receipt.get("predecessor") != {
        "catalog_sha256": RNA_METHOD_PREDECESSOR_CATALOG_SHA256,
        "audit_sha256": RNA_METHOD_PREDECESSOR_AUDIT_SHA256,
        "snapshot": prefix,
    }:
        fail("RNA Methods artwork revision receipt predecessor mismatch")
    if receipt.get("current_catalog_sha256") != canonical_json_sha256(pack):
        fail("RNA Methods artwork receipt does not bind its current catalog")
    review = receipt.get("review")
    if (not isinstance(review, dict) or any(review.get(key) != value for key, value in
            {"status": "accepted", "scientific_review": "pass", "visual_review": "pass", "editor_checks": "pass"}.items())):
        fail("RNA Methods artwork refinement requires scientific, visual and native editor acceptance")
    evidence = review.get("evidence")
    if not isinstance(evidence, list) or not evidence:
        fail("RNA Methods artwork review must bind evidence records")
    evidence_files = set()
    for record in evidence:
        if not isinstance(record, dict) or set(record) != {"file", "sha256"}:
            fail("RNA Methods artwork evidence must contain file and sha256 records")
        relative = canonical_relative_file(record.get("file"), label="RNA Methods review evidence", suffix=".json").as_posix()
        if (not relative.startswith("qa_artifacts/") or relative.casefold() in evidence_files
                or not isinstance(record.get("sha256"), str) or not re.fullmatch(r"[0-9a-f]{64}", record["sha256"])):
            fail("RNA Methods artwork evidence path or identity mismatch")
        evidence_files.add(relative.casefold())
    allowed_catalog_fields = {"qa_status", "release_audit", "source_records", "assets", "artwork_revision", "artwork_revision_receipt"}
    if any(pack.get(key) != prior.get(key) for key in (set(pack) | set(prior)) - allowed_catalog_fields):
        fail("RNA Methods artwork refinement changed stable catalog or owner-grant metadata")
    if pack.get("qa_status") != RNA_METHOD_ARTWORK_QA_STATUS:
        fail("RNA Methods artwork QA status must identify the dated scientific and visual acceptance")
    expected_reference = {**prior["release_audit"], "audit_id": RNA_METHOD_ARTWORK_AUDIT_ID, "audit_date": RNA_METHOD_ARTWORK_DATE}
    if pack.get("release_audit") != expected_reference:
        fail("RNA Methods artwork revision must preserve its rights grant and pending product-release state")
    validate_rna_method_artwork_source(pack, prior)
    assets = pack.get("assets")
    previous_assets = prior["assets"]
    if (not isinstance(assets, list) or len(assets) != 4
            or [asset.get("id") for asset in assets] != list(RNA_METHOD_ARTWORK_FILES)
            or {asset["id"]: asset["file"] for asset in previous_assets} != RNA_METHOD_ARTWORK_FILES):
        fail("RNA Methods artwork revision must preserve its four ordered stable asset identities")
    rows = receipt.get("changed_assets")
    if (not isinstance(rows, list) or len(rows) != 4 or not all(isinstance(row, dict) for row in rows)
            or [row.get("asset_id") for row in rows] != list(RNA_METHOD_ARTWORK_FILES)):
        fail("RNA Methods artwork receipt must bind exactly four ordered refinements")
    for before, current, row in zip(previous_assets, assets, rows):
        asset_id = before["id"]
        if any(before.get(key) != current.get(key) for key in (set(before) | set(current)) - RNA_METHOD_ARTWORK_ASSET_FIELDS):
            fail(f"{asset_id}: RNA Methods refinement changed stable scientific or editable-region metadata")
        relative = RNA_METHOD_ARTWORK_FILES[asset_id]
        previous_svg = exact_pack_file(pack_dir, PurePosixPath(f"{prefix}/{relative}"), label="RNA Methods predecessor SVG")
        current_svg = exact_pack_file(pack_dir, PurePosixPath(relative), label="RNA Methods current SVG")
        before_hash, after_hash = sha256_bytes(previous_svg.read_bytes()), sha256_bytes(current_svg.read_bytes())
        if before_hash == after_hash:
            fail(f"{asset_id}: RNA Methods revision claims refinement without an SVG change")
        if rna_method_svg_paints(previous_svg) != rna_method_svg_paints(current_svg):
            fail(f"{asset_id}: RNA Methods refinement changed effective semantic paints")
        if row != {"asset_id": asset_id, "file": relative, "before_svg_sha256": before_hash,
                   "after_svg_sha256": after_hash, "before_metadata_sha256": canonical_json_sha256(before),
                   "after_metadata_sha256": canonical_json_sha256(current), "license": "CC0-1.0"}:
            fail(f"{asset_id}: RNA Methods artwork receipt SVG or metadata identity mismatch")
    audit = load_pack(exact_pack_file(pack_dir, PurePosixPath("rights-release-record.json"), label="RNA Methods current rights audit"))
    if (audit.get("audit_id") != RNA_METHOD_ARTWORK_AUDIT_ID or audit.get("audit_date") != RNA_METHOD_ARTWORK_DATE
            or canonical_json_sha256(audit) != RNA_METHOD_ARTWORK_AUDIT_SHA256):
        fail("RNA Methods artwork revision rights-audit exact identity mismatch")
    notice = exact_pack_file(pack_dir, PurePosixPath("LICENSE-ASSETS-CC0-1.0.md"), label="RNA Methods current CC0 notice")
    if sha256_bytes(notice.read_bytes()) != RNA_METHOD_PREDECESSOR_BYTE_PINS["LICENSE-ASSETS-CC0-1.0.md"]:
        fail("RNA Methods artwork refinement must preserve its original CC0 notice")
    if canonical_json_sha256(pack) != RNA_METHOD_ARTWORK_CATALOG_SHA256:
        fail("RNA Methods artwork revision catalog exact identity mismatch")
    return {*RNA_METHOD_ARTWORK_PREDECESSOR_FILES, RNA_METHOD_ARTWORK_RECEIPT}


def protein_product_release_selected(pack: dict) -> bool:
    """Select only the explicitly implemented Protein product qualification."""
    reference = pack.get("release_audit") or {}
    selected = pack.get("id") == PROTEIN_PACK_ID and reference.get("status") == "released"
    if "product_release_receipt" in pack and not selected:
        fail("Unknown scientific product-release receipt requires a reviewed implementation")
    return selected


def protein_product_release_identity(pack: dict) -> None:
    expected = {
        "audit_id": PROTEIN_PRODUCT_RELEASE_ID,
        "audit_date": PROTEIN_PRODUCT_RELEASE_DATE,
        "release_effective_date": PROTEIN_PRODUCT_RELEASE_DATE,
        "rights_grant_effective_date": "2026-10-10",
        "product_release_status": "released",
        "status": "released",
        "asset_count": 8,
        "concept_count": 8,
        "public_distribution_authorized": True,
        "selected_public_license": "CC0-1.0",
        "file": "rights-release-record.json",
        "license_notice": "LICENSE-ASSETS-CC0-1.0.md",
    }
    if (pack.get("id") != PROTEIN_PACK_ID
            or pack.get("product_release_receipt") != PROTEIN_PRODUCT_RELEASE_RECEIPT
            or any(pack.get("release_audit", {}).get(key) != value for key, value in expected.items())):
        fail("Protein Homeostasis qualified product-release identity or date mismatch")


def protein_product_release_audit_binding(receipt: dict) -> dict:
    return {
        "release_id": PROTEIN_PRODUCT_RELEASE_ID,
        "receipt": PROTEIN_PRODUCT_RELEASE_RECEIPT,
        "receipt_sha256": canonical_json_sha256(receipt),
        "predecessor": receipt["predecessor"],
        "asset_ids": [row["asset_id"] for row in receipt["assets"]],
        "contour_refinement_record_id": PROTEIN_CONTOUR_REFINEMENT_RECORD_ID,
    }


def validate_protein_contour_source(pack: dict, prior: dict, changed_ids: list[str]) -> None:
    """A bounded new drawing record supplements the exact original science record."""
    sources = pack.get("source_records")
    if (not isinstance(sources, list) or len(sources) != 2
            or sources[:1] != prior.get("source_records")):
        fail("Protein Homeostasis contour refinement must preserve the exact original source-record prefix")
    refinement = sources[1]
    expected = {
        "id": PROTEIN_CONTOUR_REFINEMENT_RECORD_ID,
        "kind": "original_vector_contour_refinement_record",
        "parent_source_record_id": PROTEIN_SOURCE_RECORD_ID,
        "pack_id": PROTEIN_PACK_ID,
        "scope": "exact_asset_ids",
        "asset_ids": changed_ids,
        "created_on": PROTEIN_PRODUCT_RELEASE_DATE,
        "third_party_material": "none_declared",
    }
    if (not isinstance(refinement, dict)
            or set(refinement) != {*expected, "generated_by", "statement"}
            or any(refinement.get(key) != value for key, value in expected.items())):
        fail("Protein Homeostasis contour-refinement source identity, scope or parent mismatch")
    for field, minimum in (("generated_by", 10), ("statement", 80)):
        if not isinstance(refinement.get(field), str) or len(refinement[field].strip()) < minimum:
            fail(f"Protein Homeostasis contour-refinement source {field} must be substantive")
    if re.search(r"[A-Za-z]:\\", json.dumps(refinement)):
        fail("Protein Homeostasis contour-refinement record must not expose absolute local Windows paths")


def validate_protein_contour_svg(before_path: Path, current_path: Path, *, asset_id: str) -> None:
    """Refit sampled path contours only; retain paints, regions and SVG structure."""
    old_elements = list(ET.fromstring(before_path.read_bytes()).iter())
    new_elements = list(ET.fromstring(current_path.read_bytes()).iter())
    if len(old_elements) != len(new_elements):
        fail(f"{asset_id}: contour refinement changed SVG element inventory")
    changed_paths = 0
    for old, new in zip(old_elements, new_elements):
        old_attrs, new_attrs = dict(old.attrib), dict(new.attrib)
        if local_name(old.tag) == "path" and old_attrs.get("d") != new_attrs.get("d"):
            before_d, after_d = old_attrs.pop("d", ""), new_attrs.pop("d", "")
            before_commands = re.findall(r"[A-Za-z]", before_d)
            after_commands = re.findall(r"[A-Za-z]", after_d)
            if (set(before_commands) != {"M", "L", "Z"}
                    or set(after_commands) != {"M", "C", "Z"}
                    or before_commands.count("M") != 1 or before_commands.count("Z") != 1
                    or after_commands.count("M") != 1 or after_commands.count("Z") != 1
                    or before_commands.count("L") < 12
                    or after_commands.count("C") >= before_commands.count("L")):
                fail(f"{asset_id}: contour refinement must only compact sampled closed L contours into cubic paths")
            changed_paths += 1
        if (old.tag != new.tag or old_attrs != new_attrs or len(old) != len(new)
                or (old.text or "").strip() != (new.text or "").strip()
                or (old.tail or "").strip() != (new.tail or "").strip()):
            fail(f"{asset_id}: contour refinement changed non-path geometry, paints, regions or SVG structure")
    if not changed_paths:
        fail(f"{asset_id}: contour refinement must change at least one sampled path")


def validate_protein_product_release(pack: dict, pack_dir: Path) -> set[str]:
    """Bind the reviewed contour refinement to its preserved grant and science."""
    protein_product_release_identity(pack)
    receipt = load_pack(exact_pack_file(pack_dir, PurePosixPath(PROTEIN_PRODUCT_RELEASE_RECEIPT),
                                      label="Protein Homeostasis product-release receipt"))
    if canonical_json_sha256(receipt) != PROTEIN_PRODUCT_RECEIPT_SHA256:
        fail("Protein Homeostasis product-release receipt exact identity mismatch")
    if (receipt.get("schema_id") != "superbench.scientificAssetProductRelease.v1"
            or receipt.get("release_id") != PROTEIN_PRODUCT_RELEASE_ID
            or receipt.get("release_date") != PROTEIN_PRODUCT_RELEASE_DATE
            or receipt.get("pack_id") != PROTEIN_PACK_ID
            or receipt.get("owner_grant_record_id") != PROTEIN_OWNER_GRANT_RECORD_ID
            or receipt.get("scientific_source_record_id") != PROTEIN_SOURCE_RECORD_ID
            or receipt.get("contour_refinement_record_id") != PROTEIN_CONTOUR_REFINEMENT_RECORD_ID):
        fail("Protein Homeostasis product-release receipt identity or date mismatch")
    review = receipt.get("review") or {}
    if (review.get("status") != "accepted" or review.get("visual_review") != "pass"
            or review.get("editor_checks") != "pass"
            or review.get("reviewed_on") != PROTEIN_PRODUCT_RELEASE_DATE):
        fail("Protein Homeostasis product release requires accepted visual and editor reviews")
    for field, minimum in (("reviewer", 10), ("scope", 40)):
        if not isinstance(review.get(field), str) or len(review[field].strip()) < minimum:
            fail(f"Protein Homeostasis product-release review {field} must be substantive")
    if review.get("evidence") != "docs/scientific-assets/PROTEIN_HOMEOSTASIS_QUALIFICATION_2026_10_11.md":
        fail("Protein Homeostasis product-release review must reference its tracked acceptance document")
    evidence_records = review.get("evidence_records")
    if not isinstance(evidence_records, list) or len(evidence_records) < 2:
        fail("Protein Homeostasis product-release review must bind native and independent evidence records")
    evidence_paths = set()
    for record in evidence_records:
        if not isinstance(record, dict):
            fail("Protein Homeostasis product-release evidence records must be objects")
        relative = canonical_relative_file(record.get("file"), label="product-release evidence", suffix=".json").as_posix()
        if (not relative.startswith("qa_artifacts/protein-homeostasis-qualification-20261011/")
                or relative in evidence_paths
                or not isinstance(record.get("sha256"), str)
                or not re.fullmatch(r"[0-9a-f]{64}", record["sha256"])):
            fail("Protein Homeostasis product-release evidence record path or digest mismatch")
        evidence_paths.add(relative)
    prior = load_pack(exact_pack_file(pack_dir,
        PurePosixPath(f"{PROTEIN_PREDECESSOR_PREFIX}/asset-pack.json"), label="Protein Homeostasis predecessor catalog"))
    prior_audit = load_pack(exact_pack_file(pack_dir,
        PurePosixPath(f"{PROTEIN_PREDECESSOR_PREFIX}/rights-release-record.json"), label="Protein Homeostasis predecessor rights audit"))
    prior_notice = exact_pack_file(pack_dir,
        PurePosixPath(f"{PROTEIN_PREDECESSOR_PREFIX}/LICENSE-ASSETS-CC0-1.0.md"), label="Protein Homeostasis predecessor notice")
    for label, actual, expected in (
        ("catalog", canonical_json_sha256(prior), PROTEIN_PREDECESSOR_CATALOG_SHA256),
        ("rights audit", canonical_json_sha256(prior_audit), PROTEIN_PREDECESSOR_AUDIT_SHA256),
        ("notice", sha256_svg_bytes(prior_notice.read_bytes()), PROTEIN_PREDECESSOR_NOTICE_SHA256),
    ):
        if actual != expected:
            fail(f"Protein Homeostasis predecessor {label} exact identity mismatch")
    expected_predecessor = {
        "audit_id": PROTEIN_PREDECESSOR_AUDIT_ID,
        "catalog_sha256": PROTEIN_PREDECESSOR_CATALOG_SHA256,
        "audit_sha256": PROTEIN_PREDECESSOR_AUDIT_SHA256,
        "license_notice_sha256": PROTEIN_PREDECESSOR_NOTICE_SHA256,
        "snapshot": PROTEIN_PREDECESSOR_PREFIX,
    }
    if receipt.get("predecessor") != expected_predecessor:
        fail("Protein Homeostasis product-release receipt predecessor mismatch")
    if receipt.get("current_catalog_sha256") != canonical_json_sha256(pack):
        fail("Protein Homeostasis product-release receipt does not bind its current catalog")
    if canonical_json_sha256(pack) != PROTEIN_PRODUCT_CATALOG_SHA256:
        fail("Protein Homeostasis qualified catalog exact identity mismatch")
    notice = exact_pack_file(pack_dir, PurePosixPath("LICENSE-ASSETS-CC0-1.0.md"), label="Protein Homeostasis released notice")
    if receipt.get("current_license_notice_sha256") != sha256_svg_bytes(notice.read_bytes()):
        fail("Protein Homeostasis product-release receipt does not bind its current notice")
    if any(pack.get(key) != prior.get(key) for key in (set(pack) | set(prior)) - PROTEIN_CATALOG_RELEASE_FIELDS):
        fail("Protein Homeostasis product release changed stable catalog, source or owner-grant metadata")
    expected_license_definitions = json.loads(json.dumps(prior["license_definitions"]))
    expected_license_definitions["CC0-1.0"]["release_status"] = "released"
    if pack.get("license_definitions") != expected_license_definitions:
        fail("Protein Homeostasis product qualification must preserve license terms apart from release status")
    if pack.get("qa_status") != PROTEIN_QUALIFIED_QA_STATUS:
        fail("Protein Homeostasis qualified QA status must identify the accepted dated native and visual review")
    prior_assets = prior["assets"]
    current_assets = pack["assets"]
    if (len(current_assets) != 8 or [a["id"] for a in current_assets] != [a["id"] for a in prior_assets]
            or {a["id"]: a["file"] for a in prior_assets} != PROTEIN_CONTOUR_FILES):
        fail("Protein Homeostasis product release must retain exactly the eight prior asset identities")
    rows = receipt.get("assets")
    if not isinstance(rows, list) or len(rows) != 8 or not all(isinstance(row, dict) for row in rows):
        fail("Protein Homeostasis product-release receipt must name exactly eight assets")
    row_by_id = {row.get("asset_id"): row for row in rows}
    if set(row_by_id) != {a["id"] for a in prior_assets}:
        fail("Protein Homeostasis product-release receipt asset identities mismatch")
    prior_audit_by_id = {row["asset_id"]: row for row in prior_audit["assets"]}
    changed_ids = []
    for before, current in zip(prior_assets, current_assets):
        asset_id = before["id"]
        if (set(current) != set(before)
                or any(current.get(key) != before.get(key) for key in set(before) - PROTEIN_RELEASE_ASSET_FIELDS)):
            fail(f"{asset_id}: product release changed stable scientific or editable-region metadata")
        expected_quality = {
            "review_status": PROTEIN_QUALIFIED_QA_STATUS,
            "style_status": "soft_line_v1_independently_qualified",
            "mvp_quality": "curated_beta", "quality_tier": "beta_curated",
        }
        if any(current.get(key) != value for key, value in expected_quality.items()):
            fail(f"{asset_id}: product qualification must use the accepted quality status")
        # The historical creation statement stays intact; only its final product
        # status sentence changes. The exact accepted receipt binds that new copy.
        prefix = before["provenance"].removesuffix("product-level release approval remains pending.")
        if (not current["provenance"].startswith(prefix)
                or PROTEIN_PRODUCT_RELEASE_DATE not in current["provenance"][len(prefix):]):
            fail(f"{asset_id}: product release changed original construction or CC0 grant provenance")
        svg = exact_pack_file(pack_dir, PurePosixPath(before["file"]), label=f"{asset_id}: qualified SVG")
        prior_svg = exact_pack_file(pack_dir, PurePosixPath(f"{PROTEIN_PREDECESSOR_PREFIX}/{before['file']}"),
                                    label=f"{asset_id}: predecessor SVG")
        before_hash = sha256_svg_bytes(prior_svg.read_bytes())
        after_hash = sha256_svg_bytes(svg.read_bytes())
        if before_hash != prior_audit_by_id[asset_id]["sha256"]:
            fail(f"{asset_id}: predecessor SVG exact identity mismatch")
        if before_hash == after_hash:
            fail(f"{asset_id}: approved contour-refinement receipt must identify a changed SVG")
        validate_protein_contour_svg(prior_svg, svg, asset_id=asset_id)
        changed_ids.append(asset_id)
        if current.get("source_record_id") != PROTEIN_CONTOUR_REFINEMENT_RECORD_ID:
            fail(f"{asset_id}: contour-refined asset must reference its declared refinement source")
        changes = {key: {"before": before.get(key), "after": current.get(key)}
                   for key in sorted(PROTEIN_RELEASE_ASSET_FIELDS) if before.get(key) != current.get(key)}
        expected = {
            "asset_id": asset_id, "file": before["file"],
            "before_svg_sha256": before_hash, "after_svg_sha256": after_hash,
            "before_metadata_sha256": canonical_json_sha256(before),
            "after_metadata_sha256": canonical_json_sha256(current),
            "source_record_id": PROTEIN_CONTOUR_REFINEMENT_RECORD_ID,
            "rights_record_id": PROTEIN_OWNER_GRANT_RECORD_ID,
            "metadata_changes": changes,
        }
        if row_by_id[asset_id] != expected:
            fail(f"{asset_id}: product-release receipt asset identity or declared refinement changes mismatch")
    validate_protein_contour_source(pack, prior, changed_ids)
    return {*PROTEIN_PREDECESSOR_FILES, PROTEIN_PRODUCT_RELEASE_RECEIPT}


def validate_iso_date(value: object, *, label: str) -> date:
    if not isinstance(value, str) or not ISO_DATE.fullmatch(value):
        fail(f"{label} must use YYYY-MM-DD")
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        fail(f"{label} is not a valid calendar date")
    if parsed > date.today():
        fail(f"{label} cannot be in the future")
    return parsed


def validate_draft_audit(pack: dict, pack_dir: Path, assets: list[dict]) -> str:
    """Validate local draft inclusion without inventing a public release decision."""
    reference = pack["release_audit"]
    missing = RELEASE_AUDIT_REFERENCE_FIELDS - reference.keys()
    if missing:
        fail(f"draft audit reference missing fields: {sorted(missing)}")
    audit_path = exact_pack_file(pack_dir, canonical_relative_file(
        reference["file"], label="draft audit file", suffix=".json"), label="draft audit file")
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    missing = RELEASE_AUDIT_REQUIRED_FIELDS - audit.keys()
    if missing:
        fail(f"draft audit missing fields: {sorted(missing)}")
    expected = {
        "schema_id": "figureStudio.scientificAssetLicenseReleaseAudit.v1",
        "pack_id": pack["id"], "status": "draft_review_pending",
        "asset_count": len(assets), "concept_count": pack["concept_count"],
        "rights_cleared_count": 0, "license_selection_pending_count": len(assets),
        "public_distribution_authorized": False, "selected_public_license": None,
        "release_effective_date": None, "third_party_component_count": 0,
    }
    for key, value in expected.items():
        if audit.get(key) != value:
            fail(f"draft audit {key} must be {value!r}")
    if audit["public_distribution_authorized"] is not False or reference.get("public_distribution_authorized") is not False:
        fail("draft public_distribution_authorized must be boolean false")
    for key in ("audit_id", "audit_date", "status", "asset_count", "concept_count",
                "public_distribution_authorized", "selected_public_license",
                "release_effective_date", "license_notice"):
        if reference.get(key) != audit.get(key):
            fail(f"draft audit {key} does not match pack reference")
    if not str(audit["audit_id"]).startswith(pack["id"] + "."):
        fail("draft audit identity must be scoped to its pack")
    validate_iso_date(audit["audit_date"], label="draft audit date")
    exact_pack_file(pack_dir, canonical_relative_file(
        audit["license_notice"], label="draft notice", suffix=".md"), label="draft notice")
    if audit.get("source_records") != pack["source_records"] or audit.get("rights_records") != pack["rights_records"]:
        fail("draft audit source and rights records must match the pack")
    basis = audit.get("rights_basis") or {}
    if (basis.get("status") != "original_output_pending_owner_review"
            or basis.get("pack_id") != pack["id"]
            or basis.get("authorization_record_id") != pack["rights_records"][0]["id"]):
        fail("draft audit rights basis must retain pending owner review")
    if not isinstance(audit.get("release_blocker"), str) or not audit["release_blocker"].strip():
        fail("draft audit must explain the pending public-release decision")
    candidates = audit.get("license_candidates")
    if not isinstance(candidates, list) or any(item.get("selected") for item in candidates):
        fail("draft audit cannot select a public license")
    rows = audit.get("assets")
    if not isinstance(rows, list) or len(rows) != len(assets):
        fail("draft audit must cover every asset exactly once")
    by_id = {row.get("asset_id"): row for row in rows if isinstance(row, dict)}
    if len(by_id) != len(rows) or set(by_id) != {asset["id"] for asset in assets}:
        fail("draft audit identities must match the pack exactly")
    for asset in assets:
        row = by_id[asset["id"]]
        if RELEASE_ASSET_REQUIRED_FIELDS - row.keys():
            fail(f"{asset['id']}: draft audit entry is incomplete")
        draft_lineages = {"original_vector_draft": "workspace_generated_original",
                          "clean_room_original_vector": "workspace_generated_clean_room_original"}
        if asset["source_type"] not in draft_lineages or row.get("lineage") != draft_lineages[asset["source_type"]]:
            fail(f"{asset['id']}: local draft inclusion supports declared original vectors only")
        expected_row = {
            "file": asset["file"], "source_type": asset["source_type"],
            "source_record_id": asset["source_record_id"], "rights_record_id": asset["rights_record_id"],
            "current_license": "FS-ORIGINAL-DRAFT", "third_party_material": "none_declared",
            "rights_basis": "original_output_pending_owner_review",
            "provenance_status": "original_draft_review_pending",
            "release_disposition": "draft_not_authorized_for_public_distribution",
            "sha256": sha256_bytes((pack_dir / asset["file"]).read_bytes()),
            "provenance_sha256": sha256_text(asset["provenance"]),
        }
        if asset["license"] != "FS-ORIGINAL-DRAFT":
            fail(f"{asset['id']}: draft asset cannot claim a released license")
        for key, value in expected_row.items():
            if row.get(key) != value:
                fail(f"{asset['id']}: draft audit {key} does not match current source / draft rights")
    return "draft_review_pending"


def validate_rights_cleared_quality_pending_audit(
    pack: dict, pack_dir: Path, assets: list[dict]
) -> str:
    """Validate an owner CC0 grant while keeping product-release approval pending."""
    reference = pack["release_audit"]
    audit_path = exact_pack_file(
        pack_dir,
        canonical_relative_file(
            reference["file"], label="rights-cleared audit file", suffix=".json"
        ),
        label="rights-cleared audit file",
    )
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    expected = {
        "schema_id": "figureStudio.scientificAssetLicenseReleaseAudit.v1",
        "pack_id": pack["id"],
        "status": "rights_cleared_quality_pending",
        "asset_count": len(assets),
        "concept_count": pack["concept_count"],
        "rights_cleared_count": len(assets),
        "license_selection_pending_count": 0,
        "public_distribution_authorized": True,
        "selected_public_license": "CC0-1.0",
        "release_effective_date": None,
        "product_release_status": "pending_quality_and_product_review",
        "third_party_component_count": 0,
    }
    for key, value in expected.items():
        if audit.get(key) != value:
            fail(f"rights-cleared audit {key} must be {value!r}")
    if (
        reference.get("status") != audit.get("status")
        or reference.get("public_distribution_authorized") is not True
        or reference.get("selected_public_license") != "CC0-1.0"
        or reference.get("product_release_status") != "pending_quality_and_product_review"
        or reference.get("rights_grant_effective_date")
        != audit.get("rights_grant_effective_date")
    ):
        fail("pack rights grant and product-release states must match the audit")
    validate_iso_date(
        audit.get("rights_grant_effective_date"), label="rights grant effective date"
    )
    audit_date = validate_iso_date(audit.get("audit_date"), label="rights-cleared audit date")
    if validate_iso_date(
        pack["source_records"][0].get("created_on"), label="source record created_on"
    ) > audit_date:
        fail("rights-cleared audit cannot predate its source record")
    exact_pack_file(
        pack_dir,
        canonical_relative_file(
            audit.get("license_notice"), label="CC0 license notice", suffix=".md"
        ),
        label="CC0 license notice",
    )
    if audit.get("source_records") != pack.get("source_records"):
        fail("rights-cleared audit source records must match the pack")
    if audit.get("rights_records") != pack.get("rights_records"):
        fail("rights-cleared audit rights records must match the pack")
    rights = pack.get("rights_records") or []
    basis = audit.get("rights_basis") or {}
    if (
        len(rights) != 1
        or basis.get("status") != "owner_attested_original_output"
        or basis.get("pack_id") != pack["id"]
        or basis.get("authorization_record_id") != rights[0].get("id")
        or basis.get("qualification") != rights[0].get("qualification")
    ):
        fail("rights-cleared audit must bind the owner grant to this pack")
    if not isinstance(audit.get("release_blocker"), str) or "Product-level release approval remains pending" not in audit["release_blocker"]:
        fail("rights-cleared audit must retain the separate product-release blocker")
    candidates = audit.get("license_candidates")
    if (
        not isinstance(candidates, list)
        or len(candidates) != 1
        or candidates[0].get("id") != "CC0-1.0"
        or candidates[0].get("selected") is not True
    ):
        fail("rights-cleared audit must identify the single selected CC0 grant")
    rows = audit.get("assets")
    if not isinstance(rows, list) or len(rows) != len(assets):
        fail("rights-cleared audit must cover every asset exactly once")
    by_id = {row.get("asset_id"): row for row in rows if isinstance(row, dict)}
    if len(by_id) != len(rows) or set(by_id) != {asset["id"] for asset in assets}:
        fail("rights-cleared audit identities must match the pack exactly")
    for asset in assets:
        row = by_id[asset["id"]]
        expected_row = {
            "file": asset["file"],
            "source_type": asset["source_type"],
            "source_record_id": asset["source_record_id"],
            "rights_record_id": asset["rights_record_id"],
            "current_license": "CC0-1.0",
            "third_party_material": "none_declared",
            "rights_basis": "owner_attested_original_output",
            "provenance_status": "owner_attested",
            "release_disposition": "licensed_under_cc0_1_0_product_release_pending",
            "sha256": sha256_bytes((pack_dir / asset["file"]).read_bytes()),
            "provenance_sha256": sha256_text(asset["provenance"]),
        }
        if asset["license"] != "CC0-1.0":
            fail(f"{asset['id']}: rights-cleared asset must use CC0-1.0")
        for key, value in expected_row.items():
            if row.get(key) != value:
                fail(f"{asset['id']}: rights-cleared audit {key} does not match the pack")
    return "rights_cleared_quality_pending"


def validate_release_audit(pack: dict, pack_dir: Path, assets: list[dict]) -> str:
    contribution = policy_contribution(pack)
    if pack.get("release_audit", {}).get("status") == "draft_review_pending":
        if pack.get("id") in {CORE_PACK_ID, EXPANSION_PACK_ID, IMMUNOLOGY_ONCOLOGY_PACK_ID}:
            fail("historical released packs cannot be downgraded to draft")
        return validate_draft_audit(pack, pack_dir, assets)
    if pack.get("release_audit", {}).get("status") == "rights_cleared_quality_pending" and not contribution:
        if pack.get("id") in {CORE_PACK_ID, EXPANSION_PACK_ID, IMMUNOLOGY_ONCOLOGY_PACK_ID}:
            fail("historical released packs cannot be downgraded to pending quality release")
        return validate_rights_cleared_quality_pending_audit(pack, pack_dir, assets)
    reference = pack.get("release_audit")
    if not isinstance(reference, dict):
        fail("release_audit must be an object")
    missing_reference = RELEASE_AUDIT_REFERENCE_FIELDS - reference.keys()
    if missing_reference:
        fail(f"release_audit reference missing fields: {sorted(missing_reference)}")

    relative_audit = canonical_relative_file(reference["file"], label="release_audit.file", suffix=".json")
    audit_path = exact_pack_file(pack_dir, relative_audit, label="release audit file")
    try:
        audit = json.loads(audit_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        fail(f"{audit_path}: invalid release-audit JSON: {error}")

    missing = RELEASE_AUDIT_REQUIRED_FIELDS - audit.keys()
    if missing:
        fail(f"release audit missing fields: {sorted(missing)}")
    if audit.get("schema_id") != "figureStudio.scientificAssetLicenseReleaseAudit.v1":
        fail("release audit has an unsupported schema_id")
    core_pin = core_release_pin(pack) if pack.get("id") == CORE_PACK_ID else None
    if core_pin and (
        audit.get("audit_id") != core_pin["id"]
        or audit.get("audit_date") != core_pin["date"]
        or audit.get("release_effective_date") != core_pin["date"]
        or audit.get("asset_count") != core_pin.get("count", CORE_ASSET_COUNT)
    ):
        fail("Core Biology release-audit identity and date must match its exact approved revision")
    if audit.get("audit_id") != reference.get("audit_id"):
        fail("release audit audit_id does not match the pack reference")
    if not str(audit.get("audit_id") or "").startswith(f"{pack.get('id')}."):
        fail("release audit audit_id must be scoped to its own pack id")
    if audit.get("pack_id") != pack.get("id"):
        fail("release audit pack_id does not match the asset pack")
    if audit.get("status") != reference.get("status"):
        fail("release audit status does not match the pack reference")
    if audit.get("asset_count") != reference.get("asset_count") or audit.get("asset_count") != len(assets):
        fail("release audit asset_count does not match the pack")
    if audit.get("public_distribution_authorized") is not reference.get("public_distribution_authorized"):
        fail("release audit public-distribution state does not match the pack reference")
    if audit.get("status") != ("rights_cleared_quality_pending" if contribution else "released"):
        fail("release audit must match its recorded license basis and separate product disposition")
    audit_date = validate_iso_date(audit.get("audit_date"), label="release audit audit_date")
    effective_date = validate_iso_date(
        audit.get("rights_grant_effective_date") if contribution else audit.get("release_effective_date"),
        label="contribution license effective date" if contribution else "release audit release_effective_date"
    )
    if contribution and (audit.get("release_effective_date") is not None
            or reference.get("release_effective_date") is not None
            or audit.get("product_release_status") != "pending_quality_and_product_review"
            or reference.get("product_release_status") != "pending_quality_and_product_review"):
        fail("Prospective contribution license clearance must preserve separate pending product approval")
    if contribution and (audit.get("rights_grant_effective_date") != "2026-10-15"
            or reference.get("rights_grant_effective_date") != "2026-10-15"
            or audit.get("audit_date") != "2026-10-15"
            or reference.get("audit_date") != "2026-10-15"):
        fail("Prospective contribution audit and license must use their current 2026-10-15 date")
    if contribution and (not isinstance(audit.get("product_release_blocker"), str)
            or len(audit["product_release_blocker"].strip()) < 40
            or "product_release" in audit):
        fail("Prospective contribution audit must state its separate pending product qualification")
    if effective_date > audit_date:
        fail("release audit release_effective_date cannot be later than audit_date")
    if reference.get("audit_date") is not None and reference.get("audit_date") != audit.get("audit_date"):
        fail("release audit audit_date does not match the pack reference")
    if (
        reference.get("release_effective_date") is not None
        and reference.get("release_effective_date") != audit.get("release_effective_date")
    ):
        fail("release audit release_effective_date does not match the pack reference")
    if audit.get("public_distribution_authorized") is not True or audit.get("selected_public_license") != "CC0-1.0":
        fail("released audit must authorize distribution under CC0-1.0")
    if reference.get("selected_public_license") != "CC0-1.0":
        fail("pack release_audit reference must select CC0-1.0")
    if audit.get("license_notice") != reference.get("license_notice"):
        fail("release audit license notice does not match the pack reference")
    relative_license = canonical_relative_file(audit.get("license_notice"), label="release audit license_notice", suffix=".md")
    exact_pack_file(pack_dir, relative_license, label="release audit CC0 license notice")
    if audit.get("rights_cleared_count") != len(assets):
        fail("release audit rights_cleared_count must cover every asset")
    if audit.get("license_selection_pending_count") != 0:
        fail("released audit cannot retain pending license selections")
    if audit.get("third_party_component_count") != 0:
        fail("release audit currently expects zero declared third-party components")
    rights_basis = audit.get("rights_basis")
    expected_basis = "repository_policy_original_output" if contribution else "owner_attested_original_output"
    if not isinstance(rights_basis, dict) or rights_basis.get("status") != expected_basis:
        fail(f"release audit rights_basis must record {expected_basis}")
    is_modern_pack = pack.get("id") != CORE_PACK_ID
    if is_modern_pack:
        concept_count = len(
            {str(asset.get("concept_id") or asset.get("id")) for asset in assets}
        )
        if audit.get("concept_count") != concept_count:
            fail("modern-pack release audit concept_count does not match the pack")
        if (
            reference.get("concept_count") is not None
            and reference.get("concept_count") != concept_count
        ):
            fail("modern-pack release-audit reference concept_count does not match the pack")
        if rights_basis.get("pack_id") != pack.get("id"):
            fail("modern-pack release audit rights_basis must be scoped to its own pack")
        pack_rights_records = pack.get("rights_records") or []
        if (
            len(pack_rights_records) != 1
            or rights_basis.get("authorization_record_id")
            != pack_rights_records[0].get("id")
            or rights_basis.get("qualification")
            != pack_rights_records[0].get("qualification")
        ):
            fail(
                "modern-pack release audit rights_basis must reference its pack-scoped authorization"
            )

    source_records = audit.get("source_records")
    if not isinstance(source_records, list) or not source_records:
        fail("release audit source_records must be a non-empty list")
    source_record_ids = {record.get("id") for record in source_records if isinstance(record, dict)}
    if pack.get("id") == CORE_PACK_ID:
        required_source_records = {
            "owner-attestation-2026-07-19",
            "owner-cc0-selection-2026-07-19",
            "model-organism-promotion-review-2026-07-20",
            "openai-terms-output-ownership-2026-01-01",
            "openai-services-agreement-output-ownership-2026-01-01",
        }
        if not required_source_records.issubset(source_record_ids):
            fail("Core Biology release audit is missing its historical owner-attestation or OpenAI ownership records")
    elif str(audit.get("audit_id") or "").startswith("core-biology."):
        fail("a non-Core Biology pack must use its own release-audit identity")
    if re.search(r"[A-Za-z]:\\", json.dumps(source_records)):
        fail("release audit source records must not expose absolute local Windows paths")
    if is_modern_pack:
        pack_source_record_ids = validate_record_table(
            pack, "source_records", required=True
        )
        if source_record_ids != pack_source_record_ids:
            fail("modern-pack release-audit source_records do not match pack source_records")
        audit_source_by_id = {
            record["id"]: record for record in source_records if isinstance(record, dict)
        }
        pack_source_by_id = {
            record["id"]: record
            for record in pack.get("source_records", [])
            if isinstance(record, dict)
        }
        if audit_source_by_id != pack_source_by_id:
            fail(
                "modern-pack release-audit source record content does not match pack source_records"
            )
        audit_rights_record_ids = validate_record_table(
            audit, "rights_records", required=True
        )
        pack_rights_record_ids = validate_record_table(
            pack, "rights_records", required=True
        )
        if audit_rights_record_ids != pack_rights_record_ids:
            fail("modern-pack release-audit rights_records do not match pack rights_records")
        audit_rights_by_id = {
            record["id"]: record
            for record in audit.get("rights_records", [])
            if isinstance(record, dict)
        }
        pack_rights_by_id = {
            record["id"]: record
            for record in pack.get("rights_records", [])
            if isinstance(record, dict)
        }
        if audit_rights_by_id != pack_rights_by_id:
            fail(
                "modern-pack release-audit rights record content does not match pack rights_records"
            )

    candidates = audit.get("license_candidates")
    if not isinstance(candidates, list) or not candidates or not all(isinstance(item, dict) for item in candidates):
        fail("release audit license_candidates must be a non-empty list of objects")
    candidate_ids = {candidate.get("id") for candidate in candidates}
    if len(candidate_ids) != len(candidates) or None in candidate_ids:
        fail("release audit license_candidates must use unique non-empty ids")
    if pack.get("id") == CORE_PACK_ID and candidate_ids != {
        "CC0-1.0",
        "CC-BY-4.0",
        "BSD-STUDIO-ASSET-USE-1.0-PROPOSED",
    }:
        fail("Core Biology release audit must retain its reviewed license-candidate set")
    if pack.get("id") == CORE_PACK_ID and not all(
        candidate.get("owner_action_required") is True for candidate in candidates
    ):
        fail("Core Biology license candidates must retain explicit owner-action records")
    selected_candidates = [candidate.get("id") for candidate in candidates if candidate.get("selected") is True]
    if selected_candidates != [audit.get("selected_public_license")]:
        fail("release audit must mark only selected_public_license as selected")
    blocker = audit.get("release_blocker")
    if blocker is not None:
        fail("released audit cannot retain a release blocker")

    audit_assets = audit.get("assets")
    if not isinstance(audit_assets, list):
        fail("release audit assets must be a list")
    audit_by_id: dict[str, dict] = {}
    audit_files: dict[str, str] = {}
    for entry in audit_assets:
        if not isinstance(entry, dict):
            fail("release audit asset entries must be objects")
        missing_entry = RELEASE_ASSET_REQUIRED_FIELDS - entry.keys()
        if is_modern_pack:
            missing_entry |= {"source_record_id", "rights_record_id"} - entry.keys()
        if missing_entry:
            fail(f"release audit asset entry missing fields: {sorted(missing_entry)}")
        asset_id = entry.get("asset_id")
        if asset_id in audit_by_id:
            fail(f"release audit contains duplicate asset_id {asset_id!r}")
        audit_file = canonical_relative_file(entry.get("file"), label=f"{asset_id}: release audit file", suffix=".svg").as_posix()
        prior_file = audit_files.get(audit_file.casefold())
        if prior_file is not None:
            fail(f"release audit contains duplicate or case-equivalent SVG paths for {prior_file} and {asset_id}")
        audit_files[audit_file.casefold()] = str(asset_id)
        audit_by_id[asset_id] = entry

    pack_by_id = {asset["id"]: asset for asset in assets}
    if set(audit_by_id) != set(pack_by_id):
        fail("release audit asset ids do not exactly match the pack")

    identity_mismatches: list[str] = []
    for asset_id, asset in pack_by_id.items():
        entry = audit_by_id[asset_id]
        svg_path = exact_pack_file(
            pack_dir,
            canonical_relative_file(asset["file"], label=f"{asset_id}: file", suffix=".svg"),
            label=f"{asset_id}: SVG file",
        )
        actual_svg_sha256 = sha256_svg_bytes(svg_path.read_bytes())
        expected_svg_sha256 = entry.get("sha256")
        if expected_svg_sha256 != actual_svg_sha256:
            identity_mismatches.append(
                f"{asset_id}: SVG expected {expected_svg_sha256}, actual {actual_svg_sha256}"
            )
        actual_provenance_sha256 = sha256_text(asset["provenance"])
        expected_provenance_sha256 = entry.get("provenance_sha256")
        if expected_provenance_sha256 != actual_provenance_sha256:
            identity_mismatches.append(
                f"{asset_id}: provenance expected {expected_provenance_sha256}, actual {actual_provenance_sha256}"
            )
    if identity_mismatches:
        fail(
            f"release audit exact-identity mismatch set ({len(identity_mismatches)}):\n  "
            + "\n  ".join(identity_mismatches)
        )

    for asset_id, asset in pack_by_id.items():
        entry = audit_by_id[asset_id]
        if entry.get("file") != asset["file"]:
            fail(f"{asset_id}: release audit file does not match asset metadata")
        if entry.get("source_type") != asset["source_type"]:
            fail(f"{asset_id}: release audit source_type does not match asset metadata")
        if entry.get("current_license") != asset["license"]:
            fail(f"{asset_id}: release audit current_license does not match asset metadata")
        if is_modern_pack:
            if entry.get("source_record_id") != asset.get("source_record_id"):
                fail(f"{asset_id}: release audit source_record_id does not match asset metadata")
            if entry.get("rights_record_id") != asset.get("rights_record_id"):
                fail(f"{asset_id}: release audit rights_record_id does not match asset metadata")
        if entry.get("lineage") == "unclassified":
            fail(f"{asset_id}: release audit lineage is unclassified")
        expected_asset_rights_basis = (
            "owner_attested_openai_output"
            if pack.get("id") == CORE_PACK_ID
            else "repository_policy_original_output" if contribution else "owner_attested_original_output"
        )
        if entry.get("rights_basis") != expected_asset_rights_basis:
            fail(
                f"{asset_id}: release audit rights_basis must be "
                f"{expected_asset_rights_basis}"
            )
        if entry.get("third_party_material") != "none_declared":
            fail(f"{asset_id}: release audit declares third-party material and requires separate disposition")
        expected_provenance = "original_construction_recorded" if contribution else "owner_attested"
        if entry.get("provenance_status") != expected_provenance:
            fail(f"{asset_id}: release audit provenance_status must be {expected_provenance}")
        if entry.get("current_license") != "CC0-1.0":
            fail(f"{asset_id}: released asset must use CC0-1.0")
        expected_disposition = "licensed_under_cc0_1_0_product_release_pending" if contribution else "released_under_cc0_1_0"
        if entry.get("release_disposition") != expected_disposition:
            fail(f"{asset_id}: release audit disposition must be {expected_disposition}")

    if pack.get("id") == CORE_PACK_ID:
        actual_audit_hash = canonical_json_sha256(audit)
        if actual_audit_hash != core_pin["audit"]:
            fail(
                "Core Biology revision release-audit exact identity is immutable; "
                f"expected {core_pin['audit']}, found {actual_audit_hash}"
            )
    elif protein_product_release_selected(pack):
        receipt = load_pack(exact_pack_file(pack_dir, PurePosixPath(PROTEIN_PRODUCT_RELEASE_RECEIPT),
                                          label="Protein Homeostasis product-release receipt"))
        if (audit.get("product_release") != protein_product_release_audit_binding(receipt)
                or audit.get("rights_grant_effective_date") != "2026-10-10"
                or audit.get("product_release_status") != "released"
                or audit.get("supersedes_audit_id") != PROTEIN_PREDECESSOR_AUDIT_ID):
            fail("Protein Homeostasis release audit must bind its separate product qualification and prior grant")
        if canonical_json_sha256(audit) != PROTEIN_PRODUCT_AUDIT_SHA256:
            fail("Protein Homeostasis qualified rights audit exact identity mismatch")

    return str(audit["status"])


def validate_pack(pack_path: Path) -> tuple[str, int, str]:
    if pack_path.is_symlink():
        fail(f"{pack_path}: asset-pack.json must not be a symlink")
    if not pack_path.is_file():
        fail(f"{pack_path}: asset-pack.json is missing or not a regular file")
    pack = load_pack(pack_path)
    if not isinstance(pack, dict):
        fail(f"{pack_path}: asset-pack.json must contain a JSON object")
    missing = PACK_REQUIRED_FIELDS - pack.keys()
    if missing:
        fail(f"{pack_path}: pack missing fields: {sorted(missing)}")

    pack_id = require_non_empty_string(pack.get("id"), label=f"{pack_path}: id")
    if not RECORD_ID.fullmatch(pack_id):
        fail(f"{pack_path}: id must use lowercase stable-id characters")
    if pack_id == IMMUNOLOGY_ONCOLOGY_PACK_ID and pack.get("version") != "1.0.0":
        fail(f"{pack_path}: Immunology & Oncology version must remain 1.0.0")

    assets = pack["assets"]
    if not isinstance(assets, list) or not assets:
        fail(f"{pack_path}: assets must be a non-empty list")
    for index, asset in enumerate(assets):
        if not isinstance(asset, dict):
            fail(f"{pack_path}: assets[{index}] must be an object")
    if pack_id == CORE_PACK_ID:
        core_pin = core_release_pin(pack)
        if pack.get("schema_version") != "0.2.0":
            fail(f"{pack_path}: historical Core Biology schema_version must remain 0.2.0")
        if len(assets) != core_pin.get("count", CORE_ASSET_COUNT):
            fail(
                f"{pack_path}: historical Core Biology catalog must remain exactly {CORE_ASSET_COUNT} assets"
            )
        core_release_reference = pack.get("release_audit") or {}
        if (
            core_release_reference.get("file") != "license-release-audit.json"
            or core_release_reference.get("audit_id") != core_pin["id"]
            or core_release_reference.get("asset_count") != core_pin.get("count", CORE_ASSET_COUNT)
        ):
            fail(f"{pack_path}: Core Biology release reference must match its exact approved revision")
    if not isinstance(pack["style_tokens"], dict):
        fail(f"{pack_path}: style_tokens must be an object")
    style_families = pack.get("style_families") or [pack["style_family"]]
    if not isinstance(style_families, list) or not style_families or not all(isinstance(value, str) and value.strip() for value in style_families):
        fail(f"{pack_path}: style_families must be a non-empty list of strings when provided")
    if pack["style_family"] not in style_families:
        fail(f"{pack_path}: primary style_family must also appear in style_families")
    license_definitions = pack["license_definitions"]
    if not isinstance(license_definitions, dict) or not license_definitions:
        fail(f"{pack_path}: license_definitions must be a non-empty object")

    is_modern_pack = pack_id != CORE_PACK_ID
    is_core_experimental = pack_id == EXPANSION_PACK_ID
    source_record_ids = validate_record_table(
        pack, "source_records", required=is_modern_pack
    )
    rights_record_ids = validate_record_table(
        pack, "rights_records", required=is_modern_pack
    )
    if is_modern_pack:
        if pack.get("schema_version") != "0.3.0":
            fail(f"{pack_path}: modern scientific pack schema_version must be 0.3.0")
        if pack["style_tokens"].get("viewBox") != "0 0 128 128":
            fail(
                f"{pack_path}: modern scientific pack style_tokens.viewBox must be '0 0 128 128'"
            )
        modern_release_reference = pack.get("release_audit")
        if not isinstance(modern_release_reference, dict):
            fail(f"{pack_path}: modern-pack release_audit must be an object")
        missing_release_fields = {
            "audit_date",
            "release_effective_date",
            "concept_count",
        } - modern_release_reference.keys()
        if missing_release_fields:
            fail(
                f"{pack_path}: modern-pack release_audit missing fields: {sorted(missing_release_fields)}"
            )
        family_revision_selected = (
            pack_id in {'cell-architecture-transport', 'culture-models-assays', 'microbial-biology'}
            and pack.get('family_expansion_revision') == '2026-10-13-family-expansion'
            and pack.get('family_expansion_receipt') == 'family-expansion-2026-10-13.json'
        )
        expected_audit_file = 'rights-release-record-2026-10-13.json' if family_revision_selected else 'rights-release-record.json'
        if modern_release_reference.get("file") != expected_audit_file:
            fail(
                f"{pack_path}: modern-pack release_audit must use its exact {expected_audit_file}"
            )
        validate_modern_release_records(pack)
        derived_concept_count = len(
            {
                str(asset.get("concept_id") or asset.get("id"))
                for asset in assets
                if isinstance(asset, dict)
            }
        )
        if pack.get("asset_count") != len(assets):
            fail(f"{pack_path}: modern-pack asset_count must match its SVG style rows")
        if pack.get("concept_count") != derived_concept_count:
            fail(f"{pack_path}: modern-pack concept_count must match its stable concepts")

    if is_core_experimental:
        if pack.get("asset_count") != EXPANSION_ASSET_COUNT:
            fail(
                f"{pack_path}: expansion asset_count must remain {EXPANSION_ASSET_COUNT}"
            )
        if pack.get("concept_count") != EXPANSION_CONCEPT_COUNT:
            fail(
                f"{pack_path}: expansion concept_count must remain {EXPANSION_CONCEPT_COUNT}"
            )
        if len(assets) != EXPANSION_ASSET_COUNT:
            fail(
                f"{pack_path}: expansion catalog must contain exactly {EXPANSION_ASSET_COUNT} SVG styles"
            )

    pack_dir = pack_path.parent.resolve()
    expected_viewbox = pack["style_tokens"].get("viewBox")
    seen_ids: set[str] = set()
    seen_files: dict[str, str] = {}
    errors: list[str] = []

    for asset in assets:
        try:
            validate_asset(
                asset,
                pack,
                pack_dir,
                license_definitions,
                expected_viewbox,
                seen_ids,
                seen_files,
                require_modern_metadata=is_modern_pack,
                source_record_ids=source_record_ids,
                rights_record_ids=rights_record_ids,
            )
        except ValueError as error:
            errors.append(str(error))

    try:
        validate_concept_variants(assets)
    except ValueError as error:
        errors.append(str(error))

    if is_modern_pack:
        try:
            concept_ids = {
                asset.get("concept_id")
                for asset in assets
                if isinstance(asset, dict) and isinstance(asset.get("concept_id"), str)
            }
            if len(concept_ids) != pack.get("concept_count"):
                fail("modern catalog stable concept count must match concept_count")
            derived_category_styles: dict[str, int] = {}
            derived_category_concepts: dict[str, set[str]] = {}
            for asset in assets:
                category = asset.get("category") if isinstance(asset, dict) else None
                if isinstance(category, str):
                    derived_category_styles[category] = (
                        derived_category_styles.get(category, 0) + 1
                    )
                    derived_category_concepts.setdefault(category, set()).add(
                        str(asset.get("concept_id") or asset.get("id"))
                    )
            if is_core_experimental and derived_category_styles.get("assay-workflow", 0) < 1:
                fail("expansion catalog must include the assay-workflow category")
            expected_category_counts = {
                category: {
                    "concept_count": len(derived_category_concepts[category]),
                    "style_count": style_count,
                }
                for category, style_count in derived_category_styles.items()
            }
            if pack.get("category_counts") != expected_category_counts:
                fail(
                    "modern-pack category_counts must exactly match catalog concept and style counts"
                )
            referenced_sources = {
                asset.get("source_record_id") for asset in assets if isinstance(asset, dict)
            }
            referenced_rights = {
                asset.get("rights_record_id") for asset in assets if isinstance(asset, dict)
            }
            if protein_product_release_selected(pack):
                if (source_record_ids != {PROTEIN_SOURCE_RECORD_ID, PROTEIN_CONTOUR_REFINEMENT_RECORD_ID}
                        or referenced_sources != {PROTEIN_CONTOUR_REFINEMENT_RECORD_ID}):
                    fail("Protein Homeostasis refined assets must reference the bounded refinement record and retain its source parent")
            elif referenced_sources != source_record_ids:
                fail("modern-pack source_records must exactly match asset source_record_id references")
            if referenced_rights != rights_record_ids:
                fail("modern-pack rights_records must exactly match asset rights_record_id references")
        except (KeyError, TypeError, ValueError) as error:
            errors.append(str(error))

    try:
        for path in pack_dir.rglob("*"):
            if path.is_symlink():
                fail(f"scientific asset pack contains a symlink: {path.relative_to(pack_dir).as_posix()}")
        release_reference = pack.get("release_audit") if isinstance(pack.get("release_audit"), dict) else {}
        audit_file = canonical_relative_file(release_reference.get("file"), label="release_audit.file", suffix=".json").as_posix()
        license_notice = canonical_relative_file(
            release_reference.get("license_notice"), label="release_audit.license_notice", suffix=".md"
        ).as_posix()
        declared_files = {"asset-pack.json", audit_file, license_notice, *(asset["file"] for asset in assets if isinstance(asset, dict) and isinstance(asset.get("file"), str))}
        if len(declared_files) != len(assets) + 3:
            fail("scientific asset pack declared-file inventory contains duplicate paths")
        if pack_id == CORE_PACK_ID:
            declared_files.update(validate_core_revision(pack, pack_dir))
        elif pack_id == RNA_METHOD_PACK_ID:
            declared_files.update(validate_rna_method_artwork_revision(pack, pack_dir))
        elif protein_product_release_selected(pack):
            declared_files.update(validate_protein_product_release(pack, pack_dir))
        if pack.get('family_expansion_revision'):
            family_spec = importlib.util.spec_from_file_location('scientific_family_revision', Path(__file__).with_name('scientific_family_revision.py'))
            family_module = importlib.util.module_from_spec(family_spec)
            family_spec.loader.exec_module(family_module)
            declared_files.update(family_module.validate(pack, pack_dir))
        casefolded = [path.casefold() for path in declared_files]
        if len(casefolded) != len(set(casefolded)):
            fail("scientific asset pack declared-file inventory contains case-equivalent duplicate paths")
        actual_files = {path.relative_to(pack_dir).as_posix() for path in pack_dir.rglob("*") if path.is_file()}
        missing = sorted(declared_files - actual_files)
        extra = sorted(actual_files - declared_files)
        if missing or extra:
            details = []
            if missing:
                details.append(f"missing={missing}")
            if extra:
                details.append(f"extra={extra}")
            fail("scientific asset pack inventory does not exactly match its receipts: " + "; ".join(details))
    except (KeyError, TypeError, ValueError) as error:
        errors.append(str(error))

    release_status = "unvalidated"
    try:
        release_status = validate_release_audit(pack, pack_dir, assets)
    except ValueError as error:
        errors.append(str(error))

    if errors:
        fail(f"{pack_path}: {len(errors)} asset validation error(s):\n- " + "\n- ".join(errors))

    if pack_id == CORE_PACK_ID:
        actual_catalog_hash = canonical_json_sha256(pack)
        if actual_catalog_hash != core_pin["catalog"]:
            fail(
                f"{pack_path}: Core Biology revision catalog exact identity is immutable; "
                f"expected {core_pin['catalog']}, found {actual_catalog_hash}"
            )

    return pack_id, len(assets), release_status


@dataclass
class LibraryIdentityState:
    asset_ids: dict[str, str] = field(default_factory=dict)
    concept_ids: dict[str, str] = field(default_factory=dict)
    svg_hashes: dict[str, tuple[str, str]] = field(default_factory=dict)
    scientific_names: dict[str, tuple[str, str]] = field(default_factory=dict)
    scoped_search_terms: dict[
        tuple[str, str, str], tuple[str, str, bool]
    ] = field(default_factory=dict)


def _concept_identity(pack_id: str, asset: dict) -> str:
    concept_id = asset.get("concept_id")
    if isinstance(concept_id, str) and concept_id:
        return f"{pack_id}:{concept_id}"
    return f"{pack_id}:{asset.get('id')}"


def _register_library_asset(
    state: LibraryIdentityState,
    *,
    pack_id: str,
    pack_dir: Path,
    asset: dict,
) -> None:
    asset_id = str(asset["id"])
    prior_pack = state.asset_ids.get(asset_id)
    if prior_pack is not None:
        fail(
            f"library asset id {asset_id!r} is duplicated across packs {prior_pack!r} and {pack_id!r}"
        )
    state.asset_ids[asset_id] = pack_id

    raw_concept_id = str(asset.get("concept_id") or asset_id)
    concept_owner = state.concept_ids.get(raw_concept_id)
    if concept_owner is not None and concept_owner != pack_id:
        fail(
            f"library concept_id {raw_concept_id!r} is duplicated across packs "
            f"{concept_owner!r} and {pack_id!r}"
        )
    state.concept_ids[raw_concept_id] = pack_id

    relative_svg = canonical_relative_file(
        asset["file"], label=f"{asset_id}: file", suffix=".svg"
    )
    svg_path = exact_pack_file(pack_dir, relative_svg, label=f"{asset_id}: SVG file")
    svg_hash = sha256_svg_bytes(svg_path.read_bytes())
    prior_svg = state.svg_hashes.get(svg_hash)
    if prior_svg is not None:
        fail(
            f"exact duplicate SVG content for {asset_id!r} in {pack_id!r}; "
            f"already used by {prior_svg[1]!r} in {prior_svg[0]!r}"
        )
    state.svg_hashes[svg_hash] = (pack_id, asset_id)

    concept = _concept_identity(pack_id, asset)
    scientific_name = str(asset.get("scientific_name") or asset.get("name") or "")
    normalized_name = normalize_search_term(scientific_name)
    prior_name = state.scientific_names.get(normalized_name)
    if prior_name is not None and prior_name[0] != concept:
        fail(
            f"normalized scientific name {scientific_name!r} for {asset_id!r} duplicates "
            f"the distinct concept {prior_name[1]!r}"
        )
    state.scientific_names[normalized_name] = (concept, asset_id)

    category = normalize_search_term(str(asset.get("category") or ""))
    subcategory = normalize_search_term(str(asset.get("subcategory") or ""))
    terms = [(scientific_name, True)] + [
        (str(value), False) for value in asset.get("synonyms", []) if isinstance(value, str)
    ]
    for raw_term, is_primary in terms:
        normalized = normalize_search_term(raw_term)
        scope = (category, subcategory, normalized)
        prior = state.scoped_search_terms.get(scope)
        if prior is not None and prior[0] != concept and (prior[2] or is_primary):
            fail(
                f"ambiguous normalized scientific search term {raw_term!r} in "
                f"{category or '<uncategorized>'}/{subcategory or '<general>'}: "
                f"{asset_id!r} conflicts with {prior[1]!r}"
            )
        if prior is None or is_primary:
            state.scoped_search_terms[scope] = (concept, asset_id, is_primary)


def validate_registered_art_styles(library_path: Path, library: dict) -> list[dict[str, object]]:
    """Accept only the finite registered Style 4 addition, with its own audit."""
    styles = library.get("art_styles", [])
    if not styles:
        if "art_style_notes" in library:
            fail("Drawing-style notes require a registered drawing style")
        return []
    if styles != [{"id":"style-4","name":"Style 4","path":"style-4/manifest.json","asset_count":486}]:
        fail("Scientific drawing styles must exactly match the registered Style 4 manifest")
    if not isinstance(library.get("art_style_notes"), str) or not library["art_style_notes"].strip():
        fail("Registered Style 4 requires a visible supplied-artwork limitation")
    relative = canonical_relative_file(styles[0]["path"], label="Style 4 manifest", suffix=".json")
    manifest = exact_pack_file(library_path.parent.resolve(), relative, label="Style 4 manifest")
    script = Path(__file__).with_name("validate-style4-library.py")
    spec = importlib.util.spec_from_file_location("figure_style4_asset_validator", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    result = module.validate(manifest.parent, library_path)
    return [{"id":"style-4","directory":"style-4","asset_count":result["asset_count"],
             "file_count":result["file_count"]}]


def validate_library(library_path: Path = DEFAULT_LIBRARY) -> dict[str, object]:
    """Validate the installed scientific-library registry and every pack it declares."""

    if library_path.is_symlink():
        fail(f"{library_path}: library registry must not be a symlink")
    if not library_path.is_file():
        fail(f"{library_path}: library registry is missing or not a regular file")
    if library_path.name != "library.json":
        fail(f"{library_path}: scientific-library registry must be named library.json")
    try:
        library = json.loads(library_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        fail(f"{library_path}: invalid JSON: {error}")
    if not isinstance(library, dict):
        fail(f"{library_path}: library registry must be an object")
    missing = LIBRARY_REQUIRED_FIELDS - library.keys()
    if missing:
        fail(f"{library_path}: library registry missing fields: {sorted(missing)}")
    if library.get("schema_version") != "1.0.0":
        fail(f"{library_path}: unsupported library schema_version")
    if library.get("id") != "figure-studio-scientific-library":
        fail(f"{library_path}: unsupported library id")
    rows = library.get("packs")
    if not isinstance(rows, list) or not rows:
        fail(f"{library_path}: packs must be a non-empty list")
    art_styles = validate_registered_art_styles(library_path, library)

    packs_root = library_path.parent.resolve()
    seen_pack_ids: set[str] = set()
    seen_paths: set[str] = set()
    state = LibraryIdentityState()
    pack_summaries: list[dict[str, object]] = []
    total_assets = 0
    total_concepts = 0

    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            fail(f"{library_path}: packs[{index}] must be an object")
        missing_row = LIBRARY_PACK_REQUIRED_FIELDS - row.keys()
        if missing_row:
            fail(
                f"{library_path}: packs[{index}] missing fields: {sorted(missing_row)}"
            )
        pack_id = require_non_empty_string(
            row.get("id"), label=f"{library_path}: packs[{index}].id"
        )
        if not RECORD_ID.fullmatch(pack_id):
            fail(f"{library_path}: packs[{index}].id must be a stable lowercase id")
        if pack_id in seen_pack_ids:
            fail(f"{library_path}: duplicate pack id {pack_id!r}")
        seen_pack_ids.add(pack_id)
        require_non_empty_string(
            row.get("name"), label=f"{library_path}: packs[{index}].name"
        )
        require_non_empty_string(
            row.get("description"), label=f"{library_path}: packs[{index}].description"
        )
        if row.get("enabled") is not True:
            fail(f"{library_path}: bundled pack {pack_id!r} must be enabled")
        if (
            pack_id == IMMUNOLOGY_ONCOLOGY_PACK_ID
            and row.get("version") != "1.0.0"
        ):
            fail(
                f"{library_path}: bundled Immunology & Oncology registry version must remain 1.0.0"
            )
        modes = row.get("modes")
        if not isinstance(modes, list) or set(modes) != {"figure", "presentation"} or len(modes) != 2:
            fail(
                f"{library_path}: bundled pack {pack_id!r} must declare figure and presentation modes exactly once"
            )

        relative_catalog = canonical_relative_file(
            row.get("path"), label=f"{library_path}: {pack_id} path", suffix=".json"
        )
        catalog_path_value = relative_catalog.as_posix()
        if catalog_path_value.casefold() in seen_paths:
            fail(f"{library_path}: duplicate or case-equivalent pack path {catalog_path_value!r}")
        seen_paths.add(catalog_path_value.casefold())
        pack_path = exact_pack_file(
            packs_root, relative_catalog, label=f"{library_path}: {pack_id} catalog"
        )
        if pack_path.name != "asset-pack.json" or pack_path.parent.name != pack_id:
            fail(
                f"{library_path}: pack {pack_id!r} path must be {pack_id}/asset-pack.json"
            )
        validated_id, asset_count, release_status = validate_pack(pack_path)
        if validated_id != pack_id:
            fail(
                f"{library_path}: registry id {pack_id!r} does not match catalog id {validated_id!r}"
            )
        pack = load_pack(pack_path)
        concept_count = len(
            {
                str(asset.get("concept_id") or asset.get("id"))
                for asset in pack["assets"]
                if isinstance(asset, dict)
            }
        )
        if row.get("asset_count") != asset_count:
            fail(f"{library_path}: {pack_id} asset_count does not match its catalog")
        if row.get("concept_count") != concept_count:
            fail(f"{library_path}: {pack_id} concept_count does not match its catalog")
        for asset in pack["assets"]:
            _register_library_asset(
                state,
                pack_id=pack_id,
                pack_dir=pack_path.parent.resolve(),
                asset=asset,
            )
        total_assets += asset_count
        total_concepts += concept_count
        pack_summaries.append(
            {
                "pack_id": pack_id,
                "asset_count": asset_count,
                "concept_count": concept_count,
                "release_status": release_status,
            }
        )

    required_packs = {
        CORE_PACK_ID,
        EXPANSION_PACK_ID,
        IMMUNOLOGY_ONCOLOGY_PACK_ID,
    }
    if not required_packs.issubset(seen_pack_ids):
        fail(
            f"{library_path}: bundled library is missing required packs {sorted(required_packs - seen_pack_ids)}"
        )
    catalog_paths = {
        path.relative_to(packs_root).as_posix().casefold()
        for path in packs_root.glob("*/asset-pack.json")
        if path.is_file()
    }
    if catalog_paths != seen_paths:
        missing_registry = sorted(catalog_paths - seen_paths)
        missing_catalog = sorted(seen_paths - catalog_paths)
        fail(
            "library registry and on-disk pack catalogs disagree: "
            f"unregistered={missing_registry}; missing={missing_catalog}"
        )
    top_level_files: set[str] = set()
    top_level_directories: set[str] = set()
    for child in packs_root.iterdir():
        if child.is_symlink() or getattr(child, "is_junction", lambda: False)():
            fail(f"library root contains a link or junction: {child.name}")
        if child.is_file():
            top_level_files.add(child.name)
        elif child.is_dir():
            top_level_directories.add(child.name)
        else:
            fail(f"library root contains an unsupported entry: {child.name}")
    if top_level_files != {"library.json"}:
        fail(
            "library root contains loose or missing files; "
            f"expected ['library.json'], found {sorted(top_level_files)}"
        )
    registered_directories = seen_pack_ids | {style["directory"] for style in art_styles}
    if top_level_directories != registered_directories:
        fail(
            "library root directories must exactly match registered pack and drawing-style ids; "
            f"expected {sorted(registered_directories)}, found {sorted(top_level_directories)}"
        )

    return {
        "library_id": library["id"],
        "pack_count": len(pack_summaries),
        "asset_count": total_assets,
        "concept_count": total_concepts,
        "packs": pack_summaries,
        "art_styles": art_styles,
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate Figure Tool scientific asset pack metadata and SVG files.")
    parser.add_argument("pack_path", nargs="?", help="Optional asset-pack.json path. Defaults to the production core-biology pack.")
    parser.add_argument("--pack", dest="pack_option", help="Asset-pack.json path to validate.")
    parser.add_argument(
        "--library",
        nargs="?",
        const=str(DEFAULT_LIBRARY),
        help="Validate the whole installed library; optionally provide a library.json path.",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Alias for --library using the production library.json registry.",
    )
    parser.add_argument("--expect-fail", action="store_true", help="Exit successfully only when validation fails. Intended for negative test fixtures.")
    parser.add_argument("--require-public-release", action="store_true",
                        help="Reject locally valid drafts when qualifying assets for public distribution.")
    return parser.parse_args(argv)


def require_public_product_release(root: Path, pending: list[str], *, single_pack: bool = False) -> None:
    """Apply only the finite reviewed supplement after ordinary pack validation."""
    if not pending:
        return
    spec = importlib.util.spec_from_file_location("scientific_product_release", Path(__file__).with_name("scientific_product_release.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    approval = module.validate(root)
    remaining = sorted(set(pending) - set(approval["packs"] if approval else ()))
    if remaining:
        fail("Public release is pending for scientific " + ("pack: " if single_pack else "packs: ") + ", ".join(remaining))


def main() -> int:
    args = parse_args(sys.argv[1:])
    if args.pack_path and args.pack_option:
        print("Use either positional pack_path or --pack, not both.", file=sys.stderr)
        return 2
    if (args.library or args.all) and (args.pack_path or args.pack_option):
        print("Use pack validation or whole-library validation, not both.", file=sys.stderr)
        return 2

    try:
        if args.library or args.all:
            library_path = Path(args.library).resolve() if args.library else DEFAULT_LIBRARY
            summary = validate_library(library_path)
            if args.require_public_release:
                pending = [str(pack["pack_id"]) for pack in summary["packs"] if pack["release_status"] != "released"]
                require_public_product_release(library_path.parents[2], pending)
            success_message = (
                f"Validated {summary['asset_count']} SVG styles across "
                f"{summary['concept_count']} concepts in {summary['pack_count']} packs."
            )
        else:
            pack_arg = args.pack_option or args.pack_path
            pack_path = Path(pack_arg).resolve() if pack_arg else DEFAULT_PACK
            pack_id, asset_count, release_status = validate_pack(pack_path)
            if args.require_public_release and release_status != "released":
                require_public_product_release(pack_path.parents[3], [pack_id], single_pack=True)
            success_message = (
                f"Validated {asset_count} assets in pack {pack_id!r}; "
                f"release audit status={release_status}."
            )
    except ValueError as error:
        if args.expect_fail:
            print(f"Asset validation failed as expected: {error}")
            return 0
        print(f"Asset validation failed: {error}", file=sys.stderr)
        return 1

    if args.expect_fail:
        print(f"Expected validation to fail, but validation succeeded: {success_message}", file=sys.stderr)
        return 1

    print(success_message)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
