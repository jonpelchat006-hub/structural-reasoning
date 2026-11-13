"""Equal-work 3D annular rise with central/outer returns and added axial swirl.

Periodic spectral incompressible NS, nu=.03, initially at rest. Smooth projected
body-force SHAPES, powered by discrete kinetic-energy increments. No physical
tube, plate, heat, magnets, explosions, or theta-dependent material law.
Swirl fraction describes the squared norm of a forcing direction, not the
fraction of actual work going into swirl once nonlinear flow develops.
"""
import argparse
import json
from pathlib import Path
import numpy as np
from vortex3d import Flow, fft, real, cross
from ring_power import kick
from threshold_transport import interp

L = 2*np.pi


def setup(n, fraction, sign=1, dt=.01):
    f = Flow(n, 'control', dt)
    f.u *= 0
    f.force *= 0
    x,y,z = np.meshgrid(*(np.arange(n)*L/n for _ in range(3)), indexing='ij')
    dx,dy,dz = x-np.pi,y-np.pi,z-np.pi
    radius2 = dx*dx+dy*dy
    envelope = np.exp(-dz*dz/(2*.8**2))
    # A_theta = r*(r^2-1)*exp(-r^2/.8)*g(z). Curl gives an upward
    # annulus between approximate radii .597 and 1.498, with two returns.
    h = (radius2-1)*np.exp(-radius2/.8)*envelope
    vector_potential = fft(np.array([-dy*h,dx*h,np.zeros_like(x)]))
    poloidal = f.project(1j*cross(f.k, vector_potential))
    band = np.exp(-.5*((radius2-1.05**2)/(2*1.05*.4))**2)*envelope
    toroidal = f.project(fft(np.array([-dy*band,dx*band,np.zeros_like(x)])))
    poloidal[:,0,0,0] = 0
    toroidal[:,0,0,0] = 0
    poloidal /= np.sqrt(2*f.energy(poloidal))
    overlap = float(np.mean(np.sum(real(poloidal)*real(toroidal),axis=0)))
    toroidal -= overlap*poloidal
    toroidal /= np.sqrt(2*f.energy(toroidal))
    direction = np.sqrt(1-fraction)*poloidal+sign*np.sqrt(fraction)*toroidal
    assert abs(2*f.energy(direction)-1) < 1e-12
    rr = np.sqrt(radius2)
    cos = np.divide(dx,rr,out=np.ones_like(rr),where=rr>0)
    sin = np.divide(dy,rr,out=np.zeros_like(rr),where=rr>0)
    return f,direction,(x,y,z),rr,cos,sin,overlap


class Labels:
    """Passive parcels; they are not particles with independent inertia."""
    def __init__(self):
        angle = np.arange(64)*L/64
        radii = np.repeat([.25,1.05,1.9],64)
        angles = np.tile(angle,3)
        self.initial = np.column_stack((np.pi+radii*np.cos(angles),
                    np.pi+radii*np.sin(angles),np.full(192,np.pi-.4)))
        self.p = self.initial.copy()
        self.max_rise = np.zeros(192)
        self.returned = np.zeros(192,dtype=bool)
        self.return_local = np.zeros(192,dtype=bool)
        self.boundary = np.zeros(192,dtype=bool)
        self.turns = np.zeros(192)
        self.up_turns = np.zeros(192)
        self.max_up_turns = np.zeros(192)
        self.current_up_turns = np.zeros(192)
        self.min_up_radius = np.full(192,np.inf)
        self.max_up_radius = np.zeros(192)
        self.sample_paths = []

    def step(self, velocity, dt):
        previous = self.p.copy()
        mid = previous+dt*interp(velocity,previous)/2
        v = interp(velocity,mid)
        self.p += dt*v
        self.boundary |= np.any((self.p<0)|(self.p>=L),axis=1)
        old_angle = np.arctan2(previous[:,1]-np.pi,previous[:,0]-np.pi)
        new_angle = np.arctan2(self.p[:,1]-np.pi,self.p[:,0]-np.pi)
        da = (new_angle-old_angle+np.pi)%L-np.pi
        radius = np.linalg.norm(self.p[:,:2]-np.pi,axis=1)
        reliable = (~self.boundary)&(radius>.2)
        upward = reliable&(v[:,2]>.02)
        self.turns += np.where(reliable,da/L,0)
        self.up_turns += np.where(upward,abs(da)/L,0)
        self.current_up_turns = np.where(upward,self.current_up_turns+abs(da)/L,0)
        self.max_up_turns = np.maximum(self.max_up_turns,self.current_up_turns)
        self.min_up_radius = np.minimum(self.min_up_radius,np.where(upward,radius,np.inf))
        self.max_up_radius = np.maximum(self.max_up_radius,np.where(upward,radius,0))
        height = self.p[:,2]-self.initial[:,2]
        self.max_rise = np.maximum(self.max_rise,height)
        event=(self.max_rise>=.3)&(height<=0)&(v[:,2]<0)&~self.returned
        self.returned |= event
        self.return_local |= event&~self.boundary

    def report(self):
        result=[]
        for j,r in enumerate((.25,1.05,1.9)):
            sl=slice(64*j,64*(j+1))
            minimum=self.min_up_radius[sl]
            result.append(dict(initial_radius=r,labels=64,
                median_max_rise=float(np.median(self.max_rise[sl])),
                fraction_rise_0_3=float(np.mean(self.max_rise[sl]>=.3)),
                fraction_local_return=float(self.return_local[sl].mean()),
                fraction_boundary_crossing=float(self.boundary[sl].mean()),
                median_signed_turns=float(np.median(self.turns[sl])),
                median_cumulative_upward_turns=float(np.median(self.up_turns[sl])),
                median_max_continuous_upward_turns=float(np.median(self.max_up_turns[sl])),
                median_minimum_upward_radius=float(np.median(minimum[np.isfinite(minimum)])) if np.isfinite(minimum).any() else None,
                median_maximum_upward_radius=float(np.median(self.max_up_radius[sl]))))
        return result


def run(n,fraction,sign=1,dt=.01,duration=4.,stop=4.):
    f,direction,coords,rr,cs,sn,overlap=setup(n,fraction,sign,dt)
    h=L/n
    radius=rr[:,:,n//2]
    masks=[radius<.5,(radius>.75)&(radius<1.35),(radius>1.65)&(radius<2.15)]
    names=('core','rising_band','outer_return')
    rows=[]
    labels=Labels()
    loss=work=cumulative_flux=0.
    max_cfl=peak_speed=max_error=0.
    previous_flux=0.
    stride=round(.1/dt)
    assert abs(stride*dt-.1)<1e-10
    for i in range(round(duration/dt)):
        t0=i*dt
        amount=.04*min((t0+dt/2)/.2,1)*dt if t0+dt/2<stop else 0.
        kick(f,direction,amount/2)
        before=f.u.copy()
        _,d=f.step(False)
        loss+=d
        mid=real((before+f.u)/2)
        kick(f,direction,amount/2)
        work+=amount
        u=real(f.u)
        speed=np.linalg.norm(u,axis=0)
        max_cfl=max(max_cfl,float(np.max(np.sum(abs(u),axis=0))*dt/h))
        peak_speed=max(peak_speed,float(speed.max()))
        assert max_cfl<.5, f'CFL {max_cfl:g}'
        e=float(np.mean(speed*speed)/2)
        max_error=max(max_error,abs(e-work+loss))
        if t0>=1-1e-10:
            labels.step(mid,dt)
        uz=u[2,:,:,n//2]
        flux=float(np.maximum(uz,0).sum()*h*h)
        cumulative_flux+=dt*(previous_flux+flux)/2
        previous_flux=flux
        if (i+1)%stride==0:
            ur=u[0]*cs+u[1]*sn
            ut=-u[0]*sn+u[1]*cs
            row=f.measure((i+1)*dt)
            row.update(input_energy=work,dissipated_energy=loss,
                radial_energy=float(np.mean(ur*ur)/2),swirl_energy=float(np.mean(ut*ut)/2),
                axial_energy=float(np.mean(u[2]**2)/2),
                max_abs_swirl=float(abs(ut).max()),max_upward_speed=float(u[2].max()),
                max_abs_radial=float(abs(ur).max()),net_plane_flux=float(uz.sum()*h*h),
                upward_flux=flux,cumulative_upward_crossing_volume=cumulative_flux)
            assert abs(row['radial_energy']+row['swirl_energy']+row['axial_energy']-e)<1e-12
            for name,mask in zip(names,masks):
                row[name+'_mean_axial']=float(uz[mask].mean())
                row[name+'_mean_swirl']=float(ut[:,:,n//2][mask].mean())
            selected=masks[1]&(uz>.05)&(abs(ut[:,:,n//2])>.05)
            row['median_rising_band_pitch']=float(np.median(L*radius[selected]*uz[selected]/abs(ut[:,:,n//2][selected]))) if selected.any() else None
            efield=speed*speed/2
            row['effective_energy_volume_fraction']=float(efield.mean()**2/np.mean(efield**2))
            rows.append(row)
            if (i+1)*dt>=1:
                # Four azimuths per group, unwrapped positions, for review.
                labels.sample_paths.append(dict(t=(i+1)*dt,positions=labels.p[np.arange(0,192,16)].tolist()))
    assert max_error<2e-6, f'energy error {max_error:g}'
    assert max(abs(r['net_plane_flux']) for r in rows)<1e-10
    result=dict(n=n,dt=dt,duration=duration,stop=stop,swirl_fraction=fraction,swirl_sign=sign,
                forcing_overlap_before_orthogonalization=overlap,
                input_energy=work,dissipated_energy=loss,max_budget_error=max_error,
                max_cfl=max_cfl,peak_speed=peak_speed,
                sampled_peak_vorticity=max(r['max_vorticity'] for r in rows),
                rows=rows,cohorts=labels.report(),sample_paths=labels.sample_paths,
                radial_profile=[dict(radius=float(a+.125),mean_axial=float(uz[(radius>=a)&(radius<a+.25)].mean()),
                    mean_swirl=float(ut[:,:,n//2][(radius>=a)&(radius<a+.25)].mean()))
                    for a in np.arange(0,2.5,.25)])
    print(n,fraction,sign,'speed',round(peak_speed,5),'vz',round(rows[-1]['max_upward_speed'],5),
          'up turns',round(result['cohorts'][1]['median_max_continuous_upward_turns'],4),
          'returns',[round(rows[-1][name+'_mean_axial'],5) for name in names],flush=True)
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--n',type=int,default=24)
    p.add_argument('--dt',type=float,default=.01)
    p.add_argument('--fractions',nargs='+',type=float,default=[0,.25,.75,.95,1.])
    p.add_argument('--sign',type=int,default=1,choices=(-1,1))
    p.add_argument('--duration',type=float,default=4.)
    p.add_argument('--stop',type=float,default=4.)
    p.add_argument('--append',action='store_true')
    args=p.parse_args()
    out=Path(__file__).with_name(f'helical_annulus_{args.n}_{args.dt:g}_{args.sign}_{args.duration:g}_{args.stop:g}_results.json')
    results=json.loads(out.read_text()) if args.append and out.exists() else []
    for fraction in args.fractions:
        assert 0<=fraction<=1
        if any(r['swirl_fraction']==fraction for r in results):
            continue
        results.append(run(args.n,fraction,args.sign,args.dt,args.duration,args.stop))
        out.write_text(json.dumps(results,indent=2)+'\n',encoding='utf-8')
