"""Persistent question shafts with append-only trials and explicit refinements.

Offline representation, not perception or causal inference. Directions/colours
are display metadata. Every gap is a named test/model question, not empty space.
"""
from copy import deepcopy
import json
from math import isfinite, sqrt


def _name(value):
    if not isinstance(value, str) or not value.strip() or len(value) > 256:
        raise ValueError('nonempty name of at most 256 characters required')
    return value


def _json_copy(value):
    raw = json.dumps(value, allow_nan=False, sort_keys=True)
    if len(raw.encode('utf-8')) > 100_000:
        raise ValueError('observation exceeds pin record budget')
    return json.loads(raw)


def _direction(value):
    if not isinstance(value, (tuple, list)) or len(value) != 3 or any(
            type(v) not in (int, float) or not isfinite(v) for v in value):
        raise ValueError('three finite direction components required')
    size = sqrt(sum(v*v for v in value))
    if not isfinite(size) or size == 0:
        raise ValueError('finite nonzero direction required')
    return [v/size for v in value]


class EvidencePin:
    """One scoped subject/action/outcome question, with a finite boolean schema.

    Callers supply observed bits and before/after data; this class cannot verify
    their origin. A missing bit means unknown, not false. Stable trial IDs are
    deduplicated across eye routes. Split rules are proposed by the caller.
    """

    def __init__(self, pin_id, *, scope, subject, action, question, factors,
                 expected=None, max_trials=512, max_rules=63):
        for value in (pin_id, scope, subject, question):
            _name(value)
        if type(action) is not int:
            raise ValueError('integer action required')
        if expected is not None and type(expected) is not bool:
            raise ValueError('expected must be boolean or unknown')
        if not isinstance(factors, dict) or not 1 <= len(factors) <= 16:
            raise ValueError('declare 1..16 factor names with display colours')
        for name, colour in factors.items():
            _name(name)
            _name(colour)
        if any(type(v) is not int or v < 1 for v in (max_trials, max_rules)):
            raise ValueError('positive record budgets required')
        self._identity = dict(id=pin_id, scope=scope, subject=subject,
                              action=action, question=question)
        self._factors = deepcopy(factors)
        self._limits = (max_trials, max_rules)
        self._trials, self._arrivals, self._events = {}, {}, []
        self._rules = {'root': dict(id='root', parent=None, conditions={},
                                   expected=expected, children=[], depth=0)}
        self._revision = 0

    def record(self, observation_id, *, scope, action, bits, outcome,
               observation, route, direction):
        """Add an actual supplied trial; repeated routing adds no trial weight."""
        _name(observation_id)
        _name(route)
        if scope != self._identity['scope'] or type(action) is not int or action != self._identity['action']:
            raise ValueError('wrong scope/action')
        if type(outcome) is not bool or not isinstance(bits, dict) or any(
                k not in self._factors or type(v) is not bool for k, v in bits.items()):
            raise ValueError('observed boolean outcome and declared boolean bits required')
        if not isinstance(observation, dict) or not {'before', 'after'} <= observation.keys():
            raise ValueError('retain before/after observations')
        trial = dict(id=observation_id, bits=deepcopy(bits), outcome=outcome,
                     observation=_json_copy(observation))
        arrival = dict(route=route, direction=_direction(direction))
        previous = self._trials.get(observation_id)
        if previous is not None and json.dumps(previous, sort_keys=True) != json.dumps(trial, sort_keys=True):
            raise ValueError('conflicting duplicate trial; original retained')
        arrivals = self._arrivals.get(observation_id, [])
        if arrival not in arrivals and len(arrivals) >= 8:
            raise ValueError('arrival metadata budget exhausted')
        if previous is None and len(self._trials) >= self._limits[0]:
            raise ValueError('trial budget exhausted; nothing evicted')
        if previous is None:
            self._trials[observation_id] = trial
        self._arrivals.setdefault(observation_id, [])
        if arrival not in arrivals:
            self._arrivals[observation_id].append(arrival)
        return previous is None

    def lift(self, rule_id, *, factor, absent_expected, present_expected,
             expected_revision):
        """Retain a leaf as parent; add two candidate branches atomically.

        Does not close questions, erase counterexamples, or certify a new rule.
        Historical trials are partitioned by recorded bits, never guessed bits.
        """
        if type(expected_revision) is not int or expected_revision != self._revision:
            raise ValueError('stale model revision')
        if rule_id not in self._rules or factor not in self._factors:
            raise ValueError('unknown rule or factor')
        parent = self._rules[rule_id]
        if parent['children'] or factor in parent['conditions']:
            raise ValueError('split an unsplit leaf on a new condition')
        if any(v is not None and type(v) is not bool for v in (absent_expected, present_expected)):
            raise ValueError('candidate outcomes must be boolean or unknown')
        if len(self._rules)+2 > self._limits[1]:
            raise ValueError('rule budget exhausted; nothing replaced')
        revision = self._revision+1
        children = []
        for value, expected in ((False, absent_expected), (True, present_expected)):
            child_id = f'r{revision}:{int(value)}'
            children.append(dict(id=child_id, parent=rule_id,
                                 conditions={**parent['conditions'], factor: value},
                                 expected=expected, children=[], depth=parent['depth']+1))
        self._events.append(dict(revision=revision, kind='lift', parent=rule_id,
                                 previous_rule=deepcopy(parent), factor=factor,
                                 children=[c['id'] for c in children]))
        for child in children:
            self._rules[child['id']] = child
        parent['children'] = [c['id'] for c in children]
        self._revision = revision
        return tuple(parent['children'])

    def _partition(self, conditions):
        matching, unknown = [], []
        for trial in self._trials.values():
            bits = trial['bits']
            if any(k in bits and bits[k] != v for k, v in conditions.items()):
                continue
            if any(k not in bits for k in conditions):
                unknown.append(trial['id'])
            else:
                matching.append(trial)
        return matching, unknown

    def predict(self, bits):
        """Read a candidate leaf prediction; not permission or confidence."""
        if not isinstance(bits, dict) or any(k not in self._factors or type(v) is not bool for k, v in bits.items()):
            raise ValueError('declared boolean bits required')
        for rule in self.snapshot()['bands']:
            if rule['children'] or not all(k in bits and bits[k] == v for k, v in rule['conditions'].items()):
                continue
            if rule['expected'] is None or not rule['trial_ids'] or rule['counterexample_ids']:
                break
            return dict(outcome=rule['expected'], rule_id=rule['id'], status='candidate',
                        execution_authorized=False)
        return dict(outcome=None, rule_id=None, status='abstain', execution_authorized=False)

    def snapshot(self):
        """Height is layout only: old IDs/evidence survive insertion below them."""
        bands, gaps = [], []
        max_depth = max(r['depth'] for r in self._rules.values())
        for rule in self._rules.values():
            trials, unknown = self._partition(rule['conditions'])
            outcomes = {t['outcome'] for t in trials}
            status = 'unknown' if not outcomes else 'conflicting' if len(outcomes) > 1 else 'yes' if True in outcomes else 'no'
            counterexamples = [t['id'] for t in trials if rule['expected'] is not None and t['outcome'] != rule['expected']]
            bands.append({**deepcopy(rule), 'height': max_depth-rule['depth'],
                          'status': status, 'trial_ids': [t['id'] for t in trials],
                          'unknown_context_ids': unknown, 'counterexample_ids': counterexamples,
                          'historical_parent': bool(rule['children']),
                          'colour_labels': {k: self._factors[k] for k in rule['conditions']}})
            if rule['children']:
                continue  # Parent conflicts remain visible, but branches drive questions.
            pending = []
            if not trials:
                pending.append(('untested_case', 'Obtain an observed trial for this condition combination.'))
            elif rule['expected'] is None:
                pending.append(('unmodelled_relationship', 'Propose a condition-to-outcome rule and a test; observations alone do not specify one.'))
            if counterexamples or len(outcomes) > 1:
                pending.append(('unexplained_observation', 'Which additional condition explains these counterexamples?'))
            if unknown:
                pending.append(('missing_context', 'Can the missing condition be measured for these trials? Do not guess it.'))
            for kind, question in pending:
                gaps.append(dict(id=f"{self._identity['id']}:{rule['id']}:{kind}",
                                 rule_id=rule['id'], kind=kind, question=question,
                                 conditions=deepcopy(rule['conditions']),
                                 scope=self._identity['scope'], revision=self._revision,
                                 subject=self._identity['subject'], action=self._identity['action'],
                                 target_question=self._identity['question'],
                                 counterexample_ids=counterexamples.copy(),
                                 unknown_context_ids=unknown.copy(), execution_ready=False))
        bundles = [dict(observation_id=t['id'], bands=[
            dict(factor=name, colour=colour, height=i,
                 state='unknown' if name not in t['bits'] else 'yes' if t['bits'][name] else 'no')
            for i, (name, colour) in enumerate(self._factors.items())])
            for t in self._trials.values()]
        return deepcopy({**self._identity, 'revision': self._revision,
                         'persistent': True, 'trial_count': len(self._trials),
                         'factor_colours': self._factors, 'bands': bands, 'gaps': gaps,
                         'trials': list(self._trials.values()), 'bit_bundles': bundles, 'arrivals': self._arrivals,
                         'refinements': self._events, 'execution_authorized': False,
                         'meaning': 'observed coverage and candidate rules; not causal verification'})
