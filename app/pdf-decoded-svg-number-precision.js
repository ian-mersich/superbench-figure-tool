/* Preserve the bundled PDF interpreter's current decoded Number values.
 * This layer changes SVG numeric spelling only. It does not replay retained
 * source geometry, change decoded operations, or patch vendor/global state.
 */
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.FigureStudioPdfSvgNumberPrecision = api;
})(typeof globalThis === 'object' ? globalThis : this, function () {
  'use strict';
  function number(value) {
    if (!Number.isFinite(value)) throw new Error('Decoded PDF SVG numbers must be finite.');
    return Object.is(value, -0) ? '-0' : String(value);
  }
  function matrix(values) {
    if (!values || values.length !== 6) throw new Error('Decoded PDF SVG requires a six-number affine matrix.');
    return `matrix(${Array.from(values, number).join(' ')})`;
  }
  function pathCommands(ops, args, OPS, initialX = 0, initialY = 0) {
    let x = initialX, y = initialY, index = 0;
    const pieces = [];
    for (const op of ops) {
      switch (op | 0) {
        case OPS.rectangle: {
          x = args[index++]; y = args[index++];
          const width = args[index++], height = args[index++];
          const right = x + width, bottom = y + height;
          pieces.push('M', number(x), number(y), 'L', number(right), number(y), 'L', number(right), number(bottom), 'L', number(x), number(bottom), 'Z');
          break;
        }
        case OPS.moveTo:
          x = args[index++]; y = args[index++]; pieces.push('M', number(x), number(y)); break;
        case OPS.lineTo:
          x = args[index++]; y = args[index++]; pieces.push('L', number(x), number(y)); break;
        case OPS.curveTo:
          x = args[index + 4]; y = args[index + 5];
          pieces.push('C', number(args[index]), number(args[index + 1]), number(args[index + 2]), number(args[index + 3]), number(x), number(y));
          index += 6; break;
        case OPS.curveTo2:
          pieces.push('C', number(x), number(y), number(args[index]), number(args[index + 1]), number(args[index + 2]), number(args[index + 3]));
          x = args[index + 2]; y = args[index + 3]; index += 4; break;
        case OPS.curveTo3:
          x = args[index + 2]; y = args[index + 3];
          pieces.push('C', number(args[index]), number(args[index + 1]), number(x), number(y), number(x), number(y));
          index += 4; break;
        case OPS.closePath: pieces.push('Z'); break;
        default: throw new Error('This decoded PDF path operator is not qualified for SVG number preservation.');
      }
    }
    if (index !== args.length) throw new Error('Decoded PDF path operands do not match their operators.');
    return { d: pieces.join(' '), x, y };
  }
  function createGraphicsClass(BaseGraphics, pdfjs) {
    if (typeof BaseGraphics !== 'function' || pdfjs?.version !== '3.11.174' || !pdfjs.OPS) throw new Error('Decoded PDF SVG number preservation requires the audited bundled PDF interpreter.');
    const OPS = pdfjs.OPS;
    return class DecodedNumberSvgGraphics extends BaseGraphics {
      constructPath(ops, args) {
        const current = this.current, plan = pathCommands(ops, args, OPS, current.x, current.y);
        let d = plan.d;
        // Preserve the bundled interpreter's path continuation and element
        // lifetime. Each decoded paint/clip retains its original geometry.
        if (current.path && ops.length > 0 && ops[0] !== OPS.rectangle && ops[0] !== OPS.moveTo) {
          d = current.path.getAttributeNS(null, 'd') + d;
        } else {
          current.path = this.svgFactory.createElement('svg:path');
          this._ensureTransformGroup().append(current.path);
        }
        current.path.setAttributeNS(null, 'd', d);
        current.path.setAttributeNS(null, 'fill', 'none');
        current.element = current.path;
        current.setCurrentPoint(plan.x, plan.y);
      }
      showText(glyphs) {
        const result = super.showText(glyphs), current = this.current;
        if (current.fontSize === 0) return result;
        current.tspan.setAttributeNS(null, 'x', current.xcoords.map(number).join(' '));
        current.tspan.setAttributeNS(null, 'y', current.font.vertical ? current.ycoords.map(number).join(' ') : number(-current.y));
        current.tspan.setAttributeNS(null, 'font-size', `${number(current.fontSize)}px`);
        return result;
      }
      _setStrokeAttributes(element, lineWidthScale = 1) {
        const result = super._setStrokeAttributes(element, lineWidthScale), current = this.current;
        element.setAttributeNS(null, 'stroke-miterlimit', number(current.miterLimit));
        element.setAttributeNS(null, 'stroke-width', `${number(lineWidthScale * current.lineWidth)}px`);
        element.setAttributeNS(null, 'stroke-dasharray', current.dashArray.map(value => number(lineWidthScale * value)).join(' '));
        element.setAttributeNS(null, 'stroke-dashoffset', `${number(lineWidthScale * current.dashPhase)}px`);
        return result;
      }
    };
  }
  return Object.freeze({ number, matrix, pathCommands, createGraphicsClass });
});
