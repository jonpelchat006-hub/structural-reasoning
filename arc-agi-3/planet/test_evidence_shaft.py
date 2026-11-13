from copy import deepcopy
import unittest

from evidence_pin import EvidencePin
from external_eye_circuit import ExternalEyeCircuit


def make_pin(**overrides):
    return EvidencePin('wall-motion', **{**dict(scope='toy/L1', subject='pixel:3,4',
                       action=1, question='Does this wall move after pressing?',
                       factors={'contact': 'cyan', 'blue_wall': 'orange'}, expected=True), **overrides})


def record(pin, name, contact=True, outcome=True, **overrides):
    return pin.record(name, **{**dict(scope='toy/L1', action=1, bits={'contact': contact},
                      outcome=outcome, observation={'before': {'contact': contact}, 'after': {'moved': outcome}},
                      route='view:0', direction=[1, 0, 1]), **overrides})


def proposals(circuit, actions=(1, 1, 1, 1)):
    return [{k: v[k] for k in ('route', 'scope', 'version', 'observation_id')} | {'action': action}
            for v, action in zip(circuit.views(), actions)]


class EvidenceShaftTests(unittest.TestCase):
    def test_persistent_empty_slot(self):
        pin = make_pin()
        state = pin.snapshot()
        self.assertTrue(state['persistent'])
        self.assertEqual(state['bands'][0]['status'], 'unknown')
        self.assertEqual(state['gaps'][0]['kind'], 'untested_case')
        self.assertFalse(state['gaps'][0]['execution_ready'])
        self.assertEqual(pin.predict({'contact': True})['status'], 'abstain')

    def test_unknown_is_not_no_and_colour_is_not_truth(self):
        pin = make_pin()
        record(pin, 'a', contact=False, outcome=False)
        state = pin.snapshot()
        bands = state['bit_bundles'][0]['bands']
        self.assertEqual([b['state'] for b in bands], ['no', 'unknown'])
        self.assertEqual(bands[0]['colour'], 'cyan')
        self.assertEqual(state['bands'][0]['status'], 'no')
        self.assertEqual(state['bands'][0]['counterexample_ids'], ['a'])

    def test_fanout_and_angles_do_not_multiply_evidence(self):
        pin = make_pin()
        self.assertTrue(record(pin, 'a'))
        for i in range(4):
            self.assertFalse(record(pin, 'a', route=f'view:{i}', direction=[i+1, 0, 1]))
        self.assertEqual(pin.snapshot()['trial_count'], 1)
        self.assertGreater(len(pin.snapshot()['arrivals']['a']), 1)
        self.assertEqual(pin.snapshot()['bands'][0]['trial_ids'], ['a'])

    def test_duplicate_conflict_is_atomic(self):
        pin = make_pin()
        record(pin, 'a')
        previous = pin.snapshot()
        with self.assertRaises(ValueError):
            record(pin, 'a', outcome=False)
        self.assertEqual(previous, pin.snapshot())

    def test_raw_boolean_and_number_are_not_interchangeable_evidence(self):
        pin = make_pin()
        record(pin, 'a', observation={'before': {'value': True}, 'after': {}})
        before = pin.snapshot()
        with self.assertRaises(ValueError):
            record(pin, 'a', observation={'before': {'value': 1}, 'after': {}})
        self.assertEqual(pin.snapshot(), before)

    def test_refinement_preserves_counterexample_parent_and_raw_trials(self):
        pin = make_pin()
        record(pin, 'a')
        record(pin, 'b', contact=False, outcome=False)
        before = pin.snapshot()
        self.assertEqual(before['bands'][0]['status'], 'conflicting')
        self.assertEqual(before['gaps'][0]['kind'], 'unexplained_observation')
        self.assertEqual(pin.predict({'contact': True})['status'], 'abstain')
        absent, present = pin.lift('root', factor='contact', absent_expected=False,
                                   present_expected=True, expected_revision=0)
        after = pin.snapshot()
        self.assertEqual(before['trials'], after['trials'])
        self.assertEqual(after['bands'][0]['counterexample_ids'], ['b'])
        self.assertEqual(after['bands'][0]['height'], 1)
        self.assertTrue(after['bands'][0]['historical_parent'])
        self.assertEqual(after['refinements'][0]['previous_rule']['children'], [])
        self.assertEqual(pin.predict({'contact': False})['rule_id'], absent)
        self.assertEqual(pin.predict({'contact': True})['rule_id'], present)
        self.assertFalse(pin.predict({'contact': True})['execution_authorized'])

    def test_unobserved_branch_is_a_question_not_an_answer(self):
        pin = make_pin()
        record(pin, 'a')
        absent, present = pin.lift('root', factor='contact', absent_expected=False,
                                   present_expected=True, expected_revision=0)
        state = pin.snapshot()
        self.assertEqual(state['gaps'][0]['rule_id'], absent)
        self.assertEqual(state['gaps'][0]['conditions'], {'contact': False})
        self.assertEqual(state['gaps'][0]['subject'], 'pixel:3,4')
        self.assertIsNone(pin.predict({'contact': False})['outcome'])
        self.assertIsNone(pin.predict({})['outcome'])

    def test_missing_context_does_not_get_guessed_into_branches(self):
        pin = make_pin()
        record(pin, 'a', bits={})
        pin.lift('root', factor='contact', absent_expected=False,
                 present_expected=True, expected_revision=0)
        for band in pin.snapshot()['bands'][1:]:
            self.assertEqual(band['trial_ids'], [])
            self.assertEqual(band['unknown_context_ids'], ['a'])
        self.assertEqual(sum(g['kind'] == 'missing_context' for g in pin.snapshot()['gaps']), 2)

    def test_nested_insertion_keeps_ids_and_partitions(self):
        pin = make_pin()
        record(pin, 'a', bits={'contact': True, 'blue_wall': True})
        record(pin, 'b', contact=False, outcome=False, bits={'contact': False, 'blue_wall': True})
        absent, present = pin.lift('root', factor='contact', absent_expected=False,
                                   present_expected=True, expected_revision=0)
        pin.lift(present, factor='blue_wall', absent_expected=None,
                 present_expected=True, expected_revision=1)
        bands = {b['id']: b for b in pin.snapshot()['bands']}
        self.assertEqual(bands['root']['height'], 2)
        self.assertEqual(bands[absent]['trial_ids'], ['b'])
        self.assertEqual(bands[present]['trial_ids'], ['a'])
        self.assertEqual(bands['r2:1']['trial_ids'], ['a'])

    def test_new_counterexample_reopens_gap_without_erasing_branch(self):
        pin = make_pin()
        record(pin, 'a')
        record(pin, 'b', contact=False, outcome=False)
        _, present = pin.lift('root', factor='contact', absent_expected=False,
                               present_expected=True, expected_revision=0)
        self.assertEqual(pin.snapshot()['gaps'], [])
        record(pin, 'c', outcome=False)
        self.assertEqual(pin.snapshot()['gaps'][0]['rule_id'], present)
        self.assertEqual(pin.snapshot()['gaps'][0]['kind'], 'unexplained_observation')
        self.assertIsNone(pin.predict({'contact': True})['outcome'])
        self.assertEqual(pin.snapshot()['trial_count'], 3)

    def test_observations_without_hypothesis_leave_relationship_gap(self):
        pin = make_pin(expected=None)
        record(pin, 'a')
        self.assertEqual(pin.snapshot()['gaps'][0]['kind'], 'unmodelled_relationship')

    def test_rejected_refinements_leave_no_changes(self):
        pin = make_pin(max_rules=3)
        pin.lift('root', factor='contact', absent_expected=False, present_expected=True, expected_revision=0)
        before = pin.snapshot()
        for rule, factor, version in [('root', 'blue_wall', 1), ('r1:0', 'contact', 1),
                                     ('r1:0', 'blue_wall', 0), ('r1:0', 'blue_wall', 1)]:
            with self.assertRaises(ValueError):
                pin.lift(rule, factor=factor, absent_expected=False, present_expected=True, expected_revision=version)
            self.assertEqual(pin.snapshot(), before)

    def test_record_validation_and_budgets_preserve_trials(self):
        pin = make_pin(max_trials=1)
        for override in [dict(scope='other'), dict(action=True), dict(outcome=1),
                         dict(bits={'contact': 1}), dict(bits={'invented': True}),
                         dict(direction=[0, 0, 0]), dict(direction=[float('nan'), 1, 0]),
                         dict(observation={'after': {}})]:
            with self.assertRaises(ValueError):
                record(pin, 'a', **override)
        self.assertEqual(pin.snapshot()['trial_count'], 0)
        record(pin, 'a')
        with self.assertRaises(ValueError):
            record(pin, 'b')
        self.assertFalse(record(pin, 'a'))
        self.assertEqual(pin.snapshot()['trial_count'], 1)

    def test_input_and_snapshot_copies(self):
        pin = make_pin()
        observation = {'before': {'value': 1}, 'after': {'value': 2}}
        record(pin, 'a', observation=observation)
        observation['before']['value'] = 99
        state = pin.snapshot()
        state['trials'][0]['observation']['before']['value'] = 88
        state['bands'][0]['expected'] = False
        self.assertEqual(pin.snapshot()['trials'][0]['observation']['before']['value'], 1)
        self.assertTrue(pin.snapshot()['bands'][0]['expected'])


class ExternalCircuitTests(unittest.TestCase):
    def setUp(self):
        self.calls = []
        def send(request):
            self.calls.append(deepcopy(request))
            return {**request, 'observation': {'moved': True}}
        self.circuit = ExternalEyeCircuit('toy/L1', {'moved': False}, send, budget=2)

    def test_external_port_two_four_topology_and_copies(self):
        layout = self.circuit.layout()
        self.assertGreater(layout['positions']['port'][2], layout['outer_bounds'][1][2])
        views = self.circuit.views()
        self.assertEqual(len(views), 4)
        self.assertEqual(len({v['path'][1] for v in views}), 2)
        self.assertEqual(len({v['path'][2] for v in views}), 4)
        self.assertEqual(len({v['observation_id'] for v in views}), 1)
        views[0]['observation']['moved'] = True
        self.assertFalse(views[1]['observation']['moved'])
        self.assertFalse(self.circuit.views()[0]['observation']['moved'])

    def test_single_game_exchange_then_stale_returns_rejected(self):
        replies = proposals(self.circuit)
        result = self.circuit.act(replies, available_actions=[1])
        self.assertEqual(result['status'], 'returned')
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(result['state']['remaining'], 1)
        self.assertEqual(result['state']['outstanding'], 0)
        self.assertEqual(result['state']['events'][0]['request_id'], result['state']['events'][1]['request_id'])
        self.assertNotEqual(self.circuit.views()[0]['observation_id'], replies[0]['observation_id'])
        with self.assertRaises(ValueError):
            self.circuit.act(replies, available_actions=[1])
        self.assertEqual(len(self.calls), 1)

    def test_abstentions_and_conflicts_do_not_dispatch(self):
        for actions, status in [((None,)*4, 'all_abstained'), ((1, 2, 1, None), 'conflicting_proposals')]:
            result = self.circuit.act(proposals(self.circuit, actions), available_actions=[1, 2])
            self.assertEqual(result['status'], status)
            self.assertFalse(result['dispatched'])
        self.assertEqual(self.calls, [])
        self.assertEqual(self.circuit.snapshot()['remaining'], 2)
        self.assertTrue(self.circuit.act(proposals(self.circuit, (1, None, None, None)), available_actions=[1])['dispatched'])

    def test_illegal_action_wrong_scope_duplicate_and_forged_returns(self):
        for key, value in [('scope', 'wrong'), ('observation_id', 'forged'),
                           ('version', True), ('action', True), ('route', 'view:1')]:
            replies = proposals(self.circuit)
            replies[0][key] = value
            with self.assertRaises(ValueError):
                self.circuit.act(replies, available_actions=[1])
        with self.assertRaises(ValueError):
            self.circuit.act(proposals(self.circuit)[:3], available_actions=[1])
        with self.assertRaises(ValueError):
            self.circuit.act(proposals(self.circuit, (2,)*4), available_actions=[1])
        self.assertEqual(self.calls, [])

    def test_uncertain_transport_blocks_fanout_and_retry(self):
        calls = []
        def send(request):
            calls.append(request)
            raise TimeoutError()
        circuit = ExternalEyeCircuit('toy/L1', {}, send)
        replies = proposals(circuit)
        self.assertEqual(circuit.act(replies, available_actions=[1])['status'], 'unresolved')
        with self.assertRaises(ValueError):
            circuit.views()
        with self.assertRaises(ValueError):
            circuit.act(replies, available_actions=[1])
        self.assertEqual(len(calls), 1)

    def test_same_scope_new_session_has_distinct_provenance(self):
        second = ExternalEyeCircuit('toy/L1', {}, lambda r: r)
        self.assertNotEqual(second.views()[0]['observation_id'], self.circuit.views()[0]['observation_id'])

    def test_four_views_fill_one_evidence_bundle(self):
        pin = make_pin()
        before = self.circuit.views()[0]['observation']
        self.circuit.act(proposals(self.circuit), available_actions=[1])
        for view in self.circuit.views():
            record(pin, view['observation_id'], route=view['route'], direction=view['direction'],
                   observation={'before': before, 'after': view['observation']})
        self.assertEqual(pin.snapshot()['trial_count'], 1)
        self.assertEqual(len(pin.snapshot()['arrivals'][self.circuit.views()[0]['observation_id']]), 4)


class DemonstrationTests(unittest.TestCase):
    def test_two_refinements_and_held_out_predictions(self):
        from demo_evidence_shaft import run
        result = run()
        self.assertEqual(result['held_out_correct'], 4)
        self.assertEqual(result['held_out_abstained'], 0)
        self.assertTrue(result['original_trials_preserved_at_second_lift'])
        self.assertEqual(result['game_dispatches'], 7)
        self.assertEqual(result['unique_trials'], 7)
        self.assertEqual(result['arrival_receipts'], 28)
        self.assertEqual(result['outstanding'], 0)
        self.assertEqual(result['remaining'], 0)
        self.assertFalse(result['discovery'][2]['matched'])
        self.assertTrue(any(g['kind'] == 'unexplained_observation'
                            for g in result['stages'][3]['gaps']))


if __name__ == '__main__':
    unittest.main()
