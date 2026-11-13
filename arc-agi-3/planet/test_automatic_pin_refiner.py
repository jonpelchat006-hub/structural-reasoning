from copy import deepcopy
from itertools import product
import unittest

from automatic_pin_refiner import AutomaticPinRefiner
from evidence_pin import EvidencePin


def make_pin(**kwargs):
    return EvidencePin('p', scope='g/L1', subject='wall', action=1, question='Does it move?',
                       factors={'a': 'cyan', 'b': 'orange'}, **kwargs)


def add(pin, name, bits, outcome, **kwargs):
    return pin.record(name, scope='g/L1', action=1, bits=bits, outcome=outcome,
                      observation={'before': deepcopy(bits), 'after': {'moved': outcome}},
                      **{'route': 'view:0', 'direction': [0, 0, 1], **kwargs})


def cohorts(pin, function=lambda a, b: a, *, prefix='', correlated=False):
    fit, check = [], []
    for role, ids in [('fit', fit), ('check', check)]:
        for i, (a, b) in enumerate(product((False, True), repeat=2)):
            if correlated:
                b = a
            name = f'{prefix}{role}{i}'
            add(pin, name, {'a': a, 'b': b}, function(a, b))
            ids.append(name)
    return fit, check


class RefinerTests(unittest.TestCase):
    def setUp(self):
        self.learner = AutomaticPinRefiner()

    def test_learns_split_and_boolean_outputs_without_supplied_predictions(self):
        pin = make_pin()
        fit, check = cohorts(pin, lambda a, b: not a)
        before = pin.snapshot()
        proposal = self.learner.inspect(pin, fit_ids=fit, check_ids=check)
        self.assertEqual(pin.snapshot(), before)
        self.assertEqual(proposal['selected'], dict(rule_id='root', factor='a',
                                                  absent_expected=True, present_expected=False))
        result = self.learner.apply(pin, proposal)
        self.assertTrue(result['changed'])
        self.assertEqual(pin.snapshot()['trials'], before['trials'])
        self.assertTrue(pin.predict({'a': False})['outcome'])
        self.assertFalse(pin.predict({'a': True})['outcome'])
        self.assertFalse(result['execution_authorized'])

    def test_empty_uniform_and_unsupported_xor_abstain(self):
        for function in [None, lambda a, b: True, lambda a, b: a != b]:
            pin = make_pin()
            fit, check = ([], []) if function is None else cohorts(pin, function)
            before = pin.snapshot()
            result = self.learner.step(pin, fit_ids=fit, check_ids=check)
            self.assertFalse(result['changed'])
            self.assertEqual(pin.snapshot(), before)
            self.assertTrue(result['proposal']['reports'][0]['questions'])

    def test_correlated_hypotheses_abstain_and_request_disagreement_cases(self):
        pin = make_pin()
        fit, check = cohorts(pin, correlated=True)
        proposal = self.learner.inspect(pin, fit_ids=fit, check_ids=check)
        report = proposal['reports'][0]
        self.assertEqual(report['status'], 'ambiguous_fit')
        self.assertIsNone(proposal['selected'])
        question = report['questions'][0]
        self.assertEqual(question['kind'], 'distinguish_hypotheses')
        self.assertFalse(question['execution_ready'])
        for case in question['cases']:
            self.assertNotEqual(case['bits']['a'], case['bits']['b'])
            self.assertNotEqual(case['predictions']['a'], case['predictions']['b'])

    def test_checking_data_cannot_break_a_fitting_tie(self):
        pin = make_pin()
        fit, _ = cohorts(pin, correlated=True)
        check = []
        for i, (a, b) in enumerate(product((False, True), repeat=2)):
            name = f'new-check{i}'
            add(pin, name, {'a': a, 'b': b}, a)
            check.append(name)
        result = self.learner.inspect(pin, fit_ids=fit, check_ids=check)
        self.assertEqual(result['reports'][0]['status'], 'ambiguous_fit')

    def test_failed_check_does_not_install_or_fallback_to_another_feature(self):
        pin = make_pin()
        fit, _ = cohorts(pin)
        check = []
        for i, (a, b) in enumerate(product((False, True), repeat=2)):
            name = f'bad-check{i}'
            add(pin, name, {'a': a, 'b': b}, b)
            check.append(name)
        before = pin.snapshot()
        result = self.learner.step(pin, fit_ids=fit, check_ids=check)
        self.assertEqual(result['proposal']['reports'][0]['status'], 'check_failed')
        self.assertFalse(result['changed'])
        self.assertEqual(pin.snapshot(), before)

    def test_both_branches_need_disjoint_check_support(self):
        pin = make_pin()
        fit, check = cohorts(pin)
        for subset in [[], check[:2], check[:3]]:
            proposal = self.learner.inspect(pin, fit_ids=fit, check_ids=subset)
            self.assertEqual(proposal['reports'][0]['status'], 'insufficient_check_support')
            self.assertIsNone(proposal['selected'])

    def test_missing_feature_is_not_false(self):
        pin = make_pin()
        fit, check = cohorts(pin)
        add(pin, 'missing', {'b': False}, False)
        for left, right, expected in [(fit+['missing'], check, 'no_supported_split'),
                                      (fit, check+['missing'], 'insufficient_check_support')]:
            result = self.learner.inspect(pin, fit_ids=left, check_ids=right)
            self.assertEqual(result['reports'][0]['status'], expected)

    def test_retained_unassigned_counterexample_vetoes_refinement(self):
        pin = make_pin()
        fit, check = cohorts(pin)
        add(pin, 'unassigned-counterexample', {'a': True, 'b': False}, False)
        proposal = self.learner.inspect(pin, fit_ids=fit, check_ids=check)
        self.assertEqual(proposal['reports'][0]['status'], 'unresolved_retained_evidence')
        self.assertIsNone(proposal['selected'])

    def test_retained_missing_context_cannot_be_hidden_by_a_split(self):
        pin = make_pin()
        fit, check = cohorts(pin)
        add(pin, 'unassigned-unknown', {}, True)
        proposal = self.learner.inspect(pin, fit_ids=fit, check_ids=check)
        self.assertEqual(proposal['reports'][0]['status'], 'unresolved_retained_evidence')

    def test_missing_parent_context_blocks_child_refinement(self):
        pin = make_pin()
        fit, check = cohorts(pin)
        pin.lift('root', factor='a', absent_expected=False, present_expected=True, expected_revision=0)
        add(pin, 'unknown-parent', {'b': False}, True)
        proposal = self.learner.inspect(pin, fit_ids=fit+['unknown-parent'], check_ids=check)
        self.assertIsNone(proposal['selected'])
        self.assertTrue(all(r['status'] == 'missing_parent_context' for r in proposal['reports']))
        self.assertTrue(all(r['questions'][0]['observation_ids'] == ['unknown-parent']
                            for r in proposal['reports']))

    def test_duplicate_view_deliveries_do_not_fill_quotas(self):
        pin = make_pin()
        for name, bit in [('f0', False), ('f1', True), ('c0', False), ('c1', True)]:
            for route in range(4):
                add(pin, name, {'a': bit, 'b': True}, bit, route=f'view:{route}')
        proposal = self.learner.inspect(pin, fit_ids=['f0', 'f1'], check_ids=['c0', 'c1'])
        self.assertEqual(pin.snapshot()['trial_count'], 4)
        self.assertIsNone(proposal['selected'])
        self.assertEqual(proposal['reports'][0]['candidates'][0]['status'], 'insufficient_fit_support')

    def test_invalid_cohort_ids_and_overlap_rejected(self):
        pin = make_pin()
        fit, check = cohorts(pin)
        for left, right in [(fit, fit), (fit+[fit[0]], check), (fit+['invented'], check),
                             ('not-list', check), ([True], check)]:
            with self.assertRaises(ValueError):
                self.learner.inspect(pin, fit_ids=left, check_ids=right)

    def test_evidence_changes_invalidate_proposals(self):
        pin = make_pin()
        fit, check = cohorts(pin)
        proposal = self.learner.inspect(pin, fit_ids=fit, check_ids=check)
        add(pin, 'new', {'a': True, 'b': True}, True)
        with self.assertRaises(ValueError):
            self.learner.apply(pin, proposal)
        self.assertEqual(pin.snapshot()['revision'], 0)

    def test_arrival_metadata_does_not_invalidate_evidence(self):
        pin = make_pin()
        fit, check = cohorts(pin)
        proposal = self.learner.inspect(pin, fit_ids=fit, check_ids=check)
        add(pin, 'fit0', {'a': False, 'b': False}, False, route='view:3')
        self.assertTrue(self.learner.apply(pin, proposal)['changed'])

    def test_mutation_wrong_pin_policy_and_replayed_proposals_rejected(self):
        pin = make_pin()
        fit, check = cohorts(pin)
        proposal = self.learner.inspect(pin, fit_ids=fit, check_ids=check)
        altered = deepcopy(proposal)
        altered['selected']['present_expected'] = False
        with self.assertRaises(ValueError):
            self.learner.apply(pin, altered)
        with self.assertRaises(ValueError):
            AutomaticPinRefiner(minimum_fit=1).apply(pin, proposal)
        other = EvidencePin('different', scope='g/L1', subject='wall', action=1,
                            question='Does it move?', factors={'a': 'cyan', 'b': 'orange'})
        cohorts(other)
        with self.assertRaises(ValueError):
            self.learner.apply(other, proposal)
        self.learner.apply(pin, proposal)
        with self.assertRaises(ValueError):
            self.learner.apply(pin, proposal)

    def test_rule_budget_failure_is_atomic(self):
        pin = make_pin(max_rules=1)
        fit, check = cohorts(pin)
        before = pin.snapshot()
        with self.assertRaises(ValueError):
            self.learner.step(pin, fit_ids=fit, check_ids=check)
        self.assertEqual(pin.snapshot(), before)

    def test_configuration_validation(self):
        for value in [True, 0, -1, 1.5]:
            with self.assertRaises(ValueError):
                AutomaticPinRefiner(minimum_check=value)

    def test_observed_disagreement_resolves_ambiguity_with_new_fit_evidence(self):
        pin = make_pin()
        fit, check = cohorts(pin, correlated=True)
        self.assertEqual(self.learner.inspect(pin, fit_ids=fit, check_ids=check)['status'], 'abstain')
        for i in range(2):
            name = f'contrast{i}'
            add(pin, name, {'a': True, 'b': False}, True)
            fit.append(name)
        result = self.learner.step(pin, fit_ids=fit, check_ids=check)
        self.assertTrue(result['changed'])
        self.assertEqual(result['proposal']['selected']['factor'], 'a')

    def test_names_and_colours_do_not_determine_the_split(self):
        pin = EvidencePin('renamed', scope='g/L1', subject='wall', action=1, question='Does it move?',
                          factors={'z_signal': 'orange', 'a_decoy': 'cyan'})
        fit, check = [], []
        for role, ids in [('fit', fit), ('check', check)]:
            for i, (a, b) in enumerate(product((False, True), repeat=2)):
                name = f'{role}{i}'
                add(pin, name, {'z_signal': a, 'a_decoy': b}, a)
                ids.append(name)
        result = self.learner.step(pin, fit_ids=fit, check_ids=check)
        self.assertEqual(result['proposal']['selected']['factor'], 'z_signal')

    def test_all_two_bit_truth_tables_expose_one_step_search_limit(self):
        combinations = list(product((False, True), repeat=2))
        ready = []
        for mask in range(16):
            pin = make_pin()
            fit, check = cohorts(pin, lambda a, b: bool(mask & (1 << combinations.index((a, b)))))
            result = self.learner.step(pin, fit_ids=fit, check_ids=check)
            if result['changed']:
                ready.append(mask)
                for a, b in combinations:
                    expected = bool(mask & (1 << combinations.index((a, b))))
                    self.assertEqual(pin.predict({'a': a, 'b': b})['outcome'], expected)
        # a, not-a, b, not-b. Constants are not installed; AND/OR/XOR need
        # deeper simultaneous search when all contexts arrive before learning.
        self.assertEqual(ready, [3, 5, 10, 12])


class AutomaticDemoTests(unittest.TestCase):
    def test_two_automatic_lifts_and_frozen_evaluation(self):
        from demo_automatic_pin_learning import run
        result = run()
        self.assertEqual([r['choice']['factor'] for r in result['learning']], ['contact', 'blue_wall'])
        self.assertTrue(all(r['evidence_preserved'] for r in result['learning']))
        self.assertEqual(result['correct'], 8)
        self.assertEqual(result['abstained'], 0)
        self.assertTrue(result['evaluation_did_not_change_model_or_evidence'])
        self.assertEqual(result['stored_trials'], 12)
        self.assertEqual(result['stored_view_receipts'], 48)
        self.assertEqual(result['game_calls'], 20)
        self.assertEqual(result['outstanding'], 0)


if __name__ == '__main__':
    unittest.main()
