"""Repeatable real-Web idle/contact/injury benchmark with one or two clients.

Frame intervals include browser scheduling; CPU samples come from production
instrumentation. This is not a GPU timer or a second-physical-PC test.
"""
import argparse
import asyncio
import json
import os
from pathlib import Path
from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[1]


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--clients', type=int, choices=[1,2], default=2)
    parser.add_argument('--output', default='logs/render-performance.json')
    args = parser.parse_args()
    url = 'http://localhost:'+os.environ.get('BACKENBEBEN_TEST_PORT','8910')
    report = dict(clients=args.clients, viewport=[1920,1080], stages={}, errors=[])
    async with async_playwright() as p:
        browser = await p.chromium.launch(executable_path=str(ROOT/'tools/playwright-browsers/chromium-1243/chrome-win64/chrome.exe'),
            headless=True, args=['--disable-background-timer-throttling','--disable-renderer-backgrounding',
                                '--disable-backgrounding-occluded-windows'])
        try:
            pages = []
            for _ in range(args.clients):
                context = await browser.new_context(viewport={'width':1920,'height':1080})
                await context.add_init_script('window.profileCPU=true')
                page = await context.new_page()
                page.on('pageerror',lambda e:report['errors'].append(str(e)))
                page.on('console',lambda m:report['errors'].append(m.text) if m.type=='error' else None)
                await page.goto(url)
                await page.wait_for_function('window.gameReady && window.characterPreviewStats',timeout=60000)
                pages.append(page)
            for page in pages:
                await page.locator('#training' if args.clients==1 else '#duel').click()
            for page in pages:await page.wait_for_function('state?.phase==="aim"')

            async def measure(label):
                async def frames(page):
                    return await page.evaluate('''()=>new Promise(resolve=>{let values=[],previous=0,warmup=20;
                      function tick(t){if(previous&&warmup<=0)values.push(t-previous);previous=t;warmup--;
                      if(values.length<90)requestAnimationFrame(tick);else{values.sort((a,b)=>a-b);
                      resolve({median_ms:values[45],p95_ms:values[85],max_ms:values[89],fps:godotStats.fps})}}
                      requestAnimationFrame(tick)})''')
                report['stages'][label] = await asyncio.gather(*(frames(page) for page in pages))
                print(label,json.dumps(report['stages'][label]),flush=True)

            await measure('idle')
            attacker = pages[0]
            for action in ['practice','slap']:
                await attacker.evaluate('''action=>sendAction({action,version:3,turn_id:state.turn_id,
                  points:Array.from({length:61},(_,i)=>[.19+.34*i/60,.6,800*i/60,0,-18,0])})''',action)
                await attacker.wait_for_function('state.practice_done' if action=='practice' else 'state.phase==="replay"',timeout=60000)
            for time,label in [(.5,'contact'),(.8,'injured')]:
                for page in pages:
                    await page.wait_for_function('state.phase==="replay"')
                    await page.locator('#replayCamera').select_option('front')
                    actual=await page.locator('#replaySeek').evaluate(
                        '(e,t)=>{e.value=t;e.dispatchEvent(new Event("input",{bubbles:true}));return +e.value}',time)
                    await page.wait_for_function('(t)=>Math.abs(godotStats.physics_time-t)<.00001',arg=actual)
                await measure(label)
            # A paused replay publishes neither dynamic frames nor repeated metadata.
            report['bridge'] = []
            for page in pages:
                before=await page.evaluate('({r:physicsRevision,c:physicsClipRevision,s:physicsClip,m:physicsMotion})')
                await page.evaluate('()=>new Promise(r=>{let n=0;function tick(){if(++n===30)r();else requestAnimationFrame(tick)}requestAnimationFrame(tick)})')
                after=await page.evaluate('({r:physicsRevision,c:physicsClipRevision,s:physicsClip,m:physicsMotion})')
                assert before==after,'Paused bridge kept publishing'
                data=await page.evaluate('({full:JSON.parse(physicsFrame),motion:JSON.parse(physicsMotion),clip:JSON.parse(physicsClip),fullBytes:physicsFrame.length,motionBytes:physicsMotion.length,warm:renderWarmup})')
                assert data['warm']['complete']
                assert data['full']['id']==data['clip']['id']==data['motion']['id']
                assert 'side_cage' not in data['motion'] and 'face_effects' not in data['motion']
                assert data['motionBytes']<data['fullBytes']
                await page.locator('#replayCamera').select_option('side')
                await page.wait_for_function('(r)=>physicsRevision>r',arg=after['r'])
                assert await page.evaluate('physicsClipRevision')==after['c'],'Camera resent static clip'
                await page.wait_for_function('JSON.parse(physicsMotion).camera==="side"')
                r=await page.evaluate('physicsRevision')
                await page.locator('#replayContact').click()
                await page.wait_for_function('(r)=>physicsRevision>r',arg=r)
                await page.locator('#replayCamera').select_option('front')
                report['bridge'].append(dict(full_bytes=data['fullBytes'],motion_bytes=data['motionBytes'],paused_revisions=0,warmup=data['warm']))
            report['cpu'] = []
            for page in pages:
                await page.evaluate('window.profileCPURead=true')
                await page.wait_for_function('window.cpuProfile')
                report['cpu'].append(await page.evaluate('cpuProfile'))
            report['renderer']=await attacker.evaluate('''()=>{const g=document.getElementById('canvas').getContext('webgl2');
                const e=g.getExtension('WEBGL_debug_renderer_info');return g.getParameter(e.UNMASKED_RENDERER_WEBGL)}''')
            await attacker.screenshot(path=str(ROOT/(args.output+'.png')))
            assert not report['errors'],report['errors']
            report['passed']=True
            print(json.dumps(report),flush=True)
        finally:
            (ROOT/args.output).write_text(json.dumps(report,indent=2),encoding='utf-8')
            await browser.close()


if __name__=='__main__':asyncio.run(main())
