#!/usr/bin/env python3
"""Native browser regression for the four existing RNA artwork revisions.

Uses real Library insertion, semantic color controls, file download/Open and
native isolated-path editing. Generated evidence stays in this repo's QA root.
"""
from __future__ import annotations

import argparse
import asyncio
import base64
import contextlib
import functools
import http.server
import io
import json
import threading
import traceback
from pathlib import Path

from PIL import Image, ImageChops, ImageStat
from playwright.async_api import async_playwright
from figure_studio_entry_qa import enter_current_document_async, show_library_async

ROOT = Path(__file__).resolve().parents[1]
ASSETS = [
    ("core.rna.strand", "rna_strand.svg", "rna strand"),
    ("core.rna.strand_linear", "rna_strand_linear.svg", "rna strand"),
    ("core.mrna.transcript", "mrna_transcript.svg", "mrna transcript"),
    ("core.rna.sirna", "sirna_duplex.svg", "sirna duplex"),
]
PACK = ROOT / "assets/scientific-packs/core-biology"
HISTORICAL = PACK / "revisions/2026-10-11-nucleic-acid-redraw"
STYLES = ["soft-color", "cut-paper", "technical-ink"]
PALETTES = ["original", "pastel", "vivid", "monochrome"]
COLORS = ["#277da8", "#bc6c25", "#a770aa", "#425466"]
STATE = """ids => {
  const app=FigureStudio.app;
  const visit=o=>({id:o.figureId,type:o.type,path:o.path||null,pathOffset:o.pathOffset||null,
    fill:o.fill,stroke:o.stroke,strokeWidth:o.strokeWidth,bounds:o.getBoundingRect(),
    matrix:o.calcTransformMatrix(),regionPaints:o.importMeta?.scientificSvgSource?.regionPaints||{},
    children:(o.getObjects?.()||[]).map(visit)});
  return ids.map(id=>{const o=app.getObjectByIdForQa(id);return o?{
    id,assetId:o.scientificAssetMeta.assetId,meta:o.scientificAssetMeta,importMode:o.importMeta?.importMode,
    tree:visit(o)}:null;});
}"""


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *_args):
        pass

    def copyfile(self, source, outputfile):
        try:
            super().copyfile(source, outputfile)
        except (ConnectionAbortedError, ConnectionResetError, BrokenPipeError):
            pass  # Chromium may cancel catalog requests when a context closes.


def leaves(tree):
    return [item for child in tree["children"] for item in leaves(child)] if tree["children"] else [tree]


def rounded(value):
    if isinstance(value, float):
        return round(value, 6)
    if isinstance(value, list):
        return [rounded(item) for item in value]
    if isinstance(value, dict):
        return {key: rounded(item) for key, item in value.items()}
    return value


def authored_document(value):
    """Omit derived clocks/bounds/thumbs and global cache-count telemetry.

    artifact_store_count is artifactStore.size (app.js), shared by workspaces;
    it does not describe a document reference. References, content, identities
    and all other storage fields remain exact; thumbnail pixels are separate.
    """
    result = json.loads(json.dumps(value))
    project = result.get("project", {})
    project.pop("savedAt", None)
    manifest = project.get("manifest", {})
    manifest.pop("exportedAt", None)
    manifest.get("export", {}).pop("exportedAt", None)
    project.get('assetStorage', {}).pop('artifact_store_count', None)
    manifest.get('assetStorage', {}).pop('artifact_store_count', None)
    for record in manifest.get("objects", []):
        record.pop("bounds", None)
    for page in project.get("deck", {}).get("pages", []):
        page.pop("updatedAt", None)
        page.pop("thumbnail", None)
    return rounded(result)


def thumbnail_difference(before, after):
    results = []
    first = before.get("project", {}).get("deck", {}).get("pages", [])
    second = after.get("project", {}).get("deck", {}).get("pages", [])
    if len(first) != len(second):
        return [{"passed": False, "reason": "Page count differs"}]
    for a, b in zip(first, second):
        source, restored = a.get("thumbnail"), b.get("thumbnail")
        if source == restored:
            results.append({"passed": True, "exactBytes": True})
            continue
        images = [Image.open(io.BytesIO(base64.b64decode(value.split(",", 1)[1]))).convert("RGBA") for value in [source, restored]]
        if images[0].size != images[1].size:
            results.append({"passed": False, "reason": "Derived thumbnail size differs"})
            continue
        delta = ImageChops.difference(*images)
        mean = sum(ImageStat.Stat(delta).mean) / 4
        maximum = max(pair[1] for pair in delta.getextrema())
        results.append({"passed": mean <= .25 and maximum <= 20, "exactBytes": False,
                        "meanChannelDifference": mean, "maximumChannelDifference": maximum,
                        "size": list(images[0].size)})
    return results


def geometry(states):
    # Imported group children can receive fresh transient IDs during history
    # reconstruction. Compare their ordered hierarchy, scene geometry and paint;
    # the separate cold-file check compares the full authored payload.
    def strip(value):
        if isinstance(value, dict):
            return {key: strip(item) for key, item in value.items() if key != "id"}
        if isinstance(value, list):
            return [strip(item) for item in value]
        return value
    return rounded([{**state, "tree": strip(state["tree"])} for state in states])


def native_reconstruction_difference(before, after):
    """Keep IDs, metadata, paths and paint exact; bound derived scene rounding."""
    result = {"passed": True, "maximumDerivedSceneDifference": 0.0, "mismatches": []}
    def visit(a, b, path=""):
        if isinstance(a, (int, float)) and isinstance(b, (int, float)) and (".bounds." in path or ".matrix[" in path):
            delta = abs(a - b)
            result["maximumDerivedSceneDifference"] = max(result["maximumDerivedSceneDifference"], delta)
            if delta > .01:
                result["mismatches"].append(path)
        elif isinstance(a, dict) and isinstance(b, dict) and a.keys() == b.keys():
            for key in a:
                visit(a[key], b[key], path + "." + key)
        elif isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
            for at, (x, y) in enumerate(zip(a, b)):
                visit(x, y, path + f"[{at}]")
        elif a != b:
            result["mismatches"].append(path)
    visit(before, after)
    result["passed"] = not result["mismatches"]
    return result


async def run(args):
    out = args.output_dir.resolve()
    out.mkdir(parents=True, exist_ok=True)
    # Record intentions before any screenshots exist.
    intents = {f"{style}-{palette}-{theme}.png":
        f"Show all four RNA drawings inserted as editable vectors using {style} / {palette}, in {theme} appearance, without selection overlays."
        for style in STYLES for palette in PALETTES
        for theme in (["light", "dark"] if palette == "original" else ["light"])}
    intents["isolated-anchor-edit.png"] = "Show a native RNA backbone anchor selected and moved inside the intact scientific-asset group."
    (out / "capture-intents.json").write_text(json.dumps(intents, indent=2) + "\n", encoding="utf8")
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(QuietHandler, directory=str(ROOT)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{server.server_port}/web/"
    proof = {"status": "running", "source": "draft overrides" if args.draft_dir else "canonical", "checks": [], "screenshots": [], "errors": []}
    proof["comparisonPolicy"] = {
        "history": "Undo may regenerate transient imported-child IDs; geometry, paint, semantic bindings and ordered hierarchy are compared, while parent and other asset IDs must remain stable. Native backbone selection is re-established within the same owning asset after Undo and Redo.",
        "coldOpen": "Every authored field and ID is compared at six-decimal numeric precision. Derived clocks, manifest scene bounds and PNG thumbnails are excluded from that comparison; thumbnails receive a separate pixel comparison.",
        "historicalScene": "Embedded native paths, paints, region bindings, hierarchy, metadata and IDs must remain exact. Fabric-derived scene matrices and bounds may differ by at most 0.01 pixels after four-decimal transform serialization."
    }
    def check(name, condition, detail=None):
        proof["checks"].append({"name": name, "passed": bool(condition), "detail": detail})
        if not condition:
            raise AssertionError(name)
    def write(name, value):
        (out / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf8")
    write("native-browser-proof.json", proof)
    page = context = browser = None
    try:
      async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        async def launch(*, override=None, catalog=None):
            context = await browser.new_context(viewport={"width": 1440, "height": 960}, accept_downloads=True)
            page = await context.new_page()
            page.set_default_timeout(30000)
            page.on("pageerror", lambda error: proof["errors"].append(str(error)))
            if override:
                async def serve_svg(route):
                    filename = route.request.url.split("?")[0].rsplit("/", 1)[-1]
                    await route.fulfill(status=200, content_type="image/svg+xml", body=(override / filename).read_text(encoding="utf8"))
                for _, filename, _ in ASSETS:
                    await page.route("**/core-biology/svg/" + filename, serve_svg)
            if catalog:
                async def serve_catalog(route):
                    await route.fulfill(status=200, content_type="application/json", body=catalog.read_text(encoding="utf8"))
                await page.route("**/core-biology/asset-pack.json", serve_catalog)
            await page.goto(url, wait_until="domcontentloaded")
            handle = await page.wait_for_selector("#figure-editor-frame")
            frame = await handle.content_frame()
            await frame.wait_for_function("window.FigureStudio?.app?.isReady===true")
            await page.wait_for_function("document.body.dataset.browserChrome==='integrated'")
            return context, page, frame, handle

        context, page, frame, handle = await launch(override=args.draft_dir)
        async def insert_four(style="soft-color", palette="original"):
            await show_library_async(frame, tab="tools")
            await frame.locator("#figureLibraryTab-assets").click()
            await frame.locator("#assetArtStyleSelect").select_option(style)
            await frame.locator("#assetPaletteSelect").select_option(palette)
            ids = []
            for at, (asset_id, _, query) in enumerate(ASSETS):
                await frame.evaluate('q=>FigureStudio.app.searchScientificAssetsForQa(q,"nucleic-acid")', query)
                variant = frame.locator(f'#assetGrid [data-asset-variant-id="{asset_id}"]')
                if await variant.count():
                    await variant.click()
                button = frame.locator(f'#assetGrid [data-asset-id="{asset_id}"]')
                await button.wait_for(state="visible")
                await button.click()
                await frame.wait_for_function('id=>FigureStudio.app.getObjectByIdForQa(FigureStudio.app.getSelectionStateForQa().activeObjectId)?.scientificAssetMeta?.assetId===id', arg=asset_id)
                object_id = await frame.evaluate("FigureStudio.app.getSelectionStateForQa().activeObjectId")
                ids.append(object_id)
                # Presentation fixture placement; insertion itself is through the real Library.
                await frame.evaluate("""({id,x})=>{const o=FigureStudio.app.getObjectByIdForQa(id);
                  o.scaleToWidth(126);o.set({originX:'center',originY:'center',left:x,top:230});o.setCoords();o.canvas.requestRenderAll();}
                """, {"id": object_id, "x": 90 + at * 164})
            states = await frame.evaluate(STATE, ids)
            write(f"native-{style}-{palette}.json", states)
            check(f"{style}/{palette} inserts four native vectors", len(states) == 4 and all(
                s and s["importMode"] != "raster_fallback" and all(p["type"].lower() != "image" for p in leaves(s["tree"])) for s in states))
            for state in states:
                region_ids = [r["id"] for r in state["meta"]["editableColorRegions"]]
                native_leaves = leaves(state["tree"])
                check(f"{state['assetId']} retains all semantic bindings in {style}/{palette}",
                      len(region_ids) == 4 and all(any(r in p["regionPaints"] for p in native_leaves) for r in region_ids))
                overrides = state["meta"].get("paletteColorOverrides", {})
                if palette != "original":
                    # The palette retains structural colors and records only
                    # changed parts. Still verify paint on every declared part.
                    defaults = {r["id"]: r["default"] for r in state["meta"]["editableColorRegions"]}
                    check(f"{state['assetId']} renders every semantic region with {palette}",
                          set(overrides).issubset(region_ids) and all(
                              str(p[channel]).lower() == str(overrides.get(r, defaults[r])).lower()
                              for r in region_ids for p in native_leaves if r in p["regionPaints"]
                              for channel in p["regionPaints"][r]),
                          {"expectedPaints": {r: overrides.get(r, defaults[r]) for r in region_ids}})
            return ids, states

        async def clean_capture(filename):
            await frame.evaluate("FigureStudio.app.clearSelectionForQa()")
            for selector in ["#figureLibraryToggle", "#figureStyleToggle"]:
                if await frame.locator(selector).get_attribute("aria-pressed") == "true":
                    await frame.locator(selector).click()
            await frame.locator('#figure-simple-toolbar [data-figure-layout-command="fit-screen"]').click()
            await frame.locator("#toast.show").wait_for(state="hidden", timeout=8000)
            await page.wait_for_timeout(120)
            await page.screenshot(path=str(out / filename), animations="disabled")
            proof["screenshots"].append({"file": filename, "intent": intents[filename]})

        async def theme(name):
            button = frame.locator("#browser-theme-" + name)
            if not await button.is_visible():
                await frame.locator("#browser-files-trigger").click()
            await button.click()
            await page.keyboard.press("Escape")

        await enter_current_document_async(frame, kind="figure", preset="double-column", name="RNA artwork regression")
        ids, original = await insert_four()
        write("native-library-insertions.json", original)
        await frame.locator('[data-figure-layout-choice="advanced"]').click()
        if await frame.locator("#figureStyleToggle").get_attribute("aria-pressed") != "true":
            await frame.locator("#figureStyleToggle").click()
        await frame.locator('[data-inspector-tab="properties"]').click()
        recolored = []
        for object_id in ids:
            await frame.evaluate("id=>FigureStudio.app.selectObjectsByIdsForQa([id])", object_id)
            state = (await frame.evaluate(STATE, [object_id]))[0]
            regions = state["meta"]["editableColorRegions"]
            colors = {r["id"]: COLORS[at] for at, r in enumerate(regions)}
            check("RNA semantic regions remain available", len(colors) == 4, {"assetId": state["assetId"], "regions": list(colors)})
            for region, color in colors.items():
                control = frame.locator(f'#scientificAssetColorList [data-asset-color-region="{region}"]')
                await control.wait_for(state="visible")
                await control.evaluate(
                    "(input,color)=>{input.value=color;input.dispatchEvent(new Event('change',{bubbles:true}));}", color)
                await frame.wait_for_function("([id,r,c])=>FigureStudio.app.getObjectByIdForQa(id)?.scientificAssetMeta?.colorOverrides?.[r]?.toLowerCase()===c", arg=[object_id, region, color])
            state = (await frame.evaluate(STATE, [object_id]))[0]
            for region, color in colors.items():
                matched = [p for p in leaves(state["tree"]) if region in p["regionPaints"]]
                check(f"{state['assetId']} recolors {region}", bool(matched) and all(
                    str(p[channel]).lower() == color for p in matched for channel in p["regionPaints"][region]))
            recolored.append(state)
        await frame.evaluate("id=>FigureStudio.app.selectObjectsByIdsForQa([id])", ids[0])
        for variant in ["core.rna.strand_linear", "core.rna.strand"]:
            await frame.locator(f'[data-scientific-asset-style-id="{variant}"]').click()
            await frame.wait_for_function("([id,a])=>FigureStudio.app.getObjectByIdForQa(id)?.scientificAssetMeta?.assetId===a", arg=[ids[0], variant])
            switched = (await frame.evaluate(STATE, [ids[0]]))[0]
            check("RNA form change preserves all semantic colors", switched["meta"]["colorOverrides"] == recolored[0]["meta"]["colorOverrides"])
            check("RNA form change preserves scene bounds", all(abs(switched["tree"]["bounds"][key] - recolored[0]["tree"]["bounds"][key]) < 1 for key in ["left", "top", "width", "height"]))
        await frame.locator('[data-figure-layout-choice="advanced"]').click()
        await frame.locator('[data-tool="directSelect"]').click()
        await frame.evaluate("id=>FigureStudio.app.enterGroupIsolationForQa({groupId:id})", ids[0])
        child_id = await frame.evaluate("""id=>{const root=FigureStudio.app.getObjectByIdForQa(id);
          const visit=o=>[o,...(o.getObjects?.()||[]).flatMap(visit)];return visit(root).find(o=>o.path&&o.importMeta?.scientificSvgSource?.regionPaints?.backbone)?.figureId;}""", ids[0])
        check("RNA backbone is a native isolated path", bool(child_id))
        await frame.evaluate("id=>FigureStudio.app.selectGroupIsolationChildForQa({objectId:id})", child_id)
        await frame.evaluate("id=>FigureStudio.app.selectBezierNodeForQa(id,0)", child_id)
        before = await frame.evaluate(STATE, ids)
        history_before = await frame.evaluate("FigureStudio.app.getHistoryStateForQa()")
        await frame.locator(".path-node-handle.selected").first.focus()
        await page.keyboard.press("ArrowRight")
        after = await frame.evaluate(STATE, ids)
        history_after = await frame.evaluate("FigureStudio.app.getHistoryStateForQa()")
        check("Isolated anchor edit changes RNA path", rounded(after[0]["tree"]) != rounded(before[0]["tree"]))
        check("Isolated anchor edit is one undo step", history_after["undoDepth"] == history_before["undoDepth"] + 1)
        check("Isolated edit preserves other RNA objects", rounded(after[1:]) == rounded(before[1:]))
        await page.screenshot(path=str(out / "isolated-anchor-edit.png"), animations="disabled")
        proof["screenshots"].append({"file": "isolated-anchor-edit.png", "intent": intents["isolated-anchor-edit.png"]})
        await frame.evaluate("FigureStudio.app.undoForQa()")
        undone = await frame.evaluate(STATE, ids)
        write("isolation-history-debug.json", {"before": before, "after": after, "undo": undone})
        check("Undo restores RNA geometry and hierarchy", geometry(undone) == geometry(before))
        check("Undo preserves owning asset and all other object IDs", undone[0]["id"] == before[0]["id"] and rounded(undone[1:]) == rounded(before[1:]))
        proof["historyChildIdsRetained"] = [p["id"] for p in leaves(undone[0]["tree"])] == [p["id"] for p in leaves(before[0]["tree"])]
        async def reselect_backbone(label):
            owner = await frame.evaluate("""id=>{const root=FigureStudio.app.getObjectByIdForQa(id);const visit=o=>[o,...(o.getObjects?.()||[]).flatMap(visit)];return visit(root).find(o=>o.path&&o.importMeta?.scientificSvgSource?.regionPaints?.backbone)?.figureId;}""", ids[0])
            await frame.evaluate("id=>FigureStudio.app.enterGroupIsolationForQa({groupId:id})", ids[0])
            await frame.evaluate("id=>FigureStudio.app.selectGroupIsolationChildForQa({objectId:id})", owner)
            await frame.evaluate("id=>FigureStudio.app.selectBezierNodeForQa(id,0)", owner)
            selection = await frame.evaluate("({isolation:FigureStudio.app.getGroupIsolationStateForQa(),direct:FigureStudio.app.getDirectSelectionStateForQa()})")
            check(label + " reselects native backbone within the correct owner", selection["isolation"]["rootId"] == ids[0] and selection["isolation"]["selectedParentId"] == ids[0] and selection["direct"]["objectId"] == owner and selection["direct"]["selectedHandleCount"] == 1)
            return selection
        history_selections = {"undo": await reselect_backbone("Undo")}
        await frame.evaluate("FigureStudio.app.redoForQa()")
        check("Redo restores isolated RNA anchor edit", geometry(await frame.evaluate(STATE, ids)) == geometry(after))
        history_selections["redo"] = await reselect_backbone("Redo")
        await frame.evaluate("FigureStudio.app.undoForQa()")
        await frame.evaluate("FigureStudio.app.exitGroupIsolationForQa()")
        await frame.evaluate("FigureStudio.app.clearSelectionForQa()")
        write("native-recolor-isolation.json", {"recolored": recolored, "beforeEdit": before, "afterEdit": after, "historySelections": history_selections})
        print("Canonical RNA recolor, form and isolated history checks passed.", flush=True)

        async def save_download(filename):
            await frame.locator("#fileMenuTrigger").click()
            async def accept_filename(dialog):
                await dialog.accept(filename)
            page.once("dialog", accept_filename)
            async with page.expect_download() as pending:
                await frame.locator('[data-menu="file"] [data-command="save-project"]').click()
            download = await pending.value
            path = out / filename
            await download.save_as(path)
            return path

        async def cold_open(path):
            nonlocal context, page, frame, handle
            await context.close()
            context, page, frame, handle = await launch()
            await enter_current_document_async(frame, kind="figure", preset="double-column", name="Cold reopen")
            await frame.locator("#fileMenuTrigger").click()
            async with page.expect_file_chooser() as pending:
                await frame.locator('[data-menu="file"] [data-command="open-project"]').click()
            await (await pending.value).set_files(path)
            await frame.wait_for_function("document.querySelector('#documentFileOperationStatus')?.dataset.state==='success'")
            return await frame.evaluate("FigureStudio.app.serializeCurrentDocumentForQa({markSaved:false})")

        path = await save_download("rna-recolored.fsfigure")
        saved = await frame.evaluate("FigureStudio.app.serializeCurrentDocumentForQa({markSaved:false})")
        write("current-before-cold-reopen.json", saved)
        reopened = await cold_open(path)
        write("current-after-cold-reopen.json", reopened)
        proof["currentDerivedThumbnails"] = thumbnail_difference(saved, reopened)
        check("Current reconstructed thumbnails remain visually equivalent", all(item["passed"] for item in proof["currentDerivedThumbnails"]))
        check("Actual downloaded Figure cold-reopens its complete authored payload", authored_document(reopened) == authored_document(saved))
        print("Actual downloaded Figure cold-reopened its complete authored payload.", flush=True)

        # Actual SVG export download; no raster images may be embedded.
        await frame.locator("#fileMenuTrigger").click()
        await frame.locator('[data-menu="file"] [data-command="export-as"]').click()
        await frame.locator("[data-export-as-format]").select_option("svg")
        await frame.wait_for_function("FigureStudio.app.getExportAsStateForQa().reviewStatus==='ready' && FigureStudio.app.getExportAsStateForQa().reviewedRequest?.format==='svg'")
        async with page.expect_download() as pending:
            await frame.locator("[data-export-as-submit]").click()
        download = await pending.value
        await download.save_as(out / "rna-native-export.svg")
        export_text = (out / "rna-native-export.svg").read_text(encoding="utf8")
        check("SVG export contains paths without raster images", "<path" in export_text and "<image" not in export_text and "data:image" not in export_text)
        await frame.locator("[data-export-as-close]").click()

        # Old documents remain embedded historical vectors even with the new catalog.
        check("Pre-redraw RNA snapshot exists", all((HISTORICAL / "svg" / filename).is_file() for _, filename, _ in ASSETS))
        await context.close()
        context, page, frame, handle = await launch(override=HISTORICAL / "svg", catalog=HISTORICAL / "asset-pack.json")
        await enter_current_document_async(frame, kind="figure", preset="double-column", name="Historical RNA drawings")
        old_ids, old_states = await insert_four()
        old_path = await save_download("rna-historical.fsfigure")
        old_saved = await frame.evaluate("FigureStudio.app.serializeCurrentDocumentForQa({markSaved:false})")
        old_reopened = await cold_open(old_path)
        write("historical-cold-reopen.json", {"before": old_saved, "after": old_reopened})
        proof["historicalDerivedThumbnails"] = thumbnail_difference(old_saved, old_reopened)
        check("Historical reconstructed thumbnails remain visually equivalent", all(item["passed"] for item in proof["historicalDerivedThumbnails"]))
        check("Historical downloaded Figure cold-reopens unchanged", authored_document(old_saved) == authored_document(old_reopened))
        old_restored_states = await frame.evaluate(STATE, old_ids)
        write("historical-native-state.json", {"before": old_states, "after": old_restored_states})
        proof["historicalNativeReconstruction"] = native_reconstruction_difference(old_states, old_restored_states)
        check("Historical native primitives, IDs and metadata stay embedded", proof["historicalNativeReconstruction"]["passed"], proof["historicalNativeReconstruction"])
        write("historical-cold-reopen.json", {"before": old_saved, "after": old_reopened})
        print("Historical RNA download cold-reopened without replacing embedded artwork.", flush=True)

        # Real importer matrix across all 3 drawing treatments and 4 palettes.
        await context.close()
        context, page, frame, handle = await launch(override=args.draft_dir)
        matrix = []
        for style in STYLES:
            for palette in PALETTES:
                await enter_current_document_async(frame, kind="figure", preset="double-column", name=f"RNA · {style} · {palette}")
                await theme("light")
                _, states = await insert_four(style, palette)
                matrix.append({"style": style, "palette": palette, "assets": states})
                await clean_capture(f"{style}-{palette}-light.png")
                if palette == "original":
                    await theme("dark")
                    await clean_capture(f"{style}-{palette}-dark.png")
                print(f"Native treatment captured: {style}/{palette}", flush=True)
        write("native-treatment-matrix.json", matrix)
        check("All twelve drawing/palette treatments checked", len(matrix) == 12)
        check("Browser telemetry remains clean", not proof["errors"], proof["errors"])
        proof["status"] = "passed"
    except Exception as error:
        proof["status"] = "failed"
        proof["failure"] = str(error)
        proof["traceback"] = traceback.format_exc()
        if page and not page.is_closed():
            with contextlib.suppress(Exception):
                await page.screenshot(path=str(out / "failure.png"))
        raise
    finally:
        write("native-browser-proof.json", proof)
        if context:
            with contextlib.suppress(Exception):
                await context.close()
        if browser:
            with contextlib.suppress(Exception):
                await browser.close()
        server.shutdown()
        server.server_close()
    print(json.dumps({"status": proof["status"], "checks": len(proof["checks"]), "screenshots": len(proof["screenshots"]), "output": str(out)}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "qa_artifacts/asset-round2-20261011/native")
    parser.add_argument("--draft-dir", type=Path, help="Optional SVG-only route override while artwork is being prepared.")
    asyncio.run(run(parser.parse_args()))
