# Figure Tool vendor source materials

`vendor/source-lock.json` identifies source material for each runtime shipped from `vendor/`. It pins upstream repository snapshots by commit and archive SHA-256, and npm distributions by registry SHA-512 integrity. `scripts/prepare-vendor-source.py` fetches and verifies those inputs into a fresh output directory:

```powershell
python scripts/prepare-vendor-source.py `
  --repository-root . `
  --output qa_artifacts/vendor-source-review/source-materials
```

For an already prepared directory, use `--verify <directory>` to check the source-lock digest, pinned archive identities, indexed extracted file sets, and file hashes without network access. The generated directory has `repositories/` with editable upstream trees, `npm/` with exact published packages/source maps/license files, `archives/` with the original pinned archives, `source-index.json`, and a standalone `THIRD_PARTY_NOTICES.md` with full package license/notice text. The output may be large. Keep it with candidate source materials; do not serve it as part of the browser site.

Build the distributable vendor notice file from a verified source-material directory and the checked-in DejaVu license:

```powershell
python scripts/build-vendor-notice.py `
  --repository-root . `
  --source-materials qa_artifacts/vendor-source-review/source-materials `
  --output vendor/NOTICE
```

The generated `vendor/NOTICE` is a standalone file containing the complete transitive package license and notice texts, the source-mapped jsPDF module attribution/license comments, and the complete DejaVu font terms. Candidate export tooling can direct `--output` into its staging tree and compare its bytes with this checked-in notice.

## Upstream build entry points

Use the package manager and lockfile present in each extracted repository. These are the upstream project build entry points, not a promise that the current compiler environment has been recreated or that the result will be byte-identical to the published npm bundle.

| Component | Pinned source | Build entry point |
| --- | --- | --- |
| Fabric 7.3.1 | [`fabric.js`](source-lock.json) at `b305406837c50b5638ce32c7558fc83e9c8c4159` | In `repositories/fabric-7.3.1`, install from its committed Yarn lockfile and run `yarn build` (the package script delegates to `scripts/index.mjs build`). |
| jsPDF 4.2.1 | [`jsPDF`](source-lock.json) at `4562ce8aa35bd5ecd98cd5e262e3da2af96476f6` | In `repositories/jspdf-4.2.1`, install using the committed Yarn lockfile and run `yarn build` (`rollup --config rollup.config.js`). |
| pdf-lib 1.17.1 | [`pdf-lib`](source-lock.json) at `4beebbef7a261ed0be089bb1d63a5b6e28cc488a` | In `repositories/pdf-lib-1.17.1`, install using the committed Yarn lockfile and run `yarn build`; its build script emits CJS, ESM, UMD and minified variants. |
| PDF.js 5.7.284 and 3.11.174 | [`pdf.js`](source-lock.json), pinned commits `7e5b36c2d572ba82e1e3adeb1c266f0052746c73` and `ce87167432819f85df49b6b16c7a78556e9a4ee0` | In each extracted `repositories/pdfjs-*` tree, follow its `README.md` and use `npx gulp generic` for the generic browser build, `npx gulp generic-legacy` for older browsers, or `npx gulp dist` for the npm distribution. `npx gulp dist-install` builds and installs the distribution locally. The npm `pdfjs-dist` package alone does not contain the complete editable source/build inputs. |
| svg2pdf.js 2.7.0 | [`svg2pdf.js`](source-lock.json) at `886439cd56a4de05db4e92d2afc264e51b1d6a16` | In `repositories/svg2pdf.js-2.7.0`, install using its committed lockfile and run `npm run build` (`rollup -c rollup.config.mjs`). |
| polygon-clipping 0.15.7 | [`polygon-clipping`](source-lock.json) at `25f2a460ca7bd750d958d3d83b0037a32fcf75f6` | In `repositories/polygon-clipping-0.15.7`, install using its committed lockfile and run `npm run build` (`rollup -c`). |
| DejaVu Fonts 2.35 | [`dejavu-fonts`](source-lock.json) at `e055422f2643c8dc4718fb2269daeb3f707ccc4b` | In `repositories/dejavu-fonts-2.35/dejavu-fonts`, install FontForge and run `make full-ttf` as directed by `BUILDING`; this emits the full glyph-set TTFs under `build/`. The four distributed TTFs came from Matplotlib 3.10.9 and are not claimed to be reproduced byte-for-byte by this source snapshot. |

The `npm/` package archives preserve the exact distribution inputs used to identify the shipped JavaScript. Their `dist/` files and source maps are useful for inspecting how upstream source and dependencies appear in the published bundle. A source map is not, by itself, complete editable source or a substitute for the upstream source archive.

## Local svg2pdf change

The shipped `vendor/svg2pdf/svg2pdf.umd.min.js` contains the local Figure Tool source-observer patch recorded in `vendor/manifest.json`. Starting with the exact `dist/svg2pdf.umd.min.js` from the pinned `svg2pdf.js@2.7.0` npm package, reconstruct and check the patched output with:

```powershell
python scripts/rebuild-svg2pdf-vendor.py `
  --repository-root . `
  --upstream qa_artifacts/vendor-source-review/source-materials/npm/svg2pdf.js@2.7.0/dist/svg2pdf.umd.min.js `
  --check
```

To write the reconstructed bytes elsewhere, replace `--check` with `--output <path>`. The tool requires the upstream bundle hash and each recorded patch anchor to match exactly once, then verifies the final byte count and SHA-256 against the vendor manifest. This proves deterministic reconstruction of the local textual patch from the pinned published UMD file. It does not prove that compiling svg2pdf.js source regenerates that upstream UMD file, nor that the patch is an upstream build output.

## Reproducibility boundary

The source repository archives and npm tarballs are identified by immutable commit/hash data, and extracted files are checked against the generated inventory. This provides the preferred editable sources, source maps, dependency package contents, build scripts, and notices needed for inspection and modification. A fresh upstream compilation remains unqualified until it is performed with the upstream toolchain and dependencies and compared against the relevant npm bundle. Do not describe the npm distribution itself as the full preferred source where the source lock includes a separate repository snapshot.
