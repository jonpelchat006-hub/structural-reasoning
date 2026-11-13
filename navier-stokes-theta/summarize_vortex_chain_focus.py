"""Numerical checks and matched-label comparisons for the staged flow test."""
import json
from pathlib import Path
import numpy as np
from vortex_chain_focus import GateLabels,L

root=Path(__file__).parent


def tracker_check():
    n=32
    x,y,z=np.meshgrid(*(np.arange(n)*L/n for _ in range(3)),indexing='ij')
    a=.2
    velocity=np.array([-a*(x-np.pi),-a*(y-np.pi),2*a*(z-1.6)+1])
    labels=GateLabels()
    dt=.001
    for i in range(2000):
        labels.step(velocity,dt,(i+1)*dt)
    expected=np.log1p(2*a*(labels.gates-1.6))/(2*a)
    time_error=float(np.max(abs(labels.cross_time-expected[:,None])))
    ratios=[float(np.exp(-a*(expected[b]-expected[a0]))) for a0,b in ((0,1),(1,2),(0,2))]
    actual=[r['width_ratio'] for r in labels.report()['matched_gate_pairs']]
    width_error=float(np.max(abs(np.array(actual)-ratios)))
    assert time_error<1e-6 and width_error<1e-7
    return dict(exact_gate_times=expected.tolist(),maximum_gate_time_error=time_error,
                expected_width_ratios=ratios,maximum_width_ratio_error=width_error)


coarse=json.loads((root/'vortex_chain_focus_24_0.01_results.json').read_text())
fine=json.loads((root/'vortex_chain_focus_32_0.01_results.json').read_text())
assert [r['mode'] for r in coarse]==[r['mode'] for r in fine]==['single','aligned','reversed']
for r in coarse+fine:
    assert abs(r['input_energy']-.236)<1e-12
    assert r['max_energy_error']<2e-6 and r['max_cfl']<.5
checks=dict(tracker=tracker_check(),total_energy_each_run=.236,
    maximum_energy_error=max(r['max_energy_error'] for r in coarse+fine),
    maximum_cfl=max(r['max_cfl'] for r in coarse+fine),
    maximum_divergence=max(x['divergence_max'] for r in coarse+fine for x in r['rows']),
    maximum_net_flux=max(abs(p['net_flux']) for r in coarse+fine for x in r['rows'] for p in x['planes']),
    grid_comparison=[])
for c,f in zip(coarse,fine):
    checks['grid_comparison'].append(dict(mode=f['mode'],coarse_peak_speed=c['peak_speed'],fine_peak_speed=f['peak_speed'],
        relative_peak_speed_difference=(f['peak_speed']-c['peak_speed'])/f['peak_speed'],
        coarse_gate_counts=[x['count'] for x in c['labels']['gates']],
        fine_gate_counts=[x['count'] for x in f['labels']['gates']],
        coarse_width_ratios=[x.get('width_ratio') for x in c['labels']['matched_gate_pairs']],
        fine_width_ratios=[x.get('width_ratio') for x in f['labels']['matched_gate_pairs']]))
(root/'vortex_chain_focus_checks.json').write_text(json.dumps(checks,indent=2)+'\n',encoding='utf-8')
print(json.dumps(checks,indent=2))
for r in fine:
    print(r['mode'],json.dumps(r['labels']['matched_gate_pairs']))
