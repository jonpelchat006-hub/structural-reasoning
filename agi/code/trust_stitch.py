#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trust_stitch.py -- #43: the memory upgrade is trust-gated by a FUNCTIONAL regression test
("can the new memory do what the old one did, plus more?"); complementary memories STITCH to
cover each other's gaps; and the folded "ball" IS the combination, whose TRUST to a lens = what
that ball is made of.

Jonathan's chain, grounded:
  * TRUST SYSTEM / truth detector -- Shovelcat_29 builds trust as a field (reputation R; "Void =
    bandwidth for VERIFICATION"; reputation-weighted influence). #24 verifies through a gate; #42's
    gate said "upgrade only what you trust." Here trust becomes FUNCTIONAL and PER-LENS.
  * PER-LENS trust -- each orthogonal lens (#38) values different capabilities for trust, and since
    lenses "switch off branches they see," a lens that switches branch RE-WEIGHTS what it trusts.
  * "test for her own usage" -- the real gate is a REGRESSION TEST: accept an upgrade only if it does
    everything the old memory did AND adds more (not just a higher average score).
  * STITCH the gaps -- a higher-scoring but gappy memory is combined with the old to cover the union
    (`FOLDING_OUTER_SLOT`: compatible layers dissipate & merge; the seam-rebuild / matching-slot union).
  * THE BALL folds the layers -- #30's ball is the combine operator over memory layers; "what the ball
    is made of" (which trusted layers supplied it) IS its trust (convergence-of-routes = agreement,
    §18.19; combine-by-dissipation, `FOLDING_OUTER_SLOT`).

MEASURED:
  (A) FUNCTIONAL REGRESSION GATE. Over a stream of upgrade candidates, "replace if higher mean score"
      silently LOSES capabilities (regressions); the regression gate / stitch never regress and cover more.
  (B) STITCHING. A strong-but-gappy candidate fails the gate alone; stitched with the old (per-capability
      best) it covers the UNION -- strictly dominates either memory.
  (C) THE BALL'S TRUST = WHAT IT'S MADE OF. A ball folded from one layer is trusted by only the lens that
      layer serves; a ball folded from diverse trusted layers is trusted by ALL lenses -- and a lens's
      trust equals the fraction of the ball (on the caps it values) supplied by layers IT trusts. When a
      lens switches branch it re-weights, and its trust in the SAME ball changes.
"""
import numpy as np
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

rng=np.random.default_rng(7)
C=12                      # capabilities a memory can serve
TAU=0.5                  # a memory "can do" a capability if quality >= TAU

# ---- the old (incumbent) memory: strong on a base skill set, weak elsewhere ----
q_old=np.full(C,0.12); base=np.arange(0,7); q_old[base]=rng.uniform(0.65,0.85,len(base))

def covered(q): return q>=TAU
def ncov(q): return int(covered(q).sum())

# ---------------------------------------------------------------------------
# (A) functional regression gate over a stream of candidates
# ---------------------------------------------------------------------------
def make_candidate():
    # higher AVERAGE quality, but drops a couple of base skills (gaps) and adds new ones
    q=np.full(C,0.12)
    keep=rng.choice(base,size=len(base)-rng.integers(1,3),replace=False)   # drop 1-2 base skills
    q[keep]=rng.uniform(0.6,0.9,len(keep))
    newcaps=rng.choice(np.arange(7,C),size=rng.integers(1,4),replace=False)
    q[newcaps]=rng.uniform(0.6,0.95,len(newcaps))
    return q

T=40
pol_cov={"naive":[], "regress":[], "stitch":[]}
pol_reg={"naive":0, "regress":0, "stitch":0}
cur={"naive":q_old.copy(), "regress":q_old.copy(), "stitch":q_old.copy()}
rng2=np.random.default_rng(3)
for t in range(T):
    cand=make_candidate()
    # naive: replace if candidate's mean quality is higher (ignores per-capability regressions)
    if cand.mean()>cur["naive"].mean():
        lost=int((covered(cur["naive"]) & ~covered(cand)).sum())
        pol_reg["naive"]+=lost; cur["naive"]=cand.copy()
    # regression gate: replace only if it does >= old on every covered cap AND adds a new one
    passes = np.all(cand[covered(cur["regress"])] >= TAU) and (ncov(cand) > ncov(cur["regress"]))
    if passes:
        cur["regress"]=cand.copy()   # (0 regressions by construction)
    # stitch: fold per-capability best (union); never regresses, absorbs every gain
    before=covered(cur["stitch"]).copy()
    cur["stitch"]=np.maximum(cur["stitch"],cand)
    pol_reg["stitch"]+=int((before & ~covered(cur["stitch"])).sum())  # =0
    for k in pol_cov: pol_cov[k].append(ncov(cur[k]))

# ---------------------------------------------------------------------------
# (B) stitching a strong-but-gappy candidate
# ---------------------------------------------------------------------------
gappy=np.full(C,0.12)
gappy[np.array([0,1,2,3])]=rng.uniform(0.7,0.9,4)        # keeps some base
gappy[np.array([7,8,9,10])]=rng.uniform(0.7,0.95,4)      # adds new -> higher mean
# but MISSES base caps 4,5,6 (gaps) -> fails the regression gate alone
stitch=np.maximum(q_old,gappy)
covB={"old":ncov(q_old),"candidate":ncov(gappy),"stitch":ncov(stitch)}
gappy_passes = np.all(gappy[covered(q_old)]>=TAU)
print("="*80)
print("  #43  TRUST-GATED UPGRADE: functional regression test + stitching + the ball's trust")
print("="*80)
print(f"  (A) over {T} candidates -- capabilities covered / regressions (capabilities silently lost):")
print(f"        naive replace-if-higher-mean : cover {pol_cov['naive'][-1]:2d}   regressions {pol_reg['naive']}")
print(f"        regression gate              : cover {pol_cov['regress'][-1]:2d}   regressions {pol_reg['regress']}")
print(f"        STITCH (fold per-cap best)   : cover {pol_cov['stitch'][-1]:2d}   regressions {pol_reg['stitch']}")
print(f"  (B) a strong-but-gappy candidate: mean quality {gappy.mean():.2f} > old {q_old.mean():.2f}, but it")
print(f"        MISSES base skills -> fails the regression gate alone ({'passes' if gappy_passes else 'FAILS'}).")
print(f"        coverage  old {covB['old']}  candidate {covB['candidate']}  STITCH {covB['stitch']}  (union dominates)")

# ---------------------------------------------------------------------------
# (C) the ball's trust = what it's made of; per-lens; lens switches branch
# ---------------------------------------------------------------------------
L=4
# each lens values a subset of capabilities (its trust criterion), on a "branch"
lens_caps={0:np.array([0,1,2]), 1:np.array([3,4,5]), 2:np.array([7,8]), 3:np.array([9,10,11])}
# which source-layer each lens TRUSTS (its truth detector accepts that provenance)
# layers: 0=old base memory, 1=skills memory, 2=perception memory, 3=social memory
lens_trusts_layer={0:{0}, 1:{0,1}, 2:{1,2}, 3:{2,3}}

# build layers, each strong on some caps, tagged by provenance
def layer(strong):
    q=np.full(C,0.12); q[strong]=rng.uniform(0.7,0.95,len(strong)); return q
layers={0:layer([0,1,2,3,4,5,6]), 1:layer([3,4,7,8]), 2:layer([7,8,9]), 3:layer([9,10,11])}

def fold(layer_ids):
    """fold selected layers into a ball; return quality vector + provenance (winning layer per cap)."""
    q=np.full(C,0.12); prov=np.full(C,-1)
    for lid in layer_ids:
        take=layers[lid]>q
        q[take]=layers[lid][take]; prov[take]=lid
    return q,prov

ball_single,prov_single=fold([1])            # a ball made of ONE layer (skills only)
ball_diverse,prov_diverse=fold([0,1,2,3])    # a ball folded from diverse trusted layers

def lens_trust(q,prov,lens,weights_caps=None):
    caps=lens_caps[lens] if weights_caps is None else weights_caps
    cov=covered(q)[caps]
    # trust = fraction of this lens's valued caps that are (a) covered AND (b) supplied by a layer it trusts
    ok=[covered(q)[c] and (prov[c] in lens_trusts_layer[lens]) for c in caps]
    return float(np.mean(ok)) if len(caps) else 0.0

trust_single=[lens_trust(ball_single,prov_single,l) for l in range(L)]
trust_diverse=[lens_trust(ball_diverse,prov_diverse,l) for l in range(L)]

# lens 0 SWITCHES BRANCH: now values a different cap subset -> its trust in the SAME diverse ball changes
lens0_branchA=lens_caps[0]                      # original branch: caps 0,1,2 (all from trusted layer 0)
lens0_branchB=np.array([7,8,9])                 # switched branch: caps it does NOT trust the provenance of
trust0_A=lens_trust(ball_diverse,prov_diverse,0,lens0_branchA)
trust0_B=lens_trust(ball_diverse,prov_diverse,0,lens0_branchB)

print(f"  (C) the ball's trust = what it's made of (per lens):")
print(f"        one-layer ball  trust by lens: "+", ".join(f"L{l}:{trust_single[l]:.2f}" for l in range(L)))
print(f"        diverse ball    trust by lens: "+", ".join(f"L{l}:{trust_diverse[l]:.2f}" for l in range(L)))
print(f"        -> the diverse ball is trusted across ALL lenses; the single-layer ball only by the lens")
print(f"           whose trusted provenance it is made of.")
print(f"        lens 0 SWITCHES BRANCH on the same ball: trust {trust0_A:.2f} -> {trust0_B:.2f}")
print(f"           (same material, but it now values caps whose provenance it doesn't trust).")

# ---------------------------------------------------------------------------
# PLOT
# ---------------------------------------------------------------------------
fig=plt.figure(figsize=(15.2,4.8)); gs=fig.add_gridspec(1,3,wspace=0.30)
NA="#c0392b"; RG="#e0a021"; ST="#238b45"

axA=fig.add_subplot(gs[0,0])
axA.plot(pol_cov["naive"],color=NA,lw=2,label=f"naive (regressions {pol_reg['naive']})")
axA.plot(pol_cov["regress"],color=RG,lw=2,label=f"regression gate ({pol_reg['regress']})")
axA.plot(pol_cov["stitch"],color=ST,lw=2.4,label=f"stitch ({pol_reg['stitch']})")
axA.set_xlabel("upgrade candidate #"); axA.set_ylabel("capabilities the memory can do")
axA.set_title("(A) 'Does what the old did, plus more':\nnaive replace silently LOSES skills",fontsize=10.2)
axA.legend(fontsize=8.4,framealpha=0.9,title="policy (capabilities lost)",title_fontsize=8)

axB=fig.add_subplot(gs[0,1])
names=["old","candidate\n(gappy)","STITCH"]; vals=[covB["old"],covB["candidate"],covB["stitch"]]
axB.bar([0,1,2],vals,0.6,color=["#888",NA,ST])
for i,v in enumerate(vals): axB.text(i,v+0.15,str(v),ha="center",fontsize=9.5)
axB.set_xticks([0,1,2]); axB.set_xticklabels(names,fontsize=9); axB.set_ylabel("capabilities covered")
axB.set_ylim(0,C)
axB.set_title("(B) Stitch the gaps: a higher-mean but gappy\ncandidate + old = cover the UNION",fontsize=10.2)

axC=fig.add_subplot(gs[0,2])
x=np.arange(L); w=0.38
axC.bar(x-w/2,trust_single,w,color="#b0752a",label="ball of ONE layer")
axC.bar(x+w/2,trust_diverse,w,color=ST,label="ball folded from diverse trusted layers")
axC.set_xticks(x); axC.set_xticklabels([f"lens {l}" for l in range(L)],fontsize=8.6)
axC.set_ylabel("lens trust in the ball"); axC.set_ylim(0,1.08)
axC.set_title("(C) Trust = what the ball is MADE OF\n(a lens trusts the layers it's folded from)",fontsize=10.2)
axC.legend(fontsize=7.8,framealpha=0.9,loc="upper center")
# annotate the branch-switch
axC.annotate(f"lens0 switches branch:\ntrust {trust0_A:.2f}→{trust0_B:.2f}",
             xy=(0+w/2,trust_diverse[0]),xytext=(0.2,0.35),fontsize=7.6,color="#333",
             arrowprops=dict(arrowstyle="->",color="#666",lw=0.9))

fig.suptitle("#43 — the memory upgrade is a TRUST gate: functional regression ('do old + more') + stitch the gaps; the folded ball's trust to a lens IS what it's made of",fontsize=10.4)
fig.savefig("trust_stitch.png",dpi=130,bbox_inches="tight")
print("\n  wrote trust_stitch.png")
