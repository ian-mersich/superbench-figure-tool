(function(root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  if (root) root.FigureStudioPdfKnockout = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function() {
  'use strict';
  const SCHEMA = 'figureStudio.pdfKnockout.v1',
    classes = new WeakMap(),
    placeholderTokens = new WeakMap();
  let orderedPlanSerial = 0;
  const clone = v => JSON.parse(JSON.stringify(v)),
    xml = v => String(v).replace(/[&<>"']/g, c => ({
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      '"': '&quot;',
      "'": '&apos;'
    } [c]));
  const n = v => Number(v).toPrecision(15).replace(/(?:\.0+|(?:(\.\d*?)0+))(?=e|$)/, '$1');
  const matrix = (a, b) => [a[0] * b[0] + a[2] * b[1], a[1] * b[0] + a[3] * b[1], a[0] * b[2] + a[2] * b[3], a[1] * b[2] + a[3] * b[3], a[0] * b[4] + a[2] * b[5] + a[4], a[1] * b[4] + a[3] * b[5] + a[5]];
  const translation = (x, y) => [1, 0, 0, 1, x, y];

  function inverse(t) {
    const determinant = t[0] * t[3] - t[1] * t[2];
    if (!determinant) throw new Error('Singular knockout member transform');
    return [t[3] / determinant, -t[1] / determinant, -t[2] / determinant, t[0] / determinant, (t[2] * t[5] - t[3] * t[4]) / determinant, (t[1] * t[4] - t[0] * t[5]) / determinant];
  }

  function transformedBox(box, t) {
    const points = [
      [box[0], box[1]],
      [box[2], box[1]],
      [box[2], box[3]],
      [box[0], box[3]]
    ].map(([x, y]) => [t[0] * x + t[2] * y + t[4], t[1] * x + t[3] * y + t[5]]);
    if (t[1] !== 0 || t[2] !== 0) throw new Error('Source outer clip transform outside rectangular envelope');
    return [Math.min(...points.map(p => p[0])), Math.min(...points.map(p => p[1])), Math.max(...points.map(p => p[0])), Math.max(...points.map(p => p[1]))];
  }

  function transformedClip(box, t) {
    return [
      [box[0], box[1]],
      [box[2], box[1]],
      [box[2], box[3]],
      [box[0], box[3]]
    ].map(([x, y]) => [t[0] * x + t[2] * y + t[4], t[1] * x + t[3] * y + t[5]]);
  }

  function outerClipPath(group) {
    const points = group.pdfKnockoutSource?.clipPolygonInGroupSpace;
    if (points) return [
      ['M', ...points[0]], ...points.slice(1).map(point => ['L', ...point]), ['Z']
    ];
    const box = group.pdfKnockoutSource?.clipInGroupSpace;
    if (!box) throw new Error('Missing canonical knockout outer clip');
    return [
      ['M', box[0], box[1]],
      ['L', box[2], box[1]],
      ['L', box[2], box[3]],
      ['L', box[0], box[3]],
      ['Z']
    ];
  }

  function svgPath(original) {
    // This string is parsed into the canonical Fabric path. Preserve every
    // source Float64 value with its shortest roundtrip representation; the
    // separate PDF/SVG presentation serializer can retain its own policy.
    const sourceNumber = value => String(value);
    return original.map(([op, v]) => {
      if (op === 're') {
        const [x, y, w, h] = v;
        return `M ${sourceNumber(x)} ${sourceNumber(y)} L ${sourceNumber(x+w)} ${sourceNumber(y)} L ${sourceNumber(x+w)} ${sourceNumber(y+h)} L ${sourceNumber(x)} ${sourceNumber(y+h)} Z`;
      }
      if (['m', 'l', 'c'].includes(op)) return `${op.toUpperCase()} ${v.map(sourceNumber).join(' ')}`;
      if (op === 'h') return 'Z';
      throw new Error('Knockout path operator outside inspected source envelope');
    }).join(' ');
  }

  function canvasPath(parts) {
    const path = new Path2D();
    for (const [op, ...v] of parts) {
      if (op === 'M') path.moveTo(v[0], v[1]);
      else if (op === 'L') path.lineTo(v[0], v[1]);
      else if (op === 'Z') path.closePath();
      else if (op === 'C') path.bezierCurveTo(...v);
      else if (op === 'Q') path.quadraticCurveTo(...v);
      else throw new Error('Unsupported edited knockout path operator');
    }
    return path;
  }

  function rgb(values) {
    return values ? `rgb(${values.map(v=>v*255).join(',')})` : null;
  }

  function localClip(member) {
    const t = member.transform;
    if (!Array.isArray(t) || t.length !== 6 || t.some(value => !Number.isFinite(value))) throw new Error('Invalid source child transform');
    if (t[0] !== 1 || t[1] !== 0 || t[2] !== 0 || t[3] !== 1) throw new Error('Source clip transform outside knockout envelope');
    const b = member.bbox;
    return [b[0] - t[4], b[1] - t[5], b[2] - t[4], b[3] - t[5]];
  }

  function validateSource(source) {
    if (!source || !source.knockout || source.isolated !== false || source.blendMode !== 'Normal' || source.members?.length !== 2) throw new Error('Knockout source outside inspected two-member Normal envelope');
    const [first, second] = source.members, states = [];
    const identity = [1, 0, 0, 1, 0, 0],
      parentOps = new Set(['q', 'Q', 'Tc', 'Tw', 'Ts', 'Tz', 'Tr', 'w', 'M', 'j', 'J', 'd', 'gs', 'TL', 'Do']),
      childOps = new Set(['rg', 'RG', 'g', 'G', 'cm', 'gs', 'q', 'Q', 'w', 'J', 'j', 'M', 'd', 'm', 'l', 'c', 're', 'h', 'f', 'f*', 'S']);
    if (source.operators?.Do !== 2 || Object.keys(source.operators).some(op => !parentOps.has(op)) || source.parentDashProof !== true || JSON.stringify(source.sourceFormMatrix) !== JSON.stringify(identity)) throw new Error('Parent Form operators outside proven envelope');
    if (![0, 1].includes(first.opacity) || ![0, 1].includes(second.opacity) || first.opacity + second.opacity !== 1) throw new Error('Source opacity pair is not one zero and one opaque member');
    if (JSON.stringify(first.path) !== JSON.stringify(second.path) || JSON.stringify(first.transform) !== JSON.stringify(second.transform)) throw new Error('Source member shape or transform differs');
    if (JSON.stringify(second.bbox) !== JSON.stringify(source.bbox) || first.bbox[0] < second.bbox[0] || first.bbox[1] < second.bbox[1] || first.bbox[2] > second.bbox[2] || first.bbox[3] > second.bbox[3]) throw new Error('Source child clips outside inspected separate-bounds envelope');
    if (!first.style.fill || first.style.stroke || second.style.fill || !second.style.stroke || !['f', 'f*'].includes(first.style.paint) || second.style.paint !== 'S') throw new Error('Source paint pair is not inspected fill then open stroke');
    for (const member of source.members) {
      if (member.childKnockout !== false || member.childIsolated !== false || member.paintCount !== 1 || !member.operators || Object.keys(member.operators).some(op => !childOps.has(op)) || JSON.stringify(member.sourceFormMatrix) !== JSON.stringify(identity)) throw new Error('Child Form outside proven single-paint envelope');
      if (!Array.isArray(member.path) || member.path.length === 0 || member.path.some(([op, args]) => !({
          m: 2,
          l: 2,
          c: 6,
          re: 4,
          h: 0
        } [op] === args.length) || args.some(v => !Number.isFinite(v)))) throw new Error('Source path outside exact M/L/C/re/h envelope');
      if (member.bbox.length !== 4 || member.bbox.some(v => !Number.isFinite(v)) || member.bbox[2] < member.bbox[0] || member.bbox[3] < member.bbox[1]) throw new Error('Invalid normalized source clip');
      localClip(member);
      for (const [state, opacity] of [
          [member.insideState, 1],
          [member.outerState, member.opacity]
        ]) {
        if (!state || Object.keys(state).some(key => !['BM', 'SMask', 'AIS', 'OP', 'op', 'OPM', 'ca', 'CA', 'SA'].includes(key)) || state.OPM !== 1 || state.BM !== 'Normal' || state.SMask !== 'None' || state.AIS !== false || state.OP !== false || state.op !== false || state.ca !== opacity || state.CA !== opacity || state.SA !== true) throw new Error('Unsupported source transparency or overprint state');
        states.push(state);
      }
      const style = member.style;
      if (style.strokeWidth !== 1 || style.lineCap !== 0 || style.lineJoin !== 0 || style.miterLimit !== 10 || style.dashArray?.length !== 0 || style.dashOffset !== 0 || (style.fill || style.stroke).some(v => !Number.isFinite(v) || v < 0 || v > 1)) throw new Error('Source style outside inspected Figure 4 envelope');
    }
    return {
      schema: SCHEMA,
      canonicalMembers: 2,
      zeroOpacityMember: first.opacity === 0 ? 0 : 1,
      alphaZeroEraser: second.opacity === 0,
      normalBlend: true,
      sourceStrokeAdjustment: states.every(s => s.SA === true)
    };
  }

  function drawMember(context, object, shape = false) {
    context.save();
    try {
      context.transform(...object.calcOwnMatrix());
      context.translate(-object.pathOffset.x, -object.pathOffset.y);
      const box = object.pdfKnockoutMember.clipInPathSpace;
      context.beginPath();
      context.rect(box[0], box[1], box[2] - box[0], box[3] - box[1]);
      context.clip();
      const path = canvasPath(object.path);
      context.globalAlpha = shape ? 1 : object.opacity;
      if (object.fill) {
        context.fillStyle = shape ? 'black' : object.fill;
        context.fill(path, object.fillRule === 'evenodd' ? 'evenodd' : 'nonzero');
      }
      if (object.stroke) {
        context.strokeStyle = shape ? 'black' : object.stroke;
        context.lineWidth = object.strokeWidth;
        context.lineCap = object.strokeLineCap;
        context.lineJoin = object.strokeLineJoin;
        context.miterLimit = object.strokeMiterLimit;
        context.setLineDash(object.strokeDashArray || []);
        context.stroke(path);
      }
    } finally {
      context.restore();
    }
  }

  function registerClass(fabric) {
    if (classes.has(fabric)) return classes.get(fabric);
    const ObjectClass = fabric.FabricObject || fabric.Object;
    ObjectClass.customProperties = Array.from(new Set([...(ObjectClass.customProperties || []), 'pdfKnockoutSource', 'pdfKnockoutMember']));
    class PdfKnockoutLayout extends fabric.FixedLayout {
      static type = 'PdfKnockoutLayout';
      shouldPerformLayout({
        type
      }) {
        // Fabric FixedLayout still recenters on an imperative layout. A native
        // Form's clip coordinate frame must remain fixed after initialization.
        return type === 'initialization';
      }
    }
    fabric.classRegistry.setClass(PdfKnockoutLayout);
    class PdfKnockoutGroup extends fabric.Group {
      static type = 'PdfKnockoutGroup';
      constructor(...args) {
        super(...args);
        this.objectCaching = false;
      }
      assertSupportedEdits() {
        if (this._objects.length !== 2 || !this.pdfKnockoutSource?.members || this._objects.some((object, index) => object.pdfKnockoutMember?.sourceId !== this.pdfKnockoutSource.members[index]?.sourceId)) throw new Error('Knockout canonical membership changed outside the supported two-member envelope');
        if (this.opacity !== 1 || this.shadow || this.clipPath || this.globalCompositeOperation !== 'source-over') throw new Error('Edited outer group effects outside qualified envelope');
        for (const object of this._objects) {
          if (!!object.fill === !!object.stroke || object.shadow || object.clipPath || object.strokeDashArray?.length || object.strokeUniform || object.globalCompositeOperation !== 'source-over') throw new Error('Edited member effects outside qualified envelope');
          const color = new fabric.Color(object.fill || object.stroke);
          if (typeof(object.fill || object.stroke) !== 'string' || color.isUnrecognised || color.getSource()[3] !== 1) throw new Error('Knockout members require a recognized opaque color; use leaf opacity for transparency');
          if (!['butt', 'round', 'square'].includes(object.strokeLineCap) || !['miter', 'round', 'bevel'].includes(object.strokeLineJoin) || !Number.isFinite(object.strokeMiterLimit) || object.strokeMiterLimit <= 0) throw new Error('Edited knockout stroke style is unsupported');
          if (!Array.isArray(object.path) || object.path.some(([op, ...values]) => !({
              M: 2,
              L: 2,
              C: 6,
              Z: 0
            } [op] === values.length) || values.some(value => !Number.isFinite(value)))) throw new Error('Edited knockout path requires finite absolute M/L/C/Z geometry');
          if (!Number.isFinite(object.opacity) || object.opacity < 0 || object.opacity > 1 || object.stroke && (!Number.isFinite(object.strokeWidth) || object.strokeWidth <= 0)) throw new Error('Edited member opacity or stroke width is invalid');
        }
        return true;
      }
      needsItsOwnCache() {
        return false;
      }
      drawObject(context, forClipping, cache) {
        if (forClipping) return super.drawObject(context, forClipping, cache);
        this._render(context);
      }
      _render(context) {
        this.assertSupportedEdits();
        const transform = context.getTransform(),
          corners = outerClipPath(this).filter(part => part[0] !== 'Z').map(([, x, y]) => [transform.a * x + transform.c * y + transform.e, transform.b * x + transform.d * y + transform.f]);
        // Buffers are transient viewport paint, never the canonical scene. Bound
        // them to the actual canvas so zooming a large group cannot allocate an
        // offscreen-sized bitmap. The source paths and clips remain unchanged.
        const pad = 2,
          left = Math.max(0, Math.floor(Math.min(...corners.map(p => p[0]))) - pad),
          top = Math.max(0, Math.floor(Math.min(...corners.map(p => p[1]))) - pad),
          right = Math.min(context.canvas.width, Math.ceil(Math.max(...corners.map(p => p[0]))) + pad),
          bottom = Math.min(context.canvas.height, Math.ceil(Math.max(...corners.map(p => p[1]))) + pad),
          w = right - left,
          h = bottom - top;
        if (w <= 0 || h <= 0) return;
        this.lastKnockoutPaint = {
          transform: [transform.a, transform.b, transform.c, transform.d, transform.e, transform.f],
          left,
          top,
          w,
          h,
          globalAlpha: context.globalAlpha,
          own: this.calcOwnMatrix(),
          ownChildren: this._objects.map(o => o.calcOwnMatrix()),
          properties: {
            left: this.left,
            top: this.top,
            width: this.width,
            height: this.height,
            originX: this.originX,
            originY: this.originY
          },
          cacheTranslation: [this.cacheTranslationX, this.cacheTranslationY],
          zoom: [this.zoomX, this.zoomY],
          objectCaching: this.objectCaching
        };
        const shape = document.createElement('canvas'),
          ink = document.createElement('canvas'),
          final = document.createElement('canvas');
        for (const buffer of [shape, ink, final]) {
          buffer.width = w;
          buffer.height = h;
        }
        const shapeContext = shape.getContext('2d', {
            willReadFrequently: true
          }),
          inkContext = ink.getContext('2d', {
            willReadFrequently: true
          }),
          finalContext = final.getContext('2d');
        const color = new Float64Array(w * h * 4);
        for (const object of this._objects) {
          if (object.visible === false) continue;
          for (const ctx of [shapeContext, inkContext]) {
            ctx.setTransform(1, 0, 0, 1, 0, 0);
            ctx.clearRect(0, 0, w, h);
            ctx.setTransform(transform.a, transform.b, transform.c, transform.d, transform.e - left, transform.f - top);
          }
          drawMember(shapeContext, object, true);
          drawMember(inkContext, object, false);
          const coverage = shapeContext.getImageData(0, 0, w, h).data,
            member = inkContext.getImageData(0, 0, w, h).data;
          for (let i = 0; i < color.length; i += 4) {
            const f = coverage[i + 3] / 255,
              a = member[i + 3] / 255;
            for (let channel = 0; channel < 3; channel++) color[i + channel] = member[i + channel] / 255 * a + color[i + channel] * (1 - f);
            color[i + 3] = a + color[i + 3] * (1 - f);
          }
        }
        const result = finalContext.createImageData(w, h);
        for (let i = 0; i < color.length; i += 4) {
          const a = color[i + 3];
          for (let c = 0; c < 3; c++) result.data[i + c] = a ? Math.round(color[i + c] / a * 255) : 0;
          result.data[i + 3] = Math.round(a * 255);
        }
        finalContext.putImageData(result, 0, 0);
        context.save();
        try {
          context.clip(canvasPath(outerClipPath(this)));
          context.setTransform(1, 0, 0, 1, 0, 0);
          context.drawImage(final, left, top);
        } finally {
          context.restore();
        }
      }
      toObject(properties = []) {
        const result = super.toObject([...properties, 'pdfKnockoutSource', 'figureId']);
        const keys = ['left', 'top', 'width', 'height', 'angle', 'scaleX', 'scaleY', 'skewX', 'skewY', 'strokeWidth'];
        for (const key of keys) result[key] = this[key];
        for (let i = 0; i < this._objects.length; i++)
          for (const key of keys) result.objects[i][key] = this._objects[i][key];
        return result;
      }
      _toSVG() {
        return [svgGroupMarkup(this, {
          transform: null,
          idNamespace: this.figureId || ''
        })];
      }
      toSVG(reviver) {
        const markup = svgGroupMarkup(this, {
          transform: this.calcOwnMatrix(),
          idNamespace: this.figureId || ''
        });
        return reviver ? reviver(markup) : markup;
      }
    }
    fabric.classRegistry.setClass(PdfKnockoutGroup);
    classes.set(fabric, PdfKnockoutGroup);
    return PdfKnockoutGroup;
  }

  function createScene(source, fabric) {
    validateSource(source);
    const Group = registerClass(fabric),
      Layout = fabric.classRegistry.getClass('PdfKnockoutLayout');
    const objects = source.members.map(member => {
      const style = member.style,
        object = new fabric.Path(svgPath(member.path), {
          fill: rgb(style.fill),
          stroke: rgb(style.stroke),
          strokeWidth: style.strokeWidth,
          strokeLineCap: ['butt', 'round', 'square'][style.lineCap],
          strokeLineJoin: ['miter', 'round', 'bevel'][style.lineJoin],
          strokeMiterLimit: style.miterLimit,
          fillRule: style.paint === 'f*' ? 'evenodd' : 'nonzero',
          opacity: member.opacity,
          objectCaching: false,
          perPixelTargetFind: false,
          selectable: true,
          evented: true
        });
      object.pdfKnockoutMember = {
        schema: SCHEMA,
        ...clone(member),
        clipInPathSpace: localClip(member),
        paintHitRole: member.knockoutEraser ? 'knockout-eraser' : member.opacity === 0 ? 'transparent' : 'paint'
      };
      const transform = matrix(matrix(source.sourceToViewport, member.transform), translation(object.pathOffset.x, object.pathOffset.y));
      fabric.util.applyTransformToObject(object, transform);
      return object;
    });
    const group = new Group(objects, {
      objectCaching: false,
      interactive: true,
      subTargetCheck: true,
      // The native Form BBox owns the outer clip. Editing a member's bounds
      // must not reframe that clip or masquerade as motion of the whole Form.
      layoutManager: new fabric.LayoutManager(new Layout())
    });
    const sourceToGroup = matrix(inverse(group.calcTransformMatrix()), source.sourceToViewport);
    group.pdfKnockoutSource = {
      schema: SCHEMA,
      ...clone(source),
      initialGroupMatrix: [...group.calcTransformMatrix()],
      clipPolygonInGroupSpace: transformedClip(source.bbox, sourceToGroup),
      clipInGroupSpace: sourceToGroup[1] === 0 && sourceToGroup[2] === 0 ? transformedBox(source.bbox, sourceToGroup) : null
    };
    for (const object of objects) {
      object.pdfKnockoutMember.initialOwnMatrix = [...object.calcOwnMatrix()];
      object.pdfKnockoutMember.initialPathOffset = {
        ...object.pathOffset
      };
      object.pdfKnockoutMember.initialFabricPath = clone(object.path);
    }
    return group;
  }

  function shapeHit(group, point, context, fabric) {
    const hits = [];
    if (group.visible === false) return hits;
    const local = fabric.util.transformPoint(point, fabric.util.invertTransform(group.calcTransformMatrix()));
    if (!context.isPointInPath(canvasPath(outerClipPath(group)), local.x, local.y)) return hits;
    for (const object of group.getObjects()) {
      const role = memberHitRole(group, object);
      if (role === 'transparent') continue;
      const inverse = fabric.util.invertTransform(object.calcTransformMatrix()),
        local = fabric.util.transformPoint(point, inverse),
        x = local.x + object.pathOffset.x,
        y = local.y + object.pathOffset.y,
        box = object.pdfKnockoutMember.clipInPathSpace;
      if (x < box[0] || x > box[2] || y < box[1] || y > box[3]) continue;
      const path = canvasPath(object.path);
      context.lineWidth = object.strokeWidth;
      context.lineCap = object.strokeLineCap;
      context.lineJoin = object.strokeLineJoin;
      context.miterLimit = object.strokeMiterLimit;
      context.setLineDash([]);
      if (object.fill && context.isPointInPath(path, x, y, object.fillRule === 'evenodd' ? 'evenodd' : 'nonzero') || object.stroke && context.isPointInStroke(path, x, y)) hits.push(object);
    }
    return hits;
  }

  function memberHitRole(group, object) {
    if (group.visible === false || object.visible === false) return 'transparent';
    const members = group.getObjects(),
      index = members.indexOf(object);
    if (index < 0) throw new Error('Knockout hit target is not a canonical group member');
    return object.opacity > 0 ? 'paint' : index > 0 && members.slice(0, index).some(o => o.visible !== false && o.opacity > 0) ? 'knockout-eraser' : 'transparent';
  }

  function memberSvg(object, id, shape = false) {
    const box = object.pdfKnockoutMember.clipInPathSpace,
      d = object.path.map(([op, ...v]) => `${op} ${v.map(n).join(' ')}`).join(' '),
      fill = object.fill ? (shape ? 'black' : object.fill) : 'none',
      stroke = object.stroke ? (shape ? 'black' : object.stroke) : 'none';
    return `<g id="${id}"${object.visible===false?' display="none"':''} opacity="${shape?1:n(object.opacity)}" transform="matrix(${object.calcOwnMatrix().map(n).join(' ')})"><g transform="translate(${-object.pathOffset.x} ${-object.pathOffset.y})"><clipPath id="${id}-clip" clipPathUnits="userSpaceOnUse"><rect x="${n(box[0])}" y="${n(box[1])}" width="${n(box[2]-box[0])}" height="${n(box[3]-box[1])}"/></clipPath><path clip-path="url(#${id}-clip)" d="${d}" fill="${xml(fill)}" fill-rule="${object.fillRule==='evenodd'?'evenodd':'nonzero'}" stroke="${xml(stroke)}" stroke-width="${n(object.strokeWidth)}" stroke-linecap="${object.strokeLineCap}" stroke-linejoin="${object.strokeLineJoin}" stroke-miterlimit="${n(object.strokeMiterLimit)}"/></g></g>`;
  }

  function svgGroupMarkup(group, {
    idNamespace = '',
    transform = group.calcTransformMatrix()
  } = {}) {
    group.assertSupportedEdits();
    const id = (group.pdfKnockoutSource.sourceId + '-' + idNamespace).replace(/[^\w-]/g, '-'),
      points = outerClipPath(group).filter(part => part[0] !== 'Z'),
      x = Math.min(...points.map(part => part[1])) - 1,
      y = Math.min(...points.map(part => part[2])) - 1,
      w = Math.max(...points.map(part => part[1])) - x + 1,
      h = Math.max(...points.map(part => part[2])) - y + 1;
    const members = group.getObjects();
    // Two-member ordered shape reduction. Both original editable paths
    // and K metadata survive. An invisible later member retains its SHAPE as
    // a vector mask, never disappearing because its paint opacity is zero.
    if (members.length === 2) {
      let definitions = '',
        body = '';
      if (members[0].opacity === 0 || members.some(o => o.visible === false)) body = members.map((object, index) => memberSvg(object, `${id}-member-${index}`)).join('');
      else {
        definitions = `<mask id="${id}-erase" maskUnits="userSpaceOnUse" maskContentUnits="userSpaceOnUse" x="${x}" y="${y}" width="${w}" height="${h}" style="mask-type:luminance"><rect x="${x}" y="${y}" width="${w}" height="${h}" fill="white"/>${memberSvg(members[1],`${id}-shape`,true)}</mask>`;
        const earlier = `<g mask="url(#${id}-erase)">${memberSvg(members[0],`${id}-member-0`)}</g>`;
        const later = memberSvg(members[1],`${id}-member-1`);
        // Previous premultiplied ink is already attenuated by later SHAPE.
        // Add the later premultiplied ink rather than attenuating twice through
        // ordinary source-over at partially covered antialiased boundaries.
        body = members[1].opacity > 0
          ? `<g style="isolation:isolate">${earlier}<g style="mix-blend-mode:plus-lighter">${later}</g></g>`
          : `${earlier}${later}`;
      }
      const outer = outerClipPath(group).map(([op, ...values]) => `${op} ${values.map(n).join(' ')}`).join(' ');
      definitions += `<clipPath id="${id}-outer-clip" clipPathUnits="userSpaceOnUse"><path d="${outer}"/></clipPath>`;
      return `<g data-pdf-knockout="true"${group.visible===false?' display="none"':''} data-pdf-knockout-source-id="${xml(group.pdfKnockoutSource.sourceId)}"${group.figureId?' data-pdf-knockout-instance-id="'+xml(group.figureId)+'"':''}${transform?' transform="matrix('+transform.map(n).join(' ')+')"':''}><metadata>${xml(JSON.stringify(group.toObject()))}</metadata><defs>${definitions}</defs><g clip-path="url(#${id}-outer-clip)">${body}</g></g>`;
    }
    throw new Error('SVG knockout export outside the two-member envelope');
  }

  function svgForGroup(group, width, height, options = {}) {
    return `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}">${svgGroupMarkup(group,options)}</svg>`;
  }

  function pdfPath(parts) {
    const lines = [];
    for (const [op, ...v] of parts) {
      if (op === 'M' || op === 'L') lines.push(`${v.map(n).join(' ')} ${op.toLowerCase()}`);
      else if (op === 'C') lines.push(`${v.map(n).join(' ')} c`);
      else if (op === 'Z') lines.push('h');
      else throw new Error('Edited PDF path outside inspected M/L/C/Z envelope');
    }
    return lines.join('\n');
  }

  function sceneSource(group, fabric, {
    pageHeight,
    sceneToOutput
  } = {}) {
    group.assertSupportedEdits();
    const original = group.pdfKnockoutSource,
      outputHeight = pageHeight ?? original.height,
      pageFromViewport = [1, 0, 0, -1, 0, outputHeight];
    if (!Number.isFinite(outputHeight) || outputHeight <= 0) throw new Error('An explicit output page height is required');
    const outputFromScene = sceneToOutput || [1, 0, 0, 1, 0, 0];
    if (!Array.isArray(outputFromScene) || outputFromScene.length !== 6 || outputFromScene.some(v => !Number.isFinite(v))) throw new Error('Invalid scene-to-output transform');
    if (group.opacity !== 1 || group.shadow || group.clipPath || group.globalCompositeOperation !== 'source-over') throw new Error('Edited outer group paint outside qualified envelope');
    outerClipPath(group);
    const members = group.getObjects().map(object => {
      const retained = object.pdfKnockoutMember,
        style = retained.style;
      if (object.shadow || object.clipPath || object.strokeDashArray?.length || object.globalCompositeOperation !== 'source-over') throw new Error('Edited member effects outside qualified envelope');
      if (!!object.fill === !!object.stroke) throw new Error('Edited knockout member requires exactly one fill or stroke paint');
      const retainedColor = object.fill ? style.fill : style.stroke,
        css = object.fill || object.stroke;
      const color = retainedColor && css === rgb(retainedColor) ? retainedColor : new fabric.Color(css).getSource().slice(0, 3).map(v => v / 255);
      if (!Number.isFinite(object.opacity) || object.opacity < 0 || object.opacity > 1) throw new Error('Invalid edited knockout opacity');
      const pathStream = JSON.stringify(retained.initialFabricPath) === JSON.stringify(object.path) ? retained.pathStream : pdfPath(object.path),
        own = object.calcOwnMatrix();
      const unchangedMatrix = JSON.stringify(own) === JSON.stringify(retained.initialOwnMatrix) && JSON.stringify(object.pathOffset) === JSON.stringify(retained.initialPathOffset);
      const invocationTransform = unchangedMatrix ? [1, 0, 0, 1, 0, 0] : matrix(matrix(matrix(matrix(inverse(original.sourceToViewport), original.initialGroupMatrix), own), translation(-object.pathOffset.x, -object.pathOffset.y)), inverse(retained.transform));
      return {
        ...clone(retained),
        invocationTransform,
        visible: object.visible !== false,
        opacity: object.opacity,
        pathStream,
        style: {
          fill: object.fill ? color : null,
          stroke: object.stroke ? color : null,
          strokeWidth: object.strokeWidth,
          lineCap: ['butt', 'round', 'square'].indexOf(object.strokeLineCap),
          lineJoin: ['miter', 'round', 'bevel'].indexOf(object.strokeLineJoin),
          miterLimit: object.strokeMiterLimit,
          paint: object.fill ? (object.fillRule === 'evenodd' ? 'f*' : 'f') : 'S'
        }
      };
    });
    const groupMatrix = group.calcTransformMatrix(),
      unchangedGroup = JSON.stringify(groupMatrix) === JSON.stringify(original.initialGroupMatrix);
    const unchangedOutput = JSON.stringify(outputFromScene) === '[1,0,0,1,0,0]' && outputHeight === original.height;
    // Preserve original placement numbers on the unchanged path. Multiplying
    // inverse/forward matrices would introduce binary tails that affect PDF
    // stroke adjustment even when the mathematical transform is identical.
    const sourceToPdf = unchangedGroup && unchangedOutput && original.sourceToPdf ? original.sourceToPdf : matrix(matrix(matrix(matrix(pageFromViewport, outputFromScene), groupMatrix), inverse(original.initialGroupMatrix)), original.sourceToViewport);
    return {
      ...clone(original),
      sourceToPdf,
      members
    };
  }

  function authorGroup(source, context, pdfLib) {
    const resources = context.obj({
      XObject: {},
      ExtGState: {}
    });
    for (let index = 0; index < source.members.length; index++) {
      const member = source.members[index],
        style = member.style,
        color = style.fill || style.stroke,
        op = style.fill ? 'rg' : 'RG';
      const commands = [`${color.map(n).join(' ')} ${op}`, `${n(style.strokeWidth)} w ${style.lineCap} J ${style.lineJoin} j ${n(style.miterLimit)} M [] 0 d`, '/Inside gs', 'q', `${member.transform.map(n).join(' ')} cm`, member.pathStream, style.paint, 'Q'].join('\n');
      const child = context.flateStream(commands, {
          Type: 'XObject',
          Subtype: 'Form',
          FormType: 1,
          BBox: member.bbox,
          Matrix: member.invocationTransform || [1, 0, 0, 1, 0, 0],
          Resources: {
            ExtGState: {
              Inside: {
                Type: 'ExtGState',
                ...member.insideState
              }
            }
          },
          Group: {
            Type: 'Group',
            S: 'Transparency',
            I: false,
            K: false
          }
        }),
        ref = context.register(child);
      resources.lookup(pdfLib.PDFName.of('XObject')).set(pdfLib.PDFName.of(`M${index}`), ref);
      const state = context.obj({
        Type: 'ExtGState',
        ...member.outerState,
        ca: member.opacity,
        CA: member.opacity,
        BM: 'Normal',
        SMask: 'None',
        AIS: false
      });
      resources.lookup(pdfLib.PDFName.of('ExtGState')).set(pdfLib.PDFName.of(`A${index}`), context.register(state));
    }
    let body = source.parentStream ? source.parentStream.replace(/\/GS([01])(?=\s+gs)/g, '/A$1').replace(/\/Fm([01])(?=\s+Do)/g, '/M$1') : source.members.map((_, index) => `q /A${index} gs /M${index} Do Q`).join('\n');
    source.members.forEach((member, index) => {
      if (member.visible === false) body = body.replace(new RegExp(`/M${index}\\s+Do`, 'g'), `% hidden canonical member ${index}\n`);
    });
    return context.flateStream(body, {
      Type: 'XObject',
      Subtype: 'Form',
      FormType: 1,
      BBox: source.bbox,
      Matrix: [1, 0, 0, 1, 0, 0],
      Resources: resources,
      Group: {
        Type: 'Group',
        S: 'Transparency',
        I: false,
        K: true
      }
    });
  }

  function emitPlaceholder(pdf, {
    token,
    source,
    pageHeight = source.height
  }) {
    if (!/^[A-Za-z0-9_-]{1,120}$/.test(token)) throw new Error('Invalid generated knockout placeholder token');
    let used = placeholderTokens.get(pdf);
    if (!used) {
      used = new Set();
      placeholderTokens.set(pdf, used);
    }
    if (used.has(token)) throw new Error('Duplicate knockout placeholder token');
    used.add(token);
    if (pdf.isAdvancedAPI()) throw new Error('Knockout placeholder requires the normal jsPDF mode between SVG chunks');
    const key = `figure-studio-knockout-${token}`,
      identity = new pdf.Matrix(1, 0, 0, 1, 0, 0),
      box = source.bbox;
    pdf.beginFormObject(box[0], box[1], box[2] - box[0], box[3] - box[1], identity);
    pdf.internal.write(`% FigureStudioPdfKnockout ${token}`);
    pdf.endFormObject(key);
    // jsPDF's Matrix.toString() otherwise expands decimal placement into
    // binary arithmetic tails. Use this module's declared authoring precision
    // consistently, or the preserved source-derived numerals when supplied.
    const placement = new pdf.Matrix(...source.sourceToPdf);
    const numerals = source.sourceToPdfNumerals || source.sourceToPdf.map(n);
    if (numerals.length !== 6 || numerals.some((value, index) => !Number.isFinite(Number(value)) || Math.abs(Number(value) - source.sourceToPdf[index]) > Number.EPSILON * Math.max(1, Math.abs(source.sourceToPdf[index])) * 8)) throw new Error('Source placement numerals do not describe the retained transform');
    pdf.internal.write('q');
    if (source.pdfAncestorClipCommands) pdf.internal.write(source.pdfAncestorClipCommands);
    placement.toString = () => numerals.join(' ');
    pdf.doFormObject(key, placement);
    pdf.internal.write('Q');
    return {
      token,
      source: clone(source)
    };
  }
  async function replacePlaceholderForms(pdfBytes, {
    pdfLib,
    placements
  }) {
    const document = await pdfLib.PDFDocument.load(pdfBytes),
      context = document.context,
      forms = [];
    context.header = pdfLib.PDFHeader.forVersion(1, 7);
    for (const [ref, object] of context.enumerateIndirectObjects())
      if (object instanceof pdfLib.PDFRawStream && object.dict.get(pdfLib.PDFName.of('Subtype'))?.asString() === '/Form') {
        const text = new TextDecoder('latin1').decode(pdfLib.decodePDFRawStream(object).decode());
        forms.push({
          ref,
          text
        });
      }
    const used = new Set();
    for (const placement of placements) {
      if (used.has(placement.token)) throw new Error('Repeated knockout replacement token');
      used.add(placement.token);
      const marker = `% FigureStudioPdfKnockout ${placement.token}`,
        matches = forms.filter(f => f.text.split(/\r?\n/).includes(marker));
      if (matches.length !== 1) throw new Error('Generated knockout placeholder absent or ambiguous');
      context.assign(matches[0].ref, authorGroup(placement.source, context, pdfLib));
    }
    if (forms.some(f => f.text.includes('% FigureStudioPdfKnockout ') && !placements.some(p => f.text.split(/\r?\n/).includes(`% FigureStudioPdfKnockout ${p.token}`)))) throw new Error('An emitted knockout placeholder was not replaced');
    return document.save({
      useObjectStreams: false
    });
  }
  async function generatedPdf(sources, {
    pdfLib,
    jsPDF
  }) {
    // jsPDF owns ordinary page construction; pdf-lib owns ONLY generated output
    // streams and dictionaries. No original source PDF is loaded or mutated.
    const first = sources[0],
      base = new jsPDF({
        unit: 'pt',
        format: [first.width, first.height],
        orientation: first.width > first.height ? 'landscape' : 'portrait',
        compress: false
      });
    for (const source of sources.slice(1)) base.addPage([source.width, source.height], source.width > source.height ? 'landscape' : 'portrait');
    const document = await pdfLib.PDFDocument.load(base.output('arraybuffer'));
    document.context.header = pdfLib.PDFHeader.forVersion(1, 7);
    for (let pageIndex = 0; pageIndex < sources.length; pageIndex++) {
      const source = sources[pageIndex],
        context = document.context,
        ref = context.register(authorGroup(source, context, pdfLib)),
        page = document.getPages()[pageIndex];
      page.node.set(pdfLib.PDFName.of('Resources'), context.obj({
        XObject: {
          Knockout: ref
        }
      }));
      page.node.set(pdfLib.PDFName.of('Contents'), context.register(context.flateStream(`q ${source.sourceToPdf.map(n).join(' ')} cm /Knockout Do Q`)));
    }
    return document.save({
      useObjectStreams: false
    });
  }

  function parseSvgTransform(value) {
    let result = [1, 0, 0, 1, 0, 0],
      offset = 0;
    const expression = /\s*(matrix|translate|scale|rotate|skewX|skewY)\s*\(([^)]*)\)\s*,?/gy;
    while (offset < String(value || '').length) {
      expression.lastIndex = offset;
      const match = expression.exec(value);
      if (!match) throw new Error('Unsupported SVG ancestor transform');
      offset = expression.lastIndex;
      const args = match[2].trim().split(/[\s,]+/).filter(Boolean).map(Number);
      if (args.some(v => !Number.isFinite(v))) throw new Error('Invalid SVG ancestor transform');
      let next;
      if (match[1] === 'matrix' && args.length === 6) next = args;
      else if (match[1] === 'translate' && (args.length === 1 || args.length === 2)) next = translation(args[0], args[1] || 0);
      else if (match[1] === 'scale' && (args.length === 1 || args.length === 2)) next = [args[0], 0, 0, args[1] ?? args[0], 0, 0];
      else if (match[1] === 'rotate' && (args.length === 1 || args.length === 3)) {
        const angle = args[0] * Math.PI / 180,
          c = Math.cos(angle),
          s = Math.sin(angle);
        next = [c, s, -s, c, 0, 0];
        if (args.length === 3) next = matrix(matrix(translation(args[1], args[2]), next), translation(-args[1], -args[2]));
      } else if ((match[1] === 'skewX' || match[1] === 'skewY') && args.length === 1) {
        const tangent = Math.tan(args[0] * Math.PI / 180);
        next = match[1] === 'skewX' ? [1, 0, tangent, 1, 0, 0] : [1, tangent, 0, 1, 0, 0];
      } else throw new Error('SVG transform arity outside the supported envelope');
      result = matrix(result, next);
    }
    return result;
  }

  function svgAttribute(element, name) {
    const inline = element.getAttribute('style') || '',
      property = inline.split(';').map(s => s.trim()).find(s => s.split(':')[0]?.trim() === name);
    return property ? property.slice(property.indexOf(':') + 1).trim() : element.getAttribute(name);
  }

  function neutralAncestor(element) {
    for (const key of ['opacity', 'fill-opacity', 'stroke-opacity']) {
      const value = svgAttribute(element, key);
      if (value !== null && value !== '' && Number(value) !== 1) throw new Error(`Knockout ancestor ${key} is outside the supported envelope`);
    }
    for (const key of ['mask', 'filter']) {
      const value = svgAttribute(element, key);
      if (value && value !== 'none') throw new Error(`Knockout ancestor ${key} is unsupported`);
    }
    const blend = svgAttribute(element, 'mix-blend-mode');
    if (blend && blend !== 'normal') throw new Error('Knockout ancestor blend mode is unsupported');
    if (element.localName.toLowerCase() === 'svg' && element.parentElement) throw new Error('Nested SVG viewport around knockout is unsupported');
    if (element.getAttribute('class')) throw new Error('Stylesheet-dependent knockout ancestors require resolved inline styles');
  }

  function hardClipCommands(clip, transform, {
    parsePath
  } = {}) {
    if ((clip.getAttribute('clipPathUnits') || 'userSpaceOnUse') !== 'userSpaceOnUse') throw new Error('Object-bounds knockout ancestor clips are unsupported');
    if (clip.children.length !== 1) throw new Error('Knockout ancestor clip needs one canonical hard path');
    neutralAncestor(clip);
    const shape = clip.children[0];
    neutralAncestor(shape);
    if (shape.getAttribute('clip-path')) throw new Error('Nested knockout ancestor clips are unsupported');
    const effective = matrix(matrix(transform, parseSvgTransform(clip.getAttribute('transform'))), parseSvgTransform(shape.getAttribute('transform')));
    const point = (x, y) => [effective[0] * x + effective[2] * y + effective[4], effective[1] * x + effective[3] * y + effective[5]];
    let path;
    if (shape.localName.toLowerCase() === 'rect') {
      const x = Number(shape.getAttribute('x') || 0),
        y = Number(shape.getAttribute('y') || 0),
        w = Number(shape.getAttribute('width')),
        h = Number(shape.getAttribute('height'));
      if (![x, y, w, h].every(Number.isFinite) || w < 0 || h < 0 || Number(shape.getAttribute('rx') || 0) || Number(shape.getAttribute('ry') || 0)) throw new Error('Rounded or invalid knockout ancestor clip is unsupported');
      path = [
        ['M', x, y],
        ['L', x + w, y],
        ['L', x + w, y + h],
        ['L', x, y + h],
        ['Z']
      ];
    } else if (shape.localName.toLowerCase() === 'path' && typeof parsePath === 'function') path = parsePath(shape.getAttribute('d'));
    else throw new Error('Knockout ancestor clip geometry is unsupported');
    const commands = path.map(([op, ...values]) => {
      if (op === 'M' || op === 'L') return `${point(...values).map(n).join(' ')} ${op.toLowerCase()}`;
      if (op === 'C') return `${[...point(values[0],values[1]),...point(values[2],values[3]),...point(values[4],values[5])].map(n).join(' ')} c`;
      if (op === 'Z' || op === 'z') return 'h';
      throw new Error('Ancestor clip parser must provide absolute M/L/C/Z commands');
    });
    const rule = svgAttribute(shape, 'clip-rule') || svgAttribute(clip, 'clip-rule') || 'nonzero';
    if (!['nonzero', 'evenodd'].includes(rule)) throw new Error('Unsupported ancestor clip winding rule');
    return `${commands.join('\n')}\n${rule==='evenodd'?'W*':'W'} n`;
  }

  function viewBoxToOutput(view, pageWidth, pageHeight, preserveAspectRatio = 'xMidYMid meet') {
    if (view.length !== 4 || view.some(v => !Number.isFinite(v)) || view[2] <= 0 || view[3] <= 0) throw new Error('Invalid ordered SVG viewBox');
    let sx = pageWidth / view[2],
      sy = pageHeight / view[3],
      x = 0,
      y = 0;
    const aspect = String(preserveAspectRatio || 'xMidYMid meet').trim();
    if (aspect !== 'none') {
      const match = /^(xMin|xMid|xMax)(YMin|YMid|YMax)(?:\s+(meet|slice))?$/.exec(aspect);
      if (!match) throw new Error('Unsupported ordered SVG aspect ratio');
      sx = sy = match[3] === 'slice' ? Math.max(sx, sy) : Math.min(sx, sy);
      const remainingX = pageWidth - view[2] * sx,
        remainingY = pageHeight - view[3] * sy;
      x = match[1] === 'xMin' ? 0 : match[1] === 'xMid' ? remainingX / 2 : remainingX;
      y = match[2] === 'YMin' ? 0 : match[2] === 'YMid' ? remainingY / 2 : remainingY;
    }
    return [sx, 0, 0, sy, x - view[0] * sx, y - view[1] * sy];
  }

  function createOrderedSvgPlan(svgRoot, {
    pageWidth,
    pageHeight,
    sourcesById,
    resolveSource,
    parsePath,
    sceneToOutput,
    idNamespace
  } = {}) {
    if (!svgRoot?.ownerDocument || svgRoot.localName.toLowerCase() !== 'svg') throw new Error('Ordered knockout export requires an SVG root');
    if (!(pageWidth > 0 && pageHeight > 0)) throw new Error('An output page extent is required');
    const view = (svgRoot.getAttribute('viewBox') || '').trim().split(/[\s,]+/).map(Number);
    const viewportMap = viewBoxToOutput(view, pageWidth, pageHeight, svgRoot.getAttribute('preserveAspectRatio'));
    if (sceneToOutput && !equalNumbers(sceneToOutput, viewportMap)) throw new Error('Explicit scene-to-output map does not match the exported SVG viewport');
    const outputMap = sceneToOutput || viewportMap;
    const planId = idNamespace || `plan-${++orderedPlanSerial}`;
    if (!/^[A-Za-z0-9_-]{1,70}$/.test(planId)) throw new Error('Invalid ordered export namespace');
    const document = svgRoot.ownerDocument,
      parts = [],
      sourceToOutput = [],
      definitions = Array.from(svgRoot.children).filter(node => ['defs', 'style', 'metadata', 'title', 'desc'].includes(node.localName.toLowerCase()));
    // Fonts may remain in stylesheets. Compositing styles must already be
    // resolved inline, so a selector cannot silently change an ancestor effect.
    if (Array.from(svgRoot.querySelectorAll('style')).some(style => style.textContent.replace(/@font-face\s*\{[^}]*\}/g, '').trim())) throw new Error('Ordered knockout export requires resolved compositing styles');
    const ids = new Map(Array.from(svgRoot.querySelectorAll('[id]')).map(element => [element.id || element.getAttribute('id'), element]));
    let root = null,
      clones = null,
      regularCount = 0,
      paintOrder = 0;
    const marker = element => element.getAttribute('data-pdf-knockout-source-id');
    const containsMarker = element => !!marker(element) || !!element.querySelector('[data-pdf-knockout-source-id]');

    function chunk() {
      if (root) return;
      root = svgRoot.cloneNode(false);
      // This wrapper is authored to coincide with the PDF page. Setting its
      // point extents and visible overflow removes only the redundant wrapper
      // clip; all retained ancestor and member clips remain in the subtree.
      root.setAttribute('width', n(pageWidth));
      root.setAttribute('height', n(pageHeight));
      root.setAttribute('x', '0');
      root.setAttribute('y', '0');
      root.setAttribute('overflow', 'visible');
      root.setAttribute('style', (root.getAttribute('style') || '') + ';overflow:visible');
      for (const definition of definitions) root.appendChild(definition.cloneNode(true));
      clones = new Map([
        [svgRoot, root]
      ]);
    }

    function append(element, ancestors) {
      chunk();
      let parent = root;
      for (const ancestor of ancestors) {
        if (ancestor === svgRoot) continue;
        if (!clones.has(ancestor)) {
          const copy = ancestor.cloneNode(false);
          parent.appendChild(copy);
          clones.set(ancestor, copy);
        }
        parent = clones.get(ancestor);
      }
      parent.appendChild(element.cloneNode(true));
      regularCount++;
    }

    function flush() {
      if (root && regularCount) {
        parts.push({
          kind: 'svg',
          svgElement: root,
          order: parts.length
        });
      }
      root = null;
      clones = null;
      regularCount = 0;
    }

    function visit(element, ancestors) {
      if (['defs', 'style', 'metadata', 'title', 'desc'].includes(element.localName.toLowerCase())) return;
      const sourceId = marker(element);
      if (sourceId) {
        flush();
        for (const ancestor of ancestors) neutralAncestor(ancestor);
        if (ancestors.some(a => svgAttribute(a, 'display') === 'none' || svgAttribute(a, 'visibility') === 'hidden') || svgAttribute(element, 'display') === 'none' || svgAttribute(element, 'visibility') === 'hidden') return;
        const source = resolveSource ? resolveSource(sourceId, element) : sourcesById instanceof Map ? sourcesById.get(sourceId) : sourcesById?.[sourceId];
        if (!source || source.sourceId !== sourceId) throw new Error('Canonical knockout source is unavailable for ordered export');
        let transform = [1, 0, 0, 1, 0, 0],
          clips = [];
        for (const ancestor of ancestors) {
          transform = matrix(transform, parseSvgTransform(ancestor.getAttribute('transform')));
          const value = svgAttribute(ancestor, 'clip-path');
          if (value && value !== 'none') {
            const match = /^url\(\s*["']?#([^\s"')]+)["']?\s*\)$/.exec(value),
              clip = match && ids.get(match[1]);
            if (!clip || clip.localName.toLowerCase() !== 'clippath') throw new Error('Unresolved knockout ancestor clip');
            clips.push(hardClipCommands(clip, matrix(matrix([1, 0, 0, -1, 0, pageHeight], outputMap), transform), {
              parsePath
            }));
          }
        }
        const token = `knockout-${planId}-${parts.length}-${sourceToOutput.length}`,
          placementSource = {
            ...clone(source),
            pdfAncestorClipCommands: clips.join('\n')
          };
        parts.push({
          kind: 'knockout',
          token,
          source: placementSource,
          order: parts.length
        });
        sourceToOutput.push({
          sourceId,
          sourceInstanceId: element.getAttribute('data-pdf-knockout-instance-id') || null,
          sourceSha256: source.sourceSha256,
          pageNumber: source.pageNumber,
          scopeStart: source.scopeStart,
          scopeEnd: source.scopeEnd,
          token,
          partIndex: parts.length - 1,
          paintOrder: paintOrder++
        });
      } else if (containsMarker(element)) {
        if (element.localName.toLowerCase() !== 'g') throw new Error('Knockout traversal container is unsupported');
        for (const child of element.children) visit(child, [...ancestors, element]);
      } else append(element, ancestors);
    }
    for (const element of svgRoot.children) visit(element, [svgRoot]);
    flush();
    return {
      schema: 'figureStudio.pdfKnockoutOrderedExport.v1',
      pageWidth,
      pageHeight,
      sceneToOutput: [...outputMap],
      parts,
      sourceToOutput
    };
  }

  function equalNumbers(a, b) {
    return a.length === b.length && a.every((value, index) => value === b[index]);
  }
  async function writeOrderedSvg(pdf, plan, {
    prepareSvg,
    onProgress
  } = {}) {
    if (pdf.internal.scaleFactor !== 1) throw new Error('Ordered knockout writer currently requires jsPDF point units');
    const placements = [];
    for (const part of plan.parts) {
      if (part.kind === 'svg') {
        let root = part.svgElement.cloneNode(true);
        if (prepareSvg) {
          const prepared = await prepareSvg(root);
          if (prepared?.nodeType === 1) root = prepared;
        }
        await pdf.svg(root, {
          x: 0,
          y: 0,
          width: plan.pageWidth,
          height: plan.pageHeight
        });
      } else if (part.kind === 'knockout') placements.push(emitPlaceholder(pdf, {
        token: part.token,
        source: part.source,
        pageHeight: plan.pageHeight
      }));
      else throw new Error('Unknown ordered export part');
      onProgress?.({
        phase: 'ordered-pdf-export',
        completedParts: part.order + 1,
        totalParts: plan.parts.length
      });
    }
    return {
      placements,
      sourceToOutput: clone(plan.sourceToOutput)
    };
  }
  return {
    SCHEMA,
    validateSource,
    registerClass,
    createScene,
    shapeHit,
    memberHitRole,
    svgForGroup,
    sceneSource,
    emitPlaceholder,
    replacePlaceholderForms,
    generatedPdf,
    svgPath,
    matrix,
    parseSvgTransform,
    viewBoxToOutput,
    hardClipCommands,
    createOrderedSvgPlan,
    writeOrderedSvg
  };
});
