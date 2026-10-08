"""Optional experimental JIT material kernel. Install requirements-lab.txt."""
import math
import numpy as np
from numba import njit
from tissue_reference import ReferenceTissue

@njit(cache=True)
def cross(a,b):
    return np.array([a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]])

@njit(cache=True)
def material_array_reference(p,w,ei,ej,el,ti,tv,edge_order,volume_order,le,lv,alpha,av):
    for k in edge_order:
        i=ei[k];j=ej[k];diff=p[i]-p[j]
        length=max(1e-12,math.sqrt(np.sum(diff*diff)))
        error=length-el[k]
        if abs(error)<1e-14:error=0.
        dl=(-error-alpha*le[k])/(w[i]+w[j]+alpha);le[k]+=dl
        correction=diff*(dl/length)
        p[i]+=correction*w[i];p[j]-=correction*w[j]
    for k in volume_order:
        ids=ti[k];a=p[ids[0]].copy();b=p[ids[1]].copy();c=p[ids[2]].copy();d=p[ids[3]].copy()
        gb=cross(c-a,d-a)/6;gc=cross(d-a,b-a)/6;gd=cross(b-a,c-a)/6
        gradients=np.empty((4,3));gradients[0]=-gb-gc-gd;gradients[1]=gb;gradients[2]=gc;gradients[3]=gd
        error=np.sum((b-a)*gb)-tv[k]
        if abs(error)<1e-18:error=0.
        denom=av
        for j in range(4):denom+=w[ids[j]]*np.sum(gradients[j]*gradients[j])
        dl=(-error-av*lv[k])/denom;lv[k]+=dl
        for j in range(4):p[ids[j]]+=gradients[j]*dl*w[ids[j]]


@njit(cache=True)
def material(p,w,ei,ej,el,ti,tv,edge_order,volume_order,le,lv,alpha,av):
    """Same constraint order/formulas, with scratch storage reused per call."""
    diff=np.empty(3);directions=np.empty((3,3));gradients=np.empty((4,3))
    for k in edge_order:
        i=ei[k];j=ej[k];squared=0.
        for axis in range(3):
            diff[axis]=p[i,axis]-p[j,axis];squared+=diff[axis]*diff[axis]
        length=max(1e-12,math.sqrt(squared));error=length-el[k]
        if abs(error)<1e-14:error=0.
        dl=(-error-alpha*le[k])/(w[i]+w[j]+alpha);le[k]+=dl
        for axis in range(3):
            correction=diff[axis]*(dl/length)
            p[i,axis]+=correction*w[i];p[j,axis]-=correction*w[j]
    for k in volume_order:
        ids=ti[k]
        for vertex in range(3):
            for axis in range(3):directions[vertex,axis]=p[ids[vertex+1],axis]-p[ids[0],axis]
        for vertex in range(3):
            left=(vertex+1)%3;right=(vertex+2)%3
            for axis in range(3):
                a=(axis+1)%3;b=(axis+2)%3
                gradients[vertex+1,axis]=(directions[left,a]*directions[right,b]-directions[left,b]*directions[right,a])/6
        for axis in range(3):gradients[0,axis]=-gradients[1,axis]-gradients[2,axis]-gradients[3,axis]
        volume=0.
        for axis in range(3):volume+=directions[0,axis]*gradients[1,axis]
        error=volume-tv[k]
        if abs(error)<1e-18:error=0.
        denom=av
        for vertex in range(4):
            squared=0.
            for axis in range(3):squared+=gradients[vertex,axis]*gradients[vertex,axis]
            denom+=w[ids[vertex]]*squared
        dl=(-error-av*lv[k])/denom;lv[k]+=dl
        for vertex in range(4):
            for axis in range(3):p[ids[vertex],axis]+=gradients[vertex,axis]*dl*w[ids[vertex]]

@njit(cache=True)
def residuals(p,ei,ej,el,ti,tv,le,lv,alpha,av):
    """Full compliant residuals; same constraints and units as the reference."""
    edge_max=0.;volume_max=0.;equivalent_max=0.
    directions=np.empty((3,3));gradients=np.empty((4,3))
    for k in range(len(ei)):
        squared=0.
        for axis in range(3):
            delta=p[ei[k],axis]-p[ej[k],axis];squared+=delta*delta
        edge_max=max(edge_max,abs(math.sqrt(squared)-el[k]+alpha*le[k]))
    for k in range(len(ti)):
        ids=ti[k]
        for vertex in range(3):
            for axis in range(3):directions[vertex,axis]=p[ids[vertex+1],axis]-p[ids[0],axis]
        for vertex in range(3):
            left=(vertex+1)%3;right=(vertex+2)%3
            for axis in range(3):
                a=(axis+1)%3;b=(axis+2)%3
                gradients[vertex+1,axis]=(directions[left,a]*directions[right,b]-directions[left,b]*directions[right,a])/6
        for axis in range(3):gradients[0,axis]=-gradients[1,axis]-gradients[2,axis]-gradients[3,axis]
        volume=0.;squared=0.
        for axis in range(3):volume+=directions[0,axis]*gradients[1,axis]
        for vertex in range(4):
            for axis in range(3):squared+=gradients[vertex,axis]*gradients[vertex,axis]
        error=abs(volume-tv[k]+av*lv[k])
        volume_max=max(volume_max,error)
        equivalent_max=max(equivalent_max,error/max(math.sqrt(squared),1e-15))
    return edge_max,volume_max,equivalent_max

class CompiledTissue(ReferenceTissue):
    def prepare(self):
        super().prepare()
        self.edge_order=np.concatenate(self.edge_batches)
        self.volume_order=np.concatenate(self.volume_batches)
    def solve_material(self,le,lv,alpha,av):
        material(self.p,self.w,self.ei,self.ej,self.el,self.ti,self.tv,self.edge_order,self.volume_order,le,lv,alpha,av)
    def measure_residuals(self,le,lv,alpha,av):
        values=residuals(self.p,self.ei,self.ej,self.el,self.ti,self.tv,le,lv,alpha,av)
        return dict(zip(('edge_m','volume_m3','volume_equivalent_m'),values))
