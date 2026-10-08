"""Optional exact-formula JIT side embedding; no fast-math or parallel reductions."""
import numpy as np
from numba import njit

@njit(cache=True)
def intersections(points,nodes,triangles):
    count=len(points);best=np.full(count,-1,np.int64)
    weights=np.zeros((count,3));positions=np.zeros((count,3));normals=np.zeros((count,3))
    for j in range(len(triangles)):
        ia,ib,ic=triangles[j]
        ax,ay,az=nodes[ia];bx=nodes[ib,0]-ax;by=nodes[ib,1]-ay;bz=nodes[ib,2]-az
        cx=nodes[ic,0]-ax;cy=nodes[ic,1]-ay;cz=nodes[ic,2]-az
        determinant=by*cz-cy*bz
        if abs(determinant)<=1e-14:continue
        nx=by*cz-bz*cy;ny=bz*cx-bx*cz;nz=bx*cy-by*cx
        if nx<0:nx=-nx;ny=-ny;nz=-nz
        length=max(np.sqrt(nx*nx+ny*ny+nz*nz),1e-15)
        nx/=length;ny/=length;nz/=length
        # Include the existing barycentric acceptance tolerance in the bounds.
        py=2e-9*(abs(by)+abs(cy))+1e-15;pz=2e-9*(abs(bz)+abs(cz))+1e-15
        ymin=min(0.,by,cy)-py;ymax=max(0.,by,cy)+py
        zmin=min(0.,bz,cz)-pz;zmax=max(0.,bz,cz)+pz
        for i in range(count):
            dy=points[i,1]-ay;dz=points[i,2]-az
            if dy<ymin or dy>ymax or dz<zmin or dz>zmax:continue
            u=(dy*cz-dz*cy)/determinant;v=(by*dz-bz*dy)/determinant
            w0=1-u-v
            if min(w0,u,v)<-1e-9:continue
            w0=max(w0,0.);u=max(u,0.);v=max(v,0.);total=w0+u+v
            w0/=total;u/=total;v/=total
            x=w0*ax+u*nodes[ib,0]+v*nodes[ic,0]
            if best[i]<0 or x>positions[i,0]:
                best[i]=j;weights[i,0]=w0;weights[i,1]=u;weights[i,2]=v
                positions[i,0]=x;positions[i,1]=w0*ay+u*nodes[ib,1]+v*nodes[ic,1]
                positions[i,2]=w0*az+u*nodes[ib,2]+v*nodes[ic,2]
                normals[i,0]=nx;normals[i,1]=ny;normals[i,2]=nz
    return best,weights,positions,normals

def embed_side_many(points,nodes,triangles):
    best,weights,positions,normals=intersections(np.asarray(points,dtype=float),np.asarray(nodes,dtype=float),np.asarray(triangles,dtype=np.int64))
    return [None if j<0 else {'indices':triangles[j].copy(),'weights':weights[i].copy(),'position':positions[i].copy(),'normal':normals[i].copy()} for i,j in enumerate(best)]
