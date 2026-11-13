from dataclasses import replace
import unittest

from border_context import BindingLedger, BorderPin, ContextMonitor, View, bind, neighbourhood_pins
from experiment_border_context import prepare, run_case, synthetic
from reaction_resonance import ResonanceReactor, condition_pin
from surprise_attention import Component


def make_scene(step=0,dx=0,material=False):
    frame=[[0]*12 for _ in range(10)]
    obj=Component(2,frozenset({(3+dx,4),(4+dx,4),(3+dx,5),(4+dx,5)}))
    for x,y in obj.pixels: frame[y][x]=2
    if material: frame[4][5+dx]=3
    view=View.capture(frame,f'e{step}','s',step)
    pin=next(p for p in neighbourhood_pins(view,obj,0) if p.feature=='right_1_material')
    return view,pin,obj


def monitor():
    rows=[dict(event_id=f'e{i}',scope='s',step=i,features={'f':bool(i%2)},outcome=bool(i%2)) for i in range(96)]
    reactor=ResonanceReactor()
    proposed=reactor.propose([condition_pin('f','s','t')],rows[:64],scope='s',target='t')
    return ContextMonitor(reactor.verify(proposed,rows[64:]),rows)


class BorderTests(unittest.TestCase):
    def test_blank_is_unknown_not_empty(self):
        view,pin,_=make_scene()
        blank=replace(view,pixels=())
        binding=bind(pin,blank)
        self.assertEqual(binding['status'],'exposed')
        self.assertIsNone(binding['value'])
        self.assertIsNone(binding['evidence_id'])
        self.assertFalse(binding['execution_authorized'])

    def test_observed_empty_and_material_differ(self):
        for material in (False,True):
            view,pin,_=make_scene(material=material)
            self.assertIs(bind(pin,view)['value'],material)

    def test_partial_region_is_unknown(self):
        view,pin,_=make_scene()
        partial=replace(view,pixels=tuple(p for p in view.pixels if p[:2]!=pin.points[0]))
        self.assertIsNone(bind(pin,partial)['value'])

    def test_stale_scope_phase_frame_and_event_rejected(self):
        view,pin,_=make_scene()
        for bad in (replace(view,scope='other'),replace(view,step=1),replace(view,event_id='other'),
                    replace(view,phase='after'),replace(view,frame_hash='other')):
            binding=bind(pin,bad)
            self.assertEqual(binding['status'],'rejected')
            self.assertIsNone(binding['value'])

    def test_duplicate_view_not_extra_evidence(self):
        view,pin,_=make_scene()
        limited=replace(view,pixels=tuple(p for p in view.pixels if p[:2] in pin.points))
        self.assertEqual(bind(pin,view)['evidence_id'],bind(pin,limited)['evidence_id'])
        ledger=BindingLedger()
        ledger.record(pin,bind(pin,view))
        self.assertIsNone(ledger.record(pin,bind(pin,limited)))
        self.assertEqual(len(ledger.events),1)

    def test_conflicting_duplicate_rejected(self):
        view,pin,_=make_scene()
        binding=bind(pin,view); ledger=BindingLedger(); ledger.record(pin,binding)
        with self.assertRaises(ValueError): ledger.record(pin,{**binding,'value':True})

    def test_offset_alone_never_creates_bound_evidence(self):
        view,pin,_=make_scene(dx=2)
        self.assertEqual(bind(pin,replace(view,pixels=()))['status'],'exposed')

    def test_transport_bends_and_retains_history(self):
        first,pin,_=make_scene()
        second,moved,_=make_scene(step=1,dx=2)
        ledger=BindingLedger(); ledger.record(pin,bind(pin,first))
        event=ledger.record(moved,bind(moved,second))
        self.assertEqual(event['operation'],'bent')
        self.assertFalse(event['value_changed'])
        self.assertEqual(len(ledger.events),2)

    def test_context_value_change_not_broken_rule(self):
        first,pin,_=make_scene()
        second,new,_=make_scene(step=1,material=True)
        ledger=BindingLedger(); ledger.record(pin,bind(pin,first))
        event=ledger.record(new,bind(new,second))
        self.assertEqual(event['operation'],'refreshed')
        self.assertTrue(event['value_changed'])

    def test_wrong_connection_breaks_not_the_object(self):
        old,_,_=make_scene()
        current,pin,_=make_scene(step=1)
        ledger=BindingLedger()
        event=ledger.record(pin,bind(pin,old))
        self.assertEqual(event['operation'],'broken_binding')
        self.assertEqual(bind(pin,current)['status'],'bound')

    def test_anchor_and_region_must_cross_border(self):
        view,_,obj=make_scene()
        with self.assertRaises(ValueError): BorderPin.request(view,obj,'x',(3,4),((8,4),),0)
        with self.assertRaises(ValueError): BorderPin.request(view,obj,'x',(4.5,4),((3,4),),0)
        with self.assertRaises(ValueError): BorderPin.request(view,obj,'x',(4.5,4),((8,4),(8,4)),0)
        with self.assertRaises(ValueError): BorderPin.request(view,obj,'x',(4.5,4),((8,4),),0,(True,False))

    def test_missing_never_demotes_and_can_rebind(self):
        m=monitor()
        for i in range(96,112):
            forecast=m.forecast(f'e{i}','s',i,{})
            self.assertEqual(forecast['prediction'],forecast['baseline'])
            self.assertEqual(m.observe(bool(i%2))['diagnosis'],'missing_context')
        self.assertTrue(m.active)
        self.assertEqual(m.demotions,[])
        self.assertGreater(m.forecast('e112','s',112,{'f':True})['prediction'],.9)

    def test_known_reversal_is_not_called_missing_context(self):
        m=monitor()
        for i in range(96,104):
            m.forecast(f'e{i}','s',i,{'f':bool(i%2)})
            self.assertEqual(m.observe(not bool(i%2))['diagnosis'],'observed_prediction_error')
        self.assertFalse(m.active)
        self.assertEqual(m.demotions[0]['reason'],'possible_rule_or_model_failure')
        self.assertEqual(m.demotions[0]['effective_after'],'e103')

    def test_pending_and_future_order_guards_remain(self):
        m=monitor()
        with self.assertRaises(ValueError): m.observe(True)
        m.forecast('e96','s',96,{})
        with self.assertRaises(ValueError): m.forecast('e97','s',97,{})
        m.observe(False)
        with self.assertRaises(ValueError): m.forecast('e96','s',98,{})

    def test_triangle_square_contract_exact_fill_not_insertion(self):
        rows,_=prepare(synthetic('triangle_slot',200))
        self.assertTrue(any(r['outcome'] for r in rows))
        self.assertTrue(any(not r['outcome'] for r in rows))
        for row in rows:
            self.assertEqual(row['local'],{})
            self.assertEqual(row['full']['destination_exact_shape'],row['outcome'])
        result=run_case(synthetic('triangle_slot',200))
        self.assertGreater(result['binding_operations']['bent'],0)

    def test_plain_context_and_pins_identical_with_same_evidence(self):
        result=run_case(synthetic('attention_shift',200))['results']
        self.assertEqual(result['outside_plain'],result['border_context'])
        self.assertLess(result['border_context']['brier'],result['inside_guarded']['brier'])
        self.assertEqual(result['inside_guarded']['demotions'],[])

    def test_hidden_and_stale_outside_cannot_supply_answer(self):
        for family in ('hidden_context','stale_context'):
            result=run_case(synthetic(family,200))['results']
            border=result['border_context']
            self.assertEqual(border['context_missing'],64)
            self.assertEqual(border['brier'],border['baseline_brier'])
            self.assertEqual(border['demotions'],[])


if __name__=='__main__': unittest.main()
