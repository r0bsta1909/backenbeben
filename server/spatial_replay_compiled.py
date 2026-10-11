"""Same 30-step inverse of the rendered neck blend, without temporary arrays."""
import numpy as np
from numba import njit

@njit(cache=True)
def invert_spatial_offsets(points,rest,angles,position):
    result=np.empty(points.shape)
    for i in range(len(points)):
        local_y=points[i,1];xx=points[i,0];zz=points[i,2];y=local_y
        for _ in range(30):
            blend=min(1.,max(0.,(local_y*4+.55)/.43));blend=blend*blend*(3-2*blend)
            ax=angles[0]*blend;ay=angles[1]*blend;az=angles[2]*blend
            cx=np.cos(ax);sx=np.sin(ax);cy=np.cos(ay);sy=np.sin(ay);cz=np.cos(az);sz=np.sin(az)
            vx=points[i,0]-position[0]*blend;vy=points[i,1]-position[1]*blend;vz=points[i,2]-position[2]*blend
            x=cz*vx+sz*vy;y=-sz*vx+cz*vy
            xx=cy*x+sy*vz;zz=-sy*x+cy*vz
            local_y=cx*y+sx*zz
        result[i,0]=(xx-rest[i,0])*4
        result[i,1]=(local_y-rest[i,1])*4
        result[i,2]=(-sx*y+cx*zz-rest[i,2])*4
    return result.ravel()
