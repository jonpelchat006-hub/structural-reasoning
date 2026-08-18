#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ship_repair.py -- the golden field as SURVIVAL: sail+patch, and the patch is made
of your own unfolded mass, available only when the tank dries.

Jonathan's correction & extension to Test 10:
  * the reserve doesn't only fire when the goal is in sight -- it's meant to KEEP
    THINGS ALIVE. The trigger is survival, not just goal-proximity.
  * the mass is made of its own stuff WITH FOLDS; when the fluid runs out and the
    environment changes it starts UNFOLDING / reacting -> it releases its parts
    (denaturing = autophagy: eat your own folded mass to make an emergency repair).
  * the golden field is attached to the VOID LINES, which send a DIFFERENT kind of
    material, through both planes -- so the crisis delivers a patch, not more sail.
  * combined it looks like object+context = SAIL+PATCH. To patch the ship you need
    sail+patch, and the patch is only available at the golden field; the rest of the
    time it's just a sail.

Grounding: SPHERE_GENERATOR J.4 (the exploratory-blind golden move, fired only when
no normal anchor works); FOLDING_TWO_CHANNEL_LOOP (two channels/planes, matter + the
return leg); Shovelcat_29 4.8 (slack e->0 -> the structure denatures/collapses);
SPARSE_VESICA 28.1-28.3 (mass is conserved; bonded folds recoverable only by a
DECOMPOSITION step at a cost = unfolding). Test 8: object+context seals the shape.

THE SETUP
---------
A hull takes a stream of damage. Two kinds of breach:
  * STANDARD (shape 0): a sail piece fits -> patched for free from the normal vocab.
  * NOVEL   (odd tear): NO sail fits. The manual has no move. Surviving it needs
    sail + PATCH, where the patch is the missing complement -- assembled only by
    UNFOLDING a stored fold (autophagy), costing permanent mass, and only unlockable
    in crisis (folds are locked = structural = "just a sail" the rest of the time).

Three policies, same damage stream:
  SAIL_ONLY   -- normal vocabulary only. Dies at the first novel tear it can't patch.
  AUTO_ALWAYS -- unfold a fold to patch EVERY breach (even standard ones a sail would
                 fix). Burns its own mass wastefully -> runs out -> dies.
  GOLDEN_GATED-- sail the standard breaches for free; unfold a fold ONLY for a novel
                 tear that would otherwise be fatal (survival-gated). Spends mass
                 surgically -> survives the longest.
"""
import numpy as np
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

I0     = 100.0     # hull integrity
DMG    = 14.0      # damage from an unpatched breach
HEAL   = 3.0       # slow self-repair per event when not freshly breached
F0     = 18        # stored folds (the mass reservoir you can unfold for patches)
FREGEN = 0.10      # folds slowly re-fold when rested (fluid coming back)
P_NOVEL= 0.40      # fraction of breaches that are novel tears (no sail fits)
N      = 140       # events in the damage stream

def stream(seed=0):
    rng = np.random.default_rng(seed)
    novel = rng.random(N) < P_NOVEL          # True = odd tear needing sail+patch
    return novel

FLOOR = 0.45*I0                                            # the "keep alive" danger line

def simulate(policy, novel):
    I = I0; folds = float(F0); alive = True
    Itrace=[]; Ftrace=[]; died=None; unfolds=0; wasted=0
    for t in range(N):
        breach_novel = novel[t]
        took_damage = False
        if not breach_novel:
            # STANDARD breach: a sail fits for free -- unless the policy wastes a fold.
            if policy == "auto_always" and folds >= 1:
                folds -= 1; unfolds += 1; wasted += 1     # wasteful: unfolded where a sail would do
        else:
            # NOVEL tear: no sail fits. Only sail+patch survives it, and the patch
            # costs one unfolded fold (autophagy).
            if policy == "sail_only":
                I -= DMG; took_damage = True              # no move -> bleed
            elif policy == "auto_always":
                if folds >= 1: folds -= 1; unfolds += 1   # unfold on every tear
                else:          I -= DMG; took_damage = True
            elif policy == "golden_gated":
                threatens = (I - DMG) <= FLOOR            # would THIS tear push us into danger?
                if threatens and folds >= 1:
                    folds -= 1; unfolds += 1              # spend mass ONLY to stay alive
                else:
                    I -= DMG; took_damage = True          # healthy enough to tank it -> save the mass
        if not took_damage:
            I = min(I0, I + HEAL)
        folds = min(F0, folds + FREGEN)                    # slow re-folding (rest / fluid returning)
        if I <= 0 and alive:
            alive = False; died = t
        Itrace.append(max(I,0)); Ftrace.append(folds)
        if not alive:
            Itrace += [0]*(N-1-t); Ftrace += [folds]*(N-1-t); break
    survived = died if died is not None else N
    return dict(policy=policy, I=np.array(Itrace[:N]), F=np.array(Ftrace[:N]),
                survived=survived, unfolds=unfolds, wasted=wasted, alive=alive)

novel = stream(0)
res = {p: simulate(p, novel) for p in ("sail_only","auto_always","golden_gated")}

n_novel = int(novel.sum())
print("="*72)
print("  SAIL + PATCH: the golden field as survival (autophagy through the void line)")
print("="*72)
print(f"  {N} damage events, {n_novel} novel tears (no sail fits) | hull {I0:.0f}, tear damage {DMG:.0f}")
print(f"  stored folds {F0} (unfold 1 = one sail+patch), slow re-fold {FREGEN}/event")
print()
print(f"  {'policy':13}{'survived (events)':>18}{'unfolds':>10}{'wasted':>9}{'end hull':>10}")
for p in ("sail_only","auto_always","golden_gated"):
    r = res[p]
    surv = f"{r['survived']}" + ("" if r['alive'] else "  DIED")
    end = "alive" if r['alive'] else "0"
    print(f"  {p:13}{surv:>18}{r['unfolds']:>10}{r['wasted']:>9}{end:>10}")
print()
print(f"  -> SAIL_ONLY has no move for a novel tear -- it bleeds out and DIES at event"
      f" {res['sail_only']['survived']}.")
print(f"  -> AUTO_ALWAYS unfolds for every breach incl. {res['auto_always']['wasted']} it could have sailed;"
      f" it eats")
print(f"     its own mass wastefully and dies at event {res['auto_always']['survived']}.")
gg = res['golden_gated']
print(f"  -> GOLDEN_GATED sails the standard breaches free and unfolds ONLY to survive a")
print(f"     fatal tear -- sail+patch, mass spent surgically -- lasting to"
      f" {'the end (alive)' if gg['alive'] else 'event '+str(gg['survived'])}.")
print(f"     The patch is a DIFFERENT piece (unfolded mass via the void line), unlocked only")
print(f"     in crisis; the rest of the time the fold is just a sail.")

# ---------------------------------------------------------------------------
# PLOT: left = hull integrity over the stream; right = fold reservoir (the mass)
# ---------------------------------------------------------------------------
fig, (axL, axR) = plt.subplots(1, 2, figsize=(13.4, 5.3))
col = {"sail_only":"#c0392b", "auto_always":"#e6820a", "golden_gated":"#238b45"}
lab = {"sail_only":"sail only (no patch move)",
       "auto_always":"always unfold (wastes its own mass)",
       "golden_gated":"golden field: sail+patch, crisis-gated"}

# mark novel tears along the bottom
for t in np.where(novel)[0]:
    axL.axvline(t, color="#ddd", lw=0.6, zorder=0)
for p in ("sail_only","auto_always","golden_gated"):
    r = res[p]
    axL.plot(r['I'], color=col[p], lw=2.3, label=lab[p])
    if not r['alive']:
        axL.scatter([r['survived']], [0], color=col[p], marker="x", s=70, zorder=5)
axL.axhline(0.45*I0, color="#888", ls=":", lw=1.0)
axL.text(1, 0.45*I0+1.5, "crisis line (survival trigger)", color="#777", fontsize=8)
axL.set_xlabel("damage event"); axL.set_ylabel("hull integrity")
axL.set_title("Hull over a stream of damage (thin lines = novel tears)\nsail-only bleeds out; gated sail+patch survives")
axL.legend(loc="upper right", fontsize=8.3, framealpha=0.93); axL.set_ylim(-4, I0+5)

for p in ("auto_always","golden_gated"):
    axR.plot(res[p]['F'], color=col[p], lw=2.3, label=lab[p])
axR.axhline(0, color="#ccc", lw=0.8)
axR.set_xlabel("damage event"); axR.set_ylabel("stored folds (the mass you can unfold)")
axR.set_title("The mass is finite: unfolding is eating yourself\nalways-unfold burns out; gated spends it only to stay alive")
axR.legend(loc="upper right", fontsize=8.3, framealpha=0.93); axR.set_ylim(-0.5, F0+1)

fig.tight_layout(); fig.savefig("ship_repair.png", dpi=130)
print("\n  wrote ship_repair.png")
