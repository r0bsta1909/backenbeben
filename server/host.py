"""Local LAN host: static Godot export + authoritative WebSocket matches."""
import argparse, asyncio, copy, json, math, secrets, socket, time, webbrowser, ipaddress
from pathlib import Path
from aiohttp import web, WSMsgType
from rules import DEFAULTS, RANGES, apply_hit
from body import collapse_track
from contact_v3 import score as v3_score, input_target, collision as arm_collision, decorate as decorate_arm
from arm import Arm, DT, lab_collision

def bot_stroke():
    return {'version':3,'points':[[.19+.34*i/60,.60,800*i/60,0,-15,0] for i in range(61)]}

def skin_state(player):
    return (min(1,player.get('zones',{}).get('L',0)/75),min(1,player.get('zones',{}).get('R',0)/75),max(0,min(1,(player.get('damage',0)-50)/40)))

def score_contact(data,defender=None):
    if data.get("version")!=3:raise ValueError("Veraltete Spielversion. Seite neu laden.")
    return v3_score(dict(data,_skin_state=skin_state(defender or {})))
from tissue import simulate
from concurrent.futures import ProcessPoolExecutor
ROOT = Path(__file__).resolve().parents[1]
ROOMS, CLIENTS, REPLAYS = {}, {}, {}
POOL = None
SETTINGS = dict(DEFAULTS)
REVISION = 1
SEQ = 0
MATCHES = 0
LOG = ROOT/'logs/matches.jsonl'
WINDUP_SECONDS = 1.4


def lan_addresses():
    try:
        addresses = {entry[4][0] for entry in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET)}
    except OSError:
        return []
    return sorted(address for address in addresses if not (ipaddress.ip_address(address).is_loopback or ipaddress.ip_address(address).is_link_local or ipaddress.ip_address(address).is_unspecified))


def record(event):
    LOG.parent.mkdir(exist_ok=True)
    with LOG.open('a', encoding='utf-8') as f:
        f.write(json.dumps(dict(time=time.time(), **event), ensure_ascii=False)+'\n')


def fighter(client=None, bot=False):
    return dict(id=client['id'] if client else 'bot', name=client['name'] if client else 'BRUNO BOT',
                skin=client['skin'] if client else 1, hair=client['hair'] if client else 0,
                shirt=client['shirt'] if client else 0, damage=0., stun=0., side='L', zones={'L':0.,'R':0.}, fouls=0, points=0, bot=bot)


def new_room(client, training):
    global MATCHES
    MATCHES += 1
    rid=secrets.token_hex(3)
    room=dict(id=rid, players=[fighter(client)], members=[client['id']], phase='waiting',
              turn=0, turn_id=0, hits=0, event={}, event_id=0, match_id=MATCHES,
              settings=dict(SETTINGS), revision=REVISION, deadline=0., brace=None,
              emote_used=False, training=training, winner=-1, first=0, practice_done=False, replay_id=None)
    if training:
        room['players'].append(fighter(bot=True))
        room['phase']='aim'; room['turn_id']=1
        room['deadline']=time.monotonic()+SETTINGS['turn_seconds']
    ROOMS[rid]=room
    client['room']=rid
    return room


def public(room):
    now=time.monotonic()
    return {k: room[k] for k in ('id','players','phase','turn','turn_id','hits','event','event_id','match_id','winner','training','revision')} | {'remaining':max(0.,room['deadline']-now),'max_pairs':room['settings']['max_pairs'], 'windup_seconds':WINDUP_SECONDS, 'brace_window_ms':room['settings']['brace_window_ms'], 'brace_used':room['brace'] is not None, 'brace_result':room.get('brace_result',''), 'practice_done':room.get('practice_done',False), 'replay_id':room.get('replay_id'), 'replay_skip':room.get('replay_skip',[]), 'diagnosis':room.get('diagnosis','')}


async def broadcast(room):
    state=public(room)
    for uid in list(room['members']):
        c=CLIENTS.get(uid)
        if c and not c['ws'].closed:
            try: await c['ws'].send_json({'type':'state', 'you':room['members'].index(uid), 'state':state})
            except ConnectionError: pass


def event(room, kind, **kwargs):
    room['event_id']+=1
    room['event']=dict(kind=kind, **kwargs)


async def leave(c):
    room=ROOMS.get(c.get('room'))
    c['room']=None
    if not room: return
    if c['id'] in room['members']: room['members'].remove(c['id'])
    room.pop('suspended',None)
    if room['members']:
        room['phase']='disconnected'; room['deadline']=0
        event(room,'disconnect',text='Gegner hat das Duell verlassen. Zur Lobby für ein neues Duell.')
        await broadcast(room)
    else: ROOMS.pop(room['id'],None)


async def command(c, d):
    action=d.get('action')
    if action=='join':
        await leave(c)
        c['name']=str(d.get('name','CHALLENGER')).strip()[:18] or 'CHALLENGER'
        for key, maximum in [('skin',3),('hair',2),('shirt',3)]:
            value=d.get(key,0)
            c[key]=max(0,min(maximum,int(value))) if isinstance(value,(int,float)) and math.isfinite(value) else 0
        training=d.get('mode')=='training'
        room=next((r for r in ROOMS.values() if r['phase']=='waiting' and not r['training']),None) if not training else None
        if room:
            room['members'].append(c['id']); room['players'].append(fighter(c)); c['room']=room['id']
            room['phase']='aim'; room['turn_id']=1; room['deadline']=time.monotonic()+room['settings']['turn_seconds']
        else: room=new_room(c,training)
        await broadcast(room); return
    if action=='leave':
        await leave(c); await c['ws'].send_json({'type':'lobby'}); return
    room=ROOMS.get(c.get('room'))
    if not room: return
    me=next((i for i,p in enumerate(room['players']) if p['id']==c['id']),-1)
    if me<0: return
    now=time.monotonic()
    if action=='pose':
        if room['phase']!='aim' or room['turn']!=me:return
        values=[d.get(k) for k in ['x','y','progress','tilt']]
        if any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) for v in values):raise ValueError('Ungültige Armhaltung.')
        x,y,progress,tilt=values
        if not(0<=x<=1 and 0<=y<=1 and 0<=progress<=1 and -45<=tilt<=45):raise ValueError('Armziel außerhalb der Grenzen.')
        if c.get('arm_turn')!=room['turn_id'] or d.get('restart') is True:
            c['arm']=Arm(input_target(x,y,0));c['arm_turn']=room['turn_id'];c['arm_time']=now-1/15
        arm=c['arm'];steps=max(1,min(24,round((now-c['arm_time'])/DT)));c['arm_time']=now
        for _ in range(steps):
            arm.drive_torso(.20-.30*max(0,min(1,(x-.19)/.34)))
            pose=arm.step(input_target(x,y,progress),arm_collision(tilt,skin_state(room["players"][1-me])))
        pose=decorate_arm(pose,tilt)
        for uid in room['members']:
            other=CLIENTS.get(uid)
            if other and not other['ws'].closed:
                try:await other['ws'].send_json({'type':'arm_pose','attacker':me,'pose':pose,'tilt':tilt})
                except ConnectionError:pass
        return
    if action=='practice':
        if room['phase']!='aim' or room['turn']!=me or d.get('turn_id')!=room['turn_id']: raise ValueError('Du bist nicht am Zug.')
        preview=score_contact(d,room["players"][1-me])
        room['practice_done']=True;room['diagnosis']='Probe: '+preview['diagnosis']
        event(room,'practice',diagnosis=room['diagnosis']);await broadcast(room);return
    if action=='skip_replay' and room['phase']=='replay':
        ready=room.setdefault('replay_skip',[])
        if me not in ready:ready.append(me)
        if room['training'] or len(ready)==2:room['deadline']=now
        await broadcast(room);return
    if action=='slap':
        if room['phase']!='aim' or room['turn']!=me or d.get('turn_id')!=room['turn_id']:
            raise ValueError('Dieser Schlag ist nicht an der Reihe.')
        if not room.get('practice_done'):raise ValueError('Zuerst den Probeschwung auf EINS ausführen.')
        scored=score_contact(d,room["players"][1-me])
        room['solve']=asyncio.get_running_loop().run_in_executor(POOL,simulate,scored,False)
        room['pending']=scored; room['brace']=None; room['brace_result']=''; room['phase']='windup'; room['deadline']=now+WINDUP_SECONDS
        event(room,'windup',attacker=me); await broadcast(room)
    elif action=='brace':
        if room['phase']=='windup' and me!=room['turn'] and room['brace'] is None:
            room['brace']=now
            remaining=room['deadline']-now
            room['brace_result']='ready' if 0 <= remaining <= room['settings']['brace_window_ms']/1000 else 'early'
            await c['ws'].send_json({'type':'notice','text':'Richtig getimt – du fängst den Schlag ab.' if room['brace_result']=='ready' else 'Zu früh! Dein Versuch ist verbraucht. Beim nächsten Schlag auf GRÜN warten.'})
            await broadcast(room)
        elif room['phase']=='windup' and me!=room['turn']:
            await c['ws'].send_json({'type':'notice','text':'Versuch bereits verbraucht – erst beim nächsten Schlag wieder.'})
        else:
            await c['ws'].send_json({'type':'notice','text':'Anspannen geht nur, wenn der Gegner zuschlägt. Warte auf die grüne Anzeige.'})
    elif action=='emote':
        if room['phase']=='recover' and me!=room['turn'] and not room['emote_used']:
            room['emote_used']=True
            idx=max(0,min(2,int(d.get('emote',0))))
            text=['War das alles?','Noch wach.','Küsschen!'][idx]
            if room['players'][me]['damage']>55: text=['Wa… da… alles?','Mmpf.','Kü… au.'][idx]
            event(room,'emote',player=me,emote=idx,text=text); await broadcast(room)
    elif action=='rematch' and room['phase']=='over':
        ready=room.setdefault('ready',[])
        if me not in ready: ready.append(me)
        if room['training'] or len(ready)==2:
            global MATCHES
            MATCHES+=1; room['match_id']=MATCHES; room['settings']=dict(SETTINGS);room['revision']=REVISION
            for p in room['players']: p['damage']=0.;p['stun']=0.;p['zones']={'L':0.,'R':0.};p['fouls']=0;p['points']=0
            room['practice_done']=False;room['replay_id']=None;room['diagnosis']=''
            room['first']=1-room['first'];room['turn']=room['first'];room['turn_id']+=1
            room['hits']=0;room['winner']=-1;room['phase']='aim';room['ready']=[]
            room['deadline']=now+room['settings']['turn_seconds'];event(room,'start')
            await broadcast(room)
        else: await c['ws'].send_json({'type':'notice','text':'Revanche angefragt – warte auf den Gegner.'})


async def socket_handler(request):
    origin=request.headers.get('Origin')
    if origin and origin not in ('http://'+request.host,'https://'+request.host): return web.Response(status=403)
    ws=web.WebSocketResponse(max_msg_size=24576, heartbeat=20)
    await ws.prepare(request)
    token=request.query.get('resume','')
    old=CLIENTS.get(token)
    if old and old.get('expires',time.monotonic()+1)>time.monotonic():
        previous_ws=old['ws'];c=old;uid=c['id'];c['ws']=ws;c.pop('expires',None)
        if not previous_ws.closed:await previous_ws.close()
    else:
        uid=secrets.token_hex(16);c=dict(id=uid,ws=ws,room=None,name='CHALLENGER',skin=0,hair=0,shirt=0)
        CLIENTS[uid]=c
    await ws.send_json({'type':'hello','id':uid})
    room=ROOMS.get(c.get('room'))
    if room:
        if room.get('suspended') and all(not CLIENTS[m]['ws'].closed for m in room['members'] if m in CLIENTS):
            phase,remaining=room.pop('suspended');room['phase']=phase;room['deadline']=time.monotonic()+remaining
            if room.get('brace') is not None:room['brace']=room['deadline']-room.pop('_brace_offset',0)
        await broadcast(room)
    recent=[]
    try:
        async for msg in ws:
            if msg.type==WSMsgType.TEXT:
                now=time.monotonic();recent=[t for t in recent if now-t<1]
                if len(recent)>25: continue
                recent.append(now)
                try:
                    d=json.loads(msg.data)
                    if not isinstance(d,dict): raise ValueError('Ungültiges Paket')
                    await command(c,d)
                except (ValueError,TypeError,OverflowError,KeyError) as e:
                    await ws.send_json({'type':'notice','text':str(e)[:100]})
    finally:
        if c['ws'] is ws:
            c['expires']=time.monotonic()+30
            room=ROOMS.get(c.get('room'))
            if room:
                if room['phase']!='disconnected':
                    room['suspended']=(room['phase'],max(0,room['deadline']-time.monotonic()))
                    if room.get('brace') is not None:room['_brace_offset']=room['deadline']-room['brace']
                room['phase']='disconnected'
                await broadcast(room)
    return ws


async def tick(app):
    last=0.
    while True:
        await asyncio.sleep(.04)
        now=time.monotonic()
        for uid,c in list(CLIENTS.items()):
            if c.get('expires',now+1)<now:
                await leave(c);CLIENTS.pop(uid,None)
        for r in list(ROOMS.values()):
            phase=r['phase']
            if phase=='aim' and r['players'][r['turn']]['bot'] and r['deadline']-now < r['settings']['turn_seconds']-2.0:
                r['pending']=score_contact(bot_stroke(),r['players'][1-r['turn']]);r['solve']=asyncio.get_running_loop().run_in_executor(POOL,simulate,r['pending'],False)
                r['phase']='windup';r['deadline']=now+WINDUP_SECONDS;r['brace']=None;r['brace_result']='';event(r,'windup',attacker=r['turn']);await broadcast(r)
            elif phase in ('windup','resolving') and now>=r['deadline']:
                if not r['solve'].done():
                    if phase!='resolving':r['phase']='resolving';await broadcast(r)
                    continue
                try:clip=r['solve'].result()
                except Exception as exc:
                    record(dict(kind='physics_error',error=str(exc)));r['phase']='disconnected';event(r,'disconnect',text='Physik konnte nicht berechnet werden. Bitte neues Duell starten.');await broadcast(r);continue
                target=1-r['turn'];p=r['players'][target]
                braced=r['brace'] is not None and 0 <= r['deadline']-r['brace'] <= r['settings']['brace_window_ms']/1000
                before=copy.deepcopy(r['players'])
                damage,ko=apply_hit(p,r['pending'],r['settings'],braced)
                attacker=r['players'][r['turn']]
                if r['pending'].get('foul'):
                    attacker['fouls']+=1
                    if attacker['fouls']>=2:r['winner']=target
                elif r['pending']['hit']:attacker['points']+=round(damage,2)
                if ko:r['winner']=r['turn']
                r['hits']+=1;r['emote_used']=False;r['diagnosis']=r['pending']['diagnosis']
                if braced:
                    for frame in clip['frames']:frame[0]=round(frame[0]*.65,5)
                rid=secrets.token_hex(10);r['replay_id']=rid;r['replay_skip']=[]
                clip.update(id=rid,target=target,attacker=r['turn'],before=before,after=copy.deepcopy(r['players']),
                            turn=r['turn_id'],braced=braced,ko=ko,body_frames=collapse_track(ko),contact_class=r['pending']['contact_class'])
                REPLAYS[rid]=clip
                while len(REPLAYS)>32:REPLAYS.pop(next(iter(REPLAYS)))
                event(r,'hit',target=target,damage=damage,quality=r['pending']['quality'],braced=braced,
                      side=r['pending']['side'],ko=ko,foul=r['pending'].get('foul',False),diagnosis=r['diagnosis'],replay_id=rid)
                record(dict(kind='hit',room=r['id'],match=r['match_id'],turn=r['turn_id'],revision=r['revision'],
                            attacker=r['turn'],scored={k:v for k,v in r['pending'].items() if k not in ('path','arm_path')},damage=damage,braced=braced,solve_ms=clip['solve_ms']))
                r['phase']='impact';r['deadline']=now+clip['duration']
                await broadcast(r)
            elif phase=='impact' and now>=r['deadline']:
                r['phase']='replay';r['deadline']=now+12.;await broadcast(r)
            elif phase=='replay' and now>=r['deadline']:
                if r['winner']>=0:
                    r['phase']='over';r['deadline']=0
                    record(dict(kind='result',match=r['match_id'],winner=r['winner'],first=r['first'],reason='ko_or_foul'))
                else:r['phase']='recover';r['deadline']=now+2.3
                await broadcast(r)
            elif phase=='recover' and now>=r['deadline']:
                if r['hits']>=int(r['settings']['max_pairs'])*2:
                    a,b=r['players'];r['winner']=0 if a['points']>b['points'] else 1 if b['points']>a['points'] else -1
                    r['phase']='over';r['deadline']=0;event(r,'decision',text='Punkteentscheidung')
                    record(dict(kind='result',match=r['match_id'],winner=r['winner'],first=r['first'],reason='points'))
                else:
                    for p in r['players']:p['stun']=max(0,p['stun']-r['settings']['recovery'])
                    r['turn']=1-r['turn'];r['turn_id']+=1;r['phase']='aim';r['practice_done']=False;r['diagnosis']='';r['deadline']=now+r['settings']['turn_seconds']
                    event(r,'turn')
                await broadcast(r)
            elif phase=='aim' and now>=r['deadline']:
                r['pending']=score_contact({'version':3,'points':[[.05,.98,0,0,0,0],[.1,.98,300,0,0,0]]});r['solve']=asyncio.get_running_loop().run_in_executor(POOL,simulate,r['pending'],False);r['phase']='windup';r['deadline']=now;r['brace']=None
            elif now-last>.2: await broadcast(r)
        if now-last>.2:last=now


def local(request):return request.remote in ('127.0.0.1','::1')


async def info(request):
    addresses=lan_addresses()
    return web.json_response({'admin':local(request),'addresses':addresses,'port':request.url.port,'revision':REVISION})


def admin_command(text):
    global REVISION
    args=text.strip().split()
    if not args:return 'help für Befehle'
    if args[0]=='help':return 'get | set PARAM WERT | save | load | reset | status'
    if args[0]=='get':return json.dumps(SETTINGS,indent=2)
    if args[0]=='status':return f'{len(CLIENTS)} Clients, {len(ROOMS)} Räume; Balance-Revision {REVISION}'
    if args[0]=='set' and len(args)==3:
        key=args[1]
        if key not in RANGES:raise ValueError('Unbekannter Parameter')
        val=float(args[2]);lo,hi=RANGES[key]
        if not math.isfinite(val) or not lo<=val<=hi:raise ValueError(f'Erlaubt: {lo} bis {hi}')
        if key=='max_pairs' and val!=int(val):raise ValueError('max_pairs muss ganzzahlig sein')
        SETTINGS[key]=val;REVISION+=1;return f'{key} = {val}. Gilt ab dem nächsten Match.'
    if args[0]=='save':
        (ROOT/'server/balance.json').write_text(json.dumps(SETTINGS,indent=2));return 'Preset gespeichert.'
    if args[0]=='load':
        saved=json.loads((ROOT/'server/balance.json').read_text())
        for k,v in saved.items():
            if k not in RANGES or not isinstance(v,(int,float)) or not math.isfinite(v) or not RANGES[k][0]<=v<=RANGES[k][1]:raise ValueError('Ungültiges Preset')
        SETTINGS.update(saved);REVISION+=1;return 'Preset geladen. Gilt ab dem nächsten Match.'
    if args[0]=='reset':
        for r in ROOMS.values():r['phase']='disconnected';r['deadline']=0;event(r,'disconnect',text='Host hat die Runde beendet. Bitte zurück zur Lobby.')
        return 'Laufende Matches beendet.'
    raise ValueError('Unbekannter Befehl. help zeigt die Befehle.')


async def admin(request):
    if not local(request):return web.Response(status=403)
    if request.headers.get('Origin') not in ('http://'+request.host,'https://'+request.host):return web.Response(status=403)
    try:
        d=await request.json();reply=admin_command(str(d.get('command','')))
        if str(d.get('command','')).strip()=='reset':
            for r in ROOMS.values():await broadcast(r)
        return web.json_response({'reply':reply})
    except (ValueError,TypeError,OSError) as e:return web.json_response({'reply':str(e)},status=400)


async def index(request):return web.FileResponse(ROOT/'build/web/index.html')


async def health(request):return web.json_response({'ok':True,'game':'backenbeben'})


async def replay(request):
    clip=REPLAYS.get(request.match_info['rid'])
    if clip is None:return web.Response(status=404)
    return web.json_response(clip,headers={'Cache-Control':'private, max-age=60'})


def prepare_physics_worker(backend):
    if backend=='coupled':
        from coupled_replay import simulate as prepare
        prepare(v3_score(bot_stroke()))


def physics_worker_ready():return True


async def lifecycle(app):
    global POOL
    backend=app.get('physics_backend','legacy')
    POOL=ProcessPoolExecutor(max_workers=2,initializer=prepare_physics_worker,initargs=(backend,))
    if backend=='coupled':
        print('Gekoppelte Physik wird vorbereitet ...',flush=True)
        await asyncio.gather(*(asyncio.get_running_loop().run_in_executor(POOL,physics_worker_ready) for _ in range(2)))
    def connection_error(loop,context):
        exc=context.get('exception')
        if isinstance(exc,ConnectionResetError) and getattr(exc,'winerror',None)==10054:return
        loop.default_exception_handler(context)
    asyncio.get_running_loop().set_exception_handler(connection_error)
    task=asyncio.create_task(tick(app))
    yield
    task.cancel()
    try:await task
    except asyncio.CancelledError:pass
    for c in list(CLIENTS.values()):await c['ws'].close()
    POOL.shutdown(wait=False,cancel_futures=True)


def main():
    global simulate
    parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=8765);parser.add_argument('--no-browser',action='store_true');parser.add_argument('--no-console',action='store_true');parser.add_argument('--physics',choices=['legacy','coupled'],default='coupled');args=parser.parse_args()
    if args.physics=='coupled':
        try:
            from coupled_replay import simulate as coupled_simulate
        except ModuleNotFoundError as exc:
            raise SystemExit('Host-Abhaengigkeit fehlt: '+str(exc.name)+'. Bitte SETUP_HOST.bat ausfuehren.') from exc
        simulate=coupled_simulate
    if not (ROOT/'build/web/index.pck').exists():raise SystemExit('Web-Build fehlt. Zuerst BUILD_GAME.bat ausführen.')
    app=web.Application(client_max_size=32768);app['physics_backend']=args.physics;app.cleanup_ctx.append(lifecycle)
    app.router.add_get('/api/replay/{rid}',replay);app.router.add_get('/ws',socket_handler);app.router.add_get('/api/info',info);app.router.add_post('/api/admin',admin);app.router.add_get('/health',health);app.router.add_get('/',index)
    app.router.add_static('/',ROOT/'build/web',show_index=False)
    async def start(app):
        url=f'http://localhost:{args.port}'
        addresses=lan_addresses()
        links='\n'.join(f'LAN: http://{address}:{args.port}' for address in addresses) or 'LAN: Keine aktive IPv4-Adresse gefunden. Netzwerkverbindung prüfen.'
        print('\nBACKENBEBEN / HOST\n'+url+'\n'+links+'\nDiese LAN-Adresse auf dem Client öffnen.\nAdmin: help, get, set base_damage 25, save, load, reset, status\n',flush=True)
        if not args.no_browser:asyncio.get_running_loop().call_later(1,webbrowser.open,url)
        if not args.no_console:
            import threading
            loop=asyncio.get_running_loop()
            async def run(text):
                try:print(admin_command(text),flush=True)
                except Exception as e:print(str(e),flush=True)
                for r in ROOMS.values():await broadcast(r)
            def reader():
                while True:
                    try:text=input('balance> ')
                    except (EOFError,OSError):break
                    asyncio.run_coroutine_threadsafe(run(text),loop).result()
            threading.Thread(target=reader,daemon=True).start()
    app.on_startup.append(start)
    web.run_app(app,host='0.0.0.0',port=args.port,access_log=None,print=None)
if __name__=='__main__':main()
