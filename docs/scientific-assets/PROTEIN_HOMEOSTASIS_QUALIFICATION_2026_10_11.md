# Protein Homeostasis artwork and editing review — 11 October 2026

Eight existing drawings cover extended and misfolded protein chains, HSP70 and HSP90 client interactions, ubiquitin attachment and removal, proteasomal processing, and an amorphous protein aggregate. No new concepts, scenes or biological claims were added. The review improves point editing while preserving the artwork's biological meaning.

## Contour refinement

The first native editing review rejected the sampled ribbon outlines: hundreds of closely spaced anchors overlapped and made individual points difficult to choose. The outlines now use compact cubic Bezier curves fitted to the original perimeter. Authored backbone controls and hydrophobic patch intervals are unchanged. SVG element order, other attributes, named regions, colors, titles and descriptions are retained exactly.

| Drawing | Longest preceding contour | Longest revised contour |
| --- | ---: | ---: |
| Unfolded Polypeptide | 159 straight segments | 26 cubic segments |
| Misfolded Protein | 303 straight segments | 40 cubic segments |
| HSP70–Client Complex | 159 straight segments | 11 cubic segments |
| HSP90–Client Complex | 87 straight segments | 7 cubic segments |
| RING E3 Ubiquitination Complex | 51 straight segments | 4 cubic segments |
| Deubiquitinase–Substrate Complex | 87 straight segments | 9 cubic segments |
| Proteasomal Substrate Processing | 159 straight segments | 12 cubic segments |
| Amorphous Protein Aggregate | 159 straight segments | 20 cubic segments |

Thirty-seven sampled contours were changed, including repeated structural outlines. The deterministic fitter bounds error at the original sampled points to 0.5 SVG units before three-decimal serialization. An additional dense numerical comparison samples every cubic at 60 intervals and measures distance to the preceding polygon in both directions. Maximum observed distances are 0.52 units or less for seven drawings and 1.005 units for the aggregate, on a 128-unit artboard. These are numerical approximations, not an analytic bound over every point of the curve. Independent visual inspection checks the resulting silhouettes and patch containment separately.

## Biological interpretation

The [original scientific review](PROTEIN_HOMEOSTASIS_ASSET_REVIEW_2026_10_07.md) and [science record](../../scripts/protein-homeostasis-science.json) remain the basis for the drawings. This round does not claim a fresh inspection of primary-figure pixels or introduce literature-derived geometry.

The extended chain, compact non-native fold and irregular aggregate remain distinct. Chaperone binding does not imply successful folding or activation. RING E3 depicts direct transfer from an E2–ubiquitin conjugate to a substrate, without an E3–ubiquitin intermediate. Deubiquitination concerns the ubiquitin attachment, not cleavage of the substrate backbone. Proteasomal processing shows an entering chain and separate peptide products. The aggregate implies neither amyloid nor toxicity. All shapes remain illustrative schematics without sequence, atomic structure or measured conformation.

## Acceptance

Independent static review passed all eight individual boards at native 64, 128 and 256 pixels in Soft color, Cut paper and Technical ink: 72 artwork cells. Eight additional before/after boards were inspected individually at matching 128- and 256-pixel sizes. No new kinks, gaps, clipping, detached patches or change in topology was observed. The aggregate's small contour bow preserves its irregular chain interactions and gold intervals.

The final native run passes 1,819 distinct acceptance checks across 24 Figure/Presentation treatment and palette combinations, with 39 unique 1440 × 960 captures and no page or console errors. All three treatments and four palettes were checked in both workspaces; each treatment also has an Original-palette Dark capture. Actual Library insertion, all 31 named-region recolors, eight real endpoint clicks and drags, and 24 Undo/Redo actions passed. Endpoint and tangent-control hit areas remain constant at 50%, 100% and 400% zoom.

Later test stages were resumed only after exact app, catalog, SVG and downloaded-file identities matched their completed checks. The record distinguishes the 1,819 unique checks from 3,552 accepted executions across those resumes. Initial dense-anchor rejection and unsuccessful test attempts remain separate evidence; they are not counted as final acceptance. Independent review passed all 39 final captures individually at full resolution, including the eight actual anchor-editing views.

Actual downloaded Figure and Presentation files cold-reopened with all serialized authored fields and object IDs intact. The Figure thumbnail and scene matched exactly. Presentation derived scene coordinates differed by at most 0.004771 pixels, within the explicit 0.01-pixel reconstruction tolerance; its thumbnail differences remained within the existing numerical limits. The historical fixture inserts all eight preceding dense-contour SVGs, saves an actual Figure file and cold-opens it with the current catalog. Its authored fields and IDs remain exact, and its maximum derived scene difference is 0.003719 pixels. Saved artwork is not replaced by current library drawings.

The historical 213 × 150 thumbnail narrowly failed the inherited numerical limits: mean RGBA channel difference 0.308255 and maximum 21, against 0.25 and 20. Those failed limits remain recorded. Independent inspection accepted only this exact before/after pair and its full native scenes: all structures and positions remain intact, with faint variation confined to contour edges. A separate control renders the same serialized preceding artwork with archived and current catalogs and produces byte-identical previews. This specific visual-continuity exception does not change any global threshold or relax the exact authored comparisons.

Independent PPTX inspection passed 122 checks: all 77 ordered vector paths and their paints survived in eight corresponding named SVG pictures, with placed coordinates within 0.00247 pixels. The original Presentation remains exact immediately after **Edit in Figure**. Exporting the copied Figure may update only the original project's non-authoring `lastProxyExportAudit` diagnostic; that difference is recorded separately, with all original slide content unchanged.

Release and source compatibility checks passed all 85 Python cases and 32 Node cases. The eight numerical contour checks and 44 existing Core Biology compatibility cases also passed. The complete library validates at 346 SVG styles, 319 concepts and eight packs; the qualified Protein Homeostasis pack passes the public-source release check and its generated audit matches the recorded version. The rights-filtered subset now has 302 eligible styles, with 44 styles in four other packs still awaiting product review. No full distribution package or public deployment was built in this round.

## Point editing

The native review exposed two shared editing defects. Handle buttons inherited the canvas zoom, making a 22-pixel endpoint hit area grow to 88 pixels at 400% zoom and obscure neighboring points. An inverse-zoom transform now keeps endpoint and tangent-control buttons at 22 and 20 screen pixels while their centers follow the artwork.

An anchor drag can also enlarge a grouped path. Fabric's fit-content layout then recenters sibling coordinates, but the app previously refreshed only the edited object and its parents. Sibling selection bounds could remain stale by about 0.51 pixels until history reconstruction. The hierarchy refresh now updates descendant coordinate caches once after the final ancestor layout. It adds no path, paint, transform or hierarchy changes.

The existing Direct Selection browser regression passed all 18 checks after both fixes, with independent inspection of its four full-resolution captures. It covers discovery of unselected points, grouped isolation, dragging, untouched-point preservation and Undo/Redo. Detailed path editing remains in Figure; Presentation's **Edit in Figure** command opens an editable copy. SVG export of that copy is performed in Figure. Presentation's PPTX export retains the eight drawings as SVG pictures, rather than PowerPoint shapes with individually editable points. It does not imply new PPTX interchange capabilities or destination-application rendering acceptance.

Qualification also exposed a separate existing Presentation navigation issue: creating a new deck can restore the Slides sidebar while retaining an Assets pane flag. The first **Asset library** click then resets that flag, and the second opens Assets. The runner records the actual visible panel state and uses the visible controls to recover. Independent visual review also found poor contrast on inactive document-tab labels in the light-theme Presentation captures. These issues do not change imported artwork or saved document content; the next small UI follow-up should reconcile pane restoration and tab appearance.

## Rights and compatibility

The owner's CC0-1.0 grant remains effective from 10 October 2026. Reuse permission and product acceptance are separate decisions. The original grant and 7 October scientific source record remain unchanged. A supplementary source record identifies the original contour refinements; no third-party artwork was introduced.

The preceding catalog, rights record, notice and eight SVGs are preserved in `assets/scientific-packs/protein-homeostasis/releases/2026-10-10-rights-cleared/`. Stable asset IDs, file names, editable region IDs, paint channels and scientific metadata are preserved. The product receipt binds only these eight changed SVGs and their release/source metadata to the exact preceding snapshot. Other packs and previous Core Biology revisions remain unchanged.

## Reproducing the checks

From the canonical Figure Tool repository:

```powershell
node --test tests/proteinHomeostasisAssetCatalog.test.mjs tests/scientificAssetCatalog.test.mjs tests/scientificAssetArtStyles.test.mjs tests/scientificAssetPalettes.test.mjs tests/scientificAssetColorControls.test.cjs
py -3 -m pytest -q tests/test_protein_homeostasis_contours.py tests/test_protein_homeostasis_assets.py tests/test_protein_homeostasis_release.py tests/test_figure_public_candidate.py --basetemp qa_artifacts/protein-homeostasis-qualification-20261011/p3
py -3 -m unittest discover -s tests -p test_core_biology_revision.py
py -3 scripts/validate-scientific-assets.py --library
py -3 scripts/validate-scientific-assets.py --pack assets/scientific-packs/protein-homeostasis/asset-pack.json --require-public-release
py -3 scripts/generate-scientific-asset-license-audit.py --pack assets/scientific-packs/protein-homeostasis/asset-pack.json --check
py -3 scripts/check-protein-homeostasis-browser.py
```

The short pytest fixture path above keeps output inside the ignored review directory without exceeding ordinary Windows path limits in older compatibility fixtures. The new whole-library test uses the builder's existing extended-path helper and checks its cleanup boundaries.

The browser runner uses the existing Figure source-preview helpers, installed Chromium, Playwright and Pillow. It starts and closes its own local server and uses disposable contexts. Captures, downloaded documents, vector exports and detailed comparisons stay under the ignored `qa_artifacts/protein-homeostasis-qualification-20261011/` root. Original rejection evidence remains in separate attempt folders. No user profile or saved work is modified.

This is a local source review. The Superbench package selection, Windows edition and live website are separate release steps. The release roadmap remains the same. The next short UI slice should reconcile Presentation pane state during document restoration and inactive-tab contrast; the four RNA-method drawings are the next coherent asset family to qualify.
