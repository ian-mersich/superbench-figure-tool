# Windows Figure browser QA

Run from `C:\Users\ianme\Desktop\Projects\superbench_figure_tool` with native
Python and Node. Keep generated output under `qa_artifacts/`. Run one browser
job at a time through `scripts/run-owned-browser-qa.py`, with a fresh output
directory, a bounded deadline and source hashes before and after execution.
Require a closed supervisor with zero remaining owned processes.

For hosted cancellation checks that compare the document's unsaved flag, wait
passively for the real Browser files status to report saved, the inner document
to report clean and the browser session to be ready and idle before recording
the gesture baseline. Record the session key and status. Public autosave can
otherwise clear that flag during an exact cancellation. Keep the maintained
artwork, selection, history and dirty-state assertions unchanged; never disable
autosave, set dirty state or acknowledge a save directly. Preserve failed runs
and use fresh paths for the complete retry, including stdout/stderr logs. The
beta.25 public retry and diagnosis are retained under `qa_artifacts/rc40/publication`.

For saved editable PDF text, verify the selected child before waiting for text
controls. An ordinary click can select the PDF container; public double-click
enters its contents. Preserve the first cold capture before any later entry or
Fit. Text stroke is intentionally absent from the current Inspector, including
More properties. Renderer stroke controls therefore use a detached native-label
clone, with recorded source-plane admission, painter/font resources and visible
colored-pixel contrast against a zero-width reference. Keep that renderer
witness separate from user-facing editing and from the unchanged live document.

## Scientific Assets and Templates

`scripts/check-assets-templates-browser.py` extends the maintained Library
drawing controller. Use `--case 1440x1000-light` for the first integrated pilot;
omit it only for a separately allocated six-case desktop/theme matrix. Keep
outputs fresh under `qa_artifacts/assets-templates-2026-11-03/` and use the shared
and owned wrappers below. Freeze the controller's complete source inventory
before launch and compare it after closure, including failed runs.

For a bounded discovery diagnosis, add `--stop-after library-surface` with one
explicit `--case`. This runs the same startup, legacy preference migration,
Library search and actual capture, then closes before insertion, edits or
Save/Open. The diagnostic records zero planned editing/persistence actions.
Use a separately allocated shared deadline of at most 90 seconds and owned
deadline of at most 70 seconds. It cannot qualify the integrated journey.

For one fresh RT-qPCR persistence check, use `--stop-after qPCR-roundtrip`
with one explicit desktop case. This mode accepts the SOURCE checkout only.
It inserts the template, edits one named part and the live title, downloads an
actual new Figure file and opens it in a fresh context. The first cold image
precedes document/native inspection; complete warm/file/cold payloads, native
states and field differences are retained before strict assertions. Independent
review must require identical complete raw `project.fabric.objects` arrays:
31 unique roots comprising six assets, five connectors and 20 text objects.
Keep the maintained authored/native comparisons unchanged and explain other
raw differences only through their existing normalization. This mode runs no
other insertion cohort, natural-paint witness or additional connector gesture.
Use a separately allocated shared90/owned70 window and fresh output paths;
planned and completed actions are recorded separately. It does not qualify the
broader Library, connector-editing or clean-package journeys.

Every Assets/Templates Save/Open path now uses that settled public Open and
captures the first cold view before serialization or native inspection. It
retains complete warm, actual-download and cold payloads, native snapshots or
errors, original embedded thumbnail PNGs, and raw, key-presence, authored and
native differences before preservation assertions. Keep the three thumbnail
sources separate: the actual Save image can differ from a later serialization.
An early failed assertion must not discard the operands needed to diagnose it.

The ignored `check-replacement-save-cold-witness.py` prepares four actual form
replacements and four stable paired references, followed by one Save/Open. It
requires an approved editor-fix App hash and a separate runtime allocation. Its
ordinary replacement clicks do not repeat natural-paint timing qualification;
the maintained full pilot retains its original timing scope by default. Failed
historical files and reports remain unchanged.

This witness also uses public Undo/Redo around the last replacement, retaining
the exact eight ordered native root arrays and all four reference drawings. It
records part IDs before Save, closes the warm browser and launches a genuinely
new Chromium process for cold Open, recording both process IDs. Assertions use
the retained pre-Save observations after the shared evidence dump is complete.

The optional request classifier requires retained image lifecycle, Library
action and DOM-source retirement evidence plus matching manifest/file hashes
and loaded replacement previews. It explains only proven image-source
cancellations. Missing, ambiguous, broken-preview, fetch, script, server and
unknown-source failures remain fatal. Keep offline explanations separate from
the original failed reports and from authored-data or pixel acceptance.

Template previews load lazily. Scroll each real card into view and bound the
combined reveal/visibility/decode operation to 12 seconds; do not force eager
loading. Record both requested/current image URLs, completion and natural
dimensions before and after. Phase checkpoints persist the partial report and
stdout before startup, Library waits, each preview and major authoring journeys.
The retained run02 deadline preceded its first capture; an unbounded aggregate
preview decode is the strongest static explanation, rather than a proved
stopped await or a diagnosed product failure.

The pilot checks the unified Templates view, legacy Scenes navigation, all eight
new scientific templates and the existing immunoblot on separate clean figures.
It inserts all 40 new drawings in Style 4 and recolors every rendered named
part. A separate paired-form cohort exercises all four styles, in-place drawing
replacement and Library navigation. Three actual File Saves and fresh-context
file chooser Opens compare downloaded content and native vectors. The complete
matrix repeats representative editing and persistence at three desktop sizes
in both themes; its planned total is 13 Save/Open pairs. These are functional
checks, without a general performance or native-host claim. The existing
representative adipocyte pair also supplies two immediate repaint witnesses:
a high-contrast part-color change and the final Style 4 form-replacement click.
They reuse the maintained action-paint observer unchanged, including its 250 ms
deadline, three correct observations over 80 ms, and opaque 3×3 pixel checks.
No serialization, save, screenshot or test-requested render precedes the frozen
paint verdict. A visible, source-bound target form supplies the replacement
reference; its mapped foreground must disagree with the old form before action.

The canonical dirty checkout is a source pilot for finding bugs and preserves
private PDF experiments. It cannot establish release or package parity. The
complete release matrix must bind a clean coordinator-composed package from the
delivered beta22 base and only accepted changes. Keep the six-hunk Library App
patch separate; never stage the entire dirty App.

Art review precedes browser acceptance. See
[the content lane note](../architecture/ASSETS_TEMPLATES_LANE_2026_11_03.md)
for current acceptance status and preserved raw failures. A passing controller
still requires independent inspection of original-resolution screenshots.

When an authored-document comparison fails after an actual saved file Open,
preserve and hash that downloaded file before recreating a figure. The bounded
`scripts/check-assets-templates-cold-file-browser.py` diagnostic accepts only the
retained pilot05 RT-qPCR file and its exact hash. It uses the maintained public
file chooser, captures the first restored image before serialization or native
inspection, then writes complete input/restored payloads, native state and raw
and authored field differences before applying strict checks. Missing native
nodes must not prevent the field-difference dump. Use a separate shared90 /
owned70 coordinator window and a fresh ignored output directory. This is a
one-file source diagnosis, with no Save, editing, paint or package claim.

## Saved workspace view restoration

Use `scripts/check-saved-viewport-browser.py --root <frozen-runtime>
--expected-app-sha256 <sha256> --fixture-dir <inputs> --output-dir <fresh-output>`
through the shared/frozen/owned wrappers below. The finite fixture directory must
contain `figure.fsproject` and `presentation.fsproject`: the same two-document
workspace ordered Figure then Slidedeck, with the named mode active and complete
manual saved views. Include the corresponding ordinary native payloads as
`figure.fsfigure` and `presentation.fsdeck`. Preserve genuine scientific native
content and bind every input byte; the controller does not construct artwork.

The light-desktop journey checks both active branches, real asynchronous resizing
at all three desktop widths, manual/Fit tab returns, new/imported documents,
four actual project Saves and two fresh-process Opens. Critical cold captures
precede any later navigation. Passive toast expiry is allowed; Fit or zoom must
not rescue a restored manual view. Require exact native file/content, history
and saved-view checks plus independent original-resolution review. This is
functional persistence qualification, with no timing or native-host claim. See
[the restoration policy](../architecture/SAVED_VIEW_RESTORATION_2026_11_02.md)
for the retained baseline and explicit-Fit counterexample.

## Public beta21 workflow adapter

`scripts/check-public-style4-browser.py` is the maintained, finite beta21 public
adapter. It reuses the Library drawing/discovery/native comparators and retains
the literal browser source executed for the fresh HTTPS six-case/root run. See
`scripts/qa/beta21-publication/README.md` for arguments, finite audit companions
and the frozen historical paths. Its promotion is QA-only; sealed product
source `24440c08` and existing package `9c2277b1…` remain authoritative.

Use `--base-url https://imersich.com` for live qualification or `--site-root`
for the built candidate, with the verified package root/digest and fresh output
beneath `qa_artifacts/rc35`. The default covers 1280×800, 1440×1000 and 1920×1080
in both themes, plus a separate public-root entry. A subset is explicit with
repeatable `--case`; never silently merge a prior pilot into a fresh matrix.

Declare Simple/Style-collapsed Figure panels and Format-closed Presentation
panels before warm Save and before the actual cold file chooser Open. The
physical warm/cold viewport must match. Capture the cold scene before any Fit
and require the complete authored/native/view state both initially and after
ordinary scope activation. The retained mixed-panel failure is not a pass or a
generic allowance for viewport drift.

The fresh matrix produces three native downloads and two reconstruction JSON
observations per case: 18 native files, 12 observations and 25 original images.
Write screenshot intents before capture and independently inspect each original
at full resolution. Require actual-file content comparisons alongside visual
acceptance; a PNG or controller exit code alone is insufficient.

Passive network collection records request method/type, case/phase, UTC and
monotonic time, plus the frame URL or its explicit unavailability. Observer tasks
drain to a fixed point. Report readable byte matches, unavailable bodies and
typed optional preview cancellations separately. Unknown observations, non200
responses, byte mismatches, observer errors or unexplained failures hold the
run. Known HTTP200 worker-body `TargetClosedError` observations remain
unavailable, never captured matches. A typed nonfixture image cancellation is
pending independent exact-URL HTTPS/static-package review; it does not change
the generic classifier or prove that individual event's cause.

Successful collection ends `JOURNEYS_PASSED_NETWORK_AUDIT_PENDING`. Close the
owned/shared/frozen intervals, require full raw HTTPS parity with the Core pin
and actual installed package, run the actual-file and exact-URL HTTPS audits,
then obtain independent content/network and original-image reviews. Retain raw
failed attempts unchanged; write any bounded acceptance as a new joined record.
This workflow qualifies declared functional behavior, not performance or all
scientific PDF v1 requirements.

## Genuine mixed text/path corner resize

`scripts/check-isolated-selection-resize-browser.py` uses the genuine recovered
Figure 2 second Save and ordinary V Selection to select a native bar and whole
editable pathway label. Supply the frozen `--root`, `--expected-app-sha256`,
fresh `--output-dir`, desktop `--viewport` and `--theme`. Run through the shared
mutex, frozen source interval and owned process job below. The code is a private
selection candidate; it does not change the delivered beta21 archives or pin.

`--full` exercises an actual three-pixel off-centre common-corner grab, outward
movement, exact pointer-down return while held and release. It requires exact
native tree/source/artwork/history/clean-state restoration, plus the existing
250 ms/RGB 2/opaque/three-observation/80 ms paint predicate. Before measuring,
both selected owners must have original foreground and actual held-out negative
evidence. `require` raises after recording a failed admission; the inherited
collector alone does not stop input. Every recorded check must pass at the end.

The literal canonical action-paint observer remains unchanged. Its finite,
inverse-checked `scripts/resize-paint-observer-adapter.json` adds original
nonuniform RGB values for the same nine pixels of a 3×3 footprint. Keep every
uniform sample, include owner-tagged original glyph-stroke patterns, and obtain
independent PNG calibration proving an actual mismatch at an original foreground
pixel in the same footprint for each owner. Foreground somewhere and a background
mismatch elsewhere cannot qualify text paint. No renderer, Fit, Reset, grid or
selection action may rescue the held-return/released original captures.

The mutually exclusive `--functional-only` mode runs the same geometry, history,
completed resize and actual Save/fresh-process Open/second Save journey without
installing a timing observer. It labels the result timing-unqualified. The first
passive cold overview precedes later public zoom/Selection and a separately
named readable cold-detail capture. Keep those authorities distinct.

The six desktop/theme functional result is retained in `qa_artifacts/resize1`.
Its original wide-light 260.5 ms timing failure, missing sparse bar witness,
failed parent batch and initial completed-control visual HOLD remain unchanged.
The separate wide functional suffix cannot turn them into passes. Four completed
timed cases and two functional-only cases give functional desktop coverage; they
do not establish a complete timing matrix, general speedup or scientific PDF v1.
See [the bounded correction](../architecture/ISOLATED_COMMON_CORNER_RESIZE_2026_11_02.md)
for source and actual-file scope.

For the bounded interruption regression, use
`scripts/check-isolated-resize-interruption-browser.py` with the same frozen
runtime/source arguments and `--interruption pointercancel` or `--interruption
blur`, through the shared/frozen/owned wrappers. It reuses the ordinary resize
workflow, then interrupts a trusted mouse resize and requires exact native
pose/pixel/selection/clean-history restoration. Unrelated pointer cancellation
must leave the held resize intact; later move/up must not commit it. The next
resize must still support Undo/Redo and actual browser Save/fresh-process
Open/second Save. Capture the held and cancelled originals before full document
serialization or any rescue action.

Both boundary events are deliberately synthetic DOM events. The retained
headless-target activation control did not emit genuine window blur. Label this
scope explicitly; do not claim physical Windows focus-loss delivery, native-host
Save qualification or timing qualification. Preserve the initial product
failures and setup timeout in `qa_artifacts/resize2`, alongside closed source
intervals and independent file/image review. The existing wide timing HOLD and
fixed beta21 release identities remain unchanged.

## Runtime ownership and the scientific PDF controllers

Since 28 October 2026, wrap each bounded browser/native/build/large-PDF job in
Core's shared runtime wrapper so independent lanes cannot overlap heavy work:

```powershell
python -B C:\Users\ianme\Desktop\Projects\mersich_lab_superbench\core\scripts\qa\run-shared-runtime-job.py --owner figure-pdf --cwd C:\Users\ianme\Desktop\Projects\superbench_figure_tool --record C:\Users\ianme\Desktop\Projects\superbench_figure_tool\qa_artifacts\<task>\runtime-01.json --wait-seconds 600 --timeout-seconds <inner-deadline-plus-cleanup> -- python -B scripts/run-owned-browser-qa.py <existing arguments>
```

The physical lock is Core `qa_artifacts/shared-runtime/heavy.lock`; the adjacent
`owner.json` is diagnostic metadata. Never delete or expire them to acquire the
slot. Yield it after each bounded job. Freeze consumed source/controller files
separately and retain both supervisors' closure records. Source review and small
unit checks may run in parallel. See Core's `docs/runtime/BROWSER_QA.md` under
“Shared heavy-runtime ownership” for the tested wrapper contract.

For the PDF editing and repeated Open controllers, select the browser explicitly:

- `--browser-channel headless-shell` retains the historical default. On the
  declared desktop, Chromium 148.0.7778.96 uses software SwiftShader rendering.
- `--browser-channel chromium` selects Playwright's documented full Chromium
  new headless mode. The same-version inventory on 23 October 2026 uses Radeon
  780M through ANGLE/D3D11. This is still headless and does not open a desktop
  window. Record each run's actual graphics report; installed adapters alone
  do not establish the selected renderer.

Keep these runtime rows separate. A different renderer does not convert an
earlier failure into a pass, establish a causal speedup, or change acceptance
ceilings. The inventory is retained in
`qa_artifacts/t22/openperf1/headless-runtime-probe/`; recheck after runtime,
driver or machine changes.

The full scientific-PDF journey uses
`scripts/check-figure-pdf-editing-browser.py --fixture <original.pdf> --page 1
--viewport 1280x800 --theme light --browser-channel chromium
--continue-after-cold --output <fresh-qa-directory>` through the owned runner.
It exercises real editing, Save, a fresh Chromium process, continued editing,
a second Save and downloaded PDFs. Require content checks and independent
original-resolution visual review in addition to its structural assertions.

The separate `scripts/check-pdf-public-open-performance-browser.py` requires
the original fixture, accepted full-journey reference report, viewport, theme,
browser channel, load note and fresh output. It measures five isolated-context
cold Opens and ten same-context warm repetitions. Request routing disables HTTP
caching. The native Close action retires unused PDF resources. Keep both facts
in the result, preserve raw intervals/failures, and stop unchanged matrix cells
after the first failure. Its Open-action result does not qualify editing,
saved-file reopen, first preview, gestures, exports or memory.

Both controllers accept `--package-root <verified-extracted-package>` and
`--package-sha256 <semantic-digest>`. Package mode serves and verifies only that
payload, including all five runtime roots, and records its source revision
separately from the QA checkout. Repeat measurements retain five isolated
browser contexts, not five fresh browser processes. The reference report must
bind the unchanged original PDF/page and a completed, stable, non-diagnostic
functional journey. Its original performance HOLD remains visible and does not
waive any limit for the measured candidate.

Current V1 policy remains authoritative: three desktop viewports in both themes,
the existing cold/warm counts, ordinary readiness p95 at most 5 seconds, maximum
10 seconds, no main-thread task above 100 ms and no foreground gap above 250 ms.
A single full-journey run under the corpus's older 15-second completion ceiling
does not establish those repeated performance requirements. Keep Affinity
comparison work separate, and activate computer use only while using Affinity.

Pixel observers must retain their version with timing results. A full backing
buffer read can trigger Chromium's default Canvas readback fallback and can
itself dominate a measured interval. The display canvas now requests
`getContext('2d', { willReadFrequently: false })` before Fabric first obtains
that context. This avoids Chromium's automatic *undefined-option* fallback;
it does not guarantee hardware acceleration. Record the actual browser/GPU
inventory and keep any other fallback visible.

The action-paint observer's sparse atlas copies the same integer 3-by-3 probe
footprints at 1:1 scale and reads them together. RGB/alpha, coverage, geometry,
deadline and stability predicates remain unchanged. Final PNG encoding is
asynchronous, but its source bitmap is still captured at the original decision
point. Keep observer-only timing changes separate from product speedups. The
old/new exact contract controls and independent source receipt are retained in
`qa_artifacts/drag30/observer-contract-equivalence.json` and
`qa_artifacts/drag30/observer-source-review.json`.

The `drag30/retained*` runs explicitly inject screen-layer reuse with a constant
guard to isolate painting cost. They are controlled-fixture diagnostics, never
normal App activation or production invalidation acceptance. Their full backing
RGBA controls do not replace the unchanged intermediate/final paint witnesses
or actual-file review. Use the maintained genuine continuous controller for
automatic activation; passive lifecycle audits may explain whether the feature
was used, but cannot activate it or insert a readiness wait into that controller.

On this Windows Python3.12 runtime, `time.get_clock_info('monotonic')` reports
GetTickCount64 with a 15.625 ms resolution, while `perf_counter` uses QPC at
100 ns. This made the old absolute asyncio input schedule itself produce about
31 ms interval p95 even in a standalone control. The continuous controller now
uses absolute `perf_counter` deadlines and awaits `time.sleep` on a worker
thread, keeping protocol I/O free. It does not request a system timer-resolution
change, poll product state or add per-move browser inspection. Record the clock,
wait method, controller hash and raw issue/ack/browser-event times. Keep older
failed trials and distinguish this controller correction from product changes.
The original event count, duration, coordinates, classification, geometry/pixel
witnesses and all performance limits remain unchanged. See `drag30/` records
`input-cadence-calibration1.json` and `controller-cadence-contract1.json`, and
Python's [Windows platform notes](https://docs.python.org/3.12/library/asyncio-platforms.html#windows)
and [native sleep documentation](https://docs.python.org/3.12/library/time.html#time.sleep).

The complete point-release painter requires OffscreenCanvas. HTML-canvas batch
diagnostics had six or seven edge differences, despite an exact single-pass
control; the offscreen fixture control has whole-backing RGBA equality. Preserve
those raw failures and avoid attributing them to a particular GPU mechanism
without further evidence. Supported final paints accumulate original native
leaves on one bounded surface; history publication must await the complete
presentation or the ordinary fallback, including failure and owner retirement.
Do not omit that work from the measured journey.

For point-drag desktop coverage, use the maintained controller at 1280×800,
1440×1000 and 1920×1080 in both themes. `drag34/matrix-summary.json` binds the six
closed normal journeys; source review, targeted units, actual-file content and
full-resolution image review remain separately required. The consolidated
independent content/image result is `drag34/matrix-receipt.json`. A later documentation
update does not replace the executable-source bindings of those closed runs.

Frame-coverage classification distinguishes elapsed-time rounding from native
frame order. Only animation-frame rows may have equal rounded elapsed values,
and only with finite numeric native RAF timestamps that strictly increase.
Backward elapsed time and render/timer ties still fail. Keep the raw timestamps,
old failed reports and the narrow replay proof; this repair changes no input
action, observation window, paint/pixel/model condition or numeric budget.

Native RAF requests may coalesce. Require the original 120 trusted inputs and
at least 30 native paint witnesses, plus all original natural-pixel/coverage
checks. Retained-frame counts explain activation; do not add an auxiliary
requirement that every input produces a distinct frame. The accepted drag34
cells happened to retain all 120 paints with zero fallbacks.

User recordings can establish visible selection behavior without an active
computer-use session. Preserve the original, bind representative full-resolution
frames to timestamps and fixture bytes, and separate observed actions from
tooltip documentation or inferred keys. A 30 fps recording does not measure a
24 ms paint-spacing ceiling or reveal a private cache implementation. Keep live
native comparisons finite and reset computer use immediately after active use.

For the bounded Figure 2 object-marquee and mixed-body journey, use
`scripts/check-figure2-object-selection-browser.py --root <frozen-runtime>
--output-dir <fresh-output> --expected-app-sha256 <sha256> --viewport 1440x1000
--theme light` through the same owned/shared wrappers. Run the three declared
desktop viewports in both themes as separate jobs. The controller includes
actual Save, a fresh Chromium process, continued editing and a second Save;
strict content checks and independent original-resolution review are required.
Its trusted window-capture witnesses establish delivered geometry. This is
functional selection qualification and does not grant mixed-body latency or
broader v1 performance acceptance. See
`docs/architecture/PDF_OBJECT_SELECTION_2026_10_29.md` for scope and retained
failed controls.

For new native gestures, use Fabric's canonical `getScenePoint` conversion for
the product and trusted event witness. A separately reconstructed client-rect
conversion can differ at fractional desktop zoom, even when both appear correct
on screen. Preserve the failed raw inputs and geometry check; fix the coordinate
source without broadening its numeric threshold. The object-selection first
matrix and corrected `selection35/matrix2-*` jobs retain this distinction.

For complete source-label editing, use
`scripts/check-figure2-whole-label-browser.py --root <frozen-runtime>
--output-dir <fresh-output> --expected-app-sha256 <sha256>
--viewport 1440x1000 --theme light` through the same owned/shared wrappers.
Repeat at 1280x800, 1440x1000 and 1920x1080 in both themes. It types a complete
pathway label including spaces and beta, checks Undo/Redo, downloads two actual
Saves, reopens in fresh Chromium, continues editing and exports SVG/PDF. Require
strict actual-file checks and independent full-resolution control/export review.

Use `scripts/check-direct-selection-labels-browser.py` for the bounded
Direct Selection label/anchor journey, and
`scripts/check-direct-selection-label-interactions-browser.py` for modifier
clicks, arrow nudges and text-only movement. Both accept `--root`, `--output-dir`,
`--expected-app-sha256`, `--viewport` and `--theme` like the whole-label controller.
The full journey includes actual Save, fresh browser continuation and SVG/PDF
export. Require independent source/content and original-resolution visual
review, and retain failed controls. See
`docs/architecture/PDF_DIRECT_SELECTION_LABELS_2026_10_30.md` for scope. These
functional checks do not qualify mixed dragging performance.

The interaction controller also provides three finite selection modes:

- `--subset-marquee` checks ordinary mixed artwork and the retained genuine
  Figure 2 file: Shift removes/re-adds a precise anchor/whole-label subset,
  blank clicks clear it, and completed edits survive actual Save, new-process
  Open and continued editing. Labels stay editable text. The ordinary fixture's
  initial view uses public zoom controls and asserts complete artwork visibility
  before selection; do not rescue the view after a gesture.
- `--ordinary-subset` repeats only that ordinary case, for focused recapture or
  diagnosis without rerunning the PDF journey.
- `--real-assets` inserts eight actual Library assets spanning Styles 1 and 4,
  filled/stroked, open/closed and compound paths. It checks whole-owner targeting,
  overlap, scale/rotation/reflection, Shift click/marquee, constrained body drag,
  Escape, Undo/Redo, nested group entry/exit, child anchors, Layers agreement,
  native text/shape companions, two actual Saves and new-process continuation.
  Supply `--asset-root <read-only-catalog-runtime>` only when an App overlay is
  served with the existing `--url`; otherwise the catalog comes from `--root`.

Retain delivered pointer events and selection/artwork/history operands. Choose
asset targets from actual paint and painter order; a Library owner can contain
only layered strokes, and an overlapping higher owner may win a public click.
Both corners of a blank Shift marquee must also avoid the active selection's
body. Keep production snapping enabled and compare all selected leaves against
the observed common owner movement. Raw pointer displacement is not an exact
movement oracle when snapping applies. Require at least one scene unit of
actual owner translation: a positive direction dot product alone can accept
floating-point residue when a small drag snaps back to its origin. The finite
Groups/Layers case uses a 20×10 CSS-pixel body drag with production snapping;
point-gesture helpers express their input in scene coordinates instead.

For native Fabric marquee handling, `mouse:up:before` still exposes the selector;
`handleSelection` consumes it before ordinary `mouse:up`. Use native resolved
hits and the existing toggle policy. A temporary ActiveSelection is not a
document group, and its children need canonical Canvas serialization for saved
world poses. Escape qualification here covers ordinary translation without
linked dependents; it does not qualify linked connectors or scaling cancellation.

The asset mode alone uses the established six-decimal authored comparison and
ignores generated ID/name only on explicitly marked derived area-text frame
clips. Clip geometry/paint and authored identities remain compared. The binding
is restored on exit; the ordinary/PDF comparison stays strict. Preserve raw
differences and negative controls rather than extending this exception to
authored objects. Require independent actual-file and original-image reviews.

Use the same maintained interaction controller with `--group-layers` for the
combined Groups/Layers journey. Its default `--group-part both` opens the exact
retained eight-asset Save and genuine PDF Save; `assets` or `pdf` runs only that
portion for a bounded diagnosis. `--asset-fixture` and `--group-pdf-fixture`
accept relocated copies with the retained hashes. The controller validates
those bytes and the eight asset/style owners before interaction. It does not
recreate the Library cohort. Its asset-only comparator is restored before the
strict PDF portion and on exit.

This mode compares canvas/Inspector/Layers targeting, nested entry/exit,
whole-plot versus child selection, final-child Shift toggles, ancestor lock/hide,
blocked ArrowRight, Undo/unlock/show, eligible siblings, movement cancellation,
actual Undo/Redo, four actual Saves and fresh-process continued editing. Warm and
cold evidence names are distinct; complete model observations are addressed by
content hash to avoid duplicate copies. Require independent actual-file and all
original-image reviews before freezing a candidate. An intentionally hidden
sole PDF owner produces an empty canvas; its hidden Layers state, disabled child
targets and absence of editing feedback are the subject of that capture.

Use public View > Fit to Screen in both Simple and Advanced layouts. The shared
`focus_plot(keep_scope=True)` retains existing PDF isolation while framing its
panel; the default clears the prior editing scope. Released PDFs can enter
contents on their first unselected canvas click. Use their existing Layers
Select on canvas command for whole-plot selection, followed by supported public
Inspector/canvas entry. A deselected PDF child can leave Layers' finite row
window; find its actual native name with the public object finder. Scope row
action locators to that row's own actions, since a root row contains nested
branches. Read native JSON explicitly as UTF-8 on Windows. Retain the raw
controller/setup failures separately from product failures.

`scripts/check-direct-selection-label-lifecycle-browser.py` adds tool/group exit,
Delete/Undo, orphan prevention and Escape on a plain authored label. It records
native pre-marquee bounds for independent membership checks; raw text JSON
width/height alone cannot reproduce `PdfPositionedText` font-derived bounds.
Use the same desktop/theme matrix and source/owner closure rules. Keep lifecycle
qualification separate from the full Save/Open/export journey and timing limits.

For sustained mixed-object diagnosis, use
`scripts/check-figure2-mixed-drag-profile-browser.py` with those same arguments;
add `--profile` only for a separate instrumented CPU run. The 120 trusted inputs
retain the continuous controller's absolute QPC schedule over two seconds.
`scripts/mixed-object-drag-observer.js` registers its actual read-only paint
callback through the existing passive-observer API so observation does not
silently disable preparation. Record observer source with every result. This
controller is explicitly diagnostic and does not grant dragging latency/pixel
acceptance. Keep original failed profiles and unqualified renderer experiments
separate from the final label runtime. See
`docs/architecture/PDF_WHOLE_LABEL_EDITING_2026_10_29.md` for scope and findings.

The mixed-drag controller awaits each trusted mouse-move acknowledgement. Its
nominal two-second due-time schedule can stretch under serial protocol/paint
backpressure; report actual issue, acknowledgement and browser-event times
separately from artwork paint gaps. Do not interpret its accumulated schedule
lag as measured physical input-to-pixel latency. Before crediting a coalescing
change, prove that the transport preserves the declared trusted inputs and
that useful coalescing occurs. A pipelined trial with fewer observed inputs is
unqualified even if every dispatch task acknowledges. The contemporaneous
accepted/candidate/accepted result and rejected transport control are recorded
in [the scheduling trial](../architecture/PDF_MIXED_DRAG_SCHEDULING_2026_10_31.md).

The separate `scripts/check-figure2-mixed-input-delivery-browser.py` retains that
strict pointermove-count check while pipelining direct CDP acknowledgements from
a single QPC producer. Record its transport ledger, raw/coalesced observation,
native paint observation and explicit failed checks. Supplied timestamps identify
samples; they do not measure physical input latency. Analyze each coalesced/raw
stream separately and never add overlapping counts or substitute recovered
samples for 120 delivered pointermove events. The finite accepted-product
calibration and its interpretation are documented in
[mixed-object input delivery](../architecture/PDF_MIXED_INPUT_DELIVERY_2026_10_31.md).

The isolated-object prefix-reuse candidate is experimental history at
`experiment/pdf-object-screen-reuse-17a`; its diagnostics are absent from the
active cancellation-only delivery source. For that experimental candidate, keep the same serial
input and record whether the preview was naturally ready at down, its preparation
and admission time, native paint intervals, first delivered motion and complete
gesture/settlement cost. `getPdfObjectScreenPreviewForQa()` exposes disposable
preview diagnostics; historical issued bytes do not describe current memory.
Do not wait for readiness or use a callback interval as pixel latency. Retained
artwork is retired before ordinary final painting; all selected geometry remains
native and editable. See [the translation candidate](../architecture/PDF_OBJECT_TRANSLATION_SCREEN_REUSE_2026_10_31.md)
for the matched case, startup tradeoff and remaining qualification.

Revealed/intermediate pixel controls must open the same actual saved file in both
runtimes, preserve its IDs and source clocks, and associate each capture with the
correct delivered input and natural artwork callback. Compare complete decoded
RGBA bytes, including RGB when alpha is unchanged; an alpha-only difference
bounding box cannot establish image equality. Keep active-cache Escape and raw
return comparisons relative to each gesture's immediate pre-state. Fixture-only
selection APIs do not replace the separately qualified public selection journey.

For passive full-artwork snapshots, serialize the actual visible owner canvas
with its canonical `FabricObject.customProperties` list. Check source-field
identity and values on roots, descendants and clips before and after observation.
The project builder synchronizes provenance metadata; calling it is a state
change that can correctly invalidate prepared artwork. Keep actual Save/Open
coverage in the maintained full-file journey.

For cancellation probes, capture the genuine held artwork, then Escape alone
before pointer release, and finally after release. Require a fresh natural
artwork callback and exact decoded lower-canvas RGBA restoration without another
click, tool switch or forced paint. Preserve raw Canvas JSON; apply the native
saved-isolation normalization only to detached copies when comparing authoring
state across scope entry. Do not discard unrelated source fields or normalize
absent metadata into null. Choose an actually hittable painted path; scientific
PDFs can store bar fills and their visible outlines as separate native paths.
Retain setup failures separately from real gesture findings. See
[canceled gesture repainting](../architecture/PDF_CANCELLED_GESTURE_REPAINT_2026_10_31.md)
for the bounded control and remaining delivery qualification.

For native canvas clipboard and Figure/Slidedeck continuity, use
`scripts/check-canvas-clipboard-browser.py --root <frozen-runtime>
--output-dir <fresh-output> --viewport 1440x1000 --theme light` through the same
shared, frozen and owned wrappers. It controls an isolated headless Chromium
clipboard, not Affinity or the foreground desktop. Run the three desktop widths
in both themes as separate jobs. Source-pin the complete runtime, controller,
server and supervisors; keep each source interval and zero-survivor closure.

The controller covers fresh Library preferences, actual Ctrl+V and menu Paste,
normal input-field paste, internal-object identity, newer external text, SVG
paths/live text, PNG, inert HTML and actual browser clipboard-permission denial.
It moves the pasted objects with trusted keys, selects two existing Slidedecks,
switches views and downloads both a Figure and a combined project. Fresh Open
compares complete authored object arrays and deck fields; page `updatedAt` is a
capture clock and is explicitly excluded from deck equality. Retain raw before/
after JSON so independent review can inspect all differences. Wait for the
transient Open toast to disappear before the final screenshot; do not hide it
with injected CSS or change input/content/performance thresholds.

Library-dependent older controllers must explicitly open the named Library
toggle rather than assume the fresh Figure layout shows it. Existing saved
panel preferences remain authoritative. Independent original-resolution review
and actual-file comparisons remain required. These checks do not qualify native
Affinity/Illustrator OS clipboard transfer, installed Windows, or dragging speed.
See `docs/architecture/CANVAS_CLIPBOARD_AND_SLIDEDECK_2026_10_31.md` for support
and ownership boundaries.


## Precise path geometry

The public slim source carries the geometry controllers and their local helper
dependencies. Install `requirements-browser-qa.txt` for their Python imports;
use `python -m playwright install chromium` when running the actual journeys.
Source CI checks both controller help entry points without launching a browser.
Scientific fixture files remain separate explicit local inputs.

Use `scripts/geometry_qa/qualify.py` for the controlled nested evenodd compound
and `scripts/geometry_qa/source-cases.py --part library|pdf` for existing actual
native sources. Both accept `--root`, `--expected-app-sha256`, `--output-dir`,
`--viewport`, `--theme` and `--asset-fixture`. The source controller also accepts
`--pdf-fixture`. `--base-runtime` serves an unchanged frozen runtime with only
candidate App/styles overlaid. Keep the actual fixture files outside the public
source archive; pin their complete bytes in each local job plan.

Run through the shared, frozen and owned wrappers described above, one browser
job at a time, with fresh output and all imported controller/helper/fixture
files pinned. Retain the source interval, overlay-server closure and zero-owned-
process supervisor result. A finite controller deadline is an ownership bound;
a timeout is an incomplete whole case and requires a fresh run. It is not a
product latency measurement.

Choose coordinates from current native geometry and use trusted input. Read
`getViewportStateForQa().zoom` when computing a public wheel input; a computed
CSS matrix is rounded and can accumulate error. Continue measuring the actual
DOM band and chord independently. Preserve the 4/14 CSS-pixel admission rules,
endpoint/tangent priority, minimum/100%/maximum zoom and short straight/curved
edge controls. Public middle-button panning may frame the complete target
before observation; do not move artwork or use Fit to rescue cancellation.

For a deformed PDF leaf, choose a current painted interior point rather than
its former center or a numerically ambiguous boundary. A product paint helper
may choose setup coordinates, but the trusted click must still select the
original native ID. Do not call that setup an independent paint-hit oracle.
Keep independent native-coordinate/transform checks for grabbed material,
allowed operands, exact command types/arity, unedited contours and neighbors.

Require actual Save downloads, complete file/model comparisons, both distinct
native browser process IDs, first cold capture before navigation, continued
editing, completed Undo/Redo and a second Save. Retain the established strict
PDF and explicit Library comparison policies; do not add broad metadata or
clip exclusions. Independent full-resolution image and actual-content reviews
remain separate from structural checks. See the
[screen-scale geometry checkpoint](../architecture/PATH_SEGMENT_SCREEN_TARGETS_2026_11_05.md)
for the retained cases and qualification boundaries.
