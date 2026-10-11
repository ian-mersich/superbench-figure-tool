(function attachFigureStudioScientificSceneCatalog(root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  if (root) root.FigureStudioScientificSceneCatalog = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function createScientificSceneCatalogApi() {
  "use strict";

  const ACTION_USE_AS_NEW_FIGURE = "use_as_new_figure";
  const ACTION_INSERT_CURRENT_DOCUMENT = "insert_current_document";

  function textField(value, label, required = false) {
    if (value == null) {
      if (required) throw new Error(`${label} is required.`);
      return "";
    }
    if (typeof value !== "string") throw new TypeError(`${label} must be a string.`);
    const normalized = value.trim();
    if (required && !normalized) throw new Error(`${label} is required.`);
    return normalized;
  }

  function stringList(value, label) {
    if (value == null) return [];
    const values = Array.isArray(value) ? value : [value];
    const seen = new Set();
    const normalized = [];
    values.forEach((entry, index) => {
      if (typeof entry !== "string") throw new TypeError(`${label}[${index}] must be a string.`);
      const item = entry.trim();
      if (item && !seen.has(item)) {
        seen.add(item);
        normalized.push(item);
      }
    });
    return normalized;
  }

  function normalizeText(value) {
    return String(value ?? "")
      .trim()
      .toLowerCase()
      .normalize("NFKD")
      .replace(/[\u0300-\u036f]/g, "")
      .replace(/[\u2010-\u2015\u2212\uFE58\uFE63\uFF0D_-]+/g, " ")
      .replace(/&/g, " and ")
      .replace(/[^a-z0-9]+/g, " ")
      .replace(/\s+/g, " ")
      .trim();
  }

  function normalizeToken(value) {
    return normalizeText(value).replace(/\s+/g, "_");
  }

  function canonicalMode(value) {
    const token = normalizeToken(value);
    if (["slide", "slides", "deck", "presentation"].includes(token)) return "presentation";
    if (["figure", "figures", "figure_document"].includes(token)) return "figure";
    return token;
  }

  function canonicalAction(value, label) {
    const token = normalizeToken(value);
    if ([
      ACTION_USE_AS_NEW_FIGURE,
      "use_new_figure",
      "new_figure",
      "create_new_figure"
    ].includes(token)) return ACTION_USE_AS_NEW_FIGURE;
    if ([
      ACTION_INSERT_CURRENT_DOCUMENT,
      "insert",
      "insert_current",
      "insert_in_current_document",
      "insert_into_current_document"
    ].includes(token)) return ACTION_INSERT_CURRENT_DOCUMENT;
    throw new Error(`${label} contains unsupported action "${String(value).trim()}".`);
  }

  function canonicalList(value, label, canonicalize) {
    const seen = new Set();
    const normalized = [];
    stringList(value, label).forEach((item) => {
      const canonical = canonicalize(item, label);
      if (canonical && !seen.has(canonical)) {
        seen.add(canonical);
        normalized.push(canonical);
      }
    });
    return normalized;
  }

  function normalizeBaseUrl(value) {
    const base = String(value ?? "").trim().replace(/\\/g, "/");
    return base && !base.endsWith("/") ? `${base}/` : base;
  }

  function directoryUrl(value) {
    const url = String(value ?? "").trim().replace(/\\/g, "/");
    const boundary = url.lastIndexOf("/");
    return boundary >= 0 ? url.slice(0, boundary + 1) : "";
  }

  function resolveResourceUrl(baseUrl, resourcePath) {
    const resource = String(resourcePath ?? "").trim().replace(/\\/g, "/");
    if (!resource) return "";
    if (/^(?:[a-z][a-z0-9+.-]*:|\/\/)/i.test(resource)) return resource;
    const base = normalizeBaseUrl(baseUrl);
    if (!base) return resource.replace(/^\.\//, "");
    try {
      if (/^(?:[a-z][a-z0-9+.-]*:|\/\/)/i.test(base) && !/^[a-z]:\//i.test(base)) {
        return new URL(resource.replace(/^\/+/, ""), base).href;
      }
    } catch (_error) {
      // Desktop protocols can still be joined safely as resource paths below.
    }
    const leadingSlash = base.startsWith("/") ? "/" : "";
    const segments = `${base}${resource.replace(/^\/+/, "")}`.split("/");
    const resolved = [];
    for (const segment of segments) {
      if (!segment || segment === ".") continue;
      if (segment === ".." && resolved.length && resolved[resolved.length - 1] !== "..") resolved.pop();
      else if (segment !== ".." || !resolved.length) resolved.push(segment);
    }
    return `${leadingSlash}${resolved.join("/")}`;
  }

  function normalizeScene(scene, index, baseUrl) {
    if (!scene || typeof scene !== "object" || Array.isArray(scene)) {
      throw new TypeError(`Scientific scene ${index + 1} must be an object.`);
    }
    const label = `Scientific scene ${index + 1}`;
    const id = textField(scene.id, `${label} id`, true);
    const scenePath = textField(scene.scene, `${label} scene`);
    const previewPath = textField(scene.preview, `${label} preview`);
    return {
      ...scene,
      id,
      name: textField(scene.name, `${label} name`) || id,
      summary: textField(scene.summary, `${label} summary`),
      category: textField(scene.category, `${label} category`),
      synonyms: stringList(scene.synonyms, `${label} synonyms`),
      tags: stringList(scene.tags, `${label} tags`),
      modes: canonicalList(scene.modes, `${label} modes`, canonicalMode),
      actions: canonicalList(scene.actions, `${label} actions`, canonicalAction),
      scene: scenePath,
      preview: previewPath,
      source_record_id: textField(scene.source_record_id, `${label} source_record_id`),
      rights_record_id: textField(scene.rights_record_id, `${label} rights_record_id`),
      _sceneUrl: resolveResourceUrl(baseUrl, scenePath),
      _previewUrl: resolveResourceUrl(baseUrl, previewPath),
      _sceneOrder: index
    };
  }

  function normalizeSceneLibrary(library, options = {}) {
    if (!library || typeof library !== "object" || Array.isArray(library)) {
      throw new TypeError("Scientific scene library must be an object.");
    }
    if (!Array.isArray(library.scenes)) throw new TypeError("Scientific scene library scenes must be an array.");
    if (options == null || (typeof options !== "object" && typeof options !== "string")) {
      throw new TypeError("Scientific scene library options must be a base URL string or an object.");
    }
    const settings = typeof options === "string" ? { baseUrl: options } : options;
    const baseUrl = normalizeBaseUrl(
      settings.baseUrl
      ?? settings.baseURL
      ?? (settings.libraryUrl ? directoryUrl(settings.libraryUrl) : "")
    );
    const seen = new Set();
    const scenes = library.scenes.map((scene, index) => {
      const normalized = normalizeScene(scene, index, baseUrl);
      if (seen.has(normalized.id)) throw new Error(`Duplicate scientific scene id "${normalized.id}".`);
      seen.add(normalized.id);
      return normalized;
    });
    return {
      ...library,
      schema: textField(library.schema, "Scientific scene library schema"),
      id: textField(library.id, "Scientific scene library id"),
      name: textField(library.name, "Scientific scene library name"),
      scenes,
      byId: Object.fromEntries(scenes.map((scene) => [scene.id, scene])),
      categories: sceneCategories(scenes),
      baseUrl
    };
  }

  function scenesOf(libraryOrScenes) {
    if (Array.isArray(libraryOrScenes)) return libraryOrScenes;
    return Array.isArray(libraryOrScenes?.scenes) ? libraryOrScenes.scenes : [];
  }

  function filterValues(value, canonicalize = normalizeText) {
    if (value == null || value === "") return [];
    const values = Array.isArray(value) ? value : [value];
    return [...new Set(values.map(canonicalize).filter(Boolean))];
  }

  function sceneSearchTokens(scene) {
    return [
      scene?.name,
      scene?.summary,
      scene?.category,
      ...stringList(scene?.synonyms, "Scientific scene synonyms"),
      ...stringList(scene?.tags, "Scientific scene tags"),
      scene?.id
    ].flatMap((value) => normalizeText(value).split(" ")).filter(Boolean);
  }

  function searchScenes(libraryOrScenes, options = {}) {
    if (!options || typeof options !== "object" || Array.isArray(options)) {
      throw new TypeError("Scientific scene search options must be an object.");
    }
    const queryTokens = [...new Set(normalizeText(options.query).split(" ").filter(Boolean))];
    const categories = filterValues(options.category);
    const modes = filterValues(options.mode, canonicalMode);
    return scenesOf(libraryOrScenes).filter((scene) => {
      if (categories.length && !categories.includes(normalizeText(scene?.category))) return false;
      const sceneModes = filterValues(scene?.modes, canonicalMode);
      if (modes.length && !modes.some((mode) => sceneModes.includes(mode))) return false;
      if (!queryTokens.length) return true;
      const haystackTokens = sceneSearchTokens(scene);
      return queryTokens.every((queryToken) => haystackTokens.some((token) => token === queryToken || token.startsWith(queryToken)));
    });
  }

  function sceneCategories(libraryOrScenes) {
    const seen = new Set();
    const categories = [];
    scenesOf(libraryOrScenes).forEach((scene) => {
      const category = typeof scene?.category === "string" ? scene.category.trim() : "";
      const key = normalizeText(category);
      if (category && key && !seen.has(key)) {
        seen.add(key);
        categories.push(category);
      }
    });
    return categories;
  }

  function actionLabels(scene, documentKind) {
    if (!scene || typeof scene !== "object") return [];
    const modes = filterValues(scene.modes, canonicalMode);
    let actions;
    try {
      actions = canonicalList(scene.actions, "Scientific scene actions", canonicalAction);
    } catch (_error) {
      return [];
    }
    const labels = [];
    if (actions.includes(ACTION_USE_AS_NEW_FIGURE) && modes.includes("figure")) {
      labels.push("Use as new figure");
    }
    const kind = canonicalMode(documentKind);
    if (actions.includes(ACTION_INSERT_CURRENT_DOCUMENT) && modes.includes(kind)) {
      if (kind === "figure") labels.push("Insert in this figure");
      if (kind === "presentation") labels.push("Insert on this slide");
    }
    return labels;
  }

  return Object.freeze({
    ACTION_USE_AS_NEW_FIGURE,
    ACTION_INSERT_CURRENT_DOCUMENT,
    normalizeText,
    resolveResourceUrl,
    normalizeSceneLibrary,
    searchScenes,
    sceneCategories,
    actionLabels
  });
});
