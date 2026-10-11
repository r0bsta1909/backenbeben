"""Gameplay response from the solved contact, retaining first-touch foul rules."""
import math

# Gameplay calibration, not a medical injury threshold.
FULL_POWER_IMPULSE_NS = 2.0

def resolve(scored, contact):
    frames=contact.get('frames',[])
    impulse=frames[-1].get('cumulative_contact_impulse_ns',[0.,0.,0.]) if frames else [0.,0.,0.]
    normal=scored.get('normal',[0.,0.,0.])
    length=math.sqrt(sum(float(v)**2 for v in normal))
    if len(impulse)!=3 or len(normal)!=3 or not all(math.isfinite(float(v)) for v in [*impulse,*normal]):
        raise ValueError('Invalid solved contact impulse')
    # Surface normal points into the cheek; the recorded impulse acts on hand.
    normal_impulse=max(0.,-sum(float(a)*float(b) for a,b in zip(impulse,normal))/length) if length else 0.
    active=any(frame.get('active_contact_samples') for frame in frames) and normal_impulse>1e-8
    coupling=min(1.,max(0.,float(scored.get('contact_area_m2',0.)))/.0015)
    penalty={'tips':.3,'glance':.55}.get(scored.get('contact_class'),1.)
    quality=coupling*min(1.,normal_impulse/FULL_POWER_IMPULSE_NS)*penalty
    hit=bool(scored.get('hit')) and active and not scored.get('foul',False)
    update={'quality':round(quality,4) if hit else 0.,'hit':hit}
    if not active and not scored.get('foul',False):
        update.update(contact_class='miss',diagnosis='Kein wirksamer Kontakt – den Schwung weiter zur Wange führen.')
    return {'normal_impulse_ns':normal_impulse,'contact_active':bool(active),'response_strength':quality if active else 0.,'score_update':update}
