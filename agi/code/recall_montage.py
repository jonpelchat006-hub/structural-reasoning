#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
recall_montage.py -- #44: the pillar plays a VIDEO that must cover certain TOPICS; because pillars are
blended, it CUTS IN scenes from other movies to fill topics the home pillar is missing (recall against an
EXPECTATION of what the topic should contain). And the void reserve gates consolidation: memories arriving
too FAST collapse the void and fully BLEND (un-sourceable); arriving CALMLY they keep the void intact and
LAYER on top (separable, sourceable).

Jonathan's two reads:
  1. TOPIC-TEMPLATED MONTAGE. Recalling "high-school math AS IT SHOULD BE TAUGHT" (precalculus) is not the
     same as recalling "my experience at that level." The canonical topic template names topics the home
     pillar never actually stored (you learned some of them at university), so recall must CUT to the
     university movie to cover them -- a montage assembled to satisfy the topic template (the expectation).
  2. RATE-GATED CONSOLIDATION. New memories carry a mixing demand paid from the .14/void reserve. Too fast
     -> the reserve crashes past its floor -> the void COLLAPSES and the memory fully blends into the layer
     below (provenance lost). Calm -> the reserve refills between arrivals -> the void holds and the memory
     LAYERS on top, staying distinct and sourceable.

Grounded:
  * #28 pillar_band -- as episodes stack and align they BLEND; per-instance discrimination collapses
    100%->19% ("days blending together"). This is the fully-blended (fast) end.
  * FOLDING_VOID_LINE_DRAW / saturation budget -- spend mixing DOWN TO a fixed non-zero reserve (~1/5),
    "never past it"; past it the boundary dissolves. The collapse threshold.
  * FOLDING_COMBINE_MEMBRANE -- slide a new element in, it dissolves and expands the layer; the un-absorbed
    part is residue. Fast/over-budget dissolution = full blend; calm = clean layering.
  * SPARSE_VESICA §23 -- recall is RECONSTRUCTIVE against context; §23.4 the chunk codebook has a COVERAGE
    metric (does it contain the foundation and span all directions) -- the topic template is that coverage.

MEASURED:
  (A) MONTAGE: recalling the canonical topic template needs cross-pillar cuts; recalling lived experience
      does not. Home-pillar coverage of the template is incomplete; the montage completes it by cutting to
      other movies; the CUT RATE is high for the canonical query, ~0 for the experience query.
  (B) RATE GATE: provenance-recovery (can you tell which movie a scene came from) stays high while arrivals
      are calm and COLLAPSES past a critical arrival rate -- the void-collapse threshold.
  (C) THE RESERVE TRAJECTORY: calm arrivals keep the reserve above the collapse floor (layers stay
      separate); fast arrivals crash it below (layers blend) -- the mechanism behind (B).
"""
import numpy as np
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

rng=np.random.default_rng(11)

# ===========================================================================
# (A) topic-templated montage recall
# ===========================================================================
LEVELS=["grade","high school","university"]
PER=6                                     # canonical topics per level
NT=PER*len(LEVELS)
canonical_level=np.repeat([0,1,2],PER)    # what SHOULD be taught where (the template)
# what the person ACTUALLY experienced: mostly matches, but some canonically-HS topics were
# only learned at UNIVERSITY (displaced up), and a couple grade topics revisited in HS.
experienced_level=canonical_level.copy()
hs=np.where(canonical_level==1)[0]
displaced_up=rng.choice(hs,size=2,replace=False)      # 2 HS-canonical topics learned at university
experienced_level[displaced_up]=2
gr=np.where(canonical_level==0)[0]
displaced_hs=rng.choice(gr,size=1,replace=False)      # 1 grade topic re-experienced in HS
experienced_level[displaced_hs]=1

pillar={L:set(np.where(experienced_level==L)[0]) for L in range(3)}

def recall(level, mode):
    """mode='experience' -> what I lived at this level; 'canonical' -> what SHOULD be taught at it."""
    if mode=="experience":
        want=set(np.where(experienced_level==level)[0])
    else:
        want=set(np.where(canonical_level==level)[0])
    home=pillar[level]
    covered_home=want & home
    need_cut=want - home                                # topics the home movie lacks -> cut from elsewhere
    # montage: fetch each missing topic from whatever pillar actually stored it
    montage_cover=set(covered_home)
    cuts=0
    for t in need_cut:
        src=experienced_level[t]                        # the movie that actually has this scene
        if t in pillar[src]:
            montage_cover.add(t); cuts+=1
    return dict(want=len(want), home=len(covered_home), montage=len(montage_cover),
                cut_rate=cuts/max(len(want),1))

# focus on the high-school level (the precalculus example)
exp=recall(1,"experience"); can=recall(1,"canonical")
print("="*80)
print("  #44  MONTAGE RECALL + RATE-GATED CONSOLIDATION")
print("="*80)
print("  (A) recalling the HIGH-SCHOOL pillar two ways:")
print(f"      'what I EXPERIENCED at HS' : home covers {exp['home']}/{exp['want']}  cuts to other movies: {exp['cut_rate']*100:.0f}%")
print(f"      'what SHOULD be taught (precalc template)': home covers {can['home']}/{can['want']} -> montage {can['montage']}/{can['want']}"
      f"  cuts: {can['cut_rate']*100:.0f}%")
print("      -> the canonical template names topics the HS pillar never stored (learned at university),")
print("         so recall CUTS to the university movie to cover them; lived-experience recall needs no cuts.")
print()

# ===========================================================================
# (B)+(C) rate-gated consolidation: void collapse vs calm layering
# ===========================================================================
D=10; NMEM=14
sigs=rng.normal(0,1,(NMEM,D)); sigs/=np.linalg.norm(sigs,axis=1,keepdims=True)
COLLAPSE=0.2          # the saturation-budget floor (~1/5); below it the void dissolves and blends
REFILL=1.0           # reserve refill per unit time between arrivals
COST=0.6             # mixing demand each arrival draws from the reserve

def layer_stack(rate, record=False):
    """Arrivals every 1/rate. Reserve refills between; if it drops below COLLAPSE at an arrival, that
    memory BLENDS into the running blob (provenance lost); else it layers cleanly (kept distinct)."""
    V=1.0; dt=1.0/rate
    stored=[]; blended=np.zeros(NMEM,dtype=bool); traj=[(0.0,V)]
    blob=None
    for i in range(NMEM):
        V=min(1.0, V+REFILL*dt)          # refill since last arrival
        V-=COST                           # this arrival's mixing demand
        if record: traj.append((i*dt, V))
        if V<COLLAPSE:                     # void collapses -> full blend into the blob
            blended[i]=True
            blob = sigs[i].copy() if blob is None else (0.6*blob+0.4*sigs[i])
            blob/=np.linalg.norm(blob)
            stored.append(blob.copy())     # stored as the indistinct blob (can't be sourced)
            V=max(V, COLLAPSE*0.5)         # partial recovery, still stressed
        else:                              # void intact -> clean layer on top
            stored.append(sigs[i].copy())
    stored=np.array(stored)
    # provenance recovery: probe each true signature (noisy), does nearest stored layer = its own source?
    ok=0
    for i in range(NMEM):
        p=sigs[i]+rng.normal(0,0.25,D)
        sims=stored@p/(np.linalg.norm(stored,axis=1)*np.linalg.norm(p)+1e-9)
        if int(np.argmax(sims))==i: ok+=1
    recovery=ok/NMEM
    if record: return recovery, blended.mean(), traj
    return recovery, blended.mean()

rates=np.linspace(0.6,3.0,16)
rec=[]; blendfrac=[]
for r in rates:
    vals=[layer_stack(r) for _ in range(12)]
    rec.append(np.mean([v[0] for v in vals])); blendfrac.append(np.mean([v[1] for v in vals]))
rec=np.array(rec); blendfrac=np.array(blendfrac)
# critical rate where the reserve first cannot refill above the collapse floor: REFILL/rate < COST-COLLAPSE
crit_rate=REFILL/(COST-COLLAPSE)      # dt*REFILL must cover COST above the floor
_,_,traj_calm=layer_stack(0.8,record=True)
_,_,traj_fast=layer_stack(2.6,record=True)

print("  (B) provenance-recovery (can you source each scene) vs arrival rate:")
print(f"      calm (rate {rates[0]:.1f}) recovery {rec[0]:.2f}, blended {blendfrac[0]*100:.0f}%  ->  "
      f"fast (rate {rates[-1]:.1f}) recovery {rec[-1]:.2f}, blended {blendfrac[-1]*100:.0f}%")
print(f"      void-collapse threshold at arrival rate ~{crit_rate:.2f} (refill can no longer clear the demand).")
print("  (C) reserve trajectory: calm stays above the collapse floor (layers stay separate); fast crashes")
print("      below it (memories blend) -- the mechanism behind (B).")

# ===========================================================================
# PLOT
# ===========================================================================
fig=plt.figure(figsize=(15.2,4.8)); gs=fig.add_gridspec(1,3,wspace=0.30)
HOME="#888"; MON="#238b45"; CUT="#c0392b"

# (A) montage coverage + cut rate
axA=fig.add_subplot(gs[0,0])
x=np.arange(2); w=0.36
axA.bar(x-w/2,[exp['home'],can['home']],w,color=HOME,label="home pillar alone")
axA.bar(x+w/2,[exp['montage'],can['montage']],w,color=MON,label="montage (cut across movies)")
axA.axhline(PER,color="#bbb",ls=":",lw=1); axA.text(1.4,PER+0.05,"template = 6 topics",fontsize=7.6,color="#999")
for i,(h,m,cr) in enumerate([(exp['home'],exp['montage'],exp['cut_rate']),(can['home'],can['montage'],can['cut_rate'])]):
    axA.text(i+w/2,m+0.12,f"cut {cr*100:.0f}%",ha="center",fontsize=8.4,color=CUT)
axA.set_xticks(x); axA.set_xticklabels(["'what I\nEXPERIENCED'","'what SHOULD be\ntaught' (precalc)"],fontsize=8.6)
axA.set_ylabel("HS topics covered"); axA.set_ylim(0,PER+1.2)
axA.legend(fontsize=7.8,framealpha=0.9,loc="lower left")
axA.set_title("(A) Montage recall: the canonical template\ncuts to other movies to cover its topics",fontsize=10.0)

# (B) provenance recovery vs rate
axB=fig.add_subplot(gs[0,1])
axB.plot(rates,rec,"-o",color=MON,lw=2,ms=4,label="provenance recovery")
axB.plot(rates,1-blendfrac,"-o",color="#2b6cb0",lw=1.6,ms=3,label="fraction kept separate")
axB.axvline(crit_rate,color="#c0392b",ls="--",lw=1.4); axB.text(crit_rate+0.03,0.35,"void collapse",color="#c0392b",fontsize=8,rotation=90,va="center")
axB.axvspan(rates[0],crit_rate,color=MON,alpha=0.06); axB.axvspan(crit_rate,rates[-1],color=CUT,alpha=0.06)
axB.set_xlabel("arrival rate (memories per unit time)"); axB.set_ylabel("recovery / separability"); axB.set_ylim(0,1.05)
axB.legend(fontsize=7.8,framealpha=0.9,loc="lower left")
axB.set_title("(B) Too fast → the void collapses and memories\nblend (un-sourceable); calm → they stay separate",fontsize=10.0)

# (C) reserve trajectory calm vs fast
axC=fig.add_subplot(gs[0,2])
tc=np.array(traj_calm); tf=np.array(traj_fast)
axC.plot(tc[:,0],tc[:,1],"-o",color=MON,lw=2,ms=3,label="calm arrivals (layer on top)")
axC.plot(tf[:,0],tf[:,1],"-o",color=CUT,lw=2,ms=3,label="fast arrivals (blend)")
axC.axhline(COLLAPSE,color="#555",ls="--",lw=1.3); axC.text(tc[-1,0]*0.4,COLLAPSE+0.03,"collapse floor (~1/5 reserve)",fontsize=7.8,color="#555")
axC.set_xlabel("time"); axC.set_ylabel("void reserve"); axC.set_ylim(0,1.05)
axC.legend(fontsize=7.8,framealpha=0.9,loc="upper right")
axC.set_title("(C) The reserve: calm stays above the floor,\nfast crashes below it → the void breaks",fontsize=10.0)

fig.suptitle("#44 — recall is a montage assembled to a topic template (cut across movies to cover it); and the void reserve gates consolidation: fast arrivals collapse it and blend, calm arrivals layer on top",fontsize=10.2)
fig.savefig("recall_montage.png",dpi=130,bbox_inches="tight")
print("\n  wrote recall_montage.png")
