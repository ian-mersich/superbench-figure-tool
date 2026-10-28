(function (root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  root.FigureStudioPdfSvgMaterializer = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  const SCHEMA = "figureStudio.pdfSvgMaterialization.v1";
  const SVG_NS = "http://www.w3.org/2000/svg";
  const IDENTITY = [1, 0, 0, 1, 0, 0];
  const KEY = "data-pdf-materializer-key";
  const DRAWABLE = new Set(["path", "rect", "circle", "ellipse", "line", "polyline", "polygon", "image", "use", "text"]);
  const DEFINITIONS = new Set(["defs", "clippath", "mask", "pattern", "marker", "symbol"]);
  const META_PROPS = ["figureType", "name", "figureStudioSvgElementId", "figureStudioSvgElementTag", "figureStudioSvgGroupPath", "figureStudioSvgSourceOrder", "figureStudioSvgTextMeta", "figureStudioSvgGroupMeta"];
  const classByFabric = new WeakMap();
  const groupClassByFabric = new WeakMap();
  const currentPlaneGroupByFabric = new WeakMap();
  const authoringLayoutByFabric = new WeakMap();
  const pathClassByFabric = new WeakMap();
  const fontProgramsByDocument = new WeakMap();
  const scenePaintBindings = new WeakMap(), clipPaintBindings = new WeakMap();
  const startupTextLineRenderers = new WeakMap();
  const startupTextStyleDeclarations = new WeakMap(), primitiveTextBindings = new WeakMap();
  const sceneTransformApi = () => typeof module === "object" && module.exports
    ? require("./native-path-scene-transform.js") : globalThis.FigureStudioNativePathSceneTransform;
  function bindScenePaint(Class, kind, names, fabric) {
    scenePaintBindings.set(Class, { kind, methods: Object.fromEntries(names.map(key => [key, Class.prototype[key]])) });
    if (!clipPaintBindings.has(fabric)) clipPaintBindings.set(fabric, [fabric.Path, fabric.Rect].filter(Boolean).map(Class => ({ Class,
      methods: Object.fromEntries(["_render", "drawObject", "calcOwnMatrix", "_renderPathCommands"].map(key => [key, Class.prototype[key]])) })));
  }
  // A deferred native-text module may register this class before App installs
  // its canonical paragraph renderer. Accept that one explicit startup handoff
  // by exact previous/replacement references; never refresh arbitrary methods
  // on later register/Open/history calls.
  function bindStartupTextLineRenderer(fabric, previous, replacement) {
    const Text = classByFabric.get(fabric), binding = Text && scenePaintBindings.get(Text);
    const issued = startupTextLineRenderers.get(fabric);
    if (typeof previous !== "function" || typeof replacement !== "function" || previous === replacement
        || fabric.Text?.prototype._renderTextLine !== replacement || Text && Text.prototype._renderTextLine !== replacement) return false;
    if (issued) return issued.previous === previous && issued.replacement === replacement;
    if (binding && binding.methods._renderTextLine !== previous) return false;
    startupTextLineRenderers.set(fabric, { previous, replacement });
    if (binding) binding.methods._renderTextLine = replacement;
    return true;
  }
  // App's scientific-style copier is one explicit startup replacement. Keep
  // exact previous/replacement references; later Open/reviver calls never
  // refresh these identities to adopt an arbitrary style implementation.
  function bindStartupTextStyleDeclaration(fabric, previous, replacement) {
    const Text=classByFabric.get(fabric),binding=primitiveTextBindings.get(fabric),issued=startupTextStyleDeclarations.get(fabric);
    if(typeof previous!=="function" || typeof replacement!=="function" || previous===replacement
        || fabric.Text?.prototype.getCompleteStyleDeclaration!==replacement
        || Text && Text.prototype.getCompleteStyleDeclaration!==replacement)return false;
    if(issued)return issued.previous===previous && issued.replacement===replacement;
    if(binding && binding.completeAtRegistration!==previous)return false;
    startupTextStyleDeclarations.set(fabric,{previous,replacement});
    if(binding)binding.complete=replacement;
    return true;
  }
  function nativeSceneClip(clip, fabric) {
    const proof = simpleNativeClip(clip, fabric), bindings = clipPaintBindings.get(fabric);
    return proof && proof.layers.every(layer => {
      const binding = bindings?.find(item => layer.object.constructor === item.Class);
      return binding && Object.entries(binding.methods).every(([key, method]) => layer.object[key] === method);
    });
  }
  // This is paint admission only. It neither changes source data nor supplies a
  // geometry/number authority. Exact lazily registered methods also cover Open
  // and history revivers; unknown subclasses and clip implementations fall back.
  function nativeScenePaintKind(object, fabric) {
    if (!object || !fabric) return null;
    const binding = scenePaintBindings.get(object.constructor);
    if (!binding) {
      const Image = fabric.FabricImage || fabric.Image;
      if (Image && object.constructor === Image && object.pdfSourceId && object.figureStudioSvgElementTag === "image"
          && Number.isFinite(object.figureStudioSvgSourceOrder) && !object.clipPath) return "image";
      return object.constructor === fabric.Path && object.pdfSourceId
        && object.figureStudioSvgElementTag === "path" && Number.isFinite(object.figureStudioSvgSourceOrder)
        && !object.clipPath ? "path" : null;
    }
    if (!Object.entries(binding.methods).every(([key, method]) => object[key] === method)) return null;
    if (binding.kind === "text") {
      return !object.clipPath && ["figureStudio.pdfPositionedText.v1", "figureStudio.pdfPositionedText.v2"].includes(object.pdfTextSource?.schema) ? "text" : null;
    }
    if (object.clipPath) {
      if (!nativeSceneClip(object.clipPath, fabric)) return null;
      // The separate current-plane clip painter retains its native policy.
      if (binding.kind === "group" && (object._currentNativePlaneClip() || !object._pdfVectorClip())) return null;
      if (binding.kind === "path" && !object._nativeRectangle() && !object._nativeVectorClip()) return null;
    }
    return binding.kind;
  }
  function transformNativeClip(context, object, matrices, fabric) {
    if (!sceneTransformApi()?.setImportedClipTransform({ fabric, object, context, matrices })) {
      for (const matrix of matrices) context.transform(...matrix);
    }
  }
  const importerApi = () => typeof module === "object" && module.exports ? require("./pdf-editable-import.js") : globalThis.FigureStudioPdfEditableImport;
  const knockoutApi = () => typeof module === "object" && module.exports ? require("./pdf-knockout.js") : globalThis.FigureStudioPdfKnockout;
  function preserveRenderPolicy(fabric) {
    const ObjectClass = fabric.FabricObject || fabric.Object;
    if (ObjectClass) ObjectClass.customProperties = Array.from(new Set([...(ObjectClass.customProperties || []), "objectCaching", "noScaleCache"]));
  }
  function isNativeRectangleDisplayPath(object, options = {}) {
    const Path = pathClassByFabric.get(options.fabric);
    return Boolean(Path && object?.constructor === Path && object.pdfDisplayFillPolicy === "pdf-opaque-axis-rectangle-device-pixels-v1");
  }
  const number = (value, fallback = 0) => Number.isFinite(Number(value)) ? Number(value) : fallback;
  const tag = (element) => String(element?.localName || element?.nodeName || "").replace(/^.*:/, "").toLowerCase();
  const numbers = (value) => (String(value || "").match(/[+-]?(?:\d*\.\d+|\d+\.?\d*)(?:e[+-]?\d+)?/gi) || []).map(Number);
  const clone = (value) => {
    if (value == null) return value;
    // The browser loads this module before the precision module. Resolve only
    // at an actual clone boundary and keep the original unsupported expression.
    const precision = typeof module === "object" && module.exports
      ? require("./pdf-scene-number-precision.js") : globalThis.FigureStudioPdfSceneNumberPrecision;
    const ownedParse = precision?.ownedJsonParserForCurrentIntrinsics?.();
    return ownedParse ? ownedParse(JSON.stringify(value)) : JSON.parse(JSON.stringify(value));
  };
  const escapeXml = (value) => String(value ?? "").replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&apos;" })[char]);
  function xmlGlyph(fontChar, unicode) {
    if (!/[\x00-\x08\x0b\x0c\x0e-\x1f]/.test(fontChar)) return fontChar;
    if (/^\s+$/.test(unicode)) return " ";
    throw new Error("This PDF font uses an XML-illegal display code for a visible glyph; SVG export requires a remapped font program.");
  }

  function multiply(a, b) {
    return [a[0] * b[0] + a[2] * b[1], a[1] * b[0] + a[3] * b[1], a[0] * b[2] + a[2] * b[3], a[1] * b[2] + a[3] * b[3], a[0] * b[4] + a[2] * b[5] + a[4], a[1] * b[4] + a[3] * b[5] + a[5]];
  }

  function transformMatrix(value) {
    let result = IDENTITY.slice();
    for (const match of String(value || "").matchAll(/(matrix|translate|scale|rotate|skewX|skewY)\s*\(([^)]*)\)/g)) {
      const v = numbers(match[2]);
      let next = IDENTITY.slice();
      if (match[1] === "matrix" && v.length === 6) next = v;
      if (match[1] === "translate") next = [1, 0, 0, 1, v[0] || 0, v[1] || 0];
      if (match[1] === "scale") next = [v[0] ?? 1, 0, 0, v[1] ?? v[0] ?? 1, 0, 0];
      if (match[1] === "rotate") {
        const radians = (v[0] || 0) * Math.PI / 180;
        next = [Math.cos(radians), Math.sin(radians), -Math.sin(radians), Math.cos(radians), 0, 0];
        if (v.length > 2) next = multiply(multiply([1, 0, 0, 1, v[1], v[2]], next), [1, 0, 0, 1, -v[1], -v[2]]);
      }
      if (match[1] === "skewX") next[2] = Math.tan((v[0] || 0) * Math.PI / 180);
      if (match[1] === "skewY") next[1] = Math.tan((v[0] || 0) * Math.PI / 180);
      result = multiply(result, next);
    }
    return result;
  }

  function length(value, fallback = 0) {
    const n = numbers(value)[0];
    if (!Number.isFinite(n)) return fallback;
    const unit = String(value).trim().match(/[a-z]+$/i)?.[0]?.toLowerCase();
    return n * ({ pt: 96 / 72, pc: 16, in: 96, cm: 96 / 2.54, mm: 96 / 25.4 }[unit] || 1);
  }

  function viewport(root) {
    const box = numbers(root.getAttribute("viewBox"));
    const width = length(root.getAttribute("width"), box[2] || 1);
    const height = length(root.getAttribute("height"), box[3] || 1);
    if (box.length !== 4 || box[2] <= 0 || box[3] <= 0) return { width, height, matrix: IDENTITY.slice() };
    let sx = width / box[2], sy = height / box[3], ox = 0, oy = 0;
    const aspect = root.getAttribute("preserveAspectRatio") || "xMidYMid meet";
    if (!/\bnone\b/.test(aspect)) {
      sx = sy = /\bslice\b/.test(aspect) ? Math.max(sx, sy) : Math.min(sx, sy);
      ox = /xMax/.test(aspect) ? width - box[2] * sx : /xMid/.test(aspect) ? (width - box[2] * sx) / 2 : 0;
      oy = /YMax/.test(aspect) ? height - box[3] * sy : /YMid/.test(aspect) ? (height - box[3] * sy) / 2 : 0;
    }
    return { width, height, matrix: [sx, 0, 0, sy, ox - box[0] * sx, oy - box[1] * sy] };
  }

  function compositeMatrix(element, root, rootMatrix) {
    const chain = [];
    for (let current = element; current && current !== root; current = current.parentElement) chain.unshift(current);
    return chain.reduce((matrix, current) => multiply(matrix, transformMatrix(current.getAttribute("transform"))), multiply(rootMatrix, transformMatrix(root.getAttribute("transform"))));
  }

  function style(element, property, fallback = "") {
    for (let current = element; current?.getAttribute; current = current.parentElement) {
      const inline = String(current.getAttribute("style") || "").split(";").map((part) => part.split(":"));
      const declared = inline.find(([key]) => key.trim().toLowerCase() === property);
      if (declared) return declared.slice(1).join(":").trim();
      const value = current.getAttribute(property);
      if (value !== null && value !== "") return value;
    }
    return fallback;
  }

  function ownStyle(element, property, fallback = "") {
    const declared = String(element.getAttribute("style") || "").split(";").map((part) => part.split(":")).find(([key]) => key.trim().toLowerCase() === property);
    return declared ? declared.slice(1).join(":").trim() : element.getAttribute(property) ?? fallback;
  }

  function registerAuthoringLayoutManager(fabric) {
    if (!fabric?.LayoutManager || !fabric.FitContentLayout || !fabric.Point || !fabric.classRegistry) return null;
    if (authoringLayoutByFabric.has(fabric)) return authoringLayoutByFabric.get(fabric);
    const retained = Symbol("authoritative-pdf-authoring-frame");
    const expandedPlane = Symbol("current-declaring-plane-bounds");
    const currentPlaneExpansions = new WeakMap();
    const numeric = ["left", "top", "width", "height", "scaleX", "scaleY", "angle", "skewX", "skewY", "strokeWidth", "strokeMiterLimit", "strokeDashOffset", "padding"];
    const textNumeric = ["fontSize", "lineHeight", "charSpacing"];
    const values = [...numeric.filter(key => key !== "padding"), "originX", "originY", "flipX", "flipY", "strokeUniform", "strokeLineCap", "strokeLineJoin", "visible", "opacity", "absolutePositioned", "inverted", "fillRule"];
    const frameValues = ["width", "height", "scaleX", "scaleY", "angle", "skewX", "skewY", "originX", "originY", "flipX", "flipY", "strokeWidth", "strokeUniform", "opacity", "globalCompositeOperation"];
    function effects(object) {
      return [object.shadow || null, object.figureStudioAppearanceStack || null,
        object.figureStudioAppearanceMeta || null, object.filters || null, object.resizeFilter || null,
        object.backgroundColor || "", object.globalCompositeOperation || "source-over"];
    }
    function nonlocalEffects(object) {
      return Boolean(object.shadow || object.mask || object.figureStudioAppearanceStack || object.figureStudioAppearanceMeta
        || object.filters?.length || object.resizeFilter || object.backgroundColor
        || (object.globalCompositeOperation && object.globalCompositeOperation !== "source-over"));
    }
    function typographyGeometry(meta) {
      if (meta === null || meta === undefined) return null;
      if (typeof meta !== "object" || Array.isArray(meta)) return meta;
      const keys = ["schema", "range_runs", "baseline_shift_convention", "native_pdf_text_stream_mutated"];
      const own = Reflect.ownKeys(meta), descriptors = Object.getOwnPropertyDescriptors(meta);
      // Only the exact empty canonical shell record is layout-neutral. Keep
      // unknown fields, accessors and nonempty scientific formatting distinct.
      if (own.length !== keys.length || !keys.every(key => own.includes(key)
          && Object.hasOwn(descriptors[key], "value"))) return meta;
      const runs = descriptors.range_runs.value;
      return descriptors.schema.value === "figureStudio.typography.v2"
        && Array.isArray(runs) && runs.length === 0 && Reflect.ownKeys(runs).length === 1
        && descriptors.baseline_shift_convention.value === "positive-raises-negative-lowers"
        && descriptors.native_pdf_text_stream_mutated.value === false ? null : meta;
    }
    function listGeometry(meta) {
      if (meta === null || meta === undefined) return null;
      if (!meta || typeof meta !== "object" || Array.isArray(meta)) return meta;
      const keys = ["schema", "paragraphs", "last_text"], descriptors = Object.getOwnPropertyDescriptors(meta);
      if (Reflect.ownKeys(meta).length !== keys.length || !keys.every(key => Object.hasOwn(descriptors[key] || {}, "value"))) return meta;
      const paragraphs = descriptors.paragraphs.value, text = descriptors.last_text.value;
      return descriptors.schema.value === "figureStudio.paragraphLists.v1" && Array.isArray(paragraphs)
        && paragraphs.length === 1 && Reflect.ownKeys(paragraphs).length === 2
        && Object.getOwnPropertyDescriptor(paragraphs, "0")?.value === null
        && typeof text === "string" && !/[\r\n]/.test(text) ? null : meta;
    }
    function clipWorldGraph(object, ownerWorld) {
      if (!object) return { graph: graph(null), data: "null" };
      const rows = [], seen = new Set();
      function visit(row, worldOwner) {
        if (!row || seen.has(row)) throw new Error("Shared or cyclic clip ownership.");
        seen.add(row);
        const own = row.calcOwnMatrix(), world = row.absolutePositioned ? own : multiply(worldOwner, own);
        if (!world.every(Number.isFinite)) throw new Error("Nonfinite clip world.");
        rows.push([values.filter(key => !["left", "top"].includes(key)).map(key => row[key]),
          row.path || null, row.points || null, row.pathOffset || null, own.slice(0, 4), world, effects(row)]);
        for (const child of row.getObjects?.() || []) visit(child, world);
        if (row.clipPath) visit(row.clipPath, world);
        if (row.mask) visit(row.mask, world);
      }
      visit(object, ownerWorld);
      const authority = graph(object);
      return { graph: { ...authority, data: "world-clip-authority" }, data: JSON.stringify(rows) };
    }
    function* clipWorldGraphSteps(object, ownerWorld) {
      if (!object) return { graph: yield* graphSteps(null), data: "null" };
      const rows = [], seen = new Set();
      function* visit(row, worldOwner) {
        if (!row || seen.has(row)) throw new Error("Shared or cyclic clip ownership.");
        seen.add(row);
        yield row;
        const own = row.calcOwnMatrix(), world = row.absolutePositioned ? own : multiply(worldOwner, own);
        if (!world.every(Number.isFinite)) throw new Error("Nonfinite clip world.");
        rows.push([values.filter(key => !["left", "top"].includes(key)).map(key => row[key]),
          row.path || null, row.points || null, row.pathOffset || null, own.slice(0, 4), world, effects(row)]);
        for (const child of row.getObjects?.() || []) yield* visit(child, world);
        if (row.clipPath) yield* visit(row.clipPath, world);
        if (row.mask) yield* visit(row.mask, world);
      }
      yield* visit(object, ownerWorld);
      const authority = yield* graphSteps(object);
      yield object;
      return { graph: { ...authority, data: "world-clip-authority" }, data: JSON.stringify(rows) };
    }
    function sameWorldClip(left, right) {
      return left && right && left.data === right.data && sameGraph(left.graph, right.graph);
    }
    function graph(object) {
      if (!object) return { refs: [], links: [], data: "null" };
      const refs = [], links = [], rows = [], seen = new Set();
      function visit(row) {
        if (!row || seen.has(row)) return;
        seen.add(row); refs.push(row);
        if (numeric.some(key => row[key] !== undefined && !Number.isFinite(row[key]))) throw new Error("Nonfinite geometry.");
        if (typeof row.text === "string" && textNumeric.some(key => !Number.isFinite(row[key]))) throw new Error("Nonfinite text inputs.");
        const own = row.calcOwnMatrix?.(), center = row.getRelativeCenterPoint?.();
        if ((own && !own.every(Number.isFinite)) || (center && ![center.x, center.y].every(Number.isFinite))) throw new Error("Nonfinite affine geometry.");
        const children = Array.from(row.getObjects?.() || []);
        links.push({ group: row.group, parent: row.parent, children, clip: row.clipPath, mask: row.mask, source: row.pdfTextSource });
        rows.push([values.map(key => row[key]), row.path || null, row.points || null,
          row.pathOffset || null, own || null, center ? [center.x, center.y] : null, row.isStrokeAccountedForInDimensions?.(),
          effects(row), typeof row.text === "string" ? [row.text, row.styles || null, row.fontFamily, row.fontSize,
            row.fontWeight, row.fontStyle, row.textAlign, row.lineHeight, row.charSpacing, row.direction,
            typographyGeometry(row.figureStudioTypographyMeta), listGeometry(row.figureStudioListMeta), row.pdfTextAuthoringFrame || null, row.pdfTextAuthoringPlane || null, row.pdfTextSource || null] : null,
          children.length, Boolean(row.clipPath), Boolean(row.mask)]);
        children.forEach(visit); visit(row.clipPath); visit(row.mask);
      }
      visit(object);
      return { refs, links, data: JSON.stringify(rows) };
    }
    function* graphSteps(object) {
      if (!object) return { refs: [], links: [], data: "null" };
      const refs = [], links = [], rows = [], seen = new Set();
      function* visit(row) {
        if (!row || seen.has(row)) return;
        seen.add(row); refs.push(row);
        yield row;
        if (numeric.some(key => row[key] !== undefined && !Number.isFinite(row[key]))) throw new Error("Nonfinite geometry.");
        if (typeof row.text === "string" && textNumeric.some(key => !Number.isFinite(row[key]))) throw new Error("Nonfinite text inputs.");
        const own = row.calcOwnMatrix?.(), center = row.getRelativeCenterPoint?.();
        if ((own && !own.every(Number.isFinite)) || (center && ![center.x, center.y].every(Number.isFinite))) throw new Error("Nonfinite affine geometry.");
        const children = Array.from(row.getObjects?.() || []);
        links.push({ group: row.group, parent: row.parent, children, clip: row.clipPath, mask: row.mask, source: row.pdfTextSource });
        rows.push([values.map(key => row[key]), row.path || null, row.points || null,
          row.pathOffset || null, own || null, center ? [center.x, center.y] : null, row.isStrokeAccountedForInDimensions?.(),
          effects(row), typeof row.text === "string" ? [row.text, row.styles || null, row.fontFamily, row.fontSize,
            row.fontWeight, row.fontStyle, row.textAlign, row.lineHeight, row.charSpacing, row.direction,
            typographyGeometry(row.figureStudioTypographyMeta), listGeometry(row.figureStudioListMeta), row.pdfTextAuthoringFrame || null, row.pdfTextAuthoringPlane || null, row.pdfTextSource || null] : null,
          children.length, Boolean(row.clipPath), Boolean(row.mask)]);
        for (const child of children) yield* visit(child);
        yield* visit(row.clipPath); yield* visit(row.mask);
      }
      yield* visit(object);
      yield object;
      return { refs, links, data: JSON.stringify(rows) };
    }
    function sameGraph(left, right) {
      return Boolean(left && right && left.data === right.data && left.refs.length === right.refs.length
        && left.refs.every((object, index) => object === right.refs[index])
        && left.links.every((row, index) => {
          const other = right.links[index];
          return row.group === other.group && row.parent === other.parent && row.clip === other.clip && row.mask === other.mask
            && row.source === other.source && row.children.length === other.children.length
            && row.children.every((child, at) => child === other.children[at]);
        }));
    }
    function geometry(object, ancestry = new Set()) {
      if (ancestry.has(object)) return null;
      const ancestors = new Set(ancestry); ancestors.add(object);
      if (numeric.some(key => object[key] !== undefined && !Number.isFinite(object[key]))) return null;
      if (typeof object.text === "string" && textNumeric.some(key => !Number.isFinite(object[key]))) return null;
      const inputs = typeof object.text === "string" ? JSON.stringify([object.text, object.fontFamily, object.fontSize,
        object.fontWeight, object.fontStyle, object.textAlign, object.lineHeight, object.charSpacing, object.direction,
        object.styles || null, typographyGeometry(object.figureStudioTypographyMeta)]) : null;
      return { data: JSON.stringify([values.map(key => object[key]), object.path || null, object.points || null,
          typeof object.text === "string" ? [object.text, object.fontFamily, object.fontSize, object.fontWeight,
            object.fontStyle, object.textAlign, object.lineHeight, object.charSpacing, object.direction,
            object.styles || null, typographyGeometry(object.figureStudioTypographyMeta), listGeometry(object.figureStudioListMeta), object.pdfTextAuthoringFrame || null, object.pdfTextAuthoringPlane || null] : null,
          effects(object)]),
        // The explicit rectangle display class retains native Path geometry.
        // Its in-place import promotion must keep the same qualified UI drag
        // path; the remaining source, clip, effect and graph checks still apply.
        translation: (object.constructor === fabric.Path || isNativeRectangleDisplayPath(object, { fabric }))
          && typeof object.pdfSourceId === "string" && object.pdfSourceId
          && object.importMeta?.mimeType === "application/pdf" && !object.clipPath && !object.mask
          && !nonlocalEffects(object) ? JSON.stringify([
            values.filter(key => key !== "left" && key !== "top").map(key => object[key]),
            object.path, object.pathOffset, object.points || null, object.pdfSourceId, object.pdfSourcePageNumber,
            effects(object)
          ], (_key, value) => typeof value === "number" && Object.is(value, -0) ? { negativeZero: true } : value) : null,
        clip: graph(object.clipPath), worldClip: clipWorldGraph(object.clipPath, object.calcTransformMatrix()), mask: graph(object.mask), subtree: graph(object), effects: JSON.stringify(effects(object)),
        owner: object.group, parent: object.parent, manager: object.layoutManager, strategy: object.layoutManager?.strategy,
        children: Array.from(object.getObjects?.() || []).map(child => ({ ref: child, geometry: geometry(child, ancestors) })),
        sourceRef: object.pdfTextSource, sourceData: JSON.stringify(object.pdfTextSource || null), inputs,
        linear: JSON.stringify([object.calcOwnMatrix().slice(0, 4), object.originX, object.originY, object.flipX, object.flipY,
          object.scaleX, object.scaleY, object.angle, object.skewX, object.skewY]) };
    }
    function* childrenGeometrySteps(object, ancestry) {
      const children = [];
      for (const child of Array.from(object.getObjects?.() || [])) children.push({ ref: child, geometry: yield* geometrySteps(child, ancestry) });
      return children;
    }
    function* geometrySteps(object, ancestry = new Set()) {
      if (ancestry.has(object)) return null;
      const ancestors = new Set(ancestry); ancestors.add(object);
      yield object;
      if (numeric.some(key => object[key] !== undefined && !Number.isFinite(object[key]))) return null;
      if (typeof object.text === "string" && textNumeric.some(key => !Number.isFinite(object[key]))) return null;
      const inputs = typeof object.text === "string" ? JSON.stringify([object.text, object.fontFamily, object.fontSize,
        object.fontWeight, object.fontStyle, object.textAlign, object.lineHeight, object.charSpacing, object.direction,
        object.styles || null, typographyGeometry(object.figureStudioTypographyMeta)]) : null;
      return { data: JSON.stringify([values.map(key => object[key]), object.path || null, object.points || null,
          typeof object.text === "string" ? [object.text, object.fontFamily, object.fontSize, object.fontWeight,
            object.fontStyle, object.textAlign, object.lineHeight, object.charSpacing, object.direction,
            object.styles || null, typographyGeometry(object.figureStudioTypographyMeta), listGeometry(object.figureStudioListMeta), object.pdfTextAuthoringFrame || null, object.pdfTextAuthoringPlane || null] : null,
          effects(object)]),
        // The explicit rectangle display class retains native Path geometry.
        // Its in-place import promotion must keep the same qualified UI drag
        // path; the remaining source, clip, effect and graph checks still apply.
        translation: (object.constructor === fabric.Path || isNativeRectangleDisplayPath(object, { fabric }))
          && typeof object.pdfSourceId === "string" && object.pdfSourceId
          && object.importMeta?.mimeType === "application/pdf" && !object.clipPath && !object.mask
          && !nonlocalEffects(object) ? JSON.stringify([
            values.filter(key => key !== "left" && key !== "top").map(key => object[key]),
            object.path, object.pathOffset, object.points || null, object.pdfSourceId, object.pdfSourcePageNumber,
            effects(object)
          ], (_key, value) => typeof value === "number" && Object.is(value, -0) ? { negativeZero: true } : value) : null,
        clip: yield* graphSteps(object.clipPath), worldClip: yield* clipWorldGraphSteps(object.clipPath, object.calcTransformMatrix()), mask: yield* graphSteps(object.mask), subtree: yield* graphSteps(object), effects: JSON.stringify(effects(object)),
        owner: object.group, parent: object.parent, manager: object.layoutManager, strategy: object.layoutManager?.strategy,
        children: yield* childrenGeometrySteps(object, ancestors),
        sourceRef: object.pdfTextSource, sourceData: JSON.stringify(object.pdfTextSource || null), inputs,
        linear: JSON.stringify([object.calcOwnMatrix().slice(0, 4), object.originX, object.originY, object.flipX, object.flipY,
          object.scaleX, object.scaleY, object.angle, object.skewX, object.skewY]) };
    }
    function sameGeometry(left, right) {
      return Boolean(left && right && left.owner === right.owner && left.parent === right.parent
        && left.manager === right.manager && left.strategy === right.strategy && left.data === right.data && left.sourceRef === right.sourceRef && left.sourceData === right.sourceData
        && sameGraph(left.clip, right.clip) && sameGraph(left.mask, right.mask)
        && ((!left.subtree && !right.subtree) || sameGraph(left.subtree, right.subtree)));
    }
    function frame(target) {
      const linear = target.calcTransformMatrix().slice(0, 4);
      if (!linear.every(Number.isFinite) || frameValues.some(key => typeof target[key] === "number" && !Number.isFinite(target[key]))) return null;
      return { data: JSON.stringify([frameValues.map(key => target[key]), linear, effects(target)]),
        clip: graph(target.clipPath), mask: graph(target.mask) };
    }
    function* frameSteps(target) {
      yield target;
      const linear = target.calcTransformMatrix().slice(0, 4);
      if (!linear.every(Number.isFinite) || frameValues.some(key => typeof target[key] === "number" && !Number.isFinite(target[key]))) return null;
      return { data: JSON.stringify([frameValues.map(key => target[key]), linear, effects(target)]),
        clip: yield* graphSteps(target.clipPath), mask: yield* graphSteps(target.mask) };
    }
    function sourceText(object) {
      const TextClass = classByFabric.get(fabric);
      return Boolean(TextClass && object instanceof TextClass && object.pdfTextSource && typeof object.text === "string");
    }
    function strictlyInside(object, target) {
      // Match native LayoutStrategy's current pen/affine extents. No cached
      // aCoords, scene-space inverse roundtrip, epsilon or changed source path.
      if (object.group !== target || object.parent !== target || nonlocalEffects(object) || object.path
          || listGeometry(object.figureStudioListMeta) !== null || typographyGeometry(object.figureStudioTypographyMeta) !== null) return false;
      // Stock uniform-stroke bounds may have negative support components under
      // reflected/rotated owner transforms. Do not use them as ink authority.
      if (object.strokeUniform && object.strokeWidth !== 0) return false;
      if (!(target.width > 0 && target.height > 0) || nonlocalEffects(target)) return false;
      const includeStroke = !object.isStrokeAccountedForInDimensions();
      const uniform = object.strokeUniform && includeStroke
        ? fabric.util.sendVectorToPlane(new fabric.Point(object.strokeWidth, object.strokeWidth), undefined, target.calcTransformMatrix())
        : new fabric.Point(0, 0);
      const stroke = !object.strokeUniform && includeStroke ? object.strokeWidth : 0;
      let center = object.getRelativeCenterPoint();
      const paint = object._pdfPaintOffset?.();
      if (object.pdfTextAuthoringFrame && (!paint || !object._pdfPaintFrameSupported?.())) return false;
      if (paint) center = center.add(fabric.util.transformPoint(new fabric.Point(paint.x, paint.y), object.calcOwnMatrix(), true));
      const half = fabric.util.sizeAfterTransform(object.width + stroke, object.height + stroke,
        fabric.util.multiplyTransformMatrixArray([object.calcOwnMatrix()], true)).add(uniform).scalarDivide(2);
      const first = center.subtract(half), second = center.add(half);
      return [first.x, first.y, second.x, second.y].every(Number.isFinite)
        && Math.min(first.x, second.x) > -target.width / 2 && Math.max(first.x, second.x) < target.width / 2
        && Math.min(first.y, second.y) > -target.height / 2 && Math.max(first.y, second.y) < target.height / 2;
    }
    function supportedOwner(object) {
      const Isolated = groupClassByFabric.get(fabric);
      let Linear;
      try { Linear = fabric.classRegistry.getClass("PdfLinearFitContentLayout"); } catch (_) {}
      return object.constructor === fabric.Group && object.layoutManager?.strategy?.constructor === fabric.FitContentLayout
        || Boolean(Isolated && Linear && object.constructor === Isolated && object.layoutManager?.strategy?.constructor === Linear)
        || currentPlaneOwner(object);
    }
    function currentPlaneOwner(object) {
      const Current = currentPlaneGroupByFabric.get(fabric);
      let Linear;
      try { Linear = fabric.classRegistry.getClass("PdfLinearFitContentLayout"); } catch (_) {}
      return Boolean(Current && Linear && object.constructor === Current
        && object.layoutManager?.constructor === PdfAuthoringLayoutManager
        && object.layoutManager.strategy.constructor === Linear
        && object.originX === "center" && object.originY === "center"
        && object.strokeWidth === 0 && object.opacity === 1 && !nonlocalEffects(object));
    }
    function currentMemberBounds(object, target) {
      if (object.group !== target || object.parent !== target || nonlocalEffects(object)
          || object.strokeUniform && object.strokeWidth !== 0) return null;
      const Text = classByFabric.get(fabric);
      const Path = typeof registerCurrentPlanePathClass === "function" ? registerCurrentPlanePathClass(fabric) : null;
      const Current = currentPlaneGroupByFabric.get(fabric), Isolated = groupClassByFabric.get(fabric);
      if (!isNativeRectangleDisplayPath(object, { fabric })
          && ![fabric.Path, fabric.Rect, fabric.Group, Isolated, Current, Text, Path].filter(Boolean).includes(object.constructor)) return null;
      let local;
      if (Text && object.constructor === Text && Text.prototype._pdfCurrentNativePlane) {
        const plane = Text.prototype._pdfCurrentNativePlane.call(object);
        if (plane) local = Text.prototype._pdfCurrentPlaneBounds.call(object, plane);
        else if (object.pdfTextSource?.currentNativeGlyphPlanes || object.pdfTextAuthoringPlane) return null;
      } else if (Path && object.constructor === Path) {
        const bounds = Path.prototype._currentPlaneBounds.call(object);
        if (bounds) local = { left: bounds.left, top: bounds.top, right: bounds.left + bounds.width, bottom: bounds.top + bounds.height };
      }
      const includeStroke = !object.isStrokeAccountedForInDimensions();
      const stroke = !object.strokeUniform && includeStroke ? object.strokeWidth : 0;
      const own = object.calcOwnMatrix();
      if (!own.every(Number.isFinite)) return null;
      let points;
      if (local) {
        if (![local.left, local.top, local.right, local.bottom].every(Number.isFinite)) return null;
        const halfStroke = stroke / 2;
        points = [[local.left - halfStroke, local.top - halfStroke], [local.right + halfStroke, local.top - halfStroke],
          [local.left - halfStroke, local.bottom + halfStroke], [local.right + halfStroke, local.bottom + halfStroke]]
          .map(([x, y]) => fabric.util.transformPoint(new fabric.Point(x, y), own));
      } else {
        if (Text && object.constructor === Text && !Text.prototype._sourceLayout.call(object)
            && !Text.prototype._pdfPaintFrameAnchor.call(object)) return null;
        // Legacy centred text has no literal baseline paint plane. Keep its
        // rotated-world transition on the existing native route; current
        // declared glyph planes above carry their actual local paint support.
        if (Text && object.constructor === Text && !Text.prototype._sourceLayout.call(object)) {
          const world = object.calcTransformMatrix();
          if (world[1] !== 0 || world[2] !== 0) return null;
        }
        let center = object.getRelativeCenterPoint();
        const paint = Text && object.constructor === Text ? Text.prototype._pdfPaintOffset.call(object) : null;
        if (object.pdfTextAuthoringFrame && (!paint || !Text?.prototype._pdfPaintFrameSupported.call(object))) return null;
        if (paint) center = center.add(fabric.util.transformPoint(new fabric.Point(paint.x, paint.y), own, true));
        const half = fabric.util.sizeAfterTransform(object.width + stroke, object.height + stroke,
          fabric.util.multiplyTransformMatrixArray([own], true)).scalarDivide(2);
        points = [center.subtract(half), center.add(half)];
      }
      const xs = points.map(p => p.x), ys = points.map(p => p.y);
      return points.every(p => Number.isFinite(p.x) && Number.isFinite(p.y))
        ? { left: Math.min(...xs), right: Math.max(...xs), top: Math.min(...ys), bottom: Math.max(...ys) } : null;
    }
    function currentPlaneContains(object, target) {
      const bounds = currentMemberBounds(object, target);
      return Boolean(bounds && target.width > 0 && target.height > 0
        && bounds.left >= -target.width / 2 && bounds.right <= target.width / 2
        && bounds.top >= -target.height / 2 && bounds.bottom <= target.height / 2);
    }
    function currentPlaneExtent(target, members) {
      if (!currentPlaneOwner(target) || !geometry(target)) return null;
      let x = target.width / 2, y = target.height / 2;
      for (const object of members) {
        const bounds = currentMemberBounds(object, target);
        if (!bounds) return null;
        x = Math.max(x, Math.abs(bounds.left), Math.abs(bounds.right));
        y = Math.max(y, Math.abs(bounds.top), Math.abs(bounds.bottom));
      }
      const width = 2 * x, height = 2 * y;
      return [width, height].every(v => Number.isFinite(v) && v > 0 && v <= 1e8) ? { width, height } : null;
    }
    function certifiedPlaneExpansion(object, after, before) {
      const proof = currentPlaneExpansions.get(object);
      return Boolean(proof && currentPlaneOwner(object) && proof.manager === object.layoutManager
        && proof.beforeData === before.data && proof.afterData === after.data
        && proof.own.every((value, index) => Object.is(value, object.calcOwnMatrix()[index]))
        && proof.width === object.width && proof.height === object.height
        && sameGraph(proof.clip, graph(object.clipPath)) && sameGraph(proof.mask, graph(object.mask)));
    }
    function compatibleReflow(object, after, before, context) {
      if (sameGeometry(after, before)) return true;
      if (!after || !before || after.owner !== before.owner || after.parent !== before.parent
          || after.manager !== before.manager || after.strategy !== before.strategy) return false;
      const translating = ["object_modifying", "object_modified"].includes(context.type)
        && ["moving", "modified"].includes(context.trigger)
        && context.e?.transform?.action === "drag";
      if (translating && context.e.transform.target === object && after.translation && after.translation === before.translation
          && after.linear === before.linear && currentPlaneContains(object, object.group)) return true;
      // A retained descendant translation can bubble through the unchanged
      // native parent frames without recentering every neighboring mark.
      if (!(context.type === "object_modifying" && context.trigger === "changed") && !translating) return false;
      if (sourceText(object)) return !translating && after.inputs !== before.inputs && after.linear === before.linear
        && after.sourceRef === before.sourceRef && after.sourceData === before.sourceData
        && sameWorldClip(after.worldClip, before.worldClip) && sameGraph(after.mask, before.mask)
        && after.effects === before.effects && (strictlyInside(object, object.group)
          || currentPlaneOwner(object.group) && Boolean(currentMemberBounds(object, object.group)));
      return supportedOwner(object) && object.layoutManager instanceof PdfAuthoringLayoutManager
        && (after.data === before.data || certifiedPlaneExpansion(object, after, before)
          && (currentPlaneContains(object, object.group)
            || currentPlaneOwner(object.group) && Boolean(currentMemberBounds(object, object.group)))) && after.linear === before.linear
        && after.sourceRef === before.sourceRef && after.sourceData === before.sourceData
        && sameGraph(after.clip, before.clip) && sameGraph(after.mask, before.mask)
        && after.effects === before.effects && after.children.length === before.children.length
        && after.children.every((row, index) => row.ref === before.children[index].ref
          && compatibleReflow(row.ref, row.geometry, before.children[index].geometry, context));
    }
    class PdfAuthoringLayoutManager extends fabric.LayoutManager {
      static type = "PdfAuthoringLayoutManager";
      constructor(strategy = new fabric.FitContentLayout()) {
        super(strategy);
        this._authoringMembers = null;
        this._authoringGeometry = null;
        this._authoringFrame = null;
      }
      *_captureAuthoringLayout(target) {
        try {
          const members = Array.from(target.getObjects()), snapshots = [];
          for (const object of members) snapshots.push(yield* geometrySteps(object));
          return { members, geometry: snapshots, frame: yield* frameSteps(target) };
        } catch (_) {
          return { members: null, geometry: null, frame: null };
        }
      }
      _publishAuthoringLayout(snapshot) {
        this._authoringMembers = snapshot.members;
        this._authoringGeometry = snapshot.geometry;
        this._authoringFrame = snapshot.frame;
      }
      _seed(target) {
        try {
          const members = Array.from(target.getObjects());
          const snapshots = members.map(object => geometry(object));
          const ownerFrame = frame(target);
          this._publishAuthoringLayout({ members, geometry: snapshots, frame: ownerFrame });
        } catch (_) {
          this._publishAuthoringLayout({ members: null, geometry: null, frame: null });
        }
      }
      subscribeTargets(context) {
        super.subscribeTargets(context);
        // Native Group.fromObject restores fields under a Noop manager, then
        // subscribes the reconstructed manager without an initialization fit.
        if (!this._authoringMembers && context.target) this._seed(context.target);
      }
      getLayoutResult(context) {
        const target = context.target;
        try {
          const members = Array.from(target.getObjects());
          const eligible = supportedOwner(target) && target.layoutManager === this
            && context.strategy === this.strategy
            && !["initialization", "added", "removed"].includes(context.type) && !context.overrides
            && this._authoringMembers && members.length === this._authoringMembers.length
            && members.every((object, index) => object === this._authoringMembers[index] && object.group === target && object.parent === target)
            && sameGeometry(frame(target), this._authoringFrame);
          if (eligible) {
            const current = members.map(object => geometry(object));
            if (current.every(Boolean) && this._authoringGeometry.every(Boolean)
                && members.every((object, index) => compatibleReflow(object, current[index], this._authoringGeometry[index], context))) {
              const extent = currentPlaneOwner(target) ? currentPlaneExtent(target, members) : null;
              if (currentPlaneOwner(target) && !extent) return super.getLayoutResult(context);
              const center = target.getRelativeCenterPoint();
              return { result: { center, size: new fabric.Point(extent?.width || target.width, extent?.height || target.height) },
                prevCenter: center, nextCenter: center, offset: new fabric.Point(0, 0), [retained]: true,
                [expandedPlane]: extent && (extent.width !== target.width || extent.height !== target.height) ? extent : null };
            }
          }
        } catch (_) { /* Unsupported geometry uses the unchanged stock path. */ }
        return super.getLayoutResult(context);
      }
      commitLayout(context, result) {
        if (result[retained]) {
          const extent = result[expandedPlane], target = context.target;
          if (extent) {
            const before = geometry(target), own = target.calcOwnMatrix().slice(), width = target.width, height = target.height;
            const clip = graph(target.clipPath), mask = graph(target.mask);
            target.set({ width: extent.width, height: extent.height });
            const after = geometry(target);
            if (!currentPlaneOwner(target) || !own.every((value, index) => Object.is(value, target.calcOwnMatrix()[index]))
                || !sameGraph(clip, graph(target.clipPath)) || !sameGraph(mask, graph(target.mask))
                || !target.getObjects().every(object => currentPlaneContains(object, target))) {
              target.set({ width, height });
              const stock = super.getLayoutResult(context);
              if (stock) super.commitLayout(context, stock);
              return;
            }
            currentPlaneExpansions.set(target, { manager: this, beforeData: before.data, afterData: after.data,
              own, width: target.width, height: target.height, clip, mask });
          }
          // Adding zero to every pose or recomposing the center is observably
          // lossy for canonical Float64 fields. Keep all pose fields untouched.
          context.target.set("dirty", true);
          context.target.setCoords();
          return;
        }
        return super.commitLayout(context, result);
      }
      onAfterLayout(context, result) {
        super.onAfterLayout(context, result);
        this._seed(context.target);
      }
      toObject() { return { type: PdfAuthoringLayoutManager.type, strategy: this.strategy.constructor.type }; }
    }
    fabric.classRegistry.setClass(PdfAuthoringLayoutManager);
    authoringLayoutByFabric.set(fabric, PdfAuthoringLayoutManager);
    return PdfAuthoringLayoutManager;
  }

  function createAuthoringLayoutManager(objects, { fabric, isPdfSourceObject } = {}) {
    if (!fabric || typeof isPdfSourceObject !== "function") return null;
    const pending = Array.from(objects || []), seen = new Set();
    let source = false;
    while (pending.length && !source) {
      const object = pending.pop();
      if (!object || seen.has(object)) continue;
      seen.add(object);
      source = Boolean(isPdfSourceObject(object));
      if (!source) pending.push(...Array.from(object.getObjects?.() || []));
    }
    if (!source) return null;
    const Manager = registerAuthoringLayoutManager(fabric);
    return Manager ? new Manager() : null;
  }

  function finalizeImportedAuthoringLayout(objects, options = {}) {
    const steps = importedAuthoringLayoutSteps(objects, options);
    let step;
    do { step = steps.next(); } while (!step.done);
    return step.value;
  }

  // Only unpublished, caller-owned import graphs may cross task boundaries.
  // Editing and restoration deliberately retain the synchronous entry above.
  async function finalizeImportedAuthoringLayoutAsync(objects, options = {}) {
    const roots = Array.from(objects || []), steps = importedAuthoringLayoutSteps(roots, { ...options, cooperative: true });
    const now = () => globalThis.performance?.now?.() ?? Date.now();
    const maxSliceMs = Number.isFinite(options.maxSliceMs) ? Math.max(0, options.maxSliceMs) : 16;
    const yieldToUi = options.yieldToUi || (() => new Promise(resolve => setTimeout(resolve, 0)));
    const current = object => {
      if (options.signal?.aborted) {
        const error = new Error("PDF authoring layout capture was cancelled."); error.name = "AbortError"; throw error;
      }
      if (object?.canvas) throw new Error("Cooperative PDF layout capture requires detached import objects.");
    };
    const capturedObjects = new Set();
    const detached = () => {
      for (const object of roots) current(object);
      for (const object of capturedObjects) current(object);
    };
    let started = now(), visited = 0, uiYieldCount = 0;
    try {
      detached();
      for (;;) {
        const step = steps.next();
        current(step.value);
        if (step.done) { detached(); return step.value; }
        if (step.value && typeof step.value === "object") capturedObjects.add(step.value);
        visited++;
        const elapsed = now() - started;
        if (elapsed < maxSliceMs) continue;
        options.onProgress?.({ stage: "authoring-layout", completed: visited, uiYieldCount: ++uiYieldCount, elapsedMs: elapsed });
        await yieldToUi();
        current(step.value);
        detached();
        started = now();
      }
    } finally {
      steps.return();
    }
  }

  function* importedAuthoringLayoutSteps(objects, { fabric, cooperative = false } = {}) {
    // Import construction attaches shared clips and adopts nested groups after
    // their native initialization layouts. Capture that completed CURRENT
    // hierarchy once; editing and restoration keep their existing guards.
    const Manager = authoringLayoutByFabric.get(fabric), Isolated = groupClassByFabric.get(fabric);
    if (!Manager) return 0;
    let Linear;
    try { Linear = fabric.classRegistry.getClass("PdfLinearFitContentLayout"); } catch (_) {}
    const pending = Array.from(objects || []), seen = new Set(), completed = [];
    let captured = 0;
    while (pending.length) {
      const object = pending.pop();
      if (!object || seen.has(object)) continue;
      seen.add(object);
      yield object;
      const children = Array.from(object.getObjects?.() || []);
      pending.push(...children.filter(child => child.group === object && child.parent === object));
      completed.push({ object, children });
    }
    // Finalize descendants first, after all parents and shared clips exist.
    for (const { object, children } of completed.reverse()) {
      const manager = object.layoutManager;
      const owner = object.constructor === fabric.Group && manager?.strategy?.constructor === fabric.FitContentLayout
        || object.constructor === Isolated && Linear && manager?.strategy?.constructor === Linear
        || object.constructor === currentPlaneGroupByFabric.get(fabric) && Linear && manager?.strategy?.constructor === Linear;
      if (owner && manager?.constructor === Manager && children.length
          && children.every(child => child.group === object && child.parent === object && manager._subscriptions?.has(child))) {
        if (cooperative) {
          const snapshot = yield* manager._captureAuthoringLayout(object);
          yield object;
          manager._publishAuthoringLayout(snapshot);
        } else manager._seed(object);
        captured++;
      }
    }
    return captured;
  }

  function registerCurrentPlaneGroupClass(fabric, registeredBase) {
    if (currentPlaneGroupByFabric.has(fabric)) return currentPlaneGroupByFabric.get(fabric);
    const Base = registeredBase || registerGroupClass(fabric);
    if (currentPlaneGroupByFabric.has(fabric)) return currentPlaneGroupByFabric.get(fabric);
    class PdfCurrentPlaneGroup extends Base {
      static type = "PdfCurrentPlaneGroup";
    }
    fabric.classRegistry.setClass(PdfCurrentPlaneGroup);
    currentPlaneGroupByFabric.set(fabric, PdfCurrentPlaneGroup);
    return PdfCurrentPlaneGroup;
  }

  function registerGroupClass(fabric) {
    preserveRenderPolicy(fabric);
    registerAuthoringLayoutManager(fabric);
    if (groupClassByFabric.has(fabric)) return groupClassByFabric.get(fabric);
    const LinearLayout = fabric.FitContentLayout && fabric.LayoutManager ? class PdfLinearFitContentLayout extends fabric.FitContentLayout {
      static type = "PdfLinearFitContentLayout";
      calcBoundingBox(objects, context) {
        if (context.type === "imperative" && context.overrides) return context.overrides;
        if (!objects.length) return;
        let left = Infinity, top = Infinity, right = -Infinity, bottom = -Infinity;
        const target = context.target, util = fabric.util;
        for (const object of objects) {
          // Use Fabric LayoutStrategy's exact per-object stroke/transform bounds
          // and arithmetic. Stream its corners instead of copying every prior
          // corner into an ever-growing array during PDF group construction.
          const plane = object.group && object.group !== target ? util.calcPlaneChangeMatrix(object.group.calcTransformMatrix(), target.calcTransformMatrix()) : null;
          const center = plane ? object.getRelativeCenterPoint().transform(plane) : object.getRelativeCenterPoint();
          const includeStroke = !object.isStrokeAccountedForInDimensions();
          const uniformStroke = object.strokeUniform && includeStroke ? util.sendVectorToPlane(new fabric.Point(object.strokeWidth, object.strokeWidth), undefined, target.calcTransformMatrix()) : new fabric.Point(0, 0);
          const stroke = !object.strokeUniform && includeStroke ? object.strokeWidth : 0;
          const half = util.sizeAfterTransform(object.width + stroke, object.height + stroke, util.multiplyTransformMatrixArray([plane, object.calcOwnMatrix()], true)).add(uniformStroke).scalarDivide(2);
          const first = center.subtract(half), second = center.add(half);
          left = Math.min(left, first.x, second.x); top = Math.min(top, first.y, second.y);
          right = Math.max(right, first.x, second.x); bottom = Math.max(bottom, first.y, second.y);
        }
        const size = new fabric.Point(right - left, bottom - top), center = new fabric.Point(left, top).add(size.scalarDivide(2));
        return context.type === "initialization" ? { center, size: this.getInitialSize(context, { size, center }), relativeCorrection: new fabric.Point(0, 0) } : { center: center.transform(target.calcOwnMatrix()), size };
      }
    } : null;
    if (LinearLayout) fabric.classRegistry?.setClass(LinearLayout);
    class PdfIsolatedGroup extends fabric.Group {
      static type = "PdfIsolatedGroup";
      constructor(objects = [], options = {}) {
        const Text = classByFabric.get(fabric), pending = Array.from(objects), seen = new Set();
        let containsText = false, bounded = true;
        while (pending.length) {
          const child = pending.pop();
          if (!child || seen.has(child)) continue;
          seen.add(child);
          if (seen.size > 512) { bounded = false; break; }
          containsText ||= Boolean(Text && child instanceof Text && child.pdfTextSource);
          pending.push(...Array.from(child.getObjects?.() || []));
        }
        const Manager = bounded && containsText ? registerAuthoringLayoutManager(fabric) : fabric.LayoutManager;
        super(objects, { ...(LinearLayout ? { layoutManager: new Manager(new LinearLayout()) } : {}), ...options });
        this._refreshPdfLocalCoordinates();
        this.on("layout:after", () => this._refreshPdfLocalCoordinates());
      }
      _shouldSetNestedCoords() { return false; }
      _refreshPdfLocalCoordinates() {
        // Fabric transforms cached parent-local aCoords into world coordinates
        // during hit testing. Ancestor movement/zoom does not change that cache.
        for (const object of this._objects) {
          object.aCoords = object.calcACoords();
          // Fabric hover checks enumerate controls even for an unselected
          // subtarget; Canvas.setActiveObject computes its actual controls.
          object.oCoords ||= {};
        }
      }
      setCoords() {
        super.setCoords();
        for (const active of this.canvas?.getActiveObjects?.() || []) {
          if (active !== this && active.isDescendantOf(this)) active.setCoords();
        }
      }
      // PDF transparency groups must composite once. Ordinary uncached Fabric
      // groups multiply opacity for each child, darkening overlapping strokes.
      _currentNativePlaneClip() {
        if (this.opacity !== 1 || this.shadow || this.mask || this.backgroundColor || this.filters?.length || this.resizeFilter
            || this.figureStudioAppearanceStack || this.figureStudioAppearanceMeta || this.globalCompositeOperation !== "source-over") return null;
        const Path = currentPlanePathClassByFabric.get(fabric), planes = [];
        const CurrentGroup = typeof registerCurrentPlaneGroupClass === "function" ? registerCurrentPlaneGroupClass(fabric) : null;
        let current = this.clipPath;
        for (let depth = 0; current && depth < 48; depth++) {
          if (current.clipPath || current.inverted || current.absolutePositioned || current.shadow || current.opacity !== 1
              || current.backgroundColor || current.mask || current.filters?.length || current.resizeFilter
              || current.figureStudioAppearanceStack || current.figureStudioAppearanceMeta
              || current.globalCompositeOperation !== "source-over"
              || current.calcOwnMatrix !== current.constructor.prototype.calcOwnMatrix
              || current.drawObject !== current.constructor.prototype.drawObject
              || current._render !== current.constructor.prototype._render) return null;
          if (![Path, fabric.Group, PdfIsolatedGroup, CurrentGroup].includes(current.constructor)) return null;
          const own = current.calcOwnMatrix();
          if (!own.every(value => Number.isFinite(value) && Math.abs(value) <= 1e8)) return null;
          planes.push(own);
          if (current.constructor === Path) {
            if (current._renderPathCommands !== Path.prototype._renderPathCommands
                || current._getOffsetTransform !== Path.prototype._getOffsetTransform) return null;
            const rows = current.path;
            if (!Array.isArray(rows) || rows.length !== 5 || rows[0][0] !== "M" || rows.at(-1)[0] !== "Z"
                || rows.slice(1, -1).some(row => row[0] !== "L") || rows.slice(0, -1).some(row => row.length !== 3 || !row.slice(1).every(Number.isFinite))
                || current.stroke && current.strokeWidth || typeof current.fill !== "string" || !["nonzero", "evenodd"].includes(current.fillRule)) return null;
            return { planes, path: current, rule: current.fillRule };
          }
          if (![fabric.Group, PdfIsolatedGroup, CurrentGroup].includes(current.constructor) || current._objects.length !== 1) return null;
          current = current._objects[0];
        }
        return null;
      }
      _pdfVectorClip() {
        if (this.opacity !== 1 || this.shadow || this.mask || this.backgroundColor || this.filters?.length || this.resizeFilter
            || this.figureStudioAppearanceStack || this.figureStudioAppearanceMeta
            || ![undefined, "source-over"].includes(this.globalCompositeOperation)) return null;
        return simpleNativeClip(this.clipPath, fabric);
      }
      drawObject(context, forClipping, cache) {
        const clip = !forClipping && this._currentNativePlaneClip();
        const vector = !forClipping && !clip && this._pdfVectorClip();
        if (!clip && !vector) return super.drawObject(context, forClipping, cache);
        context.save();
        try {
          if (vector) applySimpleNativeClip(context, vector, this, fabric);
          else {
            context.save();
            try { for (const matrix of clip.planes) context.transform(...matrix); clip.path._renderPathCommands(context); }
            finally { context.restore(); }
            context.clip(clip.rule);
          }
          this.__pdfCurrentNativeClipActive = true;
          return super.drawObject(context, forClipping, cache);
        } finally { this.__pdfCurrentNativeClipActive = false; context.restore(); }
      }
      _drawClipPath(context, clip, cache) { if (!this.__pdfCurrentNativeClipActive) return super._drawClipPath(context, clip, cache); }

      needsItsOwnCache() { return !this._currentNativePlaneClip() && !this._pdfVectorClip() && (this.opacity < 1 || super.needsItsOwnCache()); }
      toObject(properties = []) { return super.toObject([...properties, ...META_PROPS]); }
    }
    fabric.classRegistry?.setClass(PdfIsolatedGroup);
    groupClassByFabric.set(fabric, PdfIsolatedGroup);
    bindScenePaint(PdfIsolatedGroup, "group", ["render", "drawObject", "_render", "calcOwnMatrix", "calcTransformMatrix",
      "_currentNativePlaneClip", "_pdfVectorClip", "_drawClipPath", "needsItsOwnCache"], fabric);
    registerCurrentPlaneGroupClass(fabric, PdfIsolatedGroup);
    return PdfIsolatedGroup;
  }

  function rectangleBounds(path) {
    if (!Array.isArray(path) || ![5, 6].includes(path.length) || path[0][0] !== "M") return null;
    const explicitClose = path.at(-1)[0].toUpperCase() === "Z";
    const points = explicitClose ? path.slice(0, -1) : path;
    if (!explicitClose && points.length !== 5) return null;
    if (points.slice(1).some((part) => part[0] !== "L") || points.some((part) => part.length !== 3 || !part.slice(1).every(Number.isFinite))) return null;
    // Relative SVG commands can accumulate binary floating-point noise while
    // Fabric normalizes them. This tests geometry; no canonical point is changed.
    const equal = (a, b) => Math.abs(a - b) <= 1e-9;
    if (points.length === 5 && (!equal(points[0][1], points[4][1]) || !equal(points[0][2], points[4][2]))) return null;
    const corners = points.slice(0, 4), x = corners.map((point) => point[1]), y = corners.map((point) => point[2]);
    const left = Math.min(...x), top = Math.min(...y), right = Math.max(...x), bottom = Math.max(...y);
    if (!(right > left && bottom > top) || new Set(corners.map((point) => `${equal(point[1], left)},${equal(point[2], top)}`)).size !== 4) return null;
    if (corners.some((point, index) => ![left, right].some((x) => equal(x, point[1])) || ![top, bottom].some((y) => equal(y, point[2])) || (!equal(point[1], corners[(index + 1) % 4][1]) && !equal(point[2], corners[(index + 1) % 4][2])))) return null;
    return { left, top, width: right - left, height: bottom - top };
  }

  function exactRectangleBounds(path) {
    if (!rectangleBounds(path)) return null;
    const corners = path.slice(0, 4), x = new Set(corners.map(row => row[1])), y = new Set(corners.map(row => row[2]));
    if (x.size !== 2 || y.size !== 2 || new Set(corners.map(row => `${row[1]},${row[2]}`)).size !== 4) return null;
    if (corners.some((point, index) => point[1] !== corners[(index + 1) % 4][1] && point[2] !== corners[(index + 1) % 4][2])) return null;
    if (path[4][0] === "L" && (path[4][1] !== path[0][1] || path[4][2] !== path[0][2])) return null;
    return { left: Math.min(...x), right: Math.max(...x), top: Math.min(...y), bottom: Math.max(...y) };
  }

  function axisDeviceRectangle(matrix, bounds) {
    if (!matrix.every(Number.isFinite) || matrix[1] !== 0 || matrix[2] !== 0 || !matrix[0] || !matrix[3]) return null;
    const x = [matrix[0] * bounds.left + matrix[4], matrix[0] * bounds.right + matrix[4]];
    const y = [matrix[3] * bounds.top + matrix[5], matrix[3] * bounds.bottom + matrix[5]];
    if (![...x, ...y].every(value => Number.isFinite(value) && Math.abs(value) <= 1e8)) return null;
    return { left: Math.min(...x), right: Math.max(...x), top: Math.min(...y), bottom: Math.max(...y) };
  }

  function rectangleDeviceSpan(low, high) {
    // Opaque PDF rectangle coverage uses a whole-device-pixel span. Choose the
    // ceil-width span with greatest coverage; clip rectangles use outer bounds.
    // This follows CFX_RenderDevice::DrawPath's no-stroke rectangle branch:
    // https://pdfium.googlesource.com/pdfium/+/a644535827f8020fdf0a436eaa69dd9196262012/core/fxge/cfx_renderdevice.cpp
    let start = Math.floor(low), end = Math.ceil(high);
    const count = Math.max(1, Math.ceil(high - low));
    if (start === end) end++;
    if (end - start >= count + 1) {
      if (low - start > end - high) start++; else end--;
    }
    return [start, end];
  }

  function hardRectangle(clip) {
    if (!clip || clip.clipPath || clip.getObjects || clip.inverted || clip.absolutePositioned || clip.shadow || number(clip.opacity, 1) !== 1) return null;
    const type = String(clip.constructor?.type || clip.type).toLowerCase();
    if (type === "rect" && !clip.rx && !clip.ry && clip.width > 0 && clip.height > 0) return { left: -clip.width / 2, top: -clip.height / 2, width: clip.width, height: clip.height };
    const bounds = type === "path" && rectangleBounds(clip.path);
    return bounds ? { ...bounds, left: bounds.left - clip.pathOffset.x, top: bounds.top - clip.pathOffset.y } : null;
  }

  function simpleNativeClip(clip, fabric) {
    const layers = [], seen = new Set();
    for (let current = clip; current; current = current.clipPath) {
      if (seen.has(current) || layers.length >= 48) return null;
      seen.add(current);
      const clip = current;
      if (clip.inverted || clip.absolutePositioned || clip.shadow || clip.mask
          || clip.opacity !== 1 || clip.backgroundColor || clip.filters?.length || clip.resizeFilter
          || clip.figureStudioAppearanceStack || clip.figureStudioAppearanceMeta
          || ![undefined, "source-over"].includes(clip.globalCompositeOperation)) return null;
      const Class = clip.constructor;
      if (![fabric.Path, fabric.Rect].includes(Class) || clip._render !== Class.prototype._render
          || clip.drawObject !== Class.prototype.drawObject || clip.calcOwnMatrix !== Class.prototype.calcOwnMatrix) return null;
      const matrix = clip.calcOwnMatrix();
      if (!matrix.every(value => Number.isFinite(value) && Math.abs(value) <= 1e8)
          || matrix[0] * matrix[3] - matrix[1] * matrix[2] === 0) return null;
      if (Class === fabric.Path && clip._renderPathCommands === fabric.Path.prototype._renderPathCommands
          && clip.path?.length && clip.path.every(row => row.length === ({ M: 3, L: 3, C: 7, Q: 5, Z: 1 })[row[0]]
            && row.slice(1).every(Number.isFinite)) && ["nonzero", "evenodd"].includes(clip.fillRule)) {
        layers.push({ object: clip, matrix, path: true, rule: clip.fillRule });
      } else if (Class === fabric.Rect && !clip.rx && !clip.ry && clip.width > 0 && clip.height > 0
          && [clip.width, clip.height].every(Number.isFinite)) {
        layers.push({ object: clip, matrix, path: false, rule: "nonzero" });
      } else return null;
    }
    return layers.length ? { layers } : null;
  }

  function applySimpleNativeClip(context, clip, owner, fabric) {
    const matrices = [];
    for (const layer of clip.layers) {
      matrices.push(layer.matrix);
      context.beginPath();
      context.save();
      try {
        // Nested relative clip planes intersect. Restore only the transform
        // before committing each clip, so every intersection remains active.
        transformNativeClip(context, owner, matrices, fabric);
        if (layer.path) layer.object._renderPathCommands(context);
        else context.rect(-layer.object.width / 2, -layer.object.height / 2, layer.object.width, layer.object.height);
      } finally { context.restore(); }
      context.clip(layer.rule);
    }
  }

  function registerPathClass(fabric) {
    preserveRenderPolicy(fabric);
    if (pathClassByFabric.has(fabric)) return pathClassByFabric.get(fabric);
    if (!fabric.Path) throw new Error("Fabric editable paths are unavailable.");
    class PdfNativeRectClippedPath extends fabric.Path {
      static type = "PdfNativeRectClippedPath";
      _pdfDeviceRectangle(context) {
        if (this.constructor !== PdfNativeRectClippedPath || !this.pdfSourceId
            || this.pdfDisplayFillPolicy !== "pdf-opaque-axis-rectangle-device-pixels-v1"
            || this._render !== fabric.Path.prototype._render || this._renderPathCommands !== fabric.Path.prototype._renderPathCommands
            || this._renderPaintInOrder !== fabric.Path.prototype._renderPaintInOrder || this._renderFill !== fabric.Path.prototype._renderFill
            || this._setFillStyles !== fabric.Path.prototype._setFillStyles || this.hasStroke !== fabric.Path.prototype.hasStroke
            || this.drawObject !== PdfNativeRectClippedPath.prototype.drawObject || this._drawClipPath !== PdfNativeRectClippedPath.prototype._drawClipPath
            || this._nativeRectangle !== PdfNativeRectClippedPath.prototype._nativeRectangle
            || this.hasStroke() || typeof this.fill !== "string" || !/^#[0-9a-f]{6}$/i.test(this.fill) || this.opacity !== 1 || this.objectCaching !== false
            || this.shadow || this.mask || this.backgroundColor || this.filters?.length || this.resizeFilter
            || this.figureStudioAppearanceStack || this.figureStudioAppearanceMeta
            || ![undefined, "source-over"].includes(this.globalCompositeOperation)
            || context.globalAlpha !== 1 || context.globalCompositeOperation !== "source-over"
            || context.filter && context.filter !== "none"
            || context.shadowBlur || context.shadowOffsetX || context.shadowOffsetY
            || typeof context.getTransform !== "function") return null;
        let owner = this.group, depth = 0;
        while (owner) {
          if (++depth > 48 || owner.ownCaching || owner.clipPath || owner.opacity !== 1 || owner.shadow || owner.mask
              || owner.filters?.length || owner.resizeFilter || owner.figureStudioAppearanceStack || owner.figureStudioAppearanceMeta
              || ![undefined, "source-over"].includes(owner.globalCompositeOperation)) return null;
          owner = owner.group;
        }
        const bounds = exactRectangleBounds(this.path);
        if (!bounds) return null;
        const transform = context.getTransform(), matrix = [transform.a, transform.b, transform.c, transform.d, transform.e, transform.f];
        const device = axisDeviceRectangle(matrix, { left: bounds.left - this.pathOffset.x, right: bounds.right - this.pathOffset.x,
          top: bounds.top - this.pathOffset.y, bottom: bounds.bottom - this.pathOffset.y });
        if (!device) return null;
        let [left, right] = rectangleDeviceSpan(device.left, device.right), [top, bottom] = rectangleDeviceSpan(device.top, device.bottom);
        if (this.clipPath) {
          const clipBounds = this._nativeRectangle();
          if (!clipBounds || this.clipPath.constructor === fabric.Path && !exactRectangleBounds(this.clipPath.path)) return null;
          const clip = axisDeviceRectangle(multiply(matrix, this.clipPath.calcOwnMatrix()), {
            left: clipBounds.left, right: clipBounds.left + clipBounds.width,
            top: clipBounds.top, bottom: clipBounds.top + clipBounds.height });
          if (!clip) return null;
          left = Math.max(left, Math.floor(clip.left)); right = Math.min(right, Math.ceil(clip.right));
          top = Math.max(top, Math.floor(clip.top)); bottom = Math.min(bottom, Math.ceil(clip.bottom));
        }
        return { left, top, right, bottom };
      }
      _setStrokeStyles(context, object) {
        super._setStrokeStyles(context, object);
        // Native PDF canvases display very thin strokes at a minimum of one
        // device pixel. Keep the declared width in the object and all exports;
        // this qualified case changes only the current Canvas paint state.
        if (this.constructor !== PdfNativeRectClippedPath || object !== this
            || this.pdfDisplayStrokePolicy !== "pdf-minimum-isotropic-device-pixel-v1"
            || typeof this.stroke !== "string" || !this.stroke || /url\s*\(/i.test(this.stroke)
            || !Number.isFinite(this.strokeWidth) || this.strokeWidth <= 0 || this.strokeUniform
            || this.opacity !== 1 || this.strokeDashArray?.length || this.shadow || this.mask
            || this.filters?.length || this.resizeFilter || this.figureStudioAppearanceStack
            || this.figureStudioAppearanceMeta || ![undefined, "source-over"].includes(this.globalCompositeOperation)
            || typeof context.getTransform !== "function") return;
        const matrix = context.getTransform();
        if (matrix.b !== 0 || matrix.c !== 0 || !Number.isFinite(matrix.a) || !Number.isFinite(matrix.d)
            || matrix.a === 0 || Math.abs(matrix.a) !== Math.abs(matrix.d)) return;
        const minimum = 1 / Math.abs(matrix.a);
        if (Number.isFinite(minimum)) context.lineWidth = Math.max(context.lineWidth, minimum);
      }
      _nativeRectangle() {
        const proof = this.pdfNativeRectClip;
        if (!proof || proof.schema !== "figureStudio.pdfRectangleScope.v1" || this.opacity !== 1 || this.shadow || this.mask
            || this.backgroundColor || this.filters?.length || this.resizeFilter || this.figureStudioAppearanceStack
            || this.figureStudioAppearanceMeta || this.hasStroke() || typeof this.fill !== "string" || /^\s*url\s*\(/i.test(this.fill)
            || (this.globalCompositeOperation && this.globalCompositeOperation !== "source-over")
            || simpleNativeClip(this.clipPath, fabric)?.layers.length !== 1) return null;
        // The proof is only a candidate. Editing canonical path/clip geometry
        // invalidates it and restores Fabric's general clipping implementation.
        const bounds = hardRectangle(this.clipPath);
        if (!bounds || JSON.stringify(this.path) !== proof.path || JSON.stringify(this.clipPath.path || ["rect", this.clipPath.width, this.clipPath.height]) !== proof.clipGeometry) return null;
        return bounds;
      }
      _nativeVectorClip() {
        if (this.opacity !== 1 || this.shadow || this.mask || this.backgroundColor || this.filters?.length || this.resizeFilter
            || this.figureStudioAppearanceStack || this.figureStudioAppearanceMeta
            || ![undefined, "source-over"].includes(this.globalCompositeOperation)) return null;
        return simpleNativeClip(this.clipPath, fabric);
      }
      needsItsOwnCache() { return this._nativeRectangle() || this._nativeVectorClip() ? false : super.needsItsOwnCache(); }
      drawObject(context, forClipping, cache) {
        const device = !forClipping && this._pdfDeviceRectangle(context);
        if (device) {
          context.save();
          try {
            context.setTransform(1, 0, 0, 1, 0, 0);context.fillStyle = this.fill;
            if (device.right > device.left && device.bottom > device.top) context.fillRect(device.left, device.top, device.right - device.left, device.bottom - device.top);
          } finally { context.restore(); }
          return;
        }
        const rectangle = !forClipping && this._nativeRectangle();
        const vector = !rectangle && !forClipping && this._nativeVectorClip();
        if (!rectangle && !vector) return super.drawObject(context, forClipping, cache);
        const matrix = this.clipPath.calcOwnMatrix();
        context.save();
        try {
          if (vector) applySimpleNativeClip(context, vector, this, fabric);
          else {
            context.beginPath();
            context.save();
            transformNativeClip(context, this, [matrix], fabric);
            context.rect(rectangle.left, rectangle.top, rectangle.width, rectangle.height);
            context.restore();
            context.clip(this.clipPath.fillRule === "evenodd" ? "evenodd" : "nonzero");
          }
          this.__pdfNativeClipActive = true;
          super.drawObject(context, forClipping, cache);
        } finally { this.__pdfNativeClipActive = false; context.restore(); }
      }
      _drawClipPath(context, clip, cache) { if (!this.__pdfNativeClipActive) super._drawClipPath(context, clip, cache); }
      toObject(properties = []) { return { ...super.toObject([...properties, "pdfDisplayStrokePolicy", "pdfDisplayFillPolicy", ...META_PROPS]), pdfNativeRectClip: clone(this.pdfNativeRectClip) }; }
    }
    fabric.classRegistry?.setClass(PdfNativeRectClippedPath);
    pathClassByFabric.set(fabric, PdfNativeRectClippedPath);
    bindScenePaint(PdfNativeRectClippedPath, "path", ["render", "drawObject", "calcOwnMatrix", "calcTransformMatrix",
      "_renderPathCommands", "_renderPaintInOrder", "_renderFill", "_renderStroke", "_setFillStyles", "_setStrokeStyles",
      "_pdfDeviceRectangle", "_nativeRectangle", "_nativeVectorClip", "_drawClipPath", "needsItsOwnCache"], fabric);
    return PdfNativeRectClippedPath;
  }

  function inDefinition(element) {
    for (let current = element.parentElement; current; current = current.parentElement) if (DEFINITIONS.has(tag(current))) return true;
    return false;
  }

  function graphemes(text, fabric) {
    return fabric?.util?.graphemeSplit ? fabric.util.graphemeSplit(String(text)) : Array.from(String(text));
  }

  function glyphPlan(text, raw, positions, mapping, fabric) {
    const unicode = graphemes(text, fabric);
    const rawGlyphs = Array.from(raw);
    const entries = Array.isArray(mapping) ? mapping : rawGlyphs.map((fontChar, index) => ({ unicode: unicode[index] ?? "", fontChar }));
    const map = Array.isArray(mapping) ? Object.fromEntries(entries.filter((entry) => entry.unicode).map((entry) => [entry.unicode, entry.fontChar])) : { ...(mapping || {}) };
    const unicodeAdvances = Object.fromEntries(entries.filter((entry) => /^\s+$/.test(entry.unicode || "") && Number.isFinite(entry.width)).map((entry) => [entry.unicode, entry.width / 1000]));
    const firstX = positions.x[0] || 0, firstY = positions.y[0] || 0;
    let cursor = 0;
    const glyphs = entries.map((entry, index) => {
      const value = String(entry.unicode ?? unicode[index] ?? "");
      const count = graphemes(value, fabric).length;
      const glyph = { unicode: value, fontChar: String(entry.fontChar ?? rawGlyphs[index] ?? value), charIndex: cursor, charCount: count, x: number(entry.x, positions.x[index] ?? firstX) - firstX, y: number(entry.y, positions.y[index] ?? firstY) - firstY };
      cursor += count;
      return glyph;
    });
    return { glyphs, map, unicodeAdvances, charCount: cursor, firstX, firstY };
  }

  // PDF font programs commonly expose private-use glyph codes. Keep Unicode in
  // IText.text, while measuring/drawing those glyph codes in the original font.
  // Imported spacing is valid only for the original text and font properties.
  const currentPlanePathClassByFabric = new WeakMap();
  function registerCurrentPlanePathClass(fabric) {
    if (currentPlanePathClassByFabric.has(fabric)) return currentPlanePathClassByFabric.get(fabric);
    class PdfCurrentPlanePath extends fabric.Path {
      static type = "PdfCurrentPlanePath";
      // These native current commands already live in their declaring plane.
      // Path measurement remains native; paint never subtracts and re-adds its
      // measured centre. A method facade supplies only the writer's local origin.
      _renderPathCommands(context) {
        const writer = Object.create(this);
        writer.pathOffset = new fabric.Point(0, 0);
        return fabric.Path.prototype._renderPathCommands.call(writer, context);
      }
      _getOffsetTransform() { return ""; }
      _currentPlaneBounds() { return fabric.Path.prototype._calcBoundsFromPath.call(this); }
      _getNonTransformedDimensions() {
        const bounds = this._currentPlaneBounds();
        return new fabric.Point(2 * Math.max(Math.abs(bounds.left), Math.abs(bounds.left + bounds.width)) + this.strokeWidth,
          2 * Math.max(Math.abs(bounds.top), Math.abs(bounds.top + bounds.height)) + this.strokeWidth);
      }
      _getTransformedDimensions(options = {}) {
        const dimensions = this._getNonTransformedDimensions();
        return super._getTransformedDimensions({ ...options, width: dimensions.x - this.strokeWidth, height: dimensions.y - this.strokeWidth });
      }
      calcACoords() {
        const bounds = this._currentPlaneBounds(), facade = Object.create(this);
        facade.getRelativeCenterPoint = () => fabric.util.transformPoint(new fabric.Point(bounds.left + bounds.width / 2,
          bounds.top + bounds.height / 2), this.calcOwnMatrix());
        facade._getTransformedDimensions = options => fabric.Path.prototype._getTransformedDimensions.call(this,
          { ...options, width: bounds.width, height: bounds.height });
        return fabric.Path.prototype.calcACoords.call(facade);
      }
      calcOCoords() {
        const bounds = this._currentPlaneBounds(), facade = Object.create(this);
        facade.getCenterPoint = () => fabric.util.transformPoint(new fabric.Point(bounds.left + bounds.width / 2,
          bounds.top + bounds.height / 2), this.calcTransformMatrix());
        facade._getTransformedDimensions = options => fabric.Path.prototype._getTransformedDimensions.call(this,
          { ...options, width: bounds.width, height: bounds.height });
        return fabric.Path.prototype.calcOCoords.call(facade);
      }
    }
    fabric.classRegistry?.setClass(PdfCurrentPlanePath);
    currentPlanePathClassByFabric.set(fabric, PdfCurrentPlanePath);
    return PdfCurrentPlanePath;
  }

  function registerTextClass(fabric) {
    preserveRenderPolicy(fabric);
    if (classByFabric.has(fabric)) return classByFabric.get(fabric);
    const Base = fabric.IText || fabric.Text;
    if (!Base) throw new Error("Fabric editable text is unavailable.");
    const primitiveBinding={completeAtRegistration:Base.prototype.getCompleteStyleDeclaration,
      complete:startupTextStyleDeclarations.get(fabric)?.replacement,
      methods:["_renderChar","_getStyleDeclaration","_getFontDeclaration","_setFillStyles","handleFiller"]
        .map(name=>[name,Base.prototype[name]])};
    primitiveTextBindings.set(fabric,primitiveBinding);
    class PdfPositionedText extends Base {
      static type = "PdfPositionedText";
      constructor(text, options = {}) {
        // Native construction measures first. Source/frame restoration begins
        // only after that constructor, before any live authoring transition.
        const { pdfTextSource, pdfTextAuthoringFrame, pdfTextAuthoringPlane, ...nativeOptions } = options;
        super(text, nativeOptions);
        this.pdfTextSource = clone(pdfTextSource || null);
        if (Object.hasOwn(options, "pdfTextAuthoringFrame")) this.pdfTextAuthoringFrame = clone(options.pdfTextAuthoringFrame);
        if (Object.hasOwn(options, "pdfTextAuthoringPlane")) this.pdfTextAuthoringPlane = clone(options.pdfTextAuthoringPlane);
        if (this.pdfTextSource?.currentNativeGlyphPlanes || this.pdfTextAuthoringPlane) this.__pdfLayoutAnchor = undefined;
        this.initDimensions();
        // Fabric may hover a grouped text child before Canvas activates it.
        // Activation still computes the real control coordinates via setCoords.
        this.oCoords ||= {};
        if (this.pdfTextSource?.currentNativeGlyphPlanes || this.pdfTextAuthoringPlane) this._toSVG = this._pdfCurrentPlaneSvgMarkup;
        this.on?.("changed", () => { this.dirty = true; this.initDimensions(); });
      }
      _pdfCurrentNativePlane() {
        if (!this.pdfTextSource?.currentNativeGlyphPlanes && !this.pdfTextAuthoringPlane) return null;
        const source = this._sourceLayout();
        const native = source?.currentNativeGlyphPlanes;
        const matrices = value => Array.isArray(value) && value.length > 0 && value.length <= 4
          && value.every(matrix => Array.isArray(matrix) && matrix.length === 6 && matrix.every(value => Number.isFinite(value) && Math.abs(value) <= 1e8 && !Object.is(value, -0))
            && Number.isFinite(matrix[0] * matrix[3] - matrix[1] * matrix[2]) && matrix[0] * matrix[3] - matrix[1] * matrix[2] !== 0);
        const keys = (value, allowed) => value && Object.keys(value).every(key => allowed.includes(key));
        const coordinate = value => (typeof value === "number" || typeof value === "string" && /^[+-]?(?:\d*\.\d+|\d+\.?\d*)(?:e[+-]?\d+)?$/i.test(value))
          && Number.isFinite(Number(value)) && Math.abs(Number(value)) <= 1e8;
        const numbers = entry => ({ ...entry, x: Number(entry.x), y: Number(entry.y) });
        if (this.constructor !== PdfPositionedText || !this._pdfCurrentPlaneSupported()) return null;
        if (native && native.schema === "figureStudio.currentNativeGlyphPlanes.v1"
            && keys(native, ["schema", "entries"]) && this._pdfPlainPaintData(native, 0, { remaining: 12000 }) && native.entries?.length === source.glyphs.length
            && native.entries.length <= 4096 && native.entries.every((entry, index) => matrices(entry.matrices)
              && keys(entry, ["matrices", "x", "y", "charIndex", "charCount", "sourceFontKey"]) && [entry.x, entry.y].every(coordinate) && entry.charIndex === source.glyphs[index].charIndex
              && entry.charCount === source.glyphs[index].charCount && entry.sourceFontKey === source.glyphs[index].sourceFontKey)) {
          const entries = native.entries.map(numbers);
          return { kind: "source", entries, first: entries[0] };
        }
        const authored = this.pdfTextAuthoringPlane;
        if (!authored || source || authored.schema !== "figureStudio.currentTextAuthoringPlane.v1"
            || authored.sourceSchema !== this.pdfTextSource?.schema || !keys(authored, ["schema", "sourceSchema", "matrices", "x", "y", "layout"]) || !this._pdfPlainPaintData(authored)
            || !matrices(authored.matrices) || ![authored.x, authored.y].every(coordinate)
            || JSON.stringify(authored.layout) !== JSON.stringify(this._pdfPaintLayout())) return null;
        return { kind: "authored", first: numbers(authored) };
      }
      _pdfCurrentPlaneFirst(plane) {
        let matrix = [1, 0, 0, 1, 0, 0];
        for (const local of plane.first.matrices) matrix = multiply(matrix, local);
        return fabric.util.transformPoint(new fabric.Point(plane.first.x, plane.first.y), matrix);
      }
      _pdfCurrentNativePaintMatrix() {
        const plane = this._pdfCurrentNativePlane();
        if (!plane) return null;
        return plane.first.matrices.reduce((current, local) => multiply(current, local), this.calcTransformMatrix());
      }
      _pdfCurrentPlaneEntries(plane) {
        if (plane.kind === "source") return plane.entries;
        const entries = [];
        let start = 0;
        this._textLines.forEach((line, lineIndex) => {
          const offset = this._pdfCurrentLineOffset(lineIndex);
          line.forEach((char, columnIndex) => entries.push({ ...plane.first, lineIndex, columnIndex,
            charIndex: start + columnIndex, charCount: 1,
            x: this.__charBounds[lineIndex][columnIndex].left === 0 ? plane.first.x : plane.first.x + this.__charBounds[lineIndex][columnIndex].left,
            y: lineIndex === 0 ? plane.first.y : plane.first.y + offset }));
          start += line.length + 1;
        });
        return entries;
      }
      _pdfCurrentLineOffset(lineIndex) {
        let offset = 0;
        for (let index = 0; index < lineIndex; index++) offset += this.getHeightOfLine(index);
        return offset + (this.getHeightOfLineImpl(lineIndex) - this.getHeightOfLineImpl(0)) * (1 - this._fontSizeFraction);
      }
      _pdfCurrentPlaneSupported() {
        if (this._pdfPaintFrameSupported()) return true;
        if ((!this.pdfTextSource?.currentNativeGlyphPlanes && !this.pdfTextAuthoringPlane)
            || this._textLines?.length < 2 || this._textLines?.length > 64 || this.text.length > 4096) return false;
        // Keep the legacy single-line frame predicate unchanged. Current native
        // planes additionally support bounded native line layout with exactly
        // the same paint, style, font, direction and effect restrictions.
        const facade = Object.create(this);
        facade._textLines = [this._textLines[0]];
        return PdfPositionedText.prototype._pdfPaintFrameSupported.call(facade);
      }
      _pdfCurrentPlaneBounds(plane) {
        const points = [];
        const entries = this._pdfCurrentPlaneEntries(plane);
        if (plane.kind === "authored") this._textLines.forEach((line, lineIndex) => {
          if (!line.length) entries.push({ ...plane.first, lineIndex, columnIndex: 0, charIndex: 0, charCount: 0,
            y: lineIndex === 0 ? plane.first.y : plane.first.y + this._pdfCurrentLineOffset(lineIndex) });
        });
        // An emptied live label still owns a finite caret and drawing plane.
        // It has no painted glyph, so use the first declaration's empty em box.
        if (!entries.length) entries.push({ ...plane.first, charIndex: 0, charCount: 0 });
        for (const entry of entries) {
          let matrix = [1, 0, 0, 1, 0, 0];
          for (const local of entry.matrices) matrix = multiply(matrix, local);
          const lineIndex = entry.lineIndex || 0, columnIndex = entry.columnIndex ?? entry.charIndex;
          const declaration = this.getCompleteStyleDeclaration(lineIndex, columnIndex), char = this._textLines[lineIndex][columnIndex];
          const width = char === undefined ? 0 : this._measureChar(char, declaration).width, height = declaration.fontSize;
          // Conservative current native font em bounds include overhangs. They
          // are computed from current paint declarations, never cached world ink.
          for (const [x, y] of [[entry.x - height, entry.y - 2 * height], [entry.x + width + height, entry.y - 2 * height],
            [entry.x + width + height, entry.y + height], [entry.x - height, entry.y + height]]) points.push(fabric.util.transformPoint(new fabric.Point(x, y), matrix));
        }
        return { left: Math.min(...points.map(point => point.x)), right: Math.max(...points.map(point => point.x)),
          top: Math.min(...points.map(point => point.y)), bottom: Math.max(...points.map(point => point.y)) };
      }
      _pdfCurrentInputPlane() {
        // Native onInput inserts inherited styles before updating the text.
        // That invalidates source-layout matching, but does not change the
        // current declaring plane. Admit only a still-identical declaration.
        if (!this.pdfTextSource?.currentNativeGlyphPlanes && !this.pdfTextAuthoringPlane) return null;
        const plane = this._pdfCurrentNativePlane();
        if (plane) return plane;
        if (!this._pdfCurrentPlaneSupported()) return null;
        const prior = this.__pdfCurrentPlaneBefore, source = this.pdfTextSource?.currentNativeGlyphPlanes;
        const authored = this.pdfTextAuthoringPlane;
        const declaration = authored?.schema === "figureStudio.currentTextAuthoringPlane.v1"
          && authored.sourceSchema === this.pdfTextSource?.schema ? authored
          : source?.schema === "figureStudio.currentNativeGlyphPlanes.v1" ? source.entries?.[0] : null;
        if (!prior?.first || !declaration || !this._pdfPlainPaintData(declaration, 0, { remaining: 12000 })
            || !Object.is(prior.first.x, Number(declaration.x)) || !Object.is(prior.first.y, Number(declaration.y))
            || !Array.isArray(declaration.matrices) || prior.first.matrices.length !== declaration.matrices.length
            || !declaration.matrices.every((matrix, index) => Array.isArray(matrix) && matrix.length === 6
              && matrix.every((value, column) => Object.is(value, prior.first.matrices[index][column])))) return null;
        return prior;
      }
      updateFromTextArea() {
        const textarea = this.hiddenTextarea;
        const inputLines = textarea && typeof textarea.value === "string" && textarea.value.length <= 4096
          ? this._splitTextIntoLines(textarea.value).lines.length : null;
        if (inputLines === null || inputLines > 64
            || !(this._pdfCurrentInputPlane() || inputLines === 1 && this._pdfPaintFrameAnchor())) {
          return super.updateFromTextArea();
        }
        // Native origin repositioning can replace an already solved baseline.
        // Current glyph planes and admitted one-line paint frames instead let
        // initDimensions preserve their geometry before caret/selection update.
        this.cursorOffsetCache = {};
        this.text = textarea.value;
        this.set("dirty", true);
        this.initDimensions();
        this.setCoords();
        const selection = this.fromStringToGraphemeSelection(textarea.selectionStart, textarea.selectionEnd, textarea.value);
        this.selectionEnd = this.selectionStart = selection.selectionEnd;
        if (!this.inCompositionMode) this.selectionStart = selection.selectionStart;
        this.updateTextareaPosition();
      }
      _getNonTransformedDimensions() {
        const plane = this._pdfCurrentNativePlane();
        if (!plane) return super._getNonTransformedDimensions();
        const bounds = this._pdfCurrentPlaneBounds(plane);
        return new fabric.Point(2 * Math.max(Math.abs(bounds.left), Math.abs(bounds.right)) + this.strokeWidth,
          2 * Math.max(Math.abs(bounds.top), Math.abs(bounds.bottom)) + this.strokeWidth);
      }
      _getTransformedDimensions(options = {}) {
        const plane = this._pdfCurrentNativePlane();
        if (!plane) return super._getTransformedDimensions(options);
        const dimensions = this._getNonTransformedDimensions();
        return super._getTransformedDimensions({ ...options, width: dimensions.x - this.strokeWidth, height: dimensions.y - this.strokeWidth });
      }
      calcACoords() {
        const plane = this._pdfCurrentNativePlane();
        if (!plane) return super.calcACoords();
        const bounds = this._pdfCurrentPlaneBounds(plane), own = this.calcOwnMatrix();
        return Object.fromEntries(Object.entries({ tl: [bounds.left, bounds.top], tr: [bounds.right, bounds.top],
          bl: [bounds.left, bounds.bottom], br: [bounds.right, bounds.bottom] }).map(([key, point]) => [key, fabric.util.transformPoint(new fabric.Point(...point), own)]));
      }
      _pdfCurrentControlFacade(plane) {
        const bounds = this._pdfCurrentPlaneBounds(plane), facade = Object.create(this);
        const center = new fabric.Point((bounds.left + bounds.right) / 2, (bounds.top + bounds.bottom) / 2), world = this.calcTransformMatrix();
        facade.width = bounds.right - bounds.left;
        facade.height = bounds.bottom - bounds.top;
        facade.calcTransformMatrix = () => multiply(world, [1, 0, 0, 1, center.x, center.y]);
        facade.getCenterPoint = () => fabric.util.transformPoint(new fabric.Point((bounds.left + bounds.right) / 2,
          (bounds.top + bounds.bottom) / 2), world);
        facade._getTransformedDimensions = options => fabric.IText.prototype._getTransformedDimensions.call(this,
          { ...options, width: bounds.right - bounds.left, height: bounds.bottom - bounds.top });
        return facade;
      }
      calcOCoords() {
        const plane = this._pdfCurrentNativePlane();
        if (!plane) return super.calcOCoords();
        return fabric.IText.prototype.calcOCoords.call(this._pdfCurrentControlFacade(plane));
      }
      _renderControls(context, options) {
        const plane = this._pdfCurrentNativePlane();
        if (!plane) return super._renderControls(context, options);
        // Literal PDF glyph coordinates can be far from the identity text
        // owner's origin. Native editing borders must use the same tight
        // glyph bounds as the handles, rather than crossing the figure from
        // that unrelated origin. Only the drawing facade changes.
        return fabric.IText.prototype._renderControls.call(this._pdfCurrentControlFacade(plane), context, options);
      }
      _pdfWithCurrentPlane(context, entry, work) {
        context.save();
        try { for (const matrix of entry.matrices) context.transform(...matrix); return work(); }
        finally { context.restore(); }
      }
      _pdfCurrentPlaneCaret(plane, selection = this.selectionStart) {
        if (this._textLines.length > 1) {
          const { lineIndex, charIndex } = this.get2DCursorLocation(selection);
          const declaration = this.getCompleteStyleDeclaration(lineIndex, Math.max(0, charIndex - 1));
          const entry = { ...plane.first, lineIndex, columnIndex: charIndex, charIndex: selection, charCount: 0,
            x: this.__charBounds[lineIndex][charIndex].left === 0 ? plane.first.x : plane.first.x + this.__charBounds[lineIndex][charIndex].left,
            y: lineIndex === 0 ? plane.first.y : plane.first.y + this._pdfCurrentLineOffset(lineIndex) };
          return { entry, declaration, x: entry.x, y: entry.y };
        }
        const entries = this._pdfCurrentPlaneEntries(plane), last = selection >= this._text.length;
        if (!entries.length) return { entry: { ...plane.first, charIndex: 0, charCount: 0 },
          declaration: this.getCompleteStyleDeclaration(0, 0), x: plane.first.x, y: plane.first.y };
        const index = last ? entries.length - 1 : Math.max(0, entries.findIndex(entry => selection < entry.charIndex + entry.charCount));
        const entry = entries[index], declaration = this.getCompleteStyleDeclaration(0, entry.charIndex);
        const width = last ? this._measureChar(this._textLines[0][entry.charIndex], declaration).width : 0;
        return { entry, declaration, x: width === 0 ? entry.x : entry.x + width, y: entry.y };
      }
      _renderCursor(context, boundaries, selection) {
        const plane = this._pdfCurrentNativePlane();
        if (!plane) return super._renderCursor(context, boundaries, selection);
        const caret = this._pdfCurrentPlaneCaret(plane, selection ?? this.selectionStart), data = this.getCursorRenderingData(selection, boundaries);
        let matrix = [1, 0, 0, 1, 0, 0];
        for (const local of caret.entry.matrices) matrix = multiply(matrix, local);
        this._pdfWithCurrentPlane(context, caret.entry, () => {
          const width = data.width / Math.hypot(matrix[0], matrix[1]);
          context.fillStyle = data.color; context.globalAlpha = data.opacity;
          context.fillRect(caret.x - width / 2, caret.y - caret.declaration.fontSize * (1 - this._fontSizeFraction), width, caret.declaration.fontSize);
        });
      }
      _getCursorBoundaries(selection = this.selectionStart, skipCaching) {
        const plane = this._pdfCurrentNativePlane();
        if (!plane) return super._getCursorBoundaries(selection, skipCaching);
        const caret = this._pdfCurrentPlaneCaret(plane, selection);
        let matrix = [1, 0, 0, 1, 0, 0];
        for (const local of caret.entry.matrices) matrix = multiply(matrix, local);
        const point = fabric.util.transformPoint(new fabric.Point(caret.x, caret.y - caret.declaration.fontSize * (1 - this._fontSizeFraction)), matrix);
        return { left: 0, top: 0, leftOffset: point.x, topOffset: point.y };
      }
      getSelectionStartFromPointer(event) {
        const plane = this._pdfCurrentNativePlane();
        if (!plane || !this.canvas?.getScenePoint) return super.getSelectionStartFromPointer(event);
        const pointer = this.canvas.getScenePoint(event).transform(fabric.util.invertTransform(this.calcTransformMatrix()));
        let nearest = 0, distance = Infinity;
        for (let index = 0; index <= this._text.length; index++) {
          const caret = this._pdfCurrentPlaneCaret(plane, index); let matrix = [1, 0, 0, 1, 0, 0];
          for (const local of caret.entry.matrices) matrix = multiply(matrix, local);
          const point = fabric.util.transformPoint(new fabric.Point(caret.x, caret.y), matrix), current = (point.x - pointer.x) ** 2 + (point.y - pointer.y) ** 2;
          if (current < distance) { distance = current; nearest = index; }
        }
        return nearest;
      }
      _renderSelection(context, selection, boundaries) {
        const plane = this._pdfCurrentNativePlane();
        if (!plane) return super._renderSelection(context, selection, boundaries);
        context.fillStyle = this.selectionColor;
        for (const entry of this._pdfCurrentPlaneEntries(plane)) {
          if (entry.charIndex < selection.selectionStart || entry.charIndex >= selection.selectionEnd) continue;
          const lineIndex = entry.lineIndex || 0, columnIndex = entry.columnIndex ?? entry.charIndex;
          const declaration = this.getCompleteStyleDeclaration(lineIndex, columnIndex), width = this._measureChar(this._textLines[lineIndex][columnIndex], declaration).width;
          this._pdfWithCurrentPlane(context, entry, () => context.fillRect(entry.x, entry.y - declaration.fontSize * (1 - this._fontSizeFraction), width, declaration.fontSize));
        }
      }
      _pdfCurrentPlaneSvgMarkup() {
        const plane = this._pdfCurrentNativePlane();
        if (!plane) return super._toSVG();
        const authoredLines = new Map();
        const spans = this._pdfCurrentPlaneEntries(plane).map(entry => {
          const lineIndex = entry.lineIndex || 0, columnIndex = entry.columnIndex ?? entry.charIndex;
          const declaration = this.getCompleteStyleDeclaration(lineIndex, columnIndex), unicode = this._textLines[lineIndex].slice(columnIndex, columnIndex + entry.charCount).join("");
          const source = plane.kind === "source" ? this.pdfTextSource.glyphs.find(glyph => glyph.charIndex === entry.charIndex) : null;
          const mapped = source ? { text: source.fontChar, declaration } : this._mapped(unicode, declaration);
          const glyph = mapped.text, styles = this.getSvgSpanStyles(mapped.declaration, true);
          const opens = entry.matrices.map(matrix => `<g transform="matrix(${matrix.map(value => Object.is(value, -0) ? "-0" : String(value)).join(" ")})">`).join("");
          const span = `<tspan data-pdf-unicode="${escapeXml(unicode)}" data-pdf-glyph-map="${escapeXml(JSON.stringify([{ unicode, fontChar: glyph }]))}" x="${Object.is(entry.x, -0) ? "-0" : entry.x}" y="${Object.is(entry.y, -0) ? "-0" : entry.y}" style="${styles}">${escapeXml(xmlGlyph(glyph, unicode))}</tspan>`;
          if (plane.kind === "authored") {
            if (!authoredLines.has(lineIndex)) authoredLines.set(lineIndex, { opens, spans: [], depth: entry.matrices.length });
            authoredLines.get(lineIndex).spans.push(span);
            return "";
          }
          return opens + `<text xml:space="preserve">${span}</text>` + "</g>".repeat(entry.matrices.length);
        });
        const markup = plane.kind === "authored" ? Array.from(authoredLines.values(), line =>
          line.opens + `<text xml:space="preserve">${line.spans.join("")}</text>` + "</g>".repeat(line.depth)) : spans;
        return ['<g style="' + this.getSvgStyles(true) + '" ', "COMMON_PARTS", ">\n", ...markup, "</g>\n"];
      }

      _pdfNominalAnchorPoint() {
        const anchor = this.pdfTextSource?.anchor || "start";
        return { x: this.width * (anchor === "middle" ? 0 : anchor === "end" ? .5 : -.5), y: -this.height / 2 + this.getHeightOfLineImpl(0) * (1 - this._fontSizeFraction) };
      }
      _pdfNearbyCoordinates(value) {
        if (!Number.isFinite(value) || Math.abs(value) > 1e8) return [];
        const result = [value], buffer = new ArrayBuffer(8), data = new DataView(buffer);
        const step = (current, up) => {
          if (current === 0) return up ? Number.MIN_VALUE : -Number.MIN_VALUE;
          data.setFloat64(0, current, false);
          let bits = data.getBigUint64(0, false);
          bits += (current > 0) === up ? 1n : -1n;
          data.setBigUint64(0, bits, false);
          return data.getFloat64(0, false);
        };
        let up = value, down = value;
        for (let index = 0; index < 16; index++) { up = step(up, true); down = step(down, false); result.push(up, down); }
        return result.filter(Number.isFinite);
      }
      _pdfPlainPaintData(value, depth = 0, budget = { remaining: 4096 }) {
        if (--budget.remaining < 0 || depth > 8) return false;
        if (value === null || ["string", "boolean"].includes(typeof value)) return true;
        if (typeof value === "number") return Number.isFinite(value);
        if (!value || typeof value !== "object") return false;
        const proto = Object.getPrototypeOf(value);
        if (Array.isArray(value)) {
          if (Reflect.ownKeys(value).length !== value.length + 1) return false;
        } else if (proto !== null && Object.getPrototypeOf(proto) !== null) return false;
        return Reflect.ownKeys(value).every(key => typeof key === "string"
          && Object.hasOwn(Object.getOwnPropertyDescriptor(value, key), "value")
          && (Array.isArray(value) && key === "length" || this._pdfPlainPaintData(Object.getOwnPropertyDescriptor(value, key).value, depth + 1, budget)));
      }
      _pdfPaintLayout() {
        const layout = { text: this.text, width: this.width, height: this.height, fontFamily: this.fontFamily,
          fontSize: this.fontSize, fontWeight: this.fontWeight, fontStyle: this.fontStyle,
          lineHeight: this.lineHeight, charSpacing: this.charSpacing, direction: this.direction,
          textAlign: this.textAlign, styles: fabric.util.stylesToArray(this.styles || {}, this.text) };
        return this._pdfPlainPaintData(layout) ? layout : null;
      }
      _pdfPaintFrameSupported() {
        const source = this.pdfTextSource;
        const solid = value => value === undefined || value === null || typeof value === "string";
        const styles = fabric.util.stylesToArray(this.styles || {}, this.text);
        const simpleStyle = style => solid(style.fill) && solid(style.stroke)
          && !style.deltaY && !style.textBackgroundColor && !style.underline && !style.overline && !style.linethrough;
        return this.constructor === PdfPositionedText
          && ["figureStudio.pdfPositionedText.v1", "figureStudio.pdfPositionedText.v2"].includes(source?.schema)
          && [undefined, "start"].includes(source?.anchor) && this.textAlign === "left"
          && this._textLines?.length === 1 && solid(this.fill) && solid(this.stroke) && styles.every(row => simpleStyle(row.style))
          && !this.deltaY && !this.textBackgroundColor && !this.underline && !this.overline && !this.linethrough
          && !this.path && !this.shadow && !this.backgroundColor
          && !this.figureStudioAppearanceStack && !this.figureStudioAppearanceMeta && !this.mask
          && !this.filters?.length && !this.resizeFilter && this.direction === "ltr"
          && (!this.globalCompositeOperation || this.globalCompositeOperation === "source-over")
          && [this.width, this.height, this.fontSize, this.lineHeight, this.charSpacing].every(Number.isFinite)
          && this.width >= 0 && this.height > 0 && this.fontSize > 0 && this.lineHeight > 0;
      }
      _pdfPaintFrameAnchor() {
        const frame = this.pdfTextAuthoringFrame;
        if (!frame || !this._pdfPaintFrameSupported() || this._sourceLayout()) return null;
        const keys = ["schema", "sourceSchema", "offsetX", "offsetY", "layout"];
        if (!this._pdfPlainPaintData(frame) || Reflect.ownKeys(frame).length !== keys.length
            || !keys.every(key => Object.hasOwn(frame, key))
            || frame.schema !== "figureStudio.positionedTextAuthoringFrame.v1"
            || frame.sourceSchema !== this.pdfTextSource.schema
            || ![frame.offsetX, frame.offsetY].every(Number.isFinite)) return null;
        const layout = this._pdfPaintLayout(), nominal = this._pdfNominalAnchorPoint();
        if (!layout || JSON.stringify(frame.layout) !== JSON.stringify(layout)
            || Math.max(Math.abs(nominal.x), Math.abs(nominal.y)) > 1e6
            || !this._pdfNearbyCoordinates(nominal.x).some(value => Object.is(value, nominal.x + frame.offsetX))
            || !this._pdfNearbyCoordinates(nominal.y).some(value => Object.is(value, nominal.y + frame.offsetY))) return null;
        return { x: nominal.x + frame.offsetX, y: nominal.y + frame.offsetY };
      }
      _pdfPaintOffset() {
        const point = this._pdfPaintFrameAnchor();
        if (!point) return { x: 0, y: 0 };
        const nominal = this._pdfNominalAnchorPoint();
        return { x: point.x - nominal.x, y: point.y - nominal.y };
      }
      _pdfAnchorPoint() { const plane = this._pdfCurrentNativePlane(); return plane ? this._pdfCurrentPlaneFirst(plane) : this._pdfPaintFrameAnchor() || this._pdfNominalAnchorPoint(); }
      getCursorRenderingData(index = this.selectionStart, boundaries = this._getCursorBoundaries(index)) {
        const result = super.getCursorRenderingData(index, boundaries), point = this._pdfPaintFrameAnchor();
        if (!point) return result;
        const cursor = this.get2DCursorLocation(index);
        if (cursor.lineIndex !== 0) return result;
        const character = cursor.charIndex > 0 ? cursor.charIndex - 1 : 0;
        const fontSize = this.getValueOfPropertyAt(0, character, "fontSize");
        const deltaY = this.getValueOfPropertyAt(0, character, "deltaY");
        // The caret rectangle uses the same CURRENT local glyph baseline as
        // Canvas and SVG. Reassociating native top/line-height expressions can
        // round to a different local baseline, even with identical getters.
        return { ...result, left: point.x + boundaries.leftOffset - result.width / 2,
          top: point.y - fontSize * (1 - this._fontSizeFraction) + deltaY };
      }
      _getLeftOffset() { return super._getLeftOffset() + this._pdfPaintOffset().x; }
      _getTopOffset() { return super._getTopOffset() + this._pdfPaintOffset().y; }
      _getSVGLeftTopOffsets() {
        const offsets = super._getSVGLeftTopOffsets(), paint = this._pdfPaintOffset();
        return { ...offsets, textLeft: offsets.textLeft + paint.x, textTop: offsets.textTop + paint.y };
      }
      _pdfSolvePaintFrame(world, target) {
        if (!this._pdfPaintFrameSupported() || this._sourceLayout() || !world.every(value => Number.isFinite(value) && Math.abs(value) <= 1e8)) return null;
        const nominal = this._pdfNominalAnchorPoint(), layout = this._pdfPaintLayout();
        if (!layout || Math.max(Math.abs(nominal.x), Math.abs(nominal.y)) > 1e6) return null;
        for (const x of this._pdfNearbyCoordinates(nominal.x)) for (const y of this._pdfNearbyCoordinates(nominal.y)) {
          const actual = fabric.util.transformPoint(new fabric.Point(x, y), world);
          if (Object.is(actual.x, target.x) && Object.is(actual.y, target.y)) return {
            schema: "figureStudio.positionedTextAuthoringFrame.v1", sourceSchema: this.pdfTextSource.schema,
            offsetX: x - nominal.x, offsetY: y - nominal.y, layout };
        }
        return null;
      }
      _pdfSolveClipTranslation(clip, world, target, initial) {
        const supported = [fabric.Path, fabric.Rect, fabric.Circle, fabric.Ellipse, fabric.Group, groupClassByFabric.get(fabric)].filter(Boolean);
        if (!supported.some(Class => clip.constructor === Class) || clip.absolutePositioned
            || !world.every(value => Number.isFinite(value) && Math.abs(value) <= 1e8)
            || !target.every(value => Number.isFinite(value) && Math.abs(value) <= 1e8)) return null;
        const probe = Object.create(clip);
        for (const left of this._pdfNearbyCoordinates(initial.left)) for (const top of this._pdfNearbyCoordinates(initial.top)) {
          probe.left = left; probe.top = top;
          const matrix = multiply(world, probe.calcOwnMatrix());
          if (matrix.every((value, index) => Object.is(value, target[index]))) return { left, top };
        }
        return null;
      }
      initDimensions() {
        // Capture the current live authored baseline and clip, never an
        // original-import pose. Only actual paint offsets may bridge a proven
        // Float64 translation representability gap after native measurement.
        const nativePlaneBefore = this._pdfCurrentNativePlane() || this.__pdfCurrentPlaneBefore;
        const prior = this.pdfTextSource && this.__pdfLayoutAnchor;
        const validFrameBefore = prior && this._pdfPaintFrameAnchor();
        const before = prior && this.calcOwnMatrix().slice();
        const worldBefore = prior && this.calcTransformMatrix().slice();
        const anchorBefore = worldBefore && fabric.util.transformPoint(new fabric.Point(prior.x, prior.y), worldBefore);
        const relativeClip = before && this.clipPath && !this.clipPath.absolutePositioned;
        const clipBefore = relativeClip && multiply(before, this.clipPath.calcOwnMatrix());
        const clipWorldBefore = relativeClip && multiply(worldBefore, this.clipPath.calcOwnMatrix());
        super.initDimensions();
        if (!this.pdfTextSource || !this._textLines?.length) return;
        let nativePlane = this._pdfCurrentNativePlane();
        if (!nativePlane && nativePlaneBefore && this._pdfCurrentPlaneSupported()) {
          this.pdfTextAuthoringPlane = { schema: "figureStudio.currentTextAuthoringPlane.v1", sourceSchema: this.pdfTextSource.schema,
            matrices: clone(nativePlaneBefore.first.matrices), x: Object.is(nativePlaneBefore.first.x, -0) ? "-0" : nativePlaneBefore.first.x,
            y: Object.is(nativePlaneBefore.first.y, -0) ? "-0" : nativePlaneBefore.first.y,
            layout: this._pdfPaintLayout() };
          nativePlane = this._pdfCurrentNativePlane();
        }
        if (nativePlane) {
          this.__pdfCurrentPlaneBefore = { kind: nativePlane.kind, first: { ...clone(nativePlane.first), x: nativePlane.first.x, y: nativePlane.first.y } };
          this.__pdfLayoutAnchor = this._pdfCurrentPlaneFirst(nativePlane);
          return;
        }
        this.__pdfCurrentPlaneBefore = null;
        const nominal = this._pdfNominalAnchorPoint();
        const validFrameAfter = validFrameBefore && this._pdfPaintFrameAnchor();
        if (validFrameAfter && Object.is(validFrameBefore.x, validFrameAfter.x) && Object.is(validFrameBefore.y, validFrameAfter.y)
            && this.calcOwnMatrix().every((value, index) => Object.is(value, before[index]))) {
          // An admitted CURRENT paint frame stays authoritative when native
          // measurement changed neither its layout nor its actual owner matrix.
          // Re-solving an unchanged admitted frame can discard its valid local ULPs.
          this.__pdfLayoutAnchor = validFrameAfter;
          return;
        }
        if (prior) {
          const next = this._pdfAnchorPoint(), after = this.calcOwnMatrix();
          const dx = before[0] * prior.x + before[2] * prior.y + before[4] - (after[0] * next.x + after[2] * next.y + after[4]);
          const dy = before[1] * prior.x + before[3] * prior.y + before[5] - (after[1] * next.x + after[3] * next.y + after[5]);
          if (dx !== 0 || dy !== 0) this.set({ left: this.left + dx, top: this.top + dy });
          const world = this.calcTransformMatrix().slice();
          const paint = this._pdfSolvePaintFrame(world, anchorBefore);
          let clipPosition = null;
          if (clipBefore) {
            const own = this.calcOwnMatrix(), inverse = fabric.util.invertTransform([own[0], own[1], own[2], own[3], 0, 0]);
            const delta = fabric.util.transformPoint(new fabric.Point(before[4] - own[4], before[5] - own[5]), inverse, true);
            clipPosition = this._pdfSolveClipTranslation(this.clipPath, world, clipWorldBefore,
              { left: this.clipPath.left + delta.x, top: this.clipPath.top + delta.y });
          }
          if (paint && (!clipBefore || clipPosition)) {
            this.pdfTextAuthoringFrame = paint;
            if (clipPosition && (this.clipPath.left !== clipPosition.left || this.clipPath.top !== clipPosition.top)) this.clipPath.set(clipPosition);
          } else {
            delete this.pdfTextAuthoringFrame;
            // Native no-op remeasurement must leave the existing relative clip
            // untouched. Inverse/recompose of an identical owner matrix changes
            // canonical Float64 translations even though the clip did not move.
            if (clipBefore && !this.calcOwnMatrix().every((value, index) => Object.is(value, before[index]))) {
              fabric.util.applyTransformToObject(this.clipPath, multiply(fabric.util.invertTransform(this.calcOwnMatrix()), clipBefore));
            }
          }
        }
        this.__pdfLayoutAnchor = this._pdfAnchorPoint();
      }
      renderCursorOrSelection() {
        if (!this.isEditing || !this.canvas) return;
        const ancestors = this.findAncestorsWithClipPath();
        if (!ancestors.length) return super.renderCursorOrSelection();
        const top = this.clearContextTop(true);
        if (!top) return;
        const dimensions = { width: top.canvas.width, height: top.canvas.height };
        const retina = this.canvas.getRetinaScaling();
        const viewport = multiply([retina, 0, 0, retina, 0, 0], this.canvas.viewportTransform);
        const createLayer = () => {
          const element = fabric.util.createCanvasElement();
          element.width = dimensions.width; element.height = dimensions.height;
          return element;
        };
        const matrixOf = (context) => { const m = context.getTransform(); return [m.a, m.b, m.c, m.d, m.e, m.f]; };
        // Ephemeral prototype copies retain Fabric's own shape/group drawing.
        // Only their clip compositor uses full overlay coordinates; no source
        // clip properties or cache canvases are changed while editing text.
        const shadow = (object, group) => {
          const copy = Object.create(object);
          copy.group = group; copy.parent = group; copy.canvas = undefined;
          copy.objectCaching = false; copy.ownCaching = false;
          copy.shouldCache = () => false;
          copy.needsItsOwnCache = () => false;
          copy._drawClipPath = (context, clip) => {
            if (!clip) return;
            const world = clip.absolutePositioned ? multiply(viewport, clip.calcTransformMatrix()) : multiply(matrixOf(context), clip.calcOwnMatrix());
            copy.drawClipPathOnCache(context, clip, mask(clip, world));
          };
          if (object.getObjects) copy._objects = object.getObjects().map((child) => shadow(child, copy));
          return copy;
        };
        const mask = (clip, matrix) => {
          const element = createLayer(), context = element.getContext("2d"), copy = shadow(clip);
          context.setTransform(...matrix);
          copy._transformDone = true;
          copy.drawObject(context, true, {});
          return element;
        };
        try {
          const layer = createLayer(), context = layer.getContext("2d");
          context.setTransform(...multiply(viewport, this.calcTransformMatrix()));
          const boundaries = this._getCursorBoundaries();
          if (this.selectionStart !== this.selectionEnd || this.inCompositionMode) this.renderSelection(context, boundaries);
          else this.renderCursor(context, boundaries);
          for (const owner of ancestors) {
            const clip = owner.clipPath;
            const world = clip.absolutePositioned ? multiply(viewport, clip.calcTransformMatrix()) : multiply(multiply(viewport, owner.calcTransformMatrix()), clip.calcOwnMatrix());
            this.drawClipPathOnCache(context, clip, mask(clip, world));
          }
          top.setTransform(1, 0, 0, 1, 0, 0); top.drawImage(layer, 0, 0);
          this.canvas.contextTopDirty = true;
        } finally { top.restore(); }
      }
      _capturedLogicalSource() {
        const source = this.pdfTextSource;
        if (source?.schema !== "figureStudio.pdfPositionedText.v2") return null;
        const api = typeof module === "object" && module.exports ? require("./pdf-logical-text-protocol.js") : globalThis.FigureStudioPdfLogicalTextProtocol;
        return api?.sourceStylesMatch(this, source) ? source : null;
      }
      _sourceFont(declaration) {
        return this.pdfTextSource?.fontSources?.[JSON.stringify([declaration.fontFamily, declaration.fontWeight || "normal", declaration.fontStyle || "normal"])];
      }
      _sourceLayout() {
        const source = this.pdfTextSource;
        const styledCharacters = typeof this.isEmptyStyles === "function" && !this.isEmptyStyles();
        if (source?.schema === "figureStudio.pdfPositionedText.v2") return this._capturedLogicalSource() && source?.glyphs?.length && this.text === source.text && this.fontFamily === source.fontFamily && number(this.fontSize) === source.fontSize && this.fontWeight === source.fontWeight && this.fontStyle === source.fontStyle && this._textLines?.length === 1 ? source : null;
        return !styledCharacters && source?.glyphs?.length && this.text === source.text && this.fontFamily === source.fontFamily && number(this.fontSize) === source.fontSize && this.fontWeight === source.fontWeight && this.fontStyle === source.fontStyle && this._textLines?.length === 1 ? source : null;
      }
      _mapped(text, declaration) {
        const source = this.pdfTextSource;
        if (source?.schema === "figureStudio.pdfPositionedText.v2") {
          const font = this._sourceFont(declaration);
          if (!font?.sourceEmbeddedProgram) return { text, declaration };
          if (Object.hasOwn(font.map, text)) return { text: font.map[text], declaration };
          return { text, declaration: { ...declaration, fontFamily: source.fallbackFont || "Arial" } };
        }
        if (!this._usesSourceGlyphMap() || !source?.map || !Object.keys(source.map).length || declaration.fontFamily !== source.fontFamily) return { text, declaration };
        if (Object.hasOwn(source.map, text)) return { text: source.map[text], declaration };
        return { text, declaration: { ...declaration, fontFamily: source.fallbackFont || "Arial" } };
      }
      _usesSourceGlyphMap() {
        const source = this.pdfTextSource;
        // Glyph codes belong to an embedded browser font program. Unembedded
        // system families use their ordinary Unicode repertoire after editing.
        // Registered programs identify older project files without this flag.
        return source?.sourceEmbeddedProgram === true || (source?.sourceEmbeddedProgram !== false && Boolean(fontProgramsByDocument.get(globalThis.document)?.has(source?.fontFamily)));
      }
      _measureChar(text, declaration, previous, previousDeclaration) {
        const source = this.pdfTextSource;
        if (source?.schema === "figureStudio.pdfPositionedText.v2" && /^\s+$/.test(text)) {
          const advance = this._sourceFont(declaration)?.unicodeAdvances?.[text];
          if (Number.isFinite(advance)) return { width: advance * declaration.fontSize, kernedWidth: advance * declaration.fontSize };
        }
        if (source && declaration.fontFamily === source.fontFamily && /^\s+$/.test(text) && Number.isFinite(source.unicodeAdvances?.[text])) {
          const width = source.unicodeAdvances[text] * declaration.fontSize;
          return { width, kernedWidth: width };
        }
        const glyph = this._mapped(text, declaration);
        const prior = previous ? this._mapped(previous, previousDeclaration || declaration) : { text: previous, declaration: previousDeclaration };
        return super._measureChar(glyph.text, glyph.declaration, prior.text, prior.declaration);
      }
      _measureLine(lineIndex) {
        const measured = super._measureLine(lineIndex);
        const source = lineIndex === 0 && this._sourceLayout();
        if (!source) return measured;
        const bounds = this.__charBounds[0];
        let right = 0;
        source.glyphs.forEach((glyph, index) => {
          const declaration = this.getCompleteStyleDeclaration(0, glyph.charIndex);
          const width = /^\s+$/.test(glyph.unicode) ? this._measureChar(glyph.unicode, declaration).width : super._measureChar(glyph.fontChar, declaration).width;
          const advance = source.glyphs[index + 1] ? source.glyphs[index + 1].x - glyph.x : width;
          for (let offset = 0; offset < glyph.charCount; offset++) {
            const charIndex = glyph.charIndex + offset;
            if (!bounds[charIndex]) continue;
            bounds[charIndex].left = glyph.x + advance * offset / Math.max(1, glyph.charCount);
            bounds[charIndex].width = advance / Math.max(1, glyph.charCount);
            bounds[charIndex].kernedWidth = advance / Math.max(1, glyph.charCount);
            bounds[charIndex].deltaY = glyph.y;
          }
          right = Math.max(right, glyph.x + width);
        });
        bounds[this._textLines[0].length] = { left: right, width: 0, kernedWidth: 0, height: this.fontSize, deltaY: 0 };
        return { ...measured, width: right };
      }
      _pdfRenderChar(method, context, lineIndex, charIndex, text, left, top, glyphToken) {
        const raster = globalThis.FigureStudioPdfiumTextRasterizer;
        const declaration = this.getCompleteStyleDeclaration(lineIndex, charIndex);
        const embedded = this.pdfTextSource?.schema === "figureStudio.pdfPositionedText.v2"
          ? this._sourceFont(declaration)?.sourceEmbeddedProgram === true
          : this._usesSourceGlyphMap() && declaration.fontFamily === this.pdfTextSource?.fontFamily;
        if (!raster || !embedded) return super._renderChar(method, context, lineIndex, charIndex, text, left, top);
        const unsupported=Boolean(this.shadow || this.path || this.direction === "rtl" || this.mask || this.filters?.length || this.resizeFilter
          || this.figureStudioAppearanceStack || this.figureStudioAppearanceMeta);
        const request={method,family:declaration.fontFamily,weight:declaration.fontWeight,style:declaration.fontStyle,fontSize:declaration.fontSize,unsupported};
        if(method==="fillText" && !unsupported && raster.paintPrimitiveFill && this.constructor===PdfPositionedText
            && primitiveBinding.complete && this.getCompleteStyleDeclaration===primitiveBinding.complete
            && primitiveBinding.methods.every(([name,expected])=>typeof expected==="function" && this[name]===expected)
            && !declaration.stroke && !declaration.textBackgroundColor && !this.textBackgroundColor && !this.backgroundColor && !declaration.backgroundColor
            && !declaration.underline && !declaration.overline && !declaration.linethrough
            && !this.underline && !this.overline && !this.linethrough) {
          const style=this._getStyleDeclaration(lineIndex,charIndex),prototype=style && Object.getPrototypeOf(style);
          const delta=style && Object.getOwnPropertyDescriptor(style,"deltaY"),background=style && Object.getOwnPropertyDescriptor(style,"textBackgroundColor");
          if(style && (prototype===Object.prototype || prototype===null)
              && (!delta || Object.hasOwn(delta,"value") && (delta.value===undefined || Number.isFinite(delta.value)))
              && (!background || Object.hasOwn(background,"value") && !background.value)) {
            // Literal stock _renderChar: only truthy raw-style deltaY shifts
            // the baseline. Primitive fill has numeric zero filler offsets.
            const y=delta?.value ? top+delta.value : top;
            const painted=raster.paintPrimitiveFill(context,{...request,text,x:left,y,fill:declaration.fill,preparation:false},glyphToken);
            if(painted===true)return;
            if(painted===false)return super._renderChar(method,context,lineIndex,charIndex,text,left,top);
          }
        }
        // Fabric still sets the exact character font, deltaY and paint offsets.
        // The receiver-correct facade intercepts only its final fillText call,
        // after current-native glyph planes and every parent transform apply.
        return raster.withFillPainter(context, request, painter => super._renderChar(method, painter, lineIndex, charIndex, text, left, top),undefined,glyphToken);
      }
      _renderChars(method, context, line, left, top, lineIndex) {
        const nativePlane = this._pdfCurrentNativePlane();
        if (nativePlane) {
          if (nativePlane.kind === "source") {
            for (const entry of nativePlane.entries) {
              const glyph = this.pdfTextSource.glyphs.find(glyph => glyph.charIndex === entry.charIndex);
              if (!/^\s+$/u.test(glyph.unicode)) this._pdfWithCurrentPlane(context, entry, () =>
                this._pdfRenderChar(method, context, 0, glyph.charIndex, glyph.fontChar, entry.x, entry.y,glyph));
            }
          } else {
            this._pdfWithCurrentPlane(context, nativePlane.first, () => {
              const baseline = lineIndex === 0 ? nativePlane.first.y : nativePlane.first.y + this._pdfCurrentLineOffset(lineIndex);
              this._textLines[lineIndex].forEach((char, charIndex) => {
                const declaration = this.getCompleteStyleDeclaration(lineIndex, charIndex), glyph = this._mapped(char, declaration), box = this.__charBounds[lineIndex][charIndex];
                const original = this._getStyleDeclaration(lineIndex, charIndex), styles = this.styles, fallback = glyph.declaration.fontFamily !== declaration.fontFamily;
                if (fallback) this.styles = { ...styles, [lineIndex]: { ...styles?.[lineIndex], [charIndex]: { ...original, fontFamily: glyph.declaration.fontFamily } } };
                try { this._pdfRenderChar(method, context, lineIndex, charIndex, glyph.text,
                  box.left === 0 ? nativePlane.first.x : nativePlane.first.x + box.left, box.deltaY ? baseline + box.deltaY : baseline); }
                finally { if (fallback) this.styles = styles; }
              });
            });
          }
          return;
        }
        const paint = lineIndex === 0 && this._pdfPaintFrameAnchor();
        const baseline = paint ? paint.y : top - this.getHeightOfLineImpl(lineIndex) * this._fontSizeFraction;
        if (paint) left = paint.x;
        const source = lineIndex === 0 && this._sourceLayout();
        if (source) {
          for (const glyph of source.glyphs) if (!/^\s+$/.test(glyph.unicode)) this._pdfRenderChar(method, context, 0, glyph.charIndex, glyph.fontChar, left + glyph.x, baseline + glyph.y,glyph);
          return;
        }
        // Drawing individually permits explicit fallback for a newly typed glyph
        // missing from a subset font, rather than rendering an invisible square.
        for (let index = 0; index < line.length; index++) {
          if (/^\s+$/.test(line[index])) continue;
          const declaration = this.getCompleteStyleDeclaration(lineIndex, index);
          const glyph = this._mapped(line[index], declaration);
          const original = this._getStyleDeclaration(lineIndex, index), styles = this.styles;
          const fallback = glyph.declaration.fontFamily !== declaration.fontFamily;
          if (fallback) this.styles = { ...styles, [lineIndex]: { ...styles?.[lineIndex], [index]: { ...original, fontFamily: glyph.declaration.fontFamily } } };
          try { this._pdfRenderChar(method, context, lineIndex, index, glyph.text, left + this.__charBounds[lineIndex][index].left, baseline); }
          finally { if (fallback) this.styles = styles; }
        }
      }
      getSvgSpanStyles(declaration, useWhiteSpace) {
        const styles = super.getSvgSpanStyles(declaration, useWhiteSpace);
        const family = declaration?.fontFamily;
        if (!this.pdfTextSource || typeof family !== "string" || !/^(?:serif|sans-serif|monospace|cursive|fantasy|system-ui|ui-serif|ui-sans-serif|ui-monospace|ui-rounded|emoji|math|fangsong)$/i.test(family.trim())) return styles;
        // Quoting a CSS generic family turns it into a literal font name.
        // Keep edited PDF labels on the same generic family as their Canvas text.
        return styles.replace(`font-family: '${escapeXml(family)}'; `, `font-family: ${escapeXml(family)}; `);
      }
      _getSVGTextAndBg(top, left) {
        const source = this._sourceLayout();
        if (!source) {
          const result = super._getSVGTextAndBg(top, left);
          if (!this.pdfTextSource) return result;
          const spans = [];
          let lineTop = top;
          for (let lineIndex = 0; lineIndex < this._textLines.length; lineIndex++) {
            const paint = lineIndex === 0 && this._pdfPaintFrameAnchor();
            const baseline = paint ? paint.y : lineTop + this.getHeightOfLineImpl(lineIndex) * (1 - this._fontSizeFraction);
            const lineLeft = paint ? paint.x : left + this._getLineLeftOffset(lineIndex);
            this._textLines[lineIndex].forEach((char, index) => {
              const glyph = this._mapped(char, this.getCompleteStyleDeclaration(lineIndex, index));
              const box = this.__charBounds[lineIndex][index];
              const span = this._createTextCharSpan(xmlGlyph(glyph.text, char), glyph.declaration, lineLeft + box.left, baseline, box);
              spans.push(span.replace("<tspan ", `<tspan data-pdf-unicode="${escapeXml(char)}" data-pdf-glyph-map="${escapeXml(JSON.stringify([{ unicode: char, fontChar: glyph.text }]))}" `));
            });
            lineTop += this.getHeightOfLine(lineIndex);
          }
          return { ...result, textSpans: spans };
        }
        const baseline = top + this.getHeightOfLineImpl(0) * (1 - this._fontSizeFraction);
        if (source.schema === "figureStudio.pdfPositionedText.v2") {
          const spans = source.glyphs.map(glyph => {
            const declaration = this.getCompleteStyleDeclaration(0, glyph.charIndex);
            const attrs = `data-pdf-unicode="${escapeXml(glyph.unicode)}" data-pdf-glyph-map="${escapeXml(JSON.stringify([{ unicode: glyph.unicode, fontChar: glyph.fontChar }]))}"`;
            return `<tspan ${attrs} x="${left + glyph.x}" y="${baseline + glyph.y}" style="${this.getSvgSpanStyles(declaration, true)}">${escapeXml(xmlGlyph(glyph.fontChar, glyph.unicode))}</tspan>`;
          });
          return { textBgRects: [], textSpans: spans };
        }
        const attrs = `data-pdf-unicode="${escapeXml(this.text)}" data-pdf-glyph-map="${escapeXml(JSON.stringify(source.glyphs.map(({ unicode, fontChar }) => ({ unicode, fontChar }))))}"`;
        const x = source.glyphs.map((glyph) => left + glyph.x).join(" ");
        const y = source.glyphs.map((glyph) => baseline + glyph.y).join(" ");
        return { textBgRects: [], textSpans: [`<tspan ${attrs} x="${x}" y="${y}">${escapeXml(source.glyphs.map((glyph) => xmlGlyph(glyph.fontChar, glyph.unicode)).join(""))}</tspan>`] };
      }
      getFontSubstitutions() {
        const source = this.pdfTextSource;
        if (this._sourceLayout()) return [];
        if (source?.schema === "figureStudio.pdfPositionedText.v2") {
          const missing = new Map();
          this._textLines.forEach((line, lineIndex) => line.forEach((char, charIndex) => {
            const declaration = this.getCompleteStyleDeclaration(lineIndex, charIndex);
            const family = declaration.fontFamily;
            const font = this._sourceFont(declaration);
            if (font?.sourceEmbeddedProgram && !Object.hasOwn(font.map, char)) missing.set(`${family}\u0000${char}`, { unicode: char, sourceFamily: family, substitutedFamily: source.fallbackFont || "Arial" });
          }));
          return Array.from(missing.values());
        }
        if (!this._usesSourceGlyphMap() || !source?.map || !Object.keys(source.map).length || this.fontFamily !== source.fontFamily) return [];
        const missing = new Set();
        this._textLines.forEach((line, lineIndex) => line.forEach((char, charIndex) => {
          if (this.getCompleteStyleDeclaration(lineIndex, charIndex).fontFamily === source.fontFamily && !Object.hasOwn(source.map, char)) missing.add(char);
        }));
        return Array.from(missing, (unicode) => ({ unicode, sourceFamily: source.fontFamily, substitutedFamily: source.fallbackFont }));
      }
      toObject(properties = []) {
        const owner = Object.getPrototypeOf(this);
        const currentHistoryFacade = this.constructor === PdfPositionedText && Object.getPrototypeOf(owner) === PdfPositionedText.prototype
            && Object.hasOwn(owner, "pdfTextAuthoringFrame") && this.pdfTextSource === owner.pdfTextSource && this._pdfPaintFrameAnchor();
        const currentPlaneFacade = this.constructor === PdfPositionedText && Object.getPrototypeOf(owner) === PdfPositionedText.prototype
            && Object.hasOwn(owner, "pdfTextAuthoringPlane") && this.pdfTextSource === owner.pdfTextSource && this._pdfCurrentNativePlane()?.kind === "authored";
        return { ...super.toObject([...properties, ...META_PROPS]), pdfTextSource: clone(this.pdfTextSource),
          ...(Object.hasOwn(this, "pdfTextAuthoringFrame") || currentHistoryFacade ? { pdfTextAuthoringFrame: clone(this.pdfTextAuthoringFrame) } : {}),
          ...(Object.hasOwn(this, "pdfTextAuthoringPlane") || currentPlaneFacade ? { pdfTextAuthoringPlane: clone(this.pdfTextAuthoringPlane) } : {}) };
      }
      static fromObject(object, options) {
        if (object?.pdfTextSource?.schema === "figureStudio.pdfPositionedText.v2") return this._fromObject({ ...object, styles: fabric.util.stylesFromArray(object.styles || {}, object.text) }, { ...options, extraParam: "text" });
        return this._fromObject(object, { ...options, extraParam: "text" });
      }
    }
    fabric.classRegistry?.setClass(PdfPositionedText);
    classByFabric.set(fabric, PdfPositionedText);
    bindScenePaint(PdfPositionedText, "text", ["render", "drawObject", "_render", "calcOwnMatrix", "calcTransformMatrix",
      "_renderChar", "_renderChars", "_pdfRenderChar", "_pdfWithCurrentPlane", "_pdfCurrentNativePlane", "_renderText", "_renderTextFill", "_renderTextStroke",
      "_renderTextLine", "_renderTextCommon", "needsItsOwnCache"], fabric);
    return PdfPositionedText;
  }

  // Prepare only derived display resources from detached, finalized IText.
  // Thumbnail preparation retains literal native ancestor transforms. Explicit
  // screen preparation shares the first live paint's admitted world transform.
  // No await occurs in a Canvas scope; this never publishes paint pixels.
  async function prepareImportedTextDisplayAsync(roots, options = {}) {
    const raster=globalThis.FigureStudioPdfiumTextRasterizer;
    if(!raster?.withPreparation || !raster.diagnostics().ready)return {preparedTextObjects:0,uiYieldCount:0};
    const Text=registerTextClass(options.fabric),document=options.document || globalThis.document;
    const surface=document.createElement('canvas');surface.width=2;surface.height=2;
    const context=surface.getContext('2d'),now=()=>globalThis.performance?.now?.() ?? Date.now();
    const maxSliceMs=Number.isFinite(options.maxSliceMs)?Math.max(0,options.maxSliceMs):8;
    const yieldToUi=options.yieldToUi || (()=>new Promise(resolve=>setTimeout(resolve,0)));
    const pending=Array.from(roots || [],object=>({object,ancestors:[]}));
    let started=now(),preparedTextObjects=0,uiYieldCount=0;
    const current=()=>{options.signal?.throwIfAborted();options.current?.();};
    try{
      while(pending.length){
        current();const {object,ancestors}=pending.pop();
        if(object.canvas)throw new Error('PDF text display preparation requires detached import objects.');
        const children=object.getObjects?.() || [];
        for(let i=children.length-1;i>=0;i--)pending.push({object:children[i],ancestors:[...ancestors,object]});
        if(object instanceof Text && [object,...ancestors].every(owner=>owner.objectCaching===false
            && owner.visible!==false && owner.opacity===1 && !owner.shadow
            && (!owner.globalCompositeOperation || owner.globalCompositeOperation==='source-over') && owner.needsItsOwnCache?.()!==true)){
          let collected;
          context.save();
          try{
            context.setTransform(...options.contextTransform);
            context.transform(...options.viewportTransform);
            const matrix=options.screenSceneTransform && context.getTransform();
            const shared=matrix && options.screenSceneTransform(context,object,[matrix.a,matrix.b,matrix.c,matrix.d,matrix.e,matrix.f]);
            if(!shared)for(const owner of [...ancestors,object])context.transform(...owner.calcOwnMatrix());
            if(raster.collectPreparation && raster.prepareCollectedAsync)collected=raster.collectPreparation(context,()=>object._render(context));
            else raster.withPreparation(context,()=>object._render(context));
            preparedTextObjects++;
          }finally{context.restore();}
          if(collected){
            const prepared=await raster.prepareCollectedAsync(collected,{maxSliceMs,yieldToUi,current,signal:options.signal});
            uiYieldCount+=prepared.uiYieldCount;
          }
        }
        if(now()-started>=maxSliceMs){current();await yieldToUi();current();uiYieldCount++;started=now();}
      }
      current();return {preparedTextObjects,uiYieldCount};
    }finally{surface.width=0;surface.height=0;}
  }

  async function registerFonts(fonts, options = {}) {
    const document = options.document || globalThis.document;
    const FontFaceCtor = options.FontFace || globalThis.FontFace;
    const loaded = [], failures = [];
    const programs = document && (fontProgramsByDocument.get(document) || new Map());
    if (document && !fontProgramsByDocument.has(document)) fontProgramsByDocument.set(document, programs);
    for (const input of fonts || []) {
      options.current?.();
      const font = { family: input?.family, dataUrl: input?.dataUrl, weight: input?.weight, style: input?.style };
      if (!font?.family || !font.dataUrl) continue;
      if (!/^data:(?:font\/|application\/(?:font|octet-stream|x-font))/i.test(font.dataUrl)) { failures.push({ family: font.family, reason: "Font is not an embedded program." }); continue; }
      try {
        if (!FontFaceCtor || !document?.fonts) throw new Error("Browser font loading is unavailable.");
        if (programs.get(font.family) !== font.dataUrl) {
          const face = new FontFaceCtor(font.family, `url(${JSON.stringify(font.dataUrl)})`, { weight: String(font.weight || "normal"), style: font.style || "normal" });
          await face.load();
          options.current?.();
          document.fonts.add(face);
          programs.set(font.family, font.dataUrl);
        }
        // No asynchronous paint completion: native font resources settle with
        // the existing awaited FontFace registration before scene installation.
        await globalThis.FigureStudioPdfiumTextRasterizer?.registerFont(font, options);
        options.current?.();
        loaded.push(font.family);
      } catch (error) { options.current?.();failures.push({ family: font.family, reason: String(error.message || error) }); }
    }
    return { loaded, failures };
  }

  function embeddedFonts(root) {
    const fonts = [];
    for (const sheet of root.querySelectorAll("style")) for (const rule of String(sheet.textContent || "").matchAll(/@font-face\s*\{([^}]+)\}/gi)) {
      const family = rule[1].match(/font-family\s*:\s*["']?([^;"']+)["']?\s*;/i)?.[1]?.trim();
      const dataUrl = rule[1].match(/src\s*:\s*url\(\s*["']?(data:[^)'"\s]+)["']?\s*\)/i)?.[1];
      if (family && dataUrl) fonts.push({ family, dataUrl });
    }
    return fonts;
  }

  function metadata(element, sourceOrder, path, type) {
    return { figureType: type, name: element.getAttribute("aria-label") || element.getAttribute("data-name") || element.id || `PDF ${type}`, figureStudioSvgElementId: element.id || "", figureStudioSvgElementTag: tag(element), figureStudioSvgGroupPath: path.slice(), figureStudioSvgSourceOrder: sourceOrder, selectable: true, evented: true, objectCaching: false };
  }

  function clipReference(element) {
    for (let current = element; current?.getAttribute; current = current.parentElement) {
      const value = ownStyle(current, "clip-path");
      if (value) return value;
    }
    return "";
  }

  function validateKnockoutMarker(element, entries) {
    if (!importerApi()?.isTrustedKnockoutSources(entries)) throw new Error("Knockout SVG masks require the current importer source map.");
    const entry = entries.find(item => item.key === element.getAttribute("data-pdf-knockout-import-key"));
    if (!entry) throw new Error("A knockout marker has no matching source scope.");
    for (const [key, value] of Object.entries({ "data-pdf-knockout-source-id": entry.sourceId, "data-pdf-knockout-source-sha256": entry.sourceSha256, "data-pdf-knockout-page": entry.pageNumber, "data-pdf-knockout-start": entry.scopeStart, "data-pdf-knockout-end": entry.scopeEnd, "data-pdf-knockout-binding": entry.schema })) {
      if (element.getAttribute(key) !== String(value)) throw new Error(`Knockout marker changed its ${key} source proof.`);
    }
    return entry;
  }

  function extractKnockoutRoots(root, options) {
    const marked = Array.from(root.querySelectorAll("[data-pdf-knockout-import-key]"));
    if (!marked.length) {
      if (options.knockoutSources?.length) throw new Error("The proved knockout source map lost its SVG scopes.");
      return new Map();
    }
    const entries = options.knockoutSources, result = new Map(), view = viewport(root);
    if (Array.from(root.querySelectorAll("style")).some(sheet => String(sheet.textContent || "").replace(/@font-face\s*\{[^}]+\}/gi, "").trim())) throw new Error("Knockout ancestors with geometry CSS are not qualified.");
    for (const element of marked) {
      const entry = validateKnockoutMarker(element, entries);
      if (result.has(entry.key)) throw new Error("An imported knockout source scope appeared twice.");
      // Discard only the derived visual subtree, after checking its safety. Its
      // mask paths never become duplicate canonical editable leaves.
      for (const node of [element, ...element.querySelectorAll("*")]) {
        if (["script", "foreignobject", "iframe", "object", "embed"].includes(tag(node))) throw new Error("Unsafe content in knockout SVG.");
        for (const attribute of node.attributes) if (/^on/i.test(attribute.name) || /^\s*javascript:/i.test(attribute.value)) throw new Error("Unsafe attribute in knockout SVG.");
      }
      for (let ancestor = element.parentElement; ancestor; ancestor = ancestor.parentElement) {
        knockoutApi().parseSvgTransform(ancestor.getAttribute("transform") || "");
        if (ancestor !== root && tag(ancestor) === "svg" || number(ownStyle(ancestor, "opacity", "1"), 1) !== 1 || ancestor.hasAttribute("mask") || ancestor.hasAttribute("filter") || /mix-blend-mode/.test(ancestor.getAttribute("style") || "")) throw new Error("Knockout ancestor compositing is outside the proved neutral envelope.");
        if (ancestor === root) break;
      }
      const proxy = root.ownerDocument.createElementNS(SVG_NS, "path"), [x0, y0, x1, y1] = entry.source.bbox;
      proxy.setAttribute("d", `M ${x0} ${y0} L ${x1} ${y0} L ${x1} ${y1} L ${x0} ${y1} Z`);
      proxy.setAttribute("transform", `matrix(${entry.ancestorTransform.join(" ")})`);
      proxy.setAttribute("fill", "none");
      proxy.setAttribute("stroke", "none");
      proxy.setAttribute("id", `pdf-knockout-${entry.key}`);
      proxy.setAttribute("data-pdf-knockout-proxy-key", entry.key);
      element.replaceWith(proxy);
      if (JSON.stringify(compositeMatrix(proxy, root, view.matrix)) !== JSON.stringify(entry.source.sourceToViewport)) throw new Error("Knockout SVG mapping differs from its proved source viewport.");
      result.set(entry.key, entry);
    }
    if (result.size !== entries.length) throw new Error("Not every proved knockout source was materialized once.");
    return result;
  }

  function materializeKnockoutProxy(proxy, entry, fabric) {
    const api = knockoutApi();
    if (!api) throw new Error("The canonical knockout compositor is unavailable.");
    const group = api.createScene(entry.source, fabric);
    if (!proxy.clipPath) return group;
    // The source parent/child BBoxes already belong to the K scene. A parsed
    // ordinary ancestor clip belongs to a neutral wrapper, never a new K effect.
    if (proxy.clipPath.absolutePositioned) throw new Error("Absolute ancestor clips are outside the proved knockout import envelope.");
    const clip = proxy.clipPath, clipWorld = multiply(proxy.calcTransformMatrix(), clip.calcTransformMatrix());
    const Wrapper = registerGroupClass(fabric);
    const wrapper = new Wrapper([group], { objectCaching: false, interactive: false, subTargetCheck: true, selectable: true, evented: true });
    fabric.util.applyTransformToObject(clip, multiply(fabric.util.invertTransform(wrapper.calcTransformMatrix()), clipWorld));
    clip.absolutePositioned = false;
    wrapper.clipPath = clip;
    return wrapper;
  }

  function initializeImportedClipRuleDefaults(objects) {
    // Fabric's SVG parser leaves fillRule undefined when source clip-rule is
    // absent. Give only that implicit native default a stable serialized value
    // before the imported clipping tree is published or captured for history.
    const pending = Array.from(objects || []), seen = new Set();
    let initialized = 0;
    while (pending.length) {
      const object = pending.pop();
      if (!object || seen.has(object)) continue;
      seen.add(object);
      pending.push(...Array.from(object.getObjects?.() || []));
      const clips = object.clipPath ? [object.clipPath] : [];
      while (clips.length) {
        const clip = clips.pop();
        if (!clip || seen.has(clip)) continue;
        seen.add(clip);
        if (clip.fillRule === undefined) { clip.set("fillRule", "nonzero"); initialized++; }
        clips.push(...Array.from(clip.getObjects?.() || []));
        if (clip.clipPath) clips.push(clip.clipPath);
      }
    }
    return initialized;
  }

  function clipSignature(clip, matrix) {
    const geometry = { type: clip.type, matrix: matrix.map((value) => Math.round(value * 1e7) / 1e7), path: clip.path, points: clip.points, width: clip.width, height: clip.height, radius: clip.radius, rx: clip.rx, ry: clip.ry, fillRule: clip.fillRule };
    if (clip.clipPath) geometry.clip = clipSignature(clip.clipPath, multiply(matrix, clip.clipPath.calcTransformMatrix()));
    if (clip.getObjects) geometry.children = clip.getObjects().map((child) => clipSignature(child, multiply(matrix, child.calcOwnMatrix())));
    return JSON.stringify(geometry);
  }

  function hoistSharedClip(group, reference, fabric, onDiagnostic) {
    let matching = [];
    let hasNativeClip = false;
    const visit = (object) => {
      if (object.pdfNativeRectClip) { hasNativeClip = true; return; }
      if (reference && object.clipPath && object.__pdfSvgClipRef === reference) matching.push(object);
      else object.getObjects?.().forEach(visit);
    };
    if (reference) group.getObjects().forEach(visit);
    if (hasNativeClip) return 0;
    if (matching.length < 2) {
      // PDF producers can create several distinct clip IDs for the same page
      // rectangle. A state scope can share that clip only when every descendant
      // is clipped and the world geometry is exactly the same for all of them.
      const all = [];
      let unclipped = 0;
      const visitAll = (object) => {
        if (object.pdfNativeRectClip) unclipped++;
        else if (object.clipPath) all.push(object);
        else if (object.getObjects) object.getObjects().forEach(visitAll);
        else unclipped++;
      };
      group.getObjects().forEach(visitAll);
      if (unclipped || all.length < 2) return 0;
      matching = all;
    }
    const world = multiply(matching[0].calcTransformMatrix(), matching[0].clipPath.calcTransformMatrix());
    const signature = clipSignature(matching[0].clipPath, world);
    const different = matching.find((object) => clipSignature(object.clipPath, multiply(object.calcTransformMatrix(), object.clipPath.calcTransformMatrix())) !== signature);
    if (different) {
      onDiagnostic?.({ code: "shared-clip-transform-mismatch", reference, count: matching.length, first: signature, different: clipSignature(different.clipPath, multiply(different.calcTransformMatrix(), different.clipPath.calcTransformMatrix())) });
      return 0;
    }
    const clip = matching[0].clipPath;
    for (const object of matching) { object.set("clipPath", undefined); delete object.__pdfSvgClipRef; }
    fabric.util.applyTransformToObject(clip, multiply(fabric.util.invertTransform(group.calcTransformMatrix()), world));
    group.set("clipPath", clip);
    group.__pdfSvgClipRef = reference || "shared-identical-world-clip";
    return matching.length;
  }

  function sharedClipRuns(children, descriptor, fabric) {
    const result = [];
    let run = [], signature = "", world = null, scopes = 0, leaves = 0;
    const flush = () => {
      if (run.length < 2) { result.push(...run); run = []; return; }
      const clip = run[0].clipPath;
      const first = run[0];
      run.forEach((object) => { object.set("clipPath", undefined); delete object.__pdfSvgClipRef; });
      const group = new (registerGroupClass(fabric))(run, { subTargetCheck: true, interactive: false, objectCaching: false, selectable: true, evented: true });
      fabric.util.applyTransformToObject(clip, multiply(fabric.util.invertTransform(group.calcTransformMatrix()), world));
      const key = `${descriptor.key}:shared-clip-${scopes + 1}`;
      group.set({ clipPath: clip, figureType: "group", name: "PDF clipped contents", figureStudioSvgGroupPath: [...descriptor.path, key], figureStudioSvgSourceOrder: first.figureStudioSvgSourceOrder, figureStudioSvgGroupMeta: { schema: "figureStudio.svgNamedGroup.v1", sourceKey: key, parentSourceKey: descriptor.key, path: [...descriptor.path, key], depth: descriptor.path.length, canvasRepresentation: "editable-group", sharedClipScope: true } });
      group.__pdfSvgClipRef = "shared-identical-world-clip";
      group.setCoords?.();
      result.push(group); scopes++; leaves += run.length; run = [];
    };
    for (const object of children) {
      if (!object.clipPath || object.pdfNativeRectClip) { flush(); result.push(object); signature = ""; continue; }
      const candidateWorld = multiply(object.calcTransformMatrix(), object.clipPath.calcTransformMatrix());
      const candidate = clipSignature(object.clipPath, candidateWorld);
      if (signature !== candidate) { flush(); signature = candidate; world = candidateWorld; }
      run.push(object);
    }
    flush();
    return { children: result, scopes, leaves };
  }

  function cloneClip(clip, fabric, depth = 0) {
    if (!clip || depth > 128) throw new Error("The clipping tree cannot be cloned safely.");
    if (depth > 0 && clip.absolutePositioned) throw new Error("Nested absolute clipping requires a separate coordinate-preserving release.");
    if (clip.inverted) throw new Error("Inverted clipping must remain in its group while editing.");
    const props = clip.toObject();
    for (const key of ["type", "objects", "path", "points", "clipPath", "layoutManager"]) delete props[key];
    for (const key of ["width", "height", "radius", "rx", "ry", "strokeWidth"]) if (clip[key] !== undefined) props[key] = clip[key];
    let result;
    const type = String(clip.constructor?.type || clip.type || "").toLowerCase();
    if (clip.getObjects) {
      const originals = clip.getObjects();
      const children = originals.map((child) => cloneClip(child, fabric, depth + 1));
      result = new fabric.Group(children, props);
      // Group constructors rebase their children. Restore the original local
      // matrices before restoring the group's own matrix and cache bounds.
      children.forEach((child, index) => fabric.util.applyTransformToObject(child, originals[index].calcOwnMatrix()));
      result.set({ width: clip.width, height: clip.height });
    } else if (type === "path" && fabric.Path) result = new fabric.Path(clone(clip.path), props);
    else if (["polygon", "polyline"].includes(type) && fabric[clip.constructor.type]) result = new fabric[clip.constructor.type](clone(clip.points), props);
    else if (type === "line" && fabric.Line) result = new fabric.Line([clip.x1, clip.y1, clip.x2, clip.y2], props);
    else if (["rect", "circle", "ellipse", "triangle"].includes(type) && fabric[clip.constructor.type]) result = new fabric[clip.constructor.type](props);
    else throw new Error(`Unsupported clipping shape: ${type || "unknown"}.`);
    fabric.util.applyTransformToObject(result, clip.calcOwnMatrix());
    result.absolutePositioned = false;
    result.inverted = Boolean(clip.inverted);
    if (clip.clipPath) result.clipPath = cloneClip(clip.clipPath, fabric, depth + 1);
    result.setCoords?.();
    return result;
  }

  function clipWorldMatrix(owner, clip) {
    return clip.absolutePositioned ? clip.calcTransformMatrix() : multiply(owner.calcTransformMatrix(), clip.calcTransformMatrix());
  }

  function prepareGroupRelease(group, options = {}) {
    const fabric = options.fabric;
    const message = "This clipping shape cannot be released safely. Edit its contents with Point Selection or group isolation.";
    if (!group?.getObjects || !fabric?.util?.applyTransformToObject) return { status: "blocked", message, reason: "missing-group-or-fabric" };
    if (number(group.opacity, 1) < 1 || (group.globalCompositeOperation && group.globalCompositeOperation !== "source-over")) return { status: "blocked", message: "This group uses transparency. Edit its contents with Point Selection or group isolation to preserve the appearance.", reason: "isolated-group-compositing" };
    if (!group.clipPath) return { status: "ready", preparedChildCount: 0, inheritedClip: false };
    const plans = [];
    try {
      const parentWorld = clipWorldMatrix(group, group.clipPath);
      for (const child of group.getObjects()) {
        const inherited = cloneClip(group.clipPath, fabric);
        fabric.util.applyTransformToObject(inherited, parentWorld);
        let merged = inherited;
        if (child.clipPath) {
          const existing = cloneClip(child.clipPath, fabric);
          const existingWorld = clipWorldMatrix(child, child.clipPath);
          let tail = inherited, tailWorld = parentWorld;
          while (tail.clipPath) { tail = tail.clipPath; tailWorld = multiply(tailWorld, tail.calcTransformMatrix()); }
          // Clip paths compose by intersection. Keep each original clipping
          // operation's frame, rather than using a bounding-box group whose
          // axis-aligned frame differs from a rotated/sheared clipping shape.
          fabric.util.applyTransformToObject(existing, multiply(fabric.util.invertTransform(tailWorld), existingWorld));
          tail.clipPath = existing;
        }
        fabric.util.applyTransformToObject(merged, multiply(fabric.util.invertTransform(child.calcTransformMatrix()), merged.calcTransformMatrix()));
        merged.absolutePositioned = false;
        plans.push({ child, previous: child.clipPath, clip: merged });
      }
    } catch (error) { return { status: "blocked", message, reason: "unsupported-clipping-tree", detail: String(error.message || error) }; }
    // Preparation above is read-only. Commit only after every independent clip
    // clone and intersection has succeeded, and roll back an unexpected setter.
    try { plans.forEach(({ child, clip }) => child.set("clipPath", clip)); }
    catch (error) {
      plans.forEach(({ child, previous }) => child.set("clipPath", previous));
      return { status: "blocked", message, reason: "clip-commit-failed", detail: String(error.message || error) };
    }
    return { status: "ready", preparedChildCount: plans.length, inheritedClip: true };
  }

  async function groupHierarchy(objects, descriptors, fabric, onDiagnostic, checkpoint) {
    const byKey = new Map(descriptors.map((row) => [row.key, row]));
    const members = new Map(descriptors.map((row) => [row.key, []]));
    const roots = [];
    for (const object of objects) {
      const key = object.figureStudioSvgGroupPath?.at(-1);
      if (byKey.has(key)) members.get(key).push(object); else roots.push(object);
    }
    let count = 0, collapsed = 0, sharedClips = 0, hoistedLeaves = 0;
    let processed = 0;
    for (const descriptor of descriptors.slice().reverse()) {
      if (++processed % 256 === 0) await checkpoint?.("groups", processed, descriptors.length);
      let children = members.get(descriptor.key).sort((a, b) => a.figureStudioSvgSourceOrder - b.figureStudioSvgSourceOrder);
      if (!children.length) continue;
      if (children.length === 1 && descriptor.neutralScope) {
        // Producers frequently wrap each dense scatter marker in a q/Q state.
        // Keeping a one-child UI group for every marker doubles the selectable
        // tree without preserving a meaningful source grouping relationship.
        const child = children[0];
        if (descriptor.parent && members.has(descriptor.parent)) members.get(descriptor.parent).push(child); else roots.push(child);
        collapsed++;
        continue;
      }
      const runs = sharedClipRuns(children, descriptor, fabric);
      children = runs.children;
      count += runs.scopes; sharedClips += runs.scopes; hoistedLeaves += runs.leaves;
      // Geometry and clip transforms are already in page coordinates. Grouping
      // changes their coordinate frames once; copying SVG transforms here would
      // apply them a second time and displace both the artwork and its clips.
      const Group = registerGroupClass(fabric);
      const group = new Group(children, { opacity: descriptor.opacity, subTargetCheck: true, interactive: false, objectCaching: false, selectable: true, evented: true });
      group.set({ ...descriptor.meta, figureStudioSvgGroupMeta: { schema: "figureStudio.svgNamedGroup.v1", id: descriptor.id, sourceKey: descriptor.key, parentSourceKey: descriptor.parent, path: descriptor.path, sourceOrder: descriptor.order, depth: descriptor.path.length - 1, canvasRepresentation: "editable-group" } });
      const hoisted = hoistSharedClip(group, descriptor.clipRef, fabric, onDiagnostic);
      if (hoisted) { sharedClips++; hoistedLeaves += hoisted; }
      group.setCoords?.();
      count++;
      if (descriptor.parent && members.has(descriptor.parent)) members.get(descriptor.parent).push(group); else roots.push(group);
    }
    return { objects: roots.sort((a, b) => a.figureStudioSvgSourceOrder - b.figureStudioSvgSourceOrder), count, collapsed, sharedClips, hoistedLeaves };
  }

  async function nativeRectanglePath(element, root, view, fabric, PathClass, clipDefinitions, geometryCss) {
    if (element.getAttribute("data-pdf-native-rect-clip") !== "1" || element.getAttribute("data-pdf-rect-proof") !== "figureStudio.pdfRectangleScope.v1" || tag(element) !== "path") return null;
    const clipOwners = [];
    for (let current = element; current?.getAttribute; current = current.parentElement) if (ownStyle(current, "clip-path")) clipOwners.push(current);
    if (clipOwners.length !== 1 || geometryCss) return null;
    const owner = clipOwners[0], reference = ownStyle(owner, "clip-path").match(/^url\(['"]?#([^'"]+)['"]?\)$/)?.[1];
    const definition = clipDefinitions.get(reference);
    if (!definition || (definition.getAttribute("clipPathUnits") && definition.getAttribute("clipPathUnits") !== "userSpaceOnUse") || ownStyle(definition, "clip-path") || definition.children.length !== 1) return null;
    const leaf = definition.children[0];
    if (tag(leaf) !== "path" || ownStyle(leaf, "clip-path")) return null;
    const object = await PathClass.fromElement(element, {}, {});
    if (!rectangleBounds(object.path) || object.hasStroke() || typeof object.fill !== "string" || /^\s*url\s*\(/i.test(object.fill) || object.shadow) return null;
    // Path.fromElement resolves the original inherited paint/transform attributes;
    // this uses Fabric's same SVG transform normalization, then the root viewport.
    delete object.clipPath;
    fabric.util.removeTransformMatrixForSvgParsing(object);
    fabric.util.applyTransformToObject(object, multiply(view.matrix, object.calcTransformMatrix()));
    const clip = new fabric.Path(leaf.getAttribute("d"), { fill: "black", strokeWidth: 0, fillRule: style(leaf, "clip-rule", style(leaf, "fill-rule", "nonzero")) });
    if (!rectangleBounds(clip.path)) return null;
    const clipWorld = multiply(multiply(multiply(compositeMatrix(owner, root, view.matrix), transformMatrix(definition.getAttribute("transform"))), transformMatrix(leaf.getAttribute("transform"))), clip.calcTransformMatrix());
    fabric.util.applyTransformToObject(clip, multiply(fabric.util.invertTransform(object.calcTransformMatrix()), clipWorld));
    object.clipPath = clip;
    object.pdfNativeRectClip = {
      schema: "figureStudio.pdfRectangleScope.v1", path: JSON.stringify(object.path), clipGeometry: JSON.stringify(clip.path),
      paintIndex: number(element.getAttribute("data-pdf-paint-index"), -1), sourceStart: number(element.getAttribute("data-pdf-source-start"), -1), sourceEnd: number(element.getAttribute("data-pdf-source-end"), -1), sourceLeafId: element.getAttribute("data-pdf-source-leaf-id") || ""
    };
    return object._nativeRectangle() ? object : null;
  }

  function referencesIn(element, references) {
    for (const attribute of element.attributes || []) {
      for (const match of attribute.value.matchAll(/url\(['"]?#([^'")]+)['"]?\)/g)) references.add(match[1]);
      if (/^(?:xlink:)?href$/.test(attribute.name) && attribute.value.startsWith("#")) references.add(attribute.value.slice(1));
    }
  }

  function svgBatchDocument(root, leaves, definitions, styles) {
    const doc = root.ownerDocument.implementation.createDocument(null, null, null);
    const batchRoot = doc.importNode(root, false);
    doc.appendChild(batchRoot);
    const defs = doc.createElementNS(SVG_NS, "defs");
    batchRoot.appendChild(defs);
    const copies = new Map([[root, batchRoot]]), references = new Set();
    referencesIn(root, references);
    for (const sheet of styles) for (const match of String(sheet.textContent || "").matchAll(/url\(['"]?#([^'")]+)['"]?\)/g)) references.add(match[1]);
    const copyAncestor = (element) => {
      if (copies.has(element)) return copies.get(element);
      const parent = copyAncestor(element.parentElement);
      const copied = doc.importNode(element, false);
      referencesIn(element, references);
      parent.appendChild(copied); copies.set(element, copied);
      return copied;
    };
    for (const leaf of leaves) {
      const parent = copyAncestor(leaf.parentElement);
      referencesIn(leaf, references);
      parent.appendChild(doc.importNode(leaf, true));
    }
    const included = new Set();
    while (references.size) {
      const id = references.values().next().value; references.delete(id);
      if (included.has(id)) continue;
      included.add(id);
      const definition = definitions.get(id);
      if (!definition) continue;
      const copied = doc.importNode(definition, true); defs.appendChild(copied);
      referencesIn(definition, references);
      for (const descendant of definition.querySelectorAll("*")) referencesIn(descendant, references);
    }
    for (const sheet of styles) defs.appendChild(doc.importNode(sheet, true));
    return doc;
  }

  async function loadGeometryBatches(root, fabric, Serializer, reviver, options, checkpoint, report) {
    const major = Number(String(fabric.version || "7").split(".")[0]);
    const leaves = Array.from(root.querySelectorAll(`[${KEY}]`)).filter((element) => !inDefinition(element));
    const batchSize = Math.max(16, Math.min(256, Math.floor(number(options.svgBatchSize, 128))));
    report.svgParserBatchCount = 0;
    const load = async (document) => {
      report.svgParserBatchCount++;
      if (major >= 6 && fabric.parseSVGDocument) return fabric.parseSVGDocument(document, reviver);
      const text = new Serializer().serializeToString(document.documentElement);
      if (major >= 6) return fabric.loadSVGFromString(text, reviver);
      return new Promise((resolve, reject) => {
        try { fabric.loadSVGFromString(text, (objects, parserOptions) => resolve({ objects, options: parserOptions }), reviver); } catch (error) { reject(error); }
      });
    };
    if (leaves.length <= batchSize || options.svgBatchSize === 0) return load(root.ownerDocument);
    const definitions = new Map(Array.from(root.querySelectorAll("[id]")).map((element) => [element.id, element]));
    const styles = Array.from(root.querySelectorAll("style"));
    const objects = [];
    let parserOptions = {};
    for (let start = 0; start < leaves.length; start += batchSize) {
      const document = svgBatchDocument(root, leaves.slice(start, start + batchSize), definitions, styles);
      const loaded = await load(document);
      objects.push(...(loaded.objects || [])); parserOptions = loaded.options || parserOptions;
      await checkpoint("svg-parser", Math.min(start + batchSize, leaves.length), leaves.length, true);
    }
    return { objects, options: parserOptions };
  }

  function prepareSvgOpenDocument(svgText, options = {}) {
    const Parser = options.DOMParser || globalThis.DOMParser;
    const Serializer = options.XMLSerializer || globalThis.XMLSerializer;
    if (!Parser || !Serializer) throw new Error("SVG Open requires the current XML parser.");
    const doc = new Parser().parseFromString(String(svgText || ""), "image/svg+xml");
    const root = doc.documentElement;
    if (tag(root) !== "svg" || doc.querySelector("parsererror")) throw new Error("Invalid SVG document.");
    const policy = root.getAttribute("data-figure-studio-svg-source-numeric-policy");
    if (policy !== null && policy !== "figureStudio.svgSourcePageNumbers.v1") throw new Error("SVG Open has an unsupported source-page numerical policy.");
    const ownPositionedPage = Boolean(root.getAttribute("data-figure-studio-version"))
      && (Number(root.getAttribute("data-pdf-source-count")) > 0 || policy === "figureStudio.svgSourcePageNumbers.v1");
    if (!ownPositionedPage) return null;
    if (Array.from(root.querySelectorAll("style")).some(sheet => String(sheet.textContent || "").replace(/@font-face\s*\{[^}]+\}/gi, "").trim())) throw new Error("SVG Open cannot resolve stylesheet text geometry safely.");
    const absoluteLength = /^[+-]?(?:\d*\.\d+|\d+\.?\d*)(?:e[+-]?\d+)?(?:px|pt|pc|in|cm|mm)?$/i;
    for (const key of ["width", "height"]) if (root.hasAttribute(key) && !absoluteLength.test(root.getAttribute(key).trim())) throw new Error("SVG Open requires absolute page dimensions.");
    const view = viewport(root);
    if (![view.width, view.height, ...view.matrix].every(Number.isFinite) || view.width <= 0 || view.height <= 0) throw new Error("The SVG page has invalid dimensions.");
    const signatureKeys = ["font-family", "font-size", "font-weight", "font-style", "fill", "fill-opacity", "stroke", "stroke-width", "stroke-opacity", "stroke-dasharray", "stroke-dashoffset", "stroke-linecap", "stroke-linejoin", "stroke-miterlimit", "fill-rule", "opacity", "text-anchor"];
    const defaults = { "font-family": "Arial", "font-size": "10", "font-weight": "normal", "font-style": "normal", fill: "#000000", "fill-opacity": "1", stroke: "none", "stroke-width": "0", "stroke-opacity": "1", "stroke-dasharray": "none", "stroke-dashoffset": "0", "stroke-linecap": "butt", "stroke-linejoin": "miter", "stroke-miterlimit": "4", "fill-rule": "nonzero", opacity: "1", "text-anchor": "start" };
    const list = value => {
      if (!/^[\s,+\-.\deE]+$/.test(String(value || ""))) throw new Error("A positioned SVG run uses nonnumeric coordinates.");
      const result = numbers(value);
      if (!result.length || !result.every(Number.isFinite)) throw new Error("A positioned SVG run uses invalid coordinates.");
      return result;
    };
    const plans = [];
    const spanAttributes = new Set([...signatureKeys, "style", "x", "y", "dx", "dy", "xml:space", "data-pdf-unicode", "data-pdf-glyph-map", "data-pdf-original-font", "data-pdf-font-substitution"]);
    const defaultTypography = { "letter-spacing": ["", "0", "0px", "normal"], "word-spacing": ["", "0", "0px", "normal"], direction: ["", "ltr"], "writing-mode": ["", "horizontal-tb"], "text-decoration": ["", "none"], "dominant-baseline": ["", "auto"], "alignment-baseline": ["", "auto", "baseline"], "baseline-shift": ["", "0", "0px", "baseline"], "font-stretch": ["", "normal"], "font-variant": ["", "normal"], "unicode-bidi": ["", "normal"], "white-space": ["", "pre", "normal"] };
    for (const element of root.querySelectorAll("text")) {
      if (inDefinition(element)) continue;
      for (let ancestor = element; ancestor?.getAttribute; ancestor = ancestor.parentElement) {
        const keys = String(ancestor.getAttribute("style") || "").split(";").filter(part => part.trim()).map(part => part.split(":", 1)[0].trim().toLowerCase());
        if (keys.some(key => !signatureKeys.includes(key) && !Object.hasOwn(defaultTypography, key) && !["text-decoration-thickness", "clip-path"].includes(key))) throw new Error("SVG Open cannot flatten unsupported inherited text styles.");
      }
      if (["rotate", "textLength", "lengthAdjust"].some(key => element.hasAttribute(key))) throw new Error("SVG Open cannot flatten adjusted text geometry.");
      const elementStyles = String(element.getAttribute("style") || "").split(";").filter(part => part.trim()).map(part => part.split(":", 1)[0].trim().toLowerCase());
      if (elementStyles.some(key => !signatureKeys.includes(key) && !Object.hasOwn(defaultTypography, key) && key !== "text-decoration-thickness")) throw new Error("SVG Open cannot flatten unsupported text styles.");
      const descendants = Array.from(element.querySelectorAll("tspan"));
      const spans = descendants.filter(span => !span.querySelector("tspan"));
      if (!spans.length || spans.length !== descendants.length || Array.from(element.children).some(child => tag(child) !== "tspan")) throw new Error("SVG Open cannot coalesce this rich text hierarchy.");
      if (Array.from(element.childNodes || []).some(node => node.nodeType === 3 && String(node.nodeValue || "").trim())) throw new Error("SVG Open cannot mix positioned spans and unpositioned text.");
      const signature = JSON.stringify(signatureKeys.map(key => style(spans[0], key, defaults[key])));
      const fontIdentity = JSON.stringify(["data-pdf-original-font", "data-pdf-font-substitution"].map(key => spans[0].getAttribute(key) ?? element.getAttribute(key)));
      const x = [], y = [], mapping = [], raw = [], unicode = [];
      let baseline;
      for (const span of spans) {
        if (JSON.stringify(signatureKeys.map(key => style(span, key, defaults[key]))) !== signature) throw new Error("SVG Open cannot coalesce differently painted or styled spans.");
        if (["fill", "stroke"].some(key => /^\s*url\s*\(/i.test(style(span, key)))) throw new Error("SVG Open cannot qualify text with a bounding-box paint server.");
        if (Number(style(span, "opacity", "1")) !== 1) throw new Error("SVG Open cannot flatten independently composited text opacity.");
        if (Array.from(span.attributes).some(attribute => !spanAttributes.has(attribute.name))) throw new Error("SVG Open cannot discard unsupported positioned-span attributes.");
        if (JSON.stringify(["data-pdf-original-font", "data-pdf-font-substitution"].map(key => span.getAttribute(key) ?? element.getAttribute(key))) !== fontIdentity) throw new Error("SVG Open cannot combine distinct source-font identities.");
        if (span.hasAttribute("transform") || span.hasAttribute("rotate") || span.hasAttribute("clip-path") || span.hasAttribute("mask") || span.hasAttribute("filter")) throw new Error("SVG Open cannot coalesce independently transformed or clipped spans.");
        for (const key of ["dx", "dy"]) if (span.hasAttribute(key) && list(span.getAttribute(key)).some(value => value !== 0)) throw new Error("SVG Open cannot coalesce relative span positioning.");
        if (Object.entries(defaultTypography).some(([key, allowed]) => !allowed.includes(style(span, key)))
          || style(span, "textLength") || style(span, "lengthAdjust")) throw new Error("SVG Open cannot coalesce this typography.");
        const declaredKeys = String(span.getAttribute("style") || "").split(";").filter(part => part.trim()).map(part => part.split(":", 1)[0].trim().toLowerCase());
        if (declaredKeys.some(key => !signatureKeys.includes(key) && !Object.hasOwn(defaultTypography, key))) throw new Error("SVG Open cannot discard unsupported span styles.");
        const text = span.getAttribute("data-pdf-unicode");
        if (text === null) throw new Error("SVG Open requires explicit Unicode for every positioned span.");
        let entries;
        try { entries = JSON.parse(span.getAttribute("data-pdf-glyph-map") || "null"); } catch (_) { throw new Error("SVG Open has an invalid glyph map."); }
        if (!Array.isArray(entries) || !entries.length || entries.some(entry => !entry || typeof entry !== "object" || Array.isArray(entry)
            || typeof entry.unicode !== "string" || !entry.unicode || typeof entry.fontChar !== "string" || !entry.fontChar
            || Object.keys(entry).some(key => !["unicode", "fontChar"].includes(key)))) throw new Error("SVG Open has an unsupported glyph map.");
        const glyphText = String(span.textContent || "");
        if (/[\r\n\t\f\v]/.test(text) || /[\r\n\t\f\v]/.test(glyphText)) throw new Error("SVG Open requires a single horizontal text baseline.");
        if (entries.map(entry => entry.unicode).join("") !== text || entries.map(entry => xmlGlyph(entry.fontChar, entry.unicode)).join("") !== glyphText) throw new Error("SVG Open Unicode does not match its displayed glyph stream.");
        const xs = list(span.getAttribute("x")), ys = list(span.getAttribute("y"));
        if (xs.length !== entries.length || ![1, entries.length].includes(ys.length)) throw new Error("SVG Open requires a complete explicit glyph-position array.");
        if (baseline === undefined) baseline = ys[0];
        if (ys.some(value => value !== baseline)) throw new Error("SVG Open cannot coalesce distinct baselines.");
        const fontSizeSource = style(span, "font-size", "10");
        if (!absoluteLength.test(fontSizeSource.trim())) throw new Error("SVG Open requires an absolute text size.");
        const fontSize = length(fontSizeSource, NaN);
        if (!Number.isFinite(fontSize) || fontSize <= 0) throw new Error("SVG Open has an invalid font size.");
        x.push(...xs); y.push(...entries.map(() => baseline)); mapping.push(...entries); raw.push(glyphText); unicode.push(text);
      }
      const merged = spans[0].cloneNode(false);
      merged.removeAttribute("id"); merged.removeAttribute("dx"); merged.removeAttribute("dy");
      merged.setAttribute("x", x.join(" ")); merged.setAttribute("y", y.join(" "));
      merged.setAttribute("data-pdf-unicode", unicode.join("")); merged.setAttribute("data-pdf-glyph-map", JSON.stringify(mapping));
      merged.setAttributeNS("http://www.w3.org/XML/1998/namespace", "xml:space", "preserve");
      merged.textContent = raw.join("");
      plans.push({ element, merged, unicode: unicode.join(""), x, y, mapping });
    }
    // Validate every run before changing the detached source document.
    for (const plan of plans) elementReplace(plan.element, plan.merged);
    function elementReplace(element, merged) { while (element.firstChild) element.removeChild(element.firstChild); element.appendChild(merged); }
    return { schema: "figureStudio.svgSourceOpen.v1", svgText: new Serializer().serializeToString(doc), width: view.width, height: view.height, matrix: view.matrix,
      textRunCount: plans.length, glyphCount: plans.reduce((count, plan) => count + plan.mapping.length, 0), numericPolicy: "figureStudio.svgSourcePageNumbers.v1" };
  }

  const ownSvgDeclaringPlaneCandidate = (function () {
function parseTransform(text=''){
 const tokens=[...text.matchAll(/(matrix|translate|scale)\(([^)]*)\)/g)];
 if(tokens.map(t=>t[0]).join('').replace(/\s/g,'')!==text.replace(/\s/g,''))refuse('Unsupported literal transform.');
 return tokens.reduce((value,t)=>{const n=t[2].trim().split(/[ ,]+/).map(Number);if(!n.every(Number.isFinite))refuse('Nonfinite current matrix.');let m;
  if(t[1]==='matrix'){if(n.length!==6)refuse('Invalid current matrix.');m=n;}
  else if(t[1]==='translate'){if(![1,2].includes(n.length))refuse('Invalid translate.');m=[1,0,0,1,n[0],n[1]??0];}
  else {if(![1,2].includes(n.length))refuse('Invalid scale.');m=[n[0],0,0,n[1]??n[0],0,0];}
  return multiply(value,m);},identity);
}
const identity=[1,0,0,1,0,0],META=['figureType','name','figureStudioSvgElementId','figureStudioSvgElementTag','figureStudioSvgGroupPath','figureStudioSvgSourceOrder','figureStudioSvgTextMeta','figureStudioSvgGroupMeta'];
const same=(a,b)=>Object.is(a,b)||Boolean(a&&b&&typeof a==='object'&&typeof b==='object'&&Object.keys(a).length===Object.keys(b).length&&Object.keys(a).every((k,i)=>k===Object.keys(b)[i]&&same(a[k],b[k])));
function refuse(reason){const e=new Error(reason);e.code='SVG_LOCAL_FULL_UNSUPPORTED';throw e;}
function pose(m){
 if(m.length!==6||!m.every(Number.isFinite))refuse('Invalid current literal affine plane.');
 const base={originX:'center',originY:'center',left:m[4],top:m[5],skewX:0,skewY:0};
 if(m[1]===0&&m[2]===0&&m[0]!==0&&m[3]!==0)return {...base,scaleX:Math.abs(m[0]),scaleY:Math.abs(m[3]),flipX:m[0]<0,flipY:m[3]<0,angle:0};
 if(m[0]===0&&m[3]===0&&m[1]!==0&&m[2]!==0)return {...base,scaleX:Math.abs(m[1]),scaleY:Math.abs(m[2]),flipX:false,flipY:m[1]>0?m[2]>0:m[2]<0,angle:m[1]>0?90:270};
 refuse('Only exact diagonal/reflected and quarter-axis current planes are admitted.');
}
const PAINT=['fill','stroke','stroke-width','stroke-linecap','stroke-linejoin','stroke-miterlimit','stroke-dasharray','stroke-dashoffset','fill-rule','opacity'];
const TEXT=['font-family','font-size','font-weight','font-style','text-anchor','text-decoration-thickness','white-space'];
function styles(attrs,inherited={}){
 const values={...inherited};for(const [k,v]of Object.entries(attrs))if([...PAINT,...TEXT].includes(k))values[k]=v;
 for(const d of (attrs.style||'').split(';')){if(!d.trim())continue;const p=d.indexOf(':');if(p<0)refuse('Invalid inline style.');const k=d.slice(0,p).trim(),v=d.slice(p+1).trim();if(![...PAINT,...TEXT].includes(k))refuse('Unsupported current style '+k);values[k]=v;}
 const numeric=(k,f)=>{if(values[k]===undefined)return f;if(!/^[-+]?\d*\.?\d+(?:e[-+]?\d+)?(?:px)?$/i.test(values[k]))refuse('Unsupported numeric style '+k);const n=Number(values[k].replace(/px$/i,''));if(!Number.isFinite(n))refuse('Nonfinite style '+k);return n;};
 for(const k of ['fill','stroke'])if(values[k]?.includes('url(')||values[k]!==undefined&&!/^(?:none|#[0-9a-f]{3}(?:[0-9a-f]{3})?|rgb\(\s*\d+(?:\.\d+)?\s*,\s*\d+(?:\.\d+)?\s*,\s*\d+(?:\.\d+)?\s*\)|black|white)$/i.test(values[k]))refuse('Unsupported current solid paint.');if(numeric('opacity',1)!==1)refuse('Independent opacity is unsupported.');
 if(values['stroke-linecap']&&!['butt','round','square'].includes(values['stroke-linecap'])||values['stroke-linejoin']&&!['miter','round','bevel'].includes(values['stroke-linejoin'])||values['fill-rule']&&!['nonzero','evenodd'].includes(values['fill-rule'])||values['text-anchor']&&!['start','middle','end'].includes(values['text-anchor']))refuse('Unknown current cap, join, fill rule or text anchor.');
 if(numeric('stroke-width',1)<0||numeric('stroke-miterlimit',4)<1||numeric('font-size',10)<=0)refuse('Invalid current width, miter limit or text size.');
 if(values['stroke-dasharray']&&values['stroke-dasharray']!=='none'){if(!/^\s*[-+]?\d*\.?\d+(?:e[-+]?\d+)?(?:[ ,]+[-+]?\d*\.?\d+(?:e[-+]?\d+)?)*\s*$/i.test(values['stroke-dasharray']))refuse('Malformed current dash array.');const dash=values['stroke-dasharray'].trim().split(/[ ,]+/).map(Number);if(dash.some(x=>!Number.isFinite(x)||x<0)||!dash.some(x=>x>0))refuse('Invalid current dash array.');}
 if(values['text-decoration-thickness']&&!/^(?:0|\d+(?:\.\d+)?%)$/.test(values['text-decoration-thickness'])||values['white-space']&&!['pre','normal'].includes(values['white-space']))refuse('Unsupported current decoration or whitespace.');
 return {values,options:{fill:values.fill==='none'?null:values.fill||'black',stroke:!values.stroke||values.stroke==='none'?null:values.stroke,strokeWidth:numeric('stroke-width',1),strokeLineCap:values['stroke-linecap']||'butt',strokeLineJoin:values['stroke-linejoin']||'miter',strokeMiterLimit:numeric('stroke-miterlimit',4),strokeDashArray:values['stroke-dasharray']&&values['stroke-dasharray']!=='none'?values['stroke-dasharray'].split(/[ ,]+/).map(Number):null,strokeDashOffset:numeric('stroke-dashoffset',0),fillRule:values['fill-rule']||'nonzero',opacity:1,objectCaching:false},numeric};
}
function guard(n){for(const [k,v]of Object.entries(n.attrs||{})){if(['mask','filter','vector-effect','display','visibility','mix-blend-mode','fill-opacity','stroke-opacity','transform-origin','clip-rule'].includes(k)||/^on/i.test(k)||/^\s*javascript:/i.test(v)||k==='style'&&/filter|mask|display|visibility|mix-blend-mode|vector-effect/.test(v))refuse('Unsupported authored effect '+k);if(['transform','d','x','y','width','height'].includes(k)&&(String(v).match(/[+-]?(?:\d*\.\d+|\d+\.?\d*)(?:e[+-]?\d+)?/gi)||[]).some(x=>Object.is(Number(x),-0)))refuse('Signed-zero literal geometry is outside this bounded plane profile.');}if(['path','rect','text'].includes(n.tag)&&n.attrs['clip-path'])refuse('Independent leaf clip requires the existing parser.');}
function meta(n,order,groupPath){const type=n.tag==='text'?'text':n.tag==='g'||n.tag==='svg'?'group':'path';return {figureType:type,name:n.attrs['aria-label']||n.attrs['data-name']||n.attrs.id||`PDF ${type}`,figureStudioSvgElementId:n.attrs.id||'',figureStudioSvgElementTag:n.tag,figureStudioSvgGroupPath:groupPath.slice(),figureStudioSvgSourceOrder:order,selectable:true,evented:true};}
function exactRaw(object,properties=META){const raw=object.toObject(properties);for(const k of ['left','top','width','height','scaleX','scaleY','angle','skewX','skewY','strokeWidth','strokeMiterLimit','strokeDashOffset','opacity','fontSize','charSpacing','lineHeight'])if(Number.isFinite(object[k]))raw[k]=object[k];if(object.path)raw.path=object.path.map(c=>c.slice());return raw;}
function collectClips(root){const defs=new Map(),ids=new Set();function visit(n){const id=n.attrs.id;if(typeof id==='string'&&id){if(ids.has(id))refuse('Current SVG global element ID is duplicated.');ids.add(id);}if(n.tag==='svg'&&String(n.attrs.transform||'').trim())refuse('Root SVG transform requires the existing parser.');if(n.tag==='defs'&&Object.entries(n.attrs).some(([k,v])=>k!=='id'&&String(v).trim()))refuse('Inherited definition presentation requires the existing parser.');if(n.tag==='style'&&String(n.text||'').replace(/@font-face\s*\{[^}]+\}/gi,'').trim())refuse('Geometry CSS is outside current literal planes.');if(n.tag==='clipPath'){if(typeof id!=='string'||!id.trim()||/\s/.test(id)||defs.has(id))refuse('Current clip definition ID is missing, empty or duplicated.');defs.set(id,n);}for(const c of n.children||[])visit(c);}visit(root);return defs;}
function currentClipDefinition(defs,reference){const match=/^url\(#([^\s)]*)\)$/.exec(reference||''),d=match&&defs.get(match[1]);if(!d||Object.keys(d.attrs).some(k=>!['id','clipPathUnits'].includes(k))||d.attrs.clipPathUnits&&d.attrs.clipPathUnits!=='userSpaceOnUse'||d.children.length!==1||!['rect','path'].includes(d.children[0].tag))refuse('Unsupported current clip declaration or ownership plane.');if(styles(d.children[0].attrs).values['fill-rule']&&styles(d.children[0].attrs).values['fill-rule']!=='nonzero')refuse('Clip paint fill-rule cannot substitute for SVG clip-rule.');return {definition:d,id:match[1]};}
function admitted(fixture,prepared){
 try{
  if(fixture.schema!=='figureStudio.ownSvgDeclaringPlaneFullFixture.v2'||!fixture.dom.attrs['data-figure-studio-version']||prepared.schema!=='figureStudio.svgSourceOpen.v1'||!same(prepared.matrix,identity))return false;
  const root=JSON.parse(prepared.svgText),defs=collectClips(root);let count=0;
  function visit(n,inherited={}){
   if(++count>10000)refuse('This local source-plane slice is bounded to10000 nodes.');guard(n);if(!['svg','g','path','rect','text'].includes(n.tag))refuse('Unsupported source-plane node.');pose(n.tag==='svg'?identity:parseTransform(n.attrs.transform));const s=styles(n.attrs,inherited);
   if(n.tag==='path'&&(!n.attrs.d||!/^[MLCZmlcz\s\d.,+\-eE]+$/.test(n.attrs.d)))refuse('Unsupported current path.');
   if(n.tag==='rect'){const a=['x','y','width','height'].map(k=>Number(n.attrs[k]??0));if(!a.every(Number.isFinite)||a[2]<=0||a[3]<=0||n.attrs.rx||n.attrs.ry)refuse('Unsupported current rect.');}
   if(n.tag==='text'){if(n.children.length!==1||n.children[0].tag!=='tspan')refuse('Unqualified current run.');styles(n.children[0].attrs,s.values);return;}
   if(n.attrs['clip-path']){const {definition}=currentClipDefinition(defs,n.attrs['clip-path']);visit(definition.children[0],{});}
   const children=(n.children||[]).filter(c=>!['defs','clipPath','metadata','desc'].includes(c.tag));if(['svg','g'].includes(n.tag)&&!children.length)refuse('Empty current source group.');for(const c of children)visit(c,s.values);
  }
  visit(root);return true;
 }catch(error){if(['SVG_LOCAL_FULL_UNSUPPORTED','SVG_LOCAL_PLANE_UNSUPPORTED'].includes(error.code))return false;throw error;}
}
async function construct(fabric,materializer,fixture,prepared,options={}){
 if(fixture.schema!=='figureStudio.ownSvgDeclaringPlaneFullFixture.v2'||!fixture.dom.attrs['data-figure-studio-version']||prepared.schema!=='figureStudio.svgSourceOpen.v1'||!same(prepared.matrix,identity))refuse('Explicit own SVG current page qualification is required.');
 const root=JSON.parse(prepared.svgText),defs=collectClips(root);let order=0,index=0;const groups=[],leaves=[],clips=[];
 const TextClass=materializer.registerTextClass(fabric),Manager=materializer.registerAuthoringLayoutManager(fabric),CurrentGroup=materializer.registerCurrentPlaneGroupClass(fabric),Linear=fabric.classRegistry.getClass("PdfLinearFitContentLayout");
 function leaf(n,inherited={},groupPath=[],clip=false){
  guard(n);const attrs=n.attrs,paint=styles(attrs,inherited),literal=parseTransform(attrs.transform),metadata=meta(n,order++,groupPath);let object,own,source;
  if(n.tag==='path'){
   if(!attrs.d||!/^[MLCZmlcz\s\d.,+\-eE]+$/.test(attrs.d))refuse('Unsupported current path command stream.');object=new fabric.Path(attrs.d,{...paint.options,originX:'center',originY:'center'});if(!object.path.length||object.path.some(c=>c.slice(1).some(v=>!Number.isFinite(v))))refuse('Invalid current native path.');own=multiply(literal,[1,0,0,1,object.pathOffset.x,object.pathOffset.y]);object.set(pose(own));
   source={kind:'path',literalMatrix:literal,ownMatrix:own,pathOffset:[object.pathOffset.x,object.pathOffset.y],path:object.path.map(c=>c.slice())};
  }else if(n.tag==='rect'){
   const [x,y,w,h]=['x','y','width','height'].map(k=>Number(attrs[k]??0));if(![x,y,w,h].every(Number.isFinite)||w<=0||h<=0||attrs.rx||attrs.ry)refuse('Unsupported current rectangle.');own=multiply(literal,[1,0,0,1,x+w/2,y+h/2]);object=new fabric.Rect({...paint.options,...pose(own),width:w,height:h});
   source={kind:'rect',literalMatrix:literal,ownMatrix:own,points:[[x,y],[x+w,y],[x+w,y+h],[x,y+h]]};
  }else if(n.tag==='text'){
   if(n.children.length!==1||n.children[0].tag!=='tspan')refuse('Text requires one qualified current run.');const span=n.children[0],values=styles(span.attrs,paint.values);if(span.attrs.transform||span.attrs['clip-path'])refuse('Independent span pose/clip unsupported.');
   const nums=s=>(s||'').trim().split(/[ ,]+/).map(Number),x=nums(span.attrs.x),y=nums(span.attrs.y),unicode=span.attrs['data-pdf-unicode'],mapping=JSON.parse(span.attrs['data-pdf-glyph-map']);
   const plan=materializer.glyphPlan(unicode,span.text,{x,y},mapping,fabric),family=(values.values['font-family']||'Arial').replace(/^['"]|['"]$/g,''),fontSize=values.numeric('font-size',10),fontWeight=values.values['font-weight']||'normal',fontStyle=values.values['font-style']||'normal',anchor=values.values['text-anchor']||'start';
   const font=(options.sourceFontPrograms||[]).find(f=>f.family===family);
   const textSource={schema:'figureStudio.pdfPositionedText.v1',text:unicode,anchor,fontFamily:family,originalFontName:span.attrs['data-pdf-original-font']||attrs['data-pdf-original-font']||family,displayFontFamily:family,sourceEmbeddedProgram:Boolean(font?.dataUrl&&(options.loadedFonts||[]).includes(family)),fontSubstitutionFamily:span.attrs['data-pdf-font-substitution']||attrs['data-pdf-font-substitution']||'',fontSize,fontWeight,fontStyle,map:{...(font?.unicodeToFontChar||{}),...plan.map},unicodeAdvances:{...(font?.unicodeAdvances||{}),...plan.unicodeAdvances},glyphs:plan.glyphs,fallbackFont:options.fallbackFont||'Arial'};
   object=new TextClass(unicode,{...values.options,fontFamily:family,fontSize,fontWeight,fontStyle,textAlign:'left',originX:'center',originY:'center',editable:true,pdfTextSource:textSource});
   const baseline=-object.height/2+object.getHeightOfLineImpl(0)*(1-object._fontSizeFraction),shift=anchor==='middle'?-object.width/2:anchor==='end'?-object.width:0;
   own=multiply(literal,[1,0,0,1,plan.firstX+object.width/2+shift,plan.firstY-baseline]);object.set(pose(own));
   metadata.figureStudioSvgTextMeta={schema:'figureStudio.svgPositionedText.v1',sourceText:unicode,sourceGlyphText:span.text,x:plan.firstX,y:plan.firstY,xPositions:x,yPositions:y,fontFamily:family,fontSize};
   source={kind:'text',literalMatrix:literal,ownMatrix:own,text:unicode,x,y,glyphPlan:plan,textSource,baseline,anchor};
  }else refuse('Unsupported current leaf '+n.tag);
  object.set(metadata);object.setCoords();if(!same(object.calcOwnMatrix(),own))refuse('Native leaf pose did not roundtrip current literal plane exactly.');
  source.index=index++;source.metadata=metadata;source.paintOptions=paint.options;if(!clip)leaves.push(source);return {object,raw:exactRaw(object),source};
 }
 async function build(n,inherited={},groupPath=[]){
  guard(n);if(['path','rect','text'].includes(n.tag))return leaf(n,inherited,groupPath);
  if(!['svg','g'].includes(n.tag))refuse('Unsupported current group '+n.tag);const attrs=n.attrs,own=n.tag==='svg'?identity:parseTransform(attrs.transform),paint=styles(attrs,inherited),metadata=meta(n,order++,groupPath),path=[...groupPath,attrs.id||`source-group-${metadata.figureStudioSvgSourceOrder}`],children=[];
  for(const c of n.children||[]){if(['defs','clipPath','metadata','desc'].includes(c.tag))continue;children.push(await build(c,paint.values,path));}
  if(!children.length)refuse('Empty authored group unsupported.');let bx=0,by=0;for(const c of children)for(const p of c.object.getCoords()){bx=Math.max(bx,Math.abs(p.x));by=Math.max(by,Math.abs(p.y));}
  const width=Math.max(1,2*bx+2),height=Math.max(1,2*by+2),raw={type:CurrentGroup.type,...pose(own),width,height,strokeWidth:0,opacity:1,objectCaching:false,subTargetCheck:true,interactive:true,...metadata,objects:children.map(c=>c.raw),layoutManager:{type:Manager.type,strategy:Linear.type}};let clipPlan=null;
  if(attrs['clip-path']){const {definition,id}=currentClipDefinition(defs,attrs['clip-path']);const c=leaf(definition.children[0],{},path,true);c.raw.fill='black';c.raw.stroke=null;c.raw.strokeWidth=0;raw.clipPath=c.raw;clipPlan={...c.source,definitionId:id};clips.push(clipPlan);}
  const object=await CurrentGroup.fromObject(raw);object.setCoords();if(!same(object.calcOwnMatrix(),own))refuse('Native Noop group matrix changed.');for(let i=0;i<children.length;i++)if(!same(object.getObjects()[i].calcOwnMatrix(),children[i].object.calcOwnMatrix()))refuse('Native Noop child matrix changed.');groups.push({ownMatrix:own,width,height,metadata});
  return {object,raw,source:{kind:'group',literalMatrix:own,ownMatrix:own,width,height,metadata,children:children.map(c=>c.source),clip:clipPlan}};
 }
 const value=await build(root);const seeded=await materializer.finalizeImportedAuthoringLayoutAsync([value.object],{fabric,signal:options.signal,yieldToUi:options.yieldToUi});return {root:value.object,sourceTree:value.source,leaves,clips,groups,seeded};
}
return Object.freeze({ construct, admitted });
  })();

  async function materialize(svgText, options = {}) {
    const fabric = options.fabric;
    if (!fabric?.loadSVGFromString || !fabric.Group) throw new Error("Fabric SVG loading is unavailable.");
    const Parser = options.DOMParser || globalThis.DOMParser;
    const Serializer = options.XMLSerializer || globalThis.XMLSerializer;
    if ((!Parser && !options.svgElement) || !Serializer) throw new Error("SVG DOM parsing is unavailable.");
    const started = globalThis.performance?.now?.() || Date.now();
    let doc;
    if (options.svgElement) {
      const element = options.svgElement;
      if (tag(element) !== "svg" || element.namespaceURI !== SVG_NS || !element.ownerDocument?.implementation?.createDocument) throw new Error("The PDF renderer returned an invalid SVG element.");
      // SVGGraphics creates namespaced elements in the HTML window document.
      // Fabric must receive an isolated SVG document, never window.document.
      // Ownership is handed over here; cloning the full dense tree would retain
      // another large allocation and repeat work already done by the renderer.
      doc = element.ownerDocument.implementation.createDocument(SVG_NS, "", null);
      doc.appendChild(doc.adoptNode(element));
    } else doc = new Parser().parseFromString(String(svgText || ""), "image/svg+xml");
    let root = doc.documentElement;
    if (tag(root) !== "svg" || doc.querySelector("parsererror")) throw new Error("The PDF renderer returned invalid SVG.");
    // Fabric supports SVGGraphics' prefixed paths/groups, but several resource
    // readers compare literal nodeName/getElementsByTagName. Normalize only
    // those resource names; preserve attributes, children and all paint nodes.
    for (const element of root.querySelectorAll("style,linearGradient,radialGradient,stop,use")) {
      if (!element.prefix || element.namespaceURI !== SVG_NS) continue;
      const replacement = doc.createElementNS(SVG_NS, element.localName);
      for (const attribute of element.attributes) replacement.setAttributeNS(attribute.namespaceURI, attribute.name, attribute.value);
      while (element.firstChild) replacement.appendChild(element.firstChild);
      element.replaceWith(replacement);
    }
    const knockoutEntries = extractKnockoutRoots(root, options);
    const report = { schema: SCHEMA, status: "complete", sourceDrawableCount: 0, vectorCount: 0, textRunCount: 0, imageCount: 0, groupCount: 0, clippedObjectCount: 0, nativeRectClipCount: 0, rejectedNativeRectClipCount: 0, uiYieldCount: 0, maxCooperativeBatchMs: 0, unsupported: [], fontFailures: [], warnings: [] };
    const batchSize = Math.max(32, Math.min(1024, Math.floor(number(options.batchSize, 512))));
    const now = () => globalThis.performance?.now?.() || Date.now();
    let batchStarted = now();
    const checkpoint = async (stage, completed, total, force = false) => {
      if (options.signal?.aborted) throw new Error("PDF object materialization was cancelled.");
      const elapsed = now() - batchStarted;
      if (!force && elapsed < 16) return;
      report.maxCooperativeBatchMs = Math.max(report.maxCooperativeBatchMs, elapsed);
      report.uiYieldCount++;
      options.onProgress?.({ stage, completed, total, uiYieldCount: report.uiYieldCount });
      await (options.yieldToUi ? options.yieldToUi() : new Promise((resolve) => setTimeout(resolve, 0)));
      batchStarted = now();
    };
    const unsupported = (element, code, message) => { report.unsupported.push({ code, message, sourceId: element.id || "" }); };
    let visited = 0;
    for (const element of root.querySelectorAll("*")) {
      if (++visited % batchSize === 0) await checkpoint("inspect", visited);
      if (["script", "foreignobject", "iframe", "object", "embed"].includes(tag(element))) throw new Error("Unsafe content in PDF SVG.");
      for (const attribute of element.attributes) if (/^on/i.test(attribute.name) || /^\s*javascript:/i.test(attribute.value)) throw new Error("Unsafe attribute in PDF SVG.");
      if (!inDefinition(element)) {
        if (element.hasAttribute("mask")) unsupported(element, "svg-mask", "SVG masks require a fidelity-preserving renderer.");
        if (element.hasAttribute("filter")) unsupported(element, "svg-filter", "SVG filters cannot be represented as editable PDF objects.");
        if (/mix-blend-mode/.test(element.getAttribute("style") || "")) unsupported(element, "blend-mode", "Blend-mode compositing is not qualified.");
      }
    }
    const sourceFontPrograms = options.fonts || embeddedFonts(root);
    const fontResult = await registerFonts(sourceFontPrograms, options);
    report.fontFailures = fontResult.failures;
    // Fabric's geometry CSS parser splits at semicolons inside data-font URLs.
    // FontFace has already loaded these programs; retain all geometry rules.
    for (const sheet of root.querySelectorAll("style")) sheet.textContent = String(sheet.textContent || "").replace(/@font-face\s*\{[^}]+\}/gi, "");
    if (Array.from(root.querySelectorAll("style")).some((sheet) => String(sheet.textContent || "").trim())) {
      // Fabric's CSS selector matcher compares literal nodeName as well. Only
      // trees with geometry CSS need prefixed paint/ancestor names normalized;
      // ordinary PDF paint trees retain their adopted nodes without copying.
      const elements = [root, ...root.querySelectorAll("*")];
      for (let index = 0; index < elements.length; index++) {
        const element = elements[index];
        if (element.prefix && element.namespaceURI === SVG_NS) {
          const replacement = doc.createElementNS(SVG_NS, element.localName);
          for (const attribute of element.attributes) replacement.setAttributeNS(attribute.namespaceURI, attribute.name, attribute.value);
          while (element.firstChild) replacement.appendChild(element.firstChild);
          element.replaceWith(replacement);
        }
        if (index % batchSize === 0) await checkpoint("normalize-css-names", index, elements.length);
      }
      root = doc.documentElement;
    }
    // Own SVG Open may retain current declaring planes instead of flattening
    // and refitting them. PDF and Place use their existing routes. Unsupported
    // own forms remain on the existing conservative parser; a failure after
    // local admission is a fidelity error, never an unreported fallback.
    if (options.ownSvgDeclaringPlanes === true) {
      const qualified = prepareSvgOpenDocument(new Serializer().serializeToString(doc), { DOMParser: Parser, XMLSerializer: Serializer });
      if (!qualified) throw new Error("Current source-plane import requires a qualified own SVG page.");
      const qualifiedDoc = new Parser().parseFromString(qualified.svgText, "image/svg+xml");
      const row = element => ({ tag: String(element.localName || element.nodeName || "").replace(/^.*:/, ""), attrs: Object.fromEntries(Array.from(element.attributes).map(attribute => [attribute.name, attribute.value])),
        text: Array.from(element.childNodes || []).filter(node => node.nodeType === 3).map(node => node.nodeValue || "").join(""), children: Array.from(element.children || []).map(row) });
      const currentRoot = row(qualifiedDoc.documentElement);
      const fixture = { schema: "figureStudio.ownSvgDeclaringPlaneFullFixture.v2", dom: currentRoot };
      const currentPlan = { ...qualified, svgText: JSON.stringify(currentRoot) };
      if (ownSvgDeclaringPlaneCandidate.admitted(fixture, currentPlan)) {
        const local = await ownSvgDeclaringPlaneCandidate.construct(fabric,
          { glyphPlan, registerTextClass, registerCurrentPlaneGroupClass, registerAuthoringLayoutManager, finalizeImportedAuthoringLayoutAsync }, fixture, currentPlan,
          { sourceFontPrograms, loadedFonts: fontResult.loaded, fallbackFont: options.fallbackFont, signal: options.signal, yieldToUi: options.yieldToUi });
        report.sourceDrawableCount = local.leaves.length;
        report.vectorCount = local.leaves.filter(source => source.kind !== "text").length;
        report.textRunCount = local.leaves.filter(source => source.kind === "text").length;
        report.groupCount = local.groups.length;
        report.clippedObjectCount = local.clips.length;
        report.sharedClipScopeCount = local.clips.length;
        report.collapsedNeutralScopeCount = 0;
        report.sourceCoordinatePolicy = "current-svg-declaring-planes";
        report.status = report.unsupported.length || report.fontFailures.length ? "unsupported" : "complete";
        report.elapsedMs = now() - started;
        options.onProgress?.({ stage: "complete", ...report });
        return { objects: [local.root], options: { width: qualified.width, height: qualified.height }, report };
      }
    }
    const TextClass = registerTextClass(fabric);
    registerGroupClass(fabric);
    const PathClass = registerPathClass(fabric);
    const view = viewport(root);
    const elements = Array.from(root.querySelectorAll("*"));
    const order = new Map(elements.map((element, index) => [element, index]));
    const groupByElement = new Map();
    const descriptors = [];
    visited = 0;
    for (const element of elements) {
      if (++visited % batchSize === 0) await checkpoint("structure", visited, elements.length);
      if (tag(element) !== "g" || inDefinition(element)) continue;
      const opacity = number(ownStyle(element, "opacity", "1"), 1);
      const named = element.id || element.getAttribute("data-pdf-scope") || element.getAttribute("data-pdf-form") || element.getAttribute("aria-label") || element.getAttribute("data-name") || element.getAttribute("clip-path") || (opacity < 1 ? "opacity" : "");
      if (!named) continue;
      let parent = element.parentElement;
      while (parent && !groupByElement.has(parent)) parent = parent.parentElement;
      const ancestor = groupByElement.get(parent);
      const key = `pdf-svg-group-${descriptors.length + 1}`;
      const path = [...(ancestor?.path || []), key];
      const unnamedClip = !element.id && !element.hasAttribute("aria-label") && !element.hasAttribute("data-name") && Boolean(ownStyle(element, "clip-path"));
      const neutralScope = opacity === 1 && !element.hasAttribute("data-pdf-form") && (unnamedClip || (element.getAttribute("data-pdf-scope") === "graphics-state" && /^pdf-scope-\d+$/.test(element.id) && !element.hasAttribute("clip-path")));
      const descriptor = { key, id: element.id || "", parent: ancestor?.key || "", path, opacity, neutralScope, clipRef: ownStyle(element, "clip-path"), order: order.get(element), meta: metadata(element, order.get(element), path, "group") };
      descriptors.push(descriptor); groupByElement.set(element, descriptor);
      if (opacity < 1) {
        element.removeAttribute("opacity");
        element.setAttribute("style", String(element.getAttribute("style") || "").split(";").filter((part) => part.split(":")[0].trim().toLowerCase() !== "opacity").join(";"));
      }
    }
    const groupPath = (element) => {
      for (let current = element.parentElement; current; current = current.parentElement) if (groupByElement.has(current)) return groupByElement.get(current).path;
      return [];
    };
    const sourceByKey = new Map();
    const textPlans = [];
    let nextKey = 0;
    const drawable = elements.filter((element) => DRAWABLE.has(tag(element)) && !inDefinition(element));
    report.sourceDrawableCount = drawable.length;
    visited = 0;
    for (const element of drawable) {
      if (++visited % batchSize === 0) await checkpoint("objects", visited, drawable.length);
      if (tag(element) !== "text") {
        const key = `pdf-svg-object-${++nextKey}`;
        element.setAttribute(KEY, key);
        const knockoutEntry = knockoutEntries.get(element.getAttribute("data-pdf-knockout-proxy-key"));
        const imageHint = options.nativePdfStrokeDisplay === true && tag(element) === "image"
          ? element.getAttribute("data-pdf-image-interpolate") : null;
        sourceByKey.set(key, { element, clipRef: clipReference(element), meta: metadata(element, order.get(element), groupPath(element), knockoutEntry ? "group" : tag(element) === "image" ? "image" : "path"),
          ...(["true", "false"].includes(imageHint) ? { imageInterpolation: imageHint === "true" } : {}), ...(knockoutEntry ? { knockoutEntry } : {}) });
        continue;
      }
      const spans = Array.from(element.querySelectorAll("tspan")).filter((span) => !span.querySelector("tspan"));
      const segments = spans.length ? spans : [element];
      const wrapper = doc.createElementNS(SVG_NS, "g");
      for (const attribute of element.attributes) wrapper.setAttribute(attribute.name, attribute.value);
      for (let segmentIndex = 0; segmentIndex < segments.length; segmentIndex++) {
        const span = segments[segmentIndex];
        const raw = String(span.textContent || "");
        const unicode = span.getAttribute("data-pdf-unicode") ?? element.getAttribute("data-pdf-unicode") ?? raw;
        if (!raw && !unicode) continue;
        let mapping = {};
        try { mapping = JSON.parse(span.getAttribute("data-pdf-glyph-map") || element.getAttribute("data-pdf-glyph-map") || "{}"); }
        catch (_error) { unsupported(span, "invalid-glyph-map", "The renderer provided an invalid text glyph mapping."); }
        const x = numbers(span.getAttribute("x") || element.getAttribute("x"));
        const y = numbers(span.getAttribute("y") || element.getAttribute("y"));
        const plan = glyphPlan(unicode, raw, { x, y }, mapping, fabric);
        if (x.length < plan.glyphs.length && plan.glyphs.length > 1) {
          // A normal SVG text run has implicit advances. Do not assign every
          // glyph to its initial x; the normal IText layout handles these runs.
          plan.glyphs = [];
        }
        if (plan.charCount !== graphemes(unicode, fabric).length && plan.glyphs.length) unsupported(span, "glyph-unicode-count", "Source glyphs and recovered Unicode cannot be aligned safely.");
        const key = `pdf-svg-object-${++nextKey}`;
        const surrogate = doc.createElementNS(SVG_NS, "rect");
        if (span !== element) for (const attribute of span.attributes) surrogate.setAttribute(attribute.name, attribute.value);
        surrogate.setAttribute(KEY, key);
        surrogate.setAttribute("x", String(plan.firstX)); surrogate.setAttribute("y", String(plan.firstY));
        surrogate.setAttribute("width", "0.01"); surrogate.setAttribute("height", "0.01");
        wrapper.appendChild(surrogate);
        const fontFamily = style(span, "font-family", "Arial").replace(/^['"]|['"]$/g, "");
        const textOptions = { fontFamily, fontSize: length(style(span, "font-size"), 10), fontWeight: style(span, "font-weight", "normal"), fontStyle: style(span, "font-style", "normal"), textAlign: "left", originX: "center", originY: "center", fill: style(span, "fill", "#000000"), stroke: style(span, "stroke", null), strokeWidth: length(style(span, "stroke-width"), 0), objectCaching: false, editable: true };
        const font = sourceFontPrograms.find((candidate) => candidate.family === fontFamily);
        const textSource = { schema: "figureStudio.pdfPositionedText.v1", text: unicode, anchor: style(span, "text-anchor", "start"), fontFamily, originalFontName: span.getAttribute("data-pdf-original-font") || element.getAttribute("data-pdf-original-font") || fontFamily, displayFontFamily: fontFamily, sourceEmbeddedProgram: Boolean(font?.dataUrl && fontResult.loaded.includes(fontFamily)), fontSubstitutionFamily: span.getAttribute("data-pdf-font-substitution") || element.getAttribute("data-pdf-font-substitution") || "", fontSize: textOptions.fontSize, fontWeight: textOptions.fontWeight, fontStyle: textOptions.fontStyle, map: { ...(font?.unicodeToFontChar || {}), ...plan.map }, unicodeAdvances: { ...(font?.unicodeAdvances || {}), ...plan.unicodeAdvances }, glyphs: plan.glyphs, fallbackFont: options.fallbackFont || "Arial" };
        // This inspection record follows the document's existing JSON number
        // semantics from its first capture. The actual plan/textSource above
        // keep their literal native glyph positions and paint authority.
        const meta = { ...metadata(span, order.get(element) + segmentIndex / 1000, groupPath(element), "text"), figureStudioSvgTextMeta: JSON.parse(JSON.stringify({ schema: "figureStudio.svgPositionedText.v1", sourceText: unicode, sourceGlyphText: raw, x: plan.firstX, y: plan.firstY, xPositions: x, yPositions: y, fontFamily, fontSize: textOptions.fontSize })) };
        if (options.logicalTextSource && span.hasAttribute("data-figure-studio-native-logical-glyph")) meta.figureStudioPdfLogicalGlyphIndex = Number(span.getAttribute("data-figure-studio-native-logical-glyph"));
        const textPlan = { key, unicode, plan, textSource, textOptions, meta, matrix: compositeMatrix(span, root, view.matrix), anchor: style(span, "text-anchor", "start") };
        textPlans.push(textPlan);
        sourceByKey.set(key, { element: span, clipRef: clipReference(span), meta, textPlan });
      }
      element.replaceWith(wrapper);
    }
    const clipDefinitions = new Map(Array.from(root.querySelectorAll("clipPath")).map((element) => [element.id, element]));
    const geometryCss = Array.from(root.querySelectorAll("style")).some((sheet) => String(sheet.textContent || "").replace(/@font-face\s*\{[^}]+\}/g, "").trim());
    const nativeObjects = [];
    const candidates = Array.from(sourceByKey).filter(([, source]) => source.element.getAttribute("data-pdf-native-rect-clip") === "1");
    for (let index = 0; index < candidates.length; index++) {
      const [key, source] = candidates[index];
      const object = await nativeRectanglePath(source.element, root, view, fabric, PathClass, clipDefinitions, geometryCss);
      if (object) { object.__pdfSvgKey = key; nativeObjects.push(object); source.element.remove(); report.nativeRectClipCount++; }
      else report.rejectedNativeRectClipCount++;
      if ((index + 1) % batchSize === 0) await checkpoint("native-clipped-paths", index + 1, candidates.length, true);
    }
    if (nativeObjects.length) {
      // Empty producer scopes and now-unreferenced clip definitions belong to
      // the direct objects. Keep the remaining SVG parser's DOM proportional to
      // the ordinary objects, rather than another 158k unused clip definitions.
      for (let index = elements.length - 1; index >= 0; index--) {
        const element = elements[index];
        if (tag(element) === "g" && !element.children.length && !element.textContent.trim()) element.remove();
        if (index % batchSize === 0) await checkpoint("prune-empty-scopes", elements.length - index, elements.length);
      }
      const references = new Set();
      visited = 0;
      for (const element of root.querySelectorAll("*")) {
        for (const attribute of element.attributes) for (const match of attribute.value.matchAll(/url\(['"]?#([^'")]+)['"]?\)/g)) references.add(match[1]);
        if (++visited % batchSize === 0) await checkpoint("retain-definitions", visited);
      }
      visited = 0;
      for (const [id, definition] of clipDefinitions) {
        if (!references.has(id)) definition.remove();
        if (++visited % batchSize === 0) await checkpoint("prune-definitions", visited, clipDefinitions.size);
      }
    }
    // Source DOM identity was needed while parsing inherited state. Release the
    // large detached producer tree before Fabric's remaining ordinary SVG load.
    groupByElement.clear(); order.clear(); clipDefinitions.clear(); elements.length = 0; drawable.length = 0; candidates.length = 0;
    for (const source of sourceByKey.values()) { source.tag = tag(source.element); delete source.element; }
    await checkpoint("svg-parser", nativeObjects.length, sourceByKey.size, true);
    const reviver = (element, object) => { object.__pdfSvgKey = element.getAttribute(KEY) || ""; };
    const loaded = await loadGeometryBatches(root, fabric, Serializer, reviver, options, checkpoint, report);
    const objects = [];
    const expected = sourceByKey.size;
    visited = 0;
    for (const original of [...nativeObjects, ...(loaded.objects || [])]) {
      if (++visited % batchSize === 0) await checkpoint("finalize-objects", visited, expected);
      if (!original) continue;
      const source = sourceByKey.get(original.__pdfSvgKey);
      if (!source) { unsupported(root, "unmapped-object", "An SVG object lost its source identity."); continue; }
      let object = original;
      // The parser's complete Path already owns its exact clip and transform.
      // Specialize rendering in place; rebuilding it would remeasure geometry.
      const nativePdfRectangle = options.nativePdfStrokeDisplay === true && source.tag === "path"
        && exactRectangleBounds(object.path) && !object.hasStroke() && typeof object.fill === "string" && /^#[0-9a-f]{6}$/i.test(object.fill);
      if (object.constructor === fabric.Path && (simpleNativeClip(object.clipPath, fabric)
          || nativePdfRectangle
          || options.nativePdfStrokeDisplay === true && typeof object.stroke === "string" && object.stroke
            && Number.isFinite(object.strokeWidth) && object.strokeWidth > 0)) {
        Object.setPrototypeOf(object, PathClass.prototype);
      }
      if (options.nativePdfStrokeDisplay === true && object.constructor === PathClass && source.tag === "path") {
        object.pdfDisplayStrokePolicy = "pdf-minimum-isotropic-device-pixel-v1";
        if (nativePdfRectangle) object.pdfDisplayFillPolicy = "pdf-opaque-axis-rectangle-device-pixels-v1";
      }
      if (source.knockoutEntry) {
        object = materializeKnockoutProxy(original, source.knockoutEntry, fabric);
        report.vectorCount += 2;
        report.sourceDrawableCount++;
      } else if (source.textPlan) {
        const run = source.textPlan;
        object = new TextClass(run.unicode, { ...run.textOptions, pdfTextSource: run.textSource });
        // Use the parser's resolved paint/opacity and clip; text baseline itself
        // uses the complete SVG affine transform, including shear and reflection.
        object.set({ fill: original.fill, stroke: original.stroke, strokeWidth: original.strokeWidth, strokeDashArray: original.strokeDashArray, opacity: original.opacity });
        const baseline = -object.height / 2 + object.getHeightOfLineImpl(0) * (1 - object._fontSizeFraction);
        let anchor = 0;
        if (run.anchor === "middle") anchor = -object.width / 2;
        if (run.anchor === "end") anchor = -object.width;
        const placement = multiply(run.matrix, [1, 0, 0, 1, run.plan.firstX + object.width / 2 + anchor, run.plan.firstY - baseline]);
        fabric.util.applyTransformToObject(object, placement);
        if (original.clipPath) {
          const clipWorld = multiply(original.calcTransformMatrix(), original.clipPath.calcTransformMatrix());
          const clipLocal = multiply(fabric.util.invertTransform(object.calcTransformMatrix()), clipWorld);
          fabric.util.applyTransformToObject(original.clipPath, clipLocal);
          object.clipPath = original.clipPath;
        }
        report.textRunCount++;
      } else if (source.tag === "image") {
        if (typeof source.imageInterpolation === "boolean") {
          const planes = typeof module === "object" && module.exports
            ? require("./pdf-current-native-plane-materializer.js") : globalThis.FigureStudioPdfCurrentNativePlaneMaterializer;
          // Reuse the existing image serializer in place: native Fabric omits
          // imageSmoothing from Save. Pixels, pose and clipping stay untouched.
          if (!planes?.retainImageInterpolation) throw new Error("The editable PDF image cannot preserve its interpolation setting.");
          planes.retainImageInterpolation(fabric, object, source.imageInterpolation);
        }
        report.imageCount++;
      } else report.vectorCount++;
      object.set(source.meta);
      object.__pdfSvgClipRef = source.clipRef;
      sourceByKey.delete(original.__pdfSvgKey);
      delete original.__pdfSvgKey;
      object.setCoords?.();
      if (object.clipPath) report.clippedObjectCount++;
      objects.push(object);
    }
    if (objects.length !== expected) unsupported(root, "missing-objects", `${expected - objects.length} SVG objects were not materialized.`);
    let hierarchyObjects = objects;
    if (options.logicalTextSource) {
      const logical = typeof module === "object" && module.exports ? require("./pdf-logical-text-runtime.js") : globalThis.FigureStudioPdfLogicalTextRuntime;
      try {
        const joined = await logical.coalesceCurrentObjects(objects, { token: options.logicalTextSource, svgText, fabric, TextClass, descriptors });
        hierarchyObjects = joined.objects;
        report.logicalText = { status: joined.status, runCount: joined.runCount, nativeGlyphCount: joined.nativeGlyphCount };
        report.textRunCount = joined.runCount;
      } catch (error) {
        if (error.code !== "PDF_LOGICAL_TEXT_UNSUPPORTED") throw error;
        report.logicalText = { status: "unsupported-current-source", reason: String(error.message) };
      }
    }
    initializeImportedClipRuleDefaults(hierarchyObjects);
    const hierarchy = await groupHierarchy(hierarchyObjects, descriptors, fabric, options.onDiagnostic, checkpoint);
    // Hierarchy construction can attach inherited clips after parsing. Adopt
    // the final eligible Path in place, retaining every path, clip and pose.
    const pendingNativeClips = [...hierarchy.objects];
    let finalizedNativeClips = 0;
    while (pendingNativeClips.length) {
      const object = pendingNativeClips.pop();
      if (object.constructor === fabric.Path && simpleNativeClip(object.clipPath, fabric)) Object.setPrototypeOf(object, PathClass.prototype);
      for (const child of object.getObjects?.() || []) pendingNativeClips.push(child);
      if (++finalizedNativeClips % batchSize === 0) await checkpoint("finalize-vector-clips", finalizedNativeClips, report.sourceDrawableCount);
    }
    await finalizeImportedAuthoringLayoutAsync(hierarchy.objects, { fabric, signal: options.signal,
      yieldToUi: options.yieldToUi, onProgress: options.onProgress });
    report.groupCount = hierarchy.count;
    if (knockoutEntries.size) {
      report.knockoutGroupCount = knockoutEntries.size;
      report.canonicalKnockoutMemberCount = knockoutEntries.size * 2;
      report.groupCount += knockoutEntries.size;
    }
    report.collapsedNeutralScopeCount = hierarchy.collapsed;
    report.sharedClipScopeCount = hierarchy.sharedClips;
    report.avoidedIndividualClipCount = hierarchy.hoistedLeaves;
    report.status = report.unsupported.length || report.fontFailures.length ? "unsupported" : "complete";
    report.elapsedMs = (globalThis.performance?.now?.() || Date.now()) - started;
    options.onProgress?.({ stage: "complete", ...report });
    return { objects: hierarchy.objects, options: { ...(loaded.options || {}), width: view.width, height: view.height }, report };
  }

  return Object.freeze({ SCHEMA, materialize, prepareSvgOpenDocument, validateKnockoutMarker, extractKnockoutRoots, materializeKnockoutProxy, registerTextClass, registerGroupClass, registerCurrentPlaneGroupClass, registerAuthoringLayoutManager, createAuthoringLayoutManager, finalizeImportedAuthoringLayout, finalizeImportedAuthoringLayoutAsync, prepareImportedTextDisplayAsync, nativeScenePaintKind, bindStartupTextLineRenderer, bindStartupTextStyleDeclaration, registerPathClass, registerCurrentPlanePathClass, isNativeRectangleDisplayPath, registerFonts, prepareGroupRelease, multiply, transformMatrix, viewport, glyphPlan, xmlGlyph, rectangleBounds });
});
