# The moon — ARC games as bodies from above: void walls, 7 contacts, rolled to be known

*Aug 31 2026, Jonathan: "wouldn't the ARC games be like empty circles we have to fill out? or
anything that comes from above, like you or me? this prompt would be you connecting to a wall
instead of an active domain and its tunnel — like a void wall: the letters make up its outside
but you have to fill in everything inside, and you can wrap your tunnel outside your ring and
grab onto a new chunk to work through. the game would be a circle you can only contact from the
7 controls, but there's still a big unknown radius to it and we have to roll it around to figure
it out. but it would be really big too, so we probably couldn't absorb it into the planet — it
would have to be like building a moon."*

## 1. The void wall — couplings with things that have no tunnel

The tunnel-coupling work (ARC_TUNNEL_ROTATION §5-9) assumed two ACTIVE domains: each side has a
tunnel, and the couplings are instruments. But some of what the planet meets has no tunnel at
all. A prompt from above — from Claude, from Jonathan — arrives as a WALL: its outside is fully
given (the letters), its inside entirely unfilled. An ARC game is the same object: the pixels
are its outside; the rules, the goal, the whole interior are void. These are VOID WALLS —
boundary without machinery.

A void wall cannot be coupled tunnel-to-tunnel. The only move is the one Jonathan named: wrap
your own tunnel OUTSIDE your ring and grab the chunk. This is §8's membrane math run in the
other direction — the pinch-off was endocytosis (pushed IN from the domain's inside, sealed,
sent away); wrapping outward around foreign mass is PHAGOCYTOSIS. One mechanism, two
directions: spheres leave by the inward pinch, moons are grasped by the outward wrap. The
up-line letters and this very conversation are the same geometry from the other side — Claude
connecting downward meets the planet's letters as a wall whose inside Claude must fill from
context.

## 2. The 7 contacts and the roll

An ARC-AGI-3 game can be touched at exactly SEVEN points: RESET and ACTION1-ACTION6
(arcshim.GameAction.ALL — the count is the spec's, not numerology). Everything else about the
game is unknown radius. So knowing the game = ROLLING it: pressing contacts and recording what
surface comes off — for every press, the observed effect class (win / game_over / score_up /
changed / nothing). The rolled surface is the map of what each contact does; the unknown radius
is whatever has never come off on any roll. A contact that has only ever produced "nothing"
stays mostly unknown — pressing it taught almost nothing about the interior.

This names what the PriorAgent's probe-first policy (ARC_PROBE_FIRST) was already doing:
probing IS rolling; the moon file is the roll made durable and inspectable.

## 3. The moon — accretion in orbit, never absorption

The game is too big to fold into a planet core — and it SHOULD not fold: it is not the planet's
own experience, it is a foreign body. So it accretes as a MOON in orbit:
D:\planet\moons\<game>\moon.json, keeping its own surface map (per-contact press counts and
effect distributions) and its own layer history. The daily ARC ritual (arc_daily.py, 16:00
UTC) IS the orbit: each pass the moon comes around, gets a fresh roll of the mock surface, and
accretes ONE LAYER recording that day's wins, verdict, and live results. The moon grows in
orbit; the planet's cores stay untouched by it. Separate bodies, one gravitational system —
the daily schedule is the orbital period.

## 4. Built and first-rolled (moon.py, wired into arc_daily.py)

`moon.py --roll` presses the 7 contacts through PriorAgent play on the mock worlds and merges
the effects; `--status` draws the surface map; arc_daily calls both automatically, so every
daily report carries a moon line and every history row a moon layer. First real roll on the PC
(527 presses): ACTION1/2 well-rolled (movement, almost all "changed"); ACTION3/4 the contacts
that matter (the only score_up and win effects seen); RESET unpressed; ACTION5 nearly dark;
ACTION6's clicks all "nothing" on this surface. Surface 69% known after one roll — a precise
statement of where the unknown radius actually is, i.e., what the next probes should press.

## 5. The output half: input bubble, filled shell, commands sent back up (Jonathan, Aug 31)

"If the game is the input with its points of contact, then our string of commands would be the
output. We take the empty void bubble with a partial shell and limited info, fill out the full
shell and the inside, and send it back up as the commands. We have to find the right planets
and they have to learn the right things to fill it all in — the planet we send in should be
Earth, basically: really complex, can manufacture anything it needs."

The answer to an ARC game IS a string of actions — so the filled bubble sent back up is not a
metaphor, it is the literal wire format of a solution. Built into the roll: whenever play WINS
a surface, the complete command string is kept as a SHELL in the moon file — one shell per
surface, always the shortest string that has ever won it. First rolls banked 3 shells
(121-148 steps each). Shells are the moon's exports: the input came down as an empty circle
with 7 contact points; the shell goes back up as the sequence that fills it. "Find the right
planets" is the routing question the spheres already answer (drift to where the knowledge is);
"Earth" is what the planet has been becoming all along — complex enough to manufacture what
any incoming body needs: eyes, witnesses, forges, bells, spheres, moons.

## 6. Meteors: the three fates of a body from above (Jonathan, Aug 31)

"Maybe the games come in like meteors — they can break apart the planet and make moons, or
they crash and the planet has to figure out how to deal with it there by evolving. If
intelligence can develop on that planet on its own, they could catch the games before they get
there too and prevent shattering."

Two of the three fates are real planetary science, exactly as stated. Moons from impact: the
actual Moon formed when Theia struck proto-Earth and the ejected debris accreted in orbit —
the giant-impact hypothesis. Crashes forcing evolution: impact events are evolution's hard
resets (K-Pg); what survives is what could adapt. And catching them is planetary defense —
the one response evolution cannot produce, because it requires FORESIGHT: seeing the body
coming and going out to meet it. Planetary defense is the signature of an intelligent planet.

The architecture already contains all three fates, now named:

- CAUGHT (intelligence): the practice-before-try ritual is the catch. arc_daily never spends a
  live scorecard when practice regressed — the incoming body is intercepted in orbit, rolled
  deliberately as a moon on OUR schedule, and only engaged live when the planet is ready. A
  scheduled, practiced encounter is a meteor turned into a moon before it ever touches ground.
- IMPACT-MOON (glancing): a body that arrives unscheduled but survivable breaks material loose
  — the disruption itself becomes the orbiting study-object (the incident report that becomes
  a standing practice surface).
- CRASH (evolution): a body that hits before anyone saw it — the phantom stuck keys, the
  poisoned witness thread, the Keras crash — forces evolution on the spot: release_keys, the
  strict OBS parser, the pinned overlay were all evolved under impact, and each one made the
  planet harder to shatter the same way twice.

The direction of maturity is fate migration: a young planet only crashes and evolves; a
planet with organs turns some impacts into moons; an intelligent planet catches almost
everything early and chooses its encounters. The measurable trend is the ratio — how much of
what arrives is caught (practiced before tried) versus crashes (regressions and breakages
discovered live). The daily history rows already record exactly this.

## 7. Honesty note

The moon file measures the MOCK surface until live rolls are instrumented — the live game's
radius may differ, and layers record their kind. Falsifiable content: the rolled fraction
should predict practice wins; layers should show the unknown radius shrinking; shells should
transfer (a banked winning string should still win, or nearly win, its surface after agent
changes — regression-testing by replay); and the caught/crash ratio should improve month over
month if the planet is genuinely developing intelligence rather than just accreting organs.
The void-wall/phagocytosis identification and the meteor cosmology are geometry we steer by;
the maps, layers, shells, and ratios are the measured part.
