// Live LAN roster from the shared authoritative host. Native launcher finds hosts.
(() => {
    const panel = document.createElement('dialog');
    panel.id = 'lanPanel';
    panel.setAttribute('aria-labelledby', 'lanTitle');
    panel.innerHTML = `<div class="lanHeading"><div><span class="tag">ZUSAMMEN AN DEN TISCH.</span><h2 id="lanTitle">LAN <em>SPIELEN.</em></h2></div><button id="lanClose" aria-label="LAN-Lobby schließen">✕</button></div>
        <p id="lanNotice" role="alert" hidden></p><p id="lanStatus" role="status">Spieler werden automatisch gesucht …</p>
        <div class="lanColumns"><section><h3>SPIELER AM HOST <span id="lanCount">0</span></h3><ul id="lanPlayers"></ul></section>
        <section><h3>OFFENE TURNIERE</h3><div id="lanTournaments"></div></section></div>
        <div class="lanActions"><button id="lanQuickDuel" class="primary">DUELL SUCHEN →</button><button id="lanCreate">TURNIER ERSTELLEN</button></div>
        <p class="tiny">Automatisch aktualisiert. Für ein Duell wählen beide Spieler „Duell suchen“.<br>Auf einem weiteren PC: LAN_SPIELEN.bat starten oder den LAN-Link unten öffnen.</p>
        <input id="lanLink" aria-label="LAN-Link zum Teilen" readonly><p class="tiny">Hostfenster geöffnet lassen. Maximal 20 Spieler pro Turnier.</p>`;
    document.body.append(panel);
    let snapshot = {players: [], tournaments: []}, connected = socket?.readyState === 1, timer;
    const labels = {available: 'BEREIT', waiting: 'SUCHT DUELL', playing: 'IM SPIEL', tournament: 'IM TURNIER'};
    const element = (tag, text, className) => {
        const node = document.createElement(tag); node.textContent = text;
        if (className) node.className = className;
        return node;
    };
    function render() {
        $('lanStatus').textContent = connected ? '● LIVE · Spieler und Turniere dieses Hosts' : 'Verbindung unterbrochen — Suche wird nach Wiederverbindung fortgesetzt.';
        $('lanCount').textContent = connected ? snapshot.players.length : '–';
        $('lanPlayers').replaceChildren(); $('lanTournaments').replaceChildren();
        for (const player of connected ? snapshot.players : []) {
            const item = element('li', '', player.id === connectionId ? 'lanSelf' : '');
            item.append(element('strong', player.name + (player.id === connectionId ? ' · DU' : '')), element('small', labels[player.status] || 'BEREIT'));
            $('lanPlayers').append(item);
        }
        for (const t of connected ? snapshot.tournaments : []) {
            const card = element('div', '', 'lanTournament');
            const info = element('div', ''); info.append(element('strong', 'Turnier von ' + t.name), element('small', `${t.count} / ${t.capacity} SPIELER`));
            const button = element('button', 'BEITRETEN →');
            button.disabled = !window.gameReady;
            button.onclick = () => { window.unlockGameAudio(); sendAction({...characterPayload(), action: 'tournament_join', code: t.id}); };
            card.append(info, button); $('lanTournaments').append(card);
        }
        if (!connected || !snapshot.players.length) $('lanPlayers').append(element('li', connected ? 'Noch keine Spieler angemeldet.' : 'Warte auf den Host …', 'lanEmpty'));
        if (!connected || !snapshot.tournaments.length) $('lanTournaments').append(element('p', connected ? 'Noch kein offenes Turnier. Erstelle das erste.' : 'Warte auf den Host …', 'lanEmpty'));
        $('lanQuickDuel').disabled = $('lanCreate').disabled = !connected || !window.gameReady;
    }
    window.announceLan = () => { if (socket?.readyState === 1) sendAction({...characterPayload(), action: 'presence'}); };
    window.lanNotice = text => { if (panel.open) { $('lanNotice').hidden = false; $('lanNotice').textContent = text; } };
    window.onLanLobby = d => { snapshot = d; render(); };
    window.lanConnection = value => { connected = value; render(); if (value) window.announceLan(); };
    window.addEventListener('character-changed', () => { clearTimeout(timer); timer = setTimeout(window.announceLan, 250); });
    $('lanOpen').onclick = () => { $('lanNotice').hidden = true; render(); panel.showModal(); window.announceLan(); };
    $('lanClose').onclick = () => panel.close();
    $('lanQuickDuel').onclick = () => { panel.close(); join('duel'); };
    $('lanCreate').onclick = () => { window.unlockGameAudio(); sendAction({...characterPayload(), action: 'tournament_create'}); };
    // A server-confirmed transition closes the dialog; rejected joins stay reviewable.
    new MutationObserver(() => {
        if (document.body.matches('.playing, .tournament') && panel.open) panel.close();
    }).observe(document.body, {attributes: true, attributeFilter: ['class']});
    $('lanLink').onclick = () => $('lanLink').select();
    fetch('/api/info').then(r => r.json()).then(d => {
        $('lanLink').value = `http://${d.addresses[0] || location.hostname}:${d.port}`;
    }).catch(() => { $('lanLink').value = location.origin; });
    render(); window.announceLan();
})();
