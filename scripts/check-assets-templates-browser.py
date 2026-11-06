#!/usr/bin/env python3
"""Qualify the unified Scientific Assets/Templates Library in desktop Chromium.

This is a thin adapter over the maintained editable-drawing browser harness.
It exercises actual Library and File controls. Source pilots and package
qualification are recorded separately, with independent controller/image review.
"""
from __future__ import annotations

import argparse
import asyncio
import base64
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
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

from PIL import Image
from playwright.async_api import async_playwright
from figure_package_qa import FigureQaTarget, add_package_arguments, classify_request_failures
import figure_action_paint_qa as paint

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location('maintained_library_drawing_qa', ROOT / 'scripts/check-library-drawings-browser.py')
library = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(library)
native = library.native
_public_repaint_spec = importlib.util.spec_from_file_location(
    'maintained_public_repaint_file_helpers', ROOT / 'scripts/check-figure-public-repaint-browser.py')
public_repaint = importlib.util.module_from_spec(_public_repaint_spec)
_public_repaint_spec.loader.exec_module(public_repaint)
TARGET = FigureQaTarget.from_arguments(ROOT)
RUNTIME_ROOT = ROOT

# Scene titles, labels and connector shapes are native objects without asset
# metadata. Preserve the maintained tree/text snapshot and strict asset roots.
_ASSET_FIELDS = 'assetId:o.scientificAssetMeta.assetId,meta:o.scientificAssetMeta,'
_OBJECT_LOOKUP = 'const o=app.getObjectByIdForQa(id);return o?{'
if library.STATE.count(_ASSET_FIELDS) != 1 or library.STATE.count(_OBJECT_LOOKUP) != 1:
    raise ValueError('Review the mixed-scene adapter against the maintained snapshot')
MIXED_SCENE_STATE = library.STATE.replace(_ASSET_FIELDS,
    'assetId:o.scientificAssetMeta?.assetId||"",meta:o.scientificAssetMeta||null,', 1).replace(
    _OBJECT_LOOKUP, 'const o=app.getObjectByIdForQa(id);if(!o)throw Error("Scene object is missing: "+id);'
    'if(o?.figureType==="scientificAsset"&&!o.scientificAssetMeta)throw Error("Scientific asset metadata is missing: "+id);return o?{', 1)

NEW_SCENES = [
    'rt-qpcr-expression-workflow', 'immunoprecipitation-workflow',
    'indirect-immunofluorescence-workflow', 'sandwich-elisa-workflow',
    'wound-closure-assay-workflow', 'epithelial-barrier-transwell-workflow',
    'chemical-synaptic-transmission', 'angiogenic-sprouting',
]
LEGACY_SCENE = 'immunoblot-assay-workflow'
NEW_PACKS = {'neurobiology', 'tissue-vascular'}
ART_STYLES = ['soft-color', 'cut-paper', 'technical-ink', 'style-4']
STYLE_LABELS = {'soft-color': 'Style 1', 'cut-paper': 'Style 2', 'technical-ink': 'Style 3', 'style-4': 'Style 4'}
STYLE_RENDERER = 'app/scientific-asset-art-styles.js'


def source_identity():
    paths = {Path(__file__).resolve(), ROOT / 'scripts/check-library-drawings-browser.py',
             ROOT / 'scripts/check-rna-artwork-browser.py', ROOT / 'scripts/figure_studio_entry_qa.py',
             ROOT / 'scripts/figure_package_qa.py', ROOT / 'scripts/figure_action_paint_qa.py',
             ROOT / 'scripts/action-paint-observer.js', ROOT / 'scripts/check-figure-public-repaint-browser.py'}
    if TARGET.package_root:
        return {**{p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                   for p in sorted(paths)}, **TARGET.inventory_identity()}
    for folder in ('app', 'web'):
        paths.update(p for p in (RUNTIME_ROOT / folder).rglob('*') if p.is_file() and p.suffix in {'.js', '.css', '.html', '.json'})
    paths.add(RUNTIME_ROOT / 'assets/scientific-packs/library.json')
    packlib = json.loads((RUNTIME_ROOT / 'assets/scientific-packs/library.json').read_text(encoding='utf8'))
    for pack in packlib['packs']:
        if pack.get('enabled'):
            catalog = RUNTIME_ROOT / 'assets/scientific-packs' / pack['path']
            paths.add(catalog)
            paths.update(catalog.parent / item['file'] for item in json.loads(catalog.read_text(encoding='utf8'))['assets'])
    for entry in packlib.get('art_styles', []):
        manifest_path = RUNTIME_ROOT / 'assets/scientific-packs' / entry['path']
        paths.add(manifest_path)
        manifests = [(manifest_path, json.loads(manifest_path.read_text(encoding='utf8')))]
        supplement = entry.get('supplement')
        if supplement:
            supplement_path = RUNTIME_ROOT / 'assets/scientific-packs' / supplement['path']
            paths.add(supplement_path)
            manifests.append((supplement_path, json.loads(supplement_path.read_text(encoding='utf8'))))
        paths.update(path.parent / item['file'] for path, manifest in manifests
                     for item in manifest.get('assets', []))
    scene_root = RUNTIME_ROOT / 'assets/scientific-scenes'
    paths.update(p for p in scene_root.rglob('*') if p.is_file())
    return {p.relative_to(RUNTIME_ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(paths) if p.is_file()}


def new_asset_records():
    records = library.catalog_records()
    selected = {asset_id: record for asset_id, record in records.items()
                if record['_catalog'].parent.name in NEW_PACKS}
    if len(selected) != 40:
        raise ValueError(f'Expected exactly 40 new neuro/tissue assets; found {len(selected)}: {len(selected)}')
    missing = {asset_id: sorted(set(ART_STYLES) - set(record.get('available_art_styles', [])))
               for asset_id, record in selected.items()
               if not set(ART_STYLES) <= set(record.get('available_art_styles', []))}
    if missing:
        raise ValueError(f'New drawings do not advertise all four styles: {missing}')
    return records, selected


def style4_variant_records(new_records):
    packlib = json.loads((RUNTIME_ROOT / 'assets/scientific-packs/library.json').read_text(encoding='utf8'))
    entries = [entry for entry in packlib.get('art_styles', []) if entry.get('id') == 'style-4']
    if len(entries) != 1:
        raise ValueError(f'Expected one Style 4 art_styles entry; found {len(entries)}')
    entry = entries[0]
    manifest_path = RUNTIME_ROOT / 'assets/scientific-packs' / entry['path']
    manifest = json.loads(manifest_path.read_text(encoding='utf8'))
    if manifest.get('id') != 'style-4':
        raise ValueError(f'Unexpected Style 4 manifest identity: {manifest.get("id")}')
    base_assets = manifest.get('assets', [])
    declared_supplement = entry.get('supplement')
    if not declared_supplement:
        raise ValueError('Style 4 registry must declare its expansion supplement')
    supplement_path = RUNTIME_ROOT / 'assets/scientific-packs' / declared_supplement['path']
    supplement = json.loads(supplement_path.read_text(encoding='utf8'))
    if supplement.get('id') != 'style-4':
        raise ValueError(f'Unexpected Style 4 supplement identity: {supplement.get("id")}')
    primary_count = len(base_assets)
    supplement_assets = supplement.get('assets', [])
    if len(supplement_assets) != declared_supplement.get('asset_count'):
        raise ValueError(f'Style 4 supplement count mismatch: expected {declared_supplement.get("asset_count")}, found {len(supplement_assets)}')
    primary_dir = manifest_path.parent.resolve()
    supplement_dir = supplement_path.parent.resolve()
    try:
        supplement_prefix = supplement_dir.relative_to(primary_dir).as_posix()
    except ValueError as error:
        raise ValueError('Style 4 supplement directory must remain under its primary manifest directory') from error
    variants, source_paths = {}, {}
    for item in base_assets:
        asset_id = item.get('asset_id')
        variants[asset_id] = item
        source_paths[asset_id] = manifest_path.parent / item['file']
    for item in supplement_assets:
        asset_id = item.get('asset_id')
        if asset_id in variants:
            raise ValueError(f'Style 4 primary manifest and supplement duplicate asset identity: {asset_id}')
        variants[asset_id] = item
        source_paths[asset_id] = manifest_path.parent / supplement_prefix / item['file']
    combined_count = len(variants)
    if primary_count + len(supplement_assets) != combined_count:
        raise ValueError('Style 4 combined manifests contain duplicate identities')
    if combined_count != entry.get('asset_count'):
        raise ValueError(f'Style 4 combined coverage mismatch: registry {entry.get("asset_count")}, combined {combined_count}')
    if primary_count != entry.get('asset_count', 0) - declared_supplement.get('asset_count', 0):
        raise ValueError(f'Style 4 primary manifest count mismatch: found {primary_count}')
    result, missing = {}, []
    for asset_id, record in new_records.items():
        if 'style-4' not in record.get('available_art_styles', []):
            raise ValueError(f'Catalog does not advertise Style 4 for {asset_id}')
        variant = variants.get(asset_id)
        if not variant:
            missing.append(asset_id)
            continue
        path = source_paths[asset_id]
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != variant.get('sha256'):
            raise ValueError(f'Style 4 SVG source identity mismatch: {asset_id}: {path}')
        regions = variant.get('editable_color_regions')
        if not isinstance(regions, list) or not regions:
            raise ValueError(f'Style 4 variant lacks semantic editable regions: {asset_id}')
        base_region_ids = sorted(region['id'] for region in record.get('editable_color_regions', []))
        style_region_ids = sorted(region['id'] for region in regions)
        if base_region_ids != style_region_ids:
            raise ValueError(f'Style 4 changes semantic region identity for {asset_id}: {base_region_ids} vs {style_region_ids}')
        resource_path = path.relative_to(RUNTIME_ROOT)
        result[asset_id] = {**record, 'file': resource_path.as_posix(),
            'editable_color_regions': [region for region in regions if region.get('no_rendered_paint') is not True],
            '_svg': path, '_style4': variant}
    if missing:
        raise ValueError(f'Style 4 has no source-bound variants for {len(missing)} new assets: {missing}')
    if len(result) != len(new_records):
        raise ValueError(f'Style 4 coverage mismatch: expected {len(new_records)}, found {len(result)}')
    return result, manifest_path, manifest, supplement_path, supplement, combined_count, primary_count


def replacement_pairs(selected):
    result = []
    for pack in sorted(NEW_PACKS):
        records = [r for r in selected.values() if r['_catalog'].parent.name == pack]
        by_concept = {}
        for record in records:
            by_concept.setdefault(record.get('concept_id'), []).append(record)
        candidates = [(key, sorted(value, key=lambda x: x['id'])) for key, value in sorted(by_concept.items())
                      if key and len(value) == 2]
        if len(candidates) < 2:
            raise ValueError(f'{pack} needs at least two two-form concepts for replacement acceptance')
        result.extend((pack, key, forms) for key, forms in candidates[:2])
    return result


def key_presence_differences(expected, actual, path='$'):
    """Supplement exact helper diffs when a missing key would resemble null."""
    if not isinstance(expected, dict) or not isinstance(actual, dict):
        if isinstance(expected, list) and isinstance(actual, list):
            return [difference for index, (left, right) in enumerate(zip(expected, actual))
                    for difference in key_presence_differences(left, right, f'{path}[{index}]')]
        return []
    differences = []
    for key in sorted(expected.keys() - actual.keys()):
        differences.append({'path': f'{path}.{key}', 'presentIn': 'before-only', 'value': expected[key]})
    for key in sorted(actual.keys() - expected.keys()):
        differences.append({'path': f'{path}.{key}', 'presentIn': 'after-only', 'value': actual[key]})
    for key in sorted(expected.keys() & actual.keys()):
        differences.extend(key_presence_differences(expected[key], actual[key], f'{path}.{key}'))
    return differences


def write_progress(report, out, case, phase, detail=None):
    row = {'case': case, 'phase': phase, 'utc': datetime.now(timezone.utc).isoformat(), 'detail': json.loads(json.dumps(detail))}
    report.setdefault('progress', []).append(row)
    (out / 'report.json').write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n', encoding='utf8')
    print(json.dumps(row), flush=True)


def report_exit_code(report):
    return 0 if report.get('status') == 'passed' else 1


def validate_stop_scope(stop_after, case, package_root=False):
    if stop_after and case == 'all':
        raise ValueError(f'--stop-after {stop_after} requires one explicit desktop case')
    if stop_after == 'qPCR-roundtrip' and package_root:
        raise ValueError('--stop-after qPCR-roundtrip is available only for the SOURCE checkout.')


def round_trip_plan(stop_after, selected_cases):
    if stop_after == 'library-surface':
        return {'qPCRTemplate': 0, 'representativeFourStyleAssets': 0, 'fullStyle4All40': 0, 'total': 0}
    if stop_after == 'qPCR-roundtrip':
        return {'qPCRTemplate': 1, 'representativeFourStyleAssets': 0, 'fullStyle4All40': 0, 'total': 1}
    return {
        'qPCRTemplate': len(selected_cases),
        'representativeFourStyleAssets': len(selected_cases),
        'fullStyle4All40': int(any(name == '1440x1000-light' for name, _ in selected_cases)),
        'total': len(selected_cases) * 2 + int(any(name == '1440x1000-light' for name, _ in selected_cases)),
    }


def canonical_svg_markup(svg):
    if ET.fromstring(svg).tag != '{http://www.w3.org/2000/svg}svg':
        raise ValueError('Expected a namespaced SVG root')
    return ET.canonicalize(svg, rewrite_prefixes=True, strip_text=False, with_comments=False)


class Case(library.Case):
    def checkpoint(self, phase, detail=None):
        self.case['phase'] = phase
        write_progress(self.report, self.out.parent, self.name, phase, detail)

    async def launch(self, routes=None):
        self.checkpoint('browser-launch-start')
        await super().launch(routes)
        self.checkpoint('initial-app-ready')
        # Exercise the actual migration path on every fresh context.
        await self.frame.evaluate("localStorage.setItem('figureStudio.libraryView.v1','scenes')")
        self.phase = 'startup'
        self.checkpoint('reload-for-legacy-preference')
        await self.page.reload(wait_until='domcontentloaded')
        self.checkpoint('legacy-reload-dom-ready')
        self.frame = await (await self.page.wait_for_selector('#figure-editor-frame')).content_frame() if self.route == 'web' else self.page
        await self.frame.wait_for_function('window.FigureStudio?.app?.isReady===true')
        self.phase = 'ready'
        self.checkpoint('legacy-reload-app-ready')
        await self.frame.wait_for_function("localStorage.getItem('figureStudio.libraryView.v1')==='templates'")
        self.check('Legacy scenes preference migrates to templates', await self.frame.evaluate("localStorage.getItem('figureStudio.libraryView.v1')" ) == 'templates')
        state = await self.frame.evaluate("FigureStudioLibrary.select('scenes'); FigureStudioLibrary.getState()")
        self.check('Legacy select scenes API aliases to Templates', state.get('activeView') == 'templates', state)
        self.checkpoint('legacy-alias-verified')

    async def library_surface(self):
        self.checkpoint('library-empty-figure-entry')
        await self.enter(name='Scientific Assets and Templates acceptance')
        self.checkpoint('library-template-wait')
        await self.frame.locator('#figureLibraryTab-templates').click()
        await self.frame.wait_for_function('FigureStudio.app.getScientificSceneStateForQa().scenes.length>=20')
        await self.frame.wait_for_function('document.querySelectorAll(".scientific-scene-entry").length>=20')
        self.checkpoint('library-cards-ready')
        tabs = await self.frame.locator('#figureLibraryTabs [role="tab"]').evaluate_all('els=>els.map(e=>e.id)')
        self.check('Library exposes only Assets and Templates tabs', tabs == ['figureLibraryTab-assets', 'figureLibraryTab-templates'], tabs)
        self.check('Scientific and layout details start collapsed',
                   await self.frame.locator('#figureLayoutPresets').evaluate('(e)=>!e.open') and
                   await self.frame.locator('.scientific-scene-notes[open]').count() == 0)
        counts = await self.frame.evaluate("""()=>({scenes:[...document.querySelectorAll('.scientific-scene-entry')].length,
          layouts:document.querySelectorAll('#figureLayoutPresets [data-template-id]').length,
          summaries:[...document.querySelectorAll('.scientific-scene-entry .scientific-scene-copy > p')].map(e=>e.textContent.trim())})""")
        self.check('Templates view includes scientific cards and three layout starters', counts['scenes'] >= 20 and counts['layouts'] == 3, counts)
        self.check('Default template summaries stay concise', all(len(s) <= 110 for s in counts['summaries']), counts['summaries'])
        self.check('Each scene card has a visible preview and Insert action', await self.frame.evaluate("""()=>[...document.querySelectorAll('.scientific-scene-entry')].every(card=>{
          const img=card.querySelector('img'), button=card.querySelector('button[data-scene-action="insert_current_document"]');
          if(!img||!button)return false;
          const c=card.getBoundingClientRect(),i=img.getBoundingClientRect(),b=button.getBoundingClientRect();
          return button.offsetParent!==null&&img.offsetParent!==null&&i.width>0&&b.width>0&&
            i.left>=c.left-1&&i.right<=c.right+1&&b.left>=c.left-1&&b.right<=c.right+1&&
            i.top>=c.top-1&&i.bottom<=c.bottom+1&&b.top>=c.top-1&&b.bottom<=c.bottom+1;
        })"""))
        preview_decode = []
        cards = self.frame.locator('.scientific-scene-entry')
        for index in range(counts['scenes']):
            card = cards.nth(index)
            preview = card.locator('img')
            scene_id = await card.get_attribute('data-scene-id')
            state_reader = 'i=>({src:i.src,currentSrc:i.currentSrc,loading:i.loading,complete:i.complete,naturalWidth:i.naturalWidth,naturalHeight:i.naturalHeight})'
            before = await preview.evaluate(state_reader)
            record = {'sceneId': scene_id, 'index': index, 'before': before, 'status': 'started'}
            self.case.setdefault('previewDecodes', []).append(record)
            self.checkpoint('template-preview-start', record)
            async def reveal_and_decode():
                await card.scroll_into_view_if_needed(timeout=12000)
                await preview.wait_for(state='visible', timeout=12000)
                return await preview.evaluate('i=>i.decode().then(()=>[i.naturalWidth,i.naturalHeight])')
            try:
                dimensions = await asyncio.wait_for(reveal_and_decode(), timeout=12)
            except Exception as error:
                after = None
                with contextlib.suppress(Exception):
                    after = await asyncio.wait_for(preview.evaluate(state_reader), timeout=2)
                record.update(status='failed', after=after, errorType=type(error).__name__, error=str(error))
                self.checkpoint('template-preview-end', record)
                raise AssertionError(f'{scene_id}: visible preview failed its12s bound: {record}') from error
            preview_decode.append(dimensions)
            record.update(status='decoded', dimensions=dimensions, after=await preview.evaluate(state_reader))
            self.checkpoint('template-preview-end', record)
        await self.frame.locator('#templateCollectionGrid').evaluate('e=>e.scrollTop=0')
        self.check('Every scientific preview fully decodes', len(preview_decode) == counts['scenes'] and all(min(size) > 0 for size in preview_decode), preview_decode)
        self.checkpoint('all-template-previews-decoded', {'count': len(preview_decode)})
        overflow = await self.frame.evaluate("""()=>({page:document.documentElement.scrollWidth<=innerWidth+1,
          panel:(()=>{const e=document.querySelector('#templateCollectionGrid');return !e||e.scrollWidth<=e.clientWidth+1})()})""")
        self.check('Templates view has no horizontal overflow', all(overflow.values()), overflow)
        await self.frame.locator('#sceneSearchInput').fill('immunoblot')
        self.check('Shared search finds legacy scientific templates', await self.frame.locator(f'.scientific-scene-entry[data-scene-id="{LEGACY_SCENE}"]').is_visible())
        await self.frame.locator('#sceneSearchInput').fill('RT-qPCR')
        self.check('Shared search filters scientific templates by their authored title',
                   await self.frame.locator('.scientific-scene-entry[data-scene-id="rt-qpcr-expression-workflow"]').is_visible() and
                   await self.frame.locator('.scientific-scene-entry:visible').count() == 1)
        await self.frame.locator('#sceneSearchInput').fill('multi-panel')
        self.check('Shared search finds the three layout starters', await self.frame.locator('#figureLayoutPresets [data-template-id="multi-panel-2x2"]').is_visible())
        await self.frame.locator('#sceneSearchInput').fill('')
        await self.frame.locator('#figureLayoutPresets').evaluate('(e)=>e.open=true')
        self.check('Layout starter details can be expanded', await self.frame.locator('#figureLayoutPresets').evaluate('(e)=>e.open'))
        await self.frame.locator('#figureLayoutPresets').evaluate('(e)=>e.open=false')
        await self.capture('templates-default.png', 'Show the unified Templates view with concise scientific cards, visible previews and Insert actions, plus closed layout starter details.')

    async def insert_scene(self, scene_id):
        self.checkpoint('template-insertion', {'sceneId': scene_id})
        card = self.frame.locator(f'.scientific-scene-entry[data-scene-id="{scene_id}"]')
        await card.wait_for(state='visible')
        button = card.locator('button[data-scene-action="insert_current_document"]')
        await button.scroll_into_view_if_needed()
        before = await self.frame.evaluate('FigureStudio.app.getScientificSceneStateForQa().objects.length')
        await button.click()
        await self.frame.wait_for_function('n=>{const s=FigureStudio.app.getScientificSceneStateForQa();return !s.busy&&s.objects.length>n}', arg=before)
        now = await self.frame.evaluate('FigureStudio.app.getScientificSceneStateForQa()')
        inserted = [o for o in now['objects'] if o.get('scene', {}).get('sceneId') == scene_id]
        self.check(f'{scene_id} inserts editable scene nodes through its visible button', bool(inserted), {'before': before, 'after': len(now['objects'])})
        self.case.setdefault('sceneInsertions', []).append({'sceneId': scene_id, 'objectCount': len(inserted)})
        styles=await self.frame.evaluate("""rows=>rows.filter(r=>r.assetId).map(r=>({id:r.figureId,style:FigureStudio.app.getObjectByIdForQa(r.figureId).scientificAssetMeta.art_style}))""", inserted)
        if any(row.get('assetId') for row in inserted):
            self.check(f'{scene_id} uses a coherent original drawing treatment',bool(styles) and all(r['style']=='soft-color' for r in styles),styles)
        return inserted

    async def selected_object_continuity(self, object_id):
        await library.show_library_async(self.frame, tab='tools')
        await self.frame.evaluate('id=>FigureStudio.app.selectObjectsByIdsForQa([id])', object_id)
        selected = await self.frame.evaluate('FigureStudio.app.getSelectionStateForQa().activeObjectId')
        for tab_id in ('figureLibraryTab-assets', 'figureLibraryTab-templates', 'figureLibraryTab-assets', 'figureLibraryTab-templates'):
            await self.frame.locator('#' + tab_id).click()
            after = await self.frame.evaluate('FigureStudio.app.getSelectionStateForQa().activeObjectId')
            self.check('Selected scientific object persists during Library navigation', after == selected, {'before': selected, 'after': after, 'tab': tab_id})

    async def verify_asset_style(self, asset_id, object_id, record, style):
        state = (await self.frame.evaluate(library.STATE, [object_id]))[0]
        meta = state['meta']
        passed = meta.get('art_style') == style and meta.get('originalSvgPath') == record['file']
        evidence = {'assetId': asset_id, 'requestedStyle': style, 'artStyle': meta.get('art_style'),
                    'sourcePath': meta.get('originalSvgPath'), 'expectedSourcePath': record['file'],
                    'importMode': state.get('importMode'), 'primitiveCount': len(native.leaves(state['tree'])),
                    'pathCount': sum(bool(p.get('path')) for p in native.leaves(state['tree']))}
        if style == 'style-4':
            expected_sha = record['_style4']['sha256']
            markup_sha = hashlib.sha256(str(meta.get('originalSvgMarkup') or '').encode('utf8')).hexdigest()
            source = record['_svg'].read_bytes()
            source_sha = hashlib.sha256(source).hexdigest()
            canonical_source = canonical_svg_markup(source.decode('utf8'))
            canonical_markup = canonical_svg_markup(str(meta.get('originalSvgMarkup') or ''))
            passed = passed and meta.get('style_family') == 'superbench-style-4-v1'
            passed = passed and meta.get('artStyleSourceSha256') == expected_sha
            passed = passed and meta.get('originalSvgMarkupStored') is True and bool(meta.get('originalSvgMarkup'))
            passed = passed and source_sha == expected_sha and canonical_markup == canonical_source
            evidence.update({'styleFamily': meta.get('style_family'), 'expectedStyleSourceSha256': expected_sha,
                             'artStyleSourceSha256': meta.get('artStyleSourceSha256'),
                             'embeddedMarkupSha256': markup_sha,
                             'rawSourceSha256': source_sha,
                             'rawMarkupByteMatch': markup_sha == source_sha,
                             'canonicalSourceSha256': hashlib.sha256(canonical_source.encode('utf8')).hexdigest(),
                             'canonicalEmbeddedSha256': hashlib.sha256(canonical_markup.encode('utf8')).hexdigest(),
                             'embeddedContentPolicy': 'Exact parsed SVG canonical content, preserving ordered elements, geometry, paints, regions, text and attributes; XML prefix/serialization differences and comments are non-artwork.',
                             'sourceMarkupStored': meta.get('originalSvgMarkupStored'),
                             'sourceMarkupLength': len(meta.get('originalSvgMarkup') or '')})
        passed = passed and state.get('importMode') != 'raster_fallback' and evidence['primitiveCount'] > 0
        passed = passed and all(p['type'].lower() != 'image' for p in native.leaves(state['tree']))
        self.check(f'{asset_id} inserts bound editable geometry in {STYLE_LABELS[style]} without fallback', passed, evidence)
        self.case.setdefault('styleEvidence', []).append(evidence)
        return state

    async def insert_new_asset(self, asset_id, record, style='soft-color'):
        await library.show_library_async(self.frame, tab='tools')
        await self.frame.locator('#figureLibraryTab-assets').click()
        await self.frame.locator('#assetArtStyleSelect').select_option(style)
        styled_record = self.style4_records[asset_id] if style == 'style-4' else record
        object_id = await super().insert(asset_id, styled_record)
        await self.verify_asset_style(asset_id, object_id, styled_record, style)
        self.case.setdefault('nativeAssetObjectIds', []).append(object_id)
        return object_id

    def paint_facade(self):
        def write(name, value):
            (self.out.parent / name).write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n', encoding='utf8')
        self.case.setdefault('actions', [])
        return SimpleNamespace(OUT=self.out.parent, R=self.report, write=write,
            check=lambda _case, name, passed, detail=None: self.check(name, passed, detail))

    async def paint_bounds(self, object_id):
        return await self.frame.evaluate('id=>{const b=FigureStudio.app.getObjectByIdForQa(id).getBoundingRect();return {left:b.left,top:b.top,width:b.width,height:b.height}}', object_id)

    @staticmethod
    def bounded_solid_probes(lower, color, replacement, bounds, limit=16):
        probes = paint.solid_probes(lower, color, replacement, limit=10000)
        probes = [p for p in probes if bounds['left'] < p['x'] < bounds['left'] + bounds['width']
                  and bounds['top'] < p['y'] < bounds['top'] + bounds['height']]
        if len(probes) < 3:
            raise AssertionError(f'No meaningful owner-scoped solid foreground for {color}: {len(probes)}')
        return probes[::max(1, len(probes) // limit)][:limit]

    async def recolor_region(self, object_id, region, color, *, natural_paint=False, reference_id=None):
        await self.frame.evaluate('id=>FigureStudio.app.selectObjectsByIdsForQa([id])', object_id)
        field = self.frame.locator(f'#scientificAssetColorList [data-asset-color-region="{region}"]')
        if not await field.is_visible():
            advanced = self.frame.locator('[data-figure-layout-choice="advanced"]')
            if await advanced.count() and await advanced.is_visible():
                await advanced.click()
            style = self.frame.locator('#figureStyleToggle')
            if await style.count() and await style.get_attribute('aria-pressed') != 'true':
                await style.click()
            properties = self.frame.locator('[data-inspector-tab="properties"]')
            if await properties.count() and await properties.is_visible():
                await properties.click()
        await field.wait_for(state='visible')
        async def action():
            await field.evaluate('(input,color)=>{input.value=color;input.dispatchEvent(new Event("change",{bubbles:true}))}', color)
        if natural_paint:
            await paint.frames(self.frame)
            state_before = (await self.frame.evaluate(library.STATE, [object_id]))[0]
            entry = next(r for r in state_before['meta']['editableColorRegions'] if r['id'] == region)
            old = state_before['meta'].get('colorOverrides', {}).get(region, entry['default'])
            self.check('Natural part-color witness requests a different high-contrast paint', old.lower() != color.lower())
            lower = await self.frame.evaluate(paint.LOWER, object_id)
            probes = self.bounded_solid_probes(lower, old, color, await self.paint_bounds(object_id))
            reference = (await self.frame.evaluate(library.STATE, [reference_id]))[0]
            protected_entry = next(r for r in reference['meta']['editableColorRegions'] if r['id'] == region)
            protected_color = reference['meta'].get('colorOverrides', {}).get(region, protected_entry['default'])
            probes += self.bounded_solid_probes(lower, protected_color, protected_color, await self.paint_bounds(reference_id), limit=3)
            await paint.observe(self.paint_facade(), self.frame, self.page, self.case, self.out,
                'new-asset-part-color', [object_id, reference_id],
                f"return app.getObjectByIdForQa(rows[0].id).scientificAssetMeta.colorOverrides?.[{json.dumps(region)}]?.toLowerCase()==={json.dumps(color.lower())};",
                {'type': 'change', 'selector': f'[data-asset-color-region="{region}"]'}, action,
                rectangles=False, probes=probes, unchangedIds=[reference_id])
        else:
            await action()
        await self.frame.wait_for_function('([id,r,c])=>FigureStudio.app.getObjectByIdForQa(id)?.scientificAssetMeta.colorOverrides?.[r]?.toLowerCase()===c', arg=[object_id, region, color.lower()])
        state = (await self.frame.evaluate(library.STATE, [object_id]))[0]
        bound = [leaf for leaf in native.leaves(state['tree']) if region in leaf.get('regionPaints', {})]
        self.check('Named color control changes the bound native part', bool(bound) and all(
            str(leaf[channel]).lower() == color.lower()
            for leaf in bound for channel in leaf['regionPaints'][region]),
            {'assetId': state['assetId'], 'region': region, 'boundPrimitives': len(bound), 'color': color})

    async def replacement_paint_probes(self, object_id, reference_id, region, color):
        """Admit target-specific foreground from the existing visible paired form."""
        lower = await self.frame.evaluate(paint.LOWER, object_id)
        source_bounds, target_bounds = await self.paint_bounds(object_id), await self.paint_bounds(reference_id)
        candidates = self.bounded_solid_probes(lower, color, color, target_bounds, limit=64)
        image = Image.open(io.BytesIO(base64.b64decode(lower['png'].split(',', 1)[1]))).convert('RGBA')
        expected = [int(color[i:i+2], 16) for i in (1, 3, 5)]
        v = lower['vpt']; mapped = []
        for p in candidates:
            x = source_bounds['left'] + (p['x'] - target_bounds['left']) / target_bounds['width'] * source_bounds['width']
            y = source_bounds['top'] + (p['y'] - target_bounds['top']) / target_bounds['height'] * source_bounds['height']
            px = math.floor((v[0] * x + v[4]) * lower['width'] / lower['cw'] + .5)
            py = math.floor((v[3] * y + v[5]) * lower['height'] / lower['ch'] + .5)
            if min(px, py) < 1 or px >= image.width - 1 or py >= image.height - 1:
                continue
            # Old pixels must fail at the very foreground footprint being tested.
            if any(any(abs(image.getpixel((px+dx, py+dy))[i] - expected[i]) > 2 for i in range(3))
                   or image.getpixel((px+dx, py+dy))[3] != 255
                   for dx in (-1, 0, 1) for dy in (-1, 0, 1)):
                mapped.append({'x': x, 'y': y, 'rgb': expected})
        self.check('Form repaint witness has target foreground absent from the old form', len(mapped) >= 3,
                   {'sourceBounds': source_bounds, 'targetBounds': target_bounds, 'heldOutTargetForegroundProbes': len(mapped)})
        mapped = mapped[::max(1, len(mapped) // 16)][:16]
        self.case['formPaintAdmission'] = {'sourceObjectId': object_id, 'referenceObjectId': reference_id,
            'region': region, 'color': color, 'sourceBounds': source_bounds, 'targetBounds': target_bounds,
            'oldPixelMismatchProbes': mapped, 'referencePng': paint.png(self.out, 'form-reference-before.png', lower['png'])}
        return mapped + candidates[:3]

    async def replacement_acceptance(self, pairs, records, object_by_asset=None, *, natural_paint=True, pair_index_offset=0):
        await library.show_library_async(self.frame, tab='tools')
        for pair_index, (pack, concept, forms) in enumerate(pairs, start=pair_index_offset):
            first, second = forms
            paint_pair = first['id'].startswith('tissue.adipose.')
            object_id = (object_by_asset or {}).get(first['id'])
            if not object_id:
                object_id = await self.insert_new_asset(first['id'], records[first['id']])
            await self.frame.evaluate('id=>FigureStudio.app.selectObjectsByIdsForQa([id])', object_id)
            before = await self.frame.evaluate("""id=>{const o=FigureStudio.app.getObjectByIdForQa(id),b=o.getBoundingRect();
              return {id:o.figureId,left:o.left,top:o.top,angle:o.angle,width:o.getScaledWidth(),height:o.getScaledHeight(),
                bounds:{left:b.left,top:b.top,width:b.width,height:b.height}};}""", object_id)
            state_before = (await self.frame.evaluate(library.STATE, [object_id]))[0]
            siblings = {r['id'] for r in second.get('editable_color_regions', [])}
            color_region = next((r['id'] for r in state_before['meta']['editableColorRegions']
                                 if r['id'] != 'outline' and r['id'] in siblings), None)
            self.check(f'{pack}/{concept} replacement pair shares an editable biological part', bool(color_region), {'first': first['id'], 'second': second['id'], 'common': sorted(siblings & {r['id'] for r in state_before['meta']['editableColorRegions']})})
            if color_region:
                custom_color = '#277da8' if paint_pair else '#8064a2'
                existing = state_before['meta'].get('colorOverrides', {}).get(color_region, '').lower()
                if existing != custom_color:
                    await self.recolor_region(object_id, color_region, custom_color)
            if paint_pair and natural_paint:
                reference_id = object_by_asset[second['id']]
                await self.recolor_region(reference_id, color_region, custom_color)
                await self.frame.evaluate('id=>FigureStudio.app.selectObjectsByIdsForQa([id])', object_id)
            # Open Change drawing through its ordinary inspector button, then
            # choose the other form in the actual Change drawing dialog.
            await library.show_library_async(self.frame, tab='tools')
            await self.frame.locator('#figureLibraryTab-assets').click()
            target_style = ART_STYLES[(pair_index + 1) % len(ART_STYLES)]
            if paint_pair:
                self.check('Natural form witness uses the existing Style 4 paired reference', target_style == 'style-4')
            await self.frame.locator('#assetArtStyleSelect').select_option(target_style)
            selected_style = await self.frame.locator('#assetArtStyleSelect').input_value()
            self.check(f'{pack}/{concept} Change drawing uses the selected {STYLE_LABELS[target_style]} treatment', selected_style == target_style)
            await self.frame.locator('#replaceScientificAssetBtn').click()
            dialog = self.frame.locator('#assetPreviewDialog[open]')
            await dialog.wait_for(state='visible')
            await self.frame.locator('#assetPreviewStatus').wait_for(state='visible')
            await self.frame.locator('#assetPreviewSearchInput').fill(second.get('scientific_name') or second['name'])
            variant = self.frame.locator('#assetPreviewVariantSelect')
            await self.frame.wait_for_function('id=>[...document.querySelectorAll("#assetPreviewVariantSelect option")].some(o=>o.value===id)', arg=second['id'])
            await variant.select_option(second['id'])
            replace_button = self.frame.locator('#assetPreviewReplaceSelectedBtn')
            await replace_button.wait_for(state='visible')
            allow_edited = self.frame.locator('#assetPreviewAllowEdited')
            if await allow_edited.is_visible() and not await allow_edited.is_checked():
                await allow_edited.check()
            await self.frame.wait_for_function("!document.querySelector('#assetPreviewReplaceSelectedBtn')?.disabled")
            if paint_pair and natural_paint:
                probes = await self.replacement_paint_probes(object_id, reference_id, color_region, custom_color)
                await paint.observe(self.paint_facade(), self.frame, self.page, self.case, self.out,
                    'new-asset-style4-form-switch', [object_id, reference_id],
                    f"const meta=app.getObjectByIdForQa(rows[0].id).scientificAssetMeta;return meta.assetId==={json.dumps(second['id'])} && meta.art_style==='style-4' && meta.colorOverrides?.[{json.dumps(color_region)}]?.toLowerCase()==={json.dumps(custom_color)};",
                    {'type': 'click', 'selector': '#assetPreviewReplaceSelectedBtn'}, replace_button.click,
                    rectangles=False, probes=probes, unchangedIds=[reference_id])
            else:
                await replace_button.click()
            await self.frame.wait_for_function('([id,asset])=>FigureStudio.app.getObjectByIdForQa(id)?.scientificAssetMeta.assetId===asset', arg=[object_id, second['id']])
            styled_second = self.style4_records[second['id']] if target_style == 'style-4' else second
            await self.verify_asset_style(second['id'], object_id, styled_second, target_style)
            after = await self.frame.evaluate("""id=>{const o=FigureStudio.app.getObjectByIdForQa(id),b=o.getBoundingRect();
              return {id:o.figureId,left:o.left,top:o.top,angle:o.angle,width:o.getScaledWidth(),height:o.getScaledHeight(),
                bounds:{left:b.left,top:b.top,width:b.width,height:b.height}};}""", object_id)
            transform_fields = ('left', 'top', 'angle', 'width', 'height')
            pose_preserved = after['id'] == before['id'] and all(abs(float(after[k])-float(before[k])) < .01 for k in transform_fields)
            for key in ('left', 'top', 'width', 'height'):
                pose_preserved = pose_preserved and abs(float(after['bounds'][key])-float(before['bounds'][key])) < .01
            self.check(f'{pack}/{concept} replacement keeps object identity, pose and visible bounds', pose_preserved, {'before': before, 'after': after})
            after_state = (await self.frame.evaluate(library.STATE, [object_id]))[0]
            bound = [leaf for leaf in native.leaves(after_state['tree']) if color_region in leaf.get('regionPaints', {})]
            paint_preserved = bool(bound) and all(str(leaf[channel]).lower() == custom_color
                                                   for leaf in bound for channel in leaf['regionPaints'][color_region])
            self.check(f'{pack}/{concept} replacement carries compatible custom color',
                       after_state['meta'].get('colorOverrides', {}).get(color_region, '').lower() == custom_color and paint_preserved,
                       {'region': color_region, 'overrides': after_state['meta'].get('colorOverrides', {}), 'nativePaintPreserved': paint_preserved})
            self.case.setdefault('formReplacements', []).append({'pack': pack, 'concept': concept, 'from': first['id'], 'to': second['id'], 'objectId': object_id})

    async def all_asset_acceptance(self, new_records, pairs, style4_records):
        ids = []
        region_count = 0
        object_by_asset = {}
        pair_regions = {forms[0]['id']: {r['id'] for r in forms[1].get('editable_color_regions', [])}
                        for _pack, _concept, forms in pairs}
        for asset_id, record in sorted(new_records.items()):
            self.checkpoint('style4-asset-editing', {'assetId': asset_id, 'completedEditableParts': region_count})
            object_id = await self.insert_new_asset(asset_id, record, 'style-4')
            ids.append(object_id)
            object_by_asset[asset_id] = object_id
            state = (await self.frame.evaluate(library.STATE, [object_id]))[0]
            for index, region in enumerate(state['meta']['editableColorRegions']):
                color = ('#8064a2' if asset_id in pair_regions and region['id'] in pair_regions[asset_id]
                         else ['#2f7f9f', '#9161a8', '#b26b37', '#4e8a60'][region_count % 4])
                await self.recolor_region(object_id, region['id'], color)
                region_count += 1
        self.check('All 40 new Assets insert as editable native drawings', len(ids) == 40, len(ids))
        expected_regions = sum(len(x.get('editable_color_regions', [])) for x in style4_records.values())
        observed_style4 = [row['assetId'] for row in self.case.get('styleEvidence', []) if row['requestedStyle'] == 'style-4']
        self.check('Every editable part across all 40 new Style 4 drawings is recolored once',
                   region_count == expected_regions and len(ids) == 40 and len(object_by_asset) == 40
                   and len(observed_style4) == 40 and set(observed_style4) == set(new_records),
                   {'assetCount': len(ids), 'nativeStyle4Count': len(observed_style4), 'recolored': region_count, 'expectedRegions': expected_regions})
        self.case['allNewAssetsStyle4'] = {'count': len(ids), 'recoloredEditableParts': region_count}
        await self.frame.evaluate("""ids=>ids.forEach((id,at)=>{const o=FigureStudio.app.getObjectByIdForQa(id);
          o.scaleToWidth(54);if(o.getScaledHeight()>50)o.scaleToHeight(50);
          o.set({originX:'center',originY:'center',left:36+(at%8)*78,top:42+Math.floor(at/8)*74});o.setCoords();o.canvas.requestRenderAll();})""", ids)
        await self.capture('all-new-assets.png', 'Show the complete 40-drawing neurobiology and tissue vascular asset set in the authoring document with selected editable artwork.')
        return object_by_asset

    async def representative_assets_acceptance(self, pairs, records):
        object_by_asset = {}
        ids = []
        for pair_index, (_pack, _concept, forms) in enumerate(pairs):
            for form_index, record in enumerate(forms):
                style = ART_STYLES[(pair_index + form_index) % len(ART_STYLES)]
                object_id = await self.insert_new_asset(record['id'], records[record['id']], style)
                object_by_asset[record['id']] = object_id
                ids.append(object_id)
        await self.frame.evaluate("""ids=>ids.forEach((id,at)=>{const o=FigureStudio.app.getObjectByIdForQa(id);
          o.scaleToWidth(86);if(o.getScaledHeight()>68)o.scaleToHeight(68);
          o.set({originX:'center',originY:'center',left:58+(at%4)*136,top:76+Math.floor(at/4)*136});o.setCoords();o.canvas.requestRenderAll();})""", ids)
        observed_styles = {style: sum(1 for row in self.case.get('styleEvidence', []) if row['requestedStyle'] == style)
                           for style in ART_STYLES}
        self.check('Per-case editable assets cover four paired concepts and all four art styles',
                   len(ids) == 8 and len(object_by_asset) == 8 and all(observed_styles[style] >= 2 for style in ART_STYLES),
                   {'pairs': [{'pack': pack, 'concept': concept, 'forms': [r['id'] for r in forms]} for pack, concept, forms in pairs],
                    'styleCountsIncludingReplacements': observed_styles})
        return object_by_asset, ids

    async def verify_style_coverage(self):
        await self.frame.locator('#figureLibraryTab-assets').click()
        style = self.frame.locator('#assetArtStyleSelect')
        options = await style.evaluate('select=>[...select.options].map(o=>({value:o.value,disabled:o.disabled,label:o.textContent.trim()}))')
        expected = {'soft-color', 'cut-paper', 'technical-ink', 'style-4'}
        self.check('All four art-style choices are visible and enabled',
                   expected <= {x['value'] for x in options if not x['disabled']}, options)
        await style.select_option('style-4')
        self.check('New four-style drawings accept actual Style 4 selection',
                   await style.input_value() == 'style-4',
                   {'value': await style.input_value()})

    async def edit_scene_live_content(self, scene_id, inserted):
        asset_object = next((o for o in inserted if o.get('assetId')), None)
        if asset_object:
            object_id = asset_object['figureId']
            state = (await self.frame.evaluate(library.STATE, [object_id]))[0]
            regions = state['meta'].get('editableColorRegions', [])
            self.check(f'{scene_id} contains a named editable biological part', bool(regions), [r['id'] for r in regions])
            await self.recolor_region(object_id, regions[0]['id'], '#537ca4')
        text_candidate = None
        for row in inserted:
            state = (await self.frame.evaluate(MIXED_SCENE_STATE, [row['figureId']]))[0]
            labels = [leaf for leaf in native.leaves(state['tree']) if isinstance(leaf.get('text'), str) and leaf['text'].strip()]
            if labels:
                text_candidate = (row['figureId'], labels[0]['id'], labels[0]['text'])
                break
        self.check(f'{scene_id} exposes a native live text label', text_candidate is not None)
        root_id, text_id, previous = text_candidate
        if root_id != text_id:
            entered = await self.frame.evaluate('([g,c])=>FigureStudio.app.enterGroupIsolationForQa({groupId:g,childId:c})', [root_id, text_id])
            self.check(f'{scene_id} label group opens for editing', bool(entered and entered.get('entered')), entered)
            selected = await self.frame.evaluate('id=>FigureStudio.app.selectGroupIsolationChildForQa({objectId:id})', text_id)
            self.check(f'{scene_id} live label selects inside its group', bool(selected and selected.get('selected')), selected)
        else:
            await self.frame.evaluate('id=>FigureStudio.app.selectObjectsByIdsForQa([id])', text_id)
        control = self.frame.locator('#appearanceStructureInspector [data-context-property="text"]')
        await control.wait_for(state='visible')
        revised = previous + ' edited'
        await control.evaluate('(e,v)=>{e.value=v;e.dispatchEvent(new Event("change",{bubbles:true}))}', revised)
        await self.frame.wait_for_function('([id,v])=>FigureStudio.app.getObjectByIdForQa(id)?.text===v', arg=[text_id, revised])
        self.check(f'{scene_id} visible text control edits the live label',
                   await self.frame.evaluate('id=>FigureStudio.app.getObjectByIdForQa(id)?.text', text_id) == revised,
                   {'id': text_id, 'before': previous, 'after': revised})
        self.case['templateLiveTextEdit'] = {'sceneId': scene_id, 'objectId': text_id, 'before': previous, 'after': revised}
        await self.frame.evaluate('FigureStudio.app.exitGroupIsolationForQa()')

    async def insert_scene_clean(self, scene_id, *, save_roundtrip=False, capture_prefix='template', cold_diagnostic=False):
        await self.frame.locator('#figureLibraryTab-templates').click()
        inserted = await self.insert_scene(scene_id)
        if scene_id != LEGACY_SCENE:
            await self.edit_scene_live_content(scene_id, inserted)
        await self.selected_object_continuity(inserted[0]['figureId'])
        await self.capture(f'{capture_prefix}-{scene_id}.png', f'Show the editable {scene_id} scientific template on a clean Figure canvas with readable labels and visible Library controls.')
        all_ids = [row['figureId'] for row in inserted]
        if save_roundtrip:
            if cold_diagnostic:
                await self.save_and_cold_open_diagnostic(all_ids, f'{scene_id}.fsfigure', prefix=capture_prefix)
            else:
                await self.save_and_cold_open(all_ids, f'{scene_id}.fsfigure', prefix=capture_prefix, mixed_scene=True)
        return inserted

    async def cold_open_for_first_capture(self, path):
        """Use the actual file chooser but defer all document/native snapshots."""
        await self.launch()
        await self.enter(name='Cold file Open')
        await public_repaint.open_native(self.frame, self.page, path)

    async def save_and_cold_open(self, ids, filename, *, prefix, mixed_scene=False):
        await self.save_and_cold_open_diagnostic(
            ids, filename, prefix=prefix, mixed_scene=mixed_scene,
            scope='mixed-scene' if mixed_scene else 'asset-cohort')

    async def save_and_cold_open_diagnostic(self, ids, filename, *, prefix,
                                            mixed_scene=True, scope='qPCR-only'):
        """Retain warm/file/cold evidence before unchanged preservation checks."""
        self.checkpoint('actual-file-save', {'file': filename, 'objectCount': len(ids), 'scope': scope})
        snapshot = MIXED_SCENE_STATE if mixed_scene else library.STATE
        before = None
        warm_snapshot_error = None
        try:
            before = await self.frame.evaluate(snapshot, ids)
        except Exception as error:
            warm_snapshot_error = {'errorType': type(error).__name__, 'error': str(error)}
        selected = await self.frame.evaluate('FigureStudio.app.getSelectionStateForQa().activeObjectId')
        saved_path, saved_doc = await self.save(filename)
        downloaded_doc = json.loads(saved_path.read_text(encoding='utf8'))
        file_sha256 = hashlib.sha256(saved_path.read_bytes()).hexdigest()
        self.case.setdefault('downloads', []).append({'file': saved_path.name,
            'bytes': saved_path.stat().st_size, 'sha256': file_sha256})
        self.write(f'{prefix}-warm-serialize.json', saved_doc)
        self.write(f'{prefix}-actual-file-payload.json', downloaded_doc)
        if before is None:
            self.write(f'{prefix}-warm-native-error.json', warm_snapshot_error)
        else:
            self.write(f'{prefix}-warm-native-before-save.json', before)
        await self.capture(f'{prefix}-pre-cold-open.png', 'Show the authored scientific figure immediately before opening its actual saved fsfigure in a fresh browser context.')
        self.checkpoint('actual-cold-file-open', {'file': filename, 'sha256': file_sha256, 'scope': scope})
        await self.cold_open_for_first_capture(saved_path)
        self.checkpoint('actual-cold-file-open-complete', {'file': filename, 'scope': scope})
        await self.capture(f'{prefix}-cold-open.png', 'Show the first restored scientific figure immediately after actual Open, before serialization, native inspection, Fit, zoom or selection changes.')

        opened_doc = None
        cold_serialize_error = None
        try:
            opened_doc = await self.frame.evaluate('FigureStudio.app.serializeCurrentDocumentForQa({markSaved:false})')
        except Exception as error:
            cold_serialize_error = {'errorType': type(error).__name__, 'error': str(error)}
            self.write(f'{prefix}-cold-serialize-error.json', cold_serialize_error)
        self.write(f'{prefix}-cold-serialize.json', opened_doc)
        after = None
        cold_snapshot_error = None
        try:
            after = await self.frame.evaluate(snapshot, ids)
        except Exception as error:
            cold_snapshot_error = {'errorType': type(error).__name__, 'error': str(error)}
        if after is None:
            self.write(f'{prefix}-cold-native-error.json', cold_snapshot_error)
        else:
            self.write(f'{prefix}-cold-native-after-open.json', after)

        payloads = {'warm': saved_doc, 'file': downloaded_doc, 'cold': opened_doc}
        thumbnail_bytes = []
        for label, payload in payloads.items():
            project = payload.get('project') if isinstance(payload, dict) else None
            self.write(f'{prefix}-{"actual-file" if label == "file" else label}-fabric.json',
                       project.get('fabric') if isinstance(project, dict) else None)
            pages = project.get('deck', {}).get('pages', []) if isinstance(project, dict) else []
            for index, page in enumerate(pages):
                record = {'payload': label, 'pageIndex': index}
                try:
                    header, encoded = page['thumbnail'].split(',', 1)
                    raw = base64.b64decode(encoded, validate=True)
                    name = f'{prefix}-{label}-page-{index + 1:02d}-thumbnail.png'
                    (self.out / name).write_bytes(raw)
                    record.update(path=name, dataUrlHeader=header, bytes=len(raw),
                                  sha256=hashlib.sha256(raw).hexdigest())
                except Exception as error:
                    record.update(errorType=type(error).__name__, error=str(error))
                thumbnail_bytes.append(record)
        self.write(f'{prefix}-embedded-thumbnail-bytes.json', thumbnail_bytes)

        authored, authored_errors = {}, {}
        for label, payload in payloads.items():
            try:
                authored[label] = native.authored_document(payload)
            except Exception as error:
                authored[label] = None
                authored_errors[label] = {'errorType': type(error).__name__, 'error': str(error)}
        pair_diffs = {}
        for suffix, left, right in [('warm-to-file', 'warm', 'file'),
                                    ('warm-to-cold', 'warm', 'cold'),
                                    ('file-to-cold', 'file', 'cold')]:
            errors = {key: authored_errors[key] for key in (left, right) if key in authored_errors}
            result = {
                'raw': {'exact': public_repaint.exact_differences(payloads[left], payloads[right]),
                        'missingOrExtraKeys': key_presence_differences(payloads[left], payloads[right])},
                'maintainedAuthored': {
                    'exact': public_repaint.exact_differences(authored[left], authored[right]) if not errors else None,
                    'missingOrExtraKeys': key_presence_differences(authored[left], authored[right]) if not errors else None},
                'authoredComparisonErrors': errors,
                'authoredEqual': not errors and authored[left] == authored[right],
            }
            pair_diffs[suffix] = result
            self.write(f'{prefix}-{suffix}-differences.json', result)
        try:
            thumbs = native.thumbnail_difference(saved_doc, opened_doc)
            thumbnail_error = None
        except Exception as error:
            thumbs = [{'passed': False, 'errorType': type(error).__name__, 'error': str(error)}]
            thumbnail_error = {'errorType': type(error).__name__, 'error': str(error)}
        raw_native_diffs = raw_native_keys = None
        if before is not None and after is not None:
            raw_native_diffs = public_repaint.exact_differences(before, after)
            raw_native_keys = key_presence_differences(before, after)
            try:
                native_diff = native.native_reconstruction_difference(before, after)
            except Exception as error:
                native_diff = {'passed': False, 'mismatches': ['native-comparator-error'],
                               'errorType': type(error).__name__, 'error': str(error)}
        else:
            native_diff = {'passed': False, 'mismatches': ['warm-or-cold-native-snapshot-unavailable'],
                           'warmSnapshotError': warm_snapshot_error, 'coldSnapshotError': cold_snapshot_error}
        self.write(f'{prefix}-native-and-thumbnail-differences.json', {
            'native': native_diff, 'rawNative': raw_native_diffs, 'nativeMissingOrExtraKeys': raw_native_keys,
            'thumbnail': thumbs, 'thumbnailError': thumbnail_error,
            'coldSerializeError': cold_serialize_error,
        })
        self.checkpoint('warm-file-cold-diagnostics-written', {
            'file': filename, 'fileSha256': file_sha256, 'bytes': saved_path.stat().st_size,
            'warmNativeSnapshotAvailable': before is not None,
            'coldNativeSnapshotAvailable': after is not None,
            'authoredDifferenceCounts': {name: (
                len(pair_diffs[key]['maintainedAuthored']['exact']) + len(pair_diffs[key]['maintainedAuthored']['missingOrExtraKeys'])
                if not pair_diffs[key]['authoredComparisonErrors'] else None)
                for name, key in [('warmToFile', 'warm-to-file'), ('warmToCold', 'warm-to-cold'),
                                  ('fileToCold', 'file-to-cold')]},
            'authoredComparisonErrors': authored_errors,
        })

        # All available payloads, native states, original PNGs and diffs are durable.
        self.check('Actual File Save writes an fsfigure file', saved_path.is_file() and saved_path.suffix == '.fsfigure', str(saved_path))
        self.check('Warm native snapshot is available before Save', before is not None, warm_snapshot_error)
        def detail(key):
            row = pair_diffs[key]
            fields = row['maintainedAuthored']
            return {'differenceCount': len(fields['exact'] or []) + len(fields['missingOrExtraKeys'] or []),
                    'authoredComparisonErrors': row['authoredComparisonErrors'],
                    'artifact': f'{prefix}-{key}-differences.json'}
        self.check('Actual downloaded file contains the complete authored figure', pair_diffs['warm-to-file']['authoredEqual'], detail('warm-to-file'))
        self.check('Cold native snapshot is available after first capture', after is not None, cold_snapshot_error)
        self.check('Cold Open preserves every authored document field and ID', pair_diffs['warm-to-cold']['authoredEqual'], detail('warm-to-cold'))
        self.check('Actual file and cold Open preserve every authored document field and ID', pair_diffs['file-to-cold']['authoredEqual'], detail('file-to-cold'))
        self.check('Cold Open preserves document thumbnail pixels', all(x['passed'] for x in thumbs), thumbs)
        self.check('Cold Open preserves native vectors, bindings and IDs', native_diff['passed'], native_diff)
        self.case.setdefault('coldOpens', []).append({'file': str(saved_path), 'selectedBeforeSave': selected, 'nativeDifference': native_diff})


async def run(args):
    global TARGET, RUNTIME_ROOT
    TARGET = FigureQaTarget.from_arguments(ROOT, args.package_root, args.package_sha256)
    RUNTIME_ROOT = TARGET.runtime_root
    library.TARGET = TARGET
    library.RUNTIME_ROOT = RUNTIME_ROOT
    validate_stop_scope(args.stop_after, args.case, TARGET.package_root)
    out = args.output_dir.resolve()
    out.relative_to(ROOT / 'qa_artifacts')
    out.mkdir(parents=True, exist_ok=False)
    report = {'status': 'running', 'sourceRoot': str(ROOT), 'runtimeTarget': TARGET.record(),
              'sourceIdentity': {}, 'cases': [], 'checks': [], 'captures': [], 'pageErrors': [],
              'consoleErrors': [], 'failedRequests': [], 'vendorResponses': [],
              'matrix': [{'viewport': [w, h], 'theme': t} for w, h in [(1280, 800), (1440, 1000), (1920, 1080)] for t in ('light', 'dark')]}
    server = case = None
    try:
        report['sourceIdentity'] = source_identity()
        report['stopAfter'] = args.stop_after
        report['qualificationScope'] = {
            'kind': 'package-bound Library checks' if TARGET.package_root else 'SOURCE Library pilot for bug finding',
            'releaseOrPackageParityQualified': False,
            'note': 'The canonical dirty source checkout preserves private PDF experiments. Its browser results do not qualify a released package; release qualification requires Root composition from delivered beta22 plus accepted deltas.' if not TARGET.package_root else 'Package byte binding is recorded separately. Root must establish clean release composition and approve the complete matrix.',
            'appSha256': hashlib.sha256((RUNTIME_ROOT / 'app/app.js').read_bytes()).hexdigest(),
            'pdfMaterializerSha256': hashlib.sha256((RUNTIME_ROOT / 'app/pdf-svg-materializer.js').read_bytes()).hexdigest(),
            'templateInsertionScope': (
                [] if args.stop_after == 'library-surface' else
                [NEW_SCENES[0]] if args.stop_after == 'qPCR-roundtrip' else
                [*NEW_SCENES, LEGACY_SCENE]
            ),
            'templateDiscoveryCount': 20,
            'journeyScope': (
                'Discovery only; no insertion, edit, natural-paint or Save/Open qualification' if args.stop_after == 'library-surface' else
                'One RT-qPCR insertion/edit and one actual Save/Open; no other inserted templates or asset cohorts' if args.stop_after == 'qPCR-roundtrip' else
                'Integrated source pilot'
            ),
        }
        if args.stop_after == 'qPCR-roundtrip':
            report['qualificationScope'].update({
                'plannedSaveOpenRoundTrips': 1,
                'completedFileOpenOperations': 0,
                'successfulSaveOpenRoundTrips': 0,
                'plannedOtherTemplateInsertions': 0,
                'completedOtherTemplateInsertions': 0,
                'plannedOtherAssetCohorts': 0,
                'plannedStyle4All40Insertions': 0,
                'plannedPartColorEdits': 1,
                'completedPartColorEdits': 0,
                'plannedLiveTextEdits': 1,
                'completedLiveTextEdits': 0,
                'plannedNaturalPaintWitnesses': 0,
                'note': 'Planned scope: one current-source RT-qPCR insertion/edit and one actual Save/Open, after 20-card discovery. No other templates, asset cohorts, 40-asset Style 4 cohort or natural-paint observer is planned; completed counts are recorded at finalization.',
            })
        report['naturalPaintPolicy'] = {
            'helper': 'scripts/figure_action_paint_qa.py', 'observer': 'scripts/action-paint-observer.js',
            'helperSha256': hashlib.sha256((ROOT / 'scripts/figure_action_paint_qa.py').read_bytes()).hexdigest(),
            'observerSha256': hashlib.sha256((ROOT / 'scripts/action-paint-observer.js').read_bytes()).hexdigest(),
            'scope': ('No natural-paint observer action in the bounded qPCR roundtrip; the qPCR template still receives its named-part color edit.' if args.stop_after == 'qPCR-roundtrip' else
                      'Two actual edits on the existing representative adipocyte pair: high-contrast part color, then final Style4 form-replacement click. Natural pixels are frozen before native serialization, save or screenshots.'),
            'plannedActionsPerCase': 0 if args.stop_after else 2,
            'naturalPaintWitnesses': 0 if args.stop_after else 2,
            'deadlineMs': 250, 'diagnosticMs': 1000, 'stableMs': 80,
            'predicate': 'Unchanged maintained observer: original 3x3 opaque RGBA footprints, RGB tolerance2, three successive correct observations spanning80ms. Target form probes must disagree with old owner pixels and protect the unchanged visible reference.',
        }
        records, new_records = new_asset_records()
        pairs = replacement_pairs(new_records)
        (style4_records, style4_manifest_path, style4_manifest, style4_supplement_path,
         style4_supplement, style4_combined_count, style4_primary_count) = style4_variant_records(new_records)
        pilot_cases = {
            '1280x800-light': ((1280, 800), 'light'), '1280x800-dark': ((1280, 800), 'dark'),
            '1440x1000-light': ((1440, 1000), 'light'), '1440x1000-dark': ((1440, 1000), 'dark'),
            '1920x1080-light': ((1920, 1080), 'light'), '1920x1080-dark': ((1920, 1080), 'dark')}
        selected_cases = list(pilot_cases.items()) if args.case == 'all' else [(args.case, pilot_cases[args.case])]
        report['matrix'] = [{'case': name, 'viewport': list(size), 'theme': theme} for name, (size, theme) in selected_cases]
        report['pilotCase'] = None if args.case == 'all' else args.case
        report['styleParity'] = {'styles': ART_STYLES, 'styleRendererPath': STYLE_RENDERER,
            'styleRendererSha256': hashlib.sha256((RUNTIME_ROOT / STYLE_RENDERER).read_bytes()).hexdigest(),
            'style4ManifestPath': style4_manifest_path.relative_to(RUNTIME_ROOT).as_posix(),
            'style4ManifestSha256': hashlib.sha256(style4_manifest_path.read_bytes()).hexdigest(),
            'style4PrimaryManifestAssetCount': style4_primary_count,
            'style4SupplementPath': style4_supplement_path.relative_to(RUNTIME_ROOT).as_posix(),
            'style4SupplementSha256': hashlib.sha256(style4_supplement_path.read_bytes()).hexdigest(),
            'style4SupplementAssetCount': len(style4_supplement.get('assets', [])),
            'style4CombinedAssetCount': style4_combined_count,
            'style4NewAssetCoverage': len(style4_records),
            'fullStyle4EditScope': 'Not executed in bounded stop-after run' if args.stop_after else 'all 40 new drawings and every rendered semantic color region in 1440x1000-light only'}
        report['roundTripPlan'] = round_trip_plan(args.stop_after, selected_cases)
        server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(native.QuietHandler, directory=str(RUNTIME_ROOT)))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        write_progress(report, out, 'run', 'playwright-driver-launch', {'serverPort': server.server_port})
        async with async_playwright() as pw:
            write_progress(report, out, 'run', 'chromium-launch')
            browser = await pw.chromium.launch()
            write_progress(report, out, 'run', 'chromium-ready')
            for case_label, (size, theme) in selected_cases:
                case = Case(browser, f'http://127.0.0.1:{server.server_port}', 'direct', size, theme, out, report, label=case_label)
                case.style4_records = style4_records
                try:
                    await case.launch()
                    await case.library_surface()
                    case.checkpoint('library-surface-complete')
                    if args.stop_after == 'library-surface':
                        case.case['status'] = 'discovery-passed'
                        continue
                    if size == (1440, 1000) and theme == 'light':
                        await case.frame.locator('.scientific-scene-entry[data-scene-id="rt-qpcr-expression-workflow"] .scientific-scene-notes summary').click()
                        await case.capture('scientific-details-expanded.png', 'Show one expanded Scientific details panel for a scientific template, with the full preview, concise card summary and Insert action visible.')
                        await case.frame.locator('.scientific-scene-entry[data-scene-id="rt-qpcr-expression-workflow"] .scientific-scene-notes summary').click()
                    await case.enter(name='RT-qPCR scientific template')
                    await case.insert_scene_clean(
                        NEW_SCENES[0], save_roundtrip=True,
                        cold_diagnostic=args.stop_after == 'qPCR-roundtrip')
                    if args.stop_after == 'qPCR-roundtrip':
                        case.case['status'] = 'qPCR-roundtrip-passed'
                        case.checkpoint('qPCR-roundtrip-complete', {'sceneId': NEW_SCENES[0], 'completedSaveOpenRoundTrips': 1})
                        continue
                    await case.enter(name='Legacy immunoblot template')
                    await case.insert_scene_clean(LEGACY_SCENE, capture_prefix='legacy-template')
                    if size == (1440, 1000) and theme == 'light':
                        for scene_id in NEW_SCENES[1:]:
                            await case.enter(name=f'{scene_id} scientific template')
                            await case.insert_scene_clean(scene_id)

                    if size == (1440, 1000) and theme == 'light':
                        await case.enter(name='All 40 new drawings in Style 4')
                        await case.verify_style_coverage()
                        all_style4 = await case.all_asset_acceptance(new_records, pairs, style4_records)
                        all_ids = list(all_style4.values())
                        await case.selected_object_continuity(all_ids[-1])
                        await case.save_and_cold_open(all_ids, 'assets-style-4-all40.fsfigure', prefix='assets-style-4-all40')

                    await case.enter(name='Representative drawings in Styles 1–4')
                    await case.verify_style_coverage()
                    object_by_asset, asset_ids = await case.representative_assets_acceptance(pairs, records)
                    for _pack, _concept, forms in pairs:
                        first, second = forms
                        state = (await case.frame.evaluate(library.STATE, [object_by_asset[first['id']]]))[0]
                        common = {r['id'] for r in second.get('editable_color_regions', [])}
                        region = next((r['id'] for r in state['meta']['editableColorRegions'] if r['id'] in common and r['id'] != 'outline'), None)
                        case.check(f'{first["id"]} has a color-compatible paired part', bool(region))
                        if region:
                            paint_pair = first['id'].startswith('tissue.adipose.')
                            await case.recolor_region(object_by_asset[first['id']], region,
                                '#277da8' if paint_pair else '#8064a2', natural_paint=paint_pair,
                                reference_id=object_by_asset[second['id']] if paint_pair else None)
                    await case.replacement_acceptance(pairs, records, object_by_asset)
                    await case.frame.locator('#figureLibraryTab-templates').click()
                    await case.capture('asset-cohort-template-cards.png', 'Show the separate representative four-style scientific asset cohort with selected native artwork and concise Templates cards.')
                    await case.selected_object_continuity(asset_ids[-1])
                    await case.save_and_cold_open(asset_ids, 'asset-cohort-styles-1-to-4.fsfigure', prefix='asset-cohort-styles-1-to-4')
                except BaseException:
                    if case.page and not case.page.is_closed():
                        with contextlib.suppress(Exception):
                            await case.page.screenshot(path=str(case.out / 'failure.png'))
                    raise
                finally:
                    if case.context:
                        case.phase = 'closing-context'
                        with contextlib.suppress(Exception):
                            await case.context.close()
                print(case.name + ' passed', flush=True)
            await browser.close()
        report['sourceIdentityAfter'] = source_identity()
        report['sourceUnchanged'] = report['sourceIdentity'] == report['sourceIdentityAfter']
        report['checks'].append({'case': 'run', 'name': 'All source inputs remain unchanged', 'passed': report['sourceUnchanged']})
        report['requestFailureClassification'] = classify_request_failures(report['failedRequests'])
        report['checks'].append({'case': 'run', 'name': 'No unexplained runtime request failures', 'passed': not report['requestFailureClassification']['unexpected'], 'detail': report['requestFailureClassification']['unexpected']})
        report['checks'].append({'case': 'run', 'name': 'Canonical vendor scripts load successfully', 'passed': bool(report['vendorResponses']) and all(x['status'] == 200 for x in report['vendorResponses'])})
        report['status'] = 'passed' if all(x['passed'] for x in report['checks']) and not report['pageErrors'] and not report['consoleErrors'] else 'failed'
    except BaseException as error:
        report['status'] = 'interrupted' if isinstance(error, (KeyboardInterrupt, asyncio.CancelledError)) else 'failed'
        report['failure'] = str(error)
        report['traceback'] = traceback.format_exc()
        raise
    finally:
        if case and case.context:
            with contextlib.suppress(Exception):
                await case.context.close()
        if server:
            server.shutdown(); server.server_close()
        report['sourceIdentityAfter'] = source_identity()
        report['sourceUnchanged'] = report.get('sourceIdentity') == report['sourceIdentityAfter']
        if args.stop_after == 'qPCR-roundtrip':
            scope = report['qualificationScope']
            qPCR_cases = list(report['cases'])
            scope['completedFileOpenOperations'] = sum(
                1 for row in report.get('progress', [])
                if row.get('phase') == 'actual-cold-file-open-complete'
                and (row.get('detail') or {}).get('scope') == 'qPCR-only'
            )
            scope['successfulSaveOpenRoundTrips'] = sum(
                1 for item in qPCR_cases
                if item.get('status') == 'qPCR-roundtrip-passed'
                and any(Path(opened.get('file', '')).name == 'rt-qpcr-expression-workflow.fsfigure'
                        for opened in item.get('coldOpens', []))
            )
            qPCR_case_names = {item.get('name') for item in qPCR_cases}
            scope['completedPartColorEdits'] = sum(
                1 for check in report.get('checks', [])
                if check.get('case') in qPCR_case_names
                and check.get('name') == 'Named color control changes the bound native part'
                and check.get('passed')
            )
            scope['completedLiveTextEdits'] = sum(1 for item in qPCR_cases if item.get('templateLiveTextEdit'))
            scope['completedOtherTemplateInsertions'] = sum(
                1 for item in qPCR_cases
                for insertion in item.get('sceneInsertions', [])
                if insertion.get('sceneId') != NEW_SCENES[0]
            )
            scope['completedOtherAssetCohorts'] = 0
            scope['completedStyle4All40Insertions'] = 0
            scope['completedNaturalPaintWitnesses'] = 0
        (out / 'report.json').write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n', encoding='utf8')
        print(json.dumps({'status': report['status'], 'checks': len(report['checks']), 'output': str(out)}), flush=True)
    return report_exit_code(report)


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    add_package_arguments(parser)
    parser.add_argument('--output-dir', type=Path, required=True, help='New output directory under qa_artifacts.')
    parser.add_argument('--case', choices=['all', '1280x800-light', '1280x800-dark', '1440x1000-light', '1440x1000-dark', '1920x1080-light', '1920x1080-dark'], default='all', help='Run one bounded desktop case for pilot debugging, or the full six-case matrix.')
    parser.add_argument('--stop-after', choices=['library-surface', 'qPCR-roundtrip'],
                        help='Stop after Library discovery, or after one qPCR warm edit/Save/cold Open (requires one explicit --case).')
    return parser


if __name__ == '__main__':
    raise SystemExit(asyncio.run(run(build_parser().parse_args())))
