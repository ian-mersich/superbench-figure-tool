(function attachFigureStudioVectorEngine(root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  if (root) root.FigureStudioVectorEngine = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function createFigureStudioVectorEngineApi() {
  "use strict";

  const SCENE_GRAPH_SCHEMA = "figureStudio.vectorSceneGraph.v1";
  const CAPABILITY_SUMMARY_SCHEMA = "figureStudio.vectorEngineCapabilitySummary.v1";
  const TRANSACTION_SCHEMA = "figureStudio.vectorTransaction.v1";
  const TRANSACTION_PLAN_SCHEMA = "figureStudio.vectorTransactionPlan.v1";
  const REQUIREMENT_SCHEMA = "figureStudio.vectorEngineRequirement.v1";
  const TRANSACTION_TYPES = Object.freeze(["replace-path-operands", "set-transform"]);
  const TRANSACTION_TYPE_SET = new Set(TRANSACTION_TYPES);

  const CLASSIFICATIONS = Object.freeze({
    EDITABLE: "editable",
    PRESERVED_SOURCE: "preserved-source",
    UNSUPPORTED: "unsupported"
  });

  const TRANSFORM_FIELDS = Object.freeze([
    "left",
    "top",
    "scaleX",
    "scaleY",
    "angle",
    "skewX",
    "skewY",
    "transformMatrix"
  ]);
  const NUMERIC_TRANSFORM_FIELDS = new Set(TRANSFORM_FIELDS.filter((field) => field !== "transformMatrix"));
  const TRANSFORM_DEFAULTS = Object.freeze({
    left: 0,
    top: 0,
    scaleX: 1,
    scaleY: 1,
    angle: 0,
    skewX: 0,
    skewY: 0,
    transformMatrix: null
  });

  const EDITABLE_FABRIC_TYPES = new Set([
    "arc",
    "circle",
    "ellipse",
    "group",
    "image",
    "itext",
    "i-text",
    "fabrictext",
    "line",
    "path",
    "polygon",
    "polyline",
    "rect",
    "text",
    "textbox",
    "triangle"
  ]);
  const EDITABLE_FIGURE_TYPES = new Set([
    "compoundpath",
    "connector",
    "connectorlabel",
    "group",
    "image",
    "path",
    "pdf",
    "shape",
    "text"
  ]);
  const PATH_FABRIC_TYPES = new Set(["path"]);
  const TEXT_FABRIC_TYPES = new Set(["text", "textbox", "itext", "i-text", "fabrictext"]);
  const EDITABLE_PDF_IMPORT_MODES = new Set([
    "pdf-editable-vector-objects",
    "pdf-local-svg-vector-objects",
    "pdf-js-svg-vector",
    "pdf-lightweight-edit-part",
    "pymupdf-svg-vector",
    "pdf-page-1-rasterized",
    "pymupdf-svg-raster-fallback",
    "embedded-raster-vector-trace",
    "embedded-raster-vector-trace-part",
    "embedded-raster-vector-trace-region",
    "embedded-raster-vector-region"
  ]);
  const PRESERVED_PDF_IMPORT_MODES = new Set([
    "pdf-placed-page-1",
    "pdf-text-raster-hybrid",
    "pdf-lightweight-edit-panel",
    "dense-svg-proxy",
    "converted-pdf-svg-proxy",
    "source-backed-vector-proxy"
  ]);
  const MUTATING_OPERATIONS = new Set([
    "crop-image",
    "duplicate",
    "edit-clipping-path",
    "edit-text",
    "group",
    "release-clipping-mask",
    "release-compound-path",
    "reorder",
    "replace-image",
    "replace-path-operands",
    "set-transform",
    "style",
    "ungroup"
  ]);
  const BASIC_FINITE_GEOMETRY_FIELDS = Object.freeze([
    "width", "height", "radius", "rx", "ry", "x1", "y1", "x2", "y2"
  ]);
  const FABRIC_PATH_FRAME_FIELDS = Object.freeze(["path", "width", "height", "pathOffset", "left", "top"]);
  const TRUSTED_GRAPHS = new WeakSet();
  const VALIDATION_CACHE = new WeakMap();
  const TRUSTED_INVERSE_REQUIREMENT_RESTORES = new WeakMap();
  const TRUSTED_TRANSACTION_PLANS = new WeakMap();

  class VectorEngineError extends Error {
    constructor(code, message, details) {
      super(message);
      this.name = "VectorEngineError";
      this.code = code;
      if (details !== undefined) this.details = details;
    }
  }

  function fail(code, message, details) {
    throw new VectorEngineError(code, message, details);
  }

  function timingNow() {
    return typeof globalThis !== "undefined" && typeof globalThis.performance?.now === "function"
      ? globalThis.performance.now()
      : Date.now();
  }

  function hasOwn(value, key) {
    return Object.prototype.hasOwnProperty.call(value, key);
  }

  function isRecord(value) {
    return Boolean(value) && typeof value === "object" && !Array.isArray(value);
  }

  function nonEmptyText(value) {
    if (value == null) return "";
    return String(value).trim();
  }

  function firstText(...values) {
    for (const value of values) {
      const text = nonEmptyText(value);
      if (text) return text;
    }
    return "";
  }

  function cloneSnapshotValue(value, state, path) {
    if (value === null || typeof value === "string" || typeof value === "boolean" || typeof value === "undefined") return value;
    if (typeof value === "number") {
      if (!Number.isFinite(value)) fail("INVALID_NUMBER", `Fabric snapshot number at ${path} must be finite.`);
      return value;
    }
    if (typeof value === "bigint" || typeof value === "function" || typeof value === "symbol") {
      fail("INVALID_SNAPSHOT", `Fabric snapshot value at ${path} is not JSON-compatible.`);
    }
    if (state.active.has(value)) fail("GRAPH_CYCLE", `Fabric snapshot contains a cycle at ${path}.`);
    if (state.clones.has(value)) return state.clones.get(value);

    const prototype = Object.getPrototypeOf(value);
    if (!Array.isArray(value) && prototype !== Object.prototype && prototype !== null) {
      fail("INVALID_SNAPSHOT", `Fabric snapshot value at ${path} must be a plain object.`);
    }

    const output = Array.isArray(value) ? new Array(value.length) : {};
    state.clones.set(value, output);
    state.active.add(value);
    for (const key of Object.keys(value)) {
      output[key] = cloneSnapshotValue(value[key], state, `${path}.${key}`);
    }
    state.active.delete(value);
    return output;
  }

  function cloneSnapshot(value) {
    return cloneSnapshotValue(value, { active: new WeakSet(), clones: new WeakMap() }, "$snapshot");
  }

  function validateFiniteSnapshotNumbers(value) {
    const stack = [{ value, path: "$snapshot" }];
    const seen = new WeakSet();
    while (stack.length) {
      const current = stack.pop();
      if (typeof current.value === "number") {
        if (!Number.isFinite(current.value)) {
          fail("INVALID_NUMBER", `Fabric snapshot number at ${current.path} must be finite.`);
        }
        continue;
      }
      if (!current.value || typeof current.value !== "object" || seen.has(current.value)) continue;
      seen.add(current.value);
      for (const key of Object.keys(current.value)) {
        stack.push({ value: current.value[key], path: `${current.path}.${key}` });
      }
    }
  }

  function deepFreeze(value, seen = new WeakSet()) {
    if (!value || typeof value !== "object" || seen.has(value)) return value;
    seen.add(value);
    Object.freeze(value);
    for (const key of Object.keys(value)) deepFreeze(value[key], seen);
    return value;
  }

  function stableSerialize(value, state = { active: new WeakSet() }) {
    if (value === null) return "null";
    if (value === undefined) return '"$undefined"';
    if (typeof value === "string" || typeof value === "boolean") return JSON.stringify(value);
    if (typeof value === "number") {
      if (Number.isNaN(value)) return '"$number:NaN"';
      if (value === Number.POSITIVE_INFINITY) return '"$number:+Infinity"';
      if (value === Number.NEGATIVE_INFINITY) return '"$number:-Infinity"';
      if (Object.is(value, -0)) return '"$number:-0"';
      return String(value);
    }
    if (typeof value === "bigint") return JSON.stringify(`$bigint:${value.toString()}`);
    if (typeof value === "function" || typeof value === "symbol") {
      fail("INVALID_VALUE", "A deterministic digest cannot include functions or symbols.");
    }
    if (state.active.has(value)) fail("GRAPH_CYCLE", "A deterministic digest cannot include a cyclic value.");
    state.active.add(value);
    let serialized;
    if (Array.isArray(value)) {
      const items = [];
      for (let index = 0; index < value.length; index += 1) {
        items.push(hasOwn(value, index) ? stableSerialize(value[index], state) : '"$array-hole"');
      }
      serialized = `[${items.join(",")}]`;
    } else {
      const keys = Object.keys(value).sort();
      serialized = `{${keys.map((key) => `${JSON.stringify(key)}:${stableSerialize(value[key], state)}`).join(",")}}`;
    }
    state.active.delete(value);
    return serialized;
  }

  function dual32Hash(text) {
    let fnv = 0x811c9dc5;
    let djb = 0x9e3779b9;
    for (let index = 0; index < text.length; index += 1) {
      const code = text.charCodeAt(index);
      fnv = Math.imul(fnv ^ code, 0x01000193) >>> 0;
      djb = (Math.imul(djb, 33) ^ code) >>> 0;
    }
    return `${fnv.toString(16).padStart(8, "0")}${djb.toString(16).padStart(8, "0")}`;
  }

  function deterministicDigest(value) {
    if (value?.schema === SCENE_GRAPH_SCHEMA && TRUSTED_GRAPHS.has(value)) return value.snapshotDigest;
    const target = value?.schema === SCENE_GRAPH_SCHEMA && value?.payload?.fabricSnapshot
      ? value.payload.fabricSnapshot
      : value;
    return `dual32:${dual32Hash(stableSerialize(target))}`;
  }

  function normalizedFabricType(object) {
    return nonEmptyText(object?.type).toLowerCase();
  }

  function normalizedFigureType(object) {
    return nonEmptyText(object?.figureType).toLowerCase();
  }

  function isPathLikeObject(object) {
    return PATH_FABRIC_TYPES.has(normalizedFabricType(object))
      || normalizedFigureType(object) === "compoundpath"
      || Array.isArray(object?.path);
  }

  function sourceIdentityForObject(object) {
    const source = isRecord(object?.source) ? object.source : {};
    const importMeta = isRecord(object?.importMeta) ? object.importMeta : {};
    const objectProvenance = isRecord(object?.provenance) ? object.provenance : {};
    const provenance = isRecord(importMeta.bsdResultProvenance)
      ? importMeta.bsdResultProvenance
      : isRecord(importMeta.bsd_result_provenance) ? importMeta.bsd_result_provenance : {};
    const artifact = isRecord(object?.artifactRef)
      ? object.artifactRef
      : isRecord(object?.artifact_ref)
        ? object.artifact_ref
        : isRecord(importMeta.artifactRef)
          ? importMeta.artifactRef
          : isRecord(importMeta.artifact_ref) ? importMeta.artifact_ref : {};
    return {
      kind: firstText(source.kind, importMeta.sourceKind, importMeta.source_kind),
      sourceId: firstText(
        source.sourceId,
        source.source_id,
        source.id,
        importMeta.sourceId,
        importMeta.source_id,
        source.sourceResultId,
        source.source_result_id,
        source.result_id,
        importMeta.sourceResultId,
        importMeta.source_result_id,
        provenance.result_id,
        object?.source_result_id,
        objectProvenance.result_id
      ),
      filename: firstText(source.filename, importMeta.sourceFilename, importMeta.source_filename),
      artifactId: firstText(
        artifact.artifact_id,
        artifact.artifactId,
        source.artifact_id,
        source.artifactId,
        provenance.artifact_id
      ),
      resultId: firstText(
        source.result_id,
        source.resultId,
        source.source_result_id,
        source.sourceResultId,
        importMeta.result_id,
        importMeta.resultId,
        importMeta.sourceResultId,
        importMeta.source_result_id,
        provenance.result_id,
        object?.source_result_id,
        objectProvenance.result_id
      ),
      moduleId: firstText(
        source.module_id,
        source.moduleId,
        source.source_module_id,
        source.sourceModuleId,
        importMeta.sourceModuleId,
        importMeta.source_module_id,
        provenance.module_id,
        object?.source_module_id,
        objectProvenance.module_id
      ),
      hasEmbeddedPayload: Boolean(
        importMeta.sourcePdfDataUrl
        || importMeta.source_pdf_data_url
        || importMeta.sourceSvgText
        || importMeta.source_svg_text
        || source.data_url
        || source.dataUrl
      )
    };
  }

  function pdfIdentityForObject(object) {
    const importMeta = isRecord(object?.importMeta) ? object.importMeta : {};
    const source = isRecord(object?.source) ? object.source : {};
    const denseMeta = isRecord(object?.denseSvgProxyLayerMeta) ? object.denseSvgProxyLayerMeta : {};
    const manifest = isRecord(object?.pdfEditabilityManifest)
      ? object.pdfEditabilityManifest
      : isRecord(importMeta.pdfEditabilityManifest)
        ? importMeta.pdfEditabilityManifest
        : isRecord(importMeta.pdf_editability_manifest) ? importMeta.pdf_editability_manifest : {};
    const conversion = isRecord(object?.pdfConversionMeta)
      ? object.pdfConversionMeta
      : isRecord(importMeta.convertedPdf)
        ? importMeta.convertedPdf
        : isRecord(importMeta.converted_pdf) ? importMeta.converted_pdf : {};
    const sourceId = firstText(
      object?.pdfSourceId,
      importMeta.pdfSourceId,
      importMeta.pdf_source_id,
      importMeta.sourcePdfObjectId,
      importMeta.source_pdf_object_id,
      manifest.source_id,
      manifest.pdf_source_id,
      conversion.pdfSourceId,
      conversion.pdf_source_id,
      source.pdfSourceId,
      source.pdf_source_id
    );
    const nativeSourceObjectId = firstText(
      object?.nativePdfSourceObjectId,
      importMeta.nativePdfSourceObjectId,
      importMeta.native_pdf_source_object_id
    );
    const descriptorId = firstText(
      object?.pdfTextDescriptorId,
      object?.pdfTextNativeNodeId,
      importMeta.pdfTextDescriptorId,
      importMeta.pdf_text_descriptor_id,
      object?.nativePdfDescriptorId,
      object?.native_pdf_descriptor_id,
      denseMeta.materialization_native_descriptor_id,
      denseMeta.materializationNativeDescriptorId
    );
    const rawPageNumber = object?.pdfSourcePageNumber
      ?? importMeta.pdfSourcePageNumber
      ?? importMeta.pdf_source_page_number
      ?? importMeta.pageNumber
      ?? importMeta.page;
    const pageNumber = rawPageNumber == null || rawPageNumber === "" ? null : Number(rawPageNumber);
    return {
      sourceId,
      pageNumber: Number.isFinite(pageNumber) && pageNumber >= 1 ? pageNumber : null,
      nativeSourceObjectId,
      descriptorId,
      importMode: firstText(importMeta.importMode, importMeta.import_mode),
      sourceBacked: false
    };
  }

  function artifactProvenancePresent(object, importMeta, source) {
    const provenance = isRecord(importMeta.bsdResultProvenance)
      ? importMeta.bsdResultProvenance
      : isRecord(importMeta.bsd_result_provenance) ? importMeta.bsd_result_provenance : {};
    const importProvenanceIsResult = Boolean(
      provenance.result_id
      || provenance.source_result_id
      || provenance.module_id
      || provenance.source_module_id
    );
    return Boolean(
      source.artifact_path
      || importMeta.artifactPath
      || importMeta.artifact_path
      || (importProvenanceIsResult && (provenance.artifact_id || provenance.artifact_path))
    );
  }

  function nestedPdfMetadataPresent(object, importMeta, pdfIdentity) {
    const manifest = object?.pdfEditabilityManifest
      || importMeta.pdfEditabilityManifest
      || importMeta.pdf_editability_manifest;
    const editPlan = object?.nativePdfEditPlan
      || importMeta.nativePdfEditPlan
      || importMeta.native_pdf_edit_plan
      || manifest?.native_pdf_edit_plan;
    const conversion = object?.pdfConversionMeta
      || importMeta.convertedPdf
      || importMeta.converted_pdf;
    const dense = importMeta.denseSvgProxy
      || importMeta.dense_svg_proxy;
    const advancedProxy = object?.denseSvgAdvancedFeatureProxyMeta
      || importMeta.advancedSvgNativeProxyLayer
      || importMeta.advanced_svg_native_proxy_layer
      || manifest?.advanced_feature_native_proxy
      || importMeta.advancedFeatureProxy
      || importMeta.advanced_feature_proxy;
    const nativeTree = importMeta.nativePdfDescriptorTree
      || importMeta.native_pdf_descriptor_tree
      || conversion?.nativePdfDescriptorTree
      || conversion?.native_pdf_descriptor_tree
      || dense?.nativePdfDescriptorTree
      || dense?.native_pdf_descriptor_tree
      || manifest?.native_pdf_descriptor_tree;
    const mode = firstText(importMeta.importMode, importMeta.import_mode).toLowerCase();
    const sourceType = firstText(importMeta.sourceType, importMeta.source_type, conversion?.sourceType, conversion?.source_type);
    const explicitlyEditable = EDITABLE_PDF_IMPORT_MODES.has(mode);
    const explicitlyPreserved = PRESERVED_PDF_IMPORT_MODES.has(mode)
      || /(?:source-backed|proxy|placed-page|preserve-only|passthrough)/i.test(mode);
    const explicitPreservationFlag = Boolean(
      importMeta.sourceBacked
      || importMeta.source_backed
      || importMeta.pdfPassthrough
      || importMeta.pdf_passthrough
      || importMeta.preserveOnly
      || importMeta.preserve_only
      || manifest?.preserve_only
      || manifest?.preserveOnly
      || manifest?.native_object_writing === "unavailable"
      || manifest?.nativeObjectWriting === "unavailable"
    );
    if (explicitlyPreserved || explicitPreservationFlag || advancedProxy) return true;
    // Editable SVG/vector PDF imports deliberately retain source identity,
    // conversion receipts, and sometimes source bytes. Those fields inform
    // export/provenance; they do not make the Fabric representation opaque.
    if (explicitlyEditable || isRecord(object?.denseSvgProxyLayerMeta)) return false;
    return Boolean(
      importMeta.sourcePdfDataUrl
      || importMeta.source_pdf_data_url
      || importMeta.sourcePdfEmbedded
      || importMeta.source_pdf_embedded
      || nativeTree
      || manifest
      || editPlan
      || conversion
      || dense
      || advancedProxy
      || /pdf|converted_pdf/i.test(sourceType)
    );
  }

  function proxyPanelIsEnabled(value) {
    if (!isRecord(value)) return false;
    return value.proxy_enabled !== false && value.proxyEnabled !== false;
  }

  function proxyPanelMetadata(object, importMeta = isRecord(object?.importMeta) ? object.importMeta : {}) {
    return isRecord(object?.proxyPanel)
      ? object.proxyPanel
      : isRecord(importMeta.proxyPanel)
        ? importMeta.proxyPanel
        : isRecord(importMeta.proxy_panel) ? importMeta.proxy_panel : null;
  }

  function sourceBackingReasons(object, pdfIdentity, sourceIdentity) {
    const importMeta = isRecord(object?.importMeta) ? object.importMeta : {};
    const source = isRecord(object?.source) ? object.source : {};
    const provenance = isRecord(importMeta.bsdResultProvenance)
      ? importMeta.bsdResultProvenance
      : isRecord(importMeta.bsd_result_provenance) ? importMeta.bsd_result_provenance : {};
    const proxyPanel = proxyPanelMetadata(object, importMeta);
    const reasons = [];
    const resultIdentityPresent = Boolean(
      source.result_id
      || source.source_result_id
      || source.sourceResultId
      || source.module_id
      || source.source_module_id
      || importMeta.sourceResultId
      || importMeta.source_result_id
      || importMeta.sourceModuleId
      || importMeta.source_module_id
      || provenance.result_id
      || provenance.module_id
      || object?.source_result_id
      || object?.source_module_id
      || source.kind === "bsd-saved-result"
    );
    if (nestedPdfMetadataPresent(object, importMeta, pdfIdentity)) reasons.push("retained-pdf-source-not-decomposed");
    if (resultIdentityPresent) reasons.push("linked-result-source");
    if (artifactProvenancePresent(object, importMeta, source)) reasons.push("artifact-provenance-retained");
    if (
      proxyPanelIsEnabled(proxyPanel)
      || object?.denseSvgAdvancedFeatureProxyMeta
      || importMeta.advancedSvgNativeProxyLayer
      || importMeta.advanced_svg_native_proxy_layer
      || importMeta.advancedFeatureProxy
      || importMeta.advanced_feature_proxy
      || /(?:source-backed|dense-svg-proxy|converted-pdf-svg-proxy)/i.test(pdfIdentity.importMode)
    ) reasons.push("source-backed-proxy");
    if (
      isRecord(object?.figureStudioLinkedPanel)
      && object.figureStudioLinkedPanel.released !== true
      && object.figureStudioLinkedPanel.detached !== true
      && firstText(object.figureStudioLinkedPanel.status).toLowerCase() !== "released"
    ) reasons.push("linked-panel-source");
    if (
      object?.referenceMeta?.reference_only
      || object?.referenceMeta?.referenceOnly
      || importMeta.reference_only
      || importMeta.referenceOnly
      || source.kind === "reference-only"
      || normalizedFigureType(object) === "reference"
      || /reference-image/i.test(firstText(importMeta.importMode, importMeta.import_mode))
    ) reasons.push("reference-only-source");
    if (
      importMeta.sourceBacked
      || importMeta.source_backed
      || importMeta.sourceBackedFeatures
      || importMeta.source_backed_features
      || /(?:saved-result|linked-result|reference-only)/i.test(sourceIdentity.kind)
    ) reasons.push("linked-source-object");
    if (/unavailable|preserve-only/i.test(firstText(importMeta.nativeObjectEditing, importMeta.native_object_editing))) {
      reasons.push("native-object-writing-unavailable");
    }
    return [...new Set(reasons)].sort();
  }

  function isAuthoredClippingMaskObject(object) {
    return Boolean(
      object?.clipPath
      && object?.figureStudioClipMaskMeta?.schema === "figureStudio.clippingMask.v1"
      && object?.figureStudioClipMaskMeta?.authored === true
    );
  }

  function isDerivedPathObject(object) {
    const figureType = normalizedFigureType(object);
    const component = isRecord(object?.figureStudioComponentInstance) ? object.figureStudioComponentInstance : null;
    const style = isRecord(object?.styleMeta) ? object.styleMeta : {};
    const hasLineVectorGeometry = ["lineVectorStartX", "lineVectorStartY", "lineVectorEndX", "lineVectorEndY"]
      .some((field) => hasOwn(object || {}, field) || hasOwn(style, field));
    return Boolean(
      object?.smartConnectorMeta
      || figureType === "smartconnector"
      || figureType === "connectorlabel"
      || object?.figureStudioLiveBooleanMeta
      || object?.figureStudioLiveBooleanRole
      || object?.figureStudioAnnotationMeta
      || object?.scientificCalloutMeta
      || hasLineVectorGeometry
      || componentBindingIsProtected(component)
    );
  }

  function componentBindingIsProtected(component) {
    if (!component || component.detached === true) return false;
    const hasOverrides = isRecord(component.overrides) && Object.keys(component.overrides).length > 0;
    return component.override !== true && component.legacyOverride !== true && !hasOverrides;
  }

  function hasEditableRawPath(object) {
    if (!Array.isArray(object?.path) || isDerivedPathObject(object)) return false;
    const fabricType = normalizedFabricType(object);
    const figureType = normalizedFigureType(object);
    return fabricType === "path" || figureType === "path" || figureType === "compoundpath";
  }

  function descendantMutationBlockReasons(object) {
    const initial = [];
    if (Array.isArray(object?.objects)) initial.push(...object.objects);
    if (isRecord(object?.clipPath)) initial.push(object.clipPath);
    if (isRecord(object?.mask)) initial.push(object.mask);
    const stack = initial;
    const seen = new Set();
    const reasons = [];
    while (stack.length) {
      const current = stack.pop();
      if (!isRecord(current) || seen.has(current)) continue;
      seen.add(current);
      if (current.locked === true) reasons.push("locked-descendant");
      if (isRecord(current.figureStudioMasterInheritance)) {
        reasons.push("master-inherited-descendant");
      }
      const component = isRecord(current.figureStudioComponentInstance) ? current.figureStudioComponentInstance : null;
      if (componentBindingIsProtected(component)) reasons.push("component-bound-descendant");
      if (current.figureStudioLiveBooleanMeta || current.figureStudioLiveBooleanRole) reasons.push("live-boolean-descendant");
      if (current.smartConnectorMeta || ["smartconnector", "connectorlabel"].includes(normalizedFigureType(current))) {
        reasons.push("smart-connector-descendant");
      }
      if (sourceBackingReasons(current, pdfIdentityForObject(current), sourceIdentityForObject(current)).length) {
        reasons.push("protected-source-descendant");
      }
      if (Array.isArray(current.objects)) stack.push(...current.objects);
      if (isRecord(current.clipPath)) stack.push(current.clipPath);
      if (isRecord(current.mask)) stack.push(current.mask);
    }
    return [...new Set(reasons)].sort();
  }

  function directMutationBlockReasons(object, context = {}) {
    const reasons = [];
    const component = isRecord(object?.figureStudioComponentInstance) ? object.figureStudioComponentInstance : null;
    const structureRole = firstText(object?.figureStudioStructureRole).toLowerCase();
    if (object?.locked === true || object?.figureStudioLayerLockOverride === true || context.layerLocked === true) {
      reasons.push("locked-object-or-layer");
    }
    if (object?.visible === false || object?.figureStudioLayerVisibilityOverride === false || context.layerHidden === true) {
      reasons.push("hidden-object-or-layer");
    }
    if (isRecord(object?.figureStudioMasterInheritance)) {
      reasons.push("master-inherited");
    }
    if (componentBindingIsProtected(component)) reasons.push("component-bound");
    if (object?.figureStudioLiveBooleanMeta || object?.figureStudioLiveBooleanRole) reasons.push("live-boolean-derived");
    if (object?.smartConnectorMeta || ["smartconnector", "connectorlabel"].includes(normalizedFigureType(object))) {
      reasons.push("smart-connector-derived");
    }
    if (
      ["image-frame-content", "image-frame-boundary", "image-frame-clip"].includes(structureRole)
      || object?.figureStudioAreaTextFrameClip === true
    ) reasons.push("internal-derived-structure");
    reasons.push(...descendantMutationBlockReasons(object));
    return [...new Set([...(context.inheritedMutationBlockReasons || []), ...reasons])].sort();
  }

  function directPathSourceProtection(object) {
    const importMeta = isRecord(object?.importMeta) ? object.importMeta : {};
    const conversion = object?.pdfConversionMeta || importMeta.convertedPdf || importMeta.converted_pdf;
    const importMode = firstText(importMeta.importMode, importMeta.import_mode).toLowerCase();
    const explicitlyEditablePdf = EDITABLE_PDF_IMPORT_MODES.has(importMode);
    const durablyReleasedForPathEditing = Boolean(
      importMeta.releasedForPathEditing === true
      || importMeta.released_for_path_editing === true
      || importMeta.sourceDetached === true
      || importMeta.source_detached === true
      || importMeta.detachedFromSource === true
      || importMeta.detached_from_source === true
      || object?.figureStudioLinkedPanel?.detached === true
      || object?.figureStudioLinkedPanel?.released === true
    );
    const denseLayer = isRecord(object?.denseSvgProxyLayerMeta) ? object.denseSvgProxyLayerMeta : null;
    const denseLayerIsEditable = denseLayer?.schema === "figureStudio.denseSvgEditableLayer.v1"
      || explicitlyEditablePdf;
    const manifest = object?.pdfEditabilityManifest
      || importMeta.pdfEditabilityManifest
      || importMeta.pdf_editability_manifest;
    return Boolean(
      importMeta.sourcePdfDataUrl
      || importMeta.source_pdf_data_url
      || (!durablyReleasedForPathEditing
        && Array.isArray(object?.path)
        && firstText(object?.pdfSourceId, importMeta.pdfSourceId, importMeta.pdf_source_id))
      || importMeta.pdfPassthrough
      || importMeta.pdf_passthrough
      || object?.nativePdfSourceObjectId
      || importMeta.nativePdfSourceObjectId
      || importMeta.native_pdf_source_object_id
      || object?.nativePdfEditPlan
      || importMeta.nativePdfEditPlan
      || importMeta.native_pdf_edit_plan
      || manifest?.native_pdf_descriptor_tree
      || importMeta.nativePdfDescriptorTree
      || importMeta.native_pdf_descriptor_tree
      || conversion?.nativePdfDescriptorTree
      || conversion?.native_pdf_descriptor_tree
      || importMeta.denseSvgProxy
      || importMeta.dense_svg_proxy
      || (denseLayer && !denseLayerIsEditable)
      || proxyPanelIsEnabled(proxyPanelMetadata(object, importMeta))
    );
  }

  function editableOperationsForObject(object, context = {}) {
    const operations = ["duplicate", "group", "inspect", "reorder", "select", "set-transform", "style"];
    const fabricType = normalizedFabricType(object);
    if (hasEditableRawPath(object) && context.pathEditingSourceProtected !== true) operations.push("replace-path-operands");
    if (TEXT_FABRIC_TYPES.has(fabricType)) operations.push("edit-text");
    if (fabricType === "image") operations.push("crop-image", "replace-image");
    if (fabricType === "group" || Array.isArray(object?.objects)) operations.push("ungroup");
    if (isAuthoredClippingMaskObject(object)) operations.push("edit-clipping-path", "release-clipping-mask");
    if (normalizedFigureType(object) === "compoundpath" || object?.figureStudioCompoundPathMeta) {
      operations.push("release-compound-path");
    }
    const unique = [...new Set(operations)].sort();
    return context.mutationBlockReasons?.length
      ? unique.filter((operation) => !MUTATING_OPERATIONS.has(operation))
      : unique;
  }

  function classifyFabricObject(object, context = {}) {
    if (!isRecord(object)) fail("INVALID_OBJECT", "A Fabric object must be a plain object.");
    const fabricType = normalizedFabricType(object);
    const figureType = normalizedFigureType(object);
    const sourceIdentity = sourceIdentityForObject(object);
    const pdfIdentity = pdfIdentityForObject(object);
    const sourceReasons = sourceBackingReasons(object, pdfIdentity, sourceIdentity);
    const mutationBlockReasons = directMutationBlockReasons(object, context);
    if (context.explicitEditableOverlay === true) {
      for (const reason of ["retained-pdf-source-not-decomposed", "ancestor-source-backed"]) {
        let index = sourceReasons.indexOf(reason);
        while (index >= 0) {
          sourceReasons.splice(index, 1);
          index = sourceReasons.indexOf(reason);
        }
      }
    } else if (context.sourceBackedAncestor === true) sourceReasons.push("ancestor-source-backed");
    const normalizedSourceReasons = [...new Set(sourceReasons)].sort();
    const recognized = EDITABLE_FABRIC_TYPES.has(fabricType)
      || EDITABLE_FIGURE_TYPES.has(figureType)
      || (Array.isArray(object.objects) && !fabricType);
    let classification;
    let operationAllowlist;
    let reasons;
    if (normalizedSourceReasons.length) {
      classification = CLASSIFICATIONS.PRESERVED_SOURCE;
      operationAllowlist = ["export-preserved-source", "inspect", "preserve-roundtrip", "select"];
      reasons = normalizedSourceReasons;
    } else if (recognized) {
      classification = CLASSIFICATIONS.EDITABLE;
      operationAllowlist = editableOperationsForObject(object, { ...context, mutationBlockReasons });
      reasons = [...mutationBlockReasons];
      if (Array.isArray(object.path) && context.pathEditingSourceProtected === true) {
        reasons.push("path-editing-source-protected");
      } else if (Array.isArray(object.path) && isDerivedPathObject(object)) {
        reasons.push("derived-path-operands");
      }
      reasons = [...new Set(reasons)].sort();
    } else {
      classification = CLASSIFICATIONS.UNSUPPORTED;
      operationAllowlist = ["inspect", "preserve-roundtrip", "select"];
      reasons = [fabricType || figureType
        ? `unsupported-fabric-object-type:${fabricType || figureType}`
        : "missing-fabric-object-type"];
    }
    return deepFreeze({
      classification,
      operationAllowlist,
      transactionAllowlist: operationAllowlist.filter((operation) => TRANSACTION_TYPE_SET.has(operation)),
      reasons,
      kind: figureType || fabricType || "unknown",
      role: firstText(context.role) || "object",
      sourceBacked: classification === CLASSIFICATIONS.PRESERVED_SOURCE,
      sourceId: sourceIdentity.sourceId,
      pdfSourceId: pdfIdentity.sourceId
    });
  }

  function explicitNodeId(object) {
    return firstText(object?.figureId, object?.objectId, object?.object_id, object?.nodeId, object?.node_id, object?.id);
  }

  function isExplicitEditableSourceOverlay(object, parentObject) {
    if (!isRecord(object) || !isRecord(parentObject)) return false;
    const role = firstText(object.denseSvgOverlayRole, object.pdfLightweightRole).toLowerCase();
    const representation = firstText(object.pdfTextRepresentation).toLowerCase();
    const objectMeta = isRecord(object.importMeta) ? object.importMeta : {};
    const objectMode = firstText(objectMeta.importMode, objectMeta.import_mode).toLowerCase();
    const parentMeta = isRecord(parentObject.importMeta) ? parentObject.importMeta : {};
    const parentMode = firstText(parentMeta.importMode, parentMeta.import_mode).toLowerCase();
    return Boolean(
      isRecord(object.denseSvgOverlay)
      || /^overlay(?:-|$)/.test(role)
      || (hasOwn(object, "denseSvgOverlayRole") && ["text", "annotation"].includes(role))
      || objectMeta.lightweightEditOverlay === true
      || objectMeta.lightweight_edit_overlay === true
      || objectMode === "pdf-lightweight-edit-part"
      || representation === "editable-text"
      || (TEXT_FABRIC_TYPES.has(normalizedFabricType(object)) && parentMode === "pdf-text-raster-hybrid")
    );
  }

  function automaticNodeId(sourcePath) {
    return `@fsve:${sourcePath.map((part) => String(part).replace(/[%/]/g, (token) => `%${token.charCodeAt(0).toString(16)}`)).join("/")}`;
  }

  function validateFiniteNumber(value, label) {
    if (typeof value !== "number" || !Number.isFinite(value)) {
      fail("INVALID_NUMBER", `${label} must be a finite number.`);
    }
    return value;
  }

  function validateTransformMatrix(value, label, allowNull = true) {
    if (value == null && allowNull) return null;
    if (!Array.isArray(value) || value.length !== 6) {
      fail("INVALID_NUMBER", `${label} must contain exactly six finite numbers.`);
    }
    return value.map((item, index) => validateFiniteNumber(item, `${label}[${index}]`));
  }

  function normalizedTransform(object, label) {
    const transform = {};
    for (const field of TRANSFORM_FIELDS) {
      if (field === "transformMatrix") {
        transform[field] = hasOwn(object, field) && object[field] != null
          ? validateTransformMatrix(object[field], `${label}.${field}`).slice()
          : null;
      } else if (hasOwn(object, field)) {
        transform[field] = validateFiniteNumber(object[field], `${label}.${field}`);
      } else {
        transform[field] = TRANSFORM_DEFAULTS[field];
      }
    }
    return transform;
  }

  function validatePath(object, label) {
    if (!hasOwn(object, "path")) return { commandCount: 0, operandCount: 0 };
    if (!Array.isArray(object.path)) {
      if (isRecord(object.path) && TEXT_FABRIC_TYPES.has(normalizedFabricType(object))) {
        return { commandCount: 0, operandCount: 0 };
      }
      if (normalizedFabricType(object) === "path" || ["path", "compoundpath"].includes(normalizedFigureType(object))) {
        fail("INVALID_PATH", `${label}.path must be an array.`);
      }
      return { commandCount: 0, operandCount: 0 };
    }
    let operandCount = 0;
    object.path.forEach((command, commandIndex) => {
      if (!Array.isArray(command) || !command.length || typeof command[0] !== "string" || !command[0].trim()) {
        fail("INVALID_PATH", `${label}.path[${commandIndex}] must begin with a path command.`);
      }
      for (let operandIndex = 1; operandIndex < command.length; operandIndex += 1) {
        validateFiniteNumber(command[operandIndex], `${label}.path[${commandIndex}][${operandIndex}]`);
        operandCount += 1;
      }
    });
    return { commandCount: object.path.length, operandCount };
  }

  function validateFiniteGeometry(object, label) {
    for (const field of BASIC_FINITE_GEOMETRY_FIELDS) {
      if (hasOwn(object, field) && object[field] != null) validateFiniteNumber(object[field], `${label}.${field}`);
    }
    if (object.pathOffset != null) {
      if (!isRecord(object.pathOffset)) fail("INVALID_NUMBER", `${label}.pathOffset must be an object with finite x and y values.`);
      if (hasOwn(object.pathOffset, "x")) validateFiniteNumber(object.pathOffset.x, `${label}.pathOffset.x`);
      if (hasOwn(object.pathOffset, "y")) validateFiniteNumber(object.pathOffset.y, `${label}.pathOffset.y`);
    }
    if (object.points != null) {
      if (!Array.isArray(object.points)) fail("INVALID_NUMBER", `${label}.points must be an array.`);
      object.points.forEach((point, pointIndex) => {
        if (!isRecord(point)) fail("INVALID_NUMBER", `${label}.points[${pointIndex}] must be an object.`);
        validateFiniteNumber(point.x, `${label}.points[${pointIndex}].x`);
        validateFiniteNumber(point.y, `${label}.points[${pointIndex}].y`);
      });
    }
  }

  function layerStatesForSnapshot(snapshot) {
    const state = isRecord(snapshot?.objectLayers)
      ? snapshot.objectLayers
      : isRecord(snapshot?.object_layers) ? snapshot.object_layers : {};
    const byId = new Map();
    for (const layer of Array.isArray(state.layers) ? state.layers : []) {
      const id = firstText(layer?.id);
      if (id) byId.set(id, layer);
    }
    return byId;
  }

  function scalarLayerMetadata(object, rootLayerId, layerState) {
    const declaredId = firstText(object?.figureStudioLayerId);
    const effectiveId = firstText(rootLayerId, declaredId);
    return {
      id: declaredId,
      effectiveId,
      inherited: Boolean(effectiveId && effectiveId !== declaredId),
      visible: layerState ? layerState.visible !== false : null,
      locked: layerState ? layerState.locked === true : null,
      visibilityOverride: typeof object?.figureStudioLayerVisibilityOverride === "boolean"
        ? object.figureStudioLayerVisibilityOverride
        : null,
      lockOverride: typeof object?.figureStudioLayerLockOverride === "boolean"
        ? object.figureStudioLayerLockOverride
        : null
    };
  }

  function compoundSourceIds(object) {
    const meta = isRecord(object?.figureStudioCompoundPathMeta) ? object.figureStudioCompoundPathMeta : {};
    const values = [];
    for (const item of Array.isArray(meta.sourceObjectIds) ? meta.sourceObjectIds : []) {
      const id = nonEmptyText(item);
      if (id) values.push(id);
    }
    for (const item of Array.isArray(meta.members) ? meta.members : []) {
      const id = firstText(item?.id, item?.figureId, item?.sourceObjectId);
      if (id) values.push(id);
    }
    return [...new Set(values)];
  }

  function normalizePendingRequirements(value, nodeIndexById) {
    if (value == null) return [];
    if (!Array.isArray(value)) fail("INVALID_GRAPH", "Scene graph pendingRequirements must be an array.");
    const seen = new Set();
    const normalized = value.map((requirement, index) => {
      if (!isRecord(requirement)
        || requirement.schema !== REQUIREMENT_SCHEMA
        || requirement.type !== "fabric-path-frame-rebuild") {
        fail("INVALID_GRAPH", `Scene graph pending requirement ${index} is not supported.`);
      }
      const nodeId = firstText(requirement.nodeId);
      if (!nodeId || !hasOwn(nodeIndexById, nodeId)) {
        fail("BROKEN_REFERENCE", `Pending Fabric path-frame requirement ${index} has a missing node.`);
      }
      if (seen.has(nodeId)) fail("INVALID_GRAPH", `Node "${nodeId}" repeats a pending Fabric path-frame requirement.`);
      seen.add(nodeId);
      const changedOperandCount = Number(requirement.changedOperandCount);
      if (!Number.isInteger(changedOperandCount) || changedOperandCount < 1) {
        fail("INVALID_GRAPH", `Pending Fabric path-frame requirement for "${nodeId}" needs a positive changedOperandCount.`);
      }
      return {
        schema: REQUIREMENT_SCHEMA,
        type: "fabric-path-frame-rebuild",
        nodeId,
        changedOperandCount,
        affectedFields: [...FABRIC_PATH_FRAME_FIELDS]
      };
    });
    return normalized.sort((left, right) => left.nodeId.localeCompare(right.nodeId));
  }

  function importBatchIdForObject(object, owningParentId) {
    const explicit = firstText(object?.importMeta?.importBatchId, object?.importMeta?.import_batch_id);
    if (explicit) return explicit;
    const legacyGroupId = firstText(object?.groupId);
    return legacyGroupId && legacyGroupId !== firstText(owningParentId) ? legacyGroupId : "";
  }

  function projectedCapabilityForObject(object, parentState, parentObject, role, layerStates) {
    const declaredLayerId = firstText(object?.figureStudioLayerId);
    const inheritedRootLayerId = parentState ? firstText(parentState.rootLayerId) : "";
    const rootLayerId = parentState ? inheritedRootLayerId : declaredLayerId;
    const effectiveLayerId = firstText(rootLayerId, declaredLayerId);
    const layerState = effectiveLayerId ? layerStates.get(effectiveLayerId) || null : null;
    const sourceBackedAncestor = parentState?.sourceBacked === true;
    const explicitEditableOverlay = sourceBackedAncestor && isExplicitEditableSourceOverlay(object, parentObject);
    const inheritedMutationBlockReasons = (parentState?.mutationBlockReasons || []).filter((reason) => (
      !explicitEditableOverlay || reason !== "ancestor-protected-source-descendant"
    ));
    if (role === "text-path") inheritedMutationBlockReasons.push("text-path-derived");
    const mutationBlockReasons = directMutationBlockReasons(object, {
      inheritedMutationBlockReasons,
      layerLocked: layerState?.locked === true,
      layerHidden: layerState?.visible === false
    });
    const pathEditingSourceProtected = parentState?.pathSourceProtected === true
      || directPathSourceProtection(object)
      || (sourceBackedAncestor && explicitEditableOverlay);
    const classification = classifyFabricObject(object, {
      role,
      sourceBackedAncestor,
      explicitEditableOverlay,
      pathEditingSourceProtected,
      inheritedMutationBlockReasons,
      layerLocked: layerState?.locked === true,
      layerHidden: layerState?.visible === false
    });
    const inheritedForChildren = mutationBlockReasons.map((reason) => (
      reason.startsWith("ancestor-") ? reason : `ancestor-${reason}`
    ));
    return {
      classification,
      layer: scalarLayerMetadata(object, rootLayerId, layerState),
      stateForChildren: {
        sourceBacked: classification.classification === CLASSIFICATIONS.PRESERVED_SOURCE,
        pathSourceProtected: pathEditingSourceProtected
          || classification.classification === CLASSIFICATIONS.PRESERVED_SOURCE,
        mutationBlockReasons: [...new Set(inheritedForChildren)].sort(),
        rootLayerId: effectiveLayerId
      }
    };
  }

  function projectFabricSnapshot(snapshot, options = {}) {
    if (!isRecord(snapshot)) fail("INVALID_SNAPSHOT", "Fabric snapshot must be an object.");
    if (snapshot.objects != null && !Array.isArray(snapshot.objects)) {
      fail("INVALID_SNAPSHOT", "Fabric snapshot objects must be an array.");
    }

    // The complete source is cloned once and retained only here. Normalized nodes
    // intentionally carry scalar indexes and identities rather than source payloads.
    const fabricSnapshot = cloneSnapshot(snapshot);
    const roots = Array.isArray(fabricSnapshot.objects) ? fabricSnapshot.objects : [];
    const nodes = [];
    const nodeIndexById = Object.create(null);
    const rootIds = [];
    const claimedObjects = new WeakMap();
    const activeObjects = new WeakSet();
    const layerStates = layerStatesForSnapshot(fabricSnapshot);

    const visit = (object, sourcePath, parentId, parentRelation, order, depth, ancestorContext, parentObject) => {
      if (!isRecord(object)) fail("INVALID_OBJECT", `Fabric object at ${sourcePath.join(".")} must be an object.`);
      if (activeObjects.has(object)) fail("GRAPH_CYCLE", `Fabric object hierarchy contains a cycle at ${sourcePath.join(".")}.`);
      if (claimedObjects.has(object)) {
        fail("INVALID_GRAPH", `Fabric object at ${sourcePath.join(".")} is owned by more than one relationship.`);
      }
      activeObjects.add(object);
      claimedObjects.set(object, sourcePath);

      const id = explicitNodeId(object) || automaticNodeId(sourcePath);
      if (hasOwn(nodeIndexById, id)) fail("DUPLICATE_NODE_ID", `Duplicate vector node id "${id}".`);
      const label = `node "${id}"`;
      const transform = normalizedTransform(object, label);
      const pathSummary = validatePath(object, label);
      validateFiniteGeometry(object, label);
      const projection = projectedCapabilityForObject(
        object,
        parentId ? ancestorContext : null,
        parentObject,
        parentRelation,
        layerStates
      );
      const classification = projection.classification;
      const sourceIdentity = sourceIdentityForObject(object);
      const pdfIdentity = pdfIdentityForObject(object);
      pdfIdentity.sourceBacked = classification.classification === CLASSIFICATIONS.PRESERVED_SOURCE;

      const node = {
        id,
        explicitId: explicitNodeId(object),
        idStability: explicitNodeId(object) ? "stable-explicit" : "source-path-derived-unstable",
        kind: classification.kind,
        fabricType: normalizedFabricType(object),
        figureType: normalizedFigureType(object),
        name: firstText(object.name),
        parentId: parentId || null,
        parentRelation: parentId ? parentRelation : "root",
        order,
        depth,
        childIds: [],
        clipPathId: null,
        maskId: null,
        textPathId: null,
        declaredGroupId: firstText(object.groupId),
        importBatchId: importBatchIdForObject(object, parentId),
        declaredClipHostId: firstText(object.figureStudioClipHostId),
        isCompoundPath: normalizedFigureType(object) === "compoundpath"
          || object.figureStudioCompoundPathMeta?.schema === "figureStudio.compoundPath.v1",
        compoundSourceIds: compoundSourceIds(object),
        layer: projection.layer,
        sourceIdentity,
        pdfIdentity,
        transform,
        path: pathSummary,
        classification: classification.classification,
        operationAllowlist: [...classification.operationAllowlist],
        transactionAllowlist: [...classification.transactionAllowlist],
        reasons: [...classification.reasons],
        sourcePath: [...sourcePath]
      };
      nodeIndexById[id] = nodes.length;
      nodes.push(node);

      const childContext = projection.stateForChildren;

      const children = object.objects == null ? [] : object.objects;
      if (!Array.isArray(children)) fail("INVALID_GRAPH", `${label}.objects must be an array.`);
      children.forEach((child, childIndex) => {
        const childId = visit(
          child,
          [...sourcePath, "objects", childIndex],
          id,
          "child",
          childIndex,
          depth + 1,
          childContext,
          object
        );
        node.childIds.push(childId);
      });
      if (object.clipPath != null) {
        if (!isRecord(object.clipPath)) fail("INVALID_GRAPH", `${label}.clipPath must be an object.`);
        node.clipPathId = visit(
          object.clipPath,
          [...sourcePath, "clipPath"],
          id,
          "clip-path",
          0,
          depth + 1,
          childContext,
          object
        );
      }
      if (object.mask != null) {
        if (!isRecord(object.mask)) fail("INVALID_GRAPH", `${label}.mask must be an object.`);
        node.maskId = visit(
          object.mask,
          [...sourcePath, "mask"],
          id,
          "mask",
          0,
          depth + 1,
          childContext,
          object
        );
      }
      if (isRecord(object.path) && TEXT_FABRIC_TYPES.has(normalizedFabricType(object))) {
        node.textPathId = visit(
          object.path,
          [...sourcePath, "path"],
          id,
          "text-path",
          0,
          depth + 1,
          childContext,
          object
        );
      }
      activeObjects.delete(object);
      return id;
    };

    roots.forEach((object, index) => {
      rootIds.push(visit(object, ["objects", index], null, "root", index, 0, {
        sourceBacked: false,
        pathSourceProtected: false,
        mutationBlockReasons: [],
        rootLayerId: ""
      }, null));
    });

    const graph = {
      schema: SCENE_GRAPH_SCHEMA,
      rootIds,
      nodes,
      nodeIndexById,
      payload: { fabricSnapshot },
      pendingRequirements: normalizePendingRequirements(options.pendingRequirements, nodeIndexById),
      snapshotDigest: ""
    };
    const validation = validateSceneGraph(graph);
    graph.snapshotDigest = validation.digest;
    const frozen = deepFreeze(graph);
    TRUSTED_GRAPHS.add(frozen);
    VALIDATION_CACHE.set(frozen, deepFreeze({ ...validation, digest: frozen.snapshotDigest }));
    return frozen;
  }

  function resolveSourcePath(snapshot, sourcePath) {
    let value = snapshot;
    for (const part of sourcePath || []) {
      if (value == null || !hasOwn(value, part)) return undefined;
      value = value[part];
    }
    return value;
  }

  function relationEntries(node) {
    return [
      ...node.childIds.map((id, index) => ({ id, relation: "child", order: index })),
      ...(node.clipPathId ? [{ id: node.clipPathId, relation: "clip-path", order: 0 }] : []),
      ...(node.maskId ? [{ id: node.maskId, relation: "mask", order: 0 }] : []),
      ...(node.textPathId ? [{ id: node.textPathId, relation: "text-path", order: 0 }] : [])
    ];
  }

  function validateSceneGraph(graph) {
    if (TRUSTED_GRAPHS.has(graph) && VALIDATION_CACHE.has(graph)) {
      return { ...VALIDATION_CACHE.get(graph) };
    }
    if (!isRecord(graph) || graph.schema !== SCENE_GRAPH_SCHEMA) {
      fail("INVALID_GRAPH", `Scene graph schema must be "${SCENE_GRAPH_SCHEMA}".`);
    }
    if (!Array.isArray(graph.nodes) || !Array.isArray(graph.rootIds)) {
      fail("INVALID_GRAPH", "Scene graph nodes and rootIds must be arrays.");
    }
    if (!isRecord(graph.nodeIndexById)) fail("INVALID_GRAPH", "Scene graph nodeIndexById must be an object.");
    if (!Array.isArray(graph.pendingRequirements)) {
      fail("INVALID_GRAPH", "Scene graph pendingRequirements must be an array.");
    }
    if (!isRecord(graph.payload) || !isRecord(graph.payload.fabricSnapshot)) {
      fail("INVALID_GRAPH", "Scene graph must retain one Fabric snapshot payload.");
    }
    validateFiniteSnapshotNumbers(graph.payload.fabricSnapshot);

    const byId = new Map();
    graph.nodes.forEach((node, index) => {
      if (!isRecord(node) || !nonEmptyText(node.id)) fail("INVALID_GRAPH", `Scene graph node ${index} requires an id.`);
      if (byId.has(node.id)) fail("DUPLICATE_NODE_ID", `Duplicate vector node id "${node.id}".`);
      byId.set(node.id, node);
      if (graph.nodeIndexById[node.id] !== index) {
        fail("NORMALIZATION_MISMATCH", `Node "${node.id}" has an inconsistent index entry.`);
      }
      if (!Object.values(CLASSIFICATIONS).includes(node.classification)) {
        fail("INVALID_GRAPH", `Node "${node.id}" has an invalid classification.`);
      }
      if (
        !Array.isArray(node.operationAllowlist)
        || !Array.isArray(node.transactionAllowlist)
        || !Array.isArray(node.reasons)
        || !Array.isArray(node.childIds)
      ) {
        fail("INVALID_GRAPH", `Node "${node.id}" has invalid capability or child metadata.`);
      }
      const operationSet = new Set(node.operationAllowlist);
      if (operationSet.size !== node.operationAllowlist.length) {
        fail("INVALID_GRAPH", `Node "${node.id}" repeats an allowed operation.`);
      }
      const transactionSet = new Set(node.transactionAllowlist);
      if (
        transactionSet.size !== node.transactionAllowlist.length
        || node.transactionAllowlist.some((type) => !TRANSACTION_TYPE_SET.has(type) || !operationSet.has(type))
      ) {
        fail("INVALID_GRAPH", `Node "${node.id}" has an invalid transaction allowlist.`);
      }
      for (const field of NUMERIC_TRANSFORM_FIELDS) validateFiniteNumber(node.transform?.[field], `node "${node.id}" transform.${field}`);
      validateTransformMatrix(node.transform?.transformMatrix, `node "${node.id}" transform.transformMatrix`);
      const sourceObject = resolveSourcePath(graph.payload.fabricSnapshot, node.sourcePath);
      if (!isRecord(sourceObject)) fail("BROKEN_REFERENCE", `Node "${node.id}" sourcePath is broken.`);
      validatePath(sourceObject, `node "${node.id}"`);
      normalizedTransform(sourceObject, `node "${node.id}"`);
      validateFiniteGeometry(sourceObject, `node "${node.id}"`);
    });
    if (Object.keys(graph.nodeIndexById).length !== graph.nodes.length) {
      fail("NORMALIZATION_MISMATCH", "Scene graph nodeIndexById contains stale entries.");
    }

    const normalizedRequirements = normalizePendingRequirements(graph.pendingRequirements, Object.fromEntries(
      Array.from(byId.keys(), (id) => [id, true])
    ));
    if (stableSerialize(graph.pendingRequirements) !== stableSerialize(normalizedRequirements)) {
      fail("NORMALIZATION_MISMATCH", "Scene graph pending requirements are not normalized.");
    }

    const rootSet = new Set();
    graph.rootIds.forEach((id, rootIndex) => {
      if (rootSet.has(id)) fail("BROKEN_REFERENCE", `Root node "${id}" is repeated.`);
      rootSet.add(id);
      if (!byId.has(id)) fail("BROKEN_REFERENCE", `Root node "${id}" does not exist.`);
      const node = byId.get(id);
      if (node.parentId != null || node.parentRelation !== "root") {
        fail("BROKEN_REFERENCE", `Root node "${id}" has a parent.`);
      }
      if (node.order !== rootIndex) fail("BROKEN_REFERENCE", `Root node "${id}" has inconsistent root order.`);
    });

    const ownerById = new Map();
    for (const node of graph.nodes) {
      if (node.parentId != null && !byId.has(node.parentId)) {
        fail("BROKEN_REFERENCE", `Node "${node.id}" refers to missing parent "${node.parentId}".`);
      }
      // groupId is also used by Figure Tool as an import-batch/cohort hint.
      // Serialized `objects` remains the sole owning group relationship.
      if (
        node.parentRelation === "clip-path"
        && node.declaredClipHostId
        && node.declaredClipHostId !== node.parentId
      ) {
        fail("BROKEN_REFERENCE", `Node "${node.id}" has an inconsistent clipping host "${node.declaredClipHostId}".`);
      }
      const localRefs = new Set();
      for (const edge of relationEntries(node)) {
        if (localRefs.has(edge.id)) fail("BROKEN_REFERENCE", `Node "${node.id}" repeats child relationship "${edge.id}".`);
        localRefs.add(edge.id);
        const child = byId.get(edge.id);
        if (!child) fail("BROKEN_REFERENCE", `Node "${node.id}" refers to missing ${edge.relation} node "${edge.id}".`);
        if (ownerById.has(edge.id)) {
          fail("BROKEN_REFERENCE", `Node "${edge.id}" has more than one owning relationship.`);
        }
        ownerById.set(edge.id, node.id);
        if (child.parentId !== node.id || child.parentRelation !== edge.relation) {
          fail("BROKEN_REFERENCE", `Node "${edge.id}" has inconsistent parent metadata.`);
        }
        if (edge.relation === "child" && child.order !== edge.order) {
          fail("BROKEN_REFERENCE", `Node "${edge.id}" has inconsistent child order.`);
        }
      }
    }

    const visitState = new Map();
    const visited = new Set();
    const visit = (id) => {
      if (visitState.get(id) === "active") fail("GRAPH_CYCLE", `Scene graph contains a relationship cycle at "${id}".`);
      if (visitState.get(id) === "done") return;
      visitState.set(id, "active");
      for (const edge of relationEntries(byId.get(id))) visit(edge.id);
      visitState.set(id, "done");
      visited.add(id);
    };
    graph.rootIds.forEach(visit);
    for (const id of byId.keys()) {
      if (visitState.get(id) !== "done") visit(id);
    }
    if (visited.size !== graph.nodes.length) fail("BROKEN_REFERENCE", "Scene graph contains unreachable nodes.");

    for (const node of graph.nodes) {
      if (node.parentId == null && !rootSet.has(node.id)) {
        fail("BROKEN_REFERENCE", `Parentless node "${node.id}" is not a root.`);
      }
      if (node.parentId != null && ownerById.get(node.id) !== node.parentId) {
        fail("BROKEN_REFERENCE", `Node "${node.id}" is not owned by its declared parent.`);
      }
    }

    const layerStates = layerStatesForSnapshot(graph.payload.fabricSnapshot);
    const expectedProjectionById = new Map();
    const expectedProjection = (node) => {
      if (expectedProjectionById.has(node.id)) return expectedProjectionById.get(node.id);
      const parentProjection = node.parentId ? expectedProjection(byId.get(node.parentId)) : null;
      const sourceObject = resolveSourcePath(graph.payload.fabricSnapshot, node.sourcePath);
      const parentObject = node.parentId
        ? resolveSourcePath(graph.payload.fabricSnapshot, byId.get(node.parentId).sourcePath)
        : null;
      const expected = projectedCapabilityForObject(
        sourceObject,
        parentProjection?.stateForChildren || null,
        parentObject,
        node.parentRelation,
        layerStates
      );
      expectedProjectionById.set(node.id, expected);
      return expected;
    };
    for (const node of graph.nodes) {
      const projection = expectedProjection(node);
      const expected = projection.classification;
      if (
        node.classification !== expected.classification
        || node.kind !== expected.kind
        || !sameValue(node.operationAllowlist, expected.operationAllowlist)
        || !sameValue(node.transactionAllowlist, expected.transactionAllowlist)
        || !sameValue(node.reasons, expected.reasons)
      ) {
        fail("NORMALIZATION_MISMATCH", `Node "${node.id}" capability metadata does not match its retained Fabric payload.`);
      }
      const sourceObject = resolveSourcePath(graph.payload.fabricSnapshot, node.sourcePath);
      const expectedExplicitId = explicitNodeId(sourceObject);
      const expectedNodeId = expectedExplicitId || automaticNodeId(node.sourcePath);
      const expectedImportBatchId = importBatchIdForObject(sourceObject, node.parentId);
      if (
        node.id !== expectedNodeId
        || node.explicitId !== expectedExplicitId
        || node.idStability !== (expectedExplicitId ? "stable-explicit" : "source-path-derived-unstable")
        || node.importBatchId !== expectedImportBatchId
        || stableSerialize(node.layer) !== stableSerialize(projection.layer)
      ) {
        fail("NORMALIZATION_MISMATCH", `Node "${node.id}" identity or layer metadata does not match its retained Fabric payload.`);
      }
      const expectedTransform = normalizedTransform(sourceObject, `node "${node.id}"`);
      for (const field of TRANSFORM_FIELDS) {
        if (!sameValue(node.transform?.[field], expectedTransform[field])) {
          fail("NORMALIZATION_MISMATCH", `Node "${node.id}" transform metadata does not match its retained Fabric payload.`);
        }
      }
      const expectedPath = validatePath(sourceObject, `node "${node.id}"`);
      if (node.path?.commandCount !== expectedPath.commandCount || node.path?.operandCount !== expectedPath.operandCount) {
        fail("NORMALIZATION_MISMATCH", `Node "${node.id}" path metadata does not match its retained Fabric payload.`);
      }
    }

    const computedDigest = deterministicDigest(graph);
    if (graph.snapshotDigest && graph.snapshotDigest !== computedDigest) {
      fail("NORMALIZATION_MISMATCH", "Scene graph snapshotDigest does not match its retained Fabric payload.");
    }
    return {
      valid: true,
      nodeCount: graph.nodes.length,
      rootCount: graph.rootIds.length,
      digest: computedDigest
    };
  }

  function cloneGraphFabricSnapshot(graph) {
    return cloneSnapshot(graph.payload.fabricSnapshot);
  }

  function toFabricSnapshot(graph, options = {}) {
    if (!TRUSTED_GRAPHS.has(graph)) {
      fail("UNTRUSTED_GRAPH", "Fabric export requires an immutable graph created by this engine instance.");
    }
    validateSceneGraph(graph);
    if (graph.pendingRequirements.length && options.allowPendingFabricFrameRebuild !== true) {
      fail(
        "FABRIC_FRAME_REBUILD_REQUIRED",
        "Path operands changed without rebuilding Fabric width, height, pathOffset, and scene-stable placement.",
        { requirements: graph.pendingRequirements.map((requirement) => ({ ...requirement, affectedFields: [...requirement.affectedFields] })) }
      );
    }
    return cloneGraphFabricSnapshot(graph);
  }

  function classificationForNode(node) {
    if (!isRecord(node) || !Object.values(CLASSIFICATIONS).includes(node.classification)) {
      fail("INVALID_GRAPH", "A normalized vector node is required.");
    }
    return deepFreeze({
      classification: node.classification,
      operationAllowlist: [...node.operationAllowlist],
      transactionAllowlist: [...node.transactionAllowlist],
      reasons: [...node.reasons]
    });
  }

  function summarizeCapabilities(graph) {
    validateSceneGraph(graph);
    const classificationCounts = {
      [CLASSIFICATIONS.EDITABLE]: 0,
      [CLASSIFICATIONS.PRESERVED_SOURCE]: 0,
      [CLASSIFICATIONS.UNSUPPORTED]: 0
    };
    const classificationIds = {
      [CLASSIFICATIONS.EDITABLE]: [],
      [CLASSIFICATIONS.PRESERVED_SOURCE]: [],
      [CLASSIFICATIONS.UNSUPPORTED]: []
    };
    const operationCounts = {};
    const kindCounts = {};
    let groupCount = 0;
    let compoundPathCount = 0;
    let clippingMaskCount = 0;
    let clipPathCount = 0;
    for (const node of graph.nodes) {
      classificationCounts[node.classification] += 1;
      classificationIds[node.classification].push(node.id);
      kindCounts[node.kind] = (kindCounts[node.kind] || 0) + 1;
      for (const operation of node.operationAllowlist) operationCounts[operation] = (operationCounts[operation] || 0) + 1;
      if (node.fabricType === "group" || node.childIds.length) groupCount += 1;
      if (node.isCompoundPath) compoundPathCount += 1;
      if (node.clipPathId) clippingMaskCount += 1;
      if (node.parentRelation === "clip-path") clipPathCount += 1;
    }
    Object.values(classificationIds).forEach((ids) => ids.sort());
    const sortedRecord = (record) => Object.fromEntries(Object.entries(record).sort(([left], [right]) => left.localeCompare(right)));
    return deepFreeze({
      schema: CAPABILITY_SUMMARY_SCHEMA,
      nodeCount: graph.nodes.length,
      rootCount: graph.rootIds.length,
      rootIds: [...graph.rootIds],
      classificationCounts,
      classificationIds,
      operationCounts: sortedRecord(operationCounts),
      kindCounts: sortedRecord(kindCounts),
      relationshipCounts: {
        groups: groupCount,
        compoundPaths: compoundPathCount,
        clippingMasks: clippingMaskCount,
        clipPaths: clipPathCount
      },
      digest: deterministicDigest(graph)
    });
  }

  function nodeById(graph, id) {
    const index = graph?.nodeIndexById?.[id];
    if (Number.isInteger(index) && graph.nodes[index]?.id === id) return graph.nodes[index];
    // Trusted graphs have already validated this index. Avoid turning a rejected
    // command-local target into an accidental whole-scene scan.
    if (TRUSTED_GRAPHS.has(graph)) return null;
    return graph?.nodes?.find((node) => node.id === id) || null;
  }

  function assertEditableOperation(node, operation) {
    if (!node) fail("NODE_NOT_FOUND", "Transaction target node does not exist.");
    if (node.classification !== CLASSIFICATIONS.EDITABLE) {
      fail(
        "NODE_NOT_EDITABLE",
        `Node "${node.id}" is ${node.classification} and cannot apply ${operation}.`,
        { nodeId: node.id, classification: node.classification, reasons: [...node.reasons] }
      );
    }
    if (!node.transactionAllowlist.includes(operation)) {
      fail("OPERATION_NOT_ALLOWED", `Node "${node.id}" does not allow the ${operation} transaction.`);
    }
  }

  function sameValue(left, right) {
    if (Object.is(left, right)) return true;
    if (Array.isArray(left) && Array.isArray(right) && left.length === right.length) {
      return left.every((value, index) => sameValue(value, right[index]));
    }
    return false;
  }

  function canonicalTransformInput(value, label) {
    if (!isRecord(value)) fail("INVALID_TRANSACTION", `${label} must be an object.`);
    const output = {};
    for (const [rawKey, rawValue] of Object.entries(value)) {
      const key = rawKey === "matrix" ? "transformMatrix" : rawKey;
      if (!TRANSFORM_FIELDS.includes(key)) fail("INVALID_TRANSACTION", `${label}.${rawKey} is not a supported transform field.`);
      if (hasOwn(output, key)) fail("OVERLAPPING_EDIT", `${label} repeats transform field "${key}".`);
      if (key === "transformMatrix") output[key] = validateTransformMatrix(rawValue, `${label}.${rawKey}`)?.slice() ?? null;
      else output[key] = validateFiniteNumber(rawValue, `${label}.${rawKey}`);
    }
    return output;
  }

  function effectiveTransformValue(object, field) {
    if (field === "transformMatrix") {
      return hasOwn(object, field) && object[field] != null ? object[field] : null;
    }
    return hasOwn(object, field) ? object[field] : TRANSFORM_DEFAULTS[field];
  }

  function isAncestor(graph, possibleAncestorId, nodeId) {
    let current = nodeById(graph, nodeId);
    const seen = new Set();
    while (current?.parentId) {
      if (seen.has(current.id)) return false;
      seen.add(current.id);
      if (current.parentId === possibleAncestorId) return true;
      current = nodeById(graph, current.parentId);
    }
    return false;
  }

  function planSetTransformTransaction(graph, transaction) {
    const edits = transaction.edits;
    if (!Array.isArray(edits) || !edits.length) fail("INVALID_TRANSACTION", "set-transform requires one or more edits.");
    const operations = [];
    const editedAddresses = new Set();
    const targetIds = [];
    let expectationCheckCount = 0;

    edits.forEach((edit, editIndex) => {
      if (!isRecord(edit)) fail("INVALID_TRANSACTION", `set-transform edit ${editIndex} must be an object.`);
      const nodeId = firstText(edit.nodeId, edit.id);
      const node = nodeById(graph, nodeId);
      if (!node) fail("NODE_NOT_FOUND", `Transaction target node "${nodeId}" does not exist.`);
      assertEditableOperation(node, "set-transform");
      const expected = canonicalTransformInput(edit.expected, `edits[${editIndex}].expected`);
      const hasValue = hasOwn(edit, "value") || hasOwn(edit, "transform") || hasOwn(edit, "next");
      const next = hasValue
        ? canonicalTransformInput(
            hasOwn(edit, "value") ? edit.value : hasOwn(edit, "transform") ? edit.transform : edit.next,
            `edits[${editIndex}].value`
          )
        : {};
      const unset = Array.isArray(edit.unset) ? edit.unset.map((field) => field === "matrix" ? "transformMatrix" : field) : [];
      for (const field of unset) {
        if (!TRANSFORM_FIELDS.includes(field)) fail("INVALID_TRANSACTION", `edits[${editIndex}].unset contains unsupported field "${field}".`);
        if (hasOwn(next, field)) fail("OVERLAPPING_EDIT", `Transform field "${field}" is both set and unset.`);
      }
      const targetFields = [...Object.keys(next), ...unset];
      if (!hasValue && !unset.length) fail("INVALID_TRANSACTION", `set-transform edit ${editIndex} has no values.`);
      if (!targetFields.length) fail("INVALID_TRANSACTION", `set-transform edit ${editIndex} has no target fields.`);

      const rawObject = resolveSourcePath(graph.payload.fabricSnapshot, node.sourcePath);
      for (const [field, expectedValue] of Object.entries(expected)) {
        expectationCheckCount += 1;
        const current = effectiveTransformValue(rawObject, field);
        if (!sameValue(current, expectedValue)) {
          fail("STALE_EXPECTATION", `Node "${nodeId}" transform.${field} no longer matches the expected value.`);
        }
      }
      for (const field of targetFields) {
        if (!hasOwn(expected, field)) {
          fail("INVALID_TRANSACTION", `set-transform requires an expected value for "${field}".`);
        }
        const address = `${nodeId}:${field}`;
        if (editedAddresses.has(address)) fail("OVERLAPPING_EDIT", `Transaction edits "${address}" more than once.`);
        editedAddresses.add(address);
        operations.push({
          node,
          field,
          mode: unset.includes(field) ? "unset" : "set",
          nextValue: next[field],
          previousExists: hasOwn(rawObject, field),
          previousValue: rawObject[field]
        });
      }
      if (!targetIds.includes(nodeId)) targetIds.push(nodeId);
    });

    for (let leftIndex = 0; leftIndex < targetIds.length; leftIndex += 1) {
      for (let rightIndex = leftIndex + 1; rightIndex < targetIds.length; rightIndex += 1) {
        const left = targetIds[leftIndex];
        const right = targetIds[rightIndex];
        if (isAncestor(graph, left, right) || isAncestor(graph, right, left)) {
          fail("OVERLAPPING_EDIT", `set-transform cannot edit ancestor and descendant nodes "${left}" and "${right}" atomically.`);
        }
      }
    }

    return {
      type: "set-transform",
      targetIds,
      operations,
      expectationCheckCount,
      readScope: targetIds.length > 1 ? "targets-and-ancestors" : "targets-only"
    };
  }

  function materializeSetTransformTransaction(graph, prepared) {
    const nextSnapshot = cloneGraphFabricSnapshot(graph);
    for (const operation of prepared.operations) {
      const rawObject = resolveSourcePath(nextSnapshot, operation.node.sourcePath);
      if (operation.mode === "unset") delete rawObject[operation.field];
      else rawObject[operation.field] = Array.isArray(operation.nextValue) ? [...operation.nextValue] : operation.nextValue;
    }

    const inverseByNode = new Map();
    for (const operation of prepared.operations) {
      if (!inverseByNode.has(operation.node.id)) {
        inverseByNode.set(operation.node.id, { nodeId: operation.node.id, expected: {}, value: {}, unset: [] });
      }
      const inverse = inverseByNode.get(operation.node.id);
      const updatedRaw = resolveSourcePath(nextSnapshot, operation.node.sourcePath);
      const expectedAfter = effectiveTransformValue(updatedRaw, operation.field);
      inverse.expected[operation.field] = Array.isArray(expectedAfter) ? [...expectedAfter] : expectedAfter;
      if (operation.previousExists) {
        inverse.value[operation.field] = Array.isArray(operation.previousValue)
          ? [...operation.previousValue]
          : operation.previousValue;
      } else {
        inverse.unset.push(operation.field);
      }
    }
    const inverseEdits = Array.from(inverseByNode.values()).map((edit) => {
      if (!Object.keys(edit.value).length) delete edit.value;
      if (!edit.unset.length) delete edit.unset;
      return edit;
    });
    return {
      nextSnapshot,
      pendingRequirements: graph.pendingRequirements,
      priorPendingRequirements: graph.pendingRequirements,
      inverse: { schema: TRANSACTION_SCHEMA, type: "set-transform", edits: inverseEdits }
    };
  }

  function pathAnchorRows(anchor, label) {
    if (!isRecord(anchor)) fail("INVALID_TRANSACTION", `${label} must be an object.`);
    const commandIndex = Number(anchor.commandIndex ?? anchor.command_index);
    if (!Number.isInteger(commandIndex) || commandIndex < 0) {
      fail("INVALID_TRANSACTION", `${label}.commandIndex must be a non-negative integer.`);
    }
    const expectedValue = hasOwn(anchor, "expected") ? anchor.expected : anchor.expectedOperands;
    const nextValue = hasOwn(anchor, "value") ? anchor.value : hasOwn(anchor, "next") ? anchor.next : anchor.operands;
    let operandIndices;
    let expectedValues;
    let nextValues;
    if (anchor.operandIndex != null || anchor.operand_index != null) {
      operandIndices = [Number(anchor.operandIndex ?? anchor.operand_index)];
      expectedValues = [expectedValue];
      nextValues = [nextValue];
    } else {
      expectedValues = Array.isArray(expectedValue) ? expectedValue : null;
      nextValues = Array.isArray(nextValue) ? nextValue : null;
      if (!expectedValues || !nextValues || expectedValues.length !== nextValues.length || !expectedValues.length) {
        fail("INVALID_TRANSACTION", `${label} must provide equal non-empty expected and value operand arrays.`);
      }
      if (Array.isArray(anchor.operandIndices) || Array.isArray(anchor.operand_indices)) {
        operandIndices = [...(anchor.operandIndices || anchor.operand_indices)].map(Number);
      } else {
        const start = Number(anchor.startOperandIndex ?? anchor.start_operand_index ?? 1);
        if (!Number.isInteger(start) || start < 1) {
          fail("INVALID_TRANSACTION", `${label}.startOperandIndex must be a positive integer.`);
        }
        operandIndices = expectedValues.map((_item, index) => start + index);
      }
      if (operandIndices.length !== expectedValues.length) {
        fail("INVALID_TRANSACTION", `${label}.operandIndices must match the operand value count.`);
      }
    }
    return operandIndices.map((operandIndex, index) => {
      if (!Number.isInteger(operandIndex) || operandIndex < 1) {
        fail("INVALID_TRANSACTION", `${label} operand indexes must be positive integers.`);
      }
      return {
        commandIndex,
        operandIndex,
        expected: validateFiniteNumber(expectedValues[index], `${label}.expected[${index}]`),
        value: validateFiniteNumber(nextValues[index], `${label}.value[${index}]`)
      };
    });
  }

  function planReplacePathOperandsTransaction(graph, transaction) {
    const edits = transaction.edits;
    if (!Array.isArray(edits) || !edits.length) {
      fail("INVALID_TRANSACTION", "replace-path-operands requires one or more edits.");
    }
    const operations = [];
    const addresses = new Set();
    const targetIds = [];
    edits.forEach((edit, editIndex) => {
      if (!isRecord(edit)) fail("INVALID_TRANSACTION", `replace-path-operands edit ${editIndex} must be an object.`);
      const nodeId = firstText(edit.nodeId, edit.id);
      const node = nodeById(graph, nodeId);
      if (!node) fail("NODE_NOT_FOUND", `Transaction target node "${nodeId}" does not exist.`);
      assertEditableOperation(node, "replace-path-operands");
      const rawObject = resolveSourcePath(graph.payload.fabricSnapshot, node.sourcePath);
      if (!Array.isArray(rawObject.path)) fail("INVALID_PATH", `Node "${nodeId}" does not contain editable path operands.`);
      const anchors = Array.isArray(edit.anchors)
        ? edit.anchors
        : Array.isArray(edit.replacements)
          ? edit.replacements
          : (edit.commandIndex != null || edit.command_index != null) ? [edit] : [];
      if (!anchors.length) fail("INVALID_TRANSACTION", `replace-path-operands edit ${editIndex} has no anchors.`);
      anchors.forEach((anchor, anchorIndex) => {
        for (const row of pathAnchorRows(anchor, `edits[${editIndex}].anchors[${anchorIndex}]`)) {
          const command = rawObject.path[row.commandIndex];
          if (!Array.isArray(command) || row.operandIndex >= command.length) {
            fail("INVALID_PATH", `Node "${nodeId}" path operand ${row.commandIndex}:${row.operandIndex} does not exist.`);
          }
          const current = command[row.operandIndex];
          validateFiniteNumber(current, `node "${nodeId}" path operand ${row.commandIndex}:${row.operandIndex}`);
          if (!Object.is(current, row.expected)) {
            fail("STALE_EXPECTATION", `Node "${nodeId}" path operand ${row.commandIndex}:${row.operandIndex} no longer matches the expected value.`);
          }
          const address = `${nodeId}:${row.commandIndex}:${row.operandIndex}`;
          if (addresses.has(address)) fail("OVERLAPPING_EDIT", `Transaction edits path operand "${address}" more than once.`);
          addresses.add(address);
          operations.push({ node, ...row, previousValue: current });
        }
      });
      if (!targetIds.includes(nodeId)) targetIds.push(nodeId);
    });

    return {
      type: "replace-path-operands",
      targetIds,
      operations,
      expectationCheckCount: operations.length,
      readScope: "targets-only"
    };
  }

  function materializeReplacePathOperandsTransaction(graph, prepared) {
    const nextSnapshot = cloneGraphFabricSnapshot(graph);
    for (const operation of prepared.operations) {
      const rawObject = resolveSourcePath(nextSnapshot, operation.node.sourcePath);
      rawObject.path[operation.commandIndex][operation.operandIndex] = operation.value;
    }
    const inverseByNode = new Map();
    for (const operation of prepared.operations) {
      if (!inverseByNode.has(operation.node.id)) inverseByNode.set(operation.node.id, { nodeId: operation.node.id, anchors: [] });
      inverseByNode.get(operation.node.id).anchors.push({
        commandIndex: operation.commandIndex,
        operandIndex: operation.operandIndex,
        expected: operation.value,
        value: operation.previousValue
      });
    }
    const frameRequirementCounts = new Map();
    for (const operation of prepared.operations) {
      const rawObject = resolveSourcePath(graph.payload.fabricSnapshot, operation.node.sourcePath);
      if (
        !Object.is(operation.value, operation.previousValue)
        && (hasOwn(rawObject, "width") || hasOwn(rawObject, "height") || hasOwn(rawObject, "pathOffset"))
      ) {
        frameRequirementCounts.set(operation.node.id, (frameRequirementCounts.get(operation.node.id) || 0) + 1);
      }
    }
    const requirementByNode = new Map(graph.pendingRequirements.map((requirement) => [requirement.nodeId, {
      ...requirement,
      affectedFields: [...requirement.affectedFields]
    }]));
    for (const [nodeId, changedOperandCount] of frameRequirementCounts) {
      const previous = requirementByNode.get(nodeId);
      requirementByNode.set(nodeId, {
        schema: REQUIREMENT_SCHEMA,
        type: "fabric-path-frame-rebuild",
        nodeId,
        changedOperandCount: changedOperandCount + (previous?.changedOperandCount || 0),
        affectedFields: [...FABRIC_PATH_FRAME_FIELDS]
      });
    }
    const pendingRequirements = Array.from(requirementByNode.values()).sort((left, right) => left.nodeId.localeCompare(right.nodeId));
    return {
      nextSnapshot,
      pendingRequirements,
      priorPendingRequirements: graph.pendingRequirements,
      inverse: {
        schema: TRANSACTION_SCHEMA,
        type: "replace-path-operands",
        edits: Array.from(inverseByNode.values())
      }
    };
  }

  function normalizeTransactionType(value) {
    return nonEmptyText(value).trim().toLowerCase().replace(/_/g, "-");
  }

  function assertTrustedTransactionGraph(graph) {
    if (!TRUSTED_GRAPHS.has(graph)) {
      fail(
        "UNTRUSTED_GRAPH",
        "Transactions require an immutable graph created by this engine instance. Reproject the retained Fabric snapshot before applying edits."
      );
    }
  }

  function planTransaction(graph, transaction) {
    assertTrustedTransactionGraph(graph);
    const startedAt = timingNow();
    const validation = validateSceneGraph(graph);
    const validatedAt = timingNow();
    if (!isRecord(transaction)) fail("INVALID_TRANSACTION", "Transaction must be an object.");
    if (transaction.schema && transaction.schema !== TRANSACTION_SCHEMA) {
      fail("INVALID_TRANSACTION", `Transaction schema must be "${TRANSACTION_SCHEMA}".`);
    }
    const beforeDigest = validation.digest;
    if (transaction.expectedDigest && transaction.expectedDigest !== beforeDigest) {
      fail("STALE_EXPECTATION", "Scene graph digest no longer matches the transaction expectation.");
    }
    const type = normalizeTransactionType(transaction.type);
    let prepared;
    if (type === "set-transform") prepared = planSetTransformTransaction(graph, transaction);
    else if (type === "replace-path-operands") prepared = planReplacePathOperandsTransaction(graph, transaction);
    else fail("INVALID_TRANSACTION", `Unsupported transaction type "${nonEmptyText(transaction.type)}".`);
    const completedAt = timingNow();

    const targetCount = prepared.targetIds.length;
    const operationCount = prepared.operations.length;
    const plan = deepFreeze({
      schema: TRANSACTION_PLAN_SCHEMA,
      type,
      beforeDigest,
      targetIds: [...prepared.targetIds],
      targetCount,
      operationCount,
      expectationChecks: {
        digest: Boolean(transaction.expectedDigest),
        targetValues: prepared.expectationCheckCount
      },
      metrics: {
        validationMs: validatedAt - startedAt,
        targetPlanningMs: completedAt - validatedAt,
        totalMs: completedAt - startedAt
      },
      structuralSharing: {
        planningScope: prepared.readScope,
        sourceGraphShared: true,
        fabricSnapshotShared: true,
        targetNodeMetadataShared: true,
        snapshotCloned: false,
        nodeMetadataCloned: 0,
        untouchedNodeCount: graph.nodes.length - targetCount
      }
    });
    TRUSTED_TRANSACTION_PLANS.set(plan, {
      graph,
      prepared,
      restoresPendingRequirements: TRUSTED_INVERSE_REQUIREMENT_RESTORES.has(transaction),
      restoredPendingRequirements: TRUSTED_INVERSE_REQUIREMENT_RESTORES.get(transaction)
    });
    return plan;
  }

  function materializePreparedTransaction(graph, prepared) {
    if (prepared.type === "set-transform") return materializeSetTransformTransaction(graph, prepared);
    if (prepared.type === "replace-path-operands") return materializeReplacePathOperandsTransaction(graph, prepared);
    fail("INVALID_TRANSACTION_PLAN", `Unsupported prepared transaction type "${nonEmptyText(prepared.type)}".`);
  }

  function applyTransactionPlan(graph, plan) {
    assertTrustedTransactionGraph(graph);
    if (!isRecord(plan) || plan.schema !== TRANSACTION_PLAN_SCHEMA || !TRUSTED_TRANSACTION_PLANS.has(plan)) {
      fail(
        "UNTRUSTED_TRANSACTION_PLAN",
        "Transaction commit requires an immutable plan created by this engine instance. Re-plan against the current graph."
      );
    }
    const planState = TRUSTED_TRANSACTION_PLANS.get(plan);
    if (planState.graph !== graph) {
      fail("STALE_EXPECTATION", "Transaction plan was prepared for a different scene graph.");
    }

    const startedAt = timingNow();
    const validation = validateSceneGraph(graph);
    if (validation.digest !== plan.beforeDigest) {
      fail("STALE_EXPECTATION", "Scene graph digest no longer matches the transaction plan.");
    }
    const guardedAt = timingNow();
    const materialized = materializePreparedTransaction(graph, planState.prepared);
    const materializedAt = timingNow();

    // Projection performs complete validation after all edits have been staged. No
    // caller-owned value is changed if any target or expectation fails.
    const restoredPendingRequirements = planState.restoresPendingRequirements
      ? planState.restoredPendingRequirements
      : materialized.pendingRequirements;
    const nextGraph = projectFabricSnapshot(materialized.nextSnapshot, {
      pendingRequirements: restoredPendingRequirements
    });
    const projectedAt = timingNow();
    const inverse = deepFreeze({
      ...materialized.inverse,
      expectedDigest: nextGraph.snapshotDigest
    });
    TRUSTED_INVERSE_REQUIREMENT_RESTORES.set(inverse, materialized.priorPendingRequirements);
    const completedAt = timingNow();
    const commitTotalMs = completedAt - startedAt;
    return deepFreeze({
      graph: nextGraph,
      inverse,
      requirements: nextGraph.pendingRequirements,
      beforeDigest: plan.beforeDigest,
      afterDigest: nextGraph.snapshotDigest,
      plan,
      metrics: {
        targetCount: plan.targetCount,
        operationCount: plan.operationCount,
        planning: { ...plan.metrics },
        commit: {
          graphGuardMs: guardedAt - startedAt,
          snapshotMaterializationMs: materializedAt - guardedAt,
          fullProjectionValidationMs: projectedAt - materializedAt,
          inverseFinalizationMs: completedAt - projectedAt,
          totalMs: commitTotalMs,
          fullSnapshotClone: true,
          fullProjection: true,
          nodeMetadataRebuilt: true
        },
        engineWorkMs: plan.metrics.totalMs + commitTotalMs
      }
    });
  }

  function applyTransaction(graph, transaction) {
    const plan = planTransaction(graph, transaction);
    return applyTransactionPlan(graph, plan);
  }

  return Object.freeze({
    SCENE_GRAPH_SCHEMA,
    CAPABILITY_SUMMARY_SCHEMA,
    TRANSACTION_SCHEMA,
    TRANSACTION_PLAN_SCHEMA,
    REQUIREMENT_SCHEMA,
    TRANSACTION_TYPES,
    CLASSIFICATIONS,
    TRANSFORM_FIELDS,
    VectorEngineError,
    fromFabricSnapshot: projectFabricSnapshot,
    projectFabricSnapshot,
    toFabricSnapshot,
    validate: validateSceneGraph,
    validateSceneGraph,
    summarize: summarizeCapabilities,
    summarizeCapabilities,
    digest: deterministicDigest,
    deterministicDigest,
    digestSceneGraph: deterministicDigest,
    classifyFabricObject,
    classificationForNode,
    planTransaction,
    applyTransactionPlan,
    applyTransaction
  });
});
