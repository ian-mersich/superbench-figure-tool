# Cell Architecture & Transport — original asset review

Prepared 7 October 2026. Owner: the Figure asset chat.

## What is ready

Sixteen original editable drawings expand the interactions available for cell
architecture and intracellular transport. These complement the existing generic
cytoskeleton, organelle and vesicle drawings.

| Biological use | New assets |
| --- | --- |
| Cell–cell contacts | Tight Junction; Adherens Junction; Desmosome; Gap Junction |
| Cell–matrix attachments | Focal Adhesion; Hemidesmosome |
| Cargo movement | Kinesin Cargo Transport; Cytoplasmic Dynein Cargo Transport |
| Vesicle coats and docking | COPII Vesicle Budding; COPI-Coated Vesicle; Trans-SNARE Complex |
| Endosomal sorting | Multivesicular Endosome; Endosomal Recycling Tubule |
| Autophagy and organelle interactions | Autophagosome–Lysosome Fusion; Importin–Cargo Nuclear Import; ER–Mitochondrion Contact Site |

Each drawing has three to five independently recolorable regions and ordinary
editable SVG primitives. Search terms, primary references and biological limits
are retained in the pack. The drawings are illustrative; they are not structures
at atomic resolution or measured observations.

## Scientific and original-image acceptance

Primary figures were inspected before geometry was authored. The merged science
record distinguishes inspected figures from additional text-only support. The
SVGs were constructed afresh; source pixels, vector components and structural
coordinates were not incorporated.

An independent reviewer inspected every one of the 48 individual treatment
boards: sixteen assets in Soft color, Cut paper and Technical ink. Each board
contains a 256 px rendering and native 64 px thumbnails on light and dark
backgrounds. All 48 passed after corrections. The overview is for navigation
only and was not used for individual approval.

Corrections made during review:

- Removed obstructing COPII crossbars so cargo and the inner coat remain visible.
- Kept the paired SNAP helices visibly above the target membrane; only the
  membrane-anchored Q helix enters it in the generic trans-SNARE drawing.
- Preserved a finite, continuous recycling-tubule lumen and shortened the
  illustrative cargo stem so it does not appear to plug the lumen.
- Drew two distinct mitochondrial membrane bands with continuous inner-membrane
  folds, separate from the ER at the contact site.
- Darkened the intraluminal-vesicle region so the topology remains clear in
  Cut paper.

The canonical validator passes all sixteen vectors and their exact region,
provenance and draft-rights records. Six Python tests and two catalog tests pass,
including aliases for all sixteen concepts. The prepared browser runner parses
and its six complete-payload comparison guards pass offline.

## App integration and release status

Registered in the shared Figure/Present source library on 8 October 2026. Actual Library insertion, recoloring, child editing, Undo/Redo, SVG export, Save/cold Open, source/web light/dark layouts and Present insertion remain pending.

The prepared UI runner retains the full 48-instance functional fixture and a separate bounded four-asset document for readable authoring screenshots. It is saved at `core/scripts/check-figure-cell-architecture-browser.py`; it has not run.

All sixteen assets remain `FS-ORIGINAL-DRAFT`, with public distribution disabled
and no selected public license. Scientific/image acceptance does not grant a
public reuse license.

The eight-pack source library now has 319 concepts and 346 authored SVG styles, including 52 drafts. Scenes remain at twelve. Figure/PDF v1 scope and milestones remain unchanged; the next step is focused in-app qualification.

## Scientific records

The [science record](../../scripts/cell-architecture-transport-science.json) retains the primary references, descriptions, search terms and biological limits. [The pack](../../assets/scientific-packs/cell-architecture-transport/asset-pack.json) retains the editable regions and original draft status. Individually reviewed originals and their exact source/image bindings remain in the active task evidence until browser qualification is completed.
