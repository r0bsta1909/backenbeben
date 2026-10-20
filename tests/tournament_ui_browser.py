"""Rendered 20-person lobby and narrow result layout, using real peers/forfeit."""
import asyncio,json
from aiohttp import ClientSession
from playwright.async_api import async_playwright
from tournament_network import Peer,wait_for,ROOT,URL

async def main():
 errors=[];peers=[]
 async with ClientSession() as session,async_playwright() as pw:
  browser=await pw.chromium.launch(executable_path=str(ROOT/'tools/playwright-browsers/chromium-1243/chrome-win64/chrome.exe'),headless=True)
  p=await browser.new_page(viewport={'width':1280,'height':800})
  p.on('pageerror',lambda e:errors.append(str(e)))
  p.on('console',lambda m:errors.append(m.text) if m.type=='error' else None)
  try:
   await p.goto(URL);await p.wait_for_function('window.gameReady',timeout=90000)
   await p.locator('#nickname').fill('TURNIER HOST');await p.locator('#tournamentCreate').click()
   await p.wait_for_function('document.body.classList.contains("tournament")')
   code=await p.locator('#tournamentCode').text_content()
   await p.locator('#tournamentCopy').focus();await p.keyboard.press('Space')
   await p.wait_for_function('document.querySelector("#toast").textContent.includes("kopiert")')
   await p.locator('.tournamentRules summary').focus();await p.keyboard.press('Space')
   assert await p.locator('.tournamentRules').evaluate('(e)=>e.open')
   await p.keyboard.press('Space');assert not await p.locator('.tournamentRules').evaluate('(e)=>e.open')
   await p.locator('#helpButton').click();assert await p.locator('#help').is_visible()
   await p.keyboard.press('Escape');assert await p.locator('#help').is_hidden()
   for i in range(19):
    peer=await Peer(session).connect();peers.append(peer)
    await peer.send(action='tournament_join',character_version=14,code=code,name=f'SPIELER {i+2}')
   await p.wait_for_function('document.querySelectorAll(".entrantList li").length===20')
   footer=await p.locator('.tournamentFooter').bounding_box()
   for selector in ('#tournamentStart','#tournamentLeave'):
    action=await p.locator(selector).bounding_box();assert action['y']+action['height']<=footer['y'],(selector,action,footer)
   await p.screenshot(path=str(ROOT/'logs/tournament-20-lobby.png'))
   await p.set_viewport_size({'width':390,'height':844})
   await p.screenshot(path=str(ROOT/'logs/tournament-20-mobile.png'))
   assert await p.evaluate('document.documentElement.scrollWidth<=innerWidth')
   for peer in peers[1:]:await peer.send(action='leave')
   await p.wait_for_function('document.querySelectorAll(".entrantList li").length===2')
   await p.locator('#tournamentStart').click()
   await p.wait_for_function('state?.phase==="aim"')
   assert await p.locator('.names').is_hidden()
   tools=await p.locator('.tools').bounding_box();header=await p.locator('header').bounding_box()
   assert tools['y']>=header['y']+header['height']-2,(tools,header)
   await peers[0].send(action='leave')
   await p.wait_for_function('state?.phase==="over"')
   assert await p.locator('#resultTitle').text_content()=='GEWONNEN.'
   for selector in ('#result','#resultTitle','#resultText','#back'):
    box=await p.locator(selector).bounding_box();assert box and box['x']>=0 and box['x']+box['width']<=390,(selector,box)
   await p.screenshot(path=str(ROOT/'logs/tournament-result-mobile.png'))
   await p.wait_for_function('document.body.classList.contains("tournament")',timeout=10000)
   assert (await p.locator('#tournamentStatus').text_content()).startswith('TURNIERSIEGER:')
   await p.locator('#tournamentLeave').click()
   await p.wait_for_function('!document.body.classList.contains("tournament") && !document.body.classList.contains("playing")')
   assert await p.locator('#tournamentCreate').is_enabled()
   assert not errors,errors
  finally:
   for peer in peers:
    if not peer.ws.closed:await peer.send(action='leave');await peer.close()
   await browser.close()
 report=dict(lobby_20=True,mobile_390=True,forfeit_result=True,no_duplicate_names=True,return_to_lobby=True,errors=errors)
 (ROOT/'logs/tournament-ui.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report),flush=True)

if __name__=='__main__':asyncio.run(main())
