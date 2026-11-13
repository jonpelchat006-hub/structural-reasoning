"""Form D (proposed 15 Sep 2026): magnitude-plane nucleation, geometry-gated sink, floor -pi.
  theta_s = 1 + 0.96 ln r_E   (MODIFIED weight: entropy factor's w p on the magnitude plane, no root)
  clip theta_s and theta to [-pi, pi]; wall at 3 (restoring beyond |theta| > 3); relax-diffuse-advect.
  Gamma = theta >= pi.  J sink on Gamma removes power kappa * a * j^+  (a = alignment gate,
  j = -u.grad Pi the pressure-plane exchange), booked in the energy budget.
  Q-R diagnostic: Q = |w|^2/4 - |S|^2/2, R = -det(grad u); Vieillefosse discriminant
  D = 27 R^2/4 + Q^3 (restricted-Euler blow-up heads to D -> 0 with R > 0).
Isothermal antiparallel tubes, 48^3.  Run: python theta_formD.py --E0 0.15 --kappa 0|1 [--dt 0.005 --duration 1.6]"""
import argparse,json,numpy as np
from pathlib import Path
from theta_three import ThreeFlow, PI
from theta_tubes import tubes
from theta_planes2 import direction_plane
from theta_J_sweep import plane_exchange
from vortex3d import real, fft, cross
from theta_kinetic import sreal, sfft

class FormD(ThreeFlow):
    def theta_static(self,Pp,Dw):
        eps=self.delta*Dw.mean();return 1+.96*np.log((Pp+eps)/(Dw+eps))

def run(E0,kappa,nu=.02,n=48,dt=.01,duration=2.,wall=3.,advect=True,tau=.1):
    f=FormD(n,'control',dt,0.);f.nu=nu;f.force*=0;f.wall=wall;f.floor=-PI;f.advect=advect;f.tau=tau;f.u,x,y,z=tubes(f,n,E0=E0);f.heat=np.zeros((n,n,n))
    E_init=f.energy(f.u);loss=sink=0.;rows=[]
    for i in range(round(duration/dt)):
        _,d=f.step(False);loss+=d
        th=f.clip(sreal(f.th));G=th>=3.
        if kappa and G.any():
            j,u=plane_exchange(f);dd=direction_plane(f);a=dd['align']
            jp=np.where(G,np.maximum(j,0)*a,0.);u2=np.sum(u*u,axis=0)
            fac=np.where(u2>1e-12,np.minimum(kappa*jp*dt/np.maximum(u2/2,1e-12),1.),0.)
            b=f.energy(f.u);f.u=f.project(fft(u*np.sqrt(np.maximum(1-fac,0))[None]));sink+=b-f.energy(f.u)
        if (i+1)%round(.2/dt)==0:
            th=f.clip(sreal(f.th));G=th>=3.;dd=direction_plane(f);L=dd['live'];gm=dd['gm'];j,u=plane_exchange(f)
            Gr=np.array([f.grad(f.u[k]) for k in range(3)]);S=.5*(Gr+Gr.transpose(1,0,2,3,4));w=real(1j*cross(f.k,f.u))
            Q=np.sum(w*w,axis=0)/4-np.sum(S*S,axis=(0,1))/2
            A=np.moveaxis(Gr,(0,1),(-2,-1));R=-np.linalg.det(A);Dv=27*R*R/4+Q**3
            top=L&(gm>=np.quantile(gm[L],.99))
            def st(m): return None if not m.any() else dict(Q=float(np.median(Q[m])),R=float(np.median(R[m])),D=float(np.median(Dv[m])),fracRpos=float((R[m]>0).mean()),fracDneg=float((Dv[m]<0).mean()))
            row=f.measure((i+1)*dt);row.update(n_gamma=int(G.sum()),theta_max=float(th.max()),theta_min=float(th.min()),grad_max=float(gm.max()),
                gamma_in_top1=float((G&top).sum()/max(G.sum(),1)),top1_in_gamma=float((G&top).sum()/max(top.sum(),1)),
                j_gamma_mean=float(j[G].mean()) if G.any() else None,sink=sink,dissipated=loss,
                QR_gamma=st(G),QR_top=st(top),QR_bulk=st(L&~top))
            rows.append(row)
            print(f"t={row['t']:.1f} grad={row['grad_max']:.1f} Omega={row['enstrophy']:.4f} | Gamma {row['n_gamma']} cells, {row['gamma_in_top1']:.2f} of Gamma in top-1% grad, {row['top1_in_gamma']:.2f} of top-1% in Gamma | theta [{row['theta_min']:.2f},{row['theta_max']:.2f}] | j@G {row['j_gamma_mean'] if row['j_gamma_mean'] is None else round(row['j_gamma_mean'],2)} sink {sink:.2e} | QR top: R>0 {row['QR_top']['fracRpos']:.2f} D<0 {row['QR_top']['fracDneg']:.2f} bulk: R>0 {row['QR_bulk']['fracRpos']:.2f} D<0 {row['QR_bulk']['fracDneg']:.2f}",flush=True)
    err=float(abs(f.energy(f.u)+loss+sink-E_init))
    res=dict(E0=E0,kappa=kappa,nu=nu,n=n,dt=dt,total_error=err,sink=sink,peak_enstrophy=max(r['enstrophy'] for r in rows),peak_vorticity=max(r['max_vorticity'] for r in rows),rows=rows)
    print(f"E0={E0} kappa={kappa}: peak Omega {res['peak_enstrophy']:.4f} peak omega {res['peak_vorticity']:.2f} sink {sink:.3e} ({sink/E_init:.2%} of E0) err {err:.1e}",flush=True)
    return res
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--E0',type=float,default=.15);ap.add_argument('--kappa',type=float,default=0.);ap.add_argument('--dt',type=float,default=.01);ap.add_argument('--duration',type=float,default=2.);ap.add_argument('--nowall',action='store_true');ap.add_argument('--eulerian',action='store_true');ap.add_argument('--tau',type=float,default=.1);ap.add_argument('--nu',type=float,default=.02);ap.add_argument('--n',type=int,default=48)
    a=ap.parse_args();res=run(a.E0,a.kappa,nu=a.nu,n=a.n,dt=a.dt,duration=a.duration,wall=None if a.nowall else 3.,advect=not a.eulerian,tau=a.tau)
    Path(__file__).with_name(f'theta_formD_n{a.n}_nu{a.nu}_E{a.E0}_k{a.kappa}{"_nowall" if a.nowall else ""}{"_eulerian" if a.eulerian else ""}_tau{a.tau}_results.json').write_text(json.dumps(res,indent=1)+'\n')
