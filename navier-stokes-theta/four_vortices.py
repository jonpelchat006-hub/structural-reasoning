"""Equal-energy four-tube comparison using the vortex3d solver.

Pulse is an instantaneous smooth spatial velocity increment, not a resolved
energy-release process. Its amplitude solves the quadratic kinetic-energy
increment exactly. No active seam, wall, or quantum coupling is assumed.
"""
from pathlib import Path
import json
import numpy as np
from vortex3d import Flow,fft,real,cross

def setup(n,pattern,offset,energy,dt):
    f=Flow(n,'control',dt)
    x,y,z=np.meshgrid(*(np.arange(n)*2*np.pi/n for _ in range(3)),indexing='ij')
    count=2 if pattern=='two_opposite' else 4
    w=np.zeros((3,n,n,n))
    for j in range(count):
        phase=2*np.pi*j/count
        sign=1 if pattern=='four_same' else (-1)**j
        cx=np.pi+offset+.7*np.cos(z+phase);cy=np.pi+.7*np.sin(z+phase)
        dx=(x-cx+np.pi)%(2*np.pi)-np.pi;dy=(y-cy+np.pi)%(2*np.pi)-np.pi
        g=np.exp(-(dx*dx+dy*dy)/(2*.45**2))
        w+=sign*g*np.array([-.7*np.sin(z+phase),.7*np.cos(z+phase),np.ones_like(z)])
    wh=f.project(fft(w))
    f.u=f.project(1j*cross(f.k,wh)*f.inv)
    f.u*=np.sqrt(.1/f.energy(f.u))
    before=f.measure(0)
    # Same pulse location and width as the earlier two-tube experiment.
    center=(np.pi+.7,np.pi,0)
    d2=sum(((q-c+np.pi)%(2*np.pi)-np.pi)**2 for q,c in zip((x,y,z),center))
    ph=f.project(fft(np.exp(-d2/(2*.55**2))*real(f.u)))
    a=f.energy(ph);b=float(np.mean(np.sum(real(f.u)*real(ph),axis=0)))
    amplitude=2*energy/(b+np.sqrt(b*b+4*a*energy)) if energy else 0.
    f.u+=amplitude*ph
    assert abs(f.energy(f.u)-.1-energy)<1e-12
    return f,before,amplitude

def run(n,pattern,offset=0.,energy=.02,dt=.02):
    f,before,amp=setup(n,pattern,offset,energy,dt)
    rows=[f.measure(0)];loss=0.
    for i in range(round(1/dt)):
        _,d=f.step(False);loss+=d
        if (i+1)%round(.1/dt)==0:rows.append(f.measure((i+1)*dt))
    residual=rows[-1]['energy']-.1-energy+loss
    assert abs(residual)<1e-6
    assert max(r['cfl'] for r in rows)<.5
    result=dict(n=n,pattern=pattern,offset=offset,pulse_energy=energy,dt=dt,
                impulse_amplitude=amp,before=before,rows=rows,budget_error=residual,
                peak_vorticity=max(r['max_vorticity'] for r in rows),
                peak_stretching=max(r['stretching'] for r in rows))
    print(n,pattern,offset,energy,'peak',round(result['peak_vorticity'],4),'stretch',round(result['peak_stretching'],4),flush=True)
    return result

if __name__=='__main__':
    out=Path(__file__).with_name('four_vortices_results.json')
    results=[]
    for n in (24,32):
        for pattern in ('two_opposite','four_same','four_alternating'):
            for offset,energy in ((0.,0.),(0.,.02),(.8,.02)):
                results.append(run(n,pattern,offset,energy))
                out.write_text(json.dumps(results,indent=2)+'\n')
    results.append(run(32,'four_alternating',0.,.02,.01))
    out.write_text(json.dumps(results,indent=2)+'\n')
