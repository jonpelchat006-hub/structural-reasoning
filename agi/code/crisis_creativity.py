#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
crisis_creativity.py -- the weird move: crisis energy crosses the rule-border.

Jonathan's third face of the golden field: the mass reacting (denaturing) creates a
HIGH-ENERGY environment, and in that environment a NEW reaction can happen that
couldn't at rest -- "an explosion in the chamber." The void line pumps in new context
on the orthogonal plane while the normal plane carries matter, so under those
conditions you ADD NEW CONTEXT TO OBJECTS -- and that's where weird ideas come from.
The leak-on-the-ship case: a leftover *sail* (an object in its normal role) gets
"repair" attached and is repurposed into a *plug* -- barely slowing the leak enough
to reach the goal. "The mass was made of rules, so the sail has borders/barriers in
it" -- and using it out of role is BENDING one of those rules.

This has an exact formal name. Shovelcat_29 §9 (Fire Economy): Fire = high-energy
excitation igniting from Fuel (unresolved problems) + Heat (activation energy); the
Fire threshold is |dθ/dt| ≈ √π (the same border a fiber tears at); and "Fire cooling
-> structure" crystallises the burst into new Ground. That is SIMULATED ANNEALING: a
crisis heat-spike lets the search cross an energy barrier (the rule-border) that is
impassable at rest, then cooling locks in the new configuration.

THE LANDSCAPE (energy = leak rate to minimise; survive if leak < threshold)
  * MANUAL basin (x≈0.15): parts used in-role. A local min, but leak 0.55 > 0.40 --
    the manual fix does NOT clear survival. You sink.
  * BARRIER (x≈0.5): the rule-border. Repurposing is temporarily WORSE (the sail is
    off its mast, not yet a plug) -- an energy hump you must cross.
  * CREATIVE basin (x≈0.85): sail+repair, repurposed as a plug. Global min, leak 0.25
    < 0.40 -- survives / reaches the goal, barely.

Three temperature policies, many seeds:
  COLD   -- rigid, never bends a rule (T low). Rolls into the manual basin, stuck, sinks.
  HOT    -- always chaotic (T high). Crosses freely but never SETTLES -- imprecise,
            unreliable, no crystallised fix.
  CRISIS -- exploit cold; when STUCK in the manual basin AND still sinking (crisis),
            spike T (the denaturing burst), cross the border, then COOL into the
            creative basin. Fire -> cooling -> new structure.
"""
import numpy as np
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

SURVIVE = 0.40      # leak below this = reach the goal / stay afloat
def E(x):           # the leak landscape
    x = np.asarray(x, float)
    return (1.0
            - 0.45*np.exp(-((x-0.15)/0.08)**2)     # manual well  -> Em = 0.55 (sinks)
            - 0.75*np.exp(-((x-0.85)/0.08)**2)     # creative well-> Ec = 0.25 (survives)
            + 0.25*np.exp(-((x-0.50)/0.10)**2))    # the rule-border barrier

def metropolis_step(x, T, rng, step=0.05):
    xp = np.clip(x + rng.normal(0, step), 0.0, 1.0)
    dE = E(xp) - E(x)
    if dE < 0 or rng.random() < np.exp(-dE/max(T,1e-9)):
        return xp
    return x

def run(policy, rng, n=1600):
    x = np.clip(0.15 + rng.normal(0,0.02), 0, 1)   # start at the manual fix
    xs=[x]; Ts=[]; stuck=0
    for t in range(n):
        if policy == "cold":
            T = 0.02
        elif policy == "hot":
            T = 0.45
        else:  # crisis: exploit cold, spike when stuck AND still sinking
            crisis = (E(x) > SURVIVE) and (x < 0.45)       # in the manual basin, still leaking
            if crisis:
                stuck += 1
            else:
                stuck = max(0, stuck-2)
            if stuck > 40:                                  # the burst: denature -> Heat
                T = 0.9                                     # high-energy excitation (Fire)
                if stuck > 80: stuck = 0                    # burst spends itself
            else:
                T = 0.02 + 0.10*np.exp(-t/500)              # otherwise cool / exploit
        Ts.append(T)
        x = metropolis_step(x, T, rng)
        xs.append(x)
    return np.array(xs), np.array(Ts)

SEEDS = 240
def survey(policy):
    finalE=[]; creative=0; survived=0
    for s in range(SEEDS):
        rng = np.random.default_rng(1000+s)
        xs,_ = run(policy, rng)
        xf = np.median(xs[-50:])                            # where it settled
        ef = float(E(xf))
        finalE.append(ef)
        creative += (xf > 0.6)
        survived += (ef < SURVIVE)
    return dict(policy=policy, meanE=float(np.mean(finalE)),
                creative=creative, survived=survived)

res = {p: survey(p) for p in ("cold","hot","crisis")}

print("="*72)
print("  CRISIS CREATIVITY: high-energy fire crosses the rule-border (annealing)")
print("="*72)
print(f"  leak landscape: manual fix {E(0.15):.2f} (SINKS, >{SURVIVE}); creative fix {E(0.85):.2f}"
      f" (survives); border hump {E(0.5):.2f}")
print()
print(f"  {'policy':8}{'mean final leak':>18}{'reached creative':>18}{'survived':>12}")
for p in ("cold","hot","crisis"):
    r = res[p]
    print(f"  {p:8}{r['meanE']:>18.3f}{str(r['creative'])+'/'+str(SEEDS):>18}"
          f"{str(r['survived'])+'/'+str(SEEDS):>12}")
print()
print(f"  -> COLD never bends a rule: it rolls into the manual fix and stays there --")
print(f"     leak {res['cold']['meanE']:.2f} > {SURVIVE}, it sinks ({res['cold']['survived']}/{SEEDS} survive).")
print(f"  -> HOT is always chaotic: it crosses the border but never SETTLES into the fix")
print(f"     -- imprecise, only {res['hot']['survived']}/{SEEDS} survive, mean leak {res['hot']['meanE']:.2f}.")
print(f"  -> CRISIS spikes the heat only when stuck-and-sinking, crosses the rule-border,")
print(f"     then COOLS into the creative fix: {res['crisis']['survived']}/{SEEDS} survive, leak"
      f" {res['crisis']['meanE']:.2f}.")
print(f"     Fire -> cooling -> new structure: the repurposed sail+repair, crystallised.")

# ---- one illustrative crisis run trajectory (energy + temperature) ----
rng = np.random.default_rng(7)
xs, Ts = run("crisis", rng)
Es = E(xs)
xc, Tc = run("cold", np.random.default_rng(7))
Ec = E(xc)

# ---------------------------------------------------------------------------
# PLOT: left = the leak landscape with the two basins + the border; right = the
# crisis run crossing the border (energy) with the heat-spike (temperature).
# ---------------------------------------------------------------------------
fig, (axL, axR) = plt.subplots(1, 2, figsize=(13.4, 5.3))

xx = np.linspace(0,1,400)
axL.plot(xx, E(xx), color="#111", lw=2.2)
axL.axhline(SURVIVE, color="#c0392b", ls="--", lw=1.2)
axL.text(0.02, SURVIVE+0.01, "survive line (reach the goal)", color="#c0392b", fontsize=8.5)
axL.scatter([0.15],[E(0.15)], s=80, color="#e6820a", zorder=5)
axL.annotate("manual: sail in role\n(sinks)", (0.15,E(0.15)), xytext=(0.02,0.30),
             fontsize=8.5, color="#e6820a", arrowprops=dict(arrowstyle="->",color="#e6820a"))
axL.scatter([0.85],[E(0.85)], s=80, color="#238b45", zorder=5)
axL.annotate("creative: sail+repair\nrepurposed (survives)", (0.85,E(0.85)), xytext=(0.55,0.12),
             fontsize=8.5, color="#238b45", arrowprops=dict(arrowstyle="->",color="#238b45"))
axL.annotate("the rule-border\n(√π: bend to cross)", (0.5,E(0.5)), xytext=(0.30,0.92),
             fontsize=8.5, color="#555", arrowprops=dict(arrowstyle="->",color="#555"))
axL.set_xlabel("x  =  how far from the in-role rule (0 = manual, 1 = repurposed)")
axL.set_ylabel("leak rate  (energy to minimise)")
axL.set_title("The fix that survives is behind the rule-border\ncold search can't reach it; crisis fire can")

ax2 = axR.twinx()
axR.plot(Es, color="#238b45", lw=2.0, label="crisis: leak over time")
axR.plot(Ec, color="#e6820a", lw=1.6, ls="--", label="cold: stuck at manual (sinks)")
axR.axhline(SURVIVE, color="#c0392b", ls="--", lw=1.0)
ax2.plot(Ts, color="#9467bd", lw=1.0, alpha=0.6)
ax2.set_ylabel("temperature (Fire / heat)", color="#7a5aa0"); ax2.set_ylim(0, 1.0)
axR.text(0, 0.02, "purple = temperature (the crisis heat-spike)", color="#7a5aa0", fontsize=8)
axR.set_xlabel("search step"); axR.set_ylabel("leak rate")
axR.set_title("The heat-spike crosses the border, then cooling\nlocks in the creative fix (Fire → cooling → structure)")
axR.legend(loc="center right", fontsize=8.5, framealpha=0.93)

fig.tight_layout(); fig.savefig("crisis_creativity.png", dpi=130)
print("\n  wrote crisis_creativity.png")
