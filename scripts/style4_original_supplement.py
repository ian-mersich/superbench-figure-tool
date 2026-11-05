"""Finite original Style 4 companions; historical supplied artwork stays exact."""
from __future__ import annotations
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PREFIX='expansion-20261103'
MARKER='original-style4-companions.2026-11-03'
SOURCE='source.style4-original-companions.2026-11-03'
RIGHTS='rights.style4-original-companions.repository-cc0.2026-11-03'
POLICY='original-vectors.cc0.repository-policy.2026-11-03'
PACKS={'neurobiology','tissue-vascular'}
REGISTRY_ENTRY={'id':'style-4','name':'Style 4','path':'style-4/manifest-corrected-20261017.json',
    'asset_count':526,'supplement':{'path':f'style-4/{PREFIX}/manifest.json','asset_count':40}}


def load_importer():
    spec=importlib.util.spec_from_file_location('_style4_original_importer',ROOT/'scripts/import-style4-library.py')
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value)
    return value


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()


def validate(style_dir: Path, library: Path) -> dict:
    importer=load_importer();base=style_dir/PREFIX
    registry=json.loads(library.read_text(encoding='utf-8'))
    if registry.get('art_styles') != [REGISTRY_ENTRY]: raise ValueError('Original Style 4 supplement registry must bind exact526coverage')
    manifest=json.loads((base/'manifest.json').read_text(encoding='utf-8'))
    if (manifest.get('schema_version'),manifest.get('id'),manifest.get('asset_count'),manifest.get('supplement_id')) != ('1.0.0','style-4',40,MARKER):
        raise ValueError('Original Style 4 supplement identity mismatch')
    old=style_dir/'manifest-corrected-20261017.json'
    if manifest.get('preserved_supplied_collection') != {'file':old.name,'sha256':sha(old),'asset_count':486}:
        raise ValueError('Historical Style 4 manifest identity changed')
    all_assets=importer.load_catalog(library)
    cohort={key:value for key,value in all_assets.items() if value['pack_id'] in PACKS}
    rows=manifest.get('assets',[])
    if len(cohort)!=40 or len(rows)!=40 or {r.get('asset_id') for r in rows} != set(cohort):
        raise ValueError('Original Style 4 supplement must cover every new drawing exactly once')
    owned={f'{PREFIX}/manifest.json',f'{PREFIX}/rights-release-record.json',f'{PREFIX}/LICENSE-ASSETS-CC0-1.0.md'}
    signatures=[]
    for row in rows:
        aid=row['asset_id'];source=cohort[aid];relative=importer.safe_relative_path(row['file'])
        if not relative.startswith('svg/') or not relative.endswith('.svg'):raise ValueError('Original Style 4 source path is invalid')
        path=base/relative
        if path.is_symlink() or not path.is_file():raise ValueError('Original Style 4 source must be an ordinary file')
        raw=path.read_bytes();svg=importer.parse_svg(raw,unique_ids=True)
        signature=importer.geometry_signature(svg)
        if sha(path)!=row['sha256'] or signature!=row['geometry_sha256'] or svg.get('viewBox')!='0 0 128 128':raise ValueError('Original Style 4 SVG identity/geometry mismatch: '+aid)
        if (row.get('source_pack_id')!=source['pack_id'] or row.get('source_asset_sha256')!=hashlib.sha256(source['original']).hexdigest()
                or row.get('source_record_id')!=SOURCE or row.get('rights_record_id')!=RIGHTS):
            raise ValueError('Original Style 4 source attribution mismatch: '+aid)
        if row['editable_color_regions']!=importer.derive_regions(svg,source['asset']['editable_color_regions']):
            raise ValueError('Original Style 4 editable parts do not match actual paint: '+aid)
        if signature==importer.geometry_signature(importer.parse_svg(source['original'])):
            raise ValueError('Original Style 4 requires genuine companion geometry: '+aid)
        owned.add(f'{PREFIX}/{relative}');signatures.append(signature)
    if len(set(signatures))!=40:raise ValueError('Original Style 4 companions must be distinct drawings')
    audit=json.loads((base/'rights-release-record.json').read_text(encoding='utf-8'))
    expected={'schema_id':'figureStudio.scientificStyleSupplementRights.v1','supplement_id':MARKER,'asset_count':40,
        'source_record_id':SOURCE,'rights_record_id':RIGHTS,'license_policy':POLICY,'selected_public_license':'CC0-1.0',
        'public_distribution_authorized':True,'product_release_status':'pending_quality_and_product_review',
        'manifest_sha256':sha(base/'manifest.json'),'license_notice_sha256':sha(base/'LICENSE-ASSETS-CC0-1.0.md')}
    for key,value in expected.items():
        if audit.get(key)!=value:raise ValueError('Original Style 4 rights/source binding differs: '+key)
    if audit.get('assets')!=[{'asset_id':r['asset_id'],'sha256':r['sha256'],'geometry_sha256':r['geometry_sha256']}for r in rows]:
        raise ValueError('Original Style 4 rights inventory differs')
    if audit.get('rights_basis')!='repository_policy_original_output' or len(audit.get('original_construction',''))<80:
        raise ValueError('Original Style 4 must retain its own prospective source attribution')
    actual={f'{PREFIX}/{p.relative_to(base).as_posix()}' for p in base.rglob('*') if p.is_file()}
    if actual!=owned:raise ValueError('Unexpected/missing original Style 4 supplement files: '+str(sorted(actual^owned)))
    return {'status':'PASS','asset_count':40,'total_style4_count':526,'file_count':len(owned),'owned_files':sorted(owned)}
