"""Real 30-second reconnect grace, resume and automatic walkover advancement."""
import asyncio,json
from aiohttp import ClientSession
from tournament_network import Peer,wait_for,ROOT

async def main():
 report={}
 async with ClientSession() as session:
  peers=[await Peer(session).connect() for _ in range(3)]
  try:
   await peers[0].send(action='tournament_create',character_version=14,name='HOST')
   await wait_for(lambda:peers[0].bracket);code=peers[0].bracket['tournament']['id']
   for i,p in enumerate(peers[1:]):await p.send(action='tournament_join',character_version=14,code=code,name=f'GRACE {i}')
   await wait_for(lambda:len(peers[0].bracket['tournament']['entries'])==3)
   await peers[0].send(action='tournament_start')
   await wait_for(lambda:any(p.state and p.state['phase']=='aim' for p in peers))
   r=next(p.state for p in peers if p.state and p.state['phase']=='aim')
   lost=next(p for p in peers if p.uid==r['players'][0]['id']);other=next(p for p in peers if p.uid==r['players'][1]['id'])
   token=lost.token;uid=lost.uid;await lost.close()
   await wait_for(lambda:other.state['phase']=='disconnected')
   await asyncio.sleep(1);assert other.state['hits']==0
   await lost.connect(token)
   await wait_for(lambda:other.state['phase']=='aim')
   assert lost.uid==uid and other.state['id']==r['id'] and other.state['turn_id']==r['turn_id']
   report['active_resume']=True
   await lost.close()
   await wait_for(lambda:other.state['phase']=='disconnected')
   await wait_for(lambda:other.state['phase']=='over',seconds=34)
   assert other.state['result_reason']=='forfeit' and other.state['players'][other.state['winner']]['id']==other.uid
   report['real_grace_expiry']=True
   await wait_for(lambda:any(p.state and p.state['phase']=='aim' and p.state['id']!=r['id'] for p in peers if not p.ws.closed),seconds=10)
   final=next(p.state for p in peers if not p.ws.closed and p.state and p.state['phase']=='aim')
   assert final['hits']==0 and all(p['points']==0 and p['damage']==0 for p in final['players'])
   await other.send(action='leave')
   winner=next(p for p in peers if p.uid==next(p['id'] for p in final['players'] if p['id']!=other.uid))
   await wait_for(lambda:winner.bracket['tournament']['status']=='finished')
   assert winner.bracket['tournament']['champion']==winner.uid
   report['automatic_final_and_champion']=True
  finally:
   for p in peers:
    if not p.ws.closed:await p.send(action='leave');await p.close()
 (ROOT/'logs/tournament-disconnect.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
 print(json.dumps(report),flush=True)

if __name__=='__main__':asyncio.run(main())
