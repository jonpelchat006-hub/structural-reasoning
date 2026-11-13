# ARC — the verified slot filler (Oct 21, 2026)

**Context.**
- Jonathan, Oct 21: *"you can start with the static solver. we should probably do the arc stuff more too with the closer deadline"*.
- This is the Mika upgrade I recommended: propose, verify on every train pair, otherwise fall back.
- It is built for the ARC-1 static solver in `D:\shovelcat-colony\arc-slice`.

**Code.** Python, in `arc-slice/slotfill/`. Start with the README there.

## Idea

For **class C** tasks (same size, only background cells change), learn one lookup table per background cell, from a feature key to the output colour.

**Features:**
- 8 neighbours
- 8 rays, giving the first colour hit in each direction
- "between" horizontally, vertically and on both diagonals
- enclosed / rim / region size and bounding box
- 5 mirror symmetries
- 2D period
- neighbour count
- nearest colour
- row and column mod 2 and mod 3
- the colour sets of the cell's row and column

**Modes:**
- **raw**: colours as they are.
- **abstract**: canonical relabelling, with answers stored as "slot j" so a rule transfers to a new palette.

**Verification is the point.** A rule is a candidate only if:
- its table is consistent;
- it reproduces **every** train output exactly;
- it has seen every test key.

Otherwise it abstains. Leave-one-out re-induction (kernel tier K2) decides trust and ranking.

## Results (ARC-1, 800 tasks)

| Split | Rule found | Correct | New | Union with solver | Class C | Trusted (LOO) |
|---|---|---|---|---|---|---|
| train | 26 | 26 | +13 | 81 → **94** | 15 → 28 | 25/25 correct |
| eval | 9 | 8 | +7 | 34 → **41** | 1 → 8 | 8/8 correct |

**Precision.**
- The one wrong answer was eval `9ddd00f0`: class B, rule sym_t+sym_at, and it did not pass LOO.
- Committing only LOO-passing rules is **100% precise on both splits**.

**What solved eval.** Rays (3 tasks), btw_h+btw_v, btw_h, r2m+c2m, rsize, sym_v. All are abstract and all pass LOO.

**A default-to-background mode for unseen keys** added false positives, so it is off.

## What it tells us

- **The ceiling of local rules.** 83 of the 91 unsolved eval C tasks have **no** consistent rule in this feature space. Their outputs depend on objects: sizes, counts, sequences, paths.
- The next gain needs **object-level slots**, keyed per object rather than per cell. More cell features won't get there.
- The verify-and-abstain pattern carries over unchanged to ARC-AGI-3:
  - a hypothesis about a game's mechanics is only acted on once it reproduces the observed frames;
  - LOO over the observed transitions decides trust.

## Files

**On the PC:** `arc-slice/slotfill/`
- `slotfill.py`, `evaluate.py`, `export.py`, `diag.py`, `show.py`
- `slotfill_predictions.json`: per task the rule, mode, trusted flag and 2 attempts, for the TS solver to import
- `eval_detail.json`
- `README.md`
