import asyncio,json
from pathlib import Path
from playwright.async_api import async_playwright
async def main():
 async with async_playwright() as p:
  browser=await p.chromium.launch(executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe',headless=True)
  page=await browser.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  await page.goto('http://localhost:8877');await page.wait_for_function('window.gameReady',timeout=60000)
  await page.locator('#training').click();await page.wait_for_function("state?.phase==='aim'")
  results=[]
  for width,height in [(1920,1080),(1366,768),(1280,720)]:
   await page.set_viewport_size({'width':width,'height':height})
   await page.wait_for_timeout(200)
   panel=await page.locator('#posePanel').bounding_box()
   assert panel['y']>=0 and panel['y']+panel['height']<=height-60,(width,height,panel)
   await page.locator('#resetPose').scroll_into_view_if_needed()
   button=await page.locator('#resetPose').bounding_box()
   assert button['y']>=panel['y'] and button['y']+button['height']<=panel['y']+panel['height'],button
   await page.locator('#resetPose').click()
   await page.locator('#poseCamera').click()
   await page.wait_for_function("document.getElementById('poseCamera').getAttribute('aria-pressed')==='true'")
   await page.locator('#poseCamera').click()
   await page.locator('#posePanel').evaluate('e=>e.scrollTop=0')
   await page.screenshot(path=f'logs/compact-guidance-{width}.png')
   results.append({'viewport':[width,height],'panel':panel,'reset_and_camera_reachable':True})
  assert not errors,errors
  Path('logs/compact-guidance.json').write_text(json.dumps({'viewports':results,'errors':errors},indent=2))
  await browser.close()
asyncio.run(main())
