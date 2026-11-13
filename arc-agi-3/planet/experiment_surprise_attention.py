"""Matched-target offline tests of object features, gaze shifts and rule demotion.

No live policy edits, environment source inspection, game calls or submissions.
All alternatives score the same preselected object's measurable outcomes.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import random
import sqlite3
import time
import zlib

from learning_session import classify_boundary, validate_observation
from reaction_resonance import ResonanceReactor, condition_pin, rows_checked
from surprise_attention import Gaze, SupportMonitor, components, match_object, select_object


VARIANTS = ('colour_frozen', 'full_frozen', 'full_demote', 'fixed_frozen', 'fixed_demote', 'shift_frozen', 'shift_demote')
FAMILIES = ('stable', 'attention_shift', 'rule_reverse', 'noisy', 'no_signal', 'occlusion')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def measured_event(before, after, *, event_id, scope, step, segment=0):
    bg, parts = components(before)
    obj = select_object(parts)
    if obj is None:
        return None, 'no_unique_compact_probe'
    if len(before) != len(after) or len(before[0]) != len(after[0]):
        return None, 'shape_change'
    _, after_parts = components(after)
    matched = match_object(obj, after_parts)
    if matched is None:
        return None, 'ambiguous_or_unmatched_probe'
    return dict(before=before, background=bg, obj=obj, target=matched.centre,
                event_id=event_id, scope=scope, step=step, segment=segment,
                outcome=obj.origin != matched.origin), None


def row_for(event, gaze, colour=False):
    values = {v for line in event['before'] for v in line}
    features = ({f'has_colour_{i}': i in values for i in range(16)} if colour else
                gaze.features(event['before'], event['obj'], event['background']))
    return dict(event_id=event['event_id'], scope=event['scope'], step=event['step'],
                features=features, outcome=event['outcome'])


def synthetic(family, seed):
    rng = random.Random(seed)
    events, excluded = [], Counter()
    scope = f'{family}:{seed}'
    for step in range(256):
        before = [[0]*32 for _ in range(24)]
        x, y = (3 if family == 'attention_shift' and step >= 192 else 15), 11
        blocked = bool(rng.getrandbits(1))
        for a,b in ((x,y),(x+1,y),(x,y+1),(x+1,y+1)):
            before[b][a] = 2
        # Same whole-frame palette regardless of local obstacle condition.
        before[y][x+2] = 3 if blocked else 0
        before[2][28] = 3
        before[1][1] = 4
        moves = not blocked
        if family == 'rule_reverse' and step >= 192: moves = not moves
        if family == 'noisy': moves = moves != (rng.random() < .2)
        if family == 'no_signal': moves = bool(rng.getrandbits(1))
        after = [r[:] for r in before]
        # Irrelevant HUD changes on EVERY trial, including stationary-object trials.
        after[1][1] = 0; after[1][2] = 4
        if moves:
            for a,b in ((x,y),(x+1,y),(x,y+1),(x+1,y+1)): after[b][a] = 0
            for a,b in ((x+1,y),(x+2,y),(x+1,y+1),(x+2,y+1)): after[b][a] = 2
        if family == 'occlusion' and step % 5 == 0:
            after = [[0 if v == 2 else v for v in r] for r in after]
        event, reason = measured_event(before, after, event_id=f'{scope}:{step}', scope=scope, step=step)
        if event: events.append(event)
        else: excluded[reason] += 1
    return dict(name=scope, family=family, events=events, exclusions=dict(excluded), eligible_transitions=256)


def replay(directory):
    groups, stats, inputs = defaultdict(list), Counter(), {}
    paths = sorted(Path(directory).glob('*_candidate/learning-archives/*.sqlite3'))
    if not paths: raise ValueError('no source archives found')
    for path in paths:
        inputs[str(path.resolve())] = sha(path)
        db = sqlite3.connect(path.resolve().as_uri()+'?mode=ro', uri=True)
        try:
            if db.execute('PRAGMA user_version').fetchone()[0] != 1:
                raise ValueError('unknown archive version')
            previous, previous_run, segment = None, None, 0
            for run_id, ordinal, key, payload in db.execute('SELECT o.run_id,o.ordinal,p.id,p.payload FROM observations o JOIN objects p ON p.id=o.payload_id ORDER BY o.run_id,o.ordinal'):
                raw = zlib.decompress(payload)
                if hashlib.sha256(raw).hexdigest() != key: raise ValueError('archive hash mismatch')
                record = validate_observation(json.loads(raw))
                stats['observations_read'] += 1
                if run_id != previous_run: previous, segment = None, 0
                if (previous is None or classify_boundary(previous, record) != 'transition'
                    or previous['state'] != 'NOT_FINISHED' or record['state'] != 'NOT_FINISHED'
                    or record['previous_action'] in (None,0)):
                    stats['boundary_or_nonordinary'] += 1
                    segment += 1
                else:
                    stats['eligible_transitions'] += 1
                    # Separate boundary segments; don't validate rules across reset contexts.
                    group = (path.parent.parent.name, str(run_id), segment, record['game_id'], record['level'], record['previous_action'])
                    scope = json.dumps(group)
                    event, reason = measured_event(previous['frame'], record['frame'],
                        event_id=record['observation_id'], scope=scope, step=ordinal, segment=segment)
                    if event:
                        groups[group].append(event); stats['matched_events'] += 1
                    else: stats[reason] += 1
                previous, previous_run = record, run_id
        finally: db.close()
        if sha(path) != inputs[str(path.resolve())]: raise RuntimeError('archive changed')
    cases, skipped = [], []
    for group, events in sorted(groups.items()):
        if len(events) < 128:
            skipped.append(dict(group=group, events=len(events), reason='fewer_than_128_matched_events'))
        else:
            cases.append(dict(name=json.dumps(group), family=group[3], events=events))
    return cases, dict(counts=dict(stats), source_sha256=inputs, skipped=skipped)


def run_case(case):
    events = case['events']
    fit_end, check_end = len(events)//2, 3*len(events)//4
    results = {}
    scope = events[0]['scope']
    for variant in VARIANTS:
        first = events[0]['before']
        gaze = Gaze(len(first[0]), len(first), full=variant.startswith(('full','colour')),
                    shifting=variant.startswith('shift'))
        history = rows_checked([row_for(event, gaze, variant.startswith('colour')) for event in events[:check_end]])
        reactor = ResonanceReactor()
        pins = [condition_pin(f, scope, 'selected_object.displaced') for f in sorted(history[0]['features'])]
        proposal = reactor.propose(pins, history[:fit_end], scope=scope, target='selected_object.displaced')
        verified = reactor.verify(proposal, history[fit_end:])
        monitor = SupportMonitor(verified, history, demote=variant.endswith('demote'))
        scored, visible = [], 0
        for event in events[check_end:]:
            row = row_for(event, gaze, variant.startswith('colour'))
            # No outcome is supplied to forecast or used to choose the probe/gaze.
            prediction = monitor.forecast(row['event_id'], row['scope'], row['step'], row['features'])
            result = monitor.observe(row['outcome'])
            visible += gaze.visible(event['obj'].centre)
            result['gaze_before'] = gaze.centre
            gaze.after_surprise(result['loss'], event['target'])
            result['gaze_after'] = gaze.centre
            if result['prediction'] != prediction['prediction']: raise AssertionError('retrospective forecast mutation')
            scored.append(result)
        n = len(scored)
        results[variant] = dict(accepted=verified['accepted'], reason=verified['reason'],
            selected=None if proposal['selected'] is None else proposal['selected']['feature'],
            test_events=n, brier=sum(r['loss'] for r in scored)/n,
            baseline_brier=sum(r['baseline_loss'] for r in scored)/n,
            visible_fraction=visible/n, shifts=gaze.shifts, demotions=monitor.demotions,
            active_at_end=monitor.active, predictions=scored)
    return dict(name=case['name'], family=case['family'], matched_events=len(events),
                splits=[fit_end,check_end-fit_end,len(events)-check_end], results=results)


def aggregate(cases):
    result = {}
    for variant in VARIANTS:
        rows = [c['results'][variant] for c in cases]
        n = len(rows)
        result[variant] = dict(cases=n, accepted=sum(r['accepted'] for r in rows),
            mean_brier=sum(r['brier'] for r in rows)/n if n else None,
            mean_baseline_brier=sum(r['baseline_brier'] for r in rows)/n if n else None,
            demotions=sum(len(r['demotions']) for r in rows), shifts=sum(r['shifts'] for r in rows),
            better_cases=sum(r['brier'] < r['baseline_brier']-1e-12 for r in rows),
            worse_cases=sum(r['brier'] > r['baseline_brier']+1e-12 for r in rows))
    return result


def run(directory):
    start = time.monotonic()
    files = [Path(__file__).with_name(name) for name in ('experiment_surprise_attention.py',
        'surprise_attention.py','reaction_resonance.py','pin_channels.py','learning_session.py')]
    sources = {str(p):sha(p) for p in files}
    synthetic_cases = [synthetic(family, seed) for family in FAMILIES for seed in range(100,120)]
    synth = [run_case(c) for c in synthetic_cases]
    cases, provenance = replay(directory)
    real = [run_case(c) for c in cases]
    for path, expected in {**sources,**provenance['source_sha256']}.items():
        if sha(path) != expected: raise RuntimeError('input changed')
    return dict(status='complete', scope='offline observational experiment, NOT leaderboard evaluation',
        settings=dict(seeds=[100,119], split='chronological 50/25/25 of matched events',
                      gaze_radius=6, surprise_brier_above=.25, regret_window=8,
                      demotion_mean_excess_above=.10, baseline_window=32,
                      minimum_branch=4, minimum_gain=.01, minimum_replay_events=128),
        source_sha256=sources,
        synthetic=dict(aggregate=aggregate(synth), families={f:aggregate([c for c in synth if c['family']==f]) for f in FAMILIES},
                       coverage=[{k:v for k,v in c.items() if k!='events'} for c in synthetic_cases], cases=synth),
        replay=dict(provenance=provenance, aggregate=aggregate(real), cases=real),
        elapsed_seconds=round(time.monotonic()-start,3), game_actions_spent=0,
        live_agent_changed=False, submitted=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archives', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    report = run(args.archives)
    (args.output/'results.json').write_text(json.dumps(report,indent=2)+'\n', encoding='utf-8')
    print(json.dumps(dict(status=report['status'], synthetic=report['synthetic']['aggregate'],
                         replay=report['replay']['aggregate'], counts=report['replay']['provenance']['counts'],
                         seconds=report['elapsed_seconds'])))
