(function (root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory();
  else root.FigureStudioScientificProtocols = factory();
})(typeof globalThis !== "undefined" ? globalThis : this, function createScientificProtocolApi() {
  "use strict";

  const SCHEMA = "figureStudio.scientificProtocolComponent.v1";
  const LIMIT = "Communication diagram only; it does not validate a wet-lab protocol, reagent choice, instrument setting, or experimental result.";
  const DIRECTIONS = ["right", "down"];
  const ICONS = Object.freeze({
    sample: { label: "Sample", glyph: "●", assetId: "figure.protocol.symbol.sample", assetVersion: "1.0.0" },
    tube: { label: "Tube", glyph: "▱", assetId: "figure.protocol.symbol.tube", assetVersion: "1.0.0" },
    gel: { label: "Gel", glyph: "▥", assetId: "figure.protocol.symbol.gel", assetVersion: "1.0.0" },
    blot: { label: "Blot", glyph: "▦", assetId: "figure.protocol.symbol.blot", assetVersion: "1.0.0" },
    stain: { label: "Stain", glyph: "✦", assetId: "figure.protocol.symbol.stain", assetVersion: "1.0.0" },
    cytometer: { label: "Cytometer", glyph: "◫", assetId: "figure.protocol.symbol.cytometer", assetVersion: "1.0.0" },
    dotplot: { label: "Dot plot", glyph: "⠿", assetId: "figure.protocol.symbol.dot-plot", assetVersion: "1.0.0" }
  });
  const TYPES = Object.freeze({
    immunoblot: {
      label: "Immunoblot communication diagram",
      steps: [
        ["sample", "Prepare sample"], ["gel", "Separate proteins"], ["blot", "Transfer and probe"], ["blot", "Record signal"]
      ]
    },
    "flow-cytometry": {
      label: "Flow cytometry communication diagram",
      steps: [
        ["sample", "Prepare cells"], ["stain", "Label cells"], ["cytometer", "Acquire events"], ["dotplot", "Review populations"]
      ]
    }
  });

  function id(prefix = "step") {
    return `${prefix}-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
  }
  function clone(value) { return JSON.parse(JSON.stringify(value)); }
  function clamp(value, min, max) { return Math.min(max, Math.max(min, Number(value) || 0)); }
  function type(typeId) { return TYPES[typeId] || TYPES.immunoblot; }
  function normalizeStep(step, index, fallback) {
    const icon = ICONS[step?.icon] ? step.icon : (ICONS[fallback?.[0]] ? fallback[0] : "sample");
    const label = String(step?.label ?? fallback?.[1] ?? `Step ${index + 1}`).trim().slice(0, 80) || `Step ${index + 1}`;
    return { id: String(step?.id || id("protocol-step")), label, icon };
  }
  function normalize(value = {}) {
    const typeId = TYPES[value.type] ? value.type : "immunoblot";
    const defaults = type(typeId).steps;
    const raw = Array.isArray(value.steps) && value.steps.length ? value.steps : defaults.map(([icon, label]) => ({ icon, label }));
    return {
      schema: SCHEMA,
      id: String(value.id || id("protocol")),
      type: typeId,
      title: String(value.title || type(typeId).label).trim().slice(0, 100) || type(typeId).label,
      direction: DIRECTIONS.includes(value.direction) ? value.direction : "right",
      numbering: value.numbering !== false,
      spacing: clamp(value.spacing || 42, 20, 120),
      steps: raw.slice(0, 8).map((step, index) => normalizeStep(step, index, defaults[index % defaults.length])),
      scientificLimit: LIMIT,
      source: { kind: "figure-studio-authored-communication-diagram", evidence: "none", protocolValidated: false }
    };
  }
  function layout(value = {}) {
    const component = normalize(value);
    const horizontal = component.direction === "right";
    const stepWidth = 152;
    const stepHeight = 112;
    const titleHeight = 42;
    const items = component.steps.map((step, index) => ({
      ...step,
      number: component.numbering ? index + 1 : null,
      x: horizontal ? index * (stepWidth + component.spacing) : 0,
      y: titleHeight + (horizontal ? 0 : index * (stepHeight + component.spacing)),
      width: stepWidth,
      height: stepHeight,
      icon: clone(ICONS[step.icon])
    }));
    const connectors = items.slice(0, -1).map((item, index) => {
      const next = items[index + 1];
      return horizontal
        ? { fromStepId: item.id, toStepId: next.id, x1: item.x + stepWidth, y1: item.y + stepHeight / 2, x2: next.x, y2: next.y + stepHeight / 2 }
        : { fromStepId: item.id, toStepId: next.id, x1: item.x + stepWidth / 2, y1: item.y + stepHeight, x2: next.x + stepWidth / 2, y2: next.y };
    });
    const width = horizontal ? Math.max(stepWidth, items.length * stepWidth + Math.max(0, items.length - 1) * component.spacing) : stepWidth;
    const height = horizontal ? titleHeight + stepHeight : titleHeight + Math.max(stepHeight, items.length * stepHeight + Math.max(0, items.length - 1) * component.spacing);
    return { component, items, connectors, width, height, selectedAssets: items.map((item) => ({ stepId: item.id, assetId: item.icon.assetId, assetVersion: item.icon.assetVersion, label: item.icon.label, sourceKind: "figure-studio-original-schematic-symbol" })) };
  }
  function preview(value = {}) {
    const result = layout(value);
    return {
      schema: "figureStudio.scientificProtocolPreview.v1",
      complete: true,
      type: result.component.type,
      title: result.component.title,
      direction: result.component.direction,
      numbering: result.component.numbering,
      spacing: result.component.spacing,
      steps: result.items.map(({ id, label, number, icon }) => ({ id, label, number, icon: icon.label })),
      selectedAssets: result.selectedAssets,
      scientificLimits: [LIMIT],
      bounds: { width: result.width, height: result.height }
    };
  }
  return { SCHEMA, LIMIT, DIRECTIONS, ICONS, TYPES, normalize, layout, preview };
});
