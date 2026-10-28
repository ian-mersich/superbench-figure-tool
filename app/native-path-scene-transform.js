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

  function install({ fabric, canvas, isIsolated, isNativePath, importedPaintKind }) {
    if (!fabric?.Path?.prototype || !fabric?.Group || typeof canvas?._renderObjects !== 'function'
        || typeof isIsolated !== 'function' || isNativePath != null && typeof isNativePath !== 'function'
        || importedPaintKind != null && typeof importedPaintKind !== 'function') throw new Error('Native path scene painting requires its Fabric canvas.');
    const prototype = fabric.Path.prototype;
    let installed = installers.get(prototype);
    if (!installed) {
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
    installed.canvases.set(canvas, { isIsolated, isNativePath, importedPaintKind });
    const nativeRenderObjects = canvas._renderObjects;
    canvas._renderObjects = function (context, objects) {
      const previous = installed.plane, matrix = context.getTransform();
      // Fabric has already applied the actual viewport and retina transform.
      // Only this fixed main paint context can use the complete scene matrix;
      // caches, exports and temporary staging contexts retain native transforms.
      installed.plane = context === this.contextContainer
        ? { canvas: this, context, matrix: [matrix.a, matrix.b, matrix.c, matrix.d, matrix.e, matrix.f] } : null;
      try { return nativeRenderObjects.call(this, context, objects); }
      finally { installed.plane = previous; }
    };
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

  return { install, setImportedClipTransform, setScreenPreparationTransform };
});
