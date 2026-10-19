# Figure web editor

This folder is a browser entry around the **same** `../app/index.html`, scripts, styles, and
vendor assets that the Figure tool uses inside Mersich Lab Superbench. Once the shared
editor is ready, **Appearance · Light / Dark** stays visible in its header.
**Browser files** opens browser saves, file controls, and **About**. About contains the Figure website and
personal-site links, licenses, source downloads, and the browser-storage explanation. Do not copy the editor implementation here
or maintain a separate Figure feature branch for the web edition.

The shared Library contains 406 drawings representing 346 concepts in eight packs,
with 12 editable scientific scenes. Original artwork has CC0 reuse permission.
The dated product-release record separately binds the accepted scientific,
visual, and editing reviews; historical permission and review records remain intact.
Before public packaging, run
`python scripts/validate-scientific-assets.py --library --require-public-release`
from the Figure component directory and review the Scene rights records as well.
Product approval must be recorded separately; a passing local browser check does
not automatically approve a pack or scene. See `docs/UNIFIED_FIGURE_RELEASE.md`.

Start the static server from the canonical Figure source repository:

```powershell
Set-Location "C:\Users\ianme\Desktop\Projects\superbench_figure_tool"
py -3 -m http.server 4177 --bind 127.0.0.1 --directory .
```

Open `http://127.0.0.1:4177/web/` directly. This source preview is separate from
the installed Windows app and the immutable Figure release selected by Superbench.

Use these HTTP addresses rather than opening `index.html` as a local file. Browser
file URLs prevent the editor from fetching its vendor manifest and accessing the
shared iframe and saved-work library. The web entry now stops before loading the
editor at a file URL and offers the port-4177 preview link. Keep the server running;
use the same address for later visits so browser saves remain at the same origin.
An editor startup failure on HTTP shows **Reload editor** and leaves saved work intact.

The first development slice supports the browser features already present in the shared
Figure application: creating/editing a figure, opening local files through the editor,
and downloading saved documents and exports. The static server has no native PDF service.
Do not present advanced native PDF operations as web-supported, or assume that a browser
download is an automatically synchronized cloud save. Public hosting, browser privacy and
file-size limits, accessibility, and exact feature qualification remain release work.

The editor shell lives in this subfolder to allow web-only hosting and status content.
Its iframe loads the shared Figure application one directory above, so Superbench and this
browser entry use the same editor source at the same repository revision.

The web host inserts Browser files and the existing Appearance selector into the
ready editor's header. Only its file and About controls move into the Browser files
popover. Their file and browser-store
handlers stay unchanged. `browser-chrome.css` loads only through this web host; direct
shared-app and native-host launches do not acquire browser controls. The outer header
remains available during loading, local-file guidance, startup failure, or a failed
popover stylesheet load. Browser save announcements remain accessible when the popover
is closed, and save failures reveal the explanation and recovery controls. Escape closes
the popover and returns focus to Browser files.

## Browser appearance

The visible **Appearance · Light / Dark** control changes the web shell and shared editor controls immediately. It uses
the shared editor's appearance API; figure and slide colors remain part of the document.
The browser remembers an explicit choice in localStorage at the same origin, independent
of installed Superbench settings and browser project saves. Before a choice is made, the
editor follows the system's light or dark appearance. If preference storage is blocked,
the selector still works for the current visit. The local-file guidance also supports
the selector without starting the iframe or accessing browser storage.

Appearance belongs to the containing host. Superbench uses its global Settings;
this web entry owns the browser preference. Both call the same shared editor
appearance API, and neither saves interface appearance into figure or slide artwork.
Host controls and storage can differ while the complete Figure runtime and Library
remain one paired release. See [the host settings boundary](../docs/architecture/FIGURE_HOST_SETTINGS.md).

## Browser saves

Edits are saved automatically to IndexedDB on this device. **Saved work** opens the local
list with thumbnails, names, last-save times, Resume, Rename, Download project and Remove.
Each entry preserves all open Figure/Present documents and their portable asset payloads.
**Earlier saves** retains two previous snapshots; recovering one creates a separate copy.
**Download file** saves the active document as `.fsfigure` or `.fsdeck`. A library download
uses `.fsproject` to retain all its open documents. **Open file** uses the shared file opener.

The database name is stable across editor revisions and URL paths. Project documents use
the shared workspace serializer/validator; no second file format or editor implementation
exists. Transactions update the document and its list entry atomically, and optimistic
revision checks reject conflicting writes from another tab. Browser save success is shown
only after transaction completion. Failed saves keep live edits and the last successful copy;
the user can download, retry, or save a separate copy for a conflict.
Browser autosave prepares the portable workspace with the same `app/file-formats.js`
serializer in a bundled worker. The editor posts already detached tab snapshots;
it does not stringify the entire workspace on the main thread for this step.
New typing, formatting or a different project can continue while serialization
runs. The completed save acknowledges only its captured source; later edits stay
pending. Worker failures use the existing save-failure and download controls.
Live-scene capture, worker transport, thumbnails and IndexedDB writes still have
main-thread costs; this change does not establish dense-PDF responsiveness.
To remove the currently open project's browser copy, first open another project or return
to the initial Saved work list. This prevents the open editor from claiming a deleted copy is saved.

Browser copies do not sync between profiles, devices or different origins. Clearing site
data removes them; private browsing does not provide lasting storage. **Keep browser saves**
requests persistent storage, which the browser may decline. Downloaded backups remain
necessary. Undo history and transient selections are not part of the portable file format.
The local library keeps entries until the user removes them or browser storage is cleared;
quota failures are reported instead of silently deleting a project.

Run `python scripts/check-figure-editor-usability-browser.py` from this Figure repository
for current shared-editor and browser-shell authoring acceptance. The following extended
save and packaging checks belong to the consuming Superbench repository and exercise its
selected immutable Figure release.

Run `node --test tests/browserCompletedCapture.test.mjs` for completed-capture
invalidation, byte-identical portable workspaces, the bundled worker and save
ownership controls. Run `py -3 scripts/check-browser-workspace-worker-browser.py`
for actual typing, the visible Bold control, IndexedDB autosave and cold Resume.
That deterministic race check holds only the final response from a real worker;
it is a behavior check, not a performance measurement. Its evidence stays under
`qa_artifacts/browser-workspace-worker/`.

Run `python scripts/check-figure-browser-saves.py` from `core/` for persistent-profile,
embedded-image, file round-trip, failed-transaction, recovery and competing-tab checks.
Evidence stays under `qa_artifacts/figure-browser-saves/<run>/`.
Run `python scripts/check-figure-web-launch-browser.py` for the website-to-editor
HTTP journey, local-file guidance and recovery from an unavailable editor dependency.
Evidence stays under `qa_artifacts/figure-web-launch/<run>/`.

Build the matching browser and Superbench release from one committed revision:

```powershell
py -3 scripts/figure_tool_package_producer.py --revision <full-commit> --distribution-scope public-release --artifacts-only --source-exports --output-root qa_artifacts/u9
```

See `docs/UNIFIED_FIGURE_RELEASE.md` for qualification, exact source export,
website mounting and local trusted-package promotion. The shared payload stays
unchanged in both archives; the website adds its root launcher outside that payload.

The illustrated manual is also available at `app/help/index.html#help/getting-started` beneath the package root. It shares its catalog and renderer with in-app Help, and is included in the existing static payload. In the editor, choose **Help > Search Help** and use the article footer to open a separate page. See `docs/HELP_CONTENT.md` in this Figure repository.
