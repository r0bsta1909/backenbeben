import asyncio,json
from pathlib import Path
from playwright.async_api import async_playwright
async def main():
 async with async_playwright() as p:
  browser=await p.chromium.launch(executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe',headless=True)
  page=await browser.new_page(viewport={'width':1366,'height':768});errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  await page.goto('http://localhost:8877');await page.wait_for_function('window.gameReady',timeout=60000)
  await page.locator('#training').click();await page.wait_for_function("state?.phase==='aim'")
  reports=[]
  for tilt,expected in [(-20,'nach unten'),(-10,'nach oben')]:
   await page.evaluate('(tilt)=>sendAction({action:"practice",turn_id:state.turn_id,version:3,points:Array.from({length:41},(_,i)=>[.19+.34*i/40,.6,800*i/40,0,tilt,0])})',tilt)
   await page.wait_for_function('(text)=>document.getElementById("contactVerdict").textContent.includes(text)',arg=expected)
   assert await page.evaluate("state.hits===0 && state.phase==='aim'")
   reports.append(await page.locator('#contactVerdict').inner_text())
  await page.locator('#contactVerdict').scroll_into_view_if_needed();await page.screenshot(path='logs/practice-advice.png')
  assert not errors,errors
  Path('logs/practice-advice.json').write_text(json.dumps({'diagnoses':reports,'errors':errors,'no_damage':True},indent=2))
  await browser.close()
asyncio.run(main())
