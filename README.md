# Structural Reasoning — an independent research program

*Work in progress. Independent, self-funded, no institution.*

*November 2026: the rest of the program has been gathered here too. **[RESEARCH_MAP.md](RESEARCH_MAP.md)** is the
index to everything: every thread, what was measured, what is design or speculation, and where each piece lives.*

This repository collects an ongoing attempt to understand reasoning, folding, and structure
**from the bottom up** — starting from a geometric/first-principles framework and testing every
claim against real data. It spans three connected threads: a **model-free ARC-AGI solver**, a
**protein-folding + protein-language-model** study of where local knowledge hits a nonlocal wall,
and the **Shovelcat / vesica** theoretical framework the other two grew out of.

The stance throughout is one thing: **name the claim, test it, and believe the number — even when
the number bounds the idea.** Every empirical result here is reported with its baseline and its
ceiling. Where something does not beat a trivial baseline, that is said plainly. The theory is
included in full, and clearly separated from what has been measured.

---

## The three threads

### 1. Model-free ARC-AGI solver
An [ARC-AGI](https://arcprize.org/) solver that uses **no language model anywhere** — it perceives
each task as a structured signature, retrieves related solved tasks by resonance, and reasons by
bending a flexible program against the hard constraint of the worked examples. Reaches **66/400
(16.5%) on train**, every solve generalizing to the held-out test pair, with the ceiling mapped
three independent ways. Not competitive with the heavy-machinery top of the leaderboard; the point
is that a fully model-free, interpretable, online-learning system reaches this at all and
*understands its own ceiling*. (Solver source: [`arc-agi-1/`](arc-agi-1/); the task files are not included.)

### 2. The folding thread — local vs. nonlocal, measured (this repo runs today)
The same question — *what is local and knowable vs. global and hard* — worked cleanly in protein
folding, tested against real PDB structures and a protein language model (ESM2). This is **not novel
biology**; it re-derives known structural facts *from scratch, by feel*, and maps exactly where the
"wall" sits. Highlights, all reproducible from `code/`:

- **The domain boundary is a flat plane made of absence** (the contact gap), ~85–98% linearly
  separable; the two faces are complementary shape/charge imprints.
- **The cut recurs** — nested bisection produces a fresh interface at every level; successive cuts
  **cross near-orthogonally** (the quaternion i/j/k frame), and the seam **survives coarse-graining**
  (blurs gently, 0.99→0.93) while the interior goes unreadable.
- **The wall:** the interdomain seam carries *no local signature*; no per-residue descriptor — or
  per-residue pLM read — ranks it above chance. The honest route past the wall is the pLM's
  **pairwise contact web** fed into a global min-cut, which recovers the cut (~0.84) and its
  recursion (fading with depth).
- **A foldability ledger (supply vs. demand):** the fold *demands* a definite interface budget
  (~36% of residues; a ~0.2×L path budget), and the *sequence supplies* one, read through the pLM.
  Scrambling the sequence collapses supply "over budget"; the supply margin is **graded**, **ranks
  designed folders above failures (AUC 0.73)**, **tracks 650 real experimental ΔΔG stabilities
  (S669; Spearman +0.19–0.21)**, and **scales with model size** (8M→35M doubles it to +0.36 on a
  fixed subset — the small-model number was a floor, not a ceiling).

The `notebooks/` folder has a **one-click Colab** that reruns the S669 calibration on a free GPU with
a large ESM2 model — the fair number this repo's author could not reach on a 2-core CPU.

### 3. The Shovelcat / vesica framework *(theory, included in full)*
The geometric framework the above grew from: a dual-domain (ψ/φ) vesica construction, a closure
equation `x² = x + k` whose unit `k=1` forces the golden field ℚ(√5), a recursive "tower" that maps
to the Cayley–Dickson algebra ladder, and a geometric derivation of the fine-structure constant.
This is **speculative and self-contained**; it is presented as the *origin and motivation* of the
tested work, not as established physics. It lives under `theory/framework/` with its own results
files, so the reproducible science and the framework are never confused for one another.

---

## The rest of the program (consolidated November 2026)

The three threads above were the first. Everything else the program produced is here as well, as it stood on
the author's machine: source and write-ups only, without data dumps, model files or anything private. Each
folder has its own README with a file-by-file index, and **[RESEARCH_MAP.md](RESEARCH_MAP.md)** ties them
together.

| Folder | Thread |
|---|---|
| [`agi/`](agi/) | the cognitive-architecture ("baby brain") experiments |
| [`detector/`](detector/) | the AI-image detector: measurement code and design docs |
| [`critical-line/`](critical-line/) | the critical-line paper and its numerical labs (no proof claims) |
| [`arc-agi-1/`](arc-agi-1/) | source of the model-free ARC-AGI-1 solver (thread 1 above) |
| [`arc-agi-3/`](arc-agi-3/) | the ARC-AGI-3 work: the planet, PriorAgent, the hybrid, the core card |
| [`alignment/`](alignment/) | "alignment as water": design notes, with tests in `arc-agi-3/planet/` |
| [`mika/`](mika/) | the Mika agent's own folder: daily runs, diary, library tools |
| [`qtube/`](qtube/) | the nested-quaternion model |
| [`navier-stokes-theta/`](navier-stokes-theta/) | Navier–Stokes theta experiments, with their own claim ledger |

Related public repositories: [pvsnp-lean](https://github.com/jonpelchat006-hub/pvsnp-lean) (a kernel-checked
Lean library around P vs NP, which is open and which nothing there claims to resolve, plus the floor_flow
experiments), [erdos-incidence-geometry](https://github.com/jonpelchat006-hub/erdos-incidence-geometry),
[Shovelcat-Alpha](https://github.com/jonpelchat006-hub/Shovelcat-Alpha) and
[Shovelcat-Security](https://github.com/jonpelchat006-hub/Shovelcat-Security) (earlier scripts).

---

## Repository layout

```
code/        Python scripts — the folding + pLM pipeline and every test/figure in thread 2
data/        S669 stability benchmark (ddG); PDB structures fetched by code/fetch_pdb.sh
results/     Saved .npz outputs from the runs (so figures reproduce without recompute)
figures/     Every figure referenced below, regenerable from code/
theory/
  folding/   The FOLDING_*.md idea-record + honest-ledger docs, and VOID_LINE_PAPER.md
  framework/ The Shovelcat / vesica / sphere-generator framework and the ARC-AGI-1 result logs
notebooks/   colab_s669_calibration.ipynb — free-GPU big-model calibration

agi/  detector/  critical-line/  arc-agi-1/  arc-agi-3/  alignment/  mika/  qtube/  navier-stokes-theta/
             The other threads, each with its own README (see RESEARCH_MAP.md)
```

## Reproducing thread 2 (folding + pLM)

```bash
pip install -r requirements.txt
bash code/fetch_pdb.sh              # downloads the 8 canonical PDB structures
python code/pipeline.py             # domains, seam, deformation (Test A)
python code/test_l.py               # the interface "blanket" budget
python code/test_o.py               # S669 calibration vs measured ΔΔG (ESM2-8M)
python code/test_wt.py esm2_t33_650M_UR50D 650M 1022   # the fair big-model run (GPU recommended)
```
The 8 two-domain proteins throughout: **1CLL, 3PGK, 1PHP, 1GD1, 6LDH, 8TLN, 4AKE, 2LZM**. The
recurring exception in nearly every test is **calmodulin (1CLL)** — a floppy dumbbell with no real
interface — which is used as a built-in negative control.

## The honest ledger

Each `theory/folding/FOLDING_*.md` ends with a CONFIRMED / CORRECTION / NEGATIVE / FRAMEWORK ledger.
Several of this program's most-liked ideas came back **corrected or refuted** by the data (e.g.
"folding folds the seam out" → folding *creates* it; "deformed pixels are the next cut" → the cut
rides rigid buried core; "the cut ratio is golden" → it's generic to bisecting compact shapes). Those
are kept, not hidden — they are the point of the method.

## Status & how to help

The reproducible folding/pLM thread runs today. The two things it can't reach on the author's
hardware (2-core CPU, no GPU) are: **(a)** the large-ESM S669 calibration — the Colab notebook does
this on free GPU; and **(b)** a fold/no-fold *probability* predictor, which wants the Tsuboyama 2023
mega-scale dataset. Contributions on either are welcome. The ARC solver source is in `arc-agi-1/`.

## On the author
Independent researcher, no formal affiliation; self-taught and self-funded. Put here in the open
because ideas should be judged by whether they hold up, not by whose name is on them.
