"""Track up-and-return trajectories in the existing powered periodic ring.

Labels follow fluid velocity, not ballistic particles; no gravity, explosion,
surface or phase change. Unwrapped positions distinguish a local return from
one after a periodic boundary crossing. Return = rise by .3, then cross own
initial height downward. This is not necessarily return to the same place.
"""
from pathlib import Path
import json
import numpy as np
from pin_ring import setup
from ring_power import kick
from threshold_transport import interp
from vortex3d import real

L=2*np.pi

class Cohort:
    def __init__(self,start,radius):
        self.start=start;self.radius=radius
        rng=np.random.default_rng(51)
        d=rng.normal(size=(128,3));d/=np.linalg.norm(d,axis=1)[:,None]
        offsets=d*(.15*rng.random(128)**(1/3))[:,None]
        self.initial=np.array([np.pi,np.pi-radius,2.])+offsets
        self.p=self.initial.copy()
        self.max_rise=np.zeros(128);self.max_lateral=np.zeros(128)
        self.crossed=np.zeros(128,dtype=bool)
        self.turned=np.zeros(128,dtype=bool)
        self.return_at=np.full(128,np.nan)
        self.return_after_boundary=np.zeros(128,dtype=bool)
        self.return_lateral=np.full(128,np.nan)
        self.return_radius=np.full(128,np.nan)
    def step(self,v,dt,t):
        mid=self.p+dt*interp(v,self.p)/2
        velocity=interp(v,mid);self.p+=dt*velocity
        self.crossed|=np.any((self.p<0)|(self.p>=L),axis=1)
        dz=self.p[:,2]-self.initial[:,2]
        self.max_rise=np.maximum(self.max_rise,dz)
        lateral=np.linalg.norm(self.p[:,:2]-self.initial[:,:2],axis=1)
        self.max_lateral=np.maximum(self.max_lateral,lateral)
        self.turned|=(self.max_rise>=.3)&(self.max_rise-dz>=.1)&(velocity[:,2]<0)
        returned=(self.max_rise>=.3)&(dz<=0)&(velocity[:,2]<0)&np.isnan(self.return_at)
        self.return_at[returned]=t
        self.return_after_boundary[returned]=self.crossed[returned]
        self.return_lateral[returned]=lateral[returned]
        self.return_radius[returned]=np.linalg.norm(self.p[returned,:2]-np.pi,axis=1)
    def report(self):
        returned=np.isfinite(self.return_at)
        local=returned&~self.return_after_boundary
        return dict(start=self.start,initial_radius=self.radius,labels=len(self.p),
                    fraction_rise_0_3=float(np.mean(self.max_rise>=.3)),
                    fraction_turned=float(self.turned.mean()),
                    fraction_return_without_boundary=float(local.mean()),
                    fraction_return_after_boundary=float((returned&self.return_after_boundary).mean()),
                    fraction_ever_cross_boundary=float(self.crossed.mean()),
                    median_max_rise=float(np.median(self.max_rise)),
                    median_max_lateral=float(np.median(self.max_lateral)),
                    median_local_return_time=float(np.median(self.return_at[local])) if local.any() else None,
                    median_local_return_lateral=float(np.median(self.return_lateral[local])) if local.any() else None,
                    median_local_return_radius=float(np.median(self.return_radius[local])) if local.any() else None)

def run(n,dt=.02,duration=8.):
    f,*_=setup(n,8);f.dt=dt;direction=f.force.copy();f.force*=0
    cohorts=[Cohort(1.5,0.),Cohort(1.5,.6)]+[Cohort(t,1.2) for t in (1.5,2.5,3.5)]
    trajectories=[];work=loss=0.;max_cfl=0.
    for i in range(round(duration/dt)):
        t0=i*dt;t=(i+1)*dt
        energy=.04*min((t0+dt/2)/.2,1)*dt
        kick(f,direction,energy/2);previous=f.u.copy()
        _,d=f.step(False);loss+=d
        mid=real((previous+f.u)/2)
        kick(f,direction,energy/2);work+=energy
        for c in cohorts:
            if t0>=c.start-1e-10:c.step(mid,dt,t)
        if (i+1)%round(.1/dt)==0:
            max_cfl=max(max_cfl,f.measure(t)['cfl'])
            trajectories.append(dict(t=t,positions=[c.p[:8].tolist() if t>=c.start else None for c in cohorts]))
    error=f.energy(f.u)+loss-work
    assert abs(error)<1e-6 and max_cfl<.5
    result=dict(n=n,dt=dt,duration=duration,budget_error=error,max_cfl=max_cfl,
                cohorts=[c.report() for c in cohorts],sample_paths=trajectories)
    print(n,dt,json.dumps(result['cohorts']),flush=True)
    return result

if __name__=='__main__':
    out=Path(__file__).with_name('return_paths_results.json');results=[]
    for n,dt in ((24,.02),(32,.02),(32,.01)):
        results.append(run(n,dt));out.write_text(json.dumps(results,indent=2)+'\n')
