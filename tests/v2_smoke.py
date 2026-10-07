import asyncio,json,socket
from pathlib import Path
from playwright.async_api import async_playwright
async def main():
 async with async_playwright() as p:
  b=await p.chromium.launch(executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe',headless=True,args=['--enable-webgl'])
  page=await b.new_page(viewport={'width':1280,'height':800});errs=[]
  page.on('pageerror',lambda e:errs.append(str(e)))
  page.on('console',lambda m:errs.append(m.text) if m.type=='error' else None)
  await page.goto('http://'+next(i[4][0] for i in socket.getaddrinfo(socket.gethostname(),None,socket.AF_INET) if not i[4][0].startswith(('127.','169.254.')))+':8877');await page.wait_for_function('window.gameReady',timeout=60000)
  await page.locator('#training').click();await page.wait_for_timeout(400)
  async def stroke():
   await page.mouse.move(1280*.19,800*.49);await page.mouse.down()
   for i in range(35):
    await page.mouse.move(1280*(.19+.28*(i+1)/35),800*.49);await page.wait_for_timeout(10)
   await page.mouse.up()
  await stroke();await page.wait_for_timeout(400)
  print('practice',await page.evaluate('JSON.parse(renderState).state.diagnosis'))
  await page.screenshot(path='logs/v2-aim.png')
  await stroke()
  await page.wait_for_function("JSON.parse(renderState).state.phase==='replay'",timeout=15000)
  await page.locator('#replaySeek').evaluate("e=>{e.value=.533312;e.dispatchEvent(new Event('input'))}");await page.wait_for_timeout(400)
  await page.screenshot(path='logs/v2-replay.png')
  print('diagnostics',await page.evaluate('({combat:combatDiagnostics,godot:godotStats,audio:audioDiagnostics})'))
  print('errors',errs[:20]);Path('logs/v2-smoke.json').write_text(json.dumps({'errors':errs},indent=2))
  await b.close()
asyncio.run(main())
