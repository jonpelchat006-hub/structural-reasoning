"""Offline border-pin contract test, with ordinary full-context controls.

Synthetic scene pairs and read-only saved ARC observations; no action selection.
Triangle/slot scenes specify an EXACT-FILL task, not physical insertion.
"""
import argparse
from collections import Counter
from dataclasses import replace
import json
from pathlib import Path
import random
import time

from border_context import BindingLedger, BorderPin, ContextMonitor, View, bind, neighbourhood_pins
from experiment_surprise_attention import replay, sha, synthetic as prior_synthetic
from reaction_resonance import ResonanceReactor, condition_pin
from surprise_attention import Component, Gaze


VARIANTS = ('inside_naive','inside_guarded','outside_plain','border_context')
FAMILIES = ('stable','attention_shift','rule_reverse','noisy','no_signal','occlusion',
            'hidden_context','stale_context','triangle_slot')


def synthetic(family,seed):
    if family != 'triangle_slot':
        source = 'attention_shift' if family in ('hidden_context','stale_context') else family
        case = prior_synthetic(source,seed)
        case['family']=family; case['name']=f'{family}:{seed}'
        for event in case['events']:
            event['scope']=case['name']; event['event_id']=f"{case['name']}:{event['step']}"
        return case
    rng = random.Random(seed)
    scope=f'{family}:{seed}'
    events=[]
    shape={(0,0),(0,1),(1,1),(0,2),(1,2),(2,2)}
    for step in range(256):
        frame=[[0]*32 for _ in range(16)]
        obj=Component(2,frozenset((x+2,y+5) for x,y in shape))
        for x,y in obj.pixels: frame[y][x]=2
        dx,dy=(20 if step<192 else 24),5
        exact=bool(rng.getrandbits(1))
        slot=shape if exact else {(x,y) for x in range(3) for y in range(3)}
        for x,y in slot: frame[y+dy][x+dx]=3
        points=tuple((x+dx,y+dy) for y in range(3) for x in range(3))
        expected=tuple((x,y) in shape for y in range(3) for x in range(3))
        events.append(dict(before=frame,background=0,obj=obj,scope=scope,event_id=f'{scope}:{step}',
                           step=step,outcome=exact,slot_points=points,expected_mask=expected))
    return dict(name=scope,family=family,events=events,eligible_transitions=256,exclusions={})


def feature_values(bindings):
    return {b['feature']:b['value'] for b in bindings if b['status']=='bound'}


def direct_context(pins, view, expected_view):
    """Ordinary masked features, no border graph. Same provenance guard/control."""
    if (view.scope,view.event_id,view.step,view.frame_hash,view.phase) != (
        expected_view.scope,expected_view.event_id,expected_view.step,expected_view.frame_hash,'before'):
        return {}
    pixels={(x,y):v for x,y,v in view.pixels}
    features={}
    for pin in pins:
        if all(p in pixels for p in pin.points):
            bits=tuple(pixels[p]!=pin.background for p in pin.points)
            features[pin.feature]=bits==pin.expected_mask if pin.expected_mask else any(bits)
    return features


def prepare(case):
    rows=[]; previous=None; ledger=BindingLedger(); counts=Counter()
    for event in case['events']:
        frame,obj=event['before'],event['obj']
        full=View.capture(frame,event['event_id'],event['scope'],event['step'])
        gaze=Gaze(len(frame[0]),len(frame),radius=6)
        visible={(x,y) for y in range(len(frame)) for x in range(len(frame[0])) if gaze.visible((x,y))}
        if 'slot_points' in event:
            # Known source/destination locations are supplied in this synthetic task.
            visible=set(obj.pixels)
            x1=max(x for x,y in obj.pixels)
            pins=[BorderPin.request(full,obj,'destination_exact_shape',(x1+.5,obj.centre[1]),
                  event['slot_points'],event['background'],event['expected_mask'])]
        else: pins=neighbourhood_pins(full,obj,event['background'])
        local=replace(full,pixels=tuple(p for p in full.pixels if p[:2] in visible))
        outside=full
        if event['step']>=192 and case['family']=='hidden_context': outside=replace(full,pixels=())
        if event['step']>=192 and case['family']=='stale_context': outside=previous
        complete=[bind(pin,full) for pin in pins]
        internal=[bind(pin,local) for pin in pins]
        external=[bind(pin,outside) for pin in pins]
        for pin,binding in zip(pins,external):
            change=ledger.record(pin,binding)
            if change: counts[change['operation']]+=1
        raw=direct_context(pins,outside,full)
        if raw != feature_values(external): raise AssertionError('graph changes observed facts')
        rows.append(dict(event_id=event['event_id'],scope=event['scope'],step=event['step'],
                         outcome=event['outcome'],full=feature_values(complete),local=feature_values(internal),
                         outside=raw,border=feature_values(external),
                         pins=[dict(feature=p.feature,anchor=p.anchor,points=p.points,
                                    state=b['status'],reason=b['reason'],evidence_id=b['evidence_id'])
                               for p,b in zip(pins,external)]))
        previous=full
    return rows,dict(counts)


def evidence(row,features):
    return {**{k:row[k] for k in ('event_id','scope','step','outcome')},'features':features}


def run_case(case):
    rows,operations=prepare(case)
    fit_end,check_end=len(rows)//2,3*len(rows)//4
    # One common fully observed fit/check history isolates test-time context delivery.
    history=[evidence(row,row['full']) for row in rows[:check_end]]
    vocabulary=sorted(set().union(*(r['features'] for r in history[:fit_end])))
    scope=rows[0]['scope']; target='observed_probe_outcome'
    reactor=ResonanceReactor()
    proposal=reactor.propose([condition_pin(f,scope,target) for f in vocabulary],history[:fit_end],scope=scope,target=target)
    verified=reactor.verify(proposal,history[fit_end:])
    results={}
    for variant in VARIANTS:
        monitor=ContextMonitor(verified,history,guard=variant!='inside_naive')
        predictions=[]
        for row in rows[check_end:]:
            key='local' if variant.startswith('inside') else 'outside' if variant=='outside_plain' else 'border'
            monitor.forecast(row['event_id'],scope,row['step'],row[key])
            predictions.append(monitor.observe(row['outcome']))
        n=len(predictions)
        results[variant]=dict(accepted=verified['accepted'],test_events=n,
            brier=sum(p['loss'] for p in predictions)/n,
            baseline_brier=sum(p['baseline_loss'] for p in predictions)/n,
            context_missing=sum(p['context_missing'] for p in predictions),
            prediction_errors=sum(p['loss']>.25 for p in predictions),
            diagnostics=dict(Counter(p['diagnosis'] for p in predictions)),
            demotions=monitor.demotions,predictions=predictions)
    # Same data, same model: pins are provenance/obligation bookkeeping, not extra information.
    if results['outside_plain'] != results['border_context']: raise AssertionError('matched context control diverged')
    paired=zip(results['inside_naive']['predictions'],results['border_context']['predictions'])
    recovered=sum(a['loss']>.25 and b['loss']<=.25 and a['context_missing'] and not b['context_missing'] for a,b in paired)
    return dict(name=case['name'],family=case['family'],matched_events=len(rows),
                splits=[fit_end,check_end-fit_end,len(rows)-check_end],accepted=verified['accepted'],
                selected=verified['model']['feature'] if verified['model'] else None,
                reason=verified['reason'],binding_operations=operations,
                local_errors_recovered_with_context=recovered,
                test_outcome_true=sum(r['outcome'] for r in rows[check_end:]),
                first_test_pins=rows[check_end]['pins'],results=results)


def aggregate(cases):
    result={}
    for variant in VARIANTS:
        rows=[c['results'][variant] for c in cases]; n=len(rows)
        result[variant]=dict(cases=n,accepted=sum(r['accepted'] for r in rows),
            mean_brier=sum(r['brier'] for r in rows)/n if n else None,
            mean_baseline_brier=sum(r['baseline_brier'] for r in rows)/n if n else None,
            context_missing=sum(r['context_missing'] for r in rows),demotions=sum(len(r['demotions']) for r in rows),
            better_cases=sum(r['brier'] < r['baseline_brier']-1e-12 for r in rows),
            worse_cases=sum(r['brier'] > r['baseline_brier']+1e-12 for r in rows))
    return result


def run(directory):
    start=time.monotonic()
    names=('experiment_border_context.py','border_context.py','experiment_surprise_attention.py',
           'surprise_attention.py','reaction_resonance.py','pin_channels.py','learning_session.py')
    sources={str(Path(__file__).with_name(n)):sha(Path(__file__).with_name(n)) for n in names}
    synth=[]; coverage=[]
    for family in FAMILIES:
        for seed in range(200,220):
            case=synthetic(family,seed)
            synth.append(run_case(case))
            coverage.append({k:v for k,v in case.items() if k!='events'})
    cases,provenance=replay(directory)
    real=[run_case(c) for c in cases]
    for path,expected in {**sources,**provenance['source_sha256']}.items():
        if sha(path)!=expected: raise RuntimeError('experiment input changed')
    return dict(status='complete',scope='offline predictive and contract tests, NOT leaderboard evaluation',
        settings=dict(seeds=[200,219],split='chronological 50/25/25 of matched events',
                      common_training='fully observed before-action context',gaze_radius=6,
                      minimum_branch=4,minimum_gain=.01,regret_window=8,regret_threshold=.10,baseline_window=32),
        source_sha256=sources,
        synthetic=dict(aggregate=aggregate(synth),families={f:aggregate([c for c in synth if c['family']==f]) for f in FAMILIES},
                       coverage=coverage,cases=synth),
        replay=dict(provenance=provenance,aggregate=aggregate(real),cases=real),
        elapsed_seconds=round(time.monotonic()-start,3),game_actions_spent=0,live_agent_changed=False,submitted=False)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archives',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args(); args.output.mkdir(parents=True,exist_ok=False)
    result=run(args.archives)
    (args.output/'results.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(status=result['status'],synthetic=result['synthetic']['aggregate'],
                         replay=result['replay']['aggregate'],seconds=result['elapsed_seconds'])))
