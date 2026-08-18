#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
memory_loop.py -- the whole memory loop as ONE running system.

Ties the separate memory tests into a single continual agent, on a regime-switching
stream that REVISITS its regimes:
  * a miss (surprise) MINTS a clip at the gap                     (discovery, FOLDING_DISCOVERY)
  * the clip STORES (x, context, target)                          (T7)
  * recall SEALS by context — the coordinate that closes it       (T8)
  * the resolved clip becomes an ANCHOR the model rests on        (T7)
Run it live and it should LEARN and RETAIN: once a regime's clips are anchored (keyed by
context), the agent keeps them, so when that regime returns it is instantly right — while a
memoryless baseline (a sliding window over x, no context) forgets and re-fails every switch.

TASK: predict y from x. Two regimes (like the folded field of T8): f_A(x)=x, f_B(x)=1−x.
The regime is given as a CONTEXT coordinate c∈{0,1}. The schedule alternates A,B,A,B,…
(each regime revisited), so retention is exactly what's tested.
"""
import numpy as np
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

rng = np.random.default_rng(2)
BLOCK = 35; BLOCKS = 8; T = BLOCK*BLOCKS
HX, HC, W = 0.06, 0.25, 30
TOL, NOISE = 0.15, 0.02

def f(r, x): return x if r == 0 else 1.0 - x

# ---- the two agents ----
class Looped:                      # gaps → clips → context-keyed anchors (the full loop)
    def __init__(self): self.ax=[]; self.ac=[]; self.ay=[]; self.stored=0
    def predict(self, x, c):
        if not self.ax: return 0.5
        ax=np.array(self.ax); ac=np.array(self.ac); ay=np.array(self.ay)
        w=np.exp(-0.5*((x-ax)/HX)**2 - 0.5*((c-ac)/HC)**2)
        s=w.sum()
        return float((w*ay).sum()/s) if s>1e-9 else 0.5
    def observe(self, x, c, y, err):
        if err > TOL:              # a miss mints a clip; storing it resolves it into an anchor
            self.ax.append(x); self.ac.append(c); self.ay.append(y); self.stored+=1

class Baseline:                    # sliding window over x, no context, no retention
    def __init__(self): self.bx=[]; self.by=[]
    def predict(self, x, c):
        if not self.bx: return 0.5
        bx=np.array(self.bx); by=np.array(self.by)
        w=np.exp(-0.5*((x-bx)/HX)**2); s=w.sum()
        return float((w*by).sum()/s) if s>1e-9 else 0.5
    def observe(self, x, c, y, err):
        self.bx.append(x); self.by.append(y)
        if len(self.bx)>W: self.bx.pop(0); self.by.pop(0)

L=Looped(); B=Baseline()
errL=np.zeros(T); errB=np.zeros(T); regime=np.zeros(T,int); anchors=np.zeros(T)
for t in range(T):
    r = (t//BLOCK) % 2                      # A,B,A,B,... (revisiting)
    x = rng.uniform(0,1); c = float(r)
    y = f(r,x) + rng.normal(0,NOISE)
    pL=L.predict(x,c); pB=B.predict(x,c)
    eL=abs(pL-y); eB=abs(pB-y)
    errL[t]=eL; errB[t]=eB; regime[t]=r; anchors[t]=len(L.ax)
    L.observe(x,c,y,eL); B.observe(x,c,y,eB)

def roll(e,k=12): return np.convolve(e,np.ones(k)/k,mode="same")
rL=roll(errL); rB=roll(errB)
switches=[b*BLOCK for b in range(1,BLOCKS)]
# error in the first 8 steps after each REVISIT (a regime seen before)
def post_switch(e):
    idx=[t for b in range(1,BLOCKS) for t in range(b*BLOCK, b*BLOCK+8)]
    return float(np.mean(e[idx]))

print("="*72)
print("  THE MEMORY LOOP END-TO-END: mint → store → seal-by-context → anchor")
print("="*72)
print(f"  {BLOCKS} regime blocks (A,B,A,B,… each revisited), {T} steps")
print()
print(f"  {'agent':26}{'mean error':>12}{'error just after a switch':>28}")
print(f"  {'LOOPED (context-keyed anchors)':26}{errL.mean():>12.3f}{post_switch(errL):>28.3f}")
print(f"  {'BASELINE (window, no memory)':26}{errB.mean():>12.3f}{post_switch(errB):>28.3f}")
print()
print(f"  clips the looped agent stored: {L.stored} (it stops storing once both regimes are anchored)")
print()
print(f"  -> the LOOPED agent stores each miss as a context-keyed anchor, so regime A's anchors")
print(f"     survive while B runs; when A returns it is instantly right (mean {errL.mean():.3f}).")
print(f"  -> the BASELINE window has no context and forgets: every regime switch flips the x→y")
print(f"     map, its window is stale, and it spikes (post-switch error {post_switch(errB):.2f} vs {post_switch(errL):.2f}).")
print(f"     The loop = retention: the same gap→clip→anchor machinery, run continuously.")

# ---------------------------------------------------------------------------
# PLOT: rolling error over the stream (regime bands shaded), + anchor count.
# ---------------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(11.8, 5.2))
for b in range(BLOCKS):
    ax.axvspan(b*BLOCK,(b+1)*BLOCK, color=("#eef5ff" if b%2==0 else "#fdeeee"), zorder=0)
for s in switches: ax.axvline(s, color="#ccc", lw=0.8)
ax.plot(rB, color="#c0392b", lw=2.0, label=f"baseline (window, no memory) — mean {errB.mean():.3f}")
ax.plot(rL, color="#238b45", lw=2.2, label=f"looped (context-keyed anchors) — mean {errL.mean():.3f}")
ax2=ax.twinx()
ax2.plot(anchors, color="#8a6fc0", lw=1.1, ls=":", alpha=0.8)
ax2.set_ylabel("anchors stored (dotted)", color="#6a4fa0"); ax2.set_ylim(0, max(anchors)*1.3)
ax.text(2, 0.44, "blue = regime A (y=x) · red = regime B (y=1−x) · each revisited", fontsize=8.5, color="#666")
ax.set_xlabel("step (continual stream)"); ax.set_ylabel("rolling prediction error")
ax.set_title("The memory loop, run live: store misses as context-keyed anchors →\n"
             "retain across regime revisits; the memoryless baseline forgets and spikes each switch")
ax.legend(loc="upper right", fontsize=9, framealpha=0.94); ax.set_ylim(0,0.5)
fig.tight_layout(); fig.savefig("memory_loop.png", dpi=130)
print("\n  wrote memory_loop.png")
