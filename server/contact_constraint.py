"""Experimental bilateral-mass, unilateral XPBD contact primitive.
Not yet used by match scoring. SI positions/masses; no friction or restitution.
Original implementation following Macklin et al. 2016, equations 17/18.
"""
import numpy as np

def project_contact(hand, nodes, inverse_hand_mass, inverse_node_masses,
                    weights, normal, dt, compliance=0., multiplier=0.):
    """Project one contact; normal points from tissue toward hand.

    Returns corrected copies and accumulated nonnegative multiplier. Reset the
    multiplier each substep, retain it across iterations within that substep.
    Weights reconstruct a tissue point and must form a partition of unity.
    """
    h=np.array(hand,dtype=float,copy=True);p=np.array(nodes,dtype=float,copy=True)
    w=np.asarray(inverse_node_masses,dtype=float);a=np.asarray(weights,dtype=float)
    n=np.asarray(normal,dtype=float)
    if h.shape!=(3,) or p.shape!=(len(a),3) or w.shape!=a.shape or n.shape!=(3,):raise ValueError('Contact shape mismatch')
    scalars=np.array([inverse_hand_mass,dt,compliance,multiplier])
    if not all(np.isfinite(x).all() for x in [h,p,w,a,n,scalars]):raise ValueError('Nonfinite contact')
    if dt<=0 or min(inverse_hand_mass,compliance,multiplier)<0 or np.any(w<0) or np.any(a<0):raise ValueError('Invalid mass or compliance')
    if not np.isclose(a.sum(),1.,atol=1e-10,rtol=0) or abs(np.linalg.norm(n)-1)>1e-8:raise ValueError('Contact weights/normal must be normalized')
    gap=float(np.dot(h-a@p,n))
    alpha=compliance/(dt*dt)
    effective=inverse_hand_mass+float(np.dot(w,a*a))
    if effective<=0:return h,p,0.
    delta=(-gap-alpha*multiplier)/(effective+alpha)
    updated=max(0.,multiplier+delta);delta=updated-multiplier
    h+=inverse_hand_mass*delta*n
    p-=((w*a)*delta)[:,None]*n
    return h,p,updated

def project_attachment(hand,arm,inverse_hand_mass,inverse_arm_mass,rest_offset,dt,compliance,multiplier):
    """Compliant vector attachment; equal/opposite mass-weighted corrections."""
    h=np.array(hand,dtype=float,copy=True);a=np.array(arm,dtype=float,copy=True)
    offset=np.asarray(rest_offset,dtype=float);lam=np.asarray(multiplier,dtype=float)
    if any(x.shape!=(3,) or not np.isfinite(x).all() for x in [h,a,offset,lam]):raise ValueError('Invalid attachment vector')
    if not np.isfinite([inverse_hand_mass,inverse_arm_mass,dt,compliance]).all() or dt<=0 or min(inverse_hand_mass,inverse_arm_mass,compliance)<0:raise ValueError('Invalid attachment parameters')
    alpha=compliance/(dt*dt);weight=inverse_hand_mass+inverse_arm_mass
    if weight==0:return h,a,np.zeros(3)
    delta=(-(h-a-offset)-alpha*lam)/(weight+alpha)
    return h+inverse_hand_mass*delta,a-inverse_arm_mass*delta,lam+delta


def rotation_increment(vector):
    """SO(3) exponential for a world-space rotation vector."""
    vector=np.asarray(vector,dtype=float);angle=float(np.linalg.norm(vector))
    if angle<1e-15:return np.eye(3)
    x,y,z=vector/angle
    skew=np.array([[0.,-z,y],[z,0.,-x],[-y,x,0.]])
    return np.eye(3)+np.sin(angle)*skew+(1-np.cos(angle))*(skew@skew)


def project_rigid_contact(center,orientation,local_point,inverse_mass,inverse_inertia_body,
                          nodes,inverse_node_masses,weights,normal,dt,compliance=0.,multiplier=0.):
    """One frictionless XPBD contact against a rigid hand with angular response.

    Orientation maps body to world. Inertia is about center in body coordinates.
    Returns corrected center/orientation/tissue/multiplier. Re-evaluate surface
    embedding and normal as the body moves; this primitive does not find contact.
    """
    center=np.array(center,dtype=float,copy=True);rotation=np.array(orientation,dtype=float,copy=True)
    local=np.asarray(local_point,dtype=float);inertia=np.asarray(inverse_inertia_body,dtype=float)
    p=np.array(nodes,dtype=float,copy=True);w=np.asarray(inverse_node_masses,dtype=float)
    a=np.asarray(weights,dtype=float);n=np.asarray(normal,dtype=float)
    if center.shape!=(3,) or rotation.shape!=(3,3) or local.shape!=(3,) or inertia.shape!=(3,3) or p.shape!=(len(a),3) or w.shape!=a.shape or n.shape!=(3,):raise ValueError('Rigid contact shape mismatch')
    if not all(np.isfinite(x).all() for x in [center,rotation,local,inertia,p,w,a,n,[inverse_mass,dt,compliance,multiplier]]):raise ValueError('Nonfinite rigid contact')
    if dt<=0 or min(inverse_mass,compliance,multiplier)<0 or np.any(w<0) or np.any(a<0):raise ValueError('Invalid rigid contact parameters')
    if not np.allclose(rotation.T@rotation,np.eye(3),atol=1e-9,rtol=0) or np.linalg.det(rotation)<0:raise ValueError('Orientation must be a proper rotation')
    if not np.allclose(inertia,inertia.T,atol=1e-12,rtol=0) or np.min(np.linalg.eigvalsh(inertia))<-1e-12:raise ValueError('Inverse inertia must be positive semidefinite')
    if not np.isclose(a.sum(),1.,atol=1e-10,rtol=0) or abs(np.linalg.norm(n)-1)>1e-8:raise ValueError('Weights and normal must be normalized')
    r=rotation@local;world_inertia=rotation@inertia@rotation.T
    angular=np.cross(r,n)
    effective=inverse_mass+float(angular@world_inertia@angular)+float(np.dot(w,a*a))
    if effective<=0:return center,rotation,p,0.
    alpha=compliance/(dt*dt);gap=float((center+r-a@p)@n)
    delta=(-gap-alpha*multiplier)/(effective+alpha)
    updated=max(0.,multiplier+delta);delta=updated-multiplier
    center+=inverse_mass*delta*n
    rotation=rotation_increment(world_inertia@angular*delta)@rotation
    p-=((w*a)*delta)[:,None]*n
    return center,rotation,p,updated
