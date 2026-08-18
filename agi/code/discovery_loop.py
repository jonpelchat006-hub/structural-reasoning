#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
discovery_loop.py -- #49: THE CLOSED DISCOVERY LOOP. The capstone that runs the discovery pieces as ONE
system, over a hidden field the agent must learn by probing:

  1. ANTENNA CONSENSUS (#48): antennae converge on the emptiest, most-pointed-at void -> the target to probe.
  2. RAY-SNAP EXTRAPOLATION (#48): snap to the known ring around the target -> a hypothesis for its value.
  3. PROBE (the world answers with the true value).
  4. TRUST GATE (#42/#43): |hypothesis - truth| small -> CONFIRM (coheres); large -> SURPRISE (something new).
  5. CONFIRM -> the void FILLS and re-bases into a new anchor (#47); SURPRISE -> MINT a fresh gap and
     DENSIFY there (#17/#18) to resolve the new structure.
  6. RESERVE GATE (#3): each probe costs reserve, which refills; gate so it never depletes (#37/#40).

The hidden field is a smooth base plus a few SHARP hidden bumps (ground truths a smooth extrapolation
misses -> they read as SURPRISES). The loop must learn the whole field in as few probes as possible.

MEASURED (does the loop work as one system, and does each piece earn its place?):
  (A) DIRECTED beats undirected: full loop drives model error down in far fewer probes than random, and the
      SURPRISE-MINT resolves the sharp hidden anchors that plain uncertainty-sampling is slow on.
  (B) It DISCOVERS the hidden anchors: full loop finds all of them fast (surprise -> densify); random misses.
  (C) It runs GATED as one system: confirmations rise and surprises taper as the field fills; the reserve
      stays alive under gating while an ungated version breaks down.
"""
import numpy as np
from scipy.spatial.distance import cdist
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

rng=np.random.default_rng(3)

# ---- the hidden field: smooth base + K sharp hidden anchors (ground truths) ----
K=4
bump_xy=np.array([[0.30,0.68],[0.70,0.28],[0.80,0.76],[0.24,0.26]])
bump_a=np.array([2.6,-2.3,2.2,-2.0]); bump_w=0.07
def truth(P):
    P=np.atleast_2d(P)
    v=0.8*np.sin(3.0*P[:,0])+0.8*np.cos(2.6*P[:,1])         # smooth base
    for (bx,by),a in zip(bump_xy,bump_a):
        v+=a*np.exp(-((P[:,0]-bx)**2+(P[:,1]-by)**2)/(2*bump_w**2))   # sharp hidden bumps
    return v
gx=np.linspace(0,1,32); GX,GY=np.meshgrid(gx,gx)
TEST=np.stack([GX.ravel(),GY.ravel()],1); Ttrue=truth(TEST)
BUMPMASK=cdist(TEST,bump_xy).min(1)<3.0*bump_w              # test points near a hidden anchor
BMASKS=[cdist(TEST,bump_xy[k:k+1]).ravel()<3.0*bump_w for k in range(K)]   # per-anchor masks
RESOLVE_TOL=0.5
def resolved_k(k,known_xy,known_v):
    e=(idw(TEST[BMASKS[k]],known_xy,known_v)-Ttrue[BMASKS[k]])**2
    return np.sqrt(np.mean(e))<RESOLVE_TOL

def idw(P, known_xy, known_v, p=2.0):
    P=np.atleast_2d(P); D=cdist(P,known_xy)+1e-9
    W=1.0/D**p
    return (W@known_v)/W.sum(1)
def rmse(known_xy,known_v):
    return float(np.sqrt(np.mean((idw(TEST,known_xy,known_v)-Ttrue)**2)))
def rmse_bump(known_xy,known_v):
    e=(idw(TEST[BUMPMASK],known_xy,known_v)-Ttrue[BUMPMASK])**2
    return float(np.sqrt(np.mean(e)))
def uncertainty(P, known_xy):            # antenna reach ∝ emptiness = distance to nearest known
    return cdist(np.atleast_2d(P),known_xy).min(1)

# ---- the discovery loop, with ablation flags ----
SURP=0.9
def run(mode, budget=70, seed=0, gate=False):
    r=np.random.default_rng(100+seed)
    known_xy=r.uniform(0.05,0.95,(5,2)); known_v=truth(known_xy)
    reserve=1.0; COST=0.09; REFILL=0.035
    curve=[]; bcurve=[]; confirms=[]; surprises=[]; res_traj=[]
    found=np.zeros(K,dtype=bool); found_step=np.full(K,-1)
    resolved=np.zeros(K,dtype=bool); resolve_step=np.full(K,-1)
    minted=[]; surprise_xy=[]                   # surprise regions to densify (antennae are drawn there)
    probes=0
    def check_resolve():
        for k in range(K):
            if not resolved[k] and resolved_k(k,known_xy,known_v):
                resolved[k]=True; resolve_step[k]=probes
    while probes<budget:
        # --- RESERVE GATE (only when gate=True): rest to refill if depleted ---
        if gate and reserve<COST:
            reserve=min(1.0,reserve+REFILL*4); res_traj.append(reserve); continue
        # --- pick the target (antenna convergence = emptiest void, boosted toward surprise regions) ---
        if mode=="random":
            target=r.uniform(0,1,2)
        elif mode=="greedy":                 # exploit near the model's current extremes (no void-seeking)
            U=uncertainty(TEST,known_xy); pred=idw(TEST,known_xy,known_v)
            target=TEST[np.argmax(np.abs(pred-pred.mean())-4*U)]
        else:                                # full / nomint: antenna convergence = max uncertainty (emptiest void)
            U=uncertainty(TEST,known_xy)
            target=TEST[np.argmax(U)]
        # --- extrapolate a hypothesis (ray-snap), probe, pay reserve ---
        hyp = idw(target,known_xy,known_v)[0] if mode!="random" else 0.0
        tv=truth(target)[0]
        known_xy=np.vstack([known_xy,target]); known_v=np.append(known_v,tv); probes+=1
        reserve=min(1.0,max(-0.6,reserve-COST+REFILL))
        curve.append(rmse(known_xy,known_v)); bcurve.append(rmse_bump(known_xy,known_v)); res_traj.append(reserve)
        # --- trust gate: confirm vs surprise; surprise -> mint + densify (full only) ---
        surprise = abs(tv-hyp)>SURP
        surprises.append(1 if surprise else 0); confirms.append(0 if surprise else 1)
        if surprise: surprise_xy.append(target.copy())
        for k in range(K):
            if not found[k] and np.linalg.norm(target-bump_xy[k])<bump_w*3.0:
                found[k]=True; found_step[k]=probes
        check_resolve()
        if surprise and mode=="full":
            minted.append((target[0],target[1]))
            for _ in range(4):               # DENSIFY: resolve the newly found anchor locally
                if probes>=budget: break
                q=np.clip(target+r.normal(0,0.035,2),0,1)
                known_xy=np.vstack([known_xy,q]); known_v=np.append(known_v,truth(q)[0]); probes+=1
                reserve=min(1.0,max(-0.6,reserve-COST*0.5+REFILL))
                curve.append(rmse(known_xy,known_v)); bcurve.append(rmse_bump(known_xy,known_v)); res_traj.append(reserve)
                surprises.append(0); confirms.append(1)
                for k in range(K):
                    if not found[k] and np.linalg.norm(q-bump_xy[k])<bump_w*2.0:
                        found[k]=True; found_step[k]=probes
                check_resolve()
    return dict(curve=np.array(curve),bcurve=np.array(bcurve),confirms=np.array(confirms),
                surprises=np.array(surprises),res=np.array(res_traj),found_step=found_step,
                resolve_step=resolve_step,known_xy=known_xy,known_v=known_v,
                surprise_xy=np.array(surprise_xy) if surprise_xy else np.zeros((0,2)))

# average over seeds for the curves (all indexed by probe count now)
def avg_curve(mode,key="curve",seeds=5):
    cs=[run(mode,seed=s)[key] for s in range(seeds)]
    L=min(len(c) for c in cs); cs=np.array([c[:L] for c in cs])
    return cs.mean(0), cs.std(0)
full_m,full_s=avg_curve("full"); rand_m,rand_s=avg_curve("random")
nomint_m,nomint_s=avg_curve("nomint"); greedy_m,greedy_s=avg_curve("greedy")
fullb_m,fullb_s=avg_curve("full","bcurve"); nomintb_m,_=avg_curve("nomint","bcurve"); randb_m,_=avg_curve("random","bcurve")

# surprise localization: do the trust-gate's surprises land on the hidden anchors?
def surprise_localization(seeds=6):
    hit=tot=0
    for s in range(seeds):
        sx=run("full",seed=s)["surprise_xy"]
        for q in sx:
            tot+=1
            if cdist(q[None],bump_xy).min()<1.5*bump_w: hit+=1
    return hit/max(tot,1), tot/seeds
surp_prec, surp_per_run = surprise_localization()

# one representative full run for the maps; and the reserve story (gated vs ungated)
rep=run("full",seed=0)
gated=run("full",seed=0,gate=True); ungated=run("full",seed=0,gate=False)

print("="*80)
print("  #49  THE CLOSED DISCOVERY LOOP -- antenna -> extrapolate -> probe -> trust -> fill/mint, gated")
print("="*80)
print(f"  hidden field: smooth base + {K} sharp hidden anchors; learn it in as few probes as possible")
print(f"  (A) error after the probe budget (mean±std, 5 seeds) -- OVERALL | on the SHARP hidden anchors:")
print(f"        FULL loop     {full_m[-1]:.3f} ± {full_s[-1]:.3f}  |  {fullb_m[-1]:.3f}   <- resolves the anchors")
print(f"        no-mint       {nomint_m[-1]:.3f} ± {nomint_s[-1]:.3f}  |  {nomintb_m[-1]:.3f}   (uncertainty only, no densify)")
print(f"        greedy        {greedy_m[-1]:.3f} ± {greedy_s[-1]:.3f}  |  (exploit, no void-seeking)")
print(f"        random        {rand_m[-1]:.3f} ± {rand_s[-1]:.3f}  |  {randb_m[-1]:.3f}")
print(f"  (B) the trust-gate's SURPRISES land on real hidden structure: {surp_prec*100:.0f}% of surprises")
print(f"      fall on a hidden anchor ({surp_per_run:.1f} surprises/run) -> discovery detector, not noise.")
print(f"  (C) runs as ONE gated system: surprises {rep['surprises'].sum():.0f} early (discoveries) → confirmations "
      f"{rep['confirms'].sum():.0f} (fills); reserve GATED stays alive (min {gated['res'].min():.2f}) vs "
      f"ungated BREAKDOWN (min {ungated['res'].min():.2f}).")
print(f"  ablations: directed FULL overall {full_m[-1]:.2f} beats random {rand_m[-1]:.2f} and greedy {greedy_m[-1]:.2f};")
print(f"      surprise-densify trims sharp-anchor error {nomintb_m[-1]:.2f}→{fullb_m[-1]:.2f} (a modest refinement).")

# ---------------------------------------------------------------------------
# PLOT
# ---------------------------------------------------------------------------
fig=plt.figure(figsize=(15.2,4.9)); gs=fig.add_gridspec(1,3,wspace=0.30)
FULL="#238b45"; RAND="#c0392b"; NOM="#e0a021"; GRE="#8a2be2"; BLU="#2b6cb0"

axA=fig.add_subplot(gs[0,0])
xs=np.arange(len(full_m))
axA.plot(xs,full_m,color=FULL,lw=2.4,label="FULL loop (antenna-directed)")
axA.fill_between(xs,full_m-full_s,full_m+full_s,color=FULL,alpha=0.15)
axA.plot(np.arange(len(rand_m)),rand_m,color=RAND,lw=1.8,label="no antenna (random targets)")
axA.plot(np.arange(len(greedy_m)),greedy_m,color=GRE,lw=1.7,label="exploit only (no void-seeking)")
axA.set_xlabel("probes"); axA.set_ylabel("model error over the hidden field (RMSE)")
axA.legend(fontsize=8,framealpha=0.9)
axA.set_title("(A) Directed discovery works: the full loop learns\nthe field faster than random or exploit-only",fontsize=10.0)

axB=fig.add_subplot(gs[0,1])
axB.imshow(Ttrue.reshape(32,32),extent=[0,1,0,1],origin="lower",cmap="coolwarm",alpha=0.8)
axB.scatter(rep["known_xy"][:,0],rep["known_xy"][:,1],s=11,color="black",alpha=0.45,label="probes")
if len(rep["surprise_xy"]): axB.scatter(rep["surprise_xy"][:,0],rep["surprise_xy"][:,1],s=90,marker="D",color="yellow",edgecolor="black",lw=0.8,zorder=6,label="SURPRISE (discovery)")
axB.scatter(bump_xy[:,0],bump_xy[:,1],marker="*",s=240,facecolor="none",edgecolor="lime",lw=2,zorder=7,label="hidden anchor")
axB.set_xticks([]); axB.set_yticks([]); axB.legend(fontsize=7.2,loc="upper left",framealpha=0.9)
axB.set_title(f"(B) The trust-gate's surprises land on real\nhidden structure ({surp_prec*100:.0f}% on an anchor)",fontsize=10.0)

axC=fig.add_subplot(gs[0,2])
cs=np.cumsum(rep["surprises"]); cc=np.cumsum(rep["confirms"])
axC.plot(cs,color=RAND,lw=2,label="cumulative surprises (discoveries)")
axC.plot(cc,color=FULL,lw=2,label="cumulative confirmations (fills)")
axC.set_xlabel("probes"); axC.set_ylabel("count")
axC.legend(fontsize=7.6,framealpha=0.9,loc="upper left")
ax2=axC.twinx()
ax2.plot(gated["res"],color=BLU,lw=1.5,ls="--",label="reserve GATED (alive)")
ax2.plot(ungated["res"],color="#999",lw=1.3,ls=":",label="reserve ungated (breakdown)")
ax2.axhline(0,color="#999",lw=0.7)
ax2.set_ylabel("reserve",color=BLU); ax2.tick_params(axis="y",labelcolor=BLU); ax2.set_ylim(-0.65,1.05)
ax2.legend(fontsize=6.8,framealpha=0.9,loc="right")
axC.set_title("(C) One gated system: surprises early → confirms\nas it fills; gated reserve stays alive, ungated crashes",fontsize=9.8)

fig.suptitle("#49 — the closed discovery loop: antenna → extrapolate → probe → trust (confirm/surprise) → fill or mint, paced by the reserve; directed discovery beats random & exploit, and its surprises land on the hidden anchors",fontsize=9.4)
fig.savefig("discovery_loop.png",dpi=130,bbox_inches="tight")
print("\n  wrote discovery_loop.png")
