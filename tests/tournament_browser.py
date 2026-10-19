"""Three rendered clients, odd bracket, two real solved fights and one champion."""
import asyncio,json,os
from pathlib import Path
from playwright.async_api import async_playwright

ROOT=Path(__file__).resolve().parents[1]
URL='http://localhost:'+os.environ.get('BACKENBEBEN_TEST_PORT','8916')

async def main():
 report={'errors':[],'matches':[],'input':'production protocol trajectories; no injected results'}
 async with async_playwright() as pw:
  browser=await pw.chromium.launch(executable_path=str(ROOT/'tools/playwright-browsers/chromium-1243/chrome-win64/chrome.exe'),headless=True,args=['--disable-background-timer-throttling','--disable-renderer-backgrounding'])
  pages=[];original=None
  async def admin(command):
   r=await pages[0].request.post(URL+'/api/admin',headers={'Origin':URL},data={'command':command});assert r.ok
   return (await r.json())['reply']
  try:
   for i in range(3):
    ctx=await browser.new_context(viewport={'width':1280,'height':800});p=await ctx.new_page();pages.append(p)
    p.on('pageerror',lambda e:report['errors'].append(str(e)))
    p.on('console',lambda m:report['errors'].append(m.text) if m.type=='error' else None)
    await p.goto(URL);await p.wait_for_function('window.gameReady',timeout=90000)
    await p.locator('#nickname').fill(f'TURNIER {i+1}');await p.locator('#face_style').select_option('1' if i==0 else '4')
   original=json.loads(await admin('get'));await admin('set max_pairs 2')
   await pages[0].locator('#tournamentCreate').click()
   await pages[0].wait_for_function('document.body.classList.contains("tournament")')
   code=await pages[0].locator('#tournamentCode').text_content()
   for p in pages[1:]:
    await p.locator('#tournamentJoinCode').fill(code);await p.locator('#tournamentJoin').click()
    await p.wait_for_function('document.body.classList.contains("tournament")')
   await pages[0].wait_for_function('document.querySelectorAll(".entrantList li").length===3')
   await pages[0].screenshot(path=str(ROOT/'logs/tournament-lobby.png'))
   await pages[0].locator('#tournamentStart').click()
   await asyncio.sleep(.4)
   waiting=next(iter([p for p in pages if await p.evaluate('document.body.classList.contains("tournament")')]))
   token=await waiting.evaluate('sessionStorage.getItem("backen-session")')
   await waiting.evaluate('socket.close()')
   await waiting.wait_for_function('socket.readyState===1 && document.body.classList.contains("tournament")',timeout=10000)
   assert await waiting.evaluate('sessionStorage.getItem("backen-session")')==token
   report['bye_resume']=True
   seen=set()
   async with asyncio.timeout(220):
    while len(report['matches'])<2:
     samples=[await p.evaluate('state') for p in pages]
     current=next((s for s in samples if s and s['phase']=='aim' and s['id'] not in seen),None)
     if not current:await asyncio.sleep(.1);continue
     rid=current['id'];seen.add(rid);hits=[]
     fighters=[p for p,s in zip(pages,samples) if s and s['id']==rid]
     assert len(fighters)==2
     for _ in range(11):
      await fighters[0].wait_for_function('state?.phase==="aim"',timeout=20000)
      r=await fighters[0].evaluate('state');seat=r['turn']
      attacker=next(iter([p for p in fighters if await p.evaluate('you')==seat]))
      await attacker.wait_for_function('state.phase==="aim" && state.turn===you')
      for action in ('practice','slap'):
       await attacker.evaluate('''action=>sendAction({action,version:3,turn_id:state.turn_id,
         points:Array.from({length:61},(_,i)=>[.19+.34*i/60,.64,350*i/60,0,-15,0])})''',action)
       await attacker.wait_for_function('state.practice_done' if action=='practice' else 'state.phase==="replay"',timeout=60000)
      r=await attacker.evaluate('state');hits.append(dict(points=r['event']['points'],ko=r['event']['ko'],quality=r['event']['quality']))
      for p in fighters:await p.evaluate('sendAction({action:"skip_replay"})')
      await fighters[0].wait_for_function('state && ["aim","over"].includes(state.phase)',timeout=20000)
      final=await fighters[0].evaluate('state')
      if final['phase']=='over':
       assert final['winner']>=0 and final['tournament']==code
       assert await fighters[0].locator('#rematch').is_hidden()
       assert final['hits']==len(hits),'Unintended timeout stroke during browser test'
       report['matches'].append(dict(id=rid,hits=hits,winner=final['players'][final['winner']]['name'],reason=final['result_reason']))
       print('MATCH',json.dumps(report['matches'][-1]),flush=True);break
     else:raise AssertionError('Tournament fight exceeded bounded overtime')
   await asyncio.sleep(6.5)
   for p in pages:await p.wait_for_function('document.body.classList.contains("tournament")')
   summaries=[await p.locator('#tournamentStatus').text_content() for p in pages]
   assert len(set(summaries))==1 and summaries[0].startswith('TURNIERSIEGER:')
   report['champion']=summaries[0];report['first_round_byes']=await pages[0].locator('.bracketMatch small').all_text_contents()
   await pages[0].screenshot(path=str(ROOT/'logs/tournament-champion.png'))
   await pages[0].set_viewport_size({'width':390,'height':844})
   await pages[0].screenshot(path=str(ROOT/'logs/tournament-mobile.png'))
   assert await pages[0].evaluate('document.documentElement.scrollWidth<=innerWidth')
   assert await pages[0].locator('#tournamentLeave').is_visible()
   assert not report['errors'],report['errors']
  finally:
   if original:
    for key,value in original.items():await admin(f'set {key} {value}')
   for p in pages:
    try:await p.evaluate('sendAction({action:"leave"})')
    except Exception:pass
   await browser.close()
 (ROOT/'logs/tournament-browser.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
 print(json.dumps(report),flush=True)

if __name__=='__main__':asyncio.run(main())
