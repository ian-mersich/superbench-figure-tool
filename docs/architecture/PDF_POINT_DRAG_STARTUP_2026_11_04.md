# Dense scientific selection: drag startup

The preserved Figure 2 file selects 19 native paths and 30 whole editable labels,
with 109 selected handles. On the released beta.23 baseline, every sampled
endpoint center reaches a path-handle button. None hits the selection frame or
count badge. The first drag also paints without a subsequent click. These
results do not reproduce a frame-interception defect for this view.

The same gesture does expose a startup delay. A separate CPU profile attributes
3.227 seconds to `beginPathNodeDrag`, chiefly repeated node-metadata and contour
reconstruction during snapshot and translation preparation. Profiling is
diagnostic; its durations are separate from the normal comparison below.

The correction reuses the existing synchronous metadata read scope during
`beginPathNodeDrag`. It restores the previous scope in `finally`, before the next
pointer event. Setup reads paths and metadata without changing them; later
gestures obtain fresh records. Target routing, point operands, whole-label
movement and painting requests are unchanged. No persistent cache is added.

One matched 1440 × 1000 light-theme comparison uses the same full Chromium
controller, saved scientific input and one trusted Ctrl-drag. Neither arm uses
another gesture, serialization or a forced render to rescue the first-held
paint.

| Observed interval | Released baseline | Candidate |
| --- | ---: | ---: |
| Captured pointer-down to next delivered move | 2,990.2 ms | 236.3 ms |
| Delivered move to natural artwork-render observation | 235.9 ms | 220.5 ms |

The first interval includes browser input delivery and protocol sequencing; the
separate profile establishes substantial baseline work inside the handler.
This is one observation per arm, not a distribution or a physical-input latency
claim. All four original image pairs—before/held, viewport/lower canvas—are
byte-identical. Independent full-resolution review accepts the first-gesture
response while retaining dense label and selection-outline crowding as a
composition HOLD.

Focused controls pass 86/86. They include a literal released-function negative
control, identical gesture geometry for 109 references, later in-place edits,
scope nesting and exception restoration. One genuine-file journey passes 57/57
checks covering cancellation, zero return, unchanged neighbors, Undo/Redo, actual
Save, fresh-process Open and continued editing with a second Save. Whole labels
remain text. Exact saved-file and original-image review records are retained
alongside the runs.

Evidence is under `qa_artifacts/selection-target-20261104/`. The candidate is
exactly the released runtime plus the drag-setup scope change; unrelated private
PDF experiments are excluded. Beta.23 remains the installed and public release.

The roadmap is unchanged. A follow-up profile of the corrected candidate places
212.7 ms inside `syncInspectorControls`, within a 264.5 ms drag-start handler.
Selection-context queries and native text-plane calculations dominate that
refresh. This diagnostic identifies the next target: reuse the existing
Inspector scheduling and selection context without delaying truthful selection
feedback. The normal first artwork interval remains about 220 ms. The 100 ms
main-thread limit, sustained dense dragging, broader selection coverage and
scientific PDF fidelity remain unaccepted.

## Inspector font sizes

The next correction measures a text object's native paint scale once while
reading its selected character sizes. Previously `sharedSelectionProperty`
revalidated the same native glyph plane for every non-newline character, though
the scale belongs to the object. Character-specific sizes still come from the
existing per-index reader. The scale is evaluated lazily on the first eligible
character and discarded when the synchronous object read returns. There is no
global cache or change to Inspector scheduling.

A new matched pair isolates this change against accepted commit `716de2cf`:

| Observed interval | Metadata-scope fix | Inspector correction |
| --- | ---: | ---: |
| Captured pointer-down to next delivered move | 276.8 ms | 134.8 ms |
| Delivered move to natural artwork-render observation | 206.8 ms | 216.9 ms |

This pair supports an incremental drag-start improvement. It establishes no
paint-speed gain or statistical regression. The earlier comparison with
released beta.23 remains separate. Each arm uses the same trusted gesture and
no later action or forced paint to complete its first-held view.

All four original image pairs are byte-identical, and complete artwork matches
under the unchanged isolation-only comparison. Inspector records before and
during the held gesture are identical across arms: selection summary, anchor
context, mixed font-size state, numeric geometry and visible property controls.
The Inspector remains correct during the same gesture.

Targeted controls pass 31/31, including the literal previous implementation,
selected ranges, Unicode, mixed/partial selections, newline-only and empty text,
invalid-scale fallbacks, later in-place changes and exception order. The same
genuine-file history, Save and fresh-process continuation passes 57/57. Evidence
is under `qa_artifacts/selection-inspector-20261104/`. Both corrections remain
private pending integration; beta.23 and the broader roadmap are unchanged.

## First-move rendering diagnosis

One subsequent diagnostic uses committed `0384c881`, the same scientific file
and the same trusted held gesture. CPU profiling and a Chrome trace begin after
pointer-down. Input, canvas-render callbacks, animation frames, long tasks and
the protocol issue/acknowledgment times are recorded separately.

The marked move reaches the after-artwork callback in 231.7 ms: 46.6 ms precedes
the before-artwork callback, followed by 185.2 ms inside that canvas render.
The App records 185.4 ms for its full render; Chrome records a 46.4 ms pointer
dispatch and one 243 ms long task. These instrumented values do not replace the
normal observations above.

Deduplicated CPU samples place 117.6 ms under native text drawing, including
45.3 ms under native-plane validation. Stock path stroke/save work accounts for
another sampled branch of 42.5 ms. These inclusive branches overlap and must
not be added as elapsed time. The 19-path/30-label selection is ineligible for
the existing single-path preview and uses the ordinary full canvas painter.
There is no full Inspector refresh in the measured dominant branch.

Canvas completion is not physical presentation. GPU work overlaps the marked
interval and continues after the canvas callback. The trace does not identify
the changed frame's scanout time. Actual lower-buffer and viewport captures
are nevertheless correct without a later gesture or forced artwork render;
all four images are byte-identical to the accepted normal candidate captures.
PNG encoding occurs after the measured trace.

Each `_renderChars` call already obtains a validated native plane and reuses it
for the glyphs it paints. `_pdfWithCurrentPlane` saves,
transforms, paints and restores; it does not repeat plane validation. This
diagnostic therefore makes no renderer patch or validation-cache change.
The next proposal should target the measured native text/full-render work with
explicit lifetime, mutation and pixel-fidelity checks. The unrelated local
dimension-query duplicate was not changed because it is outside the dominant
measured branch. Evidence is under `qa_artifacts/selection-paint-20261104/`.
The two accepted responsiveness fixes and the broader roadmap are unchanged.

## Repaint proposals that were not adopted

Two isolated prototypes used the accepted Inspector correction and the same
49-object scientific gesture. Neither changed the product default.

Fabric object caching was ruled out during source review: native PDF text and
its parent groups require the uncached transform route, and the stock dirty
properties do not cover the native planes and font resources. The first
prototype instead shared only adjacent, identical glyph transform chains,
retaining a separate state boundary for each glyph. The second skipped only a
proved empty stroke glyph pass after unchanged native-plane validation; stock
outer path, dash, shadow, clip and save/restore handling remained intact.

| Normal matched observation | Canvas paint, baseline → candidate | Protocol issue → acknowledgment, baseline → candidate |
| --- | ---: | ---: |
| Adjacent transform reuse | 176.6 → 144.7 ms | 241.7 → 273.5 ms |
| Guarded transform reuse repeat | 187.9 → 182.0 ms | 256.3 → 319.3 ms |
| Empty stroke glyph skip | 184.3 → 185.2 ms | 248.9 → 249.0 ms |

The first paint gain did not repeat at similar size, and its protocol interval
worsened twice. The empty-stroke candidate removed the intended traversal for
all 100 native labels but showed no useful paint gain. These small samples do
not establish statistical regressions. They do not support adopting either
implementation. Host protocol and browser canvas intervals remain separate;
no physical presentation or causal clock subtraction is claimed. A proposed
matched diagnostic trace was cancelled before acquiring a lease.

Independent original-image reviews found no introduced glyph, baseline or
clipping changes. Both genuine-file continuations passed their maintained 57
checks, including two actual Saves and fresh-process Open. The batching trial's
targeted cross-run model comparison retains its exactness HOLD: 627 generated
edit-provenance field differences across 19 path objects were preserved, with
no broader comparator normalization. Before/held artwork and Inspector values
matched. A common edited-file witness was deferred for the unadopted route.

The empty-stroke negative controls used detached clones of a real native label,
because text stroke is not exposed by the current Inspector. Three outlined
characters produced visible colored ink absent from the zero-width reference,
with 965 differing pixels. All ten matched image pairs were byte-identical.
These images support the declared renderer comparison. A direct painter/font
resource diagnostic snapshot was not recorded.

The prototypes and raw failures remain under
`qa_artifacts/selection-batching-20261104/` and
`qa_artifacts/selection-stroke-20261104/`. The two accepted startup fixes remain
intact. The next source assessment is whether existing ordered screen reuse
can retain unchanged content during mixed dragging; an invalid whole frame
must not be reused. Sustained dragging remains unaccepted; the roadmap remains
unchanged.
