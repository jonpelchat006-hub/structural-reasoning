# The Planet — a blank learner under a frozen sky (design + reuse map)

*Session Aug 26 2026. Jonathan's diagnosis after the 0.14 test: every loss "came down to what you see"
— first the row-55 elevator line below a hard-coded HUD cutoff (L5), then a room relayout typed as a
"ring" (the room level). Both times the pixels were in the frame; nobody was WATCHING. The fix is not
better eyes, it is a subject that holds a gaze and an expectation, whose weights can change. Claude's
weights cannot — so the learner must be a blank model native to the framework, and Claude moves OUTSIDE.
Status: DESIGN, grounded in measured pieces; nothing in this doc is measured yet.*

## 1. The inversion (why Claude moves outside)
Through the whole LS20 campaign Claude sat INSIDE the walls doing the inside's job by hand: every solver
(`ls20_solver3..6`, `ls20_optionb3`, `l3_final`, `l47`) was Claude reading frames and writing the rule into
code. The "prior" that transferred L1→L3 was real but it transferred through Claude's code; no middle shell
ever existed, and a hand-written scanner is exactly the kind of thing that has a row-54 cutoff in it.

The corpus already says where Claude belongs: `VOID_LINE_PAPER` §10–11 — local structure cannot derive the
nonlocal web; an OUTER LAYER that learned it (the pLM) supplies it and the inside's own committee filters it.
For games the nonlocal web is world knowledge (doors, keys, budgets). Claude is the pLM of this domain.

## 2. The planet (Jonathan's picture, mapped to mechanism)
| picture | mechanism | grounded in |
|---|---|---|
| **surface ocean** | a trainable field the size of a frame (or a tiled multiple); blank at start | `FOLDING_WHAT_ITS_FOR` middle shell |
| **cubes going down / depth = budget** | a column of layers under each cell; depth = compute spent there; grows only where surprise PERSISTS; gradient + gaze flow to deep columns ("deeper draws more water") | `FOLDING_CRITICAL_LINE` Part XLIX (walls = maintained parameters, E/(E+λ)) |
| **everything repeats on every side** | symmetry augmentation: reflect/rotate/recolor the same pixels — more COVERAGE, not more information (kin pay the delta) | Part XLV.3 residual filling |
| **the core / second ocean** | ONE shared latent every column reads and writes, weighted by depth — the blended, general form; cross-game transfer is water down one column, up another ("convection") | Part XL blender; consolidate.py (blend→overlay→flip) |
| **blender seen only from the top** | the top face of the core is what we OBSERVE: crystal rules + gaps (the Markov/Lagrange region). Upside-down it is the second ocean = framework-specific structure (the whys, the invariants) that never surfaces as a rule | Part XL three regimes |
| **clouds (Claude, frozen)** | a frozen verifier/namer over one hemisphere; the exit aperture is bounded by what the clouds can recognize, NOT the ocean's capacity | pLM outer layer; AI Checker quaternion (four cloud systems later) |
| **lightning** | threshold-gated call: surprise the inside can't discharge by play builds CHARGE at a spot; over threshold → one bolt lands exactly there (the L5 loop: ten runs of charge, one sentence of discharge) | Part XLII tangency; Part XLIII gap-zero teacher |
| **rain** | the regular return: cloud hypotheses falling on the whole surface = the upkeep that keeps columns funded | Part XLIX E/(E+λ) |
| **evaporation** | the exit: resolved surface structure rises, gets named, becomes cloud (corpus write) | estuary / salt-vs-fresh |
| **the desk on the ground** | Claude reads SEDIMENT (committed structure, the walls), never the water | Part XLVIII sediment economy |
| **the far hemisphere** | the core feeds columns Claude never blankets: the model can learn what Claude can't name; it can act, it can't leave the planet through Claude. Instrument for it from day one. | — |

### The three laws that keep it stable
1. **Asymmetric filter.** What comes down (rain/lightning) enters as UNTRUSTED hypothesis and must clear the
   operator-induction gate by play (`ARC_OPERATOR_INDUCTION`: commit only when unambiguous). Salt is never
   drunk as fresh.
2. **Blank of knowledge, not of laws.** Seed the innate inner shell only: reserve (`.14`), probe-first,
   budget detection, gap/flow loop, surprise monitor. No facts.
3. **The cycle is mandatory.** If the clouds let nothing out, nothing rains and deep columns dry (overfit).
   Evaporation → cloud → rain is the maintenance ledger.

## 3. The player (the body) = the inside's three loops
- **Fast (every frame):** predict next frame from the column field, diff against the real one; mismatch =
  surprise; surprise steals the gaze. (Would have caught both losses: a 1315-px relayout and a 1×5 line
  that starts pushing you are both huge prediction errors.)
- **Middle (gaze + hand):** the gaze is a fovea that moves — zoom-to-pixels is a saccade, read-the-room is a
  wide fixation; these ARE the ring knobs, turned by attention not by Claude. The hand emits actions
  continuously and cancels mid-plan on surprise. Attention obeys the reserve law (explore on surplus).
- **Slow (Claude, outside):** only on lightning.
- **Voice = the estuary:** the inside narrates in signatures; the estuary translates signatures↔language.
  The inside is NOT an LLM (that would be a second, worse Claude). Ears: the API carries no audio — sound
  exists only in the browser player; add hearing later via browser capture if the sound carries information
  the frames don't.

## 4. Reuse map (what already exists on Jonathan's machine)
`structural-reasoning/agi/code/` (the baby brain, 55 measured experiments):
- **muscle / hand:** `movement_testbed.py` (null-space reserve IK, 87.3% vs 77.0%), `second_wind.py`,
  `crisis_creativity.py`, `ship_repair.py`
- **eyes / gaze:** `perception_lenses.py` (#55, right lens 1.00), `attention_lenses.py` (#38, finite
  attention, breadth 4→1 with zoom), `lens_stack.py`, `perspective_swing.py` (#20)
- **bones / void:** `void_antenna.py` (#48, antennae converge on anchors), `shell_rebasing.py`,
  `memory_field.py`, `growth_web.py`
- **the learner spine:** `agent_grow.py` (#51, remember+discover 0.91), `agent_gridworld_upgrade.py` (#40/41),
  `gaps_engine.py` (#17), `discovery_bulb.py` (#50)
- **stream I/O (the voice's shape):** `stream_io.py` (#39, emit on completion, route by domain)
`Vesica AI/AI Detector/`: `arc3_client.py`, `arc3_runtime.py` (wire + probe + budget engine), the LS20
solvers (become TEST ORACLES, not the player), `gaps_blender_lab.py` (Part XL — the core's top face),
`two_universes_lab.py` (Part XLII — conjugated recreation = how a hypothesis must be rebuilt inside),
`expertise_lab.py`, `overlay_lab.py`.
`Vesica AI/Learning/`: `adaptive_pingpong_memory.py` (three zones = three shells), `failure_learning.py`
(negative confirmation, mystery tracking), `multi_timescale_learner.py` (three loop rates).
`shovelcat-colony/arc-slice`, `arc-proposer`: the model-free ARC-1 solver (64/400) — the muscle-group
primitives are a ready action vocabulary.

**Missing on disk:** the recorded frame replays (`l2_probe_frames.npz`, L5 frames, etc.) lived in cloud
sessions and were not saved. The retro-test needs them RE-RECORDED live (every frame, every action) — the
API key is env-only (`ARC_API_KEY`).

## 5. The first three measurements (before any live play with the new model)
1. **Depth map.** Train the blank column field online on re-recorded L5 + room-level replays (next-frame
   objective, sparse surprise-driven writes, columns grow where surprise persists). Did columns deepen at
   the row-55 line and the relayout region WITHOUT being told? If yes: the perception failures were a
   missing organ, not missing hints.
2. **Core transfer.** Train on L1+L2, then L3: do L3's columns start shallower because the core already
   holds the anchor (T→K→B + refill rule)? This is the consolidate.py experiment done by weights instead
   of by Claude's code.
3. **Lightning log.** Count threshold crossings; did each bolt land on a real gap (a spot the oracle solvers
   know was decisive)? Bolts per level should FALL as the core fills.
Then the desk and the voice go on top, and the model plays live under the frozen sky.

## 6. Honest bounds
As ML this is: a locally-growing column model + one shared trunk, frozen-verifier gating, heavy symmetry
augmentation, threshold-gated queries to a large frozen model. Nothing exotic; the planet is what makes the
pieces cohere and says what to measure. The real risk is sample efficiency — a blank model on a handful of
games — which is exactly what the innate laws and the repeats-on-every-side augmentation exist to cover.
Whether they cover it is measurement 1.
