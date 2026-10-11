(function (root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  root.FigureStudioPdfHistoryNodeStore = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  const SCHEMA = "figureStudio.runtimePdfHistory.v1";
  const REF_KEY = "$figureStudioPdfHistoryNode";
  const PREFIX = `{"schema":"${SCHEMA}"`;
  const own = (value, key) => Object.prototype.hasOwnProperty.call(value, key);
  const isObject = (value) => value && typeof value === "object" && !Array.isArray(value);
  const isRef = (value) => isObject(value) && Object.keys(value).length === 1 && own(value, REF_KEY) && Number.isSafeInteger(value[REF_KEY]) && value[REF_KEY] > 0;
  const ref = (id) => ({ [REF_KEY]: id });
  const defaultYield = () => new Promise((resolve) => setTimeout(resolve, 0));
  const encoder = typeof TextEncoder !== "undefined" ? new TextEncoder() : null;
  const byteLength = (text) => encoder ? encoder.encode(text).byteLength : textMetrics(text).bytes;
  let sessionCounter = 0;

  function textMetrics(text) {
    let bytes = 0, hashA = 0xdeadbeef, hashB = 0x41c6ce57;
    for (let index = 0; index < text.length; index++) {
      const code = text.charCodeAt(index);
      hashA = Math.imul(hashA ^ code, 2654435761);
      hashB = Math.imul(hashB ^ code, 1597334677);
      if (code < 128) bytes++;
      else if (code < 2048) bytes += 2;
      else if (code >= 0xd800 && code <= 0xdbff && text.charCodeAt(index + 1) >= 0xdc00 && text.charCodeAt(index + 1) <= 0xdfff) {
        bytes += 4;
        // Hash both UTF-16 code units while counting this UTF-8 pair once.
        const tail = text.charCodeAt(++index);
        hashA = Math.imul(hashA ^ tail, 2654435761);
        hashB = Math.imul(hashB ^ tail, 1597334677);
      } else bytes += 3;
    }
    hashA = Math.imul(hashA ^ (hashA >>> 16), 2246822507) ^ Math.imul(hashB ^ (hashB >>> 13), 3266489909);
    hashB = Math.imul(hashB ^ (hashB >>> 16), 2246822507) ^ Math.imul(hashA ^ (hashA >>> 13), 3266489909);
    return { bytes, hash: `${text.length}:${(hashB >>> 0).toString(36)}${(hashA >>> 0).toString(36)}`, approximateStringHeapBytes: text.length * 2 };
  }

  function defaultIsPdfNode(value) {
    if (!isObject(value) || typeof value.type !== "string") return false;
    const meta = value.importMeta || {};
    return Boolean(value.pdfTextSource || value.pdfNativeRectClip || value.nativePdfSourceObjectId || meta.nativePdfSourceObjectId || meta.native_pdf_source_object_id || /^pdf-/.test(String(meta.importMode || meta.import_mode || "")));
  }

  function abortIfNeeded(signal) {
    if (signal?.aborted) {
      const error = new Error("PDF history encoding was cancelled.");
      error.name = "AbortError";
      throw error;
    }
  }

  class Store {
    constructor({ isPdfNode = defaultIsPdfNode, minPayloadChars = 512, hashString } = {}) {
      if (typeof isPdfNode !== "function" || !Number.isSafeInteger(minPayloadChars) || minPayloadChars < 128 || (hashString != null && typeof hashString !== "function")) throw new Error("Invalid PDF history store options.");
      Object.defineProperty(this, "sessionId", { value: globalThis.crypto?.randomUUID?.() || `${Date.now().toString(36)}-${++sessionCounter}` });
      this._isPdfNode = isPdfNode;
      this._minPayloadChars = minPayloadChars;
      this._hashString = hashString;
      this._nextId = 1;
      this._nodes = new Map();
      this._index = new Map();
      this._snapshots = new Map();
      this._pins = new Set();
      this._builder = null;
      this._immutable = new WeakSet();
      this._memo = new WeakMap();
      this._keyBytes = new Map();
    }

    get nodeCount() { return this._nodes.size; }
    isCompact(snapshot) { return typeof snapshot === "string" && snapshot.startsWith(PREFIX); }

    _envelope(snapshot) {
      const value = JSON.parse(snapshot);
      if (!this.isCompact(snapshot)) return null;
      if (value.schema !== SCHEMA || value.session !== this.sessionId || !own(value, "state")) throw new Error("This PDF history snapshot belongs to another runtime store.");
      return value;
    }

    _references(value, output = new Set()) {
      const pending = [value];
      while (pending.length) {
        const item = pending.pop();
        if (!item || typeof item !== "object") continue;
        if (isRef(item)) output.add(item[REF_KEY]);
        else for (const key of Object.keys(item)) pending.push(item[key]);
      }
      return output;
    }

    _snapshotInfo(snapshot) {
      if (!this.isCompact(snapshot)) return { bytes: byteLength(snapshot), approximateStringHeapBytes: snapshot.length * 2, refs: new Set() };
      let info = this._snapshots.get(snapshot);
      if (!info) {
        const envelope = this._envelope(snapshot);
        info = { ...textMetrics(snapshot), refs: this._references(envelope.state) };
        this._snapshots.set(snapshot, info);
      }
      return info;
    }

    _begin(snapshot, options) {
      if (this._builder) throw new Error("A PDF history encoding is already pending; queue or cancel it before starting another.");
      if (typeof snapshot !== "string") throw new Error("PDF history encoding requires the existing serialized JSON snapshot.");
      if (this.isCompact(snapshot)) throw new Error("Expand a PDF history snapshot before encoding its current canonical state.");
      abortIfNeeded(options.signal);
      const parsed = JSON.parse(snapshot);
      const builder = { snapshot, parsed, staged: new Map(), index: new Map(), existing: new Set(), rootRefs: new Set(), reserved: false, pdfNodeCount: 0, payloadCount: 0, reusedCount: 0, stageBytes: 0, stageHeapBytes: 0, isPdfNode: options.isPdfNode || this._isPdfNode, sourceBytes: byteLength(snapshot) };
      if (typeof builder.isPdfNode !== "function") throw new Error("PDF history selection requires a node predicate.");
      this._builder = builder;
      return builder;
    }

    _intern(value, builder, json = JSON.stringify(value)) {
      const metrics = textMetrics(json);
      const hash = this._hashString ? String(this._hashString(json)) : metrics.hash;
      for (const id of [...(this._index.get(hash) || []), ...(builder.index.get(hash) || [])]) {
        const stored = this._nodes.get(id) || builder.staged.get(id);
        // Hashes are only an index. Equality always compares the complete JSON.
        if (stored.json === json) {
          builder.reusedCount++;
          if (this._nodes.has(id)) builder.existing.add(id);
          return ref(id);
        }
      }
      const id = this._nextId++;
      const entry = Object.freeze({ id, json, hash, bytes: metrics.bytes, approximateStringHeapBytes: metrics.approximateStringHeapBytes, refs: Object.freeze([...this._references(value)]) });
      builder.staged.set(id, entry);
      builder.stageBytes += entry.bytes;
      builder.stageHeapBytes += entry.approximateStringHeapBytes;
      const bucket = builder.index.get(hash) || [];
      bucket.push(id); builder.index.set(hash, bucket);
      return ref(id);
    }

    *_walk(value, builder, inPdfScope = false, path = []) {
      if (!value || typeof value !== "object") return value;
      if (own(value, REF_KEY)) builder.reserved = true;
      const pdfNode = isObject(value) && typeof value.type === "string" && builder.isPdfNode(value, { path: [...path] });
      const scope = inPdfScope || pdfNode;
      for (const key of Object.keys(value)) {
        path.push(key);
        value[key] = yield* this._walk(value[key], builder, scope, path);
        path.pop();
      }
      if (pdfNode) {
        builder.pdfNodeCount++;
        const result = this._intern(value, builder);
        yield 1;
        return result;
      }
      if (scope) {
        const json = JSON.stringify(value);
        if (json.length >= this._minPayloadChars) {
          builder.payloadCount++;
          const result = this._intern(value, builder, json);
          yield 1;
          return result;
        }
      }
      return value;
    }

    _finish(builder, state) {
      if (!builder.pdfNodeCount || builder.reserved) return { snapshot: builder.snapshot ?? JSON.stringify(builder.sourceValue), compacted: false, reason: builder.reserved ? "reserved-source-field" : "no-pdf-nodes", sourceBytes: builder.sourceBytes, snapshotBytes: builder.sourceBytes, newNodeCount: 0, newNodeBytes: 0 };
      const snapshot = JSON.stringify({ schema: SCHEMA, session: this.sessionId, state });
      const metrics = textMetrics(snapshot), roots = this._references(state);
      // All parsing/predicate/serialization work succeeds before pooled records
      // become visible. Cancelled or failed encodes cannot leave partial nodes.
      for (const [id, entry] of builder.staged) {
        this._nodes.set(id, entry);
        const bucket = this._index.get(entry.hash) || [];
        bucket.push(id); this._index.set(entry.hash, bucket);
      }
      this._snapshots.set(snapshot, { ...metrics, refs: roots });
      for (const [value, scope, memo] of builder.memoUpdates || []) {
        const scopes = this._memo.get(value) || new Map();
        scopes.set(scope, memo); this._memo.set(value, scopes);
      }
      return { snapshot, compacted: true, sourceBytes: builder.sourceBytes, snapshotBytes: metrics.bytes, pdfNodeCount: builder.pdfNodeCount, sharedPayloadCount: builder.payloadCount, reusedCount: builder.reusedCount, newNodeCount: builder.staged.size, newNodeBytes: builder.stageBytes, newRetainedBytes: builder.stageBytes + metrics.bytes, ...(builder.memoUpdates ? { memoizedBranchHits: builder.memoHits, memoizedBranchWrites: builder.memoUpdates.length } : {}) };
    }

    compact(snapshot, options = {}) {
      const builder = this._begin(snapshot, options);
      try {
        const walker = this._walk(builder.parsed, builder);
        let result;
        do { abortIfNeeded(options.signal); result = walker.next(); } while (!result.done);
        return this._finish(builder, result.value);
      } finally { this._builder = null; }
    }

    async compactAsync(snapshot, { yieldEvery = 128, yieldToUi = defaultYield, ...options } = {}) {
      if (!Number.isSafeInteger(yieldEvery) || yieldEvery < 1 || typeof yieldToUi !== "function") throw new Error("PDF history batches require a positive size and yield callback.");
      const builder = this._begin(snapshot, options);
      try {
        const walker = this._walk(builder.parsed, builder);
        let result, count = 0;
        do {
          abortIfNeeded(options.signal);
          result = walker.next();
          if (!result.done && ++count % yieldEvery === 0) await yieldToUi();
        } while (!result.done);
        abortIfNeeded(options.signal);
        return this._finish(builder, result.value);
      } finally { this._builder = null; }
    }

    *_validateDetachedJson(value, pending, visiting = new Set(), checked = new Set()) {
      if (value === null || ["string", "boolean"].includes(typeof value) || (typeof value === "number" && Number.isFinite(value))) return;
      if (!value || typeof value !== "object") throw new Error("Immutable history requires detached canonical JSON values.");
      if (this._immutable.has(value) || checked.has(value)) return;
      if (visiting.has(value)) throw new Error("Immutable history cannot adopt cyclic values.");
      const array = Array.isArray(value), keys = Object.keys(value);
      if (array ? Object.getPrototypeOf(value) !== Array.prototype : ![Object.prototype, null].includes(Object.getPrototypeOf(value))) throw new Error("Immutable history cannot adopt live Fabric or non-JSON objects.");
      if (Object.getOwnPropertySymbols(value).length) throw new Error("Immutable history cannot adopt symbolic fields.");
      if (Object.getOwnPropertyNames(value).some((key) => !(array && key === "length") && !Object.prototype.propertyIsEnumerable.call(value, key))) throw new Error("Immutable history requires canonical enumerable JSON fields.");
      visiting.add(value);
      if (array && (keys.length !== value.length || keys.some((key, index) => key !== String(index)))) throw new Error("Immutable history requires dense canonical JSON arrays.");
      for (const key of keys) {
        const descriptor = Object.getOwnPropertyDescriptor(value, key);
        if (!descriptor || !own(descriptor, "value")) throw new Error("Immutable history cannot adopt getters or setters.");
        yield* this._validateDetachedJson(descriptor.value, pending, visiting, checked);
      }
      visiting.delete(value); checked.add(value); pending.push(value);
      yield 1;
    }

    _freezeValidated(pending, value) {
      for (const item of pending) { Object.freeze(item); this._immutable.add(item); }
      return value;
    }

    freezeDetachedJson(value) {
      // Ownership transfer for detached JSON only. Never call this on live
      // Fabric objects or mutable app state. Validate everything before freezing
      // any newly adopted branch; already registered immutable branches are O(1).
      const pending = [], walker = this._validateDetachedJson(value, pending);
      while (!walker.next().done) { /* Validate before the ownership transfer. */ }
      return this._freezeValidated(pending, value);
    }

    async freezeDetachedJsonAsync(value, { yieldEvery = 128, yieldToUi = defaultYield, signal } = {}) {
      if (!Number.isSafeInteger(yieldEvery) || yieldEvery < 1 || typeof yieldToUi !== "function") throw new Error("Immutable history batches require a positive size and yield callback.");
      const pending = [], walker = this._validateDetachedJson(value, pending);
      let count = 0, result;
      do {
        abortIfNeeded(signal); result = walker.next();
        if (!result.done && ++count % yieldEvery === 0) await yieldToUi();
      } while (!result.done);
      abortIfNeeded(signal);
      return this._freezeValidated(pending, value);
    }

    _keyByteLength(key) {
      let bytes = this._keyBytes.get(key);
      if (bytes === undefined) {
        bytes = byteLength(JSON.stringify(key));
        // Property names repeat heavily in Fabric JSON. Bound this convenience
        // cache independently from the exact history pool.
        if (this._keyBytes.size < 2048) this._keyBytes.set(key, bytes);
      }
      return bytes;
    }

    *_walkImmutable(value, builder, inPdfScope = false) {
      if (!value || typeof value !== "object") {
        const json = JSON.stringify(value);
        return { encoded: value, sourceBytes: typeof value === "string" ? byteLength(json) : json.length, pdfNodes: 0, payloads: 0 };
      }
      const memo = this._memo.get(value)?.get(inPdfScope);
      if (memo && memo.refs.every((id) => this._nodes.has(id))) {
        memo.refs.forEach((id) => builder.existing.add(id));
        builder.memoHits++;
        return memo;
      }
      if (own(value, REF_KEY)) builder.reserved = true;
      const pdfNode = isObject(value) && typeof value.type === "string" && defaultIsPdfNode(value);
      const scope = inPdfScope || pdfNode, array = Array.isArray(value), encoded = array ? [] : Object.create(null);
      let sourceBytes = 2, pdfNodes = pdfNode ? 1 : 0, payloads = 0, count = 0;
      for (const key of Object.keys(value)) {
        const child = yield* this._walkImmutable(value[key], builder, scope);
        encoded[key] = child.encoded;
        sourceBytes += child.sourceBytes + (count++ ? 1 : 0) + (array ? 0 : this._keyByteLength(key) + 1);
        pdfNodes += child.pdfNodes; payloads += child.payloads;
      }
      let result = encoded, payload = false;
      if (pdfNode) result = this._intern(encoded, builder);
      else if (scope) {
        const json = JSON.stringify(encoded);
        if (json.length >= this._minPayloadChars) { result = this._intern(encoded, builder, json); payloads++; payload = true; }
      }
      Object.freeze(result);
      const entry = Object.freeze({ encoded: result, sourceBytes, pdfNodes, payloads, refs: Object.freeze([...this._references(result)]) });
      // Small ordinary fields need no second stored representation. Memoize
      // canonical PDF nodes, pooled fields, and their changed outer containers.
      if (pdfNode || payload || pdfNodes) builder.memoUpdates.push([value, inPdfScope, entry]);
      yield 1;
      return entry;
    }

    compactImmutable(value, { replacer, ...options } = {}) {
      // Arbitrary JSON replacers/toJSON/getters can be context-dependent. Keep
      // their complete standard serialization semantics rather than memoizing
      // an output that might change on the next call. Artifact placeholders can
      // be prepared once before adopting the detached immutable JSON tree.
      if (replacer !== undefined || !value || typeof value !== "object" || !this._immutable.has(value) || this._isPdfNode !== defaultIsPdfNode || options.isPdfNode) {
        const result = this.compact(JSON.stringify(value, replacer), options);
        return { ...result, memoizedBranchHits: 0, memoized: false, memoFallback: replacer !== undefined ? "standard-replacer-semantics" : "unregistered-or-contextual-state" };
      }
      if (this._builder) throw new Error("A PDF history encoding is already pending; queue or cancel it before starting another.");
      abortIfNeeded(options.signal);
      const builder = { sourceValue: value, snapshot: null, staged: new Map(), index: new Map(), existing: new Set(), reserved: false, pdfNodeCount: 0, payloadCount: 0, reusedCount: 0, stageBytes: 0, stageHeapBytes: 0, sourceBytes: 0, memoUpdates: [], memoHits: 0 };
      this._builder = builder;
      try {
        const walker = this._walkImmutable(value, builder);
        let step;
        do { abortIfNeeded(options.signal); step = walker.next(); } while (!step.done);
        const result = step.value;
        builder.sourceBytes = result.sourceBytes; builder.pdfNodeCount = result.pdfNodes; builder.payloadCount = result.payloads;
        abortIfNeeded(options.signal);
        return { ...this._finish(builder, result.encoded), memoized: true };
      } finally { this._builder = null; }
    }

    async compactImmutableAsync(value, { yieldEvery = 128, yieldToUi = defaultYield, replacer, ...options } = {}) {
      if (!Number.isSafeInteger(yieldEvery) || yieldEvery < 1 || typeof yieldToUi !== "function") throw new Error("Immutable history batches require a positive size and yield callback.");
      if (replacer !== undefined || !value || typeof value !== "object" || !this._immutable.has(value) || this._isPdfNode !== defaultIsPdfNode || options.isPdfNode) {
        const result = await this.compactAsync(JSON.stringify(value, replacer), { yieldEvery, yieldToUi, ...options });
        return { ...result, memoizedBranchHits: 0, memoized: false, memoFallback: replacer !== undefined ? "standard-replacer-semantics" : "unregistered-or-contextual-state" };
      }
      if (this._builder) throw new Error("A PDF history encoding is already pending; queue or cancel it before starting another.");
      abortIfNeeded(options.signal);
      const builder = { sourceValue: value, snapshot: null, staged: new Map(), index: new Map(), existing: new Set(), reserved: false, pdfNodeCount: 0, payloadCount: 0, reusedCount: 0, stageBytes: 0, stageHeapBytes: 0, sourceBytes: 0, memoUpdates: [], memoHits: 0 };
      this._builder = builder;
      try {
        const walker = this._walkImmutable(value, builder);
        let step, count = 0;
        do {
          abortIfNeeded(options.signal); step = walker.next();
          if (!step.done && ++count % yieldEvery === 0) await yieldToUi();
        } while (!step.done);
        builder.sourceBytes = step.value.sourceBytes; builder.pdfNodeCount = step.value.pdfNodes; builder.payloadCount = step.value.payloads;
        abortIfNeeded(options.signal);
        return { ...this._finish(builder, step.value.encoded), memoized: true };
      } finally { this._builder = null; }
    }

    parse(snapshot) {
      const value = JSON.parse(snapshot);
      if (!this.isCompact(snapshot)) return value;
      if (value.schema !== SCHEMA || value.session !== this.sessionId || !own(value, "state")) throw new Error("This PDF history snapshot belongs to another runtime store.");
      const visiting = new Set();
      const expand = (item) => {
        if (!item || typeof item !== "object") return item;
        if (isRef(item)) {
          const id = item[REF_KEY], entry = this._nodes.get(id);
          if (!entry) throw new Error(`PDF history node ${id} is unavailable; the snapshot cannot be restored.`);
          if (visiting.has(id)) throw new Error("The PDF history reference graph contains a cycle.");
          visiting.add(id);
          const result = expand(JSON.parse(entry.json));
          visiting.delete(id);
          return result;
        }
        for (const key of Object.keys(item)) item[key] = expand(item[key]);
        return item;
      };
      // A fresh parse for each occurrence prevents Fabric/artifact hydration or
      // editor normalization from mutating pooled records or another history step.
      return expand(value.state);
    }

    expand(snapshot) { return JSON.stringify(this.parse(snapshot)); }

    pin(snapshots) {
      const token = { snapshots: [...snapshots] };
      this._reachable(token.snapshots, false); // Validate before adding a pin.
      this._pins.add(token);
      let released = false;
      return () => { if (!released) { released = true; this._pins.delete(token); } };
    }

    _reachable(snapshots, includePins) {
      const roots = [...snapshots];
      if (includePins) for (const pin of this._pins) roots.push(...pin.snapshots);
      const snapshotSet = new Set(roots), ids = new Set(), pending = [];
      let snapshotBytes = 0, snapshotHeapBytes = 0;
      for (const snapshot of snapshotSet) {
        if (typeof snapshot !== "string") throw new Error("History reachability requires serialized snapshot strings.");
        const info = this._snapshotInfo(snapshot);
        snapshotBytes += info.bytes; snapshotHeapBytes += info.approximateStringHeapBytes;
        pending.push(...info.refs);
      }
      // A yielding encoder temporarily pins reused existing nodes. Its new
      // strings are reported separately until the encode atomically commits.
      if (includePins && this._builder) pending.push(...this._builder.existing);
      let nodeBytes = 0, nodeHeapBytes = 0;
      while (pending.length) {
        const id = pending.pop();
        if (ids.has(id)) continue;
        const entry = this._nodes.get(id);
        if (!entry) throw new Error(`PDF history node ${id} is unavailable; reachable history cannot be pruned.`);
        ids.add(id); nodeBytes += entry.bytes; nodeHeapBytes += entry.approximateStringHeapBytes;
        pending.push(...entry.refs);
      }
      return { ids, snapshotSet, snapshotBytes, nodeBytes, nodeHeapBytes, snapshotHeapBytes };
    }

    measure(snapshots, { includePins = true } = {}) {
      const reachable = this._reachable(snapshots, includePins);
      const stagedNodeBytes = includePins ? this._builder?.stageBytes || 0 : 0;
      const stagedHeapBytes = includePins ? this._builder?.stageHeapBytes || 0 : 0;
      return { snapshotBytes: reachable.snapshotBytes, nodeBytes: reachable.nodeBytes, stagedNodeBytes, reachableBytes: reachable.snapshotBytes + reachable.nodeBytes + stagedNodeBytes, uniqueSnapshotCount: reachable.snapshotSet.size, reachableNodeCount: reachable.ids.size, pooledNodeCount: this._nodes.size, pinCount: this._pins.size, approximateStringHeapBytes: reachable.snapshotHeapBytes + reachable.nodeHeapBytes + stagedHeapBytes, accounting: "Unique reachable UTF-8 serialized strings; 2-byte-per-code-unit string estimate reported separately. Map/array/object overhead and external artifact data are not measured heap bytes." };
    }

    collect(snapshots) {
      const reachable = this._reachable(snapshots, true);
      let removedNodeCount = 0, removedNodeBytes = 0;
      // Validate the entire live graph above before deleting anything. All tab
      // stacks and rollback pins must remain roots throughout a stack transition.
      for (const [id, entry] of this._nodes) if (!reachable.ids.has(id)) {
        this._nodes.delete(id); removedNodeCount++; removedNodeBytes += entry.bytes;
        const bucket = this._index.get(entry.hash).filter((candidate) => candidate !== id);
        if (bucket.length) this._index.set(entry.hash, bucket); else this._index.delete(entry.hash);
      }
      for (const snapshot of this._snapshots.keys()) if (!reachable.snapshotSet.has(snapshot)) this._snapshots.delete(snapshot);
      return { removedNodeCount, removedNodeBytes, ...this.measure(snapshots) };
    }

    planPrune(stack, { maxSteps, maxBytes } = {}) {
      if (!Number.isSafeInteger(maxSteps) || maxSteps < 1 || !Number.isFinite(maxBytes) || maxBytes < 0) throw new Error("History pruning needs existing positive step and byte limits.");
      const next = [...stack];
      let pruned = 0;
      while (next.length > maxSteps) { next.shift(); pruned++; }
      // Match the existing plain-history byte policy when no runtime PDF
      // references are present. PDF plans count the shared reachable pool once.
      const bytes = () => next.some((snapshot) => this.isCompact(snapshot)) ? this.measure(next, { includePins: false }).reachableBytes : next.reduce((sum, snapshot) => sum + byteLength(snapshot), 0);
      let totalBytes = bytes();
      while (next.length > 1 && totalBytes > maxBytes) { next.shift(); pruned++; totalBytes = bytes(); }
      return { stack: next, pruned, totalBytes, latestExceedsBudget: next.length <= 1 && totalBytes > maxBytes };
    }

    prepareMove(undoStack, redoStack, direction) {
      if (!["undo", "redo"].includes(direction)) throw new Error("History movement must be undo or redo.");
      if ((direction === "undo" && undoStack.length < 2) || (direction === "redo" && !redoStack.length)) return { status: "unavailable" };
      const nextUndo = [...undoStack], nextRedo = [...redoStack], currentSnapshot = nextUndo.at(-1);
      const targetSnapshot = direction === "undo" ? (nextRedo.push(nextUndo.pop()), nextUndo.at(-1)) : nextRedo.pop();
      if (direction === "redo") nextUndo.push(targetSnapshot);
      const release = this.pin([...undoStack, ...redoStack, ...nextUndo, ...nextRedo]);
      try {
        const state = this.parse(targetSnapshot), rollbackState = currentSnapshot ? this.parse(currentSnapshot) : null;
        return { status: "ready", currentSnapshot, targetSnapshot, state, rollbackState, undoStack: Object.freeze(nextUndo), redoStack: Object.freeze(nextRedo), release };
      } catch (error) { release(); throw error; }
    }
  }

  return { SCHEMA, REF_KEY, Store, defaultIsPdfNode, textMetrics };
});
