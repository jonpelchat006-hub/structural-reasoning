# Alignment as water

Design notes for an alignment scheme anchored on the water cycle rather than on information flow alone, with
the small simulations that were built to test parts of it. The starting proposal is Jonathan's (Sep 18 2026):
put the planet at the top of the hierarchy, require the water cycle to stay intact at every level, and treat
humans and AI as the bottom two levels; keep a survival floor separate from a growth region; an AI defers on
growth choices and refuses actions that break the floor.

The code for the tests is in [`../arc-agi-3/planet/`](../arc-agi-3/planet/) (`alignment_*.py`,
`experiment_alignment_*.py`, `test_alignment_*.py`), with one results file per experiment
(`ALIGNMENT_*_RESULTS.md`). `tower_map.png` is the tower drawn as a map.

**Status:** design notes and toy-model tests. Nothing here has been tried on a deployed system.

## Files

**``**

- [`ARC_ALIGNMENT.md`](ARC_ALIGNMENT.md) — Alignment as Water — the planet's water cycle is the anchor, information is what the water carries
- [`ARC_ALIGNMENT_GRID.md`](ARC_ALIGNMENT_GRID.md) — The Alignment Grid — bars are people with closed cycles; a task's votes are the domains it crosses
- [`ARC_ALIGNMENT_PHASES.md`](ARC_ALIGNMENT_PHASES.md) — The Five Substrates on the θ Ladder — and the tower rotated into a map
- [`ARC_ALIGNMENT_REFUSAL.md`](ARC_ALIGNMENT_REFUSAL.md) — Test 3: the refusal battery, plus perspective slots on the Cayley–Dickson ladder
- [`ARC_ALIGNMENT_REVIEW_SEP22.md`](ARC_ALIGNMENT_REVIEW_SEP22.md) — Review of the Sep 19–22 alignment work — what landed, what drifted, what to run next
- [`ARC_ALIGNMENT_TESTS.md`](ARC_ALIGNMENT_TESTS.md) — Testing the Alignment Tower — seven measurements, what each would falsify, and the order to run them
- [`ARC_ALIGNMENT_WITNESS.md`](ARC_ALIGNMENT_WITNESS.md) — The Witness — model makers witness the instrument, not the act; and the same family is the weakest witness
