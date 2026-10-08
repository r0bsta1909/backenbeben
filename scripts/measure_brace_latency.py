"""Measure real WebSocket windup-to-impact latency with a correctly timed brace."""
import asyncio,json,time,sys,statistics
from pathlib import Path
import aiohttp
ROOT=Path(__file__).resolve().parents[1]
async def state(ws,phase):
 async with asyncio.timeout(20):
  while True:
   message=await ws.receive_json()
   if message.get('type')=='state' and message['state']['phase']==phase:return message['state']
async def main():
 rows=[]
 async with aiohttp.ClientSession() as session:
  for trial in range(3):
   a=await session.ws_connect('http://localhost:8877/ws');b=await session.ws_connect('http://localhost:8877/ws')
   await a.receive_json();await b.receive_json()
   await a.send_json({'action':'join','mode':'duel','name':'TIMING A'})
   await b.send_json({'action':'join','mode':'duel','name':'TIMING B'})
   ready=await state(a,'aim');attacker=[a,b][ready['turn']];defender=[a,b][1-ready['turn']]
   stroke={'version':3,'turn_id':ready['turn_id'],'points':[[.19+.34*i/40,.6,800*i/40,0,-15,0] for i in range(41)]}
   await attacker.send_json(dict(stroke,action='practice'))
   await state(attacker,'aim')
   started=time.perf_counter();await attacker.send_json(dict(stroke,action='slap'))
   windup=await state(attacker,'windup')
   await asyncio.sleep(max(0,windup['remaining']-windup['brace_window_ms']/2000))
   await defender.send_json({'action':'brace'})
   impact=await state(attacker,'impact');elapsed=time.perf_counter()-started
   async with session.get('http://localhost:8877/api/replay/'+impact['replay_id']) as response:clip=await response.json()
   assert clip['physics_backend']=='coupled-moving' and clip['braced'] and clip['head_response']['braced']
   rows.append({'seconds_to_impact':elapsed,'solve_ms':clip['solve_ms'],'normal_impulse_ns':clip['normal_impulse_ns'],'quality':clip['score_update']['quality']})
   await a.send_json({'action':'leave'});await b.send_json({'action':'leave'});await a.close();await b.close()
 report={'trials':rows,'median_seconds':statistics.median(r['seconds_to_impact'] for r in rows)}
 label=sys.argv[1] if len(sys.argv)>1 else 'current'
 if not label.isalnum():raise ValueError('Alphanumeric label required')
 (ROOT/'logs'/('brace-latency-'+label+'.json')).write_text(json.dumps(report,indent=2))
 print(json.dumps(report,indent=2))
asyncio.run(main())
