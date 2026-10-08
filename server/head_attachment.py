"""Experimental two-way yaw attachment between tissue boundary and a rigid head.

Uses the shader's negative-Y angle convention. Head origin is fixed for now;
only yaw is dynamic. Constants are prototype parameters, not anatomical data.
"""
import math
import numpy as np
from numba import njit
from head_response import YAW_INERTIA_KG_M2,NECK_STIFFNESS_NM_RAD,NECK_DAMPING_NMS_RAD

@njit(cache=True)
def project_pins(p,w,rest,ids,angle,inverse_inertia):
    for index in ids:
        for axis in range(3):
            c=math.cos(angle);s=math.sin(angle)
            x=c*rest[index,0]-s*rest[index,2]
            z=s*rest[index,0]+c*rest[index,2]
            target=x if axis==0 else rest[index,1] if axis==1 else z
            gradient=z if axis==0 else 0. if axis==1 else -x
            error=p[index,axis]-target
            delta=-error/(w[index]+inverse_inertia*gradient*gradient)
            p[index,axis]+=w[index]*delta
            angle+=inverse_inertia*gradient*delta
    return angle

class HeadAttachment:
    def __init__(self,cage,braced=False):
        self.ids=np.flatnonzero((cage.w==0)&(cage.node_masses>0))
        cage.w[self.ids]=1/cage.node_masses[self.ids]
        self.cage=cage;self.angle=0.;self.velocity=0.;self.old_angle=0.
        self.inverse_inertia=1/YAW_INERTIA_KG_M2
        self.stiffness=NECK_STIFFNESS_NM_RAD*(1.5 if braced else 1.)
        self.multiplier=0.
    def begin_step(self,dt):
        self.old_angle=self.angle;self.multiplier=0.
        self.velocity*=math.exp(-NECK_DAMPING_NMS_RAD*self.inverse_inertia*dt)
        self.angle+=self.velocity*dt
    def project(self,dt):
        self.angle=project_pins(self.cage.p,self.cage.w,self.cage.rest,self.ids,self.angle,self.inverse_inertia)
        alpha=1/(self.stiffness*dt*dt)
        delta=(-self.angle-alpha*self.multiplier)/(self.inverse_inertia+alpha)
        self.multiplier+=delta;self.angle+=self.inverse_inertia*delta
    def finish_step(self,dt):self.velocity=(self.angle-self.old_angle)/dt
    def residual(self):
        points=self.cage.rest[self.ids].copy();c=math.cos(self.angle);s=math.sin(self.angle)
        x=points[:,0].copy();z=points[:,2].copy()
        points[:,0]=c*x-s*z;points[:,2]=s*x+c*z
        return float(np.max(np.linalg.norm(self.cage.p[self.ids]-points,axis=1)))
    def energy(self):
        return .5*self.velocity*self.velocity/self.inverse_inertia+.5*self.stiffness*self.angle*self.angle
