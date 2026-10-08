"""Experimental simultaneous frictionless impact; established contacts only."""
import numpy as np
from contact_constraint import resolve_rigid_inelastic_velocity


def resolve_contacts(velocity, angular_velocity, orientation, local_points,
                     inverse_mass, inverse_inertia_body, node_velocities,
                     inverse_node_masses, weights, normals,
                     tolerance=1e-10, max_iterations=2048):
    """Project velocity onto all unilateral contact half-spaces in mass metric.

    Dense laboratory solver. Accumulated nonnegative impulses can decrease
    during iteration; independently clamping each incremental impulse is wrong.
    Reports nonconvergence explicitly. No detection, restitution or friction.
    """
    points=np.asarray(local_points,dtype=float)
    weights=np.asarray(weights,dtype=float);normals=np.asarray(normals,dtype=float)
    nv=np.asarray(node_velocities,dtype=float)
    if points.ndim!=2 or points.shape[1]!=3 or normals.shape!=points.shape or weights.shape!=(len(points),len(nv)) or len(points)==0:
        raise ValueError('Invalid contact batch')
    if not np.isfinite(tolerance) or tolerance<=0 or not isinstance(max_iterations,int) or max_iterations<1:
        raise ValueError('Invalid convergence parameters')
    # Reuse complete primitive validation, including proper orientation/inertia.
    for point,a,n in zip(points,weights,normals):
        resolve_rigid_inelastic_velocity(velocity,angular_velocity,orientation,point,
            inverse_mass,inverse_inertia_body,nv,inverse_node_masses,a,n)
    R=np.asarray(orientation,dtype=float)
    inverse_I=R@np.asarray(inverse_inertia_body,dtype=float)@R.T
    node_w=np.asarray(inverse_node_masses,dtype=float)
    count=len(points);size=6+nv.size
    J=np.zeros((count,size));J[:,:3]=normals
    J[:,3:6]=np.cross(points@R.T,normals)
    J[:,6:]=(-weights[:,:,None]*normals[:,None,:]).reshape(count,-1)
    W=np.zeros((size,size));W[:3,:3]=np.eye(3)*inverse_mass
    W[3:6,3:6]=inverse_I;W[6:,6:]=np.diag(np.repeat(node_w,3))
    initial=np.concatenate((velocity,angular_velocity,nv.ravel()))
    A=J@W@J.T;b=J@initial;impulses=np.zeros(count)
    residual=float('inf')
    for iteration in range(max_iterations):
        for i in range(count):
            if A[i,i]>0:
                impulses[i]=max(0.,impulses[i]-(b[i]+A[i]@impulses)/A[i,i])
        speed=b+A@impulses
        # Active constraints require zero speed; unloaded ones allow separation.
        errors=np.where(impulses>0,np.abs(speed),np.maximum(-speed,0.))
        residual=float(np.max(errors))
        if residual<=tolerance:break
    final=initial+W@J.T@impulses
    return dict(velocity=final[:3],angular_velocity=final[3:6],
        node_velocities=final[6:].reshape(nv.shape),impulses=impulses,
        residual_m_s=residual,converged=residual<=tolerance,iterations=iteration+1)
