/* Keep admitted native painting in one actual main-Canvas scene plane.
 * Geometry, layout, style, clips and the actual painters remain Fabric's.
 */
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.FigureStudioNativePathSceneTransform = api;
})(typeof globalThis === 'object' ? globalThis : this, function () {
  'use strict';
  const installers = new WeakMap();
  const screenSegments = new WeakMap();
  const passivePaintObservers = new WeakSet();
  const bundledFabric = typeof module === 'object' && module.exports ? require('../vendor/fabric/index.min.js') : globalThis.fabric;
  const nativeGroupDrawObject = bundledFabric?.Group?.prototype.drawObject;
  const regexpSource = Object.getOwnPropertyDescriptor(RegExp.prototype, 'source').get;
  const regexpFlags = Object.getOwnPropertyDescriptor(RegExp.prototype, 'flags').get;
  // These values are derived by Fabric painting/hit testing, never inputs to
  // the screen artwork. Everything else is checked, including nested source
  // glyph data, path commands, styles, clips, ownership and drawing order.
  const derivedScreenKeys = new Set(['dirty', 'ownCaching', '_cacheCanvas', '_cacheContext',
    'cacheTranslationX', 'cacheTranslationY', 'zoomX', 'zoomY', '_transformDone', 'matrixCache', 'ownMatrixCache',
    'aCoords', 'oCoords', 'lineCoords', '__pdfCurrentNativeClipActive',
    'controls', '__eventListeners', 'layoutManager', '_objectsToRender', 'draggableTextDelegate', 'cursorOffsetCache']);

  // First-party diagnostic observers explicitly promise not to mutate artwork.
  // Ordinary foreign Fabric callbacks retain the complete painter.
  function registerPassivePaintObserver(callback) {
    if (typeof callback !== 'function') throw new Error('A passive paint callback is required.');
    passivePaintObservers.add(callback);
  }
  function passivePaintCallbacks(canvas) {
    const descriptor = Object.getOwnPropertyDescriptor(canvas, '__eventListeners');
    if (!descriptor) return true;
    if (!Object.hasOwn(descriptor, 'value') || !descriptor.value) return false;
    const listeners = descriptor.value;
    return ['before:render', 'after:render'].every(key => {
      const descriptor = Object.getOwnPropertyDescriptor(listeners, key);
      if (!descriptor) return true;
      if (!Object.hasOwn(descriptor, 'value') || !Array.isArray(descriptor.value)) return false;
      const rows = descriptor.value;
      if (rows.length > 1024) return false;
      for (let index = 0; index < rows.length; index++)
        if (!passivePaintObservers.has(Object.getOwnPropertyDescriptor(rows, String(index))?.value)) return false;
      return true;
    });
  }

  function createFontFaceGuard(document) {
    const fonts = document.fonts;
    if (!fonts || fonts.status !== 'loaded') throw new Error('Screen fonts are still loading.');
    const faces = Array.from(fonts), fields = ['family', 'style', 'weight', 'stretch', 'unicodeRange', 'variant',
      'featureSettings', 'variationSettings', 'display', 'ascentOverride', 'descentOverride', 'lineGapOverride', 'status'];
    const records = faces.map(face => fields.map(key => face[key]));
    return () => {
      const current = Array.from(fonts);
      return document.fonts === fonts && fonts.status === 'loaded' && current.length === faces.length
        && current.every((face, index) => face === faces[index] && fields.every((key, at) => Object.is(face[key], records[index][at])));
    };
  }

  function captureScreenState({ fabric, canvas, object, admit, inputs = [] }) {
    if (typeof canvas.backgroundColor !== 'string' || !/^#[0-9a-f]{6}$/i.test(canvas.backgroundColor)
        || canvas.backgroundImage != null || canvas.clipPath || canvas.overlayImage || canvas.overlayColor)
      throw new Error('Screen point layers require an opaque solid background.');
    const roots = canvas.getObjects(), nodes = [], leaves = [], clips = new Set(), seen = new Set(), records = [], resources = [], references = new Set([canvas]);
    function visit(node, depth = 0, clipping = false) {
      if (!node || seen.has(node) || depth > 48 || nodes.length >= 10000) throw new Error('Screen artwork graph is not bounded.');
      seen.add(node); nodes.push(node); references.add(node);
      if (clipping) clips.add(node);
      if (!admit(node, clipping)) throw new Error('Screen artwork has an unsupported painter.');
      const children = node._objects;
      if (children?.length) for (const child of children) visit(child, depth + 1, clipping);
      else if (!clipping) leaves.push(node);
      if (node.clipPath) visit(node.clipPath, depth + 1, true);
    }
    roots.forEach(node => visit(node));
    const index = leaves.indexOf(object);
    if (index < 0 || !object.group) throw new Error('Screen point editing requires one nested native path.');
    const dataSeen = new Set(); let fields = 0;
    function data(value, depth = 0, top = false, prototypeRecord = false) {
      if (!value || typeof value !== 'object' || references.has(value) && !top || dataSeen.has(value)) return;
      if (depth > 48 || fields > 500000) throw new Error('Screen state exceeds its data envelope.');
      dataSeen.add(value);
      const prototype = Object.getPrototypeOf(value);
      if (!top && prototype === RegExp.prototype) {
        const source = regexpSource.call(value), flags = regexpFlags.call(value);
        resources.push(() => regexpSource.call(value) === source && regexpFlags.call(value) === flags);
      }
      if (!top && !Array.isArray(value) && prototype !== Object.prototype && prototype !== null
          && prototype !== fabric.Point.prototype && prototype !== RegExp.prototype) {
        // PDF image resources are loaded, immutable PNG URLs. Replacing their
        // decoded image or changing its URL/dimensions invalidates the layer.
        const Image = fabric.getEnv?.().window?.HTMLImageElement;
        if (!Image || !(value instanceof Image) || !value.complete || !value.naturalWidth
            || !value.src.startsWith('data:image/png;base64,')) throw new Error('Screen state contains a mutable external resource.');
        const binary = atob(value.src.slice(value.src.indexOf(',') + 1));
        if (binary.length < 20 || binary.slice(0, 8) !== '\x89PNG\r\n\x1a\n') throw new Error('Screen image is not a native PNG.');
        for (let at = 8; at + 12 <= binary.length;) {
          const size = (binary.charCodeAt(at) * 0x1000000 + (binary.charCodeAt(at + 1) << 16)
            + (binary.charCodeAt(at + 2) << 8) + binary.charCodeAt(at + 3));
          const tag = binary.slice(at + 4, at + 8);
          if (tag === 'acTL' || at + size + 12 > binary.length) throw new Error('Animated or malformed PNG screen resources are unsupported.');
          at += size + 12;
        }
        const selected = ['src', 'currentSrc', 'complete', 'naturalWidth', 'naturalHeight'].map(key => [key, value[key]]);
        resources.push(() => selected.every(([key, expected]) => value[key] === expected));
        return;
      }
      const ignore = key => top && (derivedScreenKeys.has(key)
        || value === object && ['path', 'figureStudioBezierNodeMeta'].includes(key));
      const keys = Reflect.ownKeys(value).filter(key => !ignore(key));
      if (!prototypeRecord && keys.some(key => typeof key !== 'string')) throw new Error('Screen state has an unknown symbol input.');
      const entries = keys.map(key => {
        const descriptor = Object.getOwnPropertyDescriptor(value, key);
        if (!Object.hasOwn(descriptor, 'value')) {
          if (!prototypeRecord) throw new Error('Screen state cannot read a foreign accessor.');
          return [key, undefined, descriptor.get, descriptor.set];
        }
        fields++;
        try { data(descriptor.value, depth + 1); }
        catch (error) { throw new Error(key + ': ' + error.message); }
        return [key, descriptor.value];
      });
      records.push({ value, prototype, entries, ignore, prototypeRecord });
    }
    for (const node of nodes) {
      data(node, 0, true);
      for (let prototype = Object.getPrototypeOf(node); prototype && prototype !== Object.prototype; prototype = Object.getPrototypeOf(prototype)) data(prototype, 0, true, true);
    }
    data(RegExp.prototype, 0, true, true);
    inputs.forEach(value => data(value));
    const view = screenView(canvas), canvasState = ['backgroundColor', 'backgroundImage', 'backgroundVpt',
      'clipPath', 'overlayColor', 'overlayImage', 'preserveObjectStacking', 'skipOffscreen',
      '_renderObjects', '_renderBackground', 'getObjects', 'getRetinaScaling'].map(key => [key, canvas[key]]);
    let failure = null;
    const fail = (reason, key) => { failure = { reason, key: String(key || '') }; return false; };
    const guard = () => {
      failure = null;
      if (!sameScreenView(canvas, view) || canvas.getObjects().length !== roots.length
          || canvas.getObjects().some((root, i) => root !== roots[i]) || canvasState.some(([key, value]) => canvas[key] !== value)) return fail('view or canvas');
      for (const record of records) {
        if (Object.getPrototypeOf(record.value) !== record.prototype
            || Reflect.ownKeys(record.value).filter(key => !record.ignore(key)).length !== record.entries.length) return fail('prototype or keys', record.entries[0]?.[0]);
        for (const [key, expected, getter, setter] of record.entries) {
          const descriptor = Object.getOwnPropertyDescriptor(record.value, key);
          if (!descriptor || (getter || setter ? Object.hasOwn(descriptor, 'value') || descriptor.get !== getter || descriptor.set !== setter
            : !Object.hasOwn(descriptor, 'value') || !Object.is(descriptor.value, expected))) return fail('data', key);
        }
      }
      return resources.every(valid => valid()) && nodes.every(node => admit(node, clips.has(node))) || fail('resource or painter');
    };
    const moving = new Set();
    for (let owner = object; owner; owner = owner.group) moving.add(owner);
    const activeRecords = records.filter(record => record.prototypeRecord || moving.has(record.value));
    // During the App-owned point transaction, publication invalidation owns
    // static artwork. Check the live object's non-path inputs and ancestors
    // cheaply; no second full-graph scan is added to each pointer frame.
    const activeGuard = () => {
      if (canvas.disposed || canvas.destroyed || !sameScreenView(canvas, view) || !passivePaintCallbacks(canvas)
          || canvasState.some(([key, value]) => canvas[key] !== value)) return false;
      for (const record of activeRecords) {
        if (Object.getPrototypeOf(record.value) !== record.prototype
            || Reflect.ownKeys(record.value).filter(key => !record.ignore(key)).length !== record.entries.length) return false;
        for (const [key, expected, getter, setter] of record.entries) {
          const descriptor = Object.getOwnPropertyDescriptor(record.value, key);
          if (!descriptor || (getter || setter ? Object.hasOwn(descriptor, 'value') || descriptor.get !== getter || descriptor.set !== setter
            : !Object.hasOwn(descriptor, 'value') || !Object.is(descriptor.value, expected))) return false;
        }
      }
      return resources.every(valid => valid());
    };
    return Object.freeze({ guard, activeGuard, diagnostics: () => failure, before: leaves.slice(0, index), after: leaves.slice(index + 1), fields, nodes: nodes.length });
  }

  async function preparePointScreenPreview({ fabric, canvas, object, admit, current, yieldFrame, inputs, signal }) {
    let prefix, suffix, live, reuse, closed = false, active = () => false;
    const startedAt = performance.now();
    const close = () => {
      closed = true;
      reuse?.stop();
      releaseScreenSegment(prefix); releaseScreenSegment(suffix); releaseScreenSegment(live);
      signal?.removeEventListener('abort', close);
    };
    signal?.addEventListener('abort', close, { once: true });
    let state;
    const valid = () => {
      try { return !closed && current() === true && state.activeGuard(); }
      catch (_) { return false; }
    };
    const checkpoint = async () => {
      await yieldFrame();
      if (!valid()) throw new Error('Screen point preparation was superseded: '
        + (closed ? 'cancelled' : current() !== true ? current.reason?.() || 'owner' : JSON.stringify(state.diagnostics())));
    };
    try {
      await yieldFrame();
      if (closed || signal?.aborted || current() !== true) throw new Error('Screen point preparation was superseded.');
      state = captureScreenState({ fabric, canvas, object, admit, inputs });
      await checkpoint();
      prefix = createScreenSegment({ fabric, canvas, objects: state.before, background: true });
      await checkpoint();
      suffix = createScreenSegment({ fabric, canvas, objects: state.after });
      await checkpoint();
      live = createScreenSegment({ fabric, canvas, objects: [object] });
      const combined = screenSegments.get(live), context = combined.element.getContext('2d');
      // The live layer is now disposable scratch space for the exact screen
      // preflight. The actual editable object continues to paint natively.
      context.save();
      try {
        context.setTransform(1, 0, 0, 1, 0, 0);
        context.globalCompositeOperation = 'destination-over';
        context.drawImage(screenSegments.get(prefix).element, 0, 0);
        context.globalCompositeOperation = 'source-over';
        context.drawImage(screenSegments.get(suffix).element, 0, 0);
      } finally { context.restore(); }
      // Compare full resolution in bounded strips, with a real frame between
      // strips. Any rounding/compositing difference retains ordinary painting.
      for (let y = 0; y < combined.view.height; y += 256) {
        await checkpoint();
        const height = Math.min(256, combined.view.height - y);
        const actual = canvas.contextContainer.getImageData(0, y, combined.view.width, height).data;
        const composed = context.getImageData(0, y, combined.view.width, height).data;
        if (actual.length !== composed.length) throw new Error('Screen point layers do not reproduce the native pixels.');
        for (let index = 0; index < actual.length; index++)
          if (actual[index] !== composed[index]) throw new Error('Screen point layers do not reproduce the native pixels.');
      }
      releaseScreenSegment(live); live = null;
      if (!valid() || !state.guard()) throw new Error('Screen point preparation changed before issue.');
      const preparingMs = performance.now() - startedAt;
      return Object.freeze({ close, valid, end() {
        const result = reuse?.pause(); reuse = null; active = () => false; return result;
      }, start(isActive) {
        try {
          // The issued full-state/pixel proof remains current through App's
          // publication revision. Do not rescan400k fields on pointerdown.
          if (reuse || typeof isActive !== 'function' || !valid()) { close(); return false; }
          active = isActive;
          reuse = beginScreenFrameReuse({ fabric, canvas, prefix, suffix, objects: [object], guard: () => active() === true && valid() });
          return true;
        } catch (_) { close(); return false; }
      }, diagnostics: () => ({ ready: !closed && (!reuse || !reuse.diagnostics().closed), preparingMs,
        fields: state.fields, nodes: state.nodes, ...reuse?.diagnostics() }) });
    } catch (error) { close(); throw error; }
  }

  function install({ fabric, canvas, isIsolated, isNativePath, importedPaintKind }) {
    if (!fabric?.Path?.prototype || !fabric?.Group || typeof canvas?._renderObjects !== 'function'
        || typeof isIsolated !== 'function' || isNativePath != null && typeof isNativePath !== 'function'
        || importedPaintKind != null && typeof importedPaintKind !== 'function') throw new Error('Native path scene painting requires its Fabric canvas.');
    const prototype = fabric.Path.prototype;
    let installed = installers.get(prototype);
    if (!installed) {
      // Screen segments use the same native objects and painters. Only their
      // membership in one synchronous paint pass changes; the live tree stays
      // intact, including its parent/clip ownership and drawing order.
      for (const Class of [fabric.Path, fabric.Group, fabric.FabricImage || fabric.Image]) {
        if (!Class?.prototype?.drawObject) continue;
        const nativeDrawObject = Class.prototype.drawObject;
        Class.prototype.drawObject = function (context, forClipping, ...args) {
          if (!forClipping && !shouldPaintScreenObject(fabric, this, context)) return;
          const screen = installers.get(prototype)?.screen;
          if (!forClipping && Class === fabric.Group && nativeDrawObject === nativeGroupDrawObject
              && screen?.context === context && screen.canvas === this.canvas) {
            // The bundled native Group.drawObject traversal, with membership
            // tested before child.render (including its transform/cache work).
            // Parent ownership, Z-order, background and clip dispatch stay native.
            this._renderBackground(context);
            for (const child of this._objects) {
              if (!screen.allowed.has(child)) continue;
              if (this.canvas?.preserveObjectStacking && child.group !== this) {
                context.save();
                try { context.transform(...fabric.util.invertTransform(this.calcTransformMatrix())); child.render(context); }
                finally { context.restore(); }
              } else if (child.group === this) child.render(context);
            }
            return this._drawClipPath(context, this.clipPath, args[0]);
          }
          return nativeDrawObject.call(this, context, forClipping, ...args);
        };
        const materializer = typeof module === 'object' && module.exports
          ? require('./pdf-svg-materializer.js') : globalThis.FigureStudioPdfSvgMaterializer;
        if (materializer?.bindScreenDrawObject && !materializer.bindScreenDrawObject(fabric, Class, nativeDrawObject, Class.prototype.drawObject))
          throw new Error('Screen object painting cannot refresh a foreign clip painter.');
        // Clip-backed images can cache even when objectCaching is false. That
        // route composites without calling drawObject on the screen context.
        const nativeDrawCache = Class.prototype.drawCacheOnCanvas;
        if (typeof nativeDrawCache === 'function') Class.prototype.drawCacheOnCanvas = function (context, ...args) {
          if (!shouldPaintScreenObject(fabric, this, context)) return;
          return nativeDrawCache.call(this, context, ...args);
        };
      }
      const nativeTransform = prototype.transform, textPrototype = (fabric.IText || fabric.Text)?.prototype;
      const nativeTextTransform = textPrototype?.transform;
      const Image = fabric.FabricImage || fabric.Image, imagePrototype = Image?.prototype, nativeImageTransform = imagePrototype?.transform;
      const nativeImageMethods = imagePrototype && Object.fromEntries(['render', 'drawObject', '_render', '_renderFill', '_stroke',
        '_renderPaintInOrder', '_renderStroke', '_setFillStyles', '_setStrokeStyles', 'calcOwnMatrix', 'calcTransformMatrix',
        'shouldCache', 'needsItsOwnCache', 'getElement'].map(key => [key, imagePrototype[key]]));
      const nativeGroup = Object.fromEntries(['transform', 'render', 'drawObject', '_render', 'calcOwnMatrix', 'calcTransformMatrix']
        .map(key => [key, fabric.Group.prototype[key]]));
      installed = { plane: null, canvases: new WeakMap(), nativePathRender: prototype._render, fabric, nativeGroup };
      const unchanged = (object, methods) => Object.entries(methods).every(([key, value]) => object[key] === value);
      const ordinaryPathMethods = Object.fromEntries(['render', 'drawObject', '_renderPathCommands', '_renderPaintInOrder',
        '_renderFill', '_renderStroke', '_setFillStyles', '_setStrokeStyles', 'calcOwnMatrix', 'calcTransformMatrix']
        .map(key => [key, prototype[key]]));
      const plain = object => object.objectCaching === false && object.ownCaching !== true && object.visible !== false
        && object.opacity === 1 && !object.transformMatrix && !object.mask && !object.shadow && !object.backgroundColor
        && !object.filters?.length && !object.resizeFilter && !object.figureStudioAppearanceStack && !object.figureStudioAppearanceMeta
        && (!object.globalCompositeOperation || object.globalCompositeOperation === 'source-over');
      installed.imported = (object, registered, ownerCanvas) => {
        if (!registered?.importedPaintKind) return false;
        let leaf = true, depth = 0;
        for (let owner = object; owner; owner = owner.group) {
          if (++depth > 48 || !plain(owner) || (ownerCanvas ? owner.canvas !== ownerCanvas : owner.canvas != null)) return false;
          const kind = registered.importedPaintKind(owner);
          if (leaf && !['path', 'text', 'image', 'group'].includes(kind)) return false;
          if (!leaf && kind !== 'group') {
            if (owner.constructor !== fabric.Group || owner.clipPath || !unchanged(owner, nativeGroup)) return false;
          } else if (kind === 'path') {
            if (owner.transform !== sceneTransform || !registered.isNativePath?.(owner)) return false;
            if (owner.constructor === fabric.Path && !unchanged(owner, ordinaryPathMethods)) return false;
          } else if (kind === 'text') {
            if (owner.transform !== textSceneTransform) return false;
          } else if (kind === 'image') {
            if (owner.constructor !== Image || owner.transform !== imageSceneTransform || owner.clipPath
                || !unchanged(owner, nativeImageMethods) || owner.cropX !== 0 || owner.cropY !== 0
                || owner._filterScalingX !== 1 || owner._filterScalingY !== 1 || typeof owner.imageSmoothing !== 'boolean') return false;
            const element = owner.getElement();
            if (!element || element !== owner._element || element !== owner._originalElement) return false;
          } else if (kind === 'group' && owner.transform !== nativeGroup.transform) return false;
          leaf = false;
        }
        return true;
      };
      const unsupported = object => object.clipPath || object.mask || object.shadow || object.filters?.length
        || object.figureStudioAppearanceStack || object.figureStudioAppearanceMeta
        || object.globalCompositeOperation && object.globalCompositeOperation !== 'source-over';
      function sceneTransform(context) {
        const plane = installed.plane, registered = plane && installed.canvases.get(plane.canvas);
        if (plane?.context === context && this.canvas === plane.canvas && installed.imported(this, registered, plane.canvas)
            && setWorld(installed, context, plane.matrix, this)) return;
        let eligible = plane?.context === context && registered && this.canvas === plane.canvas
          && this.constructor === fabric.Path && this.transform === sceneTransform && this.group && this.objectCaching === false
          && prototype._render === installed.nativePathRender && this.ownCaching !== true && !unsupported(this)
          && (registered.isNativePath ? registered.isNativePath(this) : this._render === installed.nativePathRender)
          && registered.isIsolated();
        for (let parent = this.group; eligible && parent; parent = parent.group) {
          eligible = parent.constructor === fabric.Group && parent.canvas === plane.canvas
            && parent.objectCaching === false && parent.ownCaching !== true && !unsupported(parent)
            && parent.transform === fabric.Group.prototype.transform && parent.drawObject === fabric.Group.prototype.drawObject
            && parent.render === fabric.Group.prototype.render && parent._render === fabric.Group.prototype._render;
        }
        if (eligible) {
          // Parent fit-content layout can rebase local coordinates while the
          // complete world matrix stays exact. One native setTransform avoids
          // the different intermediate Canvas rounding from those equivalent
          // parent/local decompositions. Keep the existing clipping/style state.
          context.setTransform(...fabric.util.multiplyTransformMatrices(plane.matrix, this.calcTransformMatrix()));
          return;
        }
        return nativeTransform.call(this, context);
      }
      function textSceneTransform(context) {
        const plane = installed.plane, registered = plane && installed.canvases.get(plane.canvas);
        if (plane?.context === context && this.canvas === plane.canvas && installed.imported(this, registered, plane.canvas)
            && setWorld(installed, context, plane.matrix, this)) return;
        return nativeTextTransform.call(this, context);
      }
      function imageSceneTransform(context) {
        const plane = installed.plane, registered = plane && installed.canvases.get(plane.canvas);
        if (plane?.context === context && this.canvas === plane.canvas && installed.imported(this, registered, plane.canvas)
            && setWorld(installed, context, plane.matrix, this)) return;
        return nativeImageTransform.call(this, context);
      }
      prototype.transform = sceneTransform;
      if (textPrototype) textPrototype.transform = textSceneTransform;
      if (imagePrototype) imagePrototype.transform = imageSceneTransform;
      installers.set(prototype, installed);
    }
    if (installed.canvases.has(canvas)) return;
    const registered = { isIsolated, isNativePath, importedPaintKind, reuse: null };
    installed.canvases.set(canvas, registered);
    const nativeRenderObjects = canvas._renderObjects;
    canvas._renderObjects = function (context, objects) {
      const previous = installed.plane, matrix = context.getTransform();
      // Fabric has already applied the actual viewport and retina transform.
      // Only this fixed main paint context can use the complete scene matrix;
      // caches, exports and temporary staging contexts retain native transforms.
      const screen = installed.screen;
      installed.plane = context === this.contextContainer || screen?.canvas === this && screen.context === context
        ? { canvas: this, context, matrix: [matrix.a, matrix.b, matrix.c, matrix.d, matrix.e, matrix.f] } : null;
      try {
        const prepared = context === this.contextContainer && registered.prepared;
        if (prepared) {
          registered.prepared = null;
          let valid = false;
          try { valid = prepared.current() === true && passivePaintCallbacks(this) && sameScreenView(this, prepared.segment.view)
            && [matrix.a, matrix.b, matrix.c, matrix.d, matrix.e, matrix.f].every((value, index) => Object.is(value, prepared.segment.plane[index])); }
          catch (_) { /* The ordinary complete painter owns unknown state. */ }
          if (valid) {
            context.save();
            try { context.setTransform(1, 0, 0, 1, 0, 0); context.drawImage(prepared.segment.element, 0, 0); }
            finally { context.restore(); prepared.close(); }
            return;
          }
          prepared.close();
        }
        const reuse = context === this.contextContainer && registered.reuse;
        if (reuse) {
          let valid = false;
          try { valid = reuse.guard() === true && sameScreenView(this, reuse.prefix.view)
            && [matrix.a, matrix.b, matrix.c, matrix.d, matrix.e, matrix.f].every((value, index) => Object.is(value, reuse.prefix.plane[index])); }
          catch (_) { /* An unknown state always returns to the complete painter. */ }
          if (valid) {
            const previousScreen = installed.screen;
            try {
              context.save();
              try { context.setTransform(1, 0, 0, 1, 0, 0); context.drawImage(reuse.prefix.element, 0, 0); }
              finally { context.restore(); }
              installed.screen = { canvas: this, context, allowed: reuse.allowed };
              nativeRenderObjects.call(this, context, objects.filter(object => reuse.allowed.has(object)));
              context.save();
              try { context.setTransform(1, 0, 0, 1, 0, 0); context.drawImage(reuse.suffix.element, 0, 0); }
              finally { context.restore(); }
              reuse.audit.frames++;
              return;
            } finally { installed.screen = previousScreen; }
          }
          reuse.audit.fallbacks++;
          reuse.stop();
        }
        return nativeRenderObjects.call(this, context,
          screen?.canvas === this && screen.context === context ? objects.filter(object => screen.allowed.has(object)) : objects);
      }
      finally { installed.plane = previous; }
    };
    registered.renderObjects = canvas._renderObjects;
  }

  function shouldPaintScreenObject(fabric, object, context) {
    const screen = installers.get(fabric?.Path?.prototype)?.screen;
    return !screen || screen.context !== context || screen.canvas !== object.canvas || screen.allowed.has(object);
  }

  function screenView(canvas) {
    return { lower: canvas.lowerCanvasEl, context: canvas.contextContainer,
      width: canvas.lowerCanvasEl.width, height: canvas.lowerCanvasEl.height,
      logicalWidth: canvas.width, logicalHeight: canvas.height, retina: canvas.getRetinaScaling(),
      viewport: canvas.viewportTransform.slice() };
  }

  function sameScreenView(canvas, view) {
    const current = screenView(canvas);
    return current.lower === view.lower && current.context === view.context && current.width === view.width && current.height === view.height
      && current.logicalWidth === view.logicalWidth && current.logicalHeight === view.logicalHeight && Object.is(current.retina, view.retina)
      && current.viewport.length === view.viewport.length && current.viewport.every((value, index) => Object.is(value, view.viewport[index]));
  }

  function screenMembership(canvas, objects) {
    if (!Array.isArray(objects) || objects.length > 100000) throw new Error('Screen segment requires a bounded object list.');
    const allowed = new WeakSet();
    for (const object of objects) {
      let depth = 0;
      for (let current = object; current; current = current.group) {
        if (++depth > 48 || current.canvas !== canvas) throw new Error('Screen segment ownership changed.');
        allowed.add(current);
      }
    }
    return allowed;
  }

  function applyScreenBase(context, base, retina) {
    // Fabric initializes its display backing with scale(retina, retina).
    // Canvas getTransform() may expose Float32-rounded coefficients; replay
    // the original operation when this is that known native backing matrix.
    const nativeScale = value => Object.is(value, retina) || Object.is(value, Math.fround(retina));
    if (base[1] === 0 && base[2] === 0 && base[4] === 0 && base[5] === 0 && nativeScale(base[0]) && nativeScale(base[3])) {
      context.setTransform(1, 0, 0, 1, 0, 0); context.scale(retina, retina);
    } else context.setTransform(...base);
  }

  // A derived, disposable screen layer. No source property, tree, geometry,
  // contextContainer, viewport, or export painter is temporarily replaced.
  function createScreenSegment({ fabric, canvas, objects, background = false, offscreen = false }) {
    const installed = installers.get(fabric?.Path?.prototype), registered = installed?.canvases.get(canvas);
    if (!registered || canvas._renderObjects !== registered.renderObjects || canvas.clipPath || canvas.overlayImage || canvas.overlayColor)
      throw new Error('Screen segments require the unchanged registered canvas painter.');
    const view = screenView(canvas);
    if (![view.width, view.height].every(value => Number.isInteger(value) && value > 0)
        || view.width * view.height > 16 * 1024 * 1024) throw new Error('Screen segment exceeds its 64 MiB surface limit.');
    if (offscreen && typeof globalThis.OffscreenCanvas !== 'function') throw new Error('Cooperative screen painting requires OffscreenCanvas.');
    const allowed = screenMembership(canvas, objects), element = offscreen
      ? new globalThis.OffscreenCanvas(view.width, view.height) : fabric.util.createCanvasElement();
    element.width = view.width; element.height = view.height;
    const context = element.getContext('2d', { willReadFrequently: false }), matrix = canvas.contextContainer.getTransform(), previous = installed.screen;
    const base = [matrix.a, matrix.b, matrix.c, matrix.d, matrix.e, matrix.f];
    let plane;
    try {
      applyScreenBase(context, base, view.retina);
      installed.screen = { canvas, context, allowed };
      if (background) canvas._renderBackground(context);
      context.save();
      try {
        context.transform(...canvas.viewportTransform);
        const matrix = context.getTransform(); plane = [matrix.a, matrix.b, matrix.c, matrix.d, matrix.e, matrix.f];
        canvas._renderObjects(context, canvas.getObjects());
      } finally { context.restore(); }
      if (!sameScreenView(canvas, view)) throw new Error('Screen view changed during layer preparation.');
    } catch (error) { element.width = 0; element.height = 0; throw error; }
    finally { installed.screen = previous; }
    const token = Object.freeze({ width: view.width, height: view.height, bytes: view.width * view.height * 4,
      plane: Object.freeze(plane.slice()) });
    screenSegments.set(token, { canvas, element, view, plane, base });
    return token;
  }

  function releaseScreenSegment(token) {
    const segment = screenSegments.get(token);
    if (!segment) return;
    screenSegments.delete(token); segment.element.width = 0; segment.element.height = 0;
  }

  // Cooperative native painting into one persistent surface. Only direct,
  // uncached transparency-free groups may split; native leaf caches remain
  // indivisible. All clipping and native drawing order stay in Fabric.
  async function prepareCompleteScreenFrame({ fabric, canvas, admit, current, yieldToUi, signal }) {
    const installed = installers.get(fabric?.Path?.prototype), registered = installed?.canvases.get(canvas);
    const audit = { allocationMs: 0, maxPaintBatchMs: 0, maxAdmissionBatchMs: 0, paintBatches: 0 };
    let token, closed = false;
    const close = () => {
      closed = true;
      if (registered?.prepared?.close === close) registered.prepared = null;
      releaseScreenSegment(token); signal?.removeEventListener('abort', close);
    };
    signal?.addEventListener('abort', close, { once: true });
    const view = screenView(canvas), leaves = [], nodes = [], seen = new Set(), pending = canvas.getObjects().slice().reverse();
    const check = () => {
      if (closed || signal?.aborted || canvas.disposed || canvas.destroyed || current() !== true
          || !sameScreenView(canvas, view) || !passivePaintCallbacks(canvas)) throw new Error('Complete screen preparation changed.');
    };
    const checkpoint = async () => { await yieldToUi(); check(); };
    try {
      if (!registered || registered.reuse || registered.prepared || typeof admit !== 'function') throw new Error('Complete screen preparation is unavailable.');
      if (typeof canvas.backgroundColor !== 'string' || !/^#[0-9a-f]{6}$/i.test(canvas.backgroundColor)
          || canvas.backgroundImage != null || canvas.clipPath || canvas.overlayImage || canvas.overlayColor)
        throw new Error('Complete screen preparation requires an opaque solid background.');
      await checkpoint();
      let started = performance.now();
      while (pending.length) {
        const object = pending.pop();
        if (!object || seen.has(object) || seen.size >= 10000 || !admit(object, false)) throw new Error('Unsupported complete screen painter.');
        seen.add(object); nodes.push(object);
        const children = object._objects;
        if (children?.length) {
          if (object.objectCaching !== false || object.needsItsOwnCache() || object.opacity !== 1 || object.backgroundColor)
            throw new Error('Isolated groups require ordinary complete painting.');
          for (let i = children.length - 1; i >= 0; i--) pending.push(children[i]);
        } else leaves.push(object);
        if (performance.now() - started >= 8) { await checkpoint(); started = performance.now(); }
      }
      const allocatingAt = performance.now();
      token = createScreenSegment({ fabric, canvas, objects: [], background: true, offscreen: true });
      audit.allocationMs = performance.now() - allocatingAt;
      const segment = screenSegments.get(token), context = segment.element.getContext('2d');
      started = performance.now();
      for (let index = 0; index < leaves.length; index += 32) {
        const paintingAt = performance.now();
        check();
        const allowed = screenMembership(canvas, leaves.slice(index, index + 32)), previous = installed.screen;
        context.save();
        try {
          // Replay the original base+viewport operations. A getTransform()
          // readback can quantize an internal native matrix; feeding it back
          // changes edge coverage for literal native fallback painters.
          applyScreenBase(context, segment.base, segment.view.retina); context.transform(...segment.view.viewport);
          installed.screen = { canvas, context, allowed };
          canvas._renderObjects(context, canvas.getObjects());
        } finally { installed.screen = previous; context.restore(); }
        audit.maxPaintBatchMs = Math.max(audit.maxPaintBatchMs, performance.now() - paintingAt); audit.paintBatches++;
        if (performance.now() - started >= 8) { await checkpoint(); started = performance.now(); }
      }
      check();
      started = performance.now();
      for (let index = 0; index < nodes.length; index += 32) {
        const checkingAt = performance.now();
        if (!nodes.slice(index, index + 32).every(object => admit(object, false))) throw new Error('Complete screen painters changed before issue.');
        audit.maxAdmissionBatchMs = Math.max(audit.maxAdmissionBatchMs, performance.now() - checkingAt);
        if (performance.now() - started >= 8) { await checkpoint(); started = performance.now(); }
      }
      check();
      return Object.freeze({ close, install() {
        check();
        if (registered.reuse || registered.prepared) throw new Error('A screen presentation is already active.');
        registered.prepared = { segment, current, close };
      }, diagnostics: () => ({ closed, leaves: leaves.length, bytes: token.bytes, ...audit }) });
    } catch (error) { close(); throw error; }
  }

  // The caller owns semantic invalidation. Its synchronous guard must affirm
  // unchanged static artwork before every frame; false, throw, or a view change
  // closes reuse and completes this frame with the ordinary complete painter.
  function beginScreenFrameReuse({ fabric, canvas, prefix, suffix, objects, guard }) {
    const installed = installers.get(fabric?.Path?.prototype), registered = installed?.canvases.get(canvas);
    const before = screenSegments.get(prefix), after = screenSegments.get(suffix);
    if (!registered || registered.reuse || canvas._renderObjects !== registered.renderObjects || typeof guard !== 'function'
        || before?.canvas !== canvas || after?.canvas !== canvas || !sameScreenView(canvas, before.view) || !sameScreenView(canvas, after.view)
        || before.plane.some((value, index) => !Object.is(value, after.plane[index]))) throw new Error('Screen frame layers are not current.');
    const allowed = screenMembership(canvas, objects), audit = { frames: 0, fallbacks: 0, closed: false };
    const finish = release => {
      if (registered.reuse?.audit === audit) registered.reuse = null;
      if (release) { releaseScreenSegment(prefix); releaseScreenSegment(suffix); }
      audit.closed = true;
      return { ...audit };
    };
    const stop = () => finish(true), pause = () => finish(false);
    registered.reuse = { prefix: before, suffix: after, allowed, guard, audit, stop };
    return Object.freeze({ stop, pause, diagnostics: () => ({ ...audit }) });
  }

  function setWorld(installed, context, plane, object, relatives = []) {
    const multiply = installed.fabric.util.multiplyTransformMatrices;
    let world = object.calcTransformMatrix();
    for (const relative of relatives) world = multiply(world, relative);
    const matrix = multiply(plane, world);
    if (!matrix.every(Number.isFinite) || matrix[0] * matrix[3] - matrix[1] * matrix[2] === 0) return false;
    context.setTransform(...matrix);
    return true;
  }

  // Called only inside the existing native relative-clip builder's saved
  // transform scope. The builder, path, fill rule and clip intersection stay
  // native. Unknown owners/contexts continue their literal native transforms.
  function setImportedClipTransform({ fabric, object, context, matrices }) {
    const installed = installers.get(fabric?.Path?.prototype), plane = installed?.plane;
    const registered = plane && installed.canvases.get(plane.canvas);
    if (plane?.context !== context || !installed.imported(object, registered, plane.canvas)) return false;
    return setWorld(installed, context, plane.matrix, object, matrices);
  }

  // Explicit SCREEN-only detached preparation. It uses the same admission,
  // current Fabric world matrix and multiplication as the first live paint.
  // No main-plane scope or Canvas state survives this synchronous call.
  function setScreenPreparationTransform({ fabric, canvas, context, object, plane }) {
    const installed = installers.get(fabric?.Path?.prototype), registered = installed?.canvases.get(canvas);
    if (!installed?.imported(object, registered, null)) return false;
    return setWorld(installed, context, plane, object);
  }

  return { install, setImportedClipTransform, setScreenPreparationTransform,
    shouldPaintScreenObject, createScreenSegment, releaseScreenSegment, beginScreenFrameReuse, captureScreenState, preparePointScreenPreview, createFontFaceGuard, registerPassivePaintObserver, prepareCompleteScreenFrame };
});
