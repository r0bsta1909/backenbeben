"""Tangential XPBD block primitive; integration into hand/sheet remains pending.

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
