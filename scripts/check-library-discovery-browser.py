#!/usr/bin/env python3
"""Focused Library preview, replacement, part-color and saved-work regression.

Uses real shared-editor UI commands in disposable headless Chromium contexts.
QA APIs supply observations, selection and fixture placement only; application
replacement, recolor, history and serialization are never reimplemented here.
This qualifies current Figure source, leaving installed component pins untouched.
"""
from __future__ import annotations

import argparse
import asyncio
import contextlib
import functools
import hashlib
import http.server
import importlib.util
import io
import json
import math
import threading
import traceback
from datetime import datetime, timezone
from pathlib import Path

from playwright.async_api import async_playwright
from PIL import Image
from figure_package_qa import FigureQaTarget, add_package_arguments, classify_request_failures

ROOT = Path(__file__).resolve().parents[1]
TARGET = FigureQaTarget.from_arguments(ROOT)
RUNTIME_ROOT = ROOT
spec = importlib.util.spec_from_file_location('discovery_library_helpers', ROOT / 'scripts/check-library-drawings-browser.py')
library = importlib.util.module_from_spec(spec)
spec.loader.exec_module(library)
native = library.native
BASE = 'core.mitochondrion.basic'
NETWORK = 'core.mitochondrion.network'
TUBULAR = 'core.mitochondrion.tubular'
CONTROL = 'core.cell.generic_cutaway'
SELECTION_KEYS = ('activeType', 'activeObjectId', 'activeSelectionChildCount', 'selectedCount', 'selectedIds', 'mismatch')


def source_identity():
    scenes = ROOT / 'assets/scientific-scenes'
    return {**library.source_identity(), Path(__file__).name: hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            **({} if TARGET.package_root else {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
               for p in scenes.rglob('*') if p.is_file() and p.suffix in {'.json', '.svg'}})}


def workspace_authored(value):
    """Apply the accepted document comparator to every complete workspace tab."""
    result = json.loads(json.dumps(value))
    for document in result['documents']:
        document['payload'] = native.authored_document(document['payload'])
    return native.rounded(result)


def record_suffix(record):
    return '/' + record['_svg'].relative_to(RUNTIME_ROOT).as_posix()


def exact_differences(expected, actual, path='$'):
    if type(expected) is not type(actual):
        return [{'path': path, 'before': expected, 'after': actual}]
    if isinstance(expected, dict):
        return [difference for key in sorted(expected.keys() | actual.keys())
                for difference in exact_differences(expected.get(key), actual.get(key), path + '.' + key)]
    if isinstance(expected, list):
        if len(expected) != len(actual):
            return [{'path': path + '.length', 'before': len(expected), 'after': len(actual)}]
        return [difference for index, (a, b) in enumerate(zip(expected, actual))
                for difference in exact_differences(a, b, path + '[' + str(index) + ']')]
    return [] if expected == actual else [{'path': path, 'before': expected, 'after': actual}]


class DiscoveryCase(library.Case):
    async def launch(self, routes=None):
        await super().launch(routes)
        if self.route == 'web':
            # App readiness precedes the web host's asynchronous control adoption.
            # Its 44px outer header disappears only once real Browser files UI
            # is installed; wait for that condition before any cold-file work.
            await self.page.wait_for_function('''()=>document.body.dataset.browserChrome==='integrated'
              &&document.querySelector('.web-header')?.hidden
              &&document.getElementById('figure-editor-frame').contentDocument.getElementById('browser-files-trigger')?.isConnected''')
            await self.settle_web_layout()
            host = await self.page.evaluate('''()=>({integrated:document.body.dataset.browserChrome,
              headerHidden:document.querySelector('.web-header').hidden,
              frame:document.getElementById('figure-editor-frame').getBoundingClientRect().toJSON(),height:innerHeight})''')
            self.check('Web host has adopted Browser files and released the outer header space',
                host['integrated'] == 'integrated' and host['headerHidden'] and abs(host['frame']['height'] - host['height']) <= 1, host)

    async def settle_web_layout(self):
        await self.frame.wait_for_function('''()=>document.getElementById('figureStudioRoot').dataset.qaLayoutStable==='true'
          && !FigureStudio.app.getDocumentWorkspaceStateForQa().switching''')
        await self.frame.evaluate('()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))')
        await self.frame.wait_for_function('document.getElementById("figureStudioRoot").dataset.qaLayoutStable==="true"')

    async def cold_open(self, path):
        opened = await super().cold_open(path)
        if self.route == 'web':
            await self.settle_web_layout()
            return await self.document()
        return opened

    async def settle_visible_library_previews(self):
        # Native files can finish opening before asynchronously loaded Library
        # thumbnails decode. Wait only for images in the visible scroll region;
        # offscreen lazy images must not block a faithful cold-Open capture.
        # Keep the polling predicate synchronous: a Promise itself is truthy
        # before its resolved readiness value is available to the poller.
        handle = await self.frame.wait_for_function('''()=>{
          const grid=document.getElementById('assetGrid');if(!grid)return false;
          const bounds=grid.getBoundingClientRect();
          const images=[...grid.querySelectorAll('img')].filter(image=>{
            const rect=image.getBoundingClientRect();
            return rect.width>0&&rect.height>0
              &&rect.right>Math.max(0,bounds.left)&&rect.left<Math.min(innerWidth,bounds.right)
              &&rect.bottom>Math.max(0,bounds.top)&&rect.top<Math.min(innerHeight,bounds.bottom);
          });
          if(!images.length||images.some(image=>!image.complete||image.naturalWidth===0))return false;
          return images;
        }''')
        try:
            images = await handle.evaluate('''async images=>{
              await Promise.all(images.map(image=>image.decode()));
              await new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)));
              return images.map(image=>({src:image.currentSrc,complete:image.complete,naturalWidth:image.naturalWidth}));
            }''')
        finally:
            await handle.dispose()
        self.check('Visible cold-Open Library previews finish decoding before capture',
                   bool(images) and all(image['complete'] and image['naturalWidth'] > 0 for image in images), images)

    async def document(self):
        return await self.frame.evaluate('FigureStudio.app.serializeCurrentDocumentForQa({markSaved:false})')

    async def history(self):
        return await self.frame.evaluate('FigureStudio.app.getHistoryStateForQa()')

    async def owners(self, ids):
        return await self.frame.evaluate('''ids=>ids.map(id=>{const o=FigureStudio.app.getObjectByIdForQa(id);return {
          id,assetId:o.scientificAssetMeta.assetId,locked:!!o.locked,left:o.left,top:o.top,
          width:o.getScaledWidth(),height:o.getScaledHeight(),angle:o.angle,flipX:o.flipX,flipY:o.flipY};})''', ids)

    async def select(self, object_id):
        await self.frame.evaluate('id=>FigureStudio.app.selectObjectsByIdsForQa([id])', object_id)

    async def menu_command(self, menu, command):
        await self.frame.locator(f'[data-menu="{menu}"] > .menu-trigger').click()
        await self.frame.locator(f'[data-menu="{menu}"] [data-command="{command}"]').click()

    async def undo(self, redo=False):
        await self.menu_command('edit', 'redo' if redo else 'undo')

    async def switch(self, kind):
        await self.frame.locator('#figureWorkspaceTab' if kind == 'figure' else '#presentationWorkspaceTab').click()
        await self.frame.wait_for_function('kind=>FigureStudio.app.getDocumentWorkspaceStateForQa().activeKind===kind', arg=kind)

    async def arrange_fixture(self, ids):
        # Place only genuine Library insertions. No geometry, metadata or source
        # payload is fabricated; replacement must preserve these varied sizes.
        await self.frame.evaluate('''ids=>{const doc=FigureStudio.app.serializeCurrentDocumentForQa({markSaved:false}),a=doc.project.artboard;
          const width=a.widthIn*96,height=a.heightIn*96;
          ids.forEach((id,i)=>{const o=FigureStudio.app.getObjectByIdForQa(id);o.scaleToWidth(width*.15);
            if(o.getScaledHeight()>height*.27)o.scaleToHeight(height*.27);
            o.set({originX:'center',originY:'center',left:width*(.18+(i%3)*.3),top:height*(i<3?.31:.68),angle:i===1?12:0});
            o.setCoords();o.canvas.requestRenderAll();});}''', ids)
        await self.frame.evaluate('FigureStudio.app.commitHistoryForQa("Place genuine Library QA fixtures")')

    async def preview(self, asset_id, query='mitochondria'):
        await self.query(query)
        opener = self.frame.locator(f'[data-asset-preview-id="{asset_id}"]')
        await opener.wait_for(state='visible')
        await opener.focus()
        await self.page.keyboard.press('Enter')
        dialog = self.frame.locator('#assetPreviewDialog')
        await dialog.wait_for(state='visible')
        await self.frame.wait_for_function('id=>{const s=FigureStudio.app.getScientificAssetPreviewStateForQa();return s.open&&s.assetId===id&&!s.loading&&!s.busy}', arg=asset_id)
        await self.frame.locator('#assetPreviewImage').evaluate('img=>img.decode()')
        return dialog, opener

    async def dialog_geometry(self, label):
        state = await self.frame.evaluate('''()=>{const d=document.getElementById('assetPreviewDialog'),image=document.getElementById('assetPreviewImage');
          const ids=['assetPreviewCloseBtn',...(FigureStudio.app.getScientificAssetPreviewStateForQa().mode==='change'?['assetPreviewReplaceSelectedBtn']:['assetPreviewInsertBtn'])];
          return {open:d.open,hidden:d.hidden,modal:d.matches(':modal'),name:d.getAttribute('aria-label')||document.getElementById(d.getAttribute('aria-labelledby'))?.textContent,
            bounds:d.getBoundingClientRect().toJSON(),image:image.getBoundingClientRect().toJSON(),natural:[image.naturalWidth,image.naturalHeight],
            actions:ids.map(id=>{const b=document.getElementById(id),r=b.getBoundingClientRect();return {id,visible:r.width>0&&r.height>0,disabled:b.disabled,text:b.textContent,bounds:r.toJSON()};}),
            pageOverflow:document.documentElement.scrollWidth>innerWidth+1,viewport:[innerWidth,innerHeight]};}''')
        self.check(label + ' enlarged preview and actions fit desktop viewport', state['open'] and state['modal'] and not state['hidden']
            and bool(state['name']) and min(state['natural']) > 0 and min(state['image']['width'], state['image']['height']) >= 192
            and all(a['visible'] and a['bounds']['left'] >= 0 and a['bounds']['right'] <= state['viewport'][0] + 1
                and a['bounds']['top'] >= 0 and a['bounds']['bottom'] <= state['viewport'][1] + 1 for a in state['actions'])
            and not state['pageOverflow'], state)
        return state

    async def preview_cancellation(self, kind, ids, records):
        before, before_native, history = await self.document(), await self.frame.evaluate(library.STATE, ids), await self.history()
        dialog, opener = await self.preview(BASE)
        await self.dialog_geometry(kind)
        text = await self.frame.locator('#assetPreviewParts').inner_text()
        self.check(kind + ' preview names declared editable biological parts', all(r['label'] in text for r in records[BASE]['editable_color_regions']), text)
        self.check(kind + ' preview supplies scientific limitations', bool((await self.frame.locator('#assetPreviewLimitations').inner_text()).strip()))
        focusable = await dialog.locator('button:not([disabled]),select:not([disabled]),input:not([disabled]),a[href]').count()
        for index, key in enumerate(['Shift+Tab', 'Tab'] + ['Tab'] * (focusable + 1)):
            await self.page.keyboard.press(key)
            self.check(kind + f' preview keyboard focus remains inside dialog {index} ' + key,
                await dialog.evaluate('d=>d.contains(document.activeElement)'),
                await self.frame.evaluate('()=>({focused:document.hasFocus(),tag:document.activeElement?.tagName,id:document.activeElement?.id})'))
        modal_file_events = []
        def file_chooser(_): modal_file_events.append('filechooser')
        def download(_): modal_file_events.append('download')
        self.page.on('filechooser', file_chooser)
        self.page.on('download', download)
        try:
            for key in ['Control+s', 'Control+o']:
                await self.page.keyboard.press(key)
                await self.frame.evaluate('()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))')
            self.check(kind + ' preview contains file shortcuts without file UI or authored actions',
                not modal_file_events and await dialog.evaluate('d=>d.open&&d.contains(document.activeElement)'), modal_file_events)
        finally:
            self.page.remove_listener('filechooser', file_chooser)
            self.page.remove_listener('download', download)
        await self.frame.locator('#assetPreviewVariantSelect').select_option(NETWORK)
        await self.frame.wait_for_function('id=>{const s=FigureStudio.app.getScientificAssetPreviewStateForQa();return s.assetId===id&&!s.loading}', arg=NETWORK)
        await self.frame.locator('#assetPreviewImage').evaluate('img=>img.decode()')
        await self.preview_source_matches_card(kind + ' original', NETWORK)
        self.check(kind + ' ordinary Library preview inserts only', await self.frame.locator('#assetPreviewInsertBtn').is_visible()
            and not await self.frame.locator('#assetPreviewReplaceSelectedBtn').is_visible() and not await self.frame.locator('#assetPreviewSearchField').is_visible())
        await self.capture(kind + '-01-enlarged-preview.png', 'Show the larger branched mitochondrial network preview with its biological form, editable parts, scientific limitations and one Insert action beside the authored ' + kind + '.')
        await self.page.keyboard.press('Escape')
        await dialog.wait_for(state='hidden')
        self.check(kind + ' Escape restores preview opener focus', await opener.evaluate('b=>b===document.activeElement'))
        dialog, _ = await self.preview(BASE)
        await self.frame.locator('#assetPreviewVariantSelect').select_option(NETWORK)
        await self.frame.wait_for_function('id=>{const s=FigureStudio.app.getScientificAssetPreviewStateForQa();return s.assetId===id&&!s.loading}', arg=NETWORK)
        await self.frame.locator('#assetPreviewImage').evaluate('img=>img.decode()')
        self.check(kind + ' preview can inspect a distinct biological form', await self.frame.locator('#assetPreviewVariantSelect').input_value() == NETWORK)
        await self.frame.locator('#assetPreviewCloseBtn').click()
        await dialog.wait_for(state='hidden')
        await self.frame.locator('#assetArtStyleSelect').select_option('technical-ink')
        await self.frame.locator('#assetPaletteSelect').select_option('pastel')
        dialog, _ = await self.preview(NETWORK)
        await self.preview_source_matches_card(kind + ' technical-ink/pastel', NETWORK)
        appearance = await self.frame.locator('#assetPreviewAppearance').inner_text()
        self.check(kind + ' preview names actual chosen style and palette', 'style 3' in appearance.lower() and 'pastel' in appearance.lower(), appearance)
        await self.frame.locator('#assetPreviewCloseBtn').click()
        await self.frame.locator('#assetArtStyleSelect').select_option('soft-color')
        await self.frame.locator('#assetPaletteSelect').select_option('original')
        self.check(kind + ' Escape/close/form inspection preserve full authored document', native.authored_document(before) == native.authored_document(await self.document()))
        self.check(kind + ' canceled preview preserves native vectors', native.native_reconstruction_difference(before_native, await self.frame.evaluate(library.STATE, ids))['passed'])
        self.check(kind + ' canceled preview creates no Undo entry', await self.history() == history)

    async def preview_source_matches_card(self, label, asset_id):
        await self.frame.wait_for_function('''async id=>{const preview=document.getElementById('assetPreviewImage'),card=document.querySelector(`#assetGrid [data-asset-id="${id}"] img`);
          if(!preview?.src||!card?.src)return false;return await(await fetch(preview.src)).text()===await(await fetch(card.src)).text();}''', arg=asset_id)
        sources = await self.frame.evaluate('''async id=>{const preview=document.getElementById('assetPreviewImage'),card=document.querySelector(`#assetGrid [data-asset-id="${id}"] img`);return {
          preview:await(await fetch(preview.src)).text(),card:await(await fetch(card.src)).text()};}''', asset_id)
        self.check(label + ' enlarged preview uses exact rendered Library SVG', sources['preview'] == sources['card'],
            {'assetId': asset_id, 'previewSha256': hashlib.sha256(sources['preview'].encode()).hexdigest(), 'cardSha256': hashlib.sha256(sources['card'].encode()).hexdigest()})

    async def suggestions(self, kind, records):
        await self.query('mitochondria')
        before = await self.document()
        favorite = self.frame.locator('[data-asset-favorite-concept="core.mitochondrion.basic"]')
        if await favorite.get_attribute('aria-pressed') != 'true':
            await favorite.click()
        await self.frame.locator('[data-asset-discovery="favorites"]').click()
        await self.frame.locator('#assetCategorySelect').select_option('organelle')
        thin = self.frame.locator('[data-asset-variant-id="core.mitochondrion.basic_manuscript"]')
        await thin.click()
        preference = await self.frame.evaluate('FigureStudio.app.getScientificAssetConceptStateForQa("core.mitochondrion.basic")')
        filters = await self.frame.evaluate('''()=>({category:assetCategorySelect.value,topic:assetSubcategorySelect.value,
          discovery:document.querySelector('[data-asset-discovery][aria-pressed="true"]')?.dataset.assetDiscovery,
          scope:document.querySelector('#figureLibraryTabs [aria-selected="true"]')?.dataset.libraryTab})''')
        suggestions = self.frame.locator('#assetRelatedSearches [data-asset-related-query]')
        self.check(kind + ' catalog-backed related searches are available', await suggestions.count() > 0)
        queries = await suggestions.evaluate_all('buttons=>buttons.map(b=>b.dataset.assetRelatedQuery)')
        names = {r.get(key) for r in records.values() for key in ['name', 'scientific_name'] if r.get(key)}
        self.check(kind + ' suggestions use verified complete catalog names', all(q in names for q in queries), queries)
        # Use an actual visible suggestion rather than reimplementing ranking.
        chosen = queries[0]
        await suggestions.first.click()
        self.check(kind + ' related search applies its exact visible query', await self.frame.locator('#assetSearchInput').input_value() == chosen)
        after_filters = await self.frame.evaluate('''()=>({category:assetCategorySelect.value,topic:assetSubcategorySelect.value,
          discovery:document.querySelector('[data-asset-discovery][aria-pressed="true"]')?.dataset.assetDiscovery,
          scope:document.querySelector('#figureLibraryTabs [aria-selected="true"]')?.dataset.libraryTab})''')
        self.check(kind + ' related search retains collection and filters', filters == after_filters, {'before': filters, 'after': after_filters})
        cards = await self.frame.locator('#assetGrid [data-asset-id]').evaluate_all('els=>els.map(e=>e.dataset.assetId)')
        matching = {asset_id for asset_id, record in records.items() if chosen in [record.get('name'), record.get('scientific_name')]}
        self.check(kind + ' related search exposes its named entity/form', bool(matching & set(cards)), {'query': chosen, 'cards': cards, 'matching': sorted(matching)})
        await self.query('mitochondria')
        restored = await self.frame.evaluate('FigureStudio.app.getScientificAssetConceptStateForQa("core.mitochondrion.basic")')
        self.check(kind + ' broad-query return retains the chosen cosmetic companion', preference['pressedVariantIds'] == restored['pressedVariantIds'] and 'core.mitochondrion.basic_manuscript' in restored['pressedVariantIds'], {'before': preference, 'after': restored})
        await self.query('unmatched-discovery-qa-94802')
        self.check(kind + ' no-result query does not insert anything', await self.frame.locator('#assetGrid [data-asset-id]').count() == 0)
        await self.frame.locator('#assetRelatedSearches [data-asset-clear-search]').click()
        self.check(kind + ' Clear search recovers within current filters', await self.frame.locator('#assetSearchInput').input_value() == ''
            and await self.frame.locator('#assetCategorySelect').input_value() == filters['category']
            and await self.frame.locator('[data-asset-discovery="favorites"]').get_attribute('aria-pressed') == 'true'
            and await self.frame.locator('#assetGrid [data-asset-id]').count() > 0)
        self.check(kind + ' refining discovery never mutates authored artwork', native.authored_document(before) == native.authored_document(await self.document()))
        await self.frame.locator('[data-asset-discovery="all"]').click()
        await self.frame.locator('#assetCategorySelect').select_option('all')
        await self.query('FISH')
        cards = await self.frame.locator('#assetGrid [data-asset-id]').evaluate_all('els=>els.map(e=>e.dataset.assetId)')
        self.check(kind + ' FISH retains its assay scope', 'rna.assay_workflow.in_situ_rna_puncta' in cards and 'core.model.zebrafish' not in cards, cards)
        await self.frame.locator('#figureLibraryTab-scenes').click()
        await self.frame.locator('#sceneSearchInput').fill('FISH')
        scene_suggestions = self.frame.locator('#sceneRelatedSearches [data-asset-related-query]')
        await scene_suggestions.first.wait_for(state='visible')
        scene_queries = await scene_suggestions.evaluate_all('els=>els.map(b=>b.dataset.assetRelatedQuery)')
        scene_records = json.loads((RUNTIME_ROOT / 'assets/scientific-scenes/library.v1.json').read_text(encoding='utf8'))['scenes']
        self.check(kind + ' Scenes suggestions contain only verified scene names', all(q in {r['name'] for r in scene_records} for q in scene_queries), scene_queries)
        scene_category = await self.frame.locator('#sceneCategorySelect').input_value()
        chosen_scene = scene_queries[0]
        await scene_suggestions.first.click()
        self.check(kind + ' related scene search retains Scenes and category', await self.frame.locator('#sceneSearchInput').input_value() == chosen_scene
            and await self.frame.locator('#figureLibraryTab-scenes').get_attribute('aria-selected') == 'true'
            and await self.frame.locator('#sceneCategorySelect').input_value() == scene_category)
        expected_scene = next(r['id'] for r in scene_records if r['name'] == chosen_scene)
        self.check(kind + ' suggested scene remains visible without insertion', await self.frame.locator(f'.scientific-scene-entry[data-scene-id="{expected_scene}"]').count() == 1
            and native.authored_document(before) == native.authored_document(await self.document()))
        await self.frame.locator('#figureLibraryTab-assets').click()
        await self.query('mitochondria')

    async def replacement(self, kind, ids, scope):
        await self.select(ids[0])
        before, owners, depth = await self.frame.evaluate(library.STATE, ids), await self.owners(ids), await self.history()
        dialog = await self.change_picker(kind)
        await self.frame.locator('#assetPreviewSearchInput').fill('mitochondria')
        await self.frame.locator('#assetPreviewVariantSelect').select_option(NETWORK)
        await self.frame.wait_for_function('()=>!FigureStudio.app.getScientificAssetPreviewStateForQa().loading')
        action = '#assetPreviewReplaceSelectedBtn'
        target_count = 1 if scope == 'selected' else 2
        if scope == 'all-same':
            await self.frame.locator('#assetPreviewIncludeCopies').check()
        action_text = await self.frame.locator(action).inner_text()
        self.check(kind + ' ' + scope + ' change action describes scope', action_text == ('Change drawing' if scope == 'selected' else 'Change 2 drawings'), action_text)
        if scope == 'all-same':
            note = await self.frame.locator('#assetPreviewReplacementNote').inner_text()
            self.check(kind + ' all-same replacement reports locked exclusion', '1' in note and 'lock' in note.lower(), note)
        await self.dialog_geometry(kind + ' ' + scope + ' ready change')
        await self.capture(kind + '-change-' + scope + '-ready.png', 'Show the chosen mitochondrial network ready to change ' + ('only the selected drawing, with other copies unchecked.' if scope == 'selected' else 'two explicitly counted matching drawings, while the locked copy is kept.'))
        await self.frame.locator(action).click()
        await dialog.wait_for(state='hidden')
        await self.frame.wait_for_function('([id,asset])=>FigureStudio.app.getObjectByIdForQa(id)?.scientificAssetMeta.assetId===asset', arg=[ids[0], NETWORK])
        after, actual_owners = await self.frame.evaluate(library.STATE, ids), await self.owners(ids)
        targets = set(ids[:target_count])
        self.check(kind + ' ' + scope + ' changes exactly its intended owners', all(a['assetId'] == (NETWORK if a['id'] in targets else b['assetId']) for a, b in zip(after, before)), {'before': owners, 'after': actual_owners})
        self.check(kind + ' ' + scope + ' preserves object identities and placement', all(a['id'] == b['id'] and all(abs(a[k] - b[k]) <= .01 for k in ['left', 'top', 'width', 'height', 'angle']) and a['locked'] == b['locked'] and a['flipX'] == b['flipX'] and a['flipY'] == b['flipY'] for a, b in zip(actual_owners, owners)), {'before': owners, 'after': actual_owners})
        unrelated_before = [x for x in before if x['id'] not in targets]
        unrelated_after = [x for x in after if x['id'] not in targets]
        self.check(kind + ' ' + scope + ' preserves unrelated and locked native drawings', native.native_reconstruction_difference(unrelated_before, unrelated_after)['passed'])
        self.check(kind + ' ' + scope + ' replacement is one Undo step', (await self.history())['undoDepth'] == depth['undoDepth'] + 1)
        await self.undo()
        undone = await self.frame.evaluate(library.STATE, ids)
        self.check(kind + ' ' + scope + ' one Undo restores complete native artwork', native.native_reconstruction_difference(native.geometry(before), native.geometry(undone))['passed'])
        await self.undo(redo=True)
        redone = await self.frame.evaluate(library.STATE, ids)
        self.check(kind + ' ' + scope + ' Redo restores replacement', native.native_reconstruction_difference(native.geometry(after), native.geometry(redone))['passed'])
        self.write(kind + '-replace-' + scope + '.json', {'before': before, 'after': after, 'undone': undone, 'redone': redone})
        if scope == 'selected':
            await self.undo()  # Restore two unlocked originals for all-same proof.

    async def change_picker(self, kind):
        button = self.frame.locator('#assetSelectionControls [data-asset-selection-action="change-drawing"]' if kind == 'figure' else '#replaceScientificAssetBtn')
        await button.click()
        dialog = self.frame.locator('#assetPreviewDialog')
        await dialog.wait_for(state='visible')
        await self.frame.wait_for_function('()=>{const s=FigureStudio.app.getScientificAssetReplacementStateForQa();return s.active&&!s.checking&&!FigureStudio.app.getScientificAssetPreviewStateForQa().loading}')
        return dialog

    async def replacement_controls(self, kind, ids):
        await self.select(ids[0])
        before, history = await self.document(), await self.history()
        surface = self.frame.locator('#assetSelectionControls' if kind == 'figure' else '#scientificAssetEditPanel')
        self.check(kind + ' selected drawing replacement controls are visible', await surface.is_visible())
        self.check(kind + ' has one Change drawing action and no all-same action', await surface.locator('[data-asset-selection-action], #replaceScientificAssetBtn').count() == 1
            and await self.frame.locator('#replaceAllScientificAssetsBtn').count() == 0)
        for attempt in range(2):
            await self.change_picker(kind)
            replacement = await self.frame.evaluate('FigureStudio.app.getScientificAssetReplacementStateForQa()')
            self.check(kind + ' chooser always starts with selected copy only ' + str(attempt), replacement['scope'] == 'selected' and replacement['targetCount'] == 1
                and replacement['otherCount'] == 1 and not replacement['edited'] and not await self.frame.locator('#assetPreviewIncludeCopies').is_checked(), replacement)
            if attempt == 1:
                await self.frame.locator('#assetPreviewSearchInput').fill('no-such-biological-drawing-xyz')
                self.check(kind + ' unmatched chooser search has explicit recovery and no stale confirmation', await self.frame.locator('#assetPreviewVariantSelect').is_disabled()
                    and await self.frame.locator('#assetPreviewReplaceSelectedBtn').is_disabled() and 'No drawings match' in await self.frame.locator('#assetPreviewStatus').inner_text())
                await self.frame.locator('#assetPreviewSearchInput').fill('mitochondria')
                await self.frame.locator('#assetPreviewVariantSelect').select_option(NETWORK)
                await self.frame.wait_for_function('()=>!FigureStudio.app.getScientificAssetPreviewStateForQa().loading')
                self.check(kind + ' chooser search recovers to an enabled drawing confirmation', not await self.frame.locator('#assetPreviewReplaceSelectedBtn').is_disabled())
            if attempt == 0:
                await self.dialog_geometry(kind + ' default change chooser')
                await self.capture(kind + '-change-drawing-picker.png', 'Show the focused Change drawing chooser before choosing a new drawing, with biological search, a large preview, and the matching-copy checkbox unchecked by default.')
            await self.frame.locator('#assetPreviewIncludeCopies').check()
            await self.frame.locator('#assetPreviewCloseBtn').click()
            self.check(kind + ' chooser Close exits transient change session', not (await self.frame.evaluate('FigureStudio.app.getScientificAssetReplacementStateForQa()'))['active'])
        self.check(kind + ' replacement scope inspection and Cancel leave authored artwork and history unchanged', native.authored_document(before) == native.authored_document(await self.document()) and history == await self.history())

    async def edited_drawing_protection(self, kind, ids):
        # Prepare a genuine edited native component as fixture content. The
        # chooser, confirmation, replacement and Undo remain real UI commands.
        async def paint_fixture(object_id, paint=None):
            return await self.frame.evaluate('''([id,paint])=>{const o=FigureStudio.app.getObjectByIdForQa(id);
              const leaves=n=>(n.getObjects?.()||[]).length?n.getObjects().flatMap(leaves):[n];
              const child=leaves(o).find(n=>typeof n.fill==='string'&&n.fill!=='none');const before=child.fill;
              child.set({fill:paint||'#258f93'});child.setCoords();o.dirty=true;o.canvas.renderAll();return before;}''', [object_id, paint])

        original_other = await paint_fixture(ids[1])
        await self.select(ids[0])
        await self.change_picker(kind)
        state = await self.frame.evaluate('FigureStudio.app.getScientificAssetReplacementStateForQa()')
        note = await self.frame.locator('#assetPreviewReplacementNote').inner_text()
        self.check(kind + ' matching-copy scope excludes edited components as well as locks', state['otherCount'] == 0
            and not await self.frame.locator('#assetPreviewScopeField').is_visible() and '1 edited' in note and '1 locked' in note, {'state': state, 'note': note})
        await self.frame.locator('#assetPreviewCloseBtn').click()
        await paint_fixture(ids[1], original_other)

        original_selected = await paint_fixture(ids[0])
        await self.frame.evaluate('FigureStudio.app.commitHistoryForQa("Customized native drawing fixture")')
        await self.select(ids[1]); await self.select(ids[0])
        before, history = await self.document(), await self.history()
        before_native = await self.frame.evaluate(library.STATE, ids)
        await self.change_picker(kind)
        await self.frame.locator('#assetPreviewSearchInput').fill('mitochondria')
        await self.frame.locator('#assetPreviewVariantSelect').select_option(NETWORK)
        await self.frame.wait_for_function('()=>!FigureStudio.app.getScientificAssetPreviewStateForQa().loading')
        self.check(kind + ' edited selected drawing needs explicit acknowledgment', await self.frame.locator('#assetPreviewEditedField').is_visible()
            and await self.frame.locator('#assetPreviewReplaceSelectedBtn').is_disabled() and not await self.frame.locator('#assetPreviewAllowEdited').is_checked())
        await self.dialog_geometry(kind + ' edited drawing')
        await self.capture(kind + '-edited-drawing-protection.png', 'Show the explicit edited-parts acknowledgment beside the single Change drawing action; without acknowledging, the selected edited drawing cannot be replaced.')
        await self.frame.locator('#assetPreviewCloseBtn').click()
        self.check(kind + ' cancel keeps all customized artwork and history', native.authored_document(before) == native.authored_document(await self.document()) and history == await self.history())
        await self.change_picker(kind)
        await self.frame.locator('#assetPreviewSearchInput').fill('mitochondria')
        await self.frame.locator('#assetPreviewVariantSelect').select_option(NETWORK)
        await self.frame.wait_for_function('()=>!FigureStudio.app.getScientificAssetPreviewStateForQa().loading')
        await self.frame.locator('#assetPreviewAllowEdited').check()
        await self.frame.locator('#assetPreviewReplaceSelectedBtn').click()
        await self.frame.locator('#assetPreviewDialog').wait_for(state='hidden')
        self.check(kind + ' explicitly acknowledged change affects only selected edited owner', (await self.owners(ids))[0]['assetId'] == NETWORK
            and (await self.owners(ids))[1]['assetId'] == BASE)
        await self.undo()
        restored_native = await self.frame.evaluate(library.STATE, ids)
        self.write(kind + '-customized-undo.json', {'before': before_native, 'restored': restored_native})
        self.check(kind + ' Undo restores complete customized native drawing', native.native_reconstruction_difference(native.geometry(before_native), native.geometry(restored_native))['passed'])
        await paint_fixture(ids[0], original_selected)
        await self.frame.evaluate('FigureStudio.app.commitHistoryForQa("Original native drawing fixture restored")')
        await self.select(ids[1]); await self.select(ids[0])
        await self.change_picker(kind)
        self.check(kind + ' each chooser opens with acknowledgment cleared', not await self.frame.locator('#assetPreviewAllowEdited').is_checked()
            and not await self.frame.locator('#assetPreviewEditedField').is_visible())
        await self.frame.locator('#assetPreviewCloseBtn').click()

        source_type = await self.frame.evaluate('id=>{const o=FigureStudio.app.getObjectByIdForQa(id),before=o.scientificAssetMeta.source_type;o.scientificAssetMeta.source_type="user_asset_library";return before;}', ids[0])
        await self.select(ids[1]); await self.select(ids[0])
        self.check(kind + ' custom saved drawing metadata cannot expose bundled Change drawing', not await self.frame.locator('#assetSelectionControls [data-asset-selection-action="change-drawing"]' if kind == 'figure' else '#replaceScientificAssetBtn').is_visible())
        await self.frame.evaluate('([id,type])=>FigureStudio.app.getObjectByIdForQa(id).scientificAssetMeta.source_type=type', [ids[0], source_type])
        await self.select(ids[1]); await self.select(ids[0])

    async def part_color(self, kind, ids):
        await self.select(ids[0])
        region = next(r for r in (await self.frame.evaluate(library.STATE, ids))[0]['meta']['editableColorRegions'] if r.get('paint', 'fill') == 'fill' and r['id'] != 'outline')
        if kind == 'figure':
            details = self.frame.locator('#assetSelectionColors')
            if await details.get_attribute('open') is None:
                await details.locator('summary').click()
        else:
            if not await self.frame.locator('[data-rail-panel="right"]').is_visible():
                await self.frame.locator('.presentation-toolbar [data-deck-command="format"]').click()
            await self.frame.locator('[data-inspector-tab="properties"]').click()
            details = self.frame.locator('#scientificAssetColorList')
        control = details.locator(f'[data-asset-color-region="{region["id"]}"]')
        self.check(kind + ' Part colors names the chosen biological region', region['label'] in await details.inner_text(), region)
        before, history = await self.frame.evaluate(library.STATE, ids), await self.history()
        color = '#277da8'
        pixels_before = await self.render_witness(kind, 'before-color', color)
        # Native browser color pickers are outside unattended UI scope. Change
        # the real color input and emit its standard committed change event.
        await control.evaluate('(input,color)=>{input.value=color;input.dispatchEvent(new Event("change",{bubbles:true}));}', color)
        await self.frame.wait_for_function('([id,r,c])=>FigureStudio.app.getObjectByIdForQa(id)?.scientificAssetMeta.colorOverrides?.[r]?.toLowerCase()===c', arg=[ids[0], region['id'], color])
        after = await self.frame.evaluate(library.STATE, ids)
        pixels_after = await self.render_witness(kind, 'after-color', color)
        a, b = native.leaves(before[0]['tree']), native.leaves(after[0]['tree'])
        geometry_differences = [{'leaf': index, 'field': key, 'before': x[key], 'after': y[key]}
            for index, (x, y) in enumerate(zip(a, b))
            for key in ['id', 'type', 'path', 'pathOffset', 'matrix', 'bounds', 'strokeWidth', 'regionPaints']
            if native.rounded(x[key]) != native.rounded(y[key])]
        keys = ['id', 'type', 'path', 'pathOffset', 'matrix', 'bounds', 'strokeWidth', 'regionPaints']
        geometry_comparison = native.native_reconstruction_difference([{k: x[k] for k in keys} for x in a], [{k: x[k] for k in keys} for x in b])
        self.write(kind + '-part-color-observed.json', {'region': region, 'color': color, 'before': before, 'after': after,
            'geometryDifferences': geometry_differences, 'geometryComparison': geometry_comparison})
        self.check(kind + ' recolor retains every native primitive and its geometry', geometry_comparison['passed'], geometry_comparison)
        self.check(kind + ' recolor affects only its named biological part', all(all(str(y[channel]).lower() == color if channel in x['regionPaints'].get(region['id'], []) else x[channel] == y[channel] for channel in ['fill', 'stroke']) for x, y in zip(a, b)))
        self.check(kind + ' recolor leaves other drawings exact', native.native_reconstruction_difference(before[1:], after[1:])['passed'])
        self.check(kind + ' part recolor is one Undo step', (await self.history())['undoDepth'] == history['undoDepth'] + 1)
        await self.undo()
        undone = await self.frame.evaluate(library.STATE, ids)
        pixels_undone = await self.render_witness(kind, 'after-undo', color)
        self.check(kind + ' Undo restores the part color and complete artwork', native.native_reconstruction_difference(native.geometry(before), native.geometry(undone))['passed'])
        await self.undo(redo=True)
        redone = await self.frame.evaluate(library.STATE, ids)
        pixels_redone = await self.render_witness(kind, 'after-redo', color)
        self.check(kind + ' Redo restores the part color and complete artwork', native.native_reconstruction_difference(native.geometry(after), native.geometry(redone))['passed'])
        self.check(kind + ' actual canvas paints requested color after edit and Redo and removes it on Undo',
            pixels_before['matchingPixels'] == pixels_undone['matchingPixels'] == 0
            and pixels_after['matchingPixels'] >= 16 and pixels_redone['matchingPixels'] >= 16,
            {'before': pixels_before, 'after': pixels_after, 'undo': pixels_undone, 'redo': pixels_redone})
        self.write(kind + '-part-color.json', {'region': region, 'color': color, 'before': before, 'after': after, 'undone': undone, 'redone': redone})

    async def render_witness(self, kind, stage, color):
        record = {'case': self.name, 'kind': kind, 'stage': stage,
            'file': kind + '-render-' + stage + '.png',
            'intent': 'Record actual authored canvas pixels for the named-part color edit at ' + stage + ', excluding inspector swatches; the separate selection outline may be visible.'}
        self.report.setdefault('renderWitnesses', []).append(record)
        self.write('render-witness-intents.json', [x for x in self.report['renderWitnesses'] if x['case'] == self.name])
        cache_before = await self.cache_observation()
        await self.frame.evaluate('()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))')
        cache_after = await self.cache_observation()
        raw = await self.frame.locator('canvas.lower-canvas').screenshot(animations='disabled')
        (self.out / record['file']).write_bytes(raw)
        target = tuple(int(color[i:i+2], 16) for i in (1, 3, 5))
        image = Image.open(io.BytesIO(raw)).convert('RGB')
        record.update(width=image.width, height=image.height,
            matchingPixels=sum(all(abs(p[i] - target[i]) <= 2 for i in range(3)) for p in image.get_flattened_data()),
            target=color, tolerancePerChannel=2, sha256=hashlib.sha256(raw).hexdigest())
        self.write(kind + '-cache-' + stage + '.json', {'beforeTwoAnimationFrames': cache_before, 'afterTwoAnimationFrames': cache_after})
        return record

    async def cache_observation(self):
        return await self.frame.evaluate('''()=>{const id=FigureStudio.app.getSelectionStateForQa().activeObjectId,o=FigureStudio.app.getObjectByIdForQa(id);
          const visit=n=>({id:n.figureId,type:n.type,fill:n.fill,stroke:n.stroke,dirty:n.dirty,objectCaching:n.objectCaching,
            ownCaching:n.ownCaching,parentId:n.group?.figureId||null,cacheWidth:n._cacheCanvas?.width||0,cacheHeight:n._cacheCanvas?.height||0,
            cacheTranslation:[n.cacheTranslationX,n.cacheTranslationY],zoom:[n.zoomX,n.zoomY],regionPaints:n.importMeta?.scientificSvgSource?.regionPaints||{},
            appearance:n.figureStudioAppearance||n.appearanceMeta||null,styleMeta:n.styleMeta||null,children:(n.getObjects?.()||[]).map(visit)});
          return {selection:id,owner:o?visit(o):null,canvas:o?.canvas?{renderOnAddRemove:o.canvas.renderOnAddRemove,isRendering:o.canvas.isRendering,viewport:o.canvas.viewportTransform}:null};}''')

    async def authored_workflow(self, kind, records):
        await self.enter(kind, 'Library discovery ' + kind)
        ids = [await self.insert(asset, records[asset]) for asset in [BASE, BASE, BASE, CONTROL]]
        await self.arrange_fixture(ids)
        await self.select(ids[0])
        await self.preview_cancellation(kind, ids, records)
        await self.select(ids[2])
        # Lock via an author-visible command, then prove accurate skipped count.
        if kind == 'figure':
            await self.frame.locator('[data-figure-layout-choice="advanced"]').click()
            if await self.frame.locator('#figureStyleToggle').get_attribute('aria-pressed') != 'true':
                await self.frame.locator('#figureStyleToggle').click()
        elif not await self.frame.locator('[data-rail-panel="right"]').is_visible():
            await self.frame.locator('.presentation-toolbar [data-deck-command="format"]').click()
        await self.frame.locator('[data-inspector-tab="layers"]').click()
        await self.frame.locator(f'.layer-actions [data-layer-id="{ids[2]}"][data-layer-action="lock"]').click()
        self.check(kind + ' visible Layers Lock sets only its fixture copy locked', [x['locked'] for x in await self.owners(ids)] == [False, False, True, False])
        await self.frame.locator('[data-inspector-tab="properties"]').click()
        if kind == 'figure':
            await self.frame.locator('[data-figure-layout-choice="simple"]').click()
        await self.select(ids[0])
        await self.replacement_controls(kind, ids)
        await self.edited_drawing_protection(kind, ids)
        await self.suggestions(kind, records)
        await self.replacement(kind, ids, 'selected')
        await self.replacement(kind, ids, 'all-same')
        dialog, _ = await self.preview(TUBULAR)
        await self.frame.locator('#assetPreviewInsertBtn').click()
        await dialog.wait_for(state='hidden')
        await self.frame.wait_for_function('id=>FigureStudio.app.getObjectByIdForQa(FigureStudio.app.getSelectionStateForQa().activeObjectId)?.scientificAssetMeta.assetId===id', arg=TUBULAR)
        inserted = await self.frame.evaluate('FigureStudio.app.getSelectionStateForQa().activeObjectId')
        self.check(kind + ' preview Insert adds a distinct native form', inserted not in ids)
        ids.append(inserted)
        await self.arrange_fixture(ids)
        await self.part_color(kind, ids)
        await self.change_picker(kind)
        self.check(kind + ' named semantic part colors do not count as discarded component edits', not (await self.frame.evaluate('FigureStudio.app.getScientificAssetReplacementStateForQa()'))['edited'])
        await self.frame.locator('#assetPreviewCloseBtn').click()
        palette_surface = self.frame.locator('#assetSelectionColors' if kind == 'figure' else '#scientificAssetColorList')
        await palette_surface.locator('[data-asset-palette]').select_option('pastel')
        await self.frame.wait_for_function('id=>FigureStudio.app.getObjectByIdForQa(id).scientificAssetMeta.paletteId==="pastel"', arg=ids[0])
        await self.change_picker(kind)
        self.check(kind + ' palette plus named part colors does not require discarding edited parts', not (await self.frame.evaluate('FigureStudio.app.getScientificAssetReplacementStateForQa()'))['edited'])
        await self.frame.locator('#assetPreviewCloseBtn').click()
        await self.undo()  # Retain the part-color witness as the saved artwork.
        await self.select(ids[0])
        await self.query('mitochondria')
        await self.capture(kind + '-02-edited-artwork.png', 'Show five complete biological drawings in the ' + kind + ', including two replaced mitochondrial networks, one locked compact mitochondrion, an unrelated cell and an inserted tubular mitochondrion; named Part colors remain available for the selection.')
        return ids

    async def representative_previews(self, records):
        examples = []
        if self.size == (1440, 1000) and self.theme == 'light':
            examples = [('culture', 'culture.model_system.hydrogel_embedded_organoid.budding'),
                        ('microbial', 'microbe.model_system.long_noncontractile_bacteriophage')]
        if self.size == (1280, 800):
            examples.append(('seven-parts', 'microbe.cell.endospore_in_mother_cell'))
        for label, asset_id in examples:
            before, history = await self.document(), await self.history()
            dialog, _ = await self.preview(asset_id, records[asset_id].get('scientific_name') or records[asset_id]['name'])
            await self.dialog_geometry(label)
            parts = await self.frame.locator('#assetPreviewParts').inner_text()
            self.check(label + ' representative names all declared editable parts', all(region['label'] in parts for region in records[asset_id]['editable_color_regions']))
            if label == 'seven-parts':
                details = dialog.locator('[role="region"][aria-label="Drawing details"]')
                await details.focus()
                before_scroll = await details.evaluate('e=>({top:e.scrollTop,height:e.clientHeight,total:e.scrollHeight})')
                await self.page.keyboard.press('End')
                await self.frame.evaluate('()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))')
                after_scroll = await details.evaluate('e=>({top:e.scrollTop,height:e.clientHeight,total:e.scrollHeight})')
                self.check('Seven-part details use an internally keyboard-scrollable pane', after_scroll['total'] <= after_scroll['height'] + 1 or after_scroll['top'] > before_scroll['top'], {'before': before_scroll, 'after': after_scroll})
                await self.dialog_geometry(label + ' after details scroll')
                await details.evaluate('e=>e.scrollTop=0')
            await self.capture('representative-' + label + '-preview.png', 'Show the larger original ' + records[asset_id]['name'] + ' preview with its named editable parts, scientific limits and usable actions; opening this preview leaves the authored Figure unchanged.')
            await self.frame.locator('#assetPreviewCloseBtn').click()
            await dialog.wait_for(state='hidden')
            self.check(label + ' representative preview remains nonmutating', native.authored_document(before) == native.authored_document(await self.document()) and history == await self.history())

    async def continuity(self, ids):
        await self.switch('figure')
        await self.select(ids['figure'][0])
        figure_selection, figure_history = await self.frame.evaluate('FigureStudio.app.getSelectionStateForQa()'), await self.history()
        await self.switch('presentation')
        await self.select(ids['presentation'][0])
        present_selection, present_history = await self.frame.evaluate('FigureStudio.app.getSelectionStateForQa()'), await self.history()
        before = await self.frame.evaluate('async()=>await FigureStudio.app.serializeWorkspace()')
        for kind, selected, history in [('figure', figure_selection, figure_history), ('presentation', present_selection, present_history)]:
            await self.switch(kind)
            actual = await self.frame.evaluate('FigureStudio.app.getSelectionStateForQa()')
            self.check(kind + ' live selection survives switching', all(actual[k] == selected[k] for k in SELECTION_KEYS), {'before': selected, 'after': actual})
            self.check(kind + ' live Undo/Redo history survives switching', await self.history() == history)
        after = await self.frame.evaluate('async()=>await FigureStudio.app.serializeWorkspace()')
        self.check('Complete authored multi-document workspace survives switching', workspace_authored(before) == workspace_authored(after))
        self.write('workspace-switching.json', {'before': before, 'after': after})
        await self.switch('figure')
        await self.frame.locator('[data-figure-layout-choice="advanced"]').click()
        await self.frame.locator('[data-tool="directSelect"]').click()
        await self.frame.evaluate('id=>FigureStudio.app.enterGroupIsolationForQa({groupId:id})', ids['figure'][0])
        child = await self.frame.evaluate('''id=>{const visit=o=>[o,...(o.getObjects?.()||[]).flatMap(visit)];return visit(FigureStudio.app.getObjectByIdForQa(id)).find(o=>o.path)?.figureId;}''', ids['figure'][0])
        await self.frame.evaluate('id=>FigureStudio.app.selectGroupIsolationChildForQa({objectId:id})', child)
        await self.frame.evaluate('id=>FigureStudio.app.selectBezierNodeForQa(id,0)', child)
        before_direct = await self.frame.evaluate('FigureStudio.app.getDirectSelectionStateForQa()')
        await self.switch('presentation'); await self.switch('figure')
        after_direct = await self.frame.evaluate('FigureStudio.app.getDirectSelectionStateForQa()')
        self.check('Live active-path selection survives workspace switching', before_direct['objectId'] == after_direct['objectId'] == child and before_direct['selectedHandleCount'] == after_direct['selectedHandleCount'] == 1, {'before': before_direct, 'after': after_direct})
        await self.frame.evaluate('FigureStudio.app.exitGroupIsolationForQa()')
        await self.frame.locator('[data-tool="select"]').click()
        await self.frame.locator('[data-figure-layout-choice="simple"]').click()

    async def cold_workspace_comparison(self, before, after, ids):
        expected, actual = workspace_authored(before), workspace_authored(after)
        active_id = expected['workspaces'][expected['activeKind']]['activeId']
        index = next(i for i, document in enumerate(expected['documents']) if document['id'] == active_id)
        differences = exact_differences(expected, actual)
        allowed = {f'$.documents[{index}].view.{key}' for key in ['zoom', 'panX', 'panY']}
        view = actual['documents'][index]['view']
        valid = set(view) == {'zoom', 'panX', 'panY'} and all(isinstance(value, (int, float)) and math.isfinite(value) for value in view.values()) and view['zoom'] > 0
        self.write('workspace-cold-differences.json', differences)
        self.check('Actual complete-workspace cold Open preserves every authored field, ID, tab order and inactive view',
            valid and all(difference['path'] in allowed for difference in differences), differences[:20])
        record = {'case': self.name, 'activeDocumentId': active_id, 'differences': differences,
                  'policy': 'Only active-document zoom/pan may adapt to fresh-context rails; every inactive view and all document content remain exact.'}
        if differences:
            kind = expected['activeKind']
            before_native = await self.frame.evaluate(library.STATE, ids[kind])
            record['coldViewport'] = await self.frame.evaluate('FigureStudio.app.getViewportStateForQa()')
            self.write('workspace-cold-view-classification.json', record)
            await self.menu_command('view', 'fit-screen')
            await self.frame.wait_for_function('document.getElementById("figureStudioRoot").dataset.qaLayoutStable==="true"')
            await self.frame.evaluate('()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))')
            fitted = await self.frame.evaluate('async()=>await FigureStudio.app.serializeWorkspace()')
            record['afterActualFit'] = fitted
            record['fittedViewport'] = await self.frame.evaluate('FigureStudio.app.getViewportStateForQa()')
            fitted_document = next(document for document in fitted['documents'] if document['id'] == active_id)
            self.check('Cold view change equals actual visible Fit to Screen at six decimals', native.rounded(view) == native.rounded(fitted_document['view']), {'cold': view, 'fit': fitted_document['view']})
            self.check('Actual Fit changes no cold authored content or native vectors', workspace_authored(after) == workspace_authored(fitted)
                and native.native_reconstruction_difference(before_native, await self.frame.evaluate(library.STATE, ids[kind]))['passed'])
        self.report.setdefault('coldViewClassifications', []).append(record)
        self.write('workspace-cold-view-classification.json', record)

    async def deferred_races(self, ids, records):
        if self.size != (1440, 1000) or self.theme != 'light':
            return
        await self.switch('figure')
        await self.select(ids['figure'][0])
        if not await self.frame.locator('#assetSelectionControls').is_visible():
            await self.frame.locator('#figureStyleToggle').click()
        await self.frame.locator('#assetSelectionControls').wait_for(state='visible')
        await self.frame.wait_for_function('document.getElementById("figureStudioRoot").dataset.qaLayoutStable==="true"')
        await self.frame.evaluate('()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))')
        before = await self.frame.evaluate('async()=>await FigureStudio.app.serializeWorkspace()')
        self.write('deferred-races-before.json', before)
        before_history = await self.history()

        # Hold only the real source fetch; image thumbnails continue normally.
        async def held_request(asset_id, action):
            record = records[asset_id]
            pattern = '**/' + record['_svg'].relative_to(RUNTIME_ROOT).as_posix() + '*'
            started, release = asyncio.Event(), asyncio.Event()
            async def handler(route):
                if route.request.resource_type == 'fetch':
                    started.set()
                    await asyncio.wait_for(release.wait(), timeout=15)
                await route.continue_()
            self.check(action + ' fixture source is genuinely uncached', not (await self.frame.evaluate('id=>FigureStudio.app.getScientificAssetCacheStateForQa(id)', asset_id))['sourceCached'])
            await self.page.route(pattern, handler)
            return pattern, handler, started, release

        asset_id = 'microbe.cell.bacterial_endospore'
        pattern, handler, started, release = await held_request(asset_id, 'Pending preview close')
        try:
            await self.query(records[asset_id]['scientific_name'])
            await self.frame.locator(f'[data-asset-preview-id="{asset_id}"]').click()
            await asyncio.wait_for(started.wait(), timeout=10)
            state = await self.frame.evaluate('FigureStudio.app.getScientificAssetPreviewStateForQa()')
            self.check('Real deferred preview is open and loading', state['open'] and state['loading'] and state['assetId'] == asset_id, state)
            await self.page.keyboard.press('Escape')
            await self.frame.locator('#assetPreviewDialog').wait_for(state='hidden')
            async with self.page.expect_response(lambda response: response.request.resource_type == 'fetch' and response.url.split('?')[0].endswith(record_suffix(records[asset_id]))) as pending_response:
                release.set()
            await (await pending_response.value).body()
            await self.frame.evaluate('()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))')
            after = await self.frame.evaluate('async()=>await FigureStudio.app.serializeWorkspace()')
            differences = exact_differences(workspace_authored(before), workspace_authored(after))
            after_history = await self.history()
            self.write('deferred-preview-observed.json', {'before': before, 'after': after, 'differences': differences, 'beforeHistory': before_history, 'afterHistory': after_history})
            self.check('Released stale preview response remains closed and nonmutating', not (await self.frame.evaluate('FigureStudio.app.getScientificAssetPreviewStateForQa()'))['open']
                and before_history == after_history and not differences, {'differences': differences[:20], 'beforeHistory': before_history, 'afterHistory': after_history})
        finally:
            release.set(); await self.page.unroute(pattern, handler)

        # Rapid options must resolve to the final chosen biological form.
        dialog, _ = await self.preview(BASE)
        options_before = await self.frame.locator('#assetPreviewVariantSelect option').evaluate_all('els=>els.map(e=>e.value)')
        for asset_id in [NETWORK, BASE, TUBULAR]:
            await self.frame.locator('#assetPreviewVariantSelect').select_option(asset_id)
        await self.frame.wait_for_function('id=>{const s=FigureStudio.app.getScientificAssetPreviewStateForQa();return s.assetId===id&&!s.loading}', arg=TUBULAR)
        self.check('Rapid form changes preserve stable choices and final identity', options_before == await self.frame.locator('#assetPreviewVariantSelect option').evaluate_all('els=>els.map(e=>e.value)'))
        await self.preview_source_matches_card('Rapid final form', TUBULAR)
        await self.frame.locator('#assetPreviewCloseBtn').click()

        # A native component edit after opening the chooser must invalidate the
        # reviewed target even when its Figure ID and document remain the same.
        await self.change_picker('figure')
        asset_id = 'culture.assay_workflow.epithelial_scratch_wound'
        pattern, handler, started, release = await held_request(asset_id, 'Pending changed-target drawing')
        try:
            await self.frame.evaluate('id=>{window.__qaPendingChangedTarget=FigureStudio.app.replaceScientificAssetsWithAssetForQa(id);return true;}', asset_id)
            await asyncio.wait_for(started.wait(), timeout=10)
            original_paint = await self.frame.evaluate('''id=>{const o=FigureStudio.app.getObjectByIdForQa(id),leaves=n=>(n.getObjects?.()||[]).length?n.getObjects().flatMap(leaves):[n];
              const n=leaves(o).find(n=>typeof n.fill==='string'&&n.fill!=='none'),before=n.fill;n.set({fill:'#ac3b7e'});o.dirty=true;o.canvas.renderAll();return before;}''', ids['figure'][0])
            await self.frame.evaluate('FigureStudio.app.commitHistoryForQa("Concurrent edited-component fixture")')
            edited_before, edited_history = await self.document(), await self.history()
            async with self.page.expect_response(lambda response: response.request.resource_type == 'fetch' and response.url.split('?')[0].endswith(record_suffix(records[asset_id]))) as pending_response:
                release.set()
            await (await pending_response.value).body()
            result = await self.frame.evaluate('()=>window.__qaPendingChangedTarget')
            self.check('Deferred change preserves same-ID component edits made while loading', result['status'] == 'cancelled' and result['reason'] == 'asset-changed'
                and native.authored_document(edited_before) == native.authored_document(await self.document()) and edited_history == await self.history(), result)
            await self.frame.locator('#assetPreviewDialog').wait_for(state='hidden')
            await self.frame.evaluate('''([id,paint])=>{const o=FigureStudio.app.getObjectByIdForQa(id),leaves=n=>(n.getObjects?.()||[]).length?n.getObjects().flatMap(leaves):[n];
              leaves(o).find(n=>typeof n.fill==='string'&&n.fill!=='none').set({fill:paint});o.dirty=true;o.canvas.renderAll();}''', [ids['figure'][0], original_paint])
            await self.frame.evaluate('FigureStudio.app.commitHistoryForQa("Concurrent component fixture restored")')
        finally:
            release.set(); await self.page.unroute(pattern, handler)

        # Exercise the real replacement command with a deferred source fetch.
        # Normal chooser previews already warm that fetch; call its existing QA
        # exposure to stress the mutation independently. A host tab activation
        # can occur while its modal is busy, unlike a blocked background click.
        # Establish both intentional rail layouts before taking this strict
        # live-view baseline, so opening Format/Library is not misclassified as
        # a late authored mutation or a viewport preservation failure.
        await self.switch('presentation')
        await self.select(ids['presentation'][0])
        if not await self.frame.locator('[data-rail-panel="right"]').is_visible():
            await self.frame.locator('.presentation-toolbar [data-deck-command="format"]').click()
        await self.frame.locator('[data-inspector-tab="properties"]').click()
        insert_menu = self.frame.locator('.deck-insert-menu')
        if not await insert_menu.evaluate('details=>details.open'):
            await insert_menu.locator(':scope > summary').click()
        await self.frame.locator('.presentation-toolbar [data-deck-command="assets"]').click()
        await self.frame.locator('#assetSearchInput').wait_for(state='visible')
        await self.frame.wait_for_function('document.getElementById("figureStudioRoot").dataset.qaLayoutStable==="true"')
        await self.switch('figure')
        await self.select(ids['figure'][0])
        if not await self.frame.locator('#assetSelectionControls').is_visible():
            await self.frame.locator('#figureStyleToggle').click()
        await self.frame.locator('#assetSelectionControls').wait_for(state='visible')
        await self.frame.wait_for_function('document.getElementById("figureStudioRoot").dataset.qaLayoutStable==="true"')
        replacement_before = await self.frame.evaluate('async()=>await FigureStudio.app.serializeWorkspace()')
        self.write('deferred-replacement-before.json', replacement_before)
        await self.change_picker('figure')
        asset_id = 'microbe.membrane_signaling.gram_positive_envelope_segment'
        pattern, handler, started, release = await held_request(asset_id, 'Pending normal replacement')
        try:
            await self.frame.evaluate('id=>{window.__qaPendingDrawingChange=FigureStudio.app.replaceScientificAssetsWithAssetForQa(id);return true;}', asset_id)
            await asyncio.wait_for(started.wait(), timeout=10)
            await self.frame.evaluate('()=>FigureStudio.app.activateDocumentTabForQa(FigureStudio.app.getDocumentWorkspaceStateForQa().workspaces.presentation.activeId)')
            await self.select(ids['presentation'][0])
            if not await self.frame.locator('[data-rail-panel="right"]').is_visible():
                await self.frame.locator('.presentation-toolbar [data-deck-command="format"]').click()
            await self.frame.locator('[data-inspector-tab="properties"]').click()
            await self.change_picker('presentation')
            session = await self.frame.evaluate('FigureStudio.app.getScientificAssetReplacementStateForQa()')
            async with self.page.expect_response(lambda response: response.request.resource_type == 'fetch' and response.url.split('?')[0].endswith(record_suffix(records[asset_id]))) as pending_response:
                release.set()
            await (await pending_response.value).body()
            pending_result = await self.frame.evaluate('()=>window.__qaPendingDrawingChange')
            self.check('Real deferred replacement command cancels on host document change', pending_result['status'] == 'cancelled', pending_result)
            await self.frame.evaluate('()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))')
            after_session = await self.frame.evaluate('FigureStudio.app.getScientificAssetReplacementStateForQa()')
            self.check('Late replacement leaves the new document replacement session intact', session == after_session and after_session['active']
                and after_session['sourceFigureId'] == ids['presentation'][0], {'before': session, 'after': after_session})
            await self.frame.locator('#assetPreviewCloseBtn').click()
            await self.switch('figure')
            after = await self.frame.evaluate('async()=>await FigureStudio.app.serializeWorkspace()')
            differences = exact_differences(workspace_authored(replacement_before), workspace_authored(after))
            self.write('deferred-replacement-observed.json', {'before': replacement_before, 'after': after, 'differences': differences})
            self.check('Late replacement mutates neither complete authored document', not differences, differences[:20])
        finally:
            release.set(); await self.page.unroute(pattern, handler)

        # Exercise the existing latency fixture with an actual Preview Insert,
        # then reload the exact same IDs through the public host API.
        await self.select(ids['figure'][0])
        await self.frame.locator('#assetCategorySelect').select_option('all')
        # A public workspace restore starts with the default closed Style rail.
        # Use that same actual layout before the strict same-ID baseline.
        if await self.frame.locator('#figureStyleToggle').get_attribute('aria-pressed') == 'true':
            await self.frame.locator('#figureStyleToggle').click()
        await self.frame.wait_for_function('document.getElementById("figureStudioRoot").dataset.qaLayoutStable==="true"')
        await self.frame.evaluate('()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))')
        before = await self.frame.evaluate('async()=>await FigureStudio.app.serializeWorkspace()')
        asset_id = 'microbe.model_system.contractile_tailed_bacteriophage'
        await self.preview(asset_id, records[asset_id]['scientific_name'])
        await self.frame.evaluate('FigureStudio.app.setScientificAssetInsertionDelayForQa(1200)')
        try:
            await self.frame.locator('#assetPreviewInsertBtn').click()
            await self.frame.wait_for_function('()=>FigureStudio.app.getScientificAssetPreviewStateForQa().busy')
            await self.page.keyboard.press('Escape')
            busy = await self.frame.evaluate('FigureStudio.app.getScientificAssetPreviewStateForQa()')
            self.check('Busy actual Preview Insert keeps its dialog open on Escape', busy['open'] and busy['busy'], busy)
            await self.frame.evaluate('async workspace=>await FigureStudio.app.loadWorkspace(workspace,{discardUnsaved:true,containerHost:false})', before)
            await self.frame.wait_for_function('id=>{const a=FigureStudio.app.getScientificAssetInsertionAuditForQa();return a?.assetId===id&&a.status==="cancelled"}', arg=asset_id)
            audit = await self.frame.evaluate('FigureStudio.app.getScientificAssetInsertionAuditForQa()')
            after = await self.frame.evaluate('async()=>await FigureStudio.app.serializeWorkspace()')
            differences = exact_differences(workspace_authored(before), workspace_authored(after))
            self.write('deferred-races.json', {'before': before, 'after': after, 'differences': differences, 'cancelledInsertion': audit})
            self.check('Same-ID public workspace restore cancels late Preview Insert', not (await self.frame.evaluate('FigureStudio.app.getScientificAssetPreviewStateForQa()'))['open']
                and not differences, {'audit': audit, 'differences': differences[:20]})
        finally:
            await self.frame.evaluate('FigureStudio.app.setScientificAssetInsertionDelayForQa(0)')

    async def full_workflow(self, records):
        ids = {}
        for kind in ['figure', 'presentation']:
            ids[kind] = await self.authored_workflow(kind, records)
            if kind == 'figure':
                await self.representative_previews(records)
        await self.continuity(ids)
        saved = {}
        for kind, extension in [('figure', '.fsfigure'), ('presentation', '.fsdeck')]:
            await self.switch(kind)
            await self.frame.evaluate('FigureStudio.app.clearSelectionForQa()')
            tree = await self.frame.evaluate(library.STATE, ids[kind])
            path, document = await self.save('discovery' + extension)
            saved[kind] = (path, document, tree)
        workspace = await self.frame.evaluate('async()=>await FigureStudio.app.serializeWorkspace()')
        await self.frame.locator('#fileMenuTrigger').click()
        self.page.once('dialog', lambda dialog: dialog.accept('discovery.fsproject'))
        async with self.page.expect_download() as pending:
            await self.frame.locator('[data-menu="file"] [data-command="save-workspace-project"]').click()
        download = await pending.value
        project_path = self.out / 'discovery.fsproject'
        await download.save_as(project_path)
        self.check('Real complete-workspace Save downloads native .fsproject', download.suggested_filename.endswith('.fsproject') and project_path.stat().st_size > 0)
        self.write('workspace-saved.json', workspace)
        for kind in ['figure', 'presentation']:
            path, document, tree = saved[kind]
            await self.check_saved_file(path, document, tree, ids[kind])
        await self.cold_open(project_path)
        reopened = await self.frame.evaluate('async()=>await FigureStudio.app.serializeWorkspace()')
        self.write('workspace-cold.json', reopened)
        await self.cold_workspace_comparison(workspace, reopened, ids)
        for kind in ['presentation', 'figure']:
            await self.switch(kind)
            tree = await self.frame.evaluate(library.STATE, ids[kind])
            self.check(kind + ' complete workspace cold Open retains native vectors', native.native_reconstruction_difference(saved[kind][2], tree)['passed'])
            self.write(kind + '-native-cold.json', tree)
        await self.query('mitochondria')
        await self.settle_visible_library_previews()
        await self.capture('05-cold-complete-workspace.png', 'Show the complete Figure with its five native drawings restored from the real downloaded multi-document project, with both Figure and Presentation available after fresh-context Open.')
        await self.deferred_races(ids, records)


async def main(args):
    global TARGET, RUNTIME_ROOT
    TARGET = FigureQaTarget.from_arguments(ROOT, args.package_root, args.package_sha256)
    RUNTIME_ROOT = TARGET.runtime_root
    library.TARGET, library.RUNTIME_ROOT = TARGET, RUNTIME_ROOT
    out = args.output_dir.resolve()
    out.relative_to((ROOT / 'qa_artifacts').resolve())
    out.mkdir(parents=True, exist_ok=False)
    report = {'schema': 'figureStudio.libraryDiscovery.browserQa.v1', 'status': 'running', 'route': args.route, 'smoke': args.smoke,
              'cases': [], 'checks': [], 'captures': [], 'pageErrors': [], 'consoleErrors': [], 'failedRequests': [], 'vendorResponses': [],
              'fixture': {'assets': [BASE, BASE, BASE, CONTROL], 'lockedBaseCopies': 1, 'previewInsertedForm': TUBULAR, 'replacementForm': NETWORK},
              'comparisonPolicy': {'document': 'Existing authored_document comparator retains authored fields and IDs; derived clocks/bounds/thumbnails and global cache-count telemetry excluded.',
                  'workspace': 'Every payload, workspace identity, tab order and filename remain exact; live switching and deferred operations also retain views at six decimals. Cold Open retains inactive views; active zoom/pan adaptation must equal actual visible Fit to Screen and is separately recorded.',
                  'native': 'Shared Library STATE includes text and typography for every observation; native_reconstruction_difference retains IDs/metadata/hierarchy/paths/paints/text/typography exactly, with derived scene values within0.01px.',
                  'history': 'Existing geometry comparator only ignores imported child IDs reconstructed by Undo/Redo; owner IDs and all paths/paints remain checked.'}}
    case = server = None
    try:
        report['sourceIdentity'] = source_identity()
        report['runtimeTarget'] = TARGET.record()
        report['catalogSchemaPreflight'] = library.catalog_schema.catalog_schema_report(RUNTIME_ROOT / 'assets/scientific-packs/library.json')
        if report['catalogSchemaPreflight']['status'] != 'passed':
            raise ValueError('Catalog schema preflight failed')
        records = library.catalog_records()
        server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(native.QuietHandler, directory=str(RUNTIME_ROOT)))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)
            for size in ([tuple(map(int, args.smoke_size.split('x')))] if args.smoke else [(1280, 800), (1440, 1000), (1920, 1080)]):
                for theme in ([args.smoke_theme] if args.smoke else ['light', 'dark']):
                    case = DiscoveryCase(browser, f'http://127.0.0.1:{server.server_port}', args.route, size, theme, out, report)
                    try:
                        await case.launch()
                        await case.full_workflow(records)
                    except BaseException:
                        if case.page and not case.page.is_closed():
                            with contextlib.suppress(Exception):
                                case.write('failure-intent.json', {'intent': 'Show the actual editor and any open dialog at the first failed focused discovery check, before browser teardown.'})
                                await case.page.screenshot(path=str(case.out / 'failure.png'))
                                (case.out / 'failure-dom.html').write_text(await case.frame.content(), encoding='utf8')
                                case.write('failure-observation.json', await case.frame.evaluate('''()=>({preview:FigureStudio.app.getScientificAssetPreviewStateForQa?.(),selection:FigureStudio.app.getSelectionStateForQa(),history:FigureStudio.app.getHistoryStateForQa(),workspace:FigureStudio.app.getDocumentWorkspaceStateForQa()})'''))
                        raise
                    case.phase = 'closing-context'
                    await case.context.close()
                    case.case['status'] = 'passed'
                    case.case['savedFiles'] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in case.out.glob('*.fs*')}
                    (out / 'report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf8')
                    print(case.name + ' discovery workflow passed', flush=True)
            await browser.close()
        report['sourceUnchanged'] = report['sourceIdentity'] == source_identity()
        report['runtimeTargetAfter'] = TARGET.record()
        if TARGET.package_root:
            report['packageUnchanged'] = report['runtimeTargetAfter'] == report['runtimeTarget']
            case.check('Exact package inventory remains unchanged', report['packageUnchanged'])
        if not args.smoke:
            case.check('Source remains unchanged throughout final acceptance', report['sourceUnchanged'])
        report['requestFailureClassification'] = classify_request_failures(report['failedRequests'])
        case.check('No unexpected runtime requests fail', not report['requestFailureClassification']['unexpected'], report['requestFailureClassification'])
        case.check('Canonical vendor dependencies load successfully', bool(report['vendorResponses']) and all(r['status'] == 200 for r in report['vendorResponses']), report['vendorResponses'])
        case.check('No page or console errors', not report['pageErrors'] and not report['consoleErrors'], {'page': report['pageErrors'], 'console': report['consoleErrors']})
        report['status'] = 'passed'
    except BaseException as error:
        report['status'] = 'interrupted' if isinstance(error, (KeyboardInterrupt, asyncio.CancelledError)) else 'failed'
        report['failure'], report['traceback'] = str(error), traceback.format_exc()
        if case and case.page and not case.page.is_closed():
            with contextlib.suppress(Exception):
                await case.page.screenshot(path=str(case.out / 'failure.png'))
        raise
    finally:
        if case and case.context:
            with contextlib.suppress(Exception):
                await case.context.close()
        if server:
            server.shutdown(); server.server_close()
        (out / 'report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf8')
        print(json.dumps({'status': report['status'], 'checks': len(report['checks']), 'output': str(out)}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    add_package_arguments(parser)
    parser.add_argument('--route', choices=['direct', 'web'], default='direct')
    parser.add_argument('--smoke', action='store_true')
    parser.add_argument('--smoke-size', choices=['1280x800', '1440x1000', '1920x1080'], default='1440x1000')
    parser.add_argument('--smoke-theme', choices=['light', 'dark'], default='light')
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'qa_artifacts/library-discovery-20261015' / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
    asyncio.run(main(parser.parse_args()))
