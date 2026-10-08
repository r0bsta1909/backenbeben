"""Exercise contact-view controls against a real training replay on port 8877."""
import asyncio,json
from pathlib import Path
from playwright.async_api import async_playwright
async def main():
 async with async_playwright() as p:
  browser=await p.chromium.launch(executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe',headless=True)
  page=await browser.new_page(viewport={'width':1920,'height':1080});errors=[]
  page.on('pageerror',lambda e:errors.append(str(e)))
  page.on('console',lambda m:errors.append(m.text) if m.type=='error' else None)
  await page.goto('http://localhost:8877');await page.wait_for_function('window.gameReady',timeout=60000)
  await page.evaluate("()=>{window.sentActions=[];const original=sendAction;sendAction=d=>{sentActions.push(d);original(d)}}")
  await page.locator('#training').click();await page.wait_for_function("state?.phase==='aim'")
  await page.locator('#poseCamera').click()
  await page.wait_for_function('godotStats?.camera_position?.[0]===3')
  assert await page.locator('#poseCamera').get_attribute('aria-pressed')=='true'
  await page.wait_for_timeout(150)
  hidden_draws=await page.evaluate('godotStats.mirror_draw_requests')
  idle_updates=await page.evaluate('godotStats.physics_material_updates')
  await page.wait_for_timeout(300)
  assert await page.evaluate('godotStats.mirror_draw_requests')==hidden_draws
  assert await page.evaluate('godotStats.physics_material_updates')==idle_updates
  await page.mouse.move(1536,648);await page.mouse.wheel(0,120)
  await page.wait_for_function('window.netArm?.tilt===-12')
  await page.screenshot(path='logs/pose-inspection.png')
  await page.locator('#resetPose').click()
  await page.wait_for_function('window.netArm?.tilt===-15')
  await page.locator('#poseCamera').click()
  await page.wait_for_function('godotStats?.camera_position?.[0]<1')
  await page.wait_for_function('(n)=>godotStats.mirror_draw_requests>n',arg=hidden_draws)
  assert 'HAND FLACH' not in await page.locator('#poseReadout').inner_text()
  async def stroke():
   await page.mouse.move(1536,648);await page.mouse.down()
   for i in range(12):
    await page.mouse.move(1920*(.8-.34/1.5*(i+1)/12),648);await page.wait_for_timeout(8)
   await page.mouse.up()
  await stroke();await page.wait_for_function('state.practice_done');await stroke()
  try:await page.wait_for_function("state.phase==='replay'",timeout=20000)
  except Exception:
   print(await page.evaluate('JSON.stringify({state,actions:sentActions})'));print(errors)
   await page.screenshot(path='logs/contact-view-failure.png')
   await browser.close();raise
  await page.locator('#replayImpact').click()
  await page.wait_for_function("JSON.parse(physicsFrame).camera==='side' && JSON.parse(physicsFrame).time===.5")
  assert await page.locator('#contactLegend').is_visible()
  assert await page.evaluate('godotStats.physics_material_updates')>idle_updates
  frame=await page.evaluate('JSON.parse(physicsFrame)');assert frame['footprint']
  await page.wait_for_timeout(300);await page.screenshot(path='logs/contact-view.png')
  await page.locator('#replayContact').click()
  await page.wait_for_function('JSON.parse(physicsFrame).footprint.length===0')
  assert not await page.locator('#contactLegend').is_visible()
  await page.locator('#replayImpact').click()
  await page.locator('#replaySeek').evaluate('e=>{e.value=.7;e.dispatchEvent(new Event("input"))}')
  await page.wait_for_function('JSON.parse(physicsFrame).time>.6')
  await page.wait_for_function('godotStats?.crowd_active===true')
  assert not await page.locator('#contactLegend').is_visible()
  assert not (await page.evaluate('JSON.parse(physicsFrame)'))['footprint']
  await page.locator('#replaySeek').evaluate('e=>{e.value=1.8;e.dispatchEvent(new Event("input"))}')
  await page.wait_for_function('JSON.parse(physicsFrame).arm.pose.finger_relax>.99')
  await page.wait_for_function('godotStats?.crowd_active===false')
  await page.locator('#replayCamera').select_option('wide')
  await page.wait_for_timeout(250);await page.screenshot(path='logs/finger-recovery.png')
  await page.locator('#replayImpact').click()
  await page.wait_for_function('JSON.parse(physicsFrame).arm.pose.finger_relax===0')
  await page.wait_for_function('godotStats?.crowd_active===false')
  assert not errors,errors
  report={'idle_material_uploads_skipped':True,'mirror_visibility_updates':True,'pose_camera_and_wheel':True,'crowd_reaction_and_rewind':True,'jump_to_contact':True,'side_camera':True,'marker_toggle':True,'no_stale_markers':True,'errors':errors}
  Path('logs/contact-view.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
  await browser.close()
asyncio.run(main())
