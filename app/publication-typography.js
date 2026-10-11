(function publicationTypographyModule(root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  root.FigureStudioPublicationTypography = api;
}(typeof globalThis !== "undefined" ? globalThis : this, function publicationTypographyFactory() {
  "use strict";

  const SCHEMA = "figureStudio.publicationTypography.v1";
  const PROFILE_SCHEMA = "figureStudio.publicationTypographyProfile.v1";
  const BINDING_SCHEMA = "figureStudio.publicationTypographyBinding.v1";
  const REVIEW_SCHEMA = "figureStudio.publicationTypographyReviewReceipt.v1";
  const UNASSIGN_ROLE = "__none__";
  const ROLES = Object.freeze(["panel-label", "title", "annotation", "legend-body"]);
  const ROLE_LABELS = Object.freeze({
    "panel-label": "Panel label",
    title: "Title",
    annotation: "Annotation",
    "legend-body": "Legend/body"
  });
  const DEFAULT_ROLE_STYLES = Object.freeze({
    "panel-label": Object.freeze({ fontFamily: "Arial, Helvetica, sans-serif", finalSizePt: 9, fontWeight: "700", lineHeight: 1.05, color: "#111827" }),
    title: Object.freeze({ fontFamily: "Arial, Helvetica, sans-serif", finalSizePt: 9, fontWeight: "700", lineHeight: 1.15, color: "#111827" }),
    annotation: Object.freeze({ fontFamily: "Arial, Helvetica, sans-serif", finalSizePt: 7.5, fontWeight: "400", lineHeight: 1.2, color: "#1f2937" }),
    "legend-body": Object.freeze({ fontFamily: "Arial, Helvetica, sans-serif", finalSizePt: 7, fontWeight: "400", lineHeight: 1.25, color: "#1f2937" })
  });

  function numberInRange(value, fallback, min, max) {
    const numeric = Number(value);
    return Number.isFinite(numeric) ? Math.min(max, Math.max(min, numeric)) : fallback;
  }

  function normalizeColor(value, fallback) {
    const color = String(value || "").trim();
    return /^#[0-9a-f]{6}$/i.test(color) ? color.toLowerCase() : fallback;
  }

  function normalizeRoleStyle(value, role) {
    const fallback = DEFAULT_ROLE_STYLES[role];
    return {
      fontFamily: String(value?.fontFamily || fallback.fontFamily).trim().slice(0, 180) || fallback.fontFamily,
      finalSizePt: numberInRange(value?.finalSizePt, fallback.finalSizePt, 3, 96),
      fontWeight: String(value?.fontWeight || fallback.fontWeight).trim().slice(0, 24) || fallback.fontWeight,
      lineHeight: numberInRange(value?.lineHeight, fallback.lineHeight, 0.5, 4),
      color: normalizeColor(value?.color, fallback.color)
    };
  }

  function defaultProfile() {
    return {
      schema: PROFILE_SCHEMA,
      id: "publisher-neutral",
      family: "publisher-neutral",
      name: "Publisher-neutral",
      revision: 1,
      roles: Object.fromEntries(ROLES.map((role) => [role, normalizeRoleStyle(null, role)]))
    };
  }

  function normalizeProfile(value) {
    const fallback = defaultProfile();
    return {
      schema: PROFILE_SCHEMA,
      id: String(value?.id || fallback.id).trim().slice(0, 80) || fallback.id,
      family: "publisher-neutral",
      name: String(value?.name || fallback.name).trim().slice(0, 80) || fallback.name,
      revision: Math.max(1, Math.round(Number(value?.revision) || 1)),
      roles: Object.fromEntries(ROLES.map((role) => [role, normalizeRoleStyle(value?.roles?.[role], role)]))
    };
  }

  function normalizeState(value) {
    const sequence = Array.isArray(value?.panelLabelSequence)
      ? value.panelLabelSequence.map((id) => String(id || "").trim()).filter(Boolean)
      : [];
    return {
      schema: SCHEMA,
      profile: normalizeProfile(value?.profile),
      panelLabelSequence: [...new Set(sequence)],
      lastAppliedAt: String(value?.lastAppliedAt || ""),
      lastAppliedObjectCount: Math.max(0, Math.round(Number(value?.lastAppliedObjectCount) || 0)),
      review: normalizeReviewReceipt(value?.review)
    };
  }

  function normalizeReviewReceipt(value) {
    if (!value || value.schema !== REVIEW_SCHEMA || !value.documentId || !value.auditSignature) return null;
    const records = (Array.isArray(value.records) ? value.records : []).map((record) => ({
      key: String(record?.key || ""),
      signature: String(record?.signature || "")
    })).filter((record) => record.key && record.signature);
    return {
      schema: REVIEW_SCHEMA,
      documentId: String(value.documentId),
      reviewedAt: String(value.reviewedAt || ""),
      auditSignature: String(value.auditSignature),
      planSignature: String(value.planSignature || ""),
      records
    };
  }

  function normalizeRole(value) {
    const role = String(value || "").trim().toLowerCase();
    return ROLES.includes(role) ? role : "";
  }

  function roleForNode(node) {
    if (String(node?.figureType || "").trim() === "panelLabel") return "panel-label";
    return normalizeRole(node?.figureStudioPublicationTypography?.role);
  }

  function binding(role, options) {
    const normalized = normalizeRole(role);
    if (!normalized) return null;
    return {
      schema: BINDING_SCHEMA,
      role: normalized,
      assignedBy: normalized === "panel-label" && options?.automatic !== false ? "panel-label" : "user",
      profileId: String(options?.profileId || "publisher-neutral"),
      profileRevision: Math.max(1, Math.round(Number(options?.profileRevision) || 1))
    };
  }

  function panelLetter(index) {
    let value = Math.max(0, Math.floor(Number(index) || 0));
    let result = "";
    do {
      result = String.fromCharCode(65 + (value % 26)) + result;
      value = Math.floor(value / 26) - 1;
    } while (value >= 0);
    return result;
  }

  function multiplyMatrices(left, right) {
    return [
      left[0] * right[0] + left[2] * right[1],
      left[1] * right[0] + left[3] * right[1],
      left[0] * right[2] + left[2] * right[3],
      left[1] * right[2] + left[3] * right[3],
      left[0] * right[4] + left[2] * right[5] + left[4],
      left[1] * right[4] + left[3] * right[5] + left[5]
    ];
  }

  function transformMatrixPoint(matrix, x, y) {
    return {
      x: matrix[0] * x + matrix[2] * y + matrix[4],
      y: matrix[1] * x + matrix[3] * y + matrix[5]
    };
  }

  function originOffset(value) {
    if (typeof value === "number") return value - 0.5;
    return ({ left: -0.5, top: -0.5, center: 0, right: 0.5, bottom: 0.5 })[String(value || "center")] ?? 0;
  }

  function snapshotDimensionMatrix(node) {
    const scaleX = (node?.flipX ? -1 : 1) * (Number(node?.scaleX) || 1);
    const scaleY = (node?.flipY ? -1 : 1) * (Number(node?.scaleY) || 1);
    let matrix = [scaleX, 0, 0, scaleY, 0, 0];
    const skewX = Math.tan((Number(node?.skewX) || 0) * Math.PI / 180);
    const skewY = Math.tan((Number(node?.skewY) || 0) * Math.PI / 180);
    if (skewX) matrix = multiplyMatrices(matrix, [1, 0, skewX, 1, 0, 0]);
    if (skewY) matrix = multiplyMatrices(matrix, [1, skewY, 0, 1, 0, 0]);
    return matrix;
  }

  function snapshotTransformedDimensions(node) {
    const strokeWidth = Math.max(0, Number(node?.strokeWidth) || 0);
    const strokeUniform = node?.strokeUniform === true;
    const width = Math.max(0, Number(node?.width) || 0) + (strokeUniform ? 0 : strokeWidth);
    const height = Math.max(0, Number(node?.height) || 0) + (strokeUniform ? 0 : strokeWidth);
    const matrix = snapshotDimensionMatrix(node);
    const points = [
      transformMatrixPoint(matrix, -width / 2, -height / 2),
      transformMatrixPoint(matrix, width / 2, -height / 2),
      transformMatrixPoint(matrix, -width / 2, height / 2),
      transformMatrixPoint(matrix, width / 2, height / 2)
    ];
    const result = {
      width: Math.max(...points.map((point) => point.x)) - Math.min(...points.map((point) => point.x)),
      height: Math.max(...points.map((point) => point.y)) - Math.min(...points.map((point) => point.y))
    };
    if (strokeUniform) {
      result.width += strokeWidth;
      result.height += strokeWidth;
    }
    return result;
  }

  function snapshotOwnMatrix(node) {
    const left = Number(node?.left) || 0;
    const top = Number(node?.top) || 0;
    const angle = (Number(node?.angle) || 0) * Math.PI / 180;
    const dimensions = snapshotTransformedDimensions(node);
    const offsetX = -originOffset(node?.originX) * dimensions.width;
    const offsetY = -originOffset(node?.originY) * dimensions.height;
    const centerX = left + offsetX * Math.cos(angle) - offsetY * Math.sin(angle);
    const centerY = top + offsetX * Math.sin(angle) + offsetY * Math.cos(angle);
    const rotation = [Math.cos(angle), Math.sin(angle), -Math.sin(angle), Math.cos(angle), centerX, centerY];
    return multiplyMatrices(rotation, snapshotDimensionMatrix(node));
  }

  function snapshotWorldMetrics(node, parentMatrix = [1, 0, 0, 1, 0, 0]) {
    const ownMatrix = snapshotOwnMatrix(node);
    const matrix = multiplyMatrices(parentMatrix, ownMatrix);
    const dimensions = snapshotTransformedDimensions(node);
    const angle = (Number(node?.angle) || 0) * Math.PI / 180;
    const coordinateMatrix = [Math.cos(angle), Math.sin(angle), -Math.sin(angle), Math.cos(angle), ownMatrix[4], ownMatrix[5]];
    const points = [
      transformMatrixPoint(coordinateMatrix, -dimensions.width / 2, -dimensions.height / 2),
      transformMatrixPoint(coordinateMatrix, dimensions.width / 2, -dimensions.height / 2),
      transformMatrixPoint(coordinateMatrix, -dimensions.width / 2, dimensions.height / 2),
      transformMatrixPoint(coordinateMatrix, dimensions.width / 2, dimensions.height / 2)
    ].map((point) => transformMatrixPoint(parentMatrix, point.x, point.y));
    const left = Math.min(...points.map((point) => point.x));
    const top = Math.min(...points.map((point) => point.y));
    const right = Math.max(...points.map((point) => point.x));
    const bottom = Math.max(...points.map((point) => point.y));
    return worldMetricsFromMatrix(matrix, {
      left,
      top,
      width: right - left,
      height: bottom - top
    });
  }

  function worldMetricsFromMatrix(matrixValue, bounds = {}) {
    const source = Array.isArray(matrixValue) ? matrixValue : [];
    const matrix = [0, 1, 2, 3, 4, 5].map((index) => {
      const value = Number(source[index]);
      return Number.isFinite(value) ? value : (index === 0 || index === 3 ? 1 : 0);
    });
    return {
      matrix,
      // Font size follows the transformed local Y axis, not QR decomposition.
      // This keeps skewY from inventing a vertical scale and lets every page use
      // the same physical-size meaning whether or not a live Fabric object exists.
      scaleX: Math.hypot(matrix[0], matrix[1]),
      scaleY: Math.hypot(matrix[2], matrix[3]),
      left: Number(bounds?.left) || 0,
      top: Number(bounds?.top) || 0,
      width: Math.max(0, Number(bounds?.width) || 0),
      height: Math.max(0, Number(bounds?.height) || 0)
    };
  }

  function spatialPanelOrder(records) {
    const stableKey = (record) => String(record?.objectId || record?.pathKey || "");
    const pages = new Map();
    (records || []).forEach((record) => {
      const pageKey = `${Number(record?.pageIndex || 0)}:${String(record?.pageId || "")}`;
      const page = pages.get(pageKey) || [];
      page.push(record);
      pages.set(pageKey, page);
    });
    return [...pages.entries()]
      .sort(([left], [right]) => left.localeCompare(right, undefined, { numeric: true }))
      .flatMap(([, pageRecords]) => {
        const heights = pageRecords.map((record) => Math.max(1, Number(record?.height) || 12)).sort((left, right) => left - right);
        const medianHeight = heights.length % 2
          ? heights[Math.floor(heights.length / 2)]
          : (heights[Math.max(0, heights.length / 2 - 1)] + heights[Math.floor(heights.length / 2)]) / 2;
        const rowTolerance = Math.max(6, medianHeight * 0.7);
        const remaining = [...pageRecords].sort((left, right) => {
          const centerDelta = (Number(left?.top || 0) + Number(left?.height || 0) / 2) - (Number(right?.top || 0) + Number(right?.height || 0) / 2);
          if (centerDelta) return centerDelta;
          const leftDelta = Number(left?.left || 0) - Number(right?.left || 0);
          return leftDelta || stableKey(left).localeCompare(stableKey(right));
        });
        const rows = [];
        while (remaining.length) {
          const anchor = remaining.shift();
          const anchorCenter = Number(anchor?.top || 0) + Number(anchor?.height || 0) / 2;
          const row = [anchor];
          for (let index = remaining.length - 1; index >= 0; index -= 1) {
            const candidate = remaining[index];
            const center = Number(candidate?.top || 0) + Number(candidate?.height || 0) / 2;
            if (Math.abs(center - anchorCenter) <= rowTolerance) row.push(...remaining.splice(index, 1));
          }
          row.sort((left, right) => {
            const leftDelta = Number(left?.left || 0) - Number(right?.left || 0);
            const topDelta = Number(left?.top || 0) - Number(right?.top || 0);
            return leftDelta || topDelta || stableKey(left).localeCompare(stableKey(right));
          });
          rows.push(row);
        }
        return rows.flat();
      });
  }

  function comparableStyle(record) {
    return {
      fontFamily: String(record?.fontFamily || ""),
      finalSizePt: Number(record?.finalSizePt || 0),
      fontWeight: String(record?.fontWeight || ""),
      lineHeight: Number(record?.lineHeight || 0),
      color: String(record?.color || "").toLowerCase()
    };
  }

  function styleDrift(record, target) {
    const current = comparableStyle(record);
    return Object.keys(current).filter((key) => key === "finalSizePt" || key === "lineHeight"
      ? Math.abs(Number(current[key]) - Number(target[key])) > 0.005
      : String(current[key]) !== String(target[key]));
  }

  function stableSignature(value) {
    const input = JSON.stringify(value);
    let hash = 2166136261;
    for (let index = 0; index < input.length; index += 1) {
      hash ^= input.charCodeAt(index);
      hash = Math.imul(hash, 16777619);
    }
    return (hash >>> 0).toString(16).padStart(8, "0");
  }

  function reviewRecordValue(record) {
    // Fabric persists transforms to four decimal places. Three-place comparison keeps
    // a cold reopen current while still detecting visible scientific-layout changes.
    const rounded = (value) => Number(Number(value || 0).toFixed(3));
    return {
      key: `${String(record?.pageId || "")}:${String(record?.objectId || record?.pathKey || "")}`,
      pageId: String(record?.pageId || ""),
      objectId: String(record?.objectId || record?.pathKey || ""),
      role: normalizeRole(record?.role),
      text: String(record?.text || ""),
      fontFamily: String(record?.fontFamily || ""),
      finalSizePt: rounded(record?.finalSizePt),
      fontWeight: String(record?.fontWeight || ""),
      lineHeight: rounded(record?.lineHeight),
      color: String(record?.color || "").toLowerCase(),
      effectiveScaleY: rounded(record?.effectiveScaleY || 1),
      left: rounded(record?.left),
      top: rounded(record?.top),
      width: rounded(record?.width),
      height: rounded(record?.height),
      overset: Boolean(record?.overset),
      editable: record?.editable !== false
    };
  }

  function createReviewReceipt(records, identity, reviewedAt = "", options = {}) {
    const values = (records || []).map(reviewRecordValue).sort((left, right) => left.key.localeCompare(right.key));
    return normalizeReviewReceipt({
      schema: REVIEW_SCHEMA,
      documentId: String(identity?.documentId || ""),
      reviewedAt: String(reviewedAt || ""),
      auditSignature: stableSignature(values),
      planSignature: String(options?.planSignature || ""),
      records: values.map((record) => ({ key: record.key, signature: stableSignature(record) }))
    });
  }

  function reviewState(stateValue, records, identity) {
    const state = normalizeState(stateValue);
    const receipt = state.review;
    if (!receipt) return { status: "not-reviewed", matched: 0, total: (records || []).length };
    if (!identity?.documentId || receipt.documentId !== String(identity.documentId)) {
      return { status: "stale", matched: 0, total: (records || []).length };
    }
    const current = createReviewReceipt(records, identity, receipt.reviewedAt);
    if (!current) return { status: "stale", matched: 0, total: (records || []).length };
    if (current.auditSignature === receipt.auditSignature) {
      return { status: "current", matched: current.records.length, total: current.records.length, reviewedAt: receipt.reviewedAt };
    }
    const prior = new Map(receipt.records.map((record) => [record.key, record.signature]));
    const matched = current.records.filter((record) => prior.get(record.key) === record.signature).length;
    const total = Math.max(current.records.length, receipt.records.length);
    return { status: matched > 0 ? "partial" : "stale", matched, total, reviewedAt: receipt.reviewedAt };
  }

  function createReviewPlan(records, exclusions, profileValue, identity, options) {
    const profile = normalizeProfile(profileValue);
    const renumber = options?.renumberPanelLabels !== false;
    const editable = (records || []).filter((record) => record.editable && (normalizeRole(record.role) || record.removeRole === true));
    const spatialOrder = spatialPanelOrder(editable.filter((record) => !record.removeRole && record.role === "panel-label"));
    const panelById = new Map(spatialOrder.map((record) => [String(record.objectId || ""), record]));
    const requestedSequence = Array.isArray(options?.panelLabelSequence)
      ? options.panelLabelSequence.map((id) => String(id || "")).filter(Boolean)
      : [];
    const exactRequestedOrder = requestedSequence.length === spatialOrder.length
      && new Set(requestedSequence).size === requestedSequence.length
      && requestedSequence.every((id) => panelById.has(id));
    const panelOrder = exactRequestedOrder ? requestedSequence.map((id) => panelById.get(id)) : spatialOrder;
    const finalPanelGeometrySignature = String(options?.finalPanelGeometrySignature || "");
    const labels = new Map(panelOrder.map((record, index) => [`${record.pageId}:${record.pathKey}`, panelLetter(index)]));
    const changes = editable.map((record) => {
      const target = record.removeRole ? comparableStyle(record) : profile.roles[record.role];
      const targetText = renumber && record.role === "panel-label"
        ? labels.get(`${record.pageId}:${record.pathKey}`) || String(record.text || "")
        : String(record.text || "");
      const drift = styleDrift(record, target);
      if (targetText !== String(record.text || "")) drift.push("text");
      if (record.pendingRoleAssignment || record.removeRole) drift.push("role");
      return {
        ...record,
        before: comparableStyle(record),
        after: { ...target },
        beforeText: String(record.text || ""),
        afterText: targetText,
        resultingRole: record.removeRole ? "" : record.role,
        drift,
        willChange: drift.length > 0,
        reflowRisk: drift.some((field) => ["fontFamily", "finalSizePt", "fontWeight", "lineHeight"].includes(field)),
        oversetWarning: Boolean(record.overset)
      };
    });
    const affected = changes.filter((record) => record.willChange);
    const signatureInput = {
      identity,
      profile,
      renumber,
      panelLabelSequence: panelOrder.map((record) => record.objectId).filter(Boolean),
      finalPanelGeometrySignature,
      changes: changes.map((record) => [record.pageId, record.pathKey, record.role, record.removeRole, record.before, record.beforeText, record.after, record.afterText, record.editable]),
      geometry: changes.map((record) => [record.pageId, record.pathKey, record.effectiveScaleY, record.left, record.top, record.width, record.height, record.overset]),
      exclusions: (exclusions || []).map((item) => [item.pageId, item.pathKey, item.reason])
    };
    return {
      schema: "figureStudio.publicationTypographyReview.v1",
      valid: affected.length > 0,
      identity: { ...(identity || {}) },
      profile,
      renumberPanelLabels: renumber,
      records: changes,
      affected,
      exclusions: [...(exclusions || [])],
      affectedObjectCount: affected.length,
      affectedPageCount: new Set(affected.map((record) => record.pageId)).size,
      roleCounts: Object.fromEntries(ROLES.map((role) => [role, editable.filter((record) => !record.removeRole && record.role === role).length])),
      panelLabelSequence: panelOrder.map((record) => record.objectId).filter(Boolean),
      finalPanelGeometrySignature,
      signature: stableSignature(signatureInput)
    };
  }

  return Object.freeze({
    SCHEMA,
    PROFILE_SCHEMA,
    BINDING_SCHEMA,
    REVIEW_SCHEMA,
    UNASSIGN_ROLE,
    ROLES,
    ROLE_LABELS,
    DEFAULT_ROLE_STYLES,
    defaultProfile,
    normalizeProfile,
    normalizeState,
    normalizeRole,
    roleForNode,
    binding,
    panelLetter,
    multiplyMatrices,
    snapshotOwnMatrix,
    worldMetricsFromMatrix,
    snapshotWorldMetrics,
    spatialPanelOrder,
    styleDrift,
    stableSignature,
    createReviewReceipt,
    reviewState,
    createReviewPlan
  });
}));
