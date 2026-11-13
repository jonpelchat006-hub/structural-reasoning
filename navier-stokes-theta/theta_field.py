"""Diagnostic evaluation of the RECOVERED theta on the thermal ring.

theta = (1+ln r_S)(1+sqrt(ln r_T))(1+sqrt(ln r_E))   [ORIGINAL_THETA.md, image]

Mapping to the thermal_loop flow (all choices explicit, none from the source):
  T0 = 1        absolute baseline temperature; T = T0 + excess.
  r_S(x,t) = ln(1+dT)/dT   local entropy gained per unit heat, relative to
                           depositing the same heat at T0.  -> 1 as dT -> 0.
  r_T(x,t) = T0/(T0+dT)    reference / actual.  <= 1 wherever heated, so the
                           sqrt(ln r_T) factor is OUTSIDE the real domain
                           everywhere in this flow.  Two rules are evaluated:
                             clamp : factor = 1                (ln r_T -> 0)
                             signed: factor = 1 - sqrt(-ln r_T)
  r_E(t)   = P_demanded/D  controller requested power over instantaneous viscous
                           dissipation rate (global).  > 1 while the fluid
                           cannot yet absorb the demand; if < 1 the same two
                           rules apply.
Dynamics are IDENTICAL to thermal_loop.run (same setup, kicks, heat step);
theta never feeds back.  Run: python theta_field.py --n 24|32
"""
import argparse, json
from pathlib import Path
import numpy as np
from pin_ring import setup
from ring_power import kick
from thermal_loop import face_velocity, heat_step
from vortex3d import real

PHI=(1+np.sqrt(5))/2
THRESHOLDS={'1':1.,'sqrt_phi':np.sqrt(PHI),'phi':PHI,'sqrt_pi':np.sqrt(np.pi),'pi':np.pi}

def factor(ratio,rule):
    """(1+sqrt(ln ratio)) with a stated below-domain rule."""
    L=np.log(ratio)
    if rule=='clamp': return 1+np.sqrt(np.maximum(L,0))
    if rule=='signed': return 1+np.sign(L)*np.sqrt(np.abs(L))
    raise ValueError(rule)

def theta_S(dT):
    with np.errstate(divide='ignore',invalid='ignore'):
        rS=np.where(dT>1e-12,np.log1p(dT)/np.where(dT>1e-12,dT,1),1.)
    return 1+np.log(rS)          # rS in (0,1]; >e^-1 for dT < ~e^... always here

def theta_field(dT,thetaE,rule):
    return theta_S(dT)*factor(1/(1+dT),rule)*thetaE

def excess_for_threshold(c,thetaE,rule):
    """dT* with theta(dT*)=c for given thetaE (theta is monotone decreasing in dT)."""
    if thetaE<=c: return 0.
    lo,hi=0.,1.
    while theta_field(hi,thetaE,rule)>c: hi*=2
    for _ in range(80):
        mid=(lo+hi)/2
        if theta_field(mid,thetaE,rule)>c: lo=mid
        else: hi=mid
    return (lo+hi)/2

def run(n,dt=.02,duration=3.,stop=3.):
    f,x,y,z=setup(n,8);f.dt=dt;direction=f.force.copy();f.force*=0
    rates=np.array([0.,.5,2.]);heat=np.zeros((3,n,n,n));cooled=np.zeros(3)
    work=loss=0.;rows=[];h=2*np.pi/n
    first={rule:{k:{name:None for name in THRESHOLDS} for k in ('min','global')} for rule in ('clamp','signed')}
    for i in range(round(duration/dt)):
        t=(i+.5)*dt;P=.04*min(t/.2,1) if t<stop else 0.;input_e=P*dt
        kick(f,direction,input_e/2);previous=f.u.copy()
        _,d=f.step(False);mid=(previous+f.u)/2
        kick(f,direction,input_e/2);work+=input_e;loss+=d
        grad=np.array([real(1j*f.k[j]*mid) for j in range(3)])
        q=.5*f.nu*np.sum((grad+grad.swapaxes(0,1))**2,axis=(0,1))
        if q.mean()>0:q*=d/(dt*q.mean())
        heat,removed=heat_step(heat,face_velocity(mid,h),q,dt,h,rates);cooled+=removed
        D=d/dt;tnow=(i+1)*dt
        rE=P/D if D>0 else np.inf
        # sample every step for crossings, every .1 for rows
        rec={}
        for rule in ('clamp','signed'):
            thE=float(factor(rE,rule)) if np.isfinite(rE) else np.inf
            th=theta_field(heat[0],thE,rule)        # insulated case field
            gm=theta_S(heat[0].mean())*factor(1/(1+heat[0].mean()),rule)*thE
            rec[rule]=dict(theta_E=thE,min=float(th.min()),max=float(th.max()),mean=float(th.mean()),
                           global_mean_inputs=float(gm),
                           argmin=[float(c[np.unravel_index(np.argmin(th),th.shape)]) for c in (x,y,z)],
                           volume_below={name:float((th<c).mean()) for name,c in THRESHOLDS.items()},
                           excess_at_threshold={name:excess_for_threshold(c,thE,rule) for name,c in THRESHOLDS.items()})
            for name,c in THRESHOLDS.items():
                if first[rule]['min'][name] is None and th.min()<c:
                    first[rule]['min'][name]=dict(t=tnow,where=rec[rule]['argmin'],excess=float(heat[0].max()))
                if first[rule]['global'][name] is None and np.isfinite(thE) and thE<c:
                    first[rule]['global'][name]=dict(t=tnow,P=P,D=float(D))
        if (i+1)%round(.1/dt)==0:
            row=f.measure(tnow)
            row.update(P_demanded=P,D=float(D),r_E=float(rE) if np.isfinite(rE) else None,
                       input_energy=work,dissipated=loss,
                       heat_mean=heat.mean(axis=(1,2,3)).tolist(),heat_max=heat.max(axis=(1,2,3)).tolist(),
                       heat_max_position=[float(c[np.unravel_index(np.argmax(heat[0]),heat[0].shape)]) for c in (x,y,z)],
                       theta=rec)
            rows.append(row)
    thermal_error=float(np.max(abs(heat.mean(axis=(1,2,3))+cooled-loss)))
    total_error=float(np.max(abs(f.energy(f.u)+heat.mean(axis=(1,2,3))+cooled-work)))
    assert thermal_error<1e-10 and total_error<1e-6
    # save the final insulated theta field slice at the drive plane for the figure
    thE=float(factor(rows[-1]['r_E'],'signed'))
    slab=dict(z_index=n//2,excess=heat[0][:,:,n//2].tolist(),
              theta_signed=theta_field(heat[0][:,:,n//2],thE,'signed').tolist(),
              theta_clamp=theta_field(heat[0][:,:,n//2],float(factor(rows[-1]['r_E'],'clamp')),'clamp').tolist())
    # also vertical slice through the hot spot
    ix=int(np.argmax(heat[0].max(axis=(1,2))))
    slab['x_index']=ix;slab['excess_xz']=heat[0][ix,:,:].tolist()
    slab['theta_signed_xz']=theta_field(heat[0][ix,:,:],thE,'signed').tolist()
    result=dict(n=n,dt=dt,duration=duration,stop=stop,T0=1.,mapping=__doc__,
                thermal_error=thermal_error,total_error=total_error,first_crossings=first,rows=rows,final_slices=slab)
    print(n,dt,'theta_E final',{r:round(rows[-1]['theta'][r]['theta_E'],4) for r in rec},
          'theta min/max signed',round(rows[-1]['theta']['signed']['min'],4),round(rows[-1]['theta']['signed']['max'],4),
          'thermal err',thermal_error,flush=True)
    return result

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--n',type=int,default=24);ap.add_argument('--dt',type=float,default=.02)
    a=ap.parse_args()
    out=Path(__file__).with_name(f'theta_field_{a.n}_{a.dt}_results.json')
    out.write_text(json.dumps(run(a.n,a.dt),indent=1)+'\n')
    print('wrote',out)
