"""Optional exact-formula JIT side embedding; no fast-math or parallel reductions."""
import numpy as np
from numba import njit

@njit(cache=True)
def intersections(points,nodes,triangles):
    count=len(points);best=np.full(count,-1,np.int64)
    weights=np.zeros((count,3));positions=np.zeros((count,3));normals=np.zeros((count,3))
    for j in range(len(triangles)):
        a=nodes[triangles[j,0]];b=nodes[triangles[j,1]]-a;c=nodes[triangles[j,2]]-a
        determinant=b[1]*c[2]-c[1]*b[2]
        if abs(determinant)<=1e-14:continue
        normal=np.array([b[1]*c[2]-b[2]*c[1],b[2]*c[0]-b[0]*c[2],b[0]*c[1]-b[1]*c[0]])
        if normal[0]<0:normal=-normal
        normal/=max(np.sqrt(np.sum(normal*normal)),1e-15)
        for i in range(count):
            dy=points[i,1]-a[1];dz=points[i,2]-a[2]
            u=(dy*c[2]-dz*c[1])/determinant;v=(b[1]*dz-b[2]*dy)/determinant
            w0=1-u-v
            if min(w0,u,v)<-1e-9:continue
            w0=max(w0,0.);u=max(u,0.);v=max(v,0.);total=w0+u+v
            w0/=total;u/=total;v/=total
            point=w0*nodes[triangles[j,0]]+u*nodes[triangles[j,1]]+v*nodes[triangles[j,2]]
            if best[i]<0 or point[0]>positions[i,0]:
                best[i]=j;weights[i,0]=w0;weights[i,1]=u;weights[i,2]=v
                positions[i]=point;normals[i]=normal
    return best,weights,positions,normals

def embed_side_many(points,nodes,triangles):
    best,weights,positions,normals=intersections(np.asarray(points,dtype=float),np.asarray(nodes,dtype=float),np.asarray(triangles,dtype=np.int64))
    return [None if j<0 else {'indices':triangles[j].copy(),'weights':weights[i].copy(),'position':positions[i].copy(),'normal':normals[i].copy()} for i,j in enumerate(best)]
