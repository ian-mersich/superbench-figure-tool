# One Figure release for the browser and Superbench

The canonical Figure repository is `C:\Users\ianme\Desktop\Projects\superbench_figure_tool`.
The browser site and Superbench consume one committed editor and asset collection:
486 Library drawings representing 386 concepts in 11 packs, and 12 editable
scientific scenes. Fixes belong here. Do not maintain a second editor in the
public source checkout or backport individual fixes into the old beta.6 site.

The beta.11 release was published on 15 October 2026. Its immutable runtime source
is `8c755c0ce0b591f178c402dc261e1f64a635b9a0`, and its selected Superbench package
is `7291043aa2f526aafde5d38c320df41e597d39097b8b2038832bcf2ef55c04d7`.
The deployed HTTPS editor and the actual installed selection passed the same
800-file payload comparison. The public source/tag, archive identities, CI and
deployment evidence are recorded in [PUBLIC_PUBLICATION.md](PUBLIC_PUBLICATION.md).

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
steps after the matched candidate is reviewed. Those steps are complete for
beta.11. All beta.6 repaint/backport candidates remain unpublished historical
diagnostics. The shared Figure release milestone is complete; the separate
Windows installer qualification remains on the same roadmap.

## Tooling changes after publication

The canonical development repository can advance its packaging scripts, tests
and release documentation without repackaging the installed or deployed editor.
The subsequent private-review eligibility correction changes only the producer
and its regression tests. It does not change any payload file, version, source
pin, public tag, archive, or installed selection. The original beta.9 source
export remains faithful to its reviewed 16d0629 snapshot; its explicit
public-release build path already emitted the correct manifest.

Do not point either consumer at a newer development commit merely because its
release tooling changed. A runtime update requires a new intentional shared
candidate, paired artifacts, qualification and promotion. Keep immutable receipts
for every release; beta.11's `u11r`, `l11s` and Core `g11` records are the evidence
for the current selection. The first failed live-network and fully rolled-back
activation attempts remain separate from the accepted fresh workflow and R2
activation. Later activation-helper and documentation changes do not change any
of the 800 payload files or require repinning either consumer to a tooling-only
commit.
