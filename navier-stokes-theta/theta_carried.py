"""The carried weight.  Jonathan: the weight is distributed between the base plane,
the walls and the third ring, and shifts as the ring lifts the walls.
A(x) = (pressure-driven frame rotation - total) / pressure-driven  in [0,1]: the share of
the strain frame's rotation carried by the vorticity ring rather than the pressure base
(measured ~0 in the bulk, ~0.4-0.5 under load).  Carried weight
    w(x) = w_base + (w_wall - w_base) A(x),   w_base = 0.4 (Table 1), w_wall = 0.96 (entropy weight).
Static theta_s = 1 + w ln r_E for three weightings: fixed .96, fixed .7, carried.  Report, per
time: Gamma_static = {theta_s >= pi} volume, its Jaccard with the top-1% gradient cells, and the
fraction of those cells covered.  Isothermal tubes, 64^3, nu .02."""
import argparse,json,numpy as np
from pathlib import Path
from theta_three import ThreeFlow
from theta_tubes import tubes
from theta_third_ring import third_ring
def jacc(A,B): return float((A&B).sum()/max((A|B).sum(),1))
def run(E0,nu=.02,n=64,dt=.005,duration=1.6):
    f=ThreeFlow(n,'control',dt,0.);f.nu=nu;f.force*=0;f.u,x,y,z=tubes(f,n,E0=E0);f.heat=np.zeros((n,n,n));rows=[]
    for i in range(round(duration/dt)):
        f.step(False)
        if (i+1)%round(.2/dt)==0:
            rates,cosHS,tanphi,d=third_ring(f);L=d['live'];gm=d['gm'];top=L&(gm>=np.quantile(gm[L],.99))
            A=np.clip((rates['pressure']-rates['total'])/np.maximum(rates['pressure'],1e-12),0,1);A=np.where(L,A,0.)
            lnr=np.log(d['rE'])
            W={'fixed_0.96':0.96,'fixed_0.7':0.7,'carried':0.4+0.56*A}
            out={}
            for k,w in W.items():
                th=1+w*lnr;G=L&(th>=np.pi)
                out[k]=dict(gamma_frac=float(G.mean()),jaccard=jacc(G,top),coverage=float((G&top).sum()/max(top.sum(),1)),theta_p99=float(np.quantile(th[L],.99)),theta_max=float(th[L].max()))
            row=dict(t=(i+1)*dt,grad_max=float(gm.max()),A_load=float(np.median(A[top])),A_bulk=float(np.median(A[L&~top])),w_load=float(np.median((0.4+0.56*A)[top])),w_bulk=float(np.median((0.4+0.56*A)[L&~top])),weightings=out)
            rows.append(row)
            print(f"E0={E0} t={row['t']:.1f} grad={row['grad_max']:.1f} A load/bulk={row['A_load']:.2f}/{row['A_bulk']:.2f} w load/bulk={row['w_load']:.2f}/{row['w_bulk']:.2f} | "+' | '.join(f"{k}: vol {v['gamma_frac']*100:.3f}% J {v['jaccard']:.2f} cov {v['coverage']:.2f} p99 {v['theta_p99']:.2f}" for k,v in out.items()),flush=True)
    return dict(E0=E0,nu=nu,n=n,rows=rows)
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--E0',type=float,default=.15);a=ap.parse_args()
    res=run(a.E0);Path(__file__).with_name(f'theta_carried_E{a.E0}_results.json').write_text(json.dumps(res,indent=1)+'\n')
