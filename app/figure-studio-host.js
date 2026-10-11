(function () {
  "use strict";

  const DEFAULT_CAPABILITIES = {
    canLoadProject: true,
    canSaveProject: false,
    canSaveProjectAs: false,
    canImportHandoffPayload: true,
    canExportFigurePackage: false,
    canDownloadArtifact: true,
    canOpenSourceResult: false,
    canOpenSourceWorkbook: false,
    canRequestPdfConversion: false,
    canPickSvgSource: false,
    nativeFileDialogs: false,
    nativeExportDialogs: false,
    nativeDocumentFiles: false,
    preferHostSave: false,
    preferHostExport: false
  };

  const MAX_NATIVE_EXPORT_FILE_BYTES = 256 * 1024 * 1024;
  const MAX_NATIVE_EXPORT_TOTAL_BYTES = 512 * 1024 * 1024;
  const MAX_NATIVE_EXPORT_FILES = 500;
  const BASE64_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";

  function normalizeCapabilities(adapter, explicit) {
    const fromAdapter = typeof adapter?.getHostCapabilities === "function"
      ? adapter.getHostCapabilities() || {}
      : {};
    return {
      ...DEFAULT_CAPABILITIES,
      ...fromAdapter,
      ...(explicit || {})
    };
  }

  function resolveTauriInvoke() {
    const invoke = window.__TAURI_INTERNALS__?.invoke;
    return typeof invoke === "function" ? invoke.bind(window.__TAURI_INTERNALS__) : null;
  }

  function ownsStandaloneDesktopBridge() {
    // Tauri exposes its IPC globals to same-WebView child frames. An embedded
    // Figure workspace must not mistake that inherited bridge for ownership of
    // native file commands; the containing Superbench project owns those
    // operations. The suite's internal direct-launch targets likewise use the
    // shared suite host, which does not expose Figure Tool's standalone file
    // command set.
    try {
      if (window.parent && window.parent !== window) return false;
    } catch (_error) {
      return false;
    }
    const search = String(window.location?.search || "");
    if (/(?:^|[?&])(?:free_bench_host=authoring|bsd_embed=[^&]*|bsd_host=bsd-studio)(?:&|$)/.test(search)) return false;
    return !/(?:^|[?&])bsd_desktop_target=/.test(search);
  }

  function authoringExportBridge() {
    try {
      if (!/(?:^|[?&])free_bench_host=authoring(?:&|$)/.test(String(window.location?.search || ""))) return null;
      if (!window.parent || window.parent === window) return null;
      const bridge = window.parent.SuperbenchNativeProjectFiles;
      return bridge?.exportsAvailable?.() === true && typeof bridge.saveExportFile === "function"
        ? bridge
        : null;
    } catch (_error) {
      return null;
    }
  }

  function createAuthoringExportHostAdapter(bridge = authoringExportBridge()) {
    if (!bridge) return null;
    return {
      mode: "authoring-host",
      getHostCapabilities() {
        return {
          ...DEFAULT_CAPABILITIES,
          nativeExportDialogs: true,
          preferHostExport: true
        };
      },
      async saveExportFile(request = {}) {
        return bridge.saveExportFile({
          suggestedName: request.suggestedName || request.suggestedFilename || request.filename || request.artifact?.filename,
          mimeType: request.mimeType || request.artifact?.mimeType,
          bytes: request.bytes ?? request.artifact?.bytes
        });
      }
    };
  }

  function nativeDocumentError(documentId, message) {
    return {
      status: "error",
      documentId: String(documentId || ""),
      path: null,
      filename: null,
      documentKind: null,
      contents: null,
      message,
      error: message
    };
  }

  function nativeExportError(message) {
    return {
      status: "error",
      path: null,
      filePath: null,
      directoryPath: null,
      filename: null,
      fileCount: 0,
      message,
      error: message
    };
  }

  function normalizeExportBytes(value) {
    if (typeof ArrayBuffer !== "undefined" && ArrayBuffer.isView(value)) {
      return new Uint8Array(value.buffer, value.byteOffset, value.byteLength);
    }
    if (typeof ArrayBuffer !== "undefined" && Object.prototype.toString.call(value) === "[object ArrayBuffer]") {
      return new Uint8Array(value);
    }
    throw new TypeError("Export data must be a byte array.");
  }

  function exportBytesToBase64(value) {
    const bytes = normalizeExportBytes(value);
    if (!bytes.byteLength || bytes.byteLength > MAX_NATIVE_EXPORT_FILE_BYTES) {
      throw new RangeError("Each exported file must be between 1 byte and 256 MB.");
    }
    let result = "";
    let chunk = "";
    for (let index = 0; index < bytes.length; index += 3) {
      const first = bytes[index];
      const second = index + 1 < bytes.length ? bytes[index + 1] : 0;
      const third = index + 2 < bytes.length ? bytes[index + 2] : 0;
      chunk += BASE64_ALPHABET[first >> 2];
      chunk += BASE64_ALPHABET[((first & 3) << 4) | (second >> 4)];
      chunk += index + 1 < bytes.length ? BASE64_ALPHABET[((second & 15) << 2) | (third >> 6)] : "=";
      chunk += index + 2 < bytes.length ? BASE64_ALPHABET[third & 63] : "=";
      if (chunk.length >= 32768) {
        result += chunk;
        chunk = "";
      }
    }
    return result + chunk;
  }

  function normalizeNativeDocumentOptions(options = {}) {
    return options && typeof options === "object" ? options : {};
  }

  function nativeDocumentId(options = {}) {
    return String(options.documentId || options.document_id || "").trim();
  }

  function nativeDocumentKind(payload, options = {}) {
    const explicitKind = String(options.documentKind || options.document_kind || "").trim().toLowerCase();
    if (["figure", "presentation", "workspace"].includes(explicitKind)) return explicitKind;
    if (payload?.schema === "figureStudio.workspaceProject.v1") return "workspace";
    const project = payload?.schema === "figureStudio.projectPayload.v1" && payload.project
      ? payload.project
      : payload;
    const kind = String(project?.document?.kind || "").trim().toLowerCase();
    return kind === "presentation" ? "presentation" : "figure";
  }

  function nativeSuggestedName(payload, options = {}) {
    const project = payload?.schema === "figureStudio.projectPayload.v1" && payload.project
      ? payload.project
      : payload;
    return String(options.suggestedName || options.suggested_name || options.filename || project?.title || "").trim();
  }

  function createTauriDesktopHostAdapter() {
    const invoke = resolveTauriInvoke();
    if (!invoke) return null;
    const invokeDocumentCommand = async (command, request) => {
      try {
        const result = await invoke(command, { request });
        if (!result || typeof result !== "object" || !String(result.status || "").trim()) {
          return nativeDocumentError(request?.documentId, "Figure Tool received an invalid desktop file response.");
        }
        return result;
      } catch (error) {
        return nativeDocumentError(
          request?.documentId,
          error?.message || String(error || "The Figure Tool desktop file service is unavailable.")
        );
      }
    };
    const invokeExportCommand = async (command, request) => {
      try {
        const result = await invoke(command, { request });
        if (!result || typeof result !== "object" || !String(result.status || "").trim()) {
          return nativeExportError("Figure Tool received an invalid desktop export response.");
        }
        return result;
      } catch (error) {
        return nativeExportError(error?.message || String(error || "The Figure Tool desktop export service is unavailable."));
      }
    };
    const save = async (projectPayload, rawOptions = {}, saveAs = false) => {
      const options = normalizeNativeDocumentOptions(rawOptions);
      const documentId = nativeDocumentId(options);
      if (!documentId) {
        return nativeDocumentError("", "Figure Tool cannot save without an active document tab.");
      }
      let contents = "";
      try {
        contents = JSON.stringify(projectPayload, null, 2);
      } catch (_error) {
        return nativeDocumentError(documentId, "The active document could not be prepared for saving.");
      }
      return invokeDocumentCommand("figure_studio_save_document", {
        documentId,
        contents,
        suggestedName: nativeSuggestedName(projectPayload, options),
        documentKind: nativeDocumentKind(projectPayload, options),
        saveAs: Boolean(saveAs)
      });
    };
    return {
      mode: "standalone-desktop",
      getHostCapabilities() {
        return {
          canLoadProject: true,
          canSaveProject: true,
          canSaveProjectAs: true,
          canImportHandoffPayload: true,
          canExportFigurePackage: false,
          canDownloadArtifact: true,
          canOpenSourceResult: false,
          canOpenSourceWorkbook: false,
          canRequestPdfConversion: false,
          canPickSvgSource: true,
          nativeFileDialogs: true,
          nativeExportDialogs: true,
          nativeDocumentFiles: true,
          preferHostSave: true,
          preferHostExport: true
        };
      },
      async saveProject(projectPayload, options = {}) {
        return save(projectPayload, options, false);
      },
      async saveProjectAs(projectPayload, options = {}) {
        return save(projectPayload, options, true);
      },
      async loadProject(rawOptions = {}) {
        const options = normalizeNativeDocumentOptions(rawOptions);
        const documentId = nativeDocumentId(options);
        if (!documentId) {
          return nativeDocumentError("", "Figure Tool cannot open a file without a destination document tab.");
        }
        const result = await invokeDocumentCommand("figure_studio_open_document", {
          documentId,
          expectedKind: String(options.expectedKind || options.expected_kind || "").trim() || null,
          requestedPath: String(options.requestedPath || options.requested_path || "").trim() || null
        });
        if (result.status !== "opened" || typeof result.contents !== "string") return result;
        try {
          const payload = JSON.parse(result.contents);
          return { ...result, payload, project: payload };
        } catch (_error) {
          return nativeDocumentError(documentId, "The opened document could not be decoded.");
        }
      },
      async pickSvgSource(rawOptions = {}) {
        const options = normalizeNativeDocumentOptions(rawOptions);
        const documentId = nativeDocumentId(options);
        if (!documentId) {
          return nativeDocumentError("", "Figure Tool cannot choose an SVG source without an active document tab.");
        }
        return invokeDocumentCommand("figure_studio_pick_svg_source", { documentId });
      },
      async takeLaunchDocument(rawOptions = {}) {
        const options = normalizeNativeDocumentOptions(rawOptions);
        const documentId = nativeDocumentId(options);
        if (!documentId) {
          return nativeDocumentError("", "Figure Tool cannot open a startup file without a destination document tab.");
        }
        const result = await invokeDocumentCommand("figure_studio_take_launch_document", {
          documentId,
          expectedKind: String(options.expectedKind || options.expected_kind || "").trim() || null
        });
        if (result.status !== "opened" || typeof result.contents !== "string") return result;
        const sourceKind = String(result.documentKind || result.document_kind || "").trim().toLowerCase();
        if (sourceKind === "svg-source" || sourceKind === "pdf-source") {
          return result;
        }
        try {
          const payload = JSON.parse(result.contents);
          return { ...result, payload, project: payload };
        } catch (_error) {
          return nativeDocumentError(documentId, "The startup document could not be decoded.");
        }
      },
      async getDocumentBinding(documentId) {
        return invokeDocumentCommand("figure_studio_get_document_binding", {
          documentId: String(documentId || "").trim()
        });
      },
      async releaseDocument(documentId) {
        return invokeDocumentCommand("figure_studio_release_document", {
          documentId: String(documentId || "").trim()
        });
      },
      async setWindowDocumentState(rawState = {}) {
        const state = normalizeNativeDocumentOptions(rawState);
        return invokeDocumentCommand("figure_studio_set_window_document_state", {
          documentId: nativeDocumentId(state) || null,
          filename: String(state.filename || "").trim() || null,
          documentKind: String(state.documentKind || state.document_kind || state.kind || "").trim() || null,
          dirty: Boolean(state.dirty)
        });
      },
      async saveExportFile(rawRequest = {}) {
        const request = rawRequest && typeof rawRequest === "object" ? rawRequest : {};
        try {
          return invokeExportCommand("figure_studio_save_export_file", {
            suggestedName: String(request.suggestedName || request.suggestedFilename || request.filename || request.artifact?.filename || "Figure Tool export").trim(),
            mimeType: String(request.mimeType || request.artifact?.mimeType || "").trim().toLowerCase(),
            dataBase64: exportBytesToBase64(request.bytes ?? request.artifact?.bytes)
          });
        } catch (error) {
          return nativeExportError(error?.message || String(error || "The exported file could not be prepared."));
        }
      },
      async saveExportFiles(rawRequest = {}) {
        const request = rawRequest && typeof rawRequest === "object" ? rawRequest : {};
        const sourceFiles = Array.isArray(request.files) ? request.files : (Array.isArray(request.artifacts) ? request.artifacts : []);
        if (!sourceFiles.length) return nativeExportError("There are no files to export.");
        if (sourceFiles.length > MAX_NATIVE_EXPORT_FILES) {
          return nativeExportError(`This export contains more than the ${MAX_NATIVE_EXPORT_FILES}-file folder limit.`);
        }
        try {
          let totalBytes = 0;
          const files = sourceFiles.map((file) => {
            const bytes = normalizeExportBytes(file?.bytes);
            totalBytes += bytes.byteLength;
            if (totalBytes > MAX_NATIVE_EXPORT_TOTAL_BYTES) {
              throw new RangeError("This folder export exceeds the 512 MB total limit.");
            }
            return {
              filename: String(file?.filename || file?.suggestedName || "Figure Tool export").trim(),
              mimeType: String(file?.mimeType || "").trim().toLowerCase(),
              dataBase64: exportBytesToBase64(bytes)
            };
          });
          return invokeExportCommand("figure_studio_save_export_files", {
            suggestedFolderName: String(request.suggestedFolderName || "Figure Tool export").trim(),
            files
          });
        } catch (error) {
          return nativeExportError(error?.message || String(error || "The exported files could not be prepared."));
        }
      }
    };
  }

  function createFigureStudioHostAdapter(adapter = {}, options = {}) {
    const capabilities = normalizeCapabilities(adapter, options.capabilities);
    const notify = typeof adapter.notify === "function"
      ? adapter.notify.bind(adapter)
      : (message, severity = "info") => {
        if (severity === "error") console.error(message);
        else if (severity === "warning") console.warn(message);
        else console.info(message);
      };

    const host = {
      mode: options.mode || adapter.mode || "standalone",
      getHostCapabilities() {
        return { ...capabilities };
      },
      async loadProject(...args) {
        if (typeof adapter.loadProject === "function") return adapter.loadProject(...args);
        return null;
      },
      async pickSvgSource(optionsArg) {
        if (typeof adapter.pickSvgSource === "function") return adapter.pickSvgSource(optionsArg);
        return null;
      },
      async takeLaunchDocument(optionsArg) {
        if (typeof adapter.takeLaunchDocument === "function") return adapter.takeLaunchDocument(optionsArg);
        return null;
      },
      async saveProject(projectPayload, optionsArg) {
        if (typeof adapter.saveProject === "function") return adapter.saveProject(projectPayload, optionsArg);
        return null;
      },
      async saveProjectAs(projectPayload, optionsArg) {
        if (typeof adapter.saveProjectAs === "function") return adapter.saveProjectAs(projectPayload, optionsArg);
        return null;
      },
      async getDocumentBinding(documentId) {
        if (typeof adapter.getDocumentBinding === "function") return adapter.getDocumentBinding(documentId);
        return null;
      },
      async releaseDocument(documentId) {
        if (typeof adapter.releaseDocument === "function") return adapter.releaseDocument(documentId);
        return null;
      },
      async setWindowDocumentState(state) {
        if (typeof adapter.setWindowDocumentState === "function") return adapter.setWindowDocumentState(state);
        return null;
      },
      async saveExportFile(request) {
        if (typeof adapter.saveExportFile === "function") return adapter.saveExportFile(request);
        return null;
      },
      async importHandoffPayload(payload) {
        if (typeof adapter.importHandoffPayload === "function") return adapter.importHandoffPayload(payload);
        return payload;
      },
      async exportFigurePackage(optionsArg) {
        if (typeof adapter.exportFigurePackage === "function") return adapter.exportFigurePackage(optionsArg);
        return null;
      },
      onProjectChanged(detail) {
        if (typeof adapter.onProjectChanged === "function") return adapter.onProjectChanged(detail);
        if (typeof adapter.onDirtyStateChanged === "function") return adapter.onDirtyStateChanged(detail);
        return null;
      },
      onDirtyStateChanged(detail) {
        if (typeof adapter.onDirtyStateChanged === "function") return adapter.onDirtyStateChanged(detail);
        return null;
      },
      onPreviewGenerated(detail) {
        if (typeof adapter.onPreviewGenerated === "function") return adapter.onPreviewGenerated(detail);
        return null;
      },
      onPackageGenerated(detail) {
        if (typeof adapter.onPackageGenerated === "function") return adapter.onPackageGenerated(detail);
        return null;
      },
      onPreflightUpdated(detail) {
        if (typeof adapter.onPreflightUpdated === "function") return adapter.onPreflightUpdated(detail);
        return null;
      },
      onArtifactGenerated(detail) {
        if (typeof adapter.onArtifactGenerated === "function") return adapter.onArtifactGenerated(detail);
        return null;
      },
      async downloadArtifact(artifact) {
        if (typeof adapter.downloadArtifact === "function") return adapter.downloadArtifact(artifact);
        return null;
      },
      notify,
      async openSourceResult(sourceRef) {
        if (typeof adapter.openSourceResult === "function") return adapter.openSourceResult(sourceRef);
        notify("Opening source Results is not supported by this host.", "warning");
        return null;
      },
      async openSourceWorkbook(sourceRef) {
        if (typeof adapter.openSourceWorkbook === "function") return adapter.openSourceWorkbook(sourceRef);
        notify("Opening source workbooks is not supported by this host.", "warning");
        return null;
      },
      async requestPdfConversion(file, page, conversionOptions) {
        if (typeof adapter.requestPdfConversion === "function") {
          return adapter.requestPdfConversion(file, page, conversionOptions);
        }
        return null;
      }
    };
    if (typeof adapter.saveExportFiles === "function") {
      host.saveExportFiles = (request) => adapter.saveExportFiles(request);
    }
    return host;
  }

  function resolveElement(container) {
    if (typeof container === "string") return document.querySelector(container);
    return container;
  }

  function resolveUrl(url) {
    return new URL(url, document.baseURI).toString();
  }

  async function ensureStylesheet(url) {
    const href = resolveUrl(url || "styles.css");
    if (Array.from(document.styleSheets).some((sheet) => sheet.href === href)) return;
    if (Array.from(document.querySelectorAll("link[data-figure-studio-style]")).some((link) => link.href === href)) return;
    await new Promise((resolve, reject) => {
      const link = document.createElement("link");
      link.rel = "stylesheet";
      link.href = href;
      link.dataset.figureStudioStyle = "true";
      link.onload = resolve;
      link.onerror = () => reject(new Error(`Could not load Figure Tool stylesheet: ${href}`));
      document.head.appendChild(link);
    });
  }

  async function loadTemplateInto(container, templateUrl) {
    const response = await fetch(resolveUrl(templateUrl || "index.html"), { cache: "no-store" });
    if (!response.ok) throw new Error(`Could not load Figure Tool template: HTTP ${response.status}`);
    const html = await response.text();
    const parsed = new DOMParser().parseFromString(html, "text/html");
    let root = parsed.querySelector(".figure-studio-root");
    if (!root) {
      const shell = parsed.querySelector(".studio-shell");
      const toast = parsed.querySelector("#toast");
      if (!shell) throw new Error("Figure Tool template does not contain .figure-studio-root or .studio-shell.");
      root = document.createElement("div");
      root.className = "figure-studio-root";
      root.id = "figureStudioRoot";
      root.appendChild(shell);
      if (toast) root.appendChild(toast);
    }
    container.replaceChildren(document.importNode(root, true));
    return container.querySelector(".figure-studio-root");
  }

  function waitForAppReady(timeoutMs = 90000) {
    const started = Date.now();
    return new Promise((resolve, reject) => {
      const check = () => {
        const api = window.FigureStudio?.app;
        if (api?.ready && typeof api.ready.then === "function") {
          api.ready.then((resolvedApi) => resolve(resolvedApi || window.FigureStudio?.app || api)).catch(reject);
          return;
        }
        if (api?.isReady) {
          resolve(api);
          return;
        }
        if (Date.now() - started > timeoutMs) {
          reject(new Error("Timed out waiting for Figure Tool to mount."));
          return;
        }
        window.setTimeout(check, 50);
      };
      check();
    });
  }

  async function ensureMountDependencies(appScriptUrl) {
    const baseUrl = new URL(".", resolveUrl(appScriptUrl || "app.js"));
    // Keep the embedded entry point in the same dependency order as app/index.html.
    const dependencies = [
      "../vendor/fabric/index.min.js",
      "../vendor/jspdf/jspdf.umd.min.js",
      "../vendor/svg2pdf/svg2pdf.umd.min.js",
      "../vendor/polygon-clipping/polygon-clipping.umd.min.js",
      "file-formats.js",
      "pptx-v1.js",
      "export-as.js",
      "help/figure-studio-help-center.js",
      "scientific-asset-catalog.js",
      "scientific-scene-catalog.js",
      "scientific-protocol-components.js",
      "vector-engine.js",
      "native-pdf-ir-materializer.js"
    ];
    for (const dependency of dependencies) {
      const src = new URL(dependency, baseUrl).toString();
      if (Array.from(document.querySelectorAll("script[src]")).some((script) => {
        const existing = new URL(script.src);
        return existing.origin === baseUrl.origin && existing.pathname === new URL(src).pathname;
      })) continue;
      await new Promise((resolve, reject) => {
        const script = document.createElement("script");
        script.src = src;
        script.dataset.figureStudioDependency = "true";
        script.onload = resolve;
        script.onerror = () => reject(new Error(`Could not load Figure Tool dependency: ${src}`));
        document.head.appendChild(script);
      });
    }
  }

  async function ensureAppScript(url) {
    if (window.FigureStudio?.app) return;
    const src = resolveUrl(url || "app.js");
    if (Array.from(document.querySelectorAll("script[data-figure-studio-app]")).some((script) => script.src === src)) return;
    await new Promise((resolve, reject) => {
      const script = document.createElement("script");
      script.src = src;
      script.defer = true;
      script.dataset.figureStudioApp = "true";
      script.onload = resolve;
      script.onerror = () => reject(new Error(`Could not load Figure Tool app script: ${src}`));
      document.body.appendChild(script);
    });
  }

  async function mountFigureStudio(container, options = {}) {
    const target = resolveElement(container);
    if (!target) throw new Error("mountFigureStudio requires a valid DOM container.");

    const mode = options.mode === "story-figure" ? "story-figure" : "standalone";
    const hostAdapter = createFigureStudioHostAdapter(options.hostAdapter || {}, {
      mode,
      capabilities: options.capabilities || {}
    });
    let readyNotified = false;
    const notifyReady = (api) => {
      if (readyNotified) return;
      readyNotified = true;
      if (typeof options.onReady === "function") options.onReady(api);
    };
    window.__FIGURE_STUDIO_MOUNT_OPTIONS__ = {
      mode,
      bsdHosted: Boolean(options.bsdHosted || options.bsd_hosted),
      hostAdapter,
      capabilities: hostAdapter.getHostCapabilities(),
      history: options.history || {},
      initialProject: options.initialProject || null,
      onReady: notifyReady
    };
    window.__FIGURE_STUDIO_RESOURCE_BASE_URL = new URL("../", resolveUrl(options.templateUrl || "index.html")).toString();

    await ensureStylesheet(options.styleUrl || "styles.css");
    await ensureStylesheet(new URL("help/figure-studio-help-center.css", resolveUrl(options.appScriptUrl || "app.js")).toString());
    let root = target.querySelector(".figure-studio-root");
    if (!root) root = await loadTemplateInto(target, options.templateUrl || "index.html");
    root.dataset.figureStudioMode = mode;
    root.classList.toggle("embedded", mode === "story-figure");
    document.body.classList.toggle("figure-studio-standalone", mode === "standalone");

    await ensureMountDependencies(options.appScriptUrl || "app.js");
    await ensureAppScript(options.appScriptUrl || "app.js");
    const api = await waitForAppReady(options.timeoutMs || 90000);
    notifyReady(api);
    return api;
  }

  function installTauriDesktopMountAdapter() {
    if (!ownsStandaloneDesktopBridge()) return null;
    const nativeAdapter = createTauriDesktopHostAdapter();
    if (!nativeAdapter) return null;
    const existing = window.__FIGURE_STUDIO_MOUNT_OPTIONS__ && typeof window.__FIGURE_STUDIO_MOUNT_OPTIONS__ === "object"
      ? window.__FIGURE_STUDIO_MOUNT_OPTIONS__
      : {};
    if (existing.hostAdapter || existing.bsdHosted || existing.bsd_hosted || existing.mode === "story-figure") return null;
    const hostAdapter = createFigureStudioHostAdapter(nativeAdapter, {
      mode: "standalone",
      capabilities: nativeAdapter.getHostCapabilities()
    });
    window.__FIGURE_STUDIO_MOUNT_OPTIONS__ = {
      ...existing,
      mode: "standalone",
      hostAdapter,
      capabilities: hostAdapter.getHostCapabilities()
    };
    return hostAdapter;
  }

  function installAuthoringExportMountAdapter() {
    const nativeAdapter = createAuthoringExportHostAdapter();
    if (!nativeAdapter) return null;
    const existing = window.__FIGURE_STUDIO_MOUNT_OPTIONS__ && typeof window.__FIGURE_STUDIO_MOUNT_OPTIONS__ === "object"
      ? window.__FIGURE_STUDIO_MOUNT_OPTIONS__
      : {};
    if (existing.hostAdapter) return null;
    const hostAdapter = createFigureStudioHostAdapter(nativeAdapter, {
      mode: existing.mode || "standalone",
      capabilities: nativeAdapter.getHostCapabilities()
    });
    window.__FIGURE_STUDIO_MOUNT_OPTIONS__ = {
      ...existing,
      authoringHost: true,
      hostAdapter,
      capabilities: hostAdapter.getHostCapabilities()
    };
    return hostAdapter;
  }

  window.FigureStudio = {
    ...(window.FigureStudio || {}),
    DEFAULT_CAPABILITIES,
    createFigureStudioHostAdapter,
    createTauriDesktopHostAdapter,
    createAuthoringExportHostAdapter,
    nativeDesktopAvailable: Boolean(resolveTauriInvoke()),
    mountFigureStudio
  };
  installAuthoringExportMountAdapter();
  installTauriDesktopMountAdapter();
})();
