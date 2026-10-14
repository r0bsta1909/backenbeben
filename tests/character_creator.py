"""Live character preview, local persistence and two-client appearance sync."""
import asyncio, json, os, sys
from pathlib import Path
from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[1]
URL = 'http://localhost:' + os.environ.get('BACKENBEBEN_TEST_PORT', '8879')

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(executable_path=str(ROOT / 'tools/playwright-browsers/chromium-1243/chrome-win64/chrome.exe'), headless=True, args=['--disable-background-timer-throttling','--disable-renderer-backgrounding','--disable-backgrounding-occluded-windows'])
        contexts = [await browser.new_context(viewport={'width':1600,'height':900}) for _ in range(2)]
        pages = [await context.new_page() for context in contexts]
        errors = []
        for page in pages:
            page.on('pageerror', lambda e: errors.append(str(e)))
            page.on('console', lambda m: errors.append(m.text) if m.type == 'error' else None)
            await page.goto(URL)
            await page.wait_for_function('window.gameReady && window.characterPreviewStats', timeout=60000)
        a, b = pages
        await a.locator('#nickname').fill('SVEN')
        for key, value in [('skin','6'),('hair','1'),('shirt','2'),('hair_style','5'),('face_style','5'),('beard_style','5'),('beard_color','2')]:
            await a.locator('#'+key).select_option(value)
        await a.wait_for_function('characterPreviewStats.hair_style===5 && characterPreviewStats.face_style===5 && characterPreviewStats.beard_style===5 && characterPreviewStats.options.beard_color===2')
        await a.screenshot(path='logs/character-body.png')
        await a.locator('#characterViewface').click()
        await a.locator('#characterRight').click()
        await a.wait_for_function('characterPreviewStats.camera==="face" && characterPreviewStats.options.yaw===30')
        await a.screenshot(path='logs/character-face.png')
        await a.reload()
        await a.wait_for_function('window.gameReady && characterPreviewStats?.hair_style===5 && characterPreviewStats.face_style===5 && characterPreviewStats.beard_style===5', timeout=60000)
        assert await a.locator('#nickname').input_value() == 'SVEN'
        assert await a.locator('#skin').input_value() == '6'
        # All controls remain reachable at smaller window sizes.
        for width, height in [(1280,720),(900,1200),(600,900)]:
            await a.set_viewport_size({'width':width,'height':height})
            await a.locator('#hair_style').scroll_into_view_if_needed()
            assert await a.locator('#hair_style').is_visible()
            await a.locator('#training').scroll_into_view_if_needed()
            await a.screenshot(path=f'logs/character-{width}x{height}.png')
        await a.set_viewport_size({'width':1600,'height':900})
        await b.locator('#nickname').fill('ROBERT')
        await b.locator('#skin').select_option('5')
        await b.locator('#hair_style').select_option('1')
        await b.locator('#face_style').select_option('4')
        await b.locator('#beard_style').select_option('2')
        await b.locator('[data-character-field="shirt"][data-value="1"]').click()
        await b.wait_for_function('characterPreviewStats.hair_style===1 && characterPreviewStats.options.shirt===1')
        await b.screenshot(path='logs/character-short.png')
        await a.locator('#duel').click()
        await b.locator('#duel').click()
        for page in pages:
            await page.wait_for_function('state?.players?.length===2 && state.phase==="aim"')
            players = await page.evaluate('state.players')
            sven = next(player for player in players if player['name'] == 'SVEN')
            robert = next(player for player in players if player['name'] == 'ROBERT')
            assert (sven['skin'],sven['shirt'],sven['hair'],sven['hair_style'],sven['face_style'],sven['beard_style'],sven['beard_color']) == (6,2,1,5,5,5,2)
            assert robert['skin'] == 5
            assert (robert['shirt'],robert['hair_style'],robert['face_style'],robert['beard_style']) == (1,1,4,2)
            await page.wait_for_function('godotStats?.creator_active===false')
        await a.wait_for_function('godotStats.fighter_hair_style===1 && godotStats.own_hair_style===5 && godotStats.fighter_face_style===4 && godotStats.fighter_beard_style===2')
        await b.wait_for_function('godotStats.fighter_hair_style===5 && godotStats.own_hair_style===1 && godotStats.fighter_face_style===5 && godotStats.fighter_beard_style===5')
        await a.screenshot(path='logs/character-duel.png')
        if '--with-replay' in sys.argv:
            async def strike(page, action):
                # Fixed real protocol trajectory; mouse input has its own replay
                # gauntlet. Avoid depending on background-tab RAF sampling here.
                await page.evaluate('(action)=>sendAction({action,version:3,turn_id:state.turn_id,points:Array.from({length:61},(_,i)=>[.19+.34*i/60,.6,800*i/60,0,-18,0])})', action)
            for striker, defender, face, hair, beard in [(a,b,4,1,2),(b,a,5,5,5)]:
                await striker.bring_to_front()
                await striker.wait_for_function('state.phase==="aim" && state.turn===you', timeout=30000, polling=100)
                await strike(striker,'practice')
                await striker.wait_for_function('state.practice_done', timeout=20000, polling=100)
                await strike(striker,'slap')
                try:
                    await striker.wait_for_function('state.phase==="replay"', timeout=20000)
                except Exception:
                    print(await striker.evaluate('JSON.stringify({state,physics:window.physicsFrame,pose:window.handPose})'))
                    await striker.screenshot(path='logs/character-replay-failure.png')
                    raise
                await striker.locator('#replayImpact').click()
                await striker.wait_for_function('(v)=>godotStats.fighter_face_style===v[0] && godotStats.fighter_hair_style===v[1] && godotStats.fighter_beard_style===v[2] && JSON.parse(physicsFrame).camera==="contact"', arg=[face,hair,beard])
                await striker.screenshot(path=f'logs/character-replay-{face}.png')
                assert await striker.evaluate('JSON.parse(physicsFrame).players[JSON.parse(physicsFrame).target].face_style') == face
                damage_state=await striker.evaluate('JSON.parse(physicsFrame).players[JSON.parse(physicsFrame).target].face_damage')
                assert damage_state['hits']>0 and sum(r['load'] for r in damage_state['regions'].values())>0
                for page in [striker,defender]:
                    await page.bring_to_front()
                    await page.locator('#replaySkip').click()
        await a.locator('#lobbyButton').click()
        await a.wait_for_function('godotStats?.creator_active===true')
        await a.locator('#characterReset').click()
        await a.wait_for_function('characterPreviewStats.hair_style===0 && characterPreviewStats.options.yaw===0')
        assert await a.locator('#nickname').input_value() == 'CHALLENGER'
        await a.locator('#characterRandom').click()
        values = await a.evaluate('window.previewFighter')
        assert all(0 <= values[key] <= limit for key, limit in [('skin',6),('shirt',3),('hair',2),('hair_style',5),('face_style',5),('beard_style',5),('beard_color',2)])
        assert not errors, errors
        print(json.dumps({'live_preview':True,'persistence':True,'rotate_and_zoom':True,'two_client_sync':True,'variant_replays':'--with-replay' in sys.argv,'reset_random':True,'responsive_controls':True,'errors':errors}))
        await browser.close()

asyncio.run(main())
