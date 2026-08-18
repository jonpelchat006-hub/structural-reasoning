#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
discovery_bulb.py -- #50: the surprise is a BULB that lights up FURTHER OUT (a slot in a far pixel filled
for free by outside work); it brightens a PATH toward it; you densify the EMPTY lit pixels (not the filled
ones); a stronger/farther bulb lights MORE empty pixels; then you FOLD them back in. This FIXES #49's
marginal densify -- there I densified in-place (near filled ground, which absorbs the energy, #18); the
right move is to densify the newly-lit EMPTY region.

Jonathan: a surprise happens further out -- a bunch of pixels suddenly light up and we build paths to that
new spot. A surprise = a slot in a far pixel getting filled for FREE (a piece of useful outside work); it
brightens a path towards it, and THAT (empty) is where we fill memories, not in already-filled pixels. How
far out + how strong the bulb lights = how many empty pixels become available; then we densify those and fold
them back in.

Grounded:
  * #18 (FOLDING_DISCOVERY §4a) -- existing pixels ABSORB the expansion energy; a mint in EMPTY room claims
    228 cells, on an existing memory claims 0 (overlap↔territory −0.84). This is exactly "densify empty, not
    filled," and it is why #49's in-place densify was a null.
  * #47 (FOLDING_REBASING) -- new info enters through the outer void (intake port), then folds back in
    (re-bases into a new core). #48 -- brighten a path from known structure to the anchor.
  * FOLDING_OUTER_SLOT -- outside work slots in and dissipates/merges if compatible (the fold-back-in).

MEASURED:
  (A) THE #49 FIX: densifying the LIT-EMPTY region claims large new territory; densifying IN-PLACE (near
      filled, the #49 move) claims ~0 -- the energy is absorbed. WHERE you densify is the whole difference.
  (B) The bulb brightens a PATH from known structure to the far spot; the new memories land in the empty lit
      region (overlap with existing ~0), connected by the path.
  (C) Bulb STRENGTH opens proportional empty pixels (illumination ∝ strength) -> more territory when
      densified; then the region FOLDS BACK IN (coverage grows, a new core).
"""
import numpy as np
from scipy.spatial.distance import cdist
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

rng=np.random.default_rng(2)

# ---- known structure: clusters on the left/centre, leaving the far right/top EMPTY ----
centers=np.array([[0.25,0.30],[0.32,0.62],[0.20,0.48],[0.45,0.40]])
known=np.vstack([rng.normal(c,0.045,(28,2)) for c in centers]); known=np.clip(known,0.02,0.98)

gx=np.linspace(0,1,56); GX,GY=np.meshgrid(gx,gx); GRID=np.stack([GX.ravel(),GY.ravel()],1)
def occupancy(P,pts,h=0.06):
    return np.exp(-(cdist(P,pts)**2)/(2*h*h)).sum(1)
OCC=occupancy(GRID,known); OCC/=OCC.max()
D0=0.085
def coverage(pts):                      # fraction of the domain within D0 of a known pixel (reached/known)
    return float(np.mean(cdist(GRID,pts).min(1)<D0))

# ---- the BULB: a surprise lights up a FAR EMPTY spot (outside work fills a slot for free) ----
nearest=cdist(GRID,known).min(1)
far_empty = (nearest>0.18)&(OCC<0.12)
bulb=GRID[far_empty][np.argmax(nearest[far_empty])]     # farthest genuinely-empty spot
def lit_pixels(strength):
    r=0.05*strength                                     # illumination radius ∝ strength
    d=cdist(GRID,bulb[None]).ravel()
    return (d<r)&(OCC<0.15)                             # empty pixels the bulb lights up

# ---- (A) the #49 fix: densify the LIT-EMPTY region vs densify IN-PLACE (near filled) ----
S=4.0
lit=lit_pixels(S); litcells=GRID[lit]
M=16
cov0=coverage(known)
# densify LIT-EMPTY: place M memories in the lit empty region
lit_new=litcells[rng.choice(len(litcells),min(M,len(litcells)),replace=False)]
cov_lit=coverage(np.vstack([known,lit_new]))
# densify IN-PLACE (the #49 move): place M memories near an already-filled cluster
inplace_new=np.clip(centers[0]+rng.normal(0,0.04,(M,2)),0,1)
cov_inplace=coverage(np.vstack([known,inplace_new]))
terr_lit=cov_lit-cov0; terr_inplace=cov_inplace-cov0

# overlap of the new memories with existing structure (should be ~0 for lit, high for in-place)
ov_lit=float(np.mean(cdist(lit_new,known).min(1)<D0))
ov_inplace=float(np.mean(cdist(inplace_new,known).min(1)<D0))

print("="*80)
print("  #50  THE SURPRISE BULB: light up further out, densify the EMPTY lit region, fold back in")
print("="*80)
print(f"  bulb lit at the far-empty spot {np.round(bulb,2)}; densify M={M} memories")
print(f"  (A) THE #49 FIX -- territory (coverage) gained:")
print(f"        densify LIT-EMPTY region : +{terr_lit*100:.1f}% coverage   (new memories overlap existing {ov_lit*100:.0f}%)")
print(f"        densify IN-PLACE (#49)   : +{terr_inplace*100:.1f}% coverage  (overlap {ov_inplace*100:.0f}% -> energy absorbed, #18)")
print(f"        -> {terr_lit/max(terr_inplace,1e-3):.0f}× more new ground by densifying the EMPTY lit region, not the filled one.")

# ---- (B) the path from known structure to the bulb ----
start=known[np.argmin(cdist(bulb[None],known).ravel())]     # nearest known pixel
path=np.linspace(start,bulb,12)

# ---- (C) strength opens proportional empty pixels; territory grows; fold back in ----
strengths=np.linspace(1,8,12); avail=[]; terr=[]
for s in strengths:
    L=lit_pixels(s); cells=GRID[L]; avail.append(int(L.sum()))
    if len(cells):
        nw=cells[rng.choice(len(cells),min(M,len(cells)),replace=False)]
        terr.append(coverage(np.vstack([known,nw]))-cov0)
    else: terr.append(0.0)
avail=np.array(avail); terr=np.array(terr)
# fold back in: after densifying, coverage grew from cov0 to cov_lit (a new core is added)
print(f"  (B) the bulb brightens a PATH from the nearest known pixel {np.round(start,2)} to the bulb; new")
print(f"      memories fill the empty lit region (overlap {ov_lit*100:.0f}%), connected by the path.")
print(f"  (C) bulb strength opens proportional empty pixels: {avail[0]} lit at S={strengths[0]:.0f} -> "
      f"{avail[-1]} at S={strengths[-1]:.0f}; territory gained rises with it.")
print(f"      fold back in: coverage {cov0*100:.0f}% -> {cov_lit*100:.0f}% (the resolved region becomes a new core).")

# ---------------------------------------------------------------------------
fig=plt.figure(figsize=(15.2,4.9)); gs=fig.add_gridspec(1,3,wspace=0.28)
LIT="#238b45"; INP="#c0392b"; BULBC="#f6c026"

axA=fig.add_subplot(gs[0,0])
axA.bar([0,1],[terr_inplace*100,terr_lit*100],0.6,color=[INP,LIT])
for i,v in enumerate([terr_inplace*100,terr_lit*100]): axA.text(i,v+0.2,f"+{v:.1f}%",ha="center",fontsize=10)
axA.set_xticks([0,1]); axA.set_xticklabels(["densify IN-PLACE\n(#49, near filled)","densify LIT-EMPTY\n(the fix)"],fontsize=8.8)
axA.set_ylabel("new territory gained (coverage %)")
axA.set_title("(A) The #49 fix: densify the EMPTY lit region,\nnot the filled one (filled absorbs it, #18)",fontsize=10.0)

axB=fig.add_subplot(gs[0,1])
axB.scatter(GRID[OCC>0.1][:,0],GRID[OCC>0.1][:,1],s=6,color="#bbb",alpha=0.5)
axB.scatter(known[:,0],known[:,1],s=12,color="black",alpha=0.6,label="known structure")
litc=GRID[lit]; axB.scatter(litc[:,0],litc[:,1],s=20,color=BULBC,alpha=0.5,label="lit-empty pixels")
axB.scatter(lit_new[:,0],lit_new[:,1],s=26,color=LIT,edgecolor="black",lw=0.4,zorder=5,label="new memories (densify)")
axB.plot(path[:,0],path[:,1],color=BULBC,lw=2.2,zorder=4,label="brightened path")
axB.scatter([bulb[0]],[bulb[1]],marker="*",s=340,color=BULBC,edgecolor="black",lw=1,zorder=6,label="surprise bulb")
axB.set_xlim(0,1); axB.set_ylim(0,1); axB.set_xticks([]); axB.set_yticks([])
axB.legend(fontsize=6.8,loc="lower left",framealpha=0.92)
axB.set_title("(B) The bulb lights up further out; a path\nbrightens toward it; fill the empty region",fontsize=10.0)

axC=fig.add_subplot(gs[0,2])
axC.plot(strengths,avail,"-o",color=BULBC,lw=2,ms=4,label="empty pixels lit (available)")
axC.set_xlabel("bulb strength"); axC.set_ylabel("empty pixels made available",color="#b8860b")
axC.tick_params(axis="y",labelcolor="#b8860b")
ax2=axC.twinx(); ax2.plot(strengths,terr*100,"-s",color=LIT,lw=1.8,ms=3,label="territory gained")
ax2.set_ylabel("territory gained (coverage %)",color=LIT); ax2.tick_params(axis="y",labelcolor=LIT)
axC.set_title(f"(C) Stronger bulb → more empty pixels → more\ngrowth; fold back in ({cov0*100:.0f}%→{cov_lit*100:.0f}% coverage)",fontsize=10.0)

fig.suptitle("#50 — the surprise is a bulb lighting up further out: brighten a path to it and densify the EMPTY lit pixels (not the filled ones, #18), then fold them back in; a stronger bulb opens more room",fontsize=9.6)
fig.savefig("discovery_bulb.png",dpi=130,bbox_inches="tight")
print("\n  wrote discovery_bulb.png")
