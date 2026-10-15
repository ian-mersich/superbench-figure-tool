"""Finite, source-bound revision checks for the three 13 October families.

These pins describe one reviewed slice, rather than granting future revisions
or changing product-release policy. The original permission records remain
immutable and older SVGs are retained as independently verifiable predecessors.
"""
from __future__ import annotations
import hashlib,json
from pathlib import Path

REVISION='2026-10-13-family-expansion'
RECEIPT='family-expansion-2026-10-13.json'
SNAPSHOT='revisions/2026-10-13-family-expansion-predecessor'
PACK_COUNTS={'cell-architecture-transport':(16,28),'culture-models-assays':(12,24),'microbial-biology':(12,24)}
# Assigned only after scientific, original-image and native editor acceptance.
PINS={'cell-architecture-transport': {'catalog': 'ec0b221148b6b25b287437f605f532d59b84d784ed260f861fb0fb84f4f435f2', 'audit': '9bd7a54ed501ddfb24769995f1d3d56b173ec0454a04e87512446e87710816e9', 'receipt': '5b74bb139b1d164566aa9300b9d6961ff89e9f6db06310bc00d2916623fa6849', 'predecessor_catalog': '93cc9a8fb06d96d846d68235ab91367c38fdb0b6c3b5b9ff78c0ee6bb0830aa7', 'predecessor_audit': '34976414f7087454b75ba9435ca8c0ac2d83a6d90666ec58d5daa28544e3d3bd'}, 'culture-models-assays': {'catalog': 'f9e64bebee918b360cc97b9b4ec89b2e11d52195cf2abca5ac39ca723c7fa60d', 'audit': 'fcceb4028f164f2da85de5a58ac6d78f5152f2b00924895f619c071c4a829b0e', 'receipt': '00ccdf41ddcb9a8849a41f4ed862a18b68bddcbb25a60153554eb4c25286c930', 'predecessor_catalog': '9b3cc2f5fc8cd4f746bd0f35e398858914ad54cdd41e9949abf23cf46662079b', 'predecessor_audit': 'f1f9518feb703b28a7da88603e756a486a41ff7581c5be2128937e2025fffc25'}, 'microbial-biology': {'catalog': '9e17fa7d43ba1d7209c6cf8c895384bf8d34fc02c04f897d55417568dd1c6744', 'audit': 'dc1ec2475e6ff44b1c42b275ae9f3c4e35dc3c3535db37fd7a69ae4334f7c980', 'receipt': '8eaad1101e95d31b076d515f735a02f94c64bcbf8128839c87a66e451e16497a', 'predecessor_catalog': '0087755676428bb69ffe95369cc231db3c15b908b80253e4ed90c66c0c43ab09', 'predecessor_audit': 'e85c63faac8b03f518cfa2d5bb68a552b8e218863941b97f685847501cd71779'}}


def canonical(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()


def file_identity(path):
    return canonical(json.loads(path.read_text(encoding='utf8'))) if path.suffix=='.json' else hashlib.sha256(path.read_bytes().replace(b'\r\n',b'\n')).hexdigest()


def need(condition,message):
    if not condition:raise ValueError('Family expansion: '+message)


def validate(pack,base):
    base=Path(base)
    selected=pack.get('family_expansion_revision')
    if not selected:
        return set()
    pack_id=pack['id']
    need(pack_id in PACK_COUNTS and selected==REVISION and pack.get('family_expansion_receipt')==RECEIPT,'exact revision identity required')
    pins=PINS.get(pack_id)
    need(bool(pins),'scientific and native qualification pins are pending')
    receipt=json.loads((base/RECEIPT).read_text(encoding='utf8'))
    need(canonical(receipt)==pins['receipt'],'reviewed receipt exact identity mismatch')
    need(canonical(pack)==pins['catalog']==receipt['current_catalog_sha256'],'reviewed catalog exact identity mismatch')
    audit=json.loads((base/pack['release_audit']['file']).read_text(encoding='utf8'))
    need(canonical(audit)==pins['audit']==receipt['current_audit_sha256'],'reviewed audit exact identity mismatch')
    need(file_identity(base/pack['release_audit']['license_notice'])==receipt['current_license_notice_sha256'],'reviewed license notice exact identity mismatch')
    need(receipt.get('schema_id')=='superbench.scientificAssetFamilyRevision.v1' and receipt.get('revision_id')==REVISION and receipt.get('pack_id')==pack_id,'receipt schema or identity mismatch')
    review=receipt.get('review',{})
    need(all(review.get(k)==v for k,v in {'status':'accepted','scientific_review':'pass','visual_review':'pass','editor_checks':'pass'}.items()),'scientific, visual and native editor acceptance required')
    need(len(review.get('evidence',[]))>=5 and all(len(r.get('sha256',''))==64 for r in review['evidence']),'review evidence bindings are incomplete')
    before=json.loads((base/SNAPSHOT/'asset-pack.json').read_text(encoding='utf8'))
    old_audit=json.loads((base/SNAPSHOT/'rights-release-record.json').read_text(encoding='utf8'))
    need(canonical(before)==pins['predecessor_catalog'] and canonical(old_audit)==pins['predecessor_audit'],'predecessor catalog/audit exact identity mismatch')
    need(receipt['predecessor']['snapshot']==SNAPSHOT and receipt['predecessor']['catalog_sha256']==canonical(before) and receipt['predecessor']['audit_sha256']==canonical(old_audit),'receipt predecessor mismatch')
    need(json.loads((base/'rights-release-record.json').read_text(encoding='utf8'))==old_audit,'original rights audit must remain immutable')
    need(pack['rights_records']==before['rights_records'],'original owner permission changed')
    source=pack['source_records'][0]
    need(len(pack['source_records'])==1 and {k:v for k,v in source.items() if k!='family_expansion'}==before['source_records'][0],'original source record changed outside its explicit expansion')
    refinement=source.get('family_expansion',{})
    need(refinement.get('revision_id')==REVISION and refinement.get('created_on')=='2026-10-13' and bool(refinement.get('scientific_references')),'bounded scientific source extension required')
    need(pack['release_audit']['status']=='rights_cleared_quality_pending' and pack['release_audit']['product_release_status']=='pending_quality_and_product_review','editing qualification must retain pending product release')
    old={a['id']:a for a in before['assets']};current={a['id']:a for a in pack['assets']}
    expected_old,expected_current=PACK_COUNTS[pack_id]
    need(len(old)==expected_old and len(current)==expected_current and set(old)<=set(current),'finite asset cohort/stable predecessor ids mismatch')
    changed={r['asset_id']:r for r in receipt['changed_assets']}
    added={r['asset_id']:r for r in receipt['added_assets']}
    need(set(changed)==set(old) and set(added)==set(current)-set(old),'receipt must cover every refinement and exactly twelve additions')
    old_rows={r['asset_id']:r for r in old_audit['assets']}
    for asset_id,asset in current.items():
        row=(changed if asset_id in old else added)[asset_id]
        need(row['file']==asset['file'] and row['after_svg_sha256']==file_identity(base/asset['file']) and row['after_metadata_sha256']==canonical(asset),asset_id+': current art/metadata binding mismatch')
        need(asset['license']=='CC0-1.0' and asset['rights_record_id']==before['rights_records'][0]['id'] and asset['source_record_id']==source['id'],asset_id+': permission/source scope mismatch')
        if asset_id not in old:continue
        previous=old[asset_id]
        need(all(asset[k]==previous[k] for k in ['id','file','category','concept_id','rights_record_id','license']),asset_id+': stable identity or biological category changed')
        original=base/SNAPSHOT/previous['file']
        need(row['before_svg_sha256']==file_identity(original)==old_rows[asset_id]['sha256'] and row['before_metadata_sha256']==canonical(previous),asset_id+': predecessor art/metadata binding mismatch')
        need(row['before_svg_sha256']!=row['after_svg_sha256'],asset_id+': claimed refinement has no SVG change')
        current_regions={r['id']:r for r in asset['editable_color_regions']}
        for region in previous['editable_color_regions']:
            now=current_regions.get(region['id'],{})
            need(now.get('default')==region['default'] and now.get('paint','fill+stroke')==region.get('paint','fill+stroke'),asset_id+'/'+region['id']+': existing paint identity changed')
    declared=set()
    for row in receipt['preserved_files']:
        relative=row['file'];path=Path(relative)
        need(not path.is_absolute() and '..' not in path.parts and relative.startswith(SNAPSHOT+'/'), 'invalid predecessor file path')
        need(file_identity(base/path)==row['sha256'],relative+': historical file identity mismatch')
        declared.add(relative)
    need({SNAPSHOT+'/'+name for name in ['asset-pack.json','rights-release-record.json','LICENSE-ASSETS-CC0-1.0.md',*[a['file'] for a in before['assets']]]}<=declared,'complete predecessor inventory missing')
    return declared|{RECEIPT,'rights-release-record.json'}
