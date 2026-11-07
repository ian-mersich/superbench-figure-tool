"""Original editable endocrine, reproductive and testicular tissue SVGs.

Generic topology studies for the asset library; forms are not to scale and do
not encode hormone identity, physiological state, or quantitative abundance.
"""
from __future__ import annotations

from html import escape


REFERENCES = [
    {"id":"anterior_pituitary_topology", "citation":"Yoshitomi M, et al. Three-dimensional ultrastructural analyses of anterior pituitary gland expose spatial relationships between endocrine cell secretory granule localization and capillary distribution. Sci Rep. 2016;6:36019.", "doi":"10.1038/srep36019", "url":"https://doi.org/10.1038/srep36019", "design_decision":"Supports the spatial arrangement of anterior-lobe endocrine cells relative to capillary profiles; the drawing uses generic cords and vascular channels without assigning endocrine cell classes."},
    {"id":"posterior_pituitary_topology", "citation":"Zhu CG, Chen AQ, Liu QY, Wei Y, Peng XL. An immunoelectron microscopic study of peptide substances in the rat neurohypophysis. J Tongji Med Univ. 1989;9(1):29–35.", "doi":"10.1007/BF02933741", "url":"https://doi.org/10.1007/BF02933741", "design_decision":"Supports neural terminals distributed near capillaries and pituicytes; no specific peptide identity or release event is assigned."},
    {"id":"median_eminence_topology", "citation":"Buma P, Nieuwenhuys R. Ultrastructural characterization of exocytotic release sites in different layers of the median eminence of the rat. Cell Tissue Res. 1988;252:107–114.", "doi":"10.1007/BF00213831", "url":"https://doi.org/10.1007/BF00213831", "design_decision":"Supports external-zone neuronal terminals adjacent to the primary portal capillary plexus and distinction from deeper neural tissue; no peptide identity or pituitary target is depicted."},
    {"id":"ovarian_follicle_topology", "citation":"Abdelnaby EA, Yasin NA, Abouelela YS, Rashad E, Daghash SM, El-Sherbiny HR. Ovarian, uterine, and luteal vascular perfusions during follicular and luteal phases in the adult cyclic female rabbits with special orientation to their histological detection of hormone receptor. BMC Vet Res. 2022;18:301.", "doi":"10.1186/s12917-022-03390-6", "url":"https://doi.org/10.1186/s12917-022-03390-6", "design_decision":"Informs the antral follicle arrangement of oocyte, granulosa, antral space and peripheral thecal support; vascular cue remains outside granulosa."},
    {"id":"corpus_luteum_topology", "citation":"Abdelnaby EA, Yasin NA, Abouelela YS, Rashad E, Daghash SM, El-Sherbiny HR. Ovarian, uterine, and luteal vascular perfusions during follicular and luteal phases in the adult cyclic female rabbits with special orientation to their histological detection of hormone receptor. BMC Vet Res. 2022;18:301.", "doi":"10.1186/s12917-022-03390-6", "url":"https://doi.org/10.1186/s12917-022-03390-6", "design_decision":"Supports luteal cell populations separated by capillaries and vascular connective capsule; the schematic omits species-specific luteal cell distinctions."},
    {"id":"leydig_interstitium_topology", "citation":"Stanley E, Lin CY, Jin S, Liu J, Sottas CM, Ge R, Zirkin BR, Chen H. Identification, proliferation, and differentiation of adult Leydig stem cells. Endocrinology. 2012;153(10):5002–5010.", "doi":"10.1210/en.2012-1417", "url":"https://doi.org/10.1210/en.2012-1417", "design_decision":"Supports Leydig/interstitial localization between seminiferous tubules; only tissue position and cluster arrangement are shown, without inferring hormone identity from shape."},
]

CONCEPTS = {
 "anterior_pituitary":{"key":"anterior_pituitary","name":"Anterior pituitary","subcategory":"pituitary gland","synonyms":["adenohypophysis","pars distalis"],"forms":[{"id":"cords_longitudinal","label":"Interlacing cords","description":"Glandular cell cords run between branching sinusoidal channels in a longitudinal tissue field."},{"id":"cords_radial","label":"Radial tissue field","description":"A second oblique field shows branching cords and vascular spaces in a compact arrangement."}],"limits":"Generic anterior-lobe parenchyma. Cells are not assigned to hormone-producing classes; vascular geometry is illustrative.","refs":["anterior_pituitary_topology"]},
 "posterior_pituitary":{"key":"posterior_pituitary","name":"Posterior pituitary","subcategory":"pituitary gland","synonyms":["neurohypophysis","neural lobe"],"forms":[{"id":"longitudinal_neural_lobe","label":"Longitudinal neural lobe","description":"Axonal profiles and terminal swellings approach a sinusoidal capillary among pituicyte processes."},{"id":"transverse_neural_lobe","label":"Transverse neural lobe","description":"A compact cross-field shows capillary profiles surrounded by axon terminals and pituicyte processes."}],"limits":"Neural-lobe topology only. Does not depict hormone synthesis, identify oxytocin or vasopressin, or imply the median eminence is part of the neural lobe.","refs":["posterior_pituitary_topology"]},
 "median_eminence":{"key":"median_eminence","name":"Median eminence","subcategory":"hypothalamic neurovascular interface","synonyms":["external zone of median eminence","hypophysial portal interface"],"forms":[{"id":"external_zone_sagittal","label":"Sagittal neurovascular section","description":"Hypothalamic terminal profiles approach a portal capillary across a tanycyte-associated boundary from deeper neural tissue."},{"id":"external_zone_field","label":"Portal interface field","description":"Several terminal profiles border portal capillaries along an explicit boundary with the neural compartment."}],"limits":"Shows a simplified external-zone interface. It is distinct from the posterior pituitary and does not assign a releasing hormone or downstream effect.","refs":["median_eminence_topology"]},
 "ovarian_follicle":{"key":"ovarian_follicle","name":"Antral ovarian follicle","subcategory":"ovary","synonyms":["antral follicle","Graafian follicle"],"forms":[{"id":"eccentric_oocyte","label":"Eccentric oocyte section","description":"An eccentric oocyte with a distinct zona pellucida is surrounded by granulosa and borders the antral space; the outer theca forms a vascularized rim."},{"id":"sector_section","label":"Sector section","description":"An oblique section retains a distinct zona pellucida around the oocyte, granulosa, antrum, theca and peripheral vascular relationship."}],"limits":"Generic antral follicle section. Not to scale; does not specify species, cycle stage, or ovulatory readiness.","refs":["ovarian_follicle_topology"]},
 "corpus_luteum":{"key":"corpus_luteum","name":"Corpus luteum","subcategory":"ovary","synonyms":["luteal tissue","luteinized follicle"],"forms":[{"id":"folded_luteal_tissue","label":"Folded luteal tissue","description":"Luteal cell cords and intervening capillary branches form a folded tissue field within a connective boundary."},{"id":"radial_luteal_tissue","label":"Radial luteal tissue","description":"Luteal cell cords radiate around an optional central cavity and are interspersed with capillary branches."}],"limits":"Generic luteal tissue. Does not distinguish granulosa- from theca-derived luteal cells, stage, species, or endocrine activity.","refs":["corpus_luteum_topology"]},
 "leydig_interstitium":{"key":"leydig_interstitium","name":"Leydig-cell interstitium","subcategory":"testis","synonyms":["testicular interstitium","interstitial Leydig cells"],"forms":[{"id":"paired_tubules","label":"Paired tubule profiles","description":"Two seminiferous-tubule cross-sections show a central lumen and surrounding epithelium; interstitial cell clusters and a small vessel lie between them."},{"id":"tubule_corner","label":"Tubule junction field","description":"Four seminiferous-tubule cross-sections frame an interstitial pocket containing cell clusters and a small vessel."}],"limits":"Location schematic only. Cell shape does not encode hormone production, developmental state, or cell identity beyond the named interstitial concept.","refs":["leydig_interstitium_topology"]},
}

COLORS={"gland":"#DDBA9B","sinusoid":"#D8EDF5","neural":"#B5A9D5","terminal":"#E5B76C","pituicyte":"#83B7AE","boundary":"#D3C1A0","oocyte":"#E7B84D","zona_pellucida":"#FFFDF7","granulosa":"#D5B5D8","antrum":"#E8F4F8","theca":"#9DC99F","luteal":"#D9A27B","vessel":"#C44D4D","interstitium":"#D8C5A4","tubule":"#D5B5D8","tubule_lumen":"#FFF8E8","outline":"#3C505B"}
REGIONS={
"anterior_pituitary":[("gland","Glandular cell cords"),("sinusoid","Sinusoidal vascular spaces"),("outline","Structural outlines")],
"posterior_pituitary":[("neural","Neural tissue"),("terminal","Axon terminals"),("pituicyte","Pituicytes"),("sinusoid","Capillary spaces"),("outline","Structural outlines")],
"median_eminence":[("neural","Neural tissue"),("terminal","Neurosecretory terminal profiles"),("boundary","Tanycyte-associated boundary"),("sinusoid","Portal capillaries"),("outline","Structural outlines")],
"ovarian_follicle":[("theca","Theca layer"),("vessel","Thecal capillaries"),("granulosa","Granulosa layer"),("antrum","Antral space"),("oocyte","Oocyte"),("zona_pellucida","Zona pellucida"),("outline","Structural outlines")],
"corpus_luteum":[("luteal","Luteal cell cords"),("vessel","Capillary network"),("antrum","Central cavity"),("outline","Structural outlines")],
"leydig_interstitium":[("interstitium","Interstitial cell clusters"),("vessel","Interstitial vessel"),("tubule","Seminiferous-tubule epithelium"),("tubule_lumen","Seminiferous-tubule lumen"),("outline","Structural outlines")],}

def regions_for(key: str,index: int)->list[dict[str,str]]:
    if key not in CONCEPTS or index not in (0,1): raise KeyError((key,index))
    return [{"id":rid,"label":label,"default":COLORS[rid]} for rid,label in REGIONS[key]]

def _p(d,fill=None,stroke=None,w=1.7,more=""):
    attrs=f'fill="{fill or "none"}"'
    if stroke: attrs+=f' stroke="{stroke}" stroke-width="{w}" stroke-linecap="round" stroke-linejoin="round"'
    return f'<path d="{d}" {attrs} {more}/>'

def _e(cx,cy,rx,ry,fill,stroke=None,w=1.5):
    return f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="{fill}"'+(f' stroke="{stroke}" stroke-width="{w}"' if stroke else '')+'/>'

def _draw(key,index,style4):
    q={rid:"" for rid,_ in REGIONS[key]}; ink=COLORS['outline']; soft=style4
    if key=='anterior_pituitary':
        # Distinct longitudinal cords versus an oblique compact network.
        if index==0:
            vessels=['M22 23Q34 35 24 47T24 72T22 104','M58 20Q47 31 59 44T57 68T60 91T55 108','M97 19Q86 31 98 45T95 70T101 94T96 109']
            if soft: vessels=['M23 18C20 38 25 49 22 66C19 83 24 96 21 110','M64 17C61 36 66 48 63 66C60 83 66 97 63 111','M104 18C101 37 106 50 103 67C100 84 105 97 102 110']
            q['sinusoid']=''.join(_p(d,None,COLORS['sinusoid'],10 if not soft else 8) for d in vessels)
            cells=[(36,27),(43,43),(37,59),(40,81),(39,99),(76,25),(77,43),(73,59),(77,79),(76,99),(111,32),(111,58),(112,83)]
            if soft: cells=[(x+(-3 if i%2 else 2),y+(-2 if i%3==0 else 2)) for i,(x,y) in enumerate(cells)]
            q['gland']=''.join(_e(x,y,6 if not soft else 7,8,COLORS['gland']) for x,y in cells)
        else:
            channels=['M19 37Q37 24 51 38T79 37T108 31','M18 73Q36 60 51 74T80 71T110 77','M34 20Q27 43 40 55T33 99','M84 19Q72 42 86 56T78 106']
            if soft: channels=['M17 33Q40 21 55 39T84 33T111 36','M19 78Q36 57 56 77T85 70T110 82','M37 17Q20 42 42 59T31 108','M87 18Q69 40 90 59T75 108']
            q['sinusoid']=''.join(_p(d,None,COLORS['sinusoid'],9 if not soft else 7) for d in channels)
            cells=[(28,54),(52,27),(62,53),(54,91),(99,57),(98,100),(75,98),(36,99)]
            q['gland']=''.join(_e(x,y,7,6 if not soft else 8,COLORS['gland']) for x,y in cells)
        q['outline']= ''.join(_p(d,None,ink,1.1) for d in vessels+channels) if False else ''
        q['outline']+= ''.join(_p(d,None,ink,1.15) for d in (vessels if index==0 else channels))
    elif key=='posterior_pituitary':
        if index==0:
            q['neural']=_p('M17 25Q37 38 28 55T36 84Q44 99 27 110L17 108Q32 95 23 82T17 55Q29 37 17 25Z',COLORS['neural'])+_p('M55 19Q76 37 63 54T70 82Q83 97 64 111L54 108Q73 93 58 80T53 54Q67 37 55 19Z',COLORS['neural'])+_p('M94 20Q111 36 99 52T107 82Q115 96 99 109L91 106Q106 92 94 80T91 53Q103 37 94 20Z',COLORS['neural'])
            if soft: q['neural']=_p('M15 21Q42 34 28 57T40 86Q45 101 21 112L14 106Q34 93 22 80T14 53Q31 34 15 21Z',COLORS['neural'])+_p('M55 18Q82 35 64 57T74 84Q86 100 58 112L52 106Q77 92 58 78T51 54Q72 35 55 18Z',COLORS['neural'])+_p('M97 18Q116 38 100 55T110 84Q120 98 96 111L89 105Q112 91 93 77T88 52Q108 34 97 18Z',COLORS['neural'])
            q['sinusoid']=_e(112,65,8,32,COLORS['sinusoid'])
            terms=[(84,37),(94,63),(83,88),(103,48),(101,78)]
            q['terminal']=''.join(_e(x,y,5,4,COLORS['terminal']) for x,y in terms)
            q['pituicyte']=''.join(_p(f'M{x} {y}q-11 -8 -15 -2m15 2q7 -12 13 -12m-13 12q8 5 13 14',None,COLORS['pituicyte'],2.6) for x,y in [(43,39),(71,77),(37,93)])
        else:
            q['neural']=_p('M18 20Q47 14 64 28T109 24L111 43Q82 49 64 38T18 43Z',COLORS['neural'])+_p('M18 85Q47 78 64 91T109 86L109 107Q82 112 64 101T18 106Z',COLORS['neural'])
            if soft:q['neural']=_p('M15 18Q44 10 65 28T112 20L114 42Q83 52 62 37T15 44Z',COLORS['neural'])+_p('M15 84Q46 75 66 92T113 83L112 109Q81 115 62 101T15 110Z',COLORS['neural'])
            caps=[(39,64,12,9),(78,64,13,10),(104,59,7,10)]
            q['sinusoid']=''.join(_e(x,y,rx,ry,COLORS['sinusoid']) for x,y,rx,ry in caps)
            q['terminal']=''.join(_e(x,y,4.5,4,COLORS['terminal']) for x,y in [(28,51),(53,49),(65,78),(94,76),(102,48),(85,49)])
            q['pituicyte']=''.join(_p(d,None,COLORS['pituicyte'],2.7) for d in ['M23 67q-12 -5 -14 -15m14 15q-8 10 -15 10','M61 62q-4 -14 -12 -18m12 18q9 -10 14 -14','M91 67q-10 -4 -12 -14m12 14q8 9 15 8'])
        if soft:
            outline_paths=(['M15 21Q42 34 28 57T40 86Q45 101 21 112L14 106Q34 93 22 80T14 53Q31 34 15 21Z','M55 18Q82 35 64 57T74 84Q86 100 58 112L52 106Q77 92 58 78T51 54Q72 35 55 18Z','M97 18Q116 38 100 55T110 84Q120 98 96 111L89 105Q112 91 93 77T88 52Q108 34 97 18Z'] if index==0 else ['M15 18Q44 10 65 28T112 20L114 42Q83 52 62 37T15 44Z','M15 84Q46 75 66 92T113 83L112 109Q81 115 62 101T15 110Z'])
            q['outline']=''.join(_p(d,None,ink,1.1) for d in outline_paths)
        else:
            q['outline']=''.join(_p(d,None,ink,1.1) for d in (['M17 25Q37 38 28 55T36 84Q44 99 27 110L17 108Q32 95 23 82T17 55Q29 37 17 25Z','M55 19Q76 37 63 54T70 82Q83 97 64 111L54 108Q73 93 58 80T53 54Q67 37 55 19Z','M94 20Q111 36 99 52T107 82Q115 96 99 109L91 106Q106 92 94 80T91 53Q103 37 94 20Z'] if index==0 else ['M18 20Q47 14 64 28T109 24L111 43Q82 49 64 38T18 43Z','M18 85Q47 78 64 91T109 86L109 107Q82 112 64 101T18 106Z']))
    elif key=='median_eminence':
        if index==0:
            q['neural']=_p('M15 18H112V43Q81 40 61 48T15 45Z',COLORS['neural'])
            q['boundary']=''.join(_p(f'M{x} 42Q{x+5} 48 {x+2} 59',None,COLORS['boundary'],3.4) for x in (28,60,92))
            q['sinusoid']=_p('M18 88Q41 80 62 87T111 82V104Q83 110 62 101T18 108Z',COLORS['sinusoid'])
            q['terminal']=''.join(_p(d,COLORS['terminal']) for d in ['M24 63Q32 55 39 65L42 79Q32 74 24 78Z','M53 62Q62 55 69 65L72 79Q61 74 53 78Z','M84 62Q93 54 100 65L103 78Q93 74 84 78Z'])
            if soft:
                q['neural']=_p('M13 16H115V43Q78 37 59 49T13 47Z',COLORS['neural'])
                q['boundary']=''.join(_p(f'M{x} 43Q{x+7} 49 {x+2} 61',None,COLORS['boundary'],4) for x in (23,57,91))
                q['sinusoid']=_p('M15 91Q39 77 63 88T114 80V108Q80 113 60 102T15 111Z',COLORS['sinusoid'])
                q['terminal']=''.join(_p(d,COLORS['terminal']) for d in ['M20 65Q32 51 42 65L44 81Q31 72 20 82Z','M51 63Q64 52 74 66L75 82Q61 72 51 81Z','M82 62Q96 51 105 66L107 82Q93 72 82 80Z'])
        else:
            q['neural']=_p('M17 17Q61 25 111 17V44Q65 51 17 43Z',COLORS['neural'])
            q['boundary']=''.join(_p(f'M{x} 43Q{x+5} 50 {x+2} 62',None,COLORS['boundary'],3.4) for x in (27,60,93))
            q['sinusoid']=_e(40,88,17,10,COLORS['sinusoid'])+_e(86,91,19,11,COLORS['sinusoid'])
            q['terminal']=''.join(_e(x,y,6,5,COLORS['terminal']) for x,y in [(25,70),(53,72),(72,70),(104,70)])
            if soft:
                q['neural']=_p('M14 15Q61 25 114 14V44Q64 54 14 42Z',COLORS['neural'])
                q['boundary']=''.join(_p(f'M{x} 43Q{x+7} 49 {x+2} 57',None,COLORS['boundary'],4) for x in (21,56,91))
                q['sinusoid']=_p('M19 94Q18 83 39 83Q61 84 60 98Q59 108 39 108Q20 108 19 94ZM65 98Q64 84 87 83Q109 84 108 99Q107 111 86 111Q66 111 65 98Z',COLORS['sinusoid'])
                q['terminal']=''.join(_p(d,COLORS['terminal']) for d in ['M20 70Q29 59 37 69L39 77Q28 73 20 80Z','M48 70Q57 59 64 69L65 77Q56 73 48 80Z','M77 69Q87 58 95 69L96 77Q86 73 77 80Z'])
        if index==0:
            neural_contour='M13 16H115V43Q78 37 59 49T13 47Z' if soft else 'M15 18H112V43Q81 40 61 48T15 45Z'
            process_paths=[f'M{x} 42Q{x+5} 48 {x+2} 59' for x in ((28,60,92) if not soft else (23,57,91))]
            vascular_contour='M15 91Q39 77 63 88T114 80V108Q80 113 60 102T15 111Z' if soft else 'M18 88Q41 80 62 87T111 82V104Q83 110 62 101T18 108Z'
        else:
            neural_contour='M14 15Q61 25 114 14V44Q64 54 14 42Z' if soft else 'M17 17Q61 25 111 17V44Q65 51 17 43Z'
            process_paths=[f'M{x} 43Q{x+7} 49 {x+2} 57' for x in (21,56,91)] if soft else [f'M{x} 43Q{x+5} 50 {x+2} 62' for x in (27,60,93)]
            vascular_contour=''.join(['M19 88Q18 77 39 77Q61 78 60 92Q59 104 39 103Q20 103 19 88Z','M65 92Q64 78 87 77Q109 78 108 93Q107 106 86 105Q66 105 65 92Z']) if soft else 'M23 88A17 10 0 1 0 57 88A17 10 0 1 0 23 88Z M67 91A19 11 0 1 0 105 91A19 11 0 1 0 67 91Z'
        q['outline']=_p(neural_contour,None,ink,1.1)+''.join(_p(d,None,ink,1.1) for d in process_paths)+_p(vascular_contour,None,ink,1.1)
    elif key=='ovarian_follicle':
        # Same anatomical parts in both; only section arrangement changes.
        if index==0:
            antrum='M58 44Q76 38 89 50Q101 65 91 79Q78 91 62 82Q58 76 58 70Q55 57 58 44Z'
            q['theca']=_p('M64 15A49 49 0 1 1 63.9 15 M64 22A42 42 0 1 0 64.1 22',COLORS['theca'],more='fill-rule="evenodd"')
            q['granulosa']=_p('M64 24A40 40 0 1 1 63.9 24 M64 34A30 30 0 1 0 64.1 34',COLORS['granulosa'],more='fill-rule="evenodd"')
            q['antrum']=_p(antrum,COLORS['antrum'])
            q['oocyte']=_e(38,70,14,14,COLORS['oocyte'])
            q['zona_pellucida']=_e(38,70,17,17,'none',COLORS['zona_pellucida'],2.5)
        else:
            antrum='M61 43Q49 39 39 50Q29 63 35 76Q41 89 54 85Q60 80 61 72Q57 63 61 54Z'
            q['theca']=_p('M17 64A47 47 0 1 1 111 64A47 47 0 1 1 17 64 M24 64A40 40 0 1 0 104 64A40 40 0 1 0 24 64',COLORS['theca'],more='fill-rule="evenodd"')
            q['granulosa']=_p('M25 64A39 39 0 1 1 103 64A39 39 0 1 1 25 64 M34 64A30 30 0 1 0 94 64A30 30 0 1 0 34 64',COLORS['granulosa'],more='fill-rule="evenodd"')
            q['antrum']=_p(antrum,COLORS['antrum'])
            q['oocyte']=_e(77,67,13,13,COLORS['oocyte'])
            q['zona_pellucida']=_e(77,67,16,16,'none',COLORS['zona_pellucida'],2.5)
        if soft:
            # Style 4 uses scalloped layers and a differently contoured but
            # still eccentric antrum that meets the zona without covering it.
            outer='M64 14Q76 13 84 19Q97 18 103 30Q114 39 109 53Q116 66 107 77Q106 92 93 97Q85 111 70 106Q57 115 46 105Q31 106 26 93Q13 84 19 70Q11 57 20 46Q20 31 34 26Q43 12 57 19Z'
            granulosa_outer='M64 24Q76 23 82 29Q94 28 98 39Q107 47 101 57Q107 68 99 77Q97 89 86 91Q78 102 67 96Q55 103 47 95Q35 96 31 85Q21 78 26 67Q20 56 28 48Q29 37 40 34Q48 23 57 29Z'
            antrum=('M58 42Q76 36 91 49Q103 65 92 80Q79 92 62 82Q57 75 58 69Q55 55 58 42Z' if index==0 else 'M61 42Q48 38 37 50Q27 64 35 78Q42 90 55 84Q61 78 61 71Q57 62 61 54Z')
            # Use even-odd rings for both outer layers so they do not paint over
            # the oocyte, zona pellucida, or antral space beneath them.
            q['theca']=_p(outer+' '+granulosa_outer,COLORS['theca'],more='fill-rule="evenodd"')
            q['granulosa']=_p(granulosa_outer+' '+antrum,COLORS['granulosa'],more='fill-rule="evenodd"')
            q['antrum']=_p(antrum,COLORS['antrum'])
        if soft:
            q['outline']=_p(outer+' '+granulosa_outer,None,ink,1.2)
        else:
            outer='M64 15A49 49 0 1 1 63.9 15'
            granulosa_outer='M64 24A40 40 0 1 1 63.9 24'
            q['outline']=_p(outer+' '+granulosa_outer,None,ink,1.3)
        vessel_paths=(['M38 15Q24 25 15 41','M91 15Q105 27 114 43','M14 83Q24 103 43 114','M114 82Q104 102 85 114'] if index==0 else ['M26 24Q14 44 13 64','M103 23Q116 44 115 65','M13 80Q22 104 42 115','M115 80Q106 104 86 115'])
        if soft:
            vessel_paths=(['M36 13Q22 23 13 41','M93 13Q107 25 116 43','M12 84Q22 105 43 116','M116 83Q106 104 85 116'] if index==0 else ['M24 22Q12 43 11 64','M105 21Q118 43 117 66','M11 81Q20 105 42 117','M117 81Q108 105 86 117'])
        q['vessel']=''.join(_p(d,None,COLORS['vessel'],3.0 if not soft else 3.2) for d in vessel_paths)
        q['outline']+=_p('M38 53A17 17 0 1 1 37.9 53' if index==0 else 'M77 51A16 16 0 1 1 76.9 51',None,ink,1.05)
        q['outline']+=_p(antrum,None,ink,1.15)
    elif key=='corpus_luteum':
        # Folded form has winding nested luteal bands; radial form has
        # discrete cords directed outward around a shared central cavity.
        if index==0:
            if soft:
                lobes=['M20 29Q34 17 47 27Q56 33 49 43Q39 49 31 59Q23 69 18 60Q13 47 20 29Z','M77 24Q91 19 103 31Q110 42 100 50Q91 53 82 45Q73 39 67 43Q66 31 77 24Z','M18 76Q25 63 37 68Q47 72 49 84Q49 95 38 103Q25 104 19 94Q14 86 18 76Z','M78 75Q87 64 100 70Q111 77 106 91Q102 103 89 104Q77 101 73 91Q70 83 78 75Z']
                vessels=['M16 24Q31 37 42 31T55 42Q45 53 34 59T18 73','M68 20Q82 34 96 28T109 43Q98 55 85 47T61 50','M17 68Q31 79 43 73T56 84Q47 98 31 104','M70 70Q83 81 97 74T109 87Q101 101 86 105']
            else:
                lobes=['M20 30Q33 19 46 28Q55 34 48 44Q39 50 30 59Q22 67 18 59Q14 47 20 30Z','M78 24Q91 20 102 31Q109 42 100 49Q91 53 82 45Q73 39 67 43Q67 31 78 24Z','M18 77Q25 64 37 68Q47 72 48 84Q49 95 38 102Q25 103 19 94Q14 86 18 77Z','M78 75Q87 65 99 70Q110 77 106 90Q102 102 89 103Q77 101 73 91Q71 83 78 75Z']
                vessels=['M16 24Q31 37 42 31T55 42Q45 53 34 59T18 73','M68 20Q82 34 96 28T109 43Q98 55 85 47T61 50','M17 68Q31 79 43 73T56 84Q47 98 31 104','M70 70Q83 81 97 74T109 87Q101 101 86 105']
        else:
            lobes=['M57 22Q66 16 72 25L70 49Q66 54 62 49Z','M82 29Q91 27 95 35L78 55Q72 57 71 51Z','M99 50Q105 55 100 63L76 66Q71 62 75 57Z','M101 72Q105 80 98 85L76 70Q74 64 80 63Z','M82 99Q75 104 69 97L72 74Q77 70 81 76Z','M58 105Q50 102 54 94L61 72Q67 70 69 77Z','M30 83Q26 76 33 71L55 75Q59 80 54 84Z','M27 52Q30 44 38 49L57 59Q58 65 52 67Z']
            if soft:
                lobes=['M56 18Q67 14 74 25L70 49Q65 55 60 49Z','M86 24Q97 26 98 37L79 56Q72 57 71 50Z','M106 51Q110 61 102 68L78 67Q72 62 77 56Z','M105 78Q101 89 90 87L73 70Q73 64 81 63Z','M82 106Q71 111 66 101L71 76Q77 71 82 78Z','M54 108Q43 104 49 92L60 71Q67 70 70 78Z','M25 86Q20 76 29 68L54 75Q60 81 53 86Z','M22 50Q27 39 39 46L58 58Q59 65 51 68Z']
            vessels=['M64 15Q65 31 66 48','M91 26Q81 40 72 53','M109 59Q92 61 76 62','M109 83Q91 76 77 67','M77 108Q73 88 68 74','M48 109Q57 89 62 71','M19 79Q39 72 56 67','M19 46Q41 52 59 61']
        q['luteal']=''.join(_p(d,COLORS['luteal']) for d in lobes)
        q['vessel']=''.join(_p(d,None,COLORS['vessel'],3.5 if soft else 3) for d in vessels)
        q['antrum']=_e(64,64,9,7,COLORS['antrum'])
        outer=('M17 29Q31 14 48 25Q63 15 78 23Q100 16 109 37Q119 54 108 69Q117 88 99 102Q81 113 65 103Q46 114 29 101Q11 89 20 71Q9 51 17 29Z' if soft else 'M18 31Q33 17 49 27Q64 18 79 25Q99 19 108 39Q117 55 107 69Q114 86 98 100Q81 110 65 101Q47 111 30 99Q13 88 21 71Q11 52 18 31Z')
        q['outline']=_p(outer,None,ink,1.5)
    elif key=='leydig_interstitium':
        # Ring profiles represent seminiferous tubules; central lumens remain
        # visibly separate from the interstitial pocket and cell clusters.
        if index==0:
            profiles=[(34,64,21,15),(94,64,20,14)]
            clusters=[(61,35),(68,44),(59,52),(66,60),(60,74),(68,83),(60,92),(77,50),(76,77)]
            vessel='M61 29Q55 42 62 53T61 76Q68 89 62 101'
        else:
            profiles=[(34,38,18,13),(92,37,19,14),(35,91,19,13),(93,91,18,14)]
            clusters=[(61,56),(68,54),(75,61),(59,69),(68,74),(77,80),(59,88),(69,94)]
            vessel='M64 48Q73 55 65 65T69 83Q77 95 69 105'
        if soft:
            profiles=[(33,63,22,16),(95,65,21,15)] if index==0 else [(32,36,19,14),(94,37,18,13),(34,93,18,14),(94,92,19,13)]
            vessel='M61 27Q75 41 64 55T65 78Q78 92 66 106'
        for cx,cy,rx,ry in profiles:
            outer=f'M{cx-rx} {cy}A{rx} {ry} 0 1 0 {cx+rx} {cy}A{rx} {ry} 0 1 0 {cx-rx} {cy}Z'
            inner_rx,inner_ry=rx-5,ry-4
            inner=f'M{cx-inner_rx} {cy}A{inner_rx} {inner_ry} 0 1 1 {cx+inner_rx} {cy}A{inner_rx} {inner_ry} 0 1 1 {cx-inner_rx} {cy}Z'
            q['tubule']+=_p(outer+' '+inner,COLORS['tubule'],more='fill-rule="evenodd"')
            q['tubule_lumen']+=_e(cx,cy,inner_rx,inner_ry,COLORS['tubule_lumen'])
            q['outline']+=_p(outer,None,ink,1.4)+_p(inner,None,ink,1.1)
        q['interstitium']=''.join(_e(x,y,5.4,6.5,COLORS['interstitium']) for x,y in clusters)
        if soft:
            q['interstitium']=''.join(_p(f'M{x} {y}q5 -6 10 0q2 5 -2 9q-5 4 -10 -1q-2 -4 2 -8Z',COLORS['interstitium']) for x,y in clusters)
        q['vessel']=_p(vessel,None,COLORS['vessel'],5.2 if not soft else 6)
        q['outline']+=_p(vessel,None,ink,1.2)
    return q

def render_svg(key:str,index:int,title:str,description:str,style4:bool=False)->str:
    if key not in CONCEPTS or index not in (0,1): raise KeyError((key,index))
    p=_draw(key,index,style4)
    groups=''.join(f'<g data-region="{rid}">{p[rid]}</g>' for rid,_ in REGIONS[key])
    form=CONCEPTS[key]['forms'][index]['id']
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 128" role="img" aria-labelledby="title desc" data-asset="endocrine.{key}.{form}"><title id="title">{escape(title)}</title><desc id="desc">{escape(description)}</desc>{groups}</svg>'

if __name__=='__main__':
    import xml.etree.ElementTree as ET
    assert list(CONCEPTS)==['anterior_pituitary','posterior_pituitary','median_eminence','ovarian_follicle','corpus_luteum','leydig_interstitium']
    for key,c in CONCEPTS.items():
        assert len(c['forms'])==2
        for i in (0,1):
            for style4 in (False,True):
                root=ET.fromstring(render_svg(key,i,'Schematic',c['forms'][i]['description'],style4))
                assert root.get('viewBox')=='0 0 128 128'
                assert root.get('data-asset')==f'endocrine.{key}.{c["forms"][i]["id"]}'
                gs=[e for e in root if e.tag.endswith('g')]
                assert [g.get('data-region') for g in gs]==[r['id'] for r in regions_for(key,i)]
                assert all(len(g) for g in gs),(key,i,style4)
                assert not ({e.tag.split('}')[-1] for e in root.iter()} & {'script','foreignObject','image','filter','iframe','text'})
                assert all(not any(a.endswith('href') and not v.startswith('#') for a,v in e.attrib.items()) for e in root.iter())
    print('PASS: 6 concepts, 12 forms, 24 safe accessible SVG renderings; all semantic regions painted.')
