import asyncio, json
from pathlib import Path
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser=await p.chromium.launch(executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe',headless=True,args=['--enable-webgl'])
        page=await browser.new_page(viewport={'width':1440,'height':900})
        errors=[]
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.on('console',lambda m:errors.append(m.text) if m.type=='error' else None)
        await page.goto('http://localhost:8765',wait_until='networkidle')
        try: await page.wait_for_function('window.gameReady===true',timeout=60000)
        except Exception: print('NOT READY')
        await page.screenshot(path='logs/browser-lobby.png')
        print(json.dumps({'ready':await page.evaluate('window.gameReady'),'errors':errors},indent=2))
        if await page.evaluate('window.gameReady'):
            await page.locator('#training').click()
            await page.wait_for_function("document.body.classList.contains('playing')")
            await page.wait_for_timeout(600)
            print('STATS',await page.evaluate('window.godotStats'))
            await page.mouse.move(1440*.22,900*.435)
            await page.mouse.down()
            for i in range(24):
                await page.mouse.move(1440*(.22+(.445-.22)*(i+1)/24),900*.435)
                await page.wait_for_timeout(18)
            await page.mouse.up()
            await page.wait_for_timeout(1600)
            await page.screenshot(path='logs/browser-hit.png')
            print('STATE',await page.evaluate('window.renderState'))
            print('ERRORS',errors)
        Path('logs/browser-errors.json').write_text(json.dumps(errors,indent=2))
        await browser.close()

asyncio.run(main())

