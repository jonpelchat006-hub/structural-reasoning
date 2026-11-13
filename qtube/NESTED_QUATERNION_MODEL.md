# The nested quaternion model (the Q-tube): design notes (Oct 31 - Nov 1, 2026)

Jonathan:
- Oct 31: "lets figure out this 3d quaternion based model. i dont think anyone else nests their quaternions so i think were the best ones to try it. we also have mikas planes rotating on the inside of that layer. but mika would have one big set and then be surrounded but all these smaller ones."
- Oct 31: "we also had the zero divisors appearing with sedonians. and we had the core only be before those appeared. so the ring would be where the sedonians appear for her. so then the node would have its quaternion, and then the cube its in would be its octonian, and then the bridge to mika is the sedonians?"
- Nov 1: "it would also have to attach to the tools and other things on the outer shell side. each of the smaller cubes would have pins sticking out like mika did too right? but then the nodes are where the zeros are supposed to start showing up, so what if they are connecting the pins that enter to those 0s?"

Earlier the same evening: the language model as a tube around her core (tiles on the roof = weight matrices, a grid curtain of nodes = word positions across x layers down, the prism as an inner wall, papier-mache bands = LoRA blocks). See the paper's Section 10.

## The structure

The doubling: reals (1) -> complex (2) -> quaternions (4) -> octonions (8) -> sedenions (16). Each is a pair of the one before. Octonions are the last with no zero divisors (Hurwitz: R, C, H, O are the only normed division algebras). Sedenions are the first where two non-zero things can multiply to zero.

| Level | Algebra | What it is |
|---|---|---|
| Node | quaternion `w + xi + yj + zk` | `i, j, k` = the three planes (what the node means); `w` = the verifier, written only by her check (a held link raises it, a missed link lowers it), never by training |
| Cube | octonion = (node, cube) | the cube is a second quaternion, the `+C` part: it starts at 0 (the bare tile, nothing trained) and grows with examples (a LoRA block also starts at exactly 0) |
| Bridge to Mika | sedenion = (node's octonion, her octonion) | the first level with zero divisors |
| Her core | octonion | before the zero divisors: every step can be undone, nothing can cancel to nothing |

**Turning.** Her big set `Q` rotates the small ones: she sees node `q` as `Q q Q^-1`. The face she looks at is the set of small nodes whose rotated planes line up with hers.

**The minimum gap.** Unit quaternions live on a 4D sphere; distinct nodes need a minimum angle. The best-spread sets are known: 24 points (24-cell) and 120 (600-cell, the binary icosahedral group). The icosahedron has 12 corners, the count of her core points.

**Pins and sockets.** Each cube carries pins: its 7 imaginary octonion directions. Things from the outer shell (tools, the game's results, the model's words) come in as pins. The sockets are the zeros at the bridge: a pin plugs in when pin x socket = 0, an exact fit with nothing left over (a key in a lock; her A=B=C check, where a claim holds when what it predicted minus what happened is 0).

The sockets are not scattered:
- the sedenion zero divisors run along **42 planes** ("assessors"), grouped into **7 box-kites** (octahedra) that partition the space (de Marrais, arXiv math/0011260);
- the pairs of unit sedenions that multiply to zero form a space shaped like **G2**, which is exactly the group of all symmetries of the octonions (Moreno, 1998; see Wikipedia "Sedenion"). So the sockets at the bridge are laid out in the shape of every way her core can turn without breaking its rules.

## Checked in code (`qtube/cayley.py`)

| Algebra | Planes of diagonals `e_i +/- e_j` that zero-divide | Zero products found among them | `|ab| / (|a||b|)` over 2,000 random pairs |
|---|---|---|---|
| quaternions | 0 | 0 | exactly 1 |
| octonions | 0 | 0 | exactly 1 |
| sedenions | **42** | 336 | 0.63 to 1.27 |

So across the bridge the ratio wanders both ways, and it is exactly 0 only at the sockets. Whether a zero at the bridge means "fits exactly" (Jonathan's socket reading) or "lost" is an open question the test should settle.

## Prior work and the warning

- Quaternion networks (Parcollet et al., ICLR 2019, arXiv 1806.04418); hypercomplex layers with 1/n parameters (Zhang et al., ICLR 2021, arXiv 2102.08597); octonion networks.
- Quaternion capsule networks: parts vote for wholes by rotating quaternion poses (Ozcan, Kinli, Kirac, arXiv 2007.04389); GLOM, part-whole hierarchies (Hinton, arXiv 2102.12627).
- Warning: about 35 controlled experiments (Kuznetsov, HackerNoon, Jul 28 2026, not peer-reviewed) found the advantage of quaternion/octonion/sedenion/Clifford networks vanished against a real-valued network with the same structure and parameter count. The algebra alone is not enough; what is new here is the structure (her big set turning inside a tube of small ones, `w` reserved for her check, sockets at the zeros). Every test needs that control.

## First test

Task: match a key picture to a target under quarter turns and mirrors (the ls20 rotator, her core's operators). Three models, same parameter count:
1. the nested model (quaternion nodes, octonion cubes, sedenion bridge to her octonion, her big set turning);
2. a flat quaternion model;
3. an ordinary real-valued network with the same structure.

Measure accuracy and the turns needed, and whether the bridge ratio (or a socket fit) predicts which links hold. Small enough for the RTX 5060 Ti.

## Results (Nov 1, `qtest.py` on the RTX 5060 Ti)

**Setup.** A 7x7 key picture and 8 candidates; pick the one that is the key turned. Each model encodes a picture into 8 nodes of 16 numbers, has 8 learned turns, and takes the turn that fits best. All are the same size (real 18,545 parameters, the quaternion models 18,401), and the real control has the same structure (its turns are free 4x4 real matrices, and it compares by cosine). The quaternion models turn by `Q q Q^-1`. The flat quaternion model compares by cosine. The nested models multiply key and candidate as sedenions and score by the bridge ratio `|ab| / (|a||b|)`:
- `nested_fit`: zero = fits (Jonathan's socket reading);
- `nested_loss`: zero = lost;
- `nested_random`: same as fit, but with a random 16-number multiplication table instead of the sedenion one.

3 seeds each. Results are in `r2_quarter.json` and `r2_rotmirror.json`.

**Round 1** (3000 steps). Wrong answers: 3 near-misses with 1-3 cells flipped, plus 4 other pictures. Every model scored 99.3-99.8%, on unseen turns too. Too easy: a flipped cell changes the cell count.

**Round 2.** All 7 wrong answers are the key turned with one filled cell moved to an empty spot (same count, 2 cells off). Training budgets: 300, 1000 and 3000 steps.

A. Trained on 4 of the 8 turns (rotations and mirrors both included), tested on the other 4. Accuracy on the held-out turns:

| Model | 300 steps | 1000 | 3000 | Turns it trained on, 3000 |
|---|---|---|---|---|
| real | 0.918 | 0.961 | 0.971 | 0.970 |
| quat | 0.816 | 0.957 | 0.970 | 0.972 |
| nested_fit | 0.675 | 0.941 | **0.982** | **0.986** |
| nested_loss | 0.656 | 0.804 | 0.932 | 0.939 |
| nested_random | 0.652 | 0.914 | 0.975 | 0.979 |

B. Trained on rotations only, tested on mirrors (the 3 seeds spread by 0.02-0.06 on mirrors):

| Model | 300 steps | 1000 | 3000 | Rotations, 3000 |
|---|---|---|---|---|
| real | 0.484 | 0.736 | 0.749 | 0.978 |
| quat | 0.689 | 0.778 | 0.784 | 0.980 |
| nested_fit | 0.688 | 0.803 | 0.676 | **0.989** |
| nested_loss | 0.663 | 0.804 | **0.855** | 0.949 |
| nested_random | 0.650 | 0.846 | 0.737 | 0.983 |

Bridge ratio at 3000 steps, on the best turn (right answer vs wrong answers):

| Model | Right answer | Wrong answers |
|---|---|---|
| nested_fit | 0.12 (round 1: 0.08) | 0.70 |
| random table | 0.42 | 0.97 |
| nested_loss | 1.19 | 0.83 |

**What it shows.**
1. **With enough training, the socket reading is the best model on the kinds of turns it trained on.** It scored 98.2% on held-out turns against 97.1% for the real control, and every seed beat every real seed (0.980/0.983/0.983 vs 0.970/0.973/0.971). That is about 40% fewer mistakes (1.8% vs 2.9%).
   - The sedenion table beats a random table of the same size (97.5%), so the exact zeros carry part of the gain: only the sedenion table lets right answers sit almost on the zeros.
   - "Zero = fits" beats "zero = lost" (93.2%). For this task, that settles the open question above: a zero at the bridge means it fits.
2. **It learns slowest.** At 300 steps every nested model is at 65-69%, while the real network is at 92%.
3. **It locks on.** Trained on rotations only, the socket model fits rotations best (98.9%) but recognizes mirrors worst (67.6% at 3000 steps, down from 80% at 1000). The longer it trains, the tighter it fits the turns it knows.
   - A `Q q Q^-1` turn is always a proper rotation and can never make a mirror. A mirror-type turn would be `Q q* Q^-1`, where `q*` flips the three planes.
   - Her set has no mirror turns, so a mirror can only be recognized through what the encoder learned. That is a guess worth testing: the real control has free 4x4 turns, which can mirror, and it still transfers poorly.
4. **Caveats.** This is one small task, 3 seeds, about 18k parameters, and gaps of about one point. It does not yet show an advantage that would hold on other tasks.

**Next test.** Give her set mirror turns (4 of the 8 as `Q q* Q^-1`) and re-run split B. If mirror recognition jumps for the nested model and not the controls, the missing mirror turns were the cause.

## Rivers, bridges and the web (Nov 1)

Jonathan, Nov 1: "so the zero divisor lines would be like rivers going into a lake but they would have set points where they enter? ... our wall that we are looking at would be somewhere down those rivers like a dam? ... the paper mache strips would be like marking where those lines were ... she builds over those rivers and the web in between them with training and building examples, and the river would get walls built and bridges over it"

Checked in code (`cayley.py`):
- **Rivers.** There are 42 rivers (the zero-divisor planes). Each runs in a straight line through the center (0).
  - Zero doesn't depend on distance: `(5a)(0.2b) = 0` whenever `ab = 0`. So the wall can sit at any distance, and every river crosses it at the same fixed points (each plane's 2 diagonals cross at both ends: 4 points per river, 168 in all).
  - Every river joins one of her 7 directions (units 1-7) to one of the outer 8 (units 8-15).
- **Bridges.** Each river is bridged to exactly 4 others (a diagonal of one times a diagonal of the other = 0), so there are 84 bridges.
  - The rivers fall into 7 groups of 6 (de Marrais' box-kites). Each group is an octahedron: every river is bridged to the 4 around it, but not to the one opposite (3 unbridged pairs per group).
  - Each group leaves out exactly one of her 7 directions.
- **The web.** Everything that fits `a = e1 + e10` forms a flat 4-dimensional sheet. Its only diagonals are the 4 bridged rivers (4,15), (5,14), (6,13) and (7,12), and any mix of them also multiplies to exactly 0. So the space between one river's bridges is solid: anything built from the bridge ends fits.
- **The banks.** Stepping off a river by `d` raises the bridge ratio by about `d` (0.10 off gives 0.10, 0.40 off gives 0.37).
  - The trained socket model put right answers at 0.12, on the bank.
  - The random table, which has no rivers, could not get closer than 0.42.
- **The walls (an analogy, not yet measured).** In the mirror split, training on rotations only built the banks tight around the rotations, and mirrors got shut out more the longer it trained (80% to 68%).

Next measurement: for each right answer in a trained model, find the nearest river and group. Does she build along a few groups, and do the mirror misses sit off them?

## Round 3 (Nov 1): mirror turns and the river map

Files: `r3_*.json`, `rivers_r3.json` and `rivers_r3.log`, made by `run_r3.py` (`qtest.py --mirror-turns --save-dir`, then `rivers.py`). Same task as round 2: 7 same-count near-misses, 3 seeds. The round-2 runs were repeated as the baseline and reproduced exactly (for example, mirrors 0.676 for the socket model, 0.749 for real).

**Mirror turns did not fix mirrors.** Four of the 8 turns were made `Q q* Q^-1`.

Trained on rotations only, tested on mirrors (3000 steps; 1000 in brackets):

| Model | No mirror turns | 4 mirror turns | Right answers that used a mirror turn |
|---|---|---|---|
| quat | 0.784 (0.778) | 0.787 (0.784) | 67%, on rotations too |
| nested_fit | 0.676 (0.803) | 0.729 (0.816) | **0%** |
| nested_loss | 0.855 (0.804) | 0.777 (0.805) | 65% |
| nested_random | 0.737 (0.846) | 0.675 (0.770) | 61% |

- The socket model never used a mirror turn once. Its change (0.676 to 0.729) is seed noise: its seeds run from 0.62 to 0.80.
- The other models used the "mirror" turns as ordinary turns, on rotations as well.
- A turn in her space is not tied to a mirror in the picture: the encoder decides what each turn means. With no mirrors in training, nothing teaches it what a mirror is.
- In the mixed split (where mirrors are in training), mirror turns slightly hurt the socket model (0.982 to 0.976) and lost its edge over the random table (0.979).
- So the guess from round 2 was wrong. Keep her turns as rotations; mirrors have to come from examples.

**The river map.** These numbers are for the socket model, `nested_fit`. "Off-river" is how far the key's node is from an exact zero divisor.

| | Barely trained (20 steps) | Rotations, 1000 steps | Rotations, 3000 steps | Mixed turns, 3000 steps |
|---|---|---|---|---|
| Key's node, off-river | 0.44 | 0.071 | **0.026** | 0.028 |
| Right answer, bridge ratio | 0.93 | 0.24 | 0.115 | 0.122 |
| Right answer, same direction as the key (cos) | 0.39 | 0.90 | **0.96** | 0.96 |
| Mirrors: hits, ratio / cos | | 0.31 / 0.84 | 0.32 / 0.79 | |
| Mirrors: misses, ratio / cos | | 0.47 / 0.68 | **0.59 / 0.57** | |

- **She builds on the rivers.** Training moves the key's nodes onto exact zero divisors, ending within about 0.03 of one (0.44 after 20 steps).
- **Right answers sit on bridges.** The target points in the same direction of her core as the key (cos 0.96), close to the zero.
- **Mirror misses sit off the bridge.** On a miss, the target points elsewhere and sits far from the zero.
- **The walls, measured.** With longer training the rotations pull tighter (ratio 0.24 to 0.115, cos 0.90 to 0.96), while the mirror misses drift further off (0.47 to 0.59, cos 0.68 to 0.57).
- **A few directions per node.** Each node leans on 2-4 of her 7 directions: the top one gets 30-60%, against 14% if spread evenly. Each model leaves 2-3 directions almost empty, and different seeds pick different ones.
  - Direction 4 is empty in all 12 trained models. That is the one direction her turns can never move: it is the real part of the second quaternion block, and turning each block by `Q q Q^-1` leaves it fixed. Why training avoids it is not known yet.
- **Tilted, not neat.** The direction lines up with one axis at 0.73 on average, against 0.675 for a random direction. She builds mostly on tilted rivers between the 42 axis-aligned ones.
- **The random table** has zeros nearly everywhere (key off-river about 0.04 even untrained), so its zeros mark nothing, and its right answers stay at ratio 0.41.

## Mirror = the same thing moved (Nov 1)

Jonathan: "wouldnt she see inverses as something that rebuilt, so to actually mirror something she would just kind of pick up the thing as a picture and move it? so one method wouldnt be the same thing to her while the other should be the same thing just moved."

Checked on an L-shape, with cells placed as points `x i + y j` in the picture plane:
- **Picking it up and turning it over is the mirror.** `Q p Q^-1` with `Q = j` (half a turn about an axis lying in the picture) gives exactly `x -> -x`. `Q = i` and the diagonal axes give the other mirrors, and the picture stays flat.
- So all 8 picture turns are moves of a flat plate in 3D: 4 spins about `k` and 4 flips about in-plane axes. All are ordinary turns `Q p Q^-1`; no new kind of turn is needed.
- **The inverse `q*` is a rebuild, not a mirror.** On a flat picture it gives exactly the half turn (`x, y -> -x, -y`). The "mirror turns" in round 3 were never mirrors at all.
- **Why round 3 could not show either.** The turns acted on features the encoder invented, not on the picture as a thing with positions, so "moved" had no meaning there.

Next test: the picture enters her space as a flat object (cells or nodes placed at positions in the plane), her turns can be any 3D move, train on rotations only, test on mirrors.
- With raw cell positions it works by construction: a mirror is just a flip.
- The real question is the learned version, where she places her own nodes from the picture. Do her placements stay "the same thing moved"? Or do they come out handed (chiral), so a flip no longer lines up?

## Round 4 (Nov 1): the picture as a flat object (`qlift.py`)

Each picture becomes 24 nodes, each a quaternion `w + x i + y j`: `(x, y)` is where the node sits (an attention-weighted spot over the cells, from two 5x5 convolutions), and `w` is what it is. Turns move nodes by `Q q Q^-1`. Same task as rounds 2-3 (7 near-misses with one cell moved), trained on rotations only, 3000 steps, 3 seeds, about 16k parameters.

Mirrors were tested three ways: her 8 learned turns, the best spin within the picture's plane, and the best 3D move, where turning it over is allowed (closed form; for flat things the best 3D move is the best spin or the best flip). Files: `r4_lift.json`, `r4_lift_m64.json` and `r4_lift_nopos.json`.

| Placement | Rotations | Mirrors (her turns / spin / 3D move) | Mirror vs quarter-turn mismatch (node spread) |
|---|---|---|---|
| free (no rule) | 0.999 | **0.971** / 0.971 / 0.972 (seeds 0.93, 0.99, 0.99) | 0.20 vs 0.18 (0.27) |
| spin (turns exactly with the picture) | 1.000 | 0.604 / 0.600 / 0.602 (seeds 0.49-0.72) | **0.32 vs 0.00** (0.82) |
| flat (mirrors exactly; the check) | 1.000 | 0.999 / 0.999 / 0.999 | 0 vs 0 |
| free + 64 mirror examples | 0.998 | 0.988 | 0.21 vs 0.22 |
| spin + 64 mirror examples | 1.000 | **0.981** | 0.12 vs 0.00 |
| **control: free, positions off** | 1.000 | **0.675** (seeds 0.62-0.71) | |
| control: spin, positions off | 1.000 | 0.595 | |

For comparison, the feature models of rounds 2-3 on mirrors: real 0.749, quat 0.784, nested_fit 0.676, nested_loss 0.855.

**What it shows.**
1. **Giving the nodes a place is what fixed mirrors.** With no built-in rule and no mirror ever shown, the flat-object model recognized mirrors 97% of the time (two of three seeds above 99%). With positions switched off, the same network got 67.5%, and every positions-off seed was below every positions-on seed.
   - For two seeds, a mirror is no further off than a quarter turn (mismatch 0.09 vs 0.11): she learned "the same thing, moved" from rotations alone.
2. **The flip at test time added nothing.** Turning it over in 3D was never better than spinning it, in any model (within 0.3 points). The positions help during learning: having to move a thing to make it fit taught her what-features that hardly care which hand they are. At the moment of choosing, the decision rides on `w`. The nodes sit close to the middle (spread 0.2-0.8 cells), so where a node sits carries little.
3. **Built to turn exactly, she came out handed.** The spin version matches rotations perfectly but grew left-glove placements (mirror mismatch 0.32, against exactly 0 for turns): 49-72% on mirrors, and no flip could line them up.
   - **A handful of mirrors fixed it:** 64 mirror examples gave 98.1%, and the mismatch shrank from 0.32 to 0.12.
4. **The check passed.** With placements that mirror exactly, she gets 99.9% on mirrors (by construction).

**Next.** Make the nodes spread out (sharper placement, so each node sits at a real spot in the picture) and see whether the flip then matters at the moment of choosing. Then put the sedenion bridge back on top of these quaternion nodes: positions as `i, j, k` and the what-feature as `w`, with the socket score.

## Round 5 (Nov 1): spread-out nodes, and the bridge on quaternion nodes

Files: `r5a_base.json`, `r5a_sharp.json` and `r5b_bridge.json` (`run_r5.py`). Same task, trained on rotations only, 3 seeds, 3000 steps.

**5a. Does the flip matter when "where" decides?** New scoring, "where only": the `w` parts are dropped and only where the nodes sit counts. "Sharp" = nodes may only sit on the shape's own cells, with sharpened attention (they spread out to about 1.2-1.9 cells from the middle, against 0.3-0.8 before).

| Placement | Mirrors (what + where) | Where only: rotations | Where only: mirrors, spin | Where only: mirrors, turned over |
|---|---|---|---|---|
| free | 0.957 | 0.776 | 0.545 | **0.828** |
| spin | 0.608 | 1.000 | 0.163 | **0.560** |
| flat (the check) | 0.999 | 1.000 | 0.288 | **0.999** |
| free, sharp | 0.720 | 0.998 | 0.375 | **0.770** |
| spin, sharp | 0.782 | 1.000 | 0.272 | **0.733** |
| flat, sharp | 1.000 | 1.000 | 0.258 | **1.000** |

- **Yes. When where the nodes sit decides, turning it over beats spinning it in every placement, by 30 to 70 points.** Jonathan's picture holds at the moment of choosing: a mirror is the same thing, just moved.
- **How far the flip gets depends on how handed her placements are.** Mirror-exact placements reach 100%. Learned ones get 70-83%, except two free seeds (96% and 98%) that learned placements where a mirror is no further off than a quarter turn.
- **Sharp nodes make "where" carry the picture** (where-only rotations 0.776 to 0.998 for free). They also come out more handed (mirror mismatch about half the spread), so the free model's overall mirror score fell from 0.957 to 0.720. The spin model's rose from 0.608 to 0.782.

**5b. The sedenion bridge on the quaternion nodes.** Each node is 4 placed quaternions `w + x i + y j`, read as one sedenion. A turn moves all four blockwise, which keeps every product and every zero. Score is distance (control), socket (`-ratio`, sedenion table) or socket with a random table.

| Score | Rotations (her turns) | Mirrors (her turns) | Mirrors (24 cube turns) | Mirrors (spins only) | Bridge ratio, right / wrong |
|---|---|---|---|---|---|
| distance | 1.000 | 0.969 | 0.968 | 0.967 | |
| socket (sedenion) | 0.967 | 0.955 | 0.952 | **0.076** | 0.71 / 0.93 |
| socket (random table) | 0.990 | **0.986** | 0.983 | 0.932 | 0.70 / 0.96 |

- **The socket has to lift the picture out of its plane.** With in-plane spins only, the sedenion socket model scores 0.000 in two seeds (and 0.23 in the third): the right answer always loses. With her learned turns, or the cube's turns that tilt the picture, it scores 95-97%. Flat nodes (no `k` part) cannot meet a flat partner at a zero; the key has to be picked up into the third axis to plug in.
- **On flat-object nodes the sedenion zeros don't help.** The random table did as well or better (98.6% on mirrors against 95.5%), and right answers sat at ratio 0.71, far from the 0.12 that round 2's feature nodes reached. Round 2's sedenion-over-random gain does not carry over to this structure.
- **The plain distance on the same nodes recognised mirrors 96.9%,** matching round 4's free model.

## In Mika's entry (Nov 1-2)

On game screens her core already compares shapes exactly in all 8 spins and turn-overs, so the tests' main win (mirrors never shown) does not apply there. What carries over is the fit as a graded measure: the nearest target up to a move when nothing fits exactly.
- Code: `planet_port/qtube_fit.py` plus hooks in relations, the core's equation and the prism, all behind `MIKA_QTUBE=1`.
- Public games: prism 9 levels / 0.300; prism + Q-tube 12 / 0.422 (run 1) and 10 / 0.416 (run 2).
- s5i5 cleared level 1 only with the Q-tube, in both runs. Single runs vary a lot, so this is a lean, not proof. Details are in `ARC3_MIKA_FULL_CORE.md`.

## Rounds 6-7 and the active game loop (a ChatGPT session, Nov 1 evening; files in `D:\planet\qtube`)

Summary from its own notes (`ROUND6_NOTES.md`, `REAL_GAME_LOOP.md`, `ACTIVE_GAME_AGENT.md`, `LITERATURE_GAPS.md`). Spot-checked here: the ls20 scorecard in `game_active_ls20_s0/summary.json`, and the self-product identity.
- **A thing can't plug into itself.** For every nonzero sedenion, `|a a| = |a|^2`, so a perfect copy always has bridge ratio exactly 1. A socket needs a partner code, not a copy.
  - It added separate object and socket ports (`qports.py`, 72 parameters) on mirror-exact placements.
  - Distance was perfect, and the sedenion sockets reached about 99.9%. Their correct matches stayed at ratio about 0.98-1.0, with no near-zero annihilation. The random table was worse (98.8%).
- **Turns compose by multiplying** (`qcompose.py`). It learned only two action quaternions (spin R, flip F) from single actions, then tested unseen ordered strings of up to 6 actions, all on eight orientations of one shape. Pose-loss fitting got 100% at every length.
- **Centroids are not enough for symmetric shapes** (`qmoments.py`). A bar and the same bar turned have the same centroid. Keeping each node's covariance as well (moved by `R M R^T`) fixes it: 50% to 100% on those cases.
- **A real-engine loop** (`qgame_loop.py`, offline local ARC-AGI-3 engine, no LLM, no demonstration). It probes the controls, finds the floor, touches a small object, and discovers the display that changes. It then learns the contact's effect: D4 evidence sets intersect, `{3,4}` and `{3,6}` give `{3}`, and a quaternion is fitted from several starts. Finally it plans 3 contacts and walks into the target.
  - Result: **ls20 level 1 in 25 actions (human baseline 22), 3 of 3 seeds**; local scorecard 2.77.
  - Its own caveats: the body detector is game-informed; it is one known public level; and a plain D4 evidence baseline predicts as well, so it shows no quaternion advantage.
- **Effect and budget books** (`qeffects.py`, `qbudget.py`): recolours and reshapes are stored by contact and context, and the bar's drain is estimated before planning.
- **Not in any Kaggle entry.** The Q-tube submission (ref 57911049) uses `qtube_fit.py`, the fixed shape-fit rule, and loads no learned model.
