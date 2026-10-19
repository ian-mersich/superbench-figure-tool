/* Browser autosave uses the same portable serializer as project downloads. */
"use strict";
importScripts("file-formats.js");

self.onmessage = ({ data }) => {
  try {
    if (data?.type !== "serialize-workspace") throw new Error("Unknown browser save request.");
    const started = performance.now();
    const workspace = self.FigureStudioFileFormats.serializeWorkspaceProject(data.source);
    const workerSerializeMs = performance.now() - started;
    const posted = performance.now();
    self.postMessage({ type: "workspace-serialized", workspace, workerSerializeMs });
    // The small second response records the worker's outbound structured-clone
    // cost separately from the canonical serializer and main-thread posting.
    self.postMessage({ type: "workspace-transport-complete", workerReturnPostMessageMs: performance.now() - posted });
  } catch (error) {
    self.postMessage({ type: "workspace-error", code: String(error?.code || ""), message: String(error?.message || error) });
  }
};
