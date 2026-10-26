"""Competing live reconnects must keep hello first and retain exactly one seat."""
import asyncio
import json
from aiohttp import ClientSession
from tournament_network import Peer,wait_for,ROOT


async def main():
    peers=[]
    async with ClientSession() as session:
        try:
            a=await Peer(session).connect();b=await Peer(session).connect();peers=[a,b]
            for i,p in enumerate(peers):await p.send(action='join',mode='duel',character_version=14,name=f'RACE {i}')
            await wait_for(lambda:a.state and a.state['phase']=='aim')
            room=a.state['id'];uid=a.uid;token=a.token
            replacements=await asyncio.gather(*(Peer(session).connect(token) for _ in range(12)))
            peers+=replacements
            assert all(p.uid==uid for p in replacements)
            await wait_for(lambda:sum(not p.ws.closed for p in [a,*replacements])==1)
            winner=next(p for p in replacements if not p.ws.closed)
            await wait_for(lambda:winner.state and winner.state['phase']=='aim')
            assert winner.state['id']==room and winner.state['hits']==0
            assert len(winner.state['players'])==2
            assert all(p.ws.close_code==4001 for p in [a,*replacements] if p is not winner)
            await winner.send(action='leave')
            await wait_for(lambda:b.state['phase']=='disconnected')
        finally:
            for peer in peers:
                if not peer.ws.closed:await peer.send(action='leave');await peer.close()
    report=dict(competing_live_resumes=12,hello_first=True,same_public_identity=True,single_active_seat=True,old_close_code=4001)
    (ROOT/'logs/resume-race.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))


if __name__=='__main__':asyncio.run(main())
