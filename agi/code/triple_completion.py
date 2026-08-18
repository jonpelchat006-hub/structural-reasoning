#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
triple_completion.py -- completing a half-truth = finding the 3rd point of a balanced triple.

Jonathan: this is like setting up the TRIPLES in the Erdős work. If there's an optimum, we
should be able to set it up from ANY starting point in an overall optimum structure. Looking at
the Green–Tao structure with its lines connected: put a point on a line and use it as the ORIGIN
for a smaller structure. And finding the INVERSE is like starting with 2 points and finding the
3rd.

Grounded — the corpus already did this exact problem (`Shovelcat/erdos-Fk/`, `orchard_phi_check.py`):
  * The ORCHARD-PLANTING problem: place N points to maximise 3-point lines (collinear TRIPLES).
    For 11 points the optimum is t₃(11) = 16, and its coordinates live in the golden field ℚ(√5)
    — pure powers of φ (P5.y = 1/φ, P2.y = 1/φ³). The √5 is the discriminant of the closure
    equation x² = x + 1 (SPHERE_GENERATOR §J.6).
  * TWO POLES (SPHERE_GENERATOR_TEST E): resonance/STRUCTURE (commensurate grid → many lines) vs
    independence/SPREAD (the golden ANGLE → 0 aligned triples). The optimum is STRUCTURE first, then
    a minimal golden-EXACT tail. Knot + tail: 12 lines on a rational lattice + 4 that live ONLY in
    ℚ(√5) and can't be approximated (Test F). Each golden point is TRIANGULATED by two rational
    corners (Test G) — "given two, the third is forced."

MEASURED (the abstract version, fully verifiable):
  (1) THE INVERSE — one point leaves the balancing 3rd FREE (a half-truth, undetermined); two
      points FORCE it (c = 2b − a, exact). Determinacy 0 → 1.
  (2) SET UP FROM ANY START — the optimum is CLOSED under triple-completion and HOMOGENEOUS: an
      arithmetic/lattice set has 2b−a landing back on a point (high closure) and ~uniform
      triples-per-point (any point is a valid origin); a golden-angle/SPREAD set is triple-sparse
      (completions leave the set) — the orchard's structure-vs-spread poles.
  (3) SELF-SIMILAR NESTING — a golden set maps to itself under φ-scaling: each point is the origin
      of a φ-scaled smaller copy (overlap peaks sharply at φ), the orchard's ℚ(√5) self-similarity.
"""
import numpy as np
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

PHI = (1+5**0.5)/2

# ---------- (1) the inverse: 1 point free, 2 points force the 3rd ----------
rng = np.random.default_rng(0)
b = 0.5                                            # the void / balance point (midpoint of the triple)
# one point known (only b): the pair (a,c) with a+c=2b is a 1-parameter family → 3rd is FREE
ds = rng.uniform(-0.4, 0.4, 4000)
thirds_1pt = b + ds                               # c = b + d, with d free  → spread out
# two points known (b and a): c = 2b − a is forced
a_known = b - 0.3
third_2pt = 2*b - a_known
determinacy_1 = 0.0
determinacy_2 = 1.0
print("="*80)
print("  COMPLETING A HALF-TRUTH = FINDING THE 3rd POINT OF A TRIPLE (the Erdős orchard)")
print("="*80)
print("  (1) THE INVERSE (start with points, find the missing one):")
print(f"        1 point known (the void b): the balancing 3rd is FREE — std {thirds_1pt.std():.2f} (undetermined half-truth)")
print(f"        2 points known (b and a)  : the 3rd is FORCED — c = 2b−a = {third_2pt:.2f} exactly (std 0)")
print(f"     -> a half-truth is one point of a triple; its OPPOSITE completes the pair; two points fix the third.")
print()

# ---------- (2) set up from any start: optimum is closed + homogeneous ----------
n = 21
ap   = np.arange(n).astype(float)                           # arithmetic / lattice (the optimum structure)
geo  = 1.35**np.arange(n)                                   # geometric — AP-free (independence pole)
lo, hi = 0.0, float(n-1)
EPS = 1e-6                                                   # EXACT collinear-triple match (a real 3-AP)

def closure_fraction(P):
    hit=0; tot=0
    for i in range(len(P)):
        for j in range(len(P)):
            if i==j: continue
            c = 2*P[j]-P[i]
            if P.min()-1e-9<=c<=P.max()+1e-9:
                tot+=1
                if np.min(np.abs(P-c))<EPS*max(1,abs(c)): hit+=1
    return hit/max(tot,1)
def triples_per_point(P):
    cnt=np.zeros(len(P))
    for i in range(len(P)):
        for j in range(len(P)):
            if i==j: continue
            c=2*P[j]-P[i]
            if np.min(np.abs(P-c))<EPS*max(1,abs(c)): cnt[j]+=1   # j is the middle/void of a real triple
    return cnt
cf_ap, cf_sp = closure_fraction(ap), closure_fraction(geo)
tp_ap, tp_sp = triples_per_point(ap), triples_per_point(geo)
print("  (2) SET UP FROM ANY START (optimum = closed under completion + homogeneous):")
print(f"        completion 2b−a lands EXACTLY on a point:  arithmetic {cf_ap*100:4.0f}%   vs   geometric {cf_sp*100:4.0f}%")
print(f"        triples per point (mean±std):  arithmetic {tp_ap.mean():.1f}±{tp_ap.std():.1f}  vs  geometric {tp_sp.mean():.1f}±{tp_sp.std():.1f}")
print(f"     -> the optimum (arithmetic/lattice) is CLOSED under 'complete the triple' — every pair's 3rd")
print(f"        lands on a point, so it can be rebuilt from ANY starting point. The AP-free geometric set is")
print(f"        triple-empty (the independence pole): completions leave it, no optimum to rebuild.")
print()

# ---------- (3) self-similar nesting: golden set maps to itself under φ-scaling ----------
K=9
G = PHI**(-np.arange(K))                                    # {1, 1/φ, 1/φ², …} — geometric golden set
def self_overlap(s):
    S = s*G
    hit=sum(1 for x in S if np.min(np.abs(G-x))<0.01*max(G.min(),1e-3))
    return hit/len(S)
scales=np.linspace(1.1,3.0,400)                            # skip s=1 (trivial identity)
ov=np.array([self_overlap(s) for s in scales])
peak_s=scales[np.argmax(ov)]
print("  (3) SELF-SIMILAR NESTING (put a point, use it as origin of a smaller copy):")
print(f"        scaling the golden set by φ={PHI:.3f} maps it onto itself (overlap {self_overlap(PHI):.2f});")
print(f"        by a non-golden 1.5 → overlap {self_overlap(1.5):.2f}. Peak scale found: {peak_s:.3f}.")
print(f"     -> each point is the ORIGIN of a φ-scaled smaller structure — the orchard's ℚ(√5) self-similarity")
print(f"        and the 'fold higher' recursion. The optimum nests inside itself at the golden ratio.")

# ---------------------------------------------------------------------------
# PLOT
# ---------------------------------------------------------------------------
fig=plt.figure(figsize=(14.4,5.3))
gs=fig.add_gridspec(1,3,wspace=0.32)

# (A) the inverse
axA=fig.add_subplot(gs[0,0])
axA.hist(thirds_1pt, bins=40, color="#c0392b", alpha=0.5, density=True, label="1 point known → 3rd is FREE")
axA.axvline(third_2pt, color="#238b45", lw=2.6, label="2 points known → 3rd FORCED")
axA.scatter([a_known,b],[0.15,0.15], color="#111", s=45, zorder=6)
axA.text(a_known,0.5,"a", fontsize=10, ha="center"); axA.text(b,0.5,"b (void)", fontsize=9, ha="center")
axA.text(third_2pt,0.5,"c=2b−a", fontsize=9, ha="center", color="#238b45")
axA.set_yticks([]); axA.set_xlabel("position of the third point")
axA.set_title("The inverse: 2 points force the 3rd\n(one point = an undetermined half-truth)", fontsize=10.2)
axA.legend(fontsize=7.8, framealpha=0.9, loc="upper left")

# (B) closure + homogeneity
axB=fig.add_subplot(gs[0,1])
axB.bar([0,1],[cf_ap*100,cf_sp*100], color=["#238b45","#c0392b"], width=0.6)
axB.set_xticks([0,1]); axB.set_xticklabels(["arithmetic\n(optimum)","geometric\n(AP-free)"])
axB.set_ylabel("completions landing on a point (%)")
axB.set_title(f"Set up from any start = closed under completion\ntriples/pt: {tp_ap.mean():.0f}±{tp_ap.std():.0f} vs {tp_sp.mean():.0f}±{tp_sp.std():.0f}", fontsize=10.2)
for x,v in zip([0,1],[cf_ap*100,cf_sp*100]): axB.text(x,v+1,f"{v:.0f}%",ha="center",fontsize=9)

# (C) self-similarity
axC=fig.add_subplot(gs[0,2])
axC.plot(scales, ov, color="#8a2be2", lw=2)
axC.axvline(PHI, color="#e0a021", lw=1.6, ls="--"); axC.text(PHI+0.03, 0.85, f"φ={PHI:.2f}", color="#a06a00", fontsize=9)
axC.axvline(PHI**2, color="#e0a021", lw=1.0, ls=":"); axC.text(PHI**2+0.03, 0.6, "φ²", color="#a06a00", fontsize=8)
axC.set_xlabel("scale factor (zoom around a point)"); axC.set_ylabel("overlap with itself (self-similarity)")
axC.set_title("Self-similar nesting: each point is the\norigin of a φ-scaled smaller copy", fontsize=10.2)

fig.suptitle("Completing a half-truth is the inverse triple problem (given 2, find the 3rd); the optimum is closed & homogeneous (set up from any start) and self-similar at φ",
             fontsize=10.3)
fig.savefig("triple_completion.png", dpi=130, bbox_inches="tight")
print("\n  wrote triple_completion.png")
