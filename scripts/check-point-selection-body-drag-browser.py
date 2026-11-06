#!/usr/bin/env python3
"""Unattended Point Selection body-drag checks on ordinary native SVG artwork."""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import subprocess
import sys
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('point_selection_helpers', ROOT / 'scripts/check-direct-selection-draw-browser.py')
HELPERS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(HELPERS)
SNAPSHOT = '''ids => ({direct:FigureStudio.app.getDirectSelectionStateForQa(),history:FigureStudio.app.getHistoryStateForQa(),objects:ids.map(id=>{const o=FigureStudio.app.getObjectByIdForQa(id);return {id:o.figureId,parent:o.group?.figureId||null,path:JSON.parse(JSON.stringify(o.path||[])),matrix:o.calcTransformMatrix(),offset:o.pathOffset||{x:0,y:0},paint:{fill:o.fill,stroke:o.stroke},bounds:o.getBoundingRect()}})})'''


def points(record):
    result = {}
    a, b, c, d, e, f = record['matrix']
    for index, command in enumerate(record['path']):
        for operand in range(1, len(command) - 1, 2):
            x, y = command[operand] - record['offset']['x'], command[operand + 1] - record['offset']['y']
            result[(index, operand)] = (a*x+c*y+e, b*x+d*y+f)
    return result


def browser_launch_options(channel):
    options = {'headless': True}
    if channel == 'chromium':
        options['channel'] = 'chromium'
    return options


async def record_browser_runtime(browser, report, phase):
    runtime = {'phase': phase, 'browserVersion': browser.version,
               'headless': True, 'launchOptions': dict(report['browserLaunchOptions'])}
    session = None
    try:
        session = await browser.new_browser_cdp_session()
        info = await session.send('SystemInfo.getInfo')
        runtime['graphics'] = info.get('gpu')
    except Exception as error:
        runtime['graphicsUnavailable'] = str(error)
    finally:
        if session:
            await session.detach()
    report.setdefault('browserRuntimes', []).append(runtime)


def deltas(before, after):
    result = []
    for first, second in zip(before['objects'], after['objects']):
        if first['id'] != second['id'] or first['parent'] != second['parent'] or first['paint'] != second['paint']:
            raise AssertionError('Object identity, document parent or paint changed')
        left, right = points(first), points(second)
        if left.keys() != right.keys():
            raise AssertionError('Path topology changed')
        result.append({key: (right[key][0]-value[0], right[key][1]-value[1]) for key, value in left.items()})
    return result


def close(a, b, tolerance=.01):
    return abs(a[0]-b[0]) <= tolerance and abs(a[1]-b[1]) <= tolerance


class Case:
    def __init__(self, browser, base, out, width, height, theme, report):
        self.browser, self.base, self.out = browser, base, out
        self.width, self.height, self.theme, self.report = width, height, theme, report
        self.row = {'name': f'{width}x{height}-{theme}', 'checks': [], 'states': {}, 'captures': [], 'pageErrors': []}
        self.fixture_ids = []
        report['cases'].append(self.row)
        self.out = out / self.row['name']
        self.out.mkdir(parents=True, exist_ok=True)

    def check(self, name, condition, detail=None):
        self.row['checks'].append({'name': name, 'passed': bool(condition), 'detail': detail})
        if not condition:
            raise AssertionError(name)

    async def snapshot(self, name, ids):
        row = await self.surface.evaluate(SNAPSHOT, ids)
        self.row['states'][name] = row
        return row

    async def capture(self, name, intent):
        self.row['captures'].append({'file': name+'.png', 'intent': intent})
        self.save()
        await self.surface.screenshot(path=str(self.out / (name+'.png')))

    def save(self):
        (self.out / 'case.json').write_text(json.dumps(self.row, indent=2), encoding='utf-8')

    async def history(self, expected):
        await self.surface.app_frame.wait_for_function('n=>FigureStudio.app.getHistoryStateForQa().undoDepth===n', arg=expected)
        await self.surface.evaluate('()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))')

    async def all_shapes(self):
        await self.clean_fixture()
        fixture = await self.surface.evaluate('()=>FigureStudio.app.createDirectSelectionShapeScenarioForQa()')
        ids = fixture['objectIds']
        self.fixture_ids = ids
        await self.surface.wait_for_visual_stability()
        await HELPERS.begin_marquee_scene(self.surface, (90, 90), (650, 310))
        await self.page.mouse.up()
        return ids

    async def clean_fixture(self):
        # QA role flags are intentionally absent from saved authoring records;
        # retain our exact IDs across Undo/Redo instead of relying on those flags.
        for object_id in self.fixture_ids:
            await self.surface.evaluate('id=>FigureStudio.app.deleteObjectForQa({objectId:id})',object_id)
        self.fixture_ids=[]

    async def click_handle(self, object_id, index=0, shift=False):
        locator = self.surface.locator(f'.path-node-handle[data-object-id="{object_id}"][data-handle-type="endpoint"]').nth(index)
        box=await locator.bounding_box()
        if not box: raise AssertionError('Expected visible native anchor')
        if shift: await self.page.keyboard.down('Shift')
        await self.page.mouse.click(box['x']+box['width']/2,box['y']+box['height']/2)
        if shift: await self.page.keyboard.up('Shift')

    async def run(self):
        context = await self.browser.new_context(viewport={'width':self.width,'height':self.height}, color_scheme=self.theme)
        self.page = await context.new_page()
        self.page.on('pageerror', lambda error:self.row['pageErrors'].append(str(error)))
        self.page.set_default_timeout(15000)
        try:
            theme = 'dark-graphite' if self.theme == 'dark' else 'light'
            url = urlsplit(self.base)
            query = dict(parse_qsl(url.query)); query.update(bsd_theme=theme, bsd_effective_theme=theme)
            await self.page.goto(urlunsplit((url.scheme,url.netloc,url.path,urlencode(query),url.fragment)), wait_until='domcontentloaded')
            self.surface = await HELPERS.resolve_figure_surface(self.page)
            await HELPERS.dismiss_first_run_surface(self.surface)
            self.check('Requested desktop theme is applied', await self.surface.evaluate('document.documentElement.dataset.theme') == theme)

            ids = await self.all_shapes()
            before = await self.snapshot('whole-before', ids)
            self.check('Marquee selects anchors and controls across two paths', before['direct']['selectedHandleCount'] == 16)
            await HELPERS.drag_scene(self.surface, (220,185), (260,215))
            await self.history(before['history']['undoDepth']+1)
            after = await self.snapshot('whole-after', ids)
            movements = deltas(before, after)
            delta = next(iter(movements[0].values()))
            self.check('Body drag rigidly translates both complete paths, including explicit closing endpoint', math.hypot(*delta)>10 and all(close(value,delta) for row in movements for value in row.values()), str(movements))
            self.check('Body drag retains entire multi-path point selection', after['direct']['selectedHandleCount']==16 and after['direct']['objectCount']==2)
            await self.capture('whole-selection-moved', 'Both complete native paths remain selected after dragging the rectangle body; the ellipse has moved by the same distance without changing shape.')
            await self.surface.evaluate('FigureStudio.app.undoForQa()')
            undone = await self.snapshot('whole-undo', ids)
            self.check('One Undo restores every path coordinate and parent', all(close(v,(0,0)) for row in deltas(before,undone) for v in row.values()))
            await self.surface.evaluate('FigureStudio.app.redoForQa()')
            redone = await self.snapshot('whole-redo', ids)
            self.check('One Redo restores complete moved geometry', all(close(v,(0,0)) for row in deltas(after,redone) for v in row.values()))
            body=(220+delta[0],185+delta[1])
            client=await HELPERS.canvas_scene_point(self.surface,*body)
            await self.page.mouse.click(client['x'],client['y'])
            noop=await self.snapshot('body-click',ids)
            self.check('Body click preserves selection and adds no Undo', noop['history']==redone['history'] and noop['direct']['selectedHandleCount']==16 and all(close(v,(0,0)) for row in deltas(redone,noop) for v in row.values()))
            await HELPERS.begin_marquee_scene(self.surface, body, (body[0]+30,body[1]+21))
            await self.page.keyboard.press('Escape'); await self.page.mouse.up()
            canceled=await self.snapshot('body-escape',ids)
            self.check('Escape rolls back body drag without history', canceled['history']==noop['history'] and all(close(v,(0,0)) for row in deltas(noop,canceled) for v in row.values()))
            await HELPERS.begin_marquee_scene(self.surface, body, (body[0]+25,body[1]-22))
            await self.page.evaluate("window.dispatchEvent(new PointerEvent('pointercancel',{pointerId:1,bubbles:true}))")
            await self.page.mouse.up()
            pointer_canceled=await self.snapshot('body-pointercancel',ids)
            self.check('Pointer cancellation rolls back body drag without history', pointer_canceled['history']==noop['history'] and all(close(v,(0,0)) for row in deltas(noop,pointer_canceled) for v in row.values()))

            ids=await self.all_shapes()
            await self.click_handle(ids[0]); await self.click_handle(ids[1],shift=True)
            partial_before=await self.snapshot('partial-before',ids)
            self.check('Partial selection spans two path members', partial_before['direct']['selectedHandleCount']==2)
            await HELPERS.drag_scene(self.surface,(220,185),(252,204))
            await self.history(partial_before['history']['undoDepth']+1)
            partial_after=await self.snapshot('partial-after',ids)
            changed=deltas(partial_before,partial_after)
            selected_before=partial_before['direct']['selectedHandles']; selected_after=partial_after['direct']['selectedHandles']
            delta=(selected_after[0]['x']-selected_before[0]['x'],selected_after[0]['y']-selected_before[0]['y'])
            self.check('Dragging a member other than primary preserves the two selected nodes', partial_after['direct']['selectedHandleCount']==2 and math.hypot(*delta)>10 and all(close((a['x']-b['x'],a['y']-b['y']),delta) for a,b in zip(selected_after,selected_before)))
            self.check('Partial-node body drag carries attached tangents and explicit SVG seam only', all(close(v,(0,0)) or close(v,delta) for row in changed for v in row.values()) and sum(not close(v,(0,0)) for row in changed for v in row.values())==5, str(changed))
            await self.capture('partial-selection-moved', 'Only the two selected nodes and their attached curve controls have moved; the other visible anchors remain in their original positions.')
            await self.surface.evaluate('FigureStudio.app.undoForQa()')
            partial_undo=await self.snapshot('partial-undo',ids)
            self.check('One Undo restores partial-node and tangent movement', all(close(v,(0,0)) for row in deltas(partial_before,partial_undo) for v in row.values()))

            await self.clean_fixture()
            fixture=await self.surface.evaluate('()=>FigureStudio.app.createDirectSelectionParityScenarioForQa({history:true})')
            ids=fixture['objectIds']
            self.fixture_ids=ids
            empty_before=await self.snapshot('empty-before',ids)
            await HELPERS.begin_marquee_scene(self.surface,(352,116),(382,132))
            visible=await self.surface.evaluate('FigureStudio.app.getDirectSelectionStateForQa()')
            await self.page.mouse.up()
            empty_after=await self.snapshot('empty-after',ids)
            self.check('Empty space between selected paths remains a point marquee', visible['marqueeVisible'] and empty_before['history']==empty_after['history'] and all(close(v,(0,0)) for row in deltas(empty_before,empty_after) for v in row.values()))

            # Full endpoint marquee excludes the upper control on this native
            # closed Bezier path. The unselected tangent must still translate.
            await self.clean_fixture()
            fixture=await self.surface.evaluate('()=>FigureStudio.app.createBezierNodeEditingScenarioForQa()')
            self.fixture_ids=await self.surface.evaluate('ids=>ids.filter(id=>!FigureStudio.app.getObjectByIdForQa(id)?.group)',list(fixture['objectIds'].values()))
            closed=fixture['objectIds']['closed']
            for object_id in self.fixture_ids:
                if object_id!=closed: await self.surface.evaluate('id=>FigureStudio.app.deleteObjectForQa({objectId:id})',object_id)
            self.fixture_ids=[closed]
            await self.surface.evaluate('id=>{FigureStudio.app.selectObjectsByIdsForQa([id]);FigureStudio.app.activateToolForQa("directSelect")}',closed)
            await self.surface.wait_for_visual_stability()
            state=await self.surface.evaluate('FigureStudio.app.getDirectSelectionStateForQa()')
            endpoints=[v for v in state['handles'] if v['objectId']==closed and v['handleType']=='endpoint']
            bounds=(min(v['x'] for v in endpoints)-25,min(v['y'] for v in endpoints)-25,max(v['x'] for v in endpoints)+25,max(v['y'] for v in endpoints)+25)
            await HELPERS.begin_marquee_scene(self.surface,bounds[:2],bounds[2:]); await self.page.mouse.up()
            hidden_before=await self.snapshot('hidden-control-before',[closed])
            s=hidden_before['direct']
            self.check('Endpoint marquee leaves at least one tangent outside selection', sum(v['handleType']=='endpoint' for v in s['selectedHandles'])==len(endpoints) and s['selectedHandleCount']<s['handleCount'])
            body=(sum(v['x'] for v in endpoints)/len(endpoints),sum(v['y'] for v in endpoints)/len(endpoints))
            await HELPERS.drag_scene(self.surface,body,(body[0]+26,body[1]+18))
            await self.history(hidden_before['history']['undoDepth']+1)
            hidden_after=await self.snapshot('hidden-control-after',[closed])
            values=list(deltas(hidden_before,hidden_after)[0].values()); delta=values[0]
            self.check('All-endpoint body movement carries unselected off-marquee controls without distortion', math.hypot(*delta)>10 and all(close(v,delta) for v in values))

            ids=await self.all_shapes()
            await self.surface.evaluate('ids=>{FigureStudio.app.clearSelectionForQa();const a=FigureStudio.app.getObjectByIdForQa(ids[0]),b=FigureStudio.app.getObjectByIdForQa(ids[1]);const p=a.getCenterPoint();b.set({left:p.x,top:p.y});b.setCoords();FigureStudio.app.selectObjectsByIdsForQa([ids[0]]);FigureStudio.app.activateToolForQa("directSelect")}',ids)
            for i in range(4): await self.click_handle(ids[0],i,shift=i>0)
            front_before=await self.snapshot('frontmost-before',ids)
            center=front_before['objects'][0]['matrix'][4:]
            await HELPERS.drag_scene(self.surface,center,(center[0]+28,center[1]+18))
            await self.history(front_before['history']['undoDepth']+1)
            front_after=await self.snapshot('frontmost-after',ids)
            movement=deltas(front_before,front_after)
            self.check('Unselected frontmost artwork keeps normal hit precedence', all(close(v,(0,0)) for v in movement[0].values()) and any(math.hypot(*v)>10 for v in movement[1].values()))

            await self.clean_fixture()
            await self.surface.evaluate('FigureStudio.app.activateToolForQa("select")')
            await self.surface.locator('#assetSearchInput').fill('Generic Eukaryotic Cell')
            card=self.surface.locator('#assetGrid [data-asset-id="core.cell.generic"]')
            await card.locator('img').evaluate('img=>img.decode()')
            await card.click()
            await self.surface.app_frame.wait_for_function('FigureStudio.app.getObjectByIdForQa(FigureStudio.app.getSelectionStateForQa().activeObjectId)?.scientificAssetMeta?.assetId==="core.cell.generic"')
            root=await self.surface.evaluate('FigureStudio.app.getSelectionStateForQa().activeObjectId')
            await self.surface.evaluate('id=>{const o=FigureStudio.app.getObjectByIdForQa(id);o.scaleToWidth(220);o.set({originX:"center",originY:"center",left:320,top:235});o.setCoords();o.canvas.renderAll();FigureStudio.app.activateToolForQa("directSelect")}',root)
            await self.surface.wait_for_visual_stability()
            body=(260,240)
            client=await HELPERS.canvas_scene_point(self.surface,*body)
            await self.page.mouse.click(client['x'],client['y'])
            isolated=await self.surface.evaluate('FigureStudio.app.getGroupIsolationStateForQa()')
            self.row['libraryEntry']={'isolation':isolated,'direct':await self.surface.evaluate('FigureStudio.app.getDirectSelectionStateForQa()'),'click':{'scene':body,'client':client}}
            self.check('Point click opens a real Library cell path inside its original group', isolated['active'] and isolated['rootId']==root)
            box=await self.surface.evaluate('id=>FigureStudio.app.getObjectByIdForQa(id).getBoundingRect()',root)
            await HELPERS.begin_marquee_scene(self.surface,(box['left']-25,box['top']-25),(box['left']+box['width']+25,box['top']+box['height']+25))
            await self.page.mouse.up()
            await self.surface.wait_for_visual_stability()
            ids=await self.surface.evaluate('FigureStudio.app.getDirectSelectionStateForQa().objectIds')
            isolated_before=await self.snapshot('library-isolated-before',ids)
            self.check('Marquee selects native paths without releasing the Library group', len(ids)>=2 and all(v['parent']==root for v in isolated_before['objects']))
            # The public and expanded Library drawings have different anchor
            # densities. Observe a finite interior grid before the gesture;
            # never retry a drag or force a click through a visible point.
            body_candidates=[(x,y) for y in [190,210,230,250,270] for x in [260,285,310,335,360]]
            body_targets=await self.surface.evaluate('''({root,points})=>{
              const owner=FigureStudio.app.getObjectByIdForQa(root),lower=owner.canvas.lowerCanvasEl;
              const box=lower.getBoundingClientRect(),ctx=lower.getContext('2d',{willReadFrequently:true});
              return points.map(([x,y])=>{
                const client=FigureStudio.app.sceneToClientForQa({x,y});
                const element=document.elementFromPoint(client.x,client.y);
                const pixelPoint={x:Math.floor((client.x-box.left)*lower.width/box.width),y:Math.floor((client.y-box.top)*lower.height/box.height)};
                const inBounds=pixelPoint.x>=0&&pixelPoint.y>=0&&pixelPoint.x<lower.width&&pixelPoint.y<lower.height;
                const pixel=inBounds?[...ctx.getImageData(pixelPoint.x,pixelPoint.y,1,1).data]:null;
                const painted=pixel&&pixel[3]>100&&(255-pixel[0]+255-pixel[1]+255-pixel[2])>32;
                const canvasTarget=element===owner.canvas.upperCanvasEl;
                return {scene:[x,y],client,target:{tag:element?.tagName,classes:element?.className},pixelPoint,pixel,painted:Boolean(painted),canvasTarget,eligible:Boolean(painted&&canvasTarget)};
              });
            }''',{'root':root,'points':body_candidates})
            body_target=next((row for row in body_targets if row['eligible']),None)
            self.row['libraryBodyTarget']={'policy':'First eligible point in a predeclared 5 by 5 scene grid, chosen before pointerdown; exact upper-canvas hit and a nonwhite rendered artwork pixel are both required.','candidates':body_targets,'chosen':body_target}
            self.check('Library body gesture starts on painted canvas rather than an anchor button', body_target is not None,self.row['libraryBodyTarget'])
            body=body_target['scene']
            await HELPERS.drag_scene(self.surface,body,(body[0]+22,body[1]+15))
            await self.history(isolated_before['history']['undoDepth']+1)
            isolated_after=await self.snapshot('library-isolated-after',ids)
            movement=deltas(isolated_before,isolated_after);delta=next(iter(movement[0].values()))
            self.check('Library path bodies move all selected native parts with stable parent IDs', math.hypot(*delta)>10 and all(close(v,delta) for row in movement for v in row.values()))
            self.check('Library body drag retains the selected point set and isolation root', isolated_after['direct']['selectedHandleCount']==isolated_before['direct']['selectedHandleCount'] and (await self.surface.evaluate('FigureStudio.app.getGroupIsolationStateForQa().rootId'))==root)
            await self.capture('library-parts-moved', 'The selected cytoplasm and nucleus paths have moved together inside the original cell group; group ownership and the selected anchors remain visible.')
            await self.surface.evaluate('FigureStudio.app.undoForQa()')
            isolated_undo=await self.snapshot('library-isolated-undo',ids)
            self.check('One Undo restores grouped Library parts exactly', all(close(v,(0,0)) for row in deltas(isolated_before,isolated_undo) for v in row.values()))
            self.check('No browser page error', not self.row['pageErrors'],self.row['pageErrors'])
            self.row['status']='passed'
        except BaseException as error:
            self.row['status']='failed'; self.row['error']=str(error)
            try: await self.page.screenshot(path=str(self.out/'failure.png'))
            except Exception: pass
            raise
        finally:
            await context.close(); self.row['contextClosed']=True; self.save()


async def run(args):
    args.output_dir=args.output_dir.resolve()
    args.output_dir.relative_to((ROOT/'qa_artifacts').resolve())
    args.output_dir.mkdir(parents=True,exist_ok=False)
    server=None; port=0
    report={'schema':'figureStudio.pointSelectionBodyDragBrowser.v1','cases':[],'sourceSHA256':hashlib.sha256((args.root/'app/app.js').read_bytes()).hexdigest(),'runnerSHA256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    report['browserChannel'] = getattr(args, 'browser_channel', 'headless-shell')
    report['browserLaunchOptions'] = browser_launch_options(report['browserChannel'])
    report['browserRuntimes'] = []
    report['expectedAppSHA256']=args.expected_app_sha256 or None
    try:
        if args.expected_app_sha256 and report['sourceSHA256']!=args.expected_app_sha256.lower():
            raise AssertionError('Exact target app SHA256 differs from expected candidate')
        url=args.url
        if not url:
            port=HELPERS.free_port()
            server=subprocess.Popen([sys.executable,str(ROOT/'scripts/figure-studio-server.py'),'--root',str(args.root),'--bind','127.0.0.1','--port',str(port)],cwd=ROOT,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            await HELPERS.wait_for_server(port)
            url=f'http://127.0.0.1:{port}/app/index.html'
        report['url']=url
        async with async_playwright() as p:
            browser=await p.chromium.launch(**report['browserLaunchOptions'])
            try:
                await record_browser_runtime(browser, report, 'warm')
                for width,height in ([(1440,1000)] if args.smoke else [(1280,800),(1440,1000),(1920,1080)]):
                    for theme in (['light'] if args.smoke else ['light','dark']):
                        case=Case(browser,url,args.output_dir,width,height,theme,report)
                        await case.run()
                        print(case.row['name']+': passed '+str(len(case.row['checks']))+' checks',flush=True)
            finally:
                await browser.close(); report['browserClosed']=not browser.is_connected()
        report['status']='passed'
    except BaseException as error:
        report['status']='failed';report['error']=str(error);raise
    finally:
        if server:
            server.terminate();server.wait(timeout=10)
            report['serverClosed']=await HELPERS.wait_for_port_closed(port)
        report['passedChecks']=sum(v['passed'] for c in report['cases'] for v in c['checks'])
        report['totalChecks']=sum(len(c['checks']) for c in report['cases'])
        report['sourceAfterSHA256']=hashlib.sha256((args.root/'app/app.js').read_bytes()).hexdigest()
        report['sourceUnchanged']=report['sourceSHA256']==report['sourceAfterSHA256']
        if not report['sourceUnchanged']:
            report['status']='failed';report['error']='Exact target app changed during unattended QA'
        (args.output_dir/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
        if not report['sourceUnchanged']:
            raise AssertionError(report['error'])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=ROOT,help='Exact editor runtime root to serve; does not mutate it')
    parser.add_argument('--url',default='',help='Use a separately owned direct editor URL')
    parser.add_argument('--expected-app-sha256',default='',help='Refuse to test any other exact runtime app; always verify it remains unchanged')
    parser.add_argument('--output-dir',type=Path,default=ROOT/'qa_artifacts/direct-selection-drag-20261015/final')
    parser.add_argument('--smoke',action='store_true')
    asyncio.run(run(parser.parse_args()))


if __name__=='__main__':main()
