"""Two-stage recapture test in the existing periodic 3D NS solver.

Same total work in all cases. Measure the same material labels at three
upward-crossing gates: lower face, waist, upper face of the second stage.
Radial width and mean radius are separate; no assumed density compression.
"""
import argparse
import json
from pathlib import Path
import numpy as np
from helical_annulus import setup, L
from vortex3d import real
from ring_power import kick
from threshold_transport import interp
from stacked_layers import plane


def direction_for(f,base,mode):
    layers=[(2.,1)]
    if mode!='single':
        layers.append((3.6,-1 if mode=='reversed' else 1))
    result=sum(sign*base*np.exp(-1j*f.k[2]*(height-np.pi)) for height,sign in layers)
    result=f.project(result)
    result[:,0,0,0]=0
    result/=np.sqrt(2*f.energy(result))
    return result,layers


class GateLabels:
    def __init__(self):
        # Three equal-size radial groups allow tracking width, not just radius.
        angle=np.tile(np.arange(48)*L/48,3)
        radius=np.repeat([.95,1.10,1.25],48)
        self.initial=np.column_stack((np.pi+radius*np.cos(angle),np.pi+radius*np.sin(angle),np.full(144,1.6)))
        self.p=self.initial.copy()
        self.boundary=np.zeros(144,dtype=bool)
        self.gates=np.array([3.,3.6,4.2])
        self.cross_time=np.full((3,144),np.nan)
        self.cross_radius=np.full((3,144),np.nan)
        self.cross_speed=np.full((3,144),np.nan)
        self.cross_uz=np.full((3,144),np.nan)
        self.paths=[]

    def step(self,u,dt,t):
        previous=self.p.copy()
        mid=previous+dt*interp(u,previous)/2
        velocity=interp(u,mid)
        self.p+=dt*velocity
        self.boundary|=np.any((self.p<0)|(self.p>=L),axis=1)
        for j,height in enumerate(self.gates):
            crossing=(previous[:,2]<height)&(self.p[:,2]>=height)&np.isnan(self.cross_time[j])&~self.boundary
            ids=np.flatnonzero(crossing)
            if not ids.size:
                continue
            frac=(height-previous[ids,2])/(self.p[ids,2]-previous[ids,2])
            positions=previous[ids]+frac[:,None]*(self.p[ids]-previous[ids])
            velocities=interp(u,positions)
            self.cross_time[j,ids]=t-dt+frac*dt
            self.cross_radius[j,ids]=np.linalg.norm(positions[:,:2]-np.pi,axis=1)
            self.cross_speed[j,ids]=np.linalg.norm(velocities,axis=1)
            self.cross_uz[j,ids]=velocities[:,2]

    def report(self):
        gates=[]
        for j,height in enumerate(self.gates):
            arrived=np.isfinite(self.cross_time[j])
            gates.append(dict(z=float(height),fraction_arrived=float(arrived.mean()),count=int(arrived.sum())))
        pairs=[]
        for a,b in ((0,1),(1,2),(0,2)):
            common=np.isfinite(self.cross_time[a])&np.isfinite(self.cross_time[b])
            # First upward crossing of the upper gate must be later for each label.
            assert np.all(self.cross_time[b,common]>=self.cross_time[a,common])
            row=dict(from_z=float(self.gates[a]),to_z=float(self.gates[b]),matched_labels=int(common.sum()))
            if common.any():
                r0,r1=self.cross_radius[a,common],self.cross_radius[b,common]
                row.update(mean_radius_in=float(r0.mean()),mean_radius_out=float(r1.mean()),
                    mean_radial_displacement=float((r1-r0).mean()),
                    radial_sd_in=float(r0.std()),radial_sd_out=float(r1.std()),
                    width_ratio=float(r1.std()/r0.std()) if r0.std()>1e-10 else None,
                    mean_crossing_speed_in=float(self.cross_speed[a,common].mean()),
                    mean_crossing_speed_out=float(self.cross_speed[b,common].mean()),
                    mean_crossing_uz_in=float(self.cross_uz[a,common].mean()),
                    mean_crossing_uz_out=float(self.cross_uz[b,common].mean()),
                    mean_transit_time=float((self.cross_time[b,common]-self.cross_time[a,common]).mean()))
            pairs.append(row)
        # Positions at different crossing times are not simultaneous cross-sections
        # of a steady streamtube: the width statistic is only a matched-label diagnostic.
        return dict(gates=gates,matched_gate_pairs=pairs,
                    fraction_any_boundary=float(self.boundary.mean()),
                    crossing_times=[[None if not np.isfinite(v) else float(v) for v in r] for r in self.cross_time],
                    crossing_radii=[[None if not np.isfinite(v) else float(v) for v in r] for r in self.cross_radius])


def run(n,mode,dt=.01,duration=6.):
    f,base,coords,rr,cs,sn,_=setup(n,.25,dt=dt)
    direction,layers=direction_for(f,base,mode)
    radial=rr[:,:,0]
    band=(radial>.85)&(radial<1.35)
    tracer=GateLabels()
    rows=[]
    energy=loss=max_error=max_cfl=peak_speed=0.
    for i in range(round(duration/dt)):
        t0=i*dt;t=(i+1)*dt
        amount=.04*min((t0+dt/2)/.2,1)*dt
        kick(f,direction,amount/2)
        previous=f.u.copy()
        _,d=f.step(False)
        loss+=d
        midpoint=real((previous+f.u)/2)
        kick(f,direction,amount/2)
        energy+=amount
        if t0>=1-1e-10:
            tracer.step(midpoint,dt,t)
        u=real(f.u)
        max_cfl=max(max_cfl,float(np.max(np.sum(abs(u),axis=0))*dt*n/L))
        peak_speed=max(peak_speed,float(np.linalg.norm(u,axis=0).max()))
        max_error=max(max_error,abs(f.energy(f.u)-energy+loss))
        assert max_cfl<.5
        if (i+1)%round(.1/dt)==0:
            ur=u[0]*cs+u[1]*sn
            row=f.measure(t)
            row.update(input_energy=energy,dissipation=loss,planes=[])
            for height in tracer.gates:
                vz=plane(u[2],height)
                vr=plane(ur,height)
                row['planes'].append(dict(z=float(height),mean_band_radial=float(vr[band].mean()),
                    mean_band_axial=float(vz[band].mean()),net_flux=float(vz.mean()*L*L)))
            rows.append(row)
            if t>=1:
                tracer.paths.append(dict(t=t,positions=tracer.p[np.arange(0,144,12)].tolist()))
    assert max_error<2e-6
    assert max(abs(p['net_flux']) for r in rows for p in r['planes'])<1e-10
    result=dict(n=n,mode=mode,dt=dt,duration=duration,layers=layers,input_energy=energy,
        dissipation=loss,max_energy_error=max_error,max_cfl=max_cfl,peak_speed=peak_speed,
        sampled_peak_vorticity=max(r['max_vorticity'] for r in rows),
        rows=rows,labels=tracer.report(),sample_paths=tracer.paths)
    print(n,mode,'peak speed',round(peak_speed,5),
          'gates',[r['count'] for r in result['labels']['gates']],
          'focus',[(r.get('width_ratio'),r.get('mean_radial_displacement')) for r in result['labels']['matched_gate_pairs']],flush=True)
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--n',type=int,default=24)
    p.add_argument('--dt',type=float,default=.01)
    p.add_argument('--modes',nargs='+',default=['single','aligned','reversed'])
    p.add_argument('--append',action='store_true')
    args=p.parse_args()
    out=Path(__file__).with_name(f'vortex_chain_focus_{args.n}_{args.dt:g}_results.json')
    results=json.loads(out.read_text()) if args.append and out.exists() else []
    for mode in args.modes:
        if any(r['mode']==mode for r in results):
            continue
        results.append(run(args.n,mode,args.dt))
        out.write_text(json.dumps(results,indent=2)+'\n',encoding='utf-8')
