/* Portable, read-only native source proof. No service or installed tool needed. */
"use strict";
importScripts("../vendor/pdf-lib/pdf-lib.min.js", "./pdf-knockout.js", "./pdf-knockout-proof.js");
self.onmessage = async event => {
  try {
    const proof = await self.FigureStudioPdfKnockoutProof.readSourceGroups(new Uint8Array(event.data.bytes), {
      pdfLib: self.PDFLib,
      sourceSha256: event.data.sourceSha256,
      onProgress: progress => self.postMessage({ type: "progress", progress })
    });
    self.postMessage({ type: "result", proof });
  } catch (error) {
    self.postMessage({ type: "error", message: String(error.message || error) });
  }
};
