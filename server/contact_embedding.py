"""Geometric side-ray embedding into the experimental front tissue cage.
No nearest-node fallback: missing coverage is explicit. Coordinates in metres.
"""
import numpy as np

def front_triangles(nx,ny):
    triangles=[]
    for y in range(ny-1):
        for x in range(nx-1):
            a=y*nx+x;b=a+1;c=a+nx;d=c+1
            triangles.extend([(a,b,c),(b,d,c)])
    return np.asarray(triangles,dtype=int)

def embed_side(point,nodes,triangles):
    """Cast along -X; return triangle indices, barycentrics and surface point."""
    point=np.asarray(point,dtype=float);nodes=np.asarray(nodes,dtype=float)
    best=None
    for indices in triangles:
        triangle=nodes[indices];a,b,c=triangle
        matrix=np.column_stack((b[1:]-a[1:],c[1:]-a[1:]))
        if abs(np.linalg.det(matrix))<1e-14:continue
        u,v=np.linalg.solve(matrix,point[1:]-a[1:]);weights=np.array([1-u-v,u,v])
        if np.min(weights)<-1e-9:continue
        weights=np.maximum(weights,0);weights/=weights.sum()
        position=weights@triangle
        if best is None or position[0]>best['position'][0]:
            best={'indices':np.array(indices),'weights':weights,'position':position}
    return best

def dense_weights(embedding,count):
    result=np.zeros(count);result[embedding['indices']]=embedding['weights'];return result


def embed_side_many(points,nodes,triangles):
    """Vectorized side projections, including deformed Y/Z and surface normals."""
    points=np.asarray(points,dtype=float);nodes=np.asarray(nodes,dtype=float)
    q=nodes[triangles];a=q[:,0];b=q[:,1]-a;c=q[:,2]-a
    determinant=b[:,1]*c[:,2]-c[:,1]*b[:,2]
    usable=np.abs(determinant)>1e-14
    safe=np.where(usable,determinant,1.)
    dy=points[:,None,1]-a[None,:,1];dz=points[:,None,2]-a[None,:,2]
    u=(dy*c[None,:,2]-dz*c[None,:,1])/safe
    v=(b[None,:,1]*dz-b[None,:,2]*dy)/safe
    weights=np.stack((1-u-v,u,v),axis=2)
    covered=usable[None,:] & np.all(weights>=-1e-9,axis=2)
    weights=np.maximum(weights,0);weights/=weights.sum(axis=2,keepdims=True)
    x=np.sum(weights*q[None,:,:,0],axis=2)
    best=np.argmax(np.where(covered,x,-np.inf),axis=1)
    normals=np.cross(b,c);normals*=np.where(normals[:,0]<0,-1.,1.)[:,None]
    normals/=np.maximum(np.linalg.norm(normals,axis=1,keepdims=True),1e-15)
    result=[]
    for i,j in enumerate(best):
        result.append({'indices':triangles[j].copy(),'weights':weights[i,j].copy(),
                       'position':weights[i,j]@q[j],'normal':normals[j].copy()} if covered[i,j] else None)
    return result
