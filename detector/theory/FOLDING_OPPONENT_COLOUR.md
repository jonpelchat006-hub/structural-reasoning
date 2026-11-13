# Opponent Colour — the corpus already contained the correction, and it worked

*Jonathan asked whether the framework's own colour work fills the gap. **Part of it does, and it is
not the part you would expect.** The semantic mapping (RED = Existence, BLUE = Temporal) is a
retrieval key — validated at 5.2× over chance on ARC task similarity — and has nothing to say about
why a phone's blue channel lacks radial structure. But `FOLDING_TUNING_SHELLS` recorded an honest seam
years of work ago: **"colour is made by comparing several differently-tuned cones — opponent processing
— not by one core reading a residual spectrum."** That was exactly my bug. Rebuilding on opponent axes
**improved the measure: `RG_opp` 0.302 against controls of 0.048 / 0.193 / 0.115, better than R/G's
0.283, with its content control more than halved.** And the pre-registered wavelength test came back
**+0.79** — partially confirming optics. But **blue is genuinely silent on every formulation**, so my
"wrong axis" hypothesis is refuted. Tally: 42 tested, 2 passed.*

---

## Part I — Which part of the framework applies, and which does not

`wave_frequency.py` carries a real `LIGHT_SPECTRUM` with physical wavelengths — 700, 600, 580, 550,
500, 450, 400 nm — mapped onto semantic specialties (Existence, Quantity, Motion, Structure, Relation,
Temporal, Consciousness) and onto musical modes and magnetic classes. `color_trails.py` builds a 7D
semantic position space on top of it.

**That mapping is a retrieval key, and it is a measured one** — `RESULTS.md` records 18.9%
nearest-signature family agreement against a 3.6% baseline, a **5.2× lift**, on ARC task similarity.
It works for what it was built for.

**It does not apply here.** The question "why does R/G show radial structure and B/G not" is about
sensor optics and image processing pipelines. Answering it with a semantic colour mapping because the
mapping is ours would be motivated reasoning — the precise failure mode that produced 40 dead features
and one retracted maker-note claim in this project.

**What does apply is the structural correction the corpus already recorded**, in
`FOLDING_TUNING_SHELLS`, under *Honest seams*:

> "Readout is multi-channel comparison, not one filtered remainder. Color is made by comparing several
> differently-tuned cones (opponent processing), not by one core reading a residual spectrum. His model
> is a single subtractive channel; real color vision is parallel comparison."

**That is my bug, written down before I made it.** `shading_observer` measured R/G and B/G — both
against green, one reference, a single subtractive channel. Colour is read by *opposition*: red against
green, and blue against **yellow** (R+G), not blue against green.

And the framework's own wavelength table makes that a quantitative prediction. Lens shading varies with
wavelength, so a channel pair should carry signal in proportion to how far apart its wavelengths sit:

| pair | separation |
|---|---|
| R/B | **250 nm** |
| R/G, RG_opp | 150 nm |
| B/Y, BY_opp | 140 nm |
| B/G | **100 nm** — the one that was silent |

## Part II — The result

All six pairs through the same real-vs-real gate. |AUC−0.5|:

| pair | sep | TARGET | CTRL1 content | CTRL2 device | CTRL3 | verdict |
|---|---|---|---|---|---|---|
| **`RG_opp`** (R−G)/(R+G) | 150 | **0.302** | **0.048** | 0.193 | 0.115 | **CLEARS** |
| **`R/G`** | 150 | 0.283 | 0.107 | 0.227 | 0.146 | **CLEARS** |
| `R/B` | 250 | 0.193 | 0.119 | 0.223 | 0.062 | confounded |
| `BY_opp` | 140 | 0.080 | 0.163 | **0.265** | 0.062 | confounded |
| `B/Y` | 140 | 0.067 | 0.052 | 0.178 | 0.031 | confounded |
| `B/G` | 100 | 0.027 | 0.087 | 0.159 | 0.021 | confounded |

**The opponent formulation is a genuine improvement.** `RG_opp` beats `R/G` on the target (0.302 vs
0.283) and **more than halves its content control** (0.048 vs 0.107). That is the framework's own
recorded correction, applied, producing a better measure. It is the first time in this session that
something from the theory corpus has improved a measurement rather than being refuted by one.

### The pre-registered wavelength test: partially confirmed

**Spearman(separation, |AUC−0.5|) = +0.79.** Wider wavelength separation does predict more signal,
which is what optics requires.

**But the prediction is not fully met.** Under a pure optics model **R/B at 250 nm should be the
strongest pair**, and it is not — 0.193, well below the two 150 nm red-green measures. The +0.79 is
carried mostly by B/G being weakest rather than by R/B being strongest. **Consistent with optics, not
demonstrating it.**

### And my hypothesis about blue is refuted

I proposed that blue looked silent because I had used the wrong opponent axis. **Both blue-yellow
formulations are also dead** — `B/Y` 0.067, `BY_opp` 0.080, and `BY_opp`'s device control (0.265) sits
*above* its target. **Blue is genuinely silent, on every formulation tested.** Not an axis artifact.

Three candidate reasons, none tested: phone pipelines correct blue shading hardest because it is the
noisiest channel; blue has the lowest SNR so any residual is buried; or the effect is not optics and
R/G is reading something else.

## Part III — The caution that has to travel with this

`RG_opp` = (R−G)/(R+G) **is essentially a redness measure.** The AI class in the target arm is 12/17
studio beauty close-ups — skin. The real class is skies and walls. **A redness measure separating skin
from sky is exactly the kind of content effect that killed 40 features here.**

The controls argue against it: CTRL1 (web portrait vs web landscape, both real, both containing skin)
comes back at **0.048**, near zero, which is the strongest single piece of evidence that this is not
just "faces are red". CTRL3 (his close-ups vs his scenes, one phone) is 0.115.

But **CTRL2, the device arm, is 0.193** against a target of 0.302 — a margin of 0.109. Better than
`R/G`'s 0.056, and still not comfortable.

**Verdict: two of six clear, the opponent version is the better one, and it needs a bigger and
content-matched target set before it is a claim rather than a lead.**

---

## Honest ledger

**MEASURED**
- `RG_opp` clears all three controls: **0.302 vs 0.048 / 0.193 / 0.115.** Best free feature recorded.
- `R/G` also clears, at 0.283 vs 0.107 / 0.227 / 0.146.
- **Spearman(wavelength separation, signal) = +0.79** — pre-registered, partially confirmed.
- **R/B, the widest pair, is NOT the strongest** — the pure optics prediction fails.
- **Blue is silent on B/G, B/Y and BY_opp alike.** The wrong-axis hypothesis is refuted.

**WHAT THE FRAMEWORK CONTRIBUTED**
- Not the semantic colour mapping — that is a validated *retrieval* key (5.2× on ARC) and is the wrong
  instrument for a physics question.
- **The opponent-processing correction in `FOLDING_TUNING_SHELLS`**, which was written down as an
  honest seam and turned out to name the bug exactly. Applying it improved the measure and halved a
  control.
- The `LIGHT_SPECTRUM` wavelengths, which turned "why is blue silent" into a **falsifiable prediction**
  rather than a shrug. It came back partially confirmed, and the part that failed is informative.

**RUNNING TALLY**
- Model-free features tested against real-vs-real controls: **42. Passed: 2** (`R/G`, `RG_opp`).

**NEXT**
1. **A content-matched target set.** Both survivors have a redness story that the current AI class
   cannot exclude. This is the same requirement `FOLDING_PHOTO_SET_AUTOPSY` Part VI set out and it is
   still the binding constraint on every free-feature claim.
2. **Per-lens shading fits.** Three sensors are now enrolled with different optics — if `RG_opp` is
   optics, the ultrawide and periscope should shade *differently*, and that is a within-device test
   with no content confound at all. **Cheapest decisive experiment available.**
3. Only then decide whether the free tier has a signal worth shipping.

*Artifacts: `shading_observer.py`, `shading_results.json`. Sources: internal —
`FOLDING_TUNING_SHELLS` (the opponent correction, and where it came from), `FOLDING_SHADING`,
`FOLDING_PHOTO_SET_AUTOPSY` (the gate), `RESULTS.md` (the 5.2× ARC retrieval validation). Device:
`Shovelcat-AI/wave_frequency.py` (LIGHT_SPECTRUM), `Shovelcat-AI/color_trails (1).py`.*
