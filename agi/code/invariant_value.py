#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
invariant_value.py -- #45: what an UNKNOWN target values = the feature that is COMMON to all examples and
MOVES all of them (an invariant), NOT a spurious feature that only correlates on a subset. And the TOPIC is
the pillar's BORDER (upgradable — add a foreign synonym and the pillar answers foreign queries), while the
BALL inside is the substance.

Jonathan: not knowing what unknown things value is where every scientist is stuck -- if we knew exactly what
properties a cancer cure needs we'd have it. People put spurious things (skin colour) as most important for
education, but real education isn't based on that; it should be based on what the memories have in COMMON or
what CHANGES all of them, not some. And the topic must be flexible/upgradable -- add "UK secondary school" to
the border so we answer with high-school memories -- the border holds the topic, the ball holds the substance.

Grounded:
  * MINING_NOTES #3 -- the "common-ancestor abstraction filter": climb to the most specific abstraction
    COMMON TO ALL examples, not the surface rule that fits only one (anti-overfit). This IS "common to all."
  * INNER_SHELL knot/tail -- the KNOT is the axes a thing NEVER changes (invariant core); the real identity
    is the invariant, the spurious is a reactive tail that only moves a subset.
  * FOLDING_ARMS_AND_BRACING / OBSERVERS_AS_D -- a merely CORRELATED feature is not independent evidence; a
    confound co-occurs but moves the posterior by 0. Stability across environments separates cause from
    confound (invariant-causal-prediction).

MEASURED:
  (A) A spurious feature correlates with the target in the sample but its sign FLIPS across environments;
      selecting features by "correlates here" picks it up and COLLAPSES out-of-distribution, while selecting
      by "stable/invariant across environments" (common to all, moves all consistently) holds up.
  (B) Ranking features by (shared across all environments) × (stability of its effect) separates the true
      invariant (high/high) from the confound (high correlation but unstable) and from noise.
  (C) The upgradable BORDER: a foreign-synonym query misses the pillar until the synonym is ADDED to the
      border; then the same query returns the pillar's ball (substance unchanged).
"""
import numpy as np
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

rng=np.random.default_rng(5)
NE=4                     # environments (e.g., schools/populations/labs)
NPER=400                 # samples per environment
# features: 2 true causal (invariant), 1 spurious (sign flips per env), 2 noise
NC=2; NF=NC+1+2
CAUSAL=[0,1]; SPUR=2; NOISE=[3,4]
w=np.array([1.2,-0.9])   # true causal weights (env-invariant)

def make_env(e, spur_sign):
    X=rng.normal(0,1,(NPER,NF))
    y = X[:,CAUSAL]@w + rng.normal(0,0.3,NPER)          # target driven ONLY by causal features
    # spurious feature is correlated with y in this env, but with an env-specific SIGN
    X[:,SPUR] = spur_sign*(y - y.mean())/ (y.std()+1e-9) + rng.normal(0,0.6,NPER)
    return X,y

# the spurious feature's coupling VARIES across the training environments (so its instability is visible if
# you look across them); the naive scientist only looks at ONE sample (env 0), where it correlates strongly.
signs=[+1.0,-1.0,+0.8]; test_sign=-1.0
train=[make_env(e,signs[e]) for e in range(3)]
Xtr=np.vstack([x for x,_ in train]); ytr=np.concatenate([y for _,y in train])
X0,y0=train[0]                                     # the single sample the naive scientist has
Xte,yte=make_env(3,test_sign)                      # a new population (OOD)

# per-environment correlation of each feature with y
corr_by_env=np.zeros((3,NF))
for e,(X,y) in enumerate(train):
    for f in range(NF):
        corr_by_env[e,f]=np.corrcoef(X[:,f],y)[0,1]
mean_abscorr=np.abs(corr_by_env).mean(0)
stability=1.0-np.abs(corr_by_env.std(0))/(np.abs(corr_by_env).mean(0)+1e-9)  # consistent across envs?
stability=np.clip(stability,0,1)

def fit_eval(feats, Xfit, yfit):
    A=np.c_[Xfit[:,feats],np.ones(len(Xfit))]
    coef,_,_,_=np.linalg.lstsq(A,yfit,rcond=None)
    def r2(X,y):
        p=np.c_[X[:,feats],np.ones(len(X))]@coef
        return 1-np.sum((y-p)**2)/np.sum((y-y.mean())**2)
    return r2(Xfit,yfit), r2(Xte,yte)

# naive: look at ONE sample, pick the features most correlated with y there, fit on it
naive_corr=np.array([abs(np.corrcoef(X0[:,f],y0)[0,1]) for f in range(NF)])
naive_feats=list(np.argsort(naive_corr)[::-1][:2])            # top-2 in the single sample -> grabs the confound
# invariant: pick features whose effect is STABLE across environments (common to all, consistent), fit pooled
invariant_feats=[f for f in range(NF) if stability[f]>0.6 and mean_abscorr[f]>0.2]

tr_n,te_n=fit_eval(naive_feats, X0, y0)
tr_i,te_i=fit_eval(invariant_feats, Xtr, ytr)

print("="*80)
print("  #45  WHAT AN UNKNOWN VALUES: the invariant (common to/moves all) vs the spurious confound")
print("="*80)
print(f"  features: causal={CAUSAL}, spurious={SPUR} (sign flips OOD), noise={NOISE}")
print(f"  naive selector picks (top-correlated in ONE sample): {[int(f) for f in naive_feats]}  -> includes spurious {SPUR in naive_feats}")
print(f"  invariant selector picks (stable across envs): {[int(f) for f in invariant_feats]}  -> {'excludes' if SPUR not in invariant_feats else 'INCLUDES'} spurious")
print(f"  in-distribution R^2 : naive {tr_n:.2f}   invariant {tr_i:.2f}")
print(f"  OUT-OF-DIST   R^2 : naive {te_n:.2f}   invariant {te_i:.2f}   <-- the spurious selector collapses")
print()

# ---- (C) the upgradable border ----
ball_substance=["quadratics","trig","precalculus","geometry proofs","functions"]   # the HS ball
border={"high school","grade 11","grade 12"}                                        # initial topic border
def answer(query):
    return ball_substance if query in border else None
foreign=["secondary school","sixth form","key stage 4","year 11"]
before=[answer(q) is not None for q in foreign]
border |= set(foreign)                     # UPGRADE the border with the foreign synonyms
after=[answer(q) is not None for q in foreign]
print("  (C) upgradable border (topic) vs the ball (substance):")
print(f"      foreign queries answered BEFORE adding to border: {sum(before)}/{len(foreign)}")
print(f"      foreign queries answered AFTER  adding to border: {sum(after)}/{len(foreign)}  (ball substance unchanged)")

# ---------------------------------------------------------------------------
# PLOT
# ---------------------------------------------------------------------------
fig=plt.figure(figsize=(15.2,4.8)); gs=fig.add_gridspec(1,3,wspace=0.32)
NAIVE="#c0392b"; INV="#238b45"

axA=fig.add_subplot(gs[0,0])
x=np.arange(2); wdt=0.36
axA.bar(x-wdt/2,[tr_n,te_n],wdt,color=NAIVE,label="naive (top-correlated → grabs the confound)")
axA.bar(x+wdt/2,[tr_i,te_i],wdt,color=INV,label="invariant (stable/common across environments)")
axA.set_xticks(x); axA.set_xticklabels(["in-distribution","OUT-of-distribution\n(confound flips)"],fontsize=8.8)
axA.set_ylabel("predictive R²"); axA.set_ylim(min(0,te_n)-0.1,1.05)
axA.axhline(0,color="#999",lw=0.8)
axA.legend(fontsize=7.6,framealpha=0.9,loc="lower left")
axA.set_title("(A) Choosing by 'what correlates here' collapses\nOOD; choosing the invariant holds",fontsize=10.0)

axB=fig.add_subplot(gs[0,1])
labels={0:"causal",1:"causal",2:"SPURIOUS\n(confound)",3:"noise",4:"noise"}
cols={0:INV,1:INV,2:NAIVE,3:"#999",4:"#999"}
for f in range(NF):
    axB.scatter(mean_abscorr[f],stability[f],s=90,color=cols[f],edgecolor="white",zorder=3)
    axB.annotate(labels[f],(mean_abscorr[f],stability[f]),fontsize=7.6,ha="center",
                 xytext=(0,9),textcoords="offset points")
axB.axhline(0.6,color="#888",ls="--",lw=1); axB.text(0.02,0.62,"stability gate",fontsize=7.6,color="#666")
axB.set_xlabel("shared / correlated across examples"); axB.set_ylabel("stability of its effect (moves ALL, not some)")
axB.set_xlim(-0.02,1.02); axB.set_ylim(-0.05,1.08)
axB.set_title("(B) The real basis = high correlation AND stable;\nthe confound is correlated but unstable",fontsize=10.0)

axC=fig.add_subplot(gs[0,2])
axC.bar([0,1],[sum(before),sum(after)],0.5,color=["#c0392b","#238b45"])
for i,v in enumerate([sum(before),sum(after)]): axC.text(i,v+0.08,f"{v}/{len(foreign)}",ha="center",fontsize=10)
axC.set_xticks([0,1]); axC.set_xticklabels(["before\n(border lacks synonym)","after\n(synonym added to border)"],fontsize=8.6)
axC.set_ylabel("foreign queries the pillar answers"); axC.set_ylim(0,len(foreign)+0.6)
axC.set_title("(C) The topic is the pillar's upgradable BORDER;\nadd a synonym → it answers, ball unchanged",fontsize=10.0)

fig.suptitle("#45 — what an unknown values is the INVARIANT common to/that moves all examples, not a spurious confound; the topic lives on the pillar's upgradable BORDER, the ball is the substance",fontsize=10.0)
fig.savefig("invariant_value.png",dpi=130,bbox_inches="tight")
print("\n  wrote invariant_value.png")
