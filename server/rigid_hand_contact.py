"""Experimental shared rigid-hand contact sheet; not active match physics."""
import numpy as np
from contact_embedding import embed_side_many
from contact_constraint import project_rigid_contact

class RigidHandContact:
    def __init__(self,points,areas,mass=.18,embedding=embed_side_many):
        self.embedding=embedding
        points=np.asarray(points,dtype=float);areas=np.asarray(areas,dtype=float)
        if len(points)<1 or points.shape!=(len(areas),3) or np.any(areas<=0) or mass<=0:raise ValueError('Invalid hand sheet')
        self.center=np.average(points,axis=0,weights=areas)
        self.local=points-self.center;self.rotation=np.eye(3)
        self.inverse_mass=1/mass
        # Laboratory box inertia only; articulated anatomical inertia is open.
        dimensions=np.array([.04,.19,.09])
        self.inverse_inertia=np.diag(12/(mass*(np.sum(dimensions**2)-dimensions**2)))
        self.multipliers=np.zeros(len(points));self.keys=[None]*len(points)
        self.last_contacts=0
    def begin_step(self):
        self.multipliers[:]=0;self.keys=[None]*len(self.local)
    def points(self):return self.local@self.rotation.T+self.center
    def project(self,cage,dt,skip_separated=True):
        embeddings=self.embedding(self.points(),cage.p,cage.geometry['triangles'])
        self.last_contacts=0
        for i,e in enumerate(embeddings):
            if e is None:self.multipliers[i]=0;self.keys[i]=None;continue
            key=tuple(e['indices'])
            if key!=self.keys[i]:self.multipliers[i]=0
            self.keys[i]=key
            ids=e['indices']
            if skip_separated and self.multipliers[i]==0:
                gap=float((self.center+self.rotation@self.local[i]-e['weights']@cage.p[ids])@e['normal'])
                # Exact zero correction for a separated, unloaded unilateral contact.
                # Re-evaluate after preceding contacts, not from stale embedding positions.
                if gap>=0:continue
            self.center,self.rotation,updated,self.multipliers[i]=project_rigid_contact(
                self.center,self.rotation,self.local[i],self.inverse_mass,self.inverse_inertia,
                cage.p[ids],cage.w[ids],e['weights'],e['normal'],dt,multiplier=self.multipliers[i])
            cage.p[ids]=updated
            self.last_contacts+=int(self.multipliers[i]>0)
    def penetration(self,cage):
        points=self.points();embeddings=self.embedding(points,cage.p,cage.geometry['triangles'])
        return max([max(0.,-float((p-e['position'])@e['normal'])) for p,e in zip(points,embeddings) if e is not None],default=0.)
