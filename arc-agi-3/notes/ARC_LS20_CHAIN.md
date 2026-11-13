# ARC_LS20_CHAIN — the live 5/7 chain, rebuilt (Sep 2, 2026)

**Status: `ls20_chain.py` completes L1–L5 live in 217 actions** (L1 13, L2 60, L3 107, L4 157, L5 217; scorecard level_actions [13, 47, 47, 50, 60]). It is the file `arc_daily.run_live` prefers, so the daily ritual plays it. This doc exists because the L3–L5 scripts were lost once with a container; everything needed to rebuild is here.

Files (planet dir on the PC, `C:\Users\GamerTech\Desktop\Vesica AI\AI Detector\planet\`): `ls20_chain.py` (the chain), `ls20_l1l2.py`, `ls20_solver.py` (older heads), `ls20_L3_start.npy`/`L4`/`L5` (level start frames saved by the chain), `ls20_l1l2_frames.npz` (every frame of the last run, saved on any exit via atexit), `arc3_trans.jsonl` (effects, laid on the torus).

## Universal rules (verified live)
- Agent = 5×5 block: top two rows color 12, bottom three rows color 9. `agent_pos` = the 2×5 bar of 12 (the old "blob containing a 12" rule was fooled by color stations that contain a stray 12). Moves on a 5-px lattice; snap features to the agent's parity before pathing.
- HUD key glyph: `f[54:64, 0:14]`, glyph color = most common color excluding {3,4,5,11,0}. **8 is a real key/goal color** (L5) — never exclude it. Goal box = color-5 blob (mask out the left HUD panel cols 0–3 and rows ≥52 cols <12; boxes can straddle row 52), inner glyph color same rule. `k = match_rot(hud_glyph, goal_glyph)`; `None` = shapes differ (needs a stamp).
- Keyhole = 0/1 blob that contains a 0. Fan strips are pure color-1 blobs (no 0). Color stations are 3×3 patches (e.g. `9EE/908/CC8`) — they also contain a 0, so exclude all 0-blobs from BFS except the target.
- Rings (color 11, ≤30 px) refill the bar to 84, once per life. Bar = count of 11 in rows 56+. Pips (8, bottom right) = lives. Death (bar 0) respawns at the level start with key reset.
- **Fan cell** = the 5×5 lattice cell on the open side of a color-1 strip. Entering it is a RIDE: one press, carried in the strip's direction to the far wall, **straight through other fan cells**. Rides cost one press of fuel. BFS must never path through a fan cell.
- Fuel: 4 px/press in L1–L3 and L5; **2 px/press in L4**. Blocked presses cost fuel in L4 (killed a life), are free in L5.
- Level detection: `levels_completed` from the frame; print `>>> LEVEL n COMPLETE at action m` (arc_daily parses it).

## L1 (13 actions) and L2 (60)
As documented in ARC3_LIVE_PLAN: L1 anchor (keyhole then box from above, push up). L2 = Jonathan's sequence: one down-entry at keyhole (47,51) → refill at the nook ring (52,41) while low → two more down-entries (k 2→3→0) → refill at (17,16) → box (42,16) from above, push down.

## L3 (47 actions, actions 61–107)
Map: spawn (47,11) at the foot of the west corridor x=11; fan at the corridor top → **(12,11) ACTION1 rides east along row 7 to (7,36)**. Rings (32,21) and (17,36). Color batch (47,31) in the lower room (x=31 column joins the rooms). Key color 12, goal 9, k=2 → two down-entries at keyhole (12,51) from (7,51). Box (52,56) below the fan shaft: from inside the keyhole go east (12,56), ACTION1 into the fan cell (7,56) → dropped to (47,56) → ACTION2 inserts.
Route: wind → ring1 (32,21) → (32,31),(42,31) → push S into the batch (key 12→9, agent lands on it) → (32,31),(17,31) → ring2 (17,36) → (27,36),(27,56),(17,56),(17,46),(7,46),(7,51) (never step on (7,56)) → entries → (12,56) → drop → push down.

## L4 (50 actions, 108–157)
Start (7,56), key 14, goal 9, shapes differ. Fan cells: (22,36)E, (22,46)S, (27,41)N, (27,46)W, (37,11)E, (37,21)S, (42,26)W, (42,46)E. Rings (17,21), (52,36) (the latter is walled off from the east half — unused).
Route: (7,41),(22,41) → ACTION4 into (22,46) rides S to (47,46) → (47,56),(32,56),(32,46) → ACTION1 into (27,46) rides W to the shelf (27,36) → station (32,36) below it: ACTION2 onto it cycles the color 14→8→12→9 (three touches, ACTION1 back up between) → ACTION4 into (27,41) rides N to (7,41) → ring (17,21) → (22,16),(37,16) → ACTION3 into (37,11) rides E to (37,26) → ACTION1 into the stamp pocket (32,26): one entry sets shape, k=0 → ACTION2 down, ACTION2 into (42,26) rides W to (42,11) → (42,16),(37,16),(22,16),(17,21),(7,26),(7,21) → ACTION3 twice inserts into the box's east face (7,11).

## L5 (60 actions, 158–217)
Start (42,51), key 12, goal 8 (shape differs). Fan cells: (7,36)S, (22,36)E, (27,21)W, (27,41)N, (32,51)S, (32,56)W, (42,46)E, (52,56)N = the elevator. Rings (7,46), (12,11), (47,16). Static keyhole (12,21) = SHAPE STAMP (each entry advances a cycle of shapes; from this start the goal shape came on the 2nd entry, at k=2). Color station (27,31) on the shelf (27,36), reached only by the ride S off (7,36); leave by the ride N off (27,41). Pendulum patch on row 37 (x 16↔26, one step per agent MOVE; frozen by blocked presses/ACTION5) is a **patrolling keyhole: landing on the same cell as it (overlap) = +1 rotation**; crossing the lane at x=11 and waiting beside it do nothing. Elevator: ACTION4 from (52,51) into (52,56) rides N up the chimney to (12,56); ACTION1 inserts.
Route: (37,56) → ACTION1 into (32,56) rides W to (32,46) → (22,46),(17,41),(7,41) → color cycles ×3 (ride S, ACTION3 touch, ACTION4 back, ride N; ring (7,46) when bar ≤20) → (17,41),(17,21) → stamp entries from below until k is not None (ring (12,11) via (12,16) when low) → (22,21) → ACTION2 into (27,21) rides W to (27,11) → (32,11),(37,11),(42,11) → ring (47,16) → (42,16) → planner: land on the patch until k=0 (parity: from a given state only overlaps or only swaps are reachable — the planner (`lane_plan`) searches rows 32/37/42/47) → ACTION2 exit south → (52,21),(52,51) → elevator → ACTION1.

## L6 recon (frame saved as `L6_start.npy`)
Start (52,26), key 14, goal 8 at box (37,56) — the current shape already matches at k=2. Second box (52,56) wants a 9-shape. Rings (7,11), (7,41), (47,11). Zeros: stamp (12,16), station (32,26), patrolling keyhole (42,36). Fans (7,51)S?, (22,51). Two pusher lines (rows 50–54 cols 24–28 `CCCCC/99999`, and the block at rows 5–14 cols 49–58). Not attempted yet.

## Lessons
The 5/7 lineage sat one folder above the planet, unwired, for weeks while the daily sent a random walker. The fix was procedural, not clever: the best known player of a game plays that game, and every level's start frame + every run's frames are saved so a lost script can be rebuilt from the map in one sitting. Probing runs are cheap (one scorecard, ~2 minutes); the expensive thing is guessing mechanics from memory.
