"""Exercise setup interpreter selection without installing dependencies."""
from pathlib import Path
import subprocess,tempfile,shutil,json
root=Path(__file__).resolve().parents[1]
target=Path(tempfile.mkdtemp(prefix='backenbeben-setup-check-'))
(target/'scripts').mkdir();shutil.copyfile(root/'scripts/setup-host.ps1',target/'scripts/setup-host.ps1')
def run(*args):
 return subprocess.run(['powershell','-NoProfile','-ExecutionPolicy','Bypass','-File',str(target/'scripts/setup-host.ps1'),'-CheckOnly',*args],capture_output=True,text=True)
valid=run('-PythonPath',str(root/'tools/python/cpython-3.12-windows-x86_64-none/python.exe'))
assert valid.returncode==0,valid.stderr
invalid=run('-PythonPath',str(target/'missing.exe'))
assert invalid.returncode!=0 and 'PythonPath' in invalid.stderr,invalid
assert not (target/'.venv').exists(), 'CheckOnly modified installation'
# An invalid existing environment must not be silently replaced.
(target/'.venv/Scripts').mkdir(parents=True)
(target/'.venv/Scripts/python.exe').write_bytes(b'invalid executable')
existing=run()
assert existing.returncode!=0 and 'umbenennen' in existing.stderr,existing.stderr
assert (target/'.venv/Scripts/python.exe').read_bytes()==b'invalid executable'
report={'explicit_python_312':True,'missing_explicit_python_rejected':True,'check_only_does_not_create_environment':True,'invalid_existing_environment_preserved':True}
(root/'logs/setup-selection.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
