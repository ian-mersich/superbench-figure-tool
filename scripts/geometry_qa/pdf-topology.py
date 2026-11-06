"""Strict genuine-PDF anchor deletion through the shared contour mutation policy."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import time

AREA = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('pdf_final_counts', AREA / 'final-counts.py')
d = importlib.util.module_from_spec(spec)
spec.loader.exec_module(d)
w, t, q, probe, i, m = d.w, d.t, d.q, d.probe, d.i, d.m
FIXTURE = t.ROOT / 'qa_artifacts/selection-reliability-20261105/regression-accepted/1280x800-light/1280x800-light/subset-second.fsfigure'
FIXTURE_SHA = '62768f6ef961dcda91a2315987612e8be53c0f64592e92e6b060fd33a5acc9da'


class PdfTopology(d.FinalCounts):
    def load_targets(self):
        raw = probe.ARGS.fixture.read_bytes()
        self.require('Exact retained actual scientific-PDF file', hashlib.sha256(raw).hexdigest() == FIXTURE_SHA)
        self.row['fixture'] = dict(path=str(probe.ARGS.fixture), bytes=len(raw), sha256=FIXTURE_SHA)
        self.root_id, self.leaf_id = 'pdf-mvwsd6u2-9', 'path-mvwsd6u3-14'
        self.doc = 'pdf'
        self.row['target'] = dict(rootId=self.root_id, leafId=self.leaf_id,
                                 scope='Existing genuine Figure 2 filled legend rectangle; no new import, fixture geometry or source conversion.')

    async def focus_crowded(self):
        await self.surface.locator('[data-figure-layout-choice="advanced"]').click()
        await self.fit_page()
        box = await self.surface.evaluate('id=>FigureStudio.app.getObjectByIdForQa(id).getBoundingRect()', self.leaf_id)
        await self.surface.locator('#viewport').focus()
        await self.page.keyboard.press('z')
        await m.base.HELPERS.drag_scene(self.surface, (box['left']-15, box['top']-15),
                                       (box['left']+box['width']+15, box['top']+box['height']+15))
        await self.page.keyboard.press('a')
        await self.settled()
        target = await self.surface.evaluate('''id=>{
          const o=FigureStudio.app.getObjectByIdForQa(id),b=o.getBoundingRect(),inverse=fabric.util.invertTransform(o.calcTransformMatrix()),path=new Path2D(o.path.map(c=>c.join(' ')).join(' ')),ctx=document.createElement('canvas').getContext('2d'),points=[];
          ctx.lineWidth=2;
          for(const y of [.5,.25,.75,.1,.9])for(const x of [.5,.25,.75,.1,.9]){
            const point={x:b.left+b.width*x,y:b.top+b.height*y},local=fabric.util.transformPoint(new fabric.Point(point.x,point.y),inverse);
            local.x+=o.pathOffset.x;local.y+=o.pathOffset.y;
            if(ctx.isPointInPath(path,local.x,local.y,o.fillRule)&&!ctx.isPointInStroke(path,local.x,local.y)
                &&FigureStudioPdfPaintHitTest.hitObject(o,point,{fabric:window.fabric,tolerance:0}))points.push(point);}
          return{points,bounds:b,policy:'Read-only setup grid; current native filled interior, exclude a two-local-unit boundary band, zero paint tolerance. Trusted selection assertion remains separate.'};}''', self.leaf_id)
        self.require('The genuine current PDF path supplies a painted interior setup point', bool(target['points']), target)
        self.row.setdefault('paintedSetupPoints', []).append(target)
        point = await m.base.HELPERS.canvas_scene_point(self.surface, target['points'][0]['x'], target['points'][0]['y'])
        await self.page.mouse.click(point['x'], point['y'])
        await self.settled()
        state = await self.state('pdf-public-target-' + str(len(self.row['states'])))
        self.require('A trusted painted-interior click selects the original PDF native leaf', state['direct']['objectIds'] == [self.leaf_id], state['direct']['objectIds'])
        await self.ensure_target_frame()

    async def capture(self, name, intent):
        if name.endswith('-deleted'):
            intent = 'The genuine Figure 2 native legend path shows its declared anchor deletion; the neighboring legend, labels and scientific panels retain their native artwork.'
        elif name.endswith('-undo'):
            intent = 'Completed Undo restores the genuine native legend rectangle/path and selected anchor while neighboring scientific labels and panels remain intact.'
        elif name.endswith('-redo'):
            intent = 'Completed Redo restores only the declared native legend-path edit, with compact point controls and unchanged scientific context.'
        elif name == 'pdf-cold-open':
            intent = 'A genuinely new browser opens the actual saved Figure 2 edit before navigation, Fit or native model inspection; the scientific page is naturally restored.'
        await super().capture(name, intent)

    def preservation(self, name, before, after, expected, removed_commands, removed_contour):
        assert expected is not None and removed_contour is None
        old = {o['id']: o for o in before['inventory']['leaves']}
        new = {o['id']: o for o in after['inventory']['leaves']}
        self.require(name + ' preserves every genuine PDF native leaf identity', old.keys() == new.keys())
        errors = []
        neighbor_max = 0
        for object_id, previous in old.items():
            current = new[object_id]
            if object_id == self.leaf_id:
                continue
            if any(previous[k] != current[k] for k in ['path','text','parent','fill','stroke','strokeWidth']):
                errors.append(dict(id=object_id, reason='content'))
            a, b = probe.world(previous), probe.world(current)
            if a.keys() != b.keys():
                errors.append(dict(id=object_id, reason='operand keys'))
            else:
                residual = max((max(abs(x-y) for x,y in zip(a[k],b[k])) for k in a), default=0)
                neighbor_max = max(neighbor_max, residual)
                if residual >= 1e-6:
                    errors.append(dict(id=object_id, reason='world geometry', residual=residual))
            if not previous['path'] and max(abs(x-y) for x,y in zip(previous['matrix'],current['matrix'])) >= 1e-6:
                errors.append(dict(id=object_id, reason='text/shape pose'))
        self.require(name + ' preserves every scientific neighbor and world placement', not errors, errors)
        previous, current = old[self.leaf_id], new[self.leaf_id]
        self.require(name + ' matches the independently declared native path commands', current['path'] == expected)
        self.require(name + ' preserves target parent, paint and source owner metadata',
                     all(previous[k] == current[k] for k in ['parent','fill','stroke','strokeWidth'])
                     and before['target']['ownerSource'] == after['target']['ownerSource']
                     and before['target']['fillRule'] == after['target']['fillRule'])
        a, b = probe.world({**previous, 'path':expected}), probe.world(current)
        residual = max((max(abs(x-y) for x,y in zip(a[k],b[k])) for k in a), default=0)
        self.require(name + ' retains surviving native operands in world coordinates', a.keys() == b.keys() and residual < 1e-6, residual)
        endpoints = [h for h in before['state']['direct']['handles'] if h['objectId'] == self.leaf_id and h['handleType'] == 'endpoint']
        meta = before['target']['bezier']
        ids = [node['id'] for node in meta['nodes']] if meta else [self.leaf_id+'-node-'+str(h['commandIndex']) for h in endpoints]
        survivors = [node_id for node_id, handle in zip(ids,endpoints) if handle['commandIndex'] not in removed_commands]
        result = after['target']['bezier']
        self.require(name + ' retains every surviving native node and contour ID',
                     [node['id'] for node in result['nodes']] == survivors
                     and [c['id'] for c in result['contours']] == ([c['id'] for c in meta['contours']] if meta else [self.leaf_id+'-contour-1']))
        self.row.setdefault('residuals', {})[name] = dict(target=residual, neighbors=neighbor_max)

    async def run(self):
        self.started = time.perf_counter()
        self.context = None
        self.same = q.STRICT_SAME
        original = m.equivalent
        m.equivalent = self.same
        try:
            self.load_targets()
            await self.record_process('warm')
            self.context = await self.open_surface(self.browser, probe.ARGS.fixture)
            await self.capture('pdf-source-open', 'The genuine saved scientific Figure 2 opens intact before navigation or native inspection, retaining original text, plots and native source content.')
            await self.focus_crowded()
            await self.capture('pdf-original-target', 'The genuine filled native legend rectangle is focused with its compact endpoint controls and nearby scientific labels visible before editing.')
            await self.delete_boundary('pdf-first-anchor', contour=0, capture=True)
            await self.fit_page()
            first, saved = await self.save_file('pdf-topology-first', await self.art('pdf-first-warm'))
            await self.new_process_open(first, 'pdf-cold', saved)
            await self.focus_crowded()
            await self.delete_boundary('pdf-cold-continued-anchor', contour=0, capture=True)
            await self.fit_page()
            await self.save_file('pdf-topology-second', await self.art('pdf-second-warm'))
            await self.capture('pdf-continued-save', 'The complete scientific page remains intact after continued native legend-path editing, completed Undo/Redo and a second actual Save.')
            pids = [rows[0]['id'] for rows in self.row['browserProcesses'].values()]
            self.require('The PDF cold Open uses a distinct actual browser process', len(pids) == len(set(pids)) == 2)
            self.require('No PDF page errors', not self.row['pageErrors'], self.row['pageErrors'])
            self.row['status'] = 'passed'
        except BaseException as error:
            self.row.update(status='failed', error=str(error))
            if hasattr(self, 'page') and not self.page.is_closed():
                await self.page.screenshot(path=str(self.out/'failure.png'))
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
    probe.execute(parser.parse_args(), PdfTopology)
