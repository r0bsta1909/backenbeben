"""Create a lightweight design preview from the production tournament UI."""
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
source=(ROOT/'game/web_shell.html').read_text(encoding='utf-8')
base=re.search(r'<style>(.*?)</style>',source,re.S).group(1)
header=re.search(r'<header>.*?</header>',source,re.S).group(0)
panel='<section id="tournamentPanel"'+source.split('<section id="tournamentPanel"',1)[1].split('<div class="tools">',1)[0]
template='''<!doctype html><html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Backenbeben / UI-Entwurf</title><link rel="icon" href="data:,"><style>BASE
body:before{content:'';position:fixed;inset:0;background:linear-gradient(#0b101b66,#0b101bbb),url('../../game/assets/arena_backdrops/hall-front.png') center/cover;pointer-events:none}.previewControls{position:fixed;left:3.5%;right:3.5%;top:86px;display:flex;gap:6px;align-items:center;z-index:6}.previewControls>span{font-size:9px;letter-spacing:1.6px;color:#c7b278;margin-right:auto}.previewControls button,.previewControls select{padding:6px 9px;font-size:9px;width:auto}.previewControls [aria-pressed=true]{color:#e8c36b;border-color:#e8c36b}.previewHint{position:fixed;bottom:5px;left:4%;font-size:8px;letter-spacing:1px;color:#b9b09f;z-index:7}#toast{bottom:40px}#previewMount{display:none}@media(max-width:750px){.previewControls{top:82px;left:12px;right:12px;gap:4px}.previewControls>span{font-size:7px;letter-spacing:0;max-width:65px}.previewControls button,.previewControls select{padding:6px;font-size:8px}.version{display:none}.previewControls{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:3px}.previewControls>span{grid-column:1/-1;max-width:none;font-size:7px}.previewControls button,.previewControls select{width:100%;min-width:0;padding:5px 3px;font-size:7px}#tournamentPanel{top:126px}}
</style><link rel="stylesheet" href="../../game/tournament.css"></head><body>HEADER
<div class="previewControls"><span>UI-ENTWURF / BEISPIELDATEN</span><button data-preview="waiting" aria-pressed="true">LOBBY</button><button data-preview="running" aria-pressed="false">TURNIERBAUM</button><button data-preview="finished" aria-pressed="false">CHAMPION</button><button data-preview="cancelled" aria-pressed="false">ABBRUCH</button><select id="previewCount" aria-label="Teilnehmerzahl"><option value="8">8 SPIELER</option><option value="20">20 SPIELER</option></select></div>
PANEL<div id="toast" class="toast"></div><p class="previewHint">GESTALTUNGSVORSCHAU · KEIN LAUFENDES MATCH</p>
<div id="previewMount"><button id="tournamentCreate"></button><button id="tournamentJoin"></button><input id="tournamentJoinCode"></div>
<script>const $=id=>document.getElementById(id);const socket={readyState:1};window.gameReady=true;window.unlockGameAudio=()=>{};window.characterPayload=()=>({});function showLobby(){document.body.classList.remove('playing');}function toast(t){$('toast').textContent=t;$('toast').style.opacity=1;setTimeout(()=>$('toast').style.opacity=0,2200);}window.sendAction=d=>toast(d.action==='tournament_start'?'Im Spiel startet hier das Turnier.':'Im Spiel kehrst du hier zur Lobby zurück.');</script>
<script src="../../game/tournament.js"></script><script src="tournament-preview.js"></script></body></html>'''
out=ROOT/'docs/ui-preview';out.mkdir(exist_ok=True)
(out/'tournament.html').write_text(template.replace('BASE',base).replace('HEADER',header).replace('PANEL',panel),encoding='utf-8')
print(out/'tournament.html')
