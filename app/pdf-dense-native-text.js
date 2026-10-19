/* Native editable label views from actual worker-owned glyph fragments. */
(function (root, factory) {
  const cjs = typeof module === "object" && module.exports;
  const api = factory(cjs ? require("./pdf-dense-document-session.js") : root.FigureStudioPdfDenseDocumentSession,
    cjs ? require("./pdf-svg-materializer.js") : root.FigureStudioPdfSvgMaterializer,
    cjs ? require("./pdf-scene-number-precision.js") : root.FigureStudioPdfSceneNumberPrecision,
    cjs ? require("./pdf-current-native-plane-materializer.js") : root.FigureStudioPdfCurrentNativePlaneMaterializer,
    cjs ? require("../vendor/fabric/index.min.js") : root.fabric);
  if (cjs) module.exports = api;
  else root.FigureStudioPdfDenseNativeText = api;
})(typeof globalThis === "object" ? globalThis : this, function (sessions, materializer, numbers, nativePlanes, fabric) {
  "use strict";
  const isSession = sessions?.isSession, prototype = sessions?.DenseDocumentSession?.prototype;
  const nativeRequest = prototype?.request;
  const getters = Object.fromEntries(["source", "frame", "revision", "nativeGlyphSvgFragments", "fontDescriptors", "sourceFontRepertoires"].map(key => [key, Object.getOwnPropertyDescriptor(prototype || {}, key)?.get]));
  const Parser = globalThis.DOMParser, Serializer = globalThis.XMLSerializer;
  const issued = new WeakMap(), snapshots = new WeakMap(), draftCaptures = new WeakMap(), LIMITS = Object.freeze({ texts: 32, glyphBytes: 33554432, fontBytes: 33554432 });
  const Text = materializer.registerTextClass(fabric), textPrototype = Text.prototype;
  const NativeGroup = fabric.Group, CurrentGroup = materializer.registerCurrentPlaneGroupClass(fabric), nativeEnterGroup = NativeGroup.prototype.enterGroup;
  const NativeLayoutManager = fabric.LayoutManager, NativeFixedLayout = fabric.FixedLayout;
  const finalizeAuthoringLayout = materializer.finalizeImportedAuthoringLayout;
  const adoptedHosts = new WeakSet();
  const clone = structuredClone;
  const same = (a, b) => {
    if (Object.is(a, b)) return true;
    if (!a || !b || typeof a !== "object" || typeof b !== "object" || Array.isArray(a) !== Array.isArray(b)) return false;
    const leftKeys = Reflect.ownKeys(a), rightKeys = Reflect.ownKeys(b);
    return leftKeys.length === rightKeys.length && leftKeys.every((key, index) => {
      const x = Object.getOwnPropertyDescriptor(a, key), y = Object.getOwnPropertyDescriptor(b, key);
      return key === rightKeys[index] && x && y && Object.hasOwn(x, "value") && Object.hasOwn(y, "value") && same(x.value, y.value);
    });
  };
  const encoded = number => Object.is(number, -0) ? "-0" : number;
  const paintKeys = ["fill", "stroke", "strokeWidth", "strokeLineCap", "strokeLineJoin", "strokeMiterLimit", "strokeDashArray", "strokeDashOffset",
    "fillRule", "opacity", "globalCompositeOperation", "shadow", "inverted", "absolutePositioned", "visible", "deltaY", "textBackgroundColor", "backgroundColor",
    "underline", "overline", "linethrough", "path", "pathStartOffset", "pathSide", "pathAlign", "figureStudioAppearanceStack", "figureStudioAppearanceMeta", "mask", "filters", "resizeFilter"];
  function descriptor(object, key) { for (let current = object; current; current = Object.getPrototypeOf(current)) { const result = Object.getOwnPropertyDescriptor(current, key); if (result) return result; } }
  function dataValue(object, key) { const entry = descriptor(object, key); if (entry && !Object.hasOwn(entry, "value")) refuse("Native text source and paint fields must remain data properties."); return entry?.value; }
  function effectiveDescriptors(object) {
    const descriptors = new Map();
    for (let current = object; current; current = Object.getPrototypeOf(current)) for (const key of Reflect.ownKeys(current)) {
      if (!descriptors.has(key)) descriptors.set(key, Object.getOwnPropertyDescriptor(current, key));
    }
    return descriptors;
  }
  function functionState(object) {
    const methods = new Map();
    for (const [key, entry] of effectiveDescriptors(object)) if (Object.hasOwn(entry, "value") && typeof entry.value === "function") methods.set(key, entry.value);
    return methods;
  }
  const hostMethods = new Map([NativeGroup, CurrentGroup].map(Class => [Class, functionState(Class.prototype)]));
  function geometryState(object, inClip) {
    const geometry = {};
    if (dataValue(object, "path")) { const offset = dataValue(object, "pathOffset"); geometry.pathOffset = offset ? { x: dataValue(offset, "x"), y: dataValue(offset, "y") } : null; }
    if (inClip) for (const key of ["width", "height", "rx", "ry", "radius", "startAngle", "endAngle", "points"]) geometry[key] = clone(dataValue(object, key));
    return geometry;
  }
  function viewState(roots, leaf) {
    const rows = [], seen = new Set();
    const visit = (object, inClip = false) => {
      if (!object || seen.has(object)) return; seen.add(object);
      const methods = functionState(object), matrix = methods.get("calcOwnMatrix");
      if (!matrix) refuse("A native text ancestor has no original matrix method.");
      const children = dataValue(object, "_objects")?.slice() || [], manager = dataValue(object, "layoutManager"), strategy = dataValue(manager, "strategy");
      rows.push({ object, prototype: Object.getPrototypeOf(object), methods, matrix: Reflect.apply(matrix, object, []).slice(),
        paint: clone(Object.fromEntries(paintKeys.map(key => [key, dataValue(object, key)]))), children,
        clipPath: dataValue(object, "clipPath"), parent: dataValue(object, "parent"), group: dataValue(object, "group"), path: object !== leaf && dataValue(object, "path") ? clone(dataValue(object, "path")) : null,
        inClip, geometry: geometryState(object, inClip), manager, strategy,
        layoutComponents: [manager, strategy].filter(Boolean).map(component => ({ object: component, prototype: Object.getPrototypeOf(component), methods: functionState(component) })) });
      children.forEach(child => visit(child, inClip)); visit(dataValue(object, "clipPath"), true);
    };
    roots.forEach(root => visit(root)); return rows;
  }
  function checkEntry(entry) {
    for (const [sourceObjectIndex, before] of entry.state.entries()) {
      const object = before.object;
      if (Object.getPrototypeOf(object) !== before.prototype || dataValue(object, "clipPath") !== before.clipPath || dataValue(object, "parent") !== before.parent || dataValue(object, "group") !== before.group
          || (dataValue(object, "_objects") || []).length !== before.children.length
          || before.children.some((child, index) => dataValue(object, "_objects")[index] !== child)) refuse("The native text source tree, clips or parents changed.");
      const descriptors = effectiveDescriptors(object);
      for (const [key, method] of before.methods) { const current = descriptors.get(key); if (!current || !Object.hasOwn(current, "value") || current.value !== method) refuse("A native text renderer or geometry method changed."); }
      if (dataValue(object, "layoutManager") !== before.manager || dataValue(before.manager, "strategy") !== before.strategy) refuse("The native text layout manager or strategy changed.");
      for (const component of before.layoutComponents) {
        if (Object.getPrototypeOf(component.object) !== component.prototype) refuse("The native text layout manager or strategy changed.");
        const componentDescriptors = effectiveDescriptors(component.object);
        for (const [key, method] of component.methods) { const current = componentDescriptors.get(key); if (!current || !Object.hasOwn(current, "value") || current.value !== method) refuse("A native text layout manager or strategy method changed."); }
      }
      const matrix = Reflect.apply(before.methods.get("calcOwnMatrix"), object, []), paint = Object.fromEntries(paintKeys.map(key => [key, dataValue(object, key)])),
        path = object !== entry.object && dataValue(object, "path") ? dataValue(object, "path") : null, geometry = geometryState(object, before.inClip);
      const mismatch = !same(before.matrix, matrix) ? ["matrix", before.matrix, matrix]
        : !same(before.paint, paint) ? (() => { const key = paintKeys.find(key => !same(before.paint[key], paint[key])); return ["paint." + key, before.paint[key], paint[key]]; })()
        : !same(before.path, path) ? ["path", before.path, path]
        : !same(before.geometry, geometry) ? (() => { const key = Object.keys(before.geometry).find(key => !same(before.geometry[key], geometry[key])); return ["geometry." + key, before.geometry[key], geometry[key]]; })() : null;
      if (mismatch) {
        const summary = value => value === undefined ? "undefined" : typeof value === "number" && Object.is(value, -0) ? "-0"
          : typeof value === "string" ? value.slice(0, 256) : value === null || typeof value !== "object" ? value
          : Array.isArray(value) && value.length <= 16 && value.every(item => item === null || typeof item !== "object") ? value.map(summary)
          : { kind: Array.isArray(value) ? "array" : "object", keys: Object.keys(value).slice(0, 16), ...(Array.isArray(value) ? { length: value.length } : {}) };
        const detail = { id: entry.id, sourceObjectIndex, leaf: object === entry.object, inClip: before.inClip, field: mismatch[0], before: summary(mismatch[1]), after: summary(mismatch[2]) };
        const error = new Error("Native text editing must retain source planes, paint and clips.");
        error.code = "PDF_DENSE_NATIVE_TEXT_REFUSED"; error.detail = detail; throw error;
      }
    }
    if (entry.object.constructor !== Text || !same(entry.source, dataValue(entry.object, "pdfTextSource"))) refuse("The native text source glyph recipe changed.");
  }
  function candidateFor(entry) {
    const object = entry.object, plane = Reflect.apply(textPrototype._pdfCurrentNativePlane, object, []), layout = Reflect.apply(textPrototype._pdfPaintLayout, object, []);
    if (!plane || !layout || typeof layout.text !== "string" || layout.text.length > 4096 || Array.from(layout.text).length !== layout.text.length || layout.styles.length) refuse("The native text edit exceeds its current scalar layout profile.");
    const entries = Reflect.apply(textPrototype._pdfCurrentPlaneEntries, object, [plane]), glyphs = [];
    let index = 0, charIndex = 0;
    for (const [lineIndex, line] of layout.text.split("\n").entries()) {
      for (let columnIndex = 0; columnIndex < line.length; columnIndex++) {
        const current = entries[index], unicode = line[columnIndex];
        if (!current || current.charIndex !== charIndex || current.charCount !== 1) refuse("The native authored glyph coverage is incomplete.");
        const sourceGlyph = plane.kind === "source" ? object.pdfTextSource.glyphs[index] : null;
        const declaration = object.getCompleteStyleDeclaration(lineIndex, columnIndex);
        const mapped = sourceGlyph ? sourceGlyph.fontChar : Reflect.apply(textPrototype._mapped, object, [unicode, declaration]).text;
        if (sourceGlyph && sourceGlyph.unicode !== unicode || Array.from(mapped).length !== 1) refuse("The current glyph mapping is outside the source scalar profile.");
        glyphs.push({ lineIndex, columnIndex, charIndex, charCount: 1, unicode, fontChar: mapped, x: encoded(current.x), y: encoded(current.y) });
        index++; charIndex++;
      }
      charIndex++;
    }
    if (index !== entries.length) refuse("The native text has extra current glyph entries.");
    return clone({ schema: "figureStudio.pdfDenseTextCandidate.v1", id: entry.id, layout,
      plane: { matrices: plane.first.matrices, x: encoded(plane.first.x), y: encoded(plane.first.y) }, glyphs });
  }
  function restoreCurrent(entry, record, source, row, fragment) {
    if (!record || record.schema !== "figureStudio.pdfDenseTextState.v1" || record.id !== entry.id
        || record.base?.sourceSha256 !== source.sha256 || record.base.sourceByteLength !== source.byteLength || record.base.pageNumber !== source.pageNumber
        || record.base.operatorIndex !== row.operatorIndex || record.base.paintOrdinal !== row.paintOrdinal || record.base.clipIndex !== row.clipIndex
        || record.base.programSha256 !== fragment.fontResource.programSha256) refuse("The authored native text state has no matching fresh source context.");
    const layout = record.layout, object = entry.object, original = Reflect.apply(textPrototype._pdfPaintLayout, object, []);
    if (!layout || !Array.isArray(layout.styles) || layout.styles.length
        || ["fontFamily", "fontSize", "fontWeight", "fontStyle", "lineHeight", "charSpacing", "direction", "textAlign"].some(key => !Object.is(layout[key], original[key]))) refuse("Cold authored text changed its original font or current layout policy.");
    for (const key of ["text", "fontFamily", "fontSize", "fontWeight", "fontStyle", "lineHeight", "charSpacing", "direction", "textAlign"]) object[key] = layout[key];
    object.styles = fabric.util.stylesFromArray(layout.styles, layout.text);
    Reflect.apply(textPrototype.initDimensions, object, []);
    const current = candidateFor(entry), expected = { schema: "figureStudio.pdfDenseTextCandidate.v1", id: record.id, layout: record.layout, plane: record.plane,
      glyphs: record.glyphs.map(({ sourceCharCode, ...glyph }) => glyph) };
    if (!same(current, expected)) refuse("Cold authored text does not regenerate the exact native layout and glyph entries.");
  }
  const value = (session, key) => Reflect.apply(getters[key], session, []);
  function refuse(message) { const error = new Error(message); error.code = "PDF_DENSE_NATIVE_TEXT_REFUSED"; throw error; }
  function abort(signal) { if (signal?.aborted) { const error = new Error("Native PDF text construction was cancelled."); error.name = "AbortError"; throw error; } }
  async function digest(bytes) { return Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256", bytes)), byte => byte.toString(16).padStart(2, "0")).join(""); }
  function base64(bytes) { let result = ""; for (let index = 0; index < bytes.length; index += 8192) result += String.fromCharCode(...bytes.subarray(index, index + 8192)); return btoa(result); }
  function textLeaves(roots, Text) { const result = []; const visit = object => { if (object.constructor === Text) result.push(object); for (const child of object.getObjects?.() || []) visit(child); }; for (const root of roots) visit(root); return result; }
  function sourceFontMaps(fragments, repertoires, source, fonts) {
    const maps = new Map();
    for (const fragment of fragments) {
      const id = fragment.sourceFontId, program = fragment.fontResource.programSha256;
      let current = maps.get(id);
      if (!current) { current = { program, map: {}, unicodeAdvances: {} }; maps.set(id, current); }
      if (current.program !== program) refuse("One actual native font ID refers to different original programs.");
      for (const glyph of fragment.record.glyphs) {
        if (typeof glyph.unicode !== "string" || typeof glyph.fontChar !== "string") refuse("Original source font glyph membership is incomplete.");
        if (Object.hasOwn(current.map, glyph.unicode) && current.map[glyph.unicode] !== glyph.fontChar) refuse("The actual same-font glyph mapping is ambiguous.");
        Object.defineProperty(current.map, glyph.unicode, { value: glyph.fontChar, enumerable: true, writable: true, configurable: true });
        if (/^\s+$/u.test(glyph.unicode)) {
          if (!Number.isFinite(glyph.width)) refuse("The actual source whitespace advance is missing.");
          const advance = glyph.width / 1000;
          if (Object.hasOwn(current.unicodeAdvances, glyph.unicode) && !Object.is(current.unicodeAdvances[glyph.unicode], advance)) refuse("The actual same-font whitespace advance is ambiguous.");
          Object.defineProperty(current.unicodeAdvances, glyph.unicode, { value: advance, enumerable: true, writable: true, configurable: true });
        }
      }
    }
    for (const repertoire of repertoires) {
      const current = maps.get(repertoire.fontId); if (!current) continue;
      if (repertoire.schema !== "figureStudio.pdfDenseFontRepertoire.v1" || !same(repertoire.source, { sha256: source.sha256, byteLength: source.byteLength, pageNumber: source.pageNumber })
          || repertoire.programSha256 !== current.program || repertoire.baseFont !== fonts.get(repertoire.fontId)?.name || !Array.isArray(repertoire.glyphs) || repertoire.glyphs.length > 256) refuse("The complete font repertoire differs from its actual private session source.");
      for (const glyph of repertoire.glyphs) {
        if (typeof glyph.unicode !== "string" || glyph.unicode.length !== 1 || typeof glyph.fontChar !== "string" || Array.from(glyph.fontChar).length !== 1
            || /[\x00-\x1f\x7f\ud800-\udfff]/.test(glyph.unicode) || /^[\x00-\x1f\x7f\ud800-\udfff]$/.test(glyph.fontChar)
            || !glyph.isInFont || !Number.isFinite(glyph.width) || glyph.width < 0) refuse("The private native font repertoire contains an unsupported scalar glyph.");
        if (Object.hasOwn(current.map, glyph.unicode) && current.map[glyph.unicode] !== glyph.fontChar) refuse("The actual complete font glyph mapping is ambiguous.");
        Object.defineProperty(current.map, glyph.unicode, { value: glyph.fontChar, enumerable: true, writable: true, configurable: true });
        if (/^\s+$/u.test(glyph.unicode)) {
          const advance = glyph.width / 1000;
          if (Object.hasOwn(current.unicodeAdvances, glyph.unicode) && !Object.is(current.unicodeAdvances[glyph.unicode], advance)) refuse("The actual complete whitespace advance is ambiguous.");
          Object.defineProperty(current.unicodeAdvances, glyph.unicode, { value: advance, enumerable: true, writable: true, configurable: true });
        }
      }
    }
    return maps;
  }
  function glyphPlaneModel(document, fragment, font, family, embedded, sharedFont) {
    const text = document.querySelector("text"), span = text?.querySelector("tspan");
    if (!text || !span || document.querySelectorAll("text").length !== 1 || text.children.length !== 1 || span.children.length) refuse("The native fragment must retain its one complete source text show.");
    const attributes = {};
    const ancestors = []; for (let node = span; node; node = node.parentElement) ancestors.unshift(node);
    for (const node of ancestors) {
      for (const attribute of node.attributes) attributes[attribute.name] = attribute.value;
      for (const declaration of (node.getAttribute("style") || "").split(";")) {
        if (!declaration.trim()) continue; const colon = declaration.indexOf(":");
        if (colon < 0) refuse("The native source text style is malformed.");
        attributes[declaration.slice(0, colon).trim()] = declaration.slice(colon + 1).trim();
      }
    }
    const coordinates = name => {
      const values = (span.getAttribute(name) || text.getAttribute(name) || "0").trim().split(/[\s,]+/);
      if (values.some(value => !/^[+-]?(?:\d*\.\d+|\d+\.?\d*)(?:e[+-]?\d+)?$/i.test(value) || !Number.isFinite(Number(value)))) refuse("The native glyph coordinates are incomplete.");
      return values;
    };
    const xs = coordinates("x"), ys = coordinates("y"), record = fragment.record;
    if (xs.length !== record.glyphs.length || ![1, record.glyphs.length].includes(ys.length) || span.textContent !== record.renderedText) refuse("The native glyph coordinates and display text differ from their actual writer record.");
    const transform = text.getAttribute("transform") || "", matrices = [];
    for (const match of transform.matchAll(/(matrix|scale|translate)\s*\(([^)]*)\)/g)) matrices.push(materializer.transformMatrix(match[0]));
    if (!matrices.length || matrices.length > 4 || transform.replace(/(matrix|scale|translate)\s*\([^)]*\)/g, "").trim()) refuse("The native text declaring planes exceed their reviewed profile.");
    const plan = materializer.glyphPlan(record.unicode, record.renderedText, { x: xs.map(Number), y: ys.map(Number) }, record.glyphs, fabric);
    if (plan.glyphs.length !== record.glyphs.length || plan.glyphs.some((glyph, index) => glyph.unicode !== record.glyphs[index].unicode || glyph.fontChar !== record.glyphs[index].fontChar)) refuse("The native glyph-to-Unicode membership is incomplete.");
    const fontSize = Number(String(attributes["font-size"] || "").replace(/px$/, "")), fontWeight = attributes["font-weight"] || "normal", fontStyle = attributes["font-style"] || "normal";
    if (!Number.isFinite(fontSize) || fontSize <= 0 || fontSize !== record.fontSize || attributes["text-anchor"] && attributes["text-anchor"] !== "start") refuse("The native font declaration differs from its actual writer record.");
    const sourceFontKey = JSON.stringify([family, fontWeight, fontStyle]);
    const source = { schema: "figureStudio.pdfPositionedText.v1", text: record.unicode, anchor: "start", fontFamily: family,
      originalFontName: font.name || record.fontName || family, displayFontFamily: family, sourceEmbeddedProgram: embedded,
      fontSubstitutionFamily: embedded ? "" : family, fontSize, fontWeight, fontStyle, map: { ...sharedFont.map, ...plan.map },
      unicodeAdvances: { ...sharedFont.unicodeAdvances, ...plan.unicodeAdvances }, glyphs: plan.glyphs.map(glyph => ({ ...glyph, sourceFontKey })), fallbackFont: "Arial",
      currentNativeGlyphPlanes: { schema: "figureStudio.currentNativeGlyphPlanes.v1", entries: plan.glyphs.map((glyph, index) => ({
        matrices: structuredClone(matrices), x: xs[index], y: ys.length === 1 ? ys[0] : ys[index],
        charIndex: glyph.charIndex, charCount: glyph.charCount, sourceFontKey })) } };
    const row = node => ({ tag: node.localName.replace(/^.*:/, ""), attrs: Object.fromEntries(Array.from(node.attributes, attribute => [attribute.name, attribute.value])),
      text: node.children.length ? "" : node.textContent, children: Array.from(node.children, row) });
    return { dom: row(document.documentElement), model: { options: { text: record.unicode, fontFamily: family, fontSize, fontWeight, fontStyle,
      textAlign: "left", charSpacing: 0, lineHeight: 1.16, stroke: null, strokeWidth: 0, objectCaching: false, editable: true }, source } };
  }
  async function create({ session, signal, yieldToUi, onProgress } = {}) {
    if (!isSession?.(session) || typeof nativeRequest !== "function" || Object.values(getters).some(getter => typeof getter !== "function")) refuse("Native text views require a completed private PDF document session.");
    if (typeof Parser !== "function" || typeof Serializer !== "function") refuse("Native text views require the supported browser SVG document implementation.");
    abort(signal);
    const revision = value(session, "revision"), source = value(session, "source"), frame = value(session, "frame"), fragments = value(session, "nativeGlyphSvgFragments"), fonts = value(session, "fontDescriptors");
    const current = () => { abort(signal); if (!isSession(session) || value(session, "revision") !== revision) refuse("The canonical PDF changed while its native text views were being constructed."); };
    if (!Array.isArray(fragments) || fragments.length > LIMITS.texts || new Set(fragments.map(fragment => fragment.id)).size !== fragments.length) refuse("The original-source text view envelope is incomplete or exceeded.");
    const read = fragments.length ? await Reflect.apply(nativeRequest, session, ["read", { ids: fragments.map(fragment => fragment.id) }, { signal }]) : { revision, result: [] };
    current();
    if (read.revision !== revision || !Array.isArray(read.result) || read.result.length !== fragments.length) refuse("The current native text source read is stale or incomplete.");
    const currentRows = new Map(read.result.map(row => [row.id, row]));
    for (const fragment of fragments) {
      const row = currentRows.get(fragment.id);
      if (!row || row.kind !== "text" || row.operatorIndex !== fragment.operatorIndex || row.paintOrdinal !== fragment.paintOrdinal
          || row.text?.unicode !== fragment.record?.unicode) refuse("Changed text requires its qualified authored-text view.");
      if (row.placement && (row.placement.documentRevision !== revision || !Array.isArray(row.placement.planePath))) refuse("The native text group placement is stale or incomplete.");
      if (row.placement?.planePath.length > 48 || row.placement?.planePath.some(plane => typeof plane.nodeId !== "string" || !Array.isArray(plane.matrix)
          || plane.matrix.length !== 6 || !plane.matrix.every(Number.isFinite) || ![1, 0, 0, 1].every((value, index) => Object.is(value, plane.matrix[index])))) refuse("The native text authored parent planes are outside their qualified translation profile.");
    }
    const fontById = new Map(fonts.map(font => [font.id, font])), aliases = new Map(), programs = [], roots = [], entries = [], privateEntries = new Map();
    let glyphBytes = 0, fontBytes = 0;
    try {
      for (const fragment of fragments) {
        current(); glyphBytes += new TextEncoder().encode(fragment.svg).length;
        if (glyphBytes > LIMITS.glyphBytes || fragment.source?.sha256 !== source.sha256 || fragment.source?.pageNumber !== source.pageNumber
            || fragment.record?.context?.id !== fragment.id || fragment.operatorIndex !== fragment.record.operatorIndex
            || fragment.paintOrdinal !== fragment.record.paintOrdinal || fragment.sourceFontId !== fragment.record.sourceFontId) refuse("A native text fragment lost its complete source membership.");
        const font = fontById.get(fragment.sourceFontId), proof = fragment.fontResource;
        if (!font || !proof || proof.id !== font.id) refuse("The native text font resource is missing.");
        if (!font.data?.length) { if (!font.missingFile || proof.programSha256 !== null) refuse("A native embedded font program is unavailable."); continue; }
        if (aliases.has(fragment.record.fontFamily)) {
          if (aliases.get(fragment.record.fontFamily).sha256 !== proof.programSha256) refuse("One native font alias refers to different programs.");
          continue;
        }
        fontBytes += font.data.byteLength;
        if (fontBytes > LIMITS.fontBytes || await digest(font.data) !== proof.programSha256) refuse("The complete native font program differs from its actual writer proof.");
        current();
        const family = "FigureDense_" + source.sha256 + "_p" + source.pageNumber + "_" + proof.programSha256;
        aliases.set(fragment.record.fontFamily, { family, sha256: proof.programSha256 });
        programs.push({ family, dataUrl: "data:" + (font.mimetype || "font/opentype") + ";base64," + base64(font.data),
          weight: font.bold ? "bold" : "normal", style: font.italic ? "italic" : "normal" });
      }
      const sharedFonts = sourceFontMaps(fragments, value(session, "sourceFontRepertoires"), source, fontById);
      const installed = await materializer.registerFonts(programs); current();
      if (installed.failures.length || installed.loaded.length !== programs.length) refuse("A native text font program could not be installed completely.");
      const precision = numbers.createInstaller({ fabric, additionalSerializers: [Text.prototype.toObject] });
      for (const fragment of fragments) {
        current();
        const document = new Parser().parseFromString(fragment.svg, "image/svg+xml");
        if (document.querySelector("parsererror")) refuse("The actual native text fragment is invalid SVG.");
        const replacement = aliases.get(fragment.record.fontFamily);
        if (replacement) for (const element of document.querySelectorAll("[font-family]")) {
          if (element.getAttribute("font-family") === fragment.record.fontFamily) element.setAttribute("font-family", replacement.family);
        }
        const placement = currentRows.get(fragment.id).placement;
        if (placement?.planePath.length) {
          const parents = Array.from(document.documentElement.children).filter(element => element.localName === "g");
          if (parents.length !== 1 || parents[0].getAttribute("transform") !== "matrix(" + frame.transform.map(number => Object.is(number, -0) ? "-0" : String(number)).join(" ") + ")") refuse("The native text viewport wrapper changed before authored placement.");
          const viewport = parents[0], authored = document.createElementNS("http://www.w3.org/2000/svg", "g");
          authored.setAttribute("transform", placement.planePath.map(plane => "matrix(" + plane.matrix.map(number => Object.is(number, -0) ? "-0" : String(number)).join(" ") + ")").join(" "));
          while (viewport.firstChild) authored.appendChild(viewport.firstChild);
          viewport.appendChild(authored);
        }
        const font = fontById.get(fragment.sourceFontId), family = replacement?.family || fragment.record.fontFamily;
        const input = glyphPlaneModel(document, fragment, font, family, Boolean(replacement), sharedFonts.get(fragment.sourceFontId));
        const result = await nativePlanes.constructTextPlanes(fabric, materializer, input, { signal, yieldControl: yieldToUi });
        const objects = [result.root]; roots.push(...objects); current();
        const leaves = textLeaves(objects, Text);
        if (result.paints.length !== 1 || result.paints[0].kind !== "text" || leaves.length !== 1
            || leaves[0].text !== fragment.record.unicode) refuse("A native glyph fragment did not produce its one complete editable text object.");
        const object = leaves[0]; object.figureId = fragment.id; object.figureType = "text"; object.name = object.text;
        precision.installScene(objects, { isPdfObject: () => true });
        const entry = { id: fragment.id, object, roots: objects, source: clone(object.pdfTextSource) };
        if (currentRows.get(fragment.id).authoredText) restoreCurrent(entry, currentRows.get(fragment.id).authoredText, source, currentRows.get(fragment.id), fragment);
        entry.state = viewState(objects, object); privateEntries.set(fragment.id, entry);
        onProgress?.({ stage: "native-text", completed: entries.length + 1, total: fragments.length });
        entries.push(Object.freeze({ id: fragment.id, operatorIndex: fragment.operatorIndex, paintOrdinal: fragment.paintOrdinal, object, roots: Object.freeze(objects) }));
      }
      current();
      const owner = Object.freeze({ source: Object.freeze(source), revision, frame: Object.freeze({ ...frame, transform: Object.freeze(frame.transform.slice()) }), entries: Object.freeze(entries) });
      issued.set(owner, { session, revision, roots, frame: clone(frame), entries: privateEntries }); return owner;
    } catch (error) { for (const root of roots) root.dispose?.(); throw error; }
  }
  function isCurrent(owner) { const data = issued.get(owner); return Boolean(data && isSession(data.session) && value(data.session, "revision") === data.revision); }
  function check(owner) { const data = issued.get(owner); if (!data || !isSession(data.session)) refuse("The native text owner is closed or foreign."); if (value(data.session, "revision") !== data.revision) refuse("The canonical PDF revision changed; rebuild its native text views."); return data; }
  function snapshot(owner, id) {
    const data = check(owner), entry = data.entries.get(id);
    if (!entry) refuse("The native text edit does not belong to this issued source view.");
    checkEntry(entry); const candidate = candidateFor(entry);
    snapshots.set(candidate, { owner, entry, revision: data.revision, candidate: clone(candidate) }); return candidate;
  }
  function captureDraft(owner, id, { signal } = {}) {
    abort(signal); const data = check(owner), entry = data.entries.get(id);
    if (!entry) refuse("The native text draft does not belong to this issued source view.");
    checkEntry(entry); const candidate = candidateFor(entry), receipt = Object.freeze({});
    abort(signal); draftCaptures.set(receipt, { owner, entry, revision: data.revision, candidate }); return receipt;
  }
  function readDraftCapture(owner, receipt, { signal } = {}) {
    abort(signal); const data = check(owner), captured = draftCaptures.get(receipt);
    if (!captured || captured.owner !== owner) refuse("The native text draft capture is foreign.");
    if (captured.revision !== data.revision || data.entries.get(captured.entry.id) !== captured.entry) refuse("The native text draft capture is stale.");
    checkEntry(captured.entry);
    if (!same(candidateFor(captured.entry), captured.candidate)) refuse("The native text draft changed during read-only capture.");
    abort(signal); return clone(captured.candidate);
  }
  function prepareEditing(owner, id) {
    const data = check(owner), entry = data.entries.get(id);
    if (!entry) refuse("The native text edit does not belong to this issued source view.");
    checkEntry(entry);
    // Allowed outer page transforms change the layout guard's world context.
    // Reseed only the audited managers after validating every source-local field.
    Reflect.apply(finalizeAuthoringLayout, materializer, [entry.roots, { fabric }]);
    checkEntry(entry); return entry.object;
  }
  function createSourceHost({ frame } = {}) {
    if (!frame || !Number.isFinite(frame.width) || !Number.isFinite(frame.height)
        || frame.width <= 0 || frame.height <= 0 || frame.width > 1e8 || frame.height > 1e8) refuse("A native source host requires a finite positive page frame.");
    const host = new NativeGroup([], { width: frame.width, height: frame.height, left: -frame.width / 2, top: -frame.height / 2,
      originX: "center", originY: "center", strokeWidth: 0, objectCaching: false, subTargetCheck: true,
      interactive: true, selectable: false, evented: true, layoutManager: new NativeLayoutManager(new NativeFixedLayout()) });
    // The application may decorate inherited Fabric methods after this module
    // loads. Source-frame hosts keep the exact component-native implementations.
    for (const [key, method] of hostMethods.get(NativeGroup)) if (key !== "constructor"
        && !["__objectSelectionTracker", "__objectSelectionDisposer"].includes(key)) {
      Object.defineProperty(host, key, { value: method, configurable: true, writable: true });
    }
    return host;
  }
  function adopt(owner, id, host) {
    const data = check(owner), entry = data.entries.get(id), Class = dataValue(host, "constructor"), methods = hostMethods.get(Class);
    if (!entry || entry.adopted || adoptedHosts.has(host)) refuse("A native text slot can be adopted only once by its current owner.");
    checkEntry(entry);
    if (!methods || Object.getPrototypeOf(host) !== Class.prototype || !Array.isArray(dataValue(host, "_objects")) || dataValue(host, "_objects").length
        || dataValue(host, "width") !== data.frame.width || dataValue(host, "height") !== data.frame.height || dataValue(host, "objectCaching") !== false) refuse("Native text adoption requires an empty actual fixed-frame native group.");
    for (const [key, method] of methods) { const current = descriptor(host, key); if (!current || !Object.hasOwn(current, "value") || current.value !== method) refuse("The native text host renderer or geometry methods changed."); }
    if (dataValue(host, "clipPath") || dataValue(host, "shadow") || dataValue(host, "mask") || dataValue(host, "filters")?.length || dataValue(host, "resizeFilter")
        || dataValue(host, "backgroundColor") || dataValue(host, "figureStudioAppearanceStack") || dataValue(host, "figureStudioAppearanceMeta")
        || dataValue(host, "opacity") !== 1 || dataValue(host, "visible") !== true || ![undefined, "source-over"].includes(dataValue(host, "globalCompositeOperation"))) refuse("The native text source host must retain a plain source plane.");
    const expected = [1, 0, 0, 1, -data.frame.width / 2, -data.frame.height / 2];
    if (!same(Reflect.apply(methods.get("calcOwnMatrix"), host, []), expected)) refuse("The native text source host plane differs from the fixed page frame.");
    for (const root of entry.roots) if (dataValue(root, "parent") || dataValue(root, "group")) refuse("The native text root already belongs to another parent.");
    const own = entry.roots.map(root => root.calcOwnMatrix().slice());
    for (const root of entry.roots) Reflect.apply(nativeEnterGroup, host, [root, false]);
    host._objects = entry.roots.slice();
    if (entry.roots.some((root, index) => !same(root.calcOwnMatrix(), own[index]))) refuse("Native host adoption changed a source root's literal plane.");
    const adopted = { ...entry, adopted: true, host, state: viewState([host], entry.object) };
    data.entries.set(id, adopted); adoptedHosts.add(host); return host;
  }
  function commit(owner, candidate, { signal } = {}) {
    const data = check(owner), pending = snapshots.get(candidate);
    if (!pending || pending.owner !== owner) refuse("The native text edit snapshot is foreign or already consumed.");
    if (pending.revision !== data.revision || data.entries.get(pending.entry.id) !== pending.entry) refuse("The native text edit snapshot is stale.");
    checkEntry(pending.entry);
    if (!same(candidate, pending.candidate) || !same(candidateFor(pending.entry), pending.candidate)) refuse("The native text edit snapshot was modified or its live view changed.");
    abort(signal); snapshots.delete(candidate);
    // The native session call captures its revision and posts synchronously.
    // Its existing leafEdit operation owns the sole document history journal.
    return Reflect.apply(nativeRequest, data.session, ["edit", { changes: [{ id: pending.entry.id, authoredText: clone(pending.candidate) }] }, { signal }]);
  }
  function close(owner) { const data = issued.get(owner); if (!data) return; issued.delete(owner); for (const root of data.roots) root.dispose?.(); }
  return Object.freeze({ create, isCurrent, snapshot, captureDraft, readDraftCapture, prepareEditing, createSourceHost, adopt, commit, close, LIMITS });
});
