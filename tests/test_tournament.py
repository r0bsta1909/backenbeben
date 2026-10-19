import asyncio,copy,json,sys,time,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'server'))
from tournament import Tournament,decision
import host


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
  host.ROOMS.clear();host.CLIENTS.clear();host.TOURNAMENTS.clear()
  self.settings=dict(host.SETTINGS)

 async def asyncTearDown(self):
  host.SETTINGS.clear();host.SETTINGS.update(self.settings)
  host.ROOMS.clear();host.CLIENTS.clear();host.TOURNAMENTS.clear()

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


if __name__=='__main__':unittest.main()
