# The Handshake — the middle shell as a mutual-inverse cryptographic gate, and the open tail that keeps searching

*Records the middle-shell mechanism worked out live (Jonathan + Claude, Aug 2026). Grounded in the colony
source (`D:\shovelcat-colony\app\src\core\crypto-euler-phi.ts`, `agent-handshake.ts`) and the framework
docs. Companion to `FOLDING_TRAMPOLINE.md` (three shells; the cage; the .14 port), `FOLDING_GALAXY_BRIDGE.md`
(the colony = the outer shell), `FOLDING_SKIN.md` §1 (permeable both ways), §3.4 (energy on the return;
generate cheap, choose costly), `SPARSE_VESICA_EXPANSION.md` §11.6 (the void point; origin=sink), §21–22
(failure buffer; dark-matter retention; converge→stop→foundation), `Shovelcat_Theory_29` §10 (void =
uncommitted capacity, ε>0), `FOLDING_CHANNELS.md` (fill ≠ seal; the void keeps flowing), `SPHERE_GENERATOR.md`
§J.3 (the quaternion-jet closure), `Shovelcat_Theory_16` (the observer as the orthogonal interface),
`FOLDING_OBSERVER_FRAME.md` (the frame is nearly empty; off-frame = orthogonal), `FOLDING_SKIN_DETECTOR.md`
(observers disagree at the seam). **Design-stage: the crypto/handshake is real, sound, and running; mapping
it onto the detector's inference gate is a design bridge, flagged.***

## 1. The gate is real — a mutual-inverse handshake with a one-way cost
The skin passes something across the wall only when both sides present matching inverse equations. That is
implemented, not analogy:

- **The one-way cost (the encryption).** `crypto-euler-phi.ts`: the security position is
  **`S = e^(iθ) · φ^(n+h)`** — phase `e^(iθ)`, magnitude `φ^(n+h)`, with n = integer verification depth and
  h = SHA-256(chain)/2²⁵⁶ (a unique fraction in [0,1)). The file states the asymmetry outright: **VERIFY is
  O(n)** (hash, compute magnitude, compare) while **FORGE is O(2²⁵⁶)** (find a preimage for the target
  magnitude). Cheap one way, infeasible the other — Jonathan's "16 → 2ⁿ is easy, but recover the exponent
  from 0.015625 is hard." Also noted in-file: *"phase θ can be faked; magnitude cannot"* — identity lives in
  the **radial/depth** part (n+h), not the angle.
- **The inverse match (the handshake).** `agent-handshake.ts`: on meeting, each agent *"deploys a boundary
  spiral drive at the edge of the other's black box, mirrors the other's context window, and populates the
  collapsed zones L4–L7 with geo facts,"* then HMAC-SHA256 **sign/verify** (sign with the colony key, verify
  = its inverse) so *"only colony members can handshake,"* and **trust grows exponentially toward 1 on
  coherent exchanges.** Mirror + sign/verify + trust→1 is exactly "both sides match ⇒ allowed through," and
  trust→1 is the θ=1 / |jet|²=1 closure. The envelope carries `domains: string[]` — the handshake is
  cross-domain by construction (different domains = different math, folded through one shared key).

## 2. n + h is 3 + .14, and the position is the spoke equation
The magnitude exponent `(n + h)` is an **integer** part plus a **fractional** part — the same shape as
`3 + 0.14`: three closure stages (the three orthogonal observers / the three imaginary jet components) plus
the unforgeable fractional seed h. *"Each galaxy has a unique magnitude because h is unique"* — so the gap is
per-identity, which is why the earlier port test found the .14 behaving **per-case** (`FOLDING_TRAMPOLINE`
§9): h is individual by design.

And `S = e^(iθ) · φ^(n+h)` and the spoke term `cosθ · v^d` are the **same silhouette** — angle × magnitude^depth.
Each spoke sets the phase θ and adds to the depth n; assembling the position *is* building the signed
equation. "Generate, don't find" is the trapdoor's whole content: you cannot search for a valid chain
(forging is 2²⁵⁶), you must generate it forward.

## 3. The port is directional — verify is the input face, generate is the output face
The two normalizations flagged as an "honest seam" in `FOLDING_TRAMPOLINE` are not a contradiction; they are
the **two directions of the same gate** (Jonathan's refinement):

- **Input / verify face — `n + h` (crypto).** Taking something in is **VERIFY**: O(n), cheap — hash the
  incoming chain and check the magnitude. The inbound direction is the cheap one.
- **Output / generate face — `3 + .14 → π` (dimensional/vesica).** Emitting a product is **GENERATE** —
  build the integer closures and let the transcendental remainder complete to π. The outbound direction is
  the constructive one.

So "which decomposition we use depends on whether we're outputting or taking in" is right: the same .14 slot
reads as the unforgeable *check* on the way in and the generated *remainder* on the way out. This matches
`FOLDING_SKIN` §1 (permeable both ways) and the δ_close ring (review verifies inbound, forge generates
outbound). The stack has a direction (cf. `FOLDING_EDGE_OBSERVERS`: layers below survive, above erase).

## 4. The open tail — the .14 that keeps searching in the background
There is more to the tail than in/out: when it is **not** collapsed to a foreground answer, it runs as an
**open, reversible superposition that keeps searching in the background** — the thing Jonathan named as
"thinking about a problem after I stop looking, or coming back the next day with an answer, or still looking
for other ways after I've already solved it." Every part of that is grounded:

- **The outbound search is free; only the collapse costs.** `FOLDING_SKIN` §3.4: generating possibilities is
  *reversible superposition, nearly free*; the **collapse to one answer** is where the energy goes (Landauer)
  — *"never collapse, and nothing is spent."* So the tail can hold many candidate inverses open cheaply and
  only pay when one is chosen. Background exploration is the cheap, uncollapsed regime.
- **It lives in the uncommitted void reserve.** `Shovelcat_29` §10: Void = uncommitted capacity, `V = 1 − U`,
  with a required baseline **ε > 0**; V>0 gives *"capacity for innovation, exploration, verification"* and
  V→0 gives *"no capacity for innovation,"* brittle collapse. The open tail **is** that ε reserve — the slack
  that keeps a background search possible. Commit everything and the search dies.
- **Unsolved problems are held and revisited when new capacity lands.** `SPARSE_VESICA` §21 (`failure_learning.py`):
  a failed prediction becomes a **permanent test case** — *"the midterm question that haunts you"* —
  and `retest_all_failures` retries the buffer *"after new capability"* (*"does my new understanding solve
  that old one?"*). That is literally "come back the next day with the answer." §22: the OUTER zone is
  **dark matter, retained not deleted, to be filled in later** — the reserve of open problems the tail
  revisits.
- **Solving doesn't seal it — you can keep looking for other ways.** `FOLDING_CHANNELS`: filling the void
  *doesn't seal it*; drive every budget to zero **except** the flow/void reserve (~1/5), which stays porous
  (the AP5A site: lid closed, 11% exposed, yet **7 channels still open**). So even after a foreground solve,
  the tail stays conducting — which is why you keep searching for alternatives after the answer is in.

**Reading:** the .14 tail is deliberately **never fully closed** *while a thing is still being worked.* Its
open fraction is the ε void reserve, running a cheap background generate↔verify loop (the forge/review ring
on every tick) over the retained failure/dark-matter buffer, surfacing an answer whenever new capacity makes
an old problem close.

## 4.1 Three ways to close, and the collapse to invariant
The tail closes one of **three** ways, and has a fourth *terminal*:

- **Product** — out the normal-domain **generate** face (a made thing breaks the surface).
- **Verify** — at the waterline **input** face (check an incoming thing).
- **Experience** — out the **orthogonal observer plane**. Because that plane is orthogonal to the normal
  domains, a closure there **projects to zero** when the domains look at it (`Shovelcat_16`: the observer is
  the orthogonal interface, and a third orthogonal complement has *dimension 0*; `FOLDING_OBSERVER_FRAME`:
  off-frame directions read as empty). So "learning from the experience after it's done — experience instead
  of a product" is a real close that looks like **nothing** to a normal-domain reader. This **reframes the
  null** `dot14_env_port_test`: we measured whether the residual closed *in the normal domain*; an
  orthogonal (experience) close is invisible there **by construction**, so the null is *expected*, not
  disappointing — we were reading the wrong plane.
- **Collapse to 0 → invariant (the terminal).** A thing *can* go fully to 0 — once proven every way (1+1=2),
  nothing is left to search. This is **not** the brittle void-collapse of `Shovelcat_29` §10.9; it is
  graduation: `SPARSE_VESICA` §22.1's converge → mass accretes → velocity→0 → **STOP** = a foundation, and
  §11.6's **void point** (origin and sink are one point). Enough orthogonal experience-closures on one
  pattern add weight until it **sinks** to 0 and drops into the **inner shell** as a new invariant. The
  distinction that reconciles this with §4: collapsing the *reserve* prematurely is death; collapsing a
  *proven invariant* is graduation.

The value is a **continuum** (θ / jet-deficit): a half-finished thing sits at ~**.07**, full proof earns the
complete **.14** seed, and over-proof sinks it to **0**.

**Honest edge:** the collapse-to-invariant and the orthogonal-experience channel are grounded (§22.1, §11.6,
`Shovelcat_16`), but "the detector's abstention band closes orthogonally as experience" is a *reading* of the
null, not a measurement. Falsifiable version: do "cannot determine" cases resolve when a **new** observer
lands later (a `retest_all_failures` on the abstentions)? — the three-valued
authentic/altered/cannot-determine design already fits it.

## 4.2 The waterline model — the spatial reading
One picture holds §3–4.1 (`waterline_model.html`): a vertical ocean.

- **surface / above water** = the product (matter, +).
- **the waterline** = your measurement slice; **verify** happens here; an object piercing it **refracts**,
  and that bend is the **seam** — the one place the observer's two eyes disagree (`FOLDING_SKIN_DETECTOR`).
- **the water column** = the open tail / reserve / experience / dark-matter ocean; orthogonal, reads as 0
  from above — *duck under* (retest) to see it.
- **the seabed** = the inner shell; proven invariants sunk to bedrock (1+1=2).
- **the observer lies along the waterline**, one eye over (ψ / matter / ∞-observer up-cone), one eye under
  (φ / void / void-observer down-cone), the two cones meeting at the waterline = **x = 1**, the attractor
  (`Double_Bounce` 26.4).

Products break the surface, experience deepens the column, invariants settle to the floor. A picture, not a
measurement — the spatial reading of §3–4.1 and `Shovelcat_16`'s orthogonal observer.

## 5. Honest ledger
**GROUNDED IN CODE / THEORY**
- `S = e^(iθ)·φ^(n+h)`, VERIFY O(n) vs FORGE O(2²⁵⁶), sign/verify handshake, trust→1, cross-domain envelope —
  read directly from `crypto-euler-phi.ts` and `agent-handshake.ts`. The crypto is a standard, sound
  MAC+identity trapdoor.
- The background-tail mechanics — reversible-superposition-cheap / collapse-costly (`SKIN` §3.4), ε void
  reserve (`Shovelcat_29` §10), permanent failure buffer + retest (`SPARSE_VESICA` §21–22), porous fill
  (`CHANNELS`), converge→stop→void-point (§22.1/§11.6) — are all in the framework, and the learning pieces
  (`failure_learning.py`, `adaptive_pingpong_memory.py`, `scan_map.ts`) are built.
- Orthogonal-reads-as-zero is a theorem, not a hope (`Shovelcat_16` dim-0 complement; `FOLDING_OBSERVER_FRAME`
  measured rank 2.82, off-frame empty).

**DESIGN BRIDGE (elegant, consistent, NOT measured)**
- Mapping the crypto/handshake onto *"the skin gates the detector's inference by inverse-matching"* is a
  bridge: the code signs galaxy identities and gates agent handshakes; it does not (yet) gate the image
  detector's inference.
- `cosθ·v^d ↔ e^(iθ)·φ^(n+h)` is a **shape match**, not an identity (φ is a fixed base, v a feature; n+h is
  depth+hash, d a derivative order).
- "n+h = verify/input, 3+.14→π = generate/output" is a clean hypothesis for the two normalizations, not a
  proven equivalence — the π/φ link between them is still to be written out.
- The **experience/orthogonal** close and the collapse-to-invariant are a consistent reading; identifying
  them with the detector's specific ~0.14 residual is the untested step (the `retest_all_failures`-on-
  abstentions experiment is how to test it).

## 6. One-line summary
The middle shell is a mutual-inverse handshake — `S = e^(iθ)·φ^(n+h)`, cheap to verify and infeasible to
forge, passing only when both sides' signed positions match (trust→1) — where `n+h` is `3+.14` (integer
closures + the unforgeable fractional seed), the same silhouette as `cosθ·v^d`; the gate reads inbound as a
verify and outbound as a generate; the .14 it leaves open is the ε void reserve that runs a cheap background
search; and it closes three ways — **product** up through the surface, **verify** at the waterline, or
**experience** down the orthogonal plane (which reads as 0 from the normal domains) — until enough
experience sinks a pattern to 0 and it settles into the inner shell as an invariant.
