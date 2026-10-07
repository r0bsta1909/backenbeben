import asyncio,json
from playwright.async_api import async_playwright
async def run():
 async with async_playwright() as p:
  b=await p.chromium.launch(executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe',headless=True)
  page=await b.new_page(viewport={'width':1600,'height':1000});errors=[]
  page.on('pageerror',lambda e:errors.append(str(e)))
  page.on('console',lambda e:errors.append(e.text) if e.type=='error' else None)
  await page.goto('http://localhost:8877');await page.wait_for_function('window.gameReady',timeout=60000)
  await page.locator('#training').click();await page.wait_for_timeout(1500)
  await page.screenshot(path='logs/v3-ready.png')
  async def stroke():
   await page.mouse.move(1600*.19,1000*.6);await page.mouse.down()
   for i in range(60):
    await page.mouse.move(1600*(.19+.34*(i+1)/60),1000*.6);await page.wait_for_timeout(10)
   await page.mouse.up();await page.wait_for_timeout(500)
  await stroke();print('probe',await page.evaluate('state.diagnosis'));await page.screenshot(path='logs/v3-probe.png')
  await stroke();await page.wait_for_function("state.phase==='replay'",timeout=20000)
  await page.locator('#replaySeek').evaluate("e=>{e.value=.5;e.dispatchEvent(new Event('input'))}")
  await page.wait_for_timeout(300);await page.screenshot(path='logs/v3-replay-front.png')
  await page.locator('#replayCamera').select_option('side');await page.wait_for_timeout(300);await page.screenshot(path='logs/v3-replay-side.png')
  print('result',await page.evaluate('state.diagnosis'));print('errors',errors[:15]);await b.close()
asyncio.run(run())
