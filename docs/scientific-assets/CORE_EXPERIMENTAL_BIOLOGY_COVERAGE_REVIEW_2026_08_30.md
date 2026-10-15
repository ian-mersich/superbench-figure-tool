# Core experimental biology coverage review

Date: 2026-08-30
Scope: bundled, offline, editable scientific assets and their library workflow in Figure Studio.

## Comparator and clean-room boundary

The review used current official public BioRender material only to understand the breadth and workflow researchers may expect: the public [feature overview](https://www.biorender.com/features), [library overview](https://www.biorender.com/library), category overviews for [cell types](https://www.biorender.com/categories/cell-types), [cell structures](https://www.biorender.com/categories/cell-structures), [proteins](https://www.biorender.com/categories/proteins), [nucleic acids](https://www.biorender.com/categories/nucleic-acids), [lab objects](https://www.biorender.com/categories/lab-and-objects), and [species](https://www.biorender.com/categories/species), plus official help for [search](https://help.biorender.com/hc/en-gb/articles/36112002743965-How-to-use-AI-powered-Smart-Search), [favorites](https://help.biorender.com/hc/en-gb/articles/17605467457181-Favorite-your-frequently-used-icons), [recoloring](https://help.biorender.com/hc/en-gb/articles/29558992677917-Change-an-icon-s-color), [replacement](https://help.biorender.com/hc/en-gb/articles/29561631967517-Using-the-Replace-tool), [connectors](https://help.biorender.com/hc/en-gb/articles/29559245923869-Using-connector-lines), [templates](https://help.biorender.com/hc/en-gb/articles/17605466139421-Using-a-BioRender-template), and [presentations](https://www.biorender.com/features/presentations).

No BioRender artwork, screenshot, template, copy, proprietary category structure, or brand styling was used. The expansion is an original Figure Studio collection drawn from common experimental-biology concepts and recorded for standalone redistribution.

## Ranked coverage matrix

| Rank | Parity dimension | Existing | Add now | Later | Out of beta |
|---:|---|---|---|---|---|
| 1 | Scientific breadth | 90 concepts / 108 editable SVG variants cover common cells, organelles, signaling, nucleic acids, lab objects, and model systems. | A coherent 100-concept core experimental-biology collection spanning cells and tissues, subcellular structures, molecular actors, gene expression, assay notation, methods, readouts, models, and samples. | Specialized immunology panels, developmental stages, host–pathogen systems, expanded anatomy, structural biology, and disease-specific collections. | Exhaustive anatomy and pathology, thousands of specialized icons, and any licensed third-party catalog. |
| 2 | Scientific search and organization | Keyword search and a flat category filter; 17 legacy aliases. | Stable scientific names, explicit synonyms, subcategories, deterministic relevance ranking, and combined offline-pack discovery. | User-defined collections, richer query interpretation, and research-context recommendations. | Cloud AI search trained on proprietary catalog behavior or copied category structures. |
| 3 | Editability and useful variants | Vector insertion, semantic recoloring, replacement, and 18 legacy style variants. | Editable SVG throughout, purposeful form/readout variants, preserved semantic color regions, and stable viewBox/stroke discipline. | Configurable brushes and more continuous shape controls. | Raster substitutes, generative restyling, or attempts to imitate proprietary artwork. |
| 4 | Figure assembly | Click insertion, resize/recolor/replace, and generic bounding-box connector ports. | Scientific connector hints for receptors, molecules, cells, workflows, and directional objects, while retaining generic ports for assets without hints. | Assisted pathway layout and reusable user assemblies. | Cloud-linked collaborative objects or proprietary smart-diagram behavior. |
| 5 | Reuse and discovery | The same bundled library is available in Figure and Presentation modes; user assets are separate. | Favorites, recent-use discovery, clear variant switching, and an original culture → treatment → assay → readout starter. | Shared team collections and personalized suggestions. | Cloud collaboration, organization-wide libraries, and public template marketplaces. |

This beta slice aims for strong coverage of common experimental-biology schematics and a substantially faster local library workflow. It does not claim full BioRender parity.

## Baseline end-user journey findings

One uninterrupted pre-change journey was run in the direct editor at 1440×1000, followed by inspection in Presentation mode. It produced eight findings:

1. The library loaded offline and exposed 90 concepts / 108 styles across nine categories.
2. Figure and Presentation modes both exposed the same scientific assets.
3. Inserted assets remained vector objects with semantic recoloring controls and style replacement.
4. Search for “T lymphocyte” returned T, B, and NK cells without ranking the exact biological synonym first.
5. Search for “mitochondria” found Mitochondrion, confirming partial synonym support.
6. The flat category taxonomy made assay, workflow, and model-system browsing slow as coverage grew.
7. The library had no favorites or recent-use path for repeatedly used concepts.
8. Cards were compact and sometimes truncated names; insertion centered every asset and connectors used generic geometry rather than scientific attachment points.

## Add-now collection

The new collection is intentionally separate from the previously audited `core-biology` pack. Its target is 100 concepts / 108 SVG variants:

| Category | Concepts | Variants | Representative additions |
|---|---:|---:|---|
| Cells and tissues | 22 | 23 | erythrocyte, platelet, monocyte, plasma cell, mast cell, fibroblast, endothelium, ciliated epithelium, tumor cluster |
| Inside the cell | 10 | 11 | centriole pair, mitotic spindle, actin network, microtubules, nuclear pore, nucleosome, ribosome, proteasome |
| Proteins and complexes | 10 | 11 | monomer, homo-/heterodimer, phosphatase, protease, adaptor, scaffold, ubiquitin chain, transcription complex |
| Membranes and receptors | 8 | 8 | T-cell receptor, B-cell receptor, integrin, death receptor, nuclear receptor, endocytosis, exocytosis |
| Genes and expression | 10 | 11 | replication fork, enhancer/promoter, open/condensed chromatin, splicing, tRNA, miRNA, translation, PCR amplicon |
| Interactions and notation | 8 | 8 | conversion, binding, dissociation, degradation, ubiquitination, dephosphorylation, localization, time course |
| Lab methods and equipment | 14 | 14 | centrifuge, flow cytometer, thermal cycler, qPCR instrument, electrophoresis, blot transfer/imager, sequencer, incubator |
| Assays and readouts | 10 | 13 | flow dot plot/histogram, qPCR curve, gel, western blot, microscopy, sequencing reads, ELISA, viability, dose response |
| Models and culture systems | 6 | 7 | organoid, epithelial monolayer, coculture, xenograft, tissue explant, transwell mono-/coculture |
| Samples | 2 | 2 | saliva and urine samples |
| **Total** | **100** | **108** | |

Purposeful variants are limited to concepts where form changes scientific meaning or workflow utility: cancer-cell morphology, actin organization, protein dimer composition, chromatin state, flow-cytometry view, microscopy mode, sequencing layout, and transwell culture configuration.

## Integration boundary

The collection is loaded through an offline library registry, so the legacy pack remains unchanged and independently auditable. The only vector-engine seam is optional normalized connector hints stored with inserted scientific-asset metadata; assets without hints continue to use the existing generic ports. The Illustrator-parity branch can preserve these metadata fields and call the existing connector-anchor function without adopting any asset-library UI or catalog code.

## Post-change end-user journey

One uninterrupted post-change journey was repeated at 1440×1000. The installed library loaded offline with 190 concepts / 216 variants across ten categories and two collections. “T lymphocyte” ranked T Cell first, followed by the more specific T-cell receptor; “mitochondria” returned the Mitochondrion concept and its two variants. T Cell and Mitochondrion were inserted as editable vector objects, recolored through their semantic regions, and switched between useful variants. The same library was available in Presentation mode, and the Favorites and Recent views preserved the chosen T Cell plus the most recently inserted Mitochondrion.

## Acceptance compositions

Three realistic compositions were assembled live from bundled resources only and retained as editable Figure Studio objects. Each composition was reviewed at all required desktop sizes; the PNG dimensions were also checked directly.

| Composition | What was exercised | Captures |
|---|---|---|
| Receptor-signaling pathway | ligand and receptor placement, membrane context, pathway cascade, editable labels, and connector attachment | `qa_artifacts/figure-studio-asset-library-expansion/final-20260830/receptor-signaling/1280x800.png`; `1440x1000.png`; `1920x1080.png` |
| Tumor-microenvironment interaction | cancer cell, T cell, fibroblast, spatial grouping, dashed cell–cell interactions, and editable scientific labels | `qa_artifacts/figure-studio-asset-library-expansion/final-20260830/tumor-microenvironment/1280x800.png`; `1440x1000.png`; `1920x1080.png` |
| Culture → treatment → assay → readout | Presentation mode, starter-scene insertion, coculture asset, treatment/assay sequence, readout plot, and editable text | `qa_artifacts/figure-studio-asset-library-expansion/final-20260830/experimental-workflow/1280x800.png`; `1440x1000.png`; `1920x1080.png` |

Full-resolution inspection found the 1440×1000 captures to be the clearest primary review set. The 1280×800 and 1920×1080 captures retain the same complete composition without artboard clipping or overflow. Labels remain legible, connector endpoints attach sensibly, and no transient tooltip or toast is present in the final files. An independent full-resolution review of all nine final PNGs passed without blockers; it confirmed the named dimensions, complete artboards, sensible connector endpoints, legible labels, and absence of selection overlays or internal product terminology.

The complete 108-variant contact sheet and 64 px matrix were also reviewed independently at full resolution. Every asset remained contained and structurally intact, with no malformed rendering, clipping, stroke/palette outlier, accidental duplicate, or release-blocking scientific ambiguity. Highly abstract round-cell concepts and the mouse xenograft model rely more on labels at 64 px, but their silhouettes and internal details remain distinct; this was accepted as a non-blocking limitation.
