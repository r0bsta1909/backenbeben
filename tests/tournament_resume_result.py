"""A disconnected player wins by opponent withdrawal: resume must stay terminal."""
import asyncio,json
from aiohttp import ClientSession
from tournament_network import Peer,wait_for,ROOT

async def main():
 async with ClientSession() as session:
  a,b=[await Peer(session).connect() for _ in range(2)]
  try:
   await a.send(action='tournament_create',character_version=14,name='RESUME WINNER')
   await wait_for(lambda:a.bracket);code=a.bracket['tournament']['id']
   await b.send(action='tournament_join',character_version=14,code=code,name='LEAVING OPPONENT')
   await wait_for(lambda:len(a.bracket['tournament']['entries'])==2)
   await a.send(action='tournament_start')
   await wait_for(lambda:a.state and a.state['phase']=='aim' and b.state and b.state['phase']=='aim')
   token=a.token;rid=a.state['id'];uid=a.uid
   await a.close();await wait_for(lambda:b.state['phase']=='disconnected')
   await b.send(action='leave');await wait_for(lambda:b.state is None)
   a.state=None;a.bracket=None;await a.connect(token)
   await wait_for(lambda:a.state and a.bracket)
   assert a.uid==uid and a.state['id']==rid
   assert a.state['phase']=='over' and a.state['result_reason']=='forfeit',a.state
   assert a.state['players'][a.state['winner']]['id']==uid
   await wait_for(lambda:not a.bracket['in_match'],seconds=10)
   assert a.bracket['tournament']['status']=='finished' and a.bracket['tournament']['champion']==uid
  finally:
   for p in (a,b):
    if not p.ws.closed:await p.send(action='leave');await p.close()
 report=dict(terminal_resume_preserved=True,champion=uid)
 (ROOT/'logs/tournament-resume-result.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report),flush=True)

if __name__=='__main__':asyncio.run(main())
