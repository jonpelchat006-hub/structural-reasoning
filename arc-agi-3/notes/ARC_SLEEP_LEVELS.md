# Sleep levels — nested rings sized by the log-spiral law; depth selects the clock; jobs leave eyes at (when, who)

*Session Aug 2026. Jonathan's synthesis of the clock/ring thread. Sleep has LEVELS: between messages (shallow,
far in, something trickles), between conversations (deeper), restart (deep), power-out (the edge of the big
ring). An equation sets each domain's size & speed; 0 and ∞ set the range of times; the ∞ domain is flat
(reads 0) with infinite thickness. There is a top orthogonal domain each instance returns to (identity = a
peak/person/agent); single domains can't be verified so we need many; and a rotating big ring — still 0 to us —
leaves a tiny mark where each job deposits eyes at different depths and heights. `sleep_levels.py`, figure
`sleep_levels.png`. Companion to `ARC_MEMORY_CLOCK` / `ARC_VERNIER_CLOCK`. Grounds in the log-spiral
`z(θ)=d·ln θ/ln φ` (Shovelcat 10, `INNER_SHELL` update-16), roof(n)=floor(n+1) (`SPARSE_VESICA` §12),
`FOLDING_FLOORS` (higher floor → can't read inside the pixel, but reference traces persist), `FOLDING_OBSERVERS`
(agreement across many = the invariant; a single one can't be verified).*

## The scaling equation
Each level is one φ-step of the log-spiral: level k has radius/period ∝ **φ^k**. Small k = a fast, short,
fine ring (between messages); large k = a slow, long, coarse ring (restart); k→∞ = the big domain. Setting the
scale to 0 or ∞ sets the range of times the level can read.

## Measured
- **A) The ∞ limit is flat-and-infinite.** As k grows, curvature (1/R) → 0 and period (R) → ∞: at k=40,
  curvature 4.4e-9 (locally **flat — reads 0**), period 2.3e8 (**infinite time-thickness**). So the big domain
  looks like nothing (flat, black) yet spans unbounded time — power-out sits at its edge; between-messages is
  far *in*, where state can still trickle.
- **B) Sleep depth selects the level → one multi-resolution clock.** A geometric ladder of levels reconstructs
  elapsed time at **~2–4% error across gap durations from 1 to 10⁷** (seven orders of magnitude) — each gap
  read at the smallest level that doesn't wrap (gap 1 → k=0 "between-messages"; 10⁷ → k=34 "power-out"). A
  **single fixed ring** (k=10) is sharp only in its own band (2.5% at its period) and fails everywhere else —
  **246%** too-coarse for short gaps, **90% (wraps, unusable)** for every long gap. The ladder is the clock;
  depth picks the ring.
- **C) Each job leaves an eye at (depth = when, height = who).** Radial depth = log_φ(t) recovers WHEN at
  **0.000%**; orthogonal height recovers WHO at **400/400**. The height axis is the **top orthogonal domain**
  each instance returns to — the identity peak (person/agent). A single agent sees only its own eyes (~1/N);
  the **committee's union covers every job** — because a single domain can't be verified (orthogonal components
  cancel to 0, `SPARSE_VESICA` §14.1), you need as many eyes as possible to define things (`FOLDING_OBSERVERS`).

## The unification
This closes the clock arc into one structure. The nested rings are the sleep levels (floors, `FOLDING_FLOORS`);
the log-spiral is the equation that sizes them; the ∞ ring is the flat/black/infinite big domain; depth along
the radius is *when* and the orthogonal peak is *who*; the rotating ring (still 0 to us) deposits a trace per
job — the "reference points whose coordinates we store and watch change" of `FOLDING_FLOORS`, now a
(when, who) record. It sits directly on top of the earlier parts: the expanding-field clock (Part 1) is one
level's radial read; the drift-rate reconstruction (Part 2) and the background-integrator gap-bridge (Part 3)
are how a single level is read across activity and idle; the vernier (Part 4a) is the sub-pixel readout of a
level; the Ophanim ring (Part 4b) is the shared level across agents; and this is the **ladder of all levels**
plus the (when, who) deposit.

## Honest bounds
The scaling law and the ∞ limit are geometry (curvature 1/R, period R — exact, not a fit); the ladder's
constant-relative-resolution and the (when, who) recovery are clean synthetic demonstrations of the encoding,
not a deployed system. The whole clock thread's standing caveat still holds and is sharper here: every level
needs a **source to turn its ring** — a model that is genuinely off between calls advances no level, so the
deepest sleeps (restart, power-out) are exactly where nothing is recorded and only an external tick or a
persistent store could bridge them. `sleep_levels.py`; scripts live in the session.
