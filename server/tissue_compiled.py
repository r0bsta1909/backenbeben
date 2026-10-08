"""Optional experimental JIT material kernel. Install requirements-lab.txt."""
import math
import numpy as np
from numba import njit
from tissue_reference import ReferenceTissue

@njit(cache=True)
def cross(a,b):
    return np.array([a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]])

@njit(cache=True)
def material(p,w,ei,ej,el,ti,tv,edge_order,volume_order,le,lv,alpha,av):
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

class CompiledTissue(ReferenceTissue):
    def prepare(self):
        super().prepare()
        self.edge_order=np.concatenate(self.edge_batches)
        self.volume_order=np.concatenate(self.volume_batches)
    def solve_material(self,le,lv,alpha,av):
        material(self.p,self.w,self.ei,self.ej,self.el,self.ti,self.tv,self.edge_order,self.volume_order,le,lv,alpha,av)
