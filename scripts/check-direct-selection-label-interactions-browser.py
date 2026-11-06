"""Public Selection/Direct Selection with editable labels and real Library artwork."""
import argparse
import asyncio
import importlib.util
import json
import hashlib
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('mixed_direct_labels', ROOT / 'scripts/check-direct-selection-labels-browser.py')
s = importlib.util.module_from_spec(spec)
spec.loader.exec_module(s)
m = s.m
from figure_studio_entry_qa import enter_current_document_async


def handle_key(handle):
    return (handle["objectId"],handle["commandIndex"],handle["handleType"])


class Interactions(s.Selection):
    async def segment_cancel(self):
        before = await self.full_artwork('segment-cancel-before')
        state = await self.state('segment-cancel-before')
        target = self.surface.locator(f'.path-segment-hit:not([data-object-id="{state["direct"]["objectId"]}"])').first
        box = await target.bounding_box()
        self.require('Mixed selection has a visible nonprimary segment target', bool(box))
        origin = (box['x'] + box['width']/2, box['y'] + box['height']/2)
        await self.page.keyboard.down('Control')
        await self.page.mouse.move(*origin)
        await self.page.mouse.down()
        await self.page.mouse.move(origin[0]-12, origin[1]+3, steps=4)
        held = await self.state('segment-cancel-held')
        self.require('Segment reshape has path-only operands while held', not held['direct']['selectedTextIds'] and held['direct']['objectId'] != state['direct']['objectId'])
        await self.page.keyboard.press('Escape')
        await self.page.mouse.up()
        await self.page.keyboard.up('Control')
        await self.settled()
        after = await self.state('segment-cancel-after')
        self.require('Segment Escape restores the complete prior label and point selection', all(after['direct'][key] == state['direct'][key] for key in ['objectId', 'objectIds', 'selectedTextIds', 'selectedHandles']) and after['selection']['selectedIds'] == state['selection']['selectedIds'])
        self.require('Segment Escape restores exact artwork and history', m.equivalent(before, await self.full_artwork('segment-cancel-after')) and after['history'] == state['history'])

    async def label_point(self, object_id):
        # Read-only geometry chooses a painted part of a real label. All actions
        # below still use ordinary trusted mouse/keyboard input.
        point = await self.surface.evaluate('''id => {
            const o = FigureStudio.app.getObjectByIdForQa(id), b = o.getBoundingRect();
            for (const y of [.3, .5, .7]) for (let x = .05; x < .95; x += .05) {
                const p = {x:b.left+b.width*x, y:b.top+b.height*y};
                if (FigureStudioPdfPaintHitTest.hitObject(o,p,{fabric:window.fabric,tolerance:0})) return p;
            }
            return null;
        }''', object_id)
        self.require('Target has a painted native text hit', bool(point), object_id)
        return await m.base.HELPERS.canvas_scene_point(self.surface, point['x'], point['y'])

    async def click_label(self, name, object_id, expected_texts, expected_paths, expected_handles, shift=False):
        artwork = await self.full_artwork(name + '-before')
        before = await self.state(name + '-before')
        point = await self.label_point(object_id)
        if shift:
            await self.page.keyboard.down('Shift')
        await self.page.mouse.click(point['x'], point['y'])
        if shift:
            await self.page.keyboard.up('Shift')
        await self.settled()
        after = await self.state(name + '-after')
        self.require(name + ' selects precisely the intended editable labels', set(after['direct']['selectedTextIds']) == set(expected_texts), after['direct']['selectedTextIds'])
        self.require(name + ' preserves the intended paths and anchors', set(after['direct']['objectIds']) == set(expected_paths) and after['direct']['selectedHandles'] == expected_handles)
        self.require(name + ' changes no artwork or history', m.equivalent(artwork, await self.full_artwork(name + '-after')) and before['history'] == after['history'])
        return after

    async def nudge_mixed(self):
        before = await self.full_artwork('nudge-before')
        state = await self.state('nudge-before')
        inventory = await self.surface.evaluate(m.g.INVENTORY)
        await self.surface.locator('#viewport').focus()
        await self.page.keyboard.press('ArrowRight')
        await self.history(state['history']['undoDepth'] + 1)
        await self.settled()
        after = await self.state('nudge-after')
        moved = await self.surface.evaluate(m.g.INVENTORY)
        (self.out / 'nudge-inventories.json').write_text(json.dumps(dict(before=inventory,after=moved),indent=2)+'\n',encoding='utf-8')
        await self.full_artwork('nudge-observed')
        selected_texts = set(state['direct']['selectedTextIds'])
        selected_paths = set(state['direct']['objectIds'])
        old = {o['id']: o for o in inventory['leaves']}
        errors = []
        for o in moved['leaves']:
            prior = old[o['id']]
            if o['id'] in selected_texts:
                if max(abs(o['matrix'][i] - prior['matrix'][i] - (1 if i == 4 else 0)) for i in range(6)) > 1e-6 or any(o[k] != prior[k] for k in ['text', 'parent', 'path', 'fill', 'stroke', 'strokeWidth']):
                    errors.append(o['id'])
            elif o['id'] not in selected_paths:
                if max(abs(a-b) for a,b in zip(o['matrix'],prior['matrix'])) > 1e-6 or max(abs(o['bounds'][k]-prior['bounds'][k]) for k in o['bounds']) > 1e-6 or any(o[k] != prior[k] for k in o if k not in ['matrix', 'bounds']):
                    errors.append(o['id'])
        actual = {(h['objectId'], h['commandIndex'], h['handleType']): h for h in after['direct']['selectedHandles']}
        for h in state['direct']['selectedHandles']:
            key = (h['objectId'], h['commandIndex'], h['handleType'])
            matrix = old[h['objectId']]['matrix']
            # Existing key nudges round local path coordinates to .001. Derive
            # the scene error bound from that unchanged policy and each matrix.
            bounds = [.000500001 * (abs(matrix[0]) + abs(matrix[2])), .000500001 * (abs(matrix[1]) + abs(matrix[3]))]
            if key not in actual or any(abs(actual[key][axis] - h[axis] - (1 if i == 0 else 0)) > bounds[i] + 1e-6 for i, axis in enumerate(['x', 'y'])):
                errors.append(key)
        self.require('Arrow nudge moves labels and points together while preserving neighbors', not errors, errors[:8])
        nudged = await self.full_artwork('nudge-after')
        await self.capture('mixed-nudge', 'A one-unit keyboard nudge moves complete editable labels and path anchors together; the feedback follows the selection and surrounding rows remain legible.')
        await self.page.keyboard.press('Control+z')
        await self.history(state['history']['undoDepth'])
        await self.settled()
        self.require('One Undo restores the entire mixed nudge', m.equivalent(before, await self.full_artwork('nudge-undone')))
        await self.page.keyboard.press('Control+y')
        await self.history(state['history']['undoDepth'] + 1)
        await self.settled()
        self.require('One Redo restores the entire mixed nudge', m.equivalent(nudged, await self.full_artwork('nudge-redone')))

    async def text_body_cancel(self, object_id):
        before = await self.full_artwork('text-body-before')
        state = await self.state('text-body-before')
        inventory = await self.surface.evaluate(m.g.INVENTORY)
        first = await self.label_point(object_id)
        await self.surface.evaluate('window.mixedInput=[]')
        await self.page.keyboard.down('Control')
        await self.page.mouse.move(first['x'], first['y'])
        await self.page.mouse.down()
        await self.page.mouse.move(first['x'] - 12, first['y'], steps=6)
        inputs = await self.surface.evaluate('window.mixedInput')
        down = next(e for e in inputs if e['type'] == 'pointerdown')
        move = next(e for e in reversed(inputs) if e['type'] == 'pointermove')
        delta = (move['x'] - down['x'], move['y'] - down['y'])
        self.require('Text body drag uses original trusted input', down['trusted'] and move['trusted'])
        errors = m.rigid(inventory, await self.surface.evaluate(m.g.INVENTORY), [object_id], delta)
        self.require('Text body drag moves only the complete editable label', not errors, errors[:8])
        await self.page.keyboard.press('Escape')
        await self.page.mouse.up()
        await self.page.keyboard.up('Control')
        await self.settled()
        self.require('Escape restores text body geometry and history', m.equivalent(before, await self.full_artwork('text-body-canceled')) and state['history'] == (await self.state('text-body-canceled'))['history'])

    async def subset_marquee(self,name,start,end,shift=False):
        self.phase(name+'-start')
        # Keep one complete native baseline per document, not repeated copies
        # of the same embedded scientific PDF after selection-only gestures.
        if not hasattr(self,'subset_artwork'):
            self.subset_artwork=await self.full_artwork(name+'-selection-baseline')
        before=await self.state(name+'-before')
        inventory=await self.surface.evaluate(m.g.INVENTORY)
        a=await m.base.HELPERS.canvas_scene_point(self.surface,*start);b=await m.base.HELPERS.canvas_scene_point(self.surface,*end)
        await self.surface.evaluate('window.mixedInput=[]')
        if shift:await self.page.keyboard.down('Shift')
        try:
            await self.page.mouse.move(a['x'],a['y']);await self.page.mouse.down()
            held=await self.surface.evaluate('FigureStudio.app.getDirectSelectionStateForQa()')
            self.require(name+' begins a marquee on blank canvas',held.get('marqueeVisible'))
            await self.page.mouse.move(b['x'],b['y'],steps=7);await self.page.mouse.up()
        finally:
            if shift:await self.page.keyboard.up('Shift')
        await self.settled();after=await self.state(name+'-after')
        events=await self.surface.evaluate('window.mixedInput');self.row.setdefault('inputs',{})[name]=events;self.save()
        down=next(e for e in events if e['type']=='pointerdown');up=next(e for e in reversed(events)if e['type']=='pointerup')
        self.require(name+' original trusted pointer events delivered',down['trusted']and up['trusted'])
        if shift:self.require(name+' receives Shift at pointerdown',any(e['type']=='modifier'and e['shift']and e['trusted']for e in events))
        x0,x1=sorted([down['x'],up['x']]);y0,y1=sorted([down['y'],up['y']])
        if shift:
            handles={handle_key(h)for h in before['direct']['handles'] if x0<=h['x']<=x1 and y0<=h['y']<=y1}
            texts={o['id']for o in inventory['leaves']if o['text']is not None and o['bounds']['left']<=x1 and o['bounds']['left']+o['bounds']['width']>=x0 and o['bounds']['top']<=y1 and o['bounds']['top']+o['bounds']['height']>=y0}
            expected_handles={handle_key(h)for h in before['direct']['selectedHandles']}^handles
            expected_texts=set(before['direct']['selectedTextIds'])^texts
            self.row.setdefault('expected',{})[name]=dict(hitHandles=sorted(handles),hitTextIds=sorted(texts),selectedHandles=sorted(expected_handles),selectedTextIds=sorted(expected_texts))
            self.require(name+' hits a strict mixed subset',bool(handles)and bool(texts)and len(handles)<len(before['direct']['handles']))
            self.require(name+' toggles precisely the intended anchors', {handle_key(h)for h in after['direct']['selectedHandles']}==expected_handles)
            self.require(name+' toggles complete editable labels and retains outside labels',set(after['direct']['selectedTextIds'])==expected_texts)
        else:self.require(name+' seeds a mixed selection',after['direct']['selectedTextCount']>0 and after['direct']['selectedHandleCount']>0)
        observed=json.loads(await self.surface.evaluate('()=>JSON.stringify(FigureStudio.app.buildProjectJsonForQa().fabric)'))
        self.row.setdefault('selectionArtworkChecks',{})[name]=dict(
            sha256=hashlib.sha256(json.dumps(observed,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
            equivalentToRetainedBaseline=m.equivalent(self.subset_artwork,observed))
        self.require(name+' preserves full artwork and history',self.row['selectionArtworkChecks'][name]['equivalentToRetainedBaseline']and before['history']==after['history'])
        self.require(name+' retains Direct Selection',after['direct']['tool']=='directSelect')
        self.phase(name+'-finished')
        return after

    async def ordinary_subset(self):
        ctx=await self.browser.new_context(viewport=dict(width=self.width,height=self.height),color_scheme=self.theme)
        await ctx.add_init_script('try{delete window.showSaveFilePicker;delete window.showOpenFilePicker;}catch(_){}')
        self.page=await ctx.new_page();self.page.set_default_timeout(20000)
        self.page.on('pageerror',lambda e:self.row['pageErrors'].append(str(e)))
        await self.page.goto(self.entry_url(),wait_until='domcontentloaded');self.surface=await m.base.HELPERS.resolve_figure_surface(self.page)
        await enter_current_document_async(self.surface.app_frame,kind='figure',preset='full-page',name='Ordinary mixed selection')
        await self.surface.evaluate('()=>FigureStudio.app.createSelectionContextParityScenarioForQa()')
        await self.surface.locator('#viewport').focus();await self.page.keyboard.press('z')
        await m.base.HELPERS.drag_scene(self.surface,(60,50),(710,350))
        # Establish the whole fixture's view before any selection gesture. At
        # narrow widths the zoom marquee can end outside the canvas, so leave
        # room for the right-hand editable note through public zoom controls.
        for _ in range(2):
            await self.surface.locator('[data-menu="view"] > .menu-trigger').click()
            await self.surface.locator('[data-menu="view"] [data-command="zoom-out"]').click()
        await self.surface.locator('#viewport').focus();await self.page.keyboard.press('Escape');await self.page.keyboard.press('a');await self.settled()
        inventory=await self.surface.evaluate(m.g.INVENTORY)
        viewport=await self.surface.locator('#viewport').bounding_box()
        for item in inventory['leaves']:
            b=item['bounds']
            first=await m.base.HELPERS.canvas_scene_point(self.surface,b['left'],b['top'])
            last=await m.base.HELPERS.canvas_scene_point(self.surface,b['left']+b['width'],b['top']+b['height'])
            self.require('Ordinary fixture is fully visible before selection: '+str(item['id']or item['text']or'unnamed native part'),
                first['x']>=viewport['x']+12 and first['y']>=viewport['y']+12 and
                last['x']<=viewport['x']+viewport['width']-12 and last['y']<=viewport['y']+viewport['height']-12)
        await self.surface.evaluate(m.WITNESS)
        # Extend the existing original-event witness with modifier delivery.
        await self.surface.evaluate("()=>window.addEventListener('pointerdown',e=>window.mixedInput.push({type:'modifier',shift:e.shiftKey,trusted:e.isTrusted}),true)")
        await self.subset_marquee('ordinary-seed',(270,70),(525,335))
        await self.subset_marquee('ordinary-remove-subset',(270,70),(400,306),True)
        await self.capture('ordinary-subset','A subset of native anchors and one whole editable label is removed, with remaining anchors still selected and readable surrounding artwork.')
        await self.subset_marquee('ordinary-readd-subset',(400,306),(270,70),True)
        await self.capture('ordinary-restored','The reverse-direction Shift marquee restores the same editable label and anchors without altering the ordinary artwork.')
        self.start=(270,70);await self.blank()
        await ctx.close()
        del self.subset_artwork

    async def run_subset_marquee(self):
        context=cold=None;self.started=time.perf_counter()
        fixture=ROOT/'qa_artifacts/drag47/cold-save-only-output/1440x1000-light/direct-second.fsfigure'
        try:
            await self.ordinary_subset()
            self.require('Exact genuine scientific fixture',hashlib.sha256(fixture.read_bytes()).hexdigest()=='78d9cd9c9952c31bccefa1eca9f4d1a3c780743ac2cb9605c89862e2e71759eb')
            context=await self.open_surface(self.browser,fixture);await self.focus_plot()
            await self.surface.evaluate("()=>window.addEventListener('pointerdown',e=>window.mixedInput.push({type:'modifier',shift:e.shiftKey,trusted:e.isTrusted}),true)")
            seed=await self.subset_marquee('pdf-seed',self.start,self.end)
            inventory=await self.surface.evaluate(m.g.INVENTORY)
            title=next(o for o in inventory['leaves']if 'Reactome pathways - genes up'in(o['text']or''))
            b=title['bounds'];end=(b['left']+b['width']*.8,self.start[1]+65)
            await self.subset_marquee('pdf-remove-subset',self.start,end,True)
            await self.capture('pdf-subset','A Shift marquee removes only the enclosed native anchors and complete pathway labels; remaining selection feedback and nearby scientific text stay readable.')
            await self.drag_points('subset-cancel',(4,1),cancel=True)
            restored=await self.subset_marquee('pdf-readd-subset',end,self.start,True)
            self.require('Reverse Shift marquee restores the original mixed selected set',set(map(handle_key,restored['direct']['selectedHandles']))==set(map(handle_key,seed['direct']['selectedHandles']))and set(restored['direct']['selectedTextIds'])==set(seed['direct']['selectedTextIds']))
            await self.capture('pdf-restored','The reverse-direction Shift marquee restores the same native anchors and editable labels, with the complete scientific panel intact.')
            await self.subset_marquee('pdf-retain-subset',self.start,end,True)
            before,moved,state,released=await self.drag_points('subset-move',(4,0))
            await self.page.keyboard.press('Control+z');await self.history(state['history']['undoDepth']);await self.settled()
            self.require('Undo restores the exact pre-move scientific artwork',m.equivalent(before,await self.full_artwork('subset-undone')))
            await self.page.keyboard.press('Control+y');await self.history(released['history']['undoDepth']);await self.settled()
            self.require('Redo restores the exact retained-subset edit',m.equivalent(moved,await self.full_artwork('subset-redone')))
            project,saved=await self.save_file('subset-first',await self.full_artwork('subset-warm-save'))
            await context.close();context=None;browser_type=self.browser.browser_type;await self.browser.close();self.row['warmBrowserClosed']=not self.browser.is_connected()
            cold=await browser_type.launch(**self.report['browserLaunchOptions']);await m.base.record_browser_runtime(cold,self.report,'cold')
            context=await self.open_surface(cold,project)
            await self.capture('subset-cold-open','The actual saved scientific file opens in a new Chromium process with editable text and intact surrounding artwork, before any further Fit or editing.')
            self.require('Fresh-process Open retains complete actual saved native artwork',m.equivalent(saved,await self.full_artwork('subset-cold-open')))
            del self.subset_artwork
            await self.focus_plot()
            await self.surface.evaluate("()=>window.addEventListener('pointerdown',e=>window.mixedInput.push({type:'modifier',shift:e.shiftKey,trusted:e.isTrusted}),true)")
            await self.subset_marquee('cold-seed',self.start,self.end)
            await self.subset_marquee('cold-remove-subset',self.start,end,True)
            await self.drag_points('cold-subset-move',(2,0))
            await self.capture('subset-cold-continued','After fresh Open, a Shift marquee again retains a precise mixed subset, and only its selected anchors and whole editable labels move.')
            await self.save_file('subset-second',await self.full_artwork('subset-cold-save'))
            self.require('No browser page errors',not self.row['pageErrors'],self.row['pageErrors']);self.row['status']='passed'
        except BaseException as error:
            self.row['status']='failed';self.row['error']=str(error)
            if hasattr(self,'page')and not self.page.is_closed():await self.page.screenshot(path=str(self.out/'failure.png'))
            raise
        finally:
            if context:await context.close()
            if cold:await cold.close();self.row['coldBrowserClosed']=not cold.is_connected()
            self.row['contextClosed']=True;self.save()

    async def run(self):
        if getattr(s.ARGS,"ordinary_subset",False):
            self.started=time.perf_counter()
            try:
                await self.ordinary_subset()
                self.require('No browser page errors',not self.row['pageErrors'],self.row['pageErrors'])
                self.row['status']='passed'
            except BaseException as error:
                self.row['status']='failed';self.row['error']=str(error)
                if hasattr(self,'page')and not self.page.is_closed():await self.page.screenshot(path=str(self.out/'failure.png'))
                raise
            finally:
                self.row['contextClosed']=True;self.save()
            return
        if getattr(s.ARGS,"subset_marquee",False):
            return await self.run_subset_marquee()
        context = None
        self.started = time.perf_counter()
        try:
            context = await self.open_surface(self.browser)
            await self.focus_plot()
            selected = await self.marquee('interaction-marquee')
            await self.segment_cancel()
            inventory = await self.surface.evaluate(m.g.INVENTORY)
            target = next(o['id'] for o in inventory['leaves'] if o['text'] == 'Extracellular Matrix Organization' and o['id'] in selected['direct']['selectedTextIds'])
            texts = selected['direct']['selectedTextIds']
            paths = selected['direct']['objectIds']
            handles = selected['direct']['selectedHandles']
            await self.click_label('shift-remove-label', target, [i for i in texts if i != target], paths, handles, shift=True)
            await self.click_label('shift-add-label', target, texts, paths, handles, shift=True)
            await self.nudge_mixed()
            await self.blank()
            await self.click_label('text-only-click', target, [target], [], [])
            await self.capture('text-only', 'Direct Selection selects a complete editable pathway label; there are no letter-outline points and neighboring artwork remains intact.')
            await self.text_body_cancel(target)
            await self.click_label('shift-remove-last-label', target, [], [], [], shift=True)
            cleared = await self.state('last-label-cleared')
            self.require('Removing the last label clears selection without changing tools', not cleared['direct']['active'] and cleared['direct']['tool'] == 'directSelect' and not cleared['selection']['selectedCount'])
            self.require('No browser page errors', not self.row['pageErrors'], self.row['pageErrors'])
            self.require('All declared interaction checks pass', all(c['passed'] for c in self.row['checks']))
            self.row['status'] = 'passed'
        except BaseException as error:
            self.row['status'] = 'failed'
            self.row['error'] = str(error)
            if hasattr(self, 'page') and not self.page.is_closed():
                await self.page.screenshot(path=str(self.out / 'failure.png'))
            raise
        finally:
            if context:
                await context.close()
            self.row['contextClosed'] = True
            self.save()


asset_library=None
ASSET_RUNTIME_ROOT=None

# Ordinary native history uses the established six-decimal authored comparator.
# The area-text constructor explicitly marks its non-editable derived frame
# clip; restoration can give that helper a generated ID/name. Keep its entire
# paint/geometry and all authored object/asset identities in the comparison.
def real_asset_artwork(value):
    def visit(item):
        if isinstance(item,dict):
            return {k:visit(v)for k,v in item.items()if not(item.get('figureStudioAreaTextFrameClip')is True and k in ['figureId','name'])}
        if isinstance(item,list):return[visit(v)for v in item]
        return item
    return asset_library.native.rounded(visit(m.pdf.artwork_without_session_isolation(value)))

def real_asset_equivalent(before,after):return real_asset_artwork(before)==real_asset_artwork(after)
REAL_ASSET_COHORT=[
    ('core.antibody.igg','soft-color'),
    ('neuro.chemical_synapse.bouton_spine','soft-color'),
    ('tissue.epithelial_sheet.lateral','soft-color'),
    ('analysis.heatmap.clustered','soft-color'),
    ('core.mitochondrion.network','style-4'),
    ('rna.lab_equipment.microfluidic_cell_partition','style-4'),
    ('neuro.oligodendrocyte.multiple_sheaths','style-4'),
    ('microbe.model_system.contractile_tailed_bacteriophage','style-4'),
]

def real_asset_records():
    asset_library.RUNTIME_ROOT=ASSET_RUNTIME_ROOT;result=asset_library.catalog_records()
    root=ASSET_RUNTIME_ROOT/'assets/scientific-packs';reg=json.loads((root/'library.json').read_text())
    style=next(s for s in reg['art_styles']if s['id']=='style-4');variants={}
    for name in [style['path'],style['supplement']['path']]:
        manifest=root/name
        for v in json.loads(manifest.read_text())['assets']:
            variants[v['asset_id']]=(v,manifest.parent/v['file'])
    chosen={}
    for asset,style in REAL_ASSET_COHORT:
        record=result[asset]
        if style=='style-4':
            variant,path=variants[asset]
            assert hashlib.sha256(path.read_bytes()).hexdigest()==variant['sha256']
            record={**record,'file':path.relative_to(ASSET_RUNTIME_ROOT).as_posix(),'_svg':path,
                'editable_color_regions':[r for r in variant['editable_color_regions']if not r.get('no_rendered_paint')]}
        chosen[asset]=record
    return chosen

class RealAssets(Interactions):
    async def query(self,text):await asset_library.Case.query(self,text)

    async def number(self,property,value):
        control=self.surface.locator(f'[data-context-property="{property}"]:visible').first
        await control.fill(str(value));await control.press('Enter');await self.settled()

    async def setup(self):
        self.context=await self.browser.new_context(viewport=dict(width=self.width,height=self.height),color_scheme=self.theme)
        await self.context.add_init_script('try{delete window.showSaveFilePicker;delete window.showOpenFilePicker;}catch(_){}')
        self.page=await self.context.new_page();self.page.set_default_timeout(12000)
        self.page.on('pageerror',lambda e:self.row['pageErrors'].append(str(e)))
        self.page.on('dialog',lambda d:d.accept(d.default_value or 'real-assets.fsfigure'))
        await self.page.goto(self.entry_url(),wait_until='domcontentloaded')
        self.surface=await m.base.HELPERS.resolve_figure_surface(self.page);self.frame=self.surface.app_frame
        await asset_library.enter_current_document_async(self.frame,kind='figure',preset='double-column',name='Selection of Library artwork')
        await self.surface.locator('[data-figure-layout-choice="advanced"]').click()
        self.case=self.row;self.case['insertions']=[];self.asset_ids=[];catalog=real_asset_records()
        for index,(asset,style)in enumerate(REAL_ASSET_COHORT):
            self.phase('insert-'+asset)
            await asset_library.show_library_async(self.frame,tab='tools')
            await self.surface.locator('#figureLibraryTab-assets').click()
            await self.surface.locator('#assetCategorySelect').select_option('all')
            await self.surface.locator('#assetSubcategorySelect').select_option('all')
            await self.surface.locator('[data-asset-discovery="all"]').click()
            await self.surface.locator('#assetArtStyleSelect').select_option(style)
            object_id=await asset_library.Case.insert(self,asset,catalog[asset]);self.asset_ids.append(object_id)
            actual=await self.surface.evaluate('id=>FigureStudio.app.getObjectByIdForQa(id).scientificAssetMeta.art_style',object_id)
            self.require(asset+' uses its requested style',actual==style,actual)
            if await self.surface.locator('#figureStyleToggle').get_attribute('aria-pressed')!='true':await self.surface.locator('#figureStyleToggle').click()
            await self.surface.locator('[data-inspector-tab="properties"]').click()
            await self.number('width',1.15 if index%2 else 1.35)
            await self.number('rotation',[-12,0,17,0,11,-9,0,23][index])
            await self.number('x',.9+(index%4)*1.55 if index!=7 else 4.55)
            await self.number('y',1.0+(index//4)*2.05 if index!=7 else 3.28)
            if index in [2,5]:
                await self.surface.locator('[data-context-action="transform-reflect-horizontal"]:visible').first.click();await self.settled()
        await self.surface.locator('#viewport').focus();await self.page.keyboard.press('Escape')
        await self.page.keyboard.press('z');await m.base.HELPERS.drag_scene(self.surface,(0,20),(690,520));await self.page.keyboard.press('v');await self.settled()

    async def client(self,point):
        return await m.base.HELPERS.canvas_scene_point(self.surface,point['x'],point['y'])

    async def blank_canvas(self):
        p=await self.client(dict(x=650,y=450));await self.page.mouse.click(p['x'],p['y']);await self.settled()

    async def paint_point(self,object_id,for_direct=False):
        result=await self.surface.evaluate('''({id,direct})=>{
          const a=FigureStudio.app,root=a.getObjectByIdForQa(id),paths=[],skipped=[];
          let top=root;while(top.group&&top.group.type.toLowerCase()!=='activeselection')top=top.group;
          const stack=root.canvas.getObjects(),higher=stack.slice(stack.indexOf(top)+1).map(o=>({id:o.figureId,b:o.getBoundingRect()}));
          const cover=p=>higher.find(({b})=>p.x>=b.left&&p.x<=b.left+b.width&&p.y>=b.top&&p.y<=b.top+b.height);
          function visit(o){if(o.path)paths.push(o);for(const c of o.getObjects?.()||[])visit(c);}visit(root);
          if(direct){const front=paths.slice().reverse(),filled=front.filter(p=>p.fill&&p.fill!=='none'&&(typeof p.fill!=='string'||new fabric.Color(p.fill).getAlpha()>0));paths.splice(0,paths.length,...filled,...front.filter(p=>!filled.includes(p)));}
          for(const p of paths){const hit=a.getPathPaintedHitProbeForQa(p.figureId);if(hit.status!=='ok'||!hit.insideHit)continue;
            const covered=cover(hit.inside);if(covered){skipped.push({point:hit.inside,frontOwnerId:covered.id});continue;}
            return{rootId:id,leafId:p.figureId,...hit,skippedOccluded:skipped};}
          if(direct)return null;
          const b=root.getBoundingRect();for(let y=.1;y<1;y+=.1)for(let x=.1;x<1;x+=.1){const p={x:b.left+b.width*x,y:b.top+b.height*y};
            if(!cover(p)&&FigureStudioPdfPaintHitTest.hitObject(root,p,{fabric:window.fabric,tolerance:0}))return{rootId:id,inside:p,insideHit:true,skippedOccluded:skipped};}
          return null;
        }''',dict(id=object_id,direct=for_direct))
        self.require('Real asset has a painted native path target',bool(result),object_id)
        self.row.setdefault('paintTargets',{})[object_id]=result;return result

    async def click_owner(self,object_id,shift=False):
        if not shift:await self.blank_canvas()
        p=await self.client((await self.paint_point(object_id))['inside'])
        await self.surface.evaluate('window.mixedInput=[]')
        if shift:await self.page.keyboard.down('Shift')
        try:await self.page.mouse.click(p['x'],p['y'])
        finally:
            if shift:await self.page.keyboard.up('Shift')
        await self.settled();name='owner-click-'+str(len(self.row['states']))
        self.row.setdefault('inputs',{})[name]=await self.surface.evaluate('window.mixedInput')
        return await self.state(name)

    async def add_ordinary_artwork(self):
        await self.surface.locator('#viewport').focus();await self.page.keyboard.press('t')
        await m.base.HELPERS.drag_scene(self.surface,(40,402),(230,443))
        await self.settled()
        editing=await self.surface.evaluate('''()=>{const a=FigureStudio.app,o=a.getObjectByIdForQa(a.getSelectionStateForQa().activeObjectId);return Boolean(o?.isEditing);}''')
        if not editing:await self.surface.locator('[data-context-action="edit-text"]:visible').first.click()
        await self.page.keyboard.press('Control+a');await self.page.keyboard.insert_text('Editable label');await self.page.keyboard.press('Escape')
        await self.surface.locator('.tool-primary[data-tool="rect"]').click()
        await self.surface.locator('.tool-popover [data-tool="rect"]').click()
        await m.base.HELPERS.drag_scene(self.surface,(435,390),(570,442));await self.surface.locator('#viewport').focus();await self.page.keyboard.press('v');await self.settled()
        ordinary=await self.surface.evaluate('''()=>{const a=FigureStudio.app;return a.getCanvasObjectInventoryForQa().objects.map(r=>a.getObjectByIdForQa(r.id)).filter(o=>!o.scientificAssetMeta).map(o=>({id:o.figureId,type:o.type,text:o.text??null}));}''')
        self.require('Public tools add a live editable label and ordinary shape',any(o['text']=='Editable label'for o in ordinary)and any(o['type']=='rect'for o in ordinary),ordinary)
        self.ordinary_ids=[o['id']for o in ordinary]
        await self.surface.evaluate(m.WITNESS)
        await self.surface.evaluate("()=>window.addEventListener('pointerdown',e=>window.mixedInput.push({type:'modifier',shift:e.shiftKey,trusted:e.isTrusted}),true)")

    async def object_marquee(self,name,start,end,shift=False):
        art=await self.full_artwork(name+'-before');before=await self.state(name+'-before')
        await self.surface.evaluate('''()=>{const a=FigureStudio.app,c=a.getObjectByIdForQa(a.getCanvasObjectInventoryForQa().objects[0].id).canvas;
          window.assetNativeSelectionEvents=[];
          if(!window.assetNativeSelectionWitness){window.assetNativeSelectionWitness=true;for(const type of ['mouse:down:before','mouse:down','mouse:up:before','mouse:up'])c.on(type,e=>window.assetNativeSelectionEvents.push({type,target:e.target?.figureId||e.target?.type||null,selected:c.getActiveObjects().map(o=>o.figureId),shift:e.e?.shiftKey,isClick:e.isClick,alreadySelected:e.alreadySelected,selector:c._groupSelector?{...c._groupSelector}:null,tool:a.getDirectSelectionStateForQa().tool}));}
        }''')
        bounds=await self.surface.evaluate('''()=>{const a=FigureStudio.app;return a.getCanvasObjectInventoryForQa().objects.map(r=>({id:r.id,b:a.getObjectByIdForQa(r.id).getBoundingRect()}));}''')
        self.require(name+' starts outside every owner and selected frame',
            not any(r['b']['left']<=start[0]<=r['b']['left']+r['b']['width']and r['b']['top']<=start[1]<=r['b']['top']+r['b']['height']for r in bounds)
            and(not before['selection']['selectedBounds']or not(before['selection']['selectedBounds']['left']<=start[0]<=before['selection']['selectedBounds']['left']+before['selection']['selectedBounds']['width']and before['selection']['selectedBounds']['top']<=start[1]<=before['selection']['selectedBounds']['top']+before['selection']['selectedBounds']['height'])))
        a=await self.client(dict(zip(['x','y'],start)));b=await self.client(dict(zip(['x','y'],end)))
        await self.surface.evaluate('window.mixedInput=[]')
        if shift:await self.page.keyboard.down('Shift')
        try:
            await self.page.mouse.move(a['x'],a['y']);await self.page.mouse.down();await self.page.mouse.move(b['x'],b['y'],steps=6);await self.page.mouse.up()
        finally:
            if shift:await self.page.keyboard.up('Shift')
        await self.settled();after=await self.state(name+'-after');events=await self.surface.evaluate('window.mixedInput')
        self.row.setdefault('nativeSelectionInputs',{})[name]=await self.surface.evaluate('window.assetNativeSelectionEvents')
        self.row.setdefault('inputs',{})[name]=events;down=next(e for e in events if e['type']=='pointerdown');up=next(e for e in reversed(events)if e['type']=='pointerup')
        x0,x1=sorted([down['x'],up['x']]);y0,y1=sorted([down['y'],up['y']]);hits={r['id']for r in bounds if r['b']['left']<=x1 and r['b']['left']+r['b']['width']>=x0 and r['b']['top']<=y1 and r['b']['top']+r['b']['height']>=y0}
        expected=set(before['selection']['selectedIds'])^hits if shift else hits
        self.require(name+' uses trusted public input',down['trusted']and up['trusted'])
        self.require(name+' selects the exact whole owners',set(after['selection']['selectedIds'])==expected,dict(expected=sorted(expected),observed=after['selection']['selectedIds']))
        self.require(name+' preserves all native artwork and history',m.equivalent(art,await self.full_artwork(name+'-after'))and before['history']==after['history'])
        return after

    async def move_owners(self,name,object_id,delta,cancel=False,shift=False):
        before=await self.full_artwork(name+'-before');state=await self.state(name+'-before');inventory=await self.surface.evaluate(m.g.INVENTORY)
        save_before=await self.surface.evaluate('FigureStudio.app.getDocumentSaveState()')
        if name=='cold-group-cancel':self.require('Cold cancellation starts from a clean opened document',save_before['dirty']is False)
        start_matrix=await self.surface.evaluate('id=>FigureStudio.app.getObjectByIdForQa(id).calcTransformMatrix()',object_id)
        selected=state['selection']['selectedIds']
        leaves=await self.surface.evaluate('''ids=>{const a=FigureStudio.app,out=[];function visit(o){const c=o.getObjects?.()||[];if(c.length)c.forEach(visit);else out.push(o.figureId);}ids.forEach(id=>visit(a.getObjectByIdForQa(id)));return out;}''',selected)
        origin=await self.client((await self.paint_point(object_id))['inside']);target=dict(x=origin['x']+delta[0],y=origin['y']+delta[1])
        await self.surface.evaluate('window.mixedInput=[]')
        if shift:await self.page.keyboard.down('Shift')
        await self.page.mouse.move(origin['x'],origin['y']);await self.page.mouse.down();await self.page.mouse.move(target['x'],target['y'],steps=5)
        # First-held original precedes all serialization, inspection or another action.
        subject='The complete mixed selection moves together'if len(selected)>1 else'The selected complete owner moves while neighboring artwork stays fixed'
        await self.capture(name+'-held',subject+' on the first held view, with no rescue click, Fit or test-requested render.')
        events=await self.surface.evaluate('window.mixedInput');down=next(e for e in events if e['type']=='pointerdown');last=next(e for e in reversed(events)if e['type']=='pointermove');delivered=(last['x']-down['x'],last['y']-down['y'])
        self.row.setdefault('inputs',{})[name]=events
        held=await self.state(name+'-held');matrix=await self.surface.evaluate('id=>FigureStudio.app.getObjectByIdForQa(id).calcTransformMatrix()',object_id)
        translated=(matrix[4]-start_matrix[4],matrix[5]-start_matrix[5])
        self.row.setdefault('movement',{})[name]=dict(deliveredSceneDelta=delivered,heldOwnerSceneDelta=translated,snapping=await self.surface.evaluate('FigureStudio.app.getSnappingStateForQa()'))
        self.require(name+' moves in the delivered direction',sum(a*b for a,b in zip(translated,delivered))>0)
        self.require(name+' moves by at least one scene unit',max(abs(value)for value in translated)>=1)
        if shift:self.require(name+' retains the horizontal Shift constraint',abs(translated[1])<1e-6)
        # Ordinary body movement retains the production grid/object snapping
        # policy. Verify every selected leaf against the independently observed
        # owner translation, rather than pretending snapping is raw pointer motion.
        errors=m.rigid(inventory,await self.surface.evaluate(m.g.INVENTORY),set(leaves),translated)
        self.require(name+' retains every selected owner and moves only its native leaves',set(held['selection']['selectedIds'])==set(selected)and not errors,errors[:8])
        if cancel:
            await self.page.keyboard.press('Escape')
            await self.capture(name+'-cancelled-held','Escape restores the entire prior native selection and artwork while the pointer is still held, before mouse release or any rescue action.')
        await self.page.mouse.up()
        if shift:await self.page.keyboard.up('Shift')
        if not cancel:await self.history(state['history']['undoDepth']+1)
        await self.settled();after=await self.full_artwork(name+'-after');finished=await self.state(name+'-after')
        if cancel:
            save_after=await self.surface.evaluate('FigureStudio.app.getDocumentSaveState()')
            self.row['movement'][name].update(documentDirtyBefore=save_before['dirty'],documentDirtyAfter=save_after['dirty'])
            self.require(name+' Escape restores exact artwork, selection, history and dirty state',m.equivalent(before,after)and state['history']==finished['history']and set(finished['selection']['selectedIds'])==set(selected)and save_before['dirty']==save_after['dirty'])
        else:
            matrix=await self.surface.evaluate('id=>FigureStudio.app.getObjectByIdForQa(id).calcTransformMatrix()',object_id)
            final_delta=(matrix[4]-start_matrix[4],matrix[5]-start_matrix[5]);errors=m.rigid(inventory,await self.surface.evaluate(m.g.INVENTORY),set(leaves),final_delta)
            self.require(name+' release preserves every selected native leaf and stationary neighbor',not errors,errors[:8])
        return before,after,state,finished

    async def context_command(self,point,command):
        p=await self.client(point);await self.page.mouse.click(p['x'],p['y'],button='right')
        action=self.surface.locator('#objectContextMenu [data-context-command="'+command+'"]:visible')
        self.require(command+' is a visible supported command',await action.count()==1 and await action.is_enabled())
        await action.click();await self.settled()

    async def nested_point_edit(self):
        await self.click_owner(self.asset_ids[0]);await self.click_owner(self.asset_ids[1],True)
        await self.surface.locator('#viewport').focus();await self.page.keyboard.press('Control+g');await self.settled()
        selected=await self.state('assets-grouped');self.group_id=selected['selection']['activeObjectId']
        self.require('Public Group preserves both component asset roots',await self.surface.evaluate('''({ids,group})=>ids.every(id=>FigureStudio.app.getObjectByIdForQa(id).group?.figureId===group)''',dict(ids=self.asset_ids[:2],group=self.group_id)))
        probe=await self.paint_point(self.asset_ids[0])
        await self.surface.locator('[data-context-action="isolate-group"]:visible').first.click();await self.settled()
        p=await self.client(probe['inside']);await self.page.mouse.click(p['x'],p['y']);await self.settled()
        await self.surface.locator('[data-context-action="enter-isolated-subgroup"]:visible').first.click();await self.settled()
        isolation=await self.surface.evaluate('FigureStudio.app.getGroupIsolationStateForQa()')
        self.row['nestedIsolation']=isolation;self.require('Public group entry preserves the nested component ownership',isolation['depth']==2 and [o['id']for o in isolation['path']]==[self.group_id,self.asset_ids[0]])
        await self.surface.locator('#viewport').focus();await self.page.keyboard.press('a');await self.settled()
        probe=await self.paint_point(self.asset_ids[0],for_direct=True);p=await self.client(probe['inside'])
        await self.page.mouse.click(p['x'],p['y']);await self.settled()
        direct=await self.state('asset-point-body')
        self.require('Direct Selection reaches the intended painted path inside its asset',direct['direct']['objectId']==probe['leafId'],direct['direct']['objectId'])
        endpoint=self.surface.locator(f'.path-node-handle[data-object-id="{probe["leafId"]}"][data-handle-type="endpoint"]').first
        box=await endpoint.bounding_box();self.require('The intended native anchor is visible',bool(box))
        await self.page.mouse.click(box['x']+box['width']/2,box['y']+box['height']/2);await self.settled()
        original=await self.state('asset-anchor-before-toggle');key=handle_key
        target=(probe['leafId'],int(await endpoint.get_attribute('data-command-index')),'endpoint')
        for name,expected in [('remove',{key(h)for h in original['direct']['selectedHandles']}^{target}),('restore',{key(h)for h in original['direct']['selectedHandles']})]:
            box=await endpoint.bounding_box();await self.page.keyboard.down('Shift')
            await self.page.mouse.click(box['x']+box['width']/2,box['y']+box['height']/2);await self.page.keyboard.up('Shift');await self.settled()
            observed=await self.state('asset-anchor-'+name)
            self.require('Public Shift anchor '+name+' retains the intended set',{key(h)for h in observed['direct']['selectedHandles']}==expected)
        await self.surface.locator('[data-inspector-tab="layers"]').click()
        row=self.surface.locator(f'[data-layer-child-id="{probe["leafId"]}"]')
        await row.wait_for(state='visible');self.require('Layers highlights the same selected native path','selected'in(await row.get_attribute('class')or'').split())
        await row.locator(f'[data-layer-child-name="{probe["leafId"]}"]').click();await self.settled()
        layer_selected=await self.state('asset-layer-selected')
        self.require('Public Layers row selects the same native canvas child',layer_selected['selection']['selectedIds']==[probe['leafId']])
        await self.capture('real-asset-anchor-layers','A native anchor is selected inside the antibody asset within a newly grouped composition, and Layers highlights the same child without losing either asset owner.')
        await self.drag_points('asset-anchor-cancel',(3,1),cancel=True)
        before,moved,state,released=await self.drag_points('asset-anchor-edit',(3,1))
        await self.page.keyboard.press('Control+z');await self.history(state['history']['undoDepth']);await self.settled();self.require('Asset point Undo restores the complete composition',m.equivalent(before,await self.full_artwork('asset-point-undo')))
        await self.page.keyboard.press('Control+y');await self.history(released['history']['undoDepth']);await self.settled();self.require('Asset point Redo restores the exact edited composition',m.equivalent(moved,await self.full_artwork('asset-point-redo')))
        await self.surface.locator('[data-isolation-action="exit"]:visible').click();await self.settled()
        await self.surface.locator('#viewport').focus();await self.page.keyboard.press('v');await self.page.keyboard.press('Escape');await self.settled()
        self.require('Public isolation exit preserves the asset and new group ownership',not(await self.surface.evaluate('FigureStudio.app.getGroupIsolationStateForQa()'))['active'])

    async def run(self):
        original_equivalent=m.equivalent;m.equivalent=real_asset_equivalent
        self.context=None;cold=None;self.started=time.perf_counter()
        try:
            self.row['artworkComparisonPolicy']='Established six-decimal native authored precision; omit only generated figureId/name on explicitly marked non-editable figureStudioAreaTextFrameClip helpers. All authored object/asset IDs, text, paths, paint, hierarchy, source and clip geometry remain checked. Raw snapshots retained.'
            await self.setup()
            await self.add_ordinary_artwork()
            await self.capture('real-assets-composition','Eight actual Library drawings in Styles 1 and 4 show varied scientific subjects, size, rotation, reflection and one deliberate overlap, with intact ownership and readable artwork.')
            for object_id in self.asset_ids:
                selected=await self.click_owner(object_id)
                self.require('Ordinary click reaches the intended complete Library owner',selected['selection']['selectedIds']==[object_id],object_id)
            await self.click_owner(self.asset_ids[0]);added=await self.click_owner(self.asset_ids[1],True)
            self.require('Shift click adds another complete asset',set(added['selection']['selectedIds'])==set(self.asset_ids[:2]))
            removed=await self.click_owner(self.asset_ids[0],True)
            self.require('Shift click removes only the intended asset',removed['selection']['selectedIds']==[self.asset_ids[1]])
            last=await self.click_owner(self.asset_ids[1],True)
            self.require('Shift click can remove its last whole asset',last['selection']['selectedCount']==0)
            await self.click_owner(self.asset_ids[0])
            before,moved,state,released=await self.move_owners('asset-shift-drag',self.asset_ids[0],(8,0),shift=True)
            await self.page.keyboard.press('Control+z');await self.history(state['history']['undoDepth']);await self.settled()
            self.require('Shift drag Undo retains the original native composition',m.equivalent(before,await self.full_artwork('asset-shift-drag-undone')))
            all_selected=await self.object_marquee('assets-all',(0,0),(680,470))
            self.require('Object marquee includes all eight assets and ordinary editable objects',set(all_selected['selection']['selectedIds'])==set(self.asset_ids+self.ordinary_ids))
            await self.object_marquee('assets-shift-remove',(5,5),(660,205),True)
            await self.capture('real-assets-subset','A Shift marquee removes a strict subset of complete Library owners while the other assets and editable ordinary objects remain selected.')
            restored=await self.object_marquee('assets-shift-restore',(660,205),(5,5),True)
            self.require('Reverse Shift marquee restores exactly the complete mixed set',set(restored['selection']['selectedIds'])==set(self.asset_ids+self.ordinary_ids))
            await self.move_owners('assets-body-cancel',self.asset_ids[0],(8,3),cancel=True)
            before,moved,state,released=await self.move_owners('assets-body-move',self.asset_ids[0],(8,3))
            await self.page.keyboard.press('Control+z');await self.history(state['history']['undoDepth']);await self.settled();self.require('Mixed owner Undo restores complete artwork',m.equivalent(before,await self.full_artwork('assets-move-undone')))
            await self.page.keyboard.press('Control+y');await self.history(released['history']['undoDepth']);await self.settled();self.require('Mixed owner Redo restores complete artwork',m.equivalent(moved,await self.full_artwork('assets-move-redone')))
            await self.nested_point_edit()
            native=await self.surface.evaluate(asset_library.STATE,self.asset_ids);(self.out/'assets-warm-native.json').write_text(json.dumps(native,indent=2)+'\n')
            path,saved=await self.save_file('assets-first',await self.full_artwork('assets-warm-save'))
            await self.context.close();self.context=None;browser_type=self.browser.browser_type;await self.browser.close();self.row['warmBrowserClosed']=not self.browser.is_connected()
            cold=await browser_type.launch(**self.report['browserLaunchOptions']);await m.base.record_browser_runtime(cold,self.report,'cold');self.context=await self.open_surface(cold,path);self.frame=self.surface.app_frame
            await self.capture('real-assets-cold-open','A genuinely new browser opens the actual file with all eight Library assets, the nested group, editable label, ordinary shape and edited native anchor intact, before further navigation.')
            self.require('Fresh-process Open preserves every saved native object and source',m.equivalent(saved,await self.full_artwork('assets-cold-open')))
            restored_native=await self.surface.evaluate(asset_library.STATE,self.asset_ids);(self.out/'assets-cold-native.json').write_text(json.dumps(restored_native,indent=2)+'\n')
            difference=asset_library.native.native_reconstruction_difference(native,restored_native);self.require('Fresh Open preserves every actual asset primitive and metadata',difference['passed'],difference)
            await self.surface.locator('#viewport').focus();await self.page.keyboard.press('v')
            selected=await self.click_owner(self.group_id);self.require('Cold public click selects the preserved complete nested group',selected['selection']['selectedIds']==[self.group_id])
            await self.surface.evaluate(m.WITNESS)
            await self.move_owners('cold-group-cancel',self.group_id,(4,1),cancel=True)
            await self.move_owners('cold-group-move',self.group_id,(4,1))
            await self.save_file('assets-second',await self.full_artwork('assets-cold-save'))
            self.require('No page errors',not self.row['pageErrors'],self.row['pageErrors']);self.row['status']='passed'
        except BaseException as error:
            self.row['status']='failed';self.row['error']=str(error)
            if hasattr(self,'page')and not self.page.is_closed():await self.page.screenshot(path=str(self.out/'failure.png'))
            raise
        finally:
            if self.context:await self.context.close()
            if cold:await cold.close();self.row['coldBrowserClosed']=not cold.is_connected()
            self.row['contextClosed']=True;self.save()
            m.equivalent=original_equivalent



class GroupConsistency(RealAssets):
    part = 'both'

    def load_group_inputs(self):
        self.part = s.ARGS.group_part
        self.asset_fixture = s.ARGS.asset_fixture
        self.group_pdf_fixture = s.ARGS.group_pdf_fixture
        fixtures = [('assets', self.asset_fixture, 'a7fae56a2d03d873145f74904c1985e50bdc37e877508d90387f21113399678b'), ('pdf', self.group_pdf_fixture, '62768f6ef961dcda91a2315987612e8be53c0f64592e92e6b060fd33a5acc9da')]
        self.row['groupInputs'] = []
        for kind, path, expected in fixtures:
            if self.part not in ['both', kind]:
                continue
            raw = path.read_bytes()
            sha = hashlib.sha256(raw).hexdigest()
            self.row['groupInputs'].append(dict(kind=kind, path=str(path), bytes=len(raw), sha256=sha))
            self.require('Exact retained ' + kind + ' saved input', sha == expected)
        if self.part != 'pdf':
            objects = json.loads(self.asset_fixture.read_text(encoding='utf8'))['project']['fabric']['objects']
            self.asset_group = next((o for o in objects if len(o.get('objects', [])) == 2 and (not o.get('scientificAssetMeta'))))
            self.antibody = next((o for o in self.asset_group['objects'] if o.get('scientificAssetMeta', {}).get('assetId') == 'core.antibody.igg'))
            cohort = []

            def visit(rows):
                for item in rows:
                    meta = item.get('scientificAssetMeta')
                    if meta:
                        cohort.append((meta['assetId'], meta['art_style']))
                    visit(item.get('objects', []))
            visit(objects)
            self.require('Retained composition contains the same eight asset/style owners', sorted(cohort) == sorted(REAL_ASSET_COHORT))

    async def observe(self, name):
        state = await self.state(name)
        extra = await self.surface.evaluate("()=>({isolation:FigureStudio.app.getGroupIsolationStateForQa(),context:FigureStudio.app.getSelectionContextStateForQa(),\n          layerSelected:Array.from(document.querySelectorAll('.layer-child-item.selected,.layer-item.selected')).map(e=>e.dataset.layerChildId||e.dataset.layerId)})")
        self.row.setdefault('groupStates', {})[name] = extra
        self.save()
        return (state, extra)

    def layer(self, object_id):
        return self.surface.locator(f'.layer-item[data-layer-id="{object_id}"],.layer-child-item[data-layer-child-id="{object_id}"]')

    async def prepare(self):
        self.context = await self.open_surface(self.browser, self.asset_fixture)
        await self.capture('saved-asset-open-' + str(len(self.row['captures'])), 'The actual saved eight-asset composition opens with the original nested pair, editable label and ordinary shape intact before navigation.')
        self.baseline = await self.full_artwork('baseline-' + str(len(self.row['captures'])))
        await self.surface.locator('[data-figure-layout-choice="advanced"]').click()
        await self.surface.locator('[data-menu="view"] > .menu-trigger').click()
        await self.surface.locator('[data-menu="view"] [data-command="zoom-out"]').click()
        await self.surface.locator('#viewport').focus()
        await self.page.keyboard.press('v')
        await self.page.keyboard.press('Escape')
        await self.settled()
        await self.surface.evaluate(m.WITNESS)
        selected = await self.click_owner(self.asset_group['figureId'])
        self.require('Canvas targets the complete outer group', selected['selection']['selectedIds'] == [self.asset_group['figureId']])
        await self.surface.locator('[data-context-action="isolate-group"]:visible').first.click()
        await self.settled()
        await self.surface.locator('#viewport').focus()
        await self.page.keyboard.press('v')
        await self.settled()
        selected = await self.click_owner(self.antibody['figureId'])
        self.require('Canvas targets the complete nested asset', selected['selection']['selectedIds'] == [self.antibody['figureId']])
        await self.surface.locator('[data-context-action="enter-isolated-subgroup"]:visible,[data-context-action="isolate-group"]:visible').first.click()
        await self.settled()
        await self.surface.locator('#viewport').focus()
        await self.page.keyboard.press('v')
        await self.settled()
        self.probe = await self.paint_point(self.antibody['figureId'], for_direct=True)
        self.leaf_id = self.probe['leafId']
        point = await self.client(self.probe['inside'])
        await self.page.mouse.click(point['x'], point['y'])
        await self.settled()
        await self.surface.locator('[data-inspector-tab="layers"]').click()
        await self.settled()
        state, extra = await self.observe('nested-target-' + str(len(self.row['captures'])))
        self.require('Canvas, Inspector and Layers target the same native leaf', state['selection']['selectedIds'] == [self.leaf_id] and extra['layerSelected'] == [self.leaf_id] and (extra['context']['selectedIds'] == [self.leaf_id]))
        self.require('Nested entry retains both owners', [p['id'] for p in extra['isolation']['path']] == [self.asset_group['figureId'], self.antibody['figureId']])
        return point

    async def open_surface(self, browser, project=None):
        context = await super().open_surface(browser, project)
        self.page.set_default_timeout(12000)
        self.page.on('pageerror', lambda error: self.row.setdefault('pageErrorDetails', []).append(dict(message=str(error), stack=error.stack, doc=getattr(self, 'doc', ''), lastState=next(reversed(self.row['states']), None))))
        return context

    async def art(self, name):
        raw = await self.surface.evaluate('()=>JSON.stringify(FigureStudio.app.buildProjectJsonForQa().fabric)')
        value = json.loads(raw)
        encoded = json.dumps(value, sort_keys=True, separators=(',', ':')).encode()
        sha = hashlib.sha256(encoded).hexdigest()
        folder = self.out / 'artwork'
        folder.mkdir(exist_ok=True)
        path = folder / (sha + '.json')
        if not path.exists():
            path.write_bytes(encoded)
        self.row.setdefault('artwork', {})[name] = dict(path=str(path), sha256=sha)
        self.save()
        return value

    def action(self, row, command):
        return row.locator(f':scope > .layer-main [data-layer-action="{command}"],:scope > .layer-actions [data-layer-action="{command}"],:scope > .layer-child-identity [data-layer-child-action="{command}"],:scope > .layer-child-actions [data-layer-child-action="{command}"]')

    async def reveal(self, object_id):
        await self.surface.locator('[data-inspector-tab="layers"]').click()
        for ancestor in self.parents:
            if await self.layer(object_id).count():
                break
            row = self.layer(ancestor)
            if not await row.count():
                continue
            button = self.action(row, 'toggle-group')
            if await button.count() and (await button.get_attribute('title') or '').startswith('Show'):
                await button.click()
                await self.settled()
        if not await self.layer(object_id).count():
            name = await self.surface.evaluate('id=>FigureStudio.app.getObjectByIdForQa(id).name', object_id)
            self.require('Unavailable Layers row has a searchable native name', bool(name), object_id)
            await self.surface.locator('#objectSearchInput').fill(name)
            await self.settled()
            self.row.setdefault('layerQueries', {})[object_id] = name
        row = self.layer(object_id)
        await row.wait_for(state='visible')
        return row

    async def select_leaf(self):
        row = await self.reveal(self.leaf_id)
        await row.locator('[data-layer-child-name]').click()
        await self.settled()

    async def toggle_pair(self, point):
        before = await self.art(self.doc + '-toggle-before')
        state = await self.state(self.doc + '-toggle-before')
        await self.surface.evaluate("()=>window.addEventListener('pointerdown',e=>window.mixedInput.push({type:'modifier',shift:e.shiftKey,trusted:e.isTrusted}),true)")
        await self.surface.evaluate('window.mixedInput=[]')
        await self.page.keyboard.down('Shift')
        await self.page.mouse.click(point['x'], point['y'])
        await self.page.keyboard.up('Shift')
        await self.settled()
        await self.capture(self.doc + '-canvas-toggle', 'Shift-click clears the final selected native child while its containing group remains open; complete surrounding artwork stays visible.')
        after, extra = await self.observe(self.doc + '-canvas-toggle')
        self.require(self.doc + ' canvas removes the final nested child', not after['selection']['selectedIds'] and (not extra['layerSelected']) and (not extra['context']['selectedIds']))
        events = await self.surface.evaluate('window.mixedInput')
        self.row.setdefault('trustedToggles', {})[self.doc] = events
        self.require(self.doc + ' original Shift pointerdown was delivered', any((e['type'] == 'pointerdown' and e['trusted'] for e in events)) and any((e['type'] == 'modifier' and e['trusted'] and e['shift'] for e in events)))
        await self.select_leaf()
        row = self.layer(self.leaf_id)
        await self.page.keyboard.down('Shift')
        await row.locator('[data-layer-child-name]').click()
        await self.page.keyboard.up('Shift')
        await self.settled()
        await self.capture(self.doc + '-layers-toggle', 'Layers Shift-click clears the same final native child and matches canvas/Inspector selection without changing the group or editable text.')
        after, extra = await self.observe(self.doc + '-layers-toggle')
        self.require(self.doc + ' Layers removes the same final nested child', not after['selection']['selectedIds'] and (not extra['layerSelected']) and (not extra['context']['selectedIds']))
        self.require(self.doc + ' toggles preserve all artwork and history', self.same(before, await self.art(self.doc + '-toggle-after')) and state['history'] == after['history'])

    async def availability_recovery(self, action, point_edit=False):
        await self.select_leaf()
        if point_edit:
            await self.surface.locator('#viewport').focus()
            await self.page.keyboard.press('a')
            point = await self.client(self.probe['inside'])
            await self.page.mouse.click(point['x'], point['y'])
            await self.settled()
            state = await self.state(self.doc + '-point-before-' + action)
            self.require(self.doc + ' ancestor command begins with genuine path editing', state['direct']['active'] and state['direct']['objectId'] == self.leaf_id)
        before = await self.art(self.doc + '-before-' + action)
        state = await self.state(self.doc + '-before-' + action)
        row = await self.reveal(self.ancestor_id)
        await self.action(row, action).click()
        await self.settled()
        await self.capture(self.doc + '-ancestor-' + action, 'Layers ' + ('locks' if action == 'lock' else 'hides') + ' the selected child’s ancestor. Unavailable native children and point handles have no active selection or editable controls.')
        locked = await self.art(self.doc + '-ancestor-' + action)
        after, extra = await self.observe(self.doc + '-ancestor-' + action)
        self.require(self.doc + ' unavailable descendant has no native/point/Inspector selection', not after['selection']['selectedIds'] and (not after['direct']['active']) and (not extra['context']['selectedIds']))
        self.require(self.doc + ' ancestor availability adds one history step', after['history']['undoDepth'] == state['history']['undoDepth'] + 1)
        self.require(self.doc + ' Layers disables unavailable child targeting', await self.layer(self.leaf_id).locator('[data-layer-child-action="select-on-canvas"]').is_disabled())
        await self.surface.locator('#viewport').focus()
        await self.page.keyboard.press('ArrowRight')
        await self.settled()
        keyed = await self.art(self.doc + '-unavailable-key-' + action)
        key_state = await self.state(self.doc + '-unavailable-key-' + action)
        self.require(self.doc + ' ArrowRight cannot change unavailable artwork or history', locked == keyed and after['history'] == key_state['history'])
        await self.page.keyboard.press('Control+z')
        await self.history(state['history']['undoDepth'])
        await self.settled()
        self.require(self.doc + ' Undo restores the complete pre-availability artwork', self.same(before, await self.art(self.doc + '-availability-undo-' + action)))
        await self.page.keyboard.press('Control+y')
        await self.history(after['history']['undoDepth'])
        await self.settled()
        restored = await self.state(self.doc + '-availability-redo-' + action)
        self.require(self.doc + ' Redo restores availability without reviving its unavailable selection', self.same(locked, await self.art(self.doc + '-availability-redo-' + action)) and (not restored['selection']['selectedIds']) and (not restored['direct']['active']))
        row = await self.reveal(self.ancestor_id)
        await self.action(row, action).click()
        await self.settled()
        self.require(self.doc + ' public unlock/show restores complete artwork', self.same(before, await self.art(self.doc + '-availability-restored-' + action)))
        await self.surface.locator('#viewport').focus()
        await self.page.keyboard.press('v')
        await self.select_leaf()
        selected = await self.state(self.doc + '-recovered-' + action)
        self.require(self.doc + ' recovered native child is selectable again', selected['selection']['selectedIds'] == [self.leaf_id])
        self.require(self.doc + ' availability recovery has no page errors', not self.row['pageErrors'], self.row.get('pageErrorDetails', self.row['pageErrors']))

    async def sibling_pruning(self):
        await self.surface.locator('[data-isolation-action="parent"]:visible').click()
        await self.settled()
        sibling = self.asset_group['objects'][1]['figureId']
        blocked = self.antibody['figureId']
        await self.layer(sibling).locator('[data-layer-child-name]').click()
        await self.settled()
        await self.page.keyboard.down('Shift')
        await self.layer(blocked).locator('[data-layer-child-name]').click()
        await self.page.keyboard.up('Shift')
        await self.settled()
        before = await self.art('assets-siblings-before')
        state = await self.state('assets-siblings-before')
        self.require('Public Layers selects both existing asset siblings', set(state['selection']['selectedIds']) == {sibling, blocked})
        await self.layer(blocked).locator('[data-layer-child-action="lock"]').click()
        await self.settled()
        await self.capture('assets-sibling-retained', 'Locking one selected nested asset removes only that unavailable target; its available synapse sibling remains selected in canvas, Layers and Inspector.')
        after, extra = await self.observe('assets-sibling-retained')
        self.require('Availability pruning retains the same eligible sibling in all surfaces', after['selection']['selectedIds'] == [sibling] and extra['layerSelected'] == [sibling] and (extra['context']['selectedIds'] == [sibling]))
        self.require('Pruning creates no extra selection history', after['history']['undoDepth'] == state['history']['undoDepth'] + 1)
        await self.layer(blocked).locator('[data-layer-child-action="lock"]').click()
        await self.settled()
        self.require('Unlock preserves original sibling geometry, paint, text and hierarchy', self.same(before, await self.art('assets-siblings-unlocked')))
        await self.surface.locator('[data-isolation-action="exit"]:visible').click()
        await self.settled()

    async def prepare_pdf(self):
        self.context = await self.open_surface(self.browser, self.group_pdf_fixture)
        await self.capture('pdf-saved-open', 'The actual saved scientific PDF opens before any Fit or editing, preserving its existing Figure 2 panel and editable labels.')
        await self.surface.locator('[data-figure-layout-choice="advanced"]').click()
        if await self.surface.locator('[data-isolation-action="exit"]:visible').count():
            await self.surface.locator('[data-isolation-action="exit"]:visible').click()
        await self.surface.locator('#viewport').focus()
        await self.page.keyboard.press('v')
        await self.settled()
        inventory = await self.surface.evaluate(m.g.INVENTORY)
        title = next((o for o in inventory['leaves'] if 'Reactome pathways - genes up' in (o['text'] or '')))
        self.leaf_id = title['id']
        self.root_id = json.loads(self.group_pdf_fixture.read_text(encoding='utf8'))['project']['fabric']['objects'][0]['figureId']
        self.ancestor_id = self.root_id
        self.parents = [self.root_id]
        await self.surface.locator('[data-inspector-tab="layers"]').click()
        await self.settled()
        await self.layer(self.root_id).locator('[data-layer-action="select-on-canvas"]').click()
        await self.settled()
        await self.capture('pdf-whole-plot', 'The existing Layers Select on canvas command selects and fits the complete imported scientific plot as one owner; its complete boundary and original Layers/Inspector identity are visible.')
        point = await self.label_point(self.leaf_id)
        await self.page.mouse.click(point['x'], point['y'])
        await self.settled()
        state = await self.state('pdf-whole-plot')
        self.require('Canvas selects the whole imported scientific plot', state['selection']['selectedIds'] == [self.root_id])
        await self.surface.locator('[data-inspector-tab="layers"]').click()
        await self.settled()
        self.require('Layers highlights the same whole imported plot', 'selected' in (await self.layer(self.root_id).get_attribute('class') or '').split())
        await self.surface.locator('[data-inspector-tab="properties"]').click()
        await self.settled()
        actions = self.surface.locator('[data-context-action="isolate-group"]:visible,[data-context-action="enter-isolated-subgroup"]:visible')
        if await actions.count():
            self.row['pdfEntrySurface'] = 'Inspector'
            await actions.first.click()
        else:
            self.row['pdfEntrySurface'] = 'Canvas double-click'
            probe = await self.paint_point(self.root_id, for_direct=True)
            inside = await self.client(probe['inside'])
            await self.page.mouse.dblclick(inside['x'], inside['y'])
        await self.settled()
        isolation = await self.surface.evaluate('FigureStudio.app.getGroupIsolationStateForQa()')
        self.require('Supported public entry retains the original imported plot owner', isolation['active'] and isolation['rootId'] == self.root_id)
        await self.focus_plot(keep_scope=True)
        await self.surface.locator('#viewport').focus()
        await self.page.keyboard.press('v')
        point = await self.label_point(self.leaf_id)
        await self.page.mouse.click(point['x'], point['y'])
        await self.settled()
        state, extra = await self.observe('pdf-native-label')
        self.require('Canvas selects the whole editable PDF label inside its original plot', state['selection']['selectedIds'] == [self.leaf_id] and extra['context']['selectedIds'] == [self.leaf_id])
        await self.reveal(self.leaf_id)
        self.require('Layers highlights the same native PDF label', 'selected' in (await self.layer(self.leaf_id).get_attribute('class') or '').split())
        self.baseline = await self.art('pdf-entry-baseline')
        return point

    async def exit_and_move(self):
        name = self.doc + '-' + self.stage
        before = await self.art(name + '-before-exit')
        history = await self.state(name + '-before-exit')
        if await self.surface.locator('[data-isolation-action="exit"]:visible').count():
            await self.surface.locator('[data-isolation-action="exit"]:visible').click()
            await self.settled()
        await self.surface.locator('#viewport').focus()
        await self.page.keyboard.press('v')
        await self.settled()
        state = await self.state(name + '-exited')
        self.require(name + ' exit preserves every pose/owner and selects the original whole group', self.same(before, await self.art(name + '-exited')) and state['history'] == history['history'] and (state['selection']['selectedIds'] == [self.root_id]))
        if self.doc == 'assets':
            await self.move_owners(name + '-cancel', self.root_id, (20, 10), cancel=True)
            before, moved, state, released = await self.move_owners(name + '-move', self.root_id, (20, 10))
        else:
            await self.focus_plot()
            await self.marquee(name + '-continuation-seed')
            await self.drag_points(name + '-cancel', (2, 0), cancel=True)
            before, moved, state, released = await self.drag_points(name + '-move', (2, 0))
        await self.page.keyboard.press('Control+z')
        await self.history(state['history']['undoDepth'])
        await self.settled()
        self.require(name + ' movement Undo restores complete artwork', self.same(before, await self.art(name + '-move-undone')))
        await self.page.keyboard.press('Control+y')
        await self.history(released['history']['undoDepth'])
        await self.settled()
        self.require(name + ' movement Redo restores complete artwork', self.same(moved, await self.art(name + '-move-redone')))

    async def roundtrip(self):
        path, saved = await self.save_file(self.doc + '-first', await self.art(self.doc + '-warm-save'))
        await self.context.close()
        self.context = None
        kind = self.browser.browser_type
        await self.browser.close()
        self.row.setdefault('browserClosures', {})[self.doc + '-warm'] = not self.browser.is_connected()
        self.browser = await kind.launch(**self.report['browserLaunchOptions'])
        await m.base.record_browser_runtime(self.browser, self.report, self.doc + '-cold')
        self.context = await self.open_surface(self.browser, path)
        await self.capture(self.doc + '-cold-open', 'A genuinely new browser opens the actual saved ' + ('eight-asset composition' if self.doc == 'assets' else 'scientific PDF') + ' before navigation, preserving native groups, poses and editable labels.')
        cold = await self.art(self.doc + '-cold-open')
        self.require(self.doc + ' fresh-process Open preserves actual saved artwork', self.same(saved, cold))
        await self.surface.evaluate(m.WITNESS)
        await self.surface.locator('[data-figure-layout-choice="advanced"]').click()
        await self.surface.locator('[data-inspector-tab="layers"]').click()
        await self.settled()
        await self.select_leaf()
        state, extra = await self.observe(self.doc + '-cold-child')
        self.require(self.doc + ' cold Layers selects the same child without reparenting', state['selection']['selectedIds'] == [self.leaf_id] and extra['isolation']['path'][0]['id'] == self.root_id)
        self.stage = 'cold'
        await self.exit_and_move()
        await self.save_file(self.doc + '-second', await self.art(self.doc + '-cold-save'))
        await self.context.close()
        self.context = None

    async def run(self):
        self.started = time.perf_counter()
        self.context = None
        original = m.equivalent
        try:
            self.load_group_inputs()
            self.row['plannedParts'] = ['assets', 'pdf'] if self.part == 'both' else [self.part]
            if self.part != 'pdf':
                self.doc = 'assets'
                self.stage = 'warm'
                self.same = real_asset_equivalent
                m.equivalent = self.same
                self.parents = [self.asset_group['figureId'], self.antibody['figureId']]
                self.root_id = self.asset_group['figureId']
                self.ancestor_id = self.antibody['figureId']
                point = await self.prepare()
                await self.toggle_pair(point)
                await self.availability_recovery('lock', point_edit=True)
                await self.availability_recovery('visible')
                await self.sibling_pruning()
                await self.exit_and_move()
                await self.roundtrip()
            if self.part != 'assets':
                self.doc = 'pdf'
                self.stage = 'warm'
                self.same = original
                m.equivalent = original
                point = await self.prepare_pdf()
                await self.toggle_pair(point)
                await self.availability_recovery('lock')
                await self.availability_recovery('visible')
                await self.exit_and_move()
                await self.roundtrip()
            self.require('No browser page errors', not self.row['pageErrors'], self.row['pageErrors'])
            self.require('All declared Groups/Layers checks pass', all((x['passed'] for x in self.row['checks'])))
            self.row['status'] = 'passed'
        except BaseException as error:
            self.row['status'] = 'failed'
            self.row['error'] = str(error)
            if hasattr(self, 'page') and (not self.page.is_closed()):
                await self.page.screenshot(path=str(self.out / 'failure.png'))
            raise
        finally:
            if self.context:
                await self.context.close()
            await self.browser.close()
            self.row['lastBrowserClosed'] = not self.browser.is_connected()
            self.row['contextClosed'] = True
            self.save()
            m.equivalent = original


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--root', type=Path, required=True)
    p.add_argument('--output-dir', type=Path, required=True)
    p.add_argument('--expected-app-sha256', required=True)
    p.add_argument('--viewport', default='1440x1000')
    p.add_argument('--theme', choices=['light', 'dark'], default='light')
    modes=p.add_mutually_exclusive_group()
    modes.add_argument('--group-layers', action='store_true', help='Run saved real-asset/PDF Groups and Layers consistency')
    modes.add_argument('--ordinary-subset', action='store_true', help='Run only the ordinary mixed Shift-marquee subset case')
    modes.add_argument('--subset-marquee', action='store_true', help='Run the ordinary/PDF mixed Shift-marquee subset and saved continuation case')
    modes.add_argument('--real-assets', action='store_true', help='Run eight actual Library assets through public selection, grouping, point editing and fresh-file continuation')
    p.add_argument('--group-part', choices=['both','assets','pdf'], default='both', help='Finite Groups/Layers portion; default runs both')
    p.add_argument('--asset-fixture', type=Path, default=ROOT/'qa_artifacts/selection-reliability-20261105/assets-accepted/1440x1000-light/1440x1000-light/assets-second.fsfigure')
    p.add_argument('--group-pdf-fixture', type=Path, default=ROOT/'qa_artifacts/selection-reliability-20261105/regression-accepted/1280x800-light/1280x800-light/subset-second.fsfigure')
    p.add_argument('--asset-root', type=Path, help='Read-only catalog root when the App is served through an overlay')
    p.add_argument('--url', default='', help='Use a separately owned direct editor URL')
    p.add_argument('--fixture', type=Path, default=m.g.SOURCE)
    args = p.parse_args()
    args.smoke = True
    args.browser_channel = 'chromium'
    s.ARGS = args
    s.label.ARGS = args
    m.ARGS = args
    global asset_library, ASSET_RUNTIME_ROOT
    if args.real_assets or args.group_layers:
        ASSET_RUNTIME_ROOT=(args.asset_root or args.root).resolve()
        if args.real_assets and not (ASSET_RUNTIME_ROOT/'assets/scientific-packs/library.json').is_file():
            p.error('Asset root must contain the actual scientific Library catalog')
        spec=importlib.util.spec_from_file_location('selection_real_library',ROOT/'scripts/check-library-drawings-browser.py')
        asset_library=importlib.util.module_from_spec(spec);spec.loader.exec_module(asset_library)
        m.base.Case=GroupConsistency if args.group_layers else RealAssets
    else:
        m.base.Case = Interactions
    asyncio.run(m.base.run(args))


if __name__ == '__main__':
    main()
