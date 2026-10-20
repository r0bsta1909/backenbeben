"""Real KO winner leaves during impact; administrative cancellation UI afterwards."""
import asyncio,json,os
from pathlib import Path
from playwright.async_api import async_playwright

ROOT=Path(__file__).resolve().parents[1]
URL='http://localhost:'+os.environ.get('BACKENBEBEN_TEST_PORT','8917')

async def main():
 report={'errors':[],'hits':[]};pages=[];original=None
 async with async_playwright() as pw:
  browser=await pw.chromium.launch(executable_path=str(ROOT/'tools/playwright-browsers/chromium-1243/chrome-win64/chrome.exe'),headless=True,args=['--disable-background-timer-throttling','--disable-renderer-backgrounding'])
  async def admin(command):
   r=await pages[0].request.post(URL+'/api/admin',headers={'Origin':URL},data={'command':command});assert r.ok
   return (await r.json())['reply']
  async def enter():
   await pages[0].locator('#tournamentCreate').click()
   await pages[0].wait_for_function('document.body.classList.contains("tournament")')
   code=await pages[0].locator('#tournamentCode').text_content()
   await pages[1].locator('#tournamentJoinCode').fill(code);await pages[1].locator('#tournamentJoin').click()
   await pages[0].wait_for_function('!document.querySelector("#tournamentStart").disabled')
   await pages[0].locator('#tournamentStart').click()
   for p in pages:await p.wait_for_function('state?.phase==="aim"')
  try:
   for i in range(2):
    ctx=await browser.new_context(viewport={'width':1280,'height':800});p=await ctx.new_page();pages.append(p)
    p.on('pageerror',lambda e:report['errors'].append(str(e)))
    p.on('console',lambda m:report['errors'].append(m.text) if m.type=='error' else None)
    await p.goto(URL);await p.wait_for_function('window.gameReady',timeout=90000)
    await p.locator('#nickname').fill(f'KO REVIEW {i+1}');await p.locator('#face_style').select_option('1' if i==0 else '4')
   original=json.loads(await admin('get'));await admin('set max_pairs 5')
   await enter()
   for _ in range(10):
    await pages[0].wait_for_function('state?.phase==="aim"',timeout=20000)
    seat=await pages[0].evaluate('state.turn')
    attacker=next(iter([p for p in pages if await p.evaluate('you')==seat]));other=next(p for p in pages if p!=attacker)
    await attacker.wait_for_function('state.phase==="aim" && state.turn===you')
    for action in ('practice','slap'):
     await attacker.evaluate('''action=>sendAction({action,version:3,turn_id:state.turn_id,points:Array.from({length:61},(_,i)=>[.19+.34*i/60,.64,350*i/60,0,-15,0])})''',action)
     await attacker.wait_for_function('state.practice_done' if action=='practice' else 'state.phase==="impact"',timeout=60000)
    r=await attacker.evaluate('state');report['hits'].append(r['event']['quality'])
    if r['event']['ko']:
     champion=r['players'][r['winner']]['name'];assert r['result_reason']=='ko'
     await attacker.evaluate('sendAction({action:"leave"})')
     await attacker.wait_for_function('!document.body.classList.contains("playing")')
     await other.wait_for_function('state?.phase==="over" && state.result_reason==="ko"')
     assert await other.evaluate('state.winner')==r['winner']
     await other.wait_for_function('document.body.classList.contains("tournament")',timeout=10000)
     assert await other.locator('#tournamentStatus').text_content()=='TURNIERSIEGER: '+champion
     assert await other.locator('.bracketMatch small').text_content()=='KO'
     report['ko_winner_preserved_after_impact_leave']=True;break
    await attacker.wait_for_function('state.phase==="replay"',timeout=10000)
    for p in pages:await p.evaluate('sendAction({action:"skip_replay"})')
   assert report.get('ko_winner_preserved_after_impact_leave')
   await other.locator('#tournamentLeave').click()
   await other.wait_for_function('!document.body.classList.contains("tournament")')
   # Start a second real event, then exercise the production cancellation path.
   await enter();await admin('reset')
   for p in pages:
    await p.wait_for_function('document.body.classList.contains("tournament")',timeout=10000)
    text=await p.locator('#tournamentStatus').text_content()
    assert 'abgebrochen' in text and 'Host' in text,text
    cards=await p.locator('.bracketMatch small').all_text_contents()
    assert cards and all(s=='Abgebrochen' for s in cards),cards
   report['cancellation_reason_and_no_running_matches']=True
   await pages[0].screenshot(path=str(ROOT/'logs/tournament-review-cancelled.png'))
   assert not report['errors'],report['errors']
  finally:
   if original:
    for key,value in original.items():await admin(f'set {key} {value}')
   for p in pages:
    try:await p.evaluate('sendAction({action:"leave"})')
    except Exception:pass
   await browser.close()
 (ROOT/'logs/tournament-review-browser.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
 print(json.dumps(report),flush=True)

if __name__=='__main__':asyncio.run(main())
