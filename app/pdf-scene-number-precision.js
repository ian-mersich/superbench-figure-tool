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
  // Only factory-created or privately parsed fresh records enter this authority. Neither
  // data shape/prototype nor a caller flag can admit a boxed object or Proxy.
  const issuedPlainJsonRecords = new WeakSet();
  function createPlainJsonRecord() {
    const record = {};
    issuedPlainJsonRecords.add(record);
    return record;
  }
  // The normal application bootstrap supplies the native intrinsic data
  // properties. Initial accessors/drift opt out without invoking those getters.
  // This is an intrinsic-bootstrap assumption, not a source-text attestation.
  const jsonDescriptor = Object.getOwnPropertyDescriptor(globalThis, 'JSON');
  const initialJson = jsonDescriptor && Object.hasOwn(jsonDescriptor, 'value') ? jsonDescriptor.value : null;
  const ownDescriptor = Object.getOwnPropertyDescriptor, ownKeys = Object.keys, isArray = Array.isArray;
  const hasOwn = Object.hasOwn, apply = Reflect.apply, weakSetAdd = WeakSet.prototype.add;
  const parseDescriptor = initialJson && (typeof initialJson === 'object' || typeof initialJson === 'function') ? ownDescriptor(initialJson, 'parse') : null;
  const stringifyDescriptor = initialJson && (typeof initialJson === 'object' || typeof initialJson === 'function') ? ownDescriptor(initialJson, 'stringify') : null;
  const initialParse = parseDescriptor && hasOwn(parseDescriptor, 'value') && typeof parseDescriptor.value === 'function' ? parseDescriptor.value : null;
  const initialStringify = stringifyDescriptor && hasOwn(stringifyDescriptor, 'value') && typeof stringifyDescriptor.value === 'function' ? stringifyDescriptor.value : null;
  function parseOwnedJsonText(text) {
    // Undefined retains the native SyntaxError for stringify(undefined). No
    // caller objects, revivers, parser callbacks or brand flags are accepted.
    if (typeof text !== 'string' && text !== undefined) throw new TypeError('Owned JSON parsing requires primitive JSON text.');
    const value = apply(initialParse, initialJson, [text]);
    let pending = { value, next: null };
    while (pending) {
      const current = pending.value; pending = pending.next;
      if (!current || typeof current !== 'object') continue;
      if (!isArray(current)) apply(weakSetAdd, issuedPlainJsonRecords, [current]);
      const keys = ownKeys(current);
      // Native parsing has no reviver, so no result escapes before this walk.
      // Indexed own-key reads and a linked stack avoid mutable iterators/methods.
      for (let i = keys.length - 1; i >= 0; i--) {
        const key = keys[i];
        if (!hasOwn(current, key)) throw new Error('A fresh JSON parse lost an own property.');
        const child = current[key];
        if (child && typeof child === 'object') pending = { value: child, next: pending };
      }
    }
    return value;
  }
  function ownedJsonParserForCurrentIntrinsics() {
    const current = ownDescriptor(globalThis, 'JSON');
    if (!initialParse || !initialStringify || !current || !hasOwn(current, 'value') || current.value !== initialJson) return null;
    const parse = ownDescriptor(initialJson, 'parse'), stringify = ownDescriptor(initialJson, 'stringify');
    return parse && stringify && hasOwn(parse, 'value') && hasOwn(stringify, 'value')
      && parse.value === initialParse && stringify.value === initialStringify ? parseOwnedJsonText : null;
  }
  function defaultYield() { return new Promise(resolve => setTimeout(resolve, 0)); }
  async function runBatches(steps, {yieldEvery = 128, yieldToUi = defaultYield, maxSliceMs = 8, signal} = {}) {
    if (!Number.isSafeInteger(yieldEvery) || yieldEvery < 1 || typeof yieldToUi !== 'function'
        || !Number.isFinite(maxSliceMs) || maxSliceMs <= 0) throw new Error('PDF capture requires bounded batches and a yield callback.');
    let count = 0, started = performance.now();
    while (true) {
      if (signal?.aborted) throw signal.reason || new Error('PDF capture was cancelled.');
      const step = steps.next();
      if (step.done) return step.value;
      if (++count % yieldEvery === 0 || performance.now() - started >= maxSliceMs) {
        await yieldToUi();
        started = performance.now();
      }
    }
  }

  // The detached result has JSON.stringify/parse semantics, including toJSON,
  // the replacer's holder/key, sparse arrays, omitted values and signed zero.
  // Repeated references are copied independently; live state is never adopted.
  function prepareJsonValue(holder, key, replacer) {
    let value = holder[key];
    if (value !== null && ['object', 'function', 'bigint'].includes(typeof value)) {
      const toJSON = value.toJSON;
      if (typeof toJSON === 'function') value = Reflect.apply(toJSON, value, [key]);
    }
    if (replacer) value = replacer.call(holder, key, value);
    if (value && typeof value === 'object' && !Array.isArray(value) && !issuedPlainJsonRecords.has(value)) {
      let boxed, boolean;
      // Intrinsic slot checks never read user tags or proxy has/get traps.
      // IsArray is also intrinsic; arrays cannot carry boxed primitive slots.
      try { Number.prototype.valueOf.call(value); boxed = 'number'; } catch (_) {}
      if (!boxed) try { String.prototype.valueOf.call(value); boxed = 'string'; } catch (_) {}
      if (!boxed) try { boolean = Boolean.prototype.valueOf.call(value); } catch (_) {}
      if (!boxed && boolean === undefined) {
        let bigint = false;
        try { BigInt.prototype.valueOf.call(value); bigint = true; } catch (_) {}
        if (bigint) throw new TypeError('Do not know how to serialize a BigInt');
      }
      if (boxed === 'number') value = +value;
      else if (boxed === 'string') value = String(value);
      else if (boolean !== undefined) value = boolean;
    }
    if (typeof value === 'bigint') throw new TypeError('Do not know how to serialize a BigInt');
    if (typeof value === 'number') return Number.isFinite(value) ? (Object.is(value, -0) ? 0 : value) : null;
    if (value === null || typeof value === 'string' || typeof value === 'boolean') return value;
    if (!value || typeof value !== 'object') return undefined;
    return value;
  }
  function* jsonCloneSteps(value, replacer, active) {
    if (value === null || typeof value !== 'object') return value;
    // Keep the same depth-first reads, assignments and yield boundaries while
    // avoiding recursive generator delegation for every JSON property.
    function enter(item, parent, key) {
      if (active.has(item)) throw new TypeError('Converting circular structure to JSON');
      active.add(item);
      const array = Array.isArray(item), result = array ? [] : createPlainJsonRecord();
      const keys = array ? null : Object.keys(item);
      const length = array ? Math.min(Math.max(Math.floor(+item.length) || 0, 0), Number.MAX_SAFE_INTEGER) : keys.length;
      return { value: item, result, array, keys, length, index: 0, parent, key };
    }
    let frame = enter(value, null, '');
    while (true) {
      if (frame.index === frame.length) {
        active.delete(frame.value);
        const child = frame.result, key = frame.key;
        frame = frame.parent;
        if (!frame) return child;
        if (frame.array) frame.result.push(child);
        else Object.defineProperty(frame.result, key, {value: child, enumerable: true, writable: true, configurable: true});
        yield 1;
        continue;
      }
      const index = frame.index++, childKey = frame.array ? String(index) : frame.keys[index];
      const prepared = prepareJsonValue(frame.value, childKey, replacer);
      if (prepared !== null && typeof prepared === 'object') {
        frame = enter(prepared, frame, childKey);
        continue;
      }
      if (frame.array) frame.result.push(prepared === undefined ? null : prepared);
      else if (prepared !== undefined) Object.defineProperty(frame.result, childKey, {value: prepared, enumerable: true, writable: true, configurable: true});
      yield 1;
    }
  }
  function cloneJsonAsync(value, {replacer, ...options} = {}) {
    if (replacer !== undefined && typeof replacer !== 'function') throw new Error('PDF capture requires a function JSON replacer.');
    function* capture() { return yield* jsonCloneSteps(prepareJsonValue({'': value}, '', replacer), replacer, new Set()); }
    return runBatches(capture(), options);
  }
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

  function* collectSceneScopeSteps(roots, isPdfObject = sourcePredicate) {
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
      yield 1;
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
      yield 1;
    }
    const sourceScope = new Set();
    for (const object of sources) pending.push(object);
    while (pending.length) {
      const object = pending.pop();
      if (sourceScope.has(object)) continue;
      sourceScope.add(object);
      for (const child of children.get(object) || []) pending.push(child);
      yield 1;
    }
    const objects = new Set(sourceScope);
    for (const object of sourceScope) pending.push(object);
    while (pending.length) {
      for (const parent of parents.get(pending.pop()) || []) {
        if (!objects.has(parent)) { objects.add(parent); pending.push(parent); }
      }
      yield 1;
    }
    return {objects, visited};
  }

  function collectSceneScope(roots, isPdfObject = sourcePredicate) {
    const steps = collectSceneScopeSteps(roots, isPdfObject);
    let step;
    do { step = steps.next(); } while (!step.done);
    return step.value;
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

  function underlyingSerializer(object) {
    let method = object.toObject;
    const seen = new Set();
    while (issuedWrappers.has(method) && !seen.has(method)) {
      seen.add(method);
      const record = issuedWrappers.get(method);
      if (record.object !== object) break;
      method = record.original;
    }
    return method;
  }

  async function canvasToObjectAsync(canvas, properties = [], options = {}) {
    // Keep the native Canvas envelope, background/overlay and clip ordering.
    // Its ordinary object hook issues placeholders without serializing a live
    // root. Each queued root is subsequently captured under one source scope.
    const jobs = [], facade = Object.create(canvas);
    Object.defineProperty(facade, '_toObject', {value(object, method, props) {
      const placeholder = {};
      jobs.push({object, method, props, placeholder});
      return placeholder;
    }});
    const result = canvas.toObject.call(facade, properties);
    const scope = await runBatches(collectSceneScopeSteps(jobs.map(job => job.object)), options);
    function* installSteps() { for (const object of scope.objects) { installObject(object, false); yield 1; } }
    await runBatches(installSteps(), options);
    const inScope = action => {
      const previous = serializationScope;
      serializationScope = scope;
      try { return action(); } finally { serializationScope = previous; }
    };
    function* capture(object, props, defaults, canvasRoot = false, inheritedClipPrecision = false) {
      const group = object instanceof fabric.Group;
      const audited = auditedSerializers.has(underlyingSerializer(object));
      const decomposable = audited && (!group || object.__serializeObjects === fabric.Group.prototype.__serializeObjects);
      if (!decomposable) {
        // Foreign serializers retain their actual receiver, parent and clip
        // identity. This bounded native fallback cannot yield in its subtree.
        const previousDefaults = object.includeDefaultValues;
        let record;
        try {
          if (!canvasRoot) object.includeDefaultValues = defaults;
          record = inScope(() => canvasRoot ? canvas._toObject(object, 'toObject', props) : object.toObject(props));
          if (inheritedClipPrecision) preserveClipNumbers(record, object);
        } finally { object.includeDefaultValues = previousDefaults; }
        yield 1;
        return record;
      }
      const copy = Object.create(object);
      // Preserve native own-property tests in registered/custom serializers
      // (including a retained text declaration currently outside admission).
      for (const key of Reflect.ownKeys(object)) {
        if (['includeDefaultValues', 'parent', '_objects', 'clipPath'].includes(key)) continue;
        Object.defineProperty(copy, key, Object.getOwnPropertyDescriptor(object, key));
      }
      Object.defineProperty(copy, 'includeDefaultValues', {value: defaults, writable: true, configurable: true});
      // Native ActiveSelection realization may mark a parent dirty through
      // Object._set. Its geometry belongs to this read-only root facade alone.
      Object.defineProperty(copy, 'parent', {value: undefined, writable: true, configurable: true});
      let childCall = null, clipCall = null;
      if (group && decomposable) {
        Object.defineProperty(copy, '_objects', {value: [], writable: true, configurable: true});
        Object.defineProperty(copy, '__serializeObjects', {value(method, childProperties) {
          childCall = {method, properties: childProperties, defaults: this.includeDefaultValues};
          return [];
        }});
      }
      const clip = object.clipPath;
      if (decomposable && clip && !clip.excludeFromExport) {
        const clipFacade = Object.create(clip);
        Object.defineProperty(clipFacade, 'toObject', {value(clipProperties) { clipCall = {properties: clipProperties}; return {}; }});
        Object.defineProperty(copy, 'clipPath', {value: clipFacade, writable: true, configurable: true});
      }
      const record = inScope(() => canvasRoot
        ? canvas._toObject(copy, 'toObject', props)
        : copy.toObject(props));
      if (inheritedClipPrecision) {
        preserveNumbers(record, copy, auditedSerializers.has(underlyingSerializer(object)));
        if (!decomposable && record.clipPath && clip) preserveClipNumbers(record.clipPath, clip);
      }
      yield 1;
      if (childCall) {
        if (childCall.method !== 'toObject' || !Array.isArray(record.objects)) throw new Error('PDF capture requires the native group object serializer.');
        const records = [];
        for (const child of object.getObjects().filter(child => !child.excludeFromExport)) {
          records.push(yield* capture(child, childCall.properties, childCall.defaults, false, inheritedClipPrecision));
        }
        record.objects = records;
      }
      if (clipCall) record.clipPath = yield* capture(clip, clipCall.properties, clip.includeDefaultValues,
        false, inheritedClipPrecision || scope.objects.has(object));
      return record;
    }
    function* captures() {
      for (const job of jobs) {
        if (job.method !== 'toObject') throw new Error('PDF capture requires the native canvas object serializer.');
        const record = yield* capture(job.object, job.props,
          canvas.includeDefaultValues === false ? false : job.object.includeDefaultValues, true);
        Object.defineProperties(job.placeholder, Object.getOwnPropertyDescriptors(record));
      }
      return result;
    }
    return runBatches(captures(), options);
  }
  return Object.freeze({installScene, installObject, precisionObjectsForScene, canvasToObjectAsync});
  }
  return Object.freeze({createInstaller, cloneJsonAsync, createPlainJsonRecord, ownedJsonParserForCurrentIntrinsics});
});
