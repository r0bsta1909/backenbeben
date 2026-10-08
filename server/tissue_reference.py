"""Experimental colored Gauss-Seidel XPBD reference; not active in matches."""
import math
import numpy as np
from tissue import Tissue

def cross3(a,b):
    """Specialized N x 3 cross product, avoiding generic axis dispatch."""
    result=np.empty_like(a)
    result[:,0]=a[:,1]*b[:,2]-a[:,2]*b[:,1]
    result[:,1]=a[:,2]*b[:,0]-a[:,0]*b[:,2]
    result[:,2]=a[:,0]*b[:,1]-a[:,1]*b[:,0]
    return result

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
        for iteration in range(self.iterations):
            for ids in self.edge_batches:
                i=self.ei[ids];j=self.ej[ids]
                diff=p[i]-p[j];dist=np.maximum(1e-12,np.linalg.norm(diff,axis=1))
                error=dist-self.el[ids];error=np.where(np.abs(error)<1e-14,0.,error)
                dl=(-error-alpha*le[ids])/(w[i]+w[j]+alpha);le[ids]+=dl
                correction=diff*(dl/dist)[:,None]
                p[i]+=correction*w[i,None];p[j]-=correction*w[j,None]
            for ids in self.volume_batches:
                indices=self.ti[ids];q=p[indices];a,b,c,d=[q[:,i] for i in range(4)]
                gb=cross3(c-a,d-a)/6;gc=cross3(d-a,b-a)/6;gd=cross3(b-a,c-a)/6
                gradients=np.stack((-gb-gc-gd,gb,gc,gd),axis=1)
                volumes=np.sum((b-a)*gb,axis=1)
                error=volumes-self.tv[ids];error=np.where(np.abs(error)<1e-18,0.,error)
                denom=av+np.sum(w[indices]*np.sum(gradients*gradients,axis=2),axis=1)
                dl=(-error-av*lv[ids])/denom;lv[ids]+=dl
                p[indices]+=gradients*(dl[:,None]*w[indices])[:,:,None]
            if project_contact is not None:project_contact(self)
            self.iterations_used=iteration+1
            tolerance=getattr(self,'residual_tolerance',None)
            if tolerance is not None and (iteration+1)%4==0:
                residuals=self.measure_residuals(le,lv,alpha,av)
                if max(residuals['edge_m'],residuals['volume_equivalent_m'])<=tolerance:break
        self.residuals=self.measure_residuals(le,lv,alpha,av)
        self.v=(p-old)/dt

    def measure_residuals(self,le,lv,alpha,av):
        p=self.p
        # Measure the actual compliant equation, not deformation alone.
        edge_residual=np.linalg.norm(p[self.ei]-p[self.ej],axis=1)-self.el+alpha*le
        q=p[self.ti];a,b,c,d=[q[:,i] for i in range(4)]
        gb=cross3(c-a,d-a)/6;gc=cross3(d-a,b-a)/6;gd=cross3(b-a,c-a)/6
        gradients=np.stack((-gb-gc-gd,gb,gc,gd),axis=1)
        volume_residual=np.sum((b-a)*gb,axis=1)-self.tv+av*lv
        gradient_norm=np.sqrt(np.sum(gradients*gradients,axis=(1,2)))
        return {'edge_m':float(np.max(np.abs(edge_residual))),
                        'volume_m3':float(np.max(np.abs(volume_residual))),
                        'volume_equivalent_m':float(np.max(np.abs(volume_residual)/np.maximum(gradient_norm,1e-15)))}
