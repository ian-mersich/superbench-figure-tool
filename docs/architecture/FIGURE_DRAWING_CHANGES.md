# Changing a Library drawing

The Library always inserts new artwork. Its cards, favorites, alternate-form
choices and Preview action do not acquire a persistent replacement mode.

Select one bundled drawing and choose **Change drawing…** in Style, the detailed
Inspector, or Presentation’s Format controls. The focused chooser provides a
biological search, drawing/view list, large preview, scientific limitations and
named editable parts. Closing it or pressing Escape leaves artwork and history
unchanged and returns focus to its opener.

The default changes only the selected drawing. When other unlocked, unmodified
copies of the same Library drawing exist on this figure or slide, a counted
checkbox can include them. Locked and individually edited copies are excluded.
The confirmation button reports the resulting count. Opening the chooser again
clears the checkbox.

Changing a drawing replaces its contents. If the selected drawing has edited
paths, moved/deleted components, individual component paints, clipping or
appearance effects, an explicit acknowledgment is required before those edits
can be discarded. An unavailable source is treated as edited. Semantic Part
colors and palettes are compared against the corresponding colored source and
do not by themselves require this acknowledgment. Same-concept changes carry
compatible named part colors; other concepts retain their chosen palette.
Existing alternate-form shortcuts also open this review for customized artwork.

Custom drawings and My Assets are edited with the canvas tools. Merely having
scientific metadata does not expose Change drawing: the selected object must
be a bundled scientific-asset group with an existing catalog identity. Nested
drawings retain the existing requirement to exit group editing and release their
containing group before changing the intact drawing.

The shared vector importer, canvas transform snapshot, palette/part-color owner
and history serializer perform the change. Object identity, layer/scene/selection
metadata, position, dimensions, rotation, reflection and stacking order are kept.
One Undo restores the previous customized artwork. No rasterization is added.

Source comparisons are local to the chooser and reuse expected content for
matching appearances. They do not add a saved baseline or change file schemas.
An in-memory session owns the selected document and source object. Before
applying and again after asynchronous SVG preparation, the operation rechecks
the document generation, session, target references and complete target records.
A stale operation cannot alter reopened artwork or clear a newer chooser.

## Unattended checks

```powershell
node --test tests/scientificAssetDiscovery.test.mjs
py -3 scripts/check-library-discovery-browser.py --route web
py -3 scripts/check-library-discovery-browser.py --route direct
```

The existing Library runner covers the three desktop widths in light and dark,
selected/default and optional matching-copy changes, edited-part acknowledgment,
locked/edited exclusions, custom metadata, cancel/focus/history, palette and part
colors, Figure/Presentation switching and actual downloaded native files opened
in fresh browser contexts. The deferred mutation case calls the same application
command directly because chooser previews normally cache its source first; it
then uses host tab activation while the modal is busy. No replacement semantics
are reimplemented by the test. Output belongs under the canonical ignored
`qa_artifacts/` directory. Selected public and installed releases remain unchanged
until this source is qualified and promoted as one paired release.
