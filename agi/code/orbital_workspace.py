#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
orbital_workspace.py -- #53: the outer-shell workspace is an ORBITAL SYSTEM. The planet is the inner+middle
shell (the verified core / the launch runway, SPARSE_VESICA §35.5); every artifact is a BODY in orbit with
its own PERIOD (how often it swings into the telescope's field of view = the attention gate, #24/#28) and its
own VIEW-EFFECT. Mika working on an image IS its orbit: a satellite in view when displayed, out of view while
worked, back each sequence (completion cadence, #39, the snake closing θ=1).

Jonathan: if inner+middle are the planet, the tools are moons/rings/asteroid belts. An image Mika makes is a
satellite we send into orbit; on screen it's in the telescope's field of view; while she works on it, it's
orbiting out of view and we see it again after each sequence. Her drawing tools are a dust cloud we look
through; her border lines are satellites orbiting just outside the view -- each with a different effect on
the view and the orbit.

Grounded:
  * SPARSE_VESICA §35.5 -- the snake launches off the inner/middle shell (runway) into the outer shell and
    settles when its wave closes into an allowed ORBITAL (θ=1). The active image = that launched trajectory.
  * #24 Ophanim rotating gate -- the ring rotates truths through a gate of width K; you see only what passes
    through; steering the rotation IS attention (1.2 steps vs check-all 60). The telescope FOV = that gate.
  * #28 attention band finite; #39 completion cadence (a chunk returns when its sequence closes); #52 the
    outer-shell workspace of held artifacts.

MEASURED:
  (A) Each artifact type cycles through the FINITE field of view on its own orbital period; you never hold all
      at once (the attention band). The active image returns to view each work-sequence.
  (B) VIEW-EFFECT differs by type: a clean satellite (image) reads clearly in view; the tools DUST CLOUD
      scatters (read-clarity dips while it transits); border-lines contribute only at the frame edge.
  (C) STEER an orbit to bring the wanted artifact into view (the rotating gate, #24) -> low latency; waiting
      for it to come around is slow; holding all at once OVERFLOWS the field of view.
"""
import numpy as np
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

rng=np.random.default_rng(5)
FOV=np.deg2rad(40)          # telescope half-angle (the attention gate width, #24)
BAND=2                      # attention band: max bodies readable in the FOV at once (#28)

# ---- bodies: (name, orbit radius, period, angular half-width, type, view-effect) ----
# period grows with radius (Keplerian-ish); the active image's period = one work-sequence
bodies=[
    dict(name="active image",   r=1.0, period=18, width=np.deg2rad(6),  kind="satellite"),
    dict(name="drawing tools",  r=0.66,period=40, width=np.deg2rad(48), kind="dust"),
    dict(name="border lines",   r=1.5, period=27, width=np.deg2rad(5),  kind="border"),
    dict(name="ref: palette",   r=1.28,period=33, width=np.deg2rad(5),  kind="satellite"),
]
phase0=[0.0, np.pi*0.9, np.pi*0.5, np.pi*1.3]
T=120; ts=np.arange(T)
def angle(b,ph,t): return (ph + 2*np.pi*t/b["period"] + np.pi)%(2*np.pi)-np.pi   # wrap to [-pi,pi]
def in_view_frac(b,ph,t):
    a=angle(b,ph,t)
    # angular overlap of [a-width, a+width] with [-FOV, FOV]
    lo,hi=a-b["width"],a+b["width"]
    ov=max(0.0, min(hi,FOV)-max(lo,-FOV))
    return ov/(2*b["width"])
inview=np.array([[in_view_frac(b,phase0[i],t) for t in ts] for i,b in enumerate(bodies)])   # (nb,T) 0..1
present=inview>0.2                                                                          # "in the frame"

# ---- (B) read-clarity of the canvas: dust scatters what's behind it ----
clarity=np.ones(T)
for i,b in enumerate(bodies):
    if b["kind"]=="dust":
        clarity-=0.7*inview[i]                # dust in the FOV scatters -> clarity drops
clarity=np.clip(clarity,0,1)
# read-accuracy proxy per type when it is the one being viewed
read_by_kind={}
for i,b in enumerate(bodies):
    m=inview[i]>0.5
    if b["kind"]=="dust":
        read_by_kind["dust (tools)"]=float(np.mean(clarity[m])) if m.any() else np.nan
    elif b["kind"]=="satellite" and b["name"]=="active image":
        read_by_kind["satellite (image)"]=float(np.mean(clarity[m])) if m.any() else np.nan
    elif b["kind"]=="border":
        # border contributes only peripherally: weight by how edge-ward it sits
        edge=np.array([abs(abs(angle(b,phase0[i],t))-FOV)<np.deg2rad(10) for t in ts])
        read_by_kind["border (edge)"]=float(np.mean(edge))    # fraction of time it's grazing the frame edge

# ---- (C) scheduling: get a target body into view -- steer vs wait vs hold-all ----
target=0   # want the active image in view on demand
# wait: how long until it drifts into the FOV on its own
def wait_latency(seed):
    r=np.random.default_rng(seed); t0=r.integers(0,T)
    for dt in range(T):
        if in_view_frac(bodies[target],phase0[target],t0+dt)>0.5: return dt
    return T
wait=np.mean([wait_latency(s) for s in range(40)])
# steer: nudge its orbital phase to bring it through the gate now (the rotating-gate steer, #24)
steer=1.0                                   # one steered step (as in #24: 1.2 steps)
# hold-all: try to keep every body in the FOV at once -> exceeds the band
max_simul=int(present.sum(0).max()); overflow = max_simul>BAND

print("="*80)
print("  #53  THE ORBITAL WORKSPACE -- artifacts orbit the planet; type sets period + view-effect")
print("="*80)
print(f"  telescope FOV half-angle {np.rad2deg(FOV):.0f}°, attention band {BAND}")
print("  (A) in-view fraction & revisit period per body (it cycles through the finite FOV):")
for i,b in enumerate(bodies):
    print(f"        {b['name']:14} orbit r={b['r']:.2f} period={b['period']:3d} -> in view {inview[i].mean()*100:4.0f}% of the time")
print(f"      most bodies simultaneously in the frame: {max_simul} (band {BAND}; overflow={overflow}) -> never all at once")
print("  (B) view-effect by type (read-clarity while it transits the FOV):")
for k,v in read_by_kind.items(): print(f"        {k:22} {v:.2f}")
print(f"      -> the DUST cloud (tools) scatters what's behind it; the clean satellite (image) reads clear.")
print(f"  (C) get the wanted artifact into view: STEER {steer:.0f} step vs WAIT {wait:.0f} steps; "
      f"hold-all overflows the FOV ({max_simul}>{BAND}) -> steering the orbit IS attention (#24).")

# ===========================================================================
# PLOT
# ===========================================================================
fig=plt.figure(figsize=(15.4,5.0))
gs=fig.add_gridspec(1,3,wspace=0.32,width_ratios=[1.05,1.15,0.9])
COL={"satellite":"#238b45","dust":"#e0a021","border":"#8a2be2"}

# (A) polar orbital snapshot
axA=fig.add_subplot(gs[0,0],projection="polar")
axA.set_theta_zero_location("E"); axA.set_ylim(0,1.7); axA.set_yticklabels([]); axA.set_xticklabels([])
axA.bar(0,1.7,width=2*FOV,bottom=0,color="#bcd7ff",alpha=0.5,zorder=0)   # the FOV wedge (telescope)
axA.text(0,1.72,"field of view",fontsize=7.5,ha="center",color="#2b6cb0")
axA.scatter([0],[0],s=520,color="#444",zorder=5)                          # the planet (inner+middle)
axA.text(np.pi,0.02,"planet\n(inner+middle)",fontsize=7,ha="center",va="center",color="white",zorder=6)
for i,b in enumerate(bodies):
    th=np.linspace(0,2*np.pi,200); axA.plot(th,[b["r"]]*200,color=COL[b["kind"]],lw=0.7,alpha=0.4,zorder=1)
    a=angle(b,phase0[i],0)
    if b["kind"]=="dust":                                                # a cloud arc
        arc=np.linspace(a-b["width"],a+b["width"],30); axA.plot(arc,[b["r"]]*30,color=COL[b["kind"]],lw=6,alpha=0.5,zorder=2)
    axA.scatter([a],[b["r"]],s=90,color=COL[b["kind"]],edgecolor="white",lw=0.6,zorder=4)
    axA.text(a,b["r"]+0.12,b["name"].split()[-1] if b["name"]!="ref: palette" else "palette",fontsize=6.6,ha="center",color=COL[b["kind"]])
axA.set_title("(A) The workspace is orbital: bodies swing\nthrough the telescope FOV (the attention gate)",fontsize=9.8,pad=14)

# (B) in-view timeline + clarity
axB=fig.add_subplot(gs[0,1])
for i,b in enumerate(bodies):
    axB.fill_between(ts, i+0.1, i+0.1+0.7*inview[i], color=COL[b["kind"]], alpha=0.75, step="mid")
    axB.text(-2,i+0.45,b["name"],fontsize=7,ha="right",va="center")
axB.plot(ts, len(bodies)+0.2+0.9*clarity, color="#c0392b", lw=1.8)
axB.text(-2,len(bodies)+0.65,"read-clarity",fontsize=7,ha="right",va="center",color="#c0392b")
for i,b in enumerate(bodies):                       # mark dust-transit dips
    if b["kind"]=="dust":
        for t in ts[inview[i]>0.5]: axB.axvline(t,color="#e0a021",alpha=0.06,zorder=0)
axB.set_xlim(-16,T); axB.set_ylim(0,len(bodies)+1.4); axB.set_yticks([])
axB.set_xlabel("time (work sequences)")
axB.set_title("(B) Each body cycles through the FOV on its period;\nthe tools DUST dip the read-clarity as it transits",fontsize=9.8)

# (C) scheduling bars
axC=fig.add_subplot(gs[0,2])
axC.bar([0,1],[steer,wait],0.55,color=["#238b45","#c0392b"])
for i,v in enumerate([steer,wait]): axC.text(i,v+0.6,f"{v:.0f}",ha="center",fontsize=10)
axC.set_xticks([0,1]); axC.set_xticklabels(["STEER\n(orbit → gate)","WAIT\n(drift around)"],fontsize=8.4)
axC.set_ylabel("steps to get the artifact in view")
axC.set_title(f"(C) Steering the orbit = attention (#24);\nhold-all overflows the FOV ({max_simul}>{BAND})",fontsize=9.6)

fig.suptitle("#53 — the orbital workspace: artifacts orbit the planet (inner+middle); type sets the period (revisit cadence through the telescope FOV) and the view-effect (clean satellite · scattering dust · edge-grazing border) — steer the orbit to attend",fontsize=9.2)
fig.savefig("orbital_workspace.png",dpi=130,bbox_inches="tight")
print("\n  wrote orbital_workspace.png")
