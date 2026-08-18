#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ring_of_truths.py -- a rotating ring of truths you verify through a narrow gate.

Jonathan: the first orthogonal level is one slot on a larger RING, and the ring rotates
through the truths it has built up. Picture the Ophanim — the big wheels covered in eyes,
each eye a truth you verify from; the rings turn on their own axis and you only check the
eyes that pass through the gate. So you never check every truth at once; you check the few
currently in the window, and either let the wheel turn (survey everything eventually) or
turn it on purpose to bring the truth you SUSPECT through the gate (attention).

The claim, made measurable: with a ring of N truths and a gate of width k << N, you do NOT
need to pay the cost of checking all N every step. A blindly-rotating wheel covers every
truth over one full turn at cost k/step, but is slow to catch a specific violation. A
STEERED wheel — turned to bring the suspected eye through the gate — catches the violation
almost as fast as checking everything, at the same cheap cost k. Attention = choosing the
rotation.

Grounded: the ring of orthogonal observers is the quaternion three-ring cage
(FOLDING_TRAMPOLINE §5: a single parallel stack has a blind axis; rings in different
orientations remove it); an observer is a projection onto its frame (FOLDING_OBSERVERS);
"only check the eyes passing through" = gating/attention over the observer frame; higher
rings are mutually orthogonal levels (the φ-ladder / Cayley-Dickson doubling, each ×φ adds
an axis orthogonal to all below — so the upper rings don't poke into the normal plane).

MEASURED: over many random single-violation trials on a ring of N truths, compare
  CHECK-ALL  (verify all N every step: latency 0, cost N),
  BLIND-ROTATE (gate width k, wheel turns +k each step: full coverage in N/k steps, cost k),
  STEERED-ROTATE (turn the suspected eye into the gate using a noisy cue: cost k),
on detection latency, per-step verification cost, and full-turn coverage.
"""
import numpy as np
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

N      = 60          # truths on the ring ("eyes")
K      = 6           # gate width (eyes visible through the gate at once)
CUE_P  = 0.75        # steering cue points at the true violated eye with this prob (else random)
TRIALS = 4000
rng = np.random.default_rng(0)

# A "trial": one eye v in 0..N-1 is being violated. A policy verifies some subset of eyes
# each step (its gate contents) and DETECTS when the violated eye is inside the gate that step.
# We record: steps-to-detect (latency) and eyes-verified-per-step (cost).

def run_check_all(v):
    # verify all N every step -> caught on step 0, cost N
    return 0, N

def run_blind_rotate(v):
    # gate covers eyes [g, g+K) mod N; g advances by K each step -> tiles the ring.
    # start the wheel at a random phase so latency isn't rigged.
    g = int(rng.integers(0, N))
    for step in range(N):                      # at most N/K distinct windows; cap generously
        window = (np.arange(g, g+K) % N)
        if v in window:
            return step, K
        g = (g + K) % N
    return N, K                                # (won't happen: full coverage guaranteed)

def run_steered_rotate(v):
    # a cheap cue suggests where to look. With prob CUE_P it points at the violated eye's
    # neighbourhood; else it points somewhere random. We rotate that suggestion into the gate
    # (cost 0 to turn), then verify the K eyes in the gate (cost K). If the cue was right, caught
    # on step 0; if wrong, fall back to blind rotation from there.
    if rng.random() < CUE_P:
        cue = (v + int(rng.integers(-K//2, K//2+1))) % N     # noisy but on-target
    else:
        cue = int(rng.integers(0, N))                        # misdirected
    g = (cue - K//2) % N
    for step in range(N):
        window = (np.arange(g, g+K) % N)
        if v in window:
            return step, K
        g = (g + K) % N
    return N, K

def sweep(policy):
    lat = np.empty(TRIALS); cost = np.empty(TRIALS)
    for i in range(TRIALS):
        v = int(rng.integers(0, N))
        l, c = policy(v)
        lat[i] = l; cost[i] = c
    return lat, cost

names = ["CHECK-ALL", "BLIND-ROTATE", "STEERED-ROTATE"]
pols  = [run_check_all, run_blind_rotate, run_steered_rotate]
res = {}
for nm, p in zip(names, pols):
    lat, cost = sweep(p)
    res[nm] = dict(lat_mean=lat.mean(), lat_p95=np.percentile(lat,95),
                   cost=cost.mean(), lat=lat)

# coverage check: does one full turn of the blind wheel touch every eye?
g=0; seen=set()
for _ in range(N):
    for e in (np.arange(g,g+K)%N): seen.add(int(e))
    g=(g+K)%N
full_cov = len(seen)==N

print("="*74)
print("  A ROTATING RING OF TRUTHS: verify through a narrow gate, steer to attend")
print("="*74)
print(f"  ring of N={N} truths, gate width K={K}  (you see {K}/{N} = {100*K/N:.0f}% of the ring at once)")
print(f"  one eye is violated per trial; {TRIALS} trials")
print()
print(f"  {'policy':16}{'verify cost / step':>20}{'mean latency':>15}{'95th‑pct latency':>18}")
for nm in names:
    r=res[nm]
    print(f"  {nm:16}{r['cost']:>18.0f}  {r['lat_mean']:>13.2f}{r['lat_p95']:>18.0f}")
print()
print(f"  full-turn coverage of the blind wheel: {'ALL '+str(N)+' eyes' if full_cov else 'INCOMPLETE'}")
print()
ca, bl, st = res["CHECK-ALL"], res["BLIND-ROTATE"], res["STEERED-ROTATE"]
print(f"  -> CHECK-ALL catches instantly (latency {ca['lat_mean']:.1f}) but pays the whole ring every")
print(f"     step (cost {ca['cost']:.0f} = {N}). That doesn't scale as the ring of truths grows.")
print(f"  -> BLIND-ROTATE pays only K={K}/step and still covers EVERY truth over one turn, but is")
print(f"     slow on any specific violation (mean latency {bl['lat_mean']:.1f}, up to {bl['lat_p95']:.0f}).")
print(f"  -> STEERED-ROTATE pays the SAME K={K}/step yet catches the violation in {st['lat_mean']:.2f} steps")
print(f"     on average — {ca['cost']/st['cost']:.0f}× cheaper than check-all at nearly its latency. Turning")
print(f"     the wheel to bring the suspected eye through the gate IS attention: same cost as the")
print(f"     blind survey, almost the responsiveness of checking everything. The ring lets you hold")
print(f"     many truths and still verify cheaply — you verify the eyes at the gate, not all of them.")

# ---------------------------------------------------------------------------
# PLOT: (L) the ring with a gate wedge + one violated eye; (R) cost vs latency tradeoff.
# ---------------------------------------------------------------------------
fig = plt.figure(figsize=(13.4, 5.6))
axL = fig.add_subplot(1,2,1, projection="polar")
ang = np.linspace(0, 2*np.pi, N, endpoint=False)
axL.scatter(ang, np.ones(N), s=26, color="#7a8aa0", zorder=3)
# the gate wedge (K eyes) near the top
g0 = N//2
gate_idx = (np.arange(g0, g0+K) % N)
axL.scatter(ang[gate_idx], np.ones(K), s=70, color="#f0c040", edgecolor="#7a5a00", zorder=5, label="eyes at the gate (verified now)")
axL.bar((ang[gate_idx].mean()), 1.25, width=2*np.pi*K/N, bottom=0, color="#f0c040", alpha=0.14, zorder=1)
# the violated eye (steered into the gate)
vi = gate_idx[K//2]
axL.scatter([ang[vi]],[1.0], s=150, color="#c0392b", marker="*", zorder=6, label="violated truth (steered in)")
axL.annotate("rotate →", xy=(ang[g0]-0.35, 1.34), fontsize=9, color="#8a6a00")
axL.set_rticks([]); axL.set_xticks([]); axL.set_ylim(0,1.45)
axL.set_title(f"Ring of N={N} truths — verify only the K={K} at the gate,\nturn the wheel to bring the suspected eye through", fontsize=10.5)
axL.legend(loc="lower center", bbox_to_anchor=(0.5,-0.16), fontsize=8.5, ncol=2, framealpha=0.9)

axR = fig.add_subplot(1,2,2)
cols = {"CHECK-ALL":"#2b6cb0","BLIND-ROTATE":"#c0392b","STEERED-ROTATE":"#238b45"}
for nm in names:
    r=res[nm]
    axR.scatter([r['cost']],[r['lat_mean']], s=150, color=cols[nm], zorder=5, edgecolor="k", linewidth=0.6)
    dy = 1.2 if nm!="STEERED-ROTATE" else 1.2
    axR.annotate(nm, (r['cost'], r['lat_mean']), xytext=(r['cost']+1.5, r['lat_mean']+dy),
                 fontsize=9.5, color=cols[nm], fontweight="bold")
# steered vs check-all callout
axR.annotate("", xy=(st['cost'], st['lat_mean']), xytext=(ca['cost'], ca['lat_mean']),
             arrowprops=dict(arrowstyle="->", color="#888", ls="--", lw=1.3))
axR.text( (st['cost']+ca['cost'])/2 - 6, (st['lat_mean']+ca['lat_mean'])/2 + 1.5,
          f"{ca['cost']/st['cost']:.0f}× cheaper,\nnearly same latency", fontsize=8.6, color="#555")
axR.set_xlabel("verification cost per step (eyes checked)")
axR.set_ylabel("mean detection latency (steps)")
axR.set_title("Cost vs responsiveness\nsteering ≈ check-all's latency at the blind wheel's cost")
axR.set_xlim(0, N+6); axR.grid(alpha=0.25)

fig.suptitle("A rotating ring of truths: hold many, verify the few at the gate — and steer the wheel to attend",
             fontsize=11.5)
fig.tight_layout(rect=[0,0,1,0.95]); fig.savefig("ring_of_truths.png", dpi=130)
print("\n  wrote ring_of_truths.png")
