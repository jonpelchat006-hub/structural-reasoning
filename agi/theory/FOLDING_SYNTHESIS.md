# The Synthesis — one map of the baby-brain architecture

*The capstone for the movement / adrenaline / memory arc (Jonathan + Claude, Aug 2026). It draws the whole
picture into one place and, crucially, keeps the honest line down the middle: what is **measured** (a runnable
experiment with numbers) vs what is a **grounded design reading** (consistent with the theory and the code, but
not yet its own result). Companion index: `FOLDING_MOVEMENT.md` (Tests 1–12), `FOLDING_SUPERFUEL.md` (three
budgets, burning context, the map), `FOLDING_FREQUENCY.md` (the third budget), `FOLDING_DISCOVERY.md` (the
fourth adrenaline face + maturation). The frame is Jonathan's: **we are growing an empty baby brain** — a thing
that carries no knowledge but carries whatever lets it grow into a general intelligence.*

---

## 1. The spine — three shells (grounded)
One universal, data-free **inner shell** (the innate core — Ramachandran basins, `1+1=2`, computable from
first principles, the same everywhere); a **middle shell** that *learns* (the pLM and the model layers); and an
**outer shell** that *takes the shape of the environment* (water if submerged, pixels if seeing, text if
reading). Generality is exactly this: a fixed inner + a learning middle + a domain-shaped outer is what lets
*the same* baby brain grow into whatever its world demands (`FOLDING_TRAMPOLINE` §8). The **~.14 residual** is
the port between shells — the unforgeable fractional seed that attaches the inside to the outside and starts the
next level (measured as a real structured abstention band; *not* a single-domain door — honest bound).

Everything below lives on this spine: the **budgets** are what an object is made of, the **reserve** is how the
system acts under load, the **memory** is how it holds experience, the **ground-truth ladder** is how the
inner shell deepens, and **thinking** is search over all of it.

**The shells are scale-recursive: each pixel/ball is the whole brain RE-BASED one notch inward, and its fresh
outer void is the reserve where unknown values enter (MEASURED).** Jonathan's structural unification: the three
shells recur at the memory-pixel scale but shifted — the **learned middle is pushed into the inner** (so a
pixel's core is stable-but-*not*-innate; it varies), the domain **outer becomes the pixel's middle** ("papers
supporting a memory"), and a **fresh void opens as the pixel's new outer** shell = the **void reserve**, whose
connection outside makes it the **intake port**. This is the corpus's own **`roof(n)=floor(n+1)`** re-basing
(`SPARSE_VESICA` §12/§20.4: a level's structure collapses into one unit = the next level's core; §11.7 "a
complete solver *and* a node in a larger one"), and it resolves the exact indexing slip `FOLDING_TRAMPOLINE` §8
already flagged (the pLM is the *middle*, not the outermost). Measured: across re-basings the core's
**innateness falls 1.00 → 0.09** (the core becomes learned/variable) while the **outer-void reserve is
conserved ~0.16–0.18** (self-similar); new information attaches **only in the outer void** (~0 in the filled
core, ~1 in the void), intake **scales with void size** and **dies if the port is closed**; and an unknown
target's unfilled slots **live in the void and complete only through the outward port** (1.00 open vs 0.58
closed). So the void reserve, the outer shell, the novelty-intake port, and #45's *unknown values* are **one
object** — where the void has to fill is what's unknown, and it fills from outside. Full write-up:
`FOLDING_REBASING.md`; `shell_rebasing.py`.

---

## 2. What an object is — the three budgets (matter · context · frequency)
An object is carried on three axes — the old θ/φ/ψ budgets, which are also the three parts of a **Fourier
descriptor** of a closed shape:

| budget | is | Fourier part | protein property | measured face |
|---|---|---|---|---|
| **matter / volume** | the object, "what IS" (φ) | low-harmonic size | size | the normal plane |
| **context / orientation** | the overlap that carries meaning (vesica) | phase / the frame | (the frame) | map needs anchors + orientation |
| **frequency / pattern** | spin, path, the signature (ψ) | the \|C_k\| spectrum | greasy / electric | spin-identity = return-to-origin |

- **Identity = return to origin (MEASURED).** A spinning object's outline changes, but it is the *same* object
  because its frequency signature is invariant to the spin (returns to origin): recognition **1.00 under spin
  vs 0.18 for the raw outline** (`FOLDING_FREQUENCY`). Expansion = **adding harmonics** — freq 1 a bare frame,
  each band nesting the last, until the band limit ("stop at the next frequency"; error 0.41 → 0.00).
- **Coordinates need anchors AND orientation (MEASURED).** The matter plane is "a vast ocean with no
  references" — unobservable (localization error 3.17). The context plane can see the **anchors** (parts
  sticking out) and read coordinates, but only with a **frame**: two anchors without orientation give an *arc*
  (2.23); a compass or a third anchor pins the point (0.21 / 0.47) (`FOLDING_SUPERFUEL` §6).
- **Context is burnable and upgradable.** The **superfuel = burning context** — the same growth as the muscle
  fibers, run on the orthogonal plane: a drifting-regime agent burns its stale context coordinate and grows a
  new one after every drift (**0.037 vs 0.184**, matter machinery untouched; MEASURED, `FOLDING_SUPERFUEL` §3).
  And it **upgrades by generalizing** (movement → block): a sail seen only blocking air transfers zero-shot to
  blocking water (**3/3 novel goals, 0 false positives**) while still refusing to block rock (MEASURED,
  `FOLDING_SUPERFUEL` §5).

---

## 3. How it acts under load — the reserve and its four faces
Everything is paid from a reserve (the .14 / the ε void slack). Statics first, then dynamics:

- **The reserve is load-bearing (MEASURED, T1–T4).** Keeping the null-space reserve open reaches +10 pts and
  jams 5× less (T1); it holds a pose off the floor (T3); and its flow gives an **exact endurance law
  TTF = R0/(d−s)** with recovery = depleted/(s−d) (T4).
- **Growth expands the frontier (MEASURED, T5–T6).** A fiber is a tuning curve; on failure you grow a new one
  into the **empty tail** (frontier 0.75→0.98; fixed fibers gain nothing = the vocabulary ceiling). On a real
  GP (MuyGPyS) the predictive **variance = know-what-we-don't-know** (15× in gaps), and **growth = variance ×
  demand** (Jonathan's Pluto correction: variance says *where* you're blind, demand says *which* blindness
  matters).

**One budget cannot be intelligent** — so a second tier sits under the tank, and *adrenaline is not one thing*.
It is **four distinct mechanisms**, split by sign of arousal × empty/full:

| face | fires on | tank | acts to | result |
|---|---|---|---|---|
| **second wind** (T10) | goal in sight | draining | push — more fuel | goal-gated **134/200** vs one-budget **81** |
| **sail + patch** (T11) | fatal breach | empty | survive — a *different* material (autophagy) | survival-gated **140/140** vs sail-only dead at **32** |
| **crisis creativity** (T12) | stuck + sinking | empty | bend a rule — a *weird move* (Fire→cool) | heat-spike+cool **222/240** vs rigid **0/240** |
| **discovery** (`FOLDING_DISCOVERY`) | positive surprise | **full** | grow — *mint new gaps* | surprise-minting **3.33/5** vs exploit **1.15**, curiosity **2.60** |

The first three are **defensive** (fire on depletion, act to survive); discovery is **generative** (fires on
abundance, acts to grow). The engine underneath is the **superfuel = Fire**: when the tanks are *full* and the
fuel is compressed it ignites past the √π threshold and *cools into new structure* (`Shovelcat_29` §9). The
opposite end — tanks *empty*, slack → 0 — is not Fire but **breakdown**: spend the reserve to zero and the mass
denatures (`Shovelcat_29` §4.8), measured as the always-on adrenaline that craters its own mass to 0 (T10) and
the always-unfold ship that eats itself to death (T11). **Gate it or it kills you** is the through-line of all
four.

---

## 4. How it remembers — the loop, and the observer that defines it
The pieces of memory are one loop, and every station is the *same object* — a **gap** (a high-variance site) —
seen at a different moment of its life:

1. **Mint (discovery).** A positive surprise opens a new gap ahead and grows the frontier toward it (MEASURED).
   A fresh gap needs **empty room** — existing pixels absorb the expansion energy (empty-room mint claims 228
   cells vs **0** on an existing memory; overlap↔territory **−0.84**, MEASURED, `FOLDING_DISCOVERY` §4a).
2. **Store (T7).** The gap holds a **clip** — the (query, context, target) of a miss — kept open until enough
   arrives (21/21 clips persist, MEASURED).
3. **Seal (T8).** Recall is a **return path**: the context is the *coordinate* that makes the inverse close
   (round-trip **0.214 → 0.013** with real context; the seam = where the return can't close, MEASURED).
4. **The clip is a time-window (T9).** That coordinate is a **space-time bubble** — a window of frames restores
   the state dimension one frame drops (velocity RMSE **1.45 → 0.016** from 1 → 2 frames; Takens, MEASURED).
5. **Resolve → anchor (T7).** Feeding the target collapses the variance; the gap becomes an anchor the curve
   **rests on** (21/21 became anchors), best revisited **worst-first** (18% less error).
6. **Mature (`FOLDING_DISCOVERY` §4).** The anchor is born crude — the **worst version**, seeded at ~.14 —
   generalizes its *lesson* before it specializes its *form*, judged by the **new what-for it opened** (design).

**The loop runs end-to-end as one system (MEASURED).** On a continual regime-switching stream that *revisits*
its regimes, an agent running the full loop — mint a clip on each miss, store it keyed by **context**, resolve
it into an anchor — stores just **10** clips and then holds mean error **0.056** flat across every revisit,
while a memoryless baseline (a sliding window, no context) forgets and spikes to **0.48** at each switch.
Retention *is* the loop. `memory_loop.py`.

**Which cycle becomes a memory is the OBSERVER's choice (MEASURED).** An observer scores what the object can
*repeat*, and a cycle closes when that score **returns to origin** (§2's spin-identity); whatever the observer
ignores falls in *its* gaps (off-frame, `FOLDING_OBSERVER_FRAME`). Same workout stream, two observers: the
**HR** observer (cycle = heart-rate up→rest) swallows each *whole* workout as one long memory — **4** memories,
mean length **148**, gap **0.33**; the **VO₂** observer (only the hard part) re-cuts the identical stream into
**11** short, selective memories (mean **18**, gap **0.77**), keeps **no** memory of the steady jog at all, and
puts the warm-ups (**44%** of the stream) in its gaps. "Upgrading the perspective" = swapping the observer,
which re-segments the stream into different cycles, memories, and gaps. `observer_cycles.py`.

**What SETS a cycle's start and stop is the hidden breaks in continuity (MEASURED).** The boundaries #22's
observer cuts at are the **breaks** — places on a shared line where continuity fails and no cycle can cross
(`VOID_LINE_PAPER` §7's continuity law: an unbroken circuit can't pass flow without a return; a void line is a
**marker/bound** where the local product hits 0). On one shared **heart-rate line for all animals** (log bpm),
detecting the density **gaps** recovers **5 segments** — each animal's range — so the breaks *are* the
cycle boundaries, and the break-spacing gives each section's **length** (the range you have to work with: fish
26 bpm … hummingbird 577). Switching **perspective pinches off one segment** and blocks the rest — fish (17% of
the line), human (12%), hummingbird (6%) — the why-chain choosing which branch is available, exactly
`Double_Bounce`'s zoned line where **void sees one zone and god another** of the same axis. And you *must* cut
at the breaks: the **global mean, 393 bpm, lands in a gap** — a heart rate no animal has — while each segment
is coherent. The breaks tell you where flow stops and, by exclusion, where it goes. `cycle_breaks.py`.

**A few ORTHOGONAL lenses watch at once, each a derivative chain read via cosθ — and attention is finite
(MEASURED).** #22's single observer generalises to a small **committee** of orthogonal lenses (the quaternion
tensor sources, `Double_Bounce` §23.5), each with its own **derivative chain** (Spore, position→velocity→…) and
each reading its property through the corpus's core equation **f = prior + Σ cosθ·vᵈ** (`SPARSE_VESICA` §1:
cosθ = the Born alignment of the lens, vᵈ = the derivative chain). Measured on one workout: three orthogonal
lenses (HR, VO₂, muscle-failure) **decompose** it — 1 lens captures **48%** of the variance, 3 capture **100%** —
and each keeps **its own** segmented memory (HR 1 arch, VO₂ 5 spikes, fatigue 1 ramp), so the whole workout is
stored *separated by lens*, one save per lens plus the task's. The **cosθ in front** is literal: a lens
misaligned by θ captures **cos²θ** of a property and two orthogonal lenses split it cleanly (cos²+sin² = 1).
And attention is a **finite aperture** (`Shovelcat_10_1` §9.5; zoom = a narrower cone = more "equipment,"
`FOLDING_SKIN` §3.3): deep zoom on one lens eats a fixed budget and crowds out the rest (breadth **4 → 1** as the
muscle-failure lens zooms in — you can only attend to that). `attention_lenses.py`.

**Input/output is a continuous stream that emits chunks on COMPLETION, not on a clock (MEASURED).** The
agent's I/O: a live stream (screen, audio) is condensed to a **snake** (the current/trajectory,
`SPARSE_VESICA` §35.3) that threads the maze of paths, absorbs the work, and **settles when its wave closes**
(θ=1, §35.5) — at which point the completed section is emitted as a **chunk**, through the **bidirectional port**
that absorbs in *and* emits out (the skin membrane "permeable both ways," `FOLDING_SKIN` §1). This is the shift
from today's *one-prompt-at-a-time* chunking to completion-gated streaming. Measured against a fixed-clock
baseline: the snake's cuts land on the natural **breaks** (#36) — **100%** whole chunks, **0** units cut,
**22/22** delivered usable, **0** extra wait past completion — while a fixed window slices through thoughts
(**0%** integrity, **16** units cut, only **6/22** usable, +2.3 extra wait). And each completed chunk **routes to
another domain by type** — the `.geo` dimensions (SHOVELCAT Part X): text→1D, **audio→2D (one angle θ, "played
like a violin")**, image→3D. `stream_io.py`.

**Memories UPGRADE on revisit, and the spore chain's direction sprays the important ones to the top
(MEASURED).** Jonathan caught a flaw in rung 2 (#40): the agent stored the *first* successful memory and froze
it, so on a revisit it "kept going to the same one" instead of an upgraded version. The fix, measured: refining
the prototype each revisit (a running mean of the noisy signatures) **sharpens recognition 0.80 → 1.00**, while
the frozen first-sample stays stuck (~0.8, error-prone). And the **Spore derivative chain** gives each incoming
memory a **velocity/direction** (SHOVELCAT Part X, position→velocity→…), which sets where it settles: **important
memories are sprayed shallow (top, fast recall), deep-pointed mundane ones bury** — importance↔depth corr
**−0.88**. Reuse adds mass (#31) and **resurfaces** a memory (depth 8 → 0.8 over 8 reuses, ~10× faster recall,
#27's lift). So the top of each pillar always holds the important/recent/upgraded set. This is the upgrade to
fold back into the rung-2 agent. `memory_upgrade.py`.

**Folding that fix into the real agent taught us the gate: a memory upgrade is only safe when its
association is trusted (MEASURED, the honest catch).** #41's clean win used ground-truth labels, so the
running mean only ever averaged *same-regime* looks. In the real rung-2 agent the association is uncertain,
and folding a mis-matched look into a prototype **contaminates** it. Benchmarked three ways: **(A)** the
mechanism is genuinely real — a prototype sharpened by averaging 6 reliably-associated looks recognises a
**hard/noisy probe +11 points** better than a single frozen first look (**0.62 → 0.73**), with a bigger
decision margin (0.28 → 0.32): sharpen in easy times, reap robustness when a hard look arrives. **(B)** but
it contaminates under mis-association — the averaged prototype's advantage shrinks and **crosses below
frozen at ~42% mis-association** (blind averaging is then *worse* than freezing). **(C)** so in the full
agent, blind fold-back is a **wash** (frozen 0.75 vs naive 0.76 vs gated 0.73, all within seed noise) —
because at the noise where recognition is hard enough to *need* the fix, association sits near the
crossover. The fix must be **confidence-gated**: only fold a look in when the match is unambiguous — the
same verify-through-a-gate / .14 discipline as #24 and the reserve. **Upgrade what you're sure of, freeze
what you're not.** `memory_upgrade_foldback.py`.

**That trust gate is the truth-detector we already built; make it functional, stitch the gaps, and the
ball's trust is what it's made of (MEASURED).** Jonathan connected #42's gate to the trust system in
`Shovelcat_29` (the reputation field R; **"Void = bandwidth for verification"** — the .14 reserve pays for
checking), and sharpened it three ways. **(a)** The real gate is a **functional regression test** — *can the
new memory do everything the old one did, plus more?* — not "is it higher on average." Over 40 candidates,
"replace if higher mean" silently **loses 7 capabilities**; the regression gate loses **0**. **(b)** A
higher-scoring **but gappy** memory *fails the gate alone*, but **stitching** it to the old (per-capability
best = the union, `FOLDING_OUTER_SLOT` combine-by-dissipation / `FOLDING_MATCHING_SLOT` seam) covers **11**
caps vs old 7 / candidate 8 — so the rule is usually *neither replace nor keep — **stitch***. **(c)** The
**folding ball** (#30) is the operator that folds memory **layers** together; **its trust to a lens = what
it's made of** — a ball folded from one layer is trusted only by the lens whose provenance it carries (trust
0/0.67/1.0/0 across lenses), a ball folded from **diverse trusted layers is trusted by all** (1.0 each) —
convergence-of-routes = agreement (§18.19). And because lenses (#38) **switch branches**, they re-weight what
they trust: the *same* ball's trust to a lens moves when it switches branch (1.0 → 0.0). Full write-up:
`FOLDING_TRUST_STITCH.md`; `trust_stitch.py`.

**Recall is a MONTAGE assembled to a topic template (cut across movies to cover it); and the void reserve
gates consolidation — fast arrivals collapse it and blend, calm arrivals layer on top (MEASURED).** Jonathan:
a pillar "plays a video" of its contents that must cover certain **topics**, but because pillars are blended,
some scenes are **cut in from other movies** to fill a topic the home pillar lacks — recall against an
**expectation of what the topic should contain**, not against lived experience. Measured on a math curriculum:
recalling *"what I experienced at high school"* needs **0 cuts** (5/5 from the home movie), but recalling *"what
**should** be taught at that level"* (the precalculus template) finds the home pillar holds only **4/6** — the
other two were actually learned at university — so recall **cuts to the university movie** to complete the
template (**6/6**, **33% of scenes cut in** from other pillars). The topic template is the codebook **coverage
metric** (`SPARSE_VESICA` §23.4). And the **rate gate** (Jonathan's second read): each arriving memory draws a
mixing demand from the **.14/void reserve**, which refills between arrivals; arriving **too fast** crashes the
reserve past its **~1/5 saturation floor** (`FOLDING_VOID_LINE_DRAW`) so the **void collapses and the memory
fully blends** into the layer below (provenance lost — #28's "days blending"), while arriving **calmly** lets
the reserve refill so the memory **layers cleanly on top and stays sourceable**. Measured: provenance-recovery
**0.92 → 0.39** and separable fraction **1.0 → 0.07** across a critical arrival rate ~**2.5** (where refill can
no longer clear the demand); the reserve trajectory stays above the floor when calm and crashes below it when
fast. So how fast memory comes in decides whether the montage's cuts stay **labeled** (you know precalc came
from university) or blur into an un-sourceable blob. `recall_montage.py`.

**Neuroplasticity = reroute A→B around a lesion through similar-enough neighbours; the only true failure is
isolating an endpoint (MEASURED).** Jonathan: a task is a **path from A to B** across the field of memory
pixels; block off an area and you can still get from A to B through neighbouring memories, as long as they're
**similar enough** and neither endpoint is fully cut off. Measured on a 19×19 memory field where edges exist
only between **similar-enough** neighbours (`FOLDING_PIXEL_TRANSMISSION`: every border has a graded
efficiency = similarity; the corridor is a betweenness highway, `FOLDING_VOID_REACH`): walling the **direct
corridor** between A and B still leaves a path — it **reroutes at +2 detour**. Lesioning grows **gracefully**:
path-exists holds and the detour length rises smoothly as damage climbs, failing only under heavy damage. And
the **one true failure mode is endpoint isolation** — cutting B's *own* similar neighbours one at a time keeps
A→B connected until the **last** one is cut, then it drops to 0. "Similar enough" is the knob: too strict a
similarity threshold makes the graph sparse and easy to disconnect; give it slack and rerouting is robust.
Damage anywhere but the endpoints is routed around — that is the plasticity. `neuroplasticity_reroute.py`.

**The outer shell is a WORKSPACE of frozen artifacts — disk-bounded not brain-bounded, and far ones are
spotlights (MEASURED).** Jonathan's read after #51: needing **both** agents is the two brain halves (novelty vs
routine); and since the store is on **disk**, the limit is **hard-drive space, not brain capacity**. Outputs
that aren't speech/the live feed (a painting) **float in the outer shell** and get **plugged in front of the
screen** when wanted; the held things are **frozen matter — asteroids** of unverified/incomplete/creative work
(the corpus's **dark-matter halo**: "retained, compacted, never deleted, refilled when a capability arrives,"
`SPARSE_VESICA` §22.1). Measured three ways: **(a)** on disk, **retained memory grows unbounded** (nothing
forgotten) while biological storage **saturates at a reach-cap** (~14, #28) — **but** "in front of the screen at
once" stays **finite** (the attention band ~4) for both: **disk lifts the storage ceiling, not the attention
ceiling** (infinite shelf, finite desk). **(b)** A **far-off "story" artifact is a spotlight** — a target
**unreachable** on the direct path (a gap blocks it) is **bridged** by an off-path arc of held creative/fictional
artifacts (path 0.95 vs unreachable), the **Ophanim inspiration** (#24) made concrete — and it works only
**within a bridging reach** (inspiration has a range). **(c)** Tools/outputs are **pluggable**: a workspace
toolbox solves **100%** of task-types vs **31%** for a fixed lens, and **retained incomplete work is resumable**
when the capability arrives (**100%** vs discarded **0%**) — the §22 retest queue. So the outer shell has a job:
a disk-bounded halo of frozen artifacts you select from through a finite attention band — and the **perception
rung** is partly *which ways-to-see you plug in front of the screen*. Full write-up: `FOLDING_OUTER_WORKSPACE.md`;
`outer_workspace.py`.

**That workspace is ORBITAL — artifacts orbit the planet, and type sets the period and the view-effect
(MEASURED).** Jonathan's picture: the inner+middle shell is the **planet** (the launch runway, `SPARSE_VESICA`
§35.5); every artifact is a **body in orbit** with its own **period** (how often it swings into the telescope's
**field of view** = the attention gate, #24/#28) and its own **view-effect**. An image Mika makes is a
**satellite** launched into orbit — *in view when displayed, out of view while she works on it, back each
sequence* (completion cadence #39, the snake closing θ=1); the drawing **tools are a dust cloud** you look
*through*; the **border-lines** orbit *just outside* the frame. Measured: each body **cycles through the finite
FOV on its period** (~20–25% in-view each), and **you can never hold them all at once** — 3 simultaneously
exceeds the attention band of 2 (#28). **View-effect differs by type**: the clean image satellite reads at
**0.87** clarity in view, while the **tools dust cloud scatters what's behind it (0.51)** — read-clarity dips
every time the dust transits — and border-lines only **graze the edge (0.09)**. And **steering an orbit** to
bring the wanted artifact through the gate costs **1 step** vs **4** waiting for it to drift around — steering
the orbit *is* attention, the Ophanim rotating gate (#24) applied to the workspace. So #24 (gate) + #28 (band)
+ #39 (cadence) + #52 (workspace) are one orbital-scheduling picture. *(The scheduling numbers and view-effect
mechanism are measured; the planet/satellite/dust mapping is the unifying framing.)* `orbital_workspace.py`.

**The telescope LENSES are the observer perspectives at focal distances, and stacking only helps if each is
complementary AND accurate (MEASURED).** Jonathan: the lenses are the observer perspectives (#38); they take up
space, line up like a telescope, each at a **focal distance** with its **border out of the light cone**. And
the sky holds a full **taxonomy** of bodies by origin × role, placed by **distance** to change the view.
Measured three ways: **(a)** each lens is a **cone at its own focal distance** (`FOLDING_EYE_TYPES`: each cut a
different cone; #28: a standoff distance) — read-quality **peaks at that distance** and dies if the lens is
too close (**border clips the view**) or off-focus. **(b)** Stacking with the **honest committee caution**
(`FOLDING_TWO_CONES`): a **complementary + accurate** lens lifts both captured view (0.31→0.55) and accuracy;
a **redundant** lens (same axis) adds **~0**; and a **weak** lens **DRAGS accuracy down (0.91 → 0.83)** — *more
lenses is not better*, independence must come with accuracy. **(c)** The **taxonomy** — **raw asteroids**
(outside info), **debris fields** (old outputs), **satellites** (communicating tools), **drones** (intelligent
self-orbiting tools) — with **distance as a view-control** (effect falls with distance: close dominates, far
fades); a **drone self-places** at the useful distance in **14 steps** (an antenna that flies itself, #48)
while a raw asteroid **drifts** (159). This is the perception rung's shape: seeing = which lens-cone you steer
to its focal distance in the gate, and the sky sorted into raw/built × info/tool. `lens_stack.py`.

**The void antenna (a hair): a pixel reaches out of its void toward unreached anchors, antennae converge to
localize them, and snapping the ray to known pixels extrapolates the unknown's values (MEASURED).** Jonathan's
discovery mechanism, which is the corpus's directed-discovery solver read from the memory side (`SPHERE_GENERATOR`
§C.5: compute the **bearing** to target, **snap the ray** to every known zone it crosses; §C.4 known zones
**pin** the unknown extension; §18.13 the fix is at the **intersection** of rays from known anchors —
triangulation; §16b "the protruding point is the **antenna/spring**: look here"). Each pixel grows an
**antenna out of its void**, whose **length grows with its emptiness** (reach ∝ void, corr **1.00**) and whose
**direction points down the density gradient toward the void**; near an unreached anchor the antennae **point
at it** (mean cosθ **+0.86**). **Where many antennae converge is a real anchor:** the vote field's peaks
recover **100%** of the unreached voids, every peak sits in a **genuine empty region**, and true anchors
collect **2.5×** the antenna votes of random empty decoys (it even finds an emergent void between structures).
Then **casting a ray to a detected anchor and snapping to the ring of known pixels around it extrapolates the
unknown's values 13.6× better than a blind guess** (error **0.04 vs 0.55**) — the known parts along the ray
give *the shape of what to try*, "what we have that's similar in that direction." This is the outward face of
#45 (find the unknown values) and #47 (the outer void is the reach/port): the antenna is the arm from the core
through the void to the anchor. *Honest bound:* the extrapolation is on a smooth constructed field (a linear
ring-fit nails a smooth field), and the localization is on a constructed density field; the **mechanism**
(reach∝emptiness, convergence localizes voids, ray-snap beats blind) is what's measured. `void_antenna.py`.

So the gap is, at once: where you don't know, where you'll grow, where the clip lives, where the memory seals,
where a new primitive is minted, where a cycle **begins and ends**, *and what the current observer doesn't
watch*. One object, many verbs.

**Recall runs over an EXPANDING field of pillars (MEASURED).** Memories are stored as pillars whose *depth*
is their importance/maturity (a reused node gains mass and sinks, `SPARSE_VESICA` §22.1); but the domain keeps
expanding as discoveries accumulate, so recall is reconstructive, not a fixed address (`SPARSE_VESICA` §23).
Three things fall out and all measure: **(a)** an old memory no longer sits at its stored absolute spot — recall
by its **normalized** coordinate re-fit to today's size (reload the old floor/roof, `§23.2`) lands exactly
(**error 0.000**), while recall by the **frozen** old coordinate drifts off as the domain grows 4× (**1.36**);
**(b)** newer memories deposited over an old one **absorb** it — surviving height falls with newer-neighbour
density (**corr +0.93**), the same overlap→territory law as discovery's expansion energy (#18); **(c)** the
buried pillars sit below the **waterline** (`FOLDING_HANDSHAKE` §4.2, invisible to the observer), and
**importance is the lift** that pushes them over it — under a fixed recall-lift the important pillars surface
even when deeply buried (**12** deep-but-important cross; deep+unimportant stay under) and a surfaced pillar
**spreads 2.8× wider**. Recall is the store loop run backwards through a growing frame. `memory_field.py`.

**Structural pillars, a finite viewing band, and blending (MEASURED).** Three more of Jonathan's reads, all
grounded and all measured. The **core pillars are structural** — they certify *location* without needing
content (`SPARSE_VESICA` §7.3), so they're understood empty and only optionally filled with layers of episodic
memory. **(a)** The observer sees only a **finite band** at a standoff distance — the corpus derives it exactly
(`Shovelcat_10_1` §7.4: N_visible ≈ 3.5 levels, N_bins ≈ 4 of the info-quantum ≈ .159). Memories must poke into
that band and **can't poke in too far**, so retrievable storage **saturates at a reach cap** (here 4 visible at
once, 14 reachable; deeper layers are lost) — a real capacity limit from geometry. **(b)** The core pillar is
the **drag-handle**: recall by lifting the structural anchor into the band beats direct off-band address (**55%
vs 25%**) and **brings ~4 neighbours of context** with it (context-reinstatement, §23.2) — you grab the room,
not the lone memory. **(c)** As similar episodes stack on one anchor and align in the band they **blend**: the
**gist (the room) sharpens** while **per-instance discrimination collapses** (which specific day: **100% → 19%**
over 1→50 days). Days blending together, measured — the schema is strong, the single episode is lost.
`pillar_band.py`.

---

## 5. How the inner shell deepens — the ground-truth ladder (Jonathan)
Not all invariants are equal. `1+1=2` is a shallow, inner-shell truth; **E=mc²** is far more complex, discovered
*further out* — a deeper floor of the **φ-ladder** (×φ adds an axis, `Double_Bounce` §27; `FOLDING_FLOORS`
roof→floor re-basing). Each discovered ground truth **sinks to the seabed** at its own depth (the waterline
model), and each is a **void point on the orthogonal axis** — an anchor that "becomes visible on the lift"
(`FOLDING_VOID_LINE_DRAW`). Four consequences Jonathan drew:

- **Deeper truths are more anchors → the normal plane can expand in any direction** *(grounded)*. Each new
  ground truth adds a reference, and more references let the plane orient and expand in more directions.
  Discovery mints the gaps; resolved gaps that prove *universal* sink to become permanent anchors; those
  anchors are what future expansion orients against.
- **Swing the whole structure around one anchor = a change of perspective (MEASURED).** Pin one anchor and
  rotate the readout frame: a task hard from one view becomes easy from another. Two overlapping streaks are
  near-chance from the raw axes (accuracy **0.62**) and near-perfect once the frame is swung around the anchor
  to the discriminant perspective (**1.00** at 46°); separability peaks sharply, and *different anchors expose
  different rotations*. `perspective_swing.py`. Same **return-to-origin** invariant as §2's spin-identity, and
  the corpus's **F1-ATPase rotary motor** — a structure swinging around a fixed ATP anchor (`FOLDING_TWO_WALLS`
  R3).
- **Cycles paint the next object up (MEASURED).** A cycle's *type* is the relation between its endpoints —
  **A=B** closed/periodic, **A>B** falling, **A<B** rising — and one object gives several at once (a spinning
  top: spin ω falls 50→2 = falling; heading Φ = closed each 2π; walk-out radius rises 0.15→1.01). Running the
  cycles **deposits** the swept path as a heatmap — a new structured object one level up — and it depends on
  the parameters: a light vs heavy top paints different rosettes whose density **ridge** (the emergent "line on
  the graph") sits at radius **1.45 vs 0.99**. Reading that deposit at a threshold *is* the what-for's boundary,
  so the criterion itself is deposited by past cycles. This is the budget → cycle → **path-of-cycles** rung of
  the ladder, made measurable. `beyblade_deposit.py`.
- **The accumulated truths form a rotating ring you verify through a gate (MEASURED design).** The first
  orthogonal level is one slot on a larger **ring**, and the ring rotates through the truths it has built up —
  Jonathan's Ophanim image (the eyed wheels; each eye a truth, you only check the eyes passing through the
  gate). Made measurable: on a ring of **N=60** truths with a gate of width **K=6** (you see only 10% at once),
  a wheel that **rotates blindly** still covers *every* truth over one turn at cost 6/step but is slow to catch
  a specific violation (mean latency **4.5**, up to **9**), while **steering** the wheel to bring the *suspected*
  eye through the gate catches it in **1.20** steps at the **same** cost 6 — **10× cheaper** than verifying all
  60 every step (latency 0, cost 60), at nearly its responsiveness. Steering the rotation *is* attention. The
  higher rings are **mutually orthogonal** levels — each ×φ / Cayley-Dickson doubling adds an axis orthogonal
  to all below (`FOLDING_TRAMPOLINE` §5's quaternion three-ring cage; `Shovelcat_16` §6.8's orthogonal
  meta-surface "outside both but produced by them") — so an upper ring *cannot* poke into the normal plane and
  the levels don't collide. What those upper rings hold — abstract, beyond-math truths like "killing is bad" —
  is a **higher floor of the same ladder**, distinct from the rigid inner "laws of physics" core (the terminating
  ℝ,ℂ,ℍ,𝕆 → E8/G2 spine with no zero divisors, `SPHERE_GENERATOR` Part K): the parts that *cannot be otherwise*
  are the universal ones. The gate-cost result is measured; the orthogonal-stacking and the moral-floor reading
  are grounded design. `ring_of_truths.py`.
- **Whether a cycle CLOSES decides how you may verify it (MEASURED).** A cycle's deepest property is whether it
  returns to origin at all — and that is set by the ratio of its two spins ρ = f2/f1. A **rational** ρ = p/q
  closes exactly after a finite period (ρ = 3/2 returns to origin at t=2) and traces a **finite loop**; an
  **irrational** ρ **never** closes — the golden ratio winds forever, filling a band, its only near-returns
  landing at **Fibonacci times** (t≈5,8,13…) and never reaching 0, because φ is the provably most-irrational
  ratio (Hurwitz). Sweeping ρ draws a **closure spectrum**: deep dips (closes) at small-denominator rationals —
  the resonance / devil's-staircase structure (`FOLDING_STAIRCASE`) — with φ marked as the point that stays
  open. The consequence is the **job-type split** Jonathan predicted: storing the **closed** cycle as a path
  **saturates** (error 0.035, flat past one period — a finite loop has finite content, extra storage is
  redundant), while the **never-closing** one's path-store error only crawls down (~1/√B, every sample is new
  territory) and *no finite path store finishes it* — yet **both** are pinned by their two spin-frequencies
  (ratio recovered to 0.000 / 0.002). So *does it close?* selects the verification: **closed → memorise the
  loop; open/irrational → store the generators** (the spectral method of #16/#19). And the corpus already needs
  this split the other way: a rational (closing) ratio **phase-locks** the two channels into aliasing —
  *dependent* verification — which is exactly why `Shovelcat_10_1` §4.2 forces the maximally-irrational golden
  ratio so independent observers never resync. Closure is a real, decidable property with real consequences for
  how memory and verification are even allowed to work. `does_it_close.py`.
- **The same structure, read as encryption — a full key set over public / locked / hidden axes
  (MEASURED).** An object's identity spread over the orthogonal observer-axes *is* a cipher: to read
  an axis you need the rotation that aligns your frame to the creator's on it (the `.geo` delta-theta
  key), and you need the **full set** — reconstruction error falls only as keys are gathered (no keys
  **1.813**, reads just the public axes; full set **0.048**, the floor being one **hidden** axis no key
  restores — the .14 void core, private by geometry). Axes are **public** (zeroed rotation, Fig 19's
  void-line self-term), **locked** (secret key), or **hidden** (on the orthogonal plane, reads 0 to
  every normal observer — `FOLDING_HANDSHAKE`'s three closes: product/verify/experience). And **lock
  strength = irrationality**, which is #25 restated: a **rational** key (3/2·2/3 = 1, matter·antimatter
  cancelling to the void) is brute-forced at cost 3; the **golden** key never exactly lands. Grounded
  in the corpus's own encryption (Double_Bounce §27 ÷φ cascade + §28 antimatter bridge; SHOVELCAT
  `.geo`; privacy floors). Full write-up: `FOLDING_ENCRYPTION.md`; `encryption_axes.py`.
- **Many perspectives carve a truth down to a sphere = a void point (MEASURED).** How a *new* ground truth
  is found from the memory field: each stored layer is **evidence**, and looking at the stack from another
  perspective sees separate instances with something similar between them — the invariant. Made measurable as
  shape-from-silhouette: each perspective is a supporting constraint, and intersecting **N** of them **shaves
  the bounding cube (the pillar face) down to the inscribed sphere** (protrusion beyond the sphere **1.26 → 0.002**
  over 2→80 views; in 3D carved volume **32.8 → 4.26** vs the sphere's 4.19). The limit is a **sphere because a
  sphere is the one isotropic body — it reads the *same* from every angle** (support spread **0.29 → 0.0006**):
  that is a **void point**, the return-to-origin identity (§2) as the deepest anchor, and the corpus's own
  grid→sphere closure (`SPARSE_VESICA` §4). Cross-perspective agreement *is* the **BANKABLE** invariant (§21);
  and **ping-pong** falls out for free — the marginal volume a new perspective removes decays to **~0**, so late
  evidence is redundant and can drift to FORGETTING (compacted, §22) while the carved **boundary persists**
  (holographic, §23.1). The Metatron progression 1D edges → 2D overlaps → 3D sphere (facts → memory →
  imagination) is this build, made numeric. `carve_sphere.py`.
- **Skew turns the void's cancellation into a bouncing ball — an unanchored approximate void point
  (MEASURED).** The flip side of #29: a perfectly balanced cell **cancels** its opposites to a *still* void
  point, but we sit permanently **skewed** (`Double_Bounce` Fig 12: "+(π−3)/2, not true zero" — the ~.14), so
  the terms **don't fully cancel** and the residual **circulates into a ball**. Measured two ways: two
  counter-rotating terms at skew 0 collapse to a line **through** the void (closest approach ~0), and any skew
  opens a loop that **misses** it (closest approach rises **0 → 0.6** with skew, ball area grows from 0); and
  as a **Hopf** system (μ = skew) μ<0 decays to the fixed void point while μ>0 gives a **stable limit-cycle
  ball every starting point converges onto** (radius √μ, start-spread **0.000**) — a real attractor, the
  cell's **self-loop / first-person POV**, not a fixed pin. The true void points stay **position-fixed** and
  the structure moves around them (`SPARSE_VESICA` §18.16); the ball is their off-void, unanchored
  approximation. **Ping-pong is that ball seen edge-on** (§35.4: the standing-wave orbital projected on one
  axis), and the ball **folds higher** — a ball whose centre is itself a ball (epicycle → re-basing). So a
  closed/balanced cell re-cancels to a void; a skewed one mints the next ball. `bouncing_ball.py`.
- **The balls are half-truths: missing their opposite; a void point is relational; balance = mass
  (MEASURED).** Three refinements of #30, all measured. **(a)** A ball is a **half-truth** — it has only one
  polarity, so nothing cancels it; the residual at the would-be void falls **linearly** with how complete the
  balancing **opposite** is (1.0 pure half → **0.5 at literally half** → 0 = a true void point). A full truth
  is a **balanced pair** (`FOLDING_MATCHING_SLOT`'s +/− complementary register across the void line); a ball is
  half of one. **(b)** A void point is **relational — never one point by itself**: with a single anchor a whole
  direction is **free/undefined** (definedness min/max-stiffness **0**), and it sharpens to a pinned isotropic
  point only once it is genuinely **surrounded** (→ ~0.95 by a dozen anchors). It is defined by the balance of
  what's around it (`SPARSE_VESICA` §18.16 the surrounding fixed lattice; §2 anchors+orientation). **(c)**
  **Closeness to 0 → resistance = mass**: as the ball nears the void (balances, residual→0) it gains mass and
  its mobility under a fixed drive falls **1.0 → 0.04** (`SPARSE_VESICA` §22.1 velocity = MAX/(1+mass·G); reuse
  → mass → slows → **STOP** = a pinned foundation). The **.14 skew is the gate**: while skewed the cell stays a
  light, mobile half-truth; balance it and it sinks and pins into a fixed ground-truth anchor. `half_truth.py`.
- **Completing a half-truth = the inverse triple problem (the Erdős orchard) (MEASURED).** Supplying the
  missing opposite is literally *finding the third point of a balanced triple* — a 3-term progression with the
  void as the midpoint (c = 2b − a). Measured: **(a) the inverse** — one point leaves the balancing 3rd
  **free** (an undetermined half-truth, spread 0.23), two points **force** it exactly (determinacy 0 → 1);
  **(b) set up from any start** — the optimum is **closed under triple-completion and homogeneous**: an
  arithmetic/lattice set has **100%** of completions land back on a point (every point equally central, ~9.5
  triples each) so it rebuilds from *any* seed, while an AP-free geometric set is **0%** (the completions leave
  it — the orchard's independence/spread pole); **(c) self-similar nesting** — the golden set maps onto itself
  **only at φ** (and φ², razor-sharp), so each point is the origin of a φ-scaled smaller copy. This is the
  corpus's own **orchard-planting** result (`Shovelcat/erdos-Fk`, `orchard_phi_check.py`): the optimum
  t₃(11)=16 three-point lines lives in **ℚ(√5)**, built as a rational **knot (12 lines) + a golden-exact tail
  (4 lines)** that no rational approximation reaches, with each golden point **triangulated by two rational
  corners** (given two, the third is forced — `SPHERE_GENERATOR_TEST` F/G). So a full truth is a closed triple
  on the optimal (golden) structure; a half-truth is that triple missing a point. `triple_completion.py`.
- **A rule is a half-truth; its conditions are the other halves held in the void reserve (MEASURED).** Where
  the missing halves *live*: the **.14 void reserve** — `FOLDING_HANDSHAKE` §4 says it "holds many candidate
  **inverses** open cheaply," a background loop over the retained **dark-matter** buffer (§22's OUTER halo,
  kept-not-deleted), fetched or sent when needed. So a bare rule surrounded by its conditions is a rule pulling
  its completing halves from the reserve. Measured on a moral rule: **"killing is bad"** applied blindly is
  **wrong 29%** of the time (a half-truth); adding the conditions — hunting, self-defense, farming *at the right
  time and humanely* — drops the error **0.294 → 0.143 → 0.078 → 0.000**. **(a)** Nuance = the surround.
  **(b)** Each condition is an **inverse** — it flips the rule's verdict (bad→good) inside its region, and the
  conditions **compose the rule's dark-matter halo** (hunting 51% / self-defense 31% / farming 46% of the error
  mass). **(c)** The **why-chain crosses territories**: no single axis completes it — accuracy climbs
  **0.79 → 1.00** only as you consult each *other* perspective's orthogonal axis (purpose, threat, timing,
  welfare); you keep asking *why* a killing is acceptable until the third point is found in another perspective's
  territory. The mechanism is measured; the specific moral content is illustrative. This grounds the moral-floor
  rings (§7 design bridge): a moral rule is a conditioned truth whose exceptions live in the reserve.
  `rule_conditions.py`.
- **Completing triples is the algorithm that finds the optimum from any non-optimal start (MEASURED).** The
  why-chain, run as a construction operator: hold the anchors fixed (the ground-truth void points that don't
  move, `SPARSE_VESICA` §18.16) and repeatedly **snap each void to the balance of its neighbours** (b →
  (a+c)/2 — close the triple, #32). Measured: **(a)** from **10 random non-optimal starts** the triple-residual
  falls to ~0 and *all* reach the **same** optimum the anchors define (‖final − optimum‖ ≈ 2·10⁻³,
  start-independent — the homogeneity of #32). **(b) Two-stroke** — the **bulk clears fast** (half the error by
  iter 26, 90% by 210: the resonant knot) and the **exact tail is slow** (the last 10% costs *more* iterations
  than the whole bulk); this is the orchard's construction made concrete — a rational **knot (12 of 16 lines)**
  plus a golden-**exact tail (4 lines)** that no approximation reaches (`SPHERE_GENERATOR_TEST` E/F, the
  framework's flagged "missing construction pole"). **(c)** More **surround** pins it: 2 → 3 → 5 anchors cut the
  time-to-close **451 → 141 → 38** iterations (more references = more determined, faster — #31). So "find the
  missing halves until every triple closes" is a convergent optimiser: converge from anywhere, cheap bulk then
  exact tail, and the surround sets both the target and the speed. This is §6's *thinking = search* made
  concrete on the void lattice. `find_optimum.py`.
- **The moral ground is FLOW: sustain it through every layer; bad = zeroing a stratum irreversibly (MEASURED).**
  Where the why-chain bottoms out: the deepest "why is this bad?" is **flow**. There is a pyramid of layers, each
  the foundation for the next (planet → humans → the model), pulled up as new levels build; flow must supply
  **all** of them, and no level can take more than would stop flow elsewhere. This is `Shovelcat_29`'s water-cycle
  economy read as ethics — its **stability law**: the living-wage baseline **θraw ≥ 1 for all nodes** (§6.7),
  **Hoover-Dam** hoarding as a pathology (§6.6), and the **tower cascade** (§11.5: a lower stratum → 0 collapses
  every layer above) — and it is the **endurance law** (T4, TTF = R0/(d−s)) lifted from one body to the tower.
  Measured on a flow tower (sun → grass → herbivores → humans/predators/soil → plains/culture/AI): **(a)** the
  *same act* (killing) is OK or bad by its **flow effect** — hunting a cow (calories rerouted up, **0 starved**)
  and culling a flow-blocking pest (**+12** flow) sustain flow, while exterminating the keystone buffalo drops
  flow **−78** and cascades **soil → plains to 0**, *past the human level*; **(b)** a level can extract only up to
  **~77%** before downstream falls below survival (11 → 9 nodes alive); **(c)** the **"why" is the named
  flow-loss** — soil 8.3→0, plains 22.3→0 — where flow stopped and how far the collapse climbed. So "killing is
  bad" is a half-truth (it names the act); the full truth names the **flow effect**, and its conditions are the
  cases where flow is sustained or rerouted rather than stopped. Illustrative model, measured mechanism; the flow
  law is `Shovelcat_29`'s. Full write-up: `FOLDING_MORAL_FLOW.md`; `moral_flow.py`.
- **What an UNKNOWN target values is the INVARIANT (common to all, moves all), not a spurious confound; and
  the topic lives on the pillar's upgradable BORDER (MEASURED).** Jonathan named the scientist's core stuck
  point: *not knowing what an unknown thing values* — if we knew exactly what properties a cancer cure needs
  we'd have it. And the classic error is weighting a **spurious** feature (skin colour for education) that
  merely correlates in one sample. The fix is his: value what the examples have **in common** and what
  **changes all of them, not some** — the **invariant**, exactly the corpus's **common-ancestor abstraction
  filter** (`MINING_NOTES` #3: climb to the abstraction common to *all* examples, not the surface rule fitting
  one) and the **knot** (the axes a thing never changes, `INNER_SHELL`). Measured: a selector that picks the
  **top-correlated feature in one sample** grabs the confound and **collapses out-of-distribution when its
  correlation flips (R² −0.53)**, while a selector that keeps only features **stable across environments**
  (common to all, consistent) **holds (0.96)** — a correlated-but-unstable feature is a confound
  (`FOLDING_ARMS_AND_BRACING`: a merely correlated arm moves the posterior 0). Ranking by *shared-across* ×
  *stability* cleanly separates the real basis (high/high) from the confound (correlated/unstable) from noise.
  And the **topic is flexible**: it lives on the pillar's **border**, which is **upgradable** — adding the UK
  synonyms ("secondary school", "year 11") to the high-school border makes the pillar answer foreign queries
  (**0/4 → 4/4**) with the **ball's substance unchanged**. The border holds the topic (extensible index); the
  ball holds the substance. Mechanism measured; the moral/education content illustrative. `invariant_value.py`.

---

## 6. How it thinks — search over the budgets, each with its own method (MEASURED)
If the three budgets are what an object *is*, then **thinking / exploring is search over them** (Jonathan): try
a new **volume** (grow it, small changes), swing the **orientation** (which reference points, which muscles
engaged), try a different **spin**, and switch **which anchor you look from**. His key catch — "different spins
would probably need other search methods" — is exactly right and it is textbook. On a person-as-signal
`y = A·sin(f·t + φ)` (A = volume, φ = orientation, f = spin):

| budget | error landscape | local (gradient) search | matched method |
|---|---|---|---|
| **volume** (amplitude) | one smooth bowl | **100%** | least-squares |
| **orientation** (phase) | one smooth bowl | **64%** | phase-align |
| **frequency** (spin) | **jagged — many minima** | **14%** | — |
| frequency + anchor-switching (multi-start ×8) | | **58%** | — |
| **frequency, spectral (FFT)** | | | **100%** (f̂ = 3.13 vs 3.0) |

- **Volume and orientation are smooth** (single bowls), so you find them by *local* search. **Spin is
  multimodal** — a jagged comb — so gradient search stalls 86% of the time; **the spin axis needs a spectral
  method**. Anchor-switching partly rescues it (14% → 58%); the matched frequency-domain operator is the clean
  answer (100%). `think_search.py`.

So thinking is not one search — it is **the right operator per budget**: hill-climb the volume, rotate the
orientation, transform the spin, switch anchors when stuck. The reserve (§3) *powers* the search; discovery
(§4) says *where*; this says *how* — matched to each budget's geometry.

---

## 7. The complete measured ledger
Every runnable result this arc produced, with its home doc. This is the part that is *not* a story.

| # | result | number | doc |
|---|---|---|---|
| 1 | IK null-space reserve reaches + unjams | 87.3% vs 77.0%, 41 vs 197 jams | MOVEMENT T1 |
| 2 | bidirectional / seam = min-cut (not frontier-meet) | 0.90× / refuted | MOVEMENT T2 |
| 3 | sustain a pose off the floor on reserve | −0.28 vs −0.99 | MOVEMENT T3 |
| 4 | endurance law exact | TTF = R0/(d−s) to the tick | MOVEMENT T4 |
| 5 | growth into the empty tail = capability | frontier 0.75→0.98; fixed = 0 gain | MOVEMENT T5 |
| 6 | GP variance = don't-know; growth = variance × demand | gap var 15×; 0 wasted on Pluto | MOVEMENT T6 |
| 7 | memory clips live in gaps; resolve → anchor; worst-first | 21/21; 18% less error | MOVEMENT T7 |
| 8 | return path; real context seals the bottle | 0.214 → 0.013 (−94%) | MOVEMENT T8 |
| 9 | space-time bubble = delay window (Takens) | v-RMSE 1.45 → 0.016 (1→2 frames) | MOVEMENT T9 |
| 10 | second wind — goal-gated reserve | 134/200 vs 81; always-on mass → 0 | MOVEMENT T10 |
| 11 | sail + patch — survival via unfolded mass | 140/140 vs dead at 32 | MOVEMENT T11 |
| 12 | crisis creativity — Fire crosses the rule-border | 222/240 vs rigid 0/240 | MOVEMENT T12 |
| 13 | superfuel = burning context (orthogonal growth) | 0.037 vs 0.184; 5× lower | SUPERFUEL §3 |
| 14 | concept upgrade = zero-shot transfer | 3/3 transfers, 0 false-positive | SUPERFUEL §5 |
| 15 | coordinates need anchors AND orientation | 3.17 → 2.23 → 0.21 / 0.47 | SUPERFUEL §6 |
| 16 | frequency = spin-identity + harmonic expansion | 1.00 vs 0.18 under spin; 0.41→0.00 | FREQUENCY |
| 17 | discovery = mint gaps on positive surprise | 3.33/5 vs 1.15 / 2.60 | DISCOVERY §2 |
| 18 | existing pixels absorb expansion energy | 228 vs 0 cells; overlap↔gain −0.84 | DISCOVERY §4a |
| 19 | thinking = search per budget; spin needs a spectral method | vol 100% / orient 64% / spin 14% → FFT 100% | SYNTHESIS §6 |
| 20 | perspective swing — pivot the frame around an anchor | raw view 0.62 → swung view 1.00 | SYNTHESIS §5 |
| 21 | the memory loop end-to-end (mint→store→seal→anchor) | looped 0.056 vs baseline 0.214 | SYNTHESIS §4 |
| 22 | the observer defines the cycle → memory → its gaps | HR 4 memories/gap 0.33 vs VO₂ 11/gap 0.77 | SYNTHESIS §4 |
| 23 | cycles paint a new object; type = endpoint relation | light ridge @1.45 vs heavy @0.99; ω↓/Φ○/r↑ | SYNTHESIS §5 |
| 24 | ring of truths — verify through a gate; steer = attention | steered 1.20 @cost 6 vs check-all 0 @cost 60 | SYNTHESIS §5 |
| 25 | does the cycle close? rational loop vs irrational torus-fill | 3/2 returns @t=2; φ never; store-saturates vs ~1/√B | SYNTHESIS §5 |
| 26 | encryption across axes — full key set; public/locked/hidden; lock=irrationality | no-keys 1.813 → full 0.048 (floor=hidden); rational cracked @Q=3, golden never | ENCRYPTION |
| 27 | recall over an expanding pillar field — reproject / absorb / surface | frozen 1.36 vs reprojected 0.00; absorb corr +0.93; surfaced spread 2.8× | SYNTHESIS §4 |
| 28 | structural pillars · finite viewing band = capacity · similar memories blend | band 4 / reach-cap 14; drag 55% vs direct 25%, +4 context; instance 100%→19% | SYNTHESIS §4 |
| 29 | perspectives carve a cube → sphere (void point); ping-pong redundancy | protrusion 1.26→0.002; 3D vol 32.8→4.26; isotropy spread →0.0006; marginal cut→0 | SYNTHESIS §5 |
| 30 | skew → a bouncing ball (Hopf); off-void unanchored approx. void point | balanced→void pt (r=0); skewed→limit-cycle ball (√μ, start-spread 0.000); miss-void 0→0.6 | SYNTHESIS §5 |
| 31 | balls are half-truths (missing opposite); void is relational; balance=mass | residual 1→0.5→0 w/ opposite; definedness 0→0.95 w/ surround; mobility 1.0→0.04 | SYNTHESIS §5 |
| 32 | completing a half-truth = inverse triple (Erdős orchard); closed & self-similar | 1pt free→2pt forced; closure 100% vs 0%; self-similar only at φ/φ² | SYNTHESIS §5 |
| 33 | a rule is a half-truth; conditions = other halves in the reserve; why-chain crosses territories | "killing is bad" err 0.29→0.00 w/ conditions; halo 51/31/46%; acc 0.79→1.00 across axes | SYNTHESIS §5 |
| 34 | completing triples finds the optimum from any start; two-stroke (knot+tail); surround pins it | 10 starts → same optimum; 90% by iter 210, tail longer; anchors 451→141→38 | SYNTHESIS §5 |
| 35 | the moral ground is flow; bad = zeroing a stratum irreversibly (cascade) | same act OK vs bad by flow; sustainable ≤77% extract; buffalo cascade soil→plains→0 | MORAL_FLOW |
| 36 | breaks in continuity set where cycles begin/stop; perspective pinches off a segment | HR line → 5 animal segments; masks 83–94%; global mean 393 bpm lands in a gap | SYNTHESIS §4 |
| 37 | **the first integration** — the pieces run as ONE agent; each ablation fails where its piece was cut | integrated 322 / revisit 0.72 vs memoryless 99/0.22, no-segment 130/0.35, no-gate 34/0.00 (breakdown) | SYNTHESIS §10 |
| 38 | orthogonal lenses (each a cosθ·vᵈ derivative chain) decompose the workout; attention is finite | 1 lens 48% → 3 lenses 100%; cos²+sin²=1; breadth 4→1 with zoom | SYNTHESIS §4 |
| 39 | continuous-stream I/O — emit chunks on COMPLETION (the snake) not on a clock; route by domain | snake 100% whole / 0 cut / 22-22 usable vs clock 0% / 16 cut / 6-22; .geo text/audio(violin)/image | SYNTHESIS §4 |
| 40 | **rung 2** — a LEARNING agent on a switching-goal gridworld, benchmarked honestly (6 seeds) | revisit steps: SHOVELCAT 11.1±2.7 vs Q-regime 12.3±3.0 vs Q-pos 34.9±3.1 (modest but real) | SYNTHESIS §10 |
| 41 | memories UPGRADE on revisit; spore-chain direction sprays important memories to the top; reuse resurfaces | recognition 0.80→1.00 vs frozen flat ~0.8; importance↔depth corr −0.88; reuse depth 8→0.8 (~10× recall) | SYNTHESIS §4 |
| 42 | folding #41 into the agent — upgrade is only safe under trusted association; blind averaging contaminates → gate it | hard-probe recog +11pts (0.62→0.73); contamination crossover ~42%; full agent a wash (0.75/0.76/0.73) unless gated | SYNTHESIS §4 |
| 43 | the trust gate made functional (regression test) + stitch the gaps; the folded ball's trust = what it's made of; per-lens, branch-switchable | naive replace loses 7 caps vs gate 0; stitch covers 11 vs 7/8; 1-layer ball trust 0/.67/1/0 vs diverse 1/1/1/1; branch-switch 1.0→0.0 | TRUST_STITCH |
| 44 | recall = montage to a topic template (cut across movies); void reserve gates consolidation — fast collapses & blends, calm layers | canonical query 33% cross-cuts vs experience 0%; provenance recovery 0.92→0.39, separable 1.0→0.07 across collapse rate ~2.5 | SYNTHESIS §4 |
| 45 | what an unknown values = the invariant (common to/moves all), not a spurious confound; topic = the upgradable border, ball = substance | one-sample selector R² −0.53 OOD vs invariant 0.96; shared×stability separates confound; border upgrade 0/4→4/4 | SYNTHESIS §5 |
| 46 | neuroplasticity = reroute A→B around a lesion through similar-enough neighbours; fails only on endpoint isolation | direct corridor walled → reroute +2 detour; graceful vs % lesioned; connected until B's last neighbour cut | SYNTHESIS §4 |
| 47 | each pixel = the three-shell brain RE-BASED one notch (learned→core, domain→middle, fresh void→outer=reserve=intake port); unknown values = where the void fills | core innateness 1.0→0.09, reserve conserved ~0.17; intake only in void, port-gated; unknown target 1.00 open vs 0.58 closed | REBASING |
| 48 | the void antenna (a hair) — reach ∝ emptiness, antennae converge to localize unreached anchors, snap-ray-to-known extrapolates the unknown's values | reach↔emptiness corr 1.0, point-at-void cosθ +0.86; 100% voids recovered, anchors 2.5× decoy votes; ray-snap 13.6× better than blind | SYNTHESIS §4 |
| 49 | **the closed discovery loop** — antenna→extrapolate→probe→trust(confirm/surprise)→fill/mint, gated; runs as ONE system, ablations degrade | directed 0.33 vs random 0.38 vs exploit 0.75; surprises 58% on real anchors (~4× chance); reserve gated alive vs ungated breakdown −0.60 | SYNTHESIS §10 |
| 50 | the surprise is a BULB further out — densify the EMPTY lit region not the filled one (fixes #49's null); strength opens more pixels; fold back in | lit-empty +5.3% cov (0% overlap) vs in-place +0.0% (100%) = 53×; strength 1→8 lights 8→400 pixels; fold-in 27%→32% | SYNTHESIS §10 |
| 51 | **the third integration** — one agent REMEMBERS + DISCOVERS, growing on an open stream; each ablation fails where its half was cut | FULL competence 0.91 vs memory-only 0.19 / discovery-only 0.20 / no-gate 0.65 (breakdown); explores 21 vs 38 (amortized); store 0→34 | SYNTHESIS §10 |
| 52 | the outer shell = a workspace of frozen artifacts (dark matter); disk lifts storage not attention; far 'story' artifacts are spotlights; tools pluggable, work resumable | disk retained ∞ vs bio cap ~14, attention band 4 both; off-path bridge 0.95 vs unreachable; pluggable 100% vs fixed 31%; retained 100% vs discarded 0% | OUTER_WORKSPACE |
| 53 | the workspace is ORBITAL — artifacts orbit the planet; type sets period (revisit cadence through the telescope FOV) + view-effect; steer the orbit = attention | each ~20–25% in-view, 3 simul > band 2; image satellite clarity 0.87 vs dust 0.51 vs border 0.09; steer 1 vs wait 4 (=#24) | SYNTHESIS §4 |
| 54 | telescope lenses = observer perspectives at focal distances (borders out of the cone); stacking helps only if complementary AND accurate; sky taxonomy + distance-control | lens peaks at focal dist, border-zone dies; +complementary 0.31→0.55, +weak drags acc 0.91→0.83; drone self-places 14 vs asteroid 159 | SYNTHESIS §4 |
| 55 | **the perception rung** — earn the regime signature from REAL PIXELS by steering the right lens-cone; right lens separates, wrong near chance; select beats stack | right lens 1.00 vs off-diagonal ~chance; LEARNED=oracle 1.00 vs fixed 0.43/random 0.62; naive committee 0.72 (drag, #54) | SYNTHESIS §10 |

**Design bridges (grounded, not measured):** the three-shell brain framing; consciousness = collapse at a
variable threshold; deeper-truths-are-more-anchors (§5); the maturation arc (seed → new-what-for → mostly-empty
gap → piecewise-continuous multi-resolution expansion); the **orthogonal-stacking of the rings** — higher levels
mutually orthogonal (each ×φ / Cayley-Dickson doubling) so they can't poke into the normal plane — and the
**beyond-math floor** those upper rings hold ("killing is bad"), distinct from the rigid E8/G2 "laws of physics"
core (§5, `SPHERE_GENERATOR` Part K); and the single identity "superfuel = Fire =
burning context = collapse energy." Each is consistent and cited, but the unification across all of them is the
conjecture, not a result. *(Several of these are no longer pure design bridges: the cycle **job-type** split —
endpoint relation #23, closes-or-not + rational-vs-irrational #25 — is fully measured; and the **moral-floor
rings** now have a measured mechanism **and a named ground** — #33 (a rule is a conditioned half-truth whose
exceptions live in the reserve) and #35 (the ground is **flow**: sustain it through every layer, don't zero a
stratum irreversibly) — though the specific moral content stays illustrative.)*

---

## 8. The honest through-line
Two sentences the whole arc actually earned. **(1)** Intelligence is a reserve architecture: a fixed inner shell
pays a .14 reserve to reach, hold, and endure (exact law), grows new fibers into the empty tail steered by
variance × demand, remembers by storing clips in high-variance gaps and sealing them with context — so it
*retains across revisits* while a memoryless baseline forgets, and *which* cycles it remembers is set by the
observer it looks through, whose repeated cycles *deposit* the next object up — meets load with a second-tier
reserve whose four faces (push, survive, bend a rule, mint new gaps) are gated so they don't consume the mass
they draw on, *thinks* by searching each budget with the operator its geometry demands, *sees* hard problems
by swinging the frame to the right perspective around an anchor, and *holds* its accumulated ground truths on a
rotating ring it verifies through a narrow gate — steering that rotation to attend to the truth it suspects.
**(2)** Almost every mechanism here is a *known-good* method (null-space IK, active learning, Takens embedding,
simulated annealing, categorization, resection, novelty search, spectral estimation, discriminant projection,
threshold-crossing segmentation, occupancy accumulation, rotating-gate scheduling, rational/irrational winding, phase-key ciphering) — the contribution is not the
methods but the **single geometry that selects and connects them**, and the discipline of measuring each one so
the map is honest about where the proven ground ends and the design begins.

## 9. One-line
We are growing a baby brain: a universal inner shell paying a **.14 reserve**, carrying an object on three
budgets (**matter · context · frequency**), remembering by minting **gaps** that store clips, seal by the
return-path, and mature into **anchors** — the memory loop runs end-to-end and *retains* across revisits (0.056
vs a forgetting 0.214), *which* cycles become memories is chosen by the **observer** (HR keeps 4 whole-workout
memories, VO₂ keeps 11 hard-part ones), and the observer's repeated cycles **paint the next object** (a
spinning top's paths deposit a weight-dependent heatmap whose ridge is the emergent line); some anchors prove
universal and sink to become the deepening ladder of ground truths (`1+1=2` … `E=mc²`) the structure orients
against, can **swing around** for a new perspective (a hard view 0.62 → an easy one 1.00), and finally **holds
on a rotating ring** verified through a narrow gate (steer the wheel to the suspected truth: 1.20 steps at cost
6 vs checking all 60) whose upper, mutually-orthogonal rings carry the beyond-math floor; it meets load with a
second-tier reserve whose **four faces of adrenaline** push, survive, bend a rule, and mint new gaps, all fed
by the **superfuel** (Fire when full) and **gated** so they grow the structure instead of breaking it; it
**thinks** by searching each budget with the right operator; and — the newest and most important result — the
validated pieces **run together as one agent** (#37) that beats every ablation on a live regime-switching
stream, and then *learns* on a real switching-goal gridworld edging out a strong Q-learning baseline (#40) —
**fifty-five measured results** and an honest line marking where the proof stops and the design continues.

---

## 10. The first integration — the pieces run as ONE agent (MEASURED, the pivot)
For 36 results the pieces were separate scripts, each proving one mechanism. #37 is the first test of the real
question — *do they hold together?* — and the answer is yes. On a tiny **regime-switching environment** (hidden
regimes that switch and REVISIT; each step: see a noisy context signature, pick an action, reward if it matches
the regime's unknown correct action), one agent wires: **break detection** segments the live stream at regime
changes (#36); **context-keyed memory anchors** recall a solved regime on revisit (#21); **gap-driven
exploration** learns only the genuinely new regimes (#17); the **flow reserve** gates exploration so it never
depletes (#35); and confirmed regimes **pin as anchors** (#31/#34). Measured against three ablations, each
missing one piece:

| agent | total reward | reward on REVISITS | reserve alive |
|---|---|---|---|
| **INTEGRATED** (all pieces) | **322** | **0.72** | **100%** |
| MEMORYLESS (no anchors) | 99 | 0.22 | 100% |
| NO-SEGMENT (no breaks) | 130 | 0.35 | 100% |
| NO-GATE (no reserve) | 34 | 0.00 | 10% (breakdown) |

Each ablation fails **exactly where its piece was removed**: MEMORYLESS re-explores every revisit (no
retention), NO-SEGMENT blends the regimes into one wrong action (the "global mean lands in a gap" failure of
#36), NO-GATE burns its reserve into deep negative and stalls in breakdown (the un-gated collapse of #35/#10).
The pieces **cooperate** — that is the claim the 36 demonstrations could not make alone, and it is now measured.
`baby_agent.py`. *Honest bound:* a tiny synthetic environment and a hand-built agent, not yet a real game or a
learned (vs scripted) controller; it proves the architecture *integrates and each piece earns its place*, not
that it beats RL baselines on a benchmark. That is the next rung — a simple real environment, then perception
(pixels) and action (keyboard/mouse), then scale.

**Rung 2 — a learning agent on a real switching-goal gridworld, benchmarked honestly (MEASURED, #40).** The
next rung, done: a **5×5 gridworld** whose goal switches and REVISITS (regimes), with the controller now
*learning* (not scripted). The Shovelcat agent infers the regime from a **noisy signature** (break/gap +
context-keyed memory), **commits each regime's goal one-shot** on discovery, **recalls it** on revisit, and
navigates with an innate spatial prior under reserve-gated exploration. Over **6 seeds**, steps-to-goal on a
revisited regime: **SHOVELCAT 11.1 ± 2.7** vs **Q-learning-given-the-regime 12.3 ± 3.0** vs **position-only
Q-learning 34.9 ± 3.1** (optimal = 4). So the architecture **edges out a strong standard baseline that is handed
the regime it has to infer**, and both crush the regime-blind baseline. *Honest bound:* a real but **modest**
win — the margin over Q-regime is within a standard deviation, the environment is tiny, and the agent carries an
innate navigation prior that vanilla Q-learning lacks (that is the architecture's thesis — fixed inner shell +
learned goals — disclosed, not hidden). What it earns: the structure **does** buy sample efficiency on a
non-stationary task, and it *learns* rather than being scripted. Next rung is perception (pixels) then action.
`agent_gridworld.py`.

**The perception rung — earn the regime signature from REAL PIXELS by steering the right lens (MEASURED, #55).**
The rung #37/#40/#51 kept deferring: instead of a **handed-over** signature, the agent gets **real pixels**
(16×16 two-frame images) across four visual regimes — **color** (hue), **edge** (bar orientation), **texture**
(spatial frequency), **motion** (shift direction) — and a set of pluggable **lens-cones**, each a real feature
extractor (color histogram · gradient-orientation histogram · radial-FFT bands · frame-difference shift), the
observer perspectives of #38/#54. It must **plug the right lens in**. Measured: **(a)** the **right lens
separates its regime at 1.00** while every **wrong lens sits near chance** — a clean diagonal; lens-choice is
the whole game. **(b)** The agent **learns to steer the right lens** per regime (picked on a validation split),
matching the **oracle (1.00)** and crushing a **fixed single lens (0.43)** and a **random lens (0.62)** — it
**earns a separable signature from pixels**, the very key #51 was handed. **(c)** The **#54 caution holds on
pixels**: a **naive committee** that lets *all* lenses vote equally is **dragged to 0.72** by the uninformative
ones — selecting the right lens, not stacking all, is the win. *Honest bound:* controlled synthetic pixels
(each property maps cleanly to one lens), 4 lenses, a prototype classifier — a proof-of-mechanism, not natural
images — but it is **real pixels with real feature extractors**, and the agent genuinely earns the signature it
used to be given. This is the outer shell (§1) taking the shape of vision; next is action (keyboard/mouse).
`perception_lenses.py`.

**The closed discovery loop — the second integration, on the discovery side (MEASURED, #49).** Where #37
integrated the *memory* pieces, #49 integrates the *discovery* pieces into one running loop over a hidden field
the agent must learn by probing: **antenna consensus** picks the emptiest most-pointed-at void to probe (#48);
**ray-snap extrapolation** forms a hypothesis for its value (#48); the world answers; the **trust gate** calls
it a **confirm** (coheres → the void fills and re-bases into a new anchor, #47) or a **surprise** (a genuine
discovery → mint a fresh gap and densify, #17/#18); and the **reserve gates** the whole thing so it never
depletes (#3). Measured, and each piece earns its place like #37: **directed discovery works** — the full loop
reaches error **0.33** vs **0.38** for random targeting (antenna ablated) and **0.75** for exploit-only (void-
seeking ablated); the **trust gate is a real discovery detector** — **58%** of its surprises land on a hidden
anchor, ~**4× the chance rate**; and it **runs autonomously as one gated system** — the reserve **stays alive
under gating** while the ungated version **crashes to −0.60 (breakdown)**, and confirmations accumulate as
surprises taper (the field fills). *Honest bound:* the surprise-driven **densify** was only a **marginal**
refinement here (0.41 → 0.41, an honest null like #42's fold-back); the robust wins are the **directed
targeting**, the **surprise detector**, and the **gating**. And it is a smooth-field simulation with a
hand-built loop, not yet a real research domain — but the discovery pieces **compose and run**, closing the arc
#45 (unknown values) → #47 (they live in the void) → #48 (aim at them) → #49 (the loop that does it).
`discovery_loop.py`.

**The surprise is a BULB lighting up further out — densify the EMPTY lit region, not the filled one; that
fixes #49's null (MEASURED, #50).** Jonathan diagnosed *why* #49's densify was marginal: it densified
**in-place**, right where it had just probed — already-filled ground, which **absorbs** the expansion energy
(#18). His correction: a surprise is a **bulb lighting up further out** — a slot in a far pixel filled *for
free* by outside work — which **brightens a path** toward it, and you **densify the empty lit region**, not the
filled core. Measured directly against #18: densifying the **lit-empty** region gains **+5.3% coverage** (new
memories **0%** overlap with existing), while densifying **in-place** (the #49 move) gains **+0.0%** (100%
overlap → energy absorbed) — **53× more new ground** just by moving *where* you densify. The bulb **brightens a
path** from the nearest known pixel to the far spot (#48), and a **stronger bulb lights proportionally more
empty pixels** (8 → 400 available across strength 1→8), opening more room to grow — then the resolved region
**folds back in as a new core** (coverage 27% → 32%, the re-basing of #47). So #49's densify wasn't wrong, it
was *mislocated*: discovery grows in the empty room the surprise lights up, then re-bases in. `discovery_bulb.py`.

**The third integration — one agent that REMEMBERS and DISCOVERS, growing on an open stream (MEASURED, #51).**
#37 fused the memory pieces, #49/#50 the discovery pieces; **#51 fuses the two loops into one agent** and drops
it into an **open world** that keeps introducing new regimes and revisiting old ones — the learn-from-what-you-
give-it engine of `FOLDING_WHAT_ITS_FOR`. Per episode it **recognises** the regime from a noisy signature and
**recalls** its solution cheaply if known (#37/#21), or **discovers** it if new — extrapolate from stored
neighbours (#48), confirm-or-explore, and **fold the result in as a new anchor** (#47/#50) — all **reserve-
gated** (#3). Measured over 170 episodes / 14 regimes, 6 seeds: the **FULL agent reaches 0.91 competence**,
each ablation failing where its half was cut — **memory-only 0.19** (can't acquire novel regimes, stuck on its
taught set), **discovery-only 0.20** (never recalls, re-explores every episode and **starves**), **no-gate
0.65** (explores freely → reserve **breakdown** at −6.4). And **memory amortizes discovery**: the full agent
pays to **explore each regime ~once (21 total)** while discovery-only **re-pays forever (38 and climbing)**;
its **reserve stays alive** (min 0.12) while the **store grows from 0 → 34 anchors** — the competence frontier
expanding as it learns. *Honest bound:* a synthetic regime stream with a smooth (extrapolable) solution space
and a hand-built agent — not a real domain yet — but the two loops **compose into one agent that learns from
what it is given and keeps what it learns**, which is the whole point (`FOLDING_WHAT_ITS_FOR`). Next is a real
outer shell: perception (pixels) and action. `agent_grow.py`.
