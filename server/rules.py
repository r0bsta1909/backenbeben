"""Authoritative, deterministic slap scoring. No renderer dependencies."""
import math
from face_damage import accumulate_face
DEFAULTS = {'base_damage': 35.0, 'brace_window_ms': 450.0, 'brace_reduction': .35,
            'recovery': 12.0, 'ko_threshold': 100.0, 'turn_seconds': 25.0, 'max_pairs': 5.0}
RANGES = {'base_damage': (5, 45), 'brace_window_ms': (80, 500), 'brace_reduction': (0, .65),
          'recovery': (0, 30), 'ko_threshold': (60, 150), 'turn_seconds': (5, 60), 'max_pairs': (2, 12)}

def score_gesture(data):
    points = data.get('points')
    if not isinstance(points, list) or not 2 <= len(points) <= 180:
        raise ValueError('Ungültiger Schwung')
    previous = -1
    for p in points:
        if not isinstance(p, list) or len(p) != 3 or any(isinstance(v, bool) or not isinstance(v, (float, int)) or not math.isfinite(v) for v in p):
            raise ValueError('Ungültige Koordinaten')
        if not 0 <= p[0] <= 1 or not 0 <= p[1] <= 1 or not previous <= p[2] <= 4000:
            raise ValueError('Ungültige Schwungdaten')
        previous = p[2]
    duration = points[-1][2] - points[0][2]
    if duration < 60 or duration > 3000:
        raise ValueError('Schwung zu kurz oder zu lang')
    x, y, _ = points[-1]
    # Fixed normalized gameplay plane. Cosmetic meshes never change the hit zones.
    distance = min(math.hypot((x-.445)/.10, (y-.435)/.18), math.hypot((x-.555)/.10, (y-.435)/.18))
    precision = max(0.0, 1.0 - distance)
    length = sum(math.hypot(b[0]-a[0], b[1]-a[1]) for a,b in zip(points, points[1:]))
    travel = math.hypot(x-points[0][0], y-points[0][1])
    clean = min(1., travel/max(.001, length))
    reach = min(1., travel/.24)
    # Timing saturates: faster mice have no unlimited bonus.
    rhythm = max(.35, 1.-abs(duration-460)/900)
    if data.get('mode') == 'simple':
        reach, clean = min(1., duration/600), 1.
    quality = precision * (.35*reach + .30*clean + .35*rhythm)
    return {'quality': round(quality, 4), 'precision': round(precision, 4),
            'side': 'L' if x < .5 else 'R', 'duration': duration, 'hit': precision > .05}

def fresh_combat():
    """Independent match-wide state; regional face damage lives elsewhere."""
    return dict(damage=0., stun=0., load=0., received_hits=0, knocked_out=False,
                ko_value=0., ko_ratio=0., combat_stage='stable')


def strike_points(scored):
    """0-10 quality points, independent of wound amount and effect generation."""
    if not scored.get('hit') or scored.get('foul'):return 0
    quality=max(0.,min(1.,float(scored.get('quality',0.))))
    if quality<=0:return 0
    cap={'glance':4,'tips':3}.get(scored.get('contact_class'),10)
    return min(cap,max(1,math.floor(quality*10.+.5)))


def head_motion(clip):
    """Bounded gameplay signal from the first 300ms of the recorded response.

    No dependence on replay camera, frame delivery speed or cosmetic identity.
    Returns normalized excursion and the signed dominant yaw for fall direction.
    """
    frames=clip.get('head_rotations')
    if not frames:frames=[[0.,float(f[0]),0.] for f in clip.get('frames',[])]
    if not frames:return 0.,0.
    fps=float(clip.get('fps',120));contact=float(clip.get('contact',.5))
    start=max(0,int(contact*fps));end=min(len(frames),int((contact+.3)*fps)+1)
    rest=frames[0];peak=0.;yaw=0.
    for row in frames[start:end]:
        delta=[float(v)-float(r) for v,r in zip(row,rest)]
        if len(delta)!=3 or not all(math.isfinite(v) for v in delta):raise ValueError('Invalid head response')
        excursion=math.sqrt(sum(v*v for v in delta))
        if excursion>peak:peak=excursion;yaw=delta[1]
    return min(1.,peak/.20),yaw


def update_combat_status(player,settings):
    value=round(float(player.get('stun',0.))+.4*float(player.get('load',0.)),3)
    ratio=max(0.,min(1.,value/settings['ko_threshold']))
    player.update(ko_value=value,ko_ratio=round(ratio,5),combat_stage=(
        'ko' if player.get('knocked_out',False) else
        'critical' if ratio>=.75 else 'dazed' if ratio>=.45 else 'stable'))


def recover_after_turn(players,completed_strikes,settings):
    """Once per complete pair, never per wall-clock second or replay frame."""
    if completed_strikes<=0 or completed_strikes%2:return
    for player in players:
        if player.get('knocked_out',False):continue
        player['stun']=round(max(0.,player.get('stun',0.)-settings['recovery']),3)
        update_combat_status(player,settings)


def apply_hit(player, scored, settings, braced=False, motion=0.):
    quality=max(0.,min(1.,float(scored.get('quality',0.))))
    valid=bool(scored.get('hit')) and not scored.get('foul',False) and quality>0
    damage=settings['base_damage']*quality if valid else 0.
    damage*=1.-settings['brace_reduction'] if braced else 1.
    if damage<=0:
        update_combat_status(player,settings)
        return 0.,False
    previous_hits=int(player.get('received_hits',0))
    player['damage']=round(min(120.,player.get('damage',0.)+damage),3)
    player['load']=round(min(100.,player.get('load',0.)+damage*.75),3)
    player['stun']=round(min(120.,player.get('stun',0.)+damage*(1.2+.4*max(0.,min(1.,motion)))),3)
    player['received_hits']=previous_hits+1
    player['side']=scored['side']
    zones=player.setdefault('zones',{'L':0.,'R':0.})
    zones[scored['side']]=round(zones[scored['side']]+damage,3)
    accumulate_face(player,scored,damage)
    update_combat_status(player,settings)
    # First valid hit can stagger a fresh fighter, but cannot end the duel.
    ko=previous_hits>=1 and player['ko_value']>=settings['ko_threshold']
    player['knocked_out']=bool(player.get('knocked_out',False) or ko)
    update_combat_status(player,settings)
    return round(damage,2),ko
