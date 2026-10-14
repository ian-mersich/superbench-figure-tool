# Superbench Figure Tool

Create editable scientific figures and presentations in your browser. Figure Tool provides vector drawing, scientific artwork, portable project files and SVG, PNG and PDF exports.

**[Open Figure Tool](https://imersich.com/superbench/figure_tool/)** · [Download a release](https://github.com/ian-mersich/superbench-figure-tool/releases)

This repository contains the **1.0.0-beta.6** editor source. The browser edition uses the same editor source as the desktop integration; an installed desktop release is qualified separately. [Download the complete source archive](https://github.com/ian-mersich/superbench-figure-tool/releases/download/v1.0.0-beta.6-docs.1/figure-tool-source.zip).

Documentation revision 1 updates the introduction and license explanation. Editor code, artwork, dependencies and saved-file formats remain beta.6.

## Run the browser editor

Serve this directory over HTTP and open `web/` at that address. The browser edition stores work in the current browser profile and downloads portable files and SVG, PNG, and PDF exports. Browser copies do not sync across devices or accounts.

## Source and build notes

The large extracted vendor source trees are not stored in this Git repository. Fetch and verify the exact pinned inputs using the steps in `vendor/SOURCE_MATERIALS.md`; the lock records upstream commits, archive hashes, and package integrity values.

Run `python scripts/prepare-vendor-source.py --repository-root . --output qa_artifacts/vendor-source-review/source-materials` to fetch the verified source inputs when they are not present. To check an existing prepared directory offline, run `python scripts/prepare-vendor-source.py --repository-root . --verify qa_artifacts/vendor-source-review/source-materials`. See `vendor/SOURCE_MATERIALS.md` for upstream build entry points and the reproducibility boundary.

## Focused checks

- `node --test tests/vectorEngine.test.mjs`
- `python -m pytest tests/test_vendor_fabric_portability.py tests/test_vendor_source_tools.py`
- `python scripts/validate-scientific-assets.py --library assets/scientific-packs/library.json --require-public-release`
- `python scripts/validate-vendor-bundle.py` (checks the shipped runtime and notices; see above to also fetch and verify preferred source materials)

The included asset registries contain only packs and scenes whose source rights records authorize public distribution. Individual CC0 asset notices and complete vendored dependency terms remain with their files. First-party code is Apache-2.0; see `LICENSE`, `NOTICE`, and `LICENSE_POLICY.md`. Original artwork uses CC0-1.0 under `assets/LICENSE-ORIGINAL-ASSETS-CC0-1.0.md`. Third-party fonts and libraries keep their original terms. This package is source for the Figure Tool and is not an npm package.
