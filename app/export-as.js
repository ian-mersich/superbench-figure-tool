/*
 * Figure Tool mode-aware Export As engine.
 *
 * This module owns export policy, validation, file naming, multi-output
 * packaging, TIFF encoding, and truthful destination status. The editor owns
 * rendering and supplies the hooks listed in RENDERER_KEYS. Keeping those
 * boundaries explicit prevents Export As from reading global canvas or deck
 * state and makes every export target the active document passed by the tab
 * controller.
 *
 * Browser: window.FigureStudioExportAs
 * Node QA: require("./export-as.js")
 */
(function exposeFigureStudioExportAs(root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  if (root) root.FigureStudioExportAs = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function createFigureStudioExportAsModule() {
  "use strict";

  const VERSION = "1.0.0";
  const CSS_PIXELS_PER_INCH = 96;
  const DPI_PRESETS = Object.freeze([96, 150, 300, 600]);
  const MIN_DPI = 36;
  const MAX_DPI = 2400;
  const MAX_RASTER_DIMENSION = 100000;
  const MAX_RASTER_PIXELS = 144000000;
  const MAX_PACKAGE_BYTES = 512 * 1024 * 1024;

  const MIME_TYPES = Object.freeze({
    svg: "image/svg+xml",
    pdf: "application/pdf",
    png: "image/png",
    jpeg: "image/jpeg",
    tiff: "image/tiff",
    pptx: "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    zip: "application/zip"
  });

  const EXTENSIONS = Object.freeze({
    svg: "svg",
    pdf: "pdf",
    png: "png",
    jpeg: "jpg",
    tiff: "tiff",
    pptx: "pptx",
    zip: "zip"
  });

  const FORMAT_CATALOG = deepFreeze({
    figure: {
      svg: {
        label: "SVG",
        outputKind: "vector",
        scopes: ["current", "all"],
        renderer: "renderFigureSvg",
        perTarget: true,
        supportsBackground: true,
        supportsTransparency: true
      },
      pdf: {
        label: "PDF",
        outputKind: "vector",
        scopes: ["current", "all"],
        renderer: "renderFigurePdf",
        perTarget: false,
        supportsBackground: false,
        supportsTransparency: false
      },
      png: rasterFormat("PNG", "renderFigureRaster", true),
      jpeg: rasterFormat("JPEG", "renderFigureRaster", false),
      tiff: rasterFormat("TIFF", "renderFigureRaster", true)
    },
    presentation: {
      pptx: {
        label: "PPTX",
        outputKind: "document",
        scopes: ["all"],
        renderer: "renderPresentationPptx",
        perTarget: false,
        supportsBackground: false,
        supportsTransparency: false
      },
      pdf: {
        label: "PDF",
        outputKind: "vector",
        scopes: ["all"],
        renderer: "renderPresentationPdf",
        perTarget: false,
        supportsBackground: false,
        supportsTransparency: false
      },
      png: rasterFormat("PNG", "renderPresentationRaster", true),
      jpeg: rasterFormat("JPEG", "renderPresentationRaster", false),
      tiff: rasterFormat("TIFF", "renderPresentationRaster", true)
    }
  });

  const RENDERER_KEYS = deepFreeze({
    renderFigureSvg: "Render one Figure artboard as SVG.",
    renderFigurePdf: "Render the requested Figure artboard set as one PDF.",
    renderFigureRaster: "Render one Figure artboard as PNG, JPEG, or pixels for TIFF.",
    renderPresentationPptx: "Render the complete Presentation document using the bounded PPTX subset.",
    renderPresentationPdf: "Render the complete Presentation document as one PDF.",
    renderPresentationRaster: "Render one Presentation slide as PNG, JPEG, or pixels for TIFF."
  });

  function rasterFormat(label, renderer, supportsTransparency) {
    return {
      label,
      outputKind: "raster",
      scopes: ["current", "all"],
      renderer,
      perTarget: true,
      supportsBackground: true,
      supportsTransparency
    };
  }

  function deepFreeze(value) {
    if (!value || typeof value !== "object" || Object.isFrozen(value)) return value;
    Object.values(value).forEach(deepFreeze);
    return Object.freeze(value);
  }

  function exportError(code, message, details = {}) {
    const error = new Error(message);
    error.name = "FigureStudioExportError";
    error.code = code;
    Object.assign(error, details);
    return error;
  }

  function finite(value, fallback = NaN) {
    const number = Number(value);
    return Number.isFinite(number) ? number : fallback;
  }

  function clamp(value, minimum, maximum) {
    return Math.min(maximum, Math.max(minimum, value));
  }

  function documentKind(document) {
    const kind = String(
      document?.kind
      || document?.document?.kind
      || document?.project?.document?.kind
      || "figure"
    ).toLowerCase();
    if (kind !== "figure" && kind !== "presentation") {
      throw exportError("document-kind-unsupported", `Export As does not support the document kind "${kind || "unknown"}".`);
    }
    return kind;
  }

  function basename(path) {
    return String(path || "").split(/[\\/]/).filter(Boolean).pop() || "";
  }

  function stripKnownExtension(filename) {
    return String(filename || "").replace(/\.(fsfigure|fsdeck|fsproject|figure-studio|presentation|json|svg|pdf|png|jpe?g|tiff?|pptx)$/i, "");
  }

  function documentLabel(document, kind = documentKind(document)) {
    const candidate = document?.displayName
      || document?.filename
      || basename(document?.filePath)
      || document?.name
      || document?.title;
    const fallback = kind === "presentation" ? "Untitled Presentation" : "Untitled Figure";
    return String(candidate || fallback).trim() || fallback;
  }

  function safeFileStem(value, fallback = "Figure Tool export") {
    const cleaned = stripKnownExtension(value)
      .replace(/[<>:"/\\|?*\u0000-\u001f]/g, " ")
      .replace(/[. ]+$/g, "")
      .replace(/\s+/g, " ")
      .trim();
    return (cleaned || fallback).slice(0, 120);
  }

  function itemLabel(item, index, kind) {
    const fallback = kind === "presentation" ? `Slide ${index + 1}` : `Artboard ${index + 1}`;
    return String(item?.label || item?.name || item?.title || fallback).trim() || fallback;
  }

  function itemId(item, index, kind) {
    const prefix = kind === "presentation" ? "slide" : "artboard";
    return String(item?.id || item?.pageId || `${prefix}-${index + 1}`);
  }

  function defaultItems(document, kind) {
    if (kind === "presentation") {
      const pages = document?.slides
        || document?.deck?.pages
        || document?.project?.deck?.pages;
      if (Array.isArray(pages) && pages.length) return pages;
      return [{
        id: "slide-1",
        label: "Slide 1",
        artboard: document?.artboard || document?.project?.artboard
      }];
    }
    const artboards = document?.artboards
      || document?.pages
      || document?.project?.artboards
      || document?.project?.document?.artboards;
    if (Array.isArray(artboards) && artboards.length) return artboards;
    return [{
      id: "artboard-1",
      label: "Artboard 1",
      artboard: document?.artboard || document?.project?.artboard
    }];
  }

  function activeItemId(document, kind) {
    return String(kind === "presentation"
      ? (document?.activeSlideId || document?.activePageId || document?.deck?.activePageId || document?.project?.deck?.activePageId || "")
      : (document?.activeArtboardId || document?.activePageId || document?.project?.activeArtboardId || ""));
  }

  function geometryForTarget(document, target, kind) {
    const geometry = target?.artboard
      || target?.geometry
      || target?.pageGeometry
      || target
      || {};
    const fallback = document?.artboard
      || document?.project?.artboard
      || document?.project?.document?.pageGeometry?.defaultArtboard
      || {};
    let widthIn = finite(geometry.widthIn, finite(fallback.widthIn));
    let heightIn = finite(geometry.heightIn, finite(fallback.heightIn));
    const widthPx = finite(geometry.width, finite(geometry.widthPx, finite(fallback.width, finite(fallback.widthPx))));
    const heightPx = finite(geometry.height, finite(geometry.heightPx, finite(fallback.height, finite(fallback.heightPx))));
    if (!(widthIn > 0) && widthPx > 0) widthIn = widthPx / CSS_PIXELS_PER_INCH;
    if (!(heightIn > 0) && heightPx > 0) heightIn = heightPx / CSS_PIXELS_PER_INCH;
    if (!(widthIn > 0)) widthIn = kind === "presentation" ? 13.333333 : 7.1;
    if (!(heightIn > 0)) heightIn = kind === "presentation" ? 7.5 : 5;
    return {
      widthIn,
      heightIn,
      widthPx: Math.max(1, Math.round(widthIn * CSS_PIXELS_PER_INCH)),
      heightPx: Math.max(1, Math.round(heightIn * CSS_PIXELS_PER_INCH))
    };
  }

  function normalizeItems(document, kind, getItems) {
    const rawItems = typeof getItems === "function" ? getItems(document, kind) : defaultItems(document, kind);
    if (!Array.isArray(rawItems) || !rawItems.length) {
      throw exportError("export-target-missing", `The ${kind === "presentation" ? "presentation has no slides" : "figure has no artboards"} to export.`);
    }
    return rawItems.map((source, index) => ({
      id: itemId(source, index, kind),
      label: itemLabel(source, index, kind),
      index,
      geometry: geometryForTarget(document, source, kind),
      source
    }));
  }

  function activeItem(items, requestedId) {
    return items.find((item) => item.id === requestedId) || items[0];
  }

  function controlsForFormat(definition) {
    const controls = {};
    if (definition.outputKind === "raster") {
      controls.resolution = {
        modes: ["dpi", "pixels", "scale"],
        dpiPresets: [...DPI_PRESETS],
        customDpi: { minimum: MIN_DPI, maximum: MAX_DPI },
        customDimensions: true,
        maximumDimension: MAX_RASTER_DIMENSION,
        maximumPixels: MAX_RASTER_PIXELS
      };
    }
    if (definition.supportsBackground) {
      controls.background = {
        modes: definition.supportsTransparency
          ? ["document", "transparent", "custom"]
          : ["document", "custom"],
        transparency: definition.supportsTransparency
      };
    }
    return controls;
  }

  function describeDocument(document, options = {}) {
    const kind = documentKind(document);
    const items = normalizeItems(document, kind, options.getItems);
    const renderers = options.renderers || {};
    const formats = Object.entries(FORMAT_CATALOG[kind]).map(([id, definition]) => ({
      id,
      label: definition.label,
      outputKind: definition.outputKind,
      extension: EXTENSIONS[id],
      mimeType: MIME_TYPES[id],
      scopes: definition.scopes.filter((scope) => scope !== "all" || items.length > 1 || definition.scopes.length === 1),
      controls: controlsForFormat(definition),
      available: typeof renderers[definition.renderer] === "function",
      unavailableReason: typeof renderers[definition.renderer] === "function"
        ? ""
        : `${definition.label} rendering has not been connected in this workspace.`
    }));
    const inferredEnvironment = typeof options.destination?.saveFile === "function" ? "native" : "browser";
    const environment = String(options.environment || options.destination?.kind || inferredEnvironment).toLowerCase();
    return {
      schema: "figureStudio.exportSurface.v1",
      document: {
        id: String(document?.id || ""),
        kind,
        name: documentLabel(document, kind),
        activeItemId: activeItem(items, activeItemId(document, kind)).id,
        itemCount: items.length
      },
      delivery: {
        single: ["file"],
        multiple: environment === "native" && typeof options.destination?.saveFiles === "function"
          ? ["folder", "package"]
          : ["package"]
      },
      formats
    };
  }

  function hasResolutionRequest(request) {
    return request?.resolution != null
      || request?.dpi != null
      || request?.widthPx != null
      || request?.heightPx != null
      || request?.scale != null;
  }

  function normalizeResolution(request, geometry) {
    const input = request?.resolution;
    const normalized = input && typeof input === "object" ? { ...input } : {};
    if (typeof input === "number") normalized.dpi = input;
    if (typeof input === "string" && /^\d+(?:\.\d+)?$/.test(input.trim())) normalized.dpi = Number(input);
    if (request?.dpi != null) normalized.dpi = request.dpi;
    if (request?.widthPx != null) normalized.widthPx = request.widthPx;
    if (request?.heightPx != null) normalized.heightPx = request.heightPx;
    if (request?.scale != null) normalized.scale = request.scale;
    const mode = String(normalized.mode || (normalized.widthPx != null || normalized.heightPx != null ? "pixels" : normalized.scale != null ? "scale" : "dpi")).toLowerCase();
    let widthPx;
    let heightPx;
    let dpi;
    let scale;
    if (mode === "dpi") {
      dpi = finite(normalized.dpi, 300);
      if (dpi < MIN_DPI || dpi > MAX_DPI) {
        throw exportError("resolution-out-of-range", `Raster resolution must be between ${MIN_DPI} and ${MAX_DPI} DPI.`);
      }
      widthPx = Math.round(geometry.widthIn * dpi);
      heightPx = Math.round(geometry.heightIn * dpi);
      scale = dpi / CSS_PIXELS_PER_INCH;
    } else if (mode === "scale") {
      scale = finite(normalized.scale, NaN);
      if (!(scale >= 0.1 && scale <= 25)) {
        throw exportError("scale-out-of-range", "Raster scale must be between 0.1x and 25x.");
      }
      widthPx = Math.round(geometry.widthPx * scale);
      heightPx = Math.round(geometry.heightPx * scale);
      dpi = CSS_PIXELS_PER_INCH * scale;
    } else if (mode === "pixels") {
      widthPx = finite(normalized.widthPx, NaN);
      heightPx = finite(normalized.heightPx, NaN);
      if (!(widthPx > 0) && !(heightPx > 0)) {
        throw exportError("dimensions-required", "Enter an export width, height, or both.");
      }
      if (!(widthPx > 0)) widthPx = heightPx * (geometry.widthIn / geometry.heightIn);
      if (!(heightPx > 0)) heightPx = widthPx * (geometry.heightIn / geometry.widthIn);
      widthPx = Math.round(widthPx);
      heightPx = Math.round(heightPx);
      dpi = widthPx / geometry.widthIn;
      scale = dpi / CSS_PIXELS_PER_INCH;
    } else {
      throw exportError("resolution-mode-unsupported", `The raster resolution mode "${mode}" is not supported.`);
    }
    if (widthPx < 1 || heightPx < 1 || widthPx > MAX_RASTER_DIMENSION || heightPx > MAX_RASTER_DIMENSION) {
      throw exportError("dimensions-out-of-range", `Raster dimensions must be between 1 and ${MAX_RASTER_DIMENSION.toLocaleString("en-US")} pixels.`);
    }
    if (widthPx * heightPx > MAX_RASTER_PIXELS) {
      throw exportError("raster-too-large", `This export would create ${Math.round(widthPx * heightPx / 1000000)} million pixels. Reduce the dimensions or resolution.`);
    }
    return { mode, dpi, scale, widthPx, heightPx };
  }

  function normalizeBackground(request, definition) {
    if (!definition.supportsBackground) return null;
    const input = request?.background;
    const background = typeof input === "string" ? { mode: input } : { ...(input || {}) };
    const mode = String(background.mode || "document").toLowerCase();
    if (!controlsForFormat(definition).background.modes.includes(mode)) {
      const explanation = mode === "transparent"
        ? `${definition.label} does not support transparent background export.`
        : `The background option "${mode}" is not available for ${definition.label}.`;
      throw exportError("background-unsupported", explanation);
    }
    if (mode === "custom" && !String(background.color || "").trim()) {
      throw exportError("background-color-required", "Choose a custom background color before exporting.");
    }
    return { mode, color: mode === "custom" ? String(background.color).trim() : null };
  }

  function uniqueTargetFilenames(documentName, targets, extension) {
    const used = new Set();
    return targets.map((target) => {
      const base = safeFileStem(`${documentName} - ${target.label}`);
      let stem = base;
      let suffix = 2;
      while (used.has(stem.toLowerCase())) {
        stem = `${base} ${suffix}`;
        suffix += 1;
      }
      used.add(stem.toLowerCase());
      return `${stem}.${extension}`;
    });
  }

  function makePlan(document, request = {}, options = {}) {
    const kind = documentKind(document);
    const format = String(request.format || "").toLowerCase().replace(/^jpg$/, "jpeg").replace(/^tif$/, "tiff");
    const definition = FORMAT_CATALOG[kind][format];
    if (!definition) {
      throw exportError("format-not-supported", `${format ? format.toUpperCase() : "That format"} is not available for ${kind === "presentation" ? "Presentation" : "Figure"} documents.`);
    }
    if (definition.outputKind !== "raster" && hasResolutionRequest(request)) {
      throw exportError("resolution-not-applicable", `${definition.label} is not a raster format, so DPI and pixel dimensions do not apply.`);
    }
    const items = normalizeItems(document, kind, options.getItems);
    const requestedScope = String(request.scope || definition.scopes[0]).toLowerCase();
    if (!definition.scopes.includes(requestedScope)) {
      throw exportError("scope-not-supported", `${definition.label} export for ${kind === "presentation" ? "Presentations" : "Figures"} does not support ${requestedScope === "current" ? "current-only" : requestedScope} scope.`);
    }
    const selectedTargets = requestedScope === "all"
      ? items
      : [activeItem(items, String(request.activeItemId || activeItemId(document, kind)))];
    const name = documentLabel(document, kind);
    const stem = safeFileStem(name);
    const extension = EXTENSIONS[format];
    const perTargetFilenames = uniqueTargetFilenames(stem, selectedTargets, extension);
    const background = normalizeBackground(request, definition);
    const targets = selectedTargets.map((target, index) => ({
      ...target,
      filename: definition.perTarget && selectedTargets.length > 1
        ? perTargetFilenames[index]
        : `${stem}.${extension}`,
      resolution: definition.outputKind === "raster" ? normalizeResolution(request, target.geometry) : null
    }));
    const multiFile = definition.perTarget && targets.length > 1;
    const deliveryChoices = multiFile ? ["folder", "package"] : ["file"];
    return {
      schema: "figureStudio.exportPlan.v1",
      document: {
        id: String(document?.id || ""),
        kind,
        name,
        source: document
      },
      format,
      formatLabel: definition.label,
      mimeType: MIME_TYPES[format],
      extension,
      outputKind: definition.outputKind,
      scope: requestedScope,
      targets,
      multiFile,
      deliveryChoices,
      requestedDelivery: String(request.delivery || "auto").toLowerCase(),
      background,
      renderer: definition.renderer,
      perTarget: definition.perTarget,
      warnings: []
    };
  }

  function bytesFromString(value) {
    return new TextEncoder().encode(String(value));
  }

  function bytesFromDataUrl(dataUrl) {
    const match = String(dataUrl || "").match(/^data:([^;,]+)?(?:;charset=[^;,]+)?(;base64)?,([\s\S]*)$/i);
    if (!match) throw exportError("artifact-data-url-invalid", "The renderer returned an invalid data URL.");
    if (match[2]) {
      const binary = typeof atob === "function"
        ? atob(match[3])
        : Buffer.from(match[3], "base64").toString("binary");
      return Uint8Array.from(binary, (character) => character.charCodeAt(0));
    }
    return bytesFromString(decodeURIComponent(match[3]));
  }

  async function toUint8Array(value) {
    if (value instanceof Uint8Array) return value;
    if (ArrayBuffer.isView(value)) return new Uint8Array(value.buffer, value.byteOffset, value.byteLength);
    if (value instanceof ArrayBuffer) return new Uint8Array(value);
    if (typeof Blob !== "undefined" && value instanceof Blob) return new Uint8Array(await value.arrayBuffer());
    throw exportError("artifact-bytes-missing", "The export renderer did not return readable file bytes.");
  }

  function startsWith(bytes, values) {
    return values.every((value, index) => bytes[index] === value);
  }

  function validateArtifactSignature(format, bytes) {
    const textPrefix = () => new TextDecoder().decode(bytes.subarray(0, Math.min(bytes.length, 256))).replace(/^\uFEFF/, "").trimStart();
    const valid = {
      svg: () => /^(?:<\?xml[\s\S]*?\?>\s*)?<svg\b/i.test(textPrefix()),
      pdf: () => textPrefix().startsWith("%PDF-"),
      png: () => startsWith(bytes, [0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]),
      jpeg: () => startsWith(bytes, [0xff, 0xd8, 0xff]),
      tiff: () => startsWith(bytes, [0x49, 0x49, 0x2a, 0x00]) || startsWith(bytes, [0x4d, 0x4d, 0x00, 0x2a]),
      pptx: () => startsWith(bytes, [0x50, 0x4b, 0x03, 0x04]),
      zip: () => startsWith(bytes, [0x50, 0x4b, 0x03, 0x04])
    }[format];
    if (valid && !valid()) {
      throw exportError("artifact-format-mismatch", `The renderer did not return a valid ${format.toUpperCase()} file, so Figure Tool did not save it.`);
    }
  }

  function parseHexColor(value, fallback = [255, 255, 255]) {
    const match = String(value || "").trim().match(/^#([0-9a-f]{3}|[0-9a-f]{6})$/i);
    if (!match) return fallback;
    const hex = match[1].length === 3
      ? match[1].split("").map((digit) => digit + digit).join("")
      : match[1];
    return [parseInt(hex.slice(0, 2), 16), parseInt(hex.slice(2, 4), 16), parseInt(hex.slice(4, 6), 16)];
  }

  function normalizeTiffPixels(input, transparent, backgroundColor) {
    const width = Math.round(finite(input?.width, NaN));
    const height = Math.round(finite(input?.height, NaN));
    const source = input?.data;
    let channels = Math.round(finite(input?.channels, NaN));
    if (!channels && source && width > 0 && height > 0) channels = source.length / (width * height);
    if (!(width > 0 && height > 0) || ![3, 4].includes(channels) || !source || source.length !== width * height * channels) {
      throw exportError("tiff-pixels-invalid", "TIFF export requires complete RGB or RGBA pixel data from the renderer.");
    }
    if (width > MAX_RASTER_DIMENSION || height > MAX_RASTER_DIMENSION || width * height > MAX_RASTER_PIXELS) {
      throw exportError("tiff-pixels-too-large", "The TIFF pixel buffer exceeds Figure Tool's safe raster export limit.");
    }
    if (transparent) {
      if (channels !== 4) throw exportError("tiff-alpha-missing", "Transparent TIFF export requires RGBA pixels from the renderer.");
      return { width, height, channels, data: Uint8Array.from(source) };
    }
    if (channels === 3) return { width, height, channels, data: Uint8Array.from(source) };
    const background = parseHexColor(backgroundColor);
    const data = new Uint8Array(width * height * 3);
    for (let sourceIndex = 0, targetIndex = 0; sourceIndex < source.length; sourceIndex += 4, targetIndex += 3) {
      const alpha = source[sourceIndex + 3] / 255;
      data[targetIndex] = Math.round(source[sourceIndex] * alpha + background[0] * (1 - alpha));
      data[targetIndex + 1] = Math.round(source[sourceIndex + 1] * alpha + background[1] * (1 - alpha));
      data[targetIndex + 2] = Math.round(source[sourceIndex + 2] * alpha + background[2] * (1 - alpha));
    }
    return { width, height, channels: 3, data };
  }

  function encodeTiff(input, options = {}) {
    const pixels = normalizeTiffPixels(input, options.transparent === true, options.backgroundColor);
    const dpi = clamp(Math.round(finite(options.dpi, 300)), 1, 65535);
    const hasAlpha = pixels.channels === 4;
    const tags = [
      [256, 4, 1, pixels.width],
      [257, 4, 1, pixels.height],
      [258, 3, pixels.channels, "bits"],
      [259, 3, 1, 1],
      [262, 3, 1, 2],
      [273, 4, 1, "pixels"],
      [274, 3, 1, 1],
      [277, 3, 1, pixels.channels],
      [278, 4, 1, pixels.height],
      [279, 4, 1, pixels.data.length],
      [282, 5, 1, "xResolution"],
      [283, 5, 1, "yResolution"],
      [284, 3, 1, 1],
      [296, 3, 1, 2]
    ];
    if (hasAlpha) tags.push([338, 3, 1, 2]);
    tags.sort((left, right) => left[0] - right[0]);
    const ifdOffset = 8;
    const ifdBytes = 2 + tags.length * 12 + 4;
    let cursor = ifdOffset + ifdBytes;
    const bitsOffset = cursor;
    cursor += pixels.channels * 2;
    if (cursor % 4) cursor += 4 - (cursor % 4);
    const xResolutionOffset = cursor;
    cursor += 8;
    const yResolutionOffset = cursor;
    cursor += 8;
    const pixelOffset = cursor;
    const output = new Uint8Array(pixelOffset + pixels.data.length);
    const view = new DataView(output.buffer);
    output[0] = 0x49;
    output[1] = 0x49;
    view.setUint16(2, 42, true);
    view.setUint32(4, ifdOffset, true);
    view.setUint16(ifdOffset, tags.length, true);
    const resolvedValue = (value) => ({ bits: bitsOffset, pixels: pixelOffset, xResolution: xResolutionOffset, yResolution: yResolutionOffset }[value] ?? value);
    tags.forEach((entry, index) => {
      const [tag, type, count, unresolved] = entry;
      const offset = ifdOffset + 2 + index * 12;
      const value = resolvedValue(unresolved);
      view.setUint16(offset, tag, true);
      view.setUint16(offset + 2, type, true);
      view.setUint32(offset + 4, count, true);
      if (type === 3 && count === 1) view.setUint16(offset + 8, value, true);
      else view.setUint32(offset + 8, value, true);
    });
    view.setUint32(ifdOffset + 2 + tags.length * 12, 0, true);
    for (let index = 0; index < pixels.channels; index += 1) view.setUint16(bitsOffset + index * 2, 8, true);
    view.setUint32(xResolutionOffset, dpi, true);
    view.setUint32(xResolutionOffset + 4, 1, true);
    view.setUint32(yResolutionOffset, dpi, true);
    view.setUint32(yResolutionOffset + 4, 1, true);
    output.set(pixels.data, pixelOffset);
    return output;
  }

  async function normalizeArtifact(result, format, suggestedFilename, context) {
    let candidate = result;
    if (candidate == null) throw exportError("renderer-returned-nothing", `The ${format.toUpperCase()} renderer did not create a file.`);
    if (typeof candidate === "string") {
      candidate = candidate.startsWith("data:") ? { dataUrl: candidate } : { text: candidate };
    } else if (candidate instanceof Uint8Array || candidate instanceof ArrayBuffer || ArrayBuffer.isView(candidate) || (typeof Blob !== "undefined" && candidate instanceof Blob)) {
      candidate = { bytes: candidate };
    }
    let bytes;
    if (candidate.pixels) {
      if (format !== "tiff") throw exportError("pixel-artifact-format-invalid", "Raw pixels can only be finalized by the TIFF export path.");
      bytes = encodeTiff(candidate.pixels, {
        dpi: context.resolution?.dpi,
        transparent: context.background?.mode === "transparent",
        backgroundColor: context.background?.color
      });
    } else if (candidate.dataUrl) {
      bytes = bytesFromDataUrl(candidate.dataUrl);
    } else if (candidate.text != null) {
      bytes = bytesFromString(candidate.text);
    } else {
      bytes = await toUint8Array(candidate.bytes ?? candidate.blob);
    }
    validateArtifactSignature(format, bytes);
    const filename = basename(candidate.filename || suggestedFilename || `Figure Tool export.${EXTENSIONS[format]}`);
    return {
      filename: filename.toLowerCase().endsWith(`.${EXTENSIONS[format]}`) ? filename : `${filename}.${EXTENSIONS[format]}`,
      format,
      mimeType: MIME_TYPES[format],
      bytes,
      size: bytes.byteLength,
      warnings: Array.isArray(candidate.warnings) ? candidate.warnings : []
    };
  }

  async function renderPlan(plan, renderers) {
    const renderer = renderers?.[plan.renderer];
    if (typeof renderer !== "function") {
      throw exportError("renderer-unavailable", `${plan.formatLabel} export has not been connected in this workspace. No file was created.`, { renderer: plan.renderer });
    }
    if (!plan.perTarget) {
      const suggestedFilename = `${safeFileStem(plan.document.name)}.${plan.extension}`;
      const result = await renderer({
        document: plan.document.source,
        documentInfo: plan.document,
        format: plan.format,
        scope: plan.scope,
        targets: plan.targets,
        background: plan.background,
        suggestedFilename
      });
      return [await normalizeArtifact(result, plan.format, suggestedFilename, {
        background: plan.background,
        resolution: null
      })];
    }
    const artifacts = [];
    for (const target of plan.targets) {
      const result = await renderer({
        document: plan.document.source,
        documentInfo: plan.document,
        format: plan.format,
        scope: plan.scope,
        target,
        background: plan.background,
        resolution: target.resolution,
        suggestedFilename: target.filename
      });
      artifacts.push(await normalizeArtifact(result, plan.format, target.filename, {
        background: plan.background,
        resolution: target.resolution
      }));
    }
    return artifacts;
  }

  function crc32(bytes) {
    let crc = 0xffffffff;
    for (let index = 0; index < bytes.length; index += 1) {
      crc ^= bytes[index];
      for (let bit = 0; bit < 8; bit += 1) crc = (crc >>> 1) ^ (0xedb88320 & -(crc & 1));
    }
    return (crc ^ 0xffffffff) >>> 0;
  }

  function dosDateTime(value) {
    const date = value instanceof Date && Number.isFinite(value.getTime()) ? value : new Date();
    const year = clamp(date.getFullYear(), 1980, 2107);
    return {
      date: ((year - 1980) << 9) | ((date.getMonth() + 1) << 5) | date.getDate(),
      time: (date.getHours() << 11) | (date.getMinutes() << 5) | Math.floor(date.getSeconds() / 2)
    };
  }

  function joinBytes(parts) {
    const total = parts.reduce((sum, part) => sum + part.length, 0);
    const result = new Uint8Array(total);
    let offset = 0;
    parts.forEach((part) => {
      result.set(part, offset);
      offset += part.length;
    });
    return result;
  }

  function buildStoredZip(entries, options = {}) {
    if (!Array.isArray(entries) || !entries.length) throw exportError("package-empty", "There are no files to package.");
    if (entries.length > 65535) throw exportError("package-entry-limit", "The multi-file export contains too many files for one ZIP package.");
    const localParts = [];
    const centralParts = [];
    const stamp = dosDateTime(options.date);
    let localOffset = 0;
    let totalBytes = 0;
    entries.forEach((entry) => {
      const path = String(entry.path || "").replace(/\\/g, "/").replace(/^\/+/, "");
      if (!path || path.includes("../")) throw exportError("package-path-invalid", `The package path "${path}" is not safe.`);
      const name = bytesFromString(path);
      if (name.length > 65535) throw exportError("package-path-too-long", "An export filename is too long for a ZIP package.");
      const data = entry.bytes instanceof Uint8Array ? entry.bytes : bytesFromString(entry.bytes || "");
      totalBytes += data.length;
      if (totalBytes > MAX_PACKAGE_BYTES) throw exportError("package-too-large", "The multi-file export exceeds the 512 MB package limit.");
      const checksum = crc32(data);
      const local = new Uint8Array(30 + name.length);
      const localView = new DataView(local.buffer);
      localView.setUint32(0, 0x04034b50, true);
      localView.setUint16(4, 20, true);
      localView.setUint16(6, 0x0800, true);
      localView.setUint16(8, 0, true);
      localView.setUint16(10, stamp.time, true);
      localView.setUint16(12, stamp.date, true);
      localView.setUint32(14, checksum, true);
      localView.setUint32(18, data.length, true);
      localView.setUint32(22, data.length, true);
      localView.setUint16(26, name.length, true);
      local.set(name, 30);
      localParts.push(local, data);

      const central = new Uint8Array(46 + name.length);
      const centralView = new DataView(central.buffer);
      centralView.setUint32(0, 0x02014b50, true);
      centralView.setUint16(4, 20, true);
      centralView.setUint16(6, 20, true);
      centralView.setUint16(8, 0x0800, true);
      centralView.setUint16(10, 0, true);
      centralView.setUint16(12, stamp.time, true);
      centralView.setUint16(14, stamp.date, true);
      centralView.setUint32(16, checksum, true);
      centralView.setUint32(20, data.length, true);
      centralView.setUint32(24, data.length, true);
      centralView.setUint16(28, name.length, true);
      centralView.setUint32(42, localOffset, true);
      central.set(name, 46);
      centralParts.push(central);
      localOffset += local.length + data.length;
    });
    const centralOffset = localOffset;
    const centralSize = centralParts.reduce((sum, part) => sum + part.length, 0);
    const end = new Uint8Array(22);
    const endView = new DataView(end.buffer);
    endView.setUint32(0, 0x06054b50, true);
    endView.setUint16(8, entries.length, true);
    endView.setUint16(10, entries.length, true);
    endView.setUint32(12, centralSize, true);
    endView.setUint32(16, centralOffset, true);
    return joinBytes([...localParts, ...centralParts, end]);
  }

  function packageArtifacts(plan, artifacts, date) {
    const root = safeFileStem(`${safeFileStem(plan.document.name)} ${plan.formatLabel} export`);
    const manifest = {
      schema: "figureStudio.multiFileExport.v1",
      document: { id: plan.document.id, name: plan.document.name, kind: plan.document.kind },
      format: plan.format,
      scope: plan.scope,
      fileCount: artifacts.length,
      files: artifacts.map((artifact) => ({ filename: artifact.filename, bytes: artifact.size }))
    };
    const bytes = buildStoredZip([
      { path: `${root}/export.json`, bytes: bytesFromString(JSON.stringify(manifest, null, 2)) },
      ...artifacts.map((artifact) => ({ path: `${root}/${artifact.filename}`, bytes: artifact.bytes }))
    ], { date });
    return {
      filename: `${root}.zip`,
      format: "zip",
      mimeType: MIME_TYPES.zip,
      bytes,
      size: bytes.length,
      warnings: artifacts.flatMap((artifact) => artifact.warnings || [])
    };
  }

  function createBrowserDestination(browserRoot = typeof window !== "undefined" ? window : null) {
    return {
      kind: "browser",
      async downloadFile({ artifact }) {
        const documentRef = browserRoot?.document;
        const urlApi = browserRoot?.URL;
        if (!documentRef || !urlApi?.createObjectURL) {
          throw exportError("browser-download-unavailable", "This browser cannot start the requested file download.");
        }
        const blob = new Blob([artifact.bytes], { type: artifact.mimeType });
        const href = urlApi.createObjectURL(blob);
        const link = documentRef.createElement("a");
        link.href = href;
        link.download = artifact.filename;
        documentRef.body.appendChild(link);
        link.click();
        link.remove();
        browserRoot.setTimeout(() => urlApi.revokeObjectURL(href), 500);
        return { status: "downloaded", filename: artifact.filename };
      }
    };
  }

  function canceledStatus(plan) {
    return {
      schema: "figureStudio.exportStatus.v1",
      status: "cancelled",
      document: { id: plan.document.id, name: plan.document.name, kind: plan.document.kind },
      format: plan.format,
      scope: plan.scope,
      destination: null,
      message: `${plan.document.name} export was canceled. No file was created.`
    };
  }

  function completedStatus(plan, destination, artifacts, warnings) {
    const count = artifacts.length;
    const countText = count > 1 ? ` (${count} files${destination.packaged ? " in one package" : ""})` : "";
    let message;
    if (destination.kind === "native-file") {
      message = `${plan.document.name} exported as ${plan.formatLabel}${countText}. Saved to ${destination.path}.`;
    } else if (destination.kind === "native-folder") {
      message = `${plan.document.name} exported as ${plan.formatLabel} (${count} files). Saved to ${destination.path}.`;
    } else {
      message = `${plan.document.name} exported as ${plan.formatLabel}${countText}. Downloaded "${destination.filename}"; your browser controls its destination.`;
    }
    return {
      schema: "figureStudio.exportStatus.v1",
      status: "completed",
      document: { id: plan.document.id, name: plan.document.name, kind: plan.document.kind },
      format: plan.format,
      formatLabel: plan.formatLabel,
      scope: plan.scope,
      fileCount: count,
      destination,
      artifacts: artifacts.map((artifact) => ({ filename: artifact.filename, mimeType: artifact.mimeType, bytes: artifact.size })),
      warnings,
      message
    };
  }

  function deliveryEnvironment(options = {}) {
    const destination = options.destination;
    const inferred = typeof destination?.saveFile === "function" ? "native" : "browser";
    return String(options.environment || destination?.kind || inferred).toLowerCase();
  }

  function validateDeliveryChoice(plan, options = {}) {
    const requested = plan.requestedDelivery;
    if (!new Set(["auto", "file", "folder", "package"]).has(requested)) {
      throw exportError("delivery-unsupported", `The export destination choice "${requested}" is not supported.`);
    }
    const environment = deliveryEnvironment(options);
    const destination = options.destination;
    if (environment === "native" && !destination) {
      throw exportError("native-destination-unavailable", "The installed app could not open its native Export As destination. No browser download was substituted.");
    }
    if (plan.multiFile && requested === "file") {
      throw exportError("delivery-unsupported", "Choose a folder or one ZIP package for a multi-file export.");
    }
    if (!plan.multiFile && requested === "folder") {
      throw exportError("delivery-unsupported", "Choose a file destination for this single-file export.");
    }
    if (plan.multiFile && requested === "folder" && (environment !== "native" || typeof destination?.saveFiles !== "function")) {
      throw exportError("folder-destination-unavailable", "Folder export is not available in this workspace. Choose one ZIP package instead.");
    }
    return environment;
  }

  async function deliver(plan, artifacts, options, request) {
    const destination = options.destination || (deliveryEnvironment(options) === "browser" ? createBrowserDestination(options.browserRoot) : null);
    const environment = validateDeliveryChoice(plan, { ...options, destination });
    const requested = plan.requestedDelivery;
    const multi = artifacts.length > 1;
    const useFolder = multi
      && environment === "native"
      && typeof destination?.saveFiles === "function"
      && requested !== "package";
    if (useFolder) {
      const result = await destination.saveFiles({
        document: plan.document.source,
        documentInfo: plan.document,
        format: plan.format,
        artifacts,
        suggestedFolderName: safeFileStem(`${safeFileStem(plan.document.name)} ${plan.formatLabel} export`)
      });
      if (!result || result.status === "cancelled") return canceledStatus(plan);
      const path = String(result.directoryPath || result.path || "").trim();
      if (!path) throw exportError("native-destination-path-missing", "The native export destination did not report the selected folder, so Figure Tool cannot claim where the files were saved.");
      return completedStatus(plan, { kind: "native-folder", path, knownPath: true, fileCount: artifacts.length }, artifacts, artifacts.flatMap((artifact) => artifact.warnings));
    }
    const artifact = multi || requested === "package"
      ? packageArtifacts(plan, artifacts, request?.date)
      : artifacts[0];
    if (environment === "native") {
      if (typeof destination?.saveFile !== "function") {
        throw exportError("native-save-file-unavailable", "The installed app could not open a native file dialog for this export. No browser download was substituted.");
      }
      const result = await destination.saveFile({
        document: plan.document.source,
        documentInfo: plan.document,
        format: artifact.format,
        artifact,
        suggestedFilename: artifact.filename
      });
      if (!result || result.status === "cancelled") return canceledStatus(plan);
      const path = String(result.path || result.filePath || "").trim();
      if (!path) throw exportError("native-destination-path-missing", "The native export dialog did not report the selected file path, so Figure Tool cannot claim where the file was saved.");
      return completedStatus(plan, {
        kind: "native-file",
        path,
        filename: basename(path),
        knownPath: true,
        packaged: multi || requested === "package"
      }, artifacts, artifact.warnings || []);
    }
    if (typeof destination?.downloadFile !== "function") {
      throw exportError("browser-download-unavailable", "Browser export could not start a download.");
    }
    const result = await destination.downloadFile({
      document: plan.document.source,
      documentInfo: plan.document,
      format: artifact.format,
      artifact,
      suggestedFilename: artifact.filename
    });
    if (!result || result.status === "cancelled") return canceledStatus(plan);
    const filename = String(result.filename || artifact.filename);
    return completedStatus(plan, {
      kind: "browser-download",
      filename,
      path: null,
      knownPath: false,
      packaged: multi || requested === "package"
    }, artifacts, artifact.warnings || []);
  }

  function createExportEngine(options = {}) {
    const renderers = { ...(options.renderers || {}) };
    const getItems = options.getItems;
    return Object.freeze({
      version: VERSION,
      describe(document) {
        return describeDocument(document, {
          renderers,
          getItems,
          environment: options.environment,
          destination: options.destination
        });
      },
      plan(document, request) {
        return makePlan(document, request, { getItems });
      },
      async exportDocument(document, request = {}) {
        const plan = makePlan(document, request, { getItems });
        validateDeliveryChoice(plan, options);
        const artifacts = await renderPlan(plan, renderers);
        return deliver(plan, artifacts, { ...options, renderers }, request);
      }
    });
  }

  return Object.freeze({
    VERSION,
    DPI_PRESETS,
    FORMAT_CATALOG,
    MIME_TYPES,
    EXTENSIONS,
    RENDERER_KEYS,
    createExportEngine,
    createBrowserDestination,
    describeDocument,
    makePlan,
    encodeTiff,
    testing: Object.freeze({
      buildStoredZip,
      crc32,
      normalizeResolution,
      normalizeBackground,
      normalizeArtifact,
      validateArtifactSignature
    })
  });
});
