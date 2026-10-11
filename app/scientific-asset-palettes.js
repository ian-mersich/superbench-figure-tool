(function attachScientificAssetPalettes(root, factory) {
  const api = factory(root && root.FigureStudioScientificAssetArtStyles);
  if (typeof module === "object" && module.exports) module.exports = api;
  if (root) root.FigureStudioScientificAssetPalettes = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function createScientificAssetPalettes(defaultArtStyles) {
  "use strict";

  const PALETTES = Object.freeze([
    Object.freeze({ id: "original", name: "Original", description: "Use the asset's original colors." }),
    Object.freeze({ id: "pastel", name: "Pastel", description: "Soft colors coordinated across biological parts." }),
    Object.freeze({ id: "vivid", name: "Vivid", description: "Stronger colors with light and dark parts retained." }),
    Object.freeze({ id: "monochrome", name: "Monochrome", description: "Distinct gray shades for biological parts." })
  ]);
  const HEX = /^#[0-9a-f]{6}$/i;
  const PALETTE_IDS = new Set(PALETTES.map((palette) => palette.id));

  function getPalettes() {
    return PALETTES.map((palette) => ({ ...palette }));
  }

  function normalizePalette(value) {
    return typeof value === "string" && PALETTE_IDS.has(value) ? value : "original";
  }

  function colorCoordinates(color) {
    const channels = [1, 3, 5].map((offset) => parseInt(color.slice(offset, offset + 2), 16) / 255);
    const [red, green, blue] = channels;
    const highest = Math.max(...channels);
    const lowest = Math.min(...channels);
    const chroma = highest - lowest;
    const lightness = (highest + lowest) / 2;
    let hue = 0;
    if (chroma) {
      if (highest === red) hue = ((green - blue) / chroma) % 6;
      else if (highest === green) hue = (blue - red) / chroma + 2;
      else hue = (red - green) / chroma + 4;
      hue = (hue * 60 + 360) % 360;
    }
    return { hue, chroma, lightness, luminance: 0.2126 * red + 0.7152 * green + 0.0722 * blue };
  }

  function grayHex(value) {
    const channel = Math.round(value).toString(16).padStart(2, "0").toUpperCase();
    return "#" + channel.repeat(3);
  }

  function hslHex(hue, saturation, lightness) {
    const chroma = (1 - Math.abs(2 * lightness - 1)) * saturation;
    const x = chroma * (1 - Math.abs((hue / 60) % 2 - 1));
    const offset = lightness - chroma / 2;
    const channels = hue < 60 ? [chroma, x, 0] : hue < 120 ? [x, chroma, 0]
      : hue < 180 ? [0, chroma, x] : hue < 240 ? [0, x, chroma]
        : hue < 300 ? [x, 0, chroma] : [chroma, 0, x];
    return "#" + channels.map((value) => Math.round((value + offset) * 255).toString(16).padStart(2, "0")).join("").toUpperCase();
  }

  function hueFamily(hue) {
    if (hue < 20 || hue >= 345) return 5;
    if (hue < 50) return 30;
    if (hue < 85) return 60;
    if (hue < 160) return 125;
    if (hue < 195) return 175;
    if (hue < 255) return 220;
    if (hue < 290) return 270;
    return 315;
  }

  function compareIds(left, right) {
    return left < right ? -1 : left > right ? 1 : 0;
  }

  function isStructural(region, coordinates) {
    const id = String(region.id || "").toLowerCase();
    return /(?:^|[-_])(?:outline|contour|structural)(?:$|[-_])/.test(id)
      || (coordinates.chroma < 0.12 && coordinates.lightness <= 0.24);
  }

  function paletteRegionOverrides(paletteId, sourceRegions) {
    const palette = normalizePalette(paletteId);
    if (palette === "original") return {};
    const ids = new Set();
    const regions = (Array.isArray(sourceRegions) ? sourceRegions : []).map((region) => {
      const id = typeof region?.id === "string" ? region.id : "";
      if (!id) throw new Error("Scientific palette regions require stable ids");
      if (ids.has(id)) throw new Error("Duplicate scientific palette region id: " + id);
      ids.add(id);
      const color = String(region.default || "").toUpperCase();
      if (!HEX.test(color) || color === "#FFFFFF") return null;
      const coordinates = colorCoordinates(color);
      return { id, color, coordinates, structural: isStructural(region, coordinates) };
    }).filter(Boolean);
    const compartments = regions.filter((region) => !region.structural).sort((left, right) =>
      left.coordinates.luminance - right.coordinates.luminance
      || left.coordinates.hue - right.coordinates.hue || compareIds(left.id, right.id));
    const grayLevels = new Map(compartments.map((region, index) =>
      [region.id, compartments.length < 2 ? 165 : 76 + index * 148 / (compartments.length - 1)]));
    const overrides = [];
    for (const region of regions.sort((left, right) => compareIds(left.id, right.id))) {
      let color;
      if (palette === "monochrome") {
        color = region.structural ? grayHex(region.coordinates.luminance * 255) : grayHex(grayLevels.get(region.id));
      } else if (region.structural) {
        color = region.color;
      } else {
        const band = region.coordinates.lightness < 0.4 ? 0 : region.coordinates.lightness < 0.72 ? 1 : 2;
        const lightness = (palette === "pastel" ? [0.56, 0.72, 0.87] : [0.38, 0.55, 0.74])[band];
        color = region.coordinates.chroma < 0.09 ? grayHex(lightness * 255)
          : hslHex(hueFamily(region.coordinates.hue), palette === "pastel" ? 0.48 : 0.75, lightness);
      }
      if (color !== region.color) overrides.push([region.id, color]);
    }
    return Object.fromEntries(overrides);
  }

  function transformAsset(svgText, sourceRegions, options = {}) {
    const artStyles = options.artStyles || defaultArtStyles;
    const styleId = artStyles?.normalizeStyle ? artStyles.normalizeStyle(options.styleId)
      : options.styleId === "cut-paper" || options.styleId === "technical-ink" ? options.styleId : "soft-color";
    if (styleId !== "soft-color" && (!artStyles?.transformSvg || !artStyles?.transformRegions)) {
      throw new Error("Alternate scientific styles require the existing art-style transformer");
    }
    const paletteId = normalizePalette(options.paletteId);
    const originalRegions = Array.isArray(sourceRegions) ? sourceRegions : [];
    const regions = artStyles?.transformRegions ? artStyles.transformRegions(originalRegions, styleId)
      : originalRegions.map((region) => ({ ...region }));
    const colorOverrides = paletteRegionOverrides(paletteId, originalRegions);
    let result = artStyles?.transformSvg ? artStyles.transformSvg(String(svgText || ""), styleId) : String(svgText || "");
    if (Object.keys(colorOverrides).length) {
      if (typeof options.recolorSvg !== "function") {
        throw new Error("Scientific palettes require a trusted semantic SVG paint callback");
      }
      const paintedRegions = regions.filter((region) => Object.hasOwn(colorOverrides, region.id)).map((region) => ({ ...region }));
      const painted = options.recolorSvg(result, paintedRegions, { ...colorOverrides }, {
        preserveWhite: true, preserveNone: true, respectNestedRegions: true, paintOnly: true
      });
      if (painted && Array.isArray(painted.missingRegions) && painted.missingRegions.length) {
        throw new Error("Scientific palette paint regions could not be matched: " + painted.missingRegions.join(", "));
      }
      const text = typeof painted === "string" ? painted : painted?.svgText;
      if (typeof text !== "string") throw new Error("Scientific palette paint callback must return SVG text");
      result = text;
    }
    return { svgText: result, regions, paletteId, styleId, colorOverrides };
  }

  return { getPalettes, normalizePalette, paletteRegionOverrides, transformAsset };
});
