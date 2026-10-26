"""Real UDP discovery, two rendered players, code-free event entry and duels."""
import asyncio
import json
import os
import sys
from pathlib import Path
from aiohttp import ClientSession
from playwright.async_api import async_playwright
from tournament_network import Peer,wait_for,ROOT,URL
sys.path.insert(0,str(ROOT/'server'))
from lan_discovery import discover


async def main():
    assert not await asyncio.to_thread(discover,.5,8924,['127.0.0.1'])
    hosts=await asyncio.to_thread(discover,1.2,int(os.environ.get('BACKENBEBEN_DISCOVERY_PORT','8923')),['127.0.0.1'])
    assert any(h['port']==int(URL.rsplit(':',1)[1]) for h in hosts),hosts
    errors=[]
    async with ClientSession() as session,async_playwright() as pw:
        browser=await pw.chromium.launch(executable_path=str(ROOT/'tools/playwright-browsers/chromium-1243/chrome-win64/chrome.exe'),headless=True)
        contexts=[await browser.new_context(viewport={'width':1280,'height':800}) for _ in range(2)]
        pages=[await c.new_page() for c in contexts]
        for page in pages:
            page.on('pageerror',lambda e:errors.append(str(e)))
            page.on('console',lambda m:errors.append(m.text) if m.type=='error' else None)
        a,b=pages
        peers=[]
        try:
            await asyncio.gather(*(p.goto(URL) for p in pages))
            await asyncio.gather(*(p.wait_for_function('window.gameReady',timeout=90000) for p in pages))
            await a.locator('#nickname').fill('SVEN');await b.locator('#nickname').fill('ROB')
            await a.locator('#lanOpen').click();await b.locator('#lanOpen').click()
            await b.wait_for_function('document.querySelector("#lanPlayers").textContent.includes("SVEN") && document.querySelector("#lanPlayers").textContent.includes("ROB")')
            assert await b.locator('#lanPlayers li').count()==2
            await a.screenshot(path=str(ROOT/'logs/lan-lobby.png'))
            await a.locator('#lanCreate').click()
            await a.wait_for_function('document.body.classList.contains("tournament")')
            await b.wait_for_function('document.querySelectorAll(".lanTournament").length===1')
            await b.locator('.lanTournament button').click()
            await b.wait_for_function('document.querySelectorAll(".entrantList li").length===2')
            assert not await b.locator('#lanPanel').is_visible()
            # New observers see the event disappear at capacity and reappear on leave.
            for i in range(18):
                peer=await Peer(session).connect();peers.append(peer)
                code=await a.locator('#tournamentCode').text_content()
                await peer.send(action='tournament_join',character_version=14,code=code,name=f'LAN {i}')
            await b.wait_for_function('document.querySelectorAll(".entrantList li").length===20')
            observer=await browser.new_page(viewport={'width':390,'height':844})
            await observer.goto(URL);await observer.wait_for_function('window.gameReady',timeout=90000)
            await observer.locator('#lanOpen').click()
            await observer.wait_for_function('document.querySelectorAll("#lanPlayers li").length===21')
            assert await observer.locator('.lanTournament').count()==0
            await observer.evaluate('(code)=>sendAction({...characterPayload(),action:"tournament_join",code})',code)
            await observer.wait_for_function('document.querySelector("#lanNotice").textContent.includes("voll")')
            assert await observer.locator('#lanNotice').is_visible()
            await peers[-1].send(action='leave')
            await observer.wait_for_function('document.querySelectorAll(".lanTournament").length===1')
            await observer.screenshot(path=str(ROOT/'logs/lan-mobile.png'))
            assert await observer.evaluate('document.documentElement.scrollWidth<=innerWidth')
            box=await observer.locator('#lanPanel').bounding_box();assert box['x']>=0 and box['x']+box['width']<=390
            await observer.keyboard.press('Escape');assert await observer.locator('#lanPanel').is_hidden()
            await observer.close()
            for peer in peers:await peer.send(action='leave');await peer.close()
            peers=[]
            for page in pages:await page.locator('#tournamentLeave').click()
            for page in pages:
                await page.locator('#lanOpen').click();await page.locator('#lanQuickDuel').click()
            await asyncio.gather(*(p.wait_for_function('state?.phase==="aim"') for p in pages))
            assert await a.evaluate('state.id')==await b.evaluate('state.id')
            # Genuine socket loss/resume preserves one public player, not a duplicate.
            uid=await b.evaluate('connectionId')
            await b.evaluate('socket.close()')
            await b.wait_for_function('socket.readyState===1 && state?.phase==="aim"',timeout=15000)
            assert await b.evaluate('connectionId')==uid
            for page in pages:await page.evaluate('sendAction({action:"leave"})')
            await b.wait_for_function('!document.body.classList.contains("playing")')
            await b.locator('#lanOpen').click()
            await b.wait_for_function('document.querySelectorAll("#lanPlayers li").length===2')
            assert not errors,errors
        finally:
            for peer in peers:
                if not peer.ws.closed:await peer.send(action='leave');await peer.close()
            await browser.close()
    report=dict(real_udp=True,rendered_clients=2,code_free_join=True,capacity_20=True,mobile_390=True,automatic_duel=True,resume_no_duplicate=True,errors=errors,second_physical_pc=False)
    (ROOT/'logs/lan-browser.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))


if __name__=='__main__':asyncio.run(main())
