"""Metre-scale, fixed-step driven arm used by the host and asset laboratory.

Three joint coordinates: shoulder yaw/elevation and elbow flexion. Motors have
bounded torque, explicit inertia and damping. IK supplies targets only. The final
pose belongs to this solver; no stretching or client hit verdict is permitted.
"""
import json, math
from pathlib import Path
META=json.loads((Path(__file__).resolve().parents[1]/'game/assets/character_v3.json').read_text())
L1=META['arms']['R']['upper_length']; L2=META['arms']['R']['forearm_length']
SHOULDER=(.235,-.16,.525)
DT=1/240
LIMITS=((-1.65,1.65),(-1.1,1.3),(.09,2.55))
INERTIA=(.14,.16,.045); MAX_TORQUE=(38.,42.,20.)

def add(a,b):return tuple(x+y for x,y in zip(a,b))
def sub(a,b):return tuple(x-y for x,y in zip(a,b))
def mul(a,s):return tuple(x*s for x in a)
def dot(a,b):return sum(x*y for x,y in zip(a,b))
def norm(a):return math.sqrt(dot(a,a))
def unit(a):return mul(a,1/max(1e-9,norm(a)))
def clamp(x,a,b):return max(a,min(b,x))

def target_angles(target):
    d=sub(target,SHOULDER);r=clamp(norm(d),abs(L1-L2)+.02,L1+L2-.004)
    yaw=math.atan2(d[0],-d[2]); elevation=math.atan2(d[1],math.hypot(d[0],d[2]))
    flex=math.acos(clamp((r*r-L1*L1-L2*L2)/(2*L1*L2),-1,1))
    shoulder=elevation-math.atan2(L2*math.sin(flex),L1+L2*math.cos(flex))
    return [clamp(v,*limit) for v,limit in zip((yaw,shoulder,flex),LIMITS)]

def forward(q):
    yaw,el,flex=q
    def vector(a,length):return (math.sin(yaw)*math.cos(a)*length,math.sin(a)*length,-math.cos(yaw)*math.cos(a)*length)
    elbow=add(SHOULDER,vector(el,L1));wrist=add(elbow,vector(el+flex,L2))
    # Fixed outward pole: move the elbow out beside the ribcage, not through the
    # table. Rotation about shoulder->wrist preserves both segment lengths.
    axis=unit(sub(wrist,SHOULDER));v=sub(elbow,SHOULDER);angle=-math.radians(68)
    cross=(axis[1]*v[2]-axis[2]*v[1],axis[2]*v[0]-axis[0]*v[2],axis[0]*v[1]-axis[1]*v[0])
    elbow=add(SHOULDER,add(add(mul(v,math.cos(angle)),mul(cross,math.sin(angle))),mul(axis,dot(axis,v)*(1-math.cos(angle)))))
    return elbow,wrist

class Arm:
    def __init__(self,target=(.27,-.04,.27)):
        self.q=target_angles(target);self.velocity=[0.,0.,0.];self.blocked=False;self.peak_torque=0.
    def step(self,target,collides=None):
        desired=target_angles(target);old=self.q[:];self.blocked=False
        for i in range(3):
            torque=clamp(95*(desired[i]-self.q[i])-7*self.velocity[i],-MAX_TORQUE[i],MAX_TORQUE[i])
            self.peak_torque=max(self.peak_torque,abs(torque))
            self.velocity[i]=clamp(self.velocity[i]+torque/INERTIA[i]*DT,-11,11)
            self.q[i]=clamp(self.q[i]+self.velocity[i]*DT,*LIMITS[i])
            if self.q[i] in LIMITS[i]:self.velocity[i]=0.
        if collides and collides(*forward(self.q)):
            # Conservative bisection in joint space; all intermediate poses keep
            # bone lengths. Remove inward kinetic energy instead of accumulating it.
            proposed=self.q[:];lo=0.;hi=1.
            for _ in range(12):
                t=(lo+hi)/2;candidate=[a+(b-a)*t for a,b in zip(old,proposed)]
                if collides(*forward(candidate)):hi=t
                else:lo=t
            self.q=[a+(b-a)*lo for a,b in zip(old,proposed)];self.velocity=[0.,0.,0.];self.blocked=True
        return self.pose()
    def pose(self):
        elbow,wrist=forward(self.q)
        return {'root':[0,0,.525],'shoulder':list(SHOULDER),'elbow':list(elbow),'wrist':list(wrist),'angles':self.q[:],'blocked':self.blocked}

def lab_collision(elbow,wrist):
    # Conservative rigid head and table proxies, with a 25 mm hand thickness.
    palm=add(wrist,(0,.054,0))
    head=(palm[0]/.145)**2+((palm[1]-.06)/.205)**2+((palm[2]-.015)/.135)**2<1
    table=palm[1]<-.242 and abs(palm[0])<.30 and .06<palm[2]<.30
    forearm_table=any((p[1]<-.244 and abs(p[0])<.30 and .06<p[2]<.30) for p in [elbow,add(elbow,mul(sub(wrist,elbow),.5)),wrist])
    return head or table or forearm_table

def laboratory():
    cases={'ready':(.27,-.04,.27),'windup':(.40,.01,.39),'half_reach':(.12,-.015,.23),'contact':(-.05,-.02,.15),'return':(.27,-.04,.27),'unreachable':(-2,2,-2),'table':(.02,-.5,.17),'behind_head':(0,.04,-.2)}
    clips={};report={}
    for name,target in cases.items():
        arm=Arm();frames=[];max_length_error=0.;blocked=0
        for step in range(720):
            pose=arm.step(target,lab_collision);blocked+=pose['blocked']
            max_length_error=max(max_length_error,abs(math.dist(pose['shoulder'],pose['elbow'])-L1),abs(math.dist(pose['elbow'],pose['wrist'])-L2))
            if step%4==0:frames.append(pose)
        clips[name]=frames
        report[name]={'max_length_error_m':max_length_error,'collision_steps':blocked,'max_torque_Nm':arm.peak_torque,'terminal_speed_rad_s':max(map(abs,arm.velocity)),'finite':all(math.isfinite(x) for x in arm.q)}
    return {'fps':60,'units':'metres','cases':clips,'report':report}

if __name__=='__main__':
    result=laboratory();path=Path(__file__).resolve().parents[1]/'game/assets/arm_lab_clips.json'
    path.write_text(json.dumps(result,separators=(',',':')),encoding='utf-8')
    print(json.dumps(result['report'],indent=2))
