"""Build a complete public host ZIP from an explicit allowlist."""
from pathlib import Path
import argparse
import zipfile

WEB_REQUIRED = ('index.html','index.js','index.wasm','index.pck','combat.js',
                'browser_support.js','character_creator.js','character_creator.css',
                'tournament.js','tournament.css','lan_lobby.js','lan_lobby.css',
                'slap.wav','bell.wav')
SOURCE_REQUIRED = ('game/assets/face_surface.json','game/assets/character_v3.json',
    'game/assets/face_v3_collision.json','game/assets/hand_contact_surface_v3.json',
    'START_HOST.bat','LAN_SPIELEN.bat','SETUP_HOST.bat','ALLOW_LAN.bat',
    'scripts/setup-host.ps1','scripts/allow_lan.ps1','SPIELEN.txt','README.md',
    'server/host.py','server/lan_play.py','server/lan_discovery.py',
    'server/requirements.txt','server/requirements-lab.txt')


def build_package(root,version):
    root=Path(root)
    if not version or not all(c.isascii() and (c.isalnum() or c in '.-') for c in version):
        raise ValueError('Invalid version')
    required=[*(root/'build/web'/name for name in WEB_REQUIRED),*(root/name for name in SOURCE_REQUIRED)]
    missing=[str(p.relative_to(root)) for p in required if not p.is_file()]
    if missing:raise ValueError('Package files missing: '+', '.join(missing))
    files=[*required,*root.glob('build/web/*'),*root.glob('server/*.py'),*root.glob('third-party/*.txt')]
    out=root/'dist'/f'backenbeben-{version}-host.zip'
    out.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as archive:
        for p in sorted(set(files)):
            if p.is_file():archive.write(p,p.relative_to(root))
    with zipfile.ZipFile(out) as archive:
        if archive.testzip() is not None:raise ValueError('Package integrity failed')
    return out


def main():
    parser=argparse.ArgumentParser();parser.add_argument('version');args=parser.parse_args()
    try:print(build_package(Path(__file__).resolve().parents[1],args.version))
    except ValueError as exc:raise SystemExit(str(exc)) from exc


if __name__=='__main__':main()
