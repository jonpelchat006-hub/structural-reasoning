"""Second orthogonal plane: the DIRECTION of vorticity (Constantin-Fefferman).
Magnitude plane:  r_E = (w.S.w)^+ / (nu |grad w|^2)          (production / destruction of |w|^2)
Direction plane:  r_R = |(I - xi xi^T) S xi| / (nu |grad xi|^2)  (strain tilting xi / viscous smoothing of xi)
  xi = w/|w|; alignment a = |xi.S xi| / |S xi| in [0,1] (1 = xi is a strain eigenvector: planes locked, octants)
Isothermal antiparallel tubes, 48^3, E0 sweep.  Run: python theta_planes2.py --E0 0.15 [--dt 0.005]"""
import argparse,json,numpy as np
from pathlib import Path
from theta_three import ThreeFlow, PI
from theta_tubes import tubes
from vortex3d import real, fft, cross
from theta_kinetic import sreal, sfft

def direction_plane(f):
    a=f.u;w=real(1j*cross(f.k,a));G=np.array([f.grad(a[i]) for i in range(3)]);S=.5*(G+G.transpose(1,0,2,3,4))
    wm=np.sqrt(np.sum(w*w,axis=0));live=wm>.05*wm.max()
    xi=w/np.maximum(wm,1e-12)[None]
    Sxi=np.einsum('ijxyz,jxyz->ixyz',S,xi);par=np.sum(xi*Sxi,axis=0)
    tilt=np.sqrt(np.maximum(np.sum(Sxi*Sxi,axis=0)-par*par,0))
    align=np.abs(par)/np.maximum(np.sqrt(np.sum(Sxi*Sxi,axis=0)),1e-12)
    gxi2=sum(np.sum(f.grad(sfft(xi[i])*f.mask)**2,axis=0) for i in range(3))
    Pp,Dw,_,_=f.loads(a)
    eps=.01*Dw.mean();rE=(Pp+eps)/(Dw+eps)
    epsR=.01*(f.nu*gxi2[live]).mean();rR=(tilt+epsR)/(f.nu*gxi2+epsR)
    gm=np.sqrt(np.sum(G*G,axis=(0,1)))
    return dict(rE=rE,rR=rR,align=align,tilt=tilt,gxi2=gxi2,live=live,gm=gm,wm=wm)

def run(E0,nu=.02,n=48,dt=.01,duration=2.):
    f=ThreeFlow(n,'control',dt,0.);f.nu=nu;f.force*=0;f.u,x,y,z=tubes(f,n,E0=E0);f.heat=np.zeros((n,n,n));rows=[]
    for i in range(round(duration/dt)):
        f.step(False)
        if (i+1)%round(.2/dt)==0:
            d=direction_plane(f);L=d['live'];top=d['gm']>=np.quantile(d['gm'],.9)
            q=lambda a,m:float(np.quantile(a[m],.99))
            rows.append(dict(t=(i+1)*dt,grad_max=float(d['gm'].max()),
                rE_max=float(d['rE'][L].max()),rE_p99=q(d['rE'],L),rR_max=float(d['rR'][L].max()),rR_p99=q(d['rR'],L),
                lnrE_p99=float(np.log(q(d['rE'],L))),lnrR_p99=float(np.log(q(d['rR'],L))),
                align_mean_live=float(d['align'][L].mean()),align_mean_topgrad=float(d['align'][L&top].mean()),
                tilt_max=float(d['tilt'][L].max()),gxi2_p99=q(d['gxi2'],L),
                rR_topgrad_over_rest=float(d['rR'][L&top].mean()/d['rR'][L&~top].mean()),
                rE_topgrad_over_rest=float(d['rE'][L&top].mean()/d['rE'][L&~top].mean()),
                live_frac=float(L.mean()),cfl=f.measure(0)['cfl']))
            r=rows[-1];print(f"t={r['t']:.1f} grad={r['grad_max']:.1f} rE p99/max={r['rE_p99']:.1f}/{r['rE_max']:.0f} rR p99/max={r['rR_p99']:.1f}/{r['rR_max']:.0f} align live/top={r['align_mean_live']:.2f}/{r['align_mean_topgrad']:.2f} rR top/rest={r['rR_topgrad_over_rest']:.1f} rE top/rest={r['rE_topgrad_over_rest']:.1f} cfl={r['cfl']:.2f}",flush=True)
    return dict(E0=E0,nu=nu,n=n,dt=dt,rows=rows)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--E0',type=float,default=.15);ap.add_argument('--dt',type=float,default=.01);ap.add_argument('--nu',type=float,default=.02)
    a=ap.parse_args();res=run(a.E0,a.nu,dt=a.dt)
    Path(__file__).with_name(f'theta_planes2_E{a.E0}_nu{a.nu}_results.json').write_text(json.dumps(res,indent=1)+'\n')
