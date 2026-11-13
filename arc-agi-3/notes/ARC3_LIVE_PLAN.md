# ARC-AGI-3 live plan — connecting the wall to the active tests

*Session Aug 2026. Jonathan: "could we try with the arc agi 3 test? i want to use the active
tests but we can also work up to that." Status: the road is open — one item needed from him.*

## What ARC-AGI-3 is (why it is OUR domain)
The interactive benchmark: no instructions, game worlds served over an API; the agent perceives
64×64 frames (colors 0–15), acts (RESET, ACTION1–5 simple, ACTION6 = click at x,y, ACTION7 =
undo), and must discover the rules by playing. This is exactly the game-loop stack the corpus
already measured on synthetic MicroGames: probe-first (6%→98%), operator-induction by
interaction (100%, 0 false rules), ψ/φ two-plane runtime (0%→95.3% vs memoryless), no-undo
fix-forward, surprise monitor. Every prior doc honestly flagged "not the real ARC-3 environment
(not loaded)" — this closes that.

## What we verified today
- **Network path is OPEN from this session**: `three.arcprize.org/api/games` answers (401 =
  needs key, not blocked). We can play the ACTIVE tests live from here.
- **Protocol captured** (docs.arcprize.org): X-API-Key header; GET /api/games; POST
  /api/scorecard/open → card_id; POST /api/cmd/RESET {game_id, card_id} → frame+guid; POST
  /api/cmd/ACTION1..6 {game_id, guid[, x, y]}; scorecard/close. Known games: ls20, ft09, ...
  (s5i5 that Jonathan played by hand is this same catalog).
- **Client built and loop tested** (`arc3_client.py`): live client + a local MOCK serving the
  identical wire format (64×64, key→door world) + the v0 agent skeleton (probe phase → live-
  action set = the affordance router; evidence store of before/after diffs = the induction
  feed; never ACTION7 — the no-undo law). Mock baseline: **0/10 wins random policy** — the
  bar the runtime has to clear, on the wire.

## The one thing needed
**An API key**: register free at **arcprize.org/platform** (Google or GitHub login) → profile →
API Keys → generate. Then `ARC_API_KEY=... python arc3_client.py --list` and we are live.
Registered keys also get the full game list at launch and tracked scorecards.

## The build order (work-up while waiting / after key)
1. **Perception = the wall.** Each frame IS a 64×64 pixelated wall (small-integer rational
   structure — the part every window sees, Part XXXIII). Imprint frame on the boundary; the
   2D wall-net's levels get resolution-matched views free (Poisson). Segment by re-based void
   borders (ARC_RECURSIVE_VOID), meter routing (Part IX).
2. **Induction on live frames.** The before/after evidence store already in the client feeds
   the operator-induction gate (ARC_OPERATOR_INDUCTION: commit only when unambiguous, abstain
   otherwise) — now on frames the agent makes by acting.
3. **The runtime.** ψ DAG + φ collapse + staged arms + drones/re-collapse (ARC_GAME_LOOP),
   probe-first budget, reserve-gated exploration (Jonathan's own play laws, ARC_INTERACTIVE_PLAY).
4. **Scorecard runs** on the active games, honest per-game action counts vs the random baseline.

## FIRST LIVE CONTACT (same session, key received)
- `--list` returned **25 active games** (bp35, m0r0, tn36, sp80, ls20, ft09, sk48, wa30, r11l,
  sc25, tr87, lf52, vc33, sb26, cd82, dc22, re86, ar25, g50t, lp85, su15, ka59, **s5i5**, cn04, tu93).
- Protocol corrections found by playing: commands also require `card_id`; the server uses
  cookie session affinity (client now keeps a cookie jar); final frames may omit `score`.
- **Full live run on LS20** (scorecard f8ca7698…, closed): probe found live actions =
  ACTION1–4 (the affordance router working on real data); random-walk v0 hit GAME_OVER at
  **131 actions, 0/7 levels** — the honest baseline. The scorecard reveals per-level human
  baselines: [22, 123, 73, 84, 96, 192, 186] actions for LS20's 7 levels.
- **Frames rendered** (`ls20_frames.png`, `arc3_run_ls20.npz`): a green region-maze on yellow,
  a dark-red block our actions push around, a framed target glyph, and a **depleting bar along
  the bottom** — an action budget; the game-over came from spending it. The frame IS a
  64×64 pixelated wall with ~9 colors — low-q rational structure end to end.
- Next build: segmentation (re-based void borders) + object/agent identification on these
  live frames → operator induction from the evidence store → ψ/φ runtime → beat 22 actions
  on LS20 level 1.

## BUDGET LAB (live LS20, budget_lab.py, budget_shave.png)
Jonathan: budgets are unworked; movement here, time or other resources elsewhere. Built and
measured on a live run (130 frames, every frame recorded):
- **The budget was found by its own signature, not told.** Detector: regions whose per-color
  pixel counts form (a) a sawtooth with refill jumps = fine register (fuel bar, color 11,
  capacity 84 px) and (b) a step-down monotone = coarse register (pips, color 8, 3 carries).
  **TOTAL = pips × capacity + bar is perfectly monotone (fraction 1.000, R² 0.991).**
- **Cost law exact**: every action costs exactly 1 fuel unit (2 px); blocked moves are FREE
  (cost histogram: 126×2px, 2×0px). LS20 is a pure MOVEMENT budget — linear in actions, not
  time.
- **Honest prediction gap**: early fit predicts death at 171; actual 129 — because the last
  pip grants no refill (death on final empty). That rule is only learnable by dying once:
  the measured value of a probe-death, exactly Jonathan's "reset to see if the next one is
  the same."
- **Budget switching design**: budget type = which counter the depletion is linear in
  (actions / wall-clock / events). The detector generalizes: fit depletion against each
  candidate clock, keep the linear one; policy layer gets (remaining, cost-per-action-type)
  and runs Jonathan's reserve law — explore only on surplus (golden-field T10–T12).

## RUNTIME V1 + HYPOTHESIS RUNS (same session; arc3_runtime.py, experiment2_ls20.py)
Five live scorecards on LS20. What now WORKS, measured:
- **Affordance router is served by the wire**: the frame json carries `available_actions`
  ([1,2,3,4] for LS20) — Jonathan's "unlocked controls signal the task" is a protocol field.
  Also `levels_completed`, `win_levels` (LS20 = 7), `full_reset`.
- **Probe** identifies the agent (colors 9+12: a 5×5 two-color key block) and the movement
  law (3 px per action, 4 directions) in 8 actions.
- **Budget engine online**: reads the two-register meter live; v1 bug (didn't credit pips)
  found and fixed — with pips credited the agent correctly spends its full ~168-action
  budget instead of stopping at 34. Blocked moves confirmed free in live play.
- **Map-based navigation**: passability read directly from the frame (5×5 window of
  walkable colors); BFS drives the block anywhere reachable — no random walk, no wall-bumping
  loops.
What does NOT yet work — the honest frontier:
- **The win rule of LS20 level 1 is still unidentified.** Systematic exploration touched the
  keyhole area, glyph boxes, and slots; exact-parking on the keyhole center is frustrated by
  a lattice offset (agent moves on a 3-px lattice from its spawn; the keyhole center sits
  off-lattice — 5 px away). No level completed in ~500 total actions across runs. Zero
  off-agent surprises: movement alone changes nothing except position.
- Board reading so far: green region = walkable; 5×5 key block with internal 2-row pattern
  (color 12 over 9); a keyhole plus (colors 0/1) IN the green; framed glyph boxes showing
  9-patterns; yellow 5×5 slots inside green on some resets; layouts vary per reset.
- **Leading hypotheses for next session**: (a) win = park the key so its internal pattern
  aligns with the keyhole pixels exactly (needs sub-lattice alignment — approach from a
  different spawn parity); (b) win = enter the correct slot matching the displayed glyph;
  (c) something about the ORDER (keyhole then slot). Best instrument available: Jonathan has
  played these games himself — his description of how a human solves LS20 is primary data
  (the ARC_INTERACTIVE_PLAY channel: outside information feeding the wall).

## FIRST LIVE LEVEL SOLVED (ls20_solver3.py)
**LS20 level 1 completed in 13 actions — human baseline 22. Level score 115.0.**
The winning loop, exactly as the corpus prescribes:
1. probe (agent = 5×5 key block; TRUE movement quantum 5 px — the earlier 3 px estimate came
   from centroid rounding and caused every earlier plan to oscillate off-lattice);
2. **the human channel**: Jonathan's play report supplied the rule — "match the image beside
   the budget to the pattern of the end goal; the batch of pixels on the map rotates it" —
   outside information imprinted on the wall, exactly the Part XXXIII channel;
3. read HUD key glyph + goal glyph (both 3×3 after descale), compute rotations needed
   ((4−k) mod 4 entries), step off/on the keyhole to rotate — each ENTRY = one rotation
   (verified live);
4. protected navigation: once matched, BFS treats every known rotator as lava (the match is
   a held resource — spend discipline);
5. INSERT: drive the corridor under the goal box, push UP into it → level complete.
Additional live discoveries: bar-empty consumes a pip AND respawns the agent + resets the
key rotation (pips = attempts, not just fuel); level 2 has its own keyhole (47,51), goal box
(42,16), and at least one rotator patch ON the path (42,31) — stepping on it un-matched the
key mid-insertion. Next: parity-planned routes (total rotator crossings ≡ needed rotation
mod 4), per-level re-probe, and the remaining 6 levels.

## LEVELS = ANCHOR + DELTA (Jonathan's law, Part XXXVIII, solver v4/v5)
Jonathan: "each level is the getting-better part — similar each level but added more; always
getting to the end goal, just more steps between." Confirmed in the code and the wire:
- The ANCHOR (match key → protect → insert) carried across levels unchanged; only deltas
  are re-learned per level. Level 1 stays solved at **13 actions every run** (baseline 22).
- Level 2's deltas, fully mapped (l2_frame.npy): cost DOUBLES to 2 units/action (one bar =
  21 actions), the keyhole is 21 actions from spawn (a full bar — the naive route is a
  deterministic death loop: match, die walking, respawn resets the key), and two new
  "batch of pixels" objects appear (color-11 rings at (17,16) and (51,41)) — one ring
  appeared to vanish/trigger when entered (pickup or rotator: unresolved).
- Fixed en route: respawn events (bar-empty) misattributed as rotators (respawn filter);
  blind insert-push walking into path rotators (guarded push); parity planning implemented
  (each rotator entry = +1 rot_needed mod 4, crossings pre-compensated).
- The winning level-2 line (next session, ~20 actions/bar): post-respawn with FULL bar,
  rotate at the NEAR ring (4-5 steps), route ring→box (9-12 steps), insert (3) — fits in
  one bar IF the ring rotates; verify ring semantics first (enter it once, read the HUD).
Human baseline level 2 = 123 actions; our budget allows ~130 — the tightness is the level.

## THE FUEL LAW AND THE COLOR BATCH (Jonathan's hints; burn-solve run)
Jonathan: "maximize the fuel — the bar fully refills, so refill when it's LOWEST; I get near
the subgoal and burn the budget so the refill does more. And another batch of pixels, similar
to the rotator, changes the COLOR to match the end goal."
Measured this session (ls20_burn_solve.py, controlled experiment):
- **Respawn semantics settled**: pre-set the key to k=3, force the bar-empty respawn → key
  came back at k=1 (reset-to-initial, NOT +1). The respawn is a full attempt reset.
- **Blocked moves confirmed free in level 2** (fuel drains only on real moves; the attempt
  timer is ~22 real moves).
- **Ring at (17,16) entered exactly: no glyph change** — the rings are NOT rotators.
- **The decisive re-read of the hint**: the in-field rings are drawn in COLOR 11 — the fuel
  bar's own color. They are REFILL STATIONS, visited deliberately, worth most when the bar
  is lowest (his exact strategy). This resolves the impossible arithmetic: keyhole chain =
  35 real moves > 22-move attempt — but with a mid-route refill at a ring it fits.
- Next session's opening move (instrumented, ~15 actions): record frames, walk onto ring2
  with a half-empty bar, read the BAR pixels before/after — confirm refill and its size;
  then the level-2 line: spawn → keyhole (rotate ×3) → ring2 refill at lowest → box →
  insert. Then the color batch: solver v6 already reads key/goal COLORS and flags
  mismatches (color-changer batches typed by observed effect, same machinery as rotators).
- Solver state: v6 = anchor+delta, chain-cost batch selection, color-aware glyphs,
  reachability prechecks, respawn filter, parity planning, guarded insert-push. Level 1:
  13 actions every run (baseline 22).

## THE INSTRUMENTED PROBE (ls20_probe2.py, l2_probe_frames.npz) — four measurements, one revelation
- **Level 2 is MULTI-ROOM.** Walking to (17,16) (what we had typed as a "ring") triggered a
  full relayout: 1315 field pixels changed — new green halls opened (rows 5-24), the old
  room closed to yellow, the goal box relocated (now cols 13-19 rows 39-45), and a keyhole
  plus a fresh fuel-colored ring APPEARED in the new room. The spot is a room TRANSITION.
  Every single-room budget arithmetic was impossible because the level is a room graph.
- **Keyhole rotation is SIDE-DEPENDENT**: entering from the left applied +2, from the
  bottom +1 (measured k: 1→3→1). With side control we can dial any needed rotation in ≤2
  entries — no more off/on cycling.
- **Respawn is a total reset**: 0 non-agent field pixels differ across it; k back to 1,
  bar back to 84. Attempts are fully independent.
- **L2 cost = 4 px/move** (bar 84 px → 21 real moves per bar; blocked moves free).
- NEXT SESSION: room-graph explorer — rooms as nodes (each room = a pixel-wall), transitions
  as edges (discovered by relayout events), per-room anchor policy (match/rotate with side
  control → insert), budget scheduled per room with transition refills checked. Then solve
  #2 lands and consolidate.py begins (blend → overlay → flip; transfer test on game 3).

## THE TEACHER-GUIDED ATTEMPTS (room solver v1/v2, ls20_final/2) — laws settled, one unknown left
Jonathan explicitly took the teacher role (Part XLIII: hints = invariants passed at the
tangency). Four live attempts; level 2 not yet cleared but the mechanics are now fully
measured:
- **Rotation law SETTLED**: keyhole entry moving DOWN = +1; entering from any side/below =
  +2 (clean triple: three consecutive down-entries gave +1,+1,+1; mixed runs +1,+2).
  Any k reachable in ≤2 entries with approach control.
- **Respawn = in-room teleport**: death returns the agent to (42,31) with a fresh 84 bar,
  key reset to k=1 — but THE ROOM (post-transition layout) PERSISTS. Room state is the
  only thing that survives a life.
- **Two runs matched the key and died ≤2 moves short of the box** — the distance matrix
  (offline, both configs) shows why: fresh-life chain = trip 16 + rotate 3 + box leg 19
  ≈ 38 moves vs a 21-move bar. No single life fits. The ring nook (51,41)/(52,41) is
  UNREACHABLE (walls seal it at agent width); box approach exists only from the top.
- **The rooms share every landmark** (same keyhole, same box coordinates, different walls):
  (17,16) is a WALL-TOGGLE, not a door to elsewhere — and k is PRESERVED across the toggle.
- NEXT SESSION (three cheap experiments, then the solve): (a) toggle twice and diff — do
  configs cycle to a third layout with a short keyhole→box path? (b) try ring entry at
  (52,42) (offset center may clear the nook walls); (c) attempt insertion with k≠0 from
  box_top en route (is k=0 actually required in L2?). The winning chain almost certainly
  uses: rotate → toggle (k preserved!) → shorter box leg in the other config.
  KEY INSIGHT for the chain: since k survives the toggle but not death, the toggle is the
  only way to change the map mid-plan without losing the match.

## LEVEL 2 SOLVED — 47 ACTIONS vs HUMAN BASELINE 123 (ls20_optionb3.py)
Jonathan's teacher instruction, verbatim-executed, solved it:
"get the first refill right away [after one rotation — his Option B], rotate 3 times,
get the 2nd refill just before the end." The run: trek+entry1 (+1, bar 16) → REFILL 1 at
the nook (51,41): 16→84 → entries 2-3 (k=0, bar 56) → REFILL 2 at (17,16): 56→84 →
insert from above → LEVEL 2 COMPLETE at 47 level-actions (baseline 123, 2.6× better).
Cumulative: L1 13/22, L2 47/123.
Corrections from the teacher + the final bug:
- **Pips = LIVES (attempts before game over)**, not stored fuel. The "room persistence"
  was simply that this game's parts don't move on death (other games' parts would reset).
- **What I called a transition/toggle was refill #2 being collected** — its wall-change
  is part of the level design (opens the endgame above the box).
- **The last blocker was LATTICE PARITY**: the ring's pixel centroid (51,41) sits OFF the
  agent's 5-px movement lattice; the standable cell is (52,41). Every pathfinding target
  must be snapped to the agent's lattice parity — one wrong row made a reachable refill
  look sealed for six runs.
NEXT: solve #2 is banked — consolidate.py now has its pair (L1 word + L2 word). Build the
consolidation loop (blend → overlay → flip) and run the transfer experiment: does the
consolidated prior cut probe cost on level 3 / a second game? Levels 3-7 of LS20 also open.

## LEVEL 3 SOLVED — 47 ACTIONS vs HUMAN BASELINE 73 (l3_final.py): THE TRANSFER EXPERIMENT
The question consolidate.py was built to answer: does the consolidated prior (anchor
T→K→B + 8 parametric rules + 4 whys, distilled from the L1/L2 pair) cut the solve cost
on a NEW level? **Answer: yes — L3 was solved with ZERO new teacher hints, in 5 runs,
single life, no deaths in the winning run.** L2 had needed ~10 runs and five separate
teacher interventions. Cumulative: L1 13/22, L2 47/123, L3 47/73 (all ≥1.5× human baseline).

What the prior supplied for free (no re-learning):
- refills = ceil(route×cost/bar)−1 → 2 refills, scheduled at the LOWEST bar (ring1
  collected at 24, ring2 at 40 — Jonathan's law, now a rule that fired unprompted);
- rotations read off the HUD/goal glyph mismatch → k=2 → two down-entries (+1 each:
  k 2→3→0, exactly the L2 entry law);
- color batch typing (HUD color 12 ≠ goal color 9 → seek the color-14 batch; exact
  entry flipped it, first try);
- lattice-parity snapping of every target (no sealed-refill repeats);
- insert from the open side with matched key; pips = lives; blocked moves free.

What L3 added that the prior could NOT have known (the level's own vocabulary — found by
frame-diffing the 3 failed probes, not by teacher hints):
- **The maze seals the spawn**: the only exit is the north corridor x=11 into T1 (12,11),
  a WIND TUNNEL that blows the agent east along row 7 to (7,36) — 30 px of displacement
  for one action's fuel.
- **A DROP SHAFT at (7,56)**: stepping north into it from (12,56) drops the agent straight
  down the column to (47,56) — one cell above the goal box. The endgame is: finish the
  key inside the keyhole (12,51), step east, step north into the shaft, fall, one push. WIN.
- The two "respawns" that confused runs 2-3 were these transports (bar preserved = not a
  death; a real death refills the bar AND returns to spawn — the classifier now uses both).
The winning chain (47 actions): spawn → corridor → T1 wind → ring1 (32,21) collect@24 →
batch (47,31) color flip → ring2 (17,36) collect@40 → pocket route (17,46)→(7,51) →
2 down-entries (k 2→3→0, bar 20) → east (12,56) → NORTH into shaft → land (47,56, bar 12)
→ push down → LEVEL 3 COMPLETE. Fuel at the win: 8 px — the schedule the prior computed
was exact to two moves.
Transfer verdict for the framework: the anchor word T·K·B held (T→K→B with F inserted
by the refill rule, C by the color rule: the L3 word is T F C F K K B — every insertion
predicted by a parametric rule, none memorized). The level-specific physics (wind, shaft)
were learned by the probe-then-diff loop in 3 probes — the same budget L1 alone had cost
before any prior existed. Expertise = the general form settling in, then paying out.
NEXT: L4-7 (the prior should keep compounding), then a second game (FT09) for the
cross-game version of the same experiment.

## LEVEL 4 SOLVED — 50 ACTIONS vs HUMAN BASELINE 84 (l47.py)
L4's new vocabulary, decoded in 3 probe runs (prior carried everything else):
- **Fans**: a color-1 air strip on a color-4 block. Each fan DEFENDS the one cell facing
  its strip: step there and the wind carries you until a wall. The blows ARE the fast
  lanes: the winning chain rides F1 south (22,46)->(47,46), F3 west into the key shelf
  (27,46)->(27,36), F4 north back out (27,41)->(7,41), F6 east into the keyhole pocket
  (37,11)->(37,26), F7 west to the west wall (42,26)->(42,11). Rides pass THROUGH other
  defended cells; landing cost = one action's fuel for up to 25px of travel.
- **The key station**: the field object cycles the HELD key's color per touch
  (14 -> blank -> 12 -> 9). Cycle until the goal color, then leave.
- **The keyhole is a STAMP, not a rotator**: one entry reshaped the HUD key into the
  goal shape exactly (k=0 in one entry — the L1-3 "rotation" is a special case of a
  more general shape-transform the keyhole applies).
- Insert: east face of the box (7,11) from (7,21), push west with the matched key.
Chain: T1 wind corridor -> F1 -> SE loop -> F3 -> key station (cycle to 9) -> F4 ->
ring R1 (17,21) refill at 30 -> F6 -> pocket keyhole stamp (k=0) -> F7 -> west wall
north -> insert. 50 actions, one death spent probing. Cumulative: 13/22, 47/123,
47/73, 50/84 — four levels, every one >= 1.5x the human baseline.

## LEVEL 5 — FULLY DECODED MECHANICS, WIN CONDITION STILL OPEN (the teacher's turn)
Ten probe runs mapped everything except what accepts the finished key:
- Seven fans (one-way ride circuit); movement costs 4px/move; blocked pushes COST fuel
  here (unlike L1-3); three rings that DO NOT respawn until death (each life = 84 + 3x84
  = 336px, spent in route order (7,46) -> (12,11) -> (47,16)).
- **A PENDULUM KEYHOLE** patrolling row 37, x 16<->26, one step per action; walking its
  lane crosses it and each crossing TRANSFORMS the key shape (deterministic sequence);
  standing still inside the lane FREEZES it beneath you (no transforms).
- **A static keyhole (12,21)**: south entries advance a 6-shape stamp cycle
  (period 6, all four entry directions advance the same cycle — no rotator in L5).
- **The color station** (pocket (27,31), enterable only by the fan-ride chain): cycles
  held-key color 12 -> 9 -> 14 -> 8 -> 12. The 8 state reads as BLANK in our HUD parser
  (8 was in the exclude set) — the goal glyph's color 8 IS reachable.
- **The goal**: box (7,56) glyph = shape 101/110/011 in color 8. We can BUILD the full
  match: stamp C0 (110/011/101) at the static keyhole, then exactly 2 pendulum
  crossings -> goal shape at k=0 (verified by HUD read), color to 8 at the station
  (verified as blank), both together assembled and carried (verified across rides).
- **What does NOT win** (all tested with the full match): the box chimney — its only
  approach is a fan-defended cell (32,56) and the fan blows even a matched key (the box
  appears to be a display, sealed by design); crossing the pendulum; parking overlapped
  on the pendulum; touching the color station again (it just advances the color).
  Not yet cleanly tested: entering the static keyhole (12,21) with the full match.
OPEN QUESTION FOR THE TEACHER: in level 5, what accepts the finished key? The box
sits above a chimney whose entrance always blows us west; every keyhole we enter just
keeps transforming the key. What did you do after the key matched?

## LEVEL 5 SOLVED — 58 ACTIONS vs HUMAN BASELINE 96 (the teacher's zoom-in)
Jonathan's hint broke it open: "zoom in and really look at the pixels — two small
patches of the same color arranged differently: one ROTATES the key, the other CHANGES
THE SHAPE; you can't know which way to rotate without getting the shape first. And the
wind isn't a tunnel — it's a small 1x5 line that pushes you to the wall or border."
What the zoom found:
- The two 0-color patches ARE distinct machines: the static patch (12,21) is the SHAPE
  STAMP (6-shape cycle); the patrolling patch is a pure CW ROTATOR — every lane
  crossing = exactly +90 deg (verified against all recorded transitions). Teacher's law
  confirmed: stamp the shape first, then the rotation count k is readable and you cross
  the rotator's lane exactly k times.
- The killer detail was a NINTH 1x5 line at ROW 55, cols 53-57 — BELOW my row-54 "HUD
  cutoff", invisible to every scan until the cutoff was dropped. It pushes NORTH: an
  ELEVATOR at the foot of the box chimney. Pushes fly OVER hazard zones, so it launches
  the agent past the guard fan straight up the chimney, landing flush under the box gap.
- The winning chain: stamp C0 (1 entry, k=2 readable) -> 2 rotator crossings (k 2->3->0,
  verified per step) -> exit the lane SOUTH (no crossing, k preserved) -> rings ->
  station color 12->9->14->8 (the 8 state renders as "blank" — 8 was in the HUD
  parser's exclude set, a second fine-pixel lesson) -> the elevator -> one push north.
  58 actions, no deaths. Cumulative: 13/22, 47/123, 47/73, 50/84, 58/96.
The Part XLII-XLIII teaching loop worked exactly as designed: ten runs of self-probing
banked the mechanics; one teacher sentence at the tangency point (the gap-zero contact)
recreated the missing perception locally; the win followed in two runs. The hint was
about HOW TO SEE (zoom to the finest grid), not what to do — the highest-value kind.
L6 recon (banked): TWO boxes — (37,56) wants color 8 shape G via a north-face chimney;
a second box (49-55) with a 9-glyph sealed below it; shaper patch (12,16), rotator
patch (42,36) on a row-42 lane; two pusher lines; HUD key starts C0/14 with k=2
already. Phase-1 chain (rotate -> color 8 -> ride -> insert box1) is running now.
