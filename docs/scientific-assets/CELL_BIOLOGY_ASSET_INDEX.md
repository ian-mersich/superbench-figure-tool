# Cell Biology Asset Index

This index is the working checklist for cell-biology, tumor, lineage, and cell-state assets. It is intentionally broader than the current production `core-biology` pack so future batches can be selected from a durable list instead of improvised per prompt.

Status values:

- `core`: already in `assets/scientific-packs/core-biology/asset-pack.json`
- `draft`: parked in `docs/scientific-assets/draft-exports/`
- `planned`: candidate concept not yet drafted
- `next-batch`: selected for the next reference-guided cell-biology draft batch
- `defer`: useful but currently too specific, too hard to draw clearly, or better as a composed scene

## Current Coverage

| Concept | Search terms | Current status | Asset ids / notes |
| --- | --- | --- | --- |
| Generic eukaryotic cell | cell, generic cell, eukaryotic | `core` | `core.cell.generic` |
| Epithelial-like cell | epithelial, adherent, junction | `core` | `core.cell.epithelial` |
| Apoptotic cell | apoptosis, cell death, blebbing | `core` | `core.cell.apoptotic` |
| Dividing cell | mitosis, proliferation, cell division | `core` | `core.cell.dividing` |
| Tumor spheroid / cell cluster | tumor spheroid, organoid, cluster | `core` | `core.cell.tumor_spheroid` |
| Nucleus | nucleus, nucleolus, chromatin | `core` | `core.nucleus.round` |
| Mitochondrion | mitochondrion, cristae, metabolism | `core` | `core.mitochondrion.basic` |
| Vesicle / endosome / lysosome family | vesicle, endosome, lysosome, cargo | `core` | `core.vesicle`, `core.endosome.basic`, `core.lysosome.basic` |
| Cell-culture context | flask, plate, incubator, cell counting | `draft` | culture/assay batch context assets, not cell-type assets |

## Tumor And Cancer Morphology

| Concept | Search terms | Status | Notes |
| --- | --- | --- | --- |
| Cancer cell, round variant | cancer cell, tumor cell, malignant cell, round | `draft` | `draft.cell.cancer_round`; duplicate display name `Cancer Cell` is intentional. |
| Cancer cell, spindle/mesenchymal variant | cancer cell, spindle, invasive, EMT | `draft` | `draft.cell.cancer_spindle`; useful for invasion/metastasis diagrams. |
| Cancer cell, irregular giant-cell variant | cancer cell, pleomorphic, giant cell | `draft` | `draft.cell.cancer_giant`; keep generic; avoid claiming a diagnosis. |
| Tumor cell cluster | tumor cells, cancer cells, cluster | `draft` | `draft.cell.tumor_cluster`; distinct from `core.cell.tumor_spheroid` by looser cluster shape. |
| Solid tumor mass | tumor mass, lesion, solid tumor | `draft` | `draft.cell.solid_tumor_mass`; compact mass/spheroid cue. |
| Invasive front / migrating cancer cell | invasion, migration, leading edge | `draft` | `draft.cell.migrating_cancer`; conservative single-cell leading-edge/protrusion cue. |
| Cancer stem-like cell | cancer stem cell, stem-like, tumor-initiating | `draft` | `draft.cell.cancer_stem_like`; uses non-overclaiming stem/state cues. |
| Metastatic colony | metastasis, colony, seeded tumor cells | `draft` | `draft.cell.metastatic_colony`; small seeded colony distinct from tumor spheroid. |

## Immune And Hematopoietic Lineages

| Concept | Search terms | Status | Notes |
| --- | --- | --- | --- |
| T cell / lymphocyte | T cell, lymphocyte, immune cell | `core` | `core.cell.t_cell`, `core.cell.t_cell_manuscript`; high nucleus-to-cytoplasm ratio with restrained paired receptor cues. |
| B cell / lymphocyte | B cell, lymphocyte, surface immunoglobulin | `core` | `core.cell.b_cell`, `core.cell.b_cell_manuscript`; membrane-bound Y-shaped surface-immunoglobulin cues distinguish it from generic T/NK lymphocytes. |
| Macrophage | macrophage, phagocyte, immune cell | `core` | `core.cell.macrophage`, `core.cell.macrophage_manuscript`; broad lobopods, kidney-shaped nucleus, and restrained vacuoles. |
| Dendritic cell | dendritic cell, antigen-presenting cell | `core` | `core.cell.dendritic`, `core.cell.dendritic_manuscript`; compact soma with seven asymmetric curved processes and restrained distal branching. |
| Neutrophil | neutrophil, granulocyte, lobed nucleus | `core` | `core.cell.neutrophil`, `core.cell.neutrophil_manuscript`; connected three-lobed nucleus and fine granules. |
| Red blood cell | RBC, erythrocyte, red blood cell | `draft` | `draft.blood.red_blood_cell`; simple biconcave disc. |
| Platelet | platelet, thrombocyte, clotting | `draft` | `draft.blood.platelet`; small fragment with clotting/fibrin cue. |
| NK cell | NK cell, cytotoxic lymphocyte | `core` | `core.cell.nk_cell`, `core.cell.nk_cell_manuscript`; broader cytoplasmic rim, mildly indented nucleus, and restrained internal granules. |
| Plasma cell | plasma cell, antibody secretion | `draft` | `draft.immune.plasma_cell`; eccentric nucleus plus antibody secretion cues. |
| Monocyte | monocyte, kidney nucleus, myeloid | `draft` | `draft.immune.monocyte`; kidney-shaped nucleus and vesicle cues. |
| Mast cell | mast cell, allergy, granules | `draft` | `draft.immune.mast_cell`; dense granule cue. |
| Eosinophil | eosinophil, bilobed nucleus, granulocyte | `draft` | `draft.immune.eosinophil`; bilobed nucleus and orange granules. |
| Basophil | basophil, dense granules, granulocyte | `draft` | `draft.immune.basophil`; dense granules partly obscure nucleus. |

## Immune Recognition And Effector Mechanisms

| Concept | Search terms | Status | Notes |
| --- | --- | --- | --- |
| MHC-I peptide complex | MHC-I, class I, peptide-MHC, antigen presentation | `core` | `core.immune.mhc_i_peptide`, `core.immune.mhc_i_peptide_manuscript`; one anchored heavy chain, unanchored beta-2-microglobulin-like partner, and contained peptide. |
| MHC-II peptide complex | MHC-II, class II, peptide-MHC, antigen presentation | `core` | `core.immune.mhc_ii_peptide`, `core.immune.mhc_ii_peptide_manuscript`; separately editable alpha and beta chains, two anchors, and overhanging peptide. |
| TCR peptide-MHC engagement | TCR, T-cell receptor, peptide-MHC, immune synapse | `core` | `core.immune.tcr_engagement`, `core.immune.tcr_engagement_manuscript`; class-neutral pMHC support and paired TCR chains across opposing membranes. |
| PD-1/PD-L1 engagement | PD-1, PD-L1, immune checkpoint | `core` | `core.immune.pd1_pdl1_checkpoint`, `core.immune.pd1_pdl1_checkpoint_manuscript`; binding-only checkpoint component with distinct one-domain and two-domain silhouettes. |
| Fc-receptor binding | Fc receptor, Fc binding, antibody | `core` | `core.immune.fc_receptor_binding`, `core.immune.fc_receptor_binding_manuscript`; receptor contacts the Fc stem of a soluble IgG-like antibody without an effector outcome. |
| Cytotoxic-granule release | cytotoxic granule, degranulation, exocytosis | `core` | `core.immune.cytotoxic_granule_release`; cargo-rich granules and a membrane-fused omega profile without target-cell damage. |

Deferred mechanism specificity: HLA alleles, CD4/CD8 co-receptors, CD3 signaling, checkpoint-blockade therapy, Fc-receptor subclasses, antibody isotypes, immune-complex crosslinking, named perforin/granzyme cargo, target-cell pores, apoptosis, and cytotoxic-synapse outcomes.

## Neural And Glial Lineages

| Concept | Search terms | Status | Notes |
| --- | --- | --- | --- |
| Neuron | neuron, neurite, axon, dendrite | `draft` | `draft.neural.neuron`; broad graphical-abstract staple. |
| Astrocyte-like cell | astrocyte, glial cell, processes | `production` | `core.cell.astrocyte_like`; adapted from user-owned Figure Studio graphical-abstract artwork. |
| Oligodendrocyte-like cell | oligodendrocyte, myelin, glia | `draft` | `draft.neural.oligodendrocyte_like`; includes myelin-wrap cues. |
| Microglia-like cell | microglia, ramified immune cell | `draft` | `draft.neural.microglia_like`; ramified surveillance morphology. |
| Schwann cell / myelin segment | Schwann cell, myelin | `draft` | `draft.neural.schwann_myelin_segment`; axon plus myelin segment cue. |

## Stromal, Vascular, And Tissue-Context Cells

| Concept | Search terms | Status | Notes |
| --- | --- | --- | --- |
| Fibroblast | fibroblast, spindle cell, stromal cell | `draft` | `draft.stromal.fibroblast`; useful for tumor microenvironment diagrams. |
| Endothelial cell | endothelial cell, vessel lining | `draft` | `draft.vascular.endothelial_cell`; elongated lining cell. |
| Smooth muscle cell | smooth muscle, contractile cell | `draft` | `draft.stromal.smooth_muscle_cell`; spindle cell with contractile-fiber cues. |
| Adipocyte | adipocyte, fat cell, lipid droplet | `draft` | `draft.stromal.adipocyte`; highly recognizable and easy to recolor. |
| Osteoblast-like cell | bone cell, osteoblast, bone matrix | `draft` | `draft.bone.osteoblast_like`; matrix-secreting bone-forming cell cue. |
| Osteocyte-like cell | bone cell, osteocyte, canaliculi | `draft` | `draft.bone.osteocyte_like`; stellate cell in lacuna with processes. |
| Chondrocyte-like cell | cartilage cell, chondrocyte | `draft` | `draft.cartilage.chondrocyte_like`; cartilage lacuna/matrix cue. |

## Epithelial And Barrier Context

| Concept | Search terms | Status | Notes |
| --- | --- | --- | --- |
| Epithelial sheet | epithelial layer, junctions, monolayer | `draft` | `draft.epithelial.epithelial_sheet`; multi-cell asset useful for barrier/tissue figures. |
| Polarized epithelial cell | apical basal, epithelial polarity | `draft` | `draft.epithelial.polarized_cell`; apical/basal/junction cues. |
| Ciliated epithelial cell | cilia, airway epithelium | `draft` | `draft.epithelial.ciliated_cell`; apical cilia and airway accent. |
| Goblet-like secretory cell | secretory epithelial cell, mucin | `draft` | `draft.epithelial.goblet_secretory`; apical secretory/mucin granule cue. |

## Stem, Development, And Model Cells

| Concept | Search terms | Status | Notes |
| --- | --- | --- | --- |
| Stem cell / progenitor cell | stem cell, progenitor, differentiation | `draft` | `draft.cell.stem_progenitor`; conservative cell-fate cue. |
| Organoid cluster | organoid, mini organ, cell cluster | `draft` | `draft.cell.organoid_lumen`; distinct from tumor spheroid via central lumen. |
| Blastocyst / embryo-like cluster | embryo, blastocyst | `defer` | Sensitive/specialized; skip for now. |
| Yeast cell | yeast, budding yeast, model organism | `production` | `core.model.yeast_budding`; redrawn and promoted in parity slice 19. |
| Bacterium | bacterium, bacillus, microbe | `production` | `core.model.bacterium_rod`; generic rod form with nucleoid and ribosome cues, promoted in parity slice 19. |

## Implemented Cell-Biology Draft Batch

The first reference-guided cell-biology batch broadened search coverage quickly and gives users multiple visual answers for broad terms like `cancer cells`, `tumor`, `immune cell`, `neuron`, and `stromal cell`.

Implemented batch folder:

```text
docs/scientific-assets/draft-exports/reference-guided-cell-biology-batch-2026-05-07/
```

Drafted concepts:

- Cancer Cell, round variant
- Cancer Cell, spindle/mesenchymal variant
- Cancer Cell, pleomorphic/giant-cell variant
- Tumor Cell Cluster
- Solid Tumor Mass
- T Cell / Lymphocyte
- Macrophage
- Dendritic Cell
- Neutrophil
- Red Blood Cell
- Neuron
- Astrocyte-Like Cell
- Fibroblast
- Endothelial Cell
- Adipocyte
- Epithelial Sheet

## Implemented Zero/Low-Count Cell Batch

The second cell-biology batch was selected from zero-count planned terms and low-count families in `docs/scientific-assets/MASTER_ASSET_INDEX.md`.

Implemented batch folder:

```text
docs/scientific-assets/draft-exports/index-guided-zero-low-cell-biology-batch-2026-05-08/
```

Drafted concepts:

- B Cell
- NK Cell
- Platelet
- Microglia-Like Cell
- Oligodendrocyte-Like Cell
- Schwann/Myelin Segment
- Smooth Muscle Cell
- Polarized Epithelial Cell
- Ciliated Epithelial Cell
- Stem / Progenitor Cell
- Organoid With Lumen
- Budding Yeast Cell
- Bacterium

Budding Yeast Cell and Bacterium were later redrawn as original production vectors for parity slice 19. The historical draft batch remains reference-only.

## Implemented Cell-State And Tissue-Context Batch

The third index-guided cell-biology batch filled planned tumor-state terms, tissue-context cells, secretory epithelium, and immune-lineage gaps.

Implemented batch folder:

```text
docs/scientific-assets/draft-exports/index-guided-cell-state-tissue-batch-2026-05-08/
```

Drafted concepts:

- Cancer Stem-Like Cell
- Migrating Cancer Cell
- Metastatic Colony
- Osteoblast-Like Cell
- Osteocyte-Like Cell
- Chondrocyte-Like Cell
- Goblet-Like Secretory Cell
- Plasma Cell
- Monocyte
- Mast Cell
- Eosinophil
- Basophil

## Next Index Expansion

Good candidates for the next cell-biology batch:

- Cell-state variants for apoptosis, senescence, quiescence, and cycling/proliferation, if broad search utility is worth the added specificity.
- Microenvironment/context assets such as extracellular matrix, basement membrane, hypoxia region, necrotic core, and immune infiltration as diagram components rather than standalone cells.
- More microbial/model organisms, such as coccus bacterium, fungal hypha, or virus-like particle, if the catalog expands beyond mammalian cell biology.
- Blastocyst / embryo-like cluster remains deferred unless explicitly needed
