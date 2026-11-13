"""Audit matched-work helical runs and verify the passive-turn tracker."""
import json
from pathlib import Path
import numpy as np
from helical_annulus import Labels

ROOT=Path(__file__).parent


def read(name):
    return json.loads((ROOT/name).read_text(encoding='utf-8'))


def check_tracker():
    n=32
    x,y,z=np.meshgrid(*(np.arange(n)*2*np.pi/n for _ in range(3)),indexing='ij')
    omega,up,dt,duration=1.2,.2,.001,.5
    velocity=np.array([-omega*(y-np.pi),omega*(x-np.pi),np.full_like(x,up)])
    labels=Labels()
    for _ in range(round(duration/dt)):
        labels.step(velocity,dt)
    initial=labels.initial-np.pi
    angle=omega*duration
    exact=labels.initial.copy()
    exact[:,0]=np.pi+np.cos(angle)*initial[:,0]-np.sin(angle)*initial[:,1]
    exact[:,1]=np.pi+np.sin(angle)*initial[:,0]+np.cos(angle)*initial[:,1]
    exact[:,2]+=up*duration
    position_error=float(abs(labels.p-exact).max())
    turn_error=float(abs(labels.turns-angle/(2*np.pi)).max())
    assert position_error<5e-7 and turn_error<1e-6
    assert not labels.boundary.any()
    return dict(position_error=position_error,turn_error=turn_error)


coarse=read('helical_annulus_24_0.01_1_4_4_results.json')
fine=read('helical_annulus_32_0.01_1_4_4_results.json')
refined=read('helical_annulus_32_0.005_1_4_4_results.json')[0]
reverse=read('helical_annulus_24_0.01_-1_4_4_results.json')[0]
fractions=[0,.25,.75,.95,1]
assert [r['swirl_fraction'] for r in coarse]==fractions
assert [r['swirl_fraction'] for r in fine]==fractions
assert all(abs(r['input_energy']-.156)<1e-12 for r in coarse+fine+[refined,reverse])
matches=[]
for c,f in zip(coarse,fine):
    matches.append(dict(swirl_fraction=f['swirl_fraction'],peak_speed=c['peak_speed'],fine_peak_speed=f['peak_speed'],
        peak_speed_relative_grid_change=(f['peak_speed']-c['peak_speed'])/f['peak_speed'],
        peak_vorticity_relative_grid_change=(f['sampled_peak_vorticity']-c['sampled_peak_vorticity'])/f['sampled_peak_vorticity'],
        coarse_final_core=c['rows'][-1]['core_mean_axial'],fine_final_core=f['rows'][-1]['core_mean_axial']))
same=fine[2]
timing={key:refined[key]-same[key] for key in ('peak_speed','sampled_peak_vorticity','dissipated_energy')}
assert abs(timing['peak_speed'])<.005
symmetry={key:reverse[key]-coarse[2][key] for key in ('peak_speed','sampled_peak_vorticity','dissipated_energy')}
assert max(abs(v) for v in symmetry.values())<1e-9
assert abs(reverse['cohorts'][1]['median_signed_turns']+coarse[2]['cohorts'][1]['median_signed_turns'])<1e-8
all_runs=coarse+fine+[refined,reverse]
checks=dict(tracker=check_tracker(),time_step_changes=timing,handedness_changes=symmetry,
    max_energy_error=max(r['max_budget_error'] for r in all_runs),
    max_cfl=max(r['max_cfl'] for r in all_runs),
    max_divergence=max(x['divergence_max'] for r in all_runs for x in r['rows']),
    max_net_plane_flux=max(abs(x['net_plane_flux']) for r in all_runs for x in r['rows']),
    grid_comparisons=matches)
(ROOT/'helical_annulus_checks.json').write_text(json.dumps(checks,indent=2)+'\n',encoding='utf-8')
print(json.dumps(checks,indent=2))
print('| Swirl-shape fraction | Peak total speed | Final mean upward-band speed | Final mean outer speed | Peak vorticity | Annulus-label median maximum rise |')
print('|---|---:|---:|---:|---:|---:|')
for r in fine:
    row=r['rows'][-1]
    print(f"| {r['swirl_fraction']:.2f} | {r['peak_speed']:.5f} | {row['rising_band_mean_axial']:.5f} | {row['outer_return_mean_axial']:.5f} | {r['sampled_peak_vorticity']:.5f} | {r['cohorts'][1]['median_max_rise']:.5f} |")
