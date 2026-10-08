"""Compiled version of the same sequential rigid-sheet XPBD projection.

No fast-math, changed contact order, relaxed tolerances or reduced samples.
The Python implementation remains the comparison reference.
"""
import numpy as np
from numba import njit
from rigid_hand_contact import RigidHandContact
from contact_embedding_compiled import intersections

@njit(cache=True)
def dot3(a,b):return a[0]*b[0]+a[1]*b[1]+a[2]*b[2]

@njit(cache=True)
def matvec(a,b):
    return np.array([dot3(a[0],b),dot3(a[1],b),dot3(a[2],b)])

@njit(cache=True)
def matmul(a,b):
    out=np.empty((3,3))
    for i in range(3):
        for j in range(3):out[i,j]=a[i,0]*b[0,j]+a[i,1]*b[1,j]+a[i,2]*b[2,j]
    return out

@njit(cache=True)
def rotation_increment(v):
    angle=np.sqrt(np.sum(v*v))
    if angle<1e-15:return np.eye(3)
    x,y,z=v/angle
    skew=np.array([[0.,-z,y],[z,0.,-x],[-y,x,0.]])
    return np.eye(3)+np.sin(angle)*skew+(1-np.cos(angle))*matmul(skew,skew)

@njit(cache=True)
def project_sheet(center,rotation,local,inverse_mass,inertia,nodes,w,triangles,
                  best,weights,normals,multipliers,keys,dt,skip_separated):
    contacts=0;switches=0;impulse=np.zeros(3)
    for i in range(len(local)):
        triangle=best[i]
        if triangle<0:
            multipliers[i]=0.;keys[i]=-1;continue
        if triangle!=keys[i]:
            switches+=int(keys[i]>=0);multipliers[i]=0.
        keys[i]=triangle
        ids=triangles[triangle];a=weights[i];normal=normals[i]
        r=matvec(rotation,local[i])
        surface=a[0]*nodes[ids[0]]+a[1]*nodes[ids[1]]+a[2]*nodes[ids[2]]
        gap=dot3(center+r-surface,normal)
        if skip_separated and multipliers[i]==0. and gap>=0.:continue
        world_inertia=matmul(matmul(rotation,inertia),rotation.T)
        angular=np.cross(r,normal)
        effective=inverse_mass+dot3(angular,matvec(world_inertia,angular))
        for j in range(3):effective+=w[ids[j]]*a[j]*a[j]
        previous=multipliers[i]
        updated=max(0.,previous-gap/effective) if effective>0 else 0.
        delta=updated-previous;multipliers[i]=updated
        center=center+inverse_mass*delta*normal
        rotation=matmul(rotation_increment(matvec(world_inertia,angular)*delta),rotation)
        for j in range(3):nodes[ids[j]]-=w[ids[j]]*a[j]*delta*normal
        impulse+=delta*normal/dt
        contacts+=int(updated>0.)
    return center,rotation,contacts,switches,impulse

class CompiledRigidHandContact(RigidHandContact):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.triangle_keys=np.full(len(self.local),-1,dtype=np.int64)
    def begin_step(self):
        super().begin_step();self.triangle_keys.fill(-1)
    def project(self,cage,dt,skip_separated=True):
        if not np.isfinite(dt) or dt<=0:raise ValueError('Positive finite timestep required')
        best,weights,_,normals=intersections(self.points(),cage.p,cage.geometry['triangles'])
        self.center,self.rotation,self.last_contacts,switches,impulse=project_sheet(
            self.center,self.rotation,self.local,self.inverse_mass,self.inverse_inertia,
            cage.p,cage.w,cage.geometry['triangles'],best,weights,normals,
            self.multipliers,self.triangle_keys,dt,skip_separated)
        self.step_contact_switches+=switches;self.step_contact_impulse+=impulse
    def penetration(self,cage):
        points=self.points()
        best,_,positions,normals=intersections(points,cage.p,cage.geometry['triangles'])
        valid=best>=0
        return max(0.,-float(np.min(np.sum((points[valid]-positions[valid])*normals[valid],axis=1)))) if np.any(valid) else 0.
