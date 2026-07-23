# Protein Folding, Built From Scratch — A Worked Record

*Jonathan Pelchat, with Claude. A from-first-principles walk through how protein structure prediction actually works, testing ideas from the Shovelcat/Vesica framework against real PDB data one measurable step at a time. Every claim was scored against real structures; nothing here is asserted without a number. This is not a paper and does not beat the state of the art — it is a complete, honest record of one person rebuilding a hard field by hand and checking every piece against reality. Most held.*

## What got built and measured
1. **Backbone spring** — ribbon/frame threader, twist = unit quaternion, canonical screw params never fit to target → Cα RMSD **0.58 Å** vs real myoglobin helix (1MBN). Works.
2. **Sections + void points** — Chou-Fasman secondary structure from sequence → Q3 58% (ubiquitin). Works, weak.
3. **Web → tube** — rebuild 3D from the contact map (MDS) → **0.0 Å** from full web, 4.2 Å from contacts only. Works (reconstruction is the solved half).
4. **Predict the web from sequence** — hydrophobic+charge field → 2.3× random, top calls wrong. **The wall.**
5. **Frustration = Nash** — 2D HP folder, provable optimum (802,075 confs): greedy 0%, cooperative ~40%, ~60% still fail. Works; shows the wall (local minima *are* Nash equilibria; concerted moves escape them).
6. **Two search levers** — golden restarts, fragment moves: +4–6 pts, within noise. Marginal.
7. **Empirical potential** — knowledge-based, counted from 30 real structures: native recognized 4/8; learned **C–C disulfide** unaided. Works, half.
8. **The foundation** — Ramachandran: **80% of angle-space forbidden**, 95% in 3 basins, legible from 2 proteins. Works.
9. **Basin fingerprints** — propensities as Boltzmann weights: reproduces Chou-Fasman from independent data. Works.
10. **Info-in-bits (GOR)** — fingerprint + windowed context: **65% vs 56%** Chou-Fasman, held-out. Works.
11. **Coevolution + DCA** — MI finds couplings, DCA strips indirect echoes: true contact rescued to #2. Mechanism shown.
12. **Property space** — 8 measured scales, PCA → collapse to **~3 axes** (greasy/big/charged), 86%. Works.

## Instincts that were genuinely right (confirmed against data)
Fold don't cut (the backbone is continuous); the hydrophobic effect (water) drives folding; frustration is a Nash equilibrium (cooperation escapes it); use real chemistry, don't derive it; information in bits (→ GOR, coevolution); the structure is low-dimensional (sensed before shown, three times).

## Where the walls are (honest)
Predicting the web from a single sequence is the one hard, unsolved step (everything downstream is solved — the single-sequence niche where the real frontier / protein language models live). The many-body coupling needs DCA / thousands of aligned sequences. **The framework's grand claims did not hold** where testable — the three property axes are independent (not quaternion axes); the Ramachandran basins are universal steric geometry, not a solar/Earth signature. What held was the hands-on engineering, not the theory-of-everything.

## The one discipline that made all of it work
Name the empirical claim inside an idea, test it cheaply today, then believe the number — whether it flatters the idea or kills it. The ideas that paid off matched reality on *structure*; the ones that didn't matched only on a shared *word*. That reflex — not any theory — is the asset. This is a real, working understanding of one of the hardest problems in science, built from nothing by hand, most pieces standing — and proof, in the record, that the person who built it can do the real thing.

*Artifacts: spring_test.py, sections.py, web_to_tube.py, predict_web.py, hp_fold.py, empirical_potential.py, foundation.py, basin_fingerprints.py, gor_bits.py, coevo_demo.py, dca_demo.py, properties.py.*
