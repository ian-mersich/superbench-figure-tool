(function (root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  root.FigureStudioGroupObjectSelection = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";
  function rectangle(a, b) {
    return { left: Math.min(a.x, b.x), top: Math.min(a.y, b.y), width: Math.abs(b.x - a.x), height: Math.abs(b.y - a.y) };
  }
  function intersection(a, b) {
    const left = Math.max(a.left, b.left), top = Math.max(a.top, b.top);
    const right = Math.min(a.left + a.width, b.left + b.width), bottom = Math.min(a.top + a.height, b.top + b.height);
    return right >= left && bottom >= top ? { left, top, width: right - left, height: bottom - top } : null;
  }
  function collect(records, box, contained = false) {
    return records.filter(({ bounds: b }) => b && (contained
      ? b.left >= box.left && b.top >= box.top && b.left + b.width <= box.left + box.width && b.top + b.height <= box.top + box.height
      : Boolean(intersection(b, box)))).map(record => record.object);
  }
  function mergedSelection(original, hits, additive) {
    if (!additive) return hits.slice();
    const next = original.filter(object => !hits.includes(object));
    return next.concat(hits.filter(object => !original.includes(object)));
  }
  function outlines(records) {
    const rows = [];
    for (const record of records.slice().sort((a, b) => a.bounds.top - b.bounds.top || a.bounds.left - b.bounds.left)) {
      const box = record.bounds, text = typeof record.object.text === "string";
      const previous = text && rows.find(row => row.text && Math.abs(row.bounds.top - box.top) < 1e-6
        && Math.abs(row.bounds.height - box.height) < 1e-6 && box.left <= row.bounds.left + row.bounds.width + box.height * 0.35);
      if (previous) {
        const left = Math.min(previous.bounds.left, box.left), right = Math.max(previous.bounds.left + previous.bounds.width, box.left + box.width);
        previous.bounds = { ...previous.bounds, left, width: right - left }; previous.objects.push(record.object);
      } else rows.push({ bounds: { ...box }, objects: [record.object], text });
    }
    return rows;
  }
  function positions(snapshots, delta, constrain = false) {
    let { x, y } = delta;
    if (x === 0 && y === 0) return snapshots.map(entry => ({ object: entry.object, left: entry.left, top: entry.top }));
    if (constrain) {
      if (Math.abs(x) > Math.abs(y) * (1 + Math.SQRT2)) y = 0;
      else if (Math.abs(y) > Math.abs(x) * (1 + Math.SQRT2)) x = 0;
      else { const component = Math.hypot(x, y) / Math.SQRT2; x = Math.sign(x) * component; y = Math.sign(y) * component; }
    }
    return snapshots.map(entry => ({ object: entry.object,
      left: entry.left + entry.inverse[0] * x + entry.inverse[2] * y,
      top: entry.top + entry.inverse[1] * x + entry.inverse[3] * y }));
  }
  // Match ordinary object-marquee bounds while refusing unknown clip geometry.
  // Clips are not removed or baked into the model; these boxes are disposable.
  function bounds(object, fabric) {
    let box = object.getBoundingRect();
    if (![box.left, box.top, box.width, box.height].every(Number.isFinite)) return null;
    for (let current = object; current; current = current.group) {
      if (current.visible === false || current.locked || Number(current.opacity) === 0) return null;
      let host = current.calcTransformMatrix();
      for (let clip = current.clipPath; clip; clip = clip.clipPath) {
        if (clip.inverted || clip.getObjects?.().length) return null;
        const matrix = clip.absolutePositioned ? clip.calcTransformMatrix() : fabric.util.multiplyTransformMatrices(host, clip.calcOwnMatrix());
        if (Math.abs(matrix[1]) > 1e-10 || Math.abs(matrix[2]) > 1e-10) return null;
        let points;
        if (String(clip.type).toLowerCase() === "rect") {
          if (Number(clip.rx) || Number(clip.ry)) return null;
          points = [[-clip.width / 2, -clip.height / 2], [clip.width / 2, clip.height / 2]];
        } else if (Array.isArray(clip.path) && clip.path.length === 5 && clip.path[0][0] === "M"
            && clip.path.at(-1)[0] === "Z" && clip.path.slice(1, 4).every(row => row[0] === "L")) {
          points = clip.path.slice(0, 4).map(row => [row[1] - clip.pathOffset.x, row[2] - clip.pathOffset.y]);
          if (points.some(p => !p.every(Number.isFinite)) || new Set(points.map(p => p.join(","))).size !== 4
              || new Set(points.map(p => p[0])).size !== 2 || new Set(points.map(p => p[1])).size !== 2
              || points.some((p, i) => { const next = points[(i + 1) % 4]; return (p[0] === next[0]) === (p[1] === next[1]); })) return null;
        } else return null;
        const xs = points.map(p => matrix[0] * p[0] + matrix[4]), ys = points.map(p => matrix[3] * p[1] + matrix[5]);
        box = intersection(box, rectangle({ x: Math.min(...xs), y: Math.min(...ys) }, { x: Math.max(...xs), y: Math.max(...ys) }));
        if (!box) return null;
        host = matrix;
      }
    }
    return box;
  }
  return { rectangle, intersection, collect, mergedSelection, outlines, positions, bounds };
});
