#!/usr/bin/env python3
"""Qualify current shared Figure PDF opening, editing, fidelity and persistence.

Default sources are reproducible producer fixtures, not user or published PDFs.
Use repeated --fixture PATH for unchanged real PDFs and --page for their page.
--baseline records every acceptance failure and exits zero only if the harness
completed. Ordinary runs fail when any acceptance check fails. PDFium is the
independent reference renderer; no retired converter or native-input QA is used.
"""
from __future__ import annotations

import argparse
import base64
from collections import Counter
import ctypes
from datetime import datetime, timezone
import hashlib
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
import json
import math
from pathlib import Path
import sys
import threading
import time
import traceback

import numpy as np
import pikepdf
from PIL import Image, ImageFilter
import pypdfium2 as pdfium
import pypdfium2.raw as pdfium_raw
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
FIGURE = ROOT
from figure_package_qa import FigureQaTarget, add_package_arguments
from figure_studio_entry_qa import enter_current_document_sync
TARGET = FigureQaTarget.from_arguments(ROOT)

FONT_CONTEXT_JS = """id => {
 const o=FigureStudio.app.getObjectByIdForQa(id),s=o?.pdfTextSource||{};
 return {source:{originalFontName:s.originalFontName,displayFontFamily:s.displayFontFamily,sourceEmbeddedProgram:s.sourceEmbeddedProgram,fontSubstitutionFamily:s.fontSubstitutionFamily},
 objectFamily:o?.fontFamily,substitutions:o?.getFontSubstitutions?.()||[],
 visibleNotes:Array.from(document.querySelectorAll('[data-pdf-font-substitution]')).filter(el=>el.getClientRects().length).map(el=>({kind:el.getAttribute('data-pdf-font-substitution'),text:el.textContent})),
 visibleFontChoices:Array.from(document.querySelectorAll('[data-context-property="fontFamily"]')).filter(el=>el.getClientRects().length).map(el=>({value:el.value,label:el.selectedOptions?.[0]?.textContent}))};
}"""

PHYSICAL_TEXT_SIZE_JS = """id => {
 const o=FigureStudio.app.getObjectByIdForQa(id),f=window.fabric;
 let m=o?.calcTransformMatrix?.()||[1,0,0,1,0,0],planeKind='ordinary';
 if(o?.pdfTextSource?.currentNativeGlyphPlanes||o?.pdfTextAuthoringPlane){
   let Text;try{Text=f?.classRegistry?.getClass('PdfPositionedText');}catch{}
   if(!Text||o.constructor!==Text||o._pdfCurrentNativePaintMatrix!==Text.prototype._pdfCurrentNativePaintMatrix
      ||o._pdfCurrentNativePlane!==Text.prototype._pdfCurrentNativePlane||o._renderChars!==Text.prototype._renderChars
      ||o.calcTransformMatrix!==f.IText.prototype.calcTransformMatrix||!o._pdfCurrentNativePlane())return null;
   m=o._pdfCurrentNativePaintMatrix();planeKind='current-native';
 }
 const axisScale=Math.hypot(m[2],m[3]),rawFontSize=Number(o?.fontSize)||0;
 const field=Array.from(document.querySelectorAll('[data-context-property="fontSize"],#fontSizeInput')).find(el=>el.getClientRects().length);
 return {id,rawFontSize,matrix:m,axisScale,planeKind,physicalPoints:rawFontSize*axisScale*72/96,
 visibleFieldPoints:field?Number(field.value):null,fieldDisabled:field?.disabled??true,
 text:o?.text||'',originalSourceFontSize:o?.pdfTextSource?.originalFontSize,
 sourceLayoutActive:Boolean(o?._sourceLayout?.())};
}"""

PATH_GEOMETRY_JS = """id => {
 const o=FigureStudio.app.getObjectByIdForQa(id),f=window.fabric;
 if(!o||!Array.isArray(o.path)||!f?.Path)return null;
 const native=new f.Path(o.path),clips=[],mul=f.util.multiplyTransformMatrices;
 function visit(clip,parentWorld,owner,relation){
   const world=relation==='clipPath'&&clip.absolutePositioned?clip.calcOwnMatrix():mul(parentWorld,clip.calcOwnMatrix());
   clips.push({owner,relation,type:clip.type,absolutePositioned:Boolean(clip.absolutePositioned),inverted:Boolean(clip.inverted),world});
   for(const child of clip.getObjects?.()||[])visit(child,world,owner,'compoundMember');
   if(clip.clipPath)visit(clip.clipPath,world,owner,'clipPath');
 }
 for(let ancestor=o;ancestor;ancestor=ancestor.group)if(ancestor.clipPath)visit(ancestor.clipPath,ancestor.calcTransformMatrix(),ancestor.figureId,'clipPath');
 return {id,width:o.width,height:o.height,pathOffset:o.pathOffset,nativeWidth:native.width,nativeHeight:native.height,nativePathOffset:native.pathOffset,world:o.calcTransformMatrix(),clips};
}"""

BROWSER_SAVE_STATE_JS = """() => {
 const status=document.querySelector('#figure-editor-frame')?.contentDocument?.querySelector('#browser-save-status')
   ||document.querySelector('#browser-save-status');
 return {state:status?.dataset.state||'',text:status?.innerText||'',
 errors:window.__figurePdfQaBrowserSave?.errors||[],calls:window.__figurePdfQaBrowserSave?.calls||[]};
}"""

INSTALL_BROWSER_SAVE_PROBE_JS = """() => {
 const state=window.__figurePdfQaBrowserSave={errors:[],calls:[]};
 const app=document.querySelector('#figure-editor-frame')?.contentWindow?.FigureStudio?.app;
 function wrap(owner,key,origin){
   if(typeof owner?.[key]!=='function')return false;
   const original=owner[key];
   owner[key]=function(...args){
     const call={origin,startMs:performance.now(),failed:false};state.calls.push(call);if(state.calls.length>128)state.calls.shift();
     const failed=error=>{call.failed=true;call.durationMs=performance.now()-call.startMs;state.errors.push({origin,name:String(error?.name||'Error'),message:String(error?.message||error),stack:String(error?.stack||''),atMs:performance.now()});throw error;};
     const success=value=>{call.durationMs=performance.now()-call.startMs;
       if(origin==='app.captureBrowserSessionAsync')call.serializationMetrics=app.getBrowserSerializationMetricsForQa?.();
       return value;};
     try{const result=original.apply(this,args);return result&&typeof result.then==='function'?result.then(success,failed):success(result);}catch(error){return failed(error);}
   };
   return true;
 }
 return {captureWrapped:wrap(app,'captureBrowserSession','app.captureBrowserSession'),asyncCaptureWrapped:wrap(app,'captureBrowserSessionAsync','app.captureBrowserSessionAsync'),storeWrapped:wrap(window.FigureBrowserStore,'save','FigureBrowserStore.save')};
}"""

INSTALL_HISTORY_SLICE_PROBE_JS = """() => {
 const Store=globalThis.FigureStudioPdfHistoryNodeStore?.Store;
 const rows=globalThis.__figurePdfQaHistorySlices=[];
 if(!Store)return false;
 for(const name of ['freezeDetachedJsonAsync','compactImmutableAsync']){
   const original=Store.prototype[name];
   Store.prototype[name]=async function(value,options={}){
     const row={name,startMs:performance.now(),yieldCount:0,maxSynchronousSliceMs:0};
     let sliceStarted=row.startMs;
     const next={...options};
     // Observe the existing scheduler rather than replacing its semantics.
     if(typeof options.yieldToUi==='function')next.yieldToUi=async()=>{
       row.maxSynchronousSliceMs=Math.max(row.maxSynchronousSliceMs,performance.now()-sliceStarted);
       row.yieldCount++;
       try{return await options.yieldToUi();}finally{sliceStarted=performance.now();}
     };
     try{return await original.call(this,value,next);}
     finally{
       row.maxSynchronousSliceMs=Math.max(row.maxSynchronousSliceMs,performance.now()-sliceStarted);
       row.durationMs=performance.now()-row.startMs;rows.push(row);
     }
   };
 }
 return true;
}"""

PDF_TEXT_SOURCE_GLYPHS_JS = """() => {
 const a=FigureStudio.app,f=window.fabric,result={};
 const Text=f.classRegistry.getClass('PdfPositionedText');
 function visit(o){
   if(o.pdfTextSource?.glyphs?.length&&o._sourceLayout?.()){
     const current=o.pdfTextSource.currentNativeGlyphPlanes||o.pdfTextAuthoringPlane||o._toSVG===Text.prototype._pdfCurrentPlaneSvgMarkup;
     if(current){
       const exact=o.constructor===Text
         &&o._renderTextFill===Text.prototype._renderTextFill&&o._renderChars===Text.prototype._renderChars
         &&o._renderCursor===Text.prototype._renderCursor&&o._getCursorBoundaries===Text.prototype._getCursorBoundaries
         &&o._pdfCurrentNativePlane===Text.prototype._pdfCurrentNativePlane&&o._sourceLayout===Text.prototype._sourceLayout
         &&o._toSVG===Text.prototype._pdfCurrentPlaneSvgMarkup
         &&o.calcOwnMatrix===Text.prototype.calcOwnMatrix&&o.calcTransformMatrix===Text.prototype.calcTransformMatrix;
       const plane=exact?o._pdfCurrentNativePlane():null;
       if(plane?.kind==='source'){
         const owner=o.calcTransformMatrix(),glyphs=[];
         for(let i=0;i<plane.entries.length;i++){
           const entry=plane.entries[i],glyph=o.pdfTextSource.glyphs[i];
           let matrix=owner;
           for(const local of entry.matrices)matrix=f.util.multiplyTransformMatrices(matrix,local);
           const point=f.util.transformPoint(new f.Point(entry.x,entry.y),matrix);
           for(const unicode of glyph.unicode)glyphs.push({unicode,x:point.x,y:point.y});
         }
         result[o.figureId]=glyphs;
       }
     }else{
       const anchor=o._pdfAnchorPoint(),matrix=o.calcTransformMatrix(),glyphs=[];
       for(const glyph of o.pdfTextSource.glyphs){
         const point=f.util.transformPoint(new f.Point(anchor.x+glyph.x,anchor.y+glyph.y),matrix);
         for(const unicode of glyph.unicode)glyphs.push({unicode,x:point.x,y:point.y});
       }
       result[o.figureId]=glyphs;
     }
   }
   for(const child of o.getObjects?.()||[])visit(child);
 }
 for(const row of a.getCanvasObjectInventoryForQa().objects){const o=a.getObjectByIdForQa(row.id);if(o)visit(o);}
 return result;
}"""


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def source_binding():
    if TARGET.package_root:
        rows = TARGET.inventory_identity()
    else:
        rows = {path.relative_to(FIGURE).as_posix(): sha(path.read_bytes())
                for directory in ("app", "vendor", "assets/scientific-packs", "assets/scientific-scenes", "web")
                for path in (FIGURE / directory).rglob("*") if path.is_file()}
    rows["@runner"] = sha(Path(__file__).read_bytes())
    for name in ('figure_package_qa.py', 'figure_tool_package_producer.py', 'figure_studio_entry_qa.py'):
        rows['@helper/' + name] = sha((ROOT / 'scripts' / name).read_bytes())
    return rows


def generate_reportlab(path, kind):
    """Exact producer coverage: recoverable text, paths, forms, clips and image."""
    from reportlab.pdfgen.canvas import Canvas
    from reportlab.lib.utils import ImageReader
    document = Canvas(str(path), pagesize=(480, 320), invariant=1, pageCompression=0)
    if kind == "dense":
        for index in range(900):
            red = .15 + (index % 6) * .10
            document.setFillColorRGB(red, .42, .68)
            document.rect(48 + index % 45 * 8, 48 + index // 45 * 10, 6, 8, fill=1, stroke=0)
        document.setFillColorRGB(.1, .12, .15)
        document.setFont("Helvetica", 12)
        document.drawString(48, 292, "Simulated expression matrix")
        document.drawString(185, 24, "Sample")
        document.saveState()
        document.translate(20, 110)
        document.rotate(90)
        document.drawString(0, 0, "Gene")
        document.restoreState()
    elif kind == "forms":
        document.beginForm("plot", 0, 0, 160, 190)
        document.setStrokeColorRGB(.16, .18, .22)
        document.setLineWidth(.75)
        document.line(0, 0, 145, 0)
        document.line(0, 0, 0, 160)
        document.saveState()
        clip = document.beginPath()
        clip.rect(0, 0, 145, 160)
        document.clipPath(clip, fill=0, stroke=0)
        document.setFillColorRGB(.13, .43, .60)
        for index in range(11):
            document.circle(-8 + index * 16, 8 + index * 14, 5, fill=1, stroke=0)
        document.restoreState()
        document.setFillColorRGB(.1, .12, .15)
        document.setFont("Helvetica", 11)
        document.drawString(18, 174, "Condition A")
        document.endForm()
        document.beginForm("nested", 0, 0, 160, 190)
        document.doForm("plot")
        document.endForm()
        for x in (55, 265):
            document.saveState()
            document.translate(x, 72)
            document.doForm("nested")
            document.restoreState()
        document.setFillColorRGB(.1, .12, .15)
        document.setFont("Helvetica", 11)
        document.drawString(74, 42, "Time (min)")
        document.drawString(287, 42, "Time (min)")
        raster = Image.fromarray(np.tile(np.arange(0, 256, 4, dtype=np.uint8), (32, 1)), "L").convert("RGB")
        document.saveState()
        document.translate(215, 278)
        document.rotate(12)
        document.drawImage(ImageReader(raster), 0, 0, width=96, height=32)
        document.restoreState()
    else:
        document.setStrokeColorRGB(.1, .12, .15)
        document.setLineWidth(.8)
        document.line(55, 55, 420, 55)
        document.line(55, 55, 55, 275)
        for x, y, color in ((110, 110, (.14, .45, .60)), (205, 190, (.28, .62, .43)), (300, 145, (.78, .40, .22))):
            document.setFillColorRGB(*color)
            document.rect(x, 55, 55, y, fill=1, stroke=0)
            document.setStrokeColorRGB(.1, .12, .15)
            document.setLineWidth(1.2)
            document.line(x + 27, y + 35, x + 27, y + 75)
            document.line(x + 20, y + 75, x + 34, y + 75)
        document.setFillColorRGB(.1, .12, .15)
        document.setFont("Helvetica", 12)
        for x, label in ((108, "Control"), (203, "Treatment"), (300, "Recovery")):
            document.drawString(x, 34, label)
        document.saveState()
        document.translate(26, 102)
        document.rotate(90)
        document.drawString(0, 0, "Protein abundance (a.u.)")
        document.restoreState()
    document.save()


def generate_matplotlib(path, fonttype):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    with matplotlib.rc_context({"pdf.fonttype": fonttype, "font.family": "DejaVu Sans", "font.size": 9}):
        fig, axes = plt.subplots(1, 2, figsize=(6.5, 3.3), layout="constrained")
        rng = np.random.default_rng(1729)
        x = np.linspace(0, 60, 60)
        axes[0].plot(x, .8 * (1 - np.exp(-x / 14)), color="#276f96", lw=1.3, label="Treatment")
        axes[0].scatter(x[::4], .8 * (1 - np.exp(-x[::4] / 14)) + rng.normal(0, .03, 15), color="#276f96", s=14)
        axes[0].plot(x, .3 * (1 - np.exp(-x / 30)), color="#bb632a", lw=1.3, linestyle="--", label="Control")
        axes[0].set(xlabel="Time (min)", ylabel="Fraction phosphorylated", ylim=(-.05, 1))
        axes[0].legend(frameon=False)
        values = rng.normal(0, .6, (12, 8))
        axes[1].imshow(values, cmap="coolwarm", vmin=-1.5, vmax=1.5, interpolation="nearest", aspect="auto")
        axes[1].set(xlabel="Sample", ylabel="Gene", xticks=[0, 3, 7], xticklabels=["1", "4", "8"])
        fig.savefig(path, metadata={"CreationDate": None, "ModDate": None})
        plt.close(fig)


def pdf_inventory(data, page_index=0):
    counts = {"paintedPaths": 0, "textShows": 0, "imageInvocations": 0, "formInvocations": 0, "clipOperations": 0, "operators": 0, "maxFormDepth": 0}
    fonts = {}
    with pikepdf.open(BytesIO(data)) as document:
        page = document.pages[page_index]
        def walk(content, resources, depth=0, ancestors=()):
            counts["maxFormDepth"] = max(depth, counts["maxFormDepth"])
            for name, font in resources.get("/Font", {}).items():
                key = str(font.objgen)
                descendant = font.get("/DescendantFonts", [font])[0]
                descriptor = descendant.get("/FontDescriptor", {})
                fonts[key] = {"name": str(font.get("/BaseFont", name)), "subtype": str(font.get("/Subtype", "")), "toUnicode": "/ToUnicode" in font, "embedded": any(k in descriptor for k in ("/FontFile", "/FontFile2", "/FontFile3"))}
            for instruction in pikepdf.parse_content_stream(content):
                operator = str(instruction.operator)
                counts["operators"] += 1
                counts["paintedPaths"] += operator in {"S", "s", "f", "F", "f*", "B", "B*", "b", "b*"}
                counts["textShows"] += operator in {"Tj", "TJ", "'", '"'}
                counts["clipOperations"] += operator in {"W", "W*"}
                if operator == "Do":
                    obj = resources.get("/XObject", {}).get(instruction.operands[0])
                    if obj is None:
                        continue
                    subtype = str(obj.get("/Subtype", ""))
                    if subtype == "/Image":
                        counts["imageInvocations"] += 1
                    elif subtype == "/Form":
                        counts["formInvocations"] += 1
                        if obj.objgen not in ancestors:
                            walk(obj, obj.get("/Resources", resources), depth + 1, (*ancestors, obj.objgen))
        walk(page, page.get("/Resources", {}))
        return {"pageCount": len(document.pages), "pageNumber": page_index + 1, "mediaBox": [float(v) for v in page.MediaBox], "cropBox": [float(v) for v in page.get('/CropBox', page.MediaBox)], "counts": counts, "fonts": list(fonts.values())}


def render_pdf(data, path, index=0, scale=2):
    document = pdfium.PdfDocument(data)
    page = document[index]
    bitmap = page.render(scale=scale)
    bitmap.to_pil().convert("RGB").save(path)
    bitmap.close()
    page.close()
    document.close()


def pdf_text(data, index=0):
    document = pdfium.PdfDocument(data)
    page = document[index]
    textpage = page.get_textpage()
    text = textpage.get_text_range()
    textpage.close()
    page.close()
    document.close()
    return text


def pdf_text_provenance(data, index=0):
    """Independent PDFium character ownership and original glyph baselines."""
    document = pdfium.PdfDocument(data)
    page = document[index]
    textpage = page.get_textpage()
    left, bottom, right, top = page.get_bbox()
    rotation = page.get_rotation()
    glyphs = []
    for position in range(textpage.count_chars()):
        codepoint = pdfium_raw.FPDFText_GetUnicode(textpage, position)
        unicode = chr(codepoint) if codepoint <= 0x10ffff else "\ufffd"
        x, y = ctypes.c_double(), ctypes.c_double()
        valid = bool(pdfium_raw.FPDFText_GetCharOrigin(textpage, position, ctypes.byref(x), ctypes.byref(y)))
        if rotation == 90:
            sx, sy = y.value-bottom, x.value-left
        elif rotation == 180:
            sx, sy = right-x.value, y.value-bottom
        elif rotation == 270:
            sx, sy = top-y.value, right-x.value
        else:
            sx, sy = x.value-left, top-y.value
        glyphs.append({"index": position, "unicode": unicode, "x": sx*96/72 if valid else None, "y": sy*96/72 if valid else None, "generated": bool(pdfium_raw.FPDFText_IsGenerated(textpage, position))})
    text = textpage.get_text_range()
    textpage.close()
    page.close()
    document.close()
    return {"text": text, "glyphs": glyphs}


def text_coverage(source, inventory, source_glyphs, editable_glyphs):
    """Run count may change; every extracted printable character must survive."""
    runs = [r["text"] for r in inventory["rows"] if r.get("isText") and r["visible"] and not r["locked"]]
    expected = Counter(c for c in source if c.isprintable() and not c.isspace())
    actual = Counter(c for run in runs for c in run if c.isprintable() and not c.isspace())
    missing = expected - actual
    # PDFium reading-order newlines do not require newlines in editable runs.
    # Preserve literal source word spaces separately from operator/run counts.
    source_compact = "".join(c for c in source if c.isprintable() and not c.isspace())
    printable_glyphs = [g for g in source_glyphs if g['unicode'].isprintable() and not g['unicode'].isspace()]
    provenance_compact = ''.join(g['unicode'] for g in printable_glyphs)
    aligned = []
    text_rows = [r for r in inventory['rows'] if r.get('isText') and r['visible'] and not r['locked']]
    for row in text_rows:
        run = row['text']
        compact = "".join(c for c in run if c.isprintable() and not c.isspace())
        actual_glyphs = [g for g in editable_glyphs.get(row['id'], []) if g['unicode'].isprintable() and not g['unicode'].isspace()]
        candidates = []
        if compact and source_compact == provenance_compact and ''.join(g['unicode'] for g in actual_glyphs) == compact:
            start = 0
            while (position := provenance_compact.find(compact, start)) >= 0:
                glyphs = printable_glyphs[position:position+len(compact)]
                if all(g['x'] is not None for g in glyphs):
                    max_distance = max(math.hypot(a['x']-b['x'],a['y']-b['y']) for a,b in zip(actual_glyphs,glyphs))
                    # SVG's serialized glyph coordinates round at four decimals.
                    # This0.05scene-pixel allowance is much less than one raster
                    # pixel and cannot confuse different word/label locations.
                    if max_distance <= .05:
                        candidates.append({'start':position,'sourceIndices':[g['index'] for g in glyphs],'maxBaselineDistanceScenePixels':max_distance})
                start = position+1
        match = candidates[0] if len(candidates) == 1 else None
        segment = ''.join(g['unicode'] for g in source_glyphs[match['sourceIndices'][0]:match['sourceIndices'][-1]+1]) if match else ''
        aligned.append({'objectId':row['id'],"editableText": run, "sourceSegment": segment, "matched": bool(match), 'whitespaceOnly':not compact, 'sourceGlyphMatch':match,'candidateCount':len(candidates), "sourceWordSpaces": segment.count(" "), "editableWordSpaces": run.count(" ")})
    expected_spaces = sum(r["sourceWordSpaces"] for r in aligned)
    actual_spaces = sum(run.count(" ") for run in runs)
    correspondence_complete = all(r['matched'] or r['whitespaceOnly'] for r in aligned)
    return {"sourceText": source, "editableRuns": runs, "sourcePrintableCharacterCount": sum(expected.values()), "editablePrintableCharacterCount": sum(actual.values()), "missingPrintableCharacters": dict(missing), "sourceWordSpaces": expected_spaces, "editableWordSpaces": actual_spaces, "alignedRunSpacing": aligned, 'sourceGlyphCorrespondenceComplete':correspondence_complete,"printableCoverageComplete": not missing, "sourceWordSpaceCoverageComplete": correspondence_complete and all(r["editableWordSpaces"] >= r["sourceWordSpaces"] for r in aligned), "runCountCaveat": "Every non-whitespace run needs a unique matching Unicode sequence at independent source glyph baseline positions. Ambiguity is rejected. Genuine source word spaces inside that located run are required; PDFium reading-order spaces between separate editable runs are excluded. Whitespace-only runs remain visible in the evidence but have no printable baseline correspondence."}


def compare_images(reference, actual, output):
    ref = Image.open(reference).convert("RGB")
    image = Image.open(actual).convert("RGBA")
    white = Image.new("RGBA", image.size, "white")
    white.alpha_composite(image)
    image = white.convert("RGB")
    original_size = image.size
    if image.size != ref.size:
        if abs(image.width - ref.width) <= 2 and abs(image.height - ref.height) <= 2:
            # PDFium rounds page bounds up; Fabric integer canvas sizes round
            # down. Pad/crop at the page edge rather than shifting every glyph.
            normalized = Image.new("RGB", ref.size, "white")
            normalized.paste(image, (0, 0))
            image = normalized
        else:
            image = image.resize(ref.size, Image.Resampling.LANCZOS)
    a, b = np.asarray(ref, dtype=np.float32), np.asarray(image, dtype=np.float32)
    difference = np.abs(a - b)
    blur_a = np.asarray(ref.filter(ImageFilter.GaussianBlur(1)), dtype=np.float32)
    blur_b = np.asarray(image.filter(ImageFilter.GaussianBlur(1)), dtype=np.float32)
    ink = np.any(a < 240, axis=2) | np.any(b < 240, axis=2)
    significant = np.max(difference, axis=2) > 40
    diff = Image.fromarray(np.uint8(np.minimum(255, difference * 4)))
    diff.save(output)
    return {"referenceSize": list(ref.size), "actualSize": list(original_size), "sameDimensions": abs(original_size[0] - ref.size[0]) <= 2 and abs(original_size[1] - ref.size[1]) <= 2, "rgbMeanAbsoluteError": float(difference.mean() / 255), "blurredMeanAbsoluteError": float(np.abs(blur_a - blur_b).mean() / 255), "significantlyChangedPageFraction": float(significant.mean()), "significantlyChangedInkFraction": float(significant[ink].mean()) if ink.any() else 0, "metricCaveat": "Independent renderers differ in antialiasing. Images and difference map require original-resolution visual review; a numerical pass alone is not visual signoff."}


def embedded_sources(value):
    rows = []
    if isinstance(value, dict):
        for item in value.values():
            rows.extend(embedded_sources(item))
    elif isinstance(value, list):
        for item in value:
            rows.extend(embedded_sources(item))
    elif isinstance(value, str) and value.startswith("data:application/pdf;base64,"):
        rows.append(base64.b64decode(value.split(",", 1)[1], validate=True))
    return rows


def equal_serialized_artwork(left, right):
    """Figure serializes geometry at four decimals; identities/paint stay exact."""
    if isinstance(left, dict) and isinstance(right, dict):
        return left.keys() == right.keys() and all(equal_serialized_artwork(left[k], right[k]) for k in left)
    if isinstance(left, list) and isinstance(right, list):
        return len(left) == len(right) and all(equal_serialized_artwork(a, b) for a, b in zip(left, right))
    if isinstance(left, (int, float)) and isinstance(right, (int, float)) and not isinstance(left, bool) and not isinstance(right, bool):
        return abs(left - right) <= .0001
    return left == right


def artwork_without_session_isolation(value):
    if isinstance(value, dict):
        return {k: artwork_without_session_isolation(v) for k, v in value.items() if k != "figureStudioIsolationMeta"}
    if isinstance(value, list):
        return [artwork_without_session_isolation(v) for v in value]
    return value


def summarize_cpu_profile(profile):
    nodes = {n["id"]: n for n in profile["nodes"]}
    parents = {child: n["id"] for n in nodes.values() for child in n.get("children", [])}
    frames, exclusive, inclusive = {}, Counter(), Counter()
    def key(node_id):
        frame = nodes[node_id]["callFrame"]
        frame_key = (frame["functionName"], frame["url"], frame["lineNumber"], frame["columnNumber"])
        frames[frame_key] = frame
        return frame_key
    for node_id, delta in zip(profile.get("samples", []), profile.get("timeDeltas", [])):
        exclusive[key(node_id)] += delta
        seen = set()
        while node_id in nodes:
            seen.add(key(node_id))
            node_id = parents.get(node_id)
        for frame_key in seen:
            inclusive[frame_key] += delta
    def hot_frames(counts):
        return [{"sampledMs": micros / 1000, **frames[frame_key]} for frame_key, micros in counts.most_common(40)]
    return {"durationMs": (profile["endTime"] - profile["startTime"]) / 1000, "hottestExclusive": hot_frames(exclusive), "hottestInclusive": hot_frames(inclusive), "metricCaveat": "Inclusive samples count each function once per stack; parent/child totals overlap. Profiling adds overhead; acceptance timing is also measured in ordinary runs."}


INVENTORY_JS = """() => {
  const api=FigureStudio.app, roots=api.getCanvasObjectInventoryForQa().objects;
  const firstRoot=roots.length?api.getObjectByIdForQa(roots[0].id):null;
  const liveObjectsById=new Map(), indexed=new Set();
  function indexObject(object){
    if(!object||indexed.has(object))return;
    indexed.add(object);
    if(!liveObjectsById.has(object.figureId))liveObjectsById.set(object.figureId,object);
    const children=object.getObjects?.()||object._objects||[];
    for(const child of children)if(child&&(typeof child==='object'||typeof child==='function'))indexObject(child);
  }
  for(const object of firstRoot?.canvas?.getObjects?.()||[])indexObject(object);
  const rows=[], counts={paths:0,text:0,images:0,groups:0,clippedObjects:0,opaquePdfPages:0,editablePaths:0,editableText:0};
  function visit(o,parent='',depth=0) {
    const type=String(o.type||'').toLowerCase(), children=o.getObjects?.()||o._objects||[];
    const frame=o.pdfPageFrame===true;
    const isText=typeof o.text==='string', isPath=Array.isArray(o.path)||['rect','circle','ellipse','line','polyline','polygon','triangle'].includes(type);
    const meta=o.importMeta||{};
    const opaque=type==='image'&&(meta.importMode==='pdf-placed-source'||meta.importMode==='pdf-placed-page-1'||meta.import_mode==='pdf-placed-page-1'||o.source?.kind==='placed-pdf-page')&&children.length===0;
    if(!frame){counts.paths+=isPath;counts.text+=isText;counts.images+=type==='image';counts.groups+=children.length>0;counts.clippedObjects+=Boolean(o.clipPath);counts.opaquePdfPages+=Boolean(opaque);counts.editablePaths+=isPath&&!o.locked;counts.editableText+=isText&&!o.locked&&o.visible!==false;}
    rows.push({id:o.figureId||'',parent,depth,type,isText,frame,locked:Boolean(o.locked),visible:o.visible!==false,selectable:o.selectable!==false,evented:o.evented!==false,text:isText?o.text:'',fontFamily:isText?o.fontFamily:'',fontSize:isText?o.fontSize:null,fill:o.fill==null?'':typeof o.fill==='string'?o.fill:typeof o.fill,stroke:o.stroke==null?'':typeof o.stroke==='string'?o.stroke:typeof o.stroke,strokeWidth:o.strokeWidth,left:o.left,top:o.top,width:o.width,height:o.height,scaleX:o.scaleX,scaleY:o.scaleY,angle:o.angle,opacity:o.opacity,clip:Boolean(o.clipPath),childCount:children.length,opaque,path:Array.isArray(o.path)?o.path:null});
    for(const child of children)visit(child,o.figureId||parent,depth+1);
  }
  for(const root of roots){const o=liveObjectsById.get(root.id)||api.getObjectByIdForQa(root.id);if(o)visit(o);}
  return {counts,roots,rows,maxDepth:Math.max(0,...rows.map(r=>r.depth))};
}"""

RENDER_JS = """() => {
  const api=FigureStudio.app, v=api.getViewportStateForQa();
  const roots=api.getCanvasObjectInventoryForQa().objects;
  const root=roots.map(r=>api.getObjectByIdForQa(r.id)).find(o=>o?.canvas);
  if(!root)throw Error('No actual Fabric canvas');
  const canvas=root.canvas;
  // Figure zoom/pan are CSS transforms on a document-sized Fabric canvas.
  // PDF points become 96dpi artboard pixels; 1.5 gives a 144dpi reference.
  const image=canvas.toCanvasElement(1.5,{left:0,top:0,width:Math.ceil(v.artboard.width*1.5)/1.5,height:Math.ceil(v.artboard.height*1.5)/1.5});
  return {dataUrl:image.toDataURL('image/png'),viewport:v,canvasViewportTransform:canvas.viewportTransform};
}"""


def save_render(editor, output):
    result = editor.evaluate(RENDER_JS)
    output.write_bytes(base64.b64decode(result.pop("dataUrl").split(",", 1)[1]))
    return result


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(TARGET.runtime_root), **kwargs)
    def log_message(self, *_):
        pass


def main():
    global TARGET, FIGURE
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--observe-open-renders", action="store_true", help="Passively observe exact native artwork/selection/derived before/after render events and glyph counters; diagnostic timing only.")
    add_package_arguments(parser)
    parser.add_argument("--viewport", choices=["1280x800", "1440x1000", "1920x1080"], default="1440x1000")
    parser.add_argument("--theme", choices=["light", "dark"], default="light")
    parser.add_argument("--browser-channel", choices=["headless-shell", "chromium"], default="headless-shell",
                        help="Explicit headless runtime; chromium uses the full browser's new headless mode. Historical shell results remain separate.")
    parser.add_argument("--baseline", action="store_true", help="Record acceptance failures; harness errors still fail.")
    parser.add_argument("--fixture", type=Path, action="append", default=[])
    parser.add_argument("--page", type=int, default=1)
    parser.add_argument("--case", action="append", choices=["control", "dense", "forms", "matplotlib-truetype", "matplotlib-type3"], help="Select default generated cases.")
    parser.add_argument("--max-import-ms", type=float, default=15000)
    parser.add_argument("--max-event-loop-gap-ms", type=float, default=250)
    parser.add_argument("--profile-open", action="store_true", help="Capture Chromium CPU profile and long tasks around actual PDF Open.")
    parser.add_argument("--profile-open-cpu", action="store_true", help="Diagnostic CPU profile of public Open without replacing runtime methods.")
    parser.add_argument("--open-only", action="store_true", help="Bounded diagnostic of original Open and unedited PDF export; skips edit/save/cold Open qualification.")
    parser.add_argument("--continue-after-cold", action="store_true", help="Continue keyboard editing after fresh Open, then Undo/Redo, second actual Save and final PDF export.")
    parser.add_argument("--engine-diagnostic", action="store_true", help="Explicitly use internal Open/PDF-byte helpers, save probes and same-process cold context; never public transport acceptance.")
    parser.add_argument("--save-probe-diagnostic", action="store_true", help="Observe browser save exceptions with pass-through method probes while retaining public Open/export and fresh cold process; diagnostic only.")
    parser.add_argument("--host-save-diagnostic", action="store_true", help="Capture the original browser-host save exception at a CDP breakpoint without replacing methods; diagnostic only.")
    parser.add_argument("--output", type=Path, help="Fresh output directory inside this repository's qa_artifacts.")
    args = parser.parse_args()
    if args.profile_open and not args.engine_diagnostic:
        parser.error('--profile-open requires --engine-diagnostic because its history probe replaces runtime methods.')
    TARGET = FigureQaTarget.from_arguments(ROOT, args.package_root, args.package_sha256)
    FIGURE = TARGET.runtime_root
    width, height = (int(value) for value in args.viewport.split("x"))
    context_options = {"viewport": {"width": width, "height": height}, "accept_downloads": True, "color_scheme": args.theme}
    output = (args.output or ROOT / "qa_artifacts/figure-pdf-editing-browser" / datetime.now(timezone.utc).strftime("run-%Y%m%dT%H%M%S%fZ")).resolve()
    if not output.is_relative_to(ROOT / 'qa_artifacts'):
        parser.error('--output must stay inside this Figure repository qa_artifacts.')
    output.mkdir(parents=True, exist_ok=False)
    report = {"schema": "figureStudio.pdfEditingQualification.v1", "status": "RUNNING", "scope": "Shared static-web editor; no native PDF mutation service. These finite editing cases do not establish arbitrary-PDF acceptance.", "baselineMode": args.baseline, "checks": [], "cases": [], "captures": [], "pageErrors": [], "consoleErrors": [], "httpErrors": [], "externalRequests": [], "sourceHashesBefore": source_binding(), "qualificationLimitations": ["The retained actual Affinity node-edit comparison is separate evidence; it does not establish typography or arbitrary-PDF equivalence.", "Numerical reference comparisons complement independent original-resolution image review.", "Where declared, this journey checks marquee, Group/isolation, public Point Selection, anchor availability, native path dimensions, physical text size and keyboard editing. Actual point-motion continuation, mixed open-line/curve movement and topology operations retain their separate qualification."]}
    report["openOnlyDiagnostic"] = args.open_only
    report["continuedColdQualification"] = args.continue_after_cold
    report["target"] = TARGET.record()
    report["desktopContext"] = {"width": width, "height": height, "theme": args.theme}
    report['desktopContext']['browserChannel'] = args.browser_channel
    report['browserRuntimes'] = []
    browser_launch_options = {'headless': True}
    if args.browser_channel == 'chromium':
        browser_launch_options['channel'] = 'chromium'

    def record_browser_runtime(browser, phase_name):
        runtime = {'phase': phase_name, 'browserVersion': browser.version,
                   'headless': True, 'launchOptions': dict(browser_launch_options)}
        session = None
        try:
            session = browser.new_browser_cdp_session()
            runtime['graphics'] = session.send('SystemInfo.getInfo').get('gpu')
        except Exception as error:
            runtime['graphicsUnavailable'] = str(error)
        finally:
            if session:
                session.detach()
        report['browserRuntimes'].append(runtime)
    report['engineDiagnostic'] = args.engine_diagnostic
    report['saveProbeDiagnostic'] = args.save_probe_diagnostic
    report['hostSaveDiagnostic'] = args.host_save_diagnostic
    report['runtimeMethodProbes'] = args.engine_diagnostic or args.save_probe_diagnostic
    report['diagnosticOnly'] = args.engine_diagnostic or args.save_probe_diagnostic or args.host_save_diagnostic or args.profile_open_cpu or args.observe_open_renders
    report['openRenderObservationDiagnostic'] = args.observe_open_renders
    if args.observe_open_renders:
        report['qualificationLimitations'].append('Passive native before/after render listeners read glyph-cache counters and exact context identity. No product methods are replaced, but observer costs make timing diagnostic only.')
    report['cpuProfileOnlyDiagnostic'] = args.profile_open_cpu
    if args.save_probe_diagnostic:
        report['qualificationLimitations'].append('Pass-through browser-save method probes are installed. This run diagnoses public-route saving; it does not qualify unchanged public runtime or performance.')
    if args.host_save_diagnostic:
        report['qualificationLimitations'].append('A CDP breakpoint reads original host save failures and resumes execution. No runtime methods are replaced by this observer; debugger timing is diagnostic, never performance or unchanged-public-runtime acceptance.')
    report['fileTransport'] = 'internal helpers and controlled Save' if args.engine_diagnostic else 'public chooser/Open, Save download and Export As download'
    report['coldProcessMode'] = 'same-process context' if args.engine_diagnostic else 'new Chromium launch after closing warm browser'
    report['phases'] = []
    write_json(output / 'report.json', report)

    def phase(row, name):
        row['qaPhase'] = name
        report['phases'].append({'case': row['id'], 'name': name, 'atUtc': datetime.now(timezone.utc).isoformat()})
        write_json(output / 'report.json', report)

    def check(case, name, passed, detail=None):
        row = {"case": case, "name": name, "passed": bool(passed), "detail": detail}
        report["checks"].append(row)
        write_json(output / 'report.json', report)
        print(("PASS " if passed else "FAIL ") + case + ": " + name, flush=True)
    sources = []
    if args.fixture:
        sources = [{"id": f"real-{index + 1}", "path": path.resolve(), "kind": "external-unchanged-source", "generated": False, "page": args.page} for index, path in enumerate(args.fixture)]
    else:
        for name in args.case or ["control", "dense", "forms", "matplotlib-truetype", "matplotlib-type3"]:
            path = output / (name + ".pdf")
            if name.startswith("matplotlib"):
                generate_matplotlib(path, 42 if name.endswith("truetype") else 3)
            else:
                generate_reportlab(path, name)
            sources.append({"id": name, "path": path, "kind": "generated-producer-fixture", "generated": True, "page": 1})
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}/"
    report["ownedServerPort"] = server.server_port
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(**browser_launch_options)
            record_browser_runtime(browser, 'initial-process')
            for source in sources:
                case = source["id"]
                directory = output / case
                directory.mkdir()
                original = source["path"].read_bytes()
                row = {**source, "path": str(source["path"]), "sha256": sha(original), "byteCount": len(original), "sourceInventory": pdf_inventory(original, source["page"] - 1), "harnessCompleted": False}
                report["cases"].append(row)
                reference = directory / "source-pdfium.png"
                render_pdf(original, reference, source["page"] - 1)
                report["captures"].append({"path": str(reference), "purpose": "Unchanged source page rendered independently with PDFium; compare all plotted marks, labels, clipping and raster placement."})
                context = browser.new_context(**context_options)
                context.add_init_script("try{delete window.showSaveFilePicker;delete window.showOpenFilePicker;}catch(_){}")
                page = context.new_page()
                page.set_default_timeout(30000)
                page.on("pageerror", lambda error: report["pageErrors"].append({"case": case, "phase": row.get("qaPhase", "startup"), "message": str(error), "stack": getattr(error, "stack", "")}))
                page.on("console", lambda message: report["consoleErrors"].append({"case": case, "message": message.text}) if message.type == "error" else None)
                page.on("response", lambda response: report["httpErrors"].append({"case": case, "url": response.url, "status": response.status}) if response.status >= 400 else None)
                page.on("request", lambda request: report["externalRequests"].append(request.url) if request.url.startswith("http") and not request.url.startswith(base) else None)
                page.on("dialog", lambda dialog: dialog.accept(dialog.default_value or case + ".fsfigure"))
                def ready(target):
                    if args.host_save_diagnostic:
                        host_source = (FIGURE / 'web/browser-session.js').read_text(encoding='utf-8').splitlines()
                        failure_line = next(i for i, line in enumerate(host_source) if line.strip() == 'function failure(error) {') + 1
                        assert host_source[failure_line].strip() == 'failed = true;'
                        diagnostic = target.context.new_cdp_session(target)
                        diagnostic.send('Debugger.enable')
                        def host_failure_paused(event):
                            observation = {'phase': row.get('qaPhase'), 'reason': event.get('reason'), 'hitBreakpoints': event.get('hitBreakpoints')}
                            try:
                                observation['frames'] = [{'function': f.get('functionName'), 'url': f.get('url'), 'location': f.get('location')} for f in event.get('callFrames', [])[:20]]
                                result = diagnostic.send('Debugger.evaluateOnCallFrame', {'callFrameId': event['callFrames'][0]['callFrameId'], 'expression': '({name:error?.name,message:error?.message,code:error?.code,stack:error?.stack})', 'returnByValue': True})
                                observation['originalException'] = result
                            except Exception:
                                observation['diagnosticError'] = traceback.format_exc()
                            finally:
                                row.setdefault('browserHostSaveFailures', []).append(observation)
                                try:
                                    write_json(output / 'report.json', report)
                                except Exception:
                                    observation['pausedCheckpointError'] = traceback.format_exc()
                                finally:
                                    observation['resumeAttempted'] = True
                                    try:
                                        diagnostic.send('Debugger.resume')
                                        observation['resumeSent'] = True
                                    except Exception:
                                        observation['resumeSent'] = False
                                        observation['resumeError'] = traceback.format_exc()
                                    finally:
                                        try:
                                            write_json(output / 'report.json', report)
                                        except Exception:
                                            observation['outcomeCheckpointError'] = traceback.format_exc()
                        diagnostic.on('Debugger.paused', host_failure_paused)
                        observation = diagnostic.send('Debugger.setBreakpointByUrl', {'urlRegex': r'/web/browser-session\.js(?:\?|$)', 'lineNumber': failure_line})
                        row.setdefault('browserHostSaveObservers', []).append({'lineNumber': failure_line, 'breakpoint': observation})
                    target.goto(base + "web/index.html", wait_until="domcontentloaded")
                    frame = target.locator("#figure-editor-frame").element_handle().content_frame()
                    frame.locator("#figureStudioRoot[data-qa-state='ready']").wait_for(timeout=30000)
                    target.wait_for_function("document.body.dataset.browserChrome === 'integrated' && document.querySelector('.web-header')?.hidden")
                    effective_theme = "dark-graphite" if args.theme == "dark" else "light"
                    frame.wait_for_function("theme => document.getElementById('figureStudioRoot').dataset.theme === theme", arg=effective_theme)
                    if args.engine_diagnostic or args.save_probe_diagnostic:
                        target.evaluate(INSTALL_BROWSER_SAVE_PROBE_JS)
                    enter_current_document_sync(frame, kind='figure', preset='double-column', name='PDF corpus entry', timeout_ms=30000)
                    return frame

                def capture_editor(target, frame, destination):
                    write_json(output / 'report.json', report)
                    frame.locator('#toast.show').wait_for(state='hidden', timeout=12000)
                    frame.evaluate('()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))')
                    target.screenshot(path=str(destination), animations='disabled')

                def public_open(target, frame):
                    # Passive measurements observe the unchanged public command.
                    failed = False
                    try:
                        if args.observe_open_renders:
                            frame.evaluate('''() => {
                              const rows=[],pending=new Map();
                              const stats=()=>{const d=globalThis.FigureStudioPdfiumTextRasterizer?.diagnostics();return d?Object.fromEntries(['painted','prepared','hits','misses','bitmapTransfers','tileBytes','fallbacks','errors'].map(k=>[k,d[k]])):null;};
                              const stop=FigureStudio.app.observeCanvasRenderForQa(event=>{
                                const {context,...data}=event;
                                const m=context.getTransform(),row={...data,atMs:performance.now(),contextTransform:[m.a,m.b,m.c,m.d,m.e,m.f],stats:stats()};
                                if(event.phase==='before'){const stack=pending.get(context)||[];stack.push(row);pending.set(context,stack);}
                                else {const before=pending.get(context)?.pop();row.before=before||null;row.durationMs=before?row.atMs-before.atMs:null;rows.push(row);}
                              });
                              globalThis.__corpusOpenRenders={rows,pending,stop};
                            }''')
                        frame.evaluate('''() => {
                          const p={start:performance.now(),last:performance.now(),gaps:[],longTasks:[]};
                          p.observer=new PerformanceObserver(list=>{for(const e of list.getEntries())p.longTasks.push({startMs:e.startTime-p.start,durationMs:e.duration});});
                          p.observer.observe({type:'longtask',buffered:false});
                          p.timer=setInterval(()=>{const now=performance.now();p.gaps.push(now-p.last);p.last=now;},16);
                          globalThis.__corpusPublicOpenObservation=p;
                        }''')
                        frame.locator('[data-menu="file"] > .menu-trigger').click()
                        frame.locator('[data-menu="file"] [data-command="new-project"]').click()
                        frame.locator('#newDocumentBackdrop').wait_for(state='visible')
                        with target.expect_file_chooser() as chooser:
                            frame.locator('#openArtworkDocumentBtn:visible').click()
                        row['publicOpenChooser'] = {'inputId': chooser.value.element.get_attribute('id'), 'accept': chooser.value.element.get_attribute('accept')}
                        assert row['publicOpenChooser']['inputId'] == 'openArtworkDocumentInput'
                        chooser.value.set_files(str(source['path']))
                        frame.locator('#importPlacementReview:not([hidden])').wait_for(timeout=30000)
                        frame.locator('#pdfEntryModeSelect:visible').select_option('editable')
                        frame.locator('#pdfPageModeSelect:visible').select_option('custom')
                        frame.locator('#pdfPageRangeInput:visible').fill(str(source['page']))
                        frame.locator('#importPlacementCenterBtn:visible').click()
                        frame.locator('#importPlacementReview').wait_for(state='hidden', timeout=30000)
                        frame.wait_for_function('FigureStudio.app.getBrowserSessionState().ready && !FigureStudio.app.getBrowserSessionState().busy', timeout=30000)
                        frame.evaluate('()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))')
                        return frame.evaluate('''() => {
                          const p=globalThis.__corpusPublicOpenObservation;
                          return {opened:{publicChooser:true},startedAtMs:p.start,durationMs:performance.now()-p.start,eventLoopGaps:p.gaps,maxEventLoopGapMs:Math.max(0,...p.gaps),longTasks:p.longTasks};
                        }''')
                    except BaseException:
                        failed = True
                        raise
                    finally:
                        try:
                            if args.observe_open_renders:
                                observed = frame.evaluate('''() => {const p=globalThis.__corpusOpenRenders;if(!p)return {rows:[],unmatchedBefore:[]};try{return {rows:p.rows,unmatchedBefore:[...p.pending.values()].flat()};}finally{p.stop();delete globalThis.__corpusOpenRenders;}}''')
                                row['openRenderObservations'] = observed['rows']
                                row['openUnmatchedBeforeRenders'] = observed['unmatchedBefore']
                            frame.evaluate('''() => {const p=globalThis.__corpusPublicOpenObservation;if(p){clearInterval(p.timer);p.observer.disconnect();delete globalThis.__corpusPublicOpenObservation;}}''')
                        except Exception:
                            row['publicOpenObserverCleanupError'] = traceback.format_exc()
                            if not failed:
                                raise

                def export_pdf(target, frame, destination):
                    if args.engine_diagnostic:
                        metadata = frame.evaluate('() => FigureStudio.app.buildPdfExportBytesForQa()')
                        data = bytes(metadata.pop('bytes'))
                        destination.write_bytes(data)
                        return data, {'transport': 'internal-byte-helper', **metadata}
                    frame.locator('[data-figure-layout-command="export-as"]:visible').first.click()
                    for selector, value in [('[data-export-as-format]', 'pdf'), ('[data-export-as-scope]', 'current')]:
                        field = frame.locator(selector)
                        field.wait_for(state='visible')
                        if field.input_value() != value:
                            field.select_option(value)
                    frame.wait_for_function("FigureStudio.app.getExportAsStateForQa().reviewStatus==='ready' && !document.querySelector('[data-export-as-submit]').disabled", timeout=20000)
                    reviewed = frame.evaluate('() => FigureStudio.app.getExportAsStateForQa()')
                    request = reviewed['reviewedRequest']
                    assert request['format'] == 'pdf' and request['scope'] == 'current' and 'background' not in request and request['delivery'] == 'file'
                    assert not frame.locator('[data-export-as-background]').is_visible()
                    with target.expect_download(timeout=30000) as pending:
                        frame.locator('[data-export-as-submit]').click()
                        frame.wait_for_function("['error','success'].includes(document.querySelector('[data-export-as-status]')?.dataset.tone)", timeout=30000)
                        outcome = frame.evaluate("() => {const e=document.querySelector('[data-export-as-status]');return {tone:e.dataset.tone,message:e.textContent};}")
                        assert outcome['tone'] == 'success', outcome
                    downloaded = pending.value
                    assert downloaded.suggested_filename.lower().endswith('.pdf')
                    downloaded.save_as(destination)
                    frame.wait_for_function('!FigureStudio.app.getExportAsStateForQa().exporting')
                    capture = directory / (destination.stem + '-dialog.png')
                    report['captures'].append({'path': str(capture), 'purpose': 'Actual public PDF/current Export As controls and success after the browser download; PDF has no background selector. A modal view, not unobstructed artwork.'})
                    write_json(output / 'report.json', report)
                    capture_editor(target, frame, capture)
                    frame.locator('[data-export-as-close]').click()
                    return destination.read_bytes(), {'transport': 'actual-public-download', 'suggestedFilename': downloaded.suggested_filename, 'reviewed': reviewed, 'outcome': outcome}
                try:
                    phase(row, 'startup')
                    editor = ready(page)
                    phase(row, 'pdf-open')
                    profile_session = None
                    if args.profile_open or args.profile_open_cpu:
                        if args.profile_open:
                            row["historySliceProbeInstalled"] = editor.evaluate(INSTALL_HISTORY_SLICE_PROBE_JS)
                        profile_session = context.new_cdp_session(page)
                        profile_session.send("Profiler.enable")
                        profile_session.send("Profiler.start")
                        row["profileStartedAtPerformanceMs"] = editor.evaluate("() => performance.now()")
                    row["open"] = public_open(page, editor) if not args.engine_diagnostic else editor.evaluate("""async value => {
                      const gaps=[],longTasks=[],start=performance.now();let last=start;
                      const observer=new PerformanceObserver(list=>{for(const entry of list.getEntries())longTasks.push({startMs:entry.startTime-start,durationMs:entry.duration});});
                      observer.observe({type:'longtask',buffered:false});
                      const timer=setInterval(()=>{const now=performance.now();gaps.push(now-last);last=now;},16);
                      try {
                        const opened=await FigureStudio.app.openPdfBytesAsDocumentForQa(value.bytes,value.name,{pdfEntryMode:'editable',pdfPageMode:'range',pdfPageRange:String(value.page)});
                        await new Promise(requestAnimationFrame);await new Promise(requestAnimationFrame);
                        return {opened,durationMs:performance.now()-start,eventLoopGaps:gaps,maxEventLoopGapMs:Math.max(0,...gaps),longTasks};
                      } finally {clearInterval(timer);observer.disconnect();}
                    }""", {"bytes": list(original), "name": source["path"].name, "page": source["page"]})
                    if profile_session:
                        row["historySynchronousSlices"] = editor.evaluate("() => globalThis.__figurePdfQaHistorySlices || []")
                        profile = profile_session.send("Profiler.stop")["profile"]
                        write_json(directory / "pdf-open-cpu-profile.json", profile)
                        row["openCpuProfile"] = {"path": str(directory / "pdf-open-cpu-profile.json"), **summarize_cpu_profile(profile)}
                        profile_session.detach()
                    row["initialNativeTextPaint"] = editor.evaluate("() => globalThis.FigureStudioPdfiumTextRasterizer?.diagnostics() || null")
                    phase(row, 'source-render-and-export')
                    editor.evaluate("() => FigureStudio.app.clearSelectionForQa()")
                    editor.wait_for_timeout(100)
                    inventory = editor.evaluate(INVENTORY_JS)
                    row["openedInventory"] = inventory
                    row["entry"] = editor.evaluate("() => FigureStudio.app.getPdfEntrySummaryForQa(FigureStudio.app.getCanvasObjectInventoryForQa().objects[0]?.id)")
                    row["editability"] = editor.evaluate("() => FigureStudio.app.getPdfEditabilityInventoryForQa()")
                    row["textState"] = editor.evaluate("() => FigureStudio.app.getPdfTextEditingStateForQa()")
                    actual = directory / "opened-artwork.png"
                    row["openedViewport"] = save_render(editor, actual)
                    row["renderCaches"] = editor.evaluate("""() => {
                      const app=FigureStudio.app, rows=[];
                      function visit(object) {
                        if(object._cacheCanvas) rows.push({id:object.figureId,type:object.type,
                          width:object.width,height:object.height,opacity:object.opacity,
                          ownCaching:object.ownCaching,objectCaching:object.objectCaching,
                          clipType:object.clipPath?.type,cacheWidth:object._cacheCanvas.width,
                          cacheHeight:object._cacheCanvas.height,zoomX:object.zoomX,zoomY:object.zoomY});
                        (object.getObjects?.()||[]).forEach(visit);
                      }
                      app.getCanvasObjectInventoryForQa().objects.forEach(row=>visit(app.getObjectByIdForQa(row.id)));
                      return rows;
                    }""")
                    row['openedImportMetadata'] = editor.evaluate("""roots => roots.map(r => {
                      const meta=FigureStudio.app.getObjectByIdForQa(r.id)?.importMeta||{};
                      return {id:r.id,importMode:meta.importMode,convertedPdf:meta.convertedPdf||null,pdfEditableImport:meta.pdfEditableImport||null};
                    })""", inventory['roots'])
                    conversion = next((meta['convertedPdf'] for meta in row['openedImportMetadata'] if meta.get('convertedPdf')), {})
                    check(case, 'live SVG conversion metadata retains nonzero path, text and image query counts', (not row['sourceInventory']['counts']['paintedPaths'] or conversion.get('pathCount',0)>0) and (not row['sourceInventory']['counts']['textShows'] or conversion.get('textCount',0)>0) and (not row['sourceInventory']['counts']['imageInvocations'] or conversion.get('imageCount',0)>0), conversion)
                    box = row['sourceInventory']['cropBox']
                    row['physicalPageGeometry'] = {'sourcePoints': [box[2]-box[0], box[3]-box[1]], 'expectedScenePixels': [(box[2]-box[0])*96/72, (box[3]-box[1])*96/72], 'openedScene': row['openedViewport']['viewport']['artboard']}
                    opened_art = row['physicalPageGeometry']['openedScene']
                    check(case, 'logical artboard preserves physical PDF point dimensions', all(abs(opened_art[k]-v) < .0001 for k,v in zip(('width','height'),row['physicalPageGeometry']['expectedScenePixels'])), row['physicalPageGeometry'])
                    row["openedFidelity"] = compare_images(reference, actual, directory / "opened-difference.png")
                    row["openedNativeTextPaint"] = editor.evaluate("() => globalThis.FigureStudioPdfiumTextRasterizer?.diagnostics() || null")
                    report["captures"].append({"path": str(actual), "purpose": "Actual Figure Fabric artboard after editable PDF Open; every mark, live label, clipping and image should match the unchanged PDFium source."})
                    report["captures"].append({"path": str(directory / "opened-editor.png"), "purpose": "Entire shared Figure editor after PDF Open at standard desktop size; inspect fitted plot, interface status and real selectable content."})
                    capture_editor(page, editor, directory / 'opened-editor.png')
                    counts, expected = inventory["counts"], row["sourceInventory"]["counts"]
                    source_text = pdf_text_provenance(original, source['page']-1)
                    original_glyphs = editor.evaluate(PDF_TEXT_SOURCE_GLYPHS_JS)
                    write_json(directory/'source-text-glyph-provenance.json',source_text)
                    write_json(directory/'opened-text-glyph-provenance.json',original_glyphs)
                    row["textCoverage"] = text_coverage(source_text['text'],inventory,source_text['glyphs'],original_glyphs)
                    check(case, 'editable text has unique independent source glyph location correspondence', row['textCoverage']['sourceGlyphCorrespondenceComplete'], {'unmatchedRuns':[r for r in row['textCoverage']['alignedRunSpacing'] if not r['matched'] and not r['whitespaceOnly']]})
                    check(case, "all source path paint invocations have editable vector objects", counts["editablePaths"] >= expected["paintedPaths"], {"actual": counts["editablePaths"], "expected": expected["paintedPaths"]})
                    check(case, "recoverable source printable characters remain actual editable text", row["textCoverage"]["printableCoverageComplete"], row["textCoverage"])
                    check(case, "source word spacing remains in recoverable editable text", row["textCoverage"]["sourceWordSpaceCoverageComplete"], {"sourceWordSpaces": row["textCoverage"]["sourceWordSpaces"], "editableWordSpaces": row["textCoverage"]["editableWordSpaces"]})
                    check(case, "no whole-page opaque preview substitutes for editable content", counts["opaquePdfPages"] == 0, counts)
                    check(case, "positioned source image invocations remain separate image objects", counts["images"] - counts["opaquePdfPages"] >= expected["imageInvocations"], {"actual": counts["images"], "expected": expected["imageInvocations"]})
                    check(case, "source clipping has a retained editable clip relationship", expected["clipOperations"] == 0 or counts["clippedObjects"] > 0, {"actual": counts["clippedObjects"], "expectedClipOperations": expected["clipOperations"]})
                    check(case, "nested Form invocations retain nested editable groups", expected["maxFormDepth"] < 2 or inventory["maxDepth"] >= expected["maxFormDepth"] + 1, {"actualDepth": inventory["maxDepth"], "formDepth": expected["maxFormDepth"]})
                    fidelity = row["openedFidelity"]
                    check(case, "opened artboard matches independent reference within provisional raster tolerance", fidelity["sameDimensions"] and fidelity["blurredMeanAbsoluteError"] <= .01 and fidelity["significantlyChangedPageFraction"] <= .025, fidelity)
                    check(case, "PDF Open completes within dense-file budget", row["open"]["durationMs"] <= args.max_import_ms, row["open"]["durationMs"])
                    check(case, "PDF Open does not monopolize browser event loop", row["open"]["maxEventLoopGapMs"] <= args.max_event_loop_gap_ms, row["open"]["maxEventLoopGapMs"])
                    longest_task = max((task["durationMs"] for task in row["open"]["longTasks"]), default=0)
                    check(case, "PDF Open has no main-thread task above 100 ms", longest_task <= 100, longest_task)
                    phase(row, 'actual-unedited-pdf-export')
                    data, exported = export_pdf(page, editor, directory / 'unedited-export.pdf')
                    row["uneditedExport"] = {**exported, "sha256": sha(data), "inventory": pdf_inventory(data)}
                    render_pdf(data, directory / "unedited-export-pdfium.png")
                    row["uneditedExportFidelity"] = compare_images(reference, directory / "unedited-export-pdfium.png", directory / "unedited-export-difference.png")
                    fidelity = row["uneditedExportFidelity"]
                    check(case, "unedited PDF export preserves source appearance", fidelity["sameDimensions"] and fidelity["blurredMeanAbsoluteError"] <= .01 and fidelity["significantlyChangedPageFraction"] <= .025, fidelity)
                    if args.open_only:
                        row["harnessCompleted"] = True
                        row["skippedQualification"] = "Actual edit, saved-file cold Open and edited export omitted by --open-only diagnostic."
                        continue
                    # Ungroup the imported complete plot, then use the normal
                    # Group command. This checks source ownership through Group.
                    roots = inventory["roots"]
                    row["groupWorkflow"] = {"status": "unavailable"}
                    if len(roots) == 1 and counts["groups"] > 0:
                        phase(row, 'ungroup-and-marquee')
                        row["ungroupCommandAttempts"] = []
                        row['groupCommandFocusBefore'] = editor.evaluate('() => ({tag:document.activeElement?.tagName,id:document.activeElement?.id,className:String(document.activeElement?.className||"")})')
                        # Export As returns focus to its button. A real canvas
                        # click returns keyboard ownership to the drawing before
                        # selecting the root and sending the Group shortcuts.
                        editor.locator('.upper-canvas:visible').click(position={'x': 8, 'y': 8})
                        row['groupCommandFocusAfter'] = editor.evaluate('() => ({tag:document.activeElement?.tagName,id:document.activeElement?.id,className:String(document.activeElement?.className||"")})')
                        assert row['groupCommandFocusAfter']['tag'] == 'CANVAS' and 'upper-canvas' in row['groupCommandFocusAfter']['className']
                        editor.evaluate("id => {FigureStudio.app.activateToolForQa('select');FigureStudio.app.selectObjectsByIdsForQa([id]);}", roots[0]["id"])
                        row["ungroupCommandAttempts"].append({"rootIds": [roots[0]["id"]], "historyBefore": editor.evaluate("() => FigureStudio.app.getHistoryStateForQa()"), "completed": False})
                        editor.locator("body").press("Control+Shift+g")
                        row["ungroupCommandAttempts"][-1].update({"completed": True, "historyAfter": editor.evaluate("() => FigureStudio.app.getHistoryStateForQa()")})
                        release_steps = []
                        for _ in range(8):
                            editor.wait_for_timeout(250)
                            state = editor.evaluate("""() => {const a=FigureStudio.app,rows=a.getCanvasObjectInventoryForQa().objects;return {ids:rows.map(r=>r.id),singleGroup:rows.length===1&&Boolean(a.getObjectByIdForQa(rows[0].id)?.getObjects?.().length)};}""")
                            release_steps.append(state)
                            if not state["singleGroup"]:
                                break
                            if len(release_steps) > 1 and state["ids"] == release_steps[-2]["ids"]:
                                break
                            editor.evaluate("ids => FigureStudio.app.selectObjectsByIdsForQa(ids)", state["ids"])
                            row["ungroupCommandAttempts"].append({"rootIds": state["ids"], "historyBefore": editor.evaluate("() => FigureStudio.app.getHistoryStateForQa()"), "completed": False})
                            editor.locator("body").press("Control+Shift+g")
                            row["ungroupCommandAttempts"][-1].update({"completed": True, "historyAfter": editor.evaluate("() => FigureStudio.app.getHistoryStateForQa()")})
                        editor.evaluate("() => FigureStudio.app.clearSelectionForQa()")
                        released = editor.evaluate("""() => {
                          const a=FigureStudio.app, rows=a.getCanvasObjectInventoryForQa().objects;
                          const boxes=rows.map(row=>a.getObjectByIdForQa(row.id)?.getBoundingRect()).filter(Boolean);
                          return {ids:rows.map(row=>row.id), bounds:boxes.length?{left:Math.min(...boxes.map(b=>b.left)),top:Math.min(...boxes.map(b=>b.top)),right:Math.max(...boxes.map(b=>b.left+b.width)),bottom:Math.max(...boxes.map(b=>b.top+b.height))}:null,artboard:a.getViewportStateForQa().artboard};
                        }""")
                        marquee = {"status": "unavailable", "released": released, "ungroupSteps": release_steps}
                        if released["bounds"] and len(released["ids"]) > 1:
                            # Use the real Reset view control so the artboard edge
                            # is inside the viewport before beginning a canvas drag.
                            reset = editor.locator("#resetViewBtn")
                            if reset.is_visible():
                                reset.click()
                                editor.wait_for_timeout(250)
                            marquee["viewport"] = editor.evaluate("() => FigureStudio.app.getViewportStateForQa()")
                            box, art = released["bounds"], released["artboard"]
                            points = [{"x": max(1, box["left"] - 6), "y": max(1, box["top"] - 6)}, {"x": min(art["width"] - 1, box["right"] + 6), "y": min(art["height"] - 1, box["bottom"] + 6)}]
                            clients = [editor.evaluate("p => FigureStudio.app.sceneToClientForQa(p)", p) for p in points]
                            frame = page.locator("#figure-editor-frame").bounding_box()
                            marquee["startTarget"] = editor.evaluate("p => FigureStudio.app.getCanvasTargetInfoForQa(p)", points[0])
                            marquee["startDomTarget"] = editor.evaluate("p => {const el=document.elementFromPoint(p.x,p.y);return el?{tag:el.tagName,id:el.id,className:String(el.className),pointerEvents:getComputedStyle(el).pointerEvents}:null;}", clients[0])
                            page.mouse.move(clients[0]["x"] + frame["x"], clients[0]["y"] + frame["y"])
                            page.mouse.down()
                            page.mouse.move(clients[1]["x"] + frame["x"], clients[1]["y"] + frame["y"], steps=12)
                            page.mouse.up()
                            editor.wait_for_timeout(250)
                            selected = editor.evaluate("() => FigureStudio.app.getSelectionStateForQa()")
                            marquee.update({"status": "attempted", "scenePoints": points, "selection": selected})
                            check(case, "whole plot pointer marquee selects every released object", set(selected.get("selectedIds", [])) == set(released["ids"]), marquee)
                        else:
                            check(case, "whole plot pointer marquee selects every released object", False, marquee)
                        # Keep the remaining journey diagnostic even after a failed
                        # pointer marquee; this explicit fallback is not a pass.
                        if set(marquee.get("selection", {}).get("selectedIds", [])) != set(released["ids"]):
                            editor.evaluate("ids => FigureStudio.app.selectObjectsByIdsForQa(ids)", released["ids"])
                        editor.locator("body").press("Control+g")
                        row["groupWorkflow"] = {"status": "attempted", "releasedCount": len(released["ids"]), "marquee": marquee, "grouped": editor.evaluate("() => FigureStudio.app.getCanvasObjectInventoryForQa()")}
                    grouped_inventory = editor.evaluate(INVENTORY_JS)
                    check(case, "complete plot ungroup and Group retain every vector and text", row["groupWorkflow"].get("releasedCount", 0) > 1 and grouped_inventory["counts"]["paths"] == counts["paths"] and grouped_inventory["counts"]["text"] == counts["text"], row["groupWorkflow"])
                    # Exercise isolation and a real Inspector paint change only on
                    # an actual vector leaf; never recolor a page raster as a pass.
                    vectors = [v for v in grouped_inventory["rows"] if isinstance(v["path"], list) and not v["locked"] and v["parent"] and not v["frame"]]
                    bounded_vectors = [v for v in vectors if v["width"] * abs(v["scaleX"]) < row["openedViewport"]["viewport"]["artboard"]["width"] * .9 and v["height"] * abs(v["scaleY"]) < row["openedViewport"]["viewport"]["artboard"]["height"] * .9]
                    neutral_paints = {"", "none", "transparent", "black", "white", "#000000", "#000", "#ffffff", "#fff", "rgb(0,0,0)", "rgb(255,255,255)", "rgba(0,0,0,0)"}
                    colored_vectors = [v for v in bounded_vectors if v["fill"].replace(" ", "").lower() not in neutral_paints]
                    vector = next(iter(colored_vectors or bounded_vectors or vectors), None)
                    row["vectorEdit"] = {"status": "unavailable"}
                    if vector:
                        phase(row, 'point-selection-and-edit-nodes')
                        editor.evaluate("() => {FigureStudio.app.clearSelectionForQa();FigureStudio.app.activateToolForQa('directSelect');}")
                        # Point Selection can reveal the Inspector and recenter
                        # the CSS canvas. Settle that UI before converting the
                        # source point; retain both origins to diagnose a later
                        # selection-driven camera change independently.
                        editor.wait_for_timeout(250)
                        editor.evaluate("() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))")
                        point = editor.evaluate("id => FigureStudio.app.getPathSegmentPointForQa(id,0,.65)", vector["id"])
                        probe = editor.evaluate("id => FigureStudio.app.getPathPaintedHitProbeForQa(id)", vector["id"])
                        interior = editor.evaluate("""args => {
                          const app=FigureStudio.app,f=window.fabric,h=window.FigureStudioPdfPaintHitTest;
                          if(!f)return null;
                          const leaves=args.leaves.map(id=>app.getObjectByIdForQa(id)).filter(Boolean).reverse(),tolerance=3/Math.max(.01,app.getViewportStateForQa().zoom||1);
                          for(const id of args.candidates){
                          const o=app.getObjectByIdForQa(id);
                          if(!o||!Array.isArray(o.path)||!o.hasFill())continue;
                          const ctx=document.createElement('canvas').getContext('2d'),p=new Path2D(f.util.joinPath(o.path)),m=o.calcTransformMatrix();
                          for(const [u,v] of [[0,0],[-.2,0],[.2,0],[0,-.2],[0,.2]]){
                            const local={x:u*o.width,y:v*o.height};
                            if(!ctx.isPointInPath(p,local.x+(o.pathOffset?.x||0),local.y+(o.pathOffset?.y||0),o.fillRule==='evenodd'?'evenodd':'nonzero'))continue;
                            const point=f.util.transformPoint(new f.Point(local.x,local.y),m);
                            if(h?.insideClips(o,point,f)===false)continue;
                            const front=leaves.find(leaf=>h?.hitObject(leaf,point,{fabric:f,tolerance}));
                            if(front?.figureId!==id)continue;
                            return {objectId:id,point,matrix:m,pathOffset:o.pathOffset,bounds:o.getBoundingRect(),insideNativePath:true,frontmostLeaf:front?.figureId||null,tolerance,canvasZoom:o.canvas?.getZoom?.(),figureZoom:app.getViewportStateForQa().zoom};
                          }
                          }
                          return null;
                        }""", {"candidates": [v['id'] for v in colored_vectors] if colored_vectors else [vector['id']], "leaves": [v['id'] for v in grouped_inventory['rows'] if not v['childCount']]})
                        if interior:
                            vector = next(v for v in vectors if v['id'] == interior['objectId'])
                            point = interior["point"]
                            probe = editor.evaluate("id => FigureStudio.app.getPathPaintedHitProbeForQa(id)", vector['id'])
                        row["pointSelection"] = {"status": "unavailable", "candidate": vector["id"], "point": point, "paintedProbe": probe, "nativeInterior": interior, "pointChoice": "Filled mark interior confirmed by native Canvas isPointInPath and source clips; otherwise first actual path segment at t=.65. A boundary midpoint can overlap a plotted axis or label."}
                        if point:
                            client = editor.evaluate("point => FigureStudio.app.sceneToClientForQa(point)", point)
                            roundtrip = editor.evaluate("point => FigureStudio.app.clientToSceneForQa(point)", client)
                            iframe = page.locator("#figure-editor-frame").bounding_box()
                            row["pointSelection"].update({"clientPoint": client, "sceneRoundtrip": roundtrip, "iframeBounds": iframe, "canvasTargetBeforeClick": editor.evaluate("point => FigureStudio.app.getCanvasTargetInfoForQa(point)", point), "beforeClickViewport": editor.evaluate("() => {const app=FigureStudio.app,isolation=app.getGroupIsolationStateForQa();return {canvasRect:isolation.canvasRect,canvasSize:isolation.canvasSize,view:app.getViewportStateForQa()};}")})
                            started = time.perf_counter()
                            page.mouse.click(client["x"] + iframe["x"], client["y"] + iframe["y"])
                            editor.evaluate("() => new Promise(requestAnimationFrame)")
                            row["pointSelection"].update({"status": "attempted", "elapsedMs": (time.perf_counter() - started) * 1000, "state": editor.evaluate("() => FigureStudio.app.getDirectSelectionStateForQa()"), "isolationState": editor.evaluate("() => FigureStudio.app.getGroupIsolationStateForQa()"), "afterClickView": editor.evaluate("() => FigureStudio.app.getViewportStateForQa()")})
                        editor.wait_for_timeout(250)
                        direct = editor.evaluate("() => FigureStudio.app.getDirectSelectionStateForQa()")
                        isolation_state = editor.evaluate("() => FigureStudio.app.getGroupIsolationStateForQa()")
                        row["pointSelection"]["firstClick"] = {"directObjectIds": direct.get("objectIds", []), "selectedIds": isolation_state.get("selectedIds", []), "isolationDepth": isolation_state.get("depth", 0), "leafReached": vector["id"] in direct.get("objectIds", []) or vector["id"] in isolation_state.get("selectedIds", [])}
                        row["pointSelection"]["nestedIsolationClicks"] = []
                        # Ordinary nested groups use the visible Isolation Mode
                        # workflow: double-click the selected containing group,
                        # then click the same painted path within that boundary.
                        for _ in range(8):
                            if vector["id"] in direct.get("objectIds", []) or vector["id"] in isolation_state.get("selectedIds", []):
                                break
                            selected_ids = isolation_state.get("selectedIds", [])
                            selected_group = editor.evaluate("ids => ids.length===1 && Boolean(FigureStudio.app.getObjectByIdForQa(ids[0])?.getObjects?.().length)", selected_ids)
                            if not selected_group or not point:
                                break
                            client = editor.evaluate("point => FigureStudio.app.sceneToClientForQa(point)", point)
                            iframe = page.locator("#figure-editor-frame").bounding_box()
                            page.mouse.dblclick(client["x"] + iframe["x"], client["y"] + iframe["y"])
                            editor.wait_for_timeout(250)
                            after_double = editor.evaluate("() => FigureStudio.app.getGroupIsolationStateForQa()")
                            group_action = {"doubleClickDepth": after_double.get("depth", 0)}
                            if after_double.get("depth", 0) == isolation_state.get("depth", 0):
                                editor.evaluate("() => FigureStudio.app.setRailCollapsedForQa('right',false)")
                                action = editor.locator('[data-context-action="enter-isolated-subgroup"]:visible,[data-context-action="isolate-group"]:visible').first
                                if not action.count() and editor.locator("#figure-more-properties").is_visible() and editor.locator("#figure-more-properties").get_attribute("aria-expanded") != "true":
                                    editor.locator("#figure-more-properties").click()
                                    editor.wait_for_timeout(250)
                                    action = editor.locator('[data-context-action="enter-isolated-subgroup"]:visible,[data-context-action="isolate-group"]:visible').first
                                group_action.update({"buttonCount": action.count(), "buttonEnabled": action.is_enabled() if action.count() else False, "buttonLabel": action.inner_text() if action.count() else None})
                                if action.count() and action.is_enabled():
                                    action.click()
                                    editor.wait_for_timeout(250)
                            client = editor.evaluate("point => FigureStudio.app.sceneToClientForQa(point)", point)
                            page.mouse.click(client["x"] + iframe["x"], client["y"] + iframe["y"])
                            editor.wait_for_timeout(250)
                            direct = editor.evaluate("() => FigureStudio.app.getDirectSelectionStateForQa()")
                            isolation_state = editor.evaluate("() => FigureStudio.app.getGroupIsolationStateForQa()")
                            step = {"directObjectIds": direct.get("objectIds", []), "selectedIds": isolation_state.get("selectedIds", []), "isolationDepth": isolation_state.get("depth", 0), "path": isolation_state.get("path", []), "visibleGroupAction": group_action}
                            row["pointSelection"]["nestedIsolationClicks"].append(step)
                            if step["selectedIds"] == selected_ids:
                                break
                        row["pointSelection"].update({"settledState": direct, "settledIsolationState": isolation_state})
                        isolated_ids = isolation_state.get("selectedIds", [])
                        check(case, "Point Selection and visible nested isolation select the intended imported vector", vector["id"] in direct.get("objectIds", []) or vector["id"] in isolated_ids, row["pointSelection"])
                        if row["pointSelection"]["nestedIsolationClicks"]:
                            save_render(editor, directory / "nested-point-selection-artwork.png")
                            row["pointSelection"]["nestedIsolationFidelity"] = compare_images(directory / "opened-artwork.png", directory / "nested-point-selection-artwork.png", directory / "nested-point-selection-difference.png")
                            check(case, "nested point isolation preserves source clip appearance", row["pointSelection"]["nestedIsolationFidelity"]["significantlyChangedPageFraction"] < .0001, row["pointSelection"]["nestedIsolationFidelity"])
                        if vector["id"] in isolated_ids and not direct.get("active"):
                            editor.evaluate("() => FigureStudio.app.setRailCollapsedForQa('right',false)")
                            nodes = editor.locator('[data-context-action="edit-path-nodes"]:visible').first
                            if not nodes.count() and editor.locator("#figure-more-properties").is_visible() and editor.locator("#figure-more-properties").get_attribute("aria-expanded") != "true":
                                editor.locator("#figure-more-properties").click()
                                editor.wait_for_timeout(250)
                                nodes = editor.locator('[data-context-action="edit-path-nodes"]:visible').first
                            row["pointSelection"]["nodesButton"] = {"count": nodes.count(), "enabled": nodes.is_enabled() if nodes.count() else False}
                            if nodes.count() and nodes.is_enabled():
                                nodes.click()
                                editor.wait_for_timeout(250)
                            direct = editor.evaluate("() => FigureStudio.app.getDirectSelectionStateForQa()")
                            row["pointSelection"]["nodeState"] = direct
                        row["pointSelection"]["selectionProtection"] = editor.evaluate("""id => {
                          const o=FigureStudio.app.getObjectByIdForQa(id),chain=[];
                          for(let p=o;p;p=p.group)chain.push({id:p.figureId,type:p.type,locked:Boolean(p.locked),visible:p.visible!==false,releasedForPathEditing:p.importMeta?.releasedForPathEditing,sourceId:p.pdfSourceId||p.importMeta?.sourceId||p.importMeta?.source_id||'',importMode:p.importMeta?.importMode||'',name:p.name||''});
                          return {chain,toast:document.querySelector('#toast')?.textContent||'',visibleActions:Array.from(document.querySelectorAll('[data-context-action]')).filter(el=>el.getClientRects().length).map(el=>({action:el.dataset.contextAction,disabled:el.disabled,text:el.textContent}))};
                        }""", vector["id"])
                        report["captures"].append({"path": str(directory / "point-selection-editor.png"), "purpose": "Imported path selected through Point Selection and the visible Edit nodes action; inspect whether actual anchors and selection are present."})
                        capture_editor(page, editor, directory / 'point-selection-editor.png')
                        check(case, "selected imported vector exposes actual editable anchors", vector["id"] in direct.get("objectIds", []) and direct.get("handleCount", 0) > 0, direct)
                        anchor = editor.locator(f'.path-node-handle[data-object-id="{vector["id"]}"][data-handle-type="endpoint"]').first
                        row["anchorDrag"] = {"status": "unavailable"}
                        if vector["id"] in direct.get("objectIds", []) and anchor.count() and anchor.is_visible():
                            phase(row, 'anchor-drag')
                            before_drag = next(v for v in editor.evaluate(INVENTORY_JS)["rows"] if v["id"] == vector["id"])
                            history_before_drag = editor.evaluate("() => FigureStudio.app.getHistoryStateForQa()")
                            geometry_before_drag = editor.evaluate(PATH_GEOMETRY_JS, vector['id'])
                            bounds = anchor.bounding_box()
                            start = {"x": bounds["x"] + bounds["width"] / 2, "y": bounds["y"] + bounds["height"] / 2}
                            page.mouse.move(start["x"], start["y"])
                            page.mouse.down()
                            page.mouse.move(start["x"] + 9, start["y"] + 6, steps=8)
                            page.mouse.up()
                            # Wait for this real point step, never the earlier
                            # marquee; Undo refuses input during history capture.
                            editor.wait_for_function("depth => FigureStudio.app.getHistoryStateForQa().undoDepth === depth + 1 && !FigureStudio.app.getBrowserSessionState().busy", arg=history_before_drag["undoDepth"], timeout=30000)
                            after_drag = next(v for v in editor.evaluate(INVENTORY_JS)["rows"] if v["id"] == vector["id"])
                            row["anchorDrag"] = {"status": "attempted", "before": before_drag, "after": after_drag, "clientStart": start, "historyBefore": history_before_drag, "historyAfter": editor.evaluate("() => FigureStudio.app.getHistoryStateForQa()")}
                            row['anchorDrag'].update({'geometryBefore': geometry_before_drag, 'geometryAfter': editor.evaluate(PATH_GEOMETRY_JS, vector['id'])})
                            check(case, "actual imported anchor drag changes vector geometry", before_drag["path"] != after_drag["path"], row["anchorDrag"])
                            geometry_after_drag = row['anchorDrag']['geometryAfter']
                            check(case, 'anchor drag updates live path dimensions and pathOffset to native geometry', abs(geometry_after_drag['width']-geometry_after_drag['nativeWidth']) < .0001 and abs(geometry_after_drag['height']-geometry_after_drag['nativeHeight']) < .0001 and equal_serialized_artwork(geometry_after_drag['pathOffset'],geometry_after_drag['nativePathOffset']), geometry_after_drag)
                            check(case, 'anchor drag preserves relative and ancestor clip world geometry', equal_serialized_artwork(geometry_before_drag['clips'],geometry_after_drag['clips']), {'before':geometry_before_drag['clips'],'after':geometry_after_drag['clips']})
                            editor.evaluate("() => FigureStudio.app.undoForQa()")
                            row["anchorDrag"]["historyAfterUndo"] = editor.evaluate("() => FigureStudio.app.getHistoryStateForQa()")
                            editor.wait_for_timeout(100)
                            restored = next(v for v in editor.evaluate(INVENTORY_JS)["rows"] if v["id"] == vector["id"])
                            check(case, "anchor drag has atomic geometry Undo", equal_serialized_artwork(before_drag, restored), restored)
                        else:
                            check(case, "actual imported anchor drag changes vector geometry", False, direct)
                        editor.evaluate("() => {FigureStudio.app.exitGroupIsolationForQa();FigureStudio.app.activateToolForQa('select');}")
                        phase(row, 'vector-inspector-edit')
                        row["vectorEdit"]["isolation"] = editor.evaluate("v => {FigureStudio.app.selectLayerTreeObjectForQa(v.id);return FigureStudio.app.getGroupIsolationStateForQa();}", vector)
                        editor.evaluate("() => FigureStudio.app.setRailCollapsedForQa('right',false)")
                        if editor.locator('[data-inspector-tab="properties"]').is_visible():
                            editor.locator('[data-inspector-tab="properties"]').click()
                        field = editor.locator('[data-context-property="stroke"]:visible').first
                        if field.count() == 0:
                            field = editor.locator("#strokeInput")
                        row["vectorEdit"]["historyBefore"] = editor.evaluate("() => FigureStudio.app.getHistoryStateForQa()")
                        vector = next(v for v in editor.evaluate(INVENTORY_JS)["rows"] if v["id"] == vector["id"])
                        field.evaluate("el => {el.value='#d51f72';el.dispatchEvent(new Event('change',{bubbles:true}));}")
                        editor.wait_for_function("depth => FigureStudio.app.getHistoryStateForQa().undoDepth === depth + 1 && !FigureStudio.app.getBrowserSessionState().busy", arg=row["vectorEdit"]["historyBefore"]["undoDepth"], timeout=30000)
                        row["vectorEdit"]["historyAfter"] = editor.evaluate("() => FigureStudio.app.getHistoryStateForQa()")
                        changed = editor.evaluate(INVENTORY_JS)
                        changed_vector = next((v for v in changed["rows"] if v["id"] == vector["id"]), None)
                        row["vectorEdit"].update({"status": "attempted", "before": vector, "after": changed_vector})
                        check(case, "group isolation edits an individual imported vector through Inspector", changed_vector is not None and changed_vector["stroke"].lower() == "#d51f72", row["vectorEdit"])
                        editor.evaluate("() => FigureStudio.app.undoForQa()")
                        row["vectorEdit"]["historyAfterUndo"] = editor.evaluate("() => FigureStudio.app.getHistoryStateForQa()")
                        undo_inventory = editor.evaluate(INVENTORY_JS)
                        row["vectorEdit"]["undoLeaf"] = next((v for v in undo_inventory["rows"] if v["id"] == vector["id"]), None)
                        check(case, "individual vector edit has atomic Undo", equal_serialized_artwork(row["vectorEdit"]["undoLeaf"], vector), row["vectorEdit"]["undoLeaf"])
                        editor.evaluate("() => FigureStudio.app.redoForQa()")
                        editor.evaluate("() => FigureStudio.app.exitGroupIsolationForQa()")
                    else:
                        check(case, "group isolation can target an imported editable path", False, counts)
                    text_inventory = editor.evaluate(INVENTORY_JS)
                    editable_texts = [v for v in text_inventory["rows"] if v["isText"] and not v["locked"] and v["visible"]]
                    text = next((v for v in editable_texts if len(v["text"].strip()) >= 6), next(iter(editable_texts), None))
                    row["textEdit"] = {"status": "unavailable"}
                    if text:
                        phase(row, 'text-keyboard-edit')
                        replacement = text["text"] + " β"
                        isolated = editor.evaluate("v => {FigureStudio.app.selectLayerTreeObjectForQa(v.id);return FigureStudio.app.getGroupIsolationStateForQa();}", text)
                        editor.evaluate("() => FigureStudio.app.setRailCollapsedForQa('right',false)")
                        more = editor.locator("#figure-more-properties")
                        if more.is_visible() and more.get_attribute("aria-expanded") == "true":
                            more.click()
                        editor.wait_for_timeout(250)
                        edit_button = editor.locator('[data-context-action="edit-text"]:visible').first
                        row['textEdit']['fontBefore'] = editor.evaluate(FONT_CONTEXT_JS, text['id'])
                        font_before = row['textEdit']['fontBefore']
                        check(case, 'imported text retains original font and explicit display-family metadata', bool(font_before['source'].get('originalFontName')) and bool(font_before['source'].get('displayFontFamily')) and isinstance(font_before['source'].get('sourceEmbeddedProgram'), bool), font_before)
                        if row['sourceInventory']['fonts'] and all(not f['embedded'] for f in row['sourceInventory']['fonts']):
                            check(case, 'nonembedded source font has an honest visible substitution note', font_before['source'].get('sourceEmbeddedProgram') is False and any(n['kind']=='unembedded' and 'did not embed' in n['text'] for n in font_before['visibleNotes']), font_before)
                        row['fontSizeEdit'] = {'status': 'unavailable', 'before': editor.evaluate(PHYSICAL_TEXT_SIZE_JS, text['id'])}
                        physical_before = row['fontSizeEdit']['before']
                        check(case, 'text Inspector shows physical point size under imported nested transforms', physical_before['visibleFieldPoints'] is not None and abs(physical_before['visibleFieldPoints']-physical_before['physicalPoints']) <= .11, physical_before)
                        size_field = editor.locator('[data-context-property="fontSize"]:visible,#fontSizeInput:visible').first
                        if size_field.count() and size_field.is_enabled():
                            phase(row, 'physical-font-size-edit')
                            before_size_leaf = next(v for v in editor.evaluate(INVENTORY_JS)['rows'] if v['id'] == text['id'])
                            # Reduce ordinary labels by1pt before adding beta so
                            # this authoring probe does not intentionally overflow
                            # the artboard with a long imported plot title.
                            desired_points = round(max(4, min(256, physical_before['physicalPoints']-1 if physical_before['physicalPoints'] > 4.1 else physical_before['physicalPoints']+1)), 1)
                            row['fontSizeEdit']['historyBefore'] = editor.evaluate('() => FigureStudio.app.getHistoryStateForQa()')
                            size_field.fill(str(desired_points))
                            size_field.press('Tab')
                            editor.wait_for_timeout(250)
                            row['fontSizeEdit'].update({'status': 'attempted', 'requestedPoints': desired_points, 'after': editor.evaluate(PHYSICAL_TEXT_SIZE_JS, text['id']), 'historyAfter': editor.evaluate('() => FigureStudio.app.getHistoryStateForQa()')})
                            check(case, 'actual Inspector text size edit applies physical points under imported transforms', abs(row['fontSizeEdit']['after']['physicalPoints']-desired_points) <= .01, row['fontSizeEdit'])
                            editor.evaluate('() => FigureStudio.app.undoForQa()')
                            restored_size_leaf = next(v for v in editor.evaluate(INVENTORY_JS)['rows'] if v['id'] == text['id'])
                            row['fontSizeEdit'].update({'afterUndo': editor.evaluate(PHYSICAL_TEXT_SIZE_JS, text['id']), 'historyAfterUndo': editor.evaluate('() => FigureStudio.app.getHistoryStateForQa()')})
                            check(case, 'physical text size edit has atomic font and geometry Undo', equal_serialized_artwork(before_size_leaf, restored_size_leaf), row['fontSizeEdit'])
                            editor.evaluate('() => FigureStudio.app.redoForQa()')
                            row['fontSizeEdit']['afterRedo'] = editor.evaluate(PHYSICAL_TEXT_SIZE_JS, text['id'])
                            check(case, 'physical text size edit Redo restores requested point size', abs(row['fontSizeEdit']['afterRedo']['physicalPoints']-desired_points) <= .01, row['fontSizeEdit']['afterRedo'])
                        else:
                            check(case, 'actual Inspector text size edit applies physical points under imported transforms', False, row['fontSizeEdit'])
                        row["textEdit"].update({"isolation": isolated, "buttonCount": edit_button.count(), "buttonEnabled": edit_button.is_enabled() if edit_button.count() else False})
                        if isolated.get("active") and edit_button.count() and edit_button.is_enabled():
                            edit_button.click()
                            editor.wait_for_timeout(100)
                            row["textEdit"]["editingState"] = editor.evaluate("id => {const o=FigureStudio.app.getObjectByIdForQa(id);return {isEditing:Boolean(o?.isEditing),activeElement:document.activeElement?.tagName,selectionStart:o?.selectionStart,selectionEnd:o?.selectionEnd};}", text["id"])
                            page.keyboard.press("Control+a")
                            page.keyboard.insert_text(replacement)
                            page.keyboard.press("Escape")
                            editor.wait_for_timeout(250)
                            updated = editor.evaluate(INVENTORY_JS)
                            updated_text = next((v for v in updated["rows"] if v["id"] == text["id"]), None)
                            row["textEdit"].update({"status": "attempted", "before": text, "after": updated_text, "sourceLayout": editor.evaluate("id => {const o=FigureStudio.app.getObjectByIdForQa(id);return {sourceText:o?.pdfTextSource?.text,sourceGlyphCount:o?.pdfTextSource?.glyphs?.length||0,originalPositionsActive:Boolean(o?._sourceLayout?.()),fontSubstitutions:o?.getFontSubstitutions?.()||[],isEditing:Boolean(o?.isEditing)};}", text["id"])})
                            row["textEdit"]["visibleFontContext"] = editor.evaluate("() => ({inspectorText:document.querySelector('#figureInspectorPanel')?.innerText||'',toast:document.querySelector('#toast')?.innerText||''})")
                            row['textEdit']['fontAfter'] = editor.evaluate(FONT_CONTEXT_JS, text['id'])
                            check(case, 'Unicode edit retains source font metadata without false subset-only copy', row['textEdit']['fontAfter']['source'] == font_before['source'] and all('only the original characters' not in n['text'] for n in row['textEdit']['fontAfter']['visibleNotes']), row['textEdit']['fontAfter'])
                            if font_before['source'].get('sourceEmbeddedProgram') is False:
                                check(case, 'full system font Unicode edit is not reported as a subset-glyph substitution', not row['textEdit']['fontAfter']['substitutions'], row['textEdit']['fontAfter'])
                            check(case, "actual imported text accepts Unicode keyboard editing on canvas", row["textEdit"]["editingState"]["isEditing"] and updated_text and updated_text["text"] == replacement and not row["textEdit"]["sourceLayout"]["originalPositionsActive"], row["textEdit"])
                            report["captures"].append({"path": str(directory / "text-edit-editor.png"), "purpose": "Imported editable label after actual keyboard typing, including beta; inspect visible text, glyph fallback, caret exit and the Figure interface."})
                            capture_editor(page, editor, directory / 'text-edit-editor.png')
                            editor.evaluate("() => FigureStudio.app.exitGroupIsolationForQa()")
                        else:
                            check(case, "actual imported text accepts Unicode keyboard editing on canvas", False, row["textEdit"])
                    elif expected["textShows"]:
                        check(case, "actual imported text accepts character editing", False, counts)
                    editor.evaluate("() => FigureStudio.app.clearSelectionForQa()")
                    phase(row, 'save-project')
                    row["editedInventory"] = editor.evaluate(INVENTORY_JS)
                    if vector:
                        row['editedPathGeometry'] = editor.evaluate(PATH_GEOMETRY_JS, vector['id'])
                    saved_artwork = json.loads(editor.evaluate("() => JSON.stringify(FigureStudio.app.buildProjectJsonForQa().fabric)"))
                    write_json(directory / "edited-complete-fabric.json", saved_artwork)
                    save_render(editor, directory / "edited-artwork.png")
                    project = directory / "edited.fsfigure"
                    with page.expect_download(timeout=30000) as download:
                        editor.locator("body").press("Control+s")
                    download.value.save_as(str(project))
                    project_text = project.read_text(encoding='utf-8')
                    payload = json.loads(project_text)
                    runtime_tokens = ('figureStudio.runtimePdfHistory','$figureStudioPdfHistoryNode')
                    check(case, 'actual downloaded Figure contains no runtime-only PDF history references', not any(token in project_text for token in runtime_tokens), {'runtimeTokensFound':[token for token in runtime_tokens if token in project_text]})
                    sources_saved = embedded_sources(payload)
                    row["savedSource"] = {"embeddedCount": len(sources_saved), "sourceSha256": [sha(data) for data in sources_saved], "allOriginalBytesRetained": original in sources_saved}
                    check(case, "actual saved Figure retains all original PDF bytes", original in sources_saved, row["savedSource"])
                    row['browserSaveOriginal'] = page.evaluate(BROWSER_SAVE_STATE_JS)
                    phase(row, 'fresh-process-cold-open' if not args.engine_diagnostic else 'same-process-cold-open-diagnostic')
                    context.close()
                    if not args.engine_diagnostic:
                        browser.close()
                        browser = pw.chromium.launch(**browser_launch_options)
                        record_browser_runtime(browser, 'fresh-process-cold-open')
                    context = browser.new_context(**context_options)
                    context.add_init_script("try{delete window.showSaveFilePicker;delete window.showOpenFilePicker;}catch(_){}")
                    cold = context.new_page()
                    page = cold  # Error captures and final observations own the live surface.
                    cold.on("pageerror", lambda error: report["pageErrors"].append({"case": case, "phase": "cold-open", "message": str(error), "stack": getattr(error, "stack", "")}))
                    cold.on("console", lambda message: report["consoleErrors"].append({"case": case, "phase": "cold-open", "message": message.text}) if message.type == "error" else None)
                    cold.on("response", lambda response: report["httpErrors"].append({"case": case, "phase": "cold-open", "url": response.url, "status": response.status}) if response.status >= 400 else None)
                    cold.on("request", lambda request: report["externalRequests"].append(request.url) if request.url.startswith("http") and not request.url.startswith(base) else None)
                    cold.on("dialog", lambda dialog: dialog.accept(dialog.default_value or case + ".fsfigure"))
                    editor = ready(cold)
                    with cold.expect_file_chooser() as chooser:
                        editor.locator("body").press("Control+o")
                    chooser.value.set_files(str(project))
                    editor.wait_for_function("document.querySelector('#documentFileOperationStatus')?.dataset.state === 'success'", timeout=30000)
                    editor.wait_for_function('!FigureStudio.app.getBrowserSessionState().busy', timeout=30000)
                    editor.evaluate("() => FigureStudio.app.clearSelectionForQa()")
                    editor.wait_for_timeout(100)
                    row["coldInventory"] = editor.evaluate(INVENTORY_JS)
                    if vector:
                        row['coldPathGeometry'] = editor.evaluate(PATH_GEOMETRY_JS, vector['id'])
                        check(case, 'cold Open retains edited path dimensions, pathOffset and world clips', equal_serialized_artwork(row['editedPathGeometry'],row['coldPathGeometry']), {'before':row['editedPathGeometry'],'after':row['coldPathGeometry']})
                    row['physicalPageGeometry']['coldScene'] = editor.evaluate('() => FigureStudio.app.getViewportStateForQa().artboard')
                    row['physicalPageGeometry']['savedDefaultArtboard'] = payload.get('project',payload).get('document',{}).get('pageGeometry',{}).get('defaultArtboard',{})
                    cold_art = row['physicalPageGeometry']['coldScene']
                    check(case, 'cold Open preserves exact logical PDF point dimensions', all(abs(cold_art[k]-v) < .0001 for k,v in zip(('width','height'),row['physicalPageGeometry']['expectedScenePixels'])), row['physicalPageGeometry'])
                    cold_artwork = json.loads(editor.evaluate("() => JSON.stringify(FigureStudio.app.buildProjectJsonForQa().fabric)"))
                    cold_export_text = json.dumps(cold_artwork,ensure_ascii=False)
                    check(case, 'cold-saved artwork contains no runtime-only PDF history references', not any(token in cold_export_text for token in runtime_tokens), {'runtimeTokensFound':[token for token in runtime_tokens if token in cold_export_text]})
                    write_json(directory / "cold-complete-fabric.json", cold_artwork)
                    check(case, "complete serialized editable artwork survives actual fresh Open", equal_serialized_artwork(artwork_without_session_isolation(saved_artwork), artwork_without_session_isolation(cold_artwork)), {"beforeJsonSha256": sha(json.dumps(saved_artwork, sort_keys=True).encode()), "afterJsonSha256": sha(json.dumps(cold_artwork, sort_keys=True).encode()), "comparison": "All Fabric objects, paths, custom glyph positioning, clip data, nested styles, source metadata and images; geometry tolerance 0.0001. Only transient figureStudioIsolationMeta selection-cache field excluded; raw complete snapshots retained."})
                    check(case, "saved editable hierarchy and every leaf property survive fresh Open", equal_serialized_artwork(row["coldInventory"], row["editedInventory"]), {"beforeCounts": row["editedInventory"]["counts"], "afterCounts": row["coldInventory"]["counts"], "beforeRows": row["editedInventory"]["rows"], "afterRows": row["coldInventory"]["rows"]})
                    save_render(editor, directory / "cold-artwork.png")
                    report["captures"].append({"path": str(directory / "cold-editor.png"), "purpose": "Fresh browser Open of the actual saved Figure file; inspect complete edited content, beta glyph, clipping and source hierarchy in the live editor."})
                    cold.wait_for_function("document.querySelector('#browser-save-status')?.dataset.state !== 'loading'", timeout=10000)
                    row['browserSaveState'] = cold.evaluate(BROWSER_SAVE_STATE_JS)
                    check(case, 'actual browser save does not show a persistent failure after cold Open', row['browserSaveState']['state'] not in ('error','conflict','startup-error'), row['browserSaveState'])
                    capture_editor(cold, editor, directory / 'cold-editor.png')
                    if row.get('textEdit',{}).get('status') == 'attempted':
                        editor.evaluate('id => FigureStudio.app.selectLayerTreeObjectForQa(id)', row['textEdit']['after']['id'])
                        editor.evaluate("() => FigureStudio.app.setRailCollapsedForQa('right',false)")
                        more = editor.locator('#figure-more-properties')
                        if more.is_visible() and more.get_attribute('aria-expanded') == 'true':
                            more.click()
                        editor.wait_for_timeout(250)
                        if row.get('fontSizeEdit', {}).get('status') == 'attempted':
                            row['fontSizeEdit']['cold'] = editor.evaluate(PHYSICAL_TEXT_SIZE_JS, row['textEdit']['after']['id'])
                            check(case, 'cold Open retains edited physical text size and honest Inspector value', abs(row['fontSizeEdit']['cold']['physicalPoints']-row['fontSizeEdit']['requestedPoints']) <= .01 and row['fontSizeEdit']['cold']['visibleFieldPoints'] is not None and abs(row['fontSizeEdit']['cold']['visibleFieldPoints']-row['fontSizeEdit']['cold']['physicalPoints']) <= .11, row['fontSizeEdit']['cold'])
                        row['textEdit']['fontCold'] = editor.evaluate(FONT_CONTEXT_JS, row['textEdit']['after']['id'])
                        row['browserSaveState'] = cold.evaluate(BROWSER_SAVE_STATE_JS)
                        check(case, 'cold Open preserves original font metadata and honest Unicode font note', row['textEdit']['fontCold']['source'] == row['textEdit']['fontAfter']['source'] and row['textEdit']['fontCold']['visibleNotes'] == row['textEdit']['fontAfter']['visibleNotes'], row['textEdit']['fontCold'])
                        report['captures'].append({'path': str(directory / 'cold-font-note-editor.png'), 'purpose': 'Actual cold-open text selection shows retained original font and truthful substituted-family information after the Unicode edit.'})
                        capture_editor(cold, editor, directory / 'cold-font-note-editor.png')
                        editor.evaluate('() => {FigureStudio.app.exitGroupIsolationForQa();FigureStudio.app.clearSelectionForQa();}')
                    row["coldFidelity"] = compare_images(directory / "edited-artwork.png", directory / "cold-artwork.png", directory / "cold-difference.png")
                    row["coldNativeTextPaint"] = editor.evaluate("() => globalThis.FigureStudioPdfiumTextRasterizer?.diagnostics() || null")
                    check(case, "actual saved-file cold Open paints the same edited artwork", row["coldFidelity"]["significantlyChangedPageFraction"] < .0001, row["coldFidelity"])
                    phase(row, 'actual-cold-edited-pdf-export')
                    data, exported = export_pdf(cold, editor, directory / 'edited-cold-export.pdf')
                    render_pdf(data, directory / "edited-cold-export-pdfium.png")
                    row["editedColdExport"] = {"sha256": sha(data), "inventory": pdf_inventory(data), "metadata": exported}
                    row["editedExportFidelity"] = compare_images(directory / "cold-artwork.png", directory / "edited-cold-export-pdfium.png", directory / "edited-cold-export-difference.png")
                    check(case, "edited PDF export agrees with reopened editable artwork", row["editedExportFidelity"]["blurredMeanAbsoluteError"] <= .01 and row["editedExportFidelity"]["significantlyChangedPageFraction"] <= .025, row["editedExportFidelity"])
                    if args.continue_after_cold:
                        phase(row, 'continued-cold-keyboard-edit')
                        if row.get('textEdit', {}).get('status') != 'attempted':
                            raise RuntimeError('Continued cold qualification requires the actual earlier editable label.')
                        text_id = row['textEdit']['after']['id']
                        before_continue = next(v for v in editor.evaluate(INVENTORY_JS)['rows'] if v['id'] == text_id)
                        editor.evaluate('id => FigureStudio.app.selectLayerTreeObjectForQa(id)', text_id)
                        editor.evaluate("() => FigureStudio.app.setRailCollapsedForQa('right', false)")
                        more = editor.locator('#figure-more-properties')
                        if more.is_visible() and more.get_attribute('aria-expanded') == 'true':
                            more.click()
                        editor.locator('[data-context-action="edit-text"]:visible').first.click()
                        cold.keyboard.press('Control+End')
                        cursor_js = """id => {const o=FigureStudio.app.getObjectByIdForQa(id);return {text:o?.text,isEditing:o?.isEditing,selectionStart:o?.selectionStart,selectionEnd:o?.selectionEnd};}"""
                        at_end = editor.evaluate(cursor_js, text_id)
                        cold.keyboard.press('Shift+ArrowLeft')
                        selected_character = editor.evaluate(cursor_js, text_id)
                        check(case, 'fresh Open text supports real caret movement and character selection',
                              at_end['isEditing'] and at_end['selectionStart'] == at_end['selectionEnd'] == len(before_continue['text'])
                              and selected_character['selectionStart'] == len(before_continue['text']) - 1
                              and selected_character['selectionEnd'] == len(before_continue['text']),
                              {'atEnd': at_end, 'selectedCharacter': selected_character})
                        report['captures'].append({'path': str(directory / 'continued-selection-editor.png'), 'purpose': 'Fresh-process continued text editing with one actual character selected; inspect the live selection and unchanged scientific page.'})
                        capture_editor(cold, editor, directory / 'continued-selection-editor.png')
                        cold.keyboard.press('ArrowRight')
                        continued_history = editor.evaluate('() => FigureStudio.app.getHistoryStateForQa()')
                        cold.keyboard.insert_text(' A')
                        after_input = editor.evaluate(cursor_js, text_id)
                        cold.keyboard.press('Escape')
                        editor.wait_for_function('depth => FigureStudio.app.getHistoryStateForQa().undoDepth === depth + 1 && !FigureStudio.app.getBrowserSessionState().busy', arg=continued_history['undoDepth'], timeout=30000)
                        continued_text = before_continue['text'] + ' A'
                        check(case, 'fresh Open label accepts continued keyboard text at the actual caret', after_input['text'] == continued_text and after_input['selectionStart'] == after_input['selectionEnd'] == len(continued_text), after_input)
                        editor.evaluate('() => FigureStudio.app.undoForQa()')
                        after_undo = next(v for v in editor.evaluate(INVENTORY_JS)['rows'] if v['id'] == text_id)
                        check(case, 'continued cold text edit has atomic Undo', equal_serialized_artwork(after_undo, before_continue), after_undo)
                        editor.evaluate('() => FigureStudio.app.redoForQa()')
                        after_redo = next(v for v in editor.evaluate(INVENTORY_JS)['rows'] if v['id'] == text_id)
                        check(case, 'continued cold text Redo restores the authored label', after_redo['text'] == continued_text, after_redo)
                        editor.evaluate('() => {FigureStudio.app.exitGroupIsolationForQa();FigureStudio.app.clearSelectionForQa();}')
                        continued_artwork = json.loads(editor.evaluate('() => JSON.stringify(FigureStudio.app.buildProjectJsonForQa().fabric)'))
                        write_json(directory / 'continued-complete-fabric.json', continued_artwork)
                        save_render(editor, directory / 'continued-artwork.png')
                        with cold.expect_download(timeout=30000) as second_download:
                            editor.locator('body').press('Control+s')
                        second_file = directory / 'continued.fsfigure'
                        second_download.value.save_as(str(second_file))
                        second_text = second_file.read_text(encoding='utf-8')
                        second_payload = json.loads(second_text)
                        second_artwork = second_payload.get('project', second_payload).get('fabric')
                        saved_target_text = []
                        pending_objects = [second_artwork]
                        while pending_objects:
                            saved_object = pending_objects.pop()
                            if not isinstance(saved_object, dict):
                                continue
                            if saved_object.get('figureId') == text_id:
                                saved_target_text.append(saved_object.get('text'))
                            pending_objects.extend(saved_object.get('objects', []))
                        check(case, 'second actual Save contains the complete continued artwork and authored text',
                              second_artwork is not None and equal_serialized_artwork(second_artwork, continued_artwork)
                              and saved_target_text == [continued_text],
                              {'completeArtworkEqual': equal_serialized_artwork(second_artwork, continued_artwork), 'savedTargetText': saved_target_text, 'expectedText': continued_text})
                        second_sources = embedded_sources(second_payload)
                        check(case, 'second actual Save retains original PDF bytes and no runtime history tokens', original in second_sources and not any(token in second_text for token in runtime_tokens), {'file': str(second_file), 'sha256': sha(second_file.read_bytes()), 'sourceSha256': [sha(value) for value in second_sources]})
                        row['continuedColdEdit'] = {'before': before_continue, 'afterInput': after_input, 'afterUndo': after_undo, 'afterRedo': after_redo, 'savedFile': str(second_file), 'savedSha256': sha(second_file.read_bytes())}
                        phase(row, 'continued-final-pdf-export')
                        final_data, final_export = export_pdf(cold, editor, directory / 'continued-export.pdf')
                        render_pdf(final_data, directory / 'continued-export-pdfium.png')
                        row['continuedColdEdit']['export'] = {'sha256': sha(final_data), 'metadata': final_export, 'inventory': pdf_inventory(final_data)}
                        row['continuedColdEdit']['exportFidelity'] = compare_images(directory / 'continued-artwork.png', directory / 'continued-export-pdfium.png', directory / 'continued-export-difference.png')
                        final_fidelity = row['continuedColdEdit']['exportFidelity']
                        check(case, 'continued final PDF export preserves the current editable artwork', final_fidelity['blurredMeanAbsoluteError'] <= .01 and final_fidelity['significantlyChangedPageFraction'] <= .025, final_fidelity)
                    row["performanceAudit"] = editor.evaluate("() => FigureStudio.app.getCanvasInteractionPerformanceForQa()")
                    row["harnessCompleted"] = True
                except Exception as error:
                    row["harnessError"] = str(error)
                    row["traceback"] = traceback.format_exc()
                    check(case, "browser qualification journey completed", False, str(error))
                    try:
                        page.screenshot(path=str(directory / "harness-failure.png"), timeout=5000)
                    except Exception as capture_error:
                        row['failureCaptureError'] = str(capture_error)
                finally:
                    try:
                        row['browserSaveProbeAtClose'] = page.evaluate(BROWSER_SAVE_STATE_JS)
                    except Exception as probe_error:
                        row['browserSaveProbeCloseError'] = str(probe_error)
                    context.close()
                    row["sourceSha256After"] = sha(source["path"].read_bytes())
                    check(case, "scientific source bytes remain unchanged", row["sourceSha256After"] == row["sha256"], {"before": row["sha256"], "after": row["sourceSha256After"]})
                    write_json(directory / "case-report.json", row)
            browser.close()
        expected_http = [r for r in report["httpErrors"] if r["status"] == 501 and "/api/pdf-native-ir-shadow?" in r["url"]]
        unexpected_http = [r for r in report["httpErrors"] if r not in expected_http]
        report["expectedUnavailableStaticNativeProbes"] = expected_http
        check("corpus", "zero browser script errors", not report["pageErrors"], report["pageErrors"])
        check("corpus", "zero browser console errors", not report["consoleErrors"], report["consoleErrors"])
        check("corpus", "only classified unavailable static native service HTTP failures", not unexpected_http, unexpected_http)
        check("corpus", "no external requests", not report["externalRequests"], report["externalRequests"])
        report["sourceHashesAfter"] = source_binding()
        report["sourceStable"] = report["sourceHashesBefore"] == report["sourceHashesAfter"]
        report["acceptanceFailureCount"] = sum(not c["passed"] for c in report["checks"])
        complete = all(r["harnessCompleted"] for r in report["cases"])
        if not complete:
            report["status"] = "HARNESS_ERROR"
        elif not report["sourceStable"]:
            report["status"] = "DIAGNOSTIC_SOURCE_CHANGED"
        elif report["acceptanceFailureCount"]:
            report["status"] = "BASELINE_COMPLETE_WITH_ACCEPTANCE_FAILURES" if args.baseline else "HOLD"
        else:
            report["status"] = "STRUCTURAL_PASS_VISUAL_REVIEW_REQUIRED"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
        report["ownedServerClosed"] = not thread.is_alive()
        write_json(output / "report.json", report)
        print(json.dumps({"output": str(output), "status": report["status"], "acceptanceFailures": report.get("acceptanceFailureCount"), "harnessCompletedCases": sum(r["harnessCompleted"] for r in report["cases"])}), flush=True)
    return 0 if report["status"] == "STRUCTURAL_PASS_VISUAL_REVIEW_REQUIRED" or (args.baseline and all(r["harnessCompleted"] for r in report["cases"])) else 1


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    raise SystemExit(main())
