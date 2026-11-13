"""Audit numerical budgets and comparable cohorts; no singularity extrapolation."""
import json
from pathlib import Path
import numpy as np

root = Path(__file__).parent
runs = []
for path in sorted(root.glob('sheath_chain_*_results.json')):
    runs += json.loads(path.read_text())
assert runs
summary = []
for r in runs:
    labels = r['labels']
    counts = [g['count'] for g in labels['gates']]
    total = labels['matched_gate_pairs'][-1]
    row = dict(n=r['n'], dt=r['dt'], mode=r['mode'], inner_counts=counts,
        outer_counts=[g['count'] for g in r['outer_labels']['gates']],
        width_ratio=total.get('width_ratio'), mean_radius_in=total.get('mean_radius_in'),
        mean_radius_out=total.get('mean_radius_out'), radial_sd_in=total.get('radial_sd_in'),
        radial_sd_out=total.get('radial_sd_out'),
        mean_crossing_speed_in=total.get('mean_crossing_speed_in'),
        mean_crossing_speed_out=total.get('mean_crossing_speed_out'),
        mean_crossing_uz_in=total.get('mean_crossing_uz_in'),
        mean_crossing_uz_out=total.get('mean_crossing_uz_out'),
        mean_transit_time=total.get('mean_transit_time'),
        peak_speed=r['peak_speed'], sampled_peak_vorticity=r['sampled_peak_vorticity'],
        input_energy=r['input_energy'], final_kinetic_energy=r['rows'][-1]['energy'],
        dissipation=r['dissipated_energy'], max_energy_error=r['max_energy_error'],
        max_cfl=r['max_cfl'], inner_boundary_fraction=labels['fraction_any_boundary'],
        outer_boundary_fraction=r['outer_labels']['fraction_any_boundary'])
    late = [a for a in r['rows'] if a['t'] >= 4-1e-10]
    row['late_planes'] = [dict(z=z, **{region: {key: float(np.mean([
        a['planes'][j][region][key] for a in late])) for key in ('mean_axial','mean_radial','mean_swirl')}
        for region in ('inner','outer')}) for j,z in enumerate((3.,3.6,4.2))]
    row['late_simultaneous_all_labels'] = {str(a['t']): a['simultaneous_inner']['all_valid']
        for a in r['rows'] if any(abs(a['t']-t)<1e-8 for t in (3.,4.,5.,6.))}
    row['max_divergence'] = max(a['divergence_max'] for a in r['rows'])
    row['max_net_plane_flux'] = max(abs(p['net_flux']) for a in r['rows'] for p in a['planes'])
    assert abs(r['input_energy']-.236) < 1e-12
    assert row['max_divergence'] < 1e-10 and row['max_net_plane_flux'] < 1e-10
    assert row['max_energy_error'] < 2e-6 and row['max_cfl'] < .5
    if r['mode'] == 'bare' and r['n'] in (24,32) and r['dt'] == .01:
        old = next(a for a in json.loads((root/f'vortex_chain_focus_{r["n"]}_0.01_results.json').read_text())
                   if a['mode']=='aligned')
        row['baseline_reproduction_speed_error'] = abs(old['peak_speed']-r['peak_speed'])
        row['baseline_reproduction_width_error'] = abs(old['labels']['matched_gate_pairs'][-1]['width_ratio']-row['width_ratio'])
        assert row['baseline_reproduction_speed_error'] < 1e-12
        assert row['baseline_reproduction_width_error'] < 1e-12
    # Same full cohort avoids the survivor-selection issue in older single-stage tests.
    row['all_inner_labels_reach_all_gates'] = counts == [144,144,144]
    summary.append(row)
out = dict(runs=summary,
    max_energy_error=max(r['max_energy_error'] for r in summary),
    max_cfl=max(r['max_cfl'] for r in summary),
    max_divergence=max(r['max_divergence'] for r in summary),
    max_net_plane_flux=max(r['max_net_plane_flux'] for r in summary))
(root/'sheath_chain_checks.json').write_text(json.dumps(out, indent=2)+'\n', encoding='utf-8')
print('n dt case | inner exit, outer exit | width ratio | mean r in -> out | peak speed')
for r in summary:
    print(r['n'],r['dt'],r['mode'], '|', r['inner_counts'][-1],r['outer_counts'][-1], '|',
          f"{r['width_ratio']:.6f}", '|', f"{r['mean_radius_in']:.6f} -> {r['mean_radius_out']:.6f}", '|',
          f"{r['peak_speed']:.6f}")
print('Maximum energy error:',out['max_energy_error'],'CFL:',out['max_cfl'])
