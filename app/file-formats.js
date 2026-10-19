/*
 * Figure Tool beta.2 file-format boundary.
 *
 * This module is deliberately independent of the editor, browser File APIs,
 * and the native host. It classifies names and payloads, validates files before
 * they reach live document state, and serializes portable document/workspace
 * records without leaking tab runtime state.
 *
 * Browser: window.FigureStudioFileFormats
 * Node QA: require("./file-formats.js")
 */
(function exposeFigureStudioFileFormats(root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  if (root) root.FigureStudioFileFormats = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function createFigureStudioFileFormats() {
  "use strict";

  const VERSION = "1.0.0";
  const DOCUMENT_PAYLOAD_SCHEMA = "figureStudio.projectPayload.v1";
  const OBJECT_CONNECTOR_DOCUMENT_PAYLOAD_SCHEMA = "figureStudio.projectPayload.v2";
  const DOCUMENT_SCHEMA = "figureStudio.project.v2";
  const WORKSPACE_SCHEMA = "figureStudio.workspaceProject.v1";
  const OBJECT_CONNECTOR_WORKSPACE_SCHEMA = "figureStudio.workspaceProject.v2";
  const SHARED_GROUP_IMPORT_META_SCHEMA_PREFIX = "figureStudio.sharedGroupImportMeta.";
  const SHARED_GROUP_IMPORT_META_SCHEMA = "figureStudio.sharedGroupImportMeta.v1";
  const MAX_FILE_BYTES = 256 * 1024 * 1024;
  const LEGACY_OPEN_MINIMUM_BETA_CYCLES = 2;
  const DOCUMENT_KINDS = Object.freeze(["figure", "presentation"]);
  const EXTENSIONS = Object.freeze({
    figure: ".fsfigure",
    presentation: ".fsdeck",
    workspace: ".fsproject"
  });
  const LEGACY_EXTENSIONS = Object.freeze([".figurestudio", ".figure-studio.json"]);
  const POSITIONED_PDF_TEXT_SCHEMAS = new Set(["figureStudio.pdfPositionedText.v1", "figureStudio.pdfPositionedText.v2"]);
  const RUNTIME_KEYS = new Set([
    "dirty",
    "directselection",
    "directorypath",
    "exporttarget",
    "filepath",
    "history",
    "historydirectselection",
    "historyselection",
    "historyundodirectselection",
    "lastpreflightreport",
    "missingartifacts",
    "nativedocumentid",
    "packageimportstate",
    "projectrevision",
    "redostack",
    "savelabel",
    "selectionids",
    "uicontext",
    "undostack"
  ]);

  class FigureStudioFormatError extends Error {
    constructor(code, message) {
      super(message);
      this.name = "FigureStudioFormatError";
      this.code = code;
    }
  }

  function fail(code, message) {
    throw new FigureStudioFormatError(code, message);
  }

  function isRecord(value) {
    return Boolean(value) && typeof value === "object" && !Array.isArray(value);
  }

  function isDocumentPayloadSchema(schema) {
    return schema === DOCUMENT_PAYLOAD_SCHEMA || schema === OBJECT_CONNECTOR_DOCUMENT_PAYLOAD_SCHEMA;
  }

  function isWorkspaceSchema(schema) {
    return schema === WORKSPACE_SCHEMA || schema === OBJECT_CONNECTOR_WORKSPACE_SCHEMA;
  }

  function requiresObjectConnectorReader(value) {
    const pending = [value], seen = new Set();
    let required = false;
    while (pending.length) {
      const row = pending.pop();
      if (!row || typeof row !== "object" || seen.has(row)) continue;
      seen.add(row);
      if (row.figureType === "smartConnector" && Object.prototype.hasOwnProperty.call(row.smartConnectorMeta || {}, "geometrySpace")) {
        if (row.smartConnectorMeta.geometrySpace !== "object") fail("unsupported_connector_geometry", "This arrow uses coordinates from a newer Figure Tool version.");
        required = true;
      }
      for (const entry of Object.values(row)) if (entry && typeof entry === "object") pending.push(entry);
    }
    return required;
  }

  function documentPayloadSchemaForProject(project) {
    return requiresObjectConnectorReader(project) ? OBJECT_CONNECTOR_DOCUMENT_PAYLOAD_SCHEMA : DOCUMENT_PAYLOAD_SCHEMA;
  }

  // This small version check also runs on a worker response before persistence.
  // It never repairs a stale worker's downgraded envelope or clones its artwork.
  function assertReaderEnvelopeVersions(payload) {
    if (isWorkspaceSchema(payload?.schema)) {
      let newerDocument = false;
      for (const document of payload.documents || []) {
        assertReaderEnvelopeVersions(document.payload);
        newerDocument ||= document.payload.schema === OBJECT_CONNECTOR_DOCUMENT_PAYLOAD_SCHEMA;
      }
      if (newerDocument && payload.schema !== OBJECT_CONNECTOR_WORKSPACE_SCHEMA) fail("connector_reader_version_required", "These arrows require the updated Figure Tool project format. Reload the editor before saving.");
      return;
    }
    if (!isDocumentPayloadSchema(payload?.schema) || !isRecord(payload.project)) fail("invalid_document_envelope", "That save is not a supported Figure Tool document.");
    if (requiresObjectConnectorReader(payload.project) && payload.schema !== OBJECT_CONNECTOR_DOCUMENT_PAYLOAD_SCHEMA) fail("connector_reader_version_required", "These arrows require the updated Figure Tool document format. Reload the editor before saving.");
  }

  function normalizeKind(value) {
    const kind = String(value || "").trim().toLowerCase();
    return DOCUMENT_KINDS.includes(kind) ? kind : "";
  }

  function normalizedFilename(value) {
    return String(value || "").trim().replace(/^.*[\\/]/, "");
  }

  function classifyFilename(filename) {
    const name = normalizedFilename(filename);
    const lower = name.toLowerCase();
    if (lower.endsWith(EXTENSIONS.figure)) {
      return Object.freeze({
        format: "document",
        kind: "figure",
        extension: EXTENSIONS.figure,
        filename: name,
        legacy: false,
        requiresSaveAs: false
      });
    }
    if (lower.endsWith(EXTENSIONS.presentation)) {
      return Object.freeze({
        format: "document",
        kind: "presentation",
        extension: EXTENSIONS.presentation,
        filename: name,
        legacy: false,
        requiresSaveAs: false
      });
    }
    if (lower.endsWith(EXTENSIONS.workspace)) {
      return Object.freeze({
        format: "workspace",
        kind: "workspace",
        extension: EXTENSIONS.workspace,
        filename: name,
        legacy: false,
        requiresSaveAs: false
      });
    }
    const legacyExtension = LEGACY_EXTENSIONS.find((extension) => lower.endsWith(extension)) || "";
    if (legacyExtension) {
      return Object.freeze({
        format: "document",
        kind: "",
        extension: legacyExtension,
        filename: name,
        legacy: true,
        requiresSaveAs: true
      });
    }
    return Object.freeze({
      format: "unknown",
      kind: "",
      extension: "",
      filename: name,
      legacy: false,
      requiresSaveAs: false
    });
  }

  function projectKind(project) {
    if (!isRecord(project)) fail("invalid_document", "The document payload must contain a project object.");
    if (project.schema !== DOCUMENT_SCHEMA) {
      fail("invalid_document_schema", `Expected ${DOCUMENT_SCHEMA}.`);
    }
    const kind = normalizeKind(project.document?.kind);
    if (!kind) fail("invalid_document_kind", "The document kind must be Figure or Presentation.");
    if (
      !isRecord(project.artboard)
      || !Number.isFinite(Number(project.artboard.widthIn))
      || !Number.isFinite(Number(project.artboard.heightIn))
      || Number(project.artboard.widthIn) <= 0
      || Number(project.artboard.heightIn) <= 0
    ) {
      fail("invalid_document_artboard", "The document must contain a valid artboard size.");
    }
    if (!isRecord(project.fabric) || !Array.isArray(project.fabric.objects)) {
      fail("invalid_document_canvas", "The document must contain a valid editable canvas.");
    }
    return kind;
  }

  function canonicalLegacyProject(project) {
    if (!isRecord(project) || Object.prototype.hasOwnProperty.call(project, "schema")) {
      fail("unsupported_payload_schema", "This is not a supported legacy Figure Tool document.");
    }
    const candidate = cloneJson(project);
    const kind = normalizeKind(candidate.document?.kind) || "figure";
    candidate.schema = DOCUMENT_SCHEMA;
    candidate.document = {
      ...(isRecord(candidate.document) ? candidate.document : {}),
      kind
    };
    projectKind(candidate);
    assertNoNestedEnvelope(candidate);
    return candidate;
  }

  function assertNoNestedEnvelope(value, seen = new Set()) {
    if (!value || typeof value !== "object") return;
    if (seen.has(value)) fail("recursive_payload", "Recursive or circular document envelopes are not supported.");
    seen.add(value);
    const values = Array.isArray(value) ? value : Object.values(value);
    for (const entry of values) {
      if (isRecord(entry) && (isDocumentPayloadSchema(entry.schema) || isWorkspaceSchema(entry.schema))) {
        fail("recursive_payload", "A document payload cannot contain another document or workspace envelope.");
      }
      assertNoNestedEnvelope(entry, seen);
    }
    seen.delete(value);
  }

  function validateDocumentEnvelope(payload, expectedKind = "") {
    if (!isRecord(payload) || !isDocumentPayloadSchema(payload.schema) || !isRecord(payload.project)) {
      fail("invalid_document_envelope", `Expected a ${DOCUMENT_PAYLOAD_SCHEMA} document envelope.`);
    }
    const kind = projectKind(payload.project);
    assertReaderEnvelopeVersions(payload);
    const normalizedExpected = expectedKind ? normalizeKind(expectedKind) : "";
    if (expectedKind && !normalizedExpected) fail("invalid_expected_kind", "Expected kind must be Figure or Presentation.");
    if (normalizedExpected && kind !== normalizedExpected) {
      fail("extension_kind_mismatch", `This ${kind} document cannot be opened as ${normalizedExpected}.`);
    }
    assertNoNestedEnvelope(payload.project);
    return kind;
  }

  function classifyPayload(payload, options = {}) {
    if (!isRecord(payload)) fail("invalid_payload", "The file must contain a JSON object.");
    if (isWorkspaceSchema(payload.schema)) {
      validateWorkspaceProject(payload);
      return Object.freeze({
        format: "workspace",
        kind: "workspace",
        schema: payload.schema,
        envelope: true,
        legacy: false
      });
    }
    if (isDocumentPayloadSchema(payload.schema)) {
      if (isRecord(payload.project) && !Object.prototype.hasOwnProperty.call(payload.project, "schema")) {
        if (!options.allowHistorical) {
          fail("invalid_document_schema", `Expected ${DOCUMENT_SCHEMA}.`);
        }
        const project = canonicalLegacyProject(payload.project);
        assertReaderEnvelopeVersions({ schema: payload.schema, project });
        return Object.freeze({
          format: "document",
          kind: project.document.kind,
          schema: payload.schema,
          envelope: true,
          legacy: true,
          legacyShape: true
        });
      }
      const kind = validateDocumentEnvelope(payload);
      return Object.freeze({
        format: "document",
        kind,
        schema: payload.schema,
        envelope: true,
        legacy: false
      });
    }
    if (payload.schema === DOCUMENT_SCHEMA) {
      const kind = projectKind(payload);
      requiresObjectConnectorReader(payload);
      assertNoNestedEnvelope(payload);
      return Object.freeze({
        format: "document",
        kind,
        schema: DOCUMENT_SCHEMA,
        envelope: false,
        legacy: true
      });
    }
    if (!Object.prototype.hasOwnProperty.call(payload, "schema")) {
      if (!options.allowHistorical) {
        fail("unsupported_payload_schema", "This is not a supported Figure Tool document or project file.");
      }
      const project = canonicalLegacyProject(payload);
      requiresObjectConnectorReader(project);
      return Object.freeze({
        format: "document",
        kind: project.document.kind,
        schema: "legacy-schema-less",
        envelope: false,
        legacy: true,
        legacyShape: true
      });
    }
    fail("unsupported_payload_schema", "This is not a supported Figure Tool document or project file.");
  }

  function utf8ByteLength(text) {
    if (typeof TextEncoder === "function") return new TextEncoder().encode(text).byteLength;
    return unescape(encodeURIComponent(text)).length;
  }

  function decodeContents(contents, maxBytes) {
    if (typeof contents === "string") {
      const byteLength = utf8ByteLength(contents);
      if (byteLength > maxBytes) fail("file_too_large", `Figure Tool files may not exceed ${maxBytes} bytes.`);
      return contents;
    }
    if (contents instanceof ArrayBuffer) contents = new Uint8Array(contents);
    if (ArrayBuffer.isView(contents)) {
      if (contents.byteLength > maxBytes) fail("file_too_large", `Figure Tool files may not exceed ${maxBytes} bytes.`);
      try {
        return new TextDecoder("utf-8", { fatal: true }).decode(
          new Uint8Array(contents.buffer, contents.byteOffset, contents.byteLength)
        );
      } catch (_error) {
        fail("invalid_encoding", "The file is not valid UTF-8 text.");
      }
    }
    fail("invalid_contents", "File contents must be JSON text or UTF-8 bytes.");
  }

  function cloneJson(value, code = "invalid_payload") {
    try {
      return JSON.parse(JSON.stringify(value));
    } catch (_error) {
      fail(code, "The payload must be finite, acyclic JSON data.");
    }
  }

  function isRecordLike(value) {
    return Boolean(value && typeof value === "object" && !Array.isArray(value));
  }

  function jsonValuesEqual(left, right) {
    if (left === right) return true;
    if (left === null || right === null || typeof left !== typeof right || typeof left !== "object") return false;
    if (Array.isArray(left) !== Array.isArray(right)) return false;
    const leftKeys = Object.keys(left);
    const rightKeys = Object.keys(right);
    if (leftKeys.length !== rightKeys.length) return false;
    for (const key of leftKeys) {
      if (!Object.prototype.hasOwnProperty.call(right, key) || !jsonValuesEqual(left[key], right[key])) return false;
    }
    return true;
  }

  function importedVectorChildren(group) {
    const groupMeta = group?.importMeta;
    const batchId = String(group?.groupId || groupMeta?.importBatchId || "");
    if (!Array.isArray(group?.objects) || !batchId || !isRecordLike(groupMeta)) return [];
    if (groupMeta.editablePanelImport !== true || groupMeta.editableObjectImport !== true) return [];
    const children = group.objects.filter((child) => !child?.pdfPageFrame);
    if (children.length < 2) return [];
    if (!children.every((child) => {
      const meta = child?.importMeta;
      return isRecordLike(meta)
        && !(typeof meta.schema === "string" && meta.schema.startsWith(SHARED_GROUP_IMPORT_META_SCHEMA_PREFIX))
        && meta.editableObjectImport === true
        && meta.editablePanelImport === false
        && String(meta.importBatchId || "") === batchId
        && String(meta.importMode || meta.import_mode || "") === String(groupMeta.importMode || groupMeta.import_mode || "");
    })) return [];
    return children;
  }

  function importMetaDelta(base, value) {
    const overrides = {};
    const removed = [];
    for (const key of Object.keys(base || {})) {
      if (!Object.prototype.hasOwnProperty.call(value || {}, key)) removed.push(key);
    }
    for (const [key, entry] of Object.entries(value || {})) {
      if (!Object.prototype.hasOwnProperty.call(base || {}, key) || !jsonValuesEqual(base[key], entry)) {
        Object.defineProperty(overrides, key, { value: entry, enumerable: true, writable: true, configurable: true });
      }
    }
    return { overrides, removed };
  }

  function cloneCompactImportMetadata(value, active = new Set(), omitImportMeta = false) {
    if (!value || typeof value !== "object") return value;
    if (active.has(value)) fail("invalid_payload", "The payload must be finite, acyclic JSON data.");
    active.add(value);
    if (Array.isArray(value)) {
      const result = value.map((entry) => cloneCompactImportMetadata(entry, active));
      active.delete(value);
      return result;
    }
    const result = {};
    const sharedChildren = importedVectorChildren(value);
    const sharedChildrenSet = new Set(sharedChildren);
    for (const [key, entry] of Object.entries(value)) {
      if (omitImportMeta && key === "importMeta") continue;
      if (key === "objects" && Array.isArray(entry)) {
        result.objects = entry.map((child) => {
          const compactChild = sharedChildrenSet.has(child);
          const copy = cloneCompactImportMetadata(child, active, compactChild);
          if (compactChild) {
            const { overrides, removed } = importMetaDelta(value.importMeta, child.importMeta);
            copy.importMeta = {
              schema: SHARED_GROUP_IMPORT_META_SCHEMA,
              groupId: String(value.groupId || value.importMeta.importBatchId || ""),
              overrides: cloneCompactImportMetadata(overrides, active),
              removed
            };
          }
          return copy;
        });
      } else {
        Object.defineProperty(result, key, { value: cloneCompactImportMetadata(entry, active), enumerable: true, writable: true, configurable: true });
      }
    }
    active.delete(value);
    return result;
  }

  function containsCompactableImportGroup(value, seen = new Set()) {
    if (!value || typeof value !== "object" || seen.has(value)) return false;
    seen.add(value);
    if (!Array.isArray(value) && importedVectorChildren(value).length) return true;
    const values = Array.isArray(value) ? value : Object.values(value);
    return values.some((entry) => containsCompactableImportGroup(entry, seen));
  }

  function containsSharedImportMetaReference(value, seen = new Set()) {
    if (!value || typeof value !== "object" || seen.has(value)) return false;
    seen.add(value);
    if (!Array.isArray(value) && typeof value.importMeta?.schema === "string"
      && value.importMeta.schema.startsWith(SHARED_GROUP_IMPORT_META_SCHEMA_PREFIX)) return true;
    const values = Array.isArray(value) ? value : Object.values(value);
    return values.some((entry) => containsSharedImportMetaReference(entry, seen));
  }

  function compactSharedGroupImportMetadata(value) {
    if (!containsCompactableImportGroup(value)) return value;
    return cloneCompactImportMetadata(value);
  }

  function* containsCompactableImportGroupSteps(value, seen = new Set()) {
    if (!value || typeof value !== "object" || seen.has(value)) return false;
    seen.add(value);
    if (!Array.isArray(value) && importedVectorChildren(value).length) return true;
    yield 1;
    for (const entry of Array.isArray(value) ? value : Object.values(value)) {
      if (yield* containsCompactableImportGroupSteps(entry, seen)) return true;
      yield 1;
    }
    return false;
  }

  function* jsonValuesEqualSteps(left, right) {
    if (left === right) return true;
    if (left === null || right === null || typeof left !== typeof right || typeof left !== "object") return false;
    if (Array.isArray(left) !== Array.isArray(right)) return false;
    const leftKeys = Object.keys(left), rightKeys = Object.keys(right);
    if (leftKeys.length !== rightKeys.length) return false;
    for (const key of leftKeys) {
      if (!Object.prototype.hasOwnProperty.call(right, key) || !(yield* jsonValuesEqualSteps(left[key], right[key]))) return false;
      yield 1;
    }
    return true;
  }

  function* cloneCompactImportMetadataSteps(value, active = new Set(), omitImportMeta = false, createRecord = () => ({})) {
    if (!value || typeof value !== "object") return value;
    if (active.has(value)) fail("invalid_payload", "The payload must be finite, acyclic JSON data.");
    active.add(value);
    if (Array.isArray(value)) {
      const result = new Array(value.length);
      for (let index = 0; index < value.length; index++) {
        if (index in value) result[index] = yield* cloneCompactImportMetadataSteps(value[index], active, false, createRecord);
        yield 1;
      }
      active.delete(value);
      return result;
    }
    const result = createRecord(), sharedChildrenSet = new Set(importedVectorChildren(value));
    for (const [key, entry] of Object.entries(value)) {
      if (omitImportMeta && key === "importMeta") continue;
      if (key === "objects" && Array.isArray(entry)) {
        result.objects = [];
        for (const child of entry) {
          const compactChild = sharedChildrenSet.has(child);
          const copy = yield* cloneCompactImportMetadataSteps(child, active, compactChild, createRecord);
          if (compactChild) {
            const overrides = createRecord(), removed = [];
            for (const field of Object.keys(value.importMeta || {})) {
              if (!Object.prototype.hasOwnProperty.call(child.importMeta || {}, field)) removed.push(field);
              yield 1;
            }
            for (const [field, fieldValue] of Object.entries(child.importMeta || {})) {
              if (!Object.prototype.hasOwnProperty.call(value.importMeta || {}, field)
                  || !(yield* jsonValuesEqualSteps(value.importMeta[field], fieldValue))) {
                Object.defineProperty(overrides, field, {value: fieldValue, enumerable: true, writable: true, configurable: true});
              }
              yield 1;
            }
            const reference = createRecord();
            Object.defineProperties(reference, {
              schema: {value: SHARED_GROUP_IMPORT_META_SCHEMA, enumerable: true, writable: true, configurable: true},
              groupId: {value: String(value.groupId || value.importMeta.importBatchId || ""), enumerable: true, writable: true, configurable: true},
              overrides: {value: yield* cloneCompactImportMetadataSteps(overrides, active, false, createRecord), enumerable: true, writable: true, configurable: true},
              removed: {value: removed, enumerable: true, writable: true, configurable: true}
            });
            copy.importMeta = reference;
          }
          result.objects.push(copy);
          yield 1;
        }
      } else Object.defineProperty(result, key, {value: yield* cloneCompactImportMetadataSteps(entry, active, false, createRecord), enumerable: true, writable: true, configurable: true});
      yield 1;
    }
    active.delete(value);
    return result;
  }

  async function compactSharedGroupImportMetadataAsync(value, {yieldEvery = 128, yieldToUi = () => new Promise(resolve => setTimeout(resolve, 0)), maxSliceMs = 8, signal, createRecord = () => ({})} = {}) {
    if (!Number.isSafeInteger(yieldEvery) || yieldEvery < 1 || typeof yieldToUi !== "function" || !Number.isFinite(maxSliceMs) || maxSliceMs <= 0 || typeof createRecord !== "function") throw new Error("Project metadata capture requires bounded batches, a yield callback and a record factory.");
    async function run(steps) {
      let count = 0, started = performance.now();
      while (true) {
        if (signal?.aborted) throw signal.reason || new Error("Project metadata capture was cancelled.");
        const step = steps.next();
        if (step.done) return step.value;
        if (++count % yieldEvery === 0 || performance.now() - started >= maxSliceMs) { await yieldToUi(); started = performance.now(); }
      }
    }
    return await run(containsCompactableImportGroupSteps(value)) ? run(cloneCompactImportMetadataSteps(value, new Set(), false, createRecord)) : value;
  }

  function resolveSharedGroupImportMetaReference(reference, parentGroup) {
    if (!isRecordLike(reference) || typeof reference.schema !== "string"
      || !reference.schema.startsWith(SHARED_GROUP_IMPORT_META_SCHEMA_PREFIX)) return null;
    if (reference.schema !== SHARED_GROUP_IMPORT_META_SCHEMA) {
      fail("unsupported_import_meta_reference", `Unsupported saved vector metadata reference version: ${reference.schema}.`);
    }
    const parentMeta = parentGroup?.importMeta;
    const groupId = String(parentGroup?.groupId || "");
    const metadataBatchId = String(parentMeta?.importBatchId || "");
    if (groupId && metadataBatchId && groupId !== metadataBatchId) {
      fail("unresolved_import_meta_reference", "A saved vector group has conflicting source identities.");
    }
    const parentId = groupId || metadataBatchId;
    if (
      !isRecordLike(parentMeta)
      || parentMeta.editablePanelImport !== true
      || parentMeta.editableObjectImport !== true
      || !parentId
      || String(reference.groupId || "") !== parentId
      || !isRecordLike(reference.overrides)
      || !Array.isArray(reference.removed)
    ) {
      fail("unresolved_import_meta_reference", "A saved vector object refers to missing group source metadata.");
    }
    const importInfo = { ...parentMeta };
    reference.removed.forEach((key) => {
      if (typeof key !== "string") fail("invalid_import_meta_reference", "A saved vector metadata reference is malformed.");
      delete importInfo[key];
    });
    // Object spread defines own data properties, including a literal __proto__
    // metadata key, without invoking Object.prototype's legacy setter.
    return { ...importInfo, ...reference.overrides };
  }

  function resolveSharedGroupImportMetadataForObjects(objects) {
    const updates = [];
    const visited = new Set();
    const childrenOf = (value) => {
      if (Array.isArray(value?.objects)) return value.objects;
      if (typeof value?.getObjects === "function") {
        const children = value.getObjects();
        return Array.isArray(children) ? children : [];
      }
      return [];
    };
    const visit = (value, parentGroup = null) => {
      if (!value || typeof value !== "object" || visited.has(value)) return;
      visited.add(value);
      const resolved = resolveSharedGroupImportMetaReference(value.importMeta, parentGroup);
      if (resolved) updates.push({ object: value, importMeta: resolved });
      const children = childrenOf(value);
      const groupContext = resolved
        ? { groupId: value.groupId, importMeta: resolved }
        : value;
      children.forEach((child) => visit(child, groupContext));
    };
    (Array.isArray(objects) ? objects : []).forEach(visit);
    return updates;
  }

  function hydrateSharedGroupImportMetadata(value) {
    if (!containsSharedImportMetaReference(value)) return value;
    function visit(current, parentGroup = null) {
      if (Array.isArray(current)) return current.map((entry) => visit(entry, parentGroup));
      if (!isRecordLike(current)) return current;
      const importInfo = resolveSharedGroupImportMetaReference(current.importMeta, parentGroup) || current.importMeta;
      const result = {};
      for (const [key, entry] of Object.entries(current)) {
        Object.defineProperty(result, key, {
          value: key === "importMeta" ? importInfo : key === "objects" && Array.isArray(entry)
            ? entry.map((child) => visit(child, current))
            : visit(entry, null),
          enumerable: true, writable: true, configurable: true
        });
      }
      return result;
    }
    return visit(value);
  }

  function assertWithinSize(value, maxBytes) {
    let text;
    try { text = JSON.stringify(value); }
    catch (_error) { fail("invalid_payload", "The payload must be finite, acyclic JSON data."); }
    if (utf8ByteLength(text) > maxBytes) {
      fail("file_too_large", `Figure Tool files may not exceed ${maxBytes} bytes.`);
    }
  }

  function serializeDocument(projectOrEnvelope, options = {}) {
    if (typeof options === "string") options = { kind: options };
    const sourceEnvelope = isRecord(projectOrEnvelope) && isDocumentPayloadSchema(projectOrEnvelope.schema)
      ? projectOrEnvelope
      : { schema: DOCUMENT_PAYLOAD_SCHEMA, project: projectOrEnvelope };
    const envelope = {
      schema: DOCUMENT_PAYLOAD_SCHEMA,
      project: cloneJson(cloneCompactImportMetadata(sourceEnvelope.project))
    };
    envelope.schema = documentPayloadSchemaForProject(envelope.project);
    validateDocumentEnvelope(envelope, options.kind || "");
    assertWithinSize(envelope, Number(options.maxBytes) > 0 ? Number(options.maxBytes) : MAX_FILE_BYTES);
    return { schema: envelope.schema, project: cloneJson(envelope.project) };
  }

  function normalizedIdentifier(value, label) {
    const id = String(value || "").trim();
    if (!id || id.length > 200 || /[\u0000-\u001f]/.test(id)) fail("invalid_document_id", `${label} must have a valid document ID.`);
    return id;
  }

  function portableView(value = {}, options = {}) {
    if (!isRecord(value)) fail("invalid_view", "Each document view must be an object.");
    const allowedKeys = new Set(["zoom", "panX", "panY"]);
    if (options.strict && Object.keys(value).some((key) => !allowedKeys.has(key))) {
      fail("invalid_view", "Document view state may contain only zoom, panX, and panY.");
    }
    const zoom = value.zoom === undefined ? 1 : Number(value.zoom);
    const panX = value.panX === undefined ? 80 : Number(value.panX);
    const panY = value.panY === undefined ? 80 : Number(value.panY);
    if (![zoom, panX, panY].every(Number.isFinite) || zoom <= 0 || zoom > 64) {
      fail("invalid_view", "Document zoom and pan values must be finite, and zoom must be greater than zero.");
    }
    return { zoom, panX, panY };
  }

  function hasAbsoluteRuntimePath(text) {
    const value = String(text || "").trim();
    return /^[a-z]:[\\/]/i.test(value)
      || /^[\\/]/.test(value)
      || /^file:\/\//i.test(value);
  }

  function literalPdfStringMap(owner, key, entry) {
    const knownMap = owner.representation === "pdfjs-browser-display-font" && ["fontCharToUnicode", "unicodeToFontChar"].includes(key)
      || POSITIONED_PDF_TEXT_SCHEMAS.has(owner.schema) && key === "map";
    return knownMap && isRecord(entry) && Object.values(entry).every(item => typeof item === "string");
  }

  function pdfGlyphRecord(value) {
    return isRecord(value) && typeof value.unicode === "string" && typeof value.fontChar === "string"
      && Number.isInteger(value.charIndex) && value.charIndex >= 0 && Number.isInteger(value.charCount) && value.charCount >= 0
      && Number.isFinite(value.x) && Number.isFinite(value.y);
  }

  function namedPdfInstruction(value) {
    return isRecord(value) && ["gs", "Do"].includes(value.operator) && Array.isArray(value.operands)
      && value.operands.length === 1 && typeof value.operands[0] === "string" && /^\/[^\s()<>\[\]{}%]+$/.test(value.operands[0]);
  }

  function assertPortableWorkspaceValue(value, path = "workspace", seen = new Set(), pathLikeContext = false, literalContext = "") {
    if (typeof value === "string") {
      if (literalContext !== "pdf-name-operand" && pathLikeContext && hasAbsoluteRuntimePath(value)) {
        fail("absolute_path_not_portable", `Workspace projects cannot contain an absolute machine path at ${path}.`);
      }
      return;
    }
    if (!value || typeof value !== "object") return;
    if (seen.has(value)) fail("recursive_workspace", "Workspace projects must be acyclic JSON data.");
    seen.add(value);
    if (Array.isArray(value)) {
      value.forEach((entry, index) => assertPortableWorkspaceValue(entry, `${path}[${index}]`, seen, pathLikeContext, literalContext));
      seen.delete(value);
      return;
    }
    for (const [key, entry] of Object.entries(value)) {
      // Glyph dictionaries contain literal text, including slash and backslash,
      // rather than resources. Non-string entries keep the recursive guards.
      if (literalPdfStringMap(value, key, entry)) continue;
      // This typed edit descriptor stores a human-readable action label, not
      // an Undo stack. Only its literal string survives this narrow context;
      // runtime siblings and malformed labels retain the recursive guards.
      if (literalContext === "pdf-edit-descriptor" && value.schema === "figureStudio.pdfNativeEditDescriptor.v1"
          && key === "history_label" && typeof entry === "string") continue;
      const normalizedKey = key.toLowerCase().replace(/[^a-z0-9]/g, "");
      if (
        RUNTIME_KEYS.has(normalizedKey)
        || normalizedKey.startsWith("history")
        || normalizedKey.startsWith("runtime")
        || normalizedKey.startsWith("session")
      ) {
        fail("runtime_state_not_portable", `Workspace projects cannot contain runtime state at ${path}.${key}.`);
      }
      const literalText = typeof entry === "string" && (
        value.schema === "figureStudio.svgPositionedText.v1" && ["sourceText", "sourceGlyphText"].includes(key)
        || POSITIONED_PDF_TEXT_SCHEMAS.has(value.schema) && key === "text"
        || literalContext === "pdf-glyph" && pdfGlyphRecord(value) && ["unicode", "fontChar"].includes(key));
      const pathLikeKey = !literalText && (/(path|file|directory|location|uri|source|target|runtime|repo|worktree)/.test(normalizedKey)
        || /(?:src|url|href)$/.test(normalizedKey));
      if (pathLikeKey && typeof entry === "string" && hasAbsoluteRuntimePath(entry)) {
        fail("absolute_path_not_portable", `Workspace projects cannot contain an absolute machine path at ${path}.${key}.`);
      }
      let childContext = "";
      if (value.schema === "figureStudio.pdfNativeEditPlan.v1" && key === "edit_descriptors" && Array.isArray(entry)) childContext = "pdf-edit-descriptor";
      if (POSITIONED_PDF_TEXT_SCHEMAS.has(value.schema) && key === "glyphs" && Array.isArray(entry)) childContext = "pdf-glyph";
      if (value.schema === "figureStudio.pdfKnockout.v1" && key === "members" && Array.isArray(entry)) childContext = "pdf-knockout-member";
      if ((value.schema === "figureStudio.pdfKnockout.v1" || literalContext === "pdf-knockout-member") && key === "instructions" && Array.isArray(entry)) childContext = "pdf-instruction";
      // /GS0 and /Fm0 are retained PDF dictionary names, not machine paths.
      if (literalContext === "pdf-instruction" && key === "operands" && namedPdfInstruction(value)) childContext = "pdf-name-operand";
      assertPortableWorkspaceValue(entry, `${path}.${key}`, seen, literalText ? false : pathLikeContext || pathLikeKey, childContext);
    }
    seen.delete(value);
  }

  function safeDisplayFilename(value, kind) {
    const filename = normalizedFilename(value);
    if (!filename) return "";
    if (filename !== String(value).trim() || /[<>:"|?*\u0000-\u001f]/.test(filename)) {
      fail("invalid_filename", "Workspace document filenames must be display names, not machine paths.");
    }
    const classification = classifyFilename(filename);
    if (classification.format !== "document" || classification.legacy || classification.kind !== kind) {
      fail("extension_kind_mismatch", `Workspace ${kind} filenames must use ${EXTENSIONS[kind]}.`);
    }
    return filename;
  }

  function sourceWorkspaceBucket(source, kind) {
    return source?.workspaces?.[kind] || source?.[kind] || {};
  }

  function sourceWorkspaceTabs(source, kind) {
    const bucket = sourceWorkspaceBucket(source, kind);
    if (Array.isArray(bucket.tabs)) return bucket.tabs;
    if (Array.isArray(bucket.tabOrder) && Array.isArray(source.documents)) {
      const byId = new Map(source.documents.map((document) => [String(document?.id || ""), document]));
      return bucket.tabOrder.map((id) => byId.get(String(id || "")));
    }
    return [];
  }

  function canonicalWorkspaceFromSource(source) {
    if (!isRecord(source)) fail("invalid_workspace", "Workspace project data must be an object.");
    const activeKind = normalizeKind(source.activeKind);
    if (!activeKind) fail("invalid_active_kind", "The active workspace must be Figure or Presentation.");
    const output = {
      schema: WORKSPACE_SCHEMA,
      activeKind,
      workspaces: {
        figure: { activeId: "", tabOrder: [] },
        presentation: { activeId: "", tabOrder: [] }
      },
      documents: []
    };
    for (const kind of DOCUMENT_KINDS) {
      const bucket = sourceWorkspaceBucket(source, kind);
      const tabs = sourceWorkspaceTabs(source, kind);
      const activeId = String(bucket.activeId || "").trim();
      for (const tab of tabs) {
        if (!isRecord(tab)) fail("invalid_workspace_document", `The ${kind} tab order refers to a missing document.`);
        const id = normalizedIdentifier(tab.id, `${kind} document`);
        const payload = serializeDocument(tab.payload || tab.project, { kind });
        output.workspaces[kind].tabOrder.push(id);
        output.documents.push({
          id,
          kind,
          title: String(tab.title || payload.project.title || "").trim().slice(0, 200),
          filename: safeDisplayFilename(tab.filename || "", kind),
          payload: { schema: payload.schema, project: payload.project },
          view: portableView(tab.view || {})
        });
      }
      output.workspaces[kind].activeId = activeId;
    }
    if (output.documents.some((document) => document.payload.schema === OBJECT_CONNECTOR_DOCUMENT_PAYLOAD_SCHEMA)) output.schema = OBJECT_CONNECTOR_WORKSPACE_SCHEMA;
    return output;
  }

  function validateWorkspaceProject(payload, options = {}) {
    if (!isRecord(payload) || !isWorkspaceSchema(payload.schema)) {
      fail("invalid_workspace_schema", `Expected ${WORKSPACE_SCHEMA}.`);
    }
    const allowedTopKeys = new Set(["schema", "activeKind", "workspaces", "documents"]);
    for (const key of Object.keys(payload)) {
      if (!allowedTopKeys.has(key)) fail("unknown_workspace_field", `Unsupported workspace field: ${key}.`);
    }
    const activeKind = normalizeKind(payload.activeKind);
    if (!activeKind || payload.activeKind !== activeKind) {
      fail("invalid_active_kind", "The active workspace must be Figure or Presentation.");
    }
    if (!isRecord(payload.workspaces) || !Array.isArray(payload.documents) || !payload.documents.length) {
      fail("invalid_workspace", "A workspace project must contain its ordered documents and workspace state.");
    }
    assertReaderEnvelopeVersions(payload);
    const workspaceKeys = Object.keys(payload.workspaces);
    if (workspaceKeys.length !== 2 || !DOCUMENT_KINDS.every((kind) => workspaceKeys.includes(kind))) {
      fail("invalid_workspace", "Workspace state must contain exactly Figure and Presentation collections.");
    }
    const byId = new Map();
    for (const document of payload.documents) {
      if (!isRecord(document)) fail("invalid_workspace_document", "Every workspace document must be an object.");
      const allowedDocumentKeys = new Set(["id", "kind", "title", "filename", "payload", "view"]);
      if (![...allowedDocumentKeys].every((key) => Object.prototype.hasOwnProperty.call(document, key))) {
        fail("invalid_workspace_document", "Each workspace document must include its ID, kind, title, filename, payload, and view.");
      }
      for (const key of Object.keys(document)) {
        if (!allowedDocumentKeys.has(key)) fail("runtime_state_not_portable", `Unsupported workspace document field: ${key}.`);
      }
      const id = normalizedIdentifier(document.id, "Workspace document");
      if (byId.has(id)) fail("duplicate_document_id", `Duplicate workspace document ID: ${id}.`);
      const kind = normalizeKind(document.kind);
      if (!kind || document.kind !== kind) fail("invalid_document_kind", `Workspace document ${id} has an invalid kind.`);
      if (typeof document.title !== "string" || document.title.length > 200 || /[\u0000-\u001f]/.test(document.title)) {
        fail("invalid_document_title", `Workspace document ${id} has an invalid title.`);
      }
      if (typeof document.filename !== "string") fail("invalid_filename", `Workspace document ${id} has an invalid filename.`);
      validateDocumentEnvelope(document.payload, kind);
      safeDisplayFilename(document.filename || "", kind);
      portableView(document.view, { strict: true });
      byId.set(id, { document, kind });
    }
    const orderedIds = new Set();
    for (const kind of DOCUMENT_KINDS) {
      const bucket = payload.workspaces[kind];
      if (
        !isRecord(bucket)
        || Object.keys(bucket).length !== 2
        || Object.keys(bucket).some((key) => !["activeId", "tabOrder"].includes(key))
        || typeof bucket.activeId !== "string"
        || !Array.isArray(bucket.tabOrder)
      ) {
        fail("invalid_workspace_order", `The ${kind} workspace must contain only activeId and tabOrder.`);
      }
      for (const rawId of bucket.tabOrder) {
        const id = normalizedIdentifier(rawId, `${kind} tab order`);
        if (orderedIds.has(id)) fail("duplicate_tab_order_id", `Document ${id} appears more than once in workspace tab order.`);
        const record = byId.get(id);
        if (!record) fail("unknown_tab_order_id", `Workspace tab order refers to unknown document ${id}.`);
        if (record.kind !== kind) fail("workspace_kind_mismatch", `Document ${id} is in the wrong workspace.`);
        orderedIds.add(id);
      }
      const activeId = String(bucket.activeId || "").trim();
      if (bucket.tabOrder.length && !bucket.tabOrder.includes(activeId)) {
        fail("invalid_active_id", `The active ${kind} document is not in its tab order.`);
      }
      if (!bucket.tabOrder.length && activeId) {
        fail("invalid_active_id", `An empty ${kind} workspace cannot have an active document.`);
      }
    }
    if (orderedIds.size !== byId.size) fail("unordered_document", "Every workspace document must appear exactly once in tab order.");
    const expectedDocumentOrder = DOCUMENT_KINDS.flatMap((kind) => payload.workspaces[kind].tabOrder);
    if (payload.documents.some((document, index) => document.id !== expectedDocumentOrder[index])) {
      fail("document_order_mismatch", "Workspace documents must follow the saved Figure and Presentation tab order.");
    }
    if (!payload.workspaces[activeKind].activeId) {
      fail("invalid_active_id", "The active workspace must have an active document.");
    }
    assertPortableWorkspaceValue(payload);
    assertWithinSize(payload, Number(options.maxBytes) > 0 ? Number(options.maxBytes) : MAX_FILE_BYTES);
    return cloneJson(payload, "invalid_workspace");
  }

  function serializeWorkspaceProject(source, options = {}) {
    const candidate = isWorkspaceSchema(source?.schema)
      ? cloneJson(cloneCompactImportMetadata(source), "invalid_workspace")
      : canonicalWorkspaceFromSource(source);
    if (Array.isArray(candidate.documents)) {
      // The candidate is already detached. Change only its version headers;
      // reserializing every document would copy artwork again and strip fields
      // that the existing workspace envelope legitimately retains.
      candidate.documents.forEach((document) => {
        if (isDocumentPayloadSchema(document?.payload?.schema) && isRecord(document.payload.project)) {
          document.payload.schema = documentPayloadSchemaForProject(document.payload.project);
        }
      });
      candidate.schema = candidate.documents.some((document) => document.payload.schema === OBJECT_CONNECTOR_DOCUMENT_PAYLOAD_SCHEMA)
        ? OBJECT_CONNECTOR_WORKSPACE_SCHEMA : WORKSPACE_SCHEMA;
    }
    const validated = validateWorkspaceProject(candidate, options);
    const byId = new Map(validated.documents.map((document) => [document.id, document]));
    validated.documents = DOCUMENT_KINDS.flatMap((kind) =>
      validated.workspaces[kind].tabOrder.map((id) => byId.get(id))
    );
    return validated;
  }

  function parseFile(contents, filename = "", options = {}) {
    if (isRecord(contents) && Object.prototype.hasOwnProperty.call(contents, "contents")) {
      options = filename && typeof filename === "object" ? filename : options;
      filename = contents.name || contents.filename || "";
      contents = contents.contents;
    }
    const nameClassification = classifyFilename(filename);
    if (nameClassification.format === "unknown") {
      fail("unsupported_extension", "Use .fsfigure, .fsdeck, .fsproject, or a supported legacy Figure Tool filename.");
    }
    const maxBytes = Number(options.maxBytes) > 0 ? Number(options.maxBytes) : MAX_FILE_BYTES;
    const text = decodeContents(contents, maxBytes);
    let payload;
    try { payload = JSON.parse(text); }
    catch (_error) { fail("corrupt_json", "The file does not contain valid JSON."); }
    const payloadClassification = classifyPayload(payload, {
      allowHistorical: nameClassification.legacy
    });

    if (nameClassification.format !== payloadClassification.format) {
      fail("extension_payload_mismatch", "The filename does not match the type of Figure Tool content in the file.");
    }
    if (nameClassification.format === "workspace") {
      const workspace = validateWorkspaceProject(payload, { maxBytes });
      const parsedWorkspace = options.deferSharedImportMetadataHydration === true
        ? workspace
        : hydrateWorkspaceSharedImportMetadata(workspace);
      return {
        format: "workspace",
        kind: "workspace",
        filename: nameClassification.filename,
        extension: EXTENSIONS.workspace,
        legacy: false,
        requiresSaveAs: false,
        payload: parsedWorkspace,
        workspace: parsedWorkspace
      };
    }
    const kind = payloadClassification.kind;
    if (!nameClassification.legacy && nameClassification.kind !== kind) {
      fail("extension_kind_mismatch", `Use ${EXTENSIONS[kind]} for this ${kind} document.`);
    }
    if (!nameClassification.legacy && !payloadClassification.envelope) {
      fail("invalid_document_envelope", `New Figure Tool document files must use ${DOCUMENT_PAYLOAD_SCHEMA}.`);
    }
    const documentSource = payloadClassification.legacyShape
      ? (payloadClassification.envelope
        ? { schema: DOCUMENT_PAYLOAD_SCHEMA, project: canonicalLegacyProject(payload.project) }
        : canonicalLegacyProject(payload))
      : payload;
    const documentPayload = serializeDocument(documentSource, { kind, maxBytes });
    const parsedProject = options.deferSharedImportMetadataHydration === true
      ? documentPayload.project
      : hydrateSharedGroupImportMetadata(documentPayload.project);
    return {
      format: "document",
      kind,
      filename: nameClassification.filename,
      extension: nameClassification.extension,
      legacy: nameClassification.legacy,
      requiresSaveAs: nameClassification.requiresSaveAs,
      payload: { schema: documentPayload.schema, project: parsedProject },
      project: parsedProject
    };
  }

  function hydrateWorkspaceSharedImportMetadata(workspace) {
    const hydrated = { ...workspace, documents: workspace.documents.map((document) => ({
      ...document,
      payload: document.payload?.project
        ? { ...document.payload, project: hydrateSharedGroupImportMetadata(document.payload.project) }
        : document.payload
    })) };
    return hydrated;
  }

  return Object.freeze({
    VERSION,
    DOCUMENT_PAYLOAD_SCHEMA,
    OBJECT_CONNECTOR_DOCUMENT_PAYLOAD_SCHEMA,
    DOCUMENT_SCHEMA,
    WORKSPACE_SCHEMA,
    OBJECT_CONNECTOR_WORKSPACE_SCHEMA,
    isDocumentPayloadSchema,
    isWorkspaceSchema,
    requiresObjectConnectorReader,
    documentPayloadSchemaForProject,
    assertReaderEnvelopeVersions,
    MAX_FILE_BYTES,
    LEGACY_OPEN_MINIMUM_BETA_CYCLES,
    DOCUMENT_KINDS,
    EXTENSIONS,
    LEGACY_EXTENSIONS,
    FigureStudioFormatError,
    classifyFilename,
    classifyPayload,
    parseFile,
    serializeDocument,
    serializeWorkspaceProject,
    compactSharedGroupImportMetadata,
    compactSharedGroupImportMetadataAsync,
    hydrateSharedGroupImportMetadata,
    resolveSharedGroupImportMetadataForObjects,
    validateWorkspaceProject
  });
});
