#!/usr/bin/env python3
"""Focused Style/preview browser checks using maintained Library and PDF owners.

Run one explicit journey through the shared/frozen/owned wrappers. Fixtures are
real saved figures. Layout covers three desktop widths, both themes and fresh /
saved preferences; the other journeys each use one 1440x1000 light desktop.
QA selection is setup only. Style/history/File actions use real UI commands;
preview color input uses the existing synthetic picker boundary.
"""
from __future__ import annotations
import argparse
import asyncio
import functools
import hashlib
import http.server
import importlib.util
import json
import re
from pathlib import Path
import sys
import threading
from urllib.parse import urlparse
from playwright.async_api import async_playwright

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
def load(name,relative):
    spec=importlib.util.spec_from_file_location(name,ROOT/relative)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module
d=load('style_discovery','scripts/check-library-discovery-browser.py')
a=load('style_paint','scripts/check-assets-templates-browser.py')
sel=load('style_selection','scripts/check-direct-selection-label-interactions-browser.py')
sel.asset_library=d.library

def authored(value):
    return sel.real_asset_artwork(d.library.native.authored_document(value))

class StyleCase(d.DiscoveryCase):
    paint_facade=a.Case.paint_facade
    paint_bounds=a.Case.paint_bounds
    bounded_solid_probes=staticmethod(a.Case.bounded_solid_probes)

    async def launch(self,routes=None):
        await super().launch(routes)
        # Resource timing records the URLs actually requested by the document.
        # Re-fetch those exact URLs only to bind returned bytes to the candidate.
        resources=await self.frame.evaluate("()=>performance.getEntriesByType('resource').map(entry=>entry.name)")
        rows=[]
        for name,reference in ARGS.ui_references.items():
            actual=next((url for url in resources if urlparse(url).path.endswith('/'+name) and urlparse(url).query==urlparse(reference).query),None)
            self.check('Document requests current cache key for '+name,bool(actual),dict(expected=reference,resources=resources if not actual else []))
            response=await self.page.request.get(actual)
            digest=hashlib.sha256(await response.body()).hexdigest()
            expected=self.report['runtimeFiles']['app/'+name]
            rows.append(dict(name=name,url=actual,status=response.status,sha256=digest))
            self.check('Requested '+name+' bytes match candidate',response.status==200 and digest==expected,rows[-1])
        self.case.setdefault('loadedUiResources',[]).append(rows)

async def open_fixture(case,path):
    await case.frame.locator('#fileMenuTrigger').click()
    async with case.page.expect_file_chooser() as chooser:
        await case.frame.locator('[data-menu="file"] [data-command="open-project"]').click()
    await(await chooser.value).set_files(path)
    await case.frame.wait_for_function("document.querySelector('#documentFileOperationStatus')?.dataset.state==='success'&&!FigureStudio.app.getBrowserSessionState().busy")

async def show_style(case):
    if await case.frame.locator('#figureStyleToggle').get_attribute('aria-pressed')!='true':
        await case.frame.locator('#figureStyleToggle').click()
    await case.frame.locator('[data-inspector-tab="appearance"]').click()
    if not await case.frame.locator('#figureInspectorPanel').evaluate('e=>e.classList.contains("is-floating")'):
        await case.frame.locator('[data-rail-action="float"][data-rail="right"]').click()

async def prepare_figure_file_panels(case):
    # Native document files retain artwork/view intent, not a new browser's UI
    # preferences. Match the physical viewport before Save and before cold Open.
    for control in ['figureLibraryToggle','figureStyleToggle']:
        button=case.frame.locator('#'+control)
        if await button.get_attribute('aria-pressed')=='true':await button.click()
    await case.frame.wait_for_function('document.getElementById("figureStudioRoot").dataset.qaLayoutStable==="true"')
    return await case.frame.locator('#viewport').evaluate('e=>e.getBoundingClientRect().toJSON()')

async def preview_journey(case,pw):
    browser=case.browser;report=case.report
    before=await case.document(); history=await case.history()
    catalog=await case.frame.evaluate('FigureStudio.app.getScientificAssetCatalogRecordsForQa()')
    await d.library.show_library_async(case.frame,tab='tools')
    await case.frame.locator('#figureLibraryTab-assets').click()
    await case.frame.locator('#assetCategorySelect').select_option('all');await case.frame.locator('#assetSubcategorySelect').select_option('all')
    await case.frame.locator('[data-asset-discovery="all"]').click()
    before=await case.document();history=await case.history();case.write('before-preview-document.json',before);case.write('before-preview-history.json',history)
    dialog,_=await case.preview(d.BASE)
    colors=case.frame.locator('#assetPreviewParts input[data-asset-color-region]')
    case.check('Preview exposes actual part-color inputs',await colors.count()>0)
    region=await colors.first.get_attribute('data-asset-color-region')
    async def draft_color(color):
     field=case.frame.locator(f'#assetPreviewParts [data-asset-color-region="{region}"]')
     await field.focus()
     await field.evaluate('(e,v)=>{e.value=v;e.dispatchEvent(new Event("input",{bubbles:true}))}',color)
     await case.frame.wait_for_function('([r,c])=>{const s=FigureStudio.app.getScientificAssetPreviewStateForQa();return !s.loading&&!s.busy&&s.displayedDraft?.customColorOverrides?.[r]?.toLowerCase()===c}',arg=[region,color.lower()])
    await draft_color('#E23422')
    await case.capture('preview-draft.png','Candidate: the mitochondrial preview has live editable part colors, shows the chosen red draft, and keeps scientific details optional; the figure is unchanged.')
    draft_document=await case.document();draft_history=await case.history();case.write('draft-document.json',draft_document);case.write('draft-history.json',draft_history)
    case.check('Live preview preserves complete authored figure and history',d.library.native.authored_document(draft_document)==d.library.native.authored_document(before) and draft_history==history)
    case.check('Draft does not mutate catalog records',await case.frame.evaluate('FigureStudio.app.getScientificAssetCatalogRecordsForQa()')==catalog)
    await case.page.keyboard.press('Escape');await dialog.wait_for(state='hidden')
    case.check('Cancel leaves complete figure/history/catalog unchanged',d.library.native.authored_document(await case.document())==d.library.native.authored_document(before) and await case.history()==history and await case.frame.evaluate('FigureStudio.app.getScientificAssetCatalogRecordsForQa()')==catalog)
    dialog,_=await case.preview(d.BASE)
    await draft_color('#E23422')
    await case.frame.locator('#assetPreviewInsertBtn').click();await dialog.wait_for(state='hidden')
    await case.frame.wait_for_function('id=>FigureStudio.app.getObjectByIdForQa(FigureStudio.app.getSelectionStateForQa().activeObjectId)?.scientificAssetMeta?.assetId===id',arg=d.BASE)
    await case.capture('draft-inserted.png','Candidate: Insert commits the previewed red drawing as an editable native asset with the useful Appearance controls; the catalog remains unchanged.')
    object_id=await case.frame.evaluate('FigureStudio.app.getSelectionStateForQa().activeObjectId')
    inserted=(await case.frame.evaluate(d.library.STATE,[object_id]))[0]
    case.write('inserted-native.json',inserted)
    bound=[leaf for leaf in d.library.native.leaves(inserted['tree']) if region in leaf.get('regionPaints',{})]
    case.check('Insert native part paints equal the displayed draft',bool(bound) and all(str(leaf[channel]).lower()=='#e23422' for leaf in bound for channel in leaf['regionPaints'][region]))
    after_insert=await case.history();case.check('Insert creates exactly one Undo entry',after_insert['undoDepth']==history['undoDepth']+1)
    await case.undo();await case.frame.wait_for_function('id=>!FigureStudio.app.getObjectByIdForQa(id)',arg=object_id)
    await case.undo(True);await case.frame.wait_for_function('id=>!!FigureStudio.app.getObjectByIdForQa(id)',arg=object_id)
    case.check('Insert Undo/Redo restores complete native asset',d.library.native.native_reconstruction_difference([inserted],await case.frame.evaluate(d.library.STATE,[object_id]))['passed'])
    await case.select(object_id)
    if await case.frame.locator('#figureStyleToggle').get_attribute('aria-pressed')!='true':await case.frame.locator('#figureStyleToggle').click()
    await case.frame.locator('#figureSimpleStyleControls [data-asset-selection-action="change-drawing"]').click()
    await dialog.wait_for(state='visible')
    await case.frame.wait_for_function('()=>{const s=FigureStudio.app.getScientificAssetPreviewStateForQa(),r=FigureStudio.app.getScientificAssetReplacementStateForQa();return !s.loading&&!s.busy&&!r.checking}')
    previous=await case.document();before_apply=await case.history()
    await draft_color('#125B8A')
    draft_document=await case.document();case.write('before-apply-document.json',previous);case.write('apply-draft-document.json',draft_document)
    case.check('Existing drawing stays unchanged while preview color changes',d.library.native.authored_document(draft_document)==d.library.native.authored_document(previous) and await case.history()==before_apply)
    case.check('Existing-copy preview provides explicit Apply colors',await case.frame.locator('#assetPreviewReplaceSelectedBtn').inner_text()=='Apply colors' and await case.frame.locator('#assetPreviewReplaceSelectedBtn').is_enabled())
    await case.capture('preview-apply-draft.png','Candidate: the selected existing drawing is previewed with a blue color draft and an explicit Apply colors action; the live figure still retains its red drawing until Apply.')
    await a.paint.frames(case.frame)
    lower=await case.frame.evaluate(a.paint.LOWER,object_id)
    probes=case.bounded_solid_probes(lower,'#E23422','#125B8A',await case.paint_bounds(object_id))
    async def apply_action():await case.frame.locator('#assetPreviewReplaceSelectedBtn').click()
    predicate=f"return app.getObjectByIdForQa(rows[0].id).scientificAssetMeta.colorOverrides?.[{json.dumps(region)}]?.toLowerCase()==='#125b8a';"
    await a.paint.observe(case.paint_facade(),case.frame,case.page,case.case,case.out,'preview-color-apply',[object_id],predicate,
      {'type':'click','selector':'#assetPreviewReplaceSelectedBtn'},apply_action,rectangles=False,probes=probes,unchangedIds=[])
    await dialog.wait_for(state='hidden')
    await case.capture('preview-applied.png','Candidate: Apply updates only the selected native drawing to the previewed blue, preserving its geometry and producing one history step.')
    applied=(await case.frame.evaluate(d.library.STATE,[object_id]))[0];case.write('applied-native.json',applied)
    bound=[leaf for leaf in d.library.native.leaves(applied['tree']) if region in leaf.get('regionPaints',{})]
    case.check('Apply native part paints equal the displayed draft',bool(bound) and all(str(leaf[channel]).lower()=='#125b8a' for leaf in bound for channel in leaf['regionPaints'][region]))
    case.check('Apply creates one Undo entry',(await case.history())['undoDepth']==before_apply['undoDepth']+1)
    await case.undo();await case.frame.wait_for_function('([id,r])=>FigureStudio.app.getObjectByIdForQa(id)?.scientificAssetMeta?.colorOverrides?.[r]?.toLowerCase()==="#e23422"',arg=[object_id,region]);case.check('Apply Undo restores exact prior native artwork',d.library.native.native_reconstruction_difference([inserted],await case.frame.evaluate(d.library.STATE,[object_id]))['passed'])
    await case.undo(True);await case.frame.wait_for_function('([id,r])=>FigureStudio.app.getObjectByIdForQa(id)?.scientificAssetMeta?.colorOverrides?.[r]?.toLowerCase()==="#125b8a"',arg=[object_id,region]);case.check('Apply Redo restores exact edited native artwork',d.library.native.native_reconstruction_difference([applied],await case.frame.evaluate(d.library.STATE,[object_id]))['passed'])
    case.check('Insert and Apply keep catalog records exact',await case.frame.evaluate('FigureStudio.app.getScientificAssetCatalogRecordsForQa()')==catalog)
    path,warm=await case.save('style-preview-first.fsfigure')
    case.case['actualSave']={'path':str(path),'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
    case.write('saved-warm.json',warm)
    await case.context.close();case.context=None;await browser.close()
    browser=await pw.chromium.launch();case.browser=browser
    await case.launch()
    await d.library.enter_current_document_async(case.frame,kind='figure',preset='double-column',name='Cold edited preview')
    await case.frame.locator('#fileMenuTrigger').click()
    async with case.page.expect_file_chooser() as chooser:await case.frame.locator('[data-menu="file"] [data-command="open-project"]').click()
    await(await chooser.value).set_files(path)
    await case.frame.wait_for_function("document.querySelector('#documentFileOperationStatus')?.dataset.state==='success'&&!FigureStudio.app.getBrowserSessionState().busy")
    await case.capture('edited-cold-open.png','Candidate: a genuinely new browser naturally opens the actual edited-color Save before native inspection or view changes; the blue drawing remains native.')
    cold=await case.document();case.write('cold-document.json',cold)
    case.check('Actual Save/fresh-process Open preserves authored document',d.library.native.authored_document(warm)==d.library.native.authored_document(cold))
    case.check('Fresh-process Open preserves native edited vector',d.library.native.native_reconstruction_difference([applied],await case.frame.evaluate(d.library.STATE,[object_id]))['passed'])
    case.check('No application page or console errors',not report['pageErrors'] and not report['consoleErrors'],{'page':report['pageErrors'],'console':report['consoleErrors']})
    case.case['syntheticControlBoundary']='Color-picker values use the maintained synthetic input boundary; Insert/Apply/Cancel/history/File actions use actual UI commands.'


async def inspector_editing_controls(case, text_id, line_id):
    """Use the regrouped owners, including actual transform and saved-color edits."""
    tabs=await case.frame.locator('[data-inspector-tab]').evaluate_all('es=>es.map(e=>({view:e.dataset.inspectorTab,label:e.textContent.trim()}))')
    case.check('Inspector has exactly Appearance, Properties and Layers',tabs==[{'view':'appearance','label':'Appearance'},{'view':'properties','label':'Properties'},{'view':'layers','label':'Layers'}],tabs)
    old=await case.history()
    field=case.frame.locator('#figureSimpleStyleControls input[data-context-property="opacity"]')
    await field.fill('0.8');await field.press('Tab')
    await case.frame.wait_for_function('id=>Math.abs(FigureStudio.app.getObjectByIdForQa(id).opacity-.8)<1e-8',arg=text_id)
    case.check('Appearance opacity uses its existing native history owner',(await case.history())['undoDepth']==old['undoDepth']+1)
    await case.frame.locator('[data-inspector-tab="properties"]').click()
    field=case.frame.locator('#appearanceStructureInspector input[data-context-property="x"][data-numeric-transform-field]')
    x=float(await field.input_value());geometry=await case.frame.evaluate('FigureStudio.app.getSelectionContextStateForQa().geometry')
    old_left=await case.frame.evaluate('id=>FigureStudio.app.getObjectByIdForQa(id).left',text_id)
    expected_left=old_left+(x+0.1-geometry['x'])*96
    case.write('inspector-transform-input.json',dict(displayedX=x,rawGeometry=geometry,enteredX=x+0.1,oldLeft=old_left,expectedLeft=expected_left))
    native_before=await case.frame.evaluate(a.MIXED_SCENE_STATE,[text_id])
    old=await case.history();await field.fill(str(x+0.1));await field.press('Tab')
    await case.frame.wait_for_function('([id,x])=>Math.abs(FigureStudio.app.getObjectByIdForQa(id).left-x)<.001',arg=[text_id,expected_left])
    native_after=await case.frame.evaluate(a.MIXED_SCENE_STATE,[text_id])
    case.write('inspector-transform-before-native.json',native_before);case.write('inspector-transform-after-native.json',native_after)
    case.check('Properties position applies one real native transform',(await case.history())['undoDepth']==old['undoDepth']+1)
    await case.undo();case.check('Properties transform Undo restores the complete prior native label',d.library.native.native_reconstruction_difference(native_before,await case.frame.evaluate(a.MIXED_SCENE_STATE,[text_id]))['passed'])
    await case.undo(True);case.check('Properties transform Redo restores the complete moved native label',d.library.native.native_reconstruction_difference(native_after,await case.frame.evaluate(a.MIXED_SCENE_STATE,[text_id]))['passed'])
    case.check('Properties has geometry and excludes Appearance fields',await field.is_visible() and not await case.frame.locator('#figureSimpleStylePanel').is_visible())
    await case.frame.locator('[data-inspector-tab="appearance"]').click();await case.frame.locator('[data-inspector-tab="properties"]').click()
    geometry_visibility=await case.frame.evaluate('''()=>{const body=document.querySelector('#inspectorContent').getBoundingClientRect();return ['x','y','width','height','rotation'].map(property=>{const e=document.querySelector('#appearanceStructureInspector input[data-context-property="'+property+'"][data-numeric-transform-field]'),r=e.getBoundingClientRect();return {property,rect:r.toJSON(),inside:r.width>0&&r.height>0&&r.top>=body.top-1&&r.bottom<=body.bottom+1&&r.left>=body.left-1&&r.right<=body.right+1};});}''')
    case.write('properties-initial-geometry-visibility.json',geometry_visibility)
    case.check('Properties initially shows complete position/dimensions/rotation inputs',all(row['inside'] for row in geometry_visibility),geometry_visibility)
    await case.capture('inspector-properties.png','Candidate: Properties shows actual position/dimensions/rotation controls for the editable label; appearance fields belong to their separate view, while the populated scientific figure remains visible.')
    await case.frame.locator('[data-inspector-tab="appearance"]').click()
    await case.frame.locator('#savedColorsDisclosure > summary').click()
    library_before=await case.frame.evaluate('FigureStudio.app.getSwatchLibraryStateForQa()')
    await case.frame.locator('#swatchNameInput').fill('Assay blue')
    await case.frame.locator('#swatchColorInput').evaluate('e=>{e.value="#125b8a";e.dispatchEvent(new Event("change",{bubbles:true}));}')
    await case.frame.locator('#swatchAddForm button[type="submit"]').click()
    await case.frame.wait_for_function('FigureStudio.app.getSwatchLibraryStateForQa().swatches.some(s=>s.name==="Assay blue")')
    library=await case.frame.evaluate('FigureStudio.app.getSwatchLibraryStateForQa()')
    swatch=next(s for s in library['swatches'] if s['name']=='Assay blue')
    case.check('Saved colors remain inside Appearance and retain the existing library',library['swatchCount']==library_before['swatchCount']+1 and await case.frame.locator('[data-inspector-tab="appearance"]').get_attribute('aria-current')=='page')
    await case.frame.locator('#swatchApplyTarget').select_option('text')
    await case.frame.locator(f'#swatchGrid [data-swatch-apply="{swatch["id"]}"]').click()
    await case.frame.wait_for_function('id=>FigureStudio.app.getObjectByIdForQa(id).fill.toLowerCase()==="#125b8a"',arg=text_id)
    case.case['savedColor']=swatch;case.write('saved-colors-warm.json',await case.frame.evaluate('FigureStudio.app.getSwatchLibraryStateForQa()'))
    await case.capture('inspector-saved-colors.png','Candidate: Saved colors is a disclosure inside Appearance; adding and applying Assay blue uses the retained document color library and leaves the scientific drawings intact.')
    await case.frame.locator('#savedColorsDisclosure > summary').click()
    roots=(await case.document())['project']['fabric']['objects']
    effect_id=next((o['figureId'] for o in roots if not o.get('scientificAssetMeta') and (o.get('figureType') in ['rect','roundedRect'] or o.get('type','').lower()=='rect')),None)
    case.check('Retained fixture includes an ordinary vector eligible for supported effects',bool(effect_id))
    case.case['effectObjectId']=effect_id
    await case.select(effect_id)
    await case.frame.locator('#appearanceStructureInspector [data-appearance-section="base-appearance"] > summary').click()
    shadow=case.frame.locator('#appearanceStructureInspector [data-appearance-effect-add="soft-shadow"]')
    case.check('Supported effects are available in Appearance',await shadow.is_enabled())
    before=await case.frame.evaluate(a.MIXED_SCENE_STATE,[effect_id]);old=await case.history();await shadow.click()
    await case.frame.wait_for_function('id=>FigureStudio.app.getObjectByIdForQa(id).figureStudioAppearanceStack?.items?.some(i=>i.type==="effect"&&i.effectKind==="soft-shadow")',arg=effect_id)
    after=await case.frame.evaluate(a.MIXED_SCENE_STATE,[effect_id]);case.write('appearance-effect-before-native.json',before);case.write('appearance-effect-after-native.json',after)
    case.check('Supported effect uses one native history entry',(await case.history())['undoDepth']==old['undoDepth']+1)
    await case.undo();case.check('Effect Undo restores complete native vector',d.library.native.native_reconstruction_difference(before,await case.frame.evaluate(a.MIXED_SCENE_STATE,[effect_id]))['passed'])
    await case.undo(True);case.check('Effect Redo restores complete native vector',d.library.native.native_reconstruction_difference(after,await case.frame.evaluate(a.MIXED_SCENE_STATE,[effect_id]))['passed'])
    await case.capture('inspector-supported-effects.png','Candidate: the retained effect controls in Appearance add a supported editable shadow to the genuine fixture rectangle, with the populated scientific figure and neighbors preserved.')
    await case.select(text_id)
    await case.frame.locator('#inspectorContent').evaluate('e=>e.scrollTop=0')

async def mixed_journey(case,pw):
    browser=case.browser;report=case.report
    fixture=ARGS.fixture
    await case.frame.locator('#fileMenuTrigger').click()
    async with case.page.expect_file_chooser() as chooser:await case.frame.locator('[data-menu="file"] [data-command="open-project"]').click()
    await(await chooser.value).set_files(fixture)
    await case.frame.wait_for_function("document.querySelector('#documentFileOperationStatus')?.dataset.state==='success'&&!FigureStudio.app.getBrowserSessionState().busy")
    await case.capture('mixed-source-open.png','Candidate: the retained scientific composition opens before new fixture creation or styling; Library is closed and the original artwork is preserved.')
    await case.frame.locator('[data-figure-layout-choice="advanced"]').click()
    if await case.frame.locator('#figureStyleToggle').get_attribute('aria-pressed')!='true':await case.frame.locator('#figureStyleToggle').click()
    if not await case.frame.locator('#figureInspectorPanel').evaluate('e=>e.classList.contains("is-floating")'):await case.frame.locator('[data-rail-action="float"][data-rail="right"]').click()
    await case.menu_command('view','fit-screen')
    async def point(x,y):return await case.frame.evaluate('p=>FigureStudio.app.sceneToClientForQa(p)',dict(x=x,y=y))
    await case.frame.locator('.tool-primary[data-tool="line"]').click()
    await case.frame.locator('[data-line-picker-preset="straight"]').click()
    p1,p2=await point(60,215),await point(210,215)
    await case.page.mouse.move(p1['x'],p1['y']);await case.page.mouse.down();await case.page.mouse.move(p2['x'],p2['y'],steps=8);await case.page.mouse.up()
    line_id=await case.frame.evaluate('FigureStudio.app.getSelectionStateForQa().activeObjectId')
    case.case['lineId']=line_id
    line=await case.frame.evaluate('id=>{const o=FigureStudio.app.getObjectByIdForQa(id);return{type:o?.type,figureType:o?.figureType,strokeWidth:o?.strokeWidth,style:o?.styleMeta}}',line_id)
    case.write('line-created.json',line)
    case.check('Trusted Line preset/drag creates a native line',line['figureType'] in ['line','arrow'] or line['type']=='line',line)
    field=case.frame.locator('#figureSimpleStyleControls input[data-context-property="strokeWidth"]')
    await field.wait_for(state='visible');case.check('Style exposes an enabled named Line width field',await field.is_enabled() and 'Line width' in await field.locator('..').inner_text())
    before_width=await case.history();await field.fill('4');await field.press('Tab')
    await case.frame.wait_for_function('id=>{const o=FigureStudio.app.getObjectByIdForQa(id);return Number(o?.styleMeta?.strokeWidth??o?.strokeWidth)===4}',arg=line_id)
    case.check('Line width uses one native history entry',(await case.history())['undoDepth']==before_width['undoDepth']+1)
    await case.capture('advanced-line-style.png','Candidate: Advanced shows the same compact floating Inspector surface with a clear Line width value on a genuinely drawn native line beside the scientific composition.')
    existing=await case.document()
    def find_label(nodes):
     for node in nodes:
      if node.get('text')=='Editable label':return node['figureId']
      found=find_label(node.get('objects',[]))
      if found:return found
    case.write('before-text-selection.json',existing)
    text_id=find_label(existing['project']['fabric']['objects'])
    assert text_id,'Real fixture label missing'
    await case.select(text_id);case.case['textId']=text_id
    text_before=await case.frame.evaluate('id=>{const o=FigureStudio.app.getObjectByIdForQa(id);return{type:o.type,text:o.text,fontSize:o.fontSize,fontWeight:o.fontWeight,fontFamily:o.fontFamily}}',text_id)
    case.check('Fixture is editable native text', 'text' in text_before['type'].lower() and text_before['text']=='Editable label',text_before)
    field=case.frame.locator('#figureSimpleStyleControls input[data-context-property="fontSize"]');await field.wait_for(state='visible')
    case.check('Style exposes enabled Text size',await field.is_enabled() and 'Text size' in await field.locator('..').inner_text())
    desired_size=20 if float(await field.input_value())==18 else 18
    case.case['textSizePoints']=desired_size
    before_size=await case.history();await field.fill(str(desired_size));await field.press('Tab')
    await case.frame.wait_for_function('size=>Number(document.querySelector("#figureSimpleStyleControls input[data-context-property=fontSize]")?.value)===size',arg=desired_size)
    case.check('Text size uses one native history entry',(await case.history())['undoDepth']==before_size['undoDepth']+1)
    desired_weight='400' if str(text_before['fontWeight']) in ['700','bold'] else '700'
    case.case['textWeight']=desired_weight
    before_bold=await case.history();bold=case.frame.locator('#figureSimpleStyleControls [data-context-action="toggle-bold"]');await bold.click()
    await case.frame.wait_for_function('([id,weight])=>String(FigureStudio.app.getObjectByIdForQa(id)?.fontWeight)===weight',arg=[text_id,desired_weight])
    case.check('Bold means font weight, keeps editable text, one history entry',(await case.history())['undoDepth']==before_bold['undoDepth']+1 and await case.frame.evaluate('id=>FigureStudio.app.getObjectByIdForQa(id)?.text',text_id)=='Editable label')
    await inspector_editing_controls(case,text_id,line_id)
    await case.capture('advanced-text-style.png','Candidate: Advanced offers readable Text size and named Bold on editable text, without presenting text outline width; the mixed figure remains visible.')
    for mode in ['simple','advanced']:
     await case.frame.locator(f'[data-figure-layout-choice="{mode}"]').click()
     rect=await case.frame.locator('#figureInspectorPanel').bounding_box()
     case.case.setdefault('modeRects',{})[mode]=rect
     case.check(mode+' keeps a visible floating Inspector and text controls',await case.frame.locator('#figureSimpleStyleControls input[data-context-property="fontSize"]').is_visible() and await case.frame.locator('#figureInspectorPanel').evaluate('e=>e.classList.contains("is-floating")'))
     await case.capture(mode+'-mixed-style.png','Candidate: the populated scientific composition, native label and native line retain one compact floating Inspector surface in '+mode+'; lower controls scroll within the preserved user-sized panel.')
    case.check('Simple/Advanced retain exact floating rect',case.case['modeRects']['simple']==case.case['modeRects']['advanced'])
    await case.frame.locator('#inspectorContent').evaluate('e=>e.scrollTop=e.scrollHeight')
    case.check('Lower Appearance controls reachable with the single inner scroll owner',await case.frame.locator('#inspectorContent').evaluate('e=>e.scrollHeight>e.clientHeight&&e.scrollTop>0'))
    await case.capture('style-lower-controls.png','Candidate: scrolling inside the compact Inspector surface reaches lower text and appearance controls without cropping them or changing the floating user geometry.')
    await case.frame.locator('[data-inspector-tab="properties"]').click()
    case.check('Properties is an optional view in the same rail',await case.frame.locator('#propertiesInspectorTab').get_attribute('aria-current')=='page' and not await case.frame.locator('#figureSimpleStylePanel').is_visible())
    await case.frame.locator('[data-inspector-tab="appearance"]').click()
    before_switch=await case.document();hist=await case.history()
    await case.switch('presentation')
    inspector=case.frame.locator('[data-deck-command="format"]')
    case.check('Slidedeck names the same Inspector surface',await inspector.inner_text()=='Inspector')
    if await inspector.get_attribute('aria-pressed')=='true':await inspector.click()
    case.check('Slidedeck Inspector is genuinely closed before the Open action',await inspector.get_attribute('aria-pressed')=='false' and not await case.frame.locator('.inspector-tabs').is_visible())
    await inspector.click()
    case.check('Slidedeck Inspector Open is an actual visible action',await inspector.get_attribute('aria-pressed')=='true')
    case.check('Slidedeck retains the three Inspector views',await case.frame.evaluate('()=>[...document.querySelectorAll("[data-inspector-tab]")].filter(e=>e.getBoundingClientRect().width).map(e=>e.dataset.inspectorTab).join(",")=="appearance,properties,layers"'))
    await case.capture('slidedeck-return-check.png','Candidate: entering Slidedeck retains Appearance, Properties and Layers beside the Figure/Slidedeck views; this is a navigation regression check, not deck/export acceptance.')
    await case.switch('figure')
    after_switch=await case.document();after_hist=await case.history()
    case.write('switch-before.json',dict(document=before_switch,history=hist));case.write('switch-after.json',dict(document=after_switch,history=after_hist))
    differences=d.exact_differences(authored(before_switch),authored(after_switch));case.write('switch-differences.json',differences);case.write('switch-raw-differences.json',d.exact_differences(before_switch,after_switch))
    case.check('Figure return preserves authored mixed document and history',not differences and after_hist==hist,dict(differences=differences,historyBefore=hist,historyAfter=after_hist))
    await case.frame.locator('[data-figure-layout-choice="simple"]').click()
    await prepare_figure_file_panels(case);await case.menu_command('view','fit-screen')
    case.case['warmPersistenceViewport']=await case.frame.locator('#viewport').evaluate('e=>e.getBoundingClientRect().toJSON()')
    path,warm=await case.save('style-mixed-first.fsfigure');case.write('mixed-saved-warm.json',warm)
    case.case['actualSave']={'path':str(path),'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
    await case.context.close();case.context=None;await browser.close();browser=await pw.chromium.launch();case.browser=browser
    await case.launch();await d.library.enter_current_document_async(case.frame,kind='figure',preset='double-column',name='Cold styled mixed figure')
    case.case['coldPreparedPersistenceViewport']=await prepare_figure_file_panels(case)
    case.check('Warm Save and prepared cold Open use the same physical viewport',case.case['warmPersistenceViewport']==case.case['coldPreparedPersistenceViewport'],dict(warm=case.case['warmPersistenceViewport'],coldPrepared=case.case['coldPreparedPersistenceViewport']))
    await case.frame.locator('#fileMenuTrigger').click()
    async with case.page.expect_file_chooser() as chooser:await case.frame.locator('[data-menu="file"] [data-command="open-project"]').click()
    await(await chooser.value).set_files(path);await case.frame.wait_for_function("document.querySelector('#documentFileOperationStatus')?.dataset.state==='success'&&!FigureStudio.app.getBrowserSessionState().busy")
    await case.capture('mixed-natural-cold.png','Candidate: a new browser naturally opens the actual styled mixed-figure Save before model inspection or Fit; editable label, native line and scientific drawings remain intact.')
    cold=await case.document();case.write('mixed-cold-document.json',cold)
    case.write('mixed-cold-differences.json',d.exact_differences(authored(warm),authored(cold)))
    case.check('Actual mixed Save/fresh browser preserves complete authored document',authored(warm)==authored(cold))
    restored_library=await case.frame.evaluate('FigureStudio.app.getSwatchLibraryStateForQa()')
    case.write('saved-colors-cold.json',restored_library)
    case.check('Actual Save/fresh-process Open preserves the added named color and global link',any(s['id']==case.case['savedColor']['id'] and s['name']=='Assay blue' and s['color'].lower()=='#125b8a' for s in restored_library['swatches']) and restored_library['linkedObjectCount']>=1)
    case.check('No application errors',not report['pageErrors'] and not report['consoleErrors'],{'page':report['pageErrors'],'console':report['consoleErrors']})


async def pdf_journey(case,pw):
    browser=case.browser;report=case.report
    fixture=ARGS.fixture
    await case.frame.locator('#fileMenuTrigger').click()
    async with case.page.expect_file_chooser() as chooser:await case.frame.locator('[data-menu="file"] [data-command="open-project"]').click()
    await(await chooser.value).set_files(fixture)
    await case.frame.wait_for_function("document.querySelector('#documentFileOperationStatus')?.dataset.state==='success'&&!FigureStudio.app.getBrowserSessionState().busy")
    await case.capture('pdf-source-natural.png','The genuine saved Figure2 opens naturally before selection or Fit; the original plots and editable labels remain visible.')
    await case.frame.locator('[data-figure-layout-choice="advanced"]').click()
    if await case.frame.locator('#figureStyleToggle').get_attribute('aria-pressed')!='true':await case.frame.locator('#figureStyleToggle').click()
    if not await case.frame.locator('#figureInspectorPanel').evaluate('e=>e.classList.contains("is-floating")'):await case.frame.locator('[data-rail-action="float"][data-rail="right"]').click()
    text_id='text-mvwsd6u3-22';await case.select(text_id)
    before=await case.document();hist=await case.history();case.write('pdf-before.json',before)
    native=await case.frame.evaluate('id=>{const o=FigureStudio.app.getObjectByIdForQa(id);return{type:o?.type,text:o?.text,fontSize:o?.fontSize,fontWeight:o?.fontWeight,fontFamily:o?.fontFamily,context:FigureStudio.app.getSelectionContextStateForQa()}}',text_id)
    case.write('pdf-label-before.json',native)
    case.check('Editable PDF label has no duplicate canvas Source badge over the scientific figure',await case.frame.locator('#objectStatusOverlay .object-status-badge.source:visible').count()==0)
    case.check('The selected label remains genuine editable PDF text',native['type'].lower()=='pdfpositionedtext' and native['text']=='Sensitive (n=91)' and native['fontFamily'].startswith('figurepdf'),native)
    field=case.frame.locator('#figureSimpleStyleControls input[data-context-property="fontSize"]');await field.wait_for(state='visible')
    old=float(await field.input_value());target=round(max(4,old+1),1)
    case.check('PDF label has an enabled Text size control',await field.is_enabled() and 'Text size' in await field.locator('..').inner_text(),dict(oldPoints=old,newPoints=target))
    await case.capture('pdf-style-before.png','Advanced Style shows the genuine selected PDF label with its supported text-size and font controls; the complete scientific figure remains available.')
    await field.fill(str(target));await field.press('Tab')
    await case.frame.wait_for_function('target=>Number(document.querySelector("#figureSimpleStyleControls [data-context-property=fontSize]")?.value)===target',arg=target)
    after=await case.document();case.write('pdf-after-size.json',after);case.write('pdf-size-differences.json',d.exact_differences(before,after))
    case.check('PDF text-size change uses one history entry',(await case.history())['undoDepth']==hist['undoDepth']+1)
    def find(nodes):
     for n in nodes:
      if n.get('figureId')==text_id:return n
      result=find(n.get('objects',[]))
      if result:return result
    old_label=find(before['project']['fabric']['objects']);new_label=find(after['project']['fabric']['objects'])
    case.check('PDF label text and complete original glyph source stay exact',old_label['text']==new_label['text'] and old_label['pdfTextSource']==new_label['pdfTextSource'])
    case.check('Text size changes the selected native label',old_label['fontSize']!=new_label['fontSize'])
    def without_target(value):
        if isinstance(value,dict):
            if value.get('figureId')==text_id:return {'selectedPdfLabel':text_id}
            return {key:without_target(item) for key,item in value.items()}
        if isinstance(value,list):return [without_target(item) for item in value]
        return value
    case.check('Neighboring native PDF artwork remains exact',sel.m.equivalent(without_target(before['project']['fabric']['objects']),without_target(after['project']['fabric']['objects'])))
    case.check('Complete PDF sources and artifact references stay exact',all(before['project'].get(k)==after['project'].get(k) for k in ['pdfSources','artifactRefs']))
    bold=case.frame.locator('#figureSimpleStyleControls [data-context-action="toggle-bold"]')
    case.case['pdfWeightAvailability']=dict(present=await bold.count()==1,enabled=await bold.is_enabled(),label=await bold.inner_text())
    case.check('Weight is named Bold and no text Line width is offered',await bold.inner_text()=='Bold' and await case.frame.locator('#figureSimpleStyleControls [data-context-property="strokeWidth"]').count()==0)
    await case.capture('pdf-style-size.png','The genuine PDF label retains text and its original embedded source after a supported size change; Style identifies text size and Bold separately from line width.')
    await case.undo();undone=await case.document();case.write('pdf-undone.json',undone)
    case.write('pdf-undo-differences.json',d.exact_differences(sel.m.pdf.artwork_without_session_isolation(before['project']['fabric']['objects']),sel.m.pdf.artwork_without_session_isolation(undone['project']['fabric']['objects'])))
    case.check('One Undo restores complete native PDF artwork',sel.m.equivalent(before['project']['fabric']['objects'],undone['project']['fabric']['objects']))
    await case.undo(redo=True);redone=await case.document();case.write('pdf-redone.json',redone)
    case.check('One Redo restores complete styled native PDF artwork',sel.m.equivalent(after['project']['fabric']['objects'],redone['project']['fabric']['objects']))
    await case.frame.locator('[data-figure-layout-choice="simple"]').click();await case.menu_command('view','fit-screen')
    path,warm=await case.save('pdf-style-first.fsfigure');case.write('pdf-saved-warm.json',warm)
    file_doc=json.loads(path.read_text(encoding='utf-8'));case.write('pdf-download-content.json',file_doc)
    case.case['actualSave']={'path':str(path),'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
    await case.context.close();case.context=None;await browser.close();browser=await pw.chromium.launch();case.browser=browser
    await case.launch();await d.library.enter_current_document_async(case.frame,kind='figure',preset='double-column',name='Cold styled PDF label')
    await case.frame.locator('#fileMenuTrigger').click()
    async with case.page.expect_file_chooser() as chooser:await case.frame.locator('[data-menu="file"] [data-command="open-project"]').click()
    await(await chooser.value).set_files(path);await case.frame.wait_for_function("document.querySelector('#documentFileOperationStatus')?.dataset.state==='success'&&!FigureStudio.app.getBrowserSessionState().busy")
    await case.capture('pdf-natural-cold.png','A genuinely new browser opens the actual styled PDF Save before inspection or Fit, preserving the scientific page and editable label.')
    cold=await case.document();case.write('pdf-cold-document.json',cold)
    case.write('pdf-warm-file-differences.json',d.exact_differences(warm['project']['fabric']['objects'],file_doc['project']['fabric']['objects']))
    case.write('pdf-file-cold-differences.json',d.exact_differences(file_doc['project']['fabric']['objects'],cold['project']['fabric']['objects']))
    case.check('Actual PDF Save and new-browser Open preserve complete native artwork under the existing strict PDF policy',sel.m.equivalent(warm['project']['fabric']['objects'],file_doc['project']['fabric']['objects']) and sel.m.equivalent(file_doc['project']['fabric']['objects'],cold['project']['fabric']['objects']))
    case.check('Cold original PDF sources and artifact references remain exact',all(before['project'].get(k)==cold['project'].get(k) for k in ['pdfSources','artifactRefs']))
    case.check('No application errors',not report['pageErrors'] and not report['consoleErrors'])

MEASURE="""()=>{const rail=document.querySelector('#figureInspectorPanel'),body=document.querySelector('#inspectorContent'),r=rail.getBoundingClientRect(),b=body.getBoundingClientRect();
 const inside=e=>{if(!e)return false;const x=e.getBoundingClientRect();return x.width>0&&x.height>0&&x.left>=b.left-1&&x.right<=b.right+1&&x.top>=b.top-1&&x.bottom<=b.bottom+1};
 return{rail:r.toJSON(),body:b.toJSON(),scrollHeight:body.scrollHeight,clientHeight:body.clientHeight,scrollTop:body.scrollTop,
 floating:rail.classList.contains('is-floating'),withinWindow:r.left>=0&&r.top>=0&&r.right<=innerWidth&&r.bottom<=innerHeight,
 activeTab:document.querySelector('[data-inspector-tab].active')?.dataset.inspectorTab,
 paletteReachable:inside(body.querySelector('[data-asset-palette]')),firstPartReachable:inside(body.querySelector('[data-asset-color-region]')),
 lastControlReachable:inside(body.querySelector('#savedColorsDisclosure > summary')),
 scrollingOwners:[...rail.querySelectorAll('*')].filter(e=>e.clientHeight>0&&e.scrollHeight>e.clientHeight+1&&['auto','scroll'].includes(getComputedStyle(e).overflowY)).map(e=>e.id||e.className),
 viewport:document.querySelector('#viewport').getBoundingClientRect().toJSON(),rootOverflow:document.documentElement.scrollWidth>innerWidth};}"""

async def layout_journey(case,pw):
    prefs=case.case['preferenceCase']
    if prefs=='saved':
        await case.frame.locator('[data-figure-layout-choice="advanced"]').click()
        await show_style(case)
        await case.frame.locator('[data-inspector-tab="layers"]').click()
        await d.library.show_library_async(case.frame,tab='tools')
        saved=await case.frame.evaluate("()=>({storage:{...localStorage},rail:document.querySelector('#figureInspectorPanel').getBoundingClientRect().toJSON(),tab:document.querySelector('[data-inspector-tab].active')?.dataset.inspectorTab})")
        case.write('preferences-before-restart.json',saved)
        await case.page.reload(wait_until='domcontentloaded');case.frame=case.page
        await case.frame.wait_for_function('window.FigureStudio?.app?.isReady===true')
        await d.library.enter_current_document_async(case.frame,kind='figure',preset='double-column',name='Saved Style preferences')
        restored=await case.frame.evaluate("()=>({storage:{...localStorage},rail:document.querySelector('#figureInspectorPanel').getBoundingClientRect().toJSON(),tab:document.querySelector('[data-inspector-tab].active')?.dataset.inspectorTab})")
        case.write('preferences-after-restart.json',restored)
        case.check('Saved layout retains floating geometry and Layers tab',saved['rail']==restored['rail'] and restored['tab']=='layers',dict(before=saved['rail'],after=restored['rail'],tab=restored['tab']))
        expected=json.loads(saved['storage']['figureStudio.layoutPresets.v1'])
        for mode in ['simple','advanced']:expected[mode]['rails']['left']['visible']=False
        actual=json.loads(restored['storage']['figureStudio.layoutPresets.v1'])
        case.check('Startup changes only Library visibility in stored Figure profiles',expected==actual and saved['storage'].get('figureStudio.libraryView.v1')==restored['storage'].get('figureStudio.libraryView.v1'))
    case.check(prefs+' startup keeps Library closed',await case.frame.locator('#figureLibraryToggle').get_attribute('aria-pressed')=='false')
    await open_fixture(case,ARGS.fixture)
    before=await case.document();history=await case.history();case.write('layout-document-before.json',before)
    assets=[n for n in before['project']['fabric']['objects'] if n.get('scientificAssetMeta')]
    case.check('Layout fixture contains real native drawings plus editable text and line',len(assets)>=4 and any(n.get('figureType')=='text' for n in before['project']['fabric']['objects']) and any(n.get('figureType')=='line' for n in before['project']['fabric']['objects']))
    asset_id=assets[0]['figureId'];await case.select(asset_id)
    await d.library.show_library_async(case.frame,tab='tools')
    await case.frame.locator('[data-figure-layout-choice="advanced"]').click();await case.select(asset_id)
    case.check('Explicit Library show survives selection and mode change',await case.frame.locator('#figureLibraryToggle').get_attribute('aria-pressed')=='true')
    await case.frame.locator('#figureLibraryToggle').click()
    await show_style(case)
    rects={}
    for mode in ['simple','advanced']:
        await case.frame.locator(f'[data-figure-layout-choice="{mode}"]').click()
        await case.select(asset_id)
        await case.frame.locator('#inspectorContent').evaluate('e=>e.scrollTop=0')
        state=await case.frame.evaluate(MEASURE);case.write(mode+'-top-metrics.json',state);rects[mode]=state['rail']
        case.check(mode+' has one contained compact Inspector rail',state['withinWindow'] and state['floating'] and not state['rootOverflow'] and state['activeTab']=='appearance' and state['scrollingOwners']==['inspectorContent'],state)
        case.check(mode+' shows Palette and a full part-color input without scrolling',state['paletteReachable'] and state['firstPartReachable'],state)
        case.check(mode+' keeps explicitly hidden Library closed',await case.frame.locator('#figureLibraryToggle').get_attribute('aria-pressed')=='false')
        await case.capture(mode+'-style.png',f'{case.name}: the populated scientific figure has a closed Library and one compact floating Inspector panel in {mode}; drawing actions and palette are visible, and lower part colors scroll inside it.')
        await case.frame.locator('#inspectorContent').hover();await case.page.mouse.wheel(0,1400)
        await case.frame.wait_for_function("document.querySelector('#inspectorContent').scrollTop>0")
        lower=await case.frame.evaluate(MEASURE);case.write(mode+'-lower-metrics.json',lower)
        case.check(mode+' lower controls are genuinely reachable within the same scroll owner',lower['lastControlReachable'] and lower['rail']==state['rail'],lower)
        if mode=='advanced' and prefs=='saved':
            await case.capture('lower-controls.png',f'{case.name}: scrolling inside the same compact Inspector panel reaches its final controls; the surrounding canvas and panel geometry stay fixed.')
    case.check('Simple and Advanced preserve the exact user-sized floating rectangle',rects['simple']==rects['advanced'])
    await case.frame.locator('[data-inspector-tab="properties"]').click()
    case.check('Properties uses the same rail',await case.frame.locator('#propertiesInspectorTab').get_attribute('aria-current')=='page' and not await case.frame.locator('#figureSimpleStylePanel').is_visible())
    await case.frame.locator('[data-inspector-tab="layers"]').click()
    case.check('Layers uses the same rail',await case.frame.locator('#layersInspectorTab').get_attribute('aria-current')=='page')
    # Inspector buttons retain native keyboard behavior. Return keyboard focus
    # to the existing canvas viewport before using its selection shortcut.
    await case.frame.locator('#viewport').focus()
    await case.page.keyboard.press('Escape')
    await case.frame.wait_for_function('FigureStudio.app.getSelectionStateForQa().selectedCount===0')
    case.check('Ordinary Escape genuinely clears the fixture selection',await case.frame.evaluate('FigureStudio.app.getSelectionStateForQa().selectedCount')==0)
    for mode in ['simple','advanced']:
        await case.frame.locator(f'[data-figure-layout-choice="{mode}"]').click()
        await case.frame.locator('[data-inspector-tab="appearance"]').click()
        case.check(mode+' keeps the saved Inspector visible with no selection',await case.frame.locator('#figureInspectorPanel').is_visible() and await case.frame.locator('#figureStyleToggle').get_attribute('aria-pressed')=='true')
        case.check(mode+' empty selection preserves the floating rectangle',await case.frame.locator('#figureInspectorPanel').evaluate('e=>e.getBoundingClientRect().toJSON()')==rects[mode])
    await case.capture('inspector-empty-selection.png',f'{case.name}: clearing fixture selection leaves the same Inspector open with a concise Appearance prompt and Saved colors; the populated scientific figure remains available.')
    after=await case.document();case.write('layout-document-after.json',after)
    case.check('Layout navigation preserves authored figure and history',authored(before)==authored(after) and history==await case.history())


async def run():
    out=ARGS.output_dir.resolve();out.mkdir(parents=True,exist_ok=False)
    report=dict(status='running',scope=ARGS.journey+' source UI checks; native host, release packaging, exports and typography backends are separate',cases=[],checks=[],captures=[],pageErrors=[],consoleErrors=[],failedRequests=[],vendorResponses=[])
    overrides=['app/app.js','app/styles.css','app/index.html','app/scientific-asset-preview.js','app/scientific-asset-color-controls.js','app/help/figure-studio-help.json']
    report['runtimeFiles']={relative:hashlib.sha256(((ARGS.overlay/relative) if ARGS.overlay and (ARGS.overlay/relative).is_file() else ARGS.root/relative).read_bytes()).hexdigest() for relative in overrides}
    index=(ARGS.overlay/'app/index.html') if ARGS.overlay and (ARGS.overlay/'app/index.html').is_file() else ARGS.root/'app/index.html'
    references=re.findall(r'(?:src|href)="([^"]+)"',index.read_text(encoding='utf-8'))
    names=['app.js','styles.css','scientific-asset-preview.js','scientific-asset-color-controls.js']
    ARGS.ui_references={name:next(url for url in references if urlparse(url).path==name) for name in names}
    report['uiReferenceUrls']=ARGS.ui_references
    if ARGS.fixture:report['fixture']={'path':str(ARGS.fixture.resolve()),'bytes':ARGS.fixture.stat().st_size,'sha256':hashlib.sha256(ARGS.fixture.read_bytes()).hexdigest()}
    class Overlay(d.library.native.QuietHandler):
        def translate_path(self,path):
            relative=path.split('?',1)[0].lstrip('/')
            target=ARGS.overlay/relative if ARGS.overlay else None
            return str(target) if target and relative in overrides and target.is_file() else super().translate_path(path)
    server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Overlay,directory=str(ARGS.root)))
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    try:
        async with async_playwright() as pw:
            rows=[(size,theme,prefs) for size in [(1280,800),(1440,1000),(1920,1080)] for theme in ['light','dark'] for prefs in ['fresh','saved']] if ARGS.journey=='layout' else [((1440,1000),'light','fresh')]
            for size,theme,prefs in rows:
                label=f'{size[0]}x{size[1]}-{theme}'+('-'+prefs if ARGS.journey=='layout' else '')
                if ARGS.case and label!=ARGS.case:continue
                browser=await pw.chromium.launch()
                case=StyleCase(browser,f'http://127.0.0.1:{server.server_port}','direct',size,theme,out,report,label=label)
                case.case['preferenceCase']=prefs
                try:
                    await case.launch()
                    await d.library.enter_current_document_async(case.frame,kind='figure',preset='double-column',name='Style and preview checks')
                    response=await case.page.request.get(case.base+'/app/app.js')
                    case.check('Served current App matches expected source',hashlib.sha256(await response.body()).hexdigest()==ARGS.expected_app_sha256)
                    await globals()[ARGS.journey+'_journey'](case,pw)
                    case.check('No application errors',not report['pageErrors'] and not report['consoleErrors'])
                    case.case['status']='passed'
                except BaseException as error:
                    case.case.update(status='failed',error=str(error))
                    if case.page and not case.page.is_closed():await case.page.screenshot(path=str(case.out/'failure.png'))
                    raise
                finally:
                    if case.context:await case.context.close();case.case['contextClosed']=True
                    await case.browser.close();case.case['browserClosed']=not case.browser.is_connected()
                    case.write('case.json',case.case)
                    (out/'report.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
            report['status']='passed'
    except BaseException as error:
        report.update(status='failed',error=str(error));raise
    finally:
        server.shutdown();server.server_close();thread.join(timeout=5);report['serverClosed']=not thread.is_alive()
        (out/'report.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
        print(json.dumps(dict(status=report['status'],checks=len(report['checks']),captures=len(report['captures']),output=str(out))),flush=True)

def main():
    global ARGS
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,required=True,help='Immutable editor runtime tree')
    parser.add_argument('--overlay',type=Path,help='Optional Inspector source candidate overlay including current Help')
    parser.add_argument('--expected-app-sha256',required=True)
    parser.add_argument('--output-dir',type=Path,required=True)
    parser.add_argument('--journey',choices=['preview','mixed','pdf','layout'],required=True)
    parser.add_argument('--case',help='One explicit layout case, e.g. 1440x1000-light-saved; one lease per case')
    parser.add_argument('--fixture',type=Path,help='Real saved figure for mixed, PDF or layout')
    ARGS=parser.parse_args()
    if ARGS.journey!='preview' and not ARGS.fixture:parser.error('This journey requires --fixture')
    asyncio.run(run())

if __name__=='__main__':main()
