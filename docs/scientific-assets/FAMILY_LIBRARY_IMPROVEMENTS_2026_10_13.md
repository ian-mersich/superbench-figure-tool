# Cell Architecture, Culture Models and Microbial Library — 13 October 2026

The shared Figure and Presentation Library improves all 40 existing drawings in
these three families and adds 36 original editable drawings. Nineteen additions
provide alternative views or states within a shared biological entry; seventeen
introduce additional entities or experimental arrangements. Cosmetic treatments
do not count as biological additions.

The complete source Library contains **406 drawings and 346 concepts across
eight packs**. The three-family cohort contains 76 drawings and 57 concepts.

| Family | Refreshed / added drawings | Current concepts | Biological choices |
| --- | ---: | ---: | --- |
| Cell Architecture & Transport | 16 / 12 | 20 | Junction cross sections and networks; gap-junction and focal-adhesion views; connected and detached vesicle carriers; recycling tubules; ER–mitochondrion contacts; pre/post-fusion compartments; myosin-Va transport, cis-SNARE, inward budding and nuclear export |
| Culture Models & Functional Assays | 12 / 12 | 18 | Cystic and budded organoids, stromal co-culture, embedded and suspended spheroids, hanging-drop and microwell arrays, microcarrier culture, floating/attached collagen gels, submerged/interface tissue slices, dual-channel perfusion, matrix outgrowth and cell-exclusion gaps |
| Microbial Structures & Interactions | 12 / 12 | 19 | Capsule forms, biofilm views, branched/unbranched hyphae, pseudohyphae and germ tubes, paired/chained cocci, isolated outer-membrane vesicles, mother-cell spore enclosure and distinct phage tail architectures |

These are illustrative schematics. They do not establish molecular counts,
dimensions, transport rates, viability, infection, assay response or measured
growth. The [combined scientific reference note](FAMILY_LIBRARY_REFERENCES_2026_10_13.md)
links each family's inspected primary figure precedents and drawing limits.
Published or proprietary illustration geometry is not incorporated.

## Choosing and editing drawings

Biological alternatives appear as direct graphical choices within their shared
Library entry. Whole-object names and form aliases are separated from contextual
component terms. For example, a septal pore remains searchable as part of a
septate hypha, while the identity alias names the hypha itself. Opposite-form
phrases are removed from both aliases and tags; a floating-gel query does not
select an attached gel remembered earlier. Culture parent names remain neutral
so their different arrangements have accurate headings.

All drawings are native SVG vectors with named editable biological parts. Every
previous identifier, file path, category, part identifier, paint channel and
default color is preserved. New forms can declare parts appropriate to the
depicted structure. Existing favorites and older documents keep their biological
identity. The previous 40 SVGs, complete catalogs, permission records and license
notices are retained in each pack's
`revisions/2026-10-13-family-expansion-predecessor/` snapshot.

Independent artwork review rejected and corrected specific topology and clarity
issues: hyphal septal partitions, viral contents touching a fusion membrane,
contracted-phage baseplate position, cytosolic Arf1 placement, and culture-model
spacing, nuclei, boundaries and outgrowth geometry. Fresh originals closed each
issue. An inherited hemidesmosome figure attribution was also corrected while
preserving the original historical record.

## Validation

Independent review accepted all 228 full-resolution artwork boards: 76 drawings
in Soft color, Cut paper and Technical ink, each at actual 64, 256 and 512 pixels.
The final generic rendering is under `qa_artifacts/family-library/artwork-final-frozen/`.
All source SVG hashes match the accepted originals. Culture diagrams were
reviewed again where inline-SVG and image rasterization differed at pixel edges;
approximate pixel similarity was not reported as exact reuse.

The canonical direct and `/web/` runners use `--cohort families`, with evidence
under `qa_artifacts/family-library/final-direct-requalified/` and
`final-web-requalified/`. The six cases
are 1280×800, 1440×1000 and 1920×1080 in light and dark. Their scope includes:

- Actual Library insertion of all 76 drawings in Figure and Presentation.
- Graphical form selection, favorites/filter regressions, whole-object selection
  and genuine child-path selection through workspace switching.
- Native part recoloring and anchor editing on one representative from each
  family, with exact Undo/Redo geometry and preservation of other objects.
- Actual Save downloads and cold Open of `.fsfigure` and `.fsdeck`, including all
  40 predecessor drawings in both native file types under the current catalog.
- Editable SVG export, and all 76 drawings in the twelve actual native
  treatment/palette combinations on each route.

The direct route passed 15,845 checks and the web route passed 15,888. Both
retained unchanged runtime source throughout, with no failed checks, page errors,
console errors or unexplained request failures. All 42 desktop originals passed
independent full-resolution review; exact decoded-pixel reuse is identified where
applicable. Each route's treatment matrix covers 912 actual native drawing states.

The larger cohort exposed two assumptions in the QA harness. History pruning is
now reconciled against actual step and byte-budget pruning, while exact single
Undo/Redo checks remain. `artifact_store_count` is a shared runtime cache-size
counter and is excluded at its two telemetry locations; actual artifact
references, embedded artwork and other storage fields remain exact. A targeted
negative check verifies that authored content changes still fail. Independent
review accepted these narrow comparator corrections.

The web runner also verifies the requested appearance at the host, editor and
effective-theme boundaries. Fresh contexts apply their system appearance before
the editor opens. The former redundant click raced the host's adoption of theme
controls into its Browser files menu. A cold-launch probe reproduced the hidden
control failure and verified real menu-based theme switching. The failed web
attempt is retained separately in `final-web/`. An earlier successful direct
candidate binds its archived original driver before this web-only correction.
The final requalified routes use the same corrected driver and identical source.

Final source validation rejected one redundant alias, `tight-junction strand
network`, because it normalized to the drawing's scientific name. Eleven
dependent Python cases failed on that one defect. The rejected candidate's
catalog, audit, tentative receipts, validation logs and native review are
preserved. The correction removes only that alias and aligns seed filtering with
the validator's punctuation-aware normalization. All 76 SVGs, visible labels,
identifiers, paint channels, permission records and dated audits remain intact.
Both complete native routes were rerun against the corrected catalog. A durable
read-only catalog/schema/SVG preflight now runs before browser launch, with a
positive corpus check and a negative duplicate fixture. It never substitutes
for exact receipt, rights or release validation.

Final native results, independent desktop acceptance and strict-validator totals
are recorded in the three finite family revision receipts. Each dated audit and
receipt binds the current source, the complete predecessor and accepted evidence;
the validator rejects modified or unreviewed source, even with a regenerated
rights audit. The earlier Core Biology and RNA revision tests remain unchanged
and all 98 pass.

The final targeted Python run passed all 158 cases, including all 18 family
mutation cases after passing cloned baselines, the current notice bindings,
seed reproduction, schema regression and unchanged Core/RNA checks. Complete
Library validation passed for 406 SVG drawings / 346 concepts / eight packs.
The Core Biology license audit remains current for all 132 drawings. All 50
focused Node asset tests passed. Final logs are retained in
`python-requalified-validation.log`, `library-requalified-validation.log` and
`node-requalified-assets.log` under `qa_artifacts/family-library/`.

The complete canonical Node suite has 423 passes and ten inherited failures. All ten match
the preceding qualified slice's failure names; there are no newly failing cases.
The remaining cases cover PDF/PPTX/source assertions and native-host tests that
still reference the former embedded layout. Their sources belong to the Core
host. No assertion was removed or skipped to hide those failures. The bounded
comparison is retained in `qa_artifacts/family-library/node-comparison.json`.
The suite enumerates `tests/**/*.test.mjs` explicitly; unrestricted discovery
also scans ignored historical release and vendor copies and is retained as a
separate, unsuitable qualification run.

## Source and roadmap

This qualifies local canonical Figure source. Existing CC0 permission and
product-level release approval remain separate. The four pending-release packs
now contain 80 drawings; the installed desktop pin, public beta.6 package and
website deployment have not been advanced. Accepted Core Biology, DNA/RNA and
Protein Homeostasis artwork remains intact.

This completes the planned native qualification of the three remaining families
while providing the broader improvements and additions requested for this slice.
Figure/PDF v1 milestones and the roadmap remain the same. A reviewed Figure
package decision is the next release boundary; native-host QA relocation and
the existing tumor-volume/confocal quality follow-ups remain separate work.
