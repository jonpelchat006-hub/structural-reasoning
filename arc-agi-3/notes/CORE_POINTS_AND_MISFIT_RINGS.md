# The inner core sits where the rings connect (Oct 20, 2026)

Jonathan, Oct 20:
- *"we still need the inner core though. i did have an idea for the story that it was the ring in the zeta function. it was kind of right. the earlier agi work also had it too. it was a structure that led to everything else."*
- *"but if its a structure then individual points wouldnt support anything. and there were rings that didnt fit into the earlier tests. maybe those are where the points connect?"*

Companions:
- `FOLDING_CRITICAL_LINE.md` Part II §4 (the ring chain), §6 (atoms do nothing), Part V (Ihara outliers), Part XXVI (Ford rings), Part XXXVI (the three shells);
- `LEAN_POLYDISC_PACKED.md` (the D5 theorem).

## 1. Points don't hold a structure up

**Already measured** (Part II §6): you can remove any finite number of terms from 1 + 1/2 + 1/3 + … and the sum is still infinite. Its weight sits in the pattern, not in any one term.

**The same law in the Lean work:**
- No number of passing cases proves `impl_correct`; one proof for every `n` covers them all.
- In polydisc D5, checking each step needs the full bits. One theorem (exact subresultant division) would cover every step at once.

## 2. Points can generate a structure

- In the ring geometry, the inner core is two points with rotations: a half turn at `i` and a third of a turn at `ρ = e^{iπ/3}` (Part XXXVI).
- Theorem: the modular group is the free product `Z/2 * Z/3`. Those two rotations, with no other rules, generate every tile, ring and wire used in Parts XXVI–XLIII.
- A point can't hold the structure up by sitting in it, but a turning point builds all of it.

## 3. The core points sit exactly where the rings connect (checked Oct 20, `ford_core.py`)

Tested on 979 pairs of touching Ford rings (denominators ≤ 40):

| Core point | Where it sits | Check |
|---|---|---|
| Half-turn point (images of `i`) | exactly on the touch point of each pair of touching rings | error 2×10⁻¹⁶; fixed by its half turn to 2×10⁻¹³ |
| Third-turn point (images of `ρ`) | in the middle of each gap between three mutually touching rings | equal distance to all three to 2×10⁻¹²; fixed by its third turn to 4×10⁻¹³ |

- The third-turn point is always `ln(2/√3) = 0.143841` outside each of its three rings.
- Neither core point lies inside any ring.
- So the core is not one of the rings. It is the set of connections between them: every touch and every gap.

## 4. Rings that don't fit

### The zeta ring chain (`gram_rings.py`)

`ζ(½+it)` loops through 0 once per zero. Gram points cut the line into rings, and Gram's law says each ring holds exactly one zero.

Measured on rings 0–1500 (1,502 zeros, mpmath, 15 minutes):

| What | Result |
|---|---|
| Rings that fit (exactly one zero) | 1,345 |
| Misfit rings | 156: 78 empty, 78 holding two zeros |
| Each empty ring sits right next to a two-zero ring | 78/78 |
| Each misfit pair holds the right total of 2 zeros (Rosser's rule) | 78/78 |
| In each pair, the empty ring is the bigger one (largest \|Z\|) | 78/78 |

- The first misfit is at ring 126.
- The empty ring swings wide, misses the centre, and its zero sits in the smaller neighbour instead.
- So **a misfit is exactly where a zero crosses from one ring into the next**, and the pair's total never changes. Single rings flex; the count across the border is conserved.
- Rosser's rule is known to fail eventually, but only millions of rings beyond this range. All misfit blocks here have length 2.

### Misfits from earlier tests

- **Ihara outliers (Part V).** The protein graphs had eigenvalues that fell off their critical circle. Those outliers are the domain structure: the seams where the two halves of the protein connect.
- **Calmodulin.** It is the odd one out in every folding test. Its two halves join at a single exposed hinge instead of a woven seam.

All three kinds of misfit are places where parts connect:
- a zero passing into the next ring;
- a seam between domains;
- a hinge.

## 5. Three points, twelve slots, and the lines that are always there (Oct 20, morning, `twelve.py`)

Jonathan: *"there was also that set of lines around the critical point that were always there too. wouldnt the inner core have to connect to those too? and theres 3 points to it? but then there was a depth too and each end there counted as another point, so there should be 6? but those were inverses. is there 12 parts that make it up? or slots … different rules could slide into them … each point on those lines are the rules we fill them with?"*

**Three points.** The base tile (the modular surface) has exactly three special points:
- the half-turn point `i`;
- the third-turn point `ρ`;
- the cusp, where the rings meet the wall.

**Depth: the inverse layer.** Every matrix `M` has a twin `−M` that moves every point the same way. Counting that layer:
- the half turn takes 4 steps to come home: `S² = −1`, `S⁴ = 1`;
- the third turn takes 6: `U³ = −1`, `U⁶ = 1`.

**Twelve slots** (read off the phase of η² under each matrix):

| Check | Result |
|---|---|
| Every matrix falls into exactly one of 12 slots | yes |
| Combining matrices adds their slots mod 12 | 300/300 random pairs; all 12 slots used |
| Slots of the generators | half turn 9, third turn 2, shift 1, the sign twin 6 |

- Dropping the sign layer leaves 6 slots. So the count goes 3 points → 6 → 12, as Jonathan guessed. (This is the abelianization `Z/12` of SL(2,ℤ).)
- The η here is the same one whose phase gave the linking ledger in Part XXVII.

**Rules slide into the slots: the forms fill twelfths.** A weight-`k` form has `k/12` zeros in total; a zero counts 1/2 at the half-turn point and 1/3 at the third-turn point. The three basic forms each put their single zero on one of the three points (checked to 30 digits):

| Form | Its zero | Share |
|---|---|---|
| E4 | the third-turn point | 4/12 = 1/3 |
| E6 | the half-turn point | 6/12 = 1/2 |
| Δ | the cusp | 12/12 = 1 |

**One whole slot, slid by a rule `λ`.** At weight 12, `E4³ − λΔ` vanishes at exactly one point of the tile, where `j = λ`:
- Every rule fills exactly one point, and every point is one rule. The tile is the catalogue of all torus shapes.
- At `λ = 0` the zero lands on the third-turn point and splits into three thirds.
- At `λ = 1728 = 12³` it lands on the half-turn point as two halves.
- As `λ → ∞` it runs out to the cusp.

**The lines that are always there.** Real rules slide along three fixed lines, which join the three points into a triangle (checked):

| Real rules | Where the zero lands |
|---|---|
| negative | on the wall `Re z = −½`, between the cusp and the third-turn point |
| 0 to 1728 | on the arc `\|z\| = 1`, between the third-turn and half-turn points |
| above 1728 | on the centre line `Re z = 0`, between the half-turn point and the cusp |

- The whole line of real rules folds into the triangle whose corners are the three core points. Complex rules fill its inside.
- So the core connects to the always-there lines at their corners.

**Zeta parallel (an analogy, not an identity).** The lines where ζ is real are the threads that cross the critical line at the Gram points (the slots of §4 and Part XX). The truths sit between them. The pattern is the same: the always-real lines make the slot frame, and the values fill it.

**Honest note.** Everything here is a standard fact about the modular surface, checked numerically.

## 6. Sliding the core: distance, orientation, filling and room (Oct 20, `slide.py`, `fill2.py`)

Jonathan: *"wouldnt we be sliding our inner core along those lines and each thing is some distance along them in some orientation? and if we are sliding along them then would the lines fill it in as it slides and have to expand as it takes more in?"*

**Distance and orientation.** Step a small distance away from a core point and see how the rule changes:
- At the half-turn point the change goes as (step)², so it depends only on twice the angle: directions 180° apart give the same rule.
- At the third-turn point it goes as (step)³: directions 120° apart give the same rule.
- The ratio is constant across directions to about 1 part in 10⁴, the size of the step.
- So a thing's address is (how far, which way), and the core fixes how many directions are really different: 2 at the half-turn point, 3 at the third-turn point.
- Around the cusp the address is the `q` coordinate: `|q|` is the height and `arg q` is the angle.

**The lines fill in as more is taken in.** All the zeros of the Eisenstein series `E_k` lie on the arc `|z| = 1` (Rankin–Swinnerton-Dyer, 1970). Checked with a converged series:

| k | Zeros on the arc | Valence total | Spacing | 2π/k |
|---|---|---|---|---|
| 12 | 1 | 1 | — | — |
| 24 | 2 | 2 | 0.2586 | 0.2618 |
| 48 | 4 | 4 | 0.1295–0.1309 | 0.1309 |
| 96 | 8 | 8 | 0.0648–0.0655 | 0.0654 |
| 144 | 12 | 12 | 0.0432–0.0436 | 0.0436 |
| 240 | 20 | 20 | 0.0259–0.0262 | 0.0262 |

- Every zero is on the line, with none elsewhere, and they are evenly spaced.
- The arc keeps its length and gets denser: one new point per 12 weight.
- The independent rules per weight are also `⌊k/12⌋ + 1`, or one fewer when `k ≡ 2 mod 12`. For example: 12 → 2, 24 → 3, 60 → 6.
- (An earlier run that cut the series at 40 terms miscounted at k = 144 and 240. The terms `n^{k−1} qⁿ` peak near `n ≈ k/5.4`, so large `k` needs more terms.)

**Room expands exponentially with distance.** Counted copies of the tile whose copy of the half-turn point lies within distance `r` of it:

| r | Tiles | Area rule 6(cosh r − 1) | Ratio |
|---|---|---|---|
| 4 | 162 | 158 | 1.03 |
| 6 | 1,242 | 1,204 | 1.03 |
| 8 | 8,874 | 8,937 | 0.99 |
| 10 | 65,802 | 66,073 | 1.00 |

- The count grows about e² ≈ 7.4× per 2 units of distance.

**Reading.**
- Capacity (slots) grows in a straight line, one per 12. Room grows exponentially with distance.
- So the structure never has to stretch to take more in: the space it slides through already widens far faster than the slots fill. The price of more room is distance, the same `e^r` that priced wall maintenance in `FOLDING_CRITICAL_LINE.md` Part XLVIII.3.
- Polydisc v8 did the costly version of this: it widened its lanes as the numbers grew, because in the kernel width is never free.

## 7. The lines are double-sided, and their sides peel off and curl into the slots (Oct 20, `peel.py`)

Jonathan: *"the lines also wrap around the points dont they? so its like some parts go into the slot and some goes around to make the structure and connect the points? its like if the line was double sided and one side peels off into the slots and curls up into it"*

**Double-sided, checked exactly.** Reflecting across any of the three always-real lines turns every rule into its mirror, the complex conjugate. Error: 0 across the centre line, 2×10⁻²⁷ across the arc, 3×10⁻²⁸ across the wall. Each line's two sides are mirror images.

**The sides take turns around each core point.**

| Core point | Real lines through it | Real rays | Sides of the slots between rays |
|---|---|---|---|
| Half-turn point | 2 (the arc and the centre line) | 4 | + − + − |
| Third-turn point | 3, at 60° | 6 | + − + − + − |

- Each side of the line fills every other slot: 2 of 4 at the half-turn point and 3 of 6 at the third-turn point.
- The other side fills the mirror slots. These are the "inverses" of §5: 6 = 3 + 3 mirrored.

**Off the line, it curls.** A line slightly off the real line (`Im j = ε`, a non-real rule) never reaches the core point. It splits into curls, each hugging two neighbouring rays and turning around the point inside one slot.

| Core point | Closest approach shrinks per 10× in ε | Theory |
|---|---|---|
| Half-turn point | 10^0.498, then 10^0.493 | 10^0.5 |
| Third-turn point | 10^0.327, then 10^0.319 | 10^0.333 |

- The theory is `ε^{1/m}` with m = 2 and 3. The drift at the largest ε is the next-order terms.

**Reading.**
- The real line itself passes through the core points and joins them: the structure (the triangle of §5).
- Anything slightly off it peels away and curls around the point inside a slot. The closer to the line, the tighter it curls.
- Both sides peel, each into alternate slots. So it is not one side into the slots and the other around: both sides curl, mirror images of each other, taking turns.

## 8. The void lines around each point, and the helix strands into the core (Oct 20, `helix.py`)

Jonathan: *"around the point would be other number lines with their positive and negative sides right? so there would be the 0s as our void lines? in the middle shell from the earlier work we had the real parts going around the void lines like a dna helix, so would it be those parts going into the core?"*

Around a point `p` with rule value `j0`, look at `j − j0` on a small circle:

| Point | Phase winds | 0-rays of the imaginary part | 0-rays of the real part | All void rays | Rays carrying one phase into the point |
|---|---|---|---|---|---|
| Half-turn point | 2.0 | 4 | 4 | 8, at 45° | 2, 180° apart |
| Third-turn point | 3.0 | 6 | 6 | **12**, at 30° | 3, 120° apart |
| Ordinary point | 1.0 | 2 | 2 | 4, a plain cross | 1 |

**Void lines.**
- Both parts have their own 0-lines, and they interleave.
- The core point is the only place where every void line meets, the one spot where both parts are 0 at once.
- At the third-turn point there are 12 void rays: twelve again.

**Number lines.**
- At the third-turn point (`j ≈ c·w³`), opposite rays carry opposite signs. So three full number lines cross there, each with a + end, a − end and 0 at the core.
- At the half-turn point (`j − 1728 ≈ c·w²`), opposite rays carry the same sign. Each line is folded in half at the core; that fold is the half turn itself. Along the arc both ends read below 1728, and along the centre line both ends read above it.

**The helix.**
- Lift the phase as height. Each phase value enters the point along `m` rays, and the rays rotate together as the phase climbs.
- That makes an `m`-strand helix with the core point as its axis: a double helix at the half-turn point, a triple helix at the third-turn point, and a single strand everywhere else.
- The single-strand case is the winding-1 vortex measured at every zeta zero (`FOLDING_CRITICAL_LINE.md` Part XXII).
- So the strands winding around the void line are the phase lines, and they run straight into the core point. The core points are exactly where the helix has more than one strand.

## 9. Three levels, the strand mix, fusion into the cores, and the three-triangle shape (Oct 20, `fuse.py`)

Jonathan: *"so then theres 3 types of the lines and cores or like different levels to them? isnt that like the real and 2 orthogonal planes … part of what makes something up would be how much of each kind of strand they used. or when something reaches the right conditions it upgrades to the other strands like in the fusion stuff? the theta/phi/psi domains too. and the strands come in from the middle shell then wrap around up to 3 cores? and they were triangles, so its kind of like a triforce shape when all 3 are being wrapped?"*

**Three levels, with a ceiling.**
- A point is single-strand (ordinary), double-strand (half-turn point) or triple-strand (third-turn point).
- No rotation of order above 3 exists in this group (census in Part XXXVI), so 3 strands and 12 void rays are the maximum anywhere.

**The strand mix.** Every function's total `k/12` splits into third-turn strands (1/3 each), half-turn strands (1/2 each) and free ordinary zeros (1 each). The weight `k mod 12` forces the core mix, and each extra 12 adds one free zero:

| Weight | Third-turn | Half-turn | Free |
|---|---|---|---|
| 4 | 1 | 0 | 0 |
| 6 | 0 | 1 | 0 |
| 8 | 2 | 0 | 0 |
| 10 | 1 | 1 | 0 |
| 12 | 0 | 0 | 1 |
| 14 | 2 | 1 | 0 |
| 16 | 1 | 0 | 1 |
| 22 | 1 | 1 | 1 |
| 24 | 0 | 0 | 2 |

**Upgrading is fusion (measured).** Zeros of `E4³ − λΔ` as `λ` approaches a core's value:

| As λ approaches | Copies that converge | Directions | Distance per 10× closer |
|---|---|---|---|
| 0 (the third-turn point) | 3 | 30°, 150°, 270° | ÷2.16 (cube root: 2.154) |
| 1728 (the half-turn point) | 2 | 180°, 360° | ÷3.16 (square root: 3.162) |

- Measured distances: 0.0613 → 0.0282 → 0.0130 → 0.0060 at the third-turn point; 0.0642 → 0.0201 → 0.00635 → 0.00201 → 0.000635 at the half-turn point.
- The converging copies are the same point of the tile seen from the neighbouring tiles. At the exact value they fuse into one triple or double strand.
- The ceiling of 3 plays the role of the iron line in `ARC_FUSION.md`.

**Count matches with Jonathan's papers** (correspondences of numbers, not derivations):
- Theory 10_1: the ψ-domain runs on two helical layers and φ on one, the double and single strands. That would leave θ for the triple, if he labels it that way.
- Theory 14's polygon ladder runs square → octagon → dodecagon, with the dodecagon (12) as the ceiling. Here the void-ray counts are 4 at an ordinary point, 8 at the half-turn point and 12 at the third-turn point, and 12 is the ceiling for the reason above.

**The three-triangle shape, checked exactly.** Take the three rings at 0, 1 and ∞ around one gap:
- They touch pairwise at three half-turn points, `i`, `1+i` and `(1+i)/2`.
- Those three points form an equilateral triangle, each side 0.962424 (hyperbolic): the empty middle of the shape.
- The third-turn point sits at its exact centre, 0.549306 = arccosh(2/√3) from each corner.
- The outer corners are the three cusps, where the rings meet the wall.
- So with all three wrapped, there are three double-strand points at the corners of the hole and one triple-strand point at its centre.

## 10. Reading the empty triangle: spray from inside, flows through (Oct 20, `spray.py`)

Jonathan: *"in the empty triangle would that be where the actual identity is stored? the strands going in wouldnt be perfectly contained in the triangles, and our framework did have jets and sprays, so would we spray into the empty part and thats how we read it? thats kind of like the agi stuff where we were making a circuit with the pins, but where the flows would come from"*

**Sealed.** The three rings touch pairwise, so the empty triangle is closed off except at three single points. Every ray sprayed from inside hits one of the three rings: total share 1.000.

**Spray from inside reads position.** Rays were sprayed in all directions (3,600 from the centre, 1,800 from each other point), and each ray's first ring was recorded:

| Point | Ring 0 | Ring 1 | Ring ∞ |
|---|---|---|---|
| Centre (third-turn point) | 0.3333 | 0.3333 | 0.3333 |
| (0.5, 0.60), low | 0.442 | 0.442 | 0.116 |
| (0.5, 0.75) | 0.374 | 0.374 | 0.251 |
| (0.5, 0.95), high | 0.301 | 0.301 | 0.399 |
| (0.4, 0.90) | 0.378 | 0.266 | 0.356 |
| (0.6, 0.90), mirror of the previous point | 0.266 | 0.378 | 0.356 |
| (0.45, 0.98) | 0.304 | 0.259 | 0.437 |

- Every point splits its spray differently, and moving toward a ring raises that ring's share. So the three shares work like coordinates.
- The centre is the even split. This matches SHOVELCAT_THEORY's observer at the centre, who is "not in any circle" and "sees all three".

**Flows through the triangles read identity.** A flow (a geodesic) crossing the triangles goes in through one side and out the left or the right. Each triangle is a switch, and the string of turns is the flow's continued fraction, its address on the wall (Series 1985; Part XXXII):

| Flow | Turns | Run lengths | Continued fraction of the far foot |
|---|---|---|---|
| Golden gear | RLRLRLRL… | 1, 1, 1, … | [1; 1, 1, 1, …] |
| Silver gear | RRLLRRLL… | 2, 2, 2, … | [2; 2, 2, …] |
| π flow | RRR LLLLLLL RRRR… | 3, 7, … | [3; 7, 15, 1, 292, …] |
| e flow | RRLRRLRLLLLRLR | 2, 1, 2, 1, 1, 4, 1, 1 | [2; 1, 2, 1, 1, 4, 1, 1] |

(The π run of 15 is cut short by the 14-triangle depth.)

**Reading.**
- No single triangle holds an identity. Each holds one turn of every flow that passes through it.
- A flow's identity is the string of switches it went through, from one foot on the wall to the other: Part XXXV's refill and spend feet.
- Spraying from inside reads where you are in a triangle; passing through reads who you are along the chain.
