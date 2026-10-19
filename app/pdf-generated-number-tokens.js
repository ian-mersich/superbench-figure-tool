/* Current own-generated PDF content only. No external source is normalized.
 * Equivalent decimal operands must retain their exact intended Number value
 * under native conversion and the audited PDF.js 3.11.174 decimal lexer.
 */
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.FigureStudioPdfGeneratedNumbers = api;
})(typeof globalThis === 'object' ? globalThis : this, function () {
  'use strict';
  const DECIMAL = /^[+-]?(?:\d+\.?\d*|\.\d+)$/;
  const LIMITS = Object.freeze({ contentBytes: 32000000, numericTokens: 250000, uniqueNumbers: 4096, tokenLength: 256 });
  const WHITESPACE = /[\0\t\n\f\r ]/;
  const WORDS = new Set(('b B b* B* BDC BMC BT BX c cm CS cs d d0 d1 Do DP EMC ET EX f F f* G g gs h i j J K k l m M MP n q Q re RG rg ri s S SC sc SCN scn sh T* Tc Td TD Tf Tj TJ TL Tm Tr Ts Tw Tz v w W W* y \" \' true false null').split(' '));

  function refuse(message) {
    const error = new Error(message);
    error.code = 'PDF_GENERATED_NUMBER_UNSUPPORTED';
    throw error;
  }

  // Arithmetic order of the bundled strict legal-decimal Lexer branch.
  // Actual native worker decoding is independently tested before qualification.
  function auditedDecimal(token) {
    if (!DECIMAL.test(token)) refuse('Generated numbers require PDF decimal tokens without exponents.');
    let sign = 1, index = 0;
    if (token[0] === '-' || token[0] === '+') {
      if (token[0] === '-') sign = -1;
      index++;
    }
    let mantissa = 0, divisor = 1, decimal = false;
    for (; index < token.length; index++) {
      if (token[index] === '.') { decimal = true; continue; }
      mantissa = mantissa * 10 + (token.charCodeAt(index) - 48);
      if (decimal) divisor *= 10;
    }
    return sign * (mantissa / divisor);
  }

  function expandExponent(token) {
    if (!/[eE]/.test(token)) return token;
    const [significand, exponent] = token.toLowerCase().split('e');
    const negative = significand[0] === '-', unsigned = negative ? significand.slice(1) : significand;
    const point = unsigned.indexOf('.'), digits = unsigned.replace('.', '');
    const position = (point < 0 ? unsigned.length : point) + Number(exponent);
    const body = position <= 0 ? '0.' + '0'.repeat(-position) + digits
      : position >= digits.length ? digits + '0'.repeat(position - digits.length)
        : digits.slice(0, position) + '.' + digits.slice(position);
    return (negative ? '-' : '') + body;
  }

  function fraction(bits) {
    const exponent = Number((bits >> 52n) & 2047n);
    if (exponent === 2047) return null;
    const mantissa = (bits & ((1n << 52n) - 1n)) + (exponent ? 1n << 52n : 0n);
    const power = (exponent ? exponent - 1023 : 1 - 1023) - 52;
    return [power >= 0 ? mantissa << BigInt(power) : mantissa, power < 0 ? 1n << BigInt(-power) : 1n];
  }

  function midpoint(a, b) { return [a[0] * b[1] + b[0] * a[1], 2n * a[1] * b[1]]; }

  function decimalInteger(integer, places, negative) {
    const digits = integer.toString().padStart(places + 1, '0');
    return (negative ? '-' : '') + (places ? digits.slice(0, -places) + '.' + digits.slice(-places) : digits);
  }

  function number(value) {
    if (!Number.isFinite(value)) refuse('Generated PDF operand must be finite.');
    if (Object.is(value, -0)) return '-0';
    const accepts = token => token.length <= LIMITS.tokenLength && DECIMAL.test(token)
      && Object.is(Number(token), value) && Object.is(auditedDecimal(token), value);
    let token = expandExponent(String(value));
    if (accepts(token)) return token;
    for (let places = 0; places <= 100; places++) {
      token = expandExponent(value.toFixed(places));
      if (accepts(token)) return token;
    }
    for (let digits = 1; digits <= 100; digits++) {
      token = expandExponent(value.toPrecision(digits));
      if (accepts(token)) return token;
    }

    // Search equivalent rationals only inside the exact Float64 rounding
    // interval. The bounded search never accepts a neighboring Number.
    const view = new DataView(new ArrayBuffer(8));
    view.setFloat64(0, Math.abs(value));
    const bits = view.getBigUint64(0), exact = fraction(bits);
    const previous = fraction(bits - 1n), next = fraction(bits + 1n);
    if (!previous || !next) refuse('Generated operand lies outside the qualified decimal search range.');
    const lower = midpoint(previous, exact), upper = midpoint(exact, next);
    // Some exact operands need a long equivalent spelling because of the
    // native lexer's repeated-digit arithmetic. Search through the existing
    // token budget; accepts still requires both parsers to return this exact
    // Number and rejects every over-budget or neighboring-value token.
    let scale = 1n;
    for (let places = 0; places <= LIMITS.tokenLength; places++, scale *= 10n) {
      const first = lower[0] * scale / lower[1], last = upper[0] * scale / upper[1];
      const center = exact[0] * scale / exact[1], integers = new Set();
      for (let offset = -8n; offset <= 8n; offset++) {
        integers.add(first + offset); integers.add(last + offset); integers.add(center + offset);
      }
      for (let sample = 1n; sample < 16n; sample++) integers.add(first + (last - first) * sample / 16n);
      for (const integer of integers) {
        if (integer < 0n) continue;
        token = decimalInteger(integer, places, value < 0);
        if (accepts(token)) return token;
      }
    }
    refuse(`Current operand ${Object.is(value, -0) ? '-0' : String(value)} has no qualified exact decimal spelling within the bounded search.`);
  }

  const delimiter = char => !char || WHITESPACE.test(char) || /[\[\]()<>\/%{}]/.test(char);
  function* scanTokens(text, enforceAggregateNumericBudget = true) {
    if (typeof text !== 'string' || text.length > LIMITS.contentBytes) refuse('Generated content byte-string exceeds its budget.');
    for (let index = 0; index < text.length; index++) if (text.charCodeAt(index) > 255) refuse('Generated content must retain native byte-string values.');
    let index = 0, numericTokens = 0;
    while (index < text.length) {
      const start = index, char = text[index];
      let kind = 'other';
      if (WHITESPACE.test(char)) { while (index < text.length && WHITESPACE.test(text[index])) index++; }
      else if (char === '%') { while (index < text.length && !/[\r\n]/.test(text[index])) index++; }
      else if (char === '/') { index++; while (index < text.length && !delimiter(text[index])) index++; }
      else if (char === '(') {
        let depth = 1; index++;
        while (index < text.length && depth) {
          const next = text[index++];
          if (next === '\\') {
            if (text[index] === '\r' && text[index + 1] === '\n') index += 2;
            else if (index < text.length) index++;
          } else if (next === '(') depth++;
          else if (next === ')') depth--;
        }
        if (depth) refuse('Generated literal string is unbalanced.');
      } else if (char === '<' && text[index + 1] !== '<') {
        index++;
        while (index < text.length && text[index] !== '>') {
          if (!/[0-9a-fA-F]/.test(text[index]) && !WHITESPACE.test(text[index])) refuse('Generated hex string has unsupported bytes.');
          index++;
        }
        if (index === text.length) refuse('Generated hex string is unbalanced.');
        index++;
      } else if (char === '<' && text[index + 1] === '<') index += 2;
      else if (char === '>' && text[index + 1] === '>') index += 2;
      else if ('[]'.includes(char)) index++;
      else if (')>{}'.includes(char)) refuse('Generated content has an unexpected delimiter.');
      else {
        while (index < text.length && !delimiter(text[index])) index++;
        if (index === start) refuse('Generated token is unsupported.');
        const token = text.slice(start, index);
        if (token === 'BI' || token === 'ID' || token === 'EI') refuse('Inline image content is outside numeric spelling qualification.');
        if (DECIMAL.test(token)) {
          if (++numericTokens > LIMITS.numericTokens && enforceAggregateNumericBudget) refuse(`Generated content exceeds its ${LIMITS.numericTokens}-numeric-token qualification budget.`);
          if (token.length > LIMITS.tokenLength) refuse(`Generated operand at offset ${start} exceeds its ${LIMITS.tokenLength}-character qualification budget (${token.length} characters).`);
          if (!Number.isFinite(Number(token))) refuse(`Generated operand at offset ${start} is not finite.`);
          kind = 'number';
        } else if (/^[+\-.0-9]/.test(token)) refuse('Generated numeric operand has unqualified syntax.');
        else if (!WORDS.has(token)) refuse('Generated content operator is outside the audited grammar.');
      }
      yield { kind, offset: start, text: text.slice(start, index) };
    }
  }
  function tokenize(text) {
    const tokens = Array.from(scanTokens(text));
    return { tokens, numericTokens: tokens.filter(token => token.kind === 'number').length };
  }

  function certifyRewrite(original, rewritten) {
    const before = tokenize(original), after = tokenize(rewritten);
    if (before.tokens.length !== after.tokens.length) refuse('Generated rewrite changed token structure.');
    let changedTokens = 0;
    for (let index = 0; index < before.tokens.length; index++) {
      const a = before.tokens[index], b = after.tokens[index];
      if (a.kind !== b.kind) refuse('Generated rewrite changed token kind.');
      if (a.kind !== 'number') {
        if (a.text !== b.text) refuse('Generated rewrite changed nonnumeric content bytes.');
      } else {
        const intended = Number(a.text);
        if (!Object.is(Number(b.text), intended) || !Object.is(auditedDecimal(b.text), intended)) refuse('Generated rewrite changed intent or is not lexer exact.');
        if (a.text !== b.text) changedTokens++;
      }
    }
    return Object.freeze({ numericTokens: before.numericTokens, changedTokens });
  }

  function rewriteOwnedContent(text) {
    const inspected = tokenize(text), cache = new Map(), changes = [];
    const pieces = inspected.tokens.map((token, index) => {
      if (token.kind !== 'number') return token.text;
      const value = Number(token.text), key = Object.is(value, -0) ? '-0' : String(value);
      if (!cache.has(key)) {
        if (cache.size >= LIMITS.uniqueNumbers) refuse('Generated number search exceeds its unique-value budget.');
        try { cache.set(key, number(value)); }
        catch (error) {
          if (error?.code === 'PDF_GENERATED_NUMBER_UNSUPPORTED') {
            const operator = inspected.tokens.slice(index + 1).find(next => next.kind !== 'number' && /^[A-Za-z*'"]+$/.test(next.text));
            error.message += ` Content offset ${token.offset}, operator ${operator?.text || 'unknown'}.`;
          }
          throw error;
        }
      }
      const replacement = cache.get(key);
      if (replacement !== token.text) changes.push({ offset: token.offset, original: token.text, replacement, value });
      return replacement;
    });
    const content = pieces.join(''), proof = certifyRewrite(text, content);
    return { content, ...proof, uniqueNumbers: cache.size, changes };
  }

  async function rewriteOwnedContentBatched(text, { yieldControl = () => new Promise(resolve => setTimeout(resolve, 0)), signal } = {}) {
    if (typeof yieldControl !== 'function') refuse('Generated numeric batches require a scheduler.');
    // The established whole byte envelope still applies. Each independent
    // proof retains the original token, unique-value and decimal budgets.
    const output = [];
    let originals = [], replacements = [], cache = new Map(), numericTokens = 0, changedTokens = 0, batchCount = 0, maxBatchUniqueNumbers = 0, batchBytes=0, maxBatchBytes=0;
    const cancelled=()=>{if(signal?.aborted){const error=new Error('Generated numeric encoding was cancelled.');error.name='AbortError';throw error;}};
    async function finishBatch() {
      if (!originals.length) return;
      cancelled();
      const before = originals.join(''), after = replacements.join(''), proof = certifyRewrite(before, after);
      if(before.length>4000000||after.length>4000000)refuse('Generated numeric batch exceeds the existing four-million-byte lexical proof envelope.');
      numericTokens += proof.numericTokens; changedTokens += proof.changedTokens;
      maxBatchUniqueNumbers = Math.max(maxBatchUniqueNumbers,cache.size);
      maxBatchBytes=Math.max(maxBatchBytes,before.length,after.length);
      output.push(after);batchCount++;
      originals=[];replacements=[];cache=new Map();batchBytes=0;
      await yieldControl();
      cancelled();
    }
    cancelled();
    for (const token of scanTokens(text, false)) {
      const value = token.kind === 'number' ? Number(token.text) : null;
      const key = Object.is(value,-0) ? '-0' : String(value);
      if (originals.length >= 8192 || batchBytes+token.text.length>4000000 || token.kind === 'number' && !cache.has(key) && cache.size >= LIMITS.uniqueNumbers) await finishBatch();
      let replacement = token.text;
      if (token.kind === 'number') {
        if (!cache.has(key)) cache.set(key,number(value));
        replacement=cache.get(key);
      }
      originals.push(token.text);replacements.push(replacement);batchBytes+=Math.max(token.text.length,replacement.length);
    }
    await finishBatch();
    cancelled();
    const content=output.join('');
    if (content.length > LIMITS.contentBytes) refuse('Generated rewritten content byte-string exceeds its budget.');
    return Object.freeze({content,numericTokens,changedTokens,batchCount,maxBatchUniqueNumbers,maxBatchBytes,completed:true});
  }

  return Object.freeze({ number, auditedDecimal, tokenize, rewriteOwnedContent, rewriteOwnedContentBatched, certifyRewrite, limits: LIMITS });
});
