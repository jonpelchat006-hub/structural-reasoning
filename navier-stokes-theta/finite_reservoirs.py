"""Lumped liquid column joining two finite open reservoirs.

Transferred volume x, volume flow Q=x': I Q'=p(t)-K x-R Q-C |Q|Q.
I=rho*L/a is tube inertance (reservoir inertia neglected); hydrostatic
K=rho*g*(1/A1+1/A2). Scaled I=K=1, initial volume 2 in each reservoir,
maximum volume 4. Stop at |x|=2: emptying/overflow, not a singularity.
No spatial vortices, thermal or quantum physics. Parameters are illustrative.
"""
import json
from pathlib import Path
import numpy as np


def pressure(t,mode,omega):
    if mode=='constant':return .2
    if mode=='periodic':return .2*np.cos(omega*t)
    return 0.


def rhs(t,y,mode,omega,resistance,quadratic):
    x,q,_,_=y;p=pressure(t,mode,omega)
    return np.array([q,p-x-resistance*q-quadratic*abs(q)*q,
                     p*q,resistance*q*q+quadratic*abs(q)**3])


def step(t,y,dt,*args):
    a=rhs(t,y,*args);b=rhs(t+dt/2,y+dt*a/2,*args)
    c=rhs(t+dt/2,y+dt*b/2,*args);d=rhs(t+dt,y+dt*c,*args)
    return y+dt*(a+2*b+2*c+d)/6


def run(name,mode='none',resistance=.2,quadratic=0.,omega=1.,initial_x=0.,dt=.02,duration=150.):
    y=np.array([initial_x,0.,0.,0.]);energy0=.5*initial_x**2
    rows=[];t=0.;peakq=0.;peakx=abs(float(initial_x));max_error=0.;boundary=False
    args=(mode,omega,resistance,quadratic)
    rows.append([t,*map(float,y)])
    for i in range(round(duration/dt)):
        next_y=step(t,y,dt,*args);used=dt
        if abs(next_y[0])>=2:
            lo,hi=0.,dt
            for _ in range(40):
                mid=(lo+hi)/2
                if abs(step(t,y,mid,*args)[0])>=2:hi=mid
                else:lo=mid
            used=hi;next_y=step(t,y,used,*args);boundary=True
        t+=used;y=next_y
        peakq=max(peakq,abs(float(y[1])));peakx=max(peakx,abs(float(y[0])))
        error=.5*(y[0]**2+y[1]**2)-energy0-y[2]+y[3]
        max_error=max(max_error,abs(float(error)))
        if (i+1)%max(1,round(.1/dt))==0 or boundary:rows.append([t,*map(float,y)])
        if boundary:break
    assert max_error<1e-6
    assert abs(y[0])<=2+1e-10
    data=np.array(rows);late=data[data[:,0]>max(0,t-8*np.pi/omega)]
    amplitude=None;analytic=None
    if mode=='periodic' and not boundary:
        basis=np.column_stack((np.sin(omega*late[:,0]),np.cos(omega*late[:,0]),np.ones(len(late))))
        fit=np.linalg.lstsq(basis,late[:,1],rcond=None)[0]
        amplitude=float(np.hypot(fit[0],fit[1]))
        if quadratic==0:
            analytic=float(.2/np.sqrt((1-omega**2)**2+(resistance*omega)**2))
    result=dict(name=name,mode=mode,R=resistance,C=quadratic,omega=omega,dt=dt,
                end_time=t,capacity_reached=boundary,peak_volume_transfer=peakx,peak_flow=peakq,
                final_volume_transfer=float(y[0]),final_flow=float(y[1]),
                final_reservoir_volumes=[float(2-y[0]),float(2+y[0])],
                supplied_work=float(y[2]),dissipated_energy=float(y[3]),
                initial_energy=energy0,final_stored_energy=float(.5*(y[0]**2+y[1]**2)),
                max_energy_error=max_error,late_amplitude=amplitude,analytic_amplitude=analytic,
                late_flow_rms=float(np.sqrt(np.mean(late[:,2]**2))),
                columns=['time','transferred_volume','volume_flow','signed_work','dissipated_energy'],rows=rows)
    print(name,'capacity',boundary,'x final',round(float(y[0]),6),'amp',amplitude,
          'late flow RMS',round(result['late_flow_rms'],6),'end',round(t,4),flush=True)
    return result


def main():
    results=[run('displace_then_release',initial_x=.6),
             run('strongly_damped_release',initial_x=.6,resistance=2.5),
             run('steady_pressure',mode='constant')]
    for omega in (.5,.75,1.,1.25,1.5):
        results.append(run('periodic_'+str(omega),mode='periodic',omega=omega))
    results.append(run('periodic_with_extra_drag',mode='periodic',quadratic=.4))
    results.append(run('lossless_resonance',mode='periodic',resistance=0.))
    results.append(run('periodic_refined_dt',mode='periodic',dt=.01))
    exact=run('undamped_free_check',initial_x=.6,resistance=0.,duration=20.)
    data=np.array(exact['rows'])
    exact_error=float(np.max(abs(data[:,1]-.6*np.cos(data[:,0]))))
    assert exact_error<1e-7
    result=dict(cases=results,undamped_position_error=exact_error)
    Path(__file__).with_name('finite_reservoirs_results.json').write_text(json.dumps(result,indent=2)+'\n')
    print('max energy error',max(r['max_energy_error'] for r in results),'undamped error',exact_error)


if __name__=='__main__':main()
