(function (root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory();
  else root.FigureStudioSourcesLimits = factory();
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  const SCHEMA = "figureStudio.sourcesLimits.v1";
  const EMPTY = Object.freeze({});

  function text(value) {
    return value === undefined || value === null ? "" : String(value).trim();
  }

  function clone(value, fallback = null) {
    if (value === undefined || value === null) return fallback;
    try { return JSON.parse(JSON.stringify(value)); } catch { return fallback; }
  }

  function compact(value) {
    if (!value || typeof value !== "object" || Array.isArray(value)) return value || null;
    const out = {};
    Object.entries(value).forEach(([key, item]) => {
      if (item === undefined || item === null || item === "") return;
      if (Array.isArray(item) && item.length === 0) return;
      if (item && typeof item === "object" && !Array.isArray(item) && Object.keys(item).length === 0) return;
      out[key] = item;
    });
    return Object.keys(out).length ? out : null;
  }

  function normalizeObjectType(object) {
    return text(object.figureType || object.type || object.kind || "object") || "object";
  }

  function objectId(object, fallback) {
    return text(object.figureId || object.id || object.name || fallback) || fallback;
  }

  function objectName(object, fallback) {
    return text(object.name || object.label || object.text || fallback) || fallback;
  }

  function pageLabel(page, index) {
    return text(page.label || page.name || page.title || page.id) || `Page ${index + 1}`;
  }

  function pageId(page, index) {
    return text(page.id || page.pageId || page.nativeId) || `page-${index + 1}`;
  }

  function childrenOf(object) {
    const lists = [object.objects, object.children, object._objects].filter(Array.isArray);
    return lists.flat();
  }

  function fabricForPage(project, page) {
    if (page?.fabric && typeof page.fabric === "object") return page.fabric;
    if (page?.source?.fabric && typeof page.source.fabric === "object") return page.source.fabric;
    if (page?.fabricRef === "project.fabric" && project?.fabric) return project.fabric;
    return page || EMPTY;
  }

  function pageSnapshots(project) {
    const deckPages = project?.deck?.pages;
    if (Array.isArray(deckPages) && deckPages.length) return deckPages;
    const pages = project?.pages;
    if (Array.isArray(pages) && pages.length) return pages;
    return [{ id: text(project?.id) || "figure", label: text(project?.title) || "Figure", fabric: project?.fabric || project?.source?.fabric || { objects: [] } }];
  }

  function collectObjects(project) {
    const refs = [];
    pageSnapshots(project).forEach((page, pageIndex) => {
      const fabric = fabricForPage(project, page);
      const objects = Array.isArray(fabric.objects) ? fabric.objects : [];
      const visit = (object, childPath = [], topObjectId = "") => {
        if (!object || typeof object !== "object") return;
        const fallback = `${pageId(page, pageIndex)}:${childPath.join(".") || refs.length + 1}`;
        const currentObjectId = objectId(object, fallback);
        const currentTopObjectId = topObjectId || currentObjectId;
        refs.push({
          object,
          pageId: pageId(page, pageIndex),
          pageLabel: pageLabel(page, pageIndex),
          objectId: currentObjectId,
          topObjectId: currentTopObjectId,
          objectName: objectName(object, normalizeObjectType(object)),
          objectType: normalizeObjectType(object),
          visible: object.visible !== false,
          childPath: childPath.join(".")
        });
        childrenOf(object).forEach((child, index) => visit(child, [...childPath, index + 1], currentTopObjectId));
      };
      objects.forEach((object, index) => visit(object, [index + 1]));
    });
    return refs;
  }

  function lowerIncludes(value, needle) {
    return text(value).toLowerCase().includes(needle);
  }

  function firstValue(...values) {
    for (const value of values) {
      const current = text(value);
      if (current) return current;
    }
    return "";
  }

  function sourceKind(source, importMeta, object) {
    const kind = firstValue(source.kind, source.sourceKind, source.source_kind, importMeta.importMode, importMeta.import_mode, object.figureType, object.type);
    const haystack = `${kind} ${source.moduleId || ""} ${source.module_id || ""} ${source.resultId || ""} ${source.result_id || ""} ${source.filename || ""}`.toLowerCase();
    if (object.figureStudioSceneMeta || object.figure_studio_scene_meta || haystack.includes("scene")) return "Scientific scene";
    if (haystack.includes("bioplot") || haystack.includes("plot") || haystack.includes("result")) return "BioPlot panel";
    if (haystack.includes("asset") || object.scientificAssetMeta) return "Scientific asset";
    if (haystack.includes("pdf")) return "Imported PDF";
    if (haystack.includes("svg")) return "Imported SVG";
    if (haystack.includes("image") || haystack.includes("raster") || haystack.includes("png") || haystack.includes("jpeg") || haystack.includes("jpg")) return "Imported image";
    if (kind) return kind;
    return "Recorded source";
  }

  function scientificMeta(object) {
    return object.scientificAssetMeta || object.scientific_asset_meta || object.figureStudioSceneMeta || object.figure_studio_scene_meta || object.scientificSceneMeta || object.scientific_scene_meta || null;
  }

  function revisionRecord(meta, source, importMeta, object) {
    return firstValue(
      meta?.sourceRevisionId, meta?.source_revision_id, meta?.revisionId, meta?.revision_id, meta?.version, meta?.assetVersion, meta?.asset_version,
      meta?.sceneVersion, meta?.scene_version, meta?.scientificRecord?.revision, meta?.scientificRecord?.version,
      source?.snapshotId, source?.snapshot_id, source?.revisionId, source?.revision_id, source?.resultRevisionId, source?.result_revision_id,
      source?.sourceRevisionId, source?.source_revision_id, source?.version,
      importMeta?.sourceRevisionId, importMeta?.source_revision_id, importMeta?.pageRevisionId, importMeta?.page_revision_id,
      importMeta?.pdfSourceRevisionId, importMeta?.pdf_source_revision_id, object?.artifactRef?.sha256, object?.artifact_ref?.sha256
    );
  }

  function pageRecord(source, importMeta, object) {
    return firstValue(
      importMeta?.pdfPageNumber, importMeta?.pdf_page_number, importMeta?.sourcePageNumber, importMeta?.source_page_number, importMeta?.pageNumber, importMeta?.page_number, importMeta?.page,
      source?.pdfPageNumber, source?.pdf_page_number, source?.sourcePageNumber, source?.source_page_number, source?.pageNumber, source?.page_number, source?.page,
      object?.pdfSourcePageNumber, object?.pdf_source_page_number
    );
  }

  function rightsRecord(meta, source) {
    return firstValue(
      meta?.rightsRecordId, meta?.rights_record_id, meta?.licenseId, meta?.license_id,
      source?.rightsRecordId, source?.rights_record_id, source?.licenseId, source?.license_id
    );
  }

  function sourceRecord(meta, source, importMeta, object) {
    return firstValue(
      meta?.sourceRecordId, meta?.source_record_id, meta?.assetId, meta?.asset_id, meta?.sceneId, meta?.scene_id,
      meta?.scientificRecordId, meta?.scientific_record_id, meta?.scientificRecord?.id,
      source?.sourceId, source?.source_id, source?.resultId, source?.result_id, source?.filename, source?.sourceFilename,
      importMeta?.sourceFilename, importMeta?.source_filename, importMeta?.filename, object?.artifactRef?.id, object?.artifact_ref?.id
    );
  }

  function sourceLabel(meta, source, importMeta, object) {
    return firstValue(
      meta?.assetName, meta?.asset_name, meta?.scientificName, meta?.scientific_name, meta?.sceneName, meta?.scene_name,
      meta?.label, meta?.name, meta?.title, meta?.scientificRecord?.label, meta?.scientificRecord?.title,
      object?.name, source?.label, source?.name, source?.title,
      source?.filename, source?.sourceFilename, importMeta?.sourceFilename, importMeta?.source_filename,
      "Recorded source"
    );
  }

  function isUnresolved(source, importMeta, object) {
    const state = `${source?.status || ""} ${source?.state || ""} ${importMeta?.status || ""} ${object?.sourceStatus || ""} ${object?.source_status || ""}`.toLowerCase();
    if (/unresolved|missing|stale|unknown|placeholder/.test(state)) return true;
    if (object?.provenancePlaceholder && !sourceRecord(scientificMeta(object), source, importMeta, object)) return true;
    return false;
  }

  function limitStringsFrom(value) {
    if (value === undefined || value === null) return [];
    if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") return [text(value)].filter(Boolean);
    if (Array.isArray(value)) return value.flatMap(limitStringsFrom);
    if (typeof value === "object") {
      return [value.text, value.label, value.note, value.description, value.summary, value.statement].flatMap(limitStringsFrom);
    }
    return [];
  }

  function claimLimits(meta, source, importMeta, object) {
    const values = [
      meta?.limits, meta?.limitations, meta?.scientificLimits, meta?.scientific_limits,
      meta?.scientificRecord?.limitations, meta?.scientificRecord?.limits, meta?.scientificRecord?.notes,
      source?.limits, source?.limitations, source?.notes, importMeta?.notes,
      object?.sourceLimit, object?.source_limit
    ];
    return Array.from(new Set(values.flatMap(limitStringsFrom).filter(Boolean)));
  }

  function sourceKeyFor(meta, source, importMeta, object) {
    const base = sourceRecord(meta, source, importMeta, object);
    const revision = revisionRecord(meta, source, importMeta, object);
    if (base) return JSON.stringify(["source", sourceKind(source, importMeta, object), base, revision || "current"]);
    return JSON.stringify(["unresolved", objectId(object, object.name || "object")]);
  }

  function buildSourceRecord(ref) {
    const object = ref.object || EMPTY;
    const source = object.source && typeof object.source === "object" ? object.source : EMPTY;
    const importMeta = object.importMeta && typeof object.importMeta === "object" ? object.importMeta : EMPTY;
    const meta = scientificMeta(object) || EMPTY;
    const sourceRecordId = sourceRecord(meta, source, importMeta, object);
    const sourceRevisionId = revisionRecord(meta, source, importMeta, object);
    const label = sourceLabel(meta, source, importMeta, object) || ref.objectName;
    const unresolved = isUnresolved(source, importMeta, object) || (!sourceRecordId && (object.type === "image" || object.figureType === "image" || importMeta.importMode || source.kind));
    const rightsId = rightsRecord(meta, source);
    const limits = claimLimits(meta, source, importMeta, object);
    if (!limits.length) limits.push("No scientific claim or reuse permission is inferred from this record.");
    return {
      key: sourceKeyFor(meta, source, importMeta, object),
      label,
      kind: sourceKind(source, importMeta, object),
      status: unresolved ? "unresolved" : "recorded",
      rightsStatus: rightsId ? "recorded" : "not recorded",
      sourceRecordId: sourceRecordId || "",
      sourceRevisionId: sourceRevisionId || "",
      rightsRecordId: rightsId || "",
      limits,
      objectRefs: [{ pageId: ref.pageId, pageLabel: ref.pageLabel, objectId: ref.objectId, topObjectId: ref.topObjectId || ref.objectId, objectName: ref.objectName, objectType: ref.objectType, visible: ref.visible, childPath: ref.childPath || "" }],
      sourceRecords: sourceRecordId ? [sourceRecordId] : [],
      sourceRevisions: sourceRevisionId ? [sourceRevisionId] : [],
      rightsRecords: rightsId ? [rightsId] : [],
      pages: pageRecord(source, importMeta, object) ? [pageRecord(source, importMeta, object)] : [],
      rightsPresentCount: rightsId ? 1 : 0,
      rightsMissingCount: rightsId ? 0 : 1,
      recordConflicts: [],
      details: compact({ source: clone(source, null), importMeta: clone(importMeta, null), scientificMeta: clone(meta, null), artifactRef: clone(object.artifactRef || object.artifact_ref, null) }) || {}
    };
  }

  function fontFamiliesForObject(object) {
    const families = new Set();
    [object.fontFamily, object.styleMeta?.fontFamily, object.style?.fontFamily].map(text).filter(Boolean).forEach((family) => families.add(family));
    const styles = object.styles;
    if (styles && typeof styles === "object") {
      if (Array.isArray(styles)) {
        styles.forEach((span) => { const family = text(span?.style?.fontFamily || span?.fontFamily); if (family) families.add(family); });
      } else {
        Object.values(styles).forEach((line) => {
          if (!line || typeof line !== "object") return;
          Object.values(line).forEach((style) => { const family = text(style?.fontFamily); if (family) families.add(family); });
        });
      }
    }
    return [...families].sort((a, b) => a.localeCompare(b));
  }

  function mergeSource(target, next) {
    next.objectRefs.forEach((ref) => {
      const id = JSON.stringify([ref.pageId, ref.objectId, ref.childPath || ""]);
      if (!target._refIds.has(id)) {
        target._refIds.add(id);
        target.objectRefs.push(ref);
      }
    });
    next.limits.forEach((limit) => { if (!target.limits.includes(limit)) target.limits.push(limit); });
    target.sourceRecords = Array.from(new Set([...(target.sourceRecords || []), ...(next.sourceRecords || []), next.sourceRecordId].filter(Boolean))).sort();
    target.sourceRevisions = Array.from(new Set([...(target.sourceRevisions || []), ...(next.sourceRevisions || []), next.sourceRevisionId].filter(Boolean))).sort();
    target.rightsRecords = Array.from(new Set([...(target.rightsRecords || []), ...(next.rightsRecords || []), next.rightsRecordId].filter(Boolean))).sort();
    target.pages = Array.from(new Set([...(target.pages || []), ...(next.pages || [])].filter(Boolean))).sort((a, b) => String(a).localeCompare(String(b), undefined, { numeric: true }));
    target.rightsPresentCount = Number(target.rightsPresentCount || 0) + Number(next.rightsPresentCount || (next.rightsRecordId ? 1 : 0));
    target.rightsMissingCount = Number(target.rightsMissingCount || 0) + Number(next.rightsMissingCount || (next.rightsRecordId ? 0 : 1));
    if (!target.sourceRecordId && next.sourceRecordId) target.sourceRecordId = next.sourceRecordId;
    if (!target.rightsRecordId && next.rightsRecordId) target.rightsRecordId = next.rightsRecordId;
    if (target.sourceRecordId && next.sourceRecordId && target.sourceRecordId !== next.sourceRecordId) target.recordConflicts.push({ field: "sourceRecordId", existing: target.sourceRecordId, next: next.sourceRecordId });
    if (target.rightsRecordId && next.rightsRecordId && target.rightsRecordId !== next.rightsRecordId) target.recordConflicts.push({ field: "rightsRecordId", existing: target.rightsRecordId, next: next.rightsRecordId });
    if (target.status !== "unresolved" && next.status === "unresolved") target.status = "unresolved";
    if (target.rightsRecords.length > 1) target.rightsStatus = "conflicting records";
    else if (target.rightsPresentCount > 0 && target.rightsMissingCount > 0) target.rightsStatus = "partly recorded";
    else target.rightsStatus = target.rightsPresentCount > 0 ? "recorded" : "not recorded";
    const example = compact({ ...(next.details || {}), objectRef: next.objectRefs?.[0] || null });
    target.details = {
      ...target.details,
      examples: [...(target.details?.examples || []), example].filter((item) => item && Object.keys(item).length).slice(0, 12)
    };
  }

  function addFontSource(map, family, ref) {
    const key = JSON.stringify(["font", family]);
    const next = {
      key,
      label: family,
      kind: "Font family",
      status: "recorded",
      rightsStatus: "not recorded",
      sourceRecordId: "",
      rightsRecordId: "",
      limits: ["Font availability and licensing are reviewed outside the figure artwork record."],
      objectRefs: [{ pageId: ref.pageId, pageLabel: ref.pageLabel, objectId: ref.objectId, topObjectId: ref.topObjectId || ref.objectId, objectName: ref.objectName, objectType: ref.objectType, visible: ref.visible, childPath: ref.childPath || "" }],
      details: { fontFamily: family }
    };
    if (!map.has(key)) map.set(key, { ...next, objectRefs: [], sourceRecords: [], sourceRevisions: [], rightsRecords: [], pages: [], rightsPresentCount: 0, rightsMissingCount: 0, recordConflicts: [], limits: [], details: {}, _refIds: new Set() });
    mergeSource(map.get(key), next);
  }

  function stableSources(map) {
    return [...map.values()].map((record) => {
      const copy = { ...record };
      delete copy._refIds;
      copy.objectRefs = copy.objectRefs.sort((a, b) => `${a.pageLabel}:${a.objectName}:${a.objectId}`.localeCompare(`${b.pageLabel}:${b.objectName}:${b.objectId}`));
      return copy;
    }).sort((a, b) => `${a.status === "unresolved" ? "0" : "1"}:${a.kind}:${a.label}`.localeCompare(`${b.status === "unresolved" ? "0" : "1"}:${b.kind}:${b.label}`));
  }

  function build(project, options = {}) {
    const refs = collectObjects(project || {});
    const selected = new Set((options.selectedObjectIds || []).map(text).filter(Boolean));
    const sourceMap = new Map();
    refs.forEach((ref) => {
      const object = ref.object || EMPTY;
      const hasRecord = object.source || object.importMeta || object.scientificAssetMeta || object.scientific_asset_meta || object.figureStudioSceneMeta || object.figure_studio_scene_meta || object.artifactRef || object.provenancePlaceholder || object.sourceStatus || object.source_status;
      if (hasRecord) {
        const next = buildSourceRecord(ref);
        if (!sourceMap.has(next.key)) sourceMap.set(next.key, { ...next, objectRefs: [], sourceRecords: [], sourceRevisions: [], rightsRecords: [], pages: [], rightsPresentCount: 0, rightsMissingCount: 0, recordConflicts: [], limits: [], details: {}, _refIds: new Set() });
        mergeSource(sourceMap.get(next.key), next);
      }
      fontFamiliesForObject(object).forEach((family) => addFontSource(sourceMap, family, ref));
    });
    const sources = stableSources(sourceMap);
    const selectedSourceKeys = sources.filter((source) => source.objectRefs.some((ref) => selected.has(ref.objectId) || selected.has(ref.topObjectId))).map((source) => source.key);
    const unresolved = sources.filter((source) => source.status === "unresolved").map((source) => ({ key: source.key, label: source.label, kind: source.kind, objectRefs: source.objectRefs }));
    return {
      schema: SCHEMA,
      app: "Figure Tool",
      version: text(options.version) || "",
      timestamp: options.timestamp === undefined ? "" : text(options.timestamp),
      projectRevision: options.projectRevision ?? project?.projectRevision ?? project?.revision ?? null,
      sourceSummaryDigest: text(options.sourceSummaryDigest || project?.sourceSummaryDigest || ""),
      digestScope: text(options.digestScope || project?.digestScope || "source-records-and-object-references.v1"),
      document: {
        kind: text(options.documentKind || project?.kind || project?.documentKind || project?.mode) || "figure",
        title: text(options.title || project?.title || project?.name) || "Untitled figure",
        pageCount: pageSnapshots(project || {}).length
      },
      summary: {
        sourceCount: sources.length,
        objectReferenceCount: sources.reduce((count, source) => count + source.objectRefs.length, 0),
        unresolvedCount: unresolved.length,
        fontFamilyCount: sources.filter((source) => source.kind === "Font family").length
      },
      selectedObjectIds: [...selected].sort(),
      selectedSourceKeys,
      sources,
      unresolved
    };
  }

  function toText(report) {
    const lines = [];
    lines.push(`${report.document?.title || "Figure"} — Sources & limits`);
    lines.push(`${report.summary?.sourceCount || 0} source records, ${report.summary?.unresolvedCount || 0} unresolved, ${report.summary?.fontFamilyCount || 0} font families.`);
    lines.push("");
    (report.sources || []).forEach((source) => {
      lines.push(`- ${source.label} (${source.kind}; ${source.status}; rights: ${source.rightsStatus})`);
      (source.limits || []).forEach((limit) => lines.push(`  Limit: ${limit}`));
      lines.push(`  Used by: ${(source.objectRefs || []).map((ref) => `${ref.pageLabel}/${ref.objectName}`).join("; ") || "No objects"}`);
      if (source.sourceRecordId || source.rightsRecordId || (source.pages || []).length) lines.push(`  Details: source=${source.sourceRecordId || "not recorded"}; revision=${source.sourceRevisionId || "not recorded"}; rights=${source.rightsRecordId || "not recorded"}; pages=${(source.pages || []).join(", ") || "not recorded"}`);
    });
    return `${lines.join("\n")}\n`;
  }

  return { SCHEMA, build, toText };
});
