"""(1) nu sweep: how does the plane exchange j = -u.grad Pi at the interface
scale with the sharpest gradients?  (2) J as a real sink: at interface cells
remove power kappa * j^+ from the normal plane (momentum sink
-(kappa j^+/|u|^2) u chi_Gamma), booked in the energy budget.
Passive theta (beta=0) unless stated; wall 3, floor -pi; 32^3, dt .02, t<=3.
Run: python theta_J_sweep.py --nu 0.03 --kappa 0 | --kappa 0.1416"""
import argparse,json,numpy as np
from pathlib import Path
from theta_three import build, PI
from ring_power import kick
from thermal_loop import face_velocity, heat_step
from vortex3d import real, fft, cross
from theta_kinetic import sreal, sfft

def plane_exchange(f):
    u=real(f.u);w=real(1j*cross(f.k,f.u))
    N=fft(cross(u,w))*f.mask;divN=np.sum(1j*f.k*N,axis=0);Pi_h=-divN*f.inv
    gPi=np.array([sreal(1j*f.k[j]*Pi_h) for j in range(3)])
    return -np.sum(u*gPi,axis=0),u

def run(nu,kappa,n=32,dt=.02,duration=3.,gamma_level=3.):
    f,direction,x,y,z=build(n,0.,dt,wall=3.,floor=-PI);f.nu=nu
    rates=np.array([0.]);heat=np.zeros((1,n,n,n));h=2*np.pi/n
    work=loss=sink=0.;rows=[]
    for i in range(round(duration/dt)):
        t=(i+.5)*dt;e=.04*min(t/.2,1)*dt
        f.heat=heat[0];kick(f,direction,e/2);prev=f.u.copy();_,d=f.step(False);mid=(prev+f.u)/2;kick(f,direction,e/2)
        work+=e;loss+=d
        # J sink: remove kappa*j^+ power on Gamma for this step
        if kappa:
            th=f.clip(sreal(f.th));G=th>=gamma_level
            if G.any():
                j,u=plane_exchange(f);jp=np.where(G,np.maximum(j,0),0.)
                u2=np.sum(u*u,axis=0);fac=np.where(u2>1e-12,np.minimum(kappa*jp*dt/np.maximum(u2/2,1e-12),1.),0.)
                # remove energy kappa*jp*dt from each Gamma cell: scale |u| so that KE drops by that amount
                s=np.sqrt(np.maximum(1-fac,0.))
                before=f.energy(f.u);f.u=f.project(fft(u*s[None]));after=f.energy(f.u)
                sink+=before-after
        g=np.array([real(1j*f.k[j]*mid) for j in range(3)]);q=.5*f.nu*np.sum((g+g.swapaxes(0,1))**2,axis=(0,1))
        if q.mean()>0:q*=d/(dt*q.mean())
        heat,_=heat_step(heat,face_velocity(mid,h),q,dt,h,rates);f.heat=heat[0]
        tn=(i+1)*dt
        if (i+1)%5==0:
            th=f.clip(sreal(f.th));G=th>=gamma_level;j,u=plane_exchange(f)
            gradmax=float(np.sqrt(np.sum(g*g,axis=(0,1))).max());row=f.measure(tn)
            row.update(n_gamma=int(G.sum()),j_gamma_mean=float(j[G].mean()) if G.any() else None,
                       j_gamma_max=float(j[G].max()) if G.any() else None,j_domain_absmean=float(np.abs(j).mean()),
                       j_domain_max=float(j.max()),grad_max=gradmax,heat_max=float(heat[0].max()),
                       theta_max=float(th.max()),sink_energy=sink,input_energy=work,dissipated=loss,
                       kolmogorov_k=float((d/dt/nu**3)**.25))
            rows.append(row)
    total_err=float(abs(f.energy(f.u)+heat.mean()+sink-work))
    res=dict(nu=nu,kappa=kappa,n=n,dt=dt,total_error=total_err,sink_energy=sink,rows=rows,
             peak_j_gamma=max((r['j_gamma_max'] or 0) for r in rows),peak_grad=max(r['grad_max'] for r in rows),
             peak_vorticity=max(r['max_vorticity'] for r in rows),first_gamma=next((r['t'] for r in rows if r['n_gamma']>0),None))
    r=rows[-1]
    print(f"nu={nu} kappa={kappa}: E={r['energy']:.5f} omega_pk={res['peak_vorticity']:.3f} grad_pk={res['peak_grad']:.3f} k_eta~{max(x['kolmogorov_k'] for x in rows):.1f} "
          f"peak j@Gamma={res['peak_j_gamma']:.3f} j_dom_max={max(x['j_domain_max'] for x in rows):.3f} Gamma cells max={max(x['n_gamma'] for x in rows)} "
          f"sink={sink:.2e} of input {work:.3f}  err={total_err:.1e}",flush=True)
    return res

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--nu',type=float,nargs='+',default=[.03]);ap.add_argument('--kappa',type=float,nargs='+',default=[0.])
    a=ap.parse_args();out=[]
    for nu in a.nu:
        for k in a.kappa:
            out.append(run(nu,k));Path(__file__).with_name(f"theta_J_sweep_nu{'_'.join(str(v) for v in a.nu)}_k{'_'.join(str(v) for v in a.kappa)}_results.json").write_text(json.dumps(out,indent=1)+'\n')
