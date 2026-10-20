# Turnier-UI: interaktiver Entwurf

`tournament.html` lokal im Browser öffnen. Alternativ im Projektordner einen
statischen Server starten und `/docs/ui-preview/tournament.html` öffnen.

Die Vorschau verwendet dieselbe Oberfläche wie das Spiel: `game/tournament.js`,
`game/tournament.css` und den aus `game/web_shell.html` erzeugten Panel-Aufbau.
Die Beispielnamen und Ergebnisse sind ausdrücklich fiktiv. Es laufen weder ein
Match noch eine Physikberechnung. Der eigentliche LAN-Modus bleibt im Web-Build.

Oben zwischen Lobby, Turnierbaum, Champion und Abbruch sowie 8/20 Spielern wechseln.
„Mein Weg“ führt zur eigenen Paarung; der Code lässt sich kopieren. Starten und
Verlassen zeigen in der Vorschau einen Hinweis und verändern kein echtes Turnier.

Nach Änderungen an `game/web_shell.html` den Vorschau-Aufbau neu erzeugen:

```powershell
.venv/Scripts/python.exe scripts/build_ui_preview.py
```

Gestaltung: dunkle Arena, warme Papierfarbe, goldene Akzente, markante Schriften,
rote/blaue Teilnehmermarkierungen, verbundene Paarungen und eigener Champion-Bereich.
Schmale Ansichten verwenden getrennte Scrollbereiche für Oberfläche und Turnierbaum.
Die echte Spieler-, Kampf- und Weiterkommenslogik wird weiterhin vom Host bestimmt.
