"""20 real WebSockets against an external host; walkovers, not physics load."""
import asyncio,json,os,time
from pathlib import Path
from aiohttp import ClientSession

ROOT=Path(__file__).resolve().parents[1]
URL='http://localhost:'+os.environ.get('BACKENBEBEN_TEST_PORT','8916')

async def wait_for(predicate,seconds=20):
 async with asyncio.timeout(seconds):
  while not predicate():await asyncio.sleep(.05)

class Peer:
 def __init__(self,session):self.session=session;self.state=None;self.bracket=None;self.notices=[];self.ws=None
 async def connect(self,token=''):
  self.ws=await self.session.ws_connect(URL+'/ws',params={'resume':token})
  hello=await self.ws.receive_json();assert hello['type']=='hello';self.uid=hello['id'];self.token=hello['resume']
  self.task=asyncio.create_task(self.read());return self
 async def read(self):
  async for msg in self.ws:
   if msg.type.name!='TEXT':continue
   d=json.loads(msg.data)
   if d['type']=='state':self.state=d['state']
   elif d['type']=='tournament':self.bracket=d
   elif d['type']=='notice':self.notices.append(d['text'])
   elif d['type']=='lobby':self.state=None
 async def send(self,**d):await self.ws.send_json(d)
 async def close(self):
  if self.ws:await self.ws.close();await self.task

async def main():
 report={'transport':'20 real WebSockets, production host','physics_load':False}
 async with ClientSession() as session:
  peers=[]
  try:
   for i in range(21):peers.append(await Peer(session).connect())
   owner=peers[0]
   await owner.send(action='tournament_create',character_version=14,name='VERANSTALTER')
   await wait_for(lambda:owner.bracket)
   code=owner.bracket['tournament']['id']
   for i,p in enumerate(peers[1:]):
    await p.send(action='tournament_join',character_version=14,code=code,name=f'SPIELER {i+1}')
   await wait_for(lambda:len(owner.bracket['tournament']['entries'])==20 and peers[20].notices)
   assert 'voll' in peers[20].notices[-1]
   # Public IDs are not resume tokens and cannot take over another player.
   intruder=await Peer(session).connect(peers[1].uid)
   assert intruder.uid!=peers[1].uid and not peers[1].ws.closed;await intruder.close()
   # Genuine resume restores the same slot without duplicate entry.
   p=peers[1];uid=p.uid;token=p.token;await p.close();await p.connect(token)
   await wait_for(lambda:p.bracket)
   assert p.uid==uid and len(p.bracket['tournament']['entries'])==20
   await peers[2].send(action='tournament_start')
   await wait_for(lambda:peers[2].notices);assert 'Veranstalter' in peers[2].notices[-1]
   await owner.send(action='tournament_start')
   await wait_for(lambda:owner.bracket['tournament']['status']=='running')
   handled=set();champion=None
   async with asyncio.timeout(100):
    while not champion:
     # Find each server-assigned match once and explicitly forfeit its first seat.
     for peer in peers[:20]:
      r=peer.state
      if r and r['phase']=='aim' and r['id'] not in handled:
       handled.add(r['id']);loser=next(p for p in peers if p.uid==r['players'][0]['id'])
       await loser.send(action='leave')
     for peer in peers[:20]:
      if peer.bracket and peer.bracket['tournament']['status']=='finished':champion=peer.bracket['tournament']['champion']
     await asyncio.sleep(.08)
   winner=next(p for p in peers if p.uid==champion)
   await wait_for(lambda:winner.bracket and not winner.bracket['in_match'])
   final=winner.bracket['tournament']
   assert len(handled)==19,(len(handled),final)
   assert sum(m['reason']=='bye' for m in final['rounds'][0])==12
   assert len(final['rounds'])==5 and final['rounds'][-1][0]['winner']==champion
   assert all(m['reason']=='forfeit' for rnd in final['rounds'] for m in rnd if m['reason']!='bye')
   report.update(matches=len(handled),first_round_byes=12,rounds=5,champion=champion,capacity_rejected=True,resume=True,public_id_takeover_rejected=True,owner_guard=True)
  finally:
   for p in peers:
    if p.ws and not p.ws.closed:await p.send(action='leave');await p.close()
 (ROOT/'logs/tournament-network.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
 print(json.dumps(report),flush=True)

if __name__=='__main__':asyncio.run(main())
