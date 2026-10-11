const MIN_ZOOM = 0.04;
const MAX_ZOOM = 8;
const SCENE_CUSTOM_PROPERTIES = ["figureSceneId", "figureSceneKind", "figureSceneData"];

function finite(value, fallback = 0) {
  const number = Number(value);
  return Number.isFinite(number) ? number : fallback;
}

function eventIds(objects) {
  return [...new Set((objects || []).map((object) => String(object?.figureSceneId || "")).filter(Boolean))];
}

function matrixPoint(point, transform) {
  return {
    x: transform[0] * point.x + transform[2] * point.y + transform[4],
    y: transform[1] * point.x + transform[3] * point.y + transform[5]
  };
}

function descriptors(frame) {
  return [
    ...(frame.regions || []).map((item) => ({ ...item, kind: "region" })),
    ...(frame.edges || []).map((item) => ({ ...item, kind: "edge" })),
    ...(frame.decorations || []).map((item) => ({ ...item, kind: "decoration" })),
    ...(frame.nodes || []).map((item) => ({ ...item, kind: "node" }))
  ];
}

function setSvgRootAttribute(attributes, name, value) {
  const pattern = new RegExp(`\\s${name}\\s*=\\s*(?:"[^"]*"|'[^']*'|[^\\s>]+)`, "i");
  const replacement = ` ${name}="${String(value).replaceAll("&", "&amp;").replaceAll('"', "&quot;")}"`;
  return pattern.test(attributes)
    ? attributes.replace(pattern, replacement)
    : `${attributes}${replacement}`;
}

function svgAttributes(source = "") {
  const attributes = new Map();
  for (const match of source.matchAll(/([^\s=]+)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+))/g)) {
    attributes.set(match[1], decodeSvgAttribute(match[2] ?? match[3] ?? match[4] ?? ""));
  }
  return attributes;
}

function decodeSvgAttribute(value) {
  return String(value).replace(/&(#x[\da-f]+|#\d+|amp|quot|apos|lt|gt);/gi, (entity, code) => {
    if (code[0] !== "#") return ({ amp: "&", quot: '"', apos: "'", lt: "<", gt: ">" })[code.toLowerCase()] || entity;
    const number = code[1].toLowerCase() === "x" ? Number.parseInt(code.slice(2), 16) : Number.parseInt(code.slice(1), 10);
    try { return String.fromCodePoint(number); } catch (_error) { return entity; }
  });
}

function setSvgAttribute(attributes, name, value) {
  attributes.set(name, String(value));
}

function serializeSvgAttributes(attributes) {
  return [...attributes].map(([name, value]) => ` ${name}="${String(value).replaceAll("&", "&amp;").replaceAll('"', "&quot;")}"`).join("");
}

function firstSvgNumber(value) {
  const scalar = String(value ?? "").trim();
  if (!/^[+-]?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][+-]?\d+)?$/.test(scalar)) return null;
  const number = Number(scalar);
  return Number.isFinite(number) ? number : null;
}

function preservePositionedTspans(svg) {
  return svg.replace(/<text\b([^>]*)>([\s\S]*?)<\/text\s*>/gi, (whole, textSourceAttributes, content) => {
    const spans = [...content.matchAll(/<tspan\b([^>]*)>([\s\S]*?)<\/tspan\s*>/gi)];
    if (!spans.length || !spans.some((span) => /\s(?:x|y|dx|dy)\s*=/i.test(span[1]))) return whole;
    const residual = content.replace(/<tspan\b[^>]*>[\s\S]*?<\/tspan\s*>/gi, "").trim();
    if (residual) return whole;

    const base = svgAttributes(textSourceAttributes);
    const positionsAreScalars = [base, ...spans.map((span) => svgAttributes(span[1]))].every((attributes) =>
      ["x", "y", "dx", "dy"].every((name) => !attributes.has(name) || firstSvgNumber(attributes.get(name)) != null));
    if (!positionsAreScalars) return whole;
    let currentX = firstSvgNumber(base.get("x")) ?? 0;
    let currentY = firstSvgNumber(base.get("y")) ?? 0;
    return spans.map((span, index) => {
      const line = svgAttributes(span[1]);
      const x = firstSvgNumber(line.get("x"));
      const y = firstSvgNumber(line.get("y"));
      const dx = firstSvgNumber(line.get("dx"));
      const dy = firstSvgNumber(line.get("dy"));
      if (x != null) currentX = x;
      if (dx != null) currentX += dx;
      if (y != null) currentY = y;
      if (dy != null) currentY += dy;

      const merged = new Map(base);
      for (const [name, value] of line) {
        if (!["x", "y", "dx", "dy"].includes(name)) merged.set(name, value);
      }
      if (index > 0 && merged.has("id")) merged.set("id", `${merged.get("id")}-line-${index + 1}`);
      setSvgAttribute(merged, "x", currentX);
      setSvgAttribute(merged, "y", currentY);
      return `<text${serializeSvgAttributes(merged)}>${span[2]}</text>`;
    }).join("");
  });
}

function normalizeSceneSvg(descriptor, bounds = {}) {
  // SVG title/description children are accessibility and tooltip metadata. Some
  // native vector importers paint them as text, so keep their semantic source in
  // descriptor.data and remove them from the visual fragment.
  const svg = preservePositionedTspans(String(descriptor.svg || "")
    .replace(/<(title|desc)\b[^>]*>[\s\S]*?<\/\1\s*>/gi, ""));
  const root = svg.match(/(<svg\b)([^>]*)(>)/i);
  if (!root) throw new TypeError(`Scene fragment "${descriptor.id}" must have an SVG root.`);
  let attributes = root[2];
  const width = descriptor.kind === "node"
    ? Math.max(1, finite(descriptor.width, 1))
    : Math.max(1, finite(bounds.width, 1));
  const height = descriptor.kind === "node"
    ? Math.max(1, finite(descriptor.height, 1))
    : Math.max(1, finite(bounds.height, 1));

  // Static frame fragments carry world-coordinate path data under a full-frame
  // viewBox. Fabric's SVG loader maps that viewBox to its implicit SVG viewport
  // (300 × 150 when width/height are absent), moving and scaling the artwork.
  // Removing the viewBox keeps those path coordinates in scene space; explicit
  // dimensions prevent Fabric's default viewport from scaling them.
  if (descriptor.kind !== "node") {
    attributes = attributes.replace(/\s+viewBox\s*=\s*(?:"[^"]*"|'[^']*'|[^\s>]+)/i, "");
  }
  attributes = setSvgRootAttribute(attributes, "width", `${width}px`);
  attributes = setSvgRootAttribute(attributes, "height", `${height}px`);
  return svg.replace(root[0], `${root[1]}${attributes}${root[3]}`);
}

function objectFromSvg(fabric, descriptor, bounds) {
  if (!String(descriptor.svg || "").trim()) return Promise.resolve(null);
  const normalizedSvg = normalizeSceneSvg(descriptor, bounds);
  return Promise.resolve(fabric.loadSVGFromString(normalizedSvg)).then((loaded) => {
    const objects = Array.isArray(loaded) ? loaded[0] : loaded?.objects;
    const options = Array.isArray(loaded) ? loaded[1] : loaded?.options;
    if (!Array.isArray(objects) || !objects.length) return null;
    if (objects.length === 1) return objects[0];
    if (typeof fabric.util?.groupSVGElements !== "function") {
      throw new Error("Fabric cannot group the native objects in this scene fragment.");
    }
    return fabric.util.groupSVGElements(objects, options || {});
  });
}

function setObject(object, values) {
  if (typeof object.set === "function") object.set(values);
  else Object.assign(object, values);
}

function nodeCenter(object) {
  // Fabric 7's getXY() reports the object's scene-plane position, including
  // its ActiveSelection transform. Nodes use center origins in this host.
  if (typeof object.getXY === "function") return object.getXY();
  if (typeof object.getCenterPoint === "function") return object.getCenterPoint();
  return { x: finite(object.left), y: finite(object.top) };
}

/**
 * Create a small Fabric-backed host for renderer-neutral vector scene frames.
 * It owns canvas interaction and artwork objects; the caller owns scene meaning
 * and responds to movement by producing a new frame.
 */
export function createVectorSceneHost(options = {}) {
  const { container, fabric, frame: initialFrame = {}, readOnly = false } = options;
  if (!container?.ownerDocument || typeof container.appendChild !== "function") {
    throw new TypeError("createVectorSceneHost requires a DOM container.");
  }
  if (!fabric?.Canvas || typeof fabric.loadSVGFromString !== "function") {
    throw new TypeError("createVectorSceneHost requires the Figure Tool Fabric namespace.");
  }

  const documentRef = container.ownerDocument;
  const windowRef = documentRef.defaultView || globalThis;
  const canvasElement = documentRef.createElement("canvas");
  canvasElement.className = "figure-vector-scene-canvas";
  canvasElement.setAttribute("aria-label", "Interactive vector scene");
  canvasElement.tabIndex = 0;
  canvasElement.style.display = "block";
  canvasElement.style.width = "100%";
  canvasElement.style.height = "100%";
  container.appendChild(canvasElement);

  const canvas = new fabric.Canvas(canvasElement, {
    selection: !readOnly,
    preserveObjectStacking: true,
    renderOnAddRemove: false,
    enableRetinaScaling: true,
    uniformScaling: true
  });
  const nodeObjects = new Map();
  const staticObjects = new Map();
  const descriptorById = new Map();
  const callback = (name, ...args) => {
    try { options[name]?.(...args); }
    catch (error) { console.error(`Vector scene host callback ${name} failed`, error); }
  };

  let frame = initialFrame;
  let generation = 0;
  let destroyed = false;
  let spaceDown = false;
  let panGesture = null;
  let pointerDownNode = null;
  let pointerDownPositions = null;
  let moveGesture = null;
  let selectedIds = [];
  let suppressSelectionCallback = false;
  let resizeObserver = null;

  const width = () => Math.max(1, finite(container.clientWidth, container.getBoundingClientRect?.().width || 1));
  const height = () => Math.max(1, finite(container.clientHeight, container.getBoundingClientRect?.().height || 1));

  function assignDescriptor(object, descriptor, { preservePosition = false } = {}) {
    object.figureSceneId = String(descriptor.id);
    object.figureSceneKind = descriptor.kind;
    object.figureSceneData = descriptor.data == null ? null : structuredCloneSafe(descriptor.data);
    object.figureSceneSource = descriptor;
    object.selectable = !readOnly && descriptor.kind === "node";
    object.evented = descriptor.kind === "node" && !readOnly;
    object.hasControls = false;
    object.hasBorders = descriptor.kind === "node";
    object.lockScalingX = true;
    object.lockScalingY = true;
    object.lockRotation = true;
    object.objectCaching = false;
    if (descriptor.kind === "node" && !preservePosition) {
      setObject(object, {
        originX: "center",
        originY: "center",
        left: finite(descriptor.x),
        top: finite(descriptor.y)
      });
    }
    object.setCoords?.();
  }

  function structuredCloneSafe(value) {
    if (value == null || typeof value !== "object") return value;
    if (typeof structuredClone === "function") {
      try { return structuredClone(value); } catch (_error) { /* use JSON-safe fallback */ }
    }
    return JSON.parse(JSON.stringify(value));
  }

  function activeNodeObjects() {
    return (canvas.getActiveObjects?.() || []).filter((object) => object.figureSceneKind === "node");
  }

  function getPositions(objects = activeNodeObjects()) {
    return new Map(objects.map((object) => {
      const center = nodeCenter(object);
      return [String(object.figureSceneId), { x: finite(center.x), y: finite(center.y) }];
    }));
  }

  function syncSelection() {
    selectedIds = eventIds(activeNodeObjects());
    if (!suppressSelectionCallback) callback("onSelect", [...selectedIds]);
  }

  function beginMoveIfNeeded() {
    if (readOnly || moveGesture || !pointerDownNode) return;
    const moving = activeNodeObjects();
    if (!moving.some((object) => object.figureSceneId === pointerDownNode)) return;
    const positions = pointerDownPositions && moveTargetsMatch(moving, pointerDownPositions)
      ? pointerDownPositions
      : getPositions(moving);
    moveGesture = {
      ids: [...positions.keys()],
      start: new Map([...positions].map(([id, point]) => [id, { ...point }]))
    };
    callback("onMoveStart", [...moveGesture.ids]);
  }

  function pointInObject(object, point) {
    if (!object || !Number.isFinite(point?.x) || !Number.isFinite(point?.y)) return false;
    try {
      if (typeof object.containsPoint === "function") return object.containsPoint(point);
      const corners = object.getCoords?.() || [];
      if (corners.length < 3) return false;
      let inside = false;
      for (let i = 0, j = corners.length - 1; i < corners.length; j = i++) {
        const a = corners[i], b = corners[j];
        const crosses = (a.y > point.y) !== (b.y > point.y)
          && point.x < ((b.x - a.x) * (point.y - a.y)) / (b.y - a.y) + a.x;
        if (crosses) inside = !inside;
      }
      return inside;
    } catch (_error) { return false; }
  }

  function nodeFromMouseDown(event) {
    const target = event?.target;
    if (target?.figureSceneKind === "node") return target;
    const subTargets = Array.isArray(event?.subTargets) ? event.subTargets : [];
    for (let index = subTargets.length - 1; index >= 0; index--) {
      if (subTargets[index]?.figureSceneKind === "node") return subTargets[index];
    }
    const point = event?.scenePoint || event?.absolutePointer || event?.pointer;
    if (Number.isFinite(point?.x) && Number.isFinite(point?.y)) {
      const activeNodes = activeNodeObjects();
      for (let index = activeNodes.length - 1; index >= 0; index--) {
        if (pointInObject(activeNodes[index], point)) return activeNodes[index];
      }
    }
    return null;
  }

  function onObjectMoving(event) {
    beginMoveIfNeeded();
    if (!moveGesture) return;
    callback("onMove", Object.fromEntries(getPositions(activeNodeObjects())));
  }

  function finishMove(cancel = false) {
    if (!moveGesture) return false;
    if (cancel) {
      const selected = activeNodeObjects();
      canvas.discardActiveObject?.();
      for (const object of nodeObjects.values()) {
        const point = moveGesture.start.get(String(object.figureSceneId));
        if (point) {
          setObject(object, { left: point.x, top: point.y });
          object.setCoords?.();
        }
      }
      if (selected.length === 1) canvas.setActiveObject?.(selected[0]);
      else if (selected.length > 1 && fabric.ActiveSelection) {
        canvas.setActiveObject?.(new fabric.ActiveSelection(selected, { canvas }));
      }
      canvas.requestRenderAll?.();
      callback("onMoveCancel");
    } else {
      const positions = Object.fromEntries(getPositions(activeNodeObjects()));
      moveGesture = null;
      pointerDownNode = null;
      pointerDownPositions = null;
      callback("onMove", positions);
      callback("onMoveEnd");
      queueMicrotask(() => {
        if (!destroyed) render(frame).catch((error) => console.error("Vector scene host could not reconcile the completed move", error));
      });
      return true;
    }
    moveGesture = null;
    pointerDownNode = null;
    pointerDownPositions = null;
    return true;
  }

  function onMouseDown(event) {
    const target = nodeFromMouseDown(event);
    pointerDownNode = target ? String(target.figureSceneId) : null;
    const selected = activeNodeObjects();
    pointerDownPositions = getPositions(selected.some((object) => object.figureSceneId === pointerDownNode)
      ? selected : (pointerDownNode ? [target] : []));
  }

  function moveTargetsMatch(objects, positions) {
    return objects.length > 0 && objects.every((object) => positions.has(String(object.figureSceneId)));
  }

  function onMouseUp() {
    finishMove(false);
  }

  function onSelectionChanged() { syncSelection(); }

  function onKeyDown(event) {
    if (event.code === "Space" && !event.repeat && !isTypingTarget(event.target)) {
      spaceDown = true;
      event.preventDefault();
    }
    if (event.key === "Escape" && moveGesture) {
      event.preventDefault();
      finishMove(true);
    }
  }

  function onKeyUp(event) {
    if (event.code === "Space") spaceDown = false;
  }

  function isTypingTarget(target) {
    return Boolean(target?.isContentEditable || ["INPUT", "TEXTAREA", "SELECT"].includes(target?.tagName));
  }

  function onPointerDown(event) {
    if (event.button !== 1 && !(spaceDown && event.button === 0)) return;
    event.preventDefault();
    event.stopPropagation?.();
    panGesture = { pointerId: event.pointerId, x: event.clientX, y: event.clientY };
    container.setPointerCapture?.(event.pointerId);
  }

  function onPointerMove(event) {
    if (!panGesture || (panGesture.pointerId != null && event.pointerId !== panGesture.pointerId)) return;
    event.stopPropagation?.();
    const transform = [...(canvas.viewportTransform || [1, 0, 0, 1, 0, 0])];
    transform[4] += event.clientX - panGesture.x;
    transform[5] += event.clientY - panGesture.y;
    panGesture = { ...panGesture, x: event.clientX, y: event.clientY };
    canvas.setViewportTransform(transform);
    canvas.requestRenderAll?.();
  }

  function onPointerUp(event) {
    if (panGesture && (panGesture.pointerId == null || event.pointerId === panGesture.pointerId)) {
      event.stopPropagation?.();
      panGesture = null;
    }
  }

  function onWheel(event) {
    if (!event.ctrlKey && !event.metaKey) return;
    event.preventDefault();
    const rect = container.getBoundingClientRect();
    const current = finite(canvas.getZoom?.(), canvas.viewportTransform?.[0] || 1);
    const next = Math.max(MIN_ZOOM, Math.min(MAX_ZOOM, current * Math.exp(-finite(event.deltaY) * 0.002)));
    const point = new fabric.Point(event.clientX - rect.left, event.clientY - rect.top);
    canvas.zoomToPoint(point, next);
    canvas.requestRenderAll?.();
  }

  async function render(nextFrame = frame) {
    if (destroyed) throw new Error("Vector scene host has been destroyed.");
    if (!nextFrame || !Array.isArray(nextFrame.nodes) || !Array.isArray(nextFrame.edges)) {
      throw new TypeError("A vector scene frame with node and edge arrays is required.");
    }
    frame = nextFrame;
    const renderGeneration = ++generation;
    const nextDescriptors = descriptors(nextFrame);
    const preservedMoveIds = new Set(moveGesture?.ids || []);
    const parsed = await Promise.all(nextDescriptors.map(async (descriptor) => {
      const id = String(descriptor.id || "");
      if (!id) throw new TypeError("Every vector scene descriptor requires an id.");
      const existing = descriptor.kind === "node" ? nodeObjects.get(id) : staticObjects.get(`${descriptor.kind}:${id}`);
      if (existing && existing.figureSceneSource?.svg === descriptor.svg) return { descriptor, object: existing };
      if (descriptor.kind === "node" && preservedMoveIds.has(id) && existing) return { descriptor, object: existing, preserve: true };
      return { descriptor, object: await objectFromSvg(fabric, descriptor, nextFrame.bounds) };
    }));
    if (destroyed || renderGeneration !== generation) return host;

    const nextNodeIds = new Set(nextDescriptors.filter((item) => item.kind === "node").map((item) => String(item.id)));
    const nextStaticKeys = new Set(nextDescriptors.filter((item) => item.kind !== "node").map((item) => `${item.kind}:${item.id}`));
    const nextObjects = new Set(parsed.map((entry) => entry.object).filter(Boolean));
    const keepSelected = new Set(selectedIds);
    if (!moveGesture) canvas.discardActiveObject?.();

    for (const [id, object] of nodeObjects) {
      if (!nextNodeIds.has(id) || !nextObjects.has(object)) canvas.remove(object);
    }
    for (const [key, object] of staticObjects) {
      if (!nextStaticKeys.has(key) || !nextObjects.has(object)) canvas.remove(object);
    }

    nodeObjects.clear();
    staticObjects.clear();
    descriptorById.clear();
    for (const entry of parsed) {
      const { descriptor, object } = entry;
      if (!object) continue;
      assignDescriptor(object, descriptor, {
        preservePosition: descriptor.kind === "node" && preservedMoveIds.has(String(descriptor.id))
      });
      descriptorById.set(String(descriptor.id), descriptor);
      if (descriptor.kind === "node") nodeObjects.set(String(descriptor.id), object);
      else staticObjects.set(`${descriptor.kind}:${descriptor.id}`, object);
      if (!canvas.getObjects?.().includes(object)) canvas.add(object);
    }
    if (!moveGesture && typeof canvas.moveObjectTo === "function") {
      parsed.forEach((entry, index) => {
        if (entry.object) canvas.moveObjectTo(entry.object, index);
      });
    }

    if (!moveGesture && keepSelected.size) {
      const selected = [...keepSelected].map((id) => nodeObjects.get(id)).filter(Boolean);
      if (selected.length === 1) canvas.setActiveObject?.(selected[0]);
      else if (selected.length > 1 && fabric.ActiveSelection) {
        canvas.setActiveObject?.(new fabric.ActiveSelection(selected, { canvas }));
      }
    }
    canvas.requestRenderAll?.();
    return host;
  }

  function fit() {
    const bounds = frame.bounds || {};
    let minX = finite(bounds.minX);
    let minY = finite(bounds.minY);
    let maxX = minX + Math.max(1, finite(bounds.width, 1));
    let maxY = minY + Math.max(1, finite(bounds.height, 1));
    // Frame bounds describe the source viewport, which can omit stroke/text
    // expansion or nodes placed just beyond that viewport. Fabric 7 getCoords
    // returns each object's scene-plane corners, independent of the current
    // zoom and viewport transform; include them so Fit contains whole cards.
    for (const object of canvas.getObjects?.() || []) {
      let corners = [];
      try { corners = object.getCoords?.() || []; } catch (_error) { /* fall back to source bounds */ }
      for (const point of corners) {
        const x = Number(point?.x);
        const y = Number(point?.y);
        if (!Number.isFinite(x) || !Number.isFinite(y)) continue;
        minX = Math.min(minX, x);
        minY = Math.min(minY, y);
        maxX = Math.max(maxX, x);
        maxY = Math.max(maxY, y);
      }
    }
    for (const node of frame.nodes || []) {
      const x = finite(node.x);
      const y = finite(node.y);
      const halfWidth = Math.max(0, finite(node.width)) / 2;
      const halfHeight = Math.max(0, finite(node.height)) / 2;
      minX = Math.min(minX, x - halfWidth);
      minY = Math.min(minY, y - halfHeight);
      maxX = Math.max(maxX, x + halfWidth);
      maxY = Math.max(maxY, y + halfHeight);
    }
    const sceneWidth = Math.max(1, maxX - minX);
    const sceneHeight = Math.max(1, maxY - minY);
    const padding = 24;
    const zoom = Math.max(MIN_ZOOM, Math.min(MAX_ZOOM,
      Math.min((width() - padding * 2) / sceneWidth, (height() - padding * 2) / sceneHeight)));
    const offsetX = (width() - sceneWidth * zoom) / 2 - minX * zoom;
    const offsetY = (height() - sceneHeight * zoom) / 2 - minY * zoom;
    canvas.setViewportTransform([zoom, 0, 0, zoom, offsetX, offsetY]);
    canvas.requestRenderAll?.();
    return getViewport();
  }

  function getViewport() {
    const transform = canvas.viewportTransform || [1, 0, 0, 1, 0, 0];
    return { width: width(), height: height(), zoom: finite(transform[0], 1), panX: finite(transform[4]), panY: finite(transform[5]) };
  }

  function setViewport(view = {}) {
    const zoom = Math.max(MIN_ZOOM, Math.min(MAX_ZOOM, finite(view.zoom, 1)));
    canvas.setViewportTransform([zoom, 0, 0, zoom, finite(view.panX), finite(view.panY)]);
    canvas.requestRenderAll?.();
    return getViewport();
  }

  function setSelection(ids = []) {
    const requested = [...new Set((Array.isArray(ids) ? ids : []).map((id) => String(id)))];
    const selected = requested.map((id) => nodeObjects.get(id)).filter(Boolean);
    suppressSelectionCallback = true;
    try {
      canvas.discardActiveObject?.();
      if (selected.length === 1) canvas.setActiveObject?.(selected[0]);
      else if (selected.length > 1 && fabric.ActiveSelection) {
        canvas.setActiveObject?.(new fabric.ActiveSelection(selected, { canvas }));
      }
      selectedIds = eventIds(selected);
    } finally {
      suppressSelectionCallback = false;
    }
    canvas.requestRenderAll?.();
    callback("onSelect", [...selectedIds]);
    return [...selectedIds];
  }

  function getNodeScreenPoint(id) {
    const object = nodeObjects.get(String(id));
    if (!object) return null;
    const world = nodeCenter(object);
    const local = matrixPoint(world, canvas.viewportTransform || [1, 0, 0, 1, 0, 0]);
    const rect = container.getBoundingClientRect();
    return { x: rect.left + local.x, y: rect.top + local.y };
  }

  function serializeArtwork() {
    const nodeRows = [...nodeObjects.values()].map((object) => ({
      id: object.figureSceneId,
      kind: "node",
      data: structuredCloneSafe(object.figureSceneData),
      ...nodeCenter(object)
    }));
    const otherRows = [...staticObjects.values()].map((object) => ({
      id: object.figureSceneId,
      kind: object.figureSceneKind,
      data: structuredCloneSafe(object.figureSceneData)
    }));
    return {
      schema: "figureStudio.vectorSceneArtwork.v1",
      svg: canvas.toSVG(),
      objects: [...otherRows, ...nodeRows],
      viewport: getViewport()
    };
  }

  function onResize() {
    if (destroyed) return;
    canvas.setDimensions({ width: width(), height: height() });
    canvas.requestRenderAll?.();
  }

  canvas.on("mouse:down", onMouseDown);
  canvas.on("mouse:up", onMouseUp);
  canvas.on("object:moving", onObjectMoving);
  canvas.on("selection:created", onSelectionChanged);
  canvas.on("selection:updated", onSelectionChanged);
  canvas.on("selection:cleared", onSelectionChanged);
  container.addEventListener("pointerdown", onPointerDown, true);
  container.addEventListener("pointermove", onPointerMove, true);
  container.addEventListener("pointerup", onPointerUp, true);
  container.addEventListener("pointercancel", onPointerUp, true);
  container.addEventListener("wheel", onWheel, { passive: false });
  documentRef.addEventListener("keydown", onKeyDown);
  documentRef.addEventListener("keyup", onKeyUp);
  if (typeof windowRef.ResizeObserver === "function") {
    resizeObserver = new windowRef.ResizeObserver(onResize);
    resizeObserver.observe(container);
  } else windowRef.addEventListener?.("resize", onResize);

  const host = {
    render,
    fit,
    getViewport,
    setViewport,
    setSelection,
    cancelMove() { return finishMove(true); },
    getNodeScreenPoint,
    destroy() {
      if (destroyed) return;
      destroyed = true;
      generation += 1;
      finishMove(true);
      resizeObserver?.disconnect();
      if (!resizeObserver) windowRef.removeEventListener?.("resize", onResize);
      container.removeEventListener("pointerdown", onPointerDown, true);
      container.removeEventListener("pointermove", onPointerMove, true);
      container.removeEventListener("pointerup", onPointerUp, true);
      container.removeEventListener("pointercancel", onPointerUp, true);
      container.removeEventListener("wheel", onWheel, { passive: false });
      documentRef.removeEventListener("keydown", onKeyDown);
      documentRef.removeEventListener("keyup", onKeyUp);
      canvas.off?.("mouse:down", onMouseDown);
      canvas.off?.("mouse:up", onMouseUp);
      canvas.off?.("object:moving", onObjectMoving);
      canvas.off?.("selection:created", onSelectionChanged);
      canvas.off?.("selection:updated", onSelectionChanged);
      canvas.off?.("selection:cleared", onSelectionChanged);
      canvas.dispose?.();
      canvasElement.remove?.();
      nodeObjects.clear();
      staticObjects.clear();
      descriptorById.clear();
    },
    serializeArtwork
  };
  host.ready = render(initialFrame);
  return host;
}

export { SCENE_CUSTOM_PROPERTIES };
