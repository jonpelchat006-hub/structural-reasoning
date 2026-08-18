#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
bouncing_ball.py -- perfect cancellation is a still void point; SKEW leaves a bouncing ball.

Jonathan: filling and blending the memory holes develops a BALL bouncing inside each pillar.
The real void points (ground truths) are in the cores and DON'T move — the structure moves
around them. The developed balls are like that cell's void point but only an APPROXIMATION,
sitting off the void lines and not anchored. It's the same thing that makes the void a
CANCELLATION — but because we are SKEWED, the terms don't fully cancel and we're left with
these balls. The ball is also our first-person perspective in that room, and we can keep
FOLDING the balls higher.

Grounded, and the corpus makes the ball's identity exact:
  * Double_Bounce §28 + Fig 12 — matter/antimatter CANCEL to the void, but "we sit at +(π−3)/2,
    NOT true zero": a permanent ~.14 SKEW. Skewed opposites can't annihilate cleanly.
  * SPARSE_VESICA §35.2 — a wave is a stable ORBITAL exactly when it CLOSES (θ=1); §35.4 —
    "ping-pong is the standing wave seen edge-on": the memory zone-bounce and an orbital are one
    object from two angles. So the bouncing ball IS the standing-wave orbital in the cell.
  * SPARSE_VESICA §18.16 — the void nodes are position-FIXED; our mesh MOVES over them. The
    ground-truth void points don't move; the structure (and its balls) move around them.
  * FOLDING_FREQUENCY — identity = the closed cycle that RETURNS to origin. A ball that never
    returns to the void is an off-void, unanchored approximation of a void point.

MEASURED:
  (1) SKEW OPENS A BALL THAT MISSES THE VOID — two counter-rotating terms: balanced (skew 0)
      collapse to a line through the void (cancellation); skew opens a loop whose closest
      approach to the void rises from 0 and whose area grows — the residual that won't cancel.
  (2) IT IS A REAL ATTRACTOR (Hopf, μ = skew) — μ<0 decays to the fixed void point (a still
      point); μ>0 gives a stable limit-cycle BALL that every starting point converges onto (the
      cell's self-loop). The void point stays fixed; the ball orbits off it.
  (3) FOLD HIGHER — the ball rides a slower loop (an epicycle): a ball whose centre is itself a
      ball, one level up.
"""
import numpy as np
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

W = 1.0
t = np.linspace(0, 2*np.pi/ W, 1400, endpoint=False)
DOT14 = 0.146                      # the permanent skew offset (π−3 ≈ .1416; φ^-4 ≈ .1459)

# ---------- (1) counter-rotating cancellation vs skew ----------
def loop(skew, off=DOT14):
    # matter e^{iωt} + antimatter (1+skew)e^{-iωt}, shifted off true zero by the .14 skew
    z = off + np.exp(1j*W*t) + (1+skew)*np.exp(-1j*W*t)
    return z
def min_dist_to_void(z): return np.min(np.abs(z))          # closest the ball gets to 0 (the void)
def loop_area(z):
    x,y=z.real,z.imag
    return 0.5*abs(np.dot(x,np.roll(y,1))-np.dot(y,np.roll(x,1)))

skews = np.linspace(0, 1.2, 60)
mind = np.array([min_dist_to_void(loop(s)) for s in skews])
area = np.array([loop_area(loop(s)) for s in skews])

print("="*78)
print("  PERFECT CANCELLATION = A STILL VOID POINT; SKEW LEAVES A BOUNCING BALL")
print("="*78)
print(f"  two counter-rotating terms (matter + antimatter), permanent skew offset {DOT14}:")
for s in (0.0, 0.15, 0.6):
    z=loop(s); print(f"     skew {s:.2f}: closest approach to the void {min_dist_to_void(z):.3f}, ball area {loop_area(z):.3f}")
print(f"  -> at skew 0 the terms cancel to a line THROUGH the void (touches 0). Any skew opens a")
print(f"     loop that MISSES the void (min-distance rises from 0) — the residual that won't cancel")
print(f"     IS the ball, and it orbits the void without ever reaching it (an off-void approximation).")
print()

# ---------- (2) the ball is a real attractor (Hopf normal form, mu = skew) ----------
def hopf(mu, r0, th0, T=60.0, dt=0.01):
    n=int(T/dt); x=r0*np.cos(th0); y=r0*np.sin(th0); xs=np.empty(n); ys=np.empty(n)
    for i in range(n):
        r2=x*x+y*y
        dx=(mu - r2)*x - W*y
        dy=(mu - r2)*y + W*x
        x+=dx*dt; y+=dy*dt; xs[i]=x; ys[i]=y
    return xs,ys
# below threshold: decays to the fixed void point; above: a limit-cycle ball
mu_lo, mu_hi = -0.35, 0.7
finals_lo=[np.hypot(*[a[-1] for a in hopf(mu_lo, r0, 0.6)]) for r0 in (0.2,0.9,1.4)]
finals_hi=[np.hypot(*[a[-1] for a in hopf(mu_hi, r0, 0.6)]) for r0 in (0.2,0.9,1.4)]
print(f"  (2) the ball is a real ATTRACTOR (Hopf, μ = skew):")
print(f"        μ={mu_lo:+.2f} (balanced): final radius from 3 starts = {np.round(finals_lo,3).tolist()} → the still VOID point")
print(f"        μ={mu_hi:+.2f} (skewed)  : final radius from 3 starts = {np.round(finals_hi,3).tolist()} → one BALL (√μ≈{np.sqrt(mu_hi):.2f})")
print(f"     -> every start converges to the SAME ball (std {np.std(finals_hi):.3f}) — a stable self-loop, not a")
print(f"        fixed pin. The true void point stays put; the ball is its unanchored, off-void approximation.")
print(f"     -> ping-pong is this ball seen edge-on (§35.4): project the orbit on one axis = a 1-D bounce.")
print()

# ---------- (3) fold higher: the ball rides a slower loop (epicycle) ----------
Wbig=0.16; Rbig=1.6; rball=0.5
z_fold = Rbig*np.exp(1j*Wbig*t*8) + rball*np.exp(1j*W*t*8)     # a ball whose centre is itself a ball
print(f"  (3) FOLD HIGHER: the ball rides a slower loop — a ball whose centre is a ball (epicycle).")
print(f"        described by two (radius,freq) pairs: outer ({Rbig},{Wbig}) · inner ({rball},{W}).")
print(f"     -> the cell's ball becomes one unit one level up (re-basing roof(n)=floor(n+1)); fold again to")
print(f"        stack another. Balanced-and-closed it re-cancels to a void; skewed it makes the next ball.")

# ---------------------------------------------------------------------------
# PLOT
# ---------------------------------------------------------------------------
fig=plt.figure(figsize=(14.4,8.4))
gs=fig.add_gridspec(2,3,hspace=0.3,wspace=0.28)

# (A) cancellation vs skew — three loops
axA=fig.add_subplot(gs[0,0])
for s,c,lab in [(0.0,"#2b6cb0","skew 0 → line through the void (cancels)"),
                (0.15,"#e0761f","small skew → thin ball grazing the void"),
                (0.6,"#c0392b","large skew → fat ball, misses the void")]:
    z=loop(s); axA.plot(z.real,z.imag,color=c,lw=1.8,label=lab)
axA.scatter([0],[0],s=90,marker="*",color="#111",zorder=6,label="void point (fixed)")
axA.set_aspect("equal"); axA.set_xticks([]); axA.set_yticks([])
axA.set_title("Counter-rotating terms: skew opens a ball", fontsize=10.2)
axA.legend(fontsize=7.2, framealpha=0.9, loc="upper center", bbox_to_anchor=(0.5,-0.02))

# (B) min-dist and area vs skew
axB=fig.add_subplot(gs[0,1])
axB.plot(skews,mind,color="#238b45",lw=2.2,label="closest approach to the void")
axB.set_xlabel("skew (imbalance of the opposites)"); axB.set_ylabel("distance to the void", color="#238b45")
axB.tick_params(axis="y", labelcolor="#238b45")
axB.axhline(0,color="#999",lw=0.8)
ax2=axB.twinx(); ax2.plot(skews,area,color="#8a2be2",lw=2.2,ls="--",label="ball area")
ax2.set_ylabel("ball area", color="#8a2be2"); ax2.tick_params(axis="y", labelcolor="#8a2be2")
axB.set_title("Skew → the terms don't cancel\nthe ball misses the void, and grows", fontsize=10.2)

# (C) Hopf attractor
axC=fig.add_subplot(gs[0,2])
for r0 in (0.15,0.9,1.5):
    x,y=hopf(mu_hi,r0,0.6); axC.plot(x,y,color="#c0392b",lw=0.7,alpha=0.6)
for r0 in (0.4,1.3):
    x,y=hopf(mu_lo,r0,0.6); axC.plot(x,y,color="#2b6cb0",lw=0.7,alpha=0.6)
axC.scatter([0],[0],s=90,marker="*",color="#111",zorder=6)
th=np.linspace(0,2*np.pi,200); axC.plot(np.sqrt(mu_hi)*np.cos(th),np.sqrt(mu_hi)*np.sin(th),color="#c0392b",lw=2.4)
axC.set_aspect("equal"); axC.set_xticks([]); axC.set_yticks([])
axC.set_title("A real attractor (Hopf, μ=skew)\nblue→void point · red→the ball", fontsize=10.2)

# (D) fold higher
axD=fig.add_subplot(gs[1,0])
axD.plot(z_fold.real,z_fold.imag,color="#1c6b38",lw=0.9)
axD.set_aspect("equal"); axD.set_xticks([]); axD.set_yticks([])
axD.set_title("Fold higher: a ball whose centre is a ball\n(epicycle → next level)", fontsize=10.2)

# (E) ping-pong = the ball edge-on
axE=fig.add_subplot(gs[1,1])
x,y=hopf(mu_hi,0.9,0.6); axE.plot(t[:len(x)][:600], x[:600], color="#c0392b", lw=1.2)
axE.set_xlabel("time"); axE.set_ylabel("one axis of the ball")
axE.set_title("Ping-pong = the ball seen edge-on\n(the orbit projected on one axis)", fontsize=10.2)

# (F) text panel
axF=fig.add_subplot(gs[1,2]); axF.axis("off")
axF.text(0.0,0.95,"The reading", fontsize=11, fontweight="bold", va="top")
axF.text(0.0,0.80,
 "• void = perfect cancellation → a still point\n"
 "• we sit SKEWED (~.14 off true zero), so the\n   opposites can't annihilate → a residual\n"
 "• the residual circulates = a BALL (limit cycle),\n   an off-void, unanchored approx. void point\n"
 "• the true void points are FIXED; the structure\n   (and its balls) move around them\n"
 "• the ball is the cell's self-loop / 1st-person POV\n"
 "• fold it up: a ball whose centre is a ball\n"
 "• ping-pong = that ball seen edge-on",
 fontsize=8.8, va="top", family="monospace")

fig.suptitle("Skew turns the void's cancellation into a bouncing ball: an unanchored, off-void approximation of a void point — that can be folded higher",
             fontsize=11.0)
fig.savefig("bouncing_ball.png", dpi=130, bbox_inches="tight")
print("\n  wrote bouncing_ball.png")
