# Core Biology Library Audit — 2026-07-19

This audit covers the complete Figure Studio Core Biology pack after parity slice 15: 97 vector styles grouped into 85 concepts across nine categories. It is a quality and discoverability pass, not a catalog-growth batch.

## Outcome

- No P0 scientific or visual blockers remained.
- Five P1 assets were replaced around clearer molecular topology.
- All 85 concepts are discoverable through at least one non-display-name search intent.
- Sixteen cross-category user-intent queries pass expected-result and relevance limits.
- The pack remains 97 styles / 85 concepts; no count-only assets were added.

## P1 Replacement Batch

| Asset | Accepted topology |
| --- | --- |
| `core.channel.ion` | Slim paired walls, uninterrupted negative-space pore through the bilayer, aligned permeating ions |
| `core.transporter.basic` | Asymmetric carrier body, one enclosed substrate pocket and cargo cue, no continuous pore, closed intracellular gate |
| `core.protein.kinase` | Unequal kinase lobes, narrow inter-lobe cleft, entering peptide, active-site phosphate-transfer cue |
| `core.protein.enzyme` | One continuous organic fold, deep complementary pocket, fitted geometric substrate, no kinase-like lobe split |
| `core.nucleic_acid.crispr_cas9` | Asymmetric Cas-like lobes framing visible target DNA, contacting guide RNA, and paired cleavage marks |

Independent visual review passed the paired comparison in color and grayscale at the app's native review scale. Protein–DNA Binding was retained as the CRISPR comparison reference and was not replaced.

## Search Audit

The prior synonym implementation expanded asset haystacks symmetrically. Broad metadata words such as `protein` and `cell` could therefore back-expand into `receptor`, `cancer`, or `immune`, producing noisy results. The canonical `receptor` check returned 42 of 85 concepts.

Search aliases now expand the user's query directionally. Asset metadata remains literal, while common query variants such as `mitochondria`, `microscopy`, `mitosis`, `apoptosis`, and British `tumour` spelling map toward catalog language without contaminating unrelated assets.

Current audited result:

- `receptor`: 10 relevant concepts instead of 42.
- Alternate-intent coverage: 85 / 85 concepts.
- Cross-category intent matrix: 16 / 16 passing.
- Maximum accepted alternate-intent result set: 12 concepts.
- Browser console errors: 0.

The intent matrix covers cancer, receptors, gene editing, blood samples, histology slides, centrifuge tubes, immune checkpoints, antigen presentation, microscopy, mitosis, apoptosis, tumor models, frozen samples, animal models, RNA interference, and cell culture.

## Variant Queue — Complete

Parity slice 17 completed five publication-style items from this queue:

- Generic Antibody and Drug-Conjugated Antibody now have manuscript-line companions.
- DNA Double Helix and Plasmid Vector now have manuscript-line companions.
- Mitochondrion now has a manuscript-line companion.

Parity slice 18 completed the final queue item with `core.rna.strand_linear`, an open ssRNA form companion for the retained `core.rna.strand` hairpin. Both share one concept, four semantic recolor regions, and the explicit `form` axis.

All five publication pairs share exact centerline geometry, element counts, concept ids, and semantic region ids. Canonical browser QA verifies every-region recoloring and soft-to-manuscript-to-soft switching without changing the object id or transform. The RNA form proof separately verifies Hairpin-to-Linear-to-Hairpin switching under nondefault position, scale, rotation, horizontal flip, opacity, selection, and z-order, then compares fresh default forms against DNA, siRNA, and mRNA at 64 px in color and grayscale.

No audited variant item remains. New variants should be justified by repeated use, reusable art recovered from user-owned figure abstracts, or a new documented visual/discoverability gap.

## Accepted As-Is

- All organelles, general cells, immune cells, model systems, lab equipment, clinical samples, pathway symbols, and immune-mechanism components.
- Membrane-signaling assets other than the replaced channel and transporter.
- Protein assets other than the replaced kinase and catalytic enzyme.
- Nucleic-acid assets other than the replaced CRISPR Cas9 complex; RNA Strand is accepted as one concept with Hairpin and Linear forms.

## Evidence

Canonical browser evidence is written under:

```text
qa_artifacts/figure-studio-assets-parity-2026-07-19-v23/
```

The decisive paired renders are:

```text
29-library-audit-p1-topology.png
30-library-audit-p1-topology-grayscale.png
```

Parity-slice-17 publication-variant evidence is written under:

```text
qa_artifacts/figure-studio-assets-parity-2026-07-19-v24/
```

with decisive color and grayscale renders `31-publication-style-companions.png` and `32-publication-style-companions-grayscale.png`.

Parity-slice-18 RNA-form evidence is written under:

```text
qa_artifacts/figure-studio-assets-parity-2026-07-19-v25/
```

with decisive color and grayscale renders `33-rna-form-variant.png` and `34-rna-form-variant-grayscale.png`.

The JSON proof includes the original 85-concept alternate-intent audit and sixteen-query relevance matrix. The initial provenance/license-release audit cleared all 103 styles on owner-attested workspace-output evidence and the owner released the scoped Core Biology asset material under CC0-1.0 on 2026-07-19.

## Parity Slice 19 Follow-Up

The 2026-07-20 thin-category expansion added Budding Yeast Model, Rod-Shaped Bacterium, Zebrafish Model, Fruit Fly Model, and Nematode Model. Independent review rejected an eye-like nematode head dot; the corrected production vector uses a neutral terminal mark. Canonical parity v30 passes 35/35 checks with zero console errors, covers all 90 concepts, and verifies six-concept `model organism`, two-concept `microbial model`, and two-concept `invertebrate model` results.

Current evidence is written under:

```text
qa_artifacts/figure-studio-assets-parity-2026-07-20-v30/
```

with decisive renders `35-model-organism-family.png` and `36-model-organism-family-grayscale.png`. The current 108-style CC0 revision is documented in `docs/scientific-assets/PROVENANCE_LICENSE_RELEASE_AUDIT_2026_07_20.md`.
