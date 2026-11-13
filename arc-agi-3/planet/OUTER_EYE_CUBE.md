# Fixed eyes, axis-endpoint tunnels, and derived shaves

2026-09-08: standalone geometry prototype in `outer_eye_cube.py`. This is not
part of either PriorAgent notebook, and no leaderboard improvement is claimed.

## Revision: restore the existing tunnel mechanism

The first prototype directly aimed arbitrary cones. That missed the earlier
`chord.py` mechanism. `tunnel_geometry.py` now provides a pure, full-precision
implementation of the same endpoint/chord geometry, with parity tests against
legacy `chord()` for ordinary inputs. Existing `chord.py`, `fovea.py`, chain,
forge, runtime configuration files and submitted notebooks are unchanged.

Two endpoints `a = exp(i theta_y)` and `b = exp(i theta_x)` form a tunnel chord
on a unit circular section of the eye. Its midpoint determines the facing
direction; its half-length determines the opening. Short-arc separation delta
gives half-angle delta/2 and depth `1 - cos(delta/2)`.

The geometric check is `|(a+b)/2|^2 + |(a-b)/2|^2 = 1`. It checks the unit-rim
construction, not learned usefulness, independent evidence, or the full
Euler/quaternion/octonion/sedenion verification equation (not located yet).

For the 3D embedding, each tunnel has a meridian-plane azimuth in the eye's
right/up basis. Endpoint zero points along the inward eye axis; a positive
endpoint angle turns toward that plane's tangent. This plane convention is
new glue for the cube, not a recovered physical law. Eye positions stay fixed.
`shave_to()` remains a convenience planner but now chooses endpoint angles;
the derived chord is authoritative. `add_tunnel()` accepts endpoints directly.
Even the immutable central view is represented by endpoints (+6, -6 degrees).

`update_tunnel()` rotates or separates the endpoints. A real endpoint change
increments the tunnel revision and makes its recorded connections stale.
Returning to the previous angles does not revive old bindings: explicitly
reconnect after checking visibility. Other tunnels and base connections are
preserved. A separate tunnel exposing the same wire cannot silently refresh
a stale binding. The inspect report separates visibility, binding freshness,
geometry closure, and context conditions. No execution is authorized.

Coincident endpoints give a CLOSED opening with zero solid angle and null
concentration (not infinity). Antipodal endpoints are rejected because their
midpoint cannot pick an aperture side. These explicitly differ from legacy
fovea's minimum-depth clamp and chord's diameter-side convention. The reported
inverse solid angle is attention concentration per steradian, not laser range;
no multi-facet energy distribution or condensate dynamics is simulated.

The connection to the existing chain/forge is currently architectural only:
no automatic focus writes, model calls, promotion or game-action integration.

## Layout and connection contract

The outer cube gives tools addresses, not merely a bag of tool names. Each
wire has a tool ID, a face, and local `(u,v)` coordinates in `[-1,1]`. Face
coordinates mean right/up as seen from outside. A wire protrudes 0.08 cube
units. Each face has an eye fixed at three times its outward normal, looking
toward the centre. This is a proposed geometry, not a claim that earlier
`views.py` already implements physical eyes.

The default eye sees a six-degree half-angle cone derived from its base chord.
The convenience planner chooses a four-degree half-angle chord around an
off-centre wire tip. Adding a tunnel does not move the eye,
replace the existing view, or forget previous connections. Nearby wires can
be exposed by the same shave: the operation changes geometry, not an ID
whitelist. Twenty-four shaves are allowed by default; this is a configurable
prototype resource limit, not a measured optimal setting. Reusing an exposed
wire costs no additional shave.

Registered glows have known addresses even before being resolved. Discovering
those addresses from observations is not implemented. Visibility is restricted
to an eye's own face; no through-wall shortcuts, cross-face ray tracing,
interior occluders, physical material removal, or optical simulation yet.

## Three distinct steps

1. **Resolve:** an existing cone or new shave exposes the wire.
2. **Connect:** explicitly register the eye-to-wire link.
3. **Check context:** supplied boolean observations must satisfy the wire's
   required conditions before it is eligible to make a proposal.

Unknown conditions and false conditions stay distinct. Neither visibility,
connection, nor satisfied preconditions authorizes an action. Conditions are
hand-specified in this prototype, not learned and not causal proof. Inspection
does not retain caller facts across observations.

A connection address includes scope, layout version, eye and wire, and its
recorded binding additionally names the tunnel ID and revision. Layouts
are immutable through the public API; create a fresh cube when tools move or
scope changes. This intentionally requires reconnecting, with no stale links
transferred. Layout-level connection persistence across game frames is a
future integration decision. The existing `CubeLedger` still owns same-pin
request/return accounting. This module does not dispatch helpers, duplicate
that ledger, consume game actions, or inject evidence into existing pins.

## What the next learned layer needs

A useful outer diagonal could link an observed condition wire to a tool wire:
"control mapping unknown AND safe test available -> propose action probe".
Its outcomes must come from the central observer and include cost, invalid
outputs, and whether the returned information changed the actual action model.
For the current candidate, learned probe effects must reach the planner before
we spend more game actions on automatic probing. Geometry alone cannot fix that.

The next comparison should test that complete path against the unchanged
submitted baseline. Shaves could then be selected for a specific unresolved
question, rather than exposing and running every tool automatically. There
is no learned shave selection or non-regression guarantee in this prototype.

## Run

```powershell
python -B -m unittest test_outer_eye_cube test_tunnel_geometry -v
python -B outer_eye_cube.py
```

The accompanying conversation visual is an independent UI illustration of
these geometric rules with demonstration tools and caller-supplied conditions,
not a live view of the ARC agent or evidence of learned usefulness.

Initial prototype verification: 14 geometry tests plus 19 existing routing and 15 existing
question tests pass (48 total). Browser checks at 320 and 736 pixels in light
and dark appearances exercise two additive shaves, two persistent connections,
condition changes, and fixed eye position; no script errors or out-of-bounds
SVG labels were found. Screenshot inspection confirms readable layouts. The
visual shows only the front eye; the Python model tests all six faces.

Tunnel revision verification: 15 new tests cover legacy parity, steering,
widening, angle wrap, the Euler chord identity, closed/ambiguous openings,
revision invalidation, atomic rejection, and reconnection. Together with the
14 prior geometry tests and 34 routing/question tests, 63 tests pass. The
updated browser checks exercise steering, width changes, preserved base links,
stale links, closed openings, context changes and fixed eye position at 320,
360 and 736 pixels in light/dark themes. Screenshot review verified the
rendered marks; the browser test also rejects an empty SVG.

The revised conversation view is a meridian slice of ONE eye, not two eyes
or a complete cube render. Its Y/X controls are rim endpoint angles, not
independent viewer positions. It retains an immutable base aperture and edits
one additional tunnel. Python supports multiple tunnels on all six faces.
