"""Summarize completed runs and independent physical/numerical controls."""
import json
from pathlib import Path
import numpy as np
from temperature_aperture import aperture_transit

ROOT = Path(__file__).parent


def read(name):
    return json.loads((ROOT/name).read_text(encoding='utf-8'))


coarse = read('temperature_aperture_96_0.02_results.json')
fine = read('temperature_aperture_192_0.01_results.json')
time = read('temperature_aperture_192_0.005_results.json')
assert [r['name'] for r in coarse['cases']] == [r['name'] for r in fine['cases']] == [r['name'] for r in time['cases']]
by_name = {r['name']: r for r in fine['cases']}
q0, r, d, duration = .15, .05, .03, fine['duration']
exact_decay = q0*np.exp(-r*duration)/(1+(d/r)*q0*(1-np.exp(-r*duration)))
for name in ('no_magnet', 'constant_susceptibility'):
    assert abs(by_name[name]['final_flow']-exact_decay) < 1e-10
    assert abs(by_name[name]['magnetic_work']) < 1e-10
    assert abs(by_name[name]['drag_heat']-(q0*q0-exact_decay**2)/2) < 1e-10

comparisons = []
for c, f, t in zip(coarse['cases'], fine['cases'], time['cases']):
    comparisons.append(dict(name=f['name'], coarse_late_flow=c['late_mean_flow'],
        fine_late_flow=f['late_mean_flow'], spatial_relative_change=(f['late_mean_flow']-c['late_mean_flow'])/max(abs(f['late_mean_flow']),1e-12),
        time_step_final_flow_change=t['final_flow']-f['final_flow']))
flow_time_error = max(abs(z['time_step_final_flow_change']) for z in comparisons)
assert flow_time_error < 1e-6
case_no = [r['name'] for r in fine['cases']].index('thermal_sources_off_at_120')
tail = np.array([row['flow'][case_no] for row in fine['history'] if row['time'] > 270])
extra = aperture_transit(chi=1.2, drag=.05, speed=1.)
refined_transit = aperture_transit(chi=1.2, drag=0., dt=.001)
assert extra['escaped_to_z3'] and extra['exit_speed'] > 0
coarse_transit = next(r for r in coarse['aperture_transits'] if r['chi']==1.2 and r['drag']==0.)
assert abs(refined_transit['exit_time']-coarse_transit['exit_time']) < 1e-8
checks = dict(
    max_energy_error=max(r['max_energy_error'] for run in (coarse,fine,time) for r in run['cases']),
    max_mechanical_error=max(r['max_mechanical_error'] for run in (coarse,fine,time) for r in run['cases']),
    min_total_entropy_change=min(r['minimum_total_entropy_change'] for run in (coarse,fine,time) for r in run['cases']),
    max_cfl=max(r['max_cfl'] for run in (coarse,fine,time) for r in run['cases']),
    maximum_time_step_final_flow_change=flow_time_error,
    analytic_no_drive_final_flow=float(exact_decay),
    sources_off_late_rms_flow=float(np.sqrt(np.mean(tail**2))),
    finite_speed_with_drag_transit=extra,
    refined_lossless_transit=refined_transit,
    comparisons=comparisons)
(ROOT/'temperature_aperture_checks.json').write_text(json.dumps(checks,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in checks.items() if k != 'comparisons'},indent=2))
print('| Case | Final flow, 96 cells | Final flow, 192 cells | Hot heat, 192 cells |')
print('|---|---:|---:|---:|')
for c, f in zip(coarse['cases'],fine['cases']):
    print(f"| {f['name']} | {c['final_flow']:.7f} | {f['final_flow']:.7f} | {f['hot_bath_heat']:.5f} |")
