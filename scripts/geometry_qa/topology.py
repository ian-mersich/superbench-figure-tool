"""Public deletion on transformed real Library compounds, with actual cold persistence."""
import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import time
from datetime import datetime

AREA = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('topology_geometry', AREA / 'qualify.py')
q = importlib.util.module_from_spec(spec)
spec.loader.exec_module(q)
probe, i, m, ROOT = q.probe, q.probe.i, q.m, q.ROOT
ORGANOID = 'culture.model_system.hydrogel_embedded_organoid.budding'
JUNCTION = 'cellarch.membrane_signaling.tight_junction_network'
COHORT = [(ORGANOID, 'style-4'), (JUNCTION, 'style-4'),
          ('core.antibody.igg', 'soft-color'), ('core.mitochondrion.network', 'style-4')]


def contours(path):
    result = []
    for command in path:
        if command[0] == 'M':
            result.append([])
        assert result, 'A contour must begin with M'
        result[-1].append(command)
    return result


def remove_first_anchor(path):
    """Independent expected first-M removal for the declared explicit cubic ring."""
    pieces = copy.deepcopy(contours(path))
    ring = pieces[0]
    assert ring[0][0] == 'M' and ring[1][0] == ring[-2][0] == 'C' and ring[-1] == ['Z']
    assert ring[-2][-2:] == ring[0][-2:], 'Declared ring has an explicit closing cubic'
    outgoing = ring.pop(1)
    ring[0] = ['M', *outgoing[-2:]]
    ring[-2][3:7] = outgoing[3:7]
    return [command for piece in pieces for command in piece]


def remove_first_contour(path):
    return [copy.deepcopy(command) for piece in contours(path)[1:] for command in piece]


class Topology(q.Geometry):
    async def setup_topology(self):
        self.doc = 'assets'
        await i.RealAssets.setup(self)
        self.row['cohort'] = COHORT
        self.targets = {}
        for index, asset in enumerate([ORGANOID, JUNCTION]):
            root = self.asset_ids[index]
            await self.surface.locator('#viewport').focus()
            await self.page.keyboard.press('v')
            await self.page.keyboard.press('Escape')
            self.parents = []
            row = await self.reveal(root)
            await self.action(row, 'select-on-canvas').click()
            await self.surface.locator('[data-inspector-tab="properties"]').click()
            link = self.surface.locator('[data-context-action="toggle-transform-proportional"]:visible').first
            if await link.get_attribute('aria-pressed') == 'true':
                await link.click()
            await self.number('width', 1.45 if index == 0 else 1.35)
            await self.number('height', 1.10 if index == 0 else .82)
            await self.number('rotation', 23 if index == 0 else -17)
            result = await self.surface.evaluate('''id=>{
              const root=FigureStudio.app.getObjectByIdForQa(id),leaves=[];
              function visit(o){if(o.path)leaves.push({id:o.figureId,name:o.name,fill:o.fill,stroke:o.stroke,fillRule:o.fillRule,path:o.path,importSource:o.importMeta?.scientificSvgSource||null,meta:o.figureStudioBezierNodeMeta||null});for(const c of o.getObjects?.()||[])visit(c);}visit(root);
              return {id,scaleX:root.scaleX,scaleY:root.scaleY,angle:root.angle,leaves};}''', root)
            self.require(asset + ' has a real nonuniform rotated placed owner',
                         abs(result['scaleX'] - result['scaleY']) > .01 and abs(result['angle']) > 5, result)
            source_key, region = ('primitive-1', 'epithelium') if index == 0 else ('primitive-3', 'junction_strand')
            candidates = [leaf for leaf in result['leaves'] if (leaf.get('importSource') or {}).get('key') == source_key
                          and 'fill' in (leaf.get('importSource') or {}).get('regionPaints', {}).get(region, [])
                          and len(contours(leaf['path'])) == (2 if index == 0 else 4)
                          and all(piece[-1] == ['Z'] for piece in contours(leaf['path']))]
            self.require(asset + ' exposes exactly its source-bound compound fill path', len(candidates) == 1)
            leaf = candidates[0]
            self.targets[asset] = dict(rootId=root, leafId=leaf['id'], placed=result,
                                       sourceSvg=self.row['insertions'][index]['sourceSvgSha256'],
                                       importKey=source_key, fillRegion=region,
                                       scope='Selected native fill path only; separately authored outlines, shading and highlights are preserved.')
        self.row['targets'] = self.targets
        await self.fit_page()
        await self.capture('transformed-library-context', 'The two real Style 4 drawings are visibly rotated and nonuniformly scaled through ordinary controls; the antibody and mitochondrion remain intact neighbors.')

    async def fit_page(self):
        await self.surface.locator('[data-menu="view"] > .menu-trigger').click()
        await self.surface.locator('[data-menu="view"] [data-command="fit-screen"]').click()
        await self.settled()

    async def focus_asset(self, asset):
        target = self.targets[asset]
        self.leaf_id, self.root_id = target['leafId'], target['rootId']
        self.parents = [self.root_id]
        await self.reach_target()

    async def observation(self, name):
        value = dict(inventory=await self.surface.evaluate(m.g.INVENTORY), state=await self.state(name))
        value['target'] = await self.surface.evaluate('''id=>{
          const o=FigureStudio.app.getObjectByIdForQa(id);
          return {fillRule:o.fillRule,bezier:o.figureStudioBezierNodeMeta||null,compound:o.figureStudioCompoundPathMeta||null,
            fixedFillProbes:(()=>{const path=new Path2D(o.path.map(c=>c.join(' ')).join(' ')),ctx=document.createElement('canvas').getContext('2d');return {hole:ctx.isPointInPath(path,65,70,o.fillRule),border:ctx.isPointInPath(path,95,68,o.fillRule)};})(),
            ancestors:(()=>{const out=[];for(let p=o.group;p;p=p.group)out.push({id:p.figureId,angle:p.angle,scaleX:p.scaleX,scaleY:p.scaleY});return out;})()};}''', self.leaf_id)
        self.row.setdefault('geometry', {})[name] = value
        self.save()
        return value

    async def select_contour(self, name, whole=False):
        before = await self.state(name + '-selection-start')
        target = await self.surface.evaluate('id=>FigureStudio.app.getObjectByIdForQa(id).path', self.leaf_id)
        boundary = len(contours(target)[0])
        handles = [h for h in before['direct']['handles'] if h['objectId'] == self.leaf_id
                   and h['handleType'] == 'endpoint' and h['commandIndex'] < boundary]
        handles.sort(key=lambda h: h['commandIndex'])
        chosen = handles if whole else handles[:1]
        self.require(name + ' declares existing first-contour endpoints', len(chosen) >= (3 if whole else 1) and chosen[0]['commandIndex'] == 0)
        inputs = []
        for index, handle in enumerate(chosen):
            selector = self.surface.locator(f'.path-node-handle[data-object-id="{self.leaf_id}"][data-command-index="{handle["commandIndex"]}"][data-handle-type="endpoint"]')
            await self.surface.evaluate("()=>{window.topologyInput=[];window.addEventListener('pointerdown',e=>window.topologyInput.push({trusted:e.isTrusted,shift:e.shiftKey,command:e.target.dataset.commandIndex,object:e.target.dataset.objectId}),{capture:true,once:true});}")
            exposed = await selector.evaluate('''element=>{
              const b=element.getBoundingClientRect(),fractions=[[.5,.5],[.5,.2],[.5,.8],[.2,.5],[.8,.5],[.2,.2],[.8,.2],[.2,.8],[.8,.8],[.1,.5],[.9,.5],[.5,.1],[.5,.9]];
              for(const [x,y] of fractions)if(document.elementFromPoint(b.left+b.width*x,b.top+b.height*y)===element)return{x,y};
              return null;}''')
            self.require(name + ' intended anchor has an exposed ordinary pointer target', bool(exposed), dict(command=handle['commandIndex']))
            box = await selector.bounding_box()
            if index:
                await self.page.keyboard.down('Shift')
            try:
                await self.page.mouse.click(box['x'] + box['width'] * exposed['x'], box['y'] + box['height'] * exposed['y'])
            finally:
                if index:
                    await self.page.keyboard.up('Shift')
            inputs.extend(await self.surface.evaluate('window.topologyInput'))
        await self.settled()
        selected = await self.state(name + '-selected')
        refs = selected['direct']['selectedHandles']
        expected = sorted(h['commandIndex'] for h in chosen)
        self.require(name + ' trusted clicks select precisely the intended anchors',
                     len(inputs) == len(chosen) and all(row['trusted'] and row['object'] == self.leaf_id for row in inputs)
                     and sorted(h['commandIndex'] for h in refs) == expected
                     and all(h['objectId'] == self.leaf_id and h['handleType'] == 'endpoint' for h in refs), inputs)
        self.require(name + ' selection creates no history step', before['history'] == selected['history'])
        self.row.setdefault('anchorSelections', {})[name] = dict(inputs=inputs, commands=expected, wholeContour=whole)
        return chosen

    def preserved(self, name, before, after, expected_path, removed_commands):
        old = {o['id']: o for o in before['inventory']['leaves']}
        new = {o['id']: o for o in after['inventory']['leaves']}
        self.require(name + ' preserves every real leaf identity', set(old) == set(new))
        errors = []
        for object_id, prior in old.items():
            current = new[object_id]
            if object_id == self.leaf_id:
                continue
            if any(prior[k] != current[k] for k in ['path', 'text', 'parent', 'fill', 'stroke', 'strokeWidth']):
                errors.append(dict(id=object_id, reason='content'))
            a, b = probe.world(prior), probe.world(current)
            if a.keys() != b.keys() or any(max(abs(x-y) for x, y in zip(a[k], b[k])) > 1e-6 for k in a):
                errors.append(dict(id=object_id, reason='world operands'))
            if not prior['path'] and max(abs(x-y) for x, y in zip(prior['matrix'], current['matrix'])) > 1e-6:
                errors.append(dict(id=object_id, reason='shape/text pose'))
        self.require(name + ' preserves all sibling paths and neighboring artwork in world coordinates', not errors, errors)
        prior, current = old[self.leaf_id], new[self.leaf_id]
        self.require(name + ' preserves target paint, parent and fill rule',
                     all(prior[k] == current[k] for k in ['parent', 'fill', 'stroke', 'strokeWidth'])
                     and before['target']['fillRule'] == after['target']['fillRule'])
        if self.leaf_id == self.targets[ORGANOID]['leafId']:
            self.require(name + ' preserves the actual evenodd lumen and painted ring',
                         after['target']['fillRule'] == 'evenodd'
                         and before['target']['fixedFillProbes'] == after['target']['fixedFillProbes'] == dict(hole=False, border=True))
        self.require(name + ' has exactly the declared independent command result', current['path'] == expected_path)
        expected = probe.world({**prior, 'path': expected_path})
        actual = probe.world(current)
        residual = max((max(abs(x-y) for x, y in zip(expected[k], actual[k])) for k in expected), default=0)
        self.require(name + ' preserves the transformed placement of every surviving operand', expected.keys() == actual.keys() and residual < 1e-6, residual)
        endpoints = [h for h in before['state']['direct']['handles'] if h['objectId'] == self.leaf_id and h['handleType'] == 'endpoint']
        prior_meta = before['target']['bezier']
        old_ids = [n['id'] for n in prior_meta['nodes']] if prior_meta else [self.leaf_id + '-node-' + str(h['commandIndex']) for h in endpoints]
        survivor_ids = [node_id for node_id, handle in zip(old_ids, endpoints) if handle['commandIndex'] not in removed_commands]
        current_meta = after['target']['bezier']
        self.require(name + ' retains all surviving native node IDs', bool(current_meta) and [n['id'] for n in current_meta['nodes']] == survivor_ids)
        old_contour_ids = [c['id'] for c in prior_meta['contours']] if prior_meta else [self.leaf_id + '-contour-' + str(n + 1) for n in range(len(contours(prior['path'])))]
        if len(contours(expected_path)) < len(old_contour_ids):
            old_contour_ids = old_contour_ids[1:]
        all_old_contours = [c['id'] for c in prior_meta['contours']] if prior_meta else [self.leaf_id + '-contour-' + str(n + 1) for n in range(len(contours(prior['path'])))]
        boundaries = []
        count = 0
        for piece in contours(prior['path']):
            boundaries.append((count, count + len(piece)))
            count += len(piece)
        memberships = ({n['id']: n['contourId'] for n in prior_meta['nodes']} if prior_meta else
                       {node_id: all_old_contours[next(j for j, (start, end) in enumerate(boundaries) if start <= handle['commandIndex'] < end)] for node_id, handle in zip(old_ids, endpoints)})
        self.require(name + ' retains surviving contour IDs and node membership',
                     [c['id'] for c in current_meta['contours']] == old_contour_ids
                     and all(n['contourId'] == memberships[n['id']] for n in current_meta['nodes']))
        self.row.setdefault('worldResiduals', {})[name] = residual

    async def delete(self, name, whole=False, toolbar=False, capture=True):
        selected = await self.select_contour(name, whole)
        before_art = await self.art(name + '-before')
        before = await self.observation(name + '-before')
        target = next(o for o in before['inventory']['leaves'] if o['id'] == self.leaf_id)
        expected = remove_first_contour(target['path']) if whole else remove_first_anchor(target['path'])
        await self.surface.evaluate("()=>{for(const [type,handler] of window.topologyDeleteHandlers||[])window.removeEventListener(type,handler,true);window.topologyDeleteInput=[];window.topologyDeleteHandlers=['keydown','click'].map(type=>{const handler=e=>window.topologyDeleteInput.push({type,trusted:e.isTrusted,key:e.key||'',action:e.target.closest?.('[data-context-action]')?.dataset.contextAction||''});window.addEventListener(type,handler,true);return[type,handler];});}")
        if toolbar:
            await self.surface.locator('[data-context-disclosure="anchor-more"]:visible').click()
            button = self.surface.locator('[data-context-action="path-delete-point"]:visible').first
            self.require(name + ' toolbar enables deletion for these anchors', await button.is_enabled())
            await button.click()
        else:
            await self.surface.locator('.path-node-handle.selected').first.focus()
            await self.page.keyboard.press('Delete')
        await self.history(before['state']['history']['undoDepth'] + 1)
        await self.settled()
        after = await self.observation(name + '-after')
        after_art = await self.art(name + '-after')
        events = await self.surface.evaluate('window.topologyDeleteInput')
        self.row.setdefault('deleteInputs', {})[name] = events
        self.require(name + ' uses a trusted public deletion action', any(e['trusted'] and (e['key'] == 'Delete' or e['action'] == 'path-delete-point') for e in events))
        self.require(name + ' creates exactly one history step', after['state']['history']['undoDepth'] == before['state']['history']['undoDepth'] + 1)
        self.preserved(name, before, after, expected, {h['commandIndex'] for h in selected})
        if capture:
            await self.capture(name + '-deleted', 'Only the selected ' + ('junction-strand fill contour is removed; the other three fill contours and separately authored outlines, shading, highlights and nearby artwork remain intact.' if whole else 'first ring anchor is deleted from the transformed organoid fill path; the lumen opening and sibling artwork remain intact.'))
        await self.surface.locator('#viewport').focus()
        await self.page.keyboard.press('Control+z')
        await self.history(before['state']['history']['undoDepth'])
        await self.settled()
        undone = await self.observation(name + '-undo')
        self.require(name + ' completed Undo restores all artwork', self.same(before_art, await self.art(name + '-undo')))
        self.require(name + ' Undo restores the exact selected anchors', q.selection(before['state']) == q.selection(undone['state']))
        if capture:
            await self.capture(name + '-undo', 'One completed Undo restores the transformed drawing, its original contours and the exact selected anchors without changing the neighboring artwork.')
        await self.page.keyboard.press('Control+y')
        await self.history(after['state']['history']['undoDepth'])
        await self.settled()
        redone = await self.observation(name + '-redo')
        self.require(name + ' completed Redo restores all edited artwork', self.same(after_art, await self.art(name + '-redo')))
        self.preserved(name + ' Redo', before, redone, expected, {h['commandIndex'] for h in selected})
        if capture:
            await self.capture(name + '-redo', 'Completed Redo restores the single intended topology change while preserving the transformed drawing and all sibling artwork.')
        return before_art, after_art, before, after

    def same_separate_actions(self, name, keyboard, toolbar):
        # The two distinct actions intentionally record distinct edit times.
        # This exception applies only to this pair, never Undo/Redo or files.
        a, b = copy.deepcopy(keyboard), copy.deepcopy(toolbar)
        def find(value):
            if isinstance(value, dict):
                if value.get('figureId') == self.leaf_id:
                    return value
                for child in value.values():
                    result = find(child)
                    if result is not None:
                        return result
            if isinstance(value, list):
                for child in value:
                    result = find(child)
                    if result is not None:
                        return result
            return None
        left, right = find(a), find(b)
        times = [row['figureStudioEditState'].pop('last_edited_at') for row in [left, right]]
        self.require(name + ' distinct actions each retain a valid edit timestamp', all(datetime.fromisoformat(t.replace('Z', '+00:00')) for t in times))
        self.row.setdefault('keyboardToolbarEditTimes', {})[name] = dict(objectId=self.leaf_id, field='figureStudioEditState.last_edited_at', keyboard=times[0], toolbar=times[1], scope='Only comparison of two separate actions; all other fields use the established Library comparator.')
        return self.same(a, b)

    async def keyboard_toolbar_pair(self, asset, name, whole):
        await self.focus_asset(asset)
        await self.capture(name + '-selected', 'The original transformed ' + ('tight-junction strand fill path shows all four closed sibling contours before deletion; independent outline and tone parts remain separate artwork.' if whole else 'organoid drawing shows the closed outer ring and clear lumen before deleting its first anchor.'))
        before, keyboard, state, after = await self.delete(name + '-keyboard', whole)
        await self.surface.locator('#viewport').focus()
        await self.page.keyboard.press('Control+z')
        await self.history(state['state']['history']['undoDepth'])
        await self.settled()
        self.require(name + ' keyboard witness can return to its exact baseline', self.same(before, await self.art(name + '-toolbar-baseline')))
        _before, toolbar, _state, _after = await self.delete(name + '-toolbar', whole, toolbar=True, capture=False)
        self.require(name + ' keyboard and toolbar produce identical artwork apart from their individual edit times', self.same_separate_actions(name, keyboard, toolbar))

    async def save_file(self, name, warm):
        path, saved = await super().save_file(name, warm)
        project = json.loads(path.read_text(encoding='utf-8'))['project']
        self.require(name + ' actual file records the accepted beta26 writer', project['version'] == project['manifest']['version'] == '1.0.0-beta.26')
        self.row.setdefault('actualWriterVersions', []).append(dict(path=str(path), writerVersion=project['version'], manifestVersion=project['manifest']['version']))
        return path, saved

    async def run(self):
        self.started = time.perf_counter()
        self.context = None
        self.same = i.real_asset_equivalent
        original = m.equivalent
        m.equivalent = self.same
        try:
            await self.record_process('warm')
            await self.setup_topology()
            await self.keyboard_toolbar_pair(ORGANOID, 'organoid-first-anchor', False)
            await self.keyboard_toolbar_pair(JUNCTION, 'junction-one-contour', True)
            await self.fit_page()
            await self.capture('warm-topology-save', 'The complete four-drawing composition remains intact after the organoid anchor deletion and removal of one tight-junction contour, before the first actual Save.')
            path, saved = await self.save_file('topology-first', await self.art('topology-warm-save'))
            await self.context.close()
            self.context = None
            kind = self.browser.browser_type
            await self.browser.close()
            self.row['warmBrowserClosed'] = not self.browser.is_connected()
            self.browser = await kind.launch(**self.report['browserLaunchOptions'])
            await m.base.record_browser_runtime(self.browser, self.report, 'topology-cold')
            await self.record_process('cold')
            pids = self.row['browserProcesses']
            self.require('Actual warm and cold browser PIDs differ', len(pids['warm']) == len(pids['cold']) == 1 and pids['warm'][0]['id'] != pids['cold'][0]['id'])
            self.context = await self.open_surface(self.browser, path)
            await self.capture('topology-cold-open', 'A genuinely new browser opens the actual saved topology edits before any navigation, Fit or model inspection; the saved four-drawing composition is naturally restored.')
            self.require('Fresh-process Open preserves complete actual saved artwork', self.same(saved, await self.art('topology-cold-open')))
            await self.focus_asset(ORGANOID)
            await self.delete('cold-organoid-first-anchor', capture=True)
            await self.focus_asset(JUNCTION)
            await self.delete('cold-junction-one-contour', whole=True, capture=True)
            await self.fit_page()
            await self.save_file('topology-second', await self.art('topology-cold-save'))
            await self.capture('topology-continued-save', 'The reopened native drawings remain editable after further anchor/contour deletions and completed Undo/Redo, with the four original artwork owners still present.')
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
    args = parser.parse_args()
    i.REAL_ASSET_COHORT = COHORT
    i.ASSET_RUNTIME_ROOT = args.base_runtime or args.root
    probe.execute(args, Topology)
