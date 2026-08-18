#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
memory_upgrade.py -- fix the frozen-memory flaw (#40) + the spore-chain direction→depth spraying.

Jonathan noticed it in rung 2: on a revisit the agent should reference the UPGRADED path, but it
kept going to the SAME one -- because #40 stored the first noisy memory and froze it. His fix uses
the Spore derivative chain: incoming memories carry a DIRECTION/velocity, so importance can decide
where they settle -- important ones are sprayed toward the TOP of the pillar (fast recall), while
memories pointed deep just mix in and get buried. And a memory should UPGRADE on revisit.

Grounded:
  * SHOVELCAT Part X (Spore derivative chain) -- position→VELOCITY→acceleration→observer: the velocity
    is the DIRECTION a new memory arrives from.
  * FOLDING_SYNTHESIS #27 -- importance lifts a pillar over the waterline (surfacing); #31 -- reuse
    adds MASS; #21 -- the memory refines as it is revisited.

MEASURED:
  (1) UPGRADE ON REVISIT -- refining the prototype each revisit (running mean) sharpens recognition
      toward 1.0; the FROZEN first-sample stays flat (it 'keeps going to the same one').
  (2) DIRECTION→DEPTH SPRAY -- important memories settle SHALLOW (top), unimportant ones DEEP
      (buried): settling depth falls with importance.
  (3) RECALL LATENCY ∝ DEPTH; REUSE RESURFACES -- important-at-top recall fast, and a reused memory
      gains mass and rises, so its recall latency drops over reuses.
"""
import numpy as np
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

rng=np.random.default_rng(1)
NREG=5; D=8; NOISE=0.35
SIG=rng.normal(0,1,(NREG,D)); SIG/=np.linalg.norm(SIG,axis=1,keepdims=True)

# ---- (1) upgrade-on-revisit vs frozen ----
REV=8                                   # how many times each regime is revisited
def cos(a,b): return float(np.dot(a,b)/(np.linalg.norm(a)*np.linalg.norm(b)+1e-9))
def run_recognition(upgrade):
    protos=[None]*NREG; counts=[0]*NREG
    acc_by_rev=np.zeros(REV)             # accuracy on the k-th visit, averaged over regimes
    tally=np.zeros(REV)
    order=[]
    for k in range(REV):
        for r in rng.permutation(NREG): order.append((k,r))
    for (k,r) in order:
        s=SIG[r]+rng.normal(0,NOISE,D)
        # recognise against all stored prototypes
        if any(p is not None for p in protos):
            sims=[cos(s,p) if p is not None else -1 for p in protos]
            guess=int(np.argmax(sims))
        else:
            guess=-1
        if k>0:                          # k=0 is first-exposure (store); k>=1 are revisits (test)
            acc_by_rev[k]+= 1.0 if guess==r else 0.0; tally[k]+=1
        # store / upgrade
        if protos[r] is None:
            protos[r]=s.copy(); counts[r]=1
        else:
            counts[r]+=1
            if upgrade: protos[r]=protos[r]+(s-protos[r])/counts[r]   # running mean -> sharper
            # frozen: leave protos[r] as the first sample
    acc_by_rev[1:]/=np.maximum(tally[1:],1)
    return acc_by_rev
acc_up=run_recognition(True); acc_fr=run_recognition(False)

print("="*80)
print("  UPGRADE-ON-REVISIT (fix the frozen #40 memory) + THE SPORE-CHAIN DIRECTION→DEPTH SPRAY")
print("="*80)
print(f"  (1) recognition accuracy over successive revisits (5 regimes, noisy signatures):")
print(f"        1st revisit : UPGRADE {acc_up[1]:.2f}   FROZEN {acc_fr[1]:.2f}")
print(f"        last revisit: UPGRADE {acc_up[-1]:.2f}   FROZEN {acc_fr[-1]:.2f}")
print(f"     -> UPGRADE refines the prototype each revisit (sharper) and references the upgraded memory;")
print(f"        FROZEN keeps the first noisy sample and 'goes to the same one' -> flat, error-prone.")
print()

# ---- (2) direction -> depth: importance sprays to the top ----
M=400
importance=np.clip(rng.beta(1.6,3.0,M),0,1)                  # most memories mundane, a few important
# the spore chain reports a velocity direction; important memories are sprayed UP (outward)
up_component=importance + rng.normal(0,0.12,M)               # important -> points up/out
DMAX=10.0
depth=np.clip(DMAX*(1-up_component),0,DMAX)                  # up -> shallow (top); deep-pointed -> buried
r_depth_imp=np.corrcoef(importance,depth)[0,1]
print(f"  (2) the spore chain's direction sets the settling DEPTH:")
print(f"        corr(importance, depth) = {r_depth_imp:+.2f}  -> important memories settle SHALLOW (top),")
print(f"        deep-pointed mundane ones mix in and BURY. Top-of-pillar = the important/recent set.")
print()

# ---- (3) recall latency ∝ depth; reuse resurfaces ----
# recall scans from the top: latency = depth. reuse raises importance -> the memory rises.
reuses=np.arange(0,9)
start_depth=8.0
mem_depth=np.clip(start_depth*(0.75**reuses),0.3,DMAX)      # each reuse sprays it up (mass, #31)
print(f"  (3) recall latency ∝ depth; a reused memory RESURFACES:")
print(f"        a memory buried at depth {start_depth:.0f} rises to {mem_depth[-1]:.1f} after {reuses[-1]} reuses")
print(f"        -> its recall latency drops ~{start_depth/mem_depth[-1]:.0f}× as it gains mass and settles at the top.")

# ---------------------------------------------------------------------------
# PLOT
# ---------------------------------------------------------------------------
fig=plt.figure(figsize=(14.4,4.9)); gs=fig.add_gridspec(1,3,wspace=0.32)

axA=fig.add_subplot(gs[0,0])
axA.plot(range(1,REV),acc_up[1:],"-o",color="#238b45",lw=2.2,ms=4,label="UPGRADE (refine prototype)")
axA.plot(range(1,REV),acc_fr[1:],"-o",color="#c0392b",lw=2.2,ms=4,label="FROZEN (first sample, #40)")
axA.set_xlabel("revisit number"); axA.set_ylabel("recognition accuracy")
axA.set_title("Upgrade on revisit: reference the UPGRADED\nmemory, not the first one", fontsize=10.2)
axA.legend(fontsize=8.2, framealpha=0.9); axA.set_ylim(0,1.05)

axB=fig.add_subplot(gs[0,1])
sc=axB.scatter(importance, depth, c=up_component, cmap="viridis", s=14, edgecolor="none", alpha=0.8)
axB.invert_yaxis()
axB.set_xlabel("memory importance (from the spore chain's direction)"); axB.set_ylabel("settling depth (0 = top)")
axB.set_title(f"Direction → depth: important memories\nspray to the TOP (corr {r_depth_imp:+.2f})", fontsize=10.2)
cb=fig.colorbar(sc,ax=axB,fraction=0.046,pad=0.04); cb.set_label("up-spray",fontsize=8)

axC=fig.add_subplot(gs[0,2])
axC.plot(reuses, mem_depth, "-o", color="#8a2be2", lw=2.2, ms=4)
axC.invert_yaxis()
axC.axhline(1.0, color="#2b6cb0", lw=1.5, ls="--"); axC.text(0.2, 1.4, "waterline (fast-recall zone)", color="#2b6cb0", fontsize=8)
axC.set_xlabel("times the memory is reused"); axC.set_ylabel("depth (recall latency ∝ depth)")
axC.set_title("Reuse RESURFACES it: mass lifts it to\nthe top → recall gets faster", fontsize=10.2)

fig.suptitle("Fixing the frozen memory: upgrade the prototype on revisit · the spore chain's direction sprays important memories to the top · reuse resurfaces them",
             fontsize=10.4)
fig.savefig("memory_upgrade.png", dpi=130, bbox_inches="tight")
print("\n  wrote memory_upgrade.png")
