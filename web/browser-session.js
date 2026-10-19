(function () {
  "use strict";
  const frame = document.getElementById("figure-editor-frame");
  const status = document.getElementById("browser-save-status");
  const library = document.getElementById("browser-library");
  const list = document.getElementById("browser-projects");
  const store = window.FigureBrowserStore;
  const localFile = window.location.protocol === "file:";
  const webHeader = document.querySelector(".web-header");
  const toolbar = document.querySelector(".browser-toolbar");
  const headerActions = document.querySelector(".web-header-actions");
  const appearance = document.getElementById("browser-appearance");
  const retryButton = document.getElementById("browser-retry");
  const copyButton = document.getElementById("browser-save-copy");
  const announcements = document.getElementById("browser-announcements");
  let browserChrome = null;

  // This same-origin web host owns browser files and appearance preferences.
  // Adopt its controls only after the shared editor is ready; the desktop host
  // owns its global Settings and never loads this browser entry.
  async function integrateBrowserChrome() {
    const editorDocument = frame.contentDocument;
    const header = editorDocument?.querySelector(".app-header .top-window-actions");
    const root = editorDocument?.getElementById("figureStudioRoot");
    if (!header || !root || browserChrome) return;
    const stylesheet = editorDocument.createElement("link");
    stylesheet.rel = "stylesheet";
    stylesheet.href = new URL("browser-chrome.css?v=20261015-appearance2", document.baseURI).href;
    const styled = await new Promise(resolve => {
      const timeout = setTimeout(() => resolve(false), 5000);
      stylesheet.onload = () => { clearTimeout(timeout); resolve(true); };
      stylesheet.onerror = () => { clearTimeout(timeout); resolve(false); };
      editorDocument.head.append(stylesheet);
    });
    if (!styled || editorDocument !== frame.contentDocument) {
      stylesheet.remove();
      return;
    }
    const trigger = editorDocument.createElement("button");
    trigger.id = "browser-files-trigger";
    trigger.className = "browser-chrome-trigger";
    trigger.type = "button";
    trigger.textContent = "Browser files";
    trigger.setAttribute("aria-haspopup", "dialog");
    trigger.setAttribute("aria-controls", "browser-files-panel");
    trigger.setAttribute("aria-expanded", "false");
    const panel = editorDocument.createElement("section");
    panel.id = "browser-files-panel";
    panel.className = "browser-chrome-panel";
    panel.setAttribute("role", "dialog");
    panel.setAttribute("aria-label", "Browser files");
    panel.hidden = true;
    const heading = editorDocument.createElement("strong");
    heading.className = "browser-chrome-heading";
    heading.textContent = "In this browser";
    const website = editorDocument.createElement("a");
    website.href = webHeader.querySelector(".brand").href;
    website.textContent = "Figure Tool website";
    website.target = "_top";
    headerActions.querySelector(".web-about-panel").append(website);
    // These links previously belonged to the outer page. Preserve full-page
    // navigation when their controls move into the editor's document.
    headerActions.querySelectorAll(".web-about-panel a").forEach(link => {
      link.href = link.href;
      link.target = "_top";
    });
    // Appearance stays visible beside Browser files. Only file/about controls
    // belong in its popover; moving this same control preserves its preference
    // owner and handlers without adding settings to the shared editor.
    appearance.classList.add("browser-chrome-appearance");
    header.prepend(trigger, appearance);
    panel.append(heading, toolbar, headerActions);
    root.append(panel);
    const position = () => {
      const bounds = trigger.getBoundingClientRect();
      const top = bounds.bottom + 6;
      panel.style.top = `${top}px`;
      panel.style.left = `${Math.max(8, Math.min(bounds.right - panel.offsetWidth, editorDocument.documentElement.clientWidth - panel.offsetWidth - 8))}px`;
      panel.style.maxHeight = `${Math.max(100, editorDocument.documentElement.clientHeight - top - 12)}px`;
    };
    const close = (restoreFocus = false) => {
      panel.hidden = true;
      trigger.setAttribute("aria-expanded", "false");
      headerActions.querySelector(".web-about").open = false;
      if (restoreFocus) trigger.focus();
    };
    const open = (focusControls = false) => {
      panel.hidden = false;
      trigger.setAttribute("aria-expanded", "true");
      position();
      if (focusControls) toolbar.querySelector("button:not(:disabled)")?.focus();
    };
    trigger.addEventListener("click", () => {
      if (panel.hidden) open(true); else close();
    });
    editorDocument.addEventListener("focusin", event => {
      if (!panel.hidden && !panel.contains(event.target) && !trigger.contains(event.target)) close();
    });
    editorDocument.addEventListener("pointerdown", event => {
      if (!panel.hidden && !panel.contains(event.target) && !trigger.contains(event.target)) close();
    }, true);
    editorDocument.addEventListener("keydown", event => {
      if (event.key === "Escape" && !panel.hidden) {
        event.preventDefault();
        event.stopPropagation();
        close(true);
      }
    }, true);
    frame.contentWindow.addEventListener("resize", () => { if (!panel.hidden) position(); });
    document.addEventListener("pointerdown", () => close());
    toolbar.querySelectorAll(".browser-toolbar-actions button").forEach(button => button.addEventListener("click", () => close()));
    library.addEventListener("close", () => trigger.focus());
    browserChrome = { trigger, panel, open, close };
    status.removeAttribute("role");
    trigger.title = status.textContent;
    webHeader.hidden = true;
    document.body.dataset.browserChrome = "integrated";
  }
  // The web host keeps its own appearance preference, separate from saved artwork
  // and the installed Superbench settings. Keep the legacy engine namespace stable.
  const themeStorageKey = "figureStudio.webTheme.v1";
  const themeButtons = document.querySelectorAll("[data-browser-theme]");
  let themePreference = null, activeTheme = "light", appliedTheme = null;
  const api = () => {
    try { return frame.contentWindow?.FigureStudio?.app; }
    catch { return null; }
  };
  let systemTheme;
  try { systemTheme = window.matchMedia?.("(prefers-color-scheme: dark)"); }
  catch { /* Light remains usable when system appearance cannot be queried. */ }
  if (!localFile) {
    try {
      const savedTheme = window.localStorage.getItem(themeStorageKey);
      if (["light", "dark-graphite"].includes(savedTheme)) themePreference = savedTheme;
    } catch { /* Appearance can still be changed for this visit without storage. */ }
  }
  function applyEditorTheme() {
    try {
      const app = api();
      if (!app?.applyProjectAppearance) return;
      app.applyProjectAppearance({ theme: activeTheme, effectiveTheme: activeTheme });
      appliedTheme = activeTheme;
    } catch { /* Retry when the editor has finished opening. */ }
  }
  function setTheme(theme, remember = false) {
    activeTheme = theme === "dark-graphite" ? "dark-graphite" : "light";
    document.documentElement.dataset.webTheme = activeTheme;
    for (const button of themeButtons) {
      const selected = button.dataset.browserTheme === activeTheme;
      button.setAttribute("aria-pressed", String(selected));
      const name = button.textContent.trim();
      button.title = selected ? `${name} appearance selected` : `Use ${name.toLowerCase()} appearance`;
    }
    if (remember) {
      themePreference = activeTheme;
      if (!localFile) {
        try { window.localStorage.setItem(themeStorageKey, activeTheme); }
        catch { /* A blocked preference write must not interrupt editing or saving. */ }
      }
    }
    applyEditorTheme();
  }
  setTheme(themePreference || (systemTheme?.matches ? "dark-graphite" : "light"));
  themeButtons.forEach(button => button.addEventListener("click", () => setTheme(button.dataset.browserTheme, true)));
  const followSystemTheme = event => {
    if (!themePreference) setTheme(event.matches ? "dark-graphite" : "light");
  };
  if (systemTheme?.addEventListener) systemTheme.addEventListener("change", followSystemTheme);
  else systemTheme?.addListener?.(followSystemTheme);
  frame.addEventListener("load", () => { appliedTheme = null; applyEditorTheme(); });
  let timer;
  function launchFailure(message, localFile = false) {
    clearInterval(timer);
    frame.hidden = true;
    status.textContent = localFile ? "Open the local browser preview to continue" : "The editor could not open";
    status.dataset.state = "startup-error";
    document.getElementById("browser-launch-error").hidden = false;
    document.getElementById("browser-launch-title").textContent = localFile ? "Open the browser preview" : "The editor could not open";
    document.getElementById("browser-launch-message").textContent = message;
    document.getElementById("browser-local-server-help").hidden = !localFile;
    document.getElementById("browser-local-launch").hidden = !localFile;
    document.getElementById("browser-launch-retry").hidden = localFile;
  }
  document.getElementById("browser-launch-retry").addEventListener("click", () => window.location.reload());
  // A file URL cannot fetch the shared editor assets or access its iframe as a
  // same-origin document. Do not start the editor or storage under that origin.
  if (localFile) {
    const localLaunch = document.getElementById("browser-local-launch");
    // Release staging replaces this legacy consumer URL. Only the canonical
    // source preview needs its current root and command explained here.
    if (localLaunch.origin === "http://127.0.0.1:4177") {
      localLaunch.href = "http://127.0.0.1:4177/web/";
      document.getElementById("browser-local-server-help").innerHTML = "Keep the local preview server running. From the Figure source folder, run <code>python -m http.server 4177 --bind 127.0.0.1 --directory .</code>.";
    }
    launchFailure("Opening the HTML file directly prevents this browser from loading the editor and its saved-work library. Use the local browser preview below.", true);
    return;
  }
  const editorUrl = new URL(frame.dataset.editorSrc, document.baseURI);
  editorUrl.searchParams.set("bsd_theme", activeTheme);
  editorUrl.searchParams.set("bsd_effective_theme", activeTheme);
  frame.src = editorUrl.href;
  const openingStarted = Date.now();
  let currentId = crypto.randomUUID(), revision = null, customName = "";
  let observedKey = "", savedKey = "", failed = false, busy = false, started = false;
  let saving = null;
  const metadata = () => api()?.getBrowserSessionState?.();
  function feedback(message, state = "ready") {
    status.textContent = message;
    status.dataset.state = state;
    if (state === "saved") status.dataset.sessionKey = savedKey;
    retryButton.hidden = state !== "error";
    copyButton.hidden = state !== "conflict";
    announcements.textContent = message;
    if (browserChrome) {
      browserChrome.trigger.title = message;
      browserChrome.trigger.dataset.saveState = state;
      browserChrome.trigger.textContent = state === "error" ? "Browser files · Save failed"
        : state === "conflict" ? "Browser files · Save conflict" : "Browser files";
      if (state === "error" || state === "conflict") browserChrome.open();
    }
  }
  function failure(error) {
    failed = true;
    feedback(error.name === "ConflictError" ? error.message
      : error.name === "QuotaExceededError" ? "Browser storage is full. Download your work, remove an older browser copy, then retry."
      : "Could not save in this browser. Your current work is still open; download a file and retry.",
    error.name === "ConflictError" ? "conflict" : "error");
  }
  async function save(force = false) {
    if (saving) { await saving; return force ? save(true) : !failed; }
    const state = metadata();
    if (!state?.ready) return false;
    if (!force && (state.key === savedKey || (!savedKey && state.key === observedKey))) return !failed;
    if (state.busy) return false;
    saving = (async () => {
      try {
        feedback("Saving in this browser…", "saving");
        const owner = { app: api(), id: currentId, revision, name: customName };
        const snapshot = await (owner.app.captureBrowserSessionAsync
          ? owner.app.captureBrowserSessionAsync() : owner.app.captureBrowserSession());
        // A project switch or iframe reload must never commit an old snapshot
        // into a different browser record or acknowledge the new editor.
        if (api() !== owner.app || currentId !== owner.id || revision !== owner.revision) return false;
        const record = await store.save(owner.id, snapshot, owner.name, owner.revision);
        if (api() !== owner.app || currentId !== owner.id || revision !== owner.revision) return false;
        revision = record.revision;
        savedKey = snapshot.key;
        observedKey = savedKey;
        const current = owner.app.acknowledgeBrowserSession(savedKey, snapshot);
        failed = false;
        feedback(current
          ? `Saved in this browser · ${new Date(record.updatedAt).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`
          : "New edits waiting for browser save…", current ? "saved" : "pending");
        if (library.open) await renderLibrary();
        return true;
      } catch (error) {
        if (error.code === "BROWSER_CAPTURE_STALE") feedback("New edits waiting for browser save…", "pending");
        else failure(error);
        return false;
      }
    })();
    try { return await saving; } finally { saving = null; }
  }
  async function resume(id, previousIndex = null) {
    if (busy) return;
    busy = true;
    try {
      if (!await save() && !window.confirm("Current edits could not be saved in this browser. Download them before continuing. Discard the current edits and reopen this saved work?")) return;
      const record = await store.get(id);
      if (!record) throw new Error("Browser save no longer exists.");
      const snapshot = previousIndex === null ? record.current : record.previous[previousIndex];
      if (!snapshot) throw new Error("That earlier save is no longer available.");
      const restored = await api().restoreBrowserSession(snapshot.workspace, { densePdfAssets: snapshot.densePdfAssets });
      currentId = previousIndex === null ? id : crypto.randomUUID();
      revision = previousIndex === null ? record.revision : null;
      customName = previousIndex === null ? record.name : `${record.name} — recovered`;
      observedKey = restored.key;
      savedKey = previousIndex === null ? restored.key : "";
      failed = false;
      library.close();
      if (previousIndex !== null) await save(true);
      else feedback(`Saved in this browser · ${record.name}`, "saved");
      frame.focus();
    } catch (error) { failure(error); } finally { busy = false; }
  }
  function button(label, action) {
    const node = document.createElement("button");
    node.type = "button";
    node.textContent = label;
    node.addEventListener("click", async () => {
      node.disabled = true;
      try { await action(); } catch (error) { failure(error); }
      finally { node.disabled = false; }
    });
    return node;
  }
  async function download(snapshot, name) {
    const blob = snapshot.densePdfAssets?.length
      ? await api().encodeBrowserSessionSnapshot(snapshot)
      : new Blob([JSON.stringify(snapshot.workspace, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${name.replace(/[<>:"/\\|?*]+/g, "-") || "figure-project"}.fsproject`;
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 30000);
  }
  async function renderLibrary() {
    const entries = await store.list();
    list.replaceChildren();
    document.getElementById("browser-library-empty").hidden = entries.length > 0;
    for (const entry of entries) {
      const row = document.createElement("article");
      row.className = "browser-project";
      row.dataset.projectId = entry.id;
      if (entry.thumbnail.startsWith("data:image/png;")) {
        const image = document.createElement("img");
        image.src = entry.thumbnail;
        image.alt = "";
        row.append(image);
      }
      const content = document.createElement("div");
      const heading = document.createElement("h3");
      heading.textContent = entry.name;
      const info = document.createElement("p");
      info.textContent = `${entry.documentCount} document${entry.documentCount === 1 ? "" : "s"} · ${new Date(entry.updatedAt).toLocaleString()}`;
      const actions = document.createElement("div");
      actions.className = "browser-project-actions";
      actions.append(button("Resume", () => resume(entry.id)));
      actions.append(button("Download project", async () => {
        if (entry.id === currentId && !await save()) return;
        const record = await store.get(entry.id);
        if (record) await download(record.current, record.name);
      }));
      actions.append(button("Rename", async () => {
        const name = window.prompt("Name this browser save:", entry.name);
        if (!name?.trim()) return;
        if (entry.id === currentId) { customName = name.trim(); await save(true); }
        else {
          const record = await store.get(entry.id);
          if (!record) return;
          await store.save(entry.id, record.current, name.trim(), record.revision);
          await renderLibrary();
        }
      }));
      const removeButton = button("Remove", async () => {
        if (!window.confirm(`Remove “${entry.name}” and its earlier saves from this browser? Downloaded files are kept.`)) return;
        if (saving) await saving;
        await store.remove(entry.id, entry.id === currentId ? revision : entry.revision);
        if (entry.id === currentId) {
          currentId = crypto.randomUUID(); revision = null; customName = "";
          savedKey = ""; observedKey = metadata()?.key || "";
          feedback("Browser copy removed. Download this open work or edit it to start another browser save.");
        }
        await renderLibrary();
      });
      removeButton.disabled = entry.id === currentId;
      if (removeButton.disabled) removeButton.title = "Open another project before removing this current browser save.";
      actions.append(removeButton);
      if (entry.recoveryCount) actions.append(button("Earlier saves", async () => {
        const record = await store.get(entry.id);
        if (!record) return;
        const recovery = document.createElement("div");
        recovery.className = "browser-recovery";
        recovery.append("Reopening an earlier save creates a separate copy. ");
        record.previous.forEach((snapshot, index) => recovery.append(button(
          `Recover ${new Date(snapshot.savedAt).toLocaleTimeString()}`, () => resume(entry.id, index)
        )));
        content.querySelector(".browser-recovery")?.remove();
        content.append(recovery);
      }));
      content.append(heading, info, actions);
      row.append(content);
      list.append(row);
    }
  }
  async function showLibrary() {
    try { await renderLibrary(); if (!library.open) library.showModal(); }
    catch (error) { failure(error); }
  }
  document.getElementById("browser-library-open").addEventListener("click", showLibrary);
  document.getElementById("browser-library-close").addEventListener("click", () => library.close());
  document.getElementById("browser-download").addEventListener("click", () => api()?.saveProject());
  document.getElementById("browser-open").addEventListener("click", () => api()?.openBrowserFile());
  document.getElementById("browser-retry").addEventListener("click", () => { failed = false; save(true); });
  document.getElementById("browser-save-copy").addEventListener("click", () => {
    currentId = crypto.randomUUID(); revision = null;
    customName = `${customName || metadata()?.title || "Figure"} — copy`;
    failed = false; save(true);
  });
  document.getElementById("browser-persist").addEventListener("click", async () => {
    const result = document.getElementById("browser-persistence-status");
    try {
      const granted = await navigator.storage?.persist?.();
      result.textContent = granted ? "Persistent storage enabled. Clearing site data still removes these saves."
        : "Persistent storage was not granted. Keep downloaded backups.";
    } catch { result.textContent = "Persistent storage is unavailable. Keep downloaded backups."; }
  });
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "hidden" && !busy && !failed) save();
  });
  window.addEventListener("beforeunload", event => {
    const state = metadata();
    if (state?.ready && state.key !== (savedKey || observedKey)) { event.preventDefault(); event.returnValue = ""; }
  });
  async function tick() {
    if (appliedTheme !== activeTheme) applyEditorTheme();
    if (!started) {
      let editorFailed = false;
      try { editorFailed = frame.contentDocument?.getElementById("figureStudioRoot")?.dataset.qaState === "error"; }
      catch { /* A failed or cross-origin frame still reaches the bounded timeout. */ }
      if (editorFailed || Date.now() - openingStarted > 60000) {
        launchFailure("The editor could not load all of its files. Reload the page. If it still fails, restart the local preview. Your browser saves have not been changed.");
        return;
      }
    }
    const state = metadata();
    if (!state?.ready || busy) return;
    if (!started) {
      started = true;
      busy = true;
      applyEditorTheme();
      observedKey = state.key;
      document.querySelectorAll(".browser-toolbar button").forEach(node => { node.disabled = false; });
      try {
        await integrateBrowserChrome();
        await store.open();
        feedback("Autosave ready · Stored only in this browser");
        if ((await store.list()).length) await showLibrary();
      } catch (error) { failure(error); }
      finally { busy = false; }
    } else if (!state.busy && !failed) await save();
  }
  timer = setInterval(tick, 1200);
  window.addEventListener("pagehide", () => clearInterval(timer));
  window.addEventListener("pageshow", event => { if (event.persisted) timer = setInterval(tick, 1200); });
})();
