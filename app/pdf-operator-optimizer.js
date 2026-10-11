(function attachPdfOperatorOptimizer(root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  if (root) root.FigureStudioPdfOperatorOptimizer = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function createPdfOperatorOptimizer() {
  "use strict";

  const SCHEMA = "figureStudio.pdfOperatorPlan.v1";
  const RECTANGLE_SCHEMA = "figureStudio.pdfRectangleScope.v1";
  const PAINT_NAMES = ["fill", "eoFill", "stroke", "fillStroke", "eoFillStroke", "closeStroke", "closeFillStroke", "closeEOFillStroke", "showText", "showSpacedText", "paintSolidColorImageMask", "paintImageXObject", "paintInlineImageXObject", "shadingFill"];
  const defaultYield = () => new Promise((resolve) => setTimeout(resolve, 0));

  function checkList(list) {
    if (!list || !Array.isArray(list.fnArray) || !Array.isArray(list.argsArray) || list.fnArray.length !== list.argsArray.length) throw new Error("PDF operator and argument arrays must have equal lengths.");
  }
  function checkBatchSize(value) {
    if (!Number.isSafeInteger(value) || value < 1 || value > 65536) throw new Error("PDF operator batch size must be an integer from 1 to 65536.");
  }
  function checkAbort(signal) {
    if (signal?.aborted) {
      const error = new Error("PDF operator planning was cancelled.");
      error.name = "AbortError";
      throw error;
    }
  }
  const empty = (args) => args == null || args.length === 0;
  const numbers = (value, length) => (Array.isArray(value) || ArrayBuffer.isView(value)) && value.length === length && Array.from(value).every((item) => typeof item === "number" && Number.isFinite(item));

  function rectangleBounds(x, y, width, height) {
    if (!width || !height) return null;
    return [Math.min(x, x + width), Math.min(y, y + height), Math.max(x, x + width), Math.max(y, y + height)];
  }
  function pathData(args) {
    if (!Array.isArray(args) || args.length < 2 || args.length > 3) return null;
    if (!(Array.isArray(args[0]) || ArrayBuffer.isView(args[0])) || !(Array.isArray(args[1]) || ArrayBuffer.isView(args[1]))) return null;
    if (args.length === 3 && !numbers(args[2], 4)) return null;
    return { ops: Array.from(args[0]), args: Array.from(args[1]), ...(args.length === 3 ? { interpreterBounds: Array.from(args[2]) } : {}) };
  }
  function closedAxisRectangle(path, OPS) {
    if (!path || path.ops.length !== 5 || path.ops[0] !== OPS.moveTo || !path.ops.slice(1).every((op) => op === OPS.lineTo) || !numbers(path.args, 10)) return null;
    const points = Array.from({ length: 5 }, (_, index) => path.args.slice(index * 2, index * 2 + 2));
    if (points[0][0] !== points[4][0] || points[0][1] !== points[4][1]) return null;
    if (new Set(points.slice(0, 4).map(([x, y]) => `${x},${y}`)).size !== 4) return null;
    const xs = [...new Set(points.map(([x]) => x))], ys = [...new Set(points.map(([, y]) => y))];
    if (xs.length !== 2 || ys.length !== 2) return null;
    if (!points.slice(0, 4).every(([x, y], i) => (x === points[i + 1][0]) !== (y === points[i + 1][1]))) return null;
    return [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)];
  }

  // This proves local geometry only. Inherited transforms, clips, transparency
  // and resources are still interpreted from the complete original list. The
  // materializer must validate its actual final clip before native-clip drawing.
  function detectRectangleScope(list, OPS, start, { sourceId = "", pageNumber = 1, paintIndex = 0 } = {}) {
    const expected = [OPS.save, OPS.constructPath, OPS.clip, OPS.endPath, OPS.setFillRGBColor, OPS.constructPath, OPS.eoFill, OPS.restore];
    if (expected.some((id) => !Number.isInteger(id)) || start < 0 || start + expected.length > list.fnArray.length) return null;
    if (!expected.every((id, offset) => list.fnArray[start + offset] === id)) return null;
    if (![0, 2, 3, 6, 7].every((offset) => empty(list.argsArray[start + offset]))) return null;
    const clip = pathData(list.argsArray[start + 1]), path = pathData(list.argsArray[start + 5]);
    if (!clip || clip.ops.length !== 1 || clip.ops[0] !== OPS.rectangle || !numbers(clip.args, 4)) return null;
    const clipBounds = rectangleBounds(...clip.args), bounds = closedAxisRectangle(path, OPS), color = list.argsArray[start + 4];
    if (!clipBounds || !bounds || !numbers(color, 3) || !Array.from(color).every((value) => Number.isInteger(value) && value >= 0 && value <= 255)) return null;
    if (bounds[0] > clipBounds[0] || bounds[1] > clipBounds[1] || bounds[2] < clipBounds[2] || bounds[3] < clipBounds[3]) return null;
    return {
      schema: RECTANGLE_SCHEMA,
      proofScope: "local-path-contains-rectangular-clip",
      sourceId,
      pageNumber,
      sourceLeafId: sourceId ? `pdf:${sourceId}:p${pageNumber}:op${start + 6}` : null,
      scopeStart: start,
      scopeEnd: start + 8,
      clipOperatorIndex: start + 1,
      pathOperatorIndex: start + 5,
      paintOperatorIndex: start + 6,
      paintIndex,
      path: { ...path, bounds, fillRule: "evenodd" },
      clip: { ...clip, bounds: clipBounds, fillRule: "nonzero" },
      localStyle: { operator: "setFillRGBColor", args: Array.from(color) },
      canonicalGeometryRewritten: false
    };
  }

  async function planOperators({ operatorList, OPS, sourceId = "", pageNumber = 1, batchSize = 2048, yieldTask = defaultYield, signal, onProgress } = {}) {
    checkList(operatorList);
    checkBatchSize(batchSize);
    if (!OPS || typeof yieldTask !== "function" || !Number.isSafeInteger(pageNumber) || pageNumber < 1 || typeof sourceId !== "string") throw new Error("Invalid PDF operator planning options.");
    const paintIds = new Set(PAINT_NAMES.map((name) => OPS[name]).filter(Number.isInteger));
    const rectangles = [];
    const batches = [];
    let paintCount = 0;
    checkAbort(signal);
    for (let start = 0; start < operatorList.fnArray.length; start += batchSize) {
      const end = Math.min(start + batchSize, operatorList.fnArray.length);
      for (let index = start; index < end; index++) {
        if (operatorList.fnArray[index] === OPS.save) {
          const scope = detectRectangleScope(operatorList, OPS, index, { sourceId, pageNumber, paintIndex: paintCount });
          if (scope) rectangles.push(scope);
        }
        if (paintIds.has(operatorList.fnArray[index])) paintCount++;
      }
      batches.push({ start, end });
      onProgress?.({ processedOperatorCount: end, originalOperatorCount: operatorList.fnArray.length, recognizedRectangleCount: rectangles.length, originalPaintCount: paintCount });
      if (end < operatorList.fnArray.length) { await yieldTask(); checkAbort(signal); }
    }
    return { schema: SCHEMA, sourceId, pageNumber, originalOperatorCount: operatorList.fnArray.length, originalPaintCount: paintCount, recognizedRectangleCount: rectangles.length, rectangles, batches, canonicalGeometryRewritten: false, qualifiedBudgetIncrease: false };
  }

  async function executeOperatorBatches(operatorList, executeBatch, { batchSize = 2048, yieldTask = defaultYield, signal, onProgress } = {}) {
    checkList(operatorList);
    checkBatchSize(batchSize);
    if (typeof executeBatch !== "function" || typeof yieldTask !== "function") throw new Error("PDF batch execution needs callbacks.");
    checkAbort(signal);
    for (let start = 0; start < operatorList.fnArray.length; start += batchSize) {
      const end = Math.min(start + batchSize, operatorList.fnArray.length);
      // The original list and exact ranges are passed through: no op is dropped,
      // reordered or replaced. The caller keeps interpreter state across ranges.
      await executeBatch(operatorList, { start, end });
      onProgress?.({ processedOperatorCount: end, originalOperatorCount: operatorList.fnArray.length });
      if (end < operatorList.fnArray.length) { await yieldTask(); checkAbort(signal); }
    }
    return { executedOperatorCount: operatorList.fnArray.length, canonicalGeometryRewritten: false };
  }

  function svgAttributes(scope) {
    if (scope?.schema !== RECTANGLE_SCHEMA || scope.canonicalGeometryRewritten !== false) throw new Error("SVG native-clip metadata requires an original-geometry rectangle proof.");
    return {
      "data-pdf-native-rect-clip": "1",
      "data-pdf-rect-proof": RECTANGLE_SCHEMA,
      "data-pdf-paint-index": String(scope.paintIndex),
      "data-pdf-source-start": String(scope.scopeStart),
      "data-pdf-source-end": String(scope.scopeEnd),
      ...(scope.sourceLeafId ? { "data-pdf-source-leaf-id": scope.sourceLeafId } : {})
    };
  }

  return Object.freeze({ SCHEMA, RECTANGLE_SCHEMA, detectRectangleScope, planOperators, executeOperatorBatches, svgAttributes });
});
