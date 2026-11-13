"""Durable boundary-aware learning from observable before/after game frames.

Features are explicitly measured colour presence. Outcome is exact frame change,
not movement, progress or causality. No archive command is executed on retrieval.
"""
from copy import deepcopy
import hashlib
import json

from automatic_pin_refiner import AutomaticPinRefiner
from evidence_pin import EvidencePin
from orbital_archive import encoded
from pin_channels import ControlChannels, Message, canonical


STATES = {'NOT_PLAYED', 'NOT_FINISHED', 'GAME_OVER', 'WIN'}


def validate_observation(record):
    for key in ('observation_id', 'game_id', 'instance_id'):
        if not isinstance(record.get(key), str) or not record[key] or len(record[key]) > 256:
            raise ValueError('named observation, game and instance IDs required')
    if type(record.get('level')) is not int or record['level'] < 0 or record.get('state') not in STATES:
        raise ValueError('explicit valid level and engine state required')
    action = record.get('previous_action')
    if action is not None and (type(action) is not int or not 0 <= action <= 7):
        raise ValueError('explicit previous action 0..7 or None required')
    frame = record.get('frame')
    if not isinstance(frame, list) or not 1 <= len(frame) <= 128 or not isinstance(frame[0], list) or not 1 <= len(frame[0]) <= 128:
        raise ValueError('bounded rectangular ARC frame required')
    if any(not isinstance(row, list) or len(row) != len(frame[0]) or any(type(v) is not int or not 0 <= v <= 15 for v in row) for row in frame):
        raise ValueError('rectangular integer palette 0..15 required')
    return deepcopy(record)


def classify_boundary(previous, current):
    if previous is None:
        return 'bootstrap'
    if current['game_id'] != previous['game_id']:
        return 'game_change'
    if current['instance_id'] != previous['instance_id']:
        return 'session_change'
    if current['previous_action'] == 0:
        return 'reset'
    if current['level'] != previous['level']:
        return 'level_change'
    if current['state'] == 'GAME_OVER' and previous['state'] != 'GAME_OVER':
        return 'death'
    if current['state'] == 'WIN' and previous['state'] != 'WIN':
        return 'win'
    if (len(current['frame']), len(current['frame'][0])) != (len(previous['frame']), len(previous['frame'][0])):
        return 'uncertain_boundary'
    if previous['state'] in ('GAME_OVER', 'WIN') and current['state'] == 'NOT_FINISHED':
        return 'uncertain_boundary'  # Never invent an unobserved reset action.
    return 'transition'


class LearningSession:
    def __init__(self, archive, run_id):
        if not isinstance(run_id, str) or not run_id:
            raise ValueError('run ID required')
        self.archive, self.run_id = archive, run_id
        self.previous, self.attempt = None, 0
        self.pins, self.roles, self.commands, self.refinements = {}, {}, [], []
        self.closed_bundles, self.seen, self.events = [], {}, []
        self.fault, self.terminal_archived = False, False
        self.refiner = AutomaticPinRefiner()
        self.channels = ControlChannels(run_id)

    @classmethod
    def resume(cls, archive, run_id):
        session = cls(archive, run_id)
        for record in archive.observations(run_id):
            session.observe(record, replay=True)
        return session

    def _bundle(self, reason):
        if self.previous is None:
            return None
        return dict(game_id=self.previous['game_id'], instance_id=self.previous['instance_id'],
                    level=self.previous['level'], attempt=self.attempt, run_id=self.run_id,
                    reason=reason, commands=deepcopy(self.commands),
                    pins={str(a): p.snapshot() for a, p in self.pins.items()},
                    roles=deepcopy(self.roles), refinements=deepcopy(self.refinements),
                    channel_codebooks=self.channels.manifest(),
                    last_observation=self.previous['observation_id'],
                    outcome='failed' if reason == 'death' else 'won' if reason == 'win' else 'incomplete',
                    execution_authorized=False)

    def archive_current(self, reason='checkpoint'):
        bundle = self._bundle(reason)
        if bundle is None:
            return None
        key = self.archive.save_bundle(bundle)
        if key not in self.closed_bundles:
            self.closed_bundles.append(key)
        return key

    def observe(self, record, *, replay=False):
        if self.fault:
            raise ValueError('session faulted; explicitly resume durable observations')
        record = validate_observation(record)
        exchange = record.get('channel_exchange')
        if exchange is not None:
            # A request cannot become a receipt simply by changing its colour.
            request = Message(canonical(exchange['request']))
            receipt = Message(canonical(exchange['receipt']))
            expected = self.channels.receipt(self.channels.request(
                request.value['id'], record['previous_action'], record.get('previous_data', {})),
                record['observation_id'])
            if exchange != expected or receipt.value['phase'] != 'executed':
                raise ValueError('control request/SDK receipt/observation binding mismatch')
        key = record['observation_id']
        digest = hashlib.sha256(encoded(record)).hexdigest()
        if key in self.seen:
            if self.seen[key] != digest:
                raise ValueError('conflicting duplicate observation')
            return dict(status='duplicate', adds_observations=False)
        event = classify_boundary(self.previous, record)
        try:
            # Commit actual observations first; a failure in derivation can be
            # replayed from the durable journal. Never silently retry game actions.
            if not replay:
                self.archive.append_observation(self.run_id, key, len(self.seen), record)
            before = self.previous
            if event in ('game_change', 'session_change', 'reset', 'level_change', 'uncertain_boundary'):
                if not self.terminal_archived:
                    self.archive_current(event)
                if event in ('game_change', 'session_change'):
                    self.attempt = 0
                else:
                    self.attempt += 1
                self.pins, self.roles, self.commands, self.refinements = {}, {}, [], []
                self.terminal_archived = False
            frame_id = self.archive.put(record['frame'])
            # Every command/outcome is retained, but boundary frames are never
            # used as ordinary within-board effect examples.
            if before is not None and record['previous_action'] is not None:
                command = dict(action=record['previous_action'], data=deepcopy(record.get('previous_data', {})),
                               before=before['observation_id'], after=key, event=event,
                               before_frame=self.archive.put(before['frame']), after_frame=frame_id)
                command['observed_signal'] = self.channels.observed(key + ':observed', record['previous_action'],
                    before['observation_id'], key, before['frame'] != record['frame'])
                if exchange is not None:
                    command['channel_exchange'] = deepcopy(exchange)
                if event in ('transition', 'death', 'win'):
                    self.commands.append(command)
            learned = False
            if event == 'transition' and before is not None and record['previous_action'] not in (None, 0) and before['state'] == record['state'] == 'NOT_FINISHED':
                action = record['previous_action']
                if action not in self.pins:
                    scope = json.dumps([self.run_id, record['game_id'], record['instance_id'], record['level'], self.attempt])
                    self.pins[action] = EvidencePin(f'action-{action}-frame-change', scope=scope,
                        subject='full-observed-frame', action=action, question='Does the returned frame differ?',
                        factors={f'has_colour_{i}': f'palette-{i}' for i in range(16)})
                    self.roles[action] = dict(fit=[], check=[])
                pin, roles = self.pins[action], self.roles[action]
                count = sum(map(len, roles.values()))
                if count >= 512:
                    # Bounded observation windows detach rather than evict.
                    self.archive_current('capacity')
                    old = pin.snapshot()
                    pin = EvidencePin(old['id'], scope=old['scope']+f'/window-{len(self.commands)}',
                                      subject=old['subject'], action=action, question=old['question'], factors=old['factor_colours'])
                    self.pins[action], self.roles[action] = pin, dict(fit=[], check=[])
                    roles, count = self.roles[action], 0
                colours = {v for row in before['frame'] for v in row}
                pin.record(key, scope=pin.snapshot()['scope'], action=action,
                    bits={f'has_colour_{i}': i in colours for i in range(16)},
                    outcome=before['frame'] != record['frame'],
                    observation={'before': {'frame_id': self.archive.put(before['frame'])}, 'after': {'frame_id': frame_id}},
                    route='central-port', direction=[0, 0, 1])
                roles['check' if count % 3 == 2 else 'fit'].append(key)
                if count >= 7 and (count+1) % 16 == 0:
                    result = self.refiner.step(pin, fit_ids=roles['fit'], check_ids=roles['check'])
                    if result['changed']:
                        self.refinements.append(result['proposal'])
                        learned = True
            self.previous = record
            if event in ('death', 'win'):
                self.archive_current(event)
                self.terminal_archived = True
            self.seen[key] = digest
            self.events.append(dict(observation_id=key, event=event, game_id=record['game_id'],
                                    instance_id=record['instance_id'], level=record['level'], attempt=self.attempt))
            return dict(status='observed', event=event, refined=learned,
                        attempt=self.attempt, execution_authorized=False)
        except Exception:
            self.fault = True
            raise

    def snapshot(self):
        return deepcopy(dict(run_id=self.run_id, attempt=self.attempt, events=self.events,
                             pins={a: p.snapshot() for a, p in self.pins.items()}, roles=self.roles,
                             refinements=self.refinements, closed_bundles=self.closed_bundles,
                             fault=self.fault, execution_authorized=False))
