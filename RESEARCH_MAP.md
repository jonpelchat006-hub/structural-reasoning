# Research map

*Consolidated November 2026.* This file is the index to the whole program: every thread, what state it is in,
and where each piece lives. The top-level [README](README.md) describes the first three threads in detail;
each folder below has its own README with a file-by-file index.

## How to read this repository

- **Measured** means a script in this repository, or a log saved next to it, produced the number.
- **Design notes** are worked-out ideas that have not been tested, or have been tested only on toy models.
- **Speculative** marks the theoretical framework the rest grew out of. It is included in full and is not
  presented as established science.
- The write-ups were drafted by AI assistants working with the author (Claude for most of them, ChatGPT for
  parts of `qtube/`). Lines quoted as "Jonathan:" are his own words.
- A number can be rechecked only where its script and its data are both here. Where data was left out, the
  README of that folder says so.
- Many ideas came back corrected or refuted, and those results are kept. See "The honest ledger" in the README.

## Threads

| Thread | Where | State |
|---|---|---|
| Protein folding and protein language models | `code/`, `results/`, `figures/`, `theory/folding/` | Measured; reruns from this repository |
| ARC-AGI-1 model-free solver | [`arc-agi-1/`](arc-agi-1/), `theory/framework/` | Measured: 66/400 on public training. Source included, task files not |
| Cognitive architecture ("baby brain") | [`agi/`](agi/) | 55 self-contained experiments, each with its figure |
| AI-image detector | [`detector/`](detector/) | Measured on a matched benchmark. Code included; photos and cached model outputs not |
| Critical-line labs | [`critical-line/`](critical-line/) | Fourteen numerical labs and a paper; no proof claims |
| ARC-AGI-3: the planet, PriorAgent, the hybrid, the core card | [`arc-agi-3/`](arc-agi-3/) | Leaderboard runs are recorded in the docs; the hybrid stayed below the unchanged third-party control |
| Alignment as water | [`alignment/`](alignment/), tests in `arc-agi-3/planet/` | Design notes and toy-model tests |
| Mika | [`mika/`](mika/), `arc-agi-3/planet/mika_*.py` | The agent's code and notes; her logs and memory are not included |
| Q-tube (nested quaternions) | [`qtube/`](qtube/) | Early experiments on one public game |
| Navier–Stokes theta | [`navier-stokes-theta/`](navier-stokes-theta/) | Has its own claim ledger (`INDEX.md`): established, suggestive, negative, untested |
| Shovelcat / vesica framework | `theory/framework/` | Speculative; the origin of the rest |
| P vs NP in Lean, and the floor_flow experiments | [pvsnp-lean](https://github.com/jonpelchat006-hub/pvsnp-lean) | A kernel-checked Lean library. Its README states that P vs NP is open and that nothing there claims to resolve it |
| Lean Kernel Challenge entries | [`lean/`](lean/) | Every round of entries to the 2026 challenge and the research behind them. Board scores as of Nov 12 are in its README |
| Erdős incidence geometry | [erdos-incidence-geometry](https://github.com/jonpelchat006-hub/erdos-incidence-geometry) | Separate repository |
| Earlier physics and security scripts | [Shovelcat-Alpha](https://github.com/jonpelchat006-hub/Shovelcat-Alpha), [Shovelcat-Security](https://github.com/jonpelchat006-hub/Shovelcat-Security) | Separate repositories; earlier work |

## What is not here

- **Data:** game recordings, learned state, model weights, result dumps, fetched market data and the
  detector's benchmark photos.
- **Third-party material:** the ARC task files, and the language-model harness the ARC-AGI-3 hybrid builds on.
- **Private material:** API keys, contact details and the detector's web app.
- **Admin and product notes:** the funding list, the competition entry forms and drafts, the product spec
  and the notes on the detector's web site. They are not research write-ups and are not listed below.

## Catalogue of write-ups

One line per write-up, newest first within each group, with its place in this repository.

The 112 write-ups marked † existed only as session notes until November 2026, when they were copied into
this repository by hand. They were retyped, not exported, so a slip in a number or a name is possible. One
private link was removed from one of them, which says so at that spot.

Session notes name the scripts that produced their numbers. Many of those scripts are in this repository,
in the same thread's folder. Others are not: most of them were run in working sessions and were not in the
folders this repository was assembled from, and a few belong to older work that was left out. For those
runs the note is the only record.

### ARC-AGI (ARC_*, ARC3_*)

- ARC3_MIKA_FULL_CORE (2026-10-30): [`arc-agi-3/notes/ARC3_MIKA_FULL_CORE.md`](arc-agi-3/notes/ARC3_MIKA_FULL_CORE.md) †
- ARC3_FAILURE_MAP (2026-10-30): [`arc-agi-3/arc3/hybrid/ARC3_FAILURE_MAP.md`](arc-agi-3/arc3/hybrid/ARC3_FAILURE_MAP.md)
- ARC3_CORE_CARD (2026-10-23): [`arc-agi-3/arc3/paper/ARC3_CORE_CARD.md`](arc-agi-3/arc3/paper/ARC3_CORE_CARD.md)
- ARC3_HYBRID (2026-10-23): [`arc-agi-3/arc3/hybrid/ARC3_HYBRID.md`](arc-agi-3/arc3/hybrid/ARC3_HYBRID.md)
- ARC3_UNIVERSITY (2026-10-22): [`arc-agi-3/notes/ARC3_UNIVERSITY.md`](arc-agi-3/notes/ARC3_UNIVERSITY.md) †
- ARC3_MIKA_EXPLORER (2026-10-21): [`arc-agi-3/notes/ARC3_MIKA_EXPLORER.md`](arc-agi-3/notes/ARC3_MIKA_EXPLORER.md) †
- ARC_SLOT_FILLER (2026-10-21): [`arc-agi-1/notes/ARC_SLOT_FILLER.md`](arc-agi-1/notes/ARC_SLOT_FILLER.md) †
- PROBLEM_ATLAS (2026-10-21): [`arc-agi-3/notes/PROBLEM_ATLAS.md`](arc-agi-3/notes/PROBLEM_ATLAS.md) †
- CORE_POINTS_AND_MISFIT_RINGS (2026-10-20): [`arc-agi-3/notes/CORE_POINTS_AND_MISFIT_RINGS.md`](arc-agi-3/notes/CORE_POINTS_AND_MISFIT_RINGS.md) †
- ARC_DAILY_TORCH_PATH (2026-09-28): [`arc-agi-3/notes/ARC_DAILY_TORCH_PATH.md`](arc-agi-3/notes/ARC_DAILY_TORCH_PATH.md) †
- ARC_DAILY_LIVE_ZERO (2026-09-21): [`arc-agi-3/notes/ARC_DAILY_LIVE_ZERO.md`](arc-agi-3/notes/ARC_DAILY_LIVE_ZERO.md) †
- ARC_DAILY_FENCE_NPZ_BUG (2026-09-07): [`arc-agi-3/notes/ARC_DAILY_FENCE_NPZ_BUG.md`](arc-agi-3/notes/ARC_DAILY_FENCE_NPZ_BUG.md) †
- ARC_SMALL_EYE (2026-09-03): [`arc-agi-3/notes/ARC_SMALL_EYE.md`](arc-agi-3/notes/ARC_SMALL_EYE.md) †
- ARC_WRITER_LOOP (2026-09-03): [`arc-agi-3/notes/ARC_WRITER_LOOP.md`](arc-agi-3/notes/ARC_WRITER_LOOP.md) †
- ARC_PROXY_EXAM (2026-09-03): [`arc-agi-3/notes/ARC_PROXY_EXAM.md`](arc-agi-3/notes/ARC_PROXY_EXAM.md) †
- ARC_ANSWER_BUBBLE (2026-09-03): [`arc-agi-3/notes/ARC_ANSWER_BUBBLE.md`](arc-agi-3/notes/ARC_ANSWER_BUBBLE.md) †
- ARC_ONCALL (2026-09-03): [`arc-agi-3/notes/ARC_ONCALL.md`](arc-agi-3/notes/ARC_ONCALL.md) †
- ARC_CHAIN (2026-09-03): [`arc-agi-3/notes/ARC_CHAIN.md`](arc-agi-3/notes/ARC_CHAIN.md) †
- ARC_CHORD (2026-09-02): [`arc-agi-3/notes/ARC_CHORD.md`](arc-agi-3/notes/ARC_CHORD.md) †
- ARC_SIDE_EYE (2026-09-02): [`arc-agi-3/notes/ARC_SIDE_EYE.md`](arc-agi-3/notes/ARC_SIDE_EYE.md) †
- ARC_TORUS (2026-09-02): [`arc-agi-3/notes/ARC_TORUS.md`](arc-agi-3/notes/ARC_TORUS.md) †
- ARC_LS20_CHAIN (2026-09-02): [`arc-agi-3/notes/ARC_LS20_CHAIN.md`](arc-agi-3/notes/ARC_LS20_CHAIN.md) †
- ARC_LS20_READ (2026-09-02): [`arc-agi-3/notes/ARC_LS20_READ.md`](arc-agi-3/notes/ARC_LS20_READ.md) †
- ARC_UNIVERSITY (2026-09-02): [`arc-agi-3/notes/ARC_UNIVERSITY.md`](arc-agi-3/notes/ARC_UNIVERSITY.md) †
- ARC_CLOSURE_SPECTRUM (2026-09-02): [`arc-agi-3/notes/ARC_CLOSURE_SPECTRUM.md`](arc-agi-3/notes/ARC_CLOSURE_SPECTRUM.md) †
- ARC_COLOR_LADDER (2026-09-02): [`arc-agi-3/notes/ARC_COLOR_LADDER.md`](arc-agi-3/notes/ARC_COLOR_LADDER.md) †
- ARC_LENS (2026-09-01): [`arc-agi-3/notes/ARC_LENS.md`](arc-agi-3/notes/ARC_LENS.md) †
- ARC_FUSION (2026-09-01): [`arc-agi-3/notes/ARC_FUSION.md`](arc-agi-3/notes/ARC_FUSION.md) †
- ARC_MIRROR (2026-09-01): [`arc-agi-3/notes/ARC_MIRROR.md`](arc-agi-3/notes/ARC_MIRROR.md) †
- ARC_PLAYGROUND (2026-09-01): [`arc-agi-3/notes/ARC_PLAYGROUND.md`](arc-agi-3/notes/ARC_PLAYGROUND.md) †
- ARC_ATP (2026-09-01): [`arc-agi-3/notes/ARC_ATP.md`](arc-agi-3/notes/ARC_ATP.md) †
- ARC_MOON (2026-08-31): [`arc-agi-3/notes/ARC_MOON.md`](arc-agi-3/notes/ARC_MOON.md) †
- ARC_TUNNEL_ROTATION (2026-08-31): [`arc-agi-3/notes/ARC_TUNNEL_ROTATION.md`](arc-agi-3/notes/ARC_TUNNEL_ROTATION.md) †
- ARC_TIME_WAKE (2026-08-31): [`arc-agi-3/notes/ARC_TIME_WAKE.md`](arc-agi-3/notes/ARC_TIME_WAKE.md) †
- ARC_ROUND_EYE (2026-08-31): [`arc-agi-3/notes/ARC_ROUND_EYE.md`](arc-agi-3/notes/ARC_ROUND_EYE.md) †
- ARC_LEARNING_AUDIT (2026-08-29): [`arc-agi-3/notes/ARC_LEARNING_AUDIT.md`](arc-agi-3/notes/ARC_LEARNING_AUDIT.md) †
- ARC_OPEN_ENDS (2026-08-29): [`arc-agi-3/notes/ARC_OPEN_ENDS.md`](arc-agi-3/notes/ARC_OPEN_ENDS.md) †
- ARC_SLEEP_ORGANS (2026-08-29): [`arc-agi-3/notes/ARC_SLEEP_ORGANS.md`](arc-agi-3/notes/ARC_SLEEP_ORGANS.md) †
- ARC_PRIME_NECKLACES (2026-08-28): [`arc-agi-3/notes/ARC_PRIME_NECKLACES.md`](arc-agi-3/notes/ARC_PRIME_NECKLACES.md) †
- ARC_MEASUREMENT_1 (2026-08-26): [`arc-agi-3/notes/ARC_MEASUREMENT_1.md`](arc-agi-3/notes/ARC_MEASUREMENT_1.md)
- ARC_PLANET (2026-08-26): [`arc-agi-3/notes/ARC_PLANET.md`](arc-agi-3/notes/ARC_PLANET.md)
- OCEAN_INDEX (2026-08-25): [`arc-agi-3/notes/OCEAN_INDEX.md`](arc-agi-3/notes/OCEAN_INDEX.md)
- ARC3_LIVE_PLAN (2026-08-25): [`arc-agi-3/notes/ARC3_LIVE_PLAN.md`](arc-agi-3/notes/ARC3_LIVE_PLAN.md)
- ARC_GAME_TIME_MAP (2026-08-20): [`arc-agi-3/notes/ARC_GAME_TIME_MAP.md`](arc-agi-3/notes/ARC_GAME_TIME_MAP.md) †
- ARC_SLEEP_LEVELS (2026-08-19): [`arc-agi-3/notes/ARC_SLEEP_LEVELS.md`](arc-agi-3/notes/ARC_SLEEP_LEVELS.md) †
- ARC_VERNIER_CLOCK (2026-08-19): [`arc-agi-3/notes/ARC_VERNIER_CLOCK.md`](arc-agi-3/notes/ARC_VERNIER_CLOCK.md) †
- ARC_VOID_DOMAIN (2026-08-19): [`arc-agi-3/notes/ARC_VOID_DOMAIN.md`](arc-agi-3/notes/ARC_VOID_DOMAIN.md) †
- ARC_MEMORY_CLOCK (2026-08-19): [`arc-agi-3/notes/ARC_MEMORY_CLOCK.md`](arc-agi-3/notes/ARC_MEMORY_CLOCK.md) †
- ARC_PAINT_VOID (2026-08-19): [`arc-agi-1/notes/ARC_PAINT_VOID.md`](arc-agi-1/notes/ARC_PAINT_VOID.md) †
- ARC_TWO_PLANES (2026-08-19): [`arc-agi-3/notes/ARC_TWO_PLANES.md`](arc-agi-3/notes/ARC_TWO_PLANES.md) †
- ARC_OPGEN (2026-08-19): [`arc-agi-1/notes/ARC_OPGEN.md`](arc-agi-1/notes/ARC_OPGEN.md) †
- ARC_HYPOTHESIS_TEST (2026-08-19): [`arc-agi-1/notes/ARC_HYPOTHESIS_TEST.md`](arc-agi-1/notes/ARC_HYPOTHESIS_TEST.md) †
- ARC_VOID_FILL (2026-08-19): [`arc-agi-3/notes/ARC_VOID_FILL.md`](arc-agi-3/notes/ARC_VOID_FILL.md) †
- ARC_OPERATOR_INDUCTION (2026-08-19): [`arc-agi-3/notes/ARC_OPERATOR_INDUCTION.md`](arc-agi-3/notes/ARC_OPERATOR_INDUCTION.md) †
- ARC_RECURSIVE_VOID (2026-08-18): [`arc-agi-3/notes/ARC_RECURSIVE_VOID.md`](arc-agi-3/notes/ARC_RECURSIVE_VOID.md) †
- ARC_PERCEPTION_SURPRISE (2026-08-18): [`arc-agi-3/notes/ARC_PERCEPTION_SURPRISE.md`](arc-agi-3/notes/ARC_PERCEPTION_SURPRISE.md) †
- ARC_GAME_LOOP (2026-08-18): [`arc-agi-3/notes/ARC_GAME_LOOP.md`](arc-agi-3/notes/ARC_GAME_LOOP.md) †
- ARC_PROBE_FIRST (2026-08-18): [`arc-agi-3/notes/ARC_PROBE_FIRST.md`](arc-agi-3/notes/ARC_PROBE_FIRST.md) †
- ARC_STAGED_ARMS (2026-08-18): [`arc-agi-3/notes/ARC_STAGED_ARMS.md`](arc-agi-3/notes/ARC_STAGED_ARMS.md) †
- ARC_INTERACTIVE_PLAY (2026-08-18): [`arc-agi-3/notes/ARC_INTERACTIVE_PLAY.md`](arc-agi-3/notes/ARC_INTERACTIVE_PLAY.md) †
- ARC_DRONES (2026-08-18): [`arc-agi-1/notes/ARC_DRONES.md`](arc-agi-1/notes/ARC_DRONES.md) †
- ARC_SOLVER_V1 (2026-08-18): [`arc-agi-1/notes/ARC_SOLVER_V1.md`](arc-agi-1/notes/ARC_SOLVER_V1.md) †
- ARC_RATCHET (2026-08-18): [`arc-agi-1/notes/ARC_RATCHET.md`](arc-agi-1/notes/ARC_RATCHET.md) †
- ARC_GAP_ANALYSIS (2026-08-18): [`arc-agi-1/notes/ARC_GAP_ANALYSIS.md`](arc-agi-1/notes/ARC_GAP_ANALYSIS.md) †

### Alignment

- ARC_ALIGNMENT_REFUSAL (2026-09-27): [`alignment/ARC_ALIGNMENT_REFUSAL.md`](alignment/ARC_ALIGNMENT_REFUSAL.md) †
- ARC_ALIGNMENT_TESTS (2026-09-26): [`alignment/ARC_ALIGNMENT_TESTS.md`](alignment/ARC_ALIGNMENT_TESTS.md)
- ARC_ALIGNMENT_PHASES (2026-09-22): [`alignment/ARC_ALIGNMENT_PHASES.md`](alignment/ARC_ALIGNMENT_PHASES.md)
- ARC_ALIGNMENT_REVIEW_SEP22 (2026-09-22): [`alignment/ARC_ALIGNMENT_REVIEW_SEP22.md`](alignment/ARC_ALIGNMENT_REVIEW_SEP22.md)
- ARC_ALIGNMENT_WITNESS (2026-09-19): [`alignment/ARC_ALIGNMENT_WITNESS.md`](alignment/ARC_ALIGNMENT_WITNESS.md)
- ARC_ALIGNMENT_GRID (2026-09-19): [`alignment/ARC_ALIGNMENT_GRID.md`](alignment/ARC_ALIGNMENT_GRID.md)
- ARC_ALIGNMENT (2026-09-19): [`alignment/ARC_ALIGNMENT.md`](alignment/ARC_ALIGNMENT.md)

### Mika, the library and the Q-tube

- NESTED_QUATERNION_MODEL (2026-11-01): [`qtube/NESTED_QUATERNION_MODEL.md`](qtube/NESTED_QUATERNION_MODEL.md) †
- MIKA_CORE (2026-10-27): [`mika/notes/MIKA_CORE.md`](mika/notes/MIKA_CORE.md) †
- MIKA_THINK (2026-10-27): [`mika/notes/MIKA_THINK.md`](mika/notes/MIKA_THINK.md) †
- MIKA_PARTS_INVENTORY (2026-10-27): [`mika/notes/MIKA_PARTS_INVENTORY.md`](mika/notes/MIKA_PARTS_INVENTORY.md) †
- MIKA_TREE (2026-10-16): [`mika/notes/MIKA_TREE.md`](mika/notes/MIKA_TREE.md) †
- MARKET_CUBE (2026-10-14): [`mika/notes/MARKET_CUBE.md`](mika/notes/MARKET_CUBE.md) †
- LIVING_LIBRARY (2026-10-13): [`mika/notes/LIVING_LIBRARY.md`](mika/notes/LIVING_LIBRARY.md) †
- OLD_IDEAS_MAP (2026-10-13): [`mika/notes/OLD_IDEAS_MAP.md`](mika/notes/OLD_IDEAS_MAP.md) †
- MIKA_AGENT (2026-10-13): [`mika/notes/MIKA_AGENT.md`](mika/notes/MIKA_AGENT.md) †

### Navier–Stokes theta

- NAVIER_STOKES_THETA_REVIEW (2026-09-17): the two reviews in that folder, [`REVIEW_2026-09-13.md`](navier-stokes-theta/REVIEW_2026-09-13.md) and [`THETA_REVIEW_20260915.md`](navier-stokes-theta/THETA_REVIEW_20260915.md)
- NAVIER_STOKES_THETA_PARAMETERS (2026-09-17): [`navier-stokes-theta/PARAMETER_TABLE.md`](navier-stokes-theta/PARAMETER_TABLE.md)
- NAVIER_STOKES_THETA_CONSOLIDATED (2026-09-17): [`navier-stokes-theta/THETA_CONSOLIDATED.md`](navier-stokes-theta/THETA_CONSOLIDATED.md)

### Lean and P vs NP

- LEAN_REVIEW_NOV12 (2026-11-12): [`lean/notes/LEAN_REVIEW_NOV12.md`](lean/notes/LEAN_REVIEW_NOV12.md) †
- PVSNP_FLOOR_FLOW (2026-10-29): the floor-flow write-up in pvsnp-lean, [`experiments/floor_flow/README.md`](https://github.com/jonpelchat006-hub/pvsnp-lean/blob/main/experiments/floor_flow/README.md), which is the later and longer version
- LEAN_PVSNP (2026-10-28): the README of [pvsnp-lean](https://github.com/jonpelchat006-hub/pvsnp-lean)
- LEAN_PERMANENT_V8T (2026-10-27): [`lean/notes/LEAN_PERMANENT_V8T.md`](lean/notes/LEAN_PERMANENT_V8T.md) †
- LEAN_PARTITION_V6 (2026-10-26): [`lean/notes/LEAN_PARTITION_V6.md`](lean/notes/LEAN_PARTITION_V6.md) †
- LEAN_PERMANENT_V8 (2026-10-25): [`lean/notes/LEAN_PERMANENT_V8.md`](lean/notes/LEAN_PERMANENT_V8.md) †
- LEAN_POLYDISC_V9 (2026-10-21): [`lean/notes/LEAN_POLYDISC_V9.md`](lean/notes/LEAN_POLYDISC_V9.md) †
- LEAN_POLYDISC_PACKED (2026-10-19): [`lean/notes/LEAN_POLYDISC_PACKED.md`](lean/notes/LEAN_POLYDISC_PACKED.md) †
- LEAN_FIB_PLANNER (2026-10-18): [`lean/notes/LEAN_FIB_PLANNER.md`](lean/notes/LEAN_FIB_PLANNER.md) †
- LEAN_KERNEL_CHALLENGE_V4 (2026-10-04): [`lean/notes/LEAN_KERNEL_CHALLENGE_V4.md`](lean/notes/LEAN_KERNEL_CHALLENGE_V4.md) †
- LEAN_KERNEL_CHALLENGE (2026-10-01): [`lean/kernel-challenge/LEAN_KERNEL_CHALLENGE.md`](lean/kernel-challenge/LEAN_KERNEL_CHALLENGE.md)

### Folding, cognitive architecture, detector and critical line (FOLDING_*)

- FOLDING_CRITICAL_LINE (2026-08-25): [`critical-line/FOLDING_CRITICAL_LINE.md`](critical-line/FOLDING_CRITICAL_LINE.md)
- CRITICAL_LINE_PAPER.tex (2026-08-23): [`critical-line/Critical_Line_Paper.tex`](critical-line/Critical_Line_Paper.tex)
- FOLDING_SYNTHESIS (2026-08-18): [`agi/theory/FOLDING_SYNTHESIS.md`](agi/theory/FOLDING_SYNTHESIS.md)
- FOLDING_OUTER_WORKSPACE (2026-08-17): [`agi/theory/FOLDING_OUTER_WORKSPACE.md`](agi/theory/FOLDING_OUTER_WORKSPACE.md)
- FOLDING_REBASING (2026-08-17): [`agi/theory/FOLDING_REBASING.md`](agi/theory/FOLDING_REBASING.md)
- FOLDING_TRUST_STITCH (2026-08-17): [`agi/theory/FOLDING_TRUST_STITCH.md`](agi/theory/FOLDING_TRUST_STITCH.md)
- FOLDING_WHAT_ITS_FOR (2026-08-16): [`agi/theory/FOLDING_WHAT_ITS_FOR.md`](agi/theory/FOLDING_WHAT_ITS_FOR.md)
- FOLDING_MORAL_FLOW (2026-08-15): [`agi/theory/FOLDING_MORAL_FLOW.md`](agi/theory/FOLDING_MORAL_FLOW.md)
- FOLDING_ENCRYPTION (2026-08-15): [`agi/theory/FOLDING_ENCRYPTION.md`](agi/theory/FOLDING_ENCRYPTION.md)
- FOLDING_DISCOVERY (2026-08-14): [`agi/theory/FOLDING_DISCOVERY.md`](agi/theory/FOLDING_DISCOVERY.md) †
- FOLDING_FREQUENCY (2026-08-14): [`agi/theory/FOLDING_FREQUENCY.md`](agi/theory/FOLDING_FREQUENCY.md) †
- FOLDING_SUPERFUEL (2026-08-14): [`agi/theory/FOLDING_SUPERFUEL.md`](agi/theory/FOLDING_SUPERFUEL.md) †
- FOLDING_MOVEMENT (2026-08-13): [`agi/theory/FOLDING_MOVEMENT.md`](agi/theory/FOLDING_MOVEMENT.md)
- FOLDING_GALAXY_BRIDGE (2026-08-12): [`agi/theory/FOLDING_GALAXY_BRIDGE.md`](agi/theory/FOLDING_GALAXY_BRIDGE.md) †
- FOLDING_HANDSHAKE (2026-08-11): [`agi/theory/FOLDING_HANDSHAKE.md`](agi/theory/FOLDING_HANDSHAKE.md) †
- FOLDING_TRAMPOLINE (2026-08-10): [`agi/theory/FOLDING_TRAMPOLINE.md`](agi/theory/FOLDING_TRAMPOLINE.md) †
- FOLDING_COMBINE_MEMBRANE (2026-08-01): [`agi/theory/FOLDING_COMBINE_MEMBRANE.md`](agi/theory/FOLDING_COMBINE_MEMBRANE.md) †
- FOLDING_DIVERGENCE_WEIGHT (2026-07-31): [`detector/theory/FOLDING_DIVERGENCE_WEIGHT.md`](detector/theory/FOLDING_DIVERGENCE_WEIGHT.md) †
- FOLDING_FROZEN_VIDEO_FLOW (2026-07-29): [`detector/theory/FOLDING_FROZEN_VIDEO_FLOW.md`](detector/theory/FOLDING_FROZEN_VIDEO_FLOW.md) †
- FOLDING_VOID_COLLAPSE (2026-07-29): [`detector/theory/FOLDING_VOID_COLLAPSE.md`](detector/theory/FOLDING_VOID_COLLAPSE.md) †
- FOLDING_THE_TRACE_IS_THE_REPORT (2026-07-28): [`detector/theory/FOLDING_THE_TRACE_IS_THE_REPORT.md`](detector/theory/FOLDING_THE_TRACE_IS_THE_REPORT.md) †
- FOLDING_PARTIAL_ATTACHMENT (2026-07-28): [`detector/theory/FOLDING_PARTIAL_ATTACHMENT.md`](detector/theory/FOLDING_PARTIAL_ATTACHMENT.md) †
- FOLDING_WINDOW_COVERAGE (2026-07-28): [`detector/theory/FOLDING_WINDOW_COVERAGE.md`](detector/theory/FOLDING_WINDOW_COVERAGE.md) †
- FOLDING_ARMS_AND_BRACING (2026-07-28): [`detector/theory/FOLDING_ARMS_AND_BRACING.md`](detector/theory/FOLDING_ARMS_AND_BRACING.md) †
- FOLDING_EVIDENCE_NOT_VERDICTS (2026-07-28): [`detector/theory/FOLDING_EVIDENCE_NOT_VERDICTS.md`](detector/theory/FOLDING_EVIDENCE_NOT_VERDICTS.md) †
- FOLDING_CAMERA5_HUMAN_ARM (2026-07-28): [`detector/theory/FOLDING_CAMERA5_HUMAN_ARM.md`](detector/theory/FOLDING_CAMERA5_HUMAN_ARM.md) †
- FOLDING_EFFORT_BUDGET (2026-07-28): [`detector/theory/FOLDING_EFFORT_BUDGET.md`](detector/theory/FOLDING_EFFORT_BUDGET.md) †
- FOLDING_DISCRETE_IMAGINARY_CAMERA (2026-07-28): [`detector/theory/FOLDING_DISCRETE_IMAGINARY_CAMERA.md`](detector/theory/FOLDING_DISCRETE_IMAGINARY_CAMERA.md) †
- FOLDING_BLUE_VOID_AND_PER_LENS (2026-07-28): [`detector/theory/FOLDING_BLUE_VOID_AND_PER_LENS.md`](detector/theory/FOLDING_BLUE_VOID_AND_PER_LENS.md) †
- FOLDING_OPPONENT_COLOUR (2026-07-27): [`detector/theory/FOLDING_OPPONENT_COLOUR.md`](detector/theory/FOLDING_OPPONENT_COLOUR.md) †
- FOLDING_SHADING (2026-07-27): [`detector/theory/FOLDING_SHADING.md`](detector/theory/FOLDING_SHADING.md) †
- FOLDING_ROBUSTNESS (2026-07-27): [`detector/theory/FOLDING_ROBUSTNESS.md`](detector/theory/FOLDING_ROBUSTNESS.md) †
- FOLDING_PER_SENSOR (2026-07-27): [`detector/theory/FOLDING_PER_SENSOR.md`](detector/theory/FOLDING_PER_SENSOR.md) †
- FOLDING_CAMERA3 (2026-07-27): [`detector/theory/FOLDING_CAMERA3.md`](detector/theory/FOLDING_CAMERA3.md) †
- FOLDING_IMAGINARY_CAMERA (2026-07-27): [`detector/theory/FOLDING_IMAGINARY_CAMERA.md`](detector/theory/FOLDING_IMAGINARY_CAMERA.md) †
- FOLDING_STACK_THICKNESS (2026-07-27): [`detector/theory/FOLDING_STACK_THICKNESS.md`](detector/theory/FOLDING_STACK_THICKNESS.md) †
- FOLDING_EDGE_OBSERVERS (2026-07-27): [`detector/theory/FOLDING_EDGE_OBSERVERS.md`](detector/theory/FOLDING_EDGE_OBSERVERS.md) †
- FOLDING_PRNU_LOCALISATION (2026-07-27): [`detector/theory/FOLDING_PRNU_LOCALISATION.md`](detector/theory/FOLDING_PRNU_LOCALISATION.md) †
- FOLDING_PRNU (2026-07-26): [`detector/theory/FOLDING_PRNU.md`](detector/theory/FOLDING_PRNU.md) †
- FOLDING_CLEAN_HISTORY (2026-07-26): [`detector/theory/FOLDING_CLEAN_HISTORY.md`](detector/theory/FOLDING_CLEAN_HISTORY.md) †
- FOLDING_TWO_CHANNEL_LOOP (2026-07-26): [`detector/theory/FOLDING_TWO_CHANNEL_LOOP.md`](detector/theory/FOLDING_TWO_CHANNEL_LOOP.md) †
- FOLDING_RATCHET_AND_ROUTING (2026-07-26): [`detector/theory/FOLDING_RATCHET_AND_ROUTING.md`](detector/theory/FOLDING_RATCHET_AND_ROUTING.md) †
- FOLDING_SEAM_REBUILD_AND_DENSITY (2026-07-26): [`detector/theory/FOLDING_SEAM_REBUILD_AND_DENSITY.md`](detector/theory/FOLDING_SEAM_REBUILD_AND_DENSITY.md) †
- STATE_OF_THE_DETECTOR (2026-07-26): [`detector/theory/STATE_OF_THE_DETECTOR.md`](detector/theory/STATE_OF_THE_DETECTOR.md)
- FOLDING_PHOTO_SET_AUTOPSY (2026-07-26): [`detector/theory/FOLDING_PHOTO_SET_AUTOPSY.md`](detector/theory/FOLDING_PHOTO_SET_AUTOPSY.md) †
- FOLDING_TWO_CONES (2026-07-26): [`detector/theory/FOLDING_TWO_CONES.md`](detector/theory/FOLDING_TWO_CONES.md)
- FOLDING_BALANCE_LAW (2026-07-26): [`detector/theory/FOLDING_BALANCE_LAW.md`](detector/theory/FOLDING_BALANCE_LAW.md)
- FOLDING_WITHIN_IMAGE (2026-07-26): [`detector/theory/FOLDING_WITHIN_IMAGE.md`](detector/theory/FOLDING_WITHIN_IMAGE.md)
- FOLDING_SEAM_TEST (2026-07-26): [`detector/theory/FOLDING_SEAM_TEST.md`](detector/theory/FOLDING_SEAM_TEST.md)
- FOLDING_DEBATE_AND_SEAM_DATA (2026-07-26): [`detector/theory/FOLDING_DEBATE_AND_SEAM_DATA.md`](detector/theory/FOLDING_DEBATE_AND_SEAM_DATA.md)
- FOLDING_OBSERVERS_AS_D (2026-07-26): [`detector/theory/FOLDING_OBSERVERS_AS_D.md`](detector/theory/FOLDING_OBSERVERS_AS_D.md)
- FOLDING_COMMITTEE_TEST (2026-07-26): [`detector/theory/FOLDING_COMMITTEE_TEST.md`](detector/theory/FOLDING_COMMITTEE_TEST.md)
- FOLDING_MATCHED_BENCHMARK (2026-07-25): [`detector/theory/FOLDING_MATCHED_BENCHMARK.md`](detector/theory/FOLDING_MATCHED_BENCHMARK.md)
- FOLDING_ENVIRONMENT_BRIDGE (2026-07-25): [`detector/theory/FOLDING_ENVIRONMENT_BRIDGE.md`](detector/theory/FOLDING_ENVIRONMENT_BRIDGE.md)
- FOLDING_AXIS_INNER_SHELL (2026-07-25): [`detector/theory/FOLDING_AXIS_INNER_SHELL.md`](detector/theory/FOLDING_AXIS_INNER_SHELL.md)
- FOLDING_OBSERVER_FRAME (2026-07-25): [`detector/theory/FOLDING_OBSERVER_FRAME.md`](detector/theory/FOLDING_OBSERVER_FRAME.md)
- FOLDING_AXIS_INDEPENDENCE (2026-07-25): [`detector/theory/FOLDING_AXIS_INDEPENDENCE.md`](detector/theory/FOLDING_AXIS_INDEPENDENCE.md)
- FOLDING_PHYSICS_OBSERVER (2026-07-25): [`detector/theory/FOLDING_PHYSICS_OBSERVER.md`](detector/theory/FOLDING_PHYSICS_OBSERVER.md)
- FOLDING_TWO_SIDED_WINDOW (2026-07-25): [`detector/theory/FOLDING_TWO_SIDED_WINDOW.md`](detector/theory/FOLDING_TWO_SIDED_WINDOW.md)
- FOLDING_RECONSTRUCTION (2026-07-25): [`detector/theory/FOLDING_RECONSTRUCTION.md`](detector/theory/FOLDING_RECONSTRUCTION.md)
- FOLDING_MIXEDNESS_CONFIDENCE (2026-07-25): [`detector/theory/FOLDING_MIXEDNESS_CONFIDENCE.md`](detector/theory/FOLDING_MIXEDNESS_CONFIDENCE.md)
- FOLDING_CONTEXT_ROUTER (2026-07-24): [`detector/theory/FOLDING_CONTEXT_ROUTER.md`](detector/theory/FOLDING_CONTEXT_ROUTER.md)
- FOLDING_OUTER_SLOT (2026-07-24): [`detector/theory/FOLDING_OUTER_SLOT.md`](detector/theory/FOLDING_OUTER_SLOT.md)
- FOLDING_VOID_LINE_DRAW (2026-07-24): [`detector/theory/FOLDING_VOID_LINE_DRAW.md`](detector/theory/FOLDING_VOID_LINE_DRAW.md)
- FOLDING_SKIN_DETECTOR (2026-07-24): [`theory/folding/FOLDING_SKIN_DETECTOR.md`](theory/folding/FOLDING_SKIN_DETECTOR.md) †
- FOLDING_SKIN_TEST (2026-07-24): [`theory/folding/FOLDING_SKIN_TEST.md`](theory/folding/FOLDING_SKIN_TEST.md) †
- FOLDING_SKIN (2026-07-23): [`theory/folding/FOLDING_SKIN.md`](theory/folding/FOLDING_SKIN.md) †
- FOLDING_PAIR_ALIGNMENT (2026-07-23): [`theory/folding/FOLDING_PAIR_ALIGNMENT.md`](theory/folding/FOLDING_PAIR_ALIGNMENT.md)
- FOLDING_METAL_WELLS (2026-07-23): [`theory/folding/FOLDING_METAL_WELLS.md`](theory/folding/FOLDING_METAL_WELLS.md)
- FOLDING_SOLVENT_SUPPLY (2026-07-23): [`theory/folding/FOLDING_SOLVENT_SUPPLY.md`](theory/folding/FOLDING_SOLVENT_SUPPLY.md)
- FOLDING_CHANNELS (2026-07-22): [`theory/folding/FOLDING_CHANNELS.md`](theory/folding/FOLDING_CHANNELS.md)
- FOLDING_VOID_REACH (2026-07-22): [`theory/folding/FOLDING_VOID_REACH.md`](theory/folding/FOLDING_VOID_REACH.md)
- FOLDING_DEFICIT_SITE (2026-07-22): [`theory/folding/FOLDING_DEFICIT_SITE.md`](theory/folding/FOLDING_DEFICIT_SITE.md)
- FOLDING_VORTEX_DEPOSITION (2026-07-22): [`theory/folding/FOLDING_VORTEX_DEPOSITION.md`](theory/folding/FOLDING_VORTEX_DEPOSITION.md)
- FOLDING_PIXEL_TRANSMISSION (2026-07-22): [`theory/folding/FOLDING_PIXEL_TRANSMISSION.md`](theory/folding/FOLDING_PIXEL_TRANSMISSION.md)
- FOLDING_SATURATION_BUDGET (2026-07-22): [`theory/folding/FOLDING_SATURATION_BUDGET.md`](theory/folding/FOLDING_SATURATION_BUDGET.md)
- FOLDING_WALL_GRADIENT (2026-07-22): [`theory/folding/FOLDING_WALL_GRADIENT.md`](theory/folding/FOLDING_WALL_GRADIENT.md)
- FOLDING_SEQUENCE_BUDGET (2026-07-21): [`theory/folding/FOLDING_SEQUENCE_BUDGET.md`](theory/folding/FOLDING_SEQUENCE_BUDGET.md)
- FOLDING_BLANKET (2026-07-21): [`theory/folding/FOLDING_BLANKET.md`](theory/folding/FOLDING_BLANKET.md)
- FOLDING_CLOSURE_UNIT (2026-07-21): [`theory/folding/FOLDING_CLOSURE_UNIT.md`](theory/folding/FOLDING_CLOSURE_UNIT.md)
- FOLDING_GOLDEN_DEPTH (2026-07-21): [`theory/folding/FOLDING_GOLDEN_DEPTH.md`](theory/folding/FOLDING_GOLDEN_DEPTH.md)
- FOLDING_FLOORS (2026-07-21): [`theory/folding/FOLDING_FLOORS.md`](theory/folding/FOLDING_FLOORS.md)
- FOLDING_PIXEL_STRAIN (2026-07-21): [`theory/folding/FOLDING_PIXEL_STRAIN.md`](theory/folding/FOLDING_PIXEL_STRAIN.md)
- FOLDING_BORDER_SLOTS (2026-07-21): [`theory/folding/FOLDING_BORDER_SLOTS.md`](theory/folding/FOLDING_BORDER_SLOTS.md)
- FOLDING_OUTLINE (2026-07-20): [`theory/folding/FOLDING_OUTLINE.md`](theory/folding/FOLDING_OUTLINE.md)
- FOLDING_TOWER (2026-07-20): [`theory/folding/FOLDING_TOWER.md`](theory/folding/FOLDING_TOWER.md)
- FOLDING_ONTO_PLM (2026-07-20): [`theory/folding/FOLDING_ONTO_PLM.md`](theory/folding/FOLDING_ONTO_PLM.md)
- FOLDING_WRAP_FULL (2026-07-20): [`theory/folding/FOLDING_WRAP_FULL.md`](theory/folding/FOLDING_WRAP_FULL.md)
- VOID_LINE_PAPER (2026-07-20): [`theory/folding/VOID_LINE_PAPER.md`](theory/folding/VOID_LINE_PAPER.md)
- FOLDING_ADAPTIVE_SIZE (2026-07-20): [`theory/folding/FOLDING_ADAPTIVE_SIZE.md`](theory/folding/FOLDING_ADAPTIVE_SIZE.md)
- FOLDING_CLIMB_WALL (2026-07-19): [`theory/folding/FOLDING_CLIMB_WALL.md`](theory/folding/FOLDING_CLIMB_WALL.md)
- FOLDING_UNIVERSAL_READER (2026-07-19): [`theory/folding/FOLDING_UNIVERSAL_READER.md`](theory/folding/FOLDING_UNIVERSAL_READER.md)
- FOLDING_EYE_TYPES (2026-07-19): [`theory/folding/FOLDING_EYE_TYPES.md`](theory/folding/FOLDING_EYE_TYPES.md)
- FOLDING_FUNNEL (2026-07-19): [`theory/folding/FOLDING_FUNNEL.md`](theory/folding/FOLDING_FUNNEL.md)
- FOLDING_RECURSIVE_C (2026-07-19): [`theory/folding/FOLDING_RECURSIVE_C.md`](theory/folding/FOLDING_RECURSIVE_C.md)
- FOLDING_FOLD_OUT (2026-07-19): [`theory/folding/FOLDING_FOLD_OUT.md`](theory/folding/FOLDING_FOLD_OUT.md)
- FOLDING_TRAILS_MEET (2026-07-18): [`theory/folding/FOLDING_TRAILS_MEET.md`](theory/folding/FOLDING_TRAILS_MEET.md)
- FOLDING_TRAIL (2026-07-18): [`theory/folding/FOLDING_TRAIL.md`](theory/folding/FOLDING_TRAIL.md)
- FOLDING_MAP (2026-07-18): [`theory/folding/FOLDING_MAP.md`](theory/folding/FOLDING_MAP.md)
- FOLDING_STAIRCASE (2026-07-18): [`theory/folding/FOLDING_STAIRCASE.md`](theory/folding/FOLDING_STAIRCASE.md)
- FOLDING_OBSERVERS (2026-07-18): [`theory/folding/FOLDING_OBSERVERS.md`](theory/folding/FOLDING_OBSERVERS.md)
- FOLDING_SHADOW (2026-07-18): [`theory/folding/FOLDING_SHADOW.md`](theory/folding/FOLDING_SHADOW.md)
- FOLDING_CONTINUITY (2026-07-18): [`theory/folding/FOLDING_CONTINUITY.md`](theory/folding/FOLDING_CONTINUITY.md)
- FOLDING_D_AND_DIRECTIONS (2026-07-18): [`theory/folding/FOLDING_D_AND_DIRECTIONS.md`](theory/folding/FOLDING_D_AND_DIRECTIONS.md)
- FOLDING_TUNING_SHELLS (2026-07-18): [`theory/folding/FOLDING_TUNING_SHELLS.md`](theory/folding/FOLDING_TUNING_SHELLS.md)
- FOLDING_THE_EYE (2026-07-17): [`theory/folding/FOLDING_THE_EYE.md`](theory/folding/FOLDING_THE_EYE.md)
- FOLDING_C_PIXELS (2026-07-17): [`theory/folding/FOLDING_C_PIXELS.md`](theory/folding/FOLDING_C_PIXELS.md)
- FOLDING_GLOW (2026-07-17): [`theory/folding/FOLDING_GLOW.md`](theory/folding/FOLDING_GLOW.md)
- FOLDING_VORTEX (2026-07-17): [`theory/folding/FOLDING_VORTEX.md`](theory/folding/FOLDING_VORTEX.md)
- FOLDING_BLOCK_AND_RAMP (2026-07-17): [`theory/folding/FOLDING_BLOCK_AND_RAMP.md`](theory/folding/FOLDING_BLOCK_AND_RAMP.md)
- FOLDING_ONE_SIDE (2026-07-17): [`theory/folding/FOLDING_ONE_SIDE.md`](theory/folding/FOLDING_ONE_SIDE.md)
- FOLDING_MATCHING_SLOT (2026-07-17): [`theory/folding/FOLDING_MATCHING_SLOT.md`](theory/folding/FOLDING_MATCHING_SLOT.md)
- FOLDING_WIRE (2026-07-16): [`theory/folding/FOLDING_WIRE.md`](theory/folding/FOLDING_WIRE.md)
- FOLDING_STRANDS (2026-07-16): [`theory/folding/FOLDING_STRANDS.md`](theory/folding/FOLDING_STRANDS.md)
- FOLDING_SITE_PREDICTION (2026-07-16): [`theory/folding/FOLDING_SITE_PREDICTION.md`](theory/folding/FOLDING_SITE_PREDICTION.md)
- FOLDING_ATP_REFERENCE (2026-07-16): [`theory/folding/FOLDING_ATP_REFERENCE.md`](theory/folding/FOLDING_ATP_REFERENCE.md)
- FOLDING_KNIT_WEAVE (2026-07-16): [`theory/folding/FOLDING_KNIT_WEAVE.md`](theory/folding/FOLDING_KNIT_WEAVE.md)
- FOLDING_SALTS (2026-07-16): [`theory/folding/FOLDING_SALTS.md`](theory/folding/FOLDING_SALTS.md)
- FOLDING_CLEANUP (2026-07-16): [`theory/folding/FOLDING_CLEANUP.md`](theory/folding/FOLDING_CLEANUP.md)
- FOLDING_CUT_SERIES (2026-07-16): [`theory/folding/FOLDING_CUT_SERIES.md`](theory/folding/FOLDING_CUT_SERIES.md)
- FOLDING_ALIASING (2026-07-16): [`theory/folding/FOLDING_ALIASING.md`](theory/folding/FOLDING_ALIASING.md)
- FOLDING_THE_KNIFE (2026-07-16): [`theory/folding/FOLDING_THE_KNIFE.md`](theory/folding/FOLDING_THE_KNIFE.md)
- FOLDING_CONSTRAINT_LADDER (2026-07-16): [`theory/folding/FOLDING_CONSTRAINT_LADDER.md`](theory/folding/FOLDING_CONSTRAINT_LADDER.md)
- FOLDING_WINDOW_SEAM (2026-07-15): [`theory/folding/FOLDING_WINDOW_SEAM.md`](theory/folding/FOLDING_WINDOW_SEAM.md)
- FOLDING_TWO_WALLS (2026-07-15): [`theory/folding/FOLDING_TWO_WALLS.md`](theory/folding/FOLDING_TWO_WALLS.md)
- FOLDING_SLOTS (2026-07-15): [`theory/folding/FOLDING_SLOTS.md`](theory/folding/FOLDING_SLOTS.md)
- RIP_TEST_RESULTS (2026-07-14): [`theory/folding/RIP_TEST_RESULTS.md`](theory/folding/RIP_TEST_RESULTS.md)
- FOLDING_RIP_ROADMAP (2026-07-14): [`theory/folding/FOLDING_RIP_ROADMAP.md`](theory/folding/FOLDING_RIP_ROADMAP.md)
- FOLDING_FROM_SCRATCH (2026-07-13): [`theory/folding/FOLDING_FROM_SCRATCH.md`](theory/folding/FOLDING_FROM_SCRATCH.md)
- FOLDING_ARC_RESULTS (2026-07-12): [`theory/folding/FOLDING_ARC_RESULTS.md`](theory/folding/FOLDING_ARC_RESULTS.md)
- SPRING_TEST_RESULTS (2026-07-12): [`theory/folding/SPRING_TEST_RESULTS.md`](theory/folding/SPRING_TEST_RESULTS.md)

### Framework results and theory

- RESULTS (2026-07-04): [`theory/framework/RESULTS.md`](theory/framework/RESULTS.md)
- ISOLATION_TEST (2026-07-04): [`theory/framework/ISOLATION_TEST.md`](theory/framework/ISOLATION_TEST.md)
- SPHERE_GENERATOR_TEST (2026-07-04): [`theory/framework/SPHERE_GENERATOR_TEST.md`](theory/framework/SPHERE_GENERATOR_TEST.md)
- INNER_SHELL (2026-07-04): [`theory/framework/INNER_SHELL.md`](theory/framework/INNER_SHELL.md)
- ROOF_RESULTS (2026-07-04): [`theory/framework/ROOF_RESULTS.md`](theory/framework/ROOF_RESULTS.md)
- TRUST_AUDIT_RESULTS (2026-07-04): [`theory/framework/TRUST_AUDIT_RESULTS.md`](theory/framework/TRUST_AUDIT_RESULTS.md)
- MINING_NOTES (2026-07-04): [`theory/framework/MINING_NOTES.md`](theory/framework/MINING_NOTES.md)
- GEN_DRAW_RESULTS (2026-07-04): [`theory/framework/GEN_DRAW_RESULTS.md`](theory/framework/GEN_DRAW_RESULTS.md)
- VESICA_RESULTS (2026-07-04): [`theory/framework/VESICA_RESULTS.md`](theory/framework/VESICA_RESULTS.md)
- TRACE_RESULTS (2026-07-04): [`theory/framework/TRACE_RESULTS.md`](theory/framework/TRACE_RESULTS.md)
- TOPO_LIFT_RESULTS (2026-07-04): [`theory/framework/TOPO_LIFT_RESULTS.md`](theory/framework/TOPO_LIFT_RESULTS.md)
- EVAL_SCHEMA_MAP (2026-07-04): [`theory/framework/EVAL_SCHEMA_MAP.md`](theory/framework/EVAL_SCHEMA_MAP.md)
- PRUNE_RESULTS (2026-07-04): [`theory/framework/PRUNE_RESULTS.md`](theory/framework/PRUNE_RESULTS.md)
- BOUNCE_SCAN_RESULTS (2026-07-04): [`theory/framework/BOUNCE_SCAN_RESULTS.md`](theory/framework/BOUNCE_SCAN_RESULTS.md)
- SPARSE_VESICA_EXPANSION (2026-07-04): [`theory/framework/SPARSE_VESICA_EXPANSION.md`](theory/framework/SPARSE_VESICA_EXPANSION.md)
- SPHERE_GENERATOR (2026-07-04): [`theory/framework/SPHERE_GENERATOR.md`](theory/framework/SPHERE_GENERATOR.md)
- SHOVELCAT_THEORY (2026-07-04): [`theory/framework/SHOVELCAT_THEORY.md`](theory/framework/SHOVELCAT_THEORY.md)

*242 write-ups are listed with their place in this repository. Nothing is waiting to be copied.*
