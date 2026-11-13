"""Form B with all three factors live: kinetic theta on the powered THERMAL ring.

theta_s = (1 + w_S ln r_S^p_S)(1 + w_T sr(ln r_T^p_T))(1 + w_E sr(ln r_E^p_E)),
sr(x) = sign(x) sqrt|x| (signed root), Table-1 weights (.8,.6,.4)/(1.2,1,.8).

References follow Shovelcat_Theory_1 App. B (mean of the surroundings):
  T   = 1 + dT (insulated excess);   r_T = <T> / T(x)        (>1 where colder than mean)
  s   = ln(1+dT) (entropy per mass); r_S = (s+e) / (<s>+e)   (>1 where hotter), e = 1e-3
  r_E = (P_w^+ + d<D_w>) / (D_w + d<D_w>)  local enstrophy production / destruction
Field: theta_t + u.grad theta = D lap theta + (theta_s - theta)/tau ; cap at pi.
Coupling: nu_eff = nu exp(beta|theta-1|); extra dissipation heats the liquid too.
Dynamics for beta=0 are identical to thermal_loop.run.  Run: python theta_three.py --n 24
"""
import argparse, json
from pathlib import Path
import numpy as np
from pin_ring import setup
from ring_power import kick
from thermal_loop import face_velocity, heat_step
from vortex3d import real, fft, cross
from theta_kinetic import ThetaFlow, sfft, sreal, PI

W=dict(S=.8,T=.6,E=.4); P=dict(S=1.2,T=1.,E=.8)
def sr(x): return np.sign(x)*np.sqrt(np.abs(x))

class ThreeFlow(ThetaFlow):
    heat=None
    wall=None      # |theta| beyond which a restoring force acts (e.g. 3)
    floor=None     # lower clip (e.g. -pi); None -> no lower clip
    def clip(self,th):
        lo=-np.inf if self.floor is None else self.floor
        return np.clip(th,lo,PI)
    def rhs(self,a,active,thh=None):
        u=real(a); Pp,Dw,S,w=self.loads(a)
        f=self.force if active else self.force*0
        r=self.project(fft(cross(u,w)))-self.nu*self.k2*a+f
        th=self.clip(sreal(thh)); extra=0.
        if self.beta:
            nup=self.nu*(np.exp(self.beta*np.abs(th-1))-1)
            tau_=2*nup[None,None]*S
            div=np.array([sum(1j*self.k[j]*sfft(tau_[i,j]) for j in range(3)) for i in range(3)])
            r=r+self.project(div); extra=float(np.mean(np.sum(tau_*S,axis=(0,1))))
        ths=self.clip(self.theta_static(Pp,Dw))
        src=(ths-th)/self.tau
        if self.wall is not None:
            src=src-np.sign(th)*np.maximum(np.abs(th)-self.wall,0)/self.tau
        adv=-sfft(np.sum(u*self.grad(thh),axis=0)) if getattr(self,'advect',True) else 0.
        rth=(adv-self.D*self.k2*thh+sfft(src))*self.mask
        power=float(np.mean(np.sum(u*real(f),axis=0)))
        diss=float(self.nu*np.mean(np.sum(w*w,axis=0)))+extra
        return r,rth,power,diss
    def step(self,active):
        a,b,h=self.u,self.th,self.dt
        r1,s1,p1,d1=self.rhs(a,active,b); r2,s2,p2,d2=self.rhs(a+h*r1/2,active,b+h*s1/2)
        r3,s3,p3,d3=self.rhs(a+h*r2/2,active,b+h*s2/2); r4,s4,p4,d4=self.rhs(a+h*r3,active,b+h*s3)
        self.u=self.project(a+h*(r1+2*r2+2*r3+r4)/6)
        self.th=sfft(self.clip(sreal((b+h*(s1+2*s2+2*s3+s4)/6)*self.mask)))*self.mask
        return h*(p1+2*p2+2*p3+p4)/6,h*(d1+2*d2+2*d3+d4)/6
    ref_scale=None   # None: global mean reference; float: Gaussian local mean of that width
    def local_mean(self,a):
        if self.ref_scale is None: return a.mean()
        return sreal(sfft(a)*np.exp(-.5*self.k2*self.ref_scale**2))
    def factors(self,Pp,Dw):
        dT=self.heat
        eps=self.delta*Dw.mean(); LE=np.log((Pp+eps)/(Dw+eps))
        T=1+dT; LT=np.log(self.local_mean(T)/T)
        s=np.log1p(dT); LS=np.log((s+1e-3)/(self.local_mean(s)+1e-3))
        fS=1+W['S']*P['S']*LS; fT=1+W['T']*sr(P['T']*LT); fE=1+W['E']*sr(P['E']*LE)
        return fS,fT,fE
    def theta_static(self,Pp,Dw):
        fS,fT,fE=self.factors(Pp,Dw); return fS*fT*fE

def build(n,beta,dt,wall=None,floor=None):
    f0,x,y,z=setup(n,8)
    f=ThreeFlow(n,'control',dt,beta); f.wall=wall; f.floor=floor; f.u=f0.u*0; f.force=f0.force.copy()
    direction=f.force.copy(); f.force*=0
    f.heat=np.zeros((n,n,n))
    return f,direction,x,y,z

def run(n,beta,dt=.02,duration=3.,wall=None,floor=None):
    f,direction,x,y,z=build(n,beta,dt,wall,floor)
    rates=np.array([0.]);heat=np.zeros((1,n,n,n));cooled=np.zeros(1)
    work=loss=0.;rows=[];h=2*np.pi/n;first={k:None for k in ('1','phi','sqrt_pi','3','pi')}
    thr={'1':1.,'phi':1.618034,'sqrt_pi':np.sqrt(np.pi),'3':3.,'pi':np.pi}
    for i in range(round(duration/dt)):
        t=(i+.5)*dt;input_e=.04*min(t/.2,1)*dt
        f.heat=heat[0]
        kick(f,direction,input_e/2);previous=f.u.copy()
        _,d=f.step(False);mid=(previous+f.u)/2
        kick(f,direction,input_e/2);work+=input_e;loss+=d
        grad=np.array([real(1j*f.k[j]*mid) for j in range(3)])
        th=f.clip(sreal(f.th));nueff=f.nu*np.exp(f.beta*np.abs(th-1))
        q=.5*nueff*np.sum((grad+grad.swapaxes(0,1))**2,axis=(0,1))
        if q.mean()>0:q*=d/(dt*q.mean())
        heat,removed=heat_step(heat,face_velocity(mid,h),q,dt,h,rates);cooled+=removed
        f.heat=heat[0]
        thm=float(th.max());tnow=(i+1)*dt
        for k,c in thr.items():
            if first[k] is None and thm>=c: first[k]=tnow
        if (i+1)%round(.1/dt)==0:
            row=f.measure(tnow);Pp,Dw,_,_=f.loads(f.u);fS,fT,fE=f.factors(Pp,Dw)
            row.update(input_energy=work,dissipated=loss,heat_mean=float(heat[0].mean()),heat_max=float(heat[0].max()),
                       fS=[float(fS.min()),float(fS.max())],fT=[float(fT.min()),float(fT.max())],fE=[float(fE.min()),float(fE.max())],
                       theta_s_max=float((fS*fT*fE).max()),theta_E_only_max=float(fE.max()),
                       argmax_theta=[float(c[np.unravel_index(np.argmax(th),th.shape)]) for c in (x,y,z)],
                       heat_at_argmax=float(heat[0][np.unravel_index(np.argmax(th),th.shape)]),
                       theta_min_clipped=float(th.min()),vol_above_3=float((th>3).mean()),vol_below_m3=float((th<-3).mean()),vol_at_floor=float((th<=-PI+1e-9).mean()))
            rows.append(row)
    thermal_error=float(abs(heat.mean()+cooled[0]-loss));total_error=float(abs(f.energy(f.u)+heat.mean()+cooled[0]-work))
    assert thermal_error<1e-9 and total_error<1e-6,(thermal_error,total_error)
    res=dict(n=n,beta=beta,dt=dt,duration=duration,wall=wall,floor=floor,thermal_error=thermal_error,total_error=total_error,
             first_theta_crossings=first,peak_theta=max(r['theta_max'] for r in rows),rows=rows)
    r=rows[-1]
    print(n,'beta',beta,'E',round(r['energy'],6),'omega',round(r['max_vorticity'],4),'heat max',round(r['heat_max'],4),
          'theta max',round(res['peak_theta'],4),'theta_s max',round(max(x['theta_s_max'] for x in rows),4),
          'E-only max',round(max(x['theta_E_only_max'] for x in rows),4),'crossings',first,'err',f'{total_error:.1e}',flush=True)
    return res

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--n',type=int,default=24);ap.add_argument('--dt',type=float,default=.02)
    ap.add_argument('--betas',type=float,nargs='+',default=[0.,.5]);ap.add_argument('--wall',type=float,default=None);ap.add_argument('--floor',type=float,default=None);a=ap.parse_args()
    tag=('' if a.wall is None else f'_wall{a.wall:g}')+('' if a.floor is None else f'_floor{a.floor:g}')
    out=Path(__file__).with_name(f'theta_three_{a.n}_{a.dt}{tag}_results.json');res=[]
    for b in a.betas: res.append(run(a.n,b,a.dt,wall=a.wall,floor=a.floor));out.write_text(json.dumps(res,indent=1)+'\n')
