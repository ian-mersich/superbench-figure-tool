(function (root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  if (root) root.FigureStudioScientificTemplateCards = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  function escape(value) {
    return String(value ?? "").replace(/[&<>"']/g, (character) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
    })[character]);
  }

  function render(scene, options = {}) {
    const kind = options.documentKind === "presentation" ? "presentation" : "figure";
    const actions = Array.isArray(scene.actions) ? scene.actions : [];
    const modes = Array.isArray(scene.modes) ? scene.modes : [];
    const button = (action, label, primary = false) => `<button type="button" data-scene-id="${escape(scene.id)}" data-scene-action="${action}"${primary ? ' class="template-insert-action"' : ""}${options.busy ? " disabled" : ""}>${label}</button>`;
    const insert = actions.includes("insert_current_document") && modes.includes(kind)
      ? button("insert_current_document", kind === "presentation" ? "Insert on this slide" : "Insert in this figure", true) : "";
    const create = actions.includes("use_as_new_figure") && modes.includes("figure")
      ? button("use_as_new_figure", "New figure") : "";
    const notes = scene.biology_note || scene.limitations;
    return `<article class="scientific-scene-entry" data-scene-id="${escape(scene.id)}">
      <img class="scientific-scene-preview" src="${escape(scene._previewUrl || scene.preview)}" alt="Preview of ${escape(scene.name)}" loading="lazy" decoding="async">
      <div class="scientific-scene-copy">
        <strong class="scientific-template-title">${escape(scene.name)}</strong>
        <p>${escape(scene.card_summary || scene.summary)}</p>
      </div>
      <div class="scientific-scene-actions">${insert}${create}</div>
      ${notes ? `<details class="scientific-scene-notes"><summary>Scientific details</summary>
        ${scene.category ? `<p>${escape(scene.category)}</p>` : ""}
        ${scene.biology_note ? `<p>${escape(scene.biology_note)}</p>` : ""}
        ${scene.limitations ? `<p><strong>Limits:</strong> ${escape(scene.limitations)}</p>` : ""}
      </details>` : ""}
    </article>`;
  }

  return Object.freeze({ render });
});
