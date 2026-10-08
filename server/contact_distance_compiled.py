"""Optional JIT closest-point query; no fast-math or parallel reductions."""
import numpy as np
from numba import njit

@njit(cache=True)
def nearest_triangle_distance_compiled(points,nodes,triangles):
    best=np.inf;best_sample=-1;best_triangle=-1
    for i in range(len(points)):
        point=points[i]
        for j in range(len(triangles)):
            a=nodes[triangles[j,0]];b=nodes[triangles[j,1]];c=nodes[triangles[j,2]]
            lower=0.
            for axis in range(3):
                lo=min(a[axis],b[axis],c[axis]);hi=max(a[axis],b[axis],c[axis])
                outside=max(lo-point[axis],point[axis]-hi,0.)
                lower+=outside*outside
            if lower>best+1e-24+1e-12*best:continue
            e=b-a;f=c-a;d=point-a
            ee=np.sum(e*e);ff=np.sum(f*f);ef=np.sum(e*f)
            de=np.sum(d*e);df=np.sum(d*f);det=ee*ff-ef*ef
            distance=np.inf
            if det>1e-28:
                u=(de*ff-df*ef)/det;v=(df*ee-de*ef)/det
                if u>=0 and v>=0 and u+v<=1:
                    delta=point-(a+u*e+v*f);distance=np.sum(delta*delta)
            for edge_index in range(3):
                start=nodes[triangles[j,edge_index]]
                edge=nodes[triangles[j,(edge_index+1)%3]]-start
                length=np.sum(edge*edge)
                t=min(1.,max(0.,np.sum((point-start)*edge)/max(length,1e-30)))
                delta=point-(start+t*edge)
                distance=min(distance,np.sum(delta*delta))
            if distance<best:
                best=distance;best_sample=i;best_triangle=j
    return np.sqrt(best),best_sample,best_triangle
