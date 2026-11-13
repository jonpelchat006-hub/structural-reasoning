"""Synthetic diagnostic snapshots; prints JSON, no game or file writes."""
import json

from circuit_analysis import CircuitProbe
from evidence_pin import EvidencePin


def run():
    pin = EvidencePin('wall', scope='diagnostic/L1', subject='pixel:3,4', action=1,
                      question='Does this wall move?', expected=True,
                      factors={'contact': 'cyan', 'blue_wall': 'orange'})
    absent, present = pin.lift('root', factor='contact', absent_expected=True,
                               present_expected=True, expected_revision=0)

    def record(name, contact, blue, outcome):
        bits = {'contact': contact, 'blue_wall': blue}
        for i in range(4):
            pin.record(name, scope='diagnostic/L1', action=1, bits=bits, outcome=outcome,
                       observation={'before': bits, 'after': {'moved': outcome}},
                       route=f'view:{i}', direction=[i-1.5, 0, 1])

    record('a0', False, True, False)
    record('a1', False, True, False)
    record('b0', True, True, True)
    record('b1', True, True, False)
    probe = CircuitProbe(pin)
    estimates = {absent: dict(impact=.9, cost=3, reachable=True),
                 present: dict(impact=.8, cost=1, reachable=True)}
    stages = []

    def capture(label, step, efforts=()):
        probe.sample(step, efforts=efforts)
        report = probe.analyze(estimates, budget=3)
        stages.append(dict(label=label, report=report,
                           details={r: probe.detail(r) for r in (absent, present)}))

    def effort(name, units, ids):
        return dict(id=name, rule_id=present, revision=1, units=units, observation_ids=ids)

    capture('Initial gaps', 0)
    capture('Old evidence circulated', 1, [effort('replay', 2, ['b0'])])
    record('b2', True, True, True)
    capture('Repeated context', 2, [effort('repeat', 1, ['b2'])])
    record('b3', True, False, False)
    capture('New context', 3, [effort('contrast', 1, ['b3'])])
    before = pin.snapshot()
    probe.analyze(estimates, budget=3)
    probe.detail(present)
    return dict(stages=stages, source='hand-authored diagnostic fixture',
                pin_unchanged_by_analysis=pin.snapshot() == before,
                limitations=['Costs and impacts are supplied estimates, not measured decision value.',
                             'Need is a declared-gap heuristic, not entropy or voltage.',
                             'Repeated trials can still establish repeatability.',
                             'No frequency in hertz is inferred; step-normalized activity only.',
                             'No game actions or live ARC policy changes.'])


if __name__ == '__main__':
    print(json.dumps(run(), indent=2))
