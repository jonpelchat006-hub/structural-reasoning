# The map — game-agent runtime, ARC solver, and time, connected back (session synthesis)

*Session Aug 2026. Summary of the recent stretch and how the three tracks are one thing. Visual version:
`shovelcat_map.html` (delivered; pin as an artifact when the desktop is connected). Per-topic detail in the
docs named at the end. Everything below is an exact measured result from a runnable script unless flagged.*

## The spine
A three-shell brain — **inner** (innate, read-only), **middle** (learned, the only writable layer — where the
notes/void-store live), **outer** (environment + void) — actuated as an underactuated arm, reasoning by the
**φ/ψ/void triad** (classical definite path / quantum meaning-superposition / orthogonal residual), verified by
a **committee** (agreement = the invariant; a single domain can't be verified).

## Track 1 — the game-agent runtime (from Jonathan's play)
The loop: perceive+surprise → probe→define → segment (re-based void) → induce operators → ψ mean (DAG) →
φ collapse (staged, gated) → execute & burn → re-collapse on break. Measured facets:
- **probe-first** vs goal-rush: **6% → 98%** success (`ARC_PROBE_FIRST`).
- **staging** (place-then-fill): product→sum, up to **10,900×** fewer expansions (`ARC_STAGED_ARMS`).
- **accretion** (+blue → opposite-grey → horseshoe → impassible): **6% → 57%, 0 wrong** (`ARC_INTERACTIVE_PLAY`).
- **two planes** (φ path / ψ DAG): fan-in to **417**, rotate-on-break **85% vs 64%**; + middle-shell notes,
  recursion-level scope, **type-generalization 1.5–3.6×** (`ARC_TWO_PLANES`).
- **assembled ψ↔φ loop**: **0% → 95.3%** vs a memoryless agent (`ARC_GAME_LOOP`).
- **surprise** = prediction error: **0 en-route / 1 at goal**; monitor **88 → 96%** (`ARC_PERCEPTION_SURPRISE`).
- **void** = alignment residual → 0, predicts change **IoU 0.98** (`ARC_VOID_DOMAIN`); **re-based per shell**
  0% → **93.8%** on inner squares (`ARC_RECURSIVE_VOID`); **operator-induction by interaction 100%, 0 false**
  (`ARC_OPERATOR_INDUCTION`); **fill-void** 26% → **100%** vs discard stuck 26% (`ARC_VOID_FILL`);
  **imagination-paint** reached 1 circler the pipeline missed (`ARC_PAINT_VOID`).

## Track 2 — the ARC solver (the same engine, on the benchmark)
- **Op-generation ladder** (`ARC_OPGEN`): v1 7.0%/0.2% → arm+induction+prior 8.5%/0.8% → Set A 10.2%/1.5% →
  Set B 11.0%/**2.0%**. **Eval 0.2% → 2.0% (10×)**, every solve exact and train-gated, zero memorization — a
  generator stores a *procedure that reads the task*.
- **Drones**: mean 5.7 programs/solve (≤38); agreement = confidence (`ARC_DRONES`). **~90 circlers** each one
  local op away.
- **Self-generated hypothesis** (`ARC_HYPOTHESIS_TEST`): **P1 holds** (residual small & local, 5.5%, 3 comp),
  **P2 fails** (drone-disagreement ≠ residual — near-misses share a blind spot). The refutation redirected the
  build. **Set C** (global ops) was a diagnosed null — wrong scope.
- **Honest ceiling**: every mechanism works; the wall is **generation-family breadth** (~6% INK_ADDED), not the
  mechanism. Grind, honestly, pointed by the frustration map.

## Track 3 — time (the clock the agent was missing)
- **Expanding field** (`ARC_MEMORY_CLOCK` P1): gap→age **corr 1.00**, radial order→timeline **τ 0.997**
  (rate-free), thickness→duration **1.00**; old memories blend (human-like).
- **Two clocks** (P2): active time via drift-rate **exact**; idle gap the blind spot.
- **Bridge the gap** (P3): a background integrator (body-like) **68% → 14%**, committee of clocks **→ 8%**; a
  single clock saturates (honest bound).
- **Vernier + Ophanim** (`ARC_VERNIER_CLOCK`): far-anchor lever err **∝ 1/D**, non-disruptive sub-pixel readout;
  a shared far ring gives cross-agent time **τ 0.997 vs 0.84** local; intermittent eyes cover the timeline.
- **Sleep levels** (`ARC_SLEEP_LEVELS`): log-spiral ladder, **∞ level flat + infinite**, depth selects the ring
  (~3% over 10⁷), each job an eye at **(when, who)**.

## The connections back (the through-lines)
1. **The void is one object, many jobs** — driven to 0, re-based to the parent fill, filled with hypotheses,
   painted by imagination, read as radial time. Perception, memory, and the clock are the same residual.
2. **Agreement is the invariant** — drones, void-fill intersection, the shared ring (far = all agree), the
   committee of clocks. A single domain can't be verified.
3. **The game track and ARC track are one engine** — op-generation from train pairs and operator-induction by
   interaction are the identical move (synthesize from paired evidence, keep what reproduces, use forward). The
   piece that reads a live screen is the piece that solves ARC.
4. **Mechanism works; breadth is the climb** — proven both places; honesty is the method (a hypothesis
   half-failed and pointed the next build).
5. **Everything that runs needs a source** — the clock's deepest truth: the architecture can represent, read,
   and share time across ms→years, but a model off between calls winds none of it. Time, like the outer shell,
   is given, not innate.

## Honest ledger
ARC = exact held-out solves, train-gated (real). Game-loop + clock = clean measurements on synthetic testbeds
built to isolate each mechanism; operators/definitions are often handed, not learned from raw pixels; the
physiological/vernier clocks are design proposals; no claim about the live ARC-3 env (not loaded). The value is
the mechanism map — where each holds and where it breaks.

## North star & next lever
One learn-from-what-you-give-it agent, different outer shells (ARC → streamer → in-game AI → researcher). This
stretch built the shared runtime, showed it is the ARC engine, and gave it a clock. **Next honest lever:** wire
the recursive-void segmentation onto real rendered pixels (close the perceive→induce loop on a screen), and
grind generative op-breadth against the 90-circler frustration map. Docs: `ARC_PROBE_FIRST`, `ARC_STAGED_ARMS`,
`ARC_INTERACTIVE_PLAY`, `ARC_TWO_PLANES`, `ARC_GAME_LOOP`, `ARC_PERCEPTION_SURPRISE`, `ARC_VOID_DOMAIN`,
`ARC_RECURSIVE_VOID`, `ARC_OPERATOR_INDUCTION`, `ARC_VOID_FILL`, `ARC_PAINT_VOID`, `ARC_OPGEN`, `ARC_DRONES`,
`ARC_HYPOTHESIS_TEST`, `ARC_MEMORY_CLOCK`, `ARC_VERNIER_CLOCK`, `ARC_SLEEP_LEVELS`. `shovelcat_map.html`.
