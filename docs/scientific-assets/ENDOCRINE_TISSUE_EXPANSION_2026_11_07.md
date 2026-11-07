# Endocrine tissue drawings and templates — 7 November 2026

This contribution adds 24 original editable drawings across 12 new endocrine
tissue concepts. Each concept has two structural forms and matching Styles
1–4, with the same named biological parts available for recoloring. Styles
and forms are separate choices; style companions do not add concepts.

The source Library now contains 550 drawings across 410 concepts in 14 packs,
24 scientific templates and three layout starters. The delivered beta.29
remains the editor baseline for source testing. Package activation and matched
desktop/web publication belong to the coordinator.

| Biological structure | Forms |
| --- | --- |
| Thyroid follicle | Single follicle; follicle field |
| Parathyroid parenchyma | Interwoven cords; lobular field |
| Pancreatic islet | Mixed cell clusters; folded cell plates |
| Adrenal cortex | Concentric zones; cortical wedge |
| Adrenal medulla | Nests around sinusoid; medullary field |
| Pineal parenchyma | Pinealocyte groups; lobular field |
| Anterior pituitary | Interlacing cords; radial tissue field |
| Posterior pituitary | Longitudinal neural lobe; transverse neural lobe |
| Median eminence | Sagittal neurovascular section; portal interface field |
| Antral ovarian follicle | Eccentric oocyte section; sector section |
| Corpus luteum | Folded luteal tissue; radial luteal tissue |
| Leydig-cell interstitium | Paired tubule profiles; tubule junction field |

The four templates cover hypothalamic–pituitary–adrenal feedback,
hypothalamic–pituitary–thyroid feedback, glucose–islet feedback and an islet
perifusion experiment. Hormone feedback and experimental apparatus serve
different purposes. The perifusion template supplies editable conditions,
collection stages and a readout placeholder; it contains no secretion data.

These are qualitative tissue schematics. Cell counts, proportions, dimensions
and colors do not represent measurements or identify an endocrine state.
Species and physiological context affect tissue organization and feedback.
Scientific details and primary references remain with each drawing or template.

## Source and preservation

Original coordinates, tissue compartments, labels and relationships are in
`docs/scientific-assets/expansion-2026-11-07/`. Regenerate only this contribution
with `python -B scripts/seed-endocrine-templates.py`.

The new pack is `assets/scientific-packs/endocrine-tissue/`. Its Style 4
companions have a separate dated collection under `style-4/expansion-20261107/`.
The flat `style-4/original-companions.json` lookup map is an exact ordered union
of the November 3 and November 7 companion records, with paths resolved from
the Style 4 directory. The existing loader consumes it without application,
controller or cache-key changes.

The 486 historical Style 4 mappings, their artwork and records, and all
November 3 neurobiology/tissue art and records are preserved. The prospective
repository CC0 policy applies to this original contribution; it does not
extend historical personal attestations. Reuse permission, scientific review,
appearance, native editing and product inclusion remain separate decisions.

## Qualification

The whole-library and Style 4 validators pass. All 76 targeted JavaScript tests
and 31 Python tests pass, including form discovery, equal style coverage,
geometry preservation, exact aggregate lookup and rejection of altered or
escaping aggregate records. Independent scientific reviews and full-resolution
art review are recorded under `qa_artifacts/assets-templates-2026-11-07/`.
All 96 drawing/style views and four template previews pass independent visual
review. `art-acceptance-02.json` replaces one thyroid-axis preview after moving
two labels above their connector lines and retains the other 99 image bindings.
Earlier failed checks and rejected views remain in their original records.

Native editor checks recolored all 112 named parts across the 24 Style 4
drawings. Eight representative drawings exercised all four styles and four
form replacements. Each template received a live text edit and a named-part
color edit. The drawings and templates were saved as actual figure files and
reopened in new browser processes. Independent saved-content and original-image
reviews are recorded beside each case. The engineering note records the scope
and limits of Undo/Redo and derived geometry comparisons.

The roadmap remains the same: complete one coherent reviewed content batch,
then let the coordinator qualify and deliver a matching package. This slice
fills a previously absent biological family without changing the Inspector or
PDF work. Further biological expansion follows acceptance of this batch.
