"""Equal-power ring controls using energy-calibrated discrete increments.
Strang split: half kinetic-energy increment, unforced NS step, half increment.
This is an ideal powered controller, NOT a motor/thermal/magnetic model.
P=.04 while active; start at rest. Smooth finite-duration startup power ramp
min(t/.2,1) avoids nonzero power at zero speed. Pulse direction stays fixed.
"""
import json
from pathlib import Path
import numpy as np
from pin_ring import setup
from vortex3d import real

def kick(f,direction,energy):
    if not energy:return
    a=f.energy(direction)
    b=float(np.mean(np.sum(real(f.u)*real(direction),axis=0)))
    amp=(-b+np.sqrt(b*b+4*a*energy))/(2*a)
    before=f.energy(f.u);f.u+=amp*direction
    assert abs(f.energy(f.u)-before-energy)<1e-12

def run(n,count,stop=3.,dt=.02,duration=3.):
    f,x,y,z=setup(n,count);f.dt=dt
    direction=f.force.copy();f.force*=0
    radius=np.sqrt((x[:,:,0]-np.pi)**2+(y[:,:,0]-np.pi)**2)
    core=radius<.45;outer=(radius>1)&(radius<1.5)
    rows=[];work=loss=0
    for i in range(round(duration/dt)):
        t=(i+.5)*dt
        energy=.04*min(t/.2,1)*dt if t<stop else 0
        kick(f,direction,energy/2)
        _,d=f.step(False);loss+=d
        kick(f,direction,energy/2);work+=energy
        if (i+1)%round(.1/dt)==0:
            row=f.measure((i+1)*dt);uz=real(f.u)[2,:,:,n//2]
            row.update(core=float(uz[core].mean()),outer=float(uz[outer].mean()),
                       input_energy=work,dissipated_energy=loss,
                       dissipation_rate=f.nu*2*row['enstrophy'])
            rows.append(row)
    residual=f.energy(f.u)-work+loss
    assert abs(residual)<1e-6
    assert max(r['cfl'] for r in rows)<.5
    result=dict(n=n,count=count,stop=stop,dt=dt,duration=duration,budget_error=residual,rows=rows)
    print(n,count,stop,dt,'E',round(rows[-1]['energy'],6),'omega',round(rows[-1]['max_vorticity'],4),
          'loss rate',round(rows[-1]['dissipation_rate'],6),flush=True)
    return result

if __name__=='__main__':
    out=Path(__file__).with_name('ring_power_results.json');results=[]
    for n in (24,32):
        for stop in (1.,3.):
            results.append(run(n,8,stop));out.write_text(json.dumps(results,indent=2)+'\n')
    results.append(run(32,16));out.write_text(json.dumps(results,indent=2)+'\n')
    results.append(run(32,8,3.,.01));out.write_text(json.dumps(results,indent=2)+'\n')
