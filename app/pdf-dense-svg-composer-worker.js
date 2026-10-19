'use strict';
importScripts('./pdf-dense-svg-composer.js','./pdf-dense-svg-composer-core.js');
const protocol='figureStudio.pdfDenseSvgComposer.v1';let busy=false;
self.onmessage=async event=>{const request=event.data;if(busy||request?.protocol!==protocol||typeof request.requestId!=='string')return;busy=true;const started=performance.now();try{const result=await FigureStudioPdfDenseSvgComposerCore.compose(request.input);self.postMessage({protocol,requestId:request.requestId,type:'complete',result,metrics:{elapsedMs:performance.now()-started,slotCount:request.input.slots.length,outputBytes:result.size}});}catch(error){self.postMessage({protocol,requestId:request.requestId,type:'error',name:error?.name||'Error',code:error?.code||'',message:String(error?.message||error)});}};
