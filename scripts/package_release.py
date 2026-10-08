"""Build a public host ZIP from an explicit allowlist, without local runtimes."""
from pathlib import Path
import argparse,zipfile

root=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser();parser.add_argument('version');args=parser.parse_args()
if not all(c.isalnum() or c in '.-' for c in args.version):raise SystemExit('Invalid version')
out=root/'dist'/f'backenbeben-{args.version}-host.zip';out.parent.mkdir(exist_ok=True)
files=[*root.glob('build/web/*'),*root.glob('server/*.py'),root/'server/requirements.txt',root/'server/requirements-lab.txt',*root.glob('third-party/*.txt')]
files += [root/p for p in ['game/assets/face_surface.json','game/assets/character_v3.json','game/assets/face_v3_collision.json','game/assets/hand_contact_surface_v3.json','START_HOST.bat','SETUP_HOST.bat','ALLOW_LAN.bat','scripts/setup-host.ps1','scripts/allow_lan.ps1','SPIELEN.txt','README.md']]
for required in ['index.html','index.js','index.wasm','index.pck','combat.js','browser_support.js']:
    if not (root/'build/web'/required).is_file():raise SystemExit('Build missing: '+required)
with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as archive:
    for p in sorted(set(files)):
        if p.is_file():archive.write(p,p.relative_to(root))
with zipfile.ZipFile(out) as archive:
    assert archive.testzip() is None
print(out)
