"""Equal delivered kinetic work, different azimuthal drive placement schedules.

One smooth localized rotational field active in each .2 time slot, except the
simultaneous-eight control. Existing energy-kick integrator at fixed power .04
with .2 startup ramp. These are ideal discrete powered controls, not magnets
or a smooth-forcing singularity construction. There is no global reversing
column here, so timing relative to such an oscillation is tested separately.
"""
import argparse
import json
from pathlib import Path
import numpy as np
from pin_ring import setup
from ring_power import kick
from stacked_layers import plane
from vortex3d import fft,real,cross


def angles(kind,slots,seed):
    if kind=='random':return np.random.default_rng(seed).uniform(0,2*np.pi,slots)
    increment={'fixed':0.,'regular8':1/8,'golden':(3-np.sqrt(5))/2,
               'sqrt2':np.sqrt(2)-1,'rational55_144':55/144}[kind]
    return 2*np.pi*(np.arange(slots)*increment%1)


def direction_at(f,coords,angle):
    x,y,z=coords
    center=(np.pi+.8*np.cos(angle),np.pi+.8*np.sin(angle),np.pi)
    delta=np.array([(q-c+np.pi)%(2*np.pi)-np.pi for q,c in zip(coords,center)])
    axis=np.array([np.full_like(x,np.sin(angle)),np.full_like(x,-np.cos(angle)),np.zeros_like(x)])
    direction=f.project(fft(cross(axis,delta)*np.exp(-np.sum(delta**2,axis=0)/(2*.38**2))))
    direction[:,0,0,0]=0
    return direction


def run(n,kind,seed=2026,dt=.02,duration=4.):
    f,x,y,z=setup(n,8);f.dt=dt
    control=f.force.copy();control[:,0,0,0]=0;f.force*=0
    schedule=None if kind=='simultaneous8' else angles(kind,round(duration/.2),seed)
    radius=np.hypot(x[:,:,0]-np.pi,y[:,:,0]-np.pi)
    core=radius<.45;outer=(radius>1)&(radius<1.5)
    rows=[];loss=work=throughput=0.;previous_flux=0.;peak_speed=peak_omega=0.;max_cfl=0.
    cache={};direction=control
    for i in range(round(duration/dt)):
        slot=int((i+.5)*dt/.2)
        if schedule is not None:
            angle=float(schedule[slot])
            if angle not in cache:cache[angle]=direction_at(f,(x,y,z),angle)
            direction=cache[angle]
        amount=.04*min((i+.5)*dt/.2,1)*dt
        kick(f,direction,amount/2)
        _,d=f.step(False);loss+=d
        kick(f,direction,amount/2);work+=amount
        u=real(f.u);above=plane(u[2],np.pi+.8)
        flux=float(np.maximum(above,0).mean()*(2*np.pi)**2)
        throughput+=dt*(previous_flux+flux)/2;previous_flux=flux
        max_cfl=max(max_cfl,float(np.max(np.sum(abs(u),axis=0))*dt*n/(2*np.pi)))
        peak_speed=max(peak_speed,float(np.linalg.norm(u,axis=0).max()))
        if (i+1)%round(.1/dt)==0:
            row=f.measure((i+1)*dt);peak_omega=max(peak_omega,row['max_vorticity'])
            e=np.sum(u*u,axis=0)/2
            row.update(upward_volume_flux=flux,cumulative_upward_crossing_volume=throughput,
                       net_volume_flux=float(above.mean()*(2*np.pi)**2),
                       core_velocity=float(above[core].mean()),outer_velocity=float(above[outer].mean()),
                       effective_energy_volume_fraction=float(e.mean()**2/np.mean(e*e)),
                       work=work,dissipation=loss)
            rows.append(row)
    error=f.energy(f.u)-work+loss
    assert abs(error)<2e-6, f'energy residual {error:g} exceeds tolerance'
    assert max_cfl<.5, f'maximum CFL {max_cfl:g} exceeds chosen .5 check'
    assert max(abs(r['net_volume_flux']) for r in rows)<1e-10
    result=dict(n=n,kind=kind,seed=seed,dt=dt,duration=duration,slot_duration=.2,
                input=work,dissipation=loss,budget_error=error,max_cfl=max_cfl,
                peak_speed=peak_speed,sampled_peak_vorticity=peak_omega,
                cumulative_upward_crossing_volume=throughput,
                angles=[] if schedule is None else schedule.tolist(),rows=rows)
    print('placement',n,kind,seed,dt,'crossings',round(throughput,5),
          'E',round(rows[-1]['energy'],6),'peak speed',round(peak_speed,5),flush=True)
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--n',type=int,default=24)
    parser.add_argument('--dt',type=float,default=.02)
    parser.add_argument('--append',action='store_true')
    parser.add_argument('--kinds',nargs='+',default=['simultaneous8','fixed','regular8','golden','sqrt2','rational55_144','random'])
    args=parser.parse_args()
    out=Path(__file__).with_name(f'ring_placement_{args.n}_{args.dt:g}_results.json')
    results=json.loads(out.read_text()) if args.append and out.exists() else []
    for kind in args.kinds:
        for seed in ((2026,2027,2028) if kind=='random' else (2026,)):
            if any(r['kind']==kind and r['seed']==seed for r in results):continue
            results.append(run(args.n,kind,seed,args.dt));out.write_text(json.dumps(results,indent=2)+'\n')
