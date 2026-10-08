"""Two real browser clients, LAN HTTP, pointer input, recorded replay and resume."""
import asyncio,json,socket,hashlib,sys,argparse,time
from pathlib import Path
from playwright.async_api import async_playwright
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"server"))
from rules import DEFAULTS

async def main():
    parser=argparse.ArgumentParser();parser.add_argument("--port",type=int,default=8877)
    options,_=parser.parse_known_args()
    assert 1 <= options.port <= 65535
    ip=next(i[4][0] for i in socket.getaddrinfo(socket.gethostname(),None,socket.AF_INET) if not i[4][0].startswith(('127.','169.254.')))
    skilled='--skilled-standard' in sys.argv
    standard=skilled or '--standard-balance' in sys.argv
    balance=dict(DEFAULTS) if standard else dict(DEFAULTS,base_damage=45,ko_threshold=60,turn_seconds=60)
    url=f'http://{ip}:{options.port}';report={'url':url,'errors':[],'hits':[],'configuration':balance}
    async with async_playwright() as p:
        browser=await p.chromium.launch(executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe',headless=True,args=['--enable-webgl'])
        pages=[]
        for _ in range(2):
            c=await browser.new_context(viewport={'width':1920,'height':1080})
            await c.add_init_script("""(() => {
                const samples={},segments=[];let last=0,previous='',start=0;
                function tick(t){
                    let phase='loading';
                    try { if(window.gameReady){const s=JSON.parse(renderState).state;
                        phase=s?.phase||'lobby';
                        if(phase==='aim')phase=document.getElementById('posePanel')?.dataset.dragging==='true'?'stroke':'aim_idle';
                        if(phase==='replay')phase=document.getElementById('replayPlay')?.textContent==='PAUSE'?'replay_playing':'replay_paused';
                    }} catch (_) {}
                    if(document.hidden)phase='hidden';
                    if(phase!==previous){if(previous)segments.push({phase:previous,ms:t-start});start=t;}
                    else if(last&&phase!=='loading'&&phase!=='hidden'){
                        const list=samples[phase]||(samples[phase]=[]);if(list.length<20000)list.push(t-last);
                    }
                    previous=phase;last=t;requestAnimationFrame(tick);
                }
                window.phasePerformance=()=>({samples,segments:[...segments,{phase:previous,ms:performance.now()-start}],
                    viewport:[innerWidth,innerHeight],devicePixelRatio,hardwareConcurrency:navigator.hardwareConcurrency});
                requestAnimationFrame(tick);
            })();""")
            page=await c.new_page();pages.append(page)
            def record_input(payload):
                try:
                    message=json.loads(payload)
                    if message.get('action') in ('practice','slap'):report.setdefault('sent_inputs',[]).append(message)
                except (ValueError,TypeError):pass
            page.on('websocket',lambda ws:ws.on('framesent',record_input))
            page.on('pageerror',lambda e:report['errors'].append(str(e)))
            page.on('console',lambda m:report['errors'].append(m.text) if m.type=='error' else None)
            await page.goto(url);await page.wait_for_function('window.gameReady',timeout=60000)
            assert await page.evaluate('audioFallback && !isSecureContext')
        a,b=pages
        async def admin(command):
            response=await a.request.post(f'http://localhost:{options.port}/api/admin',headers={'Origin':f'http://localhost:{options.port}'},data={'command':command})
            assert response.ok
            return (await response.json())['reply']
        original_balance=json.loads(await admin('get'))
        try:
            for key,value in balance.items():await admin(f'set {key} {value}')
            assert json.loads(await admin('get'))==balance
            report['skilled_standard']=skilled
            await a.locator('#nickname').fill('PALM PILOT');await b.locator('#nickname').fill('LAN CHALLENGER')
            await a.locator('#duel').click();await b.locator('#duel').click()
            async def state(page):return await page.evaluate('JSON.parse(renderState).state')
            async def stroke(page):
                await page.bring_to_front();await page.wait_for_timeout(150)
                height=.64 if skilled else .6
                await page.mouse.move(1920*.8,1080*height)
                if skilled:
                    await page.wait_for_function('window.netArm?.pose',timeout=5000)
                    tilt=await page.evaluate('netArm.tilt')
                    steps=round((-15-tilt)/3)
                    for _ in range(abs(steps)):await page.mouse.wheel(0,120 if steps>0 else -120)
                    await page.wait_for_function('Math.abs(netArm.tilt+15)<.01')
                await page.mouse.down()
                started=time.perf_counter()
                count=4 if skilled else 12
                for i in range(count):
                    if skilled:await asyncio.sleep(max(0,started+.35*(i+1)/count-time.perf_counter()))
                    await page.mouse.move(1920*(.8-.34/1.5*(i+1)/count),1080*height)
                    if not skilled:await page.wait_for_timeout(8)
                report.setdefault('input_duration_ms',[]).append(round((time.perf_counter()-started)*1000,1))
                await page.mouse.up()
                await page.wait_for_timeout(100)
                print('stroke',report['input_duration_ms'][-1],await page.locator('#toast').text_content(),flush=True)
            for turn in range(12):
                await a.wait_for_function("['aim','over'].includes(JSON.parse(renderState).state.phase)",timeout=15000)
                s=await state(a)
                if s['phase']=='over':break
                attacker=pages[s['turn']];defender=pages[1-s['turn']]
                if turn==0:
                    await attacker.bring_to_front()
                    await attacker.wait_for_function("window.netArm?.pose",timeout=10000)
                    await attacker.mouse.move(1920*.8,1080*.6)
                    await attacker.mouse.wheel(0,120)
                    await attacker.wait_for_function('window.netArm?.tilt > -18',timeout=5000)
                    await attacker.locator('#resetPose').click()
                    report['single_tilt_control']=True
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
                Path('logs/v3-duel-last-attempt.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
                print('HIT',json.dumps({k:hit.get(k) for k in ('damage','quality','ko','braced','contact_class')}),flush=True)
                await attacker.wait_for_function("JSON.parse(renderState).state.phase==='replay'",timeout=6000)
                await defender.wait_for_function("JSON.parse(renderState).state.phase==='replay'",timeout=6000)
                sa,sb=await state(a),await state(b);assert sa['replay_id']==sb['replay_id']
                if turn==0:
                    clip=await (await a.request.get(url+'/api/replay/'+sa['replay_id'])).json()
                    clip_b=await (await b.request.get(url+'/api/replay/'+sb['replay_id'])).json()
                    assert clip==clip_b
                    report['physics_backend']=clip.get('physics_backend','legacy')
                    if '--expect-moving' in sys.argv:
                        assert clip['physics_backend']=='coupled-moving'
                        assert clip['head_response']['braced']==clip['braced']
                        assert clip['head_response']['translation'] is True
                        if '--expect-spatial' in sys.argv:assert clip['head_response']['spatial_rotation'] is True
                        assert len(clip['head_positions'])==len(clip['frames'])
                        report['moving_head_brace_consistent']=True
                    if clip.get('physics_backend') in ('coupled','coupled-moving'):
                        assert clip['contact_active'] and clip['normal_impulse_ns']>0
                        assert clip['score_update']['quality']==hit['quality']
                        report['solved_normal_impulse_ns']=clip['normal_impulse_ns']
                        report['solved_quality_matches_hit']=True
                    if '--expect-friction' in sys.argv:
                        assert clip['friction']['coefficient']==.2
                        assert clip['friction']['maximum_cone_error']<=1e-12
                        report['friction']=clip['friction']
                    assert clip['version']==3 and len(clip['arm_path'])>100
                    report['recorded_arm_frames']=len(clip['arm_path'])
                    report['clip_hash']=hashlib.sha256(json.dumps(clip,sort_keys=True).encode()).hexdigest()
                    if '--expect-brace-expression' in sys.argv:
                        await a.locator('#replaySeek').evaluate('(e)=>{e.value=.4;e.dispatchEvent(new Event("input",{bubbles:true}))}')
                        await a.wait_for_function('JSON.parse(physicsFrame).braced && Math.abs(godotStats.face_eye_closure-.35)<.00001')
                        await a.wait_for_timeout(350)
                        assert abs(await a.evaluate('godotStats.face_eye_closure')-.35)<.00001
                        await a.screenshot(path='logs/brace-expression-contact.png')
                        report['brace_expression_stable_in_paused_replay']=True
                    peak_i=max(range(len(clip['frames'])),key=lambda i:max(abs(v) for v in clip['frames'][i][2:]))
                    peak_t=peak_i/120
                    await a.locator('#replaySeek').evaluate('(e,t)=>{e.value=t;e.dispatchEvent(new Event("input",{bubbles:true}))}',peak_t)
                    await a.locator('#replayCamera').select_option('side')
                    await a.wait_for_timeout(300);await a.screenshot(path='logs/v3-physics-peak.png')
                    d=await a.evaluate('combatDiagnostics');assert d['deformation']>.003,d
                    report['replay']=d
                    frames=await a.evaluate("() => new Promise(resolve=>{let values=[],last=performance.now();function tick(t){values.push(t-last);last=t;if(values.length<120)requestAnimationFrame(tick);else resolve(values.slice(5));}requestAnimationFrame(tick)})")
                    frames.sort();report['replay_frame_ms_p95']=frames[int(len(frames)*.95)]
                    report['viewport']=[1920,1080]
                    report['msaa_3d']=await a.evaluate('godotStats?.msaa_3d ?? null')
                    # Browser reload resumes the same seat, room and recorded clip.
                    await b.reload();await b.wait_for_function('window.gameReady',timeout=60000)
                    await b.wait_for_function("JSON.parse(renderState).state?.phase==='replay'",timeout=5000)
                    resumed=await state(b);assert resumed['id']==sb['id'] and resumed['replay_id']==sb['replay_id']
                    assert await b.evaluate('JSON.parse(renderState).you')==1
                    report['resume']=True
                health_clip=await (await a.request.get(url+'/api/replay/'+sa['replay_id'])).json()
                for moment,key in [(0.9,'after'),(0.2,'before')]:
                    player=health_clip[key][health_clip['target']]
                    expected=[min(1,player['zones'].get(side,0)/75) for side in ['L','R']]+[max(0,min(1,(player['damage']-50)/40))]
                    await a.locator('#replaySeek').evaluate('(e,t)=>{e.value=t;e.dispatchEvent(new Event("input",{bubbles:true}))}',moment)
                    try:
                        await a.wait_for_function('(wanted)=>godotStats.face_injury?.every((v,i)=>Math.abs(v-wanted[i])<1e-5)',arg=expected,timeout=3000)
                    except Exception:
                        print('INJURY_REWIND_FAILURE',json.dumps({'expected':expected,'moment':moment,'actual':await a.evaluate('({state:JSON.parse(renderState).state,frame:JSON.parse(physicsFrame),stats:godotStats})')}),flush=True)
                        await a.screenshot(path='logs/injury-rewind-failure.png')
                        raise
                report['injury_material_rewind']=True
                if hit.get('ko'):
                    ko_clip=await (await a.request.get(url+'/api/replay/'+sa['replay_id'])).json()
                    assert ko_clip['ko'] and len(ko_clip['body_frames'])==337
                    assert ko_clip['body_frames'][-1][0]>.20
                    report['ko_body_recorded']=True
                    await attacker.locator('#replaySeek').evaluate('e=>{e.value=2;e.dispatchEvent(new Event("input",{bubbles:true}))}')
                    await attacker.locator('#replayCamera').select_option('wide')
                    await attacker.wait_for_timeout(250)
                    await attacker.screenshot(path='logs/lateral-ko-side.png')
                    await attacker.locator('#replaySeek').evaluate('e=>{e.value=.2;e.dispatchEvent(new Event("input",{bubbles:true}))}')
                    await attacker.wait_for_timeout(100)
                    frame=await attacker.evaluate('JSON.parse(physicsFrame)')
                    assert frame['body'][0]==0
                    report['ko_reverse_seek']=True
                for page in pages:
                    await page.locator('#replaySkip').click()
                await a.wait_for_function("['recover','over'].includes(JSON.parse(renderState).state.phase)",timeout=4000)
                if (await state(a))['phase']=='recover':
                    await defender.locator('[data-emote="2"]').click()
                    await defender.wait_for_function("JSON.parse(renderState).state.event.kind==='emote'")
            sa,sb=await state(a),await state(b)
            assert sa['phase']==sb['phase']=='over';assert sa['players']==sb['players'] and sa['winner']==sb['winner']
            assert report['hits'][0]['braced'];report['winner']=sa['winner']
            if skilled:assert report.get('ko_body_recorded'), 'Standard skilled duel must reach KO'
            report['audio']=await a.evaluate('audioDiagnostics');assert report['audio']['played']>=2
            await a.screenshot(path='logs/v3-result.png')
            await a.locator('#rematch').click();await b.locator('#rematch').click()
            await a.wait_for_function("JSON.parse(renderState).state.phase==='aim'")
            rematch=await state(a);assert rematch['turn']==1 and all(p['damage']==0 and p['fouls']==0 for p in rematch['players'])
            for page in pages:
                await page.wait_for_function('godotStats.face_injury?.every(v=>v===0) && godotStats.mirror_injury?.every(v=>v===0) && godotStats.face_head_offset?.every(v=>v===0) && godotStats.face_head_rotation?.every(v=>v===0)',timeout=3000)
            report['rematch_material_reset']=True
            report['rematch']=True
            await b.locator('#lobbyButton').click()
            await a.wait_for_function("JSON.parse(renderState).state.phase==='disconnected'")
            report['leave']=True
            report['stats']=await a.evaluate('godotStats')
            performance=await a.evaluate('phasePerformance()')
            phase_summary={}
            for phase,values in performance.pop('samples').items():
                values.sort()
                phase_summary[phase]={'frames':len(values),'median_ms':round(values[len(values)//2],2),'p95_ms':round(values[min(len(values)-1,int(len(values)*.95))],2),'max_ms':round(values[-1],2),'over_33ms':sum(v>33.34 for v in values),'over_50ms':sum(v>50 for v in values),'over_100ms':sum(v>100 for v in values)}
            report['phase_performance']=dict(performance,phases=phase_summary,limits='Browser requestAnimationFrame intervals, not GPU timings. Two headless clients and host share one PC. Transition-crossing frames excluded; phase segment durations retained. Primary client only, including replay inspection pauses.')
            for required in ('aim_idle','stroke','impact','replay_playing','replay_paused'):
                assert phase_summary.get(required,{}).get('frames',0)>0,required
            assert not report['errors'],report['errors']
            output='logs/v3-standard-duel.json' if standard else 'logs/v3-browser-gauntlet.json'
            Path(output).write_text(json.dumps(report,indent=2),encoding='utf-8')
            print(json.dumps(report,indent=2))
        finally:
            Path('logs/v3-duel-last-attempt.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
            for key,value in original_balance.items():await admin(f'set {key} {value}')
            await browser.close()

asyncio.run(main())
