(function attachScientificAssetColorControls(root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  if (root) root.FigureStudioScientificAssetColorControls = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function createScientificAssetColorControls() {
  "use strict";

  const HEX = /^#[0-9a-f]{6}$/i;
  const bindings = new WeakMap();
  let generatedPrefix = 0;
  const DEFAULT_PALETTES = [
    { id: "original", name: "Original" },
    { id: "pastel", name: "Pastel" },
    { id: "vivid", name: "Vivid" },
    { id: "monochrome", name: "Monochrome" }
  ];

  function escape(value) {
    return String(value == null ? "" : value).replace(/[&<>"']/g, (character) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
    }[character]));
  }

  function hex(value) {
    return typeof value === "string" && HEX.test(value) ? value.toUpperCase() : "";
  }

  function normalizedRegions(source) {
    const seen = new Set();
    return (Array.isArray(source) ? source : []).filter((region) => {
      if (!region || typeof region.id !== "string" || !region.id || seen.has(region.id)) return false;
      seen.add(region.id);
      return true;
    }).map((region) => ({
      id: region.id,
      label: String(region.label || region.id.replace(/[_-]+/g, " ")),
      default: hex(region.default) || "#000000"
    }));
  }

  function normalizedPalettes(source) {
    const seen = new Set();
    const result = (Array.isArray(source) ? source : DEFAULT_PALETTES).filter((palette) => {
      const id = palette?.id;
      if (typeof id !== "string" || !/^[a-z0-9_-]+$/i.test(id) || id.toLowerCase() === "custom" || seen.has(id)) return false;
      seen.add(id);
      return true;
    }).map((palette) => ({ id: palette.id, name: String(palette.name || palette.label || palette.id) }));
    if (!seen.has("original")) result.unshift({ id: "original", name: "Original" });
    return result;
  }

  function normalizedOverrides(source, regions) {
    const overrides = new Map();
    for (const region of regions) {
      if (source && Object.prototype.hasOwnProperty.call(source, region.id)) {
        const value = hex(source[region.id]);
        if (value) overrides.set(region.id, value);
      }
    }
    return overrides;
  }

  function render(meta, options = {}) {
    const mode = options.mode === "advanced" ? "advanced" : "simple";
    const regions = normalizedRegions(options.regions || meta?.editableColorRegions || meta?.editable_color_regions);
    if (!regions.length) return "";
    const prefix = typeof options.prefix === "string" && /^[a-z][a-z0-9_-]*$/i.test(options.prefix)
      ? options.prefix : `scientific-colors-${++generatedPrefix}`;
    const headingId = `${prefix}-heading`;
    const hintId = `${prefix}-custom-hint`;
    const palettes = normalizedPalettes(options.palettes);
    const requestedPalette = options.paletteId || meta?.paletteId || "original";
    const paletteId = palettes.some((palette) => palette.id === requestedPalette) ? requestedPalette : "original";
    const sourceOverrides = options.overrides || meta?.colorOverrides || {};
    const overrides = normalizedOverrides(sourceOverrides, regions);
    const sourceCustomOverrides = Object.prototype.hasOwnProperty.call(options, "customOverrides")
      ? options.customOverrides : meta && Object.prototype.hasOwnProperty.call(meta, "customColorOverrides")
        ? meta.customColorOverrides : sourceOverrides;
    const customOverrides = normalizedOverrides(sourceCustomOverrides, regions);
    const locked = Boolean(options.locked);
    const disabled = locked ? " disabled" : "";
    const custom = Boolean(options.hasCustomColors) && customOverrides.size > 0;
    const canResetAll = paletteId !== "original" || overrides.size > 0 || customOverrides.size > 0;
    const showHeading = options.heading !== false;
    const showResetAll = options.resetAll !== false;
    const heading = showHeading ? `<strong id="${headingId}">Colors</strong>` : "";
    const resetAll = showResetAll
      ? `<button type="button" class="asset-colors-reset" data-asset-colors-reset aria-label="Reset this asset’s colors" title="Reset palette and part colors; keep individual component edits"${locked || !canResetAll ? " disabled" : ""}>Reset colors</button>`
      : "";
    const header = heading || resetAll ? `<div class="asset-color-header">${heading}${resetAll}</div>` : "";
    const paletteOptions = palettes.map((palette) =>
      `<option value="${escape(palette.id)}"${palette.id === paletteId ? " selected" : ""}>${escape(palette.name)}</option>`
    ).join("");
    const rows = regions.map((region, index) => {
      const inputId = `${prefix}-part-${index}`;
      const labelId = `${inputId}-label`;
      const reset = mode === "advanced"
        ? `<button type="button" class="asset-color-reset" data-asset-color-reset="${escape(region.id)}" aria-label="${escape(`Reset ${region.label} color`)}"${locked || !customOverrides.has(region.id) ? " disabled" : ""}>Reset</button>`
        : "";
      return `<div class="asset-color-row" data-asset-color-row="${escape(region.id)}">` +
        `<label class="asset-color-name" id="${labelId}" for="${inputId}">${escape(region.label)}</label>` +
        `<input type="color" id="${inputId}" value="${overrides.get(region.id) || region.default}" data-asset-color-region="${escape(region.id)}" aria-labelledby="${labelId}"${disabled}>${reset}</div>`;
    }).join("");
    const disabledReason = typeof options.disabledReason === "string" && options.disabledReason.trim()
      ? ` title="${escape(options.disabledReason)}"` : "";
    return `<section class="scientific-asset-colors scientific-asset-colors-${mode}" data-scientific-asset-colors="${mode}"${showHeading ? ` aria-labelledby="${headingId}"` : ' aria-label="Colors"'}${disabledReason}>` + header +
      `<label class="asset-palette-control" for="${prefix}-palette"><span id="${prefix}-palette-label">Palette</span>` +
      `<select id="${prefix}-palette" data-asset-palette aria-labelledby="${prefix}-palette-label"${custom ? ` aria-describedby="${hintId}"` : ""}${disabled}>${paletteOptions}</select></label>` +
      (custom ? `<p class="asset-colors-custom-hint" id="${hintId}">Your edited part colors are kept.</p>` : "") +
      `<div class="asset-color-list">${rows}</div></section>`;
  }

  function bind(surface, callbacks = {}) {
    if (!surface || typeof surface.addEventListener !== "function") return () => {};
    bindings.get(surface)?.();
    const controlFor = (event, selector) => {
      const control = event.target?.closest?.(selector);
      return control && surface.contains(control) && !control.disabled ? control : null;
    };
    const onChange = (event) => {
      const palette = controlFor(event, "select[data-asset-palette]");
      if (palette) {
        const validOption = Array.from(palette.options || []).some((option) => option.value === palette.value && !option.disabled);
        if (validOption) callbacks.onPalette?.(palette.value, event);
        return;
      }
      const part = controlFor(event, 'input[type="color"][data-asset-color-region]');
      const color = part && hex(part.value);
      if (part && part.dataset.assetColorRegion && color) callbacks.onPartColor?.(part.dataset.assetColorRegion, color, event);
    };
    const onClick = (event) => {
      const resetAll = controlFor(event, "button[data-asset-colors-reset]");
      if (resetAll) {
        event.preventDefault();
        callbacks.onResetAll?.(event);
        return;
      }
      const resetPart = controlFor(event, "button[data-asset-color-reset]");
      if (resetPart && resetPart.dataset.assetColorReset) {
        event.preventDefault();
        callbacks.onResetPart?.(resetPart.dataset.assetColorReset, event);
      }
    };
    surface.addEventListener("change", onChange);
    surface.addEventListener("click", onClick);
    let cleaned = false;
    const cleanup = () => {
      if (cleaned) return;
      cleaned = true;
      surface.removeEventListener("change", onChange);
      surface.removeEventListener("click", onClick);
      if (bindings.get(surface) === cleanup) bindings.delete(surface);
    };
    bindings.set(surface, cleanup);
    return cleanup;
  }

  return { render, bind };
});
