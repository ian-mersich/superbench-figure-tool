(function attach(root, factory) {
  const base = typeof module === "object" && module.exports ? require("./pdf-editable-import.js") : root.FigureStudioPdfEditableImport;
  const optimizer = typeof module === "object" && module.exports ? require("./pdf-operator-optimizer.js") : root.FigureStudioPdfOperatorOptimizer;
  const api = factory(base, optimizer);
  if (typeof module === "object" && module.exports) module.exports = api;
  if (root) root.FigureStudioPdfEditableImportBatching = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function create(base, optimizer) {
  "use strict";
  if (!base || !optimizer) throw new Error("The original editable importer and operator planner must load first.");
  const PAINT_NAMES = ["fill", "eoFill", "stroke", "fillStroke", "eoFillStroke", "closeStroke", "closeFillStroke", "closeEOFillStroke", "showText", "showSpacedText", "paintSolidColorImageMask", "paintImageXObject", "paintInlineImageXObject", "shadingFill"];
  const knockoutApi = () => typeof module === "object" && module.exports ? require("./pdf-knockout.js") : globalThis.FigureStudioPdfKnockout;

  function rendererClass(pdfjs, options = {}) {
    const Original = base.rendererClass(pdfjs, options);
    return class BatchedEditableSvgGraphics extends Original {
      async getSVG(operatorList, viewport) {
        this.viewport = viewport;
        const svg = this._initialize(viewport);
        await this.loadDependencies(operatorList);
        this.transformMatrix = [1, 0, 0, 1, 0, 0];
        const neutralParents = [], scopeKinds = [];
        const clipProofs = new Map(), paintProofs = new Map();
        const names = new Map(Object.entries(pdfjs.OPS).map(([name, id]) => [id, name]));
        const paintIds = new Set(PAINT_NAMES.map((name) => pdfjs.OPS[name]).filter(Number.isInteger));
        let paintIndex = 0, proofCount = 0, yieldedBatches = 0, maxBatchExecutionMs = 0;
        let interpretationYieldCount = 0, maxSynchronousSliceMs = 0;
        const yieldTask = options.yieldTask || (() => new Promise(resolve => setTimeout(resolve, 0)));
        let skippedKnockoutEnd = -1, knockoutCount = 0;
        const knockoutSources = options.knockoutSources || [];
        if (knockoutSources.length && !base.isTrustedKnockoutSources(knockoutSources)) throw new Error("Knockout rendering requires the current importer source map.");
        const sourceByStart = new Map(knockoutSources.map(entry => [entry.scopeStart, entry]));
        const start = performance.now();
        await optimizer.executeOperatorBatches(operatorList, async (canonical, { start, end }) => {
          const batchStarted = performance.now();
          let sliceStarted = batchStarted;
          for (let index = start; index < end; index++) {
            // Operator counts alone do not bound image decoding time. Yield
            // between complete original operators, retaining every open scope.
            if (performance.now() - sliceStarted >= 8) {
              maxSynchronousSliceMs = Math.max(maxSynchronousSliceMs, performance.now() - sliceStarted);
              await yieldTask();
              if (options.signal?.aborted) throw Object.assign(new Error("PDF interpretation was cancelled."), { name: "AbortError" });
              interpretationYieldCount++;
              sliceStarted = performance.now();
            }
            const fnId = canonical.fnArray[index], args = canonical.argsArray[index] || [];
            if (index <= skippedKnockoutEnd) {
              if (paintIds.has(fnId)) paintIndex++;
              continue;
            }
            const bound = base.boundKnockoutScope(canonical, index, options.knockoutBinding, pdfjs.OPS);
            if (bound) {
              const entry = sourceByStart.get(index), api = knockoutApi();
              if (!entry || !api || !options.fabric) throw new Error("A proved knockout scope lost its source map or compositor.");
              if (JSON.stringify(this.transformMatrix) !== JSON.stringify(bound.ancestorTransform)) throw new Error("Knockout renderer state differs from its exact source binding.");
              const group = api.createScene({ ...entry.source, sourceToViewport: [...bound.ancestorTransform] }, options.fabric);
              group.figureId = entry.key;
              let element;
              if (options.createKnockoutElement) element = options.createKnockoutElement(group, entry);
              else {
                const Parser = options.DOMParser || globalThis.DOMParser;
                if (!Parser) throw new Error("Knockout vector SVG parsing is unavailable.");
                const fragment = new Parser().parseFromString(`<svg xmlns="http://www.w3.org/2000/svg">${group.toSVG()}</svg>`, "image/svg+xml");
                if (fragment.querySelector("parsererror")) throw new Error("The knockout compositor returned invalid SVG.");
                element = this.svg.ownerDocument.importNode(fragment.documentElement.firstElementChild, true);
              }
              for (const [key, value] of Object.entries({ "data-pdf-knockout-import-key": entry.key, "data-pdf-knockout-source-id": entry.sourceId, "data-pdf-knockout-source-sha256": entry.sourceSha256, "data-pdf-knockout-page": entry.pageNumber, "data-pdf-knockout-start": entry.scopeStart, "data-pdf-knockout-end": entry.scopeEnd, "data-pdf-knockout-binding": entry.schema })) element.setAttribute(key, String(value));
              // A fresh normal transform group on either side preserves sibling
              // paint order. The PDF.js root already owns the viewport matrix.
              this.tgrp = null;
              (this.current.activeClipUrl ? this._ensureClipGroup() : this.svg).append(element);
              this.tgrp = null;
              skippedKnockoutEnd = bound.scopeEnd;
              knockoutCount++;
              continue;
            }
            if (fnId === pdfjs.OPS.beginGroup && args[0]?.knockout) throw new Error("An unproved knockout scope cannot be rendered as ordinary transparency.");
            if (fnId === pdfjs.OPS.save) {
              // Exactly the original neutral group() opening, without recursion.
              const parent = this.svg;
              const scope = this.svgFactory.createElement("svg:g");
              scope.setAttribute("id", `pdf-scope-${++this.scopeSerial}`);
              scope.setAttribute("data-pdf-scope", "graphics-state");
              this._ensureTransformGroup();
              parent.append(scope);
              this.save();
              neutralParents.push(parent);
              scopeKinds.push("neutral");
              this.svg = scope;
              this.current.clipGroup = null;
              this.tgrp = null;
              if (options.markRectangleScopes !== false) {
                const proof = optimizer.detectRectangleScope(canonical, pdfjs.OPS, index, { sourceId: options.sourceId || "", pageNumber: options.pageNumber || 1, paintIndex });
                if (proof) { clipProofs.set(index + 3, proof); paintProofs.set(proof.paintOperatorIndex, proof); proofCount++; options.onRectangleProof?.(proof); }
              }
            } else if (fnId === pdfjs.OPS.restore) {
              if (!neutralParents.length || scopeKinds.pop() !== "neutral") throw new Error("Batched PDF neutral groups are unbalanced.");
              this.svg = neutralParents.pop();
              this.restore();
            } else {
              if (fnId === pdfjs.OPS.beginGroup) scopeKinds.push("transparency");
              if (fnId === pdfjs.OPS.endGroup && scopeKinds.pop() !== "transparency") throw new Error("Batched PDF transparency groups are unbalanced.");
              const proof = paintProofs.get(index);
              if (proof) {
                if (!this.current.path) throw new Error("A proven source paint has no canonical SVG path.");
                for (const [key, value] of Object.entries(optimizer.svgAttributes(proof))) this.current.path.setAttribute(key, value);
                paintProofs.delete(index);
              }
              // Delegates original Form, font, clip and transparency behavior.
              // No synthetic group (fnId 92) is created, and no subtree recurses.
              super.executeOpTree([{ fnId, fn: names.get(fnId), args }]);
              const clipProof = clipProofs.get(index);
              if (clipProof) {
                const clip = this.defs.lastElementChild;
                if (clip?.localName?.toLowerCase() !== "clippath") throw new Error("A proven source clip has no canonical SVG definition.");
                clip.setAttribute("data-pdf-source-clip-index", String(clipProof.clipOperatorIndex));
                clip.setAttribute("data-pdf-source-start", String(clipProof.scopeStart));
                clip.setAttribute("data-pdf-source-end", String(clipProof.scopeEnd));
                clipProofs.delete(index);
              }
            }
            if (paintIds.has(fnId)) paintIndex++;
          }
          maxSynchronousSliceMs = Math.max(maxSynchronousSliceMs, performance.now() - sliceStarted);
          yieldedBatches++;
          maxBatchExecutionMs = Math.max(maxBatchExecutionMs, performance.now() - batchStarted);
          options.onProgress?.({ stage: "interpret", processedOperatorCount: end, originalOperatorCount: canonical.fnArray.length, paintCount: paintIndex, rectangleProofCount: proofCount });
        }, { batchSize: options.batchSize || 2048, signal: options.signal, ...(options.yieldTask ? { yieldTask: options.yieldTask } : {}) });
        if (scopeKinds.length || neutralParents.length || this.transparencyScopes.length || clipProofs.size || paintProofs.size || this.extraStack.length || this.transformStack.length) throw new Error("Batched PDF scope or proof state is unbalanced.");
        if (knockoutCount !== knockoutSources.length) throw new Error("A proved knockout source was not emitted at its original scope.");
        this.batchReport = { operatorCount: operatorList.fnArray.length, paintCount: paintIndex, rectangleProofCount: proofCount, batchCount: yieldedBatches, interpretationElapsedMs: performance.now() - start, maxBatchExecutionMs, interpretationYieldCount, maxSynchronousSliceMs, canonicalGeometryRewritten: false, ...(knockoutCount ? { knockoutGroupCount: knockoutCount, canonicalKnockoutPaintCount: knockoutCount * 2 } : {}) };
        return svg;
      }
    };
  }

  async function renderPageBatched({ pdfjs, bytes, pageNumber = 1, budgets = base.DEFAULT_BUDGETS, onProgress, batchSize = 2048, signal, markRectangleScopes = true, fabric, knockoutProofWorkerUrl, readKnockoutSource, loadPdfLib } = {}) {
    if (!pdfjs?.SVGGraphics) throw new Error("The bundled PDF interpreter is unavailable.");
    const data = bytes instanceof Uint8Array ? bytes : new Uint8Array(bytes || []);
    const limits = { ...base.DEFAULT_BUDGETS, ...budgets };
    if (!data.length || data.length > limits.sourceBytes) throw new Error("PDF source exceeds the editable import byte budget.");
    const started = performance.now();
    let handle;
    try {
      handle = await pdfjs.getDocument({ data: data.slice(), fontExtraProperties: true, isOffscreenCanvasSupported: false, useSystemFonts: true }).promise;
      const page = await handle.getPage(pageNumber), viewport = page.getViewport({ scale: 1 });
      const operators = await page.getOperatorList();
      const logicalRuntime = typeof module === "object" && module.exports ? require("./pdf-logical-text-runtime.js") : globalThis.FigureStudioPdfLogicalTextRuntime;
      const logicalTextSource = logicalRuntime ? await logicalRuntime.sourceForPage({ handle, page, operators, pdfjs, bytes: data, pageNumber, loadPdfLib, signal }) : null;
      const { currentPlanePage, currentPlaneViewport } = await base.prepareCurrentNativePageRoute({ logicalTextSource, logicalRuntime, page, operators, pdfjs, viewport, fabric });
      const prepared = await base.prepareKnockoutScopes({ operatorList: operators, OPS: pdfjs.OPS, bytes: data, pageNumber, budgets: limits, signal, onProgress, workerUrl: knockoutProofWorkerUrl, readSource: readKnockoutSource });
      const inventory = prepared.inventory;
      if (inventory.unsupported.length) {
        const error = new Error(`Editable PDF reconstruction does not yet support ${inventory.unsupported.join(", ")}. The original page was retained.`);
        error.code = "PDF_EDITABLE_UNSUPPORTED";
        error.report = { schema: base.SCHEMA, status: "unsupported", ...inventory };
        throw error;
      }
      onProgress?.({ stage: "reconstruct", ...inventory });
      const digest = new Uint8Array(await globalThis.crypto.subtle.digest("SHA-256", data));
      const sourceId = Array.from(digest, (byte) => byte.toString(16).padStart(2, "0")).join("");
      const knockoutSources = prepared.binding ? base.createKnockoutSources(operators, prepared.binding, viewport, pageNumber) : [];
      const Renderer = rendererClass(pdfjs, { batchSize, signal, markRectangleScopes, sourceId, pageNumber, onProgress, fabric, knockoutBinding: prepared.binding, knockoutSources, logicalTextSource });
      const CurrentRenderer = currentPlanePage
        ? await logicalRuntime.currentNativeRenderer(logicalTextSource, { Base: Renderer, page, operators, pdfjs, viewport: currentPlaneViewport }) : Renderer;
      const graphics = new CurrentRenderer(page.commonObjs, page.objs);
      const textContent = await page.getTextContent({ disableNormalization: true });
      graphics.recoveredTextItems = textContent.items;
      const sourceItems = typeof module === "object" && module.exports ? require("./pdf-source-text-items.js") : globalThis.FigureStudioPdfSourceTextItems;
      if (!logicalTextSource && !prepared.binding) sourceItems?.begin(graphics, operators, textContent.items, pdfjs);
      const svg = await graphics.getSVG(operators, currentPlaneViewport);
      if (currentPlanePage) {
        svg.setAttribute("width", String(currentPlanePage.widthPx));
        svg.setAttribute("height", String(currentPlanePage.heightPx));
        svg.setAttribute("viewBox", `0 0 ${currentPlanePage.widthPx} ${currentPlanePage.heightPx}`);
      }
      const objectCount = base.canonicalSvgObjectCount(svg, knockoutSources);
      if (objectCount > limits.objects) throw new Error(`Editable PDF reconstruction contains ${objectCount} objects, exceeding its qualified object budget.`);
      const fonts = [...graphics.programs.values()];
      if (fonts.length) base.namespaceFontPrograms(svg, fonts, `${sourceId}_p${pageNumber}`);
      await base.registerFonts(fonts);
      const sourceTextItems = sourceItems?.finish(graphics, svg, fonts, { sourceSha256: sourceId, pageNumber });
      const svgText = new XMLSerializer().serializeToString(svg);
      if (logicalTextSource) await logicalRuntime.finishDecodedSvg(logicalTextSource, svgText, svg);
      const currentPlaneObjects = currentPlanePage
        ? await logicalRuntime.constructCurrentPlaneObjects({ token: logicalTextSource, svgText, svg, fabric,
            materializer: globalThis.FigureStudioPdfSvgMaterializer || (typeof module === "object" && module.exports ? require("./pdf-svg-materializer.js") : null) }) : null;
      const report = { schema: base.SCHEMA, status: "reconstructed", ...inventory, objectCount, fonts, warnings: [...graphics.recoveryWarnings], wordSpacingRecovery: graphics.wordSpacingRecovery, sourceTextItems, nativeEquivalent: false, elapsedMs: performance.now() - started, operatorBatching: graphics.batchReport, ...(prepared.binding ? { knockout: { groupCount: knockoutSources.length, canonicalMemberCount: knockoutSources.length * 2, sourceSha256: sourceId, scopeIndexes: knockoutSources.map(entry => [entry.scopeStart, entry.scopeEnd]), operatorBinding: prepared.binding.operatorBinding } } : {}) };
      return { svgText, svgElement: svg, logicalTextSource, currentPlaneObjects, currentPlanePage, knockoutSources, width: viewport.width, height: viewport.height, sourceWidth: viewport.width, sourceHeight: viewport.height, pageNumber, pageCount: handle.numPages, operatorCount: inventory.operatorCount, editableImport: report };
    } finally { await handle?.destroy?.(); }
  }
  return { rendererClass, renderPageBatched };
});
