"""One-shot trusted center picking on the exact retained transformed Library witness."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import time

AREA = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('crowded_topology', AREA / 'topology.py')
t = importlib.util.module_from_spec(spec)
spec.loader.exec_module(t)
q, probe, i, m, ROOT = t.q, t.probe, t.i, t.m, t.ROOT
FIXTURE = ROOT / 'qa_artifacts/topology-20261105/runs/reproduce-02/1440x1000-light/topology-first.fsfigure'
FIXTURE_SHA = '61d2a3704a3837d065efd345b97faee6576477fdf7e5c98eff9af62c720f411d'


class Crowded(t.Topology):
    async def focus_crowded(self):
        await self.surface.locator('#viewport').focus()
        await self.page.keyboard.press('v')
        await self.page.keyboard.press('Escape')
        await self.focus_asset(t.JUNCTION)

    def load_targets(self):
        raw = probe.ARGS.fixture.read_bytes()
        self.require('Exact retained actual topology witness bytes', hashlib.sha256(raw).hexdigest() == FIXTURE_SHA)
        self.row['fixture'] = dict(path=str(probe.ARGS.fixture), bytes=len(raw), sha256=FIXTURE_SHA)
        objects = json.loads(raw)['project']['fabric']['objects']
        self.targets = {}
        for asset, key in [(t.ORGANOID, 'primitive-1'), (t.JUNCTION, 'primitive-3')]:
            root = next(o for o in objects if o.get('scientificAssetMeta', {}).get('assetId') == asset)
            leaf = next(o for o in root['objects'] if o.get('importMeta', {}).get('scientificSvgSource', {}).get('key') == key)
            self.targets[asset] = dict(rootId=root['figureId'], leafId=leaf['figureId'], importKey=key)
        self.doc = 'assets'
        self.row['targets'] = self.targets

    async def click_witness(self, name, exposed=False):
        await self.focus_crowded()
        before = await self.state(name + '-before')
        artwork = await self.art(name + '-before')
        ledger = await self.surface.evaluate('''id=>{
          const rows=[2,16].map(command=>{const el=document.querySelector(`.path-node-handle[data-object-id="${id}"][data-command-index="${command}"][data-handle-type="endpoint"]`);
            const b=el.getBoundingClientRect(),s=getComputedStyle(el),center=[b.left+b.width/2,b.top+b.height/2];
            const identify=e=>e?{tag:e.tagName,object:e.dataset?.objectId||'',command:e.dataset?.commandIndex||'',kind:e.dataset?.handleType||'',classes:e.className}:null;
            const stack=document.elementsFromPoint(...center).map(identify);let exposed=null;
            for(const [x,y] of [[.5,.5],[.5,.2],[.5,.8],[.2,.5],[.8,.5],[.2,.2],[.8,.2],[.2,.8],[.8,.8],[.1,.5],[.9,.5],[.5,.1],[.5,.9]])
              if(document.elementFromPoint(b.left+b.width*x,b.top+b.height*y)===el){exposed={x,y};break;}
            return{command,rect:b.toJSON(),center,zIndex:s.zIndex,transform:s.transform,borderRadius:s.borderRadius,receiver:identify(document.elementFromPoint(...center)),stack,exposed};});
          return{rows,zoom:FigureStudio.app.getViewportStateForQa().zoom,
            centerDistance:Math.hypot(rows[0].center[0]-rows[1].center[0],rows[0].center[1]-rows[1].center[1]),
            overlap:[Math.min(rows[0].rect.right,rows[1].rect.right)-Math.max(rows[0].rect.left,rows[1].rect.left),Math.min(rows[0].rect.bottom,rows[1].rect.bottom)-Math.max(rows[0].rect.top,rows[1].rect.top)]};
        }''', self.leaf_id)
        self.require(name + ' records distinct nearby overlapping native endpoint boxes',
                     ledger['centerDistance'] > 0 and all(value > 0 for value in ledger['overlap']), ledger)
        row = ledger['rows'][0]
        fraction = row['exposed'] if exposed else dict(x=.5, y=.5)
        self.require(name + ' has its declared ordinary click coordinate', bool(fraction))
        selector = self.surface.locator(f'.path-node-handle[data-object-id="{self.leaf_id}"][data-command-index="2"][data-handle-type="endpoint"]')
        box = await selector.bounding_box()
        point = [box['x'] + box['width'] * fraction['x'], box['y'] + box['height'] * fraction['y']]
        await self.surface.evaluate('''()=>{for(const [type,handler] of window.crowdedListeners||[])window.removeEventListener(type,handler,true);
          window.crowdedInput=[];window.crowdedListeners=['pointerdown','pointerup','click'].map(type=>{const handler=e=>window.crowdedInput.push({type,trusted:e.isTrusted,detail:e.detail,client:[e.clientX,e.clientY],shift:e.shiftKey,ctrl:e.ctrlKey,meta:e.metaKey,receiver:{object:e.target.dataset?.objectId||'',command:e.target.dataset?.commandIndex||'',kind:e.target.dataset?.handleType||'',classes:e.target.className}});
            window.addEventListener(type,handler,true);return[type,handler];});}''')
        # Exactly one real click; no locator retry, force, setter or drag.
        await self.page.mouse.click(*point)
        events = await self.surface.evaluate('window.crowdedInput')
        await self.settled()
        after = await self.state(name + '-after')
        # Pointerdown rebuilds native overlay buttons; the browser may therefore
        # emit no DOM click after its one ordinary down/up input pair.
        downs = [e for e in events if e['type'] == 'pointerdown']
        ups = [e for e in events if e['type'] == 'pointerup']
        clicks = [e for e in events if e['type'] == 'click']
        self.require(name + ' delivers exactly one trusted ordinary pointer pair',
                     len(downs) == len(ups) == 1 and len(clicks) <= 1
                     and [e['type'] for e in events[:2]] == ['pointerdown', 'pointerup']
                     and all(e['trusted'] for e in events), events)
        if exposed:
            self.require(name + ' exposed-point input reaches the intended button', downs[0]['receiver']['object'] == self.leaf_id and downs[0]['receiver']['command'] == '2')
        self.require(name + ' changes no authored artwork or history', self.same(artwork, await self.art(name + '-after')) and before['history'] == after['history'])
        selected = after['direct']['selectedHandles']
        correct = len(selected) == 1 and selected[0]['objectId'] == self.leaf_id and selected[0]['commandIndex'] == 2 and selected[0]['handleType'] == 'endpoint'
        value = dict(ledger=ledger, clickPoint=point, fraction=fraction, events=events, selected=selected,
                     centerClick=not exposed, intendedCommand=2, correct=correct,
                     interpretation='DOM event receiver and native selected anchor are recorded separately. Distinct centers; no new tie rule is asserted.')
        self.row.setdefault('pickingWitnesses', {})[name] = value
        self.save()
        await self.capture(name, 'One ordinary trusted ' + ('exposed-point' if exposed else 'center') + ' click on endpoint 2 records the actual native selection among its nearby sibling-contour anchors; complete transformed junction artwork remains visible.')
        return correct

    async def run(self):
        self.started = time.perf_counter()
        self.context = None
        self.same = i.real_asset_equivalent
        original = m.equivalent
        m.equivalent = self.same
        try:
            self.load_targets()
            await self.record_process('warm')
            self.context = await self.open_surface(self.browser, probe.ARGS.fixture)
            await self.capture('warm-file-open', 'The actual retained four-drawing file opens intact before navigation or native inspection, with both original transformed Library drawings preserved.')
            warm = await self.click_witness('warm-center')
            await self.context.close()
            self.context = None
            kind = self.browser.browser_type
            await self.browser.close()
            self.row['warmBrowserClosed'] = not self.browser.is_connected()
            self.browser = await kind.launch(**self.report['browserLaunchOptions'])
            await m.base.record_browser_runtime(self.browser, self.report, 'crowded-cold')
            await self.record_process('cold')
            self.require('Warm and cold witnesses use distinct actual browser processes', self.row['browserProcesses']['warm'][0]['id'] != self.row['browserProcesses']['cold'][0]['id'])
            self.context = await self.open_surface(self.browser, probe.ARGS.fixture)
            await self.capture('cold-file-open', 'A genuinely new browser opens the exact actual file before any navigation, Fit or native model inspection; the original composition is naturally restored.')
            cold = await self.click_witness('cold-center')
            exposed = await self.click_witness('cold-exposed', exposed=True)
            self.row['finding'] = 'DISTINCT_CROWDED_CENTER_PICKING_ALREADY_CORRECT' if warm and cold and exposed else 'REPRODUCED_NATIVE_PICKING_DISAGREEMENT'
            self.row['productFixNeeded'] = not (warm and cold and exposed)
            self.require('No page errors', not self.row['pageErrors'], self.row['pageErrors'])
            self.row['status'] = 'passed'
        except BaseException as error:
            self.row.update(status='failed', error=str(error))
            if hasattr(self, 'page') and not self.page.is_closed():
                await self.page.screenshot(path=str(self.out / 'failure.png'))
            raise
        finally:
            if self.context:
                await self.context.close()
            await self.browser.close()
            self.row['contextClosed'] = True
            self.row['browserClosed'] = not self.browser.is_connected()
            self.save()
            m.equivalent = original


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--expected-app-sha256', required=True)
    parser.add_argument('--base-runtime', type=Path)
    parser.add_argument('--viewport', default='1440x1000')
    parser.add_argument('--theme', default='light')
    parser.add_argument('--fixture', type=Path, default=FIXTURE)
    probe.execute(parser.parse_args(), Crowded)
