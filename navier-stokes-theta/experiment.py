"""Periodic 2D incompressible Navier-Stokes; diagnostic, not a 3D blow-up test.
Run: python navier_stokes_theta/experiment.py
"""
from pathlib import Path
import json
import numpy as np

OUT = Path(__file__).resolve().parent


class Flow:
    def __init__(self, n, nu, dt, amplitude=1., perturb=.01, seed=12, k=4):
        self.n, self.nu, self.dt, self.k = n, nu, dt, k
        self.y = np.arange(n)[None, :] * 2*np.pi/n
        freq = np.fft.fftfreq(n, 1/n)
        self.kx, self.ky = np.meshgrid(freq, freq, indexing='ij')
        self.k2 = self.kx**2+self.ky**2
        self.inv = np.divide(1., self.k2, out=np.zeros_like(self.k2), where=self.k2>0)
        self.mask = (abs(self.kx)<n/3)&(abs(self.ky)<n/3)
        # Fix a continuous perturbation across resolutions.
        x = np.arange(n)[:, None]*2*np.pi/n
        rng = np.random.default_rng(seed)
        noise = np.zeros((n,n))
        for a,b in [(1,1),(2,1),(1,2),(3,2)]:
            noise += np.cos(a*x+b*self.y+rng.uniform(0,2*np.pi))
        w = np.broadcast_to(-amplitude*k*np.cos(k*self.y),(n,n)).copy()
        w += perturb*noise
        self.w = np.fft.fft2(w)*self.mask
        self.force = nu*k*k # equilibrium shear amplitude 1
        self.fhat = np.fft.fft2(np.broadcast_to(-self.force*k*np.cos(k*self.y),(n,n)))

    def real(self,a): return np.fft.ifft2(a).real

    def fields(self,w):
        return self.real(1j*self.ky*self.inv*w), self.real(-1j*self.kx*self.inv*w)

    def rhs(self,w):
        u,v=self.fields(w)
        adv=u*self.real(1j*self.kx*w)+v*self.real(1j*self.ky*w)
        return -np.fft.fft2(adv)*self.mask-self.nu*self.k2*w+self.fhat

    def step(self):
        w,h=self.w,self.dt
        a=self.rhs(w); b=self.rhs(w+h*a/2); c=self.rhs(w+h*b/2); d=self.rhs(w+h*c)
        self.w=(w+h*(a+2*b+2*c+d)/6)*self.mask

    def measure(self,t):
        u,v=self.fields(self.w); w=self.real(self.w)
        E=np.mean(u*u+v*v)/2
        P=np.mean(u*self.force*np.sin(self.k*self.y))
        D=self.nu*np.mean(w*w)
        power=abs(self.w)**2*self.inv
        off=(self.kx!=0)
        # Off-shear energy measures symmetry breaking, not a turbulence certificate.
        fraction=float(power[off].sum()/power.sum())
        gh=[self.real(1j*a*b) for a in (self.kx,self.ky)
            for b in (1j*self.ky*self.inv*self.w,-1j*self.kx*self.inv*self.w)]
        grad=float(np.sqrt(sum(z*z for z in gh)).max())
        wd=self.rhs(self.w)
        ud,vd=self.fields(wd)
        residual=float(np.mean(u*ud+v*vd)-(P-D))
        return dict(t=t,E=float(E),P=float(P),D=float(D),theta=float(P/D),
                    off_shear=fraction,grad_max=grad,vorticity_max=float(abs(w).max()),
                    compact_grad=grad/(1+grad),budget_residual=residual,
                    cfl=float((abs(u).max()+abs(v).max())*self.dt*self.n/(2*np.pi)))


def run(n,nu,dt,amplitude=1.,perturb=.01,seed=12,T=20):
    f=Flow(n,nu,dt,amplitude,perturb,seed)
    rows=[f.measure(0)]
    steps=round(T/dt); stride=round(.1/dt)
    for i in range(steps):
        f.step()
        if (i+1)%stride==0: rows.append(f.measure((i+1)*dt))
    assert all(np.isfinite(r['E']) for r in rows)
    assert max(r['cfl'] for r in rows)<.5
    return f,rows


def summarize(rows):
    r=rows[-1]
    crossings={}
    for threshold in (1.,np.sqrt((1+np.sqrt(5))/2),(1+np.sqrt(5))/2,np.sqrt(np.pi),np.pi):
        times=[b['t'] for a,b in zip(rows,rows[1:]) if (a['theta']-threshold)*(b['theta']-threshold)<0]
        crossings[str(round(float(threshold),6))]=times
    onset=next((x['t'] for x in rows if x['off_shear']>=.1),None)
    return dict(final_energy=r['E'],final_theta=r['theta'],off_shear_final=r['off_shear'],
                off_shear_10pct_time=onset,peak_gradient=max(x['grad_max'] for x in rows),
                peak_compact_gradient=max(x['compact_grad'] for x in rows),
                max_budget_residual=max(abs(x['budget_residual']) for x in rows),
                max_cfl=max(x['cfl'] for x in rows),theta_crossings=crossings)


def main():
    results={}; checks=[]
    for amp in (.5,1.,2.):
        f,rows=run(32,.03,.01,amp,0,T=2)
        exact=1+(amp-1)*np.exp(-.03*16*2)
        u,_=f.fields(f.w)
        err=float(abs(u-exact*np.sin(4*f.y)).max())
        assert err<1e-8
        checks.append(dict(amplitude=amp,max_velocity_error=err))
    print('Exact shear checks passed',flush=True)
    # Same shape and forcing scale; viscosity changes the reference Reynolds number.
    for nu in (.1,.03,.01):
        for amp in (.5,1.,2.):
            key=f'nu{nu}_a{amp}'
            _,rows=run(48,nu,.01,amp)
            results[key]=dict(n=48,nu=nu,amplitude=amp,seed=12,dt=.01,T=20,
                              reference_Re=1/(4*nu),summary=summarize(rows),series=rows)
            print(key,results[key]['summary']['off_shear_10pct_time'],flush=True)
    for n,dt,seed in [(64,.01,12),(96,.01,12),(48,.005,12),(48,.01,37)]:
        key=f'check_n{n}_dt{dt}_seed{seed}'
        _,rows=run(n,.01,dt,1.,seed=seed)
        results[key]=dict(n=n,nu=.01,amplitude=1.,seed=seed,dt=dt,T=20,
                          reference_Re=25.,summary=summarize(rows),series=rows)
        print(key,'done',flush=True)
    (OUT/'results.json').write_text(json.dumps(dict(exact_checks=checks,runs=results),indent=2))
    lines=['# First theta / fluid experiment','',
           '2D periodic forced flow on [0, 2pi)^2, spectral vorticity solver, strict 2/3 dealiasing, RK4. '
           'These are dimensionless numerical experiments, not tests of 3D finite-time singularity.', '',
           'Off-shear energy >=10% is a preselected symmetry-breaking marker, not a validated turbulence definition. '
           'Thresholds were measured, not inserted into the dynamics. All runs end at t=20.', '',
           '| Run | Reference Re | Final theta | Final off-shear fraction | 10% marker time | Peak velocity gradient |',
           '|---|---:|---:|---:|---:|---:|']
    for key,r in results.items():
        s=r['summary']
        lines.append(f"| {key} | {r['reference_Re']:.3g} | {s['final_theta']:.4g} | {s['off_shear_final']:.4g} | {s['off_shear_10pct_time']} | {s['peak_gradient']:.4g} |")
    lines+=['','Exact shear max velocity error: '+str(max(c['max_velocity_error'] for c in checks)),
            'Max instantaneous energy budget residual: '+str(max(r['summary']['max_budget_residual'] for r in results.values())),
            '', 'Full sampled time series and threshold crossing times are in results.json. '
            'Spatial/time refinement and a second perturbation seed apply to nu=.01, initial amplitude=1 only. '
            'No material-specific constitutive laws or real-fluid calibration are included.']
    (OUT/'RESULTS.md').write_text('\n'.join(lines)+'\n')


if __name__=='__main__': main()
