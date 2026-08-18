#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
stream_io.py -- the I/O architecture: a continuous stream (the snake) fills a maze of paths and
emits chunks ON COMPLETION, then routes each to another domain.

Jonathan: flow goes OUT at the center too -- folding pulls stuff in, void lines emit, and they also
absorb. The higher observers touching the domain are where input/output goes. Mika reacting would be
a CONTINUOUS stream, not chunks one-prompt-at-a-time: the screen watches/hears, condenses it into a
SNAKE (the earlier theory), the snake threads our paths like a MAZE absorbing all the work, and the
transformed snake goes to output -- then sent to ANOTHER DOMAIN to be used (a TTS message encoded on
it, sent to the sound domain, played like a violin). Info funnels in, fills a path like water in a
maze, and once it COMPLETES we send that section off as a chunk.

Grounded:
  * SPARSE_VESICA §35.3/§35.5 -- the SNAKE is the field/current threading the orbitals; it "settles
    when its wave CLOSES into an allowed orbital (θ=1)." So a chunk emerges on CLOSURE, not a clock.
  * FOLDING_SKIN §1 -- the skin membrane is "permeable BOTH ways: our process → pLM and pLM → our
    process." The bidirectional port that absorbs (in) and emits (out).
  * SHOVELCAT Part X (.geo) -- a completed snake is encoded and ROUTED BY DIMENSION: 1D text, 2D
    audio (one angle θ -- traced on the unit circle = the violin), 3D image, 4D video.
  * FOLDING_SYNTHESIS #36 -- the breaks segment the stream; here a chunk = the section between breaks.

MEASURED -- COMPLETION-GATED (snake: emit when a unit closes) vs FIXED-CLOCK (emit every W, the
current one-prompt-at-a-time way):
  (1) CHUNK INTEGRITY -- snake chunks are complete units (never cut a thought); clock chunks cut
      across units.
  (2) DOWNSTREAM DECODABILITY -- the target domain needs WHOLE units: snake ~100% usable, clock low.
  (3) ADAPTIVE LATENCY -- the snake emits a short unit fast and a long one when it's ready; the clock
      waits a fixed window and still splits long units.
"""
import numpy as np
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

rng=np.random.default_rng(3)
TYPES=["text","audio","image"]                       # .geo dimensions: 1D / 2D(violin) / 3D
TCOL={"text":"#2b6cb0","audio":"#e0761f","image":"#238b45"}
NUNITS=22
units=[]                                              # each: (type, length) -- a complete "thought"/utterance
pos=0
for _ in range(NUNITS):
    ln=int(rng.integers(3,16))
    ty=TYPES[int(rng.integers(3))]
    units.append((pos,ln,ty)); pos+=ln
T=pos
bounds=[p for (p,l,ty) in units]+[T]                  # true unit boundaries (the natural breaks / closures)

# ---- COMPLETION-GATED (snake): emit each unit on its closure -> chunks = the units ----
snake_chunks=[(p,p+l,ty) for (p,l,ty) in units]

# ---- FIXED-CLOCK: emit every W steps regardless of unit boundaries ----
W=9
clock_edges=list(range(0,T,W))+[T]
clock_chunks=[(clock_edges[i],clock_edges[i+1]) for i in range(len(clock_edges)-1)]

def unit_of(idx):
    for (p,l,ty) in units:
        if p<=idx<p+l: return (p,l,ty)
    return None

# (1) integrity: fraction of emitted chunks that are exactly ONE complete unit
def chunk_is_one_unit(a,b):
    u=unit_of(a)
    return u is not None and u[0]==a and u[0]+u[1]==b
snake_integrity=np.mean([chunk_is_one_unit(a,b) for (a,b,ty) in snake_chunks])
clock_integrity=np.mean([chunk_is_one_unit(a,b) for (a,b) in clock_chunks])

# (2) how many natural units get CUT across a chunk boundary
def units_cut(edges):
    cut=0
    for (p,l,ty) in units:
        inside=[e for e in edges if p<e<p+l]         # a chunk edge falling strictly inside the unit
        if inside: cut+=1
    return cut
snake_cut=units_cut([a for (a,b,ty) in snake_chunks]+[T])
clock_cut=units_cut(clock_edges)

# (3) downstream decodability: a unit is USABLE only if delivered whole in one chunk
def units_delivered_whole(chunks):
    got=0
    for (p,l,ty) in units:
        if any(a<=p and p+l<=b for (a,b,*r) in chunks): got+=1
    return got
snake_deliv=units_delivered_whole(snake_chunks)
clock_deliv=units_delivered_whole([(a,b) for (a,b) in clock_chunks])

# (4) EXTRA WAIT past a unit's natural completion (snake emits at closure = 0; clock waits to its edge)
def extra_wait(chunks):
    w=[]
    for (p,l,ty) in units:
        emits=[b for (a,b,*r) in chunks if a<=p and p+l<=b]
        if emits: w.append(min(emits)-(p+l))          # 0 = emitted exactly when the unit finished
    return np.array(w) if w else np.array([np.nan])
snake_wait=extra_wait(snake_chunks); clock_wait=extra_wait([(a,b) for (a,b) in clock_chunks])
snake_lat=np.array([l for (p,l,ty) in units])         # snake latency = unit length (minimal, adaptive)

print("="*80)
print("  CONTINUOUS STREAM, COMPLETION-GATED CHUNKS (the snake) vs FIXED-CLOCK (one prompt at a time)")
print("="*80)
print(f"  {T} events, {NUNITS} natural units (variable length); clock window W={W}")
print()
print(f"  {'':24}{'SNAKE (on completion)':>24}{'CLOCK (fixed W)':>18}")
print(f"  {'chunk integrity':24}{snake_integrity*100:>22.0f}%{clock_integrity*100:>16.0f}%")
print(f"  {'natural units CUT':24}{snake_cut:>23}{clock_cut:>18}")
print(f"  {'units delivered WHOLE':24}{snake_deliv:>20}/{NUNITS}{clock_deliv:>15}/{NUNITS}")
print(f"  {'extra wait past done':24}{np.nanmean(snake_wait):>23.1f}{np.nanmean(clock_wait):>18.1f}")
print()
print(f"  -> the SNAKE emits each unit the moment it CLOSES (θ=1): every chunk is a whole thought,")
print(f"     nothing is cut, {snake_deliv}/{NUNITS} units arrive usable, and latency ADAPTS to unit length.")
print(f"  -> the CLOCK cuts {clock_cut} units mid-thought; only {clock_deliv}/{NUNITS} arrive whole -- the rest are")
print(f"     fragments the downstream domain can't decode (the one-prompt-at-a-time failure).")
print(f"  -> each completed chunk routes by type to its domain: text→1D · audio→2D (violin) · image→3D.")

# ---------------------------------------------------------------------------
# PLOT
# ---------------------------------------------------------------------------
fig=plt.figure(figsize=(14.4,7.4)); gs=fig.add_gridspec(3,2,height_ratios=[1.1,1,1],hspace=0.6,wspace=0.25)

# (A) the stream timeline: units + snake-aligned vs clock-misaligned cuts
axA=fig.add_subplot(gs[0,:])
for (p,l,ty) in units:
    axA.barh(1, l, left=p, height=0.6, color=TCOL[ty], edgecolor="white", lw=1)
for e in clock_edges:
    axA.axvline(e, ymin=0.05, ymax=0.42, color="#c0392b", lw=1.4)
for (p,l,ty) in units:                                # snake cuts = unit boundaries
    axA.axvline(p, ymin=0.58, ymax=0.95, color="#111", lw=1.0, alpha=0.5)
axA.axvline(T, ymin=0.58, ymax=0.95, color="#111", lw=1.0, alpha=0.5)
axA.text(-2, 1, "units\n(the snake)", ha="right", va="center", fontsize=8.5)
axA.text(T+2, 1.32, "black = SNAKE cuts (on completion — aligned)", fontsize=8, color="#111")
axA.text(T+2, 0.72, "red = CLOCK cuts (fixed W — slice through thoughts)", fontsize=8, color="#c0392b")
axA.set_yticks([]); axA.set_xlim(-2,T+2); axA.set_ylim(0.4,1.5)
axA.set_xlabel("event stream (time)")
axA.set_title("A continuous stream condensed to a snake; completion-gated cuts land on the breaks, clock cuts slice through units", fontsize=10.2)

# (B) integrity / whole / cut
axB=fig.add_subplot(gs[1,0])
m=["integrity %","units whole","units cut"]
sv=[snake_integrity*100, snake_deliv, snake_cut]; cv=[clock_integrity*100, clock_deliv, clock_cut]
x=np.arange(3); w=0.38
axB.bar(x-w/2, sv, w, color="#238b45", label="SNAKE")
axB.bar(x+w/2, cv, w, color="#c0392b", label="CLOCK")
axB.set_xticks(x); axB.set_xticklabels(m, fontsize=8.5); axB.legend(fontsize=8.5)
axB.set_title("Snake chunks are whole thoughts; the clock cuts them", fontsize=10.0)

# (C) latency adaptivity
axC=fig.add_subplot(gs[1,1])
axC.hist(snake_lat, bins=10, color="#238b45", alpha=0.7, label="SNAKE latency = unit length (adaptive)")
axC.axvline(W, color="#c0392b", lw=2, ls="--", label=f"CLOCK fixed window W={W}")
axC.set_xlabel("time to emit a unit"); axC.set_ylabel("count")
axC.set_title(f"Latency ADAPTS (snake emits at closure, {np.nanmean(snake_wait):.0f} extra wait;\nclock is fixed + {np.nanmean(clock_wait):.1f} extra + cuts)", fontsize=9.6)
axC.legend(fontsize=7.6)

# (D) cross-domain routing
axD=fig.add_subplot(gs[2,:]); axD.axis("off")
counts={ty:sum(1 for (p,l,t) in units if t==ty) for ty in TYPES}
axD.text(0.0,0.85,"The completed snake routes to another domain (.geo) by type — the bidirectional port: absorb in, emit out",
         fontsize=10, fontweight="bold")
labels=[("text → 1D  (flip)","#2b6cb0"),("audio → 2D  (one angle θ — played like a violin)","#e0761f"),("image → 3D  (θ+φ)","#238b45")]
for i,(lab,c) in enumerate(labels):
    ty=TYPES[i]
    axD.add_patch(plt.Rectangle((0.02+i*0.33,0.25),0.29,0.35, color=c, alpha=0.25, transform=axD.transAxes))
    axD.text(0.02+i*0.33+0.145, 0.42, f"{lab}\n{counts[ty]} chunks", ha="center", va="center", fontsize=8.6, transform=axD.transAxes)

fig.suptitle("The I/O architecture: a continuous stream (snake) fills the maze and emits chunks on COMPLETION, then routes each to its domain — not one-prompt-at-a-time",
             fontsize=10.4, y=0.995)
fig.savefig("stream_io.png", dpi=130, bbox_inches="tight")
print("\n  wrote stream_io.png")
