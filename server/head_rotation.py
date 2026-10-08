"""Three-axis head attachment math; not yet selected by the game solver.
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
            rotation,derivatives=rotation_and_derivatives(angles)
            target=position[axis]+np.sum(rotation[axis]*rest[index])
            gradient=np.empty(3)
            for j in range(3):gradient[j]=-np.sum(derivatives[j,axis]*rest[index])
            denominator=weights[index]+inverse_mass+np.sum(inverse_inertias*gradient*gradient)
            delta=-(points[index,axis]-target)/denominator
            points[index,axis]+=weights[index]*delta
            position[axis]-=inverse_mass*delta
            angles+=inverse_inertias*gradient*delta
    return angles
