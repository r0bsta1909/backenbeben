"""Torque-free rigid rotation with implicit midpoint Euler equations.

Cayley orientation update paired with body angular momentum midpoint preserves
world angular momentum and quadratic rotational energy to solver tolerance.
This is a time discretization with phase error, not an exact rotation solution.
"""
import numpy as np


def skew(v):
    x,y,z=v
    return np.array([[0.,-z,y],[z,0.,-x],[-y,x,0.]])


def advance_free_rotation(orientation,angular_velocity,inertia_body,dt,
                          tolerance=1e-12,max_iterations=32):
    R=np.asarray(orientation,dtype=float);omega=np.asarray(angular_velocity,dtype=float)
    I=np.asarray(inertia_body,dtype=float)
    if R.shape!=(3,3) or I.shape!=(3,3) or omega.shape!=(3,):raise ValueError('Invalid rigid state shapes')
    if not all(np.isfinite(v).all() for v in (R,I,omega,[dt,tolerance])) or dt<0 or tolerance<=0 or not isinstance(max_iterations,int) or max_iterations<1:
        raise ValueError('Invalid rigid integration values')
    if not np.allclose(R.T@R,np.eye(3),atol=1e-9,rtol=0) or np.linalg.det(R)<0:
        raise ValueError('Orientation must be a proper rotation')
    if not np.allclose(I,I.T,atol=1e-12,rtol=0) or np.min(np.linalg.eigvalsh(I))<=0:
        raise ValueError('Inertia must be positive definite')
    inverse=np.linalg.inv(I);initial=R.T@omega;final=initial.copy()
    for iteration in range(max_iterations):
        middle=.5*(initial+final);momentum=I@middle
        residual=final-initial+dt*(inverse@np.cross(middle,momentum))
        error=float(np.linalg.norm(residual,np.inf))
        if error<=tolerance:break
        jacobian=np.eye(3)+.5*dt*inverse@(-skew(momentum)+skew(middle)@I)
        final-=np.linalg.solve(jacobian,residual)
    else:raise RuntimeError('Free rotation midpoint did not converge')
    half=.5*dt*skew(middle)
    increment=np.linalg.solve(np.eye(3)-half,np.eye(3)+half)
    updated=R@increment
    return dict(orientation=updated,angular_velocity=updated@final,
                residual_rad_s=error,iterations=iteration+1)
