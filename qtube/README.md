# Q-tube: the nested quaternion model

Experiments with a model built from nested quaternions, run against the official local ARC-AGI-3 engine
(November 2026). The picture behind it: each node carries a quaternion, the cube it sits in is its octonion,
and the bridge to the agent's core is where the sedenions, and their zero divisors, appear.

From `ACTIVE_GAME_AGENT.md` (Nov 1 2026): the active branch completes the first public `ls20` level in 25
official engine actions with zero resets, across three model seeds, using no language model, saved
demonstration route, supplied display crop or target coordinates. The same document says what this is:
development on a known public level.

**Status:** early experiments on one public game. Run outputs are not included.

## Files

**``**

- [`ACTIVE_GAME_AGENT.md`](ACTIVE_GAME_AGENT.md) — Active quaternion agent: first real level
- [`LITERATURE_GAPS.md`](LITERATURE_GAPS.md) — QTUBE: literature gaps and the next executable experiment
- [`REAL_GAME_LOOP.md`](REAL_GAME_LOOP.md) — Observed contact learning in the real ARC engine
- [`ROUND6_NOTES.md`](ROUND6_NOTES.md) — Quaternion model: round 6, November 1, 2026
- [`cayley.py`](cayley.py) — cayley.py - Cayley-Dickson doubling (reals -> complex -> quaternions -> octonions -> sedenions) and a check of where
- [`qbootstrap.py`](qbootstrap.py) — Bounded, demonstration-free acquisition of an observed contact transition.
- [`qbridge.py`](qbridge.py) — qbridge.py - round 5b (Nov 1 2026): the sedenion bridge on top of the flat-object quaternion nodes.
- [`qbudget.py`](qbudget.py) — Infer a consumable strip from observation history, without game-specific rules.
- [`qcompose.py`](qcompose.py) — Frozen qtube orientation/action-composition diagnostic (no encoder training).
- [`qeffects.py`](qeffects.py) — Evidence-scoped discrete glyph effects, without game code or engine actions.
- [`qengine_rpc.py`](qengine_rpc.py) — JSONL worker for the public ARC-AGI-3 OFFLINE engine.
- [`qgame_loop.py`](qgame_loop.py) — Bounded real-engine contact learning and verified goal-directed execution.
- [`qlift.py`](qlift.py) — qlift.py - round 4 (Nov 1 2026): the picture enters her space as a flat object, and a mirror is the same thing moved.
- [`qmoments.py`](qmoments.py) — Frozen-attention pose diagnostic: quaternion means plus second moments.
- [`qnav.py`](qnav.py) — Frame-only local navigation hypotheses learned from observed body motions.
- [`qports.py`](qports.py) — Round 6: can distinct object/socket ports make the bridge useful?
- [`qrecording.py`](qrecording.py) — Read observed ARC-3 recordings and locate a demonstrated object contact.
- [`qscene.py`](qscene.py) — Frame-only enclosed-glyph candidates for an experimental ARC-3 goal.
- [`qtest.py`](qtest.py) — qtest.py - the first test of the nested quaternion model (Nov 1 2026). See NESTED_QUATERNION_MODEL.md.
- [`qtransition.py`](qtransition.py) — Observed contact laws: learned quaternion poses plus exact evidence support.
- [`rivers.py`](rivers.py) — rivers.py - where a trained nested model builds (Nov 1 2026). See NESTED_QUATERNION_MODEL.md, "Rivers, bridges and the web".
- [`run_r3.py`](run_r3.py) — run_r3.py - round 3 (Nov 1): mirror turns + the river map. Stops starting new parts after 11:38 local
- [`run_r5.py`](run_r5.py) — run_r5.py - round 5 (Nov 1): 5a spread-out nodes in the flat-object model, 5b the sedenion bridge on quaternion nodes.
