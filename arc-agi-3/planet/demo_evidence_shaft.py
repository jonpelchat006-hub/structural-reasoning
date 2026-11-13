"""Read-only synthetic demonstration; no ARC/network/file writes.

Toy rule and both refinements are hand-authored. This tests the plumbing and
preservation of evidence, not automatic discovery or improved game scores.
"""
import json

from evidence_pin import EvidencePin
from external_eye_circuit import ExternalEyeCircuit


def run():
    # Three discovery fixtures, then all four combinations as held-out trials.
    cases = [(True, True), (False, True), (True, False),
             (False, False), (False, True), (True, False), (True, True)]
    step = 0

    def frame(index, moved=None):
        contact, blue = cases[min(index, len(cases)-1)]
        return dict(contact=contact, blue_wall=blue, moved=moved)

    def send(request):
        nonlocal step
        contact, blue = cases[step]
        step += 1
        return {**request, 'observation': frame(step, contact and blue)}

    circuit = ExternalEyeCircuit('synthetic/L1', frame(0), send, budget=len(cases))
    pin = EvidencePin('wall-motion', scope='synthetic/L1', subject='pixel:3,4', action=1,
                      question='Does pressing move this wall?',
                      factors={'contact': 'cyan', 'blue_wall': 'orange'}, expected=True)

    def trial():
        views = circuit.views()
        before = views[0]['observation']
        bits = {key: before[key] for key in ('contact', 'blue_wall')}
        prediction = pin.predict(bits)
        replies = [{k: v[k] for k in ('route', 'scope', 'version', 'observation_id')} |
                   {'action': 1} for v in views]
        result = circuit.act(replies, available_actions=[1])
        if result['status'] != 'returned':
            raise RuntimeError('toy exchange did not return')
        returned = circuit.views()
        outcome = returned[0]['observation']['moved']
        for view in returned:
            pin.record(view['observation_id'], scope=view['scope'], action=1, bits=bits,
                       outcome=outcome, observation={'before': before, 'after': view['observation']},
                       route=view['route'], direction=view['direction'])
        return dict(bits=bits, prediction=prediction['outcome'], outcome=outcome,
                    matched=None if prediction['outcome'] is None else prediction['outcome'] == outcome)

    stages = []

    def capture(label):
        snapshot = pin.snapshot()
        stages.append(dict(label=label, revision=snapshot['revision'],
                           trials=snapshot['trial_count'], bands=snapshot['bands'], gaps=snapshot['gaps']))

    capture('persistent empty question')
    first = trial()
    second = trial()
    capture('broad rule contradicted; evidence retained')
    _, contact_branch = pin.lift('root', factor='contact', absent_expected=False,
                                 present_expected=True, expected_revision=0)
    capture('first lift: contact branches')
    third = trial()
    capture('new failure reopens contact-present branch')
    originals = pin.snapshot()['trials']
    pin.lift(contact_branch, factor='blue_wall', absent_expected=False,
             present_expected=True, expected_revision=1)
    capture('second lift: colour within contact-present branch')
    preserved = originals == pin.snapshot()['trials']
    held_out = [trial() for _ in range(4)]
    capture('held-out cases recorded')
    state = circuit.snapshot()
    snapshot = pin.snapshot()
    return dict(experiment='hand-authored contact AND blue-wall toy',
                discovery=[first, second, third], stages=stages, held_out=held_out,
                held_out_correct=sum(row['matched'] is True for row in held_out),
                held_out_abstained=sum(row['matched'] is None for row in held_out),
                original_trials_preserved_at_second_lift=preserved,
                game_dispatches=step, unique_trials=snapshot['trial_count'],
                arrival_receipts=sum(len(v) for v in snapshot['arrivals'].values()),
                outstanding=state['outstanding'], remaining=state['remaining'],
                limitations=['Toy rule and refinement choices are supplied, not learned.',
                             'Four held-out cases test plumbing, not statistical confidence or ARC gain.',
                             'Colour names and angles are metadata, not evidence or causality.',
                             'Live agent and saved submissions are unchanged.'])


if __name__ == '__main__':
    print(json.dumps(run(), indent=2))
