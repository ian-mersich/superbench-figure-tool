"""Validate the finite endocrine supplement and exact two-batch lookup map."""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

def _load_original_supplement():
    helper_path = Path(__file__).resolve().with_name('style4_original_supplement.py')
    spec = importlib.util.spec_from_file_location('_style4_original_supplement', helper_path)
    if spec is None or spec.loader is None:
        raise ImportError(f'Cannot load sibling Style 4 supplement helper: {helper_path}')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


original = _load_original_supplement()

PREFIX = 'expansion-20261107'
MARKER = 'original-style4-companions.2026-11-07'
SOURCE = 'source.style4-original-companions.2026-11-07'
RIGHTS = 'rights.style4-original-companions.repository-cc0.2026-11-07'
POLICY = 'original-vectors.cc0.repository-policy.2026-11-07'
AGGREGATE_FILE = 'original-companions.json'
OLD_MANIFEST_SHA256 = '9149ed783517fd139a04a0eceb143a7576ed033918405a13beb4c83fa4d46244'
REGISTRY_ENTRY = {'id': 'style-4', 'name': 'Style 4',
    'path': 'style-4/manifest-corrected-20261017.json', 'asset_count': 550,
    'supplement': {'path': 'style-4/' + AGGREGATE_FILE, 'asset_count': 64}}


def validate(style_dir: Path, library: Path) -> dict:
    importer = original.load_importer()
    registry = json.loads(library.read_text(encoding='utf-8'))
    if registry.get('art_styles') != [REGISTRY_ENTRY]:
        raise ValueError('Endocrine Style 4 registration must bind exact 550-drawing coverage')
    base = style_dir / PREFIX
    manifest = json.loads((base / 'manifest.json').read_text(encoding='utf-8'))
    if (manifest.get('schema_version'), manifest.get('id'), manifest.get('asset_count'), manifest.get('supplement_id')) != ('1.0.0', 'style-4', 24, MARKER):
        raise ValueError('Endocrine Style 4 supplement identity mismatch')
    old = style_dir / 'manifest-corrected-20261017.json'
    if manifest.get('preserved_supplied_collection') != {'file': old.name, 'sha256': original.sha(old), 'asset_count': 486}:
        raise ValueError('Endocrine supplement historical source binding differs')
    catalog = {k: v for k, v in importer.load_catalog(library).items() if v['pack_id'] == 'endocrine-tissue'}
    rows = manifest.get('assets', [])
    if len(catalog) != 24 or len(rows) != 24 or {r.get('asset_id') for r in rows} != set(catalog):
        raise ValueError('Endocrine supplement must cover exactly its 24 drawings')
    if manifest.get('source_record_id') != SOURCE or manifest.get('rights_record_id') != RIGHTS:
        raise ValueError('Endocrine Style 4 manifest attribution differs')
    owned = {f'{PREFIX}/{name}' for name in ('manifest.json', 'rights-release-record.json', 'LICENSE-ASSETS-CC0-1.0.md')}
    signatures, paths = [], set()
    for row in rows:
        aid = row['asset_id']
        source = catalog[aid]
        relative = importer.safe_relative_path(row['file'])
        if not relative.startswith('svg/') or not relative.endswith('.svg') or relative.casefold() in paths:
            raise ValueError('Endocrine Style 4 path is invalid or duplicated: ' + aid)
        paths.add(relative.casefold())
        path = base / relative
        if not path.is_file() or path.is_symlink():
            raise ValueError('Endocrine Style 4 must use ordinary source files')
        svg = importer.parse_svg(path.read_bytes(), unique_ids=True)
        signature = importer.geometry_signature(svg)
        if original.sha(path) != row.get('sha256') or signature != row.get('geometry_sha256') or svg.get('viewBox') != '0 0 128 128':
            raise ValueError('Endocrine Style 4 source/geometry identity differs: ' + aid)
        if (row.get('source_pack_id') != 'endocrine-tissue'
                or row.get('source_asset_sha256') != hashlib.sha256(source['original']).hexdigest()
                or row.get('source_record_id') != SOURCE or row.get('rights_record_id') != RIGHTS):
            raise ValueError('Endocrine Style 4 attribution differs: ' + aid)
        expected_regions = importer.derive_regions(svg, source['asset']['editable_color_regions'])
        if row.get('editable_color_regions') != expected_regions or any(r.get('no_rendered_paint') for r in expected_regions):
            raise ValueError('Endocrine Style 4 parts must bind actual painted geometry: ' + aid)
        if signature == importer.geometry_signature(importer.parse_svg(source['original'])):
            raise ValueError('Endocrine Style 4 needs genuinely redrawn geometry: ' + aid)
        signatures.append(signature)
        owned.add(f'{PREFIX}/{relative}')
    if len(set(signatures)) != 24:
        raise ValueError('Endocrine Style 4 companions must be distinct drawings')
    audit = json.loads((base / 'rights-release-record.json').read_text(encoding='utf-8'))
    expected = dict(schema_id='figureStudio.scientificStyleSupplementRights.v1', supplement_id=MARKER,
        asset_count=24, source_record_id=SOURCE, rights_record_id=RIGHTS, license_policy=POLICY,
        selected_public_license='CC0-1.0', public_distribution_authorized=True,
        rights_basis='repository_policy_original_output', product_release_status='pending_quality_and_product_review',
        effective_date='2026-11-07', manifest_sha256=original.sha(base / 'manifest.json'),
        license_notice_sha256=original.sha(base / 'LICENSE-ASSETS-CC0-1.0.md'))
    for key, value in expected.items():
        if audit.get(key) != value:
            raise ValueError('Endocrine Style 4 rights/source binding differs: ' + key)
    if len(audit.get('original_construction', '')) < 80 or audit.get('assets') != [
            {k: r[k] for k in ('asset_id', 'sha256', 'geometry_sha256')} for r in rows]:
        raise ValueError('Endocrine Style 4 source inventory differs')
    actual = {f'{PREFIX}/{p.relative_to(base).as_posix()}' for p in base.rglob('*') if p.is_file()}
    if actual != owned:
        raise ValueError('Endocrine Style 4 unexpected/missing files: ' + str(sorted(actual ^ owned)))
    # The runtime consumes one flat supplement. Its rows are an exact path-
    # prefixed union, retaining all other historical row fields byte-for-value.
    aggregate = json.loads((style_dir / AGGREGATE_FILE).read_text(encoding='utf-8'))
    sources, combined = [], []
    for prefix in ('expansion-20261103', PREFIX):
        path = style_dir / prefix / 'manifest.json'
        child = json.loads(path.read_text(encoding='utf-8'))
        if prefix == 'expansion-20261103' and original.sha(path) != OLD_MANIFEST_SHA256:
            raise ValueError('Preserved November 3 Style 4 manifest changed')
        sources.append(dict(file=f'{prefix}/manifest.json', sha256=original.sha(path), asset_count=child['asset_count'], supplement_id=child['supplement_id']))
        combined.extend({**r, 'file': prefix + '/' + r['file']} for r in child['assets'])
    expected_aggregate = dict(schema_version='1.0.0', id='style-4', name='Style 4', asset_count=64,
        aggregate_id='original-style4-companions.aggregate.2026-11-07', source_supplements=sources, assets=combined)
    if aggregate != expected_aggregate:
        raise ValueError('Style 4 aggregate must be the exact ordered two-batch union')
    owned.add(AGGREGATE_FILE)
    return dict(status='PASS', asset_count=24, file_count=len(owned), owned_files=sorted(owned),
        aggregate_asset_count=64, total_style4_count=550)
