(function attachFigureStudioScientificAssetPreview(root, factory) {
  const api = factory(root);
  if (typeof module === "object" && module.exports) module.exports = api;
  if (root) root.FigureStudioScientificAssetPreview = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function createScientificAssetPreviewApi(root) {
  "use strict";

  const controllers = new WeakMap();
  const HEX = /^#[0-9a-f]{6}$/i;

  function create(callbacks = {}) {
    const document = root.document;
    const dialog = document?.getElementById("assetPreviewDialog");
    if (!dialog) throw new Error("The Library preview dialog is unavailable.");
    if (controllers.has(dialog)) return controllers.get(dialog);
    const element = (suffix) => document.getElementById(`assetPreview${suffix}`);
    const els = Object.fromEntries([
      "Title", "CloseBtn", "VariantSelect", "Image", "Appearance", "Description",
      "Limitations", "PartsHeading", "Parts", "EditHint", "Status", "ReplacementNote",
      "InsertBtn", "ReplaceSelectedBtn", "Eyebrow", "SearchField", "SearchInput", "ScopeField", "ScopeLabel", "IncludeCopies", "EditedField", "AllowEdited"
    ].map((suffix) => [suffix, element(suffix)]));
    if (Object.values(els).some((entry) => !entry)) throw new Error("The Library preview dialog is incomplete.");
    const state = { open: false, assetId: "", contextId: "", loading: false, busy: false, mode: "preview" };
    let serial = 0;
    let focusOrigin = null;
    let variants = [];
    let previewReady = false;
    const drafting = typeof callbacks.createDraft === "function";
    const clone = (value) => value == null ? null : JSON.parse(JSON.stringify(value));
    let draft = null;
    let displayedDraft = null;
    let draftRegions = [];
    let draftPaletteOverrides = {};
    let unbindParts = null;
    const contextId = () => String(callbacks.contextId?.() ?? "");
    const count = (value) => Number.isFinite(Number(value)) ? Math.max(0, Math.floor(Number(value))) : 0;
    const asset = () => callbacks.getAsset?.(state.assetId);

    function focusAfterClose(origin, assetId) {
      const matching = [...document.querySelectorAll("[data-asset-preview-id]")]
        .find((button) => button.dataset.assetPreviewId === assetId);
      for (const target of [origin, matching, document.getElementById("assetSearchInput")]) {
        if (!target?.isConnected || target.disabled || typeof target.focus !== "function") continue;
        target.focus({ preventScroll: true });
        if (document.activeElement === target) break;
      }
    }

    function close({ restoreFocus = true, force = false } = {}) {
      if (state.busy && !force) return false;
      if (!state.open && !dialog.open) return true;
      const previousId = state.assetId;
      const origin = focusOrigin;
      serial += 1;
      const changing = state.mode === "change";
      Object.assign(state, { open: false, assetId: "", contextId: "", loading: false, busy: false, mode: "preview" });
      previewReady = false;
      draft = displayedDraft = null;
      draftRegions = [];
      draftPaletteOverrides = {};
      unbindParts?.();
      unbindParts = null;
      if (drafting) els.Parts.replaceChildren();
      focusOrigin = null;
      if (dialog.open) dialog.close();
      dialog.hidden = true;
      els.Image.removeAttribute("src");
      if (changing) callbacks.onCloseChange?.();
      if (restoreFocus) focusAfterClose(origin, previousId);
      return true;
    }

    function current(token) {
      if (state.open && state.contextId !== contextId()) {
        close({ restoreFocus: false, force: true });
        return false;
      }
      return state.open && token === serial;
    }

    function replacementInfo() {
      return (drafting ? callbacks.replacementInfo?.(asset(), clone(draft)) : callbacks.replacementInfo?.(asset())) || {};
    }

    function updateControls() {
      if (state.open && state.contextId !== contextId()) {
        close({ restoreFocus: false, force: true });
        return;
      }
      const info = replacementInfo();
      const unavailable = state.loading || state.busy || !state.open || !previewReady;
      const changing = state.mode === "change";
      els.CloseBtn.disabled = state.busy;
      els.VariantSelect.disabled = state.busy || !variants.length || (!changing && variants.length < 2);
      els.SearchField.hidden = !changing;
      els.SearchInput.disabled = state.busy;
      els.Eyebrow.textContent = changing ? "Change drawing" : "Library preview";
      els.InsertBtn.hidden = changing;
      els.InsertBtn.disabled = unavailable;
      els.ReplaceSelectedBtn.hidden = !changing;
      els.ReplaceSelectedBtn.disabled = unavailable || info.checking || info.selectedDisabled === true || !count(info.selectedCount)
        || !variants.some((variant) => variant.id === state.assetId) || (info.edited && !els.AllowEdited.checked);
      const others = count(info.otherCount);
      els.ScopeField.hidden = !changing || !others;
      els.IncludeCopies.disabled = unavailable || info.checking || !others;
      if (!others) els.IncludeCopies.checked = false;
      els.ScopeLabel.textContent = `Also change ${others} matching ${others === 1 ? "copy" : "copies"} on this ${info.documentKind || "figure"}`;
      els.EditedField.hidden = !changing || !info.edited;
      els.AllowEdited.disabled = unavailable || info.checking;
      els.ReplaceSelectedBtn.textContent = String(info.actionLabel || (els.IncludeCopies.checked ? `Change ${others + 1} drawings` : "Change drawing"));
      els.ReplacementNote.textContent = changing ? String(info.note || "") : "Library cards and previews insert a new drawing. Existing artwork stays as it is.";
      if (drafting) els.Parts.inert = state.busy;
    }

    function renderDetails(source) {
      const name = String(source.name || source.scientific_name || source.id);
      els.Title.textContent = name;
      els.Image.alt = `${name} preview`;
      els.Description.textContent = String(source.description || "");
      els.EditHint.textContent = String(callbacks.partColorHint?.() || "After insertion, select the drawing to change its part colors in Inspector > Appearance.");
      const recordedLimits = Array.isArray(source.scientific_limitations)
        ? source.scientific_limitations : source.scientific_limitations ? [source.scientific_limitations] : [];
      const description = String(source.description || "").trim();
      const limits = [...new Set(recordedLimits.map(String).map((value) => value.trim()))]
        .filter((value) => value && value !== description);
      els.Limitations.replaceChildren();
      for (const value of limits) {
        const item = document.createElement("li");
        item.textContent = String(value);
        els.Limitations.append(item);
      }
      if (!limits.length) {
        const item = document.createElement("li");
        item.textContent = "No additional limitations are recorded for this drawing.";
        els.Limitations.append(item);
      }
      const changing = state.mode === "change";
      const choices = changing ? callbacks.getChoices?.(els.SearchInput.value) || [] : callbacks.getVariants?.(source) || [];
      variants = [...new Map([...choices, ...(changing && els.SearchInput.value ? [] : [source])]
        .filter((entry) => entry?.id).map((entry) => [entry.id, entry])).values()];
      els.VariantSelect.replaceChildren();
      if (changing && !variants.some((variant) => variant.id === source.id)) {
        const prompt = document.createElement("option");
        prompt.value = "";
        prompt.textContent = "Choose a drawing…";
        prompt.disabled = true;
        els.VariantSelect.append(prompt);
      }
      for (const variant of variants) {
        const option = document.createElement("option");
        option.value = variant.id;
        option.textContent = changing ? String(callbacks.changeChoiceLabel?.(variant) || variant.name || variant.id)
          : String(callbacks.choiceLabel?.(variant, variants) || variant.name || variant.id);
        els.VariantSelect.append(option);
      }
      els.VariantSelect.value = source.id;
    }

    function renderParts(regions, overrides) {
      els.Parts.replaceChildren();
      const seen = new Set();
      for (const region of Array.isArray(regions) ? regions : []) {
        if (!region?.id || seen.has(region.id)) continue;
        seen.add(region.id);
        const row = document.createElement(["UL", "OL"].includes(els.Parts.tagName) ? "li" : "div");
        const swatch = document.createElement("span");
        swatch.className = "asset-preview-swatch";
        swatch.setAttribute("aria-hidden", "true");
        const override = overrides?.[region.id];
        const color = typeof override === "string" && HEX.test(override) ? override
          : typeof region.default === "string" && HEX.test(region.default) ? region.default : "";
        if (color) swatch.style.backgroundColor = color;
        else swatch.hidden = true;
        const label = document.createElement("span");
        label.textContent = String(region.label || region.id);
        row.append(swatch, label);
        els.Parts.append(row);
      }
      els.PartsHeading.textContent = `Editable part colors (${seen.size})`;
    }

    function changeDraft(update) {
      if (!drafting || !draft || !current(serial) || state.busy) return;
      const next = clone(draft);
      update(next);
      if (JSON.stringify(next) === JSON.stringify(draft) && (previewReady || state.loading)) return;
      draft = next;
      void showAsset(state.assetId, { draftRefresh: true });
    }

    function changePart(id, color) {
      const region = draftRegions.find((entry) => entry.id === id);
      if (!region || !HEX.test(String(color || ""))) return;
      changeDraft((next) => {
        const baseline = draftPaletteOverrides[id] || region.default;
        if (String(baseline).toUpperCase() === color.toUpperCase()) delete next.customColorOverrides[id];
        else next.customColorOverrides[id] = color.toUpperCase();
      });
    }

    function renderDraftParts(loaded, preserveControls) {
      const controls = root.FigureStudioScientificAssetColorControls;
      if (!controls?.render || !controls?.bind) throw new Error("Preview color controls are unavailable.");
      const regions = Array.isArray(loaded.regions) ? loaded.regions : [];
      const identity = (entries) => JSON.stringify(entries.map((entry) => [entry.id, entry.label]));
      const rebuild = !preserveControls || identity(regions) !== identity(draftRegions);
      draftRegions = clone(regions);
      draftPaletteOverrides = clone(loaded.paletteOverrides || loaded.paletteColorOverrides
        || root.FigureStudioScientificAssetPalettes?.paletteRegionOverrides(draft.paletteId, asset()?.editable_color_regions || regions) || {});
      const overrides = { ...draftPaletteOverrides, ...(loaded.colorOverrides || {}), ...draft.customColorOverrides };
      if (rebuild) {
        unbindParts?.();
        els.Parts.innerHTML = controls.render({}, {
          mode: "advanced", prefix: "asset-preview-colors", heading: false, resetAll: true,
          regions, palettes: root.FigureStudioScientificAssetPalettes?.getPalettes?.(),
          paletteId: draft.paletteId, overrides, customOverrides: draft.customColorOverrides,
          hasCustomColors: Object.keys(draft.customColorOverrides).length > 0
        });
        unbindParts = controls.bind(els.Parts, {
          onPalette: (id) => changeDraft((next) => { next.paletteId = id; }),
          onPartColor: changePart, onPartColorInput: changePart,
          onResetPart: (id) => {
            if (draftRegions.some((entry) => entry.id === id)) changeDraft((next) => { delete next.customColorOverrides[id]; });
          },
          onResetAll: () => changeDraft((next) => { next.paletteId = "original"; next.customColorOverrides = {}; })
        });
      }
      const palette = els.Parts.querySelector("select[data-asset-palette]");
      if (palette) palette.value = draft.paletteId;
      for (const input of els.Parts.querySelectorAll('input[type="color"][data-asset-color-region]')) {
        const region = regions.find((entry) => entry.id === input.dataset.assetColorRegion);
        const color = overrides[region?.id] || region?.default;
        if (HEX.test(String(color || "")) && input.value.toUpperCase() !== color.toUpperCase()) input.value = color;
      }
      for (const button of els.Parts.querySelectorAll("button[data-asset-color-reset]")) {
        button.disabled = !Object.hasOwn(draft.customColorOverrides, button.dataset.assetColorReset);
      }
      const reset = els.Parts.querySelector("button[data-asset-colors-reset]");
      if (reset) reset.disabled = draft.paletteId === "original" && !Object.keys(draft.customColorOverrides).length;
      let hint = els.Parts.querySelector(".asset-colors-custom-hint");
      if (!hint && Object.keys(draft.customColorOverrides).length) {
        hint = document.createElement("p");
        hint.className = "asset-colors-custom-hint";
        hint.id = "asset-preview-colors-custom-hint";
        hint.textContent = "Your edited part colors are kept.";
        els.Parts.append(hint);
      }
      if (hint) {
        hint.hidden = !Object.keys(draft.customColorOverrides).length;
        if (palette && !hint.hidden) palette.setAttribute("aria-describedby", hint.id);
        else palette?.removeAttribute("aria-describedby");
      }
      els.PartsHeading.textContent = `Editable part colors (${new Set(regions.map((entry) => entry.id)).size})`;
    }

    async function showAsset(assetId, options = {}) {
      const source = callbacks.getAsset?.(String(assetId || ""));
      if (!source || state.busy) return false;
      const refreshing = drafting && options.draftRefresh === true && state.assetId === source.id;
      const token = ++serial;
      state.assetId = source.id;
      state.loading = true;
      previewReady = false;
      if (!refreshing) {
        els.Image.removeAttribute("src");
        els.Appearance.textContent = "";
        els.Parts.replaceChildren();
        els.PartsHeading.textContent = "Editable part colors";
        displayedDraft = null;
        draftRegions = [];
        unbindParts?.();
        unbindParts = null;
      }
      els.Status.textContent = "Loading preview…";
      try {
        if (!refreshing) {
          if (drafting) {
            draft = clone(callbacks.createDraft(source, { mode: state.mode, previousDraft: clone(draft) }));
            if (!draft || draft.assetId !== source.id) throw new Error("Invalid preview appearance draft.");
            draft.customColorOverrides = Object.fromEntries(Object.entries(draft.customColorOverrides || {})
              .filter(([, color]) => typeof color === "string" && HEX.test(color)).map(([id, color]) => [id, color.toUpperCase()]));
          }
          renderDetails(source);
        }
        const snapshot = clone(draft);
        updateControls();
        if (!current(token)) return false;
        const loaded = drafting
          ? await callbacks.getPreview(source, clone(snapshot))
          : await callbacks.loadPreview(source);
        if (!current(token)) return false;
        if (typeof loaded?.svgText !== "string" || !loaded.svgText.trim()) throw new Error("Preview unavailable.");
        els.Image.src = `data:image/svg+xml;charset=utf-8,${encodeURIComponent(loaded.svgText)}`;
        await els.Image.decode();
        if (!current(token)) return false;
        els.Appearance.textContent = String(loaded.appearanceLabel || "");
        if (drafting) {
          renderDraftParts(loaded, refreshing);
          displayedDraft = snapshot;
        } else renderParts(loaded.regions, loaded.paletteOverrides);
        state.loading = false;
        previewReady = true;
        els.Status.textContent = state.mode === "change" ? "Choose a drawing, then confirm below." : "Ready to insert.";
        updateControls();
        return true;
      } catch (_error) {
        if (!current(token)) return false;
        state.loading = false;
        displayedDraft = null;
        els.Image.removeAttribute("src");
        els.Status.textContent = "This preview could not be loaded. Choose another drawing or try again.";
        updateControls();
        return false;
      }
    }

    async function open(assetId, returnFocus, options = {}) {
      if (state.busy || !callbacks.getAsset?.(String(assetId || ""))) return false;
      if (!state.open) focusOrigin = returnFocus || document.activeElement;
      else if (returnFocus) focusOrigin = returnFocus;
      const mode = options.mode === "change" ? "change" : "preview";
      if (!state.open || state.mode !== mode || state.contextId !== contextId()) draft = null;
      state.open = true;
      state.mode = mode;
      els.SearchInput.value = "";
      els.IncludeCopies.checked = false;
      els.AllowEdited.checked = false;
      state.contextId = contextId();
      dialog.hidden = false;
      if (!dialog.open) dialog.showModal();
      return showAsset(assetId);
    }

    async function act(action, button) {
      if (!current(serial) || state.loading || state.busy || button.disabled) return;
      updateControls();
      if (button.disabled) return;
      const token = serial;
      const id = state.assetId;
      state.busy = true;
      updateControls();
      els.Status.textContent = action === "insert" ? "Inserting drawing…"
        : replacementInfo().actionLabel === "Apply colors" ? "Applying colors…" : "Replacing drawings…";
      try {
        const actionOptions = { includeCopies: els.IncludeCopies.checked, allowEdited: els.AllowEdited.checked };
        if (drafting) actionOptions.appearanceDraft = clone(displayedDraft);
        const success = await callbacks.onAction?.(action, id, actionOptions);
        if (!current(token)) return;
        state.busy = false;
        if (success) close({ restoreFocus: false });
        else {
          updateControls();
          els.Status.textContent = "The action could not be completed. You can try again.";
        }
      } catch (_error) {
        if (!current(token)) return;
        state.busy = false;
        updateControls();
        els.Status.textContent = "The action could not be completed. You can try again.";
      }
    }

    dialog.addEventListener("keydown", (event) => {
      event.stopPropagation();
      if (event.key === "Tab" && state.open) {
        const controls = [...dialog.querySelectorAll('button:not(:disabled), select:not(:disabled), input:not(:disabled), a[href], [tabindex]:not([tabindex="-1"])')]
          .filter((node) => node.getClientRects().length && root.getComputedStyle(node).visibility !== "hidden");
        const index = controls.indexOf(document.activeElement);
        const next = event.shiftKey
          ? index <= 0 ? controls.length - 1 : index - 1
          : index < 0 || index === controls.length - 1 ? 0 : index + 1;
        event.preventDefault();
        controls[next]?.focus({ preventScroll: true });
      }
      if ((event.ctrlKey || event.metaKey) && ["s", "o"].includes(event.key.toLowerCase())) event.preventDefault();
    });
    dialog.addEventListener("cancel", (event) => { event.preventDefault(); close(); });
    dialog.addEventListener("close", () => { if (!dialog.open) close({ force: true }); });
    els.CloseBtn.addEventListener("click", () => close());
    els.SearchInput.addEventListener("input", () => {
      if (!current(serial) || state.busy || state.mode !== "change") return;
      renderDetails(asset());
      updateControls();
      els.Status.textContent = variants.length ? `${variants.length} drawings found. Choose one from Drawing / view.` : "No drawings match. Try another biological term.";
    });
    els.IncludeCopies.addEventListener("change", updateControls);
    els.AllowEdited.addEventListener("change", updateControls);
    els.VariantSelect.addEventListener("change", () => {
      if (current(serial) && !state.busy && variants.some((entry) => entry.id === els.VariantSelect.value)) {
        void showAsset(els.VariantSelect.value);
      }
    });
    for (const [action, button] of [
      ["insert", els.InsertBtn], ["change", els.ReplaceSelectedBtn]
    ]) button.addEventListener("click", () => { void act(action, button); });
    const controller = Object.freeze({ open, close, refresh: updateControls,
      getState: () => drafting ? { ...state, draft: clone(draft), displayedDraft: clone(displayedDraft) } : { ...state } });
    controllers.set(dialog, controller);
    return controller;
  }

  return Object.freeze({ create });
});
