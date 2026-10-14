"""Render timing and reversible regional-injury onset in the real Web build."""
import asyncio,json,os
from pathlib import Path
from playwright.async_api import async_playwright
ROOT=Path(__file__).resolve().parents[1]
URL='http://localhost:'+os.environ.get('BACKENBEBEN_TEST_PORT','8879')
async def main():
 async with async_playwright() as p:
  browser=await p.chromium.launch(executable_path=str(ROOT/'tools/playwright-browsers/chromium-1243/chrome-win64/chrome.exe'),headless=True,args=['--disable-background-timer-throttling','--disable-renderer-backgrounding'])
  page=await browser.new_page(viewport={'width':1920,'height':1080});errors=[]
  page.on('pageerror',lambda e:errors.append(str(e)))
  page.on('console',lambda m:errors.append(m.text) if m.type=='error' else None)
  await page.goto(URL);await page.wait_for_function('window.gameReady',timeout=60000)
  await page.locator('#training').click();await page.wait_for_function('state.phase==="aim"')
  async def measure():
   return await page.evaluate('''()=>new Promise(resolve=>{let previous=0;const values=[];let warmup=30;
    function tick(t){if(previous&&warmup<=0)values.push(t-previous);previous=t;warmup--;
     if(values.length<90)requestAnimationFrame(tick);else{values.sort((a,b)=>a-b);resolve({median_ms:values[45],p95_ms:values[85],max_ms:values[89]})}}
    requestAnimationFrame(tick)})''')
  report={'viewport':[1920,1080],'idle':await measure()}
  for action in ['practice','slap']:
   await page.evaluate('(action)=>sendAction({action,version:3,turn_id:state.turn_id,points:Array.from({length:61},(_,i)=>[.19+.34*i/60,.6,800*i/60,0,-18,0])})',action)
   await page.wait_for_function('state.practice_done' if action=='practice' else 'state.phase==="replay"',timeout=60000)
  await page.locator('#replayImpact').click()
  await page.wait_for_function('JSON.parse(physicsFrame).camera==="contact"')
  await page.wait_for_function('godotStats.physics_time===.5')
  frames=await page.evaluate('JSON.parse(physicsFrame)')
  target=frames['target']
  assert frames['display_players'][target]['face_damage']['hits']==0
  assert frames['players'][target]['face_damage']['hits']==1
  report['contact']=await measure()
  await page.locator('#replaySeek').evaluate('e=>{e.value=.8;e.dispatchEvent(new Event("input",{bubbles:true}))}')
  await page.wait_for_function('Math.abs(JSON.parse(physicsFrame).time-.8)<.0001')
  frames=await page.evaluate('JSON.parse(physicsFrame)')
  assert frames['display_players'][target]['face_damage']==frames['players'][target]['face_damage']
  report['injured']=await measure()
  await page.locator('#replaySeek').evaluate('e=>{e.value=.3;e.dispatchEvent(new Event("input",{bubbles:true}))}')
  await page.wait_for_function('Math.abs(JSON.parse(physicsFrame).time-.3)<.0001')
  assert await page.evaluate('JSON.parse(physicsFrame).display_players[JSON.parse(physicsFrame).target].face_damage.hits')==0
  report['onset_and_rewind']=True
  report['renderer']=await page.evaluate('''()=>{const gl=document.getElementById('canvas').getContext('webgl2');const e=gl?.getExtension('WEBGL_debug_renderer_info');return e?gl.getParameter(e.UNMASKED_RENDERER_WEBGL):'unavailable'}''')
  report['errors']=errors;assert not errors,errors
  (ROOT/'logs/face-performance.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
  await page.screenshot(path=str(ROOT/'logs/face-onset-rewind.png'))
  await browser.close()
asyncio.run(main())
