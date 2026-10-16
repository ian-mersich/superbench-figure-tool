"""Bounded checks for the new structures/stress drawings, not release approval."""
import importlib.util,json,re,runpy,sys,xml.etree.ElementTree as ET
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
PACK=ROOT/'assets/scientific-packs/cell-structure-stress'

def load():return json.loads((PACK/'asset-pack.json').read_text(encoding='utf8'))

def test_twenty_requested_concepts_have_two_true_forms_each():
 p=load();groups={}
 for a in p['assets']:groups.setdefault(a['concept_id'],[]).append(a)
 assert p['asset_count']==40 and p['concept_count']==len(groups)==20
 for group in groups.values():
  assert len(group)==2
  assert all(a['variant_axis']=='form' and a['style_variant']=='standard' for a in group)
  assert len({a['form_id']for a in group})==len({a['form_label']for a in group})==2
  roots=[ET.parse(PACK/a['file']).getroot() for a in group]
  # Ignore title/description: the actual drawing geometry differs.
  painted=lambda r:ET.tostring(ET.fromstring('<g>'+''.join(ET.tostring(e,encoding='unicode')for e in r if e.tag.split('}')[-1]not in {'title','desc'})+'</g>'))
  assert painted(roots[0])!=painted(roots[1])

def test_semantic_parts_have_names_and_safe_editable_geometry():
 for a in load()['assets']:
  svg=ET.parse(PACK/a['file']).getroot();regions=set();ids=[]
  assert svg.attrib['viewBox']=='0 0 128 128'
  assert a['editable_region_count']==len(a['editable_color_regions'])
  for e in svg.iter():
   assert e.tag.split('}')[-1]not in {'image','text','filter','foreignObject','script','use'}
   assert not any(k.split('}')[-1]=='href' or k.startswith('on') for k in e.attrib)
   if 'id'in e.attrib:ids.append(e.attrib['id'])
   if 'data-region'in e.attrib:
    assert 'id'in e.attrib;regions.add(e.attrib['data-region'])
  assert len(ids)==len(set(ids))
  assert regions=={r['id']for r in a['editable_color_regions']}

def test_primary_sources_and_nondiagnostic_limits_are_preserved():
 p=load();assets=p['assets']
 for a in assets:
  assert len(a['scientific_limitations'])>100
  assert all(r['doi'].startswith('10.')and r['figure']and 'no source artwork or geometry copied' in r['use']for r in a['scientific_references'])
 assert all('cannot establish'in a['scientific_limitations']for a in assets if '.extracellular_vesicle.'in a['id'])
 assert all('Detachment alone does not imply death'in a['scientific_limitations']for a in assets if '.anoikis.'in a['id'])
 assert all(re.search(r'diagnos|diagnostic',a['scientific_limitations'])for a in assets if any('.'+key+'.'in a['id'] for key in ['necrotic_cell','ferroptotic_cell','pyroptotic_cell','necroptotic_cell']))

def test_native_geometry_reproduces_without_copying_or_overwriting_rights(tmp_path):
 module=runpy.run_path(str(ROOT/'scripts/seed-cell-structure-stress-assets.py'))
 generated=tmp_path/'reproduction';module['generate'](generated,render_only=True)
 for a in load()['assets']:assert (generated/a['file']).read_bytes()==(PACK/a['file']).read_bytes()
 generated.mkdir(exist_ok=True)
 (generated/'rights-release-record.json').write_text('{"status":"a_separate_rights_decision"}')
 sentinel=generated/'svg/nucleolus_subcompartments.svg';sentinel.write_text('do not mutate before rejecting')
 with pytest.raises(ValueError,match='Refusing'):module['generate'](generated)
 with pytest.raises(ValueError,match='Refusing'):module['generate'](generated,render_only=True)
 assert sentinel.read_text()=='do not mutate before rejecting'
 assert json.loads((generated/'rights-release-record.json').read_text())['status']=='a_separate_rights_decision'
