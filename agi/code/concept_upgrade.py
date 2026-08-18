#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
concept_upgrade.py -- the sail's term upgrades (movement -> block), enabling transfer.

Jonathan: the sail starts as "cloth + perpendicular + MOVEMENT" -- it was only ever used
to block the wind FOR movement. After a crisis the MOVEMENT term upgrades to BLOCK: a
more general term where "block wind -> movement" is one special case, and now "block
water coming in" is another. So the same sail transfers to a NEW goal (stay afloat) it
was never trained for -- without over-claiming (it still can't block a rockfall; wrong
class). That is abstraction / generalization: burning the specific context term and
minting a more general parent (SPHERE_GENERATOR C.2, pointed upward).

MEASURED CLAIM
--------------
A tool is seen only in its CANONICAL use (sail demonstrated blocking AIR). Two ways to
represent what it learned:

  SPECIFIC -- the tool works on goals whose medium is EXACTLY the demonstrated one (air).
              Ties the tool to the exact context it was seen in. Cannot transfer.
  UPGRADE  -- generalize the demonstrated medium to its learned CLASS (air -> the fluid
              cluster, discovered unsupervised from the media's own feature space). The
              tool works on any medium in that class. Transfers to water (a fluid) but
              NOT to rock (a solid) -- generalize the term, keep the class boundary.

We measure, on NOVEL (tool, goal) pairs (never the tool's canonical goal):
  * TRANSFER RECALL  -- of the pairs the tool truly solves, how many are caught.
  * FALSE-POSITIVE   -- of the pairs it truly does NOT solve, how many are wrongly claimed
                        (guards against "generalize = say yes to everything").

Ground truth: tool T solves goal G iff T.operation == G.required_op AND
class(G.medium) == class(T.demonstrated_medium). The operation generalizes WITHIN a
medium class (block works on any fluid), not across (block a fluid ≠ block a solid).
"""
import numpy as np
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

# ---- media live in a 2-D feature space; their CLASS is a cluster we must discover ----
media = {
    "air":   (0.20, 0.80), "water": (0.34, 0.70), "steam": (0.16, 0.64),   # fluids
    "rock":  (0.82, 0.22), "sand":  (0.90, 0.28),                          # solids
    "light": (0.85, 0.86),                                                 # radiation
}
mnames = list(media); MF = np.array([media[m] for m in mnames])

def cluster_media(MF, thresh=0.28):
    """Unsupervised: single-link threshold clustering over the media feature space.
    This is the 'learned class' the upgrade generalizes to -- not given labels."""
    n = len(MF); lab = list(range(n))
    for i in range(n):
        for j in range(i+1, n):
            if np.hypot(*(MF[i]-MF[j])) < thresh:
                old, new = lab[j], lab[i]
                lab = [new if x == old else x for x in lab]
    # relabel 0..k-1
    remap = {c: k for k, c in enumerate(sorted(set(lab)))}
    return np.array([remap[x] for x in lab])

clab = cluster_media(MF)
cluster_of = {m: int(clab[i]) for i, m in enumerate(mnames)}

# ---- tools: an operation + the ONE medium each was demonstrated on ----
tools = {
    "sail":  dict(op="block", demo="air"),    # cloth+perpendicular+(block air -> movement)
    "wall":  dict(op="block", demo="rock"),   # blocks a solid (rockfall)
    "pump":  dict(op="move",  demo="water"),
    "lamp":  dict(op="emit",  demo="light"),
    "blade": dict(op="cut",   demo="rock"),
}
# ---- goals: a required operation + a target medium ----
goals = {
    "reach_dest":   dict(op="block", medium="air"),    # sail's canonical use
    "stay_afloat":  dict(op="block", medium="water"),  # <-- the transfer target
    "harness_steam":dict(op="block", medium="steam"),  # <-- also a transfer target
    "shelter":      dict(op="block", medium="rock"),   # wall's canonical (sail must REFUSE)
    "dam_sand":     dict(op="block", medium="sand"),   # solid (sail must refuse)
    "illuminate":   dict(op="emit",  medium="light"),  # lamp's canonical
    "bilge":        dict(op="move",  medium="water"),  # pump's canonical
    "carve":        dict(op="cut",   medium="rock"),   # blade's canonical
}

def truth(t, g):
    T, G = tools[t], goals[g]
    return int(T["op"] == G["op"] and cluster_of[T["demo"]] == cluster_of[G["medium"]])

# each tool's canonical goal (the one it was demonstrated on)
canonical = {t: next(g for g in goals
                     if goals[g]["op"] == tools[t]["op"] and goals[g]["medium"] == tools[t]["demo"])
             for t in tools}

def predict(t, g, mode):
    T, G = tools[t], goals[g]
    if T["op"] != G["op"]:
        return 0                                     # operation must match (both know this)
    if mode == "specific":
        return int(G["medium"] == T["demo"])         # exact medium only
    else:  # upgrade: generalize demonstrated medium to its learned class
        return int(cluster_of[G["medium"]] == cluster_of[T["demo"]])

# ---- evaluate on NOVEL pairs (exclude each tool's canonical goal) ----
rows = [(t, g) for t in tools for g in goals if g != canonical[t]]
def score(mode):
    tp=fp=fn=tn=0
    for t, g in rows:
        y = truth(t, g); p = predict(t, g, mode)
        tp += (y==1 and p==1); fn += (y==1 and p==0)
        fp += (y==0 and p==1); tn += (y==0 and p==0)
    recall = tp/(tp+fn) if tp+fn else float("nan")
    fpr    = fp/(fp+tn) if fp+tn else float("nan")
    acc    = (tp+tn)/(tp+tn+fp+fn)
    return dict(tp=tp, fn=fn, fp=fp, tn=tn, recall=recall, fpr=fpr, acc=acc)

S, U = score("specific"), score("upgrade")

print("="*72)
print("  CONCEPT UPGRADE: movement -> block enables zero-shot transfer")
print("="*72)
print(f"  learned media classes (unsupervised): ", end="")
for c in sorted(set(clab)):
    print("{" + ",".join(m for m in mnames if cluster_of[m]==c) + "} ", end="")
print("\n")
print(f"  the sail was only ever demonstrated on: {tools['sail']['demo']} (goal '{canonical['sail']}')")
print(f"  headline transfer -- sail on NEW goal 'stay_afloat' (block water):")
print(f"     truth: {truth('sail','stay_afloat')}   specific says: {predict('sail','stay_afloat','specific')}"
      f"   upgrade says: {predict('sail','stay_afloat','upgrade')}")
print(f"  guard -- sail on 'shelter' (block ROCK, wrong class):")
print(f"     truth: {truth('sail','shelter')}   specific: {predict('sail','shelter','specific')}"
      f"   upgrade: {predict('sail','shelter','upgrade')}   (upgrade must REFUSE)")
print()
print(f"  over all {len(rows)} novel (tool, goal) pairs:")
print(f"  {'rep':10}{'transfer recall':>18}{'false-positive':>16}{'accuracy':>12}")
print(f"  {'SPECIFIC':10}{S['recall']:>18.2f}{S['fpr']:>16.2f}{S['acc']:>12.2f}")
print(f"  {'UPGRADE':10}{U['recall']:>18.2f}{U['fpr']:>16.2f}{U['acc']:>12.2f}")
print()
print(f"  -> SPECIFIC ties each tool to the exact medium it was demonstrated on, so it")
print(f"     catches {S['tp']}/{S['tp']+S['fn']} true transfers (recall {S['recall']:.2f}) -- it can't reuse a tool on a new goal.")
print(f"  -> UPGRADE generalizes the demonstrated medium to its learned class (air->fluid),")
print(f"     catching {U['tp']}/{U['tp']+U['fn']} true transfers (recall {U['recall']:.2f}) with false-positive {U['fpr']:.2f}:")
print(f"     it transfers the sail to water WITHOUT claiming it can block a rockfall.")

# ---------------------------------------------------------------------------
# PLOT: left = media feature space with the sail's generalization region (its class);
# right = transfer recall / false-positive for SPECIFIC vs UPGRADE.
# ---------------------------------------------------------------------------
fig, (axL, axR) = plt.subplots(1, 2, figsize=(13.2, 5.4))
cols = ["#238b45", "#8a5a2b", "#e0a021"]
sail_c = cluster_of["air"]
# shade the sail's class region (fluid cluster convex-ish hull via circle around members)
fluid_pts = MF[clab == sail_c]
cx, cy = fluid_pts.mean(0); rad = max(np.hypot(*(p-[cx,cy])) for p in fluid_pts)+0.10
th = np.linspace(0,2*np.pi,100)
axL.fill(cx+rad*np.cos(th), cy+rad*np.sin(th), color="#238b45", alpha=0.12, zorder=0)
axL.text(cx-0.02, cy+rad+0.02, "sail's UPGRADED reach\n(block → any FLUID)", color="#238b45",
         fontsize=9, ha="center")
for i, m in enumerate(mnames):
    c = cols[clab[i] % len(cols)]
    axL.scatter(*MF[i], s=160, color=c, zorder=4, edgecolor="white")
    axL.annotate(m, MF[i], xytext=(6,5), textcoords="offset points", fontsize=9)
axL.scatter(*media["air"], s=340, facecolor="none", edgecolor="#c0392b", lw=2.2, zorder=5)
axL.text(media["air"][0]-0.02, media["air"][1]-0.09, "demonstrated (air)", color="#c0392b", fontsize=8.5)
axL.set_xlim(0,1.05); axL.set_ylim(0,1.05)
axL.set_xlabel("medium feature 1"); axL.set_ylabel("medium feature 2")
axL.set_title("The upgrade generalizes the demonstrated medium to its CLASS\n"
              "water falls inside (transfers); rock/sand/light stay out")

x = np.arange(2); w=0.35
axR.bar(x-w/2, [S['recall'], U['recall']], w, color="#238b45", label="true-transfer recall")
axR.bar(x+w/2, [S['fpr'], U['fpr']], w, color="#c0392b", label="false-positive rate")
for i,(r,f) in enumerate([(S['recall'],S['fpr']),(U['recall'],U['fpr'])]):
    axR.text(i-w/2, r+0.02, f"{r:.2f}", ha="center", fontsize=9)
    axR.text(i+w/2, f+0.02, f"{f:.2f}", ha="center", fontsize=9)
axR.set_xticks(x); axR.set_xticklabels(["SPECIFIC\n(tied to exact medium)","UPGRADE\n(generalize to class)"])
axR.set_ylim(0,1.1); axR.set_ylabel("rate over novel (tool, goal) pairs")
axR.set_title("Upgrade recovers the transfers the specific concept can't\n(without over-claiming)")
axR.legend(loc="center right", fontsize=9, framealpha=0.93)

fig.tight_layout(); fig.savefig("concept_upgrade.png", dpi=130)
print("\n  wrote concept_upgrade.png")
