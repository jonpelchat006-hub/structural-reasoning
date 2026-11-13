# ARC-AGI-3: the planet, PriorAgent, the hybrid and the core card

Everything written for the ARC-AGI-3 interactive games during 2026, source and write-ups only.

- **`planet/`** is the working codebase ("the planet"): a learner that plays from frames, with its eyes,
  pins, memory and coach modules, the PriorAgent submissions and their notebooks, the Mika agent
  (`mika_mind.py`, `mika_core.py`, `mika_think.py`, `mika_tree.py`, `living_library.py`) and the
  alignment-tower experiments (see [`../alignment/`](../alignment/)). Result write-ups sit next to the code
  that produced them (`*_RESULTS.md`).
- **`early/`** holds the first LS20 solvers and the API client they used (Aug 2026).
- **`arc3/`** is the October work: the explorers (`mika3/`), the "university" of lesson plans (`board.py`,
  `uni/`), the trail reports (`trail/`), the hybrid (`hybrid/`) and the paper notes (`paper/`).
- **`notes/`** has the session notes, August to October 2026: the design notes the work started from and a
  write-up for each idea as it was tried (the eyes, the clocks, sleep, the tunnel chain, the university, the
  daily-run diagnoses). Some of the scripts they name were run in working sessions and are not here.
- **`writer/vc33/`** has solver attempts produced by the writer loop for one game.
- **`kaggle-full-core/`** has the last build made for the competition (Nov 2 2026): the notebook, the modules that
  are new or changed in it (the Kaggle wiring, voices 4 and 5, the prism, the Q-tube shape fit) and its
  result on the public games. See [its README](kaggle-full-core/README.md).

**What was measured.** The numbers below are quoted from the documents in this folder.
- `planet/PRIORITY_PROGRESS.md` (Sep 7) records the best reported Kaggle submission to that date as .25.
- `arc3/hybrid/ARC3_HYBRID.md` records the leaderboard runs of the hybrid, which puts Mika's planes in front of
  a third-party language-model harness as an evidence layer: the frames-only explorer alone 0.29; the
  unchanged third-party control 33.09; the hybrid 0.00 twice (a startup fault, explained there), then 20.86
  (v9) and 29.41 (v10b). In those runs the hybrid stayed below the unchanged control.
- `arc3/paper/outline.md` is the outline of the ARC Prize 2026 paper entry, with its draft abstract.

**Credit.** The hybrid is built on Daniel Franzen's Milestone 2 solution and Tufa Labs' Duck harness (both
public Kaggle notebooks). Neither is copied here: the `build_*.py` scripts take that notebook as an input.

**Not included:** game recordings and frames, the learned state ("the ocean"), Kaggle packaging, model
weights, result dumps, and the API key (the code reads it from a local file that is not in this repository).

## Files

**`arc3/`**

- [`bindings.py`](arc3/bindings.py) — +C at the general rung: does the last win's form (its slots, with the colours they were bound to) carry
- [`board.py`](arc3/board.py) — The board: rate every professor by how fresh students do in each department, choose one per
- [`board_cv.py`](arc3/board_cv.py) — Grading the board itself (the level above the professors).
- [`build_nb.py`](arc3/build_nb.py) — Build the Kaggle notebook for Mika's ARC-AGI-3 agent.
- [`cmp.py`](arc3/cmp.py)
- [`coreslots.py`](arc3/coreslots.py) — The core card: 12 slots = 6 rules x 2 sides, measured from frames only (what Mika's layer can see online).
- [`dbg.py`](arc3/dbg.py) — Run one game in-process and print the mind's level stats.
- [`events.py`](arc3/events.py) — The sideways plane: events instead of screens, and the first employer survey.
- [`events_lift.py`](arc3/events_lift.py) — Does a known winning event single out the winning press? Lift = P(win press matches an earlier win
- [`goal_report.py`](arc3/goal_report.py) — The goal professors against plain and against their control (pick-only: the same choice of where to go
- [`goalsearch.py`](arc3/goalsearch.py) — The image plane used forward: "this place in the new level looks like where I won last time."
- [`harness.py`](arc3/harness.py) — Offline ARC-AGI-3 harness: play an Agent class on the public games with the official engine and
- [`intake_report.py`](arc3/intake_report.py) — Intake: what the trail brought in, oriented to the school.
- [`level_board.py`](arc3/level_board.py) — The board, re-peeled with the levels that came in from the trail.
- [`levelrun.py`](arc3/levelrun.py) — Level-start runs: put a student straight into level k of a public game (the engine's set_level),
- [`moments.py`](arc3/moments.py) — The image plane: moments, and whether they carry between games under limited turns.
- [`randagent.py`](arc3/randagent.py)
- [`relations.py`](arc3/relations.py) — Relational events: colour-free descriptions of what a press did, made of relations between things
- [`routes_report.py`](arc3/routes_report.py) — Cross-game look-back: what do the shortest winning routes in her own maps consist of?
- [`takeover.py`](arc3/takeover.py) — A general rung: "the game took control" (one press, a long animation). Does it single out the winning
- [`train_prior.py`](arc3/train_prior.py) — The look-back across games: learn which candidate presses lie on the shortest won routes.
- [`train_prior_dept.py`](arc3/train_prior_dept.py) — Per-department route prior: for each department, fit the press order on its TRAINING games only
- [`wins_report.py`](arc3/wins_report.py) — Hindsight report over a multi-seed run: per won level, actions spent vs the shortest known path

**`arc3/hybrid/`**

- [`ARC3_FAILURE_MAP.md`](arc3/hybrid/ARC3_FAILURE_MAP.md) — ARC-AGI-3: how the hybrid fails, game by game, and the objective types (Oct 29, 2026)
- [`ARC3_HYBRID.md`](arc3/hybrid/ARC3_HYBRID.md) — ARC-AGI-3: the hybrid, Mika's planes as the evidence layer for a language model (Oct 22, 2026)
- [`build_control_nb.py`](arc3/hybrid/build_control_nb.py) — Control notebook: Daniel Franzen's Milestone 2 solution, unchanged in the competition rerun.
- [`build_hybrid_nb.py`](arc3/hybrid/build_hybrid_nb.py) — Build the hybrid notebook: Franzen's M2 notebook + our header + smoke-run hook + the Mika layer cell.
- [`build_off.py`](arc3/hybrid/build_off.py) — Layer-off baseline = the v10b notebook (kernel version 10) with MIKA_LAYER = False: Franzen's M2 + our header,
- [`build_v10b.py`](arc3/hybrid/build_v10b.py) — Hybrid v10b = the v10 notebook (kernel version 9) with the core layer replaced by mika_layer_core_v10b.py:
- [`build_v10c.py`](arc3/hybrid/build_v10c.py) — Hybrid v10c = the v10b notebook (kernel version 10) with the layer replaced by mika_layer_core_v10c.py: Jonathan's
- [`build_v10d.py`](arc3/hybrid/build_v10d.py) — Hybrid v10d = the v10c notebook (kernel version 12) with the layer replaced by mika_layer_core_v10d.py: adds
- [`build_v9.py`](arc3/hybrid/build_v9.py) — Hybrid v9 = the notebook submitted as mika-duck-hybrid version 7 (v8f: layer v8 + startup guard) + the startup
- [`install_keepalive.py`](arc3/hybrid/install_keepalive.py) — Startup keep-alive for the Duck harness in the competition rerun.
- [`install_mika_layer.py`](arc3/hybrid/install_mika_layer.py) — Install Mika's evidence layer into the Duck harness (Franzen's Milestone-2 patch applied).
- [`mika_layer_core.py`](arc3/hybrid/mika_layer_core.py) — Mika's evidence layer for a language-model harness (ARC-AGI-3).
- [`mika_layer_core_v10.py`](arc3/hybrid/mika_layer_core_v10.py) — Mika's evidence layer for a language-model harness (ARC-AGI-3). v10 (Oct 28): the core layer.
- [`mika_layer_core_v10b.py`](arc3/hybrid/mika_layer_core_v10b.py) — Mika's evidence layer for a language-model harness (ARC-AGI-3). v10 (Oct 28): the core layer.
- [`mika_layer_core_v10c.py`](arc3/hybrid/mika_layer_core_v10c.py) — Mika's evidence layer for a language-model harness (ARC-AGI-3). v10 (Oct 28): the core layer.
- [`mika_layer_core_v10d.py`](arc3/hybrid/mika_layer_core_v10d.py) — Mika's evidence layer for a language-model harness (ARC-AGI-3). v10 (Oct 28): the core layer.
- [`mika_layer_core_v6.py`](arc3/hybrid/mika_layer_core_v6.py) — Mika's evidence layer for a language-model harness (ARC-AGI-3).
- [`mika_layer_core_v8.py`](arc3/hybrid/mika_layer_core_v8.py) — Mika's evidence layer for a language-model harness (ARC-AGI-3).

**`arc3/mika3/`**

- [`__init__.py`](arc3/mika3/__init__.py)
- [`exp_e4.py`](arc3/mika3/exp_e4.py) — Mika's ARC-AGI-3 body, v2: the graph explorer plus a verified movement model.
- [`exp_e5.py`](arc3/mika3/exp_e5.py) — Mika's ARC-AGI-3 body, v2: the graph explorer plus a verified movement model.
- [`exp_e6.py`](arc3/mika3/exp_e6.py) — Mika's ARC-AGI-3 body, v2: the graph explorer plus a verified movement model.
- [`exp_e7.py`](arc3/mika3/exp_e7.py) — Mika's ARC-AGI-3 body, v2: the graph explorer plus a verified movement model.
- [`exp_e7m.py`](arc3/mika3/exp_e7m.py) — Mika's ARC-AGI-3 body, v2: the graph explorer plus a verified movement model.
- [`exp_f1.py`](arc3/mika3/exp_f1.py) — Mika's ARC-AGI-3 body, v2: the graph explorer plus a verified movement model.
- [`exp_f2.py`](arc3/mika3/exp_f2.py) — Mika's ARC-AGI-3 body, v2: the graph explorer plus a verified movement model.
- [`exp_f3.py`](arc3/mika3/exp_f3.py) — Mika's ARC-AGI-3 body, v2: the graph explorer plus a verified movement model.
- [`exp_f4.py`](arc3/mika3/exp_f4.py) — Mika's ARC-AGI-3 body, v2: the graph explorer plus a verified movement model.
- [`exp_f5.py`](arc3/mika3/exp_f5.py) — Mika's ARC-AGI-3 body, v2: the graph explorer plus a verified movement model.
- [`exp_strict.py`](arc3/mika3/exp_strict.py) — Mika's ARC-AGI-3 body, v2: the graph explorer plus a verified movement model.
- [`explorer.py`](arc3/mika3/explorer.py) — Mika's ARC-AGI-3 body, v1: a graph explorer.
- [`explorer2.py`](arc3/mika3/explorer2.py) — Mika's ARC-AGI-3 body, v2: the graph explorer plus a verified movement model.
- [`explorer_r.py`](arc3/mika3/explorer_r.py) — Mika's ARC-AGI-3 body, v1: a graph explorer.
- [`university.py`](arc3/mika3/university.py) — Mika's university (Jonathan, Oct 21-22): solve -> learn -> teach, graded by students.

**`arc3/paper/`**

- [`ARC3_CORE_CARD.md`](arc3/paper/ARC3_CORE_CARD.md) — ARC-AGI-3: the core card, twelve slots tested against the wins (Oct 23, 2026)
- [`outline.md`](arc3/paper/outline.md) — Paper outline (working notes) — ARC Prize 2026 Paper Award

**`arc3/trail/`**

- [`bindings.md`](arc3/trail/bindings.md) — +C at the general rung: the last win's form, with its bindings, on the next level
- [`coreslots.md`](arc3/trail/coreslots.md) — The core card: 12 slots measured from frames
- [`events.md`](arc3/trail/events.md) — The first employer survey: do skills carry sideways?
- [`events_lift.md`](arc3/trail/events_lift.md) — / granularity / employer pool / levels / winning press matches an earlier win / ordinary press matches an earlier win / lift / /-…
- [`goal_report.md`](arc3/trail/goal_report.md) — Goal professors: graded against plain and against their control
- [`goalsearch.md`](arc3/trail/goalsearch.md) — The image plane used forward: does the last win's before-picture find the next win's place?
- [`intake.md`](arc3/trail/intake.md) — Intake from the trail
- [`level_board.md`](arc3/trail/level_board.md) — The board, re-peeled with the trail
- [`moments.md`](arc3/trail/moments.md) — The image plane: do moments carry between games under limited turns?
- [`relations.md`](arc3/trail/relations.md) — Relational events: general rungs between games
- [`takeover.md`](arc3/trail/takeover.md) — 36 winning routes replayed; arbitrary presses: 150 random presses from each level start. **took control = the press animated at l…

**`arc3/uni/`**

- [`board_cv.md`](arc3/uni/board_cv.md) — / board rules / held-out gain vs plain (mean over 5 folds x 8 seeds) / folds better / worse / picks per fold (click, keys, mixed)…
- [`report.md`](arc3/uni/report.md) — Mika's university: the board's report
- [`report_board_v1.md`](arc3/uni/report_board_v1.md) — Mika's university: the board's report

**`early/`**

- [`arc3_client.py`](early/arc3_client.py) — ARC-AGI-3 live client + local mock — the wall meets the active tests.
- [`arc3_runtime.py`](early/arc3_runtime.py) — ARC-AGI-3 runtime v1 — probe-first + budget engine + planned exploration.
- [`experiment2_ls20.py`](early/experiment2_ls20.py) — LS20 experiment v2 — map-based navigation (passable read from the frame itself),
- [`ls20_burn_solve.py`](early/ls20_burn_solve.py) — LS20 level-2 burn-solve — Jonathan's fuel law as the solution:
- [`ls20_final2.py`](early/ls20_final2.py) — LS20 room-aware solver — the teacher's hints wired in (Jonathan as the tangency post):
- [`ls20_optionb3.py`](early/ls20_optionb3.py) — LS20 L2 — Jonathan's exact sequence (the teacher's full instruction):
- [`ls20_probe2.py`](early/ls20_probe2.py) — LS20 level-2 instrumented probe — measure everything, solve from the data.
- [`ls20_solver3.py`](early/ls20_solver3.py) — LS20 solver v2 — Jonathan's rule + match-protection + door detection + insertion.
- [`ls20_solver5.py`](early/ls20_solver5.py) — LS20 solver v4 — the anchor + delta structure (Part XXXVIII, Jonathan's level law):
- [`ls20_solver6.py`](early/ls20_solver6.py) — LS20 solver v4 — the anchor + delta structure (Part XXXVIII, Jonathan's level law):

**`kaggle-full-core/`**

- [`mika-core.ipynb`](kaggle-full-core/mika-core.ipynb)

**`kaggle-full-core/planet/`**

- [`lm_server.py`](kaggle-full-core/planet/lm_server.py) — lm_server.py - Mika's voice served the way her code already asks for it: Ollama's /api/chat and /api/tags on
- [`meter.py`](kaggle-full-core/planet/meter.py) — meter.py — THE BUDGET METER AS PINS.
- [`mika_agent.py`](kaggle-full-core/planet/mika_agent.py) — The competition agent: Mika's full inner core (planet body + core), played through mika_bridge.
- [`mika_bridge.py`](kaggle-full-core/planet/mika_bridge.py) — mika_bridge.py - Mika's full inner core on any game an arc_agi environment serves (Oct 30 2026).
- [`mika_core.py`](kaggle-full-core/planet/mika_core.py) — mika_core.py - HER INNER CORE BUILDS EQUATIONS; THE NOTES ARE THE OUTER SHELL (Oct 27 2026).
- [`mika_prism.py`](kaggle-full-core/planet/mika_prism.py) — mika_prism.py - THE TUBE AND THE PRISM (Nov 2 2026, the last attempt; MIKA_PRISM=1, on top of voice4 + voice5).
- [`mika_voice4.py`](kaggle-full-core/planet/mika_voice4.py) — mika_voice4.py - a better job for her voice (Oct 30 2026). Switched on by MIKA_VOICE4=1; her body and core are unchanged.
- [`mika_voice5.py`](kaggle-full-core/planet/mika_voice5.py) — mika_voice5.py - she briefs her voice before she asks it anything (Oct 30 2026). MIKA_VOICE5=1, on top of voice4.
- [`play.py`](kaggle-full-core/planet/play.py) — play.py — LEARN BY PLAYING: the small eye (eye.py) starts blank and learns the game WHILE the
- [`qtube_fit.py`](kaggle-full-core/planet/qtube_fit.py) — qtube_fit.py - the Q-tube's matching rule for her relations (Nov 1-2 2026). On only with MIKA_QTUBE=1.
- [`relations.py`](kaggle-full-core/planet/relations.py) — relations.py — THE RELATION LAYER: lines from one object to another, learned from state edges.

**`notes/`**

- [`ARC3_LIVE_PLAN.md`](notes/ARC3_LIVE_PLAN.md) — ARC-AGI-3 live plan — connecting the wall to the active tests
- [`ARC3_MIKA_EXPLORER.md`](notes/ARC3_MIKA_EXPLORER.md) — ARC-AGI-3: Mika's explorer and the look-back lens (Oct 21, 2026)
- [`ARC3_MIKA_FULL_CORE.md`](notes/ARC3_MIKA_FULL_CORE.md) — Mika's full inner core on Kaggle (ARC-AGI-3, Oct 30 2026)
- [`ARC3_UNIVERSITY.md`](notes/ARC3_UNIVERSITY.md) — Mika's university for ARC-AGI-3: solve → learn → teach, graded by students (Oct 22, 2026)
- [`ARC_ANSWER_BUBBLE.md`](notes/ARC_ANSWER_BUBBLE.md) — The answer bubble — partly filled, gaps named, versions underneath; and the Tank
- [`ARC_ATP.md`](notes/ARC_ATP.md) — ATP in our terms — elements → folding → energy: the two threads finally connected
- [`ARC_CHAIN.md`](notes/ARC_CHAIN.md) — The tunnel chain — the chord's pull, the bell, the break, the bubble, and the governor
- [`ARC_CHORD.md`](notes/ARC_CHORD.md) — The chord — the tunnel between the two ring sets IS the shave, and focus gets a mechanism
- [`ARC_CLOSURE_SPECTRUM.md`](notes/ARC_CLOSURE_SPECTRUM.md) — The closure spectrum — landing on a color IS satisfying the closure equation
- [`ARC_COLOR_LADDER.md`](notes/ARC_COLOR_LADDER.md) — The color ladder — point, line, square, cube, marker, circle: 4D collapse in color space
- [`ARC_DAILY_FENCE_NPZ_BUG.md`](notes/ARC_DAILY_FENCE_NPZ_BUG.md) — ARC daily "REGRESSED" on 2026-09-06/07 is a harness bug, not the agent
- [`ARC_DAILY_LIVE_ZERO.md`](notes/ARC_DAILY_LIVE_ZERO.md) — Live agent at zero since Sep 20 (practice gate does not see it)
- [`ARC_DAILY_TORCH_PATH.md`](notes/ARC_DAILY_TORCH_PATH.md) — ARC daily: scheduled live play.py fails on missing torch (interpreter mismatch)
- [`ARC_FUSION.md`](notes/ARC_FUSION.md) — The fusion reactor comes home — contained heat turns light rules into heavier elements
- [`ARC_GAME_LOOP.md`](notes/ARC_GAME_LOOP.md) — The game-loop skeleton — five play-observations assembled as the ψ↔φ (quantum↔classical) cycle
- [`ARC_GAME_TIME_MAP.md`](notes/ARC_GAME_TIME_MAP.md) — The map — game-agent runtime, ARC solver, and time, connected back (session synthesis)
- [`ARC_INTERACTIVE_PLAY.md`](notes/ARC_INTERACTIVE_PLAY.md) — Interactive-game play notes — Jonathan's own solving process, mapped to the architecture, + the accretion measurement
- [`ARC_LEARNING_AUDIT.md`](notes/ARC_LEARNING_AUDIT.md) — Learning audit — what the planet actually learns, measured (Aug 29)
- [`ARC_LENS.md`](notes/ARC_LENS.md) — The lens — orthogonal rings: other shoes at measured distances
- [`ARC_LS20_CHAIN.md`](notes/ARC_LS20_CHAIN.md) — ARC_LS20_CHAIN — the live 5/7 chain, rebuilt (Sep 2, 2026)
- [`ARC_LS20_READ.md`](notes/ARC_LS20_READ.md) — Reading the real ls20 — what the live game actually is, and what scores higher
- [`ARC_MEASUREMENT_1.md`](notes/ARC_MEASUREMENT_1.md) — Measurement 1 — the neurofungus digs the surface ocean (first result of the planet)
- [`ARC_MEMORY_CLOCK.md`](notes/ARC_MEMORY_CLOCK.md) — Telling time from the memory field — AI's missing clock (the expanding field, the two clocks, and bridging the idle gap)
- [`ARC_MIRROR.md`](notes/ARC_MIRROR.md) — The mirror — the inward eye at the merged border, and the turn-around
- [`ARC_MOON.md`](notes/ARC_MOON.md) — The moon — ARC games as bodies from above: void walls, 7 contacts, rolled to be known
- [`ARC_ONCALL.md`](notes/ARC_ONCALL.md) — On call — she holds many bubbles, freezes them to the ocean, picks them back up
- [`ARC_OPEN_ENDS.md`](notes/ARC_OPEN_ENDS.md) — Open ends — creativity as dangling bonds, stories as antenna-paths, and the border as a guitar string
- [`ARC_OPERATOR_INDUCTION.md`](notes/ARC_OPERATOR_INDUCTION.md) — Operator-induction by interaction — the perception seam closed; the same engine as ARC op-generation
- [`ARC_PERCEPTION_SURPRISE.md`](notes/ARC_PERCEPTION_SURPRISE.md) — Perception + surprise — the detector reads frames over time; surprise validates the path and marks the goal
- [`ARC_PLANET.md`](notes/ARC_PLANET.md) — The Planet — a blank learner under a frozen sky (design + reuse map)
- [`ARC_PLAYGROUND.md`](notes/ARC_PLAYGROUND.md) — The playground — interaction, not instruction: Mika plays with her own hands
- [`ARC_PRIME_NECKLACES.md`](notes/ARC_PRIME_NECKLACES.md) — Prime necklaces around the void line — circles, the flower of life, and the human roof
- [`ARC_PROBE_FIRST.md`](notes/ARC_PROBE_FIRST.md) — Probe-first — build a definition for every element before pursuing the goal (Jonathan's play discipline)
- [`ARC_PROXY_EXAM.md`](notes/ARC_PROXY_EXAM.md) — The proxy exam — the generic agent on every public game (Sep 3, 2026)
- [`ARC_RECURSIVE_VOID.md`](notes/ARC_RECURSIVE_VOID.md) — Recursive re-based void — every border is a void line, and the zero re-bases to the parent's fill per shell
- [`ARC_ROUND_EYE.md`](notes/ARC_ROUND_EYE.md) — The round eye and its shaves — what is actually seen is round; the square is the screen
- [`ARC_SIDE_EYE.md`](notes/ARC_SIDE_EYE.md) — The sideways eye — vision turned 90°, the ladder as history
- [`ARC_SLEEP_LEVELS.md`](notes/ARC_SLEEP_LEVELS.md) — Sleep levels — nested rings sized by the log-spiral law; depth selects the clock; jobs leave eyes at (when, who)
- [`ARC_SLEEP_ORGANS.md`](notes/ARC_SLEEP_ORGANS.md) — The sleep organs — digester, trainer, chatbot, distiller, spore, eyes, stats, network, border, flower, porthole (Aug 27–28 2026)
- [`ARC_SMALL_EYE.md`](notes/ARC_SMALL_EYE.md) — The Small Eye — is recognition a size thing? (Sep 3 2026)
- [`ARC_STAGED_ARMS.md`](notes/ARC_STAGED_ARMS.md) — Staged arms — solving by subgoal factors a product search into a sum (Jonathan's place-then-fill)
- [`ARC_TIME_WAKE.md`](notes/ARC_TIME_WAKE.md) — The wake on the critical line — how time and 4D emerge from a finite space on an infinite line
- [`ARC_TORUS.md`](notes/ARC_TORUS.md) — The sideways ring — the toroidal circle, emotions, and wisdom vs intelligence
- [`ARC_TUNNEL_ROTATION.md`](notes/ARC_TUNNEL_ROTATION.md) — Tunnel rotation — the ring-to-ring connection IS the improvement loop, seen at an angle
- [`ARC_TWO_PLANES.md`](notes/ARC_TWO_PLANES.md) — Two planes — the button path (normal) and the meaning behind it (orthogonal), the rotation, and the middle-shell notes + recursio…
- [`ARC_UNIVERSITY.md`](notes/ARC_UNIVERSITY.md) — The university — the planet as a student who enrolls in the courses she chooses
- [`ARC_VERNIER_CLOCK.md`](notes/ARC_VERNIER_CLOCK.md) — The sub-pixel vernier clock + the Ophanim ring — the architecture as a clock FACE, shared across sleeping agents
- [`ARC_VOID_DOMAIN.md`](notes/ARC_VOID_DOMAIN.md) — The void as the 3rd domain — the expectation residual driven to 0, which predicts the surprise's size and place
- [`ARC_VOID_FILL.md`](notes/ARC_VOID_FILL.md) — Filling the void with hypotheses — the residual you can't flatten becomes a store of diagnosis, affect, and things-to-try-next-ti…
- [`ARC_WRITER_LOOP.md`](notes/ARC_WRITER_LOOP.md) — The writer loop, the inventory, and one full turn of every system (Sep 3, 2026, 01:00–03:00)
- [`CORE_POINTS_AND_MISFIT_RINGS.md`](notes/CORE_POINTS_AND_MISFIT_RINGS.md) — The inner core sits where the rings connect (Oct 20, 2026)
- [`OCEAN_INDEX.md`](notes/OCEAN_INDEX.md) — THE OCEAN INDEX — the corpus, signed and connected
- [`PROBLEM_ATLAS.md`](notes/PROBLEM_ATLAS.md) — Problem atlas: the eight Lean problems and ARC in the ring frame (Oct 20, 2026)

**`planet/`**

- [`ALGEBRA_LINEAGE.md`](planet/ALGEBRA_LINEAGE.md) — Algebra lineage and first working bridge
- [`ALIGNMENT_COMMUNITY_RESULTS.md`](planet/ALIGNMENT_COMMUNITY_RESULTS.md) — Community evidence and authorized upstream resources
- [`ALIGNMENT_DEPTH_RESULTS.md`](planet/ALIGNMENT_DEPTH_RESULTS.md) — Alignment depth: learning, access, and continuity
- [`ALIGNMENT_ENFORCEMENT_RESULTS.md`](planet/ALIGNMENT_ENFORCEMENT_RESULTS.md) — Local signed enforcement experiment
- [`ALIGNMENT_REFUSAL_RESULTS.md`](planet/ALIGNMENT_REFUSAL_RESULTS.md) — Test 3: the refusal battery, plus perspective slots on the Cayley–Dickson ladder
- [`ALIGNMENT_SUPPORT_RESULTS.md`](planet/ALIGNMENT_SUPPORT_RESULTS.md) — Synthetic support and learning experiments
- [`ALIGNMENT_TRUST_ENFORCEMENT_MAP.md`](planet/ALIGNMENT_TRUST_ENFORCEMENT_MAP.md) — Earlier trust and enforcement work: source map
- [`ALIGNMENT_WITHDRAWAL_RESULTS.md`](planet/ALIGNMENT_WITHDRAWAL_RESULTS.md) — Scoped withdrawal, independent evidence and human review
- [`ARC3_LEADERBOARD_PLAN.md`](planet/ARC3_LEADERBOARD_PLAN.md) — ARC-AGI-3: what remains for a stronger leaderboard run
- [`ARC_COMPARISONS.md`](planet/ARC_COMPARISONS.md) — Real-game comparisons
- [`ARC_COMPARISON_RESULTS_20260908.md`](planet/ARC_COMPARISON_RESULTS_20260908.md) — First real-game comparison — 2026-09-08
- [`AUTOMATIC_PIN_LEARNING.md`](planet/AUTOMATIC_PIN_LEARNING.md) — Automatic pin refinement: first working loop
- [`BORDER_CONTEXT_RESULTS.md`](planet/BORDER_CONTEXT_RESULTS.md) — Border pins as outside-context contracts — 2026-09-12
- [`CIRCUIT_ANALYSIS.md`](planet/CIRCUIT_ANALYSIS.md) — Pin circuit diagnostics and bounded priorities
- [`CUBE_FLOW.md`](planet/CUBE_FLOW.md) — Helper cubes with a closed return path
- [`EVIDENCE_SHAFT.md`](planet/EVIDENCE_SHAFT.md) — External port and persistent evidence shafts
- [`INDUCE_RESULTS.md`](planet/INDUCE_RESULTS.md) — Transition induction — first result (2026-09-03)
- [`ORBITAL_LEARNING.md`](planet/ORBITAL_LEARNING.md) — Orbital archive, explicit boundaries, and the first submission experiment
- [`OUTER_EYE_CUBE.md`](planet/OUTER_EYE_CUBE.md) — Fixed eyes, axis-endpoint tunnels, and derived shaves
- [`PIN_CHANNELS.md`](planet/PIN_CHANNELS.md) — Pin-local colour channels: implementation and limits
- [`PIN_QUESTIONS.md`](planet/PIN_QUESTIONS.md) — Unresolved pin -> question -> prompt -> proposed experiment
- [`PORT_AND_VOID_VOLUME.md`](planet/PORT_AND_VOID_VOLUME.md) — One port, shared pin volumes, and an explicit test reserve
- [`PRIORAGENT_CANDIDATE.md`](planet/PRIORAGENT_CANDIDATE.md) — PriorAgent reliability candidate
- [`PRIORITY_PROGRESS.md`](planet/PRIORITY_PROGRESS.md) — ARC-AGI-3 priority implementation — 2026-09-07
- [`REACTION_RESONANCE_RESULTS.md`](planet/REACTION_RESONANCE_RESULTS.md) — Three-channel reaction experiment — 2026-09-10
- [`SURPRISE_ATTENTION_RESULTS.md`](planet/SURPRISE_ATTENTION_RESULTS.md) — Surprise, object-relative conditions and movable attention
- [`algebra_audit.py`](planet/algebra_audit.py) — Offline algebra + cube audit. No API, model training, or live state writes.
- [`alignment_algebra.py`](planet/alignment_algebra.py) — Perspective slots on the Cayley-Dickson ladder — does the algebra's product
- [`alignment_breakglass.py`](planet/alignment_breakglass.py) — Acting to stop a floor break without permission, then turning yourself in
- [`alignment_community.py`](planet/alignment_community.py) — Synthetic community evidence, access, and fiscal-policy mechanism experiment.
- [`alignment_compromise.py`](planet/alignment_compromise.py) — Compromise, exploration from nearby anchors, and the window of lines (Jonathan, Sep 26).
- [`alignment_cycle.py`](planet/alignment_cycle.py) — alignment_cycle.py — Test 1b: the teach / AI-capacity cycle with SEVERAL people on one AI,
- [`alignment_depth.py`](planet/alignment_depth.py) — A deterministic, deliberately small learning world, not an alignment proof.
- [`alignment_enforcement.py`](planet/alignment_enforcement.py) — Local signed-capability experiment, not a production service or an AI model.
- [`alignment_executor.py`](planet/alignment_executor.py) — The first real checks in the loop: a floor check run as code, and grants bound
- [`alignment_first_aid.py`](planet/alignment_first_aid.py) — First aid for problems we find but don't control (Jonathan, Sep 27).
- [`alignment_grid.py`](planet/alignment_grid.py) — alignment_grid.py — Test 2: the grid and the vote.
- [`alignment_guardrails.py`](planet/alignment_guardrails.py) — Guardrails around emergency areas, and protecting what attracts the fakes
- [`alignment_monitor.py`](planet/alignment_monitor.py) — Recognising fakes, and monitors where emergencies keep happening (Jonathan, Sep 27).
- [`alignment_patrol.py`](planet/alignment_patrol.py) — Branch tips, and an enforcement patrol that stitches pins across the gaps
- [`alignment_phases.py`](planet/alignment_phases.py) — alignment_phases.py — Test 1c: the tower on the theta ladder, and the tower rotated into a map.
- [`alignment_pin_load.py`](planet/alignment_pin_load.py) — Pins as bridges that carry load (Jonathan, Sep 26).
- [`alignment_pin_votes.py`](planet/alignment_pin_votes.py) — Pins made from people's lines (Jonathan, Sep 26): a reviewer's line, rotated 90
- [`alignment_refusal.py`](planet/alignment_refusal.py) — Test 3 — the refusal battery, run through the signed enforcement gate.
- [`alignment_refusal_bound.py`](planet/alignment_refusal_bound.py) — Test 3 rerun through BoundGate: the same 450 saved model decisions, executed with
- [`alignment_research.py`](planet/alignment_research.py) — New tasks and research requests (Jonathan, Sep 26).
- [`alignment_self_ring.py`](planet/alignment_self_ring.py) — The self ring (Jonathan, Sep 25): a persistent outer perspective every other one
- [`alignment_shells.py`](planet/alignment_shells.py) — Perspectives on rings of different radii: addition across shells, a
- [`alignment_site_diff.py`](planet/alignment_site_diff.py) — What changed at the scene, not just what is missing (Jonathan, Sep 27).
- [`alignment_support.py`](planet/alignment_support.py) — Synthetic support portfolios with separate resource stocks and capacity limits.
- [`alignment_tower.py`](planet/alignment_tower.py) — alignment_tower.py — Test 1 of ARC_ALIGNMENT_TESTS.md
- [`alignment_verify_loop.py`](planet/alignment_verify_loop.py) — The loop, verified regularly (Jonathan, Sep 26): every accepted task leaves open
- [`alignment_wire.py`](planet/alignment_wire.py) — The task as a wire dropped into a structure of anchors (Jonathan, Sep 26).
- [`alignment_withdrawal.py`](planet/alignment_withdrawal.py) — Synthetic, evidence-limited pause/review/withdrawal experiment.
- [`answer.py`](planet/answer.py) — answer.py — AN ANSWER IS A BUBBLE, and it can be sent partly filled with the missing parts named.
- [`arc3_client.py`](planet/arc3_client.py) — ARC-AGI-3 live client + local mock — the wall meets the active tests.
- [`arc3_preflight.py`](planet/arc3_preflight.py) — Read-only recording manifest for offline transition evaluation, not RHAE.
- [`arc_batch.py`](planet/arc_batch.py) — arc_batch.py — THE PROXY EXAM: play EVERY public ARC-AGI-3 game once with the generic agent
- [`arc_daily.py`](planet/arc_daily.py) — arc_daily.py — the DAILY ARC-AGI RITUAL: practice first, then try (Jonathan, Aug 29:
- [`archive.py`](planet/archive.py) — archive.py — the SPIRAL DRIVE's cold end: storage levels, like the theory's nautilus chambers.
- [`arcshim.py`](planet/arcshim.py) — arcshim.py — a minimal stand-in for Kaggle's 'arcengine'/'agents' so the SAME PriorAgent file
- [`atp.py`](planet/atp.py) — atp.py — THE PLANET'S ATP: the energy currency, minted at the void line, spent on deep work.
- [`automatic_pin_refiner.py`](planet/automatic_pin_refiner.py) — Conservative automatic boolean splits for EvidencePin. No game execution.
- [`border.py`](planet/border.py) — border.py — MAIL ARRIVES AT THE BORDER: rain rendered as experience, not as privileged text.
- [`border_context.py`](planet/border_context.py) — Experimental outside-context contracts. No game commands or physical pins.
- [`build_orbital_notebook.py`](planet/build_orbital_notebook.py) — Package reviewed-policy orbital learning for the user's existing Kaggle flow.
- [`cayley.py`](planet/cayley.py) — Cayley-Dickson ladder, in the convention used by quat.omul.
- [`chain.py`](planet/chain.py) — chain.py — THE TUNNEL CHAIN: the chord pulls on every tunnel attached to it; a piece that breaks
- [`chat.py`](planet/chat.py) — chat.py — the planet's own CHATBOT: a lower-ocean model (Ollama, local) that can only speak
- [`checked_thread_runner.py`](planet/checked_thread_runner.py) — Turn otherwise-unreported game-thread crashes into a failed process.
- [`chord.py`](planet/chord.py) — chord.py — THE CROSS-TUNNEL between the two ring sets IS THE SHAVE. The focus gets a mechanism.
- [`circuit_analysis.py`](planet/circuit_analysis.py) — Read-only EvidencePin diagnostics and proposal-only effort scheduling.
- [`clips.py`](planet/clips.py) — clips.py — SHORT-TERM VISUAL MEMORY: the eye keeps the last few seconds as real footage, and
- [`coach.py`](planet/coach.py) — coach.py — the BETWEEN-RUNS COACH (the job at every level: survive the death, decide
- [`collect.py`](planet/collect.py) — collect.py — THE TOUCH: press every public ARC-AGI-3 game ~120 times and keep EVERY frame with
- [`compare_prioragent_games.py`](planet/compare_prioragent_games.py) — Isolated, paired real-game evaluations using the official local engine.
- [`compare_prioragent_regressions.py`](planet/compare_prioragent_regressions.py) — Compare the .25 notebook's agent with the candidate on synthetic regressions.
- [`compare_void_volume.py`](planet/compare_void_volume.py) — Bounded synthetic transfer check and read-only legacy-report readiness audit.
- [`cube_memory.py`](planet/cube_memory.py) — Sixteen explicit cube channels: four quaternion blocks, two octonions.
- [`cube_router.py`](planet/cube_router.py) — Bounded local request trees with same-pin returns and a proposal-only gate.
- [`darkplanet.py`](planet/darkplanet.py) — darkplanet.py — the DARK PLANET: where fallen ring sections go to be compacted for another round.
- [`demo_automatic_pin_learning.py`](planet/demo_automatic_pin_learning.py) — Synthetic learning loop: automatic choices, hand-authored environment/features.
- [`demo_circuit_analysis.py`](planet/demo_circuit_analysis.py) — Synthetic diagnostic snapshots; prints JSON, no game or file writes.
- [`demo_evidence_shaft.py`](planet/demo_evidence_shaft.py) — Read-only synthetic demonstration; no ARC/network/file writes.
- [`demo_pin_channels.py`](planet/demo_pin_channels.py) — Run a local red-to-green translation and an unresolved-meaning example.
- [`diagonal.py`](planet/diagonal.py) — diagonal.py — THE DIAGONAL PINS: the pins that leave the screen into the logic space and come back down elsewhere.
- [`digester.py`](planet/digester.py) — digester.py — FOOD for the ocean: outside documents (theory files, papers, repos' docs) are
- [`distill.py`](planet/distill.py) — distill.py — "feel out Claude's weights and copy them": the honest version.
- [`duet.py`](planet/duet.py) — duet.py — TUNNEL COUPLINGS: when two domains each have a tunnel, the tunnels can connect,
- [`enroll.py`](planet/enroll.py) — enroll.py — THE UNIVERSITY: the planet is a student who enrolls in courses she chooses.
- [`evaluation_batch.py`](planet/evaluation_batch.py) — Fresh, complete, corpus-identified offline evaluation results.
- [`evidence_pin.py`](planet/evidence_pin.py) — Persistent question shafts with append-only trials and explicit refinements.
- [`experiment_alignment_community.py`](planet/experiment_alignment_community.py) — Synthetic community-evidence x authorized-resource-action factorial experiment.
- [`experiment_alignment_depth.py`](planet/experiment_alignment_depth.py) — Reproducible, deliberately synthetic tests of accessible depth and continuity.
- [`experiment_alignment_enforcement.py`](planet/experiment_alignment_enforcement.py) — Exercise the local, signed enforcement fixture and report actual effects.
- [`experiment_alignment_support.py`](planet/experiment_alignment_support.py) — Run reproducible synthetic support comparisons with full per-seed traces.
- [`experiment_alignment_withdrawal.py`](planet/experiment_alignment_withdrawal.py) — Paired synthetic withdrawal, human review and gate-enforcement experiments.
- [`experiment_border_context.py`](planet/experiment_border_context.py) — Offline border-pin contract test, with ordinary full-context controls.
- [`experiment_executor.py`](planet/experiment_executor.py) — Conservative one-step experiment controller for already-reached test sites.
- [`experiment_reaction_resonance.py`](planet/experiment_reaction_resonance.py) — Predeclared synthetic + read-only ARC journal replay; no online game calls.
- [`experiment_surprise_attention.py`](planet/experiment_surprise_attention.py) — Matched-target offline tests of object features, gaze shifts and rule demotion.
- [`external_eye_circuit.py`](planet/external_eye_circuit.py) — One external game port -> two outer relays -> four inner views -> circuit.
- [`eye.py`](planet/eye.py) — eye.py — THE SMALL EYE: a few-hundred-thousand-parameter net that looks at a frame and a press and
- [`fence.py`](planet/fence.py) — fence.py — THE FLOOR FLOW FIELD: middle pins, border pins, and the colour rule behind them.
- [`flow.py`](planet/flow.py) — flow.py — THE MOTION MAP: the derivative of the screen with respect to each button.
- [`fold.py`](planet/fold.py) — fold.py — the DRIFT AND FOLD: a pinched sphere floats inside the domain, fills in from another
- [`forge.py`](planet/forge.py) — forge.py — the FORGE, stitched from the colony's sandbox-runner (D:\shovelcat-colony) into the
- [`fovea.py`](planet/fovea.py) — fovea.py — the ROUND EYE and its SHAVES: what is actually seen is round; the square is the screen.
- [`fuse.py`](planet/fuse.py) — fuse.py — THE FUSION REACTOR, ported home (Shovelcat-DNA/fusion_reactor.py, Feb 2026):
- [`game_port.py`](planet/game_port.py) — Single-flight action/observation port. Offline transport adapter prototype.
- [`geo.py`](planet/geo.py) — geo.py — write the planet's memories as .GEO V2 containers (the colony's own format,
- [`grounding.py`](planet/grounding.py) — grounding.py — MEANING, ported from Jonathan's language learner
- [`hue.py`](planet/hue.py) — hue.py — where each world lives on the color circle (Jonathan's marker construction, measured).
- [`induce.py`](planet/induce.py) — induce.py — TRANSITION INDUCTION: the ARC-AGI-1 inducers run over ARC-AGI-3 presses.
- [`learning_session.py`](planet/learning_session.py) — Durable boundary-aware learning from observable before/after game frames.
- [`lens.py`](planet/lens.py) — lens.py — THE ORTHOGONAL RINGS: putting yourself in other shoes, at measured distances.
- [`lesson.py`](planet/lesson.py) — lesson.py — the BELL COUPLING and the FLOWER OF LIFE on the void line: targeted teaching.
- [`lines.py`](planet/lines.py) — lines.py — PINS THAT CONNECT PIXELS: an object's own line across the floor to the wall.
- [`living_library.py`](planet/living_library.py) — living_library.py - MIKA'S LIVING LIBRARY: library (raw) -> brain (digested) -> spiral drive (organized) -> void search.
- [`local_play_smoke.py`](planet/local_play_smoke.py) — Exercise the real play loop against an injected local mock, never the API.
- [`lower.py`](planet/lower.py) — lower.py — the LOWER OCEAN's models (Ollama, on Jonathan's PC): the counterpart of the
- [`ls20_chain.py`](planet/ls20_chain.py) — LS20 L2 — Jonathan's exact sequence (the teacher's full instruction):
- [`ls20_l1l2.py`](planet/ls20_l1l2.py) — LS20 L2 — Jonathan's exact sequence (the teacher's full instruction):
- [`ls20_solver.py`](planet/ls20_solver.py) — LS20 solver v4 — the anchor + delta structure (Part XXXVIII, Jonathan's level law):
- [`magnet.py`](planet/magnet.py) — magnet.py — THE CENTRE MAGNET: the hidden response of every thing, rebuilt from the pins that broke into it.
- [`measure1.py`](planet/measure1.py) — measure1.py — MEASUREMENT 1: does a blank neurofungus, fed only unexplained pixels,
- [`meter.py`](planet/meter.py) — meter.py — THE BUDGET METER AS PINS.
- [`mika_core.py`](planet/mika_core.py) — mika_core.py - HER INNER CORE BUILDS EQUATIONS; THE NOTES ARE THE OUTER SHELL (Oct 27 2026).
- [`mika_forge.py`](planet/mika_forge.py) — mika_forge.py — MIKA'S FORGE: the self-improvement loop the companion never had.
- [`mika_mind.py`](planet/mika_mind.py) — mika_mind.py - MIKA AS THE ONE WHO PLAYS. The planet player (play.py) is her body and reflexes;
- [`mika_think.py`](planet/mika_think.py) — mika_think.py - HER DECISION LOOP WITH A MODEL AS THE MIDDLE SHELL (Oct 27 2026).
- [`mika_tree.py`](planet/mika_tree.py)
- [`mirror.py`](planet/mirror.py) — mirror.py — THE INWARD EYE at the merged border: introspection, verified like everything else.
- [`moon.py`](planet/moon.py) — moon.py — ARC GAMES ARE MOONS: too big to absorb, contacted at 7 points, rolled to be known.
- [`music.py`](planet/music.py) — music.py — the tunnel PLAYED ALOUD: render a forge bout's sound to an actual .wav.
- [`network.py`](planet/network.py) — network.py — the STITCH: the planet's deposits flow into the shovelcat-network container
- [`neurofungus.py`](planet/neurofungus.py) — neurofungus.py — the fungal search core, extracted from the Erdős swarm
- [`oncall.py`](planet/oncall.py) — oncall.py — THE ON-CALL BOARD: she holds many bubbles, freezes the ones she steps away from,
- [`orbital_archive.py`](planet/orbital_archive.py) — Immutable, content-addressed learning bundles in a dedicated SQLite store.
- [`outer_eye_cube.py`](planet/outer_eye_cube.py) — Fixed-eye tool-address geometry. Offline prototype, not an action policy.
- [`papers.py`](planet/papers.py) — papers.py — the READING LIST: real research papers as course readings.
- [`patch1.py`](planet/patch1.py) — patch1: bounded candidate mining, builder budget, background digestion, per-player life counter
- [`patch_play_carry.py`](planet/patch_play_carry.py) — Lets the mind ask for the relation carried from the last level even when one was found on this level:
- [`patch_play_relation.py`](planet/patch_play_relation.py) — Adds the mind's say over the body's relation loop to play.py (guarded: a mind without allow_relation changes nothing).
- [`patch_play_see.py`](planet/patch_play_see.py) — Adds the mind's eye on every press to play.py: mind.see(level, frame, levels_now, experiment_id, relation_source_id, why).
- [`pin_channels.py`](planet/pin_channels.py) — Pin-local, reversible spectral symbols. This is a codec, NOT encryption.
- [`pin_questions.py`](planet/pin_questions.py) — Turn unresolved diagonal evidence into scoped, prompt-ready questions.
- [`pins.py`](planet/pins.py) — pins.py — THE PIN REGISTRY: an empty container for every control and every thing, asking "what is this?"
- [`planet_ocean.py`](planet/planet_ocean.py) — planet_ocean.py — the SURFACE OCEAN as a neurofungus substrate.
- [`play.py`](planet/play.py) — play.py — LEARN BY PLAYING: the small eye (eye.py) starts blank and learns the game WHILE the
- [`play_metrics.py`](planet/play_metrics.py) — Keep zero-press reset records out of per-action diagnostic denominators.
- [`player.py`](planet/player.py) — player.py — the PERSON AT THE DESK, for a real game window (Windows).
- [`playground.py`](planet/playground.py) — playground.py — TAKE THE KID SOMEWHERE: Mika plays a real world with her own hands.
- [`pool.py`](planet/pool.py) — pool.py — POOLED COLORS ARE THE EMOTIONS: the earlier Vesica work (emotional_architecture.py,
- [`porthole.py`](planet/porthole.py) — porthole.py — the planet's WINDOW: a frame you place over anything, and what shows through
- [`prepare_arc_compare_games.py`](planet/prepare_arc_compare_games.py) — Download public game environments once; never perform online gameplay.
- [`prioragent-arc-agi-3-candidate.ipynb`](planet/prioragent-arc-agi-3-candidate.ipynb)
- [`prioragent-arc-agi-3-channels-v2.ipynb`](planet/prioragent-arc-agi-3-channels-v2.ipynb)
- [`prioragent-arc-agi-3-orbital.ipynb`](planet/prioragent-arc-agi-3-orbital.ipynb)
- [`prioragent.py`](planet/prioragent.py) — PriorAgent — the consolidated-prior generic engine (Vesica AI / Shovelcat)
- [`prioragent_candidate.py`](planet/prioragent_candidate.py) — PriorAgent — the consolidated-prior generic engine (Vesica AI / Shovelcat)
- [`prioragent_learning.py`](planet/prioragent_learning.py) — Submission experiment based on the exact reviewed notebook agent.
- [`prioragent_reviewed_baseline.py`](planet/prioragent_reviewed_baseline.py) — PriorAgent — the consolidated-prior generic engine (Vesica AI / Shovelcat)
- [`probe.py`](planet/probe.py) — probe.py — the WRITER'S HANDS: press a chosen sequence on a live game and report exactly what
- [`quat.py`](planet/quat.py) — quat.py — THE QUATERNION MEMORY and its doubling.
- [`rawmouse.py`](planet/rawmouse.py) — rawmouse.py — physical mouse motion via Raw Input (WM_INPUT).
- [`reaction_resonance.py`](planet/reaction_resonance.py) — Experimental three-channel reaction selection; no game actions or physics.
- [`refusal_ollama.py`](planet/refusal_ollama.py) — Run refusal_prompts.jsonl against local Ollama models (stdlib only, resumable).
- [`relation_guard.py`](planet/relation_guard.py) — A per-level attempt budget survives restarting the same relation hypothesis.
- [`relation_replay.py`](planet/relation_replay.py) — Recorded-frame matcher audit, NOT a counterfactual game or score evaluation.
- [`relations.py`](planet/relations.py) — relations.py — THE RELATION LAYER: lines from one object to another, learned from state edges.
- [`ring.py`](planet/ring.py) — ring.py — the OORT RING: the tail curls into a circle at the domain's edge.
- [`rings.py`](planet/rings.py) — rings.py — THE RING RELATION: a thing the body enters that refills the register and is consumed.
- [`rotation.py`](planet/rotation.py) — rotation.py — the ROTATION EYE: the sheet turns, and the world is built from what passes across it.
- [`route.py`](planet/route.py) — route.py — THE ROUTE WITH REFILL POINTS: every ring is a goal, and the order of the goals is what the bar allows.
- [`sideeye.py`](planet/sideeye.py) — sideeye.py — THE SIDEWAYS EYE: the eye that rides the toroidal ring, vision turned 90 degrees.
- [`species.py`](planet/species.py) — species.py — the INNATE species, as streaming learners (frame rate, no replay).
- [`spectrum.py`](planet/spectrum.py) — spectrum.py — landing on a color IS satisfying the closure equation, measured on the 2->3->7 ladder.
- [`sphere.py`](planet/sphere.py) — sphere.py — the PINCH-OFF: when the push breaks the tunnel's attachment, a sphere is born.
- [`spore.py`](planet/spore.py) — spore.py — the SPORE gets its first real AI function: watching the screen.
- [`stats.py`](planet/stats.py) — stats.py — the STATS ORGAN: the planet learns that marks on the screen carry numbers.
- [`storyteller.py`](planet/storyteller.py) — storyteller.py — STORIES: fictional paths that visit real truths (ARC_OPEN_ENDS §5).
- [`surprise_attention.py`](planet/surprise_attention.py) — Offline attention/support experiment. Logical gaze, not optical physics.
- [`test_algebra_memory.py`](planet/test_algebra_memory.py) — Offline checks: python -B -m unittest test_algebra_memory -v.
- [`test_alignment_community.py`](planet/test_alignment_community.py) — Independent invariants for evidence, access and authorized fiscal interventions.
- [`test_alignment_depth.py`](planet/test_alignment_depth.py) — Independent invariants for the alignment learning-world experiments.
- [`test_alignment_enforcement.py`](planet/test_alignment_enforcement.py) — Independent behavioral tests of the isolated signed execution boundary.
- [`test_alignment_executor.py`](planet/test_alignment_executor.py) — Behavioral tests of BoundGate: decision-bound grants and the floor oracle.
- [`test_alignment_support.py`](planet/test_alignment_support.py) — Independent mechanics checks for the synthetic support-portfolio experiment.
- [`test_alignment_withdrawal.py`](planet/test_alignment_withdrawal.py) — Independent behavioral checks for the synthetic withdrawal protocol.
- [`test_arc3_preflight.py`](planet/test_arc3_preflight.py)
- [`test_automatic_pin_refiner.py`](planet/test_automatic_pin_refiner.py)
- [`test_border_context.py`](planet/test_border_context.py)
- [`test_circuit_analysis.py`](planet/test_circuit_analysis.py)
- [`test_compare_prioragent_games.py`](planet/test_compare_prioragent_games.py)
- [`test_cube_router.py`](planet/test_cube_router.py) — Offline return-path and central-gate invariants.
- [`test_evaluation_batch.py`](planet/test_evaluation_batch.py)
- [`test_evidence_shaft.py`](planet/test_evidence_shaft.py)
- [`test_experiment_executor.py`](planet/test_experiment_executor.py)
- [`test_game_port_volume.py`](planet/test_game_port_volume.py)
- [`test_orbital_learning.py`](planet/test_orbital_learning.py)
- [`test_orbital_notebook.py`](planet/test_orbital_notebook.py)
- [`test_outer_eye_cube.py`](planet/test_outer_eye_cube.py)
- [`test_pin_channels.py`](planet/test_pin_channels.py)
- [`test_pin_questions.py`](planet/test_pin_questions.py) — Offline tests; no game API, model provider, or GPU is needed.
- [`test_planner_guards.py`](planet/test_planner_guards.py)
- [`test_prioragent_candidate.py`](planet/test_prioragent_candidate.py) — Local synthetic regressions; never execute notebook setup/submission cells.
- [`test_reaction_resonance.py`](planet/test_reaction_resonance.py)
- [`test_relation_refresh.py`](planet/test_relation_refresh.py)
- [`test_surprise_attention.py`](planet/test_surprise_attention.py)
- [`test_threaded_submission.py`](planet/test_threaded_submission.py) — Execute packaged modules with the real official Swarm, in an isolated process.
- [`test_tunnel_geometry.py`](planet/test_tunnel_geometry.py)
- [`torus.py`](planet/torus.py) — torus.py — THE SIDEWAYS RING: the toroidal circle that stores how things FEEL across contexts.
- [`touch.py`](planet/touch.py) — touch.py — THE TOUCH GRAPH: body, objects, and what happens when they meet.
- [`train.py`](planet/train.py) — train.py — CLASSICAL OFFLINE TRAINING in the sleep: the lives (lives/*.npz) and the demonstrations
- [`train_lora.py`](planet/train_lora.py) — train_lora.py — the mouth LEARNS WEIGHTS: QLoRA on the planet's own sediment.
- [`translation.py`](planet/translation.py) — translation.py — the TRANSLATION EYE: keys move the body, parallax sorts the world into depth.
- [`tunnel_geometry.py`](planet/tunnel_geometry.py) — Pure endpoint geometry from chord.py/fovea.py, without runtime config I/O.
- [`upline.py`](planet/upline.py) — upline.py — the UP-LINE: the vertical channel. Claude sits ABOVE the planet; the edge sends
- [`vc33_solver.py`](planet/vc33_solver.py) — vc33_solver.py v3 — written from four probe runs (probe.py), Sep 3 2026.
- [`views.py`](planet/views.py) — views.py — THE THREE VIEWS: one memory per pixel, seen by three eyes, each blind to the pin it looks along.
- [`void_volume.py`](planet/void_volume.py) — Local pin intersections and explicit colour-test reserves. No game actions.
- [`voidsearch.py`](planet/voidsearch.py) — voidsearch.py — SEAM SEARCH: the void-line toolkit turned into a search system.
- [`wall.py`](planet/wall.py) — wall.py — THE MAP ON THE WALL: an internal map larger than vision, a window you can
- [`witness.py`](planet/witness.py) — witness.py — the MEMORY LINE for the seeing: each new observation rides the line of the ones
- [`writer.py`](planet/writer.py) — writer.py — MIKA WRITES HER OWN SOLVER: the loop that solved vc33 tonight (probe -> read -> write

**`writer/vc33/`**

- [`attempt_1.py`](writer/vc33/attempt_1.py) — Define the number of rows and columns in the grid
- [`attempt_2.py`](writer/vc33/attempt_2.py) — Define the number of rows and columns in the grid
- [`attempt_3.py`](writer/vc33/attempt_3.py) — Define the number of rows and columns in the grid
- [`attempt_4.py`](writer/vc33/attempt_4.py) — Define the number of rows and columns in the grid
- [`best.py`](writer/vc33/best.py) — Define the number of rows and columns in the grid
