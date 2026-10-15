# Scientific Assets Catalog Expansion Plan

This plan defines the next-stage expansion path for the Superbench Figure Tool Scientific Assets Library. It keeps the work intentionally controlled: original vector drafts, an explicit soft-line primary family with manuscript-line companions where they add real value, recoloring-safe SVG structure, validator-first metadata, and no use of BioRender or other proprietary illustration-library artwork.

## Current library — 13 October 2026

The shared Figure and Present source library contains 346 concepts and 406 authored
SVG drawings across eight packs. The four latest families contain 84 editable drawings:

| Family | Concepts / drawings | Scientific review |
| --- | ---: | --- |
| [Protein Homeostasis](PROTEIN_HOMEOSTASIS_QUALIFICATION_2026_10_11.md) | 8 / 8 | Folding states, chaperone interactions, ubiquitination and substrate processing; artwork and native editing qualified |
| [Cell Architecture & Transport](CELL_ARCHITECTURE_TRANSPORT_FAMILY_EXPANSION_2026-10-13.md) | 20 / 28 | Cell contacts, vesicle states, cytoskeletal motors and import/export arrangements |
| [Culture Models & Functional Assays](CULTURE_FAMILY_SCIENTIFIC_REFERENCES_2026_10_13.md) | 18 / 24 | Alternative culture arrangements, organoid and spheroid models, tissue interfaces and illustrative assay setups |
| [Microbial Structures & Interactions](MICROBIAL_FAMILY_EXPANSION_2026_10_13.md) | 19 / 24 | Envelope, capsule, biofilm, coccoid and fungal forms, spore enclosure, phage tail architectures and selected viral membrane interactions |

All 84 drawings passed independent scientific and original-image review in Soft
color, Cut paper and Technical ink. The Protein Homeostasis qualification remains
unchanged. The three expanded families have their own
[native editing and persistence record](FAMILY_LIBRARY_IMPROVEMENTS_2026_10_13.md).
Source qualification does not establish a deployed web release.

There are 326 released SVG drawings and 80 drawings awaiting product-level release approval, including the four
earlier RNA-method additions: droplet cell partitioning, an oligo-barcoded capture
bead, a spatial RNA capture array and illustrative RNA puncta. The Scene library
remains at ten released recipes and two drafts, covering the separate single-cell,
spatial-capture and RNA-imaging routes. Original artwork and recipes received CC0
permission on 10 October; permission and product-quality approval remain separate.

Five existing contextual drawings were revised: microglia, endothelium, tumor
hypoxia, tumor-associated antigen and neoantigen peptide. Scientific limits,
references and editing checks are recorded in
[the RNA-method review](RNA_METHODS_ASSET_REVIEW_2026_10_07.md), with subsequent
refinements in [the DNA/RNA artwork review](RNA_ARTWORK_REVISION_2026_10_11.md).

The [broader Library slice](BROAD_LIBRARY_IMPROVEMENTS_2026_10_13.md) improves 12
existing Core Biology concepts and their matched Thin companions, refines the four
RNA-method drawings, and adds 24 original drawings across cells, organelles and
molecules. Fourteen additions are views, morphologies or ligand states of existing
entries; ten represent additional entities. Direct form previews, precise search
aliases and native editing/persistence checks support these choices. RNA-method
reuse permission and pending product-release approval remain separate.

The [family Library slice](FAMILY_LIBRARY_IMPROVEMENTS_2026_10_13.md) refreshes all
40 Cell Architecture, Culture Models and Microbial drawings and adds 36 original
drawings. Nineteen are alternative views or states within a shared biological
entry; seventeen introduce additional entities or arrangements. The source reviews and native
checks advance the planned Library qualification without selecting a deployed
release. Tumor-volume plot labeling and confocal optical-path clarity remain
separate quality follow-ups. Figure and PDF v1 milestones remain unchanged, and
the roadmap remains the same. The next release decision is whether to include
these qualified source families in a new reviewed Figure package.

## Core Biology pack summary

Production pack:

```text
assets/scientific-packs/core-biology/asset-pack.json
```

Current status after the broader biological drawing slice:

- Total assets: 132
- Original seed assets: 15
- Batch-1 additions: 38
- Batch-2 additions: 10
- Model-system batch-1 additions: 4
- Model-organism batch-1 additions: 5
- Immune-cell batch-1 additions: 12
- Immune-cell manuscript companions: 6
- Immune-mechanism batch-1 additions: 6
- Immune-mechanism manuscript companions: 5
- Clinical-sample batch-1 additions: 6
- Publication-variant batch-1 additions: 5
- RNA form-variant batch-1 additions: 1
- Broad cells, organelles and molecules additions: 24
- Manuscript-line companions: 17
- Style families: `figure-studio-soft-line-v1` and `figure-studio-manuscript-line-v1`
- ViewBox standard: `0 0 128 128`
- QA status: `independent_scientific_and_visual_review_passed_2026_10_13`
- Source/license status: all 132 Core Biology drawings use the owner-selected `CC0-1.0` policy; the bounded revision preserves the previous audits and notices and records current scientific/artwork/native evidence. Public package and deployment selection remains separate.

Category coverage:

| Category | Count | Current role |
| --- | ---: | --- |
| `cell` | 26 | Animal-cell sections and cutaway, epithelial views, neuron morphologies, cell states, spheroids, glial and immune cells |
| `organelle` | 21 | Core organelles and compartments, additional views and networks, envelope/pore detail, smooth ER and autolysosome |
| `nucleic-acid` | 12 | DNA/RNA, chromatin, promoter, protein-DNA binding, two manuscript-line companions, and explicit hairpin/linear RNA forms |
| `protein` | 13 | Intact antibody and fragments, generic binding/catalysis, explicit oligomer compositions and manuscript-line companions |
| `membrane-signaling` | 21 | Receptor ligand states and extracellular domain, peptide/small-molecule ligand symbols, channels, transporters and immune-recognition complexes |
| `pathway-symbol` | 14 | Activation, inhibition, arrows, mechanism symbols, and regulated granule release |
| `lab-equipment` | 10 | Common bench/assay objects |
| `model-system` | 9 | 3D culture, co-culture, mouse, and five distinct microbial/vertebrate/invertebrate model-organism concepts |
| `clinical-sample` | 6 | Generic blood, tissue, pellet, slide, and storage-vial sample primitives |

## Catalog Structure

Keep the MVP categories stable until there is a clear product need to add more:

- `cell`
- `organelle`
- `nucleic-acid`
- `protein`
- `membrane-signaling`
- `pathway-symbol`
- `lab-equipment`
- `model-system`
- `clinical-sample`

Adjacent future categories should be opened only when the current categories become misleading:

- `assay-workflow`: assay diagrams, readout summaries, sample-processing workflows
- `immune-biology`: immune-cell family and immune mechanism assets
- `neuroscience`: neuron/glia/synapse/brain-region concepts
- `oncology`: tumor microenvironment, metastasis, therapy-response concepts
- `tissue-anatomy`: simple tissue layers or generic organ-level cues

## Working Indexes

The master asset ledger is generated from production packs, draft packs, and planning docs:

```text
docs/scientific-assets/MASTER_ASSET_INDEX.md
docs/scientific-assets/master-asset-index.json
```

Use the master index before choosing new work. It records created asset counts per keyword, production-versus-draft status, duplicate display names, asset file paths, and planned/deferred concepts.

Cell-biology, tumor, lineage, and cell-state coverage is tracked in the focused supplemental checklist:

```text
docs/scientific-assets/CELL_BIOLOGY_ASSET_INDEX.md
```

Use the focused cell index before adding more cell-related assets. It intentionally allows multiple assets with the same display name when the visual morphology is meaningfully different, such as multiple `Cancer Cell` variants for broad search terms.

## Expansion Priorities

Priority order:

1. Fill broad graphical-abstract primitives before specialty biology.
2. Add reusable object families, not one-off scenes.
3. Prefer concepts that combine well with existing arrows, labels, and imported panels.
4. Add categories only when search/filter behavior benefits from the distinction.
5. Keep every asset recoloring-safe from day one.

## Near-Term Batches

Batch 1: Core biology and workflow primitives, implemented

- Added organelles: Golgi, rough ER, lysosome, endosome, peroxisome
- Added cell states/models: apoptotic cell, dividing cell, tumor spheroid
- Added protein/signaling concepts: kinase, enzyme, transcription factor, ligand, RTK-like receptor, GPCR-like receptor, transporter, drug-conjugated antibody
- Added nucleic-acid/gene-regulation concepts: RNA, mRNA, siRNA, promoter, transcription flow, protein-DNA binding
- Added pathway symbols: dashed/bidirectional/secretion/translocation arrows, phosphorylation, cleavage, drug inhibition, small-molecule interaction
- Added lab/assay objects: tubes, syringe, microscope, flask, 96-well plate, plate reader

Batch 2: Focused core-biology expansion, implemented

- Added cell concepts: neuron-like cell and immune-like round cell
- Added organelles: lipid droplet and autophagosome
- Added nucleic-acid concepts: plasmid vector and CRISPR-Cas9 complex
- Added protein/signaling concepts: protein multimer complex and cytokine receptor
- Added pathway concepts: metabolic cycle and feedback loop

Batch 3: Model systems from real Figure Studio use, implemented

- Added a cell spheroid cluster, tumor-glia co-culture, and mouse model under the new `model-system` category.
- Promoted an astrocyte-like cell into the production pack under `cell`.
- Adapted these assets from user-owned Figure Studio graphical-abstract artwork and normalized them to the production SVG and recoloring contract.
- Replaced the tangled mouse drawing while preserving its stable id, then added a separate manuscript-line companion with the same concept and semantic region ids.

Visual triage after Batch 3:

- `KEEP`: 36 assets.
- `ADD VARIANT`: 5 assets whose soft-line art remains useful but would benefit from a manuscript-line companion.
- `IMPROVE`: 22 assets with localized readability, scale, or semantic-shape issues.
- `REPLACE`: 4 assets originally had silhouette failures. All four are now replaced: the mouse in parity slice 1, followed by `core.model.cell_spheroid_cluster`, `core.model.tumor_glia_coculture`, and `core.er.rough` in parity slice 2.
- Structural validator success does not count as visual approval; use 64 px unlabeled review plus full-resolution contact-sheet inspection.

Parity slice 2 also groups shared `concept_id` entries in the asset browser. One concept now occupies one library card, explicit style choices select the inserted variant, and the selected-asset inspector can switch between compatible variants while preserving transform and semantic color overrides.

Parity slice 3 refreshes the principal soft-line organelle family as a coherent set. Mitochondrion, Golgi apparatus, lysosome, endosome, peroxisome, lipid droplet, and autophagosome were rebuilt with distinct scientific silhouettes, quieter internal detail, and consistent line-weight/padding discipline. The parity-slice-2 rough ER remains the reviewed family reference. All eight now pass both 64 px library-thumbnail and enlarged-canvas review.

Parity slice 4 applies the same morphology-led review to the eight-asset cell family. Generic eukaryotic, epithelial-like, apoptotic, dividing, tumor-spheroid, neuron-like, and immune-like cells were rebuilt to remove badge, smile, lollipop, and sunburst reads. The user-derived astrocyte-like cell was retained and promoted after family-scale review. All eight now carry reviewed metadata and pass both library-thumbnail and enlarged-canvas checks.

Parity slice 5 refreshes the seven-asset membrane-signaling family around distinct topology rather than interchangeable objects placed over decorative rails. The family now includes an explicit phospholipid bilayer, a single-pass membrane receptor, a continuous ion-channel pore, a ligand-bridged RTK-like dimer with kinase lobes and phosphates, a seven-pass GPCR-like receptor, a gated carrier transporter, and paired cytokine-receptor chains with a convergent cytosolic signal. All seven now carry reviewed metadata and pass both library-thumbnail and enlarged-canvas checks.

Parity slice 6 refreshes the seven-asset protein family around recognizable molecular architecture instead of generic circles, blobs, and Y-shaped symbols. The family now includes a paired-chain IgG-like antibody, a bilobed kinase with a catalytic cleft, a DNA-bound transcription factor, an enzyme wrapped around a fitted substrate, a compact protein ligand with a distinct binding face, a structured antibody-drug conjugate, and an interlocking multimeric complex. All seven now carry reviewed metadata and pass both library-thumbnail and enlarged-canvas checks.

Parity slice 7 refreshes the nine-asset nucleic-acid and gene-regulation family around distinct molecular form and mechanism. The family now separates a crossing DNA helix, compact nucleosome-bearing chromatin loop, single-stranded RNA hairpin, mature mRNA, short siRNA duplex, promoter-to-gene cassette, protein-DNA binding complex, directional plasmid map, and bilobed CRISPR-Cas-like complex. The RNA strand was specifically corrected from an erroneous duplex-like read. All nine now carry reviewed metadata and pass both library-thumbnail and enlarged-canvas checks.

Parity slice 8 refreshes the ten-asset lab-equipment family around recognizable bench-object silhouettes and truthful assay geometry. The family now separates a single-channel micropipette, shallow Petri dish with offset lid, non-overlapping six-well plate, hinged microcentrifuge tube, graduated conical tube, fine-needle syringe, compound microscope, tissue-culture flask, exact 8-by-12 96-well microplate, and plate reader with a visible tray/readout relationship. All ten now carry reviewed metadata and pass both library-thumbnail and enlarged-canvas checks.

Parity slice 9 refreshes the thirteen-asset pathway-symbol family around conventional connector grammar and explicit mechanism cues. The family now separates positive and negative regulation, indirect and two-way relations, DNA-to-RNA transcription, vesicle secretion across a membrane, cargo translocation through a boundary, explicit phosphate attachment, restrained substrate cleavage, drug-to-target inhibition, small-molecule pocket binding, a true four-step metabolic cycle, and a two-node negative-feedback loop. All thirteen use the thinner pathway-symbol treatment, carry reviewed metadata, and pass both library-thumbnail and enlarged-canvas checks.

Parity slice 10 closes the remaining organelle-quality gap and completes the first full-library curation pass. Round Nucleus was rebuilt from a concentric bullseye into an organic double-envelope nucleus with restrained pores, distributed chromatin, and a smaller offset nucleolus. Vesicle was rebuilt from a generic cargo badge into a smooth transport-vesicle silhouette with close membrane contours, open lumen, and sparse cargo. All ten organelle assets now pass one unlabeled family-scale comparison, and all 68 production assets carry curated, visually reviewed metadata.

Parity slice 11 opens the first dedicated immune-cell family while keeping the stable `cell` category. T cell, B cell, natural killer cell, macrophage, dendritic cell, and neutrophil use distinct lineage-level morphology or restrained identity cues without encoding subtype, activation, maturation, polarization, or interaction state. T cell and macrophage also include geometry-matched manuscript-line companions exposed through concept-level style switching. The eight new styles pass color and grayscale family review at thumbnail and enlarged-canvas scale, bringing the production pack to 76 curated assets across 73 concepts.

Parity slice 12 adds six modular immune-recognition and effector-mechanism components without opening a new category. MHC-I and MHC-II are distinguished by anchor and partner topology; TCR and PD-1/PD-L1 engagements use opposing membranes and remain free of downstream-state cues; Fc-receptor binding contacts the antibody Fc stem; and cytotoxic-granule release stops at regulated exocytosis without implying target-cell pores or killing. All six expose independently recolorable biological components and are discoverable together with the `immune mechanism` tag, bringing the production pack to 82 curated assets across 79 concepts.

Parity slice 13 adds geometry-matched manuscript-line companions for MHC-I, MHC-II, TCR engagement, PD-1/PD-L1 engagement, and Fc-receptor binding. Each companion preserves the base concept's viewBox, pose, contacts, semantic region ids, and biological exclusions while reducing outline weight and palette intensity. Concept-level style switching keeps transforms and recoloring compatible. Cytotoxic-granule release intentionally remains soft-line only. The five companions bring the production pack to 87 curated assets across the same 79 concepts, with eight manuscript-line styles overall.

Parity slice 14 completes manuscript-style coverage across the six immune-cell concepts. B cell, natural killer cell, dendritic cell, and neutrophil join the existing T-cell and macrophage companions with geometry-matched poses, identical semantic region ids, muted fills, and thinner outlines. Surface immunoglobulin, NK granules, dendritic processes, and connected neutrophil nuclear lobes remain legible at 64 px and in grayscale. The four companions bring the production pack to 91 curated assets across the same 79 concepts, with twelve manuscript-line styles overall.

Parity slice 15 opens the `clinical-sample` category with six sample-centric primitives: a neutral-stopper blood sample tube, blood drop, tissue biopsy core, tissue section slide, cell-pellet tube, and cryovial. The family is distinguished from generic labware by sample topology—meniscus, cut surfaces, mounted tissue, compact pellet, or restrained stored volume—rather than vendor shape or cap color. Metadata avoids patient, disease, additive, stain, preservation, viability, and assay-readiness claims. The six original concepts bring the production pack to 97 curated assets across 85 concepts.

Parity slice 16 audits all 97 styles / 85 concepts instead of increasing the count. Ion Channel and Membrane Transporter were separated around open-pore versus enclosed alternating-access carrier topology; Generic Kinase and Catalytic Enzyme were separated around unequal-lobe phosphate transfer versus a single-fold complementary pocket; CRISPR Cas9 was rebuilt to frame visible target DNA, guide RNA, and cleavage marks beside the retained Protein-DNA Binding reference. A directional search-alias fix removes symmetric synonym contamination, and canonical browser QA now checks one non-name intent for all 85 concepts plus sixteen bounded cross-category user intents. See `docs/scientific-assets/LIBRARY_AUDIT_2026_07_19.md`.

Parity slice 17 delivers the audit's publication-variant queue for Generic Antibody, Drug-Conjugated Antibody, DNA Double Helix, Plasmid Vector, and Mitochondrion. Each manuscript-line companion preserves the base viewBox, exact centerline geometry, element count, semantic region ids, pose, and biological exclusions while reducing line and palette weight. Browser QA recolors every region, switches every concept soft-to-manuscript-to-soft in place, and verifies stable object identity, transform, recolors, and style state. The five companions bring the pack to 102 curated styles across the same 85 concepts, with seventeen manuscript-line styles overall.

Parity slice 18 closes the audit's final variant item with a linear/open ssRNA companion for the retained RNA Strand hairpin. Both forms share one concept, the same four semantic regions, and an explicit `form` axis rather than presenting biological topology as a visual style. The linear form uses one continuous open backbone, seven attached base marks, and two terminal accents without claiming sequence, length, end chemistry, modification, or a named RNA class. Canonical browser QA verifies every-region recoloring plus a nondefault Hairpin-to-Linear-to-Hairpin round trip that preserves object identity, position, displayed bounds, rotation, flips, opacity, selection, and z-order. A fresh 64 px color/grayscale board distinguishes both ssRNA forms from DNA, siRNA, and mRNA. The pack now contains 103 curated styles across the same 85 concepts.

Parity slice 19 fills the thinnest stable category with five original soft-line model-organism concepts: Budding Yeast Model, Rod-Shaped Bacterium, Zebrafish Model, Fruit Fly Model, and Nematode Model. The family uses defining topology rather than labels alone—bud neck and vacuole, unbound nucleoid and ribosome dots, fins and fan tail, segmented fly body with one wing pair and six legs, and an open nematode body with a neutral terminal cue. The existing Mouse Model joins the family search. All six concepts pass unlabeled 64 px color/grayscale review without genotype, strain, sex, age, developmental-stage, treatment, disease, or assay-outcome claims. The five additions bring the pack to 108 curated styles across 90 concepts.

Batch 4: Fill gaps revealed by repeated Figure Studio use

- Add only assets requested by repeated figure-building workflows.
- Avoid adding near-duplicates unless a subfamily needs distinct morphology or mechanism semantics.
- The audited replacement and variant queue is complete. Open the next batch only from repeated Figure Studio use, figure-abstract extraction, or a newly evidenced discoverability gap.
- The first thin-category expansion is complete for model systems. Continue only with another coherent, independently reviewed family; do not add automatic manuscript companions.

## Medium-Term Targets

Medium-term catalog targets should remain modest:

- 75-100 total assets before opening external/user pack workflows.
- 5-20 assets per stable MVP category.
- 1-2 small subfamilies per category, with consistent naming and region semantics.
- Contact-sheet review after every batch.
- Validator pass plus manual art/provenance review before any public redistribution claim.

## Add / Do Not Add Criteria

Add an asset when:

- It represents a broad reusable scientific concept.
- It can be named honestly without overclaiming specificity.
- It can be drawn simply in 3-5 recolorable regions.
- It will help graphical abstracts, mechanism diagrams, annotations, or assay workflows.
- It complements rather than duplicates existing assets.

Do not add an asset when:

- It is a manuscript-specific full scene or compound figure that should be composed from primitives. A compact model-system object may combine several cell types when the co-culture or organoid model itself is the reusable concept.
- It is too close to a proprietary scientific illustration-library asset or style.
- It requires specialized biological accuracy beyond a generic schematic.
- It would be better as text, a chart, an imported analysis panel, or a user-specific illustration.
- It mainly exists to fill a category count.

## Duplicate and Overlap Strategy

Before adding a concept:

1. Search `asset-pack.json` by id, name, category, and tags.
2. Check the contact sheet for visual overlap.
3. Decide whether the new asset is:
   - a replacement, if the old asset is unclear
   - a subfamily member, if morphology is meaningfully different
   - a composition, if it should be built from existing assets
   - out of scope, if it is too narrow
4. Prefer renaming or retagging an existing asset over adding a near-duplicate.

## Naming Conventions

Asset ids:

- Use `core.<family>.<concept>` where possible.
- Keep lowercase dot-delimited ids with underscores inside tokens.
- Use stable family names: `cell`, `lab`, `symbol`, `protein`, `receptor`, `rna`, `gene`.
- Avoid vendor, drug, disease, or institution-specific ids in the core pack.

Display names:

- Use clear user-facing names.
- Prefer `Generic`, `Basic`, `Like`, or `Segment` when specificity is intentionally limited.
- Avoid names that imply exact molecular structure, cell lineage, organism, or clinical status unless the art supports it.

Subfamily examples:

- `core.cell.generic`, `core.cell.apoptotic`, `core.cell.dividing`
- `core.receptor.membrane`, `core.receptor.rtk_like`, `core.receptor.gpcr_like`
- `core.symbol.activation_arrow`, `core.symbol.dashed_arrow`, `core.symbol.translocation_arrow`
- `core.lab.microcentrifuge_tube`, `core.lab.conical_tube`, `core.lab.plate_96_well`

## Backlog

| Asset id concept | Display name | Category | Intended use | Priority | Recolorable regions | Status |
| --- | --- | --- | --- | --- | --- | --- |
| `core.membrane.plasma_segment` | Plasma Membrane Segment | `membrane-signaling` | Cell surface and membrane context | P0 | membrane, lipid_head, accent, outline | Added batch 1; refreshed parity slice 5 |
| `core.receptor.membrane` | Membrane Receptor | `membrane-signaling` | Generic single-pass receptor signaling | P0 | membrane, receptor, ligand, outline | Added seed pack; refreshed parity slice 5 |
| `core.channel.ion` | Ion Channel | `membrane-signaling` | Ion transport and channel signaling | P0 | membrane, channel, ion, outline | Added seed pack; replaced library-audit slice 16 |
| `core.nucleus.round` | Round Nucleus | `organelle` | Nuclear organization and cell-state schematics | P0 | nucleoplasm, envelope, nucleolus, chromatin, outline | Added seed pack; refreshed parity slice 10 |
| `core.vesicle` | Vesicle | `organelle` | Generic transport and cargo-trafficking schematics | P0 | lumen, membrane, cargo, outline | Added seed pack; refreshed parity slice 10 |
| `core.mitochondrion.basic` | Mitochondrion | `organelle` | Metabolism and cell-state schematics | P0 | matrix, cristae, accent, outline | Seed asset; refreshed parity slice 3; soft-line and manuscript variants parity slice 17 |
| `core.golgi.basic` | Golgi Apparatus | `organelle` | Secretory pathway schematics | P0 | cisterna, vesicle, accent, outline | Added batch 1; refreshed parity slice 3 |
| `core.er.rough` | Rough Endoplasmic Reticulum | `organelle` | Protein synthesis/ER stress | P0 | membrane, lumen, ribosome, outline | Added batch 1; replaced parity slice 2 |
| `core.lysosome.basic` | Lysosome | `organelle` | Degradation/autophagy diagrams | P0 | lumen, membrane, enzyme, outline | Added batch 1; refreshed parity slice 3 |
| `core.endosome.basic` | Endosome | `organelle` | Trafficking/internalization | P0 | lumen, membrane, cargo, outline | Added batch 1; refreshed parity slice 3 |
| `core.peroxisome.basic` | Peroxisome | `organelle` | Generic organelle/metabolism | P1 | lumen, core, membrane, outline | Added batch 1; refreshed parity slice 3 |
| `core.organelle.lipid_droplet` | Lipid Droplet | `organelle` | Lipid storage and metabolism | P1 | droplet, highlight, outline | Added batch 2; refreshed parity slice 3 |
| `core.organelle.autophagosome` | Autophagosome | `organelle` | Autophagy and cargo sequestration | P1 | vesicle, cargo, outline | Added batch 2; refreshed parity slice 3 |
| `core.cell.apoptotic` | Apoptotic Cell | `cell` | Cell death mechanism figures | P0 | cytoplasm, nucleus, bleb, outline | Added batch 1; refreshed parity slice 4 |
| `core.cell.dividing` | Dividing Cell | `cell` | Proliferation/cell-cycle figures | P0 | cytoplasm, chromosome, spindle, outline | Added batch 1; refreshed parity slice 4 |
| `core.cell.t_cell` | T Cell | `cell` | Generic T-lymphocyte diagrams | P0 | cytoplasm, nucleus, receptor, outline | Added immune batch 1; soft-line and manuscript variants; parity slice 11 |
| `core.cell.b_cell` | B Cell | `cell` | Generic B-lymphocyte diagrams | P0 | cytoplasm, nucleus, surface_ig, outline | Added immune batch 1; soft-line and manuscript variants; parity slice 14 |
| `core.cell.nk_cell` | Natural Killer Cell | `cell` | Generic NK-cell and innate-cytotoxicity context | P0 | cytoplasm, nucleus, granule, outline | Added immune batch 1; soft-line and manuscript variants; parity slice 14 |
| `core.cell.macrophage` | Macrophage | `cell` | Generic macrophage and myeloid context | P0 | cytoplasm, nucleus, vacuole, outline | Added immune batch 1; soft-line and manuscript variants; parity slice 11 |
| `core.cell.dendritic` | Dendritic Cell | `cell` | Generic dendritic-cell and antigen-presentation context | P0 | cytoplasm, nucleus, process, outline | Added immune batch 1; soft-line and manuscript variants; parity slice 14 |
| `core.cell.neutrophil` | Neutrophil | `cell` | Generic neutrophil and granulocyte context | P0 | cytoplasm, nucleus, granule, outline | Added immune batch 1; soft-line and manuscript variants; parity slice 14 |
| `core.antibody.igg` | Generic Antibody | `protein` | Antibody binding and immunology figures | P0 | heavy_chain, binding_tip, hinge, outline | Added seed pack; refreshed parity slice 6; soft-line and manuscript variants parity slice 17 |
| `core.protein.kinase` | Generic Kinase | `protein` | Signaling cascade nodes | P0 | body, active_site, phosphate, outline | Added batch 1; replaced library-audit slice 16 |
| `core.protein.transcription_factor` | Transcription Factor | `protein` | Gene regulation figures | P0 | body, dna_binding, activation_domain, outline | Added batch 1; refreshed parity slice 6 |
| `core.protein.enzyme` | Catalytic Enzyme | `protein` | Generic catalysis/reaction diagrams | P0 | body, active_site, substrate, outline | Added batch 1; replaced library-audit slice 16 |
| `core.ligand.generic` | Generic Ligand | `protein` | Binding/signaling cue | P0 | ligand, accent, outline | Added batch 1; refreshed parity slice 6 |
| `core.receptor.rtk_like` | RTK-Like Receptor | `membrane-signaling` | Growth-factor signaling | P0 | membrane, receptor, ligand, phosphate, outline | Added batch 1; refreshed parity slice 5 |
| `core.receptor.gpcr_like` | GPCR-Like Receptor | `membrane-signaling` | Membrane signaling mechanisms | P1 | membrane, receptor, ligand, outline | Added batch 1; refreshed parity slice 5 |
| `core.transporter.basic` | Membrane Transporter | `membrane-signaling` | Solute/drug transport | P0 | membrane, transporter, cargo, outline | Added batch 1; replaced library-audit slice 16 |
| `core.membrane_signaling.cytokine_receptor` | Cytokine Receptor | `membrane-signaling` | Cytokine-receptor signaling | P1 | membrane, receptor, ligand, signal, outline | Added batch 2; refreshed parity slice 5 |
| `core.immune.mhc_i_peptide` | MHC-I Peptide Complex | `membrane-signaling` | Class-I antigen-presentation component | P0 | membrane, mhc, beta2m, peptide, outline | Added immune-mechanism batch 1; soft-line and manuscript variants; parity slice 13 |
| `core.immune.mhc_ii_peptide` | MHC-II Peptide Complex | `membrane-signaling` | Class-II antigen-presentation component | P0 | membrane, mhc_alpha, mhc_beta, peptide, outline | Added immune-mechanism batch 1; soft-line and manuscript variants; parity slice 13 |
| `core.immune.tcr_engagement` | TCR Peptide-MHC Engagement | `membrane-signaling` | Class-neutral TCR recognition component | P0 | membrane, pmhc, peptide, tcr, outline | Added immune-mechanism batch 1; soft-line and manuscript variants; parity slice 13 |
| `core.immune.pd1_pdl1_checkpoint` | PD-1 PD-L1 Checkpoint | `membrane-signaling` | Checkpoint-ligand engagement component | P0 | membrane, pdl1, pd1, outline | Added immune-mechanism batch 1; soft-line and manuscript variants; parity slice 13 |
| `core.immune.fc_receptor_binding` | Fc Receptor Binding | `membrane-signaling` | Antibody-Fc-receptor binding component | P0 | membrane, fc_receptor, antibody, fc_domain, outline | Added immune-mechanism batch 1; soft-line and manuscript variants; parity slice 13 |
| `core.antibody.drug_conjugate` | Drug-Conjugated Antibody | `protein` | Simple ADC-like concept | P1 | antibody, linker, payload, outline | Added batch 1; refreshed parity slice 6; soft-line and manuscript variants parity slice 17 |
| `core.protein.multimer_complex` | Protein Multimer Complex | `protein` | Generic oligomeric protein complex | P1 | subunit_a, subunit_b, active_site, outline | Added batch 2; refreshed parity slice 6 |
| `core.dna.double_helix` | DNA Double Helix | `nucleic-acid` | Generic DNA and genomics diagrams | P0 | backbone, base_pair, accent, outline | Added seed pack; refreshed parity slice 7; soft-line and manuscript variants parity slice 17 |
| `core.chromatin.loop` | Chromatin Loop | `nucleic-acid` | Chromatin organization and compaction | P1 | fiber, histone, accent, outline | Added seed pack; refreshed parity slice 7 |
| `core.rna.strand` | RNA Strand | `nucleic-acid` | RNA biology schematics | P0 | backbone, base, accent, outline | Added batch 1; refreshed parity slice 7; Hairpin and Linear form variants parity slice 18 |
| `core.mrna.transcript` | mRNA Transcript | `nucleic-acid` | Expression/translation diagrams | P0 | utr, coding_region, cap_tail, outline | Added batch 1; refreshed parity slice 7 |
| `core.rna.sirna` | siRNA Duplex | `nucleic-acid` | Perturbation/RNAi workflows | P0 | sense, antisense, overhang, outline | Added batch 1; refreshed parity slice 7 |
| `core.gene.promoter` | Gene Promoter Segment | `nucleic-acid` | Gene regulation diagrams | P0 | gene, promoter, transcript, outline | Added batch 1; refreshed parity slice 7 |
| `core.symbol.activation_arrow` | Activation Arrow | `pathway-symbol` | Positive-regulation connector | P0 | stroke, head, accent, outline | Added seed pack; refreshed parity slice 9 |
| `core.symbol.inhibition_bar` | Inhibition Bar | `pathway-symbol` | Negative-regulation connector | P0 | stroke, terminal_bar, accent, outline | Added seed pack; refreshed parity slice 9 |
| `core.symbol.transcription_flow` | Transcription Flow Arrow | `pathway-symbol` | Transcription direction cue | P1 | stroke, head, rna, outline | Added batch 1; refreshed parity slice 9 |
| `core.dna.protein_binding` | Protein-DNA Binding | `nucleic-acid` | Regulatory binding diagrams | P1 | dna, protein, contact, outline | Added batch 1; refreshed parity slice 7 |
| `core.nucleic_acid.plasmid_vector` | Plasmid Vector | `nucleic-acid` | Cloning and molecular-biology workflows | P1 | backbone, insert, marker, outline | Added batch 2; refreshed parity slice 7; soft-line and manuscript variants parity slice 17 |
| `core.nucleic_acid.crispr_cas9` | CRISPR Cas9 Complex | `nucleic-acid` | Generic gene-editing mechanisms | P1 | protein, guide_rna, dna, outline | Added batch 2; replaced library-audit slice 16 |
| `core.symbol.dashed_arrow` | Dashed Arrow | `pathway-symbol` | Indirect or inferred relationship | P0 | stroke, head, accent, outline | Added batch 1; refreshed parity slice 9 |
| `core.symbol.bidirectional_arrow` | Bidirectional Arrow | `pathway-symbol` | Two-way or exchange relationship | P0 | stroke, head, accent, outline | Added batch 1; refreshed parity slice 9 |
| `core.symbol.secretion_arrow` | Secretion Arrow | `pathway-symbol` | Vesicle export/secretion | P1 | vesicle, stroke, head, outline | Added batch 1; refreshed parity slice 9 |
| `core.symbol.translocation_arrow` | Translocation Arrow | `pathway-symbol` | Movement across boundary | P1 | boundary, stroke, head, outline | Added batch 1; refreshed parity slice 9 |
| `core.symbol.phosphorylation` | Phosphorylation Symbol | `pathway-symbol` | Post-translational modification | P0 | phosphate, connector, accent, outline | Added batch 1; refreshed parity slice 9 |
| `core.symbol.cleavage` | Cleavage Symbol | `pathway-symbol` | Protease/processing mechanism | P1 | blade, handle, cut_line, outline | Added batch 1; refreshed parity slice 9 |
| `core.symbol.drug_inhibition_badge` | Drug Inhibition Cue | `pathway-symbol` | Inhibitor/drug effect annotation | P0 | badge, drug, bar, outline | Added batch 1; refreshed parity slice 9 |
| `core.symbol.interaction_cue` | Small-Molecule Interaction Cue | `pathway-symbol` | Binding/interaction annotation | P1 | molecule, target, connector, outline | Added batch 1; refreshed parity slice 9 |
| `core.pathway.metabolic_cycle` | Metabolic Cycle | `pathway-symbol` | Directed cyclic conversion | P1 | cycle, node, accent, outline | Added batch 2; refreshed parity slice 9 |
| `core.pathway.feedback_loop` | Feedback Loop | `pathway-symbol` | Negative-feedback regulation | P1 | arrow, signal, block, outline | Added batch 2; refreshed parity slice 9 |
| `core.immune.cytotoxic_granule_release` | Cytotoxic Granule Release | `pathway-symbol` | Regulated immune-granule exocytosis | P0 | membrane, granule, cargo, release_path, outline | Added immune-mechanism batch 1; parity slice 12 |
| `core.lab.pipette` | Pipette | `lab-equipment` | Liquid-handling workflow | P0 | barrel, plunger, tip, fluid, outline | Added seed pack; refreshed parity slice 8 |
| `core.lab.petri_dish` | Petri Dish | `lab-equipment` | Culture and colony workflows | P0 | dish, media, colony, outline | Added seed pack; refreshed parity slice 8 |
| `core.lab.well_plate` | Six-Well Plate | `lab-equipment` | Cell-culture and assay setup | P0 | plate, well, media, outline | Added seed pack; refreshed parity slice 8 |
| `core.lab.microcentrifuge_tube` | Microcentrifuge Tube | `lab-equipment` | Sample-processing workflow | P0 | body, cap, fluid, outline | Added batch 1; refreshed parity slice 8 |
| `core.lab.conical_tube` | Conical Tube | `lab-equipment` | Cell/sample-processing workflow | P0 | body, cap, fluid, outline | Added batch 1; refreshed parity slice 8 |
| `core.lab.syringe` | Syringe | `lab-equipment` | Injection/sample-transfer cue | P1 | barrel, plunger, fluid, needle, outline | Added batch 1; refreshed parity slice 8 |
| `core.lab.microscope` | Microscope | `lab-equipment` | Imaging/readout workflow | P1 | frame, lens, stage, accent, outline | Added batch 1; refreshed parity slice 8 |
| `core.lab.tissue_culture_flask` | Tissue Culture Flask | `lab-equipment` | Cell-culture workflow | P0 | vessel, cap, media, cell, outline | Added batch 1; refreshed parity slice 8 |
| `core.lab.plate_96_well` | 96-Well Plate | `lab-equipment` | Screening/assay setup | P0 | plate, well, media, outline | Added batch 1; refreshed parity slice 8 |
| `core.lab.plate_reader` | Plate Reader Readout | `lab-equipment` | Screening/readout result | P1 | instrument, screen, signal, outline | Added batch 1; refreshed parity slice 8 |
| `core.cell.tumor_spheroid` | Tumor Spheroid | `cell` | 3D cell model/oncology assays | P1 | cluster, inner_cell, core, outline | Added batch 1; refreshed parity slice 4 |
| `core.cell.neuron_basic` | Neuron | `cell` | Neuroscience graphical abstracts | P1 | soma, neurite, nucleus, outline | Covered by released `core.cell.neuron_like`; do not add a duplicate |
| `core.cell.astrocyte_like` | Astrocyte-Like Cell | `cell` | Glia context | P2 | cytoplasm, nucleus, accent, outline | Added model-system batch 1; reviewed parity slice 4 |
| `core.sample.blood_tube` | Blood Sample Tube | `clinical-sample` | Generic whole-blood sample workflows | P1 | tube, stopper, blood, label, outline | Added clinical-sample batch 1; parity slice 15 |
| `core.sample.blood_drop` | Blood Drop | `clinical-sample` | Generic blood-sample primitive | P1 | blood, highlight, outline | Added clinical-sample batch 1; parity slice 15 |
| `core.sample.tissue_biopsy_core` | Tissue Biopsy Core | `clinical-sample` | Generic solid-tissue sample workflows | P1 | tissue, cut_surface, structure, outline | Added clinical-sample batch 1; parity slice 15 |
| `core.sample.tissue_section_slide` | Tissue Section Slide | `clinical-sample` | Mounted tissue-section workflows | P1 | slide, coverslip, tissue, label, outline | Added clinical-sample batch 1; parity slice 15 |
| `core.sample.cell_pellet_tube` | Cell Pellet Tube | `clinical-sample` | Processed-cell sample workflows | P1 | tube, cap, supernatant, pellet, outline | Added clinical-sample batch 1; parity slice 15 |
| `core.sample.cryovial` | Cryovial | `clinical-sample` | Generic stored-sample workflows | P1 | vial, cap, sample, label, outline | Added clinical-sample batch 1; parity slice 15 |
| `core.immune.t_cell` | T Cell | `cell` | Immunology mechanisms | P1 | cytoplasm, nucleus, receptor, outline | Covered by released `core.cell.t_cell`; do not add a duplicate |
| `core.immune.macrophage` | Macrophage | `cell` | Immune/tumor microenvironment | P2 | cytoplasm, nucleus, vesicle, outline | Covered by released `core.cell.macrophage`; do not add a duplicate |
| `core.model.cell_spheroid_cluster` | Cell Spheroid Cluster | `model-system` | 3D culture and oncology models | P1 | outer_cell, inner_cell, nucleus, outline | Added model-system batch 1; replaced parity slice 2 |
| `core.model.tumor_glia_coculture` | Tumor-Glia Co-Culture | `model-system` | Brain-tumor co-culture model | P1 | matrix, tumor_cell, glial_cell, nucleus, outline | Added model-system batch 1; replaced parity slice 2 |
| `core.model.mouse_simple` | Mouse Model | `model-system` | In vivo workflow cue | P2 | body, ear, eye, nose, accent, outline | Added model-system batch 1; repaired after visual triage |
| `core.model.mouse_manuscript` | Mouse Model — Manuscript Line | `model-system` | Thin-line in vivo workflow cue | P2 | body, ear, eye, nose, accent, outline | Added parity slice 1 |
| `core.model.yeast_budding` | Budding Yeast Model | `model-system` | Fungal/model-organism workflows | P1 | cell_body, bud, vacuole, nucleus, outline | Added parity slice 19 |
| `core.model.bacterium_rod` | Rod-Shaped Bacterium | `model-system` | Generic prokaryotic/model-organism workflows | P1 | cell_body, nucleoid, ribosome, outline | Added parity slice 19 |
| `core.model.zebrafish` | Zebrafish Model | `model-system` | Aquatic vertebrate/model-organism workflows | P1 | body, fin, eye, outline | Added parity slice 19 |
| `core.model.fruit_fly` | Fruit Fly Model | `model-system` | Invertebrate genetics/model-organism workflows | P1 | body, wing, appendage, eye, outline | Added parity slice 19 |
| `core.model.nematode` | Nematode Model | `model-system` | Invertebrate genetics/model-organism workflows | P1 | body, internal_tract, head, outline | Added parity slice 19 |
| `core.assay.flow_cytometry` | Flow Cytometry Readout | `assay-workflow` | Assay/workflow summary | P2 | plot, gate, event, outline | Covered by released `exp.assay_workflow.flow_cytometry_readout` forms; do not add a duplicate |

## Coherence Rules For Future Batches

- Use the authoring guide before drawing.
- Keep region names shared across related assets.
- Generate/update the contact sheet after every batch.
- Run production and negative validator tests after every batch.
- Add review notes for assets that may be ambiguous or category-borderline.
- Do not mix asset expansion with editor UI features in the same branch.
