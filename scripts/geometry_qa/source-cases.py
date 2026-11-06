"""Same geometry workflow on an actual Library compound and genuine scientific-PDF leaf."""
import argparse
import importlib.util
from pathlib import Path

AREA=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('geometry_qualified',AREA/'qualify.py')
q=importlib.util.module_from_spec(spec);spec.loader.exec_module(q)
probe,ROOT,m=q.probe,q.ROOT,q.m


def contour_points(record):
    result={};contour=-1;ordinal=-1;points=probe.world(record)
    for index,command in enumerate(record['path'] or []):
        if command[0]=='M':contour+=1;ordinal=0
        else:ordinal+=1
        for operand in range(1,len(command)-1,2):result[(contour,ordinal,operand)]=points[(index,operand)]
    return result


class SourceGeometry(q.Geometry):
    async def capture(self,name,intent):
        subject='the actual bacteriophage tail compound' if self.part=='library' else 'the genuine Figure2 bar path'
        if name.startswith('zoom-'):
            intent=f'{subject} is shown at the declared projected edge size. Compact native anchors and the visible segment remain the editing targets; other scientific artwork supplies context.'
        elif name.endswith('-escaped-held'):
            intent=f'Escape alone restores {subject} and its selected geometry while the pointer remains held, without a click, Fit or forced render.'
        elif name.endswith('-held'):
            intent=f'The trusted pointer edits the selected native segment, anchor or tangent of {subject}. Other contours and nearby scientific artwork remain fixed. Underlying parts can remain visible through the real compound opening.'
        elif name=='geometry-cold-open':
            intent=f'A genuinely new browser opens the actual saved scene containing {subject}, before navigation, Fit or inspection. This first view records natural file restoration; later captures show continued focused editing.'
        elif name in ['completed-redo','geometry-continued-redo']:
            intent=f'{subject} remains native and editable after completed Undo/Redo'+(' and fresh-process continued editing.' if name=='geometry-continued-redo' else '.')+' The full target and its compact editing controls are visible.'
        await super().capture(name,intent)

    async def prepare_compound(self):
        self.part=probe.ARGS.part;self.doc='assets' if self.part=='library' else 'pdf'
        if self.part=='library':
            self.leaf_id='path-mw3d1boz-151';self.parents=['scientificAsset-mw3d1boz-147']
            self.root_id=self.parents[0];self.seam=9;self.anchor_command=8;self.contour_start=5
            self.hole_point=[64,80];self.border_point=[54,80]
            file=probe.ARGS.asset_fixture
        else:
            self.leaf_id='path-mvwsd6uk-286';self.parents=['pdf-mvwsd6u2-9'];self.root_id=self.parents[0]
            self.seam=4;self.anchor_command=3;self.contour_start=3
            self.hole_point=None;self.border_point=None
            file=probe.ARGS.pdf_fixture
        self.row['sourceCase']={'kind':self.part,'file':str(file),'target':self.leaf_id,'editedContour':1,
                               'newSyntheticFixtureAdded':False,'scope':'Existing actual saved native source, not a new import or Library reinsertion'}
        self.context=await self.open_surface(self.browser,file)
        await self.capture('source-open','The retained actual scientific artwork opens intact before navigation or editing; its original native source objects remain available.')
        await self.reach_target()
        selector=f'.path-node-handle[data-object-id="{self.leaf_id}"][data-command-index="{self.contour_start}"][data-handle-type="endpoint"]'
        self.require('Public controls reach the declared native source anchor',await self.surface.locator(selector).count()==1)
        box=await self.surface.locator(selector).bounding_box();await self.page.mouse.click(box['x']+box['width']/2,box['y']+box['height']/2);await self.settled()
        await self.capture('source-target','The actual native compound or scientific bar is focused before geometry edits. Existing contours and compact point controls are visible in their original scientific context.')

    async def reach_target(self):
        if self.part=='library':return await super().reach_target()
        await self.surface.locator('[data-figure-layout-choice="advanced"]').click()
        await self.surface.locator('[data-menu="view"] > .menu-trigger').click();await self.surface.locator('[data-command="fit-screen"]').first.click();await self.settled()
        target=await self.surface.evaluate('id=>FigureStudio.app.getObjectByIdForQa(id).getBoundingRect()',self.leaf_id)
        await self.surface.locator('#viewport').focus();await self.page.keyboard.press('z')
        await m.base.HELPERS.drag_scene(self.surface,(target['left']-15,target['top']-15),(target['left']+target['width']+15,target['top']+target['height']+15))
        await self.page.keyboard.press('a');await self.settled()
        if self.row.get('warmBrowserClosed'):
            points=await self.surface.evaluate('''id=>{const o=FigureStudio.app.getObjectByIdForQa(id),b=o.getBoundingRect(),out=[];
              for(const y of [.5,.25,.75,.1,.9])for(const x of [.5,.25,.75,.1,.9]){const p={x:b.left+b.width*x,y:b.top+b.height*y};
                if(FigureStudioPdfPaintHitTest.hitObject(o,p,{fabric:window.fabric,tolerance:0}))out.push(p);}return out;}''',self.leaf_id)
            self.require('The cold edited leaf has an actual painted interior point',bool(points),points)
            point=points[0]
            self.row['coldPointerTarget']={'world':point,'paintedCandidates':points,'policy':'Public click at the first zero-tolerance native painted interior point; no selection setter'}
        else:
            point=await self.surface.evaluate('''id=>{const o=FigureStudio.app.getObjectByIdForQa(id),p=o.path;
              const x=(p[3][1]+p[5][1])/2-o.pathOffset.x,y=(p[3][2]+p[5][2])/2-o.pathOffset.y;
              const q=fabric.util.transformPoint(new fabric.Point(x,y),o.calcTransformMatrix());return{x:q.x,y:q.y};}''',self.leaf_id)
        client=await m.base.HELPERS.canvas_scene_point(self.surface,point['x'],point['y'])
        await self.page.mouse.click(client['x'],client['y']);await self.settled()
        state=await self.state('pdf-public-target')
        self.require(('A cold painted-interior click' if self.row.get('warmBrowserClosed') else 'A genuine painted-bar click')+' targets its original native leaf',state['direct']['objectIds']==[self.leaf_id],state['direct']['objectIds'])
        await self.surface.evaluate(m.WITNESS)
        await self.ensure_target_frame()

    def stationary(self,name,before,after):
        old={o['id']:o for o in before['inventory']['leaves']};errors=[]
        self.require(name+' preserves the complete native leaf inventory',set(old)=={o['id'] for o in after['inventory']['leaves']})
        for o in after['inventory']['leaves']:
            if o['id']==self.leaf_id:continue
            prior=old[o['id']]
            if any(o.get(k)!=prior.get(k) for k in ['path','text','parent','fill','stroke','strokeWidth']):errors.append({'id':o['id'],'reason':'source content'})
            a,b=probe.world(prior),probe.world(o)
            if a.keys()!=b.keys() or any(max(abs(x-y) for x,y in zip(a[k],b[k]))>1e-6 for k in a):errors.append({'id':o['id'],'reason':'world operands'})
            if not prior['path'] and max(abs(x-y) for x,y in zip(prior['matrix'],o['matrix']))>1e-6:errors.append({'id':o['id'],'reason':'text/shape pose'})
        self.require(name+' preserves all scientific neighbors, text and geometry',not errors,errors)
        current=next(o for o in after['inventory']['leaves'] if o['id']==self.leaf_id)
        a,b=contour_points(old[self.leaf_id]),contour_points(current)
        self.require(name+' preserves every operand of every unedited contour',{k for k in a if k[0]!=1}=={k for k in b if k[0]!=1} and all(max(abs(x-y) for x,y in zip(v,b[k]))<1e-6 for k,v in a.items() if k[0]!=1))
        self.require(name+' retains the original fill rule',before['target']['fillRule']==after['target']['fillRule'])
        if self.part=='library':self.require(name+' retains the actual evenodd opening and painted side',not after['target']['holeFilled'] and after['target']['borderFilled'])


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,required=True);p.add_argument('--output-dir',type=Path,required=True);p.add_argument('--expected-app-sha256',required=True)
    p.add_argument('--base-runtime',type=Path);p.add_argument('--viewport',default='1440x1000');p.add_argument('--theme',default='light')
    p.add_argument('--part',choices=['library','pdf'],required=True)
    p.add_argument('--pdf-fixture',type=Path,default=ROOT/'qa_artifacts/selection-reliability-20261105/regression-accepted/1280x800-light/1280x800-light/subset-second.fsfigure')
    p.add_argument('--asset-fixture',type=Path,default=ROOT/'qa_artifacts/selection-reliability-20261105/assets-accepted/1440x1000-light/1440x1000-light/assets-second.fsfigure')
    probe.execute(p.parse_args(),SourceGeometry)
