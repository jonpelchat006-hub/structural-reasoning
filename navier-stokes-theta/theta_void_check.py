"""Does the theta=pi interface sit on the fluid's zero-divisor channels?
Zero-divisor channel := P = w.S.w ~ 0 while |w|,|S| > 0 (product of two live
fields collapsing).  Alignment a = P / (|w|^2 |S|_F) in [-1,1].  Compare a at
interface cells (theta >= 3) with the whole domain, at several times.
Passive theta_three run, wall 3, floor -pi, 32^3."""
import json,numpy as np
from theta_three import build, PI
from ring_power import kick
from thermal_loop import face_velocity, heat_step
from vortex3d import real
from theta_kinetic import sreal
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
        th=f.clip(sreal(f.th));Pp,Dw,S,w=f.loads(f.u)
        G=np.array([f.grad(f.u[k]) for k in range(3)]);Sf=np.sqrt(np.sum((.5*(G+G.transpose(1,0,2,3,4)))**2,axis=(0,1)))
        P=sum(w[a]*(.5*(G+G.transpose(1,0,2,3,4)))[a,b]*w[b] for a in range(3) for b in range(3))
        w2=np.sum(w*w,axis=0);live=(w2>1e-3*w2.mean())&(Sf>1e-3*Sf.mean())
        a=np.where(live,P/np.maximum(w2*Sf,1e-30),np.nan)
        iface=th>=3.;hot=heat[0]>=.5*heat[0].max()
        def stats(m):
            v=a[m&live];return dict(count=int(m.sum()),median_abs_a=float(np.nanmedian(np.abs(v))) if v.size else None,
                                   frac_abs_a_lt_0p1=float(np.nanmean(np.abs(v)<.1)) if v.size else None,mean_a=float(np.nanmean(v)) if v.size else None)
        rec=dict(t=tn,interface=stats(iface),hot_half=stats(hot),domain=stats(np.ones_like(iface)),
                 domain_frac_live=float(live.mean()),theta_max=float(th.max()))
        out.append(rec);print(tn,'iface',rec['interface'],'| domain',rec['domain'],flush=True)
json.dump(out,open('theta_void_check_results.json','w'),indent=1)
