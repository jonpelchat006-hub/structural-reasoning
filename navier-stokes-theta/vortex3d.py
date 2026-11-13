"""Periodic 3D Navier-Stokes controls; dimensionless, no void/quantum law.
Velocity projection, rotational nonlinearity, strict 2/3 dealiasing, RK4.
Two smooth opposite helical vorticity tubes are constructed by projection
of Gaussian tangent fields; projection slightly changes prescribed tubes.
All pulses have equal spatial L2 norm and duration, NOT equal signed work.
"""
import json
from pathlib import Path
import numpy as np

AX=(1,2,3)
def fft(a): return np.fft.fftn(a,axes=AX)
def real(a): return np.fft.ifftn(a,axes=AX).real
def cross(a,b): return np.cross(a,b,axisa=0,axisb=0,axisc=0)

class Flow:
    def __init__(self,n,kind,dt):
        self.n,self.dt,self.nu=n,dt,.03
        x,y,z=np.meshgrid(*(np.arange(n)*2*np.pi/n for _ in range(3)),indexing='ij')
        self.k=np.array(np.meshgrid(*(np.fft.fftfreq(n,1/n) for _ in range(3)),indexing='ij'))
        self.k2=np.sum(self.k*self.k,axis=0)
        self.inv=np.divide(1.,self.k2,out=np.zeros_like(self.k2),where=self.k2>0)
        self.mask=np.all(abs(self.k)<n/3,axis=0)
        w=np.zeros((3,n,n,n))
        for sign,phase in ((1,0),(-1,np.pi)):
            cx=np.pi+.7*np.cos(z+phase); cy=np.pi+.7*np.sin(z+phase)
            dx=(x-cx+np.pi)%(2*np.pi)-np.pi; dy=(y-cy+np.pi)%(2*np.pi)-np.pi
            g=np.exp(-(dx*dx+dy*dy)/(2*.45**2))
            tangent=np.array([-.7*np.sin(z+phase),.7*np.cos(z+phase),np.ones_like(z)])
            w+=sign*g*tangent
        wh=self.project(fft(w))
        self.u=self.project(1j*cross(self.k,wh)*self.inv)
        self.u*=np.sqrt(.1/self.energy(self.u))
        base=real(self.u)
        center=(np.pi+.7,np.pi,0.)
        distance=sum(((q-c+np.pi)%(2*np.pi)-np.pi)**2 for q,c in zip((x,y,z),center))
        envelope=np.exp(-distance/(2*.55**2))
        raw=envelope*base
        if kind=='opposing': raw=-raw
        if kind=='transverse': raw=cross(np.array([np.zeros_like(z),np.zeros_like(z),np.ones_like(z)]),raw)
        self.force=self.project(fft(raw))
        self.force*=.3/np.sqrt(np.mean(real(self.force)**2)*3)
        if kind=='control': self.force*=0
    def project(self,a): return (a-self.k*np.sum(self.k*a,axis=0)*self.inv)*self.mask
    def energy(self,a): return float(np.mean(np.sum(real(a)**2,axis=0))/2)
    def rhs(self,a,active):
        u=real(a); w=real(1j*cross(self.k,a))
        f=self.force if active else self.force*0
        r=self.project(fft(cross(u,w)))-self.nu*self.k2*a+f
        power=float(np.mean(np.sum(u*real(f),axis=0)))
        diss=float(self.nu*np.mean(np.sum(w*w,axis=0)))
        return r,power,diss
    def measure(self,t):
        u=real(self.u); w=real(1j*cross(self.k,self.u))
        stretch=sum(w[j]*real(1j*self.k[j]*self.u) for j in range(3))
        return dict(t=t,energy=self.energy(self.u),max_speed=float(np.linalg.norm(u,axis=0).max()),
                    max_vorticity=float(np.linalg.norm(w,axis=0).max()),
                    enstrophy=float(np.mean(np.sum(w*w,axis=0))/2),
                    stretching=float(np.mean(np.sum(w*stretch,axis=0))),
                    divergence_max=float(abs(real(np.sum(1j*self.k*self.u,axis=0)[None])) .max()),
                    cfl=float(np.max(np.sum(abs(u),axis=0))*self.dt*self.n/(2*np.pi)))
    def step(self,active):
        a=self.u; h=self.dt
        r1,p1,d1=self.rhs(a,active);r2,p2,d2=self.rhs(a+h*r1/2,active)
        r3,p3,d3=self.rhs(a+h*r2/2,active);r4,p4,d4=self.rhs(a+h*r3,active)
        self.u=self.project(a+h*(r1+2*r2+2*r3+r4)/6)
        return h*(p1+2*p2+2*p3+p4)/6,h*(d1+2*d2+2*d3+d4)/6

def run(n,kind,dt=.01):
    f=Flow(n,kind,dt); rows=[f.measure(0)];work=loss=0.
    for i in range(round(2/dt)):
        p,d=f.step(i<round(.3/dt));work+=p;loss+=d
        if (i+1)%round(.1/dt)==0: rows.append(f.measure((i+1)*dt))
    residual=rows[-1]['energy']-rows[0]['energy']-work+loss
    assert abs(residual)<1e-7
    assert max(r['cfl'] for r in rows)<.5
    result=dict(n=n,kind=kind,dt=dt,work=work,dissipation=loss,budget_error=residual,
                peak_vorticity=max(r['max_vorticity'] for r in rows),rows=rows)
    print(n,kind,dt,'work',round(work,6),'peak omega',round(result['peak_vorticity'],5),'final E',round(rows[-1]['energy'],6),flush=True)
    return result

if __name__=='__main__':
    results=[run(n,k) for n in (24,32) for k in ('control','aligned','opposing','transverse')]
    results.append(run(32,'aligned',.005))
    Path(__file__).with_name('vortex3d_results.json').write_text(json.dumps(results,indent=2)+'\n')
