# Scientific PDF and Slides V1 acceptance status

## Current status — 5 November 2026

Figure beta.25 is the synchronized desktop/web delivery. The runtime and support
source are `f718d3dc`; the documentation-only source revision is `b744782b`.
The local package `355d0f0a` contains 1,723 files. Public source commit
`dcd16ee9` and website commit `87df773e` passed exact-head source CI and Pages
deployment. The Core pin, active package, installed beta.25 and persistent trust
agree; beta.24 remains available for rollback. The existing beta.5 host is
unchanged.

Scoped qualification passes 900 checks across six Groups/Layers cases, 155
Library checks and seven read-only beta.24 reader checks: 1,062 total, with 26
actual Saves and 133 reviewed originals. A fresh public case adds 150 checks,
four actual Saves and 20 independently reviewed originals. The earlier public
failure and initial visual-review HOLD remain failures; the corrected whole
retry and visual review pass. Two worker bodies remain unavailable and are not
counted as body matches. Installed and portable 60-second whole-workflow checks
pass as functional qualification; the latest beta.25 installed 45-second
startup miss remains a failure.

Scientific PDF V1, complete Illustrator/Affinity selection parity, fidelity,
performance and whole-project coverage remain open. The 100 ms blocking limit,
dense selection-outline crowding and retained Figure 2 Canvas appearance
failure (3.358% against the fixed 2.5% limit) remain open. Smoother sustained
dragging is deferred. A local precise-geometry correction now addresses
reproduced short-edge admission, overlapping segment targets and PDF control
obstruction. It preserves native path editing and editable text. Functional
qualification passes 2,132 browser checks across six desktop/theme compound
cases, an actual Library compound and the retained Figure 2 PDF, with 16 actual
Saves and fresh-process continued editing. Independent review accepts all 144
original screenshots and 16 actual saved files; source and private-preservation
reviews also pass. This is a local source checkpoint and beta.25 remains
delivered. See the [geometry checkpoint](PATH_SEGMENT_SCREEN_TARGETS_2026_11_05.md)
and [active implementation plan](SELECTION_PDF_RESUMPTION_2026_10_22.md).

The beta.25 delivery advances the existing roadmap without changing its scope
or milestones. The full V1 acceptance contract still requires broader editing,
scientific-corpus fidelity and export/reimport qualification.

## Historical beta.24 status before beta.25 delivery — 5 November 2026

This section preserves beta.24 qualification and startup/latency observations as they stood before beta.25 delivery. Its claims and verdicts are historical and do not describe the current release.
Figure beta.24 is the synchronized desktop/web delivery. See the
[beta.24 release](https://github.com/ian-mersich/superbench-figure-tool/releases/tag/v1.0.0-beta.24)
and the [current Core Figure pin](https://github.com/ian-mersich/superbench/blob/main/config/figure-release.json).
The two accepted [drag-startup corrections](PDF_POINT_DRAG_STARTUP_2026_11_04.md)
are delivered in beta.24. The first reduces one observed 49-object
pointer-down-to-next-move interval from 2.99 seconds to 0.24 seconds while
preserving the first-held artwork. The Inspector correction reduces a separate
matched interval from 277 ms to 135 ms against that first fix, with identical
Inspector values and artwork. These bounded observations establish neither
sustained-drag acceptance nor repeatable latency across documents.

Qualification passes 79 package checks and 72 fresh live HTTPS checks, including
whole editable Unicode text, font changes, Undo/Redo, two actual Saves,
fresh-process Open and continued dragging. Independent saved-content and
original-resolution visual reviews pass. All 1,723 deployed files match the
qualified package; the Core pin, installed selection and persistent trust agree.
The existing beta.5 host is unchanged. Installed startup passes the 45-second
bound and portable startup passes the 60-second bound; the earlier portable
45-second miss remains recorded. Beta.23 is retained for rollback.

Scientific PDF V1 and sustained dense dragging remain unaccepted. The 100 ms
blocking limit, dense selection-outline crowding and the retained Figure 2
Canvas appearance failure (3.358% versus the fixed 2.5% limit) remain open.
The [Selection and editable-PDF parity contract](SELECTION_AND_PDF_PARITY_2026_10_21.md)
still requires broader object, group and node behavior, scientific-corpus
editing/fidelity, and export/reimport qualification. Whole labels remain text;
the delivered checks do not establish full Illustrator/Affinity parity.

Remaining first-move work is concentrated in ordinary native text rendering.
The transform-reuse and empty-stroke trials produced no repeatable, useful
repaint improvement and were not adopted. Earlier ordered static/live reuse
also failed exact pixel admission and activated no retained frames. Those
findings close the existing reuse assessment; the next rendering change needs
a separate bounded proposal. Ian's current priority is Selection/Direct
Selection reliability and readable feedback, then Groups/Layers consistency,
then precise geometry editing. Smoother sustained dragging is deferred; see
the [active implementation plan](SELECTION_PDF_RESUMPTION_2026_10_22.md).

Root has accepted the six-fix selection checkpoint as bounded source work.
The following Groups/Layers candidate adds ancestor-aware selection, consistent
final-child toggles and restored native-control readiness. Its 171 targeted tests
and 146 retained-asset/PDF browser checks pass, with a focused 68-check asset
rerun after strengthening the movement assertion; the active plan records the
actual-file and original-image review scope. The combined candidate is being
frozen for delivery review. It has not changed beta.24 or completed Scientific
PDF V1 acceptance.

The checkpoints below preserve their original dates and acceptance scope.
Their delivery versions describe those historical checkpoints, not the current
shared release.

## Historical checkpoint — beta.16 delivered; implementation resumed 22 October 2026

The actual LF beta.16 package passes 532 checks: 270 ordinary point/curve,
192 genuine Figure 2 and 33 selection checks (495 normal), plus 37 separate
post-Store.collect failure/recovery checks. The fault run does not qualify normal
timing. Independent runtime visual review accepts the declared captures; the
consolidated saved-file/PDF-content audit passes 161 checks. Combined native
qualification passes 186 checks across six width/theme cases and 12 fresh hosts,
with 24 independently accepted original captures. Core browser qualification
passes 119 checks across six cases, also with 24 independently accepted originals.

The first native attempt remains a retained failure: its 45-second auto-close
could precede the unchanged 60-second inspection budget. One reviewed CLI-only
amendment uses 60-second auto-close for the fresh complete run; all 12 inspection
budgets are nonnegative. No product code, 250 ms paint criterion, content check
or performance threshold was changed by this lifecycle correction.

Immutable source `d170100675e2ed96dffccc2fd6ae3cd207a8c484` / package
`ceec84e7e18bd0945a99874817b9ff59f444ffa001eb87fa49b6a8c6587ce54d` binds the delivered 1,584-file package;
public source `5a0627773b4cb93196300dd2bca6a654b956fc27` and website
`29ab77f6b34a3d8f2874aa539dffb312b914118e` select the same reviewed payload.

**Beta.16 is published, deployed and installed**, with beta.15 retained for
rollback. All 1,584 raw HTTPS payload files match the actual installed package;
the Core pin, active selection and trust record agree. Actual HTTPS qualification
and independent live review pass; see the paired publication checkpoint for scope.

Actual Affinity 3.3.1 evidence for the unchanged 1,592,921-byte Figure 2 and one
red marker supports only the declared node gesture. It does not establish overall
parity, typography equality or a speedup. The 3.358% Canvas difference still fails
the fixed 2.5% limit; general selection, dense interaction, corpus and fidelity
acceptance remain open. Full scientific PDF v1 is not accepted.

The user has reviewed the joint project summary and explicitly resumed Figure
implementation on 22 October: close the remaining Selection/Direct Selection
gaps and correct the genuine Figure 2 typography failure, using the fastest
credible reuse-first route and unattended QA. The [resumed work record](SELECTION_PDF_RESUMPTION_2026_10_22.md)
distinguishes demonstrated failures from missing public-gesture coverage.
Beta.16 stays selected until a reviewed canonical candidate passes combined
qualification; Core and website/installed delivery remain coordinated.
The reuse-first roadmap and all scientific PDF v1 requirements are unchanged.

Dated sections below preserve earlier plans and evidence. They do not authorize
new work or replace this checkpoint's delivery status. See the
[paired release checkpoint](../PUBLIC_PUBLICATION.md#beta16--point-and-curve-continuity).

## Earlier direction and beta.14/beta.15 checkpoints — 21 October 2026

Ian confirmed two release-blocking requirements: Illustrator/Affinity Selection
and Direct Selection behavior, and fully editable imported scientific PDF objects.
Neither is qualified. Use the [current parity and delivery contract](SELECTION_AND_PDF_PARITY_2026_10_21.md).
Choose the fastest credible integrated route, including replacement of custom
interaction/import internals. Judge visible behavior, saved compatibility and
maintenance; preserving existing record layouts or retiring whole named functions
is not an adoption gate.

The isolated Fabric controls pilot and VectorCraft comparison are complete, with
retain decisions for those tested routes. They do not exhaust broader reuse.
The next work is actual interaction ownership and editable-PDF behavior, not a
repeat of those pilots. The evidence below keeps its historical scope.

The first [implemented interaction slice](SELECTION_BODY_INTERACTION_2026_10_21.md)
is committed as `001c4e6740821e31950beefebfdf8c5d81038c9e`. Native Fabric body
dragging, Shift marquee removal, short-path deletion, grouped Escape cancellation
and saved-content continuity pass the bounded browser checks and independent
review. It was delivered in the paired beta.14 release: exact-package native
qualification passes 186 checks across six cases and 12 fresh hosts, the packaged
interaction journey passes 33 checks, and actual HTTPS qualification passes 702
checks across the public root and six width/theme cases. All 1,583 website runtime
files match the installed package. Independent native visual review accepts all
24 originals; independent live review accepts all 25 originals and replays 18
retained authored-payload comparisons. See the publication checkpoint.
Broader selection parity, the scientific PDF corpus, fidelity and performance
remain open.

Beta.15 was published, deployed and selected at that earlier checkpoint, with
beta.14 retained for rollback; see its [historical publication checkpoint](../PUBLIC_PUBLICATION.md#beta15--explicit-pdf-image-settings-and-shared-delivery-21-october-2026).
Its actual LF payload retains this selection slice and passes the 33-check
interaction regression. All 1,583 served files match the actual installed
package. Neither complete v1 requirement is accepted.

The next genuine-PDF case uses the recovered original Figure 2, verified against
its retained source hash. One bounded packaged baseline opened in 5.070 seconds
with a maximum observed event-loop gap of 212.9 ms, within its unchanged budgets.
Its Canvas appearance still fails the declared significant-difference threshold
(3.358% versus 2.5%). The Figure chat is addressing that measured typography
paint gap. Browser font-size normalization changed no pixels and was reverted;
detached bundled PDF.js glyph/image paint diagnostics also failed the unchanged
appearance limit and were not promoted. This single baseline establishes neither
a repeatable speedup nor general corpus acceptance. The full genuine-page
editing, Save/cold Open and export journey remains required after a correction.

A separate [explicit image-interpolation correction](PDF_IMAGE_INTERPOLATION_2026_10_21.md)
now preserves decoded Boolean settings across ordinary editable Open, actual Save
and fresh-process Open. Its contrastive control passes 48/50 public checks and
53 focused controls, with exact edited/cold scenes and pixels. The two remaining
failures at that checkpoint were the existing explicit-true PDF-export loss.
A follow-on [writer correction](PDF_IMAGE_INTERPOLATION_EXPORT_2026_10_21.md)
passes 50/50 public checks with repeated opposing image settings, soft alpha and
a polygon-clipped image; its unedited PDF matches the independent render exactly.
It passes 130 targeted and 11 vendor-source controls. An actual canvas-to-slide
test then finds and corrects loss of the same explicit settings in the existing
SVG snapshot reviver. The shared Boolean-only helper passes 131 targeted controls,
50/50 ordinary Figure checks and 21/21 public slide checks, including actual Save,
fresh-process Open and both slide PDF downloads. Independent source, actual-file,
PDF and original-resolution visual reviews bind the supplement. The copied slide
retains the existing SVG/PNG snapshot semantics, not original-PDF editing authority.
At the earlier writer checkpoint, all seven retained Figure 2 absent-hint
captures remained byte-identical to beta.14. The predeclared matched Open pair
on `202966f2` passed the unchanged timing budgets in both arms and retained the
same Canvas failure. It does not erase the separate 286 ms Open gap against
250 ms or establish a speedup on the later source.

The explicit image corrections shipped in paired beta.15 from immutable source
`1a20663eacd6e2ab9059bad1b2d57094dfeda2e0`. The actual LF payload passes separate
50-check Figure/image, 22-check slide and 33-check selection journeys. Native
qualification passes 186 checks across six cases and 12 hosts; Core browser
qualification passes 119 checks across six cases. Their independent reviews each
accept 24 originals. Live HTTPS passes 702 checks with 25 independently accepted
originals and 18 retained saved-content comparisons. The copied-slide run covers
transfer, entry into the editor, PDF exports and Save/cold Open, without a new
post-copy content mutation. Original PDF authority remains in the source Figure.
The compatible host was unchanged and beta.14 was then available for rollback.

These results deliver the bounded image fixes, not general PDF fidelity,
Selection/Direct Selection parity or performance acceptance. A subsequent
[anchor and curve continuity slice](POINT_AND_CURVE_CONTINUITY_2026_10_21.md)
adds actual Affinity Figure 2 references and improves native point movement,
nested group entry, natural painting and cooperative PDF history recovery.
Its source qualification and saved continuation remain separate from release
delivery. Affinity rewrites fonts and some text positioning; that comparison
does not waive the retained Canvas typography failure. Broader selection and
Figure 2 typography remained open at that checkpoint. The joint-summary hold
was subsequently lifted on 22 October as recorded above. The roadmap and full
V1 scope remain unchanged.

## Historical checkpoint — 19 October 2026

19 October 2026. **Implementation resumed explicitly by the user. V1 and PDF
release qualification remain open.** The Figure chat owns the isolated Fabric
controls pilot, followed by the PDF importer comparison. The coordinator owns
review and qualification of the earlier source for matched desktop/web delivery.
A completed component or browser journey is a checkpoint, not completion of
this workstream. See the [pre-plan integration record](FIGURE_PREPLAN_SYNC_2026_10_19.md).

The source owner is `C:\Users\ianme\Desktop\Projects\superbench_figure_tool`.
Superbench Core and the website consume a committed, qualified Figure payload;
they must not acquire separate editor implementations. A separate, qualified
Library update has delivered beta.12, source
`649b413ba392c0220d8405327a9fe9ba11dd7ff8`. Core's
`config/figure-release.json` selects that asset release. It does not include the
unfinished PDF work recorded here. Local PDF checkpoints do not change that
selection.

## Resumption order: reuse before new custom implementation, 19 October 2026

**Historical sequence, superseded by the 21 October parity contract above. The
two named investigations are complete; they are not the next tasks.**

This approved decision changed the development priorities on 19 October. The user had
explicitly resumed implementation with unattended QA. Do the
ordinary-path Fabric controls pilot first, then the PDF importer comparison below.
This supersedes Lock-selector-first and further custom capture/copy optimization
as the leading development tasks. Historical “next” statements and the immutable
`qa_artifacts/curve19/paused-checkpoint.json` retain their original context; use
the 21 October contract for the current order. The retained Lock harness correction, final
connector matrix, SVG/PPTX destination review, native Save/Open/real-picker checks,
PDF V1 requirements, performance/memory HOLDs and matched release gates remain
required. The sequence changes; milestone scope and acceptance budgets do not.
The earlier documentation-only update did not authorize execution. The later
explicit resumption authorizes the pilot/comparison and coordinated pre-plan
integration; promotion still depends on the applicable candidate checks.

### 1. Bounded ordinary-path Fabric controls pilot

Fabric 7.3.1 is already pinned in `package.json` and `vendor/manifest.json`; the
bundled module contains `controlsUtils.createPathControls`, with no current App
callers found in the local source inventory. API availability is a reason to
investigate reuse, not evidence that it meets Figure's editing requirements.
Keep the pilot on ordinary native paths. Do not automatically replace Smart
connector semantics, dense-PDF source editing or the whole point-editing system.

Use a small adapter between Fabric's controls and the existing edit transaction,
commit/cancel and history boundaries. Fabric may supply pointer controls; the
current Figure document, scene and transaction/history system remain authoritative.
Preserve multi-node selection/editing, keyboard movement, Escape/pointer cancel,
source/object IDs and metadata, native path commands and transforms, grouped or
reflected/skewed geometry, atomic Undo/Redo, actual Save and fresh-process Open,
and immediate natural painting. Preserve unaffected nodes and neighboring artwork.
Use the existing paint deadline/stability rules without a corrective Fit or render
inside observation. Check handle placement against native geometry.

Reuse the matching upstream regression cases where useful, supplementing them
with Figure's existing source-ID, multi-node, transform, transaction, keyboard,
Save/cold and paint controls. Record the precise upstream revision and relevant
license/notice obligations. Accept reuse only after the bounded public editing
journey and targeted controls preserve the existing behavior. The decision must
name the exact custom control/adapter code that can be retired, retained or
simplified and why. If an essential behavior is missing, record the gap and retain
the current implementation; do not leave a second scene or history authority.

### 2. Same-corpus PDF importer comparison

Compare one frozen current integrated importer against VectorCraft or another
selected, proven upstream importer at a recorded release/commit. Selection and
suitability remain open; upstream claims, demos and marketing are not measurements
of Figure's performance. Retain `qa_artifacts/op19/e/` and the paused source as
historical references, and bind the actual comparison to its own exact source.
Use the same retained genuine PDFs, pages and named edit targets for both arms;
keep original bytes untouched. Follow the existing corpus and Affinity reference
protocols. Synthetic fixtures can isolate regressions but do not replace the corpus.

Compare the following before making an adoption decision:

| Requirement | Evidence needed for both importers |
| --- | --- |
| Source fidelity and useful editability | Native path geometry, editable text and fonts/glyph placement, clips/masks, images, transparency and nested transforms; named edits and unaffected neighbors compared with the same source/reference. An opaque picture or outlined text cannot substitute for a required editable object. |
| Continued authoring | Editing, grouping/isolation, Undo/Redo, actual Save, fresh-process Open, continued editing, PDF/SVG/PNG export and supported reimport. Preserve source IDs/associations and declared native semantics through any adapter. |
| Measured cost | The same end-to-end public Open/edit/Save/cold/export tasks, hardware and quiet-window policy, fixed budgets, repeated cold/warm observations, failures, long tasks and peak/retained memory. Include copying, conversion and transfer, rather than reporting an upstream parser kernel alone. |
| Integration and ongoing cost | Bridge/WASM setup and transfer, workers and WASM/native/browser memory, browser plus Windows packaging/runtime support, fonts/assets, maintenance/update burden, upstream regression coverage and licenses/notices for code and dependencies. |

Prefer a maintained module, its upstream regression tests and small adapters over
new custom importer infrastructure. Route imported data into the existing native
Figure scene and transaction/history model; avoid a parallel scene graph or
history engine. Record unsupported constructs and per-case failures explicitly.
A faster subset does not close required fidelity, editability or V1 cases.

The comparison deliverable is a bounded reuse/adapt/retain decision with actual
source-bound results, integration costs, supported scope and an exact inventory
of custom code/tests that can be retired or must remain. Only after that decision
should further custom performance work be prioritized. The existing repeated
JSON/capture/copy findings remain evidence and a fallback backlog, not the default
next implementation. No adoption, dependency change or code retirement happens
as part of this planning turn.

## Requirements and evidence

The governing requirements are Core's
`docs/architecture/FIGURE_PDF_V1_ACCEPTANCE.md`,
`FIGURE_PDF_QUALIFICATION_CORPUS.md`, and
`FIGURE_PDF_DENSE_AND_KNOCKOUT_PLAN.md`, under
`C:\Users\ianme\Desktop\Projects\mersich_lab_superbench\core`.
Their October 7/8 baseline and pause entries are historical. The current user
pause remains in effect. Preserve their acceptance thresholds and source/reference
requirements; the resumption order above changes no acceptance gate.
Figure/Slides behavior is described in [Figure and Slides](FIGURE_AND_SLIDES_PROJECT.md).

On 17 October the user selected **Affinity instead of Illustrator** as the external
comparison application. Use the [Affinity comparison protocol](AFFINITY_PDF_COMPARISON.md)
for this task; historical Illustrator requirements below refer to the earlier plan.
This changes the comparator, without changing the corpus or performance budgets.

| Area | Current evidence | Remaining V1 acceptance |
| --- | --- | --- |
| Ordinary scientific vector/text editing | Genuine ggplot/native keyboard and geometry journeys have source-bound functional results. Current-source Prism child targeting is corrected; the bounded native marker/Undo/Redo/Save/fresh-Open journey passes 24 producer checks, 85 independent file/source checks and 14 independently reviewed originals. | Broader marquee/group/isolation, typing, Layers, exports, host/theme coverage and final committed-source qualification remain open. |
| Natural action-to-paint | The current local candidate passes 24 desktop/theme/family cases and 156 actions after correcting stale numeric/compound painting, native typing-input placement and repeated Library suggestion work. The maintained command passes 69 JavaScript and 38 Python checks; the full Library discovery web workflow passes 238 checks. | These are finite repaint cases. Required repeated authoring/performance measurements, broader corpus/native geometry and matched release qualification remain open. |
| Public ordinary PDF export | A genuine R plot passes 50 public browser checks, 33 independent complete-file checks and 17 original visual reviews after correcting standard Helvetica minus export; 35 targeted source controls pass. All 11 minus regions match the source in both actual PDF downloads, and actual Save/full warm/full cold scenes are literally equal. | This closes the declared minus defect and recorder corrections. Continued cold editing/second Save, SVG/PNG/reimport, failure guards, broader corpus and final source qualification remain open. The later PDF-check correction is recorded separately below. |
| Opaque rectangle display | The genuine clipped heatmap passes 50 public checks, 48 independent complete-file checks and review of all 17 originals after its cell seams and color-scale stripes are corrected. Its actual Save/full warm/full cold scenes match literally; canonical geometry and source bytes remain intact. | New imported eligible rectangles only. Historical project migration, effects/complex transforms, continued cold edits, other formats, performance and full V1 remain separate. |
| Browser workspace saving after PDF edits | A captured worker error identified a canonical PDF edit label rejected as runtime history. The bounded correction passes 115 targeted controls and 13 independent controls. Fresh public R/Prism runs retain complete actual saved scenes and show Saved at all recorded host snapshots. | Per-edit transient acknowledgement, durable browser-store recovery and continued cold edits remain separate. Prism's two existing appearance failures remain. |
| PDF checks and export feedback | Actual retained labels now determine whether imported text can be checked. Rounded small-text warnings remain truthful, long font names wrap, warning badges stay whole and export results remain visible beside footer actions. The exact candidate passes 86 targeted controls, 15 independent preflight controls and fresh Adobe/drug-targets original-image reviews. Drug-targets passes 50 public and 62 independent file checks. | Adobe retains its Canvas fidelity failure; the selected drug-targets bar still has a Clip/title overlay collision. Host close status remains pending. Other corpus, width/theme and export-failure cases remain separate. |
| Continued Adobe text editing and second Save | The actual first Save opens, accepts `Z-score β [c]`, passes complete-scene Undo/Redo and downloads a second Save. That file opens in another fresh process and exports a real PDF with the complete live scene and artwork pixels unchanged. The staged runs pass 39 and 5 checks, independent file audits pass 35 and 25, and all fourteen originals receive independent visual review. | This closes three bounded materializer defects. The original full-journey deadline, Adobe Canvas/JPEG appearance, event-loop finding, repeated performance, other formats/reimport and full V1 remain open. |
| Adobe public SVG/PNG/PDF downloads | A fresh three-format run passes 21 checks, 31 independent file checks and review of all seventeen originals. SVG now reports 343 actual Canvas paths, preserving its other content; PNG is byte-identical to the live artwork, and PDF geometry/streams match the prior actual export. The complete live scene and artwork remain unchanged after each download. | Edited second-Save case only. Exported-PDF reimport/recoverable editing, other corpus/scopes, repeated costs and full V1 remain open. SVG retains three system-Arial spans; PNG has no observed embedded density tag. Existing Adobe source-appearance findings remain. |
| Adobe exported-PDF reimport | An isolated, unpromoted candidate now opens the exact downloaded PDF as 344 editable paths, 960 text objects and six images, with zero opaque pages. Trial 7 retains the complete live project and exact new source bytes; all 960 text geometry/font observations validate. | **HOLD.** A PDFium reading-order assumption prevents one label from matching, while source appearance also fails: thin dendrogram connections disappear in the raster and Venn edges become jagged. Browser saving reports failure. Open takes 29.13 s, with a 1,480.9 ms event-loop gap and a 1,298 ms main-thread task. Actual Save/cold editing, general group operations, broader corpus and release qualification remain open. |
| Affinity comparison | Native Affinity 3.3.1.4940 has an actual unchanged and corrected edited Prism PDF pair, separate native saves, text/group history and native close/reopen. The corrected export passes 21 independent checks; all 13 marker points are literally restored, with other paths and neighboring labels unchanged. All 22 native UI originals were independently reviewed. | The earlier 0.24 pt marker-shift HOLD remains preserved. Pointer node dragging is unqualified. Page rounding, font/glyph placement, separate paint operands and raster-size differences remain measured; native `.af` structure is opaque. Broader comparator cases remain open. |
| Dense original-source editing | Complete heatmap source/leaf identities, live text, native point edits, history and cold continuation have bounded results. | Initial point entry remains above its 1 s maximum; full opening, gesture, input, export and memory budgets remain unqualified. |
| Local Slides Duplicate | Active/inactive source, independent owners, placement, Undo/Redo, Save and cold continuation pass the declared three-slide journey. | Do not extend this to creation, Figure handoff or inherited/master artwork. |
| Edit a copy in Figure | Frozen `d59d6687` passes the declared local Group(Page, Rect) warm and fresh-browser continuation: 160 checks, two actual Saves, 11 independently reviewed original captures, unchanged source slides and zero retained owners/views after both public Closes. | Open source Figure, broader scenes, creation, final combined-source rebind and performance qualification remain separate. |
| Native Figure to Slides | Declared existing-deck Add/Create and fresh-process source-editing journeys pass 134 producer predicates, 530 independent complete-file checks and 24 independently reviewed originals; 874 sequential source controls pass. Open source Figure, actual Undo/Redo, four Saves and all public Closes are covered. | Local Group(Page, Rect), empty Add or new blank Create, direct 1440x1000 only. Ordinary copies, broader scenes, host/theme coverage, final combined-source rebind and performance remain separate. |
| Ordinary Figure/Slides desktop and web | Frozen `df26e814` passes twelve cases: direct/web, 1280x800/1440x1000/1920x1080, light/dark. All 768 browser checks, 504 independent complete-file checks and 72 original visual reviews pass for the declared three Library drawings and generated editable PPTX fixture. | Dense scientific PDF host/theme coverage, broader interchange/corpus, installed Windows, public Close/resource cycles and performance remain separate. |
| Main/static restoration | Final source passes 826 Node controls, 13 Python controls and six browser modes: 100 checks, 30 independently reviewed originals, four complete actual saved-file proofs, and exact recovery for two omission faults. | This is the declared 1440 by 1000 deck, with local native-canvas recovery. Enclosing project/slide/history controllers are not globally atomic. |
| Dense SVG export | Public single/mixed SVG routes have complete vector/source and actual-download results for their declared inputs. | Final committed-source rebind, affine parent/nested clips, other scopes, reopened editability, PDF/PNG routes and measured costs remain separate. |
| PDF composition | Detached bounded composition and source-preserving controls exist. | Current-source composition, native caller integration and the declared memory limit remain open; detached results do not qualify actual file export. |
| Shared desktop/web delivery | The separate beta.12 Library release is delivered; PDF checkpoint work remains local. | Commit and freeze a new PDF candidate, build one matched native/static payload, qualify both consumers, then promote and verify both delivery surfaces through the existing release process. |

Detailed restoration evidence and limits are in
[Dense PDF canvas restoration](PDF_DENSE_CANVAS_RESTORE.md). Other component
results remain in their architecture notes and immutable reports beneath
`qa_artifacts/`. Historical passes must be rebound when their consumed source
changes; a current passing unit subset does not refresh an older browser journey.

## Remaining acceptance checklist

- [x] Review ownership/dependencies, then checkpoint accepted coherent source,
  tests and docs using explicit file/hunk manifests. Preserve unrelated work and
  keep detached or rejected experiments identified. An empty staging area was
  recorded before this resumed checkpoint audit.
- [ ] Qualify explicit **Open source Figure** and **Edit a copy in Figure** for
  dense artwork. Preserve the intended source/copy ownership, exact complete
  content, native geometry, history and actual saved-file continuation.
- [ ] Qualify **Create slide from canvas** and **Add canvas copy to slide** for
  ordinary and dense artwork; retain Figure selection/view/history, deck history,
  metadata and supported master/layout/inheritance behavior.
- [ ] Qualify the genuine scientific corpus: at least six independent PDFs from
  at least three producers, with the required vector/text/image/clip/font/Form,
  multipage and transparency coverage. Freeze original files/pages and named edit
  targets; never alter or publish private originals. Deterministic simulated
  producer fixtures supplement this corpus rather than replace it.
- [ ] Resolve the required source/reference appearance comparisons; verify actual
  edit targets, unaffected neighbors and high-resolution dense regions. A relevant
  unsupported construct keeps its required case open.
- [ ] Download and independently inspect SVG, PDF and PNG for unchanged and edited
  artwork, reimport supported exports, and continue editing after actual Save and
  fresh-context/process Open. Retain export failure/concurrent-save protections.
- [ ] Run populated direct/web authoring, Figure/Slides switching and supported
  external PPTX interchange at 1280x800, 1440x1000 and 1920x1080, light and dark,
  on one frozen candidate. Independently review all original captures.
- [ ] Measure ordinary/dense opening, cold Open, selection, text, point entry/edit,
  group/isolation/history, two-second gestures, Save and each export format.
  Require five cold runs and ten warm repetitions per action group, raw intervals,
  p50/p95/max, long tasks, actual renderer/hardware and incomplete/error counts.
- [ ] Meet the fixed budgets: preview p95 <=2.5 s/max5 s; editable Open/cold Open
  ordinary p95 <=5 s/max10 s and dense <=15 s/max30 s; input p95 <=100 ms/max250 ms
  (typing max200 ms); point entry <=500 ms/max1 s and edit <=100 ms/max250 ms;
  group/isolation/bulk history ordinary <=500 ms/max1 s, dense <=1.5 s/max3 s;
  gesture frame gap p95 <=24 ms/max100 ms; no main-thread task >100 ms and no
  foreground event-loop gap >250 ms. Save/serialize and preparation of each PDF,
  SVG and PNG download require ordinary p95 <=5 s/max10 s, dense <=15 s/max30 s.
  Keep the original policy's failure rules.
- [ ] Meet peak incremental JS/process budgets: ordinary384/768 MiB, dense1/2 GiB;
  after three load/edit/close cycles, stabilized growth <=20%. Growth above40% or
  monotonic retained growth is an immediate failure. Include workers,
  source/history, fonts, SVG/DOM and render surfaces. Unavailable measurements are
  unavailable, not passes.
- [ ] Requalify the 486-drawing Library and ordinary editing regressions, current
  rights/notices/vendor inputs and exact packaging dependencies before release.
- [ ] Build reviewed matched artifacts from the exact qualified commit, then
  synchronize public source/release, website and installed selection; verify
  their served/installed payloads and actual workflows. Keep the qualified release selected until
  this gate passes. Follow [the shared release process](../UNIFIED_FIGURE_RELEASE.md).

## Historical foundation execution order

The reviewed foundation is committed as `64b505b92966e77a8709890aea93be770a8da578`.
The separate detached-component checkpoint is `74126235` (30 files; no new editor
caller). Six incomplete composed-native diagnostic files remain outside these
commits. Package metadata, Library assets and the beta.11 consumer pin did not
change in those foundation checkpoints. The later beta.12 Library release is
separate from PDF acceptance. The roadmap remains the same.

The combined clean Git archive ran 2,164 Node controls: 2,153 passed and 11 were
explicitly skipped (nine require the external native host and two require retained
genuine component artifacts). The archived PDF Python controls passed 57 with 35
explicit private-artifact skips; all 13 changed-script checks passed. A broader
Python run recorded 483 passes, 36 skips and 65 setup errors caused by long Windows
temporary paths. After shortening only that test output path, all 66 cases in the
affected module passed. Original failed reports are retained. These are source and
regression checks, not refreshed browser, corpus or performance qualification.

The bounded dense handoff and native creation journeys now have the results
below. Ordinary Figure/Slides has its declared historical desktop/web matrix.
The current resumption order is the Fabric controls pilot followed by the
same-corpus PDF comparison above. Genuine-corpus, public-export and measured-cost
qualification remain required. Any later performance hypothesis must name the
observed cost, proposed change and accept/reject criterion; retain failed attempts
and change approach when gains plateau. Final qualification still uses one
committed frozen source and matched native/static payloads. Implementation stays
paused until the user resumes it.

## Public R export correction, 17 October 2026

The public recorder now opens original PDFs through New Document → Open artwork,
uses actual PDF Export As downloads, downloads the real Save and launches a fresh
Chromium process for cold Open. It records the correct chooser owner and reviewed
export request, returns drawing keyboard ownership through a real canvas click,
and captures complete native JSON before bridge traversal. All 57 original
check-call sites remain; console-error acceptance adds one. The declared R path
executes 50 checks. Internal helpers and save probes require explicit diagnostic
opt-in. Reproducibility and limits are in [public corpus QA](PDF_CORPUS_PUBLIC_QA.md).

Public trials reproduced a real export defect: U+2212 in negative tick labels and
rotated axis text used a different fallback glyph. The bounded correction keeps
the current positioned standard Helvetica minus through an export-owned Type1
encoding difference. It clones per-instance font tables, verifies the actual
generated standard-font resource and completes its encoding before file delivery.
Current drawing commands and glyph positions stay intact. Registered display
programs and native logical glyphs keep their existing paths; this does not grant
arbitrary font or source-PDF write equivalence.

The accepted R trial completes in 47.906 seconds under the unchanged owned
90-second supervisor, with zero remaining processes, script or console errors.
It passes 50 producer checks, 33 independent file checks, 17 full-original visual
reviews and 35 targeted source controls. Independent product and recorder source
reviews pass 16 and 10 checks. Both actual downloads retain all 11 Unicode minus
characters; all 11 affected raster regions match the source in each export.
The actual Save and complete warm/cold scenes match literally, including key
order, types and unknown fields. Original PDF bytes remain intact. Root rechecked
the full frozen source, 1,587 runtime/helper pins and every required binding.

The joined record is
`qa_artifacts/pdf-v1-checkpoints-20261017/reviewed-r-minus-export-and-public-recorder.json`.
Earlier chooser/control/focus failures, the exported-minus finding, the 35 lossy
absent/null observation differences and superseded reviewer attempts remain
retained; the fresh result closes only their declared corrections.

The unedited R export review still incorrectly reports no SVG text. A separate
genuine Prism public run passes editing, downloaded Save and fresh Open but fails
two fixed raster-comparison checks; its unedited PDF export matches source pixels
exactly. Independent review also observes a browser Save-failed status during that
journey. These remain active investigations. Continued cold child editing/second
Save, other public formats/reimport, export failure/concurrent-save guards,
Illustrator, mixed native/custom/deck exports, dense, installed, performance and
paired delivery remain separate. The roadmap and beta.12 selection remain the same.

## Prism source-size metadata, 17 October 2026

Independent complete-file review found that the original Prism PDF's 4,030 bytes
were preserved exactly, while derived artifact/storage metadata reported 4,032.
The shared size estimator counted Base64 padding as source bytes. It now subtracts
the one or two trailing padding characters without decoding or copying the asset.
Artifact identities, hashes and retained source content stay unchanged.

The correction passes 65 targeted controls and a fresh 42-check independent file
audit. All nineteen source-size fields in the actual Save, including its duplicated
manifest, report 4,030. The complete actual saved Fabric scene equals the warm and
cold observations literally. Reopened complete storage/registry fields and private
runtime store sizes were not retained by this recorder; this is saved-file metadata
qualification only. Root rechecked all 2,400 baseline source files, three overrides
or added test, 1,587 runtime pins, 27 file bindings and the actual embedded source.
The joined record is
`qa_artifacts/pdf-v1-checkpoints-20261017/artifact-size-padding-1/reviewed-metadata-correction.json`
(SHA256 `432a7f05f761885e794eb6195bd15c17ab0e7b374807265734adfc1269628118`).

The public run completes in 46.797 seconds under the unchanged owned 90-second
supervisor, with no remaining processes. It still passes 48 of 50 checks: both
original raster comparisons remain failed. Warm/cold browser saves succeed in this
run, which does not resolve the earlier observed browser-save error.

A separate capture-only experiment normalizes the font-size/transform split for
all 112 actual text draws. Both artwork and difference PNGs remain byte-identical;
independent review rejects this hypothesis for the measured Prism page. No product
font-rendering change follows from that negative result. Its joined record is
`qa_artifacts/pdf-v1-checkpoints-20261017/prism-font-gauge-qa1/reviewed-negative-result.json`.

A separate fixed 300 dpi Open/export diagnostic captures matched 986 by 592
source and actual-canvas images without resampling or registration shifts. Changed
page pixels are 0.9986%, compared with 3.2127% in the original 144 dpi comparison.
All 112 explicit-Arial text draws produce identical PNG bytes to the generic
sans-serif render. Independent review of all five originals supports a
rasterization/hinting explanation and finds no gross missing, shifted or clipped
artwork. It does not authenticate Chromium's font-program bytes or close the
original predicates, edited-export comparison or Illustrator requirement. The
separate review is
`qa_artifacts/v1src6/qa_artifacts/corpus-prism-300dpi-1/real-1/independent-300dpi-review.json`.
Continue the source/reference appearance investigation, text-preflight correction,
genuine corpus and full V1 requirements. The roadmap and beta.12 selection remain
the same; this checkpoint does not promote a PDF release.

## Clipped heatmap Canvas finding, 17 October 2026

The genuine Prism `generic heatmap.pdf` completes all 50 public recorder checks
in 51.703 seconds under the unchanged owned 90-second bound, with zero remaining
processes. Independent actual-file/source review passes 43 checks: the complete
Save/warm/cold scenes match literally, all 8,867 source bytes and nineteen saved
size fields match, and the 281 path records, 81 clip relationships and 22 text
runs remain present. Raw PDF readback differences remain documented without an
exact source-geometry or new-tolerance claim.

Independent review of all seventeen original captures rejects the Canvas
appearance. It introduces pale cell boundaries and conspicuous horizontal bands
in the color scale; both actual PDF exports retain the smoother source appearance.
Numerical raster success does not close this defect. The actual A-to-A-beta label
edit survives cold Open. The cold browser-save snapshot says saving, while a later
close observation says saved; these are distinct observations.

The joined HOLD is
`qa_artifacts/pdf-v1-checkpoints-20261017/reviewed-heatmap-public-1-hold.json`.
Investigate device coverage for opaque rectangle fills and rectangular clips while
preserving canonical paths, clips, transforms and exports. The first capture-probe
source review requires ownership-safe cleanup and a complete numerical/visual
decision before execution; no product rendering patch has been applied. The false
text-preflight advisory remains open. The roadmap and release selection remain
unchanged; continue the full V1 workstream.

## Resumed handoff result, 17 October 2026

The bounded **Edit a copy in Figure** journey now passes both complete public
intervals on an exact Git archive of `d59d6687`. Warm copy, native K-to-Z title
replacement, Undo/Redo, source independence, actual Save and public Close pass
65 checks in a 59.828-second owned job. A fresh browser opens that exact download,
joins three saved sources to three distinct fresh owners, replaces copied Z with
Q, checks Undo/Redo and both unchanged sources, then actually Saves and Closes:
95 checks in 72.968 seconds. Both jobs retain the unchanged 90-second deadline,
finish with no owned processes and release all PDF owners, views, bitmaps and
native labels. Job duration is not an interaction benchmark.

Independent file reviews pass 35 warm and 44 cold checks. Root and an independent
visual reviewer inspected all 11 full 1440 by 1000 originals. The warm and cold
files are 18,125,104 and 18,126,338 bytes. The latter's complete actual saved-file
proof was also independently recomputed by root. Fresh Open starts fresh history;
this does not claim continuity of the warm Undo stack.

Earlier deadlines and visual rejections remain preserved. The repeated warm
observer transport was corrected to transfer each immutable full observation
once and to encode lossless native witnesses before crossing the browser bridge;
own undefined values, negative zero, field order and complete geometry remain
checked. Source C's pre-existing KM title collision was corrected through an
actual public native edit and Save, independently reviewed, then admitted as a
declared fixture. No scientific original, product renderer or acceptance bound
was changed to obtain the result.

The joined evidence is
`qa_artifacts/fhsrc1/qa_artifacts/pdf-dense-figure-handoff/reviewed-warm5-cold3-closure.json`
(SHA256 `fd76f02ba73d3c099ebd3583ea62daca900540f87849f3ba91b671e19be8b209`).
It binds the actual reports/downloads, supervisors, independent reviews, all
captures, corrected input and frozen source. The source tools and exact dispatch
records are described in [the bounded handoff QA note](PDF_FIGURE_HANDOFF_QA.md).

This closes the declared reverse-copy journey on that frozen source. The later
Style 4 Library changes, final combined candidate, other handoff/creation actions,
corpus, exports and fixed performance/memory requirements still require their
own evidence. No PDF release was promoted. The roadmap remains the same; continue
with native Figure-to-Slides creation and copying before shared qualification.

## Native Figure-to-Slides result, 17 October 2026

The accepted native Add-12/Create-2 and cold Add-2/Create-1 journeys preserve the
complete source Figure, create independent native copies and retain exact deck
metadata. After actual Save and fresh-process Open, **Open source Figure** edits
source Z to Q while the placed slide remains Z. Real Undo/Redo, complete native
geometry, all other text items, four full asset bundles and public Close cleanup
pass. Detailed text editing occurs in Figure; placed Slides artwork remains a
whole group.

Independent reviews cover all four actual downloaded files and all 24 original
captures. Create-2 closes the earlier missing exact blank-page timestamp witness
with a complete runtime-to-file metadata join. The four jobs finish in
64.828/63.141/65.437/68.343 seconds under separate unchanged 90-second supervisors,
each with zero remaining owned processes and zero retained PDF resources after
Close. These durations are not interaction benchmarks.

The joined evidence is
`qa_artifacts/pdf-figure-slides-20261017/reviewed-add12-create2-cold-closure.json`
(SHA256 `5e5daa28c0cd6fc1607213ffbe68a619e54e69306bd1ae2b4c446090adaaab1a`).
It records 134 producer predicates, 530 independent file checks, the 874-control
source regression and 79 root-rechecked file bindings. See
[native Figure-to-Slides creation](PDF_FIGURE_TO_SLIDES_CREATION.md) for scene,
history, ownership and visual limits. Earlier failures remain preserved.

This closes the declared direct 1440x1000 local Group(Page, Rect) journeys.
The roadmap remains the same. Continue ordinary Figure/Slides, desktop/theme/web
coverage, corpus, exports and fixed performance/memory requirements on a frozen
combined candidate. The beta.12 Library release remains selected; no PDF release
was promoted.

## Ordinary Figure/Slides matrix, 17 October 2026

An exact 2,398-file Git archive of `df26e814` supplies one unchanged application
for all twelve route/size/theme cases. The only overlay is independently reviewed
QA recording: one coherent idle native-JSON workspace observation before and
after actual downloaded-file Open, and correct classification of context-close
request cancellations. Product, vendor and asset bytes remain frozen. Each case
runs in a separate unchanged 90-second owned job, finishing in 47.484–50.906
seconds with no owned processes, browser errors or unexpected failed requests.
Job duration does not establish interaction performance.

The journeys exercise actual Library insertion, ordinary SVG canvas copies,
slide creation/order/removal, source selection/history, rail controls, play,
combined project download, fresh-browser-process Open and supported editable
PowerPoint import/move/Undo/Redo/export/reopen. Independent file review compares
complete serialized workspace content without rounding, including every retained
slide and unknown field. Only the exact named active capture clocks and two
derived manifest bounds differ; the full source forest remains literal. The
original inherited comparator's broader omissions are not used as complete-file
proof. The PPTX fixture has one ordinary rectangle and one live label, generated
outside Figure with python-pptx; arbitrary Office presentation fidelity is open.

All 72 originals have independent visual approval. Four 1280-wide initial views
leave the third thumbnail below its scrollable list viewport. Eight smaller
floating-pane frames intentionally overlap the Golgi drawing. These declared
views do not claim unobscured artwork or every thumbnail visible. Wide frames
have neither limitation.

The joined closure is
`qa_artifacts/pdf-v1-checkpoints-20261017/reviewed-ordinary-figure-slides-matrix.json`
(SHA256 `d48c32615611b3a0b464b2d952ceed458cc00fe8c11a8e5fbb7e35f35a50124a`).
It binds all twelve reports/downloads/supervisors, 24 independent reviews, 72
originals, the complete frozen source manifest and the sole reviewed QA overlay;
root rechecked 296 file bindings. The initial old-recorder 1440-light run remains
preserved separately. See [Figure and Slides](FIGURE_AND_SLIDES_PROJECT.md) for
the bounded command and file-comparison limits.

The roadmap remains the same: continue the genuine scientific corpus, actual
public export/download/reimport, dense host/theme coverage, fixed performance
and memory budgets, then matched native/static delivery. No PDF release was
promoted; beta.12 Library remains selected.

## Rectangle display and current regression findings, 17 October 2026

The fresh heatmap result closes the two specifically rejected Canvas defects:
pale cell seams and color-scale stripes. Its explicit source-owned rectangle
display policy preserves literal vector operands and clip ownership. The normal
import/reopen keeps the native fill renderer when no variable stroke is active;
actual variable-stroke editing still installs its existing renderer. Exact native
child-drag checks preserve every unaffected neighbor and ancestor frame. Stroked
and nonhex imports retain their prior policy and authoring routes.

The final candidate passes 83 targeted controls and a separately run independent
48-control subset. Six independently authored PDFium controls match actual device
bounds without a new tolerance. The public run completes in 52.547 seconds under
the unchanged 90-second owner, with no remaining owned processes. All 50 producer
checks, 48 complete-file checks and 17 original visual reviews pass for the declared
heatmap scope. Root rechecked 80 file bindings, its actual embedded original, all
19 source-size fields and all 2,402 frozen source files. Complete native JSON Fabric
observations equal the actual downloaded Save, including unknown fields/order.
The 231 raw source-to-export numeric readback differences remain unchanged and
retained; this adds no exact-source-geometry claim.

The joined result is
`qa_artifacts/pdf-v1-checkpoints-20261017/heatmap-device-rectangle-product-4/reviewed-product-final-controls.json`
(SHA256 `2be3e046feb530d2b0ee37b6df3f92372cf8e56493de376cd8e1dc7154c3eba7`).
Three earlier product revisions, their independent HOLDs and the temporary paint
hypothesis remain preserved. This result applies to new imports and saved
continuation of eligible rectangles, not migration of historical plain Paths or
arbitrary effects/native-v2/performance qualification. Resetting an active variable
stroke to uniform retains the existing wrapper until reconstruction.

The pre-correction R and Prism artwork pixels match their earlier corrected runs.
The R minus regions remain correct, but both current warm editor views show a
browser-save failure; the successful downloaded files and cold scenes do not close
that failure. Prism also retains its two 144-dpi raster findings. The heatmap cold
host snapshot still says `saving`, followed by a later `saved` observation. Keep
these distinct from actual file Save/reopen proof. At that checkpoint the false
text-preflight advisory remained open; its later correction is recorded below.

The user selected Affinity as the external comparator. The earlier Windows input
failure was resolved after the user dismissed the screen saver. Actual separate
native saves, exports and reopening are now recorded below; the initial prepared
copy and paused observation remain historical evidence. Other corpus, export,
performance and delivery work continues. Apart from this requested comparator
change, the roadmap remains the same. No PDF release was promoted; beta.12 Library
remains selected.

## Browser workspace save correction, 17 October 2026

The original browser failure was reproduced at the host's actual failure handler.
The workspace worker rejected a canonical PDF path-edit descriptor's
`history_label` field as runtime history. The portability validator now preserves
that literal string only inside the exact schema-matched PDF edit-plan descriptor
array. Unknown schemas, nonstring labels, runtime siblings and machine resource
paths remain rejected. No history data is stripped or writer authority added.

The correction passes 115 targeted controls, 13 independent controls and 13 source
assertions, including an actual App-produced descriptor and the unmodified
workspace worker. Frozen `v1src9` contains 2,404 source files. The fresh default R
and Prism journeys complete in 47.797 and 47.313 seconds under the unchanged
90-second supervisor, with zero remaining owned processes. R passes 50 of 50
producer checks; Prism retains its two original raster failures at 48 of 50.

Independent actual-file audits pass 51 R and 54 Prism checks. Each complete actual
Save equals its full warm and fresh-process cold scene using native JSON
serialization. Original source bytes and all nineteen size fields per file remain
correct. All 34 original screenshots are independently reviewed. Each case's ten
artwork/difference images and complete geometry/text/paint comparison match the
preceding run; recorded warm/current/close browser-save states now all say Saved.

The joined evidence is
`qa_artifacts/pdf-v1-checkpoints-20261017/browser-save-edit-label-1/reviewed-product.json`.
It rechecks 132 file bindings, both embedded sources, 38 size fields and all 2,404
frozen source files. Historical failures remain intact. These are recorded host
snapshots, not per-edit acknowledgement or durable IndexedDB recovery. The final
journeys Undo their path changes, so typed-plan preservation remains a separate
worker/producer control rather than a final-file claim. Text-preflight correction,
Affinity, broader corpus/exports, performance and matched delivery continue.
The roadmap and selected beta.12 Library release remain unchanged.

## Truthful PDF checks and visible export feedback, 17 October 2026

Imported panels now use their retained nonempty text labels or issued native text
inventory when deciding whether text checks are available. Historical absent or
stale SVG counts cannot contradict real editable labels; path-only, empty and
metadata-lookalike cases retain the advisory. Small-text thresholds and severity
remain unchanged. When rounding hides a strict size/threshold relation, the warning
says the text is just below the configured threshold instead of displaying the
contradictory pair “7 pt below 7 pt.”

Export warnings wrap long generated font names, keep severity badges on one line,
and place the existing polite result message beside the fixed footer actions.
The same request, controller, success/error and reset behavior is retained. The
static ready hint hides while a result is shown. This corrects the observed
1280x800 screenshots whose actual successful downloads had feedback below the
visible footer.

The exact revision 6 candidate in frozen `v1src11` passes the inherited 86 targeted
controls, 15 independent preflight controls and 14 independent footer/source
checks. After copying those exact three source/test files to the canonical tree,
15 focused controls and App syntax pass again. The first post-copy report parser
expected TAP while Node emitted its passing spec report; both original output and
the corrected explicit-TAP run are retained. No test or product failure was hidden.

Fresh Adobe Open-only and drug-targets full public runs complete in 32.625 and
52.625 seconds under the unchanged 90-second supervisor, with zero remaining
owned processes. All 24 original images receive independent review. Both actual
drug-targets PDF result messages and the Adobe result are fully visible beside
Cancel/Export; whole badges and long font tokens fit. The false missing-text
advisory is absent and the near-threshold wording is truthful.

Drug-targets passes 50 public and 62 independent file checks. Complete actual
Save/warm/fresh-process cold scenes match literally, with its 4,651-byte source
and all nineteen size fields retained. All ten artwork/difference PNGs and decoded
PDF streams match the earlier run. Its 409 raw PDF numeric readback residuals,
selected-bar Clip/title collision and final pending browser-save snapshot remain
explicit. Adobe remains 18/19 with its original Canvas fidelity HOLD; its unchanged
artwork/difference images match the previous revision exactly. No AA-only claim or
threshold change is made.

The joined result is
`qa_artifacts/pdf-v1-checkpoints-20261017/preflight-inspectable-text-6/reviewed-product.json`
(SHA256 `cdde746d3fde73f6954dc8e0bf9c7d6690c199dd494309705be72743605f3a41`).
It rechecks 2,527 file bindings, the embedded source, nineteen saved size fields
and all 2,405 frozen source files. Earlier rejected revisions and their original
reviews remain intact. This closes the declared checks/feedback defects, while
continued cold edits, other export formats, dense/performance and final delivery
remain required. The roadmap and selected beta.12 Library release remain the same.

## Actual Affinity Prism comparison, 17 October 2026

Affinity opens the byte-identical 4,030-byte Prism source using its recorded PDF
import settings, with Arial replacements visible. It produces an unchanged native
save and PDF, then the same beta-containing title at 6.9 pt and pink 1 pt outline
on the second teal rosiglitazone marker. Native text Undo/Redo, Group/Undo/Redo/
Ungroup and curve-handle keyboard editing are observed. Separate edited native
documents are actually closed and reopened; the corrected reopen exposes the
title's 6.9 pt control and the marker's retained position and outline.

The first edited export audit catches a 0.24 pt unintended marker translation:
18/19 checks pass and the position check holds. A separate corrected native/PDF
pair restores all thirteen control/end points, matrix, topology and clipping
literally. Its 21/21 audit passes; all 67 other path records and 93 non-title
glyph origin/bounds/em-axis records remain literal to unchanged Affinity. The
earlier failed pair is preserved. All 22 actual native UI originals are reviewed.
The initial pointer attempts changed selection; they do not qualify node dragging.

The comparison retains real differences: Affinity rounds page dimensions, embeds
Arial subsets and shifts glyph spacing. Figure keeps a separate original thin teal
stroke when adding the pink outline; Affinity combines fill/stroke. At 300 dpi
Affinity renders 986x593 versus source/Figure 986x592, so no resized comparison is
used. The native `.af` format is opaque, with file identity and public UI behavior
recorded separately. This is one ordinary comparator case, not arbitrary PDF or
full V1 qualification.

The joined comparison is
`qa_artifacts/pdf-v1-checkpoints-20261017/affinity-comparator-1/reviewed-comparison.json`
(SHA256 `6ea346343d7a5b94e40902b5cce2f19e20a8a2422cc13ed17afdba08368e4c67`),
which rechecks 122 file bindings. The [comparison protocol](AFFINITY_PDF_COMPARISON.md)
retains the settings, scope and remaining differences. The roadmap remains the same.

The next larger Adobe Figure 2 full public attempt reaches a real 16,535,791-byte
Save and starts fresh-process Open, then reaches the unchanged 90-second deadline
(90.047 seconds, zero remaining owned processes). Its producer remains `RUNNING`
at the last checkpoint, with 31/33 recorded checks passing. Canvas fidelity and a
300.1 ms event-loop gap fail; cold continuation and edited PDF export are absent.
The warm browser-save observation says `saving`. Preserve that partial attempt
and continue from its actual downloaded file in a bounded interval, rather than
repeating or relabeling the incomplete full journey.

## Adobe continued editing and second Save, 17 October 2026

The actual downloaded Adobe first Save now has a completed staged continuation.
Public Object Selection and Enter Isolation reach the intended label; actual
typing changes `Z-score β` to `Z-score β [c]`. The existing strict semantic,
typed and ordered native-field checks pass, with its physical baseline literally
unchanged and all 1,308 other leaf records retained. Complete native Fabric Undo
equals the cold scene, Redo equals the edited scene, and the actual second Save
contains that edited scene literally.

Three bounded fixes in `app/pdf-svg-materializer.js` address observed failures.
Fallback glyph painting temporarily copies its style records and restores the
original full styles reference in `finally`, so a frozen export descriptor is
not mutated. Grouped text starts with an empty hover-coordinate cache until
normal activation computes its real coordinates. Existing text-input handling
also admits an already valid single-line paint frame, letting the existing
measurement solver retain its baseline instead of applying a second native
origin reposition. Existing native-plane, unframed and multiline paths retain
their admission rules. No geometric epsilon or raster threshold changes.

The earlier exact one-ULP baseline failure, original fallback-paint exception,
hover stack, selection/readiness failures and rejected candidate/test revisions
remain preserved. The source/arithmetic explanation of native repositioning is
separate from the actual five passive baseline observations. Frozen-source
review status was PENDING when copied; the later exact candidate source review
passes 17 checks. Its 46 focused controls include eighteen fallback, four hover
and five input-anchor controls. Nine checks on repository-LF test variants repeat
the hover/input coverage; they are not nine additional distinct controls.

The continued-edit/Undo/Redo/second-Save interval passes 39/39 checks in 52.813
seconds. A separate fresh-process public Open of that exact second Save and
actual public PDF download passes 5/5 in 45.281 seconds. Both use the unchanged
90-second supervisor, close with zero owned processes and record no script or
console errors. The native Fabric stored in the second Save matches the edited,
Redo, reopened and post-export scenes literally. The continued, reopened and
post-export artwork PNGs are byte-identical. Export also preserves all live artwork
pixels. Recorded host snapshots say Saved;
durable browser-store recovery is still unmeasured.

Independent file audits pass 35/35 and 25/25, and all fourteen original images
receive independent review. The first file-review HOLD is preserved: its failed
assertion incorrectly equated image-local and active-registry role notes that
already differed in the input. The corrected review retains all six raw note
differences and proves the complete image objects and complete registry separately
unchanged. Save1 to Save2 has sixteen complete-project differences: six declared
text/reflow fields and ten regenerated metadata fields. All raw values remain;
the entire portable project containers are not byte-identical.

The actual PDF retains all panels, the added suffix and pink legend outline.
Its paths/paint/clip fields and existing painted glyph geometry match the prior
actual beta export; emission-index and generated CR/LF anchor differences are
retained separately. Existing Canvas/JPEG/glyph residuals remain, including the
0.034382324 changed-page fraction above the unchanged 0.025 diagnostic ceiling.
The original 90.047-second full-journey HOLD and 300.1 ms event-loop failure are
not replaced by these staged results. No AA-only or full appearance clearance
follows.

The joined result is
`qa_artifacts/pdf-v1-checkpoints-20261017/pdf-native-textarea-anchor-1/reviewed-product.json`.
It rechecks 5,019 unique bindings, all 2,408 frozen files and 1,587 runtime
authorities per actual stage. The canonical materializer is byte-identical to
that consumed runtime. Its three regression tests use the explicitly reviewed
LF variants; all 46 focused controls and syntax pass at their canonical paths.
Six detached diagnostic files remain excluded. No release or consumer pin changes.
Next continue actual SVG/PNG downloads and reimport, broader genuine corpus,
source appearance, performance and matched delivery. The roadmap remains the same.

## Adobe SVG, PNG and PDF downloads, 17 October 2026

Actual public SVG/PNG downloads first exposed a metadata error: the SVG advertised
1,319 editable paths by counting inherited release flags on text, images and
groups. Its painted path count is 343. That first file audit remains HOLD, with
26/27 final checks passing; its file content and live-state proofs are retained.
The initial reviewer numeric-type adapter mistakes and corrected literal numeric
token parser are preserved separately.

`documentPdfSourceExportMetadata` now records the existing actual Canvas-path
classification separately from historical release flags. Per-source and total
editable-path counts require both. Raw release flags, source identity and the
1,319 reconstructed-object count remain unchanged. Native page/vector primitive
inventory remains separate; a native owner is not one synthetic Canvas path.
Import, selection, painting and export execution are unchanged.

Five new functional controls fail three cases on the original source and pass all
five on the candidate. The candidate passes twenty controls including fifteen
existing preflight checks; the frozen candidate passes those twenty plus three
existing PDF child/source checks. All 23 pass again at their canonical paths,
with App syntax clear. These are overlapping control groups, not additive totals.
Independent product-source review passes fourteen checks. A separate seventeen-case
oracle review rejects incorrect classifications even when the total remains 343,
and protects unknown metadata fields, types and native key order.

The fresh three-format public run completes in 56.234 seconds under the unchanged
90-second supervisor, with 21/21 checks, zero retained processes and no browser
errors. Independent file review passes 31/31, and all seventeen originals receive
independent visual review. Native Fabric in the actual second Save matches the
cold and post-SVG/PNG/PDF scenes literally. Each complete live artwork PNG and the
actual PNG download are byte-identical to the continued artwork.

The complete 3,734-node SVG differs from the prior actual export only in the
declared source-metadata classifications/counts, root count/export clock and one
verified generated artboard-clip definition/reference pair. All raw differences
are retained. Its actual vectors, Unicode mappings, images and font data remain
unchanged. The fresh PDF's streams and resolved objects are literal to the prior
actual PDF except its two Info clocks; trailer IDs also differ. No geometry or
character tolerance is introduced.

All three success messages remain visible in the fixed footer. SVG Image/canvas
and PDFium difference images match the prior originals exactly. Existing SVG
raster uncertainty and the PDF/Canvas 0.034382324 versus 0.025 HOLD remain; this
does not establish an AA-only explanation. SVG embeds its two source font programs
but retains three system-Arial spans. PNG has the requested 1224x1584 pixels for
144 dpi on the 8.5x11 inch page; no embedded PNG physical-density tag is observed.
Reimport, font portability, original JPEG/source appearance, durable store recovery
and repeated performance/memory remain separate.

The joined result is
`qa_artifacts/pdf-v1-checkpoints-20261017/svg-pdf-path-count-1/reviewed-product.json`.
It rechecks 2,606 unique bindings, all 2,409 frozen files and 1,587 runtime
authorities. The copied App/test bytes match that consumed candidate. Historical
HOLDs and both initial reviewer assertions remain intact. Next reimport the actual
exported PDF and test recoverable editing, then continue broader corpus, source
appearance, performance and matched delivery. The roadmap and selected beta.12
Library release remain unchanged.

## Isolated Adobe reimport investigation, 17 October 2026

The original placed-page HOLD remains preserved. Source-bound diagnostics traced
its rejection through the generated SVG declaration budget, repeated whole-source
clip comparisons, the private renderer's initial miter limit, and native affine
pose construction. The reviewed experiments retain the original limits and exact
numeric comparisons. Their source lives in ignored candidates; they have not been
copied into the canonical runtime or a release payload.

Trials 6 and 7 reach native reconstruction. Trial 6 stops in a QA observer that
incorrectly expects every text run to paint its first character. Sixty-five real
runs start with spaces, including six entirely blank runs. The revised observer
records every actual painted source index, all source SVG spans and the native
cursor anchor, without inventing Canvas paint for spaces. All 65 detached native
records pass; 50 altered-record controls reject. Its scope is geometry and fonts,
with a declared native SVG style profile; it does not prove fill color or raster
fidelity. Trial 7 independently validates all 960 live text records through the
two declared physical schemas.

Trial 7 finishes within its unchanged 90-second supervisor in 60.546 seconds,
with zero owned processes or cleanup errors. Four producer predicates pass before
glyph correspondence stops the run. Complete project/native Fabric values join
literally, and the exact exported PDF remains retained. All 2,580 printable
characters are present, but the strict run matcher leaves 15 source indices
unassigned: PDFium interleaves nearby axis labels into `Sensitive (n=91)`.
Independent per-glyph analysis finds unique Unicode/baseline matches within the
existing 0.05 scene-pixel limit. Space association still needs an independent
resolution; no correspondence predicate has been waived.

All seven original captures received independent visual review. The page is
unobstructed after a real Escape closes the Browser files menu, while its
**Save failed** and **Unsaved** feedback remains visible. Panel A loses thin
dendrogram connectivity in the raster, and the Venn raster has jagged edges.
These observations do not establish missing native paths or their cause. The
source comparison remains above its unchanged 0.025 threshold at 0.030953427.
The complete captured project also reproduces a portable-format rejection of a
literal slash in the newer positioned-text schema; that is a controlled serializer
diagnosis, not a caught live host exception or a successful Save.

Evidence is under `qa_artifacts/pdf-v1-checkpoints-20261017/`, principally
`adobe-current-affine-pose-1/`, `adobe-leading-space-observer-1/`, and
`adobe-exported-pdf-reimport-7/`. Native reparenting still has three exact QR
normalization failures. Neither successful construction nor the live text checks
qualify arbitrary Ungroup/reparent operations. Next address the typed text saving
failure, independent glyph/space correspondence, visible raster defects and
measured costs, then continue the remaining V1 corpus and paired delivery.
The roadmap and selected beta.12 Library release remain unchanged.

## Historical restart checkpoint, 17 October 2026

The user requested a restart at a safe stopping point. All three delegated tasks
are stopped with no active processes. The last browser job was terminated by its
unchanged 90-second supervisor, which confirmed zero remaining owned processes.
Resume from this checkpoint after restart; this is not V1 completion.

The guarded **Edit a copy in Figure** caller is implemented for one complete local
Group containing an issued PDF Page followed by an ordinary rectangle. It prepares
an independent owner, retires unused views before the existing document loader,
and protects source metadata, history and newer document operations. Geometry
that cannot survive an exact native round trip, unsupported appearances and
inherited artwork still refuse. The normal PDF registry's optional undefined
typed-revision field is recognized without permitting other metadata loss.

The current source passed **608 targeted Node controls, zero failures or skips,
and two syntax checks** in 15.547 seconds. The exact commands, source bindings and
logs are in
`qa_artifacts/pdf-v1-checkpoints-20261017/validation/handoff-metadata-regression-1/`.
The earlier failed integration run and both corrected test fixtures are retained.

The third genuine warm browser run passed 54 recorded checks: the actual copy,
native title edit, Undo/Redo, unchanged original source slides and their separate
owner bindings. It reached the return from the source deck to the copied Figure
before the deadline. **No actual Save download or cold-open qualification was
reached.** Its producer report remains `RUNNING` because the process was killed;
the authoritative supervisor result is `HOLD_DEADLINE`, exit 124, owned processes
zero. Four full-resolution captures received an independent bounded appearance
review. Do not reinterpret these observations as a passing complete journey.

Resume with the following evidence:

- Browser report and independent diagnostic review:
  `qa_artifacts/pdf-dense-figure-handoff/warm-20261017-3/`.
- Supervisor:
  `qa_artifacts/owned-browser-qa/figure-handoff-warm-20261017-3/supervisor.json`.
- Actual invocation and source stability record:
  `qa_artifacts/pdf-v1-checkpoints-20261017/handoff-integration/warm-3-actual-execution.json`.
- Reviewed warm test source:
  `qa_artifacts/pdf-v1-checkpoints-20261017/handoff-success-qa/revision-2/`.
- Prepared cold test state, with a small source-control rerun still pending:
  `qa_artifacts/pdf-v1-checkpoints-20261017/handoff-cold-qa/revision-3/source-state-pending.json`.

First diagnose the time spent returning to the copied Figure, then finish the
actual Save, public Close and independently reviewed warm execution chain before
running cold continuation. Keep the 90-second bound and every independence,
geometry, history and saved-file check; any revised test staging needs review.
At this historical checkpoint there was no successful warm file or approved cold predecessor to reuse.
The two earlier failed warm runs and the read-only registry diagnosis remain
preserved beside this evidence.

Six untracked composed-native diagnostic files remain intentionally outside the
checkpoint; do not stage, delete or treat them as qualified export code. No PDF
release was promoted. The roadmap remains the same: complete handoff/creation,
then corpus, exports, performance/memory and matched desktop/web qualification.

## Affinity comparison and continued reimport qualification

The user selected Affinity as the external comparator. The unchanged exported
PDF was opened with Affinity's actual import settings recorded, saved as a new
QA `.af` file, closed, and reopened. The full page and the recovered
`Sensitive (n=91)` label retain visible continuity. The actual copied label has
one ASCII space before `(n=91)`. A strictly bounded QA supplement can resolve
that one interleaved source-label match; it retains the original failed matcher
and every other glyph, baseline, word-space and once-only source-index check.
Its 49 controls pass, but no later native browser run has yet completed it.

Affinity's actual PDF export is also retained and independently reviewed. Its
paths, image dimensions, printable characters and inspected labels survive, but
all text uses a substituted embedded Arial font, including formerly bold text.
Four images were JPEG-reencoded. Its overall raster comparison is below the
existing page threshold, while those typography and image changes remain
explicit limitations. The modified QA tab was left open after export; no
subsequent Save or Close of that tab or the user's original modified figure
was performed. Evidence is in `affinity-adobe-reimport-1/` below the checkpoint
root, including the native Save/reopen and actual PDF-export reviews.

The positioned-text slash correction passes the retained complete-project
serializer controls. Public trial 8 nevertheless times out in editable SVG
construction and produces an opaque fallback: zero native paths/text and one
image. Its first three checks pass, with the zero-text physical check vacuous;
the native inventory rejects before any Save. The existing 15-second import
limit, performance failures and appearance failure remain unchanged.

A separate display-font encoding cache avoids reencoding unchanged font bytes
and MIME on repeated selections. Its final source review passes 20 scenarios;
44 focused frozen-source tests also pass. Public trial 9 reaches visible
editable artwork, but the original 30-second completion wait expires before
scene capture or Save. No native counts, glyph qualification or cache speedup
can be inferred from that screenshot. Trials 8 and 9 both finish below the
90-second supervisor with zero owned processes; their independent file and
full-resolution visual reviews preserve the failures.

The missing Panel A connector is localized to an embedded image. A separate
image-sampling candidate distinguishes an omitted PDF interpolation setting
from explicit false, with 25 source controls passing. It is excluded from
trials 8 and 9 and has no fresh browser, raster or Save qualification. The next
step is to identify trial 9's outstanding completion condition, then finish
actual native Save/cold editing and the image comparison before wider corpus
and performance work. All candidates remain unpromoted. The roadmap and selected
beta.12 Library release remain unchanged.

A readonly busy-state diagnostic reproduces the completion failure and retains
a native scene with 344 paths, 960 text objects and six images. All 7,491
inventory rows join the later captured project, and the exact input PDF and
portable resources remain retained. At the first post-error sample, history
capture is still locked; later samples show history completed and the outer
import capture still active, then idle. Those readings are separate instants;
the intervening diagnostic reads themselves add work. Independent file review
passes 24 checks, while the original 30-second Open failure remains HOLD.

A second same-source diagnostic omits the large scene snapshot and records a
Chrome CPU profile. Its 30.840-second sampled window contains substantial JSON
copying, native serialization and layout-graph work. The named hot frames map
to frozen source; all independently recomputed sample weights agree. In that
run, history is already complete at the first sample but import capture remains
busy through the last observation. Sample weights overlap across callers and
do not measure wall time of asynchronous functions or normal Open performance.
Both diagnostic jobs finish under the unchanged 90-second supervisor with zero
owned processes. Their evidence is in `adobe-public-open-busy-diagnostic-1/` and
`adobe-public-open-history-profile-1/` below the checkpoint root.

The next isolated correction replaces recursive generator delegation in the
cooperative JSON copier with explicit parent frames. The existing value
conversion, private fresh-record authority, 128-step/8-ms yielding and
cancellation checks are unchanged. Source review passes 12 checks and 20 fresh
adversarial controls; 31 root checks include 17 retained cooperative cases. Four
ordered Node copies of the retained project preserve complete JSON bytes and
source values. Those local observations do not qualify browser latency. Internal
stack behavior changes for extremely deep input, without a new product depth or
resource admission claim. The normal browser candidate excludes the diagnostic
App accessor, CPU profiler and separate image-sampling correction. Actual public
Open/Save, cold restoration and appearance/performance checks remain next.

The copier evidence is in `adobe-cooperative-json-clone-1/` below the checkpoint
root. Frozen24 contains only that additional runtime delta over frozen23;
148 targeted frozen-source tests pass with no failures or skips. Seventeen of
those repeat the earlier retained cooperative cases. The next public Open and
Save recorder is prepared in `adobe-exported-pdf-reimport-10/`; preparation and
source controls do not establish an actual Open or Save result. The roadmap
and selected release remain unchanged.

Public trial 10 still fails the original 30-second completion wait, before
retaining native observations or attempting Save. Its unchanged 90-second owner
finishes in 39.360 seconds with zero children or cleanup errors. All source and
input bindings remain exact. Independent file review passes 18 evidence checks;
the full original shows the figure, Unsaved feedback and an import toast over
part of panel H. It does not establish native counts or the outstanding busy
condition. The Node copier improvement has not qualified browser performance.

A separate 40-byte metadata-scan condition skips only generator calls that would
immediately return false for null/nonobjects. Its source and 49 controls pass,
but four ordered full-project Node observations show no clear gain. It remains
outside the browser candidate, in `adobe-shared-metadata-scan-1/`.

Existing history and page caches are not portable raw-scene authority: history
normalization can replace large data URLs with artifact references, and mutable
page fabric must remain separate from project fabric. The next diagnostic,
prepared in `adobe-import-capture-pair-1/`, records immutable JSON at the original
history and workspace raw-capture endpoints without reusing either. The v2
getter exposed observation aliases; v3 returns detached observations and retains
the earlier finding. Capture availability and JSON equality cannot by themselves
prove future reuse, mutation invalidation, source ownership or numeric identity.
The normal App, release and roadmap remain unchanged.

The actual paired-capture diagnostic now retains two byte-identical 28,652,283-byte
raw Fabric JSON files. Independent file review passes seventeen checks and parses
both complete files; full-resolution review confirms the broad A–H figure and
visible Unsaved status. History and workspace capture observations have different
revision/depth/lock states. All five recorded owner-reference comparisons are
true, but those observations do not authorize reuse. The original 30-second Open
timeout remains; later idle and the host's separate Saving status do not clear it.
The owned job finishes in 54.625 seconds with zero remaining owned processes.

A future one-shot import handoff must prove successful history publication and
account for derived metadata writes that do not advance the public revision. No
reuse is implemented. A separate normal-frozen24 staged Save check preserves
the original Open error, waits independently for idle, and attempts the actual
public download. Its preparation is not a Save or cold-restoration result. The
roadmap and release remain unchanged.

The separate staged normal-frozen24 run reaches a real public Save after later
idle. Its 69,681,414-byte download completes in 7,285.6 ms and retains a complete
native Fabric scene byte-identical to the live observation, the exact actual
source PDF, and no private history tokens. Five producer checks pass. The file
is pretty-printed JSON: its compact equivalent is 33,748,022 bytes; the larger
download is not evidence of a duplicated scene. These remain one-run observations,
with complete independent file review and cold continuation tracked separately.

The original Open timeout remains. The later acknowledgement wait has a recorder
selector error: browser chrome adopts its sole status control into the editor
document, while the new check searched only the outer page. Its Saved/Saved in
browser frames and later host status do not establish the unobserved key equality.
Keep the failed report and the separate independent selector correction. The
owned job finishes in 86.328 seconds with zero remaining owned processes and no
cleanup errors. A corrected iframe-first readonly observer has fourteen passing
finite controls and will be checked in a fresh-process Open of this exact Save;
that future result cannot retroactively qualify the warm key acknowledgement.
The evidence is in `adobe-v2-staged-public-save-1/` below the checkpoint root.

The actual normal-frozen24 Save now passes 31 independent file/custody checks.
Both parser paths preserve its complete ordered project. All 960 v2 text objects,
2,823 glyph/plane records, 344 paths, six images, 1,499 clip owners and seven
decoded payloads survive. Thirteen observed PDF-size fields and 59 nested
artifact references retain their actual sizes. This closes the observed v2 file
validation failure for this exact actual public download, with broader editing
and release qualification still open.

The first fresh-process project Open fails its canonical 30-second success-status
wait before any cold data is captured; its fitted figure and Opened toast do not
clear that failure. A separate staged cold attempt preserves the same original
timeout, then observes actual success and idle after 34,723.1 ms elapsed. It
retains the complete cold scene byte-identical to the actual Save/live scene,
exact original PDF bytes, and literal complete pdfSources/artifactRefs. The full
project comparison retains four capture-clock differences and two object-key
order changes; it does not claim complete project-byte equality.

The corrected iframe-first observer now records Saved with the exact current
nonempty key and ready/not-busy state in that cold run. This is a genuine current
key observation, not a durable transaction receipt or retroactive warm result.
The staged run finishes in 62.735 seconds under the unchanged 90-second owner,
with zero remaining owned processes. Six of seven producer checks pass; the
unchanged source raster fraction is 0.0309534272, above 0.025. The normal 10-second
Open predicate is not reached, and the original completion failure remains.

Full-resolution review finds the cold artwork and difference map byte-identical
to the earlier trial 7 baseline. The thin panel A connector remains absent and
Venn edges remain jagged; these are retained display defects, not cold data
drift. Evidence is in `adobe-v2-staged-cold-open-1/` and
`adobe-v2-staged-cold-open-2/` below the checkpoint root. The reviewed image
sampling correction is now isolated in frozen25, with two runtime-file deltas
and one finite test-profile adaptation over normal24. Its actual integration
controls and browser appearance/Save/cold checks remain next. Canonical runtime,
release and roadmap remain unchanged.

Frozen25 image integration passes its source controls under the 90-second owner
in 8.156 seconds, with no remaining owned processes. The exact retained original
17-case suite has sixteen passes and its one expected image-fill method identity
failure. The separately reviewed adapted suite has 165 passing Node entries,
including the prior 148; internal protocol controls are not added again. Initial
controls-driver admission gaps and their unrun HOLD remain preserved; the final
driver binds original source, loader, complete frozen source and every input
before and after execution, and rejects missing, cancelled or incomplete results.

The actual image-policy public attempt retains 344 editable paths, 960 native
texts, six images and zero opaque pages. Its real 69,682,990-byte Save completes
in 8,009.0 ms and matches the complete live Fabric scene literally. Exact source
PDF bytes and a genuine current-key Saved/idle observation survive. The owned
interval finishes in 74.171 seconds with zero owned processes. Seven of eight
producer checks pass; the source raster fraction improves from 0.0309534272 to
0.0288748391 but remains above 0.025. The original 30-second Open failure and
unreached normal Save-timing assertion remain recorded; a raw single duration
does not qualify the repeated performance budgets.

Full-resolution review finds the missing connector visible again and the severe
Venn stair-stepping resolved at this capture scale. The connector still differs
in contrast and raster column, so this is not exact source-pixel or physical
geometry acceptance. Every changed normal24-to-candidate pixel is within the
six declared image regions plus their one-pixel borders. About 95.2 percent of
the remaining source-significant pixels lie outside those regions; their cause
is not established by that localization. No AA waiver or raster-budget change
is made. The actual file audit and image-policy cold continuation remain next.
Evidence is in `adobe-image-sampling-integration-1/` and
`adobe-image-sampling-public-save-1/` below the checkpoint root. Canonical runtime,
selected Library release and roadmap remain unchanged.

The image-policy actual Save passes 38 independent file/custody checks. Its six
image payloads retain byte-identical PNGs and decoded pixels; all explicitly
checked text, geometry, clipping, paint and source properties match normal24.
The 28,834 raw cross-import field/order residuals are retained separately, without
a whole-scene normalization claim. Three display-font programs are retained with
matching hashes; this does not observe actual Canvas font selection.

The exact Save subsequently opens in a fresh Chromium process under normal25.
Seven of eight producer checks pass, with complete cold Fabric bytes equal to
the actual Save/live scene, literal source registries and all retained source
bytes, and a genuine current-key Saved/idle observation. The complete artwork
and source-difference PNGs are byte-identical to the actual warm captures. All
five fresh originals are reviewed; the restored connector and smoother Venn
survive, with their existing contrast/column and text/vector residuals.

The original 30-second project-status wait still fails; the separate staged
completion reaches idle after 33,050.1 ms elapsed. The same raster fraction
0.0288748391 exceeds 0.025, and the normal 10-second Open predicate is not reached.
The owned interval finishes in 61.438 seconds with zero remaining owned processes
and no cleanup errors. Evidence is in `adobe-image-sampling-cold-open-1/` below
the checkpoint root. Direct bundled PDF.js Canvas comparison is the next
diagnostic for remaining source differences; canonical runtime, selected Library
release and roadmap remain unchanged.

The direct bundled legacy PDF.js Canvas diagnostic completes in 8.250 seconds
under the 90-second owner, with five checks passing and zero remaining processes.
It renders the exact same source bytes at 1,224 by 1,584 pixels, without App
materialization or resampling. Its source fraction is 0.0290625825, also above
0.025. Direct PDF.js versus editable Canvas has only 1,290 significant pixels
(886 outside the prior image boxes). All 52,359 source-direct significant pixels
outside those boxes also occur in the source-native set; native adds 924.
Therefore the missing current-path thin-stroke display option cannot explain
most of this shared source mismatch. No font or AA-only cause is established.

The three observed embedded display-program hashes match actual saved program
bytes. Four FontFaces are loaded in the detached diagnostic, with the unembedded
Helvetica record and data-null system face kept distinct. This does not prove
which program paints every glyph or observe the editor's live font set. The
initial unrun recorder race/error-masking HOLD is retained; the corrected source
passes sixteen source checks and fifteen finite fault controls before dispatch.
Evidence is in `adobe-direct-pdfjs-canvas-1/` below the checkpoint root. A separate
outlined-glyph counterfactual is prepared but unrun; it changes only the explicit
disableFontFace flag and cannot qualify product behavior. Full V1 and roadmap
remain unchanged.

The separately reviewed disableFontFace:true counterfactual completes in
8.750 seconds under the same owner, with five producer and 21 independent
evidence checks. It changes only that requested renderer flag and its recorded
metadata; source bytes, scale, background, geometry and three observed embedded
program records remain exact. Its source fraction worsens to 0.0320592568,
versus default direct PDF.js 0.0290625825. Most default-to-outline significant
pixels lie outside the old image boxes; connector/Venn regions match the default.

All five fresh originals are reviewed. Both brackets in “Z-score β [c]” disappear
even though the renderer reports no warnings or errors. The unembedded Helvetica
record has no retained program. This is a concrete content regression, and the
outline flag is rejected as a product correction. Its successful diagnostic
execution does not qualify source fidelity, font substitution, an AA-only cause
or the editable route. Evidence is in `adobe-direct-pdfjs-outline-1/` below the
checkpoint root. No font-policy/runtime change is promoted. Import completion
performance remains the next product issue; roadmap and release remain unchanged.

A parser-owned metadata candidate now passes its offline measurement and source
integration checks. Only fresh records created by its captured, no-reviver native
JSON parser acquire private identity; caller objects cannot supply that identity.
The existing cooperative copy and serializers are unchanged. Intrinsic data
properties at bootstrap remain an explicit assumption, with the original clone
expression retained when later descriptors or functions differ.

The corrected owned measurement finishes in 28.531 seconds with no remaining
processes: seventeen original cooperative controls, 23 independent semantic
controls and six ordered-wire-exact measurements pass. Four realistic trials use
the actual 960 text-source metadata records. Their parse/metadata/copy stage totals
are 3,684.7/4,133.4 ms for the baseline and 3,318.8/3,255.5 ms for the candidate.
Metadata preparation itself becomes slower; its longest individual candidate
copy reaches 14.7 ms. The two whole-wire trials are upper-bound diagnostics only.
The initial recorder failed before any workload timing and remains retained; it
is not candidate performance evidence. No public Open gain follows from Node.

Normal26 freezes 2,414 inherited manifest entries plus one explicitly additional
test, with eighteen cumulative overrides and only two runtime changes from
normal25: precision and the SVG materializer. All 188 adapted controls pass; they
include the prior 165 plus the 23 parser cases. The separate original image
profile retains sixteen passes and its known identity failure. The owned
integration interval finishes in 8.047 seconds with zero remaining processes.
Evidence is in `adobe-parser-owned-json-1/` and
`adobe-parser-owned-json-integration-1/` below the checkpoint root. One normal
public-browser diagnostic is prepared with unchanged guards and budgets; its
actual result is still pending. Canonical runtime, release and roadmap remain
unchanged.

The normal26 public attempt completes its owned interval in 75.063 seconds
without deadline or cleanup failure and leaves zero owned processes. Seven of
eight producer checks pass. Its actual 69,682,966-byte Save equals the complete
live Fabric scene literally, retains the exact source PDF and has a genuine
current-key Saved/idle observation. Forty-one independent file/custody/pixel
checks pass within that bounded scope. All 28,818 raw cross-import residuals
remain retained separately; no new geometry, paint, text or source invariant
change was found. All six fresh originals and both references are reviewed.
The artwork and source-difference PNGs are byte-identical to normal25; decoded
artwork pixels also match exactly, including both beta-label brackets.

The original 30-second completion wait still fails. Its retained existing
observer reports 16 main-thread tasks over 100 ms, a longest task of 2,357 ms
and a 2,695.8 ms maximum event-loop gap. The separate staged idle sample is
38,553.4 ms after that observer began. These are distinct intervals; no speedup
is inferred from earlier unmatched runs. The same 0.0288748391 source fraction
fails 0.025. Raw single-Save duration is 7,449.4 ms; the ordinary 10-second Save
assertion remains unreached after raster failure. Both independent reviews
retain their overall HOLD while explicitly recording bounded unchanged data
and appearance. No cold/edit or durable browser-store claim is added.

Evidence is in `adobe-parser-owned-json-public-save-1/` below the checkpoint
root. A separate CPU diagnostic is prepared over exact normal26, without any
App change or full-project getter. It will sample through separately staged
idle and stop before inventory, screenshots and host observations. Its purpose
is remaining-work attribution, not normal performance qualification; the
profile has not run at this checkpoint. Canonical runtime, selected release,
full V1 status and roadmap remain unchanged.

The exact normal26 CPU diagnostic completes in 46.984 seconds under the
90-second owner, with zero remaining processes. Sampling stops after separately
staged idle and before inventory, screenshots and host observations. Actual
344 editable paths, 960 text objects, six images and zero opaque pages remain.
The full editor is unobstructed and honestly Unsaved because this interval
performs no Save. Nineteen independent capture/graph/source checks pass.

The immutable profile contains one negative 11-microsecond interval and 238
per-node hit-count discrepancies. The strict nonnegative-interval analyzer
fails before producing a summary; that failure is retained. A separate analysis
uses all 25,417 ordered samples without altering intervals or using reported
hitCount fields. Fourteen independent comparison checks pass. Anonymous merged
frames disclose all script IDs. Function rankings are sample frequencies only,
not durations, CPU-time percentages, call counts or a benchmark improvement.
Native capture, JSON copying, shared-import scanning and geometry snapshots
remain active hotspots; no weighted timing attribution is qualified. Evidence
is in `adobe-parser-owned-json-cpu-1/` under the checkpoint root.

An iterative shared-import scan is now an unpromoted source experiment. Forty-six
ordinary traversal, mutation, iterator and error controls agree with the original.
A modified shared Generator.next accessor distinguishes the implementations and
can throw only in the candidate; unrestricted compatibility therefore remains
HOLD. Its original candidate, review and counterexamples are retained unchanged.
One offline actual-scene comparison is being prepared under an explicit fresh,
hook-free Node/native-intrinsic precondition with descriptor checks around module
loading and every trial. That measurement-only disposition neither resolves the
compatibility boundary nor authorizes browser dispatch or product promotion.
See `adobe-cooperative-import-scan-1/`. Canonical runtime, release, full V1 and
roadmap remain unchanged.

The restricted scan experiment now completes in 9.047 seconds under the unchanged
90-second owner, with zero remaining processes. All seventeen original cooperative
controls pass. Four complete actual-scene trials preserve input identity and the
exact 28,652,650-byte ordered wire. The baseline scan calls take 621.1 and 771.2 ms;
the candidate calls take 278.4 and 246.1 ms. Parsing and input/output comparisons
are measured separately. All fifteen intrinsic-stability checkpoints pass.
The largest observed yield interval is 8.65 ms for the candidate and 12.78 ms for
the baseline; the configured eight milliseconds is not a hard synchronous bound.
These four exploratory Node trials do not establish browser improvement, repeated
performance or unrestricted compatibility. The known generator counterexample
remains HOLD. Nineteen independent measurement checks pass. The production-boundary
review confirms the exported compactor admits custom callbacks and getters;
entry-only guards cannot cover changes during execution, and restarting can replay
side effects. Keep this scan candidate offline; no source promotion follows.

The next source experiment targets native layout snapshots. A legacy import-only
deferral preserves ordinary tiny fixtures but fails three native reentrant/error
controls and has no positive affected-stack evidence in the actual profile. It
remains rejected. All 2,667 unweighted samples below `_seed` instead belong to
current-plane subscription or the two later finalization passes. Those are sample
frequencies, not call counts or durations.

The revised current-plane candidate defers only the initial snapshot of nonempty
artwork groups that the existing complete-hierarchy pass will seed before return.
Clip-only and empty groups keep their eager snapshot. The first draft missed
clip-only managers because the finalizer traverses artwork children, and is held;
the subsequent empty-group correction is retained separately. No finalizer, App,
geometry cache, capture, serializer, ownership check, cancellation or await changes.
Twenty-four finite native construction checks and six independent method-refusal
checks pass. They compare complete geometry/frame/member state as well as ordered
wire, exercise actual early/late cancellation and preserve the fixture-only cold
precision installer boundary. These are not actual Adobe/browser measurements.
See `adobe-plane-construction-seed-1/`. Normal27 now freezes the sole plane-module
delta across 2,415 declared files, eighteen cumulative overrides and 1,587 source
pins. All 280 retained adapted entries pass: the prior 188 plus 92 existing affine,
clip, source-text and isolated-child entries. The separate original image profile
retains sixteen passes and its known identity failure. The owned interval finishes
in 7.344 seconds under ninety, with zero remaining processes and stable bindings.
Thirteen independent execution checks confirm the actual freeze and test logs.
The public Open/Save diagnostic is prepared with unchanged commands, waits,
source-fidelity predicates and separate performance classification; its actual
result is still pending.
Canonical runtime, release, full V1 status and roadmap remain unchanged.

The actual normal27 public interval now finishes in 72.781 seconds under the
unchanged ninety-second owner, with zero remaining processes or cleanup errors.
Seven of eight producer checks pass. The 69,682,988-byte Save equals the complete
live Fabric scene literally, retains the original PDF and acknowledges the actual
current key as Saved/ready/not-busy. Counts remain 344 editable paths, 960 text
objects, six images, 6,181 groups, 1,499 clipped objects and zero opaque pages.
Artwork and source-difference PNGs are byte-identical to normal26; decoded artwork
pixels match exactly. All six fresh originals are independently viewed.

The original thirty-second completion wait still fails. The existing observer
records fourteen tasks over 100 ms, a 2,187 ms maximum task and a 2,546.9 ms maximum
loop gap. Separately staged idle is observed 37,363.7 ms after that observer began;
this is not a paired Open improvement. The unchanged source fraction remains
0.0288748391 above 0.025. Raw Save duration is 7,920.7 ms, with the ordinary
ten-second Save assertion unreached after raster failure. The isolated source
change preserves the observed data/display interval but does not qualify import
completion, responsiveness, source fidelity, new editing/cold or full V1. Evidence
is in `adobe-plane-construction-seed-public-save-1/`. All 41 independent file checks
pass within the bounded data/display scope; 28,816 raw cross-import residuals are
preserved separately. The independent visual review also records unchanged
appearance while retaining the original overall HOLD. Canonical runtime, selected
release and roadmap remain unchanged.

The following browser scheduling diagnostic changes no runtime source. Exact
normal27 clone and metadata-scan APIs process the complete actual saved scene in
eight trials, comparing 128 and 2,048 steps with the existing eight-millisecond
check and literal App yield callback. Every output retains the exact ordered
28,652,661-byte wire. Each clone has 107,650 distinct corresponding objects; each
scan returns its original input. The owned interval completes in 18.078 seconds
under ninety, with no remaining processes or recorder/cleanup errors.

Exploratory mean clone times are 695.30 versus 648.50 ms; scan times are 916.30
versus 876.55 ms. Both pairs of trial ranges overlap. Per-trial callback resets,
measurement-wrapper overhead, changing clock-check cadence and uncontrolled
allocation/GC prevent attribution of the differences solely to scheduling.
Observed work phases reach 23 ms despite the eight-millisecond check. Twelve
independent execution checks and a separate method/result review support these
bounded observations. Keep the App stride at 128: these modest, variable results
do not explain slow public Open or justify a caller change. Evidence is in
`adobe-capture-batch-cadence-1/`. No new UI, latency, memory, repeated-performance
or V1 qualification is claimed; existing HOLDs and roadmap remain unchanged.

The subsequent exact-normal27 timeline is complete after correcting trace
transfer. The first attempt remains incomplete: its uncompressed stream exceeded
the recorder's eight-second bookkeeping check, despite clean process cleanup.
The fresh retry retains the raw gzip stream and exact decoded JSON, uses fewer
trace categories and a fifteen-second post-collection transfer check within the
same ninety-second process owner. Original public completion and separate idle
waits are unchanged. The retry completes in 55.719 seconds with zero remaining
processes, no reported trace loss/fullness and stable source/input bindings.

The 37,174.425 ms marked interval contains 91,812 recognized, nonoverlapping
whole Chrome main-thread tasks; sixteen exceed 100 ms and the largest is
2,111.532 ms. Whole tasks can straddle the marks, and nested events are not
additive. Separate actual callback records include about 350 ms of Fabric
drawing and 298 ms in automatic viewport refit, not preview generation. CPU
rankings remain counts-only: ten negative intervals and 253 per-node count
disagreements are preserved. Fifteen independent execution/analysis checks and
the full-resolution screenshot review support bounded diagnostic continuity.
There is no new actual Save, normal-timing or source-fidelity acceptance.
See `adobe-current-open-timeline-1/` and `adobe-current-open-timeline-2/`.

The next App candidate targets that automatic refit callback. Its existing
settled-resolution policy can avoid forcing a full redraw when the backing
width, height and ratio remain unchanged through stage update. Manual viewport
commands and changed backing stores keep immediate painting. An initial finite
control caught queued rather than immediate first-backing paint; V2 adds a
local three-scalar comparison and retains that failed source/run unchanged.
All thirteen paired VM cases pass, with fake DOM/Canvas scope explicit. The
existing owner cases and zoom checks also pass after maintaining their fixture
dependency and option-aware source assertions. Frozen normal28 declares 2,415
files and 21 cumulative overrides: App is the only runtime change, with two
explicitly maintained test fixtures. Its 32 ownership checks, four zoom checks
and thirteen paired VM cases pass against the frozen files. The independent
execution audit confirms the complete source and input bindings.

The actual first idle Open view shows the complete scientific figure before any
manual viewport command or artwork-render helper. Both automatic desktop resizes
retain identical 816-by-1,056 artwork pixels with zero newly recorded full renders.
Manual Reset, Zoom and Fit each paint; the observed backing ratio changes from
1 to 1.18 and back to 1. All sixteen original page/native captures are reviewed.
The selected PDF root has much larger bounds than the page, so those captures
cannot qualify its off-page selection handles. A separate real, pointer-drawn
rectangle tests visible common controls on the same frozen App: both automatic
resizes preserve pixels, six-pixel corners and 22-pixel touch areas, and dragging
the actual bottom-right handle enlarges the selected rectangle. This does not
qualify PDF-root or nested PDF selection geometry. All ten supplementary
originals are independently reviewed. Native edge shading differs between the
post-drag and forced-Fit captures; the required automatic-resize pairs match
exactly, and no cause or new regression is inferred from that separate difference.

The fresh normal28 public Save also passes 41 independent bounded file checks.
Its complete 28,652,646-byte saved Fabric scene equals the live observation
literally; source bytes, 344 paths, 960 text objects, six images, 6,181 groups and
1,499 clips survive. Artwork and source-difference PNGs match normal27 exactly,
and all seven fresh originals are reviewed. All 28,815 raw cross-import residuals
remain retained; no normalized whole-scene equivalence is claimed.

The original thirty-second completion wait and fixed source fraction still fail.
Fourteen observed tasks exceed 100 ms, with a 2,115 ms maximum task and 2,487.1 ms
maximum loop gap. Separately staged idle at 36,430.4 ms does not reverse the
original failure or establish a paired gain. Raw Save duration is 7,954.1 ms;
the ordinary ten-second assertion remains unreached after the same raster failure.
No new cold, PDF editing/history, export, physical-glyph, memory or repeated
performance acceptance follows. Evidence is in `adobe-automatic-refit-render-1/`,
`adobe-automatic-refit-integration-1/`, `adobe-automatic-refit-viewport-1/`,
`adobe-automatic-refit-visible-handles-1/` and `adobe-automatic-refit-public-save-1/`.
Canonical runtime and the selected release remain unchanged. The roadmap remains
the same: resolve the original Open/runtime budgets and complete PDF authoring
qualification before matched delivery.

The subsequent complete normal28 diagnostic narrows the largest remaining Open
task to work resumed after the final imported-page preparation yield. Its
2,182.025 ms task contains a 2,181.994 ms microtask interval, and its timer
registration precedes final layout, canvas insertion and UI synchronization.
This does not attribute that duration to any one operation. Independent analysis
and original screenshot review pass within diagnostic scope; the original
thirty-second completion failure remains. The initial added-stack capture lost
data and is retained as incomplete; a distinct capacity-only retry completes
under the unchanged ninety-second owner. Evidence is in
`adobe-current-open-microtasks-1/` and `adobe-current-open-microtasks-2/`.
The subsequent direct-call probe in `adobe-current-open-seed-spans-1/` confirms
that layout snapshot capture contributes to two long tasks. In the instrumented
run, seed-call spans occupy a 1,283.6 ms union within a 2,149.523 ms task, and
1,326.0 ms within another 1,346.003 ms task. A single call lasts 494.8 ms, so
yielding only between calls would leave a substantial block. All 17,049 calls
are retained, and independent raw analysis reproduces the task/span joins.
The probe's temporary methods are restored before inventory and the fresh
editor screenshot matches its reference byte for byte. Its initial restoration
defect was caught and corrected before any browser run; failed controls remain
preserved. No product behavior change or normal timing pass follows.
The other fifteen recognized long tasks contain no recorded seed spans in this
capture, so this is one performance target rather than a complete Open solution.
The next bounded implementation should address work inside recursive geometry
capture while preserving native numbers, clips, membership and authoring checks.
The roadmap and selected release remain unchanged.


## 18 October: natural painting after authoring actions

The original visible alignment failure is reproduced before correction: the
object model completes in 39.4 ms, but the artwork buffer stays unchanged through
the one-second diagnostic interval. A live-compound creation case independently
shows retained blue operands where the orange union result should appear. Both
failures and their source bindings remain preserved.

Numeric alignment/distribution/transform completion and live-compound
create/edit/Done/Cancel now request artwork painting after rebuilding selection.
The existing selection-only optimization remains in place. Internal compound
mode changes retain the previous result while computing, without an extra
operand-view paint. The live-text fixture also exposed a separate native-input
position error at reduced canvas zoom. The input now follows the displayed caret
and stays inside the editor viewport, preserving the authored text geometry and
font values. Typing no longer scrolls the complete editor out of view.

The first full repaint matrix retains a real Library Undo deadline failure:
correct paint appears at 255.8 ms against the unchanged 250 ms limit. A separate
CPU sample points to repeated Library search suggestions inside restoration.
The correction reuses the existing suggestion view only while the loaded catalog,
pack, query, effective filters and rendered content stay unchanged. Favorites and
Recent retain their respective lists; irrelevant lists do not invalidate All.
Pack arrival, source replacement and externally changed markup still rebuild the
view. Real search implementation tests preserve recommendation order, counts and
fields, including protected biological query behavior.

The final maintained `qa:action-paint:release` invocation passes all 24 combinations
of three desktop widths, two themes and four fixture families. Its 156 actions
retain natural paint within 250 ms and at least 80 ms of continuous correctness;
all 24 intentionally stale negative controls fail as required. Maximum observed
paint is 138.1 ms for ordinary/group actions, 81.6 ms for compounds/live text,
103.7 ms for Library part/history actions and 218.8 ms for the genuine imported
heatmap root movement. Library Undo/Redo paints in 66.6–103.7 ms in these six
cases. These are bounded observed intervals, not repeated p50/p95 performance
qualification. All owners finish cleanly within 14.8 seconds of their original
90-second limits, with frozen source inventories and stable controllers.

Early group screenshots preceded the existing deferred full Properties refresh.
A separate read-only observation now requires the visible object title, context
type and isolation controls to agree with the actual selection within the same
250 ms action deadline before page capture. Final agreement is observed at
164.6–186.3 ms; artwork timing and original lower buffers remain separate.
No extra render or unrelated action can rescue either check. The prior wrong
scroll-origin and early inspector captures remain preserved for review.

The same final App passes 69 JavaScript tests, 38 existing Python repaint/history
checks and the 238-check Library discovery web workflow. The imported heatmap
case retains the explicitly compared raw local fields, ordered membership,
parents, clips, paths, text and paint apart from the requested root translation;
its genuine source bytes remain unchanged. This does not qualify the larger
Adobe root bounds, source fidelity, physical glyphs, complete saved-file
continuation or the broader PDF corpus. Evidence is under `qa_artifacts/ap-final1/`,
with the earlier failure in `ap-matrix1/` and diagnostic profile in `ap-prof1/`.
The commands and observation rules are documented in
[Public scientific PDF corpus checks](PDF_CORPUS_PUBLIC_QA.md#natural-action-to-paint-regression-18-october-2026).

The independent execution audit passes 1,021 checks, including a fresh hash of
all 2,415 frozen files, exact Library history pixels and the declared PDF field
comparisons. Two independent reviewers inspect all 60 declared critical page
originals at full resolution across the six desktop/theme cases, with no remaining
visual HOLD. The earlier rejected captures and latency failures remain intact.
These reviews qualify the declared repaint cases rather than all PDF authoring.

The selected release remains unchanged. The roadmap remains the same: resume the
recursive geometry-capture performance work while preserving complete native
numbers, frames, membership, clips and editing behavior, then complete the shared
PDF qualification and matched delivery requirements. This authoring checkpoint
does not turn the original Open failure into a performance pass.


## 19 October: canonical source reconciliation and recursive import capture

The nine cumulative PDF runtime changes previously retained only in normal28
are now integrated into the canonical Windows-native working tree, together with
their reviewed tests and leading-space observation helpers. Recent repaint fixes
are retained. [The source integration map](PDF_SOURCE_INTEGRATION.md) records the
exact scope, source bindings, current controls and excluded experiments.
The selected release remains unchanged; full V1 and the roadmap remain open.

The final implementation keeps cooperative recursive capture on detached imports
and restores the literal synchronous editing routines. Focused controls pass
54/54, with 17/17 SVG controls and the real native-tree fixture passing. In the
final quiet e/s/s/e comparison, candidate Open is 29.477 seconds on its first
attempt and fails the original 30-second completion wait on its second. Baseline
is 26.267/28.733 seconds. All attempts exceed the retained 10-second budget;
lower observed maximum task lengths do not establish an overall speedup or
consistent completion. Later staged idle does not rescue the failed Open.

All four recorded native inventories agree under the declared runtime-ID/parent
normalization, and their untouched first-idle PNGs are byte-identical. Corrected
heatmap fixtures pass natural painting at three desktop sizes and independent
full-resolution review of the complete matrix, axes and color scale. Page width
and public Fit are setup before the unchanged 48 px movement observation.
Historical failures remain preserved. The exact final timing, helper provenance,
visual scope and open requirements are recorded in the source integration map;
this checkpoint does not close full V1 or change the selected release or roadmap.