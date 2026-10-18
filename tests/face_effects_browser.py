"""Production replay bridge/render test with an explicitly severe visual fixture.

Records the unmodified real host event metadata first, then substitutes the
three-hit damage snapshots in the replay response. This is not a played severe
match or an assertion about the physical contact solve for that fixture.
"""
import asyncio,json,os,sys
from pathlib import Path
from playwright.async_api import async_playwright
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'server'))
from face_effects import build_face_effects
URL='http://localhost:'+os.environ.get('BACKENBEBEN_TEST_PORT','8905')

async def main():
    fixture=json.loads((ROOT/'logs/face43-fixture.json').read_text(encoding='utf-8'))
    report={'severe_fixture':True,'real_host_events':None,'stages':[]};errors=[]
    async with async_playwright() as p:
        browser=await p.chromium.launch(executable_path=str(ROOT/'tools/playwright-browsers/chromium-1243/chrome-win64/chrome.exe'),headless=True,
            args=['--disable-background-timer-throttling','--disable-renderer-backgrounding'])
        try:
            page=await browser.new_page(viewport={'width':1600,'height':900})
            page.on('pageerror',lambda e:errors.append(str(e)))
            page.on('console',lambda m:errors.append(m.text) if m.type=='error' else None)
            async def inject(route):
                response=await route.fetch();clip=await response.json()
                original=clip['face_effects'];assert original['version']==1
                target=clip['target']
                expected=[round(max(0.,clip['after'][target]['face_damage']['regions'][r]['bleeding']-clip['before'][target]['face_damage']['regions'][r]['bleeding']),6)
                    for r in ['cheek_L','cheek_R','eye_L','eye_R','jaw_L','jaw_R','mouth','nose']]
                assert original['new_bleeding']==expected
                report['real_host_events']={'count':len(original['events']),'new_bleeding':original['new_bleeding']}
                clip['before'][target].update(fixture['before']);clip['after'][target].update(fixture['after'])
                clip['face_effects']=build_face_effects(fixture['before'],fixture['after'],dict(hit=True,side='L'),clip)
                await route.fulfill(response=response,json=clip)
            await page.route('**/api/replay/*',inject)
            await page.goto(URL);await page.wait_for_function('window.gameReady && window.characterPreviewStats',timeout=60000)
            await page.locator('#training').click();await page.wait_for_function('state?.phase==="aim"')
            for action in ['practice','slap']:
                await page.evaluate('(action)=>sendAction({action,version:3,turn_id:state.turn_id,points:Array.from({length:61},(_,i)=>[.19+.34*i/60,.6,800*i/60,0,-18,0])})',action)
                await page.wait_for_function('state.practice_done' if action=='practice' else 'state.phase==="replay"',timeout=60000)
            await page.locator('#replayImpact').click()
            for index,time in enumerate([.49,.70,1.55,.49]):
                actual=await page.locator('#replaySeek').evaluate('(e,t)=>{e.value=t;e.dispatchEvent(new Event("input",{bubbles:true}));return +e.value}',time)
                await page.wait_for_function('(t)=>Math.abs(godotStats.physics_time-t)<.00001',arg=actual)
                await page.wait_for_function('(t)=>t===.7 ? godotStats.face_effects.tooth>0 && godotStats.face_effects.bone>0 && godotStats.face_effects.blood>0 : t===1.55 ? godotStats.face_effects.stains>0 : godotStats.face_effects.tooth+godotStats.face_effects.bone+godotStats.face_effects.blood+godotStats.face_effects.stains===0',arg=time)
                stats=await page.evaluate('godotStats.face_effects');report['stages'].append(dict(time=actual,**stats))
                await page.screenshot(path=str(ROOT/f'logs/face43-web-{index}.png'))
            assert report['real_host_events'] is not None;assert not errors,errors
            report['errors']=errors;(ROOT/'logs/face43-web-report.json').write_text(json.dumps(report,indent=2))
            print(json.dumps(report))
        finally:await browser.close()

asyncio.run(main())
