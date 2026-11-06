"""Action-alone paint cases for the existing public repaint entry point.

Fixtures are authored with visible controls and pointer/keyboard input. Only the
negative control has a synthetic isolated canvas. Model readers never paint.
"""
import base64,hashlib,json,io
from pathlib import Path
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
OBSERVER=(ROOT/'scripts/action-paint-observer.js').read_text(encoding='utf8')
MODEL="""ids=>ids.map(id=>{const o=FigureStudio.app.getObjectByIdForQa(id);return o?{
 id,type:o.type,fill:o.fill,stroke:o.stroke,width:o.width,height:o.height,strokeWidth:o.strokeWidth,
 matrix:[...o.calcTransformMatrix()],text:o.text,path:o.path,visible:o.visible!==false}:null})"""

async def frames(f):
    await f.evaluate('()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))')

def png(out,name,value):
    raw=base64.b64decode(value.split(',',1)[1]);path=out/name;path.write_bytes(raw)
    return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())

async def observe(q,f,page,row,out,name,ids,model,event,action,**options):
    visible_target=options.pop('visible_target',None)
    if name.startswith('compound-') and row.get('compoundIdentity'):
        identity=json.dumps(row['compoundIdentity'])
        model=f"const expected={identity},live=app.getLiveBooleanStateForQa();if(live.objectId!==expected.objectId || JSON.stringify(live.operandIds)!==JSON.stringify(expected.operandIds))return false;\n"+model
    config=dict(ids=ids,model=model,event=event,deadlineMs=250,diagnosticMs=1000,**options)
    armed=await f.evaluate(OBSERVER,config)
    await action()
    result=await f.evaluate('()=>window.__figureActionPaintObservation.done')
    record=dict(name=name,**result)
    record['beforePng']=png(out,name+'-before.png',record['beforePng'])
    record['afterPng']=png(out,name+'-after.png',record['afterPng'])
    row['actions'].append(record);q.write('report.json',q.R)
    if visible_target:
        # Artwork evidence is already frozen. Observe the existing deferred
        # Properties refresh separately, using the original action clock.
        agreement=await f.evaluate('''async ({expected,started})=>{
 const sample=()=>{const panel=document.getElementById('appearanceStructureInspector'),o=FigureStudio.app.getObjectByIdForQa(expected.id);
 const actual={title:panel?.querySelector('.asi-header strong')?.textContent?.trim(),kind:panel?.querySelector('[data-selection-context-kind]')?.dataset.selectionContextKind,inside:Boolean(panel?.querySelector('[data-context-action="exit-isolation"]')),activeId:FigureStudio.app.getSelectionStateForQa().activeObjectId};
 return {ms:performance.now()-started,actual,passed:actual.title===o?.name && actual.kind===expected.kind && actual.inside===expected.inside && actual.activeId===expected.id};};
 return await new Promise(resolve=>{const tick=()=>{const value=sample();if(value.passed || value.ms>250)resolve(value);else requestAnimationFrame(tick);};tick();});
}''',dict(expected=visible_target,started=result['requestedAt']))
        record['visibleTarget']=agreement;q.write('report.json',q.R)
        q.check(row['name'],name+' visible Properties identifies the same object and isolation state within250ms',agreement['passed'] and agreement['ms']<=250,agreement)
    # A screenshot follows the saved lower pixels and verdict. It cannot rescue it.
    intent=f'{name}: requested artwork and unchanged neighbors must be visible without a second action.'
    q.R['captures'].append(dict(case=row['name'],file=str((out/(name+'-page.png')).relative_to(q.OUT)),intent=intent))
    q.write('capture-intents.json',q.R['captures'])
    await page.screenshot(path=str(out/(name+'-page.png')))
    q.check(row['name'],name+' model completes and natural artwork paint is correct within250ms and stable',result['passed'],{
        k:result[k] for k in ['classification','modelCompleteMs','firstCorrectPaintMs','stablePaintMs','last']})
    return record

async def negative(q,browser,row):
    """Real browser with intentionally stale isolated canvas, never the editor."""
    context=await browser.new_context();page=await context.new_page()
    try:
        await page.set_content('''<canvas class="lower-canvas" width="200" height="100"></canvas><button id="mutate">Change model only</button>
<script>
const e=document.querySelector('canvas'),c=e.getContext('2d');c.fillStyle='#ffffff';c.fillRect(0,0,200,100);c.fillStyle='#277da8';c.fillRect(20,20,60,40);
const canvas={lowerCanvasEl:e,width:200,height:100,viewportTransform:[1,0,0,1,0,0]};
const o={figureId:'negative',type:'rect',width:60,height:40,fill:'#277da8',strokeWidth:0,canvas,calcTransformMatrix:()=>[1,0,0,1,50,40]};
window.FigureStudio={app:{getObjectByIdForQa:()=>o,getCanvasInteractionPerformanceForQa:()=>({}),getSelectionStateForQa:()=>({selectedIds:['negative']})}};
document.querySelector('button').onclick=()=>{o.fill='#bc6c25';};
</script>''')
        await page.evaluate(OBSERVER,dict(ids=['negative'],model="return rows[0].fill==='#bc6c25';",
            event=dict(type='click',selector='#mutate'),deadlineMs=250,diagnosticMs=350))
        await page.locator('#mutate').click();result=await page.evaluate('()=>window.__figureActionPaintObservation.done')
        result['beforePng']=png(q.OUT,'negative-before.png',result['beforePng'])
        result['afterPng']=png(q.OUT,'negative-after.png',result['afterPng'])
        row['negativeControl']=result
        q.check(row['name'],'Withheld artwork paint fails despite completed model',not result['passed'] and result['modelCompleteMs'] is not None and result['firstCorrectPaintMs'] is None and result['classification']=='STALE_OR_WRONG_PAINT',result['last'])
    finally:await context.close()

async def draw_rectangle(f,page,x,y,w,h):
    await f.locator('.tool-button[data-tool="rect"]').click()
    await f.locator('[role="menuitem"][data-tool="rect"]:visible').click()
    box=await f.locator('.upper-canvas').bounding_box()
    await page.mouse.move(box['x']+x,box['y']+y);await page.mouse.down()
    await page.mouse.move(box['x']+x+w,box['y']+y+h,steps=6);await page.mouse.up();await frames(f)
    owner=await f.evaluate('FigureStudio.app.getSelectionStateForQa().activeObjectId')
    if not owner:raise AssertionError('Real rectangle drawing did not select a new object')
    return owner

async def select(f,page,ids,fractions=None):
    await f.locator('.tool-button[data-tool="select"]').click()
    # A click within an existing ActiveSelection preserves that selection in
    # Fabric. Clear it with an actual blank-canvas click during fixture setup.
    await f.locator('.upper-canvas').click(position=dict(x=10,y=10))
    points=await f.evaluate("""([ids,fractions])=>{const c=document.querySelector('.upper-canvas'),r=c.getBoundingClientRect();
 return ids.map((id,i)=>{const o=FigureStudio.app.getObjectByIdForQa(id),v=o.canvas.viewportTransform,f=fractions?.[i]||[.5,.5];
 const scene=fabric.util.transformPoint({x:(f[0]-.5)*o.width,y:(f[1]-.5)*o.height},o.calcTransformMatrix()),p=fabric.util.transformPoint(scene,v);
 return {x:r.left+p.x*r.width/o.canvas.width,y:r.top+p.y*r.height/o.canvas.height};});}""",[ids,fractions])
    # Editor coordinates from getBoundingClientRect need the iframe origin.
    iframe=await f.frame_element();frame_box=await iframe.bounding_box()
    for i,p in enumerate(points):
        if i:await page.keyboard.down('Shift')
        await page.mouse.click(frame_box['x']+p['x'],frame_box['y']+p['y'])
        if i:await page.keyboard.up('Shift')
    await frames(f)
    actual=await f.evaluate('FigureStudio.app.getSelectionStateForQa().selectedIds')
    if set(actual)!=set(ids):raise AssertionError(f'Pointer selection target mismatch: {actual} vs {ids}')
    await f.wait_for_function("document.getElementById('selectionContextBar').dataset.selectionUiState==='complete'")

async def color_control(f,value,property='fill'):
    field=f.locator(f'[data-context-property="{property}"]:visible').first
    if not await field.count():field=f.locator('#fillInput' if property=='fill' else '#strokeInput')
    await field.evaluate('(e,v)=>{e.value=v;e.dispatchEvent(new Event("input",{bubbles:true}));e.dispatchEvent(new Event("change",{bubbles:true}));}',value)
    await frames(f)

async def action_case(q,browser,base,size,theme):
    name=f'action-{size[0]}x{size[1]}-{theme}';out=q.OUT/name;out.mkdir()
    row=dict(name=name,status='running',actions=[]);q.R['cases'].append(row)
    context=page=f=None
    try:
        context,page,f=await q.launch(browser,base,size,theme)
        await q.enter_current_document_async(f,kind='figure',preset='full-page',name='Action-alone artwork paint')
        await f.locator('[data-figure-layout-choice="advanced"]').click()
        a=await draw_rectangle(f,page,70,90,65,45);await color_control(f,'#277da8')
        b=await draw_rectangle(f,page,245,220,65,45);await color_control(f,'#bc6c25')
        neighbor=await draw_rectangle(f,page,330,370,60,45);await color_control(f,'#4f772d')
        ids=[a,b,neighbor]
        await select(f,page,[a,b])
        selector='[data-context-action="align-left"]'
        await observe(q,f,page,row,out,'align-left',ids,
            "return Math.abs((rows[0].matrix[4]-rows[0].width/2)-(rows[1].matrix[4]-rows[1].width/2))<1e-8 && JSON.stringify(rows[0])===JSON.stringify(before[0]) && Math.abs(before[0].matrix[4]-before[1].matrix[4])>50;",
            dict(type='click',selector=selector),lambda:f.locator(selector+':visible').first.click(),unchangedIds=[neighbor])
        await select(f,page,ids)
        selector='[data-context-action="distribute-vertical"]'
        await observe(q,f,page,row,out,'distribute-vertical',ids,
            """const top=o=>o.matrix[5]-o.height/2-o.strokeWidth/2,bottom=o=>o.matrix[5]+o.height/2+o.strokeWidth/2;
return Math.abs((top(rows[1])-bottom(rows[0]))-(top(rows[2])-bottom(rows[1])))<1e-8 &&
 JSON.stringify(rows[0])===JSON.stringify(before[0]) && JSON.stringify(rows[1])!==JSON.stringify(before[1]);""",
            dict(type='click',selector=selector),lambda:f.locator(selector+':visible').first.click(),unchangedIds=[neighbor])
        await select(f,page,[a,b])
        # Numeric rotation also reconstructs selection. The oracle uses all four
        # local corners and analytic interior/background tests, not cached bounds.
        field=f.locator('#appearanceStructureInspector [data-context-property="rotation"]')
        await field.fill('25')
        await observe(q,f,page,row,out,'multi-rotation',ids,
            "return rows.slice(0,2).every(o=>Math.abs(o.matrix[0]-Math.cos(25*Math.PI/180))<1e-8 && Math.abs(o.matrix[1]-Math.sin(25*Math.PI/180))<1e-8);",
            dict(type='keydown',key='Enter',selector='[data-context-property="rotation"]'),lambda:field.press('Enter'),unchangedIds=[neighbor])
        # Undo this rotation before the independent Delete sequence. Ordinary
        # history rounds reconstructed transforms; this case requires the exact
        # prior axis-aligned state, without borrowing PDF/Library tolerances.
        await f.locator('.upper-canvas').click(position=dict(x=10,y=10))
        await observe(q,f,page,row,out,'rotation-undo',ids,
            "return rows.slice(0,2).every(o=>o.matrix[0]===1 && o.matrix[1]===0 && o.matrix[2]===0 && o.matrix[3]===1);",
            dict(type='keydown',key='z',selector='body'),lambda:page.keyboard.press('Control+z'),unchangedIds=[neighbor])
        # Undo/Redo are actual keyboard commands after returning focus to canvas.
        await select(f,page,[a])
        selector='[data-context-property="fill"]'
        async def appearance():
            await f.locator(selector+':visible').first.evaluate('(e)=>{e.value="#d62828";e.dispatchEvent(new Event("change",{bubbles:true}));}')
        await observe(q,f,page,row,out,'fill',ids,"return rows[0].fill==='#d62828';",
            dict(type='change',selector=selector),appearance,unchangedIds=[b,neighbor])
        await select(f,page,[a])
        relative=f.locator('#appearanceStructureInspector [data-context-action="toggle-transform-relative"]')
        if await relative.get_attribute('aria-pressed')!='true':await relative.click()
        field=f.locator('#appearanceStructureInspector [data-context-property="x"]');await field.fill('.5')
        await observe(q,f,page,row,out,'numeric-relative-x',ids,
            "return rows[0].matrix[4]===before[0].matrix[4]+48 && rows[0].matrix.slice(0,4).every((x,i)=>x===before[0].matrix[i]);",
            dict(type='keydown',key='Enter',selector='[data-context-property="x"]'),lambda:field.press('Enter'),unchangedIds=[b,neighbor])
        await select(f,page,[a])
        async def keypress(key):await page.keyboard.press(key)
        await observe(q,f,page,row,out,'delete',ids,"return rows[0]===null && rows[1]!==null && rows[2]!==null;",
            dict(type='keydown',key='Delete',selector='body'),lambda:keypress('Delete'),unchangedIds=[b,neighbor])
        # Remaining neighbor anchors the observer's existing canvas when a is gone.
        await observe(q,f,page,row,out,'delete-undo',[b,neighbor,a],"return rows[2]!==null && rows[2].fill==='#d62828';",
            dict(type='keydown',key='z',selector='body'),lambda:keypress('Control+z'),unchangedIds=[b,neighbor])
        await observe(q,f,page,row,out,'delete-redo',[b,neighbor,a],"return rows[2]===null;",
            dict(type='keydown',key='y',selector='body'),lambda:keypress('Control+y'),unchangedIds=[b,neighbor])
        await select(f,page,[b])
        objects=await f.evaluate(MODEL,[b,neighbor]);shape,green=objects
        left=shape['matrix'][4]-shape['width']/2;right=left+shape['width'];top=shape['matrix'][5]-shape['height']/2
        fill=[int(shape['fill'][i:i+2],16) for i in [1,3,5]]
        protected=dict(x=green['matrix'][4],y=green['matrix'][5],rgb=[79,119,45])
        field=f.locator('#appearanceStructureInspector [data-context-property="strokeWidth"]');await field.fill('8')
        await observe(q,f,page,row,out,'stroke-width',[b,neighbor],
            "return rows[0].strokeWidth===8 && rows[0].width===before[0].width && rows[0].height===before[0].height && rows[0].matrix[4]===before[0].matrix[4]+3.5 && rows[0].matrix[5]===before[0].matrix[5]+3.5;",
            dict(type='keydown',key='Enter',selector='[data-context-property="strokeWidth"]'),lambda:field.press('Enter'),
            rectangles=False,probes=[dict(x=left+3,y=shape['matrix'][5],rgb=[38,50,61]),dict(x=left+20,y=shape['matrix'][5],rgb=fill),protected],unchangedIds=[neighbor])
        shape=(await f.evaluate(MODEL,[b]))[0]
        left=shape['matrix'][4]-shape['width']/2;right=left+shape['width'];top=shape['matrix'][5]-shape['height']/2
        await f.locator('.tool-button[data-tool="directSelect"]').click()
        handle=f.locator(f'.path-node-handle[data-object-id="{b}"][data-command-index="1"][data-handle-type="endpoint"]')
        # Handles are drawn over a canvas that owns native point hit testing.
        # Click the measured handle center through the real pointer surface.
        hb=await handle.bounding_box()
        await page.mouse.click(hb['x']+hb['width']/2,hb['y']+hb['height']/2);await frames(f)
        target=right-48
        field=f.locator('[data-context-property="anchorX"]:visible').first;await field.fill(str(target/96))
        model=f"""const vertices=r=>r.path.filter(s=>s.length===3).map(s=>({{x:r.matrix[0]*(s[1]-r.pathOffset.x)+r.matrix[2]*(s[2]-r.pathOffset.y)+r.matrix[4],y:r.matrix[1]*(s[1]-r.pathOffset.x)+r.matrix[3]*(s[2]-r.pathOffset.y)+r.matrix[5]}}));
const aa=vertices(before[0]),bb=vertices(rows[0]);
return aa.length===4 && bb.length===4 && Math.abs(bb[1].x-{target})<1e-8 && Math.abs(bb[1].y-aa[1].y)<1e-8 &&
 bb.every((p,i)=>i===1 || Math.abs(p.x-aa[i].x)<1e-8 && Math.abs(p.y-aa[i].y)<1e-8) &&
 ['fill','stroke','strokeWidth','type'].every(k=>rows[0][k]===before[0][k]) &&
 JSON.stringify(rows[0].path.map(p=>p[0]))===JSON.stringify(before[0].path.map(p=>p[0]));"""
        await observe(q,f,page,row,out,'path-anchor-coordinate',[b,neighbor],model,
            dict(type='keydown',key='Enter',selector='[data-context-property="anchorX"]'),lambda:field.press('Enter'),
            rectangles=False,probes=[dict(x=right-12,y=top+13,rgb=[255,255,255]),dict(x=left+18,y=top+shape['height']*.7,rgb=fill),protected],unchangedIds=[neighbor])
        await select(f,page,[b,neighbor])
        retained=[dict(x=right-12,y=top+13,rgb=[255,255,255]),dict(x=left+18,y=top+shape['height']*.7,rgb=fill),protected]
        await observe(q,f,page,row,out,'group-keyboard',[b,neighbor],
            "const a=app.getObjectByIdForQa(rows[0].id),b=app.getObjectByIdForQa(rows[1].id);return a.group && a.group===b.group && a.group.type.toLowerCase()==='group' && app.getSelectionStateForQa().activeObjectId===a.group.figureId;",
            dict(type='keydown',key='g',selector='body'),lambda:page.keyboard.press('Control+g'),rectangles=False,probes=retained)
        group_id=await f.evaluate('FigureStudio.app.getSelectionStateForQa().activeObjectId')
        selector='[data-context-action="isolate-group"]'
        await observe(q,f,page,row,out,'group-enter-isolation',[b,neighbor],
            f"return app.getGroupIsolationStateForQa().rootId==={json.dumps(group_id)} && app.getGroupIsolationStateForQa().active && app.getSelectionStateForQa().activeObjectId===rows[0].id;",
            dict(type='click',selector=selector),lambda:f.locator(selector+':visible').first.click(),rectangles=False,probes=retained,
            visible_target=dict(id=b,kind='path',inside=True))
        selector='[data-context-property="fill"]'
        async def child_fill():
            await f.locator(selector+':visible').first.evaluate('(e)=>{e.value="#d62828";e.dispatchEvent(new Event("change",{bubbles:true}));}')
        red=[{**p,'rgb':[214,40,40] if p['rgb']==fill else p['rgb']} for p in retained]
        await observe(q,f,page,row,out,'group-child-fill',[b,neighbor],
            f"return rows[0].fill==='#d62828' && ['path','matrix'].every(k=>JSON.stringify(rows[0][k])===JSON.stringify(before[0][k])) && app.getObjectByIdForQa(rows[0].id).group.figureId==={json.dumps(group_id)};",
            dict(type='change',selector=selector),child_fill,rectangles=False,probes=red,unchangedIds=[neighbor])
        selector='[data-isolation-action="exit"]'
        await observe(q,f,page,row,out,'group-exit-isolation',[b,neighbor],
            f"return !app.getGroupIsolationStateForQa().active && app.getSelectionStateForQa().activeObjectId==={json.dumps(group_id)};",
            dict(type='click',selector=selector),lambda:f.locator(selector+':visible').click(),rectangles=False,probes=red,unchangedIds=[b,neighbor],
            visible_target=dict(id=group_id,kind='group',inside=False))
        row['status']='passed'
    except BaseException:
        row['status']='failed'
        if page:await page.screenshot(path=str(out/'failure.png'))
        raise
    finally:
        if context:await context.close()
        row['contextsClosed']=True;q.write('report.json',q.R)

async def run(q,browser,base,case):
    """One selected case per90s owner; release entry iterates separate owners."""
    size,theme=case.rsplit('-',1);width,height=map(int,size.split('x'))
    control=dict(name='observer-negative-control');q.R['cases'].append(control)
    await negative(q,browser,control)
    families={'ordinary':action_case,'structure':structure_case,'library':library_case,'pdf':pdf_case}
    await families[q.ARGS.action_paint_family](q,browser,base,(width,height),theme)

def overlap_probes(rows,mode):
    """Solid, independently expected regions of two axis-aligned source rectangles."""
    def inside(o,x,y,pad=12):
        return abs(x-o['matrix'][4])<o['width']/2-pad and abs(y-o['matrix'][5])<o['height']/2-pad
    a,b,n=rows;regions={}
    loX=min(o['matrix'][4]-o['width']/2 for o in [a,b])
    hiX=max(o['matrix'][4]+o['width']/2 for o in [a,b])
    loY=min(o['matrix'][5]-o['height']/2 for o in [a,b])
    hiY=max(o['matrix'][5]+o['height']/2 for o in [a,b])
    for x in range(round(loX)+13,round(hiX)-12,7):
        for y in range(round(loY)+13,round(hiY)-12,7):
            aa,bb=inside(a,x,y),inside(b,x,y)
            if (aa,bb)==(False,False):continue
            # Do not choose a point near either source boundary.
            if any(abs(abs(x-o['matrix'][4])-o['width']/2)<12 or abs(abs(y-o['matrix'][5])-o['height']/2)<12 for o in [a,b]):continue
            regions.setdefault((aa,bb),(x,y))
    if set(regions)!={(True,False),(False,True),(True,True)}:raise AssertionError(f'Overlap fixture lacks three solid regions: {regions}')
    probes=[]
    for (aa,bb),(x,y) in regions.items():
        color=(b['fill'] if mode=='unite' else '#ffffff') if mode!='operands' else b['fill'] if bb else a['fill']
        if mode=='intersect' and aa and bb:color=b['fill']
        probes.append(dict(x=x,y=y,rgb=[int(color[i:i+2],16) for i in [1,3,5]]))
    probes.append(dict(x=n['matrix'][4],y=n['matrix'][5],rgb=[79,119,45]))
    return probes

async def structure_case(q,browser,base,size,theme):
    name=f'structure-{size[0]}x{size[1]}-{theme}';out=q.OUT/name;out.mkdir()
    row=dict(name=name,status='running',actions=[]);q.R['cases'].append(row)
    context,page,f=await q.launch(browser,base,size,theme)
    try:
        await q.enter_current_document_async(f,kind='figure',preset='full-page',name='Compound natural paint')
        await f.locator('[data-figure-layout-choice="advanced"]').click()
        a=await draw_rectangle(f,page,70,90,130,115);await color_control(f,'#277da8')
        b=await draw_rectangle(f,page,145,150,130,115);await color_control(f,'#bc6c25')
        n=await draw_rectangle(f,page,340,380,55,40);await color_control(f,'#4f772d')
        ids=[a,b,n];source=await f.evaluate(MODEL,ids);row['fixtureRectangles']=source;q.write('report.json',q.R)
        await select(f,page,[a,b],fractions=[[.15,.15],[.85,.85]])
        selector='[data-context-action="make-live-boolean"]'
        await observe(q,f,page,row,out,'compound-create',ids,
            "return app.getLiveBooleanStateForQa().status==='ok' && !app.getLiveBooleanStateForQa().active;",
            dict(type='click',selector=selector),lambda:f.locator(selector+':visible').first.click(),
            rectangles=False,probes=overlap_probes(source,'unite'),unchangedIds=[n])
        compound=await f.evaluate('FigureStudio.app.getLiveBooleanStateForQa()')
        row['compoundIdentity']=dict(objectId=compound['objectId'],operandIds=compound['operandIds'])
        selector='[data-context-property="liveBooleanOperation"]'
        await observe(q,f,page,row,out,'compound-intersect',ids,
            "return app.getLiveBooleanStateForQa().operation==='intersect' && !app.getLiveBooleanStateForQa().committing;",
            dict(type='change',selector=selector),lambda:f.locator(selector+':visible').first.select_option('intersect'),
            rectangles=False,probes=overlap_probes(source,'intersect'),unchangedIds=[n])
        selector='[data-context-action="edit-live-boolean"]'
        await observe(q,f,page,row,out,'compound-edit-shapes',ids,
            "return app.getLiveBooleanStateForQa().active && app.getLiveBooleanStateForQa().operandVisibility.every(Boolean) && !app.getLiveBooleanStateForQa().resultVisible;",
            dict(type='click',selector=selector),lambda:f.locator(selector+':visible').first.click(),
            rectangles=False,probes=overlap_probes(source,'operands'),unchangedIds=[n])
        selector='[data-isolation-action="done"]'
        await observe(q,f,page,row,out,'compound-done',ids,
            "return !app.getLiveBooleanStateForQa().active && app.getLiveBooleanStateForQa().resultVisible;",
            dict(type='click',selector=selector),lambda:f.locator(selector+':visible').click(),
            rectangles=False,probes=overlap_probes(source,'intersect'),unchangedIds=[n])
        selector='[data-context-action="edit-live-boolean"]'
        await observe(q,f,page,row,out,'compound-edit-again',ids,
            "return app.getLiveBooleanStateForQa().active && app.getLiveBooleanStateForQa().operandVisibility.every(Boolean);",
            dict(type='click',selector=selector),lambda:f.locator(selector+':visible').first.click(),
            rectangles=False,probes=overlap_probes(source,'operands'),unchangedIds=[n])
        selector='[data-isolation-action="cancel"]'
        await observe(q,f,page,row,out,'compound-cancel',ids,
            "return !app.getLiveBooleanStateForQa().active && app.getLiveBooleanStateForQa().resultVisible;",
            dict(type='click',selector=selector),lambda:f.locator(selector+':visible').click(),
            rectangles=False,probes=overlap_probes(source,'intersect'),unchangedIds=[n])
        await live_text_action(q,f,page,row,out,n)
        row['status']='passed'
    except BaseException:
        row['status']='failed';await page.screenshot(path=str(out/'failure.png'));raise
    finally:
        await context.close();row['contextsClosed']=True;q.write('report.json',q.R)

async def live_text_action(q,f,page,row,out,neighbor):
    row['textViewport']=[]
    async def viewport(label):
        row['textViewport'].append(dict(label=label,outer=await page.evaluate('({x:scrollX,y:scrollY,height:innerHeight,scrollHeight:document.documentElement.scrollHeight,iframe:document.querySelector("iframe").getBoundingClientRect().toJSON()})'),inner=await f.evaluate('({x:scrollX,y:scrollY,height:innerHeight,scrollHeight:document.documentElement.scrollHeight,active:document.activeElement?.tagName,textarea:document.activeElement?.getBoundingClientRect().toJSON()})')))
        q.write('report.json',q.R)
    await viewport('before-text-tool')
    await f.locator('.tool-button[data-tool="text"]').click()
    await f.locator('[role="menuitem"][data-tool="text"]:visible').click()
    box=await f.locator('.upper-canvas').bounding_box()
    x=box['x']+box['width']*.12;y=box['y']+box['height']*.72
    await page.mouse.move(x,y);await page.mouse.down()
    await page.mouse.move(x+box['width']*.62,y+box['height']*.17,steps=6);await page.mouse.up()
    await frames(f)
    await viewport('after-text-draw')
    owner=await f.evaluate('FigureStudio.app.getSelectionStateForQa().activeObjectId')
    # Text intentionally uses its essentials strip; the generic shape strip's
    # complete state is not the readiness signal for this selection type.
    field=f.locator('#appearanceStructureInspector [data-context-property="fontSize"]')
    await field.wait_for(state='visible')
    await field.fill('48');await field.press('Tab');await frames(f)
    await viewport('after-font-change')
    await f.locator('[data-context-action="edit-text"]:visible').first.click()
    await viewport('after-edit-click')
    await page.keyboard.press('Control+a');await page.keyboard.type('MMMM')
    await f.wait_for_function("id=>FigureStudio.app.getObjectByIdForQa(id).text==='MMMM'",arg=owner)
    await page.keyboard.press('Home');await page.keyboard.press('ArrowRight')
    await page.keyboard.down('Shift');await page.keyboard.press('End');await page.keyboard.up('Shift');await frames(f)
    await viewport('after-type-selection')
    q.check(row['name'],'Live text keeps editor and host at their original scroll origin',all(v['inner']['x']==0 and v['inner']['y']==0 and v['outer']['x']==0 and v['outer']['y']==0 for v in row['textViewport']),row['textViewport'])
    lower=await f.evaluate(LOWER,owner)
    bounds=await f.evaluate("""id=>{const o=FigureStudio.app.getObjectByIdForQa(id);return {points:o.getCoords().map(p=>({x:p.x,y:p.y})),fill:o.fill};}""",owner)
    image=Image.open(io.BytesIO(base64.b64decode(lower['png'].split(',')[1]))).convert('RGB')
    v=lower['vpt'];assert v[1]==v[2]==0
    px=lambda x:round((v[0]*x+v[4])*lower['width']/lower['cw'])
    py=lambda y:round((v[3]*y+v[5])*lower['height']/lower['ch'])
    x0=max(3,min(px(p['x']) for p in bounds['points']));x1=min(image.width-3,max(px(p['x']) for p in bounds['points']))
    y0=max(3,min(py(p['y']) for p in bounds['points']));y1=min(image.height-3,max(py(p['y']) for p in bounds['points']))
    color=tuple(int(bounds['fill'][i:i+2],16) for i in [1,3,5])
    columns=[x for x in range(x0,x1) if any(image.getpixel((x,y))==color for y in range(y0,y1))]
    clusters=[]
    for x in columns:
        if clusters and x<=clusters[-1][-1]+1:clusters[-1].append(x)
        else:clusters.append([x])
    if len(clusters)!=4:raise AssertionError(f'Live text fixture requires four separated M glyphs, got{len(clusters)}')
    probes=[]
    for index,cluster in enumerate(clusters):
        points=[]
        for y in range(y0+2,y1-2):
            for x in cluster[2:-2]:
                if all(image.getpixel((x+dx,y+dy))==color for dx in range(-2,3) for dy in range(-2,3)):
                    points.append((x,y))
        if len(points)<3:raise AssertionError('Live glyph lacks meaningful solid stroke interior')
        stride=max(1,len(points)//3)
        for x,y in points[::stride][:3]:
            probes.append(dict(x=(x*lower['cw']/lower['width']-v[4])/v[0],
                y=(y*lower['ch']/lower['height']-v[5])/v[3],rgb=list(color) if index==0 else [255,255,255]))
    green=(await f.evaluate(MODEL,[neighbor]))[0]
    probes.append(dict(x=green['matrix'][4],y=green['matrix'][5],rgb=[79,119,45]))
    await observe(q,f,page,row,out,'live-text-delete-suffix',[owner,neighbor],
        "return rows[0].text==='M' && rows[0].isEditing && rows[0].fontSize===before[0].fontSize && rows[0].fontFamily===before[0].fontFamily && rows[0].width===before[0].width && JSON.stringify(rows[0].matrix)===JSON.stringify(before[0].matrix);",
        dict(type='keydown',key='Delete',selector='textarea'),lambda:page.keyboard.press('Delete'),
        rectangles=False,probes=probes,unchangedIds=[neighbor])

LOWER="""id=>{const o=FigureStudio.app.getObjectByIdForQa(id),c=o.canvas,e=c.lowerCanvasEl;
return {png:e.toDataURL('image/png'),width:e.width,height:e.height,cw:c.width,ch:c.height,vpt:[...c.viewportTransform]};}"""

def solid_probes(lower,old_color,new_color,limit=16):
    """Select actual uniform interior pixels; never infer paint from selection."""
    image=Image.open(io.BytesIO(base64.b64decode(lower['png'].split(',')[1]))).convert('RGB')
    old=tuple(int(old_color[i:i+2],16) for i in [1,3,5]);new=[int(new_color[i:i+2],16) for i in [1,3,5]]
    v=lower['vpt'];assert v[1]==v[2]==0
    points=[]
    for y in range(4,image.height-4,7):
        for x in range(4,image.width-4,7):
            if all(image.getpixel((x+dx,y+dy))==old for dx in range(-2,3) for dy in range(-2,3)):
                points.append(dict(x=(x*lower['cw']/lower['width']-v[4])/v[0],
                    y=(y*lower['ch']/lower['height']-v[5])/v[3],rgb=new))
    if len(points)<3:raise AssertionError(f'No meaningful solid interior coverage for {old_color}: {len(points)}')
    stride=max(1,len(points)//limit);return points[::stride][:limit]

async def library_case(q,browser,base,size,theme):
    name=f'library-{size[0]}x{size[1]}-{theme}';out=q.OUT/name;out.mkdir()
    row=dict(name=name,status='running',actions=[]);q.R['cases'].append(row)
    context,page,f=await q.launch(browser,base,size,theme)
    try:
        await q.enter_current_document_async(f,kind='figure',preset='full-page',name='Library part natural paint')
        await f.locator('[data-figure-layout-choice="advanced"]').click()
        if await f.locator('#figureStyleToggle').get_attribute('aria-pressed')!='true':await f.locator('#figureStyleToggle').click()
        await f.locator('[data-inspector-tab="properties"]').click();await q.library(f)
        owner=await q.insert(f,'core.cell.generic','Generic Eukaryotic Cell')
        await frames(f)
        meta=await f.evaluate('id=>FigureStudio.app.getObjectByIdForQa(id).scientificAssetMeta',owner)
        region=next(r for r in meta['editableColorRegions'] if r.get('paint','fill')=='fill' and r['id']!='outline')
        old=region['default'];selector=f'[data-asset-color-region="{region["id"]}"]'
        if old.lower()=='#277da8':raise AssertionError('Part-color fixture must request a different paint')
        before=await f.evaluate(q.native.STATE,[owner]);lower=await f.evaluate(LOWER,owner)
        probes=solid_probes(lower,old,'#277da8')
        protected=[]
        for other in meta['editableColorRegions']:
            value=other.get('default','')
            if other['id']!=region['id'] and value.lower()!=old.lower() and other.get('paint','fill')=='fill':
                try:protected+=solid_probes(lower,value,value,limit=3)
                except AssertionError:continue
        if not protected:raise AssertionError('Library fixture lacks independent unchanged-part probes')
        probes+=protected
        row['region']=region
        async def recolor():
            await f.locator(selector+':visible').evaluate('(e)=>{e.value="#277da8";e.dispatchEvent(new Event("change",{bubbles:true}));}')
        await observe(q,f,page,row,out,'library-part-color',[owner],
            f"return app.getObjectByIdForQa(rows[0].id).scientificAssetMeta.colorOverrides?.[{json.dumps(region['id'])}]?.toLowerCase()==='#277da8';",
            dict(type='change',selector=selector),recolor,rectangles=False,probes=probes)
        after=await f.evaluate(q.native.STATE,[owner])
        await f.locator('.upper-canvas').click(position=dict(x=10,y=10))
        restore=[{**p,'rgb':[int(old[i:i+2],16) for i in [1,3,5]]} for p in probes[:-len(protected)]]+protected
        undo=await observe(q,f,page,row,out,'library-part-undo',[owner],
            f"return app.getObjectByIdForQa(rows[0].id).scientificAssetMeta.colorOverrides?.[{json.dumps(region['id'])}]?.toLowerCase()!=='#277da8';",
            dict(type='keydown',key='z',selector='body'),lambda:page.keyboard.press('Control+z'),rectangles=False,probes=restore)
        actual=await f.evaluate(q.native.STATE,[owner])
        comparison=q.native.native_reconstruction_difference(q.native.geometry(before),q.native.geometry(actual))
        q.check(name,'Library Undo retains native identity, hierarchy, paths, paints and metadata',comparison['passed'],comparison)
        first=row['actions'][0]
        a=Image.open(first['beforePng']['path']).convert('RGB');b=Image.open(undo['afterPng']['path']).convert('RGB')
        q.check(name,'Library part Undo keeps the existing exact-pixel history protection',q.history_pixel_comparison(a,b,'first-part',comparison)['passed'])
        redo=await observe(q,f,page,row,out,'library-part-redo',[owner],
            f"return app.getObjectByIdForQa(rows[0].id).scientificAssetMeta.colorOverrides?.[{json.dumps(region['id'])}]?.toLowerCase()==='#277da8';",
            dict(type='keydown',key='y',selector='body'),lambda:page.keyboard.press('Control+y'),rectangles=False,probes=probes)
        actual=await f.evaluate(q.native.STATE,[owner]);comparison=q.native.native_reconstruction_difference(q.native.geometry(after),q.native.geometry(actual))
        q.check(name,'Library Redo retains native identity, hierarchy, paths, paints and metadata',comparison['passed'],comparison)
        a=Image.open(first['afterPng']['path']).convert('RGB');b=Image.open(redo['afterPng']['path']).convert('RGB')
        q.check(name,'Library part Redo keeps the existing exact-pixel history protection',q.history_pixel_comparison(a,b,'first-part',comparison)['passed'])
        row['status']='passed'
    finally:await context.close();row['contextsClosed']=True;q.write('report.json',q.R)

PDF_RAW_TREE="""id=>{
 const keys=['figureId','type','left','top','width','height','originX','originY','scaleX','scaleY','angle','skewX','skewY','flipX','flipY','transformMatrix','path','pathOffset','points','fill','stroke','strokeWidth','strokeUniform','fillRule','opacity','visible','globalCompositeOperation','absolutePositioned','inverted','text','styles','fontSize','fontFamily','fontWeight','fontStyle','textAlign','lineHeight','charSpacing','importMeta','source','figureStudioPdfMeta','figureStudioNativePdfMeta'];
 const visit=o=>({parentId:o.group?.figureId||null,values:Object.fromEntries(keys.filter(k=>o[k]!==undefined).map(k=>[k,structuredClone(o[k])])),clip:o.clipPath?visit(o.clipPath):null,children:(o.getObjects?.()||[]).map(visit)});
 return visit(FigureStudio.app.getObjectByIdForQa(id));
}"""

async def pdf_case(q,browser,base,size,theme):
    fixture=q.ARGS.pdf_fixture
    if not fixture or not fixture.is_file():raise ValueError('The PDF family requires --pdf-fixture with an unchanged genuine input.')
    original=fixture.read_bytes();digest=hashlib.sha256(original).hexdigest()
    name=f'pdf-{size[0]}x{size[1]}-{theme}';out=q.OUT/name;out.mkdir()
    row=dict(name=name,status='running',actions=[],source=dict(path=str(fixture.resolve()),bytes=len(original),sha256=digest));q.R['cases'].append(row)
    context,page,f=await q.launch(browser,base,size,theme)
    try:
        await q.enter_current_document_async(f,kind='figure',preset='full-page',name='Imported PDF natural paint')
        await f.locator('[data-menu="file"] > .menu-trigger').click()
        await f.locator('[data-menu="file"] [data-command="new-project"]').click()
        async with page.expect_file_chooser() as pending:await f.locator('#openArtworkDocumentBtn:visible').click()
        chooser=await pending.value
        if await chooser.element.get_attribute('id')!='openArtworkDocumentInput':raise AssertionError('Wrong public artwork input')
        await chooser.set_files(fixture)
        await f.locator('#importPlacementReview:not([hidden])').wait_for(timeout=30000)
        await f.locator('#pdfEntryModeSelect:visible').select_option('editable')
        await f.locator('#pdfPageModeSelect:visible').select_option('custom')
        await f.locator('#pdfPageRangeInput:visible').fill('1')
        await f.locator('#importPlacementCenterBtn:visible').click()
        await f.locator('#importPlacementReview').wait_for(state='hidden',timeout=30000)
        # These original completion limits are independent of action paint.
        await f.wait_for_function('FigureStudio.app.getBrowserSessionState().ready && !FigureStudio.app.getBrowserSessionState().busy',timeout=30000)
        await frames(f);await f.locator('[data-figure-layout-choice="advanced"]').click();await frames(f)
        owner=await f.evaluate('FigureStudio.app.getSelectionStateForQa().activeObjectId')
        if not owner:raise AssertionError('Opened PDF root is not selected')
        # Give the genuine source page room for the requested whole-figure move.
        # This is visible authoring setup before the observer is armed; neither
        # the movement nor the natural-paint deadline is changed.
        await f.locator('#figureDocumentSetupBtn').click()
        width=f.locator('.document-review-dialog #documentArtboardWidthInput:visible')
        original_width=float(await width.input_value())
        await width.fill(str(original_width+1))
        await width.press('Tab')
        await f.locator('.document-review-dialog .document-review-close').click()
        await f.locator('#fitBtn').click()
        await frames(f)
        row['movementRoom']=dict(publicControl='Document setup / Width',originalWidthIn=original_width,
            requestedWidthIn=original_width+1,requestedRootTranslationPx=48,publicFitBeforeObservation=True)
        q.check(name,'Page is widened before observation and original imported root remains selected',
            await f.evaluate('id=>FigureStudio.app.getSelectionStateForQa().activeObjectId===id',owner))
        raw_before=await f.evaluate(PDF_RAW_TREE,owner)
        (out/'pdf-raw-before.json').write_text(json.dumps(raw_before,indent=2),encoding='utf8')
        lower=await f.evaluate(LOWER,owner);image=Image.open(io.BytesIO(base64.b64decode(lower['png'].split(',')[1]))).convert('RGB')
        v=lower['vpt'];assert v[1]==v[2]==0
        dx=48;shift=round(dx*v[0]*lower['width']/lower['cw']);probes=[]
        for y in range(8,image.height-8,17):
            for x in range(shift+8,image.width-shift-8,17):
                color=image.getpixel((x,y))
                if color!=(255,255,255) and all(image.getpixel((x+xx,y+yy))==color for xx in range(-2,3) for yy in range(-2,3)):
                    probes.append(dict(x=(x*lower['cw']/lower['width']-v[4])/v[0]+dx,y=(y*lower['ch']/lower['height']-v[5])/v[3],rgb=list(color)))
                    if all(image.getpixel((x-shift+xx,y+yy))==(255,255,255) for xx in range(-2,3) for yy in range(-2,3)):
                        probes.append(dict(x=(x*lower['cw']/lower['width']-v[4])/v[0],y=(y*lower['ch']/lower['height']-v[5])/v[3],rgb=[255,255,255]))
                if len(probes)>=40:break
            if len(probes)>=40:break
        if len(probes)<4 or not any(p['rgb']==[255,255,255] for p in probes):raise AssertionError('PDF fixture lacks both painted destination and cleared-old-region probes')
        relative=f.locator('#appearanceStructureInspector [data-context-action="toggle-transform-relative"]')
        if await relative.get_attribute('aria-pressed')!='true':await relative.click()
        selector='#appearanceStructureInspector [data-context-property="x"]'
        field=f.locator(selector);await field.fill('.5')
        await observe(q,f,page,row,out,'pdf-numeric-move',[owner],
            "return Math.abs(rows[0].matrix[4]-before[0].matrix[4]-48)<1e-8 && rows[0].matrix.slice(0,4).every((x,i)=>x===before[0].matrix[i]);",
            dict(type='keydown',key='Enter',selector=selector),lambda:field.press('Enter'),rectangles=False,probes=probes)
        raw_after=await f.evaluate(PDF_RAW_TREE,owner)
        (out/'pdf-raw-after.json').write_text(json.dumps(raw_after,indent=2),encoding='utf8')
        expected=json.loads(json.dumps(raw_before));expected['values']['left']+=48
        q.check(name,'PDF local numbers, ordered membership, parents, clips, paths, text and paints stay exact except requested root translation',raw_after==expected)
        q.check(name,'Genuine PDF source remains unchanged',hashlib.sha256(fixture.read_bytes()).hexdigest()==digest)
        row['status']='passed'
    finally:await context.close();row['contextsClosed']=True;q.write('report.json',q.R)
