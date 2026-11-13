# First theta / fluid experiment

2D periodic forced flow on [0, 2pi)^2, spectral vorticity solver, strict 2/3 dealiasing, RK4. These are dimensionless numerical experiments, not tests of 3D finite-time singularity.

Off-shear energy >=10% is a preselected symmetry-breaking marker, not a validated turbulence definition. Thresholds were measured, not inserted into the dynamics. All runs end at t=20.

| Run | Reference Re | Final theta | Final off-shear fraction | 10% marker time | Peak velocity gradient |
|---|---:|---:|---:|---:|---:|
| nu0.1_a0.5 | 2.5 | 1 | 3.967e-08 | None | 4.002 |
| nu0.1_a1.0 | 2.5 | 1 | 2.364e-08 | None | 4.019 |
| nu0.1_a2.0 | 2.5 | 1 | 1.784e-08 | None | 8.016 |
| nu0.03_a0.5 | 8.33 | 1.114 | 0.8434 | 15.3 | 4.099 |
| nu0.03_a1.0 | 8.33 | 1.007 | 0.8513 | 14.5 | 4.116 |
| nu0.03_a2.0 | 8.33 | 0.9974 | 0.8603 | 12.4 | 8.016 |
| nu0.01_a0.5 | 25 | 0.2638 | 0.9161 | 13.3 | 4.481 |
| nu0.01_a1.0 | 25 | 0.908 | 0.59 | 10.5 | 4.896 |
| nu0.01_a2.0 | 25 | 0.9577 | 0.6669 | 6.4 | 8.016 |
| check_n64_dt0.01_seed12 | 25 | 0.9096 | 0.5879 | 10.5 | 4.839 |
| check_n96_dt0.01_seed12 | 25 | 0.9096 | 0.5877 | 10.5 | 4.858 |
| check_n48_dt0.005_seed12 | 25 | 0.908 | 0.59 | 10.5 | 4.896 |
| check_n48_dt0.01_seed37 | 25 | 0.903 | 0.5874 | 10.5 | 4.778 |

Exact shear max velocity error: 1.6362466936925557e-12
Max instantaneous energy budget residual: 8.881784197001252e-16

Full sampled time series and threshold crossing times are in results.json. Spatial/time refinement and a second perturbation seed apply to nu=.01, initial amplitude=1 only. No material-specific constitutive laws or real-fluid calibration are included.

Interpretation and numerical uncertainty: see FINDINGS.md.
