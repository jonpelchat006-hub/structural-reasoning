"""Form D with the degeneracy weight carried per cell or per bubble.
theta_s = 1 + w(x) ln r_E,  w = 0.4 + 0.56|s*|  (LINES result),
  --weight fixed  : w = 0.96 everywhere (original Form D)
  --weight cell   : w from the local |s*|
  --weight bubble : inside each Gamma bubble (from the previous step's theta, dilated one cell) w = bubble mean of the
                    cell weight; outside bubbles the cell weight. Gamma is the carrier of the weight, as in the third-ring picture.
Same protocol as the Re-trend runs: n=64, E0=.6, kappa=1, tau=.02, T=1.6, nu = .02 / .01.
"""
import argparse,json,numpy as np
from pathlib import Path
from scipy import ndimage
from vortex3d import fft,real,cross
from theta_kinetic import sreal
from theta_formD import FormD,PI
from theta_tubes import tubes
from theta_J_sweep import plane_exchange
from theta_planes2 import direction_plane
from theta_faces import periodic_label
class FormDW(FormD):
    weight='fixed';wfield=None
    def theta_static(self,Pp,Dw):
        eps=self.delta*Dw.mean();w=.96 if self.wfield is None else self.wfield
        return 1+w*np.log((Pp+eps)/(Dw+eps))
def sstar_field(f):
    G=np.array([f.grad(f.u[k]) for k in range(3)]);S=.5*(G+G.transpose(1,0,2,3,4))
    lam=np.linalg.eigvalsh(np.moveaxis(S,(0,1),(-2,-1)));l3,l2,l1=lam[...,0],lam[...,1],lam[...,2]
    mag=np.sqrt(l1**2+l2**2+l3**2);return -3*np.sqrt(6)*l1*l2*l3/np.maximum(mag**3,1e-30)
def run(E0,kappa,weight,nu=.02,n=64,dt=.005,duration=1.6,tau=.02):
    f=FormDW(n,'control',dt,0.);f.nu=nu;f.force*=0;f.wall=3.;f.floor=-PI;f.advect=True;f.tau=tau;f.weight=weight
    f.u,x,y,z=tubes(f,n,E0=E0);f.heat=np.zeros((n,n,n))
    E_init=f.energy(f.u);loss=sink=0.;rows=[];nb_hist=[];i0=0
    ck=Path(__file__).with_name(f'ckpt_weight_{weight}_n{n}_nu{nu}_k{kappa}.npz')
    if ck.exists():
        z=np.load(ck,allow_pickle=True);f.u=z['u'];f.th=z['th'];loss=float(z['loss']);sink=float(z['sink']);E_init=float(z['E_init']);rows=list(z['rows']);nb_hist=list(z['nb']);i0=int(z['i'])+1
        print(f'resumed at step {i0}',flush=True)
    for i in range(i0,round(duration/dt)):
        if weight!='fixed':
            wc=.4+.56*np.abs(sstar_field(f))
            if weight=='bubble':
                G=f.clip(sreal(f.th))>=3.
                if G.any():
                    lab=periodic_label(ndimage.binary_dilation(G));ids=np.unique(lab[lab>0])
                    wb=wc.copy()
                    for c in ids: m=lab==c;wb[m]=wc[m].mean()
                    wc=wb;nb_hist.append(len(ids))
            f.wfield=wc
        _,d=f.step(False);loss+=d
        th=f.clip(sreal(f.th));G=th>=3.
        if kappa and G.any():
            j,u=plane_exchange(f);dd=direction_plane(f);a=dd['align']
            jp=np.where(G,np.maximum(j,0)*a,0.);u2=np.sum(u*u,axis=0)
            fac=np.where(u2>1e-12,np.minimum(kappa*jp*dt/np.maximum(u2/2,1e-12),1.),0.)
            b=f.energy(f.u);f.u=f.project(fft(u*np.sqrt(np.maximum(1-fac,0))[None]));sink+=b-f.energy(f.u)
        if (i+1)%round(.2/dt)==0:
            th=f.clip(sreal(f.th));G=th>=3.;dd=direction_plane(f);L=dd['live'];gm=dd['gm']
            top=L&(gm>=np.quantile(gm[L],.99))
            row=f.measure((i+1)*dt);row.update(n_gamma=int(G.sum()),grad_max=float(gm.max()),
                gamma_in_top1=float((G&top).sum()/max(G.sum(),1)),top1_in_gamma=float((G&top).sum()/max(top.sum(),1)),
                w_gamma=float(f.wfield[G].mean()) if (G.any() and f.wfield is not None) else None,
                w_bulk=float(f.wfield[L&~G].mean()) if f.wfield is not None else None,
                n_bubbles=int(np.median(nb_hist[-40:])) if nb_hist else None,sink=sink,dissipated=loss)
            rows.append(row)
            np.savez(ck,u=f.u,th=f.th,loss=loss,sink=sink,E_init=E_init,rows=np.array(rows,dtype=object),nb=np.array(nb_hist),i=i)
            print(f"[{weight} nu={nu}] t={row['t']:.1f} grad={row['grad_max']:.1f} Omega={row['enstrophy']:.4f} | Gamma {row['n_gamma']} cells (bubbles {row['n_bubbles']}) {row['gamma_in_top1']:.2f} in top1 / {row['top1_in_gamma']:.2f} of top1 | w Gamma/bulk {row['w_gamma']}/{row['w_bulk']} | sink {sink:.2e}",flush=True)
    err=float(abs(f.energy(f.u)+loss+sink-E_init))
    res=dict(E0=E0,kappa=kappa,nu=nu,n=n,dt=dt,weight=weight,total_error=err,sink=sink,peak_enstrophy=max(r['enstrophy'] for r in rows),peak_vorticity=max(r['max_vorticity'] for r in rows),rows=rows)
    ck.unlink(missing_ok=True)
    print(f"DONE weight={weight} nu={nu} kappa={kappa}: peak Omega {res['peak_enstrophy']:.4f} peak omega {res['peak_vorticity']:.2f} sink {sink:.3e} ({sink/E_init:.2%}) err {err:.1e}",flush=True)
    return res
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--weight',default='cell');ap.add_argument('--nu',type=float,default=.02);ap.add_argument('--kappa',type=float,default=1.);ap.add_argument('--n',type=int,default=64);ap.add_argument('--E0',type=float,default=.6)
    a=ap.parse_args();res=run(a.E0,a.kappa,a.weight,nu=a.nu,n=a.n)
    Path(__file__).with_name(f'theta_formD_weight_{a.weight}_n{a.n}_nu{a.nu}_k{a.kappa}_results.json').write_text(json.dumps(res,indent=1)+'\n')
