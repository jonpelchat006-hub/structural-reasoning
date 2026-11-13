"""Conservative automatic boolean splits for EvidencePin. No game execution.

Fit chooses a unique exact split; disjoint checks accept or reject that choice.
This deliberately abstains on noisy, tied, incomplete or multi-step-only fits.
It learns within caller-supplied features, not from raw pixels or vortex physics.
"""
from copy import deepcopy
from hashlib import sha256
import json


def _canonical(value):
    return json.dumps(value, sort_keys=True, allow_nan=False, separators=(',', ':'))


def _fingerprint(state):
    # Delivery angles/counts are metadata, not new evidence. No proposal survives
    # changes to the actual model, identity, feature schema, or trial records.
    fields = ('id', 'scope', 'subject', 'action', 'question', 'revision',
              'factor_colours', 'bands', 'trials', 'refinements')
    return sha256(_canonical({k: state[k] for k in fields}).encode()).hexdigest()


def _ids(values, known):
    if not isinstance(values, (list, tuple)) or any(not isinstance(v, str) for v in values):
        raise ValueError('explicit list/tuple of observation IDs required')
    if len(values) != len(set(values)) or not set(values) <= known:
        raise ValueError('unique known observation IDs required')
    return sorted(values)


def _partition(trials, conditions):
    matching, unknown = [], []
    for trial in trials:
        bits = trial['bits']
        if any(k in bits and bits[k] != v for k, v in conditions.items()):
            continue
        if any(k not in bits for k in conditions):
            unknown.append(trial['id'])
        else:
            matching.append(trial)
    return matching, unknown


class AutomaticPinRefiner:
    def __init__(self, *, minimum_fit=2, minimum_check=2):
        if any(type(v) is not int or v < 1 for v in (minimum_fit, minimum_check)):
            raise ValueError('positive integer per-branch support quotas required')
        self._minimum_fit, self._minimum_check = minimum_fit, minimum_check

    def inspect(self, pin, *, fit_ids, check_ids):
        """Read-only proposal. Checks never select a feature among tied fits.

        Data roles must be assigned by the caller before inspecting outcomes.
        IDs ensure provenance/deduplication, not statistical independence.
        Unassigned trials cannot promote a split, but may veto a contradiction.
        """
        state = pin.snapshot()
        known = {t['id'] for t in state['trials']}
        fit_ids, check_ids = _ids(fit_ids, known), _ids(check_ids, known)
        if set(fit_ids) & set(check_ids):
            raise ValueError('fit and check sets must be disjoint')
        index = {t['id']: t for t in state['trials']}
        fit = [index[k] for k in fit_ids]
        checks = [index[k] for k in check_ids]
        reports, selected = [], None
        for rule in state['bands']:
            if rule['children']:
                continue
            rows, missing_parent = _partition(fit, rule['conditions'])
            validation, missing_check_parent = _partition(checks, rule['conditions'])
            report = dict(rule_id=rule['id'], conditions=deepcopy(rule['conditions']),
                          fit_ids=[t['id'] for t in rows], check_ids=[t['id'] for t in validation],
                          candidates=[], questions=[], status='no_supported_split')
            reports.append(report)

            def question(kind, text, **details):
                report['questions'].append(dict(kind=kind, question=text,
                    scope=state['scope'], subject=state['subject'], action=state['action'],
                    target_question=state['question'], rule_id=rule['id'],
                    conditions=deepcopy(rule['conditions']), execution_ready=False, **details))

            if missing_parent or missing_check_parent:
                report['status'] = 'missing_parent_context'
                question('measure_missing_context', 'Measure missing branch conditions; do not guess them.',
                         observation_ids=sorted(set(missing_parent+missing_check_parent)))
                continue
            if len({t['outcome'] for t in rows}) < 2:
                report['status'] = 'no_observed_contrast'
                # No constant-rule installer yet: a uniform sample cannot choose
                # a distinguishing condition. Existing rules are left intact.
                question('seek_contrast', 'Can a reachable case challenge the current outcome pattern?')
                continue
            for factor in sorted(set(state['factor_colours'])-set(rule['conditions'])):
                candidate = dict(factor=factor, status='unsupported', branches=[])
                report['candidates'].append(candidate)
                missing = [t['id'] for t in rows if factor not in t['bits']]
                if missing:
                    candidate.update(status='missing_fit_feature', missing_ids=missing)
                    continue
                for value in (False, True):
                    branch = [t for t in rows if t['bits'][factor] == value]
                    outcomes = {t['outcome'] for t in branch}
                    candidate['branches'].append(dict(value=value, fit_ids=[t['id'] for t in branch],
                        expected=next(iter(outcomes)) if len(outcomes) == 1 else None))
                if any(len(b['fit_ids']) < self._minimum_fit for b in candidate['branches']):
                    candidate['status'] = 'insufficient_fit_support'
                elif any(b['expected'] is None for b in candidate['branches']):
                    candidate['status'] = 'mixed_branch_outcomes'
                elif candidate['branches'][0]['expected'] == candidate['branches'][1]['expected']:
                    candidate['status'] = 'no_distinguishing_effect'
                else:
                    candidate['status'] = 'fit_supported'
            supported = [c for c in report['candidates'] if c['status'] == 'fit_supported']
            if len(supported) > 1:
                report['status'] = 'ambiguous_fit'
                # A concrete pair of assignments where the first two tied
                # hypotheses disagree; neither outcome is asserted to be true.
                first, second = supported[:2]
                choices = []
                for a in first['branches']:
                    for b in second['branches']:
                        if a['expected'] != b['expected']:
                            choices.append(dict(bits={**rule['conditions'], first['factor']: a['value'],
                                                      second['factor']: b['value']},
                                                predictions={first['factor']: a['expected'],
                                                             second['factor']: b['expected']}))
                question('distinguish_hypotheses', 'Can either disagreement case be reached and observed?',
                         factors=[c['factor'] for c in supported], cases=choices, reachability='unknown')
                continue
            if not supported:
                question('collect_or_expand_features',
                         'Collect branch contrasts or measure another condition; no supported one-step split exists.',
                         candidate_statuses={c['factor']: c['status'] for c in report['candidates']})
                continue
            candidate = supported[0]
            factor = candidate['factor']
            report['chosen_on_fit'] = factor
            unknown = [t['id'] for t in validation if factor not in t['bits']]
            errors = []
            for branch in candidate['branches']:
                matching = [t for t in validation if factor in t['bits'] and t['bits'][factor] == branch['value']]
                branch['check_ids'] = [t['id'] for t in matching]
                errors.extend(t['id'] for t in matching if t['outcome'] != branch['expected'])
            report.update(check_errors=errors, missing_check_feature=unknown)
            if errors:
                report['status'] = 'check_failed'
                question('explain_check_failure', 'Which missing condition explains the checking counterexamples?',
                         observation_ids=errors)
                continue
            if unknown or any(len(b['check_ids']) < self._minimum_check for b in candidate['branches']):
                report['status'] = 'insufficient_check_support'
                question('collect_check_cases', 'Obtain fresh checking trials for both branches, without refitting this choice.',
                         factor=factor, missing_ids=unknown,
                         branches=[dict(value=b['value'], required=max(0, self._minimum_check-len(b['check_ids'])))
                                   for b in candidate['branches']])
                continue
            # Never hide a known counterexample just because the caller did not
            # put it into a fit/check cohort. These records can only veto.
            all_rows, all_unknown = _partition(state['trials'], rule['conditions'])
            all_unknown += [t['id'] for t in all_rows if factor not in t['bits']]
            all_errors = [t['id'] for t in all_rows if factor in t['bits'] and
                          t['outcome'] != candidate['branches'][int(t['bits'][factor])]['expected']]
            if all_unknown or all_errors:
                report['status'] = 'unresolved_retained_evidence'
                question('resolve_retained_evidence', 'Resolve retained counterexamples or missing context before refining.',
                         missing_ids=sorted(set(all_unknown)), counterexample_ids=all_errors)
                continue
            report['status'] = 'ready'
            if selected is None:  # At most one mutation per step; then recompute.
                selected = dict(rule_id=rule['id'], factor=factor,
                                absent_expected=candidate['branches'][0]['expected'],
                                present_expected=candidate['branches'][1]['expected'])
        return dict(schema='automatic-pin-refiner-v1', pin_id=state['id'], scope=state['scope'],
                    revision=state['revision'], evidence_fingerprint=_fingerprint(state),
                    policy=dict(minimum_fit=self._minimum_fit, minimum_check=self._minimum_check),
                    fit_ids=fit_ids, check_ids=check_ids, reports=reports, selected=selected,
                    status='ready' if selected else 'abstain', execution_authorized=False)

    def apply(self, pin, proposal):
        """Revalidate the complete proposal before installing a local candidate.

        Synchronous/single-owner API, not thread-safe or a security boundary.
        Calling this changes only EvidencePin, never a game or active planner.
        """
        if not isinstance(proposal, dict) or 'fit_ids' not in proposal or 'check_ids' not in proposal:
            raise ValueError('refiner proposal required')
        current = self.inspect(pin, fit_ids=proposal['fit_ids'], check_ids=proposal['check_ids'])
        if _canonical(proposal) != _canonical(current):
            raise ValueError('stale, altered, or incompatible proposal')
        if current['status'] != 'ready':
            return dict(status='abstained', changed=False, proposal=current)
        choice = current['selected']
        children = pin.lift(choice['rule_id'], factor=choice['factor'],
                            absent_expected=choice['absent_expected'], present_expected=choice['present_expected'],
                            expected_revision=current['revision'])
        return dict(status='refined_candidate', changed=True, children=list(children),
                    proposal=current, execution_authorized=False)

    def step(self, pin, *, fit_ids, check_ids):
        return self.apply(pin, self.inspect(pin, fit_ids=fit_ids, check_ids=check_ids))
