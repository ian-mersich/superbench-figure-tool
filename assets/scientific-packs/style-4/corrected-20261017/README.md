# Corrected Style 4 drawings

The owner's `style4_corrected_486.zip` supplies 243 corrected drawings. This overlay selects those exact SVG bytes and keeps the other 243 current Style 4 entries, including earlier recovered artwork. It does not replace Style 1, Style 2, or Style 3.

`../manifest-corrected-20261017.json` records the complete 486-ID selection, per-file source hashes, the unchanged previous entries and the corrected archive identity. Four supplied mapping/documentation files are retained in `source/`; the large contact sheet and source audits remain in the original download rather than the runtime.

Six supplied nucleic-acid drawings have an empty outline group: their contours belong to the nucleic-acid region. These empty roles are recorded explicitly, without inventing geometry or changing supplied SVG bytes. All current Style 4 live scientific text, viewBoxes and semantic region identities are preserved. Illustrative analytical templates remain examples, not measured results.

Reproduce with `python scripts/import-style4-correction.py --source-archive <ZIP>`. Add `--check` to compare exact generated files; `python scripts/validate-style4-library.py` validates the complete committed selection without Downloads.
