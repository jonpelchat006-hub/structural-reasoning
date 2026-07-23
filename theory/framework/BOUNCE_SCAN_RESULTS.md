# §16 Bounce-scan — the first eval movement in the project

Built `arc-slice/src/bounce_scan.ts`: the double-bounce roof search (SPARSE_VESICA §16). A
COMPOSITIONAL program search that **jumps into territory the depth-2 (prefix×residual) engine never
reaches** — ops visited in **golden-ratio order** (the φ-bounce ergodic scan of the op space), a beam
pruned toward the target by cell-agreement, accepting a candidate when it **phase-locks** (reproduces
every train pair). Depth ≤ 3.

## Result — full eval sweep (0–400, depth 3, beam 30)
| range | solved | net-new |
|---|---|---|
| 0–40 | 1 | 0 |
| 40–100 | 2 | 0 |
| 100–160 | 3 | 0 |
| 160–220 | 3 | **1** (8ee62060) |
| 220–280 | 0 | 0 |
| 280–340 | 1 | 0 |
| 340–400 | 3 | **2** (f823c43c, fc754716) |
| **total** | **13** | **3** |

## The 3 net-new (verified: program fits ALL train pairs AND reproduces the held-out test)
- **8ee62060** — 3 train pairs, fits all, solves test. Strong.
- **fc754716** — 4 train pairs, fits all, solves test. Strong (well-constrained).
- **f823c43c** — 2 train pairs, fits all, solves test. *Caveat:* only 2 pairs (milder constraint),
  but it did reproduce the full held-out test grid exactly.

## Why this matters (honest framing)
- **First non-zero eval gain from a new mechanism.** Every prior probe — generative draw, topology
  lift, register-combine, the ability-draft reordering — added **+0** net-new on eval. The bounce-scan
  added **+3**. Small in absolute terms (3 of ~400; baseline was 26 verified → ~29), but it is the
  first method to *cross* at all.
- **It crossed by GENERATING, not reordering.** The draft (§13.4) could only reweight existing
  abilities (+0). The bounce-scan reaches depth-3 compositions the hand-written depth-2 inducers don't
  enumerate — "jumping into new territory" (Jonathan's framing) is exactly what found the new solves.
  This confirms §14.4: eval gain comes from raising the **roof-projection** (new candidates), not from
  re-weighting the floor.
- **The golden-order scan is doing real work:** ergodic op-space coverage reaches programs a fixed
  sweep order would deprioritize.

## Honest limits / next
- **Small and slow.** 3/400, and depth-3 brute search is expensive (~40s per 60 tasks). f823c43c rests
  on 2 train pairs (mild overfit risk, though test passed).
- **Next levers:** (1) use the **ability-draft prior** to order ops inside the scan (faster + smarter
  than pure golden) — the two roof tools combined; (2) push to depth 4 on the tasks where depth-3
  leaves the beam close (high cell-agreement but not locked); (3) add the floor's newer atoms
  (register-combine, paintRank, sort) into the searchable op set so compositions can use them.
- The direction is validated: a *generating* search over the residual is what moves the number. The
  bounce gave the roof a real search dynamics, and it crossed.

Files: `arc-slice/src/bounce_scan.ts`. New eval ids: 8ee62060, fc754716, f823c43c.

---

# §16b — the SECOND bounce: springs + the broken-spring diagnostic

Abilities = springs sticking out of floor/roof; the layer bounces off the *springs* (2nd bounce), the
draft sets their stiffness/direction, and a spring poking too far into the void = a near-miss that
needs another cycle / compaction / lift. Built `bounceSearchDiag` (tracks the furthest-poking spring =
best near-miss program) + `spring_scan.ts` (depth-3, then "another recursive cycle" = depth-4 retry on
springs poking ≥0.90).

## Result — EVAL slice [0,45)
- depth-3 solved=1, net-new=0 (consistent with the full-sweep rate on this slice).
- **near-miss (broken-spring) distribution:** `0.95+: 4`, `0.90–95: 2`, `0.80–90: 13`, `0.60–80: 6`,
  `<0.60: 19`. Many springs poke 80–99% of the way and don't lock.
- **DEEPENED (depth-4 on ≥0.90 pokers): +0.** "Another recursive cycle" did **not** close the near
  misses — more of the same op-space doesn't reach them.
- **Top broken springs (where to look):**
  `0b17323b 0.989 cropToColor`, `18419cfa 0.978 cropToColor`, `11e1fe23 0.968 cropToColor`,
  `14754a24 0.961 cropToColor`, `1acc24af 0.948 paintRank`, `009d5c81 0.938 keepCommon→keepTopK`.

## The honest, useful finding
- **The broken-spring diagnostic localizes the gaps precisely.** Four eval tasks are
  *cropToColor + ε* (96–99% locked by one op). The springs point exactly at what's missing.
- **Deepening is the WRONG closer here (+0).** These aren't almost-deeper-compositions; they're one op
  + a tiny residual. Of Jonathan's three options — recurse / compact / lift — **"recurse" (depth+1)
  fails**; the diagnostic says the closer is **compact** (fix the few mismatched cells), a refinement
  ability, not more depth.
- **Concrete next build:** a *residual-closer* ability — run the best near-miss program, then repair
  the handful of disagreeing cells (learn the per-cell fix from train). The springs say this would
  target a real cluster (cropToColor-adjacent tasks). This is the §16 phase-lock "final snap."

## Status
Second bounce built; the spring diagnostic is the keeper — it turns the blind golden scan into a
*guided* one that reports where the abilities almost-reach. Next ability is pinned by the data:
a residual-closer over the top broken springs. (Slice = 45 tasks; the cropToColor cluster is already
a clear signal.)

Files: `arc-slice/src/bounce_scan.ts` (bounceSearchDiag), `arc-slice/src/spring_scan.ts`.
