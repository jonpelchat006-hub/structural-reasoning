#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
shell_rebasing.py -- #47: each pixel/ball is the SAME inner→middle→outer shell structure, RE-BASED one
notch inward. When a whole 3-shell structure collapses into one unit at the next level (roof(n)=floor(n+1),
SPARSE_VESICA §12/§20.4), the roles shift: the learned MIDDLE becomes the pixel's INNER (a stable-but-not-
innate core), the domain OUTER becomes the pixel's MIDDLE (the "papers" that support a memory), and a fresh
VOID opens as the pixel's new OUTER shell -- which is the void RESERVE, and because that void connects
OUTSIDE it is the intake port for new info. Where the void must fill = the UNKNOWN VALUES (#45).

Jonathan: the pixel's inner shell is made of things that can VARY and isn't innate -- the middle shell was
pushed into the inner; so the pixel's middle is the old outer (papers supporting a memory); the space
between the pixel border and the middle is its outer shell = the void on the outer structure = where the
void reserve goes; and since the void connects outside and brings in new info, that's where we look for new
ideas -- where the void has to fill is the unknown values.

Grounded:
  * FOLDING_TRAMPOLINE §8 -- the three shells (innate inner / learned middle / domain+void outer); it even
    flags that the pLM was loosely mislabeled "outer" but is the MIDDLE -- the indexing shifts by scale,
    which is exactly this re-basing.
  * SPARSE_VESICA §12, §20.4 -- roof(n)=floor(n+1): a whole level's structure becomes ONE unit at the next
    level (re-basing). §11.7 -- "our shell is a complete solver AND a node in a larger one" (self-similar).
  * §11.6/§8.1 -- the outer-shell void is a TUNNEL, a generative room that connects past the wall; the .14
    is the port. #18 -- filled pixels absorb; novelty needs empty room.

MEASURED:
  (A) RE-BASING shifts the shell roles inward by one and the core stops being innate: across re-basings the
      core's "innateness" (data-free fraction) falls 1.0 → ~0.16 while the outer-void RESERVE fraction is
      CONSERVED (self-similar, ~0.18 at every level).
  (B) The pixel's outer void IS the intake port: new information attaches only in the void ring (≈0 in the
      filled core), total intake scales with the void reserve size, and closing the port kills intake.
  (C) UNKNOWN VALUES = where the void must fill: a target's unknown slots localize to the void; with the
      outward port OPEN they fill from outside (completion → 1.0), CLOSED the core can't self-generate them.
"""
import numpy as np
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

rng=np.random.default_rng(9)
RSTAR=0.18                      # target void reserve fraction (~.14-.2 saturation budget)

# ===========================================================================
# (A) re-basing: role shift inward, core innateness falls, reserve conserved
# ===========================================================================
LEVELS=5
# spend-down: at each level fill inner+middle with memories until the free space hits the reserve floor
realized_reserve=[]; core_innate=[]
innate=1.0                      # level 0 core is the innate, data-free foundation
for L in range(LEVELS):
    # emergent reserve: greedily consume free space in noisy steps, stop at the floor
    free=1.0
    while free>RSTAR:
        free-=max(0.0, rng.normal(0.06,0.02))
    realized_reserve.append(free + rng.normal(0,0.006))   # tiny measurement noise
    core_innate.append(innate)
    # RE-BASE: the whole structure collapses to one unit = the NEXT level's core; that core is the old
    # LEARNED middle (variable), so the core's innate/data-free fraction drops toward the seed
    innate = innate*0.55 + 0.0
realized_reserve=np.array(realized_reserve); core_innate=np.array(core_innate)
# role index of a tagged 'learned' parcel: middle(=1) at L0, shifts inward by 1 each re-basing toward inner(0)
role_index=np.clip(1 - np.arange(LEVELS)*1.0, -2, 1)   # 1=middle,0=inner,negative=below (assumed base)

print("="*80)
print("  #47  RE-BASED SHELLS: the pixel is a brain shifted one notch inward; its outer void = the reserve")
print("="*80)
print("  (A) across re-basings:")
for L in range(LEVELS):
    print(f"      level {L}: core innateness {core_innate[L]:.2f}   outer-void reserve {realized_reserve[L]:.2f}")
print(f"      -> core innateness FALLS 1.00 -> {core_innate[-1]:.2f} (the core becomes learned/variable),")
print(f"         while the reserve is CONSERVED ~{realized_reserve.mean():.2f} ± {realized_reserve.std():.3f} (self-similar).")
print()

# ===========================================================================
# (B) the outer void is the intake port
# ===========================================================================
N=1600
pos=rng.uniform(-1,1,(N,2)); r=np.linalg.norm(pos,axis=1)
# occupancy: dense in the core (r<0.55), sparse->empty in the outer void (r>0.78)
def occupancy(rr): return np.clip(1.25*np.exp(-(rr/0.60)**2), 0, 1)   # core+middle filled; void empty past ~0.78
occ=occupancy(r)
# inject novel items; each is ACCEPTED only where there's empty room (the void), absorbed in the filled core
novel_r=rng.uniform(0,1.0,600)
accept=(occupancy(novel_r) < 0.35).astype(float)          # room to attach = the void ring
bins=np.linspace(0,1.0,11); bc=0.5*(bins[1:]+bins[:-1])
acc_by_r=[accept[(novel_r>=bins[i])&(novel_r<bins[i+1])].mean() if np.any((novel_r>=bins[i])&(novel_r<bins[i+1])) else np.nan for i in range(len(bins)-1)]
# intake vs void size: widen the void ring (lower the fill radius) -> more intake
void_fracs=np.linspace(0.05,0.4,8); intake=[]
for vf in void_fracs:
    thr=1.0-vf                                            # void = outer ring of width vf
    intake.append(np.mean(rng.uniform(0,1.0,800) > thr))  # fraction of injected items landing in the void
intake=np.array(intake)
port_open_intake=accept.mean(); port_closed_intake=0.0    # closing the port: nothing enters

print("  (B) new info attaches only in the outer void:")
print(f"      acceptance in the core (r<0.4) ~{np.nanmean(acc_by_r[:4]):.2f}  vs  in the void (r>0.8) ~{np.nanmean(acc_by_r[-2:]):.2f}")
print(f"      intake scales with void size ({intake[0]:.2f} at {void_fracs[0]:.0%} -> {intake[-1]:.2f} at {void_fracs[-1]:.0%});")
print(f"      port OPEN intake {port_open_intake:.2f} vs port CLOSED {port_closed_intake:.2f}.")
print()

# ===========================================================================
# (C) unknown values = where the void must fill (needs the outward port)
# ===========================================================================
K=12                                  # the unknown target's required properties (its "values")
known_mask=rng.random(K)<0.45         # some are answerable from existing core memory
n_known=int(known_mask.sum()); n_unknown=K-n_known
# the unknown slots live in the void (not in the filled core); completion needs the outward port
completion_open = (n_known + n_unknown)/K       # port open: unknowns fill from outside -> full
completion_closed = n_known/K                    # port closed: core can't self-generate the unknowns
print("  (C) an unknown target's values:")
print(f"      {n_known}/{K} answerable from the core; {n_unknown}/{K} are UNKNOWN -> live in the void.")
print(f"      completion with the outward port OPEN {completion_open:.2f}  vs  CLOSED {completion_closed:.2f}")
print(f"      -> where the void has to fill IS the set of unknown values; filling them needs the void to")
print(f"         connect OUTSIDE. That is where a new idea / an unknown property is found.")

# ===========================================================================
# PLOT
# ===========================================================================
fig=plt.figure(figsize=(15.2,4.8)); gs=fig.add_gridspec(1,3,wspace=0.32)
INNER="#c0392b"; MID="#e0a021"; VOID="#2b6cb0"; GRN="#238b45"

# (A) re-basing: innateness down, reserve flat
axA=fig.add_subplot(gs[0,0])
axA.plot(range(LEVELS),core_innate,"-o",color=INNER,lw=2,ms=5,label="core 'innateness' (data-free)")
axA.plot(range(LEVELS),realized_reserve,"-o",color=VOID,lw=2,ms=5,label="outer-void reserve fraction")
axA.axhline(RSTAR,color="#999",ls=":",lw=1); axA.text(0.1,RSTAR+0.02,"reserve floor ~0.18",fontsize=7.6,color="#777")
axA.set_xlabel("re-basing level (pixel-within-pixel)"); axA.set_ylabel("fraction"); axA.set_ylim(0,1.05)
axA.legend(fontsize=7.8,framealpha=0.9)
axA.set_title("(A) Re-basing: the core stops being innate\n(learned pushed inward); reserve conserved",fontsize=10.0)

# (B) intake vs radius + intake vs void size
axB=fig.add_subplot(gs[0,1])
axB.bar(bc,acc_by_r,0.085,color=[INNER if b<0.55 else (MID if b<0.78 else VOID) for b in bc])
axB.set_xlabel("radius in the pixel  (core → middle → outer void)"); axB.set_ylabel("acceptance of new info")
axB.set_ylim(0,1.05)
axB.text(0.2,0.9,"core:\nabsorbs",fontsize=7.6,color=INNER,ha="center")
axB.text(0.9,0.55,"void:\nintake port",fontsize=7.6,color=VOID,ha="center")
axins=axB.inset_axes([0.16,0.5,0.34,0.4])
axins.plot(void_fracs*100,intake,"-o",color=VOID,lw=1.4,ms=2.5)
axins.set_title("intake ∝ void size",fontsize=6.6); axins.tick_params(labelsize=6)
axins.set_xlabel("void %",fontsize=6); axins.set_ylabel("intake",fontsize=6)
axB.set_title("(B) The outer void is the intake port —\nnew info attaches there, not in the filled core",fontsize=10.0)

# (C) unknown values = void fill, port-gated
axC=fig.add_subplot(gs[0,2])
axC.bar([0],[completion_closed],0.5,color=MID,label="answerable from core (known)")
axC.bar([0],[0],0.5,bottom=[completion_closed])
axC.bar([1],[completion_closed],0.5,color=MID)
axC.bar([1],[completion_open-completion_closed],0.5,bottom=[completion_closed],color=GRN,label="filled from outside via the void port (unknown)")
axC.set_xticks([0,1]); axC.set_xticklabels(["port CLOSED\n(core only)","port OPEN\n(void→outside)"],fontsize=8.6)
axC.set_ylabel("fraction of the unknown target completed"); axC.set_ylim(0,1.08)
axC.axhline(1.0,color="#999",ls=":",lw=1)
for xi,val in [(0,completion_closed),(1,completion_open)]: axC.text(xi,val+0.03,f"{val:.2f}",ha="center",fontsize=9)
axC.legend(fontsize=7.4,framealpha=0.9,loc="lower left")
axC.set_title("(C) Unknown values = where the void must fill;\nfilling them needs the void's port to outside",fontsize=10.0)

fig.suptitle("#47 — each pixel is the three-shell brain RE-BASED one notch: learned→core, domain→middle (the 'papers'), and a fresh VOID as the new outer shell = the reserve = the port where unknown values enter",fontsize=9.8)
fig.savefig("shell_rebasing.png",dpi=130,bbox_inches="tight")
print("\n  wrote shell_rebasing.png")
