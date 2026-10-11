(function (root, factory) {
  "use strict";
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  if (root) root.FigureStudioRecentDocuments = api;
})(typeof window !== "undefined" ? window : globalThis, function () {
  "use strict";

  const SCHEMA = "figureStudio.recentDocuments.v1";
  const STORAGE_KEY = "figureStudio.recentDocuments.v1";
  const MAX_ENTRIES = 8;
  const DOCUMENT_EXTENSIONS = Object.freeze({
    ".fsfigure": "figure",
    ".fsdeck": "presentation"
  });

  function normalizeWindowsPath(value) {
    let path = String(value || "").trim();
    if (!path || /[\u0000-\u001f]/.test(path)) return "";
    path = path.replace(/\//g, "\\");
    if (/^\\\\\?\\UNC\\/i.test(path)) path = `\\\\${path.slice(8)}`;
    else if (/^\\\\\?\\[A-Za-z]:\\/.test(path)) path = path.slice(4);
    if (/^[A-Za-z]:\\/.test(path)) {
      path = `${path[0].toUpperCase()}${path.slice(1).replace(/\\{2,}/g, "\\")}`;
    } else if (/^\\\\[^\\]+\\[^\\]+(?:\\|$)/.test(path)) {
      path = `\\\\${path.slice(2).replace(/\\{2,}/g, "\\")}`;
    } else {
      return "";
    }
    while (path.length > 3 && path.endsWith("\\")) path = path.slice(0, -1);
    return path.length <= 32767 ? path : "";
  }

  function filenameFromPath(path) {
    return String(path || "").split("\\").filter(Boolean).at(-1) || "";
  }

  function extensionForFilename(filename) {
    const lower = String(filename || "").toLowerCase();
    return Object.keys(DOCUMENT_EXTENSIONS).find((extension) => lower.endsWith(extension)) || "";
  }

  function kindForPath(path) {
    return DOCUMENT_EXTENSIONS[extensionForFilename(filenameFromPath(path))] || "";
  }

  function canonicalKey(path) {
    return normalizeWindowsPath(path).toLocaleLowerCase("en-US");
  }

  function stableId(path) {
    const source = canonicalKey(path);
    if (!source) return "";
    let hash = 2166136261;
    for (let index = 0; index < source.length; index += 1) {
      hash ^= source.charCodeAt(index);
      hash = Math.imul(hash, 16777619);
    }
    return `recent-${(hash >>> 0).toString(36)}`;
  }

  function normalizedTimestamp(value) {
    const timestamp = String(value || "").trim();
    if (!timestamp || !Number.isFinite(Date.parse(timestamp))) return "";
    return new Date(timestamp).toISOString();
  }

  function createEntry(value = {}, options = {}) {
    const path = normalizeWindowsPath(value.path);
    const kind = kindForPath(path);
    if (!path || !kind) return null;
    const requestedKind = String(value.kind || value.documentKind || "").trim().toLowerCase();
    if (requestedKind && requestedKind !== kind) return null;
    const touchedAt = normalizedTimestamp(value.touchedAt || value.touched_at || options.now)
      || new Date(Number(options.nowMs) || Date.now()).toISOString();
    return {
      id: stableId(path),
      path,
      filename: filenameFromPath(path),
      kind,
      touchedAt
    };
  }

  function normalizeEntries(value, options = {}) {
    const source = Array.isArray(value) ? value : Array.isArray(value?.entries) ? value.entries : [];
    const limit = Math.max(1, Math.min(MAX_ENTRIES, Number(options.limit) || MAX_ENTRIES));
    const seen = new Set();
    const entries = [];
    for (const candidate of source) {
      const entry = createEntry(candidate, options);
      const key = entry ? canonicalKey(entry.path) : "";
      if (!entry || seen.has(key)) continue;
      seen.add(key);
      entries.push(entry);
      if (entries.length >= limit) break;
    }
    return entries;
  }

  function record(entries, value, options = {}) {
    const entry = createEntry(value, options);
    if (!entry) return { changed: false, entries: normalizeEntries(entries, options), entry: null };
    const key = canonicalKey(entry.path);
    const current = normalizeEntries(entries, options);
    const next = normalizeEntries([entry, ...current.filter((candidate) => canonicalKey(candidate.path) !== key)], options);
    return { changed: JSON.stringify(current) !== JSON.stringify(next), entries: next, entry };
  }

  function remove(entries, idOrPath, options = {}) {
    const requested = String(idOrPath || "");
    const key = canonicalKey(requested);
    const current = normalizeEntries(entries, options);
    const next = current.filter((entry) => entry.id !== requested && (!key || canonicalKey(entry.path) !== key));
    return { changed: next.length !== current.length, entries: next };
  }

  function serialize(entries, options = {}) {
    return JSON.stringify({ schema: SCHEMA, entries: normalizeEntries(entries, options) });
  }

  function parse(serialized, options = {}) {
    try {
      const value = typeof serialized === "string" ? JSON.parse(serialized) : serialized;
      if (!value || value.schema !== SCHEMA) return [];
      return normalizeEntries(value.entries, options);
    } catch (_error) {
      return [];
    }
  }

  return Object.freeze({
    SCHEMA,
    STORAGE_KEY,
    MAX_ENTRIES,
    normalizeWindowsPath,
    filenameFromPath,
    kindForPath,
    canonicalKey,
    stableId,
    createEntry,
    normalizeEntries,
    record,
    remove,
    serialize,
    parse
  });
});
