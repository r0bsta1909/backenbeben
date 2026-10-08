"""JIT evaluation of the existing arm FK frame; checked against Arm.joints."""
import math
import numpy as np
from numba import njit
from arm import L1,L2,SHOULDER

@njit(cache=True)
def frame(q,torso):
    yaw,elevation,flex=q
    sy,cy=math.sin(yaw),math.cos(yaw)
    upper=np.array([sy*math.cos(elevation)*L1,math.sin(elevation)*L1,-cy*math.cos(elevation)*L1])
    reach=upper+np.array([sy*math.cos(elevation+flex)*L2,math.sin(elevation+flex)*L2,-cy*math.cos(elevation+flex)*L2])
    axis=reach/math.sqrt(np.sum(reach*reach))
    amount=max(0.,min(1.,(.28-(SHOULDER[2]+reach[2]))/.10))
    amount=amount*amount*(3-2*amount)
    angle=-math.radians(35+43*amount)
    elbow=upper*math.cos(angle)+np.cross(axis,upper)*math.sin(angle)+axis*np.sum(axis*upper)*(1-math.cos(angle))
    forward=reach-elbow
    c,s=math.cos(torso),math.sin(torso)
    f=np.array([c*forward[0]+s*forward[2],forward[1],-s*forward[0]+c*forward[2]])
    e=np.array([c*elbow[0]+s*elbow[2],elbow[1],-s*elbow[0]+c*elbow[2]])
    f/=math.sqrt(np.sum(f*f))
    n=np.cross(f,e);length=math.sqrt(np.sum(n*n))
    if length<1e-10:raise ValueError('Forearm frame requires a bent arm')
    n/=length;w=np.cross(f,n)
    return np.array([[w[0],f[0],n[0]],[w[1],f[1],n[1]],[w[2],f[2],n[2]]])

def forearm_frame(arm,q):return frame(np.asarray(q,dtype=float),arm.torso_yaw)
