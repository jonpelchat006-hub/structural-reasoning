"""Independent checks of the September 15 theta work; does not modify its code.

Analytic Taylor-Green pressure check and a saved unforced tube snapshot.
No new time evolution or parameter fitting. No object arrays are unpickled.
"""
import json
from pathlib import Path
import numpy as np
from scipy.integrate import quad
from theta_formD import FormD
from theta_third_ring import third_ring
from theta_planes2 import direction_plane
from vortex3d import real, fft, cross
from theta_kinetic import sfft, sreal

root = Path(__file__).parent


def pressure_fields(f):
    u = real(f.u)
    w = real(1j*cross(f.k, f.u))
    N = fft(cross(u,w))*f.mask
    total = -np.sum(1j*f.k*N,axis=0)*f.inv
    kinetic = sfft(np.sum(u*u,axis=0)/2)*f.mask
    physical = total-kinetic
    physical[0,0,0] = 0
    G = np.array([f.grad(f.u[i]) for i in range(3)])
    trAA = np.einsum('ijxyz,jixyz->xyz',G,G)
    poisson = sfft(trAA)*f.mask*f.inv
    hess = lambda a: np.array([[sreal(-f.k[i]*f.k[j]*a) for j in range(3)] for i in range(3)])
    Htotal,Hphysical,Hpoisson = map(hess,(total,physical,poisson))
    norm = lambda a: float(np.sqrt(np.mean(a*a)))
    return dict(u=u,G=G,total=total,physical=physical,Htotal=Htotal,Hphysical=Hphysical,
        poisson_error=norm(Hphysical-Hpoisson)/norm(Hpoisson),
        old_hessian_relative_error=norm(Htotal-Hpoisson)/norm(Hpoisson))


f = FormD(24,'control',.005,0.)
x,y,z = np.meshgrid(*(np.arange(24)*2*np.pi/24 for _ in range(3)),indexing='ij')
f.u = f.project(fft(np.array([np.sin(x)*np.cos(y),-np.cos(x)*np.sin(y),0*x])))
fields = pressure_fields(f)
p_exact = .25*(np.cos(2*x)+np.cos(2*y))
tg = dict(corrected_pressure_max_error=float(abs(sreal(fields['physical'])-p_exact).max()),
          corrected_hessian_poisson_relative_error=fields['poisson_error'],
          current_hessian_relative_error=fields['old_hessian_relative_error'])
assert tg['corrected_pressure_max_error'] < 1e-12
assert tg['corrected_hessian_poisson_relative_error'] < 1e-12

checkpoint = root/'theta_tubes_ckpt_48_0.02_0.0_0.6_0.005.npz'
with np.load(checkpoint,allow_pickle=False) as c:
    velocity = c['u']
    step = int(c['i'])
f = FormD(48,'control',.005,0.)
f.nu = .02
f.u = velocity
fields = pressure_fields(f)
G = fields['G']
S = .5*(G+G.transpose(1,0,2,3,4))
W = .5*(G-G.transpose(1,0,2,3,4))
W2 = np.einsum('ikxyz,kjxyz->ijxyz',W,W)
visc = np.array([[f.nu*sreal(-f.k2*sfft(S[i,j])) for j in range(3)] for i in range(3)])
matrix = lambda a: np.moveaxis(a,(0,1),(-2,-1))
lam,E = np.linalg.eigh(matrix(S))
toframe = lambda a: np.einsum('...ki,...kl,...lj->...ij',E,matrix(a),E)
Sf = np.sqrt(np.sum(S*S,axis=(0,1)))
valid = np.ones(Sf.shape,dtype=bool)
for i in range(3):
    for j in range(i+1,3):
        valid &= abs(lam[...,i]-lam[...,j]) > 1e-6*Sf.max()
d = direction_plane(f)
top = d['live']&(d['gm']>=np.quantile(d['gm'][d['live']],.99))&valid
def rate(M):
    MF = toframe(M)
    total = 0
    for i in range(3):
        for j in range(i+1,3):
            denom=lam[...,i]-lam[...,j]
            total += (MF[...,i,j]/np.where(abs(denom)>1e-6*Sf.max(),denom,np.inf))**2
    return np.sqrt(total)/np.maximum(Sf,1e-12)
def cosaxis(H):
    _,EH=np.linalg.eigh(matrix(H))
    return abs(np.einsum('...i,...i->...',EH[...,0],E[...,0]))
oldrates,oldcos,_,_ = third_ring(f)
snapshot = dict(file=checkpoint.name,step=step,time=step*.005,top_cells=int(top.sum()),
    corrected_hessian_poisson_relative_error=fields['poisson_error'],
    current_hessian_relative_error=fields['old_hessian_relative_error'],
    old_axis_cosine_median=float(np.median(oldcos[top])),
    physical_pressure_axis_cosine_median=float(np.median(cosaxis(fields['Hphysical'])[top])),
    old_reported_total_rate_median=float(np.median(oldrates['total'][top])),
    corrected_inviscid_rate_median=float(np.median(rate(fields['Hphysical']+W2)[top])),
    corrected_with_viscosity_rate_median=float(np.median(rate(fields['Hphysical']+W2-visc)[top])))
assert snapshot['corrected_hessian_poisson_relative_error'] < 1e-10
diffusivity = []
for nu in (.02,.01,.007):
    g=FormD(8,'control',.005,0.)
    g.nu=nu
    diffusivity.append(dict(nu=g.nu,theta_diffusivity_D=g.D))
pairs=[]
for n,nu in [(64,.02),(64,.01),(96,.007)]:
    a,b = [json.loads((root/f'theta_formD_n{n}_nu{nu}_E0.6_k{k:.1f}_tau0.02_results.json').read_text()) for k in (0,1)]
    pairs.append(dict(n=n,nu=nu,peak_enstrophy_reduction_percent=100*(1-b['peak_enstrophy']/a['peak_enstrophy']),
        peak_vorticity_reduction_percent=100*(1-b['peak_vorticity']/a['peak_vorticity']),
        removed_energy_percent=100*b['sink']/b['E0'],
        max_reported_budget_error=max(a['total_error'],b['total_error'])))
# Restricted Euler: Q'=-3R, R'=2Q^2/3, so Delta=Q^3+27R^2/4 is constant.
# Starting Q=0,R=1, put q=-Q. The invariant gives R=sqrt(1+4q^3/27).
# The time to q=infinity is finite since the integrand decays as q^(-3/2).
blowup_time, quadrature_error = quad(lambda q: 1/(3*np.sqrt(1+4*q**3/27)),0,np.inf)
re_check=dict(initial_Q=0,initial_R=1,constant_discriminant=27/4,
    finite_time_to_infinity=blowup_time,quadrature_error_estimate=quadrature_error,
    applies_to='Restricted Euler ODE only, not Navier-Stokes')
result=dict(taylor_green=tg,saved_snapshot=snapshot,diffusivity=diffusivity,
    restricted_euler_positive_discriminant=re_check,
    stored_results=pairs,static_rE_at_theta3=float(np.exp(2/.96)),
    static_rE_at_theta_pi=float(np.exp((np.pi-1)/.96)),
    uniform_wall_equilibrium_at_capped_source=float((np.pi+3)/2))
(root/'theta_review_20260915_checks.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result,indent=2))
