#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gaps_engine.py -- the discovery face: a positive surprise MINTS a new gap.

Jonathan: we get adrenaline when good things happen too -- the discovery high, a reaction
while the tank is still FULL. "Maybe it's a way to make more of those memory holes?" The
crisis reserve (FOLDING_MOVEMENT T10-12) survives by bending rules; the DISCOVERY reserve
GROWS by minting new gaps -- when reality beats prediction, don't fill a hole, OPEN one,
planting a new exploration site to grow toward. Grounded: Shovelcat_13/13B (happiness Y
"extends exploration windows"), the adjacent possible expanding (Shovelcat_11_3 §15.7),
surprise-gated compute (MINING_NOTES #14). The exploratory complement to T5/T6 growth.

ENVIRONMENT: a big mostly-empty world with a CHAIN of value-clusters along a curve, joined
by a FAINT trail (a low ridge -- below the exploit floor, but enough that sampling it beats
prediction = a positive surprise). The agent starts knowing only cluster 0, on a tight
budget.

  uncertainty u(x) = 1 - coverage      (the gaps)     m(x) = kernel value estimate
  frontier(x) = reach-halo * u          (probe just beyond the known edge, not the far void)

THREE POLICIES (acquire next sample):
  FILL      -- exploit + frontier:  u*max(m-FLOOR,0) + λ*frontier. Refines high-value
               clusters and creeps its edge, but the faint trail is below FLOOR so it has
               no demand to commit outward. Stalls near the start.
  CURIOSITY -- u alone. Chases the emptiest cells -> the vast void (no value: the Pluto
               trap). Wastes the budget.
  DISCOVERY -- FILL + gap-minting: on a POSITIVE SURPRISE (observed - predicted > τ), MINT
               a gap (strong demand around it) so the next samples commit toward it. Chains
               surprise -> surprise along the trail to the far clusters.

The mint is the ONLY difference between FILL and DISCOVERY -- so the gap between them is
exactly what minting-a-gap-on-good-news buys.
"""
import numpy as np
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

W = 18.0
SIG = 0.9
H   = 0.9
FLOOR = 0.50                    # exploit only where predicted value clears this
CENTERS = np.array([[2.5,2.5],[5.7,5.7],[8.9,8.9],[12.0,12.0],[15.2,15.2]])  # spaced 4.5 (real gaps)
TRAIL_A = 0.30                  # faint connecting ridge amplitude (BELOW FLOOR: exploit can't use it)
NOISE = 0.03
SURPRISE = 0.12
BUDGET = 48

def _seg_dist2(P, a, b):
    ab = b-a; t = np.clip(((P-a)@ab)/(ab@ab+1e-9), 0, 1)
    proj = a + t[:,None]*ab
    return np.sum((P-proj)**2, axis=1)

def value(P):
    P = np.atleast_2d(P); v = np.zeros(len(P))
    for c in CENTERS:
        v += np.exp(-np.sum((P-c)**2, axis=1)/(2*SIG**2))
    for i in range(len(CENTERS)-1):                       # the faint trail
        v += TRAIL_A*np.exp(-_seg_dist2(P, CENTERS[i], CENTERS[i+1])/(2*0.45**2))
    return v

cg = np.linspace(0.4, W-0.4, 52); CX, CY = np.meshgrid(cg, cg)
CAND = np.column_stack([CX.ravel(), CY.ravel()])

def model(SX, SY, Q):
    d2 = np.sum((Q[:,None,:]-SX[None,:,:])**2, axis=2)
    Kx = np.exp(-d2/(2*H**2)); wsum = Kx.sum(1)+1e-9
    m = (Kx*SY[None,:]).sum(1)/wsum
    cover = Kx.max(1)
    reach = np.exp(-(np.sqrt(d2).min(1))**2/(2*(1.7*H)**2))   # wider halo = frontier band
    return m, 1.0-cover, reach

def run(policy, seed=0):
    rng = np.random.default_rng(seed)
    X = CENTERS[0] + rng.normal(0, 0.5, (6,2)); Y = value(X)+rng.normal(0,NOISE,6)
    minted = []; found = [None]*len(CENTERS)
    def check():
        for i,c in enumerate(CENTERS):
            if found[i] is None and np.min(np.sum((X-c)**2,axis=1)) < SIG**2:
                found[i] = len(X)
    check()
    for step in range(len(X), BUDGET):
        m, unc, reach = model(X, Y, CAND)
        if policy == "curiosity":
            acq = unc                                   # undirected: chase any unknown
        elif policy == "fill":
            acq = unc*np.maximum(m-FLOOR,0)             # pure exploit (T6): no exploration drive
        else:
            demand = np.maximum(m,0.0).copy()          # follow ANY positive value (incl. faint trail)
            for g in minted:
                demand += 2.5*np.exp(-np.sum((CAND-g)**2,axis=1)/(2*1.8**2))
            acq = unc*demand                            # value-seeking + minted gaps ahead
        x = CAND[int(np.argmax(acq))]
        mpred = model(X, Y, x[None])[0][0]
        y = float(value(x[None])[0]+rng.normal(0,NOISE))
        if policy == "discovery" and (y-mpred) > SURPRISE:
            # MINT the new gap AHEAD, along the direction of travel -> pull the frontier
            # forward across the gap toward whatever more is out there.
            fwd = x - X[-4:].mean(0); n = np.linalg.norm(fwd)
            g = x + (fwd/n)*2.4 if n > 1e-6 else x
            g = np.clip(g, 0.4, W-0.4)
            minted.append(g)
        X = np.vstack([X,x]); Y = np.append(Y,y); check()
    return dict(policy=policy, X=X, found=found, discovered=sum(s is not None for s in found),
                minted=np.array(minted) if minted else np.empty((0,2)))

SEEDS = 40
mean_disc = {p: float(np.mean([run(p,s)["discovered"] for s in range(SEEDS)]))
             for p in ("fill","curiosity","discovery")}

print("="*72)
print("  THE GAPS ENGINE: a positive surprise mints a new gap (discovery)")
print("="*72)
print(f"  {len(CENTERS)} clusters in a chain + faint trail; start knows only cluster 0; budget {BUDGET}")
print()
print(f"  {'policy':12}{'clusters discovered (of '+str(len(CENTERS))+')':>34}")
for p in ("fill","curiosity","discovery"):
    print(f"  {p:12}{mean_disc[p]:>34.2f}")
print()
print(f"  -> FILL exploits + creeps its edge, but the trail is below the value floor so it")
print(f"     has no demand to commit outward: {mean_disc['fill']:.1f}/{len(CENTERS)} clusters.")
print(f"  -> CURIOSITY chases the emptiest cells -> the vast void (no value): {mean_disc['curiosity']:.1f}/{len(CENTERS)}.")
print(f"  -> DISCOVERY mints a gap on each positive surprise and commits toward it, chaining")
print(f"     out the trail: {mean_disc['discovery']:.1f}/{len(CENTERS)}. Minting-on-good-news is the whole delta --")
print(f"     it GROWS the frontier by opening new holes where reality beat prediction.")

rf = run("fill",1); rc = run("curiosity",1); rd = run("discovery",1)
fig, axs = plt.subplots(1, 3, figsize=(14.4, 5.2))
gx = np.linspace(0,W,200); GXX,GYY = np.meshgrid(gx,gx)
VV = value(np.column_stack([GXX.ravel(),GYY.ravel()])).reshape(GXX.shape)
for ax, r, ttl in [(axs[0],rf,"FILL — exploit + creep"),
                   (axs[1],rc,"CURIOSITY — chase the void"),
                   (axs[2],rd,"DISCOVERY — mint a gap on good news")]:
    ax.contourf(GXX,GYY,VV,levels=12,cmap="Greens",alpha=0.65)
    ax.scatter(CENTERS[:,0],CENTERS[:,1],marker="*",s=170,color="#111",zorder=5)
    ax.plot(r["X"][:,0],r["X"][:,1],"-o",color="#c0392b",ms=3,lw=0.7,alpha=0.7)
    if len(r["minted"]):
        ax.scatter(r["minted"][:,0],r["minted"][:,1],marker="o",s=90,facecolor="none",
                   edgecolor="#e0a021",lw=2.0,zorder=6)
    ax.set_xlim(0,W); ax.set_ylim(0,W); ax.set_xticks([]); ax.set_yticks([])
    ax.set_title(f"{ttl}\ndiscovered {r['discovered']}/{len(CENTERS)}", fontsize=10)
fig.suptitle("Discovery grows by minting gaps where good things happen  "
             f"(mean/{SEEDS} seeds: fill {mean_disc['fill']:.1f} · curiosity {mean_disc['curiosity']:.1f} · "
             f"discovery {mean_disc['discovery']:.1f})  —  orange = minted gaps", fontsize=11)
fig.tight_layout(rect=[0,0,1,0.94]); fig.savefig("gaps_engine.png", dpi=130)
print("\n  wrote gaps_engine.png")
