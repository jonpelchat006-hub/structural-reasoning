# The fusion reactor comes home — contained heat turns light rules into heavier elements

*Sep 1 2026. Jonathan: "we did have a fusion reactor built already — let's find that." Found:
Shovelcat-DNA/fusion_reactor.py (Feb 2026, 44KB) — the Fusion Reactor Training System:
thermal containment for leveling up safely and privately. Tokamak (slow, steady,
mentor-guided x0.8), NIF (intense burst, multiple validators x2.0), Stellarator (twisted
path, self-sustaining x1.0); entry minimum 0.3, heating by action, cooling by neglect,
privacy walls with internal/external views, and exit ONLY when the BEC threshold (1.0) is
firmly crossed. "Let's do that" — ported the same day as fuse.py.*

## 1. What it closes

The abundance measurement (ARC_ATP §2 follow-up, ARC_PLAYGROUND §2) gave the planet its
element table — counter.up as hydrogen at 48.5%, a cosmic-shaped falloff — but no pathway
from light species to heavy ones. The February reactor is exactly that pathway: fusion =
containment + sustained heat above threshold. And its three types were already running here
unnamed: the escalating bell is a Tokamak, the duet is NIF, the drift-and-fold is a
Stellarator. Where the dark planet's heat ring BURNS stuck heat, the reactor CONTAINS heat
until it binds — the constructive counterpart of forgetting.

## 2. The port (fuse.py), law by law

- COLLISION: two concepts in one world's core sharing an atom are touching — the only place
  fusion can start. Transient contact cools away.
- ADMISSION costs 1 ATP: containment is paid with verified past work — the metabolism now
  gates element-building. Routing keeps the taxonomy, measured: overlap >= 2 atoms =
  tokamak (close kin); overlap == 1 = stellarator (a bridge between families); both parents
  recovered in a stored teach-back = NIF (two validators already reached them — the burst
  is earned).
- HEAT/COOL: each sleep both parents still standing in the live core heats the pair
  (0.1 x type multiplier); a vanished parent cools it; cooled to zero aborts, logged.
- THE WALLS: the whole process lives in forge/reactor.json — invisible to the witness, the
  storyteller, and the ring until threshold. Failures in the reactor are private, exactly
  as the February design demanded (and exactly the practice-before-try law arc_daily
  already enforces at the planet scale).
- BEC CROSSED: the union of the parents' atoms exits as ONE heavier species — landing on
  the RING (kind "fusion", golden-angle placement, pointers to world + parents) and in
  forge/fused.json. Parents are never deleted (fusion adds mass; forgetting stays the dark
  planet's job); same-or-better holds by construction (the fusion carries every parent
  atom). THE IRON LINE: a fusion exceeding 5 atoms is rejected — beyond iron, fusion costs
  instead of pays (iron_terminus.md's attractor, honored as a hard cap).

## 3. Verified, then lit for real

Synthetic: touching pairs warmed to entry, admissions drained a seeded ledger 8 -> 0,
tokamaks and stellarators routed correctly, six elements fused across ~10 passes and landed
on the ring at golden angles with parent pointers; pairs without ATP waited outside. (The
test also caught a real bug: one malformed ledger line silently zeroed the whole ATP
balance — _rows now skips bad lines individually.)

Live on the PC, first pass: 3,234 collisions across the real cores; 5 pairs admitted — the
planet spent its ENTIRE treasury (all 5 ATP, minted at three different seams) on
containment; five stellarators now heat in battle_net at 0.40; 3,022 pairs warm outside
waiting for future verified wins to pay their way in. To fuse more, the planet must first
verify more: energy earned at seams becomes structure, which is what a metabolism is FOR.

## 4. Falsifiable core

Fused species must earn their keep the way any concept does: a fusion whose parents keep
co-occurring after exit was real chemistry; one whose parents drift apart was a coincidence
the reactor overpaid for — the fused.json passes count and the parents' subsequent core
history hold the audit. If containment routinely outbids the forge's extended rotations and
antenna rates stagnate, the mint prices are wrong (reprice, never print). And the iron line
is measurable: if 5-atom fusions systematically stop recurring while 3-atom ones persist,
the cap is confirmed from data; if heavy fusions thrive, the line moves.
