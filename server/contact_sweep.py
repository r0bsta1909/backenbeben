"""Reference CCD for linearly moving point samples and triangle vertices.

Not a rigid rotational sweep: callers must not replace curved motion by one
chord without an error bound. Side-cage normals use the existing positive-X
convention. Coplanar candidate trajectories are explicitly unsupported.
"""
import numpy as np


def first_linear_contact(points_start,points_end,nodes_start,nodes_end,triangles):
    p0=np.asarray(points_start,dtype=float);p1=np.asarray(points_end,dtype=float)
    n0=np.asarray(nodes_start,dtype=float);n1=np.asarray(nodes_end,dtype=float)
    ids=np.asarray(triangles)
    if p0.ndim!=2 or p0.shape[1]!=3 or p1.shape!=p0.shape or n0.ndim!=2 or n0.shape[1]!=3 or n1.shape!=n0.shape or ids.ndim!=2 or ids.shape[1]!=3:
        raise ValueError('Invalid linear sweep shapes')
    if not all(np.isfinite(v).all() for v in (p0,p1,n0,n1)) or not np.issubdtype(ids.dtype,np.integer) or np.any(ids<0) or np.any(ids>=len(n0)):
        raise ValueError('Invalid linear sweep data')
    t0=n0[ids];t1=n1[ids];lower=np.minimum(t0,t1).min(axis=1);upper=np.maximum(t0,t1).max(axis=1)
    best=None
    for sample,(start,end) in enumerate(zip(p0,p1)):
        candidates=np.flatnonzero(np.all(np.maximum(start,end)>=lower-1e-12,axis=1)&np.all(np.minimum(start,end)<=upper+1e-12,axis=1))
        for tri in candidates:
            base=t0[tri];delta=t1[tri]-base
            d=start-base[0];dd=end-start-delta[0]
            e=base[1]-base[0];de=delta[1]-delta[0]
            f=base[2]-base[0];df=delta[2]-delta[0]
            c0=np.cross(e,f);c1=np.cross(de,f)+np.cross(e,df);c2=np.cross(de,df)
            coefficients=np.array([d@c0,dd@c0+d@c1,dd@c1+d@c2,dd@c2])
            scale=np.max(np.abs(coefficients))
            if scale<1e-24:
                raise ValueError('Coplanar or degenerate sweep candidate requires separate handling')
            coefficients=np.polynomial.polynomial.polytrim(coefficients,tol=scale*1e-13)
            for root in np.polynomial.polynomial.polyroots(coefficients):
                if abs(root.imag)>1e-9:continue
                time=float(root.real)
                if time < -1e-10 or time>1+1e-10:continue
                time=float(np.clip(time,0,1))
                if best is not None and time>=best['fraction']:continue
                triangle=base+time*delta;point=start+time*(end-start)
                edge1=triangle[1]-triangle[0];edge2=triangle[2]-triangle[0]
                normal=np.cross(edge1,edge2);length=np.linalg.norm(normal)
                if length<1e-14:continue
                uv=np.linalg.lstsq(np.column_stack((edge1,edge2)),point-triangle[0],rcond=None)[0]
                weights=np.array([1-uv.sum(),*uv])
                if weights.min() < -1e-9:continue
                normal/=length
                if normal[0]<0:normal=-normal
                relative=(end-start)-weights@delta
                if relative@normal>=-1e-12:continue
                weights=np.maximum(weights,0);weights/=weights.sum()
                best=dict(fraction=time,sample_index=sample,triangle_index=int(tri),
                          indices=ids[tri].copy(),weights=weights,normal=normal,
                          position=point)
    return best
