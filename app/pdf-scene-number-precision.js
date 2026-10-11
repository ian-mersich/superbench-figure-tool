/* Preserve the current numeric values of explicitly identified PDF objects.
 * Class/type identity, stock ActiveSelection realization, source metadata and
 * ordinary Fabric serialization stay under their existing implementations.
 */
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.FigureStudioPdfSceneNumberPrecision = api;
})(typeof globalThis === 'object' ? globalThis : this, function () {
  'use strict';
  // Constructor and editor installers may nest their own issued wrappers.
  // Only this module can register a wrapper and its actual source object.
  const issuedWrappers = new WeakMap();
  function createInstaller({fabric, additionalSerializers = []} = {}) {
  if (!fabric?.util?.toFixed || !fabric.config) throw new Error('PDF numeric preservation requires the bundled Fabric serializer.');
  const auditedSerializers = new Set(additionalSerializers);
  for (const name of ['FabricObject', 'Object', 'Group', 'Path', 'Rect', 'Circle', 'Ellipse', 'Triangle', 'Line', 'Polyline', 'Polygon', 'Image', 'Text', 'IText', 'Textbox']) {
    const serializer = fabric[name]?.prototype?.toObject;
    if (typeof serializer === 'function') auditedSerializers.add(serializer);
  }
  const installed = new WeakMap();
  const explicitlyInstalled = new WeakSet();
  let sourcePredicate = () => false;
  let serializationScope = null;
  // These are the numeric fields in the bundled Fabric Object serializer.
  // A nondefault value can round to its default before stock omission runs.
  const BASE_NUMBERS = ['left', 'top', 'width', 'height', 'strokeWidth', 'strokeDashOffset',
    'strokeMiterLimit', 'scaleX', 'scaleY', 'angle', 'opacity', 'skewX', 'skewY'];
  const TEXT_NUMBERS = ['fontSize', 'charSpacing', 'lineHeight', 'pathStartOffset'];

  function preserveNumbers(result, object, allowDefaultReconstruction) {
    if (!result || typeof result !== 'object' || Array.isArray(result)) throw new Error('A PDF object did not return its canonical serialization.');
    const fields = typeof object.text === 'string' ? [...BASE_NUMBERS, ...TEXT_NUMBERS] : BASE_NUMBERS;
    for (const key of fields) {
      const value = result[key], current = object[key];
      if (Object.hasOwn(result, key) && Number.isFinite(value) && Number.isFinite(current)
          && value === fabric.util.toFixed(current, fabric.config.NUM_FRACTION_DIGITS)) {
        Object.defineProperty(result, key, {value: current, enumerable: true, writable: true, configurable: true});
      }
    }
    if (allowDefaultReconstruction && object.includeDefaultValues === false) {
      const defaults = object.constructor.getDefaults?.() || {};
      const fields = typeof object.text === 'string' ? [...BASE_NUMBERS, ...TEXT_NUMBERS] : BASE_NUMBERS;
      for (const key of fields) {
        const current = object[key];
        if (!Object.hasOwn(result, key) && Number.isFinite(current) && Object.hasOwn(defaults, key) && current !== defaults[key]) {
          Object.defineProperty(result, key, {value: current, enumerable: true, writable: true, configurable: true});
        }
      }
    }
    return result;
  }

  function installObject(object, explicit = true) {
    if (explicit) explicitlyInstalled.add(object);
    if (installed.has(object)) {
      const expected = installed.get(object).wrapper;
      let current = object.toObject;
      const visited = new Set();
      while (current !== expected) {
        const issued = issuedWrappers.get(current);
        if (!issued || issued.object !== object || visited.has(current)) throw new Error('The PDF serializer changed after numeric preservation was installed.');
        visited.add(current);
        current = issued.original;
      }
      return false;
    }
    const original = object?.toObject;
    if (typeof original !== 'function') throw new Error('A PDF object requires its existing Fabric serializer.');
    const wrapper = function (...args) {
      // History uses a read-only facade inheriting from the live object. Its
      // numeric values are current, while source ancestry belongs to the owner.
      if (this !== object && !Object.prototype.isPrototypeOf.call(object, this)) return original.apply(this, args);
      const previousScope = serializationScope;
      try {
        if (!serializationScope || !serializationScope.visited.has(object)) {
          serializationScope = collectSceneScope([object]);
          for (const row of serializationScope.objects) installObject(row, false);
        }
        const result = original.apply(this, args);
        if (!serializationScope.objects.has(object)) return result;
        preserveNumbers(result, this, auditedSerializers.has(original));
        if (result.clipPath && this.clipPath) preserveClipNumbers(result.clipPath, this.clipPath);
        return result;
      } finally {
        serializationScope = previousScope;
      }
    };
    Object.defineProperty(object, 'toObject', {value: wrapper, configurable: true, writable: true});
    installed.set(object, {original, wrapper});
    issuedWrappers.set(wrapper, {object, original});
    return true;
  }

  function collectSceneScope(roots, isPdfObject = sourcePredicate) {
    if (typeof isPdfObject !== 'function') throw new Error('PDF numeric preservation requires an explicit source-object predicate.');
    const rootObjects = Array.from(roots || []).filter(Boolean);
    const children = new Map(), parents = new Map(), visited = new Set(), sources = [];
    const pending = [...rootObjects];
    const isSource = object => explicitlyInstalled.has(object) || Boolean(isPdfObject(object));
    // All edges are recorded once. Source containers confer precision to their
    // descendants; containing ordinary groups gain precision only themselves.
    while (pending.length) {
      const object = pending.pop();
      if (!object || visited.has(object)) continue;
      visited.add(object);
      const rows = Array.from(object.getObjects?.() || []).filter(Boolean);
      children.set(object, rows);
      if (isSource(object)) sources.push(object);
      for (const child of rows) {
        if (!parents.has(child)) parents.set(child, []);
        parents.get(child).push(object);
        pending.push(child);
      }
    }
    // A separately serialized child can still belong to an explicit PDF
    // container. An ordinary parent with a PDF sibling confers no precision.
    const ancestorSources = new Map(), parentMembers = new Map();
    for (const rootObject of rootObjects) {
      let child = rootObject;
      let parent = rootObject.parent || rootObject.group;
      const chain = [], seen = new Set();
      let inherited = false;
      while (parent && !seen.has(parent)) {
        if (parent.constructor?.type === 'ActiveSelection') break;
        if (!parentMembers.has(parent)) parentMembers.set(parent, new Set(children.get(parent) || parent.getObjects?.() || []));
        if (!parentMembers.get(parent).has(child)) break;
        if (ancestorSources.has(parent)) { inherited = ancestorSources.get(parent); break; }
        seen.add(parent); chain.push(parent);
        if (isSource(parent)) { inherited = true; break; }
        child = parent;
        parent = parent.parent || parent.group;
      }
      for (const row of chain) ancestorSources.set(row, inherited);
      if (inherited) sources.push(rootObject);
    }
    const sourceScope = new Set();
    for (const object of sources) pending.push(object);
    while (pending.length) {
      const object = pending.pop();
      if (sourceScope.has(object)) continue;
      sourceScope.add(object);
      for (const child of children.get(object) || []) pending.push(child);
    }
    const objects = new Set(sourceScope);
    for (const object of sourceScope) pending.push(object);
    while (pending.length) {
      for (const parent of parents.get(pending.pop()) || []) {
        if (!objects.has(parent)) { objects.add(parent); pending.push(parent); }
      }
    }
    return {objects, visited};
  }

  function precisionObjectsForScene(roots, {isPdfObject = sourcePredicate} = {}) {
    return collectSceneScope(roots, isPdfObject).objects;
  }

  function preserveClipNumbers(result, clip) {
    preserveNumbers(result, clip, auditedSerializers.has(installed.get(clip)?.original || clip.toObject));
    if (Array.isArray(result.objects)) {
      const children = (clip.getObjects?.() || []).filter(child => !child.excludeFromExport);
      if (children.length !== result.objects.length) throw new Error('The saved PDF clip changed its canonical child order.');
      children.forEach((child, index) => preserveClipNumbers(result.objects[index], child));
    }
    if (result.clipPath && clip.clipPath) preserveClipNumbers(result.clipPath, clip.clipPath);
  }

  function installScene(roots, {isPdfObject} = {}) {
    if (typeof isPdfObject !== 'function') throw new Error('PDF numeric preservation requires an explicit source-object predicate.');
    sourcePredicate = isPdfObject;
    const scope = collectSceneScope(roots);
    let installedCount = 0;
    for (const object of scope.objects) if (installObject(object, false)) installedCount++;
    // Shared ordinary clip instances keep their original serializers. Their
    // numbers are preserved only in this source owner's saved result.
    return {installedCount, visitedCount: scope.visited.size};
  }
  return Object.freeze({installScene, installObject, precisionObjectsForScene});
  }
  return Object.freeze({createInstaller});
});
