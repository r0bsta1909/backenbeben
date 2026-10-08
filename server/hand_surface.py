"""Mesh-derived contact sheet shared by live poses and match scoring.

Blend the hand and forearm transforms exactly as the exported skin does.
Individual fingers currently retain their rest poses relative to the hand.
"""
import json
import numpy as np
from pathlib import Path
from arm import add,sub,mul,dot,unit
DATA=json.loads((Path(__file__).resolve().parents[1]/'game/assets/hand_contact_surface_v3.json').read_text())
def cross(a,b):return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
LOCAL=np.array([s['local'] for s in DATA['samples']])
HAND_LOCAL=np.array([s['hand_local'] for s in DATA['samples']])
FORE_LOCAL=LOCAL-HAND_LOCAL
def world_positions(pose,finger,normal):
 width=cross(finger,normal)
 forearm=unit(sub(pose['wrist'],pose['elbow']))
 fore_normal=unit(sub(normal,mul(forearm,dot(normal,forearm))))
 fore_width=cross(forearm,fore_normal)
 hand=HAND_LOCAL@np.array([width,finger,normal])
 fore=FORE_LOCAL@np.array([fore_width,forearm,fore_normal])
 return np.array(pose['wrist'])+hand+fore
def world_samples(pose,finger,normal):
 return [(s['region'],point.tolist(),s['area_m2']) for s,point in zip(DATA['samples'],world_positions(pose,finger,normal))]
