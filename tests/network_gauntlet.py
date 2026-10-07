import asyncio,json,time
from pathlib import Path
import aiohttp
from test_rules import stroke

BASE='http://localhost:8765'
async def match(session,index):
    a=await session.ws_connect(BASE+'/ws');b=await session.ws_connect(BASE+'/ws')
    await a.receive_json();await b.receive_json()
    await a.send_json({'action':'join','mode':'duel','name':f'A{index}'})
    first=await a.receive_json()
    assert first['state']['phase']=='waiting'
    await b.send_json({'action':'join','mode':'duel','name':f'B{index}'})
    sent=set();finals={};notices=0
    async def drive(ws,me):
        nonlocal notices
        while True:
            d=await ws.receive_json(timeout=40)
            if d['type']=='notice':notices+=1;continue
            if d['type']!='state':continue
            r=d['state']
            if r['phase']=='over':finals[me]=r;return
            if r['phase']=='aim' and r['turn']==me and r['turn_id'] not in sent:
                sent.add(r['turn_id'])
                bad={'action':'slap','turn_id':r['turn_id'],'points':[[.4,.4,0],[.5,.4,-1]]}
                await ws.send_json(bad)
                good={'action':'slap','turn_id':r['turn_id'],**stroke()}
                await ws.send_json(good)
                await ws.send_json(good) # must not apply twice
    await asyncio.gather(drive(a,0),drive(b,1))
    assert finals[0]==finals[1], 'Clients disagree'
    assert finals[0]['hits']==len(sent),'Duplicate damage'
    assert notices>=2,'Invalid or duplicate packets were not rejected'
    old=finals[0]['match_id']
    await a.send_json({'action':'rematch'});await b.send_json({'action':'rematch'})
    for ws in (a,b):
        while True:
            d=await ws.receive_json(timeout=5)
            if d['type']=='state' and d['state']['match_id']!=old:
                assert d['state']['turn']==1
                assert all(p['damage']==0 for p in d['state']['players']);break
    await b.close()
    while True:
        d=await a.receive_json(timeout=5)
        if d['type']=='state' and d['state']['phase']=='disconnected':break
    await a.close()
    return {'match':index,'hits':len(sent),'winner':finals[0]['winner'],'rejections':notices,'rematch':True,'disconnect':True}

async def main():
    async with aiohttp.ClientSession() as session:
        # Sequential pairing avoids matching unrelated clients; matches themselves run together.
        tasks=[]
        for i in range(20):
            tasks.append(asyncio.create_task(match(session,i)))
            await asyncio.sleep(.12)
        results=await asyncio.gather(*tasks)
        r=await session.post(BASE+'/api/admin',headers={'Origin':'http://evil.invalid'},json={'command':'set base_damage 40'})
        assert r.status==403
        r=await session.post(BASE+'/api/admin',headers={'Origin':BASE},json={'command':'get'})
        assert r.status==200
        report={'completed_matches':len(results),'results':results,'cross_origin_admin_blocked':True}
        Path('logs/network-gauntlet.json').write_text(json.dumps(report,indent=2))
        print(json.dumps(report,indent=2))

asyncio.run(main())
