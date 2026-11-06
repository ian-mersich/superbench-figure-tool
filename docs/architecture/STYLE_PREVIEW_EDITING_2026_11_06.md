# Figure Style and drawing previews

Figure uses one right-hand rail with Style, Properties, Colors and Layers views.
The compact Style controls work in Simple and Advanced. Switching layouts keeps
the visible rail, selected view and useful floating geometry. Library starts
closed, including when an older saved layout left it open. Its saved size,
position and tab remain available; an explicit show or hide lasts through
selection and layout changes during the session.

Style names the supported edits directly: Line width for lines, Text size (pt)
and Bold for text, and named part colors for Library drawings. Bold changes font
weight. Supported PDF labels keep their editable text and original glyph source
when their size changes. The redundant canvas Source badge stays off editable
PDF labels so it cannot cover neighboring scientific marks; other warnings and
the original source metadata remain available. Capability checks still belong to the existing text
and selection owners; this change adds no font backend or text-outline control.

Drawing previews have a local appearance draft. Palette and part-color changes
update the preview image. Insert or Apply colors commits the exact displayed
draft through the existing native asset commands and history. Close or Escape
cancels it. Catalog records, other drawings and the current figure remain
unchanged until commit. The preview controller clones draft values and blocks
commit until the latest image has decoded. App callbacks derive preview SVG
without changing shared records or cached prototypes.

For an existing drawing, Apply colors stages a native clone through the same
color owner used on the canvas. It retains edited geometry and component paint,
checks the target fingerprint, then publishes one native history step. Variant
replacement retains its existing matching-copy and edited-drawing safeguards.
Full geometry editing stays in the main editor's Edit parts workflow.

The user-sized Style panel has one inner scroll owner. Controls align at the top;
Change drawing and Edit parts share a row so a complete first part-color input
fits in the compact floating panel. Scientific details in Preview are optional.

## Verification and scope

`scripts/check-style-preview-browser.py` reuses the maintained Library,
selection, PDF and action-paint helpers. Its separate journeys cover preview
drafts and native commits; real line/text styling and a Slidedeck return; a
genuine PDF-label size change; and populated desktop layouts with fresh and saved
preferences. Save journeys download actual files and open them in a new Chromium
process. Cold screenshots precede model inspection and view changes.

Ordinary artwork uses the established authored/native comparisons. Its explicitly
marked, derived area-text frame clip may receive a generated ID/name on restore;
the existing selection comparator retains its geometry and all authored IDs.
The PDF journey uses the strict existing comparison, excluding only transient
selection-isolation metadata. Original PDF sources and artifact references remain
exact. Serialized byte-size estimates are diagnostic metadata, not source bytes.
Raw comparison operands and failed epochs remain available in task QA output.

This is a source UI slice. Core-host composition, installed native qualification,
release packaging and publication belong to the coordinating delivery. Preview
node editing, new typography engines, native PDF-stream mutation and export
fidelity claims are outside this change. The roadmap remains the same: qualify
the combined accepted Figure changes through the existing delivery sequence.
