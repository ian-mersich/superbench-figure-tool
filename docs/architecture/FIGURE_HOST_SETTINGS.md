# Figure appearance and host settings

The web edition and Mersich Lab Superbench consume one canonical Figure editor
release. Editing behavior, document formats, styles, vendor files, Library
drawings and scenes come from the same committed package. A host can provide its
own settings and surrounding controls without creating a second editor.

Personal preferences do not need to synchronize between the website, browser
profiles and Superbench. A user may prefer a dark website and a light desktop
workspace while editing the same portable figure.

## Ownership

| Concern | Web edition | Superbench |
| --- | --- | --- |
| Interface appearance | The web entry owns its visible appearance control, system preference and remembered browser choice. | Global App Settings owns theme, accent and interface density for the workspace, including Figure and Present. |
| Document colors | The shared editor owns artwork fills, strokes, part colors, slide backgrounds and presentation themes. | The same shared editor and document values apply. |
| File access | The browser entry supplies supported file inputs, downloads and browser save controls. | The host supplies supported native file services through its adapters. |
| Local persistence | Browser preferences and browser project saves belong to their documented browser/profile/origin stores. | Desktop preferences and project files belong to their existing host stores and file services. |
| Licensing and service availability | The host entry can present About, legal information and explanations of unavailable services. | The desktop can present its own About, legal information and native-service availability. |

Host differences belong in the entry, surrounding shell or explicit adapters.
They must not fork core editing tools, reduce the shared Library, change drawing
identities, introduce different document semantics or condition core editing on
which host is running. Legal presentation can differ; the underlying code,
artwork permissions and required notices remain those of the shared release.
Unavailable native services must be described honestly rather than replaced by
different editor behavior.

## Existing appearance interface

The ready editor exposes:

```javascript
window.FigureStudio.app.applyProjectAppearance({
  theme: "light",            // e.g. "dark-graphite" or "system"
  effectiveTheme: "light",   // the host-resolved system choice, when applicable
  accent: "amber",
  density: "spacious"
});
```

The implementation is in `app/app.js`. It applies normalized appearance tokens
to the editor's interface. It does not recolor artwork or serialize interface
preferences into a figure, slide or workspace document. The existing technical
method name is retained for compatibility.

The Superbench authoring shell calls this method when the child editor becomes
ready and when global appearance settings change. Superbench owns its existing
normalization, persistence and system-theme listener. The web entry owns the
equivalent browser preference lifecycle and calls the same editor method. A
browser preference storage failure must still permit a choice for that visit.

The currently compatible Superbench host does not expose an editor-facing
`openSettings` action, appearance setter or settings request capability.
`openAppSettings` is private to its authoring shell. The shared editor must not
click the parent's DOM, edit host preference storage or manufacture a host action
to open that dialog. Its existing App Settings entry remains the desktop control.
A future shortcut from inside Figure would need an explicit host callback or
capability and separate host qualification; it is not needed for a web appearance
control.

## Release boundary

Develop shared editing changes once in `app/` and the canonical asset roots.
Develop browser controls in `web/` and Superbench framing in its host source.
The web entry is part of the same Figure package, but only the browser entry
loads its controls and styles. Desktop users need not acquire a browser-specific
control merely because that code ships in the complete shared package.

Build both Figure deployment archives from one committed revision, compare the
complete payload, and qualify that candidate before publication and pin changes.
Do not patch deployed web files separately, keep a web-only editor branch, or
maintain host-specific editor versions. A wrapper-only runtime change still
follows the shared Figure release procedure. A compatible host can consume the
new Figure package without a host rebuild; a new host capability requires its
own host validation.

See [the unified release procedure](../UNIFIED_FIGURE_RELEASE.md) for artifact
identity and promotion. This architecture note does not select a new release or
change either consumer's pin.

## Acceptance principles

- Verify the visible browser appearance control at 1280 × 800, 1440 × 1000 and
  1920 × 1080 in light and dark, including keyboard operation, focus and legible
  active/inactive states. Inspect original-resolution captures independently.
- Verify the web entry follows the system before an explicit choice, applies a
  choice immediately to shell and editor, remembers it after a cold visit, and
  remains usable when preference storage is blocked.
- Verify Superbench retains its global Settings control and does not acquire
  browser-only controls. Its appearance changes must reach both Figure and
  Present, including an editor becoming ready after the setting changes.
- Compare authored document values before and after an interface change: artwork
  colors, object identities, hierarchy and history must be unchanged. Appearance
  changes must not mark a saved scientific document as edited.
- Run switching, selection and actual Save/cold Open checks in light/dark at all
  three desktop widths against the same candidate package in both entries and
  the compatible hidden native host. Preferences are host state, not a reason to
  weaken authored-workspace equality checks.
- Verify the full served payload, source pin and installed selection against the
  exact accepted package. A matching version label alone is insufficient.

Use the existing unattended browser and hidden native runners. Keep controlled
native file transport distinct from OS dialog or end-to-end native IPC
qualification, and retain those limits in the acceptance record.
