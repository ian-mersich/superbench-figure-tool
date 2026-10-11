(function (root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  root.FigureStudioNativePdfIrMaterializer = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  const SOURCE_SCHEMA = "figureStudio.nativePdfIrShadow.v1";
  const DESCRIPTOR_TREE_SCHEMA = "figureStudio.nativePdfDescriptorTree.v1";
  const MATERIALIZATION_SCHEMA = "figureStudio.nativePdfIrMaterialization.v1";
  const SUPPORTED_NODE_KINDS = Object.freeze(["text-run"]);
  const MAX_NATIVE_PDF_DESCRIPTORS = 240;
  const APPROVED_TEXT_OPERATORS = Object.freeze(["Tj", "TJ", "'", '"']);
  const QUOTE_TEXT_OPERATORS = new Set(["'", '"']);
  const APPROVED_FONT_WRITE_PROFILES = Object.freeze([
    "supported-bounded-single-byte",
    "supported-proven-single-byte-code-map"
  ]);

  function clone(value) {
    return value == null ? value : JSON.parse(JSON.stringify(value));
  }

  function finite(value, fallback = 0) {
    const number = Number(value);
    return Number.isFinite(number) ? number : fallback;
  }

  function positive(value, fallback = 0) {
    const number = finite(value, fallback);
    return number > 0 ? number : fallback;
  }

  function isFiniteMatrix(value) {
    return Array.isArray(value)
      && value.length === 6
      && value.every((item) => typeof item === "number" && Number.isFinite(item));
  }

  function matricesMatch(left, right, tolerance = 1e-9) {
    return isFiniteMatrix(left)
      && isFiniteMatrix(right)
      && left.every((value, index) => Math.abs(value - right[index]) <= tolerance);
  }

  function sameInvocationPath(left, right) {
    return Array.isArray(left)
      && Array.isArray(right)
      && left.length === right.length
      && left.every((value, index) => value === right[index]);
  }

  function matrix(value) {
    if (!isFiniteMatrix(value)) throw new TypeError("An affine matrix must contain exactly six finite numeric primitive values.");
    return value.slice();
  }

  // Mirrors pdf_native.parser._multiply_matrix. PDF coordinates use row-vector
  // affine matrices: text space is applied before the current transformation.
  function multiplyMatrix(leftValue, rightValue) {
    const [a, b, c, d, e, f] = matrix(leftValue);
    const [g, h, i, j, k, l] = matrix(rightValue);
    return [
      a * g + b * i,
      a * h + b * j,
      c * g + d * i,
      c * h + d * j,
      e * g + f * i + k,
      e * h + f * j + l
    ];
  }

  function transformPoint(matrixValue, x, y) {
    const [a, b, c, d, e, f] = matrix(matrixValue);
    return {
      x: finite(x) * a + finite(y) * c + e,
      y: finite(x) * b + finite(y) * d + f
    };
  }

  function xrefNumber(value) {
    const match = /^\s*(\d+)\s+\d+\s+R\s*$/.exec(String(value || ""));
    return match ? Number(match[1]) : 0;
  }

  function normalizePageSize(options = {}) {
    const source = options.sourcePageSize || options.source_page_size || {};
    const x0 = finite(source.x0 ?? source.left, 0);
    const y0 = finite(source.y0 ?? source.bottom, 0);
    const explicitWidth = positive(source.width ?? options.pageWidth ?? options.page_width, 0);
    const explicitHeight = positive(source.height ?? options.pageHeight ?? options.page_height, 0);
    const x1 = finite(source.x1 ?? source.right, x0 + explicitWidth);
    const y1 = finite(source.y1 ?? source.top, y0 + explicitHeight);
    const width = explicitWidth || positive(x1 - x0, 612);
    const height = explicitHeight || positive(y1 - y0, 792);
    const rotation = finite(source.rotation ?? options.rotation, 0);
    return { x0, y0, x1: x0 + width, y1: y0 + height, width, height, rotation, units: "pt" };
  }

  function coordinateBasis(options, pageSize) {
    const source = options.sourcePageSize || options.source_page_size || {};
    const candidate = options.viewportTransform || options.viewport_transform
      || source.viewportTransform || source.viewport_transform;
    const width = positive(options.viewportWidth ?? options.viewport_width ?? source.viewportWidth ?? source.viewport_width, pageSize.width);
    const height = positive(options.viewportHeight ?? options.viewport_height ?? source.viewportHeight ?? source.viewport_height, pageSize.height);
    if (candidate != null) {
      if (!isFiniteMatrix(candidate)) return { valid: false, blocker: "malformed-pdfjs-viewport-transform" };
      const transform = candidate.slice();
      const determinant = transform[0] * transform[3] - transform[1] * transform[2];
      if (Math.abs(determinant) <= 1e-12 || !width || !height) {
        return { valid: false, blocker: "degenerate-pdfjs-viewport-transform" };
      }
      return {
        valid: true,
        schema: "figureStudio.pdfJsViewportCoordinateBasis.v1",
        source_box: { x0: pageSize.x0, y0: pageSize.y0, x1: pageSize.x1, y1: pageSize.y1 },
        viewport_transform: transform,
        viewport_width: width,
        viewport_height: height,
        rotation: finite(source.rotation ?? options.rotation, pageSize.rotation),
        provenance: "pdfjs-page-viewport"
      };
    }
    if (Math.abs(finite(pageSize.rotation, 0)) % 360 > 1e-9) {
      return { valid: false, blocker: "pdfjs-viewport-transform-required-for-rotated-page" };
    }
    return {
      valid: true,
      schema: "figureStudio.pdfJsViewportCoordinateBasis.v1",
      source_box: { x0: pageSize.x0, y0: pageSize.y0, x1: pageSize.x1, y1: pageSize.y1 },
      viewport_transform: [1, 0, 0, -1, -pageSize.x0, pageSize.y1],
      viewport_width: pageSize.width,
      viewport_height: pageSize.height,
      rotation: 0,
      provenance: "derived-unrotated-page-box"
    };
  }

  function colorChannel(value) {
    return Math.max(0, Math.min(255, Math.round(finite(value) * 255)));
  }

  function rgbHex(red, green, blue) {
    return `#${[red, green, blue].map((value) => colorChannel(value).toString(16).padStart(2, "0")).join("")}`;
  }

  function fillColorCss(state = {}) {
    const values = Array.isArray(state.fill_color) ? state.fill_color.map(Number) : [];
    const space = String(state.fill_color_space || "DeviceGray");
    if (space === "DeviceRGB" && values.length >= 3) return rgbHex(values[0], values[1], values[2]);
    if (space === "DeviceCMYK" && values.length >= 4) {
      const [cyan, magenta, yellow, black] = values.map((value) => Math.max(0, Math.min(1, finite(value))));
      return rgbHex(
        1 - Math.min(1, cyan * (1 - black) + black),
        1 - Math.min(1, magenta * (1 - black) + black),
        1 - Math.min(1, yellow * (1 - black) + black)
      );
    }
    const gray = values.length ? Math.max(0, Math.min(1, finite(values[0]))) : 0;
    return rgbHex(gray, gray, gray);
  }

  function normalizedVector(x, y, fallback = { x: 1, y: 0 }) {
    const length = Math.hypot(finite(x), finite(y));
    return length > 1e-9 ? { x: x / length, y: y / length, length } : { ...fallback, length: 1 };
  }

  function textAdvance(node, state, combined, text) {
    const metadata = node.metadata || {};
    const fontSize = positive(state.font_size, 10);
    const horizontalScale = Math.max(0.01, Math.abs(finite(state.horizontal_scale, 100)) / 100);
    const textScale = normalizedVector(combined[0], combined[1]).length;
    const mappedWidths = Array.isArray(metadata.text_segment_advances)
      ? metadata.text_segment_advances.map(Number).filter(Number.isFinite)
      : [];
    let advance = mappedWidths.length
      ? mappedWidths.reduce((sum, value) => sum + value, 0) / 1000 * fontSize
      : Math.max(1, Array.from(text).length) * fontSize * 0.55;
    const operands = metadata.normalized_operands;
    const arrayOperand = Array.isArray(operands) && Array.isArray(operands[0]) ? operands[0] : [];
    const positioningAdjustment = arrayOperand
      .filter((value) => Number.isFinite(Number(value)))
      .reduce((sum, value) => sum - Number(value) / 1000 * fontSize, 0);
    const characters = Array.from(text);
    const spacingAdjustment = finite(state.character_spacing, 0) * characters.length
      + finite(state.word_spacing, 0) * characters.filter((value) => value === " ").length;
    advance = Math.max(fontSize * 0.2, advance + positioningAdjustment + spacingAdjustment);
    return advance * horizontalScale * textScale;
  }

  function textGeometry(node, coordinateSpace) {
    const metadata = node.metadata || {};
    const state = metadata.graphics_state || {};
    const combined = multiplyMatrix(state.text_matrix, state.ctm);
    const baselinePdf = transformPoint(combined, 0, finite(state.text_rise, 0));
    const along = normalizedVector(combined[0], combined[1]);
    const up = normalizedVector(combined[2], combined[3], { x: -along.y, y: along.x });
    const fontSize = positive(state.font_size, 10);
    const renderedFontSize = fontSize * up.length;
    const text = String(metadata.decoded_text || "");
    const advance = textAdvance(node, state, combined, text);
    const ascent = renderedFontSize * 0.86;
    const descent = renderedFontSize * 0.24;
    const corners = [
      { along: 0, up: -descent },
      { along: advance, up: -descent },
      { along: 0, up: ascent },
      { along: advance, up: ascent }
    ].map((offset) => ({
      x: baselinePdf.x + along.x * offset.along + up.x * offset.up,
      y: baselinePdf.y + along.y * offset.along + up.y * offset.up
    })).map((point) => transformPoint(coordinateSpace.viewport_transform, point.x, point.y));
    const baselineViewport = transformPoint(coordinateSpace.viewport_transform, baselinePdf.x, baselinePdf.y);
    const directionEndpoint = transformPoint(
      coordinateSpace.viewport_transform,
      baselinePdf.x + along.x,
      baselinePdf.y + along.y
    );
    const viewportDirection = normalizedVector(
      directionEndpoint.x - baselineViewport.x,
      directionEndpoint.y - baselineViewport.y
    );
    const xs = corners.map((point) => point.x);
    const ys = corners.map((point) => point.y);
    const x0 = Math.min(...xs);
    const y0 = Math.min(...ys);
    const x1 = Math.max(...xs);
    const y1 = Math.max(...ys);
    return {
      bbox: { x0, y0, x1, y1, width: x1 - x0, height: y1 - y0 },
      origin: { x: baselineViewport.x, y: baselineViewport.y },
      direction: {
        x: Math.abs(viewportDirection.x) < 1e-12 ? 0 : viewportDirection.x,
        y: Math.abs(viewportDirection.y) < 1e-12 ? 0 : viewportDirection.y
      },
      size: renderedFontSize,
      advance,
      combined_matrix: combined
    };
  }

  function invocationResolutionForNode(node, invocations) {
    const path = Array.isArray(node?.invocation_path) ? node.invocation_path : [];
    if (path.length <= 1) return { status: "page-owned", invocation: null };
    const matches = (Array.isArray(invocations) ? invocations : []).filter((row) => {
      const candidate = Array.isArray(row?.invocation_path) ? row.invocation_path : [];
      return candidate.length === path.length && candidate.every((value, index) => value === path[index]);
    });
    if (matches.length === 1) return { status: "exact", invocation: matches[0] };
    return { status: matches.length ? "ambiguous" : "missing", invocation: null };
  }

  function instructionForNode(node, instructions) {
    const ids = Array.isArray(node?.metadata?.instruction_span_ids) ? node.metadata.instruction_span_ids : [];
    if (ids.length !== 1) return null;
    const matches = (Array.isArray(instructions) ? instructions : []).filter((row) => (
      row?.instruction_id === ids[0]
      && sameInvocationPath(row?.invocation_path, node?.invocation_path)
    ));
    return matches.length === 1 ? matches[0] : null;
  }

  function exactOperandSpans(instruction, physicalStreamRef) {
    const spans = Array.isArray(instruction?.operand_spans) ? instruction.operand_spans : [];
    return spans.length > 0 && spans.every((span) => {
      const slices = Array.isArray(span?.physical_slices) ? span.physical_slices : [];
      return slices.length === 1
        && String(slices[0]?.physical_stream_ref || "") === physicalStreamRef
        && Number.isInteger(slices[0]?.local_start)
        && Number.isInteger(slices[0]?.local_end)
        && slices[0].local_end > slices[0].local_start;
    });
  }

  function textOperandShapeIsExact(instruction, operator) {
    const operands = Array.isArray(instruction?.normalized_operands) ? instruction.normalized_operands : [];
    const operandHex = Array.isArray(instruction?.operand_lexeme_hex) ? instruction.operand_lexeme_hex : [];
    if (operator === "Tj" || operator === "'") {
      return operands.length === 1 && typeof operands[0] === "string" && operandHex.length === 1 && Boolean(operandHex[0]);
    }
    if (operator === '"') {
      return operands.length === 3
        && typeof operands[0] === "number" && Number.isFinite(operands[0])
        && typeof operands[1] === "number" && Number.isFinite(operands[1])
        && typeof operands[2] === "string"
        && operandHex.length === 3 && operandHex.every(Boolean);
    }
    const values = operands.length === 1 && Array.isArray(operands[0]) ? operands[0] : [];
    return operator === "TJ"
      && values.length > 0
      && values.some((value) => typeof value === "string")
      && values.every((value) => typeof value === "string" || (typeof value === "number" && Number.isFinite(value)))
      && operandHex.length === 1 && Boolean(operandHex[0]);
  }

  function followingTextPositionIsIsolated(instruction, instructions) {
    if (!instruction) return false;
    const rows = (Array.isArray(instructions) ? instructions : [])
      .filter((row) => sameInvocationPath(row?.invocation_path, instruction.invocation_path))
      .sort((left, right) => Number(left?.ordinal || 0) - Number(right?.ordinal || 0));
    const targetIndex = rows.findIndex((row) => row?.instruction_id === instruction.instruction_id);
    if (targetIndex < 0) return false;
    const resetOperators = new Set(["ET", "BT", "Tm", "Td", "TD", "T*", "'", '"']);
    const textShowOperators = new Set(["Tj", "TJ", "'", '"']);
    for (const row of rows.slice(targetIndex + 1)) {
      const operator = String(row?.operator || "");
      if (resetOperators.has(operator)) return true;
      if (textShowOperators.has(operator)) return false;
    }
    return true;
  }

  function quoteStateTransitionIsProven(metadata, operator) {
    if (!QUOTE_TEXT_OPERATORS.has(operator)) return true;
    const state = metadata?.graphics_state || {};
    const sideEffects = metadata?.text_show_side_effects || {};
    const transition = metadata?.text_show_state_transition || {};
    if (
      sideEffects.line_advance !== true
      || sideEffects.sets_word_and_character_spacing !== (operator === '"')
      || transition.status !== "proven"
      || transition.composition !== "text-space-translation-left-multiplied"
      || transition.line_translation_applied !== true
      || typeof transition.leading !== "number"
      || !Number.isFinite(transition.leading)
      || !isFiniteMatrix(transition.text_matrix_before)
      || !isFiniteMatrix(transition.text_line_matrix_before)
      || !isFiniteMatrix(transition.expected_text_line_matrix_after)
      || !isFiniteMatrix(transition.text_matrix_after)
      || !isFiniteMatrix(transition.text_line_matrix_after)
    ) return false;
    const expected = multiplyMatrix(
      [1, 0, 0, 1, 0, -transition.leading],
      transition.text_line_matrix_before
    );
    if (
      !matricesMatch(expected, transition.expected_text_line_matrix_after)
      || !matricesMatch(expected, transition.text_matrix_after)
      || !matricesMatch(expected, transition.text_line_matrix_after)
      || !matricesMatch(state.text_matrix, transition.text_matrix_after)
      || !matricesMatch(state.text_line_matrix, transition.text_line_matrix_after)
    ) return false;
    const spacingValues = Array.isArray(transition.spacing_operand_values) ? transition.spacing_operand_values : [];
    if (operator === '"') {
      return spacingValues.length === 2
        && spacingValues.every((value) => typeof value === "number" && Number.isFinite(value))
        && typeof state.word_spacing === "number" && state.word_spacing === spacingValues[0]
        && typeof state.character_spacing === "number" && state.character_spacing === spacingValues[1]
        && transition.word_spacing_after === spacingValues[0]
        && transition.character_spacing_after === spacingValues[1];
    }
    return spacingValues.length === 0
      && transition.word_spacing_after === transition.word_spacing_before
      && transition.character_spacing_after === transition.character_spacing_before;
  }

  function textWriteEligibility(node, invocations = [], instructions = []) {
    const metadata = node && node.metadata && typeof node.metadata === "object" ? node.metadata : {};
    const font = metadata.font && typeof metadata.font === "object" ? metadata.font : {};
    const codeMap = font.code_map && typeof font.code_map === "object" ? font.code_map : {};
    const operatorNames = Array.isArray(node && node.operator_names) ? node.operator_names.map(String) : [];
    const operator = String(metadata.text_operator || (operatorNames.length === 1 ? operatorNames[0] : ""));
    const reasons = [];
    if (!node || node.kind !== "text-run") reasons.push("unsupported-node-kind");
    if (!String(node && node.id || "")) reasons.push("stable-node-id-required");
    if (node?.identity_status !== "stable" || node?.identity_confidence !== "high") reasons.push("stable-high-confidence-identity-required");
    if (metadata.write_candidate !== true) reasons.push("explicit-write-candidate-required");
    if (metadata.operator_span_exact !== true) reasons.push("exact-operator-span-required");
    if (!APPROVED_TEXT_OPERATORS.includes(operator)) reasons.push("approved-text-operator-required");
    if (!Array.isArray(metadata.instruction_span_ids) || metadata.instruction_span_ids.length !== 1) reasons.push("single-instruction-span-required");
    const instruction = instructionForNode(node, instructions);
    if (!instruction) {
      reasons.push("exact-source-instruction-required");
    } else {
      if (instruction.operator !== operator || instruction.write_candidate !== true || instruction.exact !== true) {
        reasons.push("exact-write-candidate-instruction-required");
      }
      const physicalStreamRef = String(metadata.source_span?.physical_stream_ref || "");
      if (!physicalStreamRef || !exactOperandSpans(instruction, physicalStreamRef)) reasons.push("exact-operand-byte-spans-required");
      if (!textOperandShapeIsExact(instruction, operator)) reasons.push("exact-text-operand-shape-required");
      if (!followingTextPositionIsIsolated(instruction, instructions)) reasons.push("dependent-following-text-run");
    }
    if (metadata.text_decode_status !== "proven") reasons.push("proven-text-decode-required");
    if (!String(metadata.decoded_text || "").trim()) reasons.push("nonblank-text-required");
    const graphicsStateComplete = metadata.graphics_state_complete === true
      && isFiniteMatrix(metadata.graphics_state?.text_matrix)
      && isFiniteMatrix(metadata.graphics_state?.ctm);
    if (!graphicsStateComplete) {
      reasons.push("complete-finite-graphics-state-required");
    } else {
      const combined = multiplyMatrix(metadata.graphics_state.text_matrix, metadata.graphics_state.ctm);
      const determinant = combined[0] * combined[3] - combined[1] * combined[2];
      if (Math.abs(determinant) <= 1e-12) reasons.push("nonsingular-combined-text-transform-required");
    }
    if (!String(node && node.resource_ref || "") || String(node.resource_ref) !== String(font.resource_ref || "")) {
      reasons.push("exact-font-resource-binding-required");
    }
    if (!APPROVED_FONT_WRITE_PROFILES.includes(String(font.write_support || ""))) {
      reasons.push("approved-single-byte-font-profile-required");
    } else if (font.write_support === "supported-bounded-single-byte" && (font.subset === true || font.cid_font === true || font.subtype === "Type0")) {
      reasons.push("bounded-nonsubset-simple-font-required");
    } else if (font.write_support === "supported-proven-single-byte-code-map" && (
      font.cid_font === true
      || font.subtype === "Type0"
      || codeMap.status !== "proven-single-byte-to-unicode"
      || Number(codeMap.source_code_bytes) !== 1
      || !String(codeMap.digest || "")
    )) {
      reasons.push("proven-single-byte-code-map-required");
    }
    const invocation = invocationResolutionForNode(node, invocations);
    if (QUOTE_TEXT_OPERATORS.has(operator) && (Array.isArray(node?.invocation_path) ? node.invocation_path.length : 0) !== 1) {
      reasons.push("page-owned-quote-text-required");
    }
    if (!quoteStateTransitionIsProven(metadata, operator)) reasons.push("proven-quote-text-state-transition-required");
    if (invocation.status === "missing") reasons.push("exact-form-invocation-path-required");
    if (invocation.status === "ambiguous") reasons.push("unique-form-invocation-path-required");
    return { eligible: reasons.length === 0, reasons, operator, invocation: invocation.invocation };
  }

  function fontResourceRows(ir) {
    const rows = [];
    const keys = new Set();
    for (const scope of Array.isArray(ir.resource_scopes) ? ir.resource_scopes : []) {
      for (const binding of Array.isArray(scope && scope.bindings) ? scope.bindings : []) {
        if (binding && binding.category !== "font") continue;
        const font = binding.font && typeof binding.font === "object" ? binding.font : {};
        const ref = String(binding.target_ref || font.resource_ref || "");
        const resourceXref = xrefNumber(ref);
        const key = `${scope.scope_id || ""}:${binding.resource_name || binding.name || ""}:${ref}`;
        if (keys.has(key)) continue;
        keys.add(key);
        const codeMap = font.code_map && typeof font.code_map === "object" ? font.code_map : {};
        rows.push({
          id: resourceXref ? `font-xref-${resourceXref}` : `font-${rows.length + 1}`,
          xref: resourceXref,
          ref,
          resource_name: String(binding.resource_name || binding.name || font.resource_name || ""),
          resource_scope_id: String(scope.scope_id || ""),
          resource_owner_ref: String(scope.owner_ref || ""),
          resource_dictionary_ref: String(scope.resource_dictionary_ref || ""),
          base_font: String(font.base_font || ""),
          type: String(font.subtype || ""),
          encoding: String(font.encoding || ""),
          subset: font.subset === true,
          embedded: Boolean(codeMap.embedded_program_ref),
          embedded_status: codeMap.embedded_program_ref ? "embedded-program-retained" : "not-proven",
          to_unicode_status: codeMap.to_unicode_ref ? "embedded-cmap" : "not-available",
          cid_font: font.cid_font === true,
          cid_encoding: font.cid_font === true ? String(font.encoding || "") : "",
          source: "qpdf-native-ir-resource-binding"
        });
      }
    }
    return rows;
  }

  function textDescriptor(node, ir, coordinateSpace, sharedDefinitions, evaluatedEligibility = null) {
    const metadata = node && node.metadata && typeof node.metadata === "object" ? node.metadata : {};
    const font = metadata.font && typeof metadata.font === "object" ? metadata.font : {};
    const text = String(metadata.decoded_text || "");
    const state = metadata.graphics_state && typeof metadata.graphics_state === "object" ? metadata.graphics_state : {};
    const eligibility = evaluatedEligibility || textWriteEligibility(node);
    if (!eligibility.eligible || !coordinateSpace?.valid) return null;
    const geometry = textGeometry(node, coordinateSpace);
    const invocation = eligibility.invocation;
    const nodeResourceRef = String(node.resource_ref || "");
    const fontResourceRef = String(font.resource_ref || "");
    const resourceXref = xrefNumber(fontResourceRef || nodeResourceRef);
    const definitionId = String(invocation && invocation.definition_id || "");
    const sharedDefinition = Boolean(definitionId && sharedDefinitions.get(definitionId) > 1);
    const baseFont = String(font.base_font || font.resource_name || "");
    const flags = (/bold|black|semibold/i.test(baseFont) ? 16 : 0) | (/italic|oblique/i.test(baseFont) ? 2 : 0);
    const codeMap = font.code_map && typeof font.code_map === "object" ? font.code_map : {};
    return {
      id: String(node.id),
      stable_object_id: String(node.id),
      native_kind: "text",
      source: "qpdf-native-ir-text-run",
      source_node_kind: "text-run",
      source_ir_schema: String(ir.schema || ""),
      source_revision_id: String(ir.source && ir.source.source_revision_id || ""),
      page_number: Number(node.page_number || ir.source && ir.source.page_number || 1),
      bbox: geometry.bbox,
      line_bbox: geometry.bbox,
      origin: geometry.origin,
      direction: geometry.direction,
      writing_mode: 0,
      text,
      font: baseFont,
      font_subset: font.subset === true,
      size: geometry.size,
      flags,
      char_flags: 0,
      ascender: 0.86,
      descender: -0.24,
      alpha: Math.round(Math.max(0, Math.min(1, finite(state.fill_alpha, 1))) * 255),
      color: parseInt(fillColorCss(state).slice(1), 16),
      color_css: fillColorCss(state),
      advance: geometry.advance,
      reconstruction_status: "editable-with-font-review",
      geometry_status: "derived-from-qpdf-text-and-graphics-state",
      coordinate_basis: clone(coordinateSpace),
      geometry_exact_for_source_write: false,
      content_stream_scope: (Array.isArray(node.invocation_path) ? node.invocation_path.length : 0) > 1
        ? "form-xobject-content-stream"
        : "page-content-stream",
      owner_xobject_id: definitionId,
      owner_xobject_xref: Number(invocation && invocation.form_xref || xrefNumber(invocation && invocation.form_ref)),
      owner_xobject_name: String(invocation && invocation.resource_name || ""),
      owner_xobject_invocation_id: String(invocation && invocation.invocation_id || ""),
      owner_xobject_invocation_path: invocation ? invocation.invocation_path.join("/") : "",
      owner_xobject_parent_invocation_id: String(invocation && invocation.parent_invocation_id || ""),
      owner_xobject_nesting_depth: invocation ? Math.max(0, invocation.invocation_path.length - 1) : 0,
      owner_xobject_page_ctm: invocation ? matrix(state.ctm) : [],
      owner_xobject_shared_definition: sharedDefinition,
      owner_xobject_per_instance_write: Boolean(invocation),
      owner_xobject_invocation_status: invocation ? "exact-form-font-and-bounds" : "page-owned",
      font_resource_id: resourceXref ? `font-xref-${resourceXref}` : "",
      font_resource_xref: resourceXref,
      font_resource_subset: font.subset === true,
      font_resource_embedded: Boolean(codeMap.embedded_program_ref),
      font_resource_association_status: resourceXref && fontResourceRef && nodeResourceRef && fontResourceRef === nodeResourceRef
        ? "proven-single-tf-binding-native-syntax"
        : "unverified",
      font_resource_embedded_status: codeMap.embedded_program_ref ? "embedded-program-retained" : "not-proven",
      font_resource_to_unicode_status: codeMap.to_unicode_ref ? "embedded-cmap" : "not-available",
      font_resource_cid_font: font.cid_font === true,
      font_resource_cid_encoding: font.cid_font === true ? String(font.encoding || "") : "",
      full_native_equivalence: false
    };
  }

  function nativePathCommands(node) {
    const rows = Array.isArray(node?.metadata?.path_commands) ? node.metadata.path_commands : [];
    const commands = [];
    let currentPoint = null;
    let subpathStart = null;
    for (const row of rows) {
      const operator = String(row?.operator || "").toLowerCase();
      const operands = Array.isArray(row?.operands) ? row.operands.map(Number) : [];
      if (operands.some((value) => !Number.isFinite(value))) return [];
      if (operator === "m" && operands.length === 2) {
        commands.push(["M", ...operands]);
        currentPoint = [...operands];
        subpathStart = [...operands];
      } else if (operator === "l" && operands.length === 2 && currentPoint) {
        commands.push(["L", ...operands]);
        currentPoint = [...operands];
      } else if (operator === "c" && operands.length === 6 && currentPoint) {
        commands.push(["C", ...operands]);
        currentPoint = operands.slice(4, 6);
      } else if (operator === "v" && operands.length === 4 && currentPoint) {
        commands.push(["C", ...currentPoint, ...operands]);
        currentPoint = operands.slice(2, 4);
      } else if (operator === "y" && operands.length === 4 && currentPoint) {
        commands.push(["C", ...operands, operands[2], operands[3]]);
        currentPoint = operands.slice(2, 4);
      } else if (operator === "h" && operands.length === 0 && subpathStart) {
        commands.push(["Z"]);
        currentPoint = [...subpathStart];
      } else if (operator === "re" && operands.length === 4) {
        const [x, y, width, height] = operands;
        commands.push(["M", x, y], ["L", x + width, y], ["L", x + width, y + height], ["L", x, y + height], ["Z"]);
        currentPoint = [x, y];
        subpathStart = [x, y];
      } else {
        return [];
      }
    }
    return commands;
  }

  function eligibleNativePathNode(node) {
    const metadata = node?.metadata || {};
    const streamRef = String(metadata.source_span?.physical_stream_ref || "");
    return node?.kind === "path-paint"
      && node.identity_status === "stable"
      && node.identity_confidence === "high"
      && metadata.write_candidate === true
      && metadata.operator_span_exact === true
      && xrefNumber(streamRef) > 0
      && nativePathCommands(node).length > 0;
  }

  function nativePathOperatorRuns(node) {
    const metadata = node.metadata || {};
    const commands = nativePathCommands(node);
    const firstOperatorIndex = Math.max(0, Number(node.operator_start || 0) || 0);
    const lastOperatorIndex = Math.max(firstOperatorIndex, Number(node.operator_end || firstOperatorIndex + 1) - 1);
    const pathSequence = {
      first_operator_index: firstOperatorIndex,
      last_operator_index: lastOperatorIndex,
      command_count: commands.length,
      commands
    };
    return (metadata.path_commands || []).map((command, index) => ({
      id: `${String(node.id || `native-path-${firstOperatorIndex}`)}:command-${index}`,
      operator: String(command?.operator || node.operator_names?.[index] || ""),
      category: "path",
      operator_index: firstOperatorIndex + index,
      byte_offset: Math.max(0, Number(metadata.source_span?.decoded_byte_start || 0) || 0),
      path_sequence: clone(pathSequence),
      typed_native_node_id: String(node.id || "")
    }));
  }

  function nativePathResources(ir, nodes) {
    const pageNodes = nodes.filter((node) => !Array.isArray(node.invocation_path) || node.invocation_path.length <= 1);
    const formNodes = nodes.filter((node) => Array.isArray(node.invocation_path) && node.invocation_path.length > 1);
    const groupByXref = (rows) => rows.reduce((groups, node) => {
      const xref = xrefNumber(node.metadata?.source_span?.physical_stream_ref) || Number(node.stream_ref?.xref || 0) || 0;
      if (!xref) return groups;
      if (!groups.has(xref)) groups.set(xref, []);
      groups.get(xref).push(node);
      return groups;
    }, new Map());
    const contentStreams = [...groupByXref(pageNodes)].map(([xref, rows]) => ({
      id: `content-stream-xref-${xref}`,
      xref,
      byte_length: Math.max(0, ...rows.map((node) => Number(node.metadata?.source_span?.decoded_byte_end || 0) || 0)),
      operator_runs: rows.flatMap(nativePathOperatorRuns)
    }));
    const formGroups = groupByXref(formNodes);
    const definitions = Array.isArray(ir.form_definitions) ? clone(ir.form_definitions) : [];
    const invocations = Array.isArray(ir.form_invocations) ? clone(ir.form_invocations) : [];
    const xobjects = [...formGroups].map(([xref, rows]) => {
      const definition = definitions.find((row) => Number(row?.form_xref || xrefNumber(row?.form_ref)) === xref) || {};
      const uses = invocations.filter((row) => Number(row?.form_xref || xrefNumber(row?.form_ref)) === xref);
      const firstState = rows[0]?.metadata?.graphics_state || {};
      return {
        id: String(definition.definition_id || `form-xobject-xref-${xref}`),
        xref,
        name: String(uses[0]?.resource_name || `Fm${xref}`),
        xobject_subtype: "Form",
        editable_content_stream: true,
        byte_length: Math.max(0, Number(definition.decoded_byte_size || 0) || 0),
        page_ctm: isFiniteMatrix(firstState.ctm) ? clone(firstState.ctm) : [1, 0, 0, 1, 0, 0],
        invocation_count: uses.length,
        shared_definition: uses.length > 1,
        per_instance_native_write_supported: uses.length === 1,
        native_write_scope: uses.length === 1 ? "selected-form-invocation-clone" : "shared-form-definition-guarded",
        invocations: uses.map((row) => ({
          ...row,
          id: String(row.invocation_id || ""),
          page_ctm: isFiniteMatrix(firstState.ctm) ? clone(firstState.ctm) : [1, 0, 0, 1, 0, 0],
          shared_definition: uses.length > 1,
          per_instance_native_write_supported: uses.length === 1,
          native_write_scope: uses.length === 1 ? "selected-form-invocation-clone" : "shared-form-definition-guarded"
        })),
        operator_runs: rows.flatMap(nativePathOperatorRuns)
      };
    });
    return { contentStreams, xobjects, definitions, invocations };
  }

  function emptyTree(ir, pageSize, status, blockers = []) {
    const source = ir && typeof ir.source === "object" ? ir.source : {};
    return {
      schema: DESCRIPTOR_TREE_SCHEMA,
      schema_extensions: [MATERIALIZATION_SCHEMA],
      source_pdf_filename: String(source.filename || "uploaded.pdf"),
      source_revision_id: String(source.source_revision_id || ""),
      source_pdf_sha256: String(source.source_revision_id || ""),
      page_number: Math.max(1, Number(source.page_number || 1)),
      page_count: Math.max(1, Number(source.page_count || 1)),
      page_descriptor_id: `pdf-page:qpdf:${source.page_number || 1}:${String(source.page_ref || "unresolved")}`,
      page_xref: xrefNumber(source.page_ref),
      source_page_size: clone(pageSize),
      xref_length: 0,
      descriptor_limit: MAX_NATIVE_PDF_DESCRIPTORS,
      object_counts: {
        drawing_count: 0,
        text_span_count: 0,
        image_block_count: 0,
        descriptor_count: 0,
        omitted_descriptor_count: Array.isArray(ir && ir.nodes) ? ir.nodes.length : 0,
        omitted_eligible_descriptor_count: 0,
        content_stream_count: Array.isArray(ir && ir.logical_streams) ? ir.logical_streams.length : 0,
        xobject_count: Array.isArray(ir && ir.form_definitions) ? ir.form_definitions.length : 0,
        form_invocation_count: Array.isArray(ir && ir.form_invocations) ? ir.form_invocations.length : 0,
        nested_form_invocation_count: Array.isArray(ir && ir.form_invocations)
          ? ir.form_invocations.filter((row) => Array.isArray(row.invocation_path) && row.invocation_path.length > 2).length
          : 0
      },
      resources: { font_count: 0, xobject_count: 0, fonts: [], form_invocations: [], invocation_index: { form_invocations: [] } },
      descriptors: [],
      materialization: {
        schema: MATERIALIZATION_SCHEMA,
        status,
        engine: "qpdf-ir-product-adapter",
        source_schema: String(ir && ir.schema || ""),
        supported_node_kinds: [...SUPPORTED_NODE_KINDS],
        approved_text_operators: [...APPROVED_TEXT_OPERATORS],
        approved_font_write_profiles: [...APPROVED_FONT_WRITE_PROFILES],
        materialized_descriptor_count: 0,
        eligible_text_node_count: 0,
        descriptor_limit_applied: false,
        deferred_node_count: Array.isArray(ir && ir.nodes) ? ir.nodes.length : 0,
        deferred_node_kinds: [...new Set((Array.isArray(ir && ir.nodes) ? ir.nodes : []).map((row) => String(row && row.kind || "unknown")))].sort(),
        blockers: blockers.map(String),
        full_native_equivalence: false
      },
      capabilities: {
        native_object_identity: "qpdf-source-revision-native-nodes",
        product_descriptor_materialization: status,
        supported_node_kinds: [...SUPPORTED_NODE_KINDS],
        typed_text_transaction_supported: false,
        content_stream_mutation_supported: false,
        form_xobject_content_stream_mutation_supported: false,
        writer_required_for_native_equivalence: true,
        source_backed_roundtrip_required: true,
        full_native_equivalence: false
      }
    };
  }

  function materializeDescriptorTree(irValue, options = {}) {
    const ir = irValue && typeof irValue === "object" ? irValue : {};
    const pageSize = normalizePageSize(options);
    if (ir.schema !== SOURCE_SCHEMA) return emptyTree(ir, pageSize, "deferred", ["unsupported-source-ir-schema"]);
    if (ir.status !== "complete") return emptyTree(ir, pageSize, "deferred", [`source-ir-${ir.status || "unavailable"}`]);
    if (!/^[a-f0-9]{64}$/i.test(String(ir.source && ir.source.source_revision_id || ""))) {
      return emptyTree(ir, pageSize, "deferred", ["valid-source-revision-required"]);
    }
    const basis = coordinateBasis(options, pageSize);
    if (!basis.valid) return emptyTree(ir, pageSize, "deferred", [basis.blocker]);
    const nodes = Array.isArray(ir.nodes) ? ir.nodes : [];
    const invocations = Array.isArray(ir.form_invocations) ? ir.form_invocations : [];
    const sharedDefinitions = invocations.reduce((counts, row) => {
      const key = String(row && row.definition_id || "");
      if (key) counts.set(key, (counts.get(key) || 0) + 1);
      return counts;
    }, new Map());
    const instructions = Array.isArray(ir.instructions) ? ir.instructions : [];
    const evaluations = nodes.map((node) => ({ node, eligibility: textWriteEligibility(node, invocations, instructions) }));
    const eligibleRows = evaluations.filter((row) => row.eligibility.eligible);
    const eligibleNodes = eligibleRows.map((row) => row.node);
    const eligiblePathNodes = nodes.filter(eligibleNativePathNode);
    const descriptors = eligibleRows
      .slice(0, MAX_NATIVE_PDF_DESCRIPTORS)
      .map((row) => textDescriptor(row.node, ir, basis, sharedDefinitions, row.eligibility))
      .filter(Boolean);
    const fonts = fontResourceRows(ir);
    const hasMaterializedNodes = descriptors.length > 0 || eligiblePathNodes.length > 0;
    const tree = emptyTree(ir, pageSize, hasMaterializedNodes ? "materialized" : "deferred", hasMaterializedNodes ? [] : ["no-supported-text-run-nodes"]);
    tree.coordinate_basis = clone(basis);
    tree.source_page_size = {
      x0: 0,
      y0: 0,
      x1: basis.viewport_width,
      y1: basis.viewport_height,
      width: basis.viewport_width,
      height: basis.viewport_height,
      rotation: basis.rotation,
      units: "pt"
    };
    tree.descriptors = descriptors;
    tree.object_counts.drawing_count = eligiblePathNodes.length;
    tree.object_counts.text_span_count = descriptors.length;
    tree.object_counts.descriptor_count = descriptors.length;
    tree.object_counts.omitted_descriptor_count = Math.max(0, nodes.length - descriptors.length);
    tree.object_counts.omitted_eligible_descriptor_count = Math.max(0, eligibleNodes.length - descriptors.length);
    const pathResources = nativePathResources(ir, eligiblePathNodes);
    tree.resources = {
      font_count: fonts.length,
      xobject_count: pathResources.xobjects.length,
      content_stream_count: Array.isArray(ir.logical_streams) ? ir.logical_streams.length : 0,
      fonts,
      content_streams: pathResources.contentStreams,
      xobjects: pathResources.xobjects,
      form_definitions: pathResources.definitions,
      form_invocations: pathResources.invocations,
      invocation_index: {
        form_definitions: pathResources.definitions,
        form_invocations: pathResources.invocations
      }
    };
    const descriptorIds = new Set(descriptors.map((descriptor) => descriptor.id));
    const pathNodeIds = new Set(eligiblePathNodes.map((node) => node.id));
    const deferredKinds = nodes
      .filter((node) => !descriptorIds.has(node && node.id) && !pathNodeIds.has(node && node.id))
      .map((node) => String(node && node.kind || "unknown"));
    tree.materialization.materialized_descriptor_count = descriptors.length;
    tree.materialization.eligible_text_node_count = eligibleNodes.length;
    tree.materialization.descriptor_limit_applied = eligibleNodes.length > MAX_NATIVE_PDF_DESCRIPTORS;
    tree.materialization.materialized_path_node_count = eligiblePathNodes.length;
    tree.materialization.deferred_node_count = Math.max(0, nodes.length - descriptors.length - eligiblePathNodes.length);
    tree.materialization.deferred_node_kinds = [...new Set(deferredKinds)].sort();
    tree.materialization.deferred_reason_counts = evaluations.reduce((counts, row) => {
      if (row.eligibility.eligible) return counts;
      row.eligibility.reasons.forEach((reason) => { counts[reason] = (counts[reason] || 0) + 1; });
      return counts;
    }, {});
    if (eligibleNodes.length > MAX_NATIVE_PDF_DESCRIPTORS) {
      tree.materialization.deferred_reason_counts["descriptor-limit-exceeded"] = eligibleNodes.length - MAX_NATIVE_PDF_DESCRIPTORS;
    }
    tree.capabilities.typed_text_transaction_supported = descriptors.length > 0;
    tree.capabilities.typed_path_transaction_supported = eligiblePathNodes.length > 0;
    tree.capabilities.content_stream_mutation_supported = eligiblePathNodes.length > 0;
    tree.capabilities.form_xobject_content_stream_mutation_supported = eligiblePathNodes.some((node) => (
      Array.isArray(node.invocation_path) && node.invocation_path.length > 1
    ));
    return tree;
  }

  return Object.freeze({
    SOURCE_SCHEMA,
    DESCRIPTOR_TREE_SCHEMA,
    MATERIALIZATION_SCHEMA,
    SUPPORTED_NODE_KINDS,
    MAX_NATIVE_PDF_DESCRIPTORS,
    APPROVED_TEXT_OPERATORS,
    APPROVED_FONT_WRITE_PROFILES,
    materializeDescriptorTree,
    multiplyMatrix,
    transformPoint
  });
});
