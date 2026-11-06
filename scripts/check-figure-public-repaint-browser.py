"""Finite public beta.6 repaint regression, bound to an explicitly supplied candidate.

Uses real Library/inspector/history/file UI and reads existing lower-canvas pixels.
No source hook requests a render. Output stays in the canonical ignored QA root.
"""
import argparse, asyncio, base64, contextlib, functools, hashlib, http.server
import importlib.util, io, json, math, os, subprocess, sys, threading, traceback
from pathlib import Path
from PIL import Image, ImageChops, ImageStat
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'qa_artifacts/public-repaint-browser-20261015'
sys.path.insert(0,str(ROOT/'scripts'))
from figure_studio_entry_qa import enter_current_document_async, show_library_async
from playwright.async_api import async_playwright
spec=importlib.util.spec_from_file_location('native_comparators',ROOT/'scripts/check-rna-artwork-browser.py')
native=importlib.util.module_from_spec(spec);spec.loader.exec_module(native)

R=dict(status='prepared-not-run',cases=[],checks=[],captures=[],pageErrors=[],consoleErrors=[],closure={})
ARGS=None
def sha(raw):return hashlib.sha256(raw).hexdigest()
def write(name,value):
    (OUT/name).write_text(json.dumps(value,indent=2)+'\n',encoding='utf8')
def check(case,name,passed,detail=None):
    R['checks'].append(dict(case=case,name=name,passed=bool(passed),detail=detail))
    if not passed:raise AssertionError(case+': '+name+': '+str(detail))
def inventory(root):
    rows=[]
    for folder,dirs,files in os.walk(root,followlinks=False):
        for entry in [*(Path(folder)/n for n in dirs),*(Path(folder)/n for n in files)]:
            if entry.is_symlink() or getattr(entry,'is_junction',lambda:False)():raise ValueError('Candidate contains link: '+str(entry))
        for name in sorted(files):
            p=Path(folder)/name;raw=p.read_bytes();rows.append(dict(path=p.relative_to(root).as_posix(),size=len(raw),sha256=sha(raw)))
    rows.sort(key=lambda x:x['path'])
    return dict(files=rows,sha256=sha(json.dumps(rows,sort_keys=True,separators=(',',':')).encode()))
class Quiet(http.server.SimpleHTTPRequestHandler):
    def translate_path(self,path):
        # Windows extended paths reject mixed separators from URL directory tails.
        return os.path.normpath(super().translate_path(path))
    def log_message(self,*_):pass
    def copyfile(self,source,output):
        try:super().copyfile(source,output)
        except (ConnectionAbortedError,ConnectionResetError,BrokenPipeError):pass

PIXELS="""id=>{const o=FigureStudio.app.getObjectByIdForQa(id),c=o.canvas,e=c.lowerCanvasEl,p=o.getCoords().map(p=>fabric.util.transformPoint(p,c.viewportTransform));return {data:e.toDataURL('image/png'),width:e.width,height:e.height,crop:[Math.floor(Math.min(...p.map(p=>p.x))*e.width/c.width)-6,Math.floor(Math.min(...p.map(p=>p.y))*e.height/c.height)-6,Math.ceil(Math.max(...p.map(p=>p.x))*e.width/c.width)+6,Math.ceil(Math.max(...p.map(p=>p.y))*e.height/c.height)+6]}}"""
async def witness(frame,case,operation,stage,owner,crop=None):
    await frame.evaluate('()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))')
    raw=await frame.evaluate(PIXELS,owner)
    data=base64.b64decode(raw['data'].split(',',1)[1]);image=Image.open(io.BytesIO(data)).convert('RGB')
    crop=crop or raw['crop'];tile=image.crop(crop)
    name=f'{case}/{operation}-{stage}.png';(OUT/name).write_bytes(data)
    row=dict(file=name,sha256=sha(data),size=list(image.size),crop=crop,cropRgbSha256=sha(tile.tobytes()),bluePixels=sum(all(abs(p[i]-(39,125,168)[i])<=2 for i in range(3)) for p in tile.get_flattened_data()))
    return row,tile
def changed(a,b):
    return sum(p!=(0,0,0) for p in ImageChops.difference(a,b).get_flattened_data())
def painted_color_pixels(record,color):
    rgb=tuple(int(color[index:index+2],16) for index in (1,3,5))
    image=Image.open(OUT/record['file']).convert('RGB').crop(record['crop'])
    return sum(all(abs(pixel[index]-rgb[index])<=2 for index in range(3)) for pixel in image.get_flattened_data())
def history_pixel_comparison(a,b,operation,native_comparison):
    """Classify reconstructed history edges only, with mandatory native proof.

    The full-canvas maximum-channel threshold borrowed from thumbnails rejected
    boundary-only differences despite unchanged vector content. The reviewed policy
    keeps mean<=0.25 and requires every changed pixel to be boundary-adjacent
    in BOTH images; a changed solid interior or crop edge always fails.
    Part/palette history remains pixel-exact. Immediate edit/grid checks do not
    use this classifier.
    """
    reconstruction=operation in ['soft-to-thin','replace-selected']
    delta_limit=native_comparison.get('maximumDerivedSceneDifference') if isinstance(native_comparison,dict) else None
    native_passed=bool(isinstance(native_comparison,dict) and native_comparison.get('passed') is True
        and not native_comparison.get('mismatches') and isinstance(delta_limit,(int,float))
        and math.isfinite(delta_limit) and 0<=delta_limit<=.01)
    result=dict(passed=False,nativeProofPassed=native_passed,reconstructedHistory=reconstruction)
    if a.size!=b.size:
        return {**result,'reason':'image-size-difference','beforeSize':list(a.size),'afterSize':list(b.size)}
    a,b=a.convert('RGB'),b.convert('RGB')
    delta=ImageChops.difference(a,b)
    mean=sum(ImageStat.Stat(delta).mean)/3;maximum=max(x[1] for x in delta.getextrema())
    left,right=a.load(),b.load()
    total=solid_before=solid_after=crop_edges=0
    for y in range(a.height):
        for x in range(a.width):
            if left[x,y]==right[x,y]:continue
            total+=1
            if x in (0,a.width-1) or y in (0,a.height-1):
                crop_edges+=1;continue
            solid_before+=all(left[x+dx,y+dy]==left[x,y] for dx in (-1,0,1) for dy in (-1,0,1))
            solid_after+=all(right[x+dx,y+dy]==right[x,y] for dx in (-1,0,1) for dy in (-1,0,1))
    bounded_edges=solid_before==solid_after==crop_edges==0
    result.update(changedPixels=total,meanChannelDifference=mean,maximumChannelDifference=maximum,
        changedSolidInteriorBefore=solid_before,changedSolidInteriorAfter=solid_after,changedCropEdgePixels=crop_edges,
        passed=native_passed and (mean<=.25 and bounded_edges if reconstruction else total==0),
        policy='Reviewed reconstructed style/replacement history only: mean<=0.25, every changed pixel within one pixel of a color boundary in BOTH images, zero changed crop-edge pixels, and mandatory native comparison preserving owner IDs/metadata/paths/paints/hierarchy with <=0.01px derived geometry. Tree-node IDs may regenerate under native.geometry; maximum channel difference is diagnostic.' if reconstruction else 'Exact drawing-crop pixels for part/palette history, plus mandatory native comparison preserving owner IDs/metadata/paths/paints/hierarchy with <=0.01px derived geometry; reconstructed tree-node IDs are omitted.')
    return result

async def launch(browser,base,size,theme):
    context=await browser.new_context(viewport=dict(width=size[0],height=size[1]),color_scheme=theme,accept_downloads=True)
    page=await context.new_page();page.set_default_timeout(25000)
    page.on('pageerror',lambda e:R['pageErrors'].append(str(e)))
    page.on('console',lambda m:R['consoleErrors'].append(m.text) if m.type=='error' else None)
    await page.goto(base+'/',wait_until='domcontentloaded')
    frame=await (await page.wait_for_selector('#figure-editor-frame')).content_frame()
    await frame.wait_for_function('window.FigureStudio?.app?.isReady===true')
    theme_id='dark-graphite' if theme=='dark' else 'light'
    selector=page.locator('[data-browser-theme="'+theme_id+'"]')
    if await selector.count():await selector.click()
    await frame.wait_for_function('theme=>document.documentElement.dataset.theme===theme',arg=theme_id)
    await frame.wait_for_function('document.getElementById("figureStudioRoot").dataset.qaLayoutStable==="true"')
    return context,page,frame

async def library(frame):
    if await frame.evaluate('FigureStudio.app.getDocumentWorkspaceStateForQa().activeKind')=='presentation':
        if await frame.locator('.figure-studio-root').get_attribute('data-deck-pane')!='assets':
            command_button=frame.locator('.presentation-toolbar [data-deck-command="assets"]')
            if not await command_button.is_visible():
                await frame.locator('.presentation-toolbar .deck-insert-menu > summary').click()
            await command_button.click()
        # Presentation has its own Assets pane. Its Figure-only Tools tab is
        # deliberately hidden, so do not reuse the Figure tab restore action.
        await frame.locator('#assetSearchInput').wait_for(state='visible')
    else:
        await show_library_async(frame,tab='tools')
    if await frame.locator('#figureLibraryTab-assets').is_visible():
        await frame.locator('#figureLibraryTab-assets').click()
    await frame.locator('#assetCategorySelect').select_option('all');await frame.locator('#assetSubcategorySelect').select_option('all')
    await frame.locator('[data-asset-discovery="all"]').click()

async def insert(frame,asset,query):
    await frame.locator('#assetSearchInput').fill(query)
    card=frame.locator('#assetGrid [data-asset-id="'+asset+'"]')
    await card.wait_for(state='visible');await card.locator('img').evaluate('img=>img.decode()');await card.click()
    await frame.wait_for_function('id=>FigureStudio.app.getObjectByIdForQa(FigureStudio.app.getSelectionStateForQa().activeObjectId)?.scientificAssetMeta?.assetId===id',arg=asset)
    return await frame.evaluate('FigureStudio.app.getSelectionStateForQa().activeObjectId')

async def command(frame,menu,action):
    await frame.locator('[data-menu="'+menu+'"] > .menu-trigger').click()
    await frame.locator('[data-menu="'+menu+'"] [data-command="'+action+'"]').click()

async def switch(frame,kind):
    await frame.locator('#figureWorkspaceTab' if kind=='figure' else '#presentationWorkspaceTab').click()
    await frame.wait_for_function('kind=>FigureStudio.app.getDocumentWorkspaceStateForQa().activeKind===kind&&!FigureStudio.app.getDocumentWorkspaceStateForQa().switching',arg=kind)
    await frame.wait_for_function('document.getElementById("figureStudioRoot").dataset.qaLayoutStable==="true"')

async def selection_history(frame):
    return await frame.evaluate('''()=>({selection:FigureStudio.app.getSelectionStateForQa(),history:FigureStudio.app.getHistoryStateForQa()})''')

def workspace_authored(value):
    result=json.loads(json.dumps(value))
    for document in result['documents']:
        document['payload']=native.authored_document(document['payload'])
    return native.rounded(result)

def exact_differences(expected,actual,path='$'):
    if type(expected) is not type(actual):return [dict(path=path,before=expected,after=actual)]
    if isinstance(expected,dict):
        return [difference for key in sorted(expected.keys()|actual.keys()) for difference in exact_differences(expected.get(key),actual.get(key),path+'.'+key)]
    if isinstance(expected,list):
        if len(expected)!=len(actual):return [dict(path=path+'.length',before=len(expected),after=len(actual))]
        return [difference for index,(a,b) in enumerate(zip(expected,actual)) for difference in exact_differences(a,b,path+'['+str(index)+']')]
    return [] if expected==actual else [dict(path=path,before=expected,after=actual)]

async def compare_cold_workspace(frame,name,saved,opened,active_ids):
    # Same bounded fitted-view policy as the reviewed Library discovery runner:
    # raw cold state first; all content/IDs/inactive views remain exact.
    expected,actual=workspace_authored(saved),workspace_authored(opened)
    active_id=expected['workspaces'][expected['activeKind']]['activeId']
    index=next(i for i,document in enumerate(expected['documents']) if document['id']==active_id)
    differences=exact_differences(expected,actual)
    allowed={f'$.documents[{index}].view.{key}' for key in ['zoom','panX','panY']}
    view=actual['documents'][index]['view']
    valid=set(view)=={'zoom','panX','panY'} and all(isinstance(v,(int,float)) and math.isfinite(v) for v in view.values()) and view['zoom']>0
    record=dict(activeDocumentId=active_id,differences=differences,policy='Only active-document fitted zoom/pan may adapt to fresh-context rails; every inactive view and all authored content/IDs remain exact.',reference='scripts/check-library-discovery-browser.py::cold_workspace_comparison')
    write(name+'/workspace-cold-view-classification.json',record)
    check(name,'Cold complete-project Open preserves every authored tab, ID and inactive view',valid and all(d['path'] in allowed for d in differences),differences)
    if differences:
        before_native=await frame.evaluate(native.STATE,active_ids)
        await command(frame,'view','fit-screen')
        await frame.wait_for_function('document.getElementById("figureStudioRoot").dataset.qaLayoutStable==="true"')
        await frame.evaluate('()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))')
        fitted=await frame.evaluate('async()=>await FigureStudio.app.serializeWorkspace()')
        record['afterActualFit']=fitted
        fitted_view=next(document for document in fitted['documents'] if document['id']==active_id)['view']
        check(name,'Cold fitted view equals actual visible Fit to Screen',native.rounded(view)==native.rounded(fitted_view),dict(cold=view,fit=fitted_view))
        comparison=native.native_reconstruction_difference(before_native,await frame.evaluate(native.STATE,active_ids))
        check(name,'Actual Fit changes no cold authored content or native vectors',workspace_authored(opened)==workspace_authored(fitted) and comparison['passed'],comparison)
    R.setdefault('coldViewClassifications',[]).append(record)
    write(name+'/workspace-cold-view-classification.json',record)

async def save_native(frame,page,name,path,workspace=False):
    await frame.locator('#fileMenuTrigger').click()
    page.once('dialog',lambda d:d.accept(path.name))
    async with page.expect_download() as pending:
        await frame.locator('[data-menu="file"] [data-command="'+('save-workspace-project' if workspace else 'save-project')+'"]').click()
    download=await pending.value
    await download.save_as(path)
    check(name,'Actual Save downloads '+path.suffix,download.suggested_filename.endswith(path.suffix) and path.stat().st_size>0,download.suggested_filename)
    return dict(file=str(path.relative_to(OUT)),sha256=sha(path.read_bytes()),bytes=path.stat().st_size)

async def open_native(frame,page,path):
    await frame.locator('#fileMenuTrigger').click()
    async with page.expect_file_chooser() as pending:
        await frame.locator('[data-menu="file"] [data-command="open-project"]').click()
    await (await pending.value).set_files(path)
    await frame.wait_for_function("document.querySelector('#documentFileOperationStatus')?.dataset.state==='success'")
    await frame.wait_for_function('!FigureStudio.app.getDocumentWorkspaceStateForQa().switching&&document.getElementById("figureStudioRoot").dataset.qaLayoutStable==="true"')

async def edit(frame,page,row,operation,owner,action,condition):
    name=row['name'];record=dict(operation=operation,owner=owner);row['operations'].append(record)
    record['beforeNative']=await frame.evaluate(native.STATE,[owner])
    record['before'],before=await witness(frame,name,operation,'before',owner)
    await action()
    await frame.wait_for_function(condition[0],arg=condition[1])
    record['after'],after=await witness(frame,name,operation,'after',owner,record['before']['crop'])
    record['afterNative']=await frame.evaluate(native.STATE,[owner])
    record['changedAfterEdit']=changed(before,after)
    check(name,operation+' paints immediately before unrelated action',record['changedAfterEdit']>16,record['changedAfterEdit'])
    if operation=='first-part':
        check(name,'Requested part color is present in actual canvas immediately',record['before']['bluePixels']==0 and record['after']['bluePixels']>16,dict(before=record['before']['bluePixels'],after=record['after']['bluePixels']))
    await command(frame,'edit','undo')
    record['afterUndo'],undo=await witness(frame,name,operation,'after-undo',owner,record['before']['crop'])
    record['undoNative']=await frame.evaluate(native.STATE,[owner])
    comparison=native.native_reconstruction_difference(native.geometry(record['beforeNative']),native.geometry(record['undoNative']))
    check(name,operation+' Undo restores native drawing and paints',comparison['passed'],comparison)
    record['undoPixelDifferences']=changed(before,undo)
    record['undoPixelComparison']=history_pixel_comparison(before,undo,operation,comparison)
    check(name,operation+' Undo restores actual preceding drawing pixels',record['undoPixelComparison']['passed'],record['undoPixelComparison'])
    await command(frame,'edit','redo')
    record['afterRedo'],redo=await witness(frame,name,operation,'after-redo',owner,record['before']['crop'])
    record['redoNative']=await frame.evaluate(native.STATE,[owner])
    comparison=native.native_reconstruction_difference(native.geometry(record['afterNative']),native.geometry(record['redoNative']))
    check(name,operation+' Redo restores native edit and paints',comparison['passed'],comparison)
    record['redoPixelDifferences']=changed(after,redo)
    record['redoPixelComparison']=history_pixel_comparison(after,redo,operation,comparison)
    check(name,operation+' Redo restores actual edited drawing pixels',record['redoPixelComparison']['passed'],record['redoPixelComparison'])
    # Grid is a real history entry in beta.6; check it only after proving the
    # edit's own Undo/Redo, so history observes the intended author action.
    await command(frame,'view','toggle-grid')
    record['afterGrid'],grid=await witness(frame,name,operation,'after-grid',owner,record['before']['crop'])
    record['changedAfterGrid']=changed(redo,grid)
    check(name,operation+' Show Grid adds zero drawing paint changes',record['changedAfterGrid']==0,record['changedAfterGrid'])
    write('report.json',R)

async def presentation_and_workspace(browser,base,size,theme,context,page,frame,row,figure_ids):
    name=row['name']
    await frame.evaluate('id=>FigureStudio.app.selectObjectsByIdsForQa([id])',figure_ids[0])
    figure_state=await selection_history(frame)
    await enter_current_document_async(frame,kind='presentation',preset='presentation-wide',name='Asset repaint Presentation')
    await library(frame)
    # Public beta.6 exposes a palette for the next insertion, while its
    # Presentation Format panel intentionally hides direct scientific-part
    # controls. Exercise that supported visible workflow only.
    await frame.locator('#assetPaletteSelect').select_option('vivid')
    owner=await insert(frame,'core.cell.generic','Generic Eukaryotic Cell')
    inserted=await frame.evaluate(native.STATE,[owner])
    expected_paint=inserted[0]['meta']['colorOverrides']['cytoplasm']
    check(name,'Presentation Library insertion applies the visible Vivid palette',inserted[0]['meta']['paletteId']=='vivid')
    bound=[leaf for leaf in native.leaves(inserted[0]['tree']) if 'cytoplasm' in leaf['regionPaints']]
    check(name,'Presentation insertion paints its native cytoplasm with the selected palette',bool(bound) and all(str(leaf[channel]).lower()==expected_paint.lower() for leaf in bound for channel in leaf['regionPaints']['cytoplasm']))
    inserted_pixels,_=await witness(frame,name,'presentation-insert','paint',owner)
    inserted_pixels['expectedPaint']=expected_paint;inserted_pixels['matchingPaintPixels']=painted_color_pixels(inserted_pixels,expected_paint)
    check(name,'Presentation insertion visibly paints the selected palette',inserted_pixels['matchingPaintPixels']>16,inserted_pixels['matchingPaintPixels'])
    row['presentationInsertionPaint']=inserted_pixels
    if not await frame.locator('[data-rail-panel="right"]').is_visible():
        await frame.locator('.presentation-toolbar [data-deck-command="format"]').click()
    await frame.locator('[data-inspector-tab="properties"]').click()
    direct_part=await frame.locator('#scientificAssetColorList [data-asset-color-region="cytoplasm"]').is_visible()
    direct_palette=await frame.locator('#scientificAssetColorList [data-asset-palette]').is_visible()
    row['presentationCapabilities']=dict(directPartColors=direct_part,directSelectedPalette=direct_palette,
        limitation='Pinned public beta.6 intentionally hides direct scientific part/palette controls in Presentation Format. They are not exercised or claimed qualified; visible next-insertion Library palette, native artwork, switching and native files are qualified.')
    check(name,'Public Presentation capability limit is observed without hidden mutations',not direct_part and not direct_palette,row['presentationCapabilities'])
    present_state=await selection_history(frame)
    workspace_before=await frame.evaluate('async()=>await FigureStudio.app.serializeWorkspace()')
    keys=('activeType','activeObjectId','activeSelectionChildCount','selectedCount','selectedIds','mismatch')
    for kind,expected in [('figure',figure_state),('presentation',present_state)]:
        await switch(frame,kind)
        actual=await selection_history(frame)
        check(name,kind+' selection survives switching',all(actual['selection'].get(k)==expected['selection'].get(k) for k in keys),dict(before=expected['selection'],after=actual['selection']))
        check(name,kind+' Undo/Redo history survives switching',actual['history']==expected['history'])
    workspace_after=await frame.evaluate('async()=>await FigureStudio.app.serializeWorkspace()')
    write(name+'/workspace-switching.json',dict(before=workspace_before,after=workspace_after))
    check(name,'Complete authored workspace survives switching',workspace_authored(workspace_before)==workspace_authored(workspace_after))
    intent='Show the native cell inserted through the visible Vivid Library palette on a Presentation slide, with both Figure and Presentation available after successful selection and history switching at '+name+'. Direct selected-part controls are unavailable in this pinned public version.'
    shot=dict(case=name,file=name+'/02-presentation-switching.png',intent=intent)
    R['captures'].append(shot);write('capture-intents.json',R['captures'])
    await page.screenshot(path=str(OUT/shot['file']),animations='disabled');shot['sha256']=sha((OUT/shot['file']).read_bytes())
    deck_path=OUT/name/'asset-repaint.fsdeck'
    row['savedDeck']=await save_native(frame,page,name,deck_path)
    deck=await frame.evaluate('FigureStudio.app.serializeCurrentDocumentForQa({markSaved:false})')
    deck_native=await frame.evaluate(native.STATE,[owner])
    project_path=OUT/name/'asset-repaint.fsproject'
    row['savedWorkspace']=await save_native(frame,page,name,project_path,workspace=True)
    workspace=await frame.evaluate('async()=>await FigureStudio.app.serializeWorkspace()')
    for kind,path in [('presentation',deck_path),('workspace',project_path)]:
        await context.close()
        context,page,frame=await launch(browser,base,size,theme)
        await enter_current_document_async(frame,kind='figure',preset='double-column',name='Cold '+kind+' Open')
        await open_native(frame,page,path)
        if kind=='presentation':
            opened=await frame.evaluate('FigureStudio.app.serializeCurrentDocumentForQa({markSaved:false})')
            write(name+'/deck-roundtrip.json',dict(saved=deck,opened=opened))
            check(name,'Cold deck Open preserves every authored field and ID',native.authored_document(deck)==native.authored_document(opened))
            opened_native=await frame.evaluate(native.STATE,[owner])
            comparison=native.native_reconstruction_difference(deck_native,opened_native)
            check(name,'Cold deck Open preserves native vectors and colors',comparison['passed'],comparison)
        else:
            opened=await frame.evaluate('async()=>await FigureStudio.app.serializeWorkspace()')
            write(name+'/workspace-roundtrip.json',dict(saved=workspace,opened=opened))
            await compare_cold_workspace(frame,name,workspace,opened,[owner])
            for document_kind,ids in [('figure',figure_ids),('presentation',[owner])]:
                await switch(frame,document_kind)
                state=await frame.evaluate(native.STATE,ids)
                check(name,'Cold complete-project retains '+document_kind+' native drawings',all(item is not None for item in state))
        await switch(frame,'presentation')
        record,_=await witness(frame,name,'cold-'+kind,'paint',owner)
        record['expectedPaint']=expected_paint;record['matchingPaintPixels']=painted_color_pixels(record,expected_paint)
        check(name,'Cold '+kind+' visibly paints the selected native cytoplasm palette',record['matchingPaintPixels']>16,record['matchingPaintPixels'])
    return context,page,frame

async def run_case(browser,base,size,theme):
    name=f'{size[0]}x{size[1]}-{theme}';(OUT/name).mkdir(exist_ok=False)
    row=dict(name=name,viewport=list(size),theme=theme,operations=[],status='running');R['cases'].append(row)
    context=page=frame=None
    try:
        context,page,frame=await launch(browser,base,size,theme)
        await enter_current_document_async(frame,kind='figure',preset='double-column',name='Asset repaint regression')
        await frame.locator('[data-figure-layout-choice="advanced"]').click()
        if await frame.locator('#figureStyleToggle').get_attribute('aria-pressed')!='true':await frame.locator('#figureStyleToggle').click()
        await frame.locator('[data-inspector-tab="properties"]').click();await library(frame)
        first=await insert(frame,'core.cell.generic','Generic Eukaryotic Cell')
        meta=await frame.evaluate('id=>FigureStudio.app.getObjectByIdForQa(id).scientificAssetMeta',first)
        region=next(r['id'] for r in meta['editableColorRegions'] if r.get('paint','fill')=='fill' and r['id']!='outline')
        async def recolor():
            await frame.locator('#scientificAssetColorList [data-asset-color-region="'+region+'"]').evaluate('(e,c)=>{e.value=c;e.dispatchEvent(new Event("change",{bubbles:true}));}','#277da8')
        await edit(frame,page,row,'first-part',first,recolor,('([id,r])=>FigureStudio.app.getObjectByIdForQa(id).scientificAssetMeta.colorOverrides?.[r]?.toLowerCase()==="#277da8"',[first,region]))
        intent='Show the first Generic Eukaryotic Cell part-color edit visibly painted in the actual Advanced editor at '+name+', with the right inspector and complete drawing visible after real Undo/Redo.'
        shot=dict(case=name,file=name+'/01-first-part-redone.png',intent=intent);R['captures'].append(shot);write('capture-intents.json',R['captures'])
        await page.screenshot(path=str(OUT/shot['file']),animations='disabled');shot['sha256']=sha((OUT/shot['file']).read_bytes())
        second=await insert(frame,'core.cell.generic','Generic Eukaryotic Cell')
        async def palette():await frame.locator('#scientificAssetColorList [data-asset-palette]').select_option('vivid')
        await edit(frame,page,row,'first-palette',second,palette,('id=>FigureStudio.app.getObjectByIdForQa(id).scientificAssetMeta.paletteId==="vivid"',second))
        tcell=await insert(frame,'core.cell.t_cell','T Cell')
        choices=await frame.locator('#scientificAssetStyleList [data-scientific-asset-style-id]').evaluate_all('xs=>xs.map(x=>({id:x.dataset.scientificAssetStyleId,text:x.textContent.trim(),disabled:x.disabled}))')
        row['styleChoices']=choices
        thin=next(x for x in choices if x['id']=='core.cell.t_cell_manuscript')
        check(name,'Public T Cell offers an enabled Thin choice',not thin['disabled'],choices)
        async def style():await frame.locator('#scientificAssetStyleList [data-scientific-asset-style-id="core.cell.t_cell_manuscript"]').click()
        await edit(frame,page,row,'soft-to-thin',tcell,style,('id=>FigureStudio.app.getObjectByIdForQa(id).scientificAssetMeta.assetId==="core.cell.t_cell_manuscript"',tcell))
        async def replace():
            await frame.locator('#replaceScientificAssetBtn').click()
            await frame.wait_for_function('FigureStudio.app.getScientificAssetReplacementStateForQa().active===true')
            # Beta.6 initially scopes replacement to the current asset's
            # category. Choose All explicitly before an organelle search.
            await frame.locator('#assetCategorySelect').select_option('all')
            await frame.locator('#assetSubcategorySelect').select_option('all')
            await frame.locator('#assetSearchInput').fill('mitochondria')
            await frame.locator('#assetGrid [data-asset-id="core.mitochondrion.basic"]').click()
        await edit(frame,page,row,'replace-selected',tcell,replace,('id=>FigureStudio.app.getObjectByIdForQa(id).scientificAssetMeta.assetId==="core.mitochondrion.basic"',tcell))
        ids=[first,second,tcell]
        # Only after all first-edit witnesses: arrange the genuine inserted
        # drawings as a readable persistence fixture. No edit rendering is forced.
        await frame.evaluate("""ids=>{const a=FigureStudio.app.serializeCurrentDocumentForQa({markSaved:false}).project.artboard;ids.forEach((id,i)=>{const o=FigureStudio.app.getObjectByIdForQa(id);o.scaleToWidth(a.widthIn*96*.22);o.set({originX:'center',originY:'center',left:a.widthIn*96*(.2+i*.3),top:a.heightIn*96*.5});o.setCoords();});}""",ids)
        # A real View command commits the separately identified arranged fixture.
        await command(frame,'view','toggle-grid')
        await frame.evaluate('FigureStudio.app.commitHistoryForQa("Arrange persistence fixture")')
        before_native=await frame.evaluate(native.STATE,ids)
        await frame.locator('#fileMenuTrigger').click();page.once('dialog',lambda d:d.accept('asset-repaint.fsfigure'))
        async with page.expect_download() as pending:await frame.locator('[data-menu="file"] [data-command="save-project"]').click()
        download=await pending.value;path=OUT/name/'asset-repaint.fsfigure';await download.save_as(path)
        check(name,'Actual Save downloads the native Figure file',download.suggested_filename.endswith('.fsfigure'),download.suggested_filename)
        saved=await frame.evaluate('FigureStudio.app.serializeCurrentDocumentForQa({markSaved:false})')
        row['savedFile']=dict(file=name+'/asset-repaint.fsfigure',sha256=sha(path.read_bytes()),bytes=path.stat().st_size)
        await context.close();context=None
        context,page,frame=await launch(browser,base,size,theme)
        await enter_current_document_async(frame,kind='figure',preset='double-column',name='Cold Figure Open')
        await frame.locator('#fileMenuTrigger').click()
        async with page.expect_file_chooser() as pending:await frame.locator('[data-menu="file"] [data-command="open-project"]').click()
        await (await pending.value).set_files(path)
        await frame.wait_for_function("document.querySelector('#documentFileOperationStatus')?.dataset.state==='success'")
        opened=await frame.evaluate('FigureStudio.app.serializeCurrentDocumentForQa({markSaved:false})')
        write(name+'/roundtrip.json',dict(saved=saved,opened=opened))
        check(name,'Cold Open preserves every authored field and ID',native.authored_document(saved)==native.authored_document(opened))
        reopened_native=await frame.evaluate(native.STATE,ids)
        comparison=native.native_reconstruction_difference(before_native,reopened_native)
        check(name,'Cold Open preserves all native drawings and part colors',comparison['passed'],comparison)
        cold,_=await witness(frame,name,'cold-open','paint',first)
        check(name,'Cold Open visibly paints the edited blue part',cold['bluePixels']>16,cold['bluePixels'])
        row['coldPaint']=cold
        await frame.locator('[data-figure-layout-choice="simple"]').click()
        await frame.wait_for_function('document.getElementById("figureStudioRoot").dataset.figureLayout==="simple"')
        smoke,_=await witness(frame,name,'simple','paint',first)
        check(name,'Simple layout smoke visibly retains the edited blue part',smoke['bluePixels']>16,smoke['bluePixels'])
        row['simpleSmoke']=smoke
        context,page,frame=await presentation_and_workspace(browser,base,size,theme,context,page,frame,row,ids)
        row['status']='passed';print(name+' passed',flush=True)
    except BaseException as e:
        row['status']='failed';row['failure']=str(e);row['traceback']=traceback.format_exc()
        if page and not page.is_closed():
            with contextlib.suppress(Exception):await page.screenshot(path=str(OUT/name/'failure.png'))
        raise
    finally:
        if context:await context.close()
        row['contextsClosed']=True;write('report.json',R)

async def run():
    global ARGS, OUT, enter_current_document_async, show_library_async
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--candidate-root',required=True,type=Path);parser.add_argument('--expected-app-sha256',required=True);parser.add_argument('--output-dir',type=Path)
    parser.add_argument('--case',action='append',choices=[f'{w}x{h}-{theme}' for w,h in [(1280,800),(1440,1000),(1920,1080)] for theme in ['light','dark']],help='Run selected diagnostic cases; omission runs all six desktop/theme cases')
    parser.add_argument('--action-paint',action='store_true',help='Action-alone mutation/paint timing and negative-control cases; no historical persistence fixture.')
    parser.add_argument('--action-paint-family',choices=['ordinary','structure','library','pdf'],default='ordinary')
    parser.add_argument('--pdf-fixture',type=Path,help='Unchanged genuine PDF for the imported-object action case.')
    ARGS=parser.parse_args();candidate=ARGS.candidate_root.resolve()
    entry_path=candidate/'scripts/figure_studio_entry_qa.py'
    entry_spec=importlib.util.spec_from_file_location('repaint_candidate_entry',entry_path)
    entry=importlib.util.module_from_spec(entry_spec);entry_spec.loader.exec_module(entry)
    enter_current_document_async=entry.enter_current_document_async
    show_library_async=entry.show_library_async
    if ARGS.output_dir:
        OUT=ARGS.output_dir.resolve()
    OUT.relative_to((ROOT/'qa_artifacts').resolve())
    OUT.mkdir(parents=True,exist_ok=False)
    check('preflight','Selected candidate is a directory',candidate.is_dir())
    check('preflight','Candidate app bytes match supplied review identity',sha((candidate/'app/app.js').read_bytes())==ARGS.expected_app_sha256)
    R['target']=dict(root=str(candidate),expectedAppSha256=ARGS.expected_app_sha256,version='public beta.6 hotfix local candidate')
    R['selectedCases']=ARGS.case or 'all-six-desktop-theme-cases'
    if ARGS.action_paint:
        R['target']['version']='Explicitly bound current Figure candidate; natural action-paint cases'
        R['selectedCases']=ARGS.case or ['1280x800-light']
        R['comparisonPolicyActionPaint']='Read-only natural lower RGBA paint; requested model plus analytic solid interiors, cleared old areas and unchanged neighbors. First correct paint<=250ms with80ms stability. No render or unrelated action may rescue a pass. Existing Library history policies are unchanged.'
    R['comparisonPolicy']=dict(immediatePaint='Drawing crop must change >16 pixels immediately after committed metadata, before any unrelated user action.',grid='Real Show Grid after edit Undo/Redo adds exactly zero drawing-crop pixel changes.',historyNative='Existing native.geometry preserves scientific asset owner IDs and all metadata, paths, paints and ordered hierarchy, while omitting tree-node ID fields that imported reconstruction may regenerate. Derived scene bounds/matrices permit <=0.01px difference.',partAndPaletteHistory='Exact crop pixels plus historyNative comparator.',replacementHistory='Mandatory historyNative comparison passed; mean channel difference<=0.25; every changed pixel must lie within1pixel of a color boundary in BOTH images, with zero changed crop-edge or uniform3x3-interior pixels on either side. Maximum channel difference remains diagnostic. This applies only to reconstructed style/replacement history; raw raster differences are retained.',coldOpen='Full authored payload compares every authored ID at six-decimal precision; existing authored_document omits clocks, derived manifest bounds/thumbnails and global artifact-count telemetry. Cold native comparison retains tree IDs, with only derived bounds/matrices tolerance <=0.01px.',workspaceViews='Live switching preserves all views exactly. Cold workspace Open preserves all inactive views and every authored field/ID; only active fitted zoom/pan may adapt to fresh rails, recorded before an actual visible Fit to Screen must reproduce it exactly without native/content changes.')
    sources=OUT/'controller-sources';sources.mkdir(exist_ok=False)
    R['controllerSources']={}
    for rel in ['scripts/check-rna-artwork-browser.py','scripts/figure_studio_entry_qa.py',
                'scripts/check-figure-public-repaint-browser.py','tests/test_public_repaint_history_raster.py']:
        raw=(entry_path if rel=='scripts/figure_studio_entry_qa.py' else ROOT/rel).read_bytes();(sources/Path(rel).name).write_bytes(raw);R['controllerSources'][rel]=sha(raw)
    if ARGS.action_paint:
        for rel in ['scripts/figure_action_paint_qa.py','scripts/action-paint-observer.js']:
            raw=(ROOT/rel).read_bytes();(sources/Path(rel).name).write_bytes(raw);R['controllerSources'][rel]=sha(raw)
    R['inventoryBefore']=inventory(candidate);R['status']='running';write('report.json',R)
    server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(candidate)));thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start();browser=None
    try:
        async with async_playwright() as pw:
            browser=await pw.chromium.launch(headless=True)
            base=f'http://127.0.0.1:{server.server_port}'
            if ARGS.action_paint:
                import figure_action_paint_qa as action_paint
                if (candidate/'web/index.html').is_file():base+='/web'
                for case in ARGS.case or ['1280x800-light']:
                    await action_paint.run(sys.modules[__name__],browser,base,case)
            for size in [(1280,800),(1440,1000),(1920,1080)]:
                for theme in ['light','dark']:
                    if ARGS.action_paint:continue
                    if not ARGS.case or f'{size[0]}x{size[1]}-{theme}' in ARGS.case:
                        await run_case(browser,f'http://127.0.0.1:{server.server_port}',size,theme)
            await browser.close();R['closure']['browserDisconnected']=not browser.is_connected();browser=None
        R['inventoryAfter']=inventory(candidate)
        check('closure','Candidate remains byte-identical throughout qualification',R['inventoryBefore']==R['inventoryAfter'])
        check('closure','No browser page errors',not R['pageErrors'],R['pageErrors']);check('closure','No browser console errors',not R['consoleErrors'],R['consoleErrors'])
        R['status']='passed'
    except BaseException as e:
        R['status']='failed';R['failure']=str(e);R['traceback']=traceback.format_exc();raise
    finally:
        if browser:
            with contextlib.suppress(Exception):await browser.close()
            R['closure']['browserDisconnected']=not browser.is_connected()
        server.shutdown();server.server_close();thread.join(5);R['closure']['serverStopped']=not thread.is_alive()
        R['scriptSha256']=sha(Path(__file__).read_bytes());write('report.json',R)
        print(json.dumps(dict(status=R['status'],checks=len(R['checks']),cases=len(R['cases']),output=str(OUT))),flush=True)

if __name__=='__main__':asyncio.run(run())
