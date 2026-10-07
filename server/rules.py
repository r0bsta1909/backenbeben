"""Authoritative, deterministic slap scoring. No renderer dependencies."""
import math
DEFAULTS = {'base_damage': 25.0, 'brace_window_ms': 450.0, 'brace_reduction': .35,
            'recovery': 6.0, 'ko_threshold': 100.0, 'turn_seconds': 25.0, 'max_pairs': 5.0}
RANGES = {'base_damage': (5, 45), 'brace_window_ms': (80, 500), 'brace_reduction': (0, .65),
          'recovery': (0, 15), 'ko_threshold': (60, 150), 'turn_seconds': (5, 60), 'max_pairs': (2, 12)}

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

def apply_hit(player, scored, settings, braced=False):
    damage = settings['base_damage'] * max(.05,scored['quality']) if scored['hit'] else 0.
    damage *= 1.-settings['brace_reduction'] if braced else 1.
    player['damage'] = round(min(120., player['damage'] + damage), 3)
    player['stun'] = round(min(80., player['stun'] + damage*.55), 3)
    player['side'] = scored['side']
    zones = player.setdefault('zones', {'L': 0., 'R': 0.})
    zones[scored['side']] = round(zones[scored['side']] + damage, 3)
    return round(damage, 2), player['damage'] + player['stun'] >= settings['ko_threshold']
