"""Point-parcel central-gravity check, separate from the 3D fluid experiment.

No atmosphere, pressure, viscosity, sheath, propulsion, or finite planet surface.
R0=GM=1. Initial velocity is tangential; time unit is sqrt(R0^3/GM).
"""
import json
from pathlib import Path
import numpy as np
from scipy.integrate import solve_ivp


def run(speed_ratio, gravity=True):
    mu = 1. if gravity else 0.
    def rhs(t, state):
        pos, vel = state[:2], state[2:]
        return np.r_[vel, -mu*pos/np.linalg.norm(pos)**3]
    times = np.linspace(0, 2*np.pi, 601)
    solution = solve_ivp(rhs, (0, times[-1]), [1., 0., 0., speed_ratio],
                         t_eval=times, rtol=1e-11, atol=1e-13, max_step=.01)
    assert solution.success
    pos, vel = solution.y[:2].T, solution.y[2:].T
    radius = np.linalg.norm(pos, axis=1)
    energy = np.sum(vel*vel, axis=1)/2-mu/radius
    angular_momentum = pos[:, 0]*vel[:, 1]-pos[:, 1]*vel[:, 0]
    energy_error = float(np.max(abs(energy-energy[0])))
    momentum_error = float(np.max(abs(angular_momentum-angular_momentum[0])))
    assert energy_error < 2e-9 and momentum_error < 2e-9
    if gravity and speed_ratio == 1:
        assert np.max(abs(radius-1)) < 1e-9
        assert np.linalg.norm(pos[-1]-pos[0]) < 1e-9
    if not gravity:
        assert np.max(abs(pos-np.column_stack((np.ones_like(times), speed_ratio*times)))) < 1e-10
    return dict(speed_ratio=speed_ratio, gravity=gravity, max_energy_error=energy_error,
        max_angular_momentum_error=momentum_error, min_sampled_radius=float(radius.min()),
        max_sampled_radius=float(radius.max()), final_radius=float(radius[-1]),
        specific_energy=float(energy[0]), eccentricity=abs(speed_ratio**2-1) if gravity else None,
        times=times.tolist(), positions=pos.tolist(), velocities=vel.tolist())


if __name__ == '__main__':
    mu, planet_radius, altitude = 3.986e14, 6.371e6, 4.e5  # Rounded Earth example, SI.
    orbit_radius = planet_radius+altitude
    example = dict(GM_m3_s2=mu, planet_radius_m=planet_radius, altitude_m=altitude,
        circular_speed_m_s=float(np.sqrt(mu/orbit_radius)),
        local_gravity_m_s2=mu/orbit_radius**2,
        period_s=float(2*np.pi*np.sqrt(orbit_radius**3/mu)),
        guide_acceleration_for_twice_circular_speed_m_s2=3*mu/orbit_radius**2)
    runs = [run(1., False)]+[run(a) for a in (.8, 1., 1.2, 1.5)]
    Path(__file__).with_name('planet_orbit_check_results.json').write_text(
        json.dumps(dict(earth_example=example, runs=runs), indent=2)+'\n', encoding='utf-8')
    print(json.dumps(dict(earth_example=example, runs=[{k:v for k,v in r.items()
        if k not in ('times', 'positions', 'velocities')} for r in runs]), indent=2))
