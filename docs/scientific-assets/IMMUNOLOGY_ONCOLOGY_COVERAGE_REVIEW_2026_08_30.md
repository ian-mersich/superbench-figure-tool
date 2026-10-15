# Immunology & Oncology coverage review

This collection extends the existing 190-concept scientific library with a focused set of immune-state, checkpoint, tumor-ecology, immunotherapy, and tissue-readout objects. It reuses established Core assets where they already express the biology clearly; it does not create renamed copies of generic T cells, antibodies, peptide–MHC complexes, PD-1/PD-L1, TCR engagement, or cytotoxic granule release.

## Bounded coverage matrix

| Area | Existing | Add now | Later | Out of beta |
| --- | --- | --- | --- | --- |
| Immune cells and functions | Generic T, B, NK, dendritic, macrophage, neutrophil, and plasma cells; generic cytotoxic granule release | Distinct naïve, activated, exhausted, regulatory, CD4+, CD8+, memory, and CAR-T cells; dendritic-cell states; suppressive-myeloid states; phagocytosis, ADCC/ADCP, and whole-cell immune synapses | Tissue-resident lymphocyte and macrophage programs; finer dendritic and innate-lymphoid subsets | Every immunophenotype, activation program, and disease-specific immune state |
| Antigen recognition and costimulation | Peptide–MHC I/II, generic TCR engagement, and the T-cell antigen receptor/CD3 complex | CD28–B7 costimulation; composable endosomal and cytosolic antigen-processing/MHC-loading objects; cross-presentation | B-cell receptor signaling and detailed processing compartments | Exhaustive CD-marker and antigen-presentation catalogs |
| Checkpoints and soluble signaling | PD-1/PD-L1, cytokine receptor, ligand, activation, and inhibition notation | Standalone CTLA-4 receptor; CTLA-4–B7, LAG-3–MHC II, TIGIT–CD155, and CD47–SIRPα interactions; a generic cytokine, chemokine receptor, JAK-associated cytokine receptor, soluble-factor gradient, and leukocyte recruitment | Named cytokine families, separate secretion mechanisms, STAT-family objects, additional context-dependent checkpoint pairs, and innate sensing pathways | A pathway-state atlas or claims that a generic symbol establishes pathway activity |
| Tumor ecology | Tumor cells, fibroblast searchable as cancer-associated fibroblast, endothelium, spheroid, organoid, and xenograft context | Hypoxia, angiogenesis, invasion, epithelial–mesenchymal transition, matrix remodeling, metastatic steps, immune-infiltrated/excluded/desert tumors, and collagen-rich matrix forms | Organ-specific metastatic niches and treatment-specific remodeling states | Full anatomy, histopathology, or disease-specific staging systems |
| Immunotherapy | Generic antibody and antibody–drug conjugate | Checkpoint-blocking antibody, CAR-T, bispecific engager, vaccine/neoantigen, oncolytic-virus, and adoptive-transfer concepts | Additional cellular therapies, delivery systems, and regimen-specific combinations | Treatment recommendations, clinical decision support, or proprietary therapeutic artwork |
| Tissue and response readouts | Tissue section, microscopy, flow cytometry, sampling, treatment, control, and time-course objects | IHC and multiplex-immunofluorescence tissue fields; immune-infiltrated/excluded/desert tumor contexts; regression and persistent-tumor contexts; tumor-volume time course | Spatial-omics layouts and organ-specific pathology patterns | Diagnostic interpretation or an exhaustive clinical biomarker library |

## Add-now inventory

| Catalog category | New concepts | SVG styles |
| --- | ---: | ---: |
| Cells | 16 | 16 |
| Membrane signaling | 14 | 14 |
| Proteins | 8 | 8 |
| Pathway symbols | 20 | 20 |
| Model systems and tissue context | 13 | 14 |
| Assay workflow | 3 | 3 |
| **Total** | **74** | **75** |

The only same-concept form variants are mesh and aligned-fiber views of collagen-rich extracellular matrix. Biologically different states remain separate concepts. State recognition relies on silhouette and internal geometry as well as color.

## Naming and search decisions

- Common field names and abbreviations are recorded alongside descriptive scientific names, including `Treg`, `CAR T`/`CAR-T`, `MDSC`, `PD-L1`, `MHC II`, and checkpoint terminology.
- Searches for `PD-L1` and `MHC II` intentionally retain the established Core results instead of introducing semantic duplicates.
- Searches for `tumor hypoxia` and `immune infiltration` resolve to composable tissue-context objects without implying a measured mechanism or clinical outcome.
- Interaction assets describe the participating receptor–ligand pair. They do not assert activation, inhibition, response, or resistance unless the user adds that relation explicitly.

## Scientific limits

These assets support schematic communication, not cell-state classification, pathology interpretation, or therapeutic inference. Checkpoint, cytokine, response, and resistance objects remain context dependent. The collection deliberately defers rare immune subsets, exhaustive receptor and cytokine families, organ-specific oncology, full anatomy, clinical staging, cloud collaboration, proprietary templates, and licensed third-party catalogs.
