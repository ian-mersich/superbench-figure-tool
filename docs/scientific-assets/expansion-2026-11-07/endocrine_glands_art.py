"""Original editable endocrine-tissue SVGs; generic topology, not to scale."""
from __future__ import annotations

from html import escape


REFERENCES = [
    {"id":"thyroid_follicle", "citation":"Wissig SL. The anatomy of secretion in the follicular cells of the thyroid gland: II. The effect of acute thyrotrophic hormone stimulation on the secretory apparatus. J Cell Biol. 1963;16:93–117.", "doi":"10.1083/jcb.16.1.93", "url":"https://doi.org/10.1083/jcb.16.1.93", "design_decision":"Ultrastructural observations support keeping follicular epithelial cells and luminal colloid as distinct compartments."},
    {"id":"parathyroid_cords", "citation":"Gilmour JR. The normal histology of the parathyroid glands. J Pathol Bacteriol. 1939;48:187–222.", "doi":"10.1002/path.1700480119", "url":"https://doi.org/10.1002/path.1700480119", "design_decision":"Supports parenchymal chief-cell fields and connective tissue; a separately visible capillary is included as a generic structural relationship."},
    {"id":"pancreatic_islet", "citation":"Cabrera O, et al. The unique cytoarchitecture of human pancreatic islets has implications for islet cell function. Proc Natl Acad Sci USA. 2006;103:2334–2339.", "doi":"10.1073/pnas.0510790103", "url":"https://doi.org/10.1073/pnas.0510790103", "design_decision":"Shows mixed human endocrine cell types associated with microvasculature; avoids imposing a universal rodent core–mantle pattern."},
    {"id":"adrenal_zones", "citation":"Fu R, et al. In Situ Spatial Reconstruction of Distinct Normal and Pathological Cell Populations Within the Human Adrenal Gland. J Endocr Soc. 2023;7:bvad131.", "doi":"10.1210/jendso/bvad131", "url":"https://doi.org/10.1210/jendso/bvad131", "design_decision":"Human spatial reconstruction supports the outward-to-inward order of capsule, zona glomerulosa, zona fasciculata, zona reticularis, and medulla."},
    {"id":"adrenal_medulla", "citation":"Kikuta A, Murakami T. Relationship between chromaffin cells and blood vessels in the rat adrenal medulla: a transmission electron microscopic study combined with blood vessel reconstructions. Am J Anat. 1984;170:73–81.", "doi":"10.1002/aja.1001700106", "url":"https://doi.org/10.1002/aja.1001700106", "design_decision":"Directly supports close relationships between chromaffin cells and sinusoidal vascular channels; rat-specific vascular anatomy is presented schematically."},
    {"id":"pineal_vasculature", "citation":"Murakami T, Kikuta A, Taguchi T, Ohtsuka A. The blood vascular architecture of the rat pineal gland: a scanning electron microscopic study of corrosion casts. Arch Histol Cytol. 1988;51:61–69.", "doi":"10.1679/aohc.51.61", "url":"https://doi.org/10.1679/aohc.51.61", "design_decision":"Supports a richly interconnected capillary network. A separate human postmortem morphometry reference supports pinealocytes within glial tissue; no calcification is implied."},
    {"id":"pineal_parenchyma", "citation":"Gheban BA, et al. Age-Related Changes of the Pineal Gland in Humans: A Digital Anatomo-Histological Morphometric Study on Autopsy Cases with Comparison to Predigital-Era Studies. Medicina. 2021;57:383.", "doi":"10.3390/medicina57040383", "url":"https://doi.org/10.3390/medicina57040383", "design_decision":"Human postmortem histology supports pinealocyte parenchyma in glial tissue and variable lobular or insular arrangements; no calcification is required in the schematic."},
]

CONCEPTS = {
    "thyroid_follicle": {"key":"thyroid_follicle","name":"Thyroid follicle","subcategory":"thyroid","synonyms":["thyroid follicles","colloid follicle"],"forms":[{"id":"single_follicle","label":"Single follicle","description":"A section through one colloid-filled follicle bounded by follicular epithelium."},{"id":"follicle_field","label":"Follicle field","description":"Several differently sized follicles separated by interfollicular stroma."}],"limits":"State-neutral schematic; epithelial height, colloid texture, and follicle size are not quantitative.","refs":["thyroid_follicle"]},
    "parathyroid_cords": {"key":"parathyroid_cords","name":"Parathyroid parenchyma","subcategory":"parathyroid","synonyms":["parathyroid chief cells","parathyroid tissue"],"forms":[{"id":"cords_longitudinal","label":"Interwoven cords","description":"Parenchymal cords course around a branching capillary in connective stroma."},{"id":"lobular_field","label":"Lobular field","description":"A compact lobular arrangement of cords with stromal septa and capillary profiles."}],"limits":"Generic adult gland topology; cell proportions and adipose content vary with age and individual.","refs":["parathyroid_cords"]},
    "pancreatic_islet": {"key":"pancreatic_islet","name":"Pancreatic islet","subcategory":"pancreas","synonyms":["islet of Langerhans","endocrine pancreas"],"forms":[{"id":"mixed_islet","label":"Mixed cell clusters","description":"Mixed endocrine-cell groups are interspersed with capillary channels."},{"id":"folded_plates","label":"Folded cell plates","description":"Curved endocrine-cell plates lie alongside branching capillary channels."}],"limits":"Cell colors distinguish broad endocrine populations only; arrangement is illustrative and not a universal species-specific blueprint.","refs":["pancreatic_islet"]},
    "adrenal_cortex": {"key":"adrenal_cortex","name":"Adrenal cortex","subcategory":"adrenal gland","synonyms":["zona glomerulosa","zona fasciculata","zona reticularis"],"forms":[{"id":"concentric_zones","label":"Concentric zones","description":"Capsule and the three cortical zones surround the medullary side in anatomical order."},{"id":"cortical_wedge","label":"Cortical wedge","description":"An expanded radial wedge shows the capsule, cortical zones, and adjoining medulla."}],"limits":"Zones are simplified and not to scale; human and other mammalian adrenal organization can differ locally.","refs":["adrenal_zones"]},
    "adrenal_medulla": {"key":"adrenal_medulla","name":"Adrenal medulla","subcategory":"adrenal gland","synonyms":["chromaffin tissue","adrenal chromaffin cells"],"forms":[{"id":"vascular_nests","label":"Nests around sinusoid","description":"Chromaffin-cell nests are arranged beside a sinusoidal channel."},{"id":"medullary_field","label":"Medullary field","description":"A broad field of chromaffin-cell groups with sinusoidal vascular space."}],"limits":"Generic medullary topology; cell subtype proportions, innervation, and vessel dimensions are not shown.","refs":["adrenal_medulla"]},
    "pineal_parenchyma": {"key":"pineal_parenchyma","name":"Pineal parenchyma","subcategory":"pineal gland","synonyms":["pinealocytes","pineal gland tissue"],"forms":[{"id":"cell_groups","label":"Pinealocyte groups","description":"Groups of pinealocytes are separated by delicate glial stroma and capillaries."},{"id":"lobular_field","label":"Lobular field","description":"Pinealocyte-rich lobules are traversed by an interconnected capillary network."}],"limits":"Generic parenchymal schematic; species differences are not resolved and calcification is not required or depicted.","refs":["pineal_vasculature","pineal_parenchyma"]},
}

_REGIONS = {
 "thyroid_follicle":[("follicular_epithelium","Follicular epithelium","#E9A997"),("colloid","Colloid","#FFFFFF"),("stroma","Interfollicular stroma","#B8D8C5"),("outline","Structural outlines","#344955")],
 "parathyroid_cords":[("parenchyma","Parathyroid parenchyma","#E5B69E"),("capillary","Capillary","#D8867A"),("stroma","Connective stroma","#B8D8C5"),("outline","Structural outlines","#344955")],
 "pancreatic_islet":[("beta_cells","β-cell population","#E9B7A5"),("other_endocrine","Other endocrine cells","#A9C5D9"),("capillary","Capillaries","#D8867A"),("stroma","Supporting stroma","#B8D8C5"),("outline","Structural outlines","#344955")],
 "adrenal_cortex":[("capsule","Capsule","#B8D8C5"),("zona_glomerulosa","Zona glomerulosa","#D9B978"),("zona_fasciculata","Zona fasciculata","#E9B7A5"),("zona_reticularis","Zona reticularis","#A9C5D9"),("medulla","Medulla","#C58B9A"),("outline","Structural outlines","#344955")],
 "adrenal_medulla":[("chromaffin_cells","Chromaffin cells","#C58B9A"),("supporting_cells","Supporting cells","#B8D8C5"),("vascular_lumen","Vascular lumen","#F2D7CE"),("outline","Structural outlines","#344955")],
 "pineal_parenchyma":[("pinealocytes","Pinealocytes","#E9B7A5"),("glial_stroma","Glial stroma","#A9C5D9"),("capillary","Capillaries","#D8867A"),("outline","Structural outlines","#344955")],
}

# Supporting fields and stromal marks are laid down first, tissue compartments
# follow, and clean outer contours finish each illustration.
_PAINT_ORDER = {
 "thyroid_follicle":["stroma","follicular_epithelium","colloid","outline"],
 "parathyroid_cords":["stroma","parenchyma","capillary","outline"],
 "pancreatic_islet":["stroma","capillary","beta_cells","other_endocrine","outline"],
 "adrenal_cortex":["capsule","zona_glomerulosa","zona_fasciculata","zona_reticularis","medulla","outline"],
 "adrenal_medulla":["vascular_lumen","chromaffin_cells","supporting_cells","outline"],
 "pineal_parenchyma":["glial_stroma","capillary","pinealocytes","outline"],
}

def regions_for(key: str, index: int) -> list[dict[str,str]]:
    if key not in CONCEPTS: raise KeyError(key)
    if index not in (0,1): raise IndexError("form index must be 0 or 1")
    return [{"id":i,"label":l,"default":c} for i,l,c in _REGIONS[key]]

def _shape(tag: str, attrs: str, color: str) -> str:
    return f'<{tag} {attrs} fill="{color}" stroke="#344955" stroke-width="1.5" stroke-linejoin="round"/>'

def _parts(key: str, ix: int, style4: bool) -> dict[str,str]:
    p={r[0]:"" for r in _REGIONS[key]}; f="#344955"; colors={r[0]:r[2] for r in _REGIONS[key]}
    body_path=None
    def path(r,d,fill=None,sw="1.5"):
        c=fill or colors[r]
        if d.rstrip().upper().endswith("Z"):
            p[r]+=f'<path d="{d}" fill="{c}" stroke="none"/>'
        else:
            p[r]+=f'<path d="{d}" fill="none" stroke="{c}" stroke-width="{sw}" stroke-linecap="round" stroke-linejoin="round"/>'
    def ellipse(r,cx,cy,rx,ry,fill=None):
        c=fill or colors[r]; p[r]+=f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="{c}" stroke="none"/>'
    if key=="thyroid_follicle":
        if ix==0:
            if style4:
                path("follicular_epithelium","M64 16 C91 16 111 37 111 64 C111 91 91 112 64 112 C37 112 17 91 17 64 C17 37 37 16 64 16Z")
                ellipse("colloid",64,64,34,34); path("follicular_epithelium","M34 39 Q64 20 94 39 L88 44 Q64 30 40 44Z","#F5C9B7",".8")
            else:
                ellipse("follicular_epithelium",64,64,46,46); ellipse("colloid",64,64,34,34)
                for x,y in [(64,19),(97,34),(109,64),(94,96),(64,109),(32,94),(19,64),(35,32)]: ellipse("follicular_epithelium",x,y,4,6)
            path("stroma","M24 102 Q39 94 49 101 M79 101 Q92 94 104 102 M22 28 Q29 22 35 23",None,"2")
        else:
            # Keep follicle profiles apart so intervening stroma remains visible.
            rings=[(36,38,13),(90,36,14),(39,90,14),(90,89,13)] if not style4 else [(37,39,15),(90,38,12),(39,88,12),(90,90,15)]
            for x,y,r in rings:
                ellipse("follicular_epithelium",x,y,r+5,r+5); ellipse("colloid",x,y,max(7,r-4),max(7,r-4))
            # The stroma strokes are painted beneath follicular profiles; only
            # the portions in interfollicular spaces remain exposed.
            path("stroma","M20 64 Q27 60 33 63 M49 64 Q62 60 68 64 M96 64 Q103 61 109 63 M20 77 Q27 82 32 84 M49 91 Q59 97 66 94 M96 83 Q103 78 109 80 M53 20 Q58 25 60 28 M75 101 Q81 96 84 91",None,"1.7")
    elif key=="parathyroid_cords":
        if ix==0:
            if style4:
                body_path="M18 32 Q31 15 54 22 Q72 14 92 24 Q114 35 109 58 Q117 82 99 101 Q78 116 59 105 Q34 114 19 93 Q10 72 20 57Z"
                path("stroma",body_path)
                path("parenchyma","M29 32 Q47 42 38 57 T31 87 M48 28 Q62 43 51 58 T49 94 M88 31 Q71 45 86 60 T91 91 M103 47 Q88 57 99 72",None,"5")
                path("capillary","M20 74 C42 64 57 83 74 68 S95 50 110 61",None,"3")
            else:
                path("stroma","M18 26 Q64 16 110 26 L110 102 Q64 112 18 102Z")
                path("parenchyma","M28 33 Q46 47 32 62 T40 94 M51 29 Q66 45 54 61 T59 99 M94 33 Q76 49 91 64 T85 96",None,"5")
                path("capillary","M19 71 C41 63 53 79 68 70 S90 61 108 67",None,"3")
        else:
            body_path=("M19 27 Q44 18 62 26 Q83 14 108 29 L110 96 Q89 110 65 101 Q40 112 18 96Z" if style4 else "M19 25 Q42 18 64 24 T109 25 V103 Q85 109 63 103 T19 103Z")
            path("stroma",body_path)
            for x in (33,52,75,95):
                path("parenchyma",f"M{x} 31 Q{x+10} 43 {x} 55 T{x+2} 77 Q{x+11} 88 {x+1} 98",None,"4.5")
            path("stroma","M41 24 Q45 45 41 62 M83 25 Q79 46 83 62",None,"2")
            path("capillary","M24 66 C42 60 55 73 70 66 S93 60 105 65 M64 66 Q72 78 70 91",None,"3")
        # Chief-cell bodies turn the cords into tissue rather than bare strands.
        cell_centers=(
            [(30,36),(37,49),(34,67),(38,84),(42,96),(51,35),(57,49),(56,68),(57,84),(60,96),(91,38),(87,54),(89,72),(84,88)]
            if ix==0 else
            [(32,38),(37,52),(35,69),(38,86),(52,35),(57,50),(55,69),(59,86),(92,39),(88,56),(89,75),(85,91)]
        )
        for x,y in cell_centers:
            ellipse("parenchyma",x,y,2.6,3.2,"#D59E86")
    elif key=="pancreatic_islet":
        if ix==0:
            path("stroma","M20 63 C20 37 40 20 65 20 C92 20 108 39 108 63 C108 89 88 108 63 108 C38 108 20 88 20 63Z")
            beta=[(43,43),(62,37),(81,48),(39,67),(59,60),(82,70),(49,88),(70,91)]
            other=[(61,25),(94,54),(28,54),(94,80),(31,78),(64,103)]
            if style4: beta=[(36,43),(56,38),(76,50),(48,61),(70,68),(39,82),(65,91),(86,88)]; other=[(92,41),(25,62),(91,72),(53,25),(31,90),(75,103)]
            for x,y in beta: ellipse("beta_cells",x,y,7,8)
            for x,y in other: ellipse("other_endocrine",x,y,6,7)
            path("capillary","M25 73 C42 56 47 54 63 60 S83 71 101 50 M42 29 Q51 47 63 60",None,"2.8")
        else:
            path("stroma","M19 29 Q50 17 77 30 Q108 44 103 68 Q96 96 68 101 Q39 107 23 83 Q12 62 19 29Z")
            for i in range(5):
                y=36+i*12
                path("beta_cells",f"M27 {y} Q42 {y-9} 55 {y} T82 {y} T98 {y-2}",None,"5")
            for x,y in [(37,51),(73,45),(91,60),(29,72),(63,81),(82,91)]: ellipse("other_endocrine",x,y,4.5,5)
            path("capillary","M22 57 C38 47 46 59 60 55 S81 44 101 52 M24 80 C41 70 52 86 67 76 S89 70 98 80",None,"2.8")
    elif key=="adrenal_cortex":
        if ix==0:
            if not style4:
                # Outer-to-inner painting leaves every named zone visible;
                # the inset capsule and medulla stay clear of the canvas edge.
                ellipse("capsule",64,64,55,56)
                ellipse("zona_glomerulosa",64,64,47,48)
                ellipse("zona_fasciculata",64,64,39,40)
                ellipse("zona_reticularis",64,64,31,32)
                ellipse("medulla",64,66,22,24)
            else:
                path("capsule","M64 8 C91 8 116 29 116 62 C116 94 93 119 64 120 C35 120 12 95 12 63 C12 30 35 8 64 8Z")
                path("zona_glomerulosa","M64 15 C87 15 109 34 109 62 C109 88 89 112 64 113 C39 112 19 89 19 63 C19 36 39 15 64 15Z")
                path("zona_fasciculata","M64 24 C84 24 100 40 100 63 C100 85 84 103 64 104 C44 103 28 85 28 63 C28 40 44 24 64 24Z")
                path("zona_reticularis","M64 32 C80 32 92 45 92 63 C92 80 80 94 64 95 C48 94 36 80 36 63 C36 45 48 32 64 32Z")
                path("medulla","M64 42 C78 42 85 51 84 65 C83 78 75 88 63 87 C51 86 44 76 45 63 C46 50 53 42 64 42Z")
            # Maintains clear compact central medullary side in a schematic section.
        else:
            capsule_path=("M16 27 Q37 11 61 22 Q83 13 112 30 L110 101 Q85 114 62 102 Q36 114 16 98Z" if style4 else "M14 24 Q35 13 57 23 Q82 13 114 27 L114 102 Q86 112 62 102 Q36 111 14 99Z")
            path("capsule",capsule_path)
            if style4:
                path("zona_glomerulosa","M20 29 Q42 16 63 27 Q87 14 108 27 L106 38 Q83 28 62 39 Q40 27 21 40Z")
                path("zona_fasciculata","M21 41 Q40 30 62 40 Q84 30 107 40 L104 67 Q81 59 61 69 Q40 59 21 70Z")
                path("zona_reticularis","M21 72 Q41 62 61 71 Q82 61 104 70 L103 83 Q81 75 61 84 Q40 76 21 84Z")
                path("medulla","M21 85 Q42 77 61 85 Q81 77 103 85 L103 98 Q82 91 61 100 Q41 92 21 99Z")
            else:
                path("zona_glomerulosa","M19 32 Q37 22 58 31 Q83 22 108 34 L108 43 Q82 32 61 41 Q39 32 19 42Z")
                path("zona_fasciculata","M19 43 Q40 34 61 42 Q84 34 108 44 L108 69 Q84 60 61 69 Q40 60 19 69Z")
                path("zona_reticularis","M19 69 Q41 60 61 69 Q83 60 108 69 L108 82 Q83 74 61 82 Q40 75 19 83Z")
                path("medulla","M19 83 Q40 75 61 82 Q83 74 108 82 L108 99 Q82 91 61 100 Q40 92 19 100Z")
        # Fine tissue architecture stays within its named zone paints in both
        # structural views: glomerulosa cell clusters, radial fascicles, and a
        # reticularis mesh. The marks remain editable with their zone color.
        if ix==0:
            import math
            for angle in range(0,360,30):
                rad=math.radians(angle)
                x=64+43*math.cos(rad); y=64+43*math.sin(rad)
                ellipse("zona_glomerulosa",round(x,2),round(y,2),2.2,2.2,"#C4A256")
            for angle in range(0,360,30):
                rad=math.radians(angle)
                r0,r1=37.5,33.5
                x0=64+r0*math.cos(rad); y0=64+r0*math.sin(rad)
                x1=64+r1*math.cos(rad); y1=64+r1*math.sin(rad)
                path("zona_fasciculata",f"M{x0:.2f} {y0:.2f} Q{64+35.5*math.cos(rad+.08):.2f} {64+35.5*math.sin(rad+.08):.2f} {x1:.2f} {y1:.2f}","#D78F80","1.05")
            # Short open anastomosing marks suggest a reticular network
            # without drawing a closed polygon around the medulla.
            for d in ["M93 64L87 60L89 56","M83 43L78 47L80 51","M84 79L78 75L81 71","M64 93L61 87L66 84","M44 84L49 79L53 82","M44 44L50 49L47 54"]:
                path("zona_reticularis",d,None,"1.25")
        else:
            for x,y in [(29,34),(44,33),(60,35),(77,33),(94,35),(105,36)]:
                ellipse("zona_glomerulosa",x,y,2.4,2.0,"#C4A256")
            for x in (30,44,58,72,86,100):
                path("zona_fasciculata",f"M{x} 44 Q{x+2} 51 {x-1} 57 T{x+1} 66","#D78F80","1.15")
            path("zona_reticularis","M25 73 Q41 68 57 74 T89 72 T105 77","#7894A2","1.1")
            path("zona_reticularis","M29 80 Q45 71 61 78 T96 73 T104 79","#7894A2","1.0")
    elif key=="adrenal_medulla":
        if ix==0:
            if style4:
                for x,y in [(32,39),(44,33),(84,36),(94,47),(34,83),(48,91),(88,91),(98,76)]: ellipse("chromaffin_cells",x,y,6,7,"#BD7D91")
                for x,y in [(57,52),(72,75)]: ellipse("supporting_cells",x,y,3.2,4.2)
            else:
                path("vascular_lumen","M19 76 C35 62 43 49 56 51 C70 53 71 74 84 72 C96 70 97 53 110 48",None,"8")
                for x,y in [(32,42),(46,33),(68,35),(91,37),(39,91),(62,91),(88,91),(28,61),(102,84)]: ellipse("chromaffin_cells",x,y,7,8)
                for x,y in [(55,30),(77,89),(105,62)]: ellipse("supporting_cells",x,y,3.5,5)
        else:
            if style4:
                for x,y in [(31,30),(50,34),(80,30),(96,32),(31,62),(50,66),(78,66),(99,70),(35,96),(58,97),(80,98),(96,89)]: ellipse("chromaffin_cells",x,y,5.8,6.4,"#BD7D91")
                for x,y in [(63,38),(64,82)]: ellipse("supporting_cells",x,y,3.0,4.0)
            else:
                path("vascular_lumen","M19 35 C37 47 40 60 57 62 C76 64 89 52 108 43 M20 91 C39 79 48 77 62 80 C81 84 91 97 109 89",None,"7")
                for x,y in [(31,31),(49,42),(72,42),(94,32),(31,57),(52,59),(77,60),(99,60),(35,78),(58,96),(80,95),(99,77)]: ellipse("chromaffin_cells",x,y,6.5,7)
                for x,y in [(62,31),(24,70),(88,74)]: ellipse("supporting_cells",x,y,3.2,4.5)
    elif key=="pineal_parenchyma":
        if ix==0:
            path("glial_stroma","M22 30 Q43 18 61 28 Q82 17 106 33 L103 96 Q82 107 62 98 Q41 108 22 94Z")
            for x,y in [(39,40),(58,36),(79,43),(91,60),(69,58),(45,64),(34,83),(58,86),(81,83)]: ellipse("pinealocytes",x,y,7,8)
            path("capillary","M27 53 C41 46 48 53 61 53 S83 46 101 52 M30 74 C44 68 53 74 66 73 S85 67 99 74",None,"2.7")
            for x,y in [(27,43),(99,89),(53,98)]: ellipse("glial_stroma",x,y,3.5,5)
        else:
            body_path=("M17 35 Q29 15 52 24 Q73 12 91 28 Q113 31 110 54 Q119 76 99 88 Q86 108 64 100 Q41 111 25 91 Q11 74 20 57Z" if style4 else "M18 29 Q42 19 64 27 T110 30 V98 Q86 108 64 99 T18 98Z")
            path("glial_stroma",body_path)
            for y in (39,58,76,86):
                for x in (32,52,75,96):
                    if (x+y)%3: ellipse("pinealocytes",x,y,6,7)
            path("capillary","M21 48 C38 37 47 49 62 45 S88 37 107 48 M21 69 C36 59 48 71 63 66 S88 59 107 69 M26 88 Q46 78 61 84 T101 85",None,"2.6")
            path("glial_stroma","M44 27 L46 39 M84 28 L82 40 M62 75 L62 98",None,"1.8")
    # Style 4 redraws each tissue boundary and changes internal packing details.
    # These additions are structural facets in their semantic paint groups.
    if style4:
        if key=="thyroid_follicle" and ix==1:
            for x,y,rx,ry in [(38,39,12,17),(84,38,10,14),(45,87,11,13),(88,86,14,17)]:
                ellipse("colloid",x,y,rx,ry,"#E9D09D")
        elif key=="parathyroid_cords":
            if ix==0:
                path("parenchyma","M24 49 Q38 38 47 49 T67 49 T89 47 T105 54",None,"3.2")
                path("capillary","M25 83 Q43 70 58 82 T88 81 T104 75",None,"2")
            else:
                # Wider lobular islands separated by a gently branching septum.
                for x,y in [(33,42),(57,42),(81,42),(43,75),(69,75),(94,75)]:
                    ellipse("parenchyma",x,y,8,6,"#E2AA90")
                path("capillary","M22 59 Q42 52 61 62 T105 57 M63 61 Q57 79 61 96",None,"2.2")
        elif key=="pancreatic_islet":
            if ix==1:
                for x,y in [(35,41),(57,43),(78,40),(48,67),(72,68),(39,88),(86,91)]:
                    ellipse("beta_cells",x,y,5,6,"#DFA28F")
                path("capillary","M30 33 Q43 51 57 55 T86 54 Q94 62 98 72",None,"2.0")
        elif key=="adrenal_medulla":
            if ix==0:
                # A narrow sinusoid follows the open corridor between cell nests.
                path("vascular_lumen","M24 63 Q39 60 54 63 T84 63 T104 63",None,"1.6")
            else:
                # Keep the short channel in the clear lane between cell rows.
                path("vascular_lumen","M39 49 Q62 47 91 49",None,"1.6")
        elif key=="pineal_parenchyma":
            if ix==0:
                # A curved glial septum and a central capillary loop change
                # the packing without implying a lesion or calcification.
                path("glial_stroma","M25 34 Q43 48 35 65 T44 91 M88 31 Q74 47 85 61 T78 95",None,"2.4")
                path("capillary","M34 59 C44 47 54 50 64 62 C74 74 86 73 96 60",None,"2.2")
                for x,y in [(55,50),(74,80),(50,94)]: ellipse("pinealocytes",x,y,5.4,6.5,"#DFA28F")
            else:
                # Lobule-like islands are separated by broad branching septa.
                path("glial_stroma","M20 62 Q41 48 61 61 T108 59 M62 25 Q53 43 62 61 T61 102",None,"2.7")
                path("capillary","M26 42 Q43 51 51 62 M72 62 Q87 48 102 43 M25 82 Q44 72 52 64 M72 65 Q88 76 103 84",None,"2.1")
                for x,y in [(39,34),(83,35),(39,86),(85,87)]: ellipse("pinealocytes",x,y,5,6,"#DFA28F")
    # A distinct, editable contour region accompanies the compartment fills.
    contours={
      "thyroid_follicle": ("M18 64 C18 38 38 18 64 18 C90 18 110 38 110 64 C110 90 90 110 64 110 C38 110 18 90 18 64Z" if ix==0 else "M17 64 C17 38 39 18 64 18 C90 18 111 38 111 64 C111 90 90 110 64 110 C38 110 17 90 17 64Z"),
      "parathyroid_cords": "M17 25 Q64 14 111 25 L111 103 Q64 114 17 103Z",
      "pancreatic_islet": "M18 63 C18 37 39 18 65 18 C92 18 110 38 110 63 C110 90 89 110 63 110 C38 110 18 89 18 63Z",
      "adrenal_cortex": "M12 63 C12 31 34 9 64 9 C94 9 116 31 116 63 C116 94 94 119 64 119 C34 119 12 94 12 63Z" if ix==0 else "M13 23 Q38 12 61 22 Q86 12 115 26 L115 103 Q86 114 62 103 Q37 114 13 100Z",
      "adrenal_medulla": "M17 27 Q64 14 111 27 L111 102 Q64 115 17 102Z",
      "pineal_parenchyma": "M17 28 Q40 16 64 25 Q87 16 111 29 L109 99 Q85 110 63 101 Q39 111 17 98Z",
    }
    if style4:
        style4_contours={
          "thyroid_follicle": ["M64 13 C91 14 115 35 112 64 C110 92 91 114 64 114 C35 114 15 91 16 63 C17 35 38 13 64 13Z", "M17 34 Q34 14 56 20 Q77 9 99 25 Q116 40 108 62 Q118 83 99 103 Q80 118 61 107 Q36 117 20 95 Q8 73 19 58 Q10 45 17 34Z"],
          "parathyroid_cords": ["M18 32 Q31 15 54 22 Q72 14 92 24 Q114 35 109 58 Q117 82 99 101 Q78 116 59 105 Q34 114 19 93 Q10 72 20 57Z", "M19 27 Q44 18 62 26 Q83 14 108 29 L110 96 Q89 110 65 101 Q40 112 18 96Z"],
          "pancreatic_islet": ["M21 61 Q17 34 39 22 Q62 12 78 24 Q104 22 109 47 Q119 68 101 85 Q90 108 65 105 Q40 114 27 91 Q12 79 21 61Z", "M18 36 Q29 17 51 23 Q73 14 90 29 Q112 31 110 55 Q119 77 96 87 Q84 108 62 101 Q37 111 25 91 Q10 71 20 57Z"],
          "adrenal_cortex": ["M64 8 C90 8 117 29 116 61 C119 91 94 120 64 120 C32 120 10 94 12 63 C10 31 37 8 64 8Z", "M16 27 Q37 11 61 22 Q83 13 112 30 L110 101 Q85 114 62 102 Q36 114 16 98Z"],
          "adrenal_medulla": ["M20 25 Q41 13 60 23 Q83 12 106 27 Q118 47 108 64 Q118 84 101 101 Q78 115 60 104 Q37 115 20 98 Q10 78 20 62 Q10 43 20 25Z", "M18 31 Q38 17 60 28 Q84 17 108 31 L109 96 Q87 109 64 100 Q41 109 18 96Z"],
          "pineal_parenchyma": ["M20 30 Q39 15 61 25 Q82 15 105 30 Q117 48 106 63 Q116 84 100 99 Q79 112 62 101 Q40 112 21 98 Q10 80 20 63 Q10 46 20 30Z", "M17 35 Q29 15 52 24 Q73 12 91 28 Q113 31 110 54 Q119 76 99 88 Q86 108 64 100 Q41 111 25 91 Q11 74 20 57Z"],
        }
        contours[key]=style4_contours[key][ix]
    if body_path is not None:
        contours[key]=body_path
    p["outline"] = f'<path d="{contours[key]}" fill="none" stroke="#344955" stroke-width="1.3" stroke-linejoin="round"/>'
    if key=="thyroid_follicle":
        if ix==0:
            p["outline"]+=f'<circle cx="64" cy="64" r="34" fill="none" stroke="#344955" stroke-width="1.1"/>'
        else:
            rings=[(36,38,13),(90,36,14),(39,90,14),(90,89,13)] if not style4 else [(37,39,15),(90,38,12),(39,88,12),(90,90,15)]
            p["outline"]="".join(
                f'<circle cx="{x}" cy="{y}" r="{r+5}" fill="none" stroke="#344955" stroke-width="1.1"/>'
                f'<circle cx="{x}" cy="{y}" r="{max(7,r-4)}" fill="none" stroke="#344955" stroke-width=".85"/>'
                for x,y,r in rings
            )
    return p

def render_svg(key: str, index: int, title: str, description: str, style4: bool=False) -> str:
    if key not in CONCEPTS: raise KeyError(key)
    if index not in (0,1): raise IndexError("form index must be 0 or 1")
    p=_parts(key,index,style4); groups=[]
    # Outline is intentionally its own final editable region; shape fills and facets stay semantic.
    for rid in _PAINT_ORDER[key]:
        content=p[rid]
        groups.append(f'<g data-region="{rid}">{content}</g>')
    form=CONCEPTS[key]["forms"][index]["id"]
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 128" role="img" aria-labelledby="title desc" data-asset="endocrine.{key}.{form}"><title id="title">{escape(title)}</title><desc id="desc">{escape(description)}</desc>{"".join(groups)}</svg>'

if __name__ == "__main__":
    import xml.etree.ElementTree as ET
    import re
    reference_ids={r["id"] for r in REFERENCES}
    assert all({"id","citation","doi","url","design_decision"} <= set(r) for r in REFERENCES)
    for k,c in CONCEPTS.items():
        assert c["key"]==k and len(c["forms"])==2
        assert set(c["refs"]) <= reference_ids
        for i in (0,1):
            expected={r["id"] for r in regions_for(k,i)}
            geometries=[]
            for depth in (False,True):
                root=ET.fromstring(render_svg(k,i,"Endocrine tissue","Generic topology schematic.",depth))
                assert root.attrib["viewBox"]=="0 0 128 128"
                assert root.attrib["data-asset"]==f'endocrine.{k}.{c["forms"][i]["id"]}'
                groups=[e for e in root if e.tag.endswith("g")]
                assert {g.get("data-region") for g in groups}==expected
                assert [g.get("data-region") for g in groups]==_PAINT_ORDER[k]
                for g in groups:
                    assert len(g),(k,i,g.get("data-region"))
                    # Every semantic group must contain a visible fill or stroke.
                    assert any((el.get("fill") not in (None,"none") or el.get("stroke") not in (None,"none")) for el in g.iter()),(k,i,g.get("data-region"))
                geom=[]
                for el in root.iter():
                    for attr in ("d","cx","cy","rx","ry","r","x","y","width","height"):
                        if attr in el.attrib: geom.append((el.tag,attr,el.attrib[attr]))
                    if el.tag.endswith("ellipse"):
                        cx=float(el.get("cx")); cy=float(el.get("cy")); rx=float(el.get("rx")); ry=float(el.get("ry"))
                        assert cx-rx >= 0 and cy-ry >= 0 and cx+rx <= 128 and cy+ry <= 128,(k,i,el.attrib)
                    if el.tag.endswith("path"):
                        nums=[float(n) for n in re.findall(r"-?\d+(?:\.\d+)?",el.get("d",""))]
                        assert all(0 <= n <= 128 for n in nums),(k,i,el.get("d"))
                geometries.append(tuple(geom))
                assert not ({e.tag.split("}")[-1] for e in root.iter()} & {"script","foreignObject","image","filter","iframe"})
                assert all(not any(a.endswith("href") and not v.startswith("#") for a,v in e.attrib.items()) for e in root.iter())
                assert len(root.findall("{http://www.w3.org/2000/svg}title"))==1
            assert geometries[0] != geometries[1],(k,i,"Style 4 geometry must differ from Style 1")
    print("PASS: 6 concepts, 12 forms, 24 safe accessible SVG renderings")
