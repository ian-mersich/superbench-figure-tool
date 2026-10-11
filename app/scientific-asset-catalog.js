(function attachFigureStudioScientificAssetCatalog(root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  if (root) root.FigureStudioScientificAssetCatalog = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function createScientificAssetCatalogApi() {
  "use strict";

  const DEFAULT_RECENT_LIMIT = 12;
  const MAX_RECENT_LIMIT = 50;
  const FIELD_WEIGHTS = Object.freeze({
    scientificName: 16,
    synonym: 14,
    name: 12,
    tag: 7,
    subcategory: 6,
    category: 4,
    description: 2,
    id: 1
  });
  const GREEK_LETTERS = Object.freeze({
    "α": "alpha", "β": "beta", "γ": "gamma", "δ": "delta", "ε": "epsilon",
    "ζ": "zeta", "η": "eta", "θ": "theta", "ι": "iota", "κ": "kappa", "λ": "lambda",
    "μ": "mu", "ν": "nu", "ξ": "xi", "ο": "omicron", "π": "pi", "ρ": "rho",
    "σ": "sigma", "ς": "sigma", "τ": "tau", "υ": "upsilon", "φ": "phi",
    "χ": "chi", "ψ": "psi", "ω": "omega"
  });
  const IRREGULAR_SINGULARS = Object.freeze({
    analyses: "analysis",
    antibodies: "antibody",
    assays: "assay",
    bacteria: "bacterium",
    complexes: "complex",
    erythrocytes: "erythrocyte",
    fungi: "fungus",
    lysosomes: "lysosome",
    media: "medium",
    mice: "mouse",
    mitochondria: "mitochondrion",
    nuclei: "nucleus",
    organelles: "organelle",
    stimuli: "stimulus",
    vesicles: "vesicle"
  });

  // These equivalences are intentionally narrow. Multi-word cell identities remain
  // one query unit, so a search for a T cell cannot degrade into a search for any cell.
  const DOMAIN_EQUIVALENT_GROUPS = Object.freeze([
    Object.freeze(["t cell", "t lymphocyte", "tcell"]),
    Object.freeze(["b cell", "b lymphocyte", "bcell"]),
    Object.freeze(["nk cell", "natural killer cell", "natural killer"]),
    Object.freeze(["red blood cell", "rbc", "erythrocyte"]),
    Object.freeze(["mitochondrion", "mitochondria", "mitochondrial"]),
    Object.freeze(["tumor", "tumour"]),
    Object.freeze(["qpcr", "q pcr", "real time pcr", "quantitative pcr"]),
    Object.freeze(["western blot", "western", "immunoblot", "protein blot"]),
    Object.freeze(["flow cytometry", "facs", "fluorescence activated cell sorting"]),
    Object.freeze(["extracellular matrix", "ecm"]),
    Object.freeze(["organoid", "3d culture", "three dimensional culture"])
  ]);

  function arrayOf(value) {
    return Array.isArray(value) ? value : [];
  }

  function text(value) {
    return String(value ?? "").trim();
  }

  function uniqueText(values) {
    return [...new Set(arrayOf(values).map(text).filter(Boolean))];
  }

  function normalizeText(value) {
    return text(value)
      .toLowerCase()
      .replace(/[α-ως]/g, (letter) => ` ${GREEK_LETTERS[letter] || letter} `)
      .normalize("NFKD")
      .replace(/[\u0300-\u036f]/g, "")
      .replace(/[\u2010-\u2015\u2212\uFE58\uFE63\uFF0D_-]+/g, " ")
      .replace(/&/g, " and ")
      .replace(/[^a-z0-9]+/g, " ")
      .replace(/\s+/g, " ")
      .trim();
  }

  function singularToken(token) {
    const word = text(token);
    if (!word) return "";
    if (IRREGULAR_SINGULARS[word]) return IRREGULAR_SINGULARS[word];
    if (word.length > 4 && /ies$/.test(word)) return `${word.slice(0, -3)}y`;
    if (word.length > 4 && /(ches|shes|sses|xes|zes)$/.test(word)) return word.slice(0, -2);
    if (word.length > 3 && /s$/.test(word) && !/(ss|us|is)$/.test(word)) return word.slice(0, -1);
    return word;
  }

  function singularPhrase(value) {
    return normalizeText(value).split(" ").filter(Boolean).map(singularToken).join(" ");
  }

  function normalizedStringArray(value) {
    if (Array.isArray(value)) return uniqueText(value);
    return text(value) ? [text(value)] : [];
  }

  function normalizeBaseUrl(value) {
    const base = text(value).replace(/\\/g, "/");
    return base && !base.endsWith("/") ? `${base}/` : base;
  }

  function directoryUrl(value) {
    const url = text(value).replace(/\\/g, "/");
    const boundary = Math.max(url.lastIndexOf("/"), url.lastIndexOf("\\"));
    return boundary >= 0 ? url.slice(0, boundary + 1) : "";
  }

  function resolveAssetUrl(baseUrl, filePath) {
    const file = text(filePath).replace(/\\/g, "/");
    if (!file) return "";
    if (/^(?:[a-z][a-z0-9+.-]*:|\/\/)/i.test(file)) return file;
    const base = normalizeBaseUrl(baseUrl);
    if (!base) return file.replace(/^\.\//, "");
    try {
      if (/^(?:[a-z][a-z0-9+.-]*:|\/\/)/i.test(base)) return new URL(file.replace(/^\/+/, ""), base).href;
    } catch (_error) {
      // Custom desktop protocols are still safe to join as resource paths.
    }
    const segments = `${base}${file.replace(/^\/+/, "")}`.split("/");
    const resolved = [];
    for (const segment of segments) {
      if (segment === ".") continue;
      if (segment === ".." && resolved.length && resolved[resolved.length - 1] !== "..") resolved.pop();
      else if (segment !== ".." || !resolved.length) resolved.push(segment);
    }
    return resolved.join("/");
  }

  function sourceDescriptor(source, index) {
    const descriptor = source && typeof source === "object" ? source : {};
    const pack = descriptor.pack || descriptor.payload || descriptor;
    if (!pack || typeof pack !== "object") throw new TypeError(`Scientific asset pack ${index + 1} is not an object.`);
    const explicitBase = descriptor.pack || descriptor.payload
      ? descriptor.baseUrl ?? descriptor.baseURL ?? (descriptor.packUrl ? directoryUrl(descriptor.packUrl) : "")
      : descriptor.baseUrl ?? descriptor.base_url ?? "";
    return { pack, baseUrl: normalizeBaseUrl(explicitBase) };
  }

  function scientificAssetConceptId(asset) {
    return text(asset?.concept_id || asset?.conceptId || asset?.assetId || asset?.id);
  }

  function normalizeAsset(asset, packMeta, assetOrder, catalogOrder) {
    if (!asset || typeof asset !== "object") {
      throw new TypeError(`Asset ${assetOrder + 1} in pack "${packMeta.id}" is not an object.`);
    }
    const id = text(asset.id);
    if (!id) throw new Error(`Asset ${assetOrder + 1} in pack "${packMeta.id}" is missing a stable id.`);
    const file = text(asset.file);
    return {
      ...asset,
      id,
      name: text(asset.name) || id,
      scientific_name: text(asset.scientific_name || asset.scientificName),
      synonyms: normalizedStringArray(asset.synonyms || asset.aliases),
      category: text(asset.category) || "uncategorized",
      subcategory: text(asset.subcategory),
      tags: normalizedStringArray(asset.tags),
      description: text(asset.description),
      file,
      editable_color_regions: arrayOf(asset.editable_color_regions),
      concept_id: scientificAssetConceptId(asset) || id,
      _conceptId: scientificAssetConceptId(asset) || id,
      _packId: packMeta.id,
      _packName: packMeta.name,
      _baseUrl: packMeta.baseUrl,
      _svgUrl: resolveAssetUrl(packMeta.baseUrl, file),
      _packOrder: packMeta.order,
      _assetOrder: assetOrder,
      _catalogOrder: catalogOrder
    };
  }

  function deriveConceptGroups(assets) {
    const groups = new Map();
    for (const asset of arrayOf(assets)) {
      const conceptId = scientificAssetConceptId(asset);
      if (!conceptId) continue;
      if (!groups.has(conceptId)) groups.set(conceptId, []);
      groups.get(conceptId).push(asset);
    }
    return [...groups.entries()].map(([conceptId, variants], groupOrder) => {
      const ordered = variants.slice().sort(compareCatalogAssets);
      const primary = ordered.find((asset) => normalizeText(asset.style_variant) === "soft line") || ordered[0];
      return {
        conceptId,
        concept_id: conceptId,
        name: primary?.name || conceptId,
        scientific_name: primary?.scientific_name || "",
        category: primary?.category || "uncategorized",
        subcategory: primary?.subcategory || "",
        primary,
        variants: ordered,
        assetIds: ordered.map((asset) => asset.id),
        packIds: [...new Set(ordered.map((asset) => asset._packId).filter(Boolean))],
        catalogOrder: Math.min(...ordered.map((asset) => finiteOrder(asset._catalogOrder))),
        groupOrder
      };
    }).sort((left, right) => left.catalogOrder - right.catalogOrder || compareText(left.conceptId, right.conceptId));
  }

  function normalizePackSources(sources) {
    const list = Array.isArray(sources) ? sources : [sources];
    const seenAssetIds = new Map();
    const assets = [];
    const packs = [];
    list.forEach((source, packOrder) => {
      const { pack, baseUrl } = sourceDescriptor(source, packOrder);
      const packId = text(pack.id) || `pack-${packOrder + 1}`;
      const packMeta = {
        ...pack,
        id: packId,
        name: text(pack.name) || packId,
        baseUrl,
        order: packOrder,
        assetCount: arrayOf(pack.assets).length
      };
      delete packMeta.assets;
      packs.push(packMeta);
      arrayOf(pack.assets).forEach((asset, assetOrder) => {
        const normalized = normalizeAsset(asset, packMeta, assetOrder, assets.length);
        if (seenAssetIds.has(normalized.id)) {
          const firstPack = seenAssetIds.get(normalized.id);
          throw new Error(`Duplicate scientific asset id "${normalized.id}" in packs "${firstPack}" and "${packId}".`);
        }
        seenAssetIds.set(normalized.id, packId);
        assets.push(normalized);
      });
    });
    const conceptGroups = deriveConceptGroups(assets);
    return {
      schema: "figureStudio.scientificAssetCatalog.v1",
      packs,
      assets,
      byId: Object.fromEntries(assets.map((asset) => [asset.id, asset])),
      conceptGroups,
      byConceptId: Object.fromEntries(conceptGroups.map((group) => [group.conceptId, group])),
      categories: [...new Set(assets.map((asset) => asset.category))].sort(compareText),
      subcategories: [...new Set(assets.map((asset) => asset.subcategory).filter(Boolean))].sort(compareText)
    };
  }

  const EQUIVALENT_LOOKUP = buildEquivalentLookup();

  function buildEquivalentLookup() {
    const entries = [];
    DOMAIN_EQUIVALENT_GROUPS.forEach((group, groupIndex) => {
      const alternatives = [...new Set(group.flatMap((phrase) => [normalizeText(phrase), singularPhrase(phrase)]).filter(Boolean))];
      alternatives.forEach((phrase) => entries.push({
        groupIndex,
        phrase,
        tokens: phrase.split(" "),
        alternatives
      }));
    });
    return entries.sort((left, right) => right.tokens.length - left.tokens.length || right.phrase.length - left.phrase.length);
  }

  function queryUnits(query) {
    const normalized = normalizeText(query);
    const tokens = normalized.split(" ").filter(Boolean);
    const units = [];
    for (let index = 0; index < tokens.length;) {
      const equivalent = EQUIVALENT_LOOKUP.find((entry) => (
        entry.tokens.length <= tokens.length - index
        && entry.tokens.every((token, offset) => token === tokens[index + offset])
      ));
      if (equivalent) {
        units.push({
          key: `domain:${equivalent.groupIndex}`,
          source: tokens.slice(index, index + equivalent.tokens.length).join(" "),
          alternatives: equivalent.alternatives,
          domainEquivalent: true
        });
        index += equivalent.tokens.length;
      } else {
        const singular = singularToken(tokens[index]);
        units.push({ key: `term:${singular}`, source: tokens[index], alternatives: [singular], domainEquivalent: false });
        index += 1;
      }
    }
    const seen = new Set();
    return {
      normalized,
      units: units.filter((unit) => unit.alternatives[0] && !seen.has(unit.key) && seen.add(unit.key))
    };
  }

  function assetSearchFields(asset) {
    return [
      ...normalizedStringArray(asset.scientific_name || asset.scientificName).map((value) => ({ field: "scientificName", value })),
      ...normalizedStringArray(asset.synonyms || asset.aliases).map((value) => ({ field: "synonym", value })),
      { field: "name", value: asset.name },
      ...normalizedStringArray(asset.tags).map((value) => ({ field: "tag", value })),
      { field: "subcategory", value: asset.subcategory },
      { field: "category", value: asset.category },
      { field: "description", value: asset.description },
      { field: "id", value: asset.id }
    ].filter((entry) => text(entry.value)).map((entry) => ({
      ...entry,
      normalized: normalizeText(entry.value),
      singular: singularPhrase(entry.value)
    }));
  }

  function includesPhrase(haystack, needle) {
    return ` ${haystack} `.includes(` ${needle} `);
  }

  function phraseMatch(field, alternative) {
    const candidates = [...new Set([field.normalized, field.singular].filter(Boolean))];
    const query = singularPhrase(alternative);
    if (!query) return null;
    let strength = 0;
    let kind = "";
    for (const candidate of candidates) {
      if (candidate === query && strength < 20) { strength = 20; kind = "exact"; }
      else if (candidate.startsWith(`${query} `) && strength < 15) { strength = 15; kind = "prefix"; }
      else if (includesPhrase(candidate, query) && strength < 12) { strength = 12; kind = "phrase"; }
      else {
        const queryTokens = query.split(" ");
        const candidateTokens = new Set(candidate.split(" "));
        if (queryTokens.length > 1 && queryTokens.every((token) => candidateTokens.has(token)) && strength < 8) {
          strength = 8;
          kind = "tokens";
        }
      }
    }
    return strength ? { strength, kind, query } : null;
  }

  function scoreAsset(asset, parsedQuery) {
    if (!parsedQuery.units.length) return { score: 0, exact: false, matchedFields: [], matchedTerms: [], matches: [] };
    const fields = assetSearchFields(asset);
    const matches = [];
    for (const unit of parsedQuery.units) {
      let best = null;
      for (const field of fields) {
        for (const alternative of unit.alternatives) {
          const match = phraseMatch(field, alternative);
          if (!match) continue;
          const score = FIELD_WEIGHTS[field.field] * match.strength;
          const candidate = { unit: unit.source, alternative, field: field.field, kind: match.kind, score };
          if (!best || candidate.score > best.score || (
            candidate.score === best.score && compareText(`${candidate.field}:${candidate.alternative}`, `${best.field}:${best.alternative}`) < 0
          )) best = candidate;
        }
      }
      if (!best) return null;
      matches.push(best);
    }
    const wholeQueryExact = fields.some((field) => (
      ["scientificName", "synonym", "name"].includes(field.field)
      && (field.normalized === parsedQuery.normalized || field.singular === singularPhrase(parsedQuery.normalized))
    ));
    const score = matches.reduce((total, match) => total + match.score, 0) + (wholeQueryExact ? 100 : 0);
    return {
      score,
      exact: wholeQueryExact || matches.every((match) => match.kind === "exact"),
      matchedFields: [...new Set(matches.map((match) => match.field))],
      matchedTerms: [...new Set(matches.map((match) => match.alternative))],
      matches
    };
  }

  function finiteOrder(value) {
    const number = Number(value);
    return Number.isFinite(number) ? number : Number.MAX_SAFE_INTEGER;
  }

  function compareText(left, right) {
    const a = String(left ?? "");
    const b = String(right ?? "");
    return a < b ? -1 : a > b ? 1 : 0;
  }

  function compareCatalogAssets(left, right) {
    return finiteOrder(left?._catalogOrder) - finiteOrder(right?._catalogOrder) || compareText(left?.id, right?.id);
  }

  function normalizedFilter(value) {
    const source = Array.isArray(value) ? value : text(value) ? [value] : [];
    return new Set(source.map(normalizeText).filter((entry) => entry && entry !== "all"));
  }

  function normalizedConceptIds(values) {
    return uniqueText(values);
  }

  function searchOrderBy(parsedQuery, options) {
    const requested = text(options.orderBy).toLowerCase();
    if (["relevance", "catalog", "favorites", "recent"].includes(requested)) return requested;
    const discovery = text(options.discovery || options.scope).toLowerCase();
    if (options.recentOnly === true || discovery === "recent") return "recent";
    if (options.favoritesOnly === true || discovery === "favorites") return "favorites";
    return parsedQuery.units.length ? "relevance" : "catalog";
  }

  function searchAssets(catalogOrAssets, query = "", options = {}) {
    const assets = Array.isArray(catalogOrAssets) ? catalogOrAssets : arrayOf(catalogOrAssets?.assets);
    const parsedQuery = queryUnits(query);
    const categories = normalizedFilter(options.category ?? options.categories);
    const subcategories = normalizedFilter(options.subcategory ?? options.subcategories);
    const favoriteIds = normalizedConceptIds(options.favoriteConceptIds);
    const recentIds = normalizedConceptIds(options.recentConceptIds);
    const favoriteIndex = new Map(favoriteIds.map((id, index) => [id, index]));
    const recentIndex = new Map(recentIds.map((id, index) => [id, index]));
    const discovery = text(options.discovery || options.scope).toLowerCase();
    const favoritesOnly = options.favoritesOnly === true || discovery === "favorites";
    const recentOnly = options.recentOnly === true || discovery === "recent";
    const orderBy = searchOrderBy(parsedQuery, options);
    const results = [];
    for (const asset of assets) {
      const conceptId = scientificAssetConceptId(asset);
      if (categories.size && !categories.has(normalizeText(asset.category))) continue;
      if (subcategories.size && !subcategories.has(normalizeText(asset.subcategory))) continue;
      if (favoritesOnly && !favoriteIndex.has(conceptId)) continue;
      if (recentOnly && !recentIndex.has(conceptId)) continue;
      const relevance = scoreAsset(asset, parsedQuery);
      if (!relevance) continue;
      results.push({
        asset,
        assetId: asset.id,
        conceptId,
        relevance,
        score: relevance.score,
        isFavorite: favoriteIndex.has(conceptId),
        favoriteIndex: favoriteIndex.has(conceptId) ? favoriteIndex.get(conceptId) : -1,
        recentIndex: recentIndex.has(conceptId) ? recentIndex.get(conceptId) : -1,
        catalogOrder: finiteOrder(asset._catalogOrder)
      });
    }
    results.sort((left, right) => compareSearchResults(left, right, orderBy));
    return results.map((result, index) => ({
      ...result,
      rank: index + 1,
      order: {
        by: orderBy,
        score: result.score,
        catalog: result.catalogOrder,
        favorite: result.favoriteIndex,
        recent: result.recentIndex,
        id: result.assetId
      }
    }));
  }

  function compareSearchResults(left, right, orderBy) {
    if (orderBy === "recent") {
      const recent = finiteOrder(left.recentIndex < 0 ? undefined : left.recentIndex) - finiteOrder(right.recentIndex < 0 ? undefined : right.recentIndex);
      if (recent) return recent;
    } else if (orderBy === "favorites") {
      const favorite = finiteOrder(left.favoriteIndex < 0 ? undefined : left.favoriteIndex) - finiteOrder(right.favoriteIndex < 0 ? undefined : right.favoriteIndex);
      if (favorite) return favorite;
    }
    if (orderBy === "relevance" || (orderBy !== "catalog" && left.score !== right.score)) {
      const relevance = right.score - left.score;
      if (relevance) return relevance;
    }
    return left.catalogOrder - right.catalogOrder || compareText(left.assetId, right.assetId);
  }

  function searchCatalog(catalog, query = "", options = {}) {
    const assetResults = searchAssets(catalog, query, options);
    const parsedQuery = queryUnits(query);
    const byConcept = new Map();
    for (const result of assetResults) {
      if (!byConcept.has(result.conceptId)) byConcept.set(result.conceptId, []);
      byConcept.get(result.conceptId).push(result);
    }
    const conceptResults = [];
    for (const [conceptId, matchedAssets] of byConcept) {
      const group = catalog?.byConceptId?.[conceptId]
        || deriveConceptGroups(matchedAssets.map((entry) => entry.asset))[0];
      const best = matchedAssets.slice().sort((left, right) => compareSearchResults(left, right, "relevance"))[0];
      conceptResults.push({
        conceptId,
        group,
        asset: best.asset,
        variants: group?.variants || matchedAssets.map((entry) => entry.asset),
        matchedAssetIds: matchedAssets.map((entry) => entry.assetId),
        relevance: best.relevance,
        score: best.score,
        isFavorite: best.isFavorite,
        favoriteIndex: best.favoriteIndex,
        recentIndex: best.recentIndex,
        catalogOrder: group?.catalogOrder ?? best.catalogOrder
      });
    }
    const orderBy = searchOrderBy(parsedQuery, options);
    conceptResults.sort((left, right) => compareSearchResults({ ...left, assetId: left.conceptId }, { ...right, assetId: right.conceptId }, orderBy));
    const results = conceptResults.map((result, index) => ({
      ...result,
      rank: index + 1,
      order: {
        by: orderBy,
        score: result.score,
        catalog: result.catalogOrder,
        favorite: result.favoriteIndex,
        recent: result.recentIndex,
        id: result.conceptId
      }
    }));
    return {
      query: text(query),
      normalizedQuery: parsedQuery.normalized,
      orderBy,
      resultCount: results.length,
      assetMatchCount: assetResults.length,
      results
    };
  }

  function updateRecentConceptIds(currentIds, conceptId, limit = DEFAULT_RECENT_LIMIT) {
    const id = text(conceptId);
    const boundedLimit = Math.min(MAX_RECENT_LIMIT, Math.max(1, Math.floor(Number(limit) || DEFAULT_RECENT_LIMIT)));
    const remaining = normalizedConceptIds(currentIds).filter((entry) => entry !== id);
    return (id ? [id, ...remaining] : remaining).slice(0, boundedLimit);
  }

  function toggleFavoriteConceptId(currentIds, conceptId) {
    const id = text(conceptId);
    const ids = normalizedConceptIds(currentIds);
    if (!id) return ids;
    return ids.includes(id) ? ids.filter((entry) => entry !== id) : [...ids, id];
  }

  function currentBrandDescription(description) {
    // Display the continuing project's current name. The original provenance
    // string remains unchanged in the catalog and saved object metadata.
    return String(description || "")
      .replace(/\bFigure[ _-]Studio\b/gi, "Superbench Figure Tool")
      .replace(/\bBSD[ _-]Studio\b/gi, "Mersich Lab Superbench")
      .replace(/\bFree[ _-]?Bench\b/gi, "Superbench");
  }

  return Object.freeze({
    DEFAULT_RECENT_LIMIT,
    MAX_RECENT_LIMIT,
    FIELD_WEIGHTS,
    DOMAIN_EQUIVALENT_GROUPS,
    normalizeText,
    currentBrandDescription,
    singularPhrase,
    resolveAssetUrl,
    scientificAssetConceptId,
    normalizePackSources,
    deriveConceptGroups,
    searchAssets,
    searchCatalog,
    updateRecentConceptIds,
    toggleFavoriteConceptId,
    updateRecent: updateRecentConceptIds,
    toggleFavorite: toggleFavoriteConceptId
  });
});
