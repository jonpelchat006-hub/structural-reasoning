# Measurement 1 — the neurofungus digs the surface ocean (first result of the planet)

*Session Aug 26 2026. The Erdős swarm's fungal core (`f_3_n_search_swarm.py`) was extracted into a
domain-agnostic module, `neurofungus.py`, and pointed at the ARC-3 frames through one substrate,
`planet_ocean.py`: the food is unexplained pixels. Replays re-recorded live today (`replays/`).
Everything below is a runnable number from `measure1.py`. Companion to `ARC_PLANET.md`.*

## What was built
- **`neurofungus.py`** — BranchTree tendrils (UCB + phantom smell + depth bonus + path authenticity),
  power stations (never evicted; radiate), spores + smell (proximity × novelty), anastomosis
  (fuse a spore with a tendril), promise flowing up. Everything Erdős-specific is behind a
  `Substrate` interface: `score / spine / candidates / realize / sow / fuse`. One flag added:
  `inherit_exhausted` (a failed dig stays failed down the tendril — the negative-confirmation memory
  of `failure_learning.py`; off = the swarm's original behaviour).
- **`planet_ocean.py`** — the surface is a 64×64 frame cut into 8×8 regions; a dig `(region, level)`
  installs one predictor of that region's next tile. Five species, learned ONLINE (prequential:
  frame t+1 is predicted only from frames ≤ t, so memorising earns nothing; only recurring structure
  is food):
  L1–L3 memory (action/tile → next tile, widening keys), **4 = MOVER** (per action a learned
  displacement + the mobile object — the hand), **5 = COUNTER** (per action/colour a learned
  pixel-count delta taken from a learned end of a run — the register). Score = pixels explained
  over the flat surface. Nothing in it knows what a key, a ring, a bar or a level is.

## The numbers (two LS20 replays, 131 frames, flat-surface error E0 = 11,481 px)
| run | explained | digs |
|---|---|---|
| **FUNGUS** (1500 iters, 62 nodes, 9 stations, 6 anastomoses) | **46.9%** | **58** |
| UNIFORM control — every level under every region | 38.3% | 320 |
| RANDOM control — same 58 digs placed at random, best of 20 (mean 10.8%) | 18.0% | 58 |
| SHUFFLED control — frames in random order (no dynamics to learn) | 16.3% | 177 |

The fungus explains MORE than digging everything everywhere, with 5.5× fewer digs — because a
memory dig where memory does not fit overrides a good species with a bad prediction; selective
growth is not a cost saving, it is the accuracy. Random placement of the same budget gets a third
of it; with the dynamics destroyed the fungus starves to the shuffled floor.

## Where it dug (no game knowledge)
- **The MOVER species (4) was dug along the agent's actual routes** — the corridor regions of the
  green maze — and nowhere in the yellow walls. The hand was found by its own footprint.
- **The COUNTER species (5) was dug along the fuel bar** (bottom row of regions) once the tree
  stopped re-trying failed memory digs (`inherit_exhausted`).
- Oracle spots (what the hand-written solvers used): keyhole region 78.5% explained (uniform 68.4%),
  ring nook 51.3%, ring end 35.0%, bar 38.6%, agent spawn 31.2%; the goal box 13.3% (its region is
  dominated by the level relayout).
- **Never dug and 0% explained: the HUD key glyph.** The glyph's rotation on keyhole entry is the
  one recurring mechanic no species can predict — exactly the rule Jonathan supplied ("the batch of
  pixels rotates it"). The fungus's blind spot is the teacher's first hint.

## The lightning list — the residual points at the mechanics that needed a teacher
Biggest unexplained single steps of the dug state: the two **level transitions** (steps 12 and
59/60, whole-screen relayouts). Excluding whole-screen changes, the next largest are, in order:
the probe's **respawn** (replay 1 step 46: 162 px; step 68: 135 px), **refill 2** at (17,16)
(replay 0 step 54: 84 px — the bar jumps 56→84 and the ring vanishes), **refill 1** at the nook
(step 32: 81 px), and the **first move on the new level** (step 13, both replays). Every one of these
is a mechanic the LS20 campaign learned by dying or by a hint (pips = lives; rings = refill stations;
respawn resets the key). The residual is not noise — it is the list of things the outside had to
supply. That is what a bolt should land on.

## Honest bounds
- Two replays of one game, 131 frames; 46.9% is not "solved perception" — it is the measurable fact
  that surprise-directed growth with innate species finds the game's moving parts and its registers
  unaided, and that its residual is the mechanics list.
- The species are hand-built innate laws (a mover, a counter), not learned weights: this is the
  inner shell digging, not yet a middle shell learning. The tendril tree is a search over WHICH
  columns to deepen; the next step is columns whose predictors have trainable parameters so the
  middle shell exists. The relayout events also expose a gap: nothing yet says "a level ended".
- The old "1315-px room relayout" did not reproduce on today's recordings (50 px on the same
  ring); it was most likely a diff across the level transition — a second perception loss that
  was a stale comparison frame, which the fast loop makes impossible by construction.

## Files
`AI Detector/planet/`: `neurofungus.py`, `planet_ocean.py`, `measure1.py`, `measure1_result.npz`,
`measure1.log`; replays in `AI Detector/replays/` (`record_L1L2.py` re-records them).
Next: measurement 2 (core transfer — L1+L2 → does L3 start shallower) needs L3 re-solved live
first; measurement 3 (lightning log) is the list above, live.
