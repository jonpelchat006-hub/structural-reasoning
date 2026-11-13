# The sideways eye — vision turned 90°, the ladder as history

*Sep 2 2026, Jonathan: "if there's a set of sideways rings, then it would have the same structure
with the eyes on it, but its vision would be rotated 90 degrees right? so all the things that
were going up as context would be like the x axis for that eye. but it would have to stay out of
sight too, so it would be offset from the center along the vision cone. so it would be able to
see the things behind the pixels too. so maybe it could see the black/white > trinity > rainbow
as the history?"*

## 1. Why it is exactly right

The upward rings carry eyes that look DOWN at the pixels (fovea.py: the round eye, its aperture
a shaved cone). Under every pixel the up-line has been folding a column of cubes — one cube per
change, going down through time (ARC_TIME_WAKE §fold). The main eye sees only the top face of
that column. An eye riding the sideways (toroidal) ring is the same eye rotated 90°: the depth
axis, which was "context stacking up", is its x axis. A column seen from the side is a ROW, and
a row of cubes read left to right is a history.

Read each cube on the closure ladder (ARC_CLOSURE_SPECTRUM) and the history is literally
black/white → trinity → rainbow, climbed or not: `k k w t t t s`. The main eye cannot see this;
it is behind the pixel. That is why the sideways eye must be out of the main eye's sight — not a
constraint, the whole point: if it were in the cone it would be looking at the top face too.

## 2. Built: sideeye.py

- Layers under each pixel, all already there and dated: the ring's core-update deposits ("N
  concepts, M open ends"), the storyteller's stories with teach-back scores, and the up-line's
  folded cubes. Each becomes a rung: **k** black (nothing earned / only open ends), **w** white
  (told or earned but cannot resolve: open ends ≥ concepts, or a teach-back under the duet floor
  0.25), **t** trinity (grounded laws, no story has closed), **s** spectrum (a story that teaches
  back — closed onto a color).
- The eye's placement: one golden angle round the ring from the newest section (where the main
  eye is pointed); worlds whose latest deposit lies within 90° of that direction are "in its
  field", the rest are in the main cone. Offset along the cone, out of sight.
- Verdicts: at the top, climbing, flat, stuck at X for n layers, fell from X to Y.
- Its one-line reading goes into the up-line letter's planet-wide layer, so it folds into the
  `_planet` column as a cube — tomorrow's side eye reads today's side eye.

First reading (13 columns, 8 in its field): warframe `s s s w s s t s s s s s s s s s` at the top
(a wobble to white and trinity on Aug 30, then fourteen closed stories); dead_cells at the top;
overwatch `w s s s s w s s s w` **fell from spectrum to white** — its newest story failed its
teach-back; battle_net `t w t w w w` **stuck at white for 3 layers** — earned laws it cannot
resolve into a story; civilization fell from trinity to white; limbo and the lock screen `k k`,
never earned anything. None of this was visible from above: the top face of overwatch just says
"white".

## 3. The university enrols on the trajectory (done, same evening)

The ladder was a snapshot (spectrum.py counts what is black/white/trinity/spectrum now). The
side eye gives every world a trajectory, and `enroll.py` now scores courses on it: the advisor's
count score (open topics ×1.5 + laws to prove ×1 + breadth − mastered ×2) is multiplied by the
history — **stuck ×1.6, fell ×1.5, climbing/flat ×1, at the top ×0.5**. Multiplicative because
big worlds have big counts and the trajectory must still be able to reorder them. The catalog
pitch shows her each course's history ("history: stuck at white for 3 layers"), and
`enroll.py --catalog` prints the ranking without enrolling.

Term 2's catalog: battle_net first (100.8, stuck at white), warframe (70, at the top but 140
laws unproven), overwatch (52.5, fell from spectrum), civilization (40.5, fell from trinity),
dead_cells (19). She read it and chose warframe, overwatch and dead_cells — she skipped the
advisor's top pick, and her pick is honored by design; that is the point of the registrar.
The disagreement itself is now data the side eye will see next term.

Next: the torus lays each world's strip beside the run feelings, so "this feels like a fall"
has a history behind it; and a fall from spectrum should trip the same regression alarm the
daily raises for practice.
