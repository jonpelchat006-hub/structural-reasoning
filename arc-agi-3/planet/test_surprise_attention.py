from copy import deepcopy
import unittest

from experiment_surprise_attention import measured_event, run_case, synthetic
from reaction_resonance import ResonanceReactor, condition_pin
from surprise_attention import Component, Gaze, SupportMonitor, components, match_object, select_object


def evidence(start, count):
    return [dict(event_id=f'e{i}', scope='s', step=i, features={'f':bool(i%2)}, outcome=bool(i%2))
            for i in range(start,start+count)]


def monitor(demote=True):
    reactor = ResonanceReactor()
    fit, checks = evidence(0,64), evidence(64,32)
    proposal = reactor.propose([condition_pin('f','s','t')],fit,scope='s',target='t')
    return SupportMonitor(reactor.verify(proposal,checks),fit+checks,demote=demote)


class AttentionTests(unittest.TestCase):
    def test_segment_and_match_translation(self):
        frame = [[0]*10 for _ in range(10)]
        frame[4][3:5] = [2,2]; frame[5][3:5] = [2,2]
        bg, parts = components(frame)
        self.assertEqual(bg,0)
        obj = select_object(parts)
        self.assertEqual(obj.origin,(3,4))
        moved = Component(2,frozenset((x+1,y) for x,y in obj.pixels))
        self.assertEqual(match_object(obj,[moved]),moved)

    def test_ambiguous_shape_and_jump_abstain(self):
        obj = Component(2,frozenset({(1,1),(1,2)}))
        other = Component(2,frozenset({(5,1),(5,2)}))
        self.assertIsNone(select_object([obj,other]))
        self.assertIsNone(match_object(obj,[obj,other]))
        self.assertIsNone(match_object(obj,[]))
        far = Component(2,frozenset({(20,1),(20,2)}))
        self.assertIsNone(match_object(obj,[far]))

    def test_invalid_frame_rejected(self):
        for frame in ([],[[]],[[0],[0,1]],[[True]],[[16]]):
            with self.assertRaises(ValueError): components(frame)

    def test_unknown_neighbour_not_claimed_empty(self):
        case = synthetic('attention_shift',100)
        event = case['events'][200]
        gaze = Gaze(32,24)
        features = gaze.features(event['before'],event['obj'],event['background'])
        self.assertFalse(features['object_visible'])
        self.assertFalse(features['right_1_observed'])
        self.assertFalse(features['right_1_visible_material'])

    def test_gaze_moves_after_surprise_only_and_clamps(self):
        gaze = Gaze(32,24,shifting=True)
        original = gaze.centre
        gaze.after_surprise(.25,(1,1))
        self.assertEqual(gaze.centre,original)
        gaze.after_surprise(.8,(-5,100))
        self.assertEqual(gaze.centre,(0,23))
        self.assertEqual(gaze.shifts,1)
        gaze.after_surprise(.8,None)
        self.assertEqual(gaze.shifts,1)

    def test_fixed_and_full_gaze_do_not_move(self):
        for gaze in (Gaze(32,24),Gaze(32,24,shifting=True,full=True)):
            original = gaze.centre
            gaze.after_surprise(.9,(1,1))
            self.assertEqual(gaze.centre,original)

    def test_object_outcome_ignores_hud_changes(self):
        case = synthetic('stable',100)
        self.assertTrue(any(not event['outcome'] for event in case['events']))
        self.assertEqual(len(case['events']),256)
        self.assertEqual(len(synthetic('occlusion',100)['events']),204)

    def test_stable_rule_keeps_support(self):
        m = monitor()
        for row in evidence(96,32):
            m.forecast(row['event_id'],'s',row['step'],row['features'])
            m.observe(row['outcome'])
        self.assertTrue(m.active)
        self.assertEqual(m.demotions,[])

    def test_reversal_demotes_without_rewriting_previous_prediction(self):
        m = monitor()
        old_model = deepcopy(m.model)
        for row in evidence(96,8):
            forecast = m.forecast(row['event_id'],'s',row['step'],row['features'])
            result = m.observe(not row['outcome'])
            self.assertEqual(result['prediction'],forecast['prediction'])
        self.assertFalse(m.active)
        self.assertEqual(m.model,old_model)
        self.assertEqual(len(m.demotions[0]['evidence']),8)
        forecast = m.forecast('e104','s',104,{'f':False})
        self.assertEqual(forecast['prediction'],forecast['baseline'])

    def test_single_error_does_not_demote(self):
        m = monitor()
        for row in evidence(96,16):
            m.forecast(row['event_id'],'s',row['step'],row['features'])
            m.observe(not row['outcome'] if row['step']==100 else row['outcome'])
        self.assertTrue(m.active)

    def test_forecast_protocol_rejects_duplicates_scopes_and_leak_order(self):
        m = monitor()
        with self.assertRaises(ValueError): m.observe(True)
        for event_id, scope, step in [('e0','s',96),('new','other',96),('new','s',50)]:
            with self.assertRaises(ValueError): m.forecast(event_id,scope,step,{'f':True})
        original = m.forecast('e96','s',96,{'f':False})
        with self.assertRaises(ValueError): m.forecast('e97','s',97,{'f':True})
        original['prediction'] = 1 # caller cannot mutate pending state
        result = m.observe(False)
        self.assertLess(result['prediction'],.1)
        with self.assertRaises(ValueError): m.forecast('e96','s',97,{'f':True})

    def test_history_validation_and_no_mutation(self):
        m = monitor()
        features = {'f':True}
        m.forecast('e96','s',96,features)
        self.assertEqual(features,{'f':True})
        with self.assertRaises(ValueError): m.observe(1)

    def test_shifting_does_not_change_targets_or_first_test_forecast(self):
        case = synthetic('attention_shift',100)
        result = run_case(case)['results']
        fixed, shifted = result['fixed_frozen'], result['shift_frozen']
        self.assertEqual([r['event_id'] for r in fixed['predictions']], [r['event_id'] for r in shifted['predictions']])
        self.assertEqual([r['outcome'] for r in fixed['predictions']], [r['outcome'] for r in shifted['predictions']])
        self.assertEqual(fixed['predictions'][0]['prediction'],shifted['predictions'][0]['prediction'])
        self.assertGreater(shifted['shifts'],0)
        self.assertLess(shifted['brier'],fixed['brier'])

    def test_seed_reproducibility(self):
        self.assertEqual(run_case(synthetic('stable',101)),run_case(synthetic('stable',101)))


if __name__ == '__main__': unittest.main()
