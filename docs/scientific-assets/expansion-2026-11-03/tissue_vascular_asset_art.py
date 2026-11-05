"""Original, editable tissue/vascular vector drafts. Generic schematics; not histology or to scale."""
from xml.sax.saxutils import escape
import math
REFERENCES = [
 {"id":"akhtar2013","citation":"Akhtar N, Streuli CH. An integrin–ILK–microtubule network orients cell polarity and lumen formation in glandular epithelium. Nat Cell Biol. 2013;15:17–27.","doi":"10.1038/ncb2646","url":"https://doi.org/10.1038/ncb2646","figure":"Figs. 1, 8","design_decision":"Informed generic apical/basal polarity and hollow epithelial lumen; no organ identity or pathway is encoded."},
 {"id":"karkkainen2004","citation":"Karkkainen MJ et al. Vascular endothelial growth factor C is required for sprouting of the first lymphatic vessels from embryonic veins. Nat Immunol. 2004;5:74–80.","doi":"10.1038/ni1013","url":"https://doi.org/10.1038/ni1013","figure":"Fig. 1","design_decision":"Informed endothelial sprout and lymphatic channel motifs, without molecular cues or developmental-origin claims."},
 {"id":"divoux2019","citation":"Divoux A et al. Lobular architecture of human adipose tissue defines the niche and fate of progenitor cells. Nat Commun. 2019;10:2546.","doi":"10.1038/s41467-019-09992-3","url":"https://doi.org/10.1038/s41467-019-09992-3","figure":"Figs. 1–2","design_decision":"Informed grouped adipocyte motif and fibrous boundary; not quantitative histology."},
 {"id":"fang2012","citation":"Fang M, Banaszak Holl MM. Type I Collagen D-Spacing in Fibril Bundles of Dermis, Tendon, and Bone: Bridging Between Nano- and Micro-Level Tissue Hierarchy. ACS Nano. 2012;6:9503–9514.","doi":"10.1021/nn302483x","url":"https://doi.org/10.1021/nn302483x","figure":"Fig. 1","design_decision":"Informed aligned-bundle versus multidirectional-mesh distinction without tissue-specific material claims."},
 {"id":"keller2021","citation":"Bindellini D, Voortman LM, Olie CS, van Putten M, van den Akker E, Raz V. Discovering fiber type architecture over the entire muscle using data-driven analysis. Cytometry A. 2021;99:1240–1249.","doi":"10.1002/cyto.a.24465","url":"https://doi.org/10.1002/cyto.a.24465","figure":"Fig. 1","design_decision":"Informed longitudinal and transverse muscle-fiber views; no fiber-type coding."},
]
_D=[
("epithelial_sheet","Epithelial Sheet","tissue-anatomy","epithelium",["epithelial layer","monolayer","apical-basal polarity"],["lateral","apical"],["Side view of polarized epithelium over basal support.","Apical view of a packed epithelial cell tiling."],"Generic organization; cell subtype and tissue identity are unspecified.",["akhtar2013"]),
("epithelial_acinus","Epithelial Acinus","tissue-anatomy","epithelium",["acinus","acinar lumen","glandular epithelium"],["closed_lumen","section"],["External acinar rosette with a small apical opening; the internal lumen is not fully exposed.","Section through a generic acinus with visible lumen and basal boundary."],"No organ, gland, developmental state, or lumen function is specified.",["akhtar2013"]),
("capillary","Capillary","vascular","microvessel",["microvessel","capillary lumen","endothelium"],["longitudinal","transverse"],["Narrow endothelial tube along its axis.","Transverse endothelial ring around a central lumen."],"No fenestration, flow, permeability, or tissue bed is specified.",["karkkainen2004"]),
("vessel_wall","Blood Vessel Wall","vascular","vessel",["artery wall","vein wall","tunica","vascular layers"],["thicker_wall","thinner_wall"],["Concentric layers with relatively prominent smooth muscle.","Concentric layers with relatively thinner smooth muscle."],"Generic relative wall thickness; does not identify artery or vein.",["karkkainen2004"]),
("lymphatic_capillary","Lymphatic Capillary","vascular","lymphatic",["initial lymphatic","lymphatic vessel","lymph uptake"],["blind_end","tissue_interface"],["Blind-ended channel with flap-like boundary cues.","Lymphatic channel at a tissue interface with fluid cues."],"No quantitative flux or specific junction state is implied.",["karkkainen2004"]),
("angiogenic_sprout","Angiogenic Sprout","vascular","angiogenesis",["endothelial sprout","neovascular sprout","branching vessel"],["single_tip","branching"],["Endothelial sprout with rounded leading tip.","Bifurcating endothelial sprout from vessel wall."],"No tip/stalk marker, growth-factor gradient, or outcome is asserted.",["karkkainen2004"]),
("collagen","Collagen Matrix","tissue-anatomy","extracellular-matrix",["collagen fibers","collagen bundle","matrix mesh"],["bundle","mesh"],["Aligned grouped collagen fibers form a bundle.","Open interwoven collagen fibers form a mesh."],"Generic organization; no scale or collagen type is claimed.",["fang2012"]),
("basement_membrane","Basement Membrane","tissue-anatomy","extracellular-matrix",["basal lamina","basement membrane sheet","epithelial support"],["isolated_sheet","epithelial_interface"],["Thin continuous basement-membrane sheet.","Basement-membrane band beneath an epithelial layer."],"Diagrammatic and not to scale; composition and permeability unspecified.",["akhtar2013"]),
("skeletal_muscle","Skeletal Muscle","tissue-anatomy","muscle",["myofiber","muscle fiber","muscle fascicle"],["longitudinal_fibers","bundle_cross_section"],["Parallel elongated fibers with restrained transverse marks.","Grouped cross-sectional muscle-fiber profiles with connective boundaries."],"No species, fiber type, contraction, pathology, or quantitative architecture.",["keller2021"]),
("adipose","Adipose Tissue","tissue-anatomy","adipose",["adipocyte","fat cell","adipose lobule"],["single_adipocyte","lobule"],["Generic unilocular adipocyte with peripheral cytoplasm and displaced nucleus.","Adipose lobule motif with grouped adipocyte profiles and fibrous boundary."],"No depot, species, metabolic state, or cell subtype is specified.",["divoux2019"]),]
CONCEPTS=[{"key":k,"name":n,"category":c,"subcategory":s,"synonyms":sy,"forms":[{"id":fid,"label":("External view" if fid=="closed_lumen" else fid.replace('_',' ').title()),"description":d} for fid,d in zip(fs,ds)],"limits":lim,"refs":refs} for k,n,c,s,sy,fs,ds,lim,refs in _D]
# Region sets are stable between a concept's two forms.
_R={
"epithelial_sheet":[("epithelium","Epithelial cells","#B8E2DA"),("lumen","Apical space","#FFF7E8"),("matrix","Basal support","#E8C98A"),("outline","Structural outlines","#26323D")],
"epithelial_acinus":[("epithelium","Epithelial cells","#B8E2DA"),("lumen","Lumen","#FFF7E8"),("matrix","Basal boundary","#E8C98A"),("outline","Structural outlines","#26323D")],
"capillary":[("endothelium","Endothelial wall","#B8E2DA"),("lumen","Lumen","#FFF7E8"),("matrix","Outer support","#E8C98A"),("outline","Structural outlines","#26323D")],
"vessel_wall":[("endothelium","Endothelial layer","#B8E2DA"),("smooth_muscle","Smooth-muscle layer","#E7A98B"),("matrix","Outer connective layer","#E8C98A"),("lumen","Lumen","#FFF7E8"),("outline","Structural outlines","#26323D")],
"lymphatic_capillary":[("endothelium","Lymphatic wall","#B8E2DA"),("fluid","Tissue-fluid cue","#8FC8E8"),("matrix","Surrounding tissue","#E8C98A"),("lumen","Lumen","#FFF7E8"),("outline","Structural outlines","#26323D")],
"angiogenic_sprout":[("endothelium","Endothelial sprout","#B8E2DA"),("matrix","Surrounding matrix","#E8C98A"),("lumen","Vessel lumen","#FFF7E8"),("outline","Structural outlines","#26323D")],
"collagen":[("matrix","Collagen fibers","#E8C98A"),("accent","Crossing fibers","#D89A72"),("outline","Structural outlines","#26323D")],
"basement_membrane":[("epithelium","Epithelial cells","#B8E2DA"),("matrix","Basement membrane","#E8C98A"),("lumen","Apical space","#FFF7E8"),("outline","Structural outlines","#26323D")],
"skeletal_muscle":[("muscle_fiber","Muscle fibers","#E7A98B"),("matrix","Connective tissue","#E8C98A"),("nucleus","Peripheral nuclei","#8D7FA8"),("outline","Structural outlines","#26323D")],
"adipose":[("adipocyte","Adipocyte","#F2D58B"),("cytoplasm","Cytoplasm","#B8E2DA"),("matrix","Fibrous boundary","#E8C98A"),("nucleus","Nucleus","#8D7FA8"),("outline","Structural outlines","#26323D")],}
def regions_for(key,index):
 if key not in _R or index not in (0,1): raise KeyError((key,index))
 return [{"id":a,"label":b,"default":c} for a,b,c in _R[key]]

def _geom(k,i):
 # Each branch defines silhouette-scale geometry; no text, filter, external resource, or raster.
 if k=="epithelial_sheet": return {"epithelium":('<path d="M20 43L40 39V83L20 79ZM43 39L63 42V84L43 83ZM66 42L87 39V82L66 84ZM90 40L108 44V79L90 82Z"/>' if i==0 else '<path d="M22 28Q40 17 57 29T90 29L108 34V53Q91 64 74 54T40 54L22 50ZM22 64Q40 54 57 65T90 64L108 69V89Q91 99 74 89T40 90L22 85Z"/>'),"lumen":'<path d="M18 20H110V33H18Z"/>' if i==0 else '',"matrix":'<path d="M18 91Q64 95 110 91V103Q64 107 18 103Z"/>' if i==0 else '',"outline":'<path d="M18 39Q64 32 110 39M18 86Q64 91 110 86"/>' if i==0 else '<path d="M22 27Q40 15 57 27T90 27L110 32M22 52Q40 62 57 52T90 52L110 63M22 63Q40 51 57 63T90 63L110 67M22 91Q40 101 57 91T90 91L110 87"/>'}
 if k=="epithelial_acinus":
  if i==0:
   cells=''.join(f'<circle cx="{x}" cy="{y}" r="9"/>' for x,y in [(64,25),(84,34),(94,53),(90,75),(73,91),(51,91),(34,77),(31,55),(42,36)])
   return {"epithelium":cells,"lumen":'<circle cx="63" cy="60" r="21"/>',"matrix":'<circle cx="63" cy="60" r="48" fill="none" stroke="#E8C98A" stroke-width="5"/>',"outline":'<circle cx="63" cy="60" r="48"/><circle cx="63" cy="60" r="21"/>'}
  return {"epithelium":'<path d="M22 35Q36 24 49 34V61Q36 68 22 59ZM51 32Q64 22 77 33V61Q64 68 50 61ZM80 35Q94 25 106 38V62Q93 69 79 61ZM22 68Q36 61 49 71V94Q36 101 22 88ZM51 69Q64 62 77 70V94Q64 101 50 94ZM80 68Q94 63 106 72V90Q93 99 80 92Z"/>',"lumen":'<path d="M52 47Q64 41 77 48V61Q64 67 50 60Z"/>',"matrix":'<path d="M18 28Q64 14 110 29V35Q64 21 18 35Z"/>',"outline":'<path d="M20 31Q64 17 109 32M20 96Q64 107 109 96"/>'}
 if k=="capillary":
  if i==0:return {"endothelium":'<path d="M17 38Q28 30 39 38H108V51H39Q28 58 17 51Z M17 76Q28 69 39 76H108V89H39Q28 97 17 89Z"/>',"lumen":'<path d="M18 55Q28 52 38 55H111V74H38Q28 77 18 74Z"/>',"matrix":'<path d="M15 32H112V36H15ZM15 91H112V95H15Z"/>',"outline":'<path d="M16 38Q28 29 40 38H109M16 51Q28 59 40 51H109M16 76Q28 68 40 76H109M16 89Q28 97 40 89H109"/>'}
  return {"endothelium":'<circle cx="64" cy="64" r="37"/>',"lumen":'<circle cx="64" cy="64" r="24"/>',"matrix":'<circle cx="64" cy="64" r="46" fill="none" stroke="#E8C98A" stroke-width="4"/>',"outline":'<circle cx="64" cy="64" r="47"/><circle cx="64" cy="64" r="23"/>'}
 if k=="vessel_wall":
  thick=i==0
  return {"endothelium":'<circle cx="64" cy="64" r="25" fill="none" stroke="#B8E2DA" stroke-width="6"/>',"smooth_muscle":f'<circle cx="64" cy="64" r="{35 if thick else 31}" fill="none" stroke="#E7A98B" stroke-width="{12 if thick else 6}"/>',"matrix":'<circle cx="64" cy="64" r="45" fill="none" stroke="#E8C98A" stroke-width="8"/>',"lumen":'<circle cx="64" cy="64" r="19"/>',"outline":'<circle cx="64" cy="64" r="49"/><circle cx="64" cy="64" r="41"/><circle cx="64" cy="64" r="28"/><circle cx="64" cy="64" r="19"/>'}
 if k=="lymphatic_capillary": return ({"endothelium":'<path d="M34 103V55A30 30 0 0 1 94 55V103H84V55A20 20 0 0 0 44 55V103Z"/>',"fluid":'<circle cx="25" cy="72" r="3.5"/><circle cx="103" cy="61" r="3.5"/>',"matrix":'<path d="M17 41V105M111 41V105" fill="none" stroke="#E8C98A" stroke-width="4"/>',"lumen":'<path d="M45 103V55A19 19 0 0 1 83 55V103Z"/>',"outline":'<path d="M34 103V55A30 30 0 0 1 94 55V103M44 103V55A20 20 0 0 1 84 55V103"/>'} if i==0 else {"endothelium":'<path d="M37 34Q64 23 91 34V88Q64 99 37 88Z"/>',"fluid":'<circle cx="24" cy="48" r="4"/><circle cx="27" cy="69" r="3.5"/><circle cx="103" cy="57" r="4"/><circle cx="99" cy="78" r="3"/>',"matrix":'<path d="M15 28V97M113 28V97" fill="none" stroke="#E8C98A" stroke-width="4"/>',"lumen":'<path d="M46 42Q64 33 82 42V80Q64 89 46 80Z"/>',"outline":'<path d="M37 34Q64 23 91 34V88Q64 99 37 88ZM46 42Q64 33 82 42V80Q64 89 46 80ZM37 48L47 55M91 67L81 74"/>'})
 if k=="angiogenic_sprout":
  br=i==1
  return {"endothelium":'<path d="M15 77H51Q62 77 66 64L75 42Q80 30 91 27Q100 25 102 33Q103 39 95 43Q87 47 84 55L77 77Q70 98 51 98H15Z"/>'+('<path d="M73 58Q88 53 99 40L105 44Q96 59 78 65Z"/>' if br else ''),"matrix":'<path d="M15 108Q64 112 113 108" fill="none" stroke="#E8C98A" stroke-width="5"/>',"lumen":'<path d="M17 82H51Q60 82 63 67L72 47Q77 35 89 32Q94 31 95 36Q95 40 88 44Q81 48 78 57L70 79Q65 92 51 92H17Z"/>',"outline":'<path d="M14 74H51Q61 74 64 62L73 39Q80 21 95 24Q107 28 102 41Q99 46 91 49Q85 52 82 59L75 81Q69 102 51 102H14"/>'+('<path d="M76 58Q92 53 104 41"/>' if br else '')}
 if k=="collagen":
  if i==0:
   p=''.join(f'<path d="M18 {y}Q58 {y-5} 110 {y+1}"/>' for y in [31,43,55,67,79,91]);return {"matrix":p,"accent":"","outline":p}
  a='<path d="M20 25Q54 44 108 100M18 53Q54 60 110 77M30 105Q57 68 98 22"/>';b='<path d="M18 39Q54 49 110 60M19 86Q61 72 106 37M45 20Q56 58 82 108"/>';return {"matrix":a,"accent":b,"outline":a+b}
 if k=="basement_membrane":return {"epithelium":'' if i==0 else '<path d="M20 26Q40 19 59 26T100 26V48Q80 54 60 48T20 48Z M20 51Q40 45 59 51T100 51V57Q64 61 20 57Z"/>',"matrix":'<path d="M18 62Q64 58 110 62V73Q64 69 18 73Z"/>',"lumen":'<path d="M17 20H111V47Q64 52 17 47Z"/>' if i==0 else '<path d="M18 15H110V21Q64 18 18 21Z"/>',"outline":'<path d="M18 62Q64 58 110 62M18 73Q64 69 110 73"/>'}
 if k=="skeletal_muscle":
  if i==0:
   f='<path d="M20 27Q64 20 108 27V45Q64 50 20 45ZM20 54Q64 49 108 54V72Q64 77 20 72ZM20 81Q64 76 108 81V99Q64 104 20 99Z"/>';m=''.join(f'<path d="M{x} 29V43M{x} 56V70M{x} 83V97"/>' for x in [39,57,75,93]);return {"muscle_fiber":f,"matrix":"","nucleus":'<ellipse cx="28" cy="35" rx="3" ry="6"/><ellipse cx="100" cy="89" rx="3" ry="6"/>',"outline":f+m}
  cs=''.join(f'<circle cx="{x}" cy="{y}" r="10"/>' for x,y in [(35,35),(64,35),(93,35),(35,64),(64,64),(93,64),(35,93),(64,93),(93,93)]);return {"muscle_fiber":cs,"matrix":'<path d="M20 20H108V108H20Z" fill="none" stroke="#E8C98A" stroke-width="4"/>',"nucleus":"","outline":cs+'<path d="M20 20H108V108H20Z"/>'}
 if k=="adipose":
  if i==0:return {"adipocyte":'<circle cx="64" cy="64" r="43"/>',"cytoplasm":'<circle cx="64" cy="64" r="37" fill="none" stroke="#B8E2DA" stroke-width="4"/>',"matrix":"","nucleus":'<ellipse cx="38" cy="82" rx="5" ry="8"/>',"outline":'<circle cx="64" cy="64" r="43"/><ellipse cx="38" cy="82" rx="5" ry="8"/>'}
  cs=''.join(f'<circle cx="{x}" cy="{y}" r="15"/>' for x,y in [(43,43),(76,42),(59,69),(91,72),(35,88),(79,99)]);return {"adipocyte":cs,"cytoplasm":"","matrix":'<path d="M25 33Q58 18 91 32L104 59L96 93L68 108L34 101L21 72Z" fill="none" stroke="#E8C98A" stroke-width="5"/>',"nucleus":'<ellipse cx="34" cy="48" rx="3" ry="5"/><ellipse cx="67" cy="47" rx="3" ry="5"/><ellipse cx="50" cy="74" rx="3" ry="5"/><ellipse cx="83" cy="77" rx="3" ry="5"/>',"outline":cs+'<path d="M25 33Q58 18 91 32L104 59L96 93L68 108L34 101L21 72Z"/>'}
 raise KeyError(k)

# Reviewed geometry overrides. The original draft branches above remain useful
# as editable starting points; these corrections fix topology and region paint.
_R["epithelial_sheet"]=[("epithelium","Epithelial cells","#B8E2DA"),("junction","Cell junctions","#D98C68"),("outline","Structural outlines","#26323D")]
_R["adipose"]=[("lipid_droplet","Lipid store","#F2D58B"),("cytoplasm","Cytoplasm","#B8E2DA"),("nucleus","Nucleus","#8D7FA8"),("outline","Structural outlines","#26323D")]
_R["basement_membrane"]=[("basement_sheets","Basement-membrane layers","#E8C98A"),("attachment_arms","Cell–matrix attachment structures","#B8E2DA"),("submembrane_mesh","Submembrane matrix mesh","#D89A72"),("outline","Structural outlines","#26323D")]
_geom_draft=_geom
def _geom(k,i):
 d=_geom_draft(k,i)
 if k=="capillary":
  if i==0:
   d={"endothelium":'<path d="M16 39Q26 31 36 39H112V52H36Q26 59 16 52ZM16 76Q26 69 36 76H112V89H36Q26 96 16 89Z"/>',"lumen":'<path d="M17 55Q27 52 38 55H111V74H38Q27 77 17 74Z"/>',"matrix":'<path d="M14 33H113V36H14ZM14 92H113V95H14Z"/>',"outline":'<path d="M15 39Q26 31 37 39H113M15 52Q26 59 37 52H113M15 76Q26 69 37 76H113M15 89Q26 96 37 89H113"/>'}
  else:
   d={"endothelium":'<circle cx="64" cy="64" r="37"/>',"lumen":'<circle cx="64" cy="64" r="24"/>',"matrix":'<circle cx="64" cy="64" r="46" fill="none" stroke="#E8C98A" stroke-width="4"/>',"outline":'<circle cx="64" cy="64" r="47"/><circle cx="64" cy="64" r="23"/>'}
 if k=="vessel_wall":
  thick=(i==0)
  d={"endothelium":'<circle cx="64" cy="64" r="25" fill="none" stroke="#B8E2DA" stroke-width="6"/>',"smooth_muscle":f'<circle cx="64" cy="64" r="{35 if thick else 32}" fill="none" stroke="#E7A98B" stroke-width="{12 if thick else 7}"/>',"matrix":'<circle cx="64" cy="64" r="45" fill="none" stroke="#E8C98A" stroke-width="8"/>',"lumen":'<circle cx="64" cy="64" r="19"/>',"outline":'<circle cx="64" cy="64" r="49"/><circle cx="64" cy="64" r="41"/><circle cx="64" cy="64" r="28"/><circle cx="64" cy="64" r="19"/>'}
 if k=="epithelial_acinus":
  if i==0:
   pts=[(64,31,10,11),(40,40,12,12),(88,40,12,12),(29,59,11,13),(99,59,11,13),(40,77,12,12),(88,77,12,12),(64,87,12,12)]
   cells=''.join(f'<ellipse cx="{x}" cy="{y}" rx="{rx}" ry="{ry}"/>' for x,y,rx,ry in pts)
   aperture='<path d="M57 49Q64 44 71 49L69 58Q64 63 59 58Z"/>'
   basal='<path d="M28 80Q64 105 100 80L96 90Q64 111 32 90Z"/>'
   d={"epithelium":cells,"lumen":aperture,"matrix":basal,"outline":cells+aperture+'<path d="M28 80Q64 105 100 80"/>'}
  else:
   sectors=[]; dividers=[]
   for n in range(8):
    a1=n*45+2; a2=(n+1)*45-2
    def pt(radius,degree):
     rad=math.radians(degree);return (64+radius*math.cos(rad),64+radius*math.sin(rad))
    x1,y1=pt(42,a1);x2,y2=pt(42,a2);u2,v2=pt(23,a2);u1,v1=pt(23,a1)
    sectors.append(f'<path d="M{x1:.2f} {y1:.2f}A42 42 0 0 1 {x2:.2f} {y2:.2f}L{u2:.2f} {v2:.2f}A23 23 0 0 0 {u1:.2f} {v1:.2f}Z"/>')
    dx,dy=pt(22,n*45);ex,ey=pt(42,n*45);dividers.append(f'<path d="M{dx:.2f} {dy:.2f}L{ex:.2f} {ey:.2f}"/>')
   matrix='<path d="M64 18A46 46 0 1 1 63.9 18M64 22A42 42 0 1 0 64.1 22Z" fill-rule="evenodd"/>'
   d={"epithelium":''.join(sectors),"lumen":'<circle cx="64" cy="64" r="21"/>',"matrix":matrix,"outline":'<circle cx="64" cy="64" r="48"/><circle cx="64" cy="64" r="21"/>'+''.join(dividers)}
 if k=="lymphatic_capillary":
  if i==0:
   d={"endothelium":'<path d="M34 108V55A30 30 0 0 1 94 55V108 M44 108V55A20 20 0 0 1 84 55V108" fill="none" stroke="#B8E2DA" stroke-width="8" stroke-linecap="round"/>',"fluid":'<circle cx="25" cy="72" r="3.5"/><circle cx="103" cy="61" r="3.5"/>',"matrix":'<path d="M17 42V108M111 42V108" fill="none" stroke="#E8C98A" stroke-width="4"/>',"lumen":'<path d="M48 105V55A16 16 0 0 1 80 55V105" fill="none" stroke="#FFF7E8" stroke-width="2"/>',"outline":'<path d="M34 108V55A30 30 0 0 1 94 55V108 M44 108V55A20 20 0 0 1 84 55V108"/>'}
  else:
   flaps='<path d="M20 82Q38 75 52 80Q59 82 63 89L68 72Q70 66 74 70L83 84Q96 77 109 83V91Q95 87 83 94L72 82Q68 79 65 84Q60 92 51 89Q37 84 20 91Z"/>'
   lumen='<path d="M24 90Q40 86 53 91Q62 96 69 89Q85 84 105 90V98Q105 102 100 102H29Q24 102 24 98Z"/>'
   tissue='<path d="M17 31Q29 24 41 31L44 38Q31 33 21 41Z M84 32Q97 24 111 32L107 41Q96 34 86 39Z M18 110Q42 113 60 109M79 110Q97 113 111 109"/>'
   d={"endothelium":flaps,"fluid":'<circle cx="49" cy="46" r="4"/><circle cx="62" cy="62" r="4"/><circle cx="72" cy="94" r="3.5"/>',"matrix":tissue,"lumen":lumen,"outline":flaps+lumen+tissue}
 if k=="collagen":
  if i==0:
   p=''.join(f'<path d="M18 {y}Q58 {y-5} 110 {y+1}"/>' for y in [31,43,55,67,79,91])
   d={"matrix":p,"accent":'<path d="M18 55Q58 50 110 56M18 67Q58 62 110 68"/>',"outline":p}
  else:
   a='<path d="M17 24Q43 34 70 54T111 103M17 43Q43 53 70 70T110 95M17 65Q43 75 72 91T105 109M22 18Q39 43 57 66T85 111M45 17Q54 42 70 69T101 109M108 20Q86 37 64 59T20 105"/>'
   b='<path d="M17 33Q44 42 72 59T111 83M18 55Q45 65 74 81T108 105M21 88Q46 72 72 52T106 20M39 112Q53 82 70 57T94 17M17 74Q43 55 66 35T98 17"/>'
   d={"matrix":a,"accent":b,"outline":a+b}
 if k=="epithelial_sheet":
  if i==0:d["junction"]='<path d="M40 40V83M63 41V84M87 40V82"/>'
  else:d["junction"]='<path d="M22 53Q40 61 57 53T90 53M22 63Q40 55 57 63T90 63"/>'
 if k=="basement_membrane":
  if i==0:
   sheets='<path d="M18 61Q42 54 64 60T110 59V68Q84 72 62 66T18 70Z M19 73Q42 67 64 72T109 71V77Q84 81 63 76T19 80Z"/>'
   arms='<path d="M34 58V41Q34 36 38 36Q42 36 42 41V58M62 58V39Q62 34 66 34Q70 34 70 39V58M90 58V41Q90 36 94 36Q98 36 98 41V58"/>'
   mesh='<path d="M22 88Q39 80 55 90T88 88T108 91M22 98Q40 91 57 100T90 98T108 101M36 84L42 105M69 84L72 106M96 85L91 105"/>'
  else:
   sheets='<path d="M18 70Q42 64 64 69T110 68V77Q84 81 62 76T18 80Z M19 82Q42 76 64 81T109 80V86Q84 90 63 85T19 89Z"/>'
   arms='<path d="M20 38Q31 30 42 38V68Q31 73 20 68ZM42 36Q53 29 64 36V68Q53 73 42 68ZM64 36Q75 29 86 36V68Q75 73 64 68ZM86 38Q97 31 108 39V68Q97 73 86 68Z"/>'
   mesh='<path d="M21 98Q41 90 60 98T98 98T110 100M25 107Q45 100 63 107T100 106M38 94L42 111M70 94L73 112M97 94L92 110"/>'
  d={"basement_sheets":sheets,"attachment_arms":arms,"submembrane_mesh":mesh,"outline":sheets+arms}
 if k=="skeletal_muscle":
  d["matrix"]='<path d="M20 49H108M20 76H108" fill="none" stroke="#E8C98A" stroke-width="3"/>' if i==0 else '<path d="M20 20H108V108H20Z" fill="none" stroke="#E8C98A" stroke-width="4"/>'
  if i==1:d["nucleus"]=''.join(f'<ellipse cx="{x}" cy="{y}" rx="2.5" ry="4"/>' for x,y in [(27,35),(56,35),(85,35),(27,64),(56,64),(85,64),(27,93),(56,93),(85,93)])
 if k=="adipose":
  if i==0:
   d={"lipid_droplet":'<circle cx="64" cy="64" r="35"/>',"cytoplasm":'<circle cx="64" cy="64" r="42" fill="none" stroke="#B8E2DA" stroke-width="5"/>',"nucleus":'<ellipse cx="38" cy="82" rx="5" ry="8"/>',"outline":'<circle cx="64" cy="64" r="43"/><circle cx="64" cy="64" r="35"/><ellipse cx="38" cy="82" rx="5" ry="8"/>'}
  else:
   pts=[(43,43),(76,42),(59,69),(91,72),(35,88),(79,99)]
   d={"lipid_droplet":''.join(f'<circle cx="{x}" cy="{y}" r="10"/>' for x,y in pts),"cytoplasm":''.join(f'<circle cx="{x}" cy="{y}" r="13" fill="none" stroke="#B8E2DA" stroke-width="3"/>' for x,y in pts),"nucleus":''.join(f'<ellipse cx="{x-10}" cy="{y}" rx="2.5" ry="4"/>' for x,y in pts),"outline":''.join(f'<circle cx="{x}" cy="{y}" r="14"/>' for x,y in pts)}
 if k=="angiogenic_sprout" and i==1:
  outer='<path d="M14 55H43Q51 55 57 49L75 30Q84 20 96 25Q105 29 98 38L78 59Q74 64 78 69L98 89Q105 98 96 103Q84 108 75 98L57 79Q51 73 43 73H14Z"/>'
  lumen='<path d="M15 61H43Q50 61 55 54L74 36Q82 27 91 31Q96 35 90 41L72 60Q68 64 72 68L90 87Q96 93 91 97Q82 101 74 93L55 74Q50 67 43 67H15Z"/>'
  tips='<path d="M76 29L80 20L84 29Z M89 25L98 21L94 31Z M76 99L80 108L84 99Z M89 103L98 107L94 97Z"/>'
  d={"endothelium":outer+tips,"matrix":'<path d="M18 107Q36 110 51 107M77 107Q94 110 111 107"/>',"lumen":lumen,"outline":'<path d="M14 55H43Q51 55 57 49L75 30Q84 20 96 25M14 73H43Q51 73 57 79L75 98Q84 108 96 103M43 61Q50 61 55 54L74 36M43 67Q50 67 55 74L74 93"/>'}
 return d

def render_svg(key,index,title,description):
 if key not in _R or index not in (0,1):raise KeyError((key,index))
 g=_geom(key,index);out=[]
 # Dark structural contour is a broad underlay; semantic colors remain visible.
 for rid,_,color in _R[key]:
  if rid=='outline':
   x=g.get(rid,'');out.append(f'<g data-region="outline" fill="none" stroke="{color}" stroke-width="5.2" stroke-linecap="round" stroke-linejoin="round">{x}</g>')
 for rid,_,color in _R[key]:
   if rid!='outline':
    x=g.get(rid,'')
    if key=='collagen' and index==1:out.append(f'<g data-region="{rid}" fill="none" stroke="{color}" stroke-width="5.5" stroke-linecap="round" stroke-linejoin="round">{x}</g>')
    elif key=='basement_membrane' and rid in {'attachment_arms','submembrane_mesh'}:out.append(f'<g data-region="{rid}" fill="none" stroke="{color}" stroke-width="4" stroke-linecap="round" stroke-linejoin="round">{x}</g>')
    elif key=='angiogenic_sprout' and index==1 and rid=='matrix':out.append(f'<g data-region="{rid}" fill="none" stroke="{color}" stroke-width="4" stroke-linecap="round" stroke-linejoin="round">{x}</g>')
    else:out.append(f'<g data-region="{rid}" fill="{color}" stroke="none">{x}</g>')
 return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 128" role="img" aria-labelledby="title desc"><title id="title">{escape(title)}</title><desc id="desc">{escape(description)}</desc>{"".join(out)}</svg>'
if __name__=='__main__':
 import xml.etree.ElementTree as ET
 assert len(CONCEPTS)==10 and sum(len(c['forms']) for c in CONCEPTS)==20
 for c in CONCEPTS:
  for i,f in enumerate(c['forms']):
   root=ET.fromstring(render_svg(c['key'],i,c['name']+' — '+f['label'],f['description']))
   assert root.get('viewBox')=='0 0 128 128' and root.find('{http://www.w3.org/2000/svg}title') is not None and root.find('{http://www.w3.org/2000/svg}desc') is not None
   assert {e.get('data-region') for e in root.iter() if e.get('data-region')}=={r['id'] for r in regions_for(c['key'],i)}
   assert not ({e.tag.split('}')[-1] for e in root.iter()} & {'script','foreignObject','filter','image','iframe'})
 print('PASS: 10 concepts, 20 forms, accessible SVG and exact region-id checks')
