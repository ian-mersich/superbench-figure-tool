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

  function prepareSvgForJsPdf(svgRoot) {
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

  async function renderCurrentPixelPage(pdf, svg, { widthPt, heightPt, qualifiedSourceScene = false } = {}) {
    if (!qualifiedSourceScene || svg?.localName !== "svg" || svg?.namespaceURI !== SVG_NS
        || ![widthPt, heightPt].every(value => Number.isFinite(value) && value > 0)
        || !["advancedAPI", "compatAPI", "isAdvancedAPI", "saveGraphicsState", "restoreGraphicsState", "setCurrentTransformationMatrix", "Matrix", "svg"].every(key => typeof pdf?.[key] === "function")) {
      fail("PDF_EXPORT_CURRENT_PAGE_UNSUPPORTED", "The current PDF page-coordinate export is unavailable.");
    }
    const widthPx = widthPt * 96 / 72, heightPx = heightPt * 96 / 72;
    const box = String(svg?.getAttribute?.("viewBox") || "").trim().split(/[ ,]+/).map(Number);
    if (box.length !== 4 || !box.every(Number.isFinite) || box[0] !== 0 || box[1] !== 0
        || !Object.is(box[2], widthPx) || !Object.is(box[3], heightPx)
        || !Object.is(pdf.internal?.pageSize?.getWidth?.(), widthPt) || !Object.is(pdf.internal?.pageSize?.getHeight?.(), heightPt)) {
      fail("PDF_EXPORT_CURRENT_PAGE_UNSUPPORTED", "This export region cannot preserve its current page-coordinate planes exactly.");
    }
    const wasAdvanced = pdf.isAdvancedAPI();
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
      finally { if (!wasAdvanced) pdf.compatAPI(); }
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

  return { SCHEMA, detectFontProgram, normalizeGlyphMap, positionedGlyphs, prepareSvgForJsPdf, renderCurrentPixelPage, ownSourcePaintObserver, rewriteToUnicodeCMap, registerFontsWithJsPdf, embedSvgFonts, restorePdfUnicode };
});
