"""Offline attention/support experiment. Logical gaze, not optical physics.

Frame-wide segmentation supplies a coarse locator. Gaze gates fine neighbour
features only: this is NOT a full sensor-bandwidth or game-action-cost model.
"""
from collections import Counter, deque
from copy import deepcopy
from dataclasses import dataclass
import math

from reaction_resonance import predict, rows_checked


@dataclass(frozen=True)
class Component:
    colour: int
    pixels: frozenset

    @property
    def origin(self):
        return min(x for x, y in self.pixels), min(y for x, y in self.pixels)

    @property
    def centre(self):
        return tuple(sum(p[i] for p in self.pixels)/len(self.pixels) for i in (0, 1))

    @property
    def signature(self):
        x, y = self.origin
        return self.colour, tuple(sorted((a-x, b-y) for a, b in self.pixels))


def components(frame):
    """Four-connected same-colour components; no game-specific palette."""
    if (not frame or not frame[0] or any(len(r) != len(frame[0]) for r in frame)
        or any(type(v) is not int or not 0 <= v <= 15 for r in frame for v in r)):
        raise ValueError('rectangular nonempty ARC palette frame required')
    height, width = len(frame), len(frame[0])
    counts = Counter(v for row in frame for v in row)
    background = min(counts, key=lambda c: (-counts[c], c))
    seen, result = set(), []
    for y in range(height):
        for x in range(width):
            if (x, y) in seen or frame[y][x] == background:
                continue
            colour, todo, pixels = frame[y][x], [(x, y)], set()
            seen.add((x, y))
            while todo:
                a, b = todo.pop()
                pixels.add((a, b))
                for u, v in ((a-1,b), (a+1,b), (a,b-1), (a,b+1)):
                    if (0 <= u < width and 0 <= v < height and (u,v) not in seen
                        and frame[v][u] == colour):
                        seen.add((u,v)); todo.append((u,v))
            result.append(Component(colour, frozenset(pixels)))
    return background, result


def select_object(parts):
    """Deterministic BEFORE-only probe, not an assertion of player identity."""
    counts = Counter(c.signature for c in parts)
    eligible = [c for c in parts if 2 <= len(c.pixels) <= 64 and counts[c.signature] == 1
                and all(max(p[i] for p in c.pixels)-min(p[i] for p in c.pixels) < 12 for i in (0,1))]
    return min(eligible, key=lambda c: (-len(c.pixels), c.colour, c.origin)) if eligible else None


def match_object(obj, parts, maximum_displacement=12):
    """Abstain on duplicate shapes, changed shape/colour, disappearance or jumps.

    Unique appearance is only a tracking heuristic, not proof of physical identity.
    """
    matches = [c for c in parts if c.signature == obj.signature]
    if len(matches) != 1:
        return None
    candidate = matches[0]
    if max(abs(a-b) for a,b in zip(candidate.origin, obj.origin)) > maximum_displacement:
        return None
    return candidate


class Gaze:
    def __init__(self, width, height, *, radius=6, shifting=False, full=False):
        if width < 1 or height < 1 or radius < 1:
            raise ValueError('positive gaze dimensions required')
        self.width, self.height, self.radius = width, height, radius
        self.shifting, self.full = shifting, full
        self.centre = ((width-1)/2, (height-1)/2)
        self.shifts = 0

    def visible(self, point):
        return self.full or max(abs(a-b) for a,b in zip(point, self.centre)) <= self.radius

    def features(self, frame, obj, background):
        # Keys describe visible material, not an unobserved assertion of free space.
        features = {'object_visible': self.visible(obj.centre),
                    'object_left_half': obj.centre[0] < self.width/2,
                    'object_top_half': obj.centre[1] < self.height/2}
        x0, y0 = obj.origin
        x1 = max(x for x,y in obj.pixels); y1 = max(y for x,y in obj.pixels)
        for distance in (1, 2):
            bands = {'left': [(x0-distance,y) for y in range(y0,y1+1)],
                     'right': [(x1+distance,y) for y in range(y0,y1+1)],
                     'up': [(x,y0-distance) for x in range(x0,x1+1)],
                     'down': [(x,y1+distance) for x in range(x0,x1+1)]}
            for side, points in bands.items():
                in_frame = all(0 <= x < self.width and 0 <= y < self.height for x,y in points)
                observed = in_frame and self.visible(obj.centre) and all(self.visible(p) for p in points)
                key = f'{side}_{distance}'
                features[key+'_observed'] = observed
                features[key+'_visible_material'] = bool(observed and any(frame[y][x] != background for x,y in points))
        return features

    def after_surprise(self, loss, target):
        """Called AFTER the forecast is scored. Only next observation is affected."""
        if not math.isfinite(loss) or not 0 <= loss <= 1:
            raise ValueError('Brier residual required')
        if self.shifting and not self.full and loss > .25 and target is not None:
            centre = (max(0, min(self.width-1, target[0])), max(0, min(self.height-1, target[1])))
            if centre != self.centre:
                self.centre = centre
                self.shifts += 1


class SupportMonitor:
    """Score before update; suspend a checked rule after excess recent loss.

    Eight-event regret window, .10 mean excess Brier threshold, rolling 32-event
    unconditional fallback. No automatic re-promotion on the same counterexamples.
    Caller retains original raw journals; this object logs the demotion evidence.
    """
    def __init__(self, verified, history, *, demote=True):
        history = rows_checked(history)
        expected = set(verified['fit_ids'] + verified['check_ids'])
        if not history or {r['event_id'] for r in history} != expected or any(r['scope'] != verified['scope'] for r in history):
            raise ValueError('matching fit/check history required')
        self.model = deepcopy(verified['model'])
        self.scope = verified['scope']
        self.active = self.model is not None
        self.demote = demote
        self.recent = deque((r['outcome'] for r in history[-32:]), maxlen=32)
        self.regret = deque(maxlen=8)
        self.last_step = verified['last_step']
        self.seen = expected
        self.pending = None
        self.demotions = []

    def forecast(self, event_id, scope, step, features):
        if (self.pending is not None or scope != self.scope or event_id in self.seen
            or type(step) is not int or step <= self.last_step):
            raise ValueError('one pending forecast; new chronological same-scope event required')
        if any(type(v) is not bool for v in features.values()):
            raise ValueError('before-action boolean features required')
        base = (sum(self.recent)+1)/(len(self.recent)+2)
        p = predict(self.model, {'features':features}) if self.active else base
        self.pending = dict(event_id=event_id, step=step, prediction=p, baseline=base)
        return deepcopy(self.pending)

    def observe(self, outcome):
        if self.pending is None or type(outcome) is not bool:
            raise ValueError('observed boolean following a forecast required')
        result = self.pending
        loss = (float(outcome)-result['prediction'])**2
        baseline_loss = (float(outcome)-result['baseline'])**2
        result.update(loss=loss, baseline_loss=baseline_loss, outcome=outcome)
        self.regret.append(deepcopy(result))
        if (self.demote and self.active and len(self.regret) == 8
            and sum(r['loss']-r['baseline_loss'] for r in self.regret)/8 > .10):
            self.active = False
            self.demotions.append(dict(reason='recent_excess_prediction_loss',
                effective_after=result['event_id'], evidence=deepcopy(list(self.regret))))
        self.recent.append(outcome)
        self.seen.add(result['event_id']); self.last_step = result['step']
        self.pending = None
        return deepcopy(result)
