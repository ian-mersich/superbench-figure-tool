# Inspector surface — 2026-11-07

**Status:** Qualified source UI checkpoint, based on delivered beta.29. Combined integration, versioning, packaging, activation, and publication remain with the coordinating chat.

## Product surface

The right Inspector has exactly three views: **Appearance**, **Properties**, and **Layers**. Appearance contains controls for fill, line, text, opacity, and supported effects. **Saved colors** is a disclosure within Appearance, not a fourth view. Properties begins with selection geometry and then shows controls that depend on the selected object. Additional options and detail sections remain expandable where the control supports them. Layers keeps object selection, naming, visibility, and lock controls together.

Simple and Advanced use the same Inspector panel. The panel can be docked or detached without replacing its contents or changing the selected object. The View menu exposes **Detach Inspector** and **Dock panels**; these call the existing rail placement actions. This path remains available in compact Core hosting, where host chrome hides the rail title bar. Clearing the selection leaves the Inspector open and its current view selected, so the user can continue with Saved colors, Layers, or another object.

The Library starts closed and can be reopened from its toolbar control. Inspector visibility and placement are independent of the Library. Figure and Slidedeck are workspace views alongside the document tabs. **Project slides** opens slide browsing beside the canvas; it does not change which document tabs are open.

## State and compatibility

Selection geometry and object-specific edits continue through their existing authoring controls and document history. Switching Inspector views, changing Simple/Advanced, or docking and detaching panels changes workspace state; those actions do not create artwork edits. Existing native object ownership, selection, and history behavior remain in place.

Saved Figure layout preferences must continue to restore panel visibility and exact floating rectangles. Migrate the legacy `style` tab preference to `appearance`, and the legacy `swatches` preference to the Saved colors disclosure within Appearance. Keep the existing swatch/color library, saved appearance styles, and Drawing Styles 1–4 intact. Preserve rail geometry while migrating view names. Do not treat named Graphic Styles or drawing art styles as aliases for the Inspector view.

The bundled Help catalog is current with this surface: beta.29, catalog date 2026-11-07, and updated Inspector/navigation articles for Appearance, Properties, and Layers.

Styles is reserved for reusable presets; it is not an Inspector view. Existing
Graphic Styles and Drawing Styles 1–4 retain their distinct supported functions.

## Qualification and next step

The current integrated controller is `qa_artifacts/inspector-20261107/check-integrated.py`. It uses the retained mixed scientific Figure, one real long-name drawing, an editable label, and a native line. It checks unchanged authored artwork/history across layout changes and captures both floating and docked Inspector states. Its eight full-window captures cover edited and unedited Appearance in Simple and Advanced, Properties, Layers, and docked Appearance in Simple and Advanced.

The final six-resource source passed 139 browser checks across five closed jobs:
three actual Core desktop cases (1280×800 light, 1440×1000 light, and 1920×1080
dark), a mixed editing and Save/Open case, and a saved-preference case. The
mixed case saved an actual Figure file and opened it in a new Chromium process;
the first cold image precedes inspection or view changes. The preference case
restored the exact floating rectangle and Layers view, then cleared selection
with the canvas Escape shortcut and verified that the Inspector remained open.
The 39 original full-window captures have separate independent visual review.
Targeted preference, color, preview, accessibility, Help, and source-export
checks passed 42 tests. The acceptance records and literal execution inputs
are retained under `qa_artifacts/inspector-20261107/`.

Earlier failed runs and visual HOLDs remain separate records. In particular,
the corrected no-selection setup focuses the existing canvas viewport before
Escape; an empty selection array is not a clearing action. This correction
changes the QA setup only. No comparison policy was relaxed.

This slice adds no new artwork representation or native editing owner. The
mixed-file result covers this retained scientific composition and its supported
line, editable text, geometry, saved color, and effect edits. Broader scientific
PDF, typography, export, and performance qualification remain separate. The
source checkpoint does not change the delivered beta.29 installation.

This advances the approved Inspector-first sequence. Inverse contour operations,
selection and PDF parity follow, then typography/export/reimport. Sustained
dragging remains behind those priorities; this slice makes no performance claim.
