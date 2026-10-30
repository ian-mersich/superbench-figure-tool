(function attach(root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  if (root) root.FigureStudioPdfPaintHitTest = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function create() {
  "use strict";
  const paths = new WeakMap();
  let scratch;
  function visiblePaint(value, fabric) {
    if (!value || ["none", "transparent"].includes(String(value).trim().toLowerCase())) return false;
    if (typeof value === "string" && fabric.Color) return new fabric.Color(value).getAlpha() > 0;
    // The bundled Fabric gradient renderer ignores a zero stop opacity; use
    // its actual color-alpha behavior rather than treating visible ink as blank.
    if (Array.isArray(value.colorStops)) return value.colorStops.some((stop) => visiblePaint(stop.color, fabric));
    return true;
  }
  function context() {
    if (!scratch) scratch = document.createElement("canvas").getContext("2d");
    return scratch;
  }
  function path(object, fabric) {
    const key = JSON.stringify(object.path);
    const cached = paths.get(object);
    if (cached?.key === key) return cached.path;
    const result = new Path2D(fabric.util.joinPath(object.path));
    paths.set(object, { key, path: result });
    return result;
  }
  function localPoint(point, matrix, fabric) {
    return fabric.util.transformPoint(new fabric.Point(point.x, point.y), fabric.util.invertTransform(matrix));
  }
  function ownMatrix(object) { return object.calcOwnMatrix(); }
  function multiply(a, b, fabric) { return fabric.util.multiplyTransformMatrices(a, b); }
  function textPlaneHit(object, point, matrix, fabric, tolerance) {
    const plane = object._pdfCurrentNativePlane?.();
    if (!plane) return null;
    return object._pdfCurrentPlaneEntries(plane).some(entry => {
      const glyphMatrix = entry.matrices.reduce((m, local) => multiply(m, local, fabric), matrix);
      const local = localPoint(point, glyphMatrix, fabric), line = entry.lineIndex || 0, column = entry.columnIndex ?? entry.charIndex;
      const declaration = object.getCompleteStyleDeclaration(line, column), char = object._textLines[line]?.[column];
      const unicode = object._textLines[line]?.slice(column, column + entry.charCount).join('');
      if (char === undefined || !unicode || /^\s+$/u.test(unicode) || !visiblePaint(declaration.fill, fabric) && !(Number(declaration.strokeWidth) > 0 && visiblePaint(declaration.stroke, fabric))) return false;
      const width = object._measureChar(unicode, declaration).width, em = declaration.fontSize;
      const scale = Math.max(1e-9, Math.min(Math.hypot(glyphMatrix[0], glyphMatrix[1]), Math.hypot(glyphMatrix[2], glyphMatrix[3]))), margin = tolerance / scale;
      return local.x >= entry.x - margin && local.x <= entry.x + width + margin && local.y >= entry.y - em - margin && local.y <= entry.y + em * .25 + margin;
    });
  }
  function geometry(object, point, matrix, fabric, clipping, tolerance) {
    const children = object.getObjects?.();
    if (children?.length) return children.some((child) => {
      if (child.visible === false) return false;
      const childMatrix = multiply(matrix, ownMatrix(child), fabric);
      return (!child.clipPath || clipContains(child.clipPath, childMatrix, point, fabric))
        && geometry(child, point, childMatrix, fabric, clipping, tolerance);
    });
    const textHit = !clipping ? textPlaneHit(object, point, matrix, fabric, tolerance) : null;
    if (textHit !== null) return textHit;
    const local = localPoint(point, matrix, fabric);
    if (Array.isArray(object.path)) {
      local.x += object.pathOffset?.x || 0;
      local.y += object.pathOffset?.y || 0;
      const ctx = context(), outline = path(object, fabric);
      if ((clipping || visiblePaint(object.fill, fabric)) && ctx.isPointInPath(outline, local.x, local.y, object.fillRule === "evenodd" ? "evenodd" : "nonzero")) return true;
      if (!clipping && visiblePaint(object.stroke, fabric) && Number(object.strokeWidth) > 0) {
        const scale = Math.max(1e-9, Math.min(Math.hypot(matrix[0], matrix[1]), Math.hypot(matrix[2], matrix[3])));
        ctx.lineWidth = Number(object.strokeWidth) + 2 * tolerance / scale;
        ctx.lineCap = object.strokeLineCap || "butt";
        ctx.lineJoin = object.strokeLineJoin || "miter";
        ctx.miterLimit = Number(object.strokeMiterLimit) || 4;
        ctx.setLineDash(object.strokeDashArray || []);
        ctx.lineDashOffset = Number(object.strokeDashOffset) || 0;
        return ctx.isPointInStroke(outline, local.x, local.y);
      }
      return false;
    }
    const type = String(object.type || object.constructor?.type || "").toLowerCase();
    if (type === "rect" || type === "circle" || type === "ellipse") {
      const outline = new Path2D(), width = Number(object.width), height = Number(object.height);
      if (type === "rect") {
        const rx = Math.min(Math.abs(Number(object.rx) || 0), width / 2);
        const ry = Math.min(Math.abs(Number(object.ry) || 0), height / 2);
        if ((rx || ry) && typeof outline.roundRect === "function") outline.roundRect(-width / 2, -height / 2, width, height, { x: rx, y: ry });
        else outline.rect(-width / 2, -height / 2, width, height);
      } else outline.ellipse(0, 0, width / 2, height / 2, 0, 0, Math.PI * 2);
      const ctx = context();
      if ((clipping || visiblePaint(object.fill, fabric)) && ctx.isPointInPath(outline, local.x, local.y)) return true;
      if (!clipping && visiblePaint(object.stroke, fabric) && Number(object.strokeWidth) > 0) {
        const scale = Math.max(1e-9, Math.min(Math.hypot(matrix[0], matrix[1]), Math.hypot(matrix[2], matrix[3])));
        ctx.lineWidth = Number(object.strokeWidth) + 2 * tolerance / scale;
        ctx.setLineDash(object.strokeDashArray || []);
        ctx.lineDashOffset = Number(object.strokeDashOffset) || 0;
        return ctx.isPointInStroke(outline, local.x, local.y);
      }
      return false;
    }
    return Math.abs(local.x) <= Number(object.width) / 2 && Math.abs(local.y) <= Number(object.height) / 2;
  }
  function clipContains(clip, hostMatrix, point, fabric) {
    const matrix = clip.absolutePositioned ? clip.calcTransformMatrix() : multiply(hostMatrix, ownMatrix(clip), fabric);
    const inside = geometry(clip, point, matrix, fabric, true, 0)
      && (!clip.clipPath || clipContains(clip.clipPath, matrix, point, fabric));
    // Fabric composites a nested clip into this mask before complementing it.
    return clip.inverted ? !inside : inside;
  }
  function insideClips(object, point, fabric) {
    const seen = new Set();
    for (let current = object; current && !seen.has(current); current = current.group || current.parent) {
      seen.add(current);
      if (current.visible === false || Number(current.opacity) === 0) return false;
      if (current.clipPath && !clipContains(current.clipPath, current.calcTransformMatrix(), point, fabric)) return false;
    }
    return true;
  }
  function hitObject(object, point, { fabric, tolerance = 3 } = {}) {
    if (!object || !point || !fabric || object.pdfPageFrame || object.visible === false || Number(object.opacity) === 0) return false;
    if (!insideClips(object, point, fabric)) return false;
    const children = object.getObjects?.();
    if (children?.length) return children.some((child) => hitObject(child, point, { fabric, tolerance }));
    const matrix = object.calcTransformMatrix();
    const textHit = textPlaneHit(object, point, matrix, fabric, tolerance);
    if (textHit !== null) return textHit;
    const local = localPoint(point, matrix, fabric);
    const scale = Math.max(1e-9, Math.min(Math.hypot(matrix[0], matrix[1]), Math.hypot(matrix[2], matrix[3])));
    const margin = tolerance / scale + (Number(object.strokeWidth) || 0) / 2;
    // aCoords can still describe the previous parent while Fabric reparents a
    // selected object. Use the current affine transform for this broad phase.
    if (Math.abs(local.x) > Number(object.width) / 2 + margin || Math.abs(local.y) > Number(object.height) / 2 + margin) return false;
    return geometry(object, point, matrix, fabric, false, tolerance);
  }
  return { hitObject, insideClips };
});
