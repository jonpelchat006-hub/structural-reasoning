"""Gyroscopic gate on the two kinetic planes.  Frame rotation rate g = tilt/|S|_F
(dimensionless: how fast the vorticity direction turns relative to the strain rate);
alignment a in [0,1] (1 = locked octants).  Candidates, all with the MODIFIED
no-root magnitude weight w p = .96 (labelled as such) and direction weight .6:
  C1 = fE fR                     (ungated)
  C2 = 1 + (fE fR - 1) a         (walls where locked)
  C3 = 1 + (fE fR - 1)(1 - a)    (load where turning)
Reported at the top-1% gradient cells vs the rest, E0 sweep.  Isothermal tubes, 48^3, nu .02."""
import argparse,json,numpy as np
from pathlib import Path
from theta_planes2 import direction_plane
from theta_three import ThreeFlow
from theta_tubes import tubes
from vortex3d import real, cross
def run(E0,nu=.02,n=48,dt=.01,duration=2.):
    f=ThreeFlow(n,'control',dt,0.);f.nu=nu;f.force*=0;f.u,x,y,z=tubes(f,n,E0=E0);f.heat=np.zeros((n,n,n));rows=[]
    for i in range(round(duration/dt)):
        f.step(False)
        if (i+1)%round(.2/dt)==0:
            d=direction_plane(f);L=d['live'];a=d['align']
            G=np.array([f.grad(f.u[k]) for k in range(3)]);Sf=np.sqrt(np.sum((.5*(G+G.transpose(1,0,2,3,4)))**2,axis=(0,1)))
            g=d['tilt']/np.maximum(Sf,1e-12)
            fE=1+.96*np.log(d['rE']);fR=1+.6*np.sign(np.log(d['rR']))*np.sqrt(np.abs(np.log(d['rR'])))
            C1=fE*fR;C2=1+(C1-1)*a;C3=1+(C1-1)*(1-a)
            top=d['gm']>=np.quantile(d['gm'][L],.99);rest=L&~top;top=L&top
            st=lambda q:(float(q[top].mean()),float(q[rest].mean()),float(np.quantile(q[L],.99)))
            rows.append(dict(t=(i+1)*dt,grad_max=float(d['gm'].max()),
                align=st(a),locked_frac_top=float((a[top]>.9).mean()),locked_frac_rest=float((a[rest]>.9).mean()),
                g=st(g),C1=st(C1),C2=st(C2),C3=st(C3),fE=st(fE),fR=st(fR)))
            r=rows[-1];print(f"t={r['t']:.1f} grad={r['grad_max']:.1f} | align top/rest={r['align'][0]:.2f}/{r['align'][1]:.2f} locked>.9 top/rest={r['locked_frac_top']:.2f}/{r['locked_frac_rest']:.2f} | g top/rest={r['g'][0]:.2f}/{r['g'][1]:.2f} | C1 top/rest/p99={r['C1'][0]:.2f}/{r['C1'][1]:.2f}/{r['C1'][2]:.2f} C2={r['C2'][0]:.2f}/{r['C2'][1]:.2f}/{r['C2'][2]:.2f} C3={r['C3'][0]:.2f}/{r['C3'][1]:.2f}/{r['C3'][2]:.2f}",flush=True)
    return dict(E0=E0,nu=nu,n=n,dt=dt,rows=rows)
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--E0',type=float,default=.15);ap.add_argument('--dt',type=float,default=.01);a=ap.parse_args()
    res=run(a.E0,dt=a.dt);Path(__file__).with_name(f'theta_gyro_E{a.E0}_results.json').write_text(json.dumps(res,indent=1)+'\n')
