"""Predeclared synthetic + read-only ARC journal replay; no online game calls.

This tests a one-condition predictor, not physical waves, a reaction simulator,
new game-solving ability, or an autonomous learning deployment.
"""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import random
import sqlite3
import time
import zlib

from learning_session import classify_boundary, validate_observation
from reaction_resonance import ResonanceReactor, condition_pin, rows_checked, POLICIES


FAMILIES = ('clear', 'noisy', 'no_signal', 'deceptive_fit', 'future_shift', 'xor', 'disconnected')
SPLIT = (64, 32, 32)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def synthetic(family, seed):
    rng = random.Random(seed)
    scope, target = f'{family}:{seed}', 'action.1.frame_changed'
    evidence = []
    for step in range(sum(SPLIT)):
        features = {f'decoy-{i}': bool(rng.getrandbits(1)) for i in range(6)}
        features['signal'] = bool(rng.getrandbits(1))
        y = features['signal']
        if family == 'noisy': y = y != (rng.random() < .2)
        elif family == 'no_signal': y = bool(rng.getrandbits(1))
        elif family == 'deceptive_fit' and step < SPLIT[0]: y = features['decoy-0']
        elif family == 'future_shift' and step >= sum(SPLIT[:2]): y = not y
        elif family == 'xor': y = y != features['decoy-0']
        elif family == 'disconnected': features, y = {}, False
        # Deliberately inadmissible after-action feature, for leakage rejection.
        if family != 'disconnected': features['after-answer'] = y
        evidence.append(dict(event_id=f'{scope}:{step}', scope=scope, step=step, features=features, outcome=y))
    features = sorted(set().union(*(row['features'] for row in evidence))) or ['missing']
    pins = [condition_pin(feature, scope, target, wavelength=530 if feature == 'signal' else 650,
                          position='after' if feature == 'after-answer' else 'before') for feature in features]
    return dict(name=scope, family=family, scope=scope, target=target, rows=evidence, pins=pins)


def replay_cases(directory):
    """Only returned observations, with read-only SQLite and checked object hashes."""
    groups, inputs, observation_count, excluded = defaultdict(list), {}, 0, 0
    for path in sorted(Path(directory).glob('*_candidate/learning-archives/*.sqlite3')):
        inputs[str(path.resolve())] = sha(path)
        db = sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True)
        try:
            if db.execute('PRAGMA user_version').fetchone()[0] != 1:
                raise ValueError('unknown archive version')
            previous = None
            for ordinal, key, payload in db.execute('SELECT o.ordinal, p.id, p.payload FROM observations o JOIN objects p ON p.id=o.payload_id ORDER BY o.run_id,o.ordinal'):
                raw = zlib.decompress(payload)
                if hashlib.sha256(raw).hexdigest() != key:
                    raise ValueError('archive integrity mismatch')
                record = validate_observation(json.loads(raw))
                observation_count += 1
                if (previous is not None and classify_boundary(previous, record) == 'transition' and
                    previous['state'] == record['state'] == 'NOT_FINISHED' and record['previous_action'] not in (None, 0)):
                    group = (record['game_id'], record['level'], record['previous_action'])
                    colours = {v for line in previous['frame'] for v in line}
                    scope = json.dumps(group)
                    groups[group].append(dict(event_id=record['observation_id'], scope=scope, step=ordinal,
                        features={f'has_colour_{i}': i in colours for i in range(16)},
                        outcome=previous['frame'] != record['frame']))
                else:
                    excluded += 1
                previous = record
        finally:
            db.close()
        if inputs[str(path.resolve())] != sha(path):
            raise RuntimeError('source archive changed during replay')
    cases, skipped = [], []
    for group, rows in sorted(groups.items()):
        rows = rows_checked(rows)
        if len(rows) < sum(SPLIT):
            skipped.append(dict(group=group, events=len(rows), reason='fewer_than_128_events'))
            continue
        scope, target = rows[0]['scope'], f'action.{group[2]}.frame_changed'
        # Freeze vocabulary using the fit-period feature schema only.
        pins = [condition_pin(feature, scope, target, wavelength=400+int(feature.rsplit('_',1)[1])*20)
                for feature in sorted(rows[0]['features'])]
        cases.append(dict(name=scope, family=group[0], scope=scope, target=target, rows=rows, pins=pins))
    return cases, dict(source_sha256=inputs, observations_read=observation_count,
                       boundary_or_nonordinary_exclusions=excluded, skipped=skipped)


def run_case(case, seed=0):
    rows = rows_checked(case['rows'])
    # Chronological halves/quarters. Synthetic 128 rows gives 64/32/32.
    fit_end, check_end = len(rows)//2, 3*len(rows)//4
    fit, checks, tests = rows[:fit_end], rows[fit_end:check_end], rows[check_end:]
    results = {}
    for policy in POLICIES:
        reactor = ResonanceReactor(minimum_branch=4, minimum_gain=.01, proposal_budget=64)
        proposal = reactor.propose(case['pins'], fit, scope=case['scope'], target=case['target'], policy=policy, seed=seed)
        verified = reactor.verify(proposal, checks)
        evaluation = reactor.evaluate(verified, tests)
        results[policy] = dict(**evaluation, selected=None if proposal['selected'] is None else proposal['selected']['feature'],
            status=verified['status'], reason=verified['reason'], check_gain=verified['check_gain'],
            fit_selected_sound=None if proposal['selected'] is None else proposal['selected']['sound_residual'],
            feature_checks=proposal['feature_checks'], rejected=proposal['rejected'])
    return dict(name=case['name'], family=case['family'], splits=[len(fit), len(checks), len(tests)], results=results)


def aggregate(cases):
    output = {}
    for policy in POLICIES:
        rows = [case['results'][policy] for case in cases]
        n = len(rows)
        output[policy] = dict(cases=n, accepted=sum(row['accepted'] for row in rows),
            mean_brier=None if not n else sum(row['test_brier'] for row in rows)/n,
            mean_baseline_brier=None if not n else sum(row['baseline_test_brier'] for row in rows)/n,
            better_cases=sum(row['test_brier'] < row['baseline_test_brier']-1e-12 for row in rows),
            worse_cases=sum(row['test_brier'] > row['baseline_test_brier']+1e-12 for row in rows))
    return output


def run(archive_directory, seeds=20):
    start = time.monotonic()
    files = [Path(__file__), Path(__file__).with_name('reaction_resonance.py'),
             Path(__file__).with_name('pin_channels.py'), Path(__file__).with_name('learning_session.py')]
    sources = {str(path): sha(path) for path in files}
    synthetic_results = [run_case(synthetic(family, seed), seed) for family in FAMILIES for seed in range(seeds)]
    cases, provenance = replay_cases(archive_directory)
    real_results = [run_case(case) for case in cases]
    for path, expected in {**sources, **provenance['source_sha256']}.items():
        if sha(path) != expected: raise RuntimeError('input changed during experiment')
    return dict(status='complete', source_sha256=sources, seed_count=seeds,
        settings=dict(minimum_branch=4, minimum_gain=.01, proposal_budget=64, split='chronological 50/25/25'),
        scope='synthetic mechanism tests and offline observational replay, NOT leaderboard evaluation',
        synthetic=dict(aggregate=aggregate(synthetic_results),
                       families={family: aggregate([r for r in synthetic_results if r['family']==family]) for family in FAMILIES},
                       cases=synthetic_results),
        replay=dict(provenance=provenance, aggregate=aggregate(real_results), cases=real_results),
        elapsed_seconds=round(time.monotonic()-start, 3), game_actions_spent=0,
        live_agent_changed=False, submitted=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archives', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    report = run(args.archives)
    (args.output/'results.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(dict(status=report['status'], synthetic=report['synthetic']['aggregate'],
                          replay=report['replay']['aggregate'], seconds=report['elapsed_seconds'])))
