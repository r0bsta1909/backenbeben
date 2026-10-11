"""Exercise contact-view controls against a real training replay on port 8877."""
import asyncio,json,sys,os
from pathlib import Path
from playwright.async_api import async_playwright
TEST_URL='http://localhost:'+os.environ.get('BACKENBEBEN_TEST_PORT','8877')
CHROME=os.environ.get('BACKENBEBEN_TEST_CHROME',str(Path(__file__).resolve().parents[1]/'tools/playwright-browsers/chromium-1243/chrome-win64/chrome.exe'))
async def main():
 async with async_playwright() as p:
  browser=await p.chromium.launch(executable_path=CHROME,headless=True)
  page=await browser.new_page(viewport={'width':1920,'height':1080});errors=[]
  page.on('pageerror',lambda e:errors.append(str(e)))
  page.on('console',lambda m:errors.append(m.text) if m.type=='error' else None)
  await page.goto(TEST_URL);await page.wait_for_function('window.gameReady',timeout=60000)
  await page.evaluate("()=>{window.sentActions=[];const original=sendAction;sendAction=d=>{sentActions.push(d);original(d)}}")
  await page.locator('#nickname').fill('WMWMWMWMWMWMWMWMWM')
  await page.locator('#training').click();await page.wait_for_function("state?.phase==='aim'")
  await page.wait_for_function("document.getElementById('posePanel').dataset.mode==='practice'")
  await page.screenshot(path='logs/guidance-practice.png')
  await page.locator('#poseCamera').click()
  await page.wait_for_function('godotStats?.camera_position?.[0]===3.5')
  assert await page.locator('#poseCamera').get_attribute('aria-pressed')=='true'
  await page.wait_for_timeout(150)
  hidden_draws=await page.evaluate('godotStats.mirror_draw_requests')
  idle_updates=await page.evaluate('godotStats.physics_material_updates')
  await page.wait_for_timeout(300)
  assert await page.evaluate('godotStats.mirror_draw_requests')==hidden_draws
  assert await page.evaluate('godotStats.physics_material_updates')==idle_updates
  await page.mouse.move(1536,648);await page.mouse.wheel(0,120)
  await page.wait_for_function('window.netArm?.tilt===-15')
  await page.screenshot(path='logs/pose-inspection.png')
  await page.locator('#resetPose').click()
  await page.wait_for_function('window.netArm?.tilt===-18')
  await page.locator('#poseCamera').click()
  await page.wait_for_function('godotStats?.camera_position?.[0]<1')
  await page.wait_for_function('(n)=>godotStats.mirror_draw_requests>n',arg=hidden_draws)
  assert 'HAND FLACH' not in await page.locator('#poseReadout').inner_text()
  async def stroke():
   await page.mouse.move(1536,648);await page.mouse.down()
   for i in range(12):
    await page.mouse.move(1920*(.8-.34/1.5*(i+1)/12),648);await page.wait_for_timeout(8)
   await page.mouse.up()
  await stroke();await page.wait_for_function('state.practice_done')
  await page.wait_for_function("document.getElementById('posePanel').dataset.mode==='strike'")
  await page.screenshot(path='logs/guidance-strike.png')
  first_event=await page.evaluate('state.event_id')
  await page.locator('#repeatPractice').click()
  await page.wait_for_function("document.getElementById('repeatPractice').textContent.includes('NUR PROBE')")
  assert await page.locator('#practiceStep').get_attribute('aria-current')=='step'
  await stroke()
  await page.wait_for_function('(old)=>state.event_id>old',arg=first_event)
  assert await page.evaluate("state.phase==='aim' && state.hits===0 && state.event.kind==='practice'")
  await stroke()
  try:await page.wait_for_function("state.phase==='replay'",timeout=20000)
  except Exception:
   print(await page.evaluate('JSON.stringify({state,actions:sentActions})'));print(errors)
   await page.screenshot(path='logs/contact-view-failure.png')
   await browser.close();raise
  coupled_evidence=None
  if '--expect-coupled' in sys.argv or '--expect-moving' in sys.argv:
   await page.wait_for_function('JSON.parse(physicsFrame).side_cage.nx===17')
   replay_id=await page.evaluate('state.replay_id')
   recorded=await (await page.request.get(TEST_URL+'/api/replay/'+replay_id)).json()
   assert recorded['physics_backend']==('coupled-moving' if '--expect-moving' in sys.argv else 'coupled')
   if '--expect-spatial' in sys.argv:assert recorded['head_response']['spatial_rotation'] is True
   coupled_evidence={'backend':recorded['physics_backend'],'solve_ms':recorded['solve_ms'],'peak':recorded['peak'],'contact_diagnostics':recorded['contact_diagnostics'],'head_response':recorded.get('head_response'),'maximum_head_yaw_rad':max(abs(f[0]) for f in recorded['frames'])}
  if '--inspect-timeout' in sys.argv:
   await page.wait_for_function("state.phase==='replay' && state.remaining<3",timeout=15000)
   await page.locator('#replayImpact').click()
   await page.wait_for_function("state.phase==='replay' && state.remaining>10",timeout=3000)
   await page.wait_for_timeout(4000)
   assert await page.evaluate("state.phase==='replay'"), 'Inspection expired at original deadline'
  await page.locator('#replayImpact').click()
  await page.wait_for_function("JSON.parse(physicsFrame).camera==='contact' && JSON.parse(physicsFrame).time===.5")
  assert await page.locator('#contactLegend').is_visible()
  assert not await page.locator('#replayKO').is_visible()
  assert await page.locator('#scoreRed .playerName').get_attribute('title')=='WMWMWMWMWMWMWMWMWM'
  assert 'Am Schlag' in await page.locator('#scoreRed').get_attribute('aria-label')
  assert await page.evaluate('godotStats.physics_material_updates')>idle_updates
  frame=await page.evaluate('JSON.parse(physicsFrame)');assert frame['footprint']
  await page.wait_for_timeout(300);await page.screenshot(path='logs/contact-view.png')
  await page.locator('#replayContact').click()
  await page.wait_for_function('JSON.parse(physicsFrame).footprint.length===0')
  assert not await page.locator('#contactLegend').is_visible()
  if '--visual-contact' in sys.argv:
   audit=[]
   # Nine captures fit the real replay window; the fixed side view is tested
   # separately through pose inspection above.
   for view in ('contact','front','wide'):
    await page.locator('#replayCamera').select_option(view)
    for moment,label in ((.46,'before'),(.5,'contact'),(.54,'after'),(.65,'head-response'),(.8,'recovery')):
     await page.locator('#replaySeek').evaluate('(e,t)=>{e.value=t;e.dispatchEvent(new Event("input",{bubbles:true}))}',moment)
     await page.wait_for_function('(s)=>{const f=JSON.parse(physicsFrame);return f.camera===s.view && Math.abs(f.time-s.time)<.002 && f.footprint.length===0}',arg={'view':view,'time':moment})
     await page.wait_for_timeout(200)
     await page.screenshot(path=f'logs/contact-audit-{view}-{label}.png')
     record=await page.evaluate('({frame:JSON.parse(physicsFrame),rendered:godotStats.rendered_arm,head_offset:godotStats.face_head_offset,head_rotation:godotStats.face_head_rotation})')
     record.update(camera=view,moment=label);audit.append(record)
     assert max(abs(a-b) for a,b in zip(record['head_rotation'],record['frame'].get('head_rotation',[0,0,0])))<1e-5
     assert max(abs(a-b) for a,b in zip(record['head_offset'],record['frame'].get('head_offset',[0,0,0])))<1e-5
     for joint in ('shoulder','elbow','wrist'):
      assert max(abs(a-b) for a,b in zip(record['frame']['arm']['pose'][joint],record['rendered'][joint]))<1e-5,(view,label,joint,record)
   Path('logs/contact-arm-render-audit.json').write_text(json.dumps(audit,indent=2))
   layout_audit=[]
   for width,height in ((1920,1080),(1280,720),(1280,1024),(900,1200)):
    await page.set_viewport_size({'width':width,'height':height})
    await page.wait_for_timeout(150)
    boxes=await page.evaluate('''()=>{
      const rect=id=>{const r=document.getElementById(id).getBoundingClientRect();return {x:r.x,y:r.y,right:r.right,bottom:r.bottom}};
      return {panel:rect('replayPanel'),score:rect('scorebug'),buttons:[...document.querySelectorAll('#replayPanel button,#replayPanel select')].map(e=>{const r=e.getBoundingClientRect();return {x:r.x,y:r.y,right:r.right,bottom:r.bottom}}),bottom:getComputedStyle(document.querySelector('.bottom')).display};
    }''')
    assert boxes['bottom']=='none',boxes
    assert await page.locator('#scoreRed .playerName').evaluate("e=>getComputedStyle(e).textOverflow==='ellipsis' && e.clientWidth<=e.parentElement.clientWidth")
    assert boxes['score']['bottom']<boxes['panel']['y'],boxes
    for box in [boxes['panel'],boxes['score'],*boxes['buttons']]:
     assert box['x']>=0 and box['y']>=0 and box['right']<=width and box['bottom']<=height,boxes
    await page.screenshot(path=f'logs/replay-layout-{width}x{height}.png')
    layout_audit.append({'width':width,'height':height,**boxes})
   Path('logs/replay-layout-audit.json').write_text(json.dumps(layout_audit,indent=2))
   await page.set_viewport_size({'width':1920,'height':1080})
  await page.locator('#replayImpact').click()
  await page.locator('#replaySeek').evaluate('e=>{e.value=.7;e.dispatchEvent(new Event("input",{bubbles:true}))}')
  await page.wait_for_function('JSON.parse(physicsFrame).time>.6')
  await page.wait_for_function('godotStats?.arena_backdrop===true && godotStats?.arena_audience_3d===0 && godotStats?.arena_sponsors===6')
  assert not await page.locator('#contactLegend').is_visible()
  assert not (await page.evaluate('JSON.parse(physicsFrame)'))['footprint']
  await page.locator('#replaySeek').evaluate('e=>{e.value=1.8;e.dispatchEvent(new Event("input",{bubbles:true}))}')
  await page.wait_for_function('JSON.parse(physicsFrame).arm.pose.finger_relax>.99')
  await page.wait_for_function('godotStats?.crowd_active===false')
  await page.locator('#replayCamera').select_option('wide')
  await page.wait_for_timeout(250);await page.screenshot(path='logs/finger-recovery.png')
  await page.locator('#replayImpact').click()
  await page.wait_for_function('JSON.parse(physicsFrame).arm.pose.finger_relax===0')
  await page.wait_for_function('godotStats?.crowd_active===false')
  assert not errors,errors
  report={'repeat_practice_without_damage':True,'idle_material_uploads_skipped':True,'mirror_visibility_updates':True,'pose_camera_and_wheel':True,'painted_arena_during_replay_and_rewind':True,'jump_to_contact':True,'side_camera':True,'marker_toggle':True,'no_stale_markers':True,'errors':errors,'inspection_survives_original_deadline':'--inspect-timeout' in sys.argv}
  if coupled_evidence:report['coupled']=coupled_evidence
  Path('logs/contact-view.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
  await browser.close()
asyncio.run(main())
