"""Two real browser clients, LAN HTTP, pointer input, recorded replay and resume."""
import asyncio,json,socket,hashlib
from pathlib import Path
from playwright.async_api import async_playwright

async def main():
    ip=next(i[4][0] for i in socket.getaddrinfo(socket.gethostname(),None,socket.AF_INET) if not i[4][0].startswith(('127.','169.254.')))
    url=f'http://{ip}:8877';report={'url':url,'errors':[],'hits':[]}
    async with async_playwright() as p:
        browser=await p.chromium.launch(executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe',headless=True,args=['--enable-webgl'])
        pages=[]
        for _ in range(2):
            c=await browser.new_context(viewport={'width':1920,'height':1080})
            page=await c.new_page();pages.append(page)
            page.on('pageerror',lambda e:report['errors'].append(str(e)))
            page.on('console',lambda m:report['errors'].append(m.text) if m.type=='error' else None)
            await page.goto(url);await page.wait_for_function('window.gameReady',timeout=60000)
            assert await page.evaluate('audioFallback && !isSecureContext')
        a,b=pages
        async def admin(command):
            response=await a.request.post('http://localhost:8877/api/admin',headers={'Origin':'http://localhost:8877'},data={'command':command})
            assert response.ok
        await admin('set base_damage 45');await admin('set ko_threshold 60');await admin('set turn_seconds 60')
        await a.locator('#nickname').fill('PALM PILOT');await b.locator('#nickname').fill('LAN CHALLENGER')
        await a.locator('#duel').click();await b.locator('#duel').click()
        async def state(page):return await page.evaluate('JSON.parse(renderState).state')
        async def stroke(page):
            await page.bring_to_front();await page.wait_for_timeout(150)
            await page.mouse.move(1920*.19,1080*.49);await page.mouse.down()
            for i in range(18):
                await page.mouse.move(1920*(.19+.28*(i+1)/18),1080*.49)
                await page.wait_for_timeout(7)
            await page.mouse.up()
        for turn in range(8):
            await a.wait_for_function("['aim','over'].includes(JSON.parse(renderState).state.phase)",timeout=15000)
            s=await state(a)
            if s['phase']=='over':break
            attacker=pages[s['turn']];defender=pages[1-s['turn']]
            if turn==0:
                await attacker.mouse.move(1920*.19,1080*.49)
                await attacker.mouse.down(button='right')
                await attacker.mouse.move(1920*.19+40,1080*.49+20,steps=3)
                await attacker.mouse.up(button='right');await attacker.mouse.wheel(0,120)
                await attacker.wait_for_timeout(100)
                pose=await attacker.evaluate('JSON.parse(handPose)')
                assert pose['yaw']>-18 and pose['pitch']>0,pose
                assert pose['position'][2]>.85,pose
                await attacker.locator('#resetPose').click()
                report['wrist_and_reach_controls']=True
            await stroke(attacker)
            await attacker.wait_for_function('JSON.parse(renderState).state.practice_done')
            assert 'Probe:' in (await state(attacker))['diagnosis']
            await stroke(attacker)
            await attacker.wait_for_function("JSON.parse(renderState).state.phase==='windup'",timeout=3000)
            if turn==0:
                await defender.bring_to_front()
                await defender.wait_for_function("document.getElementById('bracePanel').dataset.mode==='ready'",polling=10,timeout=3000)
                await defender.keyboard.press('Space')
            await attacker.wait_for_function("JSON.parse(renderState).state.phase==='impact'",timeout=10000)
            hit=(await state(attacker))['event'];assert hit['damage']>0,hit
            report['hits'].append(hit)
            await attacker.wait_for_function("JSON.parse(renderState).state.phase==='replay'",timeout=6000)
            await defender.wait_for_function("JSON.parse(renderState).state.phase==='replay'",timeout=6000)
            sa,sb=await state(a),await state(b);assert sa['replay_id']==sb['replay_id']
            if turn==0:
                clip=await (await a.request.get(url+'/api/replay/'+sa['replay_id'])).json()
                clip_b=await (await b.request.get(url+'/api/replay/'+sb['replay_id'])).json()
                assert clip==clip_b
                report['clip_hash']=hashlib.sha256(json.dumps(clip,sort_keys=True).encode()).hexdigest()
                peak_i=max(range(len(clip['frames'])),key=lambda i:max(abs(v) for v in clip['frames'][i][2:]))
                peak_t=peak_i/120
                await a.locator('#replaySeek').evaluate('(e,t)=>{e.value=t;e.dispatchEvent(new Event("input"))}',peak_t)
                await a.locator('#replayCamera').select_option('side')
                await a.wait_for_timeout(300);await a.screenshot(path='logs/v2-physics-peak.png')
                d=await a.evaluate('combatDiagnostics');assert d['deformation']>.01,d
                report['replay']=d
                frames=await a.evaluate("() => new Promise(resolve=>{let values=[],last=performance.now();function tick(t){values.push(t-last);last=t;if(values.length<120)requestAnimationFrame(tick);else resolve(values.slice(5));}requestAnimationFrame(tick)})")
                frames.sort();report['replay_frame_ms_p95']=frames[int(len(frames)*.95)]
                report['viewport']=[1920,1080]
                # Browser reload resumes the same seat, room and recorded clip.
                await b.reload();await b.wait_for_function('window.gameReady',timeout=60000)
                await b.wait_for_function("JSON.parse(renderState).state?.phase==='replay'",timeout=5000)
                resumed=await state(b);assert resumed['id']==sb['id'] and resumed['replay_id']==sb['replay_id']
                assert await b.evaluate('JSON.parse(renderState).you')==1
                report['resume']=True
            for page in pages:
                await page.locator('#replaySkip').click()
            await a.wait_for_function("['recover','over'].includes(JSON.parse(renderState).state.phase)",timeout=4000)
            if (await state(a))['phase']=='recover':
                await defender.locator('[data-emote="2"]').click()
                await defender.wait_for_function("JSON.parse(renderState).state.event.kind==='emote'")
        sa,sb=await state(a),await state(b)
        assert sa['phase']==sb['phase']=='over';assert sa['players']==sb['players'] and sa['winner']==sb['winner']
        assert report['hits'][0]['braced'];report['winner']=sa['winner']
        report['audio']=await a.evaluate('audioDiagnostics');assert report['audio']['played']>=2
        await a.screenshot(path='logs/v2-result.png')
        await a.locator('#rematch').click();await b.locator('#rematch').click()
        await a.wait_for_function("JSON.parse(renderState).state.phase==='aim'")
        rematch=await state(a);assert rematch['turn']==1 and all(p['damage']==0 and p['fouls']==0 for p in rematch['players'])
        report['rematch']=True
        await b.locator('#lobbyButton').click()
        await a.wait_for_function("JSON.parse(renderState).state.phase==='disconnected'")
        report['leave']=True
        await admin('set base_damage 35');await admin('set ko_threshold 100');await admin('set turn_seconds 25')
        report['stats']=await a.evaluate('godotStats')
        assert not report['errors'],report['errors']
        Path('logs/v2-browser-gauntlet.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
        print(json.dumps(report,indent=2));await browser.close()

asyncio.run(main())
