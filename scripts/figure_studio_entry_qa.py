#!/usr/bin/env python3
"""Visible Figure Studio document-entry helpers for browser acceptance.

The helpers deliberately use the same New Document dialog, File menu, and
panel-restore controls available to an author. They do not seed application
state or call Figure Studio's QA scenario APIs.
"""

from __future__ import annotations

from typing import Any


DOCUMENT_PRESETS = {
    "figure": frozenset({"double-column", "single-column", "full-page", "graphical-abstract", "a4", "custom"}),
    "presentation": frozenset({"presentation-wide", "presentation-standard", "custom"}),
}


def validate_document_entry(kind: str, preset: str, name: str) -> tuple[str, str, str]:
    normalized_kind = str(kind or "").strip().lower()
    normalized_preset = str(preset or "").strip().lower()
    normalized_name = str(name or "").strip()
    if normalized_kind not in DOCUMENT_PRESETS:
        raise ValueError(f"Unsupported Figure Studio document kind: {kind!r}")
    if normalized_preset not in DOCUMENT_PRESETS[normalized_kind]:
        raise ValueError(f"Preset {preset!r} is not valid for {normalized_kind} documents")
    if not normalized_name:
        raise ValueError("Figure Studio acceptance documents require an explicit name")
    return normalized_kind, normalized_preset, normalized_name


def _entry_state_script() -> str:
    return """() => {
      const app = window.FigureStudio?.app;
      const mode = app?.getDocumentModeState?.() || {};
      const workspace = app?.getDocumentWorkspaceStateForQa?.() || {};
      const root = document.querySelector('.figure-studio-root');
      const canvasStage = document.getElementById('canvasStage');
      const canvas = document.querySelector('canvas.upper-canvas');
      const canvasRect = canvas?.getBoundingClientRect();
      return {
        schema: 'figureStudio.currentDocumentEntry.browserQa.v1',
        documentKind: mode.document?.kind || '',
        documentTitle: mode.title || '',
        artboardPreset: mode.document?.pageGeometry?.defaultArtboard?.preset || '',
        activeWorkspace: workspace.activeKind || '',
        activeDocumentId: workspace.workspaces?.[mode.document?.kind]?.activeId || '',
        routeReady: root?.dataset.qaRouteReady || '',
        layoutStable: root?.dataset.qaLayoutStable || '',
        canvasMarker: canvasStage?.dataset.qaCanvas || '',
        canvasVisible: Boolean(canvasRect && canvasRect.width > 0 && canvasRect.height > 0),
        activeElement: document.activeElement?.id || document.activeElement?.getAttribute?.('data-command') || '',
        activeDocumentTab: Boolean(document.activeElement?.matches?.('[data-document-tab-id][aria-selected="true"]'))
      };
    }"""


def _assert_entry_state(state: dict[str, Any], kind: str, preset: str, name: str, expected_focus: str) -> None:
    if expected_focus == '#documentTabs [data-document-tab-id][aria-selected="true"]':
        focus_restored = state.get("activeDocumentTab") is True
    elif expected_focus == "#fileMenuTrigger":
        focus_restored = state.get("activeElement") == "fileMenuTrigger"
    else:
        focus_restored = state.get("activeElement") == "newProjectBtn"
    checks = {
        "document kind": state.get("documentKind") == kind,
        "document title": state.get("documentTitle") == name,
        "artboard preset": state.get("artboardPreset") == preset,
        "active workspace": state.get("activeWorkspace") == kind,
        "active document identity": bool(state.get("activeDocumentId")),
        "route readiness": state.get("routeReady") == "true",
        "layout stability": state.get("layoutStable") == "true",
        "canvas marker": state.get("canvasMarker") == "figure-studio-artboard",
        "visible canvas": state.get("canvasVisible") is True,
        "focus restoration": focus_restored,
    }
    failed = [label for label, passed in checks.items() if not passed]
    if failed:
        raise RuntimeError(f"Current Figure Studio document entry failed {', '.join(failed)}: {state}")


def enter_current_document_sync(
    subject: Any,
    *,
    kind: str,
    preset: str,
    name: str,
    layout_id: str | None = None,
    theme_id: str | None = None,
    timeout_ms: int = 45_000,
) -> dict[str, Any]:
    """Create one document through the visible sync Playwright surface."""

    kind, preset, name = validate_document_entry(kind, preset, name)
    subject.wait_for_function("window.FigureStudio?.app?.isReady === true", timeout=timeout_ms)
    subject.locator('.figure-studio-root[data-qa-route-ready="true"]').wait_for(state="attached", timeout=timeout_ms)
    subject.locator('.figure-studio-root[data-qa-layout-stable="true"]').wait_for(state="attached", timeout=timeout_ms)
    backdrop = subject.locator("#newDocumentBackdrop")
    if backdrop.is_visible():
        entry = "first-run"
        expected_focus = '#documentTabs [data-document-tab-id][aria-selected="true"]'
    else:
        subject.locator('[data-menu="file"] > .menu-trigger').click()
        subject.locator('[data-menu="file"] [data-command="new-project"]').click()
        entry = "file-menu"
        expected_focus = "#fileMenuTrigger"
    backdrop.wait_for(state="visible", timeout=timeout_ms)
    subject.locator(f'[data-new-document-kind="{kind}"]').click()
    uses_size_selector = subject.locator("#newDocumentSizeInput").count() > 0
    effective_preset = "custom" if preset == "a4" or (uses_size_selector and preset in {"single-column", "graphical-abstract"}) else preset
    selected_size = "custom" if uses_size_selector and preset in {"single-column", "graphical-abstract"} else preset
    if uses_size_selector:
        subject.locator("#newDocumentSizeInput").select_option(selected_size)
    else:
        # Immutable historical candidates retain their original preset cards.
        subject.locator(f'[data-new-document-preset="{preset}"]').click()
    if uses_size_selector and preset in {"single-column", "graphical-abstract"}:
        width, height = (3.35, 4.8) if preset == "single-column" else (7.1, 3.2)
        subject.locator("#newDocumentWidthInput").fill(str(width))
        subject.locator("#newDocumentHeightInput").fill(str(height))
    subject.locator("#newDocumentNameInput").fill(name)
    if kind == "presentation" and layout_id:
        subject.locator("#newDocumentLayoutInput").select_option(layout_id)
    if kind == "presentation" and theme_id:
        subject.locator("#newDocumentThemeInput").select_option(theme_id)
    selection = subject.evaluate(
        """([kind, preset]) => ({
          kind: document.querySelector(`[data-new-document-kind="${kind}"]`)?.getAttribute('aria-checked'),
          preset: document.getElementById("newDocumentSizeInput")
            ? (document.getElementById("newDocumentSizeInput").value === preset ? "true" : "false")
            : document.querySelector(`[data-new-document-preset="${preset}"]`)?.getAttribute('aria-checked')
        })""",
        [kind, selected_size],
    )
    if selection != {"kind": "true", "preset": "true"}:
        raise RuntimeError(f"New Document did not retain the requested kind and preset: {selection}")
    subject.locator("#createNewDocumentBtn").click()
    backdrop.wait_for(state="hidden", timeout=timeout_ms)
    subject.wait_for_function(
        "([kind, name]) => window.FigureStudio.app.getDocumentModeState().document.kind === kind && window.FigureStudio.app.getDocumentModeState().title === name",
        arg=[kind, name],
        timeout=timeout_ms,
    )
    subject.locator('.figure-studio-root[data-qa-layout-stable="true"]').wait_for(state="attached", timeout=timeout_ms)
    subject.locator('canvas.upper-canvas').wait_for(state="visible", timeout=timeout_ms)
    subject.wait_for_function("selector => document.activeElement?.matches?.(selector) === true", arg=expected_focus, timeout=timeout_ms)
    state = subject.evaluate(_entry_state_script())
    state.update({"entry": entry, "requestedKind": kind, "requestedPreset": preset, "requestedLayout": layout_id or "", "expectedFocus": expected_focus})
    _assert_entry_state(state, kind, effective_preset, name, expected_focus)
    return state


async def enter_current_document_async(
    subject: Any,
    *,
    kind: str,
    preset: str,
    name: str,
    layout_id: str | None = None,
    theme_id: str | None = None,
    timeout_ms: int = 45_000,
) -> dict[str, Any]:
    """Create one document through the visible async Playwright surface."""

    kind, preset, name = validate_document_entry(kind, preset, name)
    await subject.wait_for_function("window.FigureStudio?.app?.isReady === true", timeout=timeout_ms)
    await subject.locator('.figure-studio-root[data-qa-route-ready="true"]').wait_for(state="attached", timeout=timeout_ms)
    await subject.locator('.figure-studio-root[data-qa-layout-stable="true"]').wait_for(state="attached", timeout=timeout_ms)
    backdrop = subject.locator("#newDocumentBackdrop")
    if await backdrop.is_visible():
        entry = "first-run"
        expected_focus = '#documentTabs [data-document-tab-id][aria-selected="true"]'
    else:
        await subject.locator('[data-menu="file"] > .menu-trigger').click()
        await subject.locator('[data-menu="file"] [data-command="new-project"]').click()
        entry = "file-menu"
        expected_focus = "#fileMenuTrigger"
    await backdrop.wait_for(state="visible", timeout=timeout_ms)
    await subject.locator(f'[data-new-document-kind="{kind}"]').click()
    uses_size_selector = await subject.locator("#newDocumentSizeInput").count() > 0
    effective_preset = "custom" if preset == "a4" or (uses_size_selector and preset in {"single-column", "graphical-abstract"}) else preset
    selected_size = "custom" if uses_size_selector and preset in {"single-column", "graphical-abstract"} else preset
    if uses_size_selector:
        await subject.locator("#newDocumentSizeInput").select_option(selected_size)
    else:
        # Immutable historical candidates retain their original preset cards.
        await subject.locator(f'[data-new-document-preset="{preset}"]').click()
    if uses_size_selector and preset in {"single-column", "graphical-abstract"}:
        width, height = (3.35, 4.8) if preset == "single-column" else (7.1, 3.2)
        await subject.locator("#newDocumentWidthInput").fill(str(width))
        await subject.locator("#newDocumentHeightInput").fill(str(height))
    await subject.locator("#newDocumentNameInput").fill(name)
    if kind == "presentation" and layout_id:
        await subject.locator("#newDocumentLayoutInput").select_option(layout_id)
    if kind == "presentation" and theme_id:
        await subject.locator("#newDocumentThemeInput").select_option(theme_id)
    selection = await subject.evaluate(
        """([kind, preset]) => ({
          kind: document.querySelector(`[data-new-document-kind="${kind}"]`)?.getAttribute('aria-checked'),
          preset: document.getElementById("newDocumentSizeInput")
            ? (document.getElementById("newDocumentSizeInput").value === preset ? "true" : "false")
            : document.querySelector(`[data-new-document-preset="${preset}"]`)?.getAttribute('aria-checked')
        })""",
        [kind, selected_size],
    )
    if selection != {"kind": "true", "preset": "true"}:
        raise RuntimeError(f"New Document did not retain the requested kind and preset: {selection}")
    await subject.locator("#createNewDocumentBtn").click()
    await backdrop.wait_for(state="hidden", timeout=timeout_ms)
    await subject.wait_for_function(
        "([kind, name]) => window.FigureStudio.app.getDocumentModeState().document.kind === kind && window.FigureStudio.app.getDocumentModeState().title === name",
        arg=[kind, name],
        timeout=timeout_ms,
    )
    await subject.locator('.figure-studio-root[data-qa-layout-stable="true"]').wait_for(state="attached", timeout=timeout_ms)
    await subject.locator('canvas.upper-canvas').wait_for(state="visible", timeout=timeout_ms)
    await subject.wait_for_function("selector => document.activeElement?.matches?.(selector) === true", arg=expected_focus, timeout=timeout_ms)
    state = await subject.evaluate(_entry_state_script())
    state.update({"entry": entry, "requestedKind": kind, "requestedPreset": preset, "requestedLayout": layout_id or "", "expectedFocus": expected_focus})
    _assert_entry_state(state, kind, effective_preset, name, expected_focus)
    return state


def show_library_sync(subject: Any, *, tab: str = "tools", timeout_ms: int = 45_000) -> dict[str, Any]:
    """Open the Library through its visible restore control and select a tab."""

    panel = subject.locator('[data-rail-panel="left"]')
    if not panel.is_visible():
        subject.locator('[data-rail-action="show"][data-rail="left"]').click()
        panel.wait_for(state="visible", timeout=timeout_ms)
    presentation_slides = tab == "slides" and subject.evaluate(
        "() => document.querySelector('.figure-studio-root')?.dataset.documentKind === 'presentation'"
    )
    if presentation_slides:
        active_pane = subject.evaluate("() => document.querySelector('.figure-studio-root')?.dataset.deckPane || 'slides'")
        if active_pane != "slides":
            command = "design" if active_pane == "design" else "assets"
            subject.locator(f'.presentation-toolbar [data-deck-command="{command}"]').click()
            subject.wait_for_function("document.querySelector('.figure-studio-root')?.dataset.deckPane === 'slides'", timeout=timeout_ms)
        return {"panelVisible": panel.is_visible(), "tab": tab, "tabActive": True}
    figure_library = tab == "tools" and subject.evaluate(
        "() => { const root = document.querySelector('.figure-studio-root'); return root?.dataset.documentKind === 'figure' && Boolean(root?.dataset.figureLayout); }"
    )
    if figure_library:
        active = subject.evaluate("() => document.querySelector('[data-sidebar-panel].active')?.dataset.sidebarPanel === 'tools'")
        if not active:
            raise RuntimeError("The Figure Library panel is not active in the current Figure layout.")
        return {"panelVisible": panel.is_visible(), "tab": tab, "tabActive": True}
    tab_button = subject.locator(f'[data-sidebar-tab="{tab}"]')
    tab_button.wait_for(state="visible", timeout=timeout_ms)
    tab_button.click()
    return {"panelVisible": panel.is_visible(), "tab": tab, "tabActive": "active" in (tab_button.get_attribute("class") or "").split()}


async def show_library_async(subject: Any, *, tab: str = "tools", timeout_ms: int = 45_000) -> dict[str, Any]:
    """Open the Library through its visible restore control and select a tab."""

    panel = subject.locator('[data-rail-panel="left"]')
    if not await panel.is_visible():
        await subject.locator('[data-rail-action="show"][data-rail="left"]').click()
        await panel.wait_for(state="visible", timeout=timeout_ms)
    presentation_slides = tab == "slides" and await subject.evaluate(
        "() => document.querySelector('.figure-studio-root')?.dataset.documentKind === 'presentation'"
    )
    if presentation_slides:
        active_pane = await subject.evaluate("() => document.querySelector('.figure-studio-root')?.dataset.deckPane || 'slides'")
        if active_pane != "slides":
            command = "design" if active_pane == "design" else "assets"
            await subject.locator(f'.presentation-toolbar [data-deck-command="{command}"]').click()
            await subject.wait_for_function("document.querySelector('.figure-studio-root')?.dataset.deckPane === 'slides'", timeout=timeout_ms)
        return {"panelVisible": await panel.is_visible(), "tab": tab, "tabActive": True}
    figure_library = tab == "tools" and await subject.evaluate(
        "() => { const root = document.querySelector('.figure-studio-root'); return root?.dataset.documentKind === 'figure' && Boolean(root?.dataset.figureLayout); }"
    )
    if figure_library:
        active = await subject.evaluate("() => document.querySelector('[data-sidebar-panel].active')?.dataset.sidebarPanel === 'tools'")
        if not active:
            raise RuntimeError("The Figure Library panel is not active in the current Figure layout.")
        return {"panelVisible": await panel.is_visible(), "tab": tab, "tabActive": True}
    tab_button = subject.locator(f'[data-sidebar-tab="{tab}"]')
    await tab_button.wait_for(state="visible", timeout=timeout_ms)
    await tab_button.click()
    return {"panelVisible": await panel.is_visible(), "tab": tab, "tabActive": "active" in (await tab_button.get_attribute("class") or "").split()}
