# Precise path editing at screen scale

5 November 2026. Qualified local source checkpoint; beta.25 remains the delivered desktop/web baseline.

The candidate corrects three public editing failures: a zoomed short edge had
no segment target, overlapping bands could select the adjacent edge of a
narrow PDF bar, and a redundant Source badge covered point controls. Segment
Escape also restores the prior native active owner, its control flags and the
node status. Existing Fabric geometry, native source objects and history remain
authoritative. Editable labels remain text.

## Reproduction and implementation

The clean beta.25 baseline supplies no target for a 33.6365-scene-unit closing
edge displayed at about 456% zoom: its visible length is 153.46 CSS pixels.
The controlled evenodd membrane/pore fixture comes from
`tests/vectorEngine.test.mjs`, under rotated, nonuniformly scaled and reflected
nested parents. Eight actual Library assets provide the surrounding scene.
This controlled baseline is distinct from the later actual-Library and
scientific-PDF cases.

`pathLocalPointToCanvas` already includes object and ancestor transforms. The
stage adds viewport zoom once. Admission now uses the existing 4 CSS-pixel
minimum chord and 14 CSS-pixel endpoint margins. The actual chord determines
hit width; the band stays 14 CSS pixels high, within observed native layout
precision. There is no longitudinal minimum-width enlargement or extra DPR
factor. Wheel zoom refreshes disposable segment targets without rebuilding
anchors or changing authored data, selected points or history.

The existing twelve-interval curve samples estimate projected arc length.
Three to twelve target intervals follow that length; smaller sets sample the
actual native curve at approximately equal projected arc distances. This also
repairs the demonstrated short curved-edge gap caused by uneven Bézier
parameter speed. Invalid and degenerate chords remain inadmissible.

When native bands overlap, the existing nearest-curve calculation chooses
among the actual hit-tested editing owners and current segment descriptors.
Equal distances retain DOM hit order. Mouse reshaping and point insertion keep
the existing geometry/history routes. Keyboard insertion projects the focused
chord midpoint onto its native curve. Endpoint and tangent controls retain
priority.

The existing PDF Source-badge policy now also applies during Direct Selection
point editing. The Inspector and context bar retain source details, and other
warnings remain available. Point-overlay entry reconciles a stale rendered
Source badge once; later renders skip that appearance work after it is gone.

## Functional qualification

All cases below use the same clean candidate App SHA-256
`e1aea6dac04f52493b505d2e1b272747a25101ded80be7249c320976da1c2fdc`.
These are unattended Chromium source checks at desktop viewport sizes.

| Case | Checks | Actual Saves | Original screenshots |
| --- | ---: | ---: | ---: |
| Controlled nested compound, 1280×800 light/dark | 528 | 4 | 36 |
| Controlled nested compound, 1440×1000 light/dark | 528 | 4 | 36 |
| Controlled nested compound, 1920×1080 light/dark | 520 | 4 | 36 |
| Actual Library bacteriophage tail compound, 1440×1000 light | 279 | 2 | 18 |
| Genuine Figure 2 PDF bar, 1440×1000 light | 277 | 2 | 18 |
| Total | 2,132 | 16 | 144 |

The four-check difference in each wide case consists only of public view-pan
setup assertions: the target already fits there. Functional assertions remain
in scope. Minimum supported zoom, 100%, maximum zoom, and 32/40/48/150 CSS-pixel
straight and curved edges check admission, trusted segment authority, compact
controls and unchanged selection/history. Meaningful focused segment, anchor
and tangent drags separately check delivered displacement, untouched operands,
other contours, holes and neighbors. Escape is tested while the pointer is
held; completed Undo/Redo compares complete artwork.

Each case downloads two actual files. The warm browser closes and a new browser
process opens the first file; both actual process IDs are required and must
differ. The first cold image precedes navigation and Fit. Continued native
editing and completed Undo/Redo precede the second Save. The PDF comparison is
strict; Library cases retain the established six-decimal numeric policy and
specific derived area-text frame-clip ID/name treatment. Raw models remain
available for independent review.

After deformation, the PDF continuation click uses a current painted interior
point, chosen with the existing zero-tolerance native paint helper. This is
read-only setup followed by a trusted click and exact target-ID assertion; it
is not an independent paint-hit correctness oracle. Grabbed-material and
untouched-operand checks independently evaluate native path coordinates and
world transforms.

Targeted tests pass 140/140. Source-export support retains the segment,
closest-point and modifier tests in generated source CI; seven export-support
checks pass without producing a new full source archive or upstream cache.
Independent source, staged-source and private-preservation reviews pass.
Independent visual reviewers accept all 144 original screenshots. Independent
complete-content review accepts all 16 actual saved files: every unedited
contour and neighbor world residual is zero, and no raw numeric rounding was
needed even in the Library cases. Only the established regenerated ID on an
explicitly marked, non-editable area-text frame clip differs there; its full
paint and geometry are unchanged. Original PDF backing, text, resources,
images/fonts, authored clips and parent metadata remain preserved. In the PDF
case, the maximum observed grabbed-material residual is 0.000109165 scene units,
below the
unchanged 0.005 check; these are geometry residuals, not latency measurements.

## Evidence and limits

Exact plans, source intervals, actual files, raw models, screenshots and clean
process closure are under `qa_artifacts/geometry-20261105/`.
`functional-join.json` binds the eight passing cases; `final-checkpoint.json`
joins source, content and visual review records. The PDF case is
`jobs/pdf-full-09`, the six compound cases use `-final02`, and the actual
Library case is `jobs/library-final-02`. The original missing-target witness,
curved admission failures, Source-badge visual HOLD, failed cold targeting,
350-second owned-controller timeout and rounded-CSS zoom-input failure remain
recorded separately. None is counted as a passing whole case. The larger final
controller ownership budget changes no product timing or behavior limit.

Maintained controllers live in `scripts/geometry_qa/`; see the
[browser playbook](../runtime/BROWSER_QA_PLAYBOOK.md). The PDF run's exact earlier
qualifier is retained as `source-snapshots/qualify-before-canonical-zoom.py`.
Later matrix input reads canonical viewport zoom rather than the rounded CSS
matrix, while retaining the same independent CSS measurement and 1e-5 limit.

This is one bounded geometry correction. It does not complete Scientific PDF
V1, full Illustrator/Affinity parity, topology/deletion, export/reimport or
sustained-drag performance qualification. Existing appearance and timing
failures remain open. No package, website, trust or native-host activation is
part of this checkpoint. Root owns coordinated promotion. The roadmap remains
the same; after integration, node deletion and contour topology are the next
geometry slice.
