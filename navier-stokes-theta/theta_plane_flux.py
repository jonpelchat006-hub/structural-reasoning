"""Local exchange between the normal (solenoidal) and orthogonal (gradient) planes
at the theta interface.  Pi solves lap Pi = div(u x w) (rotational form); the
projection removes grad Pi.  Local exchange density j = -u.grad Pi (sums to 0).
Also the potential-plane 'load' |grad Pi|^2.  Passive thermal run, wall 3, floor -pi."""
import json,numpy as np
from theta_three import build, PI
from ring_power import kick
from thermal_loop import face_velocity, heat_step
from vortex3d import real, fft, cross
from theta_kinetic import sreal, sfft
n,dt=32,.02
f,direction,x,y,z=build(n,0.,dt,wall=3.,floor=-PI)
rates=np.array([0.]);heat=np.zeros((1,n,n,n));h=2*np.pi/n;out=[]
for i in range(150):
    t=(i+.5)*dt;e=.04*min(t/.2,1)*dt
    f.heat=heat[0];kick(f,direction,e/2);prev=f.u.copy();_,d=f.step(False);mid=(prev+f.u)/2;kick(f,direction,e/2)
    g=np.array([real(1j*f.k[j]*mid) for j in range(3)]);q=.5*f.nu*np.sum((g+g.swapaxes(0,1))**2,axis=(0,1))
    if q.mean()>0:q*=d/(dt*q.mean())
    heat,_=heat_step(heat,face_velocity(mid,h),q,dt,h,rates);f.heat=heat[0]
    tn=(i+1)*dt
    if abs(tn-round(tn*2)/2)<1e-9 and tn>=.5:
        th=f.clip(sreal(f.th));u=real(f.u);w=real(1j*cross(f.k,f.u))
        N=fft(cross(u,w))*f.mask                       # nonlinear term (rotational form)
        divN=np.sum(1j*f.k*N,axis=0);Pi_h=-divN*f.inv    # lap Pi = div N  ->  Pi_h = -divN/k^2
        gPi=np.array([sreal(1j*f.k[j]*Pi_h) for j in range(3)])
        j=-np.sum(u*gPi,axis=0);load=np.sum(gPi*gPi,axis=0)
        iface=th>=3.
        def st(m,a): v=a[m];return [float(v.mean()),float(np.median(v)),float(np.abs(v).mean())] if v.size else None
        rec=dict(t=tn,n_iface=int(iface.sum()),j_iface=st(iface,j),j_domain=st(np.ones_like(iface),j),
                 j_abs_rank=float((np.abs(j)[iface].mean()>np.abs(j)).mean()) if iface.any() else None,
                 load_iface=st(iface,load),load_domain=st(np.ones_like(iface),load),
                 load_rank=float((load[iface].mean()>load).mean()) if iface.any() else None,
                 sum_j=float(j.mean()))
        out.append(rec);print(tn,'iface',rec['n_iface'],'j iface(mean,med,|.|)',rec['j_iface'],'domain',rec['j_domain'],'|j| percentile',rec['j_abs_rank'],'load pct',rec['load_rank'],'sum j',f"{rec['sum_j']:.1e}",flush=True)
json.dump(out,open('theta_plane_flux_results.json','w'),indent=1)
