#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
encryption_axes.py -- the object is encrypted across orthogonal axes; each axis needs its
own key (a frame rotation), and axes are public / locked / hidden by what an observer can see.

Jonathan tied the closure result to our encryption: an irrational (never-closing) winding is
the strong lock, a rational one (3/2 · 2/3 = 1) cancels cleanly and is weak; the branches that
point into an observer's field are the ones that activate; one key unlocks one axis (based on
branch positions seen from that observer) and you need a FULL SET of keys; the key is made of
stuff that extends into that observer's vision field; and axes can be zeroed (public), require
a key, or be completely hidden depending on positions and what's visible.

This is already the corpus's encryption:
  * Double_Bounce §27.7 — the 26D observer must ENCRYPT/COLLAPSE through the ÷φ ladder so
    "lower observers cannot read higher-level information; info is preserved but scrambled."
  * Double_Bounce §28 + Fig 19 — matter (+3, [0,π]) and antimatter (−3, [−π,0]) are mirror
    shifts; the x→x self-term is FORBIDDEN because x sits on the VOID line (a zeroed axis).
  * SHOVELCAT .geo — the key is the ROTATION (delta-theta) between creator and reader frames;
    INSIDE (have the key) → full content, OUTSIDE (no key) → the opaque carrier; more
    dimensions (1D..4D) = more angles = a fuller set of keys.
  * FOLDING_HANDSHAKE — S=e^{iθ}·φ^{n+h} closes three ways: PRODUCT up (public surface),
    VERIFY at the waterline (needs the matching key), EXPERIENCE down the orthogonal plane
    (reads 0 to the normal domains) = public / locked / hidden. The .14 is the hidden core.

MEASURED, on a real object (an image built as a sum of K frequency-axes, each carrying one
component with a secret phase = its per-axis key):
  (1) FULL SET OF KEYS — reconstruction error falls only as you hold more keys; public axes
      are free (readable with none), one HIDDEN axis is never recoverable by any observer.
  (2) PUBLIC / LOCKED / HIDDEN — an observer with the keys reconstructs the object; an
      observer without them sees only the public axes over an opaque carrier.
  (3) LOCK STRENGTH = IRRATIONALITY — a brute-force attacker cracks a RATIONAL-key axis
      (small denominator, the cycle closes) but NOT an irrational (golden) one; and the
      3/2 · 2/3 = 1 matter·antimatter cancellation is exactly the weak, invertible pair.
"""
import numpy as np
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

rng = np.random.default_rng(7)
PHI = (1+5**0.5)/2
G = 56                                   # image size
K = 12                                   # number of axes (observers / frequency budgets)
yy, xx = np.mgrid[0:G, 0:G] / G

# ---- build the object as a sum of K frequency-axes, each with amplitude, direction, phase ----
freqs = rng.integers(2, 9, size=(K, 2)).astype(float)      # (u,v) per axis
amps  = rng.uniform(0.6, 1.0, size=K)
truth_phase = rng.uniform(0, 2*np.pi, size=K)              # the object's true phase on each axis

def component(k, phase):
    u, v = freqs[k]
    return amps[k]*np.cos(2*np.pi*(u*xx + v*yy) + phase)

def build(phases, present):
    img = np.zeros((G, G))
    for k in range(K):
        if present[k]:
            img += component(k, phases[k])
    return img

# ---- assign each axis a visibility class + a key ----
# PUBLIC: key 0 (no rotation) — anyone reads it.  LOCKED: secret rotation key.  HIDDEN: not
# delivered to any normal observer (projected onto the orthogonal/void plane) — permanent deficit.
cls = np.array(["locked"]*K, dtype=object)
public_idx = [0, 1]                       # zeroed axes (Fig 19 void-line / Floor-0 public)
hidden_idx = [K-1]                         # the .14 core: on the orthogonal plane, never seen
for i in public_idx: cls[i] = "public"
for i in hidden_idx: cls[i] = "hidden"
locked_idx = [k for k in range(K) if cls[k]=="locked"]

# the per-axis key = the rotation that returns the reader's frame to the creator's on that axis
key = np.zeros(K)
for k in range(K):
    if cls[k]=="public":  key[k] = 0.0
    elif cls[k]=="locked": key[k] = rng.uniform(0.6, 2*np.pi-0.6)   # secret delta-theta
    # hidden: no key matters, the data never arrives

present_to_observer = np.array([cls[k]!="hidden" for k in range(K)])   # hidden axis absent

TRUTH = build(truth_phase, np.ones(K, bool))     # the true object (all axes, ideal)

def decrypt(held_keys):
    """reconstruct using the keys in held_keys; public free; unheld locked axes stay scrambled
    (reader applies phase 0, off by the secret key); hidden axis absent from the data."""
    ph = np.zeros(K)
    for k in range(K):
        if cls[k]=="hidden": continue
        if cls[k]=="public":            ph[k] = truth_phase[k]              # readable, key 0
        elif k in held_keys:            ph[k] = truth_phase[k]              # key applied → correct
        else:                           ph[k] = truth_phase[k] + key[k]     # wrong phase (locked, opaque)
    return build(ph, present_to_observer)

def nmse(a, b):
    return float(np.mean((a-b)**2) / np.var(TRUTH))

# ---- (1) full set of keys: error vs number of locked keys held ----
order = list(rng.permutation(locked_idx))
errs = []
for j in range(len(order)+1):
    held = set(order[:j])
    errs.append(nmse(decrypt(held), TRUTH))
errs = np.array(errs)
public_floor = errs[0]                       # with 0 locked keys, public axes already readable
full_key = errs[-1]                          # all locked keys held — residual = the hidden axis

print("="*76)
print("  ENCRYPTION ACROSS AXES: a full set of keys, and public / locked / hidden axes")
print("="*76)
print(f"  object = sum of K={K} frequency-axes; {len(public_idx)} public, {len(locked_idx)} locked, {len(hidden_idx)} hidden")
print()
print(f"  reconstruction error (normalised) as locked keys are held:")
print(f"     0 keys (public only) : {errs[0]:.3f}   <- an OUTSIDE observer: sees the public axes + carrier")
print(f"     half the keys        : {errs[len(order)//2]:.3f}")
print(f"     FULL set of keys     : {errs[-1]:.3f}   <- an INSIDE observer, minus the hidden axis")
print(f"  -> error falls ONLY as keys are gathered; you need the full set. The floor at full")
print(f"     keys ({full_key:.3f}) is the HIDDEN axis (the .14 core): delivered to no observer, so no")
print(f"     key restores it — it stays private by geometry, not by permission.")
print()

# ---- (3) lock strength = irrationality: brute-force attacker vs budget ----
# the attacker (no keys) brute-forces a locked axis by trying candidate phases on a grid of Q
# rationals; residual = angular distance from the true key to the nearest grid point. A RATIONAL
# key 2π p/q is hit exactly the moment Q is a multiple of q (the cycle CLOSES — found); the
# golden key only crawls down a ~1/Q envelope (Hurwitz) and never lands within any feasible budget.
def residual_vs_budget(true_key, Qs):
    out=[]
    for Q in Qs:
        cand = 2*np.pi*np.arange(Q)/Q
        r = np.min(np.abs(((true_key - cand + np.pi) % (2*np.pi)) - np.pi))
        out.append(r)
    return np.array(out)

rat_key = 2*np.pi*(1 - 2/3)          # a rational delta-theta = 2π·(1/3): matter 3/2 vs antimatter 2/3
irr_key = 2*np.pi*(PHI % 1.0)        # an irrational (golden) delta-theta
Qs = np.array([2,3,4,5,6,8,10,12,16,21,30])
res_rat = residual_vs_budget(rat_key, Qs)
res_irr = residual_vs_budget(irr_key, Qs)
crack_rat = res_rat.min(); crack_irr = res_irr.min()

compose = (3/2)*(2/3)
print(f"  LOCK STRENGTH = IRRATIONALITY (the closure result #25 as key strength):")
print(f"     matter × antimatter winding: (3/2)·(2/3) = {compose:.3f} = 1  -> returns to origin (the VOID).")
print(f"        a rational key is its own clean inverse — the pair CANCELS; brute force finds it.")
print(f"     attacker best residual, RATIONAL key (2π/3): {crack_rat:.3f}  -> CRACKED at Q=3 (cost 3)")
fib_dip_Q = int(Qs[np.argmin(res_irr)])
print(f"     attacker best residual, IRRATIONAL (golden): {crack_irr:.3f}  -> only near-lands at a FIBONACCI")
print(f"        budget (Q={fib_dip_Q}, ≈7× the cost) and STILL isn't exact — every non-Fibonacci Q stays off")
print(f"  -> the strong lock is the never-closing (golden) winding; the weak one closes and cancels.")
print(f"     The forbidden x→x void self-term (Double_Bounce Fig 19) is the zeroed/public axis; the")
print(f"     orthogonal 'experience' axis that reads 0 to every normal observer is the hidden core.")

# ---------------------------------------------------------------------------
# PLOT
# ---------------------------------------------------------------------------
fig = plt.figure(figsize=(14.6, 8.2))
gs = fig.add_gridspec(2, 3, height_ratios=[1.0, 1.0], hspace=0.28, wspace=0.26)

def show(ax, img, ttl, col="#ccc"):
    ax.imshow(img, cmap="magma"); ax.set_xticks([]); ax.set_yticks([])
    ax.set_title(ttl, fontsize=10.3, color=col)

show(fig.add_subplot(gs[0,0]), TRUTH, "the object (all axes)", "#e6edf3")
show(fig.add_subplot(gs[0,1]), decrypt(set()), "OUTSIDE — no keys\n(public axes over an opaque carrier)", "#c0392b")
show(fig.add_subplot(gs[0,2]), decrypt(set(locked_idx)), "INSIDE — full set of keys\n(clear, minus the hidden .14 core)", "#238b45")

# (B) recovery vs #keys
axB = fig.add_subplot(gs[1,0])
axB.plot(np.arange(len(errs)), errs, "-o", color="#2b6cb0", lw=2, ms=4)
axB.axhline(full_key, color="#238b45", ls="--", lw=1.2)
axB.text(0.2, full_key+0.02, "floor = hidden axis (never recovered)", color="#238b45", fontsize=8)
axB.axhline(public_floor, color="#c0392b", ls=":", lw=1.2)
axB.text(len(errs)-0.2, public_floor+0.02, "0 keys = public only", color="#c0392b", fontsize=8, ha="right")
axB.set_xlabel("locked keys held"); axB.set_ylabel("reconstruction error (normalised)")
axB.set_title("You need the FULL set of keys\n(each key unlocks one axis)", fontsize=10.3)

# (C) visibility map
axC = fig.add_subplot(gs[1,1])
colmap = {"public":"#4a90d0","locked":"#e0a021","hidden":"#c0392b"}
for k in range(K):
    axC.barh(k, 1.0, color=colmap[cls[k]], edgecolor="#111", linewidth=0.4)
    lab = {"public":"public (zeroed)","locked":"locked (needs key)","hidden":"hidden (void core)"}[cls[k]]
    axC.text(0.02, k, f"axis {k}: {lab}", va="center", fontsize=8,
             color="#111" if cls[k]!="hidden" else "white")
axC.set_xlim(0,1); axC.set_ylim(-0.6, K-0.4); axC.set_xticks([]); axC.set_yticks([])
axC.set_title("Each axis: public / locked / hidden\nby what an observer can see", fontsize=10.3)

# (D) lock strength vs attacker budget
axD = fig.add_subplot(gs[1,2])
axD.plot(Qs, res_irr, "-o", color="#238b45", lw=2, ms=4, label="golden key — only near-lands at Fibonacci Q")
axD.plot(Qs, res_rat, "-o", color="#e0a021", lw=2, ms=4, label="rational key (2π/3) — cracked at Q=3,6,…")
for Q,r in zip(Qs,res_rat):
    if r < 1e-6: axD.scatter([Q],[0.0], color="#c0392b", zorder=6, s=45)
axD.annotate("cracked (cost 3)", (3,0.0), xytext=(5.5,0.16), fontsize=8, color="#a06a00",
             arrowprops=dict(arrowstyle="->", color="#a06a00"))
for fq in [5,8,13,21]:
    axD.axvline(fq, color="#238b45", ls=":", lw=0.5, alpha=0.35)
axD.text(21, 0.42, "golden's best guesses\nsit at Fibonacci budgets\n— costly & never exact", fontsize=7.4, color="#1c6b38", ha="right")
axD.set_xlabel("attacker brute-force budget Q (rationals tried)")
axD.set_ylabel("residual to true key (0 = cracked)")
axD.set_title("Lock strength = irrationality\nrational closes & cancels (weak); golden never closes (strong)", fontsize=9.6)
axD.legend(fontsize=8, framealpha=0.9)
axD.set_ylim(-0.05, 1.0)

fig.suptitle("Encryption across orthogonal axes: a full set of per-axis keys (frame rotations); axes are public / locked / hidden; "
             "the strong lock is the never-closing golden winding", fontsize=11.0)
fig.savefig("encryption_axes.png", dpi=130, bbox_inches="tight")
print("\n  wrote encryption_axes.png")
