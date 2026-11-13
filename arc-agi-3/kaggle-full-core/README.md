# Mika's full core on Kaggle: the last build (Nov 2 2026)

The code of the last build made for ARC-AGI-3, as it ran on Kaggle: Mika's full inner core with Gemma 4 as her
voice, the tube and the prism, and the Q-tube shape fit. The write-up is
[`../notes/ARC3_MIKA_FULL_CORE.md`](../notes/ARC3_MIKA_FULL_CORE.md), which calls these sources `planet_port/`.

The working copy of the planet in [`../planet/`](../planet/) stops a few days earlier and does not have the
Kaggle wiring, the later voices, the prism or the shape fit. Those files were recovered from the Kaggle run
"prism + Q-tube v2" (notebook `mika-gemma-26b-v5-ask-prism-qtube-irr-arc-agi-3`) and checked against the
archive inside the notebook: all 49 modules match.

## What is here

- **`mika-core.ipynb`** is the notebook that ran. One cell unpacked the 49 planet modules from a base64
  archive; the archive is removed from this copy, so the notebook shows how the run was wired but will not run
  as it is.
- **`planet/`** has the 11 modules of that build that are new or changed:
  - new: `mika_agent.py` (the competition agent), `mika_bridge.py` (her body and core on any game an `arc_agi`
    environment serves), `lm_server.py` (her voice, served the way her code asks for it), `mika_voice4.py`
    (the screen goes with the question), `mika_voice5.py` (she briefs her voice before she asks),
    `mika_prism.py` (the tube and the prism) and `qtube_fit.py` (the Q-tube's shape fit);
  - changed by a few lines each: `mika_core.py` and `relations.py` (the Q-tube hooks), `play.py` and `meter.py`
    (small fixes, one of them for the crash the write-up mentions).
- **`mika_smoke.json`** is that run's result on the 25 public games: 10 levels, mean score 0.416, no crashes.
  It is the "prism + Q-tube v2" row of the table in the write-up.

The other 38 modules the build unpacked are the same as the files of the same name in `../planet/`, apart
from line endings:

`arc3_client.py`, `arc3_preflight.py`, `arc_daily.py`, `arcshim.py`, `chain.py`, `collect.py`,
`cube_memory.py`, `cube_router.py`, `diagonal.py`, `evaluation_batch.py`, `eye.py`, `fence.py`, `fold.py`,
`geo.py`, `induce.py`, `lines.py`, `lower.py`, `magnet.py`, `mika_mind.py`, `mika_think.py`, `mika_tree.py`,
`moon.py`, `oncall.py`, `pin_questions.py`, `pins.py`, `play_metrics.py`, `pool.py`, `prioragent.py`,
`prioragent_candidate.py`, `prioragent_reviewed_baseline.py`, `quat.py`, `relation_guard.py`, `rings.py`,
`route.py`, `storyteller.py`, `torus.py`, `touch.py`, `views.py`.

**Not included:** the Gemma 4 weights, the wheels dataset, the run logs, and the notebook builder
(`build_core_nb.py`), which was not in the folders this repository was assembled from.
