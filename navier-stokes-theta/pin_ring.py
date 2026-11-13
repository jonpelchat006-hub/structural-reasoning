"""Localized rotational body-force surrogates, NOT solid pin boundaries.
Evenly spaced drives on radius .8 at z=pi; axes tangent to ring with sign
chosen for upward force on each drive's outer side. Opposite drives have
opposite axes. Gaussian width .38, constant total force RMS .3. Initially
quiescent periodic incompressible fluid, viscosity .03; run to t=1.
No walls, heating, magnetic fields, theta or prescribed return flow.
"""
import json
from pathlib import Path
import numpy as np
from vortex3d import Flow,fft,real,cross

def setup(n,count):
    f=Flow(n,'control',.02);f.u*=0
    x,y,z=np.meshgrid(*(np.arange(n)*2*np.pi/n for _ in range(3)),indexing='ij')
    raw=np.zeros_like(real(f.u))
    for j in range(count):
        a=2*np.pi*j/count
        center=(np.pi+.8*np.cos(a),np.pi+.8*np.sin(a),np.pi)
        delta=np.array([(q-c+np.pi)%(2*np.pi)-np.pi for q,c in zip((x,y,z),center)])
        axis=np.array([np.full_like(x,np.sin(a)),np.full_like(x,-np.cos(a)),np.zeros_like(x)])
        raw+=cross(axis,delta)*np.exp(-np.sum(delta**2,axis=0)/(2*.38**2))
    f.force=f.project(fft(raw))
    f.force*=.3/np.sqrt(np.mean(np.sum(real(f.force)**2,axis=0)))
    return f,x,y,z

def run(n,count):
    f,x,y,z=setup(n,count)
    rows=[];work=loss=0
    r=np.sqrt((x[:,:,0]-np.pi)**2+(y[:,:,0]-np.pi)**2)
    inner=r<.45;outer=(r>1)&(r<1.5)
    for i in range(50):
        p,d=f.step(True);work+=p;loss+=d
        if (i+1)%5==0:
            row=f.measure((i+1)*.02)
            uz=real(f.u)[2,:,:,n//2]
            row.update(core_vertical=float(uz[inner].mean()),outer_vertical=float(uz[outer].mean()),
                       plane_flux=float(uz.mean()*(2*np.pi)**2))
            rows.append(row)
    # Azimuthal variation in outer-ring upward flow, binned into eight sectors.
    uz=real(f.u)[2,:,:,n//2];theta=np.arctan2(y[:,:,0]-np.pi,x[:,:,0]-np.pi)
    sectors=[float(uz[outer&(theta>=-np.pi+j*np.pi/4)&(theta<-np.pi+(j+1)*np.pi/4)].mean()) for j in range(8)]
    residual=f.energy(f.u)-work+loss
    assert abs(residual)<1e-6
    assert max(row['cfl'] for row in rows)<.5
    result=dict(n=n,drives=count,work=work,dissipation=loss,budget_error=residual,
                sector_means=sectors,sector_cv=float(np.std(sectors)/abs(np.mean(sectors))),rows=rows)
    print(n,count,'core',round(rows[-1]['core_vertical'],5),'outer',round(rows[-1]['outer_vertical'],5),
          'variation',round(result['sector_cv'],3),flush=True)
    return result

if __name__=='__main__':
    results=[];out=Path(__file__).with_name('pin_ring_results.json')
    for n in (24,32):
        for count in (2,4,8,16):
            results.append(run(n,count));out.write_text(json.dumps(results,indent=2)+'\n')
