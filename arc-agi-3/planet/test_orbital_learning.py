from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import numpy as np

from learning_session import LearningSession, classify_boundary, validate_observation
from orbital_archive import OrbitalArchive
from prioragent_learning import PriorAgent


def observation(name, *, game='g-v1', instance='session1', level=0, state='NOT_FINISHED', action=1, frame=None):
    return dict(observation_id=name, game_id=game, instance_id=instance, level=level,
                state=state, previous_action=action, frame=[[0, 0], [0, 1]] if frame is None else frame,
                previous_data={})


class ArchiveTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.path = Path(self.tmp.name)/'learning.sqlite3'
        self.archive = OrbitalArchive(self.path)

    def tearDown(self):
        self.archive.close(); self.tmp.cleanup()

    def test_roundtrip_dedup_and_immutable_copies(self):
        value = {'pins': [1, 2], 'yes': True}
        key = self.archive.put(value)
        self.assertEqual(key, self.archive.put(deepcopy(value)))
        value['pins'].append(3)
        recovered = self.archive.get(key); recovered['pins'].append(4)
        self.assertEqual(self.archive.get(key)['pins'], [1, 2])
        self.archive.close(); self.archive = OrbitalArchive(self.path)
        self.assertEqual(self.archive.get(key)['pins'], [1, 2])

    def test_retrieval_is_candidate_not_new_evidence(self):
        session = LearningSession(self.archive, 'run')
        session.observe(observation('0', action=None))
        session.observe(observation('1', state='GAME_OVER'))
        before = session.snapshot()
        retrieved = self.archive.retrieve(game_id='g-v1')
        self.assertEqual(retrieved[0]['bundle']['outcome'], 'failed')
        self.assertFalse(retrieved[0]['adds_observations'])
        self.assertFalse(retrieved[0]['execution_authorized'])
        self.assertEqual(session.snapshot(), before)
        self.assertEqual(self.archive.retrieve(game_id='different'), [])

    def test_corruption_is_detected(self):
        key = self.archive.put({'data': 1})
        other = self.archive.put({'data': 2})
        self.archive.db.execute('UPDATE objects SET payload=(SELECT payload FROM objects WHERE id=?) WHERE id=?', (other, key))
        self.archive.db.commit()
        with self.assertRaises(ValueError): self.archive.get(key)

    def test_journal_conflicting_duplicate_rejected(self):
        self.archive.append_observation('r', 'o', 0, {'value': 1})
        self.assertFalse(self.archive.append_observation('r', 'o', 0, {'value': 1}))
        with self.assertRaises(ValueError):
            self.archive.append_observation('r', 'o', 0, {'value': 2})
        self.assertEqual(self.archive.observations('r'), [{'value': 1}])


class SessionTests(ArchiveTests):
    def test_explicit_boundaries_not_pixel_overlap_or_amount_of_motion(self):
        before = observation('0')
        self.assertEqual(classify_boundary(before, observation('1', frame=[[15, 15], [15, 15]])), 'transition')
        self.assertEqual(classify_boundary(before, observation('1', action=0)), 'reset')
        self.assertEqual(classify_boundary(before, observation('1', game='other')), 'game_change')
        self.assertEqual(classify_boundary(before, observation('1', instance='other')), 'session_change')
        self.assertEqual(classify_boundary(before, observation('1', level=1)), 'level_change')
        self.assertEqual(classify_boundary(before, observation('1', state='GAME_OVER')), 'death')
        self.assertEqual(classify_boundary(before, observation('1', state='WIN')), 'win')
        self.assertEqual(classify_boundary(before, observation('1', frame=[[0]])), 'uncertain_boundary')

    def test_death_then_reset_then_new_game_detaches_scopes(self):
        s = LearningSession(self.archive, 'run')
        s.observe(observation('0', action=None))
        s.observe(observation('1'))
        self.assertEqual(s.pins[1].snapshot()['trial_count'], 1)
        old_scope = s.pins[1].snapshot()['scope']
        s.observe(observation('2', state='GAME_OVER'))
        s.observe(observation('3', action=0))
        self.assertEqual(s.attempt, 1); self.assertEqual(s.pins, {})
        s.observe(observation('4'))
        self.assertNotEqual(s.pins[1].snapshot()['scope'], old_scope)
        s.observe(observation('5', game='other'))
        self.assertEqual(s.attempt, 0); self.assertEqual(s.pins, {})
        self.assertTrue(any(r['bundle']['reason'] == 'death' for r in self.archive.retrieve()))

    def test_duplicate_observation_and_stale_conflict_do_not_add_trials(self):
        s = LearningSession(self.archive, 'run')
        s.observe(observation('0', action=None)); record = observation('1')
        s.observe(record); before = s.snapshot()
        self.assertEqual(s.observe(record)['status'], 'duplicate')
        self.assertEqual(s.snapshot(), before)
        with self.assertRaises(ValueError): s.observe({**record, 'frame': [[1]]})

    def test_durable_replay_restores_pins_and_boundary_history(self):
        s = LearningSession(self.archive, 'run')
        for record in [observation('0', action=None), observation('1'),
                       observation('2', action=0), observation('3'), observation('4', state='WIN')]:
            s.observe(record)
        before = s.snapshot()
        self.archive.close(); self.archive = OrbitalArchive(self.path)
        restored = LearningSession.resume(self.archive, 'run')
        self.assertEqual(restored.snapshot(), before)
        for pin_state in restored.snapshot()['pins'].values():
            for trial in pin_state['trials']:
                self.assertIsInstance(self.archive.get(trial['observation']['before']['frame_id']), list)

    def test_measured_features_and_outcome_ignore_hypotheses(self):
        s = LearningSession(self.archive, 'run')
        s.observe(observation('0', action=None))
        s.observe(observation('1', frame=[[0, 0], [0, 2]]))
        t = s.pins[1].snapshot()['trials'][0]
        self.assertTrue(t['bits']['has_colour_1'])
        self.assertFalse(t['bits']['has_colour_2'])
        self.assertTrue(t['outcome'])
        before = s.snapshot()
        s.archive_current()
        self.assertEqual(s.snapshot()['pins'], before['pins'])

    def test_validation_rejects_missing_metadata_and_bad_frames_before_journal(self):
        s = LearningSession(self.archive, 'run')
        for changes in [dict(level=True), dict(state='guess'), dict(frame=[[True]]),
                        dict(frame=[[0], [0, 1]]), dict(previous_action=True), dict(game_id='')]:
            with self.assertRaises(ValueError): s.observe({**observation('0'), **changes})
        self.assertEqual(self.archive.observations('run'), [])

    def test_revival_without_observed_reset_stays_uncertain(self):
        self.assertEqual(classify_boundary(observation('0', state='GAME_OVER'), observation('1')), 'uncertain_boundary')

    def test_online_frame_features_can_drive_an_automatic_split(self):
        s = LearningSession(self.archive, 'run')
        s.observe(observation('start', action=None, frame=[[0, 0], [0, 0]]))
        for i in range(24):
            present = i % 2 == 0
            before = [[1 if present else 0, 0], [0, 0]]
            after = [[1, 0], [0, 3]] if present else before
            s.observe(observation(f'setup-{i}', action=2, frame=before))
            s.observe(observation(f'test-{i}', action=1, frame=after))
        self.assertTrue(s.refinements)
        choice = next(r['selected'] for r in s.refinements if r['pin_id'] == 'action-1-frame-change')
        self.assertEqual(choice['factor'], 'has_colour_1')
        self.assertFalse(choice['absent_expected'])
        self.assertTrue(choice['present_expected'])
        restored = LearningSession.resume(self.archive, 'run')
        self.assertEqual(restored.snapshot(), s.snapshot())


class LearnedPlannerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.agent = PriorAgent(game_id='mock', archive_path=Path(self.tmp.name)/'a.sqlite3')

    def tearDown(self):
        if self.agent._archive is not None:
            self.agent._archive.close()
        self.tmp.cleanup()

    def test_consistent_observed_motion_changes_planner_mapping(self):
        effect = self.agent.effects[1]
        effect['dy'] = [0, 0, 0]; effect['dx'] = [2, 2, 2]
        self.assertEqual(self.agent._movement_deltas(2)[1], (0, 2))
        self.agent._passable = lambda grid, y, x, r: 0 <= y < 10 and 0 <= x < 10
        action = self.agent._bfs_step(np.zeros((10, 10)), (4, 2), (4, 8), 2)
        self.assertEqual(action, 1)
        self.assertEqual(self.agent.learned_plan_calls, 1)

    def test_sparse_conflicting_diagonal_and_large_moves_keep_prior(self):
        for dy, dx in [([0, 0], [2, 2]), ([0, 0, 2], [2, 2, 0]),
                       ([2]*3, [2]*3), ([0]*3, [20]*3)]:
            self.agent.effects[1]['dy'] = dy; self.agent.effects[1]['dx'] = dx
            self.assertEqual(self.agent._movement_deltas(2)[1], (-2, 0))


if __name__ == '__main__':
    unittest.main()
