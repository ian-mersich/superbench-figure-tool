(function attachFigureStudioLearningCenter(root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  if (root) root.FigureStudioLearningCenter = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function createFigureStudioLearningCenterApi() {
  "use strict";

  const HELP_DEEP_LINK_PREFIX = "#help/";
  const TUTORIAL_DEEP_LINK_PREFIX = "#tutorial/";
  const DEFAULT_HELP_TOPIC = "getting-started";
  const DEFAULT_PROGRESS_KEY = "figure-studio.tutorial-progress.v2";

  function arrayOf(value) {
    return Array.isArray(value) ? value : [];
  }

  function text(value) {
    return String(value ?? "").trim();
  }

  function unique(values) {
    return [...new Set(arrayOf(values).map(text).filter(Boolean))];
  }

  function slug(value, fallback = "topic") {
    return text(value)
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "") || fallback;
  }

  function escapeHtml(value) {
    return String(value ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  function normalizedSearchTerms(query) {
    return unique(text(query).toLowerCase().replace(/[^a-z0-9+#./-]+/g, " ").split(/\s+/))
      .filter((term) => term.length > 1);
  }

  function blockSearchText(block = {}) {
    const values = [block.title, block.text, block.caption, block.label];
    for (const key of ["items", "rows", "headers", "columns"]) {
      for (const item of arrayOf(block[key])) {
        if (typeof item === "object") values.push(...Object.values(item || {}));
        else values.push(item);
      }
    }
    return values.map(text).filter(Boolean).join(" ");
  }

  function normalizeHelpArticle(entry = {}, index = 0, payload = {}) {
    const id = text(entry.id || entry.slug) || `help-${index + 1}`;
    const body = arrayOf(entry.body).map(text).filter(Boolean);
    const blocks = arrayOf(entry.blocks).length
      ? arrayOf(entry.blocks).map((block) => ({ ...block, type: text(block?.type || "paragraph") }))
      : body.map((line) => ({ type: "paragraph", text: line }));
    const contextRoutes = payload.context_routes || {};
    const coverageRoutes = payload.coverage || {};
    return Object.freeze({
      id,
      slug: id,
      title: text(entry.title) || "Figure Tool help",
      summary: text(entry.summary || body[0]),
      keywords: unique(entry.keywords),
      body,
      blocks,
      contexts: unique([
        ...arrayOf(entry.contexts),
        ...Object.entries(contextRoutes).filter(([, target]) => target === id).map(([context]) => context)
      ]),
      coverage: unique([
        ...arrayOf(entry.coverage),
        ...Object.entries(coverageRoutes).filter(([, target]) => target === id).map(([area]) => area)
      ]),
      related: unique(entry.related || payload.related?.[id]),
      tutorials: unique(entry.tutorials || payload.learn_routes?.[id]),
      updated: text(entry.updated || payload.updated)
    });
  }

  function normalizeTocNodes(nodes, validIds, prefix = "section") {
    return arrayOf(nodes).map((node, index) => {
      const id = text(node?.id) || `${prefix}-${index + 1}`;
      return Object.freeze({
        id,
        title: text(node?.title) || "Help",
        description: text(node?.description),
        articles: unique(node?.articles).filter((articleId) => validIds.has(articleId)),
        children: normalizeTocNodes(node?.children, validIds, id)
      });
    }).filter((node) => node.articles.length || node.children.length);
  }

  function collectTocArticleIds(nodes, output = []) {
    for (const node of arrayOf(nodes)) {
      output.push(...arrayOf(node.articles));
      collectTocArticleIds(node.children, output);
    }
    return output;
  }

  function articleSiblings(toc, articleId) {
    const ordered = collectTocArticleIds(toc);
    const index = ordered.indexOf(articleId);
    if (index < 0) return [];
    return unique([ordered[index - 1], ordered[index + 1]]);
  }

  function normalizeHelpCatalog(payload = {}) {
    const sourceArticles = arrayOf(payload.sections).length ? payload.sections : arrayOf(payload.articles);
    const preliminary = sourceArticles.map((entry, index) => normalizeHelpArticle(entry, index, payload));
    const byId = Object.fromEntries(preliminary.map((entry) => [entry.id, entry]));
    const validIds = new Set(Object.keys(byId));
    let toc = normalizeTocNodes(payload.toc, validIds);
    if (!toc.length) {
      toc = [{
        id: "all-topics",
        title: "All topics",
        description: "Figure Tool reference",
        articles: preliminary.map((entry) => entry.id),
        children: []
      }];
    }
    const listed = new Set(collectTocArticleIds(toc));
    const unlisted = preliminary.map((entry) => entry.id).filter((id) => !listed.has(id));
    if (unlisted.length) {
      toc = [...toc, {
        id: "more-topics",
        title: "More topics",
        description: "Additional Figure Tool reference",
        articles: unlisted,
        children: []
      }];
    }
    const articles = preliminary.map((entry) => Object.freeze({
      ...entry,
      related: unique([...entry.related.filter((id) => validIds.has(id)), ...articleSiblings(toc, entry.id)])
        .filter((id) => id !== entry.id)
        .slice(0, 5)
    }));
    const finalById = Object.freeze(Object.fromEntries(articles.map((entry) => [entry.id, entry])));
    const contextRoutes = Object.freeze(Object.fromEntries(
      Object.entries(payload.context_routes || {}).filter(([, target]) => finalById[target])
    ));
    return Object.freeze({
      schema: text(payload.schema || "figureStudio.helpContent.v2"),
      version: text(payload.version),
      title: text(payload.title || "Figure Tool Help"),
      articles: Object.freeze(articles),
      byId: finalById,
      toc: Object.freeze(toc),
      contextRoutes,
      coverage: Object.freeze({ ...(payload.coverage || {}) }),
      learnRoutes: Object.freeze({ ...(payload.learn_routes || {}) })
    });
  }

  function helpArticleSearchText(article = {}) {
    return [
      article.title,
      article.summary,
      ...arrayOf(article.keywords),
      ...arrayOf(article.contexts),
      ...arrayOf(article.coverage),
      ...arrayOf(article.blocks).map(blockSearchText)
    ].map(text).filter(Boolean).join(" ");
  }

  function scoreHelpArticle(article, query) {
    const terms = normalizedSearchTerms(query);
    if (!terms.length) return 1;
    const title = text(article.title).toLowerCase();
    const summary = text(article.summary).toLowerCase();
    const keywords = arrayOf(article.keywords).map((value) => text(value).toLowerCase());
    const contexts = arrayOf(article.contexts).map((value) => text(value).toLowerCase());
    const haystack = helpArticleSearchText(article).toLowerCase();
    const phrase = text(query).toLowerCase();
    let score = title === phrase ? 80 : title.includes(phrase) ? 32 : 0;
    if (keywords.some((keyword) => keyword === phrase)) score += 28;
    for (const term of terms) {
      if (!haystack.includes(term)) return 0;
      if (title.includes(term)) score += 14;
      if (keywords.some((keyword) => keyword.includes(term))) score += 9;
      if (contexts.some((context) => context.includes(term))) score += 7;
      if (summary.includes(term)) score += 4;
      score += 1;
    }
    return score;
  }

  function searchHelpCatalog(catalog, query, options = {}) {
    const normalized = catalog?.articles ? catalog : normalizeHelpCatalog(catalog);
    const allowedIds = options.articleIds ? new Set(arrayOf(options.articleIds).map(text)) : null;
    const limit = Number.isFinite(Number(options.limit)) ? Math.max(0, Number(options.limit)) : Infinity;
    return normalized.articles
      .filter((article) => !allowedIds || allowedIds.has(article.id))
      .map((article, order) => ({ article, order, score: scoreHelpArticle(article, query) }))
      .filter((result) => result.score > 0)
      .sort((a, b) => b.score - a.score || a.order - b.order)
      .slice(0, limit)
      .map((result) => result.article);
  }

  function getHelpDeepLink(articleId) {
    return `${HELP_DEEP_LINK_PREFIX}${encodeURIComponent(text(articleId) || DEFAULT_HELP_TOPIC)}`;
  }

  function parseHelpDeepLink(value) {
    const candidate = text(value);
    const hashIndex = candidate.indexOf("#");
    const hash = hashIndex >= 0 ? candidate.slice(hashIndex) : candidate;
    if (!hash.startsWith(HELP_DEEP_LINK_PREFIX)) return null;
    const id = decodeURIComponent(hash.slice(HELP_DEEP_LINK_PREFIX.length).split(/[?&]/)[0] || "");
    return id ? { id, slug: id } : null;
  }

  function getTutorialDeepLink(tutorialId, stepId = "") {
    const base = `${TUTORIAL_DEEP_LINK_PREFIX}${encodeURIComponent(text(tutorialId))}`;
    return text(stepId) ? `${base}/${encodeURIComponent(text(stepId))}` : base;
  }

  function parseTutorialDeepLink(value) {
    const candidate = text(value);
    const hashIndex = candidate.indexOf("#");
    const hash = hashIndex >= 0 ? candidate.slice(hashIndex) : candidate;
    if (!hash.startsWith(TUTORIAL_DEEP_LINK_PREFIX)) return null;
    const parts = hash.slice(TUTORIAL_DEEP_LINK_PREFIX.length).split("/").map((part) => decodeURIComponent(part));
    return parts[0] ? { tutorialId: parts[0], stepId: parts[1] || "" } : null;
  }

  function resolveHelpContext(catalog, context, fallbackId = DEFAULT_HELP_TOPIC) {
    const normalized = catalog?.articles ? catalog : normalizeHelpCatalog(catalog);
    const key = text(context);
    const exact = normalized.contextRoutes[key];
    if (exact && normalized.byId[exact]) return normalized.byId[exact];
    const owned = normalized.articles.find((article) => article.contexts.includes(key));
    return owned || normalized.byId[fallbackId] || normalized.articles[0] || null;
  }

  function normalizeTutorialStep(step = {}, index = 0) {
    const id = text(step.id) || `step-${index + 1}`;
    const action = step.action && typeof step.action === "object"
      ? { ...step.action }
      : { kind: "focus", label: text(step.continue_label || "Show in workspace"), focus: text(step.focus) };
    return Object.freeze({
      ...step,
      id,
      title: text(step.title) || `Step ${index + 1}`,
      instruction: text(step.instruction),
      why: text(step.why),
      callout: text(step.callout || step.contextual_callout),
      helpTopic: text(step.help_topic || step.helpTopic || action.help_topic),
      focus: text(step.focus || action.focus || action.target),
      action: Object.freeze({
        kind: text(action.kind || "focus"),
        label: text(action.label || step.continue_label || "Show in workspace"),
        command: text(action.command),
        target: text(action.target || action.selector),
        focus: text(action.focus || step.focus),
        help_topic: text(action.help_topic || step.help_topic)
      }),
      completion: Object.freeze({
        kind: text(step.completion?.kind || "acknowledge"),
        event: text(step.completion?.event),
        predicate: text(step.completion?.predicate),
        value: step.completion?.value
      })
    });
  }

  function normalizeTutorialCatalog(payload = {}) {
    const tutorials = arrayOf(payload.tutorials).map((tutorial, index) => {
      const id = text(tutorial.id) || `TUTORIAL-${index + 1}`;
      return Object.freeze({
        ...tutorial,
        id,
        slug: text(tutorial.slug) || slug(tutorial.title, id.toLowerCase()),
        title: text(tutorial.title) || "Figure Tool tutorial",
        summary: text(tutorial.summary),
        mode: text(tutorial.mode || "shared"),
        difficulty: text(tutorial.difficulty || "Beginner"),
        estimatedMinutes: Number(tutorial.estimated_minutes || tutorial.estimatedMinutes || 0),
        outcome: text(tutorial.outcome),
        helpTopics: unique(tutorial.help_topics || tutorial.helpTopics),
        prerequisites: unique(tutorial.prerequisites),
        start: Object.freeze({ ...(tutorial.start || {}) }),
        steps: Object.freeze(arrayOf(tutorial.steps).map(normalizeTutorialStep))
      });
    }).filter((tutorial) => tutorial.steps.length);
    return Object.freeze({
      schema: text(payload.schema || "figureStudio.tutorialCatalog.v2"),
      version: text(payload.version),
      progress: Object.freeze({ ...(payload.progress || {}) }),
      tutorials: Object.freeze(tutorials),
      byId: Object.freeze(Object.fromEntries(tutorials.map((tutorial) => [tutorial.id, tutorial])))
    });
  }

  function emptyTutorialProgress(catalog) {
    return {
      schema: "figureStudio.tutorialProgress.v2",
      activeTutorialId: catalog?.tutorials?.[0]?.id || "",
      tutorials: {}
    };
  }

  function normalizeTutorialProgress(catalog, value = {}) {
    const normalized = catalog?.tutorials ? catalog : normalizeTutorialCatalog(catalog);
    const output = emptyTutorialProgress(normalized);
    output.activeTutorialId = normalized.byId[text(value.activeTutorialId)]
      ? text(value.activeTutorialId)
      : output.activeTutorialId;
    for (const tutorial of normalized.tutorials) {
      const source = value.tutorials?.[tutorial.id] || {};
      const stepIds = new Set(tutorial.steps.map((step) => step.id));
      const completedStepIds = unique(source.completedStepIds).filter((id) => stepIds.has(id));
      const firstIncomplete = tutorial.steps.find((step) => !completedStepIds.includes(step.id));
      const requested = text(source.activeStepId);
      output.tutorials[tutorial.id] = {
        completedStepIds,
        activeStepId: stepIds.has(requested) && !completedStepIds.includes(requested)
          ? requested
          : (firstIncomplete?.id || tutorial.steps.at(-1)?.id || ""),
        updatedAt: text(source.updatedAt)
      };
    }
    return output;
  }

  function getTutorialProgress(catalog, progress, tutorialId, options = {}) {
    const normalized = catalog?.tutorials ? catalog : normalizeTutorialCatalog(catalog);
    const tutorial = normalized.byId[text(tutorialId)];
    if (!tutorial) return null;
    const state = normalizeTutorialProgress(normalized, progress).tutorials[tutorial.id];
    const completed = new Set(state.completedStepIds);
    const completedCount = tutorial.steps.filter((step) => completed.has(step.id)).length;
    const requestedStepId = text(options.activeStepId);
    const current = tutorial.steps.find((step) => step.id === requestedStepId)
      || tutorial.steps.find((step) => step.id === state.activeStepId)
      || tutorial.steps.find((step) => !completed.has(step.id))
      || tutorial.steps.at(-1)
      || null;
    return Object.freeze({
      tutorialId: tutorial.id,
      completedCount,
      completedStepIds: Object.freeze([...state.completedStepIds]),
      totalCount: tutorial.steps.length,
      percent: tutorial.steps.length ? Math.round((completedCount / tutorial.steps.length) * 100) : 100,
      currentStepId: current?.id || "",
      currentStepIndex: current ? tutorial.steps.indexOf(current) : -1,
      complete: completedCount === tutorial.steps.length
    });
  }

  function requestTutorialStartTransition({ tutorial, documentContext = {}, discardConfirmed = false } = {}) {
    const documentPolicy = text(tutorial?.start?.document_policy || "preserve-active");
    const dirty = documentContext.dirty === true;
    if (documentPolicy === "replace-active" && dirty && !discardConfirmed) {
      return Object.freeze({
        status: "confirmation-required",
        preserveActiveDocument: true,
        tutorialId: text(tutorial?.id),
        message: "Keep the current document unless you explicitly choose to discard its unsaved changes."
      });
    }
    return Object.freeze({
      status: "start",
      preserveActiveDocument: documentPolicy !== "replace-active" || !discardConfirmed,
      discardConfirmed: documentPolicy === "replace-active" && discardConfirmed,
      tutorialId: text(tutorial?.id),
      command: text(tutorial?.start?.command),
      documentPolicy
    });
  }

  function highlight(value, query) {
    const source = escapeHtml(value);
    const terms = normalizedSearchTerms(query).sort((a, b) => b.length - a.length);
    if (!terms.length) return source;
    const pattern = new RegExp(`(${terms.map((term) => term.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|")})`, "ig");
    return source.replace(pattern, "<mark>$1</mark>");
  }

  function renderHelpBlock(block = {}) {
    const type = text(block.type || "paragraph");
    if (type === "paragraph") return `<p>${escapeHtml(block.text)}</p>`;
    if (type === "note" || type === "warning") {
      return `<aside class="fs-help-${type}" role="note"><strong>${escapeHtml(block.title || (type === "warning" ? "Important" : "Note"))}</strong><p>${escapeHtml(block.text)}</p></aside>`;
    }
    if (type === "bullets") {
      return `<ul>${arrayOf(block.items).map((item) => `<li>${escapeHtml(typeof item === "object" ? item.text || item.label : item)}</li>`).join("")}</ul>`;
    }
    if (type === "steps") {
      return `<ol class="fs-help-steps">${arrayOf(block.items).map((item) => `<li><strong>${escapeHtml(item?.action || item?.title || "Step")}</strong><span>${escapeHtml(item?.detail || item?.text || "")}</span></li>`).join("")}</ol>`;
    }
    if (type === "table" || type === "shortcuts") {
      const headers = arrayOf(block.headers || block.columns);
      const rows = arrayOf(block.rows);
      return `<div class="fs-help-table-wrap"><table><thead><tr>${headers.map((header) => `<th>${escapeHtml(header)}</th>`).join("")}</tr></thead><tbody>${rows.map((row) => `<tr>${arrayOf(row).map((cell) => `<td>${escapeHtml(cell)}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`;
    }
    return `<p>${escapeHtml(block.text || blockSearchText(block))}</p>`;
  }

  function create(options = {}) {
    if (typeof document === "undefined") throw new Error("FigureStudioLearningCenter.create requires a browser document.");
    const fetcher = options.fetch || (typeof fetch === "function" ? fetch.bind(globalThis) : null);
    const resourceUrl = typeof options.resourceUrl === "function" ? options.resourceUrl : (value) => value;
    const helpUrl = options.helpUrl || "app/help/figure-studio-help.json";
    const tutorialUrl = options.tutorialUrl || "app/help/figure-studio-tutorials.json";
    let defaultStorage = null;
    try { defaultStorage = globalThis.localStorage; } catch { defaultStorage = null; }
    const storage = options.storage || defaultStorage;
    let helpCatalog = options.helpCatalog ? normalizeHelpCatalog(options.helpCatalog) : null;
    let tutorialCatalog = options.tutorialCatalog ? normalizeTutorialCatalog(options.tutorialCatalog) : null;
    let progress = null;
    let loadPromise = null;
    let rootElement = null;
    let returnFocus = null;
    let currentView = "help";
    let activeArticleId = DEFAULT_HELP_TOPIC;
    let activeTutorialId = "";
    let tutorialStepOverride = null;
    let query = "";
    let historyEntries = [];
    let historyIndex = -1;

    function progressKey() {
      return text(tutorialCatalog?.progress?.storage_key) || DEFAULT_PROGRESS_KEY;
    }

    function loadStoredProgress() {
      let stored = {};
      try { stored = JSON.parse(storage?.getItem(progressKey()) || "{}"); } catch { stored = {}; }
      progress = normalizeTutorialProgress(tutorialCatalog, stored);
      return progress;
    }

    function persistProgress() {
      try { storage?.setItem(progressKey(), JSON.stringify(progress)); } catch { /* Session progress remains usable. */ }
    }

    async function load() {
      if (helpCatalog && tutorialCatalog) {
        if (!progress) loadStoredProgress();
        return { helpCatalog, tutorialCatalog };
      }
      if (!fetcher) throw new Error("Figure Tool learning content cannot be loaded without fetch.");
      if (!loadPromise) {
        loadPromise = Promise.all([
          helpCatalog ? Promise.resolve(helpCatalog) : fetcher(resourceUrl(helpUrl), { cache: "no-store" }).then((response) => {
            if (!response.ok) throw new Error(`Help content unavailable (${response.status})`);
            return response.json().then(normalizeHelpCatalog);
          }),
          tutorialCatalog ? Promise.resolve(tutorialCatalog) : fetcher(resourceUrl(tutorialUrl), { cache: "no-store" }).then((response) => {
            if (!response.ok) throw new Error(`Tutorial content unavailable (${response.status})`);
            return response.json().then(normalizeTutorialCatalog);
          })
        ]).then(([help, tutorials]) => {
          helpCatalog = help;
          tutorialCatalog = tutorials;
          loadStoredProgress();
          return { helpCatalog, tutorialCatalog };
        });
      }
      return loadPromise;
    }

    function ensureRoot() {
      if (rootElement?.isConnected) return rootElement;
      rootElement = document.createElement("div");
      rootElement.id = options.rootId || "figureStudioLearningCenter";
      rootElement.className = "fs-learning-backdrop";
      rootElement.hidden = true;
      rootElement.innerHTML = `
        <section class="fs-learning-dialog" role="dialog" aria-modal="true" aria-labelledby="fsLearningTitle">
          <header class="fs-learning-header">
            <div class="fs-learning-title"><span class="fs-learning-title-badge" aria-hidden="true">?</span><div><strong id="fsLearningTitle">Figure Tool Help</strong><span>Figures and Presentations</span></div></div>
            <div class="fs-learning-history" role="group" aria-label="Help history">
              <button type="button" data-fs-history="back" aria-label="Back" title="Back" disabled>←</button>
              <button type="button" data-fs-history="forward" aria-label="Forward" title="Forward" disabled>→</button>
            </div>
            <label class="fs-learning-search-field"><span>Search Figure Tool Help</span><input id="fsHelpSearch" type="search" data-fs-help-search placeholder="Search tools, tasks, and formats" autocomplete="off"></label>
            <nav aria-label="Learning navigation">
              <button type="button" data-fs-view="help">Help</button>
              <button type="button" data-fs-view="tutorials">Tutorials</button>
            </nav>
            <button type="button" class="fs-learning-close" data-fs-close aria-label="Close Help" title="Close">×</button>
          </header>
          <div class="fs-learning-content" data-fs-learning-content></div>
        </section>`;
      rootElement.addEventListener("click", handleClick);
      rootElement.addEventListener("input", handleInput);
      document.body.appendChild(rootElement);
      return rootElement;
    }

    function setDeepLink(hash) {
      try {
        const next = `${globalThis.location?.pathname || ""}${globalThis.location?.search || ""}${hash}`;
        globalThis.history?.replaceState?.(globalThis.history.state, "", next);
      } catch { /* Deep links remain available through the controller state. */ }
    }

    function recordHistory(entry) {
      const signature = `${entry.view}:${entry.id}:${entry.stepId || ""}`;
      const current = historyEntries[historyIndex];
      if (`${current?.view}:${current?.id}:${current?.stepId || ""}` === signature) return;
      historyEntries = historyEntries.slice(0, historyIndex + 1);
      historyEntries.push({ ...entry });
      historyIndex = historyEntries.length - 1;
    }

    function updateHistoryButtons() {
      rootElement?.querySelector('[data-fs-history="back"]')?.toggleAttribute("disabled", historyIndex <= 0);
      rootElement?.querySelector('[data-fs-history="forward"]')?.toggleAttribute("disabled", historyIndex >= historyEntries.length - 1);
    }

    function renderTocNodes(nodes, depth = 0) {
      return arrayOf(nodes).map((node) => `
        <details class="fs-help-toc-group" ${depth < 2 ? "open" : ""}>
          <summary>${escapeHtml(node.title)}</summary>
          ${node.description ? `<p>${escapeHtml(node.description)}</p>` : ""}
          <div>
            ${arrayOf(node.articles).map((articleId) => {
              const article = helpCatalog.byId[articleId];
              return article ? `<button type="button" data-fs-help-topic="${escapeHtml(article.id)}" aria-current="${article.id === activeArticleId}">${escapeHtml(article.title)}</button>` : "";
            }).join("")}
            ${renderTocNodes(node.children, depth + 1)}
          </div>
        </details>`).join("");
    }

    function renderArticle(article) {
      if (!article) return `<article class="fs-help-article"><h2>Choose a help topic</h2></article>`;
      const related = article.related.map((id) => helpCatalog.byId[id]).filter(Boolean);
      const tutorialIds = unique([...article.tutorials, ...arrayOf(helpCatalog.learnRoutes[article.id])]);
      const tutorials = tutorialIds.map((id) => tutorialCatalog.byId[id]).filter(Boolean);
      return `<article class="fs-help-article" data-fs-active-help="${escapeHtml(article.id)}">
        <p class="fs-help-breadcrumb">Figure Tool Help / ${escapeHtml(article.title)}</p>
        <h2>${escapeHtml(article.title)}</h2>
        <p class="fs-help-summary">${escapeHtml(article.summary)}</p>
        <div class="fs-help-blocks">${article.blocks.map(renderHelpBlock).join("")}</div>
        ${tutorials.length ? `<section class="fs-contextual-learn"><h3>Learn by doing</h3>${tutorials.map((tutorial) => `<button type="button" data-fs-tutorial="${escapeHtml(tutorial.id)}"><strong>${escapeHtml(tutorial.title)}</strong><span>${escapeHtml(tutorial.summary)}</span></button>`).join("")}</section>` : ""}
        ${related.length ? `<nav class="fs-help-related" aria-label="Related topics"><h3>Related topics</h3>${related.map((entry) => `<button type="button" data-fs-help-topic="${escapeHtml(entry.id)}">${escapeHtml(entry.title)}</button>`).join("")}</nav>` : ""}
      </article>`;
    }

    function renderHelp() {
      const content = rootElement.querySelector("[data-fs-learning-content]");
      const results = query ? searchHelpCatalog(helpCatalog, query) : [];
      const article = helpCatalog.byId[activeArticleId] || helpCatalog.articles[0];
      const searchInput = rootElement.querySelector("[data-fs-help-search]");
      if (searchInput && searchInput.value !== query) searchInput.value = query;
      content.innerHTML = `<div class="fs-help-layout">
          <aside class="fs-help-toc" aria-label="Help contents">
            <p class="fs-help-result-count" aria-live="polite">${query ? `${results.length} result${results.length === 1 ? "" : "s"}` : `${helpCatalog.articles.length} articles`}</p>
            ${query ? `<div class="fs-help-search-results">${results.length ? results.map((entry) => `<button type="button" data-fs-help-topic="${escapeHtml(entry.id)}"><strong>${highlight(entry.title, query)}</strong><span>${highlight(entry.summary, query)}</span></button>`).join("") : `<p>No help topic matched “${escapeHtml(query)}”. Try a tool, file format, or task.</p>`}</div>` : renderTocNodes(helpCatalog.toc)}
          </aside>
          ${renderArticle(article)}
        </div>`;
      rootElement.querySelector('[data-fs-view="help"]')?.setAttribute("aria-current", "page");
      rootElement.querySelector('[data-fs-view="tutorials"]')?.removeAttribute("aria-current");
      updateHistoryButtons();
    }

    function tutorialModeLabel(mode) {
      if (mode === "presentation") return "Presentation";
      if (mode === "figure") return "Figure";
      return "Figure + Presentation";
    }

    function activeTutorialProgress(tutorialId) {
      const override = tutorialStepOverride?.tutorialId === tutorialId ? tutorialStepOverride.stepId : "";
      return getTutorialProgress(tutorialCatalog, progress, tutorialId, { activeStepId: override });
    }

    function renderTutorials() {
      const content = rootElement.querySelector("[data-fs-learning-content]");
      const tutorial = tutorialCatalog.byId[activeTutorialId] || tutorialCatalog.tutorials[0];
      activeTutorialId = tutorial?.id || "";
      progress.activeTutorialId = activeTutorialId;
      const status = tutorial ? activeTutorialProgress(tutorial.id) : null;
      const step = tutorial?.steps?.[status?.currentStepIndex] || null;
      content.innerHTML = `<div class="fs-tutorial-layout">
        <aside class="fs-tutorial-curriculum" aria-label="Tutorial curriculum">
          <header><strong>Guided curriculum</strong><span>Progress resumes separately for every course.</span></header>
          ${tutorialCatalog.tutorials.map((entry) => {
            const itemStatus = getTutorialProgress(tutorialCatalog, progress, entry.id);
            return `<button type="button" data-fs-tutorial="${escapeHtml(entry.id)}" aria-current="${entry.id === tutorial?.id}">
              <span>${escapeHtml(tutorialModeLabel(entry.mode))} · ${entry.estimatedMinutes} min</span>
              <strong>${escapeHtml(entry.title)}</strong>
              <small>${itemStatus.completedCount}/${itemStatus.totalCount} steps · ${itemStatus.percent}%</small>
            </button>`;
          }).join("")}
        </aside>
        <main class="fs-tutorial-guide" data-fs-active-tutorial="${escapeHtml(tutorial?.id || "")}">
          ${tutorial && step ? `<header>
            <p>${escapeHtml(tutorial.id)} · ${escapeHtml(tutorialModeLabel(tutorial.mode))} · ${escapeHtml(tutorial.difficulty)}</p>
            <h2>${escapeHtml(tutorial.title)}</h2>
            <span>${escapeHtml(tutorial.summary)}</span>
          </header>
          <div class="fs-tutorial-progress" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${status.percent}"><i style="width:${status.percent}%"></i></div>
          <section class="fs-tutorial-step">
            <p>Step ${status.currentStepIndex + 1} of ${status.totalCount}${status.complete ? " · Complete" : ""}</p>
            <h3>${escapeHtml(step.title)}</h3>
            <p>${escapeHtml(step.instruction)}</p>
            ${step.why ? `<aside><strong>Why this matters</strong><span>${escapeHtml(step.why)}</span></aside>` : ""}
            ${step.callout ? `<aside class="fs-tutorial-callout"><strong>Look for</strong><span>${escapeHtml(step.callout)}</span></aside>` : ""}
            <div class="fs-tutorial-step-actions">
              ${step.helpTopic && helpCatalog.byId[step.helpTopic] ? `<button type="button" data-fs-help-topic="${escapeHtml(step.helpTopic)}">Read related Help</button>` : ""}
              ${step.focus || step.action.command || step.action.target ? `<button type="button" data-fs-tutorial-focus>${escapeHtml(step.action.label || "Show in workspace")}</button>` : ""}
            </div>
          </section>
          <p class="fs-tutorial-outcome"><strong>Outcome:</strong> ${escapeHtml(tutorial.outcome)}</p>
          <footer>
            <button type="button" data-fs-tutorial-restart>Restart course</button>
            <span>Progress is saved on this device. Restarting never changes document content.</span>
            <button type="button" data-fs-tutorial-step="back" ${status.currentStepIndex <= 0 ? "disabled" : ""}>Back</button>
            <button type="button" data-fs-tutorial-step="next" ${status.complete ? "disabled" : ""}>${status.currentStepIndex + 1 >= status.totalCount ? "Finish" : "Continue"}</button>
          </footer>` : `<h2>Tutorials are unavailable</h2>`}
        </main>
      </div>`;
      rootElement.querySelector('[data-fs-view="tutorials"]')?.setAttribute("aria-current", "page");
      rootElement.querySelector('[data-fs-view="help"]')?.removeAttribute("aria-current");
      persistProgress();
      updateHistoryButtons();
    }

    function render() {
      if (!rootElement || !helpCatalog || !tutorialCatalog) return;
      if (currentView === "tutorials") renderTutorials();
      else renderHelp();
    }

    function navigateArticle(articleId, settings = {}) {
      const article = helpCatalog.byId[text(articleId)] || helpCatalog.byId[DEFAULT_HELP_TOPIC] || helpCatalog.articles[0];
      if (!article) return null;
      currentView = "help";
      activeArticleId = article.id;
      if (settings.record !== false) recordHistory({ view: "help", id: article.id });
      if (settings.deepLink !== false) setDeepLink(getHelpDeepLink(article.id));
      render();
      return article;
    }

    function navigateTutorial(tutorialId, settings = {}) {
      const tutorial = tutorialCatalog.byId[text(tutorialId)] || tutorialCatalog.tutorials[0];
      if (!tutorial) return null;
      currentView = "tutorials";
      activeTutorialId = tutorial.id;
      progress.activeTutorialId = tutorial.id;
      const tutorialProgress = progress.tutorials[tutorial.id];
      if (settings.stepId && tutorial.steps.some((step) => step.id === settings.stepId)) {
        tutorialProgress.activeStepId = settings.stepId;
        tutorialStepOverride = { tutorialId: tutorial.id, stepId: settings.stepId };
      } else {
        tutorialStepOverride = null;
      }
      const status = activeTutorialProgress(tutorial.id);
      if (settings.record !== false) recordHistory({ view: "tutorials", id: tutorial.id, stepId: status.currentStepId });
      if (settings.deepLink !== false) setDeepLink(getTutorialDeepLink(tutorial.id, status.currentStepId));
      render();
      return tutorial;
    }

    function moveHistory(direction) {
      const nextIndex = historyIndex + direction;
      if (nextIndex < 0 || nextIndex >= historyEntries.length) return null;
      historyIndex = nextIndex;
      const entry = historyEntries[historyIndex];
      return entry.view === "tutorials"
        ? navigateTutorial(entry.id, { stepId: entry.stepId, record: false })
        : navigateArticle(entry.id, { record: false });
    }

    function moveTutorialStep(direction) {
      const tutorial = tutorialCatalog.byId[activeTutorialId];
      if (!tutorial) return;
      const state = progress.tutorials[tutorial.id];
      const currentStatus = activeTutorialProgress(tutorial.id);
      const currentIndex = Math.max(0, currentStatus?.currentStepIndex ?? 0);
      if (direction > 0) {
        state.completedStepIds = unique([...state.completedStepIds, tutorial.steps[currentIndex].id]);
        state.activeStepId = tutorial.steps[currentIndex + 1]?.id || tutorial.steps[currentIndex].id;
        tutorialStepOverride = { tutorialId: tutorial.id, stepId: state.activeStepId };
      } else if (currentIndex > 0) {
        state.activeStepId = tutorial.steps[currentIndex - 1].id;
        tutorialStepOverride = { tutorialId: tutorial.id, stepId: state.activeStepId };
      }
      state.updatedAt = new Date().toISOString();
      persistProgress();
      const status = activeTutorialProgress(tutorial.id);
      setDeepLink(getTutorialDeepLink(tutorial.id, status.currentStepId));
      render();
    }

    function restartTutorial() {
      const tutorial = tutorialCatalog.byId[activeTutorialId];
      if (!tutorial) return;
      progress.tutorials[tutorial.id] = {
        completedStepIds: [],
        activeStepId: tutorial.steps[0]?.id || "",
        updatedAt: new Date().toISOString()
      };
      tutorialStepOverride = null;
      persistProgress();
      render();
    }

    function focusTutorialTarget() {
      const tutorial = tutorialCatalog.byId[activeTutorialId];
      const status = activeTutorialProgress(activeTutorialId);
      const step = tutorial?.steps?.[status?.currentStepIndex];
      if (!tutorial || !step) return false;
      const documentContext = typeof options.getDocumentContext === "function" ? options.getDocumentContext() || {} : {};
      const transition = requestTutorialStartTransition({ tutorial, documentContext });
      if (transition.status === "confirmation-required") {
        if (typeof options.onRequestTutorialTransition === "function") options.onRequestTutorialTransition({ transition, tutorial, step });
        return false;
      }
      close({ restoreFocus: false });
      if (typeof options.onFocusTarget === "function") {
        options.onFocusTarget({
          tutorialId: tutorial.id,
          stepId: step.id,
          focus: step.focus,
          action: step.action,
          preserveActiveDocument: true
        });
        return true;
      }
      return false;
    }

    function handleClick(event) {
      if (event.target === rootElement || event.target.closest("[data-fs-close]")) return close();
      const historyButton = event.target.closest("[data-fs-history]");
      if (historyButton) return moveHistory(historyButton.dataset.fsHistory === "back" ? -1 : 1);
      const viewButton = event.target.closest("[data-fs-view]");
      if (viewButton) {
        if (viewButton.dataset.fsView === "tutorials") return navigateTutorial(activeTutorialId || progress.activeTutorialId);
        return navigateArticle(activeArticleId);
      }
      const helpButton = event.target.closest("[data-fs-help-topic]");
      if (helpButton) return navigateArticle(helpButton.dataset.fsHelpTopic);
      const tutorialButton = event.target.closest("[data-fs-tutorial]");
      if (tutorialButton) return navigateTutorial(tutorialButton.dataset.fsTutorial);
      const stepButton = event.target.closest("[data-fs-tutorial-step]");
      if (stepButton) return moveTutorialStep(stepButton.dataset.fsTutorialStep === "back" ? -1 : 1);
      if (event.target.closest("[data-fs-tutorial-restart]")) return restartTutorial();
      if (event.target.closest("[data-fs-tutorial-focus]")) return focusTutorialTarget();
    }

    function handleInput(event) {
      if (!event.target.matches("[data-fs-help-search]")) return;
      query = event.target.value || "";
      currentView = "help";
      renderHelp();
      rootElement.querySelector("[data-fs-help-search]")?.focus({ preventScroll: true });
    }

    function handleKeydown(event) {
      if (!rootElement || rootElement.hidden) return;
      if (event.key === "Escape") return close();
      if (event.key !== "Tab") return;
      const focusable = [...rootElement.querySelectorAll('button:not([disabled]), input:not([disabled]), summary, [href], [tabindex]:not([tabindex="-1"])')]
        .filter((element) => !element.closest("[hidden]") && element.getClientRects().length > 0);
      if (!focusable.length) return;
      const first = focusable[0];
      const last = focusable.at(-1);
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    }

    async function open(topic = DEFAULT_HELP_TOPIC, settings = {}) {
      returnFocus = document.activeElement;
      ensureRoot().hidden = false;
      await load();
      const parsedTutorial = parseTutorialDeepLink(typeof topic === "string" ? topic : "");
      const parsedHelp = parseHelpDeepLink(typeof topic === "string" ? topic : "");
      if (parsedTutorial) navigateTutorial(parsedTutorial.tutorialId, { stepId: parsedTutorial.stepId });
      else navigateArticle(parsedHelp?.id || topic?.topic || topic?.id || topic || DEFAULT_HELP_TOPIC);
      if (settings.query !== undefined) {
        query = String(settings.query || "");
        renderHelp();
      }
      requestAnimationFrame(() => rootElement.querySelector("[data-fs-help-search], [data-fs-tutorial][aria-current='true'], [data-fs-close]")?.focus());
      return getState();
    }

    async function openContext(context) {
      await load();
      const article = resolveHelpContext(helpCatalog, context);
      return open(article?.id || DEFAULT_HELP_TOPIC);
    }

    async function openTutorial(tutorialId, settings = {}) {
      returnFocus = document.activeElement;
      ensureRoot().hidden = false;
      await load();
      navigateTutorial(tutorialId, { stepId: settings.stepId });
      requestAnimationFrame(() => rootElement.querySelector("[data-fs-tutorial][aria-current='true']")?.focus());
      return getState();
    }

    function openFromLocation() {
      const hash = globalThis.location?.hash || "";
      const helpLink = parseHelpDeepLink(hash);
      const tutorialLink = parseTutorialDeepLink(hash);
      if (tutorialLink) return openTutorial(tutorialLink.tutorialId, { stepId: tutorialLink.stepId });
      if (helpLink) return open(helpLink.id);
      return Promise.resolve(null);
    }

    function handleHashChange() {
      void openFromLocation();
    }

    function close(settings = {}) {
      if (!rootElement || rootElement.hidden) return false;
      rootElement.hidden = true;
      if (settings.restoreFocus !== false && returnFocus?.isConnected) returnFocus.focus({ preventScroll: true });
      returnFocus = null;
      return true;
    }

    function bindContextualLearn(container = document) {
      const listener = (event) => {
        const tutorialTarget = event.target.closest?.("[data-learn-tutorial]");
        if (tutorialTarget) return void openTutorial(tutorialTarget.dataset.learnTutorial);
        const helpTarget = event.target.closest?.("[data-help-context]");
        if (helpTarget) return void openContext(helpTarget.dataset.helpContext);
      };
      container.addEventListener("click", listener);
      return () => container.removeEventListener("click", listener);
    }

    function getState() {
      const tutorialStatus = tutorialCatalog && progress && activeTutorialId
        ? activeTutorialProgress(activeTutorialId)
        : null;
      return {
        schema: "figureStudio.learningCenterState.v2",
        open: Boolean(rootElement && !rootElement.hidden),
        view: currentView,
        activeArticleId,
        activeArticleTitle: helpCatalog?.byId?.[activeArticleId]?.title || "",
        activeTutorialId,
        query,
        articleCount: helpCatalog?.articles?.length || 0,
        knownLimitationsPresent: Boolean(helpCatalog?.byId?.["known-limitations"]),
        tutorialCount: tutorialCatalog?.tutorials?.length || 0,
        tutorialStepCount: tutorialCatalog?.tutorials?.reduce((count, tutorial) => count + tutorial.steps.length, 0) || 0,
        resultCount: helpCatalog ? searchHelpCatalog(helpCatalog, query).length : 0,
        canGoBack: historyIndex > 0,
        canGoForward: historyIndex >= 0 && historyIndex < historyEntries.length - 1,
        tutorialStatus
      };
    }

    function destroy() {
      close({ restoreFocus: false });
      rootElement?.remove();
      rootElement = null;
      document.removeEventListener("keydown", handleKeydown);
      globalThis.removeEventListener?.("hashchange", handleHashChange);
    }

    document.addEventListener("keydown", handleKeydown);
    if (options.listenForDeepLinks !== false) globalThis.addEventListener?.("hashchange", handleHashChange);
    if (options.openDeepLinkOnCreate !== false && (parseHelpDeepLink(globalThis.location?.hash || "") || parseTutorialDeepLink(globalThis.location?.hash || ""))) {
      queueMicrotask(() => void openFromLocation());
    }
    return Object.freeze({
      load,
      open,
      openContext,
      openTutorial,
      openFromLocation,
      close,
      back: () => moveHistory(-1),
      forward: () => moveHistory(1),
      continueTutorial: () => { moveTutorialStep(1); return getState(); },
      previousTutorial: () => { moveTutorialStep(-1); return getState(); },
      restartTutorial: () => { restartTutorial(); return getState(); },
      search(value) { query = String(value || ""); render(); return helpCatalog ? searchHelpCatalog(helpCatalog, query) : []; },
      bindContextualLearn,
      getState,
      destroy
    });
  }

  return Object.freeze({
    HELP_DEEP_LINK_PREFIX,
    TUTORIAL_DEEP_LINK_PREFIX,
    normalizeHelpCatalog,
    searchHelpCatalog,
    helpArticleSearchText,
    getHelpDeepLink,
    parseHelpDeepLink,
    getTutorialDeepLink,
    parseTutorialDeepLink,
    resolveHelpContext,
    normalizeTutorialCatalog,
    normalizeTutorialProgress,
    getTutorialProgress,
    requestTutorialStartTransition,
    renderHelpBlock,
    create
  });
});
