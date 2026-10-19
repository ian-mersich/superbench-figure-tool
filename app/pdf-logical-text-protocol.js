(function(root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.FigureStudioPdfLogicalTextProtocol = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function() {
'use strict';
// Staged source-semantic protocol. No installer, native write authority, or browser.
const SCHEMA = 'figureStudio.pdfLogicalTextEmission.v1';
const SOURCE_SCHEMA = 'figureStudio.pdfPositionedText.v2';
const INFO_KEY = 'FigureStudioLogicalTextV1';
const validatedMarkers = new WeakMap();
const validatedRuns = new WeakMap();
const captureIssuedMarkers = new WeakMap();
const bundledStyleFonts = new WeakMap();
const BUNDLED_STYLE_PROGRAMS = Object.freeze([
  ['normal', 'DejaVuSans.ttf', '3fdf69cabf06049ea70a00b5919340e2ce1e6d02b0cc3c4b44fb6801bd1e0d22', 0],
  ['bold', 'DejaVuSans-Bold.ttf', 'b184b89e3c1075f22f6b71575b6fc20d4972b3cfd3b23322ca6fd596dcaef167', 1],
  ['italic', 'DejaVuSans-Oblique.ttf', 'ccdf74b350f11fd3dd5774de50e5e6346a1a5da1f5b7d5fb83590665e97a5213', 2],
  ['bolditalic', 'DejaVuSans-BoldOblique.ttf', '6edf0283160186af451cbee71e7b845f2e4cabf264bb992ce668c83c25465e6f', 3]
]);
const STYLE_KEYS = ['fontFamily', 'fontSize', 'fontWeight', 'fontStyle'];
const bytes = value => Uint8Array.from(value, character => character.charCodeAt(0));
async function hash(value) {
  if (!globalThis.crypto?.subtle) refuse('Source digest provider unavailable.');
  const digest = new Uint8Array(await globalThis.crypto.subtle.digest('SHA-256', value));
  return Array.from(digest, value => value.toString(16).padStart(2, '0')).join('');
}
const clone = value => JSON.parse(JSON.stringify(value));
const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);
const finite = values => Array.isArray(values) && values.every(Number.isFinite);
function refuse(message) { const error = new Error(message); error.code = 'PDF_LOGICAL_TEXT_UNSUPPORTED'; throw error; }
function bundledFontFamily(style) {
  const suffix = {normal:'',bold:'-Bold',italic:'-Oblique',bolditalic:'-BoldOblique'}[style];
  if (suffix === undefined) refuse('The scientific font style is unsupported.');
  return 'FigureStudioUnicode' + suffix;
}
async function certifyBundledFontStyles(pdf) {
  const pending = [];
  for (const [style, filename, digest, bits] of BUNDLED_STYLE_PROGRAMS) {
    const fontName = bundledFontFamily(style);
    const font = pdf?.internal?.getFont?.(fontName, style), metadata = font?.metadata;
    if (!font || font.isStandardFont || font.fontName !== fontName || font.fontStyle !== style
        || font.postScriptName !== filename || !(metadata?.rawData instanceof Uint8Array)
        || metadata.head?.macStyle !== bits || metadata.os2?.selection !== (bits ? (bits & 1 ? 32 : 0) | (bits & 2 ? 1 : 0) : 64)
        || metadata.post?.italicAngle !== (bits & 2 ? -720896 : 0)
        || !Number.isSafeInteger(metadata.flags) || await hash(metadata.rawData) !== digest) {
      refuse('The bundled scientific font differs from its qualified native style program.');
    }
    pending.push({ pdf, font, fontName, style, filename, metadata, rawData: metadata.rawData, digest, bits,
      flags: (metadata.flags & ~(64 | 262144)) | (bits & 1 ? 262144 : 0) | (bits & 2 ? 64 : 0),
      italicAngle: metadata.post.italicAngle / 65536 });
  }
  // Set PDF descriptors from the actual program after all four inputs pass.
  // jsPDF otherwise leaves every bundled style at regular/zero inclination.
  for (const proof of pending) {
    proof.metadata.flags = proof.flags;
    proof.metadata.italicAngle = proof.italicAngle;
    bundledStyleFonts.set(proof.font, proof);
  }
  return pending.length;
}
function currentBundledStyle(font, pdf) {
  const proof = bundledStyleFonts.get(font);
  return proof?.pdf === pdf && font.fontName === proof.fontName && font.fontStyle === proof.style && font.postScriptName === proof.filename
    && font.metadata === proof.metadata && proof.metadata.rawData === proof.rawData
    && proof.metadata.flags === proof.flags && proof.metadata.italicAngle === proof.italicAngle
    && proof.metadata.head.macStyle === proof.bits ? proof : null;
}
function keys(object, expected) {
  if (!object || typeof object !== 'object' || Array.isArray(object) || !same(Object.keys(object).sort(), [...expected].sort())) refuse('Malformed or geometry-bearing logical text marker.');
}
function validateMarker(marker) {
  keys(marker, ['schema', 'producer', 'pageNumber', 'contentSha256', 'glyphFontStyleSha256', 'runs']);
  if (marker.schema !== SCHEMA || marker.producer !== 'FigureStudio.current-positioned-svg-emission' || marker.pageNumber !== 1 || !/^[a-f0-9]{64}$/.test(marker.contentSha256) || !/^[a-f0-9]{64}$/.test(marker.glyphFontStyleSha256) || !Array.isArray(marker.runs) || !marker.runs.length || marker.runs.length > 2048) refuse('Unqualified logical text marker.');
  if (JSON.stringify(marker).length > 2000000) refuse('Logical text marker byte budget exceeded.');
  let next = 0;
  for (const [index, run] of marker.runs.entries()) {
    keys(run, ['id', 'firstGlyph', 'glyphCount', 'unicode']);
    if (run.id !== `run-${index + 1}` || run.firstGlyph !== next || !Number.isSafeInteger(run.glyphCount) || run.glyphCount < 1 || typeof run.unicode !== 'string' || !run.unicode || /[\u0000-\u0008\u000b\u000c\u000e-\u001f\ud800-\udfff]/u.test(run.unicode)) refuse('Overlapping, ambiguous, incomplete or invalid logical run membership.');
    next += run.glyphCount;
    if (next > 30000) refuse('Logical text glyph budget exceeded.');
  }
  return marker;
}
function currentScalarParents(svgRoot) {
  const parents = Array.from(svgRoot?.querySelectorAll?.('text') || []);
  if (!parents.length) refuse('Current positioned source text parents unavailable.');
  return parents.map(parent => {
    const leaves = Array.from(parent.querySelectorAll('tspan'));
    const owners = leaves.length ? leaves : [parent];
    return { owner: parent, leaves: owners.map(owner => {
      if (owner.children?.length || [...String(owner.textContent || '')].length !== 1 || !owner.hasAttribute('data-pdf-unicode') || !owner.hasAttribute('data-pdf-glyph-map')) refuse('Current own-export text is not a scalar positioned source leaf.');
      let mapping;
      try { mapping = JSON.parse(owner.getAttribute('data-pdf-glyph-map')); } catch (_) { refuse('Malformed current source glyph map.'); }
      const unicode = owner.getAttribute('data-pdf-unicode'), fontChar = owner.textContent;
      if (!Array.isArray(mapping) || mapping.length !== 1 || mapping[0]?.unicode !== unicode || mapping[0]?.fontChar !== fontChar) refuse('Current source scalar Unicode/display mapping differs.');
      return { owner, unicode, fontChar };
    }) };
  });
}
// Transport is deliberately contingent on a writer supplying the current DOM
// parent at each actual native text emission. It never searches Unicode ranges.
function createEmissionCapture(parents, { pdf } = {}) {
  if (!Array.isArray(parents) || !parents.length || parents.length > 2048) refuse('Current source parent list unavailable.');
  const authority = new WeakMap(), runs = [], records = [];
  let active = null, finished = false, totalLeaves = 0;
  const usedStyleProofs = new Set();
  parents.forEach((parent, index) => {
    if (!parent?.owner || typeof parent.owner !== 'object' || authority.has(parent.owner) || !Array.isArray(parent.leaves) || !parent.leaves.length) refuse('Ambiguous current source parent identity.');
    const leaves = new WeakMap();
    const run = { id: `run-${index + 1}`, firstGlyph: 0, glyphCount: parent.leaves.length, unicode: '' };
    parent.leaves.forEach((leaf, leafIndex) => {
      if (++totalLeaves > 30000) refuse('Current source glyph budget exceeded.');
      if (!leaf?.owner || typeof leaf.owner !== 'object' || leaves.has(leaf.owner) || typeof leaf.unicode !== 'string' || !leaf.unicode || typeof leaf.fontChar !== 'string' || [...leaf.fontChar].length !== 1) refuse('Unsupported scalar source glyph leaf.');
      leaves.set(leaf.owner, { index: leafIndex, unicode: leaf.unicode, fontChar: leaf.fontChar });
      run.unicode += leaf.unicode;
    });
    authority.set(parent.owner, { index, leaves, count: 0 }); runs.push(run);
  });
  return {
    beforeText(parent, leaf, nativeText, pageRows) {
      if (finished || active) refuse('Nested or late source text emission.');
      const owner = authority.get(parent), glyph = owner?.leaves.get(leaf);
      if (!owner || !glyph || owner.index !== records.at(-1)?.runIndex && records.length && owner.index !== records.at(-1).runIndex + 1 || glyph.index !== owner.count || nativeText !== glyph.fontChar || !Array.isArray(pageRows)) refuse('Actual text emission does not match its exact current source owner/leaf/order.');
      if (!records.length && owner.index !== 0) refuse('Source text parent order changed.');
      const font = pdf?.internal?.getFont?.(), style = font?.fontStyle;
      if (!font?.postScriptName || !['normal', 'bold', 'italic', 'bolditalic'].includes(style) || !Number.isFinite(pdf.getFontSize())) refuse('Actual native writer font/style unavailable.');
      // jsPDF's embedded postScriptName is its VFS filename; /BaseFont is
      // fontName. Keep that actual native resource distinction explicit.
      // Styled embedded aliases need an additional source-program style proof.
      const styleProof = currentBundledStyle(font, pdf);
      if (bundledStyleFonts.has(font) && !styleProof) refuse('The native scientific font style changed during export.');
      if (!font.isStandardFont && style !== 'normal' && !styleProof) refuse('Styled embedded source program lacks native style certification.');
      if (styleProof) usedStyleProofs.add(styleProof);
      // Each certified embedded variant has its own program/family. PDF.js
      // exposes that program with normal CSS styling; adding bold/italic again
      // would synthesize a second style on top of its actual glyph outlines.
      const nativeFont = [font.isStandardFont ? font.postScriptName : font.fontName, pdf.getFontSize(),
        !styleProof && style.includes('bold') ? 'bold' : 'normal', !styleProof && style.includes('italic') ? 'italic' : 'normal'];
      active = { parent, leaf, runIndex: owner.index, unicode: glyph.unicode, nativeFont, start: pageRows.length, pageRows };
    },
    afterText(parent, leaf, pageRows) {
      if (!active || active.parent !== parent || active.leaf !== leaf || active.pageRows !== pageRows || pageRows.length <= active.start) refuse('Native text writer ownership or output unavailable.');
      const source = pageRows.slice(active.start);
      const body = source.join('\n');
      if ((body.match(/(?:^|\n)BT(?:\n|$)/g) || []).length !== 1 || (body.match(/(?:^|\n)ET(?:\n|$)/g) || []).length !== 1 || (body.match(/\sTj(?:\n|$)|\sTJ(?:\n|$)/g) || []).length !== 1) refuse('Native source leaf did not emit exactly one text object/show.');
      records.push({ ...active, end: pageRows.length, rows: source.slice() });
      authority.get(parent).count++; active = null;
    },
    async finish(decodedFinalContent) {
      if (finished || active || typeof decodedFinalContent !== 'string') refuse('Unfinished logical source emission.');
      for (const parent of parents) if (authority.get(parent.owner).count !== parent.leaves.length) refuse('Missing native source glyph emission.');
      if (records.length !== runs.reduce((sum, run) => sum + run.glyphCount, 0)) refuse('Extra or missing source glyph emissions.');
      const pageRows = records[0].pageRows;
      for (const proof of usedStyleProofs) {
        if (!currentBundledStyle(proof.font, pdf) || await hash(proof.rawData) !== proof.digest) refuse('The native scientific font program changed during export.');
      }
      // This exact prefix is the existing jsPDF page array; advanced API may
      // append one final Q while serializing. No substring/range matching.
      const body = pageRows.join('\n');
      if (decodedFinalContent !== body && decodedFinalContent !== body + '\nQ') refuse('Final native page content differs from captured writer output.');
      for (const record of records) if (!same(pageRows.slice(record.start, record.end), record.rows)) refuse('Captured native glyph segment changed.');
      let cursor = 0;
      for (const run of runs) { run.firstGlyph = cursor; cursor += run.glyphCount; }
      finished = true;
      const marker = validateMarker({ schema: SCHEMA, producer: 'FigureStudio.current-positioned-svg-emission', pageNumber: 1, contentSha256: await hash(bytes(decodedFinalContent)), glyphFontStyleSha256: await hash(new TextEncoder().encode(JSON.stringify(records.map(record => record.nativeFont)))), runs: clone(runs) });
      captureIssuedMarkers.set(marker, { fingerprint: JSON.stringify(marker), content: decodedFinalContent, contentSha256: marker.contentSha256, used: false, busy: false });
      return marker;
    },
  };
}
// Own-generated content only. The scalar decoder is trusted runtime code,
// never PDF metadata or a formatter's unverified certificate. No numeric
// spelling search, native text writer or source geometry is supplied here.
const CONTENT_BYTE_LIMIT = 4000000;
const CONTENT_TOKEN_LIMIT = 200000;
const NUMERIC_BYTE_LIMIT = 4096;
const PDF_DECIMAL = /^[+-]?(?:\d+(?:\.\d*)?|\.\d+)$/;
function* generatedContentTokenIterator(content, batched = false) {
  if (typeof content !== 'string' || content.length > CONTENT_BYTE_LIMIT * (batched ? 8 : 1)) refuse('Generated content byte budget exceeded or content unavailable.');
  for (let i = 0; i < content.length; i++) if (content.charCodeAt(i) > 255) refuse('Generated content is not an exact PDF byte string.');
  const whitespace = character => character === '\x00' || character === '\t' || character === '\n' || character === '\f' || character === '\r' || character === ' ';
  const delimiter = character => '()<>[]{}/%'.includes(character);
  const containers = [];
  let batchTokens=0,batchBytes=0;
  function push(kind, start, end) {
    if(end-start>CONTENT_BYTE_LIMIT)refuse('Generated lexical token exceeds its byte budget.');
    if(batched&&(batchTokens>=CONTENT_TOKEN_LIMIT||batchBytes+end-start>CONTENT_BYTE_LIMIT)){batchTokens=0;batchBytes=0;}
    if (batchTokens >= CONTENT_TOKEN_LIMIT) refuse('Generated content token budget exceeded.');
    batchTokens++;batchBytes+=end-start;
    return { kind, raw: content.slice(start, end) };
  }
  for (let i = 0; i < content.length;) {
    const start = i, character = content[i];
    if (whitespace(character)) {
      while (i < content.length && whitespace(content[i])) i++;
      yield push('bytes', start, i); continue;
    }
    if (character === '%') {
      while (i < content.length && content[i] !== '\n' && content[i] !== '\r') i++;
      yield push('bytes', start, i); continue;
    }
    if (character === '/') {
      i++;
      while (i < content.length && !whitespace(content[i]) && !delimiter(content[i])) i++;
      yield push('bytes', start, i); continue;
    }
    if (character === '(') {
      let depth = 1; i++;
      while (i < content.length && depth) {
        const current = content[i++];
        if (current === '\\') {
          if (i >= content.length) refuse('Unclosed generated literal string.');
          if (content[i++] === '\r' && content[i] === '\n') i++;
        } else if (current === '(') {
          if (++depth > 32) refuse('Generated literal string nesting budget exceeded.');
        } else if (current === ')') depth--;
      }
      if (depth) refuse('Unclosed generated literal string.');
      yield push('bytes', start, i); continue;
    }
    if (character === '<' && content[i + 1] !== '<') {
      i++;
      while (i < content.length && content[i] !== '>') {
        if (!whitespace(content[i]) && !/[a-f0-9]/i.test(content[i])) refuse('Malformed generated hexadecimal string.');
        i++;
      }
      if (i === content.length) refuse('Unclosed generated hexadecimal string.');
      yield push('bytes', start, ++i); continue;
    }
    if (character === '[' || character === '<' && content[i + 1] === '<') {
      const entry = character === '[' ? ']' : '>>';
      if (containers.length >= 32) refuse('Generated object nesting budget exceeded.');
      containers.push(entry); i += entry.length; yield push('bytes', start, i); continue;
    }
    if (character === ']' || character === '>' && content[i + 1] === '>') {
      const entry = character === ']' ? ']' : '>>';
      if (containers.pop() !== entry) refuse('Unbalanced generated content objects.');
      i += entry.length; yield push('bytes', start, i); continue;
    }
    if (delimiter(character)) refuse('Unsupported generated content delimiter.');
    while (i < content.length && !whitespace(content[i]) && !delimiter(content[i])) i++;
    const raw = content.slice(start, i);
    if (['BI', 'ID', 'EI'].includes(raw)) refuse('Inline image content is outside the generated numeric rebind scope.');
    const numeric = PDF_DECIMAL.test(raw);
    if (!numeric && /^[+\-.0-9]/.test(raw)) refuse('Unsupported generated numeric spelling.');
    if (numeric && (raw.length > NUMERIC_BYTE_LIMIT || !Number.isFinite(Number(raw)))) refuse('Nonfinite or over-budget generated decimal token.');
    yield push(numeric ? 'number' : 'bytes', start, i);
  }
  if (containers.length) refuse('Unclosed generated content objects.');
}
async function rebindGeneratedContent(marker, originalContent, rewrittenContent, { decodeNumericToken, yieldControl = () => new Promise(resolve => setTimeout(resolve, 0)), signal } = {}, batched = false) {
  validateMarker(marker);
  const issued = captureIssuedMarkers.get(marker);
  if (!issued || issued.used || issued.busy || issued.fingerprint !== JSON.stringify(marker) || originalContent !== issued.content) refuse('Numeric rebind requires an unchanged, unused marker issued by the exact current emission capture.');
  if (typeof decodeNumericToken !== 'function') refuse('Audited native decimal decoder unavailable.');
  if(batched&&typeof yieldControl!=='function')refuse('Generated numeric proof batches require a scheduler.');
  const cancelled=()=>{if(signal?.aborted){const error=new Error('Generated numeric proof was cancelled.');error.name='AbortError';throw error;}};
  issued.busy = true;
  try {
    cancelled();
    if (await hash(bytes(originalContent)) !== marker.contentSha256) refuse('Captured generated content digest changed.');
    cancelled();
    const original = generatedContentTokenIterator(originalContent,batched), rewritten = generatedContentTokenIterator(rewrittenContent,batched);
    let numericTokenCount = 0, changedNumericTokenCount = 0, signedZeroTokenCount = 0,tokenCount=0;
    while(true){
      const left=original.next(),right=rewritten.next();
      if(left.done!==right.done)refuse('Generated content token structure changed.');
      if(left.done)break;
      const before = left.value, after = right.value;
      tokenCount++;
      if(batched&&tokenCount%8192===0){cancelled();await yieldControl();cancelled();}
      if (before.kind !== after.kind) refuse('Generated content token kind changed.');
      if (before.kind !== 'number') {
        if (before.raw !== after.raw) refuse('Generated nonnumeric token or whitespace bytes changed.');
        continue;
      }
      const intended = Number(before.raw), finalNumber = Number(after.raw);
      if (!Object.is(intended, finalNumber)) refuse('Generated numeric value or signed zero changed.');
      let decoded;
      try { decoded = decodeNumericToken(after.raw); } catch (_) { refuse('Audited native decimal decoder rejected generated spelling.'); }
      if (typeof decoded !== 'number' || !Object.is(decoded, intended)) refuse('Final generated decimal does not preserve the audited native numeric value.');
      numericTokenCount++;
      if (before.raw !== after.raw) changedNumericTokenCount++;
      if (Object.is(intended, -0)) signedZeroTokenCount++;
    }
    if (issued.fingerprint !== JSON.stringify(marker)) refuse('Capture-issued marker changed during numeric proof.');
    const contentSha256 = await hash(bytes(rewrittenContent));
    if (issued.fingerprint !== JSON.stringify(marker)) refuse('Capture-issued marker changed during final digest.');
    const rebound = validateMarker({ ...clone(marker), contentSha256 });
    // This marker deliberately has no final native validation authority. The
    // rewritten PDF still needs validateNativeShows before attachMarker.
    cancelled();
    const proof = Object.freeze({ schema: 'figureStudio.ownGeneratedDecimalRebind.v1', originalContentSha256: issued.contentSha256, contentSha256, tokenCount, numericTokenCount, changedNumericTokenCount, signedZeroTokenCount, nonnumericBytesExact: true, numericValuesObjectIsExact: true, auditedDecoderEveryFinalNumericTokenExact: true, finalNativeShowsValidationRequired: true });
    issued.used = true; issued.content = null;
    return { marker: rebound, proof };
  } finally { issued.busy = false; }
}
function rebindOwnGeneratedContent(marker,originalContent,rewrittenContent,options){return rebindGeneratedContent(marker,originalContent,rewrittenContent,options,false);}
function rebindOwnGeneratedContentBatched(marker,originalContent,rewrittenContent,options){return rebindGeneratedContent(marker,originalContent,rewrittenContent,options,true);}
async function validatePackets(marker, decodedFinalContent, packets) {
  if (marker == null) return null; // Untagged external PDF route stays unchanged.
  validateMarker(marker);
  if (await hash(bytes(decodedFinalContent)) !== marker.contentSha256 || !Array.isArray(packets) || packets.length !== marker.runs.reduce((sum, run) => sum + run.glyphCount, 0)) refuse('Logical run source binding or native glyph count differs.');
  const result = marker.runs.map(run => {
    const members = packets.slice(run.firstGlyph, run.firstGlyph + run.glyphCount);
    if (members.some((packet, index) => typeof packet.unicode !== 'string' || !packet.unicode || typeof packet.fontChar !== 'string' || [...packet.fontChar].length !== 1 || !finite(packet.matrix) || packet.matrix.length !== 6 || !finite(packet.baseline) || packet.baseline.length !== 2 || typeof packet.fontFamily !== 'string' || !packet.fontFamily || typeof packet.sourceFontName !== 'string' || !packet.sourceFontName || typeof packet.sourceEmbeddedProgram !== 'boolean' || packet.sourceEmbeddedProgram && !/^[a-f0-9]{64}$/.test(packet.programSha256 || '') || !Number.isFinite(packet.fontSize) || packet.fontSize <= 0 || packet.sourceTextShowIndex !== run.firstGlyph + index || packet.nativeShowGlyphCount !== 1 || !Number.isSafeInteger(packet.paintOrdinal) || packet.paintOrdinal < 0)) refuse('Incomplete actual native glyph/font/geometry/paint-order packet.');
    if (members.some((packet, index) => index && packet.paintOrdinal !== members[index - 1].paintOrdinal + 1)) refuse('Intervening native paint separates one logical source run.');
    if (members.map(packet => packet.unicode).join('') !== run.unicode) refuse('Final decoded native Unicode does not match source-emitted membership.');
    return { id: run.id, unicode: run.unicode, members };
  });
  const fontStyles = packets.map(packet => [packet.sourceFontName, packet.nativeFontSize ?? packet.fontSize, packet.nativeFontWeight ?? packet.fontWeight ?? 'normal', packet.nativeFontStyle ?? packet.fontStyle ?? 'normal']);
  if (await hash(new TextEncoder().encode(JSON.stringify(fontStyles))) !== marker.glyphFontStyleSha256) refuse('Final decoded native font/style source differs from actual observed emission.');
  validatedMarkers.set(marker, JSON.stringify(marker));
  for (const run of result) validatedRuns.set(run, JSON.stringify(run));
  return result;
}
async function validateNativeShows(marker, decodedFinalContent, shows) {
  validateMarker(marker);
  if (await hash(bytes(decodedFinalContent)) !== marker.contentSha256 || !Array.isArray(shows) || shows.length !== marker.runs.reduce((sum, run) => sum + run.glyphCount, 0)) refuse('Native source text show count/content differs from actual emission.');
  for (const run of marker.runs) {
    const members = shows.slice(run.firstGlyph, run.firstGlyph + run.glyphCount);
    if (members.some((show, index) => show.sourceTextShowIndex !== run.firstGlyph + index || show.nativeShowGlyphCount !== 1 || typeof show.unicode !== 'string' || !show.unicode || typeof show.sourceFontName !== 'string' || !show.sourceFontName || !Number.isFinite(show.fontSize) || show.fontSize <= 0 || !Number.isSafeInteger(show.paintOrdinal) || index && show.paintOrdinal !== members[index - 1].paintOrdinal + 1) || members.map(show => show.unicode).join('') !== run.unicode) refuse('Actual source text Unicode/order/contiguous paint differs from source-emitted membership.');
  }
  const styles = shows.map(show => [show.sourceFontName, show.fontSize, show.fontWeight || 'normal', show.fontStyle || 'normal']);
  if (await hash(new TextEncoder().encode(JSON.stringify(styles))) !== marker.glyphFontStyleSha256) refuse('Actual decoded native font/style differs from source emission.');
  validatedMarkers.set(marker, JSON.stringify(marker));
  return true;
}
function capturedStyle(declaration) { return Object.fromEntries(STYLE_KEYS.map(key => [key, declaration[key]])); }
function fontSourceKey(declaration) { return JSON.stringify([declaration.fontFamily, declaration.fontWeight || 'normal', declaration.fontStyle || 'normal']); }
function sourceFontFor(source, declaration) { return source?.fontSources?.[fontSourceKey(declaration)]; }
function sourceStylesMatch(object, source) {
  if (source?.schema !== SOURCE_SCHEMA || !source.capture || !same(object.styles || {}, source.capture.styles) || !same([object.charSpacing || 0, object.textAlign, object.lineHeight], source.capture.baseLayout)) return false;
  if (!Array.isArray(source.capture.declarations) || source.capture.declarations.length !== object._textLines?.[0]?.length) return false;
  return source.capture.declarations.every((declaration, index) => same(capturedStyle(object.getCompleteStyleDeclaration(0, index)), declaration));
}
function clipIdentity(clip) {
  keys(clip, ['schema', 'scopes']);
  if (clip.schema !== 'figureStudio.decodedEffectiveClip.v1' || !Array.isArray(clip.scopes) || clip.scopes.length > 16) refuse('Actual effective native clip is unavailable or unsupported.');
  return clip.scopes.map(scope => {
    keys(scope, ['kind', 'points', 'rule', 'inverted', 'source', 'sourceOperatorIndex']);
    if (scope.kind !== 'rect' || scope.source !== 'decoded-pdf' || !Number.isSafeInteger(scope.sourceOperatorIndex) || scope.sourceOperatorIndex < 0 || !['nonzero', 'evenodd'].includes(scope.rule) || scope.inverted !== false || !Array.isArray(scope.points) || scope.points.length !== 4 || !scope.points.every(point => finite(point) && point.length === 2)) refuse('Only exact decoded rectangular clip scopes are currently supported.');
    const cross = scope.points.map((p, i, a) => { const q = a[(i + 1) % 4], r = a[(i + 2) % 4]; return (q[0] - p[0]) * (r[1] - q[1]) - (q[1] - p[1]) * (r[0] - q[0]); });
    if (cross.some(value => !Number.isFinite(value) || !value || Math.sign(value) !== Math.sign(cross[0]))) refuse('Degenerate or unsupported decoded rectangle clip.');
    // Repeated q/clip emission may use different operation indices. Compare
    // ordered actual geometry/rule, retaining the first decoded source index.
    return { kind: scope.kind, points: scope.points, rule: scope.rule, inverted: scope.inverted };
  });
}
function combineNativeRun(run) {
  if (!run?.members?.length || validatedRuns.get(run) !== JSON.stringify(run)) refuse('Native source run lacks unchanged final source validation.');
  const first = run.members[0];
  if (typeof first.fill !== 'string' || !first.fill) refuse('Only a common solid current source fill is supported.');
  const frame = first.matrix.slice(), determinant = frame[0] * frame[3] - frame[1] * frame[2];
  if (!determinant || !Number.isFinite(determinant)) refuse('Singular native source text frame.');
  // Translation is the decoded first baseline, never an original scene pose.
  frame[4] = first.baseline[0]; frame[5] = first.baseline[1];
  const inverse = [frame[3] / determinant, -frame[1] / determinant, -frame[2] / determinant, frame[0] / determinant];
  const firstClip = clipIdentity(first.effectiveClip);
  const glyphs = [], styles = {}, fontSources = {}, declarations = [];
  let cursor = 0;
  for (const packet of run.members) {
    // Retain the actual common decoded clip, including an active page crop.
    // No inactivity claim is made. Different/unknown clips remain unsupported.
    if (!same(packet.matrix.slice(0, 4), frame.slice(0, 4)) || !same(clipIdentity(packet.effectiveClip), firstClip) || !same(packet.compositingScope, first.compositingScope) || packet.compositingScope !== 'source-over' || packet.opacity !== 1 || packet.stroke != null || packet.fill !== first.fill) refuse('Incompatible native glyph frame/effective clip/compositing.');
    const dx = packet.baseline[0] - frame[4], dy = packet.baseline[1] - frame[5];
    const declaration = { fontFamily: packet.fontFamily, fontSize: packet.fontSize, fontWeight: packet.fontWeight || 'normal', fontStyle: packet.fontStyle || 'normal' };
    const chars = [...packet.unicode];
    for (const [offset] of chars.entries()) { styles[cursor + offset] = clone(declaration); declarations.push(clone(declaration)); }
    const sourceFontKey = fontSourceKey(declaration);
    const entry = fontSources[sourceFontKey] ||= { fontFamily: packet.fontFamily, fontWeight: declaration.fontWeight, fontStyle: declaration.fontStyle, sourceFontName: packet.sourceFontName, sourceEmbeddedProgram: packet.sourceEmbeddedProgram, programSha256: packet.programSha256 || null, map: {}, unicodeAdvances: {} };
    if (entry.sourceFontName !== packet.sourceFontName || entry.sourceEmbeddedProgram !== packet.sourceEmbeddedProgram || entry.programSha256 !== (packet.programSha256 || null) || Object.hasOwn(entry.map, packet.unicode) && entry.map[packet.unicode] !== packet.fontChar) refuse('Ambiguous source font family/program/display mapping.');
    entry.map[packet.unicode] = packet.fontChar;
    if (/^\s+$/u.test(packet.unicode) && Number.isFinite(packet.sourceAdvance)) entry.unicodeAdvances[packet.unicode] = packet.sourceAdvance;
    glyphs.push({ unicode: packet.unicode, fontChar: packet.fontChar, charIndex: cursor, charCount: chars.length, x: inverse[0] * dx + inverse[2] * dy, y: inverse[1] * dx + inverse[3] * dy, sourceFontFamily: packet.fontFamily, sourceFontKey });
    cursor += chars.length;
  }
  const options = { text: run.unicode, fontFamily: first.fontFamily, fontSize: first.fontSize, fontWeight: first.fontWeight || 'normal', fontStyle: first.fontStyle || 'normal', styles: { 0: styles }, fill: first.fill, stroke: null, opacity: 1, charSpacing: 0, textAlign: 'left', lineHeight: 1.16 };
  const retainedClips = first.effectiveClip.scopes.map(scope => ({ ...clone(scope), localPoints: scope.points.map(point => { const dx = point[0] - frame[4], dy = point[1] - frame[5]; return [inverse[0] * dx + inverse[2] * dy, inverse[1] * dx + inverse[3] * dy]; }) }));
  const source = { schema: SOURCE_SCHEMA, text: run.unicode, anchor: 'start', fontFamily: options.fontFamily, fontSize: options.fontSize, fontWeight: options.fontWeight, fontStyle: options.fontStyle, glyphs, map: {}, fontSources, fallbackFont: 'Arial', nativeClipSources: clone(first.effectiveClip), logicalSourceMembership: { schema: SCHEMA, runId: run.id, nativeGlyphCount: glyphs.length, originalPdfWriterAuthority: false }, capture: { styles: clone(options.styles), baseLayout: [0, 'left', 1.16], declarations } };
  return { frame, options, source, retainedClips };
}
function createNativeText(model, fabric, TextClass) {
  const text = new TextClass(model.options.text, { ...clone(model.options), pdfTextSource: clone(model.source), strokeWidth: 0, originX: 'center', originY: 'center', objectCaching: false });
  const anchor = text._pdfAnchorPoint();
  const pose = fabric.util.multiplyTransformMatrices(model.frame, [1, 0, 0, 1, -anchor.x, -anchor.y]);
  fabric.util.applyTransformToObject(text, pose);
  const clips = model.retainedClips.map(scope => {
    const points = scope.localPoints.map(point => [point[0] + anchor.x, point[1] + anchor.y]);
    const commands = points.map((point, index) => [index ? 'L' : 'M', ...point]); commands.push(['Z']);
    const clip = new fabric.Path(commands, { fill: '#000000', fillRule: scope.rule, stroke: null, strokeWidth: 0, originX: 'center', originY: 'center', inverted: false, absolutePositioned: false });
    clip.set({ left: clip.pathOffset.x, top: clip.pathOffset.y });
    return clip;
  });
  const ownClipFrames = clips.map(clip => clip.calcOwnMatrix());
  for (let i = 0; i + 1 < clips.length; i++) {
    fabric.util.applyTransformToObject(clips[i + 1], fabric.util.multiplyTransformMatrices(fabric.util.invertTransform(ownClipFrames[i]), ownClipFrames[i + 1]));
    clips[i].clipPath = clips[i + 1];
  }
  if (clips.length) text.clipPath = clips[0];
  return text;
}
async function readContent(pdfBytes, pdfLib) {
  const document = await pdfLib.PDFDocument.load(pdfBytes), page = document.getPages()[0];
  if (document.getPageCount() !== 1) refuse('Logical text protocol currently supports one generated page.');
  const raw = page.node.get(pdfLib.PDFName.of('Contents'));
  const object = document.context.lookup(raw);
  const streams = object instanceof pdfLib.PDFArray ? object.asArray().map(ref => document.context.lookup(ref)) : [object];
  if (streams.length !== 1 || !(streams[0] instanceof pdfLib.PDFRawStream)) refuse('Generated source content stream structure changed.');
  const bytes = pdfLib.decodePDFRawStream(streams[0]).decode();
  return { document, content: Array.from(bytes, value => String.fromCharCode(value)).join('') };
}
async function attachMarker(pdfBytes, marker, pdfLib) {
  validateMarker(marker);
  if (validatedMarkers.get(marker) !== JSON.stringify(marker)) refuse('Logical membership lacks final native decoded Unicode/font/style validation or changed after validation.');
  const { document, content } = await readContent(pdfBytes, pdfLib);
  if (await hash(bytes(content)) !== marker.contentSha256) refuse('Final source content changed before attaching logical membership.');
  const name = pdfLib.PDFName.of;
  let info = document.context.lookup(document.context.trailerInfo.Info);
  if (!info) { info = document.context.obj({}); document.context.trailerInfo.Info = document.context.register(info); }
  if (info.has(name(INFO_KEY))) refuse('Generated PDF already has conflicting logical membership.');
  info.set(name(INFO_KEY), pdfLib.PDFHexString.fromText(JSON.stringify(marker)));
  return document.save({ useObjectStreams: false });
}
async function readMarker(pdfBytes, pdfLib) {
  const document = await pdfLib.PDFDocument.load(pdfBytes);
  const info = document.context.lookup(document.context.trailerInfo.Info);
  const value = info?.get(pdfLib.PDFName.of(INFO_KEY));
  if (!value) return null;
  if (!(value instanceof pdfLib.PDFHexString) && !(value instanceof pdfLib.PDFString)) refuse('Logical source marker is not a native PDF string.');
  let marker;
  try { marker = JSON.parse(value.decodeText()); } catch (_) { refuse('Logical source marker is malformed.'); }
  validateMarker(marker);
  const { content } = await readContent(pdfBytes, pdfLib);
  if (await hash(bytes(content)) !== marker.contentSha256) refuse('Logical source marker content binding is stale.');
  return marker;
}
function installInstanceObserver(pdf, capture) {
  const key = '__figureStudioLogicalTextObserver';
  if (!pdf?.internal?.pages || typeof pdf.internal.getCurrentPageInfo !== 'function' || key in pdf) refuse('Native per-instance observer property unavailable or already owned.');
  const rows = () => {
    const page = pdf.internal.getCurrentPageInfo().pageNumber;
    if (page !== 1) refuse('Source-owner observer supports one current generated page.');
    return pdf.internal.pages[page];
  };
  const observer = { beforeText(parent, leaf, text) { capture.beforeText(parent, leaf, text, rows()); }, afterText(parent, leaf) { capture.afterText(parent, leaf, rows()); } };
  Object.defineProperty(pdf, key, { value: observer, configurable: true });
  let detached = false;
  return function detach() {
    if (detached) return;
    if (Object.getOwnPropertyDescriptor(pdf, key)?.value !== observer) refuse('Source observer ownership changed before cleanup.');
    delete pdf[key]; detached = true;
  };
}
return { SCHEMA, SOURCE_SCHEMA, INFO_KEY, bundledFontFamily, certifyBundledFontStyles, validateMarker, currentScalarParents, createEmissionCapture, installInstanceObserver, rebindOwnGeneratedContent, rebindOwnGeneratedContentBatched, validateNativeShows, validatePackets, capturedStyle, fontSourceKey, sourceFontFor, sourceStylesMatch, clipIdentity, combineNativeRun, createNativeText, readContent, attachMarker, readMarker };
});
