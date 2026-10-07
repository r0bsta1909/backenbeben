"""Authoritative foul / duplicate / validation regression against port 8877."""
import asyncio,json,sys
from pathlib import Path
import aiohttp
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'server'))
def bot_stroke():return {'points':[[.19+.34*i/40,.60,800*i/40,0,-10,0] for i in range(41)]}

async def receive(ws,predicate,timeout=20):
    async with asyncio.timeout(timeout):
        while True:
            d=await ws.receive_json()
            if predicate(d):return d

async def phase(ws,name):return (await receive(ws,lambda d:d.get('type')=='state' and d['state']['phase']==name))['state']

async def main():
    report={}
    async with aiohttp.ClientSession() as session:
        a=await session.ws_connect('http://localhost:8877/ws');await a.receive_json()
        b=await session.ws_connect('http://localhost:8877/ws');await b.receive_json()
        await a.send_json({'action':'join','mode':'duel','name':'FOUL TEST'})
        await b.send_json({'action':'join','mode':'duel','name':'VALID TEST'})
        for i in range(3):
            s=await phase(a,'aim');attacker=a if s['turn']==0 else b
            points=bot_stroke()['points']
            if s['turn']==0:
                for p in points:p[1]=.35;p[4]=35
            await attacker.send_json({'version':3,'action':'slap','turn_id':s['turn_id'],'points':points})
            notice=await receive(attacker,lambda d:d.get('type')=='notice')
            assert 'Probeschwung' in notice['text'];report['practice_required']=True
            await attacker.send_json({'version':3,'action':'practice','turn_id':s['turn_id'],'points':points})
            await receive(attacker,lambda d:d.get('type')=='state' and d['state']['practice_done'])
            packet={'version':3,'action':'slap','turn_id':s['turn_id'],'points':points}
            await attacker.send_json(packet);await attacker.send_json(packet)
            notice=await receive(attacker,lambda d:d.get('type')=='notice')
            assert 'Reihe' in notice['text'];report['duplicate_rejected']=True
            impact=await phase(a,'impact')
            if s['turn']==0:
                assert impact['event']['foul'] and impact['event']['damage']==0
                assert impact['players'][1]['damage']==0
            else:assert impact['event']['damage']>0
            await phase(a,'replay')
            await a.send_json({'action':'skip_replay'});await b.send_json({'action':'skip_replay'})
        result=await phase(a,'over');assert result['winner']==1 and result['players'][0]['fouls']==2
        report['foul_disqualification']=True
        await a.send_json({'action':'rematch'});await b.send_json({'action':'rematch'})
        rematch=await phase(a,'aim');assert rematch['turn']==1 and all(p['fouls']==0 for p in rematch['players'])
        report['rematch_clears_fouls']=True
        bad=bot_stroke()['points'];bad[3][3]=999
        await b.send_json({'version':3,'action':'practice','points':bad,'turn_id':rematch['turn_id']})
        notice=await receive(b,lambda d:d.get('type')=='notice');assert 'Grenzen' in notice['text']
        report['out_of_range_rejected']=True
        await b.send_json({'action':'practice','points':bot_stroke()['points'],'turn_id':rematch['turn_id']})
        notice=await receive(b,lambda d:d.get('type')=='notice');assert 'Veraltete' in notice['text']
        report['legacy_scoring_rejected']=True
        await a.send_json({'action':'leave'});await b.send_json({'action':'leave'})
        await a.close();await b.close()
    Path('logs/v3-network-gauntlet.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))

asyncio.run(main())
