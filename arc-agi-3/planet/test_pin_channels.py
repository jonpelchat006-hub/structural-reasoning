from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from learning_session import LearningSession
from orbital_archive import OrbitalArchive
from pin_channels import Message, PinCodebook, ChannelRouter, ControlChannels, canonical


class ChannelTests(unittest.TestCase):
    def setUp(self):
        self.message = Message.create('request-1', 'scope', 'action.3', 'requested', {'action': 3}, ['observation-0'])
        self.red = PinCodebook('controls', 'scope', 1, {('action.3', 'requested'): (650, 0)})
        self.green = PinCodebook('planner', 'scope', 1, {('action.3', 'requested'): (530, 90)})

    def test_same_meaning_changes_colour_and_orientation_not_identity(self):
        router = ChannelRouter([self.red, self.green], [('controls', 'planner')])
        result = router.route(self.red.encode(self.message), 'planner')
        self.assertEqual(result['status'], 'delivered')
        self.assertEqual([h['signal']['wavelength'] for h in result['hops']], [650, 530])
        self.assertEqual([h['signal']['orientation'] for h in result['hops']], [0, 90])
        self.assertEqual(result['message_id'], self.message.identity)
        self.assertFalse(result['execution_authorized'])

    def test_wrong_pin_cannot_directly_read_source_colour(self):
        with self.assertRaises(ValueError): self.green.decode(self.red.encode(self.message))

    def test_opaque_relay_retains_original_message(self):
        relay = PinCodebook('relay', 'scope', 1, {('unknown', 'observed'): (600, 0)})
        router = ChannelRouter([self.red, relay, self.green], [('controls', 'relay'), ('relay', 'planner')])
        result = router.route(self.red.encode(self.message), 'planner')
        self.assertFalse(result['hops'][1]['visible'])
        self.assertIsNone(result['hops'][1]['signal'])
        self.assertEqual(result['message'], self.message.value)

    def test_unreachable_unknown_or_budget_exhausted_becomes_question(self):
        unknown = PinCodebook('unknown', 'scope', 1, {('different', 'observed'): (500, 1)})
        router = ChannelRouter([self.red, self.green, unknown],
                               [('controls', 'unknown'), ('unknown', 'controls'), ('unknown', 'planner')])
        for target, hops in [('planner', 1), ('unknown', 8)]:
            result = router.route(self.red.encode(self.message), target, hops)
            self.assertEqual(result['status'], 'question')
            self.assertEqual(result['message'], self.message.value)
            self.assertLessEqual(len(result['visited']), 3)
            self.assertFalse(result['execution_authorized'])

    def test_cross_scope_and_revision_mismatch_rejected(self):
        for book in [PinCodebook('controls', 'other', 1, self.red.symbols),
                     PinCodebook('controls', 'scope', 2, self.red.symbols)]:
            with self.assertRaises(ValueError): book.decode(self.red.encode(self.message))
        other = PinCodebook('other', 'other-scope', 1, self.red.symbols)
        router = ChannelRouter([self.red, other], [('controls', 'other')])
        self.assertEqual(router.route(self.red.encode(self.message), 'other')['status'], 'question')

    def test_symbols_collisions_bounds_tampering_and_phase_forgery(self):
        with self.assertRaises(ValueError):
            PinCodebook('bad', 'scope', 1, {('a', 'requested'): (500, 0), ('b', 'observed'): (500, 0)})
        for wavelength, orientation in [(900, 0), (500, 360), (True, 0)]:
            with self.assertRaises(ValueError):
                PinCodebook('bad', 'scope', 1, {('a', 'observed'): (wavelength, orientation)})
        signal = self.red.encode(self.message)
        changed_phase = Message.create('request-1', 'scope', 'action.3', 'executed', {'action': 3})
        for changed in [replace(signal, wavelength=651), replace(signal, checksum='0'*64), replace(signal, message=changed_phase)]:
            with self.assertRaises(ValueError): self.red.decode(changed)

    def test_deterministic_assignment_is_reversible_and_full_hash_retained(self):
        meanings = [(f'action.{a}', phase) for a in range(8) for phase in ('requested', 'executed', 'observed')]
        a = PinCodebook.assigned('a', 'scope', meanings)
        b = PinCodebook.assigned('a', 'scope', reversed(meanings))
        self.assertEqual(a.manifest(), b.manifest())
        self.assertEqual(len(set(a.symbols.values())), len(meanings))
        for semantic, phase in meanings:
            message = Message.create('id', 'scope', semantic, phase, {'value': True})
            self.assertEqual(a.decode(a.encode(message)), message)
            self.assertEqual(len(message.identity), 64)

    def test_reused_colour_can_mean_something_else_on_other_pin(self):
        other = PinCodebook('different', 'scope', 1, {('action.2', 'observed'): (650, 0)})
        with self.assertRaises(ValueError): other.decode(self.red.encode(self.message))
        router = ChannelRouter([self.red, other], [('controls', 'different')])
        self.assertEqual(router.route(self.red.encode(self.message), 'different')['status'], 'question')

    def test_message_payload_copies_and_boolean_outcomes(self):
        payload = {'nested': [1]}
        message = Message.create('id', 'scope', 'x', 'observed', payload)
        payload['nested'].append(2)
        read = message.value; read['payload']['nested'].append(3)
        self.assertEqual(message.value['payload']['nested'], [1])
        bus = ControlChannels('scope')
        with self.assertRaises(ValueError): bus.observed('x', 1, 'a', 'b', 1)

    def test_requested_receipt_observed_are_distinct_and_bound(self):
        bus = ControlChannels('scope')
        request = bus.request('r', 3, {'x': 4, 'y': 5})
        receipt = bus.receipt(request, 'observation-1')
        observed = bus.observed('o', 3, 'observation-0', 'observation-1', False)
        self.assertNotIn('receipt', request)
        self.assertEqual(receipt['receipt']['phase'], 'executed')
        self.assertEqual(observed['message']['phase'], 'observed')
        self.assertFalse(observed['message']['payload']['frame_changed'])
        self.assertEqual(receipt['receipt']['payload']['request_id'], request['request_id'])

    def test_exchange_persists_and_replays_without_becoming_extra_evidence(self):
        with TemporaryDirectory() as tmp:
            archive = OrbitalArchive(Path(tmp)/'a.sqlite3')
            try:
                session = LearningSession(archive, 'scope')
                first = dict(observation_id='0', game_id='g', instance_id='i', level=0,
                             state='NOT_FINISHED', previous_action=None, previous_data={}, frame=[[0]])
                session.observe(first)
                bus = ControlChannels('scope')
                second = dict(first, observation_id='1', previous_action=3, frame=[[1]],
                              channel_exchange=bus.receipt(bus.request('r', 3, {}), '1'))
                session.observe(second)
                session.archive_current()
                replay = LearningSession.resume(archive, 'scope')
                self.assertEqual(session.snapshot()['pins'], replay.snapshot()['pins'])
                self.assertEqual(session.commands, replay.commands)
                self.assertEqual(len(replay.events), 2)
                self.assertEqual(replay.commands[0]['observed_signal']['message']['payload'], {'frame_changed': True})
                forged = deepcopy(second); forged['observation_id'] = '2'
                with self.assertRaises(ValueError): session.observe(forged)
                self.assertEqual(len(archive.observations('scope')), 2)
            finally:
                archive.close()


if __name__ == '__main__': unittest.main()
