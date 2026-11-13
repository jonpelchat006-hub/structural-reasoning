# slotfill: the verified slot filler (Oct 21, 2026)

This is a static ARC-1 solver for **class C** tasks, where the output is the same size as the input and only background cells change. It is meant as an extra candidate source next to the TypeScript solver.

## How it works

1. **Features.** Each background cell gets a set of local features:
   - its 8 neighbours;
   - the first coloured cell along each of 8 rays;
   - "between" in each of 4 directions (horizontal, vertical and both diagonals);
   - whether it is enclosed, on a rim, and the size of its region;
   - its region's bounding box and whether the region is a rectangle;
   - 5 mirror symmetries;
   - the 2D period;
   - its count of non-background neighbours;
   - the nearest colour;
   - its row and column taken mod 2 and mod 3;
   - the set of colours in its row and in its column.
2. **Learning.** For a group of features (one group, or a pair of small groups), learn a table from the feature key to the output colour, using every train pair.
   - **raw** mode uses the colours as they are.
   - **abstract** mode relabels colours canonically and stores answers as "slot j", so a rule can transfer to a new palette.
3. **Verification.** A rule is a candidate only if:
   - the table never contradicts itself;
   - it reproduces **every** train output exactly;
   - it covers every key in the test input.

   If any key is unseen, the rule abstains rather than guessing.
4. **Trust.** Re-learn the rule with each train pair held out in turn, and check it predicts that pair. This is leave-one-out, kernel tier K2. Candidates are ranked with LOO-passing rules first, then smaller tables, then fewer features.

## Results (all 800 ARC-1 tasks)

| Split | Rule found | Correct | New vs verified list | Union | Class C solved | LOO-gated (trusted) |
|---|---|---|---|---|---|---|
| train | 26 | 26 | +13 | 81 → **94** / 400 | 15 → 28 | 25/25 correct |
| eval | 9 | 8 | +7 | 34 → **41** / 400 | 1 → 8 | 8/8 correct |

The only wrong answer was eval `9ddd00f0` (class B, rule sym_t+sym_at). Its rule did **not** pass LOO, so committing only trusted rules gives **100% precision on both splits**.

The rules that solved eval tasks:

| Task | Rule |
|---|---|
| 070dd51e | btw_h+btw_v |
| 332efdb3 | r2m+c2m |
| 45bbe264, a406ac07, e9c9d9a1 | rays 0–3 |
| 84f2aca1 | rsize |
| a8610ef7 | sym_v |
| aa18de87 | btw_h |

All of them are abstract mode and pass LOO.

**What is left.** 83 of the 91 unsolved eval C tasks have **no** consistent rule in this feature space. Their outputs depend on objects, sizes, counts and paths rather than local neighbourhoods. More local features won't reach them; object-level slots would.

## Files

| File | Purpose |
|---|---|
| `slotfill.py` | Features, learn/predict, `solve(task)` |
| `evaluate.py` | Per-class table for train and eval; writes `eval_detail.json`. Run `python evaluate.py [train\|eval]` |
| `export.py` | Writes `slotfill_predictions.json`: per task the rule, mode, `trusted` (LOO) and up to 2 attempts |
| `diag.py` | For unsolved C tasks: whether no rule is consistent, or only coverage fails |
| `show.py` | Prints a task's first train pair as text |
| `arc_levels.py` | The class labels (A–F) |
| `train_tasks.json`, `eval_tasks.json` | The 400+400 tasks as single files (the solver's data/ and data-eval/) |

Requires Python 3 and numpy. The evaluation takes about 6 minutes on 2 cores.

`_wtest_empty` is an empty file left over from a write test. It is safe to delete.
