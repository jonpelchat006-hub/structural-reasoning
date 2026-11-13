"""Synthetic learning loop: automatic choices, hand-authored environment/features.

No API, filesystem writes, submissions or live policy changes. Fit/check roles
are assigned before outcomes. Final evaluation neither fits nor updates the pin.
"""
from itertools import product
import json

from automatic_pin_refiner import AutomaticPinRefiner
from evidence_pin import EvidencePin
from external_eye_circuit import ExternalEyeCircuit


def run():
    # First two groups reveal contact; third reveals a colour-specific failure.
    # Every group has two fit trials and two disjoint checking trials. Wobble
    # varies within both cohorts and is intentionally unrelated to the outcome.
    training = [(contact, blue, bool(i % 2))
                for contact, blue in [(True, True), (False, True), (True, False)]
                for i in range(4)]
    held_out = list(product((False, True), repeat=3))
    cases = training + held_out
    index = 0

    def frame(i, outcome=None):
        contact, blue, wobble = cases[min(i, len(cases)-1)]
        return dict(contact=contact, blue_wall=blue, wobble=wobble, moved=outcome)

    def transport(request):
        nonlocal index
        contact, blue, _ = cases[index]
        index += 1
        return {**request, 'observation': frame(index, contact and blue)}

    circuit = ExternalEyeCircuit('synthetic-auto/L1', frame(0), transport, budget=len(cases))
    pin = EvidencePin('wall-motion', scope='synthetic-auto/L1', subject='pixel:3,4', action=1,
                      question='Does pressing move the wall?', expected=None,
                      factors={'contact': 'cyan', 'blue_wall': 'orange', 'wobble': 'violet'})
    learner = AutomaticPinRefiner()
    fit_ids, check_ids, learning = [], [], []

    def trial(role):
        incoming = circuit.views()
        before = incoming[0]['observation']
        bits = {k: before[k] for k in ('contact', 'blue_wall', 'wobble')}
        prediction = pin.predict(bits)['outcome']
        replies = [{k: v[k] for k in ('scope', 'route', 'version', 'observation_id')} |
                   {'action': 1} for v in incoming]
        result = circuit.act(replies, available_actions=[1])
        if result['status'] != 'returned':
            raise RuntimeError('toy exchange did not close')
        returned = circuit.views()
        outcome = returned[0]['observation']['moved']
        if role != 'evaluation':
            for view in returned:
                pin.record(view['observation_id'], scope=view['scope'], action=1, bits=bits,
                           outcome=outcome, observation={'before': before, 'after': view['observation']},
                           route=view['route'], direction=view['direction'])
            (fit_ids if role == 'fit' else check_ids).append(returned[0]['observation_id'])
        return dict(bits=bits, predicted=prediction, observed=outcome,
                    correct=None if prediction is None else prediction == outcome)

    for stop in (8, 12):
        while index < stop:
            trial('fit' if index % 4 < 2 else 'check')
        before = pin.snapshot()['trials']
        result = learner.step(pin, fit_ids=fit_ids, check_ids=check_ids)
        learning.append(dict(status=result['status'], choice=result['proposal']['selected'],
                             evidence_preserved=before == pin.snapshot()['trials'],
                             fit_trials=len(fit_ids), check_trials=len(check_ids)))
    frozen = pin.snapshot()
    evaluation = [trial('evaluation') for _ in held_out]
    return dict(experiment='automatic refinement within declared boolean features',
                learning=learning, evaluation=evaluation,
                correct=sum(r['correct'] is True for r in evaluation),
                abstained=sum(r['correct'] is None for r in evaluation),
                evaluation_did_not_change_model_or_evidence=frozen == pin.snapshot(),
                stored_trials=pin.snapshot()['trial_count'],
                stored_view_receipts=sum(len(v) for v in pin.snapshot()['arrivals'].values()),
                game_calls=index, outstanding=circuit.snapshot()['outstanding'],
                limitations=['Environment, feature extractor, and context schedule are hand-authored.',
                             'Split features and branch predictions are learned, not supplied.',
                             'Checking quotas are not statistical confidence or causal proof.',
                             'No automatic navigation, pixel feature discovery, or ARC-score claim.'])


if __name__ == '__main__':
    print(json.dumps(run(), indent=2))
