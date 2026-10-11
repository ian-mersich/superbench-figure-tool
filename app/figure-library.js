(function (global) {
  "use strict";

  const VIEW_ORDER = ["assets", "scenes", "templates"];
  const SEARCH_IDS = { assets: "assetSearchInput", scenes: "sceneSearchInput", templates: "templateSearchInput" };
  const GALLERY_IDS = { assets: "assetGrid", scenes: "assetSceneGrid", templates: "templateGallery" };
  const scrollPositions = new Map();
  let panel = null;
  let activeView = "";
  let onViewChange = null;
  let pendingScrollFrame = 0;

  function viewPanel(view) {
    return panel?.querySelector(`[data-library-view="${view}"]`) || null;
  }

  function viewTab(view) {
    return panel?.querySelector(`[data-library-tab="${view}"]`) || null;
  }

  function searchInput(view) {
    return panel?.querySelector(`#${SEARCH_IDS[view]}`) || null;
  }

  function gallery(view) {
    return panel?.querySelector(`#${GALLERY_IDS[view]}`) || null;
  }

  function availableViews() {
    return VIEW_ORDER.filter((view) => {
      const tab = viewTab(view);
      return tab && !tab.hidden && global.getComputedStyle(tab).display !== "none";
    });
  }

  function currentScroll(view) {
    return {
      gallery: gallery(view)?.scrollTop || 0,
      section: viewPanel(view)?.scrollTop || 0,
      body: panel?.scrollTop || 0
    };
  }

  function restoreScroll(view) {
    if (pendingScrollFrame) global.cancelAnimationFrame(pendingScrollFrame);
    pendingScrollFrame = global.requestAnimationFrame(() => {
      pendingScrollFrame = 0;
      if (activeView !== view) return;
      const saved = scrollPositions.get(view) || { gallery: 0, section: 0, body: 0 };
      const list = gallery(view);
      const section = viewPanel(view);
      if (list) list.scrollTop = saved.gallery;
      if (section) section.scrollTop = saved.section;
      if (panel) panel.scrollTop = saved.body;
    });
  }

  function filterTemplates() {
    const query = String(searchInput("templates")?.value || "").trim().toLocaleLowerCase();
    const terms = query.split(/\s+/).filter(Boolean);
    const cards = Array.from(gallery("templates")?.querySelectorAll("[data-template-id]") || []);
    let matches = 0;
    cards.forEach((card) => {
      const content = String(card.textContent || "").toLocaleLowerCase();
      card.hidden = !terms.every((term) => content.includes(term));
      if (!card.hidden) matches += 1;
    });
    const status = panel?.querySelector("#templateLibraryStatus");
    if (status) status.textContent = query
      ? `${matches} of ${cards.length} templates`
      : `${cards.length} templates`;
    const empty = panel?.querySelector("#templateLibraryEmpty");
    if (empty) empty.hidden = matches > 0;
    return matches;
  }

  function select(view, options = {}) {
    if (!panel || !availableViews().includes(view) || !viewPanel(view)) return false;
    const previousView = activeView;
    const focused = global.document.activeElement;
    const focusBecomesHidden = previousView !== view && (
      viewPanel(previousView)?.contains(focused) || searchInput(previousView) === focused
    );
    if (previousView) scrollPositions.set(previousView, currentScroll(previousView));
    activeView = view;
    panel.dataset.libraryView = view;

    VIEW_ORDER.forEach((candidate) => {
      const selected = candidate === view;
      const tab = viewTab(candidate);
      const section = viewPanel(candidate);
      if (tab) {
        tab.setAttribute("aria-selected", String(selected));
        tab.tabIndex = selected ? 0 : -1;
        tab.classList.toggle("active", selected);
        tab.classList.toggle("is-active", selected);
      }
      if (section) {
        section.hidden = !selected;
        section.classList.toggle("is-active", selected);
      }
      const input = searchInput(candidate);
      if (input) input.hidden = !selected;
    });
    if (view === "templates") filterTemplates();

    // Application code expands and renders the selected native library section.
    // Navigation itself never reads or writes the figure, selection, or history.
    if (typeof onViewChange === "function") onViewChange(view);
    panel.dispatchEvent(new global.CustomEvent("figure-library-view-change", {
      bubbles: true,
      detail: { view, previousView }
    }));
    restoreScroll(view);
    if (options.focusSearch) searchInput(view)?.focus({ preventScroll: true });
    else if (options.focusTab || focusBecomesHidden) viewTab(view)?.focus({ preventScroll: true });
    return true;
  }

  function initialize(options = {}) {
    onViewChange = typeof options.onViewChange === "function" ? options.onViewChange : onViewChange;
    const candidate = global.document.querySelector('[data-sidebar-panel="tools"]');
    const tabs = candidate?.querySelector("#figureLibraryTabs");
    if (!candidate || !tabs || !VIEW_ORDER.every((view) => candidate.querySelector(`[data-library-view="${view}"]`))) return false;
    panel = candidate;
    if (tabs.dataset.libraryReady === "true") return true;
    tabs.dataset.libraryReady = "true";

    tabs.addEventListener("click", (event) => {
      const tab = event.target.closest("[data-library-tab]");
      if (tab && tabs.contains(tab)) select(tab.dataset.libraryTab);
    });
    tabs.addEventListener("keydown", (event) => {
      const tab = event.target.closest("[data-library-tab]");
      if (!tab || !tabs.contains(tab)) return;
      const views = availableViews();
      const index = views.indexOf(tab.dataset.libraryTab);
      if (index < 0) return;
      let nextIndex;
      if (event.key === "ArrowRight") nextIndex = (index + 1) % views.length;
      else if (event.key === "ArrowLeft") nextIndex = (index + views.length - 1) % views.length;
      else if (event.key === "Home") nextIndex = 0;
      else if (event.key === "End") nextIndex = views.length - 1;
      else return;
      event.preventDefault();
      event.stopPropagation();
      select(views[nextIndex], { focusTab: true });
    });
    searchInput("templates")?.addEventListener("input", () => {
      filterTemplates();
      const list = gallery("templates");
      if (list) list.scrollTop = 0;
    });
    filterTemplates();
    return select("assets");
  }

  function getState() {
    return {
      activeView,
      searches: Object.fromEntries(VIEW_ORDER.map((view) => [view, searchInput(view)?.value || ""])),
      scroll: Object.fromEntries(VIEW_ORDER.map((view) => [view,
        activeView === view ? currentScroll(view) : { ...(scrollPositions.get(view) || { gallery: 0, section: 0, body: 0 }) }
      ]))
    };
  }

  function syncVisibility() {
    if (panel && !availableViews().includes(activeView)) select("assets");
  }

  global.FigureStudioLibrary = { initialize, select, getState, syncVisibility };
})(globalThis);
