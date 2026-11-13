"""Equal-total-work test of an outer driven layer around two annular stages.

Dimensionless periodic 3D incompressible Navier-Stokes. No planetary gravity,
solid apertures, heat, magnets, interfaces or independently injected fluid.
The sheath is a forcing shape; whether a surrounding coflow forms is measured.
"""
import argparse
import json
from pathlib import Path
import numpy as np
from helical_annulus import setup, L
from vortex3d import fft, real
from vortex_chain_focus import direction_for, GateLabels
from ring_power import kick
from stacked_layers import plane

CASES = {'bare': (0., 1), 'co_weak': (.2, 1), 'co_strong': (.5, 1),
         'counter_weak': (.2, -1), 'axial_weak': (.2, 0)}


def make_direction(f, base, coords, mode):
    inner, layers = direction_for(f, base, 'aligned')
    x, y, z = coords
    dx, dy = x-np.pi, y-np.pi
    r2 = dx*dx+dy*dy
    # A broad, smooth outer annulus. The axial envelope is exactly periodic.
    radius, width = 1.8, .35
    band = np.exp(-.5*((r2-radius**2)/(2*radius*width))**2)
    band *= np.exp(.8*(np.cos(z-3.1)-1))
    axial = f.project(fft(np.array([0*band, 0*band, band])))
    spin = f.project(fft(np.array([-dy*band/radius, dx*band/radius, 0*band])))
    # Zero mean is necessary in this periodic closed recirculation experiment.
    axial[:, 0, 0, 0] = spin[:, 0, 0, 0] = 0
    axial /= np.sqrt(2*f.energy(axial))
    overlap = float(np.mean(np.sum(real(axial)*real(spin), axis=0)))
    spin -= overlap*axial
    spin /= np.sqrt(2*f.energy(spin))
    eta, sign = CASES[mode]
    sheath = axial if sign == 0 else np.sqrt(.75)*axial+sign*np.sqrt(.25)*spin
    shape = (1-eta)*inner+eta*sheath
    shape /= np.sqrt(2*f.energy(shape))
    assert abs(2*f.energy(shape)-1) < 1e-12
    return shape, dict(layers=layers, sheath_radius=radius, sheath_width=width,
                      blend_coefficient=eta, sheath_spin_sign=sign,
                      axial_spin_overlap=overlap,
                      inner_sheath_overlap=float(np.mean(np.sum(real(inner)*real(sheath), axis=0))))


def simultaneous(labels):
    valid = ~labels.boundary
    r = np.linalg.norm(labels.p[:, :2]-np.pi, axis=1)
    inside = valid & (labels.p[:, 2] >= 3.) & (labels.p[:, 2] <= 4.2)
    report = dict(valid_count=int(valid.sum()), upper_corridor_count=int(inside.sum()))
    for name, mask in [('all_valid', valid), ('upper_corridor', inside)]:
        if mask.any():
            report[name] = dict(count=int(mask.sum()), mean_radius=float(r[mask].mean()),
                radial_sd=float(r[mask].std()), radial_q10=float(np.quantile(r[mask], .1)),
                radial_q90=float(np.quantile(r[mask], .9)),
                mean_z=float(labels.p[mask, 2].mean()), axial_sd=float(labels.p[mask, 2].std()))
    return report


def run(n, mode, dt=.01, duration=6.):
    f, base, coords, rr, cs, sn, _ = setup(n, .25, dt=dt)
    direction, geometry = make_direction(f, base, coords, mode)
    radial = rr[:, :, 0]
    masks = {'inner': (radial>.85)&(radial<1.35),
             'outer': (radial>1.45)&(radial<2.1)}
    labels = GateLabels()
    # An outer cohort diagnoses transport in the nominal sheath. These tags
    # have no separate material law or resistance to interpenetration/mixing.
    outer = GateLabels()
    angles = np.tile(np.arange(48)*L/48, 3)
    radius = np.repeat([1.55, 1.8, 2.05], 48)
    outer.initial[:, :2] = np.column_stack((np.pi+radius*np.cos(angles), np.pi+radius*np.sin(angles)))
    outer.p = outer.initial.copy()
    rows, paths = [], []
    work = loss = error = cfl = peak = 0.
    profile_accumulator = np.zeros((3, 3, 12))
    profile_samples = 0
    for i in range(round(duration/dt)):
        t0, t = i*dt, (i+1)*dt
        amount = .04*min((t0+dt/2)/.2, 1)*dt
        kick(f, direction, amount/2)
        before = f.u.copy()
        _, dissipated = f.step(False)
        loss += dissipated
        midpoint = real((before+f.u)/2)
        kick(f, direction, amount/2)
        work += amount
        if t0 >= 1-1e-10:
            labels.step(midpoint, dt, t)
            outer.step(midpoint, dt, t)
        u = real(f.u)
        cfl = max(cfl, float(np.max(np.sum(abs(u), axis=0))*dt*n/L))
        peak = max(peak, float(np.linalg.norm(u, axis=0).max()))
        error = max(error, abs(f.energy(f.u)-work+loss))
        assert cfl < .5
        if (i+1) % round(.1/dt) == 0:
            ur, ut = u[0]*cs+u[1]*sn, -u[0]*sn+u[1]*cs
            row = f.measure(t)
            row.update(input_energy=work, dissipation=loss, planes=[],
                       simultaneous_inner=simultaneous(labels))
            for j, height in enumerate(labels.gates):
                vz, vr, vt = (plane(a, height) for a in (u[2], ur, ut))
                item = dict(z=float(height), net_flux=float(vz.mean()*L*L))
                for name, mask in masks.items():
                    item[name] = dict(mean_axial=float(vz[mask].mean()),
                        mean_radial=float(vr[mask].mean()), mean_swirl=float(vt[mask].mean()))
                row['planes'].append(item)
                if t >= 4-1e-10:
                    for k in range(12):
                        mask = (radial>=k*.2)&(radial<(k+1)*.2)
                        profile_accumulator[j, :, k] += [float(v[mask].mean()) for v in (vz, vr, vt)]
            if t >= 4-1e-10:
                profile_samples += 1
            rows.append(row)
            if t >= 1:
                paths.append(dict(t=t, inner=labels.p[::12].tolist(), outer=outer.p[::12].tolist()))
    assert error < 2e-6
    assert max(abs(p['net_flux']) for r in rows for p in r['planes']) < 1e-10
    result = dict(n=n, mode=mode, dt=dt, duration=duration, geometry=geometry,
        input_energy=work, dissipated_energy=loss, max_energy_error=error,
        max_cfl=cfl, peak_speed=peak,
        sampled_peak_vorticity=max(r['max_vorticity'] for r in rows),
        rows=rows, labels=labels.report(), outer_labels=outer.report(), sample_paths=paths,
        late_profiles=dict(times=[4., duration], radial_bin_centers=(.1+.2*np.arange(12)).tolist(),
                           components=['axial', 'radial', 'swirl'], gates=labels.gates.tolist(),
                           values=(profile_accumulator/profile_samples).tolist()))
    print(n, mode, 'peak', round(peak, 5), 'inner gates', [g['count'] for g in result['labels']['gates']],
          'outer gates', [g['count'] for g in result['outer_labels']['gates']],
          'width ratio', result['labels']['matched_gate_pairs'][-1].get('width_ratio'), flush=True)
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--n', type=int, default=24)
    p.add_argument('--dt', type=float, default=.01)
    p.add_argument('--modes', nargs='+', choices=list(CASES), default=list(CASES))
    p.add_argument('--append', action='store_true')
    args = p.parse_args()
    out = Path(__file__).with_name(f'sheath_chain_{args.n}_{args.dt:g}_results.json')
    results = json.loads(out.read_text()) if args.append and out.exists() else []
    for mode in args.modes:
        if any(r['mode']==mode for r in results):
            continue
        results.append(run(args.n, mode, args.dt))
        out.write_text(json.dumps(results, indent=2)+'\n', encoding='utf-8')
