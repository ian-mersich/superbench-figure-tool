# Core Biology nucleic-acid revision — 2026-10-11

This record describes the first October 11 artwork revision. The subsequent [RNA artwork revision](RNA_ARTWORK_REVISION_2026_10_11.md) retains these three drawings and adds four RNA redraws with a separate receipt and current audit. The catalog, audit and receipt described below remain preserved as the preceding release; the unchanged-file counts refer to this first revision.

This revision replaces three existing drawings in Superbench Figure Tool: the two DNA Double Helix styles and Chromatin Loop. The Core Biology pack still contains 108 styles and 90 concepts. Its stable asset IDs, SVG paths, style families, color-region IDs, labels, default colors, and CC0 license remain compatible with the preceding release.

The DNA drawings now use two crossing ribbons with twelve connected base-pair marks and short terminal caps. The chromatin drawing uses one continuous fiber with nine nucleosome-like beads placed evenly along it. These are generic biological schematics; they do not establish a nucleotide sequence, exact molecular structure, nucleosome occupancy, or a loop-extrusion mechanism.

The workspace owner authorized these three redraws and had previously allowed unrestricted reuse of the original assets. The new audit carries every historical owner, license-selection, and source record forward unchanged and adds the October 11 redraw and owner-authorization records. All three redraws remain under CC0-1.0. This revision changes neither the application-code license nor the treatment of imported third-party material.

The July 20 catalog, release audit, CC0 notice, and three predecessor SVGs are preserved exactly under `assets/scientific-packs/core-biology/revisions/2026-07-20/`. The other 105 asset records and SVG identities are unchanged. The historical July 20 identity pins remain in the validator, alongside a separate exact October 11 catalog/audit/receipt pin set. A historical release can be reconstructed from the snapshot and the 105 unchanged files without rewriting its original identity.

Three color-paint bindings change explicitly:

| Asset | Region | Previous paint | Current paint |
| --- | --- | --- | --- |
| DNA Double Helix | `backbone` | Stroke | Fill |
| DNA Double Helix — Thin line | `backbone` | Stroke | Fill |
| Chromatin Loop | `histone` | Implicit fill and stroke | Fill |

The independent outline region remains available. These bindings let each ribbon or bead use one outlined primitive while its fill and outline can be recolored separately. Existing saved artwork retains its embedded vector content; new insertions use the revised drawings.

The revision is recorded in `revision-2026-10-11.json`; the current rights audit is `license-release-audit.json`. The deterministic audit generator reproduces the latter from the current catalog, source records, SVGs, and revision receipt. Validation rejects changed predecessors, extra archive files, mixed release dates or identities, altered receipts, unrelated asset or region changes, and vector hash drift. LF and CRLF checkouts share the same reviewed SVG text identity.

Independent visual review accepted all three drawings at 96 and 160 pixels and reviewed the native editor and Technical ink captures. Real editor checks passed for vector insertion, independent region recoloring, Soft color and Thin line switching, Technical ink, save/reopen, and isolation with editable path handles. Existing saved artwork retained its preceding embedded vector primitives. The current catalog, audit, and receipt are pinned separately from the preserved July 20 release.

Targeted checks:

```powershell
python -m unittest discover -s tests -p test_core_biology_revision.py
python scripts/validate-scientific-assets.py --library
python scripts/generate-scientific-asset-license-audit.py --check
```

The public-source export includes this review record, the audit generator, and the revision tests alongside the asset pack and predecessor snapshot.
