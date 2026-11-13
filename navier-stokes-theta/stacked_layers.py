"""One or two driven vortex-ring layers at fixed delivered power.

Lower ring z=pi-.55, optional upper z=pi+.55. Eight tangential-axis
rotational body forces per ring; upper circulation either agrees or opposes.
All cases start at rest, use nu=.03, and receive power .04 after a .2 ramp.
No material layers, repulsion law, top/bottom openings or magnetic fields.
"""
from pathlib import Path
import json
import numpy as np
from pin_ring import setup
from ring_power import kick
from vortex3d import fft,real,cross

def layer_setup(n,configuration,dt):
    f,x,y,z=setup(n,8);f.dt=dt
    layers=[(np.pi-.55,1)]
    if configuration!='single':layers.append((np.pi+.55,1 if configuration=='reinforcing' else -1))
    raw=np.zeros_like(real(f.u))
    for height,sense in layers:
        for j in range(8):
            a=2*np.pi*j/8
            center=(np.pi+.8*np.cos(a),np.pi+.8*np.sin(a),height)
            delta=np.array([(q-c+np.pi)%(2*np.pi)-np.pi for q,c in zip((x,y,z),center)])
            axis=np.array([np.full_like(x,np.sin(a)),np.full_like(x,-np.cos(a)),np.zeros_like(x)])
            raw+=sense*cross(axis,delta)*np.exp(-np.sum(delta**2,axis=0)/(2*.38**2))
    direction=f.project(fft(raw))
    direction/=np.sqrt(np.mean(np.sum(real(direction)**2,axis=0)))
    f.force*=0
    return f,direction,x,y

def plane(v,z):
    n=v.shape[2];q=z*n/(2*np.pi);i=int(q)%n;frac=q-int(q)
    return (1-frac)*v[:,:,i]+frac*v[:,:,(i+1)%n]

def run(n,configuration,dt=.02):
    f,direction,x,y=layer_setup(n,configuration,dt)
    radius=np.hypot(x[:,:,0]-np.pi,y[:,:,0]-np.pi)
    core=radius<.45;outer=(radius>1)&(radius<1.5)
    work=loss=0.;rows=[]
    for i in range(round(3/dt)):
        energy=.04*min((i+.5)*dt/.2,1)*dt
        kick(f,direction,energy/2)
        _,d=f.step(False);loss+=d
        kick(f,direction,energy/2);work+=energy
        if (i+1)%round(.1/dt)==0:
            row=f.measure((i+1)*dt);uz=real(f.u)[2]
            row['planes']={}
            for name,height in (('lower',np.pi-.55),('between',np.pi),('above',np.pi+1.1)):
                p=plane(uz,height)
                row['planes'][name]=dict(z=height,core=float(p[core].mean()),outer=float(p[outer].mean()),net=float(p.mean()))
            rows.append(row)
    error=f.energy(f.u)-work+loss
    assert abs(error)<1e-6 and max(r['cfl'] for r in rows)<.5
    assert max(abs(p['net']) for r in rows for p in r['planes'].values())<1e-12
    result=dict(n=n,configuration=configuration,dt=dt,input=work,dissipated=loss,budget_error=error,rows=rows)
    print(n,configuration,dt,'E',round(rows[-1]['energy'],6),
          'above',rows[-1]['planes']['above'],'between',rows[-1]['planes']['between'],flush=True)
    return result

if __name__=='__main__':
    out=Path(__file__).with_name('stacked_layers_results.json');results=[]
    for n in (24,32):
        for configuration in ('single','reinforcing','opposing'):
            results.append(run(n,configuration));out.write_text(json.dumps(results,indent=2)+'\n')
    results.append(run(32,'reinforcing',.01));out.write_text(json.dumps(results,indent=2)+'\n')
