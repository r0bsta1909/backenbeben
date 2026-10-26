// Cosmetic choices share the live character model used by the match and replay.
(() => {
    const fields = ['skin', 'hair', 'shirt', 'hair_style', 'face_style', 'beard_style', 'beard_color'];
    const limits = {skin: 6, hair: 2, shirt: 3, hair_style: 5, face_style: 5, beard_style: 5, beard_color: 2};
    const defaults = {name: 'CHALLENGER', skin: 0, hair: 0, shirt: 0, hair_style: 0, face_style: 0, beard_style: 1, beard_color: 0};
    const palette = {skin: ['#b48968','#8c654e','#634737','#d2aa8c','#f0d7c4','#38271f','#dec19a'], hair: ['#241b16','#6b3624','#b8afa0'], shirt: ['#6e242b','#26354b','#deb64c','#534979'], beard_color: ['#241b16','#6b3624','#b8afa0']};
    const storageKey = 'backenbeben-character-v1';
    let view = 'body', yaw = 0, persisted = true;
    const get = id => document.getElementById(id);
    function sanitize(raw) {
        const data = {...defaults};
        if (!raw || typeof raw !== 'object') return data;
        data.name = typeof raw.name === 'string' ? raw.name.slice(0,18) : defaults.name;
        for (const field of fields) data[field] = Number.isInteger(raw[field]) && raw[field] >= 0 && raw[field] <= limits[field] ? raw[field] : defaults[field];
        return data;
    }
    function read() {
        return {name: get('nickname').value, ...Object.fromEntries(fields.map(field => [field, +get(field).value]))};
    }
    function update(save = true) {
        const data = read();
        if (save) window.dispatchEvent(new Event('character-changed'));
        window.previewFighter = {...data, view, yaw};
        get('characterName').textContent = data.name.trim() || 'CHALLENGER';
        get('characterSummary').textContent = `${get('face_style').selectedOptions[0].text} · ${get('hair_style').selectedOptions[0].text} · ${get('beard_style').selectedOptions[0].text}`;
        document.querySelectorAll('[data-character-field]').forEach(button => {
            button.setAttribute('aria-pressed', String(data[button.dataset.characterField] === +button.dataset.value));
        });
        if (save) {
            try { localStorage.setItem(storageKey, JSON.stringify(data)); persisted = true; }
            catch { persisted = false; }
        }
        get('characterSaved').textContent = persisted ? 'Auswahl wird auf diesem Gerät gespeichert.' : 'Auswahl gilt für diese Sitzung.';
    }
    function apply(raw) {
        const data = sanitize(raw);
        get('nickname').value = data.name;
        for (const field of fields) get(field).value = String(data[field]);
        update();
    }
    for (const field of fields) {
        get(field).addEventListener('change', () => update());
        if (!palette[field]) continue;
        const group = document.createElement('div');
        group.className = 'characterSwatches';
        group.setAttribute('role', 'group');
        group.setAttribute('aria-label', get(field).labels[0].textContent);
        palette[field].forEach((color, index) => {
            const button = document.createElement('button');
            button.type = 'button'; button.style.setProperty('--swatch', color);
            button.dataset.characterField = field; button.dataset.value = index;
            button.setAttribute('aria-label', get(field).options[index].text);
            button.title = get(field).options[index].text;
            button.addEventListener('click', () => { get(field).value = String(index); update(); });
            group.appendChild(button);
        });
        get(field).after(group);
    }
    get('nickname').addEventListener('input', () => update());
    get('characterRandom').onclick = () => apply({...read(), ...Object.fromEntries(fields.map(field => [field, Math.floor(Math.random() * (limits[field] + 1))]))});
    get('characterReset').onclick = () => { view = 'body'; yaw = 0; setView(view); apply(defaults); };
    function setView(value) {
        view = value;
        for (const mode of ['body','face']) get('characterView' + mode).setAttribute('aria-pressed', String(mode === view));
        update(false);
    }
    get('characterViewbody').onclick = () => setView('body');
    get('characterViewface').onclick = () => setView('face');
    get('characterLeft').onclick = () => { yaw = (yaw - 30 + 360) % 360; update(false); };
    get('characterRight').onclick = () => { yaw = (yaw + 30) % 360; update(false); };
    let saved;
    try { saved = JSON.parse(localStorage.getItem(storageKey)); } catch { persisted = false; }
    apply(saved); setView('body');
})();
