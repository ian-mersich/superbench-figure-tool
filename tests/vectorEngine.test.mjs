import assert from "node:assert/strict";
import { createRequire } from "node:module";
import { performance } from "node:perf_hooks";
import test from "node:test";

const require = createRequire(import.meta.url);
const engine = require("../app/vector-engine.js");

const PDF_DATA_URL = "data:application/pdf;base64,JVBERi0xLjQKJUZpZ3VyZVN0dWRpbwo=";

function figureSnapshot() {
  return {
    version: "7.3.1",
    width: 1200,
    height: 800,
    background: "#ffffff",
    customDocumentField: { keep: ["exactly", { value: 17 }] },
    objects: [
      {
        type: "Group",
        figureId: "group-1",
        figureType: "group",
        name: "Editable assay group",
        left: 40,
        top: 55,
        scaleX: 1,
        scaleY: 1,
        angle: 0,
        figureStudioLayerId: "layer-artwork",
        objects: [
          {
            type: "Path",
            figureId: "path-1",
            figureType: "path",
            name: "Response trace",
            groupId: "group-1",
            left: 5,
            top: 6,
            scaleX: 1,
            scaleY: 1,
            path: [
              ["M", 0, 0],
              ["C", 10, 0, 20, 10, 30, 10],
              ["L", 40, 20],
              ["Z"]
            ],
            fill: "",
            stroke: "#176b68",
            source: { kind: "authored-vector", sourceId: "assay-response" }
          },
          {
            type: "Path",
            figureId: "compound-1",
            figureType: "compoundPath",
            name: "Membrane with pore",
            groupId: "group-1",
            left: 90,
            top: 24,
            path: [
              ["M", 0, 0], ["L", 100, 0], ["L", 100, 80], ["L", 0, 80], ["Z"],
              ["M", 30, 20], ["L", 70, 20], ["L", 70, 60], ["L", 30, 60], ["Z"]
            ],
            fillRule: "evenodd",
            figureStudioCompoundPathMeta: {
              schema: "figureStudio.compoundPath.v1",
              fillRule: "evenodd",
              sourceObjectIds: ["source-outer", "source-pore"]
            }
          }
        ]
      },
      {
        type: "Group",
        figureId: "clip-group",
        figureType: "group",
        name: "Microscopy crop",
        left: 360,
        top: 80,
        figureStudioLayerId: "layer-images",
        figureStudioClipMaskMeta: {
          schema: "figureStudio.clippingMask.v1",
          authored: true,
          inverted: false
        },
        objects: [
          {
            type: "Image",
            figureId: "image-1",
            figureType: "image",
            groupId: "clip-group",
            left: 0,
            top: 0,
            width: 320,
            height: 220,
            src: "data:image/png;base64,aW1hZ2U="
          }
        ],
        clipPath: {
          type: "Path",
          figureId: "clip-path-1",
          figureType: "path",
          figureStudioClipHostId: "clip-group",
          absolutePositioned: false,
          path: [["M", 0, 0], ["L", 280, 0], ["L", 280, 180], ["L", 0, 180], ["Z"]]
        }
      },
      {
        type: "Textbox",
        figureId: "text-1",
        figureType: "text",
        name: "Figure title",
        left: 70,
        top: 18,
        groupId: "import-batch-77",
        text: "Treatment response",
        fontFamily: "Arial",
        fontSize: 24,
        figureStudioLayerId: "layer-labels"
      },
      {
        type: "Image",
        figureId: "pdf-page-1",
        figureType: "pdf",
        name: "Source-backed PDF page",
        left: 720,
        top: 80,
        width: 300,
        height: 420,
        importMeta: {
          importMode: "source-backed-vector-proxy",
          sourcePdfDataUrl: PDF_DATA_URL,
          pdfSourceId: "pdf-source-alpha",
          pdfSourcePageNumber: 2,
          pdfPassthrough: true,
          nativeObjectEditing: "unavailable",
          arbitraryWriterPayload: { operators: ["q", "Do", "Q"], xref: 91 }
        },
        source: { kind: "placed-pdf-page", filename: "source-figure.pdf" }
      },
      {
        type: "FutureMeshObject",
        figureId: "unknown-1",
        name: "Future Fabric construct",
        left: 1040,
        top: 100,
        vendorExtension: {
          knots: [[0, 0, 0.25], [1, 1, 0.75]],
          opaque: "must survive"
        }
      }
    ]
  };
}

function byId(graph, id) {
  return graph.nodes[graph.nodeIndexById[id]];
}

function countExactString(value, expected, seen = new WeakSet()) {
  if (value === expected) return 1;
  if (!value || typeof value !== "object" || seen.has(value)) return 0;
  seen.add(value);
  return Object.keys(value).reduce((count, key) => count + countExactString(value[key], expected, seen), 0);
}

function percentile(samples, proportion) {
  const sorted = [...samples].sort((left, right) => left - right);
  return sorted[Math.max(0, Math.ceil(sorted.length * proportion) - 1)];
}

test("projects ordinary groups, paths, compound paths, clipping, text, and images into one normalized graph", () => {
  const graph = engine.fromFabricSnapshot(figureSnapshot());
  const validation = engine.validate(graph);
  assert.deepEqual(validation, {
    valid: true,
    nodeCount: 9,
    rootCount: 5,
    digest: graph.snapshotDigest
  });
  assert.deepEqual(graph.rootIds, ["group-1", "clip-group", "text-1", "pdf-page-1", "unknown-1"]);

  assert.deepEqual(byId(graph, "group-1").childIds, ["path-1", "compound-1"]);
  assert.equal(byId(graph, "path-1").parentId, "group-1");
  assert.equal(byId(graph, "path-1").order, 0);
  assert.equal(byId(graph, "compound-1").order, 1);
  assert.equal(byId(graph, "compound-1").isCompoundPath, true);
  assert.deepEqual(byId(graph, "compound-1").compoundSourceIds, ["source-outer", "source-pore"]);

  assert.deepEqual(byId(graph, "clip-group").childIds, ["image-1"]);
  assert.equal(byId(graph, "clip-group").clipPathId, "clip-path-1");
  assert.equal(byId(graph, "clip-path-1").parentId, "clip-group");
  assert.equal(byId(graph, "clip-path-1").parentRelation, "clip-path");
  assert.equal(byId(graph, "image-1").layer.id, "");
  assert.equal(byId(graph, "text-1").layer.id, "layer-labels");
  assert.equal(byId(graph, "text-1").declaredGroupId, "import-batch-77", "batch hints are non-owning");
  assert.equal(byId(graph, "text-1").importBatchId, "import-batch-77");
  assert.equal(byId(graph, "path-1").importBatchId, "", "an owning group ID is not mislabeled as an import batch");

  for (const id of ["group-1", "path-1", "compound-1", "clip-group", "clip-path-1", "image-1", "text-1"]) {
    assert.equal(byId(graph, id).classification, "editable", id);
  }
  assert.ok(byId(graph, "path-1").operationAllowlist.includes("replace-path-operands"));
  assert.deepEqual(byId(graph, "path-1").transactionAllowlist, ["replace-path-operands", "set-transform"]);
  assert.ok(byId(graph, "text-1").operationAllowlist.includes("edit-text"));
  assert.deepEqual(byId(graph, "text-1").transactionAllowlist, ["set-transform"]);
  assert.ok(byId(graph, "image-1").operationAllowlist.includes("crop-image"));

  const summary = engine.summarize(graph);
  assert.deepEqual(summary.classificationCounts, {
    editable: 7,
    "preserved-source": 1,
    unsupported: 1
  });
  assert.deepEqual(summary.relationshipCounts, {
    groups: 2,
    compoundPaths: 1,
    clippingMasks: 1,
    clipPaths: 1
  });
  assert.equal(summary.digest, graph.snapshotDigest);
  assert.equal(JSON.stringify(summary).includes(PDF_DATA_URL), false);
});

test("source-backed PDF and unknown objects are classified honestly and retained without payload duplication", () => {
  const snapshot = figureSnapshot();
  const graph = engine.fromFabricSnapshot(snapshot);
  const pdf = byId(graph, "pdf-page-1");
  const unknown = byId(graph, "unknown-1");

  assert.equal(pdf.classification, "preserved-source");
  assert.deepEqual(pdf.pdfIdentity, {
    sourceId: "pdf-source-alpha",
    pageNumber: 2,
    nativeSourceObjectId: "",
    descriptorId: "",
    importMode: "source-backed-vector-proxy",
    sourceBacked: true
  });
  assert.ok(pdf.reasons.includes("retained-pdf-source-not-decomposed"));
  assert.ok(pdf.reasons.includes("native-object-writing-unavailable"));
  assert.equal(pdf.operationAllowlist.includes("set-transform"), false);
  assert.equal(unknown.classification, "unsupported");
  assert.match(unknown.reasons[0], /unsupported-fabric-object-type/);
  assert.equal(unknown.operationAllowlist.includes("set-transform"), false);

  assert.equal(countExactString(graph, PDF_DATA_URL), 1, "retained PDF bytes have one graph owner");
  assert.equal(JSON.stringify(pdf).includes(PDF_DATA_URL), false);
  assert.deepEqual(engine.toFabricSnapshot(graph), snapshot);

  assert.throws(
    () => engine.applyTransaction(graph, {
      type: "set-transform",
      edits: [{ nodeId: "pdf-page-1", expected: { left: 720 }, value: { left: 730 } }]
    }),
    (error) => error.code === "NODE_NOT_EDITABLE" && /preserved-source/.test(error.message)
  );
  assert.throws(
    () => engine.applyTransaction(graph, {
      type: "set-transform",
      edits: [{ nodeId: "unknown-1", expected: { left: 1040 }, value: { left: 1050 } }]
    }),
    (error) => error.code === "NODE_NOT_EDITABLE" && /unsupported/.test(error.message)
  );
});

test("app-authoritative result, proxy, linked-panel, reference, and ambiguous PDF metadata fail closed", () => {
  const protectedSnapshot = {
    objects: [
      {
        type: "Rect",
        figureId: "source-aliases",
        source: { source_result_id: "result-17", source_module_id: "bioplot" }
      },
      {
        type: "Rect",
        figureId: "artifact-provenance",
        importMeta: { bsdResultProvenance: { artifact_path: "results/panel.svg", module_id: "bioplot" } }
      },
      {
        type: "Image",
        figureId: "artifact-ref",
        artifact_ref: { artifact_id: "artifact-91", media_type: "image/png" },
        artifactRefs: [{ artifact_id: "artifact-91" }]
      },
      {
        type: "Image",
        figureId: "import-proxy",
        importMeta: {
          proxyPanel: {
            schema: "figureStudio.proxyPanel.v1",
            proxy_enabled: true,
            source_artifact_ref: { artifact_id: "full-image" }
          }
        }
      },
      {
        type: "Group",
        figureId: "linked-panel",
        figureStudioLinkedPanel: {
          schema: "figureStudio.linkedPanel.v1",
          id: "linked-1",
          status: "linked",
          released: false,
          detached: false
        },
        objects: []
      },
      {
        type: "Image",
        figureId: "reference-only",
        referenceMeta: { reference_only: true, source_url_or_id: "microscopy-reference" }
      },
      {
        type: "Path",
        figureId: "nested-pdf-manifest",
        path: [["M", 0, 0], ["L", 10, 10]],
        importMeta: {
          pdf_editability_manifest: {
            schema: "figureStudio.pdfEditabilityManifest.v1",
            source_retained_for_export: true,
            native_pdf_descriptor_tree: { schema: "figureStudio.nativePdfDescriptorTree.v1" }
          }
        }
      },
      {
        type: "Path",
        figureId: "nested-pdf-conversion",
        path: [["M", 0, 0], ["L", 5, 5]],
        importMeta: {
          convertedPdf: {
            sourceType: "converted_pdf_svg",
            nativePdfDescriptorTree: { schema: "figureStudio.nativePdfDescriptorTree.v1" }
          }
        }
      },
      {
        type: "Group",
        figureId: "protected-parent",
        importMeta: { proxy_panel: { schema: "figureStudio.proxyPanel.v1", proxy_enabled: true } },
        objects: [{
          type: "Path",
          figureId: "protected-descendant",
          path: [["M", 0, 0], ["L", 20, 20]]
        }]
      }
    ]
  };
  const graph = engine.fromFabricSnapshot(protectedSnapshot);
  const protectedIds = [
    "source-aliases",
    "artifact-provenance",
    "import-proxy",
    "linked-panel",
    "reference-only",
    "nested-pdf-manifest",
    "nested-pdf-conversion",
    "protected-parent",
    "protected-descendant"
  ];
  for (const id of protectedIds) {
    const node = byId(graph, id);
    assert.equal(node.classification, "preserved-source", node.id);
    assert.equal(node.operationAllowlist.includes("set-transform"), false, node.id);
    assert.equal(node.operationAllowlist.includes("replace-path-operands"), false, node.id);
  }
  assert.ok(byId(graph, "source-aliases").reasons.includes("linked-result-source"));
  assert.ok(byId(graph, "artifact-provenance").reasons.includes("artifact-provenance-retained"));
  assert.equal(byId(graph, "artifact-ref").classification, "editable", "storage artifact refs do not grant or remove edit authority");
  assert.ok(byId(graph, "artifact-ref").operationAllowlist.includes("crop-image"));
  assert.ok(byId(graph, "import-proxy").reasons.includes("source-backed-proxy"));
  assert.ok(byId(graph, "linked-panel").reasons.includes("linked-panel-source"));
  assert.ok(byId(graph, "reference-only").reasons.includes("reference-only-source"));
  assert.ok(byId(graph, "nested-pdf-manifest").reasons.includes("retained-pdf-source-not-decomposed"));
  assert.ok(byId(graph, "nested-pdf-conversion").reasons.includes("retained-pdf-source-not-decomposed"));
  assert.ok(byId(graph, "protected-descendant").reasons.includes("ancestor-source-backed"));
  assert.deepEqual(engine.toFabricSnapshot(graph), protectedSnapshot);
});

test("retained PDF and artifact identity stays orthogonal to explicitly editable representations", () => {
  const snapshot = {
    objects: [
      {
        type: "Group",
        figureId: "pdf-js-root",
        figureType: "pdf",
        importMeta: {
          importMode: "pdf-js-svg-vector",
          pdfSourceId: "pdf-editable-source",
          sourcePdfDataUrl: PDF_DATA_URL,
          convertedPdf: { sourceType: "converted_pdf_svg", nativePdfDescriptorTree: { schema: "native-tree" } }
        },
        pdfEditabilityManifest: {
          source_retained_for_export: true,
          native_pdf_descriptor_tree: { schema: "native-tree" }
        },
        objects: [{
          type: "Path",
          figureId: "pdf-js-path",
          pdfSourceId: "pdf-editable-source",
          importMeta: { importMode: "pdf-js-svg-vector", pdfSourceId: "pdf-editable-source" },
          path: [["M", 0, 0], ["L", 40, 20]]
        }, {
          type: "Path",
          figureId: "pdf-hidden-fidelity-fallback",
          visible: false,
          importMeta: { importMode: "pdf-js-svg-vector", pdfSourceId: "pdf-editable-source" },
          path: [["M", 0, 0], ["L", 12, 4]]
        }]
      },
      {
        type: "Group",
        figureId: "dense-proxy",
        importMeta: { importMode: "dense-svg-proxy", sourcePdfDataUrl: PDF_DATA_URL },
        objects: [
          {
            type: "Image",
            figureId: "dense-source-preview",
            proxyPanel: { schema: "figureStudio.proxyPanel.v1", proxy_enabled: true },
            importMeta: { denseSvgBackground: true }
          },
          {
            type: "Path",
            figureId: "dense-editable-overlay",
            denseSvgOverlay: { schema: "figureStudio.denseSvgOverlay.v1" },
            path: [["M", 1, 1], ["L", 9, 9]]
          },
          {
            type: "Textbox",
            figureId: "dense-legacy-role-overlay",
            denseSvgOverlayRole: "text",
            text: "Editable dense label"
          }
        ]
      },
      {
        type: "Group",
        figureId: "hybrid-panel",
        importMeta: { importMode: "pdf-text-raster-hybrid", sourcePdfDataUrl: PDF_DATA_URL },
        objects: [
          { type: "Image", figureId: "hybrid-source-preview", importMeta: { hybridRasterBackground: true } },
          {
            type: "Textbox",
            figureId: "hybrid-editable-text",
            pdfTextRepresentation: "editable-text",
            text: "Editable label"
          }
        ]
      },
      {
        type: "Image",
        figureId: "ordinary-artifact-image",
        artifactRef: { artifact_id: "local-image-1", media_type: "image/png" },
        artifactRefs: [{ artifact_id: "local-image-1" }]
      },
      {
        type: "Image",
        figureId: "editable-pdf-raster",
        importMeta: { importMode: "pdf-page-1-rasterized", pdfSourceId: "raster-source" }
      },
      {
        type: "Path",
        figureId: "released-dense-layer",
        importMeta: {
          importMode: "pdf-editable-vector-objects",
          pdfSourceId: "dense-source",
          releasedForPathEditing: true
        },
        denseSvgProxyLayerMeta: { schema: "figureStudio.denseSvgEditableLayer.v1", materialization_native_descriptor_id: "path-17" },
        path: [["M", 0, 0], ["L", 5, 5]]
      },
      {
        type: "Path",
        figureId: "bounded-dense-layer",
        importMeta: {
          importMode: "pdf-editable-vector-objects",
          denseSvgProxy: { schema: "figureStudio.denseSvgProxy.v1", source_object_id: "dense-proxy-source" }
        },
        denseSvgProxyLayerMeta: { schema: "figureStudio.denseSvgEditableLayer.v1" },
        path: [["M", 0, 0], ["L", 6, 6]]
      },
      {
        type: "Path",
        figureId: "persisted-pdf-path",
        pdfSourceId: "registered-pdf-source",
        importMeta: { importMode: "pdf-js-svg-vector", pdfSourceId: "registered-pdf-source" },
        path: [["M", 0, 0], ["L", 14, 9]]
      },
      {
        type: "Path",
        figureId: "released-pdf-path",
        pdfSourceId: "registered-pdf-source",
        importMeta: {
          importMode: "pdf-js-svg-vector",
          pdfSourceId: "registered-pdf-source",
          releasedForPathEditing: true
        },
        path: [["M", 0, 0], ["L", 16, 11]]
      },
      {
        type: "Rect",
        figureId: "released-linked-panel",
        figureStudioLinkedPanel: { schema: "figureStudio.linkedPanel.v1", status: "released", released: true, detached: true }
      },
      {
        type: "Rect",
        figureId: "disabled-proxy",
        proxyPanel: { schema: "figureStudio.proxyPanel.v1", proxy_enabled: false },
        importMeta: { proxyPanel: { schema: "figureStudio.proxyPanel.v1", proxy_enabled: true } }
      },
      {
        type: "Image",
        figureId: "provenance-artifact-only",
        importMeta: { bsdResultProvenance: { artifact_path: "imports/local-image.png" } }
      },
      {
        type: "Path",
        figureId: "overridden-component-path",
        figureStudioComponentInstance: {
          schema: "figureStudio.componentInstance.v2",
          componentId: "component-1",
          overrides: { "node-1": { fill: "#cc0000" } },
          detached: false
        },
        path: [["M", 0, 0], ["L", 7, 7]]
      },
      {
        type: "Rect",
        figureId: "generic-camel-result-aliases",
        source: { resultId: "ordinary-domain-result", moduleId: "ordinary-module" },
        provenance: { result_id: "display-only", artifact_path: "display-only/path" }
      }
    ]
  };
  const graph = engine.fromFabricSnapshot(snapshot);

  for (const id of [
    "pdf-js-root",
    "pdf-js-path",
    "dense-editable-overlay",
    "dense-legacy-role-overlay",
    "hybrid-editable-text",
    "ordinary-artifact-image",
    "editable-pdf-raster",
    "released-dense-layer",
    "bounded-dense-layer",
    "persisted-pdf-path",
    "released-pdf-path",
    "released-linked-panel",
    "disabled-proxy",
    "provenance-artifact-only",
    "overridden-component-path",
    "generic-camel-result-aliases"
  ]) assert.equal(byId(graph, id).classification, "editable", id);

  assert.ok(byId(graph, "pdf-js-path").operationAllowlist.includes("set-transform"));
  assert.ok(byId(graph, "pdf-js-root").operationAllowlist.includes("set-transform"), "a hidden fidelity fallback does not lock visible PDF artwork");
  assert.equal(
    byId(graph, "pdf-js-path").operationAllowlist.includes("replace-path-operands"),
    false,
    "retained native PDF source uses its dedicated path writer"
  );
  assert.equal(byId(graph, "dense-proxy").classification, "preserved-source");
  assert.equal(byId(graph, "dense-source-preview").classification, "preserved-source");
  assert.ok(byId(graph, "dense-editable-overlay").operationAllowlist.includes("set-transform"));
  assert.equal(byId(graph, "dense-editable-overlay").operationAllowlist.includes("replace-path-operands"), false);
  assert.ok(byId(graph, "dense-legacy-role-overlay").operationAllowlist.includes("set-transform"));
  assert.equal(byId(graph, "dense-legacy-role-overlay").operationAllowlist.includes("replace-path-operands"), false);
  assert.ok(byId(graph, "dense-legacy-role-overlay").operationAllowlist.includes("edit-text"));
  assert.equal(byId(graph, "hybrid-panel").classification, "preserved-source");
  assert.equal(byId(graph, "hybrid-source-preview").classification, "preserved-source");
  assert.ok(byId(graph, "hybrid-editable-text").operationAllowlist.includes("edit-text"));
  assert.ok(byId(graph, "ordinary-artifact-image").operationAllowlist.includes("crop-image"));
  assert.ok(byId(graph, "released-dense-layer").operationAllowlist.includes("replace-path-operands"));
  assert.equal(byId(graph, "bounded-dense-layer").operationAllowlist.includes("replace-path-operands"), false);
  assert.equal(byId(graph, "persisted-pdf-path").operationAllowlist.includes("replace-path-operands"), false);
  assert.ok(byId(graph, "released-pdf-path").operationAllowlist.includes("replace-path-operands"));
  assert.ok(byId(graph, "overridden-component-path").operationAllowlist.includes("replace-path-operands"));
  assert.equal(byId(graph, "released-dense-layer").pdfIdentity.descriptorId, "path-17");
  assert.deepEqual(engine.toFabricSnapshot(graph), snapshot);
});

test("normalized authority inherits locks, layers, and derived-object guards while retaining valid Fabric relations", () => {
  const snapshot = {
    objectLayers: {
      schema: "figureStudio.objectLayers.v1",
      layers: [{ id: "locked-layer", name: "Locked analysis", visible: true, locked: true }]
    },
    objects: [
      {
        type: "Group",
        figureId: "locked-parent",
        locked: true,
        objects: [{ type: "Path", figureId: "locked-child", path: [["M", 0, 0], ["L", 3, 3]] }]
      },
      {
        type: "Group",
        figureId: "locked-descendant-parent",
        objects: [
          { type: "Path", figureId: "locked-descendant", locked: true, path: [["M", 0, 0], ["L", 2, 2]] },
          { type: "Path", figureId: "locked-sibling", path: [["M", 0, 0], ["L", 4, 4]] }
        ]
      },
      {
        type: "Group",
        figureId: "layer-root",
        figureStudioLayerId: "locked-layer",
        objects: [{ type: "Rect", figureId: "layer-child" }]
      },
      {
        type: "Path",
        figureId: "smart-connector",
        figureType: "smartConnector",
        smartConnectorMeta: { start: { x: 0, y: 0 }, end: { x: 20, y: 10 } },
        path: [["M", 0, 0], ["L", 20, 10]]
      },
      {
        type: "Path",
        figureId: "live-boolean-result",
        figureStudioLiveBooleanRole: "result",
        path: [["M", 0, 0], ["L", 5, 0], ["Z"]]
      },
      {
        type: "Path",
        figureId: "line-vector-style-meta",
        styleMeta: { lineVectorStartX: 0, lineVectorStartY: 0, lineVectorEndX: 15, lineVectorEndY: 5 },
        path: [["M", 0, 0], ["L", 15, 5]]
      },
      {
        type: "Path",
        figureId: "topology-guarded-operands",
        figureStudioPathTopologyGuard: { commands: ["S"] },
        path: [["M", 0, 0], ["S", 4, 4, 8, 8]]
      },
      {
        type: "Polygon",
        figureId: "polygon-points",
        points: [{ x: 0, y: 0 }, { x: 10, y: 0 }, { x: 4, y: 7 }]
      },
      {
        type: "FabricText",
        figureId: "fabric-text",
        text: "Fabric 7 text",
        path: {
          type: "Path",
          figureId: "fabric-text-guide",
          path: [["M", 0, 0], ["C", 10, 0, 20, 10, 30, 10]]
        }
      },
      {
        type: "Group",
        figureId: "authored-clip",
        figureStudioClipMaskMeta: { schema: "figureStudio.clippingMask.v1", authored: true },
        objects: [{ type: "Rect", figureId: "authored-clip-content" }],
        clipPath: { type: "Path", figureId: "authored-clip-path", figureStudioClipHostId: "authored-clip", path: [["M", 0, 0], ["L", 4, 4]] }
      },
      {
        type: "Group",
        figureId: "incidental-clip",
        objects: [{ type: "Rect", figureId: "incidental-clip-content" }],
        clipPath: { type: "Path", figureId: "incidental-clip-path", path: [["M", 0, 0], ["L", 4, 4]] }
      },
      {
        type: "Path",
        figureId: "released-former-clip",
        figureStudioClipHostId: "removed-host-id",
        path: [["M", 0, 0], ["L", 1, 1]]
      },
      {
        type: "Group",
        figureId: "image-frame-root",
        figureStudioFrameMeta: { schema: "figureStudio.imageFrame.v2", mode: "fit" },
        objects: [
          { type: "Rect", figureId: "image-frame-boundary", figureStudioStructureRole: "image-frame-boundary" },
          { type: "Image", figureId: "image-frame-content", figureStudioStructureRole: "image-frame-content" }
        ],
        clipPath: { type: "Rect", figureId: "image-frame-clip", figureStudioStructureRole: "image-frame-clip" }
      },
      {
        type: "Textbox",
        figureId: "area-text-root",
        figureStudioAreaTextMeta: { schema: "figureStudio.areaText.v1" },
        text: "Bounded text",
        clipPath: { type: "Rect", figureId: "area-text-clip", figureStudioAreaTextFrameClip: true }
      }
    ]
  };
  const graph = engine.fromFabricSnapshot(snapshot);

  for (const id of ["locked-parent", "locked-child", "locked-descendant-parent", "locked-descendant", "locked-sibling", "layer-root", "layer-child"]) {
    assert.equal(byId(graph, id).operationAllowlist.includes("set-transform"), false, id);
  }
  assert.equal(byId(graph, "layer-child").layer.id, "");
  assert.equal(byId(graph, "layer-child").layer.effectiveId, "locked-layer");
  assert.equal(byId(graph, "layer-child").layer.inherited, true);
  assert.equal(byId(graph, "layer-child").layer.locked, true);
  assert.equal(byId(graph, "smart-connector").classification, "editable");
  assert.equal(byId(graph, "smart-connector").operationAllowlist.includes("set-transform"), false);
  assert.equal(byId(graph, "smart-connector").operationAllowlist.includes("replace-path-operands"), false);
  assert.equal(byId(graph, "live-boolean-result").operationAllowlist.includes("replace-path-operands"), false);
  assert.equal(byId(graph, "line-vector-style-meta").operationAllowlist.includes("replace-path-operands"), false);
  assert.ok(byId(graph, "topology-guarded-operands").operationAllowlist.includes("replace-path-operands"));
  assert.equal(byId(graph, "polygon-points").operationAllowlist.includes("replace-path-operands"), false);
  assert.ok(byId(graph, "fabric-text").operationAllowlist.includes("edit-text"));
  assert.equal(byId(graph, "fabric-text").textPathId, "fabric-text-guide");
  assert.equal(byId(graph, "fabric-text-guide").parentRelation, "text-path");
  assert.deepEqual(byId(graph, "fabric-text-guide").transactionAllowlist, []);
  assert.ok(byId(graph, "authored-clip").operationAllowlist.includes("edit-clipping-path"));
  assert.ok(byId(graph, "authored-clip").operationAllowlist.includes("release-clipping-mask"));
  assert.equal(byId(graph, "incidental-clip").operationAllowlist.includes("edit-clipping-path"), false);
  assert.ok(byId(graph, "image-frame-root").transactionAllowlist.includes("set-transform"));
  for (const id of ["image-frame-boundary", "image-frame-content", "image-frame-clip", "area-text-clip"]) {
    assert.deepEqual(byId(graph, id).transactionAllowlist, [], id);
    assert.ok(byId(graph, id).reasons.includes("internal-derived-structure"), id);
  }
  assert.ok(byId(graph, "area-text-root").transactionAllowlist.includes("set-transform"));
  assert.equal(engine.validate(graph).valid, true, "a released clip's historical host id is non-owning");
  assert.deepEqual(engine.toFabricSnapshot(graph), snapshot);

  assert.throws(
    () => engine.applyTransaction(graph, {
      type: "set-transform",
      edits: [{ nodeId: "locked-sibling", expected: { left: 0 }, value: { left: 1 } }]
    }),
    (error) => error.code === "OPERATION_NOT_ALLOWED"
  );
});

test("graph-to-Fabric roundtrip is exact for supported, source-backed, and opaque unsupported payloads", () => {
  const snapshot = figureSnapshot();
  const graph = engine.projectFabricSnapshot(snapshot);
  const roundtrip = engine.toFabricSnapshot(graph);
  assert.deepEqual(roundtrip, snapshot);
  assert.notEqual(roundtrip, snapshot);
  assert.notEqual(roundtrip.objects[0], snapshot.objects[0]);
  roundtrip.objects[0].name = "Caller-owned copy";
  assert.equal(engine.toFabricSnapshot(graph).objects[0].name, "Editable assay group");
  assert.equal(Object.isFrozen(graph), true);
  assert.equal(Object.isFrozen(graph.payload.fabricSnapshot), true);
});

test("atomic path transaction replaces multiple anchors across paths and its inverse restores the exact snapshot", () => {
  const snapshot = figureSnapshot();
  const graph = engine.fromFabricSnapshot(snapshot);
  const result = engine.applyTransaction(graph, {
    schema: engine.TRANSACTION_SCHEMA,
    type: "replace-path-operands",
    expectedDigest: graph.snapshotDigest,
    edits: [
      {
        nodeId: "path-1",
        anchors: [
          { commandIndex: 0, expected: [0, 0], value: [2.5, 3.5] },
          { commandIndex: 1, operandIndices: [5, 6], expected: [30, 10], value: [34, 14] }
        ]
      },
      {
        nodeId: "compound-1",
        anchors: [
          { commandIndex: 1, operandIndex: 1, expected: 100, value: 112 }
        ]
      }
    ]
  });

  assert.notEqual(result.graph, graph);
  assert.notEqual(result.afterDigest, result.beforeDigest);
  const changed = engine.toFabricSnapshot(result.graph);
  assert.deepEqual(changed.objects[0].objects[0].path[0], ["M", 2.5, 3.5]);
  assert.deepEqual(changed.objects[0].objects[0].path[1], ["C", 10, 0, 20, 10, 34, 14]);
  assert.deepEqual(changed.objects[0].objects[1].path[1], ["L", 112, 0]);
  assert.deepEqual(engine.toFabricSnapshot(graph), snapshot, "input graph remains unchanged");

  const undone = engine.applyTransaction(result.graph, result.inverse);
  assert.equal(undone.afterDigest, graph.snapshotDigest);
  assert.deepEqual(engine.toFabricSnapshot(undone.graph), snapshot);
});

test("trusted target plans validate without materializing the scene and commit their exact prepared operations", () => {
  const snapshot = figureSnapshot();
  const graph = engine.fromFabricSnapshot(snapshot);
  const transaction = {
    schema: engine.TRANSACTION_SCHEMA,
    type: "replace-path-operands",
    expectedDigest: graph.snapshotDigest,
    edits: [{
      nodeId: "path-1",
      anchors: [
        { commandIndex: 0, expected: [0, 0], value: [7, 9] },
        { commandIndex: 2, expected: [40, 20], value: [44, 24] }
      ]
    }]
  };
  const retainedSnapshot = graph.payload.fabricSnapshot;
  const retainedNodes = graph.nodes;
  const plan = engine.planTransaction(graph, transaction);

  assert.equal(plan.schema, engine.TRANSACTION_PLAN_SCHEMA);
  assert.equal(plan.type, "replace-path-operands");
  assert.equal(plan.beforeDigest, graph.snapshotDigest);
  assert.deepEqual(plan.targetIds, ["path-1"]);
  assert.equal(plan.targetCount, 1);
  assert.equal(plan.operationCount, 4);
  assert.deepEqual(plan.expectationChecks, { digest: true, targetValues: 4 });
  assert.equal(plan.structuralSharing.planningScope, "targets-only");
  assert.equal(plan.structuralSharing.sourceGraphShared, true);
  assert.equal(plan.structuralSharing.fabricSnapshotShared, true);
  assert.equal(plan.structuralSharing.targetNodeMetadataShared, true);
  assert.equal(plan.structuralSharing.snapshotCloned, false);
  assert.equal(plan.structuralSharing.nodeMetadataCloned, 0);
  assert.equal(plan.structuralSharing.untouchedNodeCount, graph.nodes.length - 1);
  assert.equal(Object.isFrozen(plan), true);
  for (const duration of Object.values(plan.metrics)) {
    assert.equal(Number.isFinite(duration) && duration >= 0, true);
  }
  assert.equal(graph.payload.fabricSnapshot, retainedSnapshot);
  assert.equal(graph.nodes, retainedNodes);
  assert.deepEqual(engine.toFabricSnapshot(graph), snapshot, "planning does not clone, patch, or reproject the graph");

  transaction.edits[0].anchors[0].value[0] = 999;
  transaction.edits[0].anchors[1].value[1] = 999;
  const result = engine.applyTransactionPlan(graph, plan);
  const changed = engine.toFabricSnapshot(result.graph);
  assert.deepEqual(changed.objects[0].objects[0].path[0], ["M", 7, 9]);
  assert.deepEqual(changed.objects[0].objects[0].path[2], ["L", 44, 24]);
  assert.equal(result.plan, plan);
  assert.equal(result.metrics.targetCount, 1);
  assert.equal(result.metrics.operationCount, 4);
  assert.equal(result.metrics.commit.fullSnapshotClone, true);
  assert.equal(result.metrics.commit.fullProjection, true);
  assert.equal(result.metrics.commit.nodeMetadataRebuilt, true);
  assert.equal(result.metrics.engineWorkMs, result.metrics.planning.totalMs + result.metrics.commit.totalMs);
  assert.deepEqual(engine.toFabricSnapshot(graph), snapshot, "commit keeps the source graph immutable");

  const undone = engine.applyTransaction(result.graph, result.inverse);
  assert.deepEqual(engine.toFabricSnapshot(undone.graph), snapshot);
});

test("transaction plans reject stale graphs, stale target values, protected sources, and portable plan copies", () => {
  const graph = engine.fromFabricSnapshot(figureSnapshot());
  assert.throws(
    () => engine.planTransaction(graph, {
      type: "set-transform",
      expectedDigest: "dual32:stale",
      edits: [{ nodeId: "text-1", expected: { left: 70 }, value: { left: 71 } }]
    }),
    (error) => error.code === "STALE_EXPECTATION" && /digest/.test(error.message)
  );
  assert.throws(
    () => engine.planTransaction(graph, {
      type: "set-transform",
      edits: [{ nodeId: "text-1", expected: { left: 999 }, value: { left: 71 } }]
    }),
    (error) => error.code === "STALE_EXPECTATION" && /transform\.left/.test(error.message)
  );
  assert.throws(
    () => engine.planTransaction(graph, {
      type: "set-transform",
      edits: [{ nodeId: "pdf-page-1", expected: { left: 720 }, value: { left: 721 } }]
    }),
    (error) => error.code === "NODE_NOT_EDITABLE" && /preserved-source/.test(error.message)
  );

  const plan = engine.planTransaction(graph, {
    type: "set-transform",
    edits: [{ nodeId: "text-1", expected: { left: 70, top: 18 }, value: { left: 71 } }]
  });
  assert.equal(plan.operationCount, 1);
  assert.deepEqual(plan.expectationChecks, { digest: false, targetValues: 2 });
  assert.equal(plan.structuralSharing.planningScope, "targets-only");
  const otherGraph = engine.fromFabricSnapshot(figureSnapshot());
  assert.throws(
    () => engine.applyTransactionPlan(otherGraph, plan),
    (error) => error.code === "STALE_EXPECTATION" && /different scene graph/.test(error.message)
  );
  assert.throws(
    () => engine.applyTransactionPlan(graph, JSON.parse(JSON.stringify(plan))),
    (error) => error.code === "UNTRUSTED_TRANSACTION_PLAN"
  );
  const applied = engine.applyTransactionPlan(graph, plan);
  assert.equal(engine.toFabricSnapshot(applied.graph).objects[2].left, 71);
  assert.equal(engine.toFabricSnapshot(applied.graph).objects[2].top, 18);
  assert.deepEqual(engine.toFabricSnapshot(graph), figureSnapshot());
});

test("bounds-changing path edits require the Fabric scene-stable frame adapter before snapshot export", () => {
  const snapshot = {
    objects: [{
      type: "Path",
      figureId: "framed-path",
      left: 120,
      top: 90,
      width: 20,
      height: 10,
      pathOffset: { x: 10, y: 5 },
      path: [["M", 0, 0], ["L", 20, 10]]
    }]
  };
  const graph = engine.fromFabricSnapshot(snapshot);
  const result = engine.applyTransaction(graph, {
    type: "replace-path-operands",
    edits: [{
      nodeId: "framed-path",
      anchors: [{ commandIndex: 1, expected: [20, 10], value: [80, 45] }]
    }]
  });

  assert.deepEqual(result.requirements, [{
    schema: engine.REQUIREMENT_SCHEMA,
    type: "fabric-path-frame-rebuild",
    nodeId: "framed-path",
    changedOperandCount: 2,
    affectedFields: ["path", "width", "height", "pathOffset", "left", "top"]
  }]);
  assert.deepEqual(result.graph.pendingRequirements, result.requirements);
  assert.throws(
    () => engine.toFabricSnapshot(result.graph),
    (error) => error.code === "FABRIC_FRAME_REBUILD_REQUIRED"
      && error.details?.requirements?.[0]?.nodeId === "framed-path"
  );
  const adapterInput = engine.toFabricSnapshot(result.graph, { allowPendingFabricFrameRebuild: true });
  assert.deepEqual(adapterInput.objects[0].path[1], ["L", 80, 45]);
  assert.equal(adapterInput.objects[0].width, 20, "the bridge must rebuild Fabric-derived geometry");
  assert.deepEqual(adapterInput.objects[0].pathOffset, { x: 10, y: 5 });
  assert.deepEqual(engine.toFabricSnapshot(graph), snapshot, "the coherent source graph remains unchanged");
  const portableInverse = engine.applyTransaction(result.graph, JSON.parse(JSON.stringify(result.inverse)));
  assert.throws(
    () => engine.toFabricSnapshot(portableInverse.graph),
    (error) => error.code === "FABRIC_FRAME_REBUILD_REQUIRED",
    "a portable inverse remains fail-closed without the engine-instance requirement journal"
  );
  const undone = engine.applyTransaction(result.graph, result.inverse);
  assert.deepEqual(undone.requirements, []);
  assert.deepEqual(engine.toFabricSnapshot(undone.graph), snapshot, "the trusted inverse restores frame coherence too");
});

test("atomic multi-node transform transaction is invertible and rejects ancestor/descendant overlap", () => {
  const snapshot = figureSnapshot();
  const graph = engine.fromFabricSnapshot(snapshot);
  const result = engine.applyTransaction(graph, {
    type: "set-transform",
    edits: [
      { nodeId: "path-1", expected: { left: 5, top: 6 }, value: { left: 15, top: 26 } },
      { nodeId: "text-1", expected: { left: 70, angle: 0 }, value: { left: 82, angle: -4 } }
    ]
  });
  const changed = engine.toFabricSnapshot(result.graph);
  assert.equal(result.plan.structuralSharing.planningScope, "targets-and-ancestors");
  assert.deepEqual(
    { left: changed.objects[0].objects[0].left, top: changed.objects[0].objects[0].top },
    { left: 15, top: 26 }
  );
  assert.deepEqual(
    { left: changed.objects[2].left, angle: changed.objects[2].angle },
    { left: 82, angle: -4 }
  );
  const undone = engine.applyTransaction(result.graph, result.inverse);
  assert.deepEqual(engine.toFabricSnapshot(undone.graph), snapshot);

  assert.throws(
    () => engine.applyTransaction(graph, {
      type: "set-transform",
      edits: [
        { nodeId: "group-1", expected: { left: 40 }, value: { left: 41 } },
        { nodeId: "path-1", expected: { left: 5 }, value: { left: 6 } }
      ]
    }),
    (error) => error.code === "OVERLAPPING_EDIT" && /ancestor and descendant/.test(error.message)
  );
});

test("stale, overlapping, and invalid atomic edits fail without changing any input", () => {
  const snapshot = figureSnapshot();
  const graph = engine.fromFabricSnapshot(snapshot);
  const beforeDigest = engine.digest(graph);

  assert.throws(
    () => engine.applyTransaction(graph, {
      type: "set-transform",
      edits: [
        { nodeId: "path-1", expected: { left: 5 }, value: { left: 15 } },
        { nodeId: "text-1", expected: { left: 999 }, value: { left: 80 } }
      ]
    }),
    (error) => error.code === "STALE_EXPECTATION"
  );
  assert.throws(
    () => engine.applyTransaction(graph, {
      type: "replace-path-operands",
      edits: [{
        nodeId: "path-1",
        anchors: [
          { commandIndex: 0, operandIndex: 1, expected: 0, value: 1 },
          { commandIndex: 0, operandIndex: 1, expected: 0, value: 2 }
        ]
      }]
    }),
    (error) => error.code === "OVERLAPPING_EDIT"
  );
  assert.throws(
    () => engine.applyTransaction(graph, {
      type: "set-transform",
      edits: [{ nodeId: "text-1", expected: { left: 70 }, value: { left: Number.NaN } }]
    }),
    (error) => error.code === "INVALID_NUMBER"
  );
  assert.equal(engine.digest(graph), beforeDigest);
  assert.deepEqual(engine.toFabricSnapshot(graph), snapshot);
  assert.deepEqual(snapshot, figureSnapshot(), "caller-owned input snapshot also remains unchanged");
});

test("serialized or tampered normalized graphs cannot grant themselves edit authority", () => {
  const snapshot = figureSnapshot();
  const graph = engine.fromFabricSnapshot(snapshot);
  const externalGraph = JSON.parse(JSON.stringify(graph));
  const protectedNode = externalGraph.nodes[externalGraph.nodeIndexById["pdf-page-1"]];
  protectedNode.classification = "editable";
  protectedNode.operationAllowlist.push("set-transform");
  protectedNode.transactionAllowlist.push("set-transform");
  protectedNode.reasons = [];

  assert.throws(
    () => engine.validate(externalGraph),
    (error) => error.code === "NORMALIZATION_MISMATCH" && /capability metadata/.test(error.message)
  );
  assert.throws(
    () => engine.applyTransaction(externalGraph, {
      type: "set-transform",
      edits: [{ nodeId: "pdf-page-1", expected: { left: 720 }, value: { left: 721 } }]
    }),
    (error) => error.code === "UNTRUSTED_GRAPH"
  );
  assert.deepEqual(engine.toFabricSnapshot(graph), snapshot);

  const cleanExternalGraph = JSON.parse(JSON.stringify(graph));
  assert.equal(engine.validate(cleanExternalGraph).valid, true, "untampered serialized graphs remain inspectable");
  assert.throws(
    () => engine.toFabricSnapshot(cleanExternalGraph),
    (error) => error.code === "UNTRUSTED_GRAPH"
  );
  assert.throws(
    () => engine.applyTransaction(cleanExternalGraph, {
      type: "set-transform",
      edits: [{ nodeId: "text-1", expected: { left: 70 }, value: { left: 71 } }]
    }),
    (error) => error.code === "UNTRUSTED_GRAPH"
  );
  const reprojected = engine.fromFabricSnapshot(cleanExternalGraph.payload.fabricSnapshot);
  const applied = engine.applyTransaction(reprojected, {
    type: "set-transform",
    edits: [{ nodeId: "text-1", expected: { left: 70 }, value: { left: 71 } }]
  });
  assert.equal(engine.toFabricSnapshot(applied.graph).objects[2].left, 71);

  const payloadTamper = JSON.parse(JSON.stringify(graph));
  payloadTamper.payload.fabricSnapshot.objects[2].left = 72;
  payloadTamper.nodes[payloadTamper.nodeIndexById["text-1"]].transform.left = 72;
  assert.throws(
    () => engine.validate(payloadTamper),
    (error) => error.code === "NORMALIZATION_MISMATCH" && /snapshotDigest/.test(error.message)
  );
});

test("projection and validation reject duplicate IDs, cycles, broken references, and non-finite geometry", () => {
  assert.throws(
    () => engine.fromFabricSnapshot({
      objects: [
        { type: "Rect", figureId: "duplicate" },
        { type: "Circle", figureId: "duplicate" }
      ]
    }),
    (error) => error.code === "DUPLICATE_NODE_ID"
  );

  const cyclic = { type: "Group", figureId: "cycle", objects: [] };
  cyclic.objects.push(cyclic);
  assert.throws(
    () => engine.fromFabricSnapshot({ objects: [cyclic] }),
    (error) => error.code === "GRAPH_CYCLE"
  );

  const broken = JSON.parse(JSON.stringify(engine.fromFabricSnapshot(figureSnapshot())));
  broken.nodes[0].childIds[0] = "missing-child";
  assert.throws(
    () => engine.validate(broken),
    (error) => error.code === "BROKEN_REFERENCE"
  );

  assert.throws(
    () => engine.fromFabricSnapshot({ objects: [{ type: "Rect", figureId: "bad-transform", left: Infinity }] }),
    (error) => error.code === "INVALID_NUMBER"
  );
  assert.throws(
    () => engine.fromFabricSnapshot({ objects: [{ type: "Path", figureId: "bad-path", path: [["M", 0, NaN]] }] }),
    (error) => error.code === "INVALID_NUMBER"
  );
  assert.throws(
    () => engine.fromFabricSnapshot({ objects: [{ type: "Rect", figureId: "bad-size", width: Infinity }] }),
    (error) => error.code === "INVALID_NUMBER"
  );
  assert.throws(
    () => engine.fromFabricSnapshot({ objects: [{ type: "Polygon", figureId: "bad-points", points: [{ x: 0, y: NaN }] }] }),
    (error) => error.code === "INVALID_NUMBER"
  );
  assert.throws(
    () => engine.fromFabricSnapshot({ objects: [{ type: "Rect", figureId: "bad-stroke", strokeWidth: Infinity }] }),
    (error) => error.code === "INVALID_NUMBER" && /strokeWidth/.test(error.message)
  );
  assert.throws(
    () => engine.fromFabricSnapshot({ objects: [{ type: "FutureObject", figureId: "bad-vendor-number", vendorPayload: { tension: NaN } }] }),
    (error) => error.code === "INVALID_NUMBER" && /vendorPayload\.tension/.test(error.message)
  );

  const externalNonFinite = JSON.parse(JSON.stringify(engine.fromFabricSnapshot(figureSnapshot())));
  externalNonFinite.payload.fabricSnapshot.objects[4].vendorExtension.unknownNumber = Infinity;
  assert.throws(
    () => engine.validate(externalNonFinite),
    (error) => error.code === "INVALID_NUMBER" && /unknownNumber/.test(error.message)
  );
});

test("digest and generated IDs are deterministic across repeated and key-reordered projections", () => {
  const first = figureSnapshot();
  const second = {
    objects: first.objects,
    customDocumentField: first.customDocumentField,
    background: first.background,
    height: first.height,
    width: first.width,
    version: first.version
  };
  const graphA = engine.fromFabricSnapshot(first);
  const graphB = engine.fromFabricSnapshot(second);
  assert.equal(engine.digest(graphA), engine.digest(graphB));

  const withoutIds = { objects: [{ type: "Group", objects: [{ type: "Path", path: [["M", 0, 0], ["L", 1, 1]] }] }] };
  const generatedA = engine.fromFabricSnapshot(withoutIds);
  const generatedB = engine.fromFabricSnapshot(withoutIds);
  assert.deepEqual(generatedA.nodes.map((node) => node.id), generatedB.nodes.map((node) => node.id));
  assert.deepEqual(generatedA.nodes.map((node) => node.id), ["@fsve:objects/0", "@fsve:objects/0/objects/0"]);
  assert.deepEqual(generatedA.nodes.map((node) => node.idStability), ["source-path-derived-unstable", "source-path-derived-unstable"]);
});

test("pure object classification is bridge-safe and classic-script/CommonJS APIs share one instance", () => {
  const classification = engine.classifyFabricObject({
    type: "Image",
    importMeta: { pdfSourceId: "pdf-source", sourcePdfDataUrl: PDF_DATA_URL }
  });
  assert.equal(classification.classification, "preserved-source");
  assert.deepEqual(classification.transactionAllowlist, []);
  assert.equal(JSON.stringify(classification).includes(PDF_DATA_URL), false);
  assert.deepEqual(engine.TRANSACTION_TYPES, ["replace-path-operands", "set-transform"]);
  assert.equal(engine.TRANSACTION_PLAN_SCHEMA, "figureStudio.vectorTransactionPlan.v1");
  assert.equal(globalThis.FigureStudioVectorEngine, engine);
  for (const method of [
    "fromFabricSnapshot",
    "toFabricSnapshot",
    "validate",
    "summarize",
    "digest",
    "planTransaction",
    "applyTransactionPlan",
    "applyTransaction",
    "classifyFabricObject"
  ]) assert.equal(typeof engine[method], "function", method);
});

test("2500-node scientific-figure graph stays within an explicit projection/validation/transaction budget", (t) => {
  const groups = [];
  const groupCount = 50;
  const pathsPerGroup = 50;
  for (let groupIndex = 0; groupIndex < groupCount; groupIndex += 1) {
    const groupId = `dense-group-${groupIndex}`;
    const objects = [];
    for (let pathIndex = 0; pathIndex < pathsPerGroup; pathIndex += 1) {
      const x = pathIndex * 2;
      const y = groupIndex * 2;
      const path = groupIndex === 25 && pathIndex === 26
        ? [
            ["M", 0, 0],
            ...Array.from({ length: 32 }, (_item, index) => ["L", index + 1, (index + 1) * 2])
          ]
        : [
            ["M", 0, 0],
            ["C", 2, 0, 4, 4, 6, 4],
            ["L", 8, 6],
            ["L", 10, 2],
            ["Z"]
          ];
      objects.push({
        type: "Path",
        figureId: `dense-path-${groupIndex}-${pathIndex}`,
        groupId,
        left: x,
        top: y,
        path,
        stroke: pathIndex % 2 ? "#176b68" : "#514a9c",
        fill: "",
        figureStudioLayerId: `dense-layer-${groupIndex % 5}`
      });
    }
    groups.push({
      type: "Group",
      figureId: groupId,
      left: groupIndex * 5,
      top: groupIndex * 3,
      objects
    });
  }
  const denseSnapshot = { version: "7.3.1", width: 2400, height: 1600, objects: groups };
  const explicitBudgetMs = 1500;
  const started = performance.now();
  const graph = engine.fromFabricSnapshot(denseSnapshot);
  const projectedAt = performance.now();
  const validation = engine.validate(graph);
  const validatedAt = performance.now();
  const capabilitySummary = engine.summarize(graph);
  const summarizedAt = performance.now();
  const transactionStartedAt = performance.now();
  const transaction = engine.applyTransaction(graph, {
    type: "replace-path-operands",
    edits: [{
      nodeId: "dense-path-25-25",
      anchors: [
        { commandIndex: 0, expected: [0, 0], value: [0.5, 0.75] },
        { commandIndex: 1, operandIndices: [5, 6], expected: [6, 4], value: [6.5, 4.5] },
        { commandIndex: 2, expected: [8, 6], value: [8.25, 6.25] }
      ]
    }]
  });
  const finished = performance.now();
  const densePlanTransaction = {
    type: "replace-path-operands",
    expectedDigest: graph.snapshotDigest,
    edits: [{
      nodeId: "dense-path-25-26",
      anchors: Array.from({ length: 32 }, (_item, index) => ({
        commandIndex: index + 1,
        expected: [index + 1, (index + 1) * 2],
        value: [index + 1.25, ((index + 1) * 2) + 0.25]
      }))
    }]
  };
  for (let warmIndex = 0; warmIndex < 25; warmIndex += 1) {
    engine.planTransaction(graph, densePlanTransaction);
  }
  const targetPlanSamples = [];
  let measuredPlan;
  for (let sampleIndex = 0; sampleIndex < 100; sampleIndex += 1) {
    const sampleStartedAt = performance.now();
    measuredPlan = engine.planTransaction(graph, densePlanTransaction);
    targetPlanSamples.push(performance.now() - sampleStartedAt);
  }
  const targetPlanP50Ms = percentile(targetPlanSamples, 0.5);
  const targetPlanP95Ms = percentile(targetPlanSamples, 0.95);

  assert.equal(graph.nodes.length, 2550);
  assert.equal(validation.valid, true);
  assert.equal(capabilitySummary.nodeCount, 2550);
  assert.equal(measuredPlan.targetCount, 1);
  assert.equal(measuredPlan.operationCount, 64);
  assert.equal(measuredPlan.structuralSharing.untouchedNodeCount, 2549);
  assert.equal(measuredPlan.structuralSharing.snapshotCloned, false);
  assert.equal(transaction.graph.nodes.length, 2550);
  const projectionMs = projectedAt - started;
  const validationMs = validatedAt - projectedAt;
  const summaryDigestMs = summarizedAt - validatedAt;
  const transactionMs = finished - transactionStartedAt;
  const totalMs = finished - started;
  const projectionValidationSummaryMs = summarizedAt - started;
  t.diagnostic(
    `engine timings: projection ${projectionMs.toFixed(1)} ms; validation ${validationMs.toFixed(1)} ms; `
    + `summary/digest ${summaryDigestMs.toFixed(1)} ms; transaction ${transactionMs.toFixed(1)} ms; total ${totalMs.toFixed(1)} ms; `
    + `warm 64-operand target plan p50 ${targetPlanP50Ms.toFixed(3)} ms, p95 ${targetPlanP95Ms.toFixed(3)} ms (100 samples)`
  );
  assert.ok(targetPlanP95Ms <= 16, `warm 64-operand target-plan p95 took ${targetPlanP95Ms.toFixed(3)} ms`);
  assert.ok(projectionMs < explicitBudgetMs, `projection took ${projectionMs.toFixed(1)} ms`);
  assert.ok(validationMs < explicitBudgetMs, `validation took ${validationMs.toFixed(1)} ms`);
  assert.ok(summaryDigestMs < explicitBudgetMs, `summary/digest took ${summaryDigestMs.toFixed(1)} ms`);
  assert.ok(transactionMs < explicitBudgetMs, `transaction took ${transactionMs.toFixed(1)} ms`);
  assert.ok(
    projectionValidationSummaryMs < 500,
    `projection + validation + summary/digest took ${projectionValidationSummaryMs.toFixed(1)} ms`
  );
  assert.ok(totalMs < explicitBudgetMs, `total engine work took ${totalMs.toFixed(1)} ms`);
});
