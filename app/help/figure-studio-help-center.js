(function attachFigureToolHelp(root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  if (root) { root.FigureToolHelp = api; root.FigureStudioLearningCenter = api; }
})(typeof globalThis !== "undefined" ? globalThis : this, function createFigureToolHelpApi() {
  "use strict";

  const HELP_DEEP_LINK_PREFIX = "#help/";
  const TUTORIAL_DEEP_LINK_PREFIX = "#tutorial/";
  const DEFAULT_HELP_TOPIC = "getting-started";


  function arrayOf(value) {
    return Array.isArray(value) ? value : [];
  }

  function text(value) {
    return String(value ?? "").trim();
  }

  function unique(values) {
    return [...new Set(arrayOf(values).map(text).filter(Boolean))];
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

  function parseDeepLink(value, prefix) {
    const candidate = text(value);
    const hash = candidate.includes("#") ? candidate.slice(candidate.indexOf("#")) : candidate;
    if (!hash.startsWith(prefix)) return null;
    try { return decodeURIComponent(hash.slice(prefix.length).split(/[?&]/)[0] || ""); }
    catch { return null; }
  }

  function parseHelpDeepLink(value) {
    const id = parseDeepLink(value, HELP_DEEP_LINK_PREFIX);
    return id ? { id, slug: id } : null;
  }

  // Old bookmarks and host commands remain read-only Help aliases.
  const RETIRED_TOPIC_ALIASES = Object.freeze({
    "FIG-00": "getting-started", "first-figure": "getting-started",
    "FIG-01": "artboards-decks", "first-four-panel-figure": "artboards-decks",
    "FIG-02": "biological-assets", "asset-based-scientific-diagram": "biological-assets",
    "FIG-03": "paths-vectors", "vector-editing": "paths-vectors",
    "FIG-04": "importing", "imported-svg-pdf": "importing",
    "FIG-05": "figure-export-options", "publication-export": "figure-export-options",
    "PRES-01": "presentation-documents", "first-scientific-presentation": "presentation-documents",
    "PRES-02": "presentation-slides", "slide-layouts-themes": "presentation-slides",
    "PRES-03": "pptx-compatibility", "pptx-interchange": "pptx-compatibility",
    "SAFE-01": "saving-recovery", "save-reopen-recovery": "saving-recovery"
  });

  function parseTutorialDeepLink(value) {
    const parsed = parseDeepLink(value, TUTORIAL_DEEP_LINK_PREFIX);
    if (!parsed) return null;
    const [tutorialId, stepId = ""] = parsed.split("/");
    return { tutorialId, stepId };
  }

  function retiredTopicAlias(value) {
    return RETIRED_TOPIC_ALIASES[text(value)] || DEFAULT_HELP_TOPIC;
  }

  function resolveHelpContext(catalog, context, fallbackId = DEFAULT_HELP_TOPIC) {
    const normalized = catalog?.articles ? catalog : normalizeHelpCatalog(catalog);
    const key = text(context);
    const exact = normalized.contextRoutes[key];
    return normalized.byId[exact] || normalized.articles.find((article) => article.contexts.includes(key))
      || normalized.byId[fallbackId] || normalized.articles[0] || null;
  }

  function highlight(value, query) {
    const terms = normalizedSearchTerms(query).sort((a, b) => b.length - a.length);
    if (!terms.length) return escapeHtml(value);
    const pattern = new RegExp(`(${terms.map((term) => term.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|")})`, "ig");
    return String(value || "").split(pattern).map((part, index) => index % 2
      ? `<mark>${escapeHtml(part)}</mark>` : escapeHtml(part)).join("");
  }

  function helpMediaPath(value) {
    const path = text(value);
    // Only packaged media is accepted. No remote tracking, SVG markup or traversal.
    return /^media\/[a-z0-9][a-z0-9_/-]*\.(png|jpg|jpeg|webp|gif|webm|mp4)$/i.test(path)
      && !path.includes("..") ? path : "";
  }

  function renderHelpBlock(block = {}, options = {}) {
    const type = text(block.type || "paragraph");
    if (type === "image" || type === "video") {
      const path = helpMediaPath(block.src);
      if (!path) return "";
      const resolve = typeof options.mediaUrl === "function" ? options.mediaUrl : (value) => value;
      const src = escapeHtml(resolve(path));
      const caption = escapeHtml(block.caption);
      const alt = escapeHtml(block.alt || block.caption || "Figure Tool demonstration");
      const posterPath = helpMediaPath(block.poster);
      const media = type === "image"
        ? `<img src="${src}" alt="${alt}" loading="lazy" decoding="async">`
        : `<video src="${src}" ${posterPath ? `poster="${escapeHtml(resolve(posterPath))}"` : ""} controls playsinline preload="none" aria-label="${alt}"><p>Your browser cannot play this clip. Follow the written steps above.</p></video>`;
      return `<figure class="fs-help-media">${media}<figcaption>${caption}${type === "video" ? '<span class="fs-help-media-hint">Play this silent demonstration when ready.</span>' : ""}</figcaption></figure>`;
    }
    if (type === "paragraph") return `<p>${escapeHtml(block.text)}</p>`;
    if (type === "note" || type === "warning") return `<aside class="fs-help-${type}" role="note"><strong>${escapeHtml(block.title || (type === "warning" ? "Important" : "Note"))}</strong><p>${escapeHtml(block.text)}</p></aside>`;
    if (type === "bullets") return `<ul>${arrayOf(block.items).map((item) => `<li>${escapeHtml(typeof item === "object" ? item.text || item.label : item)}</li>`).join("")}</ul>`;
    if (type === "steps") return `<ol class="fs-help-steps">${arrayOf(block.items).map((item) => `<li><strong>${escapeHtml(item?.action || item?.title || "Step")}</strong><span>${escapeHtml(item?.detail || item?.text || (typeof item === "string" ? item : ""))}</span></li>`).join("")}</ol>`;
    if (type === "table" || type === "shortcuts") {
      const headers = arrayOf(block.headers || block.columns);
      return `<div class="fs-help-table-wrap"><table><thead><tr>${headers.map((header) => `<th scope="col">${escapeHtml(header)}</th>`).join("")}</tr></thead><tbody>${arrayOf(block.rows).map((row) => `<tr>${arrayOf(row).map((cell) => `<td>${escapeHtml(cell)}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`;
    }
    return `<p>${escapeHtml(block.text || blockSearchText(block))}</p>`;
  }

  function create(options = {}) {
    if (typeof document === "undefined") throw new Error("FigureToolHelp.create requires a browser document.");
    const fetcher = options.fetch || (typeof fetch === "function" ? fetch.bind(globalThis) : null);
    const resourceUrl = typeof options.resourceUrl === "function" ? options.resourceUrl : (value) => value;
    const helpUrl = options.helpUrl || "app/help/figure-studio-help.json";
    const mediaUrl = typeof options.mediaUrl === "function" ? options.mediaUrl : (path) => {
      const catalogUrl = new URL(resourceUrl(helpUrl), document.baseURI);
      return new URL(path, catalogUrl).href;
    };
    const pageMode = options.pageMode === true;
    let helpCatalog = options.helpCatalog ? normalizeHelpCatalog(options.helpCatalog) : null;
    let loadPromise = null;
    let rootElement = null;
    let returnFocus = null;
    let activeArticleId = DEFAULT_HELP_TOPIC;
    let query = "";
    let historyEntries = [];
    let historyIndex = -1;

    async function load() {
      if (helpCatalog) return { helpCatalog };
      if (!fetcher) throw new Error("Help content cannot be loaded.");
      if (!loadPromise) loadPromise = fetcher(resourceUrl(helpUrl), { cache: "no-store" }).then((response) => {
        if (!response.ok) throw new Error(`Help content unavailable (${response.status})`);
        return response.json();
      }).then((payload) => {
        const catalog = normalizeHelpCatalog(payload);
        if (!catalog.articles.length) throw new Error("Help content is empty.");
        helpCatalog = catalog;
        return { helpCatalog };
      }).catch((error) => { loadPromise = null; throw error; });
      return loadPromise;
    }

    function ensureRoot() {
      if (rootElement?.isConnected) return rootElement;
      rootElement = document.createElement("div");
      rootElement.id = options.rootId || "figureStudioLearningCenter";
      rootElement.className = `fs-learning-backdrop${pageMode ? " fs-help-page" : ""}`;
      rootElement.hidden = true;
      const titleId = `${rootElement.id}-title`;
      rootElement.innerHTML = `<section class="fs-learning-dialog" ${pageMode ? 'role="main"' : 'role="dialog" aria-modal="true"'} aria-labelledby="${escapeHtml(titleId)}">
        <header class="fs-learning-header">
          <div class="fs-learning-title"><span class="fs-learning-title-badge" aria-hidden="true">?</span><div><strong id="${escapeHtml(titleId)}">Figure Tool Help</strong><span>Figures and presentations</span></div></div>
          <div class="fs-learning-history" role="group" aria-label="Help history"><button type="button" data-fs-history="back" aria-label="Back" title="Back" disabled>←</button><button type="button" data-fs-history="forward" aria-label="Forward" title="Forward" disabled>→</button></div>
          <label class="fs-learning-search-field"><span>Search Figure Tool Help</span><input type="search" data-fs-help-search placeholder="Search tools, tasks, and formats" autocomplete="off"></label>
          ${pageMode ? '<a class="fs-help-page-link" href="../../web/">Open editor</a>' : '<button type="button" class="fs-learning-close" data-fs-close aria-label="Close Help" title="Close">×</button>'}
        </header><div class="fs-learning-content" data-fs-learning-content></div></section>`;
      if (pageMode && options.returnUrl) rootElement.querySelector(".fs-help-page-link").href = options.returnUrl;
      rootElement.addEventListener("click", handleClick);
      rootElement.addEventListener("input", handleInput);
      (options.mountElement || document.body).appendChild(rootElement);
      return rootElement;
    }

    function setDeepLink(id) {
      try { globalThis.history?.replaceState?.(globalThis.history.state, "", `${globalThis.location?.pathname || ""}${globalThis.location?.search || ""}${getHelpDeepLink(id)}`); }
      catch { /* Help remains usable in hosts that disallow URL updates. */ }
    }

    function pauseMedia() { rootElement?.querySelectorAll("video").forEach((video) => video.pause()); }

    function renderTocNodes(nodes, depth = 0) {
      return arrayOf(nodes).map((node) => `<details class="fs-help-toc-group" ${depth < 2 ? "open" : ""}><summary>${escapeHtml(node.title)}</summary>
        ${node.description ? `<p>${escapeHtml(node.description)}</p>` : ""}<div>${arrayOf(node.articles).map((id) => {
          const article = helpCatalog.byId[id];
          return article ? `<button type="button" data-fs-help-topic="${escapeHtml(id)}" ${id === activeArticleId ? 'aria-current="page"' : ""}>${escapeHtml(article.title)}</button>` : "";
        }).join("")}${renderTocNodes(node.children, depth + 1)}</div></details>`).join("");
    }

    function renderArticle(article) {
      if (!article) return '<article class="fs-help-article"><h2>Choose a Help topic</h2></article>';
      const related = article.related.map((id) => helpCatalog.byId[id]).filter(Boolean);
      const pageUrl = new URL("index.html", new URL(resourceUrl(helpUrl), document.baseURI));
      pageUrl.hash = getHelpDeepLink(article.id);
      try {
        const parentUrl = new URL(globalThis.parent.location.href);
        if (parentUrl.origin === pageUrl.origin && /\/web\/(?:index\.html)?$/.test(parentUrl.pathname)) {
          parentUrl.hash = "";
          pageUrl.searchParams.set("editor", parentUrl.href);
        }
      } catch { /* A hosted editor may have a different parent origin. */ }
      return `<article class="fs-help-article" data-fs-active-help="${escapeHtml(article.id)}"><p class="fs-help-breadcrumb">Figure Tool Help</p><h2 tabindex="-1">${escapeHtml(article.title)}</h2><p class="fs-help-summary">${escapeHtml(article.summary)}</p>
        <div class="fs-help-blocks">${article.blocks.map((block) => renderHelpBlock(block, { mediaUrl })).join("")}</div>
        ${related.length ? `<nav class="fs-help-related" aria-label="Related topics"><h3>Related topics</h3>${related.map((entry) => `<button type="button" data-fs-help-topic="${escapeHtml(entry.id)}">${escapeHtml(entry.title)}</button>`).join("")}</nav>` : ""}
        <footer class="fs-help-article-footer">${article.updated ? `<span>Reviewed ${escapeHtml(article.updated)}</span>` : ""}${pageMode ? "" : `<a href="${escapeHtml(pageUrl.href)}" target="_blank" rel="noopener">Open this article in a separate page</a>`}</footer></article>`;
    }

    function render() {
      if (!rootElement || !helpCatalog) return;
      pauseMedia();
      const content = rootElement.querySelector("[data-fs-learning-content]");
      const results = query ? searchHelpCatalog(helpCatalog, query) : [];
      rootElement.querySelector("[data-fs-help-search]").value = query;
      content.innerHTML = `<div class="fs-help-layout"><aside class="fs-help-toc" aria-label="Help contents"><p class="fs-help-result-count" aria-live="polite">${query ? `${results.length} result${results.length === 1 ? "" : "s"}` : `${helpCatalog.articles.length} articles`}</p>
        ${query ? `<div class="fs-help-search-results">${results.length ? results.map((entry) => `<button type="button" data-fs-help-topic="${escapeHtml(entry.id)}"><strong>${highlight(entry.title, query)}</strong><span>${highlight(entry.summary, query)}</span></button>`).join("") : `<p>No Help topic matched “${escapeHtml(query)}”. Try a tool, file format, or task.</p>`}</div>` : renderTocNodes(helpCatalog.toc)}</aside>${renderArticle(helpCatalog.byId[activeArticleId] || helpCatalog.articles[0])}</div>`;
      rootElement.querySelector('[data-fs-history="back"]').disabled = historyIndex <= 0;
      rootElement.querySelector('[data-fs-history="forward"]').disabled = historyIndex >= historyEntries.length - 1;
    }

    function navigateArticle(id, settings = {}) {
      const article = helpCatalog.byId[text(id)] || helpCatalog.byId[DEFAULT_HELP_TOPIC] || helpCatalog.articles[0];
      if (!article) return null;
      activeArticleId = article.id;
      if (settings.record !== false && historyEntries[historyIndex] !== article.id) {
        historyEntries = historyEntries.slice(0, historyIndex + 1);
        historyEntries.push(article.id);
        historyIndex = historyEntries.length - 1;
      }
      setDeepLink(article.id);
      render();
      if (settings.focus) rootElement.querySelector(".fs-help-article h2")?.focus({ preventScroll: true });
      return article;
    }

    function moveHistory(direction) {
      const next = historyIndex + direction;
      if (next < 0 || next >= historyEntries.length) return null;
      historyIndex = next;
      return navigateArticle(historyEntries[next], { record: false, focus: true });
    }

    function showLoadError() {
      rootElement.querySelector("[data-fs-learning-content]").innerHTML = '<article class="fs-help-error"><h2>Help could not be loaded</h2><p>Check your connection or reopen the app, then try again.</p><button type="button" data-fs-help-retry>Try again</button></article>';
    }

    function handleClick(event) {
      if (!pageMode && (event.target === rootElement || event.target.closest("[data-fs-close]"))) return close();
      const historyButton = event.target.closest("[data-fs-history]");
      if (historyButton) return moveHistory(historyButton.dataset.fsHistory === "back" ? -1 : 1);
      const topic = event.target.closest("[data-fs-help-topic]");
      if (topic) return navigateArticle(topic.dataset.fsHelpTopic, { focus: true });
      if (event.target.closest("[data-fs-help-retry]")) void open(activeArticleId);
    }

    function handleInput(event) {
      if (!event.target.matches("[data-fs-help-search]")) return;
      query = event.target.value || "";
      render();
    }

    function handleKeydown(event) {
      if (!rootElement || rootElement.hidden || pageMode) return;
      if (event.key === "Escape") { event.preventDefault(); event.stopImmediatePropagation(); return close(); }
      if (event.key !== "Tab") return;
      const focusable = [...rootElement.querySelectorAll('button:not([disabled]), input:not([disabled]), summary, [href], video[controls], [tabindex]:not([tabindex="-1"])')]
        .filter((element) => !element.closest("[hidden]") && element.getClientRects().length);
      const first = focusable[0], last = focusable.at(-1);
      if (event.shiftKey && (document.activeElement === first || !rootElement.contains(document.activeElement))) { event.preventDefault(); last?.focus(); }
      else if (!event.shiftKey && (document.activeElement === last || !rootElement.contains(document.activeElement))) { event.preventDefault(); first?.focus(); }
    }

    async function open(topic = DEFAULT_HELP_TOPIC, settings = {}) {
      if (!rootElement || rootElement.hidden) {
        const active = document.activeElement;
        returnFocus = active?.closest?.(".app-menu")?.querySelector(".menu-trigger")
          || (active !== document.body && active?.getClientRects?.().length ? active : null)
          || document.querySelector('.app-menu[data-menu="help"] .menu-trigger');
      }
      ensureRoot().hidden = false;
      const retired = parseTutorialDeepLink(typeof topic === "string" ? topic : "");
      const parsed = parseHelpDeepLink(typeof topic === "string" ? topic : "");
      const target = retired ? retiredTopicAlias(retired.tutorialId) : parsed?.id || topic?.topic || topic?.id || topic || DEFAULT_HELP_TOPIC;
      if (settings.query !== undefined) query = String(settings.query || "");
      try { await load(); navigateArticle(target); }
      catch { showLoadError(); }
      requestAnimationFrame(() => rootElement?.querySelector("[data-fs-help-search]")?.focus({ preventScroll: true }));
      return getState();
    }

    async function openContext(context) {
      try { await load(); return open(resolveHelpContext(helpCatalog, context)?.id || DEFAULT_HELP_TOPIC); }
      catch { return open(DEFAULT_HELP_TOPIC); }
    }

    function openTutorial(id) { return open(retiredTopicAlias(id)); }
    function openFromLocation() {
      const hash = globalThis.location?.hash || "";
      const help = parseHelpDeepLink(hash), retired = parseTutorialDeepLink(hash);
      return help ? open(help.id) : retired ? openTutorial(retired.tutorialId) : Promise.resolve(null);
    }
    function handleHashChange() { void openFromLocation(); }
    function close(settings = {}) {
      if (!rootElement || rootElement.hidden || pageMode) return false;
      pauseMedia();
      rootElement.hidden = true;
      if (settings.restoreFocus !== false) {
        const target = returnFocus?.isConnected && returnFocus.getClientRects().length
          ? returnFocus : document.querySelector('.app-menu[data-menu="help"] .menu-trigger');
        target?.focus({ preventScroll: true });
      }
      returnFocus = null;
      return true;
    }
    function bindContextualLearn(container = document) {
      const listener = (event) => {
        const target = event.target.closest?.("[data-help-context], [data-learn-tutorial]");
        if (target?.dataset.helpContext) void openContext(target.dataset.helpContext);
        else if (target?.dataset.learnTutorial) void openTutorial(target.dataset.learnTutorial);
      };
      container.addEventListener("click", listener);
      return () => container.removeEventListener("click", listener);
    }
    function getState() {
      return { schema: "figureStudio.learningCenterState.v2", open: Boolean(rootElement && !rootElement.hidden), view: "help", activeArticleId,
        activeArticleTitle: helpCatalog?.byId[activeArticleId]?.title || "", query, articleCount: helpCatalog?.articles.length || 0,
        knownLimitationsPresent: Boolean(helpCatalog?.byId["known-limitations"]), resultCount: helpCatalog ? searchHelpCatalog(helpCatalog, query).length : 0,
        canGoBack: historyIndex > 0, canGoForward: historyIndex >= 0 && historyIndex < historyEntries.length - 1,
        tutorialCount: 0, tutorialStepCount: 0, activeTutorialId: "", tutorialStatus: null };
    }
    function destroy() {
      pauseMedia(); close({ restoreFocus: false }); rootElement?.remove(); rootElement = null;
      document.removeEventListener("keydown", handleKeydown, true);
      globalThis.removeEventListener?.("hashchange", handleHashChange);
    }
    document.addEventListener("keydown", handleKeydown, true);
    if (options.listenForDeepLinks !== false) globalThis.addEventListener?.("hashchange", handleHashChange);
    if (options.openDeepLinkOnCreate !== false && (parseHelpDeepLink(globalThis.location?.hash || "") || parseTutorialDeepLink(globalThis.location?.hash || ""))) queueMicrotask(() => void openFromLocation());
    return Object.freeze({ load, open, openContext, openTutorial, openFromLocation, close, back: () => moveHistory(-1), forward: () => moveHistory(1),
      search(value) { query = String(value || ""); render(); return helpCatalog ? searchHelpCatalog(helpCatalog, query) : []; },
      bindContextualLearn, getState, destroy });
  }

  return Object.freeze({ HELP_DEEP_LINK_PREFIX, TUTORIAL_DEEP_LINK_PREFIX, normalizeHelpCatalog, searchHelpCatalog, helpArticleSearchText,
    getHelpDeepLink, parseHelpDeepLink, parseTutorialDeepLink, retiredTopicAlias, resolveHelpContext, helpMediaPath, renderHelpBlock, create });
});
