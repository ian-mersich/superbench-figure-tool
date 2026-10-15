(function (root) {
  "use strict";

  // Previews are first-party vector drawings, independent of canvas bounds.
  const presets = [
    { id: "straight", group: "Lines", label: "Straight", tool: "line", legacyTool: "line", route: "straight" },
    { id: "curved", group: "Lines", label: "Curved", tool: "line", route: "curved" },
    { id: "orthogonal", group: "Lines", label: "Orthogonal", tool: "line", route: "elbow" },
    { id: "dashed", group: "Lines", label: "Dashed", tool: "dashedLine", legacyTool: "dashedLine", route: "straight", dash: "dashed" },
    { id: "dotted", group: "Lines", label: "Dotted", tool: "line", route: "straight", dash: "dotted" },
    { id: "arrow", group: "Arrows", label: "Straight", tool: "arrow", legacyTool: "arrow", route: "straight", end: "triangle" },
    { id: "curved-arrow", group: "Arrows", label: "Curved", tool: "arrow", route: "curved", end: "triangle" },
    { id: "orthogonal-arrow", group: "Arrows", label: "Orthogonal", tool: "arrow", route: "elbow", end: "triangle" },
    { id: "dashed-arrow", group: "Arrows", label: "Dashed", tool: "arrow", route: "straight", dash: "dashed", end: "triangle" },
    { id: "double-arrow", group: "Arrows", label: "Both ends", tool: "arrow", route: "straight", start: "triangle", end: "triangle" },
    { id: "curved-double-arrow", group: "Arrows", label: "Curved, both ends", tool: "arrow", route: "curved", start: "triangle", end: "triangle" },
    { id: "inhibitor", group: "Inhibition", label: "Straight", tool: "line", route: "straight", end: "bar" },
    { id: "curved-inhibitor", group: "Inhibition", label: "Curved", tool: "line", route: "curved", end: "bar" },
    { id: "orthogonal-inhibitor", group: "Inhibition", label: "Orthogonal", tool: "line", route: "elbow", end: "bar" },
    { id: "dot-end", group: "Dots", label: "End dot", tool: "line", route: "straight", end: "dot" },
    { id: "dot-both", group: "Dots", label: "Both ends", tool: "line", route: "straight", start: "dot", end: "dot" },
    { id: "diamond-end", group: "Dots", label: "End diamond", tool: "line", route: "straight", end: "diamond" },
    { id: "arc", group: "Circular", label: "Arc", tool: "arc", legacyTool: "arc", shape: "arc" },
    { id: "ring", group: "Circular", label: "Circle outline", tool: "ring", shape: "ring" },
    { id: "comparison-bracket", group: "Brackets", label: "Comparison bracket", command: "insert-comparison-bracket", shape: "bracket" },
    { id: "curve", group: "Custom", label: "Bézier curve", tool: "curve", legacyTool: "curve", shape: "curve" },
    { id: "wave", group: "Custom", label: "Wave", tool: "wave", legacyTool: "wave", shape: "wave" },
    { id: "freehand", group: "Custom", label: "Freehand", tool: "freehand", legacyTool: "freehand", shape: "freehand" },
    { id: "smart-connector", group: "Custom", label: "Attach to objects", tool: "smartConnector", legacyTool: "smartConnector", shape: "connector" }
  ];

  function stylePatch(preset) {
    return {
      arrowStart: preset.start || "none",
      arrowEnd: preset.end || "none",
      arrowHead: preset.end || "none",
      lineDash: preset.dash || "solid"
    };
  }

  function previewMarkup(preset) {
    const path = preset.shape === "arc" || preset.shape === "curve" ? "M 14 31 C 24 5 64 5 74 31"
      : preset.shape === "ring" ? "M 61 23 A 17 17 0 1 1 27 23 A 17 17 0 1 1 61 23"
        : preset.shape === "bracket" ? "M 14 31 V 15 H 74 V 31"
          : preset.shape === "wave" || preset.shape === "freehand" ? "M 12 27 C 23 7 28 7 39 24 S 58 41 76 17"
            : preset.route === "curved" ? "M 14 29 C 30 29 34 13 50 13 S 64 13 74 13"
              : preset.route === "elbow" ? "M 14 31 H 44 V 15 H 74"
                : "M 14 23 H 74";
    const endY = ["curved", "elbow"].includes(preset.route) ? (preset.route === "curved" ? 13 : 15) : 23;
    const startY = preset.route === "curved" ? 29 : preset.route === "elbow" ? 31 : 23;
    const head = (kind, x, y, start) => kind === "triangle"
      ? `<path d="M ${x} ${y} l ${start ? 8 : -8} -4.5 v 9 Z" fill="currentColor" stroke="none"/>`
      : kind === "bar" ? `<path d="M ${x} ${y - 7} v 14"/>`
        : kind === "dot" ? `<circle cx="${x}" cy="${y}" r="4" fill="currentColor" stroke="none"/>`
          : kind === "diamond" ? `<path d="M ${x - 5} ${y} l 5 -5 5 5 -5 5 Z" fill="currentColor" stroke="none"/>` : "";
    const dash = preset.dash === "dashed" ? 'stroke-dasharray="7 5"' : preset.dash === "dotted" ? 'stroke-dasharray="1 5"' : "";
    return `<svg viewBox="0 0 88 46" aria-hidden="true" focusable="false" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="${path}" ${dash}/>${head(preset.start, 14, startY, true)}${head(preset.end, 74, endY, false)}${preset.shape === "connector" ? '<rect x="9" y="18" width="10" height="10" rx="2"/><rect x="69" y="18" width="10" height="10" rx="2"/>' : ""}</svg>`;
  }

  root.FigureToolLinePicker = Object.freeze({ presets, stylePatch, previewMarkup });
})(typeof window !== "undefined" ? window : globalThis);
