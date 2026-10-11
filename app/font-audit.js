/*
 * Pure helpers for Figure Tool's document-wide editable-font review.
 *
 * Runtime font measurement and document editability stay in app.js. This
 * module owns exact family matching, inventory summaries, immutable review
 * plans, and the narrow serialized-node mutation used at confirmation time.
 */
(function exposeFigureStudioFontAudit(root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  if (root) root.FigureStudioFontAudit = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function createFigureStudioFontAuditModule() {
  "use strict";

  const VERSION = "1.0.0";
  const DEFAULT_FAMILY = "Arial, Helvetica, sans-serif";

  function normalizedFamily(value, fallback = DEFAULT_FAMILY) {
    return String(value == null ? "" : value).replace(/\s+/g, " ").trim() || String(fallback == null ? DEFAULT_FAMILY : fallback);
  }

  function familyKey(value, fallback = DEFAULT_FAMILY) {
    return normalizedFamily(value, fallback).toLocaleLowerCase("en-US");
  }

  function stableHash(value) {
    let hash = 2166136261;
    const text = String(value || "");
    for (let index = 0; index < text.length; index += 1) {
      hash ^= text.charCodeAt(index);
      hash = Math.imul(hash, 16777619);
    }
    return (hash >>> 0).toString(36);
  }

  function nodeFontDeclarations(node = {}, options = {}) {
    const fallback = options.defaultFamily || DEFAULT_FAMILY;
    const base = normalizedFamily(node.fontFamily ?? node.styleMeta?.fontFamily, fallback);
    const byKey = new Map([[familyKey(base, fallback), { family: base, fields: new Set(["base"]) }]]);
    Object.values(node.styles || {}).forEach((line) => {
      Object.values(line || {}).forEach((declaration) => {
        if (!declaration || typeof declaration !== "object" || declaration.fontFamily == null) return;
        const family = normalizedFamily(declaration.fontFamily, fallback);
        const key = familyKey(family, fallback);
        const current = byKey.get(key) || { family, fields: new Set() };
        current.fields.add("inline");
        byKey.set(key, current);
      });
    });
    return [...byKey.values()].map((entry) => ({ family: entry.family, fields: [...entry.fields].sort() }));
  }

  function resolutionState(resolution = {}) {
    if (resolution.status === "requested-font-available") return "resolved";
    if (resolution.status === "substituted-installed-font") return "substituted";
    return "unavailable";
  }

  function summarize(records = [], boundaries = [], options = {}) {
    const resolveFamily = typeof options.resolveFamily === "function"
      ? options.resolveFamily
      : (family) => ({ requestedFamily: family, requestedFont: family, resolvedFamily: "", status: "not-measured", note: "Font availability was not measured." });
    const groups = new Map();
    (Array.isArray(records) ? records : []).forEach((source) => {
      if (!source || typeof source !== "object") return;
      const family = normalizedFamily(source.family, options.defaultFamily || DEFAULT_FAMILY);
      const key = familyKey(family, options.defaultFamily || DEFAULT_FAMILY);
      const group = groups.get(key) || { key, family, records: [] };
      group.records.push({ ...source, family, fields: [...new Set(source.fields || [])].sort() });
      groups.set(key, group);
    });
    const families = [...groups.values()].map((group) => {
      const editable = group.records.filter((record) => record.editable === true);
      const reportOnly = group.records.filter((record) => record.editable !== true);
      const resolution = resolveFamily(group.family) || {};
      return {
        key: group.key,
        family: group.family,
        state: resolutionState(resolution),
        resolution: { ...resolution },
        editableObjectCount: new Set(editable.map((record) => `${record.pageId}:${record.pathKey || record.objectId}`)).size,
        editablePageCount: new Set(editable.map((record) => record.pageId)).size,
        reportOnlyObjectCount: new Set(reportOnly.map((record) => `${record.pageId}:${record.pathKey || record.objectId}`)).size,
        reportOnlyPageCount: new Set(reportOnly.map((record) => record.pageId)).size,
        locations: group.records.map((record) => ({
          pageId: record.pageId,
          pageLabel: record.pageLabel,
          objectId: record.objectId,
          objectLabel: record.objectLabel,
          text: record.text,
          editable: record.editable === true,
          reason: record.reason || "",
          fields: [...(record.fields || [])],
          path: [...(record.path || [])],
          pathKey: record.pathKey || (record.path || []).join(".")
        })),
        records: group.records
      };
    }).sort((left, right) => left.family.localeCompare(right.family));
    return {
      schema: "figureStudio.documentFontAudit.v1",
      familyCount: families.length,
      editableFamilyCount: families.filter((family) => family.editableObjectCount > 0).length,
      editableObjectCount: new Set((records || []).filter((record) => record.editable).map((record) => `${record.pageId}:${record.pathKey || record.objectId}`)).size,
      editablePageCount: new Set((records || []).filter((record) => record.editable).map((record) => record.pageId)).size,
      families,
      boundaries: (Array.isArray(boundaries) ? boundaries : []).map((boundary) => ({ ...boundary }))
    };
  }

  function createReplacementPlan(audit = {}, sourceFamily, targetFamily, identity = {}) {
    const source = normalizedFamily(sourceFamily, "");
    const target = normalizedFamily(targetFamily, "");
    const sourceKey = familyKey(source, "");
    const targetKey = familyKey(target, "");
    const family = (audit.families || []).find((entry) => entry.key === sourceKey);
    const affected = (family?.records || []).filter((record) => record.editable === true).map((record) => ({
      pageId: record.pageId,
      pageLabel: record.pageLabel,
      objectId: record.objectId,
      objectLabel: record.objectLabel,
      text: record.text,
      fields: [...(record.fields || [])],
      path: [...(record.path || [])],
      pathKey: record.pathKey || (record.path || []).join(".")
    }));
    const normalizedIdentity = {
      documentId: String(identity.documentId || ""),
      projectRevision: Number(identity.projectRevision || 0),
      activePageId: String(identity.activePageId || "")
    };
    const signatureInput = {
      identity: normalizedIdentity,
      sourceKey,
      targetKey,
      affected: affected.map((record) => ({ pageId: record.pageId, pathKey: record.pathKey, fields: record.fields }))
    };
    return {
      schema: "figureStudio.documentFontReplacementPlan.v1",
      sourceFamily: family?.family || source,
      sourceKey,
      targetFamily: target,
      targetKey,
      valid: Boolean(family && source && target && sourceKey !== targetKey && affected.length),
      affectedObjectCount: affected.length,
      affectedPageCount: new Set(affected.map((record) => record.pageId)).size,
      affected,
      identity: normalizedIdentity,
      signature: stableHash(JSON.stringify(signatureInput))
    };
  }

  function replaceFamilyInNode(node = {}, sourceFamily, targetFamily, options = {}) {
    const fallback = options.defaultFamily || DEFAULT_FAMILY;
    const sourceKey = familyKey(sourceFamily, fallback);
    const target = normalizedFamily(targetFamily, "");
    if (!target || sourceKey === familyKey(target, fallback)) return { changed: false, baseChanged: false, inlineChangeCount: 0 };
    const effectiveBase = normalizedFamily(node.fontFamily ?? node.styleMeta?.fontFamily, fallback);
    let baseChanged = false;
    let inlineChangeCount = 0;
    if (familyKey(effectiveBase, fallback) === sourceKey) {
      node.fontFamily = target;
      node.styleMeta = { ...(node.styleMeta || {}), fontFamily: target };
      baseChanged = true;
    }
    Object.values(node.styles || {}).forEach((line) => {
      Object.values(line || {}).forEach((declaration) => {
        if (!declaration || typeof declaration !== "object" || declaration.fontFamily == null) return;
        if (familyKey(declaration.fontFamily, fallback) !== sourceKey) return;
        declaration.fontFamily = target;
        inlineChangeCount += 1;
      });
    });
    return { changed: baseChanged || inlineChangeCount > 0, baseChanged, inlineChangeCount };
  }

  return Object.freeze({
    VERSION,
    DEFAULT_FAMILY,
    normalizedFamily,
    familyKey,
    nodeFontDeclarations,
    resolutionState,
    summarize,
    createReplacementPlan,
    replaceFamilyInNode,
    testing: Object.freeze({ stableHash })
  });
});
