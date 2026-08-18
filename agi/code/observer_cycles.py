#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
observer_cycles.py -- the observer defines the cycle, the cycle becomes memory,
and what the observer ignores falls in its gaps.

Jonathan: pick an observer whose score is based on something the object can REPEAT;
when those branches repeat, that becomes a memory. A workout cycle can be defined by
the heart-rate going up and coming back to rest — the actual workout can be anything.
"Upgrading / a different perspective" = looking from VO2-max instead. Then everything
that observer didn't care about during the cycle goes in ITS gaps: the HR observer takes
a larger memory (HR is up through the whole warm-up→cooldown arch), while the VO2 observer
only cares about the hard part and keeps different workouts' hard efforts as its memories.

So the SAME stream, seen by two observers, is segmented into different cycles → different
memories → different gaps. Grounded: an observer is a projection/measurement
(FOLDING_OBSERVERS, the spanning frame); a cycle closes when the observer's score returns
to origin (FOLDING_FREQUENCY spin-identity); what reads as ~0 to an observer is off its
frame = its gap (FOLDING_OBSERVER_FRAME; the .14 orthogonal complement).

MEASURED: over one workout stream, compare the HR observer and the VO2 observer on
  #cycles (memories) · mean cycle length · gap fraction (time it ignores) · and the
  fraction of the stream one observer watches while the other gaps it.
"""
import numpy as np
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

# ---- build a workout stream: HR (broad arches) + VO2 (spikes on hard efforts only) ----
HR_REST, VO2_REST = 60.0, 5.0
hr=[]; vo2=[]; marks=[]   # marks: (start, label)
def seg(n, hr_lvl, vo2_lvl, ramp=False):
    global hr, vo2
    for i in range(n):
        f = (i/n) if ramp else 1.0
        hr.append(hr_lvl if not ramp else HR_REST + (hr_lvl-HR_REST)*f)
        vo2.append(vo2_lvl)
def rest(n): seg(n, HR_REST, VO2_REST)

def workout(kind):
    marks.append((len(hr), kind))
    if kind == "steady jog":
        seg(35, 135, VO2_REST, ramp=True); seg(120, 138, 12); seg(35, HR_REST, VO2_REST)
    elif kind == "intervals":
        seg(35, 150, VO2_REST, ramp=True)
        for _ in range(5):
            seg(16, 155, 55)          # hard -> VO2 spikes
            seg(16, 140, 10)          # easy -> VO2 back down (HR stays up)
        seg(35, HR_REST, VO2_REST)
    elif kind == "sprint":
        seg(28, 150, VO2_REST, ramp=True); seg(42, 168, 60); seg(40, HR_REST, VO2_REST)

rest(20)
for k in ["steady jog","intervals","sprint","intervals"]:
    workout(k); rest(25)

hr=np.array(hr); vo2=np.array(vo2); T=len(hr)
t=np.arange(T)
hr += np.random.default_rng(1).normal(0,1.2,T); vo2 += np.random.default_rng(2).normal(0,1.0,T)

# ---- an observer: a channel + a threshold; a CYCLE = an excursion above baseline and back ----
def cycles(sig, thr):
    on = sig > thr; segs=[]; i=0
    while i < len(sig):
        if on[i]:
            j=i
            while j<len(sig) and on[j]: j+=1
            segs.append((i,j)); i=j
        else: i+=1
    return segs

HR_THR, VO2_THR = HR_REST+15, VO2_REST+15
hr_cyc  = cycles(hr, HR_THR)
vo2_cyc = cycles(vo2, VO2_THR)

def summarize(name, segs):
    cov = sum(b-a for a,b in segs)
    lens = [b-a for a,b in segs]
    return dict(name=name, n=len(segs), mean_len=(np.mean(lens) if lens else 0),
                gap_frac=1-cov/T, cov=cov)
H=summarize("HR (up→rest)", hr_cyc); V=summarize("VO2 (hard part)", vo2_cyc)

# ---- what one observer watches while the other gaps it ----
hr_on = hr>HR_THR; vo2_on = vo2>VO2_THR
hr_only = np.mean(hr_on & ~vo2_on)     # HR active but VO2 ignores (warm-ups, steady, cooldown)
vo2_only= np.mean(vo2_on & ~hr_on)     # VO2 active but HR ignores (~none: hard parts are always HR-active)

print("="*72)
print("  THE OBSERVER DEFINES THE CYCLE → THE MEMORY → ITS GAPS")
print("="*72)
print(f"  one workout stream ({T} steps): steady jog · intervals · sprint · intervals")
print()
print(f"  {'observer':22}{'#cycles (memories)':>20}{'mean length':>14}{'gap fraction':>15}")
for O in (H,V):
    print(f"  {O['name']:22}{O['n']:>20}{O['mean_len']:>14.0f}{O['gap_frac']:>15.2f}")
print()
print(f"  the two observers gap DIFFERENT things (same stream):")
print(f"     HR watches but VO2 ignores: {hr_only*100:4.0f}% of the stream (warm-ups / steady / cooldown)")
print(f"     VO2 watches but HR ignores: {vo2_only*100:4.0f}% (≈0 — a hard effort is always HR-active too)")
print()
print(f"  -> the HR observer's cycle = up-then-rest, so it swallows each WHOLE workout as one")
print(f"     long memory ({H['n']} memories, mean {H['mean_len']:.0f} long): a LARGER, coarser memory.")
print(f"  -> the VO2 observer only fires on the HARD part, so it segments the SAME stream into")
print(f"     {V['n']} short, selective memories (mean {V['mean_len']:.0f}) — the steady jog leaves NO VO2 memory")
print(f"     at all, and the warm-ups sit in its gaps ({V['gap_frac']*100:.0f}% gap). 'Upgrading' the observer")
print(f"     re-cuts the stream: different cycles, different memories, different gaps.")

# ---------------------------------------------------------------------------
# PLOT: two stacked channels with their cycle bands + gaps shaded.
# ---------------------------------------------------------------------------
fig, (a1,a2) = plt.subplots(2,1, figsize=(12.4,6.4), sharex=True)
for a in (a1,a2):
    for s,lab in marks:
        a.axvline(s, color="#ddd", lw=0.8)
# HR
a1.plot(t, hr, color="#c0392b", lw=1.4)
a1.axhline(HR_THR, color="#c0392b", ls=":", lw=1, alpha=0.6)
for (s,e) in hr_cyc: a1.axvspan(s,e, color="#c0392b", alpha=0.10)
a1.set_ylabel("heart rate"); a1.set_title("HR observer — cycle = up→rest → each WHOLE workout is one long memory (red bands); gaps = rest between", fontsize=10.5)
for s,lab in marks: a1.text(s+3, hr.max()-6, lab, fontsize=8, color="#555")
# VO2
a2.plot(t, vo2, color="#238b45", lw=1.4)
a2.axhline(VO2_THR, color="#238b45", ls=":", lw=1, alpha=0.6)
for (s,e) in vo2_cyc: a2.axvspan(s,e, color="#238b45", alpha=0.16)
a2.set_ylabel("VO₂"); a2.set_xlabel("time (steps)")
a2.set_title(f"VO₂ observer — cycle = the hard part only → {V['n']} short selective memories; warm-ups/steady in its gaps ({V['gap_frac']*100:.0f}%)", fontsize=10.5)

fig.tight_layout(); fig.savefig("observer_cycles.png", dpi=130)
print("\n  wrote observer_cycles.png")
