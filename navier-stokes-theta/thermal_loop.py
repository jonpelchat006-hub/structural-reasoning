"""Advected viscous heat on the powered ring; one-way thermal coupling.

Dimensionless heat capacity per mass=1, temperature excess initially zero,
thermal diffusivity=.02, cooling rates 0,.5,2 to a zero-excess baseline.
Viscous heating shape is 2*nu*S:S; its spatial mean is calibrated each step
to the RK4-integrated kinetic dissipation. Heat does NOT change the flow.
Conservative upwind finite-volume advection plus diffusion, with positive
substeps; face velocity has its own discrete divergence-free projection.
Thermal peak resolution is limited by first-order numerical diffusion.
"""
import json
from pathlib import Path
import numpy as np
from pin_ring import setup
from ring_power import kick
from vortex3d import real

def face_velocity(uh,h):
    u=real(uh)
    faces=np.array([(u[j]+np.roll(u[j],-1,axis=j))/2 for j in range(3)])
    div=sum((faces[j]-np.roll(faces[j],1,axis=j))/h for j in range(3))
    n=u.shape[1];freq=2*np.pi*np.fft.fftfreq(n)
    ks=np.meshgrid(freq,freq,freq,indexing='ij')
    lap=-4*sum(np.sin(k/2)**2 for k in ks)/h**2
    ph=np.divide(np.fft.fftn(div),lap,out=np.zeros_like(np.fft.fftn(div)),where=lap!=0)
    p=np.fft.ifftn(ph).real
    for j in range(3):faces[j]-=(np.roll(p,-1,axis=j)-p)/h
    err=np.max(abs(sum((faces[j]-np.roll(faces[j],1,axis=j))/h for j in range(3))))
    assert err<1e-11
    return faces

def heat_step(heat,faces,q,dt,h,rates):
    # Outgoing donor-cell rate plus six diffusive neighbors controls positivity.
    outgoing=sum(np.maximum(faces[j],0)+np.maximum(-np.roll(faces[j],1,axis=j),0) for j in range(3))/h
    count=max(1,int(np.ceil(dt*(outgoing.max()+6*.02/h**2)/.7)))
    sub=dt/count;removed=np.zeros(len(rates));decay=np.exp(-rates[:,None,None,None]*sub/2)
    for _ in range(count):
        before=heat.mean(axis=(1,2,3));heat*=decay
        removed+=before-heat.mean(axis=(1,2,3))
        change=np.zeros_like(heat)
        for j in range(3):
            v=faces[j][None]
            flux=np.maximum(v,0)*heat+np.minimum(v,0)*np.roll(heat,-1,axis=j+1)
            change-=(flux-np.roll(flux,1,axis=j+1))/h
            change+=.02*(np.roll(heat,-1,axis=j+1)-2*heat+np.roll(heat,1,axis=j+1))/h**2
        heat+=sub*(change+q)
        before=heat.mean(axis=(1,2,3));heat*=decay
        removed+=before-heat.mean(axis=(1,2,3))
    assert heat.min()>-1e-12
    return heat,removed

def run(n,dt=.02,duration=3.,stop=3.,observer=None):
    f,x,y,z=setup(n,8);f.dt=dt;direction=f.force.copy();f.force*=0
    rates=np.array([0.,.5,2.]);heat=np.zeros((3,n,n,n));cooled=np.zeros(3)
    work=loss=0.;rows=[];h=2*np.pi/n
    for i in range(round(duration/dt)):
        t=(i+.5)*dt;input_e=.04*min(t/.2,1)*dt if t<stop else 0
        kick(f,direction,input_e/2);previous=f.u.copy()
        _,d=f.step(False);mid=(previous+f.u)/2
        kick(f,direction,input_e/2);work+=input_e;loss+=d
        grad=np.array([real(1j*f.k[j]*mid) for j in range(3)])
        q=.5*f.nu*np.sum((grad+grad.swapaxes(0,1))**2,axis=(0,1))
        if q.mean()>0:q*=d/(dt*q.mean())
        heat,removed=heat_step(heat,face_velocity(mid,h),q,dt,h,rates);cooled+=removed
        if observer is not None:
            observer((i+1)*dt,heat,real(mid),dt,(x,y,z))
        if (i+1)%round(.1/dt)==0:
            row=f.measure((i+1)*dt)
            row.update(input_energy=work,dissipated=loss,heat_mean=heat.mean(axis=(1,2,3)).tolist(),
                       heat_max=heat.max(axis=(1,2,3)).tolist(),removed_heat=cooled.tolist(),
                       heat_max_position=[float(qcoord[np.unravel_index(np.argmax(heat[0]),heat[0].shape)]) for qcoord in (x,y,z)])
            rows.append(row)
    thermal_error=float(np.max(abs(heat.mean(axis=(1,2,3))+cooled-loss)))
    total_error=float(np.max(abs(f.energy(f.u)+heat.mean(axis=(1,2,3))+cooled-work)))
    assert thermal_error<1e-10 and total_error<1e-6
    result=dict(n=n,dt=dt,duration=duration,stop=stop,cooling_rates=rates.tolist(),
                thermal_error=thermal_error,total_error=total_error,rows=rows)
    print(n,dt,stop,'mean',rows[-1]['heat_mean'],'peak',rows[-1]['heat_max'],'error',total_error,flush=True)
    return result

if __name__=='__main__':
    results=[];out=Path(__file__).with_name('thermal_loop_results.json')
    for n,dt,stop in ((24,.02,3.),(32,.02,3.),(32,.01,3.),(32,.02,1.)):
        results.append(run(n,dt,stop=stop));out.write_text(json.dumps(results,indent=2)+'\n')
