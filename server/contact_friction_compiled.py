"""Compiled equivalent of the experimental tangential contact projection."""
import numpy as np
from numba import njit
from rigid_hand_compiled import rotation_increment

@njit(cache=True)
def norm(v):return np.sqrt(np.sum(v*v))

@njit(cache=True)
def mv(a,b):
    out=np.zeros(a.shape[0])
    for i in range(a.shape[0]):
        for j in range(a.shape[1]):out[i]+=a[i,j]*b[j]
    return out

@njit(cache=True)
def mm(a,b):
    out=np.zeros((a.shape[0],b.shape[1]))
    for i in range(a.shape[0]):
        for j in range(b.shape[1]):
            for k in range(a.shape[1]):out[i,j]+=a[i,k]*b[k,j]
    return out

@njit(cache=True)
def solve2(K,d,gamma):
    a=K[0,0]+gamma;b=K[0,1];c=K[1,0];e=K[1,1]+gamma
    determinant=a*e-b*c
    return np.array([(-e*d[0]+b*d[1])/determinant,(c*d[0]-a*d[1])/determinant])

@njit(cache=True)
def tangent_block(d,K,normal,mu):
    cap=normal*mu
    if cap==0:return np.zeros(2)
    free=solve2(K,d,0.)
    if norm(free)<=cap:return free
    lo=0.;hi=norm(d)/cap
    for _ in range(64):
        mid=(lo+hi)*.5;trial=solve2(K,d,mid)
        if norm(trial)>cap:lo=mid
        else:hi=mid
    return solve2(K,d,hi)

@njit(cache=True)
def project_friction(center,rotation,local,inverse_mass,inverse_inertia,nodes,w,triangles,
                     best,weights,normals,normal_multipliers,normal_keys,
                     old_points,old_nodes,keys,anchors,multipliers,coefficient,dt):
    impulse=np.zeros(3);moment=np.zeros(3);residual=0.;cone_error=0.
    for i in range(len(best)):
        triangle=best[i]
        if triangle<0 or triangle!=normal_keys[i]:
            keys[i]=-1;multipliers[i]=0.;continue
        ids=triangles[triangle];n=normals[i]
        if keys[i]!=triangle:
            keys[i]=triangle;anchors[i]=weights[i];multipliers[i]=0.
        a=anchors[i];axis=np.zeros(3);axis[np.argmin(np.abs(n))]=1.
        t0=np.cross(n,axis);t0/=norm(t0)
        T=np.empty((2,3));T[0]=t0;T[1]=np.cross(n,t0)
        r=mv(rotation,local[i]);surface=np.zeros(3);old_surface=np.zeros(3);node_mass=0.
        for j in range(3):
            surface+=a[j]*nodes[ids[j]];old_surface+=a[j]*old_nodes[ids[j]]
            node_mass+=w[ids[j]]*a[j]*a[j]
        displacement=(center+r-old_points[i])-(surface-old_surface)
        inertia=mm(mm(rotation,inverse_inertia),rotation.T)
        angular=np.empty((2,3));angular[0]=np.cross(r,T[0]);angular[1]=np.cross(r,T[1])
        K=np.eye(2)*(inverse_mass+node_mass)+mm(mm(angular,inertia),angular.T)
        previous=mv(T,multipliers[i])
        updated=tangent_block(mv(T,displacement)-mv(K,previous),K,normal_multipliers[i],coefficient)
        delta=mv(T.T,updated-previous)
        residual=max(residual,norm(mv(K,updated-previous)))
        multipliers[i]=mv(T.T,updated)
        cone_error=max(cone_error,norm(updated)-coefficient*normal_multipliers[i])
        center+=inverse_mass*delta
        rotation=mm(rotation_increment(mv(inertia,np.cross(r,delta))),rotation)
        for j in range(3):nodes[ids[j]]-=w[ids[j]]*a[j]*delta
        impulse+=delta/dt;moment+=np.cross(surface,delta/dt)
    return center,rotation,impulse,moment,residual,cone_error
