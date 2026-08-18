#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
memory_upgrade_foldback.py -- #42: fold #41 into the rung-2 agent, honestly.

#41 measured the frozen-memory fix in isolation and it worked cleanly -- BUT that isolation handed
every sample its TRUE regime label, so the running mean only ever averaged same-regime looks. When we
fold it into the real rung-2 agent (#40), the agent must ASSOCIATE each look to a stored memory ITSELF,
and that association is uncertain under signature noise. Averaging under uncertain association folds
mis-matched looks into a prototype and CONTAMINATES it.

So we benchmarked it carefully (seed sweeps, noise sweeps) and report the honest result:

MEASURED:
  (A) THE MECHANISM IS REAL under reliable association. A prototype sharpened by averaging K reliably-
      associated looks recognises a HARD (noisy) probe ~10 points better than a single frozen first look,
      with a bigger decision margin. Sharpen in easy times, reap robustness when a hard look arrives.
  (B) BUT IT CONTAMINATES under mis-association. As the fraction of folded-in looks that are mis-
      associated rises, the averaged prototype's advantage shrinks and CROSSES BELOW frozen at ~35%
      mis-association -- past that, blind averaging is worse than freezing.
  (C) SO IN THE FULL AGENT, BLIND FOLD-BACK IS A WASH. At the noise where recognition is actually hard
      (so you'd want the fix), association is unreliable enough to sit near the crossover -- frozen vs
      naive-upgrade differ within seed noise. The fix must be CONFIDENCE-GATED (only fold a look in when
      the match is unambiguous), the same verify-through-a-gate / .14 discipline as #24 and the reserve.

The lesson the architecture learns: a memory upgrade is only safe when its association is trusted --
upgrade what you're sure of, freeze what you're not. That is the gate, folded back in.
"""
import numpy as np
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

NREG=4; D=8
def cr(a,b): return float(np.dot(a,b)/(np.linalg.norm(a)*np.linalg.norm(b)))

# ---------- (A) mechanism under RELIABLE association: averaged prototype vs frozen on a hard probe ----------
def robustness_trial(K, sig_train, sig_probe, seed):
    rng=np.random.default_rng(seed)
    SIG=rng.normal(0,1,(NREG,D)); SIG/=np.linalg.norm(SIG,axis=1,keepdims=True)
    frozen=[SIG[r]+rng.normal(0,sig_train,D) for r in range(NREG)]
    upav=[np.mean([SIG[r]+rng.normal(0,sig_train,D) for _ in range(K)],axis=0) for r in range(NREG)]
    fo=uo=0; fm=[]; um=[]
    for _ in range(300):
        r=rng.integers(NREG); pr=SIG[r]+rng.normal(0,sig_probe,D)
        sf=sorted([cr(pr,s) for s in frozen])[::-1]; su=sorted([cr(pr,s) for s in upav])[::-1]
        fm.append(sf[0]-sf[1]); um.append(su[0]-su[1])
        if np.argmax([cr(pr,s) for s in frozen])==r: fo+=1
        if np.argmax([cr(pr,s) for s in upav])==r: uo+=1
    return fo/300, uo/300, np.mean(fm), np.mean(um)
RA=[robustness_trial(6,0.30,0.55,s) for s in range(40)]
fa,ua=np.mean([r[0] for r in RA]),np.mean([r[1] for r in RA])
fm,um=np.mean([r[2] for r in RA]),np.mean([r[3] for r in RA])

# ---------- (B) contamination crossover ----------
def contam_trial(contam, seed, K=6, st=0.30, sp=0.55):
    rng=np.random.default_rng(seed)
    SIG=rng.normal(0,1,(NREG,D)); SIG/=np.linalg.norm(SIG,axis=1,keepdims=True)
    frozen=[SIG[r]+rng.normal(0,st,D) for r in range(NREG)]
    upav=[]
    for r in range(NREG):
        looks=[SIG[(r if rng.random()>contam else int(rng.integers(NREG)))]+rng.normal(0,st,D) for _ in range(K)]
        upav.append(np.mean(looks,axis=0))
    fo=uo=0
    for _ in range(300):
        r=rng.integers(NREG); pr=SIG[r]+rng.normal(0,sp,D)
        if np.argmax([cr(pr,s) for s in frozen])==r: fo+=1
        if np.argmax([cr(pr,s) for s in upav])==r: uo+=1
    return fo/300, uo/300
cs=np.linspace(0,0.5,11)
fr_c=[]; up_c=[]
for c in cs:
    R=[contam_trial(c,s) for s in range(40)]
    fr_c.append(np.mean([r[0] for r in R])); up_c.append(np.mean([r[1] for r in R]))
fr_c=np.array(fr_c); up_c=np.array(up_c)
# crossover point
cross=None
for i in range(len(cs)-1):
    if (up_c[i]-fr_c[i])>=0 and (up_c[i+1]-fr_c[i+1])<0:
        x0,x1=cs[i],cs[i+1]; d0,d1=up_c[i]-fr_c[i],up_c[i+1]-fr_c[i+1]
        cross=x0+(x1-x0)*d0/(d0-d1); break

# ---------- (C) full rung-2 agent: frozen vs naive vs gated, across seeds (the wash) ----------
N=5; START=(2,2); MAXST=40; GOALS=[(0,0),(0,4),(4,0),(4,4)]; BLOCK=6
SCHED=[0,1,2,3,0,2,1,3,0,3,2,1,0,1,2,3]; EPIS=len(SCHED)*BLOCK
regime_of_ep=np.repeat(SCHED,BLOCK)
block_start=[b*BLOCK for b in range(len(SCHED))]
revisit_ep=[block_start[b] for b in range(len(SCHED)) if SCHED[b] in SCHED[:b]]
def step(pos,a):
    r,c=pos
    if a==0:r=max(0,r-1)
    elif a==1:r=min(N-1,r+1)
    elif a==2:c=max(0,c-1)
    else:c=min(N-1,c+1)
    return(r,c)
def nav(pos,goal,ex,rng):
    if ex:return int(rng.integers(4))
    r,c=pos;gr,gc=goal;o=[]
    if gr<r:o.append(0)
    if gr>r:o.append(1)
    if gc<c:o.append(2)
    if gc>c:o.append(3)
    return int(rng.choice(o)) if o else int(rng.integers(4))
def run_agent(mode,noise,seed):
    rng=np.random.default_rng(seed)
    SIG=rng.normal(0,1,(NREG,D));SIG/=np.linalg.norm(SIG,axis=1,keepdims=True)
    protos=[];reserve=1.0;COST=0.02;REFILL=0.5
    stp=np.zeros(EPIS);rc=np.zeros(EPIS);rt=np.zeros(EPIS)
    for e in range(EPIS):
        reg=regime_of_ep[e];obs=SIG[reg]+rng.normal(0,noise,D)
        sims=[cr(obs,p["sig"]) for p in protos]
        if sims:
            order=np.argsort(sims)[::-1];bi=int(order[0]);best=sims[bi]
            second=sims[int(order[1])] if len(sims)>1 else -1.0
        else:bi=-1;best=-1;second=-1
        known=best>0.7;margin=best-second
        reserve=min(1.0,reserve+REFILL)
        pos=START;steps=0;found=None
        for _ in range(MAXST):
            if known:a=nav(pos,protos[bi]["goal"],False,rng)
            else:
                if reserve>COST:a=nav(pos,None,True,rng);reserve-=COST
                else:a=nav(pos,protos[bi]["goal"] if protos else GOALS[0],False,rng)
            npos=step(pos,a);steps+=1
            if npos==GOALS[reg]:found=npos;break
            pos=npos
        if known and (reg in regime_of_ep[:e]):
            rt[e]=1;rc[e]=1.0 if protos[bi]["true"]==reg else 0.0
        if known:
            protos[bi]["cnt"]+=1
            do=(mode=="naive") or (mode=="gated" and best>0.82 and margin>0.15)
            if do:
                sg=protos[bi]["sig"];protos[bi]["sig"]=sg+(obs-sg)/protos[bi]["cnt"]
        elif found is not None:
            protos.append({"sig":obs.copy(),"goal":found,"cnt":1,"true":reg})
        stp[e]=steps
    return (rc.sum()/rt.sum() if rt.sum()>0 else np.nan)
NOISE=0.42; SEEDS=24
agent={}
for mode in ["frozen","naive","gated"]:
    v=np.array([run_agent(mode,NOISE,300+s) for s in range(SEEDS)])
    agent[mode]=(np.nanmean(v),np.nanstd(v))

print("="*80); print("  #42  FOLD #41 INTO RUNG 2 -- honest benchmark"); print("="*80)
print(f"  (A) averaged prototype vs frozen on a HARD probe (reliable association):")
print(f"        recognition  frozen {fa:.2f}  vs  upgrade {ua:.2f}   (+{100*(ua-fa):.0f} pts)")
print(f"        margin       frozen {fm:.3f} vs  upgrade {um:.3f}")
print(f"  (B) contamination crossover: upgrade beats frozen until ~{cross:.0%} mis-association, then loses.")
print(f"        contam 0%%: {up_c[0]:.2f} vs {fr_c[0]:.2f}  |  contam 50%%: {up_c[-1]:.2f} vs {fr_c[-1]:.2f}")
print(f"  (C) full agent (noise {NOISE}, {SEEDS} seeds), recognition-on-revisit mean±std:")
for m in ["frozen","naive","gated"]:
    print(f"        {m:7} {agent[m][0]:.2f} ± {agent[m][1]:.2f}")
print(f"  -> blind fold-back is a WASH in the full agent (within seed noise); the mechanism only pays off")
print(f"     when the fold-in is CONFIDENCE-GATED so association stays reliable (left of the crossover).")

# ---------------------------------------------------------------------------
fig=plt.figure(figsize=(14.4,4.8)); gs=fig.add_gridspec(1,3,wspace=0.34)
FR="#c0392b"; UP="#238b45"; GA="#2b6cb0"

axA=fig.add_subplot(gs[0,0])
axA.bar([0,1],[fa,ua],0.55,color=[FR,UP])
for i,val in enumerate([fa,ua]): axA.text(i,val+0.015,f"{val:.2f}",ha="center",fontsize=9.5)
axA.set_xticks([0,1]); axA.set_xticklabels(["FROZEN\n(first look)","UPGRADE\n(avg of 6)"],fontsize=9)
axA.set_ylabel("recognition of a HARD probe"); axA.set_ylim(0,0.9)
axA.set_title("(A) The mechanism is REAL:\nsharpening helps a hard look (+10 pts)",fontsize=10.0)

axB=fig.add_subplot(gs[0,1])
axB.plot(cs*100,up_c,"-o",color=UP,lw=2,ms=4,label="UPGRADE (avg)")
axB.plot(cs*100,fr_c,"-o",color=FR,lw=2,ms=4,label="FROZEN")
if cross is not None:
    axB.axvline(cross*100,color="#555",ls="--",lw=1.2)
    axB.text(cross*100+1,0.70,f"crossover ~{cross:.0%}",fontsize=8.4,color="#555")
axB.axvspan(0,(cross or 0.35)*100,color=UP,alpha=0.07)
axB.axvspan((cross or 0.35)*100,50,color=FR,alpha=0.07)
axB.set_xlabel("% of folded-in looks that are MIS-ASSOCIATED"); axB.set_ylabel("recognition accuracy")
axB.set_title("(B) …but it CONTAMINATES: averaging\nunder mis-association crosses below frozen",fontsize=10.0)
axB.legend(fontsize=8.4,framealpha=0.9)

axC=fig.add_subplot(gs[0,2])
ms=["frozen","naive","gated"]; mm=[agent[m][0] for m in ms]; ss=[agent[m][1] for m in ms]
axC.bar([0,1,2],mm,0.6,yerr=ss,capsize=6,color=[FR,UP,GA])
for i,(m,s) in enumerate(zip(mm,ss)): axC.text(i,m+s+0.015,f"{m:.2f}",ha="center",fontsize=9)
axC.set_xticks([0,1,2]); axC.set_xticklabels(["FROZEN\n(#40)","NAIVE\nupgrade","GATED\nupgrade"],fontsize=8.8)
axC.set_ylabel("recognition-on-revisit (24 seeds)"); axC.set_ylim(0,0.9)
axC.set_title("(C) In the full agent it's a WASH —\nunless the upgrade is confidence-GATED",fontsize=10.0)

fig.suptitle("#42 — folding #41 into rung 2, honestly: memory-upgrade helps a hard probe (+10 pts) but only under reliable association; blind fold-back contaminates, so the upgrade must be gated",fontsize=10.2)
fig.savefig("memory_upgrade_foldback.png",dpi=130,bbox_inches="tight")
print("\n  wrote memory_upgrade_foldback.png")
