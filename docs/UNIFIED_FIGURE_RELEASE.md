# One Figure release for the browser and Superbench

The canonical Figure repository is `C:\Users\ianme\Desktop\Projects\superbench_figure_tool`.
The browser site and Superbench consume one committed editor and asset collection:
486 Library drawings representing 386 concepts in 11 packs, four drawing styles, and 12 editable
scientific scenes. Fixes belong here. Do not maintain a second editor in the
public source checkout or backport individual fixes into the old beta.6 site.

## Beta.17 integration candidate — 23 October 2026

The accepted `00c6ccfe` checkpoint is being prepared as a paired beta.17
candidate. Its product logic is exact to `58e17ccb`; the package version change
adds no editing behavior. Against the delivered beta.16, the candidate includes
the accepted selection, handle, Layers/Isolation, native PDF glyph painting and
cooperative Open changes. Private candidates 4/5/6, Figure 4 knockout experiments
and untracked experiments are excluded by building the committed revision.

This is candidate preparation, not publication or installed selection. Qualify
the exact paired artifacts and six desktop width/theme cases before promotion.
The single passing Figure 2 journey does not establish repeated v1 performance;
the later repeated Open check still fails its original limits. General reference
parity, dense editing and memory, arbitrary editable PDF fidelity, and Figure 4
typography/export remain unfinished. Preserve the current fallback/export warnings
and the original failed results. Beta.16 remains installed and public until a
qualified successor is promoted. Figure implementation is paused during this
integration window; the reuse-first roadmap remains unchanged.

## Current delivered release

The delivered beta.16 point/curve package uses immutable source
`d170100675e2ed96dffccc2fd6ae3cd207a8c484`, semantic package
`ceec84e7e18bd0945a99874817b9ff59f444ffa001eb87fa49b6a8c6587ce54d`, with 1,584 shared payload files.
Its public source commit is `5a0627773b4cb93196300dd2bca6a654b956fc27` and website
consumer commit is `29ab77f6b34a3d8f2874aa539dffb312b914118e`. The 486-drawing Library,
four styles and 12 scenes are unchanged. See the
[beta.16 checkpoint](PUBLIC_PUBLICATION.md#beta16--point-and-curve-continuity).

**Beta.16 is published, deployed and installed**, with beta.15 retained for
rollback. All 1,584 raw HTTPS payload files match the actual installed package;
the Core pin, active selection and trust record agree. Actual HTTPS qualification
and independent live review pass; see the paired publication checkpoint for scope.

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

The [point and curve slice](architecture/POINT_AND_CURVE_CONTINUITY_2026_10_21.md)
corrects off-center anchor grabs, attached tangent movement, nested Direct
Selection painting and cooperative PDF history recovery. The actual Affinity
3.3.1 comparison uses the unchanged 1,592,921-byte Figure 2 and its single red
marker; it establishes that bounded gesture, not overall parity or a speedup.
Tiny ordinary Undo translations and sparse edge-pixel differences retain their
documented limits. General Selection/Direct Selection, sustained dense dragging,
Figure 2 typography, corpus fidelity and scientific PDF v1 remain open.

The user requested a joint project summary before another Figure task.
Next implementation is on hold. The reuse-first roadmap and full scientific PDF
v1 requirements are unchanged; the remaining work is a backlog for that review,
not an instruction to start another slice.

Beta.15 is the previous delivered image-interpolation checkpoint, from source
`1a20663eacd6e2ab9059bad1b2d57094dfeda2e0` and package
`c2daf1a7736f1dcb90e5be15dac5111eac840f9b3b3bcb472fdce88c01034538`.
Its reviewed editable-PDF and Figure-to-slide fixes remain included. Copied
slides retain the existing fresh-ID SVG/PNG snapshot semantics without original
PDF editing authority; a new post-copy content mutation was not qualified.
Earlier beta.13/14 and reuse-pilot results retain their original scopes.

Host-owned appearance and file controls can differ without forking the editor.
The website has a persistent Light/Dark control; Superbench uses global App
Settings. Document colors and editing behavior remain shared. Browser preferences
do not enter saved scientific documents. The boundary and existing appearance
interface are documented in [Figure host settings](architecture/FIGURE_HOST_SETTINGS.md).
A browser-only control still ships through the paired release procedure below.

The 15 October product decision is recorded in
`config/scientific-product-release-2026-10-15.json`. It binds the exact accepted
artwork, scientific metadata, native-editing reviews and the owner's instruction
to release the reviewed Library in both consumers. It supplements the historical
pending product records; it does not rewrite them or create a new license grant.
The original 10 October CC0 grants and all predecessor/revision records remain
unchanged. The strict validator checks those records first, then accepts only the
finite reviewed product decision. See
`docs/scientific-assets/REVIEWED_LIBRARY_PRODUCT_RELEASE_2026_10_15.md`.

The finite successor decision in
`config/scientific-product-release-2026-10-15-expansion.json` adds the reviewed 80
drawings for 40 concepts. It binds the three new collections, scientific and native
editing reviews, and the prospective 15 October repository CC0 contribution
policy. The original grants, predecessor records and source-time acceptance
document remain unchanged. Current deployment and installed-selection outcomes
are recorded in `PUBLIC_PUBLICATION.md`; the finite acceptance inputs are preserved.

The finite Style 4 successor is
`config/scientific-product-release-2026-10-17-style4.json`. It binds the supplied
486 alternate SVGs, the selected earlier-batch recoveries and their exact source
identities. Historical grants and prior decisions are preserved. Source-time
acceptance is separate from the later package, native, live website and actual
installed-selection outcomes recorded in `PUBLIC_PUBLICATION.md`.

## Prepare the matched artifacts

Commit the reviewed version, runtime, assets, approval record and release tools
first. Use a short, fresh ignored output path to accommodate complete upstream
source trees on Windows:

```powershell
py -3 scripts/figure_tool_package_producer.py --revision <full-commit> --distribution-scope public-release --artifacts-only --source-exports --output-root qa_artifacts/u9
```

The producer archives that exact Git revision once. It validates every Library
pack, scene, license record, notice and vendor identity, then builds one payload.
It emits:

- A native tool-package ZIP, including its content-addressed manifest.
- A complete static ZIP containing the same `app/`, `vendor/`,
  `assets/scientific-packs/`, `assets/scientific-scenes/` and `web/` files.
- Source, web-shell, rights and release receipts. ZIP readback compares every
  decompressed static member against its native member and manifest hash.
- `source-repository/`, a slim public source export with the complete unchanged
  payload, validation tools, scientific review notes and source CI.
- `figure-tool-source.zip`, the same source plus verified preferred upstream
  source materials under `preferred-source-materials/`, outside every runtime root. Those materials never enter
  the browser/native payload. Full source ZIP readback checks every runtime file.

`SOURCE_RELEASE.json` describes the canonical commit, product version, package
digest, payload tree, immutable tag and vendor-source location. It is source
metadata outside the shared payload. The full archive and slim Git tree differ
only in source-material inclusion and that explicit location metadata. The code
license, CC0 artwork terms, complete third-party notices and source lock travel
with both. Fresh upstream compiler rebuilds are not qualified as byte-identical;
the local svg2pdf patch is checked against its pinned published input.

`--artifacts-only` issues no update catalog and reads no signing key. It retains
all public rights/product validators and rejects catalog/signing options. This
supports reviewed static hosting and a locally trusted immutable Superbench
package without provisioning an update-feed signer. A public automatic update
feed remains a separate signed-catalog operation.

Source eligibility and package distribution scope are distinct. Validation may
report that the complete collection is eligible for public release even during
a private-review build. A private-review manifest must still declare
`public_release_eligible: false`; the public assertion is emitted only for an
explicit public-release build whose source passes every public check. Build and
rights receipts preserve the truthful source-validation result.

## Qualify and promote the same release

Qualify the exact native/static payloads, including the current repaint, direct
selection, Library discovery and light/dark chrome fixes. Run the existing desktop
width/theme matrix and native Save/cold Open checks before promotion. Bind each
report to the canonical commit and semantic package digest. Independent visual
review is separate from structural pass counts. No open artwork or UI hold may
be reported as accepted.

The public source repository receives the reviewed `source-repository/` tree,
without private Git history or ignored QA/user files. Its immutable tag is
`v<product-version>`; the matching release attaches the producer's web ZIP as
`figure-tool-web.zip` and the full source archive as `figure-tool-source.zip`.
Renaming a release asset does not change its bytes.

The website consumer uses a pinned v2 `config/figure-release.json`: exact release
URL and ZIP SHA-256, canonical source revision, semantic package digest and payload
tree digest. It mounts the flat ZIP beneath `superbench/figure_tool/` unchanged.
Only outside the shared payload, it adds a root redirect to `web/` (preserving query
and fragment), root legal aliases copied from `app/legal/`, and source metadata.
It must not flatten `web/`, rewrite iframe paths, remove packs/scenes, or edit
runtime files. Verify the served `web/`, `app/`, vendors and assets against the same
payload inventory before publishing and again against the deployed HTTPS site.

Superbench's consumer installs and trusts that exact native package, retaining the
previous package for rollback. Its source pin must carry the real public-release
provenance. An existing compatible native host can consume it after the separate
headless native checks; a package update does not establish a new MSI qualification.

For future releases, publishing the public repository/release, updating the
website, and changing the actual local selected package remain explicit promotion
steps after the matched candidate is reviewed. Public source/release publication,
website deployment, actual desktop selection and final interactive HTTPS
acceptance are complete for beta.16. All beta.6 repaint/backport
candidates remain unpublished historical diagnostics. The separate Windows
installer qualification remains on the same roadmap.

## Tooling changes after publication

The canonical development repository can advance its packaging scripts, tests
and release documentation without repackaging the installed or deployed editor.
Later beta.14 documentation commits do not replace runtime source
`4598703fd1dfd80642983705365f3d07c84f3d1b` or package
`d44ffb7f767f68fec6db512f51c5955e8be9ee844a5c35816bc8df58d6b245aa`.
At that historical checkpoint, both consumer pins, the public `v1.0.0-beta.14`
tag and its archives remained bound to that qualified runtime. Its evidence is
in `qa_artifacts/v14/` and Core `qa_artifacts/g14/`, linked from the
[publication checkpoint](PUBLIC_PUBLICATION.md#beta14--selection-movement-and-editing-continuity-21-october-2026).
Historical beta.13 source, tag and archives remain immutable at their original
identities; retaining them does not keep today's consumer pins on beta.13.

The following beta.9 and beta.11 tooling/activation records remain historical.
The subsequent private-review eligibility correction changes only the producer
and its regression tests. It does not change any payload file, version, source
pin, public tag, archive, or installed selection. The original beta.9 source
export remains faithful to its reviewed 16d0629 snapshot; its explicit
public-release build path already emitted the correct manifest.

Do not point either consumer at a newer development commit merely because its
release tooling changed. A runtime update requires a new intentional shared
candidate, paired artifacts, qualification and promotion. Keep immutable receipts
for every release; beta.11's `u11r`, `l11s` and Core `g11` records are the evidence
for that historical selection. The first failed live-network and fully rolled-back
activation attempts remain separate from the accepted fresh workflow and R2
activation. Later activation-helper and documentation changes do not change any
of the 800 payload files or require repinning either consumer to a tooling-only
commit.
