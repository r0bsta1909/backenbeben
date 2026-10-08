"""Experimental six-axis compliant hand/wrist attachment in joint coordinates.
Uses the current arm's diagonal joint inertias; not a full articulated mass matrix.
"""
import numpy as np
from arm import INERTIA,LIMITS,L1,L2,SHOULDER
from contact_constraint import rotation_increment

def rotation_log(rotation):
    vector=np.array([rotation[2,1]-rotation[1,2],rotation[0,2]-rotation[2,0],rotation[1,0]-rotation[0,1]])*.5
    sine=float(np.linalg.norm(vector));cosine=float(np.clip((np.trace(rotation)-1)*.5,-1,1))
    angle=np.arctan2(sine,cosine)
    if sine>1e-8:return vector*(angle/sine)
    if cosine>0:return vector
    values,vectors=np.linalg.eigh((rotation+rotation.T)*.5)
    axis=vectors[:,np.argmax(values)]
    if axis[np.argmax(np.abs(axis))]<0:axis=-axis
    return axis*angle

def forearm_frame(arm,q):
    elbow,wrist=map(np.asarray,arm.joints(q));axis=wrist-elbow;axis/=np.linalg.norm(axis)
    # The bent arm defines its own continuous plane. Switching a world helper
    # axis at a threshold would inject a discontinuous wrist rotation.
    shoulder=np.asarray(arm.rotate(SHOULDER,arm.torso_yaw))
    normal=np.cross(axis,elbow-shoulder);length=np.linalg.norm(normal)
    if length<1e-10:raise ValueError('Forearm frame requires a bent arm')
    normal/=length
    return np.column_stack((np.cross(axis,normal),axis,normal))

class ArmHandAttachment:
    def __init__(self,hand,arm,position_compliance=2e-5,angle_compliance=2e-3):
        if min(position_compliance,angle_compliance)<0:raise ValueError('Negative compliance')
        self.hand=hand;self.arm=arm
        self.local_wrist=hand.rotation.T@(np.asarray(arm.joints(arm.q)[1])-hand.center)
        self.relative_rotation=forearm_frame(arm,arm.q).T@hand.rotation
        self.compliance=np.array([position_compliance]*3+[angle_compliance]*3)
        self.multiplier=np.zeros(6)
    def begin_step(self):self.multiplier[:]=0
    def error(self,center=None,rotation=None,q=None):
        center=self.hand.center if center is None else center
        rotation=self.hand.rotation if rotation is None else rotation
        q=self.arm.q if q is None else q
        wrist=np.asarray(self.arm.joints(q)[1]);target=forearm_frame(self.arm,q)@self.relative_rotation
        return np.r_[center+rotation@self.local_wrist-wrist,rotation_log(rotation@target.T)]
    def jacobian_numeric(self):
        # Numerical reference, deliberately kept simple for later kernel comparison.
        result=np.zeros((6,9));result[:3,:3]=np.eye(3);eps=1e-6
        for i in range(3):
            delta=np.eye(3)[i]*eps
            result[:,i+3]=(self.error(rotation=rotation_increment(delta)@self.hand.rotation)-self.error(rotation=rotation_increment(-delta)@self.hand.rotation))/(2*eps)
            q=np.asarray(self.arm.q)
            result[:,i+6]=(self.error(q=q+delta)-self.error(q=q-delta))/(2*eps)
        return result
    def jacobian(self):
        """Exact position/SO(3) derivatives; forearm-frame derivative stays numerical."""
        hand=self.hand;arm=self.arm;q=np.asarray(arm.q)
        phi=self.error()[3:];theta=float(np.linalg.norm(phi))
        if theta>np.pi-.01:return self.jacobian_numeric()
        def skew(v):
            x,y,z=v;return np.array([[0.,-z,y],[z,0.,-x],[-y,x,0.]])
        k=skew(phi)
        coefficient=(1/12+theta*theta/720) if theta<1e-4 else (1-.5*theta/np.tan(.5*theta))/(theta*theta)
        left_inverse=np.eye(3)-.5*k+coefficient*(k@k)
        right_inverse=np.eye(3)+.5*k+coefficient*(k@k)
        result=np.zeros((6,9));result[:3,:3]=np.eye(3)
        result[:3,3:6]=-skew(hand.rotation@self.local_wrist)
        result[3:,3:6]=left_inverse
        yaw,elevation,flex=q
        sy,cy=np.sin(yaw),np.cos(yaw)
        radius=L1*np.cos(elevation)+L2*np.cos(elevation+flex)
        height=L1*np.sin(elevation)+L2*np.sin(elevation+flex)
        distal_sine=L2*np.sin(elevation+flex);distal_cosine=L2*np.cos(elevation+flex)
        wrist=np.array([[cy*radius,-sy*height,-sy*distal_sine],
                        [0.,radius,distal_cosine],
                        [sy*radius,cy*height,cy*distal_sine]])
        c,s=np.cos(arm.torso_yaw),np.sin(arm.torso_yaw)
        result[:3,6:]=-np.array([[c,0,s],[0,1,0],[-s,0,c]])@wrist
        frame=forearm_frame(arm,q);eps=1e-6
        for i in range(3):
            delta=np.eye(3)[i]*eps
            derivative=(forearm_frame(arm,q+delta)-forearm_frame(arm,q-delta))/(2*eps)
            angular=derivative@frame.T
            omega=np.array([angular[2,1]-angular[1,2],angular[0,2]-angular[2,0],angular[1,0]-angular[0,1]])*.5
            result[3:,i+6]=-right_inverse@omega
        return result

    def project(self,dt):
        if not np.isfinite(dt) or dt<=0:raise ValueError('Positive finite timestep required')
        hand=self.hand;arm=self.arm;jacobian=self.jacobian()
        mass=np.zeros((9,9));mass[:3,:3]=np.eye(3)*hand.inverse_mass
        mass[3:6,3:6]=hand.rotation@hand.inverse_inertia@hand.rotation.T
        mass[6:,6:]=np.diag(1/np.asarray(INERTIA))
        alpha=self.compliance/(dt*dt)
        delta=np.linalg.solve(jacobian@mass@jacobian.T+np.diag(alpha),-self.error()-alpha*self.multiplier)
        correction=mass@jacobian.T@delta;self.multiplier+=delta
        hand.center+=correction[:3];hand.rotation=rotation_increment(correction[3:6])@hand.rotation
        arm.q=[float(np.clip(v,*limit)) for v,limit in zip(np.asarray(arm.q)+correction[6:],LIMITS)]
    def residual(self,dt):
        value=self.error()+self.compliance/(dt*dt)*self.multiplier
        return max(float(np.max(np.abs(value[:3]))),float(np.max(np.abs(value[3:])))*.1)
