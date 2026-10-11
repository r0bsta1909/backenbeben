"""Real-pointer bot training: one renderer, normal settings, both impact roles."""
import asyncio,json,time
from pathlib import Path
from playwright.async_api import async_playwright
async def main():
 async with async_playwright() as p:
  browser=await p.chromium.launch(executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe',headless=True,args=['--enable-webgl'])
  context=await browser.new_context(viewport={'width':1920,'height':1080})
  await context.add_init_script(path=str(Path(__file__).with_name('browser_phase_profile.js')))
  page=await context.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  await page.goto('http://localhost:8877');await page.wait_for_function('window.gameReady',timeout=60000)
  await page.locator('#training').click();await page.wait_for_function("state?.phase==='aim'")
  await page.mouse.move(1536,691.2);await page.mouse.wheel(0,120)
  await page.wait_for_function('netArm?.tilt===-15')
  seen=set();turns=set();hits=[];deadline=time.monotonic()+150
  while time.monotonic()<deadline and len(hits)<6:
   view=await page.evaluate('JSON.parse(renderState)');s=view['state']
   if s['phase']=='over':break
   if s['phase']=='aim' and s['turn']==view['you'] and s['turn_id'] not in turns:
    turns.add(s['turn_id'])
    for _ in range(2):
     await page.mouse.move(1536,691.2);await page.mouse.down();start=time.perf_counter()
     for i in range(4):
      await asyncio.sleep(max(0,start+.35*(i+1)/4-time.perf_counter()))
      await page.mouse.move(1920*(.8-.34/1.5*(i+1)/4),691.2)
     await page.mouse.up()
     await page.wait_for_function('state.practice_done')
   elif s['phase']=='replay' and s['replay_id'] not in seen:
    seen.add(s['replay_id']);hits.append(s['event'])
    await page.wait_for_timeout(1700)
    await page.locator('#replaySkip').click()
   await page.wait_for_timeout(50)
  result=await page.evaluate('phasePerformance()');summary={}
  for phase,values in result.pop('samples').items():
   values.sort();summary[phase]={'frames':len(values),'median_ms':round(values[len(values)//2],2),'p95_ms':round(values[min(len(values)-1,int(len(values)*.95))],2),'max_ms':round(values[-1],2),'over_50ms':sum(v>50 for v in values)}
  for phase in ['stroke','impact_striker','impact_receiver','replay_playing']:assert summary.get(phase,{}).get('frames',0)>10,phase
  assert not errors,errors
  result.update(phases=summary,browser=browser.version,hits_observed=len(hits),errors=errors,limits='One headless renderer plus local host; bot strokes differ from two-human test, not identical replay A/B. Measures browser frame intervals, not GPU time. No full match acceptance claimed.')
  Path('logs/single-browser-performance.json').write_text(json.dumps(result,indent=2));print(json.dumps(summary,indent=2))
  await browser.close()
asyncio.run(main())
