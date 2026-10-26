"""Hold the renderer's asset load during a real replay: do not resume early."""
import asyncio
import json
from aiohttp import ClientSession
from playwright.async_api import async_playwright
from tournament_network import Peer,wait_for,ROOT,URL


async def main():
    errors=[];blocked=asyncio.Event();release=asyncio.Event()
    async with ClientSession() as session,async_playwright() as pw:
        browser=await pw.chromium.launch(executable_path=str(ROOT/'tools/playwright-browsers/chromium-1243/chrome-win64/chrome.exe'),headless=True)
        page=await browser.new_page(viewport={'width':1280,'height':800})
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.on('console',lambda m:errors.append(m.text) if m.type=='error' else None)
        sockets=[];page.on('websocket',lambda ws:sockets.append(ws))
        peer=await Peer(session).connect()
        try:
            await peer.send(action='join',mode='duel',character_version=14,name='LOADING TEST')
            await page.goto(URL);await page.wait_for_function('window.gameReady',timeout=90000)
            await page.locator('#duel').click();await wait_for(lambda:peer.state['phase']=='aim')
            uid=await page.evaluate('connectionId');room=peer.state['id']
            stroke=dict(version=3,turn_id=peer.state['turn_id'],points=[[.19+.34*i/60,.64,350*i/60,0,-15,0] for i in range(61)])
            await peer.send(action='practice',**stroke);await wait_for(lambda:peer.state['practice_done'])
            await peer.send(action='slap',**stroke);await wait_for(lambda:peer.state['phase']=='replay',seconds=60)
            await page.wait_for_function('state?.phase==="replay"')
            replay=peer.state['replay_id'];before=len(sockets)
            async def hold(route):
                blocked.set();await release.wait();await route.continue_()
            await page.route('**/index.pck',hold)
            await page.reload(wait_until='domcontentloaded');await asyncio.wait_for(blocked.wait(),20)
            await wait_for(lambda:peer.state['phase']=='disconnected')
            await asyncio.sleep(3)
            assert len(sockets)==before,'Renderer still loading, but socket resumed match'
            assert peer.state['phase']=='disconnected'
            release.set();await page.wait_for_function('window.gameReady && state?.phase==="replay"',timeout=60000)
            assert await page.evaluate('connectionId')==uid
            assert await page.evaluate('state.id')==room
            assert await page.evaluate('state.replay_id')==replay
            assert not errors,errors
        except Exception:
            print(json.dumps({'errors':errors,'startup':await page.evaluate('({ready:window.gameReady,warmup:window.renderWarmup,text:document.querySelector("#loadText")?.textContent})')}),flush=True)
            raise
        finally:
            release.set()
            if not peer.ws.closed:await peer.send(action='leave');await peer.close()
            await browser.close()
    report=dict(real_recorded_replay=True,renderer_asset_delayed=True,held_without_early_socket=True,same_identity_room_clip=True,errors=errors)
    (ROOT/'logs/reload-ready-browser.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))


if __name__=='__main__':asyncio.run(main())
