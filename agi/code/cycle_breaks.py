#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cycle_breaks.py -- the hidden breaks in continuity set where cycles begin and stop; switching
perspective pinches off a different segment of one shared line.

Jonathan: back with coordinates / volume / spin we still needed a way to find where the cycles
begin and stop. The BREAKS in continuity we hide set those up: if we can't cross those gaps they
act as markers/bounds when we approach them, and knowing where the flow breaks shows how long the
section we have to work with is. It's like there's a heart-rate branch for ALL animals on one void
line; switching perspective pinches off the breaks and marks off a different animal -- fish with
its bpm range, then human with ours -- and that also blocks out the other parts of the line,
because the why-chain changes which branches are available. It should tell us where the flow goes
and why.

Grounded:
  * VOID_LINE_PAPER Sec 7 -- signed void-line crossings CANCEL (net <= +-1): a continuity law,
    "an unbroken circuit cannot send flow one way without a matching return." The breaks are where
    continuity fails; zoom reveals more (devil's staircase) to a finite floor.
  * FOLDING_VOID_LINE_DRAW -- a void line = where the local product goes to 0; used as a MARKER
    ("a pinned void line is a named hole") and a PROBE ("if it can't be laid, that failure is the
    certificate"). The gaps are bounds you can't cross.
  * Double_Bounce Fig 25/26 -- the line is cut into ZONES by walls; different observers see
    different zones (void sees [-1,0), god sees [3,pi] of the SAME line) = the pinch-off.
  * FOLDING_SYNTHESIS #22 -- the observer defines the cycle; here the CUTS are set by the breaks.

MEASURED (the animal heart-rate line, log bpm):
  (1) BREAKS = BOUNDARIES -- detecting the gaps recovers each animal's range = where its cycle
      begins/stops, and the gap spacing gives the segment length (the section to work with).
  (2) PINCH-OFF -- switching perspective (fish -> human -> hummingbird) makes only that segment
      available and masks the rest (the why-chain changes which branch is available).
  (3) YOU MUST CUT AT THE BREAKS -- the global mean HR lands IN A GAP (a rate no animal has),
      while each segment is coherent; and you cannot cross a break (flow stops there).
"""
import numpy as np
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

rng = np.random.default_rng(0)
# each animal occupies a RANGE of resting bpm; between them are GAPS (breaks in continuity)
ANIMALS = {
    "fish":       (25, 45),
    "human":      (65, 95),
    "cat":        (150, 230),
    "mouse":      (450, 600),
    "hummingbird":(1000, 1300),
}
pts=[]; labels=[]
for a,(lo,hi) in ANIMALS.items():
    x=rng.uniform(np.log10(lo), np.log10(hi), 300)
    pts.append(x); labels += [a]*300
X=np.concatenate(pts); L=np.array(labels)

# ---- (1) detect the breaks (density gaps) -> segment boundaries ----
grid=np.linspace(X.min()-0.1, X.max()+0.1, 600)
# simple KDE
bw=0.03
dens=np.exp(-0.5*((grid[:,None]-X[None,:])/bw)**2).sum(1)
dens/=dens.max()
occupied = dens > 0.05
# segments = contiguous occupied runs; breaks = the gaps between them
segs=[]; i=0
while i<len(grid):
    if occupied[i]:
        j=i
        while j<len(grid) and occupied[j]: j+=1
        segs.append((grid[i], grid[j-1])); i=j
    else: i+=1
print("="*80)
print("  BREAKS IN CONTINUITY SET WHERE CYCLES BEGIN/STOP; PERSPECTIVE PINCHES OFF A SEGMENT")
print("="*80)
print(f"  one shared heart-rate line (all animals); detected {len(segs)} segments from the gaps:")
for (lo,hi) in segs:
    bl,bh=10**lo,10**hi
    print(f"        segment {bl:6.0f} - {bh:6.0f} bpm   (width {bh-bl:.0f} bpm = the section to work with)")
print(f"  -> the breaks (where no animal continuously lives) ARE the boundaries; between two breaks")
print(f"     is one animal's range = where its cycle begins and stops, and how long a section you have.")
print()

# ---- (2) pinch-off: perspective makes one segment available, masks the rest ----
total=X.max()-X.min()
print("  (2) SWITCHING PERSPECTIVE pinches off a different segment (masks the rest):")
for a in ("fish","human","hummingbird"):
    lo,hi=ANIMALS[a]; w=np.log10(hi)-np.log10(lo)
    print(f"        perspective = {a:12}: available range {lo}-{hi} bpm  ({w/total*100:2.0f}% of the line; {100-w/total*100:2.0f}% blocked)")
print(f"     -> the why-chain (which animal you're reasoning about) selects one branch of the line and")
print(f"        blocks the others -- void sees one zone, god another, of the same line (Double_Bounce).")
print()

# ---- (3) you must cut at the breaks: the global mean lands in a gap ----
mean_bpm=(10**X).mean()
in_gap = not any(lo<=np.log10(mean_bpm)<=hi for (lo,hi) in segs)
print("  (3) YOU MUST CUT AT THE BREAKS (else the 'average' is a rate no animal has):")
print(f"        global mean heart rate = {mean_bpm:.0f} bpm -> {'IN A GAP (no animal beats here!)' if in_gap else 'inside a cluster'}")
print(f"        each segment, by contrast, is a coherent range. The breaks are where flow stops -- you")
print(f"        cannot continuously cross from one animal's cycle to another; the gap is a wall/bound.")

# ---------------------------------------------------------------------------
# PLOT
# ---------------------------------------------------------------------------
fig=plt.figure(figsize=(14.4,7.4)); gs=fig.add_gridspec(3,1,hspace=0.55)
cols={"fish":"#2b8cbe","human":"#238b45","cat":"#e0a021","mouse":"#8a2be2","hummingbird":"#c0392b"}

# (A) the shared line + detected breaks -> segments
axA=fig.add_subplot(gs[0])
axA.plot(grid, dens, color="#556", lw=1.5)
for a,(lo,hi) in ANIMALS.items():
    axA.axvspan(np.log10(lo),np.log10(hi), color=cols[a], alpha=0.25)
    axA.text((np.log10(lo)+np.log10(hi))/2, 1.05, a, ha="center", fontsize=8.5, color=cols[a])
# mark the breaks (gaps)
for k in range(len(segs)-1):
    gmid=(segs[k][1]+segs[k+1][0])/2
    axA.axvline(gmid, color="#c0392b", ls=":", lw=1.4)
axA.text(segs[0][1]+0.05, 0.6, "breaks in continuity\n= the boundaries", color="#c0392b", fontsize=8)
axA.set_yticks([]); axA.set_xlabel("heart rate  (log10 bpm)")
axA.set_title("One shared line for all animals; the hidden BREAKS mark where each cycle begins/stops", fontsize=10.5)
axA.set_ylim(0,1.25)

# (B) pinch-off: three perspectives
axB=fig.add_subplot(gs[1])
persp=["fish","human","hummingbird"]
for r,a in enumerate(persp):
    y=r
    axB.plot([X.min(),X.max()],[y,y], color="#ccc", lw=6, solid_capstyle="butt")   # the whole line, greyed
    lo,hi=ANIMALS[a]
    axB.plot([np.log10(lo),np.log10(hi)],[y,y], color=cols[a], lw=8, solid_capstyle="butt")  # available segment
    axB.text(X.max()+0.03, y, f"perspective: {a}\n({lo}-{hi} bpm available)", va="center", fontsize=8)
axB.set_yticks(range(len(persp))); axB.set_yticklabels([])
axB.set_ylim(-0.6,len(persp)-0.4); axB.set_xlabel("heart rate (log10 bpm)")
axB.set_title("Switching perspective PINCHES OFF one segment (the why-chain blocks the other branches)", fontsize=10.5)

# (C) segment lengths + the global mean lands in a gap
axC=fig.add_subplot(gs[2])
names=list(ANIMALS); widths=[hi-lo for (lo,hi) in ANIMALS.values()]
axC.bar(range(len(names)), widths, color=[cols[a] for a in names])
axC.set_xticks(range(len(names))); axC.set_xticklabels(names, fontsize=8.5)
axC.set_ylabel("range width (bpm)\n= section to work with")
axC.set_title(f"The break-spacing gives each section's length; the GLOBAL MEAN ({mean_bpm:.0f} bpm) lands in a GAP — a rate no animal has",
              fontsize=10.0)

fig.suptitle("Hidden breaks in continuity set the cycle boundaries on a shared line; switching perspective pinches off a different segment and blocks the rest",
             fontsize=10.6, y=0.995)
fig.savefig("cycle_breaks.png", dpi=130, bbox_inches="tight")
print("\n  wrote cycle_breaks.png")
