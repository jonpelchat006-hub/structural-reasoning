"""Three rings, three radii, three rates.
Strain frame = three principal lines (radii |lam_i|). The frame turns about each line at its own rate:
  Omega_k = M_ij/(lam_i-lam_j)  (i,j != k), M = pressure Hessian + W^2 in the strain frame.
Jonathan's question: do the rings turn at different rates (base fastest), do the ratios lock (rational -> periodic return
to the 'straight set-up') or drift (irrational)? And 'wrapping round to equal lengths' = |lam_i|=|lam_j| = degeneracy.
"""
import numpy as np,json,argparse
from pathlib import Path
from vortex3d import fft,real,cross
from theta_three import ThreeFlow
from theta_kinetic import sreal
from theta_tubes import tubes
from theta_planes2 import direction_plane
def rings(f):
    a=f.u;u=real(a);w=real(1j*cross(f.k,a))
    N=fft(cross(u,w))*f.mask;Pi_h=-np.sum(1j*f.k*N,axis=0)*f.inv
    H=np.array([[sreal(-f.k[i]*f.k[j]*Pi_h) for j in range(3)] for i in range(3)])
    G=np.array([f.grad(a[i]) for i in range(3)]);S=.5*(G+G.transpose(1,0,2,3,4));W=.5*(G-G.transpose(1,0,2,3,4))
    W2=np.einsum('ikxyz,kjxyz->ijxyz',W,W)
    Sm=np.moveaxis(S,(0,1),(-2,-1));lam,E=np.linalg.eigh(Sm)          # lam0<=lam1<=lam2 : compressive, intermediate, extensional
    M=np.moveaxis(H+W2,(0,1),(-2,-1));Mf=np.einsum('...ki,...kl,...lj->...ij',E,M,E)
    Sf=np.maximum(np.sqrt(np.sum(S*S,axis=(0,1))),1e-12)
    eps=1e-6*Sf.max()
    def rate(i,j):
        d=lam[...,i]-lam[...,j];return np.abs(Mf[...,i,j])/np.maximum(np.abs(d),eps)/Sf
    # ring k turns about line k, driven by the other two lines' coupling
    Om={'about_compressive(0)':rate(1,2),'about_intermediate(1)':rate(0,2),'about_extensional(2)':rate(0,1)}
    rad={'r0':np.abs(lam[...,0])/Sf,'r1':np.abs(lam[...,1])/Sf,'r2':np.abs(lam[...,2])/Sf}
    # vorticity anchor line
    wm=np.sqrt(np.sum(w*w,axis=0));xi=w/np.maximum(wm,1e-12)[None]
    anch=np.argmax(np.abs(np.einsum('ixyz,xyzik->xyzk',xi,E)),axis=-1)
    return Om,rad,anch,lam/Sf[...,None]
def nearest_rational(x,qmax=6):
    """distance from x to nearest p/q with q<=qmax, p/q in (0,1]"""
    best=np.full_like(x,9.)
    for q in range(1,qmax+1):
        for p in range(1,q+1):
            best=np.minimum(best,np.abs(x-p/q))
    return best
def run(E0,nu=.02,n=48,duration=2.,seed=0,dt=None):
    dt=dt or (.01 if n<=48 else .005);f=ThreeFlow(n,"control",dt,0.);f.nu=nu;f.force*=0;f.u,x,y,z=tubes(f,n,E0=E0);f.heat=np.zeros((n,n,n));rows=[]
    rng=np.random.default_rng(seed);i0=0
    ck=Path(__file__).with_name(f'ckpt_rings_E{E0}_n{n}.npz')
    if ck.exists():
        z=np.load(ck,allow_pickle=True);f.u=z['u'];rows=list(z['rows']);i0=int(z['i'])+1;print(f'resumed at step {i0}',flush=True)
    for i in range(i0,round(duration/dt)):
        f.step(False)
        if (i+1)%10==0 and (i+1)%round(.4/dt)!=0: np.savez(ck,u=f.u,rows=np.array(rows,dtype=object),i=i)
        if (i+1)%round(.4/dt)==0:
            Om,rad,anch,lam=rings(f);d=direction_plane(f);L=d['live']
            top=L&(d['gm']>=np.quantile(d['gm'][L],.99));rest=L&~top
            names=list(Om);A=np.stack([Om[k] for k in names],-1)
            row=dict(t=(i+1)*dt,grad_max=float(d['gm'].max()))
            for lab,m in (('load',top),('bulk',rest)):
                a=A[m];fast=np.argmax(a,-1)
                row[lab]=dict(
                    median_rate={k:float(np.median(a[:,j])) for j,k in enumerate(names)},
                    fastest_share={k:float(np.mean(fast==j)) for j,k in enumerate(names)},
                    radii={k:float(np.median(rad[k][m])) for k in rad},
                    anchor_share=[float(np.mean(anch[m]==j)) for j in range(3)])
                # ratio slow/fast of the two fastest rings, and rational-lock test vs shuffled control
                s=np.sort(a,-1);ratio=s[:,1]/np.maximum(s[:,2],1e-12)
                dist=nearest_rational(ratio);ctrl=nearest_rational(rng.uniform(0,1,ratio.size))
                row[lab]['ratio_2nd_over_fastest']=(float(np.median(ratio)),float(np.quantile(ratio,.25)),float(np.quantile(ratio,.75)))
                row[lab]['rational_lock']=dict(median_dist=float(np.median(dist)),control=float(np.median(ctrl)),
                                               frac_within_0p02=float(np.mean(dist<.02)),control_frac=float(np.mean(ctrl<.02)))
                # equal lengths: which pair of |lam| is closest, and is the fastest ring the one about the remaining line?
                r=np.stack([rad['r0'][m],rad['r1'][m],rad['r2'][m]],-1)
                pairgap=np.stack([np.abs(r[:,1]-r[:,2]),np.abs(r[:,0]-r[:,2]),np.abs(r[:,0]-r[:,1])],-1)  # gap of pair excluding line k
                closest=np.argmin(pairgap,-1)
                row[lab]['fastest_is_about_line_between_equal_pair']=float(np.mean(fast==closest))
                row[lab]['closest_pair_share']=[float(np.mean(closest==j)) for j in range(3)]
            rows.append(row);np.savez(ck,u=f.u,rows=np.array(rows,dtype=object),i=i)
            for lab in ('load','bulk'):
                R=row[lab];print(f"t={row['t']:.1f} {lab:4s} rate(about c/i/e)=" +
                    '/'.join(f"{R['median_rate'][k]:.2f}" for k in names)+
                    " fastest c/i/e="+'/'.join(f"{R['fastest_share'][k]:.2f}" for k in names)+
                    f" radii={R['radii']['r0']:.2f}/{R['radii']['r1']:.2f}/{R['radii']['r2']:.2f}"
                    f" ratio={R['ratio_2nd_over_fastest'][0]:.2f} lock={R['rational_lock']['frac_within_0p02']:.2f}(ctrl {R['rational_lock']['control_frac']:.2f})"
                    f" fast=eq-pair {R['fastest_is_about_line_between_equal_pair']:.2f}",flush=True)
    ck.unlink(missing_ok=True);return dict(E0=E0,nu=nu,n=n,rows=rows)
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--E0',type=float,default=.15);ap.add_argument('--n',type=int,default=48);ap.add_argument("--duration",type=float,default=2.);ap.add_argument("--dt",type=float,default=None)
    a=ap.parse_args();res=run(a.E0,n=a.n,duration=a.duration,dt=a.dt)
    Path(__file__).with_name(f'theta_rings_E{a.E0}_n{a.n}_results.json').write_text(json.dumps(res,indent=1)+'\n')
