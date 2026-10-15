# Scientific Asset Authoring Guide

This guide defines the contributor rules for the shared Superbench Figure and Present scientific asset library.

The goal is not to build a large icon dump. The goal is a small, original, manuscript-friendly vector library whose assets can be searched, inserted, recolored, validated, and traced back to clear provenance.

For catalog roadmap, backlog, category coverage, and duplicate-avoidance rules, see `docs/scientific-assets/CATALOG_EXPANSION_PLAN.md`.

## Non-Negotiables

- Do not scrape, trace, copy, closely recreate, or package BioRender assets or any other proprietary scientific illustration library.
- Do not prompt generated images from proprietary library screenshots, watermarked assets, or "make this BioRender-like asset" references.
- Use generic biological concepts, original vector drawing, open-license sources after review, or user-provided assets with explicit redistribution permission.
- Keep every asset vector-first. Raster generation may be used only as rough concept input, then redrawn into SVG.
- The 302 released styles across Core Biology, Core Experimental Biology, Immunology & Oncology and Protein Homeostasis use `CC0-1.0`, as defined by each pack's notice and audit. The other 44 styles also have CC0 reuse permission but await product qualification. Keep future contributions pending until their provenance, rights, scientific meaning, appearance and native editing behavior are reviewed; a new contribution does not inherit an existing pack's release.
- Keep expansion small and reviewed. Add one coherent pack slice at a time, not scattered one-off assets.

## Figure Library Insertion Styles

The Superbench Figure library offers Style 1, Style 2, and Style 3 for newly inserted bundled assets. Style 1 uses the authored SVG. The other two treatments are applied when previewing or inserting an asset; they do not create new catalog records or change the source artwork. Style 2 uses stronger flat color and restrained contours. Style 3 uses muted color and finer lines. The selected treatment is recorded on the inserted object, while SVG paths and `data-region` identifiers remain editable. Changing the library selector does not restyle assets already on the canvas. These display names retain the existing `soft-color`, `cut-paper`, and `technical-ink` saved identifiers, respectively.

Review each new asset at library thumbnail size in all three treatments. Fine instrument details and scientific distinctions should remain legible, and the asset name must accurately describe what the drawing actually shows.

## Scientific Asset Colors

In the Library, **Style** chooses the illustration treatment—Style 1, Style 2 or Style 3—and **Palette** chooses coordinated colors. These settings update the previews and apply to assets you insert next. To recolor an asset already on the artboard, select it and use **Colors**: choose a palette or edit a named biological part, such as Cytoplasm or Nucleus. **Original** uses the colors authored for that asset’s current style. A palette change keeps your edited part colors; an individual part reset in Advanced returns that part to the selected palette. **Reset colors** returns the palette and named part colors to Original while keeping individual component edits made in Advanced. **Saved colors** holds reusable named colors for the document; “swatches” is the vector-editor term for these saved color entries and their more detailed controls.

## File and Metadata Contract

Each reusable asset should have:

- One SVG file under the pack's `svg/` folder.
- One matching entry in `asset-pack.json`.
- A stable asset id, for example `core.mitochondrion.basic`.
- A clear user-facing name, for example `Mitochondrion`.
- A top-level searchable category, for example `organelle`.
- Search tags including common biology terms and visual synonyms.
- `source_type`, `license`, and `provenance`.
- `style_family`, normally `figure-studio-soft-line-v1` or the thinner `figure-studio-manuscript-line-v1` companion family.
- For alternate drawings of the same concept, a shared `concept_id` plus an explicit `style_variant`; never silently replace one visual style or biological form with another.
- Use `variant_axis: "form"` when variants encode biological topology or state-neutral morphology, such as Hairpin versus Linear RNA. Omit it or use `style` only for visual treatments such as Soft line versus Manuscript.
- Assets that share a `concept_id` appear as one library concept with explicit style or form choices. Keep their categories and semantic recolor-region ids aligned so in-place switching can preserve geometry and color edits.
- QA fields: `review_status`, `style_status`, `mvp_quality`, `editable_region_count`, and `reviewer_notes`.
- `editable_color_regions` entries whose ids exactly match SVG `data-region` values.

Good metadata shape:

```json
{
  "id": "core.example.concept",
  "name": "Example Concept",
  "category": "organelle",
  "tags": ["example", "biology", "schematic"],
  "file": "svg/example_concept.svg",
  "source_type": "original_vector_draft",
  "license": "FS-ORIGINAL-DRAFT",
  "provenance": "Original vector draft created for Superbench Figure Tool from a generic biological concept; no proprietary reference image, scraping, tracing, or protected asset-library recreation was used.",
  "style_family": "figure-studio-soft-line-v1",
  "review_status": "draft_qa_passed",
  "style_status": "harmonized_soft_line_v1",
  "mvp_quality": "usable_mvp_draft",
  "editable_region_count": 3,
  "reviewer_notes": "Clear generic silhouette. Provenance review is required before public-license selection.",
  "editable_color_regions": [
    { "id": "body", "label": "Body fill", "default": "#C7F2EC" },
    { "id": "accent", "label": "Accent marks", "default": "#F4A261" },
    { "id": "outline", "label": "Outer outline", "default": "#26323D" }
  ]
}
```

## SVG Structure

Use a simple, safe SVG:

- Root: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 128" role="img" aria-labelledby="title desc">`
- Include `<title id="title">...</title>`.
- Include `<desc id="desc">...</desc>`.
- Use the canonical `viewBox="0 0 128 128"` unless a future pack explicitly defines a different standard.
- Leave roughly 14-18 units of visual padding where possible.
- Use simple shapes and paths.
- Use rounded joins/caps for linework.
- Keep the asset legible at thumbnail size and at manuscript annotation size.
- Avoid embedded raster images, external hrefs, scripts, foreignObject, iframes, CSS imports, filters, and complex effects.

Preferred region structure:

```xml
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 128" role="img" aria-labelledby="title desc">
  <title id="title">Example Concept</title>
  <desc id="desc">Original vector concept with editable body, accent, and outline regions.</desc>

  <path data-region="body" fill="#C7F2EC" d="..."/>

  <g data-region="accent" fill="#F4A261">
    <circle cx="48" cy="52" r="4"/>
    <circle cx="78" cy="70" r="4"/>
  </g>

  <g data-region="outline" fill="none" stroke="#26323D" stroke-linecap="round" stroke-linejoin="round" stroke-width="3.5">
    <path d="..."/>
    <circle cx="48" cy="52" r="4"/>
  </g>
</svg>
```

## Recoloring-Safe Data Regions

Figure Studio recoloring uses the asset metadata as the authoritative region list. Because Fabric does not reliably preserve child SVG `data-region` attributes after import, the app reloads the original SVG, applies color overrides to matching `data-region` elements, then re-imports the recolored vector group.

That means every recolorable semantic region must be easy to find and repaint in the original SVG.

Rules:

- Put `data-region` on the element or group that owns the paint.
- Every `editable_color_regions[].id` must appear in the SVG as a `data-region`.
- Every SVG `data-region` must appear in `editable_color_regions`.
- Use stable semantic names: `cytoplasm`, `nucleus`, `membrane`, `matrix`, `cristae`, `receptor`, `ligand`, `cargo`, `fluid`, `body`, `accent`, `outline`.
- Prefer one semantic idea per region.
- Keep regions small in number, usually 3-5.
- Use direct `fill` or `stroke` attributes when possible.
- Use `fill="none"` for stroke-only regions and `stroke` for linework.
- Use `outline` for the dark structural linework.
- Optional future metadata may specify `paint: "fill"`, `paint: "stroke"`, or `paint: "both"` for a region. The current seed pack infers this from SVG paint attributes, so keep those attributes direct and obvious.
- Do not use a single `data-region` for unrelated biological parts just because they share a color today.
- Do not depend on global color find/replace. Recoloring is region-based, not palette-value-based.

Good stroke-only region:

```xml
<g data-region="cristae" fill="none" stroke="#E76F51" stroke-linecap="round" stroke-linejoin="round" stroke-width="4">
  <path d="M43 49c8-7 14 5 22-2 8-6 15 5 24-2"/>
  <path d="M39 66c9-6 16 6 25-1 8-7 15 6 27-2"/>
</g>
```

Good outline region:

```xml
<g data-region="outline" fill="none" stroke="#26323D" stroke-linecap="round" stroke-linejoin="round" stroke-width="3.5">
  <path d="M27 73c-8-17 0-35 18-44..."/>
  <path d="M43 49c8-7 14 5 22-2..."/>
</g>
```

Good grouped fill region:

```xml
<g data-region="membrane" fill="#C7F2EC">
  <rect x="16" y="59" width="96" height="10" rx="5"/>
  <rect x="16" y="77" width="96" height="10" rx="5"/>
</g>
```

Avoid:

```xml
<!-- Bad: metadata cannot target semantic parts separately. -->
<g data-region="primary" fill="#C7F2EC">
  <path id="cell-body" d="..."/>
  <path id="ligand" d="..."/>
</g>

<!-- Bad: no data-region, so future recoloring cannot target it. -->
<path fill="#F4A261" d="..."/>

<!-- Bad: style-heavy paint is harder to audit and less consistent. -->
<path data-region="body" style="fill:#C7F2EC;stroke:#26323D;filter:url(#shadow)" d="..."/>
```

## Style Rules

Use `figure-studio-soft-line-v1` for the primary icon-like library. Use `figure-studio-manuscript-line-v1` only for intentionally thinner companion art. A different line weight alone is not enough to justify a duplicate asset: the variant must improve manuscript-scale clarity or anatomical restraint.

Core style:

- Canonical viewBox: `0 0 128 128`.
- Primary outline: `#26323D`.
- Common outline width: `3.5`.
- Detail outline width: about `2.75`.
- Line-heavy assets may use outline underlay plus colored inner stroke.
- Rounded caps and joins.
- Flat fills.
- No pseudo-3D, glossy shading, heavy gradients, or decorative effects.

Default palette:

- Cytoplasm/membrane: `#C7F2EC`, `#D9F4E5`, `#7DD3C7`
- Protein/receptor: `#8EC8FF`, `#5EA9DD`
- Nucleus/chromatin: `#B8B5FF`, `#D9D7FF`, `#7B78C9`
- Labware: `#E8EEF7`, `#F7F9FC`, `#FFFFFF`
- Accent/cargo: `#F4A261`, `#E76F51`
- Outline: `#26323D`

Manuscript-line companion contract:

- Canonical viewBox: `0 0 128 128`.
- Primary outline: `2.0` to `2.25` units; detail strokes: `1.25` to `1.5` units.
- Line-heavy underlays: at most `4.0` to `4.5` units with a `2.0` to `2.5` unit inner stroke.
- Optical padding: normally `14` to `18` units; tails, whiskers, and processes may reach `10` to `12` units but never the edge.
- Draw one coherent exterior silhouette. Interior contours stop at occlusions; do not run complete closed outlines through overlapping anatomy.
- Keep the outline plus no more than three chromatic groups unless extra color communicates distinct biology.
- Share `concept_id` and semantic recolor-region ids with the primary style variant.
- The asset must remain identifiable without its label at 64 px.

## Biological Readability

Each asset should communicate one generic concept quickly.

Check:

- Is it recognizable without a label at thumbnail size?
- Is the name honest, or does it overclaim a specific biology?
- Are receptor/channel/protein variants visually distinct?
- Are nucleic acid and chromatin assets recognizable without copying a proprietary visual language?
- Would a manuscript reader understand it as a schematic, not a literal anatomical rendering?
- Are important parts not hidden by outlines or overlapping fills?

## Safety and Originality Review

Before adding an asset:

- Record whether it is original, open-license, user-provided, or generated concept input redrawn into SVG.
- For open-license sources, keep the URL, license name, author/attribution, modification permission, redistribution permission, and review date.
- For generated concept input, keep prompts generic and text-first. Do not use proprietary screenshots or proprietary library names as references.
- Mark unreviewed assets as draft and keep them out of public distribution.
- Reject anything that feels like a close recreation of a proprietary illustration-library object, composition, or visual system.

## Contributor QA Checklist

Run this before requesting inclusion:

- The asset has canonical `viewBox="0 0 128 128"`.
- The asset has `title` and `desc`.
- Visible bounds have consistent padding.
- No raster images are embedded.
- No external hrefs are present.
- No scripts, event handlers, `foreignObject`, iframes, or object/embed tags are present.
- Every recolorable region has `data-region`.
- Every metadata region appears in the SVG.
- Every SVG region appears in metadata.
- Region defaults match the intended current SVG colors.
- Region names are semantic and stable.
- `editable_region_count` matches `editable_color_regions.length`.
- Source/provenance and draft license fields are present.
- `reviewer_notes` explicitly state draft/manual/legal review status.
- The pack license-release audit contains the current SVG hash, provenance hash, source type, lineage, and release disposition.
- The contact sheet looks visually consistent with the pack.
- The asset validates.

Commands:

```bash
python3 scripts/validate-scientific-assets.py
python3 scripts/test-scientific-asset-validator.py
python3 scripts/generate-scientific-asset-license-audit.py --check
python3 scripts/generate-scientific-assets-contact-sheet.py
```

The first structured expansion batch is reproducible with:

```bash
python3 scripts/seed-core-biology-expansion-batch.py
```

That script is idempotent for existing batch ids, but contributors should still review diffs, run validation, and regenerate the contact sheet after changing it.

To inspect the intentionally invalid region-drift examples directly:

```bash
python3 scripts/validate-scientific-assets.py --pack tests/scientific-assets/invalid-region-fixtures/asset-pack.json --expect-fail
```

Region drift means the SVG `data-region` values and the metadata `editable_color_regions` ids no longer match exactly. This matters because Figure Studio recolors scientific assets by reloading the original SVG and applying overrides to matching `data-region` elements before re-importing the vector group.

Open the generated contact sheet:

```text
docs/scientific-assets/core-biology-contact-sheet.html
```

## Figure Studio Draft Export Helper

The Assets tab has a user-facing `Build Asset` area for sketching reusable project assets. `Add selection to My Assets` saves selected editable artwork inside the current project for immediate reuse. `Export asset files` is the internal bridge from Figure Studio sketching to production SVG authoring.

It exports the active selection only and downloads:

- normalized 128 x 128 SVG
- metadata stub JSON
- mini draft asset-pack JSON
- checklist JSON with dry-run warnings

Save these files under:

```text
docs/scientific-assets/draft-exports/
```

Draft exports are intentionally not production-ready. If the author tags selected objects in Build Asset > Recolor regions, the draft exporter preserves those semantic ids as SVG `data-region` values and non-placeholder editable-region metadata. Untagged painted objects still receive placeholder region ids such as `fill_1`, `stroke_1`, `outline`, or `accent`, inferred from object paint. Before promotion, replace any remaining placeholders with semantic region names, remove accidental text/scaffold/background geometry, confirm the viewBox and padding, complete category/tags/provenance/reviewer notes, and run validation against a temporary pack.

The Build Asset area also supports guide-image-backed drafting:

- Use `Add guide image` only for safe, permitted, generic morphology references.
- Guide images are locked, low opacity, marked reference-only internally, and excluded from manuscript exports and saved/exported asset artwork.
- Record source notes if the guide needs to be traceable later.
- Keep guide images separate from candidate geometry. Do not group them into the candidate.
- Complete the user-facing Build Asset fields for any export-worthy draft: asset name, status, concept, and design notes.
- Tag recolorable regions before export when the semantic part is obvious, for example `cytoplasm`, `nucleus`, `membrane`, `outline`, `receptor`, `ligand`, `fluid`, or `instrument_body`.
- Draft metadata and checklist files record guide-image context when present, but guide images are never exported as asset geometry.

The Build Asset area also has primitive organic-cell draft buttons:

- `Cell` creates a simple editable cell with a nucleus and small organelle markers.
- `Star cell` creates an astrocyte/microglia-like draft from a central soma plus separate stretched projection primitives.
- `Neuron/glia` creates a soma with a long neurite-like process and editable side branches.
- `Spindle cell` creates an elongated fibroblast/smooth-muscle-like draft with stretchable tapered ends.

These are construction templates, not production assets. They intentionally insert ungrouped editable primitives and select them together so authors can reshape individual projections with normal Figure Studio handles, then either save them to `My Assets` for project reuse or use `Export asset files` for a review-only candidate.

Do not paste draft-export metadata directly into `core-biology` without review. The helper cannot infer biological semantics, licensing status, or final pack quality.

## Pre-Inclusion Review Gates

Use these gates before expanding a pack:

1. Product fit: the asset belongs in a broadly reusable Figure Studio pack.
2. Originality fit: it is not copied, traced, scraped, or too close to a proprietary library asset.
3. Science readability: the concept is recognizable but not over-specific.
4. Style fit: it follows the active style family.
5. Recoloring fit: `data-region` and metadata align.
6. Technical fit: validator and contact-sheet QA pass.
7. Legal fit: source/license/provenance are recorded, and public redistribution is not implied until approved.

## Current Manual Review Watch List

The 2026-07-19 full-library audit found no remaining P0 template blockers. Parity slice 17 completed the queued manuscript companions for Generic Antibody, Drug-Conjugated Antibody, DNA Double Helix, Plasmid Vector, and Mitochondrion. Parity slice 18 completed the final queued item by adding a linear/open ssRNA form beside the retained RNA hairpin. Preserve all of those base/companion relationships under shared concept ids.

- Keep `core.rna.strand` and `core.rna.strand_linear` together on the `form` axis with the shared `backbone`, `base`, `accent`, and `outline` regions. Do not turn the linear drawing into a named RNA class or imply sequence, length, end chemistry, or modification.
- The audited replacement and variant queue is now complete; new watch-list items require evidence from repeated use, figure-abstract extraction, or a fresh visual/discoverability audit.
- Parity slice 19 added five soft-line model-organism concepts after independent gap and visual review. Do not add manuscript companions until repeated publication use shows a concrete readability benefit.
- The current provenance/license-release audit revision clears all 108 production styles under CC0-1.0. The scope is limited to SVGs and asset-specific metadata explicitly listed in the machine-readable audit; see `docs/scientific-assets/PROVENANCE_LICENSE_RELEASE_AUDIT_2026_07_20.md`.

See `docs/scientific-assets/LIBRARY_AUDIT_2026_07_19.md` for the audited replacement batch, accepted-as-is families, and search-intent evidence.

## Minimal New Asset Pull Request Shape

A small asset contribution should include:

- SVG file.
- Metadata entry.
- Updated contact sheet.
- Validator output.
- Brief source/provenance note.
- One sentence explaining why the asset is reusable enough for the pack.
- Manual art/legal review status.

Do not include broad library expansion, UI feature work, and asset art changes in the same slice unless explicitly planned.
