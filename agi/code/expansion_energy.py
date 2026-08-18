#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
expansion_energy.py -- existing pixels absorb the expansion energy: novelty needs empty room.

Jonathan: "the existing pixels also absorb the energy for the expansion, so if there's too
much overlap with earlier memories it can't expand." A newly minted gap (FOLDING_DISCOVERY)
has an expansion-energy budget, and it grows by claiming NEW territory -- but pushing into
ground already covered by earlier memories COSTS that energy (the overlap absorbs it) and
returns nothing new. So an innovation minted in empty room expands into its own domain; one
minted on top of what you already know can't move -- the energy is eaten by the overlap.

Grounding: SPARSE_VESICA §11.6 -- the VOID is the generative space ("matter is the recipe
book, finite; void is the room to invent"); growth happens in the empty room, not in filled
matter. INNER_SHELL update-30 -- Jonathan's energy model "expand -> the cores must MOVE to
keep balance": expansion has a cost paid against existing structure. FOLDING_MOVEMENT Test 5
-- growth only into the EMPTY tail (fixed structure gains nothing). SPHERE_GENERATOR C.2 --
closure fails (and a primitive is born) in the GAPS, where the current structure can't answer.

MODEL
-----
A 2-D memory field: existing memories are Gaussian bumps -> density ρ(x). A new innovation is
minted at a point with a fixed expansion ENERGY E. Expansion spreads outward from the mint;
the cost to push the frontier through a cell is (1 + λ·ρ) -- empty ground is cheap, covered
ground is dear (overlap absorbs energy). The reachable set = cells within geodesic cost E.
The innovation's GAINED TERRITORY = the reachable cells that are genuinely EMPTY (ρ < ε) --
new domain it can call its own. Overlap-heavy mints get their energy absorbed and gain almost
nothing; empty-room mints expand freely.
"""
import numpy as np, heapq
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

rng = np.random.default_rng(5)
G = 64                          # grid resolution
LAM = 12.0                      # how strongly overlap absorbs energy
E = 6.0                         # expansion energy budget
EMPTY = 0.12                    # ρ below this = genuinely empty (claimable) ground

# existing memories: several Gaussian bumps across the field
MEM = np.array([[0.24,0.30],[0.30,0.72],[0.55,0.50],[0.72,0.25],[0.78,0.78],[0.50,0.16]])
MW  = np.array([0.10,0.11,0.14,0.10,0.12,0.09])
gx = np.linspace(0,1,G); GX,GY = np.meshgrid(gx,gx)
def density(px,py):
    r = np.zeros_like(px)
    for (mx,my),w in zip(MEM, MW):
        r += np.exp(-((px-mx)**2+(py-my)**2)/(2*w**2))
    return r
RHO = density(GX,GY)
COST = 1.0 + LAM*RHO            # cost to push the frontier through each cell

def geodesic(src):
    """min accumulated cost from src cell to every cell (Dijkstra, 4-connected)."""
    d = np.full((G,G), np.inf); d[src]=0.0
    pq=[(0.0,src[0],src[1])]
    while pq:
        dd,i,j = heapq.heappop(pq)
        if dd>d[i,j]: continue
        for di,dj in ((-1,0),(1,0),(0,-1),(0,1)):
            ni,nj=i+di,j+dj
            if 0<=ni<G and 0<=nj<G:
                nd = dd + 0.5*(COST[i,j]+COST[ni,nj])/G*10   # step-scaled avg cost
                if nd<d[ni,nj]:
                    d[ni,nj]=nd; heapq.heappush(pq,(nd,ni,nj))
    return d

def gained(mint_ij):
    d = geodesic(mint_ij)
    reach = d < E
    new_territory = np.sum(reach & (RHO < EMPTY))       # empty ground claimed
    return new_territory, reach

def ij(px,py): return (int(round(py*(G-1))), int(round(px*(G-1))))

# ---- sweep: gained territory vs overlap at the mint, over many mint locations ----
mints = rng.uniform(0.06,0.94,(120,2))
ov = []; gain = []
for (px,py) in mints:
    m = ij(px,py); ov.append(float(RHO[m])); gain.append(int(gained(m)[0]))
ov = np.array(ov); gain = np.array(gain)

# two illustrative mints: an empty valley vs a crowded peak
empty_pt = (0.10,0.52); crowd_pt = (0.55,0.50)
gE, reachE = gained(ij(*empty_pt)); gC, reachC = gained(ij(*crowd_pt))

print("="*72)
print("  EXPANSION ENERGY: existing pixels absorb it -- novelty needs empty room")
print("="*72)
print(f"  {len(MEM)} existing memories; expansion energy E={E}; overlap-absorption λ={LAM}")
print()
print(f"  illustrative mints (new territory claimed, in cells):")
print(f"     EMPTY room  {empty_pt}  overlap ρ={RHO[ij(*empty_pt)]:.2f}  -> gained {gE}")
print(f"     CROWDED     {crowd_pt}  overlap ρ={RHO[ij(*crowd_pt)]:.2f}  -> gained {gC}")
print(f"     ratio: the empty-room mint expands {gE/max(gC,1):.0f}× further.")
print()
lo = ov < 0.15; hi = ov > 0.6
print(f"  over {len(mints)} random mints:")
print(f"     mints in EMPTY room (ρ<0.15):   mean territory gained {gain[lo].mean():.0f}")
print(f"     mints on EXISTING memory (ρ>0.6): mean territory gained {gain[hi].mean():.0f}")
corr = np.corrcoef(ov, gain)[0,1]
print(f"     correlation(overlap, territory gained) = {corr:+.2f}")
print()
print(f"  -> the more a mint OVERLAPS earlier memory, the LESS it can expand -- the existing")
print(f"     pixels absorb the expansion energy. Novelty grows only in the empty room (the void);")
print(f"     minting on top of what you already know gains almost nothing (a redundant 'worst")
print(f"     version'). This is why a new gap must be mostly EMPTY to become its own domain.")

# ---------------------------------------------------------------------------
# PLOT: left = the memory field + two mints' reachable regions; right = the law.
# ---------------------------------------------------------------------------
fig, (axL, axR) = plt.subplots(1, 2, figsize=(13.2, 5.4))
axL.imshow(RHO, origin="lower", extent=[0,1,0,1], cmap="Greens", alpha=0.9)
axL.contour(GX, GY, reachE.astype(float), levels=[0.5], colors="#2b6cb0", linewidths=2.2)
axL.contour(GX, GY, reachC.astype(float), levels=[0.5], colors="#c0392b", linewidths=2.2)
axL.scatter(*empty_pt, color="#2b6cb0", s=90, zorder=5, edgecolor="white")
axL.scatter(*crowd_pt, color="#c0392b", s=90, zorder=5, edgecolor="white")
axL.text(empty_pt[0], empty_pt[1]+0.05, f"minted in EMPTY room\n→ expands far ({gE} cells)",
         color="#1f4e79", fontsize=8.5)
axL.text(crowd_pt[0]-0.02, crowd_pt[1]-0.13, f"minted on a MEMORY\n→ energy absorbed ({gC} cells)",
         color="#8c1d10", fontsize=8.5, ha="center")
axL.set_xlim(0,1); axL.set_ylim(0,1); axL.set_xticks([]); axL.set_yticks([])
axL.set_title("Existing memory (green) absorbs expansion energy\nblue reach (empty mint) vs red reach (crowded mint)")

axR.scatter(ov, gain, s=22, color="#238b45", alpha=0.75)
# binned trend
bins = np.linspace(ov.min(), ov.max(), 7)
bc = 0.5*(bins[1:]+bins[:-1]); bm = [gain[(ov>=bins[i])&(ov<bins[i+1])].mean() if np.any((ov>=bins[i])&(ov<bins[i+1])) else np.nan for i in range(6)]
axR.plot(bc, bm, "-o", color="#c0392b", lw=2, label="binned mean")
axR.set_xlabel("overlap with earlier memory at the mint  (ρ)")
axR.set_ylabel("new territory the innovation can claim")
axR.set_title(f"Too much overlap → it can't expand\n(correlation {corr:+.2f}: overlap absorbs the energy)")
axR.legend(loc="upper right", fontsize=9, framealpha=0.9)

fig.tight_layout(); fig.savefig("expansion_energy.png", dpi=130)
print("\n  wrote expansion_energy.png")
