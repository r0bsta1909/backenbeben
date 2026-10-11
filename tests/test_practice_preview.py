import sys,unittest,copy
from pathlib import Path
from unittest.mock import AsyncMock,patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'server'))
import host
from practice_guidance import tilted_probe
class PreviewTests(unittest.IsolatedAsyncioTestCase):
 async def test_inspection_preserves_match_and_original_and_uses_real_scorer(self):
  data=host.bot_stroke();before=copy.deepcopy(data)
  client={'id':'a','room':'test','ws':AsyncMock()}
  room={'phase':'aim','turn':0,'turn_id':7,'practice_done':True,'practice_id':'saved','practice_data':data,'players':[{'id':'a','damage':0},{'id':'b','damage':0}],'hits':0}
  original=copy.deepcopy(room)
  with patch.dict(host.ROOMS,{'test':room},clear=True):
   await host.command(client,{'action':'inspect_practice','turn_id':7,'practice_id':'saved','tilt':-21})
  self.assertEqual(room,original);self.assertEqual(data,before)
  result=client['ws'].send_json.call_args.args[0]
  expected=host.score_contact(tilted_probe(data,-21),room['players'][1])
  self.assertEqual(result['diagnosis'],expected['diagnosis']);self.assertEqual(result['arm']['tilt'],-21)
  for a,b in zip(data['points'],tilted_probe(data,-21)['points']):self.assertEqual(a[:4]+a[5:],b[:4]+b[5:])
 async def test_stale_or_opponent_requests_do_not_score(self):
  room={'phase':'aim','turn':0,'turn_id':7,'practice_done':True,'practice_id':'saved','players':[{'id':'a'},{'id':'b'}]}
  with patch.dict(host.ROOMS,{'test':room},clear=True),patch.object(host,'score_contact') as score:
   for uid,turn,key in [('b',7,'saved'),('a',6,'saved'),('a',7,'old')]:
    await host.command({'id':uid,'room':'test','ws':AsyncMock()},{'action':'inspect_practice','turn_id':turn,'practice_id':key,'tilt':-15})
   room['phase']='windup'
   await host.command({'id':'a','room':'test','ws':AsyncMock()},{'action':'inspect_practice','turn_id':7,'practice_id':'saved','tilt':-15})
   score.assert_not_called()
 def test_invalid_tilts_rejected(self):
  for value in (True,None,float('nan'),float('inf'),-46,46,'15'):
   with self.assertRaises(ValueError):tilted_probe(host.bot_stroke(),value)
