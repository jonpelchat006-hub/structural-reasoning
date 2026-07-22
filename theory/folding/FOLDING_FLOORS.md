# The Floors — successive cuts CROSS, the next floor is a fresh cut, the C line survives coarse-graining, and the reference spots contract

*Companion to `FOLDING_PIXEL_STRAIN.md`, `FOLDING_TOWER.md` (nested bisection = algebra tower), `FOLDING_OBSERVERS.md` (1 real + 3 orthogonal observers = i/j/k), `FOLDING_STAIRCASE.md`, `SPARSE_VESICA_EXPANSION.md` §12 & §20.4, `SPHERE_GENERATOR.md` §J.6. Jonathan's extension: a golden field underneath; off-origin → a different segment shifting the cut; multiple floors that close off spaces; deformed pixels re-base into a fresh square on the 2nd floor; old C meets new C at an intersection (or parallel, multiple intersections); on a higher floor you can't read inside the pixels but the C line stays on the wall; spots the void lines are drawn to. Tested on the canonical 8; `test_e.py`, `test_f.py`, `test_gh.py`.*

## 1 — Old C meets new C: they CROSS, not parallel (CONFIRMED)
Angle between successive cut planes (primary domain-axis n₁ vs secondary sub-domain axis n₂): 1CLL 84.9°, 4AKE 80.0°, 1GD1 70.3°, 8TLN 67.9°, 2LZM 67.1°, 1PHP 51.4°, 6LDH 47.1°, 3PGK 46.0°. **Mean 64.3°; crossing (>55°) 5/8, parallel (<35°) 0/8.** The old C and new C intersect at a steep angle; none stack parallel. The crossing **leans orthogonal** — the quaternion i/j/k independent axes (each floor opens a new independent direction, Cayley–Dickson doubling).

## 2 — Does the 2nd floor re-use the 1st floor's leftover pixels? NO (NEGATIVE)
corr(level-1 mixedness, level-2 seam-ness) within the larger domain = **−0.07**. No inheritance — the 2nd floor is a fresh, independent cut through new buried core, not a re-basing of floor 1's leftovers forward.

## 3 — Reading across floors: the C line survives coarse-graining (blurry), the interior does not (CONFIRMED)
Coarse-grain into blocks of size b, re-cut, compare to the fine cut. Means b=1→12: **C-line survival** 1.00, 0.99, 0.97, 0.95, 0.94, **0.93** (chance ~0.56); **interior hidden** (pixels straddling the seam) 0.00 → **0.12**. The C line stays on the new wall and blurs only gently; the interior goes unreadable. Structural twin of the pLM depth-fade. 6LDH (most-knitted) blurs fastest.

## 4 — Do the lower C lines make a distinctive PATTERN on the next wall? NO (NEGATIVE)
Project C1 onto the C2 plane; line-likeness **0.764** vs random-residue null **0.776** (4/8 beat null). Proteins are globally elongated, so any projection looks striped — C1's shadow doesn't stand out.

## 5 — The reference spots persist and CONTRACT, but don't home on the ligand (MIXED)
Convergence spots per cut level, stored on shells: cut 1 sits innermost (mean radius **0.40**), deeper cuts outer (~0.76). Successive spots **contract** (S1→S2 > S2→S3 in **7/8**) — a settling trajectory, not a random walk. But they home on the bound ligand D in only **2/6** — the wall again (convergence ≠ functional site).

## Ledger
**CONFIRMED:** successive cuts cross (mean 64.3°, 0/8 parallel, leaning orthogonal = quaternion axes); the C line survives coarse-graining (0.99→0.93) while the interior goes unreadable; reference spots persist and contract (7/8). **NEGATIVE:** 2nd floor doesn't re-use leftovers (−0.07); no distinctive wall-stripe (0.76 vs 0.78 null); spots don't home on the ligand (2/6). **FRAMEWORK:** the golden field / off-origin segment stay Shovelcat-side substrate; the protein instance of "spots the void lines are drawn to" is D, the convergence point (`VOID_LINE_PAPER.md` §8).
