"""Chain of bubbles along a void line.  Antiparallel tubes with a k-wavelength
perturbation (Crow-type: k pinch sites) or an envelope-localised perturbation
(finite chain with free ends).  Diagnostics on the Form D nucleation field
(passive, tau .02): connected components of Gamma, their x-positions and sizes,
merging over time; where the zero-divisor channels (P ~ 0, live w and S) lie
relative to the bubbles (in the x-gaps between components?); and the pressure
exchange j in the low-x / high-x halves of each component (symmetric = interior,
asymmetric = single-sided end)."""
import argparse,json,numpy as np
from pathlib import Path
from scipy import ndimage
from theta_formD import FormD, PI
from theta_planes2 import direction_plane
from theta_J_sweep import plane_exchange
from vortex3d import real, fft, cross
from theta_kinetic import sreal

def tubes_chain(f,n,k=3,env=None,d=.8,a=.2,sig=.3,E0=.6):
    x,y,z=np.meshgrid(*(np.arange(n)*2*np.pi/n for _ in range(3)),indexing='ij')
    pert=a*np.cos(k*x); dpert=-a*k*np.sin(k*x)
    if env is not None:   # localised: Gaussian envelope of width env around x=pi
        e=np.exp(-((x-np.pi)**2)/(2*env**2)); de=e*(-(x-np.pi)/env**2)
        pert,dpert=pert*e,dpert*e+a*np.cos(k*x)*de
    w=np.zeros((3,n,n,n))
    for s,sign in ((+1,+1),(-1,-1)):
        yc=np.pi+s*(d/2+pert); dy=(y-yc+np.pi)%(2*np.pi)-np.pi; dz=(z-np.pi+np.pi)%(2*np.pi)-np.pi
        g=np.exp(-(dy*dy+dz*dz)/(2*sig*sig)); tang=np.array([np.ones_like(x),s*dpert,np.zeros_like(x)])
        w+=sign*g*tang
    wh=f.project(fft(w));u=f.project(1j*cross(f.k,wh)*f.inv);u*=np.sqrt(E0/f.energy(u));return u,x

def analyse(f,x,n):
    th=f.clip(sreal(f.th));G=th>=3.
    lab,ncomp=ndimage.label(G)          # periodic wrap not handled: note in write-up
    j,u=plane_exchange(f);d=direction_plane(f);L=d['live']
    Pp,Dw,S,w=f.loads(f.u)
    wm=d['wm'];Sf=np.sqrt(np.sum(S*S,axis=(0,1)))
    P=sum(w[i]*S[i,j2]*w[j2] for i in range(3) for j2 in range(3))
    a_al=np.abs(P)/np.maximum(np.sum(w*w,axis=0)*Sf,1e-30)
    void=L&(a_al<.1)                    # zero-divisor channel cells
    comps=[]
    for c in range(1,ncomp+1):
        m=lab==c
        if m.sum()<4: continue
        xs=x[m];xc=float(np.mean(xs));lo=m&(x<xc);hi=m&(x>=xc)
        comps.append(dict(size=int(m.sum()),x_center=xc,x_span=float(xs.max()-xs.min()),
            j_lo=float(j[lo].mean()) if lo.any() else None,j_hi=float(j[hi].mean()) if hi.any() else None,j_mean=float(j[m].mean())))
    comps.sort(key=lambda c:c['x_center'])
    # void cells in gaps: fraction of void cells whose x lies strictly between consecutive component centers vs inside a component's x-span
    gap=0;inside=0
    if len(comps)>=1:
        vx=x[void]
        for c in comps:
            inside+=int(((vx>=c['x_center']-c['x_span']/2)&(vx<=c['x_center']+c['x_span']/2)).sum())
        gap=int(void.sum())-inside
    return dict(n_gamma=int(G.sum()),n_comp=len(comps),components=comps,void_cells=int(void.sum()),void_in_gaps=gap,void_in_spans=inside,
                void_frac_by_x=[float(void[i].mean()) for i in range(0,n,n//12)],gamma_frac_by_x=[float(G[i].mean()) for i in range(0,n,n//12)])

def run(tag,k,env,nu=.01,n=64,dt=.005,duration=1.6,E0=.6):
    f=FormD(n,'control',dt,0.);f.nu=nu;f.force*=0;f.wall=3.;f.floor=-PI;f.tau=.02;f.u,x=tubes_chain(f,n,k,env,E0=E0);f.heat=np.zeros((n,n,n));rows=[]
    for i in range(round(duration/dt)):
        f.step(False)
        if (i+1)%round(.2/dt)==0:
            r=analyse(f,x,n);r['t']=(i+1)*dt;r['enstrophy']=f.measure(0)['enstrophy'];rows.append(r)
            cs=' '.join(f"[x={c['x_center']:.2f} n={c['size']} jlo={c['j_lo'] if c['j_lo'] is None else round(c['j_lo'],2)} jhi={c['j_hi'] if c['j_hi'] is None else round(c['j_hi'],2)}]" for c in r['components'])
            print(f"{tag} t={r['t']:.1f} Gamma={r['n_gamma']} comps={r['n_comp']} void gaps/spans={r['void_in_gaps']}/{r['void_in_spans']} {cs}",flush=True)
    return dict(tag=tag,k=k,env=env,nu=nu,n=n,rows=rows)
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--tag',default='chain3');ap.add_argument('--k',type=int,default=3);ap.add_argument('--env',type=float,default=None);a=ap.parse_args()
    res=run(a.tag,a.k,a.env);Path(__file__).with_name(f'theta_chain_{a.tag}_results.json').write_text(json.dumps(res,indent=1)+'\n')
