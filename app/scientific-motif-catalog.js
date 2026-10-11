(function attachFigureStudioScientificMotifCatalog(root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  if (root) root.FigureStudioScientificMotifCatalog = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function createScientificMotifCatalogApi() {
  "use strict";

  const PACK_ID = "free-bench-core-scientific-motifs";
  const PACK_VERSION = "1.0.0";
  const RIGHTS_RECORD_ID = "free-bench-core-scientific-motifs-cc0-1.0";
  const SOURCE_RECORD_ID = "free-bench-core-scientific-motifs-original-geometry-v1";

  function circlePoints(cx, cy, radius, count = 16) {
    return Array.from({ length: count }, (_value, index) => {
      const angle = Math.PI * 2 * index / count;
      return { x: cx + Math.cos(angle) * radius, y: cy + Math.sin(angle) * radius };
    });
  }

  function piece({ points, closed = false, fillRole = "", strokeRole = "", strokeWidth = 0, opacity = 1 }) {
    return Object.freeze({
      subpaths: Object.freeze([{ points: Object.freeze(points.map((point) => Object.freeze({ x: point.x, y: point.y }))), closed }]),
      fillRole,
      strokeRole,
      strokeWidth,
      opacity,
      fillRule: "nonzero"
    });
  }

  function dot(cx, cy, radius, fillRole = "primary", strokeRole = "outline") {
    return piece({ points: circlePoints(cx, cy, radius), closed: true, fillRole, strokeRole, strokeWidth: 0.9 });
  }

  function line(points, strokeRole = "secondary", strokeWidth = 1.6) {
    return piece({ points, strokeRole, strokeWidth });
  }

  function motif(definition) {
    return Object.freeze({
      schema: "figureStudio.scientificMotif.v1",
      packId: PACK_ID,
      packVersion: PACK_VERSION,
      rightsRecordId: RIGHTS_RECORD_ID,
      sourceRecordId: SOURCE_RECORD_ID,
      intendedUse: "Editable schematic illustration of a repeated scientific structure.",
      ...definition,
      bounds: Object.freeze({ ...definition.bounds }),
      defaultColors: Object.freeze({ ...definition.defaultColors }),
      colorRoleLabels: Object.freeze({ ...definition.colorRoleLabels }),
      scientificLimits: Object.freeze([...definition.scientificLimits]),
      pieces: Object.freeze([...definition.pieces])
    });
  }

  const motifs = Object.freeze([
    motif({
      id: "phospholipid-monolayer",
      name: "Phospholipid monolayer",
      shortName: "Monolayer",
      category: "Membranes",
      bounds: { left: -6, top: -10, width: 12, height: 22 },
      defaultSpacing: 15,
      defaultScale: 1,
      defaultColors: { primary: "#4f9da6", secondary: "#334e68", outline: "#26323d" },
      colorRoleLabels: { primary: "Headgroups", secondary: "Hydrophobic tails", outline: "Outlines" },
      scientificLimits: [
        "Generic phospholipid-like schematic; it does not specify lipid composition, leaflet identity, polarity, or compartment."
      ],
      pieces: [
        dot(0, -6.5, 3.4, "primary", "outline"),
        line([{ x: -1.4, y: -3.2 }, { x: -2.2, y: 3.5 }, { x: -1.4, y: 10 }], "secondary", 1.5),
        line([{ x: 1.4, y: -3.2 }, { x: 2.3, y: 3.5 }, { x: 1.5, y: 10 }], "secondary", 1.5)
      ]
    }),
    motif({
      id: "phospholipid-bilayer",
      name: "Phospholipid bilayer",
      shortName: "Bilayer",
      category: "Membranes",
      bounds: { left: -6, top: -16, width: 12, height: 32 },
      defaultSpacing: 15,
      defaultScale: 1,
      defaultColors: { primary: "#4f9da6", secondary: "#334e68", outline: "#26323d" },
      colorRoleLabels: { primary: "Headgroups", secondary: "Hydrophobic tails", outline: "Outlines" },
      scientificLimits: [
        "Generic symmetric bilayer schematic; it does not specify membrane composition, leaflet asymmetry, orientation, or compartment."
      ],
      pieces: [
        dot(0, -12.2, 3.4, "primary", "outline"),
        line([{ x: -1.4, y: -8.8 }, { x: -2.1, y: -4.2 }, { x: -1.2, y: -0.7 }], "secondary", 1.5),
        line([{ x: 1.4, y: -8.8 }, { x: 2.1, y: -4.2 }, { x: 1.2, y: -0.7 }], "secondary", 1.5),
        dot(0, 12.2, 3.4, "primary", "outline"),
        line([{ x: -1.4, y: 8.8 }, { x: -2.1, y: 4.2 }, { x: -1.2, y: 0.7 }], "secondary", 1.5),
        line([{ x: 1.4, y: 8.8 }, { x: 2.1, y: 4.2 }, { x: 1.2, y: 0.7 }], "secondary", 1.5)
      ]
    }),
    motif({
      id: "double-stranded-nucleic-acid",
      name: "Double-stranded nucleic acid",
      shortName: "Double strand",
      category: "Nucleic acids",
      bounds: { left: -8, top: -8, width: 16, height: 16 },
      defaultSpacing: 17,
      defaultScale: 1,
      defaultColors: { primary: "#4c78a8", secondary: "#e07a5f", outline: "#26323d" },
      colorRoleLabels: { primary: "Backbones", secondary: "Paired bases", outline: "Outlines" },
      scientificLimits: [
        "Generic double-stranded nucleic-acid schematic; it does not specify DNA versus RNA, sequence, base pairing, handedness, or molecular scale."
      ],
      pieces: [
        line([{ x: -8, y: -4 }, { x: -4, y: -6 }, { x: 0, y: -4 }, { x: 4, y: -2 }, { x: 8, y: -4 }], "primary", 2.1),
        line([{ x: -8, y: 4 }, { x: -4, y: 2 }, { x: 0, y: 4 }, { x: 4, y: 6 }, { x: 8, y: 4 }], "primary", 2.1),
        line([{ x: -4, y: -5.8 }, { x: -4, y: 2.2 }], "secondary", 1.25),
        line([{ x: 4, y: -2.2 }, { x: 4, y: 5.8 }], "secondary", 1.25)
      ]
    }),
    motif({
      id: "single-stranded-nucleic-acid",
      name: "Single-stranded nucleic acid",
      shortName: "Single strand",
      category: "Nucleic acids",
      bounds: { left: -8, top: -7, width: 16, height: 14 },
      defaultSpacing: 17,
      defaultScale: 1,
      defaultColors: { primary: "#4c78a8", secondary: "#f2c14e", outline: "#26323d" },
      colorRoleLabels: { primary: "Backbone", secondary: "Nucleotide markers", outline: "Outlines" },
      scientificLimits: [
        "Generic single-stranded nucleic-acid schematic; it does not specify DNA versus RNA, sequence, secondary structure, directionality, or molecular scale."
      ],
      pieces: [
        line([{ x: -8, y: 2 }, { x: -4, y: -3.5 }, { x: 0, y: 2.5 }, { x: 4, y: -2.5 }, { x: 8, y: 1.5 }], "primary", 2.1),
        dot(0, 2.5, 2.1, "secondary", "outline")
      ]
    }),
    motif({
      id: "vessel-tubule-wall",
      name: "Vessel or tubule wall",
      shortName: "Tubule wall",
      category: "Tissues",
      bounds: { left: -8, top: -11, width: 16, height: 22 },
      defaultSpacing: 18,
      defaultScale: 1,
      defaultColors: { primary: "#cf6f68", secondary: "#f2c7a5", outline: "#5b3741" },
      colorRoleLabels: { primary: "Wall cells", secondary: "Cell boundaries", outline: "Outlines" },
      scientificLimits: [
        "Generic paired wall schematic; it does not identify vessel class, epithelial or endothelial identity, tissue, lumen contents, flow, or anatomical scale."
      ],
      pieces: [
        piece({ points: [{ x: -8, y: -10 }, { x: 8, y: -10 }, { x: 8, y: -4 }, { x: -8, y: -4 }], closed: true, fillRole: "primary", strokeRole: "outline", strokeWidth: 0.9 }),
        piece({ points: [{ x: -8, y: 4 }, { x: 8, y: 4 }, { x: 8, y: 10 }, { x: -8, y: 10 }], closed: true, fillRole: "primary", strokeRole: "outline", strokeWidth: 0.9 }),
        line([{ x: 0, y: -9.6 }, { x: 0, y: -4.4 }], "secondary", 2),
        line([{ x: 0, y: 4.4 }, { x: 0, y: 9.6 }], "secondary", 2)
      ]
    }),
    motif({
      id: "actin-filament",
      name: "Actin filament",
      shortName: "Actin",
      category: "Cytoskeleton",
      bounds: { left: -9, top: -8, width: 18, height: 16 },
      defaultSpacing: 17,
      defaultScale: 1,
      defaultColors: { primary: "#7e57a3", secondary: "#b39ddb", outline: "#3f3155" },
      colorRoleLabels: { primary: "First filament strand", secondary: "Second filament strand", outline: "Outlines" },
      scientificLimits: [
        "Stylized filament motif; bead count, helical pitch, polymer polarity, binding partners, force, and molecular scale are not encoded."
      ],
      pieces: [
        dot(-4.2, -2.8, 4.3, "primary", "outline"),
        dot(4.2, 2.8, 4.3, "secondary", "outline")
      ]
    }),
    motif({
      id: "microtubule",
      name: "Microtubule",
      shortName: "Microtubule",
      category: "Cytoskeleton",
      bounds: { left: -9, top: -9, width: 18, height: 18 },
      defaultSpacing: 18,
      defaultScale: 1,
      defaultColors: { primary: "#2f8f9d", secondary: "#74c0c7", outline: "#24545c" },
      colorRoleLabels: { primary: "Alternating subunit 1", secondary: "Alternating subunit 2", outline: "Outlines" },
      scientificLimits: [
        "Stylized microtubule wall motif; protofilament number, seam, tubulin nucleotide state, polymer polarity, lumen, and molecular scale are not encoded."
      ],
      pieces: [
        dot(-4.2, -4.1, 4.1, "primary", "outline"),
        dot(4.2, -4.1, 4.1, "secondary", "outline"),
        dot(-4.2, 4.1, 4.1, "secondary", "outline"),
        dot(4.2, 4.1, 4.1, "primary", "outline")
      ]
    })
  ]);

  const byId = Object.freeze(Object.fromEntries(motifs.map((entry) => [entry.id, entry])));

  function getMotif(id) {
    return byId[String(id || "")] || null;
  }

  function listMotifs() {
    return motifs.slice();
  }

  return Object.freeze({
    schema: "figureStudio.scientificMotifPack.v1",
    packId: PACK_ID,
    packVersion: PACK_VERSION,
    rightsRecordId: RIGHTS_RECORD_ID,
    sourceRecordId: SOURCE_RECORD_ID,
    rights: "CC0-1.0",
    source: "Original geometric artwork authored for The Mersich Lab's Superbench Figure Tool project.",
    motifs,
    byId,
    getMotif,
    listMotifs
  });
});
