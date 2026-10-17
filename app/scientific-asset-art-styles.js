(function attachScientificAssetArtStyles(root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  if (root) root.FigureStudioScientificAssetArtStyles = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function createScientificAssetArtStyles() {
  "use strict";

  const SOFT_COLOR = "soft-color";
  const TECHNICAL_INK = "technical-ink";
  const CUT_PAPER = "cut-paper";
  const STYLE_FOUR = "style-4";

  function normalizeStyle(value) {
    return value === TECHNICAL_INK || value === CUT_PAPER || value === STYLE_FOUR ? value : SOFT_COLOR;
  }

  function technicalInkColor(hex) {
    const value = String(hex || "").toUpperCase();
    if (value === "#FFFFFF") return "#FBFAF6";
    if (value === "#26323D" || value === "#1F2D3A") return "#263039";
    const red = parseInt(value.slice(1, 3), 16) / 255;
    const green = parseInt(value.slice(3, 5), 16) / 255;
    const blue = parseInt(value.slice(5, 7), 16) / 255;
    if (![red, green, blue].every(Number.isFinite)) return value;
    const max = Math.max(red, green, blue);
    const min = Math.min(red, green, blue);
    const chroma = max - min;
    const lightness = (max + min) / 2;
    if (lightness < 0.34) return "#263039";
    if (chroma < 0.09) return lightness > 0.8 ? "#E9E8E1" : "#A9B0AE";
    let hue = 0;
    if (chroma) {
      if (max === red) hue = ((green - blue) / chroma) % 6;
      else if (max === green) hue = (blue - red) / chroma + 2;
      else hue = (red - green) / chroma + 4;
      hue = (hue * 60 + 360) % 360;
    }
    const dark = lightness < 0.69;
    if (hue < 55 || hue >= 345) return dark ? "#A45F4E" : "#DFC8B8";
    if (hue < 155) return dark ? "#5F806D" : "#CEDCCF";
    if (hue < 250) return dark ? "#5A7582" : "#CFD9DB";
    return dark ? "#796C85" : "#DCD6DF";
  }

  function cutPaperColor(hex) {
    const value = String(hex || "").toUpperCase();
    if (value === "#FFFFFF") return "#FFFFFF";
    const red = parseInt(value.slice(1, 3), 16) / 255;
    const green = parseInt(value.slice(3, 5), 16) / 255;
    const blue = parseInt(value.slice(5, 7), 16) / 255;
    if (![red, green, blue].every(Number.isFinite)) return value;
    const max = Math.max(red, green, blue);
    const min = Math.min(red, green, blue);
    const chroma = max - min;
    const lightness = (max + min) / 2;
    if (lightness < 0.34) return "#273747";
    if (chroma < 0.09) return lightness > 0.8 ? "#DBE5E9" : "#879DAC";
    let hue = 0;
    if (chroma) {
      if (max === red) hue = ((green - blue) / chroma) % 6;
      else if (max === green) hue = (blue - red) / chroma + 2;
      else hue = (red - green) / chroma + 4;
      hue = (hue * 60 + 360) % 360;
    }
    const light = lightness > 0.69;
    if (hue < 55 || hue >= 345) return light ? "#F4B18B" : "#D36B56";
    if (hue < 155) return light ? "#A9DEC9" : "#49AA90";
    if (hue < 250) return light ? "#B9DBEE" : "#569BC9";
    return light ? "#D6C6ED" : "#9473C8";
  }

  function transformSvg(svgText, style) {
    const source = String(svgText || "");
    const selected = normalizeStyle(style);
    if (selected === SOFT_COLOR || selected === STYLE_FOUR) return source;
    if (selected === CUT_PAPER) {
      // Make the supplied shapes read as flat color pieces: stronger block color,
      // minimized contour, and square-ended diagram details. Region geometry and
      // identifiers remain editable after insertion into the figure canvas.
      return source
        .replace(/#[0-9a-fA-F]{6}\b/g, cutPaperColor)
        .replace(/<[A-Za-z][^>]*\bdata-region="outline"[^>]*>/g, (element) => element.replace(/\bstroke="#[0-9a-fA-F]{6}"/, 'stroke="#273747"'))
        .replace(/(<g data-region="outline"[^>]*?)stroke="#[0-9a-fA-F]{6}"/, '$1stroke="#273747" opacity="0.25"')
        .replace(/(<g data-region="outline"[^>]*?)stroke-width="[0-9]+(?:\.[0-9]+)?"/, '$1stroke-width="1.2"')
        .replace(/stroke-linecap="round"/g, 'stroke-linecap="square"')
        .replace(/stroke-linejoin="round"/g, 'stroke-linejoin="bevel"');
    }
    // Bundled scientific SVGs use explicit six-digit colors and stroke widths.
    // This preserves paths, labels, semantic regions, and viewBox geometry.
    return source
      .replace(/#[0-9a-fA-F]{6}\b/g, technicalInkColor)
      .replace(/stroke-width="([0-9]+(?:\.[0-9]+)?)"/g, (_match, width) => {
        const value = Math.max(1.4, Math.min(3.2, Number(width) * 0.68));
        return `stroke-width="${Number(value.toFixed(2))}"`;
      })
      .replace(/stroke-linecap="round"/g, 'stroke-linecap="square"')
      .replace(/stroke-linejoin="round"/g, 'stroke-linejoin="miter"');
  }

  function transformRegions(regions, style) {
    const selected = normalizeStyle(style);
    if (selected === SOFT_COLOR || selected === STYLE_FOUR) return (regions || []).map((region) => ({ ...region }));
    return (regions || []).map((region) => ({
      ...region,
      default: /^#[0-9a-fA-F]{6}$/.test(String(region.default || ""))
        ? (selected === CUT_PAPER
          ? (region.id === "outline" && region.paint !== "fill" ? "#273747" : cutPaperColor(region.default))
          : technicalInkColor(region.default))
        : region.default
    }));
  }

  function relativeSvgPath(value) {
    const path = String(value || "");
    if (!path || /[\\?#:]/.test(path) || path.startsWith("/")
      || path.split("/").some((part) => !part || part === "." || part === "..")
      || !path.endsWith(".svg")) throw new Error("Invalid scientific style SVG path");
    return path;
  }

  function attachVariantManifest(assets, manifest, options = {}) {
    if (manifest?.id !== STYLE_FOUR || manifest.schema_version !== "1.0.0") {
      throw new Error("Unsupported scientific drawing style manifest");
    }
    const byId = new Map((assets || []).map((asset) => [asset.id, asset]));
    const variants = Array.isArray(manifest.assets) ? manifest.assets : [];
    const seen = new Set();
    // Validate the complete mapping before attaching anything. A partial or
    // mismatched source must never quietly display Style 1 under Style 4.
    const prepared = variants.map((variant) => {
      const asset = byId.get(variant?.asset_id);
      if (!asset || seen.has(asset.id)) throw new Error("Unknown or duplicate scientific style drawing");
      seen.add(asset.id);
      const file = relativeSvgPath(variant.file);
      const regions = variant.editable_color_regions;
      const expected = (asset.editable_color_regions || []).map((region) => region.id).sort();
      if (!Array.isArray(regions) || JSON.stringify(regions.map((region) => region.id).sort()) !== JSON.stringify(expected)
        || !/^[a-f0-9]{64}$/.test(variant.sha256 || "")) {
        throw new Error("Scientific style regions or source identity do not match the drawing");
      }
      const svgUrl = new URL(file, options.baseUrl);
      svgUrl.searchParams.set("v", variant.sha256);
      return [asset, { ...variant, _svgUrl: svgUrl.toString(),
        _resourcePath: `${options.basePath || ""}${file}` }];
    });
    if (seen.size !== byId.size) throw new Error("Scientific drawing style coverage is incomplete");
    prepared.forEach(([asset, variant]) => {
      asset.art_styles = { ...(asset.art_styles || {}), [STYLE_FOUR]: variant };
    });
    return assets;
  }

  function assetForStyle(asset, style) {
    const selected = normalizeStyle(style);
    if (selected === SOFT_COLOR) return asset;
    if (selected === STYLE_FOUR) {
      const variant = asset?.art_styles?.[STYLE_FOUR];
      if (!variant?._svgUrl || !variant._resourcePath) throw new Error("Style 4 is unavailable for this drawing");
      return { ...asset, file: variant._resourcePath, _svgUrl: variant._svgUrl, _packAssetPath: "",
        style_family: "superbench-style-4-v1", art_style: STYLE_FOUR,
        art_style_source_sha256: variant.sha256,
        editable_color_regions: transformRegions(variant.editable_color_regions, STYLE_FOUR) };
    }
    return { ...asset, style_family: `superbench-${selected}-v1`, art_style: selected,
      editable_color_regions: transformRegions(asset.editable_color_regions, selected) };
  }

  return { SOFT_COLOR, TECHNICAL_INK, CUT_PAPER, STYLE_FOUR, normalizeStyle, technicalInkColor, cutPaperColor,
    transformSvg, transformRegions, attachVariantManifest, assetForStyle };
});
