"""Placement of Gamma relative to gradient concentration, tube flow, 48^3, nu=.01."""
import json,numpy as np
from theta_tubes import tubes
from theta_three import ThreeFlow, PI
from thermal_loop import face_velocity, heat_step
from vortex3d import real
from theta_kinetic import sreal
n,nu,dt=48,.01,.01
f=ThreeFlow(n,'control',dt,0.);f.nu=nu;f.wall=3.;f.floor=-PI;f.force*=0
f.u,x,y,z=tubes(f,n);heat=np.zeros((1,n,n,n));h=2*np.pi/n;out=[]
X=np.stack([x,y,z],-1)
def mind(p,mask):
    q=X[mask];d=(q-p+np.pi)%(2*np.pi)-np.pi;return float(np.sqrt((d*d).sum(1)).min())
for i in range(300):
    f.heat=heat[0];prev=f.u.copy();_,d=f.step(False);mid=(prev+f.u)/2
    g=np.array([real(1j*f.k[j]*mid) for j in range(3)]);q=.5*nu*np.sum((g+g.swapaxes(0,1))**2,axis=(0,1))
    if q.mean()>0:q*=d/(dt*q.mean())
    heat,_=heat_step(heat,face_velocity(mid,h),q,dt,h,np.array([0.]));f.heat=heat[0]
    if (i+1)%30==0:
        th=f.clip(sreal(f.th));G=th>=3.;gm=np.sqrt(np.sum(g*g,axis=(0,1)));top=gm>=np.quantile(gm,.9);hot=heat[0]>=np.quantile(heat[0],.9)
        if G.any():
            pg=X[np.unravel_index(np.argmax(gm),gm.shape)]
            rec=dict(t=(i+1)*dt,n_gamma=int(G.sum()),dist_gradmax_to_gamma=mind(pg,G),frac_gamma_in_top10_grad=float((G&top).sum()/G.sum()),
                     frac_gamma_in_top10_heat=float((G&hot).sum()/G.sum()),gradmax_in_gamma=bool(G[np.unravel_index(np.argmax(gm),gm.shape)]),
                     mean_grad_at_gamma_over_domain=float(gm[G].mean()/gm.mean()))
        else: rec=dict(t=(i+1)*dt,n_gamma=0)
        out.append(rec);print(rec,flush=True)
json.dump(out,open('theta_tubes_place_results.json','w'),indent=1)
