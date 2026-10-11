(function (global) {
  "use strict";

  const OWNER = "figureStudio";
  const ID_PREFIX = `${OWNER}:`;

  function projectItemId(tabId) {
    return `${ID_PREFIX}${String(tabId || "")}`;
  }

  function tabIdFromProjectItemId(itemId) {
    const value = String(itemId || "");
    return value.startsWith(ID_PREFIX) ? value.slice(ID_PREFIX.length) : "";
  }

  function kindForTab(tab = {}) {
    if (String(tab.sourceFormat || "").toLowerCase() === "pdf") return "pdf";
    return String(tab.kind || "").toLowerCase() === "presentation" ? "presentation" : "figure";
  }

  function storedPresentationThumbnail(tab = {}) {
    const payload = tab.payload || {};
    const project = payload.project || payload;
    const pages = project?.deck?.pages;
    if (!Array.isArray(pages)) return "";
    const page = pages.find((candidate) => candidate?.id === project?.deck?.activePageId) || pages[0];
    const thumbnail = String(page?.thumbnail || "");
    return thumbnail.startsWith("data:image/") ? thumbnail : "";
  }

  function listItems(tabs = [], options = {}) {
    const activeTabId = String(options.activeTabId || "");
    const activePreview = String(options.activePreview || "");
    return (Array.isArray(tabs) ? tabs : []).filter((tab) => tab?.id).map((tab) => {
      const kind = kindForTab(tab);
      const previewSource = tab.id === activeTabId
        ? activePreview
        : kind === "presentation" ? storedPresentationThumbnail(tab) : "";
      const subtitleParts = [kind === "presentation" ? "Presentation" : kind === "pdf" ? "PDF" : "Figure"];
      if (tab.dirty) subtitleParts.push("Unsaved changes");
      return {
        id: projectItemId(tab.id),
        owner: OWNER,
        kind,
        title: String(tab.title || tab.filename || "Untitled document"),
        subtitle: subtitleParts.join(" · "),
        preview: previewSource ? { type: "image", src: previewSource } : null
      };
    });
  }

  async function openItem(itemId, tabs = [], activate) {
    const tabId = tabIdFromProjectItemId(itemId);
    if (!tabId || !Array.isArray(tabs) || !tabs.some((tab) => String(tab?.id || "") === tabId) || typeof activate !== "function") return false;
    const result = await activate(tabId);
    return result === true || String(result?.id || "") === tabId;
  }

  const api = { OWNER, projectItemId, tabIdFromProjectItemId, kindForTab, listItems, openItem };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  global.FigureStudioProjectOverview = api;
})(globalThis);
