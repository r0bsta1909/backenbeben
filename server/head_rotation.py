"""Three-axis head attachment math used by the spatial game solver.
Angles are pitch (+X), shader yaw (-Y), roll (+Z), applied in that order.
"""
import numpy as np
from numba import njit

@njit(cache=True)
def mm(a,b):
    result=np.zeros((3,3))
    for i in range(3):
        for j in range(3):
            for k in range(3):result[i,j]+=a[i,k]*b[k,j]
    return result

@njit(cache=True)
def rotation_and_derivatives(angles):
    x,y,z=angles
    cx,sx=np.cos(x),np.sin(x);cy,sy=np.cos(y),np.sin(y);cz,sz=np.cos(z),np.sin(z)
    rx=np.array([[1.,0.,0.],[0.,cx,-sx],[0.,sx,cx]])
    ry=np.array([[cy,0.,-sy],[0.,1.,0.],[sy,0.,cy]])
    rz=np.array([[cz,-sz,0.],[sz,cz,0.],[0.,0.,1.]])
    dx=np.array([[0.,0.,0.],[0.,-sx,-cx],[0.,cx,-sx]])
    dy=np.array([[-sy,0.,-cy],[0.,0.,0.],[cy,0.,-sy]])
    dz=np.array([[-sz,-cz,0.],[cz,-sz,0.],[0.,0.,0.]])
    return mm(mm(rz,ry),rx),np.stack((mm(mm(rz,ry),dx),mm(mm(rz,dy),rx),mm(mm(dz,ry),rx)))

@njit(cache=True)
def project_spatial_pins(points,weights,rest,ids,angles,inverse_inertias,position,inverse_mass):
    for index in ids:
        for axis in range(3):
            cx,sx=np.cos(angles[0]),np.sin(angles[0]);cy,sy=np.cos(angles[1]),np.sin(angles[1]);cz,sz=np.cos(angles[2]),np.sin(angles[2])
            x,y,z=rest[index];u=cx*y-sx*z;v=sx*y+cx*z
            xx=cy*x-sy*v;zz=sy*x+cy*v
            tx=cz*xx-sz*u;ty=sz*xx+cz*u
            if axis==0:
                target=tx;gx=cz*sy*u-sz*v;gy=cz*zz;gz=ty
            elif axis==1:
                target=ty;gx=sz*sy*u+cz*v;gy=sz*zz;gz=-tx
            else:
                target=zz;gx=-cy*u;gy=-xx;gz=0.
            denominator=weights[index]+inverse_mass+inverse_inertias[0]*gx*gx+inverse_inertias[1]*gy*gy+inverse_inertias[2]*gz*gz
            delta=-(points[index,axis]-target-position[axis])/denominator
            points[index,axis]+=weights[index]*delta
            position[axis]-=inverse_mass*delta
            angles[0]+=inverse_inertias[0]*gx*delta
            angles[1]+=inverse_inertias[1]*gy*delta
            angles[2]+=inverse_inertias[2]*gz*delta
    return angles


from head_attachment import HeadAttachment

class SpatialHeadAttachment(HeadAttachment):
    """Prototype generalized-coordinate neck; diagonal Euler inertias are tuned."""
    def __init__(self,cage,braced=False,translation=True):
        super().__init__(cage,braced,translation)
        self.angles=np.zeros(3);self.angular_velocity=np.zeros(3);self.old_angles=np.zeros(3)
        self.inverse_inertias=np.array([1/.022,self.inverse_inertia,1/.022])
        self.angular_stiffness=np.array([2.2,self.stiffness,2.2])
        if braced:self.angular_stiffness[[0,2]]*=1.5
        self.angular_multipliers=np.zeros(3)
    def begin_step(self,dt):
        self.old_angles=self.angles.copy();self.angular_multipliers[:]=0.
        super().begin_step(dt)
        self.angular_velocity*=np.exp(-.216*self.inverse_inertias*dt)
        self.angles+=self.angular_velocity*dt
        self.angle=float(self.angles[1])
    def project(self,dt):
        project_spatial_pins(self.cage.p,self.cage.w,self.cage.rest,self.ids,self.angles,self.inverse_inertias,self.position,self.inverse_mass)
        if self.inverse_mass:
            alpha=1/(self.linear_stiffness*dt*dt)
            delta=(-self.position-alpha*self.linear_multiplier)/(self.inverse_mass+alpha)
            self.linear_multiplier+=delta;self.position+=self.inverse_mass*delta
        alpha=1/(self.angular_stiffness*dt*dt)
        delta=(-self.angles-alpha*self.angular_multipliers)/(self.inverse_inertias+alpha)
        self.angular_multipliers+=delta;self.angles+=self.inverse_inertias*delta
        self.angle=float(self.angles[1])
    def finish_step(self,dt):
        super().finish_step(dt)
        self.angular_velocity=(self.angles-self.old_angles)/dt
        self.velocity=float(self.angular_velocity[1])
    def residual(self):
        rotation=rotation_and_derivatives(self.angles)[0]
        target=self.cage.rest[self.ids]@rotation.T+self.position
        return float(np.max(np.linalg.norm(self.cage.p[self.ids]-target,axis=1)))
    def energy(self):
        linear=(.5*np.sum(self.linear_velocity**2)/self.inverse_mass+.5*np.sum(self.linear_stiffness*self.position**2)) if self.inverse_mass else 0.
        return linear+.5*np.sum(self.angular_velocity**2/self.inverse_inertias)+.5*np.sum(self.angular_stiffness*self.angles**2)
