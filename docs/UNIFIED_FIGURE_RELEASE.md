# One Figure release for the browser and Superbench

The canonical Figure repository is `C:\Users\ianme\Desktop\Projects\superbench_figure_tool`.
The browser site and Superbench consume one committed editor and asset collection:
486 Library drawings representing 386 concepts in 11 packs, four drawing styles, and 12 editable
scientific scenes. Fixes belong here. Do not maintain a second editor in the
public source checkout or backport individual fixes into the old beta.6 site.

The [beta.15 release](https://github.com/ian-mersich/superbench-figure-tool/releases/tag/v1.0.0-beta.15)
was published on 21 October 2026. Its immutable runtime source is
`1a20663eacd6e2ab9059bad1b2d57094dfeda2e0`, and its selected Superbench package is
`c2daf1a7736f1dcb90e5be15dac5111eac840f9b3b3bcb472fdce88c01034538`.
The [HTTPS editor](https://imersich.com/superbench/figure_tool/) and actual
installed selection match all 1,583 payload files; the Core pin, active selection
and trust record agree. Beta.14 is retained for rollback. The desktop host is
unchanged. Reopen the desktop app or refresh the website to load the new editor;
an already running app retains its loaded version.

This release delivers the reviewed explicit image-interpolation corrections:
editable PDF Open and native-format Save/cold Open, actual artwork PDF export,
and Figure-to-slide copy followed by actual slide PDF export. The copied slide
retains the existing editable SVG/PNG snapshot semantics with fresh identities,
without transferring original-PDF editing authority. Its qualification covers
copy, entry into the slide editor, exports and Save/reopen; new post-copy content
mutation was not qualified. The beta.14
[selection interaction slice](architecture/SELECTION_BODY_INTERACTION_2026_10_21.md)
remains included and passes the 33-check actual-package regression.

Separate exact-package groups pass 50 Figure/image checks, 22 slide checks,
186 native checks across six cases and 12 hosts, and 119 Core browser checks
across six cases. Native and Core browser visual reviews each accept 24 originals.
Actual HTTPS qualification passes 702 checks; independent live review accepts
25 originals and replays 18 saved-content comparisons. The public source/tag,
archive identities, exact-commit CI, qualification scopes and deployment are in
the [beta.15 publication checkpoint](PUBLIC_PUBLICATION.md#beta15--explicit-pdf-image-settings-and-shared-delivery-21-october-2026).

Beta.13 previously combined document setup, compact editing controls, curved-arrow
editing, saved-file compatibility and narrow-window Presentation menus. Beta.14
delivered the native Fabric selection movement and editing-continuity changes.
The explicit image work now ships in beta.15. Full Selection/Direct Selection,
genuine Figure 2 typography/geometry, general PDF fidelity and performance/memory
acceptance remain open. Continue substantive selection behavior and the measured
Figure 2 typography case next; the reuse-first roadmap and full v1 requirements
remain unchanged. The earlier Fabric controls pilot and importer comparison retain
their original experimental scope. See the
[image source qualification](architecture/PDF_IMAGE_INTERPOLATION_EXPORT_2026_10_21.md).

A beta.16 candidate is being qualified from the committed anchor/curve work at
`c9c92b5ed325bd3fd1da27d61c8ec0b949d59170`. It corrects off-center grabs,
attached tangent movement, nested Direct Selection painting and cooperative PDF
point-history recovery. Its source matrices and actual Affinity comparison are
recorded in [point and curve continuity](architecture/POINT_AND_CURVE_CONTINUITY_2026_10_21.md).
The coordinator will qualify the exact committed LF payload before native/public
delivery. Beta.15 remains selected and deployed until that process passes. Tiny
ordinary Undo translations and sparse edge-pixel differences retain their precise
bounded disposition; full selection and scientific-PDF v1 are not accepted.

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
acceptance are complete for beta.14. All beta.6 repaint/backport
candidates remain unpublished historical diagnostics. The separate Windows
installer qualification remains on the same roadmap.

## Tooling changes after publication

The canonical development repository can advance its packaging scripts, tests
and release documentation without repackaging the installed or deployed editor.
Later beta.14 documentation commits do not replace runtime source
`4598703fd1dfd80642983705365f3d07c84f3d1b` or package
`d44ffb7f767f68fec6db512f51c5955e8be9ee844a5c35816bc8df58d6b245aa`.
Keep both current consumer pins, the public `v1.0.0-beta.14` tag and its archives
bound to that qualified runtime. Current evidence is in `qa_artifacts/v14/`
and Core `qa_artifacts/g14/`, linked from the
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
