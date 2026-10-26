"""Local LAN host: static Godot export + authoritative WebSocket matches."""
import argparse, asyncio, copy, json, math, secrets, socket, time, webbrowser, ipaddress
from pathlib import Path
from aiohttp import web, WSMsgType
from rules import DEFAULTS, RANGES, apply_hit, fresh_combat, strike_points, head_motion, recover_after_turn
from body import collapse_track
from face_damage import healthy_face,check_character_version
from face_effects import build_face_effects
from contact_v3 import score as v3_score, input_target, collision as arm_collision, decorate as decorate_arm
from arm import Arm, DT, lab_collision
from tournament import Tournament, decision as match_decision
from lan_discovery import serve as serve_discovery

def bot_stroke():
    return {'version':3,'points':[[.19+.34*i/60,.60,800*i/60,0,-18,0] for i in range(61)]}

def skin_state(player):
    legacy=(min(1,player.get('zones',{}).get('L',0)/75),min(1,player.get('zones',{}).get('R',0)/75),max(0,min(1,(player.get('damage',0)-50)/40)))
    if 'face_damage' not in player:return legacy
    from face_damage import REGIONS
    face=player['face_damage']
    jaw=max(face.get('bones',{}).get(name,{}).get('fracture',0.) for name in ('mandible_L','mandible_R','mandible_center'))
    return (*legacy[:2],jaw,*(face.get('regions',{}).get(r['name'],{}).get('swelling',0.) for r in REGIONS),int(player.get('face_style',0)),*(face.get('bones',{}).get(r['bone'],{}).get('fracture',0.) for r in REGIONS))

def score_contact(data,defender=None):
    if data.get("version")!=3:raise ValueError("Veraltete Spielversion. Seite neu laden.")
    return v3_score(dict(data,_skin_state=skin_state(defender or {})))
from tissue import simulate
from concurrent.futures import ProcessPoolExecutor
ROOT = Path(__file__).resolve().parents[1]
ROOMS, CLIENTS, REPLAYS = {}, {}, {}
TOURNAMENTS = {}
POOL = None
PHYSICS_BACKEND = 'legacy'
SETTINGS = dict(DEFAULTS)
REVISION = 1
SEQ = 0
MATCHES = 0
LOG = ROOT/'logs/matches.jsonl'
WINDUP_SECONDS = 1.4
SEND_TIMEOUT = 1.5


def lan_addresses():
    try:
        addresses = {entry[4][0] for entry in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET)}
    except OSError:
        return []
    return sorted(address for address in addresses if not (ipaddress.ip_address(address).is_loopback or ipaddress.ip_address(address).is_link_local or ipaddress.ip_address(address).is_unspecified))


def lobby_snapshot():
    players = []
    for c in CLIENTS.values():
        if c['ws'].closed or not c.get('announced'): continue
        room = ROOMS.get(c.get('room'))
        status = 'tournament' if c.get('tournament') in TOURNAMENTS else ('waiting' if room and room['phase']=='waiting' else 'playing' if room else 'available')
        players.append(dict(id=c['id'],name=c['name'],status=status))
    tournaments = [dict(id=t.id,name=t.entries.get(t.owner,{}).get('name','HOST'),
                        count=len(t.entries),capacity=20)
                   for t in TOURNAMENTS.values() if t.status=='waiting' and len(t.entries)<20]
    return dict(type='lan_lobby',players=players,tournaments=tournaments)


async def send_client(client, message):
    # A blocked receiver must not stop every match on the host.
    ws=client['ws']
    if ws.closed:return False
    try:
        await asyncio.wait_for(ws.send_json(message),SEND_TIMEOUT)
        return True
    except (OSError,TimeoutError):
        if client['ws'] is ws:
            transport=client.get('transport')
            if transport:transport.close()
        return False


async def broadcast_lobby(snapshot):
    await asyncio.gather(*(send_client(c,snapshot) for c in list(CLIENTS.values()) if not c['ws'].closed))


def record(event):
    LOG.parent.mkdir(exist_ok=True)
    with LOG.open('a', encoding='utf-8') as f:
        f.write(json.dumps(dict(time=time.time(), **event), ensure_ascii=False)+'\n')


def fighter(client=None, bot=False):
    return dict(id=client['id'] if client else 'bot', name=client['name'] if client else 'BRUNO BOT',
                skin=client['skin'] if client else 1, hair=client['hair'] if client else 0,
                shirt=client['shirt'] if client else 0, hair_style=client.get('hair_style',0) if client else 0,
                face_style=client.get('face_style',0) if client else 0, beard_style=client.get('beard_style',1) if client else 1,
                beard_color=client.get('beard_color',0) if client else 0,
                **fresh_combat(), side='L', zones={'L':0.,'R':0.}, face_damage=healthy_face(), fouls=0, points=0, bot=bot)


def new_room(client, training):
    global MATCHES
    MATCHES += 1
    rid=secrets.token_hex(3)
    room=dict(id=rid, players=[fighter(client)], members=[client['id']], phase='waiting',
              turn=0, turn_id=0, hits=0, event={}, event_id=0, match_id=MATCHES,
              settings=dict(SETTINGS), revision=REVISION, deadline=0., brace=None,
              emote_used=False, training=training, winner=-1, result_reason='', first=0, practice_done=False, replay_id=None)
    if training:
        room['players'].append(fighter(bot=True))
        room['phase']='aim'; room['turn_id']=1
        room['deadline']=time.monotonic()+SETTINGS['turn_seconds']
    ROOMS[rid]=room
    client['room']=rid
    return room


def public(room):
    now=time.monotonic()
    return {k: room[k] for k in ('id','players','phase','turn','turn_id','hits','event','event_id','match_id','winner','result_reason','training','revision')} | {'remaining':max(0.,room['deadline']-now),'max_pairs':room['settings']['max_pairs'], 'windup_seconds':WINDUP_SECONDS, 'brace_window_ms':room['settings']['brace_window_ms'], 'brace_used':room['brace'] is not None, 'brace_result':room.get('brace_result',''), 'practice_done':room.get('practice_done',False), 'replay_id':room.get('replay_id'), 'replay_skip':room.get('replay_skip',[]), 'diagnosis':room.get('diagnosis',''), 'practice_pose':room.get('practice_pose') if room.get('practice_done') else None, 'practice_id':room.get('practice_id') if room.get('practice_done') else None}


async def broadcast(room):
    state=copy.deepcopy(public(room))
    state['tournament']=room.get('tournament')
    state['tournament_match']=room.get('tournament_match')
    state['cancel_reason']=room.get('cancel_reason','')
    messages=[]
    for uid in list(room['members']):
        c=CLIENTS.get(uid)
        if c and c.get('room')==room['id'] and not c['ws'].closed:
            messages.append(send_client(c,{'type':'state', 'you':next(i for i,p in enumerate(room['players']) if p['id']==uid), 'state':state}))
    await asyncio.gather(*messages)


def event(room, kind, **kwargs):
    room['event_id']+=1
    room['event']=dict(kind=kind, **kwargs)


async def leave(c,prune=True):
    tid=c.pop('tournament',None)
    if tid in TOURNAMENTS:
        tournament=TOURNAMENTS[tid]
        room=ROOMS.get(c.get('room'))
        freeze_tournament_result(room,tournament)
        tournament.withdraw(c['id'])
        room=ROOMS.get(c.get('room'))
        if room and room.get('tournament'):
            # Keep seat order stable for the opponent and turn completed walkovers
            # into ordinary result screens; no pending solve may apply damage.
            if room['phase']!='over':
                winner=tournament.match(room['tournament_match'])['winner']
                room['winner']=next((i for i,p in enumerate(room['players']) if p['id']==winner),-1)
                room['result_reason']='forfeit';room['phase']='over';room['deadline']=0
                room.pop('suspended',None);room.pop('_brace_offset',None)
                room['release_at']=time.monotonic()+6
                if 'solve' in room:room['solve'].cancel()
                await broadcast(room)
            c['room']=None
            await broadcast_tournament(tournament)
            if prune and not any(x.get('tournament')==tid for x in CLIENTS.values()):TOURNAMENTS.pop(tid,None)
            return
        await broadcast_tournament(tournament)
        if prune and not any(x.get('tournament')==tid for x in CLIENTS.values()):TOURNAMENTS.pop(tid,None)
    room=ROOMS.get(c.get('room'))
    c['room']=None
    if not room: return
    if c['id'] in room['members']: room['members'].remove(c['id'])
    room.pop('suspended',None)
    room.pop('_replay_remaining',None)
    if 'solve' in room:room['solve'].cancel()
    if room['members']:
        room['phase']='disconnected'; room['deadline']=0
        event(room,'disconnect',text='Gegner hat das Duell verlassen. Zur Lobby für ein neues Duell.')
        await broadcast(room)
    else: ROOMS.pop(room['id'],None)


def freeze_tournament_result(room,t):
    # KO/DQ are already authoritative during impact/replay, before the result UI.
    if room and room['winner']>=0 and t.status!='cancelled':
        t.finish(room['tournament_match'],room['players'][room['winner']]['id'],room['result_reason'])
        room.update(phase='over',deadline=0)
        room.pop('suspended',None);room.pop('_brace_offset',None)
        room.setdefault('release_at',time.monotonic()+6)


async def expire_clients(now):
    expired={uid:c for uid,c in CLIENTS.items() if c.get('expires',now+1)<now}
    for t in list(TOURNAMENTS.values()):
        batch=[uid for uid,c in expired.items() if c.get('tournament')==t.id]
        if not batch:continue
        for room in list(ROOMS.values()):
            if room.get('tournament')==t.id and any(uid in batch for uid in room['members']):
                freeze_tournament_result(room,t)
        t.withdraw_many(batch)
    # Claim every expired identity before the first send can yield to a resume.
    for uid in expired:CLIENTS.pop(uid,None)
    for c in expired.values():await leave(c,prune=False)
    for tid in list(TOURNAMENTS):
        if not any(c.get('tournament')==tid for c in CLIENTS.values()):TOURNAMENTS.pop(tid,None)


def cancel_tournament(t,reason):
    if t.status not in ('waiting','running'):return
    t.status='cancelled';t.champion=None;t.cancel_reason=reason
    for rnd in t.rounds:
        for m in rnd:
            if m['status']!='done':m.update(status='cancelled',winner=None,reason='cancelled')
    for r in list(ROOMS.values()):
        if r.get('tournament')!=t.id:continue
        r.update(phase='over',winner=-1,result_reason='cancelled',deadline=0,
                 release_at=time.monotonic()+6,cancel_reason=reason)
        r.pop('suspended',None);r.pop('_brace_offset',None)
        if 'solve' in r:r['solve'].cancel()
        event(r,'disconnect',text=reason)


def prune_replays():
    # A slow/paused match must survive replay traffic from parallel matches.
    pinned={r.get('replay_id') for r in ROOMS.values()}
    for rid in list(REPLAYS):
        if len(REPLAYS)<=32:break
        if rid not in pinned:REPLAYS.pop(rid,None)


async def broadcast_tournament(t):
    snapshot=t.public()
    for entry in snapshot['entries']:
        c=CLIENTS.get(entry['id'])
        entry['connected']=bool(c and not c['ws'].closed)
    await asyncio.gather(*(send_client(c,dict(type='tournament',you=c['id'],tournament=snapshot,in_match=c.get('room') in ROOMS))
                           for c in list(CLIENTS.values()) if c.get('tournament')==t.id and not c['ws'].closed))


async def schedule_tournaments(now):
    for room in list(ROOMS.values()):
        if room.get('tournament') and room['phase']=='over':
            t=TOURNAMENTS.get(room['tournament'])
            if 'release_at' not in room:
                room['release_at']=now+6
                if t and room['winner']>=0:
                    t.finish(room['tournament_match'],room['players'][room['winner']]['id'],room['result_reason'])
                    await broadcast_tournament(t)
            if now>=room['release_at']:
                for uid in room['members']:
                    c=CLIENTS.get(uid)
                    if c and c.get('room')==room['id']:c['room']=None
                ROOMS.pop(room['id'],None)
                if t:await broadcast_tournament(t)
    for t in list(TOURNAMENTS.values()):
        if t.status!='running':continue
        changed=False
        for m in t.rounds[-1]:
            if m['status']!='ready':continue
            clients=[CLIENTS.get(uid) for uid in m['players']]
            if any(not c or c['ws'].closed or c.get('room') in ROOMS for c in clients):continue
            a,b=clients
            r=new_room(a,False)
            r.update(tournament=t.id,tournament_match=m['id'],tie_lot=secrets.randbelow(2))
            # All rounds share the settings frozen when the tournament started.
            r['settings']=dict(t.settings);r['revision']=t.revision
            r['players'].append(fighter(b));r['members'].append(b['id']);b['room']=r['id']
            r['first']=secrets.randbelow(2);r['turn']=r['first'];r['turn_id']=1
            r['phase']='aim';r['deadline']=now+r['settings']['turn_seconds']
            m.update(status='playing',room=r['id']);changed=True
            await broadcast(r)
        if changed:await broadcast_tournament(t)


def character(c,d):
    check_character_version(d)
    c['announced']=True
    c['name']=str(d.get('name','CHALLENGER')).strip()[:18] or 'CHALLENGER'
    for key,maximum in [('skin',6),('hair',2),('shirt',3),('hair_style',5),('face_style',5),('beard_style',5),('beard_color',2)]:
        value=d.get(key,1 if key=='beard_style' else 0)
        c[key]=max(0,min(maximum,int(value))) if isinstance(value,(int,float)) and math.isfinite(value) else 0


def start_braced_solve(room):
    if PHYSICS_BACKEND not in ('coupled-moving','coupled-spatial','coupled-friction') or room.get('brace_result')!='ready':
        return False
    previous=room['solve']
    room['solve']=asyncio.get_running_loop().run_in_executor(POOL,simulate,room['pending'],True)
    # Cancellation drops an obsolete queued result. A running process may finish
    # its old calculation, while the other worker handles the accepted brace.
    previous.cancel()
    return True


async def command(c, d):
    action=d.get('action')
    if action=='ping':
        await send_client(c,dict(type='pong'))
        return
    if action=='presence':
        if not c.get('tournament') and c.get('room') not in ROOMS:character(c,d)
        return
    if action in ('tournament_create','tournament_join'):
        if c.get('tournament') or c.get('room') in ROOMS:raise ValueError('Zuerst das aktuelle Spiel oder Turnier verlassen.')
        character(c,d)
        if action=='tournament_create':
            code=secrets.token_hex(3).upper()
            while code in TOURNAMENTS:code=secrets.token_hex(3).upper()
            t=Tournament(code,c['id'],c['name']);TOURNAMENTS[code]=t
        else:
            code=str(d.get('code','')).strip().upper()
            t=TOURNAMENTS.get(code)
            if not t:raise ValueError('Turniercode nicht gefunden.')
            t.add(c['id'],c['name'])
        c['tournament']=t.id
        await broadcast_tournament(t);return
    if action=='tournament_start':
        t=TOURNAMENTS.get(c.get('tournament'))
        if not t:raise ValueError('Kein Turnier ausgewählt.')
        if t.status!='waiting':raise ValueError('Dieses Turnier wurde bereits gestartet oder beendet.')
        if any(CLIENTS[uid]['ws'].closed for uid in t.entries):raise ValueError('Ein Teilnehmer verbindet sich noch. Bitte warten.')
        t.start(c['id']);t.settings=dict(SETTINGS);t.revision=REVISION
        await broadcast_tournament(t);await schedule_tournaments(time.monotonic());return
    if action=='join':
        check_character_version(d)
        await leave(c)
        character(c,d)
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
    if action=='inspect_practice':
        if room['phase']!='aim' or room['turn']!=me or not room.get('practice_done') or d.get('turn_id')!=room['turn_id'] or d.get('practice_id')!=room.get('practice_id'):return
        from practice_guidance import tilted_probe
        candidate=tilted_probe(room['practice_data'],d.get('tilt'))
        if now-c.get('last_practice_inspection',0)<.12:return
        c['last_practice_inspection']=now
        preview=score_contact(candidate,room['players'][1-me])
        records=preview.get('arm_path',[])
        moment=min(records,key=lambda r:abs(r['time']-preview['contact_time'])) if records else None
        await c['ws'].send_json({'type':'practice_preview','turn_id':room['turn_id'],'practice_id':room['practice_id'],'tilt':d['tilt'],'arm':dict(moment,attacker=me) if moment else None,'diagnosis':preview['diagnosis']})
        return
    if action=='practice':
        if room['phase']!='aim' or room['turn']!=me or d.get('turn_id')!=room['turn_id']: raise ValueError('Du bist nicht am Zug.')
        preview=score_contact(d,room["players"][1-me])
        from practice_guidance import wheel_hint
        hint=wheel_hint(d,preview,lambda candidate:score_contact(candidate,room['players'][1-me]))
        records=preview.get('arm_path',[])
        moment=min(records,key=lambda r:abs(r['time']-preview['contact_time'])) if records else None
        room['practice_data']=copy.deepcopy(d);room['practice_id']=secrets.token_hex(6)
        room['practice_pose']=dict(moment,attacker=me) if moment else None
        room['practice_done']=True;room['diagnosis']='Probe: '+preview['diagnosis']+' '+hint
        event(room,'practice',diagnosis=room['diagnosis']);await broadcast(room);return
    if action=='inspect_replay':
        from replay_timing import extend_inspection
        if me not in room.get('replay_skip',[]) and extend_inspection(room,d.get('replay_id'),now):
            await broadcast(room)
        return
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
            start_braced_solve(room)
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
    elif action=='rematch' and room['phase']=='over' and not room.get('tournament'):
        ready=room.setdefault('ready',[])
        if me not in ready: ready.append(me)
        if room['training'] or len(ready)==2:
            global MATCHES
            MATCHES+=1; room['match_id']=MATCHES; room['settings']=dict(SETTINGS);room['revision']=REVISION
            for p in room['players']: p.update(fresh_combat());p['zones']={'L':0.,'R':0.};p['face_damage']=healthy_face();p['fouls']=0;p['points']=0
            room['practice_done']=False;room['replay_id']=None;room['diagnosis']=''
            room['first']=1-room['first'];room['turn']=room['first'];room['turn_id']+=1
            room['hits']=0;room['winner']=-1;room['result_reason']='';room['phase']='aim';room['ready']=[]
            room['deadline']=now+room['settings']['turn_seconds'];event(room,'start')
            await broadcast(room)
        else: await c['ws'].send_json({'type':'notice','text':'Revanche angefragt – warte auf den Gegner.'})


def resume_room(room,now):
    phase,remaining=room.pop('suspended')
    room['phase']=phase;room['deadline']=now+remaining
    if room.get('brace') is not None:room['brace']=room['deadline']-room.pop('_brace_offset',0)
    if '_replay_remaining' in room:room['replay_limit']=now+room.pop('_replay_remaining')


async def socket_handler(request):
    origin=request.headers.get('Origin')
    if origin and origin not in ('http://'+request.host,'https://'+request.host): return web.Response(status=403)
    ws=web.WebSocketResponse(max_msg_size=24576, heartbeat=20)
    await ws.prepare(request)
    token=request.query.get('resume','')
    if len(token)!=64 or any(ch not in '0123456789abcdef' for ch in token):token=''
    # Public bracket/player IDs must never serve as reconnection credentials.
    old=next((c for c in CLIENTS.values() if token and secrets.compare_digest(c.get('resume_token',''),token)),None)
    previous_ws=None
    if old and old.get('expires',time.monotonic()+1)>time.monotonic():
        previous_ws=old['ws'];c=old;uid=c['id'];c['ws']=ws;c.pop('expires',None)
    else:
        uid=secrets.token_hex(16);c=dict(id=uid,resume_token=secrets.token_hex(32),ws=ws,room=None,name='CHALLENGER',skin=0,hair=0,shirt=0)
        CLIENTS[uid]=c
    try:
        c['transport']=request.transport
        await ws.send_json({'type':'hello','id':uid,'resume':c['resume_token']})
        if previous_ws and not previous_ws.closed:await previous_ws.close(code=4001,message=b'Spiel in anderem Tab fortgesetzt')
        if c['ws'] is not ws:
            await ws.close(code=4001);return ws
        room=ROOMS.get(c.get('room'))
        if room:
            if room['phase']=='disconnected' and room.get('suspended') and all(not CLIENTS[m]['ws'].closed for m in room['members'] if m in CLIENTS):
                resume_room(room,time.monotonic())
            await broadcast(room)
        if c.get('tournament') in TOURNAMENTS:await broadcast_tournament(TOURNAMENTS[c['tournament']])
        await ws.send_json(lobby_snapshot())
        recent=[]
        async for msg in ws:
            if c['ws'] is not ws:break
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
    except ConnectionError:pass
    finally:
        if c['ws'] is ws:
            c['expires']=time.monotonic()+30
            room=ROOMS.get(c.get('room'))
            if room:
                if room['phase'] not in ('disconnected','over'):
                    paused_at=time.monotonic()
                    room['suspended']=(room['phase'],max(0,room['deadline']-paused_at))
                    if room['phase']=='replay':room['_replay_remaining']=max(0,room.get('replay_limit',room['deadline'])-paused_at)
                    if room.get('brace') is not None:room['_brace_offset']=room['deadline']-room['brace']
                    room['phase']='disconnected'
                await broadcast(room)
            if c.get('tournament') in TOURNAMENTS:await broadcast_tournament(TOURNAMENTS[c['tournament']])
    return ws


async def tick(app):
    lobby_last=0.;lobby_previous=None
    last=0.
    while True:
        await asyncio.sleep(.04)
        now=time.monotonic()
        await expire_clients(now)
        await schedule_tournaments(now)
        if now-lobby_last>=1:
            snapshot=lobby_snapshot();lobby_last=now
            if snapshot!=lobby_previous:
                await broadcast_lobby(snapshot);lobby_previous=snapshot
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
                    record(dict(kind='physics_error',error=str(exc)))
                    t=TOURNAMENTS.get(r.get('tournament'))
                    if t:
                        cancel_tournament(t,'Technischer Fehler bei der Schlagberechnung. Turnier abgebrochen; bitte neu erstellen.')
                        for affected in list(ROOMS.values()):
                            if affected.get('tournament')==t.id:await broadcast(affected)
                        await broadcast_tournament(t)
                    else:
                        r['phase']='disconnected';event(r,'disconnect',text='Physik konnte nicht berechnet werden. Bitte neues Duell starten.');await broadcast(r)
                    continue
                target=1-r['turn'];p=r['players'][target]
                braced=r['brace'] is not None and 0 <= r['deadline']-r['brace'] <= r['settings']['brace_window_ms']/1000
                if braced and clip.get('head_response',{}).get('model')=='coupled-yaw-through-contact-and-tail' and not clip['head_response'].get('braced'):
                    r['solve']=asyncio.get_running_loop().run_in_executor(POOL,simulate,r['pending'],True)
                    r['phase']='resolving';await broadcast(r);continue
                r['pending'].update(clip.get('score_update',{}))
                if braced:
                    if clip.get('head_response',{}).get('model')=='passive-yaw-after-anchored-contact':
                        from head_response import yaw_state
                        response=clip['head_response']
                        for i,frame in enumerate(clip['frames']):
                            frame[0]=round(yaw_state(response['contact_moment_nms'][1],i/clip['fps']-response['start_time'],True)[0],5)
                        response['braced']=True
                    elif clip.get('head_response',{}).get('model')!='coupled-yaw-through-contact-and-tail':
                        for frame in clip['frames']:frame[0]=round(frame[0]*.65,5)
                before=copy.deepcopy(r['players'])
                motion,yaw=head_motion(clip)
                damage,ko=apply_hit(p,r['pending'],r['settings'],braced,motion)
                awarded=strike_points(r['pending'])
                attacker=r['players'][r['turn']]
                if r['pending'].get('foul'):
                    attacker['fouls']+=1
                    if attacker['fouls']>=2:r['winner']=target;r['result_reason']='disqualification'
                else:attacker['points']+=awarded
                if ko:r['winner']=r['turn'];r['result_reason']='ko'
                r['hits']+=1;r['emote_used']=False;r['diagnosis']=r['pending']['diagnosis']
                rid=secrets.token_hex(10);r['replay_id']=rid;r['replay_skip']=[]
                clip.update(id=rid,target=target,attacker=r['turn'],before=before,after=copy.deepcopy(r['players']),
                            turn=r['turn_id'],braced=braced,ko=ko,body_frames=collapse_track(ko,direction=(1 if yaw>0 else -1) if abs(yaw)>1e-9 else (1 if r['pending']['side']=='L' else -1),lean=.30+.08*motion),head_motion=motion,awarded_points=awarded,contact_class=r['pending']['contact_class'])
                clip['face_effects']=build_face_effects(before[target],r['players'][target],r['pending'],clip)
                REPLAYS[rid]=clip
                prune_replays()
                event(r,'hit',target=target,damage=damage,points=awarded,ko_value=p['ko_value'],head_motion=motion,quality=r['pending']['quality'],braced=braced,
                      side=r['pending']['side'],ko=ko,foul=r['pending'].get('foul',False),diagnosis=r['diagnosis'],replay_id=rid)
                record(dict(kind='hit',room=r['id'],match=r['match_id'],turn=r['turn_id'],revision=r['revision'],
                            attacker=r['turn'],scored={k:v for k,v in r['pending'].items() if k not in ('path','arm_path')},damage=damage,braced=braced,solve_ms=clip['solve_ms']))
                r['phase']='impact';r['deadline']=now+clip['duration']
                await broadcast(r)
            elif phase=='impact' and now>=r['deadline']:
                from replay_timing import REPLAY_SECONDS,MAX_REPLAY_SECONDS
                r['phase']='replay';r['deadline']=now+REPLAY_SECONDS;r['replay_limit']=now+MAX_REPLAY_SECONDS;await broadcast(r)
            elif phase=='replay' and now>=r['deadline']:
                if r['winner']>=0:
                    r['phase']='over';r['deadline']=0
                    record(dict(kind='result',match=r['match_id'],winner=r['winner'],first=r['first'],reason=r['result_reason']))
                else:r['phase']='recover';r['deadline']=now+2.3
                await broadcast(r)
            elif phase=='recover' and now>=r['deadline']:
                recover_after_turn(r['players'],r['hits'],r['settings'])
                decision=match_decision(r)
                if decision is not None:
                    r['winner'],r['result_reason']=decision
                    r['phase']='over';r['deadline']=0;event(r,'decision',text='Unentschieden' if r['winner']<0 else 'Punkteentscheidung')
                    record(dict(kind='result',match=r['match_id'],winner=r['winner'],first=r['first'],reason=r['result_reason']))
                else:
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
        for t in list(TOURNAMENTS.values()):cancel_tournament(t,'Host hat das Turnier beendet.')
        for r in ROOMS.values():
            r['phase']='disconnected';r['deadline']=0;event(r,'disconnect',text='Host hat die Runde beendet. Bitte zurück zur Lobby.')
            if r.get('tournament'):r.update(phase='over',winner=-1,result_reason='cancelled',release_at=time.monotonic())
        return 'Laufende Matches beendet.'
    raise ValueError('Unbekannter Befehl. help zeigt die Befehle.')


async def admin(request):
    if not local(request):return web.Response(status=403)
    if request.headers.get('Origin') not in ('http://'+request.host,'https://'+request.host):return web.Response(status=403)
    try:
        d=await request.json();reply=admin_command(str(d.get('command','')))
        if str(d.get('command','')).strip()=='reset':
            for r in list(ROOMS.values()):await broadcast(r)
            for t in list(TOURNAMENTS.values()):await broadcast_tournament(t)
        return web.json_response({'reply':reply})
    except (ValueError,TypeError,OSError) as e:return web.json_response({'reply':str(e)},status=400)


async def index(request):return web.FileResponse(ROOT/'build/web/index.html')


async def health(request):return web.json_response({'ok':True,'game':'backenbeben'})


async def replay(request):
    clip=REPLAYS.get(request.match_info['rid'])
    if clip is None:return web.Response(status=404)
    return web.json_response(clip,headers={'Cache-Control':'private, max-age=60'})


def prepare_physics_worker(backend):
    if backend in ('coupled','coupled-moving','coupled-spatial','coupled-friction'):
        if backend=='coupled-friction':
            from friction_head_replay import simulate as prepare
        elif backend=='coupled-spatial':
            from spatial_head_replay import simulate as prepare
        elif backend=='coupled-moving':
            from moving_head_replay import simulate as prepare
        else:
            from coupled_replay import simulate as prepare
        prepare(v3_score(bot_stroke()))


def physics_worker_ready():return True


async def lifecycle(app):
    global POOL
    backend=app.get('physics_backend','legacy')
    POOL=ProcessPoolExecutor(max_workers=2,initializer=prepare_physics_worker,initargs=(backend,))
    if backend in ('coupled','coupled-moving','coupled-spatial','coupled-friction'):
        print('Gekoppelte Physik wird vorbereitet ...',flush=True)
        await asyncio.gather(*(asyncio.get_running_loop().run_in_executor(POOL,physics_worker_ready) for _ in range(2)))
    def connection_error(loop,context):
        exc=context.get('exception')
        if isinstance(exc,ConnectionResetError) and getattr(exc,'winerror',None)==10054:return
        loop.default_exception_handler(context)
    asyncio.get_running_loop().set_exception_handler(connection_error)
    discovery=None
    if app.get('discovery_port') is not None:
        try:
            discovery=await serve_discovery(app['http_port'],lambda:dict(players=sum(not c['ws'].closed for c in CLIENTS.values())),app['discovery_port'])
        except OSError as exc:
            print('LAN-Suche nicht verfuegbar: '+str(exc)+'. Beitritt ueber LAN-Link bleibt moeglich.',flush=True)
    task=asyncio.create_task(tick(app))
    yield
    if discovery:discovery.close()
    task.cancel()
    try:await task
    except asyncio.CancelledError:pass
    for c in list(CLIENTS.values()):await c['ws'].close()
    POOL.shutdown(wait=False,cancel_futures=True)


def main():
    global simulate,PHYSICS_BACKEND
    parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=8765);parser.add_argument('--discovery-port',type=int,default=8766);parser.add_argument('--no-browser',action='store_true');parser.add_argument('--no-console',action='store_true');parser.add_argument('--physics',choices=['legacy','coupled','coupled-moving','coupled-spatial','coupled-friction'],default='coupled-friction');args=parser.parse_args()
    PHYSICS_BACKEND=args.physics
    if args.physics in ('coupled','coupled-moving','coupled-spatial','coupled-friction'):
        try:
            if args.physics=='coupled-friction':
                from friction_head_replay import simulate as coupled_simulate
            elif args.physics=='coupled-spatial':
                from spatial_head_replay import simulate as coupled_simulate
            elif args.physics=='coupled-moving':
                from moving_head_replay import simulate as coupled_simulate
            else:
                from coupled_replay import simulate as coupled_simulate
        except ModuleNotFoundError as exc:
            raise SystemExit('Host-Abhaengigkeit fehlt: '+str(exc.name)+'. Bitte SETUP_HOST.bat ausfuehren.') from exc
        simulate=coupled_simulate
    if not (ROOT/'build/web/index.pck').exists():raise SystemExit('Web-Build fehlt. Zuerst BUILD_GAME.bat ausführen.')
    app=web.Application(client_max_size=32768);app['physics_backend']=args.physics;app['http_port']=args.port;app['discovery_port']=args.discovery_port;app.cleanup_ctx.append(lifecycle)
    app.router.add_get('/api/replay/{rid}',replay);app.router.add_get('/ws',socket_handler);app.router.add_get('/api/info',info);app.router.add_post('/api/admin',admin);app.router.add_get('/health',health);app.router.add_get('/',index)
    app.router.add_static('/',ROOT/'build/web',show_index=False)
    async def start(app):
        url=f'http://localhost:{args.port}'
        addresses=lan_addresses()
        links='\n'.join(f'LAN: http://{address}:{args.port}' for address in addresses) or 'LAN: Keine aktive IPv4-Adresse gefunden. Netzwerkverbindung prüfen.'
        print('\nBACKENBEBEN / HOST\n'+url+'\n'+links+'\nLAN_SPIELEN.bat findet diesen Host automatisch. Alternativ diese LAN-Adresse auf dem Client öffnen.\nAdmin: help, get, set base_damage 35, save, load, reset, status\n',flush=True)
        if not args.no_browser:asyncio.get_running_loop().call_later(1,webbrowser.open,url)
        if not args.no_console:
            import threading
            loop=asyncio.get_running_loop()
            async def run(text):
                try:print(admin_command(text),flush=True)
                except Exception as e:print(str(e),flush=True)
                for r in list(ROOMS.values()):await broadcast(r)
                for t in list(TOURNAMENTS.values()):await broadcast_tournament(t)
            def reader():
                while True:
                    try:text=input('balance> ')
                    except (EOFError,OSError):break
                    asyncio.run_coroutine_threadsafe(run(text),loop).result()
            threading.Thread(target=reader,daemon=True).start()
    app.on_startup.append(start)
    web.run_app(app,host='0.0.0.0',port=args.port,access_log=None,print=None)
if __name__=='__main__':main()
