# RNA artwork review — 11 October 2026

Four existing Superbench Figure Tool drawings were revised: RNA Strand (Hairpin), RNA Strand (Linear), mRNA Transcript and siRNA Duplex. Their outlines are lighter, curves are smoother, and base marks and terminal details connect to the appropriate strand. No new catalog concepts were added.

The library review covered overview sheets for all 346 styles across eight packs, representing 319 concepts. These sheets identified priorities; they do not replace individual scientific, artwork or editing acceptance. Four RNA drawings were selected because their older shapes and disconnected details lagged behind the preceding DNA and chromatin revision.

| Drawing | What the revised artwork shows | Interpretation limit |
| --- | --- | --- |
| Hairpin RNA | One continuous strand with a paired stem, an unpaired connecting loop and free ends | No sequence, measured fold, RNA class or terminal chemistry |
| Linear RNA | One smooth open strand with connected unpaired base marks | Linear is a drawing form, not evidence for an experimentally unstructured state |
| mRNA Transcript | Connected cap, 5′ UTR, one coding region, 3′ UTR and poly(A)-like tail | A typical capped/polyadenylated eukaryotic transcript; lengths are illustrative, and the coding region is not an exon map |
| siRNA Duplex | Two antiparallel strands, connected pairing marks and two illustrative unpaired marks on each opposite terminal extension | No sequence, exact nucleotide count, guide-strand identity or silencing outcome |

## Scientific references

Actual figures were inspected before authoring. They informed biological connectivity and component order. No published artwork, sequence, coordinates or distinctive composition was incorporated into the original SVGs.

- [Danaee et al., *Nucleic Acids Research* (2018), Figure 1A–B](https://pmc.ncbi.nlm.nih.gov/articles/PMC6009582/), DOI `10.1093/nar/gky285`: distinguish the paired stem, unpaired hairpin loop and unpaired terminal regions of one RNA chain.
- [Elbashir et al., *Nature* (2001), Figure 1b](https://www.nature.com/articles/35078107), DOI `10.1038/35078107`: connect opposing unpaired terminal extensions to an antiparallel short RNA duplex.
- [Amrani et al., *Nature* (2008), Figure 1a](https://pmc.ncbi.nlm.nih.gov/articles/PMC2587346/), DOI `10.1038/nature06974`: retain cap → 5′ UTR → coding region → 3′ UTR → poly(A) order without copying sequence or experimental lengths.
- [Ringnér and Krogh, *PLOS Computational Biology* (2005), Figure 1A–B](https://journals.plos.org/ploscompbiol/article?id=10.1371/journal.pcbi.0010072), DOI `10.1371/journal.pcbi.0010072`: distinguish transcript regions and an explanatory single-strand secondary structure.

## Compatibility and source history

Stable asset IDs, concept and form IDs, SVG paths, semantic region IDs, default colors, paint channels and CC0-1.0 reuse terms remain unchanged. The mRNA region label changes from “Segmented coding sequence” to “Coding sequence” because the new drawing deliberately uses one continuous region. Hairpin and Linear remain forms of the same RNA concept.

The preceding October 11 DNA/chromatin catalog, audit, CC0 notice, revision receipt and four original RNA SVGs are preserved under `assets/scientific-packs/core-biology/revisions/2026-10-11-nucleic-acid-redraw/`. The earlier July snapshot and original three-asset receipt remain unchanged. The other 104 current Core Biology records and SVGs, including the accepted DNA/chromatin redraws, retain their exact preceding identities.

The new `revision-2026-10-11-rna.json` receipt binds only these four redraws to their predecessor. Validation retains the earlier identity pins and rejects unrelated artwork or metadata changes, modified predecessor files, extra or missing snapshot files, mixed revisions, receipt drift and undeclared region changes. Historical source and owner records remain an exact prefix of the new audit; the RNA redraw and continued CC0 authorization records are appended separately.

## Acceptance

Independent visual review accepted each drawing at native 64, 96, 160 and 224 pixels in Soft color, Cut paper and Technical ink. All four passed review for connected strand topology, distinct forms, terminal details, readability and clipping. A compact before/after board supports navigation; individual full-resolution boards were used for acceptance.

The canonical browser run passed 148 checks with clean browser telemetry and 16 captures. It tested real Library insertion across three drawing treatments and four palettes, all 16 named color regions, Hairpin/Linear form switching, native anchor editing inside the original group, Undo/Redo and an actual SVG export containing vector paths without raster images.

Actual downloaded Figure files cold-reopened with their authored object IDs, paths, paints, region bindings, hierarchy and metadata intact. A second fixture inserted the preceding catalog and four preceding SVGs, saved a Figure file and reopened it against the new catalog. Its embedded artwork remained unchanged; updating the library does not replace drawings in existing saved figures.

An independent reviewer inspected all 16 final editor captures at original resolution and accepted the artwork across every treatment, palette and theme. The review record binds the exact screenshots, source SVGs and native browser proof; no artwork corrections were required.

Automated checks also passed: 29 catalog/style/palette/color-control cases, all 44 revision compatibility cases (including the preceding 23), and 12 public-candidate contract cases. Core Biology passes its public-release validation for 108 styles, and the complete library validates 346 styles across 319 concepts and eight packs. The audit regenerates exactly. The full-library public-release check still rejects the five pending packs, as expected; this four-drawing revision does not qualify them automatically.

The comparison records retain two existing reconstruction details: Undo can regenerate transient imported-child IDs, while owning asset identity, geometry and correct anchor reselection are tested separately; cold Open rounds serialized transforms to four decimals. The historical scene's derived bounds/matrices differed by at most 0.004163 pixels, within the explicit 0.01-pixel comparison tolerance. Authored native fields and IDs remained exact. Its regenerated 213 × 150 thumbnail differed only in small antialiasing changes, checked separately from the authored payload. These observations did not require changes to the editor.

### Reproducing the checks

From the canonical Figure Tool repository, run:

```powershell
node --test tests/scientificAssetCatalog.test.mjs tests/scientificAssetArtStyles.test.mjs tests/scientificAssetPalettes.test.mjs tests/scientificAssetColorControls.test.cjs
py -3 -m unittest discover -s tests -p test_core_biology_revision.py
py -3 scripts/validate-scientific-assets.py --library
py -3 scripts/validate-scientific-assets.py --pack assets/scientific-packs/core-biology/asset-pack.json --require-public-release
py -3 scripts/generate-scientific-asset-license-audit.py --check
py -3 scripts/check-rna-artwork-browser.py
py -3 -m pytest tests/test_figure_public_candidate.py -q
```

The browser check uses the existing native Figure Tool entry helpers and installed Chromium, Playwright and Pillow. It starts and closes its own local server, uses disposable browser contexts and writes its captures, downloaded figures, SVG export and comparison records only under `qa_artifacts/asset-round2-20261011/native/`. It does not modify user profiles or saved work.

## Next library work

The five newer packs already have owner-authorized CC0 reuse terms. Their product release remains pending; historical October 7–8 review notes about an unresolved license decision have been superseded by the October 10 rights records. This round does not change their release status. Fifty-two styles await final pack qualification, with the eight Protein Homeostasis drawings a coherent next family to test in the app. The RNA capture bead, multivesicular endosome and contractile-tailed bacteriophage passed refreshed individual static review and need editing qualification rather than another redraw.

Confocal optical-path clarity, tumor-volume plot labeling and the older Core Experimental Biology RNA family remain separate artwork follow-ups. The Figure Tool release roadmap remains the same. This is a local source revision; package selection and website publication are separate steps.
