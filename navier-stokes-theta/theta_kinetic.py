"""Form B: a kinetic theta field coupled to 3D Navier-Stokes (proposed 2026-09-13).

Built from Shovelcat_Theory_1.pdf: theta is a load field obeying a
reaction-diffusion equation relaxing to 1 (Sec. 3.3, Eq. 2); at theta = pi an
interface forms that acts as an energy SINK (Prop. 1); near equilibrium
g_eff = g exp(-|theta-1|).  Weights/powers from Table 1: w_E=.4, p_E=.8.

Fluid translation (all choices explicit):
  r_E(x,t)   = (P_w^+ + d<Dw>) / (Dw + d<Dw>),   P_w = w_i S_ij w_j (enstrophy
               production, positive part), Dw = nu |grad w|^2 (viscous enstrophy
               destruction), d=.01 keeps r_E -> 1 in quiescent fluid.
  theta_s    = 1 + w_E sign(L) sqrt(|p_E L|),  L = ln r_E   (signed root, as
               in THETA_FIELD_RESULTS; isothermal so r_S = r_T = 1 exactly).
  field      : theta_t + u.grad theta = D lap theta + (theta_s - theta)/tau
  interface  : theta <= pi (Dirichlet cap; the sink)
  coupling   : nu_eff = nu exp(beta |theta-1|); momentum gets div(2(nu_eff-nu)S)
               beta = 0 -> theta is a passive diagnostic (control).
Flow: vortex3d two helical tubes, .3-time-unit pulse (aligned / transverse).
Run: python theta_kinetic.py --n 24|32
"""
import argparse, json
from pathlib import Path
import numpy as np
from vortex3d import Flow, fft, real, cross
def sfft(a): return np.fft.fftn(a)
def sreal(a): return np.fft.ifftn(a).real

PI=np.pi; W_E=.4; P_E=.8

class ThetaFlow(Flow):
    def __init__(self,n,kind,dt,beta,D=.03,tau=.1,delta=.01):
        super().__init__(n,kind,dt)
        self.beta,self.D,self.tau,self.delta=beta,D,tau,delta
        self.th=sfft(np.ones((n,n,n)))*self.mask      # theta starts at 1 everywhere
    def grad(self,a): return np.array([sreal(1j*self.k[j]*a) for j in range(3)])
    def loads(self,a):
        """enstrophy production (positive part), viscous enstrophy destruction, strain."""
        wh=1j*cross(self.k,a); w=real(wh)
        G=np.array([self.grad(a[i]) for i in range(3)])    # G[i,j] = d_j u_i
        S=.5*(G+G.transpose(1,0,2,3,4))
        Pw=sum(w[i]*S[i,j]*w[j] for i in range(3) for j in range(3))
        Dw=self.nu*sum(np.sum(self.grad(wh[i])**2,axis=0) for i in range(3))
        return np.maximum(Pw,0),Dw,S,w
    def theta_static(self,Pp,Dw):
        eps=self.delta*Dw.mean()
        L=np.log((Pp+eps)/(Dw+eps))
        return 1+W_E*np.sign(L)*np.sqrt(np.abs(P_E*L))
    def rhs(self,a,active,thh=None):
        u=real(a); Pp,Dw,S,w=self.loads(a)
        f=self.force if active else self.force*0
        r=self.project(fft(cross(u,w)))-self.nu*self.k2*a+f
        th=np.minimum(sreal(thh),PI)                        # interface cap
        extra=0.
        if self.beta:
            nup=self.nu*(np.exp(self.beta*np.abs(th-1))-1)  # excess viscosity
            tau_=2*nup[None,None]*S
            div=np.array([sum(1j*self.k[j]*sfft(tau_[i,j]) for j in range(3)) for i in range(3)])
            r=r+self.project(div)
            extra=float(np.mean(np.sum(tau_*S,axis=(0,1))))   # extra dissipation rate
        ths=self.theta_static(Pp,Dw)
        rth=(-sfft(np.sum(u*self.grad(thh),axis=0))-self.D*self.k2*thh+sfft((ths-th)/self.tau))*self.mask
        power=float(np.mean(np.sum(u*real(f),axis=0)))
        diss=float(self.nu*np.mean(np.sum(w*w,axis=0)))+extra
        return r,rth,power,diss
    def step(self,active):
        a,b,h=self.u,self.th,self.dt
        r1,s1,p1,d1=self.rhs(a,active,b); r2,s2,p2,d2=self.rhs(a+h*r1/2,active,b+h*s1/2)
        r3,s3,p3,d3=self.rhs(a+h*r2/2,active,b+h*s2/2); r4,s4,p4,d4=self.rhs(a+h*r3,active,b+h*s3)
        self.u=self.project(a+h*(r1+2*r2+2*r3+r4)/6)
        self.th=(b+h*(s1+2*s2+2*s3+s4)/6)*self.mask
        # enforce the interface cap on the stored field as well
        self.th=sfft(np.minimum(sreal(self.th),PI))*self.mask
        return h*(p1+2*p2+2*p3+p4)/6,h*(d1+2*d2+2*d3+d4)/6
    def measure(self,t):
        row=super().measure(t); th=sreal(self.th); Pp,Dw,_,_=self.loads(self.u)
        row.update(theta_min=float(th.min()),theta_max=float(th.max()),theta_mean=float(th.mean()),
                   vol_theta_gt1=float((th>1.).mean()),vol_theta_gt_phi=float((th>1.618034).mean()),
                   vol_theta_at_pi=float((th>=PI-1e-9).mean()),
                   enstrophy_production=float(Pp.mean()),enstrophy_destruction=float(Dw.mean()))
        return row

def run(n,kind,beta,dt=.01,T=2.):
    f=ThetaFlow(n,kind,dt,beta); rows=[f.measure(0)];work=loss=0.
    for i in range(round(T/dt)):
        p,d=f.step(i<round(.3/dt));work+=p;loss+=d
        if (i+1)%round(.1/dt)==0: rows.append(f.measure((i+1)*dt))
    residual=rows[-1]['energy']-rows[0]['energy']-work+loss
    assert abs(residual)<1e-6, residual
    assert max(r['cfl'] for r in rows)<.5
    res=dict(n=n,kind=kind,beta=beta,dt=dt,work=work,dissipation=loss,budget_error=residual,
             peak_vorticity=max(r['max_vorticity'] for r in rows),peak_enstrophy=max(r['enstrophy'] for r in rows),
             peak_theta=max(r['theta_max'] for r in rows),rows=rows)
    print(n,kind,'beta',beta,'peak omega',round(res['peak_vorticity'],4),'peak Omega',round(res['peak_enstrophy'],5),
          'final E',round(rows[-1]['energy'],6),'theta max',round(res['peak_theta'],4),'budget',f'{residual:.1e}',flush=True)
    return res

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--n',type=int,default=24);ap.add_argument('--dt',type=float,default=.01)
    ap.add_argument('--betas',type=float,nargs='+',default=[0.,.5,1.]);ap.add_argument('--kinds',nargs='+',default=['aligned','transverse'])
    a=ap.parse_args();tag='_'.join(a.kinds)+'_'+'_'.join(str(b) for b in a.betas);out=Path(__file__).with_name(f'theta_kinetic_{a.n}_{a.dt}_{tag}_results.json');results=[]
    for kind in a.kinds:
        for beta in a.betas:
            results.append(run(a.n,kind,beta,a.dt));out.write_text(json.dumps(results,indent=1)+'\n')
