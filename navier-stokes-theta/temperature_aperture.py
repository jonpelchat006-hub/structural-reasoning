"""Dimensionless, prescribed-conduit thermomagnetic tests; not 3D Navier--Stokes.

The aperture transit uses the exact on-axis field shape of a thin current loop.
The circulation test uses a smooth periodic field-energy profile along a GIVEN
closed path. It does not compute the field of a plate, create vortices, or fit a
real material. The chosen linear susceptibility is valid only while positive.

Thermal coupling follows the illustrative free energy
  psi(T,s) = c*T*(1-log(T)) - (a-b*T)*Phi(s).
Then entropy = c*log(T)-b*Phi and internal energy = c*T-a*Phi.
The b*T*Q*Phi_s term is essential: magnetic work is paid for thermally.
Drag heat returns to the liquid. Heater and cooler exchange are both recorded.
"""
import argparse
import json
from pathlib import Path
import numpy as np


def rk4(y, dt, rhs):
    k1 = rhs(y)
    k2 = rhs(y + dt*k1/2)
    k3 = rhs(y + dt*k2/2)
    k4 = rhs(y + dt*k3)
    return y + dt*(k1+2*k2+2*k3+k4)/6


def aperture_transit(chi=1.2, drag=0., speed=.25, dt=.002):
    def phi(z):
        return .5/(1+z*z)**3

    def rhs(y):
        z, v, _ = y
        gradient = -3*z/(1+z*z)**4
        return np.array([v, chi*gradient-drag*v, drag*v*v])

    y = np.array([-3., speed, 0.])
    energy0 = .5*speed*speed-chi*phi(-3.)
    max_error = 0.
    peak_speed = speed
    crossing_speed = None
    exit_speed = None
    exit_time = None
    for i in range(round(150/dt)):
        old = y.copy()
        y = rk4(y, dt, rhs)
        max_error = max(max_error, abs(.5*y[1]**2-chi*phi(y[0])+y[2]-energy0))
        peak_speed = max(peak_speed, abs(y[1]))
        if crossing_speed is None and old[0] < 0 <= y[0]:
            crossing_speed = float(y[1])
        if y[0] >= 3:
            # Resolve the exit event rather than using an overshot endpoint.
            lo, hi = 0., dt
            for _ in range(35):
                mid = (lo+hi)/2
                if rk4(old, mid, rhs)[0] >= 3:
                    hi = mid
                else:
                    lo = mid
            y = rk4(old, hi, rhs)
            exit_speed = float(y[1])
            exit_time = i*dt+hi
            break
    assert max_error < 1e-8
    if drag == 0:
        assert exit_speed is not None and abs(exit_speed-speed) < 1e-7
    return dict(chi=chi, drag=drag, initial_speed=speed,
                plate_crossing_speed=crossing_speed, peak_speed=float(peak_speed),
                escaped_to_z3=exit_speed is not None, exit_speed=exit_speed,
                exit_time=exit_time, final_z=float(y[0]), final_speed=float(y[1]),
                max_energy_error=float(max_error))


def cases():
    return [
        dict(name='hot_base_cool_approach', heater=-2.2, cooler=-.8),
        dict(name='hot_base_slow_cooling', heater=-2.2, cooler=-.8, cooling=.1),
        dict(name='hot_base_fast_cooling', heater=-2.2, cooler=-.8, cooling=3.2),
        dict(name='heat_at_aperture_cool_return', heater=0., cooler=np.pi),
        dict(name='heat_after_aperture_cool_return', heater=.35, cooler=np.pi),
        dict(name='heat_at_aperture_slow_cooling', heater=0., cooler=np.pi, cooling=.1),
        dict(name='heat_at_aperture_fast_cooling', heater=0., cooler=np.pi, cooling=3.2),
        dict(name='constant_susceptibility', heater=0., cooler=np.pi, b=0.),
        dict(name='no_magnet', heater=0., cooler=np.pi, field=0.),
        dict(name='equal_bath_temperatures', heater=0., cooler=np.pi, hot=1.5, cold=1.5),
        dict(name='thermal_sources_off_at_120', heater=0., cooler=np.pi, stop=120.),
    ]


def run_loop(n=96, dt=.02, duration=300.):
    config = cases()
    m = len(config)
    s = np.linspace(-np.pi, np.pi, n, endpoint=False)
    ds = 2*np.pi/n
    # Prescribed field-energy landscape with its maximum at the aperture.
    phi = np.exp(4*(np.cos(s)-1))
    g = -4*np.sin(s)*phi
    assert abs(g.mean()) < 1e-14
    def column(key, default):
        return np.array([z.get(key, default) for z in config])[:, None]
    def zone(center):
        return np.exp((np.cos(s[None, :]-center)-1)/.35**2)

    a = 1.8
    b = column('b', .6)
    c = 4.
    resistance, quadratic, diffusivity = .05, .03, .003
    grad = column('field', 1.)*g
    mean_phi = column('field', 1.)[:, 0]*phi.mean()
    h = .8*zone(column('heater', 0.))
    cool = column('cooling', .8)*zone(column('cooler', np.pi))
    hot_t, cold_t = column('hot', 2.), column('cold', 1.)
    stop = column('stop', duration+1.)
    # T cells, Q, signed hot heat, signed cold heat, magnetic work, drag heat,
    # signed circuits, and entropy delivered to the two reservoirs.
    y = np.zeros((m, n+7))
    y[:, :n] = 1.5
    y[:, n] = .15
    e0 = .5*y[:, n]**2 + c*y[:, :n].mean(axis=1)-a*mean_phi
    k0 = .5*y[:, n]**2
    s0 = c*np.log(y[:, :n]).mean(axis=1)-b[:, 0]*mean_phi
    max_energy = np.zeros(m)
    max_mechanical = np.zeros(m)
    min_entropy = np.zeros(m)
    max_cfl = np.zeros(m)
    min_t = np.full(m, 1.5)
    max_t = min_t.copy()
    min_chi = np.full(m, np.inf)
    peak_q = np.full(m, .15)
    history = []

    def rhs(v):
        temp, q = v[:, :n], v[:, n:n+1]
        left, right = np.roll(temp, 1, axis=1), np.roll(temp, -1, axis=1)
        advection = -np.maximum(q, 0)*(temp-left)/ds-np.minimum(q, 0)*(right-temp)/ds
        diffusion = diffusivity*(left-2*temp+right)/ds**2
        chi = a-b*temp
        force = np.mean(chi*grad, axis=1, keepdims=True)
        loss = resistance*q*q+quadratic*np.abs(q)**3
        qh = enabled*c*h*(hot_t-temp)
        qc = enabled*c*cool*(cold_t-temp)
        dy = np.zeros_like(v)
        dy[:, :n] = advection+diffusion+(qh+qc+b*temp*q*grad+loss)/c
        dy[:, n:n+1] = force-resistance*q-quadratic*np.abs(q)*q
        dy[:, n+1] = qh.mean(axis=1)
        dy[:, n+2] = qc.mean(axis=1)
        dy[:, n+3] = (q*force)[:, 0]
        dy[:, n+4] = loss[:, 0]
        dy[:, n+5] = q[:, 0]/(2*np.pi)
        dy[:, n+6] = -np.mean(qh/hot_t+qc/cold_t, axis=1)
        return dy

    count = round(duration/dt)
    assert abs(count*dt-duration) < 1e-10
    for i in range(count):
        # Switch sources at a step boundary, using the same value at all stages.
        enabled = ((i+.5)*dt < stop)
        y = rk4(y, dt, rhs)
        temp, q = y[:, :n], y[:, n]
        energy = .5*q*q+c*temp.mean(axis=1)-a*mean_phi
        max_energy = np.maximum(max_energy, abs(energy-e0-y[:, n+1]-y[:, n+2]))
        max_mechanical = np.maximum(max_mechanical, abs(.5*q*q-k0-y[:, n+3]+y[:, n+4]))
        entropy = c*np.log(temp).mean(axis=1)-b[:, 0]*mean_phi-s0+y[:, n+6]
        min_entropy = np.minimum(min_entropy, entropy)
        min_t = np.minimum(min_t, temp.min(axis=1))
        max_t = np.maximum(max_t, temp.max(axis=1))
        min_chi = np.minimum(min_chi, (a-b*temp).min(axis=1))
        peak_q = np.maximum(peak_q, abs(q))
        max_cfl = np.maximum(max_cfl, abs(q)*dt/ds+2*diffusivity*dt/ds**2)
        if i % max(1, round(.5/dt)) == 0 or i == count-1:
            history.append(dict(time=(i+1)*dt, flow=q.tolist(), temperature=temp.mean(axis=1).tolist()))
    assert np.isfinite(y).all() and min_t.min() > 0 and min_chi.min() > 0
    assert max_cfl.max() < .8
    assert max_energy.max() < 1e-7 and max_mechanical.max() < 1e-7
    assert min_entropy.min() > -1e-7
    results = []
    tail = [row['flow'] for row in history if row['time'] > duration-30]
    for j, spec in enumerate(config):
        temp, q = y[j, :n], y[j, n]
        row = dict(**spec, final_flow=float(q), late_mean_flow=float(np.mean(np.array(tail)[:, j])),
                   late_flow_range=float(np.ptp(np.array(tail)[:, j])), peak_abs_flow=float(peak_q[j]),
                   final_mean_temperature=float(temp.mean()), min_temperature=float(min_t[j]),
                   max_temperature=float(max_t[j]), min_susceptibility=float(min_chi[j]),
                   hot_bath_heat=float(y[j, n+1]), cold_bath_heat=float(y[j, n+2]),
                   magnetic_work=float(y[j, n+3]), drag_heat=float(y[j, n+4]),
                   signed_circuits=float(y[j, n+5]), total_entropy_change=float(entropy[j]),
                   minimum_total_entropy_change=float(min_entropy[j]),
                   max_energy_error=float(max_energy[j]), max_mechanical_error=float(max_mechanical[j]),
                   max_cfl=float(max_cfl[j]), final_temperature_profile=temp.tolist())
        results.append(row)
        print(spec['name'], 'flow', round(q, 7), 'heat', round(row['hot_bath_heat'], 5), flush=True)
    return dict(n=n, dt=dt, duration=duration, constants=dict(c=c, a=a, default_b=.6,
                resistance=resistance, quadratic=quadratic, diffusivity=diffusivity),
                s=s.tolist(), field_energy=phi.tolist(), field_gradient=g.tolist(),
                cases=results, history=history)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--n', type=int, default=96)
    parser.add_argument('--dt', type=float, default=.02)
    parser.add_argument('--duration', type=float, default=300.)
    parser.add_argument('--transit', action='store_true')
    args = parser.parse_args()
    result = run_loop(args.n, args.dt, args.duration)
    if args.transit:
        result['aperture_transits'] = [aperture_transit(chi=chi, drag=drag)
                                       for chi in (.6, 1.2) for drag in (0., .05)]
        print('aperture transits', json.dumps(result['aperture_transits']), flush=True)
    target = Path(__file__).with_name(f'temperature_aperture_{args.n}_{args.dt:g}_results.json')
    target.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print('Saved', target, flush=True)
