#!/usr/bin/env python3
"""Local Figure Tool development server and native PDF compiler.

PDF page preview and source-backed placement run in the browser through PDF.js.
This server provides the bounded QPDF-backed inspection and mutation operations
that require native object access, plus the local desktop web surface.
"""

from __future__ import annotations

import argparse
import base64
from datetime import datetime, timezone
import hashlib
import hmac
from http.cookies import CookieError, SimpleCookie
from io import BytesIO
import json
import math
import mimetypes
import os
from pathlib import Path
import re
import sys
import threading
import xml.etree.ElementTree as ET
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse


FIGURE_STUDIO_VERSION = "1.0.0-beta.6"
MAX_UPLOAD_BYTES = 50 * 1024 * 1024
MAX_NATIVE_PDF_DESCRIPTORS = 240
MAX_NATIVE_PDF_RESOURCE_ROWS = 80
MAX_NATIVE_PDF_OPERATOR_RUNS = 96
MAX_NATIVE_PDF_RESOURCE_SCOPES = 128
MAX_NATIVE_PDF_FORM_INVOCATIONS = 512
MAX_NATIVE_PDF_RESOURCE_USAGES = 2048
MAX_NATIVE_PDF_FORM_DEPTH = 8
MAX_NATIVE_PDF_PATH_ITEMS = 24
MAX_NATIVE_PDF_MUTATION_DESCRIPTORS = 12
MAX_NATIVE_PDF_MUTATION_PATH_COMMANDS = 96
MAX_TEXT_OUTLINE_JSON_BYTES = 24 * 1024 * 1024
MAX_TEXT_OUTLINE_CHARACTERS = 1024
MAX_PDF_FONT_REQUESTS = 96
MAX_PDF_FONT_PROGRAM_BYTES = 16 * 1024 * 1024

SUPPORTED_NATIVE_PDF_CONTENT_STREAM_DESCRIPTOR_TYPES = {
    "annotation_rectangle_overlay",
    "object_tree_mutation",
    "path_overlay",
    "path_boolean_operation",
    "path_anchor_edit",
    "path_control_handle_edit",
}
SUPPORTED_NATIVE_PDF_RESOURCE_REWRITE_DESCRIPTOR_TYPES = {
    "advanced_feature_graph_edit",
    "gradient_stop_edit",
    "gradient_mesh_pattern_edit",
}


def resolve_text_outline_font_path(font_family: str, font_weight: str, font_style: str) -> Path:
    fonts_dir = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"
    family = re.sub(r"[^a-z0-9]+", " ", str(font_family or "").lower()).strip()
    bold = str(font_weight or "").lower() in {"bold", "600", "700", "800", "900"}
    italic = str(font_style or "").lower() in {"italic", "oblique"}
    if "courier" in family:
        names = {("normal", False): "cour.ttf", ("normal", True): "courbd.ttf", ("italic", False): "couri.ttf", ("italic", True): "courbi.ttf"}
    elif "times" in family:
        names = {("normal", False): "times.ttf", ("normal", True): "timesbd.ttf", ("italic", False): "timesi.ttf", ("italic", True): "timesbi.ttf"}
    elif "georgia" in family:
        names = {("normal", False): "georgia.ttf", ("normal", True): "georgiab.ttf", ("italic", False): "georgiai.ttf", ("italic", True): "georgiaz.ttf"}
    else:
        names = {("normal", False): "arial.ttf", ("normal", True): "arialbd.ttf", ("italic", False): "ariali.ttf", ("italic", True): "arialbi.ttf"}
    path = fonts_dir / names[("italic" if italic else "normal", bold)]
    if not path.is_file():
        fallback = fonts_dir / "arial.ttf"
        if fallback.is_file():
            return fallback
        raise RuntimeError("A supported local font file was not found for text outlining.")
    return path


def build_text_glyph_outline_payload(payload: dict[str, object]) -> dict[str, object]:
    try:
        from fontTools.pens.boundsPen import BoundsPen
        from fontTools.pens.svgPathPen import SVGPathPen
        from fontTools.pens.transformPen import TransformPen
        from fontTools.ttLib import TTFont
    except ImportError as error:
        raise RuntimeError("fontTools is required for reversible text outlines. Install requirements-pdf.txt.") from error

    raw_characters = str(payload.get("characters") or "")
    characters = "".join(dict.fromkeys(raw_characters))
    if not characters:
        raise ValueError("At least one character is required for text outlining.")
    if len(characters) > MAX_TEXT_OUTLINE_CHARACTERS:
        raise ValueError(f"Text outline request exceeds the {MAX_TEXT_OUTLINE_CHARACTERS} character limit.")

    font_base64 = str(payload.get("font_base64") or payload.get("fontBase64") or "").strip()
    font_source = ""
    if font_base64:
        try:
            font_bytes = base64.b64decode(font_base64, validate=True)
        except Exception as error:  # noqa: BLE001 - friendly API error
            raise ValueError("The retained source-font program is not valid base64.") from error
        if len(font_bytes) > MAX_PDF_FONT_PROGRAM_BYTES:
            raise ValueError("The retained source-font program exceeds the outline conversion limit.")
        font_input: BytesIO | str = BytesIO(font_bytes)
        font_source = "retained-source-font"
    else:
        font_path = resolve_text_outline_font_path(
            str(payload.get("font_family") or payload.get("fontFamily") or "Arial"),
            str(payload.get("font_weight") or payload.get("fontWeight") or "400"),
            str(payload.get("font_style") or payload.get("fontStyle") or "normal"),
        )
        font_input = str(font_path)
        font_source = font_path.name

    font = TTFont(font_input, lazy=False, recalcBBoxes=False, recalcTimestamp=False)
    try:
        glyph_set = font.getGlyphSet()
        cmap = font.getBestCmap() or {}
        units_per_em = int(font["head"].unitsPerEm)
        hhea = font.get("hhea")
        ascender = int(getattr(hhea, "ascent", units_per_em))
        descender = int(getattr(hhea, "descent", 0))
        glyphs: dict[str, object] = {}
        unsupported: list[str] = []
        for character in characters:
            glyph_name = cmap.get(ord(character))
            if not glyph_name or glyph_name not in glyph_set:
                unsupported.append(f"U+{ord(character):04X}")
                continue
            glyph = glyph_set[glyph_name]
            svg_pen = SVGPathPen(glyph_set)
            glyph.draw(TransformPen(svg_pen, (1, 0, 0, -1, 0, 0)))
            bounds_pen = BoundsPen(glyph_set)
            glyph.draw(TransformPen(bounds_pen, (1, 0, 0, -1, 0, 0)))
            bounds = list(bounds_pen.bounds) if bounds_pen.bounds else [0, 0, 0, 0]
            glyphs[character] = {
                "glyph_name": glyph_name,
                "path": svg_pen.getCommands(),
                "bounds": bounds,
                "advance": float(getattr(glyph, "width", 0) or 0),
            }
        return {
            "schema": "figureStudio.textGlyphOutlines.v1",
            "ok": True,
            "font_source": font_source,
            "units_per_em": units_per_em,
            "ascender": ascender,
            "descender": descender,
            "glyphs": glyphs,
            "unsupported": unsupported,
            "native_pdf_text_stream_mutated": False,
            "native_equivalence": False,
        }
    finally:
        font.close()

PDF_BLEND_MODE_NAMES = {
    "Normal",
    "Compatible",
    "Multiply",
    "Screen",
    "Overlay",
    "Darken",
    "Lighten",
    "ColorDodge",
    "ColorBurn",
    "HardLight",
    "SoftLight",
    "Difference",
    "Exclusion",
    "Hue",
    "Saturation",
    "Color",
    "Luminosity",
}
PDF_BLEND_MODE_LOOKUP = {
    re.sub(r"[^a-z0-9]+", "", name.lower()): name
    for name in PDF_BLEND_MODE_NAMES
}

PDF_CONTENT_STREAM_OPERATOR_CATEGORIES = {
    "q": "graphics_state",
    "Q": "graphics_state",
    "cm": "graphics_state",
    "w": "graphics_state",
    "J": "graphics_state",
    "j": "graphics_state",
    "M": "graphics_state",
    "d": "graphics_state",
    "ri": "graphics_state",
    "i": "graphics_state",
    "gs": "graphics_state",
    "CS": "color",
    "cs": "color",
    "SC": "color",
    "SCN": "color",
    "sc": "color",
    "scn": "color",
    "G": "color",
    "g": "color",
    "RG": "color",
    "rg": "color",
    "K": "color",
    "k": "color",
    "m": "path",
    "l": "path",
    "c": "path",
    "v": "path",
    "y": "path",
    "h": "path",
    "re": "path",
    "S": "paint",
    "s": "paint",
    "f": "paint",
    "F": "paint",
    "f*": "paint",
    "B": "paint",
    "B*": "paint",
    "b": "paint",
    "b*": "paint",
    "n": "paint",
    "W": "clip",
    "W*": "clip",
    "BT": "text",
    "ET": "text",
    "Tf": "text",
    "Td": "text",
    "TD": "text",
    "Tm": "text",
    "T*": "text",
    "Tj": "text",
    "TJ": "text",
    "'": "text",
    '"': "text",
    "Tr": "text",
    "Tc": "text",
    "Tw": "text",
    "Tz": "text",
    "TL": "text",
    "Ts": "text",
    "sh": "shading",
    "Do": "image",
    "BI": "image",
    "ID": "image",
    "EI": "image",
    "BMC": "marked_content",
    "BDC": "marked_content",
    "EMC": "marked_content",
    "MP": "marked_content",
    "DP": "marked_content",
}

PDF_PAINT_OPERATOR_TOKENS = {"S", "s", "f", "F", "f*", "B", "B*", "b", "b*"}
PDF_DEVICE_COLOR_OPERATOR_COMPONENTS = {
    "g": 1,
    "G": 1,
    "rg": 3,
    "RG": 3,
    "k": 4,
    "K": 4,
}
PDF_DEVICE_COLOR_OPERATOR_SPACES = {
    "g": "DeviceGray",
    "G": "DeviceGray",
    "rg": "DeviceRGB",
    "RG": "DeviceRGB",
    "k": "DeviceCMYK",
    "K": "DeviceCMYK",
}
PDF_DEVICE_COLOR_OPERATOR_TOKENS = set(PDF_DEVICE_COLOR_OPERATOR_COMPONENTS)
PDF_RGB_COLOR_OPERATOR_TOKENS = {"rg", "RG"}
PDF_STROKE_WIDTH_OPERATOR_TOKENS = {"w"}
PDF_STROKE_STYLE_OPERATOR_PROPERTIES = {
    "w": "width",
    "d": "dash",
    "J": "cap",
    "j": "join",
    "M": "miter_limit",
}
PDF_PATH_GEOMETRY_OPERATOR_TOKENS = {"m", "l", "c", "v", "y", "re"}
PDF_NATIVE_RESOURCE_CATEGORIES = {
    "ExtGState": "extgstate",
    "Font": "font",
    "ColorSpace": "colorspace",
    "Shading": "shading",
    "Pattern": "pattern",
    "XObject": "xobject",
}
PDF_NATIVE_RESOURCE_USAGE_OPERATORS = {
    "gs": "extgstate",
    "Tf": "font",
    "cs": "colorspace",
    "CS": "colorspace",
    "sh": "shading",
    "Do": "xobject",
    "scn": "pattern",
    "SCN": "pattern",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Serve Figure Tool and its native PDF compiler.")
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Project root to serve")
    parser.add_argument("--bind", default="127.0.0.1", help="Bind host")
    parser.add_argument("--port", type=int, default=4173, help="Port")
    parser.add_argument(
        "--desktop-sidecar",
        action="store_true",
        help="Use the authenticated Figure Tool desktop host protocol.",
    )
    parser.add_argument(
        "--payload-manifest-sha256",
        default="",
        help="Host-verified payload manifest digest required by desktop-sidecar mode.",
    )
    parser.add_argument(
        "--runtime-proof",
        action="store_true",
        help="Run one native PDF parse/render proof transaction and exit.",
    )
    return parser.parse_args()


def count_svg_elements(svg: str) -> dict[str, int]:
    return {
        "text_count": len(re.findall(r"<(?:[a-zA-Z0-9_-]+:)?text\b", svg)),
        "path_count": len(re.findall(r"<(?:[a-zA-Z0-9_-]+:)?path\b", svg)),
        "image_count": len(re.findall(r"<(?:[a-zA-Z0-9_-]+:)?image\b", svg)),
    }


SVG_NAMESPACE = "http://www.w3.org/2000/svg"
SVG_GRAPHIC_TAGS = {"path", "text", "line", "polyline", "polygon", "rect", "circle", "ellipse", "image"}
SVG_IDENTITY_MATRIX = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)


def svg_local_name(element: ET.Element) -> str:
    return str(element.tag).rsplit("}", 1)[-1].lower()


def svg_affine_compose(parent: tuple[float, ...], local: tuple[float, ...]) -> tuple[float, ...]:
    pa, pb, pc, pd, pe, pf = parent
    la, lb, lc, ld, le, lf = local
    return (
        pa * la + pc * lb,
        pb * la + pd * lb,
        pa * lc + pc * ld,
        pb * lc + pd * ld,
        pa * le + pc * lf + pe,
        pb * le + pd * lf + pf,
    )


def svg_transform_matrix(value: str | None) -> tuple[float, ...]:
    matrix = SVG_IDENTITY_MATRIX
    for name, raw_values in re.findall(r"([A-Za-z]+)\s*\(([^)]*)\)", value or ""):
        values = [finite_number(item) for item in re.findall(r"[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?", raw_values)]
        operation = SVG_IDENTITY_MATRIX
        lowered = name.lower()
        if lowered == "matrix" and len(values) >= 6:
            operation = tuple(values[:6])
        elif lowered == "translate" and values:
            operation = (1.0, 0.0, 0.0, 1.0, values[0], values[1] if len(values) > 1 else 0.0)
        elif lowered == "scale" and values:
            operation = (values[0], 0.0, 0.0, values[1] if len(values) > 1 else values[0], 0.0, 0.0)
        elif lowered == "rotate" and values:
            radians = math.radians(values[0])
            cosine = math.cos(radians)
            sine = math.sin(radians)
            rotation = (cosine, sine, -sine, cosine, 0.0, 0.0)
            if len(values) >= 3:
                cx, cy = values[1], values[2]
                operation = svg_affine_compose(
                    svg_affine_compose((1.0, 0.0, 0.0, 1.0, cx, cy), rotation),
                    (1.0, 0.0, 0.0, 1.0, -cx, -cy),
                )
            else:
                operation = rotation
        elif lowered == "skewx" and values:
            operation = (1.0, 0.0, math.tan(math.radians(values[0])), 1.0, 0.0, 0.0)
        elif lowered == "skewy" and values:
            operation = (1.0, math.tan(math.radians(values[0])), 0.0, 1.0, 0.0, 0.0)
        matrix = svg_affine_compose(matrix, operation)
    return matrix


def svg_element_matrix(element: ET.Element, parents: dict[ET.Element, ET.Element]) -> tuple[float, ...]:
    chain: list[ET.Element] = []
    cursor: ET.Element | None = element
    while cursor is not None:
        chain.append(cursor)
        cursor = parents.get(cursor)
    matrix = SVG_IDENTITY_MATRIX
    for row in reversed(chain):
        matrix = svg_affine_compose(matrix, svg_transform_matrix(row.get("transform")))
    return matrix


def svg_transform_point(matrix: tuple[float, ...], x: float, y: float) -> tuple[float, float]:
    a, b, c, d, e, f = matrix
    return (a * x + c * y + e, b * x + d * y + f)


def svg_points_bounds(points: list[tuple[float, float]], matrix: tuple[float, ...]) -> tuple[float, float, float, float] | None:
    if not points:
        return None
    transformed = [svg_transform_point(matrix, x, y) for x, y in points]
    xs = [point[0] for point in transformed]
    ys = [point[1] for point in transformed]
    return (min(xs), min(ys), max(xs), max(ys))


def svg_numeric_attribute(element: ET.Element, name: str, default: float = 0.0) -> float:
    match = re.search(r"[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?", str(element.get(name) or ""))
    return finite_number(match.group(0), default) if match else default


def svg_path_bounds(path_data: str, matrix: tuple[float, ...]) -> tuple[float, float, float, float] | None:
    if not path_data:
        return None
    try:
        from fontTools.pens.boundsPen import BoundsPen  # type: ignore
        from fontTools.pens.transformPen import TransformPen  # type: ignore
        from fontTools.svgLib.path import parse_path  # type: ignore

        bounds_pen = BoundsPen(None)
        parse_path(path_data, TransformPen(bounds_pen, matrix))
        return tuple(float(value) for value in bounds_pen.bounds) if bounds_pen.bounds else None
    except (ImportError, ValueError, TypeError):
        return None


def svg_element_analytic_bounds(
    element: ET.Element,
    matrix: tuple[float, ...],
) -> tuple[tuple[float, float, float, float] | None, str]:
    tag = svg_local_name(element)
    if tag == "path":
        return svg_path_bounds(str(element.get("d") or ""), matrix), "fonttools-transformed-path"
    if tag == "line":
        return svg_points_bounds([
            (svg_numeric_attribute(element, "x1"), svg_numeric_attribute(element, "y1")),
            (svg_numeric_attribute(element, "x2"), svg_numeric_attribute(element, "y2")),
        ], matrix), "analytic-line"
    if tag in {"polyline", "polygon"}:
        values = [finite_number(item) for item in re.findall(r"[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?", str(element.get("points") or ""))]
        return svg_points_bounds([(values[index], values[index + 1]) for index in range(0, len(values) - 1, 2)], matrix), "analytic-points"
    if tag in {"rect", "image"}:
        x = svg_numeric_attribute(element, "x")
        y = svg_numeric_attribute(element, "y")
        width = max(0.0, svg_numeric_attribute(element, "width"))
        height = max(0.0, svg_numeric_attribute(element, "height"))
        return svg_points_bounds([(x, y), (x + width, y), (x + width, y + height), (x, y + height)], matrix), "analytic-rect"
    if tag in {"circle", "ellipse"}:
        cx = svg_numeric_attribute(element, "cx")
        cy = svg_numeric_attribute(element, "cy")
        rx = max(0.0, svg_numeric_attribute(element, "r" if tag == "circle" else "rx"))
        ry = rx if tag == "circle" else max(0.0, svg_numeric_attribute(element, "ry"))
        a, b, c, d, e, f = matrix
        center_x, center_y = svg_transform_point(matrix, cx, cy)
        extent_x = math.hypot(a * rx, c * ry)
        extent_y = math.hypot(b * rx, d * ry)
        return (center_x - extent_x, center_y - extent_y, center_x + extent_x, center_y + extent_y), "analytic-ellipse"
    return None, ""


def svg_bbox_from_descriptor(descriptor: dict[str, object] | None) -> tuple[float, float, float, float] | None:
    bbox = descriptor.get("bbox") if isinstance(descriptor, dict) else None
    if not isinstance(bbox, dict):
        return None
    return (
        finite_number(bbox.get("x0")),
        finite_number(bbox.get("y0")),
        finite_number(bbox.get("x1")),
        finite_number(bbox.get("y1")),
    )


def svg_bounds_attribute(bounds: tuple[float, float, float, float]) -> str:
    x0, y0, x1, y1 = bounds
    return ",".join(f"{value:.5f}".rstrip("0").rstrip(".") for value in (x0, y0, max(0.0, x1 - x0), max(0.0, y1 - y0)))


def svg_url_reference_ids(value: object) -> list[str]:
    return [
        match.group(1)
        for match in re.finditer(r"url\(\s*['\"]?#([^'\")\s]+)['\"]?\s*\)", str(value or ""), re.IGNORECASE)
    ]


def svg_ancestor_feature_memberships(element: ET.Element, parents: dict[ET.Element, ET.Element]) -> dict[str, list[str]]:
    memberships = {"clip_path": [], "mask": [], "filter": [], "blend_mode": []}
    cursor: ET.Element | None = element
    while cursor is not None:
        style = str(cursor.get("style") or "")
        style_values = {
            key.lower(): value.strip()
            for key, value in (
                part.split(":", 1)
                for part in style.split(";")
                if ":" in part
            )
        }
        for feature, attribute in (("clip_path", "clip-path"), ("mask", "mask"), ("filter", "filter")):
            value = cursor.get(attribute) or style_values.get(attribute) or ""
            for reference in svg_url_reference_ids(value):
                if reference not in memberships[feature]:
                    memberships[feature].append(reference)
        blend = cursor.get("mix-blend-mode") or style_values.get("mix-blend-mode") or ""
        if blend and str(blend).strip().lower() != "normal" and str(blend).strip() not in memberships["blend_mode"]:
            memberships["blend_mode"].append(str(blend).strip())
        cursor = parents.get(cursor)
    return memberships


def annotate_pdf_svg_edit_index(
    svg: str,
    page_number: int,
    native_tree: dict[str, object],
) -> tuple[str, dict[str, object]]:
    try:
        root = ET.fromstring(svg)
    except ET.ParseError:
        return svg, {
            "schema": "figureStudio.pdfSvgEditIndex.v3",
            "status": "parse-failed",
            "full_native_equivalence": False,
        }
    ET.register_namespace("", SVG_NAMESPACE)
    ET.register_namespace("xlink", "http://www.w3.org/1999/xlink")
    ET.register_namespace("inkscape", "http://www.inkscape.org/namespaces/inkscape")
    parents = {child: parent for parent in root.iter() for child in parent}

    def in_definitions(element: ET.Element) -> bool:
        cursor = parents.get(element)
        while cursor is not None:
            if svg_local_name(cursor) in {"defs", "clippath", "mask", "pattern", "symbol"}:
                return True
            cursor = parents.get(cursor)
        return False

    descriptors = native_tree.get("descriptors") if isinstance(native_tree, dict) else []
    descriptors = descriptors if isinstance(descriptors, list) else []
    resources = native_tree.get("resources") if isinstance(native_tree, dict) else {}
    resources = resources if isinstance(resources, dict) else {}
    pattern_resources = [row for row in resources.get("patterns", []) if isinstance(row, dict)]
    svg_pattern_elements = [element for element in root.iter() if svg_local_name(element) == "pattern"]
    svg_pattern_resources: dict[str, dict[str, object]] = {}
    if pattern_resources and len(svg_pattern_elements) == len(pattern_resources):
        for element, resource in zip(svg_pattern_elements, pattern_resources):
            svg_pattern_id = str(element.get("id") or "")
            if svg_pattern_id:
                svg_pattern_resources[svg_pattern_id] = resource
    drawing_descriptors = [row for row in descriptors if isinstance(row, dict) and row.get("native_kind") == "path"]
    text_descriptors = [row for row in descriptors if isinstance(row, dict) and row.get("native_kind") == "text"]
    image_descriptors = [row for row in descriptors if isinstance(row, dict) and row.get("native_kind") == "image"]
    graphics = [element for element in root.iter() if svg_local_name(element) in SVG_GRAPHIC_TAGS and not in_definitions(element)]
    text_index = 0
    image_index = 0
    digest_occurrences: dict[str, int] = {}
    descriptor_parts: dict[str, int] = {}
    counts = {
        "path": 0,
        "text": 0,
        "image": 0,
        "shape": 0,
        "indexed": 0,
        "exact_bounds": 0,
        "native_links": 0,
        "native_resource_links": 0,
        "form_xobject_members": 0,
        "nested_form_xobject_members": 0,
        "shared_form_xobject_members": 0,
        "clip_members": 0,
        "mask_members": 0,
        "filter_members": 0,
        "blend_members": 0,
        "represented_svg_clip_members": 0,
        "represented_svg_mask_members": 0,
        "native_clip_members": 0,
        "native_mask_members": 0,
        "native_gradient_members": 0,
        "native_pattern_members": 0,
    }

    for sequence, element in enumerate(graphics):
        tag = svg_local_name(element)
        counts[tag if tag in {"path", "text", "image"} else "shape"] += 1
        matrix = svg_element_matrix(element, parents)
        bounds, bounds_source = svg_element_analytic_bounds(element, matrix)
        descriptor: dict[str, object] | None = None
        if tag == "text" and text_index < len(text_descriptors):
            descriptor = text_descriptors[text_index]
            text_index += 1
            bounds = svg_bbox_from_descriptor(descriptor) or bounds
            bounds_source = "native-text-span"
        elif tag == "image" and image_index < len(image_descriptors):
            descriptor = image_descriptors[image_index]
            image_index += 1
            bounds = svg_bbox_from_descriptor(descriptor) or bounds
            bounds_source = "native-image-block"
        elif tag == "path" and bounds and drawing_descriptors:
            candidates = [(max(abs(left - right) for left, right in zip(bounds, svg_bbox_from_descriptor(row) or bounds)), row) for row in drawing_descriptors]
            distance, candidate = min(candidates, key=lambda row: row[0])
            span = max(1.0, bounds[2] - bounds[0], bounds[3] - bounds[1])
            if distance <= max(0.25, span * 0.01):
                descriptor = candidate

        native_id = str((descriptor or {}).get("stable_object_id") or (descriptor or {}).get("id") or "")
        if native_id:
            part = descriptor_parts.get(native_id, 0) + 1
            descriptor_parts[native_id] = part
            source_id = native_id if part == 1 else f"{native_id}-svg-part-{part}"
            counts["native_links"] += 1
            element.set("data-figure-studio-native-descriptor-id", native_id)
            link_status = str((descriptor or {}).get("membership_status") or ("ordered-native-span" if tag in {"text", "image"} else "bounds-consensus"))
            element.set("data-figure-studio-native-link-status", link_status)
        else:
            stable_attributes = {
                key: value
                for key, value in sorted(element.attrib.items())
                if not key.startswith("data-figure-studio-") and key != "id"
            }
            digest = hashlib.sha256(json.dumps({"tag": tag, "attributes": stable_attributes}, sort_keys=True).encode("utf-8")).hexdigest()[:16]
            occurrence = digest_occurrences.get(digest, 0) + 1
            digest_occurrences[digest] = occurrence
            source_id = f"pdf-p{page_number}-svg-{tag}-{digest}-{occurrence}"
        owner_scope = str((descriptor or {}).get("content_stream_scope") or "")
        owner_xobject_id = str((descriptor or {}).get("owner_xobject_id") or "")
        owner_xobject_xref = int(finite_number((descriptor or {}).get("owner_xobject_xref"), 0))
        owner_xobject_name = str((descriptor or {}).get("owner_xobject_name") or "")
        owner_xobject_invocation_id = str((descriptor or {}).get("owner_xobject_invocation_id") or "")
        owner_xobject_invocation_path = str((descriptor or {}).get("owner_xobject_invocation_path") or "")
        owner_xobject_parent_invocation_id = str((descriptor or {}).get("owner_xobject_parent_invocation_id") or "")
        owner_xobject_nesting_depth = int(finite_number((descriptor or {}).get("owner_xobject_nesting_depth"), 0))
        owner_xobject_invocation_ordinal = int(finite_number((descriptor or {}).get("owner_xobject_invocation_ordinal"), 0))
        owner_xobject_resource_scope_id = str((descriptor or {}).get("owner_xobject_resource_scope_id") or "")
        owner_xobject_resource_owner_xref = int(finite_number((descriptor or {}).get("owner_xobject_resource_owner_xref"), 0))
        owner_xobject_shared_definition = bool((descriptor or {}).get("owner_xobject_shared_definition"))
        per_instance_native_write_supported = bool((descriptor or {}).get("per_instance_native_write_supported", True))
        owner_xobject_invocation_ctm = [
            finite_number(value) for value in (descriptor or {}).get("owner_xobject_invocation_ctm", [])
        ]
        if owner_scope:
            element.set("data-figure-studio-native-content-stream-scope", owner_scope)
        if owner_xobject_id:
            element.set("data-figure-studio-native-owner-xobject-id", owner_xobject_id)
            element.set("data-figure-studio-native-owner-xobject-xref", str(owner_xobject_xref))
            if owner_xobject_name:
                element.set("data-figure-studio-native-owner-xobject-name", owner_xobject_name)
            if owner_xobject_invocation_id:
                element.set("data-figure-studio-native-owner-xobject-invocation-id", owner_xobject_invocation_id)
            if owner_xobject_invocation_path:
                element.set("data-figure-studio-native-owner-xobject-invocation-path", owner_xobject_invocation_path)
            if owner_xobject_parent_invocation_id:
                element.set("data-figure-studio-native-owner-xobject-parent-invocation-id", owner_xobject_parent_invocation_id)
            if owner_xobject_nesting_depth:
                element.set("data-figure-studio-native-owner-xobject-nesting-depth", str(owner_xobject_nesting_depth))
            if owner_xobject_invocation_ordinal:
                element.set("data-figure-studio-native-owner-xobject-invocation", str(owner_xobject_invocation_ordinal))
            if owner_xobject_resource_scope_id:
                element.set("data-figure-studio-native-owner-resource-scope-id", owner_xobject_resource_scope_id)
            if owner_xobject_resource_owner_xref:
                element.set("data-figure-studio-native-owner-resource-xref", str(owner_xobject_resource_owner_xref))
            element.set("data-figure-studio-native-owner-shared-definition", "true" if owner_xobject_shared_definition else "false")
            element.set("data-figure-studio-native-owner-per-instance-write", "true" if per_instance_native_write_supported else "false")
            if len(owner_xobject_invocation_ctm) >= 6:
                element.set(
                    "data-figure-studio-native-owner-xobject-ctm",
                    ",".join(f"{value:.6g}" for value in owner_xobject_invocation_ctm[:6]),
                )
            counts["form_xobject_members"] += 1
            counts["nested_form_xobject_members"] += int(owner_xobject_nesting_depth > 1)
            counts["shared_form_xobject_members"] += int(owner_xobject_shared_definition)
        svg_memberships = svg_ancestor_feature_memberships(element, parents)
        native_clip_memberships = [str(value) for value in (descriptor or {}).get("clip_memberships", []) if value]
        native_mask_memberships = [str(value) for value in (descriptor or {}).get("mask_memberships", []) if value]
        native_extgstate_memberships = [str(value) for value in (descriptor or {}).get("extgstate_memberships", []) if value]
        native_blend_memberships = [str(value) for value in (descriptor or {}).get("blend_memberships", []) if value]
        native_shading_memberships = [str(value) for value in (descriptor or {}).get("shading_memberships", []) if value]
        native_shading_usage_ids = [str(value) for value in (descriptor or {}).get("shading_usage_ids", []) if value]
        style = str(element.get("style") or "")
        style_values = {
            key.lower(): value.strip()
            for key, value in (
                part.split(":", 1)
                for part in style.split(";")
                if ":" in part
            )
        }
        svg_pattern_ids = list(dict.fromkeys([
            *svg_url_reference_ids(element.get("fill") or style_values.get("fill") or ""),
            *svg_url_reference_ids(element.get("stroke") or style_values.get("stroke") or ""),
        ]))
        matched_pattern_resources = [
            svg_pattern_resources[pattern_id]
            for pattern_id in svg_pattern_ids
            if pattern_id in svg_pattern_resources
        ]
        native_pattern_memberships = [
            str(row.get("id") or row.get("binding_id") or "")
            for row in matched_pattern_resources
            if row.get("id") or row.get("binding_id")
        ]
        native_pattern_usage_ids = list(dict.fromkeys([
            str(value)
            for row in matched_pattern_resources
            for value in row.get("resource_usage_ids", [])
            if value
        ]))
        native_pattern = matched_pattern_resources[0] if len(matched_pattern_resources) == 1 else {}
        counts["represented_svg_clip_members"] += int(bool(svg_memberships["clip_path"]))
        counts["represented_svg_mask_members"] += int(bool(svg_memberships["mask"]))
        counts["native_clip_members"] += int(bool(native_clip_memberships))
        counts["native_mask_members"] += int(bool(native_mask_memberships))
        feature_types = [feature for feature, values in svg_memberships.items() if values]
        if native_clip_memberships and "clip_path" not in feature_types:
            feature_types.append("clip_path")
        if native_mask_memberships and "mask" not in feature_types:
            feature_types.append("mask")
        if (native_extgstate_memberships or native_blend_memberships) and "blend_mode" not in feature_types:
            feature_types.append("blend_mode")
        if native_shading_memberships and "gradient" not in feature_types:
            feature_types.append("gradient")
        if native_pattern_memberships and "pattern" not in feature_types:
            feature_types.append("pattern")
        for attribute, values in (
            ("data-figure-studio-svg-clip-membership-ids", svg_memberships["clip_path"]),
            ("data-figure-studio-svg-mask-membership-ids", svg_memberships["mask"]),
            ("data-figure-studio-svg-filter-membership-ids", svg_memberships["filter"]),
            ("data-figure-studio-native-clip-membership-ids", native_clip_memberships),
            ("data-figure-studio-native-mask-membership-ids", native_mask_memberships),
            ("data-figure-studio-native-extgstate-membership-ids", native_extgstate_memberships),
            ("data-figure-studio-native-blend-membership-ids", native_blend_memberships),
            ("data-figure-studio-native-shading-membership-ids", native_shading_memberships),
            ("data-figure-studio-native-shading-usage-ids", native_shading_usage_ids),
            ("data-figure-studio-native-pattern-membership-ids", native_pattern_memberships),
            ("data-figure-studio-native-pattern-usage-ids", native_pattern_usage_ids),
        ):
            if values:
                element.set(attribute, ",".join(values))
        for attribute, value in (
            ("data-figure-studio-native-shading-binding-id", (descriptor or {}).get("shading_binding_id")),
            ("data-figure-studio-native-shading-resource-name", (descriptor or {}).get("shading_resource_name")),
            ("data-figure-studio-native-shading-xref", (descriptor or {}).get("shading_xref")),
            ("data-figure-studio-native-shading-function-xref", (descriptor or {}).get("shading_function_xref")),
            ("data-figure-studio-native-shading-operator-index", (descriptor or {}).get("shading_operator_index")),
            ("data-figure-studio-native-shading-operator-byte-offset", (descriptor or {}).get("shading_operator_byte_offset")),
            ("data-figure-studio-native-pattern-binding-id", native_pattern.get("binding_id") or native_pattern.get("id")),
            ("data-figure-studio-native-pattern-resource-name", native_pattern.get("resource_name")),
            ("data-figure-studio-native-pattern-xref", native_pattern.get("xref")),
            ("data-figure-studio-native-pattern-type", native_pattern.get("pattern_type")),
            ("data-figure-studio-native-pattern-paint-type", native_pattern.get("paint_type")),
        ):
            if value is not None and str(value) != "":
                element.set(attribute, str(value))
        if feature_types:
            element.set("data-figure-studio-source-feature-types", ",".join(feature_types))
        counts["clip_members"] += int("clip_path" in feature_types)
        counts["mask_members"] += int("mask" in feature_types)
        counts["filter_members"] += int("filter" in feature_types)
        counts["blend_members"] += int("blend_mode" in feature_types)
        counts["native_gradient_members"] += int(bool(native_shading_memberships))
        counts["native_pattern_members"] += int(bool(native_pattern_memberships))
        counts["native_resource_links"] += int(bool(native_id or native_pattern_memberships))
        element.set("data-figure-studio-source-id", source_id)
        element.set("data-figure-studio-source-sequence", str(sequence))
        counts["indexed"] += 1
        if bounds:
            element.set("data-figure-studio-bounds", svg_bounds_attribute(bounds))
            element.set("data-figure-studio-bounds-source", bounds_source or "analytic")
            counts["exact_bounds"] += 1

    indexed_svg = ET.tostring(root, encoding="unicode")
    return indexed_svg, {
        "schema": "figureStudio.pdfSvgEditIndex.v3",
        "status": "indexed",
        "id_strategy": "native-descriptor-link-or-content-hash",
        "bounds_strategy": "transformed-analytic-path-shape-and-native-text-bounds",
        "element_count": len(graphics),
        "indexed_element_count": counts["indexed"],
        "exact_bounds_count": counts["exact_bounds"],
        "native_descriptor_link_count": counts["native_links"],
        "form_xobject_member_count": counts["form_xobject_members"],
        "nested_form_xobject_member_count": counts["nested_form_xobject_members"],
        "shared_form_xobject_member_count": counts["shared_form_xobject_members"],
        "clip_member_count": counts["clip_members"],
        "mask_member_count": counts["mask_members"],
        "filter_member_count": counts["filter_members"],
        "blend_member_count": counts["blend_members"],
        "represented_svg_clip_member_count": counts["represented_svg_clip_members"],
        "represented_svg_mask_member_count": counts["represented_svg_mask_members"],
        "native_clip_member_count": counts["native_clip_members"],
        "native_mask_member_count": counts["native_mask_members"],
        "native_gradient_member_count": counts["native_gradient_members"],
        "native_pattern_member_count": counts["native_pattern_members"],
        "native_resource_link_count": counts["native_resource_links"],
        "path_count": counts["path"],
        "text_count": counts["text"],
        "image_count": counts["image"],
        "shape_count": counts["shape"],
        "unindexed_element_count": max(0, len(graphics) - counts["indexed"]),
        "bounds_coverage": round(counts["exact_bounds"] / max(1, len(graphics)), 6),
        "full_native_equivalence": False,
    }


def classify_preservation(text_count: int, path_count: int, image_count: int) -> str:
    if image_count and not text_count and not path_count:
        return "image_only_wrapper"
    if image_count and (text_count or path_count):
        return "mixed_vector_raster"
    if text_count:
        return "vector_text"
    if path_count:
        return "vector_paths"
    return "unknown"


def build_warnings(classification: str, counts: dict[str, int], svg_bytes: int) -> list[str]:
    warnings: list[str] = []
    if classification == "image_only_wrapper":
        warnings.append("PDF page converted to an SVG wrapper around embedded raster image data.")
    if classification == "mixed_vector_raster":
        warnings.append("Converted SVG contains embedded raster image data alongside vector elements.")
    if counts["text_count"] == 0 and counts["path_count"] >= 50:
        warnings.append("No SVG text elements detected; labels may be converted to paths.")
    if counts["path_count"] >= 1000:
        warnings.append("High SVG path count may slow browser import, selection, save/load, or export.")
    if svg_bytes >= 1_000_000:
        warnings.append("Large SVG output may increase project JSON size and browser memory use.")
    if classification == "unknown":
        warnings.append("Could not classify preservation quality from generated SVG elements.")
    return warnings


def finite_number(value: object, default: float = 0.0) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return default
    if numeric != numeric or numeric in {float("inf"), float("-inf")}:
        return default
    return numeric


def rect_payload(rect: object) -> dict[str, float] | None:
    if rect is None:
        return None
    try:
        x0 = finite_number(getattr(rect, "x0"))
        y0 = finite_number(getattr(rect, "y0"))
        x1 = finite_number(getattr(rect, "x1"))
        y1 = finite_number(getattr(rect, "y1"))
    except Exception:  # noqa: BLE001 - tolerate rectangle-like value variants
        if isinstance(rect, dict) and all(key in rect for key in ("x0", "y0", "x1", "y1")):
            x0, y0, x1, y1 = (finite_number(rect.get(key)) for key in ("x0", "y0", "x1", "y1"))
        elif isinstance(rect, (list, tuple)) and len(rect) >= 4:
            x0, y0, x1, y1 = (finite_number(part) for part in rect[:4])
        else:
            return None
    return {
        "x0": x0,
        "y0": y0,
        "x1": x1,
        "y1": y1,
        "width": max(0.0, x1 - x0),
        "height": max(0.0, y1 - y0),
    }


def color_payload(value: object) -> list[float] | None:
    if not isinstance(value, (list, tuple)):
        return None
    return [round(finite_number(part), 4) for part in value[:4]]


def hex_color_triplet(value: object, fallback: str = "#111820") -> tuple[float, float, float]:
    text = str(value or fallback).strip()
    match = re.match(r"^#?([0-9a-fA-F]{6})$", text) or re.match(r"^#?([0-9a-fA-F]{3})$", text)
    hex_value = match.group(1) if match else fallback.replace("#", "")
    if len(hex_value) == 3:
        hex_value = "".join(part * 2 for part in hex_value)
    try:
        return (
            int(hex_value[0:2], 16) / 255,
            int(hex_value[2:4], 16) / 255,
            int(hex_value[4:6], 16) / 255,
        )
    except ValueError:
        return (17 / 255, 24 / 255, 32 / 255)


class PikePdfPoint:
    """Small point value used by the legacy descriptor geometry helpers."""

    def __init__(self, x: object, y: object) -> None:
        self.x = finite_number(x)
        self.y = finite_number(y)


class PikePdfRect:
    """Top-left page rectangle compatible with the descriptor geometry helpers."""

    def __init__(self, x0: object, y0: object, x1: object, y1: object) -> None:
        self.x0 = finite_number(x0)
        self.y0 = finite_number(y0)
        self.x1 = finite_number(x1)
        self.y1 = finite_number(y1)

    @property
    def width(self) -> float:
        return max(0.0, self.x1 - self.x0)

    @property
    def height(self) -> float:
        return max(0.0, self.y1 - self.y0)


class PikePdfGeometry:
    """Namespace passed to geometry helpers in place of a renderer module."""

    Point = PikePdfPoint
    Rect = PikePdfRect


def pikepdf_object_ref(value: object) -> tuple[int, int]:
    try:
        objgen = tuple(value.objgen)
    except (AttributeError, TypeError):
        return (0, 0)
    if len(objgen) != 2:
        return (0, 0)
    return (int(objgen[0]), int(objgen[1]))


def pikepdf_object_by_xref(pdf: object, xref: int) -> object | None:
    if xref <= 0:
        return None
    try:
        return pdf.get_object((xref, 0))
    except Exception:  # noqa: BLE001 - tolerate nonzero generations in malformed/legacy PDFs
        for item in getattr(pdf, "objects", []):
            if pikepdf_object_ref(item)[0] == xref:
                return item
    return None


def pikepdf_direct_object_bytes(value: object) -> bytes:
    """Serialize an object body rather than its indirect-reference token."""

    try:
        import pikepdf

        if value is None:
            return b"null"
        if isinstance(value, bool):
            return b"true" if value else b"false"
        if isinstance(value, (int, float)):
            return pdf_operator_number(value).encode("ascii")
        if isinstance(value, str):
            return value.encode("latin-1", errors="replace")
        if isinstance(value, pikepdf.Stream):
            return bytes(value.stream_dict.unparse())
        if isinstance(value, pikepdf.Dictionary):
            return bytes(value.copy().unparse())
        if isinstance(value, pikepdf.Array):
            return bytes(pikepdf.Array(list(value)).unparse())
        return bytes(value.unparse())
    except Exception:  # noqa: BLE001 - diagnostic callers treat an empty body as unavailable
        return b""


_PIKEPDF_REFERENCE_PATTERN = re.compile(rb"(?<![A-Za-z0-9_])(\d+)\s+(\d+)\s+R(?![A-Za-z0-9_])")


def parse_pikepdf_object_value(pdf: object, source: str) -> object:
    """Parse QPDF object syntax while resolving indirect references in ``pdf``."""

    import pikepdf

    raw = str(source or "null").encode("latin-1", errors="replace")
    references: dict[str, tuple[int, int]] = {}

    def replace_reference(match: re.Match[bytes]) -> bytes:
        token = f"/__FS_REF_{len(references)}"
        references[token] = (int(match.group(1)), int(match.group(2)))
        return token.encode("ascii")

    parsed = pikepdf.Object.parse(_PIKEPDF_REFERENCE_PATTERN.sub(replace_reference, raw))

    def resolve(value: object) -> object:
        if isinstance(value, pikepdf.Name):
            ref = references.get(str(value))
            return pdf.get_object(ref) if ref else value
        if isinstance(value, pikepdf.Array):
            for index, item in enumerate(list(value)):
                value[index] = resolve(item)
            return value
        if isinstance(value, pikepdf.Dictionary):
            for key, item in list(value.items()):
                value[key] = resolve(item)
            return value
        return value

    return resolve(parsed)


def pikepdf_box_rect(value: object) -> PikePdfRect | None:
    try:
        values = [finite_number(item) for item in list(value)[:4]]
    except (TypeError, ValueError):
        return None
    if len(values) < 4:
        return None
    x0, x1 = sorted((values[0], values[2]))
    y0, y1 = sorted((values[1], values[3]))
    if x1 <= x0 or y1 <= y0:
        return None
    return PikePdfRect(x0, y0, x1, y1)


def pikepdf_page_box(page: object) -> PikePdfRect:
    media = pikepdf_box_rect(pikepdf_inherited_page_value(page, "/MediaBox"))
    crop = pikepdf_box_rect(pikepdf_inherited_page_value(page, "/CropBox"))
    if media and crop:
        intersection = PikePdfRect(
            max(media.x0, crop.x0),
            max(media.y0, crop.y0),
            min(media.x1, crop.x1),
            min(media.y1, crop.y1),
        )
        if intersection.width > 0 and intersection.height > 0:
            return intersection
    return crop or media or PikePdfRect(0, 0, 612, 792)


def pikepdf_page_rotation(page: object) -> int:
    rotation = int(finite_number(pikepdf_inherited_page_value(page, "/Rotate"), 0)) % 360
    return rotation if rotation in {0, 90, 180, 270} else 0


def pikepdf_page_content_objects(page: object) -> list[object]:
    import pikepdf

    contents = page.obj.get("/Contents")
    if isinstance(contents, pikepdf.Stream):
        return [contents]
    if isinstance(contents, pikepdf.Array):
        return [item for item in contents if isinstance(item, pikepdf.Stream)]
    return []


def pikepdf_inherited_page_value(page: object, key: str) -> object | None:
    cursor = page.obj
    visited: set[tuple[int, int]] = set()
    while cursor is not None:
        ref = pikepdf_object_ref(cursor)
        if ref in visited:
            return None
        visited.add(ref)
        try:
            value = cursor.get(key)
        except AttributeError:
            return None
        if value is not None:
            return value
        cursor = cursor.get("/Parent")
    return None


def pikepdf_append_page_stream(pdf: object, page: object, stream_bytes: bytes) -> int:
    import pikepdf

    stream = pikepdf.Stream(pdf, stream_bytes)
    contents = page.obj.get("/Contents")
    if isinstance(contents, pikepdf.Array):
        page.obj["/Contents"] = pikepdf.Array([*list(contents), stream])
    elif isinstance(contents, pikepdf.Stream):
        page.obj["/Contents"] = pikepdf.Array([contents, stream])
    else:
        page.obj["/Contents"] = stream
    return pikepdf_object_ref(stream)[0]


def pikepdf_page_extgstate_name(pdf: object, page: object, fill_alpha: float, stroke_alpha: float) -> str:
    import pikepdf

    inherited = pikepdf_inherited_page_value(page, "/Resources")
    resources = inherited.copy() if isinstance(inherited, pikepdf.Dictionary) else pikepdf.Dictionary()
    extgstates = resources.get("/ExtGState")
    extgstates = extgstates.copy() if isinstance(extgstates, pikepdf.Dictionary) else pikepdf.Dictionary()
    index = 1
    while f"/FSPdfAlpha{index}" in extgstates:
        index += 1
    name = f"FSPdfAlpha{index}"
    extgstates[f"/{name}"] = pdf.make_indirect(pikepdf.Dictionary({
        "/Type": pikepdf.Name("/ExtGState"),
        "/ca": max(0.0, min(1.0, fill_alpha)),
        "/CA": max(0.0, min(1.0, stroke_alpha)),
    }))
    resources["/ExtGState"] = extgstates
    page.obj["/Resources"] = resources
    return name


def pdf_content_color_operator(color: tuple[float, float, float], operator: str) -> str:
    return " ".join(pdf_operator_number(component) for component in color) + f" {operator}"


class PikePdfShape:
    """Accumulate the bounded path overlay operations emitted by Figure Tool."""

    def __init__(self, document: "PikePdfDocument", page: "PikePdfPage") -> None:
        self.document = document
        self.page = page
        self.commands: list[str] = []
        self.style: dict[str, object] = {}
        self.cursor: tuple[float, float] | None = None

    def point(self, value: PikePdfPoint) -> tuple[float, float]:
        return (value.x, value.y)

    def draw_line(self, start: PikePdfPoint, end: PikePdfPoint) -> None:
        x0, y0 = self.point(start)
        x1, y1 = self.point(end)
        if self.cursor != (x0, y0):
            self.commands.append(f"{pdf_operator_number(x0)} {pdf_operator_number(y0)} m")
        self.commands.append(f"{pdf_operator_number(x1)} {pdf_operator_number(y1)} l")
        self.cursor = (x1, y1)

    def draw_bezier(
        self,
        start: PikePdfPoint,
        control1: PikePdfPoint,
        control2: PikePdfPoint,
        end: PikePdfPoint,
    ) -> None:
        x0, y0 = self.point(start)
        x1, y1 = self.point(control1)
        x2, y2 = self.point(control2)
        x3, y3 = self.point(end)
        if self.cursor != (x0, y0):
            self.commands.append(f"{pdf_operator_number(x0)} {pdf_operator_number(y0)} m")
        self.commands.append(
            f"{pdf_operator_number(x1)} {pdf_operator_number(y1)} "
            f"{pdf_operator_number(x2)} {pdf_operator_number(y2)} "
            f"{pdf_operator_number(x3)} {pdf_operator_number(y3)} c"
        )
        self.cursor = (x3, y3)

    def finish(self, **style: object) -> None:
        self.style = style

    def commit(self, overlay: bool = True) -> None:  # noqa: ARG002 - compatibility with the previous writer
        if not self.commands:
            return
        fill = self.style.get("fill")
        stroke = self.style.get("color") or (0.0, 0.0, 0.0)
        fill_alpha = finite_number(self.style.get("fill_opacity"), 1.0)
        stroke_alpha = finite_number(self.style.get("stroke_opacity"), 1.0)
        alpha_name = pikepdf_page_extgstate_name(
            self.document.pdf,
            self.page.page,
            fill_alpha,
            stroke_alpha,
        )
        lines = [
            "q",
            f"/{alpha_name} gs",
            pdf_content_color_operator(stroke, "RG"),
            f"{pdf_operator_number(max(0.25, finite_number(self.style.get('width'), 1.0)))} w",
        ]
        if fill is not None:
            lines.append(pdf_content_color_operator(fill, "rg"))
        lines.extend(self.commands)
        lines.append("B*" if fill is not None and self.style.get("even_odd") else "B" if fill is not None else "S")
        lines.extend(["Q", ""])
        pikepdf_append_page_stream(self.document.pdf, self.page.page, "\n".join(lines).encode("ascii"))


class PikePdfPage:
    def __init__(self, document: "PikePdfDocument", index: int) -> None:
        self.document = document
        self.index = index
        self.page = document.pdf.pages[index]
        self.xref = pikepdf_object_ref(self.page.obj)[0]
        self.crop_box = pikepdf_page_box(self.page)
        self.rotation = pikepdf_page_rotation(self.page)
        viewport_width = self.crop_box.height if self.rotation in {90, 270} else self.crop_box.width
        viewport_height = self.crop_box.width if self.rotation in {90, 270} else self.crop_box.height
        # Match PDF.js' scale=1 viewport: crop-relative, top-left, and rotation-aware.
        self.rect = PikePdfRect(0, 0, viewport_width, viewport_height)

    def viewport_point_to_pdf(self, x: object, y: object) -> PikePdfPoint:
        """Invert PDF.js' page viewport transform into default PDF user space."""

        u = finite_number(x)
        v = finite_number(y)
        box = self.crop_box
        if self.rotation == 90:
            return PikePdfPoint(box.x0 + v, box.y0 + u)
        if self.rotation == 180:
            return PikePdfPoint(box.x1 - u, box.y0 + v)
        if self.rotation == 270:
            return PikePdfPoint(box.x1 - v, box.y1 - u)
        return PikePdfPoint(box.x0 + u, box.y1 - v)

    def descriptor_point(self, x: object, y: object, origin: str) -> PikePdfPoint:
        normalized_origin = str(origin or "bottom-left").strip().lower()
        if normalized_origin in {"pdf-stream", "native-stream"}:
            return PikePdfPoint(x, y)
        viewport_y = self.rect.height - finite_number(y) if normalized_origin == "bottom-left" else finite_number(y)
        return self.viewport_point_to_pdf(x, viewport_y)

    def descriptor_rect(
        self,
        x: object,
        y: object,
        width: object,
        height: object,
        origin: str,
    ) -> PikePdfRect:
        x0 = finite_number(x)
        y0 = finite_number(y)
        x1 = x0 + max(0.25, finite_number(width, 1))
        y1 = y0 + max(0.25, finite_number(height, 1))
        corners = [
            self.descriptor_point(px, py, origin)
            for px, py in ((x0, y0), (x1, y0), (x0, y1), (x1, y1))
        ]
        return PikePdfRect(
            min(point.x for point in corners),
            min(point.y for point in corners),
            max(point.x for point in corners),
            max(point.y for point in corners),
        )

    def get_contents(self) -> list[int]:
        return [
            pikepdf_object_ref(item)[0]
            for item in pikepdf_page_content_objects(self.page)
            if pikepdf_object_ref(item)[0] > 0
        ]

    def new_shape(self) -> PikePdfShape:
        return PikePdfShape(self.document, self)

    def draw_rect(
        self,
        rect: PikePdfRect,
        color: tuple[float, float, float],
        width: float,
        overlay: bool = True,  # noqa: ARG002 - the stream is always appended
    ) -> None:
        x = rect.x0
        y = rect.y0
        lines = [
            "q",
            pdf_content_color_operator(color, "RG"),
            f"{pdf_operator_number(max(0.25, finite_number(width, 1.0)))} w",
            (
                f"{pdf_operator_number(x)} {pdf_operator_number(y)} "
                f"{pdf_operator_number(rect.width)} {pdf_operator_number(rect.height)} re S"
            ),
            "Q",
            "",
        ]
        pikepdf_append_page_stream(self.document.pdf, self.page, "\n".join(lines).encode("ascii"))


class PikePdfDocument:
    """Minimal QPDF adapter for the established bounded descriptor compiler."""

    def __init__(self, pdf: object) -> None:
        self.pdf = pdf

    @classmethod
    def open(cls, pdf_bytes: bytes) -> "PikePdfDocument":
        import pikepdf

        return cls(pikepdf.Pdf.open(BytesIO(pdf_bytes)))

    @property
    def page_count(self) -> int:
        return len(self.pdf.pages)

    def __getitem__(self, index: int) -> PikePdfPage:
        return PikePdfPage(self, index)

    def load_page(self, index: int) -> PikePdfPage:
        return self[index]

    def xref_length(self) -> int:
        return max([pikepdf_object_ref(item)[0] for item in self.pdf.objects] or [0]) + 1

    def xref_object(self, xref: int, compressed: bool = False) -> str:  # noqa: ARG002
        value = pikepdf_object_by_xref(self.pdf, xref)
        return pikepdf_direct_object_bytes(value).decode("latin-1", errors="replace") if value is not None else ""

    def xref_stream(self, xref: int) -> bytes:
        import pikepdf

        value = pikepdf_object_by_xref(self.pdf, xref)
        return bytes(value.read_bytes(pikepdf.StreamDecodeLevel.specialized)) if isinstance(value, pikepdf.Stream) else b""

    def update_stream(self, xref: int, data: bytes) -> None:
        import pikepdf

        value = pikepdf_object_by_xref(self.pdf, xref)
        if not isinstance(value, pikepdf.Stream):
            raise ValueError(f"PDF object {xref} is not a stream.")
        value.write(bytes(data))

    def get_new_xref(self) -> int:
        import pikepdf

        value = self.pdf.make_indirect(pikepdf.Dictionary())
        return pikepdf_object_ref(value)[0]

    def xref_copy(self, source_xref: int, target_xref: int) -> None:
        import pikepdf

        source = pikepdf_object_by_xref(self.pdf, source_xref)
        target = pikepdf_object_by_xref(self.pdf, target_xref)
        if source is None or target is None:
            raise ValueError("Cannot clone an unavailable PDF object.")
        target_ref = pikepdf_object_ref(target)
        if isinstance(source, pikepdf.Stream):
            copied = source.copy()
            self.pdf._swap_objects(target_ref, pikepdf_object_ref(copied))
            return
        if isinstance(source, pikepdf.Dictionary):
            copied = source.copy()
        elif isinstance(source, pikepdf.Array):
            copied = pikepdf.Array(list(source))
        else:
            copied = parse_pikepdf_object_value(self.pdf, pikepdf_direct_object_bytes(source).decode("latin-1"))
        self.pdf._replace_object(target_ref, copied)

    def update_object(self, xref: int, source: str) -> None:
        import pikepdf

        existing = pikepdf_object_by_xref(self.pdf, xref)
        if existing is None:
            raise ValueError(f"PDF object {xref} is unavailable.")
        parsed = parse_pikepdf_object_value(self.pdf, source)
        if isinstance(existing, pikepdf.Stream) and isinstance(parsed, pikepdf.Dictionary):
            for key in list(existing.keys()):
                if key != "/Length" and key not in parsed:
                    del existing[key]
            for key, value in parsed.items():
                if key != "/Length":
                    existing[key] = value
            return
        if isinstance(existing, pikepdf.Dictionary) and isinstance(parsed, pikepdf.Dictionary):
            for key in list(existing.keys()):
                if key not in parsed:
                    del existing[key]
            for key, value in parsed.items():
                existing[key] = value
            return
        self.pdf._replace_object(pikepdf_object_ref(existing), parsed)

    def xref_get_key(self, xref: int, key: str) -> tuple[str, str]:
        import pikepdf

        value = pikepdf_object_by_xref(self.pdf, xref)
        for part in [part for part in str(key or "").split("/") if part]:
            if not isinstance(value, (pikepdf.Dictionary, pikepdf.Stream)):
                return ("null", "null")
            value = value.get(f"/{part}")
            if value is None:
                return ("null", "null")
        ref = pikepdf_object_ref(value)
        if ref[0] > 0:
            return ("xref", f"{ref[0]} {ref[1]} R")
        if isinstance(value, pikepdf.Dictionary):
            value_type = "dict"
        elif isinstance(value, pikepdf.Array):
            value_type = "array"
        elif isinstance(value, pikepdf.Name):
            value_type = "name"
        elif isinstance(value, pikepdf.String):
            value_type = "string"
        elif isinstance(value, bool):
            value_type = "bool"
        elif isinstance(value, int):
            value_type = "int"
        elif isinstance(value, float):
            value_type = "float"
        elif value is None:
            value_type = "null"
        else:
            value_type = "unknown"
        return (value_type, pikepdf_direct_object_bytes(value).decode("latin-1", errors="replace"))

    def xref_set_key(self, xref: int, key: str, source: str) -> None:
        import pikepdf

        owner = pikepdf_object_by_xref(self.pdf, xref)
        if not isinstance(owner, (pikepdf.Dictionary, pikepdf.Stream)):
            raise ValueError(f"PDF object {xref} cannot own dictionary key {key}.")
        parts = [part for part in str(key or "").split("/") if part]
        if not parts:
            raise ValueError("PDF dictionary key is required.")
        target = owner
        for part in parts[:-1]:
            child = target.get(f"/{part}")
            if not isinstance(child, pikepdf.Dictionary):
                child = pikepdf.Dictionary()
                target[f"/{part}"] = child
            target = child
        target[f"/{parts[-1]}"] = parse_pikepdf_object_value(self.pdf, source)

    def write(self, **_options: object) -> bytes:
        import pikepdf

        output = BytesIO()
        self.pdf.save(
            output,
            compress_streams=True,
            object_stream_mode=pikepdf.ObjectStreamMode.preserve,
            normalize_content=False,
            recompress_flate=True,
        )
        return output.getvalue()

    def close(self) -> None:
        self.pdf.close()


def page_content_xrefs(page: object) -> list[int]:
    try:
        return [int(finite_number(xref, 0)) for xref in page.get_contents()]
    except Exception:  # noqa: BLE001
        return []


def pdf_xref_object_source(doc: object, xref: int) -> str:
    if xref <= 0:
        return ""
    try:
        return str(doc.xref_object(xref, compressed=False) or "")
    except Exception:  # noqa: BLE001
        return ""


def pdf_xref_stream_bytes(doc: object, xref: int) -> bytes:
    if xref <= 0:
        return b""
    try:
        return bytes(doc.xref_stream(xref) or b"")
    except Exception:  # noqa: BLE001
        return b""


def pdf_xobject_subtype(source: str) -> str:
    match = re.search(r"/Subtype\s*/([A-Za-z0-9_.-]+)", source or "")
    return match.group(1) if match else ""


def pdf_matrix_multiply(left: list[float], right: list[float]) -> list[float]:
    a, b, c, d, e, f = left
    a2, b2, c2, d2, e2, f2 = right
    return [
        a * a2 + c * b2,
        b * a2 + d * b2,
        a * c2 + c * d2,
        b * c2 + d * d2,
        a * e2 + c * f2 + e,
        b * e2 + d * f2 + f,
    ]


def pdf_uniform_stroke_scale(matrix: list[object] | tuple[object, ...]) -> float | None:
    if len(matrix) < 6:
        return None
    a, b, c, d = [finite_number(value, 0) for value in list(matrix)[:4]]
    x_scale = math.hypot(a, b)
    y_scale = math.hypot(c, d)
    dot = (a * c) + (b * d)
    tolerance = max(0.0001, max(x_scale, y_scale) * 0.001)
    if x_scale <= 0 or y_scale <= 0 or abs(x_scale - y_scale) > tolerance or abs(dot) > tolerance:
        return None
    return (x_scale + y_scale) / 2


def pdf_bbox_to_page_payload(bbox: object, matrix: list[float], page_height: float) -> dict[str, float] | None:
    source = rect_payload(bbox)
    if not source or len(matrix) < 6:
        return None
    a, b, c, d, e, f = (finite_number(value) for value in matrix[:6])
    corners = (
        (source["x0"], source["y0"]),
        (source["x1"], source["y0"]),
        (source["x1"], source["y1"]),
        (source["x0"], source["y1"]),
    )
    transformed = [(a * x + c * y + e, b * x + d * y + f) for x, y in corners]
    xs = [point[0] for point in transformed]
    ys = [page_height - point[1] for point in transformed]
    return rect_payload((min(xs), min(ys), max(xs), max(ys)))


def pdf_xref_key_payload(doc: object, owner_xref: int, key: str) -> tuple[str, str]:
    if owner_xref <= 0 or not hasattr(doc, "xref_get_key"):
        return "", ""
    try:
        value_type, value = doc.xref_get_key(owner_xref, key)
        return str(value_type or ""), str(value or "")
    except Exception:  # noqa: BLE001
        return "", ""


def pdf_indirect_reference_map(source: str) -> dict[str, int]:
    rows: dict[str, int] = {}
    for name, xref in re.findall(r"/([A-Za-z0-9_.#-]+)\s+(\d+)\s+\d+\s+R", source or ""):
        parsed = int(finite_number(xref, 0))
        if parsed > 0:
            rows[name] = parsed
    return rows


def pdf_resource_ref_map(doc: object, owner_xref: int, category: str) -> tuple[dict[str, int], int, bool]:
    value_type, value = pdf_xref_key_payload(doc, owner_xref, f"Resources/{category}")
    resource_dictionary_xref = 0
    source = value
    if value_type == "xref":
        match = re.match(r"(\d+)\s+\d+\s+R", value.strip())
        resource_dictionary_xref = int(finite_number(match.group(1), 0)) if match else 0
        source = pdf_xref_object_source(doc, resource_dictionary_xref)
    if value_type in {"null", "none", ""}:
        return {}, resource_dictionary_xref, True
    refs = pdf_indirect_reference_map(source)
    complete = bool(refs) or source.strip() in {"", "<<>>", "<< >>"}
    return refs, resource_dictionary_xref, complete


def pdf_value_end(source: str, start: int) -> int:
    if start >= len(source):
        return start
    if source.startswith("<<", start):
        dictionary_depth = 1
        index = start + 2
        while index < len(source) and dictionary_depth > 0:
            if source[index] == "(":
                depth = 1
                index += 1
                while index < len(source) and depth > 0:
                    if source[index] == "\\":
                        index += 2
                        continue
                    if source[index] == "(":
                        depth += 1
                    elif source[index] == ")":
                        depth -= 1
                    index += 1
                continue
            if source.startswith("<<", index):
                dictionary_depth += 1
                index += 2
                continue
            if source.startswith(">>", index):
                dictionary_depth -= 1
                index += 2
                continue
            index += 1
        return index
    if source[start] == "[":
        array_depth = 1
        index = start + 1
        while index < len(source) and array_depth > 0:
            if source[index] == "(":
                depth = 1
                index += 1
                while index < len(source) and depth > 0:
                    if source[index] == "\\":
                        index += 2
                        continue
                    if source[index] == "(":
                        depth += 1
                    elif source[index] == ")":
                        depth -= 1
                    index += 1
                continue
            if source[index] == "[":
                array_depth += 1
            elif source[index] == "]":
                array_depth -= 1
            index += 1
        return index
    reference_match = re.match(r"\d+\s+\d+\s+R\b", source[start:])
    if reference_match:
        return start + reference_match.end()
    token_match = re.match(r"(?:/[^\s\[\]<>/()]+|[^\s\[\]<>/()]+)", source[start:])
    return start + token_match.end() if token_match else start


def pdf_top_level_dictionary_entries(source: str) -> tuple[list[tuple[str, str]], bool]:
    start = source.find("<<")
    if start < 0:
        return [], False
    entries: list[tuple[str, str]] = []
    index = start + 2
    complete = True
    while index < len(source):
        while index < len(source) and source[index].isspace():
            index += 1
        if source.startswith(">>", index):
            return entries, complete
        if index >= len(source) or source[index] != "/":
            complete = False
            index += 1
            continue
        name_match = re.match(r"/([^\s\[\]<>/()]+)", source[index:])
        if not name_match:
            complete = False
            index += 1
            continue
        name = name_match.group(1)
        index += name_match.end()
        while index < len(source) and source[index].isspace():
            index += 1
        value_start = index
        value_end = pdf_value_end(source, value_start)
        if value_end <= value_start:
            complete = False
            index += 1
            continue
        entries.append((name, source[value_start:value_end].strip()))
        index = value_end
    return entries, False


def pdf_color_space_resource_entries(
    doc: object,
    owner_xref: int,
) -> tuple[list[dict[str, object]], int, bool]:
    value_type, value = pdf_xref_key_payload(doc, owner_xref, "Resources/ColorSpace")
    dictionary_xref = 0
    source = value
    if value_type == "xref":
        match = re.match(r"(\d+)\s+\d+\s+R", value.strip())
        dictionary_xref = int(finite_number(match.group(1), 0)) if match else 0
        source = pdf_xref_object_source(doc, dictionary_xref)
    if value_type in {"null", "none", ""}:
        return [], dictionary_xref, True
    entries, complete = pdf_top_level_dictionary_entries(source)
    rows: list[dict[str, object]] = []
    for raw_name, definition in entries:
        reference_match = re.fullmatch(r"(\d+)\s+\d+\s+R", definition)
        target_xref = int(reference_match.group(1)) if reference_match else 0
        rows.append({
            "name": decode_pdf_name(raw_name),
            "raw_name": raw_name,
            "target_xref": target_xref,
            "direct_definition": "" if target_xref else definition,
            "definition_kind": (
                "indirect-object"
                if target_xref
                else "direct-array"
                if definition.lstrip().startswith("[")
                else "direct-object"
            ),
            "definition_sha256": hashlib.sha256(definition.encode("latin-1", errors="ignore")).hexdigest(),
        })
    return rows, dictionary_xref, complete


def pdf_xref_number_array(doc: object, xref: int, key: str, fallback: list[float]) -> list[float]:
    _value_type, value = pdf_xref_key_payload(doc, xref, key)
    numbers = [finite_number(item, 0) for item in re.findall(r"[-+]?\d*\.?\d+", value)]
    return numbers if numbers else [*fallback]


def pdf_form_matrix(doc: object, xref: int) -> list[float]:
    values = pdf_xref_number_array(doc, xref, "Matrix", [1.0, 0.0, 0.0, 1.0, 0.0, 0.0])
    return [float(value) for value in (values[:6] if len(values) >= 6 else [1.0, 0.0, 0.0, 1.0, 0.0, 0.0])]


def pdf_form_bbox(doc: object, xref: int) -> dict[str, float] | None:
    values = pdf_xref_number_array(doc, xref, "BBox", [])
    return rect_payload(values[:4]) if len(values) >= 4 else None


def pdf_native_resource_scopes(doc: object, page: object, page_number: int) -> tuple[list[dict[str, object]], bool]:
    page_xref = int(finite_number(getattr(page, "xref", 0), 0))
    queue: list[tuple[int, str, list[int]]] = [(page_xref, "page", page_content_xrefs(page))]
    visited: set[int] = set()
    scopes: list[dict[str, object]] = []
    binding_count = 0
    truncated = False
    while queue and len(scopes) < MAX_NATIVE_PDF_RESOURCE_SCOPES:
        owner_xref, owner_kind, stream_xrefs = queue.pop(0)
        if owner_xref <= 0 or owner_xref in visited:
            continue
        visited.add(owner_xref)
        scope_id = f"scope:{owner_kind}:xref:{owner_xref}"
        bindings: list[dict[str, object]] = []
        scope_complete = True
        resource_dictionary_xrefs: set[int] = set()
        for category, kind in PDF_NATIVE_RESOURCE_CATEGORIES.items():
            if category == "ColorSpace":
                resource_entries, dictionary_xref, complete = pdf_color_space_resource_entries(doc, owner_xref)
            else:
                refs, dictionary_xref, complete = pdf_resource_ref_map(doc, owner_xref, category)
                resource_entries = [
                    {
                        "name": name,
                        "raw_name": name,
                        "target_xref": target_xref,
                        "direct_definition": "",
                        "definition_kind": "indirect-object",
                        "definition_sha256": "",
                    }
                    for name, target_xref in refs.items()
                ]
            scope_complete = scope_complete and complete
            if dictionary_xref > 0:
                resource_dictionary_xrefs.add(dictionary_xref)
            for resource_entry in resource_entries:
                if binding_count >= MAX_NATIVE_PDF_RESOURCE_USAGES:
                    truncated = True
                    break
                name = str(resource_entry.get("name") or "")
                target_xref = int(finite_number(resource_entry.get("target_xref"), 0))
                direct_definition = str(resource_entry.get("direct_definition") or "")
                target_source = pdf_xref_object_source(doc, target_xref)
                if not target_source and direct_definition:
                    target_source = direct_definition
                subtype = pdf_xobject_subtype(target_source) if kind == "xobject" else ""
                binding_kind = (
                    "form-xobject" if kind == "xobject" and subtype == "Form"
                    else "image-xobject" if kind == "xobject" and subtype == "Image"
                    else kind
                )
                definition_key = f"xref:{target_xref}" if target_xref > 0 else f"direct:{str(resource_entry.get('definition_sha256') or '')[:18]}"
                binding_id = f"{scope_id}:{kind}:{name}:{definition_key}"
                bindings.append({
                    "id": binding_id,
                    "scope_id": scope_id,
                    "owner_kind": owner_kind,
                    "owner_xref": owner_xref,
                    "kind": kind,
                    "binding_kind": binding_kind,
                    "name": name,
                    "raw_name": resource_entry.get("raw_name") or name,
                    "target_xref": target_xref,
                    "direct_definition": direct_definition,
                    "definition_kind": resource_entry.get("definition_kind") or "indirect-object",
                    "definition_sha256": resource_entry.get("definition_sha256") or "",
                    "target_subtype": subtype,
                    "target_object_sha256": hashlib.sha256(target_source.encode("utf-8", errors="ignore")).hexdigest() if target_source else "",
                    "ownership_status": "proven-native-resource-dictionary",
                })
                binding_count += 1
                if binding_kind == "form-xobject" and target_xref not in visited:
                    queue.append((target_xref, "form", [target_xref]))
            if truncated:
                break
        scopes.append({
            "id": scope_id,
            "owner_kind": owner_kind,
            "owner_xref": owner_xref,
            "page_number": page_number,
            "stream_xrefs": stream_xrefs,
            "resource_dictionary_xrefs": sorted(resource_dictionary_xrefs),
            "bindings": bindings,
            "binding_count": len(bindings),
            "resource_dictionary_parse_complete": scope_complete,
        })
        if truncated:
            break
    if queue:
        truncated = True
    return scopes, truncated


def pdf_content_resource_usage_events(doc: object, stream_xrefs: list[int]) -> tuple[list[dict[str, object]], bool]:
    events: list[dict[str, object]] = []
    current = [1.0, 0.0, 0.0, 1.0, 0.0, 0.0]
    stack: list[list[float]] = []
    occurrences: dict[tuple[int, str, str], int] = {}
    parser_complete = True
    for stream_xref in stream_xrefs:
        stream_bytes = pdf_xref_stream_bytes(doc, stream_xref)
        _text, tokens = scan_pdf_content_stream_tokens(stream_bytes)
        parser_complete = parser_complete and not any(token == "BI" for token, _offset in tokens)
        parser_complete = parser_complete and not pdf_content_span_has_unknown_operator(stream_bytes, 0, len(stream_bytes))
        operator_index = -1
        for token_index, (token, offset) in enumerate(tokens):
            if token in PDF_CONTENT_STREAM_OPERATOR_CATEGORIES:
                operator_index += 1
            if token == "q":
                stack.append([*current])
                continue
            if token == "Q":
                if not stack:
                    parser_complete = False
                    current = [1.0, 0.0, 0.0, 1.0, 0.0, 0.0]
                else:
                    current = stack.pop()
                continue
            if token == "cm":
                values = pdf_numeric_operands_before(tokens, token_index, 6)
                if values:
                    current = pdf_matrix_multiply(current, [float(value) for value in values])
                continue
            resource_kind = PDF_NATIVE_RESOURCE_USAGE_OPERATORS.get(token)
            if not resource_kind:
                continue
            if token in {"scn", "SCN"}:
                prior_token = tokens[token_index - 1][0] if token_index > 0 else ""
                if not prior_token.startswith("/"):
                    continue
                resource_name = prior_token[1:]
            else:
                resource_name = pdf_operator_resource_name(tokens, token_index)
            if not resource_name:
                continue
            occurrence_key = (stream_xref, token, resource_name)
            occurrence = occurrences.get(occurrence_key, 0) + 1
            occurrences[occurrence_key] = occurrence
            events.append({
                "stream_xref": stream_xref,
                "operator": token,
                "operator_index": operator_index,
                "byte_offset": offset,
                "resource_kind": resource_kind,
                "resource_name": resource_name,
                "occurrence": occurrence,
                "local_ctm": [round(value, 6) for value in current],
            })
    if stack:
        parser_complete = False
    return events, parser_complete


PDF_APPEARANCE_STATE_OPERATOR_TOKENS = {
    "g", "G", "rg", "RG", "k", "K", "cs", "CS", "sc", "SC", "scn", "SCN",
    "w", "d", "J", "j", "M", "gs",
}


def pdf_stream_prefix_preserves_default_appearance(
    doc: object,
    stream_xref: int,
    stop_operator_index: int | None = None,
) -> bool:
    stream_bytes = pdf_xref_stream_bytes(doc, stream_xref)
    if not stream_bytes:
        return False
    _text, tokens = scan_pdf_content_stream_tokens(stream_bytes)
    if any(token in {"BI", "ID", "EI"} for token, _offset in tokens):
        return False
    operator_index = -1
    depth = 0
    stop_found = stop_operator_index is None
    for token, _offset in tokens:
        if token in PDF_CONTENT_STREAM_OPERATOR_CATEGORIES:
            operator_index += 1
            if stop_operator_index is not None and operator_index == stop_operator_index:
                stop_found = True
                break
            if token in PDF_APPEARANCE_STATE_OPERATOR_TOKENS:
                return False
            if token == "q":
                depth += 1
            elif token == "Q":
                depth -= 1
                if depth < 0:
                    return False
            continue
        if (
            re.fullmatch(r"[A-Za-z][A-Za-z0-9*']*", token or "")
            and token not in {"true", "false", "null"}
        ):
            return False
    if not stop_found:
        return False
    return stop_operator_index is not None or depth == 0


def invocation_entry_default_appearance_proven(
    doc: object,
    page: object,
    invocation: dict[str, object],
    invocations_by_id: dict[str, dict[str, object]],
) -> bool:
    chain: list[dict[str, object]] = []
    cursor: dict[str, object] | None = invocation
    seen: set[str] = set()
    while cursor:
        cursor_id = str(cursor.get("id") or "")
        if not cursor_id or cursor_id in seen:
            return False
        seen.add(cursor_id)
        chain.append(cursor)
        parent_id = str(cursor.get("parent_invocation_id") or "")
        cursor = invocations_by_id.get(parent_id) if parent_id else None
    if not chain:
        return False
    for row in chain:
        form_xref = int(finite_number(row.get("form_xref"), 0))
        if form_xref <= 0 or selected_form_has_transparency_group(doc, form_xref):
            return False
    root = chain[-1]
    root_stream_xref = int(finite_number(root.get("caller_stream_xref"), 0))
    page_streams = page_content_xrefs(page)
    root_indexes = [index for index, xref in enumerate(page_streams) if xref == root_stream_xref]
    if len(root_indexes) != 1:
        return False
    for prior_xref in page_streams[:root_indexes[0]]:
        if not pdf_stream_prefix_preserves_default_appearance(doc, prior_xref):
            return False
    for row in reversed(chain):
        caller_stream_xref = int(finite_number(row.get("caller_stream_xref"), 0))
        do_operator_index = int(finite_number(row.get("do_operator_index"), -1))
        if caller_stream_xref <= 0 or do_operator_index < 0:
            return False
        if not pdf_stream_prefix_preserves_default_appearance(doc, caller_stream_xref, do_operator_index):
            return False
    return True


def native_pdf_invocation_index(doc: object, page: object, page_number: int = 1) -> dict[str, object]:
    page_xref = int(finite_number(getattr(page, "xref", 0), 0))
    page_height = finite_number(getattr(getattr(page, "rect", None), "height", 0), 0)
    page_stream_xrefs = page_content_xrefs(page)
    scopes, scope_truncated = pdf_native_resource_scopes(doc, page, page_number)
    scopes_by_owner = {int(finite_number(scope.get("owner_xref"), 0)): scope for scope in scopes}
    scan_cache: dict[int, tuple[list[dict[str, object]], bool]] = {}
    invocations: list[dict[str, object]] = []
    usages: list[dict[str, object]] = []
    unresolved_usages: list[dict[str, object]] = []
    cycle_count = 0
    depth_truncated = False
    usage_truncated = False
    invocation_truncated = False

    def scan_scope(owner_xref: int) -> tuple[list[dict[str, object]], bool]:
        if owner_xref not in scan_cache:
            scope = scopes_by_owner.get(owner_xref) or {}
            stream_xrefs = [int(finite_number(value, 0)) for value in scope.get("stream_xrefs", []) if int(finite_number(value, 0)) > 0]
            scan_cache[owner_xref] = pdf_content_resource_usage_events(doc, stream_xrefs)
        return scan_cache[owner_xref]

    def walk_scope(
        owner_xref: int,
        parent_invocation_id: str,
        parent_path: str,
        parent_page_ctm: list[float],
        depth: int,
        ancestors: tuple[int, ...],
    ) -> None:
        nonlocal cycle_count, depth_truncated, usage_truncated, invocation_truncated
        if depth > MAX_NATIVE_PDF_FORM_DEPTH:
            depth_truncated = True
            return
        scope = scopes_by_owner.get(owner_xref)
        if not scope:
            return
        bindings = {
            (str(binding.get("kind") or ""), str(binding.get("name") or "")): binding
            for binding in scope.get("bindings", [])
            if isinstance(binding, dict)
        }
        events, parser_complete = scan_scope(owner_xref)
        for event in events:
            binding = bindings.get((str(event.get("resource_kind") or ""), str(event.get("resource_name") or "")))
            if not binding:
                unresolved_usages.append({
                    **event,
                    "scope_id": scope.get("id") or "",
                    "owner_xref": owner_xref,
                    "owner_invocation_id": parent_invocation_id,
                    "resolution_status": "unresolved-resource-name",
                })
                continue
            if len(usages) >= MAX_NATIVE_PDF_RESOURCE_USAGES:
                usage_truncated = True
                return
            context_id = parent_invocation_id or f"page:{page_number}:xref:{page_xref}"
            usage_path = f"{parent_path}/{event['operator']}:{event['resource_name']}[{event['occurrence']}]"
            usage_hash = hashlib.sha256(usage_path.encode("utf-8")).hexdigest()[:18]
            usage = {
                "id": f"usage:{usage_hash}",
                "scope_id": scope.get("id") or "",
                "owner_xref": owner_xref,
                "owner_kind": scope.get("owner_kind") or "",
                "owner_invocation_id": parent_invocation_id,
                "owner_invocation_path": parent_path,
                "stream_xref": event.get("stream_xref"),
                "operator": event.get("operator"),
                "operator_index": event.get("operator_index"),
                "byte_offset": event.get("byte_offset"),
                "resource_kind": event.get("resource_kind"),
                "resource_name": event.get("resource_name"),
                "binding_id": binding.get("id") or "",
                "target_xref": binding.get("target_xref"),
                "local_ctm": event.get("local_ctm") or [],
                "page_ctm": pdf_matrix_multiply(parent_page_ctm, event.get("local_ctm") or [1, 0, 0, 1, 0, 0]),
                "resolution_status": "proven-native-syntax" if parser_complete else "bounded-native-syntax-inline-image-review",
                "context_id": context_id,
            }
            usages.append(usage)
            if event.get("operator") != "Do" or binding.get("binding_kind") != "form-xobject":
                continue
            if len(invocations) >= MAX_NATIVE_PDF_FORM_INVOCATIONS:
                invocation_truncated = True
                return
            form_xref = int(finite_number(binding.get("target_xref"), 0))
            form_matrix = pdf_form_matrix(doc, form_xref)
            invocation_page_ctm = pdf_matrix_multiply(usage["page_ctm"], form_matrix)
            invocation_path = f"{usage_path}@xref:{form_xref}"
            invocation_hash = hashlib.sha256(invocation_path.encode("utf-8")).hexdigest()[:18]
            invocation_id = f"inv:{invocation_hash}"
            same_binding_count = 1 + len([row for row in invocations if row.get("binding_id") == binding.get("id")])
            form_bbox = pdf_form_bbox(doc, form_xref)
            cycle = form_xref in ancestors
            invocation = {
                "id": invocation_id,
                "invocation_id": invocation_id,
                "invocation_path": invocation_path,
                "parent_invocation_id": parent_invocation_id,
                "parent_owner_xref": owner_xref,
                "nesting_depth": depth,
                "ordinal": same_binding_count,
                "binding_id": binding.get("id") or "",
                "resource_scope_id": scope.get("id") or "",
                "resource_owner_xref": owner_xref,
                "resource_owner_scope": "form-xobject" if scope.get("owner_kind") == "form" else "page",
                "caller_stream_xref": event.get("stream_xref"),
                "caller_stream_sha256": hashlib.sha256(
                    pdf_xref_stream_bytes(doc, int(finite_number(event.get("stream_xref"), 0)))
                ).hexdigest(),
                "caller_contents_indexes": [
                    index for index, xref in enumerate(page_stream_xrefs)
                    if scope.get("owner_kind") == "page" and xref == int(finite_number(event.get("stream_xref"), 0))
                ],
                "do_operator_index": event.get("operator_index"),
                "do_byte_offset": event.get("byte_offset"),
                "name": event.get("resource_name") or "",
                "form_xref": form_xref,
                "local_ctm": event.get("local_ctm") or [],
                "form_matrix": form_matrix,
                "page_ctm": [round(value, 6) for value in invocation_page_ctm],
                "form_bbox": form_bbox,
                "page_bbox": pdf_bbox_to_page_payload(form_bbox, invocation_page_ctm, page_height),
                "cycle_truncated": cycle,
                "ownership_status": usage.get("resolution_status") or "",
            }
            invocation["caller_contents_index"] = (
                invocation["caller_contents_indexes"][0]
                if len(invocation["caller_contents_indexes"]) == 1
                else None
            )
            invocation["caller_stream_placement_unambiguous"] = (
                scope.get("owner_kind") != "page" or len(invocation["caller_contents_indexes"]) == 1
            )
            invocations.append(invocation)
            usage["form_invocation_id"] = invocation_id
            if cycle:
                cycle_count += 1
                continue
            walk_scope(
                form_xref,
                invocation_id,
                invocation_path,
                invocation_page_ctm,
                depth + 1,
                ancestors + (form_xref,),
            )

    page_path = f"page:{page_number}:xref:{page_xref}"
    walk_scope(page_xref, "", page_path, [1.0, 0.0, 0.0, 1.0, 0.0, 0.0], 1, tuple())
    invocation_counts_by_xref: dict[int, int] = {}
    for row in invocations:
        xref = int(finite_number(row.get("form_xref"), 0))
        invocation_counts_by_xref[xref] = invocation_counts_by_xref.get(xref, 0) + 1
    for row in invocations:
        shared_count = invocation_counts_by_xref.get(int(finite_number(row.get("form_xref"), 0)), 0)
        row["definition_invocation_count"] = shared_count
        row["shared_definition"] = shared_count > 1
        row["per_instance_native_write_supported"] = shared_count <= 1
        row["native_write_scope"] = "shared-form-definition" if shared_count > 1 else "form-definition"
    invocations_by_id = {str(row.get("id") or ""): row for row in invocations if row.get("id")}
    for row in invocations:
        cursor = row
        chain_form_xrefs: list[int] = []
        chain_seen: set[str] = set()
        while cursor:
            cursor_id = str(cursor.get("id") or "")
            if not cursor_id or cursor_id in chain_seen:
                chain_form_xrefs = []
                break
            chain_seen.add(cursor_id)
            chain_form_xrefs.append(int(finite_number(cursor.get("form_xref"), 0)))
            parent_id = str(cursor.get("parent_invocation_id") or "")
            cursor = invocations_by_id.get(parent_id) if parent_id else None
        row["transparency_group_in_chain"] = not chain_form_xrefs or any(
            xref <= 0 or selected_form_has_transparency_group(doc, xref)
            for xref in chain_form_xrefs
        )
        row["entry_default_appearance_proven"] = invocation_entry_default_appearance_proven(
            doc,
            page,
            row,
            invocations_by_id,
        )

    form_definitions: list[dict[str, object]] = []
    for scope in scopes:
        for binding in scope.get("bindings", []):
            if not isinstance(binding, dict) or binding.get("binding_kind") != "form-xobject":
                continue
            matching = [row for row in invocations if row.get("binding_id") == binding.get("id")]
            xref = int(finite_number(binding.get("target_xref"), 0))
            stream_bytes = pdf_xref_stream_bytes(doc, xref)
            _group_type, group_subtype = pdf_xref_key_payload(doc, xref, "Group/S")
            form_source = pdf_xref_object_source(doc, xref)
            transparency_group = (
                str(group_subtype or "").strip() == "/Transparency"
                or bool(re.search(r"/Group\s*<<[^>]*?/S\s*/Transparency\b", form_source, re.DOTALL))
            )
            form_definitions.append({
                **binding,
                "definition_id": binding.get("id") or "",
                "form_xref": xref,
                "form_matrix": pdf_form_matrix(doc, xref),
                "form_bbox": pdf_form_bbox(doc, xref),
                "byte_length": len(stream_bytes),
                "stream_sha256": hashlib.sha256(stream_bytes).hexdigest() if stream_bytes else "",
                "transparency_group": transparency_group,
                "invocation_count": len(matching),
                "invocation_ids": [str(row.get("id") or "") for row in matching],
                "min_nesting_depth": min([int(finite_number(row.get("nesting_depth"), 0)) for row in matching], default=0),
                "max_nesting_depth": max([int(finite_number(row.get("nesting_depth"), 0)) for row in matching], default=0),
                "shared_definition": invocation_counts_by_xref.get(xref, 0) > 1,
                "per_instance_native_write_supported": invocation_counts_by_xref.get(xref, 0) <= 1,
            })
    return {
        "schema": "figureStudio.nativePdfInvocationIndex.v1",
        "page_xref": page_xref,
        "limits": {
            "max_depth": MAX_NATIVE_PDF_FORM_DEPTH,
            "max_invocations": MAX_NATIVE_PDF_FORM_INVOCATIONS,
            "max_resource_usages": MAX_NATIVE_PDF_RESOURCE_USAGES,
            "max_resource_scopes": MAX_NATIVE_PDF_RESOURCE_SCOPES,
        },
        "resource_scopes": scopes,
        "form_definitions": form_definitions,
        "form_invocations": invocations,
        "resource_usages": usages,
        "unresolved_resource_usages": unresolved_usages[:MAX_NATIVE_PDF_RESOURCE_ROWS],
        "resource_scope_count": len(scopes),
        "form_definition_count": len(form_definitions),
        "form_invocation_count": len(invocations),
        "resource_usage_count": len(usages),
        "nested_form_invocation_count": len([row for row in invocations if int(finite_number(row.get("nesting_depth"), 0)) > 1]),
        "shared_form_invocation_count": len([row for row in invocations if row.get("shared_definition")]),
        "cycle_count": cycle_count,
        "parser_complete": all(value[1] for value in scan_cache.values()),
        "truncated": scope_truncated or depth_truncated or usage_truncated or invocation_truncated,
        "truncation": {
            "resource_scopes": scope_truncated,
            "depth": depth_truncated,
            "resource_usages": usage_truncated,
            "form_invocations": invocation_truncated,
        },
        "full_native_equivalence": False,
    }


def page_form_xobject_invocation_ctms(doc: object, page: object) -> dict[str, list[list[float]]]:
    index = native_pdf_invocation_index(doc, page)
    placements: dict[str, list[list[float]]] = {}
    for row in index.get("form_invocations", []):
        if not isinstance(row, dict):
            continue
        name = str(row.get("name") or "")
        if name:
            placements.setdefault(name, []).append(row.get("page_ctm") or [1, 0, 0, 1, 0, 0])
    return placements


def page_form_xobject_first_invocation_ctms(doc: object, page: object) -> dict[str, list[float]]:
    return {name: matrices[0] for name, matrices in page_form_xobject_invocation_ctms(doc, page).items() if matrices}


def page_form_xobject_rows(
    doc: object,
    page: object,
    invocation_index: dict[str, object] | None = None,
) -> list[dict[str, object]]:
    graph = invocation_index if isinstance(invocation_index, dict) else native_pdf_invocation_index(doc, page)
    rows: list[dict[str, object]] = []
    for index, definition in enumerate(list(graph.get("form_definitions", []))[:MAX_NATIVE_PDF_RESOURCE_ROWS]):
        if not isinstance(definition, dict):
            continue
        xref = int(finite_number(definition.get("form_xref") or definition.get("target_xref"), 0))
        if xref <= 0:
            continue
        definition_binding_id = definition.get("binding_id") or definition.get("id") or ""
        invocations = [
            row for row in graph.get("form_invocations", [])
            if isinstance(row, dict) and row.get("binding_id") == definition_binding_id
        ]
        first = invocations[0] if invocations else {}
        stream_bytes = pdf_xref_stream_bytes(doc, xref)
        rows.append({
            "index": index,
            "id": definition.get("definition_id") or definition.get("id") or "",
            "definition_id": definition.get("definition_id") or definition.get("id") or "",
            "binding_id": definition_binding_id,
            "xref": xref,
            "name": str(definition.get("name") or ""),
            "invoker_xref": int(finite_number(definition.get("owner_xref"), 0)),
            "resource_owner_xref": int(finite_number(definition.get("owner_xref"), 0)),
            "resource_owner_scope": "form-xobject" if definition.get("owner_kind") == "form" else "page",
            "kind": "Form",
            "subtype": "Form",
            "byte_length": len(stream_bytes),
            "page_ctm": first.get("page_ctm") or definition.get("form_matrix") or [1, 0, 0, 1, 0, 0],
            "form_matrix": definition.get("form_matrix") or pdf_form_matrix(doc, xref),
            "form_bbox": definition.get("form_bbox") or pdf_form_bbox(doc, xref),
            "page_bbox": first.get("page_bbox"),
            "invocation_count": len(invocations),
            "invocations": invocations,
            "min_nesting_depth": int(finite_number(definition.get("min_nesting_depth"), 0)),
            "max_nesting_depth": int(finite_number(definition.get("max_nesting_depth"), 0)),
            "shared_definition": bool(definition.get("shared_definition")),
            "per_instance_native_write_supported": bool(definition.get("per_instance_native_write_supported")),
            "editable_content_stream": bool(stream_bytes),
        })
    return rows


def editable_pdf_content_stream_target(doc: object, page: object, target_xref: int) -> dict[str, object]:
    if target_xref <= 0:
        return {"editable": False, "scope": ""}
    if target_xref in page_content_xrefs(page):
        return {
            "editable": True,
            "scope": "page-content-stream",
            "target_content_stream_scope": "page-content-stream",
            "target_xobject_xref": 0,
            "target_xobject_name": "",
        }
    for row in page_form_xobject_rows(doc, page):
        if int(finite_number(row.get("xref"), 0)) != target_xref:
            continue
        if not row.get("editable_content_stream"):
            return {"editable": False, "scope": "form-xobject-content-stream"}
        return {
            "editable": True,
            "scope": "form-xobject-content-stream",
            "target_content_stream_scope": "form-xobject-content-stream",
            "target_xobject_xref": target_xref,
            "target_xobject_name": row.get("name") or "",
            "target_xobject_subtype": row.get("subtype") or row.get("kind") or "",
        }
    source = pdf_xref_object_source(doc, target_xref)
    if pdf_xobject_subtype(source) == "Form" and pdf_xref_stream_bytes(doc, target_xref):
        return {
            "editable": True,
            "scope": "form-xobject-content-stream",
            "target_content_stream_scope": "form-xobject-content-stream",
            "target_xobject_xref": target_xref,
            "target_xobject_name": "",
            "target_xobject_subtype": "Form",
        }
    return {"editable": False, "scope": ""}


def editable_pdf_content_stream_xrefs(doc: object, page: object) -> list[int]:
    xrefs = list(page_content_xrefs(page))
    for row in page_form_xobject_rows(doc, page):
        xref = int(finite_number(row.get("xref"), 0))
        if xref > 0 and row.get("editable_content_stream") and xref not in xrefs:
            xrefs.append(xref)
    return xrefs


def normalize_pdf_blend_mode(value: object, fallback: str = "Normal") -> str:
    text = str(value or "").strip().lstrip("/")
    key = re.sub(r"[^a-z0-9]+", "", text.lower())
    return PDF_BLEND_MODE_LOOKUP.get(key, fallback)


def parse_pdf_scalar_after_key(source: str, key: str) -> float | None:
    match = re.search(rf"/{re.escape(key)}\s+([-+]?\d*\.?\d+)", source)
    if not match:
        return None
    return finite_number(match.group(1), 0)


def parse_pdf_number_array_after_key(source: str, key: str) -> list[float]:
    match = re.search(rf"/{re.escape(key)}\s*\[([^\]]*)\]", source, re.DOTALL)
    if not match:
        return []
    return [
        finite_number(value, 0)
        for value in re.findall(r"[-+]?\d*\.?\d+", match.group(1))
    ]


def parse_pdf_boolean_array_after_key(source: str, key: str) -> list[bool]:
    match = re.search(rf"/{re.escape(key)}\s*\[([^\]]*)\]", source, re.DOTALL)
    if not match:
        return []
    values = re.findall(r"\b(true|false)\b", match.group(1), re.IGNORECASE)
    return [value.lower() == "true" for value in values]


def parse_pdf_smask_value(source: str) -> dict[str, object]:
    match = re.search(r"/SMask\s+(?P<value>/[A-Za-z0-9]+|\d+\s+\d+\s+R)", source)
    if not match:
        return {
            "has_soft_mask": False,
            "soft_mask": "",
            "soft_mask_xref": 0,
        }
    value = match.group("value").strip()
    xref_match = re.match(r"(\d+)\s+\d+\s+R", value)
    return {
        "has_soft_mask": value != "/None",
        "soft_mask": value,
        "soft_mask_xref": int(finite_number(xref_match.group(1), 0)) if xref_match else 0,
    }


def parse_extgstate_resource_map(doc: object, page: object) -> dict[str, int]:
    page_xref = int(finite_number(getattr(page, "xref", 0), 0))
    if page_xref <= 0:
        return {}
    resource_map, _dictionary_xref, _complete = pdf_resource_ref_map(doc, page_xref, "ExtGState")
    return resource_map


def native_pdf_resource_bindings(
    invocation_index: dict[str, object] | None,
    kind: str,
) -> list[dict[str, object]]:
    if not isinstance(invocation_index, dict):
        return []
    invocations = [row for row in invocation_index.get("form_invocations", []) if isinstance(row, dict)]
    usages = [row for row in invocation_index.get("resource_usages", []) if isinstance(row, dict)]
    rows: list[dict[str, object]] = []
    for scope in invocation_index.get("resource_scopes", []):
        if not isinstance(scope, dict):
            continue
        owner_xref = int(finite_number(scope.get("owner_xref"), 0))
        owner_invocations = [row for row in invocations if int(finite_number(row.get("form_xref"), 0)) == owner_xref]
        for binding in scope.get("bindings", []):
            if not isinstance(binding, dict) or binding.get("kind") != kind:
                continue
            binding_id = str(binding.get("id") or "")
            binding_usages = [row for row in usages if row.get("binding_id") == binding_id]
            rows.append({
                **binding,
                "resource_scope_id": scope.get("id") or "",
                "resource_owner_scope": "form-xobject" if scope.get("owner_kind") == "form" else "page",
                "resource_owner_xref": owner_xref,
                "resource_usage_ids": [str(row.get("id") or "") for row in binding_usages],
                "content_stream_refs": sorted({str(row.get("stream_xref") or "") for row in binding_usages if row.get("stream_xref")}),
                "owner_form_invocation_ids": [str(row.get("id") or "") for row in owner_invocations],
                "owner_form_invocation_paths": [str(row.get("invocation_path") or "") for row in owner_invocations],
                "owner_form_invocation_count": len(owner_invocations),
                "shared_owner_form_definition": len(owner_invocations) > 1,
                "per_instance_native_write_supported": len(owner_invocations) <= 1,
            })
    return rows


def decode_pdf_name(value: object) -> str:
    source = str(value or "")
    output = bytearray()
    index = 0
    while index < len(source):
        if index + 2 < len(source) and source[index] == "#" and re.fullmatch(r"[0-9A-Fa-f]{2}", source[index + 1:index + 3]):
            output.append(int(source[index + 1:index + 3], 16))
            index += 3
            continue
        output.extend(source[index].encode("latin-1", errors="replace"))
        index += 1
    try:
        return output.decode("utf-8")
    except UnicodeDecodeError:
        return output.decode("latin-1", errors="replace")


def pdf_color_space_alternate_value(value: object) -> tuple[str, int]:
    source = str(value or "").strip()
    xref_match = re.fullmatch(r"(\d+)\s+\d+\s+R", source)
    if xref_match:
        return f"xref:{xref_match.group(1)}", int(xref_match.group(1))
    name_match = re.fullmatch(r"/([^\s\[\]<>/()]+)", source)
    return (decode_pdf_name(name_match.group(1)), 0) if name_match else (source[:80], 0)


def pdf_xref_stream_sha256(doc: object, xref: int) -> str:
    if xref <= 0:
        return ""
    try:
        stream = bytes(doc.xref_stream(xref) or b"")
    except Exception:  # noqa: BLE001
        stream = b""
    return hashlib.sha256(stream).hexdigest() if stream else ""


def pdf_alternate_color_component_count(color_space: str) -> int:
    return {
        "DeviceGray": 1,
        "DeviceRGB": 3,
        "DeviceCMYK": 4,
    }.get(str(color_space or ""), 0)


def pdf_tint_preview_contract(
    doc: object,
    model: str,
    alternate_space: str,
    tint_transform_xref: int,
    expected_input_count: int = 0,
) -> dict[str, object]:
    contract: dict[str, object] = {
        "schema": "figureStudio.nativePdfTintPreviewContract.v1",
        "status": "unsupported",
        "supported": False,
        "function_type": 0,
        "alternate_space": alternate_space,
        "input_count": 0,
        "output_count": pdf_alternate_color_component_count(alternate_space),
    }
    if model not in {"Separation", "DeviceN"} or tint_transform_xref <= 0 or contract["output_count"] <= 0:
        contract["reason"] = "unsupported-color-space-chain"
        return contract
    source = pdf_xref_object_source(doc, tint_transform_xref)
    function_type = int(finite_number(parse_pdf_scalar_after_key(source, "FunctionType"), 0))
    contract["function_type"] = function_type
    output_count = int(contract["output_count"])
    if model == "Separation" and function_type == 2:
        c0 = parse_pdf_number_array_after_key(source, "C0") or [0.0] * output_count
        c1 = parse_pdf_number_array_after_key(source, "C1") or [1.0] * output_count
        domain = parse_pdf_number_array_after_key(source, "Domain")
        value_range = parse_pdf_number_array_after_key(source, "Range")
        exponent = finite_number(parse_pdf_scalar_after_key(source, "N"), -1)
        if (
            expected_input_count not in {0, 1}
            or len(c0) != output_count
            or len(c1) != output_count
            or len(domain) != 2
            or (value_range and len(value_range) != output_count * 2)
            or exponent <= 0
        ):
            contract["reason"] = "unsupported-type2-function-shape"
            return contract
        contract.update({
            "status": "supported",
            "supported": True,
            "input_count": 1,
            "domain": domain,
            "range": value_range,
            "c0": c0,
            "c1": c1,
            "exponent": exponent,
        })
        return contract
    if model == "DeviceN" and function_type == 0:
        size = [int(finite_number(value, 0)) for value in parse_pdf_number_array_after_key(source, "Size")]
        input_count = len(size)
        domain = parse_pdf_number_array_after_key(source, "Domain")
        value_range = parse_pdf_number_array_after_key(source, "Range")
        encode = parse_pdf_number_array_after_key(source, "Encode") or [
            value
            for dimension in size
            for value in (0.0, float(max(0, dimension - 1)))
        ]
        decode = parse_pdf_number_array_after_key(source, "Decode") or value_range
        bits_per_sample = int(finite_number(parse_pdf_scalar_after_key(source, "BitsPerSample"), 0))
        order = int(finite_number(parse_pdf_scalar_after_key(source, "Order"), 1))
        try:
            samples = bytes(doc.xref_stream(tint_transform_xref) or b"")
        except Exception:  # noqa: BLE001
            samples = b""
        expected_values = math.prod(size) * output_count if size and all(value > 0 for value in size) else 0
        if (
            input_count <= 0
            or input_count > 4
            or expected_input_count <= 0
            or input_count != expected_input_count
            or bits_per_sample != 8
            or order != 1
            or len(domain) != input_count * 2
            or len(encode) != input_count * 2
            or len(decode) != output_count * 2
            or len(value_range) != output_count * 2
            or expected_values <= 0
            or expected_values > 16384
            or len(samples) != expected_values
        ):
            contract["reason"] = "unsupported-sampled-function-shape"
            contract["sample_value_count"] = len(samples)
            return contract
        contract.update({
            "status": "supported",
            "supported": True,
            "input_count": input_count,
            "domain": domain,
            "range": value_range,
            "size": size,
            "bits_per_sample": bits_per_sample,
            "order": order,
            "encode": encode,
            "decode": decode,
            "sample_values": [round(value / 255, 6) for value in samples],
            "sample_value_count": len(samples),
        })
        return contract
    contract["reason"] = "unsupported-tint-function-type"
    return contract


def color_space_resource_rows(
    doc: object,
    page_id: str,
    invocation_index: dict[str, object] | None = None,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    bindings = native_pdf_resource_bindings(invocation_index, "colorspace")
    for index, binding in enumerate(bindings[:MAX_NATIVE_PDF_RESOURCE_ROWS]):
        xref = int(finite_number(binding.get("target_xref"), 0))
        source = pdf_xref_object_source(doc, xref) or str(binding.get("direct_definition") or "")
        model_match = re.search(r"\[\s*/(ICCBased|Separation|DeviceN|Pattern)\b", source)
        if not model_match:
            continue
        model = model_match.group(1)
        component_count = 0
        colorant_names: list[str] = []
        colorant_names_raw: list[str] = []
        alternate_space = ""
        alternate_space_xref = 0
        icc_profile_xref = 0
        icc_profile_component_count = 0
        icc_profile_alternate = ""
        icc_profile_alternate_xref = 0
        tint_transform_xref = 0
        tint_transform_function_type = 0
        referenced_object_sha256 = ""
        referenced_stream_sha256 = ""
        inspection_complete = False

        if model == "ICCBased":
            profile_match = re.search(r"/ICCBased\s+(\d+)\s+\d+\s+R", source)
            icc_profile_xref = int(profile_match.group(1)) if profile_match else 0
            profile_source = pdf_xref_object_source(doc, icc_profile_xref)
            icc_profile_component_count = int(finite_number(parse_pdf_scalar_after_key(profile_source, "N"), 0))
            component_count = icc_profile_component_count
            alternate_match = re.search(r"/Alternate\s+(?P<value>/[^\s\[\]<>/()]+|\d+\s+\d+\s+R)", profile_source)
            if alternate_match:
                icc_profile_alternate, icc_profile_alternate_xref = pdf_color_space_alternate_value(alternate_match.group("value"))
            alternate_space = icc_profile_alternate
            alternate_space_xref = icc_profile_alternate_xref
            referenced_object_sha256 = hashlib.sha256(profile_source.encode("utf-8", errors="ignore")).hexdigest() if profile_source else ""
            referenced_stream_sha256 = pdf_xref_stream_sha256(doc, icc_profile_xref)
            inspection_complete = icc_profile_xref > 0 and component_count in {1, 3, 4} and bool(referenced_stream_sha256)
        elif model == "Separation":
            separation_match = re.search(
                r"/Separation\s*/([^\s\[\]<>/()]+)\s*(?P<alternate>/[^\s\[\]<>/()]+|\d+\s+\d+\s+R)\s+(?P<tint>\d+)\s+\d+\s+R",
                source,
                re.DOTALL,
            )
            if separation_match:
                colorant_names_raw = [separation_match.group(1)]
                colorant_names = [decode_pdf_name(value) for value in colorant_names_raw]
                alternate_space, alternate_space_xref = pdf_color_space_alternate_value(separation_match.group("alternate"))
                tint_transform_xref = int(separation_match.group("tint"))
            component_count = 1
            tint_source = pdf_xref_object_source(doc, tint_transform_xref)
            tint_transform_function_type = int(finite_number(parse_pdf_scalar_after_key(tint_source, "FunctionType"), 0))
            referenced_object_sha256 = hashlib.sha256(tint_source.encode("utf-8", errors="ignore")).hexdigest() if tint_source else ""
            inspection_complete = bool(colorant_names and alternate_space and tint_transform_xref > 0 and tint_source)
        elif model == "DeviceN":
            device_n_match = re.search(
                r"/DeviceN\s*\[\s*(?P<names>[^\]]*)\]\s*(?P<alternate>/[^\s\[\]<>/()]+|\d+\s+\d+\s+R)\s+(?P<tint>\d+)\s+\d+\s+R",
                source,
                re.DOTALL,
            )
            if device_n_match:
                colorant_names_raw = re.findall(r"/([^\s\[\]<>/()]+)", device_n_match.group("names"))
                colorant_names = [decode_pdf_name(value) for value in colorant_names_raw]
                alternate_space, alternate_space_xref = pdf_color_space_alternate_value(device_n_match.group("alternate"))
                tint_transform_xref = int(device_n_match.group("tint"))
            component_count = len(colorant_names)
            tint_source = pdf_xref_object_source(doc, tint_transform_xref)
            tint_transform_function_type = int(finite_number(parse_pdf_scalar_after_key(tint_source, "FunctionType"), 0))
            referenced_object_sha256 = hashlib.sha256(tint_source.encode("utf-8", errors="ignore")).hexdigest() if tint_source else ""
            inspection_complete = component_count > 0 and bool(alternate_space and tint_transform_xref > 0 and tint_source)

        tint_preview_contract = pdf_tint_preview_contract(
            doc,
            model,
            alternate_space,
            tint_transform_xref,
            component_count,
        )
        resource_name = str(binding.get("name") or "")
        usage_ids = [str(value) for value in binding.get("resource_usage_ids", []) if value]
        preserve_only = model in {"ICCBased", "Separation", "DeviceN"}
        rows.append({
            "schema": "figureStudio.nativePdfColorSpaceResource.v1",
            "id": str(binding.get("id") or f"{page_id}-colorspace-{index}-xref-{xref}"),
            "binding_id": str(binding.get("id") or ""),
            "xref": xref,
            "resource_name": resource_name,
            "resource_name_raw": str(binding.get("raw_name") or resource_name),
            "resource_names": [resource_name] if resource_name else [],
            "definition_kind": binding.get("definition_kind") or "indirect-object",
            "definition_sha256": binding.get("definition_sha256") or "",
            "resource_type": "colorspace",
            "native_color_model": model,
            "component_count": component_count,
            "colorant_names": colorant_names,
            "colorant_names_raw": colorant_names_raw,
            "alternate_space": alternate_space,
            "alternate_space_xref": alternate_space_xref,
            "icc_profile_xref": icc_profile_xref,
            "icc_profile_component_count": icc_profile_component_count,
            "icc_profile_alternate": icc_profile_alternate,
            "icc_profile_alternate_xref": icc_profile_alternate_xref,
            "icc_profile_object_sha256": referenced_object_sha256 if model == "ICCBased" else "",
            "icc_profile_stream_sha256": referenced_stream_sha256 if model == "ICCBased" else "",
            "tint_transform_xref": tint_transform_xref,
            "tint_transform_function_type": tint_transform_function_type,
            "tint_transform_object_sha256": referenced_object_sha256 if model in {"Separation", "DeviceN"} else "",
            "tint_transform_stream_sha256": pdf_xref_stream_sha256(doc, tint_transform_xref) if model in {"Separation", "DeviceN"} else "",
            "tint_preview_contract": tint_preview_contract,
            "selected_use_tint_mutation_supported": bool(tint_preview_contract.get("supported")),
            "resource_usage_ids": usage_ids,
            "resource_usage_count": len(usage_ids),
            "resource_scope_id": binding.get("resource_scope_id") or "",
            "resource_owner_scope": binding.get("resource_owner_scope") or "page",
            "resource_owner_xref": int(finite_number(binding.get("resource_owner_xref"), 0)),
            "content_stream_refs": binding.get("content_stream_refs") or [],
            "owner_form_invocation_ids": binding.get("owner_form_invocation_ids") or [],
            "owner_form_invocation_paths": binding.get("owner_form_invocation_paths") or [],
            "owner_form_invocation_count": int(finite_number(binding.get("owner_form_invocation_count"), 0)),
            "shared_owner_form_definition": bool(binding.get("shared_owner_form_definition")),
            "per_instance_native_write_supported": False,
            "object_sha256": hashlib.sha256(source.encode("utf-8", errors="ignore")).hexdigest() if source else "",
            "inspection_status": "proven-native-resource" if inspection_complete else "bounded-resource-review",
            "inspection_complete": inspection_complete,
            "preserve_only": preserve_only,
            "mutation_supported": False,
            "full_native_equivalence": False,
            "mutation_status": (
                "source color space, alternate ownership, and component usage inspected; native mutation is preserve-only"
                if preserve_only
                else "pattern color-space identity preserved; native pattern paint mutation is not supported"
            ),
        })
    return rows


def link_named_color_space_paint_contexts(
    stream_descriptors: list[dict[str, object]],
    owner_xref: int,
    color_spaces: list[dict[str, object]],
    invocation_index: dict[str, object],
) -> None:
    owner_resources = [
        row for row in color_spaces
        if int(finite_number(row.get("resource_owner_xref"), 0)) == owner_xref
    ]
    index_complete = invocation_index.get("parser_complete") is True and invocation_index.get("truncated") is not True
    for stream in stream_descriptors:
        for operator_run in stream.get("operator_runs", []):
            if not isinstance(operator_run, dict):
                continue
            sequence = operator_run.get("path_sequence") if isinstance(operator_run.get("path_sequence"), dict) else None
            paint_context = sequence.get("paint_context") if isinstance(sequence, dict) and isinstance(sequence.get("paint_context"), dict) else None
            if not paint_context:
                continue
            statuses: list[str] = []
            for channel in ("fill", "stroke"):
                color = paint_context.get(channel) if isinstance(paint_context.get(channel), dict) else None
                if not color or color.get("preserve_only") is not True:
                    continue
                resource_name = str(color.get("source_color_space_resource_name") or "")
                candidates = [row for row in owner_resources if str(row.get("resource_name") or "") == resource_name]
                components = [finite_number(value, 0) for value in color.get("source_components", [])]
                resource = candidates[0] if len(candidates) == 1 else None
                component_count = int(finite_number(resource.get("component_count"), 0)) if resource else 0
                component_shape_valid = (
                    component_count > 0
                    and len(components) == component_count
                    and all(math.isfinite(value) for value in components)
                )
                proven = bool(
                    resource
                    and index_complete
                    and resource.get("inspection_complete") is True
                    and int(finite_number(resource.get("resource_usage_count"), 0)) > 0
                    and component_shape_valid
                    and paint_context.get("graphics_state_balanced") is True
                    and paint_context.get("exact") is True
                )
                color.update({
                    "syntax_status": "exact" if paint_context.get("exact") is True else "bounded",
                    "resource_status": "proven-native-resource" if proven else "unresolved-or-bounded-resource",
                    "inspection_status": "proven-preserve-only" if proven else "preserve-only-review",
                    "color_space_resource_id": str(resource.get("id") or "") if resource else "",
                    "color_space_binding_id": str(resource.get("binding_id") or "") if resource else "",
                    "resolved_color_space_model": str(resource.get("native_color_model") or "") if resource else "",
                    "resolved_component_count": component_count,
                    "component_shape_valid": component_shape_valid,
                    "appearance_status": "partial" if paint_context.get("active_extgstate_resource_names") else "source-color-proven",
                    "mutation_supported": False,
                    "preserve_only": True,
                })
                statuses.append(str(color.get("inspection_status") or "preserve-only-review"))
            if statuses:
                paint_context["named_color_inspection_status"] = (
                    "proven-preserve-only" if all(status == "proven-preserve-only" for status in statuses) else "preserve-only-review"
                )
                paint_context["named_color_mutation_supported"] = False


def extgstate_usage_by_resource(doc: object, content_streams: list[dict[str, object]]) -> dict[str, list[str]]:
    usage: dict[str, list[str]] = {}
    for stream in content_streams:
        xref = int(finite_number(stream.get("xref"), 0))
        if xref <= 0:
            continue
        try:
            text = bytes(doc.xref_stream(xref) or b"").decode("latin-1", errors="ignore")
        except Exception:  # noqa: BLE001
            continue
        for match in re.finditer(r"/([A-Za-z0-9_.-]+)\s+gs\b", text):
            usage.setdefault(match.group(1), []).append(str(stream.get("id") or xref))
    return usage


def extgstate_resource_rows(
    doc: object,
    page: object,
    page_id: str,
    content_streams: list[dict[str, object]],
    invocation_index: dict[str, object] | None = None,
) -> list[dict[str, object]]:
    scoped_bindings = native_pdf_resource_bindings(invocation_index, "extgstate")
    resource_map = parse_extgstate_resource_map(doc, page)
    usage = extgstate_usage_by_resource(doc, content_streams)
    candidate_xrefs = {int(finite_number(row.get("target_xref"), 0)) for row in scoped_bindings}
    candidate_xrefs.discard(0)
    candidate_xrefs.update(resource_map.values())
    if not candidate_xrefs:
        try:
            xref_limit = int(finite_number(doc.xref_length() if hasattr(doc, "xref_length") else 0, 0))
        except Exception:  # noqa: BLE001
            xref_limit = 0
        for xref in range(1, xref_limit):
            try:
                source = str(doc.xref_object(xref, compressed=False) or "")
            except Exception:  # noqa: BLE001
                continue
            if "/Type /ExtGState" in source or "/BM " in source:
                candidate_xrefs.add(xref)
    rows: list[dict[str, object]] = []
    candidates = scoped_bindings or [
        {
            "target_xref": xref,
            "name": next((name for name, mapped_xref in resource_map.items() if mapped_xref == xref), ""),
            "resource_scope_id": "",
            "resource_owner_scope": "page",
            "resource_owner_xref": int(finite_number(getattr(page, "xref", 0), 0)),
            "resource_usage_ids": [],
            "content_stream_refs": [],
            "owner_form_invocation_ids": [],
            "owner_form_invocation_paths": [],
            "owner_form_invocation_count": 0,
            "shared_owner_form_definition": False,
            "per_instance_native_write_supported": True,
        }
        for xref in sorted(candidate_xrefs)
    ]
    for index, binding in enumerate(candidates[:MAX_NATIVE_PDF_RESOURCE_ROWS]):
        xref = int(finite_number(binding.get("target_xref"), 0))
        try:
            source = str(doc.xref_object(xref, compressed=False) or "")
        except Exception:  # noqa: BLE001
            continue
        if "/Type /ExtGState" not in source and "/BM " not in source and "/ca " not in source and "/CA " not in source and "/SMask " not in source:
            continue
        resource_names = [str(binding.get("name") or "")]
        resource_names.extend(name for name, mapped_xref in resource_map.items() if mapped_xref == xref and name not in resource_names)
        resource_names = [name for name in resource_names if name]
        blend_match = re.search(r"/BM\s*/([A-Za-z0-9]+)", source)
        blend_mode = normalize_pdf_blend_mode(blend_match.group(1), "") if blend_match else ""
        smask = parse_pdf_smask_value(source)
        content_refs: list[str] = [str(value) for value in binding.get("content_stream_refs", []) if value]
        for name in resource_names:
            content_refs.extend(usage.get(name, []))
        rows.append({
            "id": str(binding.get("id") or f"{page_id}-extgstate-{index}-xref-{xref}"),
            "binding_id": str(binding.get("id") or ""),
            "xref": xref,
            "resource_name": resource_names[0] if resource_names else "",
            "resource_names": resource_names,
            "resource_type": "extgstate",
            "semantic_feature_type": "blend_mode" if blend_mode else "graphics_state",
            "blend_mode": blend_mode,
            "has_blend_mode": bool(blend_mode),
            "fill_alpha": parse_pdf_scalar_after_key(source, "ca"),
            "stroke_alpha": parse_pdf_scalar_after_key(source, "CA"),
            "line_width_override": parse_pdf_scalar_after_key(source, "LW"),
            "line_cap_override": parse_pdf_scalar_after_key(source, "LC"),
            "line_join_override": parse_pdf_scalar_after_key(source, "LJ"),
            "miter_limit_override": parse_pdf_scalar_after_key(source, "ML"),
            "has_line_width_override": bool(re.search(r"/LW\s", source)),
            "has_line_cap_override": bool(re.search(r"/LC\s", source)),
            "has_line_join_override": bool(re.search(r"/LJ\s", source)),
            "has_miter_limit_override": bool(re.search(r"/ML\s", source)),
            "has_dash_override": bool(re.search(r"/D\s", source)),
            "has_line_style_override": bool(re.search(r"/(?:LW|LC|LJ|ML|D)\s", source)),
            "overprint_fill": bool(re.search(r"/op\s+true\b", source)),
            "overprint_stroke": bool(re.search(r"/OP\s+true\b", source)),
            "has_overprint": bool(re.search(r"/(?:OP|op)\s+true\b", source)),
            "has_soft_mask": smask["has_soft_mask"],
            "soft_mask": smask["soft_mask"],
            "soft_mask_xref": smask["soft_mask_xref"],
            "content_stream_refs": sorted(set(content_refs)),
            "resource_usage_ids": binding.get("resource_usage_ids") or [],
            "resource_scope_id": binding.get("resource_scope_id") or "",
            "resource_owner_scope": binding.get("resource_owner_scope") or "page",
            "resource_owner_xref": int(finite_number(binding.get("resource_owner_xref"), 0)),
            "owner_form_invocation_ids": binding.get("owner_form_invocation_ids") or [],
            "owner_form_invocation_paths": binding.get("owner_form_invocation_paths") or [],
            "owner_form_invocation_count": int(finite_number(binding.get("owner_form_invocation_count"), 0)),
            "shared_owner_form_definition": bool(binding.get("shared_owner_form_definition")),
            "per_instance_native_write_supported": bool(binding.get("per_instance_native_write_supported", True)),
            "native_write_scope": "shared-resource-definition" if binding.get("shared_owner_form_definition") else "resource-definition",
            "object_sha256": hashlib.sha256(source.encode("utf-8", errors="ignore")).hexdigest() if source else "",
            "mutation_status": (
                "bounded ExtGState /BM resource rewrite supported"
                if blend_mode
                else "resource identity preserved; non-blend graphics state rewrite still requires native compiler work"
            ),
        })
    return rows


def skip_pdf_literal_string(text: str, index: int) -> int:
    depth = 1
    index += 1
    while index < len(text) and depth > 0:
        char = text[index]
        if char == "\\":
            index += 2
            continue
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
        index += 1
    return index


def scan_pdf_content_stream_tokens(stream_bytes: bytes) -> tuple[str, list[tuple[str, int]]]:
    text = stream_bytes.decode("latin-1", errors="ignore")
    tokens: list[tuple[str, int]] = []
    delimiters = set("[]<>(){}%")
    index = 0
    while index < len(text):
        char = text[index]
        if char.isspace():
            index += 1
            continue
        if char == "%":
            while index < len(text) and text[index] not in "\r\n":
                index += 1
            continue
        if char == "(":
            index = skip_pdf_literal_string(text, index)
            continue
        if char == "<" and index + 1 < len(text) and text[index + 1] != "<":
            index += 1
            while index < len(text) and text[index] != ">":
                index += 1
            index += 1
            continue
        if char == "<" and index + 1 < len(text) and text[index + 1] == "<":
            tokens.append(("<<", index))
            index += 2
            continue
        if char == ">" and index + 1 < len(text) and text[index + 1] == ">":
            tokens.append((">>", index))
            index += 2
            continue
        if char in "[]{}":
            tokens.append((char, index))
            index += 1
            continue
        if char == "/":
            start = index
            index += 1
            while index < len(text) and not text[index].isspace() and text[index] not in delimiters and text[index] != "/":
                index += 1
            tokens.append((text[start:index], start))
            continue
        start = index
        while index < len(text) and not text[index].isspace() and text[index] not in delimiters and text[index] != "/":
            index += 1
        if index == start:
            tokens.append((char, index))
            index += 1
        else:
            tokens.append((text[start:index], start))
    return text, tokens


def compact_pdf_stream_context(text: str, start: int, end: int, pad: int = 54) -> str:
    left = max(0, start - pad)
    right = min(len(text), end + pad)
    return re.sub(r"\s+", " ", text[left:right]).strip()[:160]


def pdf_operator_resource_name(tokens: list[tuple[str, int]], token_index: int) -> str:
    for prior, _offset in reversed(tokens[max(0, token_index - 6):token_index]):
        if prior.startswith("/"):
            return prior[1:]
        if prior in {"BT", "ET", "q", "Q", "cm", "m", "l", "c", "re", "W", "W*", "n", "S", "f", "B", "sh", "Do", "gs"}:
            break
    return ""


def pdf_content_operator_runs_from_tokens(tokens: list[tuple[str, int]]) -> list[dict[str, object]]:
    runs: list[dict[str, object]] = []
    operator_index = -1
    for token_position, (token, offset) in enumerate(tokens):
        category = PDF_CONTENT_STREAM_OPERATOR_CATEGORIES.get(token)
        if not category:
            continue
        operator_index += 1
        runs.append({
            "token_position": token_position,
            "operator_index": operator_index,
            "operator": token,
            "category": category,
            "byte_offset": offset,
        })
    return runs


def pdf_dash_operands_before(tokens: list[tuple[str, int]], token_position: int) -> tuple[list[float], float] | None:
    if token_position < 3:
        return None
    phase_token, _phase_offset = tokens[token_position - 1]
    close_token, _close_offset = tokens[token_position - 2]
    if not is_pdf_numeric_token(phase_token) or close_token != "]":
        return None
    open_position = token_position - 3
    while open_position >= 0 and tokens[open_position][0] != "[":
        if not is_pdf_numeric_token(tokens[open_position][0]):
            return None
        open_position -= 1
    if open_position < 0:
        return None
    dash_tokens = tokens[open_position + 1:token_position - 2]
    if not all(is_pdf_numeric_token(token) for token, _offset in dash_tokens):
        return None
    dash_array = [finite_number(token, 0) for token, _offset in dash_tokens]
    if len(dash_array) > 24 or any(value < 0 for value in dash_array):
        return None
    return dash_array, finite_number(phase_token, 0)


def pdf_device_color_preview_rgb(color_space: str, components: list[float]) -> list[float]:
    values = [max(0.0, min(1.0, finite_number(value, 0))) for value in components]
    if color_space == "DeviceGray" and len(values) == 1:
        return [round(values[0], 4)] * 3
    if color_space == "DeviceRGB" and len(values) == 3:
        return [round(value, 4) for value in values]
    if color_space == "DeviceCMYK" and len(values) == 4:
        cyan, magenta, yellow, black = values
        return [
            round(1 - min(1.0, cyan + black), 4),
            round(1 - min(1.0, magenta + black), 4),
            round(1 - min(1.0, yellow + black), 4),
        ]
    return [0.0, 0.0, 0.0]


def pdf_numeric_operand_sequence_before(
    tokens: list[tuple[str, int]],
    token_position: int,
    limit: int = 32,
) -> list[float]:
    values: list[float] = []
    cursor = token_position - 1
    while cursor >= 0 and len(values) < limit:
        token = tokens[cursor][0]
        if not is_pdf_numeric_token(token):
            break
        values.insert(0, finite_number(token, 0))
        cursor -= 1
    return values


def pdf_path_paint_context_from_runs(
    tokens: list[tuple[str, int]],
    runs: list[dict[str, object]],
    run_position: int,
) -> dict[str, object] | None:
    if run_position < 0 or run_position >= len(runs):
        return None
    graphics_state_depth = 0
    for run in runs:
        operator = str(run.get("operator") or "")
        if operator == "q":
            graphics_state_depth += 1
        elif operator == "Q":
            graphics_state_depth -= 1
            if graphics_state_depth < 0:
                return None
    if graphics_state_depth != 0:
        return None
    first_path_position = run_position
    while first_path_position > 0 and str(runs[first_path_position - 1].get("category") or "") == "path":
        first_path_position -= 1
    last_path_position = run_position
    while last_path_position + 1 < len(runs) and str(runs[last_path_position + 1].get("category") or "") == "path":
        last_path_position += 1
    paint_position = last_path_position + 1
    if paint_position >= len(runs):
        return None
    paint_run = runs[paint_position]
    paint_operator = str(paint_run.get("operator") or "")
    if str(paint_run.get("category") or "") != "paint" or paint_operator not in PDF_PAINT_OPERATOR_TOKENS:
        return None

    def default_color(operator: str) -> dict[str, object]:
        return {
            "operator": operator,
            "operator_index": -1,
            "byte_offset": -1,
            "source_color_space": "DeviceGray",
            "source_components": [0.0],
            "source_rgb": [0.0, 0.0, 0.0],
            "source_origin": "unresolved_inherited",
            "localize_required": True,
        }

    def default_stroke_property(operator: str, source_value: float) -> dict[str, object]:
        return {
            "operator": operator,
            "operator_index": -1,
            "byte_offset": -1,
            "source_value": source_value,
            "source_origin": "unresolved_inherited",
            "localize_required": True,
        }

    def default_state() -> dict[str, object]:
        return {
            "fill": default_color("g"),
            "stroke": default_color("G"),
            "stroke_style": {
                "width": default_stroke_property("w", 1.0),
                "dash": {
                    "operator": "d",
                    "operator_index": -1,
                    "byte_offset": -1,
                    "source_dash_array": [],
                    "source_dash_phase": 0.0,
                    "source_origin": "unresolved_inherited",
                    "localize_required": True,
                },
                "cap": default_stroke_property("J", 0.0),
                "join": default_stroke_property("j", 0.0),
                "miter_limit": default_stroke_property("M", 10.0),
            },
            "extgstates": [],
            "extgstate_usages": [],
            "local_ctm": [1.0, 0.0, 0.0, 1.0, 0.0, 0.0],
        }

    state: dict[str, object] = default_state()
    stack: list[dict[str, object]] = []
    for prior_run in runs[:first_path_position]:
        operator = str(prior_run.get("operator") or "")
        token_position = int(finite_number(prior_run.get("token_position"), -1))
        if operator == "q":
            stack.append({
                "fill": dict(state["fill"]) if isinstance(state.get("fill"), dict) else None,
                "stroke": dict(state["stroke"]) if isinstance(state.get("stroke"), dict) else None,
                "stroke_style": {
                    key: dict(value) if isinstance(value, dict) else None
                    for key, value in (state.get("stroke_style") or {}).items()
                },
                "extgstates": list(state.get("extgstates") or []),
                "extgstate_usages": [dict(value) for value in (state.get("extgstate_usages") or []) if isinstance(value, dict)],
                "local_ctm": list(state.get("local_ctm") or [1, 0, 0, 1, 0, 0]),
            })
            continue
        if operator == "Q":
            state = stack.pop() if stack else default_state()
            continue
        if operator == "cm":
            values = pdf_numeric_operands_before(tokens, token_position, 6)
            if values is None:
                return None
            state["local_ctm"] = pdf_matrix_multiply(
                list(state.get("local_ctm") or [1, 0, 0, 1, 0, 0]),
                values,
            )
            continue
        if operator == "gs":
            resource_name = pdf_operator_resource_name(tokens, token_position)
            if resource_name:
                extgstates = list(state.get("extgstates") or [])
                if resource_name not in extgstates:
                    extgstates.append(resource_name)
                state["extgstates"] = extgstates
                usages = [dict(value) for value in (state.get("extgstate_usages") or []) if isinstance(value, dict)]
                usages.append({
                    "resource_name": resource_name,
                    "operator": "gs",
                    "operator_index": prior_run.get("operator_index"),
                    "byte_offset": prior_run.get("byte_offset"),
                })
                state["extgstate_usages"] = usages
            continue
        if operator in PDF_DEVICE_COLOR_OPERATOR_TOKENS:
            component_count = PDF_DEVICE_COLOR_OPERATOR_COMPONENTS[operator]
            values = pdf_numeric_operands_before(tokens, token_position, component_count)
            channel = "fill" if operator.islower() else "stroke"
            if values is None:
                state[channel] = None
                continue
            components = [round(value, 4) for value in values]
            color_space = PDF_DEVICE_COLOR_OPERATOR_SPACES[operator]
            state[channel] = {
                "operator": operator,
                "operator_index": prior_run.get("operator_index"),
                "byte_offset": prior_run.get("byte_offset"),
                "source_color_space": color_space,
                "source_components": components,
                "source_rgb": pdf_device_color_preview_rgb(color_space, components),
                "source_origin": "explicit",
            }
            continue
        if operator in {"cs", "CS"}:
            channel = "fill" if operator == "cs" else "stroke"
            resource_name = pdf_operator_resource_name(tokens, token_position)
            state[channel] = (
                {
                    "operator": operator,
                    "operator_index": prior_run.get("operator_index"),
                    "byte_offset": prior_run.get("byte_offset"),
                    "source_color_space": "NamedResource",
                    "source_color_space_resource_name": resource_name,
                    "source_color_space_operator": operator,
                    "source_color_space_operator_index": prior_run.get("operator_index"),
                    "source_color_space_byte_offset": prior_run.get("byte_offset"),
                    "source_components": [],
                    "source_rgb": [],
                    "source_origin": "explicit-resource-selection",
                    "preserve_only": True,
                    "mutation_supported": False,
                }
                if resource_name
                else None
            )
            continue
        if operator in {"sc", "SC", "scn", "SCN"}:
            channel = "fill" if operator.islower() else "stroke"
            selected_space = state.get(channel) if isinstance(state.get(channel), dict) else None
            components = pdf_numeric_operand_sequence_before(tokens, token_position)
            if not selected_space or not selected_space.get("source_color_space_resource_name") or not components:
                state[channel] = None
                continue
            state[channel] = {
                **selected_space,
                "operator": operator,
                "operator_index": prior_run.get("operator_index"),
                "byte_offset": prior_run.get("byte_offset"),
                "source_color_operator": operator,
                "source_components": [round(value, 6) for value in components],
                "source_origin": "explicit-resource-color",
                "preserve_only": True,
                "mutation_supported": False,
            }
            continue
        stroke_property = PDF_STROKE_STYLE_OPERATOR_PROPERTIES.get(operator)
        if not stroke_property:
            continue
        stroke_style = state.get("stroke_style") if isinstance(state.get("stroke_style"), dict) else {}
        base_context = {
            "operator": operator,
            "operator_index": prior_run.get("operator_index"),
            "byte_offset": prior_run.get("byte_offset"),
            "source_origin": "explicit",
        }
        if operator == "d":
            dash_operands = pdf_dash_operands_before(tokens, token_position)
            stroke_style[stroke_property] = (
                {**base_context, "source_dash_array": [round(value, 4) for value in dash_operands[0]], "source_dash_phase": round(dash_operands[1], 4)}
                if dash_operands is not None
                else None
            )
        else:
            values = pdf_numeric_operands_before(tokens, token_position, 1)
            value = values[0] if values else None
            valid = value is not None
            if operator in {"J", "j"}:
                valid = valid and float(value).is_integer() and int(value) in {0, 1, 2}
            elif operator == "w":
                valid = valid and value >= 0
            elif operator == "M":
                valid = valid and value >= 1
            stroke_style[stroke_property] = {**base_context, "source_value": round(value, 4)} if valid else None
        state["stroke_style"] = stroke_style

    uses_fill = paint_operator in {"f", "F", "f*", "B", "B*", "b", "b*"}
    uses_stroke = paint_operator in {"S", "s", "B", "B*", "b", "b*"}
    fill = state.get("fill") if uses_fill and isinstance(state.get("fill"), dict) else None
    stroke = state.get("stroke") if uses_stroke and isinstance(state.get("stroke"), dict) else None
    stroke_style = (
        {
            key: dict(value) if isinstance(value, dict) else None
            for key, value in (state.get("stroke_style") or {}).items()
        }
        if uses_stroke
        else {"width": None, "dash": None, "cap": None, "join": None, "miter_limit": None}
    )
    if not uses_fill and not uses_stroke:
        return None
    target_run = runs[run_position]
    first_run = runs[first_path_position]
    last_run = runs[last_path_position]
    return {
        "schema": "figureStudio.nativePdfPathPaintContext.v1",
        "exact": True,
        "fill": fill,
        "stroke": stroke,
        "stroke_style": stroke_style,
        "miter_limit": dict(stroke_style["miter_limit"]) if isinstance(stroke_style.get("miter_limit"), dict) else None,
        "path_sequence": {
            "first_operator_index": first_run.get("operator_index"),
            "last_operator_index": last_run.get("operator_index"),
            "target_operator_index": target_run.get("operator_index"),
            "target_operator": target_run.get("operator"),
            "target_operator_byte_offset": target_run.get("byte_offset"),
        },
        "paint_operator": {
            "operator": paint_operator,
            "operator_index": paint_run.get("operator_index"),
            "byte_offset": paint_run.get("byte_offset"),
        },
        "active_extgstate_resource_names": list(state.get("extgstates") or []),
        "active_extgstate_usages": [dict(value) for value in (state.get("extgstate_usages") or []) if isinstance(value, dict)],
        "local_ctm": [round(finite_number(value, 0), 6) for value in list(state.get("local_ctm") or [])[:6]],
        "local_state_materialization_supported": True,
        "graphics_state_balanced": True,
        "overprint_guard_required": bool(state.get("extgstates")),
        "device_color_spaces_supported": ["DeviceGray", "DeviceRGB", "DeviceCMYK"],
        "non_rgb_color_spaces_supported": True,
        "full_native_equivalence": False,
    }


def pdf_numeric_operands_before(tokens: list[tuple[str, int]], token_position: int, needed: int) -> list[float] | None:
    if needed <= 0:
        return []
    if token_position < needed:
        return None
    operand_tokens = tokens[token_position - needed:token_position]
    if not all(is_pdf_numeric_token(token) for token, _offset in operand_tokens):
        return None
    return [finite_number(token, 0) for token, _offset in operand_tokens]


def pdf_path_sequence_from_runs(tokens: list[tuple[str, int]], runs: list[dict[str, object]], run_position: int) -> dict[str, object] | None:
    if run_position < 0 or run_position >= len(runs):
        return None
    target_run = runs[run_position]
    if str(target_run.get("category") or "") != "path":
        return None
    first_run_position = run_position
    while first_run_position > 0 and str(runs[first_run_position - 1].get("category") or "") == "path":
        first_run_position -= 1
    last_run_position = run_position
    while last_run_position + 1 < len(runs) and str(runs[last_run_position + 1].get("category") or "") == "path":
        last_run_position += 1

    commands: list[list[object]] = []
    points: list[tuple[float, float]] = []
    operator_names: list[str] = []
    current: tuple[float, float] | None = None
    subpath_start: tuple[float, float] | None = None
    editable_anchor_count = 0
    control_handle_count = 0
    skipped_operator_count = 0
    first_byte_offset = -1
    last_byte_offset = -1
    for run in runs[first_run_position:last_run_position + 1]:
        operator = str(run.get("operator") or "")
        token_position = int(finite_number(run.get("token_position"), -1))
        operator_names.append(operator)
        if first_byte_offset < 0:
            indexes = path_geometry_operand_indexes(operator)
            if indexes:
                needed = max(indexes) + 1
                if token_position >= needed:
                    first_byte_offset = int(finite_number(tokens[token_position - needed][1], -1))
                else:
                    first_byte_offset = int(finite_number(run.get("byte_offset"), -1))
            else:
                first_byte_offset = int(finite_number(run.get("byte_offset"), -1))
        last_byte_offset = int(finite_number(run.get("byte_offset"), -1)) + len(operator)

        if operator == "h":
            if current is not None and subpath_start is not None:
                commands.append(["Z"])
                current = subpath_start
            continue
        if operator in {"m", "l"}:
            values = pdf_numeric_operands_before(tokens, token_position, 2)
            if not values:
                skipped_operator_count += 1
                continue
            point = (values[0], values[1])
            commands.append(["M" if operator == "m" or current is None else "L", round(point[0], 4), round(point[1], 4)])
            points.append(point)
            current = point
            if operator == "m" or subpath_start is None:
                subpath_start = point
            editable_anchor_count += 1
            continue
        if operator == "c":
            values = pdf_numeric_operands_before(tokens, token_position, 6)
            if not values:
                skipped_operator_count += 1
                continue
            c1 = (values[0], values[1])
            c2 = (values[2], values[3])
            end = (values[4], values[5])
            if current is None:
                commands.append(["M", round(end[0], 4), round(end[1], 4)])
                subpath_start = end
            else:
                commands.append(["C", round(c1[0], 4), round(c1[1], 4), round(c2[0], 4), round(c2[1], 4), round(end[0], 4), round(end[1], 4)])
                control_handle_count += 2
            points.extend([c1, c2, end])
            current = end
            editable_anchor_count += 1
            continue
        if operator in {"v", "y"}:
            values = pdf_numeric_operands_before(tokens, token_position, 4)
            if not values:
                skipped_operator_count += 1
                continue
            if operator == "v":
                c1 = current or (values[0], values[1])
                c2 = (values[0], values[1])
                end = (values[2], values[3])
            else:
                c1 = (values[0], values[1])
                end = (values[2], values[3])
                c2 = end
            if current is None:
                commands.append(["M", round(end[0], 4), round(end[1], 4)])
                subpath_start = end
            else:
                commands.append(["C", round(c1[0], 4), round(c1[1], 4), round(c2[0], 4), round(c2[1], 4), round(end[0], 4), round(end[1], 4)])
                control_handle_count += 2
            points.extend([c1, c2, end])
            current = end
            editable_anchor_count += 1
            continue
        if operator == "re":
            values = pdf_numeric_operands_before(tokens, token_position, 4)
            if not values:
                skipped_operator_count += 1
                continue
            x, y, width, height = values
            rect_points = [
                (x, y),
                (x + width, y),
                (x + width, y + height),
                (x, y + height),
            ]
            commands.extend([
                ["M", round(rect_points[0][0], 4), round(rect_points[0][1], 4)],
                ["L", round(rect_points[1][0], 4), round(rect_points[1][1], 4)],
                ["L", round(rect_points[2][0], 4), round(rect_points[2][1], 4)],
                ["L", round(rect_points[3][0], 4), round(rect_points[3][1], 4)],
                ["Z"],
            ])
            points.extend(rect_points)
            current = rect_points[0]
            subpath_start = rect_points[0]
            editable_anchor_count += 4
            continue
    if not commands:
        return None
    return {
        "schema": "figureStudio.nativePdfPathSequence.v1",
        "origin": "pdf-stream",
        "units": "pt",
        "commands": commands[:MAX_NATIVE_PDF_MUTATION_PATH_COMMANDS],
        "command_count": min(len(commands), MAX_NATIVE_PDF_MUTATION_PATH_COMMANDS),
        "operator_count": last_run_position - first_run_position + 1,
        "operators": operator_names,
        "first_operator_index": runs[first_run_position].get("operator_index"),
        "last_operator_index": runs[last_run_position].get("operator_index"),
        "first_byte_offset": first_byte_offset,
        "last_byte_offset": last_byte_offset,
        "target_operator_index": target_run.get("operator_index"),
        "target_operator": target_run.get("operator"),
        "target_operator_byte_offset": target_run.get("byte_offset"),
        "editable_anchor_count": editable_anchor_count,
        "control_handle_count": control_handle_count,
        "skipped_operator_count": skipped_operator_count,
        "bbox": path_geometry_bbox(points),
    }


def pdf_content_stream_operator_profile(stream_bytes: bytes) -> dict[str, object]:
    text, tokens = scan_pdf_content_stream_tokens(stream_bytes)
    inline_image_ambiguous = any(token in {"BI", "ID", "EI"} for token, _offset in tokens)
    all_runs = pdf_content_operator_runs_from_tokens(tokens)
    runs: list[dict[str, object]] = []
    categories: dict[str, int] = {}
    operator_total = len(all_runs)
    for run_position, run in enumerate(all_runs):
        token = str(run.get("operator") or "")
        offset = int(finite_number(run.get("byte_offset"), 0))
        token_index = int(finite_number(run.get("token_position"), -1))
        category = str(run.get("category") or "")
        categories[category] = categories.get(category, 0) + 1
        if len(runs) >= MAX_NATIVE_PDF_OPERATOR_RUNS:
            continue
        resource_name = pdf_operator_resource_name(tokens, token_index) if token in {"gs", "sh", "Tf", "Do"} else ""
        context_end = min(len(text), offset + len(token))
        row = {
            "id": f"op-{len(runs) + 1}-{offset}-{token.replace('*', 'star')}",
            "operator_index": run.get("operator_index"),
            "operator": token,
            "category": category,
            "byte_offset": offset,
            "resource_name": resource_name,
            "context": compact_pdf_stream_context(text, offset, context_end),
            "mutation_status": (
                "bounded clip-path disable rewrite supported"
                if category == "clip"
                else "operator identity exposed; arbitrary native operator mutation requires compiler work"
            ),
        }
        if category == "path" and token in PDF_PATH_GEOMETRY_OPERATOR_TOKENS:
            sequence = pdf_path_sequence_from_runs(tokens, all_runs, run_position)
            if sequence:
                paint_context = pdf_path_paint_context_from_runs(tokens, all_runs, run_position)
                if paint_context:
                    paint_operator = paint_context.get("paint_operator") if isinstance(paint_context.get("paint_operator"), dict) else {}
                    span_start = int(finite_number(sequence.get("first_byte_offset"), -1))
                    paint_offset = int(finite_number(paint_operator.get("byte_offset"), -1))
                    span_end = paint_offset + len(str(paint_operator.get("operator") or ""))
                    if span_start < 0 or span_end <= span_start or pdf_content_span_has_unknown_operator(stream_bytes, span_start, span_end):
                        paint_context["exact"] = False
                        paint_context["local_state_materialization_supported"] = False
                    sequence["paint_context"] = paint_context
                row["path_sequence"] = sequence
                row["mutation_status"] = (
                    "bounded native path anchor edit supported; contiguous path sequence can be replaced in place"
                )
        runs.append(row)
    paint_usage: dict[tuple[str, int, int], set[tuple[str, int, int]]] = {}
    stroke_style_usage: dict[tuple[str, int, int], set[tuple[str, int, int]]] = {}
    for row in runs:
        sequence = row.get("path_sequence") if isinstance(row.get("path_sequence"), dict) else None
        paint_context = sequence.get("paint_context") if isinstance(sequence, dict) and isinstance(sequence.get("paint_context"), dict) else None
        if not paint_context:
            continue
        paint = paint_context.get("paint_operator") if isinstance(paint_context.get("paint_operator"), dict) else {}
        paint_identity = (
            str(paint.get("operator") or ""),
            int(finite_number(paint.get("operator_index"), -1)),
            int(finite_number(paint.get("byte_offset"), -1)),
        )
        for channel in ("fill", "stroke"):
            color = paint_context.get(channel) if isinstance(paint_context.get(channel), dict) else None
            if not color:
                continue
            color_identity = (
                str(color.get("operator") or ""),
                int(finite_number(color.get("operator_index"), -1)),
                int(finite_number(color.get("byte_offset"), -1)),
            )
            paint_usage.setdefault(color_identity, set()).add(paint_identity)
        stroke_style = paint_context.get("stroke_style") if isinstance(paint_context.get("stroke_style"), dict) else {}
        for property_context in stroke_style.values():
            if not isinstance(property_context, dict):
                continue
            property_identity = (
                str(property_context.get("operator") or ""),
                int(finite_number(property_context.get("operator_index"), -1)),
                int(finite_number(property_context.get("byte_offset"), -1)),
            )
            stroke_style_usage.setdefault(property_identity, set()).add(paint_identity)
    inherited_consumers = [
        row for row in runs
        if str(row.get("operator") or "") in {"Tj", "TJ", "'", '"', "Do"}
    ]
    for usage_map in (paint_usage, stroke_style_usage):
        for state_identity, consumers in usage_map.items():
            state_operator_index = state_identity[1]
            for consumer in inherited_consumers:
                consumer_index = int(finite_number(consumer.get("operator_index"), -1))
                if consumer_index > state_operator_index:
                    consumers.add((
                        f"consumer:{consumer.get('operator') or ''}",
                        consumer_index,
                        int(finite_number(consumer.get("byte_offset"), -1)),
                    ))
    for row in runs:
        sequence = row.get("path_sequence") if isinstance(row.get("path_sequence"), dict) else None
        paint_context = sequence.get("paint_context") if isinstance(sequence, dict) and isinstance(sequence.get("paint_context"), dict) else None
        if not paint_context:
            continue
        for channel in ("fill", "stroke"):
            color = paint_context.get(channel) if isinstance(paint_context.get(channel), dict) else None
            if not color:
                continue
            color_identity = (
                str(color.get("operator") or ""),
                int(finite_number(color.get("operator_index"), -1)),
                int(finite_number(color.get("byte_offset"), -1)),
            )
            semantic_use_count = len(paint_usage.get(color_identity, set()))
            color["semantic_use_count"] = semantic_use_count
            source_origin = str(color.get("source_origin") or "explicit")
            color["single_paint_sequence"] = (
                source_origin == "explicit"
                and semantic_use_count == 1
                and operator_total <= len(runs)
                and not inline_image_ambiguous
            )
            color["localize_required"] = not color["single_paint_sequence"]
        stroke_style = paint_context.get("stroke_style") if isinstance(paint_context.get("stroke_style"), dict) else {}
        for property_name, property_context in list(stroke_style.items()):
            if not isinstance(property_context, dict):
                continue
            property_identity = (
                str(property_context.get("operator") or ""),
                int(finite_number(property_context.get("operator_index"), -1)),
                int(finite_number(property_context.get("byte_offset"), -1)),
            )
            semantic_use_count = len(stroke_style_usage.get(property_identity, set()))
            property_context["semantic_use_count"] = semantic_use_count
            source_origin = str(property_context.get("source_origin") or "explicit")
            property_context["single_paint_sequence"] = (
                source_origin == "explicit"
                and semantic_use_count == 1
                and operator_total <= len(runs)
                and not inline_image_ambiguous
            )
            property_context["localize_required"] = not property_context["single_paint_sequence"]
        paint_context["miter_limit"] = (
            dict(stroke_style["miter_limit"])
            if isinstance(stroke_style.get("miter_limit"), dict)
            else None
        )
        paint_context["local_state_materialization_supported"] = operator_total <= len(runs) and not inline_image_ambiguous
    return {
        "operator_count": operator_total,
        "operator_runs": runs,
        "operator_categories": categories,
        "operator_run_limit": MAX_NATIVE_PDF_OPERATOR_RUNS,
        "operator_runs_truncated": operator_total > len(runs),
        "inline_image_ambiguity": inline_image_ambiguous,
        "sample_operators": [run["operator"] for run in runs[:18]],
    }


def native_pdf_content_stream_descriptors(doc: object, page: object, page_id: str) -> list[dict[str, object]]:
    descriptors: list[dict[str, object]] = []
    for index, xref in enumerate(page_content_xrefs(page)):
        stream_bytes = b""
        try:
            stream_bytes = bytes(doc.xref_stream(xref) or b"")
        except Exception:  # noqa: BLE001 - tolerate unavailable compressed/object-stream variants
            stream_bytes = b""
        operator_profile = pdf_content_stream_operator_profile(stream_bytes)
        descriptors.append({
            "id": f"{page_id}-content-{index}-xref-{xref}",
            "xref": xref,
            "sequence": index,
            "byte_size": len(stream_bytes),
            "byte_length": len(stream_bytes),
            "sha256": hashlib.sha256(stream_bytes).hexdigest() if stream_bytes else "",
            "operator_identity_scope": "page-content-stream",
            "operator_count": operator_profile["operator_count"],
            "operator_runs": operator_profile["operator_runs"],
            "operator_categories": operator_profile["operator_categories"],
            "operator_run_limit": operator_profile["operator_run_limit"],
            "operator_runs_truncated": operator_profile["operator_runs_truncated"],
            "sample_operators": operator_profile["sample_operators"],
            "rewrite_status": "operator runs exposed; bounded stream replacement, selected path transform, and clip disable supported; arbitrary operator graph mutation still requires native compiler work",
        })
    return descriptors


def native_pdf_content_stream_operation_matrix() -> dict[str, object]:
    bounded_descriptor_types = sorted(
        SUPPORTED_NATIVE_PDF_CONTENT_STREAM_DESCRIPTOR_TYPES
        | SUPPORTED_NATIVE_PDF_RESOURCE_REWRITE_DESCRIPTOR_TYPES
    )
    return {
        "schema": "figureStudio.nativePdfContentStreamOperationMatrix.v1",
        "mode": "bounded-page-and-form-xobject-content-stream-plus-extgstate-resource-rewrite-with-noop-roundtrip",
        "appendable_now_descriptor_types": bounded_descriptor_types,
        "supported_descriptor_types": bounded_descriptor_types,
        "compiler_required_descriptor_types": [
            "arbitrary_advanced_feature_graph_edit",
            "gradient_mesh_pattern_edit",
            "gradient_stop_edit",
            "line_stroke_style_edit",
            "arbitrary_object_tree_mutation",
        ],
        "supported_operations": [
            "noop_parse_reserialize_roundtrip",
            "write_annotation_rectangle_overlay",
            "write_path_overlay",
            "write_path_boolean_overlay",
            "write_path_anchor_overlay",
            "write_path_control_handle_overlay",
            "replace_simple_path_content_stream",
            "replace_path_geometry_with_boolean_result",
            "target_form_xobject_content_stream_operator_runs",
            "disable_paint_operator_run",
            "rewrite_rgb_color_operator_run",
            "rewrite_selected_form_rgb_color_operator",
            "rewrite_selected_form_device_color_operator",
            "rewrite_selected_form_special_color_tint_operator",
            "rewrite_selected_form_path_stroke_geometry",
            "materialize_selected_form_path_local_appearance_state",
            "rewrite_stroke_width_operator_run",
            "transform_path_geometry_operator_run",
            "rewrite_selected_form_extgstate_appearance",
            "rewrite_extgstate_blend_mode",
            "rewrite_extgstate_opacity",
            "disable_extgstate_soft_mask",
            "disable_content_stream_clip_path",
            "rewrite_shading_function_colors",
            "rewrite_shading_coordinates",
            "rewrite_shading_background_color",
            "rewrite_tiling_pattern_stream_colors",
        ],
        "mutation_descriptor_limit": MAX_NATIVE_PDF_MUTATION_DESCRIPTORS,
        "path_command_limit": MAX_NATIVE_PDF_MUTATION_PATH_COMMANDS,
        "unsupported_native_equivalence_features": [
            "semantic_clip_mask_filter_graph_rewrite",
            "arbitrary_clip_path_shape_graph_rewrite",
            "freeform_path_anchor_ui_for_native_pdf_streams",
            "arbitrary_blend_graph_rewrite_beyond_extgstate_bm",
            "arbitrary_soft_mask_shape_graph_rewrite",
            "arbitrary_gradient_mesh_vertex_patch_rewrite",
        ],
        "bounded_native_rewrite_descriptor_types": ["object_tree_mutation", "advanced_feature_graph_edit"],
        "bounded_native_resource_rewrite_descriptor_types": ["advanced_feature_graph_edit", "gradient_stop_edit"],
        "source_backed_preview_remains_authoritative": True,
        "native_noop_roundtrip_available": True,
        "native_equivalent_pdf_output_available": False,
        "full_native_equivalence": False,
    }


def native_pdf_page_descriptor_id(page_number: int, page_xref: int) -> str:
    suffix = page_xref if page_xref else page_number
    return f"pdf-page-{page_number}-xref-{suffix}"


def drawing_descriptor(
    drawing: dict[str, object],
    page_number: int,
    index: int,
    page_id: str,
    content_streams: list[dict[str, object]],
    render_membership: dict[str, object] | None = None,
) -> dict[str, object]:
    items = drawing.get("items") if isinstance(drawing, dict) else []
    operators: list[str] = []
    safe_items: list[dict[str, object]] = []
    for item in list(items or [])[:MAX_NATIVE_PDF_PATH_ITEMS]:
        if not isinstance(item, (list, tuple)) or not item:
            continue
        operator = str(item[0])
        operators.append(operator)
        safe_items.append({
            "operator": operator,
            "arity": max(0, len(item) - 1),
        })
    bbox = rect_payload(drawing.get("rect") if isinstance(drawing, dict) else None)
    membership = render_membership if isinstance(render_membership, dict) else {}
    owner_xobject_id = str(membership.get("owner_xobject_id") or "")
    owner_content_refs = [str(value) for value in membership.get("content_stream_refs", []) if value]
    return {
        "id": f"pdf-p{page_number}-draw-{index}",
        "stable_object_id": f"{page_id}-draw-{index}",
        "native_kind": "path",
        "source": "native-content-stream-path",
        "content_stream_refs": owner_content_refs or [stream.get("id") for stream in content_streams],
        "content_stream_scope": str(membership.get("content_stream_scope") or "page-content-stream"),
        "membership_status": str(membership.get("membership_status") or "page-render-sequence"),
        "membership_provenance": str(membership.get("membership_provenance") or "native-render-sequence"),
        "owner_xobject_id": owner_xobject_id,
        "owner_xobject_xref": int(finite_number(membership.get("owner_xobject_xref"), 0)),
        "owner_xobject_name": str(membership.get("owner_xobject_name") or ""),
        "owner_xobject_invocation_id": str(membership.get("owner_xobject_invocation_id") or ""),
        "owner_xobject_invocation_path": str(membership.get("owner_xobject_invocation_path") or ""),
        "owner_xobject_parent_invocation_id": str(membership.get("owner_xobject_parent_invocation_id") or ""),
        "owner_xobject_nesting_depth": int(finite_number(membership.get("owner_xobject_nesting_depth"), 0)),
        "owner_xobject_invocation_ordinal": int(finite_number(membership.get("owner_xobject_invocation_ordinal"), 0)),
        "owner_xobject_invocation_ctm": membership.get("owner_xobject_invocation_ctm") or [],
        "owner_xobject_resource_scope_id": str(membership.get("owner_xobject_resource_scope_id") or ""),
        "owner_xobject_resource_owner_xref": int(finite_number(membership.get("owner_xobject_resource_owner_xref"), 0)),
        "owner_xobject_shared_definition": bool(membership.get("owner_xobject_shared_definition")),
        "per_instance_native_write_supported": bool(membership.get("per_instance_native_write_supported", True)),
        "clip_memberships": [str(value) for value in membership.get("clip_memberships", []) if value],
        "mask_memberships": [str(value) for value in membership.get("mask_memberships", []) if value],
        "extgstate_memberships": [str(value) for value in membership.get("extgstate_memberships", []) if value],
        "blend_memberships": [str(value) for value in membership.get("blend_memberships", []) if value],
        "operator_identities": [
            {
                "id": f"{page_id}-draw-{index}-op-{operator_index}",
                "operator": item["operator"],
                "arity": item["arity"],
                "content_stream_scope": "page-content-stream-sequence",
            }
            for operator_index, item in enumerate(safe_items)
        ],
        "sequence": index,
        "seqno": int(finite_number(drawing.get("seqno") if isinstance(drawing, dict) else index, index)),
        "paint_type": str(drawing.get("type") or ""),
        "bbox": bbox,
        "stroke": color_payload(drawing.get("color")) if isinstance(drawing, dict) else None,
        "fill": color_payload(drawing.get("fill")) if isinstance(drawing, dict) else None,
        "stroke_width": finite_number(drawing.get("width") if isinstance(drawing, dict) else 0),
        "opacity": {
            "stroke": finite_number(drawing.get("stroke_opacity") if isinstance(drawing, dict) else 1, 1),
            "fill": finite_number(drawing.get("fill_opacity") if isinstance(drawing, dict) else 1, 1),
        },
        "operator_count": len(items or []),
        "operators": operators[:MAX_NATIVE_PDF_PATH_ITEMS],
        "sample_items": safe_items,
    }


def text_descriptors(page: object, page_number: int) -> list[dict[str, object]]:
    try:
        text = page.get_text("dict")
    except Exception:  # noqa: BLE001 - optional descriptor extraction
        return []
    descriptors: list[dict[str, object]] = []
    for block_index, block in enumerate(text.get("blocks", [])):
        if block.get("type") != 0:
            continue
        for line_index, line in enumerate(block.get("lines", [])):
            direction = line.get("dir") if isinstance(line.get("dir"), (list, tuple)) else (1, 0)
            direction_x = finite_number(direction[0] if len(direction) > 0 else 1, 1)
            direction_y = finite_number(direction[1] if len(direction) > 1 else 0, 0)
            for span_index, span in enumerate(line.get("spans", [])):
                value = str(span.get("text") or "")
                if not value.strip():
                    continue
                bbox = rect_payload(span.get("bbox"))
                origin = span.get("origin") if isinstance(span.get("origin"), (list, tuple)) else None
                color = int(finite_number(span.get("color"), 0)) & 0xFFFFFF
                advance = 0.0
                if bbox:
                    corners = (
                        (bbox["x0"], bbox["y0"]),
                        (bbox["x1"], bbox["y0"]),
                        (bbox["x0"], bbox["y1"]),
                        (bbox["x1"], bbox["y1"]),
                    )
                    projections = [x * direction_x + y * direction_y for x, y in corners]
                    advance = max(projections) - min(projections)
                font_name = str(span.get("font") or "")
                descriptors.append({
                    "id": f"pdf-p{page_number}-text-{block_index}-{line_index}-{span_index}",
                    "native_kind": "text",
                    "source": "native-content-stream-text",
                    "block_index": block_index,
                    "line_index": line_index,
                    "span_index": span_index,
                    "bbox": bbox,
                    "line_bbox": rect_payload(line.get("bbox")),
                    "origin": {
                        "x": finite_number(origin[0]) if origin and len(origin) > 0 else (bbox or {}).get("x0", 0),
                        "y": finite_number(origin[1]) if origin and len(origin) > 1 else (bbox or {}).get("y1", 0),
                    },
                    "direction": {"x": direction_x, "y": direction_y},
                    "writing_mode": int(finite_number(line.get("wmode"), 0)),
                    "text": value[:2048],
                    "font": font_name,
                    "font_subset": bool(re.match(r"^[A-Z]{6}\+", font_name)),
                    "size": finite_number(span.get("size")),
                    "flags": int(finite_number(span.get("flags"), 0)),
                    "char_flags": int(finite_number(span.get("char_flags"), 0)),
                    "ascender": finite_number(span.get("ascender"), 0.8),
                    "descender": finite_number(span.get("descender"), -0.2),
                    "alpha": int(finite_number(span.get("alpha"), 255)),
                    "color": color,
                    "color_css": f"#{color:06x}",
                    "advance": round(max(0.0, advance), 5),
                    "reconstruction_status": "editable-with-font-review",
                })
                if len(descriptors) >= MAX_NATIVE_PDF_DESCRIPTORS:
                    return descriptors
    return descriptors


def graphics_svg_without_text_uses(svg: str) -> str:
    """Remove materialized glyph <use data-text=.../> nodes while retaining page graphics."""
    if not svg:
        return ""
    return re.sub(
        r"<use\b(?=[^>]*\bdata-text=(?:\"[^\"]*\"|'[^']*'))[^>]*/>",
        "",
        svg,
        flags=re.IGNORECASE,
    )


def fidelity_text_run_svgs(svg: str, text_rows: list[dict[str, object]]) -> tuple[str, list[dict[str, object]]]:
    """Split MuPDF glyph-outline uses into descriptor-owned SVG fragments."""
    if not svg or not text_rows:
        return svg, []
    try:
        root = ET.fromstring(svg)
    except ET.ParseError:
        return svg, []
    svg_ns = "http://www.w3.org/2000/svg"
    xlink_ns = "http://www.w3.org/1999/xlink"
    ET.register_namespace("", svg_ns)
    ET.register_namespace("xlink", xlink_ns)
    uses = list(root.iter(f"{{{svg_ns}}}use"))
    definitions = {
        str(node.get("id") or ""): node
        for node in root.iter()
        if node.get("id")
    }
    parents = {child: parent for parent in root.iter() for child in parent}
    assigned: dict[str, list[ET.Element]] = {str(row.get("id") or ""): [] for row in text_rows}
    assigned_glyph_ids: dict[str, list[str]] = {str(row.get("id") or ""): [] for row in text_rows}
    assigned_glyph_tokens: dict[str, list[dict[str, str]]] = {str(row.get("id") or ""): [] for row in text_rows}
    original_fill_by_glyph_id: dict[str, str] = {}

    def inherited_fill(element: ET.Element) -> str:
        ancestry: list[ET.Element] = []
        current: ET.Element | None = element
        while current is not None:
            ancestry.append(current)
            current = parents.get(current)
        fill = "#000000"
        for ancestor in reversed(ancestry):
            if ancestor.get("fill") is not None:
                fill = str(ancestor.get("fill"))
            style = str(ancestor.get("style") or "")
            style_match = re.search(r"(?:^|;)\s*fill\s*:\s*([^;]+)", style, re.IGNORECASE)
            if style_match:
                fill = style_match.group(1).strip()
        return fill

    for use_index, use in enumerate(uses):
        transform = str(use.get("transform") or "")
        values = [finite_number(value) for value in re.findall(r"[-+]?(?:\d*\.\d+|\d+)(?:[eE][-+]?\d+)?", transform)]
        if len(values) < 6:
            continue
        x, y = values[4], values[5]
        best: tuple[float, str] | None = None
        for row in text_rows:
            row_id = str(row.get("id") or "")
            origin = row.get("origin") if isinstance(row.get("origin"), dict) else {}
            direction = row.get("direction") if isinstance(row.get("direction"), dict) else {}
            ox = finite_number(origin.get("x"))
            oy = finite_number(origin.get("y"))
            dx = finite_number(direction.get("x"), 1)
            dy = finite_number(direction.get("y"), 0)
            magnitude = math.hypot(dx, dy) or 1
            dx, dy = dx / magnitude, dy / magnitude
            along = (x - ox) * dx + (y - oy) * dy
            across = abs((x - ox) * -dy + (y - oy) * dx)
            advance = max(0.0, finite_number(row.get("advance")))
            font_size = max(1.0, finite_number(row.get("size"), 10))
            if across > max(1.5, font_size * 0.2) or along < -font_size * 0.2 or along > advance + font_size * 0.75:
                continue
            score = across * 1000 + abs(min(max(along, 0), advance) - along)
            if best is None or score < best[0]:
                best = (score, row_id)
        if best:
            row_id = best[1]
            glyph_id = f"fs-pdf-text-glyph-{use_index}"
            glyph_token = f"#{0xFD0000 + (use_index % 0x10000):06x}"
            original_fill = inherited_fill(use)
            use.set("id", glyph_id)
            use.set("data-pdf-text-descriptor-id", row_id)
            use.set("fill", glyph_token)
            use.set("style", f"{str(use.get('style') or '').rstrip(';')};fill:{glyph_token}")
            assigned[row_id].append(use)
            assigned_glyph_ids[row_id].append(glyph_id)
            assigned_glyph_tokens[row_id].append({"token": glyph_token, "originalFill": original_fill})
            original_fill_by_glyph_id[glyph_id] = original_fill
    fragments: list[dict[str, object]] = []
    root_attributes = {key: value for key, value in root.attrib.items()}
    presentation_attributes = ("fill", "fill-opacity", "stroke", "stroke-width", "stroke-opacity", "opacity", "color", "style")
    for row in text_rows:
        row_id = str(row.get("id") or "")
        row_uses = assigned.get(row_id) or []
        if not row_uses:
            continue
        fragment_root = ET.Element(f"{{{svg_ns}}}svg", root_attributes)
        glyph_count = 0
        for use in row_uses:
            href = str(use.get(f"{{{xlink_ns}}}href") or use.get("href") or "")
            definition = definitions.get(href[1:]) if href.startswith("#") else None
            if definition is None:
                continue
            glyph = ET.fromstring(ET.tostring(definition, encoding="unicode"))
            glyph.attrib.pop("id", None)
            use_transform = str(use.get("transform") or "").strip()
            definition_transform = str(glyph.get("transform") or "").strip()
            if use_transform or definition_transform:
                glyph.set("transform", " ".join(value for value in (use_transform, definition_transform) if value))
            inherited: dict[str, str] = {}
            ancestry: list[ET.Element] = []
            current: ET.Element | None = use
            while current is not None:
                ancestry.append(current)
                current = parents.get(current)
            for ancestor in reversed(ancestry):
                for attribute in presentation_attributes:
                    value = ancestor.get(attribute)
                    if value is not None:
                        inherited[attribute] = value
            for attribute, value in inherited.items():
                if glyph.get(attribute) is None:
                    glyph.set(attribute, value)
            original_fill = original_fill_by_glyph_id.get(str(use.get("id") or ""), "#000000")
            glyph.set("fill", original_fill)
            glyph.set("style", f"{str(glyph.get('style') or '').rstrip(';')};fill:{original_fill}")
            data_text = use.get("data-text")
            if data_text is not None:
                glyph.set("data-text", data_text)
            fragment_root.append(glyph)
            glyph_count += 1
        if not glyph_count:
            continue
        fragments.append({
            "descriptorId": row_id,
            "svgText": ET.tostring(fragment_root, encoding="unicode"),
            "glyphCount": glyph_count,
            "glyphIds": assigned_glyph_ids.get(row_id) or [],
            "glyphTokens": assigned_glyph_tokens.get(row_id) or [],
            "source": "materialized-glyph-paths",
        })
    return ET.tostring(root, encoding="unicode"), fragments


def image_resource_rows(
    page: object,
    invocation_index: dict[str, object] | None = None,
) -> list[dict[str, object]]:
    base_rows: list[dict[str, object]] = []
    try:
        images = page.get_images(full=True)
    except Exception:  # noqa: BLE001
        images = []
    for index, image in enumerate(images[:MAX_NATIVE_PDF_RESOURCE_ROWS]):
        base_rows.append({
            "index": index,
            "xref": int(finite_number(image[0], 0)) if len(image) > 0 else 0,
            "smask": int(finite_number(image[1], 0)) if len(image) > 1 else 0,
            "width": int(finite_number(image[2], 0)) if len(image) > 2 else 0,
            "height": int(finite_number(image[3], 0)) if len(image) > 3 else 0,
            "bits_per_component": int(finite_number(image[4], 0)) if len(image) > 4 else 0,
            "colorspace": str(image[5]) if len(image) > 5 else "",
            "resource_name": str(image[7]) if len(image) > 7 else "",
            "filter": str(image[8]) if len(image) > 8 else "",
            "reported_resource_owner_xref": int(finite_number(image[9], 0)) if len(image) > 9 else 0,
        })
    bindings = [row for row in native_pdf_resource_bindings(invocation_index, "xobject") if row.get("binding_kind") == "image-xobject"]
    if not bindings:
        return base_rows
    rows: list[dict[str, object]] = []
    for index, binding in enumerate(bindings[:MAX_NATIVE_PDF_RESOURCE_ROWS]):
        xref = int(finite_number(binding.get("target_xref"), 0))
        name = str(binding.get("name") or "")
        base = next((row for row in base_rows if int(finite_number(row.get("xref"), 0)) == xref and str(row.get("resource_name") or "") == name), None)
        if base is None:
            base = next((row for row in base_rows if int(finite_number(row.get("xref"), 0)) == xref), {})
        rows.append({
            **base,
            "index": index,
            "id": binding.get("id") or f"image-xref-{xref}",
            "binding_id": binding.get("id") or "",
            "xref": xref,
            "resource_name": name,
            "resource_scope_id": binding.get("resource_scope_id") or "",
            "resource_owner_scope": binding.get("resource_owner_scope") or "page",
            "resource_owner_xref": int(finite_number(binding.get("resource_owner_xref"), 0)),
            "resource_usage_ids": binding.get("resource_usage_ids") or [],
            "content_stream_refs": binding.get("content_stream_refs") or [],
            "owner_form_invocation_ids": binding.get("owner_form_invocation_ids") or [],
            "owner_form_invocation_paths": binding.get("owner_form_invocation_paths") or [],
            "shared_owner_form_definition": bool(binding.get("shared_owner_form_definition")),
            "per_instance_native_write_supported": bool(binding.get("per_instance_native_write_supported", True)),
        })
    return rows


def pdf_xref_reference(value: object) -> int:
    match = re.search(r"(?P<xref>\d+)\s+\d+\s+R", str(value or ""))
    return int(match.group("xref")) if match else 0


def pdf_font_unicode_context(doc: object, xref: int, font_type: str, encoding: str) -> dict[str, object]:
    to_unicode_type = "null"
    to_unicode_value = ""
    descendant_value = ""
    if xref > 0:
        try:
            to_unicode_type, to_unicode_value = doc.xref_get_key(xref, "ToUnicode")
        except Exception:  # noqa: BLE001 - malformed font dictionaries remain inspectable
            to_unicode_type, to_unicode_value = "unavailable", ""
        try:
            _, descendant_value = doc.xref_get_key(xref, "DescendantFonts")
        except Exception:  # noqa: BLE001
            descendant_value = ""
    to_unicode_xref = pdf_xref_reference(to_unicode_value)
    to_unicode_stream_bytes = 0
    if to_unicode_xref > 0:
        try:
            to_unicode_stream_bytes = len(doc.xref_stream(to_unicode_xref) or b"")
        except Exception:  # noqa: BLE001
            to_unicode_stream_bytes = 0
    cid_font = str(font_type or "").lower() == "type0" or "identity-" in str(encoding or "").lower()
    return {
        "to_unicode_status": "embedded-cmap" if to_unicode_xref > 0 and to_unicode_stream_bytes > 0 else "not-available",
        "to_unicode_xref": to_unicode_xref,
        "to_unicode_stream_byte_size": to_unicode_stream_bytes,
        "cid_font": cid_font,
        "cid_encoding": str(encoding or "") if cid_font else "",
        "descendant_font_xref": pdf_xref_reference(descendant_value),
    }


def font_resource_rows(
    doc: object,
    page: object,
    invocation_index: dict[str, object] | None = None,
) -> list[dict[str, object]]:
    base_rows: list[dict[str, object]] = []
    try:
        fonts = page.get_fonts(full=True)
    except Exception:  # noqa: BLE001
        fonts = []
    for index, font in enumerate(fonts[:MAX_NATIVE_PDF_RESOURCE_ROWS]):
        base_font = str(font[3]) if len(font) > 3 else ""
        extension = str(font[1]) if len(font) > 1 else ""
        xref = int(finite_number(font[0], 0)) if len(font) > 0 else 0
        font_type = str(font[2]) if len(font) > 2 else ""
        encoding = str(font[5]) if len(font) > 5 else ""
        base_rows.append({
            "index": index,
            "xref": xref,
            "ext": extension,
            "type": font_type,
            "base_font": base_font,
            "normalized_base_font": re.sub(r"^[A-Z]{6}\+", "", base_font),
            "subset": bool(re.match(r"^[A-Z]{6}\+", base_font)),
            "embedded": bool(int(finite_number(font[0], 0)) > 0 and extension.lower() not in {"", "n/a"}),
            "subset_status": "basefont-name-inferred" if re.match(r"^[A-Z]{6}\+", base_font) else "not-detected",
            "embedded_status": "font-program-reported" if int(finite_number(font[0], 0)) > 0 and extension.lower() not in {"", "n/a"} else "unverified",
            "resource_name": str(font[4]) if len(font) > 4 else "",
            "encoding": encoding,
            "reported_resource_owner_xref": int(finite_number(font[6], 0)) if len(font) > 6 else 0,
            **pdf_font_unicode_context(doc, xref, font_type, encoding),
        })
    bindings = native_pdf_resource_bindings(invocation_index, "font")
    if not bindings:
        return base_rows
    rows: list[dict[str, object]] = []
    for index, binding in enumerate(bindings[:MAX_NATIVE_PDF_RESOURCE_ROWS]):
        xref = int(finite_number(binding.get("target_xref"), 0))
        name = str(binding.get("name") or "")
        base = next((row for row in base_rows if int(finite_number(row.get("xref"), 0)) == xref and str(row.get("resource_name") or "") == name), None)
        if base is None:
            base = next((row for row in base_rows if int(finite_number(row.get("xref"), 0)) == xref), {})
        rows.append({
            **base,
            "index": index,
            "id": binding.get("id") or f"font-xref-{xref}",
            "binding_id": binding.get("id") or "",
            "xref": xref,
            "resource_name": name,
            "resource_scope_id": binding.get("resource_scope_id") or "",
            "resource_owner_scope": binding.get("resource_owner_scope") or "page",
            "resource_owner_xref": int(finite_number(binding.get("resource_owner_xref"), 0)),
            "resource_usage_ids": binding.get("resource_usage_ids") or [],
            "content_stream_refs": binding.get("content_stream_refs") or [],
            "owner_form_invocation_ids": binding.get("owner_form_invocation_ids") or [],
            "owner_form_invocation_paths": binding.get("owner_form_invocation_paths") or [],
            "shared_owner_form_definition": bool(binding.get("shared_owner_form_definition")),
            "per_instance_native_write_supported": bool(binding.get("per_instance_native_write_supported", True)),
        })
    return rows


def link_text_font_resources(
    text_rows: list[dict[str, object]],
    font_resources: list[dict[str, object]],
    invocation_index: dict[str, object] | None = None,
) -> None:
    def font_key(value: object) -> str:
        normalized = re.sub(r"^[A-Z]{6}\+", "", str(value or "")).lower()
        return re.sub(r"[^a-z0-9]", "", normalized)

    tf_usages = [
        usage for usage in (invocation_index or {}).get("resource_usages", [])
        if usage.get("operator") == "Tf"
        and usage.get("resource_kind") == "font"
        and usage.get("resolution_status") == "proven-native-syntax"
    ]
    tf_binding_ids = {str(usage.get("binding_id") or "") for usage in tf_usages if usage.get("binding_id")}
    form_invocations = [
        row for row in (invocation_index or {}).get("form_invocations", [])
        if isinstance(row, dict)
    ]

    def containing_form_invocations(row: dict[str, object], owner_xref: int) -> list[dict[str, object]]:
        bbox = row.get("bbox") if isinstance(row.get("bbox"), dict) else {}
        if owner_xref <= 0 or not bbox:
            return []
        center_x = (finite_number(bbox.get("x0")) + finite_number(bbox.get("x1"))) / 2
        center_y = (finite_number(bbox.get("y0")) + finite_number(bbox.get("y1"))) / 2
        matches = []
        for invocation in form_invocations:
            page_bbox = invocation.get("page_bbox") if isinstance(invocation.get("page_bbox"), dict) else {}
            if int(finite_number(invocation.get("form_xref"), 0)) != owner_xref or not page_bbox:
                continue
            tolerance = 0.5
            if (
                finite_number(page_bbox.get("x0")) - tolerance <= center_x <= finite_number(page_bbox.get("x1")) + tolerance
                and finite_number(page_bbox.get("y0")) - tolerance <= center_y <= finite_number(page_bbox.get("y1")) + tolerance
            ):
                matches.append(invocation)
        if not matches:
            return []
        deepest = max(int(finite_number(item.get("nesting_depth"), 0)) for item in matches)
        return [item for item in matches if int(finite_number(item.get("nesting_depth"), 0)) == deepest]

    for row in text_rows:
        key = font_key(row.get("font"))
        if not key:
            continue
        exact_resources = [item for item in font_resources if font_key(item.get("base_font")) == key]
        spatial_exact_resources = [
            (item, containing_form_invocations(row, int(finite_number(item.get("resource_owner_xref"), 0))))
            for item in exact_resources
        ]
        spatial_exact_resources = [item for item in spatial_exact_resources if len(item[1]) == 1]
        preselected_owner_invocations: list[dict[str, object]] = []
        if len(spatial_exact_resources) == 1:
            resource, preselected_owner_invocations = spatial_exact_resources[0]
        else:
            resource = exact_resources[0] if len(exact_resources) == 1 else None
        association_status = "render-consensus-exact-name"
        if len(spatial_exact_resources) == 1:
            association_status = "proven-form-font-and-bounds"
        elif len(exact_resources) > 1:
            association_status = "ambiguous-page-resource-name"
        if resource is None and not exact_resources:
            fuzzy_resources = [
                item for item in font_resources
                if key in font_key(item.get("base_font")) or font_key(item.get("base_font")) in key
            ]
            if len(fuzzy_resources) == 1:
                association_status = "render-consensus-fuzzy-name"
                resource = fuzzy_resources[0]
            elif fuzzy_resources:
                association_status = "ambiguous-page-resource-name"
        if resource is None:
            row["font_resource_association_status"] = association_status
            row["font_resource_writer_authoritative"] = False
            continue
        if (
            len(tf_binding_ids) == 1
            and str(resource.get("binding_id") or resource.get("id") or "") in tf_binding_ids
        ):
            association_status = "proven-single-tf-binding-native-syntax"
        row.update({
            "font_resource_id": resource.get("id") or "",
            "font_resource_xref": int(finite_number(resource.get("xref"), 0)),
            "font_resource_name": resource.get("resource_name") or "",
            "font_resource_scope_id": resource.get("resource_scope_id") or "",
            "font_resource_embedded": bool(resource.get("embedded")),
            "font_resource_subset": bool(resource.get("subset")),
            "font_resource_type": resource.get("type") or "",
            "font_resource_encoding": resource.get("encoding") or "",
            "font_resource_association_status": association_status,
            "font_resource_writer_authoritative": False,
            "font_resource_subset_status": resource.get("subset_status") or "unverified",
            "font_resource_embedded_status": resource.get("embedded_status") or "unverified",
            "font_resource_to_unicode_status": resource.get("to_unicode_status") or "not-available",
            "font_resource_to_unicode_xref": int(finite_number(resource.get("to_unicode_xref"), 0)),
            "font_resource_cid_font": bool(resource.get("cid_font")),
            "font_resource_cid_encoding": resource.get("cid_encoding") or "",
        })
        owner_xref = int(finite_number(resource.get("resource_owner_xref"), 0))
        owner_invocations = preselected_owner_invocations or containing_form_invocations(row, owner_xref)
        if len(owner_invocations) == 1:
            owner = owner_invocations[0]
            row.update({
                "owner_xobject_invocation_status": "exact-form-font-and-bounds",
                "owner_xobject_invocation_id": str(owner.get("id") or owner.get("invocation_id") or ""),
                "owner_xobject_invocation_path": str(owner.get("invocation_path") or ""),
                "owner_xobject_parent_invocation_id": str(owner.get("parent_invocation_id") or ""),
                "owner_xobject_nesting_depth": int(finite_number(owner.get("nesting_depth"), 0)),
                "owner_xobject_xref": int(finite_number(owner.get("form_xref"), 0)),
                "owner_xobject_page_ctm": owner.get("page_ctm") or [],
                "owner_xobject_shared_definition": bool(owner.get("shared_definition")),
                "owner_xobject_per_instance_write": bool(owner.get("per_instance_native_write_supported", True)),
            })
        elif owner_xref > 0:
            row["owner_xobject_invocation_status"] = (
                "ambiguous-form-font-and-bounds" if owner_invocations else "form-invocation-unmatched"
            )


def image_block_descriptors(page: object, page_number: int, offset: int) -> list[dict[str, object]]:
    try:
        text = page.get_text("dict")
    except Exception:  # noqa: BLE001
        return []
    descriptors: list[dict[str, object]] = []
    for block_index, block in enumerate(text.get("blocks", [])):
        if block.get("type") != 1:
            continue
        descriptors.append({
            "id": f"pdf-p{page_number}-image-block-{block_index}",
            "native_kind": "image",
            "source": "native-content-stream-text",
            "sequence": offset + block_index,
            "bbox": rect_payload(block.get("bbox")),
            "width": int(finite_number(block.get("width"), 0)),
            "height": int(finite_number(block.get("height"), 0)),
            "ext": str(block.get("ext") or ""),
        })
        if len(descriptors) >= MAX_NATIVE_PDF_DESCRIPTORS:
            return descriptors
    return descriptors


def xobject_descriptors(
    doc: object,
    page: object,
    page_id: str,
    invocation_index: dict[str, object] | None = None,
) -> list[dict[str, object]]:
    descriptors: list[dict[str, object]] = []
    for row in page_form_xobject_rows(doc, page, invocation_index):
        index = int(finite_number(row.get("index"), len(descriptors)))
        xref = int(finite_number(row.get("xref"), 0))
        stream_bytes = pdf_xref_stream_bytes(doc, xref)
        operator_profile = pdf_content_stream_operator_profile(stream_bytes) if stream_bytes else {
            "operator_count": 0,
            "operator_runs": [],
            "operator_categories": {},
            "operator_run_limit": MAX_NATIVE_PDF_OPERATOR_RUNS,
            "operator_runs_truncated": False,
            "sample_operators": [],
        }
        editable_stream = bool(row.get("editable_content_stream"))
        descriptor_id = str(row.get("definition_id") or row.get("id") or f"{page_id}-xobject-{index}-xref-{xref}")
        descriptors.append({
            "id": descriptor_id,
            "definition_id": descriptor_id,
            "binding_id": str(row.get("binding_id") or ""),
            "xref": xref,
            "name": str(row.get("name") or ""),
            "invoker_xref": int(finite_number(row.get("invoker_xref"), 0)),
            "resource_owner_xref": int(finite_number(row.get("resource_owner_xref"), 0)),
            "resource_owner_scope": str(row.get("resource_owner_scope") or "page"),
            "kind": str(row.get("kind") or "xobject"),
            "xobject_subtype": str(row.get("subtype") or row.get("kind") or ""),
            "resource_type": "xobject",
            "content_stream_scope": "form-xobject-content-stream" if editable_stream else "",
            "operator_identity_scope": "form-xobject-content-stream" if editable_stream else "xobject-resource",
            "editable_content_stream": editable_stream,
            "page_ctm": row.get("page_ctm") or [1.0, 0.0, 0.0, 1.0, 0.0, 0.0],
            "form_matrix": row.get("form_matrix") or [1.0, 0.0, 0.0, 1.0, 0.0, 0.0],
            "form_bbox": row.get("form_bbox"),
            "page_bbox": row.get("page_bbox"),
            "invocation_count": int(finite_number(row.get("invocation_count"), 0)),
            "invocations": row.get("invocations") or [],
            "min_nesting_depth": int(finite_number(row.get("min_nesting_depth"), 0)),
            "max_nesting_depth": int(finite_number(row.get("max_nesting_depth"), 0)),
            "shared_definition": bool(row.get("shared_definition")),
            "per_instance_native_write_supported": bool(row.get("per_instance_native_write_supported")),
            "native_write_scope": "shared-form-definition" if row.get("shared_definition") else "form-definition",
            "byte_size": len(stream_bytes),
            "byte_length": len(stream_bytes),
            "sha256": hashlib.sha256(stream_bytes).hexdigest() if stream_bytes else "",
            "operator_count": operator_profile["operator_count"],
            "operator_runs": operator_profile["operator_runs"],
            "operator_categories": operator_profile["operator_categories"],
            "operator_run_limit": operator_profile["operator_run_limit"],
            "operator_runs_truncated": operator_profile["operator_runs_truncated"],
            "sample_operators": operator_profile["sample_operators"],
            "mutation_status": (
                "shared Form definition is editable, but a native write affects every invocation; per-instance native mutation requires clone-and-rebind"
                if editable_stream and row.get("shared_definition")
                else "bounded Form XObject content-stream operator mutation supported; semantic XObject graph rewriting still requires broader compiler work"
                if editable_stream
                else "preserved; semantic XObject compiler required for native graph mutation"
            ),
        })
    return descriptors


def content_stream_clip_path_rows(doc: object, page_id: str, content_streams: list[dict[str, object]]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    seen_xrefs: set[int] = set()
    for stream in content_streams[:MAX_NATIVE_PDF_RESOURCE_ROWS]:
        xref = int(finite_number(stream.get("xref"), 0))
        if xref <= 0 or xref in seen_xrefs:
            continue
        seen_xrefs.add(xref)
        try:
            stream_bytes = bytes(doc.xref_stream(xref) or b"")
        except Exception:  # noqa: BLE001
            continue
        text = stream_bytes.decode("latin-1", errors="ignore")
        matches = list(re.finditer(r"(?<![A-Za-z0-9_])W\*?(?![A-Za-z0-9_])", text))
        if not matches:
            continue
        samples = []
        for match in matches[:8]:
            start = max(0, match.start() - 48)
            end = min(len(text), match.end() + 48)
            samples.append({
                "operator": match.group(0),
                "byte_offset": match.start(),
                "context": re.sub(r"\s+", " ", text[start:end]).strip()[:140],
            })
        rows.append({
            "id": f"{page_id}-clip-stream-xref-{xref}",
            "content_stream_id": stream.get("id") or "",
            "target_content_stream_xref": xref,
            "content_stream_scope": stream.get("content_stream_scope") or stream.get("operator_identity_scope") or "page-content-stream",
            "target_xobject_xref": xref if str(stream.get("content_stream_scope") or "") == "form-xobject-content-stream" else 0,
            "name": stream.get("name") or "",
            "resource_owner_scope": stream.get("resource_owner_scope") or ("form-xobject" if str(stream.get("content_stream_scope") or "") == "form-xobject-content-stream" else "page"),
            "resource_owner_xref": int(finite_number(stream.get("resource_owner_xref") or stream.get("invoker_xref"), 0)),
            "owner_form_definition_id": stream.get("definition_id") or "",
            "owner_form_invocation_ids": [str(row.get("id") or "") for row in stream.get("invocations", []) if isinstance(row, dict)],
            "owner_form_invocation_paths": [str(row.get("invocation_path") or "") for row in stream.get("invocations", []) if isinstance(row, dict)],
            "shared_owner_form_definition": bool(stream.get("shared_definition")),
            "per_instance_native_write_supported": bool(stream.get("per_instance_native_write_supported", True)),
            "operator_count": len(matches),
            "operators": sorted({match.group(0) for match in matches}),
            "operator_samples": samples,
            "content_stream_sha256": hashlib.sha256(stream_bytes).hexdigest() if stream_bytes else "",
            "mutation_status": "bounded content-stream clip-path disable rewrite supported; clip shape editing remains compiler work",
        })
    return rows


def parse_shading_resource_map(doc: object, page: object) -> dict[str, int]:
    page_xref = int(finite_number(getattr(page, "xref", 0), 0))
    if page_xref <= 0:
        return {}
    resource_map, _dictionary_xref, _complete = pdf_resource_ref_map(doc, page_xref, "Shading")
    return resource_map


def shading_usage_by_resource(doc: object, content_streams: list[dict[str, object]]) -> dict[str, list[str]]:
    usage: dict[str, list[str]] = {}
    for stream in content_streams:
        xref = int(finite_number(stream.get("xref"), 0))
        if xref <= 0:
            continue
        try:
            text = bytes(doc.xref_stream(xref) or b"").decode("latin-1", errors="ignore")
        except Exception:  # noqa: BLE001
            continue
        for match in re.finditer(r"/([A-Za-z0-9_.-]+)\s+sh\b", text):
            usage.setdefault(match.group(1), []).append(str(stream.get("id") or xref))
    return usage


def parse_pdf_indirect_reference_array_after_key(source: str, key: str) -> list[int]:
    match = re.search(rf"/{re.escape(key)}\s*\[([^\]]*)\]", source or "", re.DOTALL)
    if not match:
        return []
    body = match.group(1)
    if not re.fullmatch(r"(?:\s*\d+\s+\d+\s+R\s*)+", body):
        return []
    return [int(value) for value in re.findall(r"(\d+)\s+\d+\s+R", body) if int(value) > 0]


def pdf_gradient_function_contract(doc: object, function_xref: int) -> dict[str, object]:
    source = pdf_xref_object_source(doc, function_xref)
    function_type = int(finite_number(parse_pdf_scalar_after_key(source, "FunctionType"), 0))
    domain = parse_pdf_number_array_after_key(source, "Domain")
    value_range = parse_pdf_number_array_after_key(source, "Range")
    contract: dict[str, object] = {
        "schema": "figureStudio.nativePdfGradientFunctionContract.v1",
        "supported": False,
        "reason": "unsupported-function-type",
        "function_xref": function_xref,
        "function_type": function_type,
        "domain": domain,
        "range": value_range,
        "object_sha256": hashlib.sha256(source.encode("utf-8", errors="ignore")).hexdigest() if source else "",
        "child_xrefs": [],
        "child_object_sha256": [],
        "bounds": [],
        "encode": [],
        "gradient_stops": [],
        "segment_exponents": [],
    }
    if not source or not pdf_number_arrays_match(domain, [0.0, 1.0]) or (value_range and len(value_range) != 6):
        contract["reason"] = "unsupported-function-domain"
        return contract
    if function_type == 2:
        c0 = parse_pdf_number_array_after_key(source, "C0")
        c1 = parse_pdf_number_array_after_key(source, "C1")
        exponent = finite_number(parse_pdf_scalar_after_key(source, "N"), -1)
        if (
            len(c0) != 3
            or len(c1) != 3
            or any(not math.isfinite(value) or value < 0 or value > 1 for value in [*c0, *c1])
            or not math.isfinite(exponent)
            or exponent <= 0
        ):
            contract["reason"] = "unsupported-type2-function-shape"
            return contract
        contract.update({
            "supported": True,
            "reason": "",
            "gradient_stops": [
                {"offset": 0.0, "color": c0},
                {"offset": 1.0, "color": c1},
            ],
            "segment_exponents": [exponent],
        })
        return contract
    if function_type != 3:
        return contract
    child_xrefs = parse_pdf_indirect_reference_array_after_key(source, "Functions")
    bounds = parse_pdf_number_array_after_key(source, "Bounds")
    encode = parse_pdf_number_array_after_key(source, "Encode")
    expected_encode = [value for _xref in child_xrefs for value in (0.0, 1.0)]
    if (
        len(child_xrefs) < 2
        or len(child_xrefs) > 16
        or len(bounds) != len(child_xrefs) - 1
        or len(encode) != len(child_xrefs) * 2
        or not pdf_number_arrays_match(encode, expected_encode)
        or any(not math.isfinite(value) or value <= 0 or value >= 1 for value in bounds)
        or any(bounds[index] >= bounds[index + 1] for index in range(len(bounds) - 1))
    ):
        contract["reason"] = "unsupported-type3-stitching-shape"
        return contract
    child_hashes: list[str] = []
    child_c0: list[list[float]] = []
    child_c1: list[list[float]] = []
    segment_exponents: list[float] = []
    for child_xref in child_xrefs:
        child_source = pdf_xref_object_source(doc, child_xref)
        child_domain = parse_pdf_number_array_after_key(child_source, "Domain")
        child_range = parse_pdf_number_array_after_key(child_source, "Range")
        c0 = parse_pdf_number_array_after_key(child_source, "C0")
        c1 = parse_pdf_number_array_after_key(child_source, "C1")
        exponent = finite_number(parse_pdf_scalar_after_key(child_source, "N"), -1)
        if (
            not child_source
            or int(finite_number(parse_pdf_scalar_after_key(child_source, "FunctionType"), 0)) != 2
            or not pdf_number_arrays_match(child_domain, [0.0, 1.0])
            or (child_range and len(child_range) != 6)
            or len(c0) != 3
            or len(c1) != 3
            or any(not math.isfinite(value) or value < 0 or value > 1 for value in [*c0, *c1])
            or not math.isfinite(exponent)
            or exponent <= 0
        ):
            contract["reason"] = "unsupported-type3-child-function"
            return contract
        child_hashes.append(hashlib.sha256(child_source.encode("utf-8", errors="ignore")).hexdigest())
        child_c0.append(c0)
        child_c1.append(c1)
        segment_exponents.append(exponent)
    if any(not pdf_number_arrays_match(child_c1[index], child_c0[index + 1]) for index in range(len(child_xrefs) - 1)):
        contract["reason"] = "discontinuous-type3-stops"
        return contract
    stops = [{"offset": 0.0, "color": child_c0[0]}]
    stops.extend({"offset": bounds[index], "color": child_c1[index]} for index in range(len(bounds)))
    stops.append({"offset": 1.0, "color": child_c1[-1]})
    contract.update({
        "supported": True,
        "reason": "",
        "child_xrefs": child_xrefs,
        "child_object_sha256": child_hashes,
        "bounds": bounds,
        "encode": encode,
        "gradient_stops": stops,
        "segment_exponents": segment_exponents,
    })
    return contract


def shading_resource_rows(
    doc: object,
    page: object,
    page_id: str,
    content_streams: list[dict[str, object]],
    invocation_index: dict[str, object] | None = None,
) -> list[dict[str, object]]:
    resource_map = parse_shading_resource_map(doc, page)
    usage = shading_usage_by_resource(doc, content_streams)
    bindings = native_pdf_resource_bindings(invocation_index, "shading")
    candidates = bindings or [
        {
            "target_xref": xref,
            "name": name,
            "resource_scope_id": "",
            "resource_owner_scope": "page",
            "resource_owner_xref": int(finite_number(getattr(page, "xref", 0), 0)),
            "resource_usage_ids": [],
            "content_stream_refs": usage.get(name, []),
            "owner_form_invocation_ids": [],
            "owner_form_invocation_paths": [],
            "shared_owner_form_definition": False,
            "per_instance_native_write_supported": True,
        }
        for name, xref in resource_map.items()
    ]
    rows: list[dict[str, object]] = []
    for index, binding in enumerate(candidates[:MAX_NATIVE_PDF_RESOURCE_ROWS]):
        name = str(binding.get("name") or "")
        xref = int(finite_number(binding.get("target_xref"), 0))
        try:
            source = str(doc.xref_object(xref, compressed=False) or "")
        except Exception:  # noqa: BLE001
            continue
        shading_type = int(finite_number(parse_pdf_scalar_after_key(source, "ShadingType"), 0))
        if shading_type not in {1, 2, 3, 4, 5, 6, 7}:
            continue
        function_match = re.search(r"/Function\s+(\d+)\s+\d+\s+R", source)
        function_xref = int(finite_number(function_match.group(1), 0)) if function_match else 0
        function_source = ""
        if function_xref > 0:
            try:
                function_source = str(doc.xref_object(function_xref, compressed=False) or "")
            except Exception:  # noqa: BLE001
                function_source = ""
        function_contract = pdf_gradient_function_contract(doc, function_xref) if function_source else {}
        function_type = int(finite_number(function_contract.get("function_type"), 0)) if function_source else 0
        c0 = parse_pdf_number_array_after_key(function_source, "C0") if function_source else []
        c1 = parse_pdf_number_array_after_key(function_source, "C1") if function_source else []
        coords = parse_pdf_number_array_after_key(source, "Coords")
        shading_domain = parse_pdf_number_array_after_key(source, "Domain")
        function_domain = parse_pdf_number_array_after_key(function_source, "Domain") if function_source else []
        function_range = parse_pdf_number_array_after_key(function_source, "Range") if function_source else []
        extend = parse_pdf_boolean_array_after_key(source, "Extend")
        function_exponent = parse_pdf_scalar_after_key(function_source, "N") if function_source else None
        direct_device_rgb = bool(re.search(r"/ColorSpace\s*/DeviceRGB\b", source))
        if shading_type == 1:
            shading_kind = "function"
        elif shading_type == 2:
            shading_kind = "axial"
        elif shading_type == 3:
            shading_kind = "radial"
        else:
            shading_kind = "mesh"
        coordinate_count = 4 if shading_type == 2 else 6 if shading_type == 3 else 0
        supported_gradient = bool(
            shading_type in {2, 3}
            and direct_device_rgb
            and function_xref > 0
            and function_contract.get("supported") is True
            and len(coords) == coordinate_count
            and (not shading_domain or len(shading_domain) == 2)
            and (not extend or len(extend) == 2)
        )
        rows.append({
            "id": str(binding.get("id") or f"{page_id}-shading-{index}-xref-{xref}"),
            "binding_id": str(binding.get("id") or ""),
            "xref": xref,
            "resource_name": name,
            "resource_type": "shading",
            "shading_type": shading_type,
            "shading_kind": shading_kind,
            "mesh_shading": shading_type in {4, 5, 6, 7},
            "colorspace": "/DeviceRGB" if direct_device_rgb else "",
            "coords": coords,
            "domain": shading_domain or [0.0, 1.0],
            "extend": extend or [False, False],
            "background": parse_pdf_number_array_after_key(source, "Background"),
            "function_xref": function_xref,
            "function_type": function_type,
            "function_domain": function_domain,
            "function_range": function_range,
            "function_c0": c0,
            "function_c1": c1,
            "function_exponent": function_exponent,
            "function_child_xrefs": function_contract.get("child_xrefs") or [],
            "function_child_object_sha256": function_contract.get("child_object_sha256") or [],
            "function_bounds": function_contract.get("bounds") or [],
            "function_encode": function_contract.get("encode") or [],
            "gradient_stops": function_contract.get("gradient_stops") or [],
            "segment_exponents": function_contract.get("segment_exponents") or [],
            "gradient_function_contract_reason": function_contract.get("reason") or "",
            "object_sha256": hashlib.sha256(source.encode("utf-8", errors="ignore")).hexdigest(),
            "function_object_sha256": hashlib.sha256(function_source.encode("utf-8", errors="ignore")).hexdigest() if function_source else "",
            "normal_gradient_controls_supported": supported_gradient,
            "content_stream_refs": sorted(set([str(value) for value in binding.get("content_stream_refs", []) if value] + usage.get(name, []))),
            "resource_usage_ids": binding.get("resource_usage_ids") or [],
            "resource_scope_id": binding.get("resource_scope_id") or "",
            "resource_owner_scope": binding.get("resource_owner_scope") or "page",
            "resource_owner_xref": int(finite_number(binding.get("resource_owner_xref"), 0)),
            "owner_form_invocation_ids": binding.get("owner_form_invocation_ids") or [],
            "owner_form_invocation_paths": binding.get("owner_form_invocation_paths") or [],
            "shared_owner_form_definition": bool(binding.get("shared_owner_form_definition")),
            "per_instance_native_write_supported": bool(binding.get("per_instance_native_write_supported", True)),
            "native_write_scope": "shared-resource-definition" if binding.get("shared_owner_form_definition") else "resource-definition",
            "mutation_status": (
                "bounded axial/radial Type 2 or continuous stitched Type 3 gradient controls supported"
                if supported_gradient
                else "bounded shading /Background resource write supported; mesh vertex/color patch editing remains compiler work"
            ),
        })
    return rows


def parse_pattern_resource_map(doc: object, page: object) -> dict[str, int]:
    page_xref = int(finite_number(getattr(page, "xref", 0), 0))
    if page_xref <= 0:
        return {}
    resource_map, _dictionary_xref, _complete = pdf_resource_ref_map(doc, page_xref, "Pattern")
    return resource_map


def pattern_usage_by_resource(doc: object, content_streams: list[dict[str, object]]) -> dict[str, list[str]]:
    usage: dict[str, list[str]] = {}
    for stream in content_streams:
        xref = int(finite_number(stream.get("xref"), 0))
        if xref <= 0:
            continue
        try:
            text = bytes(doc.xref_stream(xref) or b"").decode("latin-1", errors="ignore")
        except Exception:  # noqa: BLE001
            continue
        for match in re.finditer(r"/([A-Za-z0-9_.-]+)\s+scn\b|/([A-Za-z0-9_.-]+)\s+SCN\b", text):
            name = match.group(1) or match.group(2)
            if name:
                usage.setdefault(name, []).append(str(stream.get("id") or xref))
    return usage


def pattern_resource_rows(
    doc: object,
    page: object,
    page_id: str,
    content_streams: list[dict[str, object]],
    invocation_index: dict[str, object] | None = None,
) -> list[dict[str, object]]:
    resource_map = parse_pattern_resource_map(doc, page)
    usage = pattern_usage_by_resource(doc, content_streams)
    bindings = native_pdf_resource_bindings(invocation_index, "pattern")
    candidates = bindings or [
        {
            "target_xref": xref,
            "name": name,
            "resource_scope_id": "",
            "resource_owner_scope": "page",
            "resource_owner_xref": int(finite_number(getattr(page, "xref", 0), 0)),
            "resource_usage_ids": [],
            "content_stream_refs": usage.get(name, []),
            "owner_form_invocation_ids": [],
            "owner_form_invocation_paths": [],
            "shared_owner_form_definition": False,
            "per_instance_native_write_supported": True,
        }
        for name, xref in resource_map.items()
    ]
    rows: list[dict[str, object]] = []
    for index, binding in enumerate(candidates[:MAX_NATIVE_PDF_RESOURCE_ROWS]):
        name = str(binding.get("name") or "")
        xref = int(finite_number(binding.get("target_xref"), 0))
        try:
            source = str(doc.xref_object(xref, compressed=False) or "")
        except Exception:  # noqa: BLE001
            continue
        pattern_type = int(finite_number(parse_pdf_scalar_after_key(source, "PatternType"), 0))
        paint_type = int(finite_number(parse_pdf_scalar_after_key(source, "PaintType"), 0))
        tiling_type = int(finite_number(parse_pdf_scalar_after_key(source, "TilingType"), 0))
        stream_bytes = pdf_xref_stream_bytes(doc, xref)
        rows.append({
            "id": str(binding.get("id") or f"{page_id}-pattern-{index}-xref-{xref}"),
            "binding_id": str(binding.get("id") or ""),
            "xref": xref,
            "resource_name": name,
            "resource_type": "pattern",
            "pattern_type": pattern_type,
            "paint_type": paint_type,
            "tiling_type": tiling_type,
            "bbox": parse_pdf_number_array_after_key(source, "BBox"),
            "matrix": parse_pdf_number_array_after_key(source, "Matrix"),
            "x_step": parse_pdf_scalar_after_key(source, "XStep"),
            "y_step": parse_pdf_scalar_after_key(source, "YStep"),
            "stream_byte_size": len(stream_bytes),
            "stream_sha256": hashlib.sha256(stream_bytes).hexdigest() if stream_bytes else "",
            "content_stream_refs": sorted(set([str(value) for value in binding.get("content_stream_refs", []) if value] + usage.get(name, []))),
            "resource_usage_ids": binding.get("resource_usage_ids") or [],
            "resource_scope_id": binding.get("resource_scope_id") or "",
            "resource_owner_scope": binding.get("resource_owner_scope") or "page",
            "resource_owner_xref": int(finite_number(binding.get("resource_owner_xref"), 0)),
            "owner_form_invocation_ids": binding.get("owner_form_invocation_ids") or [],
            "owner_form_invocation_paths": binding.get("owner_form_invocation_paths") or [],
            "shared_owner_form_definition": bool(binding.get("shared_owner_form_definition")),
            "per_instance_native_write_supported": bool(binding.get("per_instance_native_write_supported", True)),
            "native_write_scope": "shared-resource-definition" if binding.get("shared_owner_form_definition") else "resource-definition",
            "mutation_status": (
                "bounded colored tiling pattern paint-stream color rewrite supported"
                if pattern_type == 1 and paint_type == 1 and bool(stream_bytes)
                else "pattern identity preserved; uncolored pattern paint operands and pattern geometry remain compiler work"
            ),
        })
    return rows


def pdf_rect_max_delta(left: object, right: object) -> float:
    left_rect = rect_payload(left)
    right_rect = rect_payload(right)
    if not left_rect or not right_rect:
        return float("inf")
    return max(abs(left_rect[key] - right_rect[key]) for key in ("x0", "y0", "x1", "y1"))


def link_image_shading_resources(
    image_rows: list[dict[str, object]],
    shadings: list[dict[str, object]],
    invocation_index: dict[str, object],
) -> None:
    if not invocation_index.get("parser_complete") or invocation_index.get("truncated"):
        return
    invocations = [row for row in invocation_index.get("form_invocations", []) if isinstance(row, dict)]
    usages = [
        row for row in invocation_index.get("resource_usages", [])
        if isinstance(row, dict) and row.get("resource_kind") == "shading"
    ]
    definitions = [row for row in invocation_index.get("form_definitions", []) if isinstance(row, dict)]
    shading_by_binding = {
        str(row.get("binding_id") or row.get("id") or ""): row
        for row in shadings
        if isinstance(row, dict) and row.get("normal_gradient_controls_supported")
    }
    for image in image_rows:
        matches: list[tuple[dict[str, object], dict[str, object], dict[str, object]]] = []
        for invocation in invocations:
            invocation_id = str(invocation.get("id") or invocation.get("invocation_id") or "")
            form_xref = int(finite_number(invocation.get("form_xref"), 0))
            if (
                not invocation_id
                or form_xref <= 0
                or invocation.get("transparency_group_in_chain") is True
                or pdf_rect_max_delta(image.get("bbox"), invocation.get("page_bbox")) > 0.75
            ):
                continue
            invocation_usages = [
                usage for usage in usages
                if str(usage.get("owner_invocation_id") or "") == invocation_id
                and int(finite_number(usage.get("owner_xref"), 0)) == form_xref
                and str(usage.get("operator") or "") == "sh"
                and str(usage.get("resolution_status") or "") == "proven-native-syntax"
            ]
            if len(invocation_usages) != 1:
                continue
            usage = invocation_usages[0]
            shading = shading_by_binding.get(str(usage.get("binding_id") or ""))
            if not shading:
                continue
            if (
                int(finite_number(shading.get("resource_owner_xref"), 0)) != form_xref
                or str(shading.get("resource_name") or "") != str(usage.get("resource_name") or "")
                or str(shading.get("resource_owner_scope") or "") != "form-xobject"
            ):
                continue
            matches.append((invocation, usage, shading))
        if len(matches) != 1:
            continue
        invocation, usage, shading = matches[0]
        form_xref = int(finite_number(invocation.get("form_xref"), 0))
        definition = next((
            row for row in definitions
            if int(finite_number(row.get("form_xref") or row.get("xref"), 0)) == form_xref
        ), {})
        image.update({
            "source": "native-content-stream-text+proven-form-shading",
            "content_stream_scope": "form-xobject-content-stream",
            "membership_status": "proven-form-shading-image",
            "membership_provenance": "image-bounds+form-invocation-bbox+single-shading-usage",
            "owner_xobject_id": str(definition.get("id") or definition.get("definition_id") or ""),
            "owner_xobject_xref": form_xref,
            "owner_xobject_name": str(invocation.get("name") or ""),
            "owner_xobject_invocation_id": str(invocation.get("id") or invocation.get("invocation_id") or ""),
            "owner_xobject_invocation_path": str(invocation.get("invocation_path") or ""),
            "owner_xobject_parent_invocation_id": str(invocation.get("parent_invocation_id") or ""),
            "owner_xobject_nesting_depth": int(finite_number(invocation.get("nesting_depth"), 0)),
            "owner_xobject_invocation_ordinal": int(finite_number(invocation.get("ordinal"), 0)),
            "owner_xobject_invocation_ctm": invocation.get("page_ctm") or [],
            "owner_xobject_resource_scope_id": str(shading.get("resource_scope_id") or ""),
            "owner_xobject_resource_owner_xref": form_xref,
            "owner_xobject_shared_definition": bool(invocation.get("shared_definition")),
            "per_instance_native_write_supported": bool(invocation.get("per_instance_native_write_supported", True)),
            "shading_memberships": [str(shading.get("id") or shading.get("binding_id") or "")],
            "shading_usage_ids": [str(usage.get("id") or "")],
            "shading_binding_id": str(shading.get("binding_id") or shading.get("id") or ""),
            "shading_resource_name": str(shading.get("resource_name") or ""),
            "shading_xref": int(finite_number(shading.get("xref"), 0)),
            "shading_function_xref": int(finite_number(shading.get("function_xref"), 0)),
            "shading_operator_index": int(finite_number(usage.get("operator_index"), -1)),
            "shading_operator_byte_offset": int(finite_number(usage.get("byte_offset"), -1)),
        })


def native_pdf_render_memberships(
    page: object,
    xobjects: list[dict[str, object]],
    clip_paths: list[dict[str, object]],
    extgstates: list[dict[str, object]],
) -> dict[str, object]:
    try:
        rows = page.get_drawings(extended=True)
    except Exception:  # noqa: BLE001 - extended drawing hierarchy is version-dependent
        rows = []
    memberships: list[dict[str, object]] = []
    clip_contexts: list[dict[str, object]] = []
    group_contexts: list[dict[str, object]] = []
    active: list[dict[str, object]] = []
    used_xobjects: set[str] = set()
    explicit_clip_index = 0
    paint_index = 0
    xobject_invocations = [
        {
            "owner": owner,
            "invocation_id": str(invocation.get("id") or invocation.get("invocation_id") or ""),
            "invocation_path": str(invocation.get("invocation_path") or ""),
            "parent_invocation_id": str(invocation.get("parent_invocation_id") or ""),
            "nesting_depth": int(finite_number(invocation.get("nesting_depth"), 0)),
            "ordinal": int(finite_number(invocation.get("ordinal"), invocation_index + 1)),
            "page_ctm": invocation.get("page_ctm") or owner.get("page_ctm") or [],
            "page_bbox": invocation.get("page_bbox") or owner.get("page_bbox"),
            "resource_scope_id": str(invocation.get("resource_scope_id") or ""),
            "resource_owner_xref": int(finite_number(invocation.get("resource_owner_xref"), 0)),
            "shared_definition": bool(invocation.get("shared_definition")),
            "per_instance_native_write_supported": bool(invocation.get("per_instance_native_write_supported", True)),
        }
        for owner in xobjects
        for invocation_index, invocation in enumerate(
            owner.get("invocations") if isinstance(owner.get("invocations"), list) else []
        )
        if isinstance(invocation, dict)
    ]

    for render_index, raw in enumerate(rows):
        if not isinstance(raw, dict):
            continue
        row_type = str(raw.get("type") or "")
        level = int(finite_number(raw.get("level"), 0))
        active = [context for context in active if int(finite_number(context.get("level"), -1)) < level]
        if row_type == "clip":
            scissor = rect_payload(raw.get("scissor") or raw.get("rect"))
            owner_invocation = next((
                item for item in xobject_invocations
                if str(item.get("invocation_id") or f"{(item.get('owner') or {}).get('id')}:{item.get('ordinal')}") not in used_xobjects
                and pdf_rect_max_delta(scissor, item.get("page_bbox")) <= 0.75
            ), None)
            owner = owner_invocation.get("owner") if owner_invocation else None
            if owner:
                invocation_ordinal = int(finite_number(owner_invocation.get("ordinal"), 1))
                invocation_id = str(owner_invocation.get("invocation_id") or f"{owner.get('id')}:invocation:{invocation_ordinal}")
                context_id = f"{invocation_id}:bounds-clip"
                used_xobjects.add(invocation_id)
                source = "form-xobject-bbox"
                native_clip_id = ""
            elif explicit_clip_index < len(clip_paths):
                native_clip = clip_paths[explicit_clip_index]
                explicit_clip_index += 1
                context_id = str(native_clip.get("id") or f"render-clip-{render_index}")
                source = "content-stream-clip-operator"
                native_clip_id = str(native_clip.get("id") or "")
            else:
                context_id = f"render-clip-{render_index}"
                source = "native-render-hierarchy"
                native_clip_id = ""
            context = {
                "id": context_id,
                "type": "clip",
                "level": level,
                "render_index": render_index,
                "source": source,
                "bbox": scissor,
                "native_clip_id": native_clip_id,
                "owner_xobject_id": str((owner or {}).get("id") or ""),
                "owner_xobject_xref": int(finite_number((owner or {}).get("xref"), 0)),
                "owner_xobject_name": str((owner or {}).get("name") or ""),
                "owner_xobject_invocation_id": str((owner_invocation or {}).get("invocation_id") or ""),
                "owner_xobject_invocation_path": str((owner_invocation or {}).get("invocation_path") or ""),
                "owner_xobject_parent_invocation_id": str((owner_invocation or {}).get("parent_invocation_id") or ""),
                "owner_xobject_nesting_depth": int(finite_number((owner_invocation or {}).get("nesting_depth"), 0)),
                "owner_xobject_invocation_ordinal": int(finite_number((owner_invocation or {}).get("ordinal"), 0)),
                "owner_xobject_invocation_ctm": (owner_invocation or {}).get("page_ctm") or [],
                "owner_xobject_resource_scope_id": str((owner_invocation or {}).get("resource_scope_id") or ""),
                "owner_xobject_resource_owner_xref": int(finite_number((owner_invocation or {}).get("resource_owner_xref"), 0)),
                "owner_xobject_shared_definition": bool((owner_invocation or {}).get("shared_definition")),
                "per_instance_native_write_supported": bool((owner_invocation or {}).get("per_instance_native_write_supported", True)),
            }
            clip_contexts.append(context)
            active.append(context)
            continue
        if row_type == "group":
            blend_mode = normalize_pdf_blend_mode(raw.get("blendmode"), "Normal")
            group_owner = next((context for context in reversed(active) if context.get("type") == "clip" and context.get("owner_xobject_id")), None)
            group_owner_xref = int(finite_number((group_owner or {}).get("owner_xobject_xref"), 0))
            extgstate_candidates = [
                item for item in extgstates
                if blend_mode != "Normal"
                and item.get("has_blend_mode")
                and normalize_pdf_blend_mode(item.get("blend_mode"), "Normal") == blend_mode
                and (
                    int(finite_number(item.get("resource_owner_xref"), 0)) == group_owner_xref
                    if group_owner_xref
                    else str(item.get("resource_owner_scope") or "") == "page"
                )
            ]
            extgstate = extgstate_candidates[0] if len(extgstate_candidates) == 1 else None
            context = {
                "id": str((extgstate or {}).get("id") or f"render-group-{render_index}"),
                "type": "group",
                "level": level,
                "render_index": render_index,
                "source": "extgstate" if extgstate else "native-render-hierarchy",
                "bbox": rect_payload(raw.get("rect")),
                "blend_mode": blend_mode,
                "extgstate_id": str((extgstate or {}).get("id") or ""),
                "mask_id": f"{extgstate.get('id')}-soft-mask" if extgstate and extgstate.get("has_soft_mask") else "",
            }
            group_contexts.append(context)
            active.append(context)
            continue

        active_clips = [context for context in active if context.get("type") == "clip"]
        active_groups = [context for context in active if context.get("type") == "group"]
        owner = next((context for context in reversed(active_clips) if context.get("owner_xobject_id")), None)
        owner_xref = int(finite_number((owner or {}).get("owner_xobject_xref"), 0))
        paint_alphas = [
            finite_number(raw.get(key), -1)
            for key in ("fill_opacity", "stroke_opacity")
            if raw.get(key) is not None
        ]
        active_blends = [
            normalize_pdf_blend_mode(context.get("blend_mode"), "Normal")
            for context in reversed(active_groups)
            if normalize_pdf_blend_mode(context.get("blend_mode"), "Normal") != "Normal"
        ]

        def exact_extgstate_score(item: dict[str, object]) -> float:
            resource_owner_xref = int(finite_number(item.get("resource_owner_xref"), 0))
            resource_owner_scope = str(item.get("resource_owner_scope") or "")
            if owner_xref:
                if resource_owner_xref != owner_xref:
                    return -1
            elif resource_owner_scope != "page":
                return -1
            score = 0.0
            blend_mode = normalize_pdf_blend_mode(item.get("blend_mode"), "Normal")
            if active_blends and blend_mode == active_blends[0]:
                score += 4.0
            for alpha in paint_alphas:
                if alpha < 0:
                    continue
                if abs(alpha - finite_number(item.get("fill_alpha"), 1)) <= 0.002:
                    score += 3.0
                if abs(alpha - finite_number(item.get("stroke_alpha"), 1)) <= 0.002:
                    score += 3.0
            return score if score > 0 else -1

        scored_extgstates = [
            (exact_extgstate_score(item), item)
            for item in extgstates
        ]
        best_score = max((score for score, _item in scored_extgstates), default=-1)
        best_extgstates = [item for score, item in scored_extgstates if score == best_score and score > 0]
        exact_extgstate = best_extgstates[0] if len(best_extgstates) == 1 else None
        ext_by_id = {str(item.get("id") or ""): item for item in extgstates}
        ext_groups = [
            context for context in active_groups
            if context.get("extgstate_id")
            and (
                int(finite_number(ext_by_id.get(str(context.get("extgstate_id") or ""), {}).get("resource_owner_xref"), 0)) == owner_xref
                if owner_xref
                else str(ext_by_id.get(str(context.get("extgstate_id") or ""), {}).get("resource_owner_scope") or "") == "page"
            )
        ]
        extgstate_memberships = list(dict.fromkeys([
            *[str(context.get("extgstate_id")) for context in ext_groups if context.get("extgstate_id")],
            *([str(exact_extgstate.get("id") or "")] if exact_extgstate and exact_extgstate.get("id") else []),
        ]))
        blend_memberships = [
            membership_id for membership_id in extgstate_memberships
            if normalize_pdf_blend_mode(ext_by_id.get(membership_id, {}).get("blend_mode"), "Normal") != "Normal"
        ]
        mask_memberships = [
            f"{membership_id}-soft-mask" for membership_id in extgstate_memberships
            if ext_by_id.get(membership_id, {}).get("has_soft_mask")
        ]
        memberships.append({
            "drawing_index": paint_index,
            "render_index": render_index,
            "content_stream_scope": "form-xobject-content-stream" if owner else "page-content-stream",
            "membership_status": "render-consensus" if owner else "page-render-sequence",
            "membership_provenance": (
                "native-render-hierarchy+form-invocation-bbox"
                if owner
                else "native-render-sequence"
            ),
            "content_stream_refs": [str(owner.get("owner_xobject_id"))] if owner else [],
            "owner_xobject_id": str((owner or {}).get("owner_xobject_id") or ""),
            "owner_xobject_xref": int(finite_number((owner or {}).get("owner_xobject_xref"), 0)),
            "owner_xobject_name": str((owner or {}).get("owner_xobject_name") or ""),
            "owner_xobject_invocation_id": str((owner or {}).get("owner_xobject_invocation_id") or ""),
            "owner_xobject_invocation_path": str((owner or {}).get("owner_xobject_invocation_path") or ""),
            "owner_xobject_parent_invocation_id": str((owner or {}).get("owner_xobject_parent_invocation_id") or ""),
            "owner_xobject_nesting_depth": int(finite_number((owner or {}).get("owner_xobject_nesting_depth"), 0)),
            "owner_xobject_invocation_ordinal": int(finite_number((owner or {}).get("owner_xobject_invocation_ordinal"), 0)),
            "owner_xobject_invocation_ctm": (owner or {}).get("owner_xobject_invocation_ctm") or [],
            "owner_xobject_resource_scope_id": str((owner or {}).get("owner_xobject_resource_scope_id") or ""),
            "owner_xobject_resource_owner_xref": int(finite_number((owner or {}).get("owner_xobject_resource_owner_xref"), 0)),
            "owner_xobject_shared_definition": bool((owner or {}).get("owner_xobject_shared_definition")),
            "per_instance_native_write_supported": bool((owner or {}).get("per_instance_native_write_supported", True)),
            "clip_memberships": [str(context.get("native_clip_id")) for context in active_clips if context.get("native_clip_id")],
            "mask_memberships": mask_memberships,
            "extgstate_memberships": extgstate_memberships,
            "blend_memberships": blend_memberships,
        })
        paint_index += 1

    return {
        "schema": "figureStudio.nativePdfRenderMembershipIndex.v1",
        "drawing_memberships": memberships,
        "clip_contexts": clip_contexts,
        "group_contexts": group_contexts,
        "form_xobject_member_count": len([row for row in memberships if row.get("owner_xobject_id")]),
        "clip_member_count": len([row for row in memberships if row.get("clip_memberships")]),
        "mask_member_count": len([row for row in memberships if row.get("mask_memberships")]),
        "extgstate_member_count": len([row for row in memberships if row.get("extgstate_memberships")]),
        "blend_member_count": len([row for row in memberships if row.get("blend_memberships")]),
        "full_native_equivalence": False,
    }


def native_pdf_advanced_feature_graph(
    page_id: str,
    drawings: list[dict[str, object]],
    image_resources: list[dict[str, object]],
    xobjects: list[dict[str, object]],
    extgstates: list[dict[str, object]],
    clip_paths: list[dict[str, object]],
    shadings: list[dict[str, object]],
    patterns: list[dict[str, object]],
) -> dict[str, object]:
    masks = [
        {
            "id": f"{page_id}-image-mask-{index}",
            "image_id": image.get("id"),
            "smask_xref": image.get("smask"),
            "mutation_status": "identity-only; soft-mask resource rewrite compiler required",
        }
        for index, image in enumerate(image_resources)
        if int(finite_number(image.get("smask"), 0)) > 0
    ]
    masks.extend([
        {
            "id": f"{row.get('id')}-soft-mask",
            "extgstate_xref": row.get("xref"),
            "resource_name": row.get("resource_name"),
            "soft_mask": row.get("soft_mask"),
            "soft_mask_xref": row.get("soft_mask_xref"),
            "content_stream_refs": row.get("content_stream_refs"),
            "binding_id": row.get("binding_id"),
            "resource_scope_id": row.get("resource_scope_id"),
            "resource_owner_scope": row.get("resource_owner_scope"),
            "resource_owner_xref": row.get("resource_owner_xref"),
            "owner_form_invocation_ids": row.get("owner_form_invocation_ids") or [],
            "owner_form_invocation_paths": row.get("owner_form_invocation_paths") or [],
            "shared_owner_form_definition": bool(row.get("shared_owner_form_definition")),
            "per_instance_native_write_supported": bool(row.get("per_instance_native_write_supported", True)),
            "mutation_status": "bounded ExtGState /SMask disable rewrite supported; mask shape editing remains compiler work",
        }
        for row in extgstates
        if row.get("has_soft_mask")
    ])
    blend_modes = [
        {
            "id": row.get("id"),
            "xref": row.get("xref"),
            "resource_name": row.get("resource_name"),
            "resource_names": row.get("resource_names"),
            "blend_mode": row.get("blend_mode"),
            "fill_alpha": row.get("fill_alpha"),
            "stroke_alpha": row.get("stroke_alpha"),
            "content_stream_refs": row.get("content_stream_refs"),
            "binding_id": row.get("binding_id"),
            "resource_scope_id": row.get("resource_scope_id"),
            "resource_owner_scope": row.get("resource_owner_scope"),
            "resource_owner_xref": row.get("resource_owner_xref"),
            "owner_form_invocation_ids": row.get("owner_form_invocation_ids") or [],
            "owner_form_invocation_paths": row.get("owner_form_invocation_paths") or [],
            "shared_owner_form_definition": bool(row.get("shared_owner_form_definition")),
            "per_instance_native_write_supported": bool(row.get("per_instance_native_write_supported", True)),
            "mutation_status": row.get("mutation_status"),
        }
        for row in extgstates
        if row.get("has_blend_mode")
    ]
    return {
        "schema": "figureStudio.nativePdfAdvancedFeatureGraph.v1",
        "page_descriptor_id": page_id,
        "clip_paths": clip_paths,
        "masks": masks,
        "filters": [],
        "blend_modes": blend_modes,
        "gradients": shadings,
        "patterns": patterns,
        "shadings": shadings,
        "xobjects": xobjects,
        "extgstates": extgstates,
        "drawing_sequence_count": len(drawings),
        "mutation_capabilities": {
            "semantic_clip_graph_rewrite": bool(clip_paths),
            "bounded_content_stream_clip_path_disable": bool(clip_paths),
            "semantic_mask_graph_rewrite": bool([row for row in extgstates if row.get("has_soft_mask")]),
            "bounded_extgstate_soft_mask_disable": bool([row for row in extgstates if row.get("has_soft_mask")]),
            "semantic_filter_graph_rewrite": False,
            "semantic_blend_mode_rewrite": bool(blend_modes),
            "bounded_extgstate_blend_mode_rewrite": bool(blend_modes),
            "bounded_extgstate_opacity_rewrite": bool(extgstates),
            "bounded_shading_function_color_rewrite": bool([
                row for row in shadings
                if int(finite_number(row.get("function_xref"), 0)) > 0 and int(finite_number(row.get("function_type"), 0)) == 2
            ]),
            "gradient_mesh_pattern_native_write": bool(patterns or shadings),
        },
        "mutation_status": (
            "bounded clip/blend/mask graphics-state rewrites available; arbitrary clip/mask/filter graph mutation still requires a broader native PDF compiler"
            if blend_modes or clip_paths
            else "resource identities preserved; semantic graph mutation requires a broader native PDF compiler"
        ),
    }


def native_pdf_descriptor_tree(doc: object, page: object, filename: str, page_number: int) -> dict[str, object]:
    page_xref = int(finite_number(getattr(page, "xref", 0), 0))
    page_id = native_pdf_page_descriptor_id(page_number, page_xref)
    content_streams = native_pdf_content_stream_descriptors(doc, page, page_id)
    invocation_index = native_pdf_invocation_index(doc, page, page_number)
    try:
        drawings = page.get_drawings()
    except Exception:  # noqa: BLE001
        drawings = []
    image_resources = image_resource_rows(page, invocation_index)
    font_resources = font_resource_rows(doc, page, invocation_index)
    color_space_resources = color_space_resource_rows(doc, page_id, invocation_index)
    xobject_resources = xobject_descriptors(doc, page, page_id, invocation_index)
    link_named_color_space_paint_contexts(
        content_streams,
        page_xref,
        color_space_resources,
        invocation_index,
    )
    for xobject_resource in xobject_resources:
        link_named_color_space_paint_contexts(
            [xobject_resource],
            int(finite_number(xobject_resource.get("xref"), 0)),
            color_space_resources,
            invocation_index,
        )
    editable_xobject_streams = [row for row in xobject_resources if row.get("editable_content_stream")]
    editable_content_streams = content_streams + editable_xobject_streams
    extgstate_resources = extgstate_resource_rows(doc, page, page_id, editable_content_streams, invocation_index)
    clip_path_resources = content_stream_clip_path_rows(doc, page_id, editable_content_streams)
    shading_resources = shading_resource_rows(doc, page, page_id, editable_content_streams, invocation_index)
    pattern_resources = pattern_resource_rows(doc, page, page_id, editable_content_streams, invocation_index)
    render_membership_index = native_pdf_render_memberships(
        page,
        xobject_resources,
        clip_path_resources,
        extgstate_resources,
    )
    drawing_memberships = render_membership_index.get("drawing_memberships") or []
    drawing_descriptors = [
        drawing_descriptor(
            drawing,
            page_number,
            index,
            page_id,
            content_streams,
            drawing_memberships[index] if index < len(drawing_memberships) else None,
        )
        for index, drawing in enumerate(drawings[:MAX_NATIVE_PDF_DESCRIPTORS])
    ]
    text_rows = text_descriptors(page, page_number)
    link_text_font_resources(text_rows, font_resources, invocation_index)
    image_rows = image_block_descriptors(page, page_number, len(drawing_descriptors) + len(text_rows))
    link_image_shading_resources(image_rows, shading_resources, invocation_index)
    descriptors = (drawing_descriptors + text_rows + image_rows)[:MAX_NATIVE_PDF_DESCRIPTORS]
    advanced_feature_graph = native_pdf_advanced_feature_graph(
        page_id,
        drawing_descriptors,
        image_resources,
        xobject_resources,
        extgstate_resources,
        clip_path_resources,
        shading_resources,
        pattern_resources,
    )
    advanced_feature_graph["render_membership_index"] = render_membership_index
    advanced_feature_graph["invocation_index"] = invocation_index
    return {
        "schema": "figureStudio.nativePdfDescriptorTree.v1",
        "schema_extensions": ["figureStudio.nativePdfInvocationIndex.v1"],
        "source_pdf_filename": filename or "uploaded.pdf",
        "page_number": page_number,
        "page_count": int(finite_number(getattr(doc, "page_count", 0), 0)),
        "page_descriptor_id": page_id,
        "page_xref": page_xref,
        "source_page_size": rect_payload(getattr(page, "rect", None)),
        "xref_length": int(finite_number(doc.xref_length() if hasattr(doc, "xref_length") else 0, 0)),
        "descriptor_limit": MAX_NATIVE_PDF_DESCRIPTORS,
        "object_counts": {
            "drawing_count": len(drawings),
            "text_span_count": len(text_rows),
            "image_block_count": len(image_rows),
            "descriptor_count": len(descriptors),
            "omitted_descriptor_count": max(0, len(drawings) + len(text_rows) + len(image_rows) - len(descriptors)),
            "content_stream_count": len(content_streams),
            "xobject_count": len(xobject_resources),
            "form_invocation_count": int(finite_number(invocation_index.get("form_invocation_count"), 0)),
            "nested_form_invocation_count": int(finite_number(invocation_index.get("nested_form_invocation_count"), 0)),
            "shared_form_invocation_count": int(finite_number(invocation_index.get("shared_form_invocation_count"), 0)),
            "resource_scope_count": int(finite_number(invocation_index.get("resource_scope_count"), 0)),
            "resource_usage_count": int(finite_number(invocation_index.get("resource_usage_count"), 0)),
            "color_space_count": len(color_space_resources),
            "preserve_only_color_space_count": len([row for row in color_space_resources if row.get("preserve_only")]),
            "xobject_content_stream_count": len(editable_xobject_streams),
            "extgstate_count": len(extgstate_resources),
            "mask_count": len(advanced_feature_graph["masks"]),
            "blend_mode_count": len(advanced_feature_graph["blend_modes"]),
            "clip_path_count": len(advanced_feature_graph["clip_paths"]),
            "gradient_count": len(advanced_feature_graph["gradients"]),
            "shading_count": len(shading_resources),
            "pattern_count": len(pattern_resources),
            "mesh_shading_count": len([row for row in shading_resources if row.get("mesh_shading")]),
            "form_xobject_member_count": int(finite_number(render_membership_index.get("form_xobject_member_count"), 0)),
            "clip_member_count": int(finite_number(render_membership_index.get("clip_member_count"), 0)),
            "mask_member_count": int(finite_number(render_membership_index.get("mask_member_count"), 0)),
            "blend_member_count": int(finite_number(render_membership_index.get("blend_member_count"), 0)),
        },
        "resources": {
            "content_stream_count": len(content_streams),
            "image_count": len(image_resources),
            "font_count": len(font_resources),
            "color_space_count": len(color_space_resources),
            "xobject_count": len(xobject_resources),
            "xobject_content_stream_count": len(editable_xobject_streams),
            "extgstate_count": len(extgstate_resources),
            "shading_count": len(shading_resources),
            "pattern_count": len(pattern_resources),
            "content_streams": content_streams,
            "images": image_resources,
            "fonts": font_resources,
            "color_spaces": color_space_resources,
            "xobjects": xobject_resources,
            "extgstates": extgstate_resources,
            "shadings": shading_resources,
            "patterns": pattern_resources,
            "resource_scopes": invocation_index.get("resource_scopes") or [],
            "resource_usages": invocation_index.get("resource_usages") or [],
            "form_invocations": invocation_index.get("form_invocations") or [],
            "invocation_index": invocation_index,
            "render_membership_index": render_membership_index,
        },
        "advanced_feature_graph": advanced_feature_graph,
        "descriptors": descriptors,
        "capabilities": {
            "native_object_identity": "qpdf-page-xref-resource-descriptors",
            "content_stream_mutation_supported": True,
            "form_xobject_content_stream_mutation_supported": bool(editable_xobject_streams),
            "content_stream_operation_matrix": native_pdf_content_stream_operation_matrix(),
            "supported_content_stream_descriptor_types": sorted(SUPPORTED_NATIVE_PDF_CONTENT_STREAM_DESCRIPTOR_TYPES),
            "resource_graph_available": True,
            "recursive_form_invocation_index_available": True,
            "form_local_resource_ownership_available": True,
            "source_color_space_inspection_supported": bool(color_space_resources),
            "preserve_only_color_models": sorted({
                str(row.get("native_color_model") or "")
                for row in color_space_resources
                if row.get("preserve_only") and row.get("native_color_model")
            }),
            "special_color_space_mutation_supported": False,
            "per_instance_shared_form_native_write_supported": False,
            "semantic_blend_mode_rewrite_supported": bool(advanced_feature_graph["blend_modes"]),
            "semantic_clip_graph_rewrite_supported": bool(advanced_feature_graph["clip_paths"]),
            "native_gradient_stop_rewrite_supported": bool([
                row for row in shading_resources
                if int(finite_number(row.get("function_xref"), 0)) > 0 and int(finite_number(row.get("function_type"), 0)) == 2
            ]),
            "native_shading_background_rewrite_supported": bool(shading_resources),
            "native_pattern_stream_rewrite_supported": bool([
                row for row in pattern_resources
                if int(finite_number(row.get("pattern_type"), 0)) == 1
                and int(finite_number(row.get("paint_type"), 0)) == 1
                and int(finite_number(row.get("stream_byte_size"), 0)) > 0
            ]),
            "writer_required_for_native_equivalence": True,
            "source_backed_roundtrip_required": True,
        },
    }


def font_name_record(font: object, name_id: int) -> str:
    name_table = font.get("name")
    if name_table is None:
        return ""
    for record in name_table.names:
        if int(getattr(record, "nameID", 0)) != name_id:
            continue
        try:
            value = record.toUnicode().strip()
        except Exception:  # noqa: BLE001
            value = ""
        if value:
            return value
    return ""


def font_embedding_permission(font: object) -> dict[str, object]:
    os2 = font.get("OS/2")
    if os2 is None:
        return {
            "status": "unknown-no-os2",
            "fs_type": None,
            "export_embedding_allowed": False,
            "reason": "The embedded font program has no OS/2 embedding-permission table.",
        }
    fs_type = int(getattr(os2, "fsType", 0) or 0)
    if fs_type & 0x0002:
        status = "restricted-license"
        allowed = False
        reason = "The source font marks embedding as restricted."
    elif fs_type & 0x0200:
        status = "bitmap-only"
        allowed = False
        reason = "The source font permits bitmap embedding only."
    elif fs_type & 0x0100:
        status = "no-subsetting"
        allowed = False
        reason = "The source font forbids subsetting, while the client PDF writer emits a glyph subset."
    elif fs_type & 0x0008:
        status = "editable"
        allowed = True
        reason = "Editable embedding is permitted."
    elif fs_type & 0x0004:
        status = "preview-print"
        allowed = False
        reason = "Preview/print-only embedding is not used because Figure Tool exports remain editable PDF documents."
    else:
        status = "installable"
        allowed = True
        reason = "Installable embedding is permitted."
    return {
        "status": status,
        "fs_type": fs_type,
        "export_embedding_allowed": allowed,
        "reason": reason,
    }


def pdf_to_unicode_cid_map(doc: object, to_unicode_xref: int) -> dict[int, int]:
    if to_unicode_xref <= 0:
        return {}
    try:
        text = (doc.xref_stream(to_unicode_xref) or b"").decode("latin-1", errors="replace")
    except Exception:  # noqa: BLE001
        return {}
    mapping: dict[int, int] = {}
    mode = ""
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line.endswith("beginbfchar"):
            mode = "bfchar"
            continue
        if line == "endbfchar":
            mode = ""
            continue
        if line.endswith("beginbfrange"):
            mode = "bfrange"
            continue
        if line == "endbfrange":
            mode = ""
            continue
        try:
            if mode == "bfchar":
                match = re.fullmatch(r"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>", line)
                if not match:
                    continue
                source, target = match.groups()
                target_text = bytes.fromhex(target).decode("utf-16-be")
                if len(target_text) == 1:
                    mapping[int(source, 16)] = ord(target_text)
            elif mode == "bfrange":
                match = re.fullmatch(r"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>", line)
                if not match:
                    continue
                start, end, target = match.groups()
                start_value = int(start, 16)
                end_value = int(end, 16)
                target_text = bytes.fromhex(target).decode("utf-16-be")
                if len(target_text) != 1 or end_value - start_value > 65535:
                    continue
                target_value = ord(target_text)
                for offset, cid in enumerate(range(start_value, end_value + 1)):
                    mapping[cid] = target_value + offset
        except (ValueError, UnicodeDecodeError):
            continue
    return mapping


def pdf_cid_to_gid_map(doc: object, descendant_xref: int, glyph_count: int) -> dict[int, int]:
    if descendant_xref <= 0:
        return {value: value for value in range(glyph_count)}
    try:
        key_type, key_value = doc.xref_get_key(descendant_xref, "CIDToGIDMap")
    except Exception:  # noqa: BLE001
        key_type, key_value = "null", ""
    if key_type != "xref":
        return {value: value for value in range(glyph_count)}
    xref = pdf_xref_reference(key_value)
    try:
        data = doc.xref_stream(xref) or b""
    except Exception:  # noqa: BLE001
        return {}
    return {
        cid: int.from_bytes(data[offset:offset + 2], "big")
        for cid, offset in enumerate(range(0, len(data) - 1, 2))
    }


def add_unicode_cmap_from_pdf(font: object, doc: object, resource: dict[str, object]) -> tuple[dict[int, str], bool]:
    try:
        existing = font.getBestCmap() or {}
    except KeyError:
        existing = {}
    if existing:
        return {int(codepoint): glyph for codepoint, glyph in existing.items()}, False
    cid_to_unicode = pdf_to_unicode_cid_map(doc, int(finite_number(resource.get("to_unicode_xref"), 0)))
    glyph_order = font.getGlyphOrder()
    cid_to_gid = pdf_cid_to_gid_map(doc, int(finite_number(resource.get("descendant_font_xref"), 0)), len(glyph_order))
    unicode_to_glyph = {
        unicode_value: glyph_order[gid]
        for cid, unicode_value in cid_to_unicode.items()
        for gid in [cid_to_gid.get(cid, cid)]
        if 0 <= gid < len(glyph_order) and 0 <= unicode_value <= 0x10FFFF
    }
    if not unicode_to_glyph:
        return {}, False
    from fontTools.ttLib import newTable  # type: ignore
    from fontTools.ttLib.tables._c_m_a_p import CmapSubtable  # type: ignore

    cmap_table = newTable("cmap")
    cmap_table.tableVersion = 0
    cmap_table.tables = []
    bmp = {codepoint: glyph for codepoint, glyph in unicode_to_glyph.items() if codepoint < 0xFFFF}
    if bmp:
        subtable = CmapSubtable.newSubtable(4)
        subtable.platformID = 3
        subtable.platEncID = 1
        subtable.language = 0
        subtable.cmap = bmp
        cmap_table.tables.append(subtable)
    full = CmapSubtable.newSubtable(12)
    full.platformID = 3
    full.platEncID = 10
    full.language = 0
    full.cmap = unicode_to_glyph
    cmap_table.tables.append(full)
    font["cmap"] = cmap_table
    if "post" not in font:
        post = newTable("post")
        post.formatType = 3.0
        post.italicAngle = 0
        post.underlinePosition = -100
        post.underlineThickness = 50
        post.isFixedPitch = 0
        post.minMemType42 = 0
        post.maxMemType42 = 0
        post.minMemType1 = 0
        post.maxMemType1 = 0
        font["post"] = post
    return unicode_to_glyph, True


def extract_pikepdf_font_program(doc: PikePdfDocument, xref: int) -> tuple[str, str, str, bytes]:
    """Return the embedded program owned by one source PDF font resource."""

    import pikepdf

    font = pikepdf_object_by_xref(doc.pdf, xref)
    if not isinstance(font, pikepdf.Dictionary):
        raise ValueError(f"PDF font resource {xref} is unavailable.")
    descendant = font
    descendants = font.get("/DescendantFonts")
    if isinstance(descendants, pikepdf.Array) and descendants and isinstance(descendants[0], pikepdf.Dictionary):
        descendant = descendants[0]
    descriptor = descendant.get("/FontDescriptor") or font.get("/FontDescriptor")
    if not isinstance(descriptor, pikepdf.Dictionary):
        raise ValueError("The source PDF font has no embedded font descriptor.")
    stream = None
    extension = ""
    program_type = ""
    for key, candidate_extension, candidate_type in (
        ("/FontFile2", "ttf", "TrueType"),
        ("/FontFile3", "otf", "OpenType"),
        ("/FontFile", "pfb", "Type1"),
    ):
        candidate = descriptor.get(key)
        if isinstance(candidate, pikepdf.Stream):
            stream = candidate
            extension = candidate_extension
            program_type = candidate_type
            if key == "/FontFile3":
                subtype = str(candidate.get("/Subtype") or "").lstrip("/")
                if subtype:
                    program_type = subtype
                    extension = "cff" if subtype in {"Type1C", "CIDFontType0C"} else "otf"
            break
    if stream is None:
        raise ValueError("The source PDF font has no embedded font program.")
    data = bytes(stream.read_bytes(pikepdf.StreamDecodeLevel.specialized))
    name = str(descendant.get("/BaseFont") or font.get("/BaseFont") or "").lstrip("/")
    return name, extension, program_type, data


def inspect_pdf_font_program(
    doc: object,
    resource: dict[str, object],
    requested_codepoints: set[int],
) -> dict[str, object]:
    xref = int(finite_number(resource.get("xref"), 0))
    result: dict[str, object] = {
        "schema": "figureStudio.pdfSourceFontProgram.v1",
        "resource_id": str(resource.get("id") or f"font-xref-{xref}"),
        "xref": xref,
        "resource_name": str(resource.get("resource_name") or ""),
        "base_font": str(resource.get("base_font") or ""),
        "font_type": str(resource.get("type") or ""),
        "encoding": str(resource.get("encoding") or ""),
        "subset": bool(resource.get("subset")),
        "to_unicode_status": str(resource.get("to_unicode_status") or "not-available"),
        "to_unicode_xref": int(finite_number(resource.get("to_unicode_xref"), 0)),
        "cid_font": bool(resource.get("cid_font")),
        "cid_encoding": str(resource.get("cid_encoding") or ""),
        "requested_codepoints": sorted(requested_codepoints),
        "full_native_equivalence": False,
    }
    try:
        extracted_name, extension, program_type, program_bytes = extract_pikepdf_font_program(doc, xref)
    except Exception as error:  # noqa: BLE001
        result.update({
            "status": "blocked",
            "reuse_status": "font-program-extraction-failed",
            "reason": str(error),
            "font_base64": "",
        })
        return result
    program_bytes = bytes(program_bytes or b"")
    result.update({
        "extracted_name": str(extracted_name or ""),
        "extension": str(extension or "").lower(),
        "program_type": str(program_type or ""),
        "font_program_byte_size": len(program_bytes),
        "font_program_sha256": hashlib.sha256(program_bytes).hexdigest() if program_bytes else "",
    })
    if not program_bytes or len(program_bytes) > MAX_PDF_FONT_PROGRAM_BYTES:
        result.update({
            "status": "blocked",
            "reuse_status": "font-program-unavailable" if not program_bytes else "font-program-too-large",
            "reason": "The embedded font program is unavailable or exceeds the bounded extraction limit.",
            "font_base64": "",
        })
        return result
    try:
        from fontTools.ttLib import TTFont  # type: ignore

        font = TTFont(BytesIO(program_bytes), lazy=False, recalcBBoxes=False, recalcTimestamp=False)
        try:
            cmap, cmap_reconstructed = add_unicode_cmap_from_pdf(font, doc, resource)
            available_codepoints = {int(value) for value in cmap}
            permission = font_embedding_permission(font)
            postscript_name = font_name_record(font, 6) or str(extracted_name or resource.get("normalized_base_font") or "SourceFont")
            family_name = font_name_record(font, 1) or str(resource.get("normalized_base_font") or postscript_name)
            export_program_bytes = program_bytes
            if cmap_reconstructed:
                output = BytesIO()
                font.save(output, reorderTables=False)
                export_program_bytes = output.getvalue()
        finally:
            font.close()
    except Exception as error:  # noqa: BLE001
        result.update({
            "status": "blocked",
            "reuse_status": "unsupported-font-program",
            "reason": f"The embedded font program cannot be registered by the client PDF writer: {error}",
            "font_base64": "",
        })
        return result
    missing_codepoints = sorted(requested_codepoints - available_codepoints)
    unicode_context_ok = not bool(resource.get("cid_font")) or str(resource.get("to_unicode_status")) == "embedded-cmap"
    supported_sfnt = program_bytes[:4] == b"\x00\x01\x00\x00"
    reusable = bool(
        supported_sfnt
        and permission.get("export_embedding_allowed")
        and not missing_codepoints
        and unicode_context_ok
    )
    reason = "Exact retained source font is reusable for reconstructed text export."
    reuse_status = "verified-source-font-reuse"
    if not supported_sfnt:
        reason = "Only TrueType-flavored embedded font programs are supported by the current client PDF writer."
        reuse_status = "unsupported-font-program"
    elif not permission.get("export_embedding_allowed"):
        reason = str(permission.get("reason") or "Font embedding permission could not be verified.")
        reuse_status = "embedding-not-permitted"
    elif missing_codepoints:
        reason = "The embedded source font does not cover every Unicode codepoint in the reconstructed run."
        reuse_status = "incomplete-glyph-coverage"
    elif not unicode_context_ok:
        reason = "The CID font has no inspectable ToUnicode map, so Unicode reconstruction ownership is not proven."
        reuse_status = "unicode-map-unverified"
    export_program_sha256 = hashlib.sha256(export_program_bytes).hexdigest()
    result.update({
        "status": "ready" if reusable else "blocked",
        "reuse_status": reuse_status,
        "reason": reason,
        "postscript_name": postscript_name,
        "family_name": family_name,
        "client_font_alias": f"FS_PDF_{export_program_sha256[:14]}",
        "embedding_permission": permission,
        "glyph_coverage_status": "complete" if not missing_codepoints else "incomplete",
        "covered_codepoint_count": len(requested_codepoints) - len(missing_codepoints),
        "missing_codepoints": missing_codepoints,
        "source_font_program_sha256": result.get("font_program_sha256") or "",
        "unicode_cmap_reconstructed_from_to_unicode": cmap_reconstructed,
        "export_font_program_byte_size": len(export_program_bytes),
        "export_font_program_sha256": export_program_sha256,
        "font_base64": base64.b64encode(export_program_bytes).decode("ascii") if reusable else "",
    })
    return result


def inspect_pdf_source_fonts(
    pdf_bytes: bytes,
    filename: str,
    page_number: int,
    packet: dict[str, object],
) -> dict[str, object]:
    tree = build_native_pdf_ir_shadow_payload(pdf_bytes, filename, page_number)
    text_rows = {
        str(row.get("id") or ""): row
        for row in tree.get("nodes", [])
        if isinstance(row, dict) and row.get("kind") == "text-run" and row.get("id")
    }
    resources: dict[str, dict[str, object]] = {}
    resource_ids_by_xref: dict[int, str] = {}
    for row in text_rows.values():
        metadata = row.get("metadata") if isinstance(row.get("metadata"), dict) else {}
        font = metadata.get("font") if isinstance(metadata.get("font"), dict) else {}
        code_map = font.get("code_map") if isinstance(font.get("code_map"), dict) else {}
        resource_xref = pdf_xref_reference(row.get("resource_ref") or font.get("resource_ref"))
        if resource_xref <= 0:
            continue
        resource_id = f"font-xref-{resource_xref}"
        resource_ids_by_xref[resource_xref] = resource_id
        resources.setdefault(resource_id, {
            "id": resource_id,
            "xref": resource_xref,
            "resource_name": str(font.get("resource_name") or ""),
            "base_font": str(font.get("base_font") or ""),
            "normalized_base_font": re.sub(r"^[A-Z]{6}\+", "", str(font.get("base_font") or "")),
            "type": str(font.get("subtype") or ""),
            "encoding": str(font.get("encoding") or ""),
            "subset": bool(font.get("subset")),
            "to_unicode_status": "embedded-cmap" if pdf_xref_reference(font.get("to_unicode_ref") or code_map.get("to_unicode_ref")) > 0 else "not-available",
            "to_unicode_xref": pdf_xref_reference(font.get("to_unicode_ref") or code_map.get("to_unicode_ref")),
            "cid_font": bool(font.get("cid_font")),
            "cid_encoding": str(font.get("encoding") or ""),
            "descendant_font_xref": pdf_xref_reference(code_map.get("descendant_font_ref")),
        })

    requests = packet.get("runs") if isinstance(packet.get("runs"), list) else []
    if len(requests) > MAX_PDF_FONT_REQUESTS:
        raise ValueError(f"At most {MAX_PDF_FONT_REQUESTS} reconstructed text runs may be inspected per request.")

    doc = PikePdfDocument.open(pdf_bytes)
    try:
        if page_number < 1 or page_number > doc.page_count:
            raise ValueError(f"PDF has {doc.page_count} page(s); page {page_number} is not available.")
        run_results: list[dict[str, object]] = []
        codepoints_by_resource: dict[str, set[int]] = {}
        for request in requests:
            request = request if isinstance(request, dict) else {}
            descriptor_id = str(request.get("descriptor_id") or request.get("descriptorId") or "")
            row = text_rows.get(descriptor_id)
            row_metadata = row.get("metadata") if isinstance((row or {}).get("metadata"), dict) else {}
            resource_xref = pdf_xref_reference((row or {}).get("resource_ref"))
            expected_xref = int(finite_number(request.get("expected_xref") or request.get("expectedXref"), resource_xref))
            if resource_xref <= 0 and expected_xref in resource_ids_by_xref:
                resource_xref = expected_xref
            resource_id = resource_ids_by_xref.get(resource_xref, "")
            expected_resource_id = str(request.get("expected_resource_id") or request.get("expectedResourceId") or resource_id)
            source_text = str(row_metadata.get("decoded_text") or "") if row_metadata.get("text_decode_status") == "proven" else ""
            current_text = str(request.get("current_text") if request.get("current_text") is not None else source_text)
            exact = bool(
                resource_id
                and expected_resource_id == resource_id
                and expected_xref == resource_xref
            )
            association = "proven-native-font-resource-xref" if exact else "unverified"
            run_results.append({
                "descriptor_id": descriptor_id,
                "resource_id": resource_id,
                "ownership_status": association,
                "exact_resource_ownership": exact,
                "source_text": source_text,
                "current_text": current_text,
            })
            if exact:
                codepoints_by_resource.setdefault(resource_id, set()).update(ord(character) for character in current_text)
        program_results = []
        for resource_id, codepoints in codepoints_by_resource.items():
            resource = resources.get(resource_id)
            if resource:
                program_results.append(inspect_pdf_font_program(doc, resource, codepoints))
    finally:
        doc.close()
    reusable_ids = {str(row.get("resource_id") or "") for row in program_results if row.get("status") == "ready"}
    for row in run_results:
        row["reuse_status"] = "verified-source-font-reuse" if row.get("resource_id") in reusable_ids else "outline-fallback-required"
    return {
        "ok": True,
        "schema": "figureStudio.pdfSourceFontInspection.v1",
        "source_pdf_filename": filename or "uploaded.pdf",
        "page_number": page_number,
        "runs": run_results,
        "resources": program_results,
        "reusable_resource_count": len(reusable_ids),
        "outline_fallback_run_count": sum(1 for row in run_results if row.get("reuse_status") != "verified-source-font-reuse"),
        "font_programs_persisted_in_project": False,
        "native_pdf_text_stream_mutated": False,
        "full_native_equivalence": False,
    }


def parse_multipart(body: bytes, content_type: str) -> dict[str, dict[str, object]]:
    """Parse the small Figure Tool multipart envelope without trimming payload bytes."""

    match = re.search(r"boundary=(?P<boundary>[^;]+)", content_type or "", re.IGNORECASE)
    if not match:
        raise ValueError("Expected multipart/form-data with a boundary.")
    boundary = match.group("boundary").strip().strip('"').encode("utf-8")
    fields: dict[str, dict[str, object]] = {}
    marker = b"--" + boundary
    for raw_part in body.split(marker):
        if not raw_part:
            continue
        if raw_part.startswith(b"--"):
            break
        part = raw_part[2:] if raw_part.startswith(b"\r\n") else raw_part
        if part.endswith(b"\r\n"):
            # Remove only the multipart framing CRLF immediately preceding the
            # next boundary. Payload whitespace and binary bytes are preserved.
            part = part[:-2]
        if b"\r\n\r\n" not in part:
            continue
        raw_headers, data = part.split(b"\r\n\r\n", 1)
        headers = raw_headers.decode("utf-8", errors="replace").split("\r\n")
        disposition = next((h for h in headers if h.lower().startswith("content-disposition:")), "")
        name_match = re.search(r'name="([^"]+)"', disposition)
        if not name_match:
            continue
        filename_match = re.search(r'filename="([^"]*)"', disposition)
        name = name_match.group(1)
        fields[name] = {
            "filename": filename_match.group(1) if filename_match else "",
            "data": data,
        }
    return fields


def build_native_pdf_ir_shadow_payload(
    pdf_bytes: bytes,
    filename: str,
    page_number: int,
) -> dict[str, object]:
    """Build the QPDF-backed source-native PDF index."""

    try:
        from pdf_native.parser import build_native_pdf_ir_shadow
    except ModuleNotFoundError:
        from scripts.pdf_native.parser import build_native_pdf_ir_shadow

    payload = build_native_pdf_ir_shadow(
        pdf_bytes,
        filename,
        page_number,
    )
    comparison = payload.get("shadow_comparison")
    if isinstance(comparison, dict):
        comparison["legacy_tree_available"] = False
        comparison["legacy_schema"] = ""
        comparison["legacy_descriptor_count"] = 0
        comparison["legacy_omitted_descriptor_count"] = 0
        comparison["legacy_comparison_retired"] = True
        comparison["legacy_identity_authoritative"] = False
    return payload


def native_edit_descriptors_from_packet(packet: dict[str, object]) -> list[dict[str, object]]:
    packets = packet.get("packets") if isinstance(packet, dict) else []
    source_packets = packets if isinstance(packets, list) else [packet]
    descriptors: list[dict[str, object]] = []
    for entry in source_packets:
        if not isinstance(entry, dict):
            continue
        plan = entry.get("edit_plan") if isinstance(entry.get("edit_plan"), dict) else {}
        raw_descriptors = plan.get("edit_descriptors") if isinstance(plan, dict) else []
        if isinstance(raw_descriptors, list):
            descriptors.extend(descriptor for descriptor in raw_descriptors if isinstance(descriptor, dict))
    return descriptors[:MAX_NATIVE_PDF_MUTATION_DESCRIPTORS]


def native_pdf_descriptor_operation_kind(descriptor: dict[str, object]) -> str:
    descriptor_type = str(descriptor.get("descriptor_type") or descriptor.get("type") or "").strip()
    action = str(descriptor.get("action") or "").strip()
    if descriptor_type == "annotation_rectangle_overlay" or action == "write_annotation_rectangle_overlay":
        return "annotation_rectangle_overlay"
    target_extgstate_xref = int(finite_number(descriptor.get("target_extgstate_xref") or descriptor.get("extgstate_xref"), 0))
    if descriptor_type == "advanced_feature_graph_edit" and action == "rewrite_extgstate_appearance":
        return "extgstate_appearance_rewrite" if target_extgstate_xref > 0 else ""
    if descriptor_type == "advanced_feature_graph_edit" and action == "rewrite_extgstate_blend_mode":
        return "extgstate_blend_rewrite" if target_extgstate_xref > 0 else ""
    if descriptor_type == "advanced_feature_graph_edit" and action == "rewrite_extgstate_opacity":
        return "extgstate_alpha_rewrite" if target_extgstate_xref > 0 else ""
    if descriptor_type == "advanced_feature_graph_edit" and action == "disable_extgstate_soft_mask":
        return "extgstate_soft_mask_disable" if target_extgstate_xref > 0 else ""
    target_clip_stream_xref = int(finite_number(descriptor.get("target_content_stream_xref") or descriptor.get("content_stream_xref"), 0))
    if descriptor_type == "advanced_feature_graph_edit" and action == "disable_content_stream_clip_path":
        return "content_stream_clip_disable" if target_clip_stream_xref > 0 else ""
    target_function_xref = int(finite_number(descriptor.get("target_function_xref") or descriptor.get("function_xref"), 0))
    if descriptor_type == "gradient_stop_edit" and action == "rewrite_shading_function_colors":
        return "shading_function_color_rewrite" if target_function_xref > 0 else ""
    target_shading_xref = int(finite_number(descriptor.get("target_shading_xref") or descriptor.get("shading_xref"), 0))
    if descriptor_type == "gradient_mesh_pattern_edit" and action == "rewrite_shading_background_color":
        return "shading_background_color_rewrite" if target_shading_xref > 0 else ""
    target_pattern_xref = int(finite_number(descriptor.get("target_pattern_xref") or descriptor.get("pattern_xref"), 0))
    if descriptor_type == "gradient_mesh_pattern_edit" and action == "rewrite_tiling_pattern_stream_colors":
        return "tiling_pattern_stream_color_rewrite" if target_pattern_xref > 0 else ""
    source_path = descriptor.get("source_path_pdf_user_space") or descriptor.get("source_path") or {}
    has_source_path_commands = isinstance(source_path, dict) and isinstance(source_path.get("commands"), list) and bool(source_path.get("commands"))
    target_xref = int(finite_number(descriptor.get("target_content_stream_xref") or descriptor.get("content_stream_xref"), 0))
    if descriptor_type == "object_tree_mutation" and action == "replace_simple_path_content_stream":
        return "content_stream_rewrite" if has_source_path_commands and target_xref > 0 else ""
    if descriptor_type == "object_tree_mutation" and action == "disable_paint_operator_run":
        operator = str(descriptor.get("target_operator") or descriptor.get("operator") or "").strip()
        return "content_stream_paint_disable" if target_xref > 0 and operator in PDF_PAINT_OPERATOR_TOKENS else ""
    if descriptor_type == "object_tree_mutation" and action == "rewrite_rgb_color_operator_run":
        operator = str(descriptor.get("target_operator") or descriptor.get("operator") or "").strip()
        return "content_stream_rgb_color_rewrite" if target_xref > 0 and operator in PDF_RGB_COLOR_OPERATOR_TOKENS else ""
    if descriptor_type == "object_tree_mutation" and action in {"rewrite_selected_use_path_appearance", "rewrite_selected_use_appearance_stack"}:
        return "selected_use_path_appearance_rewrite" if target_xref > 0 and bool(descriptor.get("clone_and_rebind_shared_form")) else ""
    if descriptor_type == "object_tree_mutation" and action == "rewrite_stroke_width_operator_run":
        operator = str(descriptor.get("target_operator") or descriptor.get("operator") or "").strip()
        return "content_stream_stroke_width_rewrite" if target_xref > 0 and operator in PDF_STROKE_WIDTH_OPERATOR_TOKENS else ""
    if descriptor_type == "object_tree_mutation" and action == "transform_path_geometry_operator_run":
        operator = str(descriptor.get("target_operator") or descriptor.get("operator") or "").strip()
        return "content_stream_path_geometry_transform" if target_xref > 0 and operator in PDF_PATH_GEOMETRY_OPERATOR_TOKENS else ""
    if descriptor_type == "path_boolean_operation" and action == "replace_path_geometry_with_boolean_result":
        operator = str(descriptor.get("target_operator") or descriptor.get("operator") or "").strip()
        return "content_stream_path_boolean_replace" if target_xref > 0 and operator in PDF_PATH_GEOMETRY_OPERATOR_TOKENS and has_source_path_commands else ""
    if descriptor_type in {"path_anchor_edit", "path_control_handle_edit"} and action in {"replace_path_geometry_with_anchor_edit", "replace_path_geometry_with_control_handle_edit", "replace_native_path_geometry"}:
        operator = str(descriptor.get("target_operator") or descriptor.get("operator") or "").strip()
        return "content_stream_path_anchor_replace" if target_xref > 0 and operator in PDF_PATH_GEOMETRY_OPERATOR_TOKENS and has_source_path_commands else ""
    if descriptor_type in SUPPORTED_NATIVE_PDF_CONTENT_STREAM_DESCRIPTOR_TYPES or action in {
        "write_path_overlay",
        "write_path_boolean_overlay",
        "write_path_anchor_overlay",
        "write_path_control_handle_overlay",
    }:
        return "path_overlay" if has_source_path_commands else ""
    return ""


def native_pdf_descriptor_targets_xobject_content_stream(descriptor: dict[str, object]) -> bool:
    scope = str(
        descriptor.get("target_content_stream_scope")
        or descriptor.get("content_stream_scope")
        or descriptor.get("operator_identity_scope")
        or ""
    ).strip()
    return scope == "form-xobject-content-stream" or int(finite_number(descriptor.get("target_xobject_xref") or 0, 0)) > 0


def pdf_rect_from_descriptor(fitz_module, page: object, descriptor: dict[str, object]) -> object | None:
    rect = descriptor.get("source_rect_pdf_user_space") or descriptor.get("source_rect") or descriptor.get("rect")
    if not isinstance(rect, dict):
        return None
    x = finite_number(rect.get("x") if "x" in rect else rect.get("left"), 0)
    y_bottom = finite_number(rect.get("y") if "y" in rect else rect.get("bottom"), 0)
    width = max(0.25, finite_number(rect.get("width") if "width" in rect else rect.get("w"), 1))
    height = max(0.25, finite_number(rect.get("height") if "height" in rect else rect.get("h"), 1))
    origin = str(rect.get("origin") or descriptor.get("origin") or "bottom-left").strip().lower()
    if hasattr(page, "descriptor_rect"):
        return page.descriptor_rect(x, y_bottom, width, height, origin)
    page_height = finite_number(getattr(getattr(page, "rect", None), "height", 0), 0)
    y0 = max(0.0, page_height - y_bottom - height)
    y1 = max(y0 + 0.25, page_height - y_bottom)
    return fitz_module.Rect(x, y0, x + width, y1)


def path_point_from_source_space(fitz_module, page: object, point: object, origin: str) -> object | None:
    if not isinstance(point, (list, tuple)) or len(point) < 2:
        return None
    page_height = finite_number(getattr(getattr(page, "rect", None), "height", 0), 0)
    x = finite_number(point[0], 0)
    y = finite_number(point[1], 0)
    if hasattr(page, "descriptor_point"):
        return page.descriptor_point(x, y, origin)
    if origin == "bottom-left":
        y = page_height - y
    return fitz_module.Point(x, y)


def path_commands_from_descriptor(descriptor: dict[str, object]) -> tuple[list[list[object]], str]:
    source_path = descriptor.get("source_path_pdf_user_space") or descriptor.get("source_path") or {}
    if not isinstance(source_path, dict):
        return [], "bottom-left"
    commands = source_path.get("commands") or descriptor.get("path_commands") or []
    origin = str(source_path.get("origin") or "bottom-left").strip() or "bottom-left"
    if not isinstance(commands, list):
        return [], origin
    normalized: list[list[object]] = []
    for command in commands[:MAX_NATIVE_PDF_MUTATION_PATH_COMMANDS]:
        if not isinstance(command, (list, tuple)) or not command:
            continue
        operator = str(command[0] or "").upper()
        if operator not in {"M", "L", "C", "Q", "Z"}:
            continue
        normalized.append([operator, *list(command[1:])])
    return normalized, origin


def pdf_operator_number(value: object) -> str:
    number = round(finite_number(value), 4)
    text = f"{number:.4f}".rstrip("0").rstrip(".")
    return text if text and text != "-0" else "0"


def descriptor_first_present(descriptor: dict[str, object], keys: list[str], default: object) -> object:
    for key in keys:
        value = descriptor.get(key)
        if value not in (None, ""):
            return value
    return default


def pdf_stream_point(page: object, point: object, origin: str) -> tuple[float, float] | None:
    if not isinstance(point, (list, tuple)) or len(point) < 2:
        return None
    x = finite_number(point[0], 0)
    y = finite_number(point[1], 0)
    if hasattr(page, "descriptor_point"):
        mapped = page.descriptor_point(x, y, origin)
        return (round(mapped.x, 4), round(mapped.y, 4))
    page_height = finite_number(getattr(getattr(page, "rect", None), "height", 0), 0)
    if origin not in {"bottom-left", "pdf-stream", "native-stream"}:
        y = page_height - y
    return (round(x, 4), round(y, 4))


def pdf_stream_color_triplet(value: object, fallback: str) -> tuple[float, float, float]:
    return tuple(round(part, 4) for part in hex_color_triplet(value, fallback))


def pdf_path_content_stream_from_descriptor(page: object, descriptor: dict[str, object]) -> bytes | None:
    commands, origin = path_commands_from_descriptor(descriptor)
    if not commands:
        return None
    style = descriptor.get("style") if isinstance(descriptor.get("style"), dict) else {}
    stroke = pdf_stream_color_triplet(style.get("stroke") if isinstance(style, dict) else "#111820", "#111820")
    fill_value = style.get("fill") if isinstance(style, dict) else ""
    has_fill = bool(fill_value and str(fill_value).strip().lower() not in {"none", "transparent"})
    fill = pdf_stream_color_triplet(fill_value, "#28e2cf") if has_fill else None
    stroke_width = max(0.25, finite_number(style.get("stroke_width") if isinstance(style, dict) else 1.5, 1.5))
    fill_rule = str(descriptor.get("fill_rule") or style.get("fill_rule") or "nonzero").lower()
    lines = [
        "q",
        f"{pdf_operator_number(stroke[0])} {pdf_operator_number(stroke[1])} {pdf_operator_number(stroke[2])} RG",
        f"{pdf_operator_number(stroke_width)} w",
    ]
    if fill:
        lines.append(f"{pdf_operator_number(fill[0])} {pdf_operator_number(fill[1])} {pdf_operator_number(fill[2])} rg")
    current: tuple[float, float] | None = None
    subpath_start: tuple[float, float] | None = None
    segment_count = 0
    for command in commands:
        operator = str(command[0]).upper()
        if operator == "M":
            point = pdf_stream_point(page, command[1:3], origin)
            if point is None:
                continue
            lines.append(f"{pdf_operator_number(point[0])} {pdf_operator_number(point[1])} m")
            current = point
            subpath_start = point
            continue
        if operator == "L":
            point = pdf_stream_point(page, command[1:3], origin)
            if point is None:
                continue
            if current is None:
                lines.append(f"{pdf_operator_number(point[0])} {pdf_operator_number(point[1])} m")
                subpath_start = point
            else:
                lines.append(f"{pdf_operator_number(point[0])} {pdf_operator_number(point[1])} l")
                segment_count += 1
            current = point
            continue
        if operator == "C":
            c1 = pdf_stream_point(page, command[1:3], origin)
            c2 = pdf_stream_point(page, command[3:5], origin)
            end = pdf_stream_point(page, command[5:7], origin)
            if c1 is None or c2 is None or end is None:
                continue
            if current is None:
                lines.append(f"{pdf_operator_number(end[0])} {pdf_operator_number(end[1])} m")
                subpath_start = end
            else:
                lines.append(
                    f"{pdf_operator_number(c1[0])} {pdf_operator_number(c1[1])} "
                    f"{pdf_operator_number(c2[0])} {pdf_operator_number(c2[1])} "
                    f"{pdf_operator_number(end[0])} {pdf_operator_number(end[1])} c"
                )
                segment_count += 1
            current = end
            continue
        if operator == "Q":
            control = pdf_stream_point(page, command[1:3], origin)
            end = pdf_stream_point(page, command[3:5], origin)
            if control is None or end is None:
                continue
            if current is None:
                lines.append(f"{pdf_operator_number(end[0])} {pdf_operator_number(end[1])} m")
                subpath_start = end
            else:
                c1 = (
                    current[0] + (2 / 3) * (control[0] - current[0]),
                    current[1] + (2 / 3) * (control[1] - current[1]),
                )
                c2 = (
                    end[0] + (2 / 3) * (control[0] - end[0]),
                    end[1] + (2 / 3) * (control[1] - end[1]),
                )
                lines.append(
                    f"{pdf_operator_number(c1[0])} {pdf_operator_number(c1[1])} "
                    f"{pdf_operator_number(c2[0])} {pdf_operator_number(c2[1])} "
                    f"{pdf_operator_number(end[0])} {pdf_operator_number(end[1])} c"
                )
                segment_count += 1
            current = end
            continue
        if operator == "Z" and current is not None and subpath_start is not None:
            lines.append("h")
            current = subpath_start
            segment_count += 1
    if segment_count <= 0:
        return None
    if has_fill:
        lines.append("B*" if fill_rule == "evenodd" else "B")
    else:
        lines.append("S")
    lines.append("Q")
    return ("\n".join(lines) + "\n").encode("ascii")


def update_pdf_stream(doc: object, xref: int, stream_bytes: bytes) -> None:
    try:
        doc.update_stream(xref, stream_bytes, compress=True)
    except TypeError:
        doc.update_stream(xref, stream_bytes)


def pdf_reference_xref(value_type: str, value: str) -> int:
    if value_type != "xref":
        return 0
    match = re.match(r"\s*(\d+)\s+\d+\s+R\s*$", value or "")
    return int(finite_number(match.group(1), 0)) if match else 0


def clone_pdf_xref_object(doc: object, source_xref: int) -> int:
    if source_xref <= 0 or not hasattr(doc, "get_new_xref") or not hasattr(doc, "xref_copy"):
        return 0
    target_xref = int(finite_number(doc.get_new_xref(), 0))
    if target_xref <= 0:
        return 0
    doc.update_object(target_xref, "<<>>")
    doc.xref_copy(source_xref, target_xref)
    return target_xref


def set_isolated_pdf_resource_binding(
    doc: object,
    owner_xref: int,
    category: str,
    name: str,
    target_xref: int,
) -> dict[str, object] | None:
    if owner_xref <= 0 or target_xref <= 0 or not re.fullmatch(r"[A-Za-z0-9_.#-]+", name or ""):
        return None
    cloned_dictionary_xrefs: list[int] = []
    resources_type, resources_value = pdf_xref_key_payload(doc, owner_xref, "Resources")
    resources_xref = pdf_reference_xref(resources_type, resources_value)
    if resources_xref > 0:
        cloned_resources_xref = clone_pdf_xref_object(doc, resources_xref)
        if cloned_resources_xref <= 0:
            return None
        doc.xref_set_key(owner_xref, "Resources", f"{cloned_resources_xref} 0 R")
        cloned_dictionary_xrefs.append(cloned_resources_xref)
        category_owner_xref = cloned_resources_xref
        category_key = category
    elif resources_type == "dict":
        category_owner_xref = owner_xref
        category_key = f"Resources/{category}"
    else:
        return None

    category_type, category_value = pdf_xref_key_payload(doc, category_owner_xref, category_key)
    category_xref = pdf_reference_xref(category_type, category_value)
    if category_xref > 0:
        cloned_category_xref = clone_pdf_xref_object(doc, category_xref)
        if cloned_category_xref <= 0:
            return None
        doc.xref_set_key(category_owner_xref, category_key, f"{cloned_category_xref} 0 R")
        cloned_dictionary_xrefs.append(cloned_category_xref)
        binding_owner_xref = cloned_category_xref
        binding_key = name
    elif category_type == "dict":
        binding_owner_xref = category_owner_xref
        binding_key = f"{category_key}/{name}"
    else:
        return None
    doc.xref_set_key(binding_owner_xref, binding_key, f"{target_xref} 0 R")
    resolved_type, resolved_value = pdf_xref_key_payload(doc, owner_xref, f"Resources/{category}/{name}")
    if pdf_reference_xref(resolved_type, resolved_value) != target_xref:
        return None
    return {
        "owner_xref": owner_xref,
        "category": category,
        "name": name,
        "target_xref": target_xref,
        "cloned_dictionary_xrefs": cloned_dictionary_xrefs,
    }


def rewrite_pdf_do_resource_name(
    doc: object,
    stream_xref: int,
    byte_offset: int,
    old_name: str,
    new_name: str,
) -> dict[str, object] | None:
    if stream_xref <= 0 or byte_offset < 0:
        return None
    if not re.fullmatch(r"[A-Za-z0-9_.#-]+", old_name or "") or not re.fullmatch(r"[A-Za-z0-9_.#-]+", new_name or ""):
        return None
    before_bytes = pdf_xref_stream_bytes(doc, stream_xref)
    if not before_bytes or before_bytes[byte_offset:byte_offset + 2] != b"Do":
        return None
    pattern = re.compile(rb"/" + re.escape(old_name.encode("ascii")) + rb"(?P<space>\s+)Do")
    match = next(
        (
            candidate
            for candidate in pattern.finditer(before_bytes)
            if candidate.end() - 2 == byte_offset
        ),
        None,
    )
    if match is None:
        return None
    replacement_token = b"/" + new_name.encode("ascii") + match.group("space") + b"Do"
    after_bytes = before_bytes[:match.start()] + replacement_token + before_bytes[match.end():]
    if after_bytes == before_bytes:
        return None
    update_pdf_stream(doc, stream_xref, after_bytes)
    return {
        "stream_xref": stream_xref,
        "operator_byte_offset": byte_offset,
        "old_resource_name": old_name,
        "new_resource_name": new_name,
        "before_sha256": hashlib.sha256(before_bytes).hexdigest(),
        "after_sha256": hashlib.sha256(after_bytes).hexdigest(),
        "before_byte_size": len(before_bytes),
        "after_byte_size": len(after_bytes),
    }


def unique_pdf_resource_name(
    doc: object,
    owner_xref: int,
    category: str,
    preferred_name: str,
) -> str:
    base = re.sub(r"[^A-Za-z0-9_.-]+", "_", preferred_name or "FS_Edit")[:64] or "FS_Edit"
    for ordinal in range(1, 1000):
        candidate = base if ordinal == 1 else f"{base}_{ordinal}"
        value_type, value = pdf_xref_key_payload(doc, owner_xref, f"Resources/{category}/{candidate}")
        if value_type in {"", "null", "none"} or not str(value or "").strip():
            return candidate
    return ""


def pdf_do_resource_name_matches(
    doc: object,
    stream_xref: int,
    byte_offset: int,
    resource_name: str,
) -> bool:
    if stream_xref <= 0 or byte_offset < 0 or not re.fullmatch(r"[A-Za-z0-9_.#-]+", resource_name or ""):
        return False
    stream_bytes = pdf_xref_stream_bytes(doc, stream_xref)
    if not stream_bytes or stream_bytes[byte_offset:byte_offset + 2] != b"Do":
        return False
    pattern = re.compile(rb"/" + re.escape(resource_name.encode("ascii")) + rb"\s+Do")
    return any(candidate.end() - 2 == byte_offset for candidate in pattern.finditer(stream_bytes))


def pdf_sh_resource_name_matches(
    doc: object,
    stream_xref: int,
    byte_offset: int,
    resource_name: str,
) -> bool:
    if stream_xref <= 0 or byte_offset < 0 or not re.fullmatch(r"[A-Za-z0-9_.#-]+", resource_name or ""):
        return False
    stream_bytes = pdf_xref_stream_bytes(doc, stream_xref)
    if not stream_bytes or stream_bytes[byte_offset:byte_offset + 2] != b"sh":
        return False
    pattern = re.compile(rb"/" + re.escape(resource_name.encode("ascii")) + rb"\s+sh")
    return any(candidate.end() - 2 == byte_offset for candidate in pattern.finditer(stream_bytes))


def pdf_resource_binding_isolatable(doc: object, owner_xref: int, category: str) -> bool:
    resources_type, _resources_value = pdf_xref_key_payload(doc, owner_xref, "Resources")
    if resources_type not in {"xref", "dict"}:
        return False
    category_owner_xref = owner_xref
    category_key = f"Resources/{category}"
    if resources_type == "xref":
        resources_xref = pdf_reference_xref(*pdf_xref_key_payload(doc, owner_xref, "Resources"))
        if resources_xref <= 0:
            return False
        category_owner_xref = resources_xref
        category_key = category
    category_type, _category_value = pdf_xref_key_payload(doc, category_owner_xref, category_key)
    return category_type in {"xref", "dict"}


def page_content_stream_placement(
    doc: object,
    page: object,
    caller_stream_xref: int,
) -> dict[str, object] | None:
    page_xref = int(finite_number(getattr(page, "xref", 0), 0))
    content_xrefs = page_content_xrefs(page)
    indexes = [index for index, xref in enumerate(content_xrefs) if xref == caller_stream_xref]
    if page_xref <= 0 or len(indexes) != 1:
        return None
    contents_index = indexes[0]
    contents_type, contents_value = pdf_xref_key_payload(doc, page_xref, "Contents")
    if contents_type == "xref":
        contents_ref_xref = pdf_reference_xref(contents_type, contents_value)
        if contents_ref_xref == caller_stream_xref:
            return {
                "page_xref": page_xref,
                "page_number": int(finite_number(getattr(page, "number", 0), 0)) + 1,
                "kind": "single-stream-reference",
                "contents_index": contents_index,
                "content_xrefs": content_xrefs,
                "contents_value": contents_value,
            }
        array_source = pdf_xref_object_source(doc, contents_ref_xref).strip()
        array_xrefs = [int(value) for value in re.findall(r"(\d+)\s+\d+\s+R", array_source)]
        if array_source.startswith("[") and array_source.endswith("]") and array_xrefs == content_xrefs:
            return {
                "page_xref": page_xref,
                "page_number": int(finite_number(getattr(page, "number", 0), 0)) + 1,
                "kind": "indirect-array-reference",
                "contents_index": contents_index,
                "content_xrefs": content_xrefs,
                "contents_value": array_source,
                "contents_array_xref": contents_ref_xref,
            }
        return None
    if contents_type == "array":
        array_xrefs = [int(value) for value in re.findall(r"(\d+)\s+\d+\s+R", contents_value)]
        if array_xrefs != content_xrefs:
            return None
    return {
        "page_xref": page_xref,
        "page_number": int(finite_number(getattr(page, "number", 0), 0)) + 1,
        "kind": "direct-array",
            "contents_index": contents_index,
            "content_xrefs": content_xrefs,
            "contents_value": contents_value,
        }
    return None


def rebind_page_content_stream(
    doc: object,
    placement: dict[str, object],
    replacement_xref: int,
) -> dict[str, object] | None:
    page_xref = int(finite_number(placement.get("page_xref"), 0))
    contents_index = int(finite_number(placement.get("contents_index"), -1))
    content_xrefs = [int(finite_number(value, 0)) for value in placement.get("content_xrefs", [])]
    if page_xref <= 0 or replacement_xref <= 0 or contents_index < 0 or contents_index >= len(content_xrefs):
        return None
    before_xref = content_xrefs[contents_index]
    content_xrefs[contents_index] = replacement_xref
    cloned_contents_array_xref = 0
    if placement.get("kind") == "single-stream-reference":
        after_value = f"{replacement_xref} 0 R"
    elif placement.get("kind") == "indirect-array-reference":
        array_value = "[ " + " ".join(f"{xref} 0 R" for xref in content_xrefs) + " ]"
        cloned_contents_array_xref = int(doc.get_new_xref())
        doc.update_object(cloned_contents_array_xref, array_value)
        after_value = f"{cloned_contents_array_xref} 0 R"
    else:
        after_value = "[ " + " ".join(f"{xref} 0 R" for xref in content_xrefs) + " ]"
    doc.xref_set_key(page_xref, "Contents", after_value)
    verified_type, verified_value = pdf_xref_key_payload(doc, page_xref, "Contents")
    verified_xrefs = page_content_xrefs(doc.load_page(int(finite_number(placement.get("page_number"), 1)) - 1)) if hasattr(doc, "load_page") else []
    if verified_xrefs and verified_xrefs != content_xrefs:
        return None
    if placement.get("kind") == "indirect-array-reference" and (
        verified_type != "xref"
        or pdf_reference_xref(verified_type, verified_value) != cloned_contents_array_xref
    ):
        return None
    return {
        "page_xref": page_xref,
        "contents_index": contents_index,
        "placement_kind": placement.get("kind") or "",
        "before_stream_xref": before_xref,
        "after_stream_xref": replacement_xref,
        "after_contents_type": verified_type,
        "after_contents_value": verified_value,
        "cloned_contents_array_xref": cloned_contents_array_xref,
        "contents_indirection_preserved": placement.get("kind") != "indirect-array-reference" or verified_type == "xref",
    }


def rewrite_content_stream_descriptor(doc: object, page: object, descriptor: dict[str, object]) -> dict[str, object] | None:
    target_xref = int(finite_number(descriptor.get("target_content_stream_xref") or descriptor.get("content_stream_xref"), 0))
    target_info = editable_pdf_content_stream_target(doc, page, target_xref)
    if target_xref <= 0 or not target_info.get("editable") or target_info.get("scope") != "page-content-stream":
        return None
    before_bytes = bytes(doc.xref_stream(target_xref) or b"")
    replacement = pdf_path_content_stream_from_descriptor(page, descriptor)
    if not replacement:
        return None
    update_pdf_stream(doc, target_xref, replacement)
    after_bytes = bytes(doc.xref_stream(target_xref) or b"")
    return {
        "target_content_stream_xref": target_xref,
        "target_content_stream_scope": target_info.get("scope") or "page-content-stream",
        "before_byte_size": len(before_bytes),
        "after_byte_size": len(after_bytes),
        "before_sha256": hashlib.sha256(before_bytes).hexdigest() if before_bytes else "",
        "after_sha256": hashlib.sha256(after_bytes).hexdigest() if after_bytes else "",
        "replacement_operator_count": replacement.count(b"\n"),
    }


def rewrite_content_stream_clip_path_descriptor(doc: object, page: object, descriptor: dict[str, object]) -> dict[str, object] | None:
    target_xref = int(finite_number(descriptor.get("target_content_stream_xref") or descriptor.get("content_stream_xref"), 0))
    target_info = editable_pdf_content_stream_target(doc, page, target_xref)
    if target_xref <= 0 or not target_info.get("editable"):
        return None
    before_bytes = bytes(doc.xref_stream(target_xref) or b"")
    if not before_bytes:
        return None
    clip_pattern = re.compile(rb"(?<![A-Za-z0-9_])W\*?(?![A-Za-z0-9_])")
    matches = list(clip_pattern.finditer(before_bytes))
    if not matches:
        return None
    raw_offset = descriptor.get("target_operator_byte_offset")
    if raw_offset is None:
        raw_offset = descriptor.get("operator_byte_offset")
    raw_index = descriptor.get("target_operator_index")
    if raw_index is None:
        raw_index = descriptor.get("operator_index")
    target_offset = int(finite_number(raw_offset, -1)) if raw_offset not in (None, "") else -1
    target_index = int(finite_number(raw_index, -1)) if raw_index not in (None, "") else -1
    target_operator = str(descriptor.get("target_operator") or descriptor.get("operator") or "").strip()
    target_match = next((match for match in matches if match.start() == target_offset), None) if target_offset >= 0 else None
    if target_match is None and target_index >= 0:
        profile = pdf_content_stream_operator_profile(before_bytes)
        for run in profile.get("operator_runs", []):
            if not isinstance(run, dict):
                continue
            if int(finite_number(run.get("operator_index"), -1)) != target_index:
                continue
            if str(run.get("category") or "") != "clip":
                continue
            run_offset = int(finite_number(run.get("byte_offset"), -1))
            target_match = next((match for match in matches if match.start() == run_offset), None)
            break
    if target_match is not None and target_operator and target_operator != target_match.group(0).decode("latin-1", errors="ignore"):
        target_match = None
    targeted_operator_run = target_match is not None
    if targeted_operator_run:
        start, end = target_match.span()
        replacement = before_bytes[:start] + (b" " * (end - start)) + before_bytes[end:]
        disabled_count = 1
    else:
        replacement = clip_pattern.sub(b" ", before_bytes)
        disabled_count = len(matches)
    if replacement == before_bytes:
        return None
    update_pdf_stream(doc, target_xref, replacement)
    after_bytes = bytes(doc.xref_stream(target_xref) or b"")
    after_matches = list(clip_pattern.finditer(after_bytes))
    return {
        "target_content_stream_xref": target_xref,
        "target_content_stream_scope": target_info.get("scope") or "",
        "target_xobject_xref": target_info.get("target_xobject_xref") or 0,
        "target_xobject_name": target_info.get("target_xobject_name") or "",
        "before_byte_size": len(before_bytes),
        "after_byte_size": len(after_bytes),
        "before_sha256": hashlib.sha256(before_bytes).hexdigest() if before_bytes else "",
        "after_sha256": hashlib.sha256(after_bytes).hexdigest() if after_bytes else "",
        "target_operator_run_rewrite": targeted_operator_run,
        "target_operator": target_match.group(0).decode("latin-1", errors="ignore") if target_match is not None else target_operator,
        "target_operator_index": target_index if target_index >= 0 else None,
        "target_operator_byte_offset": target_match.start() if target_match is not None else (target_offset if target_offset >= 0 else None),
        "disabled_clip_operator_count": disabled_count,
        "remaining_clip_operator_count": len(after_matches),
        "native_stream_mutated": disabled_count > 0 and len(after_matches) < len(matches),
    }


def rewrite_content_stream_paint_operator_descriptor(doc: object, page: object, descriptor: dict[str, object]) -> dict[str, object] | None:
    target_xref = int(finite_number(descriptor.get("target_content_stream_xref") or descriptor.get("content_stream_xref"), 0))
    target_info = editable_pdf_content_stream_target(doc, page, target_xref)
    if target_xref <= 0 or not target_info.get("editable"):
        return None
    before_bytes = bytes(doc.xref_stream(target_xref) or b"")
    if not before_bytes:
        return None
    target_operator = str(descriptor.get("target_operator") or descriptor.get("operator") or "").strip()
    if target_operator not in PDF_PAINT_OPERATOR_TOKENS:
        return None
    raw_offset = descriptor.get("target_operator_byte_offset")
    if raw_offset is None:
        raw_offset = descriptor.get("operator_byte_offset")
    raw_index = descriptor.get("target_operator_index")
    if raw_index is None:
        raw_index = descriptor.get("operator_index")
    target_offset = int(finite_number(raw_offset, -1)) if raw_offset not in (None, "") else -1
    target_index = int(finite_number(raw_index, -1)) if raw_index not in (None, "") else -1
    profile = pdf_content_stream_operator_profile(before_bytes)
    target_run = None
    for run in profile.get("operator_runs", []):
        if not isinstance(run, dict) or str(run.get("category") or "") != "paint":
            continue
        run_operator = str(run.get("operator") or "")
        run_offset = int(finite_number(run.get("byte_offset"), -1))
        run_index = int(finite_number(run.get("operator_index"), -1))
        offset_matches = target_offset >= 0 and run_offset == target_offset
        index_matches = target_index >= 0 and run_index == target_index
        if run_operator == target_operator and (offset_matches or index_matches):
            target_run = {
                **run,
                "byte_offset": run_offset,
                "operator_index": run_index,
            }
            break
    if not target_run:
        return None
    start = int(target_run["byte_offset"])
    end = start + len(target_operator)
    if before_bytes[start:end].decode("latin-1", errors="ignore") != target_operator:
        return None
    replacement_token = b"n" + (b" " * max(0, len(target_operator) - 1))
    replacement = before_bytes[:start] + replacement_token + before_bytes[end:]
    if replacement == before_bytes:
        return None
    update_pdf_stream(doc, target_xref, replacement)
    after_bytes = bytes(doc.xref_stream(target_xref) or b"")
    return {
        "target_content_stream_xref": target_xref,
        "target_content_stream_scope": target_info.get("scope") or "",
        "target_xobject_xref": target_info.get("target_xobject_xref") or 0,
        "target_xobject_name": target_info.get("target_xobject_name") or "",
        "before_byte_size": len(before_bytes),
        "after_byte_size": len(after_bytes),
        "before_sha256": hashlib.sha256(before_bytes).hexdigest() if before_bytes else "",
        "after_sha256": hashlib.sha256(after_bytes).hexdigest() if after_bytes else "",
        "target_operator_run_rewrite": True,
        "target_operator": target_operator,
        "target_operator_index": target_run.get("operator_index"),
        "target_operator_byte_offset": target_run.get("byte_offset"),
        "replacement_operator": "n",
        "disabled_paint_operator_count": 1,
        "native_stream_mutated": True,
    }


def is_pdf_numeric_token(token: str) -> bool:
    return bool(re.match(r"^[-+]?(?:\d+\.?\d*|\.\d+)$", str(token or "")))


def pdf_rgb_triplet_from_descriptor(descriptor: dict[str, object]) -> tuple[float, float, float]:
    raw_rgb = descriptor.get("target_rgb") or descriptor.get("rgb")
    if isinstance(raw_rgb, (list, tuple)) and len(raw_rgb) >= 3:
        values = [finite_number(value, 0) for value in raw_rgb[:3]]
        if any(value > 1 for value in values):
            values = [value / 255 for value in values]
        return tuple(max(0.0, min(1.0, round(value, 4))) for value in values)  # type: ignore[return-value]
    return tuple(round(value, 4) for value in hex_color_triplet(descriptor.get("target_color") or descriptor.get("color"), "#10b981"))


def pdf_device_color_components_from_descriptor(
    descriptor: dict[str, object],
    operator: str,
) -> list[float] | None:
    component_count = PDF_DEVICE_COLOR_OPERATOR_COMPONENTS.get(operator, 0)
    color_space = PDF_DEVICE_COLOR_OPERATOR_SPACES.get(operator, "")
    requested_space = str(descriptor.get("target_color_space") or descriptor.get("source_color_space") or color_space)
    if component_count <= 0 or requested_space != color_space:
        return None
    raw_components = descriptor.get("target_components")
    if isinstance(raw_components, (list, tuple)) and len(raw_components) == component_count:
        values = [round(finite_number(value, -1), 4) for value in raw_components]
    elif color_space == "DeviceRGB":
        values = list(pdf_rgb_triplet_from_descriptor(descriptor))
    else:
        return None
    if any(value < 0 or value > 1 for value in values):
        return None
    return values


def pdf_unit_interval_components(raw_values: object, component_count: int) -> list[float] | None:
    if not isinstance(raw_values, (list, tuple)) or len(raw_values) != component_count:
        return None
    try:
        values = [float(value) for value in raw_values]
    except (TypeError, ValueError):
        return None
    if any(not math.isfinite(value) or value < 0 or value > 1 for value in values):
        return None
    return [round(value, 4) for value in values]


def rewrite_content_stream_device_color_operator_descriptor(doc: object, page: object, descriptor: dict[str, object]) -> dict[str, object] | None:
    target_xref = int(finite_number(descriptor.get("target_content_stream_xref") or descriptor.get("content_stream_xref"), 0))
    target_info = editable_pdf_content_stream_target(doc, page, target_xref)
    if target_xref <= 0 or not target_info.get("editable"):
        return None
    before_bytes = bytes(doc.xref_stream(target_xref) or b"")
    if not before_bytes:
        return None
    target_operator = str(descriptor.get("target_operator") or descriptor.get("operator") or "").strip()
    component_count = PDF_DEVICE_COLOR_OPERATOR_COMPONENTS.get(target_operator, 0)
    color_space = PDF_DEVICE_COLOR_OPERATOR_SPACES.get(target_operator, "")
    if component_count <= 0 or not color_space:
        return None
    raw_offset = descriptor.get("target_operator_byte_offset")
    if raw_offset is None:
        raw_offset = descriptor.get("operator_byte_offset")
    raw_index = descriptor.get("target_operator_index")
    if raw_index is None:
        raw_index = descriptor.get("operator_index")
    target_offset = int(finite_number(raw_offset, -1)) if raw_offset not in (None, "") else -1
    target_index = int(finite_number(raw_index, -1)) if raw_index not in (None, "") else -1
    text, tokens = scan_pdf_content_stream_tokens(before_bytes)
    operator_index = -1
    token_position = -1
    for index, (token, offset) in enumerate(tokens):
        if token not in PDF_CONTENT_STREAM_OPERATOR_CATEGORIES:
            continue
        operator_index += 1
        if token != target_operator:
            continue
        offset_matches = target_offset >= 0 and offset == target_offset
        index_matches = target_index >= 0 and operator_index == target_index
        if offset_matches or index_matches:
            token_position = index
            break
    if token_position < component_count:
        return None
    operand_tokens = tokens[token_position - component_count:token_position]
    if not all(is_pdf_numeric_token(token) for token, _offset in operand_tokens):
        return None
    start = operand_tokens[0][1]
    operator_offset = tokens[token_position][1]
    end = operator_offset + len(target_operator)
    if text[operator_offset:end] != target_operator:
        return None
    source_components = [round(finite_number(token, 0), 4) for token, _offset in operand_tokens]
    requested_source = descriptor.get("source_components")
    if isinstance(requested_source, (list, tuple)):
        expected_source = [round(finite_number(value, 0), 4) for value in requested_source]
        if expected_source != source_components:
            return None
    target_components = pdf_device_color_components_from_descriptor(descriptor, target_operator)
    if target_components is None:
        return None
    replacement_text = f"{' '.join(pdf_operator_number(value) for value in target_components)} {target_operator}"
    replacement = before_bytes[:start] + replacement_text.encode("ascii") + before_bytes[end:]
    if replacement == before_bytes:
        return None
    update_pdf_stream(doc, target_xref, replacement)
    after_bytes = bytes(doc.xref_stream(target_xref) or b"")
    return {
        "target_content_stream_xref": target_xref,
        "target_content_stream_scope": target_info.get("scope") or "",
        "target_xobject_xref": target_info.get("target_xobject_xref") or 0,
        "target_xobject_name": target_info.get("target_xobject_name") or "",
        "before_byte_size": len(before_bytes),
        "after_byte_size": len(after_bytes),
        "before_sha256": hashlib.sha256(before_bytes).hexdigest() if before_bytes else "",
        "after_sha256": hashlib.sha256(after_bytes).hexdigest() if after_bytes else "",
        "target_operator_run_rewrite": True,
        "target_operator": target_operator,
        "target_operator_index": target_index if target_index >= 0 else operator_index,
        "target_operator_byte_offset": operator_offset,
        "source_color_space": color_space,
        "target_color_space": color_space,
        "source_components": source_components,
        "target_components": target_components,
        "source_rgb": pdf_device_color_preview_rgb(color_space, source_components),
        "target_rgb": pdf_device_color_preview_rgb(color_space, target_components),
        "replacement_operator": target_operator,
        "native_stream_mutated": True,
    }


def rewrite_content_stream_special_color_operator_descriptor(doc: object, page: object, descriptor: dict[str, object]) -> dict[str, object] | None:
    target_xref = int(finite_number(descriptor.get("target_content_stream_xref") or descriptor.get("content_stream_xref"), 0))
    target_info = editable_pdf_content_stream_target(doc, page, target_xref)
    if target_xref <= 0 or not target_info.get("editable"):
        return None
    before_bytes = pdf_xref_stream_bytes(doc, target_xref)
    if not before_bytes:
        return None
    target_operator = str(descriptor.get("target_operator") or descriptor.get("operator") or "").strip()
    component_count = int(finite_number(descriptor.get("component_count"), 0))
    native_model = str(descriptor.get("native_color_model") or "")
    if target_operator not in {"scn", "SCN"} or native_model not in {"Separation", "DeviceN"} or component_count <= 0:
        return None
    raw_offset = descriptor.get("target_operator_byte_offset")
    raw_index = descriptor.get("target_operator_index")
    target_offset = int(finite_number(raw_offset, -1)) if raw_offset not in (None, "") else -1
    target_index = int(finite_number(raw_index, -1)) if raw_index not in (None, "") else -1
    text, tokens = scan_pdf_content_stream_tokens(before_bytes)
    operator_index = -1
    token_position = -1
    for index, (token, offset) in enumerate(tokens):
        if token not in PDF_CONTENT_STREAM_OPERATOR_CATEGORIES:
            continue
        operator_index += 1
        if token != target_operator:
            continue
        if (target_offset >= 0 and offset == target_offset) or (target_index >= 0 and operator_index == target_index):
            token_position = index
            break
    if token_position < component_count:
        return None
    operand_tokens = tokens[token_position - component_count:token_position]
    if not all(is_pdf_numeric_token(token) for token, _offset in operand_tokens):
        return None
    start = operand_tokens[0][1]
    operator_offset = tokens[token_position][1]
    end = operator_offset + len(target_operator)
    if text[operator_offset:end] != target_operator:
        return None
    source_components = pdf_unit_interval_components([token for token, _offset in operand_tokens], component_count)
    expected_source = pdf_unit_interval_components(descriptor.get("source_components"), component_count)
    target_components = pdf_unit_interval_components(descriptor.get("target_components"), component_count)
    if source_components is None or expected_source != source_components or target_components is None:
        return None
    replacement_text = f"{' '.join(pdf_operator_number(value) for value in target_components)} {target_operator}"
    replacement = before_bytes[:start] + replacement_text.encode("ascii") + before_bytes[end:]
    if replacement == before_bytes:
        return None
    update_pdf_stream(doc, target_xref, replacement)
    after_bytes = pdf_xref_stream_bytes(doc, target_xref)
    if after_bytes != replacement:
        update_pdf_stream(doc, target_xref, before_bytes)
        return None
    replacement_end = start + len(replacement_text.encode("ascii"))
    if after_bytes[:start] != before_bytes[:start] or after_bytes[replacement_end:] != before_bytes[end:]:
        update_pdf_stream(doc, target_xref, before_bytes)
        return None
    return {
        "target_content_stream_xref": target_xref,
        "target_content_stream_scope": target_info.get("scope") or "",
        "target_xobject_xref": target_info.get("target_xobject_xref") or 0,
        "target_xobject_name": target_info.get("target_xobject_name") or "",
        "before_byte_size": len(before_bytes),
        "after_byte_size": len(after_bytes),
        "before_sha256": hashlib.sha256(before_bytes).hexdigest(),
        "after_sha256": hashlib.sha256(after_bytes).hexdigest(),
        "target_operator_run_rewrite": True,
        "target_operator": target_operator,
        "target_operator_index": target_index if target_index >= 0 else operator_index,
        "target_operator_byte_offset": operator_offset,
        "source_color_space": native_model,
        "target_color_space": native_model,
        "source_components": source_components,
        "target_components": target_components,
        "color_space_resource_name": descriptor.get("color_space_resource_name") or "",
        "color_space_resource_id": descriptor.get("color_space_resource_id") or "",
        "color_space_binding_id": descriptor.get("color_space_binding_id") or "",
        "replacement_operator": target_operator,
        "native_stream_mutated": True,
        "native_resource_mutated": False,
        "changed_byte_span_before": [start, end],
        "changed_byte_span_after": [start, replacement_end],
        "unchanged_prefix_sha256": hashlib.sha256(before_bytes[:start]).hexdigest(),
        "unchanged_suffix_sha256": hashlib.sha256(before_bytes[end:]).hexdigest(),
        "post_write_bytes_verified": True,
    }


def rewrite_content_stream_rgb_color_operator_descriptor(doc: object, page: object, descriptor: dict[str, object]) -> dict[str, object] | None:
    target_operator = str(descriptor.get("target_operator") or descriptor.get("operator") or "").strip()
    if target_operator not in PDF_RGB_COLOR_OPERATOR_TOKENS:
        return None
    return rewrite_content_stream_device_color_operator_descriptor(doc, page, descriptor)


def rewrite_content_stream_stroke_width_operator_descriptor(doc: object, page: object, descriptor: dict[str, object]) -> dict[str, object] | None:
    target_xref = int(finite_number(descriptor.get("target_content_stream_xref") or descriptor.get("content_stream_xref"), 0))
    target_info = editable_pdf_content_stream_target(doc, page, target_xref)
    if target_xref <= 0 or not target_info.get("editable"):
        return None
    before_bytes = bytes(doc.xref_stream(target_xref) or b"")
    if not before_bytes:
        return None
    target_operator = str(descriptor.get("target_operator") or descriptor.get("operator") or "").strip()
    if target_operator not in PDF_STROKE_WIDTH_OPERATOR_TOKENS:
        return None
    raw_offset = descriptor.get("target_operator_byte_offset")
    if raw_offset is None:
        raw_offset = descriptor.get("operator_byte_offset")
    raw_index = descriptor.get("target_operator_index")
    if raw_index is None:
        raw_index = descriptor.get("operator_index")
    target_offset = int(finite_number(raw_offset, -1)) if raw_offset not in (None, "") else -1
    target_index = int(finite_number(raw_index, -1)) if raw_index not in (None, "") else -1
    text, tokens = scan_pdf_content_stream_tokens(before_bytes)
    operator_index = -1
    token_position = -1
    for index, (token, offset) in enumerate(tokens):
        if token not in PDF_CONTENT_STREAM_OPERATOR_CATEGORIES:
            continue
        operator_index += 1
        if token != target_operator:
            continue
        offset_matches = target_offset >= 0 and offset == target_offset
        index_matches = target_index >= 0 and operator_index == target_index
        if offset_matches or index_matches:
            token_position = index
            break
    if token_position < 1:
        return None
    operand_token, operand_offset = tokens[token_position - 1]
    if not is_pdf_numeric_token(operand_token):
        return None
    operator_offset = tokens[token_position][1]
    end = operator_offset + len(target_operator)
    if text[operator_offset:end] != target_operator:
        return None
    source_width = finite_number(operand_token, 0)
    target_width = max(0.01, min(500.0, finite_number(
        descriptor.get("target_stroke_width")
        or descriptor.get("stroke_width")
        or descriptor.get("target_width")
        or descriptor.get("width"),
        2.5,
    )))
    replacement_text = f"{pdf_operator_number(target_width)} {target_operator}"
    replacement = before_bytes[:operand_offset] + replacement_text.encode("ascii") + before_bytes[end:]
    if replacement == before_bytes:
        return None
    update_pdf_stream(doc, target_xref, replacement)
    after_bytes = bytes(doc.xref_stream(target_xref) or b"")
    return {
        "target_content_stream_xref": target_xref,
        "target_content_stream_scope": target_info.get("scope") or "",
        "target_xobject_xref": target_info.get("target_xobject_xref") or 0,
        "target_xobject_name": target_info.get("target_xobject_name") or "",
        "before_byte_size": len(before_bytes),
        "after_byte_size": len(after_bytes),
        "before_sha256": hashlib.sha256(before_bytes).hexdigest() if before_bytes else "",
        "after_sha256": hashlib.sha256(after_bytes).hexdigest() if after_bytes else "",
        "target_operator_run_rewrite": True,
        "target_operator": target_operator,
        "target_operator_index": target_index if target_index >= 0 else operator_index,
        "target_operator_byte_offset": operator_offset,
        "source_stroke_width": round(source_width, 4),
        "target_stroke_width": round(target_width, 4),
        "replacement_operator": target_operator,
        "native_stream_mutated": True,
    }


def rewrite_content_stream_stroke_style_operator_descriptor(doc: object, page: object, descriptor: dict[str, object]) -> dict[str, object] | None:
    target_xref = int(finite_number(descriptor.get("target_content_stream_xref") or descriptor.get("content_stream_xref"), 0))
    target_info = editable_pdf_content_stream_target(doc, page, target_xref)
    if target_xref <= 0 or not target_info.get("editable"):
        return None
    before_bytes = bytes(doc.xref_stream(target_xref) or b"")
    if not before_bytes:
        return None
    property_name = str(descriptor.get("stroke_property") or descriptor.get("property") or "").strip().lower()
    target_operator = str(descriptor.get("target_operator") or descriptor.get("operator") or "").strip()
    if PDF_STROKE_STYLE_OPERATOR_PROPERTIES.get(target_operator) != property_name:
        return None
    raw_offset = descriptor.get("target_operator_byte_offset")
    raw_index = descriptor.get("target_operator_index")
    target_offset = int(finite_number(raw_offset, -1)) if raw_offset not in (None, "") else -1
    target_index = int(finite_number(raw_index, -1)) if raw_index not in (None, "") else -1
    text, tokens = scan_pdf_content_stream_tokens(before_bytes)
    operator_index = -1
    token_position = -1
    for index, (token, offset) in enumerate(tokens):
        if token not in PDF_CONTENT_STREAM_OPERATOR_CATEGORIES:
            continue
        operator_index += 1
        if token != target_operator:
            continue
        offset_matches = target_offset >= 0 and offset == target_offset
        index_matches = target_index >= 0 and operator_index == target_index
        if offset_matches or index_matches:
            token_position = index
            break
    if token_position < 1:
        return None
    operator_offset = tokens[token_position][1]
    end = operator_offset + len(target_operator)
    if text[operator_offset:end] != target_operator:
        return None

    source_payload: object
    target_payload: object
    if property_name == "dash":
        operands = pdf_dash_operands_before(tokens, token_position)
        if operands is None:
            return None
        source_array = [round(value, 4) for value in operands[0]]
        source_phase = round(operands[1], 4)
        expected_array = descriptor.get("source_dash_array")
        if isinstance(expected_array, (list, tuple)):
            normalized_expected = [round(finite_number(value, 0), 4) for value in list(expected_array)[:24]]
            if source_array != normalized_expected:
                return None
        if descriptor.get("source_dash_phase") not in (None, "") and source_phase != round(finite_number(descriptor.get("source_dash_phase"), 0), 4):
            return None
        target_array_raw = descriptor.get("target_dash_array")
        if not isinstance(target_array_raw, (list, tuple)):
            return None
        target_array = [max(0.0, min(10000.0, finite_number(value, 0))) for value in list(target_array_raw)[:24]]
        if target_array and not any(value > 0 for value in target_array):
            return None
        target_phase = max(-10000.0, min(10000.0, finite_number(descriptor.get("target_dash_phase"), 0)))
        open_position = token_position - 3
        while open_position >= 0 and tokens[open_position][0] != "[":
            open_position -= 1
        if open_position < 0:
            return None
        replacement_start = tokens[open_position][1]
        replacement_text = f"[{' '.join(pdf_operator_number(value) for value in target_array)}] {pdf_operator_number(target_phase)} d"
        source_payload = {"dash_array": source_array, "dash_phase": source_phase}
        target_payload = {"dash_array": [round(value, 4) for value in target_array], "dash_phase": round(target_phase, 4)}
    else:
        operand_token, operand_offset = tokens[token_position - 1]
        if not is_pdf_numeric_token(operand_token):
            return None
        source_value = finite_number(operand_token, 0)
        if descriptor.get("source_value") not in (None, "") and round(source_value, 4) != round(finite_number(descriptor.get("source_value"), 0), 4):
            return None
        target_value = finite_number(descriptor.get("target_value"), source_value)
        if property_name == "width":
            if target_value <= 0 or target_value > 500:
                return None
        elif property_name == "miter_limit":
            if target_value < 1 or target_value > 1000:
                return None
        elif not float(target_value).is_integer() or int(target_value) not in {0, 1, 2}:
            return None
        replacement_start = operand_offset
        replacement_text = f"{pdf_operator_number(target_value)} {target_operator}"
        source_payload = round(source_value, 4)
        target_payload = round(target_value, 4)

    replacement = before_bytes[:replacement_start] + replacement_text.encode("ascii") + before_bytes[end:]
    if replacement == before_bytes:
        return None
    update_pdf_stream(doc, target_xref, replacement)
    after_bytes = bytes(doc.xref_stream(target_xref) or b"")
    return {
        "target_content_stream_xref": target_xref,
        "target_content_stream_scope": target_info.get("scope") or "",
        "target_xobject_xref": target_info.get("target_xobject_xref") or 0,
        "target_xobject_name": target_info.get("target_xobject_name") or "",
        "before_byte_size": len(before_bytes),
        "after_byte_size": len(after_bytes),
        "before_sha256": hashlib.sha256(before_bytes).hexdigest(),
        "after_sha256": hashlib.sha256(after_bytes).hexdigest(),
        "target_operator_run_rewrite": True,
        "stroke_property": property_name,
        "target_operator": target_operator,
        "target_operator_index": target_index if target_index >= 0 else operator_index,
        "target_operator_byte_offset": operator_offset,
        "source_value": source_payload,
        "target_value": target_payload,
        "replacement_operator": target_operator,
        "native_stream_mutated": True,
    }


def path_geometry_operand_indexes(operator: str) -> list[int]:
    if operator in {"m", "l"}:
        return [0, 1]
    if operator == "c":
        return [0, 1, 2, 3, 4, 5]
    if operator in {"v", "y", "re"}:
        return [0, 1, 2, 3]
    return []


def transformed_pdf_path_number(operator: str, operand_index: int, value: float, transform: dict[str, float]) -> float:
    if operator == "re" and operand_index in {2, 3}:
        scale_key = "scale_x" if operand_index == 2 else "scale_y"
        return value * transform[scale_key]
    if operand_index % 2 == 0:
        return transform["origin_x"] + ((value - transform["origin_x"]) * transform["scale_x"]) + transform["dx"]
    return transform["origin_y"] + ((value - transform["origin_y"]) * transform["scale_y"]) + transform["dy"]


def path_geometry_bbox(points: list[tuple[float, float]]) -> dict[str, float]:
    if not points:
        return {"x0": 0.0, "y0": 0.0, "x1": 0.0, "y1": 0.0, "width": 0.0, "height": 0.0}
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    x0 = min(xs)
    y0 = min(ys)
    x1 = max(xs)
    y1 = max(ys)
    return {
        "x0": round(x0, 4),
        "y0": round(y0, 4),
        "x1": round(x1, 4),
        "y1": round(y1, 4),
        "width": round(max(0.0, x1 - x0), 4),
        "height": round(max(0.0, y1 - y0), 4),
    }


def rewrite_content_stream_path_geometry_operator_descriptor(doc: object, page: object, descriptor: dict[str, object]) -> dict[str, object] | None:
    target_xref = int(finite_number(descriptor.get("target_content_stream_xref") or descriptor.get("content_stream_xref"), 0))
    target_info = editable_pdf_content_stream_target(doc, page, target_xref)
    if target_xref <= 0 or not target_info.get("editable"):
        return None
    before_bytes = bytes(doc.xref_stream(target_xref) or b"")
    if not before_bytes:
        return None
    target_operator = str(descriptor.get("target_operator") or descriptor.get("operator") or "").strip()
    if target_operator not in PDF_PATH_GEOMETRY_OPERATOR_TOKENS:
        return None
    raw_offset = descriptor.get("target_operator_byte_offset")
    if raw_offset is None:
        raw_offset = descriptor.get("operator_byte_offset")
    raw_index = descriptor.get("target_operator_index")
    if raw_index is None:
        raw_index = descriptor.get("operator_index")
    target_offset = int(finite_number(raw_offset, -1)) if raw_offset not in (None, "") else -1
    target_index = int(finite_number(raw_index, -1)) if raw_index not in (None, "") else -1
    text, tokens = scan_pdf_content_stream_tokens(before_bytes)
    operator_runs: list[dict[str, object]] = []
    operator_index = -1
    for token_position, (token, offset) in enumerate(tokens):
        category = PDF_CONTENT_STREAM_OPERATOR_CATEGORIES.get(token)
        if not category:
            continue
        operator_index += 1
        operator_runs.append({
            "token_position": token_position,
            "operator_index": operator_index,
            "operator": token,
            "category": category,
            "byte_offset": offset,
        })
    target_run_position = -1
    for run_position, run in enumerate(operator_runs):
        if str(run.get("category") or "") != "path":
            continue
        run_operator = str(run.get("operator") or "")
        run_offset = int(finite_number(run.get("byte_offset"), -1))
        run_index = int(finite_number(run.get("operator_index"), -1))
        offset_matches = target_offset >= 0 and run_offset == target_offset
        index_matches = target_index >= 0 and run_index == target_index
        if run_operator == target_operator and (offset_matches or index_matches):
            target_run_position = run_position
            break
    if target_run_position < 0:
        return None
    first_run_position = target_run_position
    while first_run_position > 0 and str(operator_runs[first_run_position - 1].get("category") or "") == "path":
        first_run_position -= 1
    last_run_position = target_run_position
    while last_run_position + 1 < len(operator_runs) and str(operator_runs[last_run_position + 1].get("category") or "") == "path":
        last_run_position += 1
    dx = max(-5000.0, min(5000.0, finite_number(
        descriptor_first_present(descriptor, ["delta_x", "dx", "target_path_delta_x", "path_delta_x"], 18.0),
        18.0,
    )))
    dy = max(-5000.0, min(5000.0, finite_number(
        descriptor_first_present(descriptor, ["delta_y", "dy", "target_path_delta_y", "path_delta_y"], 12.0),
        12.0,
    )))
    scale_x = max(0.01, min(100.0, finite_number(
        descriptor_first_present(descriptor, ["scale_x", "target_path_scale_x", "path_scale_x"], 1.0),
        1.0,
    )))
    scale_y = max(0.01, min(100.0, finite_number(
        descriptor_first_present(descriptor, ["scale_y", "target_path_scale_y", "path_scale_y"], 1.0),
        1.0,
    )))
    replacements: list[tuple[int, int, str]] = []
    source_points: list[tuple[float, float]] = []
    transformed_points: list[tuple[float, float]] = []
    transformed_operator_count = 0
    skipped_operator_count = 0
    operator_names: list[str] = []
    pending_operands: list[tuple[str, int]] = []
    for run in operator_runs[first_run_position:last_run_position + 1]:
        operator = str(run.get("operator") or "")
        token_position = int(finite_number(run.get("token_position"), -1))
        indexes = path_geometry_operand_indexes(operator)
        if not indexes:
            continue
        needed = max(indexes) + 1
        if token_position < needed:
            skipped_operator_count += 1
            continue
        operand_tokens = tokens[token_position - needed:token_position]
        if not all(is_pdf_numeric_token(token) for token, _offset in operand_tokens):
            skipped_operator_count += 1
            continue
        values = [finite_number(token, 0) for token, _offset in operand_tokens]
        pending_operands.append((operator, int(finite_number(run.get("byte_offset"), -1))))
        operator_names.append(operator)
        for operand_index in indexes:
            token, start = operand_tokens[operand_index]
            end = start + len(token)
            source_value = values[operand_index]
            transformed_value = transformed_pdf_path_number(operator, operand_index, source_value, {
                "dx": dx,
                "dy": dy,
                "scale_x": scale_x,
                "scale_y": scale_y,
                "origin_x": 0.0,
                "origin_y": 0.0,
            })
            replacements.append((start, end, pdf_operator_number(transformed_value)))
        if operator == "re":
            source_points.extend([
                (values[0], values[1]),
                (values[0] + values[2], values[1] + values[3]),
            ])
            transformed_x = transformed_pdf_path_number(operator, 0, values[0], {"dx": dx, "dy": dy, "scale_x": scale_x, "scale_y": scale_y, "origin_x": 0.0, "origin_y": 0.0})
            transformed_y = transformed_pdf_path_number(operator, 1, values[1], {"dx": dx, "dy": dy, "scale_x": scale_x, "scale_y": scale_y, "origin_x": 0.0, "origin_y": 0.0})
            transformed_w = transformed_pdf_path_number(operator, 2, values[2], {"dx": dx, "dy": dy, "scale_x": scale_x, "scale_y": scale_y, "origin_x": 0.0, "origin_y": 0.0})
            transformed_h = transformed_pdf_path_number(operator, 3, values[3], {"dx": dx, "dy": dy, "scale_x": scale_x, "scale_y": scale_y, "origin_x": 0.0, "origin_y": 0.0})
            transformed_points.extend([
                (transformed_x, transformed_y),
                (transformed_x + transformed_w, transformed_y + transformed_h),
            ])
        else:
            for operand_index in indexes[0::2]:
                if operand_index + 1 >= len(values):
                    continue
                source_points.append((values[operand_index], values[operand_index + 1]))
                transformed_points.append((
                    transformed_pdf_path_number(operator, operand_index, values[operand_index], {"dx": dx, "dy": dy, "scale_x": scale_x, "scale_y": scale_y, "origin_x": 0.0, "origin_y": 0.0}),
                    transformed_pdf_path_number(operator, operand_index + 1, values[operand_index + 1], {"dx": dx, "dy": dy, "scale_x": scale_x, "scale_y": scale_y, "origin_x": 0.0, "origin_y": 0.0}),
                ))
        transformed_operator_count += 1
    if not replacements:
        return None
    replacement_bytes = before_bytes
    for start, end, value in sorted(replacements, key=lambda item: item[0], reverse=True):
        replacement_bytes = replacement_bytes[:start] + value.encode("ascii") + replacement_bytes[end:]
    if replacement_bytes == before_bytes:
        return None
    update_pdf_stream(doc, target_xref, replacement_bytes)
    after_bytes = bytes(doc.xref_stream(target_xref) or b"")
    target_run = operator_runs[target_run_position]
    return {
        "target_content_stream_xref": target_xref,
        "target_content_stream_scope": target_info.get("scope") or "",
        "target_xobject_xref": target_info.get("target_xobject_xref") or 0,
        "target_xobject_name": target_info.get("target_xobject_name") or "",
        "before_byte_size": len(before_bytes),
        "after_byte_size": len(after_bytes),
        "before_sha256": hashlib.sha256(before_bytes).hexdigest() if before_bytes else "",
        "after_sha256": hashlib.sha256(after_bytes).hexdigest() if after_bytes else "",
        "target_operator_run_rewrite": True,
        "target_operator": target_operator,
        "target_operator_index": target_run.get("operator_index"),
        "target_operator_byte_offset": target_run.get("byte_offset"),
        "path_sequence_operator_count": last_run_position - first_run_position + 1,
        "transformed_operator_count": transformed_operator_count,
        "skipped_operator_count": skipped_operator_count,
        "transformed_number_count": len(replacements),
        "path_operators": operator_names,
        "path_operator_targets": [
            {"operator": operator, "byte_offset": offset}
            for operator, offset in pending_operands[:MAX_NATIVE_PDF_PATH_ITEMS]
        ],
        "delta_x": round(dx, 4),
        "delta_y": round(dy, 4),
        "scale_x": round(scale_x, 4),
        "scale_y": round(scale_y, 4),
        "source_path_bbox": path_geometry_bbox(source_points),
        "target_path_bbox": path_geometry_bbox(transformed_points),
        "native_stream_mutated": True,
    }


def pdf_path_sequence_bytes_from_descriptor(page: object, descriptor: dict[str, object]) -> tuple[bytes | None, dict[str, object]]:
    commands, origin = path_commands_from_descriptor(descriptor)
    if not commands:
        return None, {"command_count": 0, "segment_count": 0, "subpath_count": 0, "origin": origin}
    lines: list[str] = []
    current: tuple[float, float] | None = None
    subpath_start: tuple[float, float] | None = None
    segment_count = 0
    subpath_count = 0
    for command in commands:
        operator = str(command[0]).upper()
        if operator == "M":
            point = pdf_stream_point(page, command[1:3], origin)
            if point is None:
                continue
            lines.append(f"{pdf_operator_number(point[0])} {pdf_operator_number(point[1])} m")
            current = point
            subpath_start = point
            subpath_count += 1
            continue
        if operator == "L":
            point = pdf_stream_point(page, command[1:3], origin)
            if point is None:
                continue
            if current is None:
                lines.append(f"{pdf_operator_number(point[0])} {pdf_operator_number(point[1])} m")
                subpath_start = point
                subpath_count += 1
            else:
                lines.append(f"{pdf_operator_number(point[0])} {pdf_operator_number(point[1])} l")
                segment_count += 1
            current = point
            continue
        if operator == "C":
            c1 = pdf_stream_point(page, command[1:3], origin)
            c2 = pdf_stream_point(page, command[3:5], origin)
            end = pdf_stream_point(page, command[5:7], origin)
            if c1 is None or c2 is None or end is None:
                continue
            if current is None:
                lines.append(f"{pdf_operator_number(end[0])} {pdf_operator_number(end[1])} m")
                subpath_start = end
                subpath_count += 1
            else:
                lines.append(
                    f"{pdf_operator_number(c1[0])} {pdf_operator_number(c1[1])} "
                    f"{pdf_operator_number(c2[0])} {pdf_operator_number(c2[1])} "
                    f"{pdf_operator_number(end[0])} {pdf_operator_number(end[1])} c"
                )
                segment_count += 1
            current = end
            continue
        if operator == "Q":
            control = pdf_stream_point(page, command[1:3], origin)
            end = pdf_stream_point(page, command[3:5], origin)
            if control is None or end is None:
                continue
            if current is None:
                lines.append(f"{pdf_operator_number(end[0])} {pdf_operator_number(end[1])} m")
                subpath_start = end
                subpath_count += 1
            else:
                c1 = (
                    current[0] + (2 / 3) * (control[0] - current[0]),
                    current[1] + (2 / 3) * (control[1] - current[1]),
                )
                c2 = (
                    end[0] + (2 / 3) * (control[0] - end[0]),
                    end[1] + (2 / 3) * (control[1] - end[1]),
                )
                lines.append(
                    f"{pdf_operator_number(c1[0])} {pdf_operator_number(c1[1])} "
                    f"{pdf_operator_number(c2[0])} {pdf_operator_number(c2[1])} "
                    f"{pdf_operator_number(end[0])} {pdf_operator_number(end[1])} c"
                )
                segment_count += 1
            current = end
            continue
        if operator == "Z" and current is not None and subpath_start is not None:
            lines.append("h")
            current = subpath_start
            segment_count += 1
    if segment_count <= 0 or not lines:
        return None, {"command_count": len(commands), "segment_count": segment_count, "subpath_count": subpath_count, "origin": origin}
    return ("\n".join(lines) + "\n").encode("ascii"), {
        "command_count": len(commands),
        "segment_count": segment_count,
        "subpath_count": subpath_count,
        "origin": origin,
        "byte_size": len(("\n".join(lines) + "\n").encode("ascii")),
    }


def rewrite_content_stream_path_boolean_replacement_descriptor(doc: object, page: object, descriptor: dict[str, object]) -> dict[str, object] | None:
    target_xref = int(finite_number(descriptor.get("target_content_stream_xref") or descriptor.get("content_stream_xref"), 0))
    target_info = editable_pdf_content_stream_target(doc, page, target_xref)
    if target_xref <= 0 or not target_info.get("editable"):
        return None
    before_bytes = bytes(doc.xref_stream(target_xref) or b"")
    if not before_bytes:
        return None
    target_operator = str(descriptor.get("target_operator") or descriptor.get("operator") or "").strip()
    if target_operator not in PDF_PATH_GEOMETRY_OPERATOR_TOKENS:
        return None
    replacement_path, replacement_summary = pdf_path_sequence_bytes_from_descriptor(page, descriptor)
    if not replacement_path:
        return None
    raw_offset = descriptor.get("target_operator_byte_offset")
    if raw_offset is None:
        raw_offset = descriptor.get("operator_byte_offset")
    raw_index = descriptor.get("target_operator_index")
    if raw_index is None:
        raw_index = descriptor.get("operator_index")
    target_offset = int(finite_number(raw_offset, -1)) if raw_offset not in (None, "") else -1
    target_index = int(finite_number(raw_index, -1)) if raw_index not in (None, "") else -1
    text, tokens = scan_pdf_content_stream_tokens(before_bytes)
    operator_runs: list[dict[str, object]] = []
    operator_index = -1
    for token_position, (token, offset) in enumerate(tokens):
        category = PDF_CONTENT_STREAM_OPERATOR_CATEGORIES.get(token)
        if not category:
            continue
        operator_index += 1
        operator_runs.append({
            "token_position": token_position,
            "operator_index": operator_index,
            "operator": token,
            "category": category,
            "byte_offset": offset,
        })
    target_run_position = -1
    for run_position, run in enumerate(operator_runs):
        if str(run.get("category") or "") != "path":
            continue
        run_operator = str(run.get("operator") or "")
        run_offset = int(finite_number(run.get("byte_offset"), -1))
        run_index = int(finite_number(run.get("operator_index"), -1))
        offset_matches = target_offset >= 0 and run_offset == target_offset
        index_matches = target_index >= 0 and run_index == target_index
        if run_operator == target_operator and (offset_matches or index_matches):
            target_run_position = run_position
            break
    if target_run_position < 0:
        return None
    first_run_position = target_run_position
    while first_run_position > 0 and str(operator_runs[first_run_position - 1].get("category") or "") == "path":
        first_run_position -= 1
    last_run_position = target_run_position
    while last_run_position + 1 < len(operator_runs) and str(operator_runs[last_run_position + 1].get("category") or "") == "path":
        last_run_position += 1
    first_run = operator_runs[first_run_position]
    last_run = operator_runs[last_run_position]
    first_token_position = int(finite_number(first_run.get("token_position"), -1))
    last_token_position = int(finite_number(last_run.get("token_position"), -1))
    if first_token_position < 0 or last_token_position < 0:
        return None
    first_operator = str(first_run.get("operator") or "")
    first_indexes = path_geometry_operand_indexes(first_operator)
    if not first_indexes:
        return None
    first_needed = max(first_indexes) + 1
    if first_token_position < first_needed:
        return None
    first_operand_tokens = tokens[first_token_position - first_needed:first_token_position]
    if not all(is_pdf_numeric_token(token) for token, _offset in first_operand_tokens):
        return None
    start = first_operand_tokens[0][1]
    end = int(finite_number(last_run.get("byte_offset"), -1)) + len(str(last_run.get("operator") or ""))
    if start < 0 or end <= start:
        return None
    before_segment = before_bytes[start:end]
    replacement = before_bytes[:start] + replacement_path + before_bytes[end:]
    if replacement == before_bytes:
        return None
    update_pdf_stream(doc, target_xref, replacement)
    after_bytes = bytes(doc.xref_stream(target_xref) or b"")
    target_run = operator_runs[target_run_position]
    return {
        "target_content_stream_xref": target_xref,
        "target_content_stream_scope": target_info.get("scope") or "",
        "target_xobject_xref": target_info.get("target_xobject_xref") or 0,
        "target_xobject_name": target_info.get("target_xobject_name") or "",
        "before_byte_size": len(before_bytes),
        "after_byte_size": len(after_bytes),
        "before_sha256": hashlib.sha256(before_bytes).hexdigest() if before_bytes else "",
        "after_sha256": hashlib.sha256(after_bytes).hexdigest() if after_bytes else "",
        "target_operator_run_rewrite": True,
        "target_operator": target_operator,
        "target_operator_index": target_run.get("operator_index"),
        "target_operator_byte_offset": target_run.get("byte_offset"),
        "path_sequence_operator_count": last_run_position - first_run_position + 1,
        "replacement_path_summary": replacement_summary,
        "replacement_byte_size": len(replacement_path),
        "replaced_byte_size": len(before_segment),
        "boolean_mode": descriptor.get("boolean_mode") or "",
        "geometry_engine": descriptor.get("geometry_engine") or "",
        "robust_geometry_engine": bool(descriptor.get("robust_geometry_engine") or descriptor.get("robust_boolean_geometry_applied")),
        "native_stream_mutated": True,
    }


def rewrite_shared_form_invocation_path_descriptor(
    doc: object,
    page: object,
    page_number: int,
    descriptor: dict[str, object],
) -> dict[str, object] | None:
    selected_invocation_id = str(
        descriptor.get("selected_form_invocation_id")
        or descriptor.get("selected_xobject_invocation_id")
        or ""
    ).strip()
    if not selected_invocation_id:
        return None
    invocation_index = native_pdf_invocation_index(doc, page, page_number)
    if not invocation_index.get("parser_complete") or invocation_index.get("truncated"):
        return None
    invocations = {
        str(row.get("id") or ""): row
        for row in invocation_index.get("form_invocations", [])
        if isinstance(row, dict) and row.get("id")
    }
    selected = invocations.get(selected_invocation_id)
    target_xref = int(finite_number(descriptor.get("target_xobject_xref") or descriptor.get("target_content_stream_xref"), 0))
    if not selected or int(finite_number(selected.get("form_xref"), 0)) != target_xref:
        return None
    chain: list[dict[str, object]] = []
    cursor = selected
    seen: set[str] = set()
    while cursor:
        cursor_id = str(cursor.get("id") or "")
        if not cursor_id or cursor_id in seen:
            return None
        seen.add(cursor_id)
        chain.append(cursor)
        parent_id = str(cursor.get("parent_invocation_id") or "")
        cursor = invocations.get(parent_id) if parent_id else None
    if not chain:
        return None

    page_xref = int(finite_number(getattr(page, "xref", 0), 0))
    root_invocation = chain[-1]
    root_owner_xref = int(finite_number(root_invocation.get("resource_owner_xref"), 0))
    root_caller_stream_xref = int(finite_number(root_invocation.get("caller_stream_xref"), 0))
    if root_owner_xref != page_xref or not pdf_resource_binding_isolatable(doc, page_xref, "XObject"):
        return None
    page_placement = page_content_stream_placement(doc, page, root_caller_stream_xref)
    if page_placement is None:
        return None

    for depth, invocation in enumerate(chain):
        caller_stream_xref = int(finite_number(invocation.get("caller_stream_xref"), 0))
        do_byte_offset = int(finite_number(invocation.get("do_byte_offset"), -1))
        resource_name = str(invocation.get("name") or "")
        if not pdf_do_resource_name_matches(doc, caller_stream_xref, do_byte_offset, resource_name):
            return None
        if depth + 1 < len(chain):
            parent_source_xref = int(finite_number(chain[depth + 1].get("form_xref"), 0))
            if caller_stream_xref != parent_source_xref or not pdf_resource_binding_isolatable(doc, parent_source_xref, "XObject"):
                return None

    cloned_form_xrefs: list[dict[str, object]] = []
    cloned_dictionary_xrefs: list[int] = []
    caller_rewrites: list[dict[str, object]] = []
    selected_clone_xref = clone_pdf_xref_object(doc, target_xref)
    if selected_clone_xref <= 0:
        return None
    cloned_form_xrefs.append({"source_xref": target_xref, "clone_xref": selected_clone_xref, "invocation_id": selected_invocation_id})
    cloned_descriptor = {
        **descriptor,
        "target_content_stream_xref": selected_clone_xref,
        "target_xobject_xref": selected_clone_xref,
        "target_content_stream_scope": "form-xobject-content-stream",
        "clone_and_rebind_shared_form": False,
    }
    target_rewrite = rewrite_content_stream_path_boolean_replacement_descriptor(doc, page, cloned_descriptor)
    if target_rewrite is None:
        return None

    current_clone_xref = selected_clone_xref
    child_invocation = selected
    for parent_invocation in chain[1:]:
        parent_source_xref = int(finite_number(parent_invocation.get("form_xref"), 0))
        parent_clone_xref = clone_pdf_xref_object(doc, parent_source_xref)
        if parent_clone_xref <= 0:
            return None
        child_old_name = str(child_invocation.get("name") or "")
        child_suffix = hashlib.sha256(
            f"{selected_invocation_id}:{child_invocation.get('id') or ''}".encode("utf-8")
        ).hexdigest()[:8]
        child_new_name = unique_pdf_resource_name(
            doc,
            parent_clone_xref,
            "XObject",
            f"FS_{child_old_name}_{child_suffix}",
        )
        if not child_new_name:
            return None
        binding = set_isolated_pdf_resource_binding(
            doc,
            parent_clone_xref,
            "XObject",
            child_new_name,
            current_clone_xref,
        )
        if binding is None:
            return None
        caller_rewrite = rewrite_pdf_do_resource_name(
            doc,
            parent_clone_xref,
            int(finite_number(child_invocation.get("do_byte_offset"), -1)),
            child_old_name,
            child_new_name,
        )
        if caller_rewrite is None:
            return None
        caller_rewrite["source_stream_xref"] = parent_source_xref
        caller_rewrite["caller_invocation_id"] = str(child_invocation.get("id") or "")
        caller_rewrites.append(caller_rewrite)
        cloned_dictionary_xrefs.extend(int(value) for value in binding.get("cloned_dictionary_xrefs", []))
        cloned_form_xrefs.append({
            "source_xref": parent_source_xref,
            "clone_xref": parent_clone_xref,
            "invocation_id": str(parent_invocation.get("id") or ""),
            "selected_child_resource_name": child_new_name,
        })
        current_clone_xref = parent_clone_xref
        child_invocation = parent_invocation

    old_root_name = str(root_invocation.get("name") or "")
    unique_suffix = hashlib.sha256(selected_invocation_id.encode("utf-8")).hexdigest()[:8]
    new_root_name = unique_pdf_resource_name(doc, page_xref, "XObject", f"FS_{old_root_name}_{unique_suffix}")
    if not new_root_name:
        return None
    root_binding = set_isolated_pdf_resource_binding(doc, page_xref, "XObject", new_root_name, current_clone_xref)
    if root_binding is None:
        return None
    cloned_dictionary_xrefs.extend(int(value) for value in root_binding.get("cloned_dictionary_xrefs", []))
    page_caller_clone_xref = clone_pdf_xref_object(doc, root_caller_stream_xref)
    if page_caller_clone_xref <= 0:
        return None
    caller_rewrite = rewrite_pdf_do_resource_name(
        doc,
        page_caller_clone_xref,
        int(finite_number(root_invocation.get("do_byte_offset"), -1)),
        old_root_name,
        new_root_name,
    )
    if caller_rewrite is None:
        return None
    caller_rewrite["source_stream_xref"] = root_caller_stream_xref
    caller_rewrite["caller_invocation_id"] = str(root_invocation.get("id") or "")
    caller_rewrites.append(caller_rewrite)
    page_rebind = rebind_page_content_stream(doc, page_placement, page_caller_clone_xref)
    if page_rebind is None:
        return None
    return {
        "selected_invocation_id": selected_invocation_id,
        "selected_invocation_path": selected.get("invocation_path") or "",
        "selected_nesting_depth": int(finite_number(selected.get("nesting_depth"), 0)),
        "target_content_stream_xref": selected_clone_xref,
        "target_content_stream_scope": "form-xobject-content-stream",
        "target_xobject_xref": selected_clone_xref,
        "source_target_xobject_xref": target_xref,
        "target_rewrite": target_rewrite,
        "cloned_form_xrefs": cloned_form_xrefs,
        "cloned_page_content_stream_xrefs": [{
            "source_xref": root_caller_stream_xref,
            "clone_xref": page_caller_clone_xref,
            "contents_index": page_placement.get("contents_index"),
        }],
        "cloned_dictionary_xrefs": sorted(set(cloned_dictionary_xrefs)),
        "root_binding": root_binding,
        "caller_rewrite": caller_rewrite,
        "caller_rewrites": caller_rewrites,
        "page_content_rebind": page_rebind,
        "shared_form_clone_rebind_applied": True,
        "native_stream_mutated": True,
    }


def rewrite_extgstate_blend_mode_descriptor(doc: object, descriptor: dict[str, object]) -> dict[str, object] | None:
    target_xref = int(finite_number(descriptor.get("target_extgstate_xref") or descriptor.get("extgstate_xref"), 0))
    if target_xref <= 0:
        return None
    try:
        xref_limit = int(finite_number(doc.xref_length() if hasattr(doc, "xref_length") else 0, 0))
    except Exception:  # noqa: BLE001
        xref_limit = 0
    if target_xref >= xref_limit:
        return None
    target_mode = normalize_pdf_blend_mode(
        descriptor.get("blend_mode") or descriptor.get("target_blend_mode") or descriptor.get("targetBlendMode"),
        "",
    )
    if not target_mode:
        return None
    try:
        before_object = str(doc.xref_object(target_xref, compressed=False) or "")
    except Exception:  # noqa: BLE001
        return None
    if "/Type /ExtGState" not in before_object and "/BM " not in before_object:
        return None
    before_match = re.search(r"/BM\s*/([A-Za-z0-9]+)", before_object)
    before_mode = normalize_pdf_blend_mode(before_match.group(1), "") if before_match else ""
    if before_match:
        after_object = re.sub(r"/BM\s*/[A-Za-z0-9]+", f"/BM /{target_mode}", before_object, count=1)
    else:
        after_object = re.sub(r">>\s*$", f"  /BM /{target_mode}\n>>", before_object, count=1)
    if after_object == before_object:
        return None
    doc.update_object(target_xref, after_object)
    try:
        verified_object = str(doc.xref_object(target_xref, compressed=False) or "")
    except Exception:  # noqa: BLE001
        verified_object = after_object
    verified_match = re.search(r"/BM\s*/([A-Za-z0-9]+)", verified_object)
    verified_mode = normalize_pdf_blend_mode(verified_match.group(1), "") if verified_match else ""
    return {
        "target_extgstate_xref": target_xref,
        "resource_name": descriptor.get("target_resource_name") or descriptor.get("resource_name") or "",
        "before_blend_mode": before_mode,
        "after_blend_mode": verified_mode,
        "requested_blend_mode": target_mode,
        "before_object_sha256": hashlib.sha256(before_object.encode("utf-8", errors="ignore")).hexdigest(),
        "after_object_sha256": hashlib.sha256(verified_object.encode("utf-8", errors="ignore")).hexdigest(),
        "native_resource_mutated": verified_mode == target_mode,
    }


def extgstate_object_source(doc: object, target_xref: int) -> str:
    if target_xref <= 0:
        return ""
    try:
        xref_limit = int(finite_number(doc.xref_length() if hasattr(doc, "xref_length") else 0, 0))
    except Exception:  # noqa: BLE001
        xref_limit = 0
    if target_xref >= xref_limit:
        return ""
    try:
        source = str(doc.xref_object(target_xref, compressed=False) or "")
    except Exception:  # noqa: BLE001
        return ""
    if "/Type /ExtGState" not in source and "/BM " not in source and "/ca " not in source and "/CA " not in source and "/SMask " not in source:
        return ""
    return source


def upsert_pdf_dictionary_scalar(source: str, key: str, value: float) -> str:
    token = f"/{key} {pdf_operator_number(max(0.0, min(1.0, value)))}"
    if re.search(rf"/{re.escape(key)}\s+[-+]?\d*\.?\d+", source):
        return re.sub(rf"/{re.escape(key)}\s+[-+]?\d*\.?\d+", token, source, count=1)
    return re.sub(r">>\s*$", f"  {token}\n>>", source, count=1)


def upsert_pdf_dictionary_number(source: str, key: str, value: float) -> str:
    token = f"/{key} {pdf_operator_number(value)}"
    if re.search(rf"/{re.escape(key)}\s+[-+]?\d*\.?\d+", source):
        return re.sub(rf"/{re.escape(key)}\s+[-+]?\d*\.?\d+", token, source, count=1)
    return re.sub(r">>\s*$", f"  {token}\n>>", source, count=1)


def rewrite_extgstate_opacity_descriptor(doc: object, descriptor: dict[str, object]) -> dict[str, object] | None:
    target_xref = int(finite_number(descriptor.get("target_extgstate_xref") or descriptor.get("extgstate_xref"), 0))
    before_object = extgstate_object_source(doc, target_xref)
    if not before_object:
        return None
    fill_alpha = descriptor.get("fill_alpha")
    if fill_alpha is None:
        fill_alpha = descriptor.get("fillAlpha")
    stroke_alpha = descriptor.get("stroke_alpha")
    if stroke_alpha is None:
        stroke_alpha = descriptor.get("strokeAlpha")
    opacity = descriptor.get("opacity")
    if opacity is None:
        opacity = descriptor.get("target_opacity")
    if fill_alpha is None and stroke_alpha is None and opacity is None:
        return None
    target_fill = max(0.0, min(1.0, finite_number(fill_alpha if fill_alpha is not None else opacity, 1)))
    target_stroke = max(0.0, min(1.0, finite_number(stroke_alpha if stroke_alpha is not None else opacity, 1)))
    before_fill = parse_pdf_scalar_after_key(before_object, "ca")
    before_stroke = parse_pdf_scalar_after_key(before_object, "CA")
    after_object = upsert_pdf_dictionary_scalar(before_object, "ca", target_fill)
    after_object = upsert_pdf_dictionary_scalar(after_object, "CA", target_stroke)
    if after_object == before_object:
        return None
    doc.update_object(target_xref, after_object)
    verified_object = extgstate_object_source(doc, target_xref) or after_object
    return {
        "target_extgstate_xref": target_xref,
        "resource_name": descriptor.get("target_resource_name") or descriptor.get("resource_name") or "",
        "before_fill_alpha": before_fill,
        "before_stroke_alpha": before_stroke,
        "after_fill_alpha": parse_pdf_scalar_after_key(verified_object, "ca"),
        "after_stroke_alpha": parse_pdf_scalar_after_key(verified_object, "CA"),
        "requested_fill_alpha": target_fill,
        "requested_stroke_alpha": target_stroke,
        "before_object_sha256": hashlib.sha256(before_object.encode("utf-8", errors="ignore")).hexdigest(),
        "after_object_sha256": hashlib.sha256(verified_object.encode("utf-8", errors="ignore")).hexdigest(),
        "native_resource_mutated": True,
    }


def rewrite_extgstate_appearance_descriptor(doc: object, descriptor: dict[str, object]) -> dict[str, object] | None:
    target_xref = int(finite_number(descriptor.get("target_extgstate_xref") or descriptor.get("extgstate_xref"), 0))
    before_object = extgstate_object_source(doc, target_xref)
    if not before_object:
        return None
    blend_result = rewrite_extgstate_blend_mode_descriptor(doc, descriptor)
    opacity_result = rewrite_extgstate_opacity_descriptor(doc, descriptor)
    if blend_result is None and opacity_result is None:
        return None
    verified_object = extgstate_object_source(doc, target_xref)
    if not verified_object:
        return None
    blend_match = re.search(r"/BM\s*/([A-Za-z0-9]+)", verified_object)
    return {
        "target_extgstate_xref": target_xref,
        "resource_name": descriptor.get("target_resource_name") or descriptor.get("resource_name") or "",
        "before_blend_mode": (blend_result or {}).get("before_blend_mode") or "",
        "after_blend_mode": normalize_pdf_blend_mode(blend_match.group(1), "") if blend_match else "",
        "requested_blend_mode": normalize_pdf_blend_mode(
            descriptor.get("blend_mode") or descriptor.get("target_blend_mode") or descriptor.get("targetBlendMode"),
            "",
        ),
        "before_fill_alpha": (opacity_result or {}).get("before_fill_alpha"),
        "before_stroke_alpha": (opacity_result or {}).get("before_stroke_alpha"),
        "after_fill_alpha": parse_pdf_scalar_after_key(verified_object, "ca"),
        "after_stroke_alpha": parse_pdf_scalar_after_key(verified_object, "CA"),
        "requested_fill_alpha": (opacity_result or {}).get("requested_fill_alpha"),
        "requested_stroke_alpha": (opacity_result or {}).get("requested_stroke_alpha"),
        "before_object_sha256": hashlib.sha256(before_object.encode("utf-8", errors="ignore")).hexdigest(),
        "after_object_sha256": hashlib.sha256(verified_object.encode("utf-8", errors="ignore")).hexdigest(),
        "blend_mode_mutated": blend_result is not None,
        "opacity_mutated": opacity_result is not None,
        "native_resource_mutated": True,
    }


def rewrite_extgstate_soft_mask_descriptor(doc: object, descriptor: dict[str, object]) -> dict[str, object] | None:
    target_xref = int(finite_number(descriptor.get("target_extgstate_xref") or descriptor.get("extgstate_xref"), 0))
    before_object = extgstate_object_source(doc, target_xref)
    if not before_object:
        return None
    before_smask = parse_pdf_smask_value(before_object)
    if before_smask.get("soft_mask") == "/None":
        return None
    if re.search(r"/SMask\s+(?:/[A-Za-z0-9]+|\d+\s+\d+\s+R)", before_object):
        after_object = re.sub(r"/SMask\s+(?:/[A-Za-z0-9]+|\d+\s+\d+\s+R)", "/SMask /None", before_object, count=1)
    else:
        after_object = re.sub(r">>\s*$", "  /SMask /None\n>>", before_object, count=1)
    if after_object == before_object:
        return None
    doc.update_object(target_xref, after_object)
    verified_object = extgstate_object_source(doc, target_xref) or after_object
    after_smask = parse_pdf_smask_value(verified_object)
    return {
        "target_extgstate_xref": target_xref,
        "resource_name": descriptor.get("target_resource_name") or descriptor.get("resource_name") or "",
        "before_soft_mask": before_smask.get("soft_mask") or "",
        "before_soft_mask_xref": before_smask.get("soft_mask_xref") or 0,
        "after_soft_mask": after_smask.get("soft_mask") or "",
        "after_soft_mask_xref": after_smask.get("soft_mask_xref") or 0,
        "before_object_sha256": hashlib.sha256(before_object.encode("utf-8", errors="ignore")).hexdigest(),
        "after_object_sha256": hashlib.sha256(verified_object.encode("utf-8", errors="ignore")).hexdigest(),
        "native_resource_mutated": after_smask.get("soft_mask") == "/None",
    }


def selected_form_invocation_clone_context(
    doc: object,
    page: object,
    page_number: int,
    descriptor: dict[str, object],
) -> dict[str, object] | None:
    selected_invocation_id = str(
        descriptor.get("selected_form_invocation_id")
        or descriptor.get("selected_xobject_invocation_id")
        or ""
    ).strip()
    if not selected_invocation_id:
        return None
    invocation_index = native_pdf_invocation_index(doc, page, page_number)
    if not invocation_index.get("parser_complete") or invocation_index.get("truncated"):
        return None
    invocations = {
        str(row.get("id") or ""): row
        for row in invocation_index.get("form_invocations", [])
        if isinstance(row, dict) and row.get("id")
    }
    selected = invocations.get(selected_invocation_id)
    if not selected:
        return None
    chain: list[dict[str, object]] = []
    cursor = selected
    seen: set[str] = set()
    while cursor:
        cursor_id = str(cursor.get("id") or "")
        if not cursor_id or cursor_id in seen:
            return None
        seen.add(cursor_id)
        chain.append(cursor)
        parent_id = str(cursor.get("parent_invocation_id") or "")
        cursor = invocations.get(parent_id) if parent_id else None
    page_xref = int(finite_number(getattr(page, "xref", 0), 0))
    root_invocation = chain[-1]
    root_caller_stream_xref = int(finite_number(root_invocation.get("caller_stream_xref"), 0))
    if int(finite_number(root_invocation.get("resource_owner_xref"), 0)) != page_xref:
        return None
    if not pdf_resource_binding_isolatable(doc, page_xref, "XObject"):
        return None
    page_placement = page_content_stream_placement(doc, page, root_caller_stream_xref)
    if page_placement is None:
        return None
    for depth, invocation in enumerate(chain):
        caller_stream_xref = int(finite_number(invocation.get("caller_stream_xref"), 0))
        do_byte_offset = int(finite_number(invocation.get("do_byte_offset"), -1))
        resource_name = str(invocation.get("name") or "")
        if not pdf_do_resource_name_matches(doc, caller_stream_xref, do_byte_offset, resource_name):
            return None
        if depth + 1 < len(chain):
            parent_source_xref = int(finite_number(chain[depth + 1].get("form_xref"), 0))
            if caller_stream_xref != parent_source_xref or not pdf_resource_binding_isolatable(doc, parent_source_xref, "XObject"):
                return None
    return {
        "selected_invocation_id": selected_invocation_id,
        "selected": selected,
        "chain": chain,
        "invocation_index": invocation_index,
        "page_xref": page_xref,
        "root_invocation": root_invocation,
        "root_caller_stream_xref": root_caller_stream_xref,
        "page_placement": page_placement,
    }


def rebind_selected_form_clone_to_page(
    doc: object,
    context: dict[str, object],
    selected_clone_xref: int,
    selected_clone_record: dict[str, object],
    cloned_dictionary_xrefs: list[int] | None = None,
) -> dict[str, object] | None:
    selected_invocation_id = str(context.get("selected_invocation_id") or "")
    selected = context.get("selected") if isinstance(context.get("selected"), dict) else {}
    chain = context.get("chain") if isinstance(context.get("chain"), list) else []
    root_invocation = context.get("root_invocation") if isinstance(context.get("root_invocation"), dict) else {}
    if not selected_invocation_id or not selected or not chain or selected_clone_xref <= 0:
        return None
    cloned_form_xrefs: list[dict[str, object]] = [selected_clone_record]
    dictionary_xrefs = [int(value) for value in (cloned_dictionary_xrefs or []) if int(finite_number(value, 0)) > 0]
    caller_rewrites: list[dict[str, object]] = []
    current_clone_xref = selected_clone_xref
    child_invocation = selected
    for parent_invocation in chain[1:]:
        parent_source_xref = int(finite_number(parent_invocation.get("form_xref"), 0))
        parent_clone_xref = clone_pdf_xref_object(doc, parent_source_xref)
        if parent_clone_xref <= 0:
            return None
        child_old_name = str(child_invocation.get("name") or "")
        child_suffix = hashlib.sha256(
            f"{selected_invocation_id}:{child_invocation.get('id') or ''}".encode("utf-8")
        ).hexdigest()[:8]
        child_new_name = unique_pdf_resource_name(doc, parent_clone_xref, "XObject", f"FS_{child_old_name}_{child_suffix}")
        if not child_new_name:
            return None
        binding = set_isolated_pdf_resource_binding(
            doc,
            parent_clone_xref,
            "XObject",
            child_new_name,
            current_clone_xref,
        )
        if binding is None:
            return None
        caller_rewrite = rewrite_pdf_do_resource_name(
            doc,
            parent_clone_xref,
            int(finite_number(child_invocation.get("do_byte_offset"), -1)),
            child_old_name,
            child_new_name,
        )
        if caller_rewrite is None:
            return None
        caller_rewrite["source_stream_xref"] = parent_source_xref
        caller_rewrite["caller_invocation_id"] = str(child_invocation.get("id") or "")
        caller_rewrites.append(caller_rewrite)
        dictionary_xrefs.extend(int(value) for value in binding.get("cloned_dictionary_xrefs", []))
        cloned_form_xrefs.append({
            "source_xref": parent_source_xref,
            "clone_xref": parent_clone_xref,
            "invocation_id": str(parent_invocation.get("id") or ""),
            "selected_child_resource_name": child_new_name,
        })
        current_clone_xref = parent_clone_xref
        child_invocation = parent_invocation

    page_xref = int(finite_number(context.get("page_xref"), 0))
    old_root_name = str(root_invocation.get("name") or "")
    unique_suffix = hashlib.sha256(selected_invocation_id.encode("utf-8")).hexdigest()[:8]
    new_root_name = unique_pdf_resource_name(doc, page_xref, "XObject", f"FS_{old_root_name}_{unique_suffix}")
    if not new_root_name:
        return None
    root_binding = set_isolated_pdf_resource_binding(doc, page_xref, "XObject", new_root_name, current_clone_xref)
    if root_binding is None:
        return None
    dictionary_xrefs.extend(int(value) for value in root_binding.get("cloned_dictionary_xrefs", []))
    root_caller_stream_xref = int(finite_number(context.get("root_caller_stream_xref"), 0))
    page_caller_clone_xref = clone_pdf_xref_object(doc, root_caller_stream_xref)
    if page_caller_clone_xref <= 0:
        return None
    caller_rewrite = rewrite_pdf_do_resource_name(
        doc,
        page_caller_clone_xref,
        int(finite_number(root_invocation.get("do_byte_offset"), -1)),
        old_root_name,
        new_root_name,
    )
    if caller_rewrite is None:
        return None
    caller_rewrite["source_stream_xref"] = root_caller_stream_xref
    caller_rewrite["caller_invocation_id"] = str(root_invocation.get("id") or "")
    caller_rewrites.append(caller_rewrite)
    page_rebind = rebind_page_content_stream(doc, context.get("page_placement") or {}, page_caller_clone_xref)
    if page_rebind is None:
        return None
    return {
        "cloned_form_xrefs": cloned_form_xrefs,
        "cloned_page_content_stream_xrefs": [{
            "source_xref": root_caller_stream_xref,
            "clone_xref": page_caller_clone_xref,
            "contents_index": (context.get("page_placement") or {}).get("contents_index"),
        }],
        "cloned_dictionary_xrefs": sorted(set(dictionary_xrefs)),
        "root_binding": root_binding,
        "caller_rewrite": caller_rewrite,
        "caller_rewrites": caller_rewrites,
        "page_content_rebind": page_rebind,
        "shared_form_clone_rebind_applied": True,
    }


def selected_form_paint_context_has_overprint(
    doc: object,
    selected_form_xref: int,
    resource_names: list[object],
) -> bool:
    for raw_name in resource_names:
        resource_name = str(raw_name or "").strip().lstrip("/")
        if not resource_name:
            continue
        value_type, value = pdf_xref_key_payload(
            doc,
            selected_form_xref,
            f"Resources/ExtGState/{resource_name}",
        )
        extgstate_xref = pdf_reference_xref(value_type, value)
        if extgstate_xref <= 0:
            return True
        source = pdf_xref_object_source(doc, extgstate_xref)
        if not source:
            return True
        if re.search(r"/(?:OP|op)\s+true\b", source):
            return True
    return False


def selected_form_has_transparency_group(doc: object, selected_form_xref: int) -> bool:
    _group_type, group_subtype = pdf_xref_key_payload(doc, selected_form_xref, "Group/S")
    if str(group_subtype or "").strip() == "/Transparency":
        return True
    source = pdf_xref_object_source(doc, selected_form_xref)
    return bool(re.search(r"/Group\s*<<[^>]*?/S\s*/Transparency\b", source, re.DOTALL))


def selected_form_extgstate_overrides_stroke_property(
    doc: object,
    selected_form_xref: int,
    resource_names: list[object],
    property_name: str,
) -> bool:
    key = {
        "width": "LW",
        "dash": "D",
        "cap": "LC",
        "join": "LJ",
        "miter_limit": "ML",
    }.get(property_name)
    if not key:
        return True
    for raw_name in resource_names:
        resource_name = str(raw_name or "").strip().lstrip("/")
        if not resource_name:
            continue
        value_type, value = pdf_xref_key_payload(
            doc,
            selected_form_xref,
            f"Resources/ExtGState/{resource_name}",
        )
        extgstate_xref = pdf_reference_xref(value_type, value)
        if extgstate_xref <= 0:
            return True
        source = pdf_xref_object_source(doc, extgstate_xref)
        if not source or re.search(rf"/{key}\s", source):
            return True
    return False


def pdf_content_span_has_unknown_operator(stream_bytes: bytes, start: int, end: int) -> bool:
    _text, tokens = scan_pdf_content_stream_tokens(stream_bytes)
    for token, offset in tokens:
        if offset < start or offset >= end:
            continue
        if token in PDF_CONTENT_STREAM_OPERATOR_CATEGORIES or is_pdf_numeric_token(token):
            continue
        if token.startswith("/") or token in {"[", "]", "{", "}", "<<", ">>", "true", "false", "null"}:
            continue
        if re.fullmatch(r"[A-Za-z][A-Za-z0-9*']*", token or ""):
            return True
    return False


def rewrite_content_stream_local_path_appearance_descriptor(
    doc: object,
    page: object,
    descriptor: dict[str, object],
    color_patches: list[dict[str, object]],
    stroke_patches: list[dict[str, object]],
) -> dict[str, object] | None:
    target_xref = int(finite_number(descriptor.get("target_content_stream_xref"), 0))
    target_info = editable_pdf_content_stream_target(doc, page, target_xref)
    if target_xref <= 0 or not target_info.get("editable"):
        return None
    before_bytes = pdf_xref_stream_bytes(doc, target_xref)
    if not before_bytes:
        return None
    profile = pdf_content_stream_operator_profile(before_bytes)
    if profile.get("operator_runs_truncated") or profile.get("inline_image_ambiguity"):
        return None
    path_operator = str(descriptor.get("selected_path_operator") or "")
    path_index = int(finite_number(descriptor.get("selected_path_operator_index"), -1))
    paint_operator = str(descriptor.get("selected_paint_operator") or "")
    paint_index = int(finite_number(descriptor.get("selected_paint_operator_index"), -1))
    matched_sequence: dict[str, object] | None = None
    for row in profile.get("operator_runs", []):
        if not isinstance(row, dict):
            continue
        sequence = row.get("path_sequence") if isinstance(row.get("path_sequence"), dict) else None
        if (
            sequence
            and str(row.get("operator") or "") == path_operator
            and int(finite_number(row.get("operator_index"), -1)) == path_index
        ):
            matched_sequence = sequence
            break
    if matched_sequence is None:
        return None
    paint_context = matched_sequence.get("paint_context") if isinstance(matched_sequence.get("paint_context"), dict) else {}
    actual_paint = paint_context.get("paint_operator") if isinstance(paint_context.get("paint_operator"), dict) else {}
    if (
        not paint_context.get("exact")
        or paint_context.get("local_state_materialization_supported") is not True
        or str(actual_paint.get("operator") or "") != paint_operator
        or int(finite_number(actual_paint.get("operator_index"), -1)) != paint_index
    ):
        return None
    first_offset = int(finite_number(matched_sequence.get("first_byte_offset"), -1))
    paint_offset = int(finite_number(actual_paint.get("byte_offset"), -1))
    paint_end = paint_offset + len(paint_operator)
    if first_offset < 0 or paint_offset <= first_offset or paint_end > len(before_bytes):
        return None
    if before_bytes[paint_offset:paint_end].decode("latin-1", errors="ignore") != paint_operator:
        return None
    if pdf_content_span_has_unknown_operator(before_bytes, first_offset, paint_end):
        return None

    operators: list[tuple[int, str, str]] = []
    for patch in color_patches:
        channel = str(patch.get("color_channel") or "").strip().lower()
        operator = str(patch.get("target_operator") or "").strip()
        expected_channel = "fill" if operator.islower() else "stroke" if operator.isupper() else ""
        target_components = pdf_device_color_components_from_descriptor(patch, operator)
        if (
            operator not in PDF_DEVICE_COLOR_OPERATOR_TOKENS
            or channel != expected_channel
            or target_components is None
        ):
            return None
        operators.append((
            0 if channel == "fill" else 1,
            channel,
            f"{' '.join(pdf_operator_number(value) for value in target_components)} {operator}",
        ))
    stroke_order = {"width": 2, "dash": 3, "cap": 4, "join": 5, "miter_limit": 6}
    for patch in stroke_patches:
        property_name = str(patch.get("stroke_property") or "").strip().lower()
        if property_name not in stroke_order:
            return None
        if property_name == "dash":
            raw_array = patch.get("target_dash_array")
            if not isinstance(raw_array, (list, tuple)):
                return None
            dash_array = [finite_number(value, -1) for value in list(raw_array)[:24]]
            if any(value < 0 or value > 10000 for value in dash_array) or (dash_array and not any(value > 0 for value in dash_array)):
                return None
            phase = finite_number(patch.get("target_dash_phase"), 0)
            if phase < -10000 or phase > 10000:
                return None
            text = f"[{' '.join(pdf_operator_number(value) for value in dash_array)}] {pdf_operator_number(phase)} d"
        else:
            value = finite_number(patch.get("target_value"), -1)
            operator = {"width": "w", "cap": "J", "join": "j", "miter_limit": "M"}[property_name]
            if property_name == "width" and not 0 < value <= 500:
                return None
            if property_name in {"cap", "join"} and (not float(value).is_integer() or int(value) not in {0, 1, 2}):
                return None
            if property_name == "miter_limit" and not 1 <= value <= 1000:
                return None
            text = f"{pdf_operator_number(value)} {operator}"
        operators.append((stroke_order[property_name], property_name, text))
    if not operators:
        return None
    operators.sort(key=lambda row: (row[0], row[1]))
    local_prefix = ("q\n" + "\n".join(row[2] for row in operators) + "\n").encode("ascii")
    source_span = before_bytes[first_offset:paint_end]
    replacement = before_bytes[:first_offset] + local_prefix + before_bytes[first_offset:paint_end] + b"\nQ\n" + before_bytes[paint_end:]
    if replacement == before_bytes:
        return None
    update_pdf_stream(doc, target_xref, replacement)
    after_bytes = pdf_xref_stream_bytes(doc, target_xref)
    return {
        "target_content_stream_xref": target_xref,
        "target_content_stream_scope": target_info.get("scope") or "",
        "before_byte_size": len(before_bytes),
        "after_byte_size": len(after_bytes),
        "before_sha256": hashlib.sha256(before_bytes).hexdigest(),
        "after_sha256": hashlib.sha256(after_bytes).hexdigest(),
        "local_state_materialization_applied": True,
        "balanced_graphics_state_wrapper": True,
        "graphics_state_wrapper_q_count": 1,
        "graphics_state_wrapper_Q_count": 1,
        "source_path_paint_span_sha256": hashlib.sha256(source_span).hexdigest(),
        "source_path_paint_span_byte_size": len(source_span),
        "localized_color_channels": [str(patch.get("color_channel") or "") for patch in color_patches],
        "localized_color_spaces": [str(patch.get("target_color_space") or patch.get("source_color_space") or "") for patch in color_patches],
        "localized_stroke_properties": [str(patch.get("stroke_property") or "") for patch in stroke_patches],
        "selected_path_operator_index": path_index,
        "selected_paint_operator_index": paint_index,
        "native_stream_mutated": True,
    }


def clone_selected_form_extgstate_appearance_resource(
    doc: object,
    context: dict[str, object],
    selected_form_xref: int,
    descriptor: dict[str, object],
) -> dict[str, object] | None:
    target_extgstate_xref = int(finite_number(descriptor.get("target_extgstate_xref") or descriptor.get("extgstate_xref"), 0))
    resource_name = str(descriptor.get("target_resource_name") or descriptor.get("resource_name") or "")
    owner_xref = int(finite_number(descriptor.get("target_resource_owner_xref") or descriptor.get("resource_owner_xref"), 0))
    binding_id = str(descriptor.get("target_resource_binding_id") or descriptor.get("resource_binding_id") or "")
    membership_id = str(descriptor.get("selected_extgstate_membership_id") or "")
    if (
        selected_form_xref <= 0
        or owner_xref != selected_form_xref
        or target_extgstate_xref <= 0
        or not resource_name
        or not binding_id
        or membership_id != binding_id
        or not pdf_resource_binding_isolatable(doc, selected_form_xref, "ExtGState")
    ):
        return None
    resolved_type, resolved_value = pdf_xref_key_payload(doc, selected_form_xref, f"Resources/ExtGState/{resource_name}")
    if pdf_reference_xref(resolved_type, resolved_value) != target_extgstate_xref:
        return None
    bindings = [
        binding
        for scope in context["invocation_index"].get("resource_scopes", [])
        if isinstance(scope, dict)
        for binding in scope.get("bindings", [])
        if isinstance(binding, dict)
    ]
    binding = next((
        row for row in bindings
        if str(row.get("id") or "") == binding_id
        and str(row.get("kind") or "") == "extgstate"
        and str(row.get("name") or "") == resource_name
        and int(finite_number(row.get("owner_xref"), 0)) == selected_form_xref
        and int(finite_number(row.get("target_xref"), 0)) == target_extgstate_xref
    ), None)
    if binding is None:
        return None
    usages = [
        row for row in context["invocation_index"].get("resource_usages", [])
        if isinstance(row, dict)
        and str(row.get("binding_id") or "") == binding_id
        and str(row.get("operator") or "") == "gs"
        and int(finite_number(row.get("owner_xref"), 0)) == selected_form_xref
    ]
    requested_usage_ids = {str(value) for value in descriptor.get("target_resource_usage_ids", []) if value}
    actual_usage_ids = {str(row.get("id") or "") for row in usages if row.get("id")}
    if not usages or (requested_usage_ids and not requested_usage_ids.issubset(actual_usage_ids)):
        return None
    semantic_usage_ids = {
        (
            int(finite_number(row.get("stream_xref"), 0)),
            int(finite_number(row.get("operator_index"), -1)),
            int(finite_number(row.get("byte_offset"), -1)),
            str(row.get("resource_name") or ""),
        )
        for row in usages
    }
    if descriptor.get("selected_path_appearance_stack") and len(semantic_usage_ids) != 1:
        return None
    source_object = extgstate_object_source(doc, target_extgstate_xref)
    expected_object_sha256 = str(descriptor.get("source_extgstate_object_sha256") or "")
    if not source_object or not expected_object_sha256 or hashlib.sha256(source_object.encode("utf-8", errors="ignore")).hexdigest() != expected_object_sha256:
        return None
    source_blend_mode = normalize_pdf_blend_mode(descriptor.get("source_blend_mode"), "Normal")
    source_blend_match = re.search(r"/BM\s*/([A-Za-z0-9]+)", source_object)
    actual_blend_mode = normalize_pdf_blend_mode(source_blend_match.group(1), "Normal") if source_blend_match else "Normal"
    actual_fill_alpha = parse_pdf_scalar_after_key(source_object, "ca")
    actual_stroke_alpha = parse_pdf_scalar_after_key(source_object, "CA")
    expected_fill_alpha = finite_number(descriptor.get("source_fill_alpha"), 1)
    expected_stroke_alpha = finite_number(descriptor.get("source_stroke_alpha"), expected_fill_alpha)
    if (
        source_blend_mode != actual_blend_mode
        or abs((actual_fill_alpha if actual_fill_alpha is not None else 1) - expected_fill_alpha) > 0.0001
        or abs((actual_stroke_alpha if actual_stroke_alpha is not None else 1) - expected_stroke_alpha) > 0.0001
    ):
        return None

    cloned_extgstate_xref = clone_pdf_xref_object(doc, target_extgstate_xref)
    if cloned_extgstate_xref <= 0:
        return None
    cloned_descriptor = {
        "descriptor_type": "advanced_feature_graph_edit",
        **descriptor,
        "target_extgstate_xref": cloned_extgstate_xref,
    }
    action = str(descriptor.get("action") or "rewrite_extgstate_appearance")
    if action == "rewrite_extgstate_appearance":
        resource_rewrite = rewrite_extgstate_appearance_descriptor(doc, cloned_descriptor)
    elif action == "rewrite_extgstate_blend_mode":
        resource_rewrite = rewrite_extgstate_blend_mode_descriptor(doc, cloned_descriptor)
    elif action == "rewrite_extgstate_opacity":
        resource_rewrite = rewrite_extgstate_opacity_descriptor(doc, cloned_descriptor)
    else:
        return None
    if resource_rewrite is None:
        return None
    return {
        "source_target_extgstate_xref": target_extgstate_xref,
        "target_extgstate_xref": cloned_extgstate_xref,
        "target_resource_name": resource_name,
        "target_resource_binding_id": binding_id,
        "target_resource_usage_ids": sorted(actual_usage_ids),
        "resource_rewrite": resource_rewrite,
    }


def rewrite_selected_form_invocation_rgb_color_descriptor(
    doc: object,
    page: object,
    page_number: int,
    descriptor: dict[str, object],
) -> dict[str, object] | None:
    context = selected_form_invocation_clone_context(doc, page, page_number, descriptor)
    if context is None:
        return None
    selected = context["selected"]
    selected_form_xref = int(finite_number(selected.get("form_xref"), 0))
    target_xref = int(finite_number(
        descriptor.get("target_xobject_xref")
        or descriptor.get("target_content_stream_xref")
        or descriptor.get("content_stream_xref"),
        0,
    ))
    if (
        selected_form_xref <= 0
        or target_xref != selected_form_xref
        or str(descriptor.get("target_content_stream_scope") or "") != "form-xobject-content-stream"
    ):
        return None

    before_bytes = pdf_xref_stream_bytes(doc, selected_form_xref)
    if not before_bytes:
        return None
    expected_source_stream_sha256 = str(descriptor.get("source_form_stream_sha256") or "")
    if not expected_source_stream_sha256 or hashlib.sha256(before_bytes).hexdigest() != expected_source_stream_sha256:
        return None
    profile = pdf_content_stream_operator_profile(before_bytes)
    raw_device_color_patches = descriptor.get("device_color_patches")
    raw_rgb_color_patches = descriptor.get("rgb_color_patches")
    raw_color_patches = raw_device_color_patches if isinstance(raw_device_color_patches, list) else raw_rgb_color_patches
    device_color_patches = [patch for patch in raw_color_patches if isinstance(patch, dict)] if isinstance(raw_color_patches, list) else []
    raw_special_color_patches = descriptor.get("special_color_patches")
    special_color_patches = [patch for patch in raw_special_color_patches if isinstance(patch, dict)] if isinstance(raw_special_color_patches, list) else []
    color_patches = [*device_color_patches, *special_color_patches]
    if not color_patches and str(descriptor.get("target_operator") or "") in PDF_DEVICE_COLOR_OPERATOR_TOKENS:
        color_patches = [descriptor]
    raw_stroke_patches = descriptor.get("stroke_style_patches")
    stroke_patches = [patch for patch in raw_stroke_patches if isinstance(patch, dict)] if isinstance(raw_stroke_patches, list) else []
    raw_extgstate_patch = descriptor.get("extgstate_appearance_patch")
    extgstate_patch = raw_extgstate_patch if isinstance(raw_extgstate_patch, dict) else None
    expected_stream_sha256 = str((extgstate_patch or {}).get("source_form_stream_sha256") or "")
    if extgstate_patch and expected_stream_sha256 != expected_source_stream_sha256:
        return None
    has_local_state_patches = any(bool(patch.get("localize_appearance_state")) for patch in [*color_patches, *stroke_patches])
    if (not color_patches and not stroke_patches and not extgstate_patch) or len(color_patches) > 2 or len(stroke_patches) > 5:
        return None
    if has_local_state_patches and any(
        selected_form_has_transparency_group(doc, int(finite_number(row.get("form_xref"), 0)))
        for row in context.get("chain", [])
        if isinstance(row, dict) and int(finite_number(row.get("form_xref"), 0)) > 0
    ):
        return None
    validated_color_patches: list[dict[str, object]] = []
    validated_stroke_patches: list[dict[str, object]] = []
    matched_sequence_identity: tuple[int, int, int] | None = None
    matched_paint_context: dict[str, object] | None = None
    extgstate_names: list[object] = []
    extgstate_usages: list[dict[str, object]] = []

    def matched_path_sequence(patch: dict[str, object]) -> tuple[dict[str, object], dict[str, object], dict[str, object]] | None:
        nonlocal matched_sequence_identity, matched_paint_context, extgstate_names, extgstate_usages
        path_operator = str(patch.get("selected_path_operator") or "")
        path_index = int(finite_number(patch.get("selected_path_operator_index"), -1))
        path_offset = int(finite_number(patch.get("selected_path_operator_byte_offset"), -1))
        paint_operator = str(patch.get("selected_paint_operator") or "")
        paint_index = int(finite_number(patch.get("selected_paint_operator_index"), -1))
        paint_offset = int(finite_number(patch.get("selected_paint_operator_byte_offset"), -1))
        matched_sequence: dict[str, object] | None = None
        for row in profile.get("operator_runs", []):
            if not isinstance(row, dict):
                continue
            sequence = row.get("path_sequence") if isinstance(row.get("path_sequence"), dict) else None
            if not sequence:
                continue
            if (
                str(row.get("operator") or "") == path_operator
                and int(finite_number(row.get("operator_index"), -1)) == path_index
                and int(finite_number(row.get("byte_offset"), -1)) == path_offset
            ):
                matched_sequence = sequence
                break
        if matched_sequence is None:
            return None
        sequence_identity = (
            int(finite_number(matched_sequence.get("first_operator_index"), -1)),
            int(finite_number(matched_sequence.get("last_operator_index"), -1)),
            paint_index,
        )
        if matched_sequence_identity is not None and sequence_identity != matched_sequence_identity:
            return None
        paint_context = matched_sequence.get("paint_context") if isinstance(matched_sequence.get("paint_context"), dict) else {}
        paint_context_operator = paint_context.get("paint_operator") if isinstance(paint_context.get("paint_operator"), dict) else {}
        if (
            not paint_context.get("exact")
            or str(paint_context_operator.get("operator") or "") != paint_operator
            or int(finite_number(paint_context_operator.get("operator_index"), -1)) != paint_index
            or int(finite_number(paint_context_operator.get("byte_offset"), -1)) != paint_offset
        ):
            return None
        span_start = int(finite_number(matched_sequence.get("first_byte_offset"), -1))
        span_end = paint_offset + len(paint_operator)
        if span_start < 0 or span_end <= span_start or pdf_content_span_has_unknown_operator(before_bytes, span_start, span_end):
            return None
        matched_sequence_identity = sequence_identity
        matched_paint_context = paint_context
        extgstate_names = list(paint_context.get("active_extgstate_resource_names") or [])
        extgstate_usages = [
            dict(value)
            for value in (paint_context.get("active_extgstate_usages") or [])
            if isinstance(value, dict)
        ]
        return matched_sequence, paint_context, paint_context_operator

    color_space_resources = color_space_resource_rows(
        doc,
        native_pdf_page_descriptor_id(page_number, int(finite_number(getattr(page, "xref", 0), 0))),
        context.get("invocation_index") if isinstance(context.get("invocation_index"), dict) else None,
    )
    for raw_patch in color_patches:
        patch = {**descriptor, **raw_patch}
        color_operator = str(patch.get("target_operator") or patch.get("operator") or "")
        color_index = int(finite_number(patch.get("target_operator_index"), -1))
        color_offset = int(finite_number(patch.get("target_operator_byte_offset"), -1))
        color_channel = str(patch.get("color_channel") or "").strip().lower()
        expected_channel = "fill" if color_operator.islower() else "stroke" if color_operator.isupper() else ""
        special_tint = str(patch.get("color_patch_kind") or "") == "special_tint"
        if special_tint:
            component_count = int(finite_number(patch.get("component_count"), 0))
            native_model = str(patch.get("native_color_model") or "")
            resource_name = str(patch.get("color_space_resource_name") or "")
            if (
                color_operator not in {"scn", "SCN"}
                or color_channel not in {"fill", "stroke"}
                or color_channel != expected_channel
                or native_model not in {"Separation", "DeviceN"}
                or component_count <= 0
                or bool(patch.get("localize_appearance_state"))
            ):
                return None
            if any(str(entry.get("color_channel") or "") == color_channel for entry in validated_color_patches):
                return None
            matched = matched_path_sequence(patch)
            if matched is None:
                return None
            _matched_sequence, paint_context, _paint_context_operator = matched
            channel_context = paint_context.get(color_channel) if isinstance(paint_context.get(color_channel), dict) else {}
            if (
                str(channel_context.get("operator") or "") != color_operator
                or int(finite_number(channel_context.get("semantic_use_count"), 0)) != 1
                or str(channel_context.get("source_origin") or "") not in {"explicit", "explicit-resource-color"}
                or int(finite_number(channel_context.get("operator_index"), -1)) != color_index
                or int(finite_number(channel_context.get("byte_offset"), -1)) != color_offset
                or str(channel_context.get("source_color_space_resource_name") or "") != resource_name
                or channel_context.get("preserve_only") is not True
            ):
                return None
            actual_source_components = pdf_unit_interval_components(channel_context.get("source_components"), component_count)
            expected_source_components = pdf_unit_interval_components(patch.get("source_components"), component_count)
            target_components = pdf_unit_interval_components(patch.get("target_components"), component_count)
            candidates = [
                resource
                for resource in color_space_resources
                if int(finite_number(resource.get("resource_owner_xref"), 0)) == selected_form_xref
                and str(resource.get("resource_name") or "") == resource_name
            ]
            resource = candidates[0] if len(candidates) == 1 else None
            if (
                actual_source_components is None
                or expected_source_components != actual_source_components
                or target_components is None
                or resource is None
                or resource.get("inspection_complete") is not True
                or resource.get("selected_use_tint_mutation_supported") is not True
                or str(resource.get("native_color_model") or "") != native_model
                or int(finite_number(resource.get("component_count"), 0)) != component_count
                or str(resource.get("id") or "") != str(patch.get("color_space_resource_id") or "")
                or str(resource.get("binding_id") or "") != str(patch.get("color_space_binding_id") or "")
                or str(resource.get("definition_sha256") or "") != str(patch.get("color_space_definition_sha256") or "")
                or str(resource.get("object_sha256") or "") != str(patch.get("color_space_object_sha256") or "")
                or str(resource.get("tint_transform_object_sha256") or "") != str(patch.get("tint_transform_object_sha256") or "")
                or str(resource.get("tint_transform_stream_sha256") or "") != str(patch.get("tint_transform_stream_sha256") or "")
                or str(resource.get("alternate_space") or "") != str(patch.get("alternate_space") or "")
                or int(finite_number(resource.get("alternate_space_xref"), 0)) != int(finite_number(patch.get("alternate_space_xref"), 0))
                or [str(value) for value in resource.get("colorant_names_raw") or []] != [str(value) for value in patch.get("colorant_names_raw") or []]
                or (native_model == "Separation" and (component_count != 1 or int(finite_number(resource.get("tint_transform_function_type"), 0)) != 2))
                or (
                    native_model == "DeviceN"
                    and (
                        component_count != len(resource.get("colorant_names") or [])
                        or int(finite_number(resource.get("tint_transform_function_type"), 0)) != 0
                        or int(finite_number((resource.get("tint_preview_contract") or {}).get("input_count"), 0)) != component_count
                    )
                )
            ):
                return None
            validated_color_patches.append({**patch, "validated_special_tint": True})
            continue
        color_space = PDF_DEVICE_COLOR_OPERATOR_SPACES.get(color_operator, "")
        component_count = PDF_DEVICE_COLOR_OPERATOR_COMPONENTS.get(color_operator, 0)
        if (
            color_channel not in {"fill", "stroke"}
            or color_channel != expected_channel
            or not color_space
            or component_count <= 0
        ):
            return None
        if any(str(entry.get("color_channel") or "") == color_channel for entry in validated_color_patches):
            return None
        matched = matched_path_sequence(patch)
        if matched is None:
            return None
        _matched_sequence, paint_context, _paint_context_operator = matched
        channel_context = paint_context.get(color_channel) if isinstance(paint_context.get(color_channel), dict) else {}
        localize = bool(patch.get("localize_appearance_state"))
        source_components = channel_context.get("source_components")
        source_color_space = str(channel_context.get("source_color_space") or "")
        actual_source_components = pdf_unit_interval_components(source_components, component_count)
        if (
            str(channel_context.get("operator") or "") != color_operator
            or source_color_space != color_space
            or actual_source_components is None
        ):
            return None
        if localize:
            if (
                paint_context.get("local_state_materialization_supported") is not True
                or (
                    str(channel_context.get("source_origin") or "") == "unresolved_inherited"
                    and selected.get("entry_default_appearance_proven") is not True
                )
            ):
                return None
        elif (
            channel_context.get("single_paint_sequence") is not True
            or int(finite_number(channel_context.get("operator_index"), -1)) != color_index
            or int(finite_number(channel_context.get("byte_offset"), -1)) != color_offset
        ):
            return None
        requested_source_space = str(patch.get("source_color_space") or color_space)
        requested_target_space = str(patch.get("target_color_space") or requested_source_space)
        if requested_source_space != color_space or requested_target_space != color_space:
            return None
        if color_space != "DeviceRGB" and (
            "source_color_space" not in raw_patch
            or "source_components" not in raw_patch
            or "target_color_space" not in raw_patch
            or "target_components" not in raw_patch
        ):
            return None
        requested_source_components = patch.get("source_components")
        if isinstance(requested_source_components, (list, tuple)):
            expected_source = pdf_unit_interval_components(requested_source_components, component_count)
            if expected_source is None:
                return None
            if actual_source_components != expected_source:
                return None
        elif color_space != "DeviceRGB":
            return None
        elif color_space == "DeviceRGB" and isinstance(patch.get("source_rgb"), (list, tuple)):
            expected_source = pdf_unit_interval_components(list(patch.get("source_rgb") or [])[:3], 3)
            if expected_source is None or actual_source_components != expected_source:
                return None
        if pdf_device_color_components_from_descriptor(patch, color_operator) is None:
            return None
        validated_color_patches.append(patch)

    for raw_patch in stroke_patches:
        patch = {**descriptor, **raw_patch}
        property_name = str(patch.get("stroke_property") or patch.get("property") or "").strip().lower()
        target_operator = str(patch.get("target_operator") or patch.get("operator") or "")
        target_index = int(finite_number(patch.get("target_operator_index"), -1))
        target_offset = int(finite_number(patch.get("target_operator_byte_offset"), -1))
        if PDF_STROKE_STYLE_OPERATOR_PROPERTIES.get(target_operator) != property_name:
            return None
        if any(str(entry.get("stroke_property") or "") == property_name for entry in validated_stroke_patches):
            return None
        matched = matched_path_sequence(patch)
        if matched is None:
            return None
        _matched_sequence, paint_context, paint_context_operator = matched
        if str(paint_context_operator.get("operator") or "") not in {"S", "s", "B", "B*", "b", "b*"}:
            return None
        stroke_style = paint_context.get("stroke_style") if isinstance(paint_context.get("stroke_style"), dict) else {}
        property_context = stroke_style.get(property_name) if isinstance(stroke_style.get(property_name), dict) else {}
        localize = bool(patch.get("localize_appearance_state"))
        if str(property_context.get("operator") or "") != target_operator:
            return None
        if localize:
            if (
                paint_context.get("local_state_materialization_supported") is not True
                or (
                    str(property_context.get("source_origin") or "") == "unresolved_inherited"
                    and selected.get("entry_default_appearance_proven") is not True
                )
                or selected_form_extgstate_overrides_stroke_property(
                    doc,
                    selected_form_xref,
                    extgstate_names,
                    property_name,
                )
            ):
                return None
        elif (
            property_context.get("single_paint_sequence") is not True
            or int(finite_number(property_context.get("operator_index"), -1)) != target_index
            or int(finite_number(property_context.get("byte_offset"), -1)) != target_offset
        ):
            return None
        if property_name == "dash":
            expected_array = [round(finite_number(value, 0), 4) for value in list(patch.get("source_dash_array") or [])[:24]]
            actual_array = [round(finite_number(value, 0), 4) for value in list(property_context.get("source_dash_array") or [])[:24]]
            if expected_array != actual_array or round(finite_number(patch.get("source_dash_phase"), 0), 4) != round(finite_number(property_context.get("source_dash_phase"), 0), 4):
                return None
        elif round(finite_number(patch.get("source_value"), 0), 4) != round(finite_number(property_context.get("source_value"), 0), 4):
            return None
        if property_name == "join" and int(finite_number(patch.get("target_value"), -1)) == 0:
            miter_limit = paint_context.get("miter_limit") if isinstance(paint_context.get("miter_limit"), dict) else {}
            if str(miter_limit.get("operator") or "") != "M" or finite_number(miter_limit.get("source_value"), 0) < 1:
                return None
        if extgstate_names and not localize:
            usage_names = {str(usage.get("resource_name") or "") for usage in extgstate_usages}
            last_extgstate_index = max(
                (int(finite_number(usage.get("operator_index"), -1)) for usage in extgstate_usages),
                default=-1,
            )
            if not set(str(value) for value in extgstate_names).issubset(usage_names) or target_index <= last_extgstate_index:
                return None
        validated_stroke_patches.append(patch)
    if matched_sequence_identity is None and matched_path_sequence(descriptor) is None:
        return None
    if stroke_patches:
        invocation_ctm = list(selected.get("page_ctm") or [])
        local_ctm = list((matched_paint_context or {}).get("local_ctm") or [1, 0, 0, 1, 0, 0])
        if len(invocation_ctm) < 6 or len(local_ctm) < 6:
            return None
        effective_ctm = pdf_matrix_multiply(invocation_ctm, local_ctm)
        if pdf_uniform_stroke_scale(effective_ctm) is None:
            return None
    if selected_form_paint_context_has_overprint(doc, selected_form_xref, extgstate_names):
        return None

    extgstate_clone = (
        clone_selected_form_extgstate_appearance_resource(doc, context, selected_form_xref, extgstate_patch)
        if extgstate_patch
        else None
    )
    if extgstate_patch and extgstate_clone is None:
        return None

    selected_clone_xref = clone_pdf_xref_object(doc, selected_form_xref)
    if selected_clone_xref <= 0:
        return None
    target_rewrites: list[dict[str, object]] = []
    for patch in validated_color_patches:
        if patch.get("localize_appearance_state"):
            continue
        cloned_descriptor = {
            **descriptor,
            **patch,
            "target_content_stream_xref": selected_clone_xref,
            "target_xobject_xref": selected_clone_xref,
            "target_content_stream_scope": "form-xobject-content-stream",
            "clone_and_rebind_shared_form": False,
        }
        target_rewrite = (
            rewrite_content_stream_special_color_operator_descriptor(doc, page, cloned_descriptor)
            if patch.get("validated_special_tint")
            else rewrite_content_stream_device_color_operator_descriptor(doc, page, cloned_descriptor)
        )
        if target_rewrite is None:
            return None
        target_rewrite["color_channel"] = patch.get("color_channel") or ""
        target_rewrites.append(target_rewrite)
    for patch in validated_stroke_patches:
        if patch.get("localize_appearance_state"):
            continue
        cloned_descriptor = {
            **descriptor,
            **patch,
            "target_content_stream_xref": selected_clone_xref,
            "target_xobject_xref": selected_clone_xref,
            "target_content_stream_scope": "form-xobject-content-stream",
            "target_operator_byte_offset": None,
            "clone_and_rebind_shared_form": False,
        }
        target_rewrite = rewrite_content_stream_stroke_style_operator_descriptor(doc, page, cloned_descriptor)
        if target_rewrite is None:
            return None
        target_rewrites.append(target_rewrite)
    localized_color_patches = [patch for patch in validated_color_patches if patch.get("localize_appearance_state")]
    localized_stroke_patches = [patch for patch in validated_stroke_patches if patch.get("localize_appearance_state")]
    if localized_color_patches or localized_stroke_patches:
        localized_descriptor = {
            **descriptor,
            "target_content_stream_xref": selected_clone_xref,
            "target_xobject_xref": selected_clone_xref,
            "target_content_stream_scope": "form-xobject-content-stream",
            "clone_and_rebind_shared_form": False,
        }
        local_rewrite = rewrite_content_stream_local_path_appearance_descriptor(
            doc,
            page,
            localized_descriptor,
            localized_color_patches,
            localized_stroke_patches,
        )
        if local_rewrite is None:
            return None
        target_rewrites.append(local_rewrite)
    resource_binding = None
    cloned_dictionary_xrefs: list[int] = []
    if extgstate_clone:
        resource_binding = set_isolated_pdf_resource_binding(
            doc,
            selected_clone_xref,
            "ExtGState",
            str(extgstate_clone.get("target_resource_name") or ""),
            int(finite_number(extgstate_clone.get("target_extgstate_xref"), 0)),
        )
        if resource_binding is None:
            return None
        cloned_dictionary_xrefs = [int(value) for value in resource_binding.get("cloned_dictionary_xrefs", [])]
    color_channels = [str(patch.get("color_channel") or "") for patch in validated_color_patches]
    color_spaces = [
        str(patch.get("native_color_model") or patch.get("target_color_space") or patch.get("source_color_space") or "")
        for patch in validated_color_patches
    ]
    stroke_properties = [str(patch.get("stroke_property") or "") for patch in validated_stroke_patches]
    chain_rebind = rebind_selected_form_clone_to_page(
        doc,
        context,
        selected_clone_xref,
        {
            "source_xref": selected_form_xref,
            "clone_xref": selected_clone_xref,
            "invocation_id": context["selected_invocation_id"],
            "selected_color_channels": color_channels,
            "selected_stroke_properties": stroke_properties,
            "selected_extgstate_resource_name": str(extgstate_clone.get("target_resource_name") or "") if extgstate_clone else "",
        },
        cloned_dictionary_xrefs,
    )
    if chain_rebind is None:
        return None
    return {
        "selected_invocation_id": context["selected_invocation_id"],
        "selected_invocation_path": selected.get("invocation_path") or "",
        "selected_nesting_depth": int(finite_number(selected.get("nesting_depth"), 0)),
        "source_target_form_xref": selected_form_xref,
        "target_form_xref": selected_clone_xref,
        "color_channel": "+".join(color_channels),
        "color_channels": color_channels,
        "color_spaces": color_spaces,
        "stroke_properties": stroke_properties,
        "source_stream_sha256": hashlib.sha256(before_bytes).hexdigest(),
        "target_rewrite": target_rewrites[0] if target_rewrites else None,
        "target_rewrites": target_rewrites,
        "selected_use_device_color_clone_rebind_applied": bool(device_color_patches),
        "selected_use_special_color_tint_clone_rebind_applied": bool(special_color_patches),
        "selected_use_rgb_color_clone_rebind_applied": any(space == "DeviceRGB" for space in color_spaces),
        "selected_use_stroke_geometry_clone_rebind_applied": bool(stroke_properties),
        "selected_use_local_state_materialization_applied": bool(localized_color_patches or localized_stroke_patches),
        "selected_use_extgstate_clone_rebind_applied": bool(extgstate_clone),
        "selected_use_appearance_stack_clone_rebind_applied": bool(extgstate_clone and (color_channels or stroke_properties)),
        "selected_form_resource_binding": resource_binding,
        "native_stream_mutated": bool(target_rewrites),
        "native_resource_mutated": bool(extgstate_clone),
        **(extgstate_clone or {}),
        **chain_rebind,
    }


def rewrite_selected_form_invocation_extgstate_descriptor(
    doc: object,
    page: object,
    page_number: int,
    descriptor: dict[str, object],
) -> dict[str, object] | None:
    context = selected_form_invocation_clone_context(doc, page, page_number, descriptor)
    if context is None:
        return None
    selected = context["selected"]
    selected_form_xref = int(finite_number(selected.get("form_xref"), 0))
    target_extgstate_xref = int(finite_number(descriptor.get("target_extgstate_xref") or descriptor.get("extgstate_xref"), 0))
    resource_name = str(descriptor.get("target_resource_name") or descriptor.get("resource_name") or "")
    owner_xref = int(finite_number(descriptor.get("target_resource_owner_xref") or descriptor.get("resource_owner_xref"), 0))
    binding_id = str(descriptor.get("target_resource_binding_id") or descriptor.get("resource_binding_id") or "")
    membership_id = str(descriptor.get("selected_extgstate_membership_id") or "")
    if (
        selected_form_xref <= 0
        or owner_xref != selected_form_xref
        or target_extgstate_xref <= 0
        or not resource_name
        or not binding_id
        or membership_id != binding_id
        or not pdf_resource_binding_isolatable(doc, selected_form_xref, "ExtGState")
    ):
        return None
    resolved_type, resolved_value = pdf_xref_key_payload(doc, selected_form_xref, f"Resources/ExtGState/{resource_name}")
    if pdf_reference_xref(resolved_type, resolved_value) != target_extgstate_xref:
        return None
    bindings = [
        binding
        for scope in context["invocation_index"].get("resource_scopes", [])
        if isinstance(scope, dict)
        for binding in scope.get("bindings", [])
        if isinstance(binding, dict)
    ]
    binding = next((
        row for row in bindings
        if str(row.get("id") or "") == binding_id
        and str(row.get("kind") or "") == "extgstate"
        and str(row.get("name") or "") == resource_name
        and int(finite_number(row.get("owner_xref"), 0)) == selected_form_xref
        and int(finite_number(row.get("target_xref"), 0)) == target_extgstate_xref
    ), None)
    if binding is None:
        return None
    usages = [
        row for row in context["invocation_index"].get("resource_usages", [])
        if isinstance(row, dict)
        and str(row.get("binding_id") or "") == binding_id
        and str(row.get("operator") or "") == "gs"
        and int(finite_number(row.get("owner_xref"), 0)) == selected_form_xref
    ]
    requested_usage_ids = {str(value) for value in descriptor.get("target_resource_usage_ids", []) if value}
    actual_usage_ids = {str(row.get("id") or "") for row in usages if row.get("id")}
    if not usages or (requested_usage_ids and not requested_usage_ids.issubset(actual_usage_ids)):
        return None

    cloned_extgstate_xref = clone_pdf_xref_object(doc, target_extgstate_xref)
    if cloned_extgstate_xref <= 0:
        return None
    cloned_descriptor = {**descriptor, "target_extgstate_xref": cloned_extgstate_xref}
    operation_kind = native_pdf_descriptor_operation_kind(descriptor)
    if operation_kind == "extgstate_appearance_rewrite":
        resource_rewrite = rewrite_extgstate_appearance_descriptor(doc, cloned_descriptor)
    elif operation_kind == "extgstate_blend_rewrite":
        resource_rewrite = rewrite_extgstate_blend_mode_descriptor(doc, cloned_descriptor)
    elif operation_kind == "extgstate_alpha_rewrite":
        resource_rewrite = rewrite_extgstate_opacity_descriptor(doc, cloned_descriptor)
    else:
        return None
    if resource_rewrite is None:
        return None

    selected_clone_xref = clone_pdf_xref_object(doc, selected_form_xref)
    if selected_clone_xref <= 0:
        return None
    resource_binding = set_isolated_pdf_resource_binding(
        doc,
        selected_clone_xref,
        "ExtGState",
        resource_name,
        cloned_extgstate_xref,
    )
    if resource_binding is None:
        return None
    chain_rebind = rebind_selected_form_clone_to_page(
        doc,
        context,
        selected_clone_xref,
        {
            "source_xref": selected_form_xref,
            "clone_xref": selected_clone_xref,
            "invocation_id": context["selected_invocation_id"],
            "selected_extgstate_resource_name": resource_name,
        },
        [int(value) for value in resource_binding.get("cloned_dictionary_xrefs", [])],
    )
    if chain_rebind is None:
        return None
    return {
        "selected_invocation_id": context["selected_invocation_id"],
        "selected_invocation_path": selected.get("invocation_path") or "",
        "selected_nesting_depth": int(finite_number(selected.get("nesting_depth"), 0)),
        "source_target_extgstate_xref": target_extgstate_xref,
        "target_extgstate_xref": cloned_extgstate_xref,
        "source_target_form_xref": selected_form_xref,
        "target_form_xref": selected_clone_xref,
        "target_resource_name": resource_name,
        "target_resource_binding_id": binding_id,
        "target_resource_usage_ids": sorted(actual_usage_ids),
        "resource_rewrite": resource_rewrite,
        "selected_form_resource_binding": resource_binding,
        "selected_use_extgstate_clone_rebind_applied": True,
        "native_resource_mutated": True,
        **chain_rebind,
    }


def pdf_color_array(value: object, fallback: str) -> list[float]:
    if isinstance(value, (list, tuple)):
        parts = [max(0.0, min(1.0, finite_number(part, 0))) for part in list(value)[:3]]
        if len(parts) == 3:
            return parts
    return list(hex_color_triplet(value, fallback))


def strict_pdf_rgb_color_array(value: object) -> list[float] | None:
    if isinstance(value, (list, tuple)) and len(value) == 3:
        channels: list[float] = []
        for raw_channel in value:
            try:
                channel = float(raw_channel)
            except (TypeError, ValueError):
                return None
            if not math.isfinite(channel) or channel < 0 or channel > 1:
                return None
            channels.append(channel)
        return channels
    text = str(value or "").strip()
    if not re.fullmatch(r"#[0-9a-fA-F]{6}", text):
        return None
    return [int(text[index:index + 2], 16) / 255 for index in (1, 3, 5)]


def pdf_number_arrays_match(left: object, right: object, tolerance: float = 0.000001) -> bool:
    if not isinstance(left, (list, tuple)) or not isinstance(right, (list, tuple)) or len(left) != len(right):
        return False
    return all(abs(finite_number(a, float("inf")) - finite_number(b, float("-inf"))) <= tolerance for a, b in zip(left, right))


def pdf_color_array_token(key: str, values: list[float]) -> str:
    numbers = " ".join(pdf_operator_number(max(0.0, min(1.0, value))) for value in values[:3])
    return f"/{key} [{numbers}]"


def pdf_number_array_token(key: str, values: list[float]) -> str:
    numbers = " ".join(pdf_operator_number(value) for value in values)
    return f"/{key} [{numbers}]"


def rewrite_pdf_array_after_key(source: str, key: str, values: list[float]) -> str:
    token = pdf_number_array_token(key, values)
    if re.search(rf"/{re.escape(key)}\s*\[[^\]]*\]", source, re.DOTALL):
        return re.sub(rf"/{re.escape(key)}\s*\[[^\]]*\]", token, source, count=1, flags=re.DOTALL)
    return re.sub(r">>\s*$", f"  {token}\n>>", source, count=1)


def rewrite_pdf_reference_array_after_key(source: str, key: str, xrefs: list[int]) -> str:
    token = f"/{key} [{' '.join(f'{int(xref)} 0 R' for xref in xrefs)}]"
    if re.search(rf"/{re.escape(key)}\s*\[[^\]]*\]", source, re.DOTALL):
        return re.sub(rf"/{re.escape(key)}\s*\[[^\]]*\]", token, source, count=1, flags=re.DOTALL)
    return re.sub(r">>\s*$", f"  {token}\n>>", source, count=1)


def strict_pdf_gradient_stops(value: object, expected_count: int = 0) -> list[dict[str, object]] | None:
    if not isinstance(value, (list, tuple)) or len(value) < 2 or len(value) > 17 or (expected_count and len(value) != expected_count):
        return None
    stops: list[dict[str, object]] = []
    for entry in value:
        if not isinstance(entry, dict):
            return None
        try:
            offset = float(entry.get("offset"))
        except (TypeError, ValueError):
            return None
        color = strict_pdf_rgb_color_array(entry.get("color") or entry.get("rgb"))
        if not math.isfinite(offset) or offset < 0 or offset > 1 or color is None:
            return None
        stops.append({"offset": offset, "color": color})
    if abs(float(stops[0]["offset"])) > 0.000001 or abs(float(stops[-1]["offset"]) - 1) > 0.000001:
        return None
    if any(float(stops[index]["offset"]) >= float(stops[index + 1]["offset"]) for index in range(len(stops) - 1)):
        return None
    return stops


def pdf_gradient_stops_match(left: object, right: object, tolerance: float = 0.000001) -> bool:
    if not isinstance(left, (list, tuple)) or not isinstance(right, (list, tuple)) or len(left) != len(right):
        return False
    for left_stop, right_stop in zip(left, right):
        if not isinstance(left_stop, dict) or not isinstance(right_stop, dict):
            return False
        if abs(finite_number(left_stop.get("offset"), -1) - finite_number(right_stop.get("offset"), -2)) > tolerance:
            return False
        left_color = strict_pdf_rgb_color_array(left_stop.get("color") or left_stop.get("rgb"))
        right_color = strict_pdf_rgb_color_array(right_stop.get("color") or right_stop.get("rgb"))
        if left_color is None or right_color is None or not pdf_number_arrays_match(left_color, right_color, tolerance):
            return False
    return True


def clone_and_rewrite_stitched_gradient_function(
    doc: object,
    source_contract: dict[str, object],
    target_stops: list[dict[str, object]],
    target_exponents: list[float],
) -> dict[str, object] | None:
    source_function_xref = int(finite_number(source_contract.get("function_xref"), 0))
    source_function_type = int(finite_number(source_contract.get("function_type"), 0))
    source_child_xrefs = [int(finite_number(value, 0)) for value in source_contract.get("child_xrefs", [])]
    source_templates = source_child_xrefs if source_function_type == 3 else [source_function_xref]
    if (
        source_function_xref <= 0
        or source_function_type not in {2, 3}
        or not source_templates
        or len(target_stops) < 2
        or len(target_stops) > 17
        or len(target_exponents) != len(target_stops) - 1
    ):
        return None
    parent_clone_xref = clone_pdf_xref_object(doc, source_function_xref)
    if parent_clone_xref <= 0:
        return None
    target_function_type = 2 if len(target_stops) == 2 else 3
    source_range = [float(value) for value in source_contract.get("range", [])]
    range_token = f"\n  {pdf_number_array_token('Range', source_range)}" if source_range else ""
    if target_function_type == 2:
        parent_source = (
            "<<\n"
            "  /FunctionType 2\n"
            "  /Domain [0 1]"
            f"{range_token}\n"
            f"  {pdf_color_array_token('C0', list(target_stops[0]['color']))}\n"
            f"  {pdf_color_array_token('C1', list(target_stops[1]['color']))}\n"
            f"  /N {pdf_operator_number(target_exponents[0])}\n"
            ">>"
        )
        doc.update_object(parent_clone_xref, parent_source)
        verified_contract = pdf_gradient_function_contract(doc, parent_clone_xref)
        if (
            verified_contract.get("supported") is not True
            or int(finite_number(verified_contract.get("function_type"), 0)) != 2
            or not pdf_gradient_stops_match(verified_contract.get("gradient_stops") or [], target_stops, 0.00011)
            or not pdf_number_arrays_match(verified_contract.get("segment_exponents") or [], target_exponents, 0.00011)
        ):
            return None
        return {
            "source_function_xref": source_function_xref,
            "target_function_xref": parent_clone_xref,
            "source_function_type": source_function_type,
            "target_function_type": 2,
            "source_child_xrefs": source_child_xrefs,
            "target_child_xrefs": [],
            "target_bounds": [],
            "target_gradient_stops": verified_contract.get("gradient_stops") or [],
            "target_segment_exponents": verified_contract.get("segment_exponents") or [],
            "child_rewrites": [],
            "before_object_sha256": source_contract.get("object_sha256") or "",
            "after_object_sha256": verified_contract.get("object_sha256") or "",
            "gradient_function_promoted": False,
            "gradient_function_demoted": source_function_type == 3,
            "native_resource_mutated": True,
        }
    child_clone_xrefs: list[int] = []
    child_rewrites: list[dict[str, object]] = []
    source_stops = source_contract.get("gradient_stops") or []
    for index in range(len(target_stops) - 1):
        segment_midpoint = (float(target_stops[index]["offset"]) + float(target_stops[index + 1]["offset"])) / 2
        template_index = 0
        if source_function_type == 3:
            template_index = next((
                source_index
                for source_index in range(len(source_stops) - 1)
                if float(source_stops[source_index]["offset"]) <= segment_midpoint <= float(source_stops[source_index + 1]["offset"])
            ), len(source_templates) - 1)
        source_child_xref = source_templates[min(template_index, len(source_templates) - 1)]
        source_child = pdf_xref_object_source(doc, source_child_xref)
        if (
            source_function_type == 3
            and len(target_stops) - 1 == len(source_templates)
            and pdf_number_arrays_match(parse_pdf_number_array_after_key(source_child, "C0"), target_stops[index]["color"], 0.00011)
            and pdf_number_arrays_match(parse_pdf_number_array_after_key(source_child, "C1"), target_stops[index + 1]["color"], 0.00011)
            and abs(finite_number(parse_pdf_scalar_after_key(source_child, "N"), -1) - target_exponents[index]) <= 0.00011
        ):
            source_hash = hashlib.sha256(source_child.encode("utf-8", errors="ignore")).hexdigest()
            child_clone_xrefs.append(source_child_xref)
            child_rewrites.append({
                "source_child_xref": source_child_xref,
                "target_child_xref": source_child_xref,
                "before_object_sha256": source_hash,
                "after_object_sha256": source_hash,
                "reused_unchanged_child": True,
            })
            continue
        child_clone_xref = clone_pdf_xref_object(doc, source_child_xref)
        if child_clone_xref <= 0:
            return None
        before_child = pdf_xref_object_source(doc, child_clone_xref)
        after_child = rewrite_pdf_array_after_key(before_child, "C0", list(target_stops[index]["color"]))
        after_child = rewrite_pdf_array_after_key(after_child, "C1", list(target_stops[index + 1]["color"]))
        after_child = upsert_pdf_dictionary_number(after_child, "N", target_exponents[index])
        if not after_child:
            return None
        if after_child != before_child:
            doc.update_object(child_clone_xref, after_child)
        verified_child = pdf_xref_object_source(doc, child_clone_xref)
        if (
            not pdf_number_arrays_match(parse_pdf_number_array_after_key(verified_child, "C0"), target_stops[index]["color"], 0.00011)
            or not pdf_number_arrays_match(parse_pdf_number_array_after_key(verified_child, "C1"), target_stops[index + 1]["color"], 0.00011)
            or abs(finite_number(parse_pdf_scalar_after_key(verified_child, "N"), -1) - target_exponents[index]) > 0.00011
        ):
            return None
        child_clone_xrefs.append(child_clone_xref)
        child_rewrites.append({
            "source_child_xref": source_child_xref,
            "target_child_xref": child_clone_xref,
            "before_object_sha256": hashlib.sha256(before_child.encode("utf-8", errors="ignore")).hexdigest(),
            "after_object_sha256": hashlib.sha256(verified_child.encode("utf-8", errors="ignore")).hexdigest(),
        })
    target_bounds = [float(stop["offset"]) for stop in target_stops[1:-1]]
    target_encode = [value for _xref in child_clone_xrefs for value in (0.0, 1.0)]
    parent_source = (
        "<<\n"
        "  /FunctionType 3\n"
        "  /Domain [0 1]"
        f"{range_token}\n"
        f"  /Functions [{' '.join(f'{xref} 0 R' for xref in child_clone_xrefs)}]\n"
        f"  {pdf_number_array_token('Bounds', target_bounds)}\n"
        f"  {pdf_number_array_token('Encode', target_encode)}\n"
        ">>"
    )
    doc.update_object(parent_clone_xref, parent_source)
    verified_contract = pdf_gradient_function_contract(doc, parent_clone_xref)
    if (
        verified_contract.get("supported") is not True
        or int(finite_number(verified_contract.get("function_type"), 0)) != 3
        or not pdf_gradient_stops_match(verified_contract.get("gradient_stops") or [], target_stops, 0.00011)
        or not pdf_number_arrays_match(verified_contract.get("segment_exponents") or [], target_exponents, 0.00011)
    ):
        return None
    return {
        "source_function_xref": source_function_xref,
        "target_function_xref": parent_clone_xref,
        "source_function_type": source_function_type,
        "target_function_type": 3,
        "source_child_xrefs": source_child_xrefs,
        "target_child_xrefs": child_clone_xrefs,
        "target_bounds": verified_contract.get("bounds") or [],
        "target_gradient_stops": verified_contract.get("gradient_stops") or [],
        "target_segment_exponents": verified_contract.get("segment_exponents") or [],
        "child_rewrites": child_rewrites,
        "before_object_sha256": source_contract.get("object_sha256") or "",
        "after_object_sha256": verified_contract.get("object_sha256") or "",
        "gradient_function_promoted": source_function_type == 2,
        "gradient_function_demoted": False,
        "native_resource_mutated": True,
    }


def rewrite_shading_function_colors_descriptor(doc: object, descriptor: dict[str, object]) -> dict[str, object] | None:
    function_xref = int(finite_number(descriptor.get("target_function_xref") or descriptor.get("function_xref"), 0))
    if function_xref <= 0:
        return None
    try:
        xref_limit = int(finite_number(doc.xref_length() if hasattr(doc, "xref_length") else 0, 0))
    except Exception:  # noqa: BLE001
        xref_limit = 0
    if function_xref >= xref_limit:
        return None
    try:
        before_object = str(doc.xref_object(function_xref, compressed=False) or "")
    except Exception:  # noqa: BLE001
        return None
    if int(finite_number(parse_pdf_scalar_after_key(before_object, "FunctionType"), 0)) != 2:
        return None
    before_c0 = parse_pdf_number_array_after_key(before_object, "C0")
    before_c1 = parse_pdf_number_array_after_key(before_object, "C1")
    target_c0 = pdf_color_array(descriptor.get("c0") or descriptor.get("start_color") or descriptor.get("startColor"), "#12b8a6")
    target_c1 = pdf_color_array(descriptor.get("c1") or descriptor.get("end_color") or descriptor.get("endColor"), "#ef4444")
    after_object = rewrite_pdf_array_after_key(before_object, "C0", target_c0)
    after_object = rewrite_pdf_array_after_key(after_object, "C1", target_c1)
    exponent = descriptor.get("exponent")
    if exponent is None:
        exponent = descriptor.get("function_exponent")
    if exponent is not None:
        after_object = upsert_pdf_dictionary_number(after_object, "N", max(0.01, finite_number(exponent, 1)))
    if after_object == before_object:
        return None
    doc.update_object(function_xref, after_object)
    try:
        verified_object = str(doc.xref_object(function_xref, compressed=False) or "")
    except Exception:  # noqa: BLE001
        verified_object = after_object
    return {
        "target_shading_xref": int(finite_number(descriptor.get("target_shading_xref") or descriptor.get("shading_xref"), 0)),
        "target_function_xref": function_xref,
        "resource_name": descriptor.get("target_resource_name") or descriptor.get("resource_name") or "",
        "before_c0": before_c0,
        "before_c1": before_c1,
        "after_c0": parse_pdf_number_array_after_key(verified_object, "C0"),
        "after_c1": parse_pdf_number_array_after_key(verified_object, "C1"),
        "requested_c0": target_c0,
        "requested_c1": target_c1,
        "before_object_sha256": hashlib.sha256(before_object.encode("utf-8", errors="ignore")).hexdigest(),
        "after_object_sha256": hashlib.sha256(verified_object.encode("utf-8", errors="ignore")).hexdigest(),
        "native_resource_mutated": True,
    }


def rewrite_selected_form_invocation_gradient_descriptor(
    doc: object,
    page: object,
    page_number: int,
    descriptor: dict[str, object],
) -> dict[str, object] | None:
    context = selected_form_invocation_clone_context(doc, page, page_number, descriptor)
    if context is None:
        return None
    selected = context["selected"]
    selected_form_xref = int(finite_number(selected.get("form_xref"), 0))
    shading_xref = int(finite_number(descriptor.get("target_shading_xref") or descriptor.get("shading_xref"), 0))
    function_xref = int(finite_number(descriptor.get("target_function_xref") or descriptor.get("function_xref"), 0))
    owner_xref = int(finite_number(descriptor.get("target_resource_owner_xref") or descriptor.get("resource_owner_xref"), 0))
    resource_name = str(descriptor.get("target_resource_name") or descriptor.get("resource_name") or "").strip().lstrip("/")
    binding_id = str(descriptor.get("target_resource_binding_id") or descriptor.get("resource_binding_id") or "")
    if (
        selected_form_xref <= 0
        or selected_form_xref != owner_xref
        or shading_xref <= 0
        or function_xref <= 0
        or not resource_name
        or not binding_id
        or str(descriptor.get("native_write_scope") or "") != "selected-form-invocation-gradient-clone"
        or not pdf_resource_binding_isolatable(doc, selected_form_xref, "Shading")
        or any(
            selected_form_has_transparency_group(doc, int(finite_number(row.get("form_xref"), 0)))
            for row in context.get("chain", [])
            if isinstance(row, dict)
        )
    ):
        return None

    resolved_type, resolved_value = pdf_xref_key_payload(doc, selected_form_xref, f"Resources/Shading/{resource_name}")
    if pdf_reference_xref(resolved_type, resolved_value) != shading_xref:
        return None
    bindings = [
        binding
        for scope in context["invocation_index"].get("resource_scopes", [])
        if isinstance(scope, dict)
        for binding in scope.get("bindings", [])
        if isinstance(binding, dict)
    ]
    binding = next((
        row for row in bindings
        if str(row.get("id") or "") == binding_id
        and str(row.get("kind") or "") == "shading"
        and str(row.get("name") or "") == resource_name
        and int(finite_number(row.get("owner_xref"), 0)) == selected_form_xref
        and int(finite_number(row.get("target_xref"), 0)) == shading_xref
    ), None)
    if binding is None:
        return None
    usages = [
        row for row in context["invocation_index"].get("resource_usages", [])
        if isinstance(row, dict)
        and str(row.get("binding_id") or "") == binding_id
        and str(row.get("operator") or "") == "sh"
        and str(row.get("owner_invocation_id") or "") == str(context["selected_invocation_id"])
        and int(finite_number(row.get("owner_xref"), 0)) == selected_form_xref
    ]
    if len(usages) != 1:
        return None
    usage = usages[0]
    actual_usage_ids = {str(usage.get("id") or "")}
    requested_usage_ids = {str(value) for value in descriptor.get("target_resource_usage_ids", []) if value}
    requested_usage_id = str(descriptor.get("target_shading_usage_id") or "")
    expected_operator_index = int(finite_number(descriptor.get("target_shading_operator_index"), -1))
    expected_byte_offset = int(finite_number(descriptor.get("target_shading_operator_byte_offset"), -1))
    stream_xref = int(finite_number(usage.get("stream_xref"), 0))
    operator_index = int(finite_number(usage.get("operator_index"), -1))
    byte_offset = int(finite_number(usage.get("byte_offset"), -1))
    if (
        not requested_usage_ids
        or requested_usage_ids != actual_usage_ids
        or requested_usage_id not in actual_usage_ids
        or expected_operator_index != operator_index
        or expected_byte_offset != byte_offset
        or stream_xref != selected_form_xref
        or not pdf_sh_resource_name_matches(doc, stream_xref, byte_offset, resource_name)
    ):
        return None

    extgstate_names = [
        row.get("resource_name")
        for row in context["invocation_index"].get("resource_usages", [])
        if isinstance(row, dict)
        and str(row.get("owner_invocation_id") or "") == str(context["selected_invocation_id"])
        and int(finite_number(row.get("owner_xref"), 0)) == selected_form_xref
        and str(row.get("operator") or "") == "gs"
    ]
    if selected_form_paint_context_has_overprint(doc, selected_form_xref, extgstate_names):
        return None

    source_form_bytes = pdf_xref_stream_bytes(doc, selected_form_xref)
    source_shading = pdf_xref_object_source(doc, shading_xref)
    source_function = pdf_xref_object_source(doc, function_xref)
    if not source_form_bytes or not source_shading or not source_function:
        return None
    source_form_sha256 = hashlib.sha256(source_form_bytes).hexdigest()
    source_shading_sha256 = hashlib.sha256(source_shading.encode("utf-8", errors="ignore")).hexdigest()
    source_function_sha256 = hashlib.sha256(source_function.encode("utf-8", errors="ignore")).hexdigest()
    if (
        source_form_sha256 != str(descriptor.get("source_form_stream_sha256") or "")
        or source_shading_sha256 != str(descriptor.get("source_shading_object_sha256") or "")
        or source_function_sha256 != str(descriptor.get("source_function_object_sha256") or "")
    ):
        return None

    shading_type = int(finite_number(parse_pdf_scalar_after_key(source_shading, "ShadingType"), 0))
    source_function_contract = pdf_gradient_function_contract(doc, function_xref)
    function_type = int(finite_number(source_function_contract.get("function_type"), 0))
    coords = parse_pdf_number_array_after_key(source_shading, "Coords")
    shading_domain = parse_pdf_number_array_after_key(source_shading, "Domain") or [0.0, 1.0]
    extend = parse_pdf_boolean_array_after_key(source_shading, "Extend") or [False, False]
    function_domain = source_function_contract.get("domain") or []
    source_c0 = parse_pdf_number_array_after_key(source_function, "C0")
    source_c1 = parse_pdf_number_array_after_key(source_function, "C1")
    source_exponent = parse_pdf_scalar_after_key(source_function, "N")
    source_stops = source_function_contract.get("gradient_stops") or []
    source_segment_exponents = source_function_contract.get("segment_exponents") or []
    source_child_xrefs = [int(finite_number(value, 0)) for value in source_function_contract.get("child_xrefs", [])]
    source_child_hashes = [str(value or "") for value in source_function_contract.get("child_object_sha256", [])]
    source_child_objects = [pdf_xref_object_source(doc, xref) for xref in source_child_xrefs]
    function_ref_type, function_ref_value = pdf_xref_key_payload(doc, shading_xref, "Function")
    colorspace_type, colorspace_value = pdf_xref_key_payload(doc, shading_xref, "ColorSpace")
    coordinate_count = 4 if shading_type == 2 else 6 if shading_type == 3 else 0
    valid_geometry = bool(
        coordinate_count
        and len(coords) == coordinate_count
        and all(math.isfinite(value) for value in coords)
        and (
            (shading_type == 2 and (abs(coords[2] - coords[0]) > 0.000001 or abs(coords[3] - coords[1]) > 0.000001))
            or (shading_type == 3 and coords[2] >= 0 and coords[5] >= 0 and (abs(coords[5] - coords[2]) > 0.000001 or abs(coords[3] - coords[0]) > 0.000001 or abs(coords[4] - coords[1]) > 0.000001))
        )
    )
    type2_source_matches = bool(
        function_type == 2
        and pdf_number_arrays_match(source_c0, descriptor.get("source_c0") or [])
        and pdf_number_arrays_match(source_c1, descriptor.get("source_c1") or [])
        and source_exponent is not None
        and abs(source_exponent - finite_number(descriptor.get("source_exponent"), -1)) <= 0.000001
    )
    type3_source_matches = bool(
        function_type == 3
        and source_child_xrefs == [int(finite_number(value, 0)) for value in descriptor.get("source_function_child_xrefs", [])]
        and source_child_hashes == [str(value or "") for value in descriptor.get("source_function_child_object_sha256", [])]
        and pdf_number_arrays_match(source_function_contract.get("bounds") or [], descriptor.get("source_function_bounds") or [])
        and pdf_number_arrays_match(source_function_contract.get("encode") or [], descriptor.get("source_function_encode") or [])
        and pdf_gradient_stops_match(source_stops, descriptor.get("source_gradient_stops") or [])
        and pdf_number_arrays_match(source_segment_exponents, descriptor.get("source_segment_exponents") or [])
    )
    if (
        shading_type not in {2, 3}
        or int(finite_number(descriptor.get("shading_type"), 0)) != shading_type
        or function_type not in {2, 3}
        or int(finite_number(descriptor.get("function_type"), 0)) != function_type
        or source_function_contract.get("supported") is not True
        or pdf_reference_xref(function_ref_type, function_ref_value) != function_xref
        or colorspace_type != "name"
        or str(colorspace_value or "").strip() != "/DeviceRGB"
        or not valid_geometry
        or not pdf_number_arrays_match(function_domain, [0.0, 1.0])
        or not pdf_number_arrays_match(shading_domain, descriptor.get("source_domain") or [0.0, 1.0])
        or list(extend) != list(descriptor.get("source_extend") or [False, False])
        or not pdf_number_arrays_match(coords, descriptor.get("source_coords") or [])
        or not (type2_source_matches or type3_source_matches)
    ):
        return None
    requested_coords = descriptor.get("target_coords")
    if requested_coords is None:
        requested_coords = descriptor.get("coords")
    if requested_coords is None:
        requested_coords = coords
    if not isinstance(requested_coords, (list, tuple)) or len(requested_coords) != coordinate_count:
        return None
    try:
        target_coords = [float(value) for value in requested_coords]
    except (TypeError, ValueError):
        return None
    valid_target_geometry = bool(
        all(math.isfinite(value) and abs(value) <= 10_000_000 for value in target_coords)
        and (
            (shading_type == 2 and (abs(target_coords[2] - target_coords[0]) > 0.000001 or abs(target_coords[3] - target_coords[1]) > 0.000001))
            or (
                shading_type == 3
                and target_coords[2] >= 0
                and target_coords[5] >= 0
                and (
                    abs(target_coords[5] - target_coords[2]) > 0.000001
                    or abs(target_coords[3] - target_coords[0]) > 0.000001
                    or abs(target_coords[4] - target_coords[1]) > 0.000001
                )
            )
        )
    )
    if not valid_target_geometry:
        return None

    target_stops = strict_pdf_gradient_stops(descriptor.get("gradient_stops"))
    raw_exponents = descriptor.get("segment_exponents")
    if target_stops is not None:
        if not isinstance(raw_exponents, (list, tuple)) or len(raw_exponents) != len(target_stops) - 1:
            return None
        try:
            target_segment_exponents = [float(value) for value in raw_exponents]
        except (TypeError, ValueError):
            return None
        if any(not math.isfinite(value) or value <= 0 or value > 10000 for value in target_segment_exponents):
            return None
    elif function_type == 2:
        target_c0 = strict_pdf_rgb_color_array(descriptor.get("c0") or descriptor.get("start_color") or descriptor.get("startColor")) or []
        target_c1 = strict_pdf_rgb_color_array(descriptor.get("c1") or descriptor.get("end_color") or descriptor.get("endColor")) or []
        try:
            target_exponent = float(descriptor.get("exponent"))
        except (TypeError, ValueError):
            return None
        if len(target_c0) != 3 or len(target_c1) != 3 or not math.isfinite(target_exponent) or target_exponent <= 0:
            return None
        target_stops = [
            {"offset": 0.0, "color": target_c0},
            {"offset": 1.0, "color": target_c1},
        ]
        target_segment_exponents = [target_exponent]
    else:
        return None
    target_c0 = list(target_stops[0]["color"])
    target_c1 = list(target_stops[-1]["color"])
    target_exponent = float(target_segment_exponents[0])
    function_changed = bool(
        not pdf_gradient_stops_match(source_stops, target_stops)
        or not pdf_number_arrays_match(source_segment_exponents, target_segment_exponents)
    )
    function_clone_xref = function_xref
    function_rewrite = None
    if function_changed:
        if function_type == 2 and len(target_stops) == 2:
            function_clone_xref = clone_pdf_xref_object(doc, function_xref)
            if function_clone_xref <= 0:
                return None
            function_rewrite = rewrite_shading_function_colors_descriptor(doc, {
                **descriptor,
                "target_function_xref": function_clone_xref,
                "c0": target_c0,
                "c1": target_c1,
                "exponent": target_exponent,
            })
        else:
            function_rewrite = clone_and_rewrite_stitched_gradient_function(
                doc,
                source_function_contract,
                target_stops,
                target_segment_exponents,
            )
            function_clone_xref = int(finite_number(function_rewrite.get("target_function_xref") if function_rewrite else 0, 0))
        if function_rewrite is None:
            return None
    shading_clone_xref = clone_pdf_xref_object(doc, shading_xref)
    if shading_clone_xref <= 0:
        return None
    if function_changed:
        doc.xref_set_key(shading_clone_xref, "Function", f"{function_clone_xref} 0 R")
    clone_function_type, clone_function_value = pdf_xref_key_payload(doc, shading_clone_xref, "Function")
    if pdf_reference_xref(clone_function_type, clone_function_value) != function_clone_xref:
        return None
    geometry_changed = not pdf_number_arrays_match(coords, target_coords)
    if geometry_changed:
        clone_shading_source = pdf_xref_object_source(doc, shading_clone_xref)
        rewritten_shading_source = rewrite_pdf_array_after_key(clone_shading_source, "Coords", target_coords)
        if not rewritten_shading_source or rewritten_shading_source == clone_shading_source:
            return None
        doc.update_object(shading_clone_xref, rewritten_shading_source)
    verified_clone_shading = pdf_xref_object_source(doc, shading_clone_xref)
    verified_clone_coords = parse_pdf_number_array_after_key(verified_clone_shading, "Coords")
    if not pdf_number_arrays_match(verified_clone_coords, target_coords):
        return None

    selected_clone_xref = clone_pdf_xref_object(doc, selected_form_xref)
    if selected_clone_xref <= 0:
        return None
    resource_binding = set_isolated_pdf_resource_binding(
        doc,
        selected_clone_xref,
        "Shading",
        resource_name,
        shading_clone_xref,
    )
    if resource_binding is None:
        return None
    chain_rebind = rebind_selected_form_clone_to_page(
        doc,
        context,
        selected_clone_xref,
        {
            "source_xref": selected_form_xref,
            "clone_xref": selected_clone_xref,
            "invocation_id": context["selected_invocation_id"],
            "selected_shading_resource_name": resource_name,
            "source_shading_xref": shading_xref,
            "target_shading_xref": shading_clone_xref,
            "source_function_xref": function_xref,
            "target_function_xref": function_clone_xref,
        },
        [int(value) for value in resource_binding.get("cloned_dictionary_xrefs", [])],
    )
    if chain_rebind is None:
        return None
    if (
        pdf_xref_stream_bytes(doc, selected_form_xref) != source_form_bytes
        or pdf_xref_object_source(doc, shading_xref) != source_shading
        or pdf_xref_object_source(doc, function_xref) != source_function
        or any(pdf_xref_object_source(doc, xref) != source for xref, source in zip(source_child_xrefs, source_child_objects))
    ):
        return None
    return {
        "selected_invocation_id": context["selected_invocation_id"],
        "selected_invocation_path": selected.get("invocation_path") or "",
        "selected_nesting_depth": int(finite_number(selected.get("nesting_depth"), 0)),
        "source_target_form_xref": selected_form_xref,
        "target_form_xref": selected_clone_xref,
        "source_target_shading_xref": shading_xref,
        "target_shading_xref": shading_clone_xref,
        "source_target_function_xref": function_xref,
        "target_function_xref": function_clone_xref,
        "target_resource_name": resource_name,
        "target_resource_binding_id": binding_id,
        "target_resource_usage_ids": sorted(actual_usage_ids),
        "source_form_stream_sha256": source_form_sha256,
        "source_shading_object_sha256": source_shading_sha256,
        "source_function_object_sha256": source_function_sha256,
        "source_function_child_xrefs": source_child_xrefs,
        "target_function_child_xrefs": function_rewrite.get("target_child_xrefs", []) if isinstance(function_rewrite, dict) else [],
        "function_rewrite": function_rewrite,
        "source_gradient_stops": source_stops,
        "target_gradient_stops": target_stops,
        "source_segment_exponents": source_segment_exponents,
        "target_segment_exponents": target_segment_exponents,
        "source_coords": coords,
        "target_coords": verified_clone_coords,
        "selected_form_resource_binding": resource_binding,
        "selected_use_gradient_clone_rebind_applied": True,
        "shading_resource_clone_applied": True,
        "function_resource_clone_applied": function_changed,
        "stitched_gradient_function_rewrite_applied": bool(function_changed and (function_type == 3 or len(target_stops) > 2)),
        "gradient_function_promoted": bool(function_rewrite and function_rewrite.get("gradient_function_promoted")),
        "gradient_function_demoted": bool(function_rewrite and function_rewrite.get("gradient_function_demoted")),
        "gradient_stop_count_rewrite_applied": bool(function_changed and len(source_stops) != len(target_stops)),
        "gradient_geometry_rewrite_applied": geometry_changed,
        "native_resource_mutated": True,
        **chain_rebind,
    }


def rewrite_shading_background_color_descriptor(doc: object, descriptor: dict[str, object]) -> dict[str, object] | None:
    shading_xref = int(finite_number(descriptor.get("target_shading_xref") or descriptor.get("shading_xref"), 0))
    if shading_xref <= 0:
        return None
    try:
        xref_limit = int(finite_number(doc.xref_length() if hasattr(doc, "xref_length") else 0, 0))
    except Exception:  # noqa: BLE001
        xref_limit = 0
    if shading_xref >= xref_limit:
        return None
    try:
        before_object = str(doc.xref_object(shading_xref, compressed=False) or "")
    except Exception:  # noqa: BLE001
        return None
    if "/ShadingType" not in before_object:
        return None
    before_background = parse_pdf_number_array_after_key(before_object, "Background")
    target_background = pdf_color_array(
        descriptor.get("background_color")
        or descriptor.get("target_background")
        or descriptor.get("color")
        or descriptor.get("target_color"),
        "#f59e0b",
    )
    after_object = rewrite_pdf_array_after_key(before_object, "Background", target_background)
    if after_object == before_object:
        return None
    doc.update_object(shading_xref, after_object)
    try:
        verified_object = str(doc.xref_object(shading_xref, compressed=False) or "")
    except Exception:  # noqa: BLE001
        verified_object = after_object
    return {
        "target_shading_xref": shading_xref,
        "resource_name": descriptor.get("target_resource_name") or descriptor.get("resource_name") or "",
        "shading_type": int(finite_number(parse_pdf_scalar_after_key(verified_object, "ShadingType"), 0)),
        "before_background": before_background,
        "after_background": parse_pdf_number_array_after_key(verified_object, "Background"),
        "requested_background": target_background,
        "before_object_sha256": hashlib.sha256(before_object.encode("utf-8", errors="ignore")).hexdigest(),
        "after_object_sha256": hashlib.sha256(verified_object.encode("utf-8", errors="ignore")).hexdigest(),
        "native_resource_mutated": True,
    }


def pdf_rgb_color_operator_bytes(values: list[float], operator: str) -> bytes:
    numbers = " ".join(pdf_operator_number(max(0.0, min(1.0, value))) for value in values[:3])
    return f"{numbers} {operator}".encode("ascii")


def rewrite_tiling_pattern_stream_colors_descriptor(doc: object, descriptor: dict[str, object]) -> dict[str, object] | None:
    pattern_xref = int(finite_number(descriptor.get("target_pattern_xref") or descriptor.get("pattern_xref"), 0))
    if pattern_xref <= 0:
        return None
    try:
        xref_limit = int(finite_number(doc.xref_length() if hasattr(doc, "xref_length") else 0, 0))
    except Exception:  # noqa: BLE001
        xref_limit = 0
    if pattern_xref >= xref_limit:
        return None
    try:
        before_object = str(doc.xref_object(pattern_xref, compressed=False) or "")
    except Exception:  # noqa: BLE001
        return None
    if int(finite_number(parse_pdf_scalar_after_key(before_object, "PatternType"), 0)) != 1:
        return None
    if int(finite_number(parse_pdf_scalar_after_key(before_object, "PaintType"), 0)) != 1:
        return None
    before_bytes = pdf_xref_stream_bytes(doc, pattern_xref)
    if not before_bytes:
        return None
    fill_rgb = pdf_color_array(descriptor.get("fill_color") or descriptor.get("color") or descriptor.get("target_color"), "#22c55e")
    stroke_rgb = pdf_color_array(descriptor.get("stroke_color") or descriptor.get("color") or descriptor.get("target_color"), "#22c55e")
    number = rb"[-+]?(?:\d*\.\d+|\d+\.?)(?:[Ee][-+]?\d+)?"
    rgb_pattern = re.compile(number + rb"\s+" + number + rb"\s+" + number + rb"\s+(rg|RG)(?![A-Za-z0-9_])")
    replacements = {"rg": 0, "RG": 0}

    def replace_match(match: re.Match[bytes]) -> bytes:
        operator = match.group(1).decode("ascii", errors="ignore")
        replacements[operator] = replacements.get(operator, 0) + 1
        return pdf_rgb_color_operator_bytes(stroke_rgb if operator == "RG" else fill_rgb, operator)

    after_bytes = rgb_pattern.sub(replace_match, before_bytes)
    inserted_color_prefix = False
    if after_bytes == before_bytes:
        after_bytes = (
            pdf_rgb_color_operator_bytes(fill_rgb, "rg")
            + b"\n"
            + pdf_rgb_color_operator_bytes(stroke_rgb, "RG")
            + b"\n"
            + before_bytes
        )
        inserted_color_prefix = True
    if after_bytes == before_bytes:
        return None
    update_pdf_stream(doc, pattern_xref, after_bytes)
    verified_bytes = pdf_xref_stream_bytes(doc, pattern_xref)
    return {
        "target_pattern_xref": pattern_xref,
        "resource_name": descriptor.get("target_resource_name") or descriptor.get("resource_name") or "",
        "pattern_type": 1,
        "paint_type": 1,
        "before_byte_size": len(before_bytes),
        "after_byte_size": len(verified_bytes),
        "before_sha256": hashlib.sha256(before_bytes).hexdigest(),
        "after_sha256": hashlib.sha256(verified_bytes).hexdigest() if verified_bytes else "",
        "rewritten_fill_color_operator_count": replacements.get("rg", 0),
        "rewritten_stroke_color_operator_count": replacements.get("RG", 0),
        "inserted_color_prefix": inserted_color_prefix,
        "requested_fill_rgb": fill_rgb,
        "requested_stroke_rgb": stroke_rgb,
        "native_stream_mutated": bool(verified_bytes and verified_bytes != before_bytes),
    }


def draw_path_descriptor(fitz_module, page: object, descriptor: dict[str, object]) -> dict[str, object] | None:
    commands, origin = path_commands_from_descriptor(descriptor)
    if not commands:
        return None
    shape = page.new_shape()
    current = None
    subpath_start = None
    segment_count = 0
    closed = False
    for command in commands:
        operator = str(command[0]).upper()
        if operator == "M":
            point = path_point_from_source_space(fitz_module, page, command[1:3], origin)
            if point is None:
                continue
            current = point
            subpath_start = point
            continue
        if operator == "L":
            point = path_point_from_source_space(fitz_module, page, command[1:3], origin)
            if point is None:
                continue
            if current is None:
                current = point
                subpath_start = point
                continue
            shape.draw_line(current, point)
            current = point
            segment_count += 1
            continue
        if operator == "C":
            c1 = path_point_from_source_space(fitz_module, page, command[1:3], origin)
            c2 = path_point_from_source_space(fitz_module, page, command[3:5], origin)
            end = path_point_from_source_space(fitz_module, page, command[5:7], origin)
            if c1 is None or c2 is None or end is None:
                continue
            if current is None:
                current = end
                subpath_start = end
                continue
            shape.draw_bezier(current, c1, c2, end)
            current = end
            segment_count += 1
            continue
        if operator == "Q":
            control = path_point_from_source_space(fitz_module, page, command[1:3], origin)
            end = path_point_from_source_space(fitz_module, page, command[3:5], origin)
            if control is None or end is None:
                continue
            if current is None:
                current = end
                subpath_start = end
                continue
            c1 = fitz_module.Point(
                current.x + (2 / 3) * (control.x - current.x),
                current.y + (2 / 3) * (control.y - current.y),
            )
            c2 = fitz_module.Point(
                end.x + (2 / 3) * (control.x - end.x),
                end.y + (2 / 3) * (control.y - end.y),
            )
            shape.draw_bezier(current, c1, c2, end)
            current = end
            segment_count += 1
            continue
        if operator == "Z" and current is not None and subpath_start is not None:
            shape.draw_line(current, subpath_start)
            current = subpath_start
            closed = True
            segment_count += 1
    if segment_count <= 0:
        return None
    style = descriptor.get("style") if isinstance(descriptor.get("style"), dict) else {}
    fill_value = style.get("fill") if isinstance(style, dict) else None
    fill = None if not fill_value or str(fill_value).lower() in {"none", "transparent"} else hex_color_triplet(fill_value, "#28e2cf")
    stroke = hex_color_triplet(style.get("stroke") if isinstance(style, dict) else "#111820", "#111820")
    shape.finish(
        width=max(0.25, finite_number(style.get("stroke_width") if isinstance(style, dict) else 1.5, 1.5)),
        color=stroke,
        fill=fill,
        even_odd=str(descriptor.get("fill_rule") or style.get("fill_rule") or "").lower() == "evenodd",
        closePath=False,
        fill_opacity=max(0.0, min(1.0, finite_number(style.get("fill_opacity") if isinstance(style, dict) else 0.24, 0.24))),
        stroke_opacity=max(0.0, min(1.0, finite_number(style.get("opacity") if isinstance(style, dict) else 0.92, 0.92))),
    )
    shape.commit(overlay=True)
    return {
        "command_count": len(commands),
        "segment_count": segment_count,
        "closed": closed,
        "origin": origin,
    }


def roundtrip_pdf_noop(pdf_bytes: bytes, filename: str) -> dict[str, object]:
    import pikepdf

    doc = PikePdfDocument.open(pdf_bytes)
    try:
        before_xref_length = int(finite_number(doc.xref_length(), 0))
        before_pages = [
            {
                "page_number": page_index + 1,
                "page_xref": int(finite_number(getattr(doc[page_index], "xref", 0), 0)),
                "content_xrefs": page_content_xrefs(doc[page_index]),
                "editable_content_stream_xrefs": editable_pdf_content_stream_xrefs(doc, doc[page_index]),
            }
            for page_index in range(doc.page_count)
        ]
        output_bytes = doc.write()
    finally:
        doc.close()

    after_doc = PikePdfDocument.open(output_bytes)
    try:
        after_xref_length = int(finite_number(after_doc.xref_length(), 0))
        after_pages = [
            {
                "page_number": page_index + 1,
                "page_xref": int(finite_number(getattr(after_doc[page_index], "xref", 0), 0)),
                "content_xrefs": page_content_xrefs(after_doc[page_index]),
                "editable_content_stream_xrefs": editable_pdf_content_stream_xrefs(after_doc, after_doc[page_index]),
            }
            for page_index in range(after_doc.page_count)
        ]
    finally:
        after_doc.close()

    return {
        "ok": True,
        "schema": "figureStudio.nativePdfNoopRoundtripResult.v1",
        "source_pdf_filename": filename or "uploaded.pdf",
        "roundtrip_engine": {
            "name": "pikepdf",
            "version": str(getattr(pikepdf, "__version__", "")),
            "library": "QPDF",
            "operation": "parse-and-reserialize-noop",
        },
        "operation_matrix": native_pdf_content_stream_operation_matrix(),
        "roundtrip": {
            "status": "source-pdf-parsed-and-reserialized",
            "page_count": len(before_pages),
            "before_xref_length": before_xref_length,
            "after_xref_length": after_xref_length,
            "before_pages": before_pages,
            "after_pages": after_pages,
            "content_stream_mutated": False,
            "native_noop_roundtrip_available": True,
            "native_equivalent_pdf_output_available": False,
            "full_native_equivalence": False,
            "visual_diff_required": True,
        },
        "pdfBase64": base64.b64encode(output_bytes).decode("ascii"),
        "output_pdf_byte_size": len(output_bytes),
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }


def compile_native_pdf_packet(pdf_bytes: bytes, filename: str, packet: dict[str, object]) -> dict[str, object]:
    if packet.get("schema") == "figureStudio.nativePdfTypedTransactionPacket.v1":
        from pdf_native.compiler import compile_typed_pdf_transactions

        return compile_typed_pdf_transactions(pdf_bytes, filename, packet)

    descriptors = native_edit_descriptors_from_packet(packet)
    appendable_descriptors = [
        descriptor
        for descriptor in descriptors
        if native_pdf_descriptor_operation_kind(descriptor)
    ]
    robust_boolean_descriptor_count = sum(
        1
        for descriptor in appendable_descriptors
        if str(descriptor.get("descriptor_type") or "") == "path_boolean_operation"
        and bool(descriptor.get("robust_geometry_engine") or descriptor.get("robust_boolean_geometry_applied"))
    )
    object_tree_rewrite_descriptor_count = sum(
        1
        for descriptor in appendable_descriptors
        if native_pdf_descriptor_operation_kind(descriptor) in {
            "content_stream_rewrite",
            "content_stream_paint_disable",
            "content_stream_rgb_color_rewrite",
            "selected_use_path_appearance_rewrite",
            "content_stream_stroke_width_rewrite",
            "content_stream_path_geometry_transform",
            "content_stream_path_boolean_replace",
            "content_stream_path_anchor_replace",
        }
    )
    xobject_content_stream_descriptor_count = sum(
        1
        for descriptor in appendable_descriptors
        if native_pdf_descriptor_operation_kind(descriptor) in {
            "content_stream_paint_disable",
            "content_stream_rgb_color_rewrite",
            "selected_use_path_appearance_rewrite",
            "content_stream_stroke_width_rewrite",
            "content_stream_path_geometry_transform",
            "content_stream_path_boolean_replace",
            "content_stream_path_anchor_replace",
            "content_stream_clip_disable",
        }
        and native_pdf_descriptor_targets_xobject_content_stream(descriptor)
    )
    paint_operator_rewrite_descriptor_count = sum(
        1
        for descriptor in appendable_descriptors
        if native_pdf_descriptor_operation_kind(descriptor) == "content_stream_paint_disable"
    )
    rgb_color_operator_rewrite_descriptor_count = sum(
        1
        for descriptor in appendable_descriptors
        if native_pdf_descriptor_operation_kind(descriptor) == "content_stream_rgb_color_rewrite"
        or bool(descriptor.get("rgb_color_patches"))
    )
    device_color_operator_rewrite_descriptor_count = sum(
        1
        for descriptor in appendable_descriptors
        if native_pdf_descriptor_operation_kind(descriptor) == "content_stream_rgb_color_rewrite"
        or bool(descriptor.get("device_color_patches"))
        or bool(descriptor.get("rgb_color_patches"))
    )
    stroke_width_operator_rewrite_descriptor_count = sum(
        1
        for descriptor in appendable_descriptors
        if native_pdf_descriptor_operation_kind(descriptor) == "content_stream_stroke_width_rewrite"
        or any(
            isinstance(patch, dict) and str(patch.get("stroke_property") or "") == "width"
            for patch in (descriptor.get("stroke_style_patches") or [])
        )
    )
    path_geometry_transform_descriptor_count = sum(
        1
        for descriptor in appendable_descriptors
        if native_pdf_descriptor_operation_kind(descriptor) == "content_stream_path_geometry_transform"
    )
    path_boolean_replacement_descriptor_count = sum(
        1
        for descriptor in appendable_descriptors
        if native_pdf_descriptor_operation_kind(descriptor) == "content_stream_path_boolean_replace"
    )
    path_anchor_replacement_descriptor_count = sum(
        1
        for descriptor in appendable_descriptors
        if native_pdf_descriptor_operation_kind(descriptor) == "content_stream_path_anchor_replace"
    )
    advanced_graph_rewrite_descriptor_count = sum(
        1
        for descriptor in appendable_descriptors
        if bool(descriptor.get("extgstate_appearance_patch")) or native_pdf_descriptor_operation_kind(descriptor) in {
            "content_stream_clip_disable",
            "extgstate_appearance_rewrite",
            "extgstate_blend_rewrite",
            "extgstate_alpha_rewrite",
            "extgstate_soft_mask_disable",
        }
    )
    clip_path_rewrite_descriptor_count = sum(
        1
        for descriptor in appendable_descriptors
        if native_pdf_descriptor_operation_kind(descriptor) == "content_stream_clip_disable"
    )
    blend_mode_rewrite_descriptor_count = sum(
        1
        for descriptor in appendable_descriptors
        if bool(descriptor.get("extgstate_appearance_patch"))
        or native_pdf_descriptor_operation_kind(descriptor) in {"extgstate_appearance_rewrite", "extgstate_blend_rewrite"}
    )
    alpha_rewrite_descriptor_count = sum(
        1
        for descriptor in appendable_descriptors
        if bool(descriptor.get("extgstate_appearance_patch"))
        or native_pdf_descriptor_operation_kind(descriptor) in {"extgstate_appearance_rewrite", "extgstate_alpha_rewrite"}
    )
    soft_mask_rewrite_descriptor_count = sum(
        1
        for descriptor in appendable_descriptors
        if native_pdf_descriptor_operation_kind(descriptor) == "extgstate_soft_mask_disable"
    )
    gradient_function_rewrite_descriptor_count = sum(
        1
        for descriptor in appendable_descriptors
        if native_pdf_descriptor_operation_kind(descriptor) == "shading_function_color_rewrite"
    )
    selected_use_gradient_clone_rebind_descriptor_count = sum(
        1
        for descriptor in appendable_descriptors
        if native_pdf_descriptor_operation_kind(descriptor) == "shading_function_color_rewrite"
        and bool(descriptor.get("clone_and_rebind_shared_form"))
        and bool(descriptor.get("selected_form_invocation_id") or descriptor.get("selected_xobject_invocation_id"))
    )
    shading_background_rewrite_descriptor_count = sum(
        1
        for descriptor in appendable_descriptors
        if native_pdf_descriptor_operation_kind(descriptor) == "shading_background_color_rewrite"
    )
    pattern_stream_rewrite_descriptor_count = sum(
        1
        for descriptor in appendable_descriptors
        if native_pdf_descriptor_operation_kind(descriptor) == "tiling_pattern_stream_color_rewrite"
    )
    gradient_mesh_pattern_rewrite_descriptor_count = shading_background_rewrite_descriptor_count + pattern_stream_rewrite_descriptor_count
    path_anchor_descriptor_count = sum(
        1
        for descriptor in appendable_descriptors
        if str(descriptor.get("descriptor_type") or "") in {"path_anchor_edit", "path_control_handle_edit"}
    )
    shared_form_clone_rebind_descriptor_count = sum(
        1
        for descriptor in appendable_descriptors
        if bool(descriptor.get("clone_and_rebind_shared_form"))
        and bool(descriptor.get("selected_form_invocation_id") or descriptor.get("selected_xobject_invocation_id"))
    )
    selected_use_extgstate_clone_rebind_descriptor_count = sum(
        1
        for descriptor in appendable_descriptors
        if (
            bool(descriptor.get("extgstate_appearance_patch"))
            or native_pdf_descriptor_operation_kind(descriptor) in {
            "extgstate_appearance_rewrite",
            "extgstate_blend_rewrite",
            "extgstate_alpha_rewrite",
            }
        )
        and bool(descriptor.get("clone_and_rebind_shared_form"))
        and bool(descriptor.get("selected_form_invocation_id") or descriptor.get("selected_xobject_invocation_id"))
    )
    selected_use_rgb_color_clone_rebind_descriptor_count = sum(
        1
        for descriptor in appendable_descriptors
        if (
            native_pdf_descriptor_operation_kind(descriptor) == "content_stream_rgb_color_rewrite"
            or bool(descriptor.get("rgb_color_patches"))
        )
        and bool(descriptor.get("clone_and_rebind_shared_form"))
        and bool(descriptor.get("selected_form_invocation_id") or descriptor.get("selected_xobject_invocation_id"))
    )
    selected_use_device_color_clone_rebind_descriptor_count = sum(
        1
        for descriptor in appendable_descriptors
        if (
            native_pdf_descriptor_operation_kind(descriptor) == "content_stream_rgb_color_rewrite"
            or bool(descriptor.get("device_color_patches"))
            or bool(descriptor.get("rgb_color_patches"))
        )
        and bool(descriptor.get("clone_and_rebind_shared_form"))
        and bool(descriptor.get("selected_form_invocation_id") or descriptor.get("selected_xobject_invocation_id"))
    )
    selected_use_special_color_tint_clone_rebind_descriptor_count = sum(
        1
        for descriptor in appendable_descriptors
        if bool(descriptor.get("special_color_patches"))
        and bool(descriptor.get("clone_and_rebind_shared_form"))
        and bool(descriptor.get("selected_form_invocation_id") or descriptor.get("selected_xobject_invocation_id"))
    )
    selected_use_stroke_geometry_clone_rebind_descriptor_count = sum(
        1
        for descriptor in appendable_descriptors
        if bool(descriptor.get("stroke_style_patches"))
        and bool(descriptor.get("clone_and_rebind_shared_form"))
        and bool(descriptor.get("selected_form_invocation_id") or descriptor.get("selected_xobject_invocation_id"))
    )
    unsupported_types = sorted({
        str(descriptor.get("descriptor_type") or descriptor.get("type") or descriptor.get("action") or "unknown")
        for descriptor in descriptors
        if not native_pdf_descriptor_operation_kind(descriptor)
    })
    if unsupported_types:
        raise ValueError(
            "Native PDF compile is atomic; the packet contains staged descriptors that the bounded writer cannot compile: "
            + ", ".join(unsupported_types)
        )
    if appendable_descriptors:
        payload = mutate_pdf_content_stream(pdf_bytes, filename, packet)
        payload["schema"] = "figureStudio.nativePdfCompileResult.v1"
        payload["compiler_endpoint"] = "/api/pdf-native-compile"
        payload["compile"] = {
            "status": "compiled-with-bounded-native-mutation-descriptors",
            "native_compiled_pdf_output_available": True,
            "native_equivalent_pdf_output_available": (
                (
                    object_tree_rewrite_descriptor_count > 0
                    or advanced_graph_rewrite_descriptor_count > 0
                    or gradient_function_rewrite_descriptor_count > 0
                    or gradient_mesh_pattern_rewrite_descriptor_count > 0
                )
                and not unsupported_types
            ),
            "full_native_equivalence": False,
            "appendable_descriptor_count": len(appendable_descriptors),
            "unsupported_descriptor_types": unsupported_types,
            "semantic_graph_rewrite_applied": advanced_graph_rewrite_descriptor_count > 0,
            "advanced_feature_graph_rewrite_applied": advanced_graph_rewrite_descriptor_count > 0,
            "advanced_feature_graph_rewrite_descriptor_count": advanced_graph_rewrite_descriptor_count,
            "clip_path_content_stream_rewrite_applied": clip_path_rewrite_descriptor_count > 0,
            "clip_path_operator_run_rewrite_applied": bool(payload.get("mutation", {}).get("clip_path_operator_run_rewrite_applied")),
            "clip_path_rewrite_descriptor_count": clip_path_rewrite_descriptor_count,
            "blend_mode_resource_rewrite_applied": blend_mode_rewrite_descriptor_count > 0,
            "blend_mode_resource_rewrite_descriptor_count": blend_mode_rewrite_descriptor_count,
            "alpha_resource_rewrite_applied": alpha_rewrite_descriptor_count > 0,
            "alpha_resource_rewrite_descriptor_count": alpha_rewrite_descriptor_count,
            "soft_mask_resource_rewrite_applied": soft_mask_rewrite_descriptor_count > 0,
            "soft_mask_resource_rewrite_descriptor_count": soft_mask_rewrite_descriptor_count,
            "gradient_mesh_pattern_native_write_applied": gradient_mesh_pattern_rewrite_descriptor_count > 0,
            "gradient_mesh_pattern_native_write_descriptor_count": gradient_mesh_pattern_rewrite_descriptor_count,
            "gradient_resource_rewrite_applied": gradient_function_rewrite_descriptor_count > 0,
            "gradient_resource_rewrite_descriptor_count": gradient_function_rewrite_descriptor_count,
            "shading_function_color_rewrite_applied": gradient_function_rewrite_descriptor_count > 0,
            "selected_use_gradient_clone_rebind_applied": bool(payload.get("mutation", {}).get("selected_use_gradient_clone_rebind_applied")),
            "selected_use_gradient_clone_rebind_descriptor_count": selected_use_gradient_clone_rebind_descriptor_count,
            "shading_resource_clone_applied": bool(payload.get("mutation", {}).get("shading_resource_clone_applied")),
            "function_resource_clone_applied": bool(payload.get("mutation", {}).get("function_resource_clone_applied")),
            "stitched_gradient_function_rewrite_applied": bool(payload.get("mutation", {}).get("stitched_gradient_function_rewrite_applied")),
            "gradient_function_promoted": bool(payload.get("mutation", {}).get("gradient_function_promoted")),
            "gradient_function_demoted": bool(payload.get("mutation", {}).get("gradient_function_demoted")),
            "gradient_stop_count_rewrite_applied": bool(payload.get("mutation", {}).get("gradient_stop_count_rewrite_applied")),
            "gradient_geometry_rewrite_applied": bool(payload.get("mutation", {}).get("gradient_geometry_rewrite_applied")),
            "shading_background_color_rewrite_applied": shading_background_rewrite_descriptor_count > 0,
            "shading_background_color_rewrite_descriptor_count": shading_background_rewrite_descriptor_count,
            "pattern_stream_color_rewrite_applied": pattern_stream_rewrite_descriptor_count > 0,
            "pattern_stream_color_rewrite_descriptor_count": pattern_stream_rewrite_descriptor_count,
            "robust_boolean_geometry_applied": robust_boolean_descriptor_count > 0,
            "robust_boolean_descriptor_count": robust_boolean_descriptor_count,
            "object_tree_content_stream_rewrite_applied": object_tree_rewrite_descriptor_count > 0,
            "object_tree_rewrite_descriptor_count": object_tree_rewrite_descriptor_count,
            "xobject_content_stream_rewrite_applied": bool(
                xobject_content_stream_descriptor_count > 0
                or payload.get("mutation", {}).get("xobject_content_stream_rewrite_applied")
            ),
            "xobject_content_stream_rewrite_descriptor_count": xobject_content_stream_descriptor_count,
            "paint_operator_run_rewrite_applied": paint_operator_rewrite_descriptor_count > 0,
            "paint_operator_rewrite_descriptor_count": paint_operator_rewrite_descriptor_count,
            "rgb_color_operator_run_rewrite_applied": rgb_color_operator_rewrite_descriptor_count > 0,
            "rgb_color_operator_rewrite_descriptor_count": rgb_color_operator_rewrite_descriptor_count,
            "device_color_operator_run_rewrite_applied": device_color_operator_rewrite_descriptor_count > 0,
            "device_color_operator_rewrite_descriptor_count": device_color_operator_rewrite_descriptor_count,
            "special_color_operator_run_rewrite_applied": bool(payload.get("mutation", {}).get("special_color_operator_run_rewrite_applied")),
            "special_color_operator_rewrite_descriptor_count": selected_use_special_color_tint_clone_rebind_descriptor_count,
            "stroke_width_operator_run_rewrite_applied": stroke_width_operator_rewrite_descriptor_count > 0,
            "stroke_width_operator_rewrite_descriptor_count": stroke_width_operator_rewrite_descriptor_count,
            "path_geometry_transform_applied": path_geometry_transform_descriptor_count > 0,
            "path_geometry_transform_descriptor_count": path_geometry_transform_descriptor_count,
            "path_boolean_replacement_applied": path_boolean_replacement_descriptor_count > 0,
            "path_boolean_replacement_descriptor_count": path_boolean_replacement_descriptor_count,
            "path_anchor_geometry_applied": path_anchor_descriptor_count > 0,
            "path_anchor_descriptor_count": path_anchor_descriptor_count,
            "path_anchor_replacement_applied": path_anchor_replacement_descriptor_count > 0,
            "path_anchor_replacement_descriptor_count": path_anchor_replacement_descriptor_count,
            "shared_form_clone_rebind_applied": bool(payload.get("mutation", {}).get("shared_form_clone_rebind_applied")),
            "shared_form_clone_rebind_descriptor_count": shared_form_clone_rebind_descriptor_count,
            "selected_use_extgstate_clone_rebind_applied": bool(payload.get("mutation", {}).get("selected_use_extgstate_clone_rebind_applied")),
            "selected_use_extgstate_clone_rebind_descriptor_count": selected_use_extgstate_clone_rebind_descriptor_count,
            "selected_use_appearance_stack_clone_rebind_applied": bool(payload.get("mutation", {}).get("selected_use_appearance_stack_clone_rebind_applied")),
            "selected_use_rgb_color_clone_rebind_applied": bool(payload.get("mutation", {}).get("selected_use_rgb_color_clone_rebind_applied")),
            "selected_use_rgb_color_clone_rebind_descriptor_count": selected_use_rgb_color_clone_rebind_descriptor_count,
            "selected_use_device_color_clone_rebind_applied": bool(payload.get("mutation", {}).get("selected_use_device_color_clone_rebind_applied")),
            "selected_use_device_color_clone_rebind_descriptor_count": selected_use_device_color_clone_rebind_descriptor_count,
            "selected_use_special_color_tint_clone_rebind_applied": bool(payload.get("mutation", {}).get("selected_use_special_color_tint_clone_rebind_applied")),
            "selected_use_special_color_tint_clone_rebind_descriptor_count": selected_use_special_color_tint_clone_rebind_descriptor_count,
            "selected_use_stroke_geometry_clone_rebind_applied": bool(payload.get("mutation", {}).get("selected_use_stroke_geometry_clone_rebind_applied")),
            "selected_use_stroke_geometry_clone_rebind_descriptor_count": selected_use_stroke_geometry_clone_rebind_descriptor_count,
            "selected_use_local_state_materialization_applied": bool(payload.get("mutation", {}).get("selected_use_local_state_materialization_applied")),
            "bounded_native_equivalent_object_tree_roundtrip_available": object_tree_rewrite_descriptor_count > 0 and not unsupported_types,
            "bounded_native_equivalent_resource_roundtrip_available": (
                (
                    advanced_graph_rewrite_descriptor_count > 0
                    or gradient_function_rewrite_descriptor_count > 0
                    or gradient_mesh_pattern_rewrite_descriptor_count > 0
                )
                and not unsupported_types
            ),
        }
        return payload
    if descriptors:
        raise ValueError(
            "Native PDF packet contains descriptors that are staged but not yet compilable by the bounded content-stream compiler: "
            + ", ".join(unsupported_types)
        )
    payload = roundtrip_pdf_noop(pdf_bytes, filename)
    payload["schema"] = "figureStudio.nativePdfCompileResult.v1"
    payload["compiler_endpoint"] = "/api/pdf-native-compile"
    payload["compile"] = {
        "status": "compiled-noop-source-roundtrip",
        "native_compiled_pdf_output_available": True,
        "native_equivalent_pdf_output_available": False,
        "full_native_equivalence": False,
        "appendable_descriptor_count": 0,
        "unsupported_descriptor_types": [],
        "semantic_graph_rewrite_applied": False,
        "advanced_feature_graph_rewrite_applied": False,
        "advanced_feature_graph_rewrite_descriptor_count": 0,
        "clip_path_content_stream_rewrite_applied": False,
        "clip_path_operator_run_rewrite_applied": False,
        "clip_path_rewrite_descriptor_count": 0,
        "blend_mode_resource_rewrite_applied": False,
        "blend_mode_resource_rewrite_descriptor_count": 0,
        "alpha_resource_rewrite_applied": False,
        "alpha_resource_rewrite_descriptor_count": 0,
        "soft_mask_resource_rewrite_applied": False,
        "soft_mask_resource_rewrite_descriptor_count": 0,
        "gradient_resource_rewrite_applied": False,
        "gradient_resource_rewrite_descriptor_count": 0,
        "gradient_mesh_pattern_native_write_applied": False,
        "gradient_mesh_pattern_native_write_descriptor_count": 0,
        "shading_function_color_rewrite_applied": False,
        "selected_use_gradient_clone_rebind_applied": False,
        "selected_use_gradient_clone_rebind_descriptor_count": 0,
        "shading_resource_clone_applied": False,
        "function_resource_clone_applied": False,
        "stitched_gradient_function_rewrite_applied": False,
        "gradient_function_promoted": False,
        "gradient_function_demoted": False,
        "gradient_stop_count_rewrite_applied": False,
        "gradient_geometry_rewrite_applied": False,
        "shading_background_color_rewrite_applied": False,
        "shading_background_color_rewrite_descriptor_count": 0,
        "pattern_stream_color_rewrite_applied": False,
        "pattern_stream_color_rewrite_descriptor_count": 0,
        "robust_boolean_geometry_applied": False,
        "robust_boolean_descriptor_count": 0,
        "object_tree_content_stream_rewrite_applied": False,
        "object_tree_rewrite_descriptor_count": 0,
        "xobject_content_stream_rewrite_applied": False,
        "xobject_content_stream_rewrite_descriptor_count": 0,
        "paint_operator_run_rewrite_applied": False,
        "paint_operator_rewrite_descriptor_count": 0,
        "rgb_color_operator_run_rewrite_applied": False,
        "rgb_color_operator_rewrite_descriptor_count": 0,
        "device_color_operator_run_rewrite_applied": False,
        "device_color_operator_rewrite_descriptor_count": 0,
        "special_color_operator_run_rewrite_applied": False,
        "special_color_operator_rewrite_descriptor_count": 0,
        "stroke_width_operator_run_rewrite_applied": False,
        "stroke_width_operator_rewrite_descriptor_count": 0,
        "path_geometry_transform_applied": False,
        "path_geometry_transform_descriptor_count": 0,
        "path_boolean_replacement_applied": False,
        "path_boolean_replacement_descriptor_count": 0,
        "path_anchor_geometry_applied": False,
        "path_anchor_descriptor_count": 0,
        "path_anchor_replacement_applied": False,
        "path_anchor_replacement_descriptor_count": 0,
        "shared_form_clone_rebind_applied": False,
        "shared_form_clone_rebind_descriptor_count": 0,
        "selected_use_extgstate_clone_rebind_applied": False,
        "selected_use_extgstate_clone_rebind_descriptor_count": 0,
        "selected_use_appearance_stack_clone_rebind_applied": False,
        "selected_use_rgb_color_clone_rebind_applied": False,
        "selected_use_rgb_color_clone_rebind_descriptor_count": 0,
        "selected_use_device_color_clone_rebind_applied": False,
        "selected_use_device_color_clone_rebind_descriptor_count": 0,
        "selected_use_special_color_tint_clone_rebind_applied": False,
        "selected_use_special_color_tint_clone_rebind_descriptor_count": 0,
        "selected_use_stroke_geometry_clone_rebind_applied": False,
        "selected_use_stroke_geometry_clone_rebind_descriptor_count": 0,
        "selected_use_local_state_materialization_applied": False,
        "bounded_native_equivalent_object_tree_roundtrip_available": False,
        "bounded_native_equivalent_resource_roundtrip_available": False,
    }
    return payload


def mutate_pdf_content_stream(pdf_bytes: bytes, filename: str, packet: dict[str, object]) -> dict[str, object]:
    import pikepdf

    descriptors = [
        descriptor
        for descriptor in native_edit_descriptors_from_packet(packet)
        if native_pdf_descriptor_operation_kind(descriptor)
    ]
    if not descriptors:
        raise ValueError("No supported native PDF content-stream mutation descriptors were provided.")
    clone_rebind_descriptors = [
        descriptor
        for descriptor in descriptors
        if native_pdf_descriptor_operation_kind(descriptor) in {
            "content_stream_path_anchor_replace",
            "content_stream_rgb_color_rewrite",
            "selected_use_path_appearance_rewrite",
            "extgstate_appearance_rewrite",
            "extgstate_blend_rewrite",
            "extgstate_alpha_rewrite",
        }
        and bool(descriptor.get("clone_and_rebind_shared_form"))
    ]
    if clone_rebind_descriptors and (len(clone_rebind_descriptors) != 1 or len(descriptors) != 1):
        raise ValueError(
            "Selected-use Form edits currently compile one clone-and-rebind descriptor at a time."
        )

    doc = PikePdfDocument.open(pdf_bytes)
    try:
        before_xref_length = int(finite_number(doc.xref_length() if hasattr(doc, "xref_length") else 0, 0))
        before_page_descriptors: list[dict[str, object]] = []
        after_page_descriptors: list[dict[str, object]] = []
        applied: list[dict[str, object]] = []
        for index, descriptor in enumerate(descriptors):
            page_number = max(1, int(finite_number(descriptor.get("page_number"), 1)))
            if page_number > doc.page_count:
                continue
            page = doc[page_number - 1]
            if not any(entry.get("page_number") == page_number for entry in before_page_descriptors):
                before_page_descriptors.append({
                    "page_number": page_number,
                    "page_xref": int(finite_number(getattr(page, "xref", 0), 0)),
                    "content_xrefs": page_content_xrefs(page),
                    "editable_content_stream_xrefs": editable_pdf_content_stream_xrefs(doc, page),
                })
            operation_kind = native_pdf_descriptor_operation_kind(descriptor)
            if operation_kind == "content_stream_rewrite":
                rewrite_result = rewrite_content_stream_descriptor(doc, page, descriptor)
                if rewrite_result is None:
                    continue
                applied.append({
                    "descriptor_id": descriptor.get("id") or f"content-stream-rewrite-{index + 1}",
                    "descriptor_type": descriptor.get("descriptor_type") or "object_tree_mutation",
                    "page_number": page_number,
                    "rewrite": rewrite_result,
                    "object_tree_content_stream_rewrite_applied": True,
                    "xobject_content_stream_rewrite_applied": bool(rewrite_result.get("target_content_stream_scope") == "form-xobject-content-stream"),
                    "mutation_kind": "in-place-content-stream-rewrite",
                })
                continue
            if operation_kind == "content_stream_paint_disable":
                rewrite_result = rewrite_content_stream_paint_operator_descriptor(doc, page, descriptor)
                if rewrite_result is None:
                    continue
                applied.append({
                    "descriptor_id": descriptor.get("id") or f"content-stream-paint-disable-{index + 1}",
                    "descriptor_type": descriptor.get("descriptor_type") or "object_tree_mutation",
                    "page_number": page_number,
                    "rewrite": rewrite_result,
                    "object_tree_content_stream_rewrite_applied": True,
                    "xobject_content_stream_rewrite_applied": bool(rewrite_result.get("target_content_stream_scope") == "form-xobject-content-stream"),
                    "paint_operator_run_rewrite_applied": True,
                    "mutation_kind": "in-place-content-stream-paint-operator-disable",
                })
                continue
            if operation_kind in {"content_stream_rgb_color_rewrite", "selected_use_path_appearance_rewrite"}:
                clone_and_rebind = bool(descriptor.get("clone_and_rebind_shared_form"))
                rewrite_result = (
                    rewrite_selected_form_invocation_rgb_color_descriptor(doc, page, page_number, descriptor)
                    if clone_and_rebind
                    else rewrite_content_stream_rgb_color_operator_descriptor(doc, page, descriptor)
                    if operation_kind == "content_stream_rgb_color_rewrite"
                    else None
                )
                if rewrite_result is None:
                    continue
                selected_stroke_properties = list(rewrite_result.get("stroke_properties") or [])
                selected_use_extgstate = bool(rewrite_result.get("selected_use_extgstate_clone_rebind_applied"))
                applied.append({
                    "descriptor_id": descriptor.get("id") or f"content-stream-rgb-color-rewrite-{index + 1}",
                    "descriptor_type": descriptor.get("descriptor_type") or "object_tree_mutation",
                    "page_number": page_number,
                    "rewrite": rewrite_result,
                    "object_tree_content_stream_rewrite_applied": True,
                    "xobject_content_stream_rewrite_applied": bool(
                        clone_and_rebind
                        or rewrite_result.get("target_content_stream_scope") == "form-xobject-content-stream"
                    ),
                    "rgb_color_operator_run_rewrite_applied": bool(rewrite_result.get("selected_use_rgb_color_clone_rebind_applied")) or not clone_and_rebind,
                    "device_color_operator_run_rewrite_applied": bool(rewrite_result.get("selected_use_device_color_clone_rebind_applied")) or not clone_and_rebind,
                    "special_color_operator_run_rewrite_applied": bool(rewrite_result.get("selected_use_special_color_tint_clone_rebind_applied")),
                    "stroke_width_operator_run_rewrite_applied": "width" in selected_stroke_properties,
                    "shared_form_clone_rebind_applied": bool(rewrite_result.get("shared_form_clone_rebind_applied")),
                    "selected_use_rgb_color_clone_rebind_applied": bool(rewrite_result.get("selected_use_rgb_color_clone_rebind_applied")),
                    "selected_use_device_color_clone_rebind_applied": bool(rewrite_result.get("selected_use_device_color_clone_rebind_applied")),
                    "selected_use_special_color_tint_clone_rebind_applied": bool(rewrite_result.get("selected_use_special_color_tint_clone_rebind_applied")),
                    "selected_use_stroke_geometry_clone_rebind_applied": bool(rewrite_result.get("selected_use_stroke_geometry_clone_rebind_applied")),
                    "selected_use_local_state_materialization_applied": bool(rewrite_result.get("selected_use_local_state_materialization_applied")),
                    "selected_use_extgstate_clone_rebind_applied": selected_use_extgstate,
                    "selected_use_appearance_stack_clone_rebind_applied": bool(rewrite_result.get("selected_use_appearance_stack_clone_rebind_applied")),
                    "advanced_feature_graph_rewrite_applied": selected_use_extgstate,
                    "blend_mode_resource_rewrite_applied": selected_use_extgstate,
                    "alpha_resource_rewrite_applied": selected_use_extgstate,
                    "mutation_kind": (
                        "clone-rebind-selected-use-appearance-stack-rewrite"
                        if clone_and_rebind and selected_use_extgstate
                        else "clone-rebind-selected-use-local-appearance-state"
                        if clone_and_rebind and rewrite_result.get("selected_use_local_state_materialization_applied")
                        else "clone-rebind-selected-use-special-color-tint-rewrite"
                        if clone_and_rebind and rewrite_result.get("selected_use_special_color_tint_clone_rebind_applied")
                        else "clone-rebind-selected-use-path-appearance-rewrite"
                        if clone_and_rebind and selected_stroke_properties
                        else "clone-rebind-selected-use-rgb-color-operator-rewrite"
                        if clone_and_rebind
                        else "in-place-content-stream-rgb-color-operator-rewrite"
                    ),
                })
                continue
            if operation_kind == "content_stream_stroke_width_rewrite":
                rewrite_result = rewrite_content_stream_stroke_width_operator_descriptor(doc, page, descriptor)
                if rewrite_result is None:
                    continue
                applied.append({
                    "descriptor_id": descriptor.get("id") or f"content-stream-stroke-width-rewrite-{index + 1}",
                    "descriptor_type": descriptor.get("descriptor_type") or "object_tree_mutation",
                    "page_number": page_number,
                    "rewrite": rewrite_result,
                    "object_tree_content_stream_rewrite_applied": True,
                    "xobject_content_stream_rewrite_applied": bool(rewrite_result.get("target_content_stream_scope") == "form-xobject-content-stream"),
                    "stroke_width_operator_run_rewrite_applied": True,
                    "mutation_kind": "in-place-content-stream-stroke-width-operator-rewrite",
                })
                continue
            if operation_kind == "content_stream_path_geometry_transform":
                rewrite_result = rewrite_content_stream_path_geometry_operator_descriptor(doc, page, descriptor)
                if rewrite_result is None:
                    continue
                applied.append({
                    "descriptor_id": descriptor.get("id") or f"content-stream-path-geometry-transform-{index + 1}",
                    "descriptor_type": descriptor.get("descriptor_type") or "object_tree_mutation",
                    "page_number": page_number,
                    "rewrite": rewrite_result,
                    "object_tree_content_stream_rewrite_applied": True,
                    "xobject_content_stream_rewrite_applied": bool(rewrite_result.get("target_content_stream_scope") == "form-xobject-content-stream"),
                    "path_geometry_transform_applied": True,
                    "mutation_kind": "in-place-content-stream-path-geometry-transform",
                })
                continue
            if operation_kind == "content_stream_path_boolean_replace":
                rewrite_result = rewrite_content_stream_path_boolean_replacement_descriptor(doc, page, descriptor)
                if rewrite_result is None:
                    continue
                applied.append({
                    "descriptor_id": descriptor.get("id") or f"content-stream-path-boolean-replace-{index + 1}",
                    "descriptor_type": descriptor.get("descriptor_type") or "path_boolean_operation",
                    "page_number": page_number,
                    "rewrite": rewrite_result,
                    "object_tree_content_stream_rewrite_applied": True,
                    "xobject_content_stream_rewrite_applied": bool(rewrite_result.get("target_content_stream_scope") == "form-xobject-content-stream"),
                    "path_boolean_replacement_applied": True,
                    "robust_boolean_geometry_applied": bool(descriptor.get("robust_geometry_engine") or descriptor.get("robust_boolean_geometry_applied")),
                    "mutation_kind": "in-place-content-stream-path-boolean-replacement",
                })
                continue
            if operation_kind == "content_stream_path_anchor_replace":
                clone_and_rebind = bool(descriptor.get("clone_and_rebind_shared_form"))
                rewrite_result = (
                    rewrite_shared_form_invocation_path_descriptor(doc, page, page_number, descriptor)
                    if clone_and_rebind
                    else rewrite_content_stream_path_boolean_replacement_descriptor(doc, page, descriptor)
                )
                if rewrite_result is None:
                    continue
                applied.append({
                    "descriptor_id": descriptor.get("id") or f"content-stream-path-anchor-replace-{index + 1}",
                    "descriptor_type": descriptor.get("descriptor_type") or "path_anchor_edit",
                    "page_number": page_number,
                    "rewrite": rewrite_result,
                    "object_tree_content_stream_rewrite_applied": True,
                    "xobject_content_stream_rewrite_applied": bool(rewrite_result.get("target_content_stream_scope") == "form-xobject-content-stream"),
                    "path_anchor_geometry_applied": True,
                    "path_anchor_replacement_applied": True,
                    "shared_form_clone_rebind_applied": bool(rewrite_result.get("shared_form_clone_rebind_applied")),
                    "mutation_kind": "clone-rebind-content-stream-path-anchor-replacement" if clone_and_rebind else "in-place-content-stream-path-anchor-replacement",
                })
                continue
            if operation_kind == "content_stream_clip_disable":
                rewrite_result = rewrite_content_stream_clip_path_descriptor(doc, page, descriptor)
                if rewrite_result is None:
                    continue
                applied.append({
                    "descriptor_id": descriptor.get("id") or f"content-stream-clip-disable-{index + 1}",
                    "descriptor_type": descriptor.get("descriptor_type") or "advanced_feature_graph_edit",
                    "page_number": page_number,
                    "rewrite": rewrite_result,
                    "advanced_feature_graph_rewrite_applied": True,
                    "xobject_content_stream_rewrite_applied": bool(rewrite_result.get("target_content_stream_scope") == "form-xobject-content-stream"),
                    "clip_path_content_stream_rewrite_applied": True,
                    "clip_path_operator_run_rewrite_applied": bool(rewrite_result.get("target_operator_run_rewrite")),
                    "mutation_kind": "in-place-content-stream-clip-path-disable",
                })
                continue
            if operation_kind == "extgstate_appearance_rewrite":
                clone_and_rebind = bool(descriptor.get("clone_and_rebind_shared_form"))
                rewrite_result = (
                    rewrite_selected_form_invocation_extgstate_descriptor(doc, page, page_number, descriptor)
                    if clone_and_rebind
                    else rewrite_extgstate_appearance_descriptor(doc, descriptor)
                )
                if rewrite_result is None:
                    continue
                applied.append({
                    "descriptor_id": descriptor.get("id") or f"extgstate-appearance-rewrite-{index + 1}",
                    "descriptor_type": descriptor.get("descriptor_type") or "advanced_feature_graph_edit",
                    "page_number": page_number,
                    "rewrite": rewrite_result,
                    "advanced_feature_graph_rewrite_applied": True,
                    "blend_mode_resource_rewrite_applied": True,
                    "alpha_resource_rewrite_applied": True,
                    "shared_form_clone_rebind_applied": bool(rewrite_result.get("shared_form_clone_rebind_applied")),
                    "selected_use_extgstate_clone_rebind_applied": bool(rewrite_result.get("selected_use_extgstate_clone_rebind_applied")),
                    "mutation_kind": "clone-rebind-selected-use-extgstate-appearance-rewrite" if clone_and_rebind else "in-place-extgstate-appearance-rewrite",
                })
                continue
            if operation_kind == "extgstate_blend_rewrite":
                clone_and_rebind = bool(descriptor.get("clone_and_rebind_shared_form"))
                rewrite_result = (
                    rewrite_selected_form_invocation_extgstate_descriptor(doc, page, page_number, descriptor)
                    if clone_and_rebind
                    else rewrite_extgstate_blend_mode_descriptor(doc, descriptor)
                )
                if rewrite_result is None:
                    continue
                applied.append({
                    "descriptor_id": descriptor.get("id") or f"extgstate-blend-rewrite-{index + 1}",
                    "descriptor_type": descriptor.get("descriptor_type") or "advanced_feature_graph_edit",
                    "page_number": page_number,
                    "rewrite": rewrite_result,
                    "advanced_feature_graph_rewrite_applied": True,
                    "blend_mode_resource_rewrite_applied": True,
                    "shared_form_clone_rebind_applied": bool(rewrite_result.get("shared_form_clone_rebind_applied")),
                    "selected_use_extgstate_clone_rebind_applied": bool(rewrite_result.get("selected_use_extgstate_clone_rebind_applied")),
                    "mutation_kind": "clone-rebind-selected-use-extgstate-blend-mode-rewrite" if clone_and_rebind else "in-place-extgstate-blend-mode-rewrite",
                })
                continue
            if operation_kind == "extgstate_alpha_rewrite":
                clone_and_rebind = bool(descriptor.get("clone_and_rebind_shared_form"))
                rewrite_result = (
                    rewrite_selected_form_invocation_extgstate_descriptor(doc, page, page_number, descriptor)
                    if clone_and_rebind
                    else rewrite_extgstate_opacity_descriptor(doc, descriptor)
                )
                if rewrite_result is None:
                    continue
                applied.append({
                    "descriptor_id": descriptor.get("id") or f"extgstate-alpha-rewrite-{index + 1}",
                    "descriptor_type": descriptor.get("descriptor_type") or "advanced_feature_graph_edit",
                    "page_number": page_number,
                    "rewrite": rewrite_result,
                    "advanced_feature_graph_rewrite_applied": True,
                    "alpha_resource_rewrite_applied": True,
                    "shared_form_clone_rebind_applied": bool(rewrite_result.get("shared_form_clone_rebind_applied")),
                    "selected_use_extgstate_clone_rebind_applied": bool(rewrite_result.get("selected_use_extgstate_clone_rebind_applied")),
                    "mutation_kind": "clone-rebind-selected-use-extgstate-alpha-rewrite" if clone_and_rebind else "in-place-extgstate-alpha-rewrite",
                })
                continue
            if operation_kind == "extgstate_soft_mask_disable":
                rewrite_result = rewrite_extgstate_soft_mask_descriptor(doc, descriptor)
                if rewrite_result is None:
                    continue
                applied.append({
                    "descriptor_id": descriptor.get("id") or f"extgstate-soft-mask-disable-{index + 1}",
                    "descriptor_type": descriptor.get("descriptor_type") or "advanced_feature_graph_edit",
                    "page_number": page_number,
                    "rewrite": rewrite_result,
                    "advanced_feature_graph_rewrite_applied": True,
                    "soft_mask_resource_rewrite_applied": True,
                    "mutation_kind": "in-place-extgstate-soft-mask-disable",
                })
                continue
            if operation_kind == "shading_function_color_rewrite":
                clone_and_rebind = bool(
                    descriptor.get("clone_and_rebind_shared_form")
                    and (descriptor.get("selected_form_invocation_id") or descriptor.get("selected_xobject_invocation_id"))
                )
                rewrite_result = (
                    rewrite_selected_form_invocation_gradient_descriptor(doc, page, page_number, descriptor)
                    if clone_and_rebind
                    else rewrite_shading_function_colors_descriptor(doc, descriptor)
                )
                if rewrite_result is None:
                    continue
                applied.append({
                    "descriptor_id": descriptor.get("id") or f"shading-function-color-rewrite-{index + 1}",
                    "descriptor_type": descriptor.get("descriptor_type") or "gradient_stop_edit",
                    "page_number": page_number,
                    "rewrite": rewrite_result,
                    "gradient_resource_rewrite_applied": True,
                    "shared_form_clone_rebind_applied": bool(rewrite_result.get("shared_form_clone_rebind_applied")),
                    "selected_use_gradient_clone_rebind_applied": bool(rewrite_result.get("selected_use_gradient_clone_rebind_applied")),
                    "shading_resource_clone_applied": bool(rewrite_result.get("shading_resource_clone_applied")),
                    "function_resource_clone_applied": bool(rewrite_result.get("function_resource_clone_applied")),
                    "stitched_gradient_function_rewrite_applied": bool(rewrite_result.get("stitched_gradient_function_rewrite_applied")),
                    "gradient_function_promoted": bool(rewrite_result.get("gradient_function_promoted")),
                    "gradient_function_demoted": bool(rewrite_result.get("gradient_function_demoted")),
                    "gradient_stop_count_rewrite_applied": bool(rewrite_result.get("gradient_stop_count_rewrite_applied")),
                    "gradient_geometry_rewrite_applied": bool(rewrite_result.get("gradient_geometry_rewrite_applied")),
                    "mutation_kind": "clone-rebind-selected-use-gradient-rewrite" if clone_and_rebind else "in-place-shading-function-color-rewrite",
                })
                continue
            if operation_kind == "shading_background_color_rewrite":
                rewrite_result = rewrite_shading_background_color_descriptor(doc, descriptor)
                if rewrite_result is None:
                    continue
                applied.append({
                    "descriptor_id": descriptor.get("id") or f"shading-background-color-rewrite-{index + 1}",
                    "descriptor_type": descriptor.get("descriptor_type") or "gradient_mesh_pattern_edit",
                    "page_number": page_number,
                    "rewrite": rewrite_result,
                    "gradient_mesh_pattern_native_write_applied": True,
                    "shading_background_color_rewrite_applied": True,
                    "mutation_kind": "in-place-shading-background-color-rewrite",
                })
                continue
            if operation_kind == "tiling_pattern_stream_color_rewrite":
                rewrite_result = rewrite_tiling_pattern_stream_colors_descriptor(doc, descriptor)
                if rewrite_result is None:
                    continue
                applied.append({
                    "descriptor_id": descriptor.get("id") or f"tiling-pattern-stream-color-rewrite-{index + 1}",
                    "descriptor_type": descriptor.get("descriptor_type") or "gradient_mesh_pattern_edit",
                    "page_number": page_number,
                    "rewrite": rewrite_result,
                    "gradient_mesh_pattern_native_write_applied": True,
                    "pattern_stream_color_rewrite_applied": True,
                    "mutation_kind": "in-place-tiling-pattern-stream-color-rewrite",
                })
                continue
            if operation_kind == "annotation_rectangle_overlay":
                rect = pdf_rect_from_descriptor(PikePdfGeometry, page, descriptor)
                if rect is None:
                    continue
                style = descriptor.get("style") if isinstance(descriptor.get("style"), dict) else {}
                page.draw_rect(
                    rect,
                    color=hex_color_triplet(style.get("stroke") if isinstance(style, dict) else "#111820"),
                    width=max(0.25, finite_number(style.get("stroke_width") if isinstance(style, dict) else 1.5, 1.5)),
                    overlay=True,
                )
                applied.append({
                    "descriptor_id": descriptor.get("id") or f"annotation-rectangle-{index + 1}",
                    "descriptor_type": descriptor.get("descriptor_type") or "annotation_rectangle_overlay",
                    "page_number": page_number,
                    "rect": rect_payload(rect),
                    "mutation_kind": "append-page-content-stream-rectangle",
                })
                continue
            path_result = draw_path_descriptor(PikePdfGeometry, page, descriptor)
            if path_result is None:
                continue
            applied.append({
                "descriptor_id": descriptor.get("id") or f"path-overlay-{index + 1}",
                "descriptor_type": descriptor.get("descriptor_type") or "path_overlay",
                "page_number": page_number,
                "path": path_result,
                "boolean_mode": descriptor.get("boolean_mode") or "",
                "geometry_engine": descriptor.get("geometry_engine") or "",
                "robust_boolean_geometry_applied": bool(descriptor.get("robust_geometry_engine") or descriptor.get("robust_boolean_geometry_applied")),
                "path_anchor_geometry_applied": str(descriptor.get("descriptor_type") or "") in {"path_anchor_edit", "path_control_handle_edit"},
                "mutation_kind": "append-page-content-stream-path",
            })
        if not applied:
            raise ValueError("No supported native PDF mutation descriptors could be applied to this PDF.")
        for before in before_page_descriptors:
            page = doc[int(before["page_number"]) - 1]
            after_page_descriptors.append({
                "page_number": before["page_number"],
                "page_xref": int(finite_number(getattr(page, "xref", 0), 0)),
                "content_xrefs": page_content_xrefs(page),
                "editable_content_stream_xrefs": editable_pdf_content_stream_xrefs(doc, page),
            })
        mutated_bytes = doc.write()
        after_xref_length = int(finite_number(doc.xref_length() if hasattr(doc, "xref_length") else 0, 0))
    finally:
        doc.close()

    return {
        "ok": True,
        "schema": "figureStudio.nativePdfContentStreamMutationResult.v1",
        "source_pdf_filename": filename or "uploaded.pdf",
        "mutation_engine": {
            "name": "pikepdf",
            "version": str(getattr(pikepdf, "__version__", "")),
            "library": "QPDF",
            "operation": "bounded-page-content-stream-and-extgstate-resource-rewrite",
        },
        "operation_matrix": native_pdf_content_stream_operation_matrix(),
        "mutation": {
            "status": "bounded-native-pdf-mutated",
            "applied_descriptor_count": len(applied),
            "applied_descriptor_types": sorted({str(item.get("descriptor_type") or "") for item in applied if item.get("descriptor_type")}),
            "applied_descriptors": applied,
            "before_xref_length": before_xref_length,
            "after_xref_length": after_xref_length,
            "before_pages": before_page_descriptors,
            "after_pages": after_page_descriptors,
            "content_stream_mutated": any(
                str(item.get("mutation_kind") or "") in {
                    "in-place-content-stream-rewrite",
                    "in-place-content-stream-paint-operator-disable",
                    "in-place-content-stream-rgb-color-operator-rewrite",
                    "clone-rebind-selected-use-rgb-color-operator-rewrite",
                    "clone-rebind-selected-use-special-color-tint-rewrite",
                    "clone-rebind-selected-use-path-appearance-rewrite",
                    "clone-rebind-selected-use-appearance-stack-rewrite",
                    "in-place-content-stream-stroke-width-operator-rewrite",
                    "in-place-content-stream-path-geometry-transform",
                    "in-place-content-stream-path-boolean-replacement",
                    "in-place-content-stream-path-anchor-replacement",
                    "clone-rebind-content-stream-path-anchor-replacement",
                    "clone-rebind-selected-use-extgstate-appearance-rewrite",
                    "clone-rebind-selected-use-extgstate-blend-mode-rewrite",
                    "clone-rebind-selected-use-extgstate-alpha-rewrite",
                    "clone-rebind-selected-use-gradient-rewrite",
                    "in-place-content-stream-clip-path-disable",
                    "append-page-content-stream-rectangle",
                    "append-page-content-stream-path",
                }
                for item in applied
            ),
            "resource_graph_mutated": any(
                bool(
                    item.get("blend_mode_resource_rewrite_applied")
                    or item.get("alpha_resource_rewrite_applied")
                    or item.get("soft_mask_resource_rewrite_applied")
                    or item.get("gradient_resource_rewrite_applied")
                    or item.get("gradient_mesh_pattern_native_write_applied")
                )
                for item in applied
            ),
            "object_tree_content_stream_rewrite_applied": any(bool(item.get("object_tree_content_stream_rewrite_applied")) for item in applied),
            "xobject_content_stream_rewrite_applied": any(bool(item.get("xobject_content_stream_rewrite_applied")) for item in applied),
            "paint_operator_run_rewrite_applied": any(bool(item.get("paint_operator_run_rewrite_applied")) for item in applied),
            "rgb_color_operator_run_rewrite_applied": any(bool(item.get("rgb_color_operator_run_rewrite_applied")) for item in applied),
            "device_color_operator_run_rewrite_applied": any(bool(item.get("device_color_operator_run_rewrite_applied")) for item in applied),
            "special_color_operator_run_rewrite_applied": any(bool(item.get("special_color_operator_run_rewrite_applied")) for item in applied),
            "stroke_width_operator_run_rewrite_applied": any(bool(item.get("stroke_width_operator_run_rewrite_applied")) for item in applied),
            "path_geometry_transform_applied": any(bool(item.get("path_geometry_transform_applied")) for item in applied),
            "path_boolean_replacement_applied": any(bool(item.get("path_boolean_replacement_applied")) for item in applied),
            "path_anchor_geometry_applied": any(bool(item.get("path_anchor_geometry_applied")) for item in applied),
            "path_anchor_replacement_applied": any(bool(item.get("path_anchor_replacement_applied")) for item in applied),
            "shared_form_clone_rebind_applied": any(bool(item.get("shared_form_clone_rebind_applied")) for item in applied),
            "selected_use_extgstate_clone_rebind_applied": any(bool(item.get("selected_use_extgstate_clone_rebind_applied")) for item in applied),
            "selected_use_appearance_stack_clone_rebind_applied": any(bool(item.get("selected_use_appearance_stack_clone_rebind_applied")) for item in applied),
            "selected_use_rgb_color_clone_rebind_applied": any(bool(item.get("selected_use_rgb_color_clone_rebind_applied")) for item in applied),
            "selected_use_device_color_clone_rebind_applied": any(bool(item.get("selected_use_device_color_clone_rebind_applied")) for item in applied),
            "selected_use_special_color_tint_clone_rebind_applied": any(bool(item.get("selected_use_special_color_tint_clone_rebind_applied")) for item in applied),
            "selected_use_gradient_clone_rebind_applied": any(bool(item.get("selected_use_gradient_clone_rebind_applied")) for item in applied),
            "shading_resource_clone_applied": any(bool(item.get("shading_resource_clone_applied")) for item in applied),
            "function_resource_clone_applied": any(bool(item.get("function_resource_clone_applied")) for item in applied),
            "stitched_gradient_function_rewrite_applied": any(bool(item.get("stitched_gradient_function_rewrite_applied")) for item in applied),
            "gradient_function_promoted": any(bool(item.get("gradient_function_promoted")) for item in applied),
            "gradient_function_demoted": any(bool(item.get("gradient_function_demoted")) for item in applied),
            "gradient_stop_count_rewrite_applied": any(bool(item.get("gradient_stop_count_rewrite_applied")) for item in applied),
            "gradient_geometry_rewrite_applied": any(bool(item.get("gradient_geometry_rewrite_applied")) for item in applied),
            "selected_use_stroke_geometry_clone_rebind_applied": any(bool(item.get("selected_use_stroke_geometry_clone_rebind_applied")) for item in applied),
            "selected_use_local_state_materialization_applied": any(bool(item.get("selected_use_local_state_materialization_applied")) for item in applied),
            "robust_boolean_geometry_applied": any(bool(item.get("robust_boolean_geometry_applied")) for item in applied),
            "advanced_feature_graph_rewrite_applied": any(bool(item.get("advanced_feature_graph_rewrite_applied")) for item in applied),
            "clip_path_content_stream_rewrite_applied": any(bool(item.get("clip_path_content_stream_rewrite_applied")) for item in applied),
            "clip_path_operator_run_rewrite_applied": any(bool(item.get("clip_path_operator_run_rewrite_applied")) for item in applied),
            "blend_mode_resource_rewrite_applied": any(bool(item.get("blend_mode_resource_rewrite_applied")) for item in applied),
            "alpha_resource_rewrite_applied": any(bool(item.get("alpha_resource_rewrite_applied")) for item in applied),
            "soft_mask_resource_rewrite_applied": any(bool(item.get("soft_mask_resource_rewrite_applied")) for item in applied),
            "gradient_resource_rewrite_applied": any(bool(item.get("gradient_resource_rewrite_applied")) for item in applied),
            "gradient_mesh_pattern_native_write_applied": any(bool(item.get("gradient_mesh_pattern_native_write_applied")) for item in applied),
            "shading_function_color_rewrite_applied": any(bool(item.get("gradient_resource_rewrite_applied")) for item in applied),
            "shading_background_color_rewrite_applied": any(bool(item.get("shading_background_color_rewrite_applied")) for item in applied),
            "pattern_stream_color_rewrite_applied": any(bool(item.get("pattern_stream_color_rewrite_applied")) for item in applied),
            "native_equivalent_pdf_output_available": any(
                bool(
                    item.get("object_tree_content_stream_rewrite_applied")
                    or item.get("clip_path_content_stream_rewrite_applied")
                    or item.get("blend_mode_resource_rewrite_applied")
                    or item.get("alpha_resource_rewrite_applied")
                    or item.get("soft_mask_resource_rewrite_applied")
                    or item.get("gradient_resource_rewrite_applied")
                    or item.get("gradient_mesh_pattern_native_write_applied")
                )
                for item in applied
            ),
            "full_native_equivalence": False,
        },
        "pdfBase64": base64.b64encode(mutated_bytes).decode("ascii"),
        "output_pdf_byte_size": len(mutated_bytes),
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }


class FigureStudioHandler(SimpleHTTPRequestHandler):
    server_version = f"FigureStudioServer/{FIGURE_STUDIO_VERSION}"

    def __init__(
        self,
        *args,
        directory: str | None = None,
        desktop_cookie_name: str = "",
        desktop_cookie_value: str = "",
        desktop_capabilities: dict[str, object] | None = None,
        **kwargs,
    ):
        self.desktop_cookie_name = desktop_cookie_name
        self.desktop_cookie_value = desktop_cookie_value
        self.desktop_capabilities = desktop_capabilities
        super().__init__(*args, directory=directory, **kwargs)

    def log_message(self, format: str, *args) -> None:  # noqa: A002 - stdlib signature
        print(f"[Figure Tool] {self.address_string()} - {format % args}")

    def send_json(self, status: int, payload: dict[str, object]) -> None:
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def end_headers(self) -> None:
        if self.desktop_cookie_name:
            self.send_header("Content-Security-Policy", "default-src 'self'; base-uri 'self'; object-src 'none'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; font-src 'self' data:; connect-src 'self'; worker-src 'self' blob:; frame-src 'self' blob:; media-src 'self' data: blob:; form-action 'self'; frame-ancestors 'self'")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Cross-Origin-Resource-Policy", "same-origin")
            self.send_header("Cross-Origin-Opener-Policy", "same-origin")
            self.send_header("X-Frame-Options", "SAMEORIGIN")
            self.send_header("Permissions-Policy", "camera=(), microphone=(), geolocation=(), payment=(), usb=(), serial=()")
        super().end_headers()

    def desktop_request_authorized(self) -> bool:
        if not self.desktop_cookie_name:
            return True
        host = str(self.headers.get("Host") or "").split(":", 1)[0].casefold()
        if host != "127.0.0.1":
            return False
        raw_cookie = str(self.headers.get("Cookie") or "")
        try:
            cookies = SimpleCookie()
            cookies.load(raw_cookie)
        except (CookieError, ValueError):
            return False
        session = cookies.get(self.desktop_cookie_name)
        return bool(
            session
            and hmac.compare_digest(session.value, self.desktop_cookie_value)
        )

    def reject_unauthorized_desktop_request(self) -> bool:
        if self.desktop_request_authorized():
            return False
        self.send_json(403, {"ok": False, "error": "Figure Tool desktop session required."})
        return True

    def do_HEAD(self) -> None:  # noqa: N802 - stdlib signature
        if self.reject_unauthorized_desktop_request():
            return
        super().do_HEAD()

    def do_GET(self) -> None:  # noqa: N802 - stdlib signature
        if self.reject_unauthorized_desktop_request():
            return
        parsed = urlparse(self.path)
        if parsed.path == "/api/status":
            if self.desktop_capabilities is not None:
                self.send_json(200, self.desktop_capabilities)
                return
            try:
                import pikepdf

                native_ir_payload = {
                    "nativePdfIrShadow": True,
                    "nativePdfIrParser": "pikepdf/QPDF",
                    "nativePdfMutation": True,
                    "nativePdfMutationEngine": "pikepdf/QPDF",
                    "pikepdfVersion": str(getattr(pikepdf, "__version__", "") or ""),
                    "qpdfVersion": str(getattr(pikepdf, "__libqpdf_version__", "") or ""),
                    **verify_pdfium_runtime_transaction(),
                }
            except (ImportError, RuntimeError) as error:
                native_ir_payload = {
                    "nativePdfIrShadow": False,
                    "nativePdfMutation": False,
                    "pdfVisualProof": False,
                    "nativePdfIrMessage": str(error) or "The native PDF runtime is unavailable in this Python environment.",
                }
            self.send_json(200, {
                "ok": True,
                "pdfImport": True,
                "pdfImportEngine": "PDF.js",
                **native_ir_payload,
            })
            return
        if parsed.path in {"/", "/index.html"}:
            target = "/app/index.html"
            if parsed.query:
                target = f"{target}?{parsed.query}"
            self.send_response(302)
            self.send_header("Location", target)
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            return
        super().do_GET()

    def do_POST(self) -> None:  # noqa: N802 - stdlib signature
        if self.reject_unauthorized_desktop_request():
            return
        parsed = urlparse(self.path)
        if parsed.path not in {"/api/pdf-source-fonts", "/api/pdf-native-ir-shadow", "/api/pdf-native-mutate", "/api/pdf-native-roundtrip", "/api/pdf-native-compile", "/api/text-to-path"}:
            self.send_json(404, {"ok": False, "error": "Unknown API endpoint."})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0:
                raise ValueError("Empty request body.")
            if parsed.path == "/api/text-to-path":
                if length > MAX_TEXT_OUTLINE_JSON_BYTES:
                    raise ValueError(f"Text outline payload is too large ({MAX_TEXT_OUTLINE_JSON_BYTES // 1024 // 1024} MB limit).")
                payload = json.loads(self.rfile.read(length).decode("utf-8", errors="replace"))
                if not isinstance(payload, dict):
                    raise ValueError("Text outline payload must be a JSON object.")
                self.send_json(200, build_text_glyph_outline_payload(payload))
                return
            if length > MAX_UPLOAD_BYTES:
                raise ValueError(f"PDF upload is too large for this prototype ({MAX_UPLOAD_BYTES // 1024 // 1024} MB limit).")
            fields = parse_multipart(self.rfile.read(length), self.headers.get("Content-Type", ""))
            file_field = fields.get("file")
            if not file_field or not file_field.get("data"):
                raise ValueError("No PDF file field was provided.")
            filename = str(file_field.get("filename") or "uploaded.pdf")
            if parsed.path == "/api/pdf-native-ir-shadow":
                query = parse_qs(parsed.query)
                page = int((query.get("page") or ["1"])[0])
                payload = build_native_pdf_ir_shadow_payload(
                    bytes(file_field["data"]),
                    filename,
                    page,
                )
            elif parsed.path == "/api/pdf-source-fonts":
                query = parse_qs(parsed.query)
                page = int((query.get("page") or ["1"])[0])
                raw_packet = fields.get("request", {}).get("data", b"{}")
                packet = json.loads(bytes(raw_packet).decode("utf-8", errors="replace"))
                if not isinstance(packet, dict):
                    raise ValueError("PDF source-font request must be a JSON object.")
                payload = inspect_pdf_source_fonts(bytes(file_field["data"]), filename, page, packet)
            elif parsed.path == "/api/pdf-native-roundtrip":
                payload = roundtrip_pdf_noop(bytes(file_field["data"]), filename)
            elif parsed.path == "/api/pdf-native-compile":
                raw_packet = fields.get("packet", {}).get("data", b"{}")
                packet = json.loads(bytes(raw_packet).decode("utf-8", errors="replace"))
                if not isinstance(packet, dict):
                    raise ValueError("Native PDF compile packet must be a JSON object.")
                payload = compile_native_pdf_packet(bytes(file_field["data"]), filename, packet)
            elif parsed.path == "/api/pdf-native-mutate":
                raw_packet = fields.get("packet", {}).get("data", b"{}")
                packet = json.loads(bytes(raw_packet).decode("utf-8", errors="replace"))
                if not isinstance(packet, dict):
                    raise ValueError("Native PDF mutation packet must be a JSON object.")
                payload = mutate_pdf_content_stream(bytes(file_field["data"]), filename, packet)
            self.send_json(200, payload)
        except RuntimeError as error:
            self.send_json(501, {"ok": False, "error": str(error)})
        except Exception as error:  # noqa: BLE001 - return friendly API error
            self.send_json(400, {"ok": False, "error": str(error)})


DESKTOP_BOOTSTRAP_PROTOCOL = "figureStudio.desktop.sidecarBootstrap.v1"
DESKTOP_READY_PROTOCOL = "figureStudio.desktop.sidecarReady.v1"
DESKTOP_SHUTDOWN_PROTOCOL = "figureStudio.desktop.sidecarShutdown.v1"
DESKTOP_ENDPOINTS = [
    "/api/status",
    "/api/pdf-source-fonts",
    "/api/pdf-native-ir-shadow",
    "/api/pdf-native-mutate",
    "/api/pdf-native-roundtrip",
    "/api/pdf-native-compile",
    "/api/text-to-path",
]


def desktop_bootstrap() -> tuple[str, str, int]:
    raw = sys.stdin.readline(16 * 1024)
    if not raw:
        raise RuntimeError("Figure Tool desktop bootstrap was not provided.")
    payload = json.loads(raw)
    if payload.get("protocol") != DESKTOP_BOOTSTRAP_PROTOCOL:
        raise RuntimeError("Figure Tool desktop bootstrap protocol is unsupported.")
    cookie_name = str(payload.get("cookie_name") or "")
    cookie_value = str(payload.get("cookie_value") or "")
    parent_pid = int(payload.get("parent_pid") or 0)
    if not re.fullmatch(r"FigureStudio_[a-f0-9]{16}", cookie_name):
        raise RuntimeError("Figure Tool desktop session name is invalid.")
    if len(cookie_value) < 43 or not re.fullmatch(r"[A-Za-z0-9_-]+", cookie_value):
        raise RuntimeError("Figure Tool desktop session secret has insufficient entropy.")
    if parent_pid <= 0:
        raise RuntimeError("Figure Tool desktop parent identity is invalid.")
    return cookie_name, cookie_value, parent_pid


def verify_desktop_payload_manifest(root: Path, expected_sha256: str) -> str:
    if not re.fullmatch(r"[a-f0-9]{64}", expected_sha256):
        raise RuntimeError("Figure Tool desktop payload digest is invalid.")
    manifest_path = root / "package-manifest.json"
    if not manifest_path.is_file() or manifest_path.is_symlink():
        raise RuntimeError("Figure Tool desktop payload manifest is missing.")
    actual = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    if not hmac.compare_digest(actual, expected_sha256):
        raise RuntimeError("Figure Tool desktop payload manifest differs from the host.")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema") != "figureStudio.payloadManifest.v1":
        raise RuntimeError("Figure Tool desktop payload manifest schema is unsupported.")
    core = manifest.get("core_biology") or {}
    if int(core.get("file_count", -1)) != 111 or int(core.get("svg_count", -1)) != 108:
        raise RuntimeError("Figure Tool desktop asset bundle is incomplete.")
    return actual


def verify_native_pdf_runtime_transaction() -> dict[str, object]:
    """Prove that the packaged native parser and compiler can commit one bounded edit."""

    import pikepdf

    source_stream = BytesIO()
    source_content = b"q 1 0 0 rg 1 1 m 5 1 l 5 5 l 1 5 l h f Q\n"
    with pikepdf.Pdf.new() as pdf:
        page = pdf.add_blank_page(page_size=(16, 12))
        page.obj["/Contents"] = pikepdf.Stream(pdf, source_content)
        pdf.save(source_stream, compress_streams=False)
    source_bytes = source_stream.getvalue()
    source_ir = build_native_pdf_ir_shadow_payload(source_bytes, "runtime-proof.pdf", 1)
    path_nodes = [row for row in source_ir.get("nodes") or [] if row.get("kind") == "path-paint"]
    if len(path_nodes) != 1:
        raise RuntimeError("The native PDF runtime proof did not index exactly one path.")
    source_node = path_nodes[0]
    instruction_ids = set((source_node.get("metadata") or {}).get("instruction_span_ids") or [])
    target_instruction = next(
        (
            row
            for row in source_ir.get("instructions") or []
            if row.get("instruction_id") in instruction_ids
            and row.get("operator") == "l"
            and row.get("normalized_operands") == [5, 1]
        ),
        None,
    )
    if target_instruction is None:
        raise RuntimeError("The native PDF runtime proof could not resolve its exact path operand.")
    physical_stream_refs = target_instruction.get("physical_stream_refs") or []
    target_stream = next(
        (
            row
            for row in source_ir.get("stream_segments") or []
            if row.get("physical_stream_ref") in physical_stream_refs
        ),
        None,
    )
    if target_stream is None:
        raise RuntimeError("The native PDF runtime proof could not resolve its physical content stream.")
    packet = {
        "schema": "figureStudio.nativePdfTypedTransactionPacket.v1",
        "source_revision_id": (source_ir.get("source") or {}).get("source_revision_id"),
        "transactions": [{
            "schema": "figureStudio.nativePdfTransaction.MovePathAnchor.v1",
            "transaction_id": "runtime-proof-move-path-anchor",
            "type": "MovePathAnchor",
            "page_number": source_node.get("page_number"),
            "node_id": source_node.get("id"),
            "expected_source_fingerprint": (source_node.get("metadata") or {}).get(
                "source_operator_fingerprint"
            ),
            "instruction_id": target_instruction.get("instruction_id"),
            "instruction_ordinal": target_instruction.get("ordinal"),
            "physical_stream_ref": target_stream.get("physical_stream_ref"),
            "physical_stream_sha256": target_stream.get("decoded_stream_sha256"),
            "operand_index": 0,
            "expected_lexeme": "5",
            "expected_value": 5,
            "replacement_value": 6,
            "replacement_lexeme": "6",
            "fallback_policy": "reject",
        }],
        "proof_policy": {
            "output_reparse": "required",
            "structural": "target-only",
            "visual": "required",
            "full_native_equivalence": False,
        },
    }
    result = compile_native_pdf_packet(source_bytes, "runtime-proof.pdf", packet)
    proof = result.get("proof") if isinstance(result.get("proof"), dict) else {}
    if not (
        result.get("ok") is True
        and result.get("schema") == "figureStudio.nativePdfTypedCompileResult.v1"
        and len(result.get("transactions") or []) == 1
        and proof.get("all_required_proofs_passed") is True
        and (proof.get("structural") or {}).get("passed") is True
        and (proof.get("reparse") or {}).get("passed") is True
        and (proof.get("visual_diff") or {}).get("passed") is True
    ):
        raise RuntimeError("The native PDF runtime proof did not pass its compiler proof gates.")
    output_bytes = base64.b64decode(str(result.get("pdfBase64") or ""), validate=True)
    output_ir = build_native_pdf_ir_shadow_payload(output_bytes, "runtime-proof-output.pdf", 1)
    output_instruction_found = any(
        row.get("operator") == "l" and row.get("normalized_operands") == [6, 1]
        for row in output_ir.get("instructions") or []
    )
    if output_bytes == source_bytes or not output_instruction_found:
        raise RuntimeError("The native PDF runtime proof did not retain the committed path mutation.")
    return {
        "nativePdfIrProof": True,
        "nativePdfMutationProof": True,
        "nativePdfMutationProofTransaction": "one-page-move-path-anchor",
        "nativePdfMutationProofOutputBytes": len(output_bytes),
    }


def verify_pdfium_runtime_transaction() -> dict[str, object]:
    """Prove that the bundled PDFium library can parse and render PDF bytes."""

    import pikepdf
    import pypdfium2 as pdfium

    source = BytesIO()
    with pikepdf.Pdf.new() as pdf:
        page = pdf.add_blank_page(page_size=(16, 12))
        page.obj["/Contents"] = pikepdf.Stream(pdf, b"q 1 0 0 rg 1 1 4 4 re f Q\n")
        pdf.save(source)
    document = pdfium.PdfDocument(source.getvalue())
    rendered_page = None
    bitmap = None
    try:
        if len(document) != 1:
            raise RuntimeError("The installed PDF proof engine could not parse a one-page PDF.")
        rendered_page = document[0]
        bitmap = rendered_page.render(scale=1)
        width = int(getattr(bitmap, "width", 0) or 0)
        height = int(getattr(bitmap, "height", 0) or 0)
        if width != 16 or height != 12:
            raise RuntimeError("The installed PDF proof engine returned an invalid page render.")
    finally:
        if bitmap is not None:
            bitmap.close()
        if rendered_page is not None:
            rendered_page.close()
        document.close()
    return {
        "pdfVisualProof": True,
        "pdfVisualProofEngine": "pypdfium2/PDFium",
        "pdfVisualProofTransaction": "one-page-parse-and-render",
        "pypdfium2Version": str(getattr(pdfium, "PYPDFIUM_INFO", "") or ""),
        "pdfiumVersion": str(getattr(pdfium, "PDFIUM_INFO", "") or ""),
    }


def preload_desktop_runtime_dependencies() -> dict[str, object]:
    """Load native libraries on the runtime main thread before serving requests."""
    try:
        from fontTools.ttLib import TTFont  # noqa: F401 - verifies the packaged outline engine
        import pikepdf
        import pypdfium2 as pdfium  # noqa: F401 - verifies the packaged proof engine
    except ImportError as error:
        raise RuntimeError(
            "The installed Figure Tool PDF/vector runtime is incomplete. Repair or reinstall Figure Tool."
        ) from error
    pdfium_payload = verify_pdfium_runtime_transaction()
    native_pdf_payload = verify_native_pdf_runtime_transaction()
    return {
        "ok": True,
        "pdfImport": True,
        "pdfImportEngine": "PDF.js",
        "nativePdfIrShadow": True,
        "nativePdfIrParser": "pikepdf/QPDF",
        "nativePdfMutation": True,
        "nativePdfMutationEngine": "pikepdf/QPDF",
        "pikepdfVersion": str(getattr(pikepdf, "__version__", "") or ""),
        "qpdfVersion": str(getattr(pikepdf, "__libqpdf_version__", "") or ""),
        **native_pdf_payload,
        **pdfium_payload,
        "textOutlines": True,
        # Stable capabilities API profile identifier; this is not the product display version.
        "runtimeProfile": "figure-studio-standalone-0.9",
    }


def main() -> int:
    args = parse_args()
    if args.runtime_proof:
        print(json.dumps({"ok": True, **preload_desktop_runtime_dependencies()}, separators=(",", ":")))
        return 0
    root = args.root.resolve()
    if not root.is_dir():
        raise RuntimeError(f"Figure Tool server root is unavailable: {root}")
    cookie_name = ""
    cookie_value = ""
    manifest_sha256 = ""
    desktop_capabilities: dict[str, object] | None = None
    if args.desktop_sidecar:
        if args.bind != "127.0.0.1":
            raise RuntimeError("Figure Tool desktop runtime may bind only to 127.0.0.1.")
        cookie_name, cookie_value, _parent_pid = desktop_bootstrap()
        manifest_sha256 = verify_desktop_payload_manifest(root, args.payload_manifest_sha256)
        desktop_capabilities = preload_desktop_runtime_dependencies()
    mimetypes.add_type("application/javascript", ".mjs")
    handler = lambda *handler_args, **handler_kwargs: FigureStudioHandler(  # noqa: E731
        *handler_args,
        directory=str(root),
        desktop_cookie_name=cookie_name,
        desktop_cookie_value=cookie_value,
        desktop_capabilities=desktop_capabilities,
        **handler_kwargs,
    )
    server = ThreadingHTTPServer((args.bind, args.port), handler)
    actual_port = int(server.server_address[1])
    if args.desktop_sidecar:
        print(json.dumps({
            "protocol": DESKTOP_READY_PROTOCOL,
            "origin": f"http://127.0.0.1:{actual_port}",
            "port": actual_port,
            "pid": os.getpid(),
            "payload_manifest_sha256": manifest_sha256,
            "endpoints": DESKTOP_ENDPOINTS,
        }, separators=(",", ":")), flush=True)

        def monitor_desktop_control() -> None:
            raw = sys.stdin.readline(16 * 1024)
            try:
                payload = json.loads(raw) if raw else {}
            except json.JSONDecodeError:
                payload = {}
            if not raw or payload.get("protocol") == DESKTOP_SHUTDOWN_PROTOCOL:
                server.shutdown()

        threading.Thread(target=monitor_desktop_control, daemon=True).start()
    else:
        print(f"Figure Tool server root: {root}")
        print(f"Serving Figure Tool at http://{args.bind}:{actual_port}")
        print("PDF page preview: browser PDF.js")
        print("PDF source font endpoint: /api/pdf-source-fonts")
        print("Native PDF IR shadow endpoint: /api/pdf-native-ir-shadow")
        print("Native PDF roundtrip endpoint: /api/pdf-native-roundtrip")
        print("Native PDF compile endpoint: /api/pdf-native-compile")
        print("Native PDF mutation endpoint: /api/pdf-native-mutate")
        print("Text outline endpoint: /api/text-to-path")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Stopping Figure Tool server.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
