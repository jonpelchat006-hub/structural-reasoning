"""Experimental outside-context contracts. No game commands or physical pins.

A boundary alone is not evidence: each pin names an external region required by
a specific predicate. Local/outside views are subsets of ONE before observation.
"""
from collections import deque
from dataclasses import dataclass
import hashlib
import json

from surprise_attention import SupportMonitor


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()


@dataclass(frozen=True)
class View:
    event_id: str
    scope: str
    step: int
    frame_hash: str
    phase: str
    pixels: tuple

    @classmethod
    def capture(cls, frame, event_id, scope, step, visible=None):
        if (not event_id or not scope or type(step) is not int or step < 0 or not frame
            or not frame[0] or any(len(row)!=len(frame[0]) for row in frame)
            or any(type(v) is not int or not 0 <= v <= 15 for row in frame for v in row)):
            raise ValueError('identified before-action ARC frame required')
        pixels = tuple((x,y,v) for y,row in enumerate(frame) for x,v in enumerate(row)
                       if visible is None or (x,y) in visible)
        return cls(event_id,scope,step,digest(frame),'before',pixels)


@dataclass(frozen=True)
class BorderPin:
    feature: str
    scope: str
    event_id: str
    step: int
    frame_hash: str
    object_id: str
    anchor: tuple
    points: tuple
    background: int
    expected_mask: tuple = ()

    @classmethod
    def request(cls, view, obj, feature, anchor, points, background, expected_mask=()):
        if not feature or not points or len(set(points)) != len(points):
            raise ValueError('named nonempty unique context region required')
        if expected_mask and (len(expected_mask)!=len(points) or any(type(v) is not bool for v in expected_mask)):
            raise ValueError('boolean mask must cover the exact context region')
        x0,y0 = obj.origin
        x1,y1 = max(x for x,y in obj.pixels),max(y for x,y in obj.pixels)
        ax,ay = anchor
        on_border = ((ax in (x0-.5,x1+.5) and y0-.5 <= ay <= y1+.5)
                     or (ay in (y0-.5,y1+.5) and x0-.5 <= ax <= x1+.5))
        if not on_border or any(x0 <= x <= x1 and y0 <= y <= y1 for x,y in points):
            raise ValueError('pin must join the object border to an outside region')
        return cls(feature,view.scope,view.event_id,view.step,view.frame_hash,digest(obj.signature),
                   tuple(anchor),tuple(points),background,tuple(expected_mask))


def bind(pin, view):
    """Unknown remains None. Copying a binding does not add independent support."""
    expected = (pin.scope,pin.event_id,pin.step,pin.frame_hash,'before')
    actual = (view.scope,view.event_id,view.step,view.frame_hash,view.phase)
    result = dict(feature=pin.feature, event_id=pin.event_id, scope=pin.scope,
                  anchor=pin.anchor, points=pin.points, value=None, execution_authorized=False)
    if expected != actual:
        return dict(result,status='rejected',reason='stale_scope_frame_or_phase',evidence_id=None)
    pixels = {(x,y):v for x,y,v in view.pixels}
    if any(point not in pixels for point in pin.points):
        return dict(result,status='exposed',reason='unobserved_required_region',evidence_id=None)
    material = tuple(pixels[p] != pin.background for p in pin.points)
    value = material == pin.expected_mask if pin.expected_mask else any(material)
    # View name is deliberately absent: two views of one event are not two events.
    evidence_id = digest([pin.scope,pin.event_id,pin.frame_hash,pin.feature,pin.points,material])
    return dict(result,status='bound',reason='observed_before_context',value=value,evidence_id=evidence_id)


def neighbourhood_pins(view, obj, background):
    x0,y0 = obj.origin
    x1,y1 = max(x for x,y in obj.pixels),max(y for x,y in obj.pixels)
    cx,cy = ((x0+x1)/2,(y0+y1)/2)
    result = []
    for distance in (1,2):
        sides = [('left',(x0-.5,cy),[(x0-distance,y) for y in range(y0,y1+1)]),
                 ('right',(x1+.5,cy),[(x1+distance,y) for y in range(y0,y1+1)]),
                 ('up',(cx,y0-.5),[(x,y0-distance) for x in range(x0,x1+1)]),
                 ('down',(cx,y1+.5),[(x,y1+distance) for x in range(x0,x1+1)])]
        for side,anchor,points in sides:
            result.append(BorderPin.request(view,obj,f'{side}_{distance}_material',anchor,points,background))
    return result


class BindingLedger:
    """Trace transport and invalidation, not a verifier of game rules."""
    def __init__(self):
        self.previous, self.seen, self.events = {}, {}, []

    def record(self, pin, binding):
        key = (pin.scope,pin.object_id,pin.feature)
        identity = (pin.scope,pin.event_id,pin.object_id,pin.feature)
        signature = digest(binding)
        if identity in self.seen:
            if self.seen[identity] != signature: raise ValueError('conflicting duplicate binding')
            return None
        previous = self.previous.get(key)
        operation = 'exposed' if binding['status']=='exposed' else 'bound'
        if binding['status']=='rejected': operation='broken_binding'
        elif previous and binding['status']=='bound' and previous['status']=='bound':
            operation = 'bent' if (previous['anchor'],previous['points']) != (binding['anchor'],binding['points']) else 'refreshed'
        event = dict(event_id=pin.event_id,feature=pin.feature,operation=operation,
            value_changed=bool(previous and previous['status']=='bound' and binding['status']=='bound'
                               and previous['value'] != binding['value']),
            evidence_id=binding['evidence_id'])
        self.seen[identity]=signature; self.previous[key]=binding.copy(); self.events.append(event)
        return event


class ContextMonitor(SupportMonitor):
    """Unobserved conditions use fallback and cannot count against a rule.

    Breaking a binding and challenging a predictive rule are distinct operations.
    Eight consecutive usable predictions with mean excess loss > .10 suspend the
    rule. This is the previous heuristic, NOT a proven noise/drift discriminator.
    """
    def __init__(self, verified, history, *, guard=True):
        super().__init__(verified,history,demote=False)
        self.guard = guard
        self.known_regret = deque(maxlen=8)

    def forecast(self,event_id,scope,step,features):
        missing = self.model is not None and self.model['feature'] not in features
        # A deliberately naive comparison maps missing to False; never used live.
        supplied = dict(features)
        if missing and not self.guard: supplied[self.model['feature']]=False
        super().forecast(event_id,scope,step,supplied)
        if missing and self.guard: self.pending['prediction']=self.pending['baseline']
        self.pending['context_missing']=missing
        self.pending['rule_used']=self.active and not (missing and self.guard)
        return self.pending.copy()

    def observe(self,outcome):
        result = super().observe(outcome)
        if result['rule_used']:
            self.known_regret.append(result.copy())
            if (self.active and len(self.known_regret)==8 and
                sum(r['loss']-r['baseline_loss'] for r in self.known_regret)/8 > .10):
                self.active=False
                self.demotions.append(dict(reason='possible_rule_or_model_failure',
                    effective_after=result['event_id'],evidence=list(self.known_regret)))
        else: self.known_regret.clear()
        result['diagnosis'] = ('missing_context' if result['context_missing'] else
            'no_active_rule' if not result['rule_used'] else
            'observed_prediction_error' if result['loss'] > .25 else 'consistent_prediction')
        return result
