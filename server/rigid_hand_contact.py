"""Reference rigid-hand contact sheet for the optional coupled match backend."""
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
        self.step_contact_impulse=np.zeros(3);self.step_contact_moment=np.zeros(3);self.step_contact_switches=0
    def begin_step(self):
        self.multipliers[:]=0;self.keys=[None]*len(self.local)
        self.step_contact_impulse[:]=0;self.step_contact_moment[:]=0;self.step_contact_switches=0
    def points(self):return self.local@self.rotation.T+self.center
    def project(self,cage,dt,skip_separated=True):
        embeddings=self.embedding(self.points(),cage.p,cage.geometry['triangles'])
        self.last_contacts=0
        for i,e in enumerate(embeddings):
            if e is None:self.multipliers[i]=0;self.keys[i]=None;continue
            key=tuple(e['indices'])
            if key!=self.keys[i]:
                self.step_contact_switches+=int(self.keys[i] is not None)
                self.multipliers[i]=0
            self.keys[i]=key
            ids=e['indices']
            if skip_separated and self.multipliers[i]==0:
                gap=float((self.center+self.rotation@self.local[i]-e['weights']@cage.p[ids])@e['normal'])
                # Exact zero correction for a separated, unloaded unilateral contact.
                # Re-evaluate after preceding contacts, not from stale embedding positions.
                if gap>=0:continue
            surface=e["weights"]@cage.p[ids]
            previous_multiplier=float(self.multipliers[i])
            self.center,self.rotation,updated,self.multipliers[i]=project_rigid_contact(
                self.center,self.rotation,self.local[i],self.inverse_mass,self.inverse_inertia,
                cage.p[ids],cage.w[ids],e['weights'],e['normal'],dt,multiplier=self.multipliers[i])
            impulse=(self.multipliers[i]-previous_multiplier)*e["normal"]/dt
            self.step_contact_impulse+=impulse
            # Moment about world origin, at the common tissue contact point.
            self.step_contact_moment+=np.cross(surface,impulse)
            cage.p[ids]=updated
            self.last_contacts+=int(self.multipliers[i]>0)
    def penetration(self,cage):
        points=self.points();embeddings=self.embedding(points,cage.p,cage.geometry['triangles'])
        return max([max(0.,-float((p-e['position'])@e['normal'])) for p,e in zip(points,embeddings) if e is not None],default=0.)

    def resolve_velocity(self,cage,velocity,angular_velocity,contact_margin=1e-7,
                         tolerance=1e-10,max_iterations=2048):
        """Non-mutating velocity solve on current touching/penetrating samples.

        Compact shared tissue nodes before constructing the laboratory system.
        Caller handles positional penetration and time-of-impact separately.
        """
        from contact_velocity_system import resolve_contacts
        if not np.isfinite(contact_margin) or contact_margin<0:
            raise ValueError('Invalid contact margin')
        points=self.points()
        embeddings=self.embedding(points,cage.p,cage.geometry['triangles'])
        contacts=[]
        for i,e in enumerate(embeddings):
            if e is None:continue
            gap=float((points[i]-e['weights']@cage.p[e['indices']])@e['normal'])
            if gap<=contact_margin:contacts.append((i,e,gap))
        if not contacts:
            return dict(velocity=np.array(velocity,dtype=float),angular_velocity=np.array(angular_velocity,dtype=float),
                node_velocities=cage.v.copy(),impulses=np.zeros(0),sample_indices=[],
                residual_m_s=0.,converged=True,iterations=0,maximum_penetration_m=0.)
        ids=np.unique(np.concatenate([e['indices'] for _,e,_ in contacts]))
        mapping={int(node):j for j,node in enumerate(ids)}
        weights=np.zeros((len(contacts),len(ids)))
        for row,(_,e,_) in enumerate(contacts):
            for node,weight in zip(e['indices'],e['weights']):weights[row,mapping[int(node)]]+=weight
        samples=[i for i,_,_ in contacts]
        result=resolve_contacts(velocity,angular_velocity,self.rotation,self.local[samples],
            self.inverse_mass,self.inverse_inertia,cage.v[ids],cage.w[ids],weights,
            [e['normal'] for _,e,_ in contacts],tolerance,max_iterations)
        velocities=cage.v.copy();velocities[ids]=result['node_velocities']
        result.update(node_velocities=velocities,sample_indices=samples,
                      maximum_penetration_m=max(0.,max(-gap for _,_,gap in contacts)))
        return result
