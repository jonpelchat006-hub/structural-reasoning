#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
agent_grow.py -- #51: THE THIRD INTEGRATION. One agent that both REMEMBERS (the #37 memory loop: recall a
solved regime cheaply on sight) and DISCOVERS (the #49/#50 loop: solve a never-seen regime by extrapolating
from neighbours, then FOLD it in as a new anchor), dropped into an OPEN stream that keeps introducing NEW
regimes and revisiting OLD ones. It must GROW -- acquire new skills and retain them -- the "learn-from-what-
you-give-it" engine of FOLDING_WHAT_ITS_FOR.

The world: a stream of episodes; each has a hidden regime with a noisy signature and a hidden solution that
is a SMOOTH function of the signature (so a new regime's solution is partly predictable from nearby solved
ones -- #48 ray-snap / #45 invariant). New regimes are introduced over time; old ones recur.

The agent, per episode:
  * RECOGNISE the regime from its noisy signature (#37); if KNOWN -> RECALL its solution (cheap, #21/#27).
  * if UNKNOWN -> DISCOVER: extrapolate a hypothesis from stored neighbours (#48); if it coheres -> CONFIRM
    (cheap); else EXPLORE to find it (costly, #49/#50 bulb); on success FOLD IT IN as a new anchor (#47).
  * RESERVE gates exploration so it never depletes (#3); recall is cheap, explore is dear.

Ablations, each cutting one half (like #37):
  * MEMORY-ONLY (no discovery): can recall a pre-taught set but CANNOT acquire novel regimes -> plateaus.
  * DISCOVERY-ONLY (no memory store): must RE-EXPLORE every episode (never recalls) -> reserve-starved.
  * NO-GATE: explores freely -> reserve breakdown -> denatured, fails.

MEASURED: the FULL agent's competence climbs highest on the open stream at the LOWEST discovery cost (explore
each new regime ONCE, recall the rest), while each ablation fails where its half was cut.
"""
import numpy as np
from scipy.spatial.distance import cdist
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

D=8; NREG=14; EPIS=170
rng0=np.random.default_rng(1)
SIG=rng0.normal(0,1,(NREG,D)); SIG/=np.linalg.norm(SIG,axis=1,keepdims=True)
Wsol=rng0.normal(0,1,(D,3))
SOL=np.tanh(SIG@Wsol)                       # smooth: similar signatures -> similar solutions

# ---- the open-world schedule: introduce new regimes over time, revisit old ones ----
def make_schedule(seed):
    r=np.random.default_rng(200+seed)
    introduced=[]; sched=[]; nxt=0
    for e in range(EPIS):
        p_intro=0.4*(1-e/EPIS)+0.05
        if nxt<NREG and (not introduced or r.random()<p_intro):
            introduced.append(nxt); sched.append(nxt); nxt+=1          # a NOVEL regime
        else:
            sched.append(introduced[r.integers(len(introduced))])      # revisit an OLD one
    return np.array(sched)

THRESH=0.80; NOISE=0.17; TOL=0.28; TOL_CONF=0.30
REFILL=0.11; EXTRAP=0.04; EXPLORE=0.33; BREAKDOWN=-0.4

def run(mode, seed=0):
    r=np.random.default_rng(500+seed); sched=make_schedule(seed)
    anchors_sig=[]; anchors_sol=[]                   # the memory store
    if mode=="memory_only":                          # pre-taught a starter set (regimes 0,1,2), no discovery
        for k in [0,1,2]: anchors_sig.append(SIG[k]+r.normal(0,NOISE,D)); anchors_sol.append(SOL[k].copy())
    reserve=1.0
    succ=np.zeros(EPIS); res_traj=np.zeros(EPIS); nanch=np.zeros(EPIS); explored=np.zeros(EPIS)
    for e in range(EPIS):
        rg=sched[e]; obs=SIG[rg]+r.normal(0,NOISE,D); true=SOL[rg]
        reserve=min(1.0,reserve+REFILL)              # baseline refill
        has_mem = mode in ("full","memory_only","no_gate")
        # --- recognise (memory) ---
        known=False; bi=-1
        if has_mem and anchors_sig:
            sims=[float(np.dot(obs,a)/(np.linalg.norm(obs)*np.linalg.norm(a))) for a in anchors_sig]
            bi=int(np.argmax(sims)); known=sims[bi]>THRESH
        if known:                                    # RECALL -- cheap
            produced=anchors_sol[bi]
            succ[e]=1.0 if np.linalg.norm(produced-true)<TOL else 0.0
        elif mode=="memory_only":                    # no discovery: cannot solve a novel regime
            succ[e]=0.0
        else:                                        # DISCOVER
            # extrapolate a hypothesis from stored neighbours (ray-snap); empty store -> no basis
            if anchors_sig:
                sig_arr=np.array(anchors_sig); w=np.exp(6*(sig_arr@obs/ (np.linalg.norm(sig_arr,axis=1)*np.linalg.norm(obs))))
                hyp=(w[:,None]*np.array(anchors_sol)).sum(0)/w.sum()
            else:
                hyp=np.zeros(3)
            reserve-=EXTRAP
            if np.linalg.norm(hyp-true)<TOL_CONF:    # CONFIRM -- extrapolation coheres, cheap
                produced=hyp; succ[e]=1.0
            else:                                    # SURPRISE -> must EXPLORE (costly) unless gated broke
                can_explore = (mode=="no_gate") or (reserve>=EXPLORE-1e-9)
                if can_explore:
                    reserve-=EXPLORE; explored[e]=1
                    if mode=="no_gate" and reserve<BREAKDOWN:
                        succ[e]=0.0                  # denatured breakdown -> fail
                    else:
                        produced=true; succ[e]=1.0   # exploration finds it
                else:
                    produced=hyp; succ[e]=1.0 if np.linalg.norm(hyp-true)<TOL_CONF else 0.0   # rest: cheap guess only
            # FOLD IN a new anchor on success (grow) -- only if this mode keeps a store
            if succ[e]>0 and mode in ("full","no_gate"):
                anchors_sig.append(obs.copy()); anchors_sol.append(true.copy())
        res_traj[e]=reserve; nanch[e]=len(anchors_sig)
    return dict(succ=succ,res=res_traj,nanch=nanch,explored=explored,sched=sched)

def roll(x,k=15):
    c=np.convolve(x,np.ones(k)/k,mode="same"); return c
def avg(mode,seeds=6):
    R=[run(mode,s) for s in range(seeds)]
    comp=np.array([roll(x["succ"]) for x in R]).mean(0)
    res=np.array([x["res"] for x in R]).mean(0)
    expl=np.array([np.cumsum(x["explored"]) for x in R]).mean(0)
    nan=np.array([x["nanch"] for x in R]).mean(0)
    final=np.array([x["succ"][-40:].mean() for x in R])
    return comp,res,expl,nan,final
comp_f,res_f,expl_f,nan_f,fin_f=avg("full")
comp_m,res_m,expl_m,nan_m,fin_m=avg("memory_only")
comp_d,res_d,expl_d,nan_d,fin_d=avg("discovery_only")
comp_n,res_n,expl_n,nan_n,fin_n=avg("no_gate")

print("="*80)
print("  #51  THE THIRD INTEGRATION -- one agent that REMEMBERS and DISCOVERS, growing on an open stream")
print("="*80)
print(f"  open stream: {EPIS} episodes, {NREG} regimes introduced over time and revisited")
print(f"  competence over the last 40 episodes (mean±std, 6 seeds):")
print(f"        FULL (memory+discovery+gate) : {fin_f.mean():.2f} ± {fin_f.std():.2f}")
print(f"        memory-only  (no discovery)  : {fin_m.mean():.2f} ± {fin_m.std():.2f}   (can't acquire novel -> plateaus)")
print(f"        discovery-only (no memory)   : {fin_d.mean():.2f} ± {fin_d.std():.2f}   (re-explores forever -> reserve-starved)")
print(f"        no-gate (memory+discovery)   : {fin_n.mean():.2f} ± {fin_n.std():.2f}   (reserve breakdown)")
print(f"  discovery COST (cumulative expensive explores): FULL {expl_f[-1]:.0f} (≈once per regime) vs "
      f"discovery-only {expl_d[-1]:.0f} (keeps paying)")
print(f"  reserve min: FULL {res_f.min():.2f} (alive) vs no-gate {res_n.min():.2f} (breakdown); "
      f"store grew to {nan_f[-1]:.0f} anchors (frontier).")

# ---------------------------------------------------------------------------
fig=plt.figure(figsize=(15.2,4.9)); gs=fig.add_gridspec(1,3,wspace=0.30)
F="#238b45"; M="#e0a021"; Dd="#2b6cb0"; N="#c0392b"

axA=fig.add_subplot(gs[0,0])
xs=np.arange(EPIS)
axA.plot(xs,comp_f,color=F,lw=2.4,label="FULL (remember + discover)")
axA.plot(xs,comp_m,color=M,lw=1.8,label="memory-only (can't discover)")
axA.plot(xs,comp_d,color=Dd,lw=1.8,label="discovery-only (can't recall)")
axA.plot(xs,comp_n,color=N,lw=1.6,ls="--",label="no-gate (breakdown)")
axA.set_xlabel("episode (open stream)"); axA.set_ylabel("competence (rolling success rate)"); axA.set_ylim(0,1.05)
axA.legend(fontsize=7.6,framealpha=0.9,loc="lower right")
axA.set_title("(A) The fused agent grows highest; each ablation\nfails where its half was cut",fontsize=10.0)

axB=fig.add_subplot(gs[0,1])
axB.plot(xs,expl_f,color=F,lw=2.2,label="FULL — explore each regime ~once")
axB.plot(xs,expl_d,color=Dd,lw=2.0,label="discovery-only — re-pays forever")
axB.set_xlabel("episode"); axB.set_ylabel("cumulative expensive explorations")
axB.legend(fontsize=8,framealpha=0.9,loc="upper left")
axB.set_title("(B) Memory amortizes discovery: pay to learn a\nregime ONCE, then recall it for free",fontsize=10.0)

axC=fig.add_subplot(gs[0,2])
axC.plot(xs,res_f,color=F,lw=2.2,label="FULL reserve (alive)")
axC.plot(xs,res_d,color=Dd,lw=1.6,label="discovery-only (starved)")
axC.plot(xs,res_n,color=N,lw=1.6,ls="--",label="no-gate (breakdown)")
axC.axhline(0,color="#999",lw=0.7); axC.axhline(BREAKDOWN,color=N,ls=":",lw=0.8)
axC.set_xlabel("episode"); axC.set_ylabel("reserve",color="#333"); axC.set_ylim(-0.7,1.05)
axC.legend(fontsize=7.4,framealpha=0.9,loc="lower left")
ax2=axC.twinx(); ax2.plot(xs,nan_f,color="#8a2be2",lw=1.4,ls="-.",label="FULL store size (frontier)")
ax2.set_ylabel("anchors stored",color="#8a2be2"); ax2.tick_params(axis="y",labelcolor="#8a2be2")
axC.set_title("(C) Gated reserve stays alive as the store GROWS;\nungated/starved break down",fontsize=10.0)

fig.suptitle("#51 — the third integration: one agent that remembers AND discovers, growing on an open stream — explore each new regime once, recall the rest, gated so it never depletes",fontsize=9.6)
fig.savefig("agent_grow.png",dpi=130,bbox_inches="tight")
print("\n  wrote agent_grow.png")
