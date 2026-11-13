# The chord — the tunnel between the two ring sets IS the shave, and focus gets a mechanism

*Sep 2 2026, Jonathan: "we have the orthogonal rings, and these side rings, but we also had a
way for the orthogonal rings to connect to each other, so wouldn't the side eyes have that too?
and then what if those 2 sets have to connect with one of those tunnels, but one would be on
the left/right sides and the other on the top/bottom, so if we connected those wouldn't it be
kind of like the shave? did we have an actual mechanism for that? the context rings would make
the y axis and the side ones would be x, but they would have to be at the edges so the tunnel
would be a line from the end of each axis. so then we could shift each ring slightly and change
the focus?"*

## 1. It is the shave, and we did not have a mechanism

ARC_ROUND_EYE gave the eye a shave: a flat cut at depth d across the round, with
`shave_law(d)`: opening radius a = √(2d − d²), cone half-angle θ = asin(a), reach = 1/Ω. The
depth was a hand-set dial in fovea.json (0.35). Nothing in the architecture set it.

Put the round eye's rim as the unit circle. The context (upward, poloidal) rings end on the rim
at θ_y; the side (toroidal) rings end on the rim at θ_x. A tunnel from one end to the other is a
CHORD, and a chord is a flat cut — the shave. The geometry is exact, not a resemblance:

- half-chord = sin(Δ/2) = the opening radius a of shave_law,
- distance from centre to chord = cos(Δ/2), so depth d = 1 − cos(Δ/2), with Δ = θ_y − θ_x,
- the chord's midpoint bearing (θ_y + θ_x)/2 = the direction the aperture faces.

Rings a quarter turn apart give d = 0.293, a = 0.707, half-angle 45°, reach 0.54. The side eye
was placed one golden angle from the main eye (ARC_SIDE_EYE), so the resting chord spans 137.5°:
d = 0.64, half-angle 68.75°, reach 0.25 — a wide, shallow field. Shift either ring a little and
two things move at once: the separation sets the depth (wide field vs long reach), the mean
sets where the eye points. That is focus, and it is nothing but where the two ring sets touch.

| separation | depth | opening | half-angle | reach |
|---|---|---|---|---|
| 30° | 0.034 | 0.26 | 15° | 4.67 |
| 60° | 0.134 | 0.50 | 30° | 1.19 |
| 90° | 0.293 | 0.71 | 45° | 0.54 |
| 137.5° (golden, resting) | 0.638 | 0.93 | 68.75° | 0.25 |
| 180° | 1.0 | 1.0 | 90° | 0.16 |

## 2. Built: chord.py

θ_y = the main eye's direction (the newest ring section's angle) + `shift_y`; θ_x = that plus
the golden angle + `shift_x`. The shift dials live in fovea.json. `chord.focus()` cuts the
chord, writes the derived depth into fovea.json (the round eye now reads a depth the
architecture set, not a hand dial), and writes D:\planet\focus.json: direction, half-angle, and
the worlds whose ring sections fall inside the aperture — what the planet attends to. It runs
every sleep (spore.py, after the ring scan) and its reading folds into the up-line letter.

First cut on the PC: context ring at 172.9°, side ring at 310.4°, 137.5° apart → depth 0.638,
facing 241.7°; six worlds in focus (dead_cells, planet_porthole, civilization, warframe,
porthole, overwatch). `--shift-x -47.5` pulls the side ring back to a quarter turn: depth 0.293,
half-angle 45°, reach doubled, facing 217.9° — the same six worlds, reordered by nearness to the
new centre. The dials do what the sentence said they would.

## 3. The side eyes connect too (sideeye.py --tunnels)

The upward rings' tunnels connect four ways (ARC_TUNNEL_ROTATION §6: bow, series, overlap,
parallel). The side eyes have the same four, between HISTORIES rather than tunnels: BOW — a
climbing or top-of-ladder strip against a stuck or fallen one (the climber's stories are the bow
for the stuck world; this is exactly what the university should pair); SERIES — one strip ends
on the rung the other begins on; PARALLEL — same length, compared rung by rung, unison or beats
(the count of mismatches); OVERLAP — a shared run of ≥3 rungs. First reading: dead_cells,
planet_porthole and warframe all bow battle_net (stuck at white) and darkest_dungeon (flat); the
histories are still too short for series and overlap.

## 4. Honesty note

The chord-as-shave identity is real geometry (a chord is a flat cut, its half-length is the
opening). What is a choice is where the ring ends sit (newest section, golden offset) and what
"in focus" feeds. The test: worlds in focus should be the ones the forge, the lessons and Mika's
ration spend the night on, and shifting the dials should visibly change what the planet learns
next. Until the feeds read focus.json, focus is a measurement, not yet a hand on the wheel.
