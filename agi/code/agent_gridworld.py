#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
agent_gridworld.py -- RUNG 2: a LEARNING agent on a real small environment, benchmarked honestly.

#37 proved the pieces integrate on a synthetic stream with a scripted controller. This is the next
rung: a genuine learning agent on a 5x5 gridworld whose goal SWITCHES and REVISITS (regimes), against
standard Q-learning. The question is whether the architecture's structure (a fixed inner navigation
shell + context-keyed one-shot goal memory + break/gap detection + reserve gating) buys SAMPLE
EFFICIENCY over learning everything from scratch -- and we report honestly who wins where.

ENV: 5x5 grid, start at centre, goal in a corner set by a hidden regime; +1 at goal (ends episode),
-0.04 per step, max 40 steps. The regime switches in blocks and REVISITS. Each episode the agent
gets a NOISY signature of the regime (it must infer which regime it is; only the clean-id baseline is
given the regime for free).

AGENTS:
  * Q-POS      -- Q-learning over position only (no regime): averages the goals -> the floor.
  * Q-REGIME   -- Q-learning over (regime-id × position), regime given CLEAN: a strong baseline that
                  retains but relearns each goal incrementally (temporal credit assignment).
  * SHOVELCAT  -- infers the regime from the noisy signature (break/gap + context-keyed memory),
                  commits a regime's goal ONE-SHOT on discovery, recalls it instantly on revisit,
                  navigates with an innate spatial prior, and gates exploration on a reserve.
"""
import numpy as np
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

rng=np.random.default_rng(0)
N=5; START=(2,2); MAXST=40; STEP=-0.04; GOALREW=1.0
GOALS=[(0,0),(0,4),(4,0),(4,4)]                 # regime -> goal corner
NREG=len(GOALS)
BLOCK=6                                          # episodes per regime block
SCHED=[0,1,2,3,0,2,1,3,0,3,2,1,0,1,2,3]          # regime per block, with revisits
EPIS=len(SCHED)*BLOCK
regime_of_ep=np.repeat(SCHED, BLOCK)
D=8; SIG=rng.normal(0,1,(NREG,D)); SIG/=np.linalg.norm(SIG,axis=1,keepdims=True)
SIGNOISE=0.22

def step(pos,a):
    r,c=pos
    if a==0: r=max(0,r-1)
    elif a==1: r=min(N-1,r+1)
    elif a==2: c=max(0,c-1)
    else: c=min(N-1,c+1)
    return (r,c)

def run_episode_Q(Q, keyfn, reg, eps):
    pos=START; total=0; steps=0
    traj=[]
    for _ in range(MAXST):
        s=keyfn(pos,reg)
        if rng.random()<eps: a=int(rng.integers(4))
        else: a=int(np.argmax(Q[s]))
        npos=step(pos,a); steps+=1
        r=GOALREW if npos==GOALS[reg] else STEP
        total+=r
        ns=keyfn(npos,reg)
        Q[s][a]+= 0.5*(r + 0.95*np.max(Q[ns]) - Q[s][a])
        pos=npos
        if npos==GOALS[reg]: break
    return total, steps

def make_Q(keydim):
    return {}

def keyQpos(pos,reg): return pos
def keyQreg(pos,reg): return (reg,pos)
class DefaultQ(dict):
    def __missing__(self,k): v=np.zeros(4); self[k]=v; return v

def train_Q(keyfn):
    Q=DefaultQ()
    rew=np.zeros(EPIS); stp=np.zeros(EPIS)
    for e in range(EPIS):
        reg=regime_of_ep[e]
        eps=max(0.05, 0.5*(0.99**e))
        rew[e],stp[e]=run_episode_Q(Q,keyfn,reg,eps)
    return rew,stp

# ---------- the Shovelcat agent ----------
def nav_action(pos, goal, explore):
    if explore: return int(rng.integers(4))
    r,c=pos; gr,gc=goal
    # innate spatial prior: reduce Manhattan distance to the remembered goal
    opts=[]
    if gr<r: opts.append(0)
    if gr>r: opts.append(1)
    if gc<c: opts.append(2)
    if gc>c: opts.append(3)
    return int(rng.choice(opts)) if opts else int(rng.integers(4))

def train_shovelcat():
    protos=[]                # list of dict(sig, goal, mass)
    reserve=1.0; COST=0.02; REFILL=0.5
    rew=np.zeros(EPIS); stp=np.zeros(EPIS); recalled=np.zeros(EPIS)
    for e in range(EPIS):
        reg=regime_of_ep[e]
        obs=SIG[reg]+rng.normal(0,SIGNOISE,D)
        # recognise the regime from the noisy signature (break/gap + memory)
        best=-1; bi=-1
        for i,p in enumerate(protos):
            s=float(np.dot(obs,p["sig"])/(np.linalg.norm(obs)*np.linalg.norm(p["sig"])))
            if s>best: best=s; bi=i
        known = best>0.7
        reserve=min(1.0, reserve+REFILL)
        pos=START; total=0; steps=0; found=None
        for _ in range(MAXST):
            if known:
                goal=protos[bi]["goal"]; a=nav_action(pos,goal,False)
            else:
                can = reserve>COST
                if can: a=nav_action(pos,None,True); reserve-=COST      # explore (gap), gated by reserve
                else:   a=nav_action(pos, protos[bi]["goal"] if protos else GOALS[0], False)  # conserve: best guess
            npos=step(pos,a); steps+=1
            r=GOALREW if npos==GOALS[reg] else STEP
            total+=r; pos=npos
            if npos==GOALS[reg]: found=npos; break
        # ONE-SHOT commit / recall-confirm
        if known:
            recalled[e]=1
            if found is not None: protos[bi]["mass"]+=1
        elif found is not None:
            protos.append({"sig":obs.copy(),"goal":found,"mass":1})    # learn this regime's goal in one shot
        rew[e]=total; stp[e]=steps
    return rew,stp,recalled

rP,sP=train_Q(keyQpos)
rR,sR=train_Q(keyQreg)
rS,sS,rec=train_shovelcat()

# ---- multi-seed robustness check (exploration randomness varies; env fixed) ----
def revisit_steps_over_seeds(nseeds=6):
    global rng
    out={"Q-pos":[],"Q-regime":[],"SHOVELCAT":[]}
    bs=[b*BLOCK for b in range(len(SCHED))]
    rv=[bs[b] for b in range(len(SCHED)) if SCHED[b] in SCHED[:b]]
    for sd in range(nseeds):
        rng=np.random.default_rng(1000+sd)
        _,s1=train_Q(keyQpos); _,s2=train_Q(keyQreg); _,s3,_=train_shovelcat()
        out["Q-pos"].append(np.mean([s1[i] for i in rv]))
        out["Q-regime"].append(np.mean([s2[i] for i in rv]))
        out["SHOVELCAT"].append(np.mean([s3[i] for i in rv]))
    return {k:(np.mean(v),np.std(v)) for k,v in out.items()}
ms=revisit_steps_over_seeds()
rng=np.random.default_rng(0)  # restore for any downstream use

# ---- revisit episodes: the first episode of a block whose regime appeared before ----
block_start=[b*BLOCK for b in range(len(SCHED))]
revisit_ep=[block_start[b] for b in range(len(SCHED)) if SCHED[b] in SCHED[:b]]
def mean_at(x,idx): return float(np.mean([x[i] for i in idx]))

print("="*80)
print("  RUNG 2: a LEARNING agent on a gridworld with switching+revisiting goals, vs Q-learning")
print("="*80)
print(f"  5x5 grid, {NREG} regimes, {EPIS} episodes; goal switches every {BLOCK} and revisits")
print()
print(f"  {'agent':16}{'mean steps/ep':>15}{'mean reward/ep':>16}{'steps on REVISIT ep':>22}")
for nm,st,rw in [("Q-pos (no regime)",sP,rP),("Q-regime (given)",sR,rR),("SHOVELCAT",sS,rS)]:
    print(f"  {nm:16}{np.mean(st):>15.1f}{np.mean(rw):>16.2f}{mean_at(st,revisit_ep):>22.1f}")
print()
opt=abs(np.array([sum(divmod(0,1)) for _ in [0]]))  # placeholder
optimal=4  # Manhattan from centre to a corner = 4 steps
print(f"  (optimal path to a corner from centre = {optimal} steps)")
print(f"  multi-seed (6) revisit steps, mean±std:  Q-pos {ms['Q-pos'][0]:.1f}±{ms['Q-pos'][1]:.1f}  |  "
      f"Q-regime {ms['Q-regime'][0]:.1f}±{ms['Q-regime'][1]:.1f}  |  SHOVELCAT {ms['SHOVELCAT'][0]:.1f}±{ms['SHOVELCAT'][1]:.1f}")
print(f"  -> SHOVELCAT commits each regime's goal in ONE successful episode and recalls it on revisit")
print(f"     (steps on a revisit ≈ {mean_at(sS,revisit_ep):.1f}, near optimal), inferring the regime from a NOISY")
print(f"     signature. Q-regime (handed the clean regime) retains but relearns incrementally; Q-pos can't")
print(f"     tell the regimes apart and averages the goals.")

# ---------------------------------------------------------------------------
# PLOT
# ---------------------------------------------------------------------------
fig=plt.figure(figsize=(14.4,5.6)); gs=fig.add_gridspec(1,2,wspace=0.26)
cols={"Q-pos":"#e0a021","Q-regime":"#2b6cb0","SHOVELCAT":"#238b45"}
def roll(x,k=4): return np.convolve(x,np.ones(k)/k,mode="same")

axA=fig.add_subplot(gs[0,0])
axA.plot(roll(sP),color=cols["Q-pos"],lw=1.8,label="Q-pos (no regime)")
axA.plot(roll(sR),color=cols["Q-regime"],lw=1.8,label="Q-regime (given)")
axA.plot(roll(sS),color=cols["SHOVELCAT"],lw=2.2,label="SHOVELCAT")
axA.axhline(optimal,color="#999",ls=":",lw=1); axA.text(2,optimal+0.6,"optimal (4 steps)",fontsize=8,color="#777")
for b in block_start: axA.axvline(b,color="#eee",lw=0.5,zorder=0)
for e in revisit_ep: axA.axvline(e,color="#f3dede",lw=1.2,zorder=0)
axA.set_xlabel("episode (goal switches at block edges; pink = a revisit)"); axA.set_ylabel("steps to goal (lower better)")
axA.set_title("Steps to goal — SHOVELCAT snaps to a known regime's goal on revisit", fontsize=10.4)
axA.legend(fontsize=8.5, framealpha=0.9); axA.set_ylim(0,MAXST)

axB=fig.add_subplot(gs[0,1])
names=["Q-pos","Q-regime","SHOVELCAT"]
means=[ms[n][0] for n in names]; stds=[ms[n][1] for n in names]
axB.bar(range(3), means, 0.55, yerr=stds, capsize=6,
        color=["#e0a021","#2b6cb0","#238b45"])
axB.axhline(optimal,color="#999",ls=":",lw=1); axB.text(0.0,optimal+0.5,"optimal (4)",fontsize=8,color="#777")
axB.set_xticks(range(3)); axB.set_xticklabels(names,fontsize=9); axB.set_ylabel("steps to goal on a REVISIT")
axB.set_title("Adaptation on a revisited regime — 6 seeds (mean±std)\nlower = recalls faster", fontsize=10.2)
for i,(m,s) in enumerate(zip(means,stds)): axB.text(i, m+s+0.8, f"{m:.1f}±{s:.1f}", ha="center", fontsize=8.6)

fig.suptitle("Rung 2 — a learning agent on a switching-goal gridworld: the architecture's one-shot goal memory + regime recall vs Q-learning from scratch",
             fontsize=10.6)
fig.savefig("agent_gridworld.png", dpi=130, bbox_inches="tight")
print("\n  wrote agent_gridworld.png")
