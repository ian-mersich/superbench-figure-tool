# RNA-method assets and scientific drawing review — 7 October 2026

This slice adds four original, editable RNA-method concepts and two editable Scenes. It also revisits five drawing weaknesses identified in the September library review. The source library contains 271 concepts and 298 SVG styles: 294 styles in the existing released packs and four RNA-method drafts. Scenes contain ten previously released recipes and two RNA-method drafts.

## RNA concepts

| Object | What the drawing communicates | Interpretation limit |
| --- | --- | --- |
| Microfluidic cell partition | An aqueous suspension and oil flow producing droplets | It does not guarantee one viable cell and one bead in every droplet. The vertical streams depict oil; they are not cell or bead inlets. |
| Oligo-barcoded RNA capture bead | A bead bearing capture oligos with shared cell barcodes, distinct molecular identifiers and oligo(dT) ends | Cell barcodes and UMIs have different roles. The diagram does not specify a commercial chemistry, sequence, bead loading or capture efficiency. |
| Spatial RNA capture array | Tissue associated with positional capture sites | A capture site may contain RNA from multiple cells. Resolution depends on the method and sampling. |
| Illustrative RNA puncta in situ | Localized RNA-probe signals within cellular and nuclear context | The puncta are schematic, not microscopy data or measured transcript counts. |

The drawings are original SVG geometry. Primary papers informed the scientific cues; their artwork, layouts and prose were not copied or traced. Source references and semantic color-region definitions are retained in the pack manifest.

## Editable Scenes

- **Droplet single-cell RNA workflow:** cell suspension → droplet partitioning and RNA capture → cDNA library → sequencing → barcode and RNA reads. A separate bead detail explains cell barcodes and UMIs. It does not imply a bead enters through an oil inlet.
- **Spatial RNA methods:** location-barcoded tissue capture and sequencing are shown separately from probe hybridization and RNA imaging in fixed tissue. The imaging route does not feed its puncta into the sequencing library.

Assets, text and relationships remain separate editable vectors. Each Scene retains its source-node definitions, groups and relation mappings. Previews embed the original SVG drawings rather than raster substitutes.

## Scientific precedents

- [Macosko et al., Cell (2015), Figures 1–2](https://pmc.ncbi.nlm.nih.gov/articles/PMC4481139/): droplet partitioning, RNA capture, bead-associated barcodes and UMIs.
- [Ståhl et al., Science (2016), Figure 2](https://pubmed.ncbi.nlm.nih.gov/27365449/): positional RNA capture beneath a tissue section and the distinction between capture-feature and cell resolution.
- [Raj et al., Nature Methods (2008), Figures 1–2](https://pmc.ncbi.nlm.nih.gov/articles/PMC3126653/): RNA localization through probe hybridization and fluorescence puncta, with method-specific validation.

## Draft rights and publication

The new pack uses `FS-ORIGINAL-DRAFT`, exact source/provenance digests and `public_distribution_authorized: false`. The two new Scene records have the same explicit pending status. Existing CC0 notices cover their listed historical releases; they do not automatically license these additions. Scientific and browser acceptance are separate from the owner's public-license decision.

The validator now accepts an explicit local draft state while requiring its pending license, zero cleared rights, exact file identities and unresolved release decision. Historical released packs retain their existing release checks. Negative tests reject silently selecting CC0, authorizing distribution, clearing pending rights or changing an SVG without refreshing its exact record.

Use `python scripts/validate-scientific-assets.py --library --require-public-release` before public packaging. Local structural validation accepts these drafts; the publication gate deliberately rejects them until the owner's license decision is recorded.

## Acceptance and follow-up

Independent static review accepted the four RNA drawings
at original resolution (24 asset originals), and all five revised contextual drawings
at 64 and 352 px in the three treatments (30 originals). Corrections made before
acceptance keep cells visible in the alternate droplet treatments and keep the
Lumen, Low O₂, TAA and MHC labels outside faded contour groups. Semantic outline
recoloring changes those labels and their contours together.

Browser work reproduced an unrelated-region recolor erasing an earlier component
opacity edit. The shared scientific importer now retains primitive-to-region
bindings, and recoloring changes requested paints on the edited native group.
Component text, geometry, opacity, identities and other paint remain intact.
Older structures that cannot be matched safely are refused without changing
artwork or history; the picker returns to the retained color and offers direct
component editing. The bounded component-text/Save/Open/recolor and legacy-refusal
proof passes 33 checks; it uses the endothelial label to exercise editable text.

Thumbnails now display on neutral light paper in both interface themes. This
preserves the SVG paint while making small contextual labels readable in the Dark
Library. The new Scenes explicitly center their native relationship labels over
the arrow midpoints, with saved offsets and the same initial font as their vector
previews. Other Scenes retain their existing placement behavior. A native numeric
edit exposed a label snapping back before its new offset was recorded; the
numeric transform owner now updates the arrow geometry before storing that
offset, then refreshes the label. This also avoids double movement when a numeric
selection contains the label and its connected icons. A single Undo step is retained.

Selecting a Scene does not move its labels or change its saved artwork. Midpoint
labels and manually bent arrows retain their saved coordinates while the editor
temporarily groups a selection. Native anchor calculations use the same coordinate
precision as portable files, so restoring a saved Scene does not move its arrows.
The focused tests include repeated Select All, mixed endpoint/label movement,
manual bends, exact native restoration and preservation of earlier Scene behavior.

The full library validator passes all 298 SVG styles. The focused Python Scene
and draft-rights tests pass 20 cases; the Node catalog, Scene, treatment and
connector-label tests pass 48 cases. Exact authored-payload comparisons retain every native field. The
RNA runner separately records regenerated manifest bounds differences of at most
0.0001 px, consistent with Fabric's four decimal serialization places; it rejects
all other changes. Its independent source review and negative preflight pass.

The fresh final browser matrix on 7 October 2026 passed 2,346 checks in the shared
editor and standalone web host, each in Light and Dark at 1280, 1440 and 1920 px.
It exercised all nine new or revised concepts in three treatments, individual
component and region-color edits, complete Undo/Redo, actual portable Save and
cold Open, editable SVG output, both RNA Scenes and a populated Present round
trip. Native relationship text, font size and movement remained editable through
history and restoration. All ten earlier Scene definitions retained their source
nodes and relation mappings. There were no console, page or HTTP failures; the
owned browser and server were closed.

Independent review accepted and reconciled all 85 final originals: 56 native UI
captures, 27 artwork pages showing two native scales each, and two vector-preview
captures. It verified the actual image list, bytes, dimensions and capture intent,
and independently confirmed that all 52 bound application/QA sources and 44
scientific sources remained exact. These results qualify the current source and
web entry routes; installed Windows builds, staged revisions, arbitrary PDF
compatibility and public distribution require their own qualification.

This tracked record retains the findings. Ordinary screenshots, downloads,
references and rejected diagnostics under `core/qa_artifacts/figure-assets-rna/`
require disposal under the generated-output policy. On 7 October, automatic
approval review rejected the exact-root cleanup with only "blocked by policy";
no deletion ran. This chat retains responsibility for their pending cleanup.
They are temporary QA, not permanent release evidence. A caption encoding error confined to temporary
artwork-review HTML was recorded separately and corrected in the runner after
the frozen matrix; the asset and native Scene text were unchanged.

The protein-homeostasis family, tumor-volume plot labeling and clearer confocal optics remain separate follow-ups. This slice advances the existing Figure authoring plan while the PDF workstream continues. The roadmap, v1 milestones and PDF acceptance target remain unchanged.

Rebuild the two Scene recipes and their vector previews with `python scripts/seed-rna-methods-scenes.py` from the Figure component directory. This command records drafts; it does not promote a public license.
