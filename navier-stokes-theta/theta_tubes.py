"""Antiparallel vortex tubes (Kerr-type perturbation), unforced, decaying,
insulated thermal field driven ONLY by viscous heating, three-factor kinetic
theta (wall 3, floor -pi), optional J sink (kappa).  No drives, no hot channel:
heat forms where gradients concentrate.  Run: python theta_tubes.py --n 48 --nu 0.02"""
import argparse,json,numpy as np
from pathlib import Path
from theta_three import ThreeFlow, PI
from thermal_loop import face_velocity, heat_step
from vortex3d import real, fft, cross
from theta_kinetic import sreal, sfft
from theta_J_sweep import plane_exchange

def tubes(f,n,d=.8,a=.2,sig=.3,E0=.15):
    x,y,z=np.meshgrid(*(np.arange(n)*2*np.pi/n for _ in range(3)),indexing='ij')
    w=np.zeros((3,n,n,n))
    for s,sign in ((+1,+1),(-1,-1)):
        yc=np.pi+s*(d/2+a*np.cos(x)); zc=np.pi
        dy=(y-yc+np.pi)%(2*np.pi)-np.pi; dz=(z-zc+np.pi)%(2*np.pi)-np.pi
        g=np.exp(-(dy*dy+dz*dz)/(2*sig*sig))
        tang=np.array([np.ones_like(x),-s*a*np.sin(x),np.zeros_like(x)])   # follows the perturbed centreline
        w+=sign*g*tang
    wh=f.project(fft(w)); u=f.project(1j*cross(f.k,wh)*f.inv)
    u*=np.sqrt(E0/f.energy(u)); return u,x,y,z

def run(n,nu,kappa=0.,dt=.01,duration=3.,E0=.15,stop=None,ckpt=None,ref=None,cool=0.):
    f=ThreeFlow(n,'control',dt,0.); f.nu=nu; f.wall=3.; f.floor=-PI; f.force*=0; f.ref_scale=ref
    f.u,x,y,z=tubes(f,n,E0=E0); f.heat=np.zeros((n,n,n))
    rates=np.array([cool]);heat=np.zeros((1,n,n,n));h=2*np.pi/n;loss=sink=0.;E_init=f.energy(f.u);rows=[];i0=0;cooled=0.
    if ckpt and Path(ckpt).exists():
        c=np.load(ckpt,allow_pickle=True);f.u=c['u'];f.th=c['th'];heat=c['heat'];loss=float(c['loss']);sink=float(c['sink']);E_init=float(c['E_init']);rows=list(c['rows']);i0=int(c['i']);cooled=float(c['cooled'])
        print('resumed at step',i0,flush=True)
    last=round((stop if stop else duration)/dt)
    for i in range(i0,last):
        f.heat=heat[0];prev=f.u.copy();_,d=f.step(False);mid=(prev+f.u)/2;loss+=d
        if kappa:
            th=f.clip(sreal(f.th));G=th>=3.
            if G.any():
                j,u=plane_exchange(f);jp=np.where(G,np.maximum(j,0),0.);u2=np.sum(u*u,axis=0)
                fac=np.where(u2>1e-12,np.minimum(kappa*jp*dt/np.maximum(u2/2,1e-12),1.),0.)
                b=f.energy(f.u);f.u=f.project(fft(u*np.sqrt(np.maximum(1-fac,0))[None]));sink+=b-f.energy(f.u)
        g=np.array([real(1j*f.k[j]*mid) for j in range(3)]);q=.5*f.nu*np.sum((g+g.swapaxes(0,1))**2,axis=(0,1))
        if q.mean()>0:q*=d/(dt*q.mean())
        heat,rem=heat_step(heat,face_velocity(mid,h),q,dt,h,rates);f.heat=heat[0];cooled+=float(rem[0])
        tn=(i+1)*dt
        if (i+1)%round(.1/dt)==0:
            th=f.clip(sreal(f.th));G=th>=3.;j,u=plane_exchange(f);gm=np.sqrt(np.sum(g*g,axis=(0,1)))
            Pp,Dw,_,_=f.loads(f.u);fS,fT,fE=f.factors(Pp,Dw)
            def loc(m): idx=np.unravel_index(np.argmax(m),m.shape);return [float(c[idx]) for c in (x,y,z)]
            def dist(p,q): return float(np.sqrt(sum(((a-b+np.pi)%(2*np.pi)-np.pi)**2 for a,b in zip(p,q))))
            pg,ph,pt=loc(gm),loc(heat[0]),loc(th)
            row=f.measure(tn);row.update(n_gamma=int(G.sum()),theta_max=float(th.max()),grad_max=float(gm.max()),heat_max=float(heat[0].max()),
                fS_max=float(fS.max()),fT_max=float(fT.max()),fE_max=float(fE.max()),
                j_gamma_mean=float(j[G].mean()) if G.any() else None,j_gamma_max=float(j[G].max()) if G.any() else None,j_domain_max=float(j.max()),
                jabs_pct_gamma=float((np.abs(j)[G].mean()>np.abs(j)).mean()) if G.any() else None,
                d_theta_grad=dist(pt,pg),d_theta_heat=dist(pt,ph),d_heat_grad=dist(ph,pg),
                dissipated=loss,sink_energy=sink,kolmogorov_k=float((d/dt/nu**3)**.25))
            rows.append(row)
    if ckpt and last<round(duration/dt):
        np.savez(ckpt,u=f.u,th=f.th,heat=heat,loss=loss,sink=sink,E_init=E_init,rows=np.array(rows,dtype=object),i=last,cooled=cooled);print('checkpoint at step',last,flush=True);return None
    err=float(abs(f.energy(f.u)+heat.mean()+sink+cooled-E_init))
    res=dict(n=n,nu=nu,kappa=kappa,dt=dt,E0=E0,total_error=err,sink_energy=sink,rows=rows,
             peak_vorticity=max(r['max_vorticity'] for r in rows),peak_grad=max(r['grad_max'] for r in rows),
             peak_theta=max(r['theta_max'] for r in rows),peak_j_gamma=max((r['j_gamma_max'] or 0) for r in rows),
             first_gamma=next((r['t'] for r in rows if r['n_gamma']>0),None),max_gamma=max(r['n_gamma'] for r in rows))
    print(f"n={n} nu={nu} kappa={kappa}: omega_pk={res['peak_vorticity']:.2f} grad_pk={res['peak_grad']:.2f} k_eta~{max(r['kolmogorov_k'] for r in rows):.1f} "
          f"theta_pk={res['peak_theta']:.3f} first Gamma={res['first_gamma']} Gamma max={res['max_gamma']} peak j@G={res['peak_j_gamma']:.3f} "
          f"fS/fT/fE max={max(r['fS_max'] for r in rows):.2f}/{max(r['fT_max'] for r in rows):.2f}/{max(r['fE_max'] for r in rows):.2f} sink={sink:.2e}/{E_init:.3f} cfl_max={max(r['cfl'] for r in rows):.3f} err={err:.1e}",flush=True)
    return res

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--n',type=int,default=32);ap.add_argument('--nu',type=float,nargs='+',default=[.02])
    ap.add_argument('--kappa',type=float,nargs='+',default=[0.]);ap.add_argument('--dt',type=float,default=.01);ap.add_argument('--E0',type=float,default=.15);ap.add_argument('--stop',type=float,default=None);ap.add_argument('--ref',type=float,default=None);ap.add_argument('--cool',type=float,default=0.)
    a=ap.parse_args();out=[]
    for nu in a.nu:
        for k in a.kappa:
            r=run(a.n,nu,k,a.dt,E0=a.E0,stop=a.stop,ckpt=f'theta_tubes_ckpt_{a.n}_{nu}_{k}_{a.E0}_{a.dt}_ref{a.ref}_cool{a.cool}.npz',ref=a.ref,cool=a.cool)
            if r is None: continue
            out.append(r)
            Path(__file__).with_name(f"theta_tubes_{a.n}_nu{'_'.join(map(str,a.nu))}_k{'_'.join(map(str,a.kappa))}_E{a.E0}_ref{a.ref}_cool{a.cool}_results.json").write_text(json.dumps(out,indent=1)+'\n')
