"""Original Style 4 depth companions for the finite tissue/vascular set."""
from __future__ import annotations

from xml.sax.saxutils import escape
import math


REGIONS = {
    "epithelial_sheet": [("epithelium", "#D8EDE5"), ("junction", "#C88770"), ("outline", "#314955")],
    "epithelial_acinus": [("epithelium", "#D8EDE5"), ("lumen", "#FFF9ED"), ("matrix", "#A9D2AE"), ("outline", "#314955")],
    "capillary": [("endothelium", "#D8EDE5"), ("lumen", "#FFF9ED"), ("matrix", "#A9D2AE"), ("outline", "#314955")],
    "vessel_wall": [("endothelium", "#D8EDE5"), ("smooth_muscle", "#D98772"), ("matrix", "#A9D2AE"), ("lumen", "#FFF9ED"), ("outline", "#314955")],
    "lymphatic_capillary": [("endothelium", "#D8EDE5"), ("fluid", "#8EC4DB"), ("matrix", "#A9D2AE"), ("lumen", "#FFF9ED"), ("outline", "#314955")],
    "angiogenic_sprout": [("endothelium", "#D8EDE5"), ("matrix", "#A9D2AE"), ("lumen", "#FFF9ED"), ("outline", "#314955")],
    "collagen": [("matrix", "#D8B987"), ("accent", "#C98768"), ("outline", "#314955")],
    "basement_membrane": [("basement_sheets", "#A9D2AE"), ("attachment_arms", "#D8EDE5"), ("submembrane_mesh", "#C98768"), ("outline", "#314955")],
    "skeletal_muscle": [("muscle_fiber", "#D98772"), ("matrix", "#A9D2AE"), ("nucleus", "#877DAC"), ("outline", "#314955")],
    "adipose": [("lipid_droplet", "#F0D38A"), ("cytoplasm", "#D8EDE5"), ("nucleus", "#877DAC"), ("outline", "#314955")],
}


def regions_for(key: str, index: int) -> list[dict[str, str]]:
    if key not in REGIONS or index not in (0, 1):
        raise KeyError((key, index))
    labels = {
        "epithelium": "Epithelial cells", "junction": "Cell junctions", "lumen": "Lumen",
        "matrix": "Matrix / connective support", "endothelium": "Endothelial wall",
        "smooth_muscle": "Smooth-muscle layer", "fluid": "Tissue-fluid cue",
        "accent": "Crossing collagen fibers", "basement_sheets": "Basement-membrane layers",
        "attachment_arms": "Cell–matrix attachment structures", "submembrane_mesh": "Submembrane matrix mesh",
        "muscle_fiber": "Muscle fibers", "nucleus": "Peripheral nuclei", "lipid_droplet": "Lipid store",
        "cytoplasm": "Cytoplasm", "outline": "Structural outlines",
    }
    return [{"id": rid, "label": labels[rid], "default": color} for rid, color in REGIONS[key]]


def _fill(path: str, color: str, *, opacity: str | None = None, extra: str = "") -> str:
    op = f' opacity="{opacity}"' if opacity else ""
    return f'<path d="{path}" fill="{color}"{op} {extra}/>'


def _stroke(path: str, color: str, width: float = 1.2, *, opacity: str | None = None) -> str:
    op = f' opacity="{opacity}"' if opacity else ""
    return f'<path d="{path}" fill="none" stroke="{color}" stroke-width="{width}" stroke-linecap="round" stroke-linejoin="round"{op}/>'


def _cell(cx: float, cy: float, rx: float, ry: float, color: str, tilt: float = 0) -> str:
    return f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="{color}" transform="rotate({tilt} {cx} {cy})"/>'


def _ring(cx: int, cy: int, outer: int, inner: int, color: str, *, ellipse_y: int | None = None) -> str:
    ry = ellipse_y or outer
    iry = round(inner * ry / outer)
    return (f'<path d="M{cx} {cy-ry} A{outer} {ry} 0 1 1 {cx-0.1} {cy-ry} '
            f'M{cx} {cy-iry} A{inner} {iry} 0 1 0 {cx+0.1} {cy-iry} Z" '
            f'fill="{color}" fill-rule="evenodd"/>')


def _parts(key: str, index: int) -> dict[str, str]:
    p: dict[str, str] = {rid: "" for rid, _ in REGIONS[key]}
    ink="#314955"; hi="#FFFFFF"; shade="#294652"
    if key == "epithelial_sheet":
        if index == 0:
            cells = ["M19 41 Q29 35 39 40 L39 83 Q29 88 19 82Z", "M42 39 Q53 35 64 40 L64 84 Q53 88 42 83Z", "M67 40 Q78 35 89 40 L89 83 Q78 88 67 84Z", "M92 40 Q102 37 110 42 L110 80 Q101 85 92 82Z"]
            p['epithelium']=''.join(_fill(d,'#D8EDE5') for d in cells)
            p['junction']=_fill('M39 39L42 39V84L39 84ZM64 40L67 40V84L64 84ZM89 40L92 40V82L89 83Z','#C88770')
            p['outline']=_stroke('M18 41Q29 34 40 40V83Q29 89 18 82Z M41 39Q53 34 65 40V84Q53 89 41 83Z M66 40Q78 34 90 40V83Q78 89 66 84Z M91 41Q102 36 111 42V80Q101 86 91 82Z',ink,1.2)
            p['epithelium'] += _fill('M19 72Q29 77 39 72V82Q29 88 19 82Z M42 72Q53 77 64 73V83Q53 88 42 83Z M67 72Q78 77 89 72V82Q78 88 67 83Z M92 70Q101 75 110 72V80Q101 85 92 82Z',shade,opacity='.17')
            p['epithelium'] += _fill('M22 43Q29 40 36 42V47Q29 44 22 47Z M45 41Q53 38 61 42V47Q53 44 45 47Z M70 42Q78 39 86 42V47Q78 44 70 47Z',hi,opacity='.6')
        else:
            tiles=["M20 34Q30 21 41 32L39 49Q30 55 20 47Z","M41 32Q53 23 64 32L62 49Q52 54 39 49Z","M64 32Q76 22 88 32L87 49Q75 55 62 49Z","M88 32Q100 23 109 35L108 48Q97 54 87 49Z","M20 60Q30 51 40 60L39 77Q29 84 20 74Z","M40 60Q52 52 64 60L63 77Q51 83 39 77Z","M64 60Q76 52 88 60L87 77Q75 83 63 77Z","M88 60Q99 52 108 60L108 75Q97 83 87 77Z"]
            p['epithelium']=''.join(_fill(d,'#D8EDE5') for d in tiles)
            p['junction']=_stroke('M20 48Q30 55 40 49M40 49Q52 55 63 49M63 49Q75 55 87 49M87 49Q98 55 109 48M20 75Q30 84 40 77M40 77Q52 84 63 77M63 77Q75 84 87 77M87 77Q98 84 109 75', '#C88770', 2.0)
            p['outline']=_stroke(' '.join(tiles),ink,1.2)
            p['epithelium']+=_fill('M27 29Q31 27 35 31L34 46Q30 48 26 46Z M72 28Q77 26 81 31L80 46Q76 48 71 46Z',hi,opacity='.52')
    elif key == 'epithelial_acinus':
        if index == 0:
            cells=[(64,31,10,12),(43,39,11,12),(85,39,11,12),(31,58,10,13),(97,58,10,13),(43,76,11,12),(85,76,11,12),(64,86,11,11)]
            p['epithelium']=''.join(_cell(x,y,rx,ry,'#D8EDE5') for x,y,rx,ry in cells)
            p['lumen']=_fill('M60 46 Q64 42 68 46 L67 55 Q64 58 61 55Z','#FFF9ED')+_stroke('M60 46Q64 42 68 46L67 55Q64 58 61 55Z',ink,1.1)
            p['matrix']=_fill('M29 79Q64 101 99 79L96 88Q64 109 32 88Z','#A9D2AE')
            p['outline']=_stroke('M29 79Q64 101 99 79M32 88Q64 109 96 88 '+' '.join(f'M{x-rx} {y}A{rx} {ry} 0 1 0 {x+rx} {y}' for x,y,rx,ry in cells),ink,1.2)
            p['epithelium']+=_fill('M58 25Q64 21 70 25L67 34Q64 36 61 34Z M36 51Q40 47 44 50L42 61Q39 63 36 60Z','#FFFFFF',opacity='.54')
        else:
            p['epithelium']=''.join(_fill(d,'#D8EDE5') for d in [
                'M64 22A42 42 0 0 1 94 35L82 47A24 24 0 0 0 64 40Z',
                'M94 35A42 42 0 0 1 106 64L88 64A24 24 0 0 0 82 47Z',
                'M106 64A42 42 0 0 1 94 93L82 81A24 24 0 0 0 88 64Z',
                'M94 93A42 42 0 0 1 64 106L64 88A24 24 0 0 0 82 81Z',
                'M64 106A42 42 0 0 1 34 93L46 81A24 24 0 0 0 64 88Z',
                'M34 93A42 42 0 0 1 22 64L40 64A24 24 0 0 0 46 81Z',
                'M22 64A42 42 0 0 1 34 35L46 47A24 24 0 0 0 40 64Z',
                'M34 35A42 42 0 0 1 64 22L64 40A24 24 0 0 0 46 47Z'])
            p['lumen']=_fill('M64 43A21 21 0 1 1 63.9 43Z','#FFF9ED')
            p['matrix']=_ring(64,64,49,44,'#A9D2AE')
            p['outline']=_stroke('M64 15A49 49 0 1 1 63.9 15 M64 43A21 21 0 1 1 63.9 43',ink,1.2)
            p['epithelium']+=_fill('M65 25Q83 27 93 40L87 46Q78 36 65 34Z',hi,opacity='.45')
    elif key == 'capillary':
        if index == 0:
            p['endothelium']=_fill('M17 43Q26 33 38 41H111V54H37Q27 61 17 54Z M17 76Q27 68 38 76H111V89H37Q26 97 17 89Z','#D8EDE5')
            p['lumen']=_fill('M18 55Q28 52 38 55H111V74H38Q28 77 18 74Z','#FFF9ED')
            p['matrix']=_fill('M17 36Q64 30 112 35V39Q63 35 17 41Z M17 92Q64 98 112 92V96Q64 102 17 97Z','#A9D2AE')
            p['outline']=_stroke('M17 43Q26 33 38 41H111M17 54Q27 61 38 54H111M17 76Q27 68 38 76H111M17 89Q26 97 38 89H111',ink,1.2)
            p['endothelium']+=_fill('M43 42H105V46H43ZM43 76H105V80H43Z','#FFFFFF',opacity='.55')
        else:
            p['endothelium']=_ring(64,64,39,24,'#D8EDE5',ellipse_y=35)
            p['lumen']=_fill('M64 42A22 22 0 1 1 63.9 42Z','#FFF9ED')
            p['matrix']=_ring(64,64,49,45,'#A9D2AE',ellipse_y=45)
            p['outline']=_stroke('M64 15A49 49 0 1 1 63.9 15 M64 29A35 35 0 1 1 63.9 29 M64 42A22 22 0 1 1 63.9 42',ink,1.2)
            p['endothelium']+=_fill('M41 43A31 28 0 0 1 76 33L73 39A24 21 0 0 0 47 48Z','#FFFFFF',opacity='.56')
    elif key == 'vessel_wall':
        radii=(20,34,45) if index==0 else (24,34,45)
        lumen_radius=radii[0]
        p['lumen']=_fill(f'M64 {64-lumen_radius}A{lumen_radius} {lumen_radius} 0 0 1 64 {64+lumen_radius}A{lumen_radius} {lumen_radius} 0 0 1 64 {64-lumen_radius}Z','#FFF9ED')
        p['endothelium']=_ring(64,64,radii[0]+5,radii[0],'#D8EDE5')
        p['smooth_muscle']=_ring(64,64,radii[1]+(8 if index==0 else 4),radii[1]-(8 if index==0 else 4),'#D98772')
        p['matrix']=_ring(64,64,49,44,'#A9D2AE')
        p['outline']=_stroke(f'M64 15A49 49 0 1 1 63.9 15 M64 {64-lumen_radius}A{lumen_radius} {lumen_radius} 0 1 1 63.9 {64-lumen_radius} M64 28A36 36 0 1 1 63.9 28',ink,1.2)
        p['smooth_muscle']+=_fill('M37 41A37 37 0 0 1 74 28L72 34A31 31 0 0 0 42 46Z',hi,opacity='.34')
    elif key == 'lymphatic_capillary':
        if index==0:
            p['endothelium']=_fill('M35 108V55A29 29 0 0 1 93 55V108H82V55A18 18 0 0 0 46 55V108Z','#D8EDE5')
            p['lumen']=_fill('M48 106V55A16 16 0 0 1 80 55V106Z','#FFF9ED')
            p['matrix']=_fill('M19 43V107H24V43ZM104 43V107H109V43Z','#A9D2AE')
            p['fluid']=''.join(_cell(x,y,3.2,4,'#8EC4DB') for x,y in [(26,67),(101,59),(48,47)])
            p['outline']=_stroke('M35 108V55A29 29 0 0 1 93 55V108M46 108V55A18 18 0 0 1 82 55V108',ink,1.2)
            p['endothelium']+=_fill('M44 57A20 20 0 0 1 62 38L64 44A14 14 0 0 0 49 58Z','#FFFFFF',opacity='.5')
        else:
            p['endothelium']=_fill('M20 83Q36 76 53 81L64 72L75 81Q94 75 109 83V101H20Z','#D8EDE5')
            p['lumen']=_fill('M24 89Q40 84 55 89L64 82L74 89Q92 83 105 89V97H24Z','#FFF9ED')
            p['matrix']=_fill('M18 30Q29 24 42 31L45 38Q31 34 21 41ZM84 31Q98 24 111 31L107 40Q96 34 86 39ZM19 106Q39 111 58 106M79 106Q98 111 110 106','#A9D2AE')
            p['fluid']=''.join(_cell(x,y,3.4,4,'#8EC4DB') for x,y in [(46,48),(61,61),(70,88)])
            p['outline']=_stroke('M20 83Q36 76 53 81L64 72L75 81Q94 75 109 83V101H20Z M24 89Q40 84 55 89L64 82L74 89Q92 83 105 89V97H24Z',ink,1.2)
    elif key == 'angiogenic_sprout':
        if index==0:
            p['endothelium']=_fill('M15 78H48Q59 78 64 67L77 40Q84 23 98 27Q108 31 102 41Q99 46 91 49Q85 53 81 62L73 82Q67 100 49 100H15Z','#D8EDE5')
            p['lumen']=_fill('M17 84H48Q57 84 61 72L74 45Q81 31 91 34Q96 36 92 41Q87 44 82 53L69 82Q64 94 49 94H17Z','#FFF9ED')
            p['matrix']=_fill('M17 106Q50 101 78 106T111 104V110Q81 114 51 109T17 112Z','#A9D2AE')
            p['outline']=_stroke('M15 78H48Q59 78 64 67L77 40Q84 23 98 27Q108 31 102 41Q99 46 91 49Q85 53 81 62L73 82Q67 100 49 100H15 M17 84H48Q57 84 61 72L74 45Q81 31 91 34',ink,1.2)
        else:
            p['endothelium']=_fill('M15 56H42Q51 56 58 49L77 30Q86 20 98 26Q107 31 99 40L79 60Q74 64 79 69L99 89Q107 98 98 103Q86 109 77 98L58 79Q51 72 42 72H15Z','#D8EDE5')
            p['lumen']=_fill('M16 62H42Q49 62 55 55L76 35Q84 27 92 32Q97 35 91 41L72 60Q68 64 72 68L91 87Q97 93 92 97Q84 101 76 93L55 73Q49 66 42 66H16Z','#FFF9ED')
            p['matrix']=_fill('M17 107Q39 103 54 107M77 107Q96 111 111 105','#A9D2AE')
            p['outline']=_stroke('M15 56H42Q51 56 58 49L77 30Q86 20 98 26M15 72H42Q51 72 58 79L77 98Q86 109 98 103M42 62Q49 62 55 55L76 35M42 66Q49 66 55 73L76 93',ink,1.2)
        p['endothelium']+=_fill('M84 29Q93 23 100 29L94 33Q89 31 84 35Z','#FFFFFF',opacity='.62')
    elif key == 'collagen':
        if index==0:
            tracks=[('M18 31Q43 27 67 31T111 32', '#D8B987'),('M18 43Q43 39 68 43T111 44','#C98768'),('M18 55Q44 51 68 55T111 56','#D8B987'),('M18 67Q44 63 68 67T111 68','#C98768'),('M18 79Q44 75 68 79T111 80','#D8B987'),('M18 91Q44 87 68 91T111 92','#C98768')]
            for n,(path,col) in enumerate(tracks):
                strand=_stroke(path,ink,6.5)+_stroke(path,col,4.2)+_stroke(path,'#FFFFFF',.8,opacity='.65')
                if n%2==0:p['matrix']+=strand
                else:p['accent']+=strand
            p['outline']=_stroke('M16 26Q63 17 112 26M16 96Q64 107 112 96',ink,1.15,opacity='.75')
        else:
            # Rounded depth ribbons cross in a distributed mat; separate hues
            # and short overpasses make each woven crossing visible.
            horizontals=['M17 28Q44 24 70 28T111 29','M17 61Q43 57 68 61T111 62','M17 94Q43 90 68 94T111 95']
            diagonals=['M25 17Q34 63 47 111','M54 17Q62 62 67 111','M103 17Q85 63 66 111']
            for path in horizontals:
                p['matrix']+=_stroke(path,ink,7)+_stroke(path,'#D8B987',4.8)+_stroke(path,'#FFF5DA',1.0,opacity='.72')
            for path in diagonals:
                p['accent']+=_stroke(path,ink,7)+_stroke(path,'#C98768',4.7)+_stroke(path,'#F6D2B6',.9,opacity='.75')
            overpasses=['M24 28Q29 26 34 28','M94 29Q99 27 104 29','M56 61Q61 59 66 61','M38 94Q43 92 48 94','M68 94Q73 92 78 94']
            for path in overpasses:
                p['accent']+=_stroke(path,ink,7)+_stroke(path,'#C98768',4.7)+_stroke(path,'#F6D2B6',.9,opacity='.75')
            p['outline']=_stroke('M18 20Q39 13 59 19L109 62L110 101Q88 115 65 108L19 65Z',ink,1.15,opacity='.7')
    elif key == 'basement_membrane':
        if index==0:
            band='M18 60Q42 54 64 59T110 58V67Q84 72 62 66T18 70Z'
            lower='M19 73Q42 67 64 72T109 71V78Q84 82 63 77T19 81Z'
            p['basement_sheets']=_fill(band,'#A9D2AE')+_fill(lower,'#B9DAB8')+_fill('M21 61Q42 57 63 61T107 60V63Q83 68 62 63T21 66Z','#FFFFFF',opacity='.55')
            arms='M34 57V42Q34 37 38 37Q42 37 42 42V58M62 57V40Q62 35 66 35Q70 35 70 40V57M90 57V42Q90 37 94 37Q98 37 98 42V57'
            p['attachment_arms']=_fill('M32 42Q32 34 38 34Q44 34 44 42V58H40V42Q40 39 38 39Q36 39 36 42V58Z M60 40Q60 32 66 32Q72 32 72 40V58H68V40Q68 37 66 37Q64 37 64 40V58Z M88 42Q88 34 94 34Q100 34 100 42V58H96V42Q96 39 94 39Q92 39 92 42V58Z','#D8EDE5')
            mesh='M22 89Q40 82 58 90T95 89T108 91M22 100Q42 93 61 101T99 100M36 86L42 106M70 85L74 107M99 86L94 106'
            p['submembrane_mesh']=_stroke(mesh,ink,4)+_stroke(mesh,'#C98768',2.5)
            p['outline']=_stroke(band+' '+lower+' '+arms,ink,1.2)
        else:
            p['attachment_arms']=''.join(_fill(f'M{x} 27Q{x+8} 22 {x+16} 27V62Q{x+8} 67 {x} 62Z','#D8EDE5') for x in [20,39,58,77,96])
            p['basement_sheets']=_fill('M17 68Q42 62 64 67T111 66V76Q84 81 62 75T17 79Z M18 81Q42 75 64 80T110 79V87Q84 91 62 85T18 90Z','#A9D2AE')+_fill('M20 70Q42 66 63 70T108 69V72Q84 77 62 72T20 76Z','#FFFFFF',opacity='.5')
            arms=''.join(f'M{x} 62V69' for x in [28,47,66,85,104])
            mesh='M21 100Q43 94 63 100T108 100M28 110Q47 104 67 110T109 108M39 96L43 112M74 96L77 112M99 96L94 111'
            p['submembrane_mesh']=_stroke(mesh,ink,4)+_stroke(mesh,'#C98768',2.5)
            p['outline']=_stroke('M20 27Q28 22 36 27V62Q28 67 20 62Z M39 27Q47 22 55 27V62Q47 67 39 62Z M58 27Q66 22 74 27V62Q66 67 58 62Z M77 27Q85 22 93 27V62Q85 67 77 62Z M96 27Q104 22 112 27V62Q104 67 96 62Z M17 68Q42 62 64 67T111 66V87Q84 91 62 85T18 90Z '+arms,ink,1.2)
    elif key == 'skeletal_muscle':
        if index==0:
            fibers=['M18 27Q62 19 110 27V43Q62 51 18 44Z','M18 53Q63 46 110 53V69Q63 77 18 70Z','M18 79Q63 72 110 79V96Q63 104 18 97Z']
            p['muscle_fiber']=''.join(_fill(d,'#D98772')+_fill(d.replace('V43','V31'), '#FFFFFF',opacity='.35') for d in fibers)
            p['matrix']=_fill('M18 47Q64 54 110 47V51Q64 58 18 51ZM18 73Q64 80 110 73V77Q64 84 18 77Z','#A9D2AE')
            p['nucleus']=''.join(_cell(x,y,2.4,5.5,'#877DAC') for x,y in [(27,35),(100,61),(29,88),(99,88)])
            p['outline']=_stroke(' '.join(fibers),ink,1.2)
        else:
            centers=[(40,40),(64,40),(88,40),(40,64),(64,64),(88,64),(40,88),(64,88),(88,88)]
            p['muscle_fiber']=''.join(_cell(x,y,11,11,'#D98772')+_fill(f'M{x-8} {y-3}A8 8 0 0 1 {x+4} {y-8}Q{x+9} {y-4} {x+8} {y+1}A8 8 0 0 0 {x-8} {y-3}Z','#FFFFFF',opacity='.48') for x,y in centers)
            p['matrix']=_ring(64,64,49,45,'#A9D2AE')
            p['nucleus']=''.join(_cell(x-7,y,2.4,4,'#877DAC') for x,y in centers)
            p['outline']=_stroke(' '.join(f'M{x-11} {y}A11 11 0 1 0 {x+11} {y}' for x,y in centers)+' M64 15A49 49 0 1 1 63.9 15',ink,1.2)
    elif key == 'adipose':
        if index==0:
            p['lipid_droplet']=_fill('M64 25A39 39 0 1 1 63.9 25Z','#F0D38A')+_fill('M43 37Q55 24 76 29Q91 32 96 47Q79 34 64 35Q52 34 43 37Z','#FFFFFF',opacity='.53')
            p['cytoplasm']=_ring(64,64,45,39,'#D8EDE5')
            p['nucleus']=_cell(37,83,5,8,'#877DAC',-28)
            p['outline']=_stroke('M64 19A45 45 0 1 1 63.9 19',ink,1.2) + '<ellipse cx="37" cy="83" rx="5" ry="8" transform="rotate(-28 37 83)" fill="none" stroke="#314955" stroke-width="1.2"/>'
        else:
            cells=[(43,40),(77,38),(60,65),(93,67),(35,90),(83,97)]
            p['cytoplasm']=''.join(_ring(x,y,15,12,'#D8EDE5') for x,y in cells)
            p['lipid_droplet']=''.join(_cell(x,y,12,12,'#F0D38A')+_fill(f'M{x-6} {y-5}A7 7 0 0 1 {x+3} {y-9}Q{x+8} {y-5} {x+7} {y-1}A8 8 0 0 0 {x-6} {y-5}Z','#FFFFFF',opacity='.48') for x,y in cells)
            p['nucleus']=''.join(_cell(x-11,y+4,2.5,4.5,'#877DAC') for x,y in cells)
            p['outline']=''.join(_stroke(f'M{x} {y-15}A15 15 0 0 1 {x} {y+15}A15 15 0 0 1 {x} {y-15}',ink,1.2) for x,y in cells)
    else:
        raise KeyError(key)
    return p


def render_svg(key: str, index: int, title: str, description: str) -> str:
    if key not in REGIONS or index not in (0, 1):
        raise KeyError((key, index))
    p=_parts(key,index)
    groups=[]
    # Thin structural strokes are rendered last for clean boundaries, while
    # same-region highlight and shade facets remain editable with each part.
    for rid,color in REGIONS[key]:
        if rid=='outline':
            content=p[rid]
        else:
            content=p[rid]
        groups.append(f'<g data-region="{rid}">{content}</g>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 128" role="img" aria-labelledby="title desc">'
            f'<title id="title">{escape(title)}</title><desc id="desc">{escape(description)}</desc>{"".join(groups)}</svg>')


if __name__ == '__main__':
    import xml.etree.ElementTree as ET
    assert len(REGIONS)==10 and sum(len(v) for v in REGIONS.values())==40
    for key in REGIONS:
        for index in (0,1):
            root=ET.fromstring(render_svg(key,index,'Tissue schematic','Generic; not to scale.'))
            groups=[e for e in root if e.tag.endswith('g')]
            assert {e.get('data-region') for e in groups}=={r['id'] for r in regions_for(key,index)}
            assert all(len(g) for g in groups),(key,index)
            assert root.get('viewBox')=='0 0 128 128'
            assert not ({e.tag.split('}')[-1] for e in root.iter()} & {'script','foreignObject','image','filter','iframe'})
            assert all(not any(a.endswith('href') and not v.startswith('#') for a,v in e.attrib.items()) for e in root.iter())
    print('PASS: 10 concepts, 20 Style 4 companions, 40 visible semantic-region groups, safe accessible SVG')
