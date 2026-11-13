"""Finite-reservoir reaction/diffusion hypothesis test, not fluid dynamics.

Periodic square [-1,1)^2. Seam x=0. Gaussian pulse sigma=.10.
Heat diffusion is exact spectrally, isotropic D=.003. Reservoir release
rate=8 above threshold. Total initial reservoir energy=.5, distributed
in a Gaussian stripe of width .12 whose angle is 0 or 45 degrees to seam.
Uniform threshold 1 vs assumed seam threshold 1-.4 exp(-x²/(2*.12²)).
Energy units arbitrary. No fitted material constants or original theta.
"""
from pathlib import Path
import json
import numpy as np


def simulate(n, location, angle, lowered, pulse, duration=1.0):
    h=2/n
    x,y=np.meshgrid(np.arange(n)*h-1,np.arange(n)*h-1,indexing='ij')
    profile=np.exp(-((x-location)**2+y*y)/(2*.1**2))
    heat=pulse*profile/(profile.sum()*h*h)
    normal=x*np.cos(angle)+y*np.sin(angle)
    reservoir=np.exp(-normal**2/(2*.12**2))
    reservoir*=.5/(reservoir.sum()*h*h)
    threshold=1-.4*np.exp(-x*x/(2*.12**2)) if lowered else np.ones_like(x)
    dt=.005
    k=2*np.pi*np.fft.fftfreq(n,d=h)
    damping=np.exp(-.003*(k[:,None]**2+k[None,:]**2)*dt)
    peak=float(heat.max())
    initial_trigger=bool(np.any(heat>=threshold))
    for _ in range(round(duration/dt)):
        heat=np.fft.ifft2(np.fft.fft2(heat)*damping).real
        released=reservoir*(-np.expm1(-8*dt))*(heat>=threshold)
        reservoir-=released
        heat+=released
        peak=max(peak,float(heat.max()))
    remaining=float(reservoir.sum()*h*h)
    error=float((heat+reservoir).sum()*h*h-pulse-.5)
    assert abs(error)<1e-10
    assert remaining>=-1e-12
    return dict(n=n,location=location,angle_deg=round(float(angle*180/np.pi)),
                lowered_threshold=lowered,pulse=pulse,initial_trigger=initial_trigger,
                released_energy=.5-remaining,peak_heat=peak,energy_error=error)


def main():
    rows=[]
    for n in (64,128):
        for lowered in (False,True):
            for angle in (0,np.pi/4):
                for location in (0,.12,.45):
                    for pulse in (0,.03,.045,.06,.08):
                        rows.append(simulate(n,location,angle,lowered,pulse))
    out=Path(__file__).parent
    (out/'seam_trigger_results.json').write_text(json.dumps(rows,indent=2)+'\n')
    print('Runs:',len(rows),'maximum energy error:',max(abs(r['energy_error']) for r in rows))
    for lower in (False,True):
        for angle in (0,45):
            for loc in (0,.12,.45):
                subset=[r for r in rows if r['n']==128 and r['lowered_threshold']==lower and r['angle_deg']==angle and r['location']==loc]
                first=next((r['pulse'] for r in subset if r['released_energy']>.005),None)
                r=next(r for r in subset if r['pulse']==.06)
                print(lower,angle,loc,'first tested pulse releasing >1% reservoir:',first,'release at .06:',round(r['released_energy'],6))
    diffs=[abs(a['released_energy']-b['released_energy']) for a,b in zip(rows[:60],rows[60:])]
    print('Max resolution difference in release:',max(diffs))


if __name__=='__main__': main()
