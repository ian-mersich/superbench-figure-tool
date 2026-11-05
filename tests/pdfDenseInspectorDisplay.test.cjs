// Actual extracted App renderers and actual private Page module. Explicit
// Session/native-view adapters qualify display ownership only, not PDF fidelity.
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),crypto=require('node:crypto');
const appSource=fs.readFileSync(require.resolve('../app/app.js'),'utf8'),pageSource=fs.readFileSync(require.resolve('../app/pdf-dense-page.js'),'utf8');
function extract(source,name){const start=source.search(new RegExp('^  (?:async )?function '+name+'\\(','m'));assert.ok(start>=0,name);const next=/\n  (?:async )?function /.exec(source.slice(start+5));assert.ok(next,name);return source.slice(start,start+5+next.index);}
// Frozen literal pre-change renderer, from the reviewed 3de22fdf App snapshot.
const legacyRendererSource="  function pdfEntrySummaryInspectorHtml(object) {\n    const summary = pdfEntrySummaryForObject(object);\n    if (!summary) return \"\";\n    const batch = pdfEntryBatchSummaryForObject(object);\n    const editability = summary.editability || {};\n    const source = summary.source || {};\n    const sourceBacked = [\"source-backed\", \"source-backed-fallback\"].includes(summary.actualMode);\n    const sourceReplacement = object?.figureStudioPdfSourceReplacement || object?.importMeta?.pdfSourceReplacement || object?.importMeta?.pdf_source_replacement || null;\n    const statusLabel = sourceBacked ? \"Layout only\" : summary.actualMode === \"partial-reconstruction\" ? \"Partial\" : \"Reconstructed\";\n    return appearanceInspectorDetailsHtml(\"pdf-entry-summary\", \"PDF import\", `\n      <div data-qa-pdf-entry-summary data-qa-pdf-entry-mode=\"${escapeHtml(summary.requestedMode || \"unknown\")}\" data-qa-pdf-entry-result=\"${escapeHtml(summary.actualMode || \"unknown\")}\">\n        <div class=\"asi-pdf-text-run-header\"><strong>Actual result: ${escapeHtml(summary.resultLabel || \"PDF import\")}</strong><span class=\"asi-status-chip ${sourceBacked ? \"source\" : \"editable\"}\">${escapeHtml(statusLabel)}</span></div>\n        <dl>\n          <dt>Chosen mode</dt><dd>${escapeHtml(summary.requestedModeLabel || pdfEntryModeLabel(summary.requestedMode))}</dd>\n          <dt>Editable content</dt><dd>${editability.sourcePathCount !== undefined\n            ? `${Number(editability.sourcePathCount).toLocaleString()} source paths; ${Number(editability.editableTextCount).toLocaleString()} editable labels; ${Number(editability.activePathControlCount).toLocaleString()} active path controls`\n            : `${Number(editability.reconstructedObjectCount || 0).toLocaleString()} reconstructed objects; ${Number(editability.editablePathCount || 0).toLocaleString()} canvas paths; ${Number(editability.nativeEditablePathCount || 0).toLocaleString()} native editable paths`}</dd>\n          <dt>Direct Selection</dt><dd>${escapeHtml(editability.directSelectionStatus || \"Unavailable\")}</dd>\n          <dt>Source</dt><dd>${source.bytesRetained ? \"Original PDF bytes retained\" : \"Source bytes unavailable\"}${source.identityRetained ? \"; page identity retained\" : \"\"}</dd>\n          <dt>SVG export</dt><dd>${escapeHtml(summary.export?.svg || \"Review required\")}</dd>\n          <dt>PDF export</dt><dd>${escapeHtml(summary.export?.pdf || \"Review required\")}</dd>\n          <dt>Project file</dt><dd>${escapeHtml(summary.export?.project || \"Mode summary retained\")}</dd>\n        </dl>\n        ${batch && batch.aggregate?.selectedPageCount > 1 ? `\n          <div data-qa-pdf-entry-batch-summary data-qa-pdf-entry-batch-mixed=\"${batch.mixedResult ? \"true\" : \"false\"}\">\n            <p class=\"asi-status-note ${batch.mixedResult ? \"review\" : \"\"}\"><strong>Actual page results</strong> - ${escapeHtml(batch.summaryLabel)}</p>\n            <dl>\n              <dt>Selected pages</dt><dd>${escapeHtml(batch.pageScope?.selectedPages?.join(\", \") || \"\")}</dd>\n              <dt>Batch content</dt><dd>${Number(batch.aggregate.reconstructedObjectCount || 0).toLocaleString()} reconstructed objects; ${Number(batch.aggregate.canvasPathCount || 0).toLocaleString()} canvas paths; ${Number(batch.aggregate.nativeEditablePathCount || 0).toLocaleString()} native editable paths</dd>\n            </dl>\n            <ol class=\"asi-status-list\">${batch.outcomes.map((outcome) => `<li data-qa-pdf-entry-page=\"${outcome.pageNumber}\" data-qa-pdf-entry-page-outcome=\"${escapeHtml(outcome.outcome)}\"><strong>Page ${outcome.pageNumber} actual result:</strong> ${escapeHtml(outcome.resultLabel)}${outcome.fallbackReason ? ` - ${escapeHtml(outcome.fallbackReason)}` : \"\"}</li>`).join(\"\")}</ol>\n            <p class=\"asi-status-note\">${escapeHtml(batch.export.pdf)} ${escapeHtml(batch.export.svg)}</p>\n          </div>\n        ` : \"\"}\n        ${summary.fallbackReason ? `<p class=\"asi-status-note review\">Editable reconstruction was not used: ${escapeHtml(summary.fallbackReason)}</p>` : \"\"}\n        ${sourceReplacement ? `<p class=\"asi-status-note\" data-qa-pdf-current-source>Current source: ${escapeHtml(sourceReplacement.currentFilename || summary.sourceFilename || \"Placed PDF\")}, page ${Number(sourceReplacement.selectedPage || summary.pageNumber || 1)}. It replaced ${escapeHtml(sourceReplacement.previousFilename || \"an earlier PDF\")} and remains source-backed.</p>` : \"\"}\n        <div class=\"asi-actions\">\n          ${appearanceActionButtonHtml(\"replace-pdf-source\", \"Replace PDF source…\", isPdfSourceReplacementEligible(object), 'data-qa-replace-pdf-source')}\n        </div>\n        <p class=\"asi-status-note\">Replacement is limited to one unlocked, single-page source-backed placement. Editable reconstructions, multi-page batches, opened PDF documents, locked or protected objects, and unsupported imported content remain report-only.</p>\n        <p class=\"asi-status-note\">This mode does not claim full native PDF equivalence. Unsupported content remains source-backed or is reported as a fallback.</p>\n      </div>\n    `, true, \"asi-source-card\");\n  }\n";
const legacyPathRowSource="appearanceInspectorDetailsHtml(\"path-vector-geometry\", \"Path and vector geometry\", `\n        <dl>\n          <dt>Bounds</dt><dd>${bbox ? `${fmt(bbox.width / INCH, 2)} x ${fmt(bbox.height / INCH, 2)} in` : \"Multiple bounds\"}</dd>\n          <dt>Editable paths</dt><dd>${vector.editablePathCount.toLocaleString()} path${vector.editablePathCount === 1 ? \"\" : \"s\"}${vector.pathNodeCount ? `, ${vector.pathNodeCount.toLocaleString()} anchor/control handle${vector.pathNodeCount === 1 ? \"\" : \"s\"}` : \"\"}</dd>\n          <dt>PDF path source</dt><dd>${vector.nativePathAvailable\n            ? status.nativeState.nativePathRow?.cloneAndRebindSharedForm\n              ? \"Selected PDF use; export clones and rebinds only this instance\"\n              : \"Available for precise path editing\"\n            : pdfEntrySummary && !Number(pdfEntrySummary.editability?.nativeEditablePathCount || 0)\n              ? \"0 native editable paths; this mode does not expose source path geometry\"\n              : \"Not available for this selection\"}</dd>\n        </dl>\n        <div class=\"asi-actions\">\n          ${appearanceActionButtonHtml(\"edit-path-nodes\", \"Edit nodes\", pathEditEnabled)}\n          ${appearanceActionButtonHtml(\n            \"native-pdf-edit-path\",\n            status.nativeState.nativePathRow?.cloneAndRebindSharedForm\n              ? \"Edit selected PDF instance\"\n              : pdfEntrySummary && !Number(pdfEntrySummary.editability?.nativeEditablePathCount || 0) ? \"No native PDF path\" : \"Edit PDF path\",\n            nativePathEnabled,\n            `title=\"${escapeHtml(nativePathEnabled ? \"Edit the exact linked PDF path\" : \"No exact native PDF path is available for this selection\")}\"`\n          )}\n          ${appearanceActionButtonHtml(\n            \"native-pdf-convert-path-overlay\",\n            pdfEntrySummary && !Number(pdfEntrySummary.editability?.nativeEditablePathCount || 0) ? \"No path to convert\" : \"Convert native path overlay\",\n            Boolean(status.nativeState.commands?.[\"native-pdf-convert-path-overlay\"]),\n            `title=\"${escapeHtml(status.nativeState.commands?.[\"native-pdf-convert-path-overlay\"] ? \"Convert the active native path edit to a canvas overlay\" : \"Start an available native PDF path edit before converting it to an overlay\")}\"`\n          )}\n        </div>\n      `, vectorOpen)";
function pathRow(source){const a=source.indexOf('${appearanceInspectorDetailsHtml("path-vector-geometry",'),b=source.indexOf('${appearanceInspectorDetailsHtml("clip-mask-blend-filter",',a);assert.ok(a>=0&&b>a);const template=source.slice(a,b).trim();assert.ok(template.endsWith('}'));return template.slice(2,-1);}
const deepFreeze=value=>{if(value&&typeof value==='object'){Object.values(value).forEach(deepFreeze);Object.freeze(value);}return value;};
const storedSummary=()=>({requestedMode:'editable',requestedModeLabel:'Editable reconstruction',actualMode:'editable-reconstruction',resultLabel:'Legacy reconstruction',
 source:{bytesRetained:false,identityRetained:false},editability:{reconstructedObjectCount:0,editablePathCount:0,nativeEditablePathCount:0,sourcePathCount:999,editableTextCount:999,activePathControlCount:0},
 export:{svg:'Legacy SVG',pdf:'Legacy PDF',project:'Legacy project'}});
async function fixture(){
 const bytes=new Uint8Array([2,3,5,7]),sha256=crypto.createHash('sha256').update(bytes).digest('hex'),live=new WeakSet(),state={revision:0,legacyReads:0,actions:0,inspections:0,apiMissing:false};
 class Session{constructor(){live.add(this);}get source(){return {sha256,byteLength:4,pageNumber:1};}get statistics(){return {pathCount:158540};}
  get revision(){return state.revision;}get frame(){return {width:100,height:50,transform:[1,0,0,-1,0,50]};}get currentCheckpoint(){return {stateId:'s:'+state.revision};}close(){live.delete(this);}
  async request(action,input){assert.equal(action,'renderTile');const segments=input.splitIds.map((id,index)=>({kind:'nativePath',record:{id,paintOrdinal:index}}));
   segments.push({kind:'paths',startOrdinal:input.splitIds.length,endOrdinal:158540,bitmap:null});
   for(let index=0;index<24;index++)segments.push({kind:'nativeText',record:{id:'label:'+index,paintOrdinal:158540+index}});
   return {result:{canonicalPaintCount:158564,segments}};}}
 class Native{constructor(options={}){Object.assign(this,options);}setCoords(){}toObject(){return {};}dispose(){}}
 class Group extends Native{constructor(objects=[],options={}){super(options);this._objects=objects.slice();}enterGroup(object){object.group=object.parent=this;}exitGroup(object){delete object.group;delete object.parent;}}
 const text={async create(){return {entries:Array.from({length:24},(_,i)=>({id:'label:'+i,object:new Native({figureId:'label:'+i})}))};},close(){},createSourceHost:()=>new Group(),
  adopt(owner,id,host){const row=owner.entries.find(row=>row.id===id);host._objects.push(row.object);host.enterGroup(row.object);}};
 const paths={LIMIT:32,create:()=>({async acquirePath(id){return new Native({figureId:id,path:[['M',0,0],['L',1,1]]});},adoptHost(object,host){host._objects.push(object);host.enterGroup(object);},close(){}})};
 const pageContext=vm.createContext({Blob,Uint8Array,AbortController,crypto:crypto.webcrypto,
  FigureStudioPdfDenseDocumentSession:{DenseDocumentSession:Session,isSession:value=>live.has(value)},FigureStudioPdfDenseNativeText:text,FigureStudioPdfDenseNativeProxies:paths,
  fabric:{FabricObject:Native,Group,StaticCanvas:class{},LayoutManager:class{},FixedLayout:class{},classRegistry:{setClass(){}}}});
 vm.runInContext(pageSource,pageContext);const api=pageContext.FigureStudioPdfDensePage,session=new Session(),page=await api.create({session,bytes});
 const context=vm.createContext({densePdfApi:()=>state.apiMissing?undefined:api,
  appearanceInspectorDetailsHtml:(id,title,body)=>`<section data-section="${id}"><h3>${title}</h3>${body}</section>`,
  pdfEntrySummaryForObject:object=>{state.legacyReads++;return object?.importMeta?.pdfEntrySummary||object?.group?.importMeta?.pdfEntrySummary||null;},
  pdfEntryBatchSummaryForObject:()=>null,pdfEntryModeLabel:()=> 'Editable reconstruction',isPdfSourceReplacementEligible:()=>{state.actions++;return false;},
  appearanceActionButtonHtml:(_action,label,enabled)=>`<button disabled="${!enabled}">${label}</button>`});
 vm.runInContext([extract(appSource,'densePdfPageForObject'),extract(appSource,'escapeHtml'),extract(appSource,'pdfDenseInspectorPageForObject'),extract(appSource,'pdfDenseEntrySummaryInspectorHtml'),extract(appSource,'pdfEntrySummaryInspectorHtml'),
  legacyRendererSource.replace('function pdfEntrySummaryInspectorHtml(','function legacyPdfEntrySummaryInspectorHtml(')].join('\n'),context);
 const nativeButton=vm.runInContext('('+extract(appSource,'appearanceActionButtonHtml')+')',context);
 function row(object,options={}){
  const vector=options.vector||{editablePathCount:1,pathNodeCount:5,nativePathAvailable:false},status=options.status||{nativeState:{commands:{},nativePathRow:null}},summary=options.summary===undefined?storedSummary():options.summary;
  Object.assign(context,{densePdfInspectorPage:context.pdfDenseInspectorPageForObject(object),vector,status,pdfEntrySummary:summary,bbox:null,INCH:96,fmt:String,
   pathEditEnabled:options.pathEditEnabled??true,nativePathEnabled:options.nativePathEnabled??false,vectorOpen:true});
  const before=JSON.stringify([vector,status,summary]),button=context.appearanceActionButtonHtml;context.appearanceActionButtonHtml=nativeButton;
  try{const current=vm.runInContext(pathRow(appSource),context),legacy=vm.runInContext(legacyPathRowSource,context);assert.equal(JSON.stringify([vector,status,summary]),before);return {current,legacy};}
  finally{context.appearanceActionButtonHtml=button;}
 }
 return {api,page,session,state,context,render:object=>context.pdfEntrySummaryInspectorHtml(object),dense:object=>context.pdfDenseEntrySummaryInspectorHtml(object),
  row,createPage:()=>api.create({session:new Session(),bytes}),legacy:object=>context.legacyPdfEntrySummaryInspectorHtml(object),finish(){page.dispose();api.collect([]);}};
}

test('actual Page without any import summary renders current retained-source display',async()=>{
 const f=await fixture(),html=f.render(f.page);assert.match(html,/Editable PDF with source retained/);assert.match(html,/158,540 source paths; 24 editable labels; 0 active path controls/);
 assert.match(html,/Original PDF retained; page 1/);assert.match(html,/Save keeps the original PDF and your current edits/);assert.match(html,/as vectors for supported scenes/);
 assert.match(html,/PDF export for this editable artwork is still in development/);assert.doesNotMatch(html,/Replace PDF source|Reconstructed|Source bytes unavailable|full native equivalence/);
 assert.equal(f.state.legacyReads,0);assert.equal(f.state.actions,0);f.finish();
});

test('actual current private path and label show the same owner and current controls without changing frozen saved summary',async()=>{
 const f=await fixture(),summary=deepFreeze(storedSummary());f.page.importMeta=deepFreeze({pdfEntrySummary:summary});const before=JSON.stringify(summary),path=await f.api.acquirePath(f.page,'selected-path'),label=f.api.textEntries(f.page)[0].object;
 for(const object of [f.page,path,label]){const html=f.render(object);assert.match(html,/1 active path control</);assert.doesNotMatch(html,/1 active path controls|999|Source bytes unavailable|Replace PDF source/);}
 await f.api.acquirePath(f.page,'another-path');assert.match(f.render(f.page),/2 active path controls</);assert.equal(JSON.stringify(summary),before);assert.equal(f.state.legacyReads,0);assert.equal(f.state.actions,0);f.finish();
});

test('private display reports updating state and omits untrusted names rather than inserting markup',async()=>{
 const f=await fixture();f.page.name='<script>bad()</script>';f.page.importMeta={sourcePdfFilename:'<img src=x onerror=bad()>',pdfEntrySummary:deepFreeze(storedSummary())};
 f.state.revision++;const html=f.render(f.page);assert.match(html,/Updating artwork…/);assert.doesNotMatch(html,/<script>|<img|onerror|bad\(\)/);f.finish();
});

test('retired native child does not inherit current private display, while the new exact child does',async()=>{
 const f=await fixture(),old=await f.api.acquirePath(f.page,'selected-path');old.importMeta={pdfEntrySummary:storedSummary()};await f.api.refresh(f.page);
 const fresh=f.api.objectById(f.page,'selected-path');assert.notEqual(old,fresh);assert.equal(f.dense(old),null);assert.equal(f.render(old),f.legacy(old));assert.match(f.render(fresh),/data-qa-pdf-entry-private="true"/);f.finish();
});

test('closed Page receives no live private card or fabricated source promise',async()=>{
 const f=await fixture();f.page.importMeta={pdfEntrySummary:storedSummary()};f.page.dispose();assert.equal(f.dense(f.page),null);assert.equal(f.render(f.page),f.legacy(f.page));f.api.collect([]);
});

test('missing optional API and ordinary/lookalike objects preserve the complete old renderer output',async()=>{
 const f=await fixture(),ordinary={importMeta:{pdfEntrySummary:storedSummary()}},lookalike={type:'PdfDensePage',densePdf:f.api.descriptor(f.page),importMeta:{pdfEntrySummary:storedSummary()}},foreign={figureId:'selected-path',group:f.page,importMeta:{pdfEntrySummary:storedSummary()}};
 for(const object of [ordinary,lookalike,foreign,{},null]){assert.equal(f.dense(object),null);assert.equal(f.render(object),f.legacy(object));}
 f.state.apiMissing=true;assert.equal(f.render(ordinary),f.legacy(ordinary));assert.equal(f.render({}), '');f.finish();
});

test('ordinary source-replacement escaping and disabled eligibility are identical to the literal old renderer',async()=>{
 const f=await fixture(),ordinary={importMeta:{pdfEntrySummary:storedSummary()},figureStudioPdfSourceReplacement:{currentFilename:'<img src=x>',previousFilename:'<script>x</script>',selectedPage:1}};
 const html=f.render(ordinary);assert.equal(html,f.legacy(ordinary));assert.match(html,/&lt;img src=x&gt;/);assert.match(html,/&lt;script&gt;/);assert.match(html,/disabled="true"/);assert.doesNotMatch(html,/<img src=x>|<script>x/);f.finish();
});

for(const mode of ['source-backed','source-backed-fallback','partial-reconstruction','raster-fallback'])test('ordinary '+mode+' result keeps the literal legacy renderer and action behavior',async()=>{
 const f=await fixture(),summary=storedSummary();summary.actualMode=mode;summary.source={bytesRetained:true,identityRetained:true};summary.editability={reconstructedObjectCount:2,editablePathCount:1,nativeEditablePathCount:0,directSelectionStatus:'Legacy selection'};
 const ordinary={importMeta:{pdfEntrySummary:deepFreeze(summary)}};assert.equal(f.render(ordinary),f.legacy(ordinary));assert.doesNotMatch(f.render(ordinary),/data-qa-pdf-entry-private/);f.finish();
});

test('summary refusal produces an honest display-only unavailable notice without falling into stale source metadata',async()=>{
 const f=await fixture();f.page.importMeta={pdfEntrySummary:storedSummary()};f.context.densePdfApi=()=>({...f.api,inspectionState(){throw null;}});
 const html=f.render(f.page);assert.match(html,/current PDF artwork summary is unavailable/);assert.doesNotMatch(html,/Source bytes unavailable|Legacy reconstruction|data-qa-pdf-entry-private="true"/);assert.equal(f.state.legacyReads,0);f.finish();
});

test('single-selection rendering invokes the actual dispatcher even with no legacy summary',async()=>{
 const f=await fixture(),needle='${single ? pdfEntrySummaryInspectorHtml(first) : ""}';assert.ok(appSource.includes(needle));
 f.context.single=true;f.context.first=f.page;const output=vm.runInContext('`'+needle+'`',f.context);assert.match(output,/Editable PDF with source retained/);
 f.context.single=false;assert.equal(vm.runInContext('`'+needle+'`',f.context),'');f.finish();
});

test('actual private Page/current path/current label row hides only legacy writer buttons and preserves Edit nodes enabled state',async()=>{
 const f=await fixture(),path=await f.api.acquirePath(f.page,'same-source-path'),label=f.api.textEntries(f.page)[0].object;
 for(const object of [f.page,path,label])for(const pathEditEnabled of [false,true]){
  const inputs={pathEditEnabled,vector:deepFreeze({editablePathCount:1,pathNodeCount:5,nativePathAvailable:false}),status:deepFreeze({nativeState:{commands:{'native-pdf-convert-path-overlay':true}}}),summary:deepFreeze(storedSummary())};
  const {current}=f.row(object,inputs);assert.match(current,/Original PDF retained; use Point Selection for supported path points\./);assert.match(current,/data-qa-dense-pdf-path-source/);
  assert.doesNotMatch(current,/native-pdf-edit-path|native-pdf-convert-path-overlay|0 native editable paths|No native PDF path|No path to convert/);
  const edit=current.match(/<button[^>]+data-appearance-inspector-action="edit-path-nodes"[^>]*>/)[0];assert.equal(edit.includes('disabled'),!pathEditEnabled);
 }f.finish();
});

for(const branch of ['native-shared','native-plain','zero-count','no-summary','unavailable'])test('ordinary row '+branch+' preserves complete original markup and both legacy actions',async()=>{
 const f=await fixture(),options={vector:{editablePathCount:0,pathNodeCount:0,nativePathAvailable:branch.startsWith('native')},status:{nativeState:{nativePathRow:{cloneAndRebindSharedForm:branch==='native-shared'},commands:{'native-pdf-convert-path-overlay':true}}},nativePathEnabled:true};
 if(branch==='no-summary')options.summary=null;if(branch==='unavailable'){options.summary=storedSummary();options.summary.editability.nativeEditablePathCount=1;}
 const result=f.row({},options);assert.equal(result.current,result.legacy);assert.match(result.current,/data-appearance-inspector-action="native-pdf-edit-path"/);assert.match(result.current,/data-appearance-inspector-action="native-pdf-convert-path-overlay"/);f.finish();
});

test('metadata lookalikes, retired children and closed owners keep old row while independent copies resolve their own actual paths',async()=>{
 const f=await fixture(),old=await f.api.acquirePath(f.page,'same-id');await f.api.refresh(f.page);const fresh=f.api.objectById(f.page,'same-id');
 const copy=await f.createPage(),copyPath=await f.api.acquirePath(copy,'same-id');assert.notEqual(f.api.descriptor(copy).assetId,f.api.descriptor(f.page).assetId);
 assert.equal(f.context.pdfDenseInspectorPageForObject(fresh),f.page);assert.equal(f.context.pdfDenseInspectorPageForObject(copyPath),copy);
 for(const object of [fresh,copyPath])assert.match(f.row(object).current,/data-qa-dense-pdf-path-source/);
 for(const object of [old,{figureId:'same-id',densePdf:f.api.descriptor(f.page),group:f.page}]){const value=f.row(object);assert.equal(value.current,value.legacy);}
 copy.dispose();assert.equal(f.row(copyPath).current,f.row(copyPath).legacy);f.state.apiMissing=true;assert.equal(f.row({}).current,f.row({}).legacy);f.finish();
});
