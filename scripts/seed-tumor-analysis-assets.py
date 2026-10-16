#!/usr/bin/env python3
"""Author 40 original editable drawings for two pending scientific packs.

No existing Library assets, rights grants, shared catalog or release decisions
are changed. Geometry is schematic, deterministic and independent of published
artwork. Run with --destination-root to inspect/reproduce away from the source.
"""
from __future__ import annotations

import argparse
from collections import Counter
from html import escape
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATE = "2026-10-15"
OUTLINE = "#26323D"
COLORS = {"body": "#C7F2EC", "nucleus": "#B8B5FF", "accent": "#F4A261",
          "blue": "#5EA9DD", "teal": "#58B8AE", "pink": "#D895B3",
          "pale": "#E8EEF7", "purple": "#7B78C9", "orange": "#E76F51"}
ORIGINAL = ("Original editable vector geometry authored for Superbench Figure Tool from "
            "generic scientific concepts and primary-literature conventions. Published figures "
            "informed biological meaning and plot conventions only. No artwork, screenshot, "
            "measured data, tracing, structural coordinates or third-party vector component was incorporated.")

REFERENCES = [
 {"id":"elyada-2019", "citation":"Elyada E et al. Cross-species single-cell analysis of pancreatic ductal adenocarcinoma reveals antigen-presenting cancer-associated fibroblasts. Cancer Discovery. 2019.", "doi":"10.1158/2159-8290.CD-19-0094", "url":"https://pmc.ncbi.nlm.nih.gov/articles/PMC6727976/", "figure":"Figure 1A, B and F; Figure 2", "use":"Cellular context and heterogeneous fibroblast populations; violin widths show distributions. Original figures inspected; no source geometry or data reused."},
 {"id":"zilionis-2019", "citation":"Zilionis R et al. Single-cell transcriptomics of human and mouse lung cancers reveals conserved myeloid populations across individuals and species. Immunity. 2019.", "doi":"10.1016/j.immuni.2019.03.009", "url":"https://pmc.ncbi.nlm.nih.gov/articles/PMC6620049/", "figure":"Figure 4B, Q; neutrophil populations described in Results", "use":"Distinct cell-state populations require molecular evidence; labeled diverging expression heatmaps are distinct from cell-count diagrams. Figure 4 inspected; no measured values reused."},
 {"id":"liu-2020", "citation":"Liu E et al. Use of CAR-transduced natural killer cells in CD19-positive lymphoid tumors. New England Journal of Medicine. 2020.", "doi":"10.1056/NEJMoa1910607", "url":"https://pmc.ncbi.nlm.nih.gov/articles/PMC7101242/", "figure":"Figure 1 inspected for distinction from mechanistic drawings; Methods for CAR-NK identity", "use":"CAR-NK is an engineered NK-cell identity. The generic receptor drawing does not reproduce this trial's construct or clinical outcomes."},
 {"id":"cabrita-2020", "citation":"Cabrita R et al. Tertiary lymphoid structures improve immunotherapy and survival in melanoma. Nature. 2020.", "doi":"10.1038/s41586-019-1914-8", "url":"https://www.nature.com/articles/s41586-019-1914-8", "use":"Organized B-cell follicles and adjacent T-cell compartments, rather than an unstructured lymphocyte cluster. No survival effect is encoded."},
 {"id":"sallusto-1995", "citation":"Sallusto F et al. Dendritic cells use macropinocytosis and the mannose receptor to concentrate macromolecules in the major histocompatibility complex class II compartment. Journal of Experimental Medicine. 1995.", "doi":"10.1084/jem.182.2.389", "url":"https://pmc.ncbi.nlm.nih.gov/articles/PMC2192110/", "use":"Separate extracellular cargo from an intracellular uptake compartment; antigen uptake alone does not establish peptide presentation or T-cell activation."},
 {"id":"xue-2014", "citation":"Xue J et al. Transcriptome-based network analysis reveals a spectrum model of human macrophage activation. Immunity. 2014.", "doi":"10.1016/j.immuni.2014.01.006", "url":"https://pmc.ncbi.nlm.nih.gov/articles/PMC3991396/", "figure":"Figure 1J (caption and methods)", "use":"Depict several incoming environmental cues and an adjustable response continuum; avoid a universal M1/M2 binary."},
 {"id":"grakoui-1999", "citation":"Grakoui A et al. The immunological synapse: a molecular machine controlling T cell activation. Science. 1999.", "doi":"10.1126/science.285.5425.221", "url":"https://doi.org/10.1126/science.285.5425.221", "use":"Apposed membranes and clustered receptor–ligand contacts. Generic drawings omit receptor identity and do not require a universal bull's-eye arrangement."},
 {"id":"sonveaux-2008", "citation":"Sonveaux P et al. Targeting lactate-fueled respiration selectively kills hypoxic tumor cells in mice. Journal of Clinical Investigation. 2008.", "doi":"10.1172/JCI36843", "url":"https://pmc.ncbi.nlm.nih.gov/articles/PMC2582933/", "figure":"Figure 7", "use":"Oxygen supply and lactate production have different source directions. Figure inspected; symbols encode qualitative availability, not measured concentrations or universal metabolic dependence."},
 {"id":"anandi-2024", "citation":"Anandi L et al. Direct visualization of emergent metastatic features within an ex vivo model of the tumor microenvironment. Life Science Alliance. 2024.", "doi":"10.26508/lsa.202403053", "url":"https://pmc.ncbi.nlm.nih.gov/articles/PMC11487089/", "figure":"Figure 1A–C; Figure 7", "use":"Spatial supply boundaries and increasing distance can be shown separately from measured fluorescence plots. Figure 1 inspected. Drug distribution and oxygen are distinct, context-dependent gradients."},
 {"id":"trapnell-2014", "citation":"Trapnell C et al. Pseudo-temporal ordering of individual cells reveals dynamics and regulators of cell fate decisions. Nature Biotechnology. 2014.", "doi":"10.1038/nbt.2859", "url":"https://pmc.ncbi.nlm.nih.gov/articles/PMC4122333/", "figure":"Figure 2A–C and F", "use":"An inferred cell-state ordering may branch; pseudotime is distinct from collection time. Heatmaps require a visible scale. Figure inspected; no cell coordinates or values reused."},
 {"id":"omicsvolcano-2021", "citation":"Kuznetsova I et al. OmicsVolcano: software for intuitive visualization and interactive exploration of high-throughput biological data. STAR Protocols. 2021.", "doi":"10.1016/j.xpro.2020.100279", "url":"https://pmc.ncbi.nlm.nih.gov/articles/PMC7821039/", "figure":"Figure 1 (caption)", "use":"Volcano axes separate effect size from adjusted statistical evidence. Hand-authored example points are not analytical output."},
 {"id":"tls-histology-2021", "citation":"TLS identification and density assessment on H&E-stained digital slides of lung cancer. PLOS ONE. 2021.", "doi":"10.1371/journal.pone.0256907", "url":"https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0256907", "use":"TLS drawings distinguish organized follicles and possible germinal centers; a diagram does not classify a sample or guarantee TLS maturity."},
 {"id":"mcinnes-2018", "citation":"McInnes L, Healy J, Melville J. UMAP: Uniform Manifold Approximation and Projection for Dimension Reduction. 2018. arXiv:1802.03426.", "url":"https://arxiv.org/abs/1802.03426", "use":"UMAP is a dimension-reduction embedding; labeled embedding axes do not denote physical spatial coordinates. Method source only, with no source point coordinates reused."},
 {"id":"kaplan-meier-1958", "citation":"Kaplan EL, Meier P. Nonparametric estimation from incomplete observations. Journal of the American Statistical Association. 1958.", "doi":"10.1080/01621459.1958.10501452", "url":"https://doi.org/10.1080/01621459.1958.10501452", "use":"The survival estimate is a nonincreasing step function, and censoring is distinct from an event. Example marks and steps have no patient-data interpretation."},
 {"id":"tinevez-2017", "citation":"Tinevez JY et al. TrackMate: An open and extensible platform for single-particle tracking. Methods. 2017.", "doi":"10.1016/j.ymeth.2016.09.016", "url":"https://pubmed.ncbi.nlm.nih.gov/27713081/", "use":"Tracking links observed positions over acquisition time. These hand-authored positions represent the drawing convention only, not a computed track."},
]
REF = {r["id"]:r for r in REFERENCES}


def path(d): return f'<path d="{d}"/>'
def circle(x,y,r): return f'<circle cx="{x}" cy="{y}" r="{r}"/>'
def ellipse(x,y,rx,ry): return f'<ellipse cx="{x}" cy="{y}" rx="{rx}" ry="{ry}"/>'
def rect(x,y,w,h,rx=0): return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}"/>'
def line(x1,y1,x2,y2): return path(f'M{x1} {y1}L{x2} {y2}')


class Drawing:
    def __init__(self): self.parts=[]; self.regions={}
    def add(self, role, label, color, content, *, stroke=False, width=2.8, dash=None):
        region={"id":role,"label":label,"default":color,"paint":"both" if role=="outline" else ("stroke" if stroke else "fill")}
        if role in self.regions:
            assert self.regions[role]["default"]==color
        else:self.regions[role]=region
        attrs=f'fill="none" stroke="{color}" stroke-width="{width}"' if stroke else f'fill="{color}" stroke="none"'
        if dash:attrs+=f' stroke-dasharray="{dash}"'
        self.parts.append(f'<g data-region="{role}" {attrs} stroke-linecap="round" stroke-linejoin="round">{content}</g>')
    def outline(self, content, width=2.8, dash=None):self.add("outline","Contours and labels",OUTLINE,content,stroke=True,width=width,dash=dash)
    def shape(self,role,label,color,content,width=2.8):
        self.add(role,label,color,content);self.outline(content,width)
    def text(self,x,y,value,size=8,anchor="middle",rotate=None):
        transform=f' transform="rotate({rotate} {x} {y})"' if rotate else ''
        content=f'<text x="{x}" y="{y}" text-anchor="{anchor}" font-family="Arial, sans-serif" font-size="{size}" font-weight="400"{transform}>{escape(value)}</text>'
        self.add("outline","Contours and labels",OUTLINE,content)
    def arrow(self,x1,y1,x2,y2,role="outline",label="Contours and labels",color=OUTLINE,width=2.4):
        import math
        a=math.atan2(y2-y1,x2-x1);r=5
        x3,y3=x2-r*math.cos(a-.55),y2-r*math.sin(a-.55)
        x4,y4=x2-r*math.cos(a+.55),y2-r*math.sin(a+.55)
        self.add(role,label,color,line(x1,y1,x2,y2)+path(f'M{x3:.2f} {y3:.2f}L{x2} {y2}L{x4:.2f} {y4:.2f}'),stroke=True,width=width)
    def svg(self,title,desc):
        return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 128" role="img" aria-labelledby="title desc">\n'
                f'<title id="title">{escape(title)}</title>\n<desc id="desc">{escape(desc)}</desc>\n'+"\n".join(self.parts)+'\n</svg>\n')


def cell(d,x,y,r=23,role="cell_body",fill=COLORS["body"],nucleus=True):
    d.shape(role,"Cell body" if role=="cell_body" else "Tumor-cell context",fill,circle(x,y,r))
    if nucleus:d.shape("nucleus","Nuclei",COLORS["nucleus"],ellipse(x-3,y+1,r*.42,r*.35),2)

def spindle(d,matrix=False):
    if matrix:
        d.add("matrix","Extracellular matrix",COLORS["teal"],path('M17 23Q51 37 106 22M15 31Q59 46 112 34M15 98Q52 84 111 104M20 108Q55 96 108 112'),stroke=True,width=3)
        geom=path('M17 77Q44 48 47 36L57 50Q78 55 110 46L89 66Q81 73 91 96L68 82Q49 76 25 92L38 73Z')
    else:
        d.add("matrix","Extracellular matrix",COLORS["teal"],path('M26 104Q66 99 105 77M30 113Q70 108 111 88'),stroke=True,width=2.2)
        geom=path('M14 91Q35 58 54 48Q73 41 113 32Q95 58 76 74Q59 84 14 91Z')
    d.shape("cell_body","Fibroblast cytoplasm",COLORS["body"],geom)
    fibers='M36 75Q52 64 82 56M38 80Q58 74 84 64' if matrix else 'M34 77Q54 65 89 48M36 83Q63 76 93 58'
    d.add("cytoskeleton","Cytoplasmic fibers",COLORS["teal"],path(fibers),stroke=True,width=2)
    d.shape("nucleus","Fibroblast nucleus",COLORS["nucleus"],ellipse(64,64,15,8),2.2)
    return d

def neutrophil(d,contact=False):
    if contact:
        cell(d,91,67,24,role="tumor_context",fill=COLORS["pink"])
        x,y,r=42,61,28
    else:x,y,r=64,64,38
    d.shape("cell_body","Neutrophil cytoplasm",COLORS["body"],circle(x,y,r))
    nuc=path(f'M{x-15} {y-5}C{x-17} {y-17} {x-3} {y-20} {x+2} {y-10}C{x+14} {y-16} {x+23} {y-3} {x+12} {y+6}C{x+20} {y+18} {x+1} {y+24} {x-4} {y+11}C{x-19} {y+16} {x-24} {y+3} {x-15} {y-5}Z')
    d.shape("nucleus","Lobulated nuclei",COLORS["nucleus"],nuc,2)
    d.add("granules","Cytoplasmic granules",COLORS["accent"],''.join(circle(x+a,y+b,2) for a,b in [(-18,-17),(12,-18),(-21,14),(19,11),(6,23),(-4,-25)]))
    return d

def car_nk(d,contact=False):
    if contact:cell(d,94,64,23,role="target",fill=COLORS["pink"]);x,y,r=39,64,27
    else:x,y,r=61,67,34
    cell(d,x,y,r)
    d.add("granules","NK-cell cytotoxic granules",COLORS["accent"],''.join(circle(x+a,y+b,2.5) for a,b in [(9,-13),(16,-5),(14,8),(6,15)]))
    if contact:
        d.add("receptor","Engineered CAR and target-contact cue",COLORS["blue"],path('M64 51H73M69 45V57M64 64H73M69 58V70M64 77H73M69 71V83'),stroke=True,width=3)
        d.add("receptor","Engineered CAR and target-contact cue",COLORS["blue"],''.join(rect(75,y-3,6,6,1) for y in [51,64,77]))
    else:
        for x0,y0,dx,dy in [(61,33,0,-12),(84,43,8,-9),(95,67,13,0),(38,43,-8,-9)]:
            x1,y1=x0+dx,y0+dy
            d.add("receptor","Engineered CAR and target-contact cue",COLORS["blue"],line(x0,y0,x1,y1)+path(f'M{x1-4} {y1-4}L{x1} {y1}L{x1+4} {y1-4}'),stroke=True,width=3)
    return d

def synapse(d,close=False):
    if not close:
        d.shape("immune_cell","Immune-cell cytoplasm",COLORS["body"],path('M55 27C21 14 10 44 16 68C20 94 36 109 56 96Q48 65 55 27Z'))
        d.shape("partner_cell","Partner-cell cytoplasm",COLORS["blue"],path('M74 27C108 14 119 44 113 68C109 94 93 109 73 96Q81 65 74 27Z'))
        d.shape("nucleus","Nuclei",COLORS["nucleus"],ellipse(33,60,11,14)+ellipse(96,66,11,14),2)
        ys=[43,57,71,85];left,right=53,75
    else:
        d.shape("immune_cell","Immune-cell cytoplasm",COLORS["body"],rect(16,20,33,87,7))
        d.shape("partner_cell","Partner-cell cytoplasm",COLORS["blue"],rect(81,20,31,87,7))
        d.shape("nucleus","Nuclei",COLORS["nucleus"],ellipse(29,67,7,14)+ellipse(100,67,7,14),2)
        ys=[36,55,74,93];left,right=49,81
    center=(left+right)/2
    d.add("contacts","Receptor–ligand contact cues",COLORS["accent"],''.join(line(left,y,center-2,y)+path(f'M{center-2} {y-4}V{y+4}')+line(center+4,y,right,y)+circle(center+2,y,3) for y in ys),stroke=True,width=2.8)
    return d

def dc_uptake(d,particulate=False):
    geom=path('M20 43L35 45L31 24L49 41L65 30L68 48L87 43L80 59L94 74L76 80L79 102L60 88L45 105L42 85L20 90L28 72L14 62L30 57Z')
    d.shape("cell_body","Dendritic-cell cytoplasm",COLORS["body"],geom)
    d.shape("nucleus","Dendritic-cell nucleus",COLORS["nucleus"],ellipse(45,65,11,14),2)
    if particulate:
        d.shape("uptake_compartment","Antigen-containing uptake compartment",COLORS["pale"],circle(67,66,11),2)
        d.shape("antigen","Particulate antigen",COLORS["accent"],path('M99 27L108 31L105 41L95 38Z')+path('M63 61L71 63L69 71L62 69Z'),1.8)
    else:
        d.shape("uptake_compartment","Antigen-containing uptake compartment",COLORS["pale"],circle(67,66,11),2)
        d.add("antigen","Soluble antigen",COLORS["accent"],''.join(circle(x,y,2.6) for x,y in [(98,27),(109,36),(95,45),(102,55),(65,63),(71,68),(64,71)]))
    d.arrow(100,63,84,65)
    return d

def macrophage(d,multiple=False):
    geom=path('M35 45Q39 32 52 39Q67 24 79 40Q99 41 91 61Q105 77 87 89Q74 105 57 94Q38 101 31 83Q17 69 30 56Z')
    d.shape("cell_body","Macrophage cytoplasm",COLORS["body"],geom)
    d.shape("nucleus","Macrophage nucleus",COLORS["nucleus"],path('M50 54Q34 68 49 80Q60 88 68 77Q51 76 59 62Q63 51 50 54Z'),2)
    d.add("cue_a","One class of environmental cue",COLORS["accent"],circle(18,25,4)+circle(34,15,3)+circle(14,40,3))
    d.arrow(24,31,37,44,role="cue_a",label="One class of environmental cue",color=COLORS["accent"])
    if multiple:
        d.add("cue_b","Additional environmental cues",COLORS["blue"],rect(92,17,7,7,1)+rect(106,32,6,6,1)+rect(103,95,7,7,1))
        d.arrow(98,39,86,48,role="cue_b",label="Additional environmental cues",color=COLORS["blue"])
        d.arrow(101,90,91,83,role="cue_b",label="Additional environmental cues",color=COLORS["blue"])
    else:
        d.add("cue_b","Response continuum cue",COLORS["blue"],path('M39 112H86'),stroke=True,width=4)
        d.add("cue_b","Response continuum cue",COLORS["blue"],circle(63,112,4))
    return d

def tls(d,mature=False):
    d.shape("stroma","Lymphoid tissue context",COLORS["pale"],path('M18 40Q25 17 53 22Q84 11 106 34Q122 60 105 89Q88 113 57 106Q28 114 17 88Q7 61 18 40Z'),2.5)
    d.shape("b_zone","B-cell follicle",COLORS["blue"],ellipse(48,58,23,28),2)
    d.shape("t_zone","T-cell zone",COLORS["body"],path('M73 30Q104 33 106 60Q107 86 78 98L66 84Q80 62 68 43Z'),2)
    if mature:
        d.shape("follicle_center","Schematic germinal center",COLORS["nucleus"],ellipse(47,56,12,17),1.5)
        d.text(47,59,"GC",9)
    else:
        d.add("follicle_center","Follicular B cells",COLORS["nucleus"],''.join(circle(x,y,3) for x,y in [(39,48),(52,45),(36,62),(50,61),(44,75),(59,71)]))
    d.add("t_zone","T-cell zone",COLORS["body"],''.join(circle(x,y,3.5) for x,y in [(87,45),(96,57),(86,68),(94,79),(81,85)]))
    d.outline(''.join(circle(x,y,3.5) for x,y in [(87,45),(96,57),(86,68),(94,79),(81,85)]),1.4)
    d.text(44,119,"B",10);d.text(89,119,"T",10)
    return d

def gradient(d,kind,radial=False):
    label={"hypoxia":"O2","drug":"Drug","lactate":"Lactate"}[kind]
    color={"hypoxia":COLORS["blue"],"drug":COLORS["purple"],"lactate":COLORS["orange"]}[kind]
    def markers(points):
        if kind=='hypoxia':return ''.join(circle(x-1.6,y,1.9)+circle(x+1.6,y,1.9) for x,y in points)
        if kind=='drug':return ''.join(path(f'M{x} {y-3.2}L{x+3.2} {y}L{x} {y+3.2}L{x-3.2} {y}Z') for x,y in points)
        return ''.join(circle(x,y,2.8) for x,y in points)
    if radial:
        d.shape("tissue","Tissue or spheroid section",COLORS["pale"],circle(64,62,42),2.5)
        d.outline(circle(64,62,27)+circle(64,62,13),1.3,dash="3 4")
        if kind=="lactate":
            d.shape("source","Metabolite-producing cell",COLORS["body"],circle(64,62,10),1.8)
            dots=[(49,48),(68,44),(79,53),(79,70),(65,81),(48,73),(35,53),(86,38),(93,73)]
            d.arrow(76,61,100,61)
        else:
            d.add("source","External supply",COLORS["body"],path('M17 27Q64 1 111 27'),stroke=True,width=5)
            dots=[(35,40),(48,27),(69,23),(91,34),(102,55),(98,79),(80,98),(57,101),(35,89),(24,65),(49,49),(80,62)]
            d.arrow(64,12,64,33)
        d.add("molecule",label+" availability cue",color,markers(dots))
        d.text(64,119,label+(' high at source' if kind=="lactate" else ' rim > core'),8)
    else:
        d.shape("tissue","Tissue section",COLORS["pale"],rect(29,29,82,67,6),2.2)
        if kind=="lactate":
            d.shape("source","Metabolite-producing cell",COLORS["body"],ellipse(97,64,12,20),2)
            dots=[(83,43),(84,57),(82,70),(81,85),(70,48),(70,70),(69,86),(58,57),(54,78),(43,66)]
            d.arrow(91,104,34,104)
            d.text(69,119,label+': source high',8)
        else:
            d.shape("source","Perfused vessel supply",COLORS["body"],rect(13,24,13,77,6),2)
            dots=[(36,40),(37,56),(36,72),(37,86),(48,45),(50,64),(49,83),(65,50),(64,76),(82,65)]
            d.arrow(32,104,104,104)
            d.text(69,119,label+' high → low',8)
        d.add("molecule",label+" availability cue",color,markers(dots))
    return d


def axes(d,xlabel="X",ylabel="Y"):
    d.outline(path('M25 20V99H112'),2)
    d.text(69,117,xlabel,8)
    d.text(10,61,ylabel,8,rotate=-90)

def dots(d,coords,role="series_a",label="Example points — series A",color=COLORS["blue"],r=2.3):
    d.add(role,label,color,''.join(circle(x,y,r) for x,y in coords))

def umap(d,continuous=False):
    axes(d,"UMAP 1","UMAP 2")
    if continuous:
        groups=[[(33,78),(36,70),(40,79),(42,66),(45,72),(47,61)],[(51,66),(54,59),(56,51),(58,60),(62,54),(65,48)],[(71,46),(75,39),(80,45),(84,32),(89,39),(96,31)]]
        for role,label,color,coords in zip(['state_a','state_b','state_c'],['Example early state','Example intermediate state','Example later state'],[COLORS['blue'],COLORS['teal'],COLORS['accent']],groups):dots(d,coords,role,label,color)
    else:
        for role,label,color,coords in [('state_a','Example cluster A',COLORS['blue'],[(35,34),(41,30),(47,36),(39,41),(48,45),(31,44),(37,50),(46,53)]),('state_b','Example cluster B',COLORS['teal'],[(79,35),(87,30),(96,34),(88,42),(103,43),(95,49),(80,47)]),('state_c','Example cluster C',COLORS['accent'],[(57,75),(65,70),(73,77),(60,84),(71,89),(81,83),(53,89)])]:dots(d,coords,role,label,color)
    d.text(103,17,"Example",7,anchor="end");return d

def volcano(d,annotated=False):
    axes(d,"log2 fold change","−log10(q)")
    d.outline(path('M42 23V98M88 23V98M26 69H111'),1.1,dash="3 4")
    dots(d,[(29,29),(34,38),(37,48),(31,57),(39,61),(39,37)],"lower","Example negative fold changes",COLORS['blue'])
    dots(d,[(93,53),(99,34),(106,25),(97,60),(104,46),(91,38)],"higher","Example positive fold changes",COLORS['orange'])
    dots(d,[(47,81),(52,87),(59,78),(63,89),(69,84),(76,81),(82,88),(65,75),(40,84),(91,86)],"neutral","Example other tested features",COLORS['teal'])
    if annotated:
        d.text(40,18,'A',8);d.outline(path('M37 21L31 27'),1.1)
        d.text(105,17,'B',8);d.outline(path('M105 19L106 23'),1.1)
    else:d.text(106,17,'Example',7,anchor='end')
    return d

def heatmap(d,clustered=False):
    x0,y0,w,h=(37,34,10,10) if clustered else (29,24,12,12)
    values=[[-1,-1,0,1,1,0],[-1,0,-1,1,1,1],[0,-1,0,1,0,1],[1,1,0,-1,-1,0],[1,0,1,-1,0,-1],[0,1,1,0,-1,-1]]
    for value,role,label,color in [(-1,'low','Lower example value',COLORS['blue']),(0,'mid','Middle example value',COLORS['pale']),(1,'high','Higher example value',COLORS['orange'])]:
        d.add(role,label,color,''.join(rect(x0+c*w,y0+r*h,w,h) for r,row in enumerate(values) for c,v in enumerate(row) if v==value))
    d.outline(rect(x0,y0,6*w,6*h),1.1)
    d.text(x0+3*w,10 if clustered else y0-7,'Samples',8)
    d.text(13,y0+3*h,'Features',8,rotate=-90)
    if clustered:d.outline(path('M42 32V26H52V32M47 26V21H67V26M62 32V26H72V32M82 32V24H92V32M67 21V17H87V24'),1.2)
    key_y=108
    for i,(role,label,color) in enumerate([('low','Lower example value',COLORS['blue']),('mid','Middle example value',COLORS['pale']),('high','Higher example value',COLORS['orange'])]):d.add(role,label,color,rect(45+i*13,key_y,13,5))
    d.text(40,113,'−',8);d.text(88,113,'+',8);d.text(65,123,'Relative value',8)
    return d

def km(d,two=False):
    axes(d,'Time','Survival')
    d.text(20,25,'1',7,anchor='end');d.text(20,101,'0',7,anchor='end')
    d.add('curve_a','Example survival curve A',COLORS['blue'],path('M26 25H43V34H57V43H73V54H88V62H109'),stroke=True,width=2.7)
    d.add('censor_a','Example censor marks A',COLORS['blue'],path('M34 22V28M64 40V46M97 59V65'),stroke=True,width=1.6)
    if two:
        d.add('curve_b','Example survival curve B',COLORS['orange'],path('M26 25H36V42H50V61H66V72H82V83H108'),stroke=True,width=2.7)
        d.add('censor_b','Example censor marks B',COLORS['orange'],path('M42 39V45M74 69V75M100 80V86'),stroke=True,width=1.6)
    d.text(110,17,'Example',7,anchor='end');return d

def violin(d,split=False):
    axes(d,'Group','Value')
    if split:
        d.shape('distribution_a','Example distribution A',COLORS['blue'],path('M68 26C65 36 53 43 51 54C48 66 59 73 68 90Z'),1.4)
        d.shape('distribution_b','Example distribution B',COLORS['orange'],path('M68 26C76 40 74 46 81 57C89 69 79 81 68 90Z'),1.4)
        d.outline(path('M68 26V90M62 61H74'),1.5);d.text(68,108,'A | B',8)
    else:
        for x,role,label,color,p in [(49,'distribution_a','Example distribution A',COLORS['blue'],'M49 28C44 39 35 42 37 56C38 69 47 78 49 91C51 78 60 69 61 56C63 42 54 39 49 28Z'),(88,'distribution_b','Example distribution B',COLORS['orange'],'M88 32C85 45 75 58 75 70C75 82 85 85 88 92C91 85 101 82 101 70C101 58 91 45 88 32Z')]:
            d.shape(role,label,color,path(p),1.4)
        d.outline(path('M44 57H54M83 72H93'),2)
        d.text(49,108,'A',8);d.text(88,108,'B',8)
    d.text(111,17,'Example',7,anchor='end');return d

def boxplot(d,horizontal=False):
    axes(d,'Value' if horizontal else 'Group','Group' if horizontal else 'Value')
    if horizontal:
        for y,role,label,color,l,q1,m,q3,r in [(44,'box_a','Example summary A',COLORS['blue'],36,48,60,71,93),(77,'box_b','Example summary B',COLORS['orange'],39,63,75,87,101)]:
            d.outline(path(f'M{l} {y}H{r}M{l} {y-4}V{y+4}M{r} {y-4}V{y+4}'),1.4)
            d.shape(role,label,color,rect(q1,y-8,q3-q1,16),1.6);d.outline(line(m,y-8,m,y+8),2)
        d.text(21,47,'A',8,anchor='end');d.text(21,80,'B',8,anchor='end')
    else:
        for x,role,label,color,top,q3,m,q1,bottom in [(49,'box_a','Example summary A',COLORS['blue'],30,43,55,66,84),(88,'box_b','Example summary B',COLORS['orange'],36,56,68,81,92)]:
            d.outline(path(f'M{x} {top}V{bottom}M{x-5} {top}H{x+5}M{x-5} {bottom}H{x+5}'),1.4)
            d.shape(role,label,color,rect(x-8,q3,16,q1-q3),1.6);d.outline(line(x-8,m,x+8,m),2)
        d.text(49,108,'A',8);d.text(88,108,'B',8)
    d.text(110,17,'Example',7,anchor='end');return d

def scatter(d,two=False):
    axes(d,'X','Y')
    dots(d,[(35,82),(41,70),(49,78),(56,57),(62,66),(71,43),(79,52),(87,32),(98,42)],'series_a','Example series A',COLORS['blue'],2.8)
    if two:dots(d,[(37,44),(47,40),(54,51),(64,59),(73,62),(82,69),(91,79),(105,84)],'series_b','Example series B',COLORS['orange'],2.8)
    else:d.add('trend','Illustrative trend guide',COLORS['teal'],path('M31 89L104 30'),stroke=True,width=1.6,dash='4 4')
    d.text(109,17,'Example',7,anchor='end');return d

def network(d,modular=False):
    if modular:
        nodes=[(28,32),(50,26),(39,52),(20,65),(66,66),(96,36),(108,62),(88,89),(60,101)]
        edges=[(0,1),(0,2),(1,2),(2,3),(2,4),(4,5),(4,6),(4,7),(5,6),(6,7),(7,8),(4,8)]
        groups=[nodes[:4],nodes[4:]]
    else:
        nodes=[(64,64),(31,30),(69,19),(103,37),(111,76),(86,105),(43,109),(17,76)]
        edges=[(0,i) for i in range(1,8)]+[(1,2),(3,4),(5,6)]
        groups=[[nodes[0]],nodes[1:]]
    d.add('edges','Undirected example associations',COLORS['teal'],''.join(line(*nodes[a],*nodes[b]) for a,b in edges),stroke=True,width=2.2)
    for role,label,color,pts in [('nodes_a','Example node group A',COLORS['blue'],groups[0]),('nodes_b','Example node group B',COLORS['accent'],groups[1])]:d.shape(role,label,color,''.join(circle(x,y,6) for x,y in pts),1.6)
    d.text(65,123,'Associations · example',7);return d

def pseudotime(d,branch=False):
    axes(d,'Component 1','Component 2')
    if branch:
        early=[(34,83),(40,76),(45,80),(49,71),(54,66)]
        mid=[(61,60),(67,55),(72,47),(78,41),(86,34)]
        late=[(70,65),(80,68),(88,73),(97,79),(104,83)]
        trace='M32 84Q51 78 64 59Q77 44 93 30M64 59Q85 72 107 86'
    else:
        early=[(33,83),(38,76),(44,81),(48,69),(54,70)]
        mid=[(59,63),(62,55),(68,60),(74,48),(79,51)]
        late=[(84,41),(91,44),(94,32),(101,35),(106,26)]
        trace='M32 86Q64 62 108 25'
    d.outline(path(trace),1.5)
    for role,label,color,pts in [('state_a','Example earlier ordering',COLORS['blue'],early),('state_b','Example middle ordering',COLORS['teal'],mid),('state_c','Example later ordering',COLORS['accent'],late)]:dots(d,pts,role,label,color,3)
    d.text(110,17,'Pseudotime',7,anchor='end');return d

def tracking(d,two=False):
    axes(d,'Position X','Position Y')
    a=[(34,86),(47,76),(45,61),(62,54),(69,37),(89,32),(104,24)]
    d.add('track_a','Example tracked cell A',COLORS['blue'],path('M34 86L47 76L45 61L62 54L69 37L89 32L104 24'),stroke=True,width=2)
    dots(d,a,'track_a','Example tracked cell A',COLORS['blue'],3)
    d.arrow(89,32,104,24,role='track_a',label='Example tracked cell A',color=COLORS['blue'])
    if two:
        b=[(34,41),(49,45),(60,70),(75,64),(91,77),(105,85)]
        d.add('track_b','Example tracked cell B',COLORS['orange'],path('M34 41L49 45L60 70L75 64L91 77L105 85'),stroke=True,width=2)
        dots(d,b,'track_b','Example tracked cell B',COLORS['orange'],3)
        d.arrow(91,77,105,85,role='track_b',label='Example tracked cell B',color=COLORS['orange'])
    else:
        d.add('time_cue','Later positions',COLORS['accent'],circle(104,24,5),stroke=True,width=1.6)
        d.text(34,77,'t0',7);d.text(114,39,'tN',7)
    d.text(30,16,'Example',7,anchor='start');return d


def row(key,name,category,description,limits,aliases,refs,forms,renderer):
    return dict(key=key,name=name,category=category,description=description,limits=limits,aliases=aliases,refs=refs,forms=forms,renderer=renderer)


TME = [
 row('cancer_associated_fibroblast','Cancer-associated Fibroblast','cell','A fibroblast in tumor-associated context, shown alone or with surrounding extracellular matrix.', 'CAF populations are heterogeneous. Shape, fibers and matrix do not identify a CAF subtype or a universal marker; add model-specific labels and evidence.', ['CAF','tumor fibroblast','cancer stromal fibroblast'],['elyada-2019'], [('spindle','Spindle cell'),('matrix','Matrix context')],lambda d,i:spindle(d,bool(i))),
 row('tumor_associated_neutrophil','Tumor-associated Neutrophil','cell','A lobulated granulocyte shown alone or apposed to tumor-cell context.', 'Tumor association and neutrophil functions require biological evidence. Granule color and lobulation do not classify suppressive, antitumor or other neutrophil states.', ['TAN','tumor neutrophil','neutrophil tumor context'],['zilionis-2019'],[('isolated','Isolated cell'),('tumor_contact','Tumor context')],lambda d,i:neutrophil(d,bool(i))),
 row('car_nk_cell','CAR-NK Cell','cell','An NK-cell schematic with engineered surface-receptor cues, optionally contacting a target.', 'CAR geometry, antigen specificity, signaling domains and receptor number are illustrative. Contact does not imply killing, response rate or a particular clinical construct.', ['chimeric antigen receptor natural killer cell','engineered NK cell'],['liu-2020'],[('receptor_display','Receptor display'),('target_contact','Target contact')],lambda d,i:car_nk(d,bool(i))),
 row('generic_immune_synapse','Immune Synapse — Generic','membrane-signaling','Two apposed cell membranes with clustered receptor–ligand contact cues, in whole-cell or interface views.', 'A generic cell-contact diagram. Receptor identity, spatial pattern and downstream response are unspecified; not every synapse forms a stable concentric bull’s-eye.', ['generic immunological synapse','immune cell contact interface'],['grakoui-1999'],[('cell_pair','Cell pair'),('interface','Interface close-up')],lambda d,i:synapse(d,bool(i))),
 row('dendritic_antigen_uptake','Dendritic Cell Antigen Uptake','assay-workflow','A dendritic-cell outline with extracellular antigen and an intracellular uptake compartment.', 'Soluble and particulate forms are schematic uptake arrangements, not measurements of efficiency. Uptake does not establish processing, peptide presentation or T-cell activation.', ['DC antigen uptake','dendritic endocytosis','antigen capture'],['sallusto-1995'],[('soluble','Soluble antigen'),('particulate','Particulate antigen')],lambda d,i:dc_uptake(d,bool(i))),
 row('macrophage_polarization_cue','Macrophage Polarization Cue','membrane-signaling','Incoming environmental signals around a macrophage, with one-cue and multiple-cue arrangements.', 'Macrophage activation is context-dependent and multidimensional. The response cue is not a universal M1/M2 binary, a measured state transition or evidence of a fixed lineage.', ['macrophage activation cue','macrophage state spectrum','polarizing signals'],['xue-2014'],[('single_cue','One cue and response range'),('multiple_cues','Multiple environmental cues')],lambda d,i:macrophage(d,bool(i))),
 row('tertiary_lymphoid_structure','Tertiary Lymphoid Structure','model-system','Organized lymphoid tissue with a B-cell follicle and adjacent T-cell zone, with or without a schematic germinal center.', 'TLS organization and maturity vary with tissue and disease. B/T zones and a germinal-center cue are illustrative; no diagnosis, measured cell fraction or favorable outcome is implied.', ['TLS','ectopic lymphoid structure','tertiary lymphoid tissue'],['cabrita-2020','tls-histology-2021'],[('primary_follicle','B/T organization'),('germinal_center','With germinal-center cue')],lambda d,i:tls(d,bool(i))),
 row('hypoxia_gradient','Hypoxia Gradient','model-system','Qualitative oxygen availability decreases with distance from a vessel or toward a spheroid core.', 'Dots indicate relative oxygen availability only. Hypoxia severity, consumption, length scale and concentration are not measured; real gradients depend on perfusion, diffusion and cellular demand.', ['oxygen gradient','O2 gradient','tumor hypoxia gradient'],['anandi-2024','sonveaux-2008'],[('perivascular','Vessel-to-tissue'),('spheroid','Spheroid section')],lambda d,i:gradient(d,'hypoxia',bool(i))),
 row('drug_penetration_gradient','Drug Penetration Gradient','model-system','Qualitative drug availability decreases away from vascular supply or from an exposed spheroid rim.', 'No dose, transport rate, penetration depth or efficacy is encoded. Actual distributions depend on compound, binding, metabolism, exposure time and tissue; limited penetration is not equivalent to cellular resistance.', ['drug diffusion gradient','compound penetration','drug distribution'],['anandi-2024'],[('perivascular','Vessel-to-tissue'),('spheroid','Spheroid penetration')],lambda d,i:gradient(d,'drug',bool(i))),
 row('lactate_metabolite_gradient','Lactate / Metabolite Gradient','model-system','A producing-cell source and qualitative decrease of metabolite availability away from that source.', 'The illustrated source direction is explicit and differs from oxygen delivery. Lactate production, uptake, clearance and pH vary; no concentration, flux, acidity or universal metabolic symbiosis is asserted.', ['lactate gradient','metabolite gradient','metabolic spatial gradient'],['sonveaux-2008','anandi-2024'],[('source_to_tissue','Source-to-tissue'),('radial_source','Local radial source')],lambda d,i:gradient(d,'lactate',bool(i))),
]

SCHEMATIC = ('Illustrative editable template with invented positions, not measured data or an analysis result. '
             'Replace marks and labels with verified study-specific content before presenting results. ')
ANALYSIS = [
 row('umap_scatter','UMAP Scatter','assay-workflow','Editable UMAP-style examples with separated clusters or a continuous color ordering.', SCHEMATIC+'UMAP axis values and apparent distances have no measured meaning here. Colors do not establish cell identities or lineage.', ['UMAP embedding','uniform manifold approximation projection'],['mcinnes-2018','elyada-2019'],[('clusters','Separated clusters'),('continuum','Continuous state example')],lambda d,i:umap(d,bool(i))),
 row('volcano_plot','Volcano Plot','assay-workflow','Editable example points on log2 fold-change and −log10(q) axes, with schematic threshold guides.', SCHEMATIC+'q denotes an adjusted statistical value in this example. Dashed cutoffs are placeholders, not a specified significance threshold; A/B labels are generic features.', ['differential expression volcano','log fold change plot'],['omicsvolcano-2021'],[('overview','Threshold overview'),('feature_labels','Example feature labels')],lambda d,i:volcano(d,bool(i))),
 row('heatmap','Heatmap','assay-workflow','Editable relative-value matrix with a labeled diverging key, optionally with a schematic column dendrogram.', SCHEMATIC+'Features, sample values, scaling and clustering are unspecified. Colors are symbolic relative values; dendrogram branches have no inferred distance.', ['expression heatmap','clustered matrix'],['zilionis-2019','trapnell-2014'],[('matrix','Value matrix'),('clustered','Column clustering cue')],lambda d,i:heatmap(d,bool(i))),
 row('kaplan_meier_curve','Kaplan–Meier Curve','assay-workflow','Editable nonincreasing step curves with censor marks, for one or two illustrative groups.', SCHEMATIC+'No cohort, event count, at-risk table, follow-up duration, uncertainty or hazard ratio is supplied. Example censor marks are not event drops.', ['KM survival curve','survival probability curve'],['kaplan-meier-1958'],[('one_group','Single group'),('two_groups','Two groups')],lambda d,i:km(d,bool(i))),
 row('violin_plot','Violin Plot','assay-workflow','Editable symmetric distributions or a split violin, with a horizontal summary guide.', SCHEMATIC+'Widths are hand-authored schematic density envelopes. The horizontal mark is a placeholder summary, not a calculated median or statistical comparison; no sample sizes are implied.', ['violin density','split violin distribution'],['elyada-2019'],[('paired','Separate groups'),('split','Split distribution')],lambda d,i:violin(d,bool(i))),
 row('box_plot','Box Plot','assay-workflow','Editable vertical or horizontal box-and-whisker examples with central median lines.', SCHEMATIC+'Boxes stand for the middle quartiles and central lines for medians; whisker rules, sample sizes, outliers and numerical summaries are unspecified.', ['box and whisker plot','boxplot'],['elyada-2019'],[('vertical','Vertical groups'),('horizontal','Horizontal groups')],lambda d,i:boxplot(d,bool(i))),
 row('scatter_plot','Scatter Plot','assay-workflow','Editable point clouds for one series with a guide or two distinct series.', SCHEMATIC+'Axes lack numerical units. Any dashed trend is a hand-authored guide, not a fitted model, correlation estimate, confidence interval or causal relationship.', ['XY scatter','bivariate point plot'],['anandi-2024'],[('single_series','Single series with guide'),('two_series','Two series')],lambda d,i:scatter(d,bool(i))),
 row('network_graph','Network Graph','assay-workflow','Editable nodes joined by undirected edges, in hub or modular arrangements.', SCHEMATIC+'Edges represent unspecified associations only; no causality, regulation, direction, measured strength, enrichment or graph inference is asserted.', ['association network','node edge graph','interaction network schematic'],['xue-2014'],[('hub','Hub arrangement'),('modular','Modular arrangement')],lambda d,i:network(d,bool(i))),
 row('pseudotime_trajectory','Pseudotime Trajectory','assay-workflow','Editable cell-state points along a continuous or branching ordering.', SCHEMATIC+'Pseudotime is an inferred ordering, not elapsed time or lineage tracing. No root, branch assignment, trajectory method or actual fate transition is inferred by this artwork.', ['cell state trajectory','inferred developmental ordering'],['trapnell-2014'],[('linear','Continuous ordering'),('branching','Branching ordering')],lambda d,i:pseudotime(d,bool(i))),
 row('cell_tracking_trajectory','Cell Tracking Trajectory','assay-workflow','Editable spatial tracks with ordered positions and endpoint labels or direction arrows for one or two example cells.', SCHEMATIC+'Endpoint labels or arrows indicate time order of positions, unlike pseudotime. No speed, elapsed duration, migration bias, physical scale or lineage is encoded.', ['cell migration track','time lapse trajectory','single cell path'],['tinevez-2017'],[('single_track','Single cell'),('two_tracks','Two cells')],lambda d,i:tracking(d,bool(i))),
]


def generate(pack_id, rows, destination_root, *, render_only=False):
    prefix='tme' if pack_id=='tumor-microenvironment' else 'analysis'
    title='Tumor Microenvironment' if prefix=='tme' else 'Analysis Graphics'
    destination=Path(destination_root)/pack_id
    existing=destination/'asset-pack.json'
    if existing.is_file():
        current=json.loads(existing.read_text(encoding='utf8'))
        if current.get('release_audit',{}).get('status')!='draft_review_pending':
            raise ValueError('Refusing to overwrite reviewed rights or qualification records; reproduce with --destination-root in ignored QA output instead.')
    (destination/'svg').mkdir(parents=True,exist_ok=True)
    source_id=f'source.{pack_id}.{DATE}'
    rights_id=f'rights.{pack_id}.pending.{DATE}'
    assets=[]
    for row_ in rows:
        for i,(form,label) in enumerate(row_['forms']):
            d=row_['renderer'](Drawing(),i)
            name=row_['name']+' — '+label
            key=row_['key']+'_'+form
            category=row_['category']; concept=prefix+'.'+row_['key']
            asset={'id':concept+'.'+form,'concept_id':concept,'name':name,
                'scientific_name':row_['name']+' — '+label,'synonyms':row_['aliases'],
                'category':category,'subcategory':'Tumor cells, contacts and spatial gradients' if prefix=='tme' else 'Analytical graphics · schematic templates',
                'tags':[row_['name'],label,*row_['aliases'],'editable vector','schematic']+(['example','template','not measured data'] if prefix=='analysis' else ['tumor microenvironment']),
                'description':row_['description'],'scientific_limitations':row_['limits'],
                'scientific_references':[REF[r] for r in row_['refs']],
                'file':'svg/'+key+'.svg','source_type':'clean_room_original_vector',
                'license':'FS-ORIGINAL-DRAFT','provenance':ORIGINAL,
                'source_record_id':source_id,'rights_record_id':rights_id,
                'style_family':'figure-studio-soft-line-v1','style_variant':'standard',
                'variant_axis':'form','form_id':form,'form_label':label,
                'review_status':'independent_scientific_and_visual_review_pending',
                'style_status':'soft_line_v1_original_draft','mvp_quality':'original_draft','quality_tier':'draft',
                'reviewer_notes':'Original vectors self-reviewed at thumbnail and enlarged sizes; independent scientific, visual, editing and rights review remain pending. No review outcome is inherited from another pack.',
                'editable_region_count':len(d.regions),'editable_color_regions':list(d.regions.values()),
                'connector_hints':[{'id':x,'label':x.capitalize()+' attachment','role':'attachment','x':a,'y':b} for x,a,b in [('left',.08,.5),('right',.92,.5),('top',.5,.08),('bottom',.5,.92)]]}
            svg_name=name;svg_description=row_['description']+' '+row_['limits']
            if render_only and existing.is_file():
                retained=next((a for a in current.get('assets',[]) if a['id']==asset['id']),None)
                if retained:
                    svg_name=retained['name'];svg_description=retained['description']+' '+retained['scientific_limitations']
            (destination/asset['file']).write_text(d.svg(svg_name,svg_description),encoding='utf8',newline='\n')
            assets.append(asset)
    if render_only:
        return {'id':pack_id,'asset_count':len(assets),'concept_count':len(rows),'assets':assets,'render_only':True}
    counts=Counter(a['category'] for a in assets)
    refs=sorted({r for row_ in rows for r in row_['refs']})
    pack={'schema_version':'0.3.0','id':pack_id,'version':'0.1.0','name':title,
        'description':('Original editable tumor-associated cells, immune contacts, organized lymphoid tissue and qualitative spatial gradients.' if prefix=='tme' else 'Editable schematic plot templates. Example geometry only; no measured data, computed statistics or analysis functions.'),
        'style_family':'figure-studio-soft-line-v1','style_families':['figure-studio-soft-line-v1'],
        'qa_status':'independent_scientific_and_visual_review_pending',
        'generated_by':{'script':'scripts/seed-tumor-analysis-assets.py','generated_on':DATE,'deterministic':True},
        'concept_count':len(rows),'asset_count':len(assets),
        'category_counts':{c:{'concept_count':len({a['concept_id'] for a in assets if a['category']==c}),'style_count':n} for c,n in counts.items()},
        'release_audit':{'file':'rights-release-record.json','audit_id':pack_id+'.draft.'+DATE,'audit_date':DATE,'release_effective_date':None,'status':'draft_review_pending','concept_count':len(rows),'asset_count':len(assets),'public_distribution_authorized':False,'selected_public_license':None,'license_notice':'LICENSE-ASSETS-PENDING.md'},
        'style_tokens':{'viewBox':'0 0 128 128','target_padding_units':'10-16; axis labels can reach 5 units','primary_outline':OUTLINE,'primary_outline_width':2.8,'detail_outline_width':1.5,'line_cap':'round','line_join':'round'},
        'source_policy':{'allowed_sources':['original vector geometry','primary-literature scientific conventions without copied artwork'],'disallowed_sources':['tracing or copying scientific/proprietary artwork','third-party components','measured values presented as new results']},
        'license_definitions':{'FS-ORIGINAL-DRAFT':{'label':'Original scientific drawing pending release review','reuse':'Internal review pending exact contribution and public-release binding.','proposed_distribution_license':'CC0-1.0 under the repository original-art policy, pending contribution binding','rights_status':'original_output_pending_owner_review','release_status':'draft_review_pending','attribution_required':False}},
        'source_records':[{'id':source_id,'kind':'clean_room_generation_record','pack_id':pack_id,'scope':'all_assets_in_pack','created_on':DATE,'generated_by':'Superbench Figure Tool AI-assisted original SVG authoring, deterministic script','third_party_material':'none_declared','statement':ORIGINAL,'scientific_references':[REF[r] for r in refs]}],
        'rights_records':[{'id':rights_id,'kind':'draft_rights_review','pack_id':pack_id,'scope':'all_assets_in_pack','status':'draft_review_pending','public_distribution_authorized':False,'selected_public_license':None,'rights_basis':'original_output_pending_owner_review','third_party_material':'none_declared','effective_date':None,'statement':'These newly authored original vector drawings are pending exact contribution and public-release binding under the repository policy. This record does not copy or extend an older pack’s owner grant.','qualification':'Scientific, visual, native editor and public-release decisions remain separate from an original-art source declaration. No independent acceptance is claimed here.'}],
        'assets':assets}
    (destination/'asset-pack.json').write_text(json.dumps(pack,indent=2,ensure_ascii=False)+'\n',encoding='utf8',newline='\n')
    (destination/'LICENSE-ASSETS-PENDING.md').write_text('# Original artwork pending release binding\n\nThese original SVG drawings were authored on 2026-10-15. The proposed license is CC0-1.0 under the repository original-art policy. Exact contribution, scientific, visual, native editing and public-release records are pending. No older owner authorization has been copied or backdated. Primary papers informed concepts only; no source artwork or measured data is redistributed.\n',encoding='utf8',newline='\n')
    (destination/'rights-release-record.json').write_text(json.dumps({'schema_id':'figureStudio.scientificAssetDraftReview.v1','pack_id':pack_id,'status':'draft_review_pending','created_on':DATE,'asset_count':len(assets),'concept_count':len(rows),'public_distribution_authorized':False,'selected_public_license':None,'source_record_id':source_id,'rights_record_id':rights_id,'scope':'Exact newly authored SVGs and catalog; public-release binding and independent review pending.'},indent=2)+'\n',encoding='utf8',newline='\n')
    return pack


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--destination-root',type=Path,default=ROOT/'assets/scientific-packs')
    p.add_argument('--render-only',action='store_true',help='Write SVGs only; preserve draft catalog/rights/audit records. Reviewed packs still require a fresh destination.')
    args=p.parse_args()
    for pack_id,rows in [('tumor-microenvironment',TME),('analysis-graphics',ANALYSIS)]:
        pack=generate(pack_id,rows,args.destination_root,render_only=args.render_only)
        print(f'{pack_id}: {pack["asset_count"]} drawings / {pack["concept_count"]} concepts; review pending')
