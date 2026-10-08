import asyncio,json
from pathlib import Path
from playwright.async_api import async_playwright
async def main():
 async with async_playwright() as p:
  browser=await p.chromium.launch(executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe',headless=True)
  page=await browser.new_page(viewport={'width':1920,'height':1080});errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  await page.goto('http://localhost:8877');await page.wait_for_function('window.gameReady',timeout=60000)
  await page.locator('#training').click();await page.wait_for_function("state?.phase==='aim'")
  await page.mouse.move(1536,648)
  for _ in range(2):await page.mouse.wheel(0,-120);await page.wait_for_timeout(100)
  await page.wait_for_function('netArm?.tilt===-21')
  async def stroke():
   old=await page.evaluate('state.event_id')
   await page.mouse.move(1536,648);await page.mouse.down()
   for i in range(12):
    await page.mouse.move(1920*(.8-.34/1.5*(i+1)/12),648);await page.wait_for_timeout(8)
   await page.mouse.up();await page.wait_for_function('(old)=>state.event_id>old',arg=old)
  await stroke()
  before=await page.locator('#contactVerdict').inner_text()
  assert 'nach unten' in before,before
  history=[before];tilt=-21
  for attempt in range(3):
   current=history[-1]
   if 'Sauber' in current:break
   assert 'eine Rastung' in current,current
   step=3 if 'nach unten' in current else -3
   await page.mouse.move(1536,648);await page.mouse.wheel(0,120 if step>0 else -120)
   tilt+=step;await page.wait_for_function('(v)=>netArm?.tilt===v',arg=tilt)
   await page.locator('#repeatPractice').click();await stroke()
   await page.wait_for_function('document.getElementById("contactVerdict").textContent===state.diagnosis')
   history.append(await page.locator('#contactVerdict').inner_text())
  after=history[-1]
  assert 'Sauber' in after,history
  assert await page.evaluate("state.hits===0 && state.phase==='aim' && state.event.kind==='practice'")
  await page.screenshot(path='logs/practice-wheel-correction.png')
  assert not errors,errors
  Path('logs/practice-wheel-correction.json').write_text(json.dumps({'before':before,'after':after,'genuine_pointer_and_wheel':True,'tilt_before':-21,'tilt_after':tilt,'diagnosis_history':history,'no_damage':True,'errors':errors},indent=2))
  await browser.close()
asyncio.run(main())
