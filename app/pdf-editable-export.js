(function attachPdfEditableExport(root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  if (root) root.FigureStudioPdfEditableExport = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function createPdfEditableExport() {
  "use strict";

  const SCHEMA = "figureStudio.pdfEditableExport.v1";
  const SVG_NS = "http://www.w3.org/2000/svg";
  const STYLE_ID = "figure-studio-pdf-display-fonts";

  function fail(code, message) {
    const error = new Error(message);
    error.code = code;
    throw error;
  }

  function prepareStandardMinusGlyphs(pdf, entries) {
    // Helvetica contains /minus, although WinAnsi has no code for U+2212.
    // Reserve an XML-illegal control code in this new PDF instance only. The
    // generated Type1 encoding is completed before these bytes can be delivered.
    // Current native logical text and registered display programs keep their
    // existing, independently qualified font path.
    const elements = new Set(), records = new Map();
    const names = { normal: "Helvetica", bold: "Helvetica-Bold", italic: "Helvetica-Oblique", bolditalic: "Helvetica-BoldOblique" };
    const reject = (message) => fail("PDF_EXPORT_STANDARD_MINUS_INVALID", message);
    for (const { element, family, style } of entries) {
      const firstFamily = String(family || "").split(",")[0].trim().replace(/^['"]|['"]$/g, "").toLowerCase();
      if (!["helvetica", "arial", "sans-serif"].includes(firstFamily) || !Object.hasOwn(names, style)
          || element.children.length || element.textContent !== "−" || element.getAttribute("data-pdf-unicode") !== "−"
          || element.closest?.("[data-figure-studio-native-logical-glyph]")) continue;
      const font = pdf?.internal?.getFont?.("helvetica", style);
      if (!font?.isStandardFont || font.fontName !== "helvetica" || font.fontStyle !== style || font.postScriptName !== names[style]
          || font.encoding !== "WinAnsiEncoding" || !font.metadata?.Unicode?.encoding?.WinAnsiEncoding
          || !Number.isFinite(font.metadata.Unicode.widths?.fof) || font.metadata.Unicode.widths.fof <= 0) {
        reject("The current Helvetica standard font is unavailable.");
      }
      if (!records.has(font)) records.set(font, { font, style, postScriptName: names[style], metadata: font.metadata, originalUnicode: font.metadata.Unicode });
      elements.add(element);
    }
    // Clone the shared vendor tables: another PDF instance must remain exact.
    for (const record of records.values()) {
      const u = record.originalUnicode;
      record.unicode = { ...u, widths: { ...u.widths, 8722: 0.584 * u.widths.fof },
        encoding: { ...u.encoding, WinAnsiEncoding: { ...u.encoding.WinAnsiEncoding, 8722: 31 } } };
      record.font.metadata.Unicode = record.unicode;
    }
    for (const element of elements) {
      element.setAttribute("font-family", "helvetica");
      element.style.setProperty("font-family", "helvetica");
    }
    return {
      elements,
      async complete(bytes, { pdfLib } = {}) {
        if (!records.size) return bytes;
        if (!pdfLib?.PDFDocument || !pdfLib?.PDFRef || !pdfLib?.PDFDict || !pdfLib?.PDFName) reject("The standard-font PDF writer is unavailable.");
        const document = await pdfLib.PDFDocument.load(bytes), name = pdfLib.PDFName.of, pending = [];
        for (const { font, style, postScriptName, metadata, unicode } of records.values()) {
          if (pdf.internal.getFont("helvetica", style) !== font || !font.isStandardFont || font.fontName !== "helvetica"
              || font.fontStyle !== style || font.postScriptName !== postScriptName || font.encoding !== "WinAnsiEncoding"
              || font.metadata !== metadata || metadata.Unicode !== unicode || unicode.encoding.WinAnsiEncoding[8722] !== 31
              || unicode.widths[8722] !== 0.584 * unicode.widths.fof) reject("The standard minus font changed during export.");
          // A clipped-away scalar may leave this font unused in the new PDF.
          if (font.objectNumber === undefined) continue;
          if (!Number.isSafeInteger(font.objectNumber) || font.objectNumber <= 0) reject("The generated standard font reference is invalid.");
          const dictionary = document.context.lookup(pdfLib.PDFRef.of(font.objectNumber), pdfLib.PDFDict);
          if (String(dictionary.get(name("Type"))) !== "/Font" || String(dictionary.get(name("Subtype"))) !== "/Type1"
              || String(dictionary.get(name("BaseFont"))) !== "/" + font.postScriptName
              || String(dictionary.get(name("Encoding"))) !== "/WinAnsiEncoding"
              || ["Widths", "FontDescriptor", "ToUnicode"].some(key => dictionary.has(name(key)))) {
            reject("The generated font differs from the current standard Helvetica resource.");
          }
          pending.push(dictionary);
        }
        for (const dictionary of pending) {
          dictionary.set(name("Encoding"), document.context.obj({ Type: name("Encoding"), BaseEncoding: name("WinAnsiEncoding"), Differences: [31, name("minus")] }));
          dictionary.set(name("FirstChar"), document.context.obj(31));
        }
        // /minus has its standard Adobe glyph name and therefore retains U+2212
        // during extraction, just as the source's Helvetica Differences does.
        return pending.length ? document.save({ useObjectStreams: false }) : bytes;
      }
    };
  }

  function bytesFromDataUrl(dataUrl) {
    const match = String(dataUrl || "").match(/^data:([^;,]+);base64,([A-Za-z0-9+/]*={0,2})$/);
    if (!match || match[2].length % 4 !== 0) fail("PDF_EXPORT_FONT_DATA_INVALID", "An imported PDF display font has invalid embedded bytes.");
    if (!/^(?:font\/|application\/(?:font|x-font|octet-stream|vnd\.ms-opentype))/i.test(match[1])) fail("PDF_EXPORT_FONT_DATA_INVALID", "An imported PDF display font is not a font data URL.");
    try {
      if (typeof Buffer === "function") return Uint8Array.from(Buffer.from(match[2], "base64"));
      return Uint8Array.from(atob(match[2]), (character) => character.charCodeAt(0));
    } catch (_error) {
      fail("PDF_EXPORT_FONT_DATA_INVALID", "An imported PDF display font could not be decoded.");
    }
  }

  function detectFontProgram(bytes) {
    const data = bytes instanceof Uint8Array ? bytes : new Uint8Array(bytes || []);
    if (data.length < 4) fail("PDF_EXPORT_FONT_UNSUPPORTED", "The imported PDF display font is truncated.");
    const tag = String.fromCharCode(...data.subarray(0, 4));
    if (tag === "OTTO" || data[0] === 1 && data[1] === 0 && data[2] >= 4) return { format: "cff", supported: false };
    if (tag === "ttcf") return { format: "collection", supported: false };
    if (tag === "wOFF" || tag === "wOF2") return { format: "webfont", supported: false };
    if (!(data[0] === 0 && data[1] === 1 && data[2] === 0 && data[3] === 0) && tag !== "true") return { format: "unknown", supported: false };
    if (data.length < 12) fail("PDF_EXPORT_FONT_DATA_INVALID", "The imported TrueType display font has no table directory.");
    const view = new DataView(data.buffer, data.byteOffset, data.byteLength);
    const count = view.getUint16(4);
    if (!count || 12 + count * 16 > data.length) fail("PDF_EXPORT_FONT_DATA_INVALID", "The imported TrueType display font has an invalid table directory.");
    const tables = {};
    for (let index = 0; index < count; index++) {
      const position = 12 + index * 16;
      const name = String.fromCharCode(...data.subarray(position, position + 4));
      const offset = view.getUint32(position + 8), length = view.getUint32(position + 12);
      if (Object.hasOwn(tables, name) || offset > data.length || length > data.length - offset) fail("PDF_EXPORT_FONT_DATA_INVALID", "The imported TrueType display font has duplicate or invalid tables.");
      tables[name] = { offset, length };
    }
    if (!tables.cmap || tables.cmap.length < 4) fail("PDF_EXPORT_FONT_CMAP_MISSING", "The imported TrueType display font has no usable character map.");
    if (!tables.glyf || !tables.loca) return { format: "sfnt-without-truetype-outlines", supported: false, tables };
    const cmap = tables.cmap, cmapCount = view.getUint16(cmap.offset + 2);
    if (view.getUint16(cmap.offset) !== 0 || !cmapCount || 4 + cmapCount * 8 > cmap.length) fail("PDF_EXPORT_FONT_CMAP_MISSING", "The imported TrueType display font has an invalid character-map directory.");
    let unicodeCMap = null;
    for (let index = 0; index < cmapCount; index++) {
      const record = cmap.offset + 4 + index * 8;
      const platform = view.getUint16(record), encoding = view.getUint16(record + 2), relative = view.getUint32(record + 4);
      if (relative > cmap.length - 2) fail("PDF_EXPORT_FONT_DATA_INVALID", "The imported display font has an invalid character-map offset.");
      const offset = cmap.offset + relative, format = view.getUint16(offset);
      // The bundled jsPDF TrueType writer selects the first Unicode format-4 map.
      if (format !== 4 || !(platform === 0 || platform === 3 && encoding === 1) || unicodeCMap) continue;
      if (relative > cmap.length - 16) fail("PDF_EXPORT_FONT_DATA_INVALID", "The imported display font has a truncated Unicode character map.");
      const length = view.getUint16(offset + 2), segments = view.getUint16(offset + 6) / 2;
      if (!Number.isInteger(segments) || !segments || length < 16 + 8 * segments || length > cmap.length - relative) fail("PDF_EXPORT_FONT_DATA_INVALID", "The imported display font has an invalid Unicode character map.");
      unicodeCMap = { offset, length, segments };
    }
    if (!unicodeCMap) fail("PDF_EXPORT_FONT_CMAP_UNSUPPORTED", "The imported TrueType display font has no Unicode character map supported by this PDF writer.");
    return { format: "truetype", supported: true, tables, unicodeCMap };
  }

  function validUnicode(value) {
    const text = String(value ?? "");
    if (!text) return false;
    for (let index = 0; index < text.length; index++) {
      const code = text.charCodeAt(index);
      if (code >= 0xd800 && code <= 0xdbff) {
        const next = text.charCodeAt(++index);
        if (!(next >= 0xdc00 && next <= 0xdfff)) return false;
      } else if (code >= 0xdc00 && code <= 0xdfff) return false;
    }
    return true;
  }

  function normalizeGlyphMap(font) {
    const map = new Map();
    const add = (glyph, unicode) => {
      if (!validUnicode(glyph) || [...String(glyph)].length !== 1 || !validUnicode(unicode)) fail("PDF_EXPORT_GLYPH_MAP_INVALID", `Imported font ${font.family || ""} has an invalid glyph-to-text mapping.`);
      glyph = String(glyph); unicode = String(unicode);
      if (map.has(glyph) && map.get(glyph) !== unicode) fail("PDF_EXPORT_GLYPH_MAP_CONFLICT", `Imported font ${font.family || ""} maps one display glyph to different text.`);
      map.set(glyph, unicode);
    };
    for (const [glyph, unicode] of Object.entries(font.fontCharToUnicode || {})) add(glyph, unicode);
    for (const [unicode, glyph] of Object.entries(font.unicodeToFontChar || {})) add(glyph, unicode);
    return map;
  }

  function normalizeFonts(fonts, requireTrueType = false) {
    const byFamily = new Map();
    for (const font of fonts || []) {
      const family = String(font?.family || "");
      if (!family || /[\u0000-\u001f\u007f]/u.test(family)) fail("PDF_EXPORT_FONT_FAMILY_INVALID", "An imported PDF display font has no valid family name.");
      const bytes = bytesFromDataUrl(font.dataUrl);
      const program = detectFontProgram(bytes);
      if (requireTrueType && !program.supported) fail("PDF_EXPORT_FONT_UNSUPPORTED", `Imported font ${family} uses ${program.format}; editable PDF export currently requires TrueType outlines.`);
      const map = normalizeGlyphMap(font);
      const prior = byFamily.get(family);
      if (prior) {
        if (prior.dataUrl !== font.dataUrl) fail("PDF_EXPORT_FONT_FAMILY_CONFLICT", `Imported font family ${family} has different display programs.`);
        for (const [glyph, unicode] of map) {
          if (prior.map.has(glyph) && prior.map.get(glyph) !== unicode) fail("PDF_EXPORT_GLYPH_MAP_CONFLICT", `Imported font ${family} has conflicting saved text mappings.`);
          prior.map.set(glyph, unicode);
        }
      } else byFamily.set(family, { ...font, family, bytes, program, map, filename: `${family}.ttf` });
    }
    return [...byFamily.values()];
  }

  function displayGlyphIds(font) {
    const map = new Map(), table = font.program.unicodeCMap;
    if (!table) return map;
    const view = new DataView(font.bytes.buffer, font.bytes.byteOffset, font.bytes.byteLength);
    const endCodes = table.offset + 14;
    const startCodes = endCodes + 2 * table.segments + 2;
    const deltas = startCodes + 2 * table.segments;
    const ranges = deltas + 2 * table.segments;
    for (const character of font.map.keys()) {
      const code = character.codePointAt(0);
      if (code > 0xffff) fail("PDF_EXPORT_FONT_GLYPH_UNSUPPORTED", "The current PDF writer cannot encode supplementary display glyph codes.");
      let glyph = 0;
      for (let index = 0; index < table.segments; index++) {
        if (code > view.getUint16(endCodes + index * 2) || code < view.getUint16(startCodes + index * 2)) continue;
        const delta = view.getInt16(deltas + index * 2), rangePosition = ranges + index * 2, range = view.getUint16(rangePosition);
        if (!range) glyph = (code + delta) & 0xffff;
        else {
          const position = rangePosition + range + (code - view.getUint16(startCodes + index * 2)) * 2;
          if (position > table.offset + table.length - 2) fail("PDF_EXPORT_FONT_DATA_INVALID", "The imported display font character map points outside its table.");
          const raw = view.getUint16(position);
          glyph = raw ? (raw + delta) & 0xffff : 0;
        }
        break;
      }
      map.set(character, glyph);
    }
    return map;
  }

  function registerFontsWithJsPdf(pdf, fonts) {
    const programs = normalizeFonts(fonts, true);
    if (programs.length && (!pdf?.addFileToVFS || !pdf?.addFont || !pdf?.internal?.getFont)) fail("PDF_EXPORT_FONT_REGISTRATION_UNAVAILABLE", "PDF export cannot register imported display fonts.");
    const registered = [];
    for (const font of programs) {
      pdf.addFileToVFS(font.filename, font.dataUrl.slice(font.dataUrl.indexOf(",") + 1));
      // A display alias already contains its original regular/bold/italic glyph
      // outlines. Bind every SVG style lookup to that exact program, rather than
      // allowing jsPDF to fall back to Times for an alias/style combination.
      const styles = ["normal", "bold", "italic", "bolditalic"];
      for (const style of styles) {
        pdf.addFont(font.filename, font.family, style, "Identity-H");
        const actual = pdf.internal.getFont(font.family, style);
        if (actual?.fontName !== font.family || actual.fontStyle !== style || !actual.metadata?.cmap?.unicode?.codeMap || !actual.metadata?.glyf) fail("PDF_EXPORT_FONT_REGISTRATION_FAILED", `PDF export could not register the TrueType character map for ${font.family}.`);
        const glyphText = new Map();
        for (const [glyph, unicode] of font.map) {
          const id = actual.metadata.cmap.unicode.codeMap[glyph.codePointAt(0)] || 0;
          if (!/^\s+$/u.test(unicode) && !id) fail("PDF_EXPORT_FONT_GLYPH_MISSING", `PDF export cannot find a retained display glyph in ${font.family}.`);
          if (id && glyphText.has(id) && glyphText.get(id) !== unicode) fail("PDF_EXPORT_GLYPH_MAP_CONFLICT", `Imported font ${font.family} maps one generated glyph ID to different text.`);
          if (id) glyphText.set(id, unicode);
        }
      }
      registered.push({ family: font.family, filename: font.filename, format: font.program.format, glyphMappingCount: font.map.size, styles });
    }
    return registered;
  }

  function embedSvgFonts(svgRoot, fonts) {
    const programs = normalizeFonts(fonts);
    if (!svgRoot?.ownerDocument?.createElementNS || !svgRoot?.appendChild) fail("PDF_EXPORT_SVG_UNAVAILABLE", "SVG export requires a parsed SVG document.");
    const sheets = [...(svgRoot.querySelectorAll?.("style") || [])];
    let sheet = sheets.find((item) => item.getAttribute("id") === STYLE_ID);
    const css = programs.map((font) => `@font-face { font-family: ${JSON.stringify(font.family)}; src: url(${JSON.stringify(font.dataUrl)}); font-weight: normal; font-style: normal; }`).join("\n");
    if (!sheet && programs.length) {
      sheet = svgRoot.ownerDocument.createElementNS(SVG_NS, "style");
      sheet.setAttribute("id", STYLE_ID);
      sheet.setAttribute("type", "text/css");
      svgRoot.appendChild(sheet);
    }
    if (sheet) sheet.textContent = css;
    return { embeddedFontCount: programs.length, families: programs.map((font) => font.family) };
  }

  function positionedGlyphs(text, x, y, glyphs = null) {
    const characters = [...String(text || "")];
    const coordinates = (value) => {
      const input = String(value || "").trim();
      if (!input) return [];
      const numbers = input.match(/[+-]?(?:\d*\.\d+|\d+\.?\d*)(?:e[+-]?\d+)?/gi) || [];
      if (input.replace(/[+-]?(?:\d*\.\d+|\d+\.?\d*)(?:e[+-]?\d+)?|[\s,]/gi, "") || numbers.some((number) => !Number.isFinite(Number(number)))) fail("PDF_EXPORT_POSITIONED_TEXT_UNSUPPORTED", "Imported PDF text has unsupported SVG position units.");
      return numbers.map(Number);
    };
    const xs = coordinates(x), ys = coordinates(y);
    if (xs.length <= 1 && ys.length <= 1) return null;
    if (xs.length !== characters.length || ![0, 1, characters.length].includes(ys.length) || glyphs && glyphs.length !== characters.length) fail("PDF_EXPORT_POSITIONED_TEXT_UNSUPPORTED", "Imported PDF text has incomplete per-glyph SVG positions.");
    return characters.map((fontChar, index) => ({ fontChar, x: xs[index], y: ys.length === characters.length ? ys[index] : ys[0], glyph: glyphs?.[index] || null }));
  }

  function useOwnedPageCropForJsPdf(svgRoot) {
    // The detached PDF conversion already has this exact, explicit page crop.
    // Keep it and suppress only svg2pdf's redundant root viewport crop.
    if (svgRoot?.localName !== "svg" || svgRoot.namespaceURI !== SVG_NS
        || svgRoot.getAttribute("data-export-clip") !== "clip-to-artboard"
        || svgRoot.getAttribute("overflow") !== "hidden") return false;
    const numeric = (text) => {
      if (typeof text !== "string" || !/^[+-]?(?:\d*\.\d+|\d+\.?\d*)(?:e[+-]?\d+)?$/i.test(text.trim())) return null;
      const value = Number(text);
      return Number.isFinite(value) ? value : null;
    };
    const box = String(svgRoot.getAttribute("viewBox") || "").trim().split(/[ ,]+/).map(numeric);
    if (box.length !== 4 || box.some(value => value === null) || box[2] <= 0 || box[3] <= 0) return false;
    const contents = Array.from(svgRoot.children).filter(child => child.getAttribute("data-figure-studio-export-content") === "true");
    if (contents.length !== 1 || contents[0].localName !== "g" || contents[0].namespaceURI !== SVG_NS
        || contents[0].hasAttribute("transform") || contents[0].hasAttribute("style")) return false;
    if (Array.from(svgRoot.children).some(child => child !== contents[0]
        && !["defs", "style", "metadata", "title", "desc"].includes(child.localName))) return false;
    const match = String(contents[0].getAttribute("clip-path") || "").match(/^url\(#(figure-studio-clip-[A-Za-z0-9_-]+)\)$/);
    if (!match) return false;
    const clips = Array.from(svgRoot.querySelectorAll("[id]")).filter(node => node.getAttribute("id") === match[1]);
    const clip = clips[0];
    if (clips.length !== 1 || clip.localName !== "clipPath" || clip.namespaceURI !== SVG_NS
        || clip.parentNode?.localName !== "defs" || clip.parentNode.parentNode !== svgRoot
        || clip.getAttribute("clipPathUnits") !== "userSpaceOnUse" || clip.children.length !== 1
        || clip.hasAttribute("transform") || clip.hasAttribute("style")) return false;
    const rect = clip.children[0];
    if (rect.localName !== "rect" || rect.namespaceURI !== SVG_NS || rect.children.length
        || ["transform", "style", "rx", "ry", "clip-path", "mask"].some(key => rect.hasAttribute(key))
        || rect.hasAttribute("clip-rule") && rect.getAttribute("clip-rule") !== "nonzero") return false;
    const crop = ["x", "y", "width", "height"].map(name => numeric(rect.getAttribute(name)));
    if (!crop.every((value, index) => value !== null && value === box[index])) return false;
    svgRoot.setAttribute("overflow", "visible");
    return true;
  }

  function preserveCurrentPathArguments(svgRoot) {
    // Fabric paints a Path by first subtracting pathOffset from each command,
    // then applying its current object matrix. svg2pdf instead combines that
    // translation into the matrix. The two arithmetic orders can differ by
    // an ULP. Its clip matrix/inverse pair can introduce the same drift.
    // Use only current SVG commands and matrices from this detached export.
    const identity = [1, 0, 0, 1, 0, 0];
    const multiply = (a, b) => [a[0]*b[0]+a[2]*b[1], a[1]*b[0]+a[3]*b[1], a[0]*b[2]+a[2]*b[3], a[1]*b[2]+a[3]*b[3], a[0]*b[4]+a[2]*b[5]+a[4], a[1]*b[4]+a[3]*b[5]+a[5]];
    const num = value => Object.is(value, -0) ? "-0" : String(value);
    const matrix = value => `matrix(${value.map(num).join(" ")})`;
    const unqualified = Symbol("unqualified-current-svg-geometry");
    const unsupported = () => { throw unqualified; };
    const transform = (text = "") => {
      const tokens = [...text.matchAll(/(matrix|translate|scale)\s*\(([^)]*)\)/g)];
      if (tokens.map(row => row[0]).join("").replace(/\s/g, "") !== text.replace(/\s/g, "")) unsupported();
      return tokens.map(row => {
        const values = row[2].trim().split(/[ ,]+/).map(Number);
        if (!values.every(Number.isFinite)) unsupported();
        if (row[1] === "matrix" && values.length === 6) return values;
        if (row[1] === "translate" && [1, 2].includes(values.length)) return [1,0,0,1,values[0],values[1] ?? 0];
        if (row[1] === "scale" && [1, 2].includes(values.length)) return [values[0],0,0,values[1] ?? values[0],0,0];
        unsupported();
      });
    };
    const path = (text, translation = [0, 0], world = null) => {
      const tokens = String(text || "").match(/[MLCQZ]|[+-]?(?:\d*\.\d+|\d+\.?\d*)(?:e[+-]?\d+)?/g) || [];
      if (!tokens.length || String(text).replace(/[MLCQZ]|[+-]?(?:\d*\.\d+|\d+\.?\d*)(?:e[+-]?\d+)?|[\s,]/g, "")) unsupported();
      const sizes = {M:2,L:2,C:6,Q:4,Z:0}, result = [];
      for (let index = 0; index < tokens.length;) {
        const command = tokens[index++], size = sizes[command];
        if (size === undefined) unsupported();
        const row = [command];
        for (let offset = 0; offset < size; offset += 2) {
          const x = Number(tokens[index++]) + translation[0], y = Number(tokens[index++]) + translation[1];
          if (![x, y].every(Number.isFinite)) unsupported();
          row.push(...(world ? [world[0]*x+world[2]*y+world[4],world[1]*x+world[3]*y+world[5]] : [x,y]));
        }
        result.push(row);
      }
      return result.map(row => row.map(value => typeof value === "number" ? num(value) : value).join(" ")).join(" ");
    };
    const operations = [], definitions = [], ids = new Map();
    for (const element of svgRoot.querySelectorAll("[id]")) {
      const id = element.getAttribute("id");
      if (ids.has(id)) return false;
      ids.set(id, element);
    }
    let ordinal = 0;
    function pathPlane(element, parent, bake = false) {
      const transforms = transform(element.getAttribute("transform") || "");
      let translation = [0, 0];
      const last = transforms.at(-1);
      // Stock Path's offset is a final literal translation. Subtract before
      // the matrix, exactly as its native Canvas command writer does.
      if (last && /translate\s*\([^)]*\)\s*$/.test(element.getAttribute("transform") || "")) {
        transforms.pop(); translation = last.slice(4);
      }
      const world = transforms.reduce(multiply, parent);
      return {world, d:path(element.getAttribute("d"), translation, bake ? world : null)};
    }
    function clip(reference, owner) {
      const match = /^url\(#([^\s)]+)\)$/.exec(reference || ""), original = match && ids.get(match[1]);
      if (!original || original.localName !== "clipPath" || original.children.length !== 1
          || original.hasAttribute("clip-path") || original.hasAttribute("style")
          || original.hasAttribute("clipPathUnits") && original.getAttribute("clipPathUnits") !== "userSpaceOnUse") unsupported();
      let plane = transform(original.getAttribute("transform") || "").reduce(multiply, owner), shape = original.children[0];
      let rule = original.getAttribute("clip-rule") || "nonzero";
      while (shape.localName === "g" && shape.children.length === 1) {
        if (shape.hasAttribute("clip-path") || String(shape.getAttribute("style") || "").trim()
            || shape.hasAttribute("mask") || shape.hasAttribute("filter")) unsupported();
        rule = shape.getAttribute("clip-rule") || rule;
        plane = transform(shape.getAttribute("transform") || "").reduce(multiply, plane); shape = shape.children[0];
      }
      let d;
      if (shape.localName === "path") d = pathPlane(shape, plane, true).d;
      else if (shape.localName === "rect" && !shape.hasAttribute("rx") && !shape.hasAttribute("ry")) {
        const [x,y,w,h] = ["x","y","width","height"].map(name => Number(shape.getAttribute(name) || 0));
        if (![x,y,w,h].every(Number.isFinite) || w <= 0 || h <= 0) unsupported();
        plane = transform(shape.getAttribute("transform") || "").reduce(multiply, plane);
        d = path(`M ${x} ${y} L ${x+w} ${y} L ${x+w} ${y+h} L ${x} ${y+h} Z`, [0,0], plane);
      } else unsupported();
      if (shape.hasAttribute("clip-path") || shape.hasAttribute("mask") || shape.hasAttribute("filter")
          || String(shape.getAttribute("style") || "").trim()) unsupported();
      rule = shape.getAttribute("clip-rule") || rule;
      if (!["nonzero", "evenodd"].includes(rule)) unsupported();
      const definition = svgRoot.ownerDocument.createElementNS(SVG_NS, "clipPath"), leaf = svgRoot.ownerDocument.createElementNS(SVG_NS, "path");
      let id; do { id = `figure-studio-native-clip-${ordinal++}`; } while (ids.has(id));
      definition.setAttribute("id", id); definition.setAttribute("clipPathUnits", "userSpaceOnUse");
      leaf.setAttribute("d", d);
      leaf.setAttribute("clip-rule", rule);
      definition.appendChild(leaf); definitions.push(definition); ids.set(id, definition);
      return `url(#${id})`;
    }
    function visit(element, parent = identity) {
      if (["defs","clipPath","metadata","desc","title","style"].includes(element.localName)) {
        if (element.localName === "style" && element.textContent.replace(/@font-face\s*\{[^}]+\}/gi, "").trim()) unsupported();
        return;
      }
      if (!["svg","g","path","rect","text"].includes(element.localName)) unsupported();
      if (element.localName === "svg" && element !== svgRoot || element.hasAttribute("class")) unsupported();
      // A clip on a transformed leaf uses that leaf's user space. Baking it
      // into the scene plane while retaining the leaf matrix would apply the
      // matrix twice. Keep those exports on their existing writer route.
      if (["path","rect","text"].includes(element.localName) && element.hasAttribute("clip-path")) unsupported();
      if (["mask","filter","vector-effect"].some(name => element.hasAttribute(name))
          || /(?:url\s*\(|filter\s*:|mask\s*:|vector-effect\s*:|transform\s*:)/i.test(element.getAttribute("style") || "")
          || ["fill","stroke"].some(name => /url\s*\(/i.test(element.getAttribute(name) || ""))) unsupported();
      if (element.localName === "text") for (const child of element.querySelectorAll("*")) {
        if (child.localName !== "tspan" || ["transform","clip-path","mask","filter","class"].some(name => child.hasAttribute(name))) unsupported();
      }
      let world = transform(element.getAttribute("transform") || "").reduce(multiply, parent);
      const changes = {};
      if (element.hasAttribute("clip-path")) changes["clip-path"] = clip(element.getAttribute("clip-path"), world);
      if (element.localName === "path") {
        const current = pathPlane(element, parent); world = current.world;
        changes.d = current.d; changes.transform = matrix(world);
      } else if (["rect","text"].includes(element.localName)) changes.transform = matrix(world);
      else if (element.hasAttribute("transform")) changes.transform = null;
      operations.push({element, changes});
      if (!["path","rect","text"].includes(element.localName)) for (const child of element.children) visit(child, world);
    }
    try {
      for (const style of svgRoot.querySelectorAll("style")) if (style.textContent.replace(/@font-face\s*\{[^}]+\}/gi, "").trim()) unsupported();
      visit(svgRoot);
    } catch (error) { if (error === unqualified) return false; throw error; }
    // Admission is complete before touching the detached conversion tree.
    for (const {element, changes} of operations) for (const [name, value] of Object.entries(changes)) {
      if (value === null) element.removeAttribute(name); else element.setAttribute(name, value);
    }
    let defs = Array.from(svgRoot.children).find(element => element.localName === "defs");
    if (!defs && definitions.length) { defs = svgRoot.ownerDocument.createElementNS(SVG_NS, "defs"); svgRoot.appendChild(defs); }
    for (const definition of definitions) defs.appendChild(definition);
    return true;
  }

  function prepareSvgForJsPdf(svgRoot, { qualifiedSourceScene = false } = {}) {
    const document = svgRoot?.ownerDocument;
    if (!document?.createElementNS || !document?.createDocumentFragment) fail("PDF_EXPORT_SVG_UNAVAILABLE", "PDF export requires a parsed SVG document.");
    const normalize = (element) => {
      const copy = document.createElementNS(element.namespaceURI, element.localName);
      for (const attribute of element.attributes) copy.setAttributeNS(attribute.namespaceURI, attribute.name, attribute.value);
      for (const child of element.childNodes) copy.appendChild(child.nodeType === 1 ? normalize(child) : child.cloneNode(true));
      return copy;
    };
    // svg2pdf dispatches on tagName rather than localName. It also reads only a
    // scalar tspan x/y; separate spans retain the imported PDF's glyph positions.
    const root = normalize(svgRoot);
    useOwnedPageCropForJsPdf(root);
    if (qualifiedSourceScene) preserveCurrentPathArguments(root);
    for (const span of root.querySelectorAll("tspan")) {
      const glyphs = span.hasAttribute("data-pdf-glyph-map") ? JSON.parse(span.getAttribute("data-pdf-glyph-map")) : null;
      const positions = positionedGlyphs(span.textContent, span.getAttribute("x"), span.getAttribute("y"), glyphs);
      if (!positions) continue;
      if (span.children.length || span.hasAttribute("dx") || span.hasAttribute("dy") || span.hasAttribute("rotate")) fail("PDF_EXPORT_POSITIONED_TEXT_UNSUPPORTED", "Imported PDF text uses unsupported nested or relative glyph positioning.");
      const fragment = document.createDocumentFragment();
      for (const position of positions) {
        const glyph = document.createElementNS(SVG_NS, "tspan");
        for (const attribute of span.attributes) glyph.setAttributeNS(attribute.namespaceURI, attribute.name, attribute.value);
        glyph.setAttribute("x", String(position.x));
        if (position.y !== undefined) glyph.setAttribute("y", String(position.y));
        if (position.glyph) {
          glyph.setAttribute("data-pdf-unicode", String(position.glyph.unicode || ""));
          glyph.setAttribute("data-pdf-glyph-map", JSON.stringify([position.glyph]));
        } else {
          glyph.removeAttribute("data-pdf-unicode");
          glyph.removeAttribute("data-pdf-glyph-map");
        }
        glyph.textContent = position.fontChar;
        fragment.appendChild(glyph);
      }
      span.parentNode.replaceChild(fragment, span);
    }
    return root;
  }

  function ownCurrentTextNumberWriter(pdf) {
    const numbers = typeof module === "object" && module.exports && typeof require === "function"
      ? require("./pdf-generated-number-tokens.js") : globalThis.FigureStudioPdfGeneratedNumbers;
    const descriptor = Object.getOwnPropertyDescriptor(pdf, "text");
    if (typeof descriptor?.value !== "function" || !descriptor.configurable || !pdf.internal?.pages
        || typeof pdf.internal.getCurrentPageInfo !== "function" || !numbers?.number || !numbers?.tokenize) {
      fail("PDF_EXPORT_CURRENT_TEXT_UNSUPPORTED", "The current native text number writer is unavailable.");
    }
    const original = descriptor.value, spellings = new Map();
    const spelling = value => {
      const key = Object.is(value, -0) ? "-0" : String(value);
      if (!spellings.has(key)) {
        let token;
        try { token=numbers.number(value); }
        catch (error) { if (error?.code !== "PDF_GENERATED_NUMBER_UNSUPPORTED") throw error; token=null; }
        if(spellings.size>=numbers.limits.uniqueNumbers)spellings.delete(spellings.keys().next().value);
        spellings.set(key,token);
      }
      return spellings.get(key);
    };
    function currentTextRow(row) {
      const tokens = numbers.tokenize(row).tokens.filter(token => token.kind === "number" || token.text.trim());
      const matrices = tokens.map((token, index) => token.text === "Tm" ? index : -1).filter(index => index >= 0);
      if (matrices.length !== 1) return row;
      const at = matrices[0], operands = tokens.slice(at - 6, at);
      if (operands.length !== 6 || operands.some(token => token.kind !== "number")) return row;
      const values = operands.map(token => Number(token.text));
      if (values.every(value => spelling(value) !== null)) return row;
      // Some finite values have no equivalent <=256-character spelling under
      // both native Number conversion and the bundled PDF decimal accumulator.
      // A native text move supplies the same current origin without changing
      // the text's linear plane, glyph, font, or logical parent membership.
      if (!["BT", "ET", "Tm"].every(op => tokens.filter(token => token.text === op).length === 1)
          || tokens.filter(token => ["Tj", "TJ"].includes(token.text)).length !== 1
          || tokens.some(token => ["Td", "TD", "T*", "Tz", "Ts"].includes(token.text))) return row;
      const [a,b,c,d,e,f] = values, determinant = a*d-b*c;
      if (!determinant || !Number.isFinite(determinant) || !values.slice(0,4).every(value => spelling(value) !== null)) return row;
      const origins = value => [...new Set([Math.trunc(value), Math.floor(value), Math.ceil(value), 0])];
      for (const x of origins(e)) for (const y of origins(f)) {
        const dx=e-x, dy=f-y, tx=(d*dx-c*dy)/determinant, ty=(-b*dx+a*dy)/determinant;
        if (![tx,ty].every(Number.isFinite) || !Object.is(a*tx+c*ty+x,e) || !Object.is(b*tx+d*ty+y,f)) continue;
        const replacement = [a,b,c,d,x,y,tx,ty].map(spelling);
        if (replacement.some(value => value === null)) continue;
        return row.slice(0,operands[0].offset) + replacement.slice(0,6).join(" ") + " Tm\n"
          + replacement.slice(6).join(" ") + " Td" + row.slice(tokens[at].offset + 2);
      }
      return row;
    }
    const writer = function (...args) {
      if (this !== pdf || Object.getOwnPropertyDescriptor(pdf,"text")?.value !== writer) fail("PDF_EXPORT_CURRENT_TEXT_UNSUPPORTED", "The current native text writer ownership changed.");
      const page = pdf.internal.getCurrentPageInfo().pageNumber, rows = pdf.internal.pages[page], start = rows?.length;
      if (!Array.isArray(rows) || page !== 1) fail("PDF_EXPORT_CURRENT_TEXT_UNSUPPORTED", "The current text number writer requires one generated page.");
      const result = Reflect.apply(original,pdf,args);
      const changes = rows.slice(start).map(row => typeof row === "string" ? currentTextRow(row) : row);
      for (let index=0;index<changes.length;index++) rows[start+index]=changes[index];
      return result;
    };
    Object.defineProperty(pdf,"text",{...descriptor,value:writer});
    let detached=false;
    return {detach(){
      if (detached) return;
      if (Object.getOwnPropertyDescriptor(pdf,"text")?.value !== writer) fail("PDF_EXPORT_CURRENT_TEXT_UNSUPPORTED", "The current native text writer ownership changed before cleanup.");
      Object.defineProperty(pdf,"text",descriptor);detached=true;
    }};
  }

  function ownCurrentMatrixNumberWriter(pdf, { heightPt } = {}) {
    const numbers = typeof module === "object" && module.exports && typeof require === "function"
      ? require("./pdf-generated-number-tokens.js") : globalThis.FigureStudioPdfGeneratedNumbers;
    const descriptor=Object.getOwnPropertyDescriptor(pdf,"setCurrentTransformationMatrix");
    if(typeof descriptor?.value!=="function"||!descriptor.configurable||typeof pdf.Matrix!=="function"
        ||!pdf.internal?.pages||!Number.isFinite(heightPt)||!numbers?.number||!numbers?.tokenize)fail("PDF_EXPORT_CURRENT_MATRIX_UNSUPPORTED","The current native matrix number writer is unavailable.");
    const original=descriptor.value,cache=new Map(),stack=[];
    const multiply=(a,b)=>[a[0]*b[0]+a[2]*b[1],a[1]*b[0]+a[3]*b[1],a[0]*b[2]+a[2]*b[3],a[1]*b[2]+a[3]*b[3],a[0]*b[4]+a[2]*b[5]+a[4],a[1]*b[4]+a[3]*b[5]+a[5]];
    let world=[96/72,0,0,-96/72,0,heightPt*(96/72)],cursor=0;
    const spelling=value=>{
      const key=Object.is(value,-0)?"-0":String(value);
      if(!cache.has(key)){
        let token;try{token=numbers.number(value);}catch(error){if(error?.code!=="PDF_GENERATED_NUMBER_UNSUPPORTED")throw error;token=null;}
        if(cache.size>=numbers.limits.uniqueNumbers)cache.delete(cache.keys().next().value);
        cache.set(key,token);
      }
      return cache.get(key);
    };
    function currentPlane(rows){
      if(cursor>rows.length)fail("PDF_EXPORT_CURRENT_MATRIX_UNSUPPORTED","The current native page rows changed during matrix emission.");
      for(;cursor<rows.length;cursor++){
        if(typeof rows[cursor]!=="string")fail("PDF_EXPORT_CURRENT_MATRIX_UNSUPPORTED","The native matrix page row is unavailable.");
        let operands=[];
        for(const token of numbers.tokenize(rows[cursor]).tokens){
          if(token.kind==="number"){operands.push(Number(token.text));continue;}
          if(!token.text.trim()||token.text.startsWith("%"))continue;
          if(token.text==="q")stack.push(world.slice());
          else if(token.text==="Q"){if(!stack.length)fail("PDF_EXPORT_CURRENT_MATRIX_UNSUPPORTED","The native graphics-state stack changed.");world=stack.pop();}
          else if(token.text==="cm"){
            if(operands.length!==6)fail("PDF_EXPORT_CURRENT_MATRIX_UNSUPPORTED","The native matrix row changed its operand structure.");
            world=multiply(world,operands);
          }
          operands=[];
        }
      }
      return world;
    }
    const writer=function(matrix){
      if(this!==pdf||Object.getOwnPropertyDescriptor(pdf,"setCurrentTransformationMatrix")?.value!==writer
          ||matrix?.constructor!==pdf.Matrix)fail("PDF_EXPORT_CURRENT_MATRIX_UNSUPPORTED","The current native matrix writer ownership changed.");
      const page=pdf.internal.getCurrentPageInfo().pageNumber,rows=pdf.internal.pages[page];
      if(page!==1||!Array.isArray(rows))fail("PDF_EXPORT_CURRENT_MATRIX_UNSUPPORTED","The current matrix number writer requires one generated page.");
      const values=[matrix.a,matrix.b,matrix.c,matrix.d,matrix.e,matrix.f];
      if(!values.every(Number.isFinite))fail("PDF_EXPORT_CURRENT_MATRIX_UNSUPPORTED","The current native matrix is not finite.");
      const parent=currentPlane(rows);
      if(values.every(value=>spelling(value)!==null))return Reflect.apply(original,pdf,[matrix]);
      if(!values.slice(0,4).every(value=>spelling(value)!==null))return Reflect.apply(original,pdf,[matrix]);
      const target=multiply(parent,values),origins=value=>[...new Set([Math.trunc(value),Math.floor(value),Math.ceil(value),0])];
      for(const x of origins(values[4]))for(const y of origins(values[5])){
        const translation=[1,0,0,1,x,y],residual=[...values.slice(0,4),values[4]-x,values[5]-y];
        if(![...translation,...residual].every(value=>spelling(value)!==null))continue;
        const actual=multiply(multiply(parent,translation),residual);
        if(!actual.every((value,index)=>Object.is(value,target[index])))continue;
        Reflect.apply(original,pdf,[pdf.Matrix(...translation)]);
        return Reflect.apply(original,pdf,[pdf.Matrix(...residual)]);
      }
      return Reflect.apply(original,pdf,[matrix]);
    };
    Object.defineProperty(pdf,"setCurrentTransformationMatrix",{...descriptor,value:writer});
    let detached=false;
    return {detach(){if(detached)return;if(Object.getOwnPropertyDescriptor(pdf,"setCurrentTransformationMatrix")?.value!==writer)fail("PDF_EXPORT_CURRENT_MATRIX_UNSUPPORTED","The native matrix writer ownership changed before cleanup.");Object.defineProperty(pdf,"setCurrentTransformationMatrix",descriptor);detached=true;}};
  }

  async function renderCurrentPixelPage(pdf, svg, { widthPt, heightPt, qualifiedSourceScene = false } = {}) {
    if (!qualifiedSourceScene || svg?.localName !== "svg" || svg?.namespaceURI !== SVG_NS
        || ![widthPt, heightPt].every(value => Number.isFinite(value) && value > 0)
        || !["advancedAPI", "compatAPI", "isAdvancedAPI", "saveGraphicsState", "restoreGraphicsState", "setCurrentTransformationMatrix", "Matrix", "svg"].every(key => typeof pdf?.[key] === "function")) {
      fail("PDF_EXPORT_CURRENT_PAGE_UNSUPPORTED", "The current PDF page-coordinate export is unavailable.");
    }
    const box = String(svg?.getAttribute?.("viewBox") || "").trim().split(/[ ,]+/).map(Number);
    const physicalPoints = value => {
      const match = /^([+-]?(?:\d*\.\d+|\d+\.?\d*)(?:e[+-]?\d+)?)in$/i.exec(String(value));
      return match ? Number(match[1]) * 72 : null;
    };
    const widthPx = box[2], heightPx = box[3];
    // Check the declared physical dimensions in their forward conversion.
    // Multiplying an already-converted point value by 96/72 is not an exact
    // inverse for every finite artboard size. It must not reject those pages
    // or rescale their current SVG coordinate planes.
    const samePhysicalPage = Object.is(physicalPoints(svg.getAttribute("width")), widthPt)
      && Object.is(physicalPoints(svg.getAttribute("height")), heightPt);
    if (box.length !== 4 || !box.every(Number.isFinite) || box[0] !== 0 || box[1] !== 0
        || widthPx <= 0 || heightPx <= 0
        || !(samePhysicalPage || Object.is(widthPx, widthPt * 96 / 72) && Object.is(heightPx, heightPt * 96 / 72))
        || !Object.is(pdf.internal?.pageSize?.getWidth?.(), widthPt) || !Object.is(pdf.internal?.pageSize?.getHeight?.(), heightPt)) {
      fail("PDF_EXPORT_CURRENT_PAGE_UNSUPPORTED", "This export region cannot preserve its current page-coordinate planes exactly.");
    }
    const wasAdvanced = pdf.isAdvancedAPI();
    const textNumbers = ownCurrentTextNumberWriter(pdf);
    let matrixNumbers;
    try{matrixNumbers=ownCurrentMatrixNumberWriter(pdf,{heightPt});}
    catch(error){textNumbers.detach();throw error;}
    let saved = false;
    try {
      pdf.advancedAPI();
      pdf.saveGraphicsState(); saved = true;
      // One physical conversion surrounds current scene coordinates. The
      // original local paths, text matrices and clipping scopes remain native.
      pdf.setCurrentTransformationMatrix(pdf.Matrix(0.75, 0, 0, 0.75, 0, 0));
      return await pdf.svg(svg, { x: 0, y: 0, width: widthPx, height: heightPx });
    } finally {
      try { if (saved) { pdf.advancedAPI(); pdf.restoreGraphicsState(); } }
      finally { try { if (!wasAdvanced) pdf.compatAPI(); } finally { try{matrixNumbers.detach();}finally{textNumbers.detach();} } }
    }
  }

  function utf16Hex(text) {
    if (!validUnicode(text)) fail("PDF_EXPORT_CMAP_INVALID", "Generated PDF text contains invalid UTF-16.");
    let result = "";
    for (let index = 0; index < text.length; index++) result += text.charCodeAt(index).toString(16).padStart(4, "0");
    return result;
  }

  function textFromHex(hex) {
    if (!/^(?:[0-9a-f]{4})+$/i.test(hex)) fail("PDF_EXPORT_CMAP_INVALID", "Generated PDF ToUnicode has an invalid UTF-16 destination.");
    let result = "";
    for (let index = 0; index < hex.length; index += 4) result += String.fromCharCode(parseInt(hex.slice(index, index + 4), 16));
    if (!validUnicode(result)) fail("PDF_EXPORT_CMAP_INVALID", "Generated PDF ToUnicode has an unpaired surrogate.");
    return result;
  }

  function privateUse(character) {
    const code = character.codePointAt(0);
    return code >= 0xe000 && code <= 0xf8ff || code >= 0xf0000 && code <= 0xffffd || code >= 0x100000 && code <= 0x10fffd;
  }

  function rewriteToUnicodeCMap(cmap, glyphMap, options = {}) {
    const map = glyphMap instanceof Map ? glyphMap : normalizeGlyphMap({ fontCharToUnicode: glyphMap });
    let rewritten = 0, mappings = 0;
    const sourceDestinations = new Map();
    const destination = (hex, source) => {
      const original = textFromHex(hex);
      let recovered = "";
      for (const character of original) {
        if (!privateUse(character)) { recovered += character; continue; }
        if (!map.has(character)) fail("PDF_EXPORT_GLYPH_MAP_MISSING", "Generated PDF contains a private-use display glyph without recovered Unicode.");
        const replacement = map.get(character);
        if (options.glyphIds && ([...original].length !== 1 || !options.glyphIds.has(character) || options.glyphIds.get(character) !== parseInt(source, 16) || options.glyphIds.get(character) === 0 && !/^\s+$/u.test(replacement))) fail("PDF_EXPORT_FONT_MATCH_INVALID", "Generated PDF display glyph IDs do not match the retained font program.");
        if (!validUnicode(replacement) || [...replacement].some(privateUse)) fail("PDF_EXPORT_GLYPH_MAP_UNRECOVERED", "Generated PDF display glyph has no recovered non-private Unicode text.");
        recovered += replacement;
      }
      if (recovered !== original) { rewritten++; return utf16Hex(recovered); }
      return hex;
    };
    const text = String(cmap || "");
    if (!/\bbegincmap\b/.test(text) || /\b(?:usecmap|beginnotdefchar|beginnotdefrange)\b/.test(text)) fail("PDF_EXPORT_CMAP_UNSUPPORTED", "Generated display-font ToUnicode uses an unsupported CMap structure.");
    let blocks = 0;
    const result = text.replace(/(\d+)\s+begin(bfchar|bfrange)\b([\s\S]*?)end\2\b/g, (block, declared, type, body) => {
      blocks++;
      const clean = body.replace(/%[^\r\n]*/g, "");
      const tokens = clean.match(/<[0-9a-f]+>|\[|\]/gi) || [];
      if (clean.replace(/<[0-9a-f]+>|\[|\]|\s/gi, "")) fail("PDF_EXPORT_CMAP_UNSUPPORTED", "Generated display-font ToUnicode contains unsupported mapping syntax.");
      const entries = [];
      let index = 0, rows = 0;
      const hex = () => {
        const token = tokens[index++];
        if (!/^<[0-9a-f]+>$/i.test(token || "")) fail("PDF_EXPORT_CMAP_INVALID", "Generated display-font ToUnicode has a malformed mapping.");
        return token.slice(1, -1);
      };
      while (index < tokens.length) {
        const start = hex();
        if (start.length % 2 || start.length > 8) fail("PDF_EXPORT_CMAP_INVALID", "Generated display-font ToUnicode has an invalid source code.");
        if (type === "bfchar") { entries.push([start, hex()]); rows++; continue; }
        const end = hex();
        if (start.length !== end.length) fail("PDF_EXPORT_CMAP_INVALID", "Generated display-font ToUnicode range changes source-code width.");
        const first = parseInt(start, 16), last = parseInt(end, 16), count = last - first + 1;
        if (count <= 0 || count > 65536) fail("PDF_EXPORT_CMAP_INVALID", "Generated display-font ToUnicode range is invalid or too large.");
        let outputs = [];
        if (tokens[index] === "[") {
          index++;
          while (index < tokens.length && tokens[index] !== "]") outputs.push(hex());
          if (tokens[index++] !== "]" || outputs.length !== count) fail("PDF_EXPORT_CMAP_INVALID", "Generated display-font ToUnicode range array has the wrong length.");
        } else {
          const initial = hex();
          const initialNumber = BigInt(`0x${initial}`);
          outputs = Array.from({ length: count }, (_, offset) => {
            const value = (initialNumber + BigInt(offset)).toString(16).padStart(initial.length, "0");
            if (value.length !== initial.length) fail("PDF_EXPORT_CMAP_INVALID", "Generated display-font ToUnicode destination range overflows.");
            return value;
          });
        }
        outputs.forEach((output, offset) => entries.push([(first + offset).toString(16).padStart(start.length, "0"), output]));
        rows++;
      }
      if (rows !== Number(declared)) fail("PDF_EXPORT_CMAP_INVALID", "Generated display-font ToUnicode mapping count is incorrect.");
      const before = rewritten;
      const replacements = entries.map(([source, output]) => {
        const recovered = destination(output, source), key = source.toLowerCase();
        if (sourceDestinations.has(key) && sourceDestinations.get(key).toLowerCase() !== recovered.toLowerCase()) fail("PDF_EXPORT_GLYPH_MAP_CONFLICT", "Generated PDF maps one source character ID to different recovered text.");
        sourceDestinations.set(key, recovered);
        return [source, recovered];
      });
      mappings += entries.length;
      if (before === rewritten) return block;
      return `${replacements.length} beginbfchar\n${replacements.map(([source, output]) => `<${source}><${output}>`).join("\n")}\nendbfchar`;
    });
    const declaredBlocks = (text.replace(/%[^\r\n]*/g, "").match(/\bbegin(?:bfchar|bfrange)\b/g) || []).length;
    if (blocks !== declaredBlocks) fail("PDF_EXPORT_CMAP_INVALID", "Generated display-font ToUnicode has an incomplete mapping block.");
    if (!mappings) fail("PDF_EXPORT_CMAP_MISSING", "Generated display-font ToUnicode has no character mappings.");
    return { text: result, rewrittenCount: rewritten, mappingCount: mappings };
  }

  function decodePdfName(value) {
    if (typeof value?.decodeText === "function") return value.decodeText();
    return String(value || "").replace(/^\//, "").replace(/#([0-9a-f]{2})/gi, (_, hex) => String.fromCharCode(parseInt(hex, 16)));
  }

  async function restorePdfUnicode(pdfBytes, options = {}) {
    const { pdfLib } = options;
    const fonts = normalizeFonts(options.fonts, true);
    const input = pdfBytes instanceof Uint8Array ? pdfBytes : new Uint8Array(pdfBytes);
    if (!fonts.length) return input;
    if (!pdfLib?.PDFDocument || !pdfLib?.PDFName || !pdfLib?.PDFDict || !pdfLib?.decodePDFRawStream) fail("PDF_EXPORT_UNICODE_RESTORE_UNAVAILABLE", "PDF export cannot restore imported display-font Unicode mappings.");
    const generated = await pdfLib.PDFDocument.load(input);
    const name = pdfLib.PDFName.of;
    let changes = 0;
    // Only generated font dictionaries owned by this export are addressed. Never
    // mutate original PDF streams or shared ToUnicode stream references in place.
    for (const [, dictionary] of generated.context.enumerateIndirectObjects()) {
      if (!(dictionary instanceof pdfLib.PDFDict) || decodePdfName(dictionary.get(name("Type"))) !== "Font") continue;
      const baseFont = decodePdfName(dictionary.get(name("BaseFont"))).replace(/^[A-Z]{6}\+/, "");
      const candidates = fonts.filter((font) => baseFont === font.family || baseFont === font.filename);
      if (!candidates.length) continue;
      if (candidates.length !== 1) fail("PDF_EXPORT_FONT_MATCH_AMBIGUOUS", "Generated PDF font name matches multiple imported display programs.");
      const subtype = decodePdfName(dictionary.get(name("Subtype")));
      if (subtype === "CIDFontType2") continue;
      if (subtype !== "Type0") fail("PDF_EXPORT_FONT_MATCH_UNSUPPORTED", `Generated font ${baseFont} is not an Identity-H display font.`);
      if (decodePdfName(dictionary.get(name("Encoding"))) !== "Identity-H") fail("PDF_EXPORT_FONT_MATCH_UNSUPPORTED", `Generated font ${baseFont} has an unsupported encoding.`);
      const stream = generated.context.lookup(dictionary.get(name("ToUnicode")));
      if (!(stream instanceof pdfLib.PDFRawStream)) fail("PDF_EXPORT_CMAP_MISSING", `Generated font ${baseFont} has no readable ToUnicode stream.`);
      const decoded = pdfLib.decodePDFRawStream(stream).decode();
      const text = Array.from(decoded, (byte) => String.fromCharCode(byte)).join("");
      const recovered = rewriteToUnicodeCMap(text, candidates[0].map, { glyphIds: displayGlyphIds(candidates[0]) });
      if (!recovered.rewrittenCount) continue;
      const streamDictionary = {};
      for (const [key, value] of stream.dict.entries()) {
        const label = decodePdfName(key);
        if (!["Length", "Filter", "DecodeParms"].includes(label)) streamDictionary[label] = value;
      }
      const replacement = generated.context.flateStream(Uint8Array.from(recovered.text, (character) => character.charCodeAt(0)), streamDictionary);
      dictionary.set(name("ToUnicode"), generated.context.register(replacement));
      changes += recovered.rewrittenCount;
    }
    return changes ? generated.save({ useObjectStreams: false }) : input;
  }

  function ownSourcePaintObserver(pdf, svg, { qualifiedSourceScene = false } = {}) {
    // Qualification comes from the current canvas source-ownership predicate.
    // Paint values come only from this temporary SVG's resolved native context.
    if (!qualifiedSourceScene) return null;
    const key = "__figureStudioSourcePaintObserver";
    const reject = (message) => fail("PDF_EXPORT_SOURCE_PAINT_UNSUPPORTED", message);
    if (!svg || svg.localName !== "svg" || typeof svg.contains !== "function") {
      reject("The current source export SVG is unavailable.");
    }
    if (!pdf || key in pdf || !Object.isExtensible(pdf)) {
      reject("The generated PDF paint observer property is unavailable or already owned.");
    }
    const writers = {};
    for (const name of ["setFillColor", "setDrawColor", "setLineCap"]) {
      const descriptor = Object.getOwnPropertyDescriptor(pdf, name);
      if (!descriptor || typeof descriptor.value !== "function") {
        reject("The generated PDF has no own native paint writer.");
      }
      writers[name] = descriptor.value;
    }
    const solidChannels = (paint) => {
      if (!paint?.color?.ok) return null;
      const values = [paint.color.r, paint.color.g, paint.color.b];
      if (!values.every((value) => Number.isFinite(value) && value >= 0 && value <= 255)) {
        reject("The current solid source color has unsupported RGB channels.");
      }
      // jsPDF's stock numeric RGB setters hard-code precision 2. The stock
      // fractional-string route emits these current RGB values without rounding.
      return values.map((value) => String(value / 255));
    };
    const observer = {
      beforePathPaint(element, context) {
        if (Object.getOwnPropertyDescriptor(pdf, key)?.value !== observer) {
          reject("The generated PDF paint observer ownership changed.");
        }
        if (context?.pdf !== pdf || !element || !svg.contains(element)) {
          reject("The native source paint is outside the current export SVG.");
        }
        // The vendor invocation occurs after the clip-only early return.
        if (context.withinClipPath) return;
        for (let parent = element.parentNode; parent && parent !== svg; parent = parent.parentNode) {
          if (["defs", "marker", "symbol", "pattern", "mask", "clipPath"].includes(parent.localName)) return;
        }
        // Referenced Forms and marker contexts keep their existing writer path.
        // They are not part of this qualified direct-paint correction.
        if (context.withinUse) return;
        const state = context.attributeState;
        if (!state) reject("The native source paint has no resolved style.");
        const fill = solidChannels(state.fill);
        const stroke = state.stroke && state.strokeWidth !== 0;
        const draw = stroke ? solidChannels(state.stroke) : null;
        const cap = stroke ? state.strokeLinecap : null;
        if (stroke && !["butt", "round", "square"].includes(cap)) {
          reject("The current source stroke has an unsupported resolved cap.");
        }
        // Validate before writing. Do not replace paths, styles, alpha, dashes,
        // joins, matrices, clips, glyphs, or the stock native paint operations.
        if (fill) Reflect.apply(writers.setFillColor, pdf, fill);
        if (draw) Reflect.apply(writers.setDrawColor, pdf, draw);
        // A clip path can change native cap state without updating the parent
        // svg2pdf style cache. Reassert the current visible stroke's resolved cap.
        if (stroke) Reflect.apply(writers.setLineCap, pdf, [cap]);
      }
    };
    Object.defineProperty(pdf, key, { value: observer, configurable: true });
    let detached = false;
    return {
      detach() {
        if (detached) return;
        if (Object.getOwnPropertyDescriptor(pdf, key)?.value !== observer) {
          reject("The generated PDF paint observer ownership changed before cleanup.");
        }
        delete pdf[key];
        detached = true;
      }
    };
  }

  return { SCHEMA, prepareStandardMinusGlyphs, detectFontProgram, normalizeGlyphMap, positionedGlyphs, prepareSvgForJsPdf, renderCurrentPixelPage, ownCurrentTextNumberWriter, ownCurrentMatrixNumberWriter, ownSourcePaintObserver, rewriteToUnicodeCMap, registerFontsWithJsPdf, embedSvgFonts, restorePdfUnicode };
});
