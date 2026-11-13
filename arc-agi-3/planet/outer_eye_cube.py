"""Fixed-eye tool-address geometry. Offline prototype, not an action policy.

Axis endpoints form tunnel chords that derive shaves; no game actions occur.
Face bases use u right, v up when looking at the face from outside.
"""
from dataclasses import dataclass
from math import acos, atan2, cos, degrees, isfinite, radians, sin, sqrt
from types import MappingProxyType
from tunnel_geometry import TunnelChord


# Outward normal, screen-right, screen-up. Cube bounds are [-1, 1].
FACES = MappingProxyType({
    "front": ((0, 0, 1), (1, 0, 0), (0, 1, 0)),
    "back": ((0, 0, -1), (-1, 0, 0), (0, 1, 0)),
    "right": ((1, 0, 0), (0, 0, -1), (0, 1, 0)),
    "left": ((-1, 0, 0), (0, 0, 1), (0, 1, 0)),
    "top": ((0, 1, 0), (1, 0, 0), (0, 0, -1)),
    "bottom": ((0, -1, 0), (1, 0, 0), (0, 0, 1)),
})


def _number(value, low, high):
    if type(value) not in (int, float) or not isfinite(value) or not low <= value <= high:
        raise ValueError(f"finite number in [{low}, {high}] required")
    return value


def _name(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("nonempty name required")


def face_point(face, u, v, protrusion=0.):
    _number(u, -1, 1)
    _number(v, -1, 1)
    _number(protrusion, 0, .25)
    n, right, up = FACES[face]
    return tuple((1 + protrusion) * n[i] + u * right[i] + v * up[i] for i in range(3))


def _unit(vector):
    length = sqrt(sum(x*x for x in vector))
    if length == 0:
        raise ValueError("zero direction")
    return tuple(x / length for x in vector)


def _angle(a, b):
    return degrees(acos(max(-1., min(1., sum(x*y for x, y in zip(a, b))))))


@dataclass(frozen=True)
class Wire:
    id: str
    tool: str
    face: str
    u: float
    v: float
    requires: tuple[str, ...] = ()

    def __post_init__(self):
        _name(self.id)
        _name(self.tool)
        face_point(self.face, self.u, self.v)
        if type(self.requires) is not tuple or len(set(self.requires)) != len(self.requires):
            raise ValueError("unique condition names in an immutable tuple required")
        for name in self.requires:
            _name(name)

    @property
    def foot(self):
        return face_point(self.face, self.u, self.v)

    @property
    def tip(self):
        return face_point(self.face, self.u, self.v, .08)


@dataclass(frozen=True)
class Eye:
    face: str

    def __post_init__(self):
        if self.face not in FACES:
            raise ValueError("unknown eye face")

    @property
    def position(self):
        return tuple(3 * x for x in FACES[self.face][0])

    @property
    def axis(self):
        return tuple(-x for x in FACES[self.face][0])

    def ray(self, wire):
        return _unit(tuple(t - p for t, p in zip(wire.tip, self.position)))


@dataclass(frozen=True)
class Shave:
    id: str
    eye: str
    revision: int
    chord: TunnelChord
    azimuth: float

    @property
    def half_angle(self):
        return self.chord.half_angle

    @property
    def axis(self):
        # Embed the rim circle in a meridian plane of this eye's sphere.
        n, right, up = FACES[self.eye]
        phi, theta = radians(self.azimuth), radians(self.chord.direction)
        tangent = tuple(cos(phi)*r + sin(phi)*u for r,u in zip(right,up))
        return tuple(-normal*cos(theta) + t*sin(theta) for normal,t in zip(n,tangent))


class OuterEyeCube:
    """One immutable layout; create a new instance for a new layout/scope.

    All registered glows have addresses. Resolved wires lie inside a view cone.
    Same-face-only visibility is deliberately conservative, not a ray tracer.
    Conditions are caller observations, NOT learned causal/applicability evidence.
    """
    def __init__(self, wires, *, scope="prototype", version="1", base_angle=6., max_shaves=24):
        _name(scope)
        _name(version)
        _number(base_angle, .1, 45)
        if type(max_shaves) is not int or max_shaves < 0:
            raise ValueError("nonnegative integer shave budget required")
        wires = tuple(wires)
        if any(not isinstance(w, Wire) for w in wires):
            raise ValueError("Wire records required")
        if len({w.id for w in wires}) != len(wires):
            raise ValueError("duplicate wire address")
        self._wires = MappingProxyType({w.id: w for w in wires})
        self._eyes = MappingProxyType({face: Eye(face) for face in FACES})
        self._scope, self._version = scope, version
        self._base_angle, self._max_shaves = base_angle, max_shaves
        self._base = {face: Shave("base:"+face, face, 1, TunnelChord(base_angle, -base_angle), 0.)
                      for face in FACES}
        self._shaves, self._connections = [], {}

    @property
    def eyes(self):
        return self._eyes

    @property
    def wires(self):
        return self._wires

    @property
    def shaves(self):
        return tuple(self._shaves)

    @property
    def connections(self):
        return frozenset(self._connections)

    def _covering(self, eye, wire_id):
        observer, wire = self.eyes[eye], self.wires[wire_id]
        if wire.face != eye:
            return []
        ray = observer.ray(wire)
        return [s for s in [self._base[eye], *self.shaves]
                if s.eye == eye and s.half_angle > 0
                and _angle(ray, s.axis) <= s.half_angle + 1e-9]

    def visible(self, eye, wire_id):
        return bool(self._covering(eye, wire_id))

    def add_tunnel(self, eye, theta_y, theta_x, *, azimuth=0.):
        """Connect rim endpoints in a named eye's meridian plane. No config writes."""
        self.eyes[eye]
        _number(azimuth, -1e9, 1e9)
        chord = TunnelChord(theta_y, theta_x)
        if len(self._shaves) >= self._max_shaves:
            raise ValueError("shave budget exhausted")
        shave = Shave(f"tunnel:{len(self._shaves)+1}", eye, 1, chord, azimuth % 360)
        self._shaves.append(shave)
        return shave

    def update_tunnel(self, tunnel_id, theta_y, theta_x):
        """Shift endpoints; old bindings remain recorded but require reconnection.

        Identical normalized endpoints are a no-op. Reject before mutating on
        invalid geometry. Other tunnels, base views and eye positions persist.
        """
        chord = TunnelChord(theta_y, theta_x)
        for i, old in enumerate(self._shaves):
            if old.id == tunnel_id:
                if chord == old.chord:
                    return old
                updated = Shave(old.id, old.eye, old.revision+1, chord, old.azimuth)
                self._shaves[i] = updated
                return updated
        raise ValueError("unknown or immutable base tunnel")

    def shave_to(self, eye, wire_id, *, half_angle=4.):
        """Convenience planner: choose endpoints around the target bearing.

        The endpoints remain the authoritative geometry, not a direct cone override.
        """
        _number(half_angle, .1, 15)
        observer, wire = self.eyes[eye], self.wires[wire_id]
        if wire.face != eye:
            raise ValueError("use the eye facing this wall; no through-wall shortcuts")
        if self.visible(eye, wire_id):
            return None  # Idempotent; an existing view does not cost another shave.
        ray = observer.ray(wire)
        _, right, up = FACES[eye]
        azimuth = degrees(atan2(sum(x*y for x,y in zip(ray,up)),
                               sum(x*y for x,y in zip(ray,right))))
        bearing = _angle(observer.axis, ray)
        return self.add_tunnel(eye, bearing+half_angle, bearing-half_angle, azimuth=azimuth)

    def connect(self, eye, wire_id):
        covering = self._covering(eye, wire_id)
        if not covering:
            raise ValueError("wire must be resolved before connecting")
        selected = min(covering, key=lambda s: (s.half_angle, s.id))
        self._connections[(eye, wire_id)] = (selected.id, selected.revision)
        return (self._scope, self._version, eye, wire_id)

    def inspect(self, eye, wire_id, facts=None):
        facts = {} if facts is None else dict(facts)
        if any(not isinstance(k, str) or type(v) is not bool for k, v in facts.items()):
            raise ValueError("named boolean observations required")
        wire = self.wires[wire_id]
        visible = self.visible(eye, wire_id)
        connected = (eye, wire_id) in self._connections
        binding = self._connections.get((eye, wire_id))
        current = next((s for s in [*self._base.values(), *self.shaves]
                        if binding and (s.id, s.revision) == binding), None)
        fresh = current is not None
        binding_visible = bool(current and current.half_angle > 0 and wire.face == eye
                               and _angle(self.eyes[eye].ray(wire), current.axis) <= current.half_angle + 1e-9)
        unknown = [name for name in wire.requires if name not in facts]
        unmet = [name for name in wire.requires if facts.get(name) is False]
        state = ("wrong_face" if wire.face != eye else "stale_connection" if connected and not fresh
                 else "needs_shave" if not visible
                 else "needs_connection" if not connected else "condition_blocked"
                 if unmet else "condition_unknown" if unknown else "proposal_ready")
        return {"address": [self._scope, self._version, eye, wire_id],
                "tool": wire.tool, "face": wire.face, "uv": [wire.u, wire.v],
                "foot": wire.foot, "tip": wire.tip, "eye_position": self.eyes[eye].position,
                "visible": visible, "connected": connected, "state": state,
                "binding": binding, "binding_current": fresh, "binding_visible": binding_visible,
                "tunnel": current.chord.snapshot() if current else None,
                "unknown": unknown, "unmet": unmet,
                "eligible_for_proposal": state == "proposal_ready",
                "execution_authorized": False}


if __name__ == "__main__":
    import json
    cube = OuterEyeCube([Wire("controls", "control model", "front", 0, 0),
                         Wire("probe", "action probe", "front", .65, .45,
                              ("unknown_control", "safe_to_probe"))])
    before = cube.inspect("front", "probe")
    cube.shave_to("front", "probe")
    cube.connect("front", "probe")
    print(json.dumps({"before": before, "after": cube.inspect("front", "probe",
          {"unknown_control": True, "safe_to_probe": True})}, indent=2))
