import sys,unittest,asyncio
from pathlib import Path
from unittest.mock import patch,Mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'server'))
import host
class BraceDispatchTests(unittest.IsolatedAsyncioTestCase):
 async def test_correct_brace_replaces_waited_result_immediately(self):
  old=asyncio.get_running_loop().create_future();new=asyncio.get_running_loop().create_future()
  room={'brace_result':'ready','pending':{'stroke':'actual'},'solve':old}
  loop=Mock();loop.run_in_executor.return_value=new
  with patch.object(host,'PHYSICS_BACKEND','coupled-moving'),patch.object(host.asyncio,'get_running_loop',return_value=loop):
   self.assertTrue(host.start_braced_solve(room))
  loop.run_in_executor.assert_called_once_with(host.POOL,host.simulate,room['pending'],True)
  self.assertIs(room['solve'],new);self.assertTrue(old.cancelled())
 async def test_early_brace_or_other_backend_does_not_replace_result(self):
  for backend,result in [('coupled-moving','early'),('coupled','ready'),('legacy','ready')]:
   old=asyncio.get_running_loop().create_future();room={'brace_result':result,'solve':old}
   with patch.object(host,'PHYSICS_BACKEND',backend):self.assertFalse(host.start_braced_solve(room))
   self.assertIs(room['solve'],old);self.assertFalse(old.cancelled());old.cancel()
