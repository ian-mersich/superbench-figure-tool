(function initFigureStudioPdfSourceReplacement(root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  if (root) root.FigureStudioPdfSourceReplacement = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function createFigureStudioPdfSourceReplacementModule() {
  "use strict";

  const VERSION = "1.0.0";
  const SCHEMA = "figureStudio.pdfSourceReplacement.v1";

  function finite(value, fallback = 0) {
    const number = Number(value);
    return Number.isFinite(number) ? number : fallback;
  }

  function dimensions(value = {}) {
    const widthPt = finite(value.widthPt ?? value.width_pt ?? value.width, 0);
    const heightPt = finite(value.heightPt ?? value.height_pt ?? value.height, 0);
    if (!(widthPt > 0 && heightPt > 0)) return null;
    return {
      widthPt,
      heightPt,
      widthIn: widthPt / 72,
      heightIn: heightPt / 72,
      rotation: ((finite(value.rotation, 0) % 360) + 360) % 360,
      userUnit: finite(value.userUnit ?? value.user_unit, 1) > 0 ? finite(value.userUnit ?? value.user_unit, 1) : 1
    };
  }

  function dimensionLabel(value) {
    const normalized = dimensions(value);
    if (!normalized) return "Unavailable";
    return `${normalized.widthIn.toFixed(3).replace(/0+$/, "").replace(/\.$/, "")} × ${normalized.heightIn.toFixed(3).replace(/0+$/, "").replace(/\.$/, "")} in (${normalized.widthPt.toFixed(1).replace(/\.0$/, "")} × ${normalized.heightPt.toFixed(1).replace(/\.0$/, "")} pt)`;
  }

  function compareDimensions(current, candidate, tolerance = 0.005) {
    const before = dimensions(current);
    const after = dimensions(candidate);
    if (!before || !after) return { measurable: false, aspectRatioChanged: false, widthRatio: 0, heightRatio: 0 };
    const beforeAspect = before.widthPt / before.heightPt;
    const afterAspect = after.widthPt / after.heightPt;
    const widthRatio = after.widthPt / before.widthPt;
    const heightRatio = after.heightPt / before.heightPt;
    return {
      measurable: true,
      aspectRatioChanged: Math.abs(afterAspect - beforeAspect) / beforeAspect > Math.max(0, finite(tolerance, 0.005)),
      widthRatio,
      heightRatio,
      sizeChanged: Math.abs(widthRatio - 1) > tolerance || Math.abs(heightRatio - 1) > tolerance
    };
  }

  function hasPdfHeader(bytes) {
    const values = bytes instanceof Uint8Array ? bytes : new Uint8Array(Array.from(bytes || []));
    const limit = Math.min(values.length, 1024);
    for (let index = 0; index <= limit - 5; index += 1) {
      if (values[index] === 0x25 && values[index + 1] === 0x50 && values[index + 2] === 0x44 && values[index + 3] === 0x46 && values[index + 4] === 0x2d) return true;
      if (values[index] > 0x20) break;
    }
    return false;
  }

  function buildReview(input = {}) {
    const comparison = compareDimensions(input.currentDimensions, input.candidateDimensions);
    const requestedPage = Math.max(1, Math.round(finite(input.requestedPage, 1)));
    const candidatePageCount = Math.max(0, Math.round(finite(input.candidatePageCount, 0)));
    return {
      schema: "figureStudio.pdfSourceReplacementReview.v1",
      currentFilename: String(input.currentFilename || "Placed PDF"),
      candidateFilename: String(input.candidateFilename || "replacement.pdf"),
      requestedPage,
      candidatePageCount,
      requestedMode: String(input.requestedMode || "source-backed"),
      actualMode: String(input.actualMode || "source-backed"),
      currentDimensions: dimensions(input.currentDimensions),
      candidateDimensions: dimensions(input.candidateDimensions),
      comparison,
      currentBounds: input.currentBounds || null,
      predictedBounds: input.predictedBounds || null,
      supported: candidatePageCount >= requestedPage && input.actualMode === "source-backed",
      consequences: {
        placement: "The top-level object keeps its center, transform values, opacity, layer, stacking order, clip and group identity.",
        size: comparison.aspectRatioChanged
          ? "The page aspect ratio changes. Existing scale values are retained, so placed bounds change without stretching the candidate page to the old bounds."
          : comparison.sizeChanged
            ? "The page size changes. Existing scale values are retained, so placed bounds change in proportion to the candidate page."
            : "The candidate has the same measured physical page size.",
        editability: "The placed page remains source-backed: its layout is editable, while PDF text, vectors, raster labels and unsupported imported content are not reconstructed.",
        export: "SVG exports the current on-canvas preview. PDF re-embeds the retained candidate page only when its placement remains eligible for exact passthrough; otherwise PDF exports the preview."
      }
    };
  }

  function buildMetadata(review = {}, input = {}) {
    return {
      schema: SCHEMA,
      previousFilename: String(review.currentFilename || input.previousFilename || "Placed PDF"),
      currentFilename: String(review.candidateFilename || input.currentFilename || "replacement.pdf"),
      selectedPage: Math.max(1, Math.round(finite(review.requestedPage ?? input.selectedPage, 1))),
      candidatePageCount: Math.max(1, Math.round(finite(review.candidatePageCount ?? input.candidatePageCount, 1))),
      replacedAt: String(input.replacedAt || ""),
      requestedMode: String(review.requestedMode || "source-backed"),
      actualMode: String(review.actualMode || "source-backed"),
      placementPolicy: "preserve-center-and-transform-values",
      topLevelIdentityRetained: true,
      nestedIdentityPolicy: "not-applicable-source-backed-page",
      originalPhysicalDimensions: dimensions(review.currentDimensions),
      replacementPhysicalDimensions: dimensions(review.candidateDimensions),
      aspectRatioChanged: Boolean(review.comparison?.aspectRatioChanged),
      physicalSizeChanged: Boolean(review.comparison?.sizeChanged),
      predictedBounds: review.predictedBounds || null,
      actualBounds: input.actualBounds || null,
      clipRetained: Boolean(input.clipRetained),
      sourceBytesRetained: true,
      externalPathStored: false,
      svgExportMode: "canvas-preview",
      pdfExportMode: String(input.pdfExportMode || "source-page-when-supported-otherwise-preview"),
      fullNativeEquivalence: false,
      previous: input.previous || null
    };
  }

  return Object.freeze({
    VERSION,
    SCHEMA,
    dimensions,
    dimensionLabel,
    compareDimensions,
    hasPdfHeader,
    buildReview,
    buildMetadata
  });
});
