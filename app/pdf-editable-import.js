(function attachPdfEditableImport(root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  if (root) root.FigureStudioPdfEditableImport = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function createPdfEditableImport() {
  "use strict";

  const SCHEMA = "figureStudio.pdfEditableImport.v1";
  const textSpacing = typeof module === "object" && module.exports
    ? require("./pdf-text-spacing.js") : globalThis.FigureStudioPdfTextSpacing;
  // This is a dedicated object reconstruction budget, not the SVG proxy cutoff.
  // Every accepted paint operation is retained; complexity is never reduced by
  // rasterizing a page and reporting it as editable.
  const DEFAULT_BUDGETS = Object.freeze({ sourceBytes: 32 * 1024 * 1024, operators: 250000, objects: 50000 });
  const IMPLEMENTED_OPERATORS = new Set([
    "dependency", "save", "restore", "transform", "beginText", "endText",
    "setLeading", "setLeadingMoveText", "setFont", "showText", "showSpacedText",
    "moveText", "setCharSpacing", "setWordSpacing", "setHScale", "setTextMatrix",
    "setTextRise", "setTextRenderingMode", "nextLine", "setLineWidth", "setLineJoin",
    "setLineCap", "setMiterLimit", "setFillRGBColor", "setStrokeRGBColor", "setStrokeColorN",
    "setFillColorN", "shadingFill", "setDash", "setRenderingIntent", "setFlatness", "setGState",
    "fill", "eoFill", "stroke", "fillStroke", "eoFillStroke", "clip", "eoClip",
    "paintSolidColorImageMask", "paintImageXObject", "paintInlineImageXObject",
    "paintFormXObjectBegin", "paintFormXObjectEnd", "closePath", "closeStroke",
    "closeFillStroke", "closeEOFillStroke", "constructPath", "endPath",
    "beginMarkedContent", "beginMarkedContentProps", "endMarkedContent", "markPoint", "markPointProps", "beginGroup", "endGroup"
  ]);
  const GSTATE_KEYS = new Set(["LW", "LC", "LJ", "ML", "D", "RI", "FL", "Font", "CA", "ca"]);
  const PAINT_OPERATORS = new Set(["fill", "eoFill", "stroke", "fillStroke", "eoFillStroke", "closeStroke", "closeFillStroke", "closeEOFillStroke", "showText", "showSpacedText", "paintSolidColorImageMask", "paintImageXObject", "paintInlineImageXObject", "shadingFill"]);
  const registeredFonts = new WeakMap();
  const knockoutAuthorities = new WeakMap();
  const knockoutSourceMaps = new WeakSet();
  const importerScriptUrl = typeof document !== "undefined" ? document.currentScript?.src : "";
  const knockoutApi = () => typeof module === "object" && module.exports ? require("./pdf-knockout.js") : globalThis.FigureStudioPdfKnockout;
  const knockoutProofApi = () => typeof module === "object" && module.exports ? require("./pdf-knockout-proof.js") : globalThis.FigureStudioPdfKnockoutProof;

  function freezeTree(value) {
    if (value && typeof value === "object" && !Object.isFrozen(value)) {
      Object.values(value).forEach(freezeTree);
      Object.freeze(value);
    }
    return value;
  }

  function scopeSignature(operatorList, start, end) {
    return JSON.stringify([operatorList.fnArray.slice(start, end + 1), operatorList.argsArray.slice(start, end + 1)]);
  }

  async function captureKnockoutOperators(operatorList, OPS, { signal, onProgress } = {}) {
    const names = new Map(Object.entries(OPS).map(([name, id]) => [id, name]));
    const fnArray = operatorList.fnArray.slice(), argsArray = new Array(fnArray.length);
    const pathPaints = new Set(["fill", "eoFill", "stroke", "fillStroke", "eoFillStroke", "closeStroke", "closeFillStroke", "closeEOFillStroke"]);
    for (let start = 0; start < fnArray.length; start += 2048) {
      if (signal?.aborted) { const error = new Error("Knockout source proof was cancelled."); error.name = "AbortError"; throw error; }
      const end = Math.min(start + 2048, fnArray.length);
      for (let index = start; index < end; index++) {
        const name = names.get(fnArray[index]);
        // The bounded native K compiler permits only path paints. Glyph and
        // image payloads outside such scopes do not affect its state proof;
        // leave those large payloads owned by the original renderer/inventory.
        argsArray[index] = !PAINT_OPERATORS.has(name) || pathPaints.has(name) ? structuredClone(operatorList.argsArray[index]) : null;
      }
      onProgress?.({ phase: "operator-proof-snapshot", visitedOperators: end, totalOperators: fnArray.length });
      if (end < fnArray.length) await new Promise(resolve => setTimeout(resolve, 0));
    }
    return { fnArray, argsArray };
  }

  function knockoutContext(operatorList, OPS, groups) {
    const names = new Map(Object.entries(OPS).map(([name, id]) => [id, name]));
    const wantedClips = new Set(groups.flatMap(group => group.ancestorClips.filter(clip => clip.kind === "source-path").map(clip => clip.clipOperatorIndex)));
    const clipPaths = new Map(), stateIndexes = [], argumentSignatures = new Map(), dependencies = new Map();
    const lastStart = Math.max(-1, ...groups.map(group => group.scopeStart));
    const fnArray = operatorList.fnArray.slice(0, lastStart);
    const pathPaints = new Set(["fill", "eoFill", "stroke", "fillStroke", "eoFillStroke", "closeStroke", "closeFillStroke", "closeEOFillStroke"]);
    let pathIndexes = [];
    for (let index = 0; index < lastStart; index++) {
      const name = names.get(operatorList.fnArray[index]);
      if (name === "constructPath") pathIndexes.push(index);
      else if (!PAINT_OPERATORS.has(name) && name !== "dependency") stateIndexes.push(index);
      if (wantedClips.has(index)) clipPaths.set(index, pathIndexes.slice());
      // PDF paths can span several constructPath calls. Save/restore does not
      // clear the current path, and text/image paints do not consume it.
      if (name === "endPath" || pathPaints.has(name)) pathIndexes = [];
    }
    for (const group of groups) {
      const indexes = new Set(stateIndexes.filter(index => index < group.scopeStart));
      for (const clip of group.ancestorClips) if (clip.kind === "source-path") {
        const contributors = clipPaths.get(clip.clipOperatorIndex);
        if (!contributors?.length || !contributors.includes(clip.pathOperatorIndex)) throw new Error("Knockout ancestor clip lost its original path construction.");
        contributors.forEach(index => indexes.add(index));
      }
      dependencies.set(group.scopeStart, [...indexes]);
      for (const index of indexes) if (!argumentSignatures.has(index)) argumentSignatures.set(index, JSON.stringify(operatorList.argsArray[index]));
    }
    return { fnArray, dependencies, argumentSignatures };
  }

  function boundKnockoutScope(operatorList, index, binding, OPS) {
    const authority = binding && knockoutAuthorities.get(binding);
    if (authority?.operatorList !== operatorList || OPS && authority.OPS !== OPS) return null;
    const bound = authority.byStart.get(index);
    if (!bound) return null;
    for (let prefix = 0; prefix < index; prefix++) if (operatorList.fnArray[prefix] !== authority.context.fnArray[prefix]) return null;
    for (const dependency of authority.context.dependencies.get(index)) if (JSON.stringify(operatorList.argsArray[dependency]) !== authority.context.argumentSignatures.get(dependency)) return null;
    return authority.signatures.get(index) === scopeSignature(operatorList, bound.scopeStart, bound.scopeEnd) ? bound : null;
  }

  async function prepareKnockoutScopes({ operatorList, OPS, bytes, pageNumber = 1, budgets = DEFAULT_BUDGETS, sourceId, signal, onProgress, workerUrl, readSource } = {}) {
    const initial = inventoryOperators(operatorList, OPS, budgets);
    const starts = operatorList.fnArray.flatMap((id, index) => id === OPS.beginGroup && operatorList.argsArray[index]?.[0]?.knockout ? [index] : []);
    // Ordinary PDFs never parse native source dictionaries or start this worker.
    if (!starts.length || initial.unsupported.some(reason => reason !== "transparency-group-knockout")) return { inventory: initial, binding: null, sourceId };
    const proofApi = knockoutProofApi();
    if (!proofApi || !knockoutApi()) throw new Error("The portable knockout proof and compositor are unavailable.");
    sourceId ||= await proofApi.sourceDigest(bytes);
    const url = workerUrl || (importerScriptUrl ? new URL("pdf-knockout-proof-worker.js", importerScriptUrl).href : "");
    const proof = readSource ? await readSource(new Uint8Array(bytes).slice(), { sourceSha256: sourceId, signal, onProgress })
      : await proofApi.readSourceGroupsInWorker(bytes, { workerUrl: url, sourceSha256: sourceId, signal, onProgress });
    const proofOperators = await captureKnockoutOperators(operatorList, OPS, { signal, onProgress });
    const binding = await proofApi.bindOperatorScopesAsync(proof, { operatorList: proofOperators, OPS, pageNumber, sourceSha256: sourceId, onProgress });
    const byStart = new Map(binding.groups.map(group => [group.scopeStart, freezeTree(JSON.parse(JSON.stringify(group)))]));
    const signatures = new Map([...byStart.values()].map(group => [group.scopeStart, scopeSignature(proofOperators, group.scopeStart, group.scopeEnd)]));
    const context = knockoutContext(proofOperators, OPS, [...byStart.values()]);
    knockoutAuthorities.set(binding, { operatorList, OPS, byStart, signatures, context, pageNumber });
    return { inventory: inventoryOperators(operatorList, OPS, budgets, binding), binding, sourceId };
  }

  function createKnockoutSources(operatorList, binding, viewport, pageNumber) {
    const authority = binding && knockoutAuthorities.get(binding);
    if (!authority || authority.operatorList !== operatorList) throw new Error("Knockout source map lacks current operator ownership.");
    if (pageNumber !== authority.pageNumber) throw new Error("Knockout source map belongs to another source page.");
    for (const start of authority.byStart.keys()) if (!boundKnockoutScope(operatorList, start, binding, authority.OPS)) throw new Error("Knockout source operators changed after their exact proof.");
    const entries = [...authority.byStart.values()].map(bound => freezeTree({
      key: `${bound.sourceSha256}_p${pageNumber}_op${bound.scopeStart}`,
      schema: bound.schema, sourceId: bound.sourceId, sourceSha256: bound.sourceSha256, pageNumber,
      scopeStart: bound.scopeStart, scopeEnd: bound.scopeEnd, ancestorTransform: [...bound.ancestorTransform],
      source: { ...bound.source, pageNumber, scopeStart: bound.scopeStart, scopeEnd: bound.scopeEnd, width: viewport.width, height: viewport.height,
        sourceToViewport: knockoutApi().matrix(viewport.transform, bound.ancestorTransform) }
    }));
    Object.freeze(entries);
    knockoutSourceMaps.add(entries);
    return entries;
  }

  function isTrustedKnockoutSources(entries) { return knockoutSourceMaps.has(entries); }

  function canonicalSvgObjectCount(svg, knockoutSources = []) {
    if (!knockoutSources.length) return svg.querySelectorAll("path,rect,circle,ellipse,line,polyline,polygon,image,text").length;
    const drawables = Array.from(svg.querySelectorAll("path,rect,circle,ellipse,line,polyline,polygon,image,text"));
    return drawables.filter(element => !element.closest?.('[data-pdf-knockout-import-key]')).length + knockoutSources.length * 2;
  }

  function inventoryOperators(operatorList, OPS, budgets = DEFAULT_BUDGETS, knockoutBinding = null) {
    const names = new Map(Object.entries(OPS || {}).map(([name, id]) => [id, name]));
    const counts = {};
    const unsupported = new Set();
    const featureStates = [];
    let objects = 0;
    let depth = 0;
    const state = [];
    let currentFont = "";
    for (let index = 0; index < (operatorList.fnArray || []).length; index += 1) {
      const name = names.get(operatorList.fnArray[index]) || `unknown-${operatorList.fnArray[index]}`;
      const args = operatorList.argsArray[index] || [];
      counts[name] = (counts[name] || 0) + 1;
      if (!IMPLEMENTED_OPERATORS.has(name)) unsupported.add(name);
      if (PAINT_OPERATORS.has(name)) objects += 1;
      if (name === "save") { depth += 1; state.push(currentFont); }
      if (name === "restore") { depth -= 1; currentFont = state.pop() || ""; }
      if (depth < 0) unsupported.add("unbalanced-graphics-state");
      if (name === "setFont") currentFont = args[0];
      if (name === "setGState") {
        for (const [key, value] of args[0] || []) {
          if (["BM", "SMask"].includes(key)) featureStates.push({ key, value });
          if (!GSTATE_KEYS.has(key) && !(key === "BM" && value === "source-over") && !(key === "SMask" && value === false)) unsupported.add(`graphics-state:${key}`);
          if (key === "Font") currentFont = value[0];
        }
      }
      if (name === "beginGroup") {
        featureStates.push({ key: "group", value: args[0] });
        if (args[0]?.smask) unsupported.add("transparency-group-soft-mask");
        if (args[0]?.knockout && !boundKnockoutScope(operatorList, index, knockoutBinding, OPS)) unsupported.add("transparency-group-knockout");
      }
      if ((name === "showText" || name === "showSpacedText") && !currentFont) unsupported.add("text-without-font");
      if (name === "setTextRenderingMode" && Number(args[0]) >= 4) unsupported.add("text-clipping-path");
    }
    if (depth !== 0) unsupported.add("unbalanced-graphics-state");
    const limits = { ...DEFAULT_BUDGETS, ...budgets };
    if ((operatorList.fnArray || []).length > limits.operators) unsupported.add("operator-budget-exceeded");
    if (objects > limits.objects) unsupported.add("editable-object-budget-exceeded");
    return { operatorCount: (operatorList.fnArray || []).length, estimatedObjectCount: objects, counts, unsupported: [...unsupported].sort(), featureStates, budgets: limits };
  }

  function toBase64(bytes) {
    if (typeof Buffer === "function") return Buffer.from(bytes).toString("base64");
    let binary = "";
    for (let index = 0; index < bytes.length; index += 16384) binary += String.fromCharCode(...bytes.subarray(index, index + 16384));
    return btoa(binary);
  }

  function fontProgram(font) {
    const data = font?.data;
    if (!data?.length || font.missingFile) return null;
    return {
      family: font.loadedName,
      originalName: font.name || font.loadedName,
      mimetype: font.mimetype || "font/opentype",
      dataUrl: `data:${font.mimetype || "font/opentype"};base64,${toBase64(data)}`,
      // PDF.js repairs and remaps subset programs for browser rendering. These
      // bytes are explicitly a display font, never native source-write authority.
      representation: "pdfjs-browser-display-font",
      fontCharToUnicode: {},
      unicodeToFontChar: {},
      weight: "normal",
      style: "normal"
    };
  }

  function recoverableGlyphs(glyphs) {
    return (glyphs || []).filter((glyph) => glyph && typeof glyph === "object").map((glyph) => ({
      unicode: String(glyph.unicode || ""),
      fontChar: String(glyph.fontChar || ""),
      width: Number(glyph.width) || 0,
      isInFont: glyph.isInFont !== false,
      ...(glyph.zeroInk ? { zeroInk: true, spacingSource: glyph.spacingSource, sourceAdjustment: glyph.sourceAdjustment } : {})
    }));
  }

  function rendererClass(pdfjs, logicalOptions = {}) {
    const EditableSvgGraphics = class EditableSvgGraphics extends pdfjs.SVGGraphics {
      constructor(commonObjs, objs) {
        super(commonObjs, objs, true);
        this.embedFonts = true;
        this.programs = new Map();
        this.runGlyphs = new WeakMap();
        this.scopeSerial = 0;
        this.scopeRoots = [];
        this.recoveryWarnings = new Set();
        this.wordSpacingRecovery = [];
        this.transparencyScopes = [];
      }
      _initialize(viewport) {
        const svg = super._initialize(viewport);
        this.svg.setAttribute("transform", `matrix(${viewport.transform.join(" ")})`);
        return svg;
      }
      _ensureTransformGroup() {
        const group = super._ensureTransformGroup();
        // The retired backend's angle formatter uses acos and loses the sign
        // of some negative rotations. Keep the full affine matrix instead.
        group.setAttribute("transform", `matrix(${this.transformMatrix.join(" ")})`);
        return group;
      }
      endPath() {
        const element = this.current.element;
        const clipped = Boolean(this.pendingClip && element);
        const unpainted = element && element.getAttribute("fill") === "none" && !element.getAttribute("stroke");
        super.endPath();
        if (clipped && this.defs.lastElementChild?.localName?.toLowerCase() === "clippath") this.defs.lastElementChild.setAttribute("transform", `matrix(${this.transformMatrix.join(" ")})`);
        // SVGGraphics leaves the path used by `W n` in the painted tree. The
        // cloned clip definition owns that geometry; the abandoned construction
        // path is not a second editable paint and must not enter the scene.
        if (clipped && unpainted) element.remove();
      }
      setFont(details) {
        const font = this.commonObjs.get(details[0]);
        if (font.isType3Font) throw new Error("PDF Type3 text needs a glyph interpreter; the original page was retained.");
        if (font.vertical) throw new Error("Vertical PDF text is not yet qualified for editable reconstruction; the original page was retained.");
        const program = fontProgram(font);
        if (program && !this.programs.has(program.family)) this.programs.set(program.family, program);
        if (!font.missingFile && !program) throw new Error("The embedded PDF font could not be recovered for editable text; the original page was retained.");
        super.setFont(details);
        this.current.pdfSourceFontName = details[0];
        if (font.missingFile) {
          this.current.fontFamily = font.fallbackName || "sans-serif";
          this.recoveryWarnings.add(`unembedded-font:${font.name || details[0]}`);
        }
      }
      showText(glyphs) {
        const span = this.current.tspan;
        const prefixLength = this.current.xcoords.length;
        const spacing = textSpacing?.planWordSpaces(glyphs, this.current, {
          textItems: this.recoveredTextItems || [], ctm: this.transformMatrix, fontName: this.current.pdfSourceFontName
        }) || { glyphs, insertions: [] };
        const recovered = recoverableGlyphs(spacing.glyphs);
        const missing = recovered.filter((glyph) => !glyph.unicode || !glyph.isInFont && !/^\s+$/u.test(glyph.unicode) && !this.current.font.missingFile);
        if (missing.length) {
          const error = new Error("PDF text contains unmapped or missing glyphs; the original page was retained.");
          error.report = { schema: SCHEMA, status: "unsupported", font: this.current.font.name, missingGlyphs: missing.slice(0, 20) };
          throw error;
        }
        const previous = this.runGlyphs.get(span) || [];
        const all = [...previous, ...recovered];
        const program = this.programs.get(this.current.font.loadedName);
        if (program) {
          for (const glyph of recovered) {
            const existing = program.fontCharToUnicode[glyph.fontChar];
            if (existing && existing !== glyph.unicode) throw new Error("A PDF display glyph has ambiguous Unicode mappings; editable text recovery needs source review.");
            program.fontCharToUnicode[glyph.fontChar] = glyph.unicode;
            if (!Object.hasOwn(program.unicodeToFontChar, glyph.unicode)) program.unicodeToFontChar[glyph.unicode] = glyph.fontChar;
          }
        }
        // Subset programs routinely omit the blank space glyph. Keep its actual
        // Unicode and advance in the run; it paints no ink in either renderer.
        super.showText(glyphs.map((glyph) => {
          if (!glyph || typeof glyph !== "object") return glyph;
          if (/^\s+$/u.test(glyph.unicode || "")) return { ...glyph, isInFont: true, fontChar: /[\u0000-\u0008\u000b\u000c\u000e-\u001f]/u.test(glyph.fontChar) ? " " : glyph.fontChar };
          if (/[\u0000-\u0008\u000b\u000c\u000e-\u001f]/u.test(glyph.fontChar)) throw new Error("A PDF display glyph uses an XML-incompatible character code; its source font needs remapping before editable import.");
          return glyph;
        }));
        if (spacing.insertions.length) {
          const serializedX = span.getAttribute("x").trim().split(/\s+/);
          this.current.xcoords = textSpacing.mergeSpacePositions(this.current.xcoords, prefixLength, spacing.insertions);
          span.setAttribute("x", textSpacing.mergeSpacePositions(serializedX, prefixLength, spacing.insertions).join(" "));
          span.textContent = all.map((glyph) => /^\s+$/u.test(glyph.unicode) && /[\u0000-\u0008\u000b\u000c\u000e-\u001f]/u.test(glyph.fontChar) ? " " : glyph.fontChar).join("");
          this.wordSpacingRecovery.push({ schema: spacing.schema, sourceFont: this.current.pdfSourceFontName, insertions: spacing.insertions, reference: spacing.reference });
        }
        this.runGlyphs.set(span, all);
        const textMatrix = this.current.textMatrix.slice();
        textMatrix[5] += this.current.textRise;
        this.current.txtElement.setAttribute("transform", `matrix(${textMatrix.join(" ")}) scale(${this.current.textHScale * this.current.fontDirection} -1)`);
        span.setAttribute("data-pdf-unicode", all.map((glyph) => glyph.unicode).join(""));
        span.setAttribute("data-pdf-glyph-map", JSON.stringify(all));
        span.setAttribute("data-pdf-original-font", this.current.font.name || this.current.fontFamily);
        if (this.current.font.missingFile) span.setAttribute("data-pdf-font-substitution", this.current.fontFamily);
        if (logicalOptions.logicalTextSource) { const logicalRuntime = typeof module === "object" && module.exports ? require("./pdf-logical-text-runtime.js") : globalThis.FigureStudioPdfLogicalTextRuntime; logicalRuntime.observeDecodedText(logicalOptions.logicalTextSource, span, recovered, this.current.font, this.current.fontSize); }
      }
      group(items) {
        // SVGGraphics flattens save/restore scopes. Isolate their output under a
        // neutral group; child transforms remain full page transforms.
        const parent = this.svg;
        const scope = this.svgFactory.createElement("svg:g");
        scope.setAttribute("id", `pdf-scope-${++this.scopeSerial}`);
        scope.setAttribute("data-pdf-scope", "graphics-state");
        this._ensureTransformGroup();
        parent.append(scope);
        this.save();
        this.svg = scope;
        this.current.clipGroup = null;
        this.tgrp = null;
        this.executeOpTree(items);
        this.svg = parent;
        this.restore();
      }
      executeOpTree(items) {
        const metadata = new Set(["beginMarkedContent", "beginMarkedContentProps", "endMarkedContent", "markPoint", "markPointProps"]);
        for (const item of items) {
          if (metadata.has(item.fn)) continue;
          if (item.fn === "beginGroup") { this.beginTransparencyGroup(item.args[0]); continue; }
          if (item.fn === "endGroup") { this.endTransparencyGroup(); continue; }
          super.executeOpTree([item]);
        }
      }
      setGState(states) {
        // Normal compositing and an explicitly disabled mask are exact no-ops.
        // Every other blend/mask state was rejected by the operator inventory.
        super.setGState(states.filter(([key]) => key !== "BM" && key !== "SMask"));
      }
      _makeShadingPattern(args) {
        const pattern = typeof args === "string" ? this.objs.get(args) : args;
        if (pattern?.[0] !== "RadialAxial" || !["axial", "radial"].includes(pattern[1])) throw new Error("This PDF shading cannot yet be reconstructed as an editable gradient; the original page was retained.");
        return super._makeShadingPattern(args);
      }
      _makeTilingPattern() {
        throw new Error("PDF tiling-pattern paints are not yet qualified for editable reconstruction; the original page was retained.");
      }
      beginTransparencyGroup(group) {
        if (this.current.fillAlpha !== this.current.strokeAlpha) throw new Error("A PDF transparency group uses different fill and stroke opacity; reconstruction is not yet qualified.");
        const parent = this.svg;
        const scope = this.svgFactory.createElement("svg:g");
        scope.setAttribute("id", `pdf-transparency-${++this.scopeSerial}`);
        scope.setAttribute("data-pdf-scope", "transparency");
        scope.setAttribute("opacity", String(this.current.fillAlpha));
        parent.append(scope);
        this.save();
        this.transparencyScopes.push(parent);
        this.svg = scope;
        this.current.clipGroup = null;
        this.current.fillAlpha = 1;
        this.current.strokeAlpha = 1;
        this.tgrp = null;
        if (group.bbox?.length === 4) {
          const rect = this.svgFactory.createElement("svg:rect");
          const [x0, y0, x1, y1] = group.bbox;
          for (const [key, value] of Object.entries({ x: x0, y: y0, width: x1 - x0, height: y1 - y0 })) rect.setAttribute(key, String(value));
          const contentMatrix = this.transformMatrix;
          if (group.matrix) this.transformMatrix = pdfjs.Util.transform(contentMatrix, group.matrix);
          this.current.element = rect;
          this.clip("nonzero");
          this.endPath();
          this.transformMatrix = contentMatrix;
          this.tgrp = null;
        }
      }
      endTransparencyGroup() {
        if (!this.transparencyScopes.length) throw new Error("PDF transparency groups are unbalanced.");
        this.svg = this.transparencyScopes.pop();
        this.restore();
      }
    };
    const numbers = typeof module === "object" && module.exports
      ? require("./pdf-decoded-svg-number-precision.js") : globalThis.FigureStudioPdfSvgNumberPrecision;
    if (!numbers?.createGraphicsClass) throw new Error("Decoded PDF SVG number preservation is unavailable.");
    return numbers.createGraphicsClass(EditableSvgGraphics, pdfjs);
  }

  async function registerFonts(fonts, targetDocument = typeof document !== "undefined" ? document : null) {
    if (!targetDocument?.fonts || typeof FontFace !== "function") return [];
    let cache = registeredFonts.get(targetDocument);
    if (!cache) { cache = new Map(); registeredFonts.set(targetDocument, cache); }
    const results = [];
    for (const program of fonts || []) {
      if (!program?.family || !/^data:/.test(program.dataUrl || "")) continue;
      const key = `${program.family}:${program.dataUrl}`;
      if (!cache.has(key)) {
        const promise = (async () => {
          const face = new FontFace(program.family, `url(${program.dataUrl})`, { weight: program.weight || "normal", style: program.style || "normal" });
          await face.load();
          targetDocument.fonts.add(face);
          return program.family;
        })();
        cache.set(key, promise);
        promise.catch(() => cache.delete(key));
      }
      results.push(await cache.get(key));
    }
    return results;
  }

  function fontsInWorkspace(value) {
    const programs = new Map();
    const seen = new Set();
    const visit = (item) => {
      if (!item || typeof item !== "object" || seen.has(item)) return;
      seen.add(item);
      if (item.schema === SCHEMA && Array.isArray(item.fonts)) {
        for (const font of item.fonts) if (font?.family && font?.dataUrl) programs.set(`${font.family}:${font.dataUrl}`, font);
      }
      for (const child of Object.values(item)) if (child && typeof child === "object") visit(child);
    };
    visit(value);
    return [...programs.values()];
  }

  function namespaceFontPrograms(svg, fonts, sourceId) {
    // Interpreter document IDs restart in a fresh browser. A saved subset font
    // must not collide with the next PDF opened in that browser.
    const aliases = new Map(fonts.map((font, index) => [font.family, `figurepdf${sourceId}_${index}`]));
    for (const element of svg.querySelectorAll("[font-family]")) {
      const family = element.getAttribute("font-family");
      if (aliases.has(family)) element.setAttribute("font-family", aliases.get(family));
    }
    for (const element of svg.querySelectorAll("style")) {
      element.textContent = element.textContent.replace(/font-family:\s*"([^"]+)"/g, (declaration, family) => aliases.has(family) ? `font-family: "${aliases.get(family)}"` : declaration);
    }
    for (const font of fonts) {
      font.interpreterFamily = font.family;
      font.family = aliases.get(font.family);
    }
    return fonts;
  }

  async function prepareCurrentNativePageRoute({ logicalTextSource, logicalRuntime, page, operators, pdfjs, viewport, fabric }) {
    if (!logicalTextSource) return { currentPlanePage: null, currentPlaneViewport: viewport };
    const view = page.view;
    if (!fabric || !logicalRuntime.bindCurrentClipPlanes || !logicalRuntime.currentNativeRenderer || !logicalRuntime.constructCurrentPlaneObjects
        || !Array.isArray(view) || view.length !== 4 || !view.every(Number.isFinite)
        || view[0] !== 0 || view[1] !== 0 || !(view[2] > 0 && view[3] > 0) || page.rotate !== 0 || page.userUnit !== 1) {
      throw new Error("This generated PDF cannot use the qualified current page-coordinate route.");
    }
    // The private binder proves the actual native page/operator/byte ownership.
    // These separately reported dimensions carry no native write authority.
    const currentPlanePage = { widthPt: view[2] - view[0], heightPt: view[3] - view[1],
      widthPx: (view[2] - view[0]) * 96 / 72, heightPx: (view[3] - view[1]) * 96 / 72 };
    const currentPlaneViewport = page.getViewport({ scale: 96 / 72 });
    await logicalRuntime.bindCurrentClipPlanes(logicalTextSource, { page, operators, pdfjs, viewport: currentPlaneViewport });
    return { currentPlanePage, currentPlaneViewport };
  }

  async function renderPage({ pdfjs, bytes, pageNumber = 1, budgets = DEFAULT_BUDGETS, onProgress, fabric, signal, knockoutProofWorkerUrl, readKnockoutSource, loadPdfLib } = {}) {
    if (!pdfjs?.SVGGraphics) throw new Error("The bundled PDF interpreter is unavailable.");
    const data = bytes instanceof Uint8Array ? bytes : new Uint8Array(bytes || []);
    const limits = { ...DEFAULT_BUDGETS, ...budgets };
    if (!data.length || data.length > limits.sourceBytes) throw new Error("PDF source exceeds the editable import byte budget.");
    const start = typeof performance !== "undefined" ? performance.now() : Date.now();
    let handle;
    try {
      handle = await pdfjs.getDocument({ data: data.slice(), fontExtraProperties: true, isOffscreenCanvasSupported: false, useSystemFonts: true }).promise;
      const page = await handle.getPage(pageNumber);
      const viewport = page.getViewport({ scale: 1 });
      const operators = await page.getOperatorList();
      const logicalRuntime = typeof module === "object" && module.exports ? require("./pdf-logical-text-runtime.js") : globalThis.FigureStudioPdfLogicalTextRuntime;
      const logicalTextSource = logicalRuntime ? await logicalRuntime.sourceForPage({ handle, page, operators, pdfjs, bytes: data, pageNumber, loadPdfLib }) : null;
      const { currentPlanePage, currentPlaneViewport } = await prepareCurrentNativePageRoute({ logicalTextSource, logicalRuntime, page, operators, pdfjs, viewport, fabric });
      const prepared = await prepareKnockoutScopes({ operatorList: operators, OPS: pdfjs.OPS, bytes: data, pageNumber, budgets: limits, signal, onProgress, workerUrl: knockoutProofWorkerUrl, readSource: readKnockoutSource });
      const inventory = prepared.inventory;
      if (inventory.unsupported.length) {
        const error = new Error(`Editable PDF reconstruction does not yet support ${inventory.unsupported.join(", ")}. The original page was retained.`);
        error.code = "PDF_EDITABLE_UNSUPPORTED";
        error.report = { schema: SCHEMA, status: "unsupported", ...inventory };
        throw error;
      }
      onProgress?.({ stage: "reconstruct", ...inventory });
      // Let the browser paint the import progress before bounded interpretation.
      await new Promise((resolve) => setTimeout(resolve, 0));
      // K scopes use the original-index asynchronous walk, avoiding a second
      // recursive implementation whose synthetic q/Q tree loses source indexes.
      const batching = typeof module === "object" && module.exports ? require("./pdf-editable-import-batching.js") : globalThis.FigureStudioPdfEditableImportBatching;
      if (prepared.binding && (!batching || !fabric)) throw new Error("Editable knockout reconstruction requires the qualified batching renderer and Fabric compositor.");
      const knockoutSources = prepared.binding ? createKnockoutSources(operators, prepared.binding, viewport, pageNumber) : [];
      const Renderer = prepared.binding ? batching.rendererClass(pdfjs, { fabric, knockoutBinding: prepared.binding, knockoutSources, sourceId: prepared.sourceId, pageNumber, signal, onProgress }) : rendererClass(pdfjs, { logicalTextSource });
      const CurrentRenderer = currentPlanePage
        ? logicalRuntime.currentNativeRenderer(logicalTextSource, { Base: Renderer, page, operators, pdfjs, viewport: currentPlaneViewport }) : Renderer;
      const graphics = new CurrentRenderer(page.commonObjs, page.objs);
      graphics.recoveredTextItems = (await page.getTextContent({ disableNormalization: true })).items;
      const svg = await graphics.getSVG(operators, currentPlaneViewport);
      if (currentPlanePage) {
        svg.setAttribute("width", String(currentPlanePage.widthPx));
        svg.setAttribute("height", String(currentPlanePage.heightPx));
        svg.setAttribute("viewBox", `0 0 ${currentPlanePage.widthPx} ${currentPlanePage.heightPx}`);
      }
      const objectCount = canonicalSvgObjectCount(svg, knockoutSources);
      if (objectCount > limits.objects) throw new Error(`Editable PDF reconstruction contains ${objectCount} objects, exceeding its qualified object budget.`);
      const fonts = [...graphics.programs.values()];
      if (fonts.length) {
        const digest = new Uint8Array(await globalThis.crypto.subtle.digest("SHA-256", data));
        const sourceId = Array.from(digest, (byte) => byte.toString(16).padStart(2, "0")).join("");
        namespaceFontPrograms(svg, fonts, `${sourceId}_p${pageNumber}`);
      }
      await registerFonts(fonts);
      const svgText = new XMLSerializer().serializeToString(svg);
      if (logicalTextSource) await logicalRuntime.finishDecodedSvg(logicalTextSource, svgText, svg);
      const currentPlaneObjects = currentPlanePage
        ? await logicalRuntime.constructCurrentPlaneObjects({ token: logicalTextSource, svgText, svg, fabric,
            materializer: globalThis.FigureStudioPdfSvgMaterializer || (typeof module === "object" && module.exports ? require("./pdf-svg-materializer.js") : null) }) : null;
      const elapsedMs = (typeof performance !== "undefined" ? performance.now() : Date.now()) - start;
      const report = {
        schema: SCHEMA,
        status: "reconstructed",
        ...inventory,
        objectCount,
        fonts,
        warnings: [...graphics.recoveryWarnings],
        wordSpacingRecovery: graphics.wordSpacingRecovery,
        ...(prepared.binding ? { knockout: { groupCount: knockoutSources.length, canonicalMemberCount: knockoutSources.length * 2, sourceSha256: prepared.sourceId, scopeIndexes: knockoutSources.map(entry => [entry.scopeStart, entry.scopeEnd]), operatorBinding: prepared.binding.operatorBinding } } : {}),
        nativeEquivalent: false,
        elapsedMs
      };
      return {
        svgText,
        svgElement: svg,
        logicalTextSource,
        currentPlaneObjects,
        currentPlanePage,
        knockoutSources,
        width: viewport.width,
        height: viewport.height,
        sourceWidth: viewport.width,
        sourceHeight: viewport.height,
        pageNumber,
        pageCount: handle.numPages,
        operatorCount: inventory.operatorCount,
        editableImport: report
      };
    } finally {
      await handle?.destroy?.();
    }
  }

  return { SCHEMA, DEFAULT_BUDGETS, inventoryOperators, prepareKnockoutScopes, boundKnockoutScope, createKnockoutSources, isTrustedKnockoutSources, canonicalSvgObjectCount, recoverableGlyphs, rendererClass, registerFonts, fontsInWorkspace, namespaceFontPrograms, prepareCurrentNativePageRoute, renderPage };
});
