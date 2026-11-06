#!/usr/bin/env python3
"""Qualify canonical Library drawing choices, search and editable saved artwork.

Uses the shared editor directly or through its web shell, disposable Chromium
contexts and actual Library/File commands. Installed Windows behavior remains
separate. Evidence stays in Figure qa_artifacts.
Use --package-root with --package-sha256 to qualify an exact extracted tool
package instead of the mutable checkout. The complete payload is verified twice.
"""
from __future__ import annotations

import argparse
import asyncio
import contextlib
import functools
import hashlib
import http.server
import importlib.util
import json
import re
import threading
import traceback
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

from playwright.async_api import async_playwright
from figure_studio_entry_qa import enter_current_document_async, show_library_async
from figure_package_qa import FigureQaTarget, add_package_arguments, classify_request_failures

ROOT = Path(__file__).resolve().parents[1]
TARGET = FigureQaTarget.from_arguments(ROOT)
RUNTIME_ROOT = ROOT
FAMILY_PACKS = ['cell-architecture-transport', 'culture-models-assays', 'microbial-biology']
EXPANSION_PACKS = ['cell-structure-stress', 'tumor-microenvironment', 'analysis-graphics']
EXPANSION_EDIT_REPRESENTATIVES = [
    'cellstress.organelle.primary_cilium.straight',
    'cellstress.cell.pyroptotic_cell.pore_bearing',
    'tme.cancer_associated_fibroblast.matrix',
    'tme.tertiary_lymphoid_structure.germinal_center',
    'tme.hypoxia_gradient.perivascular',
    'analysis.heatmap.clustered',
]

def cohort_packs(kind):
    return EXPANSION_PACKS if kind == 'expansion' else FAMILY_PACKS if kind == 'families' else []

FAMILY_PREDECESSOR = 'revisions/2026-10-13-family-expansion-predecessor'
LEGACY = [
    'core.cell.generic', 'core.cell.epithelial', 'core.cell.neuron_like',
    'core.nucleus.round', 'core.mitochondrion.basic', 'core.golgi.basic',
    'core.er.rough', 'core.lysosome.basic', 'core.antibody.igg',
    'core.receptor.membrane', 'core.protein.enzyme', 'core.protein.kinase',
]
RNA_METHODS = ['rna.lab_equipment.microfluidic_cell_partition',
               'rna.nucleic_acid.barcoded_capture_bead',
               'rna.assay_workflow.spatial_capture_array',
               'rna.assay_workflow.in_situ_rna_puncta']
NEW_ASSETS = [
    'core.cell.generic_spread', 'core.cell.generic_cutaway', 'core.cell.epithelial_apical',
    'core.cell.epithelial_cuboidal', 'core.cell.neuron_bipolar', 'core.cell.neuron_pseudounipolar',
    'core.nucleus.oval_cutaway', 'core.nucleus.envelope_detail', 'core.mitochondrion.tubular',
    'core.mitochondrion.network', 'core.golgi.oblique', 'core.golgi.ribbon', 'core.er.rough_network',
    'core.er.smooth', 'core.antibody.fab_fragment', 'core.antibody.fc_fragment',
    'core.receptor.single_pass_unliganded', 'core.receptor.extracellular_domain',
    'core.ligand.peptide', 'core.ligand.small_molecule', 'core.lysosome.cutaway',
    'core.autolysosome', 'core.protein.homotrimer', 'core.protein.heterotetramer',
]
HISTORICAL = ROOT / 'assets/scientific-packs/core-biology/revisions/2026-10-13-broad-library-predecessor'

spec = importlib.util.spec_from_file_location('library_native_comparators', ROOT / 'scripts/check-rna-artwork-browser.py')
native = importlib.util.module_from_spec(spec)
spec.loader.exec_module(native)

# Extend the established native comparator without changing its other callers.
# Text was absent from its RNA-only snapshot, which was insufficient for the
# analytical templates and the live labels in the new tissue/gradient drawings.
STATE = native.STATE.replace(
    'id:o.figureId,type:o.type,path:o.path||null',
    "id:o.figureId,type:o.type,text:typeof o.text==='string'?o.text:null,"
    "typography:typeof o.text==='string'?{fontFamily:o.fontFamily,fontSize:o.fontSize,"
    "fontWeight:o.fontWeight,fontStyle:o.fontStyle,textAlign:o.textAlign,"
    "lineHeight:o.lineHeight,charSpacing:o.charSpacing,styles:o.styles||{}}:null,"
    'path:o.path||null')
if STATE == native.STATE:
    raise ValueError('Native snapshot changed; review the analytical-text extension.')


def source_text_labels(record):
    """Return authored live SVG text independently of the imported objects."""
    root = ET.parse(record['_svg']).getroot()
    return sorted(''.join(element.itertext()).strip() for element in root.iter()
                  if element.tag.rsplit('}', 1)[-1] == 'text')


def native_text_labels(state):
    return sorted(part['text'].strip() for part in native.leaves(state['tree'])
                  if part.get('text') is not None)

schema_spec = importlib.util.spec_from_file_location('library_catalog_schema', ROOT / 'scripts/check-scientific-catalog-schema.py')
catalog_schema = importlib.util.module_from_spec(schema_spec)
schema_spec.loader.exec_module(catalog_schema)


def source_identity(*, allow_pending=False):
    paths = {Path(__file__).resolve(), ROOT / 'scripts/figure_studio_entry_qa.py', ROOT / 'scripts/check-rna-artwork-browser.py',
             ROOT / 'scripts/check-scientific-catalog-schema.py', ROOT / 'scripts/validate-scientific-assets.py'}
    paths.update({ROOT / 'scripts/figure_package_qa.py', ROOT / 'scripts/figure_tool_package_producer.py'})
    if TARGET.package_root:
        return {**{path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(paths)},
                **TARGET.inventory_identity()}
    for folder in ['app', 'web']:
        paths.update(p for p in (ROOT / folder).rglob('*') if p.is_file() and p.suffix in {'.js', '.css', '.html', '.json'})
    library = json.loads((ROOT / 'assets/scientific-packs/library.json').read_text(encoding='utf8'))
    paths.add(ROOT / 'assets/scientific-packs/library.json')
    for pack in library['packs']:
        if not pack.get('enabled'):
            continue
        catalog = ROOT / 'assets/scientific-packs' / pack['path']
        paths.add(catalog)
        paths.update(catalog.parent / asset['file'] for asset in json.loads(catalog.read_text(encoding='utf8'))['assets'])
    result = {}
    for path in sorted(paths):
        if path.is_file():
            result[path.relative_to(ROOT).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
        elif allow_pending:
            result[path.relative_to(ROOT).as_posix()] = '<pending SVG>'
        else:
            raise FileNotFoundError(path)
    return result


def catalog_records():
    records = {}
    library = json.loads((RUNTIME_ROOT / 'assets/scientific-packs/library.json').read_text(encoding='utf8'))
    for pack in library['packs']:
        if pack.get('enabled'):
            path = RUNTIME_ROOT / 'assets/scientific-packs' / pack['path']
            for asset in json.loads(path.read_text(encoding='utf8'))['assets']:
                records[asset['id']] = {**asset, '_catalog': path, '_svg': path.parent / asset['file']}
    return records


def paint_components(value):
    """Compare CSS paint values while retaining their authored alpha exactly."""
    paint = str(value).strip().lower()
    if re.fullmatch(r'#[0-9a-f]{6}', paint):
        return tuple(int(paint[at:at+2], 16) for at in (1, 3, 5)), 1.0
    match = re.fullmatch(r'rgba?\(\s*([0-9.]+)\s*,\s*([0-9.]+)\s*,\s*([0-9.]+)(?:\s*,\s*([0-9.]+))?\s*\)', paint)
    if match:
        return tuple(float(match.group(at)) for at in (1, 2, 3)), float(match.group(4) or 1)
    raise ValueError('Unsupported native paint representation: ' + paint)


class Case:
    def __init__(self, browser, base, route, size, theme, out, report, *, label=None):
        self.browser, self.base, self.route, self.size, self.theme = browser, base, route, size, theme
        self.name = label or f'{size[0]}x{size[1]}-{theme}'
        self.out = out / self.name
        self.out.mkdir()
        self.report = report
        self.case = {'name': self.name, 'viewport': list(size), 'theme': theme, 'insertions': []}
        report['cases'].append(self.case)
        self.context = self.page = self.frame = None
        self.phase = 'startup'

    def check(self, name, passed, detail=None):
        self.report['checks'].append({'case': self.name, 'name': name, 'passed': bool(passed), 'detail': detail})
        if not passed:
            raise AssertionError(f'{self.name}: {name}: {detail}')

    def write(self, name, value):
        (self.out / name).write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n', encoding='utf8')

    async def launch(self, routes=None):
        if self.context:
            self.phase = 'closing-context'
            await self.context.close()
        self.phase = 'startup'
        self.context = await self.browser.new_context(viewport={'width': self.size[0], 'height': self.size[1]}, accept_downloads=True, color_scheme=self.theme)
        self.page = await self.context.new_page()
        self.page.set_default_timeout(20000)
        self.page.on('pageerror', lambda error: self.report['pageErrors'].append({'case': self.name, 'error': str(error)}))
        self.page.on('console', lambda msg: self.report['consoleErrors'].append({'case': self.name, 'error': msg.text}) if msg.type == 'error' else None)
        self.page.on('requestfailed', lambda request: self.report['failedRequests'].append({'case': self.name, 'method': request.method, 'url': request.url, 'failure': request.failure, 'phase': self.phase}))
        self.page.on('response', lambda response: self.report['vendorResponses'].append({'case': self.name, 'method': response.request.method, 'url': response.url, 'status': response.status}) if '/vendor/' in response.url and response.request.method == 'GET' else None)
        if routes:
            for suffix, path in routes.items():
                def handler(source):
                    async def override(route):
                        await route.fulfill(status=200, content_type='application/json' if source.suffix == '.json' else 'image/svg+xml', body=source.read_text(encoding='utf8'))
                    return override
                await self.page.route('**/' + suffix, handler(path))
        theme = 'dark-graphite' if self.theme == 'dark' else 'light'
        path = 'web/' if self.route == 'web' else f'app/index.html?bsd_theme={theme}&bsd_effective_theme={theme}'
        await self.page.goto(self.base + '/' + path, wait_until='domcontentloaded')
        self.frame = await (await self.page.wait_for_selector('#figure-editor-frame')).content_frame() if self.route == 'web' else self.page
        await self.frame.wait_for_function('window.FigureStudio?.app?.isReady===true')
        self.phase = 'ready'
        self.check('Canonical native vector dependencies are ready', await self.frame.evaluate('Boolean(window.fabric)&&Boolean(window.jspdf?.jsPDF)'))
        if self.route == 'web':
            # Fresh contexts request this system appearance. The web host applies
            # it before loading the editor, then adopts its controls into a hidden
            # Browser files panel. Verify the result without racing that adoption.
            appearance = await self.page.evaluate('''theme => {
              const editor = document.getElementById('figure-editor-frame').contentDocument;
              const selector = `[data-browser-theme="${theme}"]`;
              const button = document.querySelector(selector) || editor.querySelector(selector);
              return {host: document.documentElement.dataset.webTheme,
                html: editor.documentElement.dataset.theme, body: editor.body.dataset.theme,
                root: editor.getElementById('figureStudioRoot').dataset.theme,
                effective: editor.documentElement.dataset.bsdEffectiveTheme,
                pressed: button?.getAttribute('aria-pressed')};
            }''', theme)
            self.check('Requested web appearance is applied',
                       all(appearance[key] == theme for key in ['host', 'html', 'body', 'root', 'effective'])
                       and appearance['pressed'] == 'true', appearance)

    async def enter(self, kind='figure', name='Library drawing acceptance'):
        await enter_current_document_async(self.frame, kind=kind, preset='presentation-wide' if kind == 'presentation' else 'double-column', name=name, layout_id='blank' if kind == 'presentation' else None)
        if kind == 'presentation':
            await show_library_async(self.frame, tab='slides')
            await self.frame.locator('.deck-insert-menu > summary').click()
            await self.frame.locator('.presentation-toolbar [data-deck-command="assets"]').click()
        else:
            await show_library_async(self.frame, tab='tools')
        await self.frame.locator('#figureLibraryTab-assets').click()
        await self.frame.locator('#assetCategorySelect').select_option('all')
        await self.frame.locator('#assetSubcategorySelect').select_option('all')
        await self.frame.locator('[data-asset-discovery="all"]').click()

    async def query(self, text):
        await self.frame.locator('#assetSearchInput').fill(text)

    async def capture(self, filename, intent):
        record = {'case': self.name, 'file': str((self.out / filename).relative_to(self.out.parent)), 'intent': intent}
        self.report['captures'].append(record)  # Intent is recorded before capture.
        self.write('capture-intents.json', [r for r in self.report['captures'] if r['case'] == self.name])
        await self.frame.locator('#toast.show').wait_for(state='hidden', timeout=12000)
        await self.page.screenshot(path=str(self.out / filename), animations='disabled')

    async def insert(self, asset_id, record):
        await self.query(record.get('scientific_name') or record['name'].split(' — ')[0])
        card = self.frame.locator(f'#assetGrid [data-asset-id="{asset_id}"]')
        if not await card.count():
            companion = self.frame.locator(f'#assetGrid [data-asset-variant-id="{asset_id}"]')
            self.check(f'{asset_id} has a visible drawing or cosmetic companion', await companion.count() == 1)
            await companion.click()
        await card.wait_for(state='visible')
        await card.scroll_into_view_if_needed()
        preview = card.locator('img')
        await preview.wait_for(state='visible')
        await preview.evaluate('img=>img.decode()')
        usability = await card.evaluate("""button=>{const b=button.getBoundingClientRect(),img=button.querySelector('img'),i=img.getBoundingClientRect(),thumb=img.parentElement.getBoundingClientRect();
          const cx=b.x+b.width/2,cy=b.y+b.height/2;
          return {button:b.toJSON(),image:i.toJSON(),thumb:thumb.toJSON(),label:button.getAttribute('aria-label'),natural:[img.naturalWidth,img.naturalHeight],
            centerHitsOwnButton:document.elementFromPoint(cx,cy)?.closest('[data-asset-id]')===button,
            pageOverflow:document.documentElement.scrollWidth>innerWidth+1};}""")
        self.check(f'{asset_id} drawing is readable and clickable in the Library', bool(usability['label']) and usability['centerHitsOwnButton'] and min(usability['natural']) > 0 and usability['image']['width'] >= 48 and usability['image']['left'] >= usability['thumb']['left'] - 1 and usability['image']['right'] <= usability['thumb']['right'] + 1 and not usability['pageOverflow'], usability)
        await card.click()
        await self.frame.wait_for_function('id=>FigureStudio.app.getObjectByIdForQa(FigureStudio.app.getSelectionStateForQa().activeObjectId)?.scientificAssetMeta?.assetId===id', arg=asset_id)
        object_id = await self.frame.evaluate('FigureStudio.app.getSelectionStateForQa().activeObjectId')
        state = (await self.frame.evaluate(STATE, [object_id]))[0]
        self.check(f'{asset_id} inserts its own native drawing', state['assetId'] == asset_id and state['meta']['originalSvgPath'] == record['file'] and state['importMode'] != 'raster_fallback' and all(p['type'].lower() != 'image' for p in native.leaves(state['tree'])))
        declared = {r['id'] for r in record['editable_color_regions']}
        bound = set().union(*(set(p['regionPaints']) for p in native.leaves(state['tree'])))
        self.check(f'{asset_id} retains every declared biological part', declared <= bound, {'declared': sorted(declared), 'bound': sorted(bound)})
        self.check(f'{asset_id} has editable geometry', bool(native.leaves(state['tree'])) and any(p['path'] or p['type'] in {'ellipse', 'circle', 'rect', 'line', 'polygon'} for p in native.leaves(state['tree'])))
        expected_labels = source_text_labels(record)
        self.check(f'{asset_id} retains every source label as native live text',
                   native_text_labels(state) == expected_labels,
                   {'sourceLabels': expected_labels, 'nativeLabels': native_text_labels(state)})
        self.case['insertions'].append({'assetId': asset_id, 'objectId': object_id, 'sourceSvgSha256': hashlib.sha256(record['_svg'].read_bytes()).hexdigest(), 'native': state})
        return object_id

    async def arrange(self, ids):
        # Only fixture placement follows actual Library insertion. It does not
        # manufacture asset metadata, geometry, bindings or document identity.
        if cohort_packs(self.report.get('cohortKind')):
            await self.frame.evaluate("""ids=>{
              const saved=FigureStudio.app.serializeCurrentDocumentForQa({markSaved:false}),a=(saved.project||saved).artboard;
              const cols=10,rows=Math.ceil(ids.length/cols),dx=(a.widthIn*96-32)/cols,dy=(a.heightIn*96-32)/rows;
              ids.forEach((id,at)=>{const o=FigureStudio.app.getObjectByIdForQa(id);
                o.scaleToWidth(dx*.78);if(o.getScaledHeight()>dy*.8)o.scaleToHeight(dy*.8);
                o.set({originX:'center',originY:'center',left:16+(at%cols+.5)*dx,top:16+(Math.floor(at/cols)+.5)*dy});o.setCoords();o.canvas.requestRenderAll();});
            }""", ids)
            return
        await self.frame.evaluate("""ids=>ids.forEach((id,at)=>{const o=FigureStudio.app.getObjectByIdForQa(id);
          o.scaleToWidth(70);if(o.getScaledHeight()>58)o.scaleToHeight(58);
          o.set({originX:'center',originY:'center',left:52+(at%7)*91,top:50+Math.floor(at/7)*73});o.setCoords();o.canvas.requestRenderAll();})""", ids)

    async def edit_acceptance(self, ids):
        kind = await self.frame.evaluate('FigureStudio.app.getDocumentWorkspaceStateForQa().activeKind')
        if kind == 'figure':
            await self.frame.locator('[data-figure-layout-choice="advanced"]').click()
            if await self.frame.locator('#figureStyleToggle').get_attribute('aria-pressed') != 'true':
                await self.frame.locator('#figureStyleToggle').click()
        elif not await self.frame.locator('[data-rail-panel="right"]').is_visible():
            await self.frame.locator('.presentation-toolbar [data-deck-command="format"]').click()
        await self.frame.locator('[data-inspector-tab="properties"]').click()
        targets = []
        packs = cohort_packs(self.report.get('cohortKind'))
        families = bool(packs)
        records = catalog_records()
        for category in (packs if families else ['cell', 'organelle', 'protein']):
            for object_id in ids:
                state = (await self.frame.evaluate(STATE, [object_id]))[0]
                if (records[state['assetId']]['_catalog'].parent.name == category if families else state['meta']['category'] == category):
                    targets.append(object_id)
                    break
        self.check('Editing cohort covers all three biological families' if families else 'Editing cohort covers a cell, organelle and molecule', len(targets) == 3, targets)
        expansion = self.report.get('cohortKind') == 'expansion'
        if expansion:
            if self.report.get('nativeEditScope') == 'representative':
                by_asset = await self.frame.evaluate('ids=>Object.fromEntries(ids.map(id=>[FigureStudio.app.getObjectByIdForQa(id).scientificAssetMeta.assetId,id]))', ids)
                missing = [asset_id for asset_id in EXPANSION_EDIT_REPRESENTATIVES if asset_id not in by_asset]
                self.check('Every representative native editing drawing is present', not missing, missing)
                targets = [by_asset[asset_id] for asset_id in EXPANSION_EDIT_REPRESENTATIVES]
            else:
                targets = list(ids)
            self.check('Expansion native editing scope matches its declared coverage',
                       len(targets) == (len(EXPANSION_EDIT_REPRESENTATIVES) if self.report.get('nativeEditScope') == 'representative' else len(self.report['cohort'])),
                       {'scope': self.report.get('nativeEditScope', 'all'), 'count': len(targets)})
        coverage = {'plannedObjectIds': targets, 'completed': []}
        self.case.setdefault('nativeEditCoverage', {})[kind] = coverage
        for at, object_id in enumerate(targets):
            if kind == 'figure':
                await self.frame.locator('[data-tool="select"]').click()
            else:
                await self.frame.evaluate('FigureStudio.app.exitGroupIsolationForQa()')
            await self.frame.evaluate('id=>FigureStudio.app.selectObjectsByIdsForQa([id])', object_id)
            self.check('Native drawing can be selected independently',
                       await self.frame.evaluate('FigureStudio.app.getSelectionStateForQa().activeObjectId') == object_id)
            before_color = await self.frame.evaluate(STATE, ids)
            index = ids.index(object_id)
            regions = before_color[index]['meta']['editableColorRegions']
            region = next((r for r in regions if r.get('paint', 'fill') == 'fill'), next(r for r in regions if r['id'] != 'outline'))
            color = ['#277da8', '#a770aa', '#bc6c25'][at % 3]
            control = self.frame.locator(f'#scientificAssetColorList [data-asset-color-region="{region["id"]}"]')
            await control.wait_for(state='visible')
            await control.evaluate("(input,color)=>{input.value=color;input.dispatchEvent(new Event('change',{bubbles:true}));}", color)
            await self.frame.wait_for_function('([id,r,c])=>FigureStudio.app.getObjectByIdForQa(id)?.scientificAssetMeta.colorOverrides?.[r]?.toLowerCase()===c', arg=[object_id, region['id'], color])
            after_color = await self.frame.evaluate(STATE, ids)
            bound = [p for p in native.leaves(after_color[index]['tree']) if region['id'] in p['regionPaints']]
            self.check('Named part recolor updates the native biological part', bool(bound) and all(str(p[channel]).lower() == color for p in bound for channel in p['regionPaints'][region['id']]), {'assetId': after_color[index]['assetId'], 'region': region['id']})
            self.check('Named part recolor preserves every other object', native.rounded(before_color[:index] + before_color[index+1:]) == native.rounded(after_color[:index] + after_color[index+1:]))
            if kind == 'figure':
                await self.frame.evaluate('FigureStudio.app.fitSelectionInViewForQa({onlyIfNeeded:false,maxZoom:2,padding:140})')
                await self.frame.locator('[data-tool="directSelect"]').click()
                await self.frame.evaluate('id=>FigureStudio.app.enterGroupIsolationForQa({groupId:id})', object_id)
                child = await self.frame.evaluate("""id=>{const root=FigureStudio.app.getObjectByIdForQa(id),visit=o=>[o,...(o.getObjects?.()||[]).flatMap(visit)],parts=visit(root);
                  const path=parts.find(o=>o.path&&Object.keys(o.importMeta?.scientificSvgSource?.regionPaints||{}).length),
                    primitive=path||parts.find(o=>['rect','circle','ellipse','line','polygon'].includes(o.type)&&Object.keys(o.importMeta?.scientificSvgSource?.regionPaints||{}).length);
                  return primitive?{id:primitive.figureId,path:Boolean(path)}:null;}""", object_id)
                self.check('Drawing exposes an editable native path or primitive', bool(child))
                await self.frame.evaluate('id=>FigureStudio.app.selectGroupIsolationChildForQa({objectId:id})', child['id'])
                if child['path']:
                    await self.frame.evaluate('id=>FigureStudio.app.selectBezierNodeForQa(id,0)', child['id'])
            else:
                # Presentation owns Format controls; detailed path-anchor work
                # belongs to Figure. Its whole native group transforms in place.
                child = {'id': object_id, 'path': False}
            before = await self.frame.evaluate(STATE, ids)
            depth = await self.frame.evaluate('FigureStudio.app.getHistoryStateForQa().undoDepth')
            history_before = await self.frame.evaluate('FigureStudio.app.getRuntimeStatus()')
            if child['path']:
                await self.frame.locator('.path-node-handle.selected').first.focus()
                await self.page.keyboard.press('ArrowRight')
            else:
                # Use the visible context transform for a primitive-only
                # heatmap in Figure, and every complete group in Presentation.
                transform = self.frame.locator('#appearanceStructureInspector [data-context-property="x"]')
                await transform.wait_for(state='visible')
                await transform.evaluate("input=>{input.value=String(Number(input.value)+.01);input.dispatchEvent(new Event('change',{bubbles:true}));}")
            after = await self.frame.evaluate(STATE, ids)
            self.check('Actual anchor keyboard edit changes native geometry' if child['path'] else 'Actual primitive transform changes native geometry', native.geometry([before[index]]) != native.geometry([after[index]]))
            after_depth = await self.frame.evaluate('FigureStudio.app.getHistoryStateForQa().undoDepth')
            history_after = await self.frame.evaluate('FigureStudio.app.getRuntimeStatus()')
            pruned = history_after['undo_history_pruned_count'] - history_before['undo_history_pruned_count']
            self.check('Native anchor edit records one history entry under the current step/byte budgets', after_depth == depth + 1 - pruned, {'beforeDepth': depth, 'afterDepth': after_depth, 'pruned': pruned, 'limits': history_after['history_limits'], 'reason': history_after['last_prune_reason']})
            self.check('Native anchor edit preserves all other objects exactly', native.rounded(before[:index] + before[index+1:]) == native.rounded(after[:index] + after[index+1:]))
            if self.size == (1440, 1000) and self.theme == 'light' and (not expansion or at < 3 or not child['path'] or any(term in after[index]['assetId'] for term in ['primary_cilium.straight', 'pyroptotic_cell.pore_bearing', 'fibroblast.matrix', 'structure.germinal_center', 'gradient.perivascular', 'heatmap.clustered'])):
                await self.capture(f'anchor-{kind}-{at}.png', f'Show {after[index]["assetId"]} in {kind} after an actual native geometry edit inside its recolored editable drawing; labels remain live text where present.')
            await self.frame.evaluate('FigureStudio.app.undoForQa()')
            undone = await self.frame.evaluate(STATE, ids)
            undo_difference = native.native_reconstruction_difference(native.geometry(before), native.geometry(undone))
            self.write(f'edit-{kind}-{at}.json', {'documentKind': kind, 'beforeColor': before_color[index], 'afterColor': after_color[index], 'before': before[index], 'after': after[index], 'undone': undone[index], 'undoDifference': undo_difference})
            self.check('Undo restores path geometry, paint, bindings and hierarchy', undo_difference['passed'], undo_difference)
            other_difference = native.native_reconstruction_difference(before[:index] + before[index+1:], undone[:index] + undone[index+1:])
            self.check('Undo preserves owner and all unrelated primitive IDs, metadata, paths and paints', undone[index]['id'] == object_id and other_difference['passed'], other_difference)
            await self.frame.evaluate('FigureStudio.app.redoForQa()')
            redone = await self.frame.evaluate(STATE, ids)
            redo_difference = native.native_reconstruction_difference(native.geometry(after), native.geometry(redone))
            self.check('Redo restores the native edit', redo_difference['passed'], redo_difference)
            self.write(f'edit-{kind}-{at}.json', {'documentKind': kind, 'beforeColor': before_color[index], 'afterColor': after_color[index], 'before': before[index], 'after': after[index], 'undone': undone[index], 'redone': redone[index]})
            label_edit = await self.edit_label_acceptance(object_id, ids, index, at, kind) if expansion and native_text_labels(redone[index]) else None
            coverage['completed'].append({'assetId': after[index]['assetId'], 'objectId': object_id,
                'geometryEdit': 'anchor-keyboard' if child['path'] else 'group-transform' if kind == 'presentation' else 'primitive-transform', 'namedRegionRecolor': region['id'], 'liveTextEdit': label_edit})
            await self.frame.evaluate('FigureStudio.app.exitGroupIsolationForQa()')
            print(f'{self.name}/{kind}: {after[index]["assetId"]} recolor/native geometry/history passed', flush=True)
        if kind == 'figure':
            await self.frame.locator('[data-figure-layout-choice="simple"]').click()
            await self.frame.locator('#figure-simple-toolbar [data-figure-layout-command="fit-screen"]').click()
        else:
            await self.frame.locator('#fitBtn').click()

    async def edit_label_acceptance(self, object_id, ids, index, at, kind):
        """Edit one live label through the ordinary text control, not a fixture API."""
        child = await self.frame.evaluate("""id=>{const visit=o=>[o,...(o.getObjects?.()||[]).flatMap(visit)];const child=visit(FigureStudio.app.getObjectByIdForQa(id)).find(o=>typeof o.text==='string');return child?{id:child.figureId,text:child.text}:null;}""", object_id)
        self.check('Text-bearing drawing exposes a native label', bool(child))
        if kind == 'figure':
            await self.frame.locator('[data-tool="select"]').click()
        # Choosing whole-object Selection intentionally exits isolation. Reenter
        # through the real group boundary before selecting the live text child.
        entered = await self.frame.evaluate('([groupId,childId])=>FigureStudio.app.enterGroupIsolationForQa({groupId,childId})', [object_id, child['id']])
        self.check('Original drawing group opens for native label editing', entered['entered'], entered)
        selected = await self.frame.evaluate('id=>FigureStudio.app.selectGroupIsolationChildForQa({objectId:id})', child['id'])
        self.check('Native scientific label can be selected within its original group', selected['selected'], selected)
        # Use the visible native Content field in Figure Properties or
        # Presentation Format; both dispatch the same ordinary text command.
        text_control = self.frame.locator('#appearanceStructureInspector [data-context-property="text"]')
        await text_control.wait_for(state='visible')
        await self.frame.wait_for_function("text=>{const input=document.querySelector('#appearanceStructureInspector [data-context-property=\"text\"]');return input&&!input.disabled&&input.value===text;}", arg=child['text'])
        before = await self.frame.evaluate(STATE, ids)
        revised = child['text'] + ' QA'
        await text_control.evaluate("(input,text)=>{if(input.disabled)throw new Error('Native label text control is disabled');input.value=text;input.dispatchEvent(new Event('change',{bubbles:true}));}", revised)
        after = await self.frame.evaluate(STATE, ids)
        self.check('Ordinary text control edits the selected scientific label', revised in native_text_labels(after[index]) and native_text_labels(after[index]) != native_text_labels(before[index]))
        self.check('Scientific label edit preserves unrelated drawings', native.rounded(before[:index] + before[index+1:]) == native.rounded(after[:index] + after[index+1:]))
        await self.frame.evaluate('FigureStudio.app.undoForQa()')
        undone = await self.frame.evaluate(STATE, ids)
        difference = native.native_reconstruction_difference(native.geometry(before), native.geometry(undone))
        self.check('Undo restores native text, fonts, paths and paints', difference['passed'], difference)
        await self.frame.evaluate('FigureStudio.app.redoForQa()')
        redone = await self.frame.evaluate(STATE, ids)
        difference = native.native_reconstruction_difference(native.geometry(after), native.geometry(redone))
        self.check('Redo restores the authored native label edit', difference['passed'], difference)
        self.write(f'text-edit-{kind}-{at}.json', {'documentKind': kind, 'assetId': after[index]['assetId'], 'textObjectId': child['id'], 'before': before[index], 'after': after[index], 'undone': undone[index], 'redone': redone[index]})
        return {'objectId': child['id'], 'before': child['text'], 'after': revised}

    async def live_continuity(self, figure_ids, presentation_ids):
        await self.frame.evaluate('id=>FigureStudio.app.selectObjectsByIdsForQa([id])', presentation_ids[-1])
        present = await self.frame.evaluate('FigureStudio.app.serializeCurrentDocumentForQa({markSaved:false})')
        await self.frame.locator('#figureWorkspaceTab').click()
        await self.frame.wait_for_function("FigureStudio.app.getDocumentWorkspaceStateForQa().activeKind==='figure'")
        await self.frame.evaluate('id=>FigureStudio.app.selectObjectsByIdsForQa([id])', figure_ids[-1])
        figure_selection = await self.frame.evaluate('FigureStudio.app.getSelectionStateForQa()')
        self.check('Live Figure fixture has the requested native selection', figure_selection.get('activeObjectId') == figure_ids[-1], figure_selection)
        figure = await self.frame.evaluate('FigureStudio.app.serializeCurrentDocumentForQa({markSaved:false})')
        await self.frame.locator('#presentationWorkspaceTab').click()
        await self.frame.wait_for_function("FigureStudio.app.getDocumentWorkspaceStateForQa().activeKind==='presentation'")
        self.check('Presentation workspace restores native selection', await self.frame.evaluate('FigureStudio.app.getSelectionStateForQa().activeObjectId') == presentation_ids[-1])
        present_after = await self.frame.evaluate('FigureStudio.app.serializeCurrentDocumentForQa({markSaved:false})')
        self.write('presentation-workspace-before.json', present)
        self.write('presentation-workspace-after.json', present_after)
        self.check('Presentation workspace restores authored artwork', native.authored_document(present) == native.authored_document(present_after))
        await self.frame.locator('#figureWorkspaceTab').click()
        await self.frame.wait_for_function("FigureStudio.app.getDocumentWorkspaceStateForQa().activeKind==='figure'")
        restored_selection = await self.frame.evaluate('FigureStudio.app.getSelectionStateForQa()')
        self.write('workspace-selection.json', {'expectedFigureId': figure_ids[-1], 'before': figure_selection, 'after': restored_selection, 'workspace': await self.frame.evaluate('FigureStudio.app.getDocumentWorkspaceStateForQa()')})
        self.check('Figure workspace restores native selection', restored_selection.get('activeObjectId') == figure_ids[-1], restored_selection)
        self.check('Figure workspace restores authored artwork', native.authored_document(figure) == native.authored_document(await self.frame.evaluate('FigureStudio.app.serializeCurrentDocumentForQa({markSaved:false})')))
        # A genuine active path selection must remain distinct from the stale
        # path state that previously overwrote a whole-object selection.
        await self.frame.locator('[data-figure-layout-choice="advanced"]').click()
        await self.frame.locator('[data-tool="directSelect"]').click()
        await self.frame.evaluate('id=>FigureStudio.app.enterGroupIsolationForQa({groupId:id})', figure_ids[0])
        child = await self.frame.evaluate("""id=>{const visit=o=>[o,...(o.getObjects?.()||[]).flatMap(visit)];return visit(FigureStudio.app.getObjectByIdForQa(id)).find(o=>o.path)?.figureId;}""", figure_ids[0])
        await self.frame.evaluate('id=>FigureStudio.app.selectGroupIsolationChildForQa({objectId:id})', child)
        await self.frame.evaluate('id=>FigureStudio.app.selectBezierNodeForQa(id,0)', child)
        direct_before = await self.frame.evaluate('FigureStudio.app.getDirectSelectionStateForQa()')
        await self.frame.locator('#presentationWorkspaceTab').click()
        await self.frame.wait_for_function("FigureStudio.app.getDocumentWorkspaceStateForQa().activeKind==='presentation'")
        await self.frame.locator('#figureWorkspaceTab').click()
        await self.frame.wait_for_function("FigureStudio.app.getDocumentWorkspaceStateForQa().activeKind==='figure'")
        direct_after = await self.frame.evaluate('FigureStudio.app.getDirectSelectionStateForQa()')
        self.check('Genuine direct path selection restores after workspace switching', direct_before['objectId'] == child and direct_after['objectId'] == child and direct_after['selectedHandleCount'] == direct_before['selectedHandleCount'] == 1, {'before': direct_before, 'after': direct_after})
        await self.frame.evaluate('FigureStudio.app.exitGroupIsolationForQa()')
        await self.frame.locator('[data-tool="select"]').click()
        await self.frame.locator('[data-figure-layout-choice="simple"]').click()
        await self.frame.evaluate('id=>FigureStudio.app.selectObjectsByIdsForQa([id])', figure_ids[-1])
        await self.frame.locator('#presentationWorkspaceTab').click()

    async def historical_acceptance(self, records):
        if self.report.get('cohortKind') == 'families':
            chosen, routes = [], {}
            for pack_id in FAMILY_PACKS:
                snapshot = RUNTIME_ROOT / 'assets/scientific-packs' / pack_id / FAMILY_PREDECESSOR
                self.check(pack_id + ' predecessor source snapshot exists', (snapshot / 'asset-pack.json').is_file())
                pack = json.loads((snapshot / 'asset-pack.json').read_text(encoding='utf8'))
                routes[pack_id + '/asset-pack.json'] = snapshot / 'asset-pack.json'
                for record in pack['assets']:
                    chosen.append({**record, '_svg': snapshot / record['file']})
                    routes[pack_id + '/' + record['file']] = snapshot / record['file']
            self.check('Historical fixture contains all 40 predecessor drawings', len(chosen) == 40)
            for kind, suffix in [('figure', 'fsfigure'), ('presentation', 'fsdeck')]:
                await self.launch(routes)
                await self.enter(kind=kind, name='Historical embedded family artwork')
                old_ids = [await self.insert(record['id'], record) for record in chosen]
                await self.arrange(old_ids)
                await self.roundtrip('library-predecessor.' + suffix, old_ids)
            self.case['historicalAssetIds'] = [record['id'] for record in chosen]
            return
        self.check('Predecessor source snapshot exists', (HISTORICAL / 'asset-pack.json').is_file())
        historical = json.loads((HISTORICAL / 'asset-pack.json').read_text(encoding='utf8'))
        chosen = [record for record in historical['assets'] if record['id'] in LEGACY or record['id'] in ['core.antibody.igg_manuscript', 'core.mitochondrion.basic_manuscript']]
        routes = {'core-biology/asset-pack.json': HISTORICAL / 'asset-pack.json'}
        routes.update({'core-biology/' + record['file']: HISTORICAL / record['file'] for record in chosen})
        await self.launch(routes)
        await self.enter(name='Historical embedded cell and molecular artwork')
        old_ids = [await self.insert(record['id'], {**record, '_svg': HISTORICAL / record['file']}) for record in chosen]
        await self.arrange(old_ids)
        await self.roundtrip('library-predecessor.fsfigure', old_ids)
        self.case['historicalAssetIds'] = [record['id'] for record in chosen]

    async def export_svg(self, records):
        expected_labels = None
        if self.report.get('cohortKind') == 'expansion':
            # The all80 contact grid is intentionally too small for manuscript
            # text and correctly fails export preflight. Qualify vector export
            # in a separate, readable-size fixture without relaxing preflight.
            await self.enter(name='Readable native drawing SVG export')
            export_assets = ['analysis.heatmap.clustered', 'tme.tertiary_lymphoid_structure.germinal_center']
            ids = [await self.insert(asset_id, records[asset_id]) for asset_id in export_assets]
            await self.frame.evaluate("""ids=>ids.forEach((id,at)=>{const o=FigureStudio.app.getObjectByIdForQa(id);
              o.scaleToWidth(260);o.set({originX:'center',originY:'center',left:170+at*335,top:240});o.setCoords();o.canvas.requestRenderAll();})""", ids)
            expected_labels = sorted(label for asset_id in export_assets for label in source_text_labels(records[asset_id]))
            if self.size == (1440, 1000) and self.theme == 'light':
                await self.capture('readable-svg-export-fixture.png', 'Show a heatmap template and organized TLS at readable label size, preserving ordinary export-preflight requirements and native editable vectors.')
        await self.frame.locator('#fileMenuTrigger').click()
        await self.frame.locator('[data-menu="file"] [data-command="export-as"]').click()
        await self.frame.locator('[data-export-as-format]').select_option('svg')
        await self.frame.wait_for_function("FigureStudio.app.getExportAsStateForQa().reviewStatus==='ready' && FigureStudio.app.getExportAsStateForQa().reviewedRequest?.format==='svg'")
        export_state = await self.frame.evaluate('FigureStudio.app.getExportAsStateForQa()')
        self.write('svg-export-review.json', export_state)
        self.check('Ordinary SVG export preflight accepts the readable fixture', await self.frame.locator('[data-export-as-submit]').is_enabled(), export_state)
        async with self.page.expect_download() as pending:
            await self.frame.locator('[data-export-as-submit]').click()
        path = self.out / 'library-native.svg'
        await (await pending.value).save_as(path)
        text = path.read_text(encoding='utf8')
        self.check('Actual SVG export retains editable vector paths without raster artwork', '<path' in text and '<image' not in text and 'data:image' not in text)
        if expected_labels is not None:
            root = ET.fromstring(text)
            labels = sorted(''.join(element.itertext()).strip() for element in root.iter() if element.tag.rsplit('}', 1)[-1] == 'text')
            self.check('Actual SVG export preserves every analytical/tissue label as live text', labels == expected_labels, {'expectedLabels': expected_labels, 'exportedLabels': labels})
        await self.frame.locator('[data-export-as-close]').click()

    async def treatment_matrix(self, cohort, records):
        matrix, canonical_geometry, canonical_alpha = [], {}, {}
        for style in ['soft-color', 'cut-paper', 'technical-ink']:
            for palette in ['original', 'pastel', 'vivid', 'monochrome']:
                await self.enter(name=f'Library · {style} · {palette}')
                await self.frame.locator('#assetArtStyleSelect').select_option(style)
                await self.frame.locator('#assetPaletteSelect').select_option(palette)
                ids = [await self.insert(asset_id, records[asset_id]) for asset_id in cohort]
                states = await self.frame.evaluate(STATE, ids)
                self.write(f'native-{style}-{palette}.json', states)
                for state in states:
                    asset_id = state['assetId']
                    self.check(f'{style}/{palette}/{asset_id} retains selected treatment and palette', state['meta'].get('art_style') == style and state['meta'].get('paletteId') == palette)
                    primitives = native.leaves(state['tree'])
                    signature = [(p['type'], p['path'], sorted(p['regionPaints'])) for p in primitives]
                    if style == 'soft-color' and palette == 'original':
                        canonical_geometry[asset_id] = signature
                        canonical_alpha[asset_id] = [{channel: paint_components(p[channel])[1] for channel in ['fill', 'stroke'] if any(channel in values for values in p['regionPaints'].values())} for p in primitives]
                    self.check(f'{style}/{palette}/{asset_id} preserves native paths and biological bindings', signature == canonical_geometry[asset_id])
                    for region in state['meta']['editableColorRegions']:
                        expected = state['meta'].get('paletteColorOverrides', {}).get(region['id'], region['default']).lower()
                        expected_rgb, _ = paint_components(expected)
                        bound = [(at, p) for at, p in enumerate(primitives) if region['id'] in p['regionPaints']]
                        observed = [{'primitive': at, 'channel': channel, 'paint': p[channel], 'canonicalAlpha': canonical_alpha[asset_id][at][channel]} for at, p in bound for channel in p['regionPaints'][region['id']]]
                        self.check(f'{style}/{palette}/{asset_id}/{region["id"]} paints its named native part and preserves alpha', bool(bound) and all(paint_components(item['paint']) == (expected_rgb, item['canonicalAlpha']) for item in observed), {'expectedRgb': expected_rgb, 'observed': observed})
                matrix.append({'style': style, 'palette': palette, 'states': states})
                self.write('native-treatment-matrix.json', matrix)
                print(f'{self.name}: {style}/{palette} all{len(cohort)} native drawings passed', flush=True)
        self.case['treatmentCount'] = len(matrix)

    async def save(self, filename):
        await self.frame.locator('#fileMenuTrigger').click()
        self.page.once('dialog', lambda dialog: dialog.accept(filename))
        async with self.page.expect_download() as pending:
            await self.frame.locator('[data-menu="file"] [data-command="save-project"]').click()
        download = await pending.value
        self.check('Actual save uses the native document extension', download.suggested_filename.endswith(Path(filename).suffix), {'requested': filename, 'suggested': download.suggested_filename})
        path = self.out / filename
        await download.save_as(path)
        return path, await self.frame.evaluate('FigureStudio.app.serializeCurrentDocumentForQa({markSaved:false})')

    async def cold_open(self, path):
        await self.launch()
        await self.enter(name='Cold file Open')
        await self.frame.locator('#fileMenuTrigger').click()
        async with self.page.expect_file_chooser() as pending:
            await self.frame.locator('[data-menu="file"] [data-command="open-project"]').click()
        await (await pending.value).set_files(path)
        await self.frame.wait_for_function("document.querySelector('#documentFileOperationStatus')?.dataset.state==='success'")
        return await self.frame.evaluate('FigureStudio.app.serializeCurrentDocumentForQa({markSaved:false})')

    async def roundtrip(self, filename, ids):
        await self.frame.evaluate('FigureStudio.app.exitGroupIsolationForQa()')
        await self.frame.evaluate('FigureStudio.app.clearSelectionForQa()')
        before_native = await self.frame.evaluate(STATE, ids)
        path, saved = await self.save(filename)
        return await self.check_saved_file(path, saved, before_native, ids)

    async def check_saved_file(self, path, saved, before_native, ids):
        filename = path.name
        opened = await self.cold_open(path)
        self.write(filename + '-roundtrip.json', {'before': saved, 'after': opened})
        self.check(filename + ' cold Open preserves every authored field and ID', native.authored_document(saved) == native.authored_document(opened))
        thumbnails = native.thumbnail_difference(saved, opened)
        self.check(filename + ' cold Open preserves thumbnail pixels', all(x['passed'] for x in thumbnails), thumbnails)
        after_native = await self.frame.evaluate(STATE, ids)
        difference = native.native_reconstruction_difference(before_native, after_native)
        self.check(filename + ' preserves native primitives and embedded artwork', difference['passed'], difference)
        print(f'{self.name}: {filename} actual download/cold Open passed', flush=True)

    async def full_workflow(self, cohort, records, *, historical=True):
        # Start a fresh authoring document after the separate search fixture.
        # The history checks also account for the existing 50-step cap. Exact
        # Undo/Redo geometry checks verify the single operation when saturated.
        await self.enter(name='Expanded Library drawing acceptance')
        figure_ids = [await self.insert(asset_id, records[asset_id]) for asset_id in cohort]
        print(f'{self.name}: Figure all{len(cohort)}native drawings inserted', flush=True)
        await self.arrange(figure_ids)
        await self.edit_acceptance(figure_ids)
        await show_library_async(self.frame, tab='tools')
        families = bool(cohort_packs(self.report.get('cohortKind')))
        expansion = self.report.get('cohortKind') == 'expansion'
        await self.query('nucleolus' if expansion else 'tight junction' if families else 'generic cell')
        await self.frame.evaluate('id=>FigureStudio.app.selectObjectsByIdsForQa([id])', figure_ids[-1])
        await self.capture('02-figure-drawings.png', 'Show new cell-structure choices beside the complete editable expansion cohort, with selected native artwork and readable controls.' if expansion else 'Show graphical cell-contact drawing choices beside the populated editable family Figure, with selected artwork and readable controls.' if families else 'Show graphical cell drawing choices in the Library beside the populated editable Figure, with selected artwork and readable biological part controls.')
        await self.frame.evaluate('FigureStudio.app.clearSelectionForQa()')
        figure_native = await self.frame.evaluate(STATE, figure_ids)
        figure_path, figure_saved = await self.save('library-cohort.fsfigure')
        await self.enter(kind='presentation', name='Library drawing presentation')
        presentation_ids = [await self.insert(asset_id, records[asset_id]) for asset_id in cohort]
        print(f'{self.name}: Presentation all{len(cohort)}native drawings inserted', flush=True)
        await self.arrange(presentation_ids)
        if expansion:
            await self.edit_acceptance(presentation_ids)
        await self.query('volcano' if expansion else 'organoid' if families else 'mitochondrion')
        await self.capture('03-presentation-drawings.png', 'Show new analytical template choices beside the complete expanded Presentation cohort; all inserted artwork and labels remain native vectors.' if expansion else 'Show culture-model drawing choices in the Library beside the populated blank-layout Presentation; every inserted biological drawing remains a native vector.' if families else 'Show mitochondrial drawing choices in the Library beside the populated blank-layout Presentation; every inserted biological drawing remains a native vector.')
        await self.live_continuity(figure_ids, presentation_ids)
        await self.roundtrip('library-cohort.fsdeck', presentation_ids)
        await self.check_saved_file(figure_path, figure_saved, figure_native, figure_ids)
        await self.export_svg(records)
        if historical:
            await self.historical_acceptance(records)
        self.write('cohort-native.json', self.case['insertions'])

    async def search_acceptance(self, smoke=False):
        await self.query('RNA strand')
        await self.frame.locator('#assetGrid [data-asset-id="core.rna.strand"]').click()
        await self.frame.wait_for_function("FigureStudio.app.getSelectionStateForQa().activeObjectId && FigureStudio.app.getObjectByIdForQa(FigureStudio.app.getSelectionStateForQa().activeObjectId)?.scientificAssetMeta.assetId==='core.rna.strand'")
        remembered = await self.frame.evaluate('FigureStudio.app.getSelectionStateForQa().activeObjectId')
        for query, expected in [('linear RNA', 'core.rna.strand_linear'), ('hairpin RNA', 'core.rna.strand')]:
            await self.query(query)
            cards = self.frame.locator('#assetGrid [data-asset-id]')
            self.check(query + ' exposes only its matching drawing', await cards.count() == 1 and await cards.first.get_attribute('data-asset-id') == expected)
            await cards.first.click()
            await self.frame.wait_for_function('id=>FigureStudio.app.getObjectByIdForQa(FigureStudio.app.getSelectionStateForQa().activeObjectId)?.scientificAssetMeta.assetId===id', arg=expected)
        await self.query('RNA strand')
        forms = await self.frame.locator('[data-asset-concept-card="core.rna.strand"] [data-asset-form-id]').count()
        self.check('Biological RNA alternatives are separate graphical drawings', forms == 2)
        if self.report.get('cohortKind') != 'families':
            await self.capture('01-visible-rna-drawings.png', 'Show both Hairpin and Linear RNA as separate graphical insertion choices within the same Library concept, beside authored RNA artwork.')
        await self.query('FISH')
        fish = await self.frame.locator('#assetGrid [data-asset-id]').evaluate_all('els=>els.map(e=>e.dataset.assetId)')
        self.check('FISH shows its RNA assay without a fish organism', 'rna.assay_workflow.in_situ_rna_puncta' in fish and 'core.model.zebrafish' not in fish, fish)
        await self.query('fish model')
        self.check('Fish model remains discoverable', await self.frame.locator('[data-asset-id="core.model.zebrafish"]').count() == 1)
        if not smoke:
            for query in ['cell', 'single cell', 'mRNA', 'RNA']:
                await self.query(query)
                observed = await self.frame.evaluate('q=>FigureStudio.app.searchScientificAssetsForQa(q,"all")', query)
                self.case.setdefault('queries', []).append({'query': query, 'observed': observed})
                ids = observed['ids']
                if query == 'cell':
                    source = catalog_records()
                    self.check('Broad cell query starts with whole-cell drawings', ids and all(source[x]['category'] == 'cell' for x in ids[:5]), ids[:5])
                elif query == 'single cell':
                    self.check('Single cell excludes unrelated cell-envelope and single-pass receptor mentions', ids and 'microbe.membrane_signaling.gram_positive_envelope_segment' not in ids and 'exp.membrane_signaling.notch_like' not in ids, ids)
                elif query == 'mRNA':
                    self.check('mRNA prioritizes the messenger RNA drawing', ids and ids[0] == 'core.mrna.transcript', ids)
                else:
                    self.check('RNA discovers existing distinct RNA molecules', {'core.mrna.transcript', 'core.rna.strand', 'core.rna.sirna', 'exp.nucleic_acid.trna', 'exp.nucleic_acid.mirna'} <= set(ids), ids)
        await self.query('RNA strand')
        await self.frame.locator('[data-asset-favorite-concept="core.rna.strand"]').click()
        await self.frame.locator('[data-asset-discovery="favorites"]').click()
        self.check('Favorites retain one semantic concept with both drawings', await self.frame.locator('[data-asset-concept-card="core.rna.strand"]').count() == 1 and await self.frame.locator('[data-asset-form-id]').count() == 2)
        await self.frame.locator('#assetCategorySelect').select_option('protein')
        self.check('Category and Favorites filters compose with query', await self.frame.locator('#assetGrid [data-asset-id]').count() == 0)
        await self.frame.locator('#assetCategorySelect').select_option('all')
        await self.frame.locator('[data-asset-discovery="recent"]').click()
        self.check('Recent remembers one RNA concept with both drawings', await self.frame.locator('[data-asset-concept-card="core.rna.strand"]').count() == 1 and await self.frame.locator('[data-asset-form-id]').count() == 2)
        await self.frame.locator('[data-asset-discovery="all"]').click()
        self.check('Browsing and filtering preserve the selected authored object', await self.frame.evaluate('FigureStudio.app.getSelectionStateForQa().activeObjectId') != '' and await self.frame.evaluate('id=>!!FigureStudio.app.getObjectByIdForQa(id)', remembered))
        if cohort_packs(self.report.get('cohortKind')):
            records = catalog_records()
            for pack_id in cohort_packs(self.report.get('cohortKind')):
                entries = [r for r in records.values() if r['_catalog'].parent.name == pack_id]
                chosen = next((r for r in reversed(entries) if sum(s.get('concept_id') == r.get('concept_id') for s in entries) > 1), None)
                self.check(pack_id + ' has authored biological alternatives', chosen is not None)
                siblings = [r for r in entries if r.get('concept_id') == chosen.get('concept_id')]
                await self.insert(siblings[0]['id'], siblings[0])
                object_id = await self.insert(chosen['id'], chosen)
                self.check(pack_id + ' specific drawing supersedes the earlier remembered form', await self.frame.evaluate('id=>FigureStudio.app.getObjectByIdForQa(id).scientificAssetMeta.assetId', object_id) == chosen['id'])
                # Some catalogs include the form suffix in scientific_name.
                # Searching that entire title correctly returns only one form;
                # use the shared concept title for this alternatives assertion.
                await self.query((siblings[0].get('scientific_name') or siblings[0]['name']).split(' — ')[0])
                concept = chosen['concept_id']
                self.check(pack_id + ' concept exposes graphical biological form choices', await self.frame.locator(f'[data-asset-concept-card="{concept}"] [data-asset-form-id]').count() == len(siblings))
            await self.query('volcano plot' if self.report.get('cohortKind') == 'expansion' else 'coccoid bacterial arrangement')
            await self.capture('01-visible-expansion-drawings.png' if self.report.get('cohortKind') == 'expansion' else '01-visible-microbial-drawings.png', 'Show distinct volcano-plot template choices inside one Library entry beside native authored artwork, with readable form labels and complete controls.' if self.report.get('cohortKind') == 'expansion' else 'Show separately bounded paired and chained coccoid bacterial drawings as direct graphical choices within one Library entry beside authored microbial artwork, with readable labels and complete controls.')


async def run(args):
    global TARGET, RUNTIME_ROOT, HISTORICAL
    TARGET = FigureQaTarget.from_arguments(ROOT, args.package_root, args.package_sha256)
    RUNTIME_ROOT = TARGET.runtime_root
    HISTORICAL = RUNTIME_ROOT / 'assets/scientific-packs/core-biology/revisions/2026-10-13-broad-library-predecessor'
    out = args.output_dir or ROOT / 'qa_artifacts/library-drawings' / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + args.route)
    out = out.resolve()
    out.relative_to(ROOT / 'qa_artifacts')
    out.mkdir(parents=True, exist_ok=False)
    report = {'status': 'running', 'sourceRoot': str(ROOT), 'route': args.route, 'smoke': args.smoke, 'cohortKind': args.cohort, 'nativeEditScope': args.edit_scope, 'sourceIdentity': {}, 'cases': [], 'checks': [], 'captures': [], 'pageErrors': [], 'consoleErrors': [], 'failedRequests': [], 'vendorResponses': []}
    report['comparisonPolicy'] = {'authoredDocument': 'Every authored field and ID at six decimals. Clocks, derived bounds/thumbnails and artifact_store_count telemetry are excluded; the latter is global artifactStore.size, not document references. Actual artifactRefs, embedded content and other storage fields remain exact. Thumbnail pixels are checked separately.', 'history': 'Existing native geometry comparator ignores transient imported-child IDs only during Undo/Redo; owner IDs, all other IDs, paths, paints, bindings and hierarchy remain checked. Derived bounds/matrices tolerance0.01pixels. One committed entry is reconciled with observed pruning under current step/byte budgets.', 'coldOpen': 'Existing native reconstruction comparator preserves every primitive ID, path, paint, semantic binding and metadata field; only derived bounds/matrices have0.01pixel tolerance.'}
    case = server = None
    try:
        report['runtimeTarget'] = TARGET.record()
        report['sourceIdentity'] = source_identity(allow_pending=args.predecessor_fixture)
        if not args.predecessor_fixture:
            report['catalogSchemaPreflight'] = catalog_schema.catalog_schema_report(RUNTIME_ROOT / 'assets/scientific-packs/library.json')
            schema_passed = report['catalogSchemaPreflight']['status'] == 'passed'
            report['checks'].append({'case': 'catalog-preflight',
                'name': 'Canonical catalogs and editable SVGs pass schema preflight',
                'passed': schema_passed,
                'detail': {key: report['catalogSchemaPreflight'][key] for key in ['asset_count', 'pack_count', 'errors']}})
            if not schema_passed:
                raise ValueError('Catalog schema preflight failed: ' + json.dumps(report['catalogSchemaPreflight']['errors']))
        records = catalog_records()
        if args.cohort == 'families' and args.predecessor_fixture:
            raise ValueError('Family predecessor acceptance runs through the normal full workflow; no preliminary fixture override is supported.')
        fixture_routes = None
        if args.predecessor_fixture:
            if not args.smoke:
                raise ValueError('--predecessor-fixture is only a preliminary --smoke diagnosis, never final current-art acceptance.')
            old_catalog = HISTORICAL / 'asset-pack.json'
            old = json.loads(old_catalog.read_text(encoding='utf8'))['assets']
            fixture_routes = {'core-biology/asset-pack.json': old_catalog}
            for record in old:
                source = HISTORICAL / record['file']
                if source.is_file():
                    fixture_routes['core-biology/' + record['file']] = source
                    records[record['id']] = {**record, '_svg': source}
            report['fixture'] = {'kind': 'canonical-predecessor', 'scope': 'Runner/current-app diagnosis only; new catalog/artwork not qualified', 'bindings': {url: hashlib.sha256(path.read_bytes()).hexdigest() for url, path in fixture_routes.items()}}
        defaults = [x for x, record in records.items() if record['_catalog'].parent.name in cohort_packs(args.cohort)] if cohort_packs(args.cohort) else LEGACY + NEW_ASSETS + RNA_METHODS
        requested = args.asset_id or ([] if args.smoke and not args.all_drawings else defaults)
        for asset_id in requested:
            if asset_id not in records:
                raise ValueError('Missing cohort record: ' + asset_id)
        concepts = {records[x].get('concept_id') or x for x in requested}
        cohort = [x for x, record in records.items() if (record.get('concept_id') or x) in concepts and (not args.predecessor_fixture or x in {r['id'] for r in old})]
        report['cohort'] = cohort
        server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(native.QuietHandler, directory=str(RUNTIME_ROOT)))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        async with async_playwright() as pw:
            browser = await pw.chromium.launch()
            sizes = [] if args.treatments_only else [(1440, 1000)] if args.smoke else [(1280, 800), (1440, 1000), (1920, 1080)]
            for size in sizes:
                for theme in (['light'] if args.smoke else ['light', 'dark']):
                    case = Case(browser, f'http://127.0.0.1:{server.server_port}', args.route, size, theme, out, report)
                    try:
                        await case.launch(fixture_routes)
                        await case.enter()
                        await case.search_acceptance(args.smoke and not args.all_drawings)
                        if cohort:
                            await case.full_workflow(cohort, records, historical=not args.smoke or args.all_drawings)
                    except BaseException:
                        if case.page and not case.page.is_closed():
                            with contextlib.suppress(Exception):
                                await case.page.screenshot(path=str(case.out / 'failure.png'))
                        raise
                    case.phase = 'closing-context'
                    await case.context.close()
                    print(case.name + ' passed', flush=True)
            if args.treatments_only or (not args.smoke and not args.without_treatments):
                case = Case(browser, f'http://127.0.0.1:{server.server_port}', args.route, (1440, 1000), 'light', out, report, label='native-treatments')
                await case.launch()
                await case.treatment_matrix(cohort, records)
                case.phase = 'closing-context'
                await case.context.close()
            await browser.close()
        report['sourceUnchanged'] = report['sourceIdentity'] == source_identity(allow_pending=args.predecessor_fixture)
        report['runtimeTargetAfter'] = TARGET.record()
        if TARGET.package_root:
            report['packageUnchanged'] = report['runtimeTargetAfter'] == report['runtimeTarget']
            case.check('Exact package inventory remains unchanged', report['packageUnchanged'])
        if not args.smoke:
            case.check('Source remains unchanged throughout final acceptance', report['sourceUnchanged'])
        report['requestFailureClassification'] = classify_request_failures(report['failedRequests'])
        unexpected = report['requestFailureClassification']['unexpected']
        case.check('No unexplained runtime request failures', not unexpected, unexpected)
        case.check('Canonical vendor scripts load successfully', report['vendorResponses'] and all(r['status'] == 200 for r in report['vendorResponses']), report['vendorResponses'])
        report['status'] = 'passed' if not report['pageErrors'] and not report['consoleErrors'] else 'failed'
    except BaseException as error:
        report['status'] = 'interrupted' if isinstance(error, (KeyboardInterrupt, asyncio.CancelledError)) else 'failed'
        report['failure'] = str(error)
        report['traceback'] = traceback.format_exc()
        if case and case.page and not case.page.is_closed():
            with contextlib.suppress(Exception):
                await case.page.screenshot(path=str(case.out / 'failure.png'))
        raise
    finally:
        if case and case.context:
            case.phase = 'closing-context'
            with contextlib.suppress(Exception):
                await case.context.close()
        if server:
            server.shutdown()
            server.server_close()
        (out / 'report.json').write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n', encoding='utf8')
        print(json.dumps({'status': report['status'], 'checks': len(report['checks']), 'output': str(out)}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    add_package_arguments(parser)
    parser.add_argument('--route', choices=['direct', 'web'], default='direct')
    parser.add_argument('--cohort', choices=['broad', 'families', 'expansion'], default='broad', help='The prior cohorts or all Cell Structure/Stress, Tumor Microenvironment and Analysis Graphics drawings.')
    parser.add_argument('--smoke', action='store_true', help='Fast existing-form/search UI diagnosis while the authored cohort is prepared.')
    parser.add_argument('--all-drawings', action='store_true', help='Include the entire selected cohort and historical compatibility in a preliminary one-case --smoke run.')
    parser.add_argument('--edit-scope', choices=['all', 'representative'], default='all', help='Edit all expansion drawings, or six declared representative drawings in both Figure and Presentation. All cohort drawings are still inserted and saved/cold-opened in every case; a separately accepted all-drawing edit checkpoint is needed when using representative scope.')
    parser.add_argument('--predecessor-fixture', action='store_true', help='Diagnose existing artwork with explicit canonical predecessor route overrides; requires --smoke.')
    parser.add_argument('--treatments-only', action='store_true', help='Run every cohort drawing in all twelve actual native treatment/palette combinations.')
    parser.add_argument('--without-treatments', action='store_true', help='Skip a separately qualified native treatment/palette matrix.')
    parser.add_argument('--asset-id', action='append', default=[], help='Include this explicit cohort asset and all drawings/companions of its concept.')
    parser.add_argument('--output-dir', type=Path)
    asyncio.run(run(parser.parse_args()))
