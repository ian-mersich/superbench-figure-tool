/* Keep native uncached path painting in one Canvas scene plane during isolation.
 * Geometry, layout, style, caches and the actual Path painter remain Fabric's.
 */
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.FigureStudioNativePathSceneTransform = api;
})(typeof globalThis === 'object' ? globalThis : this, function () {
  'use strict';
  const installers = new WeakMap();

  function install({ fabric, canvas, isIsolated, isNativePath }) {
    if (!fabric?.Path?.prototype || !fabric?.Group || typeof canvas?._renderObjects !== 'function'
        || typeof isIsolated !== 'function' || isNativePath != null && typeof isNativePath !== 'function') throw new Error('Native path scene painting requires its Fabric canvas.');
    const prototype = fabric.Path.prototype;
    let installed = installers.get(prototype);
    if (!installed) {
      const nativeTransform = prototype.transform;
      installed = { plane: null, canvases: new WeakMap(), nativePathRender: prototype._render };
      const unsupported = object => object.clipPath || object.mask || object.shadow || object.filters?.length
        || object.figureStudioAppearanceStack || object.figureStudioAppearanceMeta
        || object.globalCompositeOperation && object.globalCompositeOperation !== 'source-over';
      prototype.transform = function sceneTransform(context) {
        const plane = installed.plane, registered = plane && installed.canvases.get(plane.canvas);
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
      };
      installers.set(prototype, installed);
    }
    if (installed.canvases.has(canvas)) return;
    installed.canvases.set(canvas, { isIsolated, isNativePath });
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

  return { install };
});
