(function attach(root, factory) {
  const knockout = typeof module === "object" && module.exports
    ? require("./pdf-knockout.js") : root.FigureStudioPdfKnockout;
  const api = factory(knockout);
  if (typeof module === "object" && module.exports) module.exports = api;
  if (root) root.FigureStudioPdfKnockoutProof = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function create(knockout) {
  "use strict";
  const SCHEMA = "figureStudio.pdfKnockoutSourceProof.v1";
  const BINDING_SCHEMA = "figureStudio.pdfKnockoutOperatorBinding.v1";
  const IDENTITY = [1, 0, 0, 1, 0, 0];
  const equal = (a, b) => JSON.stringify(a) === JSON.stringify(b);
  const normalize = value => ArrayBuffer.isView(value) ? Array.from(value)
    : Array.isArray(value) ? value.map(normalize)
      : value && typeof value === "object" ? Object.fromEntries(Object.entries(value).map(([key, item]) => [key, normalize(item)])) : value;

  // This lexer deliberately has a small envelope. Strings, dictionaries,
  // inline images and unknown token forms fail rather than disappearing.
  function parseOperators(source) {
    const expression = /\s+|%[^\r\n]*|\/[A-Za-z0-9_.-]+|[+-]?(?:\d+(?:\.\d*)?|\.\d+)|\[|\]|[A-Za-z][A-Za-z0-9*]*/gy;
    const stack = [[]], instructions = [];
    let offset = 0;
    while (offset < source.length) {
      expression.lastIndex = offset;
      const match = expression.exec(source);
      if (!match) throw new Error("Source content outside the bounded lexical envelope");
      offset = expression.lastIndex;
      const token = match[0];
      if (/^\s|^%/.test(token)) continue;
      if (token === "[") {
        const array = [];
        stack.at(-1).push(array);
        stack.push(array);
      } else if (token === "]") {
        if (stack.length === 1) throw new Error("Unbalanced source array");
        stack.pop();
      } else if (token[0] === "/") stack.at(-1).push(token);
      else if (/^[+-.\d]/.test(token)) stack.at(-1).push(Number(token));
      else {
        if (stack.length !== 1) throw new Error("Source array contains an operator");
        instructions.push({ operator: token, operands: stack[0] });
        stack[0] = [];
      }
    }
    if (stack.length !== 1 || stack[0].length) throw new Error("Incomplete source operator");
    return instructions;
  }

  async function sourceDigest(bytes) {
    if (globalThis.crypto?.subtle) {
      const digest = await globalThis.crypto.subtle.digest("SHA-256", bytes);
      return Array.from(new Uint8Array(digest), value => value.toString(16).padStart(2, "0")).join("");
    }
    if (typeof require === "function") return require("node:crypto").createHash("sha256").update(bytes).digest("hex");
    throw new Error("SHA-256 support is required for the source proof");
  }

  function validateProgram(instructions, child = false) {
    const arities = { q: 0, Q: 0, Tc: 1, Tw: 1, Ts: 1, Tz: 1, Tr: 1, TL: 1, w: 1, M: 1, j: 1, J: 1, d: 2, gs: 1, Do: 1, rg: 3, RG: 3, g: 1, G: 1, cm: 6, m: 2, l: 2, c: 6, re: 4, h: 0, f: 0, 'f*': 0, S: 0 };
    const pathNames = new Set(['m', 'l', 'c', 're', 'h']);
    let depth = 0, selectedState = null, memberIndex = 0;
    const stateStack = [];
    for (const { operator, operands } of instructions) {
      if (!Object.hasOwn(arities, operator) || operands.length !== arities[operator]) throw new Error('Native operator arity outside the bounded source envelope');
      if (operator === 'q') { stateStack.push(selectedState); depth++; }
      if (operator === 'Q') { if (!depth--) throw new Error('Native source save/restore is unbalanced'); selectedState = stateStack.pop(); }
      if (operator === 'gs') selectedState = operands[0];
      if (!child && operator === 'Do') {
        if (operands[0] !== `/Fm${memberIndex}` || selectedState !== `/GS${memberIndex}`) throw new Error('Native child paint is not bound to its declared outer graphics state');
        memberIndex++;
      }
    }
    if (depth !== 0) throw new Error('Native source save/restore is unbalanced');
    if (!child) return;
    const firstPath = instructions.findIndex(item => pathNames.has(item.operator));
    const paint = instructions.findIndex(item => ['f', 'f*', 'S'].includes(item.operator));
    if (firstPath < 0 || paint < firstPath || instructions.slice(firstPath, paint).some(item => !pathNames.has(item.operator)) || instructions.slice(paint + 1).some(item => item.operator !== 'Q')) throw new Error('Native child changes state during or after its canonical path paint');
    if(instructions.slice(0,firstPath).some(item=>item.operator==='Q')||instructions.slice(0,firstPath).filter(item=>item.operator==='q').length>1)throw new Error('Native child restores unproved inherited styles before its path');
    const cm = instructions.findIndex(item => item.operator === 'cm');
    if (cm >= 0 && cm + 1 !== firstPath) throw new Error('Native child transform is not immediately before its canonical path');
    if (instructions[paint].operator === 'S' && ['w', 'M', 'j', 'J', 'd'].some(operator => !instructions.slice(0, firstPath).some(item => item.operator === operator))) throw new Error('Native stroke inherits an unproved parent style');
    if (!instructions.slice(0, firstPath).some(item => item.operator === 'gs' && item.operands[0] === '/GS0')) throw new Error('Native child paint does not use the proved inner graphics state');
  }

  async function readSourceGroups(pdfBytes, { pdfLib, sourceSha256, sourceNamespace, yieldControl, onProgress } = {}) {
    if (!pdfLib?.PDFDocument || !knockout) throw new Error("PDF source proof dependencies are unavailable");
    const bytes = pdfBytes instanceof Uint8Array ? pdfBytes : new Uint8Array(pdfBytes);
    if (!bytes.length || bytes.length > 32 * 1024 * 1024) throw new Error("PDF source exceeds the current proof byte budget");
    const actualSha = await sourceDigest(bytes);
    if (sourceSha256 && sourceSha256 !== actualSha) throw new Error("PDF source SHA-256 does not match the requested proof");
    const namespace = sourceNamespace || actualSha;
    if (!/^[A-Za-z0-9:._-]{1,180}$/.test(namespace)) throw new Error("Invalid source namespace");
    // The source document is read-only: no context assignment, dictionary set,
    // stream write, or save. Generated export uses a different PDF document.
    const document = await pdfLib.PDFDocument.load(bytes, { parseSpeed: pdfLib.ParseSpeeds?.Slow ?? 100, updateMetadata: false });
    const context = document.context, N = pdfLib.PDFName.of;
    const lookup = (dict, key) => dict.lookup(N(key));
    const name = value => value?.asString?.().slice(1);
    const number = value => value?.asNumber?.();
    const boolean = value => value?.asBoolean?.();
    const numbers = value => value.asArray().map(item => number(context.lookup(item)));
    const box = value => {
      const raw = numbers(value);
      return { raw, normalized: [Math.min(raw[0], raw[2]), Math.min(raw[1], raw[3]), Math.max(raw[0], raw[2]), Math.max(raw[1], raw[3])] };
    };
    const formMatrix = dict => dict.has(N("Matrix")) ? numbers(lookup(dict, "Matrix")) : [...IDENTITY];
    const content = stream => new TextDecoder("latin1").decode(pdfLib.decodePDFRawStream(stream).decode());
    const counts = instructions => instructions.reduce((all, item) => (all[item.operator] = (all[item.operator] || 0) + 1, all), {});
    const graphicsState = dict => Object.fromEntries(dict.entries().filter(([key]) => name(key) !== "Type").map(([key, value]) => {
      value = context.lookup(value);
      let actual;
      if (value instanceof pdfLib.PDFName) actual = name(value);
      else if (value instanceof pdfLib.PDFBool) actual = boolean(value);
      else if (value instanceof pdfLib.PDFNumber) actual = number(value);
      else throw new Error("Unsupported source graphics-state resource");
      return [name(key), actual];
    }));
    const groups = [], unsupported = [], objects = context.enumerateIndirectObjects();
    const cooperate = yieldControl || (() => new Promise(resolve => setTimeout(resolve, 0)));
    for (let objectIndex = 0; objectIndex < objects.length; objectIndex++) {
      if (objectIndex && objectIndex % 64 === 0) {
        onProgress?.({ phase: "source-proof", visitedObjects: objectIndex, totalObjects: objects.length });
        await cooperate();
      }
      const [ref, parent] = objects[objectIndex];
      if (!(parent instanceof pdfLib.PDFRawStream) || name(lookup(parent.dict, "Subtype")) !== "Form") continue;
      const group = lookup(parent.dict, "Group");
      if (!(group instanceof pdfLib.PDFDict) || boolean(lookup(group, "K")) !== true) continue;
      try {
        if (name(lookup(group, "S")) !== "Transparency") throw new Error("Knockout group is not a transparency group");
        if (group.has(N("CS")) && name(lookup(group, "CS")) !== "DeviceRGB") throw new Error("Unsupported knockout blend color space");
        const resources = lookup(parent.dict, "Resources"), xobjects = lookup(resources, "XObject"), states = lookup(resources, "ExtGState");
        const parentStream = content(parent), instructions = parseOperators(parentStream), operators = counts(instructions);
        validateProgram(instructions);
        if (instructions.filter(i => i.operator === "Do").map(i => i.operands[0]).join(",") !== "/Fm0,/Fm1" || instructions.filter(i => i.operator === "gs").map(i => i.operands[0]).join(",") !== "/GS0,/GS1") throw new Error("Source Form invocation binding outside the bounded envelope");
        const members = [];
        for (let index = 0; index < 2; index++) {
          const childRef = xobjects.get(N(`Fm${index}`)), child = context.lookup(childRef), childGroup = lookup(child.dict, "Group");
          const childResources = lookup(child.dict, "Resources"), childStates = lookup(childResources, "ExtGState"), stream = content(child);
          const childInstructions = parseOperators(stream), operatorCounts = counts(childInstructions);
          validateProgram(childInstructions, true);
          if (childGroup.has(N("CS")) && name(lookup(childGroup, "CS")) !== "DeviceRGB") throw new Error("Unsupported child blend color space");
          for (const scope of [resources, childResources]) {
            const colors = lookup(scope, "ColorSpace");
            if (colors instanceof pdfLib.PDFDict && ["DefaultRGB", "DefaultCMYK", "DefaultGray"].some(key => colors.has(N(key)))) throw new Error("Default color-space substitution outside the source proof");
          }
          if (name(lookup(child.dict, "Subtype")) !== "Form" || name(lookup(childGroup, "S")) !== "Transparency" || childInstructions.filter(i => i.operator === "gs").map(i => i.operands[0]).join(",") !== "/GS0" || (operatorCounts.cm || 0) > 1) throw new Error("Child Form resource binding outside the bounded envelope");
          const path = [], pathLines = [], style = { fill: null, stroke: null, strokeWidth: 1, lineCap: 0, lineJoin: 0, miterLimit: 10, dashArray: [], dashOffset: 0 };
          let transform = [...IDENTITY], paintCount = 0;
          for (const { operator: op, operands: values } of childInstructions) {
            if (["m", "l", "c", "re", "h"].includes(op)) {
              path.push([op, values]);
              pathLines.push(`${values.join(" ")}${values.length ? " " : ""}${op}`);
            } else if (op === "cm") transform = values;
            else if (op === "rg" || op === "RG") style[op === "rg" ? "fill" : "stroke"] = values;
            else if (op === "g" || op === "G") style[op === "g" ? "fill" : "stroke"] = [values[0], values[0], values[0]];
            else if (op === "w") style.strokeWidth = values[0];
            else if (op === "J") style.lineCap = values[0];
            else if (op === "j") style.lineJoin = values[0];
            else if (op === "M") style.miterLimit = values[0];
            else if (op === "d") { style.dashArray = values[0]; style.dashOffset = values[1]; }
            else if (["f", "f*", "S", "F", "s", "B", "B*", "b", "b*"].includes(op)) { style.paint = op; paintCount++; }
          }
          if (["f", "f*"].includes(style.paint)) style.stroke = null;
          else style.fill = null;
          const insideState = graphicsState(lookup(childStates, "GS0")), outerState = graphicsState(lookup(states, `GS${index}`)), childBox = box(lookup(child.dict, "BBox"));
          members.push({ sourceObject: [childRef.objectNumber, childRef.generationNumber], sourceId: `${namespace}:form:${ref.objectNumber}:${childRef.objectNumber}`, childKnockout: boolean(lookup(childGroup, "K")) ?? false, childIsolated: boolean(lookup(childGroup, "I")) ?? false, sourceFormMatrix: formMatrix(child.dict), sourceMatrixPresent: child.dict.has(N("Matrix")), paintCount, operators: operatorCounts, instructions: childInstructions, path, pathStream: pathLines.join("\n"), transform, rawBBox: childBox.raw, bbox: childBox.normalized, style, insideState, outerState, opacity: outerState.ca, knockoutEraser: index > 0 && outerState.ca === 0 });
        }
        const parentBox = box(lookup(parent.dict, "BBox"));
        const source = { sourceSha256: actualSha, sourceGroup: ref.objectNumber, sourceObject: [ref.objectNumber, ref.generationNumber], sourceId: `${namespace}:form:${ref.objectNumber}`, knockout: true, isolated: boolean(lookup(group, "I")) ?? false, blendMode: "Normal", sourceFormMatrix: formMatrix(parent.dict), sourceMatrixPresent: parent.dict.has(N("Matrix")), parentStream, instructions, operators, parentDashProof: instructions.filter(i => i.operator === "d").every(i => i.operands[0].length === 0 && i.operands[1] === 0), rawBBox: parentBox.raw, bbox: parentBox.normalized, members };
        groups.push({ ...source, proof: knockout.validateSource(source) });
      } catch (error) {
        unsupported.push({ sourceObject: [ref.objectNumber, ref.generationNumber], reason: String(error.message || error) });
      }
    }
    const pageEnvelopes=document.getPages().map((page,index)=>{
      const group=lookup(page.node,'Group');
      const supported=!(group instanceof pdfLib.PDFDict)||(name(lookup(group,'S'))==='Transparency'&&boolean(lookup(group,'K'))!==true&&(!group.has(N('CS'))||name(lookup(group,'CS'))==='DeviceRGB'));
      return{pageNumber:index+1,supported,reason:supported?null:'Source page has an unproved transparency/blend-space envelope'};
    });
    return { schema: SCHEMA, sourceSha256: actualSha, sourceNamespace: namespace, groups, unsupported, pageEnvelopes, sourceWriteAuthority: false };
  }

  const OP_NAMES = { q: "save", Q: "restore", cm: "transform", Tc: "setCharSpacing", Tw: "setWordSpacing", Ts: "setTextRise", Tz: "setHScale", Tr: "setTextRenderingMode", TL: "setLeading", w: "setLineWidth", M: "setMiterLimit", j: "setLineJoin", J: "setLineCap", d: "setDash", f: "fill", "f*": "eoFill", S: "stroke" };
  const PATH_NAMES = { m: "moveTo", l: "lineTo", c: "curveTo", re: "rectangle", h: "closePath" };
  function groupOptions(source, child = false) {
    return { matrix: source.sourceMatrixPresent === false ? null : source.sourceFormMatrix, bbox: source.bbox, smask: null, isolated: child ? source.childIsolated : source.isolated, knockout: child ? source.childKnockout : source.knockout };
  }
  function stateProjection(state) {
    return [["BM", "source-over"], ["CA", state.CA], ["SMask", false], ["ca", state.ca]];
  }
  function compileScope(source, OPS, child = false) {
    const output = [], options = groupOptions(source, child);
    const add = (name, args) => output.push({ name, args });
    add("beginGroup", [options]);
    add("paintFormXObjectBegin", [options.matrix, null]);
    const instructions = source.instructions || parseOperators(child ? source.pathStream : source.parentStream);
    for (let index = 0; index < instructions.length; index++) {
      const { operator: op, operands: values } = instructions[index];
      if (PATH_NAMES[op]) {
        const pathOps = [], coordinates = [], bounds = [Infinity, -Infinity, Infinity, -Infinity];
        do {
          const item = instructions[index], v = item.operands;
          pathOps.push(OPS[PATH_NAMES[item.operator]]);
          coordinates.push(...v);
          if (item.operator === "re") {
            bounds[0] = Math.min(bounds[0], v[0], v[0] + v[2]); bounds[1] = Math.max(bounds[1], v[0], v[0] + v[2]);
            bounds[2] = Math.min(bounds[2], v[1], v[1] + v[3]); bounds[3] = Math.max(bounds[3], v[1], v[1] + v[3]);
          } else if (item.operator === "m" || item.operator === "l") {
            bounds[0] = Math.min(bounds[0], v[0]); bounds[1] = Math.max(bounds[1], v[0]);
            bounds[2] = Math.min(bounds[2], v[1]); bounds[3] = Math.max(bounds[3], v[1]);
          }
          index++;
        } while (index < instructions.length && PATH_NAMES[instructions[index].operator]);
        index--;
        add("constructPath", [pathOps, coordinates, bounds]);
      } else if (op === "Do") {
        const memberIndex = values[0] === "/Fm0" ? 0 : values[0] === "/Fm1" ? 1 : -1;
        if (child || memberIndex < 0) throw new Error("Unproved source Form invocation");
        output.push(...compileScope(source.members[memberIndex], OPS, true));
      } else if (op === "gs") {
        const state = child ? source.insideState : source.members[values[0] === "/GS0" ? 0 : 1].outerState;
        add("setGState", [stateProjection(state)]);
      } else if (["rg", "RG", "g", "G"].includes(op)) {
        const rgb = op === "g" || op === "G" ? [values[0], values[0], values[0]] : values;
        add(op === "rg" || op === "g" ? "setFillRGBColor" : "setStrokeRGBColor", rgb.map(value => Math.round(value * 255)));
      } else if (OP_NAMES[op]) add(OP_NAMES[op], op === "q" || op === "Q" || op === "f" || op === "f*" || op === "S" ? null : values);
      else throw new Error(`Unproved source operator ${op}`);
    }
    add("paintFormXObjectEnd", []);
    add("endGroup", [options]);
    return output;
  }

  function exactArgs(actual, expected) {
    // PDF.js 3.11 uses doubles for these paths. If a future qualified caller
    // supplies Float32 coordinates, only the exact IEEE projection is valid;
    // no epsilon, bounding-box tolerance or nearest-geometry matching exists.
    if (actual instanceof Float32Array) return equal(Array.from(actual), expected.map(Math.fround));
    if (ArrayBuffer.isView(actual)) return equal(Array.from(actual), expected);
    if (Array.isArray(actual) && Array.isArray(expected)) return actual.length === expected.length && actual.every((item, index) => exactArgs(item, expected[index]));
    if (actual && expected && typeof actual === "object" && typeof expected === "object") {
      return equal(Object.keys(actual).sort(), Object.keys(expected).sort()) && Object.keys(expected).every(key => exactArgs(actual[key], expected[key]));
    }
    return Object.is(actual, expected) || actual === expected;
  }

  function* bindingSteps(proof, { operatorList, OPS, pageNumber, sourceSha256 } = {}) {
    if (proof?.schema !== SCHEMA || proof.sourceWriteAuthority !== false || !/^[a-f0-9]{64}$/.test(sourceSha256 || "") || sourceSha256 !== proof.sourceSha256) throw new Error("Source proof and operator document SHA-256 must agree");
    if (!Number.isInteger(pageNumber) || pageNumber < 1) throw new Error("A source page number is required");
    if(proof.pageEnvelopes&&!proof.pageEnvelopes.some(page=>page.pageNumber===pageNumber&&page.supported))throw new Error('Source page transparency envelope is not proved');
    if (!operatorList?.fnArray || operatorList.fnArray.length !== operatorList.argsArray?.length || !OPS) throw new Error("Malformed PDF.js operator list");
    const names = new Map(Object.entries(OPS).map(([name, id]) => [id, name]));
    const scopes = [], stack = [], paintIndexes = new Map(), frames = [];
    const paints = new Set(["fill", "eoFill", "stroke", "fillStroke", "eoFillStroke", "closeStroke", "closeFillStroke", "closeEOFillStroke", "showText", "showSpacedText", "paintImageXObject", "paintInlineImageXObject", "paintSolidColorImageMask", "shadingFill"]);
    let paintIndex = 0;
    let state = { transform: [...IDENTITY], clips: [], fillAlpha: 1, strokeAlpha: 1, blendMode: "source-over", softMask: false };
    let currentPathIndex = null, pendingClip = null;
    const pushState = kind => frames.push({ kind, state: structuredClone(state) });
    const popState = kind => {
      const frame = frames.pop();
      if (!frame || frame.kind !== kind) throw new Error("PDF.js graphics-state/Form scopes are unbalanced");
      state = frame.state;
    };
    for (let index = 0; index < operatorList.fnArray.length; index++) {
      if (index && index % 2048 === 0) yield { phase: "operator-binding", visitedOperators: index, totalOperators: operatorList.fnArray.length };
      const name = names.get(operatorList.fnArray[index]), args = operatorList.argsArray[index];
      if (paints.has(name)) paintIndexes.set(index, paintIndex++);
      if (name === "save") pushState("save");
      if (name === "restore") popState("save");
      if (name === "transform") state.transform = knockout.matrix(state.transform, args);
      if (name === "setGState") {
        for (const [key, value] of args[0]) {
          if (key === "ca") state.fillAlpha = value;
          if (key === "CA") state.strokeAlpha = value;
          if (key === "BM") state.blendMode = value;
          if (key === "SMask") state.softMask = value;
        }
      }
      if (name === "constructPath") currentPathIndex = index;
      if (name === "clip" || name === "eoClip") pendingClip = { kind: "source-path", pathOperatorIndex: currentPathIndex, clipOperatorIndex: index, fillRule: name === "eoClip" ? "evenodd" : "nonzero", transform: [...state.transform] };
      if (name === "endPath" || paints.has(name)) {
        if (pendingClip) state.clips.push(pendingClip);
        pendingClip = null;
      }
      if (name === "beginGroup") {
        const options = args?.[0];
        stack.push({ start: index, options, ancestorState: structuredClone(state),ancestorScopes:frames.filter(frame=>frame.kind!=='save').map(frame=>frame.kind) });
        pushState("group");
        if (options?.bbox) state.clips.push({ kind: "source-group-bbox", groupOperatorIndex: index, bbox: [...options.bbox], transform: options.matrix ? knockout.matrix(state.transform, options.matrix) : [...state.transform] });
        state.fillAlpha = state.strokeAlpha = 1;
      }
      if (name === "paintFormXObjectBegin") {
        pushState("form");
        if (args?.[0]) state.transform = knockout.matrix(state.transform, args[0]);
        if (args?.[1]) state.clips.push({ kind: "source-form-bbox", formOperatorIndex: index, bbox: [...args[1]], transform: [...state.transform] });
      }
      if (name === "paintFormXObjectEnd") popState("form");
      if (name === "endGroup") {
        const scope = stack.pop();
        if (!scope) throw new Error("PDF.js group scopes are unbalanced");
        if (scope.options?.knockout) scopes.push({ ...scope, end: index });
        popState("group");
      }
    }
    if (stack.length) throw new Error("PDF.js group scopes are unbalanced");
    const compiled = proof.groups.map(source => {
      if(source.sourceSha256!==sourceSha256)throw new Error('A native group belongs to another source SHA-256');
      knockout.validateSource(source);validateProgram(source.instructions);
      source.members.forEach(member=>validateProgram(member.instructions,true));
      return{source,operators:compileScope(source,OPS)};
    });
    const byStart = new Map(), unsupported = [];
    for (const scope of scopes.sort((a, b) => a.start - b.start)) {
      const outer = scope.ancestorState;
      // This initial native proof covers the observed Forms invoked directly
      // from page graphics state. Raw blend-space/resource inheritance through
      // another native Form/group is not recoverable from worker flags alone.
      if(scope.ancestorScopes.length){unsupported.push({pageNumber,scopeStart:scope.start,scopeEnd:scope.end,reason:'Knockout native Form/group ancestor envelope is not proved'});continue;}
      if (outer.fillAlpha !== 1 || outer.strokeAlpha !== 1 || outer.blendMode !== "source-over" || outer.softMask) {
        unsupported.push({ pageNumber, scopeStart: scope.start, scopeEnd: scope.end, reason: "Knockout invocation has an unsupported ancestor compositing state" });
        continue;
      }
      const length = scope.end - scope.start + 1;
      const matches = compiled.filter(candidate => candidate.operators.length === length && candidate.operators.every((expected, offset) => {
        const index = scope.start + offset;
        return names.get(operatorList.fnArray[index]) === expected.name && exactArgs(operatorList.argsArray[index], expected.args);
      }));
      if (matches.length !== 1) {
        unsupported.push({ pageNumber, scopeStart: scope.start, scopeEnd: scope.end, reason: matches.length ? "Ambiguous native knockout source binding" : "No exact native knockout source binding" });
        continue;
      }
      const source = matches[0].source, children = [];
      for (let index = scope.start + 1; index < scope.end; index++) {
        if (names.get(operatorList.fnArray[index]) !== "beginGroup") continue;
        const start = index;
        let depth = 1;
        while (depth && ++index <= scope.end) {
          if (names.get(operatorList.fnArray[index]) === "beginGroup") depth++;
          if (names.get(operatorList.fnArray[index]) === "endGroup") depth--;
        }
        const pathIndex = Array.from({ length: index - start }, (_, offset) => start + offset).find(i => names.get(operatorList.fnArray[i]) === "constructPath");
        const painted = Array.from({ length: index - start }, (_, offset) => start + offset).filter(i => paints.has(names.get(operatorList.fnArray[i])));
        if (pathIndex === undefined || painted.length !== 1) throw new Error("An exactly matched source member lost its paint inventory");
        const member = source.members[children.length], coordinates = operatorList.argsArray[pathIndex][1];
        children.push({ sourceId: member.sourceId, sourceObject: member.sourceObject, scopeStart: start, scopeEnd: index, pathOperatorIndex: pathIndex, paintOperatorIndex: painted[0], paintIndex: paintIndexes.get(painted[0]), rawBBox: [...member.rawBBox], bbox: [...member.bbox], transform: [...member.transform], clip: { kind: "source-form-bbox", rawBBox: [...member.rawBBox], bbox: [...member.bbox] }, pathProjection: { coordinatePrecision: coordinates instanceof Float32Array ? "Float32" : "Float64", exact: true, float32Projection: coordinates instanceof Float32Array, originalPathRetained: true } });
      }
      const binding = { schema: BINDING_SCHEMA, sourceSha256, pageNumber, sourceId: source.sourceId, sourceObject: source.sourceObject, scopeStart: scope.start, scopeEnd: scope.end, rawBBox: [...source.rawBBox], bbox: [...source.bbox], sourceFormMatrix: [...source.sourceFormMatrix], ancestorTransform: [...outer.transform], ancestorTransformFloat32: Array.from(new Float32Array(outer.transform)), ancestorClips: structuredClone(outer.clips), children, source };
      byStart.set(scope.start, binding);
    }
    return { schema: BINDING_SCHEMA, sourceSha256, pageNumber, groups: Array.from(byStart.values()), byStart, unsupported, sourceWriteAuthority: false, totalPaints: paintIndex };
  }

  function bindOperatorScopes(proof, options) {
    const steps = bindingSteps(proof, options);
    let result;
    do { result = steps.next(); } while (!result.done);
    return result.value;
  }

  async function bindOperatorScopesAsync(proof, options = {}) {
    const steps = bindingSteps(proof, options);
    const yieldControl = options.yieldControl || (() => new Promise(resolve => setTimeout(resolve, 0)));
    let result, yieldedBatches = 0, maxBatchMs = 0;
    do {
      const start = performance.now();
      result = steps.next();
      maxBatchMs = Math.max(maxBatchMs, performance.now() - start);
      if (!result.done) {
        options.onProgress?.(result.value);
        yieldedBatches++;
        await yieldControl();
      }
    } while (!result.done);
    return { ...result.value, operatorBinding: { batchSize: 2048, yieldedBatches, maxBatchMs } };
  }

  async function readSourceGroupsInWorker(pdfBytes, { workerUrl, sourceSha256, onProgress, signal } = {}) {
    if (!workerUrl || typeof Worker !== "function") throw new Error("A portable source-proof worker is required");
    // Transfer a private copy. The caller's immutable source bytes stay owned
    // by the importer for preservation, hashing and normal PDF.js opening.
    const copy = new Uint8Array(pdfBytes instanceof Uint8Array ? pdfBytes : new Uint8Array(pdfBytes));
    return new Promise((resolve, reject) => {
      const worker = new Worker(workerUrl);
      const finish = (callback, value) => { signal?.removeEventListener("abort", abort); worker.terminate(); callback(value); };
      const abort = () => finish(reject, new Error("PDF source proof cancelled"));
      if (signal?.aborted) return abort();
      signal?.addEventListener("abort", abort, { once: true });
      worker.onerror = event => finish(reject, new Error(event.message || "PDF source-proof worker failed"));
      worker.onmessage = event => {
        if (event.data?.type === "progress") onProgress?.(event.data.progress);
        else if (event.data?.type === "result") finish(resolve, event.data.proof);
        else if (event.data?.type === "error") finish(reject, new Error(event.data.message));
      };
      worker.postMessage({ bytes: copy.buffer, sourceSha256 }, [copy.buffer]);
    });
  }
  return { SCHEMA, BINDING_SCHEMA, parseOperators, sourceDigest, readSourceGroups, readSourceGroupsInWorker, compileScope, bindOperatorScopes, bindOperatorScopesAsync };
});
