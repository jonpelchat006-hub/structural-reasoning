#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
baby_agent.py -- the FIRST integrated agent: the validated pieces wired into ONE running loop.

Until now the 36 results were separate scripts, each proving one mechanism. This is the first
test of the real question: do they hold together as one agent that learns? We wire, on a tiny
regime-switching environment:
  * BREAK detection  (#36) -- segment the live stream where continuity breaks (a regime change)
  * context-keyed MEMORY anchors (#21) -- store each solved regime, recall it on revisit
  * GAP-driven exploration (#17) -- when the context is novel/uncertain, go learn it
  * FLOW / RESERVE gating (#35, the .14) -- explore only while the reserve allows; conserve when low
  * commit + MASS pinning (#31/#34) -- a confirmed regime pins as an anchor and is reused instantly

ENVIRONMENT: a hidden regime r(t) in {0,1,2} switches every L steps and REVISITS (A,B,A,C,...).
Each step the agent sees a noisy context signature (regime vector + noise) and picks an action in
{0..3}; reward 1 iff the action matches that regime's (unknown) correct action. Retention across
revisits is the whole game.

ABLATIONS (to see each piece contribute):
  * MEMORYLESS  -- segments + learns a regime, but keeps NO anchors -> re-explores every revisit.
  * NO-SEGMENT  -- never breaks; one blended action-value -> plays the globally-commonest action.
  * NO-GATE     -- explores whenever unsure, ignoring the reserve -> reserve crashes -> breakdown.
"""
import numpy as np
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

rng = np.random.default_rng(4)
D=10; NREG=5; NACT=6; L=22
SIG = rng.normal(0,1,(NREG,D)); SIG/=np.linalg.norm(SIG,axis=1,keepdims=True)   # regime signatures
CORRECT = rng.integers(0,NACT,NREG)                                              # unknown to the agent
SCHEDULE = [0,1,2,0,3,1,4,2,3,0,4,1,2,3,4,0,1,4,3,2]                             # learn 5, then revisit heavily
NOISE=0.22
T=len(SCHEDULE)*L
regime_at=np.repeat(SCHEDULE, L)

def observe(t):
    r=regime_at[t]
    return r, SIG[r] + rng.normal(0,NOISE,D)

COST=0.14; REFILL=0.02; RESERVE0=1.0    # exploration is expensive; refill slow -> the reserve must be paced
SIM_ANCHOR=0.72; SIM_CONT=0.45

def run(agent, seed=0):
    rr=np.random.default_rng(100+seed)
    reserve=RESERVE0
    anchors=[]            # list of dict(sig, action, mass)
    cur=None              # current unknown segment: dict(sig, tried{}, solved)
    glob={}               # for NO-SEGMENT: global tried counts action-> [correct, total]
    rew=np.zeros(T); res=np.zeros(T); explored=np.zeros(T); recalled=np.zeros(T)
    for t in range(T):
        r,obs=observe(t)
        act=None; mode="?"
        if agent=="nosegment":
            # never segment: pick globally-best action seen so far (blends all regimes)
            if glob and rr.random()>0.1:
                act=max(glob, key=lambda a: glob[a][0]/max(glob[a][1],1))
            else:
                act=int(rr.integers(NACT))
            mode="glob"
        else:
            # nearest stored anchor
            sim_anc,ai=(-1,-1)
            if anchors and agent!="memoryless":
                sims=[float(np.dot(obs,a["sig"])/ (np.linalg.norm(obs)*np.linalg.norm(a["sig"]))) for a in anchors]
                ai=int(np.argmax(sims)); sim_anc=sims[ai]
            sim_cur=-1
            if cur is not None:
                sim_cur=float(np.dot(obs,cur["sig"])/(np.linalg.norm(obs)*np.linalg.norm(cur["sig"])))
            if sim_anc>SIM_ANCHOR:                       # RECALL a known regime (retention)
                act=anchors[ai]["action"]; mode="recall"; recalled[t]=1
            elif cur is not None and sim_cur>SIM_CONT:   # continue the current segment
                if cur["solved"] is not None:
                    act=cur["solved"]; mode="exploit"
                else:
                    can=(reserve>COST) or (agent=="nogate")
                    if can:
                        untried=[a for a in range(NACT) if a not in cur["tried"]]
                        act=int(rr.choice(untried)) if untried else int(rr.integers(NACT))
                        mode="explore"; explored[t]=1
                        if agent!="nogate": reserve-=COST
                        else: reserve-=COST
                    else:
                        act=max(cur["tried"], key=lambda a: cur["tried"][a]) if cur["tried"] else 0
                        mode="conserve"
            else:                                        # BREAK -> new segment (a gap)
                cur={"sig":obs.copy(),"tried":{},"solved":None}
                can=(reserve>COST) or (agent=="nogate")
                if can:
                    act=int(rr.integers(NACT)); mode="explore"; explored[t]=1; reserve-=COST
                else:
                    act=0; mode="conserve"
        # environment reward -- but if the reserve is already spent (only NO-GATE lets it go <0),
        # the agent is in BREAKDOWN and its action is corrupted regardless of correctness (#35).
        breakdown = reserve < 0
        got=0 if breakdown else (1 if act==CORRECT[r] else 0)
        rew[t]=got
        reserve=min(RESERVE0, reserve+REFILL)   # refill (can't lift it above 0 in one step if deep negative)
        res[t]=reserve
        # learning
        if agent=="nosegment":
            g=glob.setdefault(act,[0,0]); g[0]+=got; g[1]+=1
        else:
            if cur is not None and mode in ("explore",):
                cur["tried"][act]=got
                if got==1:
                    cur["solved"]=act
                    if agent!="memoryless":
                        # commit / pin an anchor (mass)
                        anchors.append({"sig":cur["sig"].copy(),"action":act,"mass":1})
            if mode=="recall" and got==1 and ai>=0:
                anchors[ai]["mass"]+=1
    return dict(rew=rew,res=res,explored=explored,recalled=recalled)

AGENTS=["integrated","memoryless","nosegment","nogate"]
RES={a: run(a) for a in AGENTS}

# post-revisit accuracy: the first 4 steps of every block whose regime appeared earlier
block_start=[b*L for b in range(len(SCHEDULE))]
revisit_blocks=[b for b in range(len(SCHEDULE)) if SCHEDULE[b] in SCHEDULE[:b]]
def post_revisit_acc(rew):
    idx=[t for b in revisit_blocks for t in range(block_start[b], block_start[b]+4)]
    return float(np.mean(rew[idx]))

print("="*80)
print("  THE FIRST INTEGRATED AGENT: memory + breaks + gaps + flow-gating, one running loop")
print("="*80)
print(f"  {T} steps, {NREG} hidden regimes switching & revisiting; reward = matched the regime's action")
print()
print(f"  {'agent':13}{'total reward':>14}{'reward on REVISITS':>20}{'reserve alive %':>17}")
for a in AGENTS:
    R=RES[a]
    alive=float(np.mean(R['res']>=0))*100
    print(f"  {a:13}{R['rew'].sum():>14.0f}{post_revisit_acc(R['rew']):>20.2f}{alive:>17.0f}")
print()
I=RES["integrated"]
print(f"  -> INTEGRATED wins because the pieces cooperate: it SEGMENTS at the breaks, RECALLS a regime it")
print(f"     already solved (revisit reward {post_revisit_acc(I['rew']):.2f}), EXPLORES only the genuinely new ones,")
print(f"     and GATES exploration on the reserve so it never breaks down (reserve alive 100%).")
print(f"  -> MEMORYLESS re-explores every revisit (revisit reward {post_revisit_acc(RES['memoryless']['rew']):.2f}); NO-SEGMENT blends the")
print(f"     regimes into one wrong action; NO-GATE burns its reserve and stalls in breakdown.")

# ---------------------------------------------------------------------------
# PLOT
# ---------------------------------------------------------------------------
fig=plt.figure(figsize=(14.4,7.6)); gs=fig.add_gridspec(2,2,hspace=0.34,wspace=0.24,height_ratios=[1,1])
cols={"integrated":"#238b45","memoryless":"#c0392b","nosegment":"#e0a021","nogate":"#8a2be2"}

# (A) cumulative reward
axA=fig.add_subplot(gs[0,0])
for a in AGENTS: axA.plot(np.cumsum(RES[a]["rew"]), color=cols[a], lw=2, label=a)
for b in block_start: axA.axvline(b, color="#eee", lw=0.6, zorder=0)
axA.set_xlabel("step (live stream)"); axA.set_ylabel("cumulative reward")
axA.set_title("Cumulative reward — the integrated agent learns and RETAINS", fontsize=10.5)
axA.legend(fontsize=8.5, framealpha=0.9, loc="upper left")

# (B) reward on revisits
axB=fig.add_subplot(gs[0,1])
vals=[post_revisit_acc(RES[a]["rew"]) for a in AGENTS]
axB.bar(range(4),vals,color=[cols[a] for a in AGENTS])
axB.set_xticks(range(4)); axB.set_xticklabels(AGENTS, fontsize=8)
axB.set_ylabel("accuracy on regime REVISITS"); axB.set_ylim(0,1)
for i,v in enumerate(vals): axB.text(i,v+0.02,f"{v:.2f}",ha="center",fontsize=9)
axB.set_title("Retention: recall a solved regime on revisit", fontsize=10.5)

# (C) reserve trajectories
axC=fig.add_subplot(gs[1,0])
for a in AGENTS: axC.plot(RES[a]["res"], color=cols[a], lw=1.4, label=a)
axC.axhline(0, color="#c0392b", ls=":", lw=1)
axC.set_xlabel("step"); axC.set_ylabel("flow reserve (.14 gate)")
axC.set_title("The reserve: gated agents stay alive; NO-GATE crashes below 0 (breakdown)", fontsize=10.5)
axC.legend(fontsize=8, framealpha=0.9, loc="lower right")

# (D) rolling accuracy — integrated vs memoryless, regime bands
axD=fig.add_subplot(gs[1,1])
def roll(x,k=15): return np.convolve(x,np.ones(k)/k,mode="same")
axD.plot(roll(RES["integrated"]["rew"]), color=cols["integrated"], lw=2, label="integrated")
axD.plot(roll(RES["memoryless"]["rew"]), color=cols["memoryless"], lw=2, label="memoryless")
band=["#eef7ee","#fdeeee","#fff7e6","#eef2fb","#f6eefb"]
for b in range(len(SCHEDULE)):
    axD.axvspan(block_start[b], block_start[b]+L, color=band[SCHEDULE[b]%len(band)], zorder=0)
axD.set_xlabel("step (regime bands: colour = which regime)"); axD.set_ylabel("rolling accuracy")
axD.set_title("Integrated snaps back instantly on a revisit; memoryless relearns each time", fontsize=10.5)
axD.legend(fontsize=8.5, framealpha=0.9, loc="lower right"); axD.set_ylim(0,1.05)

fig.suptitle("The first integrated agent: breaks segment the stream · memory recalls solved regimes on revisit · gaps drive exploration · the reserve gates it — all in one loop",
             fontsize=10.4, y=0.995)
fig.savefig("baby_agent.png", dpi=130, bbox_inches="tight")
print("\n  wrote baby_agent.png")
