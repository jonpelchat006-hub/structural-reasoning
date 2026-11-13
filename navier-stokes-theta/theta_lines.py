"""Three lines from the origin: the strain principal axes with eigenvalues l1>=l2>=l3 (sum 0).
Degeneracy ('lines lying on top of each other'): strain state s* = -3 sqrt6 l1 l2 l3 / (l1^2+l2^2+l3^2)^{3/2}
in [-1,1] (Lund-Rogers): +1 axisymmetric extension (l2=l3, tube), -1 axisymmetric compression (l1=l2, sheet).
Weight transfer between planes: beta = (l2-l3)/(l1-l3) in [0,1], where the middle line sits between the extremes.
Anchor: which axis the vorticity direction lies along (index of max |xi.e_i|).
Candidate carried weights: w_deg = 0.4 + 0.56 |s*|, w_beta = 0.4 + 0.56 beta, w_beta' = 0.4 + 0.56 (1-beta).
Static Gamma test as in theta_carried.py.  Tubes 64^3 nu .02."""
import argparse,json,numpy as np
from pathlib import Path
from theta_three import ThreeFlow
from theta_tubes import tubes
from theta_planes2 import direction_plane
def jacc(A,B): return float((A&B).sum()/max((A|B).sum(),1))
def run(E0,nu=.02,n=64,dt=.005,duration=1.6):
    f=ThreeFlow(n,'control',dt,0.);f.nu=nu;f.force*=0;f.u,x,y,z=tubes(f,n,E0=E0);f.heat=np.zeros((n,n,n));rows=[]
    for i in range(round(duration/dt)):
        f.step(False)
        if (i+1)%round(.2/dt)==0:
            d=direction_plane(f);L=d['live'];gm=d['gm'];top=L&(gm>=np.quantile(gm[L],.99));bulk=L&~top
            G=np.array([f.grad(f.u[k]) for k in range(3)]);S=.5*(G+G.transpose(1,0,2,3,4))
            lam,E=np.linalg.eigh(np.moveaxis(S,(0,1),(-2,-1)))      # ascending: l3<=l2<=l1
            l3,l2,l1=lam[...,0],lam[...,1],lam[...,2]
            mag=np.sqrt(l1**2+l2**2+l3**2);sstar=-3*np.sqrt(6)*l1*l2*l3/np.maximum(mag**3,1e-30)
            beta=(l2-l3)/np.maximum(l1-l3,1e-12)
            w=d['wm'];xi=np.moveaxis(np.array([f.u.real*0]*3),0,-1) # placeholder shape
            wv=np.moveaxis(np.array([np.fft.ifftn(1j*(f.k[(k+1)%3]*f.u[(k+2)%3]-f.k[(k+2)%3]*f.u[(k+1)%3])).real for k in range(3)]),0,-1)
            xiv=wv/np.maximum(np.linalg.norm(wv,axis=-1,keepdims=True),1e-12)
            proj=np.abs(np.einsum('...i,...ij->...j',xiv,E))       # |xi.e_j|, j=0 (l3),1 (l2),2 (l1)
            anchor=np.argmax(proj,axis=-1)
            lnr=np.log(d['rE'])
            W={'w_deg':0.4+0.56*np.abs(sstar),'w_beta':0.4+0.56*beta,'w_1-beta':0.4+0.56*(1-beta),'fixed_0.7':0.7}
            out={}
            for k,wt in W.items():
                th=1+wt*lnr;Gm=L&(th>=np.pi)
                out[k]=dict(gamma_frac=float(Gm.mean()),jaccard=jacc(Gm,top),coverage=float((Gm&top).sum()/max(top.sum(),1)),w_load=float(np.median(np.broadcast_to(wt,lnr.shape)[top])),w_bulk=float(np.median(np.broadcast_to(wt,lnr.shape)[bulk])))
            row=dict(t=(i+1)*dt,grad_max=float(gm.max()),
                sstar=(float(np.median(sstar[top])),float(np.median(sstar[bulk]))),abs_sstar=(float(np.median(np.abs(sstar)[top])),float(np.median(np.abs(sstar)[bulk]))),
                beta=(float(np.median(beta[top])),float(np.median(beta[bulk]))),
                anchor_load=[float((anchor[top]==j).mean()) for j in (2,1,0)],anchor_bulk=[float((anchor[bulk]==j).mean()) for j in (2,1,0)],
                ratios_load=[float(np.median((l1/np.maximum(mag,1e-12))[top])),float(np.median((l2/np.maximum(mag,1e-12))[top])),float(np.median((l3/np.maximum(mag,1e-12))[top]))],
                weightings=out)
            rows.append(row)
            print(f"E0={E0} t={row['t']:.1f} | s* load/bulk={row['sstar'][0]:+.2f}/{row['sstar'][1]:+.2f} |s*|={row['abs_sstar'][0]:.2f}/{row['abs_sstar'][1]:.2f} beta={row['beta'][0]:.2f}/{row['beta'][1]:.2f} | anchor load (l1,l2,l3)={[round(v,2) for v in row['anchor_load']]} bulk={[round(v,2) for v in row['anchor_bulk']]} | "+' | '.join(f"{k}: w {v['w_load']:.2f}/{v['w_bulk']:.2f} vol {v['gamma_frac']*100:.3f}% J {v['jaccard']:.2f} cov {v['coverage']:.2f}" for k,v in out.items()),flush=True)
    return dict(E0=E0,nu=nu,n=n,rows=rows)
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--E0',type=float,default=.15);a=ap.parse_args()
    res=run(a.E0);Path(__file__).with_name(f'theta_lines_E{a.E0}_results.json').write_text(json.dumps(res,indent=1)+'\n')
