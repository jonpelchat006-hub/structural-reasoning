#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
perspective_swing.py -- swing the structure around an anchor: a hard view becomes easy.

Jonathan: swinging the whole structure around one anchor point, then switching which
anchor you're on, is looking at the thing through a different perspective. Measured claim:
a task that is HARD from one frame is EASY from another — the same data, seen by pivoting
the readout frame around a ground-truth anchor.

SETUP: two classes that are two parallel streaks, separated along a diagonal direction u
but each stretched along the perpendicular v. Read the world through a 1-D "view" — project
onto a direction and threshold. From the raw axes (x or y) the streaks OVERLAP (you can't
tell them apart). Pivot the frame around the anchor (the between-class midpoint) to the
discriminant direction and a single coordinate separates them cleanly. Separability vs the
perspective angle has a sharp peak: the right perspective makes the hard problem trivial.

This is the perspective-swing of FOLDING_SYNTHESIS §5 made measurable — a rotation about a
ground-truth anchor — and it is the same return-to-origin frame idea as the spin-identity
(FOLDING_FREQUENCY): change the view, not the object.
"""
import numpy as np
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

rng = np.random.default_rng(7)
N = 400
ALPHA = np.deg2rad(50.0)                        # the true discriminant direction
u = np.array([np.cos(ALPHA), np.sin(ALPHA)])    # separation direction
v = np.array([-np.sin(ALPHA), np.cos(ALPHA)])   # elongation direction
SEP = 1.15; SPREAD = 3.2; TIGHT = 0.35

def make():
    X=[]; y=[]
    for c,s in [(0,-SEP),(1,+SEP)]:
        a = rng.normal(0, SPREAD, N)            # along v (elongated -> overlap on axes)
        b = rng.normal(s, TIGHT, N)             # along u (separated)
        P = np.outer(a, v) + np.outer(b, u)
        X.append(P); y += [c]*N
    return np.vstack(X), np.array(y)

X, y = make()
anchor = X.mean(0)                              # the ground-truth pivot (between-class midpoint)

def acc_at(theta):
    d = np.array([np.cos(theta), np.sin(theta)])
    p = (X - anchor) @ d                         # 1-D view through the anchor, direction theta
    # best threshold = midpoint of class means on this projection (no fitting to labels beyond means)
    m0, m1 = p[y==0].mean(), p[y==1].mean()
    thr = 0.5*(m0+m1); pred = (p > thr).astype(int)
    if m0 > m1: pred = 1-pred
    return max((pred==y).mean(), 1-(pred==y).mean())

thetas = np.linspace(0, np.pi, 361)
accs = np.array([acc_at(t) for t in thetas])
axis_acc = acc_at(0.0)                           # the raw x-axis view
best_i = int(np.argmax(accs)); best_theta = thetas[best_i]; best_acc = accs[best_i]

print("="*72)
print("  PERSPECTIVE SWING: pivot the frame around an anchor -> a hard view becomes easy")
print("="*72)
print(f"  two classes, separated along {np.rad2deg(ALPHA):.0f}° but elongated across it")
print(f"  read the world as a 1-D view (project + threshold), pivoting on the anchor {anchor.round(2)}")
print()
print(f"  RAW axis view (θ=0°)      : accuracy {axis_acc:.2f}  (streaks overlap — hard)")
print(f"  y-axis view (θ=90°)       : accuracy {acc_at(np.pi/2):.2f}")
print(f"  BEST perspective (θ={np.rad2deg(best_theta):.0f}°): accuracy {best_acc:.2f}  (the discriminant frame — easy)")
print()
print(f"  -> the SAME data is near-chance from the raw axes and near-perfect once you swing the")
print(f"     frame to the right perspective around the anchor. Different anchors expose different")
print(f"     rotations, so which ground truth you pivot on decides which views you can reach.")
print(f"     'Looking at things through a different perspective,' measured: separability peaks")
print(f"     sharply at the discriminant angle ({np.rad2deg(best_theta):.0f}°).")

# ---------------------------------------------------------------------------
# PLOT: left = the 2-D data + the two frames (raw axis vs swung discriminant axis);
# right = separability vs perspective angle, peak marked.
# ---------------------------------------------------------------------------
fig, (axL, axR) = plt.subplots(1, 2, figsize=(13.2, 5.4))
for c,col in [(0,"#2b8cbe"),(1,"#c0392b")]:
    axL.scatter(X[y==c,0], X[y==c,1], s=8, color=col, alpha=0.45)
axL.scatter(*anchor, s=140, color="#111", marker="*", zorder=6, label="anchor (pivot)")
L=4.2
# raw axis view (bad)
axL.annotate("", anchor+np.array([L,0]), anchor-np.array([L,0]),
             arrowprops=dict(arrowstyle="<->", color="#888", lw=1.6))
axL.text(anchor[0]+L*0.5, anchor[1]-0.6, "raw view (θ=0°) → overlap", color="#777", fontsize=9)
# swung discriminant view (good)
dd = np.array([np.cos(best_theta), np.sin(best_theta)])
axL.annotate("", anchor+dd*L, anchor-dd*L,
             arrowprops=dict(arrowstyle="<->", color="#238b45", lw=2.4))
axL.text(anchor[0]+dd[0]*L*0.6+0.2, anchor[1]+dd[1]*L*0.6, f"swung view (θ={np.rad2deg(best_theta):.0f}°) → separates",
         color="#1c6b38", fontsize=9)
axL.set_aspect("equal"); axL.set_xticks([]); axL.set_yticks([])
axL.set_title("Same data, two frames\nraw axes overlap; the swung frame separates")
axL.legend(loc="upper left", fontsize=8.5, framealpha=0.9)

axR.plot(np.rad2deg(thetas), accs, color="#238b45", lw=2.2)
axR.axhline(axis_acc, color="#888", ls=":", lw=1)
axR.scatter([np.rad2deg(best_theta)],[best_acc], color="#c0392b", s=60, zorder=5)
axR.annotate(f"best perspective\n{np.rad2deg(best_theta):.0f}° → {best_acc:.2f}",
             (np.rad2deg(best_theta), best_acc), xytext=(np.rad2deg(best_theta)+16, best_acc-0.13),
             fontsize=9, color="#c0392b", arrowprops=dict(arrowstyle="->", color="#c0392b"))
axR.text(2, axis_acc+0.01, f"raw axis {axis_acc:.2f}", color="#777", fontsize=9)
axR.set_xlabel("perspective angle (° pivoting on the anchor)"); axR.set_ylabel("class separability (accuracy)")
axR.set_title("A hard view becomes easy by swinging the frame\nseparability peaks at the discriminant perspective")
axR.set_ylim(0.45,1.02)

fig.tight_layout(); fig.savefig("perspective_swing.png", dpi=130)
print("\n  wrote perspective_swing.png")
