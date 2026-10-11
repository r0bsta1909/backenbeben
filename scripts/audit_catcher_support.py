"""Check both helper palms against the real recorded KO support track."""
import json, subprocess, sys
from pathlib import Path
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'server'))
from body import collapse_track
(root/'logs').mkdir(exist_ok=True)
(root/'logs/catcher-body-track.json').write_text(json.dumps(collapse_track(True)))
godot=root/'tools/godot/Godot_v4.7.2-stable_win64_console.exe'
subprocess.run([str(godot),'--headless','--path',str(root/'game'),'--script',str(root/'tests/catcher_support.gd')],cwd=root,check=True)
