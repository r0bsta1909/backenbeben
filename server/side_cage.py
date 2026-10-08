"""Experimental SI tissue geometry sampled from the actual lateral face mesh."""
import numpy as np
from contact_v3 import side_surface
from contact_embedding import front_triangles

def build_side_cage(nx=17,ny=17,skin_state=(0.,0.,0.)):
    if nx<2 or ny<2:raise ValueError('Cage needs at least two rows/columns')
    zs=np.linspace(-.025,.100,nx);ys=np.linspace(-.110,.140,ny)
    front=[];valid=[]
    for y in ys:
        for z in zs:
            depth=side_surface(y*4,z*4,skin_state)
            valid.append(depth is not None)
            front.append([depth/4 if depth is not None else 0.,y,z])
    front=np.array(front);valid=np.array(valid);count=nx*ny
    deep=front.copy();deep[:,0]-=.020
    nodes=np.concatenate((front,deep))
    triangles=front_triangles(nx,ny)
    triangles=triangles[np.all(valid[triangles],axis=1)]
    tets=[]
    for y in range(ny-1):
        for x in range(nx-1):
            a=y*nx+x;b=a+1;c=a+nx;d=c+1
            if not all(valid[[a,b,c,d]]):continue
            tets.extend([(a,b,c,a+count),(b,d,c,d+count),(b,c,a+count,d+count),
                         (b,a+count,b+count,d+count),(c,a+count,d+count,c+count)])
    return {'nodes':nodes,'triangles':triangles,'tetrahedra':np.asarray(tets,dtype=int),
            'valid_front':valid,'nx':nx,'ny':ny,'y_bounds':[ys[0],ys[-1]],'z_bounds':[zs[0],zs[-1]]}


from tissue_reference import ReferenceTissue

class SideTissue(ReferenceTissue):
    """Experimental SI solver on the lateral cage, with volume-lumped masses.

    Density is a laboratory parameter, not an anatomical calibration. Deep
    nodes and the outer grid boundary are fixed; unused mesh samples have no
    mass and cannot receive contact. No legacy frontal depth clamp is used.
    """
    def __init__(self,nx=17,ny=17,skin_state=(0.,0.,0.),density=1000.):
        if not np.isfinite(density) or density<=0:raise ValueError('Positive finite density required')
        self.geometry=build_side_cage(nx,ny,skin_state)
        self.rest=self.geometry['nodes'].copy()
        self.p=self.rest.copy();self.v=np.zeros_like(self.p)
        indices=self.geometry['tetrahedra']
        q=self.rest[indices];a,b,c,d=[q[:,i] for i in range(4)]
        volumes=np.sum((b-a)*np.cross(c-a,d-a),axis=1)/6
        self.node_masses=np.zeros(len(self.rest))
        np.add.at(self.node_masses,indices.ravel(),np.repeat(np.abs(volumes)*density/4,4))
        count=nx*ny;ids=np.arange(len(self.rest))
        movable=(ids<count)&(ids%nx>0)&(ids%nx<nx-1)&(ids//nx>0)&(ids//nx<ny-1)&(self.node_masses>0)
        self.w=np.zeros(len(self.rest));self.w[movable]=1/self.node_masses[movable]
        self.tets=list(zip(map(tuple,indices),volumes))
        pairs=set()
        for tet in indices:
            for i in tet:
                for j in tet:
                    if i<j and (self.w[i] or self.w[j]):pairs.add((int(i),int(j)))
        self.edges=[(i,j,float(np.linalg.norm(self.rest[i]-self.rest[j]))) for i,j in sorted(pairs)]
        self.edge_compliance=6e-5;self.volume_compliance=1e-9
