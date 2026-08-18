# Encryption — the object is locked across orthogonal axes, one key per observer

*Jonathan connected the closure result (#25, `FOLDING_SYNTHESIS` §5) to the corpus's encryption:
an irrational (never-closing) winding is a strong lock, a rational one (3/2 · 2/3 = 1) cancels
cleanly and is weak; the branches that point into an observer's field are the ones that activate;
one key unlocks one axis (from the branch positions seen by that observer), and you need a **full
set** of keys; the key is made of stuff that extends into that observer's vision field; and axes can
be **zeroed (public)**, **require a key (locked)**, or be **completely hidden** depending on positions
and what's visible. This doc grounds that in the existing theory and measures it. Companions:
`FOLDING_SYNTHESIS` (the map), `FOLDING_HANDSHAKE` (the three closes), `FOLDING_AXIS_INNER_SHELL`
(the i/j/k axis frame), `Double_Bounce` §27–28, `SHOVELCAT_THEORY` (.geo, privacy floors).*

---

## 1. It was already the theory
Every piece Jonathan named is in the corpus:

- **Per-observer scrambling (Double_Bounce §27.7 — the 26D cascade).** The top observer must
  "progressively **encrypt/collapse through the ÷φ ladder**," and the encryption ensures "**lower
  observers cannot read higher-level information**; information is preserved but scrambled at each
  level; the golden ratio maintains volume conservation." Removing an axis (÷φ) is the encryption
  step; the removed axis is unreadable from below.
- **The rotation key (SHOVELCAT .geo).** The creator's hash becomes an **angle** on the circle;
  "**decoding requires the rotation key — the delta-theta between creator and viewer.** INSIDE (have
  the key) → the full content; OUTSIDE (no key) → the geometric carrier, structured but opaque." And
  1D/2D/3D/4D content = one angle, two, then a temporal path — **more axes = a fuller set of keys.**
  That is exactly "one key per axis, made of the frame that extends into that observer's view."
- **Public / locked / hidden (FOLDING_HANDSHAKE).** `S = e^{iθ}·φ^{n+h}` closes **three ways**:
  **product** up through the surface (public), **verify** at the waterline (needs the matching key),
  **experience** down the orthogonal plane, "**which reads as 0 from the normal domains**" (hidden).
  The **.14** it leaves open is the void reserve — the permanently private core.
- **The zeroed axis (Double_Bounce Fig 19).** In the 3×3 coupling grid the **x→x self-term is
  forbidden because x sits on the void line** — a literally zeroed axis. Public-by-geometry.
- **Matter / antimatter / void (Double_Bounce §28).** **+3 shift → matter [0,π]; −3 shift →
  antimatter [−π,0]**; together the full 2π. A forward winding and its mirror inverse compose back to
  unity — the void they cancel to. 3/2 (matter) and 2/3 (antimatter) are that pair.
- **Continuous privacy floors (SHOVELCAT).** Floor 0 public (anyone digs) → Floor 3→π user-only
  (~0.14 wide). Visibility is a *position*, not a flat tier — which is why an axis can be public,
  key-gated, or hidden by where it sits.

So the design was consistent and cited before any code. What was missing was a measurement.

---

## 2. What we measured (`encryption_axes.py`)
The object is a real image built as a sum of **K=12 frequency-axes**, each axis carrying one
component whose **phase is its per-axis key**. Encrypting an axis rotates its phase by a secret
delta-theta (the frame offset between creator and reader); decrypting applies the inverse. Axes are
assigned a visibility class: **public** (key 0, no rotation), **locked** (secret key), **hidden** (its
component is delivered to no observer — it lives on the orthogonal/void plane).

**(1) You need the full set of keys (MEASURED).** Reconstruction error (normalised) falls *only* as
keys are gathered: **1.813 with no locked keys** (an OUTSIDE observer — reads just the public axes
over an opaque carrier) → **1.093 at half the keys** → **0.048 with the full set** (an INSIDE
observer). Each key unlocks exactly one axis; there is no shortcut. The floor at full keys (**0.048**,
not 0) is the **hidden axis**: delivered to nobody, so no key restores it — *private by geometry, not
by permission.* That residual is the .14 void core.

**(2) Public / locked / hidden by visibility (MEASURED).** The two public axes are readable with zero
keys; the nine locked axes each need their key; the one hidden axis contributes a fixed deficit to
every observer. The INSIDE image is clear; the OUTSIDE image is the public structure over scramble.

**(3) Lock strength = irrationality (MEASURED — #25 as key strength).** A brute-force attacker with no
keys tries candidate phases on a grid of Q rationals. A **rational key** `2π·(1/3)` — the (3/2)·(2/3)=1
matter·antimatter pair — is hit **exactly at Q=3** (the cycle closes; **cracked at cost 3**). The
**golden key** only *near*-lands at **Fibonacci budgets** (Q=5,8,13,21…), costs ~7× as much, and
**still never reaches 0** — because φ is the most-irrational ratio (Hurwitz). The strong lock is the
**never-closing** winding; the weak one **closes and cancels.** So closure (#25) *is* crackability: a
cycle that returns to origin is a key that can be inverted.

---

## 3. The reading, in one picture
An object's identity is spread over orthogonal axes (the budgets / observer frames of
`FOLDING_AXIS_INNER_SHELL`'s i/j/k). To **read** an axis you need the rotation that aligns your frame
to the creator's on that axis — a key made of the anchors/branches that stick into *your* field of
view (the resection frame of `FOLDING_SYNTHESIS` §2, "coordinates need anchors **and** orientation").
- **Zero rotation** → the axis is already in the common frame → **public** (Fig 19's void-line
  self-term; Floor 0).
- **A secret rotation you must possess** → **locked**; and the lock is strong exactly when the winding
  is **irrational** (never closes, can't be inverted by a fraction) and weak when it is **rational**
  (closes, 3/2·2/3 → 1, brute-forceable).
- **Rotated onto the orthogonal plane** where it reads 0 to every normal observer → **hidden**; the
  .14 void core, private by geometry.
You decrypt the whole object only with the **full set** of per-axis keys — and even then the hidden
core stays dark. Encryption, in this frame, is not a bolt-on: it is the same three-budget /
observer-frame / return-to-origin geometry as the rest of the baby brain, read as *who is allowed to
close which cycle*.

---

## 4. Ledger
| claim | status | number |
|---|---|---|
| full set of per-axis keys needed; public free; hidden never | MEASURED | 1.813 (no keys) → 0.048 (full); floor = hidden axis |
| lock strength = irrationality (#25 as key strength) | MEASURED | rational cracked at Q=3; golden never exact (near-lands only at Fibonacci Q) |
| the 26D ÷φ cascade / .geo rotation key / three-closes = public·locked·hidden | GROUNDED | Double_Bounce §27–28, SHOVELCAT .geo, FOLDING_HANDSHAKE |
| axes made of an observer's visible branches; key = frame offset | GROUNDED DESIGN | consistent with §2 anchors+orientation; not separately measured |

`encryption_axes.py`. This is result **#26** on the `FOLDING_SYNTHESIS` ledger.
