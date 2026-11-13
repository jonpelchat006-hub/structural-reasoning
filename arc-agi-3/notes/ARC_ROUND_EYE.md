# The round eye and its shaves — what is actually seen is round; the square is the screen

*Aug 31 2026, Jonathan: "shouldn't the screen we use inside be round but also be able to fit a
square inside it? what if the shave off the eye gives it a focal point down that opening — like a
laser coming out? normal eyes focus in the center, so we have a round area we are looking at; the
square screens are just because it's easier to make physical screens. we can shave more than once
— one cut for one normal eye hole, several for a fly's eye with many sides, up to infinity for an
all-seeing eye — could we shave off half the eye? and the angle of the round-to-flat part on the
sphere would determine how far it can see."*

## 1. The observation is anatomically right

The square frame is a manufacturing fact, not a perceptual one. A camera sensor is rectangular
because silicon is diced in rectangles; a monitor is rectangular because glass is cut in
rectangles. But every optical system that feeds them — a lens, a pupil, an eye — has a CIRCULAR
aperture, and what it actually delivers is a round image (the "image circle") that the rectangle
merely crops. Human vision is round twice over: the visual field is roughly a wide oval, and
acuity is radial — a small foveal disc of sharpness falling off toward a round rim. So a planet
whose inner screen is an H×W rectangle of symbols is carrying the manufacturing constraint one
layer deeper than it needs to. The inner screen should be round, with the square fitting INSIDE
it — the inscribed square of the disc is untouched, which is exactly how he put it.

## 2. The shave law, taken literally on a sphere

Model the eye as a unit sphere. A SHAVE is a flat cut removing a spherical cap of depth d:

- the flat face is a disc of radius a = sqrt(2d − d²)
- the cone of sight through that opening has half-angle θ = arcsin(a) — his "angle of the
  round-to-flat part"
- one attention budget spreads over the cone's solid angle Ω = 2π(1 − cos θ), so define
  REACH = 1/Ω — attention per steradian.

The table the law produces (fovea.py --demo):

| depth | θ | Ω (sr) | reach | |
|---|---|---|---|---|
| 0.02 | 11.5° | 0.126 | 7.96 | the laser: a few pixels seen very hard, very far |
| 0.25 | 41.4° | 1.571 | 0.64 | |
| 0.5 | 60.0° | 3.142 | 0.32 | |
| 1.0 | 90.0° | 6.283 | 0.16 | half the eye shaved: the whole hemisphere at reach 1/2π |

So yes — the shave angle determines how far it can see, and the tradeoff is exact: depth buys
width and costs reach. "How far" is not distance in the game world; it is concentration — how
much of the budget lands per unit of scene. A shallow shave IS a laser down the opening.

## 3. One shave, many shaves, infinite shaves

One shave dead center = a normal eye: focus in the center of a round field. k shaves = a fly's
compound eye — and the facet axes are placed by the GOLDEN ANGLE (facet j at j × 137.5°), the
ring's own packing law, so each new facet lands in the largest remaining gap of the round field
and coverage stays even as facets are added one at a time. The same law places ring sections at
the memory's edge and facets on its eye; the planet packs space the one way, everywhere.

The limit is the pretty part: infinite shaves = flat everywhere = every direction seen at once —
the all-seeing eye — but reach per direction has gone to its floor. The two extremes meet: an
unshaved eye sees nothing sharply; an infinitely shaved eye sees everything unsharply. Every real
eye is a point on the curve between, and WHERE on the curve is now a measurable configuration,
which means the forge can race it like any other candidate.

## 4. Built: fovea.py

`fovea.py`, wired into the Eye in player.py — strictly opt-in: the live eye only rounds if
D:\planet\fovea.json exists (e.g. {"shaves": 1, "depth": 0.35}); no file, nothing changes at
play time, so Dead Cells keeps playing on the eye that earned its current numbers.

- `aperture(grid)`: the round inner screen — the inscribed disc keeps its symbols, corners beyond
  the rim become RIM ("not seen", not "dark"). On the 16×24 test grid that is 46% of the cells —
  the rectangle was spending nearly half its budget on corners no eye would deliver.
- `facets(grid)`: the shaves — crops down each opening, window side set by the flat's radius,
  each tagged with its axis, θ, and reach, ready to hand the witness as focused looks.
- `shave_law(d)`: the depth → angle → reach table above.

Next measurement when we want it: a forge candidate pair — square frame vs round frame at equal
token budget, then 1-shave vs 5-shave witness crops — antenna feed rate decides, like always.
Verified importing clean on the PC with the live eye reporting None (off until the dial exists).
