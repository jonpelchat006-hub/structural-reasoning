from copy import deepcopy
import unittest

from circuit_analysis import CircuitProbe
from evidence_pin import EvidencePin


def pin():
    return EvidencePin('p', scope='g', subject='wall', action=1, question='Does it move?',
                       factors={'a': 'cyan', 'b': 'orange'}, expected=True)


def add(p, name, outcome=True, bits=None, route='view:0'):
    bits = {'a': True, 'b': False} if bits is None else bits
    p.record(name, scope='g', action=1, bits=bits, outcome=outcome,
             observation={'before': bits, 'after': {'moved': outcome}},
             route=route, direction=[1, 0, 1])


def effort(name, ids, units=1, rule='root', revision=0):
    return dict(id=name, rule_id=rule, revision=revision, units=units, observation_ids=ids)


def estimate(cost=1, impact=1, reachable=True):
    return dict(cost=cost, impact=impact, reachable=reachable)


class CircuitAnalysisTests(unittest.TestCase):
    def test_empty_node_has_need_but_unknown_estimates_block_ranking(self):
        p = pin(); probe = CircuitProbe(p); probe.sample(0)
        report = probe.analyze({}, budget=10)
        node = report['nodes'][0]
        self.assertEqual(node['need'], 1)
        self.assertIsNone(node['potential'])
        self.assertIsNone(node['priority'])
        self.assertIn('reachability_unknown', node['blockers'])
        self.assertEqual(report['proposals'], [])

    def test_estimated_priority_and_budget_are_not_actual_current(self):
        p = pin(); probe = CircuitProbe(p); probe.sample(0)
        report = probe.analyze({'root': estimate(cost=2, impact=.8)}, budget=2)
        node = report['nodes'][0]
        self.assertEqual(node['potential'], .8)
        self.assertEqual(node['priority'], .4)
        self.assertEqual(node['total_effort'], 0)
        self.assertIsNone(node['effort_rate'])
        self.assertEqual(report['proposed_cost'], 2)
        self.assertFalse(report['execution_authorized'])
        self.assertEqual(probe.analyze({'root': estimate(2)}, budget=1)['proposals'], [])

    def test_scope_geometry_height_not_used_as_voltage(self):
        p = pin()
        absent, present = p.lift('root', factor='a', absent_expected=True, present_expected=True, expected_revision=0)
        probe = CircuitProbe(p); probe.sample(0)
        estimates = {present: estimate()}
        before = next(n for n in probe.analyze(estimates, budget=1)['nodes'] if n['rule_id'] == present)
        p.lift(absent, factor='b', absent_expected=True, present_expected=False, expected_revision=1)
        probe.sample(1)
        after = next(n for n in probe.analyze(estimates, budget=1)['nodes'] if n['rule_id'] == present)
        self.assertNotEqual(before['structural_height'], after['structural_height'])
        self.assertEqual(before['potential'], after['potential'])
        self.assertEqual(before['priority'], after['priority'])

    def test_coverage_decreases_without_claiming_proof(self):
        p = pin(); probe = CircuitProbe(p); probe.sample(0)
        add(p, 'a'); probe.sample(1, efforts=[effort('a-test', ['a'])])
        middle = probe.analyze({'root': estimate()}, budget=1)['nodes'][0]
        self.assertEqual(middle['need'], .5)
        self.assertIn('declared_need_decreased', middle['diagnostics'])
        add(p, 'b'); probe.sample(2, efforts=[effort('b-test', ['b'])])
        report = probe.analyze({'root': estimate()}, budget=1)
        self.assertEqual(report['nodes'][0]['need'], 0)
        self.assertEqual(report['proposals'], [])
        self.assertFalse(report['execution_authorized'])

    def test_recirculated_evidence_is_not_a_new_observation(self):
        p = pin(); add(p, 'a', False)
        probe = CircuitProbe(p); probe.sample(0)
        for route in range(4):
            add(p, 'a', False, route=f'view:{route}')
        probe.sample(2, efforts=[effort('replay', ['a'], units=3)])
        node = probe.analyze({'root': estimate()}, budget=1)['nodes'][0]
        self.assertEqual(node['new_observation_count'], 0)
        self.assertEqual(node['effort_rate'], 1.5)
        self.assertIn('effort_without_new_observation', node['diagnostics'])

    def test_repeated_context_flags_only_with_unresolved_need_and_effort(self):
        p = pin(); add(p, 'a', False)
        probe = CircuitProbe(p); probe.sample(0)
        add(p, 'b', False); probe.sample(1, efforts=[effort('repeat', ['b'])])
        node = probe.analyze({'root': estimate()}, budget=1)['nodes'][0]
        self.assertEqual(node['new_observation_count'], 1)
        self.assertEqual(node['novel_signature_count'], 0)
        self.assertIn('repeated_context_still_unresolved', node['diagnostics'])
        add(p, 'c', False, bits={'a': False, 'b': False})
        probe.sample(2, efforts=[effort('new-context', ['c'])])
        node = probe.analyze({'root': estimate()}, budget=1)['nodes'][0]
        self.assertEqual(node['novel_signature_count'], 1)
        self.assertNotIn('repeated_context_still_unresolved', node['diagnostics'])

    def test_repeated_effort_receipts_are_idempotent(self):
        p = pin(); add(p, 'a', False); probe = CircuitProbe(p); probe.sample(0)
        receipt = effort('once', ['a'], 2)
        probe.sample(1, efforts=[receipt, receipt])
        probe.sample(2, efforts=[receipt])
        node = probe.analyze({'root': estimate()}, budget=1)['nodes'][0]
        self.assertEqual(node['attempt_count'], 1)
        self.assertEqual(node['total_effort'], 2)
        self.assertEqual(node['diagnostics'], [])

    def test_effort_validation_is_atomic(self):
        p = pin(); add(p, 'a'); probe = CircuitProbe(p); probe.sample(0)
        initial = probe.analyze({}, budget=0)
        for receipt in [effort('x', ['missing']), effort('x', ['a'], -1),
                        effort('x', ['a'], True), effort('x', ['a'], revision=True),
                        effort('x', ['a'], rule='missing')]:
            with self.assertRaises(ValueError):
                probe.sample(1, efforts=[effort('valid', ['a']), receipt])
            self.assertEqual(probe.analyze({}, budget=0), initial)

    def test_conflicting_duplicate_cannot_bypass_type_validation(self):
        p = pin(); add(p, 'a'); probe = CircuitProbe(p)
        probe.sample(0, efforts=[effort('x', ['a'], 1)])
        with self.assertRaises(ValueError):
            probe.sample(1, efforts=[effort('x', ['a'], True)])

    def test_unreachable_unknown_zero_and_invalid_costs(self):
        p = pin(); probe = CircuitProbe(p); probe.sample(0)
        for e in [estimate(reachable=False), estimate(reachable=None), estimate(cost=None),
                  estimate(impact=None), estimate(impact=0)]:
            self.assertEqual(probe.analyze({'root': e}, budget=10)['proposals'], [])
        for e in [estimate(cost=0), estimate(cost=-1), estimate(cost=float('inf')),
                  estimate(impact=True), estimate(impact=2), estimate(reachable=1)]:
            with self.assertRaises(ValueError):
                probe.analyze({'root': e}, budget=10)

    def test_greedy_budget_and_parent_exclusion(self):
        p = pin()
        absent, present = p.lift('root', factor='a', absent_expected=True, present_expected=True, expected_revision=0)
        probe = CircuitProbe(p); probe.sample(0)
        estimates = {'root': estimate(.1), absent: estimate(3, .9), present: estimate(1, .8)}
        report = probe.analyze(estimates, budget=3)
        self.assertEqual([r['rule_id'] for r in report['proposals']], [present])
        self.assertEqual(report['remaining_budget'], 2)
        self.assertIn('historical_parent', report['nodes'][0]['blockers'])

    def test_detail_retains_unknown_bits_and_route_angles(self):
        p = pin(); add(p, 'a', bits={'a': False}); probe = CircuitProbe(p); probe.sample(0)
        detail = probe.detail('root')
        self.assertEqual(detail['bit_bundles'][0]['bands'][1]['state'], 'unknown')
        self.assertEqual(len(detail['arrivals']['a'][0]['direction']), 3)
        detail['trials'][0]['outcome'] = False
        self.assertTrue(probe.detail('root')['trials'][0]['outcome'])

    def test_frequency_uses_sample_steps_not_colour_or_angle(self):
        p = pin(); probe = CircuitProbe(p); probe.sample(0)
        add(p, 'a'); probe.sample(2)
        node = probe.analyze({'root': estimate()}, budget=1)['nodes'][0]
        self.assertIsNone(node['frequency_hz'])
        self.assertEqual(node['need_changes_per_step'], .5)

    def test_stale_sample_capacity_and_clock_bounds(self):
        p = pin(); probe = CircuitProbe(p, max_samples=1); probe.sample(0)
        with self.assertRaises(ValueError):
            probe.sample(1)
        add(p, 'a')
        with self.assertRaises(ValueError):
            probe.analyze({}, budget=0)
        p = pin(); probe = CircuitProbe(p); probe.sample(2)
        for step in [1, 2, True, -1]:
            with self.assertRaises(ValueError):
                probe.sample(step)

    def test_analysis_and_detail_never_mutate_pin(self):
        p = pin(); add(p, 'a'); before = p.snapshot()
        probe = CircuitProbe(p); probe.sample(0)
        probe.analyze({'root': estimate()}, budget=1); probe.detail('root')
        self.assertEqual(p.snapshot(), before)

    def test_lost_or_changed_trials_are_not_silently_accepted(self):
        for change in ['remove', 'alter']:
            p = pin(); add(p, 'a'); probe = CircuitProbe(p); probe.sample(0)
            if change == 'remove':
                p._trials.pop('a')  # Simulate an upstream storage bug.
            else:
                p._trials['a']['outcome'] = False
            with self.assertRaises(ValueError):
                probe.sample(1)

    def test_empty_result_effort_and_effort_capacity(self):
        p = pin(); probe = CircuitProbe(p, max_attempts=1); probe.sample(0)
        probe.sample(1, efforts=[effort('no-result', [], 2)])
        node = probe.analyze({'root': estimate()}, budget=1)['nodes'][0]
        self.assertIn('effort_without_new_observation', node['diagnostics'])
        before = probe.analyze({}, budget=0)
        with self.assertRaises(ValueError):
            probe.sample(2, efforts=[effort('second', [], 1)])
        self.assertEqual(probe.analyze({}, budget=0), before)

    def test_unknown_branch_context_is_still_a_new_observation(self):
        p = pin()
        absent, _ = p.lift('root', factor='a', absent_expected=False, present_expected=True, expected_revision=0)
        probe = CircuitProbe(p); probe.sample(0)
        add(p, 'unknown', bits={'b': False})
        probe.sample(1, efforts=[effort('unknown-context', ['unknown'], rule=absent, revision=1)])
        node = next(n for n in probe.analyze({absent: estimate()}, budget=1)['nodes'] if n['rule_id'] == absent)
        self.assertEqual(node['new_observation_count'], 1)
        self.assertEqual(node['trial_ids'], [])
        self.assertNotIn('effort_without_new_observation', node['diagnostics'])

    def test_demo_replay_repeat_and_new_context(self):
        from demo_circuit_analysis import run
        result = run()
        self.assertTrue(result['pin_unchanged_by_analysis'])
        active = [[n for n in s['report']['nodes'] if n['rule_id'] == 'r1:1'][0] for s in result['stages']]
        self.assertIn('effort_without_new_observation', active[1]['diagnostics'])
        self.assertIn('repeated_context_still_unresolved', active[2]['diagnostics'])
        self.assertEqual(active[3]['novel_signature_count'], 1)


if __name__ == '__main__':
    unittest.main()
