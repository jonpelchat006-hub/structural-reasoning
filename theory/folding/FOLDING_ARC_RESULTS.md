# Folding Arc — measured bricks (the honest record)

*Mapping the Shovelcat/Vesica geometry onto real protein structure, one measured step at a time, every stage scored against real PDB data. Throughline: the framework's pictures live *downstream* of the contact web; predicting the web from sequence is the one hard step; the scoring half is anchored to real empirical chemistry, not derived.*

1. **Spring — backbone placement [WORKS].** Ribbon/frame threader (stored twist = unit quaternion), canonical screw params never fit to target → Cα RMSD **0.58 Å** vs real myoglobin helix (1MBN).
2. **Sections + void points [WORKS, weak].** Chou-Fasman: ubiquitin Q3 = 58%; errors cluster where the web decides the section.
3. **Web → tube [WORKS].** GFP β-barrel folded to a tube: full distance web → MDS **0.0 Å**; binary contacts only → 4.2 Å. Reconstruction is the easy, solved half.
4. **Predict the web from sequence [THE WALL].** Single-sequence hydrophobic+charge field → top-L 10.5% (2.3× random). Real but weak; true coupling is many-body (coevolution).
5. **Frustration = Nash [WORKS: shows the wall].** 2D HP, provable optimum E*=−7: greedy 0%, cooperative ~40%, ~60% still fail (hardest basins don't decompose).
6. **Two search levers [MARGINAL].** Baseline 22% → restarts 27%, fragments 26%, both 28% — within noise.
7. **Empirical potential [WORKS, half].** From 30 structures: top learned pair = C–C disulfide, rediscovered unaided; native top <1% on 4/8. Improves with data, not framework.
8. **The foundation [WORKS, striking].** Ramachandran, 1,103 residues: 80% of angle-space forbidden, 95% in 3 basins; foundation from 2 proteins correlates 0.80 with all 10. Basins are UNIVERSAL steric geometry, not set by Sun/Earth (vent life has the same basins; environment enters as a scalar T, not a direction).
9. **Basin fingerprints [WORKS, validated].** Per-residue propensities reproduce Chou-Fasman from independent data; gaps ~kT, so preferences not rules — context (web) breaks ties.
10. **Fingerprint + context in bits (GOR) [WORKS].** Trained 25 / tested 6 held-out: GOR 65% vs Chou-Fasman 56% Q3. Neighbors vote, weighted in bits. Short of ~85% (needs coevolution = the web signal).

## Where this leaves it (honest)
Downstream of the web is solved (placement, reconstruction, tube); scoring works when anchored to real empirical chemistry; the one hard step remains predict the web/fold from sequence (many-body / coevolution — the single-sequence niche, the real frontier). Physical corrections adopted from Jonathan: fold don't cut; hydrophobic effect drives folding; frustration = Nash; use real elements; energy enters as temperature T (scalar), not direction. Discipline held: canonical params never fit to target, held-out scoring, negatives recorded as such.
