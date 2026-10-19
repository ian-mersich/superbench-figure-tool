/* Native controls for worker-owned canonical PDF paths. */
(function (root, factory) {
  const cjs = typeof module === "object" && module.exports;
  const api = factory(
    cjs ? require("./pdf-dense-document-session.js") : root.FigureStudioPdfDenseDocumentSession,
    cjs ? require("./pdf-current-native-plane-materializer.js") : root.FigureStudioPdfCurrentNativePlaneMaterializer,
    cjs ? require("./pdf-svg-materializer.js") : root.FigureStudioPdfSvgMaterializer,
    cjs ? require("./pdf-dense-vector-replay.js") : root.FigureStudioPdfDenseVectorReplay,
    cjs ? require("../vendor/fabric/index.min.js") : root.fabric
  );
  if (cjs) module.exports = api;
  else root.FigureStudioPdfDenseNativeProxies = api;
})(typeof globalThis === "object" ? globalThis : this, function (sessions, nativePlanes, materializer, replay, bundledFabric) {
  "use strict";
  const owners = new WeakMap(), proxies = new WeakMap(), editPlans = new WeakMap(), LIMIT = 32;
  const POINT_LIMITS = Object.freeze({ commands: 4096, operands: 32768 });
  const isSession = sessions?.isSession, sessionPrototype = sessions?.DenseDocumentSession?.prototype;
  const nativeRequest = sessionPrototype?.request;
  const sessionGetters = Object.fromEntries(["revision", "frame", "operationNames"].map(key => [key, Object.getOwnPropertyDescriptor(sessionPrototype || {}, key)?.get]));
  const nativeEnterGroup = bundledFabric?.Group?.prototype.enterGroup;
  const nativeHostMethods = functions(bundledFabric?.Group?.prototype);
  const nativeHostMatrix = nativeHostMethods.get("calcOwnMatrix");
  const sessionValue = (session, key) => Reflect.apply(sessionGetters[key], session, []);
  const fillPaints = new Set(["fill", "eoFill", "fillStroke", "eoFillStroke", "closeFillStroke", "closeEOFillStroke"]);
  const strokePaints = new Set(["stroke", "closeStroke", "fillStroke", "eoFillStroke", "closeFillStroke", "closeEOFillStroke"]);
  const closePaints = new Set(["closeStroke", "closeFillStroke", "closeEOFillStroke"]);
  const evenPaints = new Set(["eoFill", "eoFillStroke", "closeEOFillStroke"]);
  const geometryCommands = { moveTo: "M", lineTo: "L", curveTo: "C", closePath: "Z" };
  const arity = { M: 2, L: 2, C: 6, Z: 0 };
  const paintKeys = ["fill", "stroke", "strokeWidth", "strokeLineCap", "strokeLineJoin", "strokeMiterLimit", "strokeDashArray", "strokeDashOffset", "fillRule", "opacity", "globalCompositeOperation", "shadow", "inverted", "absolutePositioned", "visible", "backgroundColor", "figureStudioAppearanceStack", "figureStudioAppearanceMeta", "filters", "resizeFilter"];
  const clone = value => structuredClone(value);
  const same = (a, b) => Object.is(a, b) || Boolean(a && b && typeof a === "object" && typeof b === "object"
    && Array.isArray(a) === Array.isArray(b) && ArrayBuffer.isView(a) === ArrayBuffer.isView(b)
    && (!ArrayBuffer.isView(a) || a.constructor === b.constructor)
    && Object.keys(a).length === Object.keys(b).length
    && Object.keys(a).every((key, index) => key === Object.keys(b)[index] && same(a[key], b[key])));
  const number = value => Object.is(value, -0) ? "-0" : String(value);
  const transforms = planes => planes.map(plane => "matrix(" + plane.map(number).join(" ") + ")").join(" ");
  const node = (tag, attrs = {}, children = []) => ({ tag, attrs, children });
  function fail(message) { const error = new Error(message); error.code = "PDF_DENSE_PROXY_REFUSED"; throw error; }
  function check(owner) {
    const data = owners.get(owner);
    if (!data || data.closed || !isSession(data.session)) fail("The native PDF controls are closed or foreign.");
    if (sessionValue(data.session, "revision") !== data.revision) fail("The canonical PDF revision changed; rebuild its native controls.");
    return data;
  }
  function color(row, channel) {
    const raw = !row.editedFields?.includes("style") && row.sourcePaint?.[channel];
    const components = raw ? (raw.components.length === 1 ? Array(3).fill(raw.components[0]) : raw.components).map(value => value * 255) : row.style[channel];
    return "rgb(" + components.map(number).join(",") + ")";
  }
  function documentFor(row, frame, names, revision) {
    const definitions = [], chain = row.clipChain || [];
    for (const clip of chain) {
      if (!clip.pathPlaneChains || clip.pathPlaneChains.some(planes => !same(planes, clip.transformPlanes))) fail("A clip needs its exact path-construction plane.");
      definitions.push(node("clipPath", { id: "dense-proxy-clip-" + clip.index, "clip-rule": clip.rule }, [node("path", {
        d: replay.sourcePath({ ...clip, paintOperator: "clip" }, names, { rectangleAsLines: true }), transform: transforms(clip.transformPlanes), "clip-rule": clip.rule
      })]));
    }
    if (!row.pathPlaneChains || row.pathPlaneChains.some(planes => !same(planes, row.transformPlanes))) fail("A path needs its exact construction and paint planes.");
    const style = row.style;
    let paint = node("g", { transform: transforms(row.transformPlanes) }, [node("path", {
      d: replay.sourcePath(row, names, { rectangleAsLines: true }), fill: fillPaints.has(row.paintOperator) ? color(row, "fill") : "none",
      stroke: strokePaints.has(row.paintOperator) ? color(row, "stroke") : "none", "stroke-width": number(style.lineWidth),
      "stroke-linecap": ["butt", "round", "square"][style.lineCap], "stroke-linejoin": ["miter", "round", "bevel"][style.lineJoin],
      "stroke-miterlimit": number(style.miter), "fill-rule": evenPaints.has(row.paintOperator) ? "evenodd" : "nonzero"
    })]);
    for (const clip of chain.slice().reverse()) paint = node("g", { "clip-path": "url(#dense-proxy-clip-" + clip.index + ")" }, [paint]);
    if (row.placement) {
      if (row.placement.documentRevision !== revision || !Array.isArray(row.placement.planePath) || row.placement.planePath.length > 48) fail("The authored group placement is stale or incomplete.");
      for (const scope of row.placement.planePath.slice().reverse()) {
        if (!Array.isArray(scope.matrix) || scope.matrix.length !== 6 || scope.matrix.some(value => !Number.isFinite(value))) fail("An authored group plane is invalid.");
        // Authored parent planes surround the complete source clip and paint.
        // The original leaf/clip coordinates remain in their declaring planes.
        paint = node("g", { transform: "matrix(" + scope.matrix.map(number).join(" ") + ")" }, [paint]);
      }
    }
    return node("svg", { width: number(frame.width), height: number(frame.height) }, [node("defs", {}, definitions), node("g", { transform: "matrix(" + frame.transform.map(number).join(" ") + ")" }, [paint])]);
  }
  function descriptor(object, key) { for (let current = object; current; current = Object.getPrototypeOf(current)) { const value = Object.getOwnPropertyDescriptor(current, key); if (value) return value; } }
  function dataValue(object, key) { const value = descriptor(object, key); if (value && !Object.hasOwn(value, "value")) fail("Native PDF source fields must remain data properties."); return value?.value; }
  function functions(object) {
    const result = new Map(), descriptors = new Map();
    for (let current = object; current; current = Object.getPrototypeOf(current)) for (const key of Reflect.ownKeys(current)) {
      if (!descriptors.has(key)) descriptors.set(key, Object.getOwnPropertyDescriptor(current, key));
    }
    for (const [key, value] of descriptors) {
      if (Object.hasOwn(value, "value") && typeof value.value === "function") result.set(key, value.value);
    }
    return result;
  }
  function objects(root) {
    const result = [], seen = new Set();
    const visit = object => { if (!object || seen.has(object)) return; seen.add(object); result.push(object); for (const child of dataValue(object, "_objects") || []) visit(child); visit(dataValue(object, "clipPath")); visit(dataValue(object, "mask")); };
    visit(root); return result;
  }
  function viewState(root, leaf, expected) {
    const previous = expected && new Map(expected.map(row => [row.object, row]));
    return objects(root).map(object => {
      const methods = functions(object), matrix = methods.get("calcOwnMatrix");
      const before = previous?.get(object);
      if (previous && (!before || methods.size !== before.methods.size || Array.from(before.methods).some(([key, method]) => methods.get(key) !== method))) fail("A point edit cannot change native planes, paint, or clips.");
      if (!matrix) fail("A native PDF source plane lost its actual geometry method.");
      return { object, prototype: Object.getPrototypeOf(object), methods, matrix: Reflect.apply(matrix, object, []).slice(),
        parent: dataValue(object, "parent"), group: dataValue(object, "group"), children: (dataValue(object, "_objects") || []).slice(), clipPath: dataValue(object, "clipPath"), mask: dataValue(object, "mask"),
        paint: clone(Object.fromEntries(paintKeys.map(key => [key, dataValue(object, key)]))),
        geometry: object !== leaf ? clone(Object.fromEntries(["width", "height", "rx", "ry", "radius", "startAngle", "endAngle", "points", "pathOffset"].map(key => [key, dataValue(object, key)]))) : null,
        path: object !== leaf && dataValue(object, "path") ? clone(dataValue(object, "path")) : null };
    });
  }
  function sameViewState(a, b) {
    return a.length === b.length && a.every((before, index) => {
      const after = b[index];
      return before.object === after.object && before.prototype === after.prototype && before.parent === after.parent && before.group === after.group
        && before.children.length === after.children.length && before.children.every((child, index) => child === after.children[index]) && before.clipPath === after.clipPath && before.mask === after.mask
        && before.methods.size === after.methods.size && Array.from(before.methods).every(([key, value]) => after.methods.get(key) === value)
        && same(before.matrix, after.matrix) && same(before.paint, after.paint) && same(before.geometry, after.geometry) && same(before.path, after.path);
    });
  }
  function pointMap(row, names) {
    if (row?.kind !== "path" || !Array.isArray(row.pathChunks) || !row.pathChunks.length || row.pathChunks.length > POINT_LIMITS.commands) return null;
    let commandCount = closePaints.has(row.paintOperator) ? 1 : 0, operandCount = 0;
    for (const chunk of row.pathChunks) {
      const args = chunk?.args;
      if (!Array.isArray(args) || !args[0] || !args[1] || !Number.isSafeInteger(args[0].length) || !Number.isSafeInteger(args[1].length)) return null;
      commandCount += args[0].length; operandCount += args[1].length;
      if (commandCount > POINT_LIMITS.commands || operandCount > POINT_LIMITS.operands) return null;
      for (let index = 0; index < args[1].length; index++) if (!Number.isFinite(args[1][index])) return null;
    }
    const commands = [], mappings = [];
    for (let chunkIndex = 0; chunkIndex < row.pathChunks.length; chunkIndex++) {
      const chunk = row.pathChunks[chunkIndex]; let offset = 0;
      for (const code of chunk.args[0]) {
        const command = geometryCommands[names[code]];
        if (!command) return null;
        const count = arity[command];
        commands.push([command, ...Array.from(chunk.args[1].slice(offset, offset + count))]);
        mappings.push({ chunkIndex, offset, count }); offset += count;
      }
      if (offset !== chunk.args[1].length) fail("The complete path command operands differ.");
    }
    if (closePaints.has(row.paintOperator)) { commands.push(["Z"]); mappings.push(null); }
    return { commands, mappings };
  }
  // This pure preflight only refuses unsupported views. Editing authority still
  // requires an actual private leaf and its unchanged source owner/tree below.
  function supportsPointMapping(row, names) { try { return Boolean(pointMap(row, names)); } catch { return false; } }
  function canEditPoints(object) {
    const entry = proxies.get(object);
    if (!entry || entry.leaf !== object || !entry.mapping) return false;
    try {
      const data = check(entry.owner);
      if (data.active.get(entry.row.id) !== entry || entry.mapping.commands.length > POINT_LIMITS.commands) return false;
      if (!sameViewState(viewState(entry.host || entry.root, entry.leaf, entry.state), entry.state)) return false;
      const path = dataValue(object, "path");
      if (!Array.isArray(path) || path.length !== entry.mapping.commands.length) return false;
      let operands = 0;
      for (let index = 0; index < path.length; index++) {
        const item = Object.getOwnPropertyDescriptor(path, String(index));
        if (!item || !Object.hasOwn(item, "value") || !Array.isArray(item.value)) return false;
        const command = item.value, before = entry.mapping.commands[index];
        if (command.length !== before.length) return false;
        for (let operand = 0; operand < command.length; operand++) {
          const value = Object.getOwnPropertyDescriptor(command, String(operand));
          if (!value || !Object.hasOwn(value, "value") || (operand === 0 ? value.value !== before[0] : !Number.isFinite(value.value))) return false;
        }
        operands += command.length - 1;
        if (operands > POINT_LIMITS.operands) return false;
      }
      return true;
    } catch { return false; }
  }
  class NativeProxySet {
    async acquirePath(id, { signal, yieldControl } = {}) {
      const data = check(this);
      if (data.active.has(id)) return data.active.get(id).root;
      if (data.pending.has(id) || data.active.size + data.pending.size >= LIMIT) fail("At most 32 native PDF edit controls may be active.");
      const controller = new AbortController(), cancel = () => controller.abort();
      if (signal?.aborted) controller.abort();
      else signal?.addEventListener("abort", cancel, { once: true });
      data.pending.set(id, controller); let built;
      try {
        const packet = await Reflect.apply(nativeRequest, data.session, ["read", { ids: [id] }, { signal: controller.signal }]);
        check(this);
        if (packet.revision !== data.revision || packet.result.length !== 1 || packet.result[0].id !== id || packet.result[0].kind !== "path") fail("The canonical path response is stale or incomplete.");
        const row = packet.result[0], dom = documentFor(row, data.frame, data.names, data.revision);
        built = await nativePlanes.construct(bundledFabric, materializer, { dom, runs: [] }, { signal: controller.signal, yieldControl });
        check(this);
        if (controller.signal.aborted) { const error = new Error("Native PDF control construction was cancelled."); error.name = "AbortError"; throw error; }
        const Path = materializer.registerCurrentPlanePathClass(bundledFabric);
        // Clip paths can themselves be wrapped groups. The one paint is the
        // first native path in the constructor's ordinary child tree.
        const paintLeaves = [];
        const visitPaint = object => { if (object.constructor === Path) paintLeaves.push(object); for (const child of object.getObjects?.() || []) visitPaint(child); };
        visitPaint(built.root);
        if (paintLeaves.length !== 1) fail("The native control lost its single canonical paint.");
        const leaf = paintLeaves[0], mapping = pointMap(row, data.names);
        if (mapping && !same(mapping.commands, leaf.path)) fail("Native path construction changed a source operand.");
        leaf.figureId = row.id; leaf.figureType = "path";
        const entry = { owner: this, row: clone(row), root: built.root, leaf, mapping, state: viewState(built.root, leaf) };
        data.active.set(id, entry); proxies.set(built.root, entry); proxies.set(leaf, entry);
        return built.root;
      } catch (error) { built?.root?.dispose?.(); throw error; }
      finally { data.pending.delete(id); signal?.removeEventListener("abort", cancel); }
    }
    pathObject(root) { const entry = proxies.get(root); if (!entry || entry.owner !== this) fail("Foreign native PDF control."); check(this); return entry.leaf; }
    adoptHost(root, host) {
      const data = check(this), entry = proxies.get(root);
      if (!entry || entry.owner !== this || entry.host || data.active.get(entry.row.id) !== entry) fail("Native PDF host adoption is foreign or already completed.");
      if (!sameViewState(viewState(entry.root, entry.leaf, entry.state), entry.state)) fail("Native PDF source changed before host adoption.");
      for (const [key, method] of functions(host)) {
        if (["__objectSelectionTracker", "__objectSelectionDisposer"].includes(key)) continue;
        if (nativeHostMethods.get(key) !== method) fail("Native PDF source hosts must retain their actual native methods.");
      }
      if (host?.constructor !== bundledFabric.Group || dataValue(host, "_objects")?.length !== 0
          || dataValue(host, "clipPath") || dataValue(host, "mask") || dataValue(host, "shadow") || dataValue(host, "objectCaching") !== false
          || dataValue(host, "width") !== data.frame.width || dataValue(host, "height") !== data.frame.height
          || dataValue(host, "filters")?.length || dataValue(host, "resizeFilter") || dataValue(host, "backgroundColor")
          || dataValue(host, "figureStudioAppearanceStack") || dataValue(host, "figureStudioAppearanceMeta")
          || dataValue(host, "visible") !== true || dataValue(host, "opacity") !== 1 || ![undefined, "source-over"].includes(dataValue(host, "globalCompositeOperation"))
          || !same(Reflect.apply(nativeHostMatrix, host, []), [1, 0, 0, 1, -data.frame.width / 2, -data.frame.height / 2])
          || bundledFabric.Group.prototype.enterGroup !== nativeEnterGroup) fail("Native PDF editing needs its unchanged source-frame host.");
      dataValue(host, "_objects").push(root); Reflect.apply(nativeEnterGroup, host, [root, false]);
      entry.host = host; entry.state = viewState(host, entry.leaf); return host;
    }
    snapshotPathEdit(root) {
      const data = check(this), entry = proxies.get(root);
      if (!entry || entry.owner !== this || data.active.get(entry.row.id) !== entry || !entry.mapping) fail("This native control has no qualified source point mapping.");
      const current = viewState(entry.host || entry.root, entry.leaf, entry.state);
      if (!sameViewState(current, entry.state)) fail("A point edit cannot change native planes, paint, or clips.");
      const chunks = clone(entry.row.pathChunks), path = entry.leaf.path;
      if (path.length !== entry.mapping.commands.length) fail("Point edits must retain the source command sequence.");
      for (let index = 0; index < path.length; index++) {
        const before = entry.mapping.commands[index], command = path[index], mapping = entry.mapping.mappings[index];
        if (command.length !== before.length || command[0] !== before[0] || command.slice(1).some(value => !Number.isFinite(value))) fail("Point edits must retain finite source command operands.");
        if (mapping) for (let operand = 0; operand < mapping.count; operand++) chunks[mapping.chunkIndex].args[1][mapping.offset + operand] = command[operand + 1];
      }
      const snapshot = { id: entry.row.id, pathChunks: chunks };
      editPlans.set(snapshot, { owner: this, entry, revision: data.revision, change: clone(snapshot) });
      return snapshot;
    }
    commitPathEdit(snapshot, { signal } = {}) {
      return commitPathChanges(this,[snapshot],signal);
    }
    commitPathEdits(snapshots, { signal } = {}) { return commitPathChanges(this,snapshots,signal); }
    release(id) {
      const data = owners.get(this), entry = data?.active.get(id);
      if (!entry) return false;
      data.active.delete(id); proxies.delete(entry.root); proxies.delete(entry.leaf); entry.root.dispose(); return true;
    }
    close() { const data = owners.get(this); if (!data || data.closed) return; data.closed = true; for (const controller of data.pending.values()) controller.abort(); for (const id of Array.from(data.active.keys())) this.release(id); }
    get activeCount() { return check(this).active.size; }
  }
  const nativeSnapshotPathEdit = NativeProxySet.prototype.snapshotPathEdit;
  function commitPathChanges(owner,snapshots,signal) {
    const data=check(owner);
    if(!Array.isArray(snapshots)||!snapshots.length||snapshots.length>LIMIT||new Set(snapshots).size!==snapshots.length)fail("A bounded distinct native point edit set is required.");
    const plans=snapshots.map(snapshot=>{
      const plan=editPlans.get(snapshot);
      if(!plan||plan.owner!==owner||plan.revision!==data.revision||data.active.get(plan.change.id)!==plan.entry||!same(snapshot,plan.change))fail("The native point snapshot is stale, modified, reused, or foreign.");
      const current=Reflect.apply(nativeSnapshotPathEdit,owner,[plan.entry.root]);editPlans.delete(current);
      if(!same(current,plan.change))fail("The native point view changed after its edit snapshot.");return plan;
    });
    if(new Set(plans.map(plan=>plan.change.id)).size!==plans.length)fail("Native point targets must be distinct.");
    if(signal?.aborted){const error=new Error("The native point edit was cancelled.");error.name="AbortError";throw error;}
    for(const snapshot of snapshots)editPlans.delete(snapshot);
    return Reflect.apply(nativeRequest,data.session,["edit",{changes:plans.map(plan=>plan.change)},{signal}]);
  }
  function create({ session, fabric = bundledFabric } = {}) {
    if (!isSession?.(session) || fabric !== bundledFabric || typeof nativeRequest !== "function"
        || Object.values(sessionGetters).some(getter => typeof getter !== "function")) fail("Native controls require a completed private PDF document session and the bundled native classes.");
    const names = sessionValue(session, "operationNames");
    if (!names || typeof names !== "object") fail("The document's native path operation names are unavailable.");
    const owner = new NativeProxySet();
    owners.set(owner, { session, revision: sessionValue(session, "revision"), frame: sessionValue(session, "frame"), names: clone(names), active: new Map(), pending: new Map(), closed: false });
    return owner;
  }
  return Object.freeze({ create, isProxy: object => { const entry = proxies.get(object); if (!entry) return false; try { check(entry.owner); return true; } catch { return false; } }, canEditPoints, supportsPointMapping, NativeProxySet, LIMIT, POINT_LIMITS });
});
