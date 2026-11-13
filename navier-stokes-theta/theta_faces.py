"""Two-face flux per bubble.  For incompressible flow -u.grad Pi = -div(Pi u), so the
pressure-plane exchange integrated over a bubble equals the inward flux of the current
G = Pi u through its boundary.  Per connected component of Gamma (periodic-merged) we
report the inward flux through faces whose outward normal is -x ('lo', looking to smaller
x) and +x ('hi'), plus the lateral (y,z) faces, for the pressure current Pi u and the
kinetic current (|u|^2/2) u.  Discrete: face values are averages of neighbouring cells,
consistent with central-difference divergence, so face fluxes sum exactly to the volume
integral of -div G.  Chain cases as in theta_chain.py."""
import argparse,json,numpy as np
from pathlib import Path
from scipy import ndimage
from theta_formD import FormD, PI
from theta_chain import tubes_chain
from vortex3d import real, fft, cross
from theta_kinetic import sreal, sfft

def periodic_label(G):
    lab,n=ndimage.label(G);parent=list(range(n+1))
    def find(a):
        while parent[a]!=a: parent[a]=parent[parent[a]];a=parent[a]
        return a
    for ax in range(3):
        a=np.take(lab,0,axis=ax);b=np.take(lab,-1,axis=ax);m=(a>0)&(b>0)
        for p,q in set(zip(a[m].tolist(),b[m].tolist())):
            ra,rb=find(p),find(q)
            if ra!=rb: parent[rb]=ra
    out=np.zeros_like(lab)
    for c in range(1,n+1): out[lab==c]=find(c)
    return out

def face_fluxes(mask,Gv,h):
    """inward flux of vector field Gv (3,n,n,n) into mask through faces along each axis, split by outward-normal sign."""
    res={}
    for ax,name in enumerate('xyz'):
        Gf_plus=(Gv[ax]+np.roll(Gv[ax],-1,axis=ax))/2      # face between cell i and i+1
        out_hi=mask&~np.roll(mask,-1,axis=ax)                # cell in mask, neighbour i+1 out: outward normal +ax
        out_lo=mask&~np.roll(mask,1,axis=ax)                 # neighbour i-1 out: outward normal -ax
        Gf_minus=np.roll(Gf_plus,1,axis=ax)                  # face between i-1 and i
        res[name+'_hi']=float(-(Gf_plus[out_hi]).sum()*h*h)  # inward = -(G.n) with n=+ax
        res[name+'_lo']=float((Gf_minus[out_lo]).sum()*h*h)  # n=-ax: inward = +G_ax
    return res

def run(tag,k,env,nu=.01,n=64,dt=.005,duration=1.2,E0=.6):
    f=FormD(n,'control',dt,0.);f.nu=nu;f.force*=0;f.wall=3.;f.floor=-PI;f.tau=.02;f.u,x=tubes_chain(f,n,k,env,E0=E0);f.heat=np.zeros((n,n,n));h=2*np.pi/n;rows=[]
    for i in range(round(duration/dt)):
        f.step(False)
        if (i+1)%round(.2/dt)==0:
            th=f.clip(sreal(f.th));G=th>=3.;lab=periodic_label(G)
            u=real(f.u);w=real(1j*cross(f.k,f.u));N=fft(cross(u,w))*f.mask;Pi=sreal(-np.sum(1j*f.k*N,axis=0)*f.inv)
            GP=Pi[None]*u;GK=(np.sum(u*u,axis=0)/2)[None]*u
            divGP=sum(sreal(1j*f.k[a]*sfft(GP[a])) for a in range(3))
            comps=[]
            for c in np.unique(lab[lab>0]):
                m=lab==c
                if m.sum()<15: continue
                xs=x[m];
                # circular mean of x for wrapped components
                xc=float((np.angle(np.exp(1j*xs).mean()))%(2*np.pi))
                fp=face_fluxes(m,GP,h);fk=face_fluxes(m,GK,h)
                vol=float(-divGP[m].sum()*h**3)
                comps.append(dict(x=xc,size=int(m.sum()),P_lo=fp['x_lo'],P_hi=fp['x_hi'],P_lat=fp['y_lo']+fp['y_hi']+fp['z_lo']+fp['z_hi'],
                                  K_lo=fk['x_lo'],K_hi=fk['x_hi'],K_lat=fk['y_lo']+fk['y_hi']+fk['z_lo']+fk['z_hi'],
                                  vol_int=vol,face_sum=sum(fp.values())))
            comps.sort(key=lambda c:c['x']);rows.append(dict(t=(i+1)*dt,n_gamma=int(G.sum()),components=comps))
            print(f"{tag} t={(i+1)*dt:.1f} Gamma={int(G.sum())} | "+' '.join(f"[x={c['x']:.2f} n={c['size']} P lo/hi={c['P_lo']:+.2e}/{c['P_hi']:+.2e} lat={c['P_lat']:+.2e} | K lo/hi={c['K_lo']:+.2e}/{c['K_hi']:+.2e} | chk {c['vol_int']:+.2e}~{c['face_sum']:+.2e}]" for c in comps),flush=True)
    return dict(tag=tag,k=k,env=env,nu=nu,n=n,rows=rows)
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--tag',default='chain3');ap.add_argument('--k',type=int,default=3);ap.add_argument('--env',type=float,default=None);a=ap.parse_args()
    res=run(a.tag,a.k,a.env);Path(__file__).with_name(f'theta_faces_{a.tag}_results.json').write_text(json.dumps(res,indent=1)+'\n')
