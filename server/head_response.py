"""One-axis passive head/neck response to the solved contact moment.

Parameters are prototype tuning, not measured anatomical properties. Contact
still uses an anchored cage; this response begins only after that interval.
"""
import math

YAW_INERTIA_KG_M2 = .018
NECK_STIFFNESS_NM_RAD = 1.62
NECK_DAMPING_NMS_RAD = .216

def yaw_state(moment_y_nms, time, braced=False):
    """Return shader yaw and angular velocity, with no timestep-dependent kick.

Recorded moment acts on the hand. The opposite acts on the head; the shader
rotates around negative Y, hence its initial velocity is +hand_moment_y / I.
"""
    if not math.isfinite(moment_y_nms) or not math.isfinite(time):
        raise ValueError('Finite head impulse and time required')
    if time < 0:
        return 0., 0.
    inertia=YAW_INERTIA_KG_M2
    stiffness=NECK_STIFFNESS_NM_RAD*(1.5 if braced else 1.)
    damping=NECK_DAMPING_NMS_RAD/(2*inertia)
    frequency=math.sqrt(stiffness/inertia-damping*damping)
    initial_velocity=moment_y_nms/inertia
    envelope=initial_velocity*math.exp(-damping*time)
    angle=envelope*math.sin(frequency*time)/frequency
    velocity=envelope*(math.cos(frequency*time)-damping*math.sin(frequency*time)/frequency)
    return angle,velocity
