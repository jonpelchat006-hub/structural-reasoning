"""Two-sided interface: sink energy enters a reservoir E_b (the 'bubble') instead of
vanishing.  dE_b/dt = J_in - E_b/tau_b (bubble's own dissipation) - backscatter,
backscatter = beta_b * E_b / tau_b returned to the flow on Gamma (or, if Gamma is
empty, on the theta >= 2 shell) as an increment along the local velocity.
Energy: E + E_b + dissipated + bubble_dissipated = E0.
Built on theta_formD.run (same nucleation, gate, tau)."""
import argparse,json,numpy as np
from pathlib import Path
from theta_formD import FormD, PI
from theta_tubes import tubes
from theta_planes2 import direction_plane
from theta_J_sweep import plane_exchange
from vortex3d import real, fft, cross
from theta_kinetic import sreal

def run(E0,kappa,tau_b,beta_b,nu=.01,n=64,dt=.005,duration=1.6,tau=.02):
    f=FormD(n,'control',dt,0.);f.nu=nu;f.force*=0;f.wall=3.;f.floor=-PI;f.tau=tau;f.u,x,y,z=tubes(f,n,E0=E0);f.heat=np.zeros((n,n,n))
    E_init=f.energy(f.u);loss=sink=Eb=bdiss=back=0.;rows=[]
    for i in range(round(duration/dt)):
        _,d=f.step(False);loss+=d
        th=f.clip(sreal(f.th));G=th>=3.
        if kappa and G.any():
            j,u=plane_exchange(f);a=direction_plane(f)['align']
            jp=np.where(G,np.maximum(j,0)*a,0.);u2=np.sum(u*u,axis=0)
            fac=np.where(u2>1e-12,np.minimum(kappa*jp*dt/np.maximum(u2/2,1e-12),1.),0.)
            b=f.energy(f.u);f.u=f.project(fft(u*np.sqrt(np.maximum(1-fac,0))[None]));dE=b-f.energy(f.u);sink+=dE;Eb+=dE
        if tau_b and Eb>0:
            dd=Eb*dt/tau_b;bd=(1-beta_b)*dd;bs=beta_b*dd;Eb-=dd;bdiss+=bd
            # return bs to the flow on the interface region as a velocity increment along u
            u=real(f.u);R=G if G.any() else (th>=2.)
            if R.any() and bs>0:
                u2=np.sum(u*u,axis=0);w=np.where(R,u2,0.);tot=w.sum()
                if tot>0:
                    # scale |u| up in region R so that KE rises by bs (exactly, before projection)
                    s=np.sqrt(1+bs*n**3/np.maximum(tot,1e-30));s=np.where(R,s,1.)
                    b=f.energy(f.u);f.u=f.project(fft(u*s[None]));back+=f.energy(f.u)-b
                    Eb+=bs-(f.energy(f.u)-b)   # projection loss stays in the bubble
        if (i+1)%round(.2/dt)==0:
            th=f.clip(sreal(f.th));G=th>=3.;row=f.measure((i+1)*dt)
            row.update(n_gamma=int(G.sum()),sink=sink,E_b=Eb,bubble_diss=bdiss,backscatter=back,dissipated=loss);rows.append(row)
            print(f"t={row['t']:.1f} Omega={row['enstrophy']:.4f} omega_max={row['max_vorticity']:.1f} Gamma={row['n_gamma']} sink={sink:.3e} E_b={Eb:.3e} back={back:.3e} bdiss={bdiss:.3e}",flush=True)
    err=float(abs(f.energy(f.u)+loss+Eb+bdiss-E_init))
    res=dict(E0=E0,kappa=kappa,tau_b=tau_b,beta_b=beta_b,nu=nu,n=n,dt=dt,total_error=err,sink=sink,E_b=Eb,bubble_diss=bdiss,backscatter=back,
             peak_enstrophy=max(r['enstrophy'] for r in rows),peak_vorticity=max(r['max_vorticity'] for r in rows),rows=rows)
    print(f"kappa={kappa} tau_b={tau_b} beta_b={beta_b}: peak Omega {res['peak_enstrophy']:.4f} peak omega {res['peak_vorticity']:.1f} sink {sink:.3e} returned {back:.3e} bubble-dissipated {bdiss:.3e} E_b left {Eb:.3e} err {err:.1e}",flush=True)
    return res
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--kappa',type=float,default=1.);ap.add_argument('--tau_b',type=float,default=.2);ap.add_argument('--beta_b',type=float,default=1.)
    ap.add_argument('--nu',type=float,default=.01);ap.add_argument('--n',type=int,default=64);a=ap.parse_args()
    res=run(.6,a.kappa,a.tau_b,a.beta_b,nu=a.nu,n=a.n)
    Path(__file__).with_name(f'theta_bubble_n{a.n}_nu{a.nu}_k{a.kappa}_taub{a.tau_b}_betab{a.beta_b}_results.json').write_text(json.dumps(res,indent=1)+'\n')
