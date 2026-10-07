// Plain LAN HTTP has no AudioWorklet. Keep sound using buffer playback instead.
window.audioFallback = !window.isSecureContext || !Engine.isAudioWorkletAvailable();
window.audioDiagnostics = {mode: window.audioFallback ? 'buffer-fallback' : 'godot', played: 0, unlocked: false};
let fallbackContext;
let fallbackBuffers;
const soundBytes = window.audioFallback ? Promise.all(['slap', 'bell'].map(async name => {
    const response = await fetch(name + '.wav');
    if (!response.ok) throw new Error('Sound konnte nicht geladen werden: ' + name);
    return [name, await response.arrayBuffer()];
})).catch(error => { window.audioDiagnostics.error = error.message; return []; }) : null;
window.unlockGameAudio = function () {
    if (!window.audioFallback) return;
    const Context = window.AudioContext || window.webkitAudioContext;
    if (!Context) return;
    if (!fallbackContext) {
        fallbackContext = new Context();
        fallbackBuffers = soundBytes.then(entries => Promise.all(entries.map(async ([name, bytes]) => [name, await fallbackContext.decodeAudioData(bytes)]))).then(Object.fromEntries);
    }
    fallbackContext.resume().then(() => { window.audioDiagnostics.unlocked = fallbackContext.state === 'running'; });
};
// A resumed tab may enter a replay directly, without pressing Join again.
document.addEventListener('pointerdown',window.unlockGameAudio,{passive:true});
document.addEventListener('keydown',window.unlockGameAudio);
window.playGameSound = function (name) {
    if (!fallbackContext || window.muted) return;
    fallbackBuffers.then(buffers => {
        if (!buffers[name] || window.muted) return;
        const source = fallbackContext.createBufferSource();
        const gain = fallbackContext.createGain();
        source.buffer = buffers[name];
        gain.gain.value = name === 'slap' ? .45 : .25;
        source.connect(gain).connect(fallbackContext.destination);
        source.start();
        source.onended = () => { source.disconnect(); gain.disconnect(); };
        window.audioDiagnostics.played++;
    }).catch(error => { window.audioDiagnostics.error = error.message; });
};

// Interpolate between authoritative snapshots so the timing cue moves smoothly.
function defenseFrame() {
    const panel = document.getElementById('bracePanel');
    const snap = window.braceSnapshot;
    if (!panel) { requestAnimationFrame(defenseFrame); return; }
    if (!snap || !document.body.classList.contains('playing')) {
        panel.hidden = true;
        requestAnimationFrame(defenseFrame); return;
    }
    const s = snap.state, defending = s.players.length > 1 && s.turn !== snap.you;
    panel.hidden = !defending || ['waiting', 'over', 'disconnected', 'replay', 'impact', 'resolving'].includes(s.phase);
    const remaining = Math.max(0, s.remaining - (performance.now()-snap.at)/1000);
    const total = s.windup_seconds || 1.4;
    const windowSeconds = s.brace_window_ms / 1000;
    const winding = defending && s.phase === 'windup';
    const ready = winding && !s.brace_used && remaining > 0 && remaining <= windowSeconds;
    const button = document.getElementById('braceButton');
    let title = 'DU BIST AM SCHLAG', hint = 'Anspannen brauchst du beim gegnerischen Schlag.', mode = 'locked';
    if (defending && s.phase === 'aim') { title = 'NOCH NICHT ANSPANNEN'; hint = 'Warte, bis der Gegner ausholt. Dann läuft die Leiste.'; }
    if (winding) {
        if (s.brace_used) {
            title = s.brace_result === 'ready' ? 'RICHTIG ANGESPANNT ✓' : 'ZU FRÜH – VERBRAUCHT';
            hint = s.brace_result === 'ready' ? 'Der Schlag wird abgeschwächt.' : 'Nächster Versuch beim nächsten Schlag. Auf GRÜN warten.';
            mode = s.brace_result === 'ready' ? 'success' : 'spent';
        } else if (ready) { title = 'JETZT ANSPANNEN!'; hint = 'RECHTSKLICK oder LEERTASTE · einmal drücken'; mode = 'ready'; }
        else if (remaining === 0) { title = 'FENSTER VORBEI'; hint = 'Der Treffer wird ausgewertet.'; mode = 'spent'; }
        else { title = 'WARTEN …'; hint = 'Grün in '+Math.max(0, remaining-windowSeconds).toFixed(1)+' s · noch nicht drücken'; mode = 'waiting'; }
        document.getElementById('phaseTitle').textContent = title;
        document.getElementById('phaseHint').textContent = hint;
    }
    if (s.phase === 'recover') {
        title = 'ANSPANNEN BEENDET'; hint = defending ? 'Jetzt kannst du mit 1–3 reagieren.' : 'Der Gegner ist als Nächstes dran.';
    }
    panel.dataset.mode = mode;
    document.getElementById('braceTitle').textContent = title;
    document.getElementById('braceHint').textContent = hint;
    document.getElementById('braceZone').style.width = Math.min(100, windowSeconds/total*100)+'%';
    document.getElementById('braceCursor').style.left = (winding ? Math.min(100, (1-remaining/total)*100) : 0)+'%';
    button.disabled = !ready;
    button.textContent = ready ? 'JETZT ANSPANNEN' : s.brace_used && winding ? 'VERSUCH VERBRAUCHT' : 'AUF GRÜN WARTEN';
    requestAnimationFrame(defenseFrame);
}
requestAnimationFrame(defenseFrame);
