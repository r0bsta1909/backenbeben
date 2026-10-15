"""Capture three freely combined appearances through real two-client matches.

Uses the real practice/slap/emote protocol and production cameras. Screenshots
are review evidence, not an automated judgement of artistic quality. Extreme
accumulated injury remains covered by the separate native fixture captures.
"""
import asyncio
import json
import os
from pathlib import Path

from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[1]
URL = 'http://localhost:' + os.environ.get('BACKENBEBEN_TEST_PORT', '8901')
OUTPUT = ROOT / 'logs/face-match-review'
COMBINATIONS = [(1, 3, 3, 0), (2, 4, 0, 5), (4, 1, 2, 2)]


async def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    errors, report = [], []
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(
            executable_path=str(ROOT / 'tools/playwright-browsers/chromium-1243/chrome-win64/chrome.exe'),
            headless=True,
            args=['--disable-background-timer-throttling', '--disable-renderer-backgrounding',
                  '--disable-backgrounding-occluded-windows'])
        try:
            for number, (face, hair, beard, skin) in enumerate(COMBINATIONS):
                contexts = [await browser.new_context(viewport={'width':1600,'height':900}) for _ in range(2)]
                try:
                    pages = [await context.new_page() for context in contexts]
                    for page in pages:
                        page.on('pageerror', lambda error: errors.append(str(error)))
                        page.on('console', lambda message: errors.append(message.text) if message.type == 'error' else None)
                        await page.goto(URL)
                        await page.wait_for_function('window.gameReady && window.characterPreviewStats', timeout=60000)
                    attacker, defender = pages
                    for key, value in [('face_style',face), ('hair_style',hair), ('beard_style',beard), ('skin',skin)]:
                        await defender.locator('#' + key).select_option(str(value))
                    await attacker.locator('#duel').click()
                    await defender.locator('#duel').click()
                    await attacker.bring_to_front()
                    await attacker.wait_for_function('state?.phase==="aim" && state.turn===you', timeout=30000)
                    await attacker.wait_for_function('(v)=>godotStats.fighter_face_style===v[0] && godotStats.fighter_hair_style===v[1] && godotStats.fighter_beard_style===v[2]', arg=[face,hair,beard])
                    await attacker.screenshot(path=str(OUTPUT / f'{number}-healthy.png'))
                    for action in ['practice', 'slap']:
                        await attacker.evaluate('(action)=>sendAction({action,version:3,turn_id:state.turn_id,points:Array.from({length:61},(_,i)=>[.19+.34*i/60,.6,800*i/60,0,-18,0])})', action)
                        await attacker.wait_for_function('state.practice_done' if action == 'practice' else 'state.phase==="replay"', timeout=60000)
                    await attacker.locator('#replayImpact').click()
                    await attacker.wait_for_function('JSON.parse(physicsFrame).camera==="contact"')
                    await attacker.locator('#replaySeek').evaluate('e=>{e.value=.8;e.dispatchEvent(new Event("input",{bubbles:true}))}')
                    await attacker.wait_for_function('Math.abs(godotStats.physics_time-.8)<.0001')
                    frame = await attacker.evaluate('JSON.parse(physicsFrame)')
                    damage = frame['display_players'][frame['target']]['face_damage']
                    assert damage['hits'] == 1
                    assert sum(region['load'] for region in damage['regions'].values()) > 0
                    await attacker.screenshot(path=str(OUTPUT / f'{number}-injured-contact.png'))
                    await attacker.locator('#replayCamera').select_option('front')
                    await attacker.wait_for_function('JSON.parse(physicsFrame).camera==="front" && Math.abs(godotStats.camera_position[2]-3.3)<.0001')
                    await attacker.screenshot(path=str(OUTPUT / f'{number}-injured-front.png'))
                    for page in pages:
                        await page.locator('#replaySkip').click()
                    await defender.wait_for_function('state.phase==="recover"', timeout=10000)
                    await defender.evaluate('sendAction({action:"emote",emote:0})')
                    await attacker.wait_for_function('state.event.kind==="emote"', timeout=2000)
                    await attacker.evaluate('()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))')
                    await attacker.screenshot(path=str(OUTPUT / f'{number}-grin.png'))
                    report.append(dict(face=face, hair=hair, beard=beard, skin=skin,
                                       damage_hits=damage['hits'], real_match_emote=True))
                finally:
                    for context in contexts:
                        await context.close()
            assert not errors, errors
            result = dict(combinations=report, errors=errors)
            (OUTPUT / 'report.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
            print(json.dumps(result))
        finally:
            await browser.close()


if __name__ == '__main__':
    asyncio.run(main())
