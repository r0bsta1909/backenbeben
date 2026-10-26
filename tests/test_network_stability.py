import asyncio
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'server'))
import host
import lan_play
from tournament import Tournament
from replay_timing import extend_inspection


class Socket:
    closed=False
    def __init__(self):self.messages=[]
    async def send_json(self,data):self.messages.append(data)


class StabilityTests(unittest.IsolatedAsyncioTestCase):
    async def test_one_stalled_peer_does_not_delay_others_and_is_closed(self):
        fast=Socket();blocked=Socket();closed=[]
        async def stall(data):await asyncio.Event().wait()
        blocked.send_json=stall
        class Transport:
            def close(self):closed.append(True)
        clients={'a':dict(ws=blocked,transport=Transport()),'b':dict(ws=fast)}
        with patch.object(host,'CLIENTS',clients),patch.object(host,'SEND_TIMEOUT',.08):
            task=asyncio.create_task(host.broadcast_lobby({'type':'lan_lobby'}))
            await asyncio.sleep(.02)
            self.assertEqual(len(fast.messages),1);self.assertFalse(task.done())
            await asyncio.wait_for(task,.5);self.assertEqual(closed,[True])

    async def test_expiry_claims_all_ids_before_yielding_and_never_pops_a_replacement(self):
        clients={str(i):dict(id=str(i),expires=1,ws=Socket()) for i in range(2)}
        entered=asyncio.Event();release=asyncio.Event()
        async def leave(c,prune=True):entered.set();await release.wait()
        with patch.object(host,'CLIENTS',clients),patch.object(host,'TOURNAMENTS',{}),patch.object(host,'leave',leave):
            task=asyncio.create_task(host.expire_clients(2));await entered.wait()
            self.assertEqual(clients,{})
            replacement=dict(id='0',ws=Socket());clients['0']=replacement
            release.set();await task;self.assertIs(clients['0'],replacement)

    async def test_simultaneous_expiry_does_not_leave_orphan_tournament_rooms(self):
        for n in range(2,21):
            clients={str(i):dict(id=str(i),name='PLAYER',ws=Socket(),room=None,skin=0,hair=0,shirt=0,tournament='ABC123',expires=1) for i in range(n)}
            t=Tournament('ABC123','0','PLAYER')
            for uid in list(clients)[1:]:t.add(uid,'PLAYER')
            t.start('0');t.settings=dict(host.SETTINGS);t.revision=1
            with patch.object(host,'CLIENTS',clients),patch.object(host,'ROOMS',{}),patch.object(host,'TOURNAMENTS',{'ABC123':t}):
                await host.schedule_tournaments(1)
                self.assertTrue(host.ROOMS)
                await host.expire_clients(2)
                self.assertFalse(host.CLIENTS);self.assertFalse(host.TOURNAMENTS)
                self.assertTrue(all(r['phase']=='over' for r in host.ROOMS.values()))
                await host.schedule_tournaments(__import__('time').monotonic()+7)
                self.assertFalse(host.ROOMS)

    async def test_ping_is_answered_even_without_a_room(self):
        c=dict(ws=Socket());await host.command(c,{'action':'ping'})
        self.assertEqual(c['ws'].messages,[{'type':'pong'}])

    def test_replay_pause_preserves_inspection_budget_and_brace_offset(self):
        room=dict(suspended=('replay',8),_replay_remaining=33,brace=90,_brace_offset=.4)
        host.resume_room(room,500)
        self.assertEqual(room['deadline'],508);self.assertEqual(room['replay_limit'],533)
        self.assertAlmostEqual(room['brace'],507.6)
        room['replay_id']='clip';self.assertTrue(extend_inspection(room,'clip',505))
        self.assertEqual(room['deadline'],517)


class HostVerificationTests(unittest.TestCase):
    def test_health_verification_rejects_dead_wrong_and_redirecting_hosts(self):
        hosts=[dict(address=f'192.168.1.{i}',port=8765,host_id='same' if i<3 else '') for i in range(1,6)]
        class Connection:
            def __init__(self,address,port,timeout):self.number=int(address.rsplit('.',1)[1])
            def request(self,*args):
                if self.number==3:raise OSError('TCP blocked')
            def getresponse(self):
                n=self.number
                class Response:
                    status=302 if n==4 else 200
                    def read(self,limit):return json.dumps(dict(ok=True,game='other' if n==5 else 'backenbeben')).encode()
                return Response()
            def close(self):pass
        with patch.object(lan_play,'HTTPConnection',Connection):
            verified=lan_play.reachable_hosts(hosts)
        self.assertEqual([h['address'] for h in verified],['192.168.1.1'])


if __name__=='__main__':unittest.main()
