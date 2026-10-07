import asyncio,json,socket
from pathlib import Path
from playwright.async_api import async_playwright

async def main():
    ip=next(i[4][0] for i in socket.getaddrinfo(socket.gethostname(),None,socket.AF_INET) if not i[4][0].startswith(('127.','169.254.')))
    url=f'http://{ip}:8877'
    report={'url':url,'errors':[]}
    async with async_playwright() as p:
        browser=await p.chromium.launch(executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe',headless=True,args=['--enable-webgl'])
        page=await browser.new_page(viewport={'width':1280,'height':800})
        page.on('pageerror',lambda e:report['errors'].append(str(e)))
        page.on('console',lambda m:report['errors'].append(m.text) if m.type=='error' else None)
        await page.goto(url,wait_until='networkidle')
        await page.wait_for_function('window.gameReady===true',timeout=60000)
        report['context']=await page.evaluate('({secure:isSecureContext,worklet:Engine.isAudioWorkletAvailable(),fallback:audioFallback})')
        assert report['context']=={'secure':False,'worklet':False,'fallback':True},report
        assert not await page.locator('#adminButton').is_visible()
        await page.locator('#inputMode').select_option('simple')
        await page.locator('#training').click()
        await page.wait_for_function("JSON.parse(renderState).state.phase==='aim'")
        async def slap():
            await page.wait_for_timeout(150)
            await page.mouse.move(1280*.445,800*.435)
            await page.mouse.down();await page.wait_for_timeout(600);await page.mouse.up()
            await page.wait_for_function("JSON.parse(renderState).state.phase==='windup' && JSON.parse(renderState).state.turn===0",timeout=3000)
        await slap()
        await page.wait_for_function("JSON.parse(renderState).state.phase==='windup' && JSON.parse(renderState).state.turn===1",timeout=10000)
        assert await page.locator('#bracePanel').get_attribute('data-mode')=='waiting'
        assert await page.locator('#braceButton').is_disabled()
        await page.keyboard.press('Space')
        await page.wait_for_function("document.getElementById('bracePanel').dataset.mode==='spent'")
        assert 'ZU FRÜH' in await page.locator('#braceTitle').inner_text()
        await page.screenshot(path='logs/brace-too-early.png')
        await page.wait_for_function("JSON.parse(renderState).state.phase==='recover' && JSON.parse(renderState).state.turn===1")
        report['early_hit']=await page.evaluate('JSON.parse(renderState).state.event')
        assert not report['early_hit']['braced']
        await page.wait_for_function("JSON.parse(renderState).state.phase==='aim' && JSON.parse(renderState).state.turn===0")
        await slap()
        await page.wait_for_function("document.getElementById('bracePanel').dataset.mode==='ready'",timeout=10000,polling=10)
        assert await page.locator('#braceButton').is_enabled()
        await page.locator('#braceButton').click()
        await page.wait_for_function("document.getElementById('bracePanel').dataset.mode==='success'",timeout=1000,polling=10)
        await page.wait_for_function("JSON.parse(renderState).state.phase==='recover' && JSON.parse(renderState).state.turn===1")
        report['timed_hit']=await page.evaluate('JSON.parse(renderState).state.event')
        assert report['timed_hit']['braced']
        report['audio']=await page.evaluate('audioDiagnostics')
        assert report['audio']['unlocked'] and report['audio']['played']>=3 and 'error' not in report['audio'],report
        await page.locator('#lobbyButton').click()
        # A secure localhost browser still uses Godot's regular audio driver.
        local=await browser.new_page(viewport={'width':1280,'height':800})
        local.on('pageerror',lambda e:report['errors'].append(str(e)))
        await local.goto('http://localhost:8877',wait_until='networkidle')
        await local.wait_for_function('window.gameReady===true',timeout=60000)
        report['localhost']=await local.evaluate('({secure:isSecureContext,fallback:audioFallback})')
        assert report['localhost']=={'secure':True,'fallback':False}
        assert not report['errors'],report
        Path('logs/lan-browser-regression.json').write_text(json.dumps(report,indent=2))
        print(json.dumps(report,indent=2))
        await browser.close()

asyncio.run(main())
