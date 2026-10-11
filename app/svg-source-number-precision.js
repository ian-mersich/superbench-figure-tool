/* Export current numerical-source artwork through detached SVG facades.
 * Stock class, clip, style, font and public toSVG writers retain ownership.
 * No source geometry replay, global precision setting or prototype hook.
 */
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.FigureStudioSvgNumberPrecision = api;
})(typeof globalThis === 'object' ? globalThis : this, function () {
  'use strict';
  function createSerializer({fabric, precisionObjectsForScene, isNumericSourceObject, positionedTextClass, currentPlanePathClass} = {}) {
    if (!fabric?.util?.joinPath || !fabric?.util?.radiansToDegrees || typeof precisionObjectsForScene !== 'function' || typeof isNumericSourceObject !== 'function') {
      throw new TypeError('SVG numerical preservation requires bundled Fabric and an explicit current-scene numerical scope.');
    }
    const stockPath = fabric.Path.prototype._toSVG;
    const stockOffset = fabric.Path.prototype._getOffsetTransform;
    const stockSpan = fabric.Text.prototype._createTextCharSpan;
    const stockGroup = fabric.Group.prototype._toSVG;
    let lastReport = null;
    const auditedShapes = new Set(['Group', 'Path', 'Rect', 'Circle', 'Ellipse', 'Triangle', 'Line', 'Polyline', 'Polygon', 'Text', 'IText', 'Textbox', 'FabricImage', 'Image'].map(name => fabric[name]?.prototype?._toSVG).filter(Boolean));
    const number = value => {
      if (!Number.isFinite(value)) throw new Error('SVG numerical-source geometry must contain finite numbers.');
      return String(value);
    };
    const property = (target, name, value) => Object.defineProperty(target, name, {value, writable: true, configurable: true, enumerable: true});
    const matrixString = matrix => {
      if (!Array.isArray(matrix) || matrix.length !== 6) throw new Error('SVG numerical-source geometry requires a six-number affine matrix.');
      return `matrix(${matrix.map(number).join(' ')})`;
    };
    // Preserve style/font/Unicode markup from the existing span writer. Only
    // the writer's own positional attributes use their current Number values.
    function preciseSpan(text, declaration, x, y, box) {
      let markup = stockSpan.call(this, text, declaration, x, y, box);
      const {angle, renderLeft, renderTop, width} = box;
      if (renderLeft !== undefined) {
        const degrees = fabric.util.radiansToDegrees(angle);
        const matrix = fabric.util.composeMatrix({angle: degrees});
        matrix[4] = renderLeft; matrix[5] = renderTop;
        const point = fabric.util.transformPoint(new fabric.Point(-width / 2, 0), matrix);
        x = point.x; y = point.y;
        if (angle) markup = replaceAttribute(markup, 'rotate', number(degrees));
      }
      markup = replaceAttribute(markup, 'x', number(x));
      markup = replaceAttribute(markup, 'y', number(y));
      if (declaration.deltaY) markup = replaceAttribute(markup, 'dy', number(declaration.deltaY));
      return markup;
    }
    function replaceAttribute(markup, name, value) {
      const expression = new RegExp(`\\b${name}="[^"]*"`, 'g');
      const matches = markup.match(expression);
      if (matches?.length !== 1 || !markup.startsWith('<tspan ')) throw new Error('The audited SVG span writer changed its positional structure.');
      return markup.replace(expression, `${name}="${value}"`);
    }
    function installNumericWriters(copy, live) {
      if (live.getSvgTransform !== fabric.FabricObject.prototype.getSvgTransform) throw new Error('An unaudited numerical-source SVG transform writer is unsupported.');
      const sourceWriter = positionedTextClass?.prototype instanceof fabric.IText && live.constructor === positionedTextClass
        && live._toSVG === positionedTextClass.prototype._pdfCurrentPlaneSvgMarkup;
      if (!auditedShapes.has(live._toSVG) && !sourceWriter) throw new Error('An unaudited numerical-source shape SVG writer is unsupported.');
      property(copy, 'getSvgTransform', function (full, additional = '') {
        return `transform="${matrixString(full ? this.calcTransformMatrix() : this.calcOwnMatrix())}${additional}" `;
      });
      if (Array.isArray(live.path) && live instanceof fabric.Path) {
        const currentPlanePath = currentPlanePathClass?.prototype instanceof fabric.Path && live.constructor === currentPlanePathClass
          && live._getOffsetTransform === currentPlanePathClass.prototype._getOffsetTransform;
        if (live._toSVG !== stockPath || live._getOffsetTransform !== stockOffset && !currentPlanePath) throw new Error('An unaudited numerical-source Path SVG writer is unsupported.');
        property(copy, '_toSVG', function (...args) {
          // A method-level substitution in the audited Path command fragment,
          // not a rewrite of the serialized document or geometry metadata.
          const pieces = stockPath.apply(this, args);
          const old = `d="${fabric.util.joinPath(this.path, fabric.config.NUM_FRACTION_DIGITS)}"`;
          const index = pieces.findIndex(piece => typeof piece === 'string' && piece.includes(old));
          if (index < 0 || pieces.filter(piece => typeof piece === 'string' && piece.includes(old)).length !== 1) throw new Error('The audited SVG Path command writer changed.');
          for (const command of this.path) for (const value of command.slice(1)) number(value);
          pieces[index] = pieces[index].replace(old, `d="${fabric.util.joinPath(this.path)}"`);
          return pieces;
        });
        property(copy, '_getOffsetTransform', function () { return currentPlanePath ? '' : ` translate(${number(-this.pathOffset.x)}, ${number(-this.pathOffset.y)})`; });
      } else if (live instanceof fabric.Group && live._toSVG !== stockGroup) {
        throw new Error('An unaudited numerical-source Group SVG writer is unsupported.');
      }
      if (live instanceof fabric.Polyline) {
        const original = live._toSVG;
        property(copy, '_toSVG', function (...args) {
          const pieces = original.apply(this, args);
          const points = this.points.map(point => `${number(point.x - this.pathOffset.x)},${number(point.y - this.pathOffset.y)}`).join(' ');
          const index = pieces.findIndex(piece => typeof piece === 'string' && /\bpoints="[^"]*"/.test(piece));
          if (index < 0) throw new Error('The audited SVG point writer changed.');
          pieces[index] = pieces[index].replace(/\bpoints="[^"]*"/, `points="${points}"`);
          return pieces;
        });
      }
      if (typeof live.text === 'string') {
        if (live._createTextCharSpan !== stockSpan) throw new Error('An unaudited numerical-source Text span writer is unsupported.');
        property(copy, '_createTextCharSpan', preciseSpan);
      }
    }
    function canvasToSVG(canvas, options = {}, reviver) {
      const roots = Array.from(canvas?.getObjects?.() || []);
      if (typeof canvas?.toSVG !== 'function') throw new TypeError('The existing Canvas SVG serializer is required.');
      const scope = precisionObjectsForScene(roots, {isPdfObject: isNumericSourceObject});
      try { Set.prototype.has.call(scope, undefined); }
      catch (_) { throw new TypeError('The current numerical-source scope must be a native Set.'); }
      const stockStyleNumerics = [];
      lastReport = Object.freeze({schema:'figureStudio.svgNumberPrecisionExportAudit.v1',numericalScopeSize:scope.size,stockStyleNumerics});
      if (!scope.size) return canvas.toSVG({...options}, reviver);
      // Existing withExportState discards selection before this boundary. Do
      // not invent owner-plane realization or double-apply an AS transform.
      if (canvas.getActiveObject?.() instanceof fabric.ActiveSelection) throw new Error('Numerical-source SVG export requires the existing export-state selection projection.');
      const copies = new Map(), pending = [], owned = new Set();
      const canvasCopy = Object.create(canvas);
      const runtime = new Set(['canvas', 'group', 'parent', '_objects', 'clipPath', 'layoutManager', '_cacheCanvas', '_cacheContext', 'matrixCache', 'ownMatrixCache', 'aCoords', 'oCoords', '_eventListeners', '__eventListeners', '_activeObjects', '_element', '_originalElement', '_filteredEl']);
      function dataCopy(value, seen = new Map()) {
        if (!value || typeof value !== 'object') return value;
        if (seen.has(value)) return seen.get(value);
        if (value instanceof fabric.FabricObject || value === canvas) throw new Error('Unexpected live Fabric reference in SVG export data.');
        if (ArrayBuffer.isView(value)) return value.slice ? value.slice() : new value.constructor(value.buffer.slice(0));
        if (value instanceof ArrayBuffer) return value.slice(0);
        if (value instanceof Map || value instanceof Set) throw new Error('Unsupported mutable runtime collection in SVG export data.');
        const copy = Array.isArray(value) ? [] : Object.create(Object.getPrototypeOf(value));
        seen.set(value, copy);
        for (const key of Reflect.ownKeys(value)) {
          if (Array.isArray(value) && key === 'length') continue;
          if (value instanceof fabric.Pattern && key === 'source') continue;
          const descriptor = Object.getOwnPropertyDescriptor(value, key);
          if (!('value' in descriptor)) throw new Error('Accessor-based SVG export data is unsupported.');
          if ('value' in descriptor) descriptor.value = dataCopy(descriptor.value, seen);
          Object.defineProperty(copy, key, descriptor);
        }
        if (value instanceof fabric.Pattern) {
          if (value.toSVG !== fabric.Pattern.prototype.toSVG || value.sourceToString !== fabric.Pattern.prototype.sourceToString) throw new Error('An unaudited SVG pattern reader is unsupported.');
          const source = value.source;
          property(copy, 'source', source ? {width:source.width,height:source.height,src:value.sourceToString()} : source);
        }
        return copy;
      }
      function allocate(live, clipEdge = false, clipScope = false, ancestors = new Set(), edgeCopies = new Map()) {
        if (ancestors.has(live)) throw new Error('Cyclic SVG paint/clip ownership is unsupported.');
        if (!clipEdge && owned.has(live)) throw new Error('Shared canonical painted children are unsupported.');
        if (!clipEdge) owned.add(live);
        const copy = Object.create(live);
        if (!clipEdge) copies.set(live, copy);
        else edgeCopies.set(live, copy);
        const precise = clipEdge ? clipScope : scope.has(live);
        if (precise) {
          // Preserve existing supported style writers, including their existing
          // formatting. Their separate style numerics are not qualified by the
          // current affine/path/span-only preservation proof.
          for (const [channel, style] of [['fill',live.fill],['stroke',live.stroke],['shadow',live.shadow]]) {
            if (!style || typeof style !== 'object') continue;
            const feature = style instanceof fabric.Gradient ? 'gradient-affine-stock' : style instanceof fabric.Pattern ? 'pattern-ratio-stock' : style instanceof fabric.Shadow ? 'shadow-filter-stock' : null;
            if (!feature) throw new Error('An unaudited SVG paint/effect writer is unsupported.');
            stockStyleNumerics.push(Object.freeze({id:String(live.figureId || live.id || ''),channel,feature,exactNumericQualification:false}));
          }
        }
        const seen = new Map();
        for (const key of Reflect.ownKeys(live)) {
          if (runtime.has(key)) continue;
          // Native IText drag state owns a back-reference to the live text.
          // Its UI delegate is never consumed by the audited SVG writers.
          // Shadow this one native runtime field; unknown data refs still fail.
          if (key === 'draggableTextDelegate' && live instanceof fabric.IText) {
            property(copy, key, undefined);
            continue;
          }
          if (precise && ['getSvgTransform', '_toSVG', '_getOffsetTransform', '_createTextCharSpan'].includes(key)) continue;
          const descriptor = Object.getOwnPropertyDescriptor(live, key);
          if (!('value' in descriptor)) throw new Error('Accessor-based SVG export object fields are unsupported.');
          if ('value' in descriptor) descriptor.value = dataCopy(descriptor.value, seen);
          Object.defineProperty(copy, key, descriptor);
        }
        for (const key of ['group', 'parent', 'matrixCache', 'ownMatrixCache', 'aCoords', 'oCoords', '_cacheCanvas', '_cacheContext', 'layoutManager']) property(copy, key, undefined);
        property(copy, 'canvas', canvasCopy);
        property(copy, '_eventListeners', {}); property(copy, '__eventListeners', {}); property(copy, '_activeObjects', []);
        if (live instanceof fabric.FabricImage) {
          if (live._toSVG !== fabric.FabricImage.prototype._toSVG || live.getSrc !== fabric.FabricImage.prototype.getSrc) throw new Error('An unaudited SVG image reader is unsupported.');
          // Stock Image SVG reads these element fields only. Snapshot DOM/canvas
          // sources rather than retaining a writable live element in a facade.
          function elementSnapshot(element, source) {
            if (!element) return element;
            return {width:element.width,height:element.height,naturalWidth:element.naturalWidth,naturalHeight:element.naturalHeight,src:source,getAttribute:name=>name === 'src' ? source : null,toDataURL:()=>source};
          }
          property(copy, '_element', elementSnapshot(live._element, live.getSrc(true)));
          property(copy, '_originalElement', elementSnapshot(live._originalElement, live.getSrc(false)));
          property(copy, '_filteredEl', undefined);
        }
        if (precise) installNumericWriters(copy, live);
        const next = new Set(ancestors); next.add(live);
        if (live.getObjects) property(copy, '_objects', live.getObjects().map(child => allocate(child, clipEdge, precise, next, edgeCopies)));
        if (live.clipPath) property(copy, 'clipPath', allocate(live.clipPath, true, precise, next));
        pending.push({live, copy, clipEdge, edgeCopies});
        return copy;
      }
      const rootCopies = roots.map(object => allocate(object));
      // A global Canvas clip has no implicit source ownership from a leaf.
      // Preserve its stock writer unless the shared own-data source predicate
      // independently grants that exact clip numerical provenance. Artboard
      // page clipping is authored later by the existing buildSvgExport path.
      if (canvas.clipPath) property(canvasCopy, 'clipPath', allocate(canvas.clipPath, true, Boolean(isNumericSourceObject(canvas.clipPath))));
      for (const name of ['backgroundImage', 'overlayImage']) if (canvas[name]) property(canvasCopy, name, allocate(canvas[name], true, false));
      // Preserve actual group/parent links, including full clip transforms.
      // A clip edge uses its edge-local descendants before canonical mapping.
      for (const {live, copy, clipEdge, edgeCopies} of pending) {
        function resolve(link) {
          if (!link) return link;
          if (link === canvas) return canvasCopy;
          if (clipEdge && edgeCopies.has(link)) return edgeCopies.get(link);
          if (!copies.has(link)) throw new Error('SVG numerical export has an unproven external ownership frame.');
          return copies.get(link);
        }
        property(copy, 'group', resolve(live.group)); property(copy, 'parent', resolve(live.parent));
      }
      property(canvasCopy, '_objects', rootCopies);
      property(canvasCopy, '_activeObject', undefined);
      if (canvas.viewportTransform) property(canvasCopy, 'viewportTransform', canvas.viewportTransform.slice());
      // Existing wrappers installed immediately outside this call are inherited
      // by the facades and execute with facade this, preserving their order.
      try { return canvas.toSVG.call(canvasCopy, {...options}, reviver); }
      finally { Object.freeze(stockStyleNumerics); }
    }
    return Object.freeze({canvasToSVG,getLastReport:()=>lastReport ? Object.freeze({...lastReport,stockStyleNumerics:Object.freeze([...lastReport.stockStyleNumerics])}) : null});
  }
  return Object.freeze({createSerializer});
});
