"""Read-only EvidencePin diagnostics and proposal-only effort scheduling.

Electrical names are analogies: need/impact, estimated cost, measured effort.
No physical voltage, inferred frequency from colour, or game execution occurs.
"""
from copy import deepcopy
from hashlib import sha256
import json
from math import isfinite


def _hash(value):
    return sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode()).hexdigest()


def _number(value, *, minimum=0, maximum=1e9):
    if type(value) not in (int, float) or not isfinite(value) or not minimum <= value <= maximum:
        raise ValueError('finite numeric value within declared bounds required')
    return value


def _state_key(state):
    # Display geometry, colours and arrival angles do not influence scheduling.
    return _hash({k: state[k] for k in ('id', 'scope', 'subject', 'action', 'question',
                                      'revision', 'trials', 'refinements')})


class CircuitProbe:
    """One pin/scope; single-owner, in-memory history. Never modifies the pin.

    Steps are caller-provided observation-clock ticks, not seconds. An effort
    receipt records work already done, not a request to do it. Units must be
    consistent across receipts and cost estimates (e.g. game actions).
    """

    def __init__(self, pin, *, unit='action_units', minimum_trials=2,
                 max_samples=256, max_attempts=1024):
        if not isinstance(unit, str) or not unit.strip():
            raise ValueError('named effort unit required')
        if any(type(n) is not int or n < 1 for n in (minimum_trials, max_samples, max_attempts)):
            raise ValueError('positive integer bounds required')
        self._pin, self._unit, self._minimum = pin, unit, minimum_trials
        self._limits = max_samples, max_attempts
        self._history, self._attempts, self._seen = [], {}, {}
        self._latest, self._key = None, None

    def sample(self, step, *, efforts=()):
        """Capture a bounded sample and atomic, deduplicated effort receipts.

        Receipts: id, rule_id, revision, units, observation_ids. A repeated
        receipt adds no cost; inconsistent duplicates reject the whole sample.
        New trial IDs count as observations, NOT independent experiments.
        """
        if type(step) is not int or step < 0 or (self._history and step <= self._history[-1]['step']):
            raise ValueError('strictly increasing nonnegative integer sample steps required')
        if len(self._history) >= self._limits[0]:
            raise ValueError('sample capacity reached; no evidence evicted')
        if not isinstance(efforts, (list, tuple)) or len(efforts) > self._limits[1]:
            raise ValueError('bounded effort receipt list required')
        state = self._pin.snapshot()
        trials = {t['id']: t for t in state['trials']}
        hashes = {name: _hash(t) for name, t in trials.items()}
        if any(hashes.get(name) != value for name, value in self._seen.items()):
            raise ValueError('trial loss or modification detected; start a new scoped probe explicitly')
        bands = {b['id']: b for b in state['bands']}
        attempts = deepcopy(self._attempts)
        for receipt in efforts:
            if not isinstance(receipt, dict) or set(receipt) != {'id', 'rule_id', 'revision', 'units', 'observation_ids'}:
                raise ValueError('complete effort receipt required')
            if not isinstance(receipt['id'], str) or not receipt['id'] or len(receipt['id']) > 256:
                raise ValueError('stable bounded effort ID required')
            if receipt['id'] in attempts:
                if _hash(attempts[receipt['id']]['receipt']) != _hash(receipt):
                    raise ValueError('conflicting duplicate effort receipt')
                continue
            if type(receipt['revision']) is not int or receipt['revision'] != state['revision']:
                raise ValueError('effort must reference the current model revision')
            if not isinstance(receipt['rule_id'], str) or receipt['rule_id'] not in bands:
                raise ValueError('unknown effort node')
            band = bands[receipt['rule_id']]
            if band['children']:
                raise ValueError('record effort against an active leaf')
            _number(receipt['units'])
            ids = receipt['observation_ids']
            if not isinstance(ids, list) or any(not isinstance(i, str) for i in ids) or len(set(ids)) != len(ids):
                raise ValueError('unique observation ID list required')
            if not set(ids) <= set(band['trial_ids'] + band['unknown_context_ids']):
                raise ValueError('effort references missing or incompatible observations')
            if len(attempts) >= self._limits[1]:
                raise ValueError('effort capacity reached; nothing evicted')
            attempts[receipt['id']] = dict(receipt=deepcopy(receipt), step=step)
        nodes = []
        for band in state['bands']:
            rows = [trials[i] for i in band['trial_ids']]
            relevant_ids = sorted(set(band['trial_ids'] + band['unknown_context_ids']))
            signals = dict(coverage_deficit=max(0, (self._minimum-len(rows))/self._minimum),
                           unexplained_outcome=int(bool(band['counterexample_ids']) or band['status'] == 'conflicting'),
                           missing_context=int(bool(band['unknown_context_ids'])),
                           missing_rule=int(band['expected'] is None))
            spent = [a for a in attempts.values() if a['receipt']['rule_id'] == band['id']]
            signatures = sorted({_hash(dict(bits=trials[i]['bits'], outcome=trials[i]['outcome'])) for i in relevant_ids})
            nodes.append(dict(rule_id=band['id'], parent=band['parent'], active=not bool(band['children']),
                              conditions=deepcopy(band['conditions']), expected=band['expected'],
                              structural_height=band['height'], need=max(signals.values()), signals=signals,
                              trial_ids=band['trial_ids'], relevant_trial_ids=relevant_ids, signature_ids=signatures,
                              total_effort=sum(a['receipt']['units'] for a in spent),
                              attempt_count=len(spent),
                              model_key=_hash([band['conditions'], band['expected'], band['children']]),
                              factors={name: dict(colour=colour,
                                  yes=sum(t['bits'].get(name) is True for t in rows),
                                  no=sum(t['bits'].get(name) is False for t in rows),
                                  unknown=sum(name not in t['bits'] for t in rows))
                                  for name, colour in state['factor_colours'].items()}))
        sample = dict(step=step, revision=state['revision'], nodes=nodes)
        self._history.append(sample)
        self._seen, self._attempts, self._latest, self._key = hashes, attempts, state, _state_key(state)
        return deepcopy(sample)

    def analyze(self, estimates, *, budget):
        """Rank leaf proposals using impact * observed-need / estimated-cost.

        An estimate is {impact:0..1 or None, cost:positive or None,
        reachable:True/False/None}. Unknown values block action-test ranking.
        This heuristic is not expected information gain or a calibrated utility.
        """
        _number(budget)
        if self._latest is None:
            raise ValueError('sample the pin first')
        if _state_key(self._pin.snapshot()) != self._key:
            raise ValueError('pin changed; capture a fresh sample before prioritizing')
        if not isinstance(estimates, dict) or not set(estimates) <= {b['id'] for b in self._latest['bands']}:
            raise ValueError('estimates must address known nodes')
        for estimate in estimates.values():
            if not isinstance(estimate, dict) or set(estimate) - {'impact', 'cost', 'reachable'}:
                raise ValueError('impact/cost/reachable estimate fields required')
            if estimate.get('impact') is not None:
                _number(estimate['impact'], maximum=1)
            if estimate.get('cost') is not None:
                _number(estimate['cost'], minimum=1e-9)
            if estimate.get('reachable') is not None and type(estimate['reachable']) is not bool:
                raise ValueError('reachability must be boolean or unknown')
        now = self._history[-1]
        nodes = []
        for original in now['nodes']:
            node = deepcopy(original)
            prior = [dict(step=s['step'], node=n) for s in self._history
                     for n in s['nodes'] if n['rule_id'] == node['rule_id'] and n['model_key'] == node['model_key']]
            elapsed = now['step'] - prior[0]['step']
            previous = prior[-2]['node'] if len(prior) > 1 else None
            effort_delta = node['total_effort']-previous['total_effort'] if previous else 0
            new_ids = set(node['relevant_trial_ids'])-set(previous['relevant_trial_ids']) if previous else set()
            novel = set(node['signature_ids'])-set(previous['signature_ids']) if previous else set()
            diagnostics = []
            if previous and effort_delta > 0 and not new_ids:
                diagnostics.append('effort_without_new_observation')
            if previous and effort_delta > 0 and new_ids and not novel and node['need'] >= previous['need'] and node['need'] > 0:
                diagnostics.append('repeated_context_still_unresolved')
            if previous and node['need'] < previous['need']:
                diagnostics.append('declared_need_decreased')
            changes = sum(a['node']['need'] != b['node']['need'] for a, b in zip(prior, prior[1:]))
            estimate = estimates.get(node['rule_id'], {})
            impact, cost, reachable = (estimate.get(k) for k in ('impact', 'cost', 'reachable'))
            blockers = []
            if not node['active']:
                blockers.append('historical_parent')
            if node['need'] == 0:
                blockers.append('no_declared_need')
            if impact is None:
                blockers.append('impact_unknown')
            elif impact == 0:
                blockers.append('zero_declared_impact')
            if cost is None:
                blockers.append('cost_unknown')
            if reachable is not True:
                blockers.append('unreachable' if reachable is False else 'reachability_unknown')
            potential = None if impact is None else impact * node['need']
            node.update(estimated_impact=impact, estimated_cost=cost, reachable=reachable,
                        potential=potential, priority=None if blockers else potential/cost,
                        blockers=blockers, diagnostics=diagnostics,
                        new_observation_count=len(new_ids), novel_signature_count=len(novel),
                        effort_rate=None if not elapsed else (node['total_effort']-prior[0]['node']['total_effort'])/elapsed,
                        need_changes_per_step=None if not elapsed else changes/elapsed,
                        frequency_hz=None,
                        timeline=[dict(step=p['step'], need=p['node']['need'],
                                       trials=len(p['node']['trial_ids']), effort=p['node']['total_effort']) for p in prior],
                        questions=[deepcopy(q) for q in self._latest['gaps'] if q['rule_id'] == node['rule_id']],
                        proposed_next_step='inspect_repeated_tests_or_missing_features' if diagnostics and
                            any(d in diagnostics for d in ('effort_without_new_observation', 'repeated_context_still_unresolved'))
                            else 'investigate_declared_gap',
                        execution_ready=False)
            if node['active'] and not node['questions'] and node['need'] > 0:
                node['questions'].append(dict(kind='replicate_observation', question='Obtain another observed trial for this branch.',
                                             conditions=node['conditions'], execution_ready=False))
            nodes.append(node)
        ranked = sorted([n for n in nodes if n['priority'] is not None], key=lambda n: (-n['priority'], n['rule_id']))
        remaining, selected = budget, []
        for node in ranked:
            if node['estimated_cost'] <= remaining:
                selected.append(dict(rule_id=node['rule_id'], cost=node['estimated_cost'], priority=node['priority'],
                                     proposed_next_step=node['proposed_next_step'], execution_ready=False))
                remaining -= node['estimated_cost']
        return deepcopy(dict(scope=self._latest['scope'], pin_id=self._latest['id'], revision=now['revision'],
                             step=now['step'], unit=self._unit, nodes=nodes, proposals=selected,
                             proposed_cost=budget-remaining, remaining_budget=remaining,
                             ranking_policy='greedy one-test-per-leaf; explicit impact times need divided by cost',
                             execution_authorized=False, meaning='diagnostic analogy, not an electrical simulation'))

    def detail(self, rule_id):
        """Zoom into the latest sampled node; no new measurements are invented."""
        if self._latest is None:
            raise ValueError('sample first')
        band = next((b for b in self._latest['bands'] if b['id'] == rule_id), None)
        if band is None:
            raise ValueError('unknown node')
        ids = set(band['trial_ids'] + band['unknown_context_ids'])
        return deepcopy(dict(band=band,
                             trials=[t for t in self._latest['trials'] if t['id'] in ids],
                             bit_bundles=[b for b in self._latest['bit_bundles'] if b['observation_id'] in ids],
                             arrivals={k: v for k, v in self._latest['arrivals'].items() if k in ids},
                             timing='sampling steps only; colours and angles do not specify frequency'))
