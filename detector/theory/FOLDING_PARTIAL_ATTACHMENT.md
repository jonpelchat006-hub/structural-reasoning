# Arms that only partly stick — and what the falling-off tells you

*2026-07-28. Jonathan: "When we make the arms would it be like parts of it can't stick and fall out?
Then we would want to replace those sections with other arms that would figure out WHY the last one
couldn't stick? … and if that's missing a section we find another arm?"*

**All three claims hold, and the middle one — that the failure to stick is itself evidence — is the
valuable one. It also found a live safety hole: the engine was treating two completely different kinds
of silence as the same thing, and on this corpus that would have meant accusing two genuine
professional photographs.**

---

## 1. Four attachment states, not two

The engine had `fired` and `silent`. Silence is actually three different things:

| state | meaning |
|---|---|
| **FIRED** | attached, and the claim is contradicted |
| **HELD** | attached, tested, claim survived — *silence as evidence* |
| **NO_GRIP** | could not attach; the **reason is informative** |
| **GAP** | could not attach; the reason is **our** missing reference |

`HELD` is the state the first coverage pass wrongly called a hole (`FOLDING_WINDOW_COVERAGE` §3).
`NO_GRIP` vs `GAP` is the new distinction, and it is a safety property, not bookkeeping.

## 2. Do arms partly fall off? Yes

163 files, 7 arms, per-file window coverage:

| window covered | files |
|---|---|
| 0–30% | 19 |
| 30–50% | 35 |
| 50–80% | 0 |
| 80–100% | 109 |

**Mean coverage 77.7%, and it is partial (neither 0 nor 1) on 54 of 163 files.** Arms do not attach
all-or-nothing. The catalogue arms in particular are a bundle that grips or slips as a unit depending
on whether the file offers an anchor.

## 3. The falling-off is evidence — and this is the safety fix

| failure mode | AI | camera 5 | capture | edit | web real |
|---|---|---|---|---|---|
| fully attached | 0 | 2 | **74** | **33** | 0 |
| **NO_GRIP** (file has nothing to grip) | **17** | 3 | 0 | 0 | **32** |
| **GAP** (our catalogue is missing) | 0 | 0 | 0 | 0 | **2** |

The two failure modes have **completely disjoint populations**.

- **NO_GRIP** is where every AI image and every stripped web photograph sits. The file *was stripped*,
  and that is a real fact about its history.
- **GAP** contains exactly two files — and they are a **Sony ILCE-7RM2 and a Nikon D3000**. Genuine
  professional cameras, absent from a catalogue that currently holds one phone.

> **If GAP were scored as evidence, the engine would have flagged two real photographs from real
> cameras for the crime of not being a Galaxy S23 Ultra.** That is the exact failure mode this whole
> project exists to avoid, and it was one line of code away.

The rule that falls out: **a failure to attach counts as evidence only when the reason is a property of
the file. When the reason is a property of us, it must contribute exactly nothing.**

## 4. Where the residual sends the next arm

| reason an arm fell off | n | next arm |
|---|---|---|
| file is PNG, not JPEG | 96 | pixel: resampling / compositing trace **[B]** |
| no device asserted | 68 | pixel: sensor-noise presence **[B]** |
| no EXIF to grip | 64 | pixel: sensor-noise presence **[B]** |
| file is WEBP, not JPEG | 18 | pixel: resampling / compositing trace **[B]** |
| `SONY\|ILCE-7RM2` not in catalogue | 4 | **catalogue enrolment (~20 frames)** — no arm helps |
| `NIKON\|D3000` not in catalogue | 4 | **catalogue enrolment (~20 frames)** — no arm helps |

**Every route leaves the container observer**, and that is forced rather than chosen:
`FOLDING_WINDOW_COVERAGE` measured the container tier at 96.6% of the *history* window and 0% of the
*authorship* window. A container arm cannot fill a container arm's hole.

Note the GAP rows route to **data, not to another arm**. That is the honest answer for that branch:
when the failure is ours, no cleverness substitutes for enrolment.

## 5. Does the recursion terminate? Yes, at depth 4

| # | observer | arm | falls off when |
|---|---|---|---|
| 1 | A container | layout vs claimed device | the file carries no device claim |
| 2 | B pixel | sensor-noise presence (PRNU) | no reference enrolled for the source device |
| 3 | B pixel | region colour identity | no original supplied to diff against |
| 4 | C semantic | does the content read as generated | **terminal** — needs nothing but the file |

**It terminates because each fallback requires strictly less context than the one before.** That
monotone decrease is what makes the recursion safe: the chain cannot loop, because there is nothing to
route back to.

**And the costs run in exactly the reverse order.** The arm that needs the most context is free; the
arm that needs nothing is the only one you pay for (~0.4c). So Jonathan's routing is *simultaneously
the accuracy design and the cost design* — run the context-hungry arms first, because when they stick
they are both cheaper and stronger, and only fall through to the paid arm when they genuinely cannot
grip.

That is a better justification for the tiering in `PRODUCT_SPEC_DROP_A_PICTURE` than the one I gave it,
which was essentially "run the cheap thing first." The real reason is that **context and cost are
inversely related, so the greedy-by-context order is also the greedy-by-cost order.**

## 6. What this changes in the engine

1. **`verdict.py` must distinguish NO_GRIP from GAP structurally**, not in prose. Currently the
   catalogue-gap case prints a disclaimer; it should be a different state that provably cannot enter
   any likelihood computation.
2. **`HELD` should be reported.** "Four checks ran and all four passed" is a stronger statement than
   silence, and it is what a genuine capture actually earns (0/61 false positives).
3. **The router should be explicit and inspectable** — the user should see *"this arm could not attach
   because X, so I sent Y instead"*, which is the same explain-your-reasons standard as the rest of the
   output.

## 7. Honest limits

- The four-state model is measured only on the **container** observer. The pixel and semantic arms have
  not been expressed in it yet, so the depth-4 chain is a design derived from measured constraints, not
  a measured chain.
- **n = 2 in the GAP bucket.** The safety argument rests on mechanism (a catalogue of one phone cannot
  speak about a Nikon), not on that sample. Both directions of the argument would strengthen with more
  device diversity in the corpus — which is the same data request as growing the catalogue.
- Partial attachment is currently bimodal (0–50% or 80–100%) because the catalogue arms grip or slip as
  a bundle. Finer-grained arms would give a smoother coverage measure, and it is an open question
  whether that buys anything.

**Code:** `attachment.py`, `attachment.json`.
