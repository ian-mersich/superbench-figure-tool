(function attachFigureStudioScientificAssetDiscovery(root, factory) {
  const commonJs = typeof module === "object" && module.exports;
  const api = factory(
    commonJs ? require("./scientific-asset-catalog.js") : root?.FigureStudioScientificAssetCatalog,
    commonJs ? require("./scientific-scene-catalog.js") : root?.FigureStudioScientificSceneCatalog
  );
  if (commonJs) module.exports = api;
  if (root) root.FigureStudioScientificAssetDiscovery = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function createScientificAssetDiscoveryApi(assetApi, sceneApi) {
  "use strict";

  const DEFAULT_LIMIT = 4;
  const MAX_LIMIT = 6;
  const IDENTITY_FIELDS = new Set(["scientificName", "synonym", "name"]);

  function classifyMatch(relevance) {
    // `exact` also covers exact contextual tags in the catalog scorer.
    if (relevance?.identityExact === true) return "exact-name";
    const fields = Array.isArray(relevance?.matchedFields) ? relevance.matchedFields : [];
    if (!fields.length) return "";
    return fields.every((field) => IDENTITY_FIELDS.has(field)) ? "name" : "context";
  }

  function sceneRecords(libraryOrScenes, query, options) {
    if (!sceneApi?.searchScenes) return [];
    const category = options.category === "all" ? "" : options.category;
    return sceneApi.searchScenes(libraryOrScenes, { ...options, category, query }).map((scene) => ({
      ...scene,
      concept_id: scene.id,
      description: scene.summary
    }));
  }

  function search(source, query, scope, options) {
    if (scope === "assets") return assetApi.searchAssets(source, query, options);
    // Retain scene category/mode eligibility and require the same protected
    // biological query units as Assets. This projection never changes scenes.
    return assetApi.searchAssets(sceneRecords(source, query, options), query);
  }

  /**
   * Suggest complete names from records already matching this query. These are
   * search refinements, not inferred synonyms or biological relationships.
   * `scope` selects the source type; other options are existing catalog filters.
   * Assets accept a catalog/asset array; Scenes accept a library/scene array.
   * Counts are distinct concepts (scene IDs in Scenes), not drawing variants.
   */
  function recommendQueries(source, query, options = {}) {
    if (!assetApi?.searchAssets || !assetApi?.singularPhrase) return [];
    const input = String(query ?? "").trim();
    if (!assetApi.normalizeText(input)) return [];
    const { scope = "assets", limit = DEFAULT_LIMIT, ...filters } = options;
    if (scope !== "assets" && scope !== "scenes") return [];
    const numericLimit = Number(limit);
    const bound = Number.isFinite(numericLimit)
      ? Math.min(MAX_LIMIT, Math.max(0, Math.floor(numericLimit))) : DEFAULT_LIMIT;
    if (!bound) return [];
    const matches = search(source, input, scope, filters);
    const seenForms = new Set();
    const seenQueries = new Set([assetApi.singularPhrase(input)]);
    const recommendations = [];
    for (const match of matches) {
      const asset = match.asset;
      const conceptId = match.conceptId;
      const formId = scope === "assets" ? assetApi.scientificAssetFormId(asset) : "default";
      const formKey = JSON.stringify([conceptId, formId]);
      if (seenForms.has(formKey)) continue;
      seenForms.add(formKey);
      const fields = [
        ["name", asset.name],
        asset.scientific_name
          ? ["scientific_name", asset.scientific_name] : ["scientificName", asset.scientificName]
      ];
      for (const [sourceField, value] of fields) {
        if (typeof value !== "string") continue;
        const candidate = value.trim();
        const key = assetApi.singularPhrase(candidate);
        if (!key || seenQueries.has(key)) continue;
        const candidateMatches = search(source, candidate, scope, filters);
        if (!candidateMatches.some((entry) => entry.assetId === match.assetId)) continue;
        seenQueries.add(key);
        recommendations.push({
          query: candidate,
          label: candidate,
          count: new Set(candidateMatches.map((entry) => entry.conceptId)).size,
          kind: classifyMatch(match.relevance),
          scope,
          sourceId: match.assetId,
          conceptId,
          sourceField,
          matchedFields: [...match.relevance.matchedFields]
        });
        break;
      }
      if (recommendations.length >= bound) break;
    }
    return recommendations;
  }

  // Compare the editable artwork inside a bundled drawing, excluding its
  // canvas placement and generated identities. The caller supplies a fresh
  // source drawing with the current semantic part colors already applied.
  function drawingContentSignature(record) {
    const fields = ["type", "left", "top", "width", "height", "scaleX", "scaleY", "angle", "skewX", "skewY",
      "flipX", "flipY", "originX", "originY", "path", "points", "rx", "ry", "radius", "x1", "y1", "x2", "y2",
      "fill", "stroke", "strokeWidth", "strokeDashArray", "strokeDashOffset", "strokeLineCap", "strokeLineJoin",
      "strokeMiterLimit", "fillRule", "paintFirst", "opacity", "visible", "clipPath", "text", "fontFamily", "fontSize",
      "fontWeight", "fontStyle", "lineHeight", "charSpacing", "textAlign", "styles", "shadow", "globalCompositeOperation",
      "strokeUniform", "backgroundColor", "filters", "figureStudioAppearanceStack", "figureStudioStrokeWidthProfile",
      "figureStudioClipMaskMeta", "figureStudioCompoundPathMeta", "figureStudioLiveBooleanMeta"];
    const normalize = (value) => {
      if (typeof value === "number") return Math.round(value * 1e6) / 1e6;
      if (Array.isArray(value)) return value.map(normalize);
      if (value && typeof value === "object") return Object.fromEntries(Object.keys(value).sort().map((key) => [key, normalize(value[key])]));
      return value;
    };
    const content = (node, root = false) => {
      const result = {};
      for (const key of fields) {
        if (root && ["left", "top", "width", "height", "scaleX", "scaleY", "angle", "skewX", "skewY", "flipX", "flipY", "originX", "originY", "opacity", "visible"].includes(key)) continue;
        if (Object.hasOwn(node || {}, key)) result[key] = normalize(node[key]);
      }
      if (Array.isArray(node?.objects)) result.objects = node.objects.map((child) => content(child));
      return result;
    };
    return JSON.stringify(content(record, true));
  }

  return Object.freeze({ DEFAULT_LIMIT, MAX_LIMIT, classifyMatch, recommendQueries, drawingContentSignature });
});
