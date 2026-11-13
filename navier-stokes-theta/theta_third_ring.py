"""The third ring: rotation of the STRAIN eigenframe, driven by the pressure Hessian
and by vorticity.  In the strain eigenframe (e1>=e2>=e3), the axes turn at
    Omega_ij = (H_ij + (W^2)_ij) / (lam_i - lam_j),  i != j
(from DS/Dt = -S^2 - W^2 - H + nu lap S; S^2 is diagonal in its own frame).
Also: tan(phi) = tilt / stretch of the vorticity direction, and the angle between
the pressure-Hessian principal frame and the strain frame.  Top = top-1% gradient cells."""
import argparse,json,numpy as np
from pathlib import Path
from theta_three import ThreeFlow
from theta_tubes import tubes
from theta_planes2 import direction_plane
from vortex3d import real, fft, cross
from theta_kinetic import sreal, sfft

def third_ring(f):
    a=f.u;u=real(a);w=real(1j*cross(f.k,a))
    N=fft(cross(u,w))*f.mask;Pi_h=-np.sum(1j*f.k*N,axis=0)*f.inv
    H=np.array([[sreal(-f.k[i]*f.k[j]*Pi_h) for j in range(3)] for i in range(3)])      # pressure Hessian
    G=np.array([f.grad(a[i]) for i in range(3)]);S=.5*(G+G.transpose(1,0,2,3,4));W=.5*(G-G.transpose(1,0,2,3,4))
    W2=np.einsum('ikxyz,kjxyz->ijxyz',W,W)
    Sm=np.moveaxis(S,(0,1),(-2,-1));lam,E=np.linalg.eigh(Sm)                              # ascending: lam[...,0]<=lam[...,1]<=lam[...,2]
    Hm=np.moveaxis(H,(0,1),(-2,-1));W2m=np.moveaxis(W2,(0,1),(-2,-1))
    Hf=np.einsum('...ki,...kl,...lj->...ij',E,Hm,E);W2f=np.einsum('...ki,...kl,...lj->...ij',E,W2m,E)
    Sf=np.sqrt(np.sum(S*S,axis=(0,1)))
    rates={}
    for name,M in (('pressure',Hf),('vorticity',W2f),('total',Hf+W2f)):
        r2=0
        for i in range(3):
            for j in range(i+1,3):
                d=lam[...,i]-lam[...,j];r2=r2+(M[...,i,j]/np.where(np.abs(d)>1e-6*Sf.max(),d,np.inf))**2
        rates[name]=np.sqrt(r2)/np.maximum(Sf,1e-12)           # dimensionless: frame turn rate / strain rate
    # angle between pressure-Hessian frame and strain frame: cos of angle between their most-compressive axes
    lh,Eh=np.linalg.eigh(Hm);cosHS=np.abs(np.einsum('...i,...i->...',Eh[...,0],E[...,0]))
    d=direction_plane(f);par=np.abs(np.einsum('ixyz,ijxyz,jxyz->xyz',d['tilt']*0+w/np.maximum(d['wm'],1e-12)[None],S,w/np.maximum(d['wm'],1e-12)[None]))
    tanphi=d['tilt']/np.maximum(par,1e-12)
    return rates,cosHS,tanphi,d
def run(E0,nu=.02,n=48,dt=.01,duration=2.):
    f=ThreeFlow(n,'control',dt,0.);f.nu=nu;f.force*=0;f.u,x,y,z=tubes(f,n,E0=E0);f.heat=np.zeros((n,n,n));rows=[]
    for i in range(round(duration/dt)):
        f.step(False)
        if (i+1)%round(.4/dt)==0:
            rates,cosHS,tanphi,d=third_ring(f);L=d['live'];top=L&(d['gm']>=np.quantile(d['gm'][L],.99));rest=L&~top
            med=lambda q,m:float(np.median(q[m]))
            row=dict(t=(i+1)*dt,grad_max=float(d['gm'].max()),
                frame_rate_total=(med(rates['total'],top),med(rates['total'],rest)),frame_rate_pressure=(med(rates['pressure'],top),med(rates['pressure'],rest)),
                frame_rate_vorticity=(med(rates['vorticity'],top),med(rates['vorticity'],rest)),
                cosHS=(med(cosHS,top),med(cosHS,rest)),tanphi=(med(tanphi,top),med(tanphi,rest)),
                pressure_share_top=float(np.median((rates['pressure']/np.maximum(rates['total'],1e-12))[top])))
            rows.append(row)
            print(f"t={row['t']:.1f} grad={row['grad_max']:.1f} | frame rate top/rest: total {row['frame_rate_total'][0]:.2f}/{row['frame_rate_total'][1]:.2f} pressure {row['frame_rate_pressure'][0]:.2f}/{row['frame_rate_pressure'][1]:.2f} vorticity {row['frame_rate_vorticity'][0]:.2f}/{row['frame_rate_vorticity'][1]:.2f} | cos(H,S) top/rest {row['cosHS'][0]:.2f}/{row['cosHS'][1]:.2f} | tan phi top/rest {row['tanphi'][0]:.2f}/{row['tanphi'][1]:.2f}",flush=True)
    return dict(E0=E0,nu=nu,rows=rows)
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--E0',type=float,default=.15);ap.add_argument('--dt',type=float,default=.01);a=ap.parse_args()
    res=run(a.E0,dt=a.dt);Path(__file__).with_name(f'theta_third_ring_E{a.E0}_results.json').write_text(json.dumps(res,indent=1)+'\n')
