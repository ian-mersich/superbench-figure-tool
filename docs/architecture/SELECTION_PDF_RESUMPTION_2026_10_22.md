# Selection and scientific PDF implementation resumed

## Active plan — 5 November 2026

Ian has changed the immediate priority. Beta.24 is the delivered baseline;
its two drag-start corrections and the qualified editable-text/Save/Open
behavior must be preserved. See the [current acceptance status](FIGURE_PDF_V1_STATUS.md).
Smoother sustained dragging and compositing/coverage/replay investigations are
deferred. The existing reuse and rounding assessments are closed checkpoints.

Work in this order:

1. **Selection and Direct Selection reliability, with readable feedback.**
   Close one demonstrated failure or missing public-gesture case on ordinary
   artwork and an existing genuine scientific PDF. Cover click, marquee and
   Shift add/remove; the intended body, stroke or anchor target; retention of
   the selected set; and compact feedback that does not obscure the artwork.
2. **Groups and Layers consistency.** Make canvas selection, Layers targeting,
   whole-group movement, child editing and isolation entry/exit agree, without
   unintended movement or ownership changes.
3. **Precise geometry editing.** Cover anchors, tangents, segments, deletion and
   topology, followed by mixed text/path transforms on nested, rotated and
   reflected artwork.

Existing functions and completed pilots are the starting point. Diagnose actual
behavior before changing code; missing evidence alone is not a product bug.
Choose the fastest credible reuse-first route without duplicate tools or
competing scene/history systems. Preserve native text/source content,
cancellation, Undo/Redo, actual Save and fresh-process continued editing.

Use the maintained unattended browser workflow, public gestures and natural
painting for each coherent slice, with targeted regression checks and independent
original-image review. Reuse fixtures and compact output. Run the broad desktop
and theme matrix on a winning candidate. Root coordinates desktop/web promotion;
this plan does not qualify or activate unfinished changes. The Selection and
editable-PDF requirements remain those in the [parity contract](SELECTION_AND_PDF_PARITY_2026_10_21.md).

### Local selection candidate — 5 November 2026

Six corrections now address failures reproduced through public gestures:
mixed Direct Selection marquees accept Fabric's temporary multi-selection;
Shift-click removes the final whole object without breaking constrained dragging;
ordinary Shift marquees toggle native-resolved hits against the existing set;
Escape restores an ordinary body drag without adding history; Redo retains
world positions for multi-selected owners; and modifier-click can remove the
final selected anchor while retaining whole editable labels. These reuse the
existing selection, transform and history paths. Real group/page boundaries
remain enforced; linked-dependent and scaling cancellation are outside this slice.

The clean candidate preserves beta.24's two startup fixes and excludes private
renderer experiments. Targeted tests pass 158/158. The maintained browser
controller passes 150 checks on eight actual Library assets at 1440×1000 light,
and 96 checks each on ordinary/genuine-PDF artwork at 1280×800 light and dark.
The real-asset journey includes native text/shape companions, transformed and
overlapping artwork, nested contents/Layers targeting, actual Save, new-process
Open and continued editing. A focused initial-view correction passes another
30 ordinary checks per theme; independent review accepts all six replacement
captures, including the complete editable note. The original cropped captures
and all failed pilots remain retained.

The aggregate independent source review is clear. Exact source, original-image
and saved-file review records are retained under
`qa_artifacts/selection-reliability-20261105/`. Nineteen failures in a separate
older diagnostic VM suite are unchanged from baseline and are not counted as
passing targeted tests. These are bounded functional checks, not a full desktop
matrix, renderer/fidelity comparison, timing qualification or release. Beta.24
and the installed desktop host remain unchanged.

Root accepted selection checkpoint `9483a817` as bounded source work. It is
not a desktop/web delivery. The next Groups/Layers slice below uses the actual
saved composition rather than repeating Library insertion.

### Combined Selection and Groups/Layers candidate — 5 November 2026

The Groups/Layers slice fixes three reproduced problems: Shift-click retained
the final nested child; hiding or locking an ancestor left its child editable
by ArrowRight; and hovering a restored nested object could reach Fabric before
its control coordinates were initialized. Isolated selection now uses the
existing ancestor-aware Layers policy. Reconciliation removes unavailable
targets, retains available siblings and editable labels, and keeps the current
group path. Native control coordinates use Fabric's existing initialization.
No second selection/history system or renderer API was added.

The maintained controller passes 146 checks at 1440×1000 light on the retained
eight-asset composition and genuine saved Figure 2. It covers canvas,
Inspector and Layers targeting, depth-two entry/exit, final-child toggles,
ancestor hide/lock, exact unchanged artwork/history after blocked ArrowRight,
Undo/unlock/show recovery, available-sibling retention, meaningful Escape,
completed Undo/Redo, four actual Saves and new-process continued editing.
All 171 targeted unit tests pass, including 13 native Canvas/Group/Path/Textbox
controls; the preceding accepted source fails 12 of those new controls.

Independent saved-content review found that the first small asset drag could
pass its movement check on floating-point residue after snapping. The QA now
requires at least one scene unit of actual movement and uses a larger public
drag, with production snapping retained. A focused 68-check asset rerun passes
with meaningful warm/cold movement, cancellation, Undo/Redo, two new actual
Saves and fresh-process continuation. Its two files and 13 original images
replace the earlier asset movement evidence; the qualified PDF portion is
unchanged. The application source did not change for this oracle correction.

Independent source and saved-content reviews are clear, and all 20 effective
unique originals are accepted: 13 new asset images and seven unchanged PDF
images. A separate clarification corrects the initial identification of the
hidden antibody versus the two components of its synapse sibling; the original
review remains unchanged. Actual-file and source records are retained under
`qa_artifacts/groups-layers-20261105/`. Earlier diagnostic VM failures remain
outside the targeted passing suite. The scope remains bounded functional
qualification, without a full desktop matrix, fresh PDF import, export/reimport,
source-fidelity, general Illustrator/Affinity or timing claim.

Released editable PDFs retain their current workflow: an unselected canvas
click can enter their contents. The existing Layers **Select on canvas** command
selects the whole imported plot, which remains a whole owner on the canvas;
supported Inspector or canvas entry then reaches its original children.
This slice qualifies those public routes without changing that policy.

Freeze the combined candidate for Root's next delivery review. Before the first
release archive, add the new selection/group regression tests to source-export
support and run them in the actual slim export. No new export, package or
activation is part of this checkpoint. Beta.24 remains selected on desktop/web.
The roadmap remains Selection/Direct Selection, Groups/Layers, then precise
geometry; geometry follows combined delivery review. Sustained dragging remains
deferred.

## Historical resumption — 22 October 2026

22 October 2026. The user reviewed the joint Figure/coordinator summary and explicitly resumed work on the remaining selection gaps and the genuine Figure 2 typography failure. The [parity contract](SELECTION_AND_PDF_PARITY_2026_10_21.md) and all existing acceptance limits remain authoritative. The delivered beta.16 source and paired web/desktop payload remain the selected baseline; this working branch does not independently update either consumer.

The dated evidence and historical next steps below retain their original scope;
the active plan above determines the current work order.

## Historical evidence and work

| Case | Current evidence | Required next proof |
| --- | --- | --- |
| Whole/subset selected-body motion, off-center anchors, transformed nested cubic curves | Delivered bounded beta.14/beta.16 public gestures, cancellation, Undo/Redo, actual Save and fresh-process continuation | Retain as regression controls alongside the new cases |
| Quadratic and compound paths | Public Q terminal-anchor motion demonstrated a missing incoming shared control. The bounded fix now passes complete-scene paint, exact geometry, protected fields and Undo/Redo. Compound seam movement passes with an explicit evenodd hollow contour | Broader anchor/control/body gestures, Save/cold continuation and the full desktop matrix |
| Tangent controls and modifiers | Public ordinary-anchor Shift motion demonstrated the missing constraint. The fix passes the same frozen public controller and 250 ms paint limit. Tangent-specific modifier behavior still lacks joined public qualification | Record Affinity differences and exact settings, then actual tangent gestures with no grab jump and correct paired/unpaired controls |
| Mixed line/path selections; open paths without fill | One native open line plus a rotated, nonuniformly scaled open cubic passes selected-anchor movement, Escape and completed Undo/Redo, with independent content/image acceptance; explicit stroke reshaping is tested separately | Ordinary modifier behavior, structured line/arrow classes, paint timing, actual Save/fresh Open and the broader desktop matrix |
| Segment and topology operations | Public Q/C segment witnesses demonstrated incorrect grabbed-point response, changed out-and-back geometry/history and failed Escape. The bounded snapshot/native-coordinate fix passes eight trusted pointer samples, unchanged endpoints/neighbors, raw return/no history and Escape | Completed segment edits, natural paint, Undo/Redo, Save/cold continuation; distinct node/segment split/join and compound-contour operations remain separate |
| Layers, group entry and isolation targeting | Delivered nested-click correction is bounded | The same leaf/selected set through Layers and canvas entry/exit, without content movement or unintended group ownership |
| Sustained dense dragging | A paced nine-position held Figure 2 gesture passes before and after actual Save/fresh Open. The controller waits for each natural paint; this does not qualify queued input or ordinary-rate responsiveness | A predeclared two-second trusted stream without per-move inspection/settling waits, retaining raw frame/event/blocking intervals and all existing budgets |
| Figure 2 typography | Native PDFium glyph painting reduces the opened page's significant difference from 3.358% to 0.1902%; the normal full editing/Save/fresh Open/continued editing/export journey passes on the combined source | Retain independent actual-file/original-image acceptance; qualify the full desktop matrix, dense responsiveness and exact binary provenance/notices before delivery |

These are evidence categories, not a list of newly diagnosed bugs. Each implementation change must answer a concrete public failing case. The completed scratch Fabric controls pilot and VectorCraft comparison are historical decisions; do not rerun them unchanged. Upstream working behavior is preferred where it shortens reliable integration. A different internal object layout is not grounds to reject reuse, but two competing permanent scene/history authorities are not acceptable.

The first source changes reuse the existing 45-degree constraint helper for ordinary anchor drags and extend operand selection so a quadratic's single control follows either adjacent selected anchor once. Fifteen actual-source tests pass, including off-center Shift motion/zero return and nested transformed open/compound quadratic contours. The unchanged executed controller is retained at `qa_artifacts/t22/sel/controller0.py`, with its small dependency manifest in `executed-1/`. Its initial failures and raw paint verdicts remain unchanged. Fresh bounded results are `s1/` (Shift pass; first correct paint 236.1 ms) and `q1/` (Q geometry/history pass; paint unresolved). These diagnostics do not yet qualify Save, cold Open, the full desktop matrix or v1.

The maintained point-gesture regression at `qa_artifacts/t22/p1/` passes 45 checks on the same source: ordinary off-center anchor motion, attached cubic controls, transformed nested editing, cancellation, actual Save and fresh-process Open/continued editing. Both browser processes close and the owned job reports zero survivors. This protects delivered behavior; it does not extend the new Q/compound cases' saved-continuation coverage. Twenty-four native-paint/transform regression controls and five diagnostic geometry-oracle controls also pass. Independent coordinator source review finds no actionable regression in the bounded Shift/Q change. Q shared-control movement is a declared Figure invariant; the retained native Affinity witness is cubic and does not establish general quadratic parity.

The corrected Q result is `qa_artifacts/t22/sel/q4/`: 22 checks pass, first correct paint 142.1 ms and stable paint 235.2 ms. Its oracle includes the complete visible path scene, actual fill rules/caps/joins and implicit fill boundaries; the same five-unit exclusion applies to every sampled pixel in the existing 3×3 footprint. Six finite isolated controls pass separately in `oc/`, including explicit omission/wrong-rule/wrong-boundary negatives. The original incomplete-domain reports remain failed. Compound `c2/` passes with the hollow contour present. Neither oracle repair changes the RGB-2, 250 ms or 80 ms criteria.

Segment witnesses `sq/` and `sc/` retain all original failures. The corrected `sq1/` and `sc1/` pass 14 checks each, including all eight delivered material-point displacements, exact raw return with no history and a separate meaningful-preview Escape. They do not yet qualify segment paint latency or completed-edit persistence. The implementation derives each sample from the original commands through the native inverse scene transform. A Q control uses its Bernstein response; the declared C choice minimizes total control displacement while moving the grabbed material point and retaining both endpoints. This is a Figure behavior choice, not a claim about Affinity's control-distribution algorithm. Segment start focuses the stable viewport; Escape restores raw legacy node metadata, prior selection and cached ancestors. Completed PDF segments use the existing cooperative point-history recovery path. The current combined source passes 44 targeted Node and seven diagnostic Python controls; broader qualification is active.

Independent review of all 20 original Q/compound/segment images accepts their declared visual scope; named unchanged-neighbor regions and both segment returned buffers remain exact. `independent-first-fixes-review.json` retains the exact differing source contexts rather than labeling every earlier result as current. A later source review found that segment Escape also needed to restore the prior primary object and complete edited-object set when another path was grabbed. That correction has a fresh independent source GO and 22 actual point/segment tests, including real begin/cancel calls on a non-primary target that was either already edited or newly added. Its non-primary public browser branch remains pending.

Typography diagnosis verifies both exact source TTF programs loaded by PDFium, all 128 used printable display-code/glyph-ID mappings, and 2,576 printable source/live glyph positions. Initial constructor diagnostics retain their rejected string/count/query assumptions. The corrected matched `font/f3/` pass-through and `font/f4/` source-program/cmap-alias substitution load all four exact expected FontFaces at both registration stages, preserve all glyph origins and native paint inputs, and produce seven byte-identical PNGs. Independent `font-source-cmap-causal-review.json` verifies the live capture boundary reuses the same objects without cloning or reloading fonts. This is a bounded negative: the substitution does not correct this page's 3.358% mismatch. It does not establish general font-engine equivalence or qualify instrumented timing. Source-program/cmap swapping is retired as a correction route for this page; offline glyph coverage and rasterization diagnosis continues. No typography product change has been accepted.

`qa_artifacts/t22/h1/` passes 104 paced held-input continuation checks on the committed checkpoint source. The same genuine source marker follows nine alternating positions during one held gesture, then nine reverse positions after actual Save/fresh-process Open. Each individual move passes the existing natural-paint predicates; maximum first correct paint is 121.8 ms warm and 121.4 ms cold. The held intervals last 10.5 and 12.969 seconds because the controller prepares its oracle and waits for stable paint between moves. Complete protected artwork, one final history step, Undo/Redo, both actual Saves, original PDF bytes and a real PDF export pass producer checks. The coordinator's joined actual-file/original-image review at `h1-review/coordinator-review.json` accepts paced continuity only: 55 content checks and all 39 bound PNGs, including five unique originals and native pixel crops. This does not extend source-PDF fidelity. The two-second ordinary-rate gesture, p95/max frame gaps, blocking, repeated performance and memory gates remain open.

Completed segment qualification is active. The `sq4/sc4/np4` raw failures exposed an absolute-coordinate test defect: `MouseEvent` truncates fractional client positions and therefore changes the independently chosen grabbed material point. The corrected `executed-5` controller uses plain fractional pointer-shaped input with native and independent upper-canvas/VPT mapping, then requires agreement with actual trusted pointerdown within .005. Seven isolated oracle controls pass. `sq5` now passes all eight material-point responses and complete held/returned/canceled geometry, but retains a paint timing failure. Its timer starts at pointerdown while the producer awaits eight intermediate geometry inspections before issuing the final requested move. The action origin is being corrected to the uniquely declared final input; the unchanged 250 ms/RGB-2/80 ms criteria and original failed reports remain retained. No additional product change follows from either controller defect.

The final-target timing correction passes its independent source review. `sq6` then reaches actual Save, fresh Open and continued editing but retains a failed Redo paint observation: its uppercase key filter never admits the actual lowercase `z` delivered with Ctrl+Shift. The observer's own final geometry is already correct, but its absent event/samples provide no timing acceptance. The exact installed Playwright mapping and maintained observer trigger independently establish this recorder defect. Corrected `executed-7` now records trusted key/code/modifier/target traces. Fresh `sq7` passes all 78 checks on the unchanged checkpoint App, including final-target natural paint, completed edit, Undo/Redo, actual Save and fresh-process continuation. The largest observed first correct paint is 84.3 ms. This qualifies one producer case pending independent original-image/actual-file review; C/non-primary and the desktop matrix remain active. Neither final-target result qualifies all intermediate segment pixels or unpaced segment responsiveness.

The continuous controller has separate independent preflight reviews for real closing-tail coverage, finite-number rejection, passive intermediate RGBA, complete 16-corner footprints, frozen input prediction and loaded-helper binding. Its first `continuous/r1` run stops before input because two safe probes do not meet the declared three-probe requirement. Bounded diagnostics distinguish the cause: the coarse 0.5-world candidate grid admits seven safe pixel centers but no triple at least five buffer pixels apart. A separately declared finite 0.25-world refinement admits 31 safe centers and a valid triple while retaining every original boundary/clip/protected-leaf/window/RGB predicate. `probe-cardinality-diagnosis.json` binds these failed/pre-input records. The refined controller still requires three probes, five-pixel separation, two-world clearance, RGB-2/opaque pixels, 250 ms final-target paint and 80 ms stability; no continuous runtime acceptance follows yet.

The completed cubic case `sel/sc7/` exposed a genuine precision defect: its grabbed material point followed input, but one control's independently predicted displacement differed by 0.01368 world units. Replaying the old nearest-point function reproduces the captured operands exactly. Its authoring interpolation rounds each intermediate de Casteljau step, introducing false minima into the nearest-curve search. The bounded correction evaluates raw native commands without rounding inside `closestSegmentRawT` and refines the same sampled bracket for 36 iterations. Authoring rounding and the existing endpoint inset remain unchanged. Ten actual-source regression controls pass, including the literal failed cubic and independently derived transformed Q/C/S/closing-seam cases; the old source fails them. The failed cubic's control error falls to 0.000000235 world units. This is a bounded local nearest search, not a global nearest-point proof for arbitrary self-intersections.

Fresh corrected-source `sel/sc8/` passes 78 checks and `sel/np8/` passes 92, including non-primary edited-member selection, raw return, meaningful Escape, actual Undo/Redo, Save and fresh-process continuation. Owned jobs close with zero survivors. Independent C content review passes 57 checks and explicitly retains its bounded scope. Q `sq7/` has a separate 54-check independent content acceptance on the prior checkpoint source. The winning combined source still needs fresh Q/full-desktop qualification, independent original-image review and continued second Save/real PDF export for these segment cases. These results do not qualify unpaced segment responsiveness or Affinity's control-distribution algorithm.

Dense continuous runs remain failed. `continuous/r2/` takes approximately 11–12 seconds to deliver the declared two-second stream; its five-second final-event admission timer also causes diagnostic capture during the gesture. The corrected admission window changes no post-event paint deadline. CPU-instrumented `r3/` admits both final events and passes final paint at 108.4/146.1 ms, but its moving frame p95 remains approximately 83 ms. About six seconds of full-scene rendering dominate the warm CPU profile, with substantial live-text painting. The recorder also counted upper selection `after:render` events as lower artwork paints. Fabric emits both contexts, so two callbacks do not demonstrate two full artwork paints. Corrected `executed-5` retains all contexts, admits artwork/pixel evidence only from the exact lower context, and passes 14 Python plus six Node controls. Prior raw failures remain unchanged; a fresh context-aware diagnostic is required before choosing a bounded performance correction.

Seven native PDFium glyph controls at `font/m1/` establish a useful limited capability: new text objects reconstructed from independently parsed source charcodes, font handles and matrices match all seven isolated originals exactly on the absolute source pixel grid. Twelve of fourteen full-source ROI comparisons pass; the retained regular-E differences are seven neighboring D/tick fringe pixels omitted by isolation, outside the E outline. The raw full-source HOLD remains unchanged. A private browser/WASM pilot is being prepared to test the same isolated comparison and a separately loaded portable font; no browser-font integration, editable-text replacement or typography acceptance follows from the native control. The 3.358% full-page typography failure remains open.

The joined independent segment review at `segment-review/coordinator-review.json` accepts bounded ordinary segments only: Q/C/non-primary content checks pass 54/57/67, and all 71 PNG references (36 unique original-resolution editor/canvas images) pass visual inspection. Source contexts remain explicit; Q uses the earlier checkpoint, C/non-primary the corrected source. A separate P2 observation records a black Fill swatch for the translucent brown fixture without assigning an introduction date or blocking the accepted geometry. The broader matrix, second Save/export and dense/Affinity/typography claims remain open.

Fresh normal `continuous/r4/` passes 62/70 checks and retains its performance failure. It records exactly 120 artwork and 120 selection paints per gesture, no unknown contexts, and 22 lower-context pixel observations. Both windows, complete input/model correspondence, protected artwork, actual Save/fresh Open/continued second Save and PDF export pass. Warm/cold stream duration is 9.504/11.321 seconds; lower-paint p95 is 87.6/126.4 ms. This confirms one slow full artwork paint per delivered move rather than duplicate full paints. Existing offscreen region helpers are not a safe direct substitute because they change paint context/phase and only cull top-level roots; Figure 2 has one root. A private same-context clipped-paint diagnostic is being prepared before any product performance change.

## Execution and ownership

The private same-context clipped-paint experiment C1 is retired as a negative.
It failed both exact visible output and responsiveness, and was not integrated.
Its 290-pixel mismatch was recorded without retaining the exact pre-repair pair;
the later full-render PNG must not be presented as that rejected comparison.
The independent rejection record retains this limitation. Full-scene painting
remains authoritative.

The browser PDFium reuse control W3 passes all 22 declared pixel comparisons,
including the original seven glyphs and one separately loaded bold E. Its strict
scientific-E extraction criterion and the earlier W1/W2 failed criteria remain
separate. That isolated control led to a canonical `PdfPositionedText` paint
adapter: existing Fabric text, Unicode, placement, caret, history and export
remain authoritative; PDFium supplies derived black glyph tiles from the exact
registered display programs. Actual cold Open registration, retained-tab font
lifetime, cancelled multi-font loads, exact descriptors and exception cleanup
have targeted controls. Native computer use stays stopped outside actual
Affinity comparisons.

The first integrated whole-page attempt `font/integration/i1/` failed visibly:
8.097% significant difference, with inverted/clipped glyphs. Native
`FPDF_RenderPageBitmapWithMatrix` first applies the page's default display y
flip and page-height translation. Cancelling that transform in the supplied
matrix corrects the actual page. Fresh `i2/` measures **0.1902%** significant
difference and 0.001320 blurred MAE, below the unchanged 2.5% and 0.01 limits.
Both real programs (64,396 and 83,192 bytes) paint all 60 + 68 used display codes,
with no native fallback or error. Actual unedited PDF export also passes.
This is a bounded typography improvement, pending independent original-image
review and full editing/persistence qualification. The run remains **HOLD**:
the opening foreground gap is 573.3 ms against the unchanged 250 ms limit.
The native binary is a local functional candidate with redistribution held
until complete dependency notices and exact source provenance are resolved.
Neither beta.16 selection nor the roadmap changes.

The normal complete `i5/` journey passes 54 of 55 checks. The unchanged opening
appearance is independently accepted at original resolution. Real Unicode text
editing, physical text-size Undo/Redo, actual Save, fresh-process Open, exact
warm/cold artwork pixels, continued caret/character selection and typing,
continued full-leaf Undo, Redo text, a second actual Save with complete artwork
and uniquely identified authored text, and final PDF export all pass producer
checks. The only remaining failure is the 390.9 ms opening gap. Earlier `i3/`
anchor/vector Undo failures remain recorded: its controller called Undo before
the cooperative point-history step finished and then compared a stale vector
record. A reviewed exact-step readiness wait fixes the fresh run without a
product history change or geometry tolerance change. The shared glyph-atlas
candidate `i6/` is retired: it preserves all opened pixels exactly but worsens
Open to 12.874 seconds with a 2,732.7 ms foreground gap. Static ownership and
mock pixel controls did not establish a performance improvement. The bounded
replacement reuses one offscreen context to create synchronous immutable
glyph bitmaps, preserving the existing individual-canvas fallback, exact device
positions, clipping and 1:1 source pixels. Bitmap eviction, font retirement,
global close, failed transfer and uncached-draw failure have explicit controls.

The detached preparation candidate retains source-font roots before any layout
or display yield. Actual registry/scanner/retirement controls preserve an opening
font while another tab closes, retain inactive-document fonts, and remove failed
reconstruction fonts plus its materialized claim on ordinary fallback. Typed
cancellation never enters fallback in a replacement document. Preparation replays
the same finalized native text and literal ancestor Canvas transforms; it does
not publish a second scene or layout.

Exact-context native render listeners in `font/integration/i9/` establish that
visible artwork already hits its prepared cache. The first native 115-by-150
deck thumbnail creates the remaining 2,576 tiles at its separate device phase.
Unpaired selection events are excluded; diagnostic timing is not acceptance.
The correction prepares the thumbnail phase cooperatively too, using shared
original thumbnail options and the actual Fabric transform. Literal native
`toCanvasElement` controls cover affine inputs and the existing .08 scale floor.
No asynchronous attached-scene paint gate was introduced.

Normal `i10/` preserves all seven selected original PNGs exactly and meets the
250 ms gap limit, but its recorded 124 ms task violates the separate 100 ms
limit. The maintained recorder now checks that requirement explicitly; the old
19/19 count never qualified it. CPU-only `i11/` retains unresolved cross-clock
alignment and is not exact task attribution. Independent local interpreter
timing in normal `i10/` records a 107.1 ms synchronous batch. The bounded
correction yields between complete original decoding operators within the same
original ranges, preserving nested state, paint order and cancellation.
`maxSynchronousSliceMs` measures uninterrupted work; `maxBatchExecutionMs` now
includes intentional yield wall time. A single original operation remains
indivisible and can still exceed either time budget.

Normal `i12/` passes 20 opening checks: 5.238 s Open, 226.1 ms maximum foreground
gap, 98 ms longest task, and 31.9 ms maximum interpreter slice. The unchanged
candidate's complete `i13/` journey passes all 56 producer checks, including
actual Save, a fresh Chromium process opening that file, exact warm/cold pixels,
continued caret/character selection and typing, full-leaf Undo, Redo text, a
second actual Save and final PDF export. Its opening gap/task are 231/99 ms.
The final export's significant page difference is 0.4026%; opened artwork remains
0.1902%. Independent review inspected all 22 originals with no new actionable
visual defect. Independent actual-file/content review passes 43 checks: actual
first Save equals complete warm and cold artwork; the second Save equals complete
continued artwork; both retain exact original PDF and portable font programs.
All 1,319 other objects retain their authored properties, hierarchy and order.
The intended added ` A` is independently identified in the final PDF. Targeted controls pass
139 renderer/import/layout checks and 23 operator checks. These are bounded
source/journey results, not repeated or full-desktop performance acceptance.
Continued Redo is text-only and anchor Redo is outside this journey.

The selected local WASM remains under redistribution hold. Immutable wrapper
and builder commits do not establish the exact PDFium checkout or complete
linked dependency notices. Keep that limitation separate from the functional
result; neither local success nor an observed branch tip certifies binary source.

The compact local evidence index is under `qa_artifacts/t22/font/integration/`:
`source-i12/manifest.json` and `tracked-source.patch` freeze the winning source;
`i13/report.json` and `i13o/` retain the normal public journey and zero-survivor
owner result; `i13-independent-content/receipt.json` and
`i13-independent-visual-review.json` record the separate independent decisions.
`i9-attribution.json`, the passive-render review and both custody appendices
retain exact context attribution and reconstructed historical source. Earlier
raw failed verdicts remain unchanged. Native computer use stays stopped unless
an actual Affinity comparison is in progress.

The normal continuous gesture remains failed on the accepted typography source.
`continuous/r5/` passes 61/70 checks, with correct trusted input/model and both
intermediate pixel windows, actual Save/fresh Open, second Save and PDF export.
The nominal two-second stream takes 15.219/15.334 seconds warm/cold; lower-paint
p95 is 150.8/151.6 ms. The owned job closes with zero survivors. Diagnostic CPU
run `r6/` attributes roughly 9.6 seconds to `renderAll` and 4.8–5.0 seconds to
native text-character dispatch during each gesture. Inclusive weights overlap;
they are not independent elapsed-time measurements. Removing every text cost
alone would still leave a substantial rendering problem.

Private glyph-command reuse `continuous/p1/` is retired, with no product change.
Its 68/79 raw failure retains 12.506/13.148-second streams and one cold
returned-native mismatch: 1,233 RGB pixels, maximum channel difference 133,
unchanged alpha. Both full buffers were saved before comparison. Independent
offline review locates the largest differences at the F in “TCF3 CHEA” and
smaller differences at nontext boundaries; the cause is unproven. Four initial
comparison pairs and the warm returned-native pair are exact. Neither initial
equality nor partial speed improvement waives the cold failure. The independent
receipt is `continuous/p1-pixel-review/independent-pixel-review.json`.

The next finite diagnostic examines native visible-area paint. At the source
marker's public zoom, the lower backing canvas is 3600×4659 even though the DOM
viewport clips most of the page. Fabric's root-only offscreen test does not cull
the nested labels. The private plan and source review under
`continuous/viewport-pilot/` retain the same main context, actual CTM, group
dispatch, native label painter and scene/history ownership. This is a controlled
feasibility test with exact visible RGBA comparisons; offscreen stale pixels and
arbitrary source/font mutation are explicitly outside its qualification. It is
distinct from the retired dirty-hull clip-only C1 and command-reuse p1 routes.
No product viewport-culling change has been adopted.

The combined visible-area trial `continuous/v1/` stops before trusted input:
498 visible pixels differ, maximum channel delta 7. Independent original-pixel
review localizes the differences to round-marker boundaries, with nearby text
exact. All original buffers precede comparison assertions; the returned native
buffer equals the native baseline byte for byte. The owned job closes after
15.062 seconds with zero survivors. No gesture or performance result follows.

The finite same-state factor control `continuous/f1/` records 55 diagnostic
checks and explicitly finishes before any gesture. All four native baselines
and returned-native full buffers, plus the pass-through candidate, are exact.
Skipping 922 offscreen labels without clipping preserves every visible RGBA
pixel; the 785,348 intentionally absent offscreen pixels remain unqualified.
Clipping alone reproduces the same 498 visible differences as the combined
candidate. The job closes after 26.093 seconds with zero survivors. This is
bounded causal support for eliminating the outer clip; it does not qualify
arbitrary documents, mutations or sustained input. Exact generated CRLF file
bytes and evaluated LF text are distinguished in the source reviews.

The guarded cull-only continuation is a deliberate derivation of that factor,
not identical factor-file bytes. It removes only actual clip/path/transform
commands, retaining live DOM/backing/canvas ownership checks, balanced native
scopes and the full-native fallback. Eight unchanged control bodies pass on
that derivation; the source/entry manifest and separate preflight review are
under `continuous/viewport-pilot/`. Its normal-controller journey remains a
private feasibility check, with the original timing and pixel limits.

Guarded `continuous/v2/` passes 89/96 checks and remains failed. Warm/cold streams still take 8.425/8.764
seconds, rAF p95 58.3/57.4 ms and lower-paint p95 85.2/88.5 ms. Tasks and
foreground gaps now meet their declared limits, and both intermediate pixel
windows and input/model checks pass, but cadence and frame limits do not.
Warm visible comparisons are exact. Cold preflight is exact; the naturally
present post-gesture buffer differs from the later native repaint at 156
visible pixels, maximum delta 6. The separately forced candidate detects a
source/paint-plane mismatch, disables skipping and completes its full-native
fallback; its entire buffer then equals the final native buffer. That forced
agreement does not repair or waive the natural failure. All pairs precede
assertions. The run stops before a second Save/final PDF export, closes after
63.125 seconds and leaves zero owned processes. This is not an adopted route:
even omitting most glyph paints remains far above the unchanged frame target.
Any shared cold post-commit natural-paint defect requires an unmodified-native
control before attribution; the private cache's invalidation is not proof of
its cause. Production source, beta.16 selection and the roadmap remain unchanged.

The subsequent unmodified-native control `continuous/n1/` reproduces exactly
the p1 cold pair: 1,233 differing RGB pixels, maximum delta 133, unchanged
alpha. Repeated natural captures and the separate pre-force capture are exact;
two forced native paints are exact with each other. The last naturally
completed lower frame precedes pointerup. Settling the path then changes
1,176 projected authored rows through fit-content rebasing, including every
one of the 960 text entry matrices, without queuing another artwork paint.
Current authored records remain unchanged between the two forced paints;
font registration/retention/closure calls remain zero. This establishes a
missing post-commit publication for this witness, rather than same-model native
raster nondeterminism or a demonstrated private-cache invalidation defect.
The raw 83/94 failure and the exact before/after buffers remain retained.

The bounded correction calls the existing `requestCanvasArtworkRender()` after
settled geometry and Inspector work in segment finalization and the nonrouted
point finalization fallback, before ordinary or cooperative history capture.
That helper clears both selection-only suppression flags and queues the native
artwork frame. Geometry, history ownership, no-op/cancel behavior and routed
editing remain unchanged. Four actual-function controls fail on the old App
and pass on the correction; the combined point/native-transform tests pass
40/40. Independent source review accepts exactly these two call insertions.

The unchanged diagnostic harness rerun `continuous/n2/` now records an actual
completed native lower frame after pointerup in both processes. All six warm
buffers are identical; all six cold buffers are identical, including the first
natural capture saved before any force. The completed post-release frame,
current scene and both forced paints have exactly matching projected authored,
derived and ownership records. The cold images equal n1's forced native image,
not its stale natural image. Independent original-buffer review accepts this
bounded publication correction. Its raw 84/94 failure remains: post-pointerup
frame completions take 291.7/539.7 ms, the nominal two-second moving streams
take 13.273/13.175 seconds, and all original moving-performance failures remain.
This diagnostic does not pass the 250 ms release or general performance limits.

Normal, uninstrumented `continuous/g7/` passes all 32 producer point-continuation
checks on the corrected App. Natural first correct paint takes 185.5/228.2 ms
from pointerdown in this single 1440×1000 light case; stable confirmations are
570.4/956 ms. Actual Undo/Redo, Save, fresh Chromium Open, continued editing,
second Save and PDF export complete. Its raw observed action long tasks remain
192/333 ms, so the reported checks do not establish normal responsiveness.
Initial-to-final equivalent-geometry pixels are a distinct comparison from
n2's same-current-model proof. Independent content review passes 38 checks:
1,320 objects (1,309 leaves and 11 groups), all 1,308 protected leaves, exact
source/font bytes, hierarchy, both actual Saves and the exported marker.
Independent original-image review accepts the bounded local gesture and
export appearance, but retains a 1,233-pixel initial-to-cold-final difference.
A sampled unchanged neighboring circle differs at 16 pixels, maximum delta 4;
the sampled transcription-factor label differs at 185 pixels, maximum delta
133. Those exceed RGB-2. Protected-artwork pixel return remains unresolved
under the original parity requirements; neither an antialiasing waiver nor
authored/world-coordinate preservation establishes that missing acceptance.

Normal typography regression `font/integration/i14/` passes all 56 producer
checks on the same corrected App: public real Figure 2 Open, live Unicode and
physical-size editing, actual Save/fresh Chromium Open, continued caret and
character selection, typing, Undo/Redo, second Save and final PDF export.
Open takes 4.8502 seconds with a 238.6 ms maximum foreground gap and a 100 ms
longest opening task. Opened page difference remains 0.1902% and final continued
export difference 0.4026%, identical to i13's metrics. Both normal jobs close all
owned processes (43.265/133.344 seconds). Source stability is bound separately
for each run. Independent actual-file review passes 45 checks on i14, including
all 1,319 other objects, portable/source fonts, Unicode edits and final exported
text. Independent image review binds 21 identical i13 originals and directly
inspects the sole changed editor screenshot: its artwork is exact, with only
ancillary toolbar/Inspector state changed. All 13 artwork/PDF/difference grids
are identical. A broader audit that also expected exact ancillary editor UI is
retained separately; this does not change any product or producer predicate.
Together with the g7 and n2 reviews, this closes the bounded publication
correction. Full desktop/performance and protected-neighbor pixel acceptance,
plus PDFium redistribution, remain open. Neither beta.16 nor the roadmap changes.

Earlier per-label omission before native Text/Object dispatch is not being
implemented on an assumed performance benefit. The retained native CPU profiles
attribute only about 9.8–11.4 ms per render to the wider relevant dispatch
envelope outside late text painting, while the retired cull-only run remains
at 85.2/88.5 ms lower-paint p95. These overlapping diagnostic estimates are not
a p95 or a rigorous removable-cost bound, but do not support reaching 24 ms by
that change alone. Any later attempt needs a new finite remaining-cost diagnosis
and native invalidation/visible-pixel proof, rather than another cache guard.

The finite retained-evidence normalization diagnosis now reproduces the selected
F difference without a browser. The containing `CF3` text run retains exactly
the same composed Fabric world matrix, source glyph positions, font program,
line metrics, style and ownership. Compensating parent/local rebases nevertheless
produce different recorded native Canvas entry translations. Independently
rounding each own-transform input to float32 before double matrix accumulation
reproduces all 14 available CF3 entry matrices exactly; three alternative
rounding policies do not. Equal composed model matrices therefore do not imply
equal native paint inputs for this hierarchy.

The frozen two-input probe uses the unchanged production PDFium renderer,
exact registered 83,192-byte font program and actual retained entry matrices.
Source-v1 local fillText positions are reconstructed from the retained fields
and checked native arithmetic, rather than claimed as directly observed calls.
Its two native F rasters have the same 26×37 tile bounds and actual native
matrix/clip/flags except one float32 translation coefficient. Their fixed
24×34 source-image regions match both original PNGs exactly, reproducing all
185 changed pixels, maximum RGB delta 133, with no alignment, resampling or
phase search. The repeated first draw is explicitly a cache-hit control, not
an independent native determinism trial. Independent review passes 24 checks;
the engine closes with zero fallbacks/errors. C and 3 in the same run remain
pixel-exact, and the nearby circle does not follow the F's apparent shift.
The exact internal native raster branch, full-scene mechanism and circle's
unrecorded paint-entry transform remain unproved. All original RGB-2 failures
remain failures. The compact evidence is `continuous/normalization-diagnosis/`.

The proposed correction is a shared, stateless native scene-transform boundary,
following the existing ordinary-path module: compose the actual canvas plane
with Fabric's current complete world matrix once before the native leaf painter.
This would remove dependence on equivalent parent/local transform factorization,
without rounding authored coordinates or adjusting particular glyphs. It must
retain native groups, clips, painting order, IText geometry/history and export;
only exact supported native classes/methods may qualify. Screen glyph preparation
must use the same new matrix policy, while thumbnail/export contexts preserve
their own native policies. Applying a different phase only when entering
selection or starting a gesture would itself require rejection. Before extending
the same treatment to imported paths, record the circle's actual native entry
and clipping inputs. This is a concrete proposal, not implemented behavior or
source/adoption clearance; fresh natural-buffer, protected-neighbor, source
fidelity and actual-file/continued-edit checks remain required.

The subsequent passive circle control (`continuous/c3/`) completes in 16.468 s
with 12 checks and no surviving owned processes. Its saved/inverse/Undo/Redo
natural buffers reproduce the retained g7 images exactly. Independent raw-data
review finds the same exact Fabric world matrix for the circle and its page
clip across all four states, while the actual native circle and clip-builder
matrices reproduce the per-transform float32 factorization difference. Native
Undo/Redo revives object instances without changing source/path/style/ownership.
The complete page-rectangle builder and nonzero rule are recorded separately
from the later clip-call CTM. This closes the missing circle-input observation;
the original protected RGB-2 failures remain failures.

A local shared-transform candidate now extends the existing module at native
Path/IText transform entry, inside their original render/style/opacity scopes.
Admitted imported objects use the current complete Fabric world matrix from
initial Open, including top-level text, irrespective of selection/isolation.
Known relative clip builders use the same main-plane product inside their
existing saved scope, preserving geometry, rules and intersections. Exact lazy
class/method guards and uncached/no-effect ownership are required; unknown,
absolute/inverted, general cached clips and foreign methods retain native
fallback. The separate current-plane clip implementation remains unchanged.
Only explicit screen glyph preparation shares this policy; thumbnails and
other contexts retain literal native transforms. Targeted controls cover exact
world inputs, native clip builders, lazy registration/revivers, nested/error
scope restoration and preparation fallback/error cleanup. Independent source
review and fresh normal source/pixel/Save/Open qualification are still required;
this candidate is not a release or performance acceptance.

The first normal candidate run g8 passes its 32 maintained workflow checks and
46 independent actual-file content checks, but protected pixel return still
fails: 711 changed pixels, 456 exceeding RGB-2. The restored marker, neighboring
circle and nearby label now return exactly; the remaining significant changes
are the selected F and a thin panel-A strip. Warm edited and fresh cold buffers
are exact. Independent exact world comparison records 176 protected leaves
with nonzero inverse-roundtrip residuals up to 1.14e-13, without normalization.
The read-only a1 control then confirms all 960 text objects reject at the private
binding's `_renderTextLine` comparison: deferred native text registered before
App installed its canonical paragraph renderer. A local correction accepts only
that once-only explicit previous-to-replacement startup handoff, with tests
executing the actual App installer for early/lazy registration and rejecting
later or mismatched foreign overrides. Image-paint ownership and fresh normal
pixel/source qualification remain open. No tolerance or release change follows.

The passive c4 control observes that corrected text admission and identical
actual native text entry inputs through inverse/Undo/Redo; F pixels now return
exactly. The remaining 444 strip pixels lie inside an actual source117 native
image-element draw, with the same eight draw operands, crop/interpolation state
and exact current world matrix, but repeated different native entry transforms.
Its raw producer remains failed: four observer assertions incorrectly required
`ownCaching === false`, whereas the native Image leaves that value undefined.
The complete raw authored projection confirms the omitted undefined field;
the actual main draw uses the original HTMLImageElement, while native cache
painting would draw a cache canvas. This is actual participation/input evidence,
not an isolated image-sampling causal proof or a rewritten producer pass.

The next local candidate extends the same complete-world native transform seam
only to exact imported stock Image objects with known native methods, coherent
original-element ownership, no cache/clip/filter/resize effect, zero crop and
unit filter scaling. Native draw operands and the existing interpolation flag
stay authoritative; clipped or other unsupported images delegate unchanged.
Source review and fresh uninstrumented pixel/source/actual-file qualification
remain required before adoption.

The coherent V5 candidate now has independent source clearance and bounded
normal qualification on the original Figure 2 PDF at 1440×1000, light theme.
It composes the actual main canvas plane with the current complete native
world transform for admitted text, paths, relative clip builders and stock
images. Screen glyph preparation uses that same policy. Native objects,
painters, drawing order, geometry, hierarchy, history and export remain their
existing authorities. Unsupported methods, caches, clips and effects retain
native fallback. The explicit canonical startup text-renderer handoff also
handles registration before App configuration without accepting later foreign
method changes. All 163 targeted tests pass; no coordinate snapping, glyph
adjustment or pixel-tolerance change was introduced.

Normal point continuation `continuous/g9/` passes 32 maintained checks and
49 independent actual-file checks. The neighboring circle, selected F/CF3,
label, image strip and restored marker return exactly. Whole-buffer return
retains 35 changed pixels, each at most one RGB channel level, with zero RGB-2
failures or alpha changes; those colorbar pixels are not described as exact.
Warm edited and actual fresh-process cold buffers are exact. Both actual Saves,
continued point editing and PDF export preserve original source/image/font
bytes and all protected content. Exact world comparison still lists 176
protected leaves with nonzero inverse-roundtrip residuals up to 1.14e-13,
without normalization. The normal job takes 43.953 s and closes every owned
process. Its 246.2/186.9 ms first-paint observations and long tasks up to 235 ms
do not close the original broader performance requirements.

Normal typography `font/integration/i15/` passes 56 maintained checks and
58 independent actual-file checks. Independent review directly inspects all
22 original screenshots and recomputes the five fidelity comparisons. Source
appearance, physical-size editing, the disclosed Arial substitution for beta,
character selection, typing, Undo/Redo, both actual Saves, fresh Chromium Open
and final PDF exports pass this bounded journey. Warm/cold artwork is exact;
all 13 artwork/export/difference images are byte-identical to i13. Opened page
difference remains 0.1902%, and the final continued export difference remains
0.4026%. Those residual source/export differences remain disclosed. Open takes
5.1157 s with a 207.3 ms maximum foreground gap and a 100 ms longest observed
opening task. The owned job closes cleanly after 136.141 s.

The separately instrumented first-Open control `continuous/prep2/` completes
in 8.141 s with clean observer restoration and no surviving owned processes.
Independent data review passes 28 checks, including exact actual registered
83,192-byte font data and independently decoded TrueType bounds. Selected F
screen preparation and the first actual main paint have identical final native
CTM, local request and style. The first main paint reuses the same ImageBitmap
and literal 11×13 tile at (582,486): preparation records one miss and ten actual
JavaScript Float32 writes; the live paint records one hit, zero writes and no
fallback. The six matrix and four clip writes match the unchanged source
formula. This is observed JavaScript buffer-writing evidence, not direct FPDF
call interception. The native source117 element draw also matches the current
complete-world product exactly at Canvas float32 input, retaining its eight
draw operands and interpolation state. Metadata read after asynchronous hashes
is distinguished from the synchronous PNG-bound paint observations. Independent
original-image review confirms complete panels A–H. This is diagnostic input
evidence, not normal timing, native replay or general raster acceptance.

The first observer attempt `continuous/prep1/` remains a raw cap HOLD. Its
128-record limit was insufficient; one independently reviewed observer-only
increase to a finite 512 records produced the complete 192-record capture.
The earlier cleanup-preflight HOLD and its corrected review are retained too.
Neither producer failure is retroactively passed. Existing g7/g8/c4 pixel HOLDs
remain historical results on their exact earlier sources. The inherited staged
descriptor-style mismatch and `nativeEquivalent: false` remain explicit; this
slice does not qualify a source-PDF compiler.

Closure storage review removes 33 superseded automated full-scene snapshots
and Save downloads from r4/r5/r6/p1/v1/f1/v2, freeing 466,289,260 bytes. The
exact plan/result are `qa_artifacts/t22/retirement-after-i14-{plan,result}.json`.
All original failed reports, PNG pairs, profiles, controllers/source patches,
final PDFs and selected n1/n2/g7/i13/i14 evidence remain; current i13's live i3
dependencies are retained. The first cleanup preflight stopped before mutation
on a PowerShell path-check error; the corrected bounded preflight rechecked all
33 hashes before removal. No deletion was blocked and no purge staging was
needed. The fresh inventory still reports 8.771 GiB total and 8.576 GiB ordinary
generated output, over the unchanged 6/2 GiB warnings. No accounting exception
or retention claim hides those bytes.

V5 closure additionally retires exactly ten superseded i13/i14 generated
full-scene snapshots and automated Save downloads, freeing 145,928,314 bytes.
The plan, active ignored-controller/input review, execution result and retained
dependency pins are `qa_artifacts/t22/retirement-after-v5-*.json`; each old run
also has an explicit retired-input mapping. Their original reports, PNGs, PDF
exports and review receipts remain immutable. Current g9/i15 evidence, live i3
font inputs, g7/g8 diagnostic Saves, Affinity documents and scientific originals
are retained. All sixteen preflight keeper pins remain exact after deletion.
No deletion was blocked and no purge move was needed. The fresh complete
inventory reports 9.033 GiB total and 8.836 GiB ordinary generated output,
still over the unchanged 6/2 GiB warnings; there are no accounting exceptions.

One owner coordinates shared interaction, rendering and history edits. Independent selection-coverage and source-font/glyph diagnosis may proceed in parallel, with one owned browser or heavy job at a time. Native computer use remains stopped. Existing Affinity originals and official reference documentation support the comparator record; new native comparisons require actual need and explicit coordination.

Use the maintained owned browser runner, current controllers, retained scientific originals and actual downloads. Keep .005 world-coordinate and RGB-2 paint predicates, nonvacuous probes, 250 ms paint deadlines, fidelity, memory and recovery limits unchanged. Broader performance acceptance is not inferred from a single point gesture. Qualify the winning coherent source in light/dark at 1280×800, 1440×1000 and 1920×1080, with independent original-resolution visual/content review, complete actual Save/fresh-process Open/continued editing and real exports. A visible in-scope HOLD requires correction.

Fresh output uses short roots under `qa_artifacts/t22/`. Do not copy complete app/source trees for each attempt. Record exact hashes and compact patches/controllers; retain the selected final proof and applicable failed witnesses. Follow [storage maintenance](../STORAGE_MAINTENANCE.md). Never use a pending manual-purge directory as an input, restore its old trees, or add new output to it. Preserve original science files, beta.16/beta.15 evidence and the six unrelated untracked composed/native experiments.

The roadmap remains the same: reliable selection and fully editable scientific PDFs before v1 acceptance. The coordinator owns Core integration and paired installed/website delivery. Handoff requires an accepted canonical commit, compact evidence index, supported behavior and precise remaining failures; beta.16 remains selected until those combined gates pass.

## Continued selection and renderer qualification, 22–23 October

Alt now moves only the grabbed direction handle. Returning to the exact grab
position restores the original path and node metadata; Escape, Undo and Redo
retain the native transaction. Releasing or pressing Alt during a gesture takes
effect on the next pointer sample. That transition is an explicit Figure policy;
the retained Affinity comparison does not establish modifier-transition parity.

An ordinary first click on a filled editable path initializes its complete
logical endpoint selection before the existing body transform begins. A later
ordinary click on a different filled child switches the target, including stored
selection inside an isolated group. The Inspector updates with that target.
Partial selections on the current path and the existing modifier policy remain.
The normal and isolated journeys pass 82 and 39 checks, respectively, with
independent content and original-image acceptance.

Overlapping handles now share the existing browser hit stack and resolve to the
nearest admitted center for both pointerdown and click. At exact coincidence,
the selected handle wins; public Tab/Shift+Tab exposes the alternate. Selected
and dragging markers paint above unselected neighbors at their original size.
The final near/coincident journeys each pass 40 checks; nested/reflected Alt
editing passes 221 checks through both actual Saves, fresh Chromium Open,
continued editing and PDF export. Independent review inspects all 28 originals
and accepts the chosen final marker, including the square endpoint versus the
diamond control. Coincident geometry is not described as separated. Earlier
normal-view ambiguity and rejected final-pose witnesses remain historical.
The exact source, actual files and independent receipts are under
`qa_artifacts/t22/alt1/`.

The browser PDFium runtime is now the pinned bblanchon 158.0.8111.0 supplier
release. Its unmodified loader and WASM, deterministic isolated factory, supplier
and supplemental notices, source lock and both source exporters are adopted
together. The canonical factory checker reproduces the exact wrapper from
checked-in inputs without compiling or executing WASM. All 65 targeted vendor,
source and package guards pass. The unchanged historical candidate provenance
is retained separately; the supplier binary record does not claim independent
attestation of the fetched PDFium source revision.

The first normal replacement-runtime typography journey at 1280×800 light passes
54 of 56 checks. Independent actual-file review passes 61 checks; all 22 original
images pass their bounded visual review. Its 13 artwork/export/difference grids
are byte-identical to the prior retained qualification, and warm/cold artwork is
exact. Source PDF, both font programs, six images, editable text, both actual
Saves and three actual PDF exports remain intact. Open still records a 253.9 ms
foreground gap and a 125 ms task, beyond the original 250/100 ms limits. This is
a performance HOLD, not release acceptance. The exact failed interval and
reviews remain under `qa_artifacts/t22/packaging-resume/t1/` and its adjacent
receipts.

The cooperative preparation correction captures final native glyph requests
synchronously, leaves every Fabric/Canvas scope, then prepares those requests
through the same renderer and cache, checking the time slice between complete
glyph calls. Native coordinates, fractional phase, float writes, fallback and
cache identity are unchanged. Its 78 targeted tests and independent source
review pass. Normal `t2/` nevertheless passes only 54 of 56 checks: the opening
gap is 261.5 ms and the longest task is 122 ms.

Moving an unused recovery-panel reference scan below the no-missing-assets
return preserves the required asset discovery. Normal `t3/` then passes 55 of
56 checks: its 240.1 ms opening gap meets the limit, while its 119 ms task does
not. A further exact-source measurement memo has 32 entries and an 8 MiB
logical UTF-16 key budget, clears with all five artifact-store resets, and
retains only immutable size/hash measurements. Ten focused cache/discovery
tests pass; the repaired four-file restore/Slides fixture command passes all
87 tests using actual production dependencies. These are source and functional
checks, not evidence of a normal responsiveness improvement.

The combined normal `t4/` journey passes 54 of 56 checks, retaining a 268.8 ms
opening gap and a 121 ms task. Independent actual-file review passes 69 checks;
all 22 original images are byte- and decoded-pixel-identical to reviewed `t2/`
images. All 13 artwork/export/difference grids remain identical to the earlier
accepted typography images. Both actual Saves, fresh Chromium Open, continued
editing, the original PDF, portable font programs, protected objects and three
PDF exports remain intact. No normal opening performance gain is established
for the combined changes. A later diagnostic must measure actual runtime
cache hits/misses and aligned event phases before changing capacity or
attributing the residual task. Retained-file URL sizes alone do not establish
live cache behavior.

The paced mixed open-path journey `qa_artifacts/t22/mixed1/m5/` passes all 106
producer checks at 1440×1000 light. Public selection constructs one selected
endpoint on the open line and one on the transformed cubic. An off-center
trusted drag moves both selected endpoints and the attached incoming cubic
control while every other world operand and the filled neighbor remain fixed.
Escape restores literal geometry, metadata and selection; completed movement
passes Undo/Redo. A separate deliberate stroke drag reshapes the cubic while
retaining its endpoints and the line; its Escape and completed Undo/Redo also
pass. Control is held only to bypass Figure snapping. The native viewport
transform is explicitly identity; this does not qualify default comparator
modifiers, arbitrary affine viewport transforms, paint timing, PDF editing,
Save/fresh Open or general parity. Independent actual-content review passes 45
checks, and all four original 1440×1000 held-state images pass visual inspection.
The two repeated held poses in each operation are recorded as identical images;
later Escape and history results are established by actual state/input records,
not by inventing screenshots of those outcomes. The independent reviews and
final frozen controller are retained beside the run.

Earlier `m1/` through `m4/` remain failed. They exposed an invalid integer-canvas
backing precondition, repeated selection setup that toggled an existing member
out, and immediate geometry reads racing overlay replacement. The corrected QA
uses exact integer backing construction, verified public empty-canvas deselection
and normal visible/stable locator input for point selection. Actual off-center
drag input, independent world mapping, protected operands, history requirements
and the .005 geometry tolerance remain unchanged. This bounded case required no
product selection change. The generic raw capture intent mentions anchors even
for the separate segment operation; the operation-specific state and review
remain authoritative for interpreting those held-state images.

All owned jobs are closed with zero surviving owned processes, and native
computer use remains inactive outside an actual Affinity comparison. The fresh
complete storage inventory measures 10.979 GiB total and 10.775 GiB ordinary QA
output, with no read errors or accounting exceptions. The existing reviewed
248 MiB pytest fixtures are staged in `qa_artifacts/PURGE-ME-2026-10-22/` after
the deletion command was blocked by policy; their exact mapping remains adjacent
to the qualification reports. Moving them did not free space; manual deletion
is still required. Current scientific inputs, actual qualification evidence and
the unrelated composed/native experiments remain retained.

The remaining desktop matrix and exact combined browser/native package
qualification follow only after the original responsiveness limits pass.
Beta.16 remains selected, and the roadmap remains the same.

## Group selection and topology follow-through, 23 October

Entering a group now refreshes the Inspector for its actual child. Changing the
isolated selection also refreshes its controls once at the selection command,
while the existing full UI update remains deferred. Internal operations that
use `sync: false` retain their command-owned refresh. Nested named-selection
recall forwards that option through its sibling loop; entering a group still
performs its explicit refresh for each entered depth. The unit adapter for the
sibling loop does not claim to exercise that exit/re-entry sequence.

Duplicating children inside a group now requests an artwork paint after their
native insertion and placement. Previously the copied objects existed in the
model but remained unpainted, including after a passive 500 ms observation.
The fix preserves the original parent and world placement. Layers selection
updates now recognize existing child rows as well as top-level rows, avoiding
unnecessary branch replacement that discarded a Reveal highlight. The update
also refreshes child selection styling in place and preserves the separate
active-path authority used by authored clipping-mask rows.

The fresh group journey `qa_artifacts/t22/layers1/g6/` passes all 40 checks, and
independent review accepts all 16 original desktop screenshots. The context
correctly describes both selected children; both group-entry views identify
the actual child; copied artwork appears at its new position. The five added
capture checks retain the original 35 assertions. They check actual displayed
selection names and IDs, clipped on-screen text bounds, and two exposed opaque
mint pixels from the real lower artwork buffer. Those pixel observations occur
after the ordinary screenshot and establish bounded ink witnesses, not an
atomic screenshot comparison, complete-copy fidelity or paint latency. The
early legacy Layers-row marker snapshot does not establish both selected row
markers, and blue browser text-selection highlighting in frame 04 remains a
capture/UI-polish caveat. The rejected `g4/` toolbar mismatch and `g5/` detached
DOM observation remain retained. Forty targeted native-selection, duplication
and Layers-row tests pass, including clipping-row cases; those adapters do not
replace browser or saved-file checks.

The maintained topology journey `qa_artifacts/t22/topology-maintenance/vector2/`
passes on the same source. The two split endpoints coincide, so selecting them
uses the public point marquee. The three-point ambiguity case first selects
the independently identified endpoint on the separate open path, then adds
the seam pair with Shift-marquee. Exact descriptor sets, literal authored
records and history are checked. Independent content review passes 45 checks;
all 75 world endpoint/control operand pairs remain within the unchanged .005
world tolerance, with a maximum observed difference of about 5.7e-14. The
actual SVG and independently parsed PDF each contain 15 vector paths and no
images; the PDF has one 612 by 792 point page. All three original desktop
captures pass bounded visual review, including the open More menu at 1280
pixels. The coincident marker is not described as two spatially separated
points, and the lower blank page area is cropped at that width.

Existing topology Undo/Redo and same-process project/package comparisons retain
their original three-decimal signatures. Raw local path operands after Redo
are exact; some world anchors differ by about 5e-5. These records establish no
actual Save/fresh-process Open, native comparator, full desktop/theme matrix or
responsiveness qualification. The source and independent receipts are retained
beside the final runs. Native computer use remains stopped between actual
Affinity comparisons.

The roadmap remains the same: reliable selection and fully editable scientific
PDFs before v1 acceptance. Beta.16 remains selected. The earlier normal Open
performance failure still requires a phase-aligned diagnosis and a fresh
uninstrumented check against the original limits; these interaction results do
not resolve it. Figure 2 does not establish Figure 4's nested Form coverage.
The original Figure 4 PDF has now been recovered from its archive as described
below; its normal qualification still needs to run.

## Compound editing and Layers follow-through, 23 October

The maintained compound-path journey `qa_artifacts/t22/topology-maintenance/compound4/`
passes all 21 original checks. Independent actual-content review passes 38
checks; separate visual review accepts all four original 1440 by 1000 images. The public setup
selects the exact point before opening More and changing its tangent mode.
The transformed drags retain their original input displacement and .03 local
tolerance, with an additional unrounded .005 world check. Their expected
positions preserve the actual grabbed offset and use the trusted native
canvas event coordinates with independently evaluated scene-to-object affine
mapping. Control explicitly bypasses snapping. This is not an independent
client-to-scene calibration or default snapping qualification. Protected path
operands, metadata, styles, parents and order survive the same-process
project/package comparisons. Actual SVG has five paths and no images; the
one-page PDF has six painted paths and no images or Forms. These results do
not establish browser Save/fresh-process Open or the broader desktop matrix.
Earlier compound failures and their original verdicts remain retained.

Native Presentation Reveal now uses the existing canvas, current slide and
Layers tree. The context command opens Format, closes the Slides pane when
necessary and reveals the selected native object without changing authored
data or history. The open Format Inspector retains its normal flex-column
height constraint, so its scrollable Layers tree fits within the window.
The floating-collapse branch is source-reviewed only; the runtime cases use
docked Format. Affinity is the requested comparator. Computer use remains
inactive outside an actual Affinity comparison.

Layers status messages have a dedicated, permanently reserved four-line
space between the finder and object list. The message itself is absolutely
positioned within that space, retains its full text and polite live-region
semantics, and scrolls when necessary. During a native drag it cannot intercept
the pointer. Changing, showing or hiding a message cannot move the object
rows. A held gesture defers message clearing until release; repeated inactive
cleanup does not restart the original timer. Cancellation and document/slide
switches clear the pending status and timer. Fifty-six targeted tests pass
on the current App, including seven actual-source status/timer controls.

The normal Layers journey `qa_artifacts/t22/layers1/l18/` passes all 35 original
checks in 72.968 seconds, with all 77 recorded source/evidence bindings stable
and zero surviving owned processes. It includes actual File Save, same-context
close/Open, metadata and hierarchy preservation, SVG export, rejection of
protected or cyclic moves, scoped document/slide transitions, and an actual
drop after an expanded subtree followed by Undo. Added guards require stable
Layers edges from idle through dragstart and hover, the actual pointer's
native target and drop band, status containment, and a Reveal row wholly
inside the viewport with an unobstructed center. The two native slide Reveal
outcomes also have original screenshots. Independent visual review accepts
all six original images and confirms the earlier status/header collision is
absent. Both slide Reveal rows are completely on screen with readable status
and useful native slide artwork beside them. Independent actual-content
review accepts the bounded result: the actual Save contains 244 uniquely
identified objects and 51 roots with the expected hierarchy and linked-frame,
scene and connector metadata. SVG preserves 43 local path records at the
existing three-decimal comparison precision, 25 Unicode text records and
seven layer maps. All eight retained held-drag geometry records have zero
Layers-edge drift. Full raw reopened-scene and final Undo states are not
serialized, and only the nested locator's trusted drop trace is retained;
the source/runtime checks cover the other scoped operation, but independent
replay of those raw records is not claimed.

The fixture uses public 10 by 7 inch Document setup before construction.
Its one tiny scene label, Lumen, is changed through Properties from 9.75 to
17 local points, giving about 8.46 effective points, before organization and
persistence baselines. The normal export readability check remains enabled.
The crowded mechanical scene establishes workbench organization and editing
behavior; it is not accepted as a publication-ready biological composition.
Close/Open in this journey uses the existing browser context rather than a
new Chromium process.

### Maintained browser QA details

Run the maintained controllers through `scripts/run-owned-browser-qa.py` with
one bounded owned job at a time and canonical ignored output under
`qa_artifacts/`. Freeze the executed source before a run and retain its
before/after interval, supervisor result and failed evidence unchanged.
The Layers controller accepts `--root`, `--output-dir` and `--timeout-ms`;
the latest normal run uses a 240 second owned deadline and 30000 ms locator
timeout. Its real Save prompt accepts only the expected filename prompt and
always removes that scoped handler.

For native root-row drops, the production hit rectangle includes the direct
title and action rows, excluding expanded descendants. Playwright's
`target_position` is relative to the row padding box. Use that native union
and subtract `clientLeft`/`clientTop` when deriving the offset. L16 retained
an Inside drop where the old title-only aiming requested After; L17 corrects
the targeting without changing input count, native thresholds or hierarchy
and Undo assertions. The existing compound helper uses actual trusted event
objects with `canvas.getScenePoint`, preserving the pointerdown origin
refresh and receiver; a plain coordinate wrapper does not establish that.

On a failure, the Layers controller writes the primary error before any
cleanup await, bounds release and screenshot operations, and closes page,
context and browser independently. Cleanup errors cannot turn a failure into
a pass. L13-L15 retain the earlier dragstart/CDP stalls and their bounded
diagnoses. L17 remains a raw 35/35 result with an independent HOLD: its status
overlapped the Layers heading in all four originals, and its slide Reveal row
was below the viewport despite being inside an oversized panel. L18 adds
the real viewport and status-slot checks; no earlier verdict is rewritten.

### Recovered Figure 4 original and remaining qualification

The original is in
`E:\closed_projects\Broad drug resistance project - closed.zip`, member
`Broad drug resistance project - closed/new pdf figures/Figure 4.pdf`.
Only that member was copied to
`qa_artifacts/t22/recovered-scientific-originals/Figure 4.pdf`. Its 2,231,722
bytes and SHA-256 exactly match the recorded corpus original. The archive
was left unchanged; the recovery receipt is adjacent to the PDF. This removes
the missing-input condition. The maintained normal nested-Form qualification
and any required Affinity comparison remain to be run on that actual file.

The closed-job storage inventory after L18 measures 11.064 GiB total and
10.858 GiB ordinary QA output, without read errors or accounting exceptions.
Both the existing 2 GiB ordinary-output and 6 GiB workspace budgets remain
exceeded. It includes the L18 outputs and recovered original. The earlier
248 MiB staged pytest fixture folder still requires manual deletion; moving
it did not free space. Preserve scientific inputs, active qualification
evidence and the unrelated composed/native experiments.

### Normal Figure 2 Open and private Figure 4 follow-through

The later Open investigation records actual call phases without replacing
runtime APIs or adding scheduler yields. In `packaging-resume/open-phase1/`,
the required recovery panel takes 14.3 ms of a 6225 ms Open; a later 130 ms
task lies outside the measured UI phases. Cache counters do not identify
repeated keys or attribute that task. A second private diagnostic records
five existing main-canvas render events, below its 48-record cap. Its two
nonempty paints take 84.2 and 80.6 ms; the second occurs inside the final
82.2 ms fit operation. Their pixels and viewport state were not retained,
so these observations do not establish identical or redundant paints.
Both diagnostics retain their failures and establish no normal performance
acceptance.

The bounded implementation applies only to a non-dense, single-page PDF
opened as a document. It holds the existing nested PDF history lock through
publication, final fit and history. Required controls and recovery information
update before an ordinary timer yield; the remaining controls finish only
while the canvas and document still belong to that Open. Pending native
paint and viewport-quality timers are cancelled for that owner before the
final fit. Synchronous insertion restores `renderOnAddRemove` before any
await. Failure cleanup requests a recovery paint when necessary and always
releases the lock. Ordinary placement, multipage and dense imports retain
their existing path. Default `syncUi` retains its original ordered,
synchronous work. Six new source-level ownership, cancellation and cleanup
controls join the previous 56 targeted tests; all 62 pass.

Normal, uninstrumented `packaging-resume/t5/` finishes in 134.063 seconds
with all 56 original checks passing, all 18 frozen source bindings stable,
and zero surviving owned processes. At 1280 by 800 in the light theme,
Figure 2 Open takes 5063.2 ms, with a 128 ms maximum event-loop gap and a
73 ms maximum main-thread task. The original 15000 ms, 250 ms and 100 ms
limits remain unchanged. This is the first successful normal observation
for this candidate; it establishes neither a repeatable speedup nor the
full desktop/theme performance matrix. The journey includes public editing,
grouping, direct anchor movement, atomic Undo/Redo, actual Save, Open in a
new Chromium process, continued keyboard editing, a second Save and three
actual PDF downloads. Independent actual-file acceptance is recorded beside
the run. Independent visual review covers all 22 original images: 20 are
byte- and RGBA-identical to previously directly reviewed originals, and both
changed dialog/editor frames are directly viewed. The residual source
appearance difference, explicit Unicode font fallback, warning-bearing
exports and tiny overview selection remain bounded limitations.

Figure 4's normal `figure4/n1/` fails editable qualification. Its explicit
fallback reason is that the portable knockout proof and compositor are
unavailable; the page contains no editable paths or text. The fallback
export preserves the original source, while the canvas is visibly softer.
That result does not qualify editable import or editable performance.
Read-only proof of the recovered original identifies six supported knockout
groups and no unsupported source groups. The existing three component test
files pass 37 tests.

Private K1 connects the existing knockout and proof modules in order,
registers their actual Fabric Group and Layout classes, and admits only
the registered group constructor. The next rejection correctly identifies
the missing importer-owned knockout source map. Private K2 forwards that
same authorized map to the existing materializer. It reconstructs all 3698
source paths, 1024 text runs, one image and 1967 groups, with no opaque-page
substitute. Canonical public admission and export are not changed.

K2 remains failed: Open takes 26190.1 ms, the maximum event-loop gap is
583.6 ms and the longest task is 400 ms. One editable U+FB00 ligature lacks
the independent source `ff` correspondence; two matched labels also retain
trailing-space differences, and whitespace-only runs need separate source
interpretation. Independent direct review of all five original images
confirms malformed glyphs in panel B's Diffuse Large B-Cell Lymphoma label.
The global provisional image metric does not override that visible defect.
The public export dialog reports zero errors and 50 warnings but never
finishes its preview within the original 20-second readiness wait. No PDF
download, browser Save or fresh-process Open is established by K2. Its
failed artifacts and private source stay separate from the normal Figure 2
candidate. The next bounded diagnosis observes the existing export-preview
load/render awaits and actual source glyph/font records, without changing
the public journey or its limits. Knockout opacity/overlap edits, protected
membership, corrected editable text appearance, actual Save/fresh Open and
ordered vector PDF export remain required before admission.

The closed-job inventory after T5 measures 11.321 GiB total and 11.114 GiB
ordinary QA output, with no read errors, reparse points or special entries.
The existing 2 GiB ordinary-output and 6 GiB workspace budgets remain
exceeded. The 248 MiB staged pytest fixtures still require manual deletion;
moving them did not free space. Scientific originals, active evidence and
the unrelated composed/native experiments remain preserved.

Beta.16 remains selected. No release, consumer payload or package was rebuilt.
The roadmap remains the same: reliable selection and editable scientific
PDFs before v1 acceptance. The first passing normal Figure 2 observation
narrows the performance work; the remaining repeated/matrix checks and
Figure 4 text, export and editing qualification still control acceptance.
Affinity remains the requested native comparator, and computer use stays
inactive outside an actual comparison.

The subsequent private K4 diagnostic keeps K2's runtime and original public
inputs, adding only capped export-phase markers and read-only glyph records.
It closes in 114.891 seconds with all 31 frozen bindings stable and no owned
processes left running. Its raw result is 12 of 20 checks passing. This time
the preview reaches readiness and the public export is submitted; the actual
failure is `An unaudited numerical-source shape SVG writer is unsupported.`
No output PDF is produced. That is distinct from K2's preview timeout, and
the numerical-source guard remains intact. The existing ordered knockout
writer still needs an integration that preserves the ordinary text, source
paint, numeric precision and image observers on the final emitted nodes.

All six records in the suspect Calibri source font have active original
glyph layout, equal current/source size and style, no character styles and
none of the eight paint exclusions. The U+FB00 run maps to display code
E001 with one logical character; five `ti` runs map to E002 with two.
The font-level raster diagnostics establish successful tile compositing
for E001 and E002, but do not identify a particular object occurrence or
prove its correct pixels. The visible defect's cause is therefore still
unresolved; no Unicode normalization or font substitution is inferred.
The static-canvas JSON waits take 610.4–708.3 ms, render calls 82.2–193.6 ms
and data-URL creation 137.4–255.1 ms. Two approximately 24-second gaps fall
outside those measured calls and are not attributed to an operation.

The repeated Open protocol is explicitly separate from T5's original
15-second corpus-run ceiling. Existing V1 policy requires five new-context
cold runs and ten same-context warm repetitions, with no route reload for
warm actions. Its ordinary tier applies to Figure 2's 1309 painted leaves:
editable readiness p95 at most 5 seconds and no run above 10 seconds, with
the same zero tasks above 100 ms and 250 ms foreground-gap maximum. The
required matrix is 1280 by 800, 1440 by 1000 and 1920 by 1080, in light and
dark. No existing maintained PDF controller performs that complete loop.
A thin Open-action controller reuses the actual public helper, retains its
original journey clock and separately records file handoff to editable
readiness. Its first planned cell is 1280 by 800/light/dev-web. It does not
replace the accepted full editing/Save/fresh-process journey or establish
saved-file reopen, first-preview, gesture, export or peak-memory budgets.

The first repeated cell, `qa_artifacts/t22/openperf1/1280-light-v2/`, is
failed evidence. It completes all five cold and ten warm Opens in 138.187
seconds, with all 19 frozen bindings stable and no surviving owned processes.
Independent review verifies every complete inventory against T5 after only
ID-to-ordinal normalization and verifies all 15 native Close/reset outcomes
are entirely empty. File-handoff readiness p95 is 6733.4 ms cold and
6541.595 ms warm, above the 5000 ms ordinary limit. The groups contain three
and eight tasks above 100 ms, respectively; their maximum tasks are 134 and
190 ms. Maximum foreground gaps, 218.8 and 202.7 ms, remain below 250 ms.
Original full-helper clocks are retained separately and do not replace the
earlier run's ceiling. No remaining unchanged matrix cells are run after
this first failed cell.

This controller blocks external requests through Playwright routing, which
disables HTTP caching. The run therefore establishes a routed, cache-disabled
context rather than ordinary cached warm behavior; OS cache state is not
controlled. The earlier generic cache wording was incomplete. Routing's
contribution to the elapsed time or long tasks has not been established.
Fifty requests report `net::ERR_ABORTED`; method, resource type and operation
phase were not retained, so these cancellations are not attributed or waived.
Page, console, HTTP-error and external-request arrays are empty, but the
failed-request guard also fails. All 15 original overview PNGs were directly
viewed at original detail. Their fitted editor is usable, but the completion
notification covers panel H's axis/caption region. They are bounded editor
overviews, not unobstructed full-figure readability evidence. The next private
four-Open diagnostic keeps these browser conditions, records synchronous UI,
publication and Fit phases plus existing native render audits, and adds
request-phase/type observations. It cannot qualify the required 5+10 protocol
or earn normal performance acceptance.

The closed four-Open phase3 diagnostic supports a bounded scheduling change:
its cold first run combines native add/select (31.9 ms) and the required UI
prefix (87.3 ms) in a 125 ms task. Missing-reference work is a nested 73.6 ms
portion of that prefix, not additional CPU time. Each Open has exactly one
nonempty audited main paint during final Fit; that paint uses all 2576 prepared
glyphs as cache hits, with no new misses. Further paint suppression or cache
capacity changes are not supported by these observations. Candidate4 adds an
ordinary timer before the required prefix, retiring queued selection callbacks
and pending paint first, and checking the document owner after the wait. The
existing caller-held history mutation scope protects both UI waits. Its exact
event coverage remains unchanged; a deferred Save can still return the existing
busy response during PDF.js destruction rather than automatically save.

The normal, uninstrumented `openperf1/normal6/` full journey closes in 158.547
seconds with all 20 source bindings stable and no surviving owned processes.
It passes 55 of 56 checks; a 125 ms Open task remains above the 100 ms limit.
Independent content review passes 70 checks covering both real Saves, complete
warm and fresh-Chromium artwork, continued editing, original source/font/image
records and all three downloaded PDFs. All 22 original PNGs are directly viewed;
all 13 native grids are identical to T5, with no new bounded visual defect. These
content and visual results do not override the performance failure. No unchanged
performance matrix cells are run. The next private diagnostic adds synchronous
reference-refresh/thumbnail timers and history boundary points to attribute the
remaining task and elapsed time after final Fit.

A separate, closed HEAD probe reproduces the network-event pattern in both
routed and unrouted contexts: JavaScript receives HTTP 200 with `ok: true` for
each of the five actual asset URLs, while the same Playwright Request object
subsequently reports `net::ERR_ABORTED`. This supports a narrowly classified
headers-complete HEAD probe, not a successful asset GET or an internal Chromium
cause. Future classification requires the exact owned origin and literal path,
HEAD/fetch, that exact failure, and a prior status-200 response for the same
context/request/URL. Raw failed counts stay visible; unmatched cancellations and
all GET failures still reject acceptance. Historical URL-only V2 failures retain
their original HOLD. The corrected controller also explicitly declares disabled
HTTP caching and captures an unobscured editor only after the final warm sample,
once the native completion toast disappears naturally. That final capture wait
occurs outside every measured Open and precedes no later timing sample.

Phase4 closes in 39.844 seconds with all 22 bindings stable, four complete
diagnostic Opens and no surviving owned processes. Independent review confirms
that add/select and the required UI prefix are separate. Each sample still has
one nonempty main render, wholly within final Fit. Fit takes 103.6, 100.1, 86.1
and 87.9 ms; history boundary elapsed times are 1689.2, 1691.5, 1600.3 and
1924.8 ms. Two thumbnail calls occur after Fit. Three terminal tasks of 235,
255 and 230 ms overlap none of the recorded wrappers and remain unattributed.
This instrumented run takes 3414.9–3555.2 ms from final-Fit end to editable
readiness. It does not attribute normal6's task or qualify repeated performance.

The existing CPU-only profiler subsequently closes in 35.531 seconds with all
20 bindings stable and no survivors. Its diagnostic Open is 5980.1 ms with a
122 ms task. Sampled exclusive costs include JSON clone traversal (342.028 ms),
JSON value preparation (244.798 ms), batch execution (223.874 ms) and shared
metadata detection (215.862 ms). Inclusive parent/child costs overlap; async
stacks are not complete elapsed measurements. The profile supports testing a
larger count ceiling for the two snapshot pipelines while preserving their
8 ms elapsed check after each generator step. That remains a cooperative
between-step target, not preemption of a slow serializer/getter. Count-only
history freeze/compaction retains its existing 128-node batches.

Private candidate5 combines that bounded scheduling hypothesis with a glyph
blit that restores only the exact, already-read Canvas matrix instead of copying
all Canvas state per glyph. Tile geometry, source fonts, admission, clipping,
paint order, cache and acceptance limits are unchanged. The recorded 108-test
run uses the actual private sources, including completed-capture ownership and
affine-transform/error restoration controls. Fresh normal browser, retained-file
and original-pixel checks remain required before accepting the candidate.

Candidate5's ordinary historical headless-shell run, `openperf1/normal7/`,
closes in 152.719 seconds with all 31 bindings stable and no surviving owned
processes. It passes 55/56 checks; its 114 ms task still fails the 100 ms limit.
Independent content review passes 75 checks, and the original-resolution visual
review retains all 13 native grids exactly against the accepted T5 run. Both
actual Saves, fresh-process reopening, continued editing and all three exported
PDFs preserve the reviewed content. This is functional and bounded visual
evidence, not repeated-performance acceptance.

A separate runtime inventory establishes that Playwright's default headless
shell uses SwiftShader on this desktop, while the explicitly documented
`channel='chromium', headless=True` mode uses Radeon 780M ANGLE/D3D11 with the
same Chromium 148.0.7778.96 version. The maintained full-journey and repeated
Open controllers now accept an explicit browser channel and record the actual
graphics report before measured work. Their historical default remains the
headless shell. These are distinct runtime rows; neither the inventory nor a
renderer change establishes a causal performance improvement or qualifies an
earlier failure. The practical workflow is in
`docs/runtime/BROWSER_QA_PLAYBOOK.md`.

The actual full-Chromium run, `openperf1/normal8-chromium/`, closes in 149.265
seconds with all 36 bindings stable and no owned survivors. Both its initial
and fresh browser processes record Radeon/D3D11. The full workflow completes,
but raw 54/56 remains HOLD: one Open task takes 134 ms, and two resource errors
reach the console. Original Open duration is 5117.1 ms; the maximum foreground
gap is 227.3 ms. Independent content review passes 74 checks, including all
1319 protected objects and both full saved/reopened documents. All three
downloaded PDFs retain the accepted T5 commands, resources and mapped Unicode.
All 16 changed PNG originals are directly viewed at original resolution, with
six exact originals carried from earlier direct review. No new bounded visual
defect is found. Native canvas artwork differs from the historical default headless-shell
row, so no literal cross-runtime pixel equivalence or antialiasing-only cause
is claimed. Source and all three PDFium export pages remain exact, and edited
and cold-reopened appearance is exact within this runtime row.

A controlled full-Chromium boot separately reproduces `GET /favicon.ico` 404
with the matching console location. Adding the existing app's explicit empty
favicon policy to `web/index.html` produces a second closed, seven-binding
stable boot with empty server, console, page and HTTP-error arrays. Independent
review confirms the one-line correction and both intervals. This fixes future
boots; Normal8's recorded console failure remains intact. Its task failure also
remains unresolved. The next private, reduced four-Open diagnostic attributes
glyph admission, bounds, geometry/key generation, tile acquisition and device
blitting with capped, observer-inclusive aggregates. It changes no product
geometry, cache, font authority or paint order and cannot qualify normal
performance. No computer-use session is active outside actual Affinity work.

The roadmap remains the same: reliable Selection/Direct Selection and editable
scientific PDFs precede V1. Figure 4 knockout editing/export and the remaining
repeated performance matrix still require their own accepted evidence; the
selected Beta.16 package is unchanged.

The closed `openperf1/phase6/` diagnostic has four complete Opens, all 29
bindings stable and zero surviving owned processes. Independent review verifies
all capped counters, phase sums, matched calls, exact inventories and empty
resets. Final Fit takes 151.4, 136.0, 168.2 and 166.6 ms; glyph aggregates account
for only 36.4, 31.4, 36.0 and 31.4 ms. Every final-Fit glyph is a prepared cache
hit, with zero misses or fallbacks. The difference is unattributed and includes
unassigned observer work; it is not exclusive CPU cost and does not justify an
atlas, larger cache or geometry change. Raw 16 HEAD failures and the reduced
2+2/incomplete 5+10 status remain unqualified.

The existing CPU-only profiler is then run on the actual full-Chromium runtime
with glyph timers off. `openperf1/cpu7-chromium/` closes in 46.063 seconds with
20 stable bindings and no owned survivors. Its Open takes 5747.2 ms, with a
274.3 ms foreground gap and a 147 ms task; these are retained diagnostic HOLDs.
Independent profile review separates three sampled Fit caller contexts:
1.522 ms for New, 3.064 ms during materialization and 146.125 ms in final Open.
All 35.985 ms of native `restore` samples within final Fit come from Fabric's
character painter, not the glyph blit's matrix restoration. That scope changes
font and can also change shadow/fill state, so transform-only restoration is
unsupported. Native `toDataURL` samples also belong to distinct final-Open,
workspace-capture and New thumbnails; their costs do not prove their scenes
are interchangeable.

Private `open-candidate6-v2/` tests one narrower hypothesis: defer the stock
character routine's browser-font assignment while the module's native glyph
painter uses its explicit font program and size. Real Fabric calculations and
native Canvas save/restore stay in place. Reads, other operations, nested scopes,
browser fallback and error cleanup flush the literal assignment. Preparation,
custom painters/helpers, foreign contexts and exceptional font state retain the
existing path. Independent source review permits one trial; all 115 targeted
tests pass against the exact private sources. Those controls use a mock Canvas
and do not establish browser setter behavior, pixel fidelity or performance.
The normal full journey and independent checks will close this candidate, then
the lane checkpoints for integration. No further optimization or Figure 4
completeness slice starts before that handoff.

The candidate is rejected at that stopping point. The uninstrumented
`openperf1/normal9-chromium/` trial closes in 145.390 seconds with all 42
bindings stable and no surviving owned processes. Raw 54/56 fails the unchanged
task and foreground-gap limits: Open is 6021.5 ms, its maximum task is 170 ms
and maximum gap is 305.4 ms. Both actual processes record Radeon/D3D11. Page,
console, HTTP-error and external-request arrays are empty. The plan's scope
string says 360 seconds by mistake; its actual argv and closed supervisor bind
the unchanged 240-second deadline. The executed plan is retained unmodified.

The full edit/Save/fresh-process/continued-edit/second-Save/three-export journey
completes. Independent content review passes 76 checks, including all 1319
protected objects, original source/font/image records and exact T5 PDF commands,
resources and mapped Unicode. All 13 artwork PNGs are byte-identical to Normal8's
same-runtime originals. The pure QPDF parse closes in 2.031 seconds with 13 stable
bindings and no owned survivors. These results do not waive either performance
failure or establish a speedup. The repeated matrix is not expanded.

All rejected product changes are retained privately, including exact source and
test copies in `open-candidate5/` and `open-candidate6-v2/`. Canonical
`app/app.js`, `app/pdfium-text-rasterizer.js` and `app/pdf-svg-materializer.js`
are restored byte-for-byte to accepted commit `58e17ccb8434ce2310b7e08c0e5dbdadcdcacb3e`.
Candidate-specific UI/raster assertions are removed from the active tests;
only the test-only explicit source-path overrides remain. The restoration map
is `openperf1/restored-baseline-product.json`. Earlier candidate descriptions
above are retained experimental history, not the final shipped implementation.

The integration checkpoint therefore contains the reviewed browser-channel and
repeated-Open QA support, runtime playbook, explicit test-source support, empty
favicon correction and this honest record. It does not contain the failed font,
batch-size, UI-scheduling or glyph-transform optimizations. Beta.16 remains the
selected package. Figure 4 knockout/export work stays private and unaccepted;
Affinity comparison and the remaining V1 performance/interaction/memory evidence
remain outstanding. The Figure roadmap remains the same. Per the coordinator's
pause instruction, no new optimization or PDF-completeness slice starts here.

The closed storage audit reports 11.873837 GiB total and 11.665218 GiB ordinary
generated output, with no read errors. Both configured budgets remain exceeded.
The existing reviewed disposable fixtures remain in
`qa_artifacts/PURGE-ME-2026-10-22` (about 248 MiB) after the earlier deletion
restriction and reversible move. Moving them frees no space; manual deletion is
still required. Current scientific originals, failed-trial witnesses and selected
release dependencies are retained. All inspected Open-performance temporary folders
are empty; no browser profile or process needs to remain running at this checkpoint.

Here, rejected means that the current candidate did not meet the unchanged
performance targets for integration at this checkpoint. It does not mean a
demonstrated content regression or proof that each component is ineffective.
Normal9's single timings are numerically worse than Normal8's, but they are
unpaired single observations without isolated component trials or controlled
OS/background caches. Their controller, fixture, viewport, Chromium version and
actual Radeon runtime agree; Normal9 additionally includes the favicon fix.
Neither causal regression nor a reliable speedup is established.

The disposition preserves incremental work explicitly:

| Piece | Observation and disposition |
| --- | --- |
| Earlier native glyph, preparation, reference and cache work | Remains in `58e17` and its ancestry, including `091770`: exact native glyph programs/tiles, immutable bitmap ownership/fallback, cooperative preparation outside Canvas scopes, the recovery-panel fast return, bounded immutable data-URL size/hash memo and native scene-plane painting. Earlier T2/T3/T4 observations did not isolate normal performance benefit; the later combined T5 passed its 56 original checks. |
| Candidate4 (`802d` App) | Adds a timer before required UI. Phase4 observes separated add/select and required-UI spans, a useful scheduling result. Normal6 still misses the task limit. Exact source and evidence remain private. |
| Candidate5 (`6150` App / `d29e` rasterizer) | Combines larger count caps with per-step 8 ms checks and matrix-only glyph-blit restoration. Normal7's 5992.4 ms / 114 ms task is modestly lower than Normal6's 6133.7 ms / 125 ms task, but two simultaneous changes and one observation do not isolate or prove a benefit. Retained privately for later isolated or combined tests. |
| Candidate6 (`9782` rasterizer / `a177` materializer) | Adds scoped font deferral to Candidate5. Its targeted, content and bounded pixel checks pass; its single normal performance result misses both limits. The complete sources, patches, builders and tests are retained privately, rather than discarded as individually disproved ideas. |

Only these later unqualified product deltas were removed from the canonical
integration source. The earlier accepted glyph/reference/cache improvements and
T5 publication/UI/final-Fit ownership remain in place. A future authorized slice
can test the retained later pieces independently or together; this checkpoint
does not start that work.

The exact small patches, full candidate/base hashes, stacked dependencies and
original-clock observations are inventoried in
`qa_artifacts/t22/openperf1/optimization-disposition.json`. Historical shell
launches did not record their own selected GPU; software rendering is established
by the separate runtime inventory, rather than retroactively added to those runs.

Final Normal9 visual closure covers all 22 originals: 21 are byte/RGBA identical
to Normal8, and the remaining continued-selection editor differs only at 38
scrollbar-edge pixels outside the scientific page. Its changed original is
directly inspected at original resolution; every carry has prior direct-view
provenance. Existing tiny-fit, fallback and export-warning limits remain.

After restoring the accepted product baseline, all 104 active targeted Node tests,
three repeated-controller Python controls, App syntax and in-memory Python syntax
checks pass. The final identical boot probe closes in 2.719 seconds with all 10
bindings stable, no owned survivors and empty server/console/page/HTTP-error
arrays. These final checks use the accepted product files; the private candidate's
115-test result is separate. No package, publication or selected release changes.

## 28 October: Figure implementation resumed

Ian's instruction to keep working revokes the integration pause above. The
accepted glyph, preparation, ownership, selection and history improvements stay
in place; retained Candidates 4/5/6 remain available for isolated reuse. A missed
target does not establish that each component was ineffective. Beta.16 remains
the delivered release, and the coordinator owns combined-package promotion.

The exact beta.17 package from `ca8c2042` passes its actual editing, Save,
fresh-process continuation and export checks, but its original 54/56 result
retains the 328.4 ms foreground gap and 128 ms task failures. A fresh sampled
package control in `qa_artifacts/t28/profile0/` retains both failures and again
identifies synchronous thumbnail encoding alongside separate final-render and
serialization costs. Instrumented timing is diagnostic, not acceptance.

The first bounded change reuses bundled Fabric's native asynchronous PNG path
for each existing thumbnail capture. Final PDF Open and project serialization
retain their separate captures; neither is skipped or reused without ownership
proof. Canvas/page/revision checks surround asynchronous completion and reject
stale or cancelled captures. Ordinary synchronous Save, master editing and
disabled-thumbnail behavior retain their existing path.

The source controls pass 85 Node tests, 35 package/controller Python checks and
15 actual-source metadata checks. The latter fixture now also extracts the
existing isolation snapshot helper it previously omitted. Independent review
accepts the bounded source, original-resolution natural editor/buffer images
and actual native PNG equivalence in `t28/thumbnail1/`: both 115 by 150 thumbnails
are byte- and RGBA-identical, the complete editable scene is unchanged and all
recorded canvas fields restore. The raw diagnostic remains HOLD at 6285.2 ms,
261.2 ms maximum gap and 115 ms maximum task. This unpaired canonical-source
trial does not establish a speedup, package acceptance or repeated performance.

The repeated Open controller now binds a verified extracted package and all
five payload roots. Its original clocks, readiness, five isolated-context cold
and ten warm repetitions, raw failure records and thresholds remain unchanged.
Shared heavy jobs use the coordinator's physical runtime lock in addition to
their existing bounded process owners. Browser/native package qualification,
first faithful natural paint, sustained dense interaction, memory, broad
selection parity and the genuine Figure 4 editable/export corpus remain open.
The roadmap and original acceptance limits remain unchanged.

The next bounded paint change keeps the existing embedded-font renderer,
current-plane transforms and device-paint scope, while avoiding a redundant
stock character state scope for strictly admitted single black glyphs. An
explicit one-time startup handoff admits the installed scientific-style copier;
unknown methods, backgrounds, effects, preparation and custom-painter scopes
retain their original path. Raw character offsets and exactly-once browser
fallback remain covered. All 67 focused source controls pass on unchanged
Fabric/PDFium supplier bytes, with independent source GO.

The ordinary `t28/native1/` journey executes the shortcut during measured Open
(7728 native primitive glyph paints before any controller-derived render).
Editing, actual Save, fresh Chromium-process Open, continued editing, second
Save and all three downloads complete: 55/56 original checks, retaining the
116 ms task failure. Its single 244 ms foreground gap is within the original
limit, while 6553.3 ms Open does not establish ordinary repeated performance.
Independent actual-file review passes 57 checks over both saved documents,
all 1319 protected objects and original source/font/image programs. A bounded
pure QPDF parse verifies complete decoded commands, resources, embedded fonts
and mapped Unicode against the accepted T5 exports. All 22 PNGs match the
previous package originals exactly; historical independent visual provenance
is retained separately from the implementation author's new inspection.

Neither this component nor its single within-limit gap qualifies the package or
V1. The current-source sampled `t28/profile1/` run records a 124.3 ms artwork
render entirely inside its 128 ms task, using the same performance clock.
All 2576 glyphs hit prepared tiles; the remaining stall is a settled full render,
not evidence that the retained pre-UI timer would correct it. The final Fit
samples 118.051 ms, including 39.700 ms in the direct native-fill helper and
25.313 ms in its existing raster paint. Those inclusive costs overlap. Native
device save samples only 1.639 ms; the historical 36 ms restore estimate does
not describe this source. Both derived thumbnail renders and native Blob calls
still consume time. All failed trials and original thresholds remain recorded.

The next source candidate reuses exact prepared glyph geometry through weak
source-glyph keys. Each record contains scalar request/transform data and tile
identity only; the current font and live bounded tile cache remain authoritative.
Custom/preparation scopes, changed inputs, absolute translations, evicted tiles
and font replacement retain the ordinary path. Both source-glyph loops pass the
token outside the immutable preparation request. All 85 focused controls pass,
and independent source review resolves the retained error, scope and Symbol-key
ownership findings before runtime execution.

The normal Open-only `t28/recipe1/` run closes in 33.438 seconds with 18 bindings
stable and zero owned survivors. All 7728 initial paints use prepared geometry
before any controller-derived render, with zero recipe misses or native
fallbacks/errors. Its 20 original checks pass: Open is 5603.7 ms, maximum gap
202.6 ms and maximum task 94 ms. Independent bounded review passes 30 checks;
all seven original PNGs are byte/RGBA-identical to previously independently
reviewed originals. One observation within the task/gap limits does not qualify
ordinary repeated Open, first faithful paint, editing, Save, cold Open or a
package. The 5-second repeated requirement remains open.

The retained Candidate5 snapshot component is then isolated: history and
workspace capture use a 1024-step count ceiling with an 8 ms elapsed check.
The capture API's default, count-only history freeze/compaction and timer
fairness remain unchanged. Nine deterministic actual-function controls cover
elapsed/count yielding, cancellation, exact output and first/48 ms timer
fairness. Related 109-test and 102-test suites pass, with overlapping coverage;
their counts are not additive. The native-Fabric history fixture retains its
original assertions and adds 257 synthetic measurement rows to exercise larger
batches; all nine checks pass. Its earlier minimum-yield failure and the clock
test's initial copy-phase fixture failure remain in the raw logs.

Independent source review passes 25 checks over this two-line App change,
fixture and clock controls. A fresh `t28/combined1/` full edit/Save/new-process
Open/continued-edit/second-Save/three-export journey is queued against 22 frozen
bindings. The earlier recipe-only `recipe2-plan.json` was prepared but never
executed. No combined runtime, committed-package, native or repeated matrix
acceptance follows from source review. The roadmap and original budgets remain
unchanged; Beta.16 remains delivered and the coordinator owns promotion.

The ordinary `t28/combined1/` journey subsequently closes in 141.985 seconds
(142.266 seconds including the shared wrapper), with zero owned survivors,
all 22 plan bindings and all 1621 controller source entries stable. All 56
original checks pass, including editing, two actual Saves, a fresh Chromium
process, continued editing and three downloaded PDFs. Initial Open is
5125.6 ms, maximum gap 194.7 ms and maximum task 78 ms; all 7728 initial glyph
paints use prepared geometry, with zero misses/fallbacks/errors. Page, console,
HTTP-error and external-request arrays are empty. These are single observations,
not repeated 5-second acceptance or an isolated causal speedup.

Fresh independent review passes 57 actual-file checks and verifies all 22 PNG
originals exactly against the prior independently reviewed originals. Both
saved documents preserve the complete protected object, source, font and image
records through cold Open and continuation. Cold renderer counters record zero
preparation and zero recipe hits; the functional journey does not measure cold
Open performance. After the shared runtime release, complete downloaded-PDF
parsing closes in 4.782 seconds (5.141 with the outer wrapper), with all 37
bindings stable and zero owned survivors. All three actual PDFs retain the
complete accepted T5 decoded commands, resources, font programs and mapped
Unicode, including the intended continued label. The final independent receipt
in `t28/combined1-content-review/final-receipt.json` passes 135 checks: 57 fresh
actual-file, 68 image/binding and 10 PDF/final checks. Previously passed checks
are retained without rerunning unchanged controls.

Ian's usage-budget instruction closes this slice at the accepted checkpoint;
no further experiment or package/matrix run starts here. The coordinator owns
the next integration and qualification. Repeated performance, natural first
paint, native/package validation, dense interaction/memory, broad selection
parity and Figure 4 remain open. The roadmap and installed/public pins remain
unchanged.

## 28 October: sustained dragging after the matched beta.17 delivery

The coordinator completed the matched desktop/web beta.17 delivery before this
bounded continuation. Its runtime source is `ee9d93b3`; the subsequent Figure
release documentation commit is `4ab1bd76`. The delivered package remains the
comparison basis, and this work does not package, publish or change its pins.
The separate private C2 clone/method-table changes remain preserved under
`qa_artifacts/rc28/correction2/private-working-source/`; they were parked while
isolating the next dragging change.

The maintained genuine Figure 2 controller now accepts an explicit Chromium
channel for both the warm and fresh-process continuation. The historical
headless-shell default, trusted input stream, timing ceilings, pixel witnesses,
geometry, protected-artwork, Undo/Redo, Save and export assertions are unchanged.
Both runs use Chromium 148.0.7778.96 with the reported Radeon 780M/D3D11 renderer
at 1440 by 1000 in the light theme. Desktop control and Affinity are inactive.

The delivered `qa_artifacts/drag29/baseline1/` journey completes all actual file
operations but passes only 58 of 70 checks. The warm and cold 120-move streams
take 24.662 and 22.904 seconds. A separate bounded CPU profile attributes
substantial time to full native text painting; its instrumented timing is not
acceptance. Native save/restore is a small part of that profile, so the retired
CTM-only blit experiment is not revived.

The bounded source change lets an ordinary admitted live glyph fill seed the
existing two-phase, globally bounded recipe cache after zooming. It retains
exact scalar request and CTM matching, live font/tile identities, full native
save/restore and the complete artwork painter. Live seeding requires all
consumed request fields to be own scalar data and an immutable parser over a
private font-byte snapshot. The exact same private bytes are uploaded to
PDFium. Caller-supplied metric callbacks retain their ordinary live path.
Independent source review resolved byte-aliasing, descriptor-callback upload
divergence and inherited-request getter findings before browser execution.
All 71 targeted tests pass, including the 11 new live-cache controls. The VM
fixture now supplies normal timer functions for legitimate cooperative yields.

The unpackaged private runtime in `qa_artifacts/drag29/live1-runtime/` differs
from the complete delivered payload in this one renderer file. Its normal
`live1/` journey also passes 58 of 70 checks, with the same 12 responsiveness
failures. Warm/cold streams take 21.761 and 20.934 seconds; animation-frame p95
is 235.1/226.8 ms and native artwork-paint p95 is 330.2/327.0 ms. One observed
pair does not establish a causal or repeated speedup. All original absolute
budgets remain failed and unchanged.

Independent actual-file and visual review passes 61 checks. Both actual Saves,
fresh-process Open and continuation preserve the complete artwork, protected
world positions, 960 source text records, original PDF, two font programs and
six images. Seven of eight original image pairs are byte/RGBA exact; the
remaining 21 pixels are confined to the horizontal scrollbar. Lossless unscaled
halves cover the large originals when whole-image transport would resize them.
Complete QPDF comparison of both actual exports verifies every decoded drawing
command, resource, font program and mapped Unicode character. All browser,
server, shared-wrapper and parser jobs close with zero owned survivors, and
all consumed-source/runtime bindings remain stable.

The exact source review, unit log, normal runs, original images, saved files,
PDF parse and independent receipt are retained under `qa_artifacts/drag29/`.
This accepts a bounded renderer component and its scientific-file continuity;
it does not qualify sustained dragging, the remaining desktop/theme matrix or
V1. The next meaningful slice must reduce the dominant full-scene painting
work. Repeated Open, dense interaction and broader selection parity remain
open; the roadmap, original thresholds and delivered beta.17 remain unchanged.

## 29 October: retained screen painting for PDF point dragging

Point dragging now derives two disposable screen layers in original drawing
order: artwork before the edited path, the live native path, and artwork after
it. Native geometry, clips, text, source records, history and export remain in
the existing scene. Each retained surface is bounded to 64 MiB; unchanged
clicks can retain the pair, while edits, commands, view/resource changes and
gesture cancellation retire it. Preparation requires an opaque solid background,
known painters and an exact full-backing RGBA comparison before issuing reuse.

This follows the documented principle of reusing displayed artwork. The
[Illustrator SIGGRAPH paper](https://web.engr.oregonstate.edu/~mjb/cs550/Projects/Papers/CAcceleratingVectorGraphicsRendering.pdf)
describes its rendering subsystem, cached CPU tiles and GPU path pipeline.
[Affinity's hardware-acceleration documentation](https://www.affinity.studio/help/extras-hardware-acceleration/)
distinguishes accelerated canvas preview from CPU vector operations. Affinity's
private rendering implementation remains unknown. Computer use is inactive
throughout this browser implementation and qualification work.

Complete source checks occur before preparation and before issue. App-owned
publication revision, canvas/document/view/resource ownership, live target and
ancestor state, and known passive paint callbacks then guard each active frame.
External artwork requests, direct renders, export, history and document/tool
commands invalidate reuse. Silent foreign writes outside the App publication
contract are unsupported. Foreign painters, layout strategies, controls and
callbacks retain ordinary painting. A duplicate 400,000-field activation scan
was removed after it caused a 107 ms first-input task without adding coverage
under the unchanged issue revision.

Release preserves the accepted native layout sequence: the scene-delta move
performs its ordinary bubbling hierarchy refresh, then final admission is
evaluated and the existing conditional non-bubbling final refresh runs. Inactive
known PDF objects receive exact parent-local hit bounds; native activation still
calculates their interactive controls. Custom coordinate and control methods
retain their original route. Native and owned-layout comparisons are strict,
including raw local fields and world matrices. No new numeric tolerance remains.

The controlled `drag30/retained*` experiments reduced the same 120-move stream
from roughly 21 seconds to 2.3 seconds, with whole-backing before/after RGBA equality.
Their constant fixture guard does not qualify normal activation. Automatic
`normal3/` used all 120 cached frames in both warm and reopened editing with zero
fallbacks. Its 62/70 result retained eight timing failures. Independent review
passed 38 content/visual checks over both actual Saves, 1320 model objects,
960 live texts, original PDF/font/image programs, complete exported-PDF commands
and all eight full-resolution images.

`normal5/` subsequently passed 66/70, retaining artwork-paint spacing and the
closing foreground gap in both sessions. Task/animation/input/geometry and pixel
witness checks passed. These failed trials remain recorded. A locked, pinned
task yield now precedes point-history capture, and the continuous observer reads
the original three footprints in one bounded region (with a 1:1 atlas fallback).
Eleven complete old/new recorder controls preserve all raw RGBA, event, time and
qualification fields. The observer's cost remains charged to the original limits.

The exact `normal6/` candidate had source-review GO, 318 targeted Node checks and
14 Python policy checks passing, but retained four browser timing failures.
`normal7/` passed 67/70, retaining two paint-spacing failures and a 294 ms warm
foreground gap. Those failed trials remain failed.

Release now paints native leaves in original order into one private full-size
OffscreenCanvas in cooperative batches, then presents only the completed image.
Unknown isolation, painter, callback, view or resource state returns to native
complete painting. Both history publication and mutation-lock release await the
final paint. Native paint errors and owner disposal settle that wait through the
existing rollback path. The whole-backing parity diagnostic `state8/` found zero
differing pixels across 3600 by 4659 pixels; the earlier HTML-canvas batch trials
with six or seven edge differences remain recorded and unqualified. This proves
that fixture result, not a general cause for browser rasterization differences.

The normal13 candidate painted valid retained point frames immediately after
input; bursts above 125 Hz coalesced onto the ordinary animation frame. In `normal7/`, most input-to-paint
latencies were 2–4 ms, while the controller itself delivered some moves 30–43 ms
apart. This Python runtime reports a 15.625 ms GetTickCount64 monotonic clock.
A separate controller calibration reproduced 31.31 ms interval p95 with the old
asyncio wait and 17.32 ms with absolute QPC deadlines plus native sleep on an
awaited worker thread. The controller now uses that precise schedule, with the
same 120 trusted moves, two-second duration, coordinates, witnesses and limits.
Its classification and percentile functions remain exactly equal as ASTs.
Cross-controller timing changes are not isolated product speedup evidence.

`normal8/` passed all 70 checks at 1440 by 1000, light theme, in full Chromium on
the recorded Radeon renderer. Warm and freshly reopened streams took 2032.9 and
2033.2 ms; native-paint gap p95 was 23.6 and 20.2 ms, and the largest foreground
gap was 240.3 and 181.1 ms. Both used all 120 retained frames with zero fallbacks.
The settled offscreen paint used 41 batches, with maximum batch durations of
5.3 and 7.6 ms. All geometry, intermediate/final pixel, Save, reopened editing,
second Save and exported-PDF controller checks passed. Independent review still
held its exact content: skipping the intermediate native refresh changed 1175
serialized `top` fields and 214 PDF translation operands, with the raw values
retained. This was already present in normal5/6 and did not originate in the
offscreen painter. Restoring the accepted layout order in `normal9/` removed
every difference: both Saves match the accepted reference across all 1320
objects, full world matrices, world path operands, effective clip coordinates
and source text; complete PDF commands also match exactly. Identity, time and
import telemetry are the only enumerated cross-run differences.

`normal9/`, `normal10/` and `normal11/` retained timing failures. A normal12 CPU
profile identified the remaining native settlement cost; that instrumented run
does not qualify timing. Retained point release now enters the existing recovery
transaction before settlement: the complete Undo/Redo state is pinned and edits
are locked before a timer turn, then the unchanged native settlement runs, then
another timer turn precedes capture. Owner checks, no-op behavior, rollback,
retirement and final-paint/history completion remain inside that transaction.

`normal13/` passed all 70 checks on the same declared desktop/runtime. Warm and
freshly reopened streams took 2038.7 and 2043.1 ms; native-paint gap p95 was
23.8 and 19.9 ms, and the largest foreground gap was 139.6 and 53.1 ms. Both
retained all 120 paints without fallback, and no long task intersected the moving
stream. Full-resolution fixture parity and every original deadline/pixel/model
predicate remain required. Source review13 is GO; 352 targeted Node tests and
15 Python tests pass with exact current bindings. Fresh independent review13 is
GO on all 39 content/visual checks: both actual Saves preserve all scientific
numbers and complete native own/world/path/clip/source fields exactly against
both accepted controls; all 38,766 actual PDF commands, resources, font programs
and 2,817 Unicode entries are exact. All seven original-resolution images were
independently inspected. The consolidated receipt is
`qa_artifacts/drag30/normal13-review/receipt.json`. Both runtime supervisors closed
with zero owned survivors and frozen source stayed unchanged. Earlier source
reviews and failed browser/content results remain recorded rather than relabeled.

The broader deck fixtures retain their separately recorded pre-existing failures;
the HEAD-App fixture differential is in `drag30/extended-unit-differential1.json`.
This is targeted point-editing validation, not a claim that every repository test
or the complete V1 desktop/theme matrix passes.

Source/output receipts and all raw runs remain under `qa_artifacts/drag30/`.
That checkpoint covered supported imported-PDF point handles at one desktop
size/theme. Its remaining desktop coverage is completed below. Repeated Open,
broader tool parity and V1 qualification remain separate; the coordinator owns
integration and promotion.

## 29 October: desktop point-drag coverage and selection references

The desktop expansion exposed remaining per-input UI work. A diagnostic profile
found repeated canonical node-metadata queries within one overlay pass. These
reads now share a private per-pass result while each caller receives independent
mutable rows. Changed path/metadata references invalidate the entry; the next
pass reads in-place edits afresh. Public node IDs, classes, control visibility,
selection normalization and original geometry calculations remain unchanged.

Artwork requests now coalesce through the existing native animation-frame queue.
The first scheduling candidate passed its matched narrow dark control, but source
review rejected an exception path that could interrupt pointer-up cleanup. Release
now clears capture/gesture state and forwards paint errors into the existing
pinned recovery transaction. The original failed review remains recorded.

The following light narrow run still failed both paint-spacing checks at 24.7 ms
against the unchanged 24 ms limit. Its profile attributed 110–136 ms across 120
moves to rebuilding the node overlay. The current candidate defers only that
disposable UI work for an active, ready, valid retained point gesture. The
existing native paint cycle consumes it once from the latest model; every input
still performs its original operand, snapping, modifier and tangent updates.
Ordinary or unsupported editing keeps the immediate UI route. Release consumes
owned pending UI even when the native preview is invalid or no frame is queued.
External publication invalidates retained artwork in `finally` if UI work throws;
an old canvas cannot consume another canvas's pending update. Cancellation,
clear, direct overlay rendering and retirement discard obsolete work. No new
timer or passive paint observer was added.

The exact `drag34` candidate passes all 70 browser checks in each desktop cell,
including warm and fresh-process continued editing, natural intermediate/final
pixels, geometry, Save, Undo/Redo, second Save and actual PDF export. All cells
use the same declared full Chromium/Radeon environment and unchanged budgets.

| Desktop | Theme | Paint-gap p95, warm / reopened (ms) | Largest foreground gap, warm / reopened (ms) |
| --- | --- | --- | --- |
| 1280 × 800 | Light | 20.1 / 20.2 | 106.5 / 151.9 |
| 1280 × 800 | Dark | 19.5 / 19.8 | 101.9 / 70.6 |
| 1440 × 1000 | Light | 19.4 / 19.5 | 78.8 / 91.9 |
| 1440 × 1000 | Dark | 18.7 / 19.8 | 174.8 / 25.1 |
| 1920 × 1080 | Light | 19.5 / 19.7 | 22.7 / 102.0 |
| 1920 × 1080 | Dark | 18.5 / 18.8 | 82.7 / 101.9 |

No moving stream intersects a long task. Each has 120 trusted moves, 120 retained
paints and zero fallbacks. Source intervals bind 3318 inputs per cell and remain
stable; every owned browser/server and shared supervisor closes with zero owned
survivors. The focused source/test group passes 429 Node and 18 Python checks.
Independent source review is GO. All six independent content/visual reviews are
also GO: 120 fresh content checks and all 42 original images pass. Both actual
Saves in each cell preserve exact scientific fields, source text, native own/world
geometry and effective clips. Complete actual PDFs match the accepted parsed
content outside four explicitly enumerated metadata values. Ten new UI originals
were viewed unscaled; 32 originals have exact independently reviewed pixel
equivalence. The consolidated independent receipt is `drag34/matrix-receipt.json`,
with per-cell records under `drag34/independent-review/`; their scope remains
separate from browser timing. The complete browser results are in
`drag34/matrix-summary.json`. Earlier failed candidates and profiling/setup trials
under `drag31/`, `drag32/` and `drag33/` retain their original dispositions.

The maintained controller also fixes a post-capture chronology classification:
two rounded elapsed frame timestamps may tie only when finite, typed native RAF
timestamps strictly increase. Backward elapsed time still fails; render and timer
ties remain invalid. The frozen input action, observation windows, raw records
and every numeric limit are unchanged. Replaying the old narrow failure changes
only its frame-coverage classification; its input-cadence failure and overall
failure remain. Regression controls cover missing, nonfinite, string, Boolean,
equal and backward native timestamps. This is a recorder-classification repair,
separate from the product improvements.

A bounded [REA](https://github.com/morluto/rea) investigation used the compatible
pinned 6.7.0 CLI under ignored QA, with lifecycle scripts disabled and no global
agent configuration or restart. Its scoped check found no configured Ghidra.
Execution-free PE inspection separately found explicit shape-cache invalidation,
transformed bounds, renderer tiles and typed PDF path/text/group/image interfaces.
These exported names corroborate useful architectural boundaries but establish
neither active call paths nor Affinity's private drag/selection algorithm. The
profiler-derived Figure changes are not attributed to decompilation. Exact tool,
installed-file and limitation records are under `drag33/rea-affinity/`.

Ian's 51.63-second Affinity recording provides a more direct behavior reference.
The document path visible at 20 seconds resolves to the byte-identical genuine
Figure 2 fixture. It shows live marquee candidate outlines/counts, intersection
with complete labels at 24–26 seconds, mixed object translation at 30–38 seconds
with unselected artwork fixed, and selection continuity through zoom. The Node
Tool tooltip is documentation visible in the recording, not a demonstrated set
of modifier executions. Import/grouping settings and input event logs are not
shown; object counts cannot be imposed on a different text reconstruction. The
recording cannot establish the 24 ms budget or an internal caching mechanism.
Its unmodified source binding, full-resolution frames and concrete comparison
cases are retained in `drag34/affinity-video1/`. Video analysis used no foreground
computer control; the earlier short native session was reset after active use.

The point-drag desktop/theme milestone is now browser-qualified. The broader
roadmap sequence remains the same: repeated Open and broader object/node
selection parity still require their own qualification before V1. The video
refines those existing selection cases without expanding this point-rendering
change or altering parked C1/C2 work. Delivered beta.17, package/version pins and
publication remain unchanged.
