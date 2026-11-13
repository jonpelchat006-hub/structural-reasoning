# polydisc v8: packed lanes (Oct 19, 2026)

`../Submission.lean` is the v8 submission (684 KB). It passes the strict build, uses only the
axioms `propext`, `Classical.choice` and `Quot.sound`, and the official local judge
(`evaluation/run.py`) accepts all six public cases.

## Files

| File | What it is |
|---|---|
| `PackDefs.lean` | Structured definitions of the packed run: `PSt`, `pstep`, `prepack`, `pinit`, `unpackT`, `prun` |
| `PackProofs.lean` | The proofs, from the E-argument through `pstep_spec`, `prun_spec`, the band theorems and `impl_correct`. Developed as `Dev.lean` importing `Base.lean`. |
| `gen10.py` | Graph generator; it mirrors `PackDefs.lean` op by op. Also writes the Lean text for each band: constants, `pkDagC` (lane constants as variables), `pkRhs`, the rfl links, `pkDag` (constants inside), `acts`/`init`/`pkRun`, and `pkDag…_struct`. |
| `mkbase.py`, `mkbands.py`, `mkfinal.py` | Assemble `Base.lean` (v7 + definitions + graphs) and the band theorems, then the single `Submission.lean`. |
| `robust.py` | Simulates the exact graphs on random inputs: 0 fallbacks in 3,000 D1 and 6,400 D3 inputs. |
| `search.py`, `seg.py`, `hybrid.py`, `packdag.py`, `cost.py`, `grid.json` | Lane-segment and switch-point search, using a GMP price grid. |
| `gmpcost.c`, `gmpgrid.c` | GMP oracle: prices operations with Lean's own `libgmp.a` under callgrind. |
| `prs_model.py`, `halfgcd_model.py`, `packed_model.py` | Python models of v7's PRS, the head/tail split, and the first packed estimate. |
| `bench_poly.py` | Replay-window bench, the same method as `bench_fib.py`. |
| `window_counts.txt` | Measured counts. |
| `merge.py` | Prototype that merges the generator and PRS graphs. It saved only 0.36M on D5, so it is not used. |
