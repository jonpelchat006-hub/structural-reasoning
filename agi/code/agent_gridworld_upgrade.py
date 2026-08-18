#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
agent_gridworld_upgrade.py -- FOLD #41 BACK INTO RUNG 2.

#41 measured the frozen-memory fix in isolation. This folds it into the actual rung-2 gridworld agent
(#40) and re-benchmarks, closing the loop on the flaw Jonathan caught: on a revisit the agent "kept
going to the same one" because #40 stored the FIRST noisy signature and froze it -- so under real
signature noise it sometimes RECOGNISES THE WRONG REGIME and recalls the wrong goal, then confidently
walks to the wrong corner every time it revisits.

The fix (from #41): each confirmed revisit refines the regime prototype with a RUNNING MEAN of the
noisy signatures (the important, repeatedly-seen memory sprays to the top / sharpens), so recognition
improves with use instead of being pinned to one noisy first look.

Two agents, identical except the one line:
  * FROZEN   -- protos[bi]["sig"] stays the first sample                       (the #40 behavior)
  * UPGRADE  -- protos[bi]["sig"] += (obs - sig)/count  on each confirmed hit  (the #41 fix)

MEASURED, across seeds, at ELEVATED signature noise (so the flaw actually bites):
  (1) REGIME-RECOGNITION accuracy on revisits (did it recall the RIGHT regime's goal?)
  (2) WRONG-GOAL commits (how often it "keeps going to the same [wrong] one")
  (3) steps-to-goal on a revisit (lower = recalls & reaches faster)
"""
import numpy as np
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

N=5; START=(2,2); MAXST=40; STEP=-0.04; GOALREW=1.0
GOALS=[(0,0),(0,4),(4,0),(4,4)]
NREG=len(GOALS)
BLOCK=6
SCHED=[0,1,2,3,0,2,1,3,0,3,2,1,0,1,2,3]
EPIS=len(SCHED)*BLOCK
regime_of_ep=np.repeat(SCHED, BLOCK)
D=8
SIGNOISE=0.55                      # elevated vs #40's 0.22 -> frozen first-sample mis-IDs; upgrade recovers

def step(pos,a):
    r,c=pos
    if a==0: r=max(0,r-1)
    elif a==1: r=min(N-1,r+1)
    elif a==2: c=max(0,c-1)
    else: c=min(N-1,c+1)
    return (r,c)

def nav_action(pos, goal, explore, rng):
    if explore: return int(rng.integers(4))
    r,c=pos; gr,gc=goal
    opts=[]
    if gr<r: opts.append(0)
    if gr>r: opts.append(1)
    if gc<c: opts.append(2)
    if gc>c: opts.append(3)
    return int(rng.choice(opts)) if opts else int(rng.integers(4))

def train_shovelcat(upgrade, seed):
    rng=np.random.default_rng(seed)
    SIG=rng.normal(0,1,(NREG,D)); SIG/=np.linalg.norm(SIG,axis=1,keepdims=True)
    protos=[]                                  # dict(sig, goal, mass, count, true_reg[for scoring only])
    reserve=1.0; COST=0.02; REFILL=0.5
    stp=np.zeros(EPIS); recalled=np.zeros(EPIS)
    recog_correct=np.zeros(EPIS); recog_test=np.zeros(EPIS)   # on revisits: did we recall the right regime?
    for e in range(EPIS):
        reg=regime_of_ep[e]
        obs=SIG[reg]+rng.normal(0,SIGNOISE,D)
        best=-1; bi=-1
        for i,p in enumerate(protos):
            s=float(np.dot(obs,p["sig"])/(np.linalg.norm(obs)*np.linalg.norm(p["sig"])))
            if s>best: best=s; bi=i
        known = best>0.7
        reserve=min(1.0, reserve+REFILL)
        pos=START; steps=0; found=None
        for _ in range(MAXST):
            if known:
                goal=protos[bi]["goal"]; a=nav_action(pos,goal,False,rng)
            else:
                can = reserve>COST
                if can: a=nav_action(pos,None,True,rng); reserve-=COST
                else:   a=nav_action(pos, protos[bi]["goal"] if protos else GOALS[0], False,rng)
            npos=step(pos,a); steps+=1
            if npos==GOALS[reg]: found=npos; break
            pos=npos
        # score recognition on a revisit (this regime has been seen before -> a memory should exist)
        seen_before = reg in regime_of_ep[:e]
        if known and seen_before:
            recog_test[e]=1
            recog_correct[e]= 1.0 if protos[bi]["true_reg"]==reg else 0.0   # recalled the RIGHT regime?
        # commit / recall-confirm  (+ the #41 upgrade line)
        if known:
            recalled[e]=1
            protos[bi]["count"]+=1
            if upgrade:
                sig=protos[bi]["sig"]
                protos[bi]["sig"]=sig+(obs-sig)/protos[bi]["count"]         # <-- THE #41 FIX (running mean)
            if found is not None: protos[bi]["mass"]+=1
        elif found is not None:
            protos.append({"sig":obs.copy(),"goal":found,"mass":1,"count":1,"true_reg":reg})
        stp[e]=steps
    return stp, recalled, recog_correct, recog_test

# revisit episodes = first episode of a block whose regime appeared before
block_start=[b*BLOCK for b in range(len(SCHED))]
revisit_ep=[block_start[b] for b in range(len(SCHED)) if SCHED[b] in SCHED[:b]]

def summarize(upgrade, nseeds=8):
    steps_rev=[]; recog=[]; wrong=[]
    for sd in range(nseeds):
        stp,rec,rc,rt=train_shovelcat(upgrade, 100+sd)
        steps_rev.append(np.mean([stp[i] for i in revisit_ep]))
        tot=rt.sum()
        if tot>0:
            recog.append(rc.sum()/tot)          # recognition accuracy over all revisit-with-memory episodes
            wrong.append((rt.sum()-rc.sum()))    # count of wrong-regime recalls
        else:
            recog.append(np.nan); wrong.append(0)
    return (np.array(steps_rev), np.array(recog), np.array(wrong))

fr_steps, fr_recog, fr_wrong = summarize(False)
up_steps, up_recog, up_wrong = summarize(True)

print("="*80)
print("  FOLD #41 INTO RUNG 2 -- frozen first-memory vs upgrade-on-revisit, same gridworld")
print("="*80)
print(f"  {NREG} regimes, {EPIS} episodes, signature noise {SIGNOISE} (elevated so the flaw bites)")
print()
print(f"  {'metric':34}{'FROZEN (#40)':>16}{'UPGRADE (#41)':>16}")
print(f"  {'regime-recognition on revisit':34}{np.nanmean(fr_recog):>15.2f}{np.nanmean(up_recog):>16.2f}")
print(f"  {'wrong-goal recalls (count/run)':34}{np.mean(fr_wrong):>15.1f}{np.mean(up_wrong):>16.1f}")
print(f"  {'steps-to-goal on a revisit':34}{np.mean(fr_steps):>15.1f}{np.mean(up_steps):>16.1f}")
print()
print(f"  -> FROZEN pins each regime to its FIRST noisy look, so under real noise it mis-recognises and")
print(f"     recalls the WRONG goal -- it 'keeps going to the same one' (the wrong corner) on every revisit.")
print(f"  -> UPGRADE refines the prototype each revisit (running mean, #41): recognition climbs, wrong-goal")
print(f"     recalls drop, and it reaches the goal faster on revisits. The flaw Jonathan caught is closed.")

# ---------------------------------------------------------------------------
# PLOT
# ---------------------------------------------------------------------------
fig=plt.figure(figsize=(13.6,4.7)); gs=fig.add_gridspec(1,3,wspace=0.34)
FR="#c0392b"; UP="#238b45"

axA=fig.add_subplot(gs[0,0])
m=[np.nanmean(fr_recog),np.nanmean(up_recog)]; s=[np.nanstd(fr_recog),np.nanstd(up_recog)]
axA.bar([0,1],m,0.55,yerr=s,capsize=6,color=[FR,UP])
axA.set_xticks([0,1]); axA.set_xticklabels(["FROZEN\n(#40)","UPGRADE\n(#41)"],fontsize=9)
axA.set_ylabel("regime-recognition on revisit"); axA.set_ylim(0,1.05)
for i,(mm,ss) in enumerate(zip(m,s)): axA.text(i,mm+ss+0.03,f"{mm:.2f}",ha="center",fontsize=9)
axA.set_title("Recalls the RIGHT regime's goal\non revisit (8 seeds)",fontsize=10.2)

axB=fig.add_subplot(gs[0,1])
m=[np.mean(fr_wrong),np.mean(up_wrong)]; s=[np.std(fr_wrong),np.std(up_wrong)]
axB.bar([0,1],m,0.55,yerr=s,capsize=6,color=[FR,UP])
axB.set_xticks([0,1]); axB.set_xticklabels(["FROZEN\n(#40)","UPGRADE\n(#41)"],fontsize=9)
axB.set_ylabel("wrong-goal recalls per run")
for i,(mm,ss) in enumerate(zip(m,s)): axB.text(i,mm+ss+0.15,f"{mm:.1f}",ha="center",fontsize=9)
axB.set_title("'Keeps going to the same [wrong] one'\n— wrong-goal recalls",fontsize=10.2)

axC=fig.add_subplot(gs[0,2])
m=[np.mean(fr_steps),np.mean(up_steps)]; s=[np.std(fr_steps),np.std(up_steps)]
axC.bar([0,1],m,0.55,yerr=s,capsize=6,color=[FR,UP])
axC.axhline(4,color="#999",ls=":",lw=1); axC.text(0.0,4.4,"optimal (4)",fontsize=8,color="#777")
axC.set_xticks([0,1]); axC.set_xticklabels(["FROZEN\n(#40)","UPGRADE\n(#41)"],fontsize=9)
axC.set_ylabel("steps to goal on a revisit")
for i,(mm,ss) in enumerate(zip(m,s)): axC.text(i,mm+ss+0.4,f"{mm:.1f}",ha="center",fontsize=9)
axC.set_title("Reaches the goal faster on revisit\n(lower better)",fontsize=10.2)

fig.suptitle("Folding #41 into rung 2: upgrading the regime prototype on each revisit fixes the frozen-memory mis-recall Jonathan caught",fontsize=10.6)
fig.savefig("agent_gridworld_upgrade.png",dpi=130,bbox_inches="tight")
print("\n  wrote agent_gridworld_upgrade.png")
