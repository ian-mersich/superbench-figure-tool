#!/usr/bin/env python3
"""Reproduce forty original drawings and draft records; never invent a rights grant.

The destination must not contain a released audit. Render-only permits geometry
reproduction in a fresh directory without creating catalog or rights records.
"""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path
import cell_structure_stress_renderers as art

ROOT=Path(__file__).resolve().parents[1]
PACK_ID='cell-structure-stress'
PACK=ROOT/'assets/scientific-packs'/PACK_ID
DATE='2026-10-15'
SOURCE_ID='source.cell-structure-stress.original.2026-10-15'
RIGHTS_ID='rights.cell-structure-stress.pending.2026-10-15'
STATEMENT=('Original editable SVG coordinates authored afresh for cell structures and cell stress. '
 'Primary literature supports biological topology and explicit limitations only. No published image, '
 'proprietary asset-library artwork, screenshot, tracing, measured coordinates, sequence, or third-party '
 'vector component was incorporated. This original-art record does not grant rights or approve release.')

def write_json(path,value):
 path.parent.mkdir(parents=True,exist_ok=True)
 path.write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n',encoding='utf-8',newline='\n')

def generate(destination=PACK,render_only=False):
 audit_path=destination/'rights-release-record.json'
 if audit_path.exists() and json.loads(audit_path.read_text(encoding='utf-8')).get('status')!='draft_review_pending':
  raise ValueError('Refusing to overwrite a separately authorized contribution; use --render-only with a fresh destination for geometry reproduction')
 data=json.loads((ROOT/'scripts/cell_structure_stress_science.json').read_text(encoding='utf-8'))
 references={r['id']:r for r in data['references']}
 source={'id':SOURCE_ID,'kind':'clean_room_generation_record','pack_id':PACK_ID,
  'scope':'all_assets_in_pack','created_on':DATE,'generated_by':'Figure Studio AI-assisted original SVG authoring',
  'third_party_material':'none_declared','statement':STATEMENT,'scientific_references':list(references.values())}
 rights={'id':RIGHTS_ID,'kind':'draft_rights_review','pack_id':PACK_ID,'scope':'all_assets_in_pack',
  'status':'draft_review_pending','public_distribution_authorized':False,'selected_public_license':None,
  'rights_basis':'original_output_pending_owner_review','third_party_material':'none_declared','effective_date':None,
  'statement':'Original contribution created on 2026-10-15. A new prospective rights decision must be recorded before public distribution; no historical owner grant is copied or extended by this generator.',
  'qualification':'Source and provenance are declared for independent review. Rights selection, independent scientific and visual review, and product qualification are separate decisions; none is asserted by this draft.'}
 assets=[]
 for c in data['concepts']:
  concept='cellstress.'+c['category'].replace('-','_')+'.'+c['key']
  for index,(form_id,form_label,description) in enumerate(c['forms']):
   aid=concept+'.'+form_id
   file='svg/'+c['key']+'_'+form_id+'.svg'
   regions=art.regions_for(c['key'],index)
   svg=art.render_svg(c['key'],index,c['name']+' — '+form_label,description+' '+c['limits'])
   target=destination/file;target.parent.mkdir(parents=True,exist_ok=True);target.write_text(svg,encoding='utf-8',newline='\n')
   assets.append({'id':aid,'concept_id':concept,'name':c['name'],'scientific_name':c['name'],
    'category':c['category'],'subcategory':'Cell structures and cell stress','synonyms':c['synonyms'],
    'tags':list(dict.fromkeys([c['key'].replace('_',' '),*c['synonyms'],form_label,'cell biology','editable vector','schematic'])),
    'description':description,'file':file,'source_type':'clean_room_original_vector',
    'license':'FS-ORIGINAL-DRAFT','provenance':STATEMENT,'source_record_id':SOURCE_ID,'rights_record_id':RIGHTS_ID,
    'style_family':'figure-studio-soft-line-v1','variant_axis':'form','style_variant':'standard',
    'form_id':form_id,'form_label':form_label,
    'review_status':'independent_scientific_and_visual_review_pending_2026_10_15',
    'style_status':'harmonized_soft_line_v1','mvp_quality':'original_draft','quality_tier':'draft',
    'editable_region_count':len(regions),'editable_color_regions':regions,
    'reviewer_notes':'Original scientific forms await independent review of original 64, 256 and 512 px captures in all three drawing styles. No public rights or product-release approval is inferred.',
    'scientific_references':[references[r] for r in c['refs']],'scientific_limitations':c['limits']})
 if render_only:return assets
 audit_id=PACK_ID+'.draft-review.2026-10-15'
 notice='LICENSE-ASSETS-DRAFT.md'
 release={'file':'rights-release-record.json','audit_id':audit_id,'audit_date':DATE,'status':'draft_review_pending',
  'release_effective_date':None,'concept_count':20,'asset_count':40,'public_distribution_authorized':False,
  'selected_public_license':None,'license_notice':notice}
 categories={}
 for a in assets:
  cat=a['category'];categories.setdefault(cat,{'concepts':set(),'style_count':0})
  categories[cat]['concepts'].add(a['concept_id']);categories[cat]['style_count']+=1
 manifest={'schema_version':'0.3.0','id':PACK_ID,'name':'Cell Structures & Stress',
  'description':'Editable nuclear bodies, cell-surface structures, vesicles, protrusions, death mechanisms and stress responses, with two biological forms for each concept.',
  'style_family':'figure-studio-soft-line-v1','style_families':['figure-studio-soft-line-v1'],
  'qa_status':'independent_scientific_and_visual_review_pending_2026_10_15','asset_count':40,'concept_count':20,
  'category_counts':{k:{'concept_count':len(v['concepts']),'style_count':v['style_count']}for k,v in categories.items()},
  'release_audit':release,'source_records':[source],'rights_records':[rights],
  'style_tokens':{'viewBox':'0 0 128 128','target_padding_units':'14-18','primary_outline':'#26323D',
   'primary_outline_width':3.5,'detail_outline_width':2.75,'line_cap':'round','line_join':'round',
   'palette':{k:v for k,v in art.COLORS.items()}},
  'source_policy':{'allowed_sources':['Original SVG geometry and scientific concepts from primary research'],
   'disallowed_sources':['Tracing or reuse of published or proprietary artwork','Measured images, coordinates or numerical observations represented as decorative marks'],
   'reference_use':'Biological concepts and limitations only. No source artwork incorporated.'},
  'license_definitions':{'FS-ORIGINAL-DRAFT':{'label':'Original draft; rights selection pending','reuse':'Not authorized for public distribution until a prospective contribution decision is recorded.','public_distribution_authorized':False,'selected_public_license':None}},
  'assets':assets}
 audit={k:v for k,v in release.items() if k!='file'}
 audit.update(schema_id='figureStudio.scientificAssetLicenseReleaseAudit.v1',pack_id=PACK_ID,
  rights_cleared_count=0,third_party_component_count=0,license_selection_pending_count=40,
  rights_basis={'status':'original_output_pending_owner_review','pack_id':PACK_ID,'authorization_record_id':RIGHTS_ID},
  source_records=[source],rights_records=[rights],license_candidates=[{'id':'CC0-1.0','selected':False}],
  release_blocker='New contribution rights decision, independent scientific and visual review, and shared Figure product QA remain pending.',
  assets=[{'asset_id':a['id'],'file':a['file'],'sha256':hashlib.sha256((destination/a['file']).read_bytes()).hexdigest(),
   'provenance_sha256':hashlib.sha256(a['provenance'].encode()).hexdigest(),'source_type':a['source_type'],
   'source_record_id':SOURCE_ID,'rights_record_id':RIGHTS_ID,'lineage':'workspace_generated_clean_room_original',
   'current_license':'FS-ORIGINAL-DRAFT','rights_basis':'original_output_pending_owner_review',
   'third_party_material':'none_declared','provenance_status':'original_draft_review_pending',
   'release_disposition':'draft_not_authorized_for_public_distribution'}for a in assets])
 write_json(destination/'asset-pack.json',manifest);write_json(audit_path,audit)
 (destination/notice).write_text('# Original draft assets\n\nThese 40 original editable drawings were authored on 2026-10-15. No historical rights grant is extended by this record. Public license selection and independent scientific, visual and product review remain pending. Scientific references inform concepts only; their images, geometry and measured observations are not included.\n',encoding='utf-8')
 return assets

if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--destination',type=Path,default=PACK);parser.add_argument('--render-only',action='store_true')
 args=parser.parse_args();assets=generate(args.destination,args.render_only)
 print(f'{len(assets)} original SVGs /20 concepts generated; no owner grant or release approval inferred')
