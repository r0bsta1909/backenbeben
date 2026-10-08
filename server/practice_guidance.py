"""Optional geometric practice advice; never changes the submitted stroke."""
from copy import deepcopy

def wheel_hint(data,preview,scorer):
    kind=preview.get('contact_class')
    if kind=='flat':return 'Haltung beibehalten. Der naechste Zug zaehlt; mit Noch einmal ueben bleibt er schadensfrei.'
    if kind not in ('tips','glance','heel'):return 'Treffhoehe und Schwung in der Seitenansicht pruefen, dann Noch einmal ueben waehlen.'
    def rank(result):
        return (2 if result.get('contact_class')=='flat' else 1 if result.get('hit') else 0,float(result.get('coverage',0)))
    candidates=[]
    for delta in (-3,3):
        changed=deepcopy(data)
        if not changed.get('points') or any(len(p)<5 for p in changed['points']):continue
        for point in changed['points']:point[4]=max(-45,min(45,point[4]+delta))
        result=scorer(changed)
        if rank(result)>rank(preview):candidates.append((rank(result),delta))
    if not candidates:return 'Hand von der Seite ansehen und eine andere Neigung schadensfrei proben.'
    delta=max(candidates)[1]
    direction='nach unten (zu dir)' if delta>0 else 'nach oben (von dir weg)'
    return 'Tipp fuer diese Probe: Mausrad eine Rastung '+direction+'. Danach Noch einmal ueben waehlen und erneut ziehen.'


def tilted_probe(data,tilt):
    """Same saved mouse path, explicitly chosen constant wrist tilt; no auto-fit."""
    import math
    if isinstance(tilt,bool) or not isinstance(tilt,(int,float)) or not math.isfinite(tilt) or not -45<=tilt<=45:
        raise ValueError('Ungültige Handneigung.')
    changed=deepcopy(data)
    for point in changed['points']:point[4]=tilt
    return changed
