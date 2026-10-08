"""Join a solved contact interval to motor-driven, collision-checked recovery.

The contact path is preserved. Recovery begins with its final joint velocities
and hand orientation; this is not yet selected by the match host.
"""
import copy
import math
import numpy as np
from arm import Arm,DT
from arm_hand_attachment import rotation_log
from contact_constraint import rotation_increment
from contact_v3 import hand_frame,table_collision,side_surfaces,WRIST_LIMIT
from hand_surface import world_positions


def smooth(value):
    t=max(0.,min(1.,value))
    return t*t*t*(10-15*t+6*t*t)


def recover(scored,contact):
    if not contact.get('attached') or not contact.get('frames'):
        raise ValueError('An attached contact interval is required')
    impact=float(scored['contact_time'])
    path=copy.deepcopy([r for r in scored['arm_path'] if r['time']<=impact+1e-8])
    tilt=path[-1]['tilt']
    for frame in contact['frames']:
        path.append({'time':impact+frame['time'],'pose':copy.deepcopy(frame['arm']),'tilt':tilt})
    final=path[-1];pose=final['pose']
    arm=Arm();arm.q=pose['angles'][:];arm.torso_yaw=pose['torso_yaw']
    arm.velocity=list(contact['final_joint_velocity'])
    release=np.array(pose['wrist']);finger=np.array(pose['finger_direction']);normal=np.array(pose['palm_normal'])
    basis=np.column_stack((np.cross(finger,normal),finger,normal))
    omega=np.array(contact['final_angular_velocity'])
    skin_state=tuple(scored.get('skin_state',(0.,0.,0.)))
    for tick in range(1,325):
        elapsed=tick*DT
        arm.drive_torso(0.)
        blend=smooth(elapsed/.24);lower=smooth((elapsed-.22)/.55)
        target=release+(np.array([.40,-.07,.30])-release)*blend+np.array([-.06,-.60,.16])*lower
        # Continue the outgoing angular velocity, damping it before returning
        # to the controlled posture. The initial orientation is never reset.
        carried=rotation_increment(omega*.08*(1-math.exp(-elapsed/.08)))@basis
        def orientation_for(elbow,wrist):
            desired_f,desired_n=map(np.asarray,hand_frame(tilt,{'elbow':elbow,'wrist':wrist}))
            desired=np.column_stack((np.cross(desired_f,desired_n),desired_f,desired_n))
            rest_f=np.asarray(wrist)-elbow;rest_f/=np.linalg.norm(rest_f)
            rest_n=normal-rest_f*(normal@rest_f);rest_n/=np.linalg.norm(rest_n)
            rest=np.column_stack((np.cross(rest_f,rest_n),rest_f,rest_n))
            desired=rotation_increment(rotation_log(rest@desired.T)*lower)@desired
            orientation=rotation_increment(rotation_log(desired@carried.T)*smooth((elapsed-.16)/.30))@carried
            # Bound the carried angular motion against the CURRENT forearm.
            # Apply one rigid rotation to finger and palm axes; collision uses
            # this same constrained orientation before the pose is accepted.
            f=orientation[:,1]
            angle=math.acos(float(np.clip(f@rest_f,-1.,1.)))
            if angle>WRIST_LIMIT:
                axis=np.cross(f,rest_f);length=float(np.linalg.norm(axis))
                if length<1e-12:axis=orientation[:,2];length=1.
                orientation=rotation_increment(axis/length*(angle-WRIST_LIMIT))@orientation
            return orientation[:,1],orientation[:,2]
        def blocked(elbow,wrist):
            if table_collision(elbow,wrist):return True
            f,n=orientation_for(elbow,wrist)
            points=world_positions({'elbow':elbow,'wrist':wrist},f,n)*4
            depths=side_surfaces(points[:,1:],skin_state)
            return bool(np.any(np.isfinite(depths)&(points[:,0]<depths)))
        pose=arm.step(tuple(target),blocked)
        f,n=orientation_for(pose['elbow'],pose['wrist'])
        pose['finger_direction']=f.tolist();pose['palm_normal']=n.tolist()
        pose['finger_relax']=smooth((elapsed-.4)/.5) if pose['wrist'][0]>.30 else 0.
        path.append({'time':final['time']+elapsed,'pose':pose,'tilt':tilt})
    return path
