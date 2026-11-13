"""Smooth strip-magnet field and a reduced closed-loop force/work audit.

Prescribed 2D field below a patterned sheet at z=1.25, in scaled units.
B is curl-free and divergence-free in the fluid region. Weak, linear response:
f=chi*grad(|B|^2/2), with rho=mu0=1 in the chosen units. Ignore demagnetization,
saturation, free surfaces, electrical conduction and magnetization dynamics.
Constant chi gives a conservative bulk force; imposed chi(x) is a maintained
material/temperature contrast, not a source-free permanent-magnet engine.
"""
import json
from pathlib import Path
import numpy as np


def field(x,z):
    b1=np.exp(z-1.25);b2=.25*np.exp(2*(z-1.25))
    bx=b1*np.sin(x)+b2*np.sin(2*x)
    bz=-b1*np.cos(x)-b2*np.cos(2*x)
    return bx,bz


def gradient(x,z):
    b1=np.exp(z-1.25);b2=.25*np.exp(2*(z-1.25))
    return -b1*b2*np.sin(x), b1*b1+2*b2*b2+3*b1*b2*np.cos(x)


def loop_work(epsilon,order=64):
    # Clockwise in the x-z plane: rise at x=0, return at x=pi.
    nodes,weights=np.polynomial.legendre.leggauss(order)
    vertices=[(0.,.1),(0.,1.),(np.pi,1.),(np.pi,.1),(0.,.1)]
    total=0.
    for a,b in zip(vertices[:-1],vertices[1:]):
        point=np.array(a)[:,None]+(np.array(b)-a)[:,None]*(nodes+1)/2
        gx,gz=gradient(*point);chi=1+epsilon*np.cos(point[0])
        total+=float(np.sum(weights*chi*(gx*(b[0]-a[0])+gz*(b[1]-a[1])))/2)
    return total


def run_loop(drive,dt=.01):
    # Uniform-volume-flow reduction in a prescribed closed conduit.
    # Inertance 1, linear resistance .3 and quadratic resistance .2.
    y=np.array([.2,0.,0.]);e0=.02;error=0.
    def rhs(a):
        q=a[0]
        return np.array([drive-.3*q-.2*abs(q)*q,drive*q,.3*q*q+.2*abs(q)**3])
    for _ in range(round(60/dt)):
        a=rhs(y);b=rhs(y+dt*a/2);c=rhs(y+dt*b/2);d=rhs(y+dt*c)
        y+=dt*(a+2*b+2*c+d)/6
        error=max(error,abs(.5*y[0]**2-e0-y[1]+y[2]))
    exact=float(np.sign(drive)*(-.3+np.sqrt(.09+.8*abs(drive)))/.4)
    assert error<1e-8 and abs(y[0]-exact)<1e-7
    return dict(loop_pressure=drive,final_flow=float(y[0]),analytic_steady_flow=exact,
                mechanical_input=float(y[1]),dissipation=float(y[2]),max_energy_error=error)


if __name__=='__main__':
    x,z=np.meshgrid(np.linspace(0,2*np.pi,257),np.linspace(0,1,129),indexing='ij')
    bx,bz=field(x,z);gx,gz=gradient(x,z)
    # Check the potential gradient and source-free field equations numerically.
    h=1e-5
    bxp,bzp=field(x+h,z);bxm,bzm=field(x-h,z)
    bxt,bzt=field(x,z+h);bxb,bzb=field(x,z-h)
    div=(bxp-bxm+bzt-bzb)/(2*h)
    curl=(bxt-bxb-bzp+bzm)/(2*h)
    gxn=((bxp*bxp+bzp*bzp)-(bxm*bxm+bzm*bzm))/(4*h)
    gzn=((bxt*bxt+bzt*bzt)-(bxb*bxb+bzb*bzb))/(4*h)
    checks=dict(max_div_B=float(abs(div).max()),max_curl_B=float(abs(curl).max()),
                max_gradient_error=float(max(abs(gxn-gx).max(),abs(gzn-gz).max())),
                minimum_upward_force=float(gz.min()),minimum_Bz=float(bz.min()),maximum_Bz=float(bz.max()))
    assert max(checks[k] for k in ('max_div_B','max_curl_B','max_gradient_error'))<1e-8
    cases=[]
    for eps in (0.,.25,-.25):
        work=loop_work(eps);refined=loop_work(eps,128)
        assert abs(work-refined)<1e-12
        if eps==0:assert abs(work)<1e-12
        result=dict(susceptibility_contrast=eps,**run_loop(work));cases.append(result)
        print('magnetic loop',eps,'work/circuit',work,'steady flow',result['final_flow'],flush=True)
    Path(__file__).with_name('magnetic_sheet_results.json').write_text(json.dumps(dict(checks=checks,cases=cases),indent=2)+'\n')
