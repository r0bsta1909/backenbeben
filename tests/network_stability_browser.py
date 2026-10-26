"""Real TCP proxy drops server traffic without closing the client's socket."""
import asyncio
import json
from aiohttp import ClientSession
from playwright.async_api import async_playwright
from tournament_network import ROOT,URL,Peer,wait_for


async def main():
    port=int(URL.rsplit(':',1)[1]);connections=[];tasks=set();muted=False
    async def proxy(reader,writer):
        task=asyncio.current_task();tasks.add(task);upstream=None
        try:
            head=await reader.readuntil(b'\r\n\r\n')
            is_ws=head.split(b'\r\n',1)[0].startswith(b'GET /ws?')
            remote,upstream=await asyncio.open_connection('127.0.0.1',port)
            upstream.write(head);await upstream.drain()
            connection={'muted':False}
            if is_ws:connections.append(connection)
            async def forward(source,destination,downstream=False):
                while data:=await source.read(65536):
                    if downstream and connection['muted']:continue
                    destination.write(data);await destination.drain()
            sides=[asyncio.create_task(forward(reader,upstream)),asyncio.create_task(forward(remote,writer,True))]
            try:await asyncio.wait(sides,return_when=asyncio.FIRST_COMPLETED)
            finally:
                for side in sides:side.cancel()
                await asyncio.gather(*sides,return_exceptions=True)
        except (OSError,asyncio.IncompleteReadError,ConnectionError):pass
        finally:
            writer.close()
            if upstream:upstream.close()
            tasks.discard(task)
    relay=await asyncio.start_server(proxy,'127.0.0.1',0)
    proxy_url='http://127.0.0.1:'+str(relay.sockets[0].getsockname()[1])
    errors=[]
    async with ClientSession() as session,async_playwright() as pw:
        browser=await pw.chromium.launch(executable_path=str(ROOT/'tools/playwright-browsers/chromium-1243/chrome-win64/chrome.exe'),headless=True)
        context=await browser.new_context(viewport={'width':1280,'height':800})
        page=await context.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
        opponent=await Peer(session).connect()
        try:
            await page.goto(proxy_url);await page.wait_for_function('window.gameReady',timeout=90000)
            await page.locator('#duel').click()
            await opponent.send(action='join',mode='duel',character_version=14,name='STABLE PEER')
            await page.wait_for_function('state?.phase==="aim"')
            uid=await page.evaluate('connectionId');room=await page.evaluate('state.id')
            turn=await page.evaluate('state.turn_id')
            # Drop only downstream data: no FIN/RST tells the browser it is offline.
            before=len(connections);connections[-1]['muted']=True
            await page.wait_for_function('document.querySelector("#connection").textContent.includes("unterbrochen")',timeout=19000)
            await page.wait_for_function('socket.readyState===1 && state?.phase==="aim" && document.querySelector("#connection").textContent.includes("VERBUNDEN")',timeout=15000)
            assert len(connections)>before
            assert await page.evaluate('connectionId')==uid
            assert await page.evaluate('state.id')==room
            assert await page.evaluate('state.turn_id')==turn
            assert await page.evaluate('state.hits')==0
            # Simulate a duplicated tab with the inherited private tab token.
            token=await page.evaluate('sessionStorage.getItem("backen-session")')
            duplicate=await context.new_page()
            await duplicate.add_init_script('(token=>sessionStorage.setItem("backen-session",token))('+json.dumps(token)+')')
            await duplicate.goto(proxy_url);await duplicate.wait_for_function('window.gameReady && state?.phase==="aim"',timeout=90000)
            await page.wait_for_function('document.querySelector("#connection").textContent.includes("anderen Tab")')
            await asyncio.sleep(5)
            assert await duplicate.evaluate('socket.readyState')==1
            assert await duplicate.evaluate('connectionId')==uid
            assert await page.evaluate('socket.readyState')==3
            await duplicate.evaluate('sendAction({action:"leave"})');await duplicate.close()
            assert not errors,errors
        finally:
            if not opponent.ws.closed:await opponent.send(action='leave');await opponent.close()
            await browser.close()
    relay.close();await relay.wait_closed()
    for task in list(tasks):task.cancel()
    await asyncio.gather(*tasks,return_exceptions=True)
    report=dict(silent_downstream_loss=True,automatic_resume=True,same_identity_room_turn=True,no_duplicate_tab_reconnect_loop=True,errors=errors,second_physical_pc=False)
    (ROOT/'logs/network-stability-browser.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))


if __name__=='__main__':asyncio.run(main())
