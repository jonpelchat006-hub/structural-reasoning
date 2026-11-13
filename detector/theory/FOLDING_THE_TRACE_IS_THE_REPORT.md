# The trace is the report — and one of my earlier claims was measured wrong

*2026-07-28. Jonathan: "That could be where the story comes from too right? It's all just collecting
evidence, not proof, and we are making a case for what we think to other people. It would be helpful
for people to know this arm failed here and was able to be replaced with y, which usually means z
happened. And then our report could be what the arms ended up being from all the observers."*

**The story is real and it is worth +27.6% over the best single arm. But the extra state detail buys
exactly 0.0%, and I have to report that rather than dress it up. And it forces a correction to
`FOLDING_WINDOW_COVERAGE`'s saturation claim.**

---

## 1. There are only eight stories

163 files, 7 arms, four attachment states each. Distinct traces: **8**.

> `o` held (tested, passed)  `X` fired (contradicted)  `-` slipped (nothing to grip)  `?` gap (our reference missing)

| trace | n | usually means | purity |
|---|---|---|---|
| `ooooooo` | 73 | **a coherent capture** | 72/73 = **99%** |
| `oooXXoo` | 34 | **a capture whose metadata was re-authored** | 31/34 = **91%** |
| `oXX----` | 25 | **a web-pipeline file, history stripped** | 25/25 = **100%** |
| `X------` | 19 | not a capture container at all | 15/19 = 79% ⚠️ |
| `ooX----` | 8 | JPEG with no device claim | 5/8 = 62% |
| `oXo????` | 2 | a camera we do not have a reference for | 2/2 = 100% |

Pre-registration 1 holds hard: **files are made in a handful of standard ways, not 163 unique ones.**
Each row is a sentence the report can say out loud with its own n attached — which is the same standard
the rest of the output already holds itself to.

⚠️ **`X------` at 79% is contaminated** and must not be quoted as an AI detector. It is the PNG/WEBP
trace, and `FOLDING_WINDOW_COVERAGE` already flagged `is_png` as a **collection artifact** — the AI
images are PNG because that is how Midjourney hands you a download, not because they are generated.
The trace is honest about *container*; it says nothing about *authorship*.

## 2. The measurement — and the pre-registration it failed

Leave-one-out accuracy (predict each file's class from the majority class of the *other* files sharing
its key; without LOO a singleton group scores 100% by memorising itself):

| encoding | LOO accuracy |
|---|---|
| best single arm (`thumbnail_present`) | **64.4%** |
| all arms, binary fired/not | **92.0%** |
| **full four-state trace** | **92.0%** |

**Pre-registration 3 failed.** The four-state trace adds **+0.0%** over the binary fired/not encoding.

The reason is structural and, once seen, obvious: **the slip and gap states are not independent bits —
they are implied by the fire pattern.** If `device_claim_present` fires, every catalogue arm downstream
*necessarily* slipped; the router determined it. So the extra states describe the routing, not new
evidence about the file.

## 3. But it beats the best single arm by 27.6% — and that corrects an earlier claim

`FOLDING_WINDOW_COVERAGE` §6 reported that *"the posterior saturates at one decisive arm."* That is
true as measured but I stated it too broadly, and the correction matters:

- **What saturates:** among files that already have one firing arm, adding a *second firing arm* does
  not sharpen the posterior. Still true.
- **What does not saturate:** using the *whole pattern across all seven arms* — including which arms
  **held** — beats the best single arm by **+27.6 points** (92.0% vs 64.4%).

> **The information is in WHICH arm fired, not HOW MANY.** A capture is identified by seven arms
> holding. An edit is identified by exactly two firing while five hold. Neither statement is available
> from a single arm, and neither is a matter of accumulating strength.

That is a materially different architecture from "find the strongest finding and latch it." The ratchet
still governs *how confident* to be; the trace governs *what class this is*.

## 4. So what is the narrative form actually worth?

Honestly: **statistically nothing, and operationally a lot.** Three reasons it should still be the
output format, none of which are about accuracy:

1. **The GAP state must be visible so it can be excluded.** `FOLDING_PARTIAL_ATTACHMENT` found the two
   GAP files are a Sony ILCE-7RM2 and a Nikon D3000 — real cameras missing from a one-phone catalogue.
   A report that renders `? gap — OUR reference is missing, contributes nothing` cannot quietly become
   an accusation. A report that renders silence can.
2. **`held` is a finding and deserves to be said.** "Seven checks ran and all seven passed" is what a
   genuine capture earns (0/61 false positives). Reporting it as silence throws away the strongest
   statement the engine can make about an authentic file.
3. **It is a case made to a person.** The slip→route line — *"this arm could not attach because the
   file has no EXIF, so I sent the sensor-noise arm instead"* — is exactly the sentence a claims
   adjuster or a judge can follow. That is the product's actual differentiator, and it was always going
   to be legibility rather than AUC.

## 5. What the report looks like

```
  20260726_145915.jpg
    [held ]  format_is_capture      attached, tested, PASSED
    [held ]  encoder_is_camera      attached, tested, PASSED
    [held ]  device_claim_present   attached, tested, PASSED
    [FIRED]  thumbnail_present      attached, CONTRADICTED
    [FIRED]  byte_order_matches     attached, CONTRADICTED
    [held ]  tagcount_matches       attached, tested, PASSED
    [held ]  geometry_is_capture    attached, tested, PASSED
    ---> this pattern appeared 34 times in the reference set;
         31 of 34 (91%) were 'edit'
```

And where an arm slips:

```
    [slip ]  thumbnail_present      could not attach: no EXIF, nothing to grip
             -> sent instead: pixel: sensor-noise presence  [B]
```

Note the last line of every report is **frequency in a named reference set**, not a confidence score.
"31 of 34 files with this exact pattern were edits" is checkable by the reader. "0.91" is not.

## 6. Honest ledger

**MEASURED**
- 8 distinct traces across 163 files; five of them with n ≥ 8 and purity 62–100%.
- Full trace LOO accuracy **92.0%**, best single arm **64.4%** — the pattern is worth **+27.6 points**.
- Four-state trace vs binary fired/not: **+0.0%**. The extra states are routing bookkeeping, not
  evidence.

**CORRECTED**
- `FOLDING_WINDOW_COVERAGE` §6's "posterior saturates at one arm" was stated too broadly. It saturates
  in the number of *firing* arms; it does not saturate across the *pattern*, which is worth 27.6
  points. The information is in **which**, not **how many**.

**FLAGGED**
- The `X------` trace (79% AI) is the PNG/WEBP container trace and is contaminated by how the AI corpus
  was collected. It reports container, never authorship.

**LIMITS**
- All 163 files, one catalogue (one phone), one editing toolchain. Trace purity would be tested
  properly by a second phone model and a second editor — the same data request as everything else.
- Traces are measured on the **container observer only**. When pixel and semantic arms are expressed in
  the same four states, the trace lengthens and this measurement must be re-run; the +0.0% result is
  specific to a set of arms whose routing is fully determined.

**Code:** `story.py`, `story.json`, `attachment.py`.
