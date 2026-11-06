"""Minimum/final anchor and contour ownership on the retained transformed Library path."""
import argparse
import copy
import importlib.util
import json
from pathlib import Path
import time

AREA = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('final_count_picking', AREA / 'crowded-anchors.py')
w = importlib.util.module_from_spec(spec)
spec.loader.exec_module(w)
t, q, probe, i, m = w.t, w.q, w.probe, w.i, w.m


def result_commands(path, contour, whole):
    pieces = copy.deepcopy(t.contours(path))
    selected = pieces[contour]
    if whole or selected == [selected[0], ['Z']]:
        pieces.pop(contour)
    else:
        assert selected[0][0] == 'M' and selected[-1] == ['Z']
        assert all(command[0] == 'L' for command in selected[1:-1]), 'Declared straight closed contour'
        selected[0] = ['M', *selected.pop(1)[-2:]]
    return [command for piece in pieces for command in piece] or None


class FinalCounts(w.Crowded):
    async def observation(self, name):
        value = dict(inventory=await self.surface.evaluate(m.g.INVENTORY), state=await self.state(name))
        value['target'] = await self.surface.evaluate('''({id,root})=>{
          const a=FigureStudio.app,o=a.getObjectByIdForQa(id),owner=a.getObjectByIdForQa(root);
          return {exists:Boolean(o),fillRule:o?.fillRule||null,bezier:o?.figureStudioBezierNodeMeta||null,
            rootId:owner?.figureId||null,rootChildren:(owner?.getObjects?.()||[]).map(c=>c.figureId),
            ownerSource:owner?{source:owner.source,importMeta:owner.importMeta,scientificAssetMeta:owner.scientificAssetMeta}:null};}''', dict(id=self.leaf_id, root=self.root_id))
        self.row.setdefault('geometry', {})[name] = value
        self.save()
        return value

    async def select_nodes(self, name, contour, whole):
        before = await self.state(name + '-selection-start')
        path = await self.surface.evaluate('id=>FigureStudio.app.getObjectByIdForQa(id).path', self.leaf_id)
        pieces = t.contours(path)
        start = sum(len(piece) for piece in pieces[:contour])
        end = start + len(pieces[contour])
        endpoints = [h for h in before['direct']['handles'] if h['objectId'] == self.leaf_id and h['handleType'] == 'endpoint' and start <= h['commandIndex'] < end]
        chosen = endpoints if whole else endpoints[:1]
        self.require(name + ' declares existing native endpoints', bool(chosen))
        inputs = []
        for index, handle in enumerate(chosen):
            element = self.surface.locator(f'.path-node-handle[data-object-id="{self.leaf_id}"][data-command-index="{handle["commandIndex"]}"][data-handle-type="endpoint"]')
            box = await element.bounding_box()
            await self.surface.evaluate("()=>{window.finalCountInput=[];window.addEventListener('pointerdown',e=>window.finalCountInput.push({trusted:e.isTrusted,shift:e.shiftKey,client:[e.clientX,e.clientY],receiver:e.target.dataset.commandIndex||'',object:e.target.dataset.objectId||''}),{capture:true,once:true});}")
            if index:
                await self.page.keyboard.down('Shift')
            try:
                await self.page.mouse.click(box['x'] + box['width']/2, box['y'] + box['height']/2)
            finally:
                if index:
                    await self.page.keyboard.up('Shift')
            inputs.extend(await self.surface.evaluate('window.finalCountInput'))
        await self.settled()
        after = await self.state(name + '-selected')
        selected = after['direct']['selectedHandles']
        self.require(name + ' trusted center clicks select exactly the intended native endpoint set',
                     len(inputs) == len(chosen) and all(e['trusted'] for e in inputs)
                     and sorted(h['commandIndex'] for h in selected) == sorted(h['commandIndex'] for h in chosen)
                     and all(h['objectId'] == self.leaf_id and h['handleType'] == 'endpoint' for h in selected), inputs)
        self.require(name + ' selection changes no history', before['history'] == after['history'])
        self.row.setdefault('selections', {})[name] = dict(contourIndex=contour, allContourEndpoints=whole, inputs=inputs, chosen=chosen)
        return chosen

    def preservation(self, name, before, after, expected, removed_commands, removed_contour):
        old = {o['id']: o for o in before['inventory']['leaves']}
        new = {o['id']: o for o in after['inventory']['leaves']}
        expected_ids = set(old) if expected is not None else set(old) - {self.leaf_id}
        self.require(name + ' preserves the exact intended leaf ownership', set(new) == expected_ids)
        self.require(name + ' retains all original top-level artwork owners', [r['id'] for r in before['inventory']['roots']] == [r['id'] for r in after['inventory']['roots']])
        errors = []
        neighbor_max = 0
        for object_id, previous in old.items():
            if object_id == self.leaf_id:
                continue
            current = new[object_id]
            if any(previous[k] != current[k] for k in ['path', 'text', 'parent', 'fill', 'stroke', 'strokeWidth']):
                errors.append(dict(id=object_id, reason='content'))
            a, b = probe.world(previous), probe.world(current)
            if a.keys() != b.keys():
                errors.append(dict(id=object_id, reason='operand keys'))
            else:
                residual = max((max(abs(x-y) for x, y in zip(a[k], b[k])) for k in a), default=0)
                neighbor_max = max(neighbor_max, residual)
                if residual >= 1e-6:
                    errors.append(dict(id=object_id, reason='world pose', residual=residual))
            if not previous['path'] and max(abs(x-y) for x, y in zip(previous['matrix'], current['matrix'])) >= 1e-6:
                errors.append(dict(id=object_id, reason='shape/text pose'))
        self.require(name + ' preserves all independent source shapes and neighboring world placement', not errors, errors)
        a, b = before['target'], after['target']
        self.require(name + ' preserves its native asset parent and complete source record', a['rootId'] == b['rootId'] == self.root_id and a['ownerSource'] == b['ownerSource'])
        children = a['rootChildren'] if expected is not None else [object_id for object_id in a['rootChildren'] if object_id != self.leaf_id]
        self.require(name + ' changes only the declared native parent membership', children == b['rootChildren'])
        residual = None
        if expected is None:
            self.require(name + ' removes only the now-empty fill path', not b['exists'])
        else:
            previous, current = old[self.leaf_id], new[self.leaf_id]
            self.require(name + ' has exactly the independent native command result', current['path'] == expected)
            self.require(name + ' preserves paint, fill rule and native parent', a['fillRule'] == b['fillRule'] and all(previous[k] == current[k] for k in ['parent', 'fill', 'stroke', 'strokeWidth']))
            expected_world = probe.world({**previous, 'path': expected})
            actual_world = probe.world(current)
            residual = max((max(abs(x-y) for x, y in zip(point, actual_world[k])) for k, point in expected_world.items()), default=0)
            self.require(name + ' retains every surviving operand in transformed world coordinates', expected_world.keys() == actual_world.keys() and residual < 1e-6, residual)
            endpoints = [h for h in before['state']['direct']['handles'] if h['objectId'] == self.leaf_id and h['handleType'] == 'endpoint']
            meta = a['bezier']
            self.require(name + ' begins with explicit native node metadata', bool(meta) and len(meta['nodes']) == len(endpoints))
            survivors = [node for node, handle in zip(meta['nodes'], endpoints) if handle['commandIndex'] not in removed_commands]
            contour_ids = [entry['id'] for index, entry in enumerate(meta['contours']) if index != removed_contour]
            self.require(name + ' retains all surviving node and contour IDs with their membership',
                         [node['id'] for node in b['bezier']['nodes']] == [node['id'] for node in survivors]
                         and [entry['id'] for entry in b['bezier']['contours']] == contour_ids
                         and {node['id']: node['contourId'] for node in b['bezier']['nodes']} == {node['id']: node['contourId'] for node in survivors})
        self.row.setdefault('residuals', {})[name] = dict(target=residual, neighbors=neighbor_max)

    async def delete_boundary(self, name, contour=2, whole=False, capture=False):
        chosen = await self.select_nodes(name, contour, whole)
        before = await self.observation(name + '-before')
        before_art = await self.art(name + '-before')
        target = next(o for o in before['inventory']['leaves'] if o['id'] == self.leaf_id)
        expected = result_commands(target['path'], contour, whole)
        removed_contour = contour if expected is None or len(t.contours(expected)) < len(t.contours(target['path'])) else None
        await self.surface.locator('.path-node-handle.selected').first.focus()
        await self.surface.evaluate("()=>{window.finalDeleteKeys=[];window.addEventListener('keydown',e=>window.finalDeleteKeys.push({key:e.key,trusted:e.isTrusted}),{capture:true,once:true});}")
        await self.page.keyboard.press('Delete')
        await self.history(before['state']['history']['undoDepth'] + 1)
        await self.settled()
        after = await self.observation(name + '-after')
        after_art = await self.art(name + '-after')
        events = await self.surface.evaluate('window.finalDeleteKeys')
        self.require(name + ' uses one trusted public Delete', events == [dict(key='Delete', trusted=True)], events)
        self.row.setdefault('deletions', {})[name] = dict(contour=contour, whole=whole, removedCommands=[h['commandIndex'] for h in chosen], expectedCommands=expected, beforeContours=len(t.contours(target['path'])), afterContours=0 if expected is None else len(t.contours(expected)), events=events)
        self.preservation(name, before, after, expected, {h['commandIndex'] for h in chosen}, removed_contour)
        self.require(name + ' creates exactly one history step', after['state']['history']['undoDepth'] == before['state']['history']['undoDepth'] + 1)
        if capture:
            await self.capture(name + '-deleted', 'The declared native fill topology boundary is visible after one Delete: ' + ('the final fill path is removed while its asset parent, separate outlines/tones and neighboring artwork remain.' if expected is None else 'the edited contour retains its surviving anchors or is removed alone; all sibling fill contours and independent artwork remain.'))
        await self.surface.locator('#viewport').focus()
        await self.page.keyboard.press('Control+z')
        await self.history(before['state']['history']['undoDepth'])
        await self.settled()
        undone = await self.observation(name + '-undo')
        self.require(name + ' completed Undo restores complete artwork and exact anchor selection', self.same(before_art, await self.art(name + '-undo')) and q.selection(before['state']) == q.selection(undone['state']))
        if capture:
            await self.capture(name + '-undo', 'One completed Undo restores the preceding native anchor/contour count, path ownership and selected anchors without changing independent artwork.')
        await self.page.keyboard.press('Control+y')
        await self.history(after['state']['history']['undoDepth'])
        await self.settled()
        redone = await self.observation(name + '-redo')
        self.require(name + ' completed Redo restores complete edited artwork', self.same(after_art, await self.art(name + '-redo')))
        self.preservation(name + ' Redo', before, redone, expected, {h['commandIndex'] for h in chosen}, removed_contour)
        if capture:
            await self.capture(name + '-redo', 'Completed Redo restores only the declared topology change, preserving independent fill/outline/tone objects, asset ownership and neighbors.')
        self.save()

    async def new_process_open(self, path, phase, saved):
        await self.context.close()
        self.context = None
        kind = self.browser.browser_type
        await self.browser.close()
        self.browser = await kind.launch(**self.report['browserLaunchOptions'])
        await m.base.record_browser_runtime(self.browser, self.report, phase)
        await self.record_process(phase)
        self.context = await self.open_surface(self.browser, path)
        await self.capture(phase + '-open', 'A genuinely new browser naturally opens the actual saved topology state before any Fit, navigation or native inspection; independent artwork and the transformed asset owner remain intact.')
        self.require(phase + ' preserves complete actual saved artwork', self.same(saved, await self.art(phase + '-open')))

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
            await self.capture('source-file-open', 'The actual retained four-drawing composition opens before navigation or native inspection; the transformed junction fill has its three retained contours.')
            await self.focus_crowded()
            await self.capture('four-anchor-target', 'The transformed junction-strand native fill path exposes the final four-anchor closed contour alongside its two sibling contours and separate outline/tone artwork.')
            await self.delete_boundary('four-to-three')
            await self.delete_boundary('three-to-two', capture=True)
            await self.delete_boundary('two-to-one', capture=True)
            state = await self.observation('one-anchor-before-save')
            endpoints = [h for h in state['state']['direct']['handles'] if h['objectId'] == self.leaf_id and h['handleType'] == 'endpoint']
            self.require('A single editable anchor retains its original native contour and path', state['target']['exists'] and sum(1 for node in state['target']['bezier']['nodes'] if node['contourId'] == state['target']['bezier']['contours'][2]['id']) == 1)
            await self.fit_page()
            await self.capture('one-anchor-save', 'The complete transformed composition is ready for Save with one editable anchor still retained in the selected native fill contour; sibling contours and independent artwork remain intact.')
            first, saved = await self.save_file('minimum-first', await self.art('minimum-first-warm'))
            await self.new_process_open(first, 'one-anchor-cold', saved)
            await self.focus_crowded()
            await self.delete_boundary('one-to-zero', capture=True)
            await self.delete_boundary('two-contours-to-one', contour=0, whole=True)
            await self.delete_boundary('final-contour-removes-fill-path', contour=0, whole=True, capture=True)
            await self.fit_page()
            await self.capture('removed-fill-save', 'The junction asset retains its separate outline/shade/highlight and neighboring owners after its final native fill path is removed, before the actual second Save.')
            second, saved = await self.save_file('minimum-second', await self.art('minimum-second-warm'))
            await self.new_process_open(second, 'removed-fill-cold', saved)
            final = await self.observation('final-cold-ownership')
            self.require('Final cold Open preserves the asset owner and intentionally absent fill path', not final['target']['exists'] and final['target']['rootId'] == self.root_id)
            processes = [rows[0]['id'] for rows in self.row['browserProcesses'].values()]
            self.require('All three actual browser processes are distinct', len(processes) == len(set(processes)) == 3)
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
    parser.add_argument('--fixture', type=Path, default=w.FIXTURE)
    probe.execute(parser.parse_args(), FinalCounts)
