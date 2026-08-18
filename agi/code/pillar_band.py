#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pillar_band.py -- core pillars are structural drag-handles; the observer sees only a finite
BAND at a distance, which caps storage; and similar memories blend in that band (days merge).

Jonathan: the CORE pillars are structural — we don't need to fill them in to understand them,
but if we have a memory of that truth we can fill it and build LAYERS of memories on them.
Those core pillars are what we push up and down, and the rest of the pillars get DRAGGED. The
observer has a DISTANCE where it can see — a band — so memories have to poke INTO that range;
that gives a LIMIT on how much can be stored (they can't poke in too far). Filled pixels build
the layers when they overlap and must ALIGN in that range when dragged by the core pillar —
which is like days blending together: the blended pillars hold a lot of similar stuff (the
rooms) but picking out one specific day is hard.

Grounded — the corpus derives exactly this:
  * Shovelcat_10_1 §7.4.2/§7.4.3 — from observer depth α=d/8 the VISIBLE Z-RANGE resolves only
    N_visible ≈ 3.5 levels, and the vesica overlap holds N_bins ≈ 4 distinguishable bins of the
    info-quantum ~0.159 (≈ the .14). A finite band and a finite bin count = a hard capacity, set
    by depth. "Beyond θ=φ requires observer intervention" = can't poke in past the reach.
  * SPARSE_VESICA §7.3 — a gap CERTIFIES necessity and LOCATION but does not supply the
    content: the core pillar is structural (understood by position) and only optionally filled.
  * SPARSE_VESICA §23.2 — recall by reinstating the context (the room/anchor), then reading what
    fits; FOLDING_HANDSHAKE §4.2 waterline (surface visible / column buried).
  * Nautilus chambers (Shovelcat_10_1 §7.5) scaled by φ^½ = the rooms.

MEASURED:
  (1) FINITE BAND → CAPACITY — memories are retrievable only while they poke into the band and
      within reach; retrievable count saturates at a reach/band capacity (can't store past it).
  (2) CORE PILLAR DRAGS ITS LAYERS — recall by lifting the structural anchor into the band
      succeeds where direct off-band address fails, and brings the neighboring context with it.
  (3) DAYS BLEND — as similar episodes pile on one anchor, the GIST (room) sharpens while
      per-INSTANCE (which day) discrimination collapses.
"""
import numpy as np
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

rng = np.random.default_rng(11)

# observer geometry (in "levels"); tuned so the band ≈ the corpus's 3–4 visible levels
DZ   = 1.0          # level spacing
B0   = 2.0          # observer standoff distance (nearest visible level)
BW   = 4.0          # band width ≈ N_visible / N_bins ≈ 3.5–4  (Shovelcat_10_1 §7.4)
LMAX = 8.0          # how far a core pillar can be lifted (reach)
band_slots  = int(round(BW/DZ))                    # ~4 : visible at once
reach_depth = LMAX + B0 + BW                        # deepest layer still liftable into the band
capacity    = int(round(reach_depth/DZ))            # total storable-and-retrievable

# ---- (1) finite band → capacity ----
stored = np.arange(1, 32)
retrievable = np.minimum(stored, capacity)
print("="*76)
print("  A FINITE OBSERVER BAND CAPS STORAGE; CORE PILLARS DRAG; SIMILAR MEMORIES BLEND")
print("="*76)
print(f"  observer band = {band_slots} levels visible at once (≈ the corpus's N_visible≈3.5 / N_bins≈4);")
print(f"  a core pillar reaches {LMAX:.0f} levels, so the deepest retrievable layer is {capacity} down.")
print(f"  (1) storage saturates: retrievable = min(stored, {capacity}); memories past reach can't poke in.")
print()

# ---- (2) core pillar drags its layers into the band ----
DEPTHS = np.arange(0, 20)                            # a stack of layers on one core pillar
T = 4000
targets = rng.integers(0, len(DEPTHS), T)
def in_band(depth, lift):
    z = depth - lift
    return (z >= B0) & (z <= B0+BW)
direct = np.mean([in_band(d, 0.0) for d in targets])                       # no lift (address it where it lies)
# anchor-drag: choose the lift that puts the target mid-band, if within reach
def drag_success(d):
    lift = d - (B0 + BW/2)                          # center the target in the band
    if lift < 0: lift = 0.0                          # can't push it below the observer
    if lift > LMAX: return False, 0                  # beyond reach — buried
    ok = in_band(d, lift)
    # context: how many OTHER layers land in the band at this same lift
    ctx = np.sum([in_band(dd, lift) for dd in DEPTHS]) - (1 if ok else 0)
    return bool(ok), int(ctx)
res = [drag_success(d) for d in targets]
drag = np.mean([r[0] for r in res])
ctx  = np.mean([r[1] for r in res if r[0]])
print(f"  (2) recall by the CORE PILLAR (drag it into the band) vs direct address:")
print(f"        direct (read it where it lies) : {direct*100:4.0f}%  (only the few already in the band)")
print(f"        drag the anchor into the band  : {drag*100:4.0f}%  (any layer within reach; deeper ones lost)")
print(f"        context brought along          : {ctx:.1f} neighbouring layers surface with it")
print(f"     -> you recall by grabbing the structural pillar (the room), not the lone memory — and its")
print(f"        neighbours come too. Layers beyond reach stay buried (the capacity limit again).")
print()

# ---- (3) days blend: gist sharpens, instance discrimination collapses ----
D = 3                                                # feature dimensions of an episode ("a day")
JIT = 1.0                                            # within-room variation between days (similar days)
NOISE = 0.9                                          # recall-cue noise
Ks = np.array([1,2,3,5,8,12,18,25,35,50])
TR = 400
gist_err = []; inst_acc = []
for K in Ks:
    ge=[]; ia=[]
    for _ in range(TR):
        c = rng.normal(0, 3, D)                      # the room centroid
        eps = c + rng.normal(0, JIT, (K, D))         # K similar days in that room
        ge.append(np.linalg.norm(eps.mean(0) - c))   # gist = estimate the room
        i = rng.integers(K)
        cue = eps[i] + rng.normal(0, NOISE, D)        # a noisy cue for one specific day
        pick = np.argmin(((eps-cue)**2).sum(1))       # nearest stored day
        ia.append(pick == i)
    gist_err.append(np.mean(ge)); inst_acc.append(np.mean(ia))
gist_err = np.array(gist_err); inst_acc = np.array(inst_acc)
print(f"  (3) DAYS BLEND (many similar episodes on one anchor):")
print(f"        gist (recall the ROOM)      : error {gist_err[0]:.2f} at 1 day → {gist_err[-1]:.2f} at {Ks[-1]} days  (sharpens)")
print(f"        instance (which specific DAY): {inst_acc[0]*100:3.0f}% at 1 → {inst_acc[-1]*100:3.0f}% at {Ks[-1]}  (collapses)")
print(f"     -> the overlapping layers AVERAGE into a strong room/schema, but the individual day is")
print(f"        lost in the blend — exactly 'days blending together; the room is clear, the day is hard.'")

# ---------------------------------------------------------------------------
# PLOT
# ---------------------------------------------------------------------------
fig = plt.figure(figsize=(14.6, 5.2))
gs = fig.add_gridspec(1, 3, wspace=0.34)

# (A) capacity
axA = fig.add_subplot(gs[0,0])
axA.plot(stored, retrievable, "-o", color="#2b6cb0", lw=2, ms=3.5)
axA.axhline(capacity, color="#c0392b", ls="--", lw=1.3)
axA.text(1, capacity+0.4, f"reach cap = {capacity} (can't poke past)", color="#c0392b", fontsize=8.5)
axA.axhspan(0, band_slots, color="#4a90d0", alpha=0.12)
axA.text(20, band_slots-0.6, f"{band_slots} visible at once (the band)", color="#2b6cb0", fontsize=8.5, ha="right")
axA.set_xlabel("memories stored on a pillar"); axA.set_ylabel("retrievable")
axA.set_title("Finite band + reach = a storage cap\n(observer sees ~4 levels; can't poke in too far)", fontsize=10.2)

# (B) drag
axB = fig.add_subplot(gs[0,1])
b = axB.bar(["direct\naddress","drag the\ncore pillar"], [direct*100, drag*100],
            color=["#8892a0","#238b45"], edgecolor="#111")
axB.set_ylabel("recall success (%)"); axB.set_ylim(0,100)
axB.set_title(f"Core pillar is the drag-handle\n(brings {ctx:.0f} neighbours of context along)", fontsize=10.2)
for r,v in zip(b,[direct*100,drag*100]): axB.text(r.get_x()+r.get_width()/2, v+2, f"{v:.0f}%", ha="center", fontsize=9)

# (C) days blend
axC = fig.add_subplot(gs[0,2])
room_recall = 1 - gist_err/gist_err[0]               # rises: the room gets clearer with more days
axC.plot(Ks, room_recall, "-o", color="#238b45", lw=2, ms=4, label="room (gist) — recalled better ↑")
axC.plot(Ks, inst_acc, "-o", color="#c0392b", lw=2, ms=4, label="specific day (instance) — lost ↓")
axC.set_xlabel("similar episodes stacked on one anchor (days)")
axC.set_ylabel("recall quality (normalised)")
axC.set_title("Days blend together\nroom sharpens, the specific day is lost", fontsize=10.2)
axC.legend(fontsize=8, framealpha=0.92, loc="center right")
axC.set_ylim(0,1.05)

fig.suptitle("Core pillars are structural drag-handles · the observer's finite band caps storage · similar memories blend into rooms",
             fontsize=10.8)
fig.savefig("pillar_band.png", dpi=130, bbox_inches="tight")
print("\n  wrote pillar_band.png")
