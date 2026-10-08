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
