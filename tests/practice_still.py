import asyncio,json,sys,argparse
from pathlib import Path
from playwright.async_api import async_playwright
async def main():
 parser=argparse.ArgumentParser();parser.add_argument("--port",type=int,default=8877)
 options,_=parser.parse_known_args();assert 1<=options.port<=65535
 tips="--tips" in sys.argv
 suffix="-tips" if tips else ""
 tilt=-24 if tips else -18
 async with async_playwright() as p:
  browser=await p.chromium.launch(executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe',headless=True)
  page=await browser.new_page(viewport={'width':1366,'height':768});errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  await page.goto(f'http://localhost:{options.port}');await page.wait_for_function('window.gameReady',timeout=60000)
  await page.locator('#training').click();await page.wait_for_function("state?.phase==='aim'")
  assert not await page.locator('#inspectPractice').is_visible()
  if tips:
   await page.mouse.move(1366*.8,768*.6)
   for _ in range(2):await page.mouse.wheel(0,-120);await page.wait_for_timeout(100)
   await page.wait_for_function('netArm?.tilt===-24')
  await page.mouse.move(1366*.8,768*.6);await page.mouse.down()
  for i in range(12):
   await page.mouse.move(1366*(.8-.34/1.5*(i+1)/12),768*.6);await page.wait_for_timeout(8)
  await page.mouse.up();await page.wait_for_function('state.practice_pose?.pose')
  recorded=await page.evaluate('state.practice_pose')
  if tips:assert 'Fingerspitzen' in await page.evaluate('state.diagnosis')
  # New probe automatically exposes the actual contact from the side.
  await page.wait_for_function('JSON.stringify(JSON.parse(handPose).arm)===JSON.stringify(state.practice_pose)')
  await page.wait_for_function('godotStats?.camera_position?.[0]===3.5')
  await page.wait_for_function('["shoulder","elbow","wrist"].every(k=>godotStats.rendered_arm?.[k]?.every((v,i)=>Math.abs(v-state.practice_pose.pose[k][i])<1e-5))')
  assert 'STANDBILD' in await page.locator('#poseTitle').inner_text()
  await page.screenshot(path=f'logs/practice-still{suffix}-side.png')
  await page.locator('#poseCamera').click();await page.wait_for_function('godotStats?.camera_position?.[0]<1')
  await page.screenshot(path=f'logs/practice-still{suffix}-front.png')
  assert await page.evaluate('state.hits===0 && state.players.every(p=>p.damage===0)')
  await page.mouse.move(1366*.8,768*.6);await page.mouse.wheel(0,120)
  await page.wait_for_function('(v)=>JSON.parse(handPose).arm?.tilt===v',arg=tilt+3)
  assert await page.locator('#practiceStillHint').is_visible()
  assert 'Vergleich:' in await page.locator('#contactVerdict').inner_text()
  assert await page.evaluate('state.practice_pose')==recorded
  await page.wait_for_function('["shoulder","elbow","wrist"].every(k=>godotStats.rendered_arm?.[k]?.every((v,i)=>Math.abs(v-JSON.parse(handPose).arm.pose[k][i])<1e-5))')
  if tips:
   await page.mouse.wheel(0,120)
   await page.wait_for_function('JSON.parse(handPose).arm?.tilt===-18')
   assert 'flachen Hand' in await page.locator('#contactVerdict').inner_text()
  await page.screenshot(path=f'logs/practice-compare{suffix}-front.png')
  await page.locator('#poseCamera').click();await page.wait_for_function('godotStats?.camera_position?.[0]===3.5')
  await page.screenshot(path=f'logs/practice-compare{suffix}-side.png')
  await page.locator('#originalPractice').click()
  await page.wait_for_function('JSON.stringify(JSON.parse(handPose).arm)===JSON.stringify(state.practice_pose)')
  assert await page.evaluate('state.practice_pose')==recorded
  assert await page.evaluate('state.hits===0 && state.players.every(p=>p.damage===0)')
  await page.mouse.move(1366*.8,768*.6);await page.mouse.wheel(0,120)
  await page.wait_for_function('(v)=>JSON.parse(handPose).arm?.tilt===v',arg=tilt+3)
  await page.locator('#inspectPractice').click()
  await page.wait_for_function('godotStats?.camera_position?.[0]<1 && JSON.parse(handPose).camera==="front"')
  await page.wait_for_function('(v)=>netArm?.tilt===v',arg=tilt+3)
  assert await page.evaluate('state.hits===0 && state.players.every(p=>p.damage===0)')
  assert await page.locator('#practiceStillHint').is_hidden()
  await page.wait_for_function('Math.hypot(...netArm.pose.wrist.map((v,i)=>v-state.practice_pose.pose.wrist[i]))>.1')
  await page.wait_for_function('["shoulder","elbow","wrist"].every(k=>godotStats.rendered_arm?.[k]?.every((v,i)=>Math.abs(v-netArm.pose[k][i])<1e-5))')
  await page.screenshot(path=f'logs/practice-ready{suffix}.png')
  saved_id=await page.evaluate('state.practice_id')
  await page.locator('#repeatPractice').click()
  assert await page.locator('#practiceStillHint').is_hidden()
  await page.mouse.move(1366*.8,768*.6);await page.mouse.down()
  for i in range(12):
   await page.mouse.move(1366*(.8-.34/1.5*(i+1)/12),768*.6);await page.wait_for_timeout(8)
  await page.mouse.up();await page.wait_for_function('(id)=>state.practice_id!==id',arg=saved_id)
  assert await page.evaluate('state.practice_pose.tilt')==tilt+3
  assert await page.evaluate('state.hits===0 && state.players.every(p=>p.damage===0)')
  assert not errors,errors
  Path(f'logs/practice-still{suffix}.json').write_text(json.dumps({'viewport':[1366,768],'msaa_3d':await page.evaluate('godotStats.msaa_3d'),'host_recorded_pose':recorded,'explicit_ready_returns_to_front':True,'ready_preserves_tilt_without_striking':True,'automatic_contact_view':True,'actual_rig_matches':True,'side_and_front':True,'wheel_compares_same_probe':True,'original_restore':True,'comparison_rig_matches':True,'next_actual_probe_uses_selected_tilt':True,'saved_probe_unchanged':True,'repeat_exits':True,'no_damage':True,'errors':errors},indent=2))
  await browser.close()
asyncio.run(main())
