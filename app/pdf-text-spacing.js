(function (root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  if (root) root.FigureStudioPdfTextSpacing = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";
  const SCHEMA = "figureStudio.pdfRecoveredWordSpacing.v1";
  const isGlyph = (value) => value && typeof value === "object";
  const whitespace = (glyph) => /^\s+$/u.test(glyph?.unicode || "");
  const multiply = (a, b) => [a[0]*b[0]+a[2]*b[1],a[1]*b[0]+a[3]*b[1],a[0]*b[2]+a[2]*b[3],a[1]*b[2]+a[3]*b[3],a[0]*b[4]+a[2]*b[5]+a[4],a[1]*b[4]+a[3]*b[5]+a[5]];

  // Only a source-mapped U+0020 width is evidence. PDF.js's fallback to the
  // widths of minus/one/i is useful for extraction, but cannot prove a space.
  function sourceSpaceWidth(font) {
    // Composite fonts index widths by CID, whereas toUnicode can index source
    // character codes. That correspondence needs a separate proven CMap path.
    if (font?.composite) return null;
    const widths = font?.widths || {};
    const unicode = font?.toUnicode?._map || [];
    const values = new Set();
    for (const key of Object.keys(widths)) {
      const code = Number(key);
      const value = Number(widths[key]);
      const name = font?.differences?.[code] || font?.defaultEncoding?.[code];
      if (Number.isFinite(value) && value > 0 && (unicode[code] === " " || !unicode[code] && name === "space")) values.add(value);
    }
    return values.size === 1 ? [...values][0] : null;
  }

  function textTransform(state, ctm) {
    const local = [state.fontSize * state.textHScale, 0, 0, state.fontSize, state.x || 0, (state.y || 0) + (state.textRise || 0)];
    return multiply(ctm, multiply(state.textMatrix, local));
  }

  function planWordSpaces(glyphs, state, { textItems = [], ctm = [1, 0, 0, 1, 0, 0], fontName = state?.font?.loadedName } = {}) {
    const original = (glyphs || []).filter(isGlyph);
    const unchanged = { schema: SCHEMA, glyphs: original, insertions: [], status: "unchanged" };
    const font = state?.font;
    const spaceWidth = sourceSpaceWidth(font);
    // Negative font direction, vertical writing and nonstandard font matrices
    // have different advance conventions. Keep those unchanged, never guess.
    if (!spaceWidth || font?.vertical || state.fontDirection !== 1 || !(state.fontSize > 0) || !(state.fontSizeScale > 0) || state.fontMatrix?.[0] !== .001 || state.fontMatrix?.[1] !== 0) return unchanged;
    let x = 0, inkIndex = 0;
    const output = [], insertions = [];
    for (let index = 0; index < glyphs.length; index += 1) {
      const glyph = glyphs[index];
      if (glyph === null) { x += state.wordSpacing; continue; }
      if (typeof glyph === "number") {
        const before = glyphs[index - 1], after = glyphs[index + 1], units = -glyph;
        // One positive gap, near the real source space width, between visible
        // glyphs. Tiny kerning and wide column/panel separations are excluded.
        if (isGlyph(before) && isGlyph(after) && before.unicode && after.unicode && !whitespace(before) && !whitespace(after) && units >= .9 * spaceWidth && units <= 1.1 * spaceWidth) {
          const space = { unicode: " ", fontChar: " ", width: units, isInFont: true, zeroInk: true, spacingSource: "TJ", sourceAdjustment: glyph };
          output.push(space);
          insertions.push({ beforeGlyphIndex: inkIndex, x: state.x + x / state.fontSizeScale, sourceAdjustment: glyph });
        }
        x += -glyph * state.fontSize / 1000;
        continue;
      }
      if (!isGlyph(glyph)) return unchanged;
      output.push(glyph); inkIndex += 1;
      x += glyph.width * state.fontSize * state.fontMatrix[0] + (glyph.isSpace ? state.wordSpacing : 0) + state.charSpacing;
    }
    if (!insertions.length) return unchanged;
    const expected = textTransform(state, ctm), recovered = output.map((glyph) => glyph.unicode || "").join("");
    const matching = textItems.filter((item) => item.dir === "ltr" && item.fontName === fontName && item.str === recovered && item.transform?.length === 6 && item.transform.every((value, index) => Math.abs(value - expected[index]) <= 1e-5));
    // Require extraction correspondence at this exact source position as well
    // as the font/TJ evidence. This does not infer words from label meaning.
    if (matching.length !== 1) return unchanged;
    return { schema: SCHEMA, glyphs: output, insertions, status: "recovered", reference: { fontName: matching[0].fontName, transform: matching[0].transform.slice() } };
  }

  // Called after the original SVGGraphics.showText(glyphs). It inserts only
  // zero-ink slots; original operators, current.x and every ink x stay intact.
  function mergeSpacePositions(originalPositions, prefixLength, insertions) {
    const result = originalPositions.slice();
    let added = 0;
    for (const insertion of insertions) {
      result.splice(prefixLength + insertion.beforeGlyphIndex + added, 0, insertion.x);
      added += 1;
    }
    return result;
  }
  return { SCHEMA, sourceSpaceWidth, textTransform, planWordSpaces, mergeSpacePositions };
});
