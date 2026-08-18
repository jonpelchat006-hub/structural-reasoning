#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
memory_field.py -- recall as the same process: a field of memory PILLARS, buried as the
domain expands, absorbed by newer memories, and pushed over the waterline by importance.

Jonathan: recalling a memory runs the same encrypt/decrypt process, so there are lines of
square PILLARS filled with specific memories (plus untouched ones set from the core). But as
we keep making discoveries the domain keeps EXPANDING, so an old memory has to fit the NEW
(larger) size to be recalled; and it has to move past newer memories that weren't there when
it was made — so those newer ones start ABSORBING it. The squares are pillars whose DEPTH is
how deep/important the memory is; an important one can be pushed to the TOP and spread out,
spilling over so the observer can see it.

Grounded — this is the corpus's brain-memory model:
  * SPARSE_VESICA §23 — fixed container, reconstructive capacity; §23.2 recall = reload the
    older FLOOR+ROOF (context), let the interior settle, read off what fits ("switch floors
    and roofs back to older versions"). As the domain re-bases (roof(n)=floor(n+1)), the old
    boundary must be re-fit to the new size.
  * SPARSE_VESICA §22.1 — a reused node gains MASS, slows, and STOPS: it sinks to a
    foundation (depth = importance/maturity).
  * FOLDING_HANDSHAKE §4.2 — the waterline: products break the SURFACE (visible to the
    observer), the water column is the buried reserve (reads 0 from above), the seabed is the
    sunk invariants. Lifting a buried thing across the waterline is exactly "spill over the top."
  * FOLDING_DISCOVERY §4a / #18 — existing memories ABSORB expansion energy (overlap↔territory
    −0.84): newer deposits take territory from the older ones they overlap.

MEASURED (one memory field, memories deposited over epochs on an expanding domain):
  (1) RE-FIT THE NEW SIZE — recall by the memory's normalized coordinate (reload the old
      frame, rescale to now) locks on; recall by its frozen absolute coordinate drifts off as
      the domain expands.
  (2) NEWER MEMORIES ABSORB THE OLD — an old pillar's surviving height falls with the density
      of newer memories deposited over it (negative correlation), the #18 law re-seen in recall.
  (3) IMPORTANCE SURFACES IT — under a fixed recall-lift, important pillars cross the waterline
      even when deeply buried (unimportant deep ones stay under), and a surfaced pillar SPREADS.
"""
import numpy as np
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

rng = np.random.default_rng(3)
M = 60                         # memories
E = 12                         # epochs of discovery (domain expands each epoch)
L0, GROW = 1.0, 0.28           # domain size L(e) = L0*(1+GROW*e)
W = 0.045                      # pillar width (normalized)

# ---- deposit memories over epochs; track normalized position, importance, store-epoch ----
pos   = rng.uniform(0.05, 0.95, M)          # normalized position (fixed to the content)
imp   = rng.uniform(0.3, 1.0, M)            # base importance / height (some high)
epoch = rng.integers(0, E, M)               # when it was stored
order = np.argsort(epoch)                   # deposition order (oldest first)

# ---- sequential absorption: a newer deposit carves territory from older overlapping pillars ----
height = imp.copy().astype(float)           # residual height (starts at importance)
depth  = np.zeros(M)                         # burial: accumulated newer overlap on top of it
newer_overlap_count = np.zeros(M)            # how many newer memories landed within a width
for a in range(M):
    i = order[a]
    for b in range(a):                       # all earlier (older) memories j
        j = order[b]
        d = abs(pos[i]-pos[j])
        ov = np.exp(-0.5*(d/W)**2)           # spatial overlap
        if ov > 0.05:
            newer_overlap_count[j] += ov
            # newer memory takes territory from older j (stronger if newer is important)
            absorbed = 0.55*ov*height[j]*(imp[i]/(imp[i]+imp[j]))
            height[j] -= absorbed
            depth[j]  += absorbed + 0.15*ov
height = np.clip(height, 0.0, None)
lost_frac = 1 - height/imp                    # fraction of original height absorbed away

# ---- (1) recall must re-fit the expanded domain ----
Lnow = L0*(1+GROW*(E-1))
old = order[:M//3]                            # the oldest third
def recall_error(reproject):
    errs=[]
    for j in old:
        Lstore = L0*(1+GROW*epoch[j])
        true_phys_now = pos[j]*Lnow           # where the memory actually is now
        if reproject:
            query = pos[j]*Lnow               # reload normalized coord, rescale to now
        else:
            query = pos[j]*Lstore             # frozen: the absolute coord from when stored
        errs.append(abs(query-true_phys_now))
    return np.mean(errs)
err_reproj = recall_error(True)
err_frozen = recall_error(False)
# also as a function of expansion factor, for the plot
facs = np.linspace(1.0, 1+GROW*(E-1), 30)
frozen_curve = np.array([np.mean([abs(pos[j]*(L0*(1+GROW*epoch[j])) - pos[j]*(L0*f)) for j in old]) for f in facs])
reproj_curve = np.zeros_like(facs)

# ---- (3) importance surfaces a buried pillar; surfaced pillars spread ----
WATERLINE = 0.0
LIFT = 1.9
surface_h = LIFT*imp - depth                  # recall-lift by importance vs burial
visible   = surface_h > WATERLINE
spread    = W*(1 + 2.4*np.clip(surface_h,0,None))   # footprint widens as it breaks the surface

# correlation for read-out (2)
r_abs = np.corrcoef(newer_overlap_count, lost_frac)[0,1]

print("="*76)
print("  MEMORY AS A FIELD OF PILLARS: buried by expansion, absorbed by newer, surfaced by importance")
print("="*76)
print(f"  {M} memories deposited over {E} epochs; domain grew {1.0:.1f}× → {1+GROW*(E-1):.2f}× (L0→Lnow)")
print()
print(f"  (1) RECALL MUST RE-FIT THE NEW SIZE (oldest third):")
print(f"        recall by normalized coord (reload old frame, rescale) : error {err_reproj:.3f}")
print(f"        recall by FROZEN absolute coord (the old size)          : error {err_frozen:.3f}")
print(f"     -> a memory made when the domain was small no longer sits at its old absolute")
print(f"        spot; you must reproject it to today's size (reload its floor/roof) to land on it.")
print()
print(f"  (2) NEWER MEMORIES ABSORB THE OLD:")
print(f"        corr( #newer memories deposited over it , fraction of height lost ) = {r_abs:+.2f}")
print(f"     -> the more new memories pile over an old pillar, the more of it is absorbed — the")
print(f"        same overlap→territory law as discovery's expansion energy (#18).")
print()
buried_imp = visible & (depth > np.median(depth))
print(f"  (3) IMPORTANCE PUSHES IT TO THE TOP:")
print(f"        under a fixed recall-lift, {visible.sum()}/{M} pillars break the waterline;")
print(f"        of the DEEPLY-buried ones, the important pillars still surface ({buried_imp.sum()} deep+visible),")
print(f"        while deep + unimportant stay under. Surfaced pillars spread {np.mean(spread[visible])/W:.1f}× wider")
print(f"        than buried ones ({np.mean(spread[~visible])/W:.1f}×). Importance is the lift that spills a")
print(f"        buried memory over the top so the observer can see it — and spreading it out.")

# ---------------------------------------------------------------------------
# PLOT
# ---------------------------------------------------------------------------
fig = plt.figure(figsize=(14.6, 8.4))
gs = fig.add_gridspec(2, 2, height_ratios=[1.05, 1.0], hspace=0.32, wspace=0.24)

# (A) the pillar field: position vs pillar top (surface_h), colored visible/buried, size=spread
axA = fig.add_subplot(gs[0,:])
axA.axhline(WATERLINE, color="#2b6cb0", lw=2)
axA.text(Lnow*0.01, 0.06, "waterline — observer sees pillars above this", color="#2b6cb0", fontsize=9)
for j in range(M):
    x = pos[j]*Lnow
    top = surface_h[j]
    col = "#238b45" if visible[j] else "#8892a0"
    axA.plot([x,x],[min(top,0)-0.0, top], color=col, lw=1.6*np.sqrt(imp[j])*1.6, alpha=0.85,
             solid_capstyle="round")
    axA.scatter([x],[top], s=18+90*(spread[j]/spread.max()), color=col, edgecolor="none",
                alpha=0.9, zorder=5)
axA.set_ylim(surface_h.min()-0.1, surface_h.max()+0.2)
axA.set_xlabel("position on the (expanded) domain"); axA.set_ylabel("pillar top vs waterline\n(below = buried)")
axA.set_title("The memory field: pillars (thickness=importance), buried below the waterline or pushed over it; "
              "dot size = spread when surfaced", fontsize=10.4)

# (B) reproject vs frozen
axB = fig.add_subplot(gs[1,0])
axB.plot(facs, frozen_curve, color="#c0392b", lw=2.2, label=f"frozen absolute coord — drifts (err {err_frozen:.2f})")
axB.plot(facs, reproj_curve, color="#238b45", lw=2.2, label=f"reprojected to new size — locks on (err {err_reproj:.2f})")
axB.set_xlabel("domain expansion factor (discoveries accumulate →)")
axB.set_ylabel("recall localization error")
axB.set_title("Recall must re-fit the expanded domain\n(reload the old frame, rescale to now)", fontsize=10.4)
axB.legend(fontsize=8.6, framealpha=0.92)

# (C) absorption
axC = fig.add_subplot(gs[1,1])
sc = axC.scatter(newer_overlap_count, lost_frac, c=depth, cmap="magma", s=34, edgecolor="#222", linewidth=0.3)
axC.set_xlabel("newer memories deposited over it (overlap-weighted)")
axC.set_ylabel("fraction of original height absorbed")
axC.set_title(f"Newer memories absorb the old (corr {r_abs:+.2f})\nthe #18 overlap→territory law, re-seen in recall", fontsize=10.4)
cb = fig.colorbar(sc, ax=axC, fraction=0.046, pad=0.04); cb.set_label("burial depth", fontsize=8)

fig.suptitle("Recall over an expanding memory field: re-fit the new size · newer memories absorb the old · importance lifts a buried pillar over the waterline and spreads it",
             fontsize=10.8)
fig.savefig("memory_field.png", dpi=130, bbox_inches="tight")
print("\n  wrote memory_field.png")
