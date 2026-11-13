"""Experimental three-channel reaction selection; no game actions or physics.

Light = decoded semantic compatibility. Magnetic = complementary condition
support/coverage. Sound = observed prediction residual, NOT an invented Hz value.
A reaction composes a measured boolean feature with an outcome-question pin to
produce a two-branch probabilistic prediction. Verification is separate.
"""
from copy import deepcopy
from dataclasses import dataclass
import math
import random

from pin_channels import Message, PinCodebook, Signal, canonical


POLICIES = ('colour_only', 'compatibility_only', 'residual_only', 'three_channel', 'shuffled_sound')


@dataclass(frozen=True)
class ConditionPin:
    book: PinCodebook
    signal: Signal


def condition_pin(feature, scope, target, *, wavelength=650, orientation=0,
                  phase='observed', position='before'):
    """Declared feature schema; values themselves come from observation rows."""
    message = Message.create('condition:' + feature, scope, 'measured.boolean-feature', phase,
        dict(feature=feature, target=target, role='condition', position=position))
    book = PinCodebook('condition:' + feature, scope, 1,
                       {('measured.boolean-feature', phase): (wavelength, orientation)})
    return ConditionPin(book, book.encode(message))


def rows_checked(rows):
    """One actual event counts once. Different delivery names cannot add support."""
    result, seen = [], {}
    for row in rows:
        if set(row) != {'event_id', 'scope', 'step', 'features', 'outcome'}:
            raise ValueError('exact evidence row schema required')
        if not isinstance(row['event_id'], str) or not row['event_id'] or not isinstance(row['scope'], str) or not row['scope']:
            raise ValueError('event/scope identities required')
        if type(row['step']) is not int or row['step'] < 0 or type(row['outcome']) is not bool:
            raise ValueError('observed boolean outcome and nonnegative step required')
        if not isinstance(row['features'], dict) or any(not isinstance(k, str) or not k or type(v) is not bool for k, v in row['features'].items()):
            raise ValueError('measured boolean features required; omit unknown values')
        key, signature = row['event_id'], canonical(row)
        if key in seen:
            if seen[key] != signature:
                raise ValueError('conflicting duplicate evidence')
            continue
        seen[key] = signature
        result.append(deepcopy(row))
    return sorted(result, key=lambda row: (row['step'], row['event_id']))


def probability(rows):
    # Fixed Laplace smoothing, shared by every policy and the fallback.
    return (sum(r['outcome'] for r in rows) + 1) / (len(rows) + 2)


def brier(rows, predictions):
    if not rows or len(rows) != len(predictions):
        raise ValueError('nonempty equal-sized outcomes/predictions required')
    if any(not math.isfinite(p) or not 0 <= p <= 1 for p in predictions):
        raise ValueError('finite probabilities required')
    return sum((float(row['outcome']) - p)**2 for row, p in zip(rows, predictions)) / len(rows)


def predict(model, row):
    feature = model['feature']
    return model['fallback'] if feature not in row['features'] else model['branches'][str(row['features'][feature])]


class ResonanceReactor:
    """One fit-selected proposal, then independent check; checks never reselect.

    IDs prevent duplicate counting but cannot establish statistical independence.
    The caller must keep future outcomes inaccessible until proposal/verification.
    """
    def __init__(self, *, minimum_branch=4, minimum_gain=0.01, proposal_budget=64):
        if type(minimum_branch) is not int or minimum_branch < 1:
            raise ValueError('positive branch support quota required')
        if not math.isfinite(minimum_gain) or not 0 < minimum_gain < 1:
            raise ValueError('positive gain threshold required')
        if type(proposal_budget) is not int or not 1 <= proposal_budget <= 512:
            raise ValueError('bounded proposal budget required')
        self.minimum_branch, self.minimum_gain, self.proposal_budget = minimum_branch, minimum_gain, proposal_budget

    def propose(self, pins, rows, *, scope, target, policy='three_channel', seed=0):
        if policy not in POLICIES:
            raise ValueError('unknown policy')
        if len(pins) > self.proposal_budget:
            raise ValueError('proposal budget exceeded; do not silently drop inputs')
        rows = rows_checked(rows)
        if not rows or any(row['scope'] != scope for row in rows):
            raise ValueError('nonempty same-scope fit evidence required')
        fallback = probability(rows)
        base_loss = brier(rows, [fallback]*len(rows))
        candidates, rejected, seen = [], [], set()
        for pin in pins:
            value = pin.book.decode(pin.signal).value  # Reject corrupt codecs, never approximate raw colours.
            payload = value['payload']
            feature = payload.get('feature')
            if not isinstance(feature, str) or not feature:
                raise ValueError('feature identity required')
            if feature in seen:
                raise ValueError('duplicate candidate feature')
            seen.add(feature)
            compatible = (value['scope'] == scope and value['phase'] == 'observed' and
                          value['semantic'] == 'measured.boolean-feature' and payload.get('target') == target and
                          payload.get('role') == 'condition' and payload.get('position') == 'before')
            if not compatible:
                rejected.append(dict(feature=feature, reason='semantic_scope_or_direction_mismatch'))
                continue
            groups = {str(bit): [r for r in rows if r['features'].get(feature) is bit] for bit in (False, True)}
            counts = [len(group) for group in groups.values()]
            coverage = sum(counts) / len(rows)
            if coverage != 1.0 or min(counts) < self.minimum_branch:
                rejected.append(dict(feature=feature, reason='missing_or_insufficient_contrast', coverage=coverage))
                continue
            model = dict(feature=feature, branches={bit: probability(group) for bit, group in groups.items()}, fallback=fallback)
            loss = brier(rows, [predict(model, row) for row in rows])
            # Dimensionless design choices, not physical constitutive laws.
            light = 1.0  # Exact matching already enforced; colour is pin-local.
            magnetic = 2 * min(counts) / len(rows)  # Balanced support for a condition and its complement.
            quieting = max(0.0, (base_loss - loss) / max(base_loss, 1e-12))
            candidates.append(dict(feature=feature, model=model, light=light, magnetic=magnetic,
                sound_residual=loss, sound_quieting=quieting, fit_gain=base_loss-loss,
                colour_affinity=max(0.0, 1-abs(pin.signal.wavelength-650)/400),
                branch_counts=counts, fit_ids=[r['event_id'] for r in rows]))
        shuffled = [c['sound_quieting'] for c in candidates]
        random.Random(seed).shuffle(shuffled)
        for index, candidate in enumerate(candidates):
            if policy == 'colour_only': score = candidate['colour_affinity']
            elif policy == 'compatibility_only': score = candidate['magnetic']
            elif policy == 'residual_only': score = candidate['sound_quieting']
            else:
                sound = shuffled[index] if policy == 'shuffled_sound' else candidate['sound_quieting']
                score = (candidate['light'] * candidate['magnetic'] * sound)**(1/3)
            candidate['selection_score'] = score
        # Fixed name tie-break, NEVER a validation/test outcome tie-break.
        candidates.sort(key=lambda candidate: (-candidate['selection_score'], candidate['feature']))
        selected = deepcopy(candidates[0]) if candidates else None
        return dict(status='proposed' if selected else 'unresolved', scope=scope, target=target,
                    policy=policy, fallback=fallback, fit_loss=base_loss, selected=selected,
                    candidates=candidates, rejected=rejected, fit_ids=[r['event_id'] for r in rows],
                    fit_last_step=max(r['step'] for r in rows), feature_checks=len(pins),
                    execution_authorized=False)

    def verify(self, proposal, checks):
        checks = rows_checked(checks)
        if not checks or any(r['scope'] != proposal['scope'] for r in checks):
            raise ValueError('nonempty same-scope check evidence required')
        if set(proposal['fit_ids']) & {r['event_id'] for r in checks} or min(r['step'] for r in checks) <= proposal['fit_last_step']:
            raise ValueError('checks must be later disjoint events')
        base_loss = brier(checks, [proposal['fallback']]*len(checks))
        result = dict(status='unresolved', accepted=False, model=None, fallback=proposal['fallback'],
                      scope=proposal['scope'], fit_ids=list(proposal['fit_ids']),
                      check_loss=base_loss, baseline_check_loss=base_loss, check_gain=0.0,
                      check_ids=[r['event_id'] for r in checks],
                      last_step=max(r['step'] for r in checks), execution_authorized=False)
        candidate = proposal['selected']
        if candidate is None:
            result['reason'] = 'no_supported_candidate_not_proof_of_silence'
            return result
        model = candidate['model']
        feature = model['feature']
        counts = [sum(r['features'].get(feature) is bit for r in checks) for bit in (False, True)]
        if sum(counts) != len(checks) or min(counts) < self.minimum_branch:
            result['reason'] = 'missing_or_insufficient_check_contrast'
            return result
        loss = brier(checks, [predict(model, row) for row in checks])
        gain = base_loss - loss
        accepted = candidate['fit_gain'] >= self.minimum_gain and gain >= self.minimum_gain
        result.update(status='supported_candidate' if accepted else 'rejected', accepted=accepted,
                      model=deepcopy(model) if accepted else None, check_loss=loss, check_gain=gain,
                      reason='later_predictive_gain' if accepted else 'no_reproduced_predictive_gain')
        return result

    def evaluate(self, verified, tests):
        tests = rows_checked(tests)
        if (not tests or any(r['scope'] != verified['scope'] for r in tests) or
            min(r['step'] for r in tests) <= verified['last_step'] or
            set(verified['check_ids'] + verified['fit_ids']) & {r['event_id'] for r in tests}):
            raise ValueError('test evidence must be later and disjoint')
        model = verified['model']
        predictions = [predict(model, row) if model else verified['fallback'] for row in tests]
        return dict(test_events=len(tests), test_brier=brier(tests, predictions),
                    baseline_test_brier=brier(tests, [verified['fallback']]*len(tests)),
                    accuracy=sum((p >= .5) == r['outcome'] for p, r in zip(predictions, tests))/len(tests),
                    accepted=verified['accepted'], execution_authorized=False)
