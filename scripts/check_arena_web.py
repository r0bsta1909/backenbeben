"""Real Chromium smoke and image check for the standalone arena preview."""
import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[1]

async def main():
    output = ROOT / 'logs' / 'arena-web-preview'
    output.mkdir(parents=True, exist_ok=True)
    errors = []
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(
            executable_path=str(ROOT / 'tools/playwright-browsers/chromium-1243/chrome-win64/chrome.exe'),
            headless=True,
        )
        page = await browser.new_page(viewport={'width': 1600, 'height': 900})
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.on('console', lambda message: errors.append(message.text) if message.type == 'error' else None)
        await page.goto('http://127.0.0.1:8878', wait_until='networkidle')
        await page.wait_for_function('window.arenaReady === true', timeout=60000)
        await page.locator('canvas').click()
        await page.keyboard.press('h')
        await page.wait_for_timeout(4000)
        stats = []
        for number in [4, 1, 2, 3]:
            await page.keyboard.press(str(number))
            await page.wait_for_function(f'window.arenaStats && window.arenaStats.view === {number}', timeout=15000)
            await page.wait_for_timeout(1500)
            await page.screenshot(path=str(output / f'view-{number}.png'))
            stats.append(await page.evaluate('window.arenaStats'))
        await page.keyboard.press('p')
        await page.wait_for_function('window.arenaStats.figures_visible === false')
        resized = []
        for width, height in [(1280, 720), (1280, 1024), (900, 1200)]:
            await page.set_viewport_size({'width': width, 'height': height})
            for number in [4, 1, 2, 3]:
                await page.keyboard.press(str(number))
                await page.wait_for_function(f'window.arenaStats.view === {number}')
                await page.wait_for_timeout(700)
                state = await page.evaluate('window.arenaStats')
                assert not state['figures_visible'], state
                assert state['table_accent'] == (number >= 3), state
                assert abs(state['viewport_width'] / state['viewport_height'] - 16 / 9) < .001, state
                await page.screenshot(path=str(output / f'resize-{width}x{height}-view-{number}.png'))
                resized.append({'browser_size': [width, height], **state})
        await page.keyboard.press('p')
        await page.wait_for_function('window.arenaStats.figures_visible === true')
        report = {'views': stats, 'resize_views': resized, 'errors': errors}
        (output / 'result.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
        print(json.dumps(report, indent=2))
        await browser.close()
        assert not errors, errors
        assert all(item['audience_3d'] == 0 and item['sponsors_3d'] == 6 and item['backdrop_2d'] for item in stats)

asyncio.run(main())
