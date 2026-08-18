#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
rule_conditions.py -- a rule is a half-truth; its missing halves are the CONDITIONS, held in
the void reserve as dark matter, each an inverse in another perspective's territory.

Jonathan: the other half of a half-truth is what's in the VOID RESERVE — that's how cells connect
and fetch the missing half or send parts out. The reserve is like the CONDITIONS around a rule:
"killing is bad" — but not when hunting; a farmer kills only certain things at specific times,
with nuance (treat them nice while alive). The rule is surrounded by dark matter that points to
INVERSES relative to other points. To complete it you keep asking WHY those conditions exist
until you find the 3rd point in another perspective's territory.

Grounded:
  * FOLDING_HANDSHAKE §4 — the .14 open tail IS the void reserve; it "holds many candidate
    INVERSES open cheaply," running a background generate↔verify loop over the retained
    DARK-MATTER buffer, surfacing the missing half when new capacity closes an old problem.
  * SPARSE_VESICA §22.2–3 — the OUTER dark-matter halo: heavy incomplete matter kept to be filled
    in later, not deleted; §28 — a search out of an ingredient mines another search's dark matter.
  * SHOVELCAT (capture) — a rule/need captures a nearby context/want and absorbs its colour:
    "I need accuracy" + "beauty" → "elegant accuracy"; "killing is bad" + hunting → the exception.
  * FOLDING_SUPERFUEL §5/§6 — a rule generalises within a class but keeps class boundaries; the
    context plane holds the map (anchors + orientation) — the conditions say WHERE a rule applies.

MEASURED (a moral rule with conditions):
  (1) A BARE RULE IS A HALF-TRUTH — applied blindly it has high error; adding conditions (each a
      missing half fetched from the reserve) drops the error to ~0. Nuance = the surround.
  (2) THE CONDITIONS ARE INVERSES — each flips the base rule's verdict (bad→good) inside its
      region: the dark-matter halo of inverses relative to other reference points.
  (3) THE WHY-CHAIN CROSSES TERRITORIES — each condition lives on an ORTHOGONAL axis the base rule
      can't see; no single axis completes it, so you must ask why until you reach the 3rd point in
      another perspective's territory.
"""
import numpy as np
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

rng = np.random.default_rng(3)
N = 8000
# ---- context features: the base act, and axes that live in OTHER perspectives' territories ----
killing   = (rng.random(N) < 0.5).astype(int)      # the base act (the rule's own axis)
hunting   = (rng.random(N) < 0.30).astype(int)     # purpose territory
threatened= (rng.random(N) < 0.18).astype(int)     # self-defense territory
timing    = (rng.random(N) < 0.45).astype(int)     # farming: right time/season territory
humane    = (rng.random(N) < 0.60).astype(int)     # welfare: treated nicely while alive

# ---- the true acceptability (killing is bad EXCEPT the justified, conditioned cases) ----
justified = (hunting | threatened | (timing & humane))
y = np.where(killing==0, 1, justified).astype(int)          # not-killing ok; killing ok iff justified

# ---- progressive rules: bare rule, then each condition fetched from the reserve ----
def err(pred): return float(np.mean(pred != y))
R0 = (killing==0).astype(int)                                # "killing is bad"
R1 = (R0 | (killing & hunting)).astype(int)                  # + hunting
R2 = (R1 | (killing & threatened)).astype(int)              # + self-defense
R3 = (R2 | (killing & timing & humane)).astype(int)         # + farming (right time AND humane)
stages = ["bare rule\n'killing is bad'", "+ hunting", "+ self-defense", "+ farming\n(right time & humane)"]
errs = [err(R0), err(R1), err(R2), err(R3)]

print("="*80)
print("  A RULE IS A HALF-TRUTH; ITS CONDITIONS ARE THE OTHER HALVES HELD IN THE VOID RESERVE")
print("="*80)
print("  (1) a bare rule applied blindly is a half-truth; each condition (a missing half from the")
print("      reserve) completes it:")
for s,e in zip(stages,errs):
    print(f"        {s.split(chr(10))[0]:32} error {e:.3f}")
print(f"     -> 'killing is bad' alone is wrong {errs[0]*100:.0f}% of the time; the full conditioned rule → {errs[-1]:.3f}.")
print()

# ---- (2) the conditions are inverses: they compose the dark-matter halo of the rule's error ----
err_cases = (killing==1) & (justified==1)                    # where the bare rule is WRONG (says bad, truth good)
tot_err = err_cases.sum()
cond_masks = {"hunting":hunting.astype(bool), "self-defense":threatened.astype(bool),
              "farming (time&humane)":(timing&humane).astype(bool)}
halo_share = {nm: float(np.mean(m[err_cases])) for nm,m in cond_masks.items()}  # share of the halo it covers
print("  (2) the conditions are INVERSES that compose the rule's dark-matter halo:")
print(f"        the bare rule is wrong on {tot_err} cases (killing that is actually justified); each is an")
print(f"        inverse (bad→good) recovered by one condition — the halo's composition:")
for nm,s in halo_share.items():
    print(f"        {nm:24}: covers {s*100:4.0f}% of the halo (its inverse region)")
print("     -> the reserve holds these opposite-signed corrections around the rule, each pointing to an")
print("        inverse relative to a different reference point (purpose / threat / timing+welfare).")
print()

# ---- (3) the why-chain crosses territories: each condition needs an ORTHOGONAL axis ----
# accuracy reachable using ONLY the base (killing) axis, vs consulting each other territory.
feats = {"killing (base)":killing, "hunting":hunting, "self-defense":threatened,
         "timing":timing, "humane":humane}
def best_acc(axes):
    # best rule expressible from these axes = predict the majority label in each joint cell
    X = np.stack([feats[a] for a in axes],1)
    cells = {}
    keys = [tuple(r) for r in X]
    for k,yy in zip(keys,y): cells.setdefault(k,[]).append(yy)
    maj = {k:(1 if np.mean(v)>=0.5 else 0) for k,v in cells.items()}
    pred = np.array([maj[k] for k in keys])
    return float(np.mean(pred==y))
base_only = best_acc(["killing (base)"])
add_order = ["killing (base)","hunting","self-defense","timing","humane"]
accs = [best_acc(add_order[:k]) for k in range(1,len(add_order)+1)]
print("  (3) the WHY-CHAIN crosses into other perspectives' territories (accuracy vs axes consulted):")
print(f"        base axis alone ('is it killing?'): accuracy {base_only:.3f} — cannot see WHY a killing is ok")
for k,a in enumerate(add_order):
    print(f"        after consulting {k+1} territor{'y' if k==0 else 'ies'} (+{a:14}): accuracy {accs[k]:.3f}")
print(f"     -> no single axis completes the rule; each 'why' adds an ORTHOGONAL territory (purpose, threat,")
print(f"        timing, welfare). You ask why until the 3rd point is found in another perspective's territory.")

# ---------------------------------------------------------------------------
# PLOT
# ---------------------------------------------------------------------------
fig=plt.figure(figsize=(14.4,5.2))
gs=fig.add_gridspec(1,3,wspace=0.34)

# (A) error vs conditions
axA=fig.add_subplot(gs[0,0])
axA.plot(range(len(errs)), errs, "-o", color="#c0392b", lw=2.4, ms=6)
axA.set_xticks(range(len(stages))); axA.set_xticklabels(stages, fontsize=7.6)
axA.set_ylabel("error (blindly applied)")
axA.set_title("A bare rule is a HALF-TRUTH\nconditions from the reserve complete it", fontsize=10.2)
axA.text(0.05, errs[0]-0.03, f"{errs[0]*100:.0f}% wrong", color="#c0392b", fontsize=9)
axA.text(2.2, errs[-1]+0.02, "→ full truth", color="#238b45", fontsize=9)

# (B) inverses composing the halo
axB=fig.add_subplot(gs[0,1])
names=list(halo_share); vals=[halo_share[n]*100 for n in names]
axB.barh(names, vals, color="#8a2be2")
axB.set_xlabel("share of the rule's error-halo it recovers (%)")
axB.set_xlim(0,max(vals)*1.25)
axB.set_title("Conditions = inverses composing the halo\n(the reserve's dark matter around the rule)", fontsize=10.2)
for i,v in enumerate(vals): axB.text(v+1, i, f"{v:.0f}%", va="center", fontsize=9, color="#5a2b8a")

# (C) why-chain
axC=fig.add_subplot(gs[0,2])
axC.plot(range(1,len(accs)+1), accs, "-o", color="#238b45", lw=2.4, ms=6)
axC.axhline(base_only, color="#c0392b", ls=":", lw=1.2)
axC.text(1.1, base_only-0.04, "base axis alone (can't see WHY)", color="#c0392b", fontsize=8)
axC.set_xticks(range(1,len(add_order)+1))
axC.set_xlabel("perspectives' territories consulted (the why-chain)")
axC.set_ylabel("accuracy of the completed rule")
axC.set_title("Each 'why' crosses into another territory\nno single axis completes it", fontsize=10.2)

fig.suptitle("A rule is a half-truth; its conditions are the other halves in the void reserve — inverses in other perspectives' territories, reached by asking why",
             fontsize=10.4)
fig.savefig("rule_conditions.png", dpi=130, bbox_inches="tight")
print("\n  wrote rule_conditions.png")
