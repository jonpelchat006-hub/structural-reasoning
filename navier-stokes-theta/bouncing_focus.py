"""Dimensionless collisionless controls, NOT a liquid or phase-change solver.

Fixed orthogonal planes x=0,y=0,z=0; marked void edge x=y=0.
Exact specular paths use absolute values of unfolded straight trajectories.
Each marker has mass 1/N. No interactions, drag, pressure, or theta law.
"""
import json
from pathlib import Path
import numpy as np


def run():
    grid = np.linspace(0.2, 1.0, 21)
    xx, yy = np.meshgrid(grid, grid)
    q = np.column_stack((xx.ravel(), yy.ravel(), np.ones(xx.size)))
    outputs = {}
    for name in ('parallel', 'converging', 'converging_with_pulse'):
        v = np.column_stack((np.zeros(len(q)), np.zeros(len(q)), np.ones(len(q))))
        if name != 'parallel':
            v[:, :2] = -q[:, :2]  # Deliberately prepared to meet the edge at t=1.
        initial_energy = float(np.mean(np.sum(v*v, axis=1))/2)
        start_time = 0.0
        supplied = 0.0
        if name == 'converging_with_pulse':
            start_time = 0.9
            q_start = np.abs(q + start_time*v)
            mask = np.linalg.norm(q_start[:, :2], axis=1) < 0.1
            before = np.sum(v*v, axis=1)/2
            v[mask, 2] = np.sqrt(v[mask, 2]**2 + 2*2.0)
            supplied = float(np.mean(np.sum(v*v, axis=1)/2-before))
        else:
            q_start = q.copy()
        records = []
        for t in (0.9, 1.0, 1.1, 2.0):
            p = np.abs(q_start + (t-start_time)*v)
            records.append({'time':t, 'rms_distance_to_edge':float(np.sqrt(np.mean(np.sum(p[:,:2]**2,axis=1)))),
                            'fraction_within_0.05':float(np.mean(np.linalg.norm(p[:,:2],axis=1)<0.05))})
        energy = float(np.mean(np.sum(v*v, axis=1))/2)
        assert abs(energy-initial_energy-supplied) < 1e-12
        outputs[name] = {'initial_energy':initial_energy, 'final_energy':energy,
                         'supplied_energy':supplied, 'max_speed':float(np.max(np.linalg.norm(v,axis=1))),
                         'samples':records}
    path = Path(__file__).with_name('bouncing_focus_results.json')
    path.write_text(json.dumps(outputs,indent=2)+'\n')
    print(json.dumps(outputs,indent=2))


if __name__ == '__main__':
    run()
