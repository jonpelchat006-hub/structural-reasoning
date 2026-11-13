from copy import deepcopy
from dataclasses import replace
import unittest

from reaction_resonance import ResonanceReactor, condition_pin, rows_checked, POLICIES


def rows(start, count=32, *, invert=False, scope='game'):
    return [dict(event_id=f'event-{i}', scope=scope, step=i,
                 features={'signal': bool(i%2), 'decoy': bool((i//2)%2)},
                 outcome=bool(i%2) != invert) for i in range(start, start+count)]


class ResonanceTests(unittest.TestCase):
    def setUp(self):
        self.reactor = ResonanceReactor()
        self.pins = [condition_pin('signal', 'game', 'action.1', wavelength=530),
                     condition_pin('decoy', 'game', 'action.1', wavelength=650)]

    def propose(self, fit=None, pins=None, **kwargs):
        return self.reactor.propose(self.pins if pins is None else pins, rows(0) if fit is None else fit,
                                    scope='game', target='action.1', **kwargs)

    def test_useful_complementary_condition_reacts_despite_different_colour(self):
        proposal = self.propose()
        self.assertEqual(proposal['selected']['feature'], 'signal')
        verified = self.reactor.verify(proposal, rows(32))
        self.assertTrue(verified['accepted'])
        self.assertFalse(verified['execution_authorized'])
        result = self.reactor.evaluate(verified, rows(64))
        self.assertEqual(result['accuracy'], 1)
        self.assertLess(result['test_brier'], result['baseline_test_brier'])

    def test_colour_coincidence_is_not_predictive_support(self):
        proposal = self.propose(policy='colour_only')
        self.assertEqual(proposal['selected']['feature'], 'decoy')
        verified = self.reactor.verify(proposal, rows(32))
        self.assertFalse(verified['accepted'])

    def test_recoding_changes_display_not_three_channel_choice(self):
        recoded = [condition_pin('signal', 'game', 'action.1', wavelength=780, orientation=270),
                   condition_pin('decoy', 'game', 'action.1', wavelength=380, orientation=90)]
        self.assertEqual(self.propose()['selected']['model'], self.propose(pins=recoded)['selected']['model'])

    def test_duplicates_do_not_amplify_support(self):
        evidence = rows(0)
        self.assertEqual(self.propose(evidence), self.propose(evidence + deepcopy(evidence)))
        wrong = deepcopy(evidence[0]); wrong['outcome'] = not wrong['outcome']
        with self.assertRaises(ValueError): rows_checked(evidence + [wrong])

    def test_no_contrast_is_not_a_new_reaction(self):
        evidence = rows(0)
        for row in evidence: row['features'] = {'signal': True}
        proposal = self.propose(evidence)
        self.assertIsNone(proposal['selected'])

    def test_disconnected_silence_is_unresolved_not_verified(self):
        evidence = rows(0)
        for row in evidence: row['features'] = {}; row['outcome'] = False
        proposal = self.propose(evidence)
        self.assertIsNone(proposal['selected'])
        verified = self.reactor.verify(proposal, rows(32))
        self.assertFalse(verified['accepted'])
        self.assertIn('not_proof_of_silence', verified['reason'])

    def test_requested_after_action_wrong_scope_and_wrong_target_do_not_bind(self):
        invalid = [condition_pin('signal', 'game', 'action.1', phase='requested'),
                   condition_pin('signal', 'game', 'action.1', position='after'),
                   condition_pin('signal', 'other-game', 'action.1'),
                   condition_pin('signal', 'game', 'action.2')]
        for pin in invalid:
            proposal = self.propose(pins=[pin])
            self.assertIsNone(proposal['selected'])
            self.assertEqual(proposal['rejected'][0]['reason'], 'semantic_scope_or_direction_mismatch')

    def test_corrupt_signal_is_rejected_not_approximately_matched(self):
        pin = self.pins[0]
        bad = replace(pin, signal=replace(pin.signal, wavelength=531))
        with self.assertRaises(ValueError): self.propose(pins=[bad])

    def test_validation_cannot_pick_an_alternative(self):
        proposal = self.propose()
        frozen = deepcopy(proposal)
        checks = rows(32)
        for row in checks: row['outcome'] = row['features']['decoy']
        verified = self.reactor.verify(proposal, checks)
        self.assertFalse(verified['accepted'])
        self.assertEqual(proposal, frozen)

    def test_later_context_shift_is_measured_not_hidden(self):
        verified = self.reactor.verify(self.propose(), rows(32))
        frozen = deepcopy(verified)
        result = self.reactor.evaluate(verified, rows(64, invert=True))
        self.assertGreater(result['test_brier'], result['baseline_test_brier'])
        self.assertEqual(verified, frozen)

    def test_overlap_nonchronological_and_cross_scope_rejected(self):
        proposal = self.propose()
        for checks in (rows(0), rows(20), rows(32, scope='other')):
            with self.assertRaises(ValueError): self.reactor.verify(proposal, checks)
        verified = self.reactor.verify(proposal, rows(32))
        for tests in (rows(32), rows(64, scope='other')):
            with self.assertRaises(ValueError): self.reactor.evaluate(verified, tests)
        reused = rows(64); reused[0]['event_id'] = 'event-0'
        with self.assertRaises(ValueError): self.reactor.evaluate(verified, reused)

    def test_missing_check_condition_stays_unresolved(self):
        checks = rows(32); checks[0]['features'].pop('signal')
        verified = self.reactor.verify(self.propose(), checks)
        self.assertFalse(verified['accepted'])

    def test_budget_is_hard_and_game_execution_never_authorized(self):
        reactor = ResonanceReactor(proposal_budget=1)
        with self.assertRaises(ValueError): reactor.propose(self.pins, rows(0), scope='game', target='action.1')
        for policy in POLICIES:
            self.assertFalse(self.propose(policy=policy)['execution_authorized'])

    def test_real_boolean_validation_and_no_mutation(self):
        evidence = rows(0); before = deepcopy(evidence)
        self.propose(evidence)
        self.assertEqual(evidence, before)
        evidence[0]['features']['signal'] = 1
        with self.assertRaises(ValueError): self.propose(evidence)


if __name__ == '__main__': unittest.main()
