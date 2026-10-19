/*
 * Figure Tool PPTX v1 interchange.
 *
 * This module deliberately implements a small, offline OOXML boundary instead
 * of promising general PowerPoint fidelity. It has no runtime dependency on
 * npm, a repository checkout, a native executable, or a network service.
 *
 * Browser: window.FigureStudioPptxV1
 * Node QA: require("./pptx-v1.js")
 */
(function exposeFigureStudioPptxV1(root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  if (root) root.FigureStudioPptxV1 = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function createFigureStudioPptxV1() {
  "use strict";

  const VERSION = "1.0.0";
  const PRODUCT_VERSION = "1.0.0-beta.6";
  const MIME_TYPE = "application/vnd.openxmlformats-officedocument.presentationml.presentation";
  const EMU_PER_POINT = 12700;
  const POINTS_PER_INCH = 72;
  const CSS_PIXELS_PER_INCH = 96;
  const MAX_ZIP_ENTRIES = 4096;
  const MAX_ZIP_BYTES = 128 * 1024 * 1024;
  const MAX_ZIP_ENTRY_BYTES = 64 * 1024 * 1024;
  const MAX_UNCOMPRESSED_BYTES = 256 * 1024 * 1024;
  const REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships";
  const OFFICE_REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships";

  const COMPATIBILITY = deepFreeze({
    schema: "figureStudio.pptxCompatibility.v1",
    version: "pptx.v1",
    productVersion: PRODUCT_VERSION,
    direction: "Common scientific-deck PPTX interchange",
    googleSlides: "Use the exported PPTX, PDF, SVG, or PNG files. Direct cloud integration is not included.",
    fidelityClaim: "Bounded editable interchange; not universal PowerPoint or Google Slides round-trip fidelity.",
    supported: {
      document: ["slide order", "one uniform slide size", "plain speaker notes", "simple solid backgrounds from slide, layout, or master"],
      text: ["editable text boxes", "ordinary title/body placeholder geometry and text defaults", "theme major/minor Latin font families", "font family", "font size", "bold", "italic", "underline", "alignment", "solid text color", "supported run-level spans"],
      shapes: ["rectangle", "rounded rectangle", "ellipse", "triangle", "solid fill", "solid stroke", "editable groups of supported shapes, text, images, and straight connectors"],
      lines: ["straight lines", "straight connectors", "solid/dashed/dotted strokes", "basic arrowheads"],
      images: ["embedded PNG", "embedded JPEG", "embedded SVG"]
    },
    approximated: [
      "Per-slide Figure Tool geometry is scaled to the presentation's uniform slide size.",
      "Theme colors are resolved to solid RGB colors. Supported directly drawn master/layout artwork is copied onto each slide; master/layout editing is not preserved.",
      "Ordinary title/body placeholders become independent text. Direct fields retain cached text; date and slide-number fields no longer update automatically.",
      "Supported run-level text spans remain editable. Superscript, subscript, baseline shift, strike, highlight, and text effects are approximated with warnings.",
      "Gradient and pattern paints use the first supported solid color when available; otherwise they are omitted with a warning.",
      "Groups containing unsupported Figure Tool vector children are embedded as one editable-position SVG image.",
      "Legacy elbow and curved connectors are reduced to straight connectors. Native arrows or their containing groups use SVG images; their internal shapes, endpoints, and attachments are not independently editable."
    ],
    unsupported: [
      "SmartArt and diagrams",
      "charts and embedded workbooks",
      "tables",
      "audio and video",
      "animations and transitions",
      "macros, OLE objects, and embedded files",
      "3D models",
      "comments, collaboration metadata, and cloud links",
      "custom geometry/freeform PowerPoint paths",
      "theme, slide-master, and layout round-trip fidelity beyond simple copied artwork",
      "advanced typography, WordArt, equations, and text effects",
      "gradients, patterns, artistic effects, blend modes, and advanced transparency",
      "direct Google Slides cloud integration"
    ],
    warningPolicy: "Import and export return structured warnings. Unsupported content is never reported as editable or silently claimed as preserved."
  });

  const NAMED_COLORS = Object.freeze({
    black: "000000", white: "FFFFFF", red: "FF0000", green: "008000", blue: "0000FF",
    gray: "808080", grey: "808080", yellow: "FFFF00", orange: "FFA500", purple: "800080",
    transparent: ""
  });

  function deepFreeze(value) {
    if (!value || typeof value !== "object" || Object.isFrozen(value)) return value;
    Object.values(value).forEach(deepFreeze);
    return Object.freeze(value);
  }

  function finite(value, fallback = 0) {
    const number = Number(value);
    return Number.isFinite(number) ? number : fallback;
  }

  function clamp(value, minimum, maximum) {
    return Math.min(maximum, Math.max(minimum, finite(value, minimum)));
  }

  function toEmu(points) {
    return Math.max(0, Math.round(finite(points) * EMU_PER_POINT));
  }

  function fromEmu(value) {
    return finite(value) / EMU_PER_POINT;
  }

  function xmlEscape(value) {
    return String(value == null ? "" : value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&apos;");
  }

  function xmlDecode(value) {
    return String(value == null ? "" : value)
      .replace(/&#x([0-9a-f]+);/gi, (_, digits) => String.fromCodePoint(parseInt(digits, 16)))
      .replace(/&#([0-9]+);/g, (_, digits) => String.fromCodePoint(parseInt(digits, 10)))
      .replace(/&quot;/g, "\"")
      .replace(/&apos;/g, "'")
      .replace(/&gt;/g, ">")
      .replace(/&lt;/g, "<")
      .replace(/&amp;/g, "&");
  }

  function parseAttributes(source) {
    const result = {};
    String(source || "").replace(/([\w:.-]+)\s*=\s*(?:"([^"]*)"|'([^']*)')/g, (_, name, doubleValue, singleValue) => {
      result[name] = xmlDecode(doubleValue == null ? singleValue : doubleValue);
      return _;
    });
    return result;
  }

  function utf8Bytes(value) {
    return new TextEncoder().encode(String(value == null ? "" : value));
  }

  function bytesToText(value) {
    const bytes = value instanceof Uint8Array ? value : new Uint8Array(value || []);
    return new TextDecoder("utf-8").decode(bytes);
  }

  function concatBytes(parts) {
    const total = (parts || []).reduce((sum, part) => sum + part.length, 0);
    const output = new Uint8Array(total);
    let offset = 0;
    (parts || []).forEach((part) => {
      output.set(part, offset);
      offset += part.length;
    });
    return output;
  }

  function base64ToBytes(value) {
    const source = String(value || "").replace(/\s+/g, "");
    if (typeof atob === "function") {
      const binary = atob(source);
      const output = new Uint8Array(binary.length);
      for (let index = 0; index < binary.length; index += 1) output[index] = binary.charCodeAt(index);
      return output;
    }
    if (typeof Buffer !== "undefined") return new Uint8Array(Buffer.from(source, "base64"));
    throw new Error("Base64 decoding is unavailable in this runtime.");
  }

  function bytesToBase64(value) {
    const bytes = value instanceof Uint8Array ? value : new Uint8Array(value || []);
    if (typeof btoa === "function") {
      let binary = "";
      const size = 0x8000;
      for (let index = 0; index < bytes.length; index += size) {
        binary += String.fromCharCode(...bytes.subarray(index, index + size));
      }
      return btoa(binary);
    }
    if (typeof Buffer !== "undefined") return Buffer.from(bytes).toString("base64");
    throw new Error("Base64 encoding is unavailable in this runtime.");
  }

  function parseDataUrl(value) {
    const match = String(value || "").match(/^data:([^;,]+)?((?:;[^,]*)*?),(.*)$/s);
    if (!match) return null;
    const mediaType = String(match[1] || "application/octet-stream").toLowerCase();
    const base64 = /;base64(?:;|$)/i.test(match[2] || "");
    const bytes = base64 ? base64ToBytes(match[3]) : utf8Bytes(decodeURIComponent(match[3]));
    return { mediaType, bytes };
  }

  function intrinsicImageDimensions(bytes, mediaType) {
    const data = bytes instanceof Uint8Array ? bytes : new Uint8Array(bytes || []);
    const type = String(mediaType || "").toLowerCase();
    if (type === "image/png" && data.length >= 24
      && [137, 80, 78, 71, 13, 10, 26, 10].every((value, index) => data[index] === value)) {
      const width = ((data[16] << 24) | (data[17] << 16) | (data[18] << 8) | data[19]) >>> 0;
      const height = ((data[20] << 24) | (data[21] << 16) | (data[22] << 8) | data[23]) >>> 0;
      return width && height ? { width, height } : null;
    }
    if (type === "image/jpeg" && data.length >= 4 && data[0] === 0xFF && data[1] === 0xD8) {
      let offset = 2;
      while (offset + 9 < data.length) {
        if (data[offset] !== 0xFF) { offset += 1; continue; }
        while (data[offset] === 0xFF) offset += 1;
        const marker = data[offset++];
        if (marker === 0xD9 || marker === 0xDA) break;
        if (marker === 0x01 || (marker >= 0xD0 && marker <= 0xD7)) continue;
        if (offset + 2 > data.length) break;
        const length = data[offset] * 256 + data[offset + 1];
        if (length < 2 || offset + length > data.length) break;
        if ([0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF].includes(marker) && length >= 7) {
          const height = data[offset + 3] * 256 + data[offset + 4];
          const width = data[offset + 5] * 256 + data[offset + 6];
          return width && height ? { width, height } : null;
        }
        offset += length;
      }
    }
    if (type === "image/svg+xml") {
      const attributes = firstTagAttributes(bytesToText(data), "svg");
      const pixels = (value) => /^\d+(?:\.\d+)?(?:px)?$/i.test(String(value || "").trim()) ? Number.parseFloat(value) : 0;
      const width = pixels(attributes.width);
      const height = pixels(attributes.height);
      const box = String(attributes.viewBox || attributes.viewbox || "").trim().split(/[\s,]+/).map(Number);
      const boxWidth = box.length === 4 && box.every(Number.isFinite) ? box[2] : 0;
      const boxHeight = box.length === 4 && box.every(Number.isFinite) ? box[3] : 0;
      const resolvedWidth = width || boxWidth;
      const resolvedHeight = height || boxHeight;
      return resolvedWidth > 0 && resolvedHeight > 0 ? { width: resolvedWidth, height: resolvedHeight } : null;
    }
    return null;
  }

  async function inputBytes(input) {
    if (input instanceof Uint8Array) return input;
    if (input instanceof ArrayBuffer) return new Uint8Array(input);
    if (ArrayBuffer.isView(input)) return new Uint8Array(input.buffer, input.byteOffset, input.byteLength);
    if (input && typeof input.arrayBuffer === "function") return new Uint8Array(await input.arrayBuffer());
    throw new TypeError("Expected a File, Blob, ArrayBuffer, or Uint8Array containing a PPTX package.");
  }

  function warningCollector(seed = []) {
    const rows = Array.isArray(seed) ? seed : [];
    const seen = new Set(rows.map((item) => JSON.stringify(item)));
    return {
      rows,
      add(code, message, context = {}) {
        const warning = {
          code: String(code || "pptx-warning"),
          message: String(message || "PPTX content needs review."),
          severity: context.severity || "warning",
          action: context.action || "review",
          ...Object.fromEntries(Object.entries(context).filter(([key]) => !["severity", "action"].includes(key)))
        };
        const key = JSON.stringify(warning);
        if (!seen.has(key)) {
          seen.add(key);
          rows.push(warning);
        }
        return warning;
      }
    };
  }

  function normalizeHexColor(value, fallback = "000000") {
    if (value && typeof value === "object") return normalizeHexColor(value.color || value.value, fallback);
    let source = String(value == null ? "" : value).trim().toLowerCase();
    if (!source || source === "none" || source === "transparent") return "";
    if (NAMED_COLORS[source] != null) return NAMED_COLORS[source];
    if (source.startsWith("#")) source = source.slice(1);
    if (/^[0-9a-f]{3}$/.test(source)) return source.split("").map((character) => character + character).join("").toUpperCase();
    if (/^[0-9a-f]{6}$/.test(source)) return source.toUpperCase();
    if (/^[0-9a-f]{8}$/.test(source)) return source.slice(0, 6).toUpperCase();
    const rgb = source.match(/^rgba?\(\s*([\d.]+)\s*[, ]\s*([\d.]+)\s*[, ]\s*([\d.]+)/);
    if (rgb) return rgb.slice(1, 4).map((entry) => clamp(Math.round(Number(entry)), 0, 255).toString(16).padStart(2, "0")).join("").toUpperCase();
    return String(fallback || "000000").replace(/^#/, "").slice(0, 6).toUpperCase();
  }

  function paintAlpha(value) {
    const source = String(value == null ? "" : value).trim().toLowerCase();
    if (!source || source === "none" || source === "transparent") return 0;
    const rgba = source.match(/^rgba\(\s*[\d.]+\s*[, ]\s*[\d.]+\s*[, ]\s*[\d.]+\s*[,/]\s*([\d.]+)\s*\)$/);
    if (rgba) return clamp(finite(rgba[1], 1), 0, 1);
    if (/^#[0-9a-f]{8}$/.test(source)) return parseInt(source.slice(7, 9), 16) / 255;
    return 1;
  }

  function paintKind(value) {
    if (!value || typeof value !== "object") return "solid";
    const type = String(value.type || value.kind || value.gradientType || value.paintKind || "").toLowerCase();
    if (type.includes("gradient") || Array.isArray(value.colorStops) || (value.colorStops && typeof value.colorStops === "object")) return "gradient";
    if (type.includes("pattern") || value.source || value.repeat) return "pattern";
    return "complex";
  }

  function paintStops(value) {
    if (!value || typeof value !== "object") return [];
    const raw = Array.isArray(value.colorStops) ? value.colorStops : Object.values(value.colorStops || {});
    return raw.filter((stop) => stop && typeof stop === "object" && stop.color).sort((left, right) => finite(left.offset) - finite(right.offset));
  }

  function solidPaintCandidate(value, fallback = "") {
    if (typeof value === "string") return value;
    if (!value || typeof value !== "object") return fallback;
    if (typeof value.color === "string") return value.color;
    if (typeof value.value === "string") return value.value;
    const first = paintStops(value)[0];
    return first?.color || fallback;
  }

  function resolveSolidPaint(value, warnings, context, role, fallback = "") {
    if (typeof value === "string" || value == null) return value || fallback;
    const kind = paintKind(value);
    const candidate = solidPaintCandidate(value, fallback);
    const code = `${kind}-paint-${candidate ? "flattened" : "omitted"}`;
    warnings.add(
      code,
      candidate
        ? `A ${kind} ${role} was reduced to its first supported solid color.`
        : `A ${kind} ${role} could not be represented and was omitted.`,
      { ...context, paintRole: role, action: candidate ? "flattened" : "omitted" }
    );
    return candidate;
  }

  function colorXml(value, opacity = 1) {
    const color = normalizeHexColor(value, "000000");
    if (!color) return "<a:noFill/>";
    const alpha = clamp(opacity, 0, 1);
    return `<a:solidFill><a:srgbClr val="${color}">${alpha < 0.999 ? `<a:alpha val="${Math.round(alpha * 100000)}"/>` : ""}</a:srgbClr></a:solidFill>`;
  }

  function normalizeArrow(value) {
    const source = String(value || "none").toLowerCase();
    if (["triangle", "arrow", "stealth"].includes(source)) return source === "arrow" ? "triangle" : source;
    if (["diamond", "oval", "dot"].includes(source)) return source === "dot" ? "oval" : source;
    return "none";
  }

  const PPTX_CONNECTOR_SITES = deepFreeze({
    rect: { indexByPort: { top: 0, left: 1, bottom: 2, right: 3 }, portByIndex: { 0: "top", 1: "left", 2: "bottom", 3: "right" } },
    roundRect: { indexByPort: { top: 0, left: 1, bottom: 2, right: 3 }, portByIndex: { 0: "top", 1: "left", 2: "bottom", 3: "right" } },
    ellipse: { indexByPort: { top: 0, left: 2, bottom: 4, right: 6 }, portByIndex: { 0: "top", 2: "left", 4: "bottom", 6: "right" } },
    triangle: { indexByPort: { top: 0, bottom: 3 }, portByIndex: { 0: "top", 3: "bottom" } }
  });

  function pptxConnectorPortForIndex(shape, value) {
    const index = String(value == null ? "" : value).trim();
    return PPTX_CONNECTOR_SITES[shape]?.portByIndex?.[index] || "";
  }

  function pptxConnectorIndexForPort(shape, value) {
    const role = String(value || "").toLowerCase();
    return PPTX_CONNECTOR_SITES[shape]?.indexByPort?.[role];
  }

  function stablePptxObjectId(value, fallback = "pptx-object") {
    const source = String(value || fallback || "pptx-object").trim() || "pptx-object";
    const safe = source.replace(/[^A-Za-z0-9_-]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 80);
    return safe || "pptx-object";
  }

  function fallbackPptxObjectId(kind = "object") {
    const randomPart = Math.random().toString(36).slice(2, 10);
    return stablePptxObjectId(`pptx-${kind || "object"}-${Date.now().toString(36)}-${randomPart}`, "pptx-object");
  }

  function arrowXml(tag, value) {
    const type = normalizeArrow(value);
    return `<a:${tag} type="${type}"${type === "none" ? "" : " w=\"med\" len=\"med\""}/>`;
  }

  function dashXml(value) {
    const source = String(value || "solid").toLowerCase();
    const mapped = source === "dotted" || source === "dot" ? "sysDot"
      : source === "dash-dot" ? "dashDot"
        : source === "dashed" || source === "dash" ? "dash" : "solid";
    return `<a:prstDash val="${mapped}"/>`;
  }

  function lineXml(object = {}) {
    const color = normalizeHexColor(object.stroke, "000000");
    if (!color || finite(object.strokeWidth, 1) <= 0) return "<a:ln><a:noFill/></a:ln>";
    const width = Math.max(1, toEmu(finite(object.strokeWidth, 1)));
    return `<a:ln w="${width}">${colorXml(color, object.opacity == null ? 1 : object.opacity)}${dashXml(object.dash || object.lineDash)}${arrowXml("headEnd", object.startArrow || object.arrowStart)}${arrowXml("tailEnd", object.endArrow || object.arrowEnd || object.arrowHead)}</a:ln>`;
  }

  const CRC_TABLE = (() => {
    const table = new Uint32Array(256);
    for (let index = 0; index < 256; index += 1) {
      let crc = index;
      for (let bit = 0; bit < 8; bit += 1) crc = (crc & 1) ? (0xedb88320 ^ (crc >>> 1)) : (crc >>> 1);
      table[index] = crc >>> 0;
    }
    return table;
  })();

  function crc32(bytes) {
    let crc = 0xffffffff;
    for (let index = 0; index < bytes.length; index += 1) crc = CRC_TABLE[(crc ^ bytes[index]) & 0xff] ^ (crc >>> 8);
    return (crc ^ 0xffffffff) >>> 0;
  }

  function zipRecord(signature, size) {
    const bytes = new Uint8Array(size);
    const view = new DataView(bytes.buffer);
    view.setUint32(0, signature, true);
    return { bytes, view };
  }

  function dosDateTime(date) {
    const value = date instanceof Date && !Number.isNaN(date.valueOf()) ? date : new Date();
    const year = clamp(value.getUTCFullYear(), 1980, 2107);
    return {
      time: (value.getUTCHours() << 11) | (value.getUTCMinutes() << 5) | Math.floor(value.getUTCSeconds() / 2),
      date: ((year - 1980) << 9) | ((value.getUTCMonth() + 1) << 5) | value.getUTCDate()
    };
  }

  function buildStoredZip(entries, options = {}) {
    const localParts = [];
    const centralParts = [];
    const stamp = dosDateTime(options.date);
    let offset = 0;
    (entries || []).forEach((entry) => {
      const path = String(entry.path || "").replace(/\\/g, "/").replace(/^\/+/, "");
      if (!path || path.includes("../")) throw new Error(`Unsafe PPTX package path: ${path || "(empty)"}`);
      const name = utf8Bytes(path);
      const data = entry.bytes instanceof Uint8Array ? entry.bytes : utf8Bytes(entry.bytes || "");
      const crc = crc32(data);
      const local = zipRecord(0x04034b50, 30 + name.length);
      local.view.setUint16(4, 20, true);
      local.view.setUint16(6, 0x0800, true);
      local.view.setUint16(8, 0, true);
      local.view.setUint16(10, stamp.time, true);
      local.view.setUint16(12, stamp.date, true);
      local.view.setUint32(14, crc, true);
      local.view.setUint32(18, data.length, true);
      local.view.setUint32(22, data.length, true);
      local.view.setUint16(26, name.length, true);
      local.bytes.set(name, 30);
      localParts.push(local.bytes, data);

      const central = zipRecord(0x02014b50, 46 + name.length);
      central.view.setUint16(4, 20, true);
      central.view.setUint16(6, 20, true);
      central.view.setUint16(8, 0x0800, true);
      central.view.setUint16(10, 0, true);
      central.view.setUint16(12, stamp.time, true);
      central.view.setUint16(14, stamp.date, true);
      central.view.setUint32(16, crc, true);
      central.view.setUint32(20, data.length, true);
      central.view.setUint32(24, data.length, true);
      central.view.setUint16(28, name.length, true);
      central.view.setUint32(42, offset, true);
      central.bytes.set(name, 46);
      centralParts.push(central.bytes);
      offset += local.bytes.length + data.length;
    });
    const centralOffset = offset;
    const centralSize = centralParts.reduce((sum, bytes) => sum + bytes.length, 0);
    const end = zipRecord(0x06054b50, 22);
    end.view.setUint16(8, centralParts.length, true);
    end.view.setUint16(10, centralParts.length, true);
    end.view.setUint32(12, centralSize, true);
    end.view.setUint32(16, centralOffset, true);
    return concatBytes([...localParts, ...centralParts, end.bytes]);
  }

  function findEndOfCentralDirectory(view) {
    const minimum = Math.max(0, view.byteLength - 22 - 65536);
    for (let offset = view.byteLength - 22; offset >= minimum; offset -= 1) {
      if (view.getUint32(offset, true) === 0x06054b50) return offset;
    }
    return -1;
  }

  async function inflateRaw(bytes, expectedSize, options, path, maxOutputBytes) {
    if (typeof options.inflateRaw === "function") {
      const result = await options.inflateRaw(bytes, expectedSize, path, maxOutputBytes);
      const output = result instanceof Uint8Array ? result : new Uint8Array(result || []);
      if (output.length > maxOutputBytes) throw new Error(`Expanded PPTX entry exceeds the safe import budget: ${path}.`);
      return output;
    }
    if (typeof DecompressionStream === "function") {
      const stream = new Blob([bytes]).stream().pipeThrough(new DecompressionStream("deflate-raw"));
      const reader = stream.getReader();
      const chunks = [];
      let total = 0;
      try {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          const chunk = value instanceof Uint8Array ? value : new Uint8Array(value || []);
          total += chunk.length;
          if (total > maxOutputBytes) {
            await reader.cancel("Figure Tool PPTX import budget exceeded.");
            throw new Error(`Expanded PPTX entry exceeds the safe import budget: ${path}.`);
          }
          chunks.push(chunk);
        }
      } finally {
        reader.releaseLock();
      }
      return concatBytes(chunks);
    }
    throw new Error(`Compressed PPTX entry ${path} cannot be opened because raw DEFLATE support is unavailable.`);
  }

  async function readZipEntries(input, options = {}) {
    const maxPackageBytes = Math.min(MAX_ZIP_BYTES, Math.max(1, finite(options.maxPackageBytes, MAX_ZIP_BYTES)));
    if (finite(input?.size, 0) > maxPackageBytes || finite(input?.byteLength, 0) > maxPackageBytes) {
      throw new Error("PPTX package is larger than the safe compressed import budget.");
    }
    const bytes = await inputBytes(input);
    if (bytes.length > maxPackageBytes) throw new Error("PPTX package is larger than the safe compressed import budget.");
    const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
    const endOffset = findEndOfCentralDirectory(view);
    if (endOffset < 0) throw new Error("This file is not a readable PPTX/ZIP package.");
    if (view.getUint16(endOffset + 8, true) === 0xffff || view.getUint32(endOffset + 12, true) === 0xffffffff) {
      throw new Error("ZIP64 PPTX packages are outside the PPTX v1 import subset.");
    }
    const count = view.getUint16(endOffset + 10, true);
    if (count > MAX_ZIP_ENTRIES) throw new Error(`PPTX package contains too many entries (${count}).`);
    const centralOffset = view.getUint32(endOffset + 16, true);
    const maxExpanded = Math.min(MAX_UNCOMPRESSED_BYTES, Math.max(1, finite(options.maxUncompressedBytes, MAX_UNCOMPRESSED_BYTES)));
    const maxEntryBytes = Math.min(MAX_ZIP_ENTRY_BYTES, maxExpanded, Math.max(1, finite(options.maxEntryBytes, MAX_ZIP_ENTRY_BYTES)));
    const centralSize = view.getUint32(endOffset + 12, true);
    if (centralOffset + centralSize > endOffset) throw new Error("Invalid PPTX ZIP central-directory bounds.");
    const descriptors = [];
    let offset = centralOffset;
    let declaredExpanded = 0;
    for (let index = 0; index < count; index += 1) {
      if (offset + 46 > view.byteLength || view.getUint32(offset, true) !== 0x02014b50) throw new Error("Invalid PPTX ZIP central directory.");
      const flags = view.getUint16(offset + 8, true);
      const method = view.getUint16(offset + 10, true);
      const compressedSize = view.getUint32(offset + 20, true);
      const uncompressedSize = view.getUint32(offset + 24, true);
      const nameLength = view.getUint16(offset + 28, true);
      const extraLength = view.getUint16(offset + 30, true);
      const commentLength = view.getUint16(offset + 32, true);
      const localOffset = view.getUint32(offset + 42, true);
      const nextOffset = offset + 46 + nameLength + extraLength + commentLength;
      if (nextOffset > view.byteLength || nextOffset > centralOffset + centralSize) throw new Error("Invalid PPTX ZIP central-directory entry bounds.");
      const path = bytesToText(bytes.subarray(offset + 46, offset + 46 + nameLength)).replace(/\\/g, "/");
      if (!path || path.startsWith("/") || path.split("/").includes("..")) throw new Error(`Unsafe path in PPTX package: ${path || "(empty)"}`);
      if (flags & 0x0001) throw new Error(`Encrypted PPTX entry is unsupported: ${path}`);
      if (uncompressedSize > maxEntryBytes) throw new Error(`PPTX entry is larger than the safe per-entry import budget: ${path}.`);
      declaredExpanded += uncompressedSize;
      if (declaredExpanded > maxExpanded) throw new Error("PPTX package is larger than the safe declared import budget.");
      if (localOffset + 30 > view.byteLength || view.getUint32(localOffset, true) !== 0x04034b50) throw new Error(`Invalid local ZIP header for ${path}.`);
      const localNameLength = view.getUint16(localOffset + 26, true);
      const localExtraLength = view.getUint16(localOffset + 28, true);
      const start = localOffset + 30 + localNameLength + localExtraLength;
      if (start > view.byteLength || start + compressedSize > view.byteLength) throw new Error(`Invalid compressed-data bounds for ${path}.`);
      descriptors.push({ path, method, compressedSize, uncompressedSize, start });
      offset = nextOffset;
    }
    if (offset !== centralOffset + centralSize) throw new Error("Invalid PPTX ZIP central-directory size.");

    const entries = [];
    let expanded = 0;
    for (const descriptor of descriptors) {
      const { path, method, compressedSize, uncompressedSize, start } = descriptor;
      const compressed = bytes.subarray(start, start + compressedSize);
      let data;
      const remainingBudget = Math.min(maxEntryBytes, maxExpanded - expanded);
      if (method === 0) {
        if (compressedSize !== uncompressedSize || compressedSize > remainingBudget) throw new Error(`Stored PPTX entry has an invalid or unsafe size: ${path}.`);
        data = new Uint8Array(compressed);
      } else if (method === 8) data = await inflateRaw(compressed, uncompressedSize, options, path, Math.min(remainingBudget, uncompressedSize));
      else throw new Error(`Unsupported ZIP compression method ${method} for ${path}.`);
      if (data.length !== uncompressedSize) throw new Error(`Expanded size mismatch for ${path}.`);
      expanded += data.length;
      if (expanded > maxExpanded) throw new Error("PPTX package is larger than the safe import budget.");
      entries.push({ path, bytes: data, method, compressedSize, uncompressedSize: data.length });
    }
    return entries.filter((entry) => !entry.path.endsWith("/"));
  }

  function normalizePartPath(sourcePart, target) {
    const raw = String(target || "").replace(/\\/g, "/");
    if (raw.startsWith("/")) return raw.replace(/^\/+/, "");
    const pieces = String(sourcePart || "").split("/");
    pieces.pop();
    raw.split("/").forEach((piece) => {
      if (!piece || piece === ".") return;
      if (piece === "..") pieces.pop();
      else pieces.push(piece);
    });
    return pieces.join("/");
  }

  function relationshipsFromXml(xml, sourcePart) {
    const relationships = new Map();
    const expression = /<(?:\w+:)?Relationship\b([^>]*?)(?:\/>|>[\s\S]*?<\/(?:\w+:)?Relationship>)/gi;
    let match;
    while ((match = expression.exec(String(xml || "")))) {
      const attributes = parseAttributes(match[1]);
      const id = attributes.Id || attributes.ID || attributes.id;
      if (!id) continue;
      relationships.set(id, {
        id,
        type: attributes.Type || "",
        target: attributes.TargetMode === "External" ? attributes.Target || "" : normalizePartPath(sourcePart, attributes.Target || ""),
        external: attributes.TargetMode === "External"
      });
    }
    return relationships;
  }

  function relationshipPartPath(sourcePart) {
    const parts = String(sourcePart || "").split("/");
    const filename = parts.pop();
    return [...parts, "_rels", `${filename}.rels`].join("/");
  }

  function xmlEntryMap(entries) {
    return new Map((entries || []).map((entry) => [entry.path, entry]));
  }

  function firstTagAttributes(xml, localName) {
    const expression = new RegExp(`<(?:\\w+:)?${localName}\\b([^>]*)>`, "i");
    const selfClosing = new RegExp(`<(?:\\w+:)?${localName}\\b([^>]*)\\/>`, "i");
    const match = String(xml || "").match(expression) || String(xml || "").match(selfClosing);
    return match ? parseAttributes(match[1]) : {};
  }

  function tagBlocks(xml, localName) {
    const expression = new RegExp(`<((?:\\w+:)?${localName})\\b[^>]*>[\\s\\S]*?<\\/\\1>`, "gi");
    return String(xml || "").match(expression) || [];
  }

  function relationshipXml(relationships) {
    return `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<Relationships xmlns="${REL_NS}">${(relationships || []).map((item) => `<Relationship Id="${xmlEscape(item.id)}" Type="${xmlEscape(item.type)}" Target="${xmlEscape(item.target)}"${item.external ? " TargetMode=\"External\"" : ""}/>`).join("")}</Relationships>`;
  }

  function objectBounds(object = {}) {
    const width = Math.max(0.01, finite(object.width, finite(object.w, 1)));
    const height = Math.max(0.01, finite(object.height, finite(object.h, 1)));
    return {
      x: finite(object.x, finite(object.left, 0)),
      y: finite(object.y, finite(object.top, 0)),
      width,
      height,
      rotation: finite(object.rotation, finite(object.angle, 0))
    };
  }

  function transformXml(bounds, options = {}) {
    const rotation = Math.round(finite(bounds.rotation) * 60000);
    const flipH = options.flipH ? " flipH=\"1\"" : "";
    const flipV = options.flipV ? " flipV=\"1\"" : "";
    const positionEmu = options.nativeSvgRoot === true ? (value) => Math.round(finite(value) * EMU_PER_POINT) : toEmu;
    return `<a:xfrm${rotation ? ` rot="${rotation}"` : ""}${flipH}${flipV}><a:off x="${positionEmu(bounds.x)}" y="${positionEmu(bounds.y)}"/><a:ext cx="${toEmu(bounds.width)}" cy="${toEmu(bounds.height)}"/></a:xfrm>`;
  }

  function groupTransformXml(object) {
    const bounds = objectBounds(object);
    const coordinateWidth = Math.max(0.01, finite(object.coordinateWidth, bounds.width));
    const coordinateHeight = Math.max(0.01, finite(object.coordinateHeight, bounds.height));
    const rotation = Math.round(finite(bounds.rotation) * 60000);
    const flipH = object.flipH ? ' flipH="1"' : "";
    const flipV = object.flipV ? ' flipV="1"' : "";
    return `<a:xfrm${rotation ? ` rot="${rotation}"` : ""}${flipH}${flipV}><a:off x="${toEmu(bounds.x)}" y="${toEmu(bounds.y)}"/><a:ext cx="${toEmu(bounds.width)}" cy="${toEmu(bounds.height)}"/><a:chOff x="0" y="0"/><a:chExt cx="${toEmu(coordinateWidth)}" cy="${toEmu(coordinateHeight)}"/></a:xfrm>`;
  }

  function styleBold(value) {
    return value === true || String(value || "").toLowerCase() === "bold" || String(value || "") === "700" || Number(value) >= 600;
  }

  function pptxTextRunStyle(base = {}, override = {}) {
    const merged = { ...base, ...override };
    const color = normalizeHexColor(override.color ?? override.fill ?? merged.color ?? merged.fill ?? base.color ?? base.fill, "000000") || "000000";
    const size = clamp(Math.round(finite(override.fontSize ?? merged.fontSize, finite(base.fontSize, 18)) * 100), 100, 40000);
    const family = String(override.fontFamily ?? merged.fontFamily ?? base.fontFamily ?? "Arial").split(",")[0].replace(/["']/g, "").trim() || "Arial";
    const boldValue = override.bold ?? override.fontWeight ?? merged.bold ?? merged.fontWeight;
    const italicValue = override.italic ?? override.fontStyle ?? merged.italic ?? merged.fontStyle;
    const underlineValue = override.underline ?? merged.underline;
    const strikeValue = override.linethrough ?? override.strike ?? merged.linethrough ?? merged.strike;
    return {
      color,
      size,
      family,
      bold: styleBold(boldValue),
      italic: italicValue === true || italicValue === "italic",
      underline: underlineValue === true || (underlineValue && underlineValue !== "none"),
      strike: strikeValue === true || strikeValue === "sngStrike"
    };
  }

  function textRunPropertiesXml(style) {
    return `<a:rPr lang="en-US" sz="${style.size}" b="${style.bold ? "1" : "0"}" i="${style.italic ? "1" : "0"}" u="${style.underline ? "sng" : "none"}" strike="${style.strike ? "sngStrike" : "noStrike"}">${colorXml(style.color)}<a:latin typeface="${xmlEscape(style.family)}"/></a:rPr>`;
  }

  function lineStyleAt(style = {}, lineIndex = 0, charIndex = 0, globalIndex = charIndex) {
    if (Array.isArray(style.styles)) {
      const range = style.styles.find((entry) => entry && Number(entry.start) <= globalIndex && globalIndex < Number(entry.end));
      return range?.style || null;
    }
    const line = style.styles?.[lineIndex] || style.styles?.[String(lineIndex)] || {};
    return line?.[charIndex] || line?.[String(charIndex)] || null;
  }

  function textGraphemes(value) {
    const text = String(value == null ? "" : value);
    if (typeof Intl !== "undefined" && typeof Intl.Segmenter === "function") {
      return [...new Intl.Segmenter(undefined, { granularity: "grapheme" }).segment(text)].map((segment) => segment.segment);
    }
    return Array.from(text);
  }

  function lineRunsForPptx(line, lineIndex, style = {}, globalOffset = 0) {
    const graphemes = textGraphemes(line);
    if (!graphemes.length) return [{ text: "", style: pptxTextRunStyle(style) }];
    const runs = [];
    let currentKey = "";
    let currentStyle = null;
    let currentText = "";
    for (let charIndex = 0; charIndex < graphemes.length; charIndex += 1) {
      const override = lineStyleAt(style, lineIndex, charIndex, globalOffset + charIndex) || {};
      const runStyle = pptxTextRunStyle(style, override);
      const key = JSON.stringify(runStyle);
      if (!currentText || key === currentKey) {
        currentText += graphemes[charIndex];
        currentKey = key;
        currentStyle = runStyle;
      } else {
        runs.push({ text: currentText, style: currentStyle });
        currentText = graphemes[charIndex];
        currentKey = key;
        currentStyle = runStyle;
      }
    }
    if (currentText) runs.push({ text: currentText, style: currentStyle || pptxTextRunStyle(style) });
    return runs;
  }

  function textParagraphXml(text, style = {}) {
    const baseStyle = pptxTextRunStyle(style);
    const align = { center: "ctr", right: "r", justify: "just", left: "l" }[String(style.align || style.textAlign || "left").toLowerCase()] || "l";
    const paragraphs = String(text == null ? "" : text).split(/\r?\n/);
    let globalOffset = 0;
    return paragraphs.map((line, lineIndex) => {
      const paragraph = style.paragraphLayout?.paragraphs?.[lineIndex];
      const paragraphAlign = { center: "ctr", right: "r", justify: "just", left: "l" }[paragraph?.align] || align;
      const attributes = paragraph ? ` lvl="${clamp(Math.trunc(finite(paragraph.level)), 0, 8)}" marL="${toEmu(paragraph.marginLeft)}" marR="${toEmu(paragraph.marginRight)}" indent="${Math.round(finite(paragraph.indent) * EMU_PER_POINT)}"` : "";
      const bullet = paragraph?.bullet;
      const bulletXml = bullet?.type === "bullet" ? `<a:buChar char="${xmlEscape(bullet.char || "•")}"/>` : bullet?.type === "number" ? `<a:buAutoNum type="${xmlEscape(bullet.autoType || "arabicPeriod")}"${bullet.startAt ? ` startAt="${bullet.startAt}"` : ""}/>` : "<a:buNone/>";
      const runs = lineRunsForPptx(line, lineIndex, style, globalOffset).map((run) => `<a:r>${textRunPropertiesXml(run.style)}<a:t${/^\s|\s$/.test(run.text) ? " xml:space=\"preserve\"" : ""}>${xmlEscape(run.text)}</a:t></a:r>`).join("");
      globalOffset += textGraphemes(line).length;
      return `<a:p><a:pPr algn="${paragraphAlign}"${attributes}>${bulletXml}</a:pPr>${runs}<a:endParaRPr lang="en-US" sz="${baseStyle.size}"/></a:p>`;
    }).join("");
  }

  function textBodyXml(text, style = {}) {
    const vertical = style.verticalAlign === "middle" ? "ctr" : style.verticalAlign === "bottom" ? "b" : "t";
    const wrap = String(style.wrap || "square").toLowerCase() === "none" ? "none" : "square";
    const overflow = wrap === "none" ? ' horzOverflow="overflow" vertOverflow="overflow"' : "";
    const layout = style.paragraphLayout;
    const insets = layout?.insets || {};
    const fit = layout?.autoFit === "normal" ? `<a:normAutofit fontScale="${Math.round(finite(layout.fontScale, 1) * 100000)}" lnSpcReduction="${Math.round(finite(layout.lineSpaceReduction) * 100000)}"/>` : layout?.autoFit === "shape" ? "<a:spAutoFit/>" : "<a:noAutofit/>";
    return `<p:txBody><a:bodyPr wrap="${layout?.wrap || wrap}"${overflow} anchor="${vertical}" lIns="${toEmu(insets.left)}" tIns="${toEmu(insets.top)}" rIns="${toEmu(insets.right)}" bIns="${toEmu(insets.bottom)}">${fit}</a:bodyPr><a:lstStyle/>${textParagraphXml(text, style)}</p:txBody>`;
  }

  function pptxStableIdentityAttribute(object) {
    const identity = String(object?.sourceId || object?.id || "");
    return /^pptx-[A-Za-z0-9_-]+$/.test(identity) ? ` title="figureStudio:id=${xmlEscape(identity)}"` : "";
  }

  function textShapeXml(object, id, name) {
    const bounds = objectBounds(object);
    return `<p:sp><p:nvSpPr><p:cNvPr id="${id}" name="${xmlEscape(name)}"${pptxStableIdentityAttribute(object)}/><p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr><p:spPr>${transformXml(bounds, object)}<a:prstGeom prst="rect"><a:avLst/></a:prstGeom><a:noFill/><a:ln><a:noFill/></a:ln></p:spPr>${textBodyXml(object.text, object)}</p:sp>`;
  }

  function shapeShapeXml(object, id, name) {
    const shape = { rect: "rect", rectangle: "rect", roundrect: "roundRect", roundedrectangle: "roundRect", ellipse: "ellipse", circle: "ellipse", triangle: "triangle" }[String(object.shape || object.kind || "rect").replace(/[\s_-]+/g, "").toLowerCase()] || "rect";
    const bounds = objectBounds(object);
    return `<p:sp><p:nvSpPr><p:cNvPr id="${id}" name="${xmlEscape(name)}"${pptxStableIdentityAttribute(object)}/><p:cNvSpPr/><p:nvPr/></p:nvSpPr><p:spPr>${transformXml(bounds, object)}<a:prstGeom prst="${shape}"><a:avLst/></a:prstGeom>${colorXml(object.fill, object.opacity == null ? 1 : object.opacity)}${lineXml(object)}</p:spPr>${object.text != null && String(object.text) !== "" ? textBodyXml(object.text, object.textStyle || object) : ""}</p:sp>`;
  }

  function connectorShapeXml(object, id, name, shapeIdByObjectId = new Map(), warnings = warningCollector(), context = {}) {
    const x1 = finite(object.x1, finite(object.x, 0));
    const y1 = finite(object.y1, finite(object.y, 0));
    const x2 = finite(object.x2, x1 + finite(object.width, 1));
    const y2 = finite(object.y2, y1 + finite(object.height, 0));
    const bounds = { x: Math.min(x1, x2), y: Math.min(y1, y2), width: Math.max(0.01, Math.abs(x2 - x1)), height: Math.max(0.01, Math.abs(y2 - y1)), rotation: 0 };
    const connectionXml = (endpoint, tag, fallbackIndex) => {
      const objectId = String(endpoint?.objectId || "");
      if (!objectId) return "";
      const target = shapeIdByObjectId.get(objectId);
      if (!target) {
        warnings.add("connector-attachment-unresolved", "A connector attachment target was not available in the PPTX editable subset, so the connector was exported with its visible endpoint geometry only.", { ...context, endpoint: tag === "stCxn" ? "start" : "end", targetObjectId: objectId, action: "approximated" });
        return "";
      }
      if (target.unsupportedConnectionTransform) {
        warnings.add("connector-attachment-transform-unsupported", "A connector endpoint targeted a flipped or rotated shape. Figure Tool exported the connector with visible geometry only because PPTX v1 does not remap transformed connection sites.", { ...context, endpoint: tag === "stCxn" ? "start" : "end", targetObjectId: objectId, targetShape: target.shape, action: "approximated" });
        return "";
      }
      const index = pptxConnectorIndexForPort(target.shape, endpoint.anchor);
      if (index == null) {
        warnings.add("connector-attachment-site-unsupported", "A connector endpoint used a Figure Tool port that does not map to the target shape's supported PowerPoint connection sites, so the endpoint was exported with visible geometry only.", { ...context, endpoint: tag === "stCxn" ? "start" : "end", targetObjectId: objectId, targetShape: target.shape, anchor: endpoint.anchor || "", action: "approximated" });
        return "";
      }
      return `<a:${tag} id="${target.shapeId}" idx="${index}"/>`;
    };
    const meta = object.smartConnectorMeta || object.connectorMeta || {};
    const connectorLocks = `${connectionXml(meta.start, "stCxn", 1)}${connectionXml(meta.end, "endCxn", 3)}`;
    return `<p:cxnSp><p:nvCxnSpPr><p:cNvPr id="${id}" name="${xmlEscape(name)}"${pptxStableIdentityAttribute(object)}/><p:cNvCxnSpPr>${connectorLocks}</p:cNvCxnSpPr><p:nvPr/></p:nvCxnSpPr><p:spPr>${transformXml(bounds, { flipH: x2 < x1, flipV: y2 < y1 })}<a:prstGeom prst="line"><a:avLst/></a:prstGeom>${lineXml(object)}</p:spPr></p:cxnSp>`;
  }

  function pictureShapeXml(object, id, name, relationshipId) {
    const bounds = objectBounds(object);
    return `<p:pic><p:nvPicPr><p:cNvPr id="${id}" name="${xmlEscape(name)}" descr="${xmlEscape(object.alt || object.description || "")}"${pptxStableIdentityAttribute(object)}/><p:cNvPicPr><a:picLocks noChangeAspect="1"/></p:cNvPicPr><p:nvPr/></p:nvPicPr><p:blipFill><a:blip r:embed="${xmlEscape(relationshipId)}"/><a:stretch><a:fillRect/></a:stretch></p:blipFill><p:spPr>${transformXml(bounds, object)}<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></p:spPr></p:pic>`;
  }

  function extensionForMediaType(mediaType) {
    const type = String(mediaType || "").toLowerCase().split(";")[0];
    if (type === "image/png") return "png";
    if (type === "image/jpeg" || type === "image/jpg") return "jpeg";
    if (type === "image/svg+xml") return "svg";
    return "";
  }

  async function imagePayload(object, options, warnings, context) {
    let mediaType = String(object.mediaType || object.mimeType || "").toLowerCase();
    let bytes = object.bytes instanceof Uint8Array ? object.bytes : null;
    const source = object.dataUrl || object.src || object.source || object.data;
    if (!bytes && typeof source === "string" && source.startsWith("data:")) {
      const parsed = parseDataUrl(source);
      if (parsed) ({ mediaType, bytes } = parsed);
    } else if (!bytes && typeof source === "string" && /^\s*<svg\b/i.test(source)) {
      mediaType = "image/svg+xml";
      bytes = utf8Bytes(source);
    } else if (!bytes && typeof options.resolveImage === "function") {
      const resolved = await options.resolveImage(source, object, context);
      if (resolved) {
        bytes = resolved.bytes instanceof Uint8Array ? resolved.bytes : resolved.dataUrl ? parseDataUrl(resolved.dataUrl)?.bytes : null;
        mediaType = resolved.mediaType || resolved.mimeType || mediaType;
      }
    }
    const extension = extensionForMediaType(mediaType);
    if (!bytes || !extension) {
      warnings.add("image-not-embedded", "An image was skipped because its PNG, JPEG, or SVG bytes were unavailable.", { ...context, action: "skipped" });
      return null;
    }
    if (extension === "svg") {
      warnings.add("svg-modern-office", "SVG artwork is embedded directly. Older PowerPoint versions may rasterize it or fail to display it.", { ...context, action: "embedded-svg" });
    }
    return { mediaType, extension, bytes };
  }

  function slideBackgroundXml(background) {
    const color = normalizeHexColor(background, "");
    return color ? `<p:bg><p:bgPr>${colorXml(color)}<a:effectLst/></p:bgPr></p:bg>` : "";
  }

  function walkCanonicalObjects(objects, visit, path = []) {
    (objects || []).forEach((object, index) => {
      const objectPath = [...path, index];
      visit(object, objectPath);
      if (String(object?.kind || "").toLowerCase() === "group") walkCanonicalObjects(object.objects, visit, objectPath);
    });
  }

  async function buildSlidePart(slide, slideIndex, mediaState, options, warnings) {
    const shapeParts = [];
    const relationships = [{ id: "rId1", type: `${OFFICE_REL_NS}/slideLayout`, target: "../slideLayouts/slideLayout1.xml" }];
    let shapeId = 2;
    const shapeIdByObject = new Map();
    walkCanonicalObjects(slide.objects, (object) => shapeIdByObject.set(object, shapeId++));
    const shapeIdByObjectId = new Map();
    walkCanonicalObjects(slide.objects, (object) => {
      const objectId = String(object?.id || object?.objectId || object?.figureId || object?.sourceId || "");
      const kind = String(object?.kind || object?.type || "").toLowerCase();
      const shape = kind === "shape" ? ({ rect: "rect", rectangle: "rect", roundrect: "roundRect", roundedrectangle: "roundRect", ellipse: "ellipse", circle: "ellipse", triangle: "triangle" }[String(object.shape || object.kind || "rect").replace(/[\s_-]+/g, "").toLowerCase()] || "rect") : "";
      const unsupportedConnectionTransform = Boolean(object?.flipH || object?.flipV || Math.abs(finite(object?.rotation, 0)) > 0.001);
      if (objectId && kind === "shape" && PPTX_CONNECTOR_SITES[shape]) shapeIdByObjectId.set(objectId, { shapeId: shapeIdByObject.get(object), shape, unsupportedConnectionTransform });
    });

    const renderObject = async (object, objectPath = []) => {
      object = object || {};
      const shapeIdForObject = shapeIdByObject.get(object);
      const kind = String(object.kind || object.type || "").toLowerCase();
      const name = String(object.name || object.label || `${kind || "Object"} ${objectPath.map((index) => index + 1).join(".")}`);
      const context = { slideIndex, slideId: slide.id, objectIndex: objectPath[0] || 0, objectPath: objectPath.join("."), objectName: name };
      if (kind === "text") {
        const textObject = { ...object, color: resolveSolidPaint(object.color ?? object.fill, warnings, context, "text color", "#000000") };
        warnCanonicalTextRanges(textObject, warnings, context);
        return textShapeXml(textObject, shapeIdForObject, name);
      } else if (kind === "shape") {
        const textStyle = object.textStyle || object;
        warnCanonicalTextRanges(textStyle, warnings, { ...context, objectName: `${name} text` });
        const shapeObject = {
          ...object,
          fill: resolveSolidPaint(object.fill, warnings, context, "shape fill", ""),
          stroke: resolveSolidPaint(object.stroke, warnings, context, "shape stroke", ""),
          ...(object.text != null && String(object.text) !== "" ? {
            textStyle: {
              ...textStyle,
              color: resolveSolidPaint(textStyle.color ?? textStyle.fill, warnings, context, "shape text color", "#000000")
            }
          } : {})
        };
        return shapeShapeXml(shapeObject, shapeIdForObject, name);
      }
      else if (kind === "line" || kind === "connector") {
        if (object.route && !["straight", "line"].includes(String(object.route).toLowerCase())) {
          warnings.add("connector-flattened-straight", "A curved or elbow connector was exported as a straight connector.", { ...context, action: "approximated" });
        }
        if ([object.startArrow, object.arrowStart, object.endArrow, object.arrowEnd, object.arrowHead].some((value) => String(value || "").toLowerCase() === "bar")) {
          warnings.add("bar-arrowhead-omitted", "A bar line ending was omitted because it is not in the PPTX v1 arrowhead subset.", { ...context, action: "approximated" });
        }
        const lineObject = { ...object, stroke: resolveSolidPaint(object.stroke, warnings, context, "line stroke", "#000000") };
        return connectorShapeXml(lineObject, shapeIdForObject, name, shapeIdByObjectId, warnings, context);
      } else if (kind === "image") {
        const payload = await imagePayload(object, options, warnings, context);
        if (!payload) return "";
        mediaState.count += 1;
        const mediaPath = `ppt/media/image${mediaState.count}.${payload.extension}`;
        const relationshipId = `rId${relationships.length + 1}`;
        mediaState.entries.push({ path: mediaPath, bytes: payload.bytes, mediaType: payload.mediaType, extension: payload.extension });
        relationships.push({ id: relationshipId, type: `${OFFICE_REL_NS}/image`, target: `../media/image${mediaState.count}.${payload.extension}` });
        return pictureShapeXml(object, shapeIdForObject, name, relationshipId);
      } else if (kind === "group") {
        const children = [];
        for (let childIndex = 0; childIndex < (object.objects || []).length; childIndex += 1) {
          children.push(await renderObject(object.objects[childIndex], [...objectPath, childIndex]));
        }
        return `<p:grpSp><p:nvGrpSpPr><p:cNvPr id="${shapeIdForObject}" name="${xmlEscape(name)}"${pptxStableIdentityAttribute(object)}/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr>${groupTransformXml(object)}</p:grpSpPr>${children.join("")}</p:grpSp>`;
      } else {
        warnings.add("object-unsupported", `Unsupported ${kind || "unknown"} content was not added to the PPTX.`, { ...context, action: "skipped" });
        return "";
      }
    };
    for (let objectIndex = 0; objectIndex < slide.objects.length; objectIndex += 1) {
      shapeParts.push(await renderObject(slide.objects[objectIndex], [objectIndex]));
    }
    const notes = String(slide.notes || slide.speakerNotes || "");
    if (notes) relationships.push({ id: `rId${relationships.length + 1}`, type: `${OFFICE_REL_NS}/notesSlide`, target: `../notesSlides/notesSlide${slideIndex + 1}.xml` });
    const xml = `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="${OFFICE_REL_NS}" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"><p:cSld>${slideBackgroundXml(slide.background)}<p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>${shapeParts.join("")}</p:spTree></p:cSld><p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sld>`;
    return { xml, relationships, hasNotes: Boolean(notes) };
  }

  function notesSlideXml(slide) {
    const notes = String(slide.notes || slide.speakerNotes || "");
    return `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<p:notes xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="${OFFICE_REL_NS}" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"><p:cSld><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr><p:sp><p:nvSpPr><p:cNvPr id="2" name="Notes Placeholder 1"/><p:cNvSpPr txBox="1"/><p:nvPr><p:ph type="body" idx="1"/></p:nvPr></p:nvSpPr><p:spPr/><p:txBody><a:bodyPr/><a:lstStyle/>${textParagraphXml(notes, { fontSize: 12, color: "000000" })}</p:txBody></p:sp></p:spTree></p:cSld><p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:notes>`;
  }

  function notesMasterXml() {
    return `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<p:notesMaster xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="${OFFICE_REL_NS}" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"><p:cSld name="Notes Master"><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr><p:sp><p:nvSpPr><p:cNvPr id="2" name="Notes Placeholder"/><p:cNvSpPr txBox="1"/><p:nvPr><p:ph type="body" idx="1"/></p:nvPr></p:nvSpPr><p:spPr/><p:txBody><a:bodyPr/><a:lstStyle/><a:p/></p:txBody></p:sp></p:spTree></p:cSld><p:clrMap accent1="accent1" accent2="accent2" accent3="accent3" accent4="accent4" accent5="accent5" accent6="accent6" bg1="lt1" bg2="lt2" folHlink="folHlink" hlink="hlink" tx1="dk1" tx2="dk2"/><p:hf hdr="0" ftr="0" dt="1" sldNum="1"/><p:notesStyle><a:lvl1pPr marL="0" indent="0"><a:defRPr sz="1200"/></a:lvl1pPr></p:notesStyle></p:notesMaster>`;
  }

  function slideMasterXml() {
    return `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<p:sldMaster xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="${OFFICE_REL_NS}" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"><p:cSld name="Figure Tool"><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr></p:spTree></p:cSld><p:clrMap accent1="accent1" accent2="accent2" accent3="accent3" accent4="accent4" accent5="accent5" accent6="accent6" bg1="lt1" bg2="lt2" folHlink="folHlink" hlink="hlink" tx1="dk1" tx2="dk2"/><p:sldLayoutIdLst><p:sldLayoutId id="2147483649" r:id="rId1"/></p:sldLayoutIdLst><p:txStyles><p:titleStyle><a:lvl1pPr><a:defRPr sz="3200" b="1"/></a:lvl1pPr></p:titleStyle><p:bodyStyle><a:lvl1pPr><a:defRPr sz="1800"/></a:lvl1pPr></p:bodyStyle><p:otherStyle><a:defPPr><a:defRPr lang="en-US"/></a:defPPr></p:otherStyle></p:txStyles></p:sldMaster>`;
  }

  function slideLayoutXml() {
    return `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<p:sldLayout xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="${OFFICE_REL_NS}" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" type="blank" preserve="1"><p:cSld name="Blank"><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr></p:spTree></p:cSld><p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sldLayout>`;
  }

  function themeXml(name = "Figure Tool") {
    return `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<a:theme xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" name="${xmlEscape(name)}"><a:themeElements><a:clrScheme name="Figure Tool"><a:dk1><a:srgbClr val="17283C"/></a:dk1><a:lt1><a:srgbClr val="FFFFFF"/></a:lt1><a:dk2><a:srgbClr val="4B657D"/></a:dk2><a:lt2><a:srgbClr val="F4F7FA"/></a:lt2><a:accent1><a:srgbClr val="2F78B7"/></a:accent1><a:accent2><a:srgbClr val="15887F"/></a:accent2><a:accent3><a:srgbClr val="A94E37"/></a:accent3><a:accent4><a:srgbClr val="7C3AED"/></a:accent4><a:accent5><a:srgbClr val="C27B16"/></a:accent5><a:accent6><a:srgbClr val="526678"/></a:accent6><a:hlink><a:srgbClr val="0563C1"/></a:hlink><a:folHlink><a:srgbClr val="954F72"/></a:folHlink></a:clrScheme><a:fontScheme name="Figure Tool"><a:majorFont><a:latin typeface="Arial"/><a:ea typeface=""/><a:cs typeface=""/></a:majorFont><a:minorFont><a:latin typeface="Arial"/><a:ea typeface=""/><a:cs typeface=""/></a:minorFont></a:fontScheme><a:fmtScheme name="Figure Tool"><a:fillStyleLst><a:solidFill><a:schemeClr val="phClr"/></a:solidFill><a:gradFill rotWithShape="1"><a:gsLst><a:gs pos="0"><a:schemeClr val="phClr"/></a:gs><a:gs pos="100000"><a:schemeClr val="phClr"/></a:gs></a:gsLst><a:lin ang="5400000" scaled="0"/></a:gradFill><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:fillStyleLst><a:lnStyleLst><a:ln w="6350"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill><a:prstDash val="solid"/></a:ln><a:ln w="12700"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill><a:prstDash val="solid"/></a:ln><a:ln w="19050"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill><a:prstDash val="solid"/></a:ln></a:lnStyleLst><a:effectStyleLst><a:effectStyle><a:effectLst/></a:effectStyle><a:effectStyle><a:effectLst/></a:effectStyle><a:effectStyle><a:effectLst/></a:effectStyle></a:effectStyleLst><a:bgFillStyleLst><a:solidFill><a:schemeClr val="phClr"/></a:solidFill><a:solidFill><a:schemeClr val="phClr"/></a:solidFill><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:bgFillStyleLst></a:fmtScheme></a:themeElements></a:theme>`;
  }

  function presentationXml(presentation, includeNotesMaster) {
    const slides = presentation.slides.map((_, index) => `<p:sldId id="${256 + index}" r:id="rId${index + 2}"/>`).join("");
    return `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<p:presentation xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="${OFFICE_REL_NS}" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"><p:sldMasterIdLst><p:sldMasterId id="2147483648" r:id="rId1"/></p:sldMasterIdLst>${includeNotesMaster ? `<p:notesMasterIdLst><p:notesMasterId r:id="rId${presentation.slides.length + 2}"/></p:notesMasterIdLst>` : ""}<p:sldIdLst>${slides}</p:sldIdLst><p:sldSz cx="${toEmu(presentation.widthPt)}" cy="${toEmu(presentation.heightPt)}" type="custom"/><p:notesSz cx="6858000" cy="9144000"/><p:defaultTextStyle><a:defPPr><a:defRPr lang="en-US"/></a:defPPr></p:defaultTextStyle></p:presentation>`;
  }

  function contentTypesXml(slideCount, mediaEntries, notesIndexes) {
    const defaultMedia = new Map([["rels", "application/vnd.openxmlformats-package.relationships+xml"], ["xml", "application/xml"]]);
    (mediaEntries || []).forEach((entry) => defaultMedia.set(entry.extension, entry.mediaType));
    const defaults = Array.from(defaultMedia.entries()).map(([extension, contentType]) => `<Default Extension="${xmlEscape(extension)}" ContentType="${xmlEscape(contentType)}"/>`).join("");
    const slides = Array.from({ length: slideCount }, (_, index) => `<Override PartName="/ppt/slides/slide${index + 1}.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>`).join("");
    const notes = (notesIndexes || []).map((index) => `<Override PartName="/ppt/notesSlides/notesSlide${index + 1}.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.notesSlide+xml"/>`).join("");
    return `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">${defaults}<Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/><Override PartName="/ppt/presProps.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presProps+xml"/><Override PartName="/ppt/viewProps.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.viewProps+xml"/><Override PartName="/ppt/tableStyles.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.tableStyles+xml"/><Override PartName="/ppt/slideMasters/slideMaster1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideMaster+xml"/><Override PartName="/ppt/slideLayouts/slideLayout1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml"/><Override PartName="/ppt/theme/theme1.xml" ContentType="application/vnd.openxmlformats-officedocument.theme+xml"/>${notesIndexes.length ? "<Override PartName=\"/ppt/notesMasters/notesMaster1.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.presentationml.notesMaster+xml\"/><Override PartName=\"/ppt/theme/theme2.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.theme+xml\"/>" : ""}${slides}${notes}<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/><Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/></Types>`;
  }

  function corePropertiesXml(presentation, date) {
    const timestamp = (date instanceof Date ? date : new Date()).toISOString();
    return `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:dcmitype="http://purl.org/dc/dcmitype/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><dc:title>${xmlEscape(presentation.title || "Figure Tool presentation")}</dc:title><dc:creator>${xmlEscape(presentation.author || "Figure Tool")}</dc:creator><cp:lastModifiedBy>Figure Tool</cp:lastModifiedBy><dcterms:created xsi:type="dcterms:W3CDTF">${timestamp}</dcterms:created><dcterms:modified xsi:type="dcterms:W3CDTF">${timestamp}</dcterms:modified></cp:coreProperties>`;
  }

  function appPropertiesXml(slideCount, notesCount, title) {
    return `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes"><Application>Figure Tool</Application><AppVersion>${PRODUCT_VERSION.split("-")[0]}</AppVersion><PresentationFormat>Custom</PresentationFormat><Slides>${slideCount}</Slides><Notes>${notesCount}</Notes><HiddenSlides>0</HiddenSlides><TitlesOfParts><vt:vector size="${slideCount}" baseType="lpstr">${Array.from({ length: slideCount }, (_, index) => `<vt:lpstr>${xmlEscape(title || `Slide ${index + 1}`)}</vt:lpstr>`).join("")}</vt:vector></TitlesOfParts></Properties>`;
  }

  function normalizePresentation(input = {}, warnings = warningCollector()) {
    const widthPt = clamp(finite(input.widthPt, finite(input.width, 10 * POINTS_PER_INCH)), 72, 56 * POINTS_PER_INCH);
    const heightPt = clamp(finite(input.heightPt, finite(input.height, 5.625 * POINTS_PER_INCH)), 72, 56 * POINTS_PER_INCH);
    const slides = (Array.isArray(input.slides) ? input.slides : []).map((slide, index) => ({
      id: String(slide?.id || `slide-${index + 1}`),
      name: String(slide?.name || slide?.label || `Slide ${index + 1}`),
      notes: String(slide?.notes ?? slide?.speakerNotes ?? "").slice(0, 12000),
      background: slide?.background || "",
      objects: Array.isArray(slide?.objects) ? slide.objects.map((object) => ({ ...object })) : []
    }));
    if (!slides.length) {
      slides.push({ id: "slide-1", name: "Slide 1", notes: "", background: "", objects: [] });
      warnings.add("empty-deck", "The presentation had no slides, so a blank slide was added.", { action: "blank-slide-added" });
    }
    return { schema: "figureStudio.pptxPresentation.v1", widthPt, heightPt, title: String(input.title || "Figure Tool presentation"), author: String(input.author || "Figure Tool"), slides };
  }

  async function exportPresentation(input, options = {}) {
    const warnings = warningCollector();
    const presentation = normalizePresentation(input, warnings);
    const mediaState = { count: 0, entries: [] };
    const slideParts = [];
    for (let index = 0; index < presentation.slides.length; index += 1) {
      slideParts.push(await buildSlidePart(presentation.slides[index], index, mediaState, options, warnings));
    }
    const notesIndexes = slideParts.map((part, index) => part.hasNotes ? index : -1).filter((index) => index >= 0);
    const includeNotesMaster = notesIndexes.length > 0;
    const date = options.date instanceof Date ? options.date : new Date();
    const presentationRelationships = [{ id: "rId1", type: `${OFFICE_REL_NS}/slideMaster`, target: "slideMasters/slideMaster1.xml" }];
    presentation.slides.forEach((_, index) => presentationRelationships.push({ id: `rId${index + 2}`, type: `${OFFICE_REL_NS}/slide`, target: `slides/slide${index + 1}.xml` }));
    if (includeNotesMaster) presentationRelationships.push({ id: `rId${presentation.slides.length + 2}`, type: `${OFFICE_REL_NS}/notesMaster`, target: "notesMasters/notesMaster1.xml" });
    presentationRelationships.push(
      { id: `rId${presentationRelationships.length + 1}`, type: `${OFFICE_REL_NS}/presProps`, target: "presProps.xml" },
      { id: `rId${presentationRelationships.length + 2}`, type: `${OFFICE_REL_NS}/viewProps`, target: "viewProps.xml" },
      { id: `rId${presentationRelationships.length + 3}`, type: `${OFFICE_REL_NS}/tableStyles`, target: "tableStyles.xml" }
    );
    const entries = [
      { path: "[Content_Types].xml", bytes: contentTypesXml(presentation.slides.length, mediaState.entries, notesIndexes) },
      { path: "_rels/.rels", bytes: relationshipXml([
        { id: "rId1", type: `${OFFICE_REL_NS}/officeDocument`, target: "ppt/presentation.xml" },
        { id: "rId2", type: "http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties", target: "docProps/core.xml" },
        { id: "rId3", type: `${OFFICE_REL_NS}/extended-properties`, target: "docProps/app.xml" }
      ]) },
      { path: "docProps/core.xml", bytes: corePropertiesXml(presentation, date) },
      { path: "docProps/app.xml", bytes: appPropertiesXml(presentation.slides.length, notesIndexes.length, presentation.title) },
      { path: "ppt/presentation.xml", bytes: presentationXml(presentation, includeNotesMaster) },
      { path: "ppt/_rels/presentation.xml.rels", bytes: relationshipXml(presentationRelationships) },
      { path: "ppt/presProps.xml", bytes: "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?><p:presentationPr xmlns:a=\"http://schemas.openxmlformats.org/drawingml/2006/main\" xmlns:r=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships\" xmlns:p=\"http://schemas.openxmlformats.org/presentationml/2006/main\"/>" },
      { path: "ppt/viewProps.xml", bytes: "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?><p:viewPr xmlns:a=\"http://schemas.openxmlformats.org/drawingml/2006/main\" xmlns:r=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships\" xmlns:p=\"http://schemas.openxmlformats.org/presentationml/2006/main\" lastView=\"sldView\"/>" },
      { path: "ppt/tableStyles.xml", bytes: "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?><a:tblStyleLst xmlns:a=\"http://schemas.openxmlformats.org/drawingml/2006/main\" def=\"{5C22544A-7EE6-4342-B048-85BDC9FD1C3A}\"/>" },
      { path: "ppt/theme/theme1.xml", bytes: themeXml() },
      { path: "ppt/slideMasters/slideMaster1.xml", bytes: slideMasterXml() },
      { path: "ppt/slideMasters/_rels/slideMaster1.xml.rels", bytes: relationshipXml([
        { id: "rId1", type: `${OFFICE_REL_NS}/slideLayout`, target: "../slideLayouts/slideLayout1.xml" },
        { id: "rId2", type: `${OFFICE_REL_NS}/theme`, target: "../theme/theme1.xml" }
      ]) },
      { path: "ppt/slideLayouts/slideLayout1.xml", bytes: slideLayoutXml() },
      { path: "ppt/slideLayouts/_rels/slideLayout1.xml.rels", bytes: relationshipXml([{ id: "rId1", type: `${OFFICE_REL_NS}/slideMaster`, target: "../slideMasters/slideMaster1.xml" }]) }
    ];
    slideParts.forEach((part, index) => {
      entries.push({ path: `ppt/slides/slide${index + 1}.xml`, bytes: part.xml });
      entries.push({ path: `ppt/slides/_rels/slide${index + 1}.xml.rels`, bytes: relationshipXml(part.relationships) });
      if (part.hasNotes) {
        entries.push({ path: `ppt/notesSlides/notesSlide${index + 1}.xml`, bytes: notesSlideXml(presentation.slides[index]) });
        entries.push({ path: `ppt/notesSlides/_rels/notesSlide${index + 1}.xml.rels`, bytes: relationshipXml([
          { id: "rId1", type: `${OFFICE_REL_NS}/notesMaster`, target: "../notesMasters/notesMaster1.xml" },
          { id: "rId2", type: `${OFFICE_REL_NS}/slide`, target: `../slides/slide${index + 1}.xml` }
        ]) });
      }
    });
    if (includeNotesMaster) {
      entries.push({ path: "ppt/notesMasters/notesMaster1.xml", bytes: notesMasterXml() });
      entries.push({ path: "ppt/notesMasters/_rels/notesMaster1.xml.rels", bytes: relationshipXml([{ id: "rId1", type: `${OFFICE_REL_NS}/theme`, target: "../theme/theme2.xml" }]) });
      entries.push({ path: "ppt/theme/theme2.xml", bytes: themeXml("Figure Tool Notes") });
    }
    mediaState.entries.forEach((entry) => entries.push({ path: entry.path, bytes: entry.bytes }));
    const normalizedEntries = entries.map((entry) => ({ path: entry.path, bytes: entry.bytes instanceof Uint8Array ? entry.bytes : utf8Bytes(entry.bytes) }));
    const bytes = buildStoredZip(normalizedEntries, { date });
    const filename = String(options.filename || "figure-studio-presentation.pptx").replace(/\.pptx$/i, "") + ".pptx";
    return {
      schema: "figureStudio.pptxExportResult.v1",
      status: "completed",
      filename,
      mimeType: MIME_TYPE,
      bytes,
      blob: typeof Blob === "function" ? new Blob([bytes], { type: MIME_TYPE }) : null,
      slideCount: presentation.slides.length,
      mediaCount: mediaState.entries.length,
      warnings: warnings.rows,
      compatibility: COMPATIBILITY,
      presentation
    };
  }

  function fabricOriginFraction(origin, axis) {
    const value = String(origin || (axis === "x" ? "left" : "top")).toLowerCase();
    if (value === "center") return 0.5;
    if (value === "right" || value === "bottom") return 1;
    return 0;
  }

  function fabricRawDimensions(object = {}) {
    return {
      width: Math.max(0.01, finite(object.width, finite(object.rx, finite(object.radius, 0.5)) * 2)),
      height: Math.max(0.01, finite(object.height, finite(object.ry, finite(object.radius, 0.5)) * 2))
    };
  }

  function pathCoordinateBounds(path) {
    const rows = Array.isArray(path) ? path : [];
    let minX = Infinity;
    let minY = Infinity;
    let maxX = -Infinity;
    let maxY = -Infinity;
    let x = 0;
    let y = 0;
    let startX = 0;
    let startY = 0;
    let previousCommand = "";
    let previousCubicControl = null;
    let previousQuadraticControl = null;
    const add = (px, py) => {
      if (!Number.isFinite(px) || !Number.isFinite(py)) return;
      minX = Math.min(minX, px);
      minY = Math.min(minY, py);
      maxX = Math.max(maxX, px);
      maxY = Math.max(maxY, py);
    };
    const cubicAt = (p0, p1, p2, p3, t) => {
      const mt = 1 - t;
      return mt * mt * mt * p0 + 3 * mt * mt * t * p1 + 3 * mt * t * t * p2 + t * t * t * p3;
    };
    const cubicExtrema = (p0, p1, p2, p3) => {
      const a = -p0 + 3 * p1 - 3 * p2 + p3;
      const b = 3 * p0 - 6 * p1 + 3 * p2;
      const c = -3 * p0 + 3 * p1;
      if (Math.abs(a) < 1e-12) return Math.abs(b) < 1e-12 ? [] : [-c / (2 * b)];
      const discriminant = 4 * b * b - 12 * a * c;
      if (discriminant < 0) return [];
      const root = Math.sqrt(discriminant);
      return [(-2 * b + root) / (6 * a), (-2 * b - root) / (6 * a)];
    };
    const arcExtrema = (start, end, sourceRadiusX, sourceRadiusY, rotation, largeArc, sweep) => {
      let radiusX = Math.abs(finite(sourceRadiusX));
      let radiusY = Math.abs(finite(sourceRadiusY));
      if (!radiusX || !radiusY || (Math.abs(start.x - end.x) < 1e-12 && Math.abs(start.y - end.y) < 1e-12)) return [start, end];
      const phi = finite(rotation) * Math.PI / 180;
      const cosPhi = Math.cos(phi);
      const sinPhi = Math.sin(phi);
      const halfDx = (start.x - end.x) / 2;
      const halfDy = (start.y - end.y) / 2;
      const xPrime = cosPhi * halfDx + sinPhi * halfDy;
      const yPrime = -sinPhi * halfDx + cosPhi * halfDy;
      const radiusScale = xPrime * xPrime / (radiusX * radiusX) + yPrime * yPrime / (radiusY * radiusY);
      if (radiusScale > 1) {
        const scale = Math.sqrt(radiusScale);
        radiusX *= scale;
        radiusY *= scale;
      }
      const radiusXSquared = radiusX * radiusX;
      const radiusYSquared = radiusY * radiusY;
      const denominator = radiusXSquared * yPrime * yPrime + radiusYSquared * xPrime * xPrime;
      const numerator = Math.max(0, radiusXSquared * radiusYSquared - denominator);
      const direction = Boolean(largeArc) === Boolean(sweep) ? -1 : 1;
      const coefficient = denominator > 0 ? direction * Math.sqrt(numerator / denominator) : 0;
      const centerPrimeX = coefficient * radiusX * yPrime / radiusY;
      const centerPrimeY = coefficient * -radiusY * xPrime / radiusX;
      const centerX = cosPhi * centerPrimeX - sinPhi * centerPrimeY + (start.x + end.x) / 2;
      const centerY = sinPhi * centerPrimeX + cosPhi * centerPrimeY + (start.y + end.y) / 2;
      const vectorAngle = (ux, uy, vx, vy) => Math.atan2(ux * vy - uy * vx, ux * vx + uy * vy);
      const startVectorX = (xPrime - centerPrimeX) / radiusX;
      const startVectorY = (yPrime - centerPrimeY) / radiusY;
      const endVectorX = (-xPrime - centerPrimeX) / radiusX;
      const endVectorY = (-yPrime - centerPrimeY) / radiusY;
      const startAngle = vectorAngle(1, 0, startVectorX, startVectorY);
      let deltaAngle = vectorAngle(startVectorX, startVectorY, endVectorX, endVectorY);
      if (!sweep && deltaAngle > 0) deltaAngle -= 2 * Math.PI;
      if (sweep && deltaAngle < 0) deltaAngle += 2 * Math.PI;
      const normalizeAngle = (angle) => {
        const turn = 2 * Math.PI;
        return ((angle % turn) + turn) % turn;
      };
      const angleIsOnArc = (angle) => sweep
        ? normalizeAngle(angle - startAngle) <= deltaAngle + 1e-9
        : normalizeAngle(startAngle - angle) <= -deltaAngle + 1e-9;
      const evaluate = (angle) => ({
        x: centerX + radiusX * cosPhi * Math.cos(angle) - radiusY * sinPhi * Math.sin(angle),
        y: centerY + radiusX * sinPhi * Math.cos(angle) + radiusY * cosPhi * Math.sin(angle)
      });
      const xExtremum = Math.atan2(-radiusY * sinPhi, radiusX * cosPhi);
      const yExtremum = Math.atan2(radiusY * cosPhi, radiusX * sinPhi);
      return [startAngle, startAngle + deltaAngle, xExtremum, xExtremum + Math.PI, yExtremum, yExtremum + Math.PI]
        .filter((angle, index) => index < 2 || angleIsOnArc(angle))
        .map(evaluate);
    };
    const relativePoint = (command, px, py) => command === command.toLowerCase()
      ? { x: x + finite(px), y: y + finite(py) }
      : { x: finite(px), y: finite(py) };

    rows.forEach((row) => {
      if (!Array.isArray(row) || !row.length) return;
      const sourceCommand = String(row[0] || "");
      const command = sourceCommand.toUpperCase();
      const relative = sourceCommand === sourceCommand.toLowerCase();
      if (command === "M" || command === "L") {
        const point = relativePoint(sourceCommand, row[1], row[2]);
        x = point.x;
        y = point.y;
        if (command === "M") {
          startX = x;
          startY = y;
        }
        add(x, y);
      } else if (command === "H") {
        x = relative ? x + finite(row[1]) : finite(row[1]);
        add(x, y);
      } else if (command === "V") {
        y = relative ? y + finite(row[1]) : finite(row[1]);
        add(x, y);
      } else if (command === "C" || command === "S") {
        let control1;
        let control2;
        let end;
        if (command === "C") {
          control1 = relativePoint(sourceCommand, row[1], row[2]);
          control2 = relativePoint(sourceCommand, row[3], row[4]);
          end = relativePoint(sourceCommand, row[5], row[6]);
        } else {
          control1 = ["C", "S"].includes(previousCommand) && previousCubicControl
            ? { x: 2 * x - previousCubicControl.x, y: 2 * y - previousCubicControl.y }
            : { x, y };
          control2 = relativePoint(sourceCommand, row[1], row[2]);
          end = relativePoint(sourceCommand, row[3], row[4]);
        }
        add(x, y);
        add(end.x, end.y);
        cubicExtrema(x, control1.x, control2.x, end.x).filter((t) => t > 0 && t < 1).forEach((t) => add(cubicAt(x, control1.x, control2.x, end.x, t), cubicAt(y, control1.y, control2.y, end.y, t)));
        cubicExtrema(y, control1.y, control2.y, end.y).filter((t) => t > 0 && t < 1).forEach((t) => add(cubicAt(x, control1.x, control2.x, end.x, t), cubicAt(y, control1.y, control2.y, end.y, t)));
        x = end.x;
        y = end.y;
        previousCubicControl = control2;
      } else if (command === "Q" || command === "T") {
        let control;
        let end;
        if (command === "Q") {
          control = relativePoint(sourceCommand, row[1], row[2]);
          end = relativePoint(sourceCommand, row[3], row[4]);
        } else {
          control = ["Q", "T"].includes(previousCommand) && previousQuadraticControl
            ? { x: 2 * x - previousQuadraticControl.x, y: 2 * y - previousQuadraticControl.y }
            : { x, y };
          end = relativePoint(sourceCommand, row[1], row[2]);
        }
        add(x, y);
        add(end.x, end.y);
        cubicExtrema(x, control.x, control.x, end.x).filter((t) => t > 0 && t < 1).forEach((t) => add(cubicAt(x, control.x, control.x, end.x, t), cubicAt(y, control.y, control.y, end.y, t)));
        cubicExtrema(y, control.y, control.y, end.y).filter((t) => t > 0 && t < 1).forEach((t) => add(cubicAt(x, control.x, control.x, end.x, t), cubicAt(y, control.y, control.y, end.y, t)));
        x = end.x;
        y = end.y;
        previousQuadraticControl = control;
      } else if (command === "A") {
        const end = relativePoint(sourceCommand, row[6], row[7]);
        arcExtrema({ x, y }, end, row[1], row[2], row[3], Number(row[4]) !== 0, Number(row[5]) !== 0).forEach((point) => add(point.x, point.y));
        x = end.x;
        y = end.y;
      } else if (command === "Z") {
        x = startX;
        y = startY;
        add(x, y);
      }
      if (!["C", "S"].includes(command)) previousCubicControl = null;
      if (!["Q", "T"].includes(command)) previousQuadraticControl = null;
      previousCommand = command;
    });
    return Number.isFinite(minX) ? { minX, minY, maxX, maxY } : null;
  }

  function fabricPathOffset(object = {}) {
    if (Number.isFinite(Number(object.pathOffset?.x)) && Number.isFinite(Number(object.pathOffset?.y))) {
      return { x: Number(object.pathOffset.x), y: Number(object.pathOffset.y) };
    }
    const bounds = pathCoordinateBounds(object.path);
    if (bounds) return { x: (bounds.minX + bounds.maxX) / 2, y: (bounds.minY + bounds.maxY) / 2 };
    const dimensions = fabricRawDimensions(object);
    return { x: dimensions.width / 2, y: dimensions.height / 2 };
  }

  function fabricSvgTransform(object = {}, options = {}) {
    const dimensions = fabricRawDimensions(object);
    if (options.root) return `translate(${dimensions.width / 2} ${dimensions.height / 2})`;
    const scaleX = finite(object.scaleX, 1) * (object.flipX ? -1 : 1);
    const scaleY = finite(object.scaleY, 1) * (object.flipY ? -1 : 1);
    const angle = finite(object.angle, 0);
    const radians = angle * Math.PI / 180;
    const dx = (0.5 - fabricOriginFraction(object.originX, "x")) * dimensions.width * Math.abs(scaleX);
    const dy = (0.5 - fabricOriginFraction(object.originY, "y")) * dimensions.height * Math.abs(scaleY);
    const centerX = finite(object.left, 0) + dx * Math.cos(radians) - dy * Math.sin(radians);
    const centerY = finite(object.top, 0) + dx * Math.sin(radians) + dy * Math.cos(radians);
    return `translate(${centerX} ${centerY}) rotate(${angle}) scale(${scaleX} ${scaleY})`;
  }

  function fabricBounds(object, scaleToPoints) {
    const scaleX = finite(object.scaleX, 1);
    const scaleY = finite(object.scaleY, 1);
    const rawWidth = Math.max(0.01, finite(object.width, finite(object.rx, 1) * 2));
    const rawHeight = Math.max(0.01, finite(object.height, finite(object.ry, 1) * 2));
    const width = Math.abs(rawWidth * scaleX);
    const height = Math.abs(rawHeight * scaleY);
    const angle = finite(object.angle, 0);
    const radians = angle * Math.PI / 180;
    const dx = (0.5 - fabricOriginFraction(object.originX, "x")) * width;
    const dy = (0.5 - fabricOriginFraction(object.originY, "y")) * height;
    const centerX = finite(object.left, 0) + dx * Math.cos(radians) - dy * Math.sin(radians);
    const centerY = finite(object.top, 0) + dx * Math.sin(radians) + dy * Math.cos(radians);
    return { x: (centerX - width / 2) * scaleToPoints, y: (centerY - height / 2) * scaleToPoints, width: width * scaleToPoints, height: height * scaleToPoints, rotation: angle };
  }

  function supportedFabricRectClip(clipPath) {
    return String(clipPath?.type || "").toLowerCase() === "rect" && !clipPath?.inverted && !clipPath?.absolutePositioned;
  }

  function svgElementForFabric(object, options = {}, svgState = { clipCount: 0 }) {
    if (!fabricObjectExportable(object)) return "";
    const type = String(object?.type || "").toLowerCase();
    const opacity = clamp(object?.opacity == null ? 1 : object.opacity, 0, 1);
    const fillSource = solidPaintCandidate(object?.fill, "");
    const strokeSource = solidPaintCandidate(object?.stroke, "");
    const fillAlpha = paintAlpha(fillSource);
    const strokeAlpha = paintAlpha(strokeSource);
    const fill = fillAlpha > 0 ? normalizeHexColor(fillSource, "") : "";
    const stroke = strokeAlpha > 0 ? normalizeHexColor(strokeSource, "") : "";
    const strokeWidth = Math.max(0, finite(object?.strokeWidth, 0));
    const paint = `fill="${fill ? `#${fill}` : "none"}" fill-opacity="${fillAlpha}" stroke="${stroke ? `#${stroke}` : "none"}" stroke-opacity="${strokeAlpha}" stroke-width="${strokeWidth}" opacity="${opacity}"`;
    const dimensions = fabricRawDimensions(object);
    const transform = fabricSvgTransform(object, options);
    if (type === 'line') {
      // Fabric paints lines relative to their midpoint. Their serialized endpoint
      // coordinates may have any origin, including reversed or zero-size axes.
      const x1 = finite(object.x1), x2 = finite(object.x2, finite(object.width));
      const y1 = finite(object.y1), y2 = finite(object.y2, finite(object.height));
      const cx = (x1 + x2) / 2, cy = (y1 + y2) / 2;
      const dash = Array.isArray(object.strokeDashArray) ? object.strokeDashArray.map(value => Math.max(0, finite(value))).join(' ') : '';
      const cap = ['butt', 'round', 'square'].includes(object.strokeLineCap) ? object.strokeLineCap : 'butt';
      return `<line x1="${x1 - cx}" y1="${y1 - cy}" x2="${x2 - cx}" y2="${y2 - cy}" ${paint} stroke-linecap="${cap}"${dash ? ` stroke-dasharray="${dash}"` : ''} transform="${transform}"/>`;
    }
    if (type === "path" && Array.isArray(object.path)) {
      const data = object.path.map((row) => Array.isArray(row) ? row.map((value, index) => index === 0 ? String(value) : finite(value)).join(" ") : "").filter(Boolean).join(" ");
      const pathOffset = fabricPathOffset(object);
      return `<path d="${xmlEscape(data)}" ${paint} transform="${transform} translate(${-finite(pathOffset.x)} ${-finite(pathOffset.y)})"/>`;
    }
    if (type === "rect") return `<rect x="${-dimensions.width / 2}" y="${-dimensions.height / 2}" width="${dimensions.width}" height="${dimensions.height}" rx="${finite(object.rx, 0)}" ${paint} transform="${transform}"/>`;
    if (type === "ellipse" || type === "circle") return `<ellipse cx="0" cy="0" rx="${finite(object.rx, finite(object.radius, dimensions.width / 2))}" ry="${finite(object.ry, finite(object.radius, dimensions.height / 2))}" ${paint} transform="${transform}"/>`;
    if (type === "polygon" || type === "polyline") {
      const points = (object.points || []).map((point) => `${finite(point.x)} ${finite(point.y)}`).join(" ");
      const pointBounds = (object.points || []).reduce((result, point) => ({
        minX: Math.min(result.minX, finite(point.x)), minY: Math.min(result.minY, finite(point.y)),
        maxX: Math.max(result.maxX, finite(point.x)), maxY: Math.max(result.maxY, finite(point.y))
      }), { minX: Infinity, minY: Infinity, maxX: -Infinity, maxY: -Infinity });
      const offset = object.pathOffset || (Number.isFinite(pointBounds.minX) ? { x: (pointBounds.minX + pointBounds.maxX) / 2, y: (pointBounds.minY + pointBounds.maxY) / 2 } : { x: 0, y: 0 });
      return `<${type} points="${xmlEscape(points)}" ${paint} transform="${transform} translate(${-finite(offset.x)} ${-finite(offset.y)})"/>`;
    }
    if (["textbox", "i-text", "itext", "text"].includes(type)) {
      const baseline = -dimensions.height / 2 + finite(object.fontSize, 16);
      return `<text x="${-dimensions.width / 2}" y="${baseline}" font-family="${xmlEscape(object.fontFamily || "Arial")}" font-size="${finite(object.fontSize, 16)}" font-weight="${xmlEscape(object.fontWeight || "400")}" ${paint} transform="${transform}">${xmlEscape(object.text || "")}</text>`;
    }
    if (type === "image") {
      const source = [object?.src, object?.dataUrl, object?.source].find((candidate) => typeof candidate === "string" && candidate.startsWith("data:image/"));
      if (!source) return "";
      const cropX = Math.max(0, finite(object.cropX, 0));
      const cropY = Math.max(0, finite(object.cropY, 0));
      const naturalWidth = Math.max(dimensions.width + cropX, finite(object.importMeta?.originalWidth, finite(object.naturalWidth, dimensions.width + cropX)));
      const naturalHeight = Math.max(dimensions.height + cropY, finite(object.importMeta?.originalHeight, finite(object.naturalHeight, dimensions.height + cropY)));
      const cropId = `figureStudioImageCrop${++svgState.clipCount}`;
      return `<g transform="${transform}"><defs><clipPath id="${cropId}" clipPathUnits="userSpaceOnUse"><rect x="${-dimensions.width / 2}" y="${-dimensions.height / 2}" width="${dimensions.width}" height="${dimensions.height}"/></clipPath></defs><image x="${-dimensions.width / 2 - cropX}" y="${-dimensions.height / 2 - cropY}" width="${naturalWidth}" height="${naturalHeight}" preserveAspectRatio="none" opacity="${opacity}" clip-path="url(#${cropId})" xlink:href="${xmlEscape(source)}"/></g>`;
    }
    if (type === "group" && Array.isArray(object.objects)) {
      const children = object.objects.map((child) => svgElementForFabric(child, {}, svgState)).join("");
      if (supportedFabricRectClip(object.clipPath)) {
        const clipDimensions = fabricRawDimensions(object.clipPath);
        const clipTransform = fabricSvgTransform(object.clipPath);
        const clipId = `figureStudioGroupClip${++svgState.clipCount}`;
        const clipRect = `<rect x="${-clipDimensions.width / 2}" y="${-clipDimensions.height / 2}" width="${clipDimensions.width}" height="${clipDimensions.height}" rx="${finite(object.clipPath.rx, 0)}" transform="${clipTransform}"/>`;
        return `<g transform="${transform}" opacity="${opacity}"><defs><clipPath id="${clipId}" clipPathUnits="userSpaceOnUse">${clipRect}</clipPath></defs><g clip-path="url(#${clipId})">${children}</g></g>`;
      }
      return `<g transform="${transform}" opacity="${opacity}">${children}</g>`;
    }
    return "";
  }

  function inspectFabricSvgFallback(object, result = { contentLoss: 0, appearanceLoss: 0, contentReasons: new Set(), appearanceReasons: new Set() }) {
    const type = String(object?.type || "").toLowerCase();
    const supported = ["line", "path", "rect", "ellipse", "circle", "polygon", "polyline", "textbox", "i-text", "itext", "text", "image", "group"];
    if (!supported.includes(type)) {
      result.contentLoss += 1;
      result.contentReasons.add(`unsupported ${type || "unknown"} child`);
      return result;
    }
    if (type === "image" && ![object?.src, object?.dataUrl, object?.source].some((candidate) => typeof candidate === "string" && candidate.startsWith("data:image/"))) {
      result.contentLoss += 1;
      result.contentReasons.add("image child without embedded data");
    }
    [["fill", object?.fill], ["stroke", object?.stroke]].forEach(([role, paint]) => {
      if (paint && typeof paint === "object") {
        result.appearanceLoss += 1;
        result.appearanceReasons.add(`${paintKind(paint)} ${role}`);
      }
    });
    const supportedClip = type === "group" && supportedFabricRectClip(object.clipPath);
    const unsupportedClip = object?.clipPath && !supportedClip;
    if (unsupportedClip || object?.shadow || object?.mask || object?.eraser || (Array.isArray(object?.filters) && object.filters.length)) {
      result.appearanceLoss += 1;
      result.appearanceReasons.add("clip, shadow, mask, eraser, or filter effect");
    }
    const composite = String(object?.globalCompositeOperation || "source-over").toLowerCase();
    if (composite && composite !== "source-over") {
      result.appearanceLoss += 1;
      result.appearanceReasons.add(`blend mode ${composite}`);
    }
    if (type === "group") (object.objects || []).forEach((child) => inspectFabricSvgFallback(child, result));
    return result;
  }

  function fabricVectorAsImage(object, bounds, warnings, context) {
    const audit = inspectFabricSvgFallback(object);
    const svgElement = svgElementForFabric(object, { root: true }, { clipCount: 0 });
    if (!svgElement) {
      audit.contentLoss += 1;
      audit.contentReasons.add("unrenderable vector root");
    }
    if (audit.contentLoss) {
      warnings.add("svg-fallback-content-loss", "Some vector or group content could not be represented in the SVG fallback and was omitted.", {
        ...context,
        omittedNodeCount: audit.contentLoss,
        reasons: Array.from(audit.contentReasons),
        action: "partially-skipped"
      });
    }
    if (audit.appearanceLoss) {
      warnings.add("svg-fallback-appearance-flattened", "Complex paint or effects in the SVG fallback were reduced to a supported solid appearance where possible.", {
        ...context,
        affectedAppearanceCount: audit.appearanceLoss,
        reasons: Array.from(audit.appearanceReasons),
        action: "flattened"
      });
    }
    if (!svgElement) return null;
    const dimensions = fabricRawDimensions(object);
    const widthPx = dimensions.width;
    const heightPx = dimensions.height;
    const svg = `<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="${widthPx}" height="${heightPx}" viewBox="0 0 ${widthPx} ${heightPx}">${svgElement}</svg>`;
    warnings.add("vector-flattened-to-svg", "Figure Tool vector artwork was embedded as one SVG image. Its internal nodes are not PowerPoint shapes.", { ...context, action: "embedded-svg" });
    return { kind: "image", ...bounds, mediaType: "image/svg+xml", data: svg, name: object.name || object.figureName || "Vector artwork" };
  }

  function fabricLineEndpoints(object, scaleToPoints) {
    const smart = object.smartConnectorMeta;
    if (smart?.start?.point && smart?.end?.point) {
      return { x1: finite(smart.start.point.x) * scaleToPoints, y1: finite(smart.start.point.y) * scaleToPoints, x2: finite(smart.end.point.x) * scaleToPoints, y2: finite(smart.end.point.y) * scaleToPoints, route: smart.route || smart.routeMode };
    }
    if (String(object.type || "").toLowerCase() === "line") {
      const left = finite(object.left, 0);
      const top = finite(object.top, 0);
      return { x1: (left + finite(object.x1, 0)) * scaleToPoints, y1: (top + finite(object.y1, 0)) * scaleToPoints, x2: (left + finite(object.x2, object.width || 1)) * scaleToPoints, y2: (top + finite(object.y2, object.height || 0)) * scaleToPoints };
    }
    const pathOffset = object.pathOffset || { x: finite(object.width, 0) / 2, y: finite(object.height, 0) / 2 };
    const start = { x: finite(object.lineVectorStartX, 0) - finite(pathOffset.x), y: finite(object.lineVectorStartY, 0) - finite(pathOffset.y) };
    const end = { x: finite(object.lineVectorEndX, object.lineVectorWidth || object.width || 1) - finite(pathOffset.x), y: finite(object.lineVectorEndY, object.lineVectorHeight || 0) - finite(pathOffset.y) };
    const angle = finite(object.angle, 0) * Math.PI / 180;
    const transform = (point) => {
      const x = point.x * finite(object.scaleX, 1);
      const y = point.y * finite(object.scaleY, 1);
      return { x: finite(object.left, 0) + x * Math.cos(angle) - y * Math.sin(angle), y: finite(object.top, 0) + x * Math.sin(angle) + y * Math.cos(angle) };
    };
    const a = transform(start);
    const b = transform(end);
    return { x1: a.x * scaleToPoints, y1: a.y * scaleToPoints, x2: b.x * scaleToPoints, y2: b.y * scaleToPoints };
  }

  function fabricTextHasCharacterRanges(object) {
    const type = String(object?.type || object?.kind || "").toLowerCase();
    if (!["textbox", "i-text", "itext", "text"].includes(type)) return false;
    const styleSource = object.styles || {};
    const hasCharacterStyles = Array.isArray(styleSource)
      ? styleSource.some((entry) => entry && typeof entry.style === "object" && Number(entry.end) > Number(entry.start))
      : Object.values(styleSource).some((line) => (
        line && typeof line === "object" && Object.keys(line).length > 0
      ));
    const hasScientificRuns = Array.isArray(object.figureStudioTypographyMeta?.range_runs)
      && object.figureStudioTypographyMeta.range_runs.length > 0;
    return hasCharacterStyles || hasScientificRuns;
  }

  function fabricTextUnsupportedCharacterRangeReasons(object) {
    const reasons = new Set();
    const supported = new Set(["fill", "color", "fontFamily", "fontSize", "fontWeight", "fontStyle", "underline", "linethrough"]);
    const inspectStyle = (style) => {
      if (!style || typeof style !== "object") return;
      Object.keys(style).forEach((key) => {
        if (!supported.has(key)) reasons.add(key);
      });
      ["fill", "color"].forEach((key) => {
        if (style[key] && typeof style[key] === "object") reasons.add(`${key}-object`);
        if (typeof style[key] === "string" && /^rgba\(/i.test(style[key])) reasons.add(`${key}-alpha`);
      });
      if (style.opacity != null && Number(style.opacity) < 1) reasons.add("alpha");
      if (style.deltaY || style.figureStudioScript || style.figureStudioBaselineShiftPt) reasons.add("baseline-shift");
      if (style.overline) reasons.add("text-decoration");
      if (style.backgroundColor && String(style.backgroundColor).toLowerCase() !== "transparent") reasons.add("background-color");
    };
    const styleSource = object?.styles || {};
    if (Array.isArray(styleSource)) {
      styleSource.forEach((entry) => inspectStyle(entry?.style));
    } else {
      Object.values(styleSource).forEach((line) => {
        if (!line || typeof line !== "object") return;
        Object.values(line).forEach(inspectStyle);
      });
    }
    if (Array.isArray(object?.figureStudioTypographyMeta?.range_runs) && object.figureStudioTypographyMeta.range_runs.length > 0) {
      reasons.add("scientific-typography-meta");
    }
    return [...reasons];
  }


  function warnCanonicalTextRanges(object, warnings, context) {
    if (!object?.styles) return;
    warnFabricCharacterRanges({ type: "text", styles: object.styles, figureStudioTypographyMeta: object.figureStudioTypographyMeta }, warnings, context);
  }

  function warnFabricCharacterRanges(object, warnings, context, path = []) {
    if (!object || typeof object !== "object") return;
    const unsupported = fabricTextUnsupportedCharacterRangeReasons(object);
    if (unsupported.length) {
      warnings.add(
        "character-range-formatting-approximated",
        "Some character-range formatting is outside the PPTX v1 editable text-run subset. Supported bold, italic, underline, strikethrough, color, family, and size spans remain editable; unsupported text effects need review.",
        {
          ...context,
          objectName: object.name || object.figureName || object.figureLabel || context.objectName || "Text",
          nestedObjectPath: path.join("."),
          reasons: unsupported,
          action: "approximated"
        }
      );
    }
    (Array.isArray(object.objects) ? object.objects : []).forEach((child, index) => {
      warnFabricCharacterRanges(child, warnings, context, [...path, index]);
    });
  }


  function pptxLabelMetaForFabricObject(object) {
    const meta = object?.figureStudioPptxLabelMeta;
    if (!meta || meta.schema !== "figureStudio.pptxShapeLabel.v1") return null;
    const parentId = String(meta.parentObjectId || meta.parent_object_id || "");
    return parentId ? { ...meta, parentObjectId: parentId } : null;
  }

  function isPptxShapeLabelFabricObject(object) {
    return Boolean(pptxLabelMetaForFabricObject(object));
  }

  function fabricObjectId(object) {
    return String(object?.figureId || object?.id || "");
  }

  function supportedPptxShapeKindForFabric(object) {
    const type = String(object?.type || "").toLowerCase();
    if (type === "rect") return finite(object.rx, 0) > 0 || finite(object.ry, 0) > 0 ? "roundRect" : "rect";
    if (type === "ellipse" || type === "circle") return "ellipse";
    if (type === "triangle") return "triangle";
    return "";
  }

  function labelVerticalAlignForFabric(label) {
    const explicit = String(label?.verticalAlign || "").toLowerCase();
    if (explicit === "middle" || explicit === "center") return "middle";
    if (explicit === "bottom") return "bottom";
    if (explicit === "top") return "top";
    const origin = String(label?.originY || "top").toLowerCase();
    if (origin === "center") return "middle";
    if (origin === "bottom") return "bottom";
    return "top";
  }


  function unitScale(value) {
    return Math.abs(finite(value, 1) - 1) <= 0.001;
  }

  function fabricObjectExportable(object) {
    return Boolean(object) && object.visible !== false && object.excludeFromExport !== true;
  }

  function requiresNativeSvgRoot(object) {
    if (!fabricObjectExportable(object)) return false;
    if (String(object.figureType || "").toLowerCase() === "smartconnector" && Object.prototype.hasOwnProperty.call(object.smartConnectorMeta || {}, "geometrySpace")) {
      if (object.smartConnectorMeta.geometrySpace !== "object") throw new Error("This arrow uses unsupported coordinates and cannot be exported to PowerPoint.");
      return true;
    }
    return (object.objects || []).some(requiresNativeSvgRoot)
      || Boolean(object.clipPath && requiresNativeSvgRoot({ ...object.clipPath, visible: true, excludeFromExport: false }));
  }

  async function prepareNativeSvgProject(payload, options) {
    if (typeof options.resolveNativeSvgRoot !== "function") return payload;
    // The callback receives only detached JSON; native reconstruction and SVG
    // capture cannot mutate the live project or its frozen export descriptor.
    const prepared = JSON.parse(JSON.stringify(payload));
    const project = rawProject(prepared) || {};
    const pages = Array.isArray(project.deck?.pages) && project.deck.pages.length ? project.deck.pages
      : [{ id: "slide-1", artboard: project.artboard || defaultArtboardForProject(project), fabric: project.fabric }];
    for (let slideIndex = 0; slideIndex < pages.length; slideIndex += 1) {
      const page = pages[slideIndex];
      const fabric = page.fabric || (page.fabricRef === "project.fabric" || page.id === project.deck?.activePageId ? project.fabric : null) || { objects: [] };
      const replacements = [];
      for (let objectIndex = 0; objectIndex < (fabric.objects || []).length; objectIndex += 1) {
        const object = fabric.objects[objectIndex];
        if (!requiresNativeSvgRoot(object)) { replacements.push(object); continue; }
        const captured = await options.resolveNativeSvgRoot(object, { project, page, fabric, slideIndex, objectIndex });
        const bounds = captured?.bounds;
        if (!captured || !/^\s*<svg\b/i.test(captured.svg || "") || !bounds || ![bounds.left, bounds.top, bounds.width, bounds.height].every(Number.isFinite) || bounds.width <= 0 || bounds.height <= 0) {
          const error = new Error("The native arrow SVG could not be prepared. Export PDF or slide PNG instead.");
          error.code = "pptx-native-arrow-svg-required";
          throw error;
        }
        replacements.push({ type: "image", figureId: object.figureId || object.id || "", name: object.name || object.figureName || "Arrow artwork",
          left: bounds.left, top: bounds.top, width: bounds.width, height: bounds.height, originX: "left", originY: "top",
          scaleX: 1, scaleY: 1, angle: 0, skewX: 0, skewY: 0, flipX: false, flipY: false, opacity: 1,
          src: captured.svg, mediaType: "image/svg+xml", figureStudioPptxNativeSvg: { schema: "figureStudio.pptxNativeSvg.v1" } });
      }
      page.fabric = { ...fabric, objects: replacements };
      delete page.fabricRef;
    }
    if (Array.isArray(project.deck?.pages) && project.deck.pages.length) {
      const active = pages.find((page) => page.id === project.deck.activePageId) || pages[0];
      project.fabric = active.fabric;
    } else project.fabric = pages[0].fabric;
    return prepared;
  }

  function labelAnchorY(label, parentBounds, scaleToPoints) {
    const align = labelVerticalAlignForFabric(label);
    if (align === "middle") return parentBounds.y + parentBounds.height / 2;
    if (align === "bottom") return parentBounds.y + parentBounds.height;
    return parentBounds.y;
  }

  function labelOriginYCoordinate(label, scaleToPoints) {
    return finite(label?.top, 0) * scaleToPoints;
  }

  function scaledFabricTextStyles(styles = {}, scale = 1) {
    if (Array.isArray(styles)) {
      return styles.map((entry) => ({
        ...entry,
        style: {
          ...(entry?.style || {}),
          ...(entry?.style?.fontSize != null ? { fontSize: Math.max(1, finite(entry.style.fontSize, 16) * scale) } : {})
        }
      })).filter((entry) => entry && entry.style && Number(entry.end) > Number(entry.start));
    }
    const result = {};
    Object.entries(styles || {}).forEach(([lineIndex, line]) => {
      if (!line || typeof line !== "object") return;
      const lineResult = {};
      Object.entries(line).forEach(([charIndex, style]) => {
        if (!style || typeof style !== "object") return;
        lineResult[charIndex] = {
          ...style,
          ...(style.fontSize != null ? { fontSize: Math.max(1, finite(style.fontSize, 16) * scale) } : {})
        };
      });
      if (Object.keys(lineResult).length) result[lineIndex] = lineResult;
    });
    return result;
  }

  function textStyleFromPptxLabel(label, scaleToPoints, warnings, context) {
    const paragraphLayout = paragraphLayoutFromFabric(label, scaleToPoints);
    const fontScale = clamp(finite(paragraphLayout?.fontScale, 1), .01, 1);
    const styles = scaledFabricTextStyles(label.styles, scaleToPoints / fontScale);
    return {
      color: resolveSolidPaint(label.fill ?? label.textFill, warnings, context, "shape text color", "#000000"),
      fontFamily: label.fontFamily || "Arial",
      fontSize: Math.max(1, finite(label.fontSize, 16) * scaleToPoints / fontScale),
      bold: String(label.fontWeight || "").toLowerCase() === "bold" || Number(label.fontWeight) >= 600,
      italic: label.fontStyle === "italic",
      underline: label.underline === true,
      align: label.textAlign || "left",
      verticalAlign: labelVerticalAlignForFabric(label),
      wrap: "square",
      ...(paragraphLayout ? { paragraphLayout } : {}),
      ...(Object.keys(styles).length ? { styles } : {})
    };
  }

  function pptxShapeLabelPairForExport(parent, labelsByParentId, scaleToPoints, warnings, context) {
    const parentId = fabricObjectId(parent);
    const labels = parentId ? labelsByParentId.get(parentId) || [] : [];
    if (!labels.length) return null;
    const parentShape = supportedPptxShapeKindForFabric(parent);
    if (!parentShape || !fabricObjectExportable(parent)) return null;
    const parentBounds = fabricBounds(parent, scaleToPoints);
    let compatible = null;
    labels.forEach((label, index) => {
      if (compatible) return;
      const labelBounds = fabricBounds(label, scaleToPoints);
      const unsupported = [];
      if (Math.abs(finite(parent.angle, 0)) > 0.001 || parent.flipX === true || parent.flipY === true || !unitScale(parent.scaleX) || !unitScale(parent.scaleY) || Math.abs(finite(parent.skewX, 0)) > 0.001 || Math.abs(finite(parent.skewY, 0)) > 0.001) unsupported.push("parent-transform");
      if (Math.abs(finite(label.angle, 0)) > 0.001 || label.flipX === true || label.flipY === true || !unitScale(label.scaleX) || !unitScale(label.scaleY) || Math.abs(finite(label.skewX, 0)) > 0.001 || Math.abs(finite(label.skewY, 0)) > 0.001) unsupported.push("label-transform");
      if (Math.abs(finite(label.opacity, 1) - 1) > 0.001) unsupported.push("label-opacity");
      if (label.backgroundColor && String(label.backgroundColor).toLowerCase() !== "transparent") unsupported.push("label-background");
      if (Math.abs(finite(label.lineHeight, 1.16) - 1.16) > 0.001) unsupported.push("label-line-height");
      if (Math.abs(finite(label.charSpacing, 0)) > 0.001) unsupported.push("label-character-spacing");
      if (label.linethrough || label.overline) unsupported.push("label-decoration");
      if (Math.abs(parentBounds.x - labelBounds.x) > 1 || Math.abs(parentBounds.width - labelBounds.width) > 1) unsupported.push("label-horizontal-bounds");
      if (Math.abs(labelOriginYCoordinate(label, scaleToPoints) - labelAnchorY(label, parentBounds, scaleToPoints)) > 1) unsupported.push("label-anchor-position");
      if (labelBounds.y < parentBounds.y - 1 || labelBounds.y + labelBounds.height > parentBounds.y + parentBounds.height + 1) unsupported.push("label-outside-parent");
      const unsupportedRichText = fabricTextUnsupportedCharacterRangeReasons(label);
      if (unsupportedRichText.length) unsupported.push(...unsupportedRichText.map((reason) => `label-rich-text-${reason}`));
      if (unsupported.length) {
        warnings.add("pptx-shape-label-separate", "A PPTX-associated label could not be folded back into its parent PowerPoint shape without changing editable placement or formatting, so it was exported as a separate editable text box.", { ...context, parentObjectId: parentId, labelObjectId: fabricObjectId(label), reasons: unsupported, action: "preserved-separate" });
        return;
      }
      compatible = { label, labelIndex: index, text: String(label.text || ""), textStyle: textStyleFromPptxLabel(label, scaleToPoints, warnings, { ...context, objectName: label.name || label.figureName || "Shape label" }) };
    });
    if (compatible && labels.length > 1) {
      warnings.add("pptx-shape-label-multiple", "Multiple PPTX labels are attached to one shape. The first compatible label was folded into shape text and the rest remain separate editable text.", { ...context, parentObjectId: parentId, action: "approximated" });
    }
    return compatible;
  }

  function computePptxShapeLabelPairsForExport(fabricObjects, scaleToPoints, warnings, context) {
    const labelsByParentId = new Map();
    fabricObjects.forEach((object) => {
      if (!fabricObjectExportable(object)) return;
      const meta = pptxLabelMetaForFabricObject(object);
      if (!meta) return;
      if (!labelsByParentId.has(meta.parentObjectId)) labelsByParentId.set(meta.parentObjectId, []);
      labelsByParentId.get(meta.parentObjectId).push(object);
    });
    const pairByParentId = new Map();
    const consumedLabelIds = new Set();
    fabricObjects.forEach((object, objectIndex) => {
      const objectId = fabricObjectId(object);
      if (!objectId || isPptxShapeLabelFabricObject(object)) return;
      const pair = pptxShapeLabelPairForExport(object, labelsByParentId, scaleToPoints, warnings, { ...context, objectIndex, objectName: object.name || object.figureName || "Shape" });
      if (!pair?.label) return;
      pairByParentId.set(objectId, pair);
      consumedLabelIds.add(fabricObjectId(pair.label));
    });
    return { pairByParentId, consumedLabelIds };
  }

  function paragraphLayoutFromFabric(object, scaleToPoints) {
    const layout = scaledPptxParagraphLayout(object.figureStudioPptxTextMeta, scaleToPoints);
    if (layout && object.figureStudioListMeta?.paragraphs) layout.paragraphs = String(object.text || "").split("\n").map((_, index) => {
      const paragraph = layout.paragraphs[index] || { align: object.textAlign || "left", level: 0, marginLeft: 0, marginRight: 0, indent: 0, bullet: null };
      const item = object.figureStudioListMeta.paragraphs[index];
      return { ...paragraph, ...(item ? { level: item.level, bullet: { type: item.type, char: item.char || "•", autoType: item.autoType || "arabicPeriod", ...(item.startAt ? { startAt: item.startAt } : item.restart ? { startAt: 1 } : {}) } } : { bullet: null }) };
    });
    return layout;
  }

  function fabricGroupSupportsEditablePptx(object) {
    if (String(object?.type || "").toLowerCase() !== "group" || !Array.isArray(object.objects)) return false;
    const unsupportedAppearance = (member) => {
      if (member?.clipPath || member?.shadow || member?.mask || member?.eraser || (Array.isArray(member?.filters) && member.filters.length)) return true;
      if (Math.abs(finite(member?.opacity, 1) - 1) > 0.001 || Math.abs(finite(member?.skewX, 0)) > 0.001 || Math.abs(finite(member?.skewY, 0)) > 0.001) return true;
      const composite = String(member?.globalCompositeOperation || "source-over").toLowerCase();
      if (composite && composite !== "source-over") return true;
      const type = String(member?.type || "").toLowerCase();
      return type === "image" && (Math.abs(finite(member?.cropX, 0)) > 0.001 || Math.abs(finite(member?.cropY, 0)) > 0.001);
    };
    if (unsupportedAppearance(object)) return false;
    return object.objects.every((child) => {
      if (!fabricObjectExportable(child)) return true;
      if (unsupportedAppearance(child)) return false;
      const type = String(child.type || "").toLowerCase();
      const figureType = String(child.figureType || "").toLowerCase();
      if (["textbox", "i-text", "itext", "text", "rect", "ellipse", "circle", "triangle", "image", "line"].includes(type)) return true;
      if (type === "path" && ["smartconnector", "line", "arrow"].includes(figureType)) return true;
      return type === "group" && fabricGroupSupportsEditablePptx(child);
    });
  }

  function offsetCanonicalObject(object, offsetX, offsetY) {
    if (!object) return object;
    const shifted = { ...object };
    if (shifted.kind === "line" || shifted.kind === "connector") {
      shifted.x1 = finite(shifted.x1) + offsetX;
      shifted.y1 = finite(shifted.y1) + offsetY;
      shifted.x2 = finite(shifted.x2) + offsetX;
      shifted.y2 = finite(shifted.y2) + offsetY;
      if (shifted.smartConnectorMeta) {
        const shiftEndpoint = (endpoint) => endpoint ? { ...endpoint, point: endpoint.point ? { x: finite(endpoint.point.x) + offsetX, y: finite(endpoint.point.y) + offsetY } : endpoint.point } : endpoint;
        shifted.smartConnectorMeta = { ...shifted.smartConnectorMeta, start: shiftEndpoint(shifted.smartConnectorMeta.start), end: shiftEndpoint(shifted.smartConnectorMeta.end) };
      }
    } else {
      shifted.x = finite(shifted.x) + offsetX;
      shifted.y = finite(shifted.y) + offsetY;
    }
    return shifted;
  }

  function scaledPptxParagraphLayout(layout, scale = 1) {
    if (layout?.schema !== "figureStudio.pptxTextLayout.v1") return null;
    return { ...layout,
      insets: Object.fromEntries(["left", "top", "right", "bottom"].map(key => [key, finite(layout.insets?.[key]) * scale])),
      paragraphs: (layout.paragraphs || []).map(paragraph => ({ ...paragraph, marginLeft: finite(paragraph.marginLeft) * scale, marginRight: finite(paragraph.marginRight) * scale, indent: finite(paragraph.indent) * scale })) };
  }

  function fabricObjectToCanonical(object, scaleToPoints, warnings, context, options = {}) {
    if (!fabricObjectExportable(object)) return null;
    if (requiresNativeSvgRoot(object)) {
      const error = new Error("Native arrows require SVG preparation for PowerPoint export. Export through Figure Tool, or use PDF or slide PNG.");
      error.code = "pptx-native-arrow-svg-required";
      throw error;
    }
    const type = String(object.type || "").toLowerCase();
    const figureType = String(object.figureType || "").toLowerCase();
    const bounds = fabricBounds(object, scaleToPoints);
    const common = {
      id: object.figureId || object.id || "",
      sourceId: object.figureId || object.id || "",
      ...bounds,
      flipH: object.flipX === true || finite(object.scaleX, 1) < 0,
      flipV: object.flipY === true || finite(object.scaleY, 1) < 0,
      name: object.name || object.figureName || object.figureLabel || "",
      opacity: object.opacity == null ? 1 : object.opacity
    };
    warnFabricCharacterRanges(object, warnings, { ...context, objectName: common.name });
    if (["textbox", "i-text", "itext", "text"].includes(type)) {
      const wrap = type === "textbox" && figureType !== "connectorlabel" ? "square" : "none";
      const paragraphLayout = paragraphLayoutFromFabric(object, scaleToPoints);
      const fontScale = clamp(finite(paragraphLayout?.fontScale, 1), .01, 1);
      const fontSize = Math.max(1, finite(object.fontSize, 16) * scaleToPoints / fontScale);
      const styles = scaledFabricTextStyles(object.styles, scaleToPoints / fontScale);
      return { kind: "text", ...common, text: String(object.text || ""), color: resolveSolidPaint(object.fill ?? object.textFill, warnings, context, "text color", "#000000"), fontFamily: object.fontFamily || "Arial", fontSize, bold: String(object.fontWeight || "").toLowerCase() === "bold" || Number(object.fontWeight) >= 600, italic: object.fontStyle === "italic", underline: object.underline === true, linethrough: object.linethrough === true, align: object.textAlign || "left", verticalAlign: object.verticalAlign || "top", wrap, ...(paragraphLayout ? { paragraphLayout } : {}), ...(Object.keys(styles).length ? { styles } : {}) };
    }
    if (["smartconnector", "line", "arrow"].includes(figureType) || type === "line") {
      const endpoints = fabricLineEndpoints(object, scaleToPoints);
      const smartMeta = object.smartConnectorMeta ? {
        start: object.smartConnectorMeta.start ? { ...object.smartConnectorMeta.start } : null,
        end: object.smartConnectorMeta.end ? { ...object.smartConnectorMeta.end } : null,
        route: object.smartConnectorMeta.route || "straight",
        detached: Boolean(object.smartConnectorMeta.detached)
      } : null;
      return { kind: figureType === "smartconnector" ? "connector" : "line", id: common.id, sourceId: common.sourceId, ...endpoints, name: common.name, stroke: resolveSolidPaint(object.stroke, warnings, context, "line stroke", "#000000"), strokeWidth: Math.max(0.5, finite(object.strokeWidth, 1) * scaleToPoints), dash: object.lineDash || (Array.isArray(object.strokeDashArray) ? "dashed" : "solid"), startArrow: object.arrowStart || "none", endArrow: object.arrowEnd || object.arrowHead || "none", opacity: common.opacity, ...(smartMeta ? { smartConnectorMeta: smartMeta } : {}) };
    }
    const shapePaint = (shape) => {
      const pairedLabel = options.pptxShapeLabelPair || null;
      return {
        kind: "shape",
        shape,
        ...common,
        fill: resolveSolidPaint(object.fill, warnings, context, "shape fill", ""),
        stroke: resolveSolidPaint(object.stroke, warnings, context, "shape stroke", ""),
        strokeWidth: finite(object.strokeWidth, 0) * scaleToPoints,
        ...(pairedLabel && pairedLabel.text !== "" ? { text: pairedLabel.text, textStyle: pairedLabel.textStyle } : {})
      };
    };
    if (type === "rect") return shapePaint(finite(object.rx, 0) > 0 || finite(object.ry, 0) > 0 ? "roundRect" : "rect");
    if (type === "ellipse" || type === "circle") return shapePaint("ellipse");
    if (type === "triangle") return shapePaint("triangle");
    if (type === "image") {
      if (object.figureStudioPptxNativeSvg?.schema === "figureStudio.pptxNativeSvg.v1") warnings.add("native-arrow-root-as-svg", "An arrow or containing group was embedded as one SVG image. Its internal shapes, arrow endpoints and attachments are not independently editable in PowerPoint.", { ...context, objectName: common.name, action: "embedded-svg" });
      return { kind: "image", ...common, src: object.src || object.dataUrl || object._element?.src || "", mediaType: object.mediaType || "", alt: object.alt || object.name || "", ...(object.figureStudioPptxNativeSvg?.schema === "figureStudio.pptxNativeSvg.v1" ? { nativeSvgRoot: true } : {}) };
    }
    if (type === "group" && fabricGroupSupportsEditablePptx(object)) {
      const dimensions = fabricRawDimensions(object);
      const coordinateWidth = dimensions.width * scaleToPoints;
      const coordinateHeight = dimensions.height * scaleToPoints;
      const children = (object.objects || []).map((child, childIndex) => {
        const canonical = fabricObjectToCanonical(child, scaleToPoints, warnings, { ...context, nestedObjectPath: String(childIndex) });
        return offsetCanonicalObject(canonical, coordinateWidth / 2, coordinateHeight / 2);
      }).filter(Boolean);
      return { kind: "group", ...common, coordinateWidth, coordinateHeight, objects: children };
    }
    if (["path", "group", "polygon", "polyline"].includes(type)) return fabricVectorAsImage(object, bounds, warnings, context);
    warnings.add("fabric-object-unsupported", `A Figure Tool ${type || figureType || "unknown"} object was skipped during PPTX export.`, { ...context, action: "skipped" });
    return null;
  }

  function rawProject(payload) {
    return ["figureStudio.projectPayload.v1", "figureStudio.projectPayload.v2"].includes(payload?.schema) && payload.project ? payload.project : payload;
  }

  function defaultArtboardForProject(project) {
    return project?.document?.pageGeometry?.defaultArtboard || project?.artboard || { preset: "presentation-wide", widthIn: 13.333333, heightIn: 7.5 };
  }

  function projectToPresentation(payload, options = {}) {
    const warnings = warningCollector();
    const project = rawProject(payload) || {};
    const kind = String(project?.document?.kind || "figure").toLowerCase();
    if (kind !== "presentation" && options.allowFigureAsSingleSlide !== true) {
      const error = new Error("PPTX export is available for Presentation documents. Export a Figure as SVG, PNG, or PDF instead.");
      error.code = "pptx-presentation-required";
      throw error;
    }
    if (kind !== "presentation") warnings.add("figure-as-single-slide", "A Figure document was exported as one PPTX slide by explicit request.", { action: "approximated" });
    const defaultArtboard = defaultArtboardForProject(project);
    const widthIn = clamp(finite(defaultArtboard.widthIn, 13.333333), 1, 56);
    const heightIn = clamp(finite(defaultArtboard.heightIn, 7.5), 1, 56);
    const pages = Array.isArray(project?.deck?.pages) && project.deck.pages.length ? project.deck.pages : [{ id: "slide-1", label: "Slide 1", artboard: project.artboard || defaultArtboard, fabric: project.fabric }];
    const slides = pages.map((page, slideIndex) => {
      const artboard = page.artboard || defaultArtboard;
      const pageWidthIn = Math.max(0.01, finite(artboard.widthIn, widthIn));
      const pageHeightIn = Math.max(0.01, finite(artboard.heightIn, heightIn));
      if (Math.abs(pageWidthIn - widthIn) > 0.001 || Math.abs(pageHeightIn - heightIn) > 0.001) {
        warnings.add("per-page-geometry-scaled", "A slide with different page geometry was scaled into the presentation's uniform slide size.", { slideIndex, slideId: page.id, action: "scaled" });
      }
      const xScale = widthIn * POINTS_PER_INCH / (pageWidthIn * CSS_PIXELS_PER_INCH);
      const yScale = heightIn * POINTS_PER_INCH / (pageHeightIn * CSS_PIXELS_PER_INCH);
      const scale = Math.min(xScale, yScale);
      const fabric = page.fabric || (page.fabricRef === "project.fabric" || page.id === project?.deck?.activePageId ? project.fabric : null) || { objects: [] };
      const fabricObjects = Array.isArray(fabric?.objects) ? fabric.objects : [];
      const labelPairs = computePptxShapeLabelPairsForExport(fabricObjects, scale, warnings, { slideIndex, slideId: page.id });
      const objects = fabricObjects.map((object, objectIndex) => {
        const objectId = fabricObjectId(object);
        if (objectId && labelPairs.consumedLabelIds.has(objectId)) return null;
        if (isPptxShapeLabelFabricObject(object)) return fabricObjectToCanonical(object, scale, warnings, { slideIndex, slideId: page.id, objectIndex });
        return fabricObjectToCanonical(object, scale, warnings, { slideIndex, slideId: page.id, objectIndex }, { pptxShapeLabelPair: labelPairs.pairByParentId.get(objectId) || null });
      }).filter(Boolean);
      return { id: String(page.id || `slide-${slideIndex + 1}`), name: String(page.label || `Slide ${slideIndex + 1}`), notes: String(page.speakerNotes || ""), background: fabric.background || page.background || page.appearanceOverrides?.background || "", objects };
    });
    return {
      presentation: normalizePresentation({ widthPt: widthIn * POINTS_PER_INCH, heightPt: heightIn * POINTS_PER_INCH, title: options.title || project.title || "Figure Tool presentation", author: options.author || "Figure Tool", slides }, warnings),
      warnings: warnings.rows
    };
  }

  async function exportProject(payload, options = {}) {
    const prepared = await prepareNativeSvgProject(payload, options);
    const mapped = projectToPresentation(prepared, options);
    const result = await exportPresentation(mapped.presentation, options);
    result.warnings = [...mapped.warnings, ...result.warnings];
    result.projectSchema = rawProject(payload)?.schema || "legacy";
    return result;
  }

  function contentTypeMap(xml) {
    const defaults = new Map();
    const overrides = new Map();
    String(xml || "").replace(/<(?:\w+:)?Default\b([^>]*?)\/>/gi, (_, source) => {
      const attributes = parseAttributes(source);
      defaults.set(String(attributes.Extension || "").toLowerCase(), attributes.ContentType || "application/octet-stream");
      return _;
    });
    String(xml || "").replace(/<(?:\w+:)?Override\b([^>]*?)\/>/gi, (_, source) => {
      const attributes = parseAttributes(source);
      overrides.set(String(attributes.PartName || "").replace(/^\//, ""), attributes.ContentType || "application/octet-stream");
      return _;
    });
    return { defaults, overrides };
  }

  function mediaTypeForPath(path, types) {
    if (types.overrides.has(path)) return types.overrides.get(path);
    const extension = String(path || "").split(".").pop().toLowerCase();
    return types.defaults.get(extension) || ({ png: "image/png", jpg: "image/jpeg", jpeg: "image/jpeg", svg: "image/svg+xml" }[extension] || "application/octet-stream");
  }

  function themeColors(xml) {
    const colors = { dk1: "000000", lt1: "FFFFFF", dk2: "17283C", lt2: "F4F7FA", accent1: "2F78B7", accent2: "15887F", accent3: "A94E37", accent4: "7C3AED", accent5: "C27B16", accent6: "526678", hlink: "0563C1", folHlink: "954F72", tx1: "000000", tx2: "17283C", bg1: "FFFFFF", bg2: "F4F7FA" };
    Object.keys(colors).forEach((key) => {
      const match = String(xml || "").match(new RegExp(`<(?:\\w+:)?${key}\\b[^>]*>[\\s\\S]*?<(?:\\w+:)?(?:srgbClr|sysClr)\\b([^>]*)`, "i"));
      if (match) {
        const attributes = parseAttributes(match[1]);
        colors[key] = normalizeHexColor(attributes.val || attributes.lastClr, colors[key]);
      }
    });
    colors.fonts = {};
    for (const [role, tag] of [["major", "majorFont"], ["minor", "minorFont"]]) {
      const fontBlock = String(xml || "").match(new RegExp(`<(?:\\w+:)?${tag}\\b[^>]*>[\\s\\S]*?<\\/(?:\\w+:)?${tag}>`, "i"))?.[0] || "";
      colors.fonts[role] = firstTagAttributes(fontBlock, "latin").typeface || "Arial";
    }
    return colors;
  }

  function resolvedThemeFont(typeface, theme, fallback = "Arial") {
    const requested = String(typeface || "");
    if (requested === "+mj-lt") return theme.fonts?.major || fallback;
    if (requested === "+mn-lt") return theme.fonts?.minor || fallback;
    return requested && !requested.startsWith("+") ? requested : fallback;
  }

  function colorFromXml(xml, theme, fallback = "000000") {
    if (/<(?:\w+:)?noFill\b/i.test(String(xml || ""))) return "";
    const srgb = String(xml || "").match(/<(?:\w+:)?srgbClr\b([^>]*)/i);
    if (srgb) return normalizeHexColor(parseAttributes(srgb[1]).val, fallback);
    const scheme = String(xml || "").match(/<(?:\w+:)?schemeClr\b([^>]*)/i);
    if (scheme) return theme[parseAttributes(scheme[1]).val] || fallback;
    const system = String(xml || "").match(/<(?:\w+:)?sysClr\b([^>]*)/i);
    if (system) {
      const attributes = parseAttributes(system[1]);
      return normalizeHexColor(attributes.lastClr || attributes.val, fallback);
    }
    return fallback;
  }

  function alphaFromXml(xml) {
    const match = String(xml || "").match(/<(?:\w+:)?alpha\b([^>]*)/i);
    return match ? clamp(finite(parseAttributes(match[1]).val, 100000) / 100000, 0, 1) : 1;
  }

  function xfrmFromXml(xml) {
    const block = String(xml || "").match(/<(?:\w+:)?xfrm\b([^>]*)>[\s\S]*?<\/(?:\w+:)?xfrm>/i);
    if (!block) return { x: 0, y: 0, width: 1, height: 1, rotation: 0, flipH: false, flipV: false };
    const attributes = parseAttributes(block[1]);
    const off = firstTagAttributes(block[0], "off");
    const ext = firstTagAttributes(block[0], "ext");
    return { x: fromEmu(off.x), y: fromEmu(off.y), width: Math.max(0.01, fromEmu(ext.cx)), height: Math.max(0.01, fromEmu(ext.cy)), rotation: finite(attributes.rot) / 60000, flipH: attributes.flipH === "1" || attributes.flipH === "true", flipV: attributes.flipV === "1" || attributes.flipV === "true" };
  }

  function groupXfrmFromXml(xml) {
    const bounds = xfrmFromXml(xml);
    const block = String(xml || "").match(/<(?:\w+:)?xfrm\b[^>]*>[\s\S]*?<\/(?:\w+:)?xfrm>/i)?.[0] || "";
    const childOffset = firstTagAttributes(block, "chOff");
    const childExtent = firstTagAttributes(block, "chExt");
    return {
      ...bounds,
      childX: fromEmu(childOffset.x || 0),
      childY: fromEmu(childOffset.y || 0),
      coordinateWidth: Math.max(0.01, fromEmu(childExtent.cx || toEmu(bounds.width))),
      coordinateHeight: Math.max(0.01, fromEmu(childExtent.cy || toEmu(bounds.height)))
    };
  }

  function lineStyleFromXml(xml, theme) {
    const line = String(xml || "").match(/<(?:\w+:)?ln\b([^>]*)>[\s\S]*?<\/(?:\w+:)?ln>/i);
    if (!line || /<(?:\w+:)?noFill\b/i.test(line[0])) return { stroke: "", strokeWidth: 0, dash: "solid", startArrow: "none", endArrow: "none" };
    const attributes = parseAttributes(line[1]);
    const dash = firstTagAttributes(line[0], "prstDash").val || "solid";
    const head = firstTagAttributes(line[0], "headEnd").type || "none";
    const tail = firstTagAttributes(line[0], "tailEnd").type || "none";
    return { stroke: `#${colorFromXml(line[0], theme, "000000")}`, strokeWidth: fromEmu(attributes.w || 12700),
      strokeOpacity: alphaFromXml(line[0]), dash: /dot/i.test(dash) ? "dotted" : /dash/i.test(dash) ? "dashed" : "solid",
      startArrow: head === "oval" ? "dot" : head, endArrow: tail === "oval" ? "dot" : tail };
  }

  function pptxRunStyleFromXml(runBlock, theme, fallback = {}) {
    const source = String(runBlock || "");
    const properties = firstTagAttributes(source, "rPr");
    const defaultProperties = Object.keys(properties).length ? properties : firstTagAttributes(source, "defRPr");
    const latin = firstTagAttributes(source, "latin");
    const family = resolvedThemeFont(latin.typeface, theme, fallback.fontFamily || "Arial");
    const hasColor = /<(?:\w+:)?(?:solidFill|srgbClr|schemeClr|sysClr)\b/i.test(source);
    return {
      fontSize: clamp(finite(defaultProperties.sz, finite(fallback.fontSize, 18) * 100) / 100, 1, 400),
      fontFamily: family,
      bold: defaultProperties.b == null ? fallback.bold === true : defaultProperties.b === "1" || defaultProperties.b === "true",
      italic: defaultProperties.i == null ? fallback.italic === true : defaultProperties.i === "1" || defaultProperties.i === "true",
      underline: defaultProperties.u == null ? fallback.underline === true : Boolean(defaultProperties.u && defaultProperties.u !== "none"),
      linethrough: defaultProperties.strike == null ? fallback.linethrough === true : defaultProperties.strike === "sngStrike" || defaultProperties.strike === "dblStrike",
      color: hasColor ? `#${colorFromXml(source, theme, normalizeHexColor(fallback.color, "000000"))}` : fallback.color || "#000000"
    };
  }

  function firstRunPropertyBlock(xml, localName = "defRPr") {
    const source = String(xml || "");
    const paired = source.match(new RegExp(`<((?:\\w+:)?${localName})\\b[^>]*>[\\s\\S]*?<\\/\\1>`, "i"));
    if (paired) return paired[0];
    const selfClosing = source.match(new RegExp(`<(?:\\w+:)?${localName}\\b[^>]*/>`, "i"));
    return selfClosing ? selfClosing[0] : "";
  }

  function fabricCharStyleFromPptxRun(runStyle) {
    return {
      fill: runStyle.color,
      fontFamily: runStyle.fontFamily,
      fontSize: runStyle.fontSize,
      fontWeight: runStyle.bold ? "700" : "400",
      fontStyle: runStyle.italic ? "italic" : "normal",
      underline: runStyle.underline === true,
      linethrough: runStyle.linethrough === true
    };
  }

  function warnUnsupportedPptxTextRun(runBlock, warnings, context) {
    const properties = firstTagAttributes(runBlock || "", "rPr");
    const unsupported = [];
    if (properties.baseline && String(properties.baseline) !== "0") unsupported.push("baseline");
    if (properties.strike && !["noStrike", "sngStrike"].includes(properties.strike)) unsupported.push("strike");
    if (properties.cap && properties.cap !== "none") unsupported.push("capitalization");
    if (/<(?:\w+:)?(?:gradFill|pattFill|effectLst|effectDag|highlight)\b/i.test(runBlock || "")) unsupported.push("text-effects");
    if (unsupported.length) {
      warnings.add("pptx-text-run-effect-approximated", "A PowerPoint text run uses effects outside the editable PPTX v1 subset. The text remains editable; supported font, size, bold, italic, underline, and color spans were preserved.", { ...context, reasons: unsupported, action: "approximated" });
    }
  }

  function textFromBody(xml, theme, warnings, context, inheritedText = {}) {
    const paragraphs = tagBlocks(xml, "p");
    const paragraphBlocks = paragraphs.length ? paragraphs : [String(xml || "")];
    const defaultFallback = { fontSize: 18, fontFamily: "Arial", bold: false, italic: false, underline: false, color: "#000000" };
    const lines = [];
    const styles = {};
    const layoutParagraphs = [];
    let baseStyle = null;
    let firstParagraphProperties = {};
    paragraphBlocks.forEach((paragraph, paragraphIndex) => {
      const ownParagraphProperties = firstTagAttributes(paragraph, "pPr");
      if (/<(?:\w+:)?(?:lnSpc|spcBef|spcAft)\b/i.test(paragraph)) warnings.add("pptx-paragraph-spacing-approximated", "Explicit PowerPoint paragraph spacing is approximated by the editable text line spacing. Review the wrapped text and frame before export.", { ...context, action: "approximated" });
      if (/<(?:\w+:)?br\b/i.test(paragraph)) warnings.add("pptx-soft-break-as-paragraph", "PowerPoint soft line breaks are retained as editable lines. They export as separate paragraphs; review continuation spacing and indentation.", { ...context, action: "approximated" });
      const level = clamp(Math.trunc(finite(ownParagraphProperties.lvl)), 0, 8);
      let paragraphFallback = { ...defaultFallback };
      let paragraphProperties = {};
      let bullet = null;
      const applyBullet = properties => {
        if (/<(?:\w+:)?buNone\b/i.test(properties)) bullet = null;
        else if (/<(?:\w+:)?buChar\b/i.test(properties)) bullet = { type: "bullet", char: firstTagAttributes(properties, "buChar").char || "•" };
        else if (/<(?:\w+:)?buAutoNum\b/i.test(properties)) {
          const value = firstTagAttributes(properties, "buAutoNum");
          bullet = { type: "number", autoType: value.type || "arabicPeriod", ...(value.startAt ? { startAt: clamp(Math.trunc(finite(value.startAt, 1)), 1, 32767) } : {}) };
          if (bullet.autoType !== "arabicPeriod") warnings.add("pptx-list-numbering-approximated", "This numbering style is displayed as decimal numbers. Its original PowerPoint numbering style is retained for export.", { ...context, action: "approximated" });
        } else if (/<(?:\w+:)?buBlip\b/i.test(properties)) warnings.add("pptx-picture-bullet-omitted", "Picture bullets are omitted; their editable paragraph text is retained.", { ...context, action: "omitted" });
      };
      for (const source of [...(inheritedText.sources || []), xml]) {
        const list = tagBlocks(source, "lstStyle")[0] || source;
        const levelBlock = tagBlocks(list, `lvl${level + 1}pPr`)[0] || "";
        const inheritedParagraph = source === xml ? "" : tagBlocks(source, "pPr")[0] || "";
        for (const properties of [levelBlock, inheritedParagraph]) {
          applyBullet(properties);
          paragraphProperties = { ...paragraphProperties, ...firstTagAttributes(properties, properties === levelBlock ? `lvl${level + 1}pPr` : "pPr") };
          const defaultBlock = firstRunPropertyBlock(properties, "defRPr");
          if (defaultBlock) paragraphFallback = pptxRunStyleFromXml(defaultBlock, theme, paragraphFallback);
        }
      }
      paragraphProperties = { ...paragraphProperties, ...ownParagraphProperties };
      if (paragraphProperties.algn && !["l", "ctr", "r"].includes(paragraphProperties.algn)) warnings.add("pptx-paragraph-alignment-approximated", "This paragraph alignment is outside the qualified left, center and right alignment subset. Review its editable layout before export.", { ...context, action: "approximated" });
      applyBullet(tagBlocks(paragraph, "pPr")[0] || "");
      if (!paragraphIndex) firstParagraphProperties = paragraphProperties;
      const paragraphDefaultBlock = firstRunPropertyBlock(paragraph, "defRPr");
      const paragraphDefaultStyle = paragraphDefaultBlock ? pptxRunStyleFromXml(paragraphDefaultBlock, theme, paragraphFallback) : paragraphFallback;
      let lineText = "";
      let lineStyles = {};
      let firstParagraphLine = true;
      const flushLine = () => {
        const lineIndex = lines.length;
        lines.push(lineText);
        if (Object.keys(lineStyles).length) styles[lineIndex] = lineStyles;
        layoutParagraphs.push({ align: { ctr: "center", r: "right", just: "justify", l: "left" }[paragraphProperties.algn] || "left", level,
          marginLeft: Math.max(0, fromEmu(paragraphProperties.marL)), marginRight: Math.max(0, fromEmu(paragraphProperties.marR)), indent: fromEmu(paragraphProperties.indent),
          bullet: firstParagraphLine ? bullet : null });
        firstParagraphLine = false;
        lineText = "";
        lineStyles = {};
      };
      const expression = /(<(?:\w+:)?(?:r|fld)\b[\s\S]*?<\/(?:\w+:)?(?:r|fld)>)|<(?:\w+:)?br\b[^>]*(?:\/>|>[\s\S]*?<\/(?:\w+:)?br>)/gi;
      let match;
      let sawRun = false;
      while ((match = expression.exec(paragraph))) {
        if (!match[1]) {
          flushLine();
          continue;
        }
        sawRun = true;
        const runBlock = match[1];
        if (/<(?:\w+:)?fld\b/i.test(runBlock)) {
          warnings.add("pptx-field-cached-text", "A PowerPoint field was retained as its saved text. Dates and slide numbers will not update automatically.", { ...context, fieldType: firstTagAttributes(runBlock, "fld").type || "unknown", action: "preserved-static" });
        }
        warnUnsupportedPptxTextRun(runBlock, warnings, context);
        const runStyle = pptxRunStyleFromXml(runBlock, theme, paragraphDefaultStyle);
        if (!baseStyle) baseStyle = runStyle;
        const charStyle = fabricCharStyleFromPptxRun(runStyle);
        const runText = [];
        runBlock.replace(/<(?:\w+:)?t\b[^>]*>([\s\S]*?)<\/(?:\w+:)?t>/gi, (_, value) => {
          runText.push(xmlDecode(value));
          return _;
        });
        const value = runText.join("");
        const start = textGraphemes(lineText).length;
        lineText += value;
        for (let offset = 0; offset < textGraphemes(value).length; offset += 1) lineStyles[start + offset] = { ...charStyle };
      }
      if (!sawRun) {
        const pieces = [];
        paragraph.replace(/<(?:\w+:)?t\b[^>]*>([\s\S]*?)<\/(?:\w+:)?t>/gi, (_, value) => {
          pieces.push(xmlDecode(value));
          return _;
        });
        lineText = pieces.join("");
        if (lineText && !baseStyle) baseStyle = paragraphDefaultStyle;
      }
      flushLine();
    });
    baseStyle = baseStyle || defaultFallback;
    const paragraphProperties = firstParagraphProperties;
    const bodyProperties = Object.assign({}, ...(inheritedText.sources || []).map((source) => firstTagAttributes(source, "bodyPr")), firstTagAttributes(xml, "bodyPr"));
    const bodyBlocks = [...(inheritedText.sources || []), xml].map(source => tagBlocks(source, "bodyPr")[0] || "");
    const fitBody = bodyBlocks.filter(block => /<(?:\w+:)?(?:normAutofit|spAutoFit|noAutofit)\b/i.test(block)).at(-1) || "";
    const fit = firstTagAttributes(fitBody, "normAutofit");
    const percentage = (value, fallback) => value == null ? fallback : String(value).endsWith("%") ? finite(String(value).slice(0, -1), fallback * 100) / 100 : finite(value, fallback * 100000) / 100000;
    const fontScale = clamp(percentage(fit.fontScale, 1), .01, 1);
    const lineSpaceReduction = clamp(percentage(fit.lnSpcReduction, 0), 0, .9);
    const autoFit = /<(?:\w+:)?normAutofit\b/i.test(fitBody) ? "normal" : /<(?:\w+:)?spAutoFit\b/i.test(fitBody) ? "shape" : "none";
    if (autoFit !== "none") warnings.add("pptx-autofit-static-frame", "The saved PowerPoint text size is retained in an editable frame. After changing its text, review Text fits or Overset text and use Fit frame to content if needed; PowerPoint's automatic resizing is not recalculated here.", { ...context, action: "preserved-static" });
    if (fontScale !== 1) {
      baseStyle = { ...baseStyle, fontSize: baseStyle.fontSize * fontScale };
      Object.values(styles).forEach(line => Object.values(line).forEach(style => { style.fontSize *= fontScale; }));
    }
    const paragraphLayout = { schema: "figureStudio.pptxTextLayout.v1", paragraphs: layoutParagraphs,
      insets: { left: fromEmu(bodyProperties.lIns ?? 91440), top: fromEmu(bodyProperties.tIns ?? 45720), right: fromEmu(bodyProperties.rIns ?? 91440), bottom: fromEmu(bodyProperties.bIns ?? 45720) },
      wrap: bodyProperties.wrap === "none" ? "none" : "square", autoFit, fontScale, lineSpaceReduction };
    const verticalAlign = { t: "top", ctr: "middle", b: "bottom" }[String(bodyProperties.anchor || "t")] || "top";
    return { text: lines.join("\n"), fontSize: baseStyle.fontSize, fontFamily: baseStyle.fontFamily, bold: baseStyle.bold, italic: baseStyle.italic, underline: baseStyle.underline, linethrough: baseStyle.linethrough, align: { ctr: "center", r: "right", just: "justify", l: "left" }[paragraphProperties.algn] || "left", verticalAlign, color: baseStyle.color, paragraphLayout, ...(Object.keys(styles).length ? { styles } : {}) };
  }

  function parseShapeBlocks(xml) {
    const source = String(xml || "");
    const expression = /<(\/?)p:(sp|pic|cxnSp|graphicFrame|grpSp)\b[^>]*>/gi;
    const blocks = [];
    const stack = [];
    let match;
    while ((match = expression.exec(source))) {
      const closing = Boolean(match[1]);
      const tag = match[2];
      if (!closing) {
        stack.push({ tag, start: match.index, offset: match.index });
        continue;
      }
      const opened = stack.pop();
      if (!opened || opened.tag !== tag) continue;
      if (!stack.length) blocks.push({ tag, xml: source.slice(opened.start, expression.lastIndex), offset: opened.offset });
    }
    return blocks.sort((left, right) => left.offset - right.offset);
  }

  function groupChildrenXml(block) {
    const source = String(block || "");
    const start = source.search(/<\/p:grpSpPr\s*>/i);
    const end = source.search(/<\/p:grpSp\s*>\s*$/i);
    return start >= 0 && end > start ? source.slice(source.indexOf(">", start) + 1, end) : "";
  }

  function shapeTreeXml(xml) {
    return String(xml || "").match(/<p:spTree\b[\s\S]*?<\/p:spTree>/i)?.[0] || "";
  }

  function placeholderDescriptor(xml) {
    if (!/<p:ph\b/i.test(xml || "")) return null;
    const attributes = firstTagAttributes(xml, "ph");
    return { index: String(attributes.idx || "0"), type: attributes.type || "obj" };
  }

  function textPlaceholderInheritance(record, slideContext, inheritance, warnings, context) {
    const descriptor = record.tag === "sp" && !slideContext.inheritedLayer && placeholderDescriptor(record.xml);
    if (!descriptor || !["title", "ctrTitle", "subTitle", "body", "obj"].includes(descriptor.type)
        || !/<p:txBody\b/i.test(record.xml)) return null;
    const layoutCandidates = parseShapeBlocks(shapeTreeXml(inheritance.layoutXml)).filter((item) => item.tag === "sp" && placeholderDescriptor(item.xml)?.index === descriptor.index);
    const directTransform = record.xml.match(/<a:xfrm\b[^>]*>[\s\S]*?<\/a:xfrm>/i)?.[0] || "";
    const directOff = firstTagAttributes(directTransform, "off"), directExt = firstTagAttributes(directTransform, "ext");
    if (inheritance.layoutXml && layoutCandidates.length !== 1 && (directOff.x == null || directOff.y == null || directExt.cx == null || directExt.cy == null)) {
      warnings.add("text-placeholder-unresolved", "A text placeholder has no unambiguous matching layout and no complete position and size on the slide. Its text was not placed; review the original slide.", { ...context, placeholderIndex: descriptor.index, action: "skipped" });
      return { unresolved: true };
    }
    const layout = layoutCandidates.length === 1 ? layoutCandidates[0].xml : "";
    const layoutDescriptor = placeholderDescriptor(layout) || descriptor;
    const masterType = ["title", "ctrTitle"].includes(layoutDescriptor.type) ? "title"
      : ["body", "obj", "subTitle"].includes(layoutDescriptor.type) ? "body" : layoutDescriptor.type;
    const masterCandidates = parseShapeBlocks(shapeTreeXml(inheritance.masterXml)).filter((item) => {
      const placeholder = placeholderDescriptor(item.xml);
      return item.tag === "sp" && placeholder && (masterType === "title" ? ["title", "ctrTitle"].includes(placeholder.type) : placeholder.type === masterType);
    });
    const master = masterCandidates.length === 1 ? masterCandidates[0].xml : "";
    // Resolve only the explicit bounds chain. In particular never borrow the
    // first unrelated layout shape when an index is absent or ambiguous.
    const transforms = [master, layout, record.xml].map((source) => source.match(/<a:xfrm\b[^>]*>[\s\S]*?<\/a:xfrm>/i)?.[0] || "");
    let off = {}, ext = {}, attributes = {};
    transforms.forEach((transform) => {
      attributes = { ...attributes, ...firstTagAttributes(transform, "xfrm") };
      off = { ...off, ...firstTagAttributes(transform, "off") };
      ext = { ...ext, ...firstTagAttributes(transform, "ext") };
    });
    if (off.x == null || off.y == null || ext.cx == null || ext.cy == null) {
      warnings.add("text-placeholder-unresolved", "A text placeholder has no unambiguous position and size in its slide, layout, or master. Its text was not placed; review the original slide.", { ...context, placeholderIndex: descriptor.index, action: "skipped" });
      return { unresolved: true };
    }
    const bounds = { x: fromEmu(off.x), y: fromEmu(off.y), width: Math.max(.01, fromEmu(ext.cx)), height: Math.max(.01, fromEmu(ext.cy)), rotation: finite(attributes.rot) / 60000, flipH: ["1", "true"].includes(attributes.flipH), flipV: ["1", "true"].includes(attributes.flipV) };
    const styleTag = ["title", "ctrTitle"].includes(layoutDescriptor.type) ? "titleStyle" : layoutDescriptor.type === "body" || layoutDescriptor.type === "obj" ? "bodyStyle" : "otherStyle";
    const masterStyles = tagBlocks(inheritance.masterXml || "", styleTag)[0] || "";
    const sources = [masterStyles, master, layout].filter(Boolean);
    warnings.add("text-placeholder-materialized", "A title or body placeholder was imported as independent editable text using its supported slide, layout, and master settings. Layout changes will not update it.", { ...context, placeholderIndex: descriptor.index, action: "copied" });
    return { bounds, sources };
  }

  function showMasterShapes(xml, rootTag) {
    const setting = firstTagAttributes(xml, rootTag).showMasterSp;
    return setting !== "0" && setting !== "false";
  }

  function relatedPart(relationships, kind, entries) {
    const relationship = Array.from(relationships.values()).find((item) => !item.external && item.type.endsWith(`/${kind}`));
    return relationship && entries.has(relationship.target) ? relationship.target : "";
  }

  function simpleBackground(xml, theme, warnings, context) {
    const block = String(xml || "").match(/<p:bg\b[\s\S]*?<\/p:bg>/i)?.[0] || "";
    if (!block) return { present: false, color: "" };
    const solid = block.match(/<a:solidFill\b[\s\S]*?<\/a:solidFill>/i)?.[0] || "";
    if (solid && /<a:(?:srgbClr|schemeClr|sysClr)\b/i.test(solid) && !/<a:alpha\b/i.test(solid)) {
      return { present: true, color: `#${colorFromXml(solid, theme, "FFFFFF")}` };
    }
    warnings.add("background-unsupported", "A PowerPoint background uses a fill outside the solid-color subset. Review this slide's background after import.", { ...context, action: "skipped" });
    return { present: true, color: "" };
  }

  function pptxShapeRecordId(record, objectIndex) {
    const attributes = firstTagAttributes(record?.xml || "", "cNvPr");
    return String(attributes.id || objectIndex + 2);
  }

  function pptxCanonicalSourceId(record, objectIndex, slideContext = {}) {
    const attributes = firstTagAttributes(record?.xml || "", "cNvPr");
    const slideId = stablePptxObjectId(slideContext.slideId || `slide-${Number(slideContext.slideIndex || 0) + 1}`, "slide");
    if (slideContext.inheritedLayer) {
      // A shared part is materialized separately on every slide. Its OOXML shape
      // id (or a Figure Tool title) cannot be reused as a page-wide object id.
      const part = stablePptxObjectId(slideContext.sourcePart || slideContext.inheritedLayer, "part");
      return `pptx-${slideId}-${slideContext.inheritedLayer}-${part}-shape-${stablePptxObjectId(attributes.id || objectIndex + 2, `object-${objectIndex + 1}`)}`;
    }
    const embeddedIdentity = String(attributes.title || "").match(/^figureStudio:id=(.+)$/)?.[1];
    if (embeddedIdentity) return stablePptxObjectId(embeddedIdentity, `pptx-${record?.tag || "object"}`);
    return `pptx-${slideId}-shape-${stablePptxObjectId(attributes.id || objectIndex + 2, `object-${objectIndex + 1}`)}`;
  }

  function pptxImportedTargetDescriptor(record, objectIndex, entries, relationships, types, slideContext = {}, resolvedBounds = null) {
    if (!record || record.tag === "graphicFrame" || record.tag === "grpSp" || record.tag === "cxnSp") return false;
    const bounds = resolvedBounds || xfrmFromXml(record.xml || "");
    const common = { objectId: pptxCanonicalSourceId(record, objectIndex, slideContext), unsupportedConnectionTransform: Boolean(bounds.flipH || bounds.flipV || Math.abs(finite(bounds.rotation, 0)) > 0.001) };
    if (record.tag === "pic") {
      const blip = firstTagAttributes(record.xml, "blip");
      const relationshipId = blip["r:embed"] || blip.embed;
      const relationship = relationships.get(relationshipId);
      const media = relationship && !relationship.external ? entries.get(relationship.target) : null;
      const mediaType = media ? mediaTypeForPath(media.path, types) : "";
      return media && extensionForMediaType(mediaType) ? { ...common, shape: "rect" } : null;
    }
    const block = String(record.xml || "");
    if (/<(?:\w+:)?custGeom\b/i.test(block)) return false;
    const body = /<p:txBody\b[\s\S]*?<\/p:txBody>/i.test(block);
    const geometry = firstTagAttributes(block, "prstGeom").prst || "rect";
    const isTextBox = firstTagAttributes(block, "cNvSpPr").txBox === "1";
    if (isTextBox) return { ...common, shape: "rect" };
    const shape = { rect: "rect", roundRect: "roundRect", ellipse: "ellipse", triangle: "triangle" }[geometry];
    return shape && PPTX_CONNECTOR_SITES[shape] ? { ...common, shape } : null;
  }

  function pptxConnectionEndpoint(block, tag, objectIdByShapeId, warnings, context, fallbackPoint, fallbackAnchor) {
    const endpoint = firstTagAttributes(block, tag);
    const rawId = String(endpoint.id || "");
    if (!rawId) return { point: fallbackPoint, anchor: fallbackAnchor };
    const target = objectIdByShapeId.get(rawId);
    if (!target) {
      warnings.add("connector-attachment-unresolved", "A PowerPoint connector attachment target is outside the editable PPTX v1 subset, so Figure Tool imported the connector with its visible endpoint geometry only.", { ...context, endpoint: tag === "stCxn" ? "start" : "end", targetShapeId: rawId, action: "approximated" });
      return { point: fallbackPoint, anchor: fallbackAnchor };
    }
    if (target.unsupportedConnectionTransform) {
      warnings.add("connector-attachment-transform-unsupported", "A PowerPoint connector attachment target is flipped or rotated. Figure Tool imported that endpoint with visible geometry only because PPTX v1 does not remap transformed connection sites.", { ...context, endpoint: tag === "stCxn" ? "start" : "end", targetShapeId: rawId, targetShape: target.shape, action: "approximated" });
      return { point: fallbackPoint, anchor: fallbackAnchor };
    }
    const anchor = pptxConnectorPortForIndex(target.shape, endpoint.idx);
    if (!anchor) {
      warnings.add("connector-attachment-site-unsupported", "A PowerPoint connector used a target connection site that Figure Tool cannot map to a supported cardinal port, so that endpoint was imported with visible geometry only.", { ...context, endpoint: tag === "stCxn" ? "start" : "end", targetShapeId: rawId, targetShape: target.shape, siteIndex: String(endpoint.idx || ""), action: "approximated" });
      return { point: fallbackPoint, anchor: fallbackAnchor };
    }
    return { objectId: target.objectId, anchor, point: fallbackPoint };
  }

  function parseSlideObjects(xml, relationships, entries, types, theme, warnings, slideContext, inheritance = {}) {
    const objects = [];
    const inherited = Boolean(slideContext.inheritedLayer);
    const blocks = parseShapeBlocks(xml).filter((record, objectIndex) => {
      if (!inherited) return true;
      const context = { ...slideContext, objectIndex, objectName: firstTagAttributes(record.xml, "cNvPr").name || `${record.tag} ${objectIndex + 1}` };
      if (/<p:ph\b/i.test(record.xml) && record.tag !== "grpSp") {
        warnings.add("inherited-placeholder-skipped", "Master/layout placeholder prompts were not copied. Review titles, dates, and slide numbers on imported slides.", { ...slideContext, action: "skipped" });
        return false;
      }
      if (/<a:fld\b/i.test(record.xml) && record.tag !== "grpSp") {
        warnings.add("inherited-field-skipped", "PowerPoint master/layout fields were not copied because their displayed values can vary by slide.", { ...slideContext, action: "skipped" });
        return false;
      }
      if (/<a:(?:gradFill|pattFill|effectDag|glow|reflection|softEdge)\b/i.test(record.xml) && record.tag !== "grpSp") {
        warnings.add("inherited-appearance-skipped", "Master/layout artwork with an advanced fill or effect was not copied.", { ...context, action: "skipped" });
        return false;
      }
      if (record.tag === "pic" && /<a:(?:srcRect|tile|alphaModFix)\b/i.test(record.xml)) {
        warnings.add("inherited-image-effect-skipped", "A cropped or effected master/layout image was not copied; its appearance needs review.", { ...context, action: "skipped" });
        return false;
      }
      return true;
    });
    const objectIdByShapeId = new Map();
    const textInheritanceByRecord = new Map();
    blocks.forEach((record, objectIndex) => {
      const shapeId = pptxShapeRecordId(record, objectIndex);
      const objectName = firstTagAttributes(record.xml, "cNvPr").name || `${record.tag} ${objectIndex + 1}`;
      const placeholder = textPlaceholderInheritance(record, slideContext, inheritance, warnings, { ...slideContext, objectIndex, objectName });
      textInheritanceByRecord.set(record, placeholder);
      const target = placeholder?.unresolved ? null : pptxImportedTargetDescriptor(record, objectIndex, entries, relationships, types, slideContext, placeholder?.bounds);
      if (shapeId && target) objectIdByShapeId.set(shapeId, target);
    });
    blocks.forEach((record, objectIndex) => {
      const context = { ...slideContext, objectIndex };
      const block = record.xml;
      const name = firstTagAttributes(block, "cNvPr").name || `${record.tag} ${objectIndex + 1}`;
      const sourceId = pptxCanonicalSourceId(record, objectIndex, slideContext);
      if (record.tag === "graphicFrame") {
        const kind = /<a:tbl\b/i.test(block) ? "table" : /chart/i.test(block) ? "chart" : /dgm:/i.test(block) ? "SmartArt" : "graphic frame";
        warnings.add(`${kind.toLowerCase().replace(/\s+/g, "-")}-unsupported`, `${kind} content is outside PPTX v1 and was skipped.`, { ...context, objectName: name, action: "skipped" });
        return;
      }
      if (record.tag === "grpSp") {
        const transformBlock = block.match(/<p:grpSpPr\b[^>]*>[\s\S]*?<\/p:grpSpPr>/i)?.[0] || "";
        const groupBounds = groupXfrmFromXml(transformBlock);
        const children = parseSlideObjects(groupChildrenXml(block), relationships, entries, types, theme, warnings, { ...slideContext, groupPath: [...(slideContext.groupPath || []), objectIndex] }, inheritance);
        if (!children.length) {
          warnings.add("group-empty-after-import", "A PowerPoint group had no members in the editable subset.", { ...context, objectName: name, action: "skipped" });
          return;
        }
        const childX = groupBounds.childX;
        const childY = groupBounds.childY;
        const normalizedChildren = children.map((child) => offsetCanonicalObject(child, -childX, -childY));
        objects.push({ kind: "group", sourceId, x: groupBounds.x, y: groupBounds.y, width: groupBounds.width, height: groupBounds.height, rotation: groupBounds.rotation, flipH: groupBounds.flipH, flipV: groupBounds.flipV, coordinateWidth: groupBounds.coordinateWidth, coordinateHeight: groupBounds.coordinateHeight, name, objects: normalizedChildren });
        return;
      }
      const placeholder = textInheritanceByRecord.get(record);
      if (placeholder?.unresolved) return;
      const bounds = placeholder?.bounds || xfrmFromXml(block);
      if (record.tag === "pic") {
        const blip = firstTagAttributes(block, "blip");
        const relationshipId = blip["r:embed"] || blip.embed;
        const relationship = relationships.get(relationshipId);
        const media = relationship && !relationship.external ? entries.get(relationship.target) : null;
        if (!media) {
          warnings.add("image-source-missing", "An image was skipped because its embedded media part was unavailable.", { ...context, objectName: name, action: "skipped" });
          return;
        }
        if (/<a:srcRect\b/i.test(block)) warnings.add("image-crop-not-preserved", "A cropped image was imported without its crop window.", { ...context, objectName: name, action: "approximated" });
        const mediaType = mediaTypeForPath(media.path, types);
        if (!extensionForMediaType(mediaType)) {
          warnings.add("image-format-unsupported", `An embedded ${mediaType} image was skipped.`, { ...context, objectName: name, action: "skipped" });
          return;
        }
        const intrinsic = intrinsicImageDimensions(media.bytes, mediaType);
        objects.push({ kind: "image", sourceId, ...bounds, name, mediaType, dataUrl: `data:${mediaType};base64,${bytesToBase64(media.bytes)}`, alt: firstTagAttributes(block, "cNvPr").descr || "",
          ...(intrinsic ? { intrinsicWidth: intrinsic.width, intrinsicHeight: intrinsic.height } : {}) });
        return;
      }
      const line = lineStyleFromXml(block, theme);
      if (record.tag === "cxnSp") {
        const connectorGeometry = firstTagAttributes(block, "prstGeom").prst || "line";
        if (!["line", "straightConnector1"].includes(connectorGeometry)) {
          warnings.add("connector-imported-straight", `A ${connectorGeometry} connector was imported as a straight connector.`, { ...context, objectName: name, action: "approximated" });
        }
        let x1 = bounds.x;
        let y1 = bounds.y;
        let x2 = bounds.x + bounds.width;
        let y2 = bounds.y + bounds.height;
        if (bounds.flipH) [x1, x2] = [x2, x1];
        if (bounds.flipV) [y1, y2] = [y2, y1];
        const start = pptxConnectionEndpoint(block, "stCxn", objectIdByShapeId, warnings, context, { x: x1, y: y1 }, "right");
        const end = pptxConnectionEndpoint(block, "endCxn", objectIdByShapeId, warnings, context, { x: x2, y: y2 }, "left");
        objects.push({ kind: "connector", sourceId, x1, y1, x2, y2, name, ...line,
          opacity: line.strokeOpacity, smartConnectorMeta: { start, end, route: "straight", detached: !(start.objectId && end.objectId) } });
        return;
      }
      if (/<(?:\w+:)?custGeom\b/i.test(block)) {
        warnings.add("freeform-path-unsupported", "A custom/freeform PowerPoint path was skipped.", { ...context, objectName: name, action: "skipped" });
        return;
      }
      const geometry = firstTagAttributes(block, "prstGeom").prst || "rect";
      const body = block.match(/<p:txBody\b[\s\S]*?<\/p:txBody>/i)?.[0] || "";
      const text = body ? textFromBody(body, theme, warnings, { ...context, objectName: name }, placeholder || {}) : null;
      const isTextBox = firstTagAttributes(block, "cNvSpPr").txBox === "1";
      const shapeProperties = tagBlocks(block, "spPr")[0] || "";
      const ordinaryTextPlaceholder = placeholder && geometry === "rect" && !/<a:(?:solidFill|gradFill|pattFill|ln)\b/i.test(shapeProperties);
      if (isTextBox || ordinaryTextPlaceholder || (!geometry && text)) {
        objects.push({ kind: "text", sourceId, ...bounds, name, ...(text || { text: "" }) });
      }
      else if (geometry === "line") {
        objects.push({ kind: "line", sourceId, x1: bounds.x, y1: bounds.y, x2: bounds.x + bounds.width, y2: bounds.y + bounds.height, name, ...line, opacity: line.strokeOpacity });
      } else {
        const shape = { rect: "rect", roundRect: "roundRect", ellipse: "ellipse", triangle: "triangle" }[geometry];
        if (!shape) {
          warnings.add("preset-shape-unsupported", `The PowerPoint ${geometry} shape was skipped.`, { ...context, objectName: name, action: "skipped" });
          return;
        }
        const shapeProperties = block.match(/<p:spPr\b[^>]*>[\s\S]*?<\/p:spPr>/i)?.[0] || "";
        const fillRegion = shapeProperties.split(/<(?:\w+:)?ln\b/i)[0];
        const complexFill = fillRegion.match(/<(?:\w+:)?(gradFill|pattFill)\b[\s\S]*?<\/(?:\w+:)?\1>/i);
        const fillBlock = complexFill?.[0] || fillRegion.match(/<(?:\w+:)?solidFill\b[\s\S]*?<\/(?:\w+:)?solidFill>|<(?:\w+:)?noFill\b[^>]*\/>/i)?.[0] || "";
        let fill = fillBlock ? `#${colorFromXml(fillBlock, theme, "FFFFFF")}` : "";
        if (complexFill) {
          const kind = complexFill[1] === "gradFill" ? "gradient" : "pattern";
          const hasSolidCandidate = /<(?:\w+:)?(?:srgbClr|schemeClr|sysClr)\b/i.test(fillBlock);
          if (!hasSolidCandidate) fill = "";
          warnings.add(
            `${kind}-shape-fill-${hasSolidCandidate ? "flattened" : "omitted"}`,
            hasSolidCandidate
              ? `A ${kind} shape fill was reduced to its first supported solid color.`
              : `A ${kind} shape fill could not be represented and was omitted.`,
            { ...context, objectName: name, paintRole: "shape fill", action: hasSolidCandidate ? "flattened" : "omitted" }
          );
        }
        objects.push({ kind: "shape", sourceId, shape, ...bounds, name, fill, opacity: alphaFromXml(fillBlock), ...line, ...(text && text.text ? { text: text.text, textStyle: text } : {}) });
      }
    });
    return objects;
  }

  function plainNotesFromXml(xml) {
    const bodyShapes = tagBlocks(xml, "sp").filter((block) => /<(?:\w+:)?ph\b[^>]*type=["']body["']/i.test(block));
    const source = bodyShapes.length ? bodyShapes.join("") : String(xml || "");
    const text = [];
    source.replace(/<(?:\w+:)?t\b[^>]*>([\s\S]*?)<\/(?:\w+:)?t>/gi, (_, value) => {
      text.push(xmlDecode(value));
      return _;
    });
    return text.join("\n").trim();
  }

  function slideOrderFromPresentation(xml, relationships) {
    const result = [];
    const expression = /<(?:\w+:)?sldId\b([^>]*?)(?:\/>|>)/gi;
    let match;
    while ((match = expression.exec(String(xml || "")))) {
      const attributes = parseAttributes(match[1]);
      const id = attributes["r:id"] || attributes.id;
      const relationship = relationships.get(id);
      if (relationship?.target && /\/slide\d+\.xml$/i.test(relationship.target)) result.push(relationship.target);
    }
    return result;
  }

  function scanUnsupportedPackage(entries, warnings) {
    const paths = new Set(entries.keys());
    const checks = [
      [/vbaProject\.bin$/i, "macros-unsupported", "Macros are not imported."],
      [/embeddings\//i, "embedded-files-unsupported", "Embedded files and workbooks are not imported."],
      [/comments\//i, "comments-unsupported", "Comments and collaboration metadata are not imported."],
      [/media\/.+\.(mp3|mp4|wav|m4a|avi|mov)$/i, "media-unsupported", "Audio and video are not imported."],
      [/model3d\//i, "3d-model-unsupported", "3D models are not imported."]
    ];
    checks.forEach(([pattern, code, message]) => {
      if (Array.from(paths).some((path) => pattern.test(path))) warnings.add(code, message, { action: "skipped" });
    });
  }

  async function importPptx(input, options = {}) {
    const warnings = warningCollector();
    const zipEntries = await readZipEntries(input, options);
    const entries = xmlEntryMap(zipEntries);
    scanUnsupportedPackage(entries, warnings);
    const presentationEntry = entries.get("ppt/presentation.xml");
    const relationshipEntry = entries.get("ppt/_rels/presentation.xml.rels");
    if (!presentationEntry || !relationshipEntry) throw new Error("The PPTX package does not contain a readable presentation document.");
    const presentationText = bytesToText(presentationEntry.bytes);
    const presentationRelationships = relationshipsFromXml(bytesToText(relationshipEntry.bytes), "ppt/presentation.xml");
    const size = firstTagAttributes(presentationText, "sldSz");
    const widthPt = clamp(fromEmu(size.cx || 12192000), 72, 56 * POINTS_PER_INCH);
    const heightPt = clamp(fromEmu(size.cy || 6858000), 72, 56 * POINTS_PER_INCH);
    const types = contentTypeMap(bytesToText(entries.get("[Content_Types].xml")?.bytes || new Uint8Array()));
    const themeRelationship = Array.from(presentationRelationships.values()).find((relationship) => !relationship.external && relationship.type.endsWith("/theme"));
    const fallbackThemePath = themeRelationship?.target || "ppt/theme/theme1.xml";
    const partXml = (path) => bytesToText(entries.get(path)?.bytes || new Uint8Array());
    const partRelationships = (path) => relationshipsFromXml(bytesToText(entries.get(relationshipPartPath(path))?.bytes || new Uint8Array()), path);
    const slidePaths = slideOrderFromPresentation(presentationText, presentationRelationships);
    if (!slidePaths.length) throw new Error("The PPTX presentation contains no readable slides.");
    let copiedInherited = 0;
    const slides = slidePaths.map((path, slideIndex) => {
      const slideEntry = entries.get(path);
      if (!slideEntry) {
        warnings.add("slide-part-missing", `Slide ${slideIndex + 1} is missing from the package.`, { slideIndex, action: "skipped" });
        return null;
      }
      const xml = bytesToText(slideEntry.bytes);
      const rels = partRelationships(path);
      const context = { slideIndex, slideId: `slide-${slideIndex + 1}` };
      const layoutPath = relatedPart(rels, "slideLayout", entries);
      const layoutXml = partXml(layoutPath);
      const layoutRels = layoutPath ? partRelationships(layoutPath) : new Map();
      const masterPath = relatedPart(layoutRels, "slideMaster", entries);
      const masterXml = partXml(masterPath);
      const masterRels = masterPath ? partRelationships(masterPath) : new Map();
      const masterThemePath = relatedPart(masterRels, "theme", entries);
      const theme = themeColors(partXml(masterThemePath || fallbackThemePath));
      if (!layoutPath) warnings.add("slide-layout-missing", "The slide layout could not be read; only artwork drawn directly on the slide was imported.", { ...context, action: "review" });
      else if (!masterPath) warnings.add("slide-master-missing", "The layout's slide master could not be read; layout and direct slide artwork were imported where supported.", { ...context, action: "review" });
      if (/<p:timing\b/i.test(xml)) warnings.add("animations-unsupported", "Slide animations are not imported.", { slideIndex, action: "skipped" });
      if (/<p:transition\b/i.test(xml)) warnings.add("transitions-unsupported", "Slide transitions are not imported.", { slideIndex, action: "skipped" });
      if (/<p:oleObj\b/i.test(xml)) warnings.add("ole-unsupported", "An OLE object was not imported.", { slideIndex, action: "skipped" });
      if (/<a:(?:gradFill|pattFill|effectDag)\b/i.test(xml) || /<a:effectLst\b[^>]*>\s*<a:/i.test(xml)) {
        warnings.add("advanced-appearance-flattened", "A gradient, pattern, or advanced effect was reduced to the supported solid appearance where possible.", { slideIndex, action: "flattened" });
      }
      const notesRelationship = Array.from(rels.values()).find((relationship) => relationship.type.endsWith("/notesSlide"));
      const notes = notesRelationship && entries.has(notesRelationship.target) ? plainNotesFromXml(bytesToText(entries.get(notesRelationship.target).bytes)) : "";
      let background = "";
      for (const [part, sourcePart] of [[xml, path], [layoutXml, layoutPath], [masterXml, masterPath]]) {
        const candidate = simpleBackground(part, theme, warnings, { ...context, sourcePart });
        if (candidate.present) { background = candidate.color; break; }
      }
      const inherited = [];
      if (showMasterShapes(xml, "sld")) {
        if (masterPath && showMasterShapes(layoutXml, "sldLayout")) {
          inherited.push(...parseSlideObjects(shapeTreeXml(masterXml), masterRels, entries, types, theme, warnings,
            { ...context, inheritedLayer: "master", sourcePart: masterPath }));
        }
        if (layoutPath) inherited.push(...parseSlideObjects(shapeTreeXml(layoutXml), layoutRels, entries, types, theme, warnings,
          { ...context, inheritedLayer: "layout", sourcePart: layoutPath }));
      }
      copiedInherited += inherited.length;
      const direct = parseSlideObjects(shapeTreeXml(xml), rels, entries, types, theme, warnings, context, { layoutXml, masterXml });
      return { id: context.slideId, name: `Slide ${slideIndex + 1}`, notes, background, objects: [...inherited, ...direct] };
    }).filter(Boolean);
    if (copiedInherited > 0) {
      warnings.add("master-layout-flattened", "Supported master and layout artwork was copied onto each slide as independent editable objects. Later edits to a shared PowerPoint master will not update those copies.", { action: "copied" });
    }
    if (slidePaths.some((path) => relatedPart(partRelationships(path), "slideLayout", entries))) {
      warnings.add("master-layout-not-preserved", "The PowerPoint master and layout definitions are not retained. Review copied artwork, placeholders, and effects on every imported slide.", { action: "review" });
    }
    const presentation = normalizePresentation({ widthPt, heightPt, title: "Imported presentation", author: "", slides }, warnings);
    const project = presentationToFigureStudioProject(presentation, { sourceFilename: options.sourceFilename || input?.name || "presentation.pptx" });
    return { schema: "figureStudio.pptxImportResult.v1", status: "completed", presentation, project, slideCount: presentation.slides.length, warnings: warnings.rows, compatibility: COMPATIBILITY };
  }

  function canonicalObjectToFabric(object, pointsToPixels) {
    const id = object.sourceId || object.id || object.figureId
      ? stablePptxObjectId(object.sourceId || object.id || object.figureId, `pptx-${object.kind || "object"}`)
      : fallbackPptxObjectId(object.kind || "object");
    const common = { figureId: id, name: object.name || "Imported PPTX object", figureName: object.name || "Imported PPTX object", left: finite(object.x) * pointsToPixels, top: finite(object.y) * pointsToPixels, angle: finite(object.rotation), opacity: object.opacity == null ? 1 : object.opacity, visible: true, selectable: true, evented: true, originX: object.originX || "left", originY: object.originY || "top", scaleX: 1, scaleY: 1,
      ...(["text", "shape", "image"].includes(object.kind) ? { flipX: object.flipH === true, flipY: object.flipV === true } : {}) };
    if (object.kind === "text") {
      const styles = scaledFabricTextStyles(object.styles, pointsToPixels);
      const paragraphLayout = scaledPptxParagraphLayout(object.paragraphLayout, pointsToPixels);
      const width = Math.max(1, finite(object.width) * pointsToPixels), height = Math.max(1, finite(object.height) * pointsToPixels);
      const metadata = paragraphLayout ? { figureStudioPptxTextMeta: paragraphLayout,
        figureStudioAreaTextMeta: { schema: "figureStudio.areaText.v1", authored: true, frame_width: width, frame_height: height, auto_height: false },
        figureStudioListMeta: { schema: "figureStudio.paragraphLists.v1", last_text: String(object.text || ""), paragraphs: paragraphLayout.paragraphs.map(paragraph => paragraph.bullet ? { ...paragraph.bullet, level: paragraph.level, restart: Boolean(paragraph.bullet.startAt) } : null) } } : {};
      return { type: "Textbox", version: "7.3.1", ...common, figureType: "text", width, height, text: String(object.text || ""), fill: object.color || "#000000", fontFamily: object.fontFamily || "Arial", fontSize: Math.max(1, finite(object.fontSize, 18) * pointsToPixels), fontWeight: object.bold ? "700" : "400", fontStyle: object.italic ? "italic" : "normal", underline: object.underline === true, linethrough: object.linethrough === true, textAlign: object.align || "left", verticalAlign: object.verticalAlign || "top", lineHeight: 1.16 * (1 - finite(paragraphLayout?.lineSpaceReduction)), strokeWidth: 0, ...metadata, ...(Object.keys(styles).length ? { styles } : {}) };
    }
    if (object.kind === "shape") {
      const base = { version: "7.3.1", ...common, figureType: object.shape, width: Math.max(1, finite(object.width) * pointsToPixels), height: Math.max(1, finite(object.height) * pointsToPixels), fill: object.fill || "", stroke: object.stroke || "", strokeWidth: finite(object.strokeWidth) * pointsToPixels };
      if (object.shape === "ellipse") return { type: "Ellipse", ...base, rx: base.width / 2, ry: base.height / 2 };
      if (object.shape === "triangle") return { type: "Triangle", ...base };
      return { type: "Rect", ...base, rx: object.shape === "roundRect" ? Math.min(base.width, base.height) * 0.08 : 0, ry: object.shape === "roundRect" ? Math.min(base.width, base.height) * 0.08 : 0 };
    }
    if (object.kind === "line" || object.kind === "connector") {
      const x1 = finite(object.x1) * pointsToPixels;
      const y1 = finite(object.y1) * pointsToPixels;
      const x2 = finite(object.x2) * pointsToPixels;
      const y2 = finite(object.y2) * pointsToPixels;
      const meta = object.kind === "connector" ? object.smartConnectorMeta || { start: { point: { x: object.x1, y: object.y1 }, anchor: "right" }, end: { point: { x: object.x2, y: object.y2 }, anchor: "left" }, route: "straight", detached: true } : null;
      const left = Math.min(x1, x2);
      const top = Math.min(y1, y2);
      const width = Math.max(1, Math.abs(x2 - x1));
      const height = Math.max(1, Math.abs(y2 - y1));
      if (meta) {
        const scalePoint = (point) => point && Number.isFinite(Number(point.x)) && Number.isFinite(Number(point.y)) ? { x: Number(point.x) * pointsToPixels, y: Number(point.y) * pointsToPixels } : null;
        const scaledMeta = {
          ...meta,
          start: { ...(meta.start || {}), point: scalePoint(meta.start?.point) || { x: x1, y: y1 } },
          end: { ...(meta.end || {}), point: scalePoint(meta.end?.point) || { x: x2, y: y2 } }
        };
        return { type: "Path", version: "7.3.1", figureId: id, name: object.name || "Imported connector", figureName: object.name || "Imported connector", figureType: "smartConnector", originX: "left", originY: "top", left, top, width, height, pathOffset: { x: width / 2, y: height / 2 }, path: [["M", x1 - left, y1 - top], ["L", x2 - left, y2 - top]], fill: "", stroke: object.stroke || "#000000", strokeWidth: Math.max(0.5, finite(object.strokeWidth, 1) * pointsToPixels), strokeDashArray: object.dash === "dashed" ? [8, 5] : object.dash === "dotted" ? [2, 4] : null, arrowStart: object.startArrow || "none", arrowEnd: object.endArrow || "none", arrowHead: object.endArrow || "none", opacity: clamp(object.opacity == null ? 1 : object.opacity, 0, 1), visible: true, selectable: true, evented: true, objectCaching: false, smartConnectorMeta: scaledMeta };
      }
      return { type: "Line", version: "7.3.1", figureId: id, name: object.name || "Imported connector", figureName: object.name || "Imported connector", figureType: "line", left, top, x1: x1 - left, y1: y1 - top, x2: x2 - left, y2: y2 - top, width, height, fill: "", stroke: object.stroke || "#000000", strokeWidth: Math.max(0.5, finite(object.strokeWidth, 1) * pointsToPixels), strokeDashArray: object.dash === "dashed" ? [8, 5] : object.dash === "dotted" ? [2, 4] : null, arrowStart: object.startArrow || "none", arrowEnd: object.endArrow || "none", opacity: clamp(object.opacity == null ? 1 : object.opacity, 0, 1), visible: true, selectable: true, evented: true };
    }
    if (object.kind === "group") {
      const coordinateWidth = Math.max(0.01, finite(object.coordinateWidth, object.width));
      const coordinateHeight = Math.max(0.01, finite(object.coordinateHeight, object.height));
      const centerX = coordinateWidth * pointsToPixels / 2;
      const centerY = coordinateHeight * pointsToPixels / 2;
      const children = (object.objects || []).flatMap((child) => canonicalObjectToFabricObjects(child, pointsToPixels)).map((child) => {
        const shiftEndpoint = (endpoint) => endpoint ? { ...endpoint, point: endpoint.point ? { x: finite(endpoint.point.x) - centerX, y: finite(endpoint.point.y) - centerY } : endpoint.point } : endpoint;
        return {
          ...child,
          left: finite(child.left) - centerX,
          top: finite(child.top) - centerY,
          ...(child.smartConnectorMeta ? { smartConnectorMeta: { ...child.smartConnectorMeta, start: shiftEndpoint(child.smartConnectorMeta.start), end: shiftEndpoint(child.smartConnectorMeta.end) } } : {})
        };
      });
      return {
        type: "Group",
        version: "7.3.1",
        ...common,
        figureType: "pptxGroup",
        width: coordinateWidth * pointsToPixels,
        height: coordinateHeight * pointsToPixels,
        scaleX: finite(object.width, coordinateWidth) / coordinateWidth * (object.flipH ? -1 : 1),
        scaleY: finite(object.height, coordinateHeight) / coordinateHeight * (object.flipV ? -1 : 1),
        objects: children,
        subTargetCheck: true,
        interactive: true,
        figureStudioPptxGroupMeta: { schema: "figureStudio.pptxGroup.v1", sourceId: id }
      };
    }
    if (object.kind === "image") {
      const targetWidth = Math.max(1, finite(object.width) * pointsToPixels);
      const targetHeight = Math.max(1, finite(object.height) * pointsToPixels);
      const intrinsicWidth = Math.max(1, finite(object.intrinsicWidth, targetWidth));
      const intrinsicHeight = Math.max(1, finite(object.intrinsicHeight, targetHeight));
      return { type: "Image", version: "7.3.1", ...common, figureType: "image", width: intrinsicWidth, height: intrinsicHeight,
        scaleX: targetWidth / intrinsicWidth, scaleY: targetHeight / intrinsicHeight, src: object.dataUrl || object.src || "", crossOrigin: "anonymous" };
    }
    return null;
  }

  function canonicalObjectToFabricObjects(object, pointsToPixels) {
    const primary = canonicalObjectToFabric(object, pointsToPixels);
    const result = primary ? [primary] : [];
    if (object?.kind === "shape" && object.text != null && String(object.text) !== "") {
      const style = object.textStyle || {};
      const parentSourceId = object.sourceId || object.id || object.figureId || fallbackPptxObjectId("shape");
      const parentFigureId = stablePptxObjectId(parentSourceId, "pptx-shape");
      const labelFontSize = Math.max(1, finite(style.fontSize, 18));
      const shapeHeight = Math.max(1, finite(object.height));
      const verticalAlign = String(style.verticalAlign || "top").toLowerCase();
      const labelOriginY = verticalAlign === "bottom" ? "bottom" : verticalAlign === "middle" || verticalAlign === "center" ? "center" : "top";
      const labelY = finite(object.y) + (labelOriginY === "bottom" ? shapeHeight : labelOriginY === "center" ? shapeHeight / 2 : 0);
      const text = canonicalObjectToFabric({
        kind: "text",
        sourceId: `${parentSourceId}-text`,
        name: `${object.name || "Shape"} text`,
        x: object.x,
        y: labelY,
        width: object.width,
        height: object.height,
        originY: labelOriginY,
        rotation: object.rotation,
        opacity: object.opacity,
        text: object.text,
        fontFamily: style.fontFamily || "Arial",
        fontSize: labelFontSize,
        bold: style.bold,
        italic: style.italic,
        underline: style.underline,
        align: style.align || "center",
        verticalAlign: labelOriginY === "center" ? "middle" : labelOriginY,
        color: style.color || style.fill || "#000000",
        styles: style.styles || {}
      }, pointsToPixels);
      if (text) {
        text.figureStudioPptxLabelMeta = {
          schema: "figureStudio.pptxShapeLabel.v1",
          parentObjectId: parentFigureId,
          parent_object_id: parentFigureId,
          sourceShapeId: parentSourceId,
          role: "shape-text"
        };
        result.push(text);
      }
    }
    return result;
  }

  function presentationToFigureStudioProject(input, options = {}) {
    const presentation = normalizePresentation(input);
    const widthIn = presentation.widthPt / POINTS_PER_INCH;
    const heightIn = presentation.heightPt / POINTS_PER_INCH;
    const artboard = { preset: "presentation-custom", widthIn, heightIn };
    const pointsToPixels = CSS_PIXELS_PER_INCH / POINTS_PER_INCH;
    const pages = presentation.slides.map((slide, index) => {
      const objects = slide.objects.flatMap((object) => canonicalObjectToFabricObjects(object, pointsToPixels));
      return { id: slide.id || `slide-${index + 1}`, label: slide.name || `Slide ${index + 1}`, createdAt: new Date().toISOString(), updatedAt: new Date().toISOString(), artboard: { ...artboard }, masterId: "master-scientific", layoutId: "blank", layoutApplied: false, appearanceOverrides: slide.background ? { background: slide.background } : {}, masterOverrides: {}, layoutAidOverrides: null, speakerNotes: slide.notes || "", guides: { showRulers: true, visible: true, locked: false, items: [] }, fabric: { version: "7.3.1", objects }, objectCount: objects.length };
    });
    const activePageId = pages[0]?.id || "slide-1";
    return {
      schema: "figureStudio.project.v2",
      app: "Figure Tool",
      version: PRODUCT_VERSION,
      savedAt: new Date().toISOString(),
      importedFrom: { format: "pptx.v1", filename: String(options.sourceFilename || "presentation.pptx") },
      document: { kind: "presentation", pageGeometry: { mode: "uniform", defaultArtboard: { ...artboard } } },
      artboard: { ...artboard, width: Math.round(widthIn * CSS_PIXELS_PER_INCH), height: Math.round(heightIn * CSS_PIXELS_PER_INCH) },
      deck: { activePageId, themeId: "scientific", layouts: ["blank"], masters: [], pages, sections: [], guidePresets: [] },
      fabric: pages[0]?.fabric || { version: "7.3.1", objects: [] }
    };
  }

  async function inspectPackage(input, options = {}) {
    const entries = await readZipEntries(input, options);
    return { entryCount: entries.length, paths: entries.map((entry) => entry.path), entries: entries.map((entry) => ({ path: entry.path, method: entry.method, compressedSize: entry.compressedSize, uncompressedSize: entry.uncompressedSize })) };
  }

  return Object.freeze({
    VERSION,
    PRODUCT_VERSION,
    MIME_TYPE,
    COMPATIBILITY,
    exportProject,
    exportPresentation,
    importPptx,
    projectToPresentation,
    requiresNativeSvgRoot,
    presentationToFigureStudioProject,
    inspectPackage,
    normalizePresentation,
    testing: Object.freeze({ buildStoredZip, readZipEntries, relationshipsFromXml, parseDataUrl, crc32 })
  });
});
