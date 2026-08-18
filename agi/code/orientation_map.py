#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
orientation_map.py -- the context plane holds coordinates; it needs anchors AND orientation.

Jonathan: the matter (normal) plane can't see the orthogonal (context) plane, but the
context plane CAN see parts of the matter one -- "parts sticking out." So the context
layer can see a MAP and use COORDINATES based on what it sees. But the matter plane is
"a vast ocean with no references" -- no landmarks, no coordinates. "We would need
something to do orientation though."

This is exactly localization from BEARINGS to anchors, and orientation is the missing
gauge. Grounding: `FOLDING_VOID_LINE_DRAW` -- the wall "emits a BEARING to a field
extension," and anchor points "become visible on the LIFT" into the orthogonal axis
(invisible in the matter projection, `INNER_SHELL`); a pinned void line is a named
anchor ("a meaning lives here"). Orientation = the frame: `FOLDING_TRAMPOLINE` §5 /
`FOLDING_OBSERVER_FRAME` -- a single ring-stack "has a blind axis"; you need the
three-ring (quaternion i/j/k) cage to fix any direction. "Parts sticking out" = the
anchors; the bearing to them is the coordinate signal; the frame is orientation.

FOUR CONDITIONS (localize the agent's 2-D position):
  A  FEATURELESS OCEAN (matter plane) -- no anchors. Position is unobservable; the best
     you can do is the prior (world center). No coordinates.
  B  2 ANCHORS, NO ORIENTATION -- you see relative bearings but not your heading. Only
     the ANGLE SUBTENDED between anchors is usable (heading cancels) -> position lies on
     an ARC (a 1-parameter ambiguity). You know you're somewhere on a curve, not where.
  C  2 ANCHORS + ORIENTATION (a compass) -- absolute bearings. Two lines of position
     cross at one point. Located.
  D  3 ANCHORS, NO COMPASS -- two independent subtended angles (resection) pin the point
     AND recover the heading. The third anchor SUPPLIES the orientation. Located.

Result: coordinates need references (anchors) AND orientation; orientation can come from
a compass OR from an extra anchor sticking out of the ocean.
"""
import numpy as np
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

W = 10.0
rng = np.random.default_rng(3)
NOISE = 0.02                       # bearing noise (rad)
ANCH3 = np.array([[0.6,0.6],[9.4,1.0],[5.0,9.4]])   # three anchors "sticking out"
ANCH2 = ANCH3[:2]

def angdiff(a, b):
    return np.abs((a - b + np.pi) % (2*np.pi) - np.pi)

# localization grid (the map the context plane reads coordinates on)
gx = np.linspace(0.2, W-0.2, 140); gy = np.linspace(0.2, W-0.2, 140)
GX, GY = np.meshgrid(gx, gy)
def grid_bearings(anchor):
    return np.arctan2(anchor[1]-GY, anchor[0]-GX)          # bearing from each grid cell to anchor

GB3 = [grid_bearings(a) for a in ANCH3]
GB2 = GB3[:2]

def true_bearings(p, anchors):
    return np.arctan2(anchors[:,1]-p[1], anchors[:,0]-p[0])

def localize(p, cond):
    if cond == "A":                                        # featureless: prior only
        return np.array([W/2, W/2]), None
    if cond == "C":                                        # 2 anchors + compass (absolute)
        b = true_bearings(p, ANCH2) + rng.normal(0, NOISE, 2)
        res = angdiff(GB2[0], b[0])**2 + angdiff(GB2[1], b[1])**2
    elif cond == "B":                                      # 2 anchors, no orientation
        b = true_bearings(p, ANCH2) + rng.normal(0, NOISE, 2)
        dmeas = b[0] - b[1]                                # subtended angle (heading cancels)
        res = angdiff(GB2[0]-GB2[1], dmeas)**2
    elif cond == "D":                                      # 3 anchors, no compass (resection)
        b = true_bearings(p, ANCH3) + rng.normal(0, NOISE, 3)
        res = (angdiff(GB3[0]-GB3[1], b[0]-b[1])**2
             + angdiff(GB3[0]-GB3[2], b[0]-b[2])**2)
    i = np.unravel_index(np.argmin(res), res.shape)
    est = np.array([GX[i], GY[i]])
    # for the ambiguous case, the honest estimate is the centroid of the near-optimal set
    if cond == "B":
        lo = res < (res.min() + 1e-3)
        est = np.array([GX[lo].mean(), GY[lo].mean()])
    return est, res

TRIALS = 300
errs = {c: [] for c in "ABCD"}
for _ in range(TRIALS):
    p = rng.uniform(1.0, W-1.0, 2)
    for c in "ABCD":
        est, _ = localize(p, c)
        errs[c].append(float(np.hypot(*(est - p))))
mean = {c: float(np.mean(errs[c])) for c in "ABCD"}

print("="*72)
print("  COORDINATES NEED ANCHORS AND ORIENTATION (localize from bearings)")
print("="*72)
print(f"  world {W:.0f}×{W:.0f}, bearing noise {NOISE} rad, {TRIALS} trials")
print()
labels = {"A":"A  featureless ocean (matter plane)",
          "B":"B  2 anchors, NO orientation",
          "C":"C  2 anchors + orientation (compass)",
          "D":"D  3 anchors, no compass (resection)"}
print(f"  {'condition':40}{'mean localization error':>24}")
for c in "ABCD":
    print(f"  {labels[c]:40}{mean[c]:>24.2f}")
print()
print(f"  -> A the matter ocean has no references: position is unobservable, error"
      f" {mean['A']:.1f} (~prior).")
print(f"  -> B anchors but NO orientation: you know you're on an ARC, not a point --"
      f" error {mean['B']:.1f}.")
print(f"     This is exactly 'we need something to do orientation.'")
print(f"  -> C add a compass (orientation) and 2 anchors pin the point: error {mean['C']:.2f}.")
print(f"  -> D no compass, but a THIRD anchor sticking out supplies the orientation"
      f" (resection): {mean['D']:.2f}.")
print(f"     Coordinates need references AND a frame; the frame comes from a compass or an extra anchor.")

# ---- illustrative single trial for the map panel ----
p0 = np.array([3.2, 6.4])
_, resB = localize(p0, "B")
estC, _ = localize(p0, "C")
estD, _ = localize(p0, "D")

fig, (axL, axR) = plt.subplots(1, 2, figsize=(13.2, 5.4))

# left: the map. anchors, true pos, the B ambiguity arc (low-residual set), C/D points.
axL.imshow((resB < (resB.min()+2e-3)), extent=[0.2,W-0.2,0.2,W-0.2], origin="lower",
           cmap="Oranges", alpha=0.55, aspect="auto")
axL.scatter(ANCH3[:,0], ANCH3[:,1], marker="*", s=240, color="#111",
            label="anchors (parts sticking out)", zorder=5)
axL.scatter([p0[0]],[p0[1]], s=90, color="#c0392b", zorder=6, label="true position")
axL.scatter([estC[0]],[estC[1]], s=80, marker="P", color="#238b45",
            label="C: 2 anchors + orientation → located", zorder=6)
axL.scatter([estD[0]],[estD[1]], s=70, marker="X", color="#2b8cbe",
            label="D: 3 anchors (resection) → located", zorder=6)
axL.text(3.4, 3.2, "orange = where B thinks it\ncould be (no orientation → an arc)",
         color="#b3560a", fontsize=8.5)
axL.set_xlim(0, W); axL.set_ylim(0, W)
axL.set_xlabel("x"); axL.set_ylabel("y")
axL.set_title("The context plane reads coordinates off anchors\nwithout orientation, position is only an arc")
axL.legend(loc="upper right", fontsize=7.8, framealpha=0.93)

# right: mean error bars
cols = {"A":"#8e8e8e","B":"#e6820a","C":"#238b45","D":"#2b8cbe"}
axR.bar(list("ABCD"), [mean[c] for c in "ABCD"], color=[cols[c] for c in "ABCD"])
for i,c in enumerate("ABCD"):
    axR.text(i, mean[c]+0.05, f"{mean[c]:.2f}", ha="center", fontsize=9)
axR.set_ylabel("mean localization error"); axR.set_xlabel("condition")
axR.set_title("Coordinates need references AND orientation\n(A ocean · B no-frame · C compass · D extra anchor)")
axR.set_xticks(range(4)); axR.set_xticklabels(
    ["A\nocean","B\n2, no orient","C\n2 + compass","D\n3 anchors"], fontsize=8.5)

fig.tight_layout(); fig.savefig("orientation_map.png", dpi=130)
print("\n  wrote orientation_map.png")
