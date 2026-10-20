import asyncio,copy,json,sys,time,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'server'))
from tournament import Tournament,decision
import host
from unittest.mock import patch


class BracketTests(unittest.TestCase):
 def bracket(self,n):
  t=Tournament('ABC123','0','Player 0')
  for i in range(1,n):t.add(str(i),f'Player {i}')
  return t

 def test_every_count_every_seed_has_one_winner_and_n_minus_one_matches(self):
  for n in range(2,21):
   for run in range(30):
    t=self.bracket(n);t.start('0');played=0;byes=0;participants=[]
    while t.status=='running':
     rnd=list(t.rounds[-1])
     if len(t.rounds)==1:
      participants=[p for m in rnd for p in m['players'] if p]
      byes=sum(m['reason']=='bye' for m in rnd)
     for m in rnd:
      if m['status']=='ready':
       self.assertEqual(len(set(m['players'])),2)
       winner=m['players'][(run+played)%2]
       self.assertTrue(t.finish(m['id'],winner,'points'));played+=1
       self.assertFalse(t.finish(m['id'],winner,'points'))
    self.assertEqual(t.status,'finished');self.assertIn(t.champion,t.entries)
    self.assertEqual(played,n-1);self.assertEqual(set(participants),set(t.entries));self.assertEqual(len(participants),n)
    self.assertEqual(byes,(1<<(n-1).bit_length())-n)

 def test_capacity_owner_start_and_no_late_entry(self):
  t=self.bracket(1)
  with self.assertRaises(ValueError):t.start('0')
  t=self.bracket(20)
  with self.assertRaises(ValueError):t.add('21','Too many')
  with self.assertRaises(ValueError):t.start('1')
  t.start('0')
  with self.assertRaises(ValueError):t.start('0')
  with self.assertRaises(ValueError):t.add('22','Late')

 def test_owner_transfer_and_withdrawal_in_all_rounds(self):
  t=self.bracket(5);t.withdraw('0');self.assertEqual(t.owner,'1');t.start('1')
  t.withdraw('2');t.withdraw('3');t.withdraw('4')
  self.assertEqual(t.status,'finished');self.assertEqual(t.champion,'1')

 def test_snapshot_and_invalid_winner(self):
  t=self.bracket(2);t.start('0');snapshot=t.public();m=t.rounds[0][0]
  with self.assertRaises(ValueError):t.finish(m['id'],'outsider','ko')
  t.finish(m['id'],'0','ko')
  self.assertEqual(snapshot['rounds'][0][0]['status'],'ready')

 def test_batch_withdrawal_every_count_never_awards_an_absent_champion(self):
  for n in range(2,21):
   t=self.bracket(n);t.start('0');t.withdraw_many(list(t.entries))
   self.assertEqual(t.status,'cancelled');self.assertIsNone(t.champion)
   t=self.bracket(n);t.start('0');t.withdraw_many(list(t.entries)[1:])
   self.assertEqual(t.status,'finished');self.assertEqual(t.champion,'0')

 def test_overtime_only_at_complete_pairs_and_lot_after_three(self):
  r=dict(hits=4,settings={'max_pairs':2},players=[{'points':5},{'points':5}],tournament='ABC',tie_lot=1)
  self.assertIsNone(decision(r))
  for hits in (5,6,7,8,9):r['hits']=hits;self.assertIsNone(decision(r))
  r['hits']=10;self.assertEqual(decision(r),(1,'lot'))
  r['players'][0]['points']=6;self.assertEqual(decision(r),(0,'points'))
  r['hits']=5;self.assertIsNone(decision(r))
  r['hits']=4;r['players'][0]['points']=5;r.pop('tournament');self.assertEqual(decision(r),(-1,'draw'))


class FakeSocket:
 closed=False
 def __init__(self):self.messages=[]
 async def send_json(self,d):self.messages.append(json.loads(json.dumps(d)))


class HostTournamentTests(unittest.IsolatedAsyncioTestCase):
 async def asyncSetUp(self):
  host.ROOMS.clear();host.CLIENTS.clear();host.TOURNAMENTS.clear();host.REPLAYS.clear()
  self.settings=dict(host.SETTINGS)

 async def asyncTearDown(self):
  host.SETTINGS.clear();host.SETTINGS.update(self.settings)
  host.ROOMS.clear();host.CLIENTS.clear();host.TOURNAMENTS.clear();host.REPLAYS.clear()

 async def enter(self,n):
  cs=[]
  for i in range(n):
   c=dict(id=str(i),ws=FakeSocket(),room=None);host.CLIENTS[c['id']]=c;cs.append(c)
   d=dict(action='tournament_create' if i==0 else 'tournament_join',character_version=14,name=f'P{i}',code=cs[0].get('tournament'),face_style=i%6)
   await host.command(c,d)
  return cs,host.TOURNAMENTS[cs[0]['tournament']]

 async def test_twenty_player_schedule_fresh_fighters_and_frozen_settings(self):
  cs,t=await self.enter(20);await host.command(cs[0],{'action':'tournament_start'})
  self.assertEqual(len(host.ROOMS),4) # 12 byes + 4 preliminary duels
  original=t.settings['base_damage'];host.SETTINGS['base_damage']=5
  played=0
  while t.status=='running' or host.ROOMS:
   for r in list(host.ROOMS.values()):
    self.assertEqual(r['settings']['base_damage'],original)
    self.assertTrue(all(p['damage']==0 and p['points']==0 and p['received_hits']==0 for p in r['players']))
    # Fixture deliberately completes results, testing scheduling, not physics.
    r.update(phase='over',winner=0,result_reason='points');played+=1
   await host.schedule_tournaments(time.monotonic())
   await host.schedule_tournaments(time.monotonic()+7)
  self.assertEqual(played,19);self.assertEqual(t.status,'finished')
  self.assertTrue(all(c['room'] is None for c in cs));self.assertIn(t.champion,t.entries)

 async def test_forfeit_keeps_seat_and_no_rematch_or_duel_contamination(self):
  cs,t=await self.enter(2);await host.command(cs[0],{'action':'tournament_start'})
  r=next(iter(host.ROOMS.values()));loser=host.CLIENTS[r['players'][0]['id']];winner=host.CLIENTS[r['players'][1]['id']]
  await host.leave(loser);self.assertEqual(r['winner'],1);self.assertEqual(t.champion,winner['id'])
  loser['ws'].messages.clear();await host.broadcast(r)
  self.assertFalse(loser['ws'].messages);self.assertEqual(winner['ws'].messages[-1]['you'],1)
  await host.command(winner,{'action':'rematch'});self.assertEqual(r['phase'],'over')
  await host.schedule_tournaments(time.monotonic()+7);self.assertIsNone(winner['room'])

 async def test_leaving_result_cannot_reverse_winner(self):
  cs,t=await self.enter(2);await host.command(cs[0],{'action':'tournament_start'})
  r=next(iter(host.ROOMS.values()));r.update(phase='over',winner=0,result_reason='ko')
  winner=r['players'][0]['id'];await host.leave(host.CLIENTS[r['players'][1]['id']])
  self.assertEqual(t.champion,winner);self.assertEqual(t.rounds[0][0]['reason'],'ko')

 async def test_owner_departure_lobby_and_disconnected_bye_wait(self):
  cs,t=await self.enter(3);await host.leave(cs[0]);self.assertEqual(t.owner,cs[1]['id'])
  cs[2]['ws'].closed=True
  with self.assertRaises(ValueError):await host.command(cs[1],{'action':'tournament_start'})
  cs[2]['ws'].closed=False;await host.command(cs[1],{'action':'tournament_start'})
  self.assertEqual(t.status,'running');self.assertEqual(len(host.ROOMS),1)

 async def test_admin_reset_does_not_award_champion(self):
  cs,t=await self.enter(3);await host.command(cs[0],{'action':'tournament_start'})
  host.admin_command('reset');await host.schedule_tournaments(time.monotonic()+7)
  self.assertEqual(t.status,'cancelled');self.assertIsNone(t.champion);self.assertFalse(host.ROOMS)

 async def test_terminal_ko_or_disqualification_is_final_during_replay(self):
  for phase in ('impact','replay','disconnected'):
   for reason in ('ko','disqualification'):
    for departing_seat in (0,1):
     host.ROOMS.clear();host.CLIENTS.clear();host.TOURNAMENTS.clear()
     cs,t=await self.enter(2);await host.command(cs[0],{'action':'tournament_start'})
     r=next(iter(host.ROOMS.values()));r.update(phase=phase,winner=0,result_reason=reason)
     await host.leave(host.CLIENTS[r['players'][departing_seat]['id']])
     self.assertEqual(t.champion,r['players'][0]['id'],(phase,reason,departing_seat))
     self.assertEqual(t.rounds[0][0]['reason'],reason)
     self.assertEqual(r['result_reason'],reason);self.assertEqual(r['phase'],'over')

 async def test_simultaneous_expiry_has_no_fabricated_champion(self):
  cs,t=await self.enter(2);await host.command(cs[0],{'action':'tournament_start'})
  for c in cs:c['ws'].closed=True;c['expires']=time.monotonic()-1
  with patch.object(host,'record'):
   task=asyncio.create_task(host.tick({}))
   try:
    await asyncio.sleep(.15);self.assertFalse(task.done())
   finally:task.cancel();await asyncio.gather(task,return_exceptions=True)
  self.assertEqual(t.status,'cancelled');self.assertIsNone(t.champion)

 async def test_physics_failure_ends_tournament_instead_of_stalling(self):
  cs,t=await self.enter(4);await host.command(cs[0],{'action':'tournament_start'})
  r=next(iter(host.ROOMS.values()));failed=asyncio.get_running_loop().create_future()
  failed.set_exception(RuntimeError('test solver failure'));r.update(phase='resolving',solve=failed,deadline=0)
  with patch.object(host,'record'):
   task=asyncio.create_task(host.tick({}))
   try:
    await asyncio.sleep(.15);self.assertFalse(task.done())
   finally:task.cancel();await asyncio.gather(task,return_exceptions=True)
  self.assertEqual(t.status,'cancelled');self.assertIsNone(t.champion)
  self.assertTrue(all(r['phase']=='over' for r in host.ROOMS.values()))
  self.assertTrue(all(m['status']=='cancelled' for rnd in t.rounds for m in rnd))
  self.assertIn('Technischer Fehler',t.cancel_reason)

 async def test_expiring_other_match_must_not_skip_unaffected_ko_replay(self):
  cs,t=await self.enter(4);await host.command(cs[0],{'action':'tournament_start'})
  r,other=list(host.ROOMS.values());other.update(phase='impact',winner=0,result_reason='ko')
  c=host.CLIENTS[r['players'][0]['id']];c['ws'].closed=True;c['expires']=time.monotonic()-1
  await host.expire_clients(time.monotonic())
  self.assertEqual(other['phase'],'impact');self.assertEqual(other['winner'],0)
  self.assertEqual(r['result_reason'],'forfeit')

 async def test_confirmed_ko_survives_both_expiring(self):
  cs,t=await self.enter(2);await host.command(cs[0],{'action':'tournament_start'})
  r=next(iter(host.ROOMS.values()));r.update(phase='disconnected',winner=1,result_reason='ko')
  for c in cs:c['ws'].closed=True;c['expires']=time.monotonic()-1
  await host.expire_clients(time.monotonic())
  self.assertEqual(t.status,'finished');self.assertEqual(t.champion,r['players'][1]['id'])
  self.assertEqual(r['winner'],1);self.assertEqual(r['result_reason'],'ko')

 async def test_duplicate_start_after_departure_has_clear_notice(self):
  cs,t=await self.enter(3);await host.command(cs[0],{'action':'tournament_start'})
  absent=cs[1];host.CLIENTS.pop(absent['id'])
  with self.assertRaisesRegex(ValueError,'bereits gestartet'):
   await host.command(cs[0],{'action':'tournament_start'})

 async def test_terminal_results_discard_suspended_phase(self):
  for reason in ('ko','forfeit','cancelled'):
   host.ROOMS.clear();host.CLIENTS.clear();host.TOURNAMENTS.clear()
   cs,t=await self.enter(2);await host.command(cs[0],{'action':'tournament_start'})
   r=next(iter(host.ROOMS.values()));r.update(phase='disconnected',suspended=('aim',20),_brace_offset=.2)
   if reason=='cancelled':host.cancel_tournament(t,'test cancellation')
   else:
    if reason=='ko':r.update(winner=0,result_reason='ko')
    await host.leave(host.CLIENTS[r['players'][1]['id']])
   self.assertEqual(r['phase'],'over');self.assertNotIn('suspended',r);self.assertNotIn('_brace_offset',r)

 async def test_busy_parallel_matches_cannot_evict_an_active_replay(self):
  cs,t=await self.enter(4);await host.command(cs[0],{'action':'tournament_start'})
  r,watching=list(host.ROOMS.values());watching.update(phase='replay',deadline=time.monotonic()+30,replay_id='pinned')
  host.REPLAYS['pinned']={'id':'pinned'}
  for i in range(31):host.REPLAYS[str(i)]={'id':str(i)}
  solved=asyncio.get_running_loop().create_future();solved.set_result(dict(frames=[[0.,0.]],fps=120,duration=2.8,solve_ms=0))
  r.update(phase='resolving',solve=solved,deadline=0,brace=None,pending=dict(hit=False,quality=0.,side='L',contact_class='miss',diagnosis='test miss'))
  with patch.object(host,'record'):
   task=asyncio.create_task(host.tick({}))
   try:
    await asyncio.sleep(.15);self.assertFalse(task.done())
   finally:task.cancel();await asyncio.gather(task,return_exceptions=True)
  self.assertEqual(r['hits'],1)
  self.assertIn('pinned',host.REPLAYS)
  self.assertEqual(len(host.REPLAYS),32)


if __name__=='__main__':unittest.main()
