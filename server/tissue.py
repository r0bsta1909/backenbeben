"""Host-only XPBD tissue cage. Fixed timestep, pinned deep tissue, volume constraints.
Recorded positions drive BOTH live presentation and replay. Browser FPS never
changes the solve. Pure Python keeps one authoritative implementation portable.
"""
import math,time
from contact import NX,NY,X0,Y0,DX,DY,surface

def sub(a,b):return [a[i]-b[i] for i in range(3)]

def dot(a,b):return sum(a[i]*b[i] for i in range(3))

def cross(a,b):return [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]

def volume(a,b,c,d):return dot(sub(b,a),cross(sub(c,a),sub(d,a)))/6

class Tissue:
    def __init__(self,surface_fn=surface):
        surface=surface_fn
        self.rest=[[X0+x*DX,Y0+y*DY,surface(X0+x*DX,Y0+y*DY)-layer*.095] for layer in range(2) for y in range(NY) for x in range(NX)]
        self.p=[v[:] for v in self.rest];self.v=[[0.,0.,0.] for _ in self.p]
        self.w=[0. if i>=NX*NY or i%NX in (0,NX-1) or i//NX in (0,NY-1) else 1. for i in range(len(self.p))]
        self.edges=[];self.tets=[]
        pairs=set();n=NX*NY
        for y in range(NY-1):
            for x in range(NX-1):
                a=y*NX+x;b=a+1;c=a+NX;d=c+1
                for tet in [(a,b,c,a+n),(b,d,c,d+n),(b,c,a+n,d+n),(b,a+n,b+n,d+n),(c,a+n,d+n,c+n)]:
                    self.tets.append((tet,volume(*(self.rest[i] for i in tet))))
                    for i in tet:
                        for j in tet:
                            if i<j and (self.w[i] or self.w[j]):pairs.add((i,j))
        for i,j in sorted(pairs):self.edges.append((i,j,math.sqrt(dot(sub(self.p[i],self.p[j]),sub(self.p[i],self.p[j])))))
    def prepare(self):
        import numpy as np
        self.np=np;self.rest=np.array(self.rest);self.p=self.rest.copy();self.v=np.zeros_like(self.p);self.w=np.array(self.w)
        self.ei=np.array([e[0] for e in self.edges]);self.ej=np.array([e[1] for e in self.edges]);self.el=np.array([e[2] for e in self.edges])
        self.ti=np.array([t[0] for t in self.tets]);self.tv=np.array([t[1] for t in self.tets])
        self.degree=np.maximum(1,np.bincount(np.r_[self.ei,self.ej],minlength=len(self.p)))[:,None]
    def step(self,dt,force=None):
        np=self.np;p=self.p;w=self.w;old=p.copy()
        if force:
            centre,impulse=force
            fall=np.exp(-np.sum((self.rest[:,:2]-centre[:2])**2,axis=1)/.025)*w
            self.v+=fall[:,None]*np.array(impulse)
        self.v*=math.exp(-6*dt)
        p+=self.v*dt
        le=np.zeros(len(self.ei));lv=np.zeros(len(self.ti))
        alpha=.00006/(dt*dt);av=.000000000003/(dt*dt)
        for iteration in range(4):
            diff=p[self.ei]-p[self.ej];dist=np.maximum(1e-9,np.linalg.norm(diff,axis=1))
            dl=(-(dist-self.el)-alpha*le)/(w[self.ei]+w[self.ej]+alpha);le+=dl
            corr=diff*(dl/dist)[:,None];delta=np.zeros_like(p)
            np.add.at(delta,self.ei,corr*w[self.ei,None]);np.add.at(delta,self.ej,-corr*w[self.ej,None])
            p+=delta/np.sqrt(self.degree)
            q=p[self.ti];a,b,c,d=[q[:,i] for i in range(4)]
            gb=np.cross(c-a,d-a)/6;gc=np.cross(d-a,b-a)/6;gd=np.cross(b-a,c-a)/6
            grads=np.stack((-gb-gc-gd,gb,gc,gd),axis=1)
            vols=np.sum((b-a)*np.cross(c-a,d-a),axis=1)/6
            denom=av+np.sum(w[self.ti]*np.sum(grads*grads,axis=2),axis=1)
            dl=(-(vols-self.tv)-av*lv)/denom;lv+=dl
            delta[:]=0
            np.add.at(delta,self.ti.ravel(),(grads*(dl[:,None]*w[self.ti])[:,:,None]).reshape(-1,3))
            p+=delta/np.sqrt(self.degree)
            p[:,2]=np.maximum(self.rest[:,2]-.065,p[:,2])
            p[w==0]=self.rest[w==0]
        self.v=(p-old)/dt

def simulate(scored,braced=False):
    start=time.perf_counter()
    if scored.get('version')==3:
        from contact_v3 import surface as mesh_surface
        tissue=Tissue(lambda x,y:mesh_surface(x,y,skin_state=tuple(scored.get("skin_state",(0,0,0)))) or .02)
    else:tissue=Tissue()
    tissue.prepare();frames=[];dt=1/240
    strength=(.35+.65*scored.get('normal_speed',0)) if scored.get('contact_class')!='miss' else 0.
    # A glancing or fingertip contact couples less of the driven hand impulse.
    if scored.get('contact_class')=='tips':strength*=.35
    elif scored.get('contact_class')=='glance':strength*=.60
    centre=scored.get('position',[0,.2,.35]);side=-1 if centre[0]<0 else 1
    head=0.;hv=0.;jaw=0.;jv=0.;peak=0.
    for step in range(673):
        t=step*dt
        forcing=step==120
        impulse=[side*strength*6.3,0.,-strength*22.0] if forcing else None
        tissue.step(dt,(centre,impulse) if impulse else None)
        hv+=((-90*(1.5 if braced else 1)*head-12*hv)+(side*strength*600 if forcing else 0))*dt;head+=hv*dt
        jv+=(-140*jaw-14*jv+(strength*450 if forcing else 0))*dt;jaw=max(-.04,min(.22,jaw+jv*dt))
        if step%2==0:
            offsets=[]
            for i in range(NX*NY):
                offsets.extend(int(round((tissue.p[i][k]-tissue.rest[i][k])*10000)) for k in range(3))
            peak=max(peak,max(abs(v) for v in offsets)/10000)
            frames.append([round(head,5),round(jaw,5),*offsets])
    return dict(fps=120,duration=2.8,contact=.5,nx=NX,ny=NY,scale=.0001,
                frames=frames,peak=round(peak,5),solve_ms=round((time.perf_counter()-start)*1000,1),
                version=scored.get('version',2),arm_path=scored.get('arm_path',[]),footprint=scored.get('footprint',[]),path=scored.get('path',[]),
                contact_time=scored.get('contact_time',0),position=centre,diagnosis=scored.get('diagnosis',''))
