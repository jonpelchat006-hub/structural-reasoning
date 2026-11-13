"""Bounded synthetic transfer check and read-only legacy-report readiness audit."""
import argparse
import json
from pathlib import Path

from game_port import GamePort
from void_volume import ColourReserve, common_factors


def run():
    # Explicitly synthetic environment: action 1 succeeds iff contact is present.
    # Colour is a nuisance variable. The boundary coordinates/annotations are
    # supplied fixtures, NOT extracted from ARC frames by an implemented mapper.
    training=[('train-blue',1,True),('train-red',2,True)]
    heldout=[('test-green-contact',3,True),('test-green-away',3,False),('test-yellow-contact',4,True)]
    reserve=ColourReserve('synthetic/level1','press-at-contact',[1,2,3,4,5])
    reserve.set_reachable(5,False)
    pins=[]; comparisons=[]
    def evaluate(trial):
        name,colour,contact=trial
        def transport(request):
            return {**request,'observation':{'door_open':contact,'wall_colour':colour}}
        port=GamePort('synthetic/level1',{'door_open':False,'wall_colour':colour},transport,budget=1)
        result=port.exchange(1,expected_version=0,available_actions=[1])
        outcome=result['observation']['door_open']
        reserve.observe(name,scope='synthetic/level1',question_id='press-at-contact',colour=colour,fired=outcome)
        return outcome,result
    for name,colour,contact in training:
        outcome,result=evaluate((name,colour,contact))
        assert outcome and result['outstanding']==0
        pins.append({'id':name,'observation_id':name,'scope':'synthetic/level1','version':'rule1',
                     'space':'synthetic-context','action':1,'effect':'door_open',
                     'start':[-1,0,0],'end':[2,0,0],
                     'annotations':[{'t':[0,1/3],'factors':{'colour':str(colour)}},
                                    {'t':[1/3,2/3],'factors':{'contact':'yes'}},
                                    {'t':[2/3,1],'factors':{'colour':str(colour)}}]})
    mined=common_factors(pins,scope='synthetic/level1',version='rule1',space='synthetic-context',
                        action=1,effect='door_open',lower=[0,-1,-1],upper=[1,1,1])
    whole=common_factors(pins,scope='synthetic/level1',version='rule1',space='synthetic-context',
                        action=1,effect='door_open',lower=[-1.1,-1,-1],upper=[2.1,1,1])
    before=reserve.snapshot()
    factors=dict(mined['common_factors'])
    for trial in heldout:
        name,colour,contact=trial
        observed_factors={'contact':'yes' if contact else 'no'}
        prediction=bool(factors) and all(observed_factors.get(k)==v for k,v in factors.items())
        # Exact-colour lookup abstains for unseen colours; abstention isn't an error.
        lookup=None if colour not in {r[1] for r in training} else True
        actual,result=evaluate(trial)
        comparisons.append({'trial':name,'volume_prediction':prediction,'colour_lookup':lookup,
                            'actual':actual,'outstanding':result['outstanding']})
    return {'kind':'synthetic_diagnostic_not_arc_score','training_trials':len(training),
            'candidate_factors':mined['common_factors'],'heldout':comparisons,
            'whole_pin_common_factors':whole['common_factors'],
            'correct_predictions':sum(x['volume_prediction']==x['actual'] for x in comparisons),
            'colour_lookup_abstentions':sum(x['colour_lookup'] is None for x in comparisons),
            'reserve_before_heldout':before,'reserve_after_heldout':reserve.snapshot(),
            'limits':['hand-authored geometry and factor annotations','toy rule known to fixture author',
                      'no learned pixel-to-volume mapper','no causal or ARC improvement claim']}


def audit(paths):
    result=[]
    for path in paths:
        report=json.loads(Path(path).read_text(encoding='utf-8'))
        pins=report.get('pins',[])
        needed=('start','end','space','observation_id','annotations','condition')
        result.append({'path':str(path),'pins':len(pins),
                       'missing_fields':{key:sum(key not in p for p in pins) for key in needed},
                       'note':'Do not invent depth, colour trials, or body-to-screen transforms.'})
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('reports',nargs='*',type=Path)
    args=parser.parse_args()
    print(json.dumps({'experiment':run(),'legacy_readiness':audit(args.reports)},indent=2))
