"""Pure endpoint geometry from chord.py/fovea.py, without runtime config I/O.

Angles are degrees. Coincident endpoints close the opening. A diameter is
rejected: its zero midpoint cannot choose one of the two aperture normals.
No BEC dynamics, optical range, tool-quality score or learned policy here.
"""
from dataclasses import dataclass
from math import cos, sin, radians, pi, isfinite


@dataclass(frozen=True)
class TunnelChord:
    theta_y: float
    theta_x: float

    def __post_init__(self):
        for field in ("theta_y", "theta_x"):
            value = getattr(self, field)
            if type(value) not in (int, float) or not isfinite(value) or abs(value) > 1e9:
                raise ValueError("finite endpoint angle within +/-1e9 degrees required")
            object.__setattr__(self, field, value % 360)
        if abs(abs(self.signed_separation) - 180) < 1e-9:
            raise ValueError("opposite endpoints need an explicit aperture-side choice")

    @property
    def signed_separation(self):
        return (self.theta_y - self.theta_x + 180) % 360 - 180

    @property
    def direction(self):
        return (self.theta_x + self.signed_separation / 2) % 360

    @property
    def half_angle(self):
        return abs(self.signed_separation) / 2

    @property
    def endpoints(self):
        return tuple((cos(radians(t)), sin(radians(t))) for t in (self.theta_y, self.theta_x))

    @property
    def midpoint(self):
        a, b = self.endpoints
        return tuple((x+y)/2 for x,y in zip(a,b))

    @property
    def half_chord(self):
        a, b = self.endpoints
        return tuple((x-y)/2 for x,y in zip(a,b))

    @property
    def depth(self):
        return 2 * sin(radians(self.half_angle) / 2) ** 2

    @property
    def opening(self):
        return sin(radians(self.half_angle))

    @property
    def solid_angle(self):
        return 2*pi*self.depth

    @property
    def closure_residual(self):
        return abs(sum(x*x for x in self.midpoint + self.half_chord) - 1)

    def snapshot(self):
        return {"theta_y": self.theta_y, "theta_x": self.theta_x,
                "endpoints": self.endpoints, "midpoint": self.midpoint,
                "half_chord": self.half_chord, "direction_deg": self.direction,
                "half_angle_deg": self.half_angle, "depth": self.depth,
                "opening": self.opening, "solid_angle_sr": self.solid_angle,
                "concentration_per_sr": 1/self.solid_angle if self.solid_angle else None,
                "closed": self.half_angle == 0,
                "closure_residual": self.closure_residual}
