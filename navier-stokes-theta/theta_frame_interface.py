"""Interface criterion built only from the frame geometry measured under load:
  a  = alignment of vorticity with a strain axis           (locked octants)
  o  = 1 - cos(H,S)   pressure frame orthogonal to strain    (the right angle)
  c  = cot(phi)/(1+cot(phi))   stretch beats rotation (>1/2 when cot>1)
  A  = (pressure rate - total rate)^+ / pressure rate        (third-ring anchoring)
  F  = a * o * c * A  in [0,1]
Compared as LOCATORS of the load (top-1% gradient cells) against C2 (alignment-gated
modified theta), r_E, and alignment alone: Jaccard overlap of each score's top-1% with
the gradient top-1%, plus volume above absolute thresholds.  Tubes, 48^3, nu .02."""
import argparse,json,numpy as np
from pathlib import Path
from theta_three import ThreeFlow
from theta_tubes import tubes
from theta_third_ring import third_ring
def jacc(A,B): return float((A&B).sum()/max((A|B).sum(),1))
def run(E0,dt=.01,nu=.02,n=48,duration=2.):
    f=ThreeFlow(n,'control',dt,0.);f.nu=nu;f.force*=0;f.u,x,y,z=tubes(f,n,E0=E0);f.heat=np.zeros((n,n,n));rows=[]
    for i in range(round(duration/dt)):
        f.step(False)
        if (i+1)%round(.4/dt)==0:
            rates,cosHS,tanphi,d=third_ring(f);L=d['live'];a=d['align']
            o=1-cosHS;cot=1/np.maximum(tanphi,1e-9);c=cot/(1+cot)
            A=np.maximum(rates['pressure']-rates['total'],0)/np.maximum(rates['pressure'],1e-12)
            F=a*o*c*A
            fE=1+.96*np.log(d['rE']);fR=1+.6*np.sign(np.log(d['rR']))*np.sqrt(np.abs(np.log(d['rR'])));C2=1+(fE*fR-1)*a
            gm=d['gm'];topG=L&(gm>=np.quantile(gm[L],.99))
            def top1(s): return L&(s>=np.quantile(s[L],.99))
            row=dict(t=(i+1)*dt,grad_max=float(gm.max()),
                jaccard=dict(F=jacc(top1(F),topG),C2=jacc(top1(C2),topG),rE=jacc(top1(d['rE']),topG),align=jacc(top1(a),topG),o=jacc(top1(o),topG),A=jacc(top1(A),topG)),
                F_top_vs_rest=(float(np.median(F[topG])),float(np.median(F[L&~topG]))),
                vol_F_gt_half=float((L&(F>.5)).mean()),vol_C2_gt_pi=float((L&(C2>np.pi)).mean()),
                frac_topG_with_F_gt_half=float((F[topG]>.5).mean()),frac_topG_with_C2_gt_pi=float((C2[topG]>np.pi).mean()),
                F_p99=float(np.quantile(F[L],.99)))
            rows.append(row);j=row['jaccard']
            print(f"t={row['t']:.1f} grad={row['grad_max']:.1f} | Jaccard with load: F {j['F']:.2f} C2 {j['C2']:.2f} rE {j['rE']:.2f} align {j['align']:.2f} orth {j['o']:.2f} anchor {j['A']:.2f} | F med top/rest {row['F_top_vs_rest'][0]:.2f}/{row['F_top_vs_rest'][1]:.2f} | vol F>.5 {row['vol_F_gt_half']:.4f} vol C2>pi {row['vol_C2_gt_pi']:.4f} | load cells with F>.5 {row['frac_topG_with_F_gt_half']:.2f}, C2>pi {row['frac_topG_with_C2_gt_pi']:.2f}",flush=True)
    return dict(E0=E0,nu=nu,rows=rows)
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--E0',type=float,default=.15);ap.add_argument('--dt',type=float,default=.01);a=ap.parse_args()
    res=run(a.E0,a.dt);Path(__file__).with_name(f'theta_frame_interface_E{a.E0}_results.json').write_text(json.dumps(res,indent=1)+'\n')
