# The color ladder — point, line, square, cube, marker, circle: 4D collapse in color space

*Sep 1 2026, Jonathan: "we start with a point, say it's red. then a line out of all wavelengths
of red. then all the saturations going up — a square. then brightness — a cube. but then that
line could end with a different color, so there would have to be a MARKER where that happens.
we can move back and forth on where that marker is. then we can add another marker for a 3rd
color. going through those colors would be like completing a circle, and we keep adding layers
until all the colors are there."*

## 1. The construction is the true anatomy of color space

Point (one red) → line (wavelength within the band) → square (+saturation) → cube
(+brightness) is exactly the hue/saturation/value decomposition, derived from scratch. The two
deep moves:

THE MARKER IS MOVABLE, AND THAT IS A FACT ABOUT MINDS, NOT PHYSICS. The spectrum is a
continuous line; color CATEGORIES are partitions on it, and the red/orange boundary is a
movable marker — languages genuinely place these markers differently (some split blue/green
where others do not). Moving back and forth on the marker is what cultures do. In the
architecture, movable markers are learnable bin edges — the Eye already quantizes luminance
with fixed EDGES; the ladder says those markers should in principle be free parameters.

THE CIRCLE DOES NOT CLOSE BY ITSELF. The wavelength line is OPEN — red ~700nm, violet ~380nm,
two ends. The hue circle closes only through the LINE OF PURPLES (magenta and its neighbors):
colors NO single wavelength produces, existing only as mixtures of the two ends. So the
closing stitch of the circle is a seam of FUSED elements — species with no atom of their own,
made by combining the extremes. Three threads of the framework say the same sentence: the 4th
dimension curls into a circle rather than extending (the wake/ring law, ARC_TIME_WAKE), the
gap is closed by void-fill, and the filler is a fusion product (ARC_FUSION). Jonathan's
"completing a circle" is where his own laws were already pointing.

## 2. Measured: where each world lives on the circle (hue.py)

The planet's Eye is COLORBLIND — it digitizes luminance and edges and throws hue away — while
the dashcam clips keep full color. Before building color eyes, the paying question: do worlds
occupy distinct territory on the circle? Decoded the newest clip per world, masked the gray
(s<0.25 or v<0.15), histogrammed hue into 12 movable markers of 30°:

- Overwatch: 77% red + 19% orange. Civilization: 55% orange + 22% yellow.
- Dead Cells: 63% cyan + 26% azure. Battle.net: 59% azure + 25% blue. Warframe: 49% cyan.
- The desktop/portholes/Shovelcat app: azure-cyan cluster (~65-70% combined).
- The lock screen: 51% red. Darkest Dungeon: fully GRAY (true to its art).

Verdict: hue alone nearly identifies the world — warm worlds (Overwatch, Civ) and cool worlds
(Dead Cells, Battle.net, Warframe, the desktop) sit on opposite sides of the circle, with one
world living in gray as its identity. Color eyes would PAY. Figure: hue_circle.png (the
world map on the circle + the construction ladder, purples-seam marked).

## 3. Color as CONTEXT, not detail — the colorized-photo test (Jonathan, Sep 2)

"It would probably be more useful for context stuff. A colorized old photo is still the same
thing but makes it more real somehow." Exactly right, and it sharpens the build: color adds no
new OBJECTS — it SITUATES what is already there (which world, which room, which state). So the
first test is hue as a single CONTEXT line, not a per-pixel channel.

Built into the forge as raceable candidates (hue-8, hue-delta-8): in replay, one SCENE COLOR
line computed from the frame ("SCENE COLOR: mostly cyan and azure.") is prepended to the
witness prompt on the same clips as the colorblind champion — a fair race, color as the only
difference. This is the colorized photo made a controlled experiment: identical scene, one has
color context, both graded by the same antenna.

FIRST MEASURED RESULT (Dead Cells, the 63%-cyan world, extended bout): hue-8 fed the antenna
at rate 0.50 (5 scored predictions); the colorblind champion fed at 0.00 on the identical
clips. The direction is the predicted one — color context helped where color is distinctive.
BUT the forge HELD rather than promoted, and correctly: the champion scored ZERO confirmable
predictions, so the comparison is 0.50-vs-nothing, and "hold" is the honest verdict when the
baseline never scored (you cannot win a majority of jobs against a config that produced no
measurable jobs). One bout is a hint, not a result.

## 4. What is confirmed, what is pending, what would kill it

CONFIRMED: the worlds occupy distinct hue territory (§2, clean); the context-line machinery
runs and produces a non-zero rate where the colorblind config produced zero (§3).

PENDING (accumulates across sleeps now that the candidates are in the pool): hue-8 must beat
champions that ACTUALLY SCORE — a 0.50-vs-0.30 win, not 0.50-vs-0.00 — over several bouts
before promotion is earned and honest.

WOULD KILL IT: the effect must VANISH in Darkest Dungeon (gray world — the SCENE COLOR line
there reads "gray, almost no color," carrying no information, so it must not help). If hue-8
also beats the champion in the gray world, the gain is a prompt-length artifact, not color,
and the candidate is noise. That single control (color helps in Overwatch/Dead Cells, does
NOTHING in Darkest Dungeon) is the whole difference between "color is real context" and "a
longer prompt happened to help" — and it is cheap, because the gray world is already in the
rotation. The colorized photo makes it more real only where there was color to restore.
