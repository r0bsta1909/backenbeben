"""Tangential XPBD block and experimental hand/sheet projection.

Solve min 0.5*j.T*K*j + displacement.T*j with ||j|| <= mu*lambda_n.
K includes both bodies' inverse masses and rotational responses. Multipliers
have position-solver units, not Newton seconds. A single coefficient is used.
"""
import numpy as np

def tangent_correction(displacement, effective_inverse_mass, normal_multiplier, coefficient):
    d=np.asarray(displacement,dtype=float);K=np.asarray(effective_inverse_mass,dtype=float)
    if d.shape!=(2,) or K.shape!=(2,2) or not np.all(np.isfinite(d)) or not np.all(np.isfinite(K)):
        raise ValueError('Finite 2D displacement and 2x2 mass block required')
    if not np.isfinite(normal_multiplier) or not np.isfinite(coefficient) or normal_multiplier<0 or coefficient<0:
        raise ValueError('Nonnegative finite contact load and coefficient required')
    if not np.allclose(K,K.T,rtol=0,atol=1e-12) or np.linalg.eigvalsh(K)[0]<=0:
        raise ValueError('Symmetric positive definite mass block required')
    cap=normal_multiplier*coefficient
    if not np.isfinite(cap):raise ValueError('Finite friction bound required')
    if cap==0:return np.zeros(2)
    free=-np.linalg.solve(K,d)
    if np.linalg.norm(free)<=cap:return free
    # A Euclidean clamp of free is wrong for anisotropic effective mass.
    # The disk-constrained quadratic has (K + gamma I) j = -d.
    lo=0.;hi=np.linalg.norm(d)/cap
    for _ in range(64):
        mid=(lo+hi)*.5
        trial=-np.linalg.solve(K+mid*np.eye(2),d)
        if np.linalg.norm(trial)>cap:lo=mid
        else:hi=mid
    return -np.linalg.solve(K+hi*np.eye(2),d)


class HandSheetFriction:
    """Per-substep material anchors; called after the normal contact projection.

    Only the compiled normal solver exposes stable triangle identifiers.
    Normal and tangential impulses remain separate for contact scoring.
    """
    def __init__(self,hand,coefficient,compiled=True):
        if not np.isfinite(coefficient) or coefficient<0:raise ValueError('Invalid friction coefficient')
        self.hand=hand;self.coefficient=coefficient;self.compiled=compiled

    def begin_step(self,cage):
        self.old_points=self.hand.points().copy();self.old_nodes=cage.p.copy()
        self.keys=np.full(len(self.old_points),-1,dtype=int)
        self.weights=np.zeros((len(self.old_points),3))
        self.multipliers=np.zeros_like(self.old_points)
        self.impulse=np.zeros(3);self.moment=np.zeros(3);self.residual=0.;self.max_cone_error=0.

    def project(self,cage,dt):
        from contact_embedding_compiled import intersections
        from contact_constraint import rotation_increment
        hand=self.hand;triangles=cage.geometry['triangles']
        best,weights,_,normals=intersections(hand.points(),cage.p,triangles)
        if self.compiled:
            from contact_friction_compiled import project_friction
            hand.center,hand.rotation,impulse,moment,self.residual,cone_error=project_friction(
                hand.center,hand.rotation,hand.local,hand.inverse_mass,hand.inverse_inertia,
                cage.p,cage.w,triangles,best,weights,normals,hand.multipliers,hand.triangle_keys,
                self.old_points,self.old_nodes,self.keys,self.weights,self.multipliers,self.coefficient,dt)
            self.impulse+=impulse;self.moment+=moment;self.max_cone_error=max(self.max_cone_error,cone_error)
            return
        self.residual=0.
        for i,triangle in enumerate(best):
            if triangle<0 or triangle!=hand.triangle_keys[i]:
                self.keys[i]=-1;self.multipliers[i]=0.;continue
            ids=triangles[triangle];n=normals[i]
            if self.keys[i]!=triangle:
                self.keys[i]=triangle;self.weights[i]=weights[i];self.multipliers[i]=0.
            a=self.weights[i]
            # Deterministic tangent frame, with accumulated multiplier in world space.
            axis=np.eye(3)[np.argmin(np.abs(n))]
            t0=np.cross(n,axis);t0/=np.linalg.norm(t0);T=np.array([t0,np.cross(n,t0)])
            r=hand.rotation@hand.local[i];surface=a@cage.p[ids]
            displacement=(hand.center+r-self.old_points[i])-(surface-a@self.old_nodes[ids])
            inertia=hand.rotation@hand.inverse_inertia@hand.rotation.T
            angular=np.cross(r,T)
            K=np.eye(2)*(hand.inverse_mass+np.sum(cage.w[ids]*a*a))+angular@inertia@angular.T
            previous=T@self.multipliers[i]
            updated=tangent_correction(T@displacement-K@previous,K,float(hand.multipliers[i]),self.coefficient)
            delta=T.T@(updated-previous)
            self.residual=max(self.residual,float(np.linalg.norm(K@(updated-previous))))
            self.multipliers[i]=T.T@updated
            self.max_cone_error=max(self.max_cone_error,float(np.linalg.norm(updated)-self.coefficient*hand.multipliers[i]))
            hand.center+=hand.inverse_mass*delta
            hand.rotation=rotation_increment(inertia@np.cross(r,delta))@hand.rotation
            cage.p[ids]-=(cage.w[ids]*a)[:,None]*delta
            self.impulse+=delta/dt;self.moment+=np.cross(surface,delta/dt)
