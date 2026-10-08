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
