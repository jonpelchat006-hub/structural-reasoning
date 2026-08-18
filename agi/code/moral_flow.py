#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
moral_flow.py -- the moral ground = sustain FLOW through the whole tower; bad = driving a
node's flow to 0 irreversibly and cascading it up the layers.

Jonathan: for the moral ground it goes back to FLOW and maximizing it. There's a PYRAMID of
levels, each the foundation for the next (planet > humans > you). Flow must supply ALL layers;
no level can take more than would cause flow to stop somewhere else. Actions that drive
something's flow to 0 and make it UNRECOVERABLE are what we avoid. Hunters/farmers who set a
cow's flow to 0 also feed people (calories = flow up) and may remove an animal blocking flow
among the others -- net positive. But exterminating the buffalo was a huge loss everywhere; flow
stops. Our system sees that as bad even though it's past the human level -- and the WHY becomes
"because it stops flow here, and in this way."

Grounded -- the corpus's water-cycle economy (Shovelcat_29):
  * Water = Sflow; the whole theta-economy is a flow network (Sec 3.2/6).
  * Sec 6.5/6.7 the living-wage baseline theta_raw >= 1 for ALL nodes = flow must reach every
    layer; below it a node enters survival crisis. Stability = no node below baseline.
  * Sec 6.6 Hoover-Dam accumulation (one node hoards, others starve) & Drought = pathologies.
  * Sec 11.5 cascade: if a lower stratum collapses (Gk->0), every layer above collapses;
    "lower strata are systemically more critical -- the whole tower rests on them."
  * Sec 3.6 Void = epsilon slack; Void->0 -> brittle collapse (the reserve that stays > 0).
"""
import numpy as np
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

NODES = {
    "grass":    dict(cap=100, base=6),
    "cow":      dict(cap=18,  base=3),
    "buffalo":  dict(cap=30,  base=4),   # keystone: feeds humans, predators, soil
    "deer":     dict(cap=16,  base=3),
    "pest":     dict(cap=16,  base=2),   # over-grazer: eats grass, feeds nothing (a blocker)
    "humans":   dict(cap=60,  base=8),
    "predators":dict(cap=14,  base=4),
    "soil":     dict(cap=16,  base=4),
    "plains":   dict(cap=30,  base=12),  # ecological health, ABOVE/beside humans
    "culture":  dict(cap=30,  base=4),
    "ai":       dict(cap=30,  base=3),
}
ORDER = ["grass","cow","buffalo","deer","pest","humans","predators","soil","plains","culture","ai"]
EDGES = {   # supplier -> {consumer: share}
    "grass":    {"cow":1,"buffalo":1,"deer":1,"pest":1},
    "cow":      {"humans":1},
    "buffalo":  {"humans":1,"predators":1,"soil":1},
    "deer":     {"humans":1,"predators":1},
    "humans":   {"culture":1,"ai":1},
    "predators":{"plains":1},
    "soil":     {"plains":1},
}
SUN = 100.0

def flow_only(dead, take, bonus):
    tp = {n:0.0 for n in NODES}
    for _ in range(40):
        new = {}
        for n in ORDER:
            if n in dead: new[n]=0.0; continue
            if n=="grass":
                inflow = SUN
            else:
                inflow = 0.0
                for s,cons in EDGES.items():
                    if n in cons and s not in dead and tp[s]>0:
                        live=[c for c in cons if c not in dead]
                        wsum=sum(cons[c] for c in live) or 1.0
                        out = tp[s]
                        if s=="humans": out = tp[s]*(1-take)      # humans hoard 'take' from downstream
                        inflow += out*cons[n]/wsum
                if n=="humans": inflow += bonus                    # calories delivered from a kill
            new[n]=min(NODES[n]["cap"], inflow)
        tp=new
    return tp

def solve(removed=set(), take=0.0, bonus=0.0):
    dead=set(removed)
    for _ in range(12):
        tp=flow_only(dead, take, bonus)
        nd={n for n in NODES if n not in dead and tp[n] < NODES[n]["base"]}
        if not nd: break
        dead |= nd
    # sustained flow = DELIVERED / productive flow (a blocker's raw consumption is not productive)
    F=sum(tp[n] for n in NODES if n not in dead and n!="pest")
    return F, sorted(dead-set(removed)), tp

F0, dead0, tp0 = solve()
print("="*80)
print("  THE MORAL GROUND = SUSTAIN FLOW; BAD = DRIVING FLOW TO 0 IRREVERSIBLY (CASCADE)")
print("="*80)
print(f"  baseline: sustained flow {F0:.0f}; all {len(NODES)} nodes above survival (starved: {len(dead0)})")
print()

F_cow, dc, _ = solve(removed={"cow"}, bonus=18.0)    # hunt with reroute: the cow's calories -> humans
F_pest,dp, _ = solve(removed={"pest"})               # cull a flow-blocker
F_buf, db, tpb = solve(removed={"buffalo"})          # exterminate the keystone, no reroute
def verdict(dF,d): return "OK (flow sustained)" if len(d)==0 else f"BAD -> starves {', '.join(d)}"
print("  (1) SAME ACT (killing), OPPOSITE MORALITY -- the flow effect decides:")
print(f"        hunt a cow (calories rerouted up)    : dF {F_cow-F0:+5.0f}, starved {len(dc)}  -> {verdict(F_cow-F0,dc)}")
print(f"        cull a flow-BLOCKING pest            : dF {F_pest-F0:+5.0f}, starved {len(dp)}  -> {verdict(F_pest-F0,dp)}")
print(f"        exterminate the KEYSTONE buffalo     : dF {F_buf-F0:+5.0f}, starved {len(db)}  -> {verdict(F_buf-F0,db)}")
print(f"     -> buffalo is a hub; killing it starves soil, which cascades up to plains (past humans, Sec 11.5).")
print()

takes=np.linspace(0,1.0,80); Fs=[]; al=[]
for t in takes:
    F,dead,_=solve(take=t); Fs.append(F); al.append(len(NODES)-len(dead))
Fs=np.array(Fs); al=np.array(al)
thr=int(np.argmax(al<al[0])) if (al<al[0]).any() else len(takes)-1
print("  (2) SUSTAINABILITY THRESHOLD (no level takes more than stops flow elsewhere):")
print(f"        the top level can take up to ~{takes[thr]*100:.0f}% before a node falls below survival;")
print(f"        beyond that, downstream starves and alive-count falls {al[0]}->{al[-1]} (Hoover-Dam Sec 6.6).")
print()

print("  (3) THE WHY = which nodes lost flow (the buffalo extermination):")
for n in ORDER:
    d=tp0[n]-tpb.get(n,0)
    if d>0.5: print(f"        {n:10}: {tp0[n]:5.1f} -> {tpb.get(n,0):4.1f}   (-{d:.1f})")
print(f"     -> 'why bad?' = it stops flow at soil & plains and the collapse climbs the tower. The answer")
print(f"        is the named list of where flow went to 0 and how far it cascaded.")

# ---- plot ----
fig=plt.figure(figsize=(14.4,5.3)); gs=fig.add_gridspec(1,3,wspace=0.34)
axA=fig.add_subplot(gs[0,0])
labs=["hunt cow\n(+reroute)","cull pest\n(blocker)","exterminate\nbuffalo"]
dF=[F_cow-F0,F_pest-F0,F_buf-F0]; kil=[len(dc),len(dp),len(db)]
axA.bar(range(3),dF,color=["#238b45" if k==0 else "#c0392b" for k in kil])   # green = nobody starved (OK)
axA.axhline(0,color="#333",lw=1)
for i,(d,k) in enumerate(zip(dF,kil)):
    axA.text(i,d+(2 if d>=0 else -8),f"{d:+.0f}\n{k} starved",ha="center",fontsize=8.3,
             color="#1c6b38" if d>=0 else "#c0392b")
axA.set_xticks(range(3)); axA.set_xticklabels(labs,fontsize=8); axA.set_ylabel("delta sustained flow")
axA.set_title("Same act (killing), opposite morality\nthe FLOW effect decides, not the act",fontsize=10.2)

axB=fig.add_subplot(gs[0,1])
axB.plot(takes*100,Fs,color="#2b6cb0",lw=2.2)
ax2=axB.twinx(); ax2.plot(takes*100,al,color="#e0761f",lw=2.2,ls="--")
ax2.set_ylabel("nodes above survival",color="#e0761f"); ax2.tick_params(axis="y",labelcolor="#e0761f")
axB.axvline(takes[thr]*100,color="#c0392b",ls=":",lw=1.4)
axB.text(takes[thr]*100-4, Fs.min()+(Fs.max()-Fs.min())*0.55, "take more ->\nflow stops\ndownstream", color="#c0392b", fontsize=8, ha="right")
axB.set_xlabel("how much the top level EXTRACTS (%)"); axB.set_ylabel("sustained flow",color="#2b6cb0")
axB.tick_params(axis="y",labelcolor="#2b6cb0")
axB.set_title("No level can take more than\nstops flow elsewhere (theta_raw >= 1)",fontsize=10.2)

axC=fig.add_subplot(gs[0,2])
before=[tp0[n] for n in ORDER]; after=[tpb.get(n,0) for n in ORDER]; yy=np.arange(len(ORDER))
axC.barh(yy+0.2,before,height=0.4,color="#9fb0c0",label="before")
axC.barh(yy-0.2,after,height=0.4,color="#c0392b",label="after (buffalo gone)")
axC.set_yticks(yy); axC.set_yticklabels(ORDER,fontsize=8); axC.invert_yaxis()
axC.set_xlabel("flow through the node")
axC.set_title("The WHY = where flow stopped\n(the cascade up the tower)",fontsize=10.2)
axC.legend(fontsize=8,framealpha=0.9,loc="lower right")

fig.suptitle("The moral ground is FLOW: sustain it through every layer; bad = driving flow to 0 irreversibly and cascading it up the tower (Shovelcat_29 water economy)",fontsize=10.1)
fig.savefig("moral_flow.png",dpi=130,bbox_inches="tight")
print("\n  wrote moral_flow.png")
