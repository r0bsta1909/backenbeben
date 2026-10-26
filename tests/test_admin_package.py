import asyncio
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'server'),str(ROOT/'scripts')]
import host
from package_release import build_package,WEB_REQUIRED,SOURCE_REQUIRED


class AdminTests(unittest.IsolatedAsyncioTestCase):
    async def test_non_object_admin_body_is_a_bad_request(self):
        class Request:
            remote='127.0.0.1';host='localhost:8765';headers={'Origin':'http://localhost:8765'}
            async def json(self):return []
        response=await host.admin(Request())
        self.assertEqual(response.status,400)

    def test_invalid_presets_are_rejected_atomically(self):
        for data in ([],None,{'max_pairs':3.5},{'recovery':False},{'base_damage':30,'bad':2}, {'recovery':float('nan')}):
            with self.subTest(data=data),tempfile.TemporaryDirectory() as folder:
                root=Path(folder);(root/'server').mkdir();(root/'server/balance.json').write_text(json.dumps(data),encoding='utf-8')
                before=dict(host.SETTINGS);revision=host.REVISION
                with patch.object(host,'ROOT',root):
                    with self.assertRaises(ValueError):host.admin_command('load')
                self.assertEqual(host.SETTINGS,before);self.assertEqual(host.REVISION,revision)


class PackageTests(unittest.TestCase):
    def fixture(self,root):
        for name in [*('build/web/'+name for name in WEB_REQUIRED),*SOURCE_REQUIRED]:
            p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b'fixture')

    def test_missing_frontend_or_collision_asset_stops_packaging(self):
        for name in ('build/web/lan_lobby.js','game/assets/face_v3_collision.json','LAN_SPIELEN.bat'):
            with self.subTest(name=name),tempfile.TemporaryDirectory() as folder:
                root=Path(folder);self.fixture(root);(root/name).unlink()
                with self.assertRaisesRegex(ValueError,'missing'):build_package(root,'test')
                self.assertFalse((root/'dist').exists())

    def test_complete_package_excludes_local_runtime_and_configuration(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);self.fixture(root)
            (root/'server/balance.json').write_text('{}')
            (root/'server/.env').write_text('secret')
            archive=build_package(root,'test')
            with zipfile.ZipFile(archive) as z:
                self.assertIsNone(z.testzip());self.assertIn('LAN_SPIELEN.bat',z.namelist())
                self.assertNotIn('server/balance.json',z.namelist());self.assertNotIn('server/.env',z.namelist())
            for version in ('','../escape','x/y','x\\y'):
                with self.assertRaises(ValueError):build_package(root,version)


if __name__=='__main__':unittest.main()
