from copy import deepcopy
import unittest

from game_port import GamePort
from void_volume import ColourReserve, clip_segment, common_factors


def pin(name,colour='blue',observation=None,contact='yes'):
    return {'id':name,'observation_id':observation or name,'scope':'toy/level1',
            'version':'hypothesis1','space':'declared-test-space','action':1,'effect':'door-opens',
            'start':[-1,0,0],'end':[2,0,0],
            'annotations':[{'t':[0,1/3],'factors':{'wall_colour':colour}},
                           {'t':[1/3,2/3],'factors':{'contact':contact}},
                           {'t':[2/3,1],'factors':{'wall_colour':colour}}]}


def mine(pins):
    return common_factors(pins,scope='toy/level1',version='hypothesis1',
                          space='declared-test-space',action=1,effect='door-opens',
                          lower=[0,-1,-1],upper=[1,1,1])


class PortTests(unittest.TestCase):
    def test_roundtrip_version_and_copy(self):
        requests=[]
        def send(r):
            requests.append(deepcopy(r))
            return {**r,'observation':{'changed':True}}
        port=GamePort('g',{'changed':False},send,budget=1)
        result=port.exchange(1,expected_version=0,available_actions=[1])
        self.assertEqual(result['outstanding'],0)
        self.assertEqual(result['version'],1)
        self.assertEqual(result['remaining'],0)
        self.assertEqual(result['events'][0]['request_id'],result['events'][1]['request_id'])
        result['observation']['changed']=False
        self.assertTrue(port.snapshot()['observation']['changed'])
        with self.assertRaises(ValueError):
            port.exchange(1,expected_version=1,available_actions=[1])
        self.assertEqual(len(requests),1)

    def test_uncertain_call_not_retried(self):
        calls=[]
        def send(r):
            calls.append(r)
            raise TimeoutError()
        port=GamePort('g',{},send)
        result=port.exchange(1,expected_version=0,available_actions=[1])
        self.assertEqual(result['outstanding'],1)
        self.assertEqual(result['remaining'],99)
        with self.assertRaises(ValueError):
            port.exchange(1,expected_version=0,available_actions=[1])
        self.assertEqual(len(calls),1)

    def test_mismatched_return_keeps_old_observation(self):
        for field,value in [('scope','other'),('request_id','wrong'),('action',True)]:
            port=GamePort('g',{'initial':True},lambda r:{**r,field:value,'observation':{}})
            result=port.exchange(1,expected_version=0,available_actions=[1])
            self.assertEqual(result['outstanding'],1)
            self.assertEqual(result['observation'],{'initial':True})

    def test_stale_illegal_and_reentrant_dispatch(self):
        def send(r):
            with self.assertRaises(ValueError):
                port.exchange(1,expected_version=0,available_actions=[1])
            return {**r,'observation':{}}
        port=GamePort('g',{},send)
        for action,version in [(2,0),(True,0),(1,1)]:
            with self.assertRaises(ValueError):
                port.exchange(action,expected_version=version,available_actions=[1])
        self.assertEqual(port.snapshot()['remaining'],100)
        self.assertEqual(port.exchange(1,expected_version=0,available_actions=[1])['outstanding'],0)


class VolumeTests(unittest.TestCase):
    def test_clip_and_reverse(self):
        self.assertEqual(clip_segment([-1,0,0],[2,0,0],[0,-1,-1],[1,1,1]),(1/3,2/3))
        self.assertEqual(clip_segment([2,0,0],[-1,0,0],[0,-1,-1],[1,1,1]),(1/3,2/3))

    def test_tangencies_and_points_not_volume(self):
        for start,end in [([-1,1,0],[2,1,0]),([-1,0,0],[0,0,0]),([.5,0,0],[.5,0,0])]:
            self.assertIsNone(clip_segment(start,end,[0,-1,-1],[1,1,1]))
        with self.assertRaises(ValueError):
            clip_segment([0,0,0],[1,1,1],[0,0,0],[0,1,1])

    def test_inside_factor_not_outside_colour(self):
        pins=[pin('one','blue'),pin('two','red')];original=deepcopy(pins)
        report=mine(pins)
        self.assertEqual(report['common_factors'],[('contact','yes')])
        self.assertFalse(report['causal_confirmation'])
        self.assertFalse(report['execution_authorized'])
        self.assertEqual(pins,original)

    def test_partial_annotation_does_not_cover_volume(self):
        p=pin('two');p['annotations']=[{'t':[.4,.5],'factors':{'contact':'yes'}}]
        self.assertEqual(mine([pin('one'),p])['common_factors'],[])

    def test_adjacent_spans_combine_but_conflicting_labels_do_not(self):
        p=pin('two');p['annotations']=[{'t':[1/3,.5],'factors':{'contact':'yes'}},
                                     {'t':[.5,2/3],'factors':{'contact':'yes'}}]
        self.assertEqual(mine([pin('one'),p])['common_factors'],[('contact','yes')])
        p['annotations'].append({'t':[0,1],'factors':{'contact':'no'}})
        self.assertEqual(mine([pin('one'),p])['common_factors'],[])

    def test_missing_fields_and_mixed_context_cannot_create_support(self):
        for field,value in [('scope','other'),('version','old'),('space','body-space'),('action',2),('effect','other')]:
            p=pin('two');p[field]=value
            report=mine([pin('one'),p])
            self.assertEqual(report['common_factors'],[])
            self.assertEqual(len(report['rejected']),1)
        p=pin('two');p.pop('observation_id')
        self.assertEqual(mine([pin('one'),p])['common_factors'],[])

    def test_duplicate_hypotheses_not_independent_observations(self):
        report=mine([pin('one',observation='same'),pin('two',observation='same')])
        self.assertEqual(report['independent_observations'],1)
        self.assertEqual(report['common_factors'],[])
        with self.assertRaises(ValueError):
            mine([pin('one'),pin('one')])


class ReserveTests(unittest.TestCase):
    def test_unknown_unreachable_and_observed_failure_are_distinct(self):
        r=ColourReserve('g','q',[1,2,3,4]);r.set_reachable(2,False);r.set_reachable(3,True)
        r.observe('trial1',scope='g',question_id='q',colour=1,fired=False)
        snap=r.snapshot()
        self.assertEqual([x['status'] for x in snap['rows']],['tested','untested_unreachable','untested_reachable','untested_reachability_unknown'])
        self.assertEqual(snap['reserve_fraction'],.75)
        self.assertEqual(snap['rows'][0]['silent'],1)
        self.assertEqual(snap['rows'][1]['silent'],0)

    def test_duplicate_and_wrong_context(self):
        r=ColourReserve('g','q',[1])
        args=dict(scope='g',question_id='q',colour=1,fired=True)
        r.observe('trial',**args);r.observe('trial',**args)
        self.assertEqual(r.snapshot()['rows'][0]['fired'],1)
        for overrides in [{'scope':'other'},{'question_id':'other'},{'fired':False}]:
            with self.assertRaises(ValueError):
                r.observe('trial',**{**args,**overrides})

    def test_snapshot_is_copy(self):
        r=ColourReserve('g','q',[1]);s=r.snapshot();s['rows'][0]['silent']=99
        self.assertEqual(r.snapshot()['rows'][0]['silent'],0)

    def test_unknown_colours_emit_questions_not_outcomes(self):
        r=ColourReserve('g','q',[1,2]);r.set_reachable(2,True)
        s=r.snapshot()
        self.assertEqual(len(s['questions']),2)
        self.assertTrue(all(q['execution_ready'] is False for q in s['questions']))
        self.assertEqual(s['questions'][1]['kind'],'propose_observed_trial')
        with self.assertRaises(ValueError):
            r.observe('bad',scope='g',question_id='q',colour=True,fired=True)


class ExperimentTests(unittest.TestCase):
    def test_offline_transfer_and_reserve(self):
        from compare_void_volume import run
        result=run()
        self.assertEqual(result['candidate_factors'],[('contact','yes')])
        self.assertEqual(result['whole_pin_common_factors'],[])
        self.assertEqual(result['correct_predictions'],3)
        self.assertEqual(result['colour_lookup_abstentions'],3)
        self.assertEqual(result['reserve_before_heldout']['untested_count'],3)
        self.assertEqual(result['reserve_after_heldout']['untested_count'],1)
        self.assertTrue(all(r['outstanding']==0 for r in result['heldout']))


if __name__=='__main__':
    unittest.main()
