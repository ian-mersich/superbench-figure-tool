# Broader biological drawings in the Library — 13 October 2026

The shared Figure and Presentation Library adds 24 original editable drawings and
improves 12 older Core Biology concepts. Four existing RNA-method schematics are
also refined. Including the matched mitochondrial and IgG Thin companions, the
reviewed cohort contains 42 SVGs: 18 revised drawings and 24 additions.

The complete source Library now contains **370 drawings and 329 concepts across
eight packs**. Core Biology contains 132 drawings and 100 concepts. Fourteen new
views, morphologies or ligand states share an existing biological entry; ten new
entities receive separate entries. Color treatments and line weights do not
count as new biological additions.

| Biological system | Improvements and new choices |
| --- | --- |
| Cells | Rounded, spread and cutaway animal-cell schematics; columnar, cuboidal and apical epithelial views; multipolar, bipolar and pseudounipolar neuron morphologies |
| Nucleus | Clearer double-envelope context; an oval cutaway; a separate nuclear-envelope and pore cross section |
| Mitochondria | Cristae connected to the inner membrane; matched Thin artwork; tubular and branched network forms |
| Golgi and ER | Separated Golgi cisternae and nearby vesicles; oblique stack and ribbon forms; connected rough ER sheets and network; separate smooth ER |
| Lysosomal compartments | Improved lumen contents; lysosome cutaway; a separate autolysosome with one outer limiting membrane and illustrative cargo |
| Antibodies | Separately editable heavy and light chains in intact IgG; matched Thin artwork; separate Fab and Fc fragments |
| Receptors and ligands | Ligand-associated and unliganded forms of the same single-pass receptor; a separate extracellular domain; distinct peptide and abstract small-molecule ligand symbols |
| Protein assemblies and catalysis | Explicit three-identical-subunit and two-pair assemblies; clearer enzyme pocket and connected bilobed kinase cleft |
| RNA experiments | Clearer droplet partitioning, oligo-barcoded capture bead, spatial capture array and illustrative RNA-FISH field |

These are schematics. Cell and organelle morphology does not establish health,
disease or activity. An unliganded receptor is not necessarily inactive. Symbols,
subunit arrangements, organelle counts, puncta, array positions and oligonucleotide
segments are illustrative rather than measured data or atomic structures. The
[scientific reference note](BROAD_LIBRARY_REFERENCES_2026_10_13.md) identifies the
primary figures inspected and the limits of each drawing.

## Choosing a drawing

Biological forms have direct graphical previews within their shared Library
entry. Soft and Thin companions stay with the corresponding form. Favorites and
recent items keep their concept identity. A specific query selects its matching
form even when a different form was used previously; for example, searching
“linear RNA” after choosing Hairpin inserts Linear RNA.

Search now distinguishes biological names and aliases from contextual tags.
“Cell” favors whole-cell drawings; “single cell” matches the phrase rather than
unrelated occurrences of its words. Uppercase FISH and RNA-FISH searches resolve
the RNA-imaging schematic, while lowercase fish still finds the model organism.
Messenger RNA has its own accurate name and aliases, without changing its
previously accepted artwork.

## Editing and persistence

All drawings remain native editable vectors with named biological parts. Existing
part identities and default paints are preserved. IgG gains a new light-chain
part; the old heavy-chain identifier remains. The apical epithelial view omits a
nucleus, and focused envelope, smooth ER and autolysosome drawings declare the
parts appropriate to their view or entity.

Leaving point editing now clears its obsolete child-path state. Switching
workspaces restores the whole object selected afterward, while an intentionally
active path selection still restores. Cut paper applies its dark outline stroke
consistently to group and path outlines; the part-color controls report the
actual default paint. Palette and custom recoloring remain separately editable.

Before revision, the current Core and RNA-method catalogs, permission records,
notices and changed SVGs were preserved in each pack's
`revisions/2026-10-13-broad-library-predecessor/` snapshot. Older saved figures keep
their embedded drawing rather than substituting a current Library drawing.
Accepted DNA/RNA and Protein Homeostasis source artwork is retained.

## Validation and source boundary

The final artwork record is
`qa_artifacts/library-drawing-review/final-cut-paper-policy/independent-artwork-review.json`.
An independent reviewer accepted all 126 full-resolution originals: 42 drawings
in Soft color, Cut paper and Technical ink, each shown at native 64, 256 and 512
pixels. Earlier rejected attachment, cleft-density, mitochondrial topology and
metadata claims were corrected and reviewed again. Exact unchanged images were
reused only with recorded source and PNG identity checks.

The canonical browser runner is `scripts/check-library-drawings-browser.py`.
Its final direct and `/web/` runs are under
`qa_artifacts/library-drawings/20261013T142958Z-direct/` and `-web/`. Final browser
results and independent visual acceptance are recorded in the revision receipts:
both routes passed 7,833 checks with zero failures, no page or console errors and
unchanged source. All 42 desktop captures passed independent visual review.
The runner covers 1280, 1440 and 1920 pixel desktop widths in both appearances,
native insertion in Figure and Presentation, part recoloring and point editing,
Undo/Redo, workspace and selection restoration, actual Save/cold Open of both
native file types, editable SVG export and the fourteen historical Core drawings.
A separate native matrix checks all 42 drawings across three treatments and four
palettes on both entry routes. Authored content and part bindings are checked
separately from derived bounds and thumbnails.

Scientific, form-grouping, palette, geometry and revision-chain tests accompany
the source checks. All 98 targeted Python tests and 43 targeted Node tests pass;
the complete eight-pack validator and reproducible Core audit pass. The full Node
suite reports 416 passes and ten failures; all
ten failures reproduce on the unchanged starting commit with the same failure
signals. They cover unrelated PDF/PPTX/source assertions and four native-host
tests still pointing at the former embedded repository layout. The native host
files belong to Core. The comparison is retained in
`qa_artifacts/library-baseline-node/comparison.json`; no assertion was removed or
test skipped to hide that boundary.

This is local canonical Figure source qualification. The installed desktop pin,
public beta.6 package and website deployment are unchanged. Existing CC0 reuse
permission and product-release approval remain separate; the four RNA-method
drawings retain their pending product-release status. The remaining Cell
Architecture, Culture Models and Microbial families also await their own native
qualification. The Figure/PDF v1 milestones and roadmap remain the same. The next
Library qualification slice is those remaining families, with native-host QA
ownership and the existing source-test debt handled in their respective lanes.
