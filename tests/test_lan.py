import asyncio
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'server'))
import host
import lan_play
from lan_discovery import DiscoveryProtocol, PROTOCOL, local_address
from tournament import Tournament


class Transport:
    def __init__(self): self.packets = []
    def sendto(self, data, addr): self.packets.append((json.loads(data), addr))


class DiscoveryTests(unittest.TestCase):
    def test_launcher_joins_single_host_without_starting_another(self):
        with patch.object(lan_play,'reachable_hosts',side_effect=lambda hosts:hosts), patch.object(lan_play,'broadcast_targets',return_value=['127.0.0.1']), patch.object(lan_play,'discover',return_value=[dict(name='HOST',url='http://192.168.1.5:8765')]), patch.object(lan_play.webbrowser,'open') as opened, patch('builtins.input') as ask:
            lan_play.main()
            opened.assert_called_once_with('http://192.168.1.5:8765');ask.assert_not_called()

    def test_launcher_does_not_create_a_host_without_user_intent(self):
        with patch.object(lan_play,'reachable_hosts',side_effect=lambda hosts:hosts), patch.object(lan_play,'broadcast_targets',return_value=[]), patch.object(lan_play,'discover',return_value=[]), patch.object(host,'main') as start, patch('builtins.input',return_value='q'):
            lan_play.main();start.assert_not_called()

    def test_launcher_selects_between_multiple_hosts(self):
        hosts=[dict(name='A',url='http://192.168.1.5:8765'),dict(name='B',url='http://192.168.1.6:8765')]
        with patch.object(lan_play,'reachable_hosts',side_effect=lambda hosts:hosts), patch.object(lan_play,'broadcast_targets',return_value=[]), patch.object(lan_play,'discover',return_value=hosts), patch.object(lan_play.webbrowser,'open') as opened, patch('builtins.input',return_value='2'):
            lan_play.main();opened.assert_called_once_with(hosts[1]['url'])

    def test_scoped_versioned_request_reply(self):
        p = DiscoveryProtocol(8922, lambda: dict(players=2)); t = Transport(); p.connection_made(t)
        packet = dict(protocol=PROTOCOL,type='discover',nonce='a'*32)
        p.datagram_received(json.dumps(packet).encode(), ('192.168.1.20', 40000))
        self.assertEqual(t.packets[0][0]['port'], 8922)
        self.assertEqual(t.packets[0][0]['nonce'], 'a'*32)
        self.assertNotIn('url', t.packets[0][0])
        p.datagram_received(json.dumps(packet).encode(), ('192.168.1.20', 40000))
        self.assertEqual(len(t.packets), 1)  # bounded per-IP replies

    def test_bad_and_public_requests_are_ignored(self):
        for packet in (b'null', b'[]', b'broken', b'\xff', b'x'*257,
                       json.dumps(dict(protocol=PROTOCOL,type='discover',nonce=[])).encode(),
                       json.dumps(dict(protocol='other',type='discover',nonce='a'*32)).encode()):
            p = DiscoveryProtocol(8922, dict); t = Transport(); p.connection_made(t)
            p.datagram_received(packet, ('192.168.1.2', 40000)); self.assertEqual(t.packets, [])
        p.datagram_received(json.dumps(dict(protocol=PROTOCOL,type='discover',nonce='a'*32)).encode(), ('8.8.8.8',40000))
        self.assertEqual(t.packets, [])
        self.assertFalse(local_address('::1')); self.assertFalse(local_address('224.0.0.1'))
        self.assertTrue(local_address('127.0.0.1')); self.assertTrue(local_address('10.1.2.3'))


class LobbyTests(unittest.IsolatedAsyncioTestCase):
    async def test_presence_and_public_snapshot_never_expose_resume_tokens(self):
        class WS:
            closed = False
            async def send_json(self, data): pass
        clients = {str(i):dict(id=str(i),name='PLAYER',resume_token='PRIVATE',ws=WS(),room=None) for i in range(3)}
        with patch.object(host,'CLIENTS',clients), patch.object(host,'ROOMS',{}), patch.object(host,'TOURNAMENTS',{}):
            await host.command(clients['0'], dict(action='presence',character_version=14,name='  SVEN  ',skin=999))
            self.assertEqual(clients['0']['name'],'SVEN'); self.assertEqual(clients['0']['skin'],6)
            data=host.lobby_snapshot(); self.assertEqual(len(data['players']),1)
            self.assertNotIn('PRIVATE', json.dumps(data)); self.assertNotIn('resume',json.dumps(data))
            await host.command(clients['0'],dict(action='tournament_create',character_version=14,name='SVEN'))
            code=clients['0']['tournament']; self.assertEqual(host.lobby_snapshot()['tournaments'][0]['id'],code)
            await host.command(clients['0'],dict(action='presence',character_version=14,name='CHANGED'))
            self.assertEqual(clients['0']['name'],'SVEN') # don't change active event identity
            t=host.TOURNAMENTS[code]
            for i in range(1,20):t.add(str(i),'PLAYER')
            self.assertEqual(host.lobby_snapshot()['tournaments'],[])
            t.status='running';self.assertEqual(host.lobby_snapshot()['tournaments'],[])
            clients['0']['ws'].closed=True;self.assertEqual(host.lobby_snapshot()['players'],[])


if __name__ == '__main__': unittest.main()
