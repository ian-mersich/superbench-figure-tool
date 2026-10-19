/* Browser-only persistence. No requests, accounts, credentials, or editor-format fork. */
(function () {
  "use strict";
  const DATABASE = "superbench.figure.web.v1"; // Stable across editor revisions and URL paths.
  let connection;
  function conflict() {
    return Object.assign(new Error("This work changed in another tab. Reopen its latest save or save a separate copy."), { name: "ConflictError" });
  }
  function open() {
    if (connection) return connection;
    connection = new Promise((resolve, reject) => {
      if (!window.indexedDB) { reject(new Error("This browser does not allow local document storage.")); return; }
      const request = indexedDB.open(DATABASE, 1);
      request.onupgradeneeded = () => {
        request.result.createObjectStore("projects", { keyPath: "id" });
        request.result.createObjectStore("summaries", { keyPath: "id" });
      };
      request.onerror = () => reject(request.error);
      request.onblocked = () => reject(new Error("Close other Figure tabs, then retry browser storage."));
      request.onsuccess = () => {
        const database = request.result;
        database.onversionchange = () => { database.close(); connection = null; };
        resolve(database);
      };
    }).catch(error => { connection = null; throw error; });
    return connection;
  }
  async function read(store, key) {
    const database = await open();
    return new Promise((resolve, reject) => {
      const transaction = database.transaction(store, "readonly");
      const request = key === undefined ? transaction.objectStore(store).getAll() : transaction.objectStore(store).get(key);
      transaction.oncomplete = () => resolve(request.result);
      transaction.onabort = () => reject(transaction.error || new Error("Could not read browser saves."));
    });
  }
  async function save(id, snapshot, name, expectedRevision) {
    if (!["figureStudio.workspaceProject.v1", "figureStudio.workspaceProject.v2"].includes(snapshot?.workspace?.schema)) throw new Error("That browser save is not a Figure project.");
    // Blob structured cloning keeps the immutable dense source base out of
    // main-thread JSON, including both retained recovery snapshots.
    const densePdfAssets = snapshot.densePdfAssets === undefined ? undefined : structuredClone(snapshot.densePdfAssets);
    if (densePdfAssets !== undefined && (!Array.isArray(densePdfAssets) || densePdfAssets.length > 8)) throw new Error("That browser PDF asset list is invalid.");
    const database = await open();
    return new Promise((resolve, reject) => {
      const transaction = database.transaction(["projects", "summaries"], "readwrite");
      const projects = transaction.objectStore("projects");
      const request = projects.get(id);
      let result, failure;
      transaction.oncomplete = () => resolve(result); // Report saved only after atomic commit.
      transaction.onabort = () => reject(failure || transaction.error || new Error("Browser save failed. Your last successful save is still available."));
      request.onsuccess = () => {
        try {
          const previous = request.result;
          if ((previous?.revision ?? null) !== expectedRevision) throw conflict();
          const now = new Date().toISOString();
          const current = { workspace: snapshot.workspace, thumbnail: snapshot.thumbnail || "", savedAt: now,
            ...(densePdfAssets?.length ? { densePdfAssets } : {}) };
          result = {
            id, name: String(name || snapshot.title || "Untitled figure").slice(0, 160),
            revision: (previous?.revision || 0) + 1,
            createdAt: previous?.createdAt || now, updatedAt: now,
            current, previous: previous ? [previous.current, ...previous.previous].slice(0, 2) : []
          };
          projects.put(result);
          transaction.objectStore("summaries").put({
            id, name: result.name, revision: result.revision, updatedAt: now,
            thumbnail: current.thumbnail, documentCount: current.workspace.documents.length,
            recoveryCount: result.previous.length
          });
        } catch (error) {
          failure = error;
          try { transaction.abort(); } catch { /* The transaction may already have aborted. */ }
        }
      };
    });
  }
  async function remove(id, expectedRevision) {
    const database = await open();
    return new Promise((resolve, reject) => {
      const transaction = database.transaction(["projects", "summaries"], "readwrite");
      const request = transaction.objectStore("projects").get(id);
      let failure;
      transaction.oncomplete = () => resolve();
      transaction.onabort = () => reject(failure || transaction.error || new Error("Could not remove that browser save."));
      request.onsuccess = () => {
        if ((request.result?.revision ?? null) !== expectedRevision) { failure = conflict(); transaction.abort(); return; }
        transaction.objectStore("projects").delete(id);
        transaction.objectStore("summaries").delete(id);
      };
    });
  }
  window.FigureBrowserStore = {
    open, save, remove,
    get: id => read("projects", id),
    list: async () => (await read("summaries")).sort((a, b) => b.updatedAt.localeCompare(a.updatedAt))
  };
})();
