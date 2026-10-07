import asyncio,json,time
from pathlib import Path
from playwright.async_api import async_playwright
async def main():
 async with async_playwright() as p:
  b=await p.chromium.launch(executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe',headless=True)
  pages=[await b.new_page(viewport={'width':1920,'height':1080}) for _ in range(2)]
  for page in pages:
   await page.goto('http://localhost:8877');await page.wait_for_function('window.gameReady',timeout=60000)
  a=pages[0];await a.bring_to_front();await a.locator('#training').click();await a.wait_for_timeout(1000)
  await a.evaluate('''()=>{window.metrics={};let last=performance.now();function tick(t){const pose=JSON.parse(window.handPose||'{}');const key=state.phase==='aim'?(pose.dragging?'moving':'idle'):state.phase==='replay'?(document.getElementById('replayPlay').textContent==='PAUSE'?'replay_moving':'replay_paused'):state.phase;(metrics[key]||=[]).push(t-last);last=t;requestAnimationFrame(tick)}requestAnimationFrame(tick)}''')
  await a.wait_for_timeout(2000)
  await a.screenshot(path='logs/v3-ready-final.png')
  async def stroke():
   await a.mouse.move(1920*.19,1080*.6);await a.mouse.down()
   for i in range(12):
    await a.mouse.move(1920*(.19+.34*(i+1)/12),1080*.6);await a.wait_for_timeout(8)
   await a.mouse.up()
  await stroke();await a.wait_for_function('state.practice_done');await stroke();await a.wait_for_function("state.phase==='replay'",timeout=15000)
  await a.locator('#replaySeek').evaluate("e=>{e.value=.53;e.dispatchEvent(new Event('input'))}");await a.locator('#replayCamera').select_option('side');await a.wait_for_timeout(1200)
  await a.locator('#replayPlay').click();await a.wait_for_timeout(1800)
  stats=await a.evaluate('''()=>{let result={};for(const [k,v] of Object.entries(metrics)){const s=v.slice(5).sort((a,b)=>a-b);result[k]={samples:s.length,p95:s[Math.floor(s.length*.95)],median:s[Math.floor(s.length*.5)]}}const gl=canvas.getContext('webgl2'),e=gl.getExtension('WEBGL_debug_renderer_info');return {stages:result,gpu:gl.getParameter(e.UNMASKED_RENDERER_WEBGL),godot:godotStats}}''')
  print(json.dumps(stats,indent=2));Path('logs/v3-performance.json').write_text(json.dumps(stats,indent=2));await b.close()
asyncio.run(main())
