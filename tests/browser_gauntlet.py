"""Two actual Godot browser clients. Uses real pointer/keyboard input, not synthetic slap RPCs."""
import asyncio,json,statistics,time
from pathlib import Path
from playwright.async_api import async_playwright

async def snapshot(page):
    return await page.evaluate('JSON.parse(window.renderState)')

async def main():
    report={'errors':[],'hits':[]}
    async with async_playwright() as p:
        browser=await p.chromium.launch(executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe',headless=True,args=['--enable-webgl'])
        contexts=[await browser.new_context(viewport={'width':1280,'height':800}) for _ in range(2)]
        pages=[await c.new_page() for c in contexts]
        for page in pages:
            page.on('pageerror',lambda e:report['errors'].append(str(e)))
            page.on('console',lambda m:report['errors'].append(m.text) if m.type=='error' else None)
            await page.goto('http://localhost:8765',wait_until='networkidle')
            await page.wait_for_function('window.gameReady===true',timeout=60000)
        a,b=pages
        await a.locator('#nickname').fill('INK FIST')
        await a.locator('#skin').select_option('2')
        await a.locator('#shirt').select_option('1')
        await b.locator('#nickname').fill('GOLD JAW')
        await b.locator('#skin').select_option('3')
        await b.locator('#hair').select_option('2')
        await b.locator('#shirt').select_option('2')
        await a.screenshot(path='logs/gauntlet-lobby.png')
        await a.locator('#duel').click()
        await a.wait_for_function("JSON.parse(renderState).state.phase==='waiting'")
        await b.locator('#duel').click()
        await a.wait_for_function("JSON.parse(renderState).state.phase==='aim'")
        report['room']=(await snapshot(a))['state']['id']
        report['customization']=(await snapshot(a))['state']['players']
        assert report['customization'][0]['skin']==2
        assert report['customization'][1]['shirt']==2
        await a.locator('#mute').click();assert await a.evaluate('window.muted')
        await a.keyboard.press('m');assert await a.evaluate('window.mirrorFocus')
        await a.wait_for_timeout(250)
        await a.screenshot(path='logs/gauntlet-mirror.png')
        await a.keyboard.press('m')
        last_turn=-1
        for _ in range(14):
            s=(await snapshot(a))['state']
            if s['phase']=='over':break
            await a.wait_for_function("JSON.parse(renderState).state.phase==='aim'||JSON.parse(renderState).state.phase==='over'",timeout=15000)
            s=(await snapshot(a))['state']
            if s['phase']=='over':break
            turn=s['turn'];page=pages[turn];defender=pages[1-turn]
            await page.bring_to_front()
            await page.wait_for_timeout(160)
            # Actual pointer gesture in the Godot canvas; coordinates are normalized by the client.
            await page.mouse.move(1280*.21,800*.435)
            await page.mouse.down()
            for i in range(18):
                await page.mouse.move(1280*(.21+(.445-.21)*(i+1)/18),800*.435)
                await page.wait_for_timeout(16)
            await page.mouse.up()
            await page.wait_for_function("JSON.parse(renderState).state.phase==='windup'",timeout=3000)
            if len(report['hits'])==0:
                await defender.bring_to_front()
                await defender.wait_for_function("JSON.parse(renderState).state.remaining<.27",timeout=2000,polling=20)
                await defender.keyboard.press('Space')
            await page.wait_for_function("['recover','over'].includes(JSON.parse(renderState).state.phase)",timeout=3000)
            current=(await snapshot(page))['state'];hit=current['event']
            assert hit['kind']=='hit' and hit['damage']>0,hit
            report['hits'].append(hit)
            if current['phase']=='recover':
                await defender.bring_to_front()
                await defender.locator('[data-emote="2"]').click()
                await defender.wait_for_function("JSON.parse(renderState).state.event.kind==='emote'",timeout=2000)
                report['emote']=True
            if len(report['hits'])==4:
                await page.screenshot(path='logs/gauntlet-damage.png')
        final_a=(await snapshot(a))['state']
        final_b=(await snapshot(b))['state']
        assert final_a['phase']=='over' and final_b['phase']=='over'
        assert final_a['players']==final_b['players'] and final_a['winner']==final_b['winner']
        assert any(hit['braced'] for hit in report['hits']),'Brace not exercised'
        report['winner']=final_a['winner'];report['synchronized']=True
        await a.screenshot(path='logs/gauntlet-result.png')
        await a.locator('#adminButton').click()
        await a.locator('#adminInput').fill('set base_damage 26')
        await a.locator('#adminForm button').click()
        await a.wait_for_function("document.getElementById('adminLog').textContent.includes('26.0')")
        await a.locator('#adminButton').click()
        old_rev=final_a['revision']
        await a.locator('#rematch').click();await b.locator('#rematch').click()
        await a.wait_for_function("JSON.parse(renderState).state.phase==='aim'")
        r=(await snapshot(a))['state']
        assert r['turn']==1 and r['revision']>old_rev and all(x['damage']==0 for x in r['players'])
        report['rematch_and_balance_revision']=True
        await a.request.post('http://localhost:8765/api/admin',headers={'Origin':'http://localhost:8765'},data={'command':'set base_damage 35'})
        await b.close()
        await a.wait_for_function("JSON.parse(renderState).state.phase==='disconnected'",timeout=5000)
        report['disconnect']=True
        await a.locator('#lobbyButton').click()
        await a.wait_for_function("!document.body.classList.contains('playing')")
        await a.bring_to_front()
        frames=await a.evaluate('''() => new Promise(resolve=>{let a=[],last=performance.now();function tick(t){a.push(t-last);last=t;if(a.length<180)requestAnimationFrame(tick);else resolve(a.slice(5));}requestAnimationFrame(tick)})''')
        frames.sort();report['raf_frame_ms_p95']=round(frames[int(len(frames)*.95)],2)
        report['godot_stats']=await a.evaluate('window.godotStats')
        assert not report['errors'],report['errors']
        Path('logs/browser-gauntlet.json').write_text(json.dumps(report,indent=2))
        print(json.dumps(report,indent=2))
        await browser.close()

asyncio.run(main())
