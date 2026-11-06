#!/usr/bin/env python3
"""Focused browser QA for drag-create tools and Direct Selection handles."""

from __future__ import annotations

import argparse
import asyncio
import json
import socket
import subprocess
import sys
import time
from pathlib import Path

from PIL import Image, ImageDraw
from playwright.async_api import async_playwright


FIGURE_STORY_ROUTE = "/modules/figure-story"
ACTIVE_FIGURE_HOST_FRAME_SELECTOR = (
    '[data-retained-surface-active="true"][data-qa-route="/modules/figure-story"]'
    ':not([hidden]):not([aria-hidden="true"]) '
    '[data-standalone-host-root][data-standalone-state-slot="figure_studio"] '
    '[data-standalone-host-frame]'
)


async def dismiss_first_run_surface(surface) -> None:
    backdrop = surface.locator("#newDocumentBackdrop")
    if await backdrop.count() and await backdrop.is_visible():
        await surface.locator("#closeNewDocumentBtn").click()
        await backdrop.wait_for(state="hidden")


class FigureSurface:
    """Route app calls into the direct page or the hosted same-origin frame."""

    def __init__(self, browser_page, app_frame=None, frame_locator=None, readiness=None):
        self.browser_page = browser_page
        self.app_frame = app_frame or browser_page
        self.frame_locator = frame_locator
        self.readiness = readiness or {}

    @property
    def mouse(self):
        return self.browser_page.mouse

    @property
    def keyboard(self):
        return self.browser_page.keyboard

    def locator(self, selector: str):
        # A FrameLocator follows the active, scoped iframe rather than retaining
        # an ElementHandle to a previous retained-surface frame.
        if self.frame_locator:
            return self.browser_page.frame_locator(ACTIVE_FIGURE_HOST_FRAME_SELECTOR).locator(selector)
        return self.app_frame.locator(selector)

    async def evaluate(self, expression: str, arg=None):
        if not self.frame_locator:
            return await self.app_frame.evaluate(expression, arg)
        return await self._with_live_frame(lambda frame: frame.evaluate(expression, arg))

    async def reacquire(self, timeout_ms: int = 10000):
        """Return the one active Figure iframe, reacquiring it after replacement."""
        if not self.frame_locator:
            return self.app_frame
        deadline = time.monotonic() + timeout_ms / 1000
        last_count = 0
        last_url = ""
        while time.monotonic() < deadline:
            try:
                count = await self.frame_locator.count()
                last_count = count
                if count == 1:
                    handle = await self.frame_locator.element_handle()
                    frame = await handle.content_frame() if handle else None
                    if frame:
                        last_url = frame.url
                        if await frame.evaluate("window.FigureStudio?.app?.isReady === true"):
                            self.app_frame = frame
                            self.readiness["frameUrl"] = frame.url
                            self.readiness["reacquired"] = int(self.readiness.get("reacquired", 0)) + 1
                            return frame
            except Exception:
                # The host may have removed the frame between count and lookup.
                pass
            await self.browser_page.wait_for_timeout(50)
        raise RuntimeError(
            "Active BSD-hosted Figure Studio frame was not ready "
            f"(activeFrameCount={last_count}, frameUrl={last_url!r})."
        )

    async def _with_live_frame(self, operation):
        last_error = None
        for attempt in range(2):
            frame = await self.reacquire()
            try:
                return await operation(frame)
            except Exception as error:
                last_error = error
                if attempt == 0:
                    await self.browser_page.wait_for_timeout(50)
        raise last_error

    async def wait_for_timeout(self, timeout: int):
        await self.browser_page.wait_for_timeout(timeout)

    async def wait_for_visual_stability(self):
        async def stabilize(target):
            await target.evaluate(
                """async () => {
                  document.documentElement.dataset.qaCaptureStable = 'true';
                  if (!document.getElementById('figure-qa-stable-capture')) {
                    const style = document.createElement('style');
                    style.id = 'figure-qa-stable-capture';
                    style.textContent = '*,*::before,*::after{animation:none!important;transition:none!important;caret-color:transparent!important}';
                    document.head.append(style);
                  }
                  if (document.fonts?.ready) await document.fonts.ready;
                  await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
                }"""
            )
        await stabilize(self.browser_page)
        if self.frame_locator:
            async def wait_for_layout(frame):
                await stabilize(frame)
                await frame.wait_for_function(
                    "document.querySelector('.figure-studio-root')?.dataset.qaLayoutStable === 'true'",
                    timeout=10000,
                )
            await self._with_live_frame(wait_for_layout)
        else:
            await self.app_frame.wait_for_function(
                "document.querySelector('.figure-studio-root')?.dataset.qaLayoutStable === 'true'",
                timeout=10000,
            )
        await self.browser_page.wait_for_timeout(40)

    async def screenshot(self, **kwargs):
        await self.wait_for_visual_stability()
        await self.browser_page.screenshot(**kwargs)

    async def main_client_point(self, point: dict[str, float]) -> dict[str, float]:
        if not self.frame_locator:
            return point
        await self.reacquire()
        box = await self.frame_locator.bounding_box()
        if not box:
            raise RuntimeError("BSD-hosted Figure Studio frame has no bounding box.")
        return {"x": box["x"] + point["x"], "y": box["y"] + point["y"]}


async def resolve_figure_surface(browser_page, timeout_ms: int = 90000) -> FigureSurface:
    """Resolve a direct app or the current hosted frame without retaining a stale iframe."""
    started = time.monotonic()
    deadline = started + timeout_ms / 1000
    attempts = 0
    frame_locator = browser_page.locator(ACTIVE_FIGURE_HOST_FRAME_SELECTOR)
    active_frame_count = 0
    while time.monotonic() < deadline:
        attempts += 1
        try:
            if await browser_page.evaluate("window.FigureStudio?.app?.isReady === true"):
                return FigureSurface(
                    browser_page,
                    readiness={"mode": "direct", "attempts": attempts, "elapsedMs": round((time.monotonic() - started) * 1000)},
                )
        except Exception:
            pass

        # Do not scan ready child frames: retained inactive panes can contain
        # another Figure Studio iframe. The shell's active route is the only
        # surface that is valid for authoring and client-coordinate mapping.
        try:
            active_frame_count = await frame_locator.count()
            if active_frame_count == 1:
                handle = await frame_locator.element_handle()
                frame = await handle.content_frame() if handle else None
                if frame and await frame.evaluate("window.FigureStudio?.app?.isReady === true"):
                    return FigureSurface(
                        browser_page,
                        frame,
                        frame_locator,
                        readiness={
                            "mode": "hosted",
                            "attempts": attempts,
                            "elapsedMs": round((time.monotonic() - started) * 1000),
                            "frameUrl": frame.url,
                        },
                    )
        except Exception:
            pass
        await browser_page.wait_for_timeout(100)

    try:
        outer_ready = await browser_page.locator('[data-qa-route-ready="true"]').count()
    except Exception:
        outer_ready = 0
    raise RuntimeError(
        "Figure Studio readiness timed out after "
        f"{timeout_ms} ms (outerRouteReady={outer_ready}, activeFrameCount={active_frame_count}, attempts={attempts})."
    )


def parse_args() -> argparse.Namespace:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="Check Figure Studio drag-create and direct-selection handles.")
    parser.add_argument("--root", type=Path, default=root)
    parser.add_argument("--output-dir", type=Path, default=root / "qa_artifacts" / "direct-selection-draw")
    parser.add_argument("--timeout-ms", type=int, default=90000)
    parser.add_argument("--url", default="", help="Reuse an already-running direct or BSD-hosted Figure Studio URL.")
    parser.add_argument("--viewport", default="1440x1000", help="Desktop viewport as WIDTHxHEIGHT.")
    return parser.parse_args()


def parse_viewport(value: str) -> dict[str, int]:
    try:
        width, height = (int(part) for part in value.lower().split("x", 1))
    except (TypeError, ValueError):
        raise argparse.ArgumentTypeError("viewport must be WIDTHxHEIGHT") from None
    if width < 960 or height < 640:
        raise argparse.ArgumentTypeError("viewport must be a desktop size")
    return {"width": width, "height": height}


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


async def wait_for_server(port: int, timeout_s: float = 20) -> None:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.25):
                return
        except OSError:
            await asyncio.sleep(0.1)
    raise RuntimeError(f"Figure Studio server did not start on port {port}.")


async def wait_for_port_closed(port: int, timeout_s: float = 5) -> bool:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.25):
                await asyncio.sleep(0.15)
        except OSError:
            return True
    return False


def write_contact_sheet(output_dir: Path, screenshots: dict[str, str]) -> Path:
    entries = [(label, Path(path)) for label, path in screenshots.items() if Path(path).exists()]
    card_w, card_h, gap, cols = 620, 460, 18, 2
    rows = max(1, (len(entries) + cols - 1) // cols)
    sheet = Image.new("RGB", (cols * card_w + (cols + 1) * gap, rows * card_h + (rows + 1) * gap), "#eef2f4")
    draw = ImageDraw.Draw(sheet)
    for index, (label, path) in enumerate(entries):
        x = gap + (index % cols) * (card_w + gap)
        y = gap + (index // cols) * (card_h + gap)
        draw.rounded_rectangle((x, y, x + card_w, y + card_h), radius=8, fill="#ffffff", outline="#cbd5dc")
        draw.text((x + 14, y + 12), label, fill="#101820")
        image = Image.open(path).convert("RGB")
        image.thumbnail((card_w - 28, card_h - 58), Image.Resampling.LANCZOS)
        sheet.paste(image, (x + (card_w - image.width) // 2, y + 42))
    path = output_dir / "contact-sheet.png"
    sheet.save(path)
    return path


def endpoints_close(left: object, right: object, tolerance: float = 1.5) -> bool:
    if not isinstance(left, dict) or not isinstance(right, dict):
        return False
    for role in ("start", "end"):
        a = left.get(role, {}) if isinstance(left.get(role, {}), dict) else {}
        b = right.get(role, {}) if isinstance(right.get(role, {}), dict) else {}
        if abs(float(a.get("x", 0)) - float(b.get("x", 0))) > tolerance:
            return False
        if abs(float(a.get("y", 0)) - float(b.get("y", 0))) > tolerance:
            return False
    return True


def is_45_constrained(endpoints: object, tolerance: float = 1.75) -> bool:
    if not isinstance(endpoints, dict):
        return False
    start = endpoints.get("start", {}) if isinstance(endpoints.get("start", {}), dict) else {}
    end = endpoints.get("end", {}) if isinstance(endpoints.get("end", {}), dict) else {}
    dx = abs(float(end.get("x", 0)) - float(start.get("x", 0)))
    dy = abs(float(end.get("y", 0)) - float(start.get("y", 0)))
    return dx <= tolerance or dy <= tolerance or abs(dx - dy) <= tolerance


async def capture(page, screenshots: dict[str, str], output_dir: Path, filename: str, label: str) -> None:
    path = output_dir / filename
    await page.screenshot(path=str(path), full_page=False)
    screenshots[label] = str(path)


async def canvas_scene_point(page, x: float, y: float) -> dict[str, float]:
    local = await page.evaluate(
        """({x, y}) => window.FigureStudio.app.sceneToClientForQa({ x, y })""",
        {"x": x, "y": y},
    )
    return await page.main_client_point(local)


async def choose_tool(page, family_tool: str, tool: str) -> None:
    if family_tool:
        await page.locator(f'.tool-primary[data-tool="{family_tool}"]').click()
        await page.locator(f'.tool-popover [data-tool="{tool}"]').click()
    else:
        await page.locator(f'[data-tool="{tool}"]').click()


async def drag_scene(page, start: tuple[float, float], end: tuple[float, float]) -> None:
    a = await canvas_scene_point(page, *start)
    b = await canvas_scene_point(page, *end)
    await page.mouse.move(a["x"], a["y"])
    await page.mouse.down()
    await page.mouse.move(b["x"], b["y"], steps=10)
    await page.mouse.up()


async def begin_marquee_scene(page, start: tuple[float, float], end: tuple[float, float]) -> None:
    first = await canvas_scene_point(page, *start)
    last = await canvas_scene_point(page, *end)
    await page.mouse.move(first["x"], first["y"])
    await page.mouse.down()
    await page.mouse.move(last["x"], last["y"], steps=10)


async def lasso_scene(page, points: list[tuple[float, float]]) -> None:
    if len(points) < 2:
        return
    first = await canvas_scene_point(page, *points[0])
    await page.mouse.move(first["x"], first["y"])
    await page.mouse.down()
    for point in points[1:]:
        mapped = await canvas_scene_point(page, *point)
        await page.mouse.move(mapped["x"], mapped["y"], steps=3)
    await page.mouse.up()


def handle_positions_equal(before: object, after: object, tolerance: float = 0.6) -> bool:
    if not isinstance(before, list) or not isinstance(after, list) or len(before) != len(after):
        return False
    return all(
        isinstance(left, dict)
        and isinstance(right, dict)
        and left.get("objectId") == right.get("objectId")
        and left.get("commandIndex") == right.get("commandIndex")
        and left.get("handleType") == right.get("handleType")
        and abs(float(left.get("x", 0)) - float(right.get("x", 0))) <= tolerance
        and abs(float(left.get("y", 0)) - float(right.get("y", 0))) <= tolerance
        for left, right in zip(before, after)
    )


async def run_browser(
    root: Path,
    output_dir: Path,
    timeout_ms: int,
    url: str = "",
    viewport: dict[str, int] | None = None,
) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    port = 0
    server = None
    target_url = url
    if not target_url:
        port = free_port()
        server = subprocess.Popen(
            [sys.executable, str(root / "scripts" / "figure-studio-server.py"), "--root", str(root), "--bind", "127.0.0.1", "--port", str(port)],
            cwd=str(root),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        target_url = f"http://127.0.0.1:{port}"
    screenshots: dict[str, str] = {}
    console_errors: list[str] = []
    states: dict[str, object] = {}
    server_port_closed = False
    try:
        if server:
            await wait_for_server(port)
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=True)
            browser_page = await browser.new_page(viewport=viewport or {"width": 1440, "height": 1000}, device_scale_factor=1)
            browser_page.set_default_timeout(timeout_ms)
            browser_page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
            await browser_page.goto(target_url, wait_until="domcontentloaded")
            page = await resolve_figure_surface(browser_page)
            await dismiss_first_run_surface(page)
            # The detailed drawing rail belongs to Advanced layout. Choose it
            # through the real UI before looking for its native tool buttons.
            await page.locator('[data-figure-layout-choice="advanced"]').click()
            await page.wait_for_visual_stability()

            await choose_tool(page, "rect", "rect")
            await drag_scene(page, (120, 108), (330, 236))
            states["rect"] = await page.evaluate("() => window.FigureStudio.app.getSelectionStateForQa()")
            await capture(page, screenshots, output_dir, "01-drag-rectangle.png", "1. Drag-created rectangle uses drag bounds")

            await choose_tool(page, "line", "arrow")
            await drag_scene(page, (150, 320), (420, 246))
            states["arrow"] = await page.evaluate("() => window.FigureStudio.app.getSelectionStateForQa()")
            states["arrow_post_create"] = await page.evaluate("() => window.FigureStudio.app.getLineArrowStyleStateForQa()")
            if (
                states["arrow"].get("selectedCount") != 1
                or states["arrow"].get("activeType") == "activeSelection"
                or states["arrow_post_create"].get("tool") != "select"
                or states["arrow_post_create"].get("hasControls") is not False
                or states["arrow_post_create"].get("hasBorders") is not False
            ):
                raise AssertionError(f"Arrow post-create selection contract failed: {states['arrow']} / {states['arrow_post_create']}")
            await capture(page, screenshots, output_dir, "02-drag-arrow.png", "2. Drag-created arrow follows drag vector")

            await choose_tool(page, "", "directSelect")
            await page.wait_for_timeout(150)
            states["direct_entered"] = await page.evaluate("() => window.FigureStudio.app.getDirectSelectionStateForQa()")
            await capture(page, screenshots, output_dir, "03-direct-selection-handles.png", "3. Direct Selection shows endpoint handles")

            handles = page.locator(".path-node-handle")
            first = await handles.nth(0).bounding_box()
            second = await handles.nth(1).bounding_box()
            if not first or not second:
                raise AssertionError("Expected two direct-selection handles.")
            await page.mouse.click(first["x"] + first["width"] / 2, first["y"] + first["height"] / 2)
            await page.keyboard.down("Shift")
            await page.mouse.click(second["x"] + second["width"] / 2, second["y"] + second["height"] / 2)
            await page.keyboard.up("Shift")
            states["multi_selected"] = await page.evaluate("() => window.FigureStudio.app.getDirectSelectionStateForQa()")
            await capture(page, screenshots, output_dir, "04-shift-endpoint-selection.png", "4. Straight line keeps one logical endpoint selected")

            before_drag = states["multi_selected"]
            await page.mouse.move(second["x"] + second["width"] / 2, second["y"] + second["height"] / 2)
            await page.mouse.down()
            await page.mouse.move(second["x"] + 42, second["y"] + 36, steps=8)
            await page.mouse.up()
            states["after_anchor_drag"] = await page.evaluate("() => window.FigureStudio.app.getDirectSelectionStateForQa()")
            states["focus_after_anchor_drag"] = await page.evaluate("() => document.activeElement?.id || ''")
            await capture(page, screenshots, output_dir, "05-single-endpoint-drag.png", "5. Dragging one line endpoint leaves the opposite endpoint fixed")

            await page.keyboard.press("ArrowDown")
            states["after_nudge"] = await page.evaluate("() => window.FigureStudio.app.getDirectSelectionStateForQa()")
            await page.evaluate("() => window.FigureStudio.app.alignSelectionForQa('top')")
            await page.wait_for_timeout(100)
            states["after_align"] = await page.evaluate("() => window.FigureStudio.app.getDirectSelectionStateForQa()")
            await capture(page, screenshots, output_dir, "06-anchor-align.png", "6. Align command works on selected endpoints")
            states["before_drag"] = before_drag

            # A straight line has exactly two logical endpoints. Its Shift drag is
            # an angle constraint, not multi-endpoint translation.
            states["line_before_shift"] = await page.evaluate("() => window.FigureStudio.app.getLineArrowStyleStateForQa()")
            end_handle = page.locator('.path-node-handle[data-command-index="1"][data-handle-type="endpoint"]')
            end_box = await end_handle.bounding_box()
            if not end_box:
                raise AssertionError("Expected the arrow end endpoint handle for Shift constraint QA.")
            await page.mouse.move(end_box["x"] + end_box["width"] / 2, end_box["y"] + end_box["height"] / 2)
            await page.mouse.down()
            await page.keyboard.down("Shift")
            await page.mouse.move(end_box["x"] + 62, end_box["y"] + 19, steps=8)
            await page.keyboard.up("Shift")
            await page.mouse.up()
            states["line_after_shift"] = await page.evaluate("() => window.FigureStudio.app.getLineArrowStyleStateForQa()")
            await capture(page, screenshots, output_dir, "06b-shift-constrained-line-endpoint.png", "6b. Shift constrains one arrow endpoint to a 45-degree direction")

            # Capture remains on the stable overlay even as rerendering replaces
            # the handle button; finish outside the canvas and prove one undo step.
            states["history_before_outside"] = await page.evaluate("() => window.FigureStudio.app.getHistoryStateForQa()")
            states["line_before_outside"] = await page.evaluate("() => window.FigureStudio.app.getLineArrowStyleStateForQa()")
            end_box = await page.locator('.path-node-handle[data-command-index="1"][data-handle-type="endpoint"]').bounding_box()
            if not end_box:
                raise AssertionError("Expected end endpoint handle for outside-canvas capture QA.")
            await page.mouse.move(end_box["x"] + end_box["width"] / 2, end_box["y"] + end_box["height"] / 2)
            await page.mouse.down()
            await page.mouse.move(end_box["x"] + 180, end_box["y"] - 120, steps=12)
            await page.mouse.up()
            states["line_after_outside"] = await page.evaluate("() => window.FigureStudio.app.getLineArrowStyleStateForQa()")
            states["history_after_outside"] = await page.evaluate("() => window.FigureStudio.app.getHistoryStateForQa()")
            await page.evaluate("async () => { await window.FigureStudio.app.undoForQa(); }")
            states["line_after_undo"] = await page.evaluate("() => window.FigureStudio.app.getLineArrowStyleStateForQa()")
            await page.evaluate("async () => { await window.FigureStudio.app.redoForQa(); }")
            states["line_after_redo"] = await page.evaluate("() => window.FigureStudio.app.getLineArrowStyleStateForQa()")
            await choose_tool(page, "", "directSelect")
            await page.wait_for_timeout(120)
            await capture(page, screenshots, output_dir, "06c-outside-canvas-line-endpoint.png", "6c. Endpoint drag completes after leaving the canvas")

            # Cancellation rolls the path back without adding history. Dispatching
            # pointercancel on window exercises the same transaction as a browser
            # capture interruption.
            states["line_before_escape"] = await page.evaluate("() => window.FigureStudio.app.getLineArrowStyleStateForQa()")
            states["history_before_escape"] = await page.evaluate("() => window.FigureStudio.app.getHistoryStateForQa()")
            end_box = await page.locator('.path-node-handle[data-command-index="1"][data-handle-type="endpoint"]').bounding_box()
            if not end_box:
                raise AssertionError("Expected end endpoint handle for Escape rollback QA.")
            await page.mouse.move(end_box["x"] + end_box["width"] / 2, end_box["y"] + end_box["height"] / 2)
            await page.mouse.down()
            await page.mouse.move(end_box["x"] + 56, end_box["y"] + 32, steps=6)
            await page.keyboard.press("Escape")
            await page.mouse.up()
            states["line_after_escape"] = await page.evaluate("() => window.FigureStudio.app.getLineArrowStyleStateForQa()")
            states["history_after_escape"] = await page.evaluate("() => window.FigureStudio.app.getHistoryStateForQa()")

            states["line_before_cancel"] = await page.evaluate("() => window.FigureStudio.app.getLineArrowStyleStateForQa()")
            states["history_before_cancel"] = await page.evaluate("() => window.FigureStudio.app.getHistoryStateForQa()")
            end_box = await page.locator('.path-node-handle[data-command-index="1"][data-handle-type="endpoint"]').bounding_box()
            if not end_box:
                raise AssertionError("Expected end endpoint handle for pointercancel rollback QA.")
            await page.mouse.move(end_box["x"] + end_box["width"] / 2, end_box["y"] + end_box["height"] / 2)
            await page.mouse.down()
            await page.mouse.move(end_box["x"] + 44, end_box["y"] - 38, steps=6)
            await page.evaluate("""() => window.dispatchEvent(new PointerEvent('pointercancel', { bubbles: true, pointerId: 1 }))""")
            await page.mouse.up()
            states["line_after_cancel"] = await page.evaluate("() => window.FigureStudio.app.getLineArrowStyleStateForQa()")
            states["history_after_cancel"] = await page.evaluate("() => window.FigureStudio.app.getHistoryStateForQa()")

            await choose_tool(page, "line", "curve")
            await drag_scene(page, (140, 420), (430, 330))
            states["curve"] = await page.evaluate("() => window.FigureStudio.app.getSelectionStateForQa()")
            await capture(page, screenshots, output_dir, "07-drag-curve.png", "7. Drag-created curve fits drag bounds")

            await choose_tool(page, "", "directSelect")
            await page.wait_for_timeout(120)
            states["curve_direct"] = await page.evaluate("() => window.FigureStudio.app.getDirectSelectionStateForQa()")
            handles_state = states["curve_direct"].get("handles", [])
            if len(handles_state) < 3:
                raise AssertionError("Expected curve direct selection handles.")
            curve_cancel_handle = await handles.nth(0).bounding_box()
            if not curve_cancel_handle:
                raise AssertionError("Expected a curve handle for pointer-cancel QA.")
            states["curve_cancel_before"] = states["curve_direct"]
            await page.mouse.move(
                curve_cancel_handle["x"] + curve_cancel_handle["width"] / 2,
                curve_cancel_handle["y"] + curve_cancel_handle["height"] / 2,
            )
            await page.mouse.down()
            await page.mouse.move(
                curve_cancel_handle["x"] + curve_cancel_handle["width"] / 2 + 34,
                curve_cancel_handle["y"] + curve_cancel_handle["height"] / 2 + 22,
                steps=5,
            )
            await page.evaluate(
                "() => window.dispatchEvent(new PointerEvent('pointercancel', { pointerId: 1, bubbles: true }))"
            )
            await page.mouse.up()
            await page.wait_for_timeout(100)
            states["curve_cancel_after"] = await page.evaluate("() => window.FigureStudio.app.getDirectSelectionStateForQa()")
            curve_handle_boxes = [await handles.nth(index).bounding_box() for index in range(3)]
            curve_handle_boxes = [box for box in curve_handle_boxes if box]
            if len(curve_handle_boxes) < 3:
                raise AssertionError("Expected at least three visible curve handles.")
            await page.mouse.click(curve_handle_boxes[0]["x"] + curve_handle_boxes[0]["width"] / 2, curve_handle_boxes[0]["y"] + curve_handle_boxes[0]["height"] / 2)
            await page.keyboard.down("Shift")
            for box in curve_handle_boxes[1:]:
                await page.mouse.click(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
            await page.keyboard.up("Shift")
            await page.wait_for_timeout(120)
            states["curve_marquee"] = await page.evaluate("() => window.FigureStudio.app.getDirectSelectionStateForQa()")
            await capture(page, screenshots, output_dir, "08-direct-curve-multi-handle.png", "8. Direct Selection selects curve anchors and handles")

            states["multi_scenario"] = await page.evaluate("() => window.FigureStudio.app.createDirectSelectionParityScenarioForQa()")
            await page.wait_for_timeout(120)
            states["multi_direct_before"] = await page.evaluate("() => window.FigureStudio.app.getDirectSelectionStateForQa()")
            states["multi_paths_before_empty_drag"] = await page.evaluate(
                """(ids) => ids.map((id) => {
                    const object = window.FigureStudio.app.getObjectByIdForQa(id);
                    return { id, path: JSON.parse(JSON.stringify(object?.path || [])) };
                })""",
                states["multi_scenario"].get("objectIds", []),
            )
            # Reproduce the reported failure: dragging empty space inside the
            # collective AABB while A is active must start only the point
            # marquee. It must never move the ActiveSelection or its children.
            await begin_marquee_scene(page, (352, 116), (382, 132))
            states["empty_drag_marquee"] = await page.evaluate("() => window.FigureStudio.app.getDirectSelectionStateForQa()")
            await capture(page, screenshots, output_dir, "09-direct-selection-rectangular-marquee.png", "9. Direct Selection uses a quiet rectangular point marquee")
            await page.mouse.up()
            await page.wait_for_timeout(120)
            states["multi_after_empty_drag"] = await page.evaluate("() => window.FigureStudio.app.getDirectSelectionStateForQa()")
            states["multi_paths_after_empty_drag"] = await page.evaluate(
                """(ids) => ids.map((id) => {
                    const object = window.FigureStudio.app.getObjectByIdForQa(id);
                    return { id, path: JSON.parse(JSON.stringify(object?.path || [])) };
                })""",
                states["multi_scenario"].get("objectIds", []),
            )
            await begin_marquee_scene(page, (352, 116), (382, 132))
            await page.keyboard.press("Escape")
            states["marquee_after_escape"] = await page.evaluate("() => window.FigureStudio.app.getDirectSelectionStateForQa()")
            await page.mouse.up()
            await begin_marquee_scene(page, (352, 116), (382, 132))
            await page.evaluate("""() => window.dispatchEvent(new PointerEvent('pointercancel', { bubbles: true, pointerId: 1 }))""")
            states["marquee_after_pointercancel"] = await page.evaluate("() => window.FigureStudio.app.getDirectSelectionStateForQa()")
            await page.mouse.up()
            # A single rectangular marquee selects points across both editable
            # paths. A freeform lasso belongs to a separate future tool.
            await begin_marquee_scene(page, (92, 86), (664, 318))
            states["multi_marquee_visible"] = await page.evaluate(
                """() => {
                    const marker = document.querySelector('.path-direct-marquee');
                    const style = marker ? getComputedStyle(marker) : null;
                    return {
                        direct: window.FigureStudio.app.getDirectSelectionStateForQa(),
                        background: style?.backgroundColor || '',
                        borderStyle: style?.borderStyle || ''
                    };
                }"""
            )
            await page.mouse.up()
            await page.wait_for_timeout(120)
            states["multi_marquee"] = await page.evaluate("() => window.FigureStudio.app.getDirectSelectionStateForQa()")
            await capture(page, screenshots, output_dir, "09b-multi-object-marquee.png", "9b. Rectangular marquee selects handles across separate paths")

            states["multi_move_scenario"] = await page.evaluate(
                "() => window.FigureStudio.app.createDirectSelectionParityScenarioForQa({ history: true })"
            )
            await page.wait_for_timeout(120)
            multi_object_ids = states["multi_move_scenario"].get("objectIds", [])
            if len(multi_object_ids) < 2:
                raise AssertionError("Expected two editable paths for multi-object point editing.")
            first_handle = page.locator(f'.path-node-handle[data-object-id="{multi_object_ids[0]}"]').nth(0)
            second_handle = page.locator(f'.path-node-handle[data-object-id="{multi_object_ids[1]}"]').nth(0)
            first_box = await first_handle.bounding_box()
            second_box = await second_handle.bounding_box()
            if not first_box or not second_box:
                raise AssertionError("Expected visible anchors on both editable paths.")
            await page.mouse.click(first_box["x"] + first_box["width"] / 2, first_box["y"] + first_box["height"] / 2)
            second_box = await page.locator(f'.path-node-handle[data-object-id="{multi_object_ids[1]}"]').nth(0).bounding_box()
            await page.keyboard.down("Shift")
            await page.mouse.click(second_box["x"] + second_box["width"] / 2, second_box["y"] + second_box["height"] / 2)
            await page.keyboard.up("Shift")
            states["multi_points_before"] = await page.evaluate("() => window.FigureStudio.app.getDirectSelectionStateForQa()")
            states["anchor_visual_states"] = await page.evaluate(
                """() => {
                    const read = (element) => {
                        if (!element) return null;
                        const style = getComputedStyle(element, '::after');
                        return {
                            background: style.backgroundColor,
                            borderColor: style.borderColor,
                            borderWidth: style.borderWidth,
                            boxShadow: style.boxShadow,
                            width: style.width,
                            height: style.height
                        };
                    };
                    return {
                        selected: read(document.querySelector('.path-node-handle.selected')),
                        unselected: read(document.querySelector('.path-node-handle:not(.selected)'))
                    };
                }"""
            )
            states["multi_paths_before"] = await page.evaluate(
                """(ids) => ids.map((id) => {
                    const object = window.FigureStudio.app.getObjectByIdForQa(id);
                    return { id, path: JSON.parse(JSON.stringify(object?.path || [])) };
                })""",
                multi_object_ids,
            )
            states["history_before_multi_move"] = await page.evaluate("() => window.FigureStudio.app.getHistoryStateForQa()")
            second_box = await page.locator(f'.path-node-handle[data-object-id="{multi_object_ids[1]}"]').nth(0).bounding_box()
            await page.mouse.move(second_box["x"] + second_box["width"] / 2, second_box["y"] + second_box["height"] / 2)
            await page.mouse.down()
            await page.mouse.move(second_box["x"] + second_box["width"] / 2 + 38, second_box["y"] + second_box["height"] / 2 + 26, steps=8)
            await page.mouse.up()
            await page.wait_for_timeout(120)
            states["multi_points_after"] = await page.evaluate("() => window.FigureStudio.app.getDirectSelectionStateForQa()")
            states["multi_paths_after"] = await page.evaluate(
                """(ids) => ids.map((id) => {
                    const object = window.FigureStudio.app.getObjectByIdForQa(id);
                    return { id, path: JSON.parse(JSON.stringify(object?.path || [])) };
                })""",
                multi_object_ids,
            )
            states["history_after_multi_move"] = await page.evaluate("() => window.FigureStudio.app.getHistoryStateForQa()")
            await capture(page, screenshots, output_dir, "10-multi-object-anchor-drag.png", "10. Selected anchors on separate objects move together")
            await page.evaluate("async () => { await window.FigureStudio.app.undoForQa(); }")
            states["multi_paths_after_undo"] = await page.evaluate(
                """(ids) => ids.map((id) => {
                    const object = window.FigureStudio.app.getObjectByIdForQa(id);
                    return { id, path: JSON.parse(JSON.stringify(object?.path || [])) };
                })""",
                multi_object_ids,
            )
            await page.evaluate("async () => { await window.FigureStudio.app.redoForQa(); }")
            states["multi_paths_after_redo"] = await page.evaluate(
                """(ids) => ids.map((id) => {
                    const object = window.FigureStudio.app.getObjectByIdForQa(id);
                    return { id, path: JSON.parse(JSON.stringify(object?.path || [])) };
                })""",
                multi_object_ids,
            )

            # Precision editing stays on the actual canvas controls: select
            # anchors across two paths, nudge them together, set an exact X,
            # then align and distribute the same logical anchors.
            states["precision_scenario"] = await page.evaluate(
                "() => window.FigureStudio.app.createDirectSelectionParityScenarioForQa({ history: true })"
            )
            precision_ids = states["precision_scenario"].get("objectIds", [])
            if len(precision_ids) < 2:
                raise AssertionError("Expected two paths for precision anchor editing.")
            precision_handles = [
                page.locator(f'.path-node-handle[data-object-id="{precision_ids[0]}"]').nth(0),
                page.locator(f'.path-node-handle[data-object-id="{precision_ids[0]}"]').nth(1),
                page.locator(f'.path-node-handle[data-object-id="{precision_ids[1]}"]').nth(0),
            ]
            precision_boxes = [await handle.bounding_box() for handle in precision_handles]
            if any(box is None for box in precision_boxes):
                raise AssertionError("Expected three direct-selection anchors for precision editing.")
            first_precision_box = precision_boxes[0]
            await page.mouse.click(first_precision_box["x"] + first_precision_box["width"] / 2, first_precision_box["y"] + first_precision_box["height"] / 2)
            await page.keyboard.down("Shift")
            for box in precision_boxes[1:]:
                await page.mouse.click(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
            await page.keyboard.up("Shift")
            await page.wait_for_timeout(100)
            states["precision_before_keyboard"] = await page.evaluate("() => window.FigureStudio.app.getDirectSelectionStateForQa()")
            states["precision_context_before"] = await page.evaluate("() => window.FigureStudio.app.getSelectionContextStateForQa()")
            states["precision_history_before_keyboard"] = await page.evaluate("() => window.FigureStudio.app.getHistoryStateForQa()")
            selected_precision_handle = page.locator(".path-node-handle.selected").last
            await selected_precision_handle.focus()
            await page.keyboard.press("ArrowRight")
            states["precision_after_fine_nudge"] = await page.evaluate("() => window.FigureStudio.app.getDirectSelectionStateForQa()")
            await page.keyboard.press("Shift+ArrowDown")
            states["precision_after_coarse_nudge"] = await page.evaluate("() => window.FigureStudio.app.getDirectSelectionStateForQa()")
            states["precision_history_after_keyboard"] = await page.evaluate("() => window.FigureStudio.app.getHistoryStateForQa()")
            await capture(page, screenshots, output_dir, "10b-multi-anchor-keyboard-nudge.png", "10b. Selected anchors across paths nudge together")

            anchor_x = page.locator('[data-context-property="anchorX"]')
            anchor_y = page.locator('[data-context-property="anchorY"]')
            if await anchor_x.count() != 1 or await anchor_y.count() != 1:
                raise AssertionError("Expected compact direct-selection coordinate controls.")
            states["precision_history_before_coordinate"] = await page.evaluate("() => window.FigureStudio.app.getHistoryStateForQa()")
            states["precision_paths_before_coordinate"] = await page.evaluate(
                """ids => ids.map((id) => ({ id, path: JSON.parse(JSON.stringify(window.FigureStudio.app.getObjectByIdForQa(id)?.path || [])) }))""",
                precision_ids,
            )
            await anchor_x.fill("3.25")
            await anchor_x.press("Enter")
            await page.wait_for_timeout(100)
            states["precision_after_coordinate"] = await page.evaluate("() => window.FigureStudio.app.getDirectSelectionStateForQa()")
            states["precision_context_after_coordinate"] = await page.evaluate("() => window.FigureStudio.app.getSelectionContextStateForQa()")
            states["precision_history_after_coordinate"] = await page.evaluate("() => window.FigureStudio.app.getHistoryStateForQa()")
            states["precision_paths_after_coordinate"] = await page.evaluate(
                """ids => ids.map((id) => ({ id, path: JSON.parse(JSON.stringify(window.FigureStudio.app.getObjectByIdForQa(id)?.path || [])) }))""",
                precision_ids,
            )
            await capture(page, screenshots, output_dir, "10c-anchor-coordinate-controls.png", "10c. Direct Selection exposes exact X and Y coordinates")
            await page.evaluate("async () => { await window.FigureStudio.app.undoForQa(); }")
            states["precision_after_coordinate_undo"] = await page.evaluate("() => window.FigureStudio.app.getDirectSelectionStateForQa()")
            states["precision_paths_after_coordinate_undo"] = await page.evaluate(
                """ids => ids.map((id) => ({ id, path: JSON.parse(JSON.stringify(window.FigureStudio.app.getObjectByIdForQa(id)?.path || [])) }))""",
                precision_ids,
            )
            await page.evaluate("async () => { await window.FigureStudio.app.redoForQa(); }")
            states["precision_after_coordinate_redo"] = await page.evaluate("() => window.FigureStudio.app.getDirectSelectionStateForQa()")
            states["precision_paths_after_coordinate_redo"] = await page.evaluate(
                """ids => ids.map((id) => ({ id, path: JSON.parse(JSON.stringify(window.FigureStudio.app.getObjectByIdForQa(id)?.path || [])) }))""",
                precision_ids,
            )
            # Rebuild the small fixture for an actual pointer-selected alignment operation.
            states["precision_align_scenario"] = await page.evaluate(
                "() => window.FigureStudio.app.createDirectSelectionParityScenarioForQa({ history: true })"
            )
            precision_align_ids = states["precision_align_scenario"].get("objectIds", [])
            layout_handles = [
                page.locator(f'.path-node-handle[data-object-id="{precision_align_ids[0]}"]').nth(0),
                page.locator(f'.path-node-handle[data-object-id="{precision_align_ids[0]}"]').nth(1),
                page.locator(f'.path-node-handle[data-object-id="{precision_align_ids[1]}"]').nth(0),
            ]
            layout_boxes = [await handle.bounding_box() for handle in layout_handles]
            if any(box is None for box in layout_boxes):
                raise AssertionError("Expected layout anchors after rebuilding precision fixture.")
            first_layout_box = layout_boxes[0]
            await page.mouse.click(first_layout_box["x"] + first_layout_box["width"] / 2, first_layout_box["y"] + first_layout_box["height"] / 2)
            await page.keyboard.down("Shift")
            for box in layout_boxes[1:]:
                await page.mouse.click(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
            await page.keyboard.up("Shift")
            states["precision_history_before_align"] = await page.evaluate("() => window.FigureStudio.app.getHistoryStateForQa()")
            states["precision_layout_before_align"] = await page.evaluate(
                """ids => ids.map((id) => ({ id, path: JSON.parse(JSON.stringify(window.FigureStudio.app.getObjectByIdForQa(id)?.path || [])) }))""",
                precision_align_ids,
            )
            await page.locator('.selection-context-bar [data-context-action="align-anchor-y"]').click()
            states["precision_after_align_y"] = await page.evaluate("() => window.FigureStudio.app.getDirectSelectionStateForQa()")
            states["precision_layout_after_align"] = await page.evaluate(
                """ids => ids.map((id) => ({ id, path: JSON.parse(JSON.stringify(window.FigureStudio.app.getObjectByIdForQa(id)?.path || [])) }))""",
                precision_align_ids,
            )
            states["precision_history_after_align"] = await page.evaluate("() => window.FigureStudio.app.getHistoryStateForQa()")
            await page.evaluate("async () => { await window.FigureStudio.app.undoForQa(); }")
            states["precision_layout_after_align_undo"] = await page.evaluate(
                """ids => ids.map((id) => ({ id, path: JSON.parse(JSON.stringify(window.FigureStudio.app.getObjectByIdForQa(id)?.path || [])) }))""",
                precision_align_ids,
            )
            await page.evaluate("async () => { await window.FigureStudio.app.redoForQa(); }")
            states["precision_layout_after_align_redo"] = await page.evaluate(
                """ids => ids.map((id) => ({ id, path: JSON.parse(JSON.stringify(window.FigureStudio.app.getObjectByIdForQa(id)?.path || [])) }))""",
                precision_align_ids,
            )

            # History restoration deliberately returns to ordinary selection.  Re-enter the
            # same user-facing Direct Selection flow before testing distribution rather than
            # relying on a no-history helper or a stale overlay.
            states["precision_distribute_scenario"] = await page.evaluate(
                "() => window.FigureStudio.app.createDirectSelectionParityScenarioForQa({ history: true })"
            )
            precision_layout_ids = states["precision_distribute_scenario"].get("objectIds", [])
            distribute_handles = [
                page.locator(f'.path-node-handle[data-object-id="{precision_layout_ids[0]}"]').nth(0),
                page.locator(f'.path-node-handle[data-object-id="{precision_layout_ids[0]}"]').nth(1),
                page.locator(f'.path-node-handle[data-object-id="{precision_layout_ids[1]}"]').nth(0),
            ]
            distribute_boxes = [await handle.bounding_box() for handle in distribute_handles]
            if any(box is None for box in distribute_boxes):
                raise AssertionError("Expected distribution anchors after rebuilding precision fixture.")
            await page.mouse.click(distribute_boxes[0]["x"] + distribute_boxes[0]["width"] / 2, distribute_boxes[0]["y"] + distribute_boxes[0]["height"] / 2)
            await page.keyboard.down("Shift")
            for box in distribute_boxes[1:]:
                await page.mouse.click(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
            await page.keyboard.up("Shift")
            states["precision_history_before_distribute"] = await page.evaluate("() => window.FigureStudio.app.getHistoryStateForQa()")
            states["precision_layout_before_distribute"] = await page.evaluate(
                """ids => ids.map((id) => ({ id, path: JSON.parse(JSON.stringify(window.FigureStudio.app.getObjectByIdForQa(id)?.path || [])) }))""",
                precision_layout_ids,
            )
            await page.locator('.selection-context-bar [data-context-action="distribute-anchor-x"]').click()
            states["precision_after_distribute_x"] = await page.evaluate("() => window.FigureStudio.app.getDirectSelectionStateForQa()")
            states["precision_layout_after_distribute"] = await page.evaluate(
                """ids => ids.map((id) => ({ id, path: JSON.parse(JSON.stringify(window.FigureStudio.app.getObjectByIdForQa(id)?.path || [])) }))""",
                precision_layout_ids,
            )
            await capture(page, screenshots, output_dir, "10d-anchor-align-distribute.png", "10d. Selected anchors align and distribute without object bounds")
            await page.evaluate("async () => { await window.FigureStudio.app.undoForQa(); }")
            states["precision_layout_after_distribute_undo"] = await page.evaluate(
                """ids => ids.map((id) => ({ id, path: JSON.parse(JSON.stringify(window.FigureStudio.app.getObjectByIdForQa(id)?.path || [])) }))""",
                precision_layout_ids,
            )
            await page.evaluate("async () => { await window.FigureStudio.app.redoForQa(); }")
            states["precision_layout_after_distribute_redo"] = await page.evaluate(
                """ids => ids.map((id) => ({ id, path: JSON.parse(JSON.stringify(window.FigureStudio.app.getObjectByIdForQa(id)?.path || [])) }))""",
                precision_layout_ids,
            )
            states["precision_history_after_distribute"] = await page.evaluate("() => window.FigureStudio.app.getHistoryStateForQa()")

            precision_project = await page.evaluate("() => window.FigureStudio.app.buildProjectJsonForQa()")
            states["precision_svg"] = await page.evaluate("() => window.FigureStudio.app.buildSvgExportForQa()")
            states["precision_project_before_reload"] = await page.evaluate(
                """ids => ids.map((id) => ({ id, path: JSON.parse(JSON.stringify(window.FigureStudio.app.getObjectByIdForQa(id)?.path || [])) }))""",
                precision_layout_ids,
            )
            await page.evaluate("payload => window.FigureStudio.app.loadProjectPayloadForQa(payload, { toast: false })", precision_project)
            await page.wait_for_timeout(150)
            states["precision_project_after_reload"] = await page.evaluate(
                """ids => ids.map((id) => ({ id, path: JSON.parse(JSON.stringify(window.FigureStudio.app.getObjectByIdForQa(id)?.path || [])) }))""",
                precision_layout_ids,
            )
            if not url:
                states["precision_package"] = await page.evaluate("async () => window.FigureStudio.app.buildDeckPackageExportForQa({ yieldDelayMs: 0 })")
                states["precision_package_state"] = await page.evaluate("async () => window.FigureStudio.app.importLastDeckPackageExportForQa()")
                states["precision_project_after_package"] = await page.evaluate(
                    """ids => ids.map((id) => ({ id, path: JSON.parse(JSON.stringify(window.FigureStudio.app.getObjectByIdForQa(id)?.path || [])) }))""",
                    precision_layout_ids,
                )
                states["precision_pdf"] = await page.evaluate("async () => window.FigureStudio.app.buildDeckPdfExportForQa({ download: false, yieldDelayMs: 0 })")

            states["multi_scenario_after_history"] = await page.evaluate("() => window.FigureStudio.app.createDirectSelectionParityScenarioForQa()")
            await page.wait_for_timeout(120)
            before_segment = await page.evaluate("() => window.FigureStudio.app.getDirectSelectionStateForQa()")
            segment = await page.locator(".path-segment-hit").nth(0).bounding_box()
            if not segment:
                raise AssertionError("Expected path segment hit target.")
            await page.mouse.move(segment["x"] + segment["width"] / 2, segment["y"] + segment["height"] / 2)
            await page.mouse.down()
            await page.mouse.move(segment["x"] + segment["width"] / 2 + 8, segment["y"] + segment["height"] / 2 + 62, steps=10)
            await page.mouse.up()
            await page.wait_for_timeout(120)
            states["after_segment_drag"] = await page.evaluate("() => window.FigureStudio.app.getDirectSelectionStateForQa()")
            states["before_segment_drag"] = before_segment
            await capture(page, screenshots, output_dir, "11-segment-drag-reshape.png", "11. Dragging a path segment reshapes the curve")

            states["shape_scenario"] = await page.evaluate("() => window.FigureStudio.app.createDirectSelectionShapeScenarioForQa()")
            await page.wait_for_timeout(120)
            states["shape_direct_before"] = await page.evaluate("() => window.FigureStudio.app.getDirectSelectionStateForQa()")
            await capture(page, screenshots, output_dir, "12-shape-direct-selection.png", "12. Direct Selection exposes rectangle and ellipse anchors")
            shape_handles = page.locator(".path-node-handle")
            shape_first = await shape_handles.nth(0).bounding_box()
            if not shape_first:
                raise AssertionError("Expected shape direct-selection handles.")
            await page.mouse.move(shape_first["x"] + shape_first["width"] / 2, shape_first["y"] + shape_first["height"] / 2)
            await page.mouse.down()
            await page.mouse.move(shape_first["x"] + shape_first["width"] / 2 + 46, shape_first["y"] + shape_first["height"] / 2 + 30, steps=8)
            await page.mouse.up()
            await page.wait_for_timeout(120)
            states["shape_direct_after"] = await page.evaluate("() => window.FigureStudio.app.getDirectSelectionStateForQa()")
            await capture(page, screenshots, output_dir, "13-shape-anchor-isolated-drag.png", "13. Shape anchor drag moves only selected anchor")
            await browser.close()
    finally:
        if server and server.poll() is None:
            server.terminate()
            try:
                server.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait(timeout=5)
        server_port_closed = await wait_for_port_closed(port) if server else True

    rect_bounds = states.get("rect", {}).get("selectedBounds") or {}
    arrow_bounds = states.get("arrow", {}).get("selectedBounds") or {}
    curve_bounds = states.get("curve", {}).get("selectedBounds") or {}
    before_bounds = states.get("before_drag", {}).get("selectedBounds") or {}
    drag_bounds = states.get("after_anchor_drag", {}).get("selectedBounds") or {}
    nudge_bounds = states.get("after_nudge", {}).get("selectedBounds") or {}
    align_bounds = states.get("after_align", {}).get("selectedBounds") or {}
    multi_marquee_handles = states.get("multi_marquee", {}).get("selectedHandles") or []
    multi_marquee_object_ids = {handle.get("objectId") for handle in multi_marquee_handles if handle.get("objectId")}
    multi_before = states.get("multi_points_before", {})
    multi_after = states.get("multi_points_after", {})
    handle_key = lambda handle: (handle.get("objectId"), handle.get("commandIndex"), handle.get("handleType"))
    multi_before_handles = {handle_key(handle): handle for handle in multi_before.get("handles", [])}
    multi_after_handles = {handle_key(handle): handle for handle in multi_after.get("handles", [])}
    multi_selected_keys = {handle_key(handle) for handle in multi_before.get("selectedHandles", [])}
    selected_point_deltas = [
        (
            float(multi_after_handles[key].get("x", 0)) - float(multi_before_handles[key].get("x", 0)),
            float(multi_after_handles[key].get("y", 0)) - float(multi_before_handles[key].get("y", 0)),
        )
        for key in multi_selected_keys
        if key in multi_before_handles and key in multi_after_handles
    ]
    unselected_point_deltas = [
        abs(float(multi_after_handles[key].get("x", 0)) - float(before.get("x", 0)))
        + abs(float(multi_after_handles[key].get("y", 0)) - float(before.get("y", 0)))
        for key, before in multi_before_handles.items()
        if key not in multi_selected_keys and key in multi_after_handles
    ]
    multi_selected_move_in_sync = (
        len({key[0] for key in multi_selected_keys if key[0]}) >= 2
        and len(selected_point_deltas) >= 2
        and all(abs(dx) + abs(dy) > 20 for dx, dy in selected_point_deltas)
        and max(dx for dx, _ in selected_point_deltas) - min(dx for dx, _ in selected_point_deltas) < 1.5
        and max(dy for _, dy in selected_point_deltas) - min(dy for _, dy in selected_point_deltas) < 1.5
    )
    multi_unselected_points_stay_fixed = bool(unselected_point_deltas) and max(unselected_point_deltas) < 1.5

    def selected_handle_points(state: object) -> dict[tuple[object, object, object], tuple[float, float]]:
        source = state if isinstance(state, dict) else {}
        values: dict[tuple[object, object, object], tuple[float, float]] = {}
        for handle in source.get("selectedHandles", []) if isinstance(source.get("selectedHandles", []), list) else []:
            key = handle_key(handle)
            values[key] = (float(handle.get("x", 0)), float(handle.get("y", 0)))
        return values

    precision_before_keyboard = selected_handle_points(states.get("precision_before_keyboard", {}))
    precision_after_fine = selected_handle_points(states.get("precision_after_fine_nudge", {}))
    precision_after_coarse = selected_handle_points(states.get("precision_after_coarse_nudge", {}))
    precision_fine_deltas = [
        (precision_after_fine[key][0] - before[0], precision_after_fine[key][1] - before[1])
        for key, before in precision_before_keyboard.items() if key in precision_after_fine
    ]
    precision_coarse_deltas = [
        (precision_after_coarse[key][0] - before[0], precision_after_coarse[key][1] - before[1])
        for key, before in precision_after_fine.items() if key in precision_after_coarse
    ]
    precision_fine_nudge_ok = (
        len(precision_fine_deltas) >= 3
        and all(abs(dx - 1) < 1.25 and abs(dy) < 1.25 for dx, dy in precision_fine_deltas)
    )
    precision_coarse_nudge_ok = (
        len(precision_coarse_deltas) >= 3
        and all(abs(dx) < 1.25 and abs(dy - 10) < 1.25 for dx, dy in precision_coarse_deltas)
    )
    precision_coordinate_handles = selected_handle_points(states.get("precision_after_coordinate", {}))
    precision_coordinate_ok = len(precision_coordinate_handles) >= 3 and all(
        abs(point[0] - 3.25 * 96) < 0.15 for point in precision_coordinate_handles.values()
    )
    precision_coordinate_history_ok = (
        states.get("precision_paths_after_coordinate_undo") == states.get("precision_paths_before_coordinate")
        and states.get("precision_paths_after_coordinate_redo") == states.get("precision_paths_after_coordinate")
    )
    precision_align_handles = selected_handle_points(states.get("precision_after_align_y", {}))
    precision_align_ok = len(precision_align_handles) >= 3 and (
        max(point[1] for point in precision_align_handles.values()) - min(point[1] for point in precision_align_handles.values()) < 0.15
    )
    precision_distribute_handles = selected_handle_points(states.get("precision_after_distribute_x", {}))
    precision_distribute_x = sorted(point[0] for point in precision_distribute_handles.values())
    precision_distribute_ok = len(precision_distribute_x) >= 3 and max(
        abs((precision_distribute_x[index + 1] - precision_distribute_x[index]) - (precision_distribute_x[1] - precision_distribute_x[0]))
        for index in range(len(precision_distribute_x) - 1)
    ) < 0.15
    precision_project_round_trip_ok = states.get("precision_project_before_reload") == states.get("precision_project_after_reload")
    precision_layout_history_ok = (
        states.get("precision_layout_after_align_undo") == states.get("precision_layout_before_align")
        and states.get("precision_layout_after_align_redo") == states.get("precision_layout_after_align")
        and states.get("precision_layout_after_distribute_undo") == states.get("precision_layout_before_distribute")
        and states.get("precision_layout_after_distribute_redo") == states.get("precision_layout_after_distribute")
    )
    precision_package_round_trip_ok = (
        not url
        and states.get("precision_package", {}).get("status") == "completed"
        and states.get("precision_project_before_reload") == states.get("precision_project_after_package")
    )
    precision_export_ok = (
        "<svg" in str(states.get("precision_svg", ""))
        and "<path" in str(states.get("precision_svg", ""))
        and (bool(url) or (
            states.get("precision_pdf", {}).get("status") == "completed"
            and int(states.get("precision_pdf", {}).get("bytes", 0)) > 100
        ))
    )
    anchor_visual_states = states.get("anchor_visual_states", {})
    selected_anchor_style = anchor_visual_states.get("selected") or {}
    unselected_anchor_style = anchor_visual_states.get("unselected") or {}
    anchor_states_are_distinct = (
        bool(selected_anchor_style)
        and bool(unselected_anchor_style)
        and selected_anchor_style.get("background") != unselected_anchor_style.get("background")
        and selected_anchor_style.get("borderColor") != unselected_anchor_style.get("borderColor")
        and selected_anchor_style.get("boxShadow") not in ("", "none")
    )
    before_segment_handles = states.get("before_segment_drag", {}).get("handles") or []
    after_segment_handles = states.get("after_segment_drag", {}).get("handles") or []
    segment_moved = any(
        abs(float(after.get("x", 0)) - float(before.get("x", 0))) > 3
        or abs(float(after.get("y", 0)) - float(before.get("y", 0))) > 3
        for before, after in zip(before_segment_handles, after_segment_handles)
    )
    shape_before_handles = states.get("shape_direct_before", {}).get("handles") or []
    shape_after_handles = states.get("shape_direct_after", {}).get("handles") or []
    shape_handle_deltas = [
        abs(float(after.get("x", 0)) - float(before.get("x", 0)))
        + abs(float(after.get("y", 0)) - float(before.get("y", 0)))
        for before, after in zip(shape_before_handles, shape_after_handles)
        if before.get("objectId") == after.get("objectId") and before.get("commandIndex") == after.get("commandIndex") and before.get("handleType") == after.get("handleType")
    ]
    shape_anchor_moved = bool(shape_handle_deltas) and max(shape_handle_deltas) > 20
    shape_anchor_left_others_still = len(shape_handle_deltas) > 1 and min(shape_handle_deltas[1:] or [999]) < 1.5
    before_shift = states.get("line_before_shift", {}).get("sceneEndpoints") or {}
    after_shift = states.get("line_after_shift", {}).get("sceneEndpoints") or {}
    before_outside = states.get("line_before_outside", {}).get("sceneEndpoints") or {}
    after_outside = states.get("line_after_outside", {}).get("sceneEndpoints") or {}
    after_undo = states.get("line_after_undo", {}).get("sceneEndpoints") or {}
    after_redo = states.get("line_after_redo", {}).get("sceneEndpoints") or {}
    before_escape = states.get("line_before_escape", {}).get("sceneEndpoints") or {}
    after_escape = states.get("line_after_escape", {}).get("sceneEndpoints") or {}
    before_cancel = states.get("line_before_cancel", {}).get("sceneEndpoints") or {}
    after_cancel = states.get("line_after_cancel", {}).get("sceneEndpoints") or {}
    outside_moved = not endpoints_close(before_outside, after_outside)
    history_before_outside = states.get("history_before_outside", {})
    history_after_outside = states.get("history_after_outside", {})
    checks = {
        "drag_rectangle_uses_drag_width": rect_bounds.get("width", 0) > 160 and rect_bounds.get("height", 0) > 90,
        "drag_arrow_uses_drag_vector": arrow_bounds.get("width", 0) > 200 and arrow_bounds.get("height", 0) > 50,
        "drag_curve_uses_drag_bounds": curve_bounds.get("width", 0) > 200 and curve_bounds.get("height", 0) > 50,
        "direct_selection_shows_exactly_two_line_endpoints": states.get("direct_entered", {}).get("overlayHandleCount") == 2,
        "line_endpoint_selection_stays_single": states.get("multi_selected", {}).get("selectedHandleCount") == 1,
        "single_line_endpoint_drag_moves_bounds": abs((drag_bounds.get("left", 0) - before_bounds.get("left", 0))) > 8 or abs((drag_bounds.get("top", 0) - before_bounds.get("top", 0))) > 8,
        "keyboard_nudge_moves_handles": abs((nudge_bounds.get("top", 0) - drag_bounds.get("top", 0))) >= 0.5,
        "anchor_drag_restores_canvas_keyboard_focus": states.get("focus_after_anchor_drag") == "viewport",
        "line_endpoint_alignment_is_safe": states.get("after_align", {}).get("selectedHandleCount") == 1,
        "shift_constrains_line_endpoint_to_45_degrees": is_45_constrained(after_shift) and not endpoints_close(before_shift, after_shift),
        "outside_canvas_pointer_capture_completes_endpoint_drag": outside_moved,
        "endpoint_drag_adds_exactly_one_undo_step": int(history_after_outside.get("undoDepth", 0)) == int(history_before_outside.get("undoDepth", 0)) + 1,
        "endpoint_undo_redo_round_trip": endpoints_close(before_outside, after_undo) and endpoints_close(after_outside, after_redo),
        "escape_rolls_back_endpoint_drag_without_history": endpoints_close(before_escape, after_escape) and states.get("history_before_escape") == states.get("history_after_escape"),
        "pointercancel_rolls_back_endpoint_drag_without_history": endpoints_close(before_cancel, after_cancel) and states.get("history_before_cancel") == states.get("history_after_cancel"),
        "curve_pointercancel_restores_geometry": handle_positions_equal(
            states.get("curve_cancel_before", {}).get("handles", []),
            states.get("curve_cancel_after", {}).get("handles", []),
        ),
        "direct_marquee_selects_curve_handles": states.get("curve_marquee", {}).get("selectedHandleCount", 0) >= 3,
        "direct_selection_active_collection_is_inert": (
            states.get("multi_direct_before", {}).get("selectionSelectable") is False
            and states.get("multi_direct_before", {}).get("selectionEvented") is False
            and states.get("multi_direct_before", {}).get("selectionMovementLocked") is True
        ),
        "empty_collective_bounds_drag_does_not_move_paths": states.get("multi_paths_after_empty_drag") == states.get("multi_paths_before_empty_drag"),
        "anchor_overlay_stays_attached_after_collective_bounds_drag": (
            states.get("multi_after_empty_drag", {}).get("overlayGeometryMaxError") is not None
            and float(states.get("multi_after_empty_drag", {}).get("overlayGeometryMaxError")) < 1
        ),
        "point_marquee_is_rectangular_and_quiet": (
            states.get("empty_drag_marquee", {}).get("marqueeVisible") is True
            and states.get("empty_drag_marquee", {}).get("lassoVisible") is False
            and states.get("multi_marquee_visible", {}).get("direct", {}).get("marqueeVisible") is True
            and states.get("multi_marquee_visible", {}).get("direct", {}).get("lassoVisible") is False
            and states.get("multi_marquee_visible", {}).get("background") in ("rgba(0, 0, 0, 0)", "transparent")
        ),
        "point_marquee_clears_after_pointerup": (
            states.get("multi_after_empty_drag", {}).get("marqueeVisible") is False
            and states.get("multi_marquee", {}).get("marqueeVisible") is False
        ),
        "point_marquee_escape_and_pointercancel_clear_without_exiting": (
            states.get("marquee_after_escape", {}).get("marqueeVisible") is False
            and states.get("marquee_after_escape", {}).get("active") is True
            and states.get("marquee_after_pointercancel", {}).get("marqueeVisible") is False
            and states.get("marquee_after_pointercancel", {}).get("active") is True
        ),
        "rectangular_marquee_selects_multiple_objects": len(multi_marquee_object_ids) >= 2 and states.get("multi_marquee", {}).get("selectedHandleCount", 0) >= 4,
        "selected_points_across_objects_move_in_sync": multi_selected_move_in_sync,
        "unselected_points_across_objects_stay_fixed": multi_unselected_points_stay_fixed,
        "anchor_overlay_stays_attached_after_point_drag": (
            multi_after.get("overlayGeometryMaxError") is not None
            and float(multi_after.get("overlayGeometryMaxError")) < 1
        ),
        "selected_and_unselected_anchor_styles_are_distinct": anchor_states_are_distinct,
        "multi_object_direct_selection_hides_transform_box": multi_after.get("selectionHasControls") is False and multi_after.get("selectionHasBorders") is False,
        "multi_object_point_drag_adds_one_undo_step": int(states.get("history_after_multi_move", {}).get("undoDepth", 0)) == int(states.get("history_before_multi_move", {}).get("undoDepth", 0)) + 1,
        "multi_object_point_drag_undo_redo_round_trip": states.get("multi_paths_after_undo") == states.get("multi_paths_before") and states.get("multi_paths_after_redo") == states.get("multi_paths_after"),
        "multi_anchor_fine_keyboard_nudge_moves_in_sync": precision_fine_nudge_ok,
        "multi_anchor_coarse_keyboard_nudge_moves_in_sync": precision_coarse_nudge_ok,
        "anchor_coordinate_entry_sets_selected_handles_exactly": precision_coordinate_ok,
        "anchor_align_and_distribute_use_selected_points": precision_align_ok and precision_distribute_ok,
        "anchor_precision_actions_are_atomic": (
            int(states.get("precision_history_after_keyboard", {}).get("undoDepth", 0)) == int(states.get("precision_history_before_keyboard", {}).get("undoDepth", 0)) + 2
            and int(states.get("precision_history_after_coordinate", {}).get("undoDepth", 0)) == int(states.get("precision_history_before_coordinate", {}).get("undoDepth", 0)) + 1
            and int(states.get("precision_history_after_align", {}).get("undoDepth", 0)) == int(states.get("precision_history_before_align", {}).get("undoDepth", 0)) + 1
            and int(states.get("precision_history_after_distribute", {}).get("undoDepth", 0)) == int(states.get("precision_history_before_distribute", {}).get("undoDepth", 0)) + 1
        ),
        "anchor_precision_undo_redo_restores_coordinate_align_and_distribute_geometry": precision_coordinate_history_ok and precision_layout_history_ok,
        "anchor_precision_project_reload_preserves_geometry": precision_project_round_trip_ok,
        "anchor_precision_package_round_trip_preserves_geometry": precision_package_round_trip_ok if not url else True,
        "anchor_precision_svg_and_pdf_exports_are_valid": precision_export_ok,
        "segment_drag_reshapes_path": segment_moved,
        "shape_direct_selection_exposes_anchors": states.get("shape_direct_before", {}).get("objectCount", 0) >= 2 and states.get("shape_direct_before", {}).get("handleCount", 0) >= 8,
        "shape_anchor_drag_is_isolated": shape_anchor_moved and shape_anchor_left_others_still,
        "no_console_errors": not console_errors,
        "server_port_closed": server_port_closed,
    }
    failed = [name for name, passed in checks.items() if not passed]
    contact_sheet = write_contact_sheet(output_dir, screenshots)
    proof = {
        "schema_id": "figureStudio.directSelectionDrawBrowserProof.v1",
        "status": "passed" if not failed else "failed",
        "server_port": port,
        "url": target_url,
        "viewport": viewport or {"width": 1440, "height": 1000},
        "server_port_closed": server_port_closed,
        "checks": checks,
        "failed_checks": failed,
        "console_errors": console_errors,
        "states": states,
        "screenshots": screenshots,
        "contact_sheet": str(contact_sheet),
    }
    proof_path = output_dir / "direct-selection-draw-proof.json"
    manifest_path = output_dir / "manifest.json"
    proof["proof_json"] = str(proof_path)
    proof["manifest"] = str(manifest_path)
    proof_path.write_text(json.dumps(proof, indent=2), encoding="utf-8")
    manifest_path.write_text(json.dumps({"schema_id": "figureStudio.directSelectionDrawManifest.v1", **proof}, indent=2), encoding="utf-8")
    return proof


def main() -> int:
    args = parse_args()
    proof = asyncio.run(run_browser(args.root, args.output_dir, args.timeout_ms, args.url, parse_viewport(args.viewport)))
    print(json.dumps(proof, indent=2))
    return 0 if proof["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
