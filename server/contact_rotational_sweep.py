"""Conservative proximity sweep for constant world angular/linear velocities.

Point samples versus linearly moving triangle vertices, no face/edge sweep of
hand surface. A proximity event still requires normal/closing-velocity filtering.
"""
import numpy as np
from contact_constraint import rotation_increment


def nearest_triangle_distance(points,nodes,triangles):
    q=nodes[triangles];a=q[:,0];e=q[:,1]-a;f=q[:,2]-a
    d=points[:,None,:]-a[None,:,:]
    ee=np.sum(e*e,axis=1);ff=np.sum(f*f,axis=1);ef=np.sum(e*f,axis=1)
    de=np.sum(d*e,axis=2);df=np.sum(d*f,axis=2)
    determinant=ee*ff-ef*ef;valid=determinant>1e-28
    denominator=np.where(valid,determinant,1.)
    u=(de*ff-df*ef)/denominator;v=(df*ee-de*ef)/denominator
    projection=a[None,:,:]+u[:,:,None]*e+v[:,:,None]*f
    inside=valid[None,:]&(u>=0)&(v>=0)&(u+v<=1)
    distances=np.where(inside,np.sum((points[:,None,:]-projection)**2,axis=2),np.inf)
    for i,j in ((0,1),(1,2),(2,0)):
        start=q[:,i];edge=q[:,j]-start;length=np.sum(edge*edge,axis=1)
        t=np.clip(np.sum((points[:,None,:]-start)*edge,axis=2)/np.maximum(length,1e-30),0,1)
        closest=start+t[:,:,None]*edge
        distances=np.minimum(distances,np.sum((points[:,None,:]-closest)**2,axis=2))
    sample,triangle=np.unravel_index(np.argmin(distances),distances.shape)
    return float(np.sqrt(distances[sample,triangle])),int(sample),int(triangle)


def nearest_triangle_distance_bounded(points,nodes,triangles):
    """Exact pruning: AABB lower bound versus a real vertex upper bound.

    Any selected vertex lies on a candidate triangle, so its distance is an
    upper bound for the global minimum. A triangle box farther away cannot win.
    No temporal approximation or contact margin is introduced.
    """
    q=nodes[triangles]
    vertex_delta=points[:,None,:]-q[None,:,0,:]
    upper_squared=float(np.min(np.sum(vertex_delta*vertex_delta,axis=2)))
    lower=q.min(axis=1);upper=q.max(axis=1)
    outside=np.maximum(np.maximum(lower[None,:,:]-points[:,None,:],
                                  points[:,None,:]-upper[None,:,:]),0.)
    lower_squared=np.sum(outside*outside,axis=2)
    # Small outward rounding cushion retains boundary/tie candidates.
    cushion=1e-24+1e-12*upper_squared
    candidates=np.flatnonzero(np.any(lower_squared<=upper_squared+cushion,axis=0))
    distance,sample,triangle=nearest_triangle_distance(points,nodes,triangles[candidates])
    return distance,sample,int(candidates[triangle])


def first_rigid_proximity(center,orientation,local_points,velocity,angular_velocity,
                          nodes,node_velocities,triangles,duration,
                          distance_tolerance=1e-8,max_iterations=4096,use_bounds=True):
    center=np.asarray(center,dtype=float);R=np.asarray(orientation,dtype=float)
    local=np.asarray(local_points,dtype=float);v=np.asarray(velocity,dtype=float)
    omega=np.asarray(angular_velocity,dtype=float);nodes=np.asarray(nodes,dtype=float)
    nv=np.asarray(node_velocities,dtype=float);tri=np.asarray(triangles)
    if center.shape!=(3,) or R.shape!=(3,3) or v.shape!=(3,) or omega.shape!=(3,) or local.ndim!=2 or local.shape[1]!=3 or not len(local) or nodes.ndim!=2 or nodes.shape[1]!=3 or nv.shape!=nodes.shape or tri.ndim!=2 or tri.shape[1]!=3 or not len(tri):
        raise ValueError('Invalid rotational sweep shapes')
    if not all(np.isfinite(x).all() for x in (center,R,local,v,omega,nodes,nv,[duration,distance_tolerance])) or duration<0 or distance_tolerance<=0 or not isinstance(max_iterations,int) or max_iterations<1:
        raise ValueError('Invalid rotational sweep values')
    if not np.issubdtype(tri.dtype,np.integer) or np.any(tri<0) or np.any(tri>=len(nodes)) or not np.allclose(R.T@R,np.eye(3),atol=1e-9,rtol=0) or np.linalg.det(R)<0:
        raise ValueError('Invalid triangles or orientation')
    # Lipschitz bound: each point speed <= |v|+|omega|r; every triangle
    # material point moves no faster than its fastest vertex.
    speed=float(np.linalg.norm(v)+np.linalg.norm(omega)*np.linalg.norm(local,axis=1).max()+np.linalg.norm(nv,axis=1).max())
    time=0.
    for iteration in range(max_iterations):
        rotation=rotation_increment(omega*time)@R
        points=local@rotation.T+center+v*time
        distance_query=nearest_triangle_distance_bounded if use_bounds else nearest_triangle_distance
        distance,sample,triangle=distance_query(points,nodes+nv*time,tri)
        result=dict(time_s=time,distance_m=distance,sample_index=sample,triangle_index=triangle,iterations=iteration+1)
        if distance<=distance_tolerance:return dict(result,status='proximity')
        remaining=duration-time
        if speed==0 or distance-distance_tolerance>speed*remaining:
            return dict(result,status='clear')
        advance=min(remaining,.9*distance/speed)
        if advance<=np.finfo(float).eps*max(1.,time):return dict(result,status='unresolved')
        time+=advance
    return dict(result,status='unresolved')
