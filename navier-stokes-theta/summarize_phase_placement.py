"""Build the comparison block only after the complete accepted runs exist."""
import json
from pathlib import Path


def main():
    base=Path(__file__).parent
    coarse=json.loads((base/'ring_placement_24_0.02_results.json').read_text())
    fine=json.loads((base/'ring_placement_32_0.01_results.json').read_text())
    temporal=json.loads((base/'ring_placement_32_0.02_results.json').read_text())
    expected={('simultaneous8',2026),('fixed',2026),('regular8',2026),('golden',2026),
              ('sqrt2',2026),('rational55_144',2026),('random',2026),('random',2027),('random',2028)}
    assert {(v['kind'],v['seed']) for v in coarse}==expected
    assert {(v['kind'],v['seed']) for v in fine}==expected
    c={(v['kind'],v['seed']):v for v in coarse};f={(v['kind'],v['seed']):v for v in fine}
    names={'simultaneous8':'Eight simultaneous drives','fixed':'One fixed drive','regular8':'45-degree cyclic steps',
           'golden':'Golden-angle steps','sqrt2':'sqrt(2) steps','rational55_144':'Rational 137.5-degree steps','random':'Random'}
    lines=['| Schedule | Upward crossing volume, 24 cubed | Upward crossing volume, 32 cubed | Final energy, 32 cubed | Effective energy volume fraction, 32 cubed |',
           '|---|---:|---:|---:|---:|']
    for key in c:
        a,b=c[key],f[key];last=b['rows'][-1]
        label=names[key[0]]+(f' seed {key[1]}' if key[0]=='random' else '')
        lines.append(f"| {label} | {a['cumulative_upward_crossing_volume']:.6f} | {b['cumulative_upward_crossing_volume']:.6f} | {last['energy']:.6f} | {last['effective_energy_volume_fraction']:.6f} |")
    golden=f['golden',2026];rational=f['rational55_144',2026];regular=f['regular8',2026]
    close=100*abs(golden['cumulative_upward_crossing_volume']/rational['cumulative_upward_crossing_volume']-1)
    improvement=100*(golden['cumulative_upward_crossing_volume']/regular['cumulative_upward_crossing_volume']-1)
    time_deltas={v['kind']:100*abs(v['cumulative_upward_crossing_volume']/f[v['kind'],v['seed']]['cumulative_upward_crossing_volume']-1) for v in temporal}
    grid_deltas={k[0]+str(k[1]):100*abs(c[k]['cumulative_upward_crossing_volume']/f[k]['cumulative_upward_crossing_volume']-1) for k in f}
    max_error=max(abs(v['budget_error']) for v in coarse+fine+temporal)
    max_cfl=max(v['max_cfl'] for v in coarse+fine+temporal)
    peak_speed=max(v['peak_speed'] for v in fine)
    peak_omega=max(v['sampled_peak_vorticity'] for v in fine)
    for v in coarse+fine+temporal:assert abs(v['input']-.156)<1e-12
    lines.extend(['',f'At 32 cubed, golden-angle scheduling gives {improvement:.2f}% more upward crossing volume than the 45-degree cyclic schedule in this run. The nearby rational schedule differs from the golden result by only {close:.6f}%. This is evidence for the effect of spatial scheduling, not for a requirement of mathematical irrationality.',
                  '',f'The largest crossing-volume change between the grids is {max(grid_deltas.values()):.2f}%. Rankings of close alternatives must therefore be treated cautiously. These are two grid sizes, not an established asymptotic convergence study.',
                  '',f'Accepted paired time-step checks at 32 cubed change crossing volume by at most {max(time_deltas.values()):.4f}%. The 45-degree schedule at dt = 0.02 exceeded the chosen CFL limit (0.520853 versus 0.5), so that run was rejected and is not included in the accepted comparisons. All nine schedules were completed at dt = 0.01.',
                  '',f'Across accepted runs the maximum absolute energy residual is {max_error:.3g}, and maximum CFL is {max_cfl:.4f}. At 32 cubed, the largest measured speed is {peak_speed:.5f} and sampled vorticity magnitude is {peak_omega:.5f}, both finite. These finite-grid peaks are not proofs about continuum regularity.',
                  '', 'Data: [24 cubed](ring_placement_24_0.02_results.json), [32 cubed](ring_placement_32_0.01_results.json), [accepted coarser-time comparisons](ring_placement_32_0.02_results.json).'])
    report=base/'PHASE_PLACEMENT_MAGNETIC_RESULTS.md';text=report.read_text()
    block='<!-- PLACEMENT_RESULTS_START -->\n'+'\n'.join(lines)+'\n<!-- PLACEMENT_RESULTS_END -->'
    if '<!-- PLACEMENT_RESULTS -->' in text:text=text.replace('<!-- PLACEMENT_RESULTS -->',block)
    else:
        start=text.index('<!-- PLACEMENT_RESULTS_START -->');end=text.index('<!-- PLACEMENT_RESULTS_END -->')+len('<!-- PLACEMENT_RESULTS_END -->')
        text=text[:start]+block+text[end:]
    report.write_text(text)
    diagnostics=dict(golden_vs_regular_percent=improvement,golden_vs_rational_percent=close,
                     grid_changes_percent=grid_deltas,time_changes_percent=time_deltas,
                     max_energy_error=max_error,max_cfl=max_cfl,peak_speed_32=peak_speed,
                     sampled_peak_vorticity_32=peak_omega)
    (base/'phase_placement_checks.json').write_text(json.dumps(diagnostics,indent=2)+'\n')
    print('\n'.join(lines));print(json.dumps(diagnostics,indent=2))


if __name__=='__main__':main()
