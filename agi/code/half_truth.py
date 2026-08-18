#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
half_truth.py -- the balls are HALF-TRUTHS: each is missing its opposite on the void point;
a void point is relational (never one point alone); and closeness to 0 gives it mass/resistance.

Jonathan: the balls are like HALF-TRUTHS. Each pillar is still relative to a void point, and
each void point is defined by what's AROUND it — it's never just one point by itself. Each ball
here is missing its OPPOSITE on the void point (so it can't cancel). It's probably the .14 gate
too, and how close to 0 it gets would increase its RESISTANCE to movement.

Grounded:
  * Double_Bounce §28 / Fig 11 — the void needs BOTH directions: matter approaches +1, antimatter
    −1; "void sees [−0.999…, +0.999…]". A single side cannot make a void — it needs its opposite.
  * FOLDING_MATCHING_SLOT — complementarity ACROSS the void line is a positioned opposite-sign
    register (+/− at rivet distance, organised beyond chance, z=2.70): the slot matched to the wire.
    A half-truth is one half of that complementary pair.
  * SPARSE_VESICA §18.16 / §J.6 — a void node is pinned by the SURROUNDING fixed lattice, not alone;
    §11.4 identify which nodes are relevant. A point is defined by its neighbours.
  * SPARSE_VESICA §22.1/§22.2 — reuse → MASS accretes → velocity = MAX_SPEED/(1+mass·G) → STOP =
    a pinned foundation / void point. Closeness to the void (balance) ↔ mass ↔ resistance to move.
  * FOLDING_SYNTHESIS §3 — the .14 / ε reserve gate; here it is the skew that leaves the ball (#30).

MEASURED:
  (1) HALF-TRUTH = MISSING ITS OPPOSITE — residual at the would-be void falls linearly with how
      complete the balancing opposite is: 0 → full residual (a ball), 0.5 → HALF, 1 → 0 (a true void).
  (2) A VOID POINT IS RELATIONAL — its definedness (min-eigenvalue of Σ uᵢuᵢᵀ over the surrounding
      anchor directions) is 0 with one anchor (a whole free/undefined direction) and rises to a sharp
      isotropic point only once it is SURROUNDED. Never just one point by itself.
  (3) CLOSENESS TO 0 → RESISTANCE (MASS) — as the ball nears the void (residual→0, balanced) it gains
      mass and its velocity under a fixed drive → 0: a half-truth is light and mobile; a near-void is
      heavy and pins into a fixed anchor.
"""
import numpy as np
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

# ---------- (1) half-truth = missing its opposite ----------
# A cell at the origin is pulled by a LEFT anchor (one polarity). Its OPPOSITE (a RIGHT anchor)
# would cancel the pull at the balance point. Completeness c = how much of the opposite is present.
BASE = 1.0                                   # strength of the one-sided pull (the half we have)
comp = np.linspace(0, 1, 101)
residual = BASE*(1 - comp)                   # net (uncancelled) pull at the would-be void point
print("="*78)
print("  THE BALLS ARE HALF-TRUTHS: missing their opposite; a void point is relational; balance = mass")
print("="*78)
print("  (1) HALF-TRUTH = MISSING ITS OPPOSITE (residual at the would-be void point):")
for c in (0.0, 0.5, 1.0):
    r=BASE*(1-c); tag = "pure half (a ball)" if c==0 else ("HALF-truth" if c==0.5 else "full — a true void point")
    print(f"        opposite present {c:.1f}: residual {r:.2f}   {tag}")
print("     -> only one polarity → nothing cancels it → a residual ball. Its exact opposite completes")
print("        the pair and the residual goes to 0 — a full truth is a balanced pair, a ball is half of one.")
print()

# ---------- (2) a void point is relational — defined by its surround ----------
# Each surrounding anchor pins the void only ALONG its own direction u_i (a rank-1 constraint,
# like a perspective in the carving / an anchor+orientation). Definedness = how pinned in ALL
# directions = the SMALLEST eigenvalue of H = sum_i u_i u_i^T. One anchor leaves a free direction.
GOLDEN_ANGLE = np.pi*(3-np.sqrt(5))
def definedness(N):
    # N surrounding directions on the sphere (3-D, so you need a real SURROUND to pin all axes)
    i = np.arange(N); ph = np.arccos(1 - 2*(i+0.5)/N); th = GOLDEN_ANGLE*i
    U = np.stack([np.sin(ph)*np.cos(th), np.sin(ph)*np.sin(th), np.cos(ph)], 1)
    H = U.T @ U
    w = np.linalg.eigvalsh(H)
    return max(0.0, w.min()/max(w.max(),1e-9))         # min/max eigenvalue ratio (0=a free axis, 1=isotropic)
Ns = np.arange(1, 13)
defd = np.array([definedness(N) for N in Ns])
print("  (2) A VOID POINT IS RELATIONAL (definedness vs number of surrounding anchors):")
print(f"        1 anchor : {defd[0]:.2f}  (a whole FREE direction — the point is undefined, could slide)")
print(f"        2 anchors: {defd[1]:.2f}   3 anchors: {defd[2]:.2f}   6 anchors: {defd[5]:.2f}  (pinned, isotropic)")
print("     -> a void point is never one point by itself; it is defined by the balance of what surrounds it.")
print()

# ---------- (3) closeness to 0 → resistance (mass), the §22.1 law ----------
# balance b = 1 - residual/BASE (0 = pure half-truth, 1 = perfectly balanced = a true void).
# The .14 skew gates it; as it balances it gains mass and slows (velocity = MAX/(1+mass·G)).
G = 6.0; MASS_MAX = 4.0; VMAX = 1.0
res = np.linspace(BASE, 0.0, 100)            # residual shrinking toward the void (0)
balance = 1 - res/BASE
mass = MASS_MAX*balance                       # closer to the void (more balanced) → more mass (§22.1 reuse→mass)
velocity = VMAX/(1 + mass*G)                   # mobility under a fixed drive
print("  (3) CLOSENESS TO 0 → RESISTANCE (mass; §22.1 velocity = MAX/(1+mass·G)):")
print(f"        residual {res[0]:.2f} (pure half-truth): velocity {velocity[0]:.3f}  (light, mobile — floats)")
print(f"        residual {res[-1]:.2f} (near the void)   : velocity {velocity[-1]:.3f}  (heavy — pins into a foundation)")
print(f"     -> the closer the ball gets to 0 (the more it balances toward a true void point), the more it")
print(f"        resists movement — it gains mass, slows, and STOPS as a fixed anchor. The .14 skew is the")
print(f"        gate: while skewed it stays a light, mobile half-truth; balance it and it sinks and pins.")

# ---------------------------------------------------------------------------
# PLOT
# ---------------------------------------------------------------------------
fig=plt.figure(figsize=(14.4,5.2))
gs=fig.add_gridspec(1,3,wspace=0.32)

# (A) half-truth
axA=fig.add_subplot(gs[0,0])
axA.plot(comp, residual, color="#c0392b", lw=2.4)
axA.scatter([0.5],[0.5], color="#e0761f", s=70, zorder=5)
axA.annotate("HALF-truth\n(half the opposite)", (0.5,0.5), xytext=(0.55,0.72),
             fontsize=9, color="#a06a00", arrowprops=dict(arrowstyle="->", color="#a06a00"))
axA.scatter([0],[1.0], color="#c0392b", s=60, zorder=5); axA.text(0.02,0.92,"pure half = a ball", fontsize=8.5, color="#c0392b")
axA.scatter([1],[0.0], color="#238b45", s=60, zorder=5); axA.text(0.62,0.03,"full = a true void point", fontsize=8.5, color="#238b45")
axA.set_xlabel("how complete the opposite is"); axA.set_ylabel("residual at the void (the uncancelled ball)")
axA.set_title("A ball is a HALF-TRUTH\nmissing its opposite → can't cancel", fontsize=10.3)

# (B) relational
axB=fig.add_subplot(gs[0,1])
axB.plot(Ns, defd, "-o", color="#2b6cb0", lw=2.2, ms=4)
axB.axhline(0, color="#999", lw=0.8)
axB.annotate("1 anchor → a FREE direction\n(the point is undefined)", (1,defd[0]), xytext=(2.4,0.12),
             fontsize=8.4, color="#c0392b", arrowprops=dict(arrowstyle="->", color="#c0392b"))
axB.set_xlabel("surrounding anchors that define the point"); axB.set_ylabel("definedness (min/max stiffness)")
axB.set_title("A void point is RELATIONAL\nnever just one point by itself", fontsize=10.3)

# (C) closeness → resistance
axC=fig.add_subplot(gs[0,2])
axC.plot(balance, velocity, color="#238b45", lw=2.4)
axC.scatter([0],[velocity[0]], color="#c0392b", s=55, zorder=5); axC.text(0.02, velocity[0]+0.02, "half-truth: light, mobile", fontsize=8.3, color="#c0392b")
axC.scatter([1],[velocity[-1]], color="#111", s=55, zorder=5); axC.text(0.98, velocity[-1]+0.06, "near-void: heavy, pinned", fontsize=8.3, color="#111", ha="right")
axC.set_xlabel("balance = closeness to the void (residual → 0)"); axC.set_ylabel("mobility (velocity under a fixed push)")
axC.set_title("Closeness to 0 → resistance (mass)\n§22.1: balance → mass → slows → pins", fontsize=10.3)

fig.suptitle("The balls are half-truths: each missing its opposite on the void point · a void point is defined by its surround · "
             "the closer to 0 (balanced), the heavier and more anchored", fontsize=10.6)
fig.savefig("half_truth.png", dpi=130, bbox_inches="tight")
print("\n  wrote half_truth.png")
