"""Experimental colored Gauss-Seidel XPBD reference; not active in matches."""
import math
import numpy as np
from tissue import Tissue

def independent_batches(indices):
    batches=[];occupied=[]
    for index,nodes in enumerate(indices):
        used=set(map(int,nodes))
        for batch,seen in zip(batches,occupied):
            if not used.intersection(seen):
                batch.append(index);seen.update(used);break
        else:batches.append([index]);occupied.append(used)
    return [np.array(batch,dtype=int) for batch in batches]

class ReferenceTissue(Tissue):
    def prepare(self):
        super().prepare()
        self.edge_batches=independent_batches(np.stack((self.ei,self.ej),axis=1))
        self.volume_batches=independent_batches(self.ti)
        self.iterations=12

    def step(self,dt,force=None,project_contact=None):
        if force is not None:raise ValueError('Reference lab uses contact, not artificial kicks')
        p=self.p;w=self.w;old=p.copy()
        self.v*=math.exp(-6*dt);p+=self.v*dt
        le=np.zeros(len(self.ei));lv=np.zeros(len(self.ti))
        alpha=self.edge_compliance/(dt*dt);av=self.volume_compliance/(dt*dt)
        for _ in range(self.iterations):
            for ids in self.edge_batches:
                i=self.ei[ids];j=self.ej[ids]
                diff=p[i]-p[j];dist=np.maximum(1e-12,np.linalg.norm(diff,axis=1))
                error=dist-self.el[ids];error=np.where(np.abs(error)<1e-14,0.,error)
                dl=(-error-alpha*le[ids])/(w[i]+w[j]+alpha);le[ids]+=dl
                correction=diff*(dl/dist)[:,None]
                p[i]+=correction*w[i,None];p[j]-=correction*w[j,None]
            for ids in self.volume_batches:
                indices=self.ti[ids];q=p[indices];a,b,c,d=[q[:,i] for i in range(4)]
                gb=np.cross(c-a,d-a)/6;gc=np.cross(d-a,b-a)/6;gd=np.cross(b-a,c-a)/6
                gradients=np.stack((-gb-gc-gd,gb,gc,gd),axis=1)
                volumes=np.sum((b-a)*np.cross(c-a,d-a),axis=1)/6
                error=volumes-self.tv[ids];error=np.where(np.abs(error)<1e-18,0.,error)
                denom=av+np.sum(w[indices]*np.sum(gradients*gradients,axis=2),axis=1)
                dl=(-error-av*lv[ids])/denom;lv[ids]+=dl
                p[indices]+=gradients*(dl[:,None]*w[indices])[:,:,None]
            if project_contact is not None:project_contact(self)
        self.v=(p-old)/dt
