"""Smooth feedback pulses in the finite-reservoir oscillator; fixed positive work.

I=K=1, R=.2, C=0; initial mechanical energy .08. Phase atan2(x,Q)
is zero at the upward equilibrium crossing. Offset is the pulse-center phase.
Pressure is bounded by .3, with two smooth opposite pulses per cycle.
Stop at cumulative positive pressure work .4; record absorbed work separately.
This is a feedback controller, not a fixed clock with a shifted start time.
"""
import json
import math
from pathlib import Path
import numpy as np


def rhs(y, offset):
    x,q,_,_,_=y
    theta=math.atan2(x,q)
    a=theta-offset
    p=.3*math.tanh(10*math.cos(a))*math.exp(2*(math.cos(2*a)-1))
    power=p*q
    return np.array([q,p-x-.2*q,max(power,0),max(-power,0),.2*q*q])


def step(y,h,offset):
    a=rhs(y,offset);b=rhs(y+h*a/2,offset)
    c=rhs(y+h*b/2,offset);d=rhs(y+h*c,offset)
    return y+h*(a+2*b+2*c+d)/6


def run(degrees,initial_phase=0.,dt=.005):
    y=np.array([.4*math.sin(initial_phase),.4*math.cos(initial_phase),0.,0.,0.])
    offset=math.radians(degrees);t=0.;error=0.;rows=[];peak=abs(y[1]);done=False
    for i in range(round(120/dt)):
        h=dt;next_y=step(y,h,offset)
        if next_y[2]>=.4:
            lo,hi=0.,h
            for _ in range(35):
                mid=(lo+hi)/2
                if step(y,mid,offset)[2]>=.4:hi=mid
                else:lo=mid
            h=hi;next_y=step(y,h,offset);done=True
        y=next_y;t+=h;peak=max(peak,abs(float(y[1])))
        energy=.5*(y[0]**2+y[1]**2)
        error=max(error,abs(energy-.08-y[2]+y[3]+y[4]))
        assert abs(y[0])<2
        if (i+1)%round(.1/dt)==0 or done:rows.append([t,*map(float,y)])
        if done:break
    assert error<2e-6
    result=dict(offset_degrees=degrees,initial_phase=initial_phase,dt=dt,
                reached_budget=done,end_time=t,positive_work=float(y[2]),
                absorbed_work=float(y[3]),dissipation=float(y[4]),
                initial_energy=.08,final_energy=float(energy),peak_flow=peak,
                max_energy_error=error,columns=['t','x','Q','positive_work','absorbed_work','dissipation'],rows=rows)
    print('phase',degrees,'initial',round(initial_phase,3),'budget',done,'time',round(t,3),
          'energy',round(energy,6),'peak Q',round(peak,5),flush=True)
    return result


if __name__=='__main__':
    results=[run(d,phase) for phase in (0.,math.pi/2) for d in (-75,-45,-15,0,15,45,75)]
    results.extend(run(d,dt=.0025) for d in (0,15))
    Path(__file__).with_name('phase_budget_results.json').write_text(json.dumps(results,indent=2)+'\n')
