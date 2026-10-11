/*
 * Canonical Figure Tool export-review helpers.
 *
 * The editor's existing Figure check remains the source of issues. This
 * module only gives those records stable identities, removes exact repeats,
 * and coordinates asynchronous review work so stale previews cannot replace
 * the review for a newer document or export choice.
 */
(function exposeFigureStudioExportReview(root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  if (root) root.FigureStudioExportReview = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function createFigureStudioExportReviewModule() {
  "use strict";

  const VERSION = "1.0.0";
  const SEVERITIES = Object.freeze(["error", "warning", "info", "pass"]);
  const SEVERITY_RANK = Object.freeze({ error: 4, warning: 3, info: 2, pass: 1 });

  function normalizedText(value) {
    return String(value == null ? "" : value).replace(/\s+/g, " ").trim();
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

  function canonicalIssueIdentity(issue = {}) {
    const code = normalizedText(issue.code || "review-note").toLowerCase();
    const page = normalizedText(issue.pageId || issue.page_id || "document").toLowerCase();
    const object = normalizedText(issue.objectId || issue.object_id || "document").toLowerCase();
    const message = normalizedText(issue.message).toLowerCase();
    return `figure-check:${code}:${page}:${object}:${stableHash(message)}`;
  }

  function canonicalizeIssues(issues = []) {
    const byIdentity = new Map();
    (Array.isArray(issues) ? issues : []).forEach((source) => {
      if (!source || typeof source !== "object") return;
      const identity = canonicalIssueIdentity(source);
      const candidate = {
        ...source,
        severity: SEVERITIES.includes(source.severity) ? source.severity : "info",
        id: identity,
        identity
      };
      const current = byIdentity.get(identity);
      if (!current || SEVERITY_RANK[candidate.severity] > SEVERITY_RANK[current.severity]) {
        byIdentity.set(identity, candidate);
      }
    });
    return [...byIdentity.values()];
  }

  function countIssues(issues = []) {
    const counts = { error: 0, warning: 0, info: 0, pass: 0 };
    canonicalizeIssues(issues).forEach((issue) => { counts[issue.severity] += 1; });
    return counts;
  }

  function planFingerprint(plan = {}) {
    const normalized = {
      documentId: String(plan.document?.id || ""),
      format: String(plan.format || ""),
      scope: String(plan.scope || ""),
      outputKind: String(plan.outputKind || ""),
      background: plan.background || null,
      targets: (Array.isArray(plan.targets) ? plan.targets : []).map((target) => ({
        id: String(target.id || ""),
        filename: String(target.filename || ""),
        geometry: target.geometry || null,
        resolution: target.resolution || null,
        sourceObjectCount: Number(target.source?.fabric?.objects?.length || 0)
      }))
    };
    return stableHash(JSON.stringify(normalized));
  }

  function requestKey(documentDescriptor = {}, request = {}, reviewSettings = null, plan = null) {
    const normalized = {
      documentId: String(documentDescriptor.id || ""),
      nativeDocumentId: String(documentDescriptor.nativeDocumentId || ""),
      projectRevision: Number(documentDescriptor.projectRevision || 0),
      workspaceProjectGeneration: Number(documentDescriptor.workspaceProjectGeneration || 0),
      format: String(request.format || ""),
      scope: String(request.scope || ""),
      delivery: String(request.delivery || ""),
      resolution: request.resolution || null,
      background: request.background || null,
      reviewSettings: reviewSettings || null,
      planFingerprint: plan ? planFingerprint(plan) : ""
    };
    return JSON.stringify(normalized);
  }

  function createCoordinator() {
    let epoch = 0;
    return Object.freeze({
      begin() {
        epoch += 1;
        return epoch;
      },
      invalidate() {
        epoch += 1;
        return epoch;
      },
      current() {
        return epoch;
      },
      isCurrent(candidate) {
        return Number(candidate) === epoch;
      }
    });
  }

  function previewLimitations(format, capped = false) {
    const vector = ["svg", "pdf", "pptx"].includes(String(format || "").toLowerCase());
    const first = capped
      ? "This screen preview is reduced to fit the preview area; it keeps the selected output aspect ratio."
      : "This is a screen rendering at the selected output size and aspect ratio.";
    const second = vector
      ? "Vector output remains vector where the selected format and source artwork support it."
      : "The exported raster uses the pixel dimensions shown above.";
    return `${first} ${second} It does not simulate a printer, paper, bleed, CMYK conversion, ICC profile, or font handling in another application.`;
  }

  return Object.freeze({
    VERSION,
    SEVERITIES,
    canonicalIssueIdentity,
    canonicalizeIssues,
    countIssues,
    requestKey,
    planFingerprint,
    createCoordinator,
    previewLimitations,
    testing: Object.freeze({ stableHash, normalizedText })
  });
});
