"""Candidate mesh-derived contact sheet; not yet used by match scoring.

Blend the hand and forearm transforms exactly as the exported skin does.
Individual fingers currently retain their rest poses relative to the hand.
"""
import json
from pathlib import Path
from arm import add,sub,mul,dot,unit
DATA=json.loads((Path(__file__).resolve().parents[1]/'game/assets/hand_contact_surface_v3.json').read_text())
def cross(a,b):return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
def world_samples(pose,finger,normal):
 width=cross(finger,normal)
 forearm=unit(sub(pose['wrist'],pose['elbow']))
 fore_normal=unit(sub(normal,mul(forearm,dot(normal,forearm))))
 fore_width=cross(forearm,fore_normal)
 result=[]
 for sample in DATA['samples']:
  u,a,d=sample['local'];blend=sample['hand_weight']
  hand=add(add(mul(width,u),mul(finger,a)),mul(normal,d))
  fore=add(add(mul(fore_width,u),mul(forearm,a)),mul(fore_normal,d))
  point=add(pose['wrist'],add(mul(hand,blend),mul(fore,1-blend)))
  result.append((sample['region'],point,sample['area_m2']))
 return result
