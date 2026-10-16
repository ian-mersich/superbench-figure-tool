"""Original editable construction for cell structures and cell stress schematics.

Coordinates are authored here, never read from a published figure or icon library.
Two forms communicate biological context/topology rather than cosmetic treatments.
"""
from __future__ import annotations
from html import escape
import math

COLORS={'cytoplasm':'#C7F2EC','membrane':'#7DD3C7','nucleus':'#D9D7FF',
 'nucleolus':'#B8B5FF','fibrillar_component':'#7B78C9','fibrillar_centers':'#F4A261',
 'speckle':'#7B78C9','rna_protein':'#F4A261','chromatid':'#B8B5FF',
 'centromere':'#F4A261','axoneme':'#8EC8FF','basal_body':'#B8B5FF',
 'coat':'#5EA9DD','cargo':'#F4A261','enzymes':'#7B78C9','actin':'#E76F51',
 'debris':'#F4A261','lipid_damage':'#E76F51','mitochondria':'#8EC8FF',
 'cristae':'#E76F51','gasdermin':'#F4A261','mlkl':'#8EC8FF','matrix':'#9FD8B5',
 'adhesion':'#8EC8FF','chromatin':'#B8B5FF','foci':'#E76F51','parent_dna':'#8EC8FF',
 'nascent_dna':'#7B78C9','stress_site':'#E76F51','er_membrane':'#8EC8FF',
 'unfolded_protein':'#E76F51','stress_sensor':'#B8B5FF','division_ring':'#B8B5FF',
 'fusion_site':'#B8B5FF','outline':'#26323D','lumen':'#F7F9FC'}
LABELS={'fibrillar_component':'Dense fibrillar component','fibrillar_centers':'Fibrillar centers',
 'rna_protein':'Illustrative RNA and protein material','chromatid':'Sister chromatids',
 'centromere':'Centromere region','axoneme':'Axonemal microtubule cue','basal_body':'Basal body',
 'coat':'Vesicle coat','enzymes':'Lysosomal enzyme cues','lipid_damage':'Lipid peroxidation cues',
 'gasdermin':'Gasdermin pore cues','mlkl':'Membrane-associated MLKL cues','matrix':'Extracellular matrix',
 'adhesion':'Cell–matrix attachment cues','foci':'Illustrative nuclear foci',
 'parent_dna':'Parental DNA strands','nascent_dna':'Newly synthesized DNA strands',
 'stress_site':'Replication stress cue','unfolded_protein':'Unfolded protein cues',
 'stress_sensor':'ER stress sensor cue','division_ring':'Constriction machinery cue',
 'fusion_site':'Membrane joining site','outline':'Structural outlines'}

class Drawing:
 def __init__(self):self.parts=[];self.used=[]
 def add(self,region,geometry,name,paint='fill',width=3.5):
  if region not in self.used:self.used.append(region)
  color=COLORS[region]
  attrs=f'fill="{color}"' if paint=='fill' else f'fill="none" stroke="{color}" stroke-width="{width}" stroke-linecap="round" stroke-linejoin="round"'
  self.parts.append(f'<g data-region="{region}" id="{name}" {attrs}>{geometry}</g>')
 def shape(self,region,geometry,name,outline=True,width=3.5):
  self.add(region,geometry,name+'-fill')
  if outline:self.add('outline',geometry,name+'-outline','stroke',width)
 def path(self,region,d,name,width=3):self.add(region,f'<path d="{d}"/>',name,'stroke',width)
 def circle(self,region,x,y,r,name,outline=True,width=3):self.shape(region,f'<circle cx="{x}" cy="{y}" r="{r}"/>',name,outline,width)
 def ellipse(self,region,x,y,rx,ry,name,outline=True,width=3):self.shape(region,f'<ellipse cx="{x}" cy="{y}" rx="{rx}" ry="{ry}"/>',name,outline,width)
 def rect(self,region,x,y,w,h,rx,name,outline=True):self.shape(region,f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}"/>',name,outline)
 def svg(self,title,desc):
  return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 128" role="img" aria-labelledby="title desc">\n'
   f'<title id="title">{escape(title)}</title>\n<desc id="desc">{escape(desc)}</desc>\n'+ '\n'.join(self.parts)+'\n</svg>\n')
 def regions(self):return [{'id':r,'label':LABELS.get(r,r.replace('_',' ').capitalize()),'default':COLORS[r]} for r in self.used]

def arrow(a,x1,y1,x2,y2,name='direction'):
 a.path('outline',f'M{x1} {y1}L{x2} {y2}',name,2.75)
 angle=math.atan2(y2-y1,x2-x1);p=[]
 for offset in [2.55,-2.55]:p.append((x2+7*math.cos(angle+offset),y2+7*math.sin(angle+offset)))
 a.path('outline',f'M{p[0][0]:.2f} {p[0][1]:.2f}L{x2} {y2}L{p[1][0]:.2f} {p[1][1]:.2f}',name+'-arrowhead',2.75)

def nucleus(a,x=64,y=64,r=43,inner=True):
 a.ellipse('nucleus',x,y,r,r-3,'nuclear-interior')
 if inner:a.path('outline',f'M{x-r+6} {y-10}C{x-r+10} {y-r+4} {x+r-5} {y-r+4} {x+r-6} {y+10}', 'inner-envelope',1.6)

def cell(a,form='round',broken=False):
 if form=='swollen': d='M99 39C112 55 109 85 91 101C72 117 42 110 27 94C11 76 17 48 33 30C51 12 83 19 99 39Z'
 elif form=='irregular':d='M98 34C113 47 104 61 109 76C110 91 94 105 76 104C58 118 45 100 30 96C14 90 19 72 18 57C12 40 34 29 45 25C64 13 83 19 98 34Z'
 else:d='M101 43C112 65 100 93 79 104C55 116 28 100 21 80C12 57 29 28 51 23C73 15 91 24 101 43Z'
 if not broken:a.shape('cytoplasm',f'<path d="{d}"/>','cell-body')
 else:
  open_path='M103 76C106 90 94 103 78 107C55 114 29 100 22 80C12 57 28 28 51 23C71 17 91 23 101 42'
  a.shape('cytoplasm',f'<path d="{open_path}Z"/>','cell-body',False)
  a.path('outline',open_path,'breached-membrane',3.5)
  a.path('outline','M99 41l7 5-7 7M104 77l-7-4 6-8','rupture-edges',3.5)

def mini_mito(a,x,y,w=25,h=12,name='mitochondrion',lines=2):
 a.rect('mitochondria',x,y,w,h,h/2,name)
 for j in range(lines):
  px=x+7+j*(w-14)/max(1,lines-1)
  a.path('cristae',f'M{px} {y+3}l-2 {h-6}',name+f'-crista-{j}',1.7)

def draw(key,form):
 a=Drawing();alt=form==1
 if key=='nucleolus':
  if alt:
   nucleus(a);a.ellipse('nucleolus',65,66,24,21,'nucleolar-granular-component')
   for i,(x,y) in enumerate([(57,61),(73,70)]):
    a.circle('fibrillar_component',x,y,9,f'dense-fibrillar-{i}',False);a.circle('fibrillar_centers',x,y,3.4,f'fibrillar-center-{i}',False)
  else:
   a.shape('nucleolus','<path d="M28 40C38 22 72 16 93 31C111 45 110 78 94 96C74 115 41 107 25 87C12 72 19 53 28 40Z"/>','nucleolar-granular-component')
   for i,(x,y,r) in enumerate([(45,50,14),(77,53,15),(62,82,12)]):
    a.circle('fibrillar_component',x,y,r,f'dense-fibrillar-{i}',False);a.circle('fibrillar_centers',x+1,y-1,4.6,f'fibrillar-center-{i}',False)
 elif key=='nuclear_speckle':
  if not alt:
   nucleus(a,inner=False)
   for i,(x,y) in enumerate([(43,42),(72,38),(86,61),(66,74),(38,78)]):
    a.shape('speckle',f'<path d="M{x-6} {y}q-4-7 3-8q7-5 11 1q7 4 2 10q-7 7-13 2Z"/>',f'nuclear-speckle-{i}',False)
   a.ellipse('nucleolus',49,60,8,6,'nucleolar-context',False)
  else:
   a.shape('speckle','<path d="M31 40Q27 28 42 28Q50 17 64 25Q81 17 87 34Q108 38 101 54Q114 67 99 78Q100 96 81 97Q65 111 52 98Q32 103 28 86Q13 77 24 62Q15 49 31 40Z"/>','speckle-condensate')
   for i,(x,y) in enumerate([(43,45),(70,39),(84,62),(56,68),(72,86),(36,81)]):a.path('rna_protein',f'M{x-3} {y}q5-8 9 0q4 6 8 0',f'ribonucleoprotein-cue-{i}',2.5)
 elif key=='condensed_chromosome':
  c=52 if alt else 63
  d=f'M36 24Q29 19 25 28Q22 33 27 42L{c-9} {c}L28 92Q23 101 30 106Q38 109 43 101L{c} {c+12}L83 102Q89 110 97 104Q103 99 97 90L{c+10} {c}L98 40Q104 29 96 24Q87 20 82 30L{c} {c-12}L45 27Q41 21 36 24Z'
  a.shape('chromatid',f'<path d="{d}"/>','replicated-chromosome')
  a.ellipse('centromere',c,c,11,7,'centromere-region')
  a.path('outline',f'M36 33L{c-5} {c-7}M91 33L{c+5} {c-7}M35 98L{c-4} {c+10}M91 98L{c+5} {c+10}','sister-chromatid-grooves',1.6)
 elif key=='primary_cilium':
  a.shape('cytoplasm','<path d="M17 88H111V112H17Z"/>','apical-cytoplasm',False)
  if not alt:
   a.shape('membrane','<path d="M17 88H51V29Q51 16 62 16Q73 16 73 29V88H111V96H69V30Q69 23 62 23Q56 23 56 30V96H17Z"/>','ciliary-membrane')
   a.path('axoneme','M59 33V90M65 33V90','axoneme-microtubules',2.7)
  else:
   a.shape('membrane','<path d="M17 88H48C49 68 61 58 72 46Q85 33 91 21Q96 13 103 18Q111 23 104 33Q95 49 82 60C66 75 63 82 62 88H111V96H56Q52 81 76 57Q91 43 98 29Q101 24 98 23Q93 35 78 50Q58 68 57 96H17Z"/>','bent-ciliary-membrane')
   a.path('axoneme','M55 89C57 70 72 61 82 48Q95 34 97 27','bent-axoneme',3)
  a.rect('basal_body',51,96,19,12,3,'basal-body')
  a.path('outline','M56 99V105M62 99V105M66 99V105','basal-body-longitudinal-cues',1.5)
 elif key=='caveola':
  if not alt:
   a.shape('cytoplasm','<path d="M17 42H111V110H17Z"/>','cytoplasmic-context',False)
   a.shape('lumen','<path d="M58 30H71V47C84 53 89 65 88 73C87 89 66 100 52 91C35 83 34 57 55 47Z"/>','extracellularly-continuous-caveolar-lumen',False)
   a.shape('membrane','<path d="M17 36H51Q58 36 55 47C34 57 35 83 52 91C66 100 87 89 88 73Q89 55 74 48Q70 36 78 36H111V44H82Q93 59 94 73Q94 99 66 103Q39 103 33 82Q25 61 47 44H17Z"/>','flask-shaped-caveolar-membrane')
   for i,(x,y) in enumerate([(36,61),(35,79),(48,96),(71,99),(89,85),(92,65)]):a.ellipse('coat',x,y,3,5,f'caveolar-coat-cue-{i}',False)
  else:
   a.shape('cytoplasm','<path d="M16 31H112V112H16Z"/>','cytoplasmic-context',False)
   a.shape('lumen','<path d="M51 22H76V30Q66 30 71 43Q86 57 79 72Q71 86 56 82Q42 77 43 62Q41 47 54 40Q59 30 48 30Z"/>','surface-connected-caveolar-lumen',False)
   a.path('membrane','M17 30H48Q59 30 54 40Q41 47 43 62Q42 77 56 82Q71 86 79 72Q86 57 71 43Q66 30 78 30H111','surface-connected-caveola',9)
   a.path('outline','M17 25H49M78 25H111M17 35H47M80 35H111','flat-membrane-contours',2.2)
   a.circle('membrane',37,90,16,'neighboring-caveolar-profile');a.circle('membrane',91,94,15,'second-caveolar-profile')
   a.circle('lumen',37,90,11,'neighboring-profile-lumen',False);a.circle('lumen',91,94,10,'second-profile-lumen',False)
   for i,(x,y) in enumerate([(26,79),(24,97),(41,107),(83,82),(103,89),(97,106),(49,51),(65,80)]):a.circle('coat',x,y,3,f'caveolar-coat-cue-{i}',False)
 elif key=='clathrin_coated_vesicle':
  if not alt:
   a.circle('membrane',64,64,32,'closed-vesicle-membrane');a.circle('lumen',64,64,25,'vesicle-lumen',False)
   for i,(x,y) in enumerate([(53,57),(74,73),(71,49)]):a.circle('cargo',x,y,4,f'cargo-{i}',False)
   pts=[]
   for i in range(12):
    t=2*math.pi*i/12;pts.append((64+44*math.cos(t),64+44*math.sin(t)))
   for i,(x,y) in enumerate(pts):
    nx,ny=pts[(i+1)%12];a.path('coat',f'M{x:.2f} {y:.2f}L{nx:.2f} {ny:.2f}',f'coat-edge-{i}',4)
    ix,iy=64+35*math.cos(2*math.pi*i/12),64+35*math.sin(2*math.pi*i/12);a.path('coat',f'M{x:.2f} {y:.2f}L{ix:.2f} {iy:.2f}',f'coat-spoke-{i}',3)
  else:
   a.circle('membrane',64,64,38,'vesicle-membrane');a.circle('lumen',64,64,29,'lumen-view',False)
   a.path('coat','M40 30L65 21L90 35L106 61L96 90L67 107L37 96L22 68L27 45Z M40 30L43 55L64 68L88 54L90 35 M22 68L43 55M37 96L45 78L64 68L83 80L96 90 M65 21L64 42L88 54L106 61 M45 78L43 55M83 80L88 54M67 107L64 91L45 78M64 91L83 80','polygonal-clathrin-cage',3.5)
   a.circle('cargo',64,58,5,'cargo-cue',False)
 elif key=='extracellular_vesicle':
  if not alt:
   a.ellipse('membrane',65,64,42,39,'extracellular-vesicle');a.ellipse('lumen',65,64,34,31,'vesicle-lumen',False)
   a.path('cargo','M43 62q5-12 12 0t13 0t14 0','illustrative-rna-cargo',3)
   for i,(x,y) in enumerate([(49,80),(81,47),(79,83)]):a.circle('cargo',x,y,4.5,f'illustrative-cargo-{i}',False)
   for i,(x,y) in enumerate([(33,38),(94,41),(103,72),(40,96)]):a.path('membrane',f'M{x} {y}l-3-8',f'surface-component-{i}',4)
  else:
   a.shape('cytoplasm','<path d="M17 18H83V111H17Z"/>','cell-interior',False)
   a.shape('lumen','<path d="M90 45L83 45C67 39 43 44 39 63C34 88 61 99 82 84L90 84Z"/>','extracellularly-continuous-endosomal-lumen',False)
   a.shape('membrane','<path d="M82 18V45C67 39 43 44 39 63C34 88 61 99 82 84V111H89V77C68 96 43 86 46 65C48 47 72 44 89 56V18Z"/>','endosome-plasma-membrane-continuity')
   for i,(x,y,r) in enumerate([(58,61,7),(61,80,6),(105,65,8),(105,38,6)]):
    a.circle('membrane',x,y,r,f'luminal-or-released-vesicle-{i}',width=2);a.circle('cargo',x,y,2,f'cargo-{i}',False)
   arrow(a,79,65,91,65,'release-direction')
 elif key=='phagolysosome':
  a.shape('membrane','<path d="M28 39C43 20 80 18 97 36C114 53 108 85 89 100C70 114 38 105 25 86C14 69 16 52 28 39Z"/>','phagolysosomal-limiting-membrane')
  if not alt:
   a.rect('cargo',38,54,52,19,9,'engulfed-bacterial-cargo')
   a.path('outline','M50 60h10M68 67h9','cargo-interior',1.5)
  else:
   for i,(x,y,r) in enumerate([(47,54,11),(76,51,9),(66,78,12)]):a.circle('cargo',x,y,r,f'degrading-cargo-fragment-{i}',width=2)
  for i,(x,y) in enumerate([(36,42),(57,34),(88,45),(94,79),(40,88),(81,94)]):a.circle('enzymes',x,y,3,f'lysosomal-enzyme-cue-{i}',False)
 elif key in {'lamellipodium','filopodium'}:
  if key=='lamellipodium':
   if not alt:
    a.shape('cytoplasm','<path d="M21 86Q13 69 28 56L55 37Q72 15 93 21Q114 30 109 52Q109 66 94 76L77 95Q47 116 21 97Z"/>','migrating-cell-body')
    a.shape('membrane','<path d="M52 39Q72 16 93 21Q113 28 109 51L94 65Q91 42 68 43Z"/>','broad-lamellipodial-sheet',False)
    a.ellipse('nucleus',46,77,17,14,'nucleus')
    branches=[]
    a.path('actin','M68 44L80 29M73 37L69 33M79 50L93 32M85 42L93 43M92 56L104 43M97 50L104 54','leading-edge-branched-actin',2.2)
   else:
    a.shape('cytoplasm','<path d="M17 98V57Q64 10 111 38V98Z"/>','leading-edge-sheet')
    a.path('membrane','M18 57Q62 12 111 38','leading-membrane',6)
    branches=[(30,86,45,45),(48,89,64,35),(70,91,82,34),(91,88,104,44)]
   for i,(x,y,u,v) in enumerate(branches):
    a.path('actin',f'M{x} {y}L{u} {v}M{x+(u-x)*.45:.2f} {y+(v-y)*.45:.2f}l-12-6M{x+(u-x)*.68:.2f} {y+(v-y)*.68:.2f}l8-4',f'branched-actin-{i}',2.2)
  else:
   if not alt:
    a.shape('cytoplasm','<path d="M20 98Q15 73 32 58Q48 43 64 55Q73 63 79 59L104 28Q110 21 114 28Q117 32 110 40L84 73Q88 93 69 105Q43 115 20 98Z"/>','cell-with-filopodium')
    a.ellipse('nucleus',43,85,14,11,'nucleus')
    a.path('actin','M62 87L108 33M67 90L111 36M58 84L105 30','parallel-actin-bundle',2)
   else:
    a.shape('cytoplasm','<path d="M17 104V82H49V29Q49 16 62 16Q75 16 75 29V82H111V104Z"/>','filopodial-membrane-protrusion')
    a.path('actin','M55 98V32M62 98V27M69 98V32','parallel-actin-filaments',2.8)
    for i,y in enumerate([43,57,71,85]):a.path('actin',f'M54 {y}h16',f'actin-bundle-crosslink-{i}',2)
 elif key=='necrotic_cell':
  if not alt:
   cell(a,'swollen',True);a.ellipse('nucleus',54,65,20,19,'swollen-nucleus')
   for i,(x,y,r) in enumerate([(33,46,5),(80,39,7),(85,88,7)]):a.circle('lumen',x,y,r,f'vacuolization-cue-{i}',width=1.6)
   for i,(x,y) in enumerate([(114,55),(112,87),(97,110)]):a.circle('debris',x,y,3.5,f'released-content-{i}',False)
  else:
   a.shape('cytoplasm','<path d="M31 29Q66 15 91 33L82 45L100 51L88 64L98 84L80 85L79 104Q47 118 27 87L36 76L20 64L33 55L22 42Z"/>','disintegrating-cell-remnant')
   for i,(x,y,r) in enumerate([(52,56,13),(63,80,10),(104,100,5),(108,41,4),(19,100,4)]):a.circle('debris' if i>1 else 'nucleus',x,y,r,f'fragment-{i}',width=2)
 elif key=='ferroptotic_cell':
  cell(a);a.ellipse('nucleus',53,66,18,19,'nucleus')
  for i,(x,y) in enumerate([(39,27),(77,25),(103,53),(97,85),(69,106),(26,91),(19,61)]):
   a.path('lipid_damage',f'M{x-4} {y-3}l4 6 4-6',f'lipid-peroxidation-cue-{i}',3.4)
  if not alt:
   mini_mito(a,76,57,19,9,'compact-mitochondrion-a',1);mini_mito(a,44,91,18,9,'compact-mitochondrion-b',1)
  else:
   mini_mito(a,72,48,25,12,'mitochondrial-detail-a',1);mini_mito(a,65,83,24,11,'mitochondrial-detail-b',1)
   a.path('lipid_damage','M77 45l3-8 4 5M91 78l5-7','mitochondrial-damage-cues',2.7)
 elif key=='pyroptotic_cell':
  cell(a,'swollen',alt);a.ellipse('nucleus',56,64,18,17,'nucleus')
  for i,(x,y) in enumerate([(30,34),(82,27),(106,65),(70,107),(20,68)]):
   a.circle('gasdermin',x,y,6,f'gasdermin-pore-ring-{i}',width=1.8);a.circle('lumen',x,y,2.8,f'gasdermin-pore-opening-{i}',False)
  if alt:
   for i,(x,y) in enumerate([(113,50),(115,89),(99,109)]):a.circle('cargo',x,y,3.4,f'released-content-{i}',False)
  else:
   a.circle('gasdermin',82,83,6,'illustrative-inflammasome-cue',False)
 elif key=='necroptotic_cell':
  cell(a,'irregular',alt);a.ellipse('nucleus',58,61,18,19,'nucleus')
  for i,(x,y) in enumerate([(33,31),(87,29),(106,67),(77,105),(21,75)]):
   a.shape('mlkl',f'<path d="M{x-7} {y+4}l3-9 4 4 4-4 3 9-7 3Z"/>',f'membrane-associated-mlkl-{i}',width=1.7)
  if alt:
   for i,(x,y) in enumerate([(113,48),(112,91),(39,112)]):a.circle('cargo',x,y,3.5,f'released-content-{i}',False)
  else:
   a.circle('lumen',78,84,8,'swelling-vacuole',width=1.6)
 elif key=='anoikis':
  a.path('matrix','M17 105H111M20 113H108','extracellular-matrix',4)
  if not alt:
   a.shape('cytoplasm','<path d="M32 58Q24 34 42 26Q59 16 77 28Q96 39 86 59Q82 78 63 77Q41 80 32 58Z"/>','detached-cell')
   a.shape('chromatin','<path d="M42 44q9-11 17 0v14q-10 7-17-2Z M67 37q13 1 12 13q-7 9-14 2Z"/>','condensing-nuclear-fragments',width=2)
   a.path('adhesion','M43 86v10M76 85v11','disengaged-attachment-cues',3)
   arrow(a,99,91,99,74,'detachment-direction')
  else:
   a.shape('cytoplasm','<path d="M35 36Q43 19 64 24Q81 17 91 34Q104 41 94 56Q95 72 78 75Q62 88 49 76Q29 77 29 60Q18 45 35 36Z"/>','detached-blebbing-cell')
   for i,(x,y,r) in enumerate([(48,43,9),(72,40,8),(64,65,8)]):a.circle('chromatin',x,y,r,f'condensed-chromatin-{i}',width=1.8)
   a.circle('cytoplasm',100,82,7,'apoptotic-body');a.circle('chromatin',100,82,3,'body-chromatin',False)
   a.path('adhesion','M35 92v6M62 91v7','lost-matrix-attachment-cues',3)
 elif key=='dna_damage_foci':
  nucleus(a,inner=False)
  for i,(x,y) in enumerate([(41,42),(75,46),(84,75),(47,83)]):a.path('chromatin',f'M{x-5} {y}q4-7 8 0q4 7 8 0',f'chromatin-fiber-{i}',2)
  positions=[(43,47),(77,69),(55,82),(82,42),(34,68)] if not alt else [(48,54),(55,51),(60,58),(52,65),(77,77),(82,72)]
  for i,(x,y) in enumerate(positions):a.circle('foci',x,y,3.5 if not alt else 4.2,f'damage-response-focus-{i}',False)
 elif key=='replication_stress':
  if not alt:
   a.path('parent_dna','M17 57H55L103 24M17 68H55L103 103','parental-fork-strands',3.5)
   a.path('nascent_dna','M65 58L104 33M65 73L102 94','nascent-strands',3.5)
   for i in range(5):a.path('outline',f'M{20+i*7} 59v7',f'double-strand-rung-{i}',1.5)
   a.shape('stress_site','<path d="M57 40l8-8 8 8-8 8Z"/>','fork-obstacle',width=1.8)
   a.path('stress_site','M62 47l-6 10','stall-site',2.5)
  else:
   a.path('parent_dna','M16 57H58L100 24M16 69H58L101 103','parental-fork-strands',3.5)
   a.path('nascent_dna','M68 53L102 32M68 76L101 95M60 59L87 59M60 67L87 67','reversed-new-dna-arm',3.5)
   for i in range(4):a.path('outline',f'M{64+i*6} 60v6',f'reversed-arm-rung-{i}',1.5)
   a.circle('stress_site',57,63,5,'reversed-fork-junction',False)
 elif key=='er_stress_upr':
  a.shape('er_membrane','<path d="M18 28Q64 20 110 28V88Q64 80 18 88Z"/>','er-cisterna')
  a.shape('lumen','<path d="M22 35Q64 27 106 35V79Q64 71 22 79Z"/>','er-lumen',False)
  for i,(x,y) in enumerate([(31,47),(55,37),(75,55),(44,66),(91,39)]):a.path('unfolded_protein',f'M{x-4} {y}q-1-8 5-6t5 8q-2 6 5 3',f'unfolded-protein-{i}',2.5)
  if not alt:
   a.path('stress_sensor','M67 79V96M76 79V96','stress-sensor-pair',5)
   a.circle('stress_sensor',67,103,5,'sensor-cytosolic-domain-a');a.circle('stress_sensor',76,103,5,'sensor-cytosolic-domain-b')
  else:
   for i,x in enumerate([44,58,72,86]):
    a.path('stress_sensor',f'M{x} 79V97',f'clustered-sensor-{i}',4.2)
    a.circle('stress_sensor',x,101,5,f'clustered-cytosolic-domain-{i}',width=1.6)
   arrow(a,100,93,100,111,'illustrative-downstream-signal')
 elif key in {'mitochondrial_fission','mitochondrial_fusion'}:
  if key=='mitochondrial_fission' and not alt:
   a.shape('mitochondria','<path d="M24 45Q12 52 19 71Q27 89 45 82Q57 76 64 77Q78 90 99 80Q117 70 108 50Q99 35 81 45Q69 53 64 51Q45 34 24 45Z"/>','constricted-mitochondrion')
   for i,(x,y) in enumerate([(29,52),(44,56),(82,55),(97,50)]):a.path('cristae',f'M{x} {y}l-3 13 7 3',f'crista-{i}',2.4)
   a.add('division_ring','<ellipse cx="64" cy="64" rx="6" ry="19"/>','constriction-ring','stroke',3.5)
   a.path('outline','M63 46Q73 64 63 82','ring-front-contour',2)
  elif key=='mitochondrial_fission':
   mini_mito(a,16,34,42,25,'daughter-mitochondrion-a',3);mini_mito(a,73,72,39,25,'daughter-mitochondrion-b',3)
   a.path('division_ring','M63 56l4-4M63 67l4 4','disassembly-cues',3)
  elif not alt:
   mini_mito(a,16,52,39,26,'approaching-mitochondrion-a',3);mini_mito(a,73,46,39,26,'approaching-mitochondrion-b',3)
   a.path('fusion_site','M56 58l8 6 8-6M56 71l8-7 8 7','contact-tethers',3)
   arrow(a,28,94,53,94,'approach-a');arrow(a,99,94,75,94,'approach-b')
  else:
   a.shape('mitochondria','<path d="M28 43Q13 47 18 66Q19 84 38 86Q52 87 64 76Q81 87 99 78Q116 69 110 52Q102 35 86 41Q73 45 64 51Q50 37 28 43Z"/>','joined-mitochondrion')
   a.path('cristae','M29 52l-2 18 9 4M45 53l-2 18 8 3M84 50l-3 18 9 3M100 49l-3 15','cristae',2.4)
   a.path('fusion_site','M59 53Q65 61 60 73M69 53Q64 61 69 73','joining-site-cue',2.3)
 else:raise KeyError(key)
 return a

def render_svg(key,form,title,description):return draw(key,form).svg(title,description)
def regions_for(key,form):return draw(key,form).regions()
