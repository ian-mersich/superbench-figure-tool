"""Scientific distinctions and editable vector constraints for 40 new drawings."""
from __future__ import annotations
import importlib.util
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

import pytest

ROOT=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location('tumor_analysis_seed',ROOT/'scripts/seed-tumor-analysis-assets.py')
seed=importlib.util.module_from_spec(SPEC);sys.modules[SPEC.name]=seed;SPEC.loader.exec_module(seed)
NS={'s':'http://www.w3.org/2000/svg'}


@pytest.mark.parametrize('pack_id,rows',[('tumor-microenvironment',seed.TME),('analysis-graphics',seed.ANALYSIS)])
def test_twenty_original_vectors_reproduce_with_two_forms_per_concept(tmp_path,pack_id,rows):
    p=seed.generate(pack_id,rows,tmp_path)
    assert p['asset_count']==20 and p['concept_count']==10
    variants={a['concept_id']:{b['form_id'] for b in p['assets'] if b['concept_id']==a['concept_id']} for a in p['assets']}
    assert len(variants)==10 and all(len(forms)==2 for forms in variants.values())
    signatures=set()
    for a in p['assets']:
        generated=tmp_path/pack_id/a['file'];canonical=ROOT/'assets/scientific-packs'/pack_id/a['file']
        assert generated.read_bytes()==canonical.read_bytes()
        xml=ET.parse(generated).getroot()
        assert xml.attrib['viewBox']=='0 0 128 128'
        regions={e.get('data-region') for e in xml.iter() if e.get('data-region')}
        assert regions=={r['id'] for r in a['editable_color_regions']}
        assert 3<=len(regions)<=6
        assert not any(e.tag.rsplit('}',1)[-1] in {'image','use','filter','script','foreignObject'} for e in xml.iter())
        geom=tuple((e.tag,tuple((k,v) for k,v in e.attrib.items() if k not in {'id','data-region','fill','stroke'})) for e in xml.iter() if e.tag.rsplit('}',1)[-1] not in {'title','desc','text'})
        assert geom not in signatures,a['id']
        signatures.add(geom)


def test_plot_templates_do_not_claim_measured_data_or_analysis_functions():
    pack=json.loads((ROOT/'assets/scientific-packs/analysis-graphics/asset-pack.json').read_text(encoding='utf8'))
    for a in pack['assets']:
        assert 'not measured data or an analysis result' in a['scientific_limitations']
        assert a['category']=='assay-workflow'
        assert 'template' in a['tags']
        assert a['scientific_references']
    limits={a['concept_id']:a['scientific_limitations'] for a in pack['assets']}
    assert 'not elapsed time' in limits['analysis.pseudotime_trajectory']
    assert 'time order' in limits['analysis.cell_tracking_trajectory']
    assert 'no causality' in limits['analysis.network_graph']


def test_survival_steps_and_plot_axis_meanings_are_conventional():
    base=ROOT/'assets/scientific-packs/analysis-graphics'
    def text(file):return ''.join(ET.parse(base/'svg'/file).getroot().itertext())
    assert 'UMAP 1' in text('umap_scatter_clusters.svg') and 'UMAP 2' in text('umap_scatter_clusters.svg')
    assert 'log2 fold change' in text('volcano_plot_overview.svg') and '−log10(q)' in text('volcano_plot_overview.svg')
    assert 'Relative value' in text('heatmap_matrix.svg')
    xml=ET.parse(base/'svg/kaplan_meier_curve_two_groups.svg').getroot()
    curves=[e for e in xml.iter() if e.get('data-region','').startswith('curve_')]
    assert len(curves)==2
    for g in curves:
        p=next(iter(g));assert 'C' not in p.get('d') and 'Q' not in p.get('d')
    assert any(e.get('data-region')=='censor_a' for e in xml.iter())
    assert any(e.get('data-region')=='censor_b' for e in xml.iter())


def test_cell_states_and_gradients_retain_scientific_limits():
    pack=json.loads((ROOT/'assets/scientific-packs/tumor-microenvironment/asset-pack.json').read_text(encoding='utf8'))
    limits={a['concept_id']:a['scientific_limitations'] for a in pack['assets']}
    assert 'universal marker' in limits['tme.cancer_associated_fibroblast']
    assert 'do not classify' in limits['tme.tumor_associated_neutrophil']
    assert 'not a universal M1/M2 binary' in limits['tme.macrophage_polarization_cue']
    assert 'Contact does not imply killing' in limits['tme.car_nk_cell']
    assert 'Uptake does not establish' in limits['tme.dendritic_antigen_uptake']
    assert 'differs from oxygen delivery' in limits['tme.lactate_metabolite_gradient']
    base=ROOT/'assets/scientific-packs/tumor-microenvironment/svg'
    for key in ['primary_follicle','germinal_center']:
        xml=ET.parse(base/f'tertiary_lymphoid_structure_{key}.svg').getroot()
        roles={e.get('data-region') for e in xml.iter()}
        assert {'b_zone','t_zone','follicle_center'}<=roles


def test_generator_cannot_overwrite_reviewed_rights_records(tmp_path):
    dest=tmp_path/'analysis-graphics';dest.mkdir()
    (dest/'asset-pack.json').write_text(json.dumps({'release_audit':{'status':'rights_cleared_quality_pending'}}),encoding='utf8')
    before=(dest/'asset-pack.json').read_bytes()
    with pytest.raises(ValueError,match='Refusing to overwrite reviewed rights'):
        seed.generate('analysis-graphics',seed.ANALYSIS,tmp_path)
    assert (dest/'asset-pack.json').read_bytes()==before


def test_render_only_preserves_separate_draft_catalog_and_rights(tmp_path):
    seed.generate('analysis-graphics',seed.ANALYSIS,tmp_path)
    dest=tmp_path/'analysis-graphics'
    protected={p.name:p.read_bytes() for p in dest.iterdir() if p.is_file()}
    seed.generate('analysis-graphics',seed.ANALYSIS,tmp_path,render_only=True)
    assert protected=={p.name:p.read_bytes() for p in dest.iterdir() if p.is_file()}
