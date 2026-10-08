"""One kinematic rigid-hand sweep followed by an inelastic velocity solve.

Constant world velocities define the search path, not free anisotropic rigid-body
integration. No material advance, arm drive, or remaining-interval integration.
"""
from copy import copy
import numpy as np
from contact_rotational_sweep import first_rigid_proximity
from contact_constraint import rotation_increment


def first_hand_impact(hand,cage,velocity,angular_velocity,duration,
                      distance_tolerance=1e-8,velocity_tolerance=1e-8):
    v=np.asarray(velocity,dtype=float);omega=np.asarray(angular_velocity,dtype=float)
    proximity=first_rigid_proximity(hand.center,hand.rotation,hand.local,v,omega,
        cage.p,cage.v,cage.geometry['triangles'],duration,distance_tolerance)
    if proximity['status']!='proximity':return dict(status=proximity['status'],proximity=proximity)
    time=proximity['time_s']
    impact_hand=copy(hand);impact_hand.center=hand.center+v*time
    impact_hand.rotation=rotation_increment(omega*time)@hand.rotation
    impact_cage=copy(cage);impact_cage.p=cage.p+cage.v*time;impact_cage.v=cage.v.copy()
    response=impact_hand.resolve_velocity(impact_cage,v,omega,
        contact_margin=2*distance_tolerance,tolerance=velocity_tolerance,max_iterations=8192)
    if not response['converged']:status='unresolved'
    elif np.any(response['impulses']>0):status='impact'
    else:status='nonclosing_proximity'
    # Preserve input states. Caller explicitly chooses whether to commit an event.
    return dict(status=status,proximity=proximity,response=response,
                hand=impact_hand,cage=impact_cage)
