#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
second_wind.py -- why one budget can't be intelligent: the golden-field reserve.

Jonathan: "when people run they burn out and want to give up, but when there's a
goal just ahead we get that boost to make it through. if we just had one budget
that doesn't make sense. adrenaline lets people survive things they otherwise
wouldn't... the golden field as a last attempt... as the tank dries up it shows
the golden field underneath... and if the mass inside doesn't have fluid coming
back in it starts to break down."

Grounding (all in-project):
  * the golden field is the framework's LAST-RESORT move -- SPHERE_GENERATOR J.4:
    placement has three modes, and the third, "exploratory-blind = the golden-angle
    step," fires ONLY when no known neighbour can be anchored to (~12% of cases).
    A costly, held-back move you spend when normal search is exhausted.
  * spend the reserve to zero and the mass fractures -- Shovelcat_29 4.8: void slack
    e->0 => "compressed sponge: brittle, vulnerable to collapse"; FOLDING_CHANNELS:
    drive every budget to zero EXCEPT the flow reserve, or the vortex locks.
  * mass without replenishment fails -- SPARSE_VESICA 28.4 (veins deplete),
    conservation of dust; FOLDING_SATURATION_BUDGET (the reserve banked at the axle).
  * extends Test 4's endurance law R0/(d-s): here a SECOND tier sits under the tank.

THE CLAIMS
----------
A one-budget agent burns out at a FIXED reach, no matter how close the goal was --
"give up at the same point whether the goal is 1 step or 100 away." That is the
thing that "doesn't make sense."

Add a golden-field emergency reserve, drawn from a slowly-refilling structural MASS
(spending it is damage). Three spend policies, over a long stream of tasks of mixed
difficulty (easy / hard-but-reachable-with-a-boost / hopeless):

  NONE   -- never fire the reserve (one budget). Misses every hard task.
  ALWAYS -- fire whenever the base runs out (adrenaline always on). Finishes hard
            tasks early, but burns mass on HOPELESS tasks too -> mass breaks down ->
            base capacity itself shrinks -> it can't even do easy tasks. Collapse.
  GATED  -- fire ONLY when the goal is within reach of the boost (goal-in-sight) and
            the base is spent. The "second wind": spend the costly reserve surgically,
            never on the hopeless. Conserves mass -> survives -> completes the most.

The GATED = ALWAYS difference is exactly Jonathan's "boost when the goal is just
ahead": both can finish a reachable task; only gating withholds the reserve when the
goal is out of reach, which is what keeps the mass alive.
"""
import numpy as np
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

# ---- units: pace 1 dist/step, net drain 1 tank/step  => base reach (dist) = R0 ----
R0_FULL = 10.0          # base tank -> base reach 10
G       = 6.0           # golden-field reserve -> extra reach 6  (total reach 16)
SURGE   = 1.30          # adrenaline pace multiplier while the reserve burns
M0      = 100.0         # structural mass the reserve is drawn from
C_FIRE  = 8.0           # mass cost to fire the reserve once (the damage)
M_REC   = 3.0           # mass recovered per task (rest / fluid coming back in)
# effective base reach couples to mass: starve the mass and the tank itself shrinks
def base_reach(M): return R0_FULL * (0.40 + 0.60*np.clip(M/M0, 0, 1))

# ---------------------------------------------------------------------------
# (1) ONE hard-but-reachable task, step by step -> the second-wind trajectory
# ---------------------------------------------------------------------------
def trajectory(D, use_reserve, M=M0, dt=1.0):
    Lb = base_reach(M); pos = 0.0; t = 0.0; xs=[0.0]; ts=[0.0]; fired=None
    # phase 1: base budget, pace 1, until base reach is spent
    while pos < min(Lb, D):
        pos += 1.0*dt; t += dt; xs.append(pos); ts.append(t)
    if pos >= D:                                   # finished on base alone
        return np.array(ts), np.array(xs), None, True
    if not use_reserve or D > Lb + G:              # base spent, no (usable) reserve
        return np.array(ts), np.array(xs), None, False
    # phase 2: GOAL IN SIGHT -> golden-field reserve fires, surge pace (the boost)
    fired = pos
    while pos < D:
        pos += SURGE*dt; t += dt; xs.append(pos); ts.append(t)
    return np.array(ts), np.array(xs), fired, True

D_hard = 13.0                                       # > base reach 10, <= 16 => reachable only with the boost
tb, xb, _, okb   = trajectory(D_hard, use_reserve=False)
tg, xg, fg, okg  = trajectory(D_hard, use_reserve=True)
# extend the burnt-out one-budget run as a flat "gave up" plateau to the same end-time
if tg[-1] > tb[-1]:
    tb = np.append(tb, tg[-1]); xb = np.append(xb, xb[-1])

# ---------------------------------------------------------------------------
# (2) a long STREAM of tasks -> which policy completes the most / survives
# ---------------------------------------------------------------------------
def run_stream(policy, n=200, seed=0):
    rng = np.random.default_rng(seed)
    M = M0; done = 0; wasted = 0; Ms=[]; cum=[]; reach=[]
    for i in range(n):
        D = rng.uniform(2.0, 20.0)                  # easy <10 / hard 10-16 / hopeless >16
        Lb = base_reach(M)
        if D <= Lb:
            done += 1                               # base budget finishes it
        else:
            fire = (policy == "always") or (policy == "gated" and D <= Lb + G)
            if fire:
                M -= C_FIRE                          # spend the reserve = damage the mass
                if D <= Lb + G: done += 1
                else:           wasted += 1          # fired but still failed (hopeless)
        M = min(M0, M + M_REC)                       # rest: fluid comes back (capped)
        M = max(0.0, M)
        Ms.append(M); cum.append(done); reach.append(base_reach(M))
    return dict(policy=policy, done=done, wasted=wasted,
                M=np.array(Ms), cum=np.array(cum), reach=np.array(reach))

res = {p: run_stream(p) for p in ("none", "always", "gated")}

print("="*72)
print("  THE GOLDEN-FIELD RESERVE: why one budget can't be intelligent")
print("="*72)
print(f"  base reach {R0_FULL:.0f}  |  reserve +{G:.0f} (total {R0_FULL+G:.0f})  |  mass {M0:.0f},"
      f" fire cost {C_FIRE:.0f}, recovery {M_REC:.0f}/task")
print()
print(f"  one hard task (goal at {D_hard:.0f}, beyond base reach {R0_FULL:.0f}):")
print(f"    base budget only : reaches {xb[-1]:.1f}  -> {'GOAL' if okb else 'BURNS OUT short'}")
print(f"    golden field     : reaches {xg[-1]:.1f}  -> {'GOAL (second wind)' if okg else 'short'}"
      f"   (reserve fired at {fg:.0f})")
print()
print(f"  over a stream of 200 mixed tasks:")
print(f"  {'policy':8}{'completed':>12}{'wasted fires':>14}{'final base reach':>18}{'final mass':>12}")
for p in ("none", "always", "gated"):
    r = res[p]
    print(f"  {p:8}{r['done']:>12}{r['wasted']:>14}{r['reach'][-1]:>18.1f}{r['M'][-1]:>12.1f}")
print()
print(f"  -> ONE budget (none) burns out at a fixed reach and misses every hard task"
      f" ({res['none']['done']}/200).")
print(f"  -> ALWAYS-on adrenaline finishes hard tasks but spends mass on {res['always']['wasted']} HOPELESS")
print(f"     ones too; the mass breaks down and base reach collapses to"
      f" {res['always']['reach'][-1]:.1f} -> only {res['always']['done']}/200.")
print(f"  -> GATED (fire only when the goal is in reach) spends the reserve surgically,")
print(f"     keeps the mass alive, and completes the most: {res['gated']['done']}/200. The gating IS")
print(f"     the 'boost when the goal is just ahead' -- and it's what one budget cannot do.")

# ---------------------------------------------------------------------------
# PLOT
# ---------------------------------------------------------------------------
fig, (axL, axR) = plt.subplots(1, 2, figsize=(13.4, 5.4))

axL.axhline(D_hard, color="#c0392b", ls="--", lw=1.3, label=f"the goal (distance {D_hard:.0f})")
axL.axhline(R0_FULL, color="#999", ls=":", lw=1.1)
axL.text(0.3, R0_FULL+0.15, "base reach (burn-out line)", color="#777", fontsize=8.5)
axL.plot(tb, xb, color="#e6820a", lw=2.4, label="one budget → burns out short, gives up")
axL.plot(tg, xg, color="#238b45", lw=2.4, label="golden field → second wind over the line")
if fg is not None:
    axL.scatter([tg[np.argmin(np.abs(xg-fg))]], [fg], s=70, color="#238b45", zorder=5)
    axL.annotate("goal in sight →\nreserve fires (surge)", (tg[np.argmin(np.abs(xg-fg))], fg),
                 xytext=(1.0, 6.2), fontsize=8.5, color="#238b45",
                 arrowprops=dict(arrowstyle="->", color="#238b45"))
axL.set_xlabel("time (steps)"); axL.set_ylabel("distance covered")
axL.set_title("Second wind: base burns out short; the reserve fires\nonly once the goal is in sight, and carries it over")
axL.legend(loc="lower right", fontsize=8.3, framealpha=0.93)

ax2 = axR.twinx()
for p, col in (("none","#8e44ad"), ("always","#e6820a"), ("gated","#238b45")):
    axR.plot(res[p]['cum'], color=col, lw=2.2, label=f"{p}: {res[p]['done']} done")
ax2.plot(res['always']['M'], color="#e6820a", lw=1.0, ls=":", alpha=0.7)
ax2.plot(res['gated']['M'],  color="#238b45", lw=1.0, ls=":", alpha=0.7)
ax2.set_ylabel("structural mass (dotted)", color="#666"); ax2.set_ylim(0, M0*1.05)
axR.set_xlabel("task number (stream)"); axR.set_ylabel("cumulative tasks completed")
axR.set_title("Over a long run: always-on burns the mass down and stalls;\ngated spends the reserve surgically and completes the most")
axR.legend(loc="upper left", fontsize=8.5, framealpha=0.93)

fig.tight_layout(); fig.savefig("second_wind.png", dpi=130)
print("\n  wrote second_wind.png")
