/* Complete-only native dense builder. No DOM, SVG page or Fabric forest. */
'use strict';
importScripts('./pdf-generated-number-tokens.js','./pdf-text-spacing.js','./pdf-editable-import.js','./pdf-decoded-svg-number-precision.js','./pdf-native-glyph-records.js','./pdf-dense-source-numbers.js','./pdf-dense-text-state.js','./pdf-dense-leaf-store.js');
const protocol='figureStudio.pdfDenseWorker.v1';
let busy=false;
self.onmessage=async event=>{
 const request=event.data;
 if(busy||request?.protocol!==protocol||typeof request.requestId!=='string')return;
 busy=true;const started=performance.now(),send=packet=>self.postMessage({protocol,requestId:request.requestId,...packet});
 try{
  let store;
  if(request.action==='open'){
   // Load the bundled native handler directly inside this owned worker. The
   // display library's fallback script loader requires a DOM if the handler is
   // absent; no DOM or second main-thread parser is needed here.
   importScripts('../vendor/pdfjs-legacy/pdf.worker.js','../vendor/pdfjs-legacy/pdf.js','../vendor/pdf-lib/pdf-lib.min.js');
   self.pdfjsLib.GlobalWorkerOptions.workerSrc=new URL('../vendor/pdfjs-legacy/pdf.worker.js',self.location.href).href;
   store=await self.FigureStudioPdfDenseLeafStore.open({bytes:request.input.bytes,pageNumber:request.input.pageNumber,pdfjs:self.pdfjsLib,pdfLib:self.PDFLib,onProgress:progress=>send({type:'progress',progress})});
  }else if(request.action==='hydrate'){
   const payload=JSON.parse(request.input.serializedPayload);
   store=await self.FigureStudioPdfDenseLeafStore.hydrate(payload);
  }else throw new Error('Unknown dense worker operation.');
  const data=self.FigureStudioPdfDenseLeafStore.takeWorkerTransfer(store),buffers=[],seen=new Set(),pending=[data];
  while(pending.length){const value=pending.pop();if(!value||typeof value!=='object'||seen.has(value))continue;seen.add(value);if(ArrayBuffer.isView(value)){if(!seen.has(value.buffer)){seen.add(value.buffer);buffers.push(value.buffer);}continue;}for(const child of Object.values(value))pending.push(child);}
  const packet={protocol,requestId:request.requestId,type:'complete',data,metrics:{workerBuildMs:performance.now()-started,transferBufferCount:buffers.length,transferBytes:buffers.reduce((sum,b)=>sum+b.byteLength,0)}};
  self.postMessage(packet,buffers);
 }catch(error){send({type:'error',name:error.name,code:error.code||'',message:String(error.message||error)});}
};
