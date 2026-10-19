"""Actual host-solved strong-hit KO, score/recovery/replay HUD, reset and draw.

Recorded valid input trajectories, not a human mouse/controls acceptance test.
"""
import asyncio,json,os,sys,copy
from pathlib import Path
from playwright.async_api import async_playwright
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'server'))
from rules import DEFAULTS,strike_points,head_motion
URL='http://localhost:'+os.environ.get('BACKENBEBEN_TEST_PORT','8914')

async def main():
 report={'errors':[],'hits':[],'input':'recorded production protocol, no injected outcomes'}
 async with async_playwright() as p:
  browser=await p.chromium.launch(executable_path=str(ROOT/'tools/playwright-browsers/chromium-1243/chrome-win64/chrome.exe'),headless=True,args=['--disable-background-timer-throttling','--disable-renderer-backgrounding'])
  pages=[];original=None
  async def admin(command):
   response=await pages[0].request.post(URL+'/api/admin',headers={'Origin':URL},data={'command':command})
   assert response.ok,(command,await response.text())
   return (await response.json())['reply']
  async def seek(page,t):
   actual=await page.locator('#replaySeek').evaluate('(e,t)=>{e.value=t;e.dispatchEvent(new Event("input",{bubbles:true}));return +e.value}',t)
   await page.wait_for_function('(t)=>Math.abs(godotStats.physics_time-t)<.00001',arg=actual)
   return await page.evaluate('JSON.parse(physicsFrame)')
  try:
   for _ in range(2):
    context=await browser.new_context(viewport={'width':1280,'height':720});page=await context.new_page()
    page.on('pageerror',lambda e:report['errors'].append(str(e)))
    page.on('console',lambda m:report['errors'].append(m.text) if m.type=='error' else None)
    await page.goto(URL);await page.wait_for_function('window.gameReady',timeout=90000);pages.append(page)
   for page,face in zip(pages,[1,4]):await page.locator('#face_style').select_option(str(face))
   original=json.loads(await admin('get'))
   for k,v in DEFAULTS.items():await admin(f'set {k} {v}')
   for page in pages:await page.locator('#duel').click()
   for turn in range(10):
    await pages[0].wait_for_function('state?.phase==="aim"',timeout=20000)
    seat=await pages[0].evaluate('state.turn');attacker=pages[seat]
    await attacker.wait_for_function('state.phase==="aim" && state.turn===you')
    for action in ['practice','slap']:
     await attacker.evaluate('''action=>sendAction({action,version:3,turn_id:state.turn_id,
       points:Array.from({length:61},(_,i)=>[.19+.34*i/60,.64,350*i/60,0,-15,0])})''',action)
     await attacker.wait_for_function('state.practice_done' if action=='practice' else 'state.phase==="replay"',timeout=60000)
    a,b=[await page.evaluate('state') for page in pages];assert a['players']==b['players']
    event=a['event'];clip=await (await attacker.request.get(URL+'/api/replay/'+a['replay_id'])).json()
    before=clip['before'];after=clip['after'];target=clip['target']
    assert all(after[i]['points']-before[i]['points']==(event['points'] if i==seat else 0) for i in range(2))
    assert event['points']==strike_points(dict(hit=True,quality=event['quality'],contact_class=clip['contact_class']))
    assert abs(clip['head_motion']-head_motion(clip)[0])<1e-9
    if before[target]['received_hits']==0:assert not clip['ko'],'First hit KO'
    if clip['ko']:assert after[target]['ko_value']>=DEFAULTS['ko_threshold'] and after[target]['combat_stage']=='ko'
    report['hits'].append(dict(damage=event['damage'],points=event['points'],quality=event['quality'],ko=clip['ko'],stun=after[target]['stun'],load=after[target]['load'],ko_value=after[target]['ko_value']))
    print('HIT',turn,event['quality'],event['points'],clip['ko'],after[target]['ko_value'],flush=True)
    for t,key in [(.9,'after'),(.2,'before')]:
     frame=await seek(attacker,t)
     assert frame['display_players'][target]['load']==clip[key][target]['load']
     assert frame['display_players'][target]['stun']==clip[key][target]['stun']
     await attacker.wait_for_timeout(250)
     for i in range(2):
      text=await attacker.locator('#scoreBlue .turnRole' if i else '#scoreRed .turnRole').text_content()
      assert str(clip[key][i]['points'])+' PKT' in text,(key,text,clip[key][i]['points'])
    await seek(attacker,.9)
    if clip['ko']:
     await attacker.locator('#replayCamera').select_option('ko');await attacker.screenshot(path=str(ROOT/'logs/combat52-ko.png'))
    for page in pages:await page.locator('#replaySkip').click()
    await pages[0].wait_for_function('["aim","over"].includes(state.phase)',timeout=20000)
    current=await pages[0].evaluate('state')
    if clip['ko']:
     assert current['phase']=='over' and current['result_reason']=='ko' and current['winner']==seat
     report['default_ko']=True;break
    for i in range(2):
     expected=max(0.,after[i]['stun']-DEFAULTS['recovery']) if (turn+1)%2==0 else after[i]['stun']
     assert abs(current['players'][i]['stun']-expected)<.001
     assert current['players'][i]['load']==after[i]['load']
     assert current['players'][i]['face_damage']==after[i]['face_damage']
   assert report.get('default_ko'),'Strong standard duel did not reach KO'
   # Fresh short match: all misses must end tied, never award damage points.
   await admin('set max_pairs 2')
   for page in pages:await page.locator('#rematch').click()
   await pages[0].wait_for_function('state.phase==="aim"')
   fresh=await pages[0].evaluate('state')
   assert fresh['result_reason']=='' and fresh['turn']==1
   for v in fresh['players']:
    assert all(v[k]==0 for k in ['damage','stun','load','ko_value','points','received_hits']) and not v['knocked_out']
   for page in pages:
    await page.wait_for_function('godotStats.face_head_offset.every(v=>v===0) && godotStats.face_head_rotation.every(v=>v===0) && godotStats.face_injury.every(v=>v===0) && godotStats.mirror_injury.every(v=>v===0)')
   for turn in range(4):
    await pages[0].wait_for_function('state.phase==="aim"',timeout=20000);seat=await pages[0].evaluate('state.turn');page=pages[seat]
    await page.wait_for_function('state.phase==="aim" && state.turn===you')
    for action in ['practice','slap']:
     await page.evaluate('''action=>sendAction({action,version:3,turn_id:state.turn_id,points:[[.05,.98,0,0,0,0],[.1,.98,300,0,0,0]]})''',action)
     await page.wait_for_function('state.practice_done' if action=='practice' else 'state.phase==="replay"',timeout=60000)
    assert await page.evaluate('state.event.points===0 && state.event.damage===0 && !state.event.ko')
    for page in pages:await page.locator('#replaySkip').click()
   await pages[0].wait_for_function('state.phase==="over"',timeout=20000)
   result=await pages[0].evaluate('state')
   assert result['winner']==-1 and result['result_reason']=='draw' and all(p['points']==0 for p in result['players'])
   assert 'REMIS' in await pages[0].locator('#resultTitle').text_content()
   report.update(draw=True,reset=True,replay_hud=True,pair_recovery=True)
   # Layout of real HUD at phone width; names and warning labels must fit boxes.
   await pages[0].set_viewport_size({'width':390,'height':844})
   await pages[0].screenshot(path=str(ROOT/'logs/combat52-mobile.png'))
   report['hud_layout']=await pages[0].evaluate('''()=>[...document.querySelectorAll('#scorebug>div')].map(e=>({id:e.id,w:e.clientWidth,h:e.clientHeight,sw:e.scrollWidth,sh:e.scrollHeight}))''')
   assert all(v['sw']<=v['w'] and v['sh']<=v['h'] for v in report['hud_layout']),report['hud_layout']
   assert not report['errors'],report['errors'];report['passed']=True
   print(json.dumps(report),flush=True)
  finally:
   if original is not None:
    for k,v in original.items():await admin(f'set {k} {v}')
   (ROOT/'logs/combat52-model-browser.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
   await browser.close()

if __name__=='__main__':asyncio.run(main())
