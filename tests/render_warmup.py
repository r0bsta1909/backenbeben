"""Two real clients and two host-authoritative hits: stain shaders must warm before join.

WebGL wrappers add overhead. Slow calls are diagnostic, not clean frame benchmarks.
"""
import asyncio,json,os
from pathlib import Path
from playwright.async_api import async_playwright
ROOT=Path(__file__).resolve().parents[1]
URL='http://localhost:'+os.environ.get('BACKENBEBEN_TEST_PORT','8912')
PROBE=r'''(()=>{
 const phase=()=>{try{return JSON.parse(window.renderState||'{}').state?.phase||'lobby'}catch{return 'unknown'}};
 window.gpuProbe={calls:{},slow:[],longFrames:[],programs:[]};
 const sources=new WeakMap(),attached=new WeakMap(),ids=new WeakMap();let next=0;
 for(const key of ['shaderSource','attachShader']){
 const original=WebGL2RenderingContext.prototype[key];WebGL2RenderingContext.prototype[key]=function(...a){
 if(key==='shaderSource')sources.set(a[0],a[1]);else{const list=attached.get(a[0])||[];list.push(a[1]);attached.set(a[0],list)}
 return original.apply(this,a);};}
 const programInfo=p=>{if(!p)return null;if(!ids.has(p)){ids.set(p,++next);gpuProbe.programs.push({id:next,phase:phase(),ready:window.gameReady===true,stain:(attached.get(p)||[]).some(s=>(sources.get(s)||'').includes('m_rim='))})}return ids.get(p)};
 for(const key of ['compileShader','linkProgram','getProgramParameter','getShaderParameter','texImage2D','texSubImage2D','bufferData','bufferSubData']){
  const original=WebGL2RenderingContext.prototype[key];
  WebGL2RenderingContext.prototype[key]=function(...args){
   const program=key==='linkProgram'||key==='getProgramParameter'?programInfo(args[0]):null;const start=performance.now();const result=original.apply(this,args);const ms=performance.now()-start;
   if(key==='getProgramParameter'&&args[1]===this.LINK_STATUS){const info=gpuProbe.programs[program-1];if(info.checkedReady===undefined)info.checkedReady=window.gameReady===true;}
   const p=phase(),name=p+'/'+key;const data=gpuProbe.calls[name]||(gpuProbe.calls[name]={count:0,total:0,max:0});
   data.count++;data.total+=ms;data.max=Math.max(data.max,ms);
   if(ms>4)gpuProbe.slow.push({phase:p,key,start,ms,program});return result;
  };
 }
 let last=0;
 function tick(t){if(last&&t-last>50)gpuProbe.longFrames.push({phase:phase(),start:last,ms:t-last});last=t;requestAnimationFrame(tick)}
 requestAnimationFrame(tick);
 window.profileCPU=true;
})()'''

async def main():
 report={'errors':[],'limits':'WebGL-call wrapper overhead; timings include possible driver stalls, not pure GPU duration','hits':[]}
 async with async_playwright() as p:
  browser=await p.chromium.launch(executable_path=str(ROOT/'tools/playwright-browsers/chromium-1243/chrome-win64/chrome.exe'),headless=True,
    args=['--disable-background-timer-throttling','--disable-renderer-backgrounding','--disable-backgrounding-occluded-windows'])
  pages=[]
  try:
   for _ in range(2):
    c=await browser.new_context(viewport={'width':1920,'height':1080});await c.add_init_script(PROBE)
    page=await c.new_page();page.on('pageerror',lambda e:report['errors'].append(str(e)));page.on('console',lambda m:report['errors'].append(m.text) if m.type=='error' else None);await page.goto(URL);await page.wait_for_function('window.gameReady',timeout=90000);pages.append(page)
   for page in pages:await page.locator('#duel').click()
   for turn in range(2):
    await pages[0].wait_for_function('state?.phase==="aim"',timeout=20000)
    seat=await pages[0].evaluate('state.turn');attacker=pages[seat]
    for action in ['practice','slap']:
     await attacker.evaluate('''action=>sendAction({action,version:3,turn_id:state.turn_id,
       points:Array.from({length:61},(_,i)=>[.19+.34*i/60,.6,800*i/60,0,-18,0])})''',action)
     await attacker.wait_for_function('state.practice_done' if action=='practice' else 'state.phase==="replay"',timeout=60000)
    report['hits'].append(await attacker.evaluate('state.event'))
    print('HIT',turn,flush=True)
    for page in pages:await page.locator('#replaySkip').click()
   report['clients']=[]
   for page in pages:
    await page.evaluate('window.profileCPURead=true');await page.wait_for_function('window.cpuProfile')
    report['clients'].append(await page.evaluate('({gpu:gpuProbe,cpu:cpuProfile,frame_chars:physicsFrame.length,stats:godotStats,warmup:renderWarmup})'))
   for client in report['clients']:
    assert client['warmup']['complete'], 'Join opened before rendering warmup'
    stains=[p for p in client['gpu']['programs'] if p['stain']]
    assert len(stains)>=6, 'Missing stain render variants in probe'
    assert all(p.get('checkedReady') is False for p in stains), 'Stain shader compiled after game became ready'
   assert not report['errors'],report['errors']
   report['passed']=True
   print(json.dumps({'hits':len(report['hits']),'summaries':[{'slow_calls':c['gpu']['slow'],'impact_frames':[v for v in c['gpu']['longFrames'] if v['phase']=='impact'],'frame_chars':c['frame_chars']} for c in report['clients']]}),flush=True)
  finally:
   (ROOT/'logs/render-warmup.json').write_text(json.dumps(report,indent=2),encoding='utf-8');await browser.close()
asyncio.run(main())
