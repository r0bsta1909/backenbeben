"""Ten actual miss trajectories: tied regulation + three extra pairs -> lot."""
import asyncio,json,os
from pathlib import Path
from playwright.async_api import async_playwright

ROOT=Path(__file__).resolve().parents[1]
URL='http://localhost:'+os.environ.get('BACKENBEBEN_TEST_PORT','8916')

async def main():
 report={'errors':[],'hits':0,'extra_pairs':[]}
 async with async_playwright() as pw:
  browser=await pw.chromium.launch(executable_path=str(ROOT/'tools/playwright-browsers/chromium-1243/chrome-win64/chrome.exe'),headless=True,args=['--disable-background-timer-throttling','--disable-renderer-backgrounding'])
  pages=[];original=None
  async def admin(command):
   r=await pages[0].request.post(URL+'/api/admin',headers={'Origin':URL},data={'command':command});assert r.ok
   return (await r.json())['reply']
  try:
   for i in range(2):
    ctx=await browser.new_context(viewport={'width':1280,'height':800});p=await ctx.new_page();pages.append(p)
    p.on('pageerror',lambda e:report['errors'].append(str(e)))
    p.on('console',lambda m:report['errors'].append(m.text) if m.type=='error' else None)
    await p.goto(URL);await p.wait_for_function('window.gameReady',timeout=90000)
    await p.locator('#nickname').fill(f'REMIS {i+1}')
   original=json.loads(await admin('get'));await admin('set max_pairs 2')
   await pages[0].locator('#tournamentCreate').click()
   await pages[0].wait_for_function('document.body.classList.contains("tournament")')
   assert await pages[0].locator('#tournamentStart').is_disabled()
   code=await pages[0].locator('#tournamentCode').text_content()
   await pages[1].locator('#tournamentJoinCode').fill(code);await pages[1].locator('#tournamentJoin').click()
   await pages[0].wait_for_function('!document.querySelector("#tournamentStart").disabled')
   await pages[0].locator('#tournamentStart').click()
   for strike in range(10):
    await pages[0].wait_for_function('state?.phase==="aim"',timeout=20000)
    r=await pages[0].evaluate('state');assert r['hits']==strike
    if strike>=4:
     number=(strike-4)//2+1
     await pages[0].wait_for_function('(n)=>document.querySelector("#phaseTag").textContent.includes("ZUSATZPAAR "+n+"/3")',arg=number)
     report['extra_pairs'].append(number)
     if strike==4:await pages[0].screenshot(path=str(ROOT/'logs/tournament-overtime.png'))
    seat=r['turn'];attacker=next(iter([p for p in pages if await p.evaluate('you')==seat]))
    await attacker.wait_for_function('state.phase==="aim" && state.turn===you')
    for action in ('practice','slap'):
     await attacker.evaluate('''action=>sendAction({action,version:3,turn_id:state.turn_id,points:[[.05,.98,0,0,0,0],[.1,.98,300,0,0,0]]})''',action)
     await attacker.wait_for_function('state.practice_done' if action=='practice' else 'state.phase==="replay"',timeout=60000)
    current=await attacker.evaluate('state');assert current['event']['points']==0 and not current['event']['ko']
    for p in pages:await p.evaluate('sendAction({action:"skip_replay"})')
    await pages[0].wait_for_function('state && ["aim","over"].includes(state.phase)',timeout=20000)
    current=await pages[0].evaluate('state');assert current['phase']==('over' if strike==9 else 'aim')
    report['hits']+=1;print('MISS',strike+1,flush=True)
   assert current['winner'] in (0,1) and current['result_reason']=='lot'
   assert all(p['damage']==0 and p['points']==0 for p in current['players'])
   assert 'Losentscheid' in await pages[0].locator('#resultText').text_content()
   await pages[0].screenshot(path=str(ROOT/'logs/tournament-lot.png'))
   await pages[0].wait_for_function('document.body.classList.contains("tournament")',timeout=10000)
   assert (await pages[0].locator('#tournamentStatus').text_content()).startswith('TURNIERSIEGER:')
   # Leaving a result must also leave the character/hand animation loop alive.
   for p in pages:assert await p.evaluate('!JSON.parse(window.handPose).active && !document.body.classList.contains("replaying")')
   report['winner']=current['winner'];report['reason']='lot';assert not report['errors'],report['errors']
  finally:
   if original:
    for key,value in original.items():await admin(f'set {key} {value}')
   for p in pages:
    try:await p.evaluate('sendAction({action:"leave"})')
    except Exception:pass
   await browser.close()
 (ROOT/'logs/tournament-overtime.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
 print(json.dumps(report),flush=True)

if __name__=='__main__':asyncio.run(main())
