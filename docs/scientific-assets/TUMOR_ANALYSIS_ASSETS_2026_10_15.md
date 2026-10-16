# Tumor microenvironment and analytical drawing additions

The new drawings connect tumor-associated cells, cell contacts and spatial
microenvironments with common ways of presenting analysis results. This
contribution adds 20 concepts with two useful forms each: 20 drawings in
**Tumor Microenvironment** and 20 in **Analysis Graphics**. They are original
editable vectors, with separate named biological parts or plot components.

Analytical drawings are schematic examples, not measured results or analysis
functions. They use invented coordinate geometry and live, editable axis text.
The Library description and limitations identify this boundary. Researchers
must replace the example marks and labels with verified study-specific content
before presenting results.

## Forms and scientific meaning

| Concept | Two forms | Meaning retained in the drawing and metadata |
|---|---|---|
| Cancer-associated fibroblast | Spindle cell; matrix context | Cell and matrix are separate; CAF subtype cannot be inferred from morphology. |
| Tumor-associated neutrophil | Isolated cell; tumor context | Lobulated nucleus and granules; tumor association does not imply one functional state. |
| CAR-NK cell | Receptor display; target contact | An engineered-receptor cue on a granular NK-cell schematic; no specified antigen or clinical construct. |
| Generic immune synapse | Cell pair; interface close-up | Apposed cells with receptor–ligand contacts; receptor identity and signaling outcome remain unspecified. |
| Dendritic-cell antigen uptake | Soluble antigen; particulate antigen | Extracellular cargo and an intracellular uptake compartment; uptake is distinct from presentation. |
| Macrophage polarization cue | One cue with response range; multiple cues | Environmental influences; no universal M1/M2 binary. |
| Tertiary lymphoid structure | B/T organization; germinal-center cue | An organized B-cell follicle adjacent to a T-cell zone; the mature form adds a possible germinal center. |
| Hypoxia gradient | Vessel-to-tissue; spheroid section | Relative oxygen availability decreases away from supply; paired molecule symbols identify oxygen. |
| Drug penetration gradient | Vessel-to-tissue; spheroid penetration | Compound diamonds decrease away from supply; no dose or penetration depth is implied. |
| Lactate/metabolite gradient | Source-to-tissue; local radial source | An explicit producing-cell source; direction differs from oxygen delivery. |
| UMAP scatter | Separate clusters; continuous state | Embedding coordinates and colors are illustrative; they establish neither cell identity nor lineage. |
| Volcano plot | Threshold overview; feature-label example | log2 fold change versus −log10(q); cutoffs and A/B feature labels are placeholders. |
| Heatmap | Value matrix; column clustering | Features, samples and a relative-value key; dendrogram is schematic. |
| Kaplan–Meier curve | Single group; two groups | Nonincreasing steps and separate censor marks; no cohort or outcome is asserted. |
| Violin plot | Separate groups; split distribution | Hand-authored density envelopes with a placeholder summary guide. |
| Box plot | Vertical; horizontal | Middle-quartile box and median line; whisker rule is unspecified. |
| Scatter plot | One series with guide; two series | A dashed guide is distinct from a fitted model or correlation estimate. |
| Network graph | Hub; modular | Undirected associations, without causal or regulatory arrows. |
| Pseudotime trajectory | Continuous; branching | Inferred state ordering, distinct from elapsed time or lineage tracing. |
| Cell tracking trajectory | One cell; two cells | Ordered spatial positions with endpoint labels or direction arrows, without measured speeds or durations. |

## Literature preparation

Published figures informed scientific meaning and familiar visual conventions.
No published geometry, palette, data coordinates, screenshot, image or vector
component was copied into these drawings. Downloaded reference images are kept
only in ignored local QA output.

Five primary-study figures were visually inspected for the following design
decisions. The complete citation, figure number and specific use are also
recorded in the deterministic source and per-asset metadata.

| Primary paper and inspected figure | Decision informed |
|---|---|
| [Elyada et al., 2019, Figure 1A/B/F](https://pmc.ncbi.nlm.nih.gov/articles/PMC6727976/#F1), DOI 10.1158/2159-8290.CD-19-0094 | Distinguish stromal cells from tumor context; represent distribution width with violin geometry. Cell-state identity requires biological evidence. The t-SNE panel informs the general convention of labeled embedding axes, not a claim that its coordinates are UMAP. |
| [Zilionis et al., 2019, Figure 4B/Q](https://pmc.ncbi.nlm.nih.gov/articles/PMC6620049/#F4), DOI 10.1016/j.immuni.2019.03.009 | Feature-by-sample heatmaps have a labeled relative-value scale. Cell-population interpretation depends on measured markers. |
| [Trapnell et al., 2014, Figure 2A–C/F](https://pmc.ncbi.nlm.nih.gov/articles/PMC4122333/#F2), DOI 10.1038/nbt.2859 | Show cell-state ordering separately from collection time; keep pseudotime distinct from actual tracked motion. A branching schematic does not prove lineage. |
| [Sonveaux et al., 2008, Figure 7](https://pmc.ncbi.nlm.nih.gov/articles/PMC2582933/#F7), DOI 10.1172/JCI36843 | Oxygen delivery and metabolite production can have opposing source directions. The generic assets omit that study's transporters, numerical concentrations and therapeutic mechanism. |
| [Anandi et al., 2024, Figure 1A–C](https://pmc.ncbi.nlm.nih.gov/articles/PMC11487089/#fig1), DOI 10.26508/lsa.202403053 | Make the supply boundary and spatial direction explicit. Qualitative spatial diagrams remain distinct from measured hypoxia-reporter fluorescence or drug efficacy. |

[Liu et al., 2020, Figure 1](https://pmc.ncbi.nlm.nih.gov/articles/PMC7101242/#F1)
was also inspected. Its clinical timelines were deliberately not used as the
structure of the CAR-NK drawing or as a survival-curve precedent. The article
supports the engineered NK-cell identity; the generic receptor arrangement
does not reproduce its construct or clinical outcomes.

Additional primary sources support specific concepts and plotting conventions:
[Cabrita et al.](https://doi.org/10.1038/s41586-019-1914-8) and the
[PLOS ONE TLS histology study](https://doi.org/10.1371/journal.pone.0256907)
for organized lymphoid tissue;
[Sallusto et al.](https://doi.org/10.1084/jem.182.2.389) for antigen uptake;
[Xue et al.](https://doi.org/10.1016/j.immuni.2014.01.006) for multidimensional
macrophage activation;
[Grakoui et al.](https://doi.org/10.1126/science.285.5425.221) for immune-cell
contact;
[McInnes et al.](https://arxiv.org/abs/1802.03426) for UMAP;
[Kuznetsova et al.](https://doi.org/10.1016/j.xpro.2020.100279) for volcano-plot
axes;
[Kaplan and Meier](https://doi.org/10.1080/01621459.1958.10501452) for survival
steps and censoring; and
[Tinevez et al.](https://doi.org/10.1016/j.ymeth.2016.09.016) for tracking
positions over acquisition time. These additional records are scientific
sources, not claims of a full-resolution visual review of their figures.

## Reproduction and review

`scripts/seed-tumor-analysis-assets.py` deterministically authors both packs.
The generator creates pending contribution records and refuses to overwrite a
catalog whose rights/release status has advanced beyond draft. To reproduce
after rights binding, use `--destination-root` under ignored `qa_artifacts/`
and compare the SVGs. `--render-only` writes SVGs while preserving any separate
draft catalog and rights files; an already reviewed pack still requires a fresh
destination. This protects subsequent exact contribution and review records
from accidental regeneration.

`tests/test_tumor_analysis_assets.py` checks 20 concepts with two genuinely
distinct forms each, exact SVG reproduction, safe vector-only primitives,
named recolor regions, survival steps/censoring and the scientific limitations
that prevent the generic diagrams from overclaiming measurements or biology.

`scripts/render-tumor-analysis-assets-review.py` captures all 40 drawings at
actual 64, 256 and 512 pixels in the editor's three drawing treatments, using
unattended Chromium. It records captures and source hashes without assigning
independent acceptance. The source review corrected a heatmap label crossing
its dendrogram, a tracking label crossing a final marker, cytoplasmic fibers
crossing a fibroblast nucleus, and insufficiently distinct oxygen/drug symbols.
Independent review also shortened the matrix-form fibroblast fibers within the
cell border and moved both TLS compartment labels below the tissue silhouette.

Independent artwork, native insertion/editing, save/cold Open, rights and final
release decisions remain separately recorded. This note does not claim those
outcomes or inherit an older pack's owner authorization.
