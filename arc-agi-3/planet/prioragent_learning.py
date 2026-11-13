"""Submission experiment based on the exact reviewed notebook agent.

Archive/conditional frame-change learning runs from observed transitions only.
The policy experiment uses consistent observed displacement in the BFS planner.
Frame-change hypotheses and retrieved archives do NOT authorize game actions.
"""
from collections import deque
from pathlib import Path
from uuid import uuid4
from threading import get_ident

from prioragent_reviewed_baseline import PriorAgent as ReviewedPriorAgent, _grid, GameAction, GameState
from learning_session import LearningSession
from orbital_archive import OrbitalArchive
from pin_channels import ControlChannels


class PriorAgent(ReviewedPriorAgent):
    CANDIDATE_VERSION = 'orbital-channels-2'

    def __init__(self, *args, **kwargs):
        archive_path = kwargs.pop('archive_path', None)
        self.learned_planning = kwargs.pop('learned_planning', True)
        super().__init__(*args, **kwargs)
        self._instance = uuid4().hex
        archive_path = archive_path or Path('learning-archives') / (self._instance+'.sqlite3')
        # Swarm constructs agents on its coordinator and plays on worker threads.
        # Do not create a SQLite connection until the worker actually starts.
        self._archive_path = archive_path
        self._archive = self.learning = self._learning_thread = None
        self.channels = ControlChannels(self._instance)
        self._exchange = None
        self._issued, self._issued_data, self._capture_counter = None, {}, None
        self.learned_plan_calls = 0
        self.learning_summary = {}

    def _ensure_learning(self):
        if self._learning_thread is not None and self._learning_thread != get_ident():
            raise RuntimeError('learning session cannot move between active threads')
        if self.learning is None:
            self._archive = OrbitalArchive(self._archive_path)
            self.learning = LearningSession(self._archive, self._instance)
            self._learning_thread = get_ident()

    def _capture(self, latest_frame):
        self._ensure_learning()
        counter = getattr(self, 'action_counter', len(self.learning.events))
        if counter == self._capture_counter:
            return
        g = _grid(latest_frame)
        if g is None or g.ndim != 2 or not g.size:
            return
        record = dict(observation_id=f'{self._instance}:{counter}',
            game_id=str(self.game_id), instance_id=self._instance,
            level=int(latest_frame.levels_completed), state=getattr(latest_frame.state, 'name', latest_frame.state),
            frame=g.tolist(), previous_action=self._issued, previous_data=self._issued_data)
        if self._exchange is not None:
            record['channel_exchange'] = self._exchange
        result = self.learning.observe(record)
        self._capture_counter = counter
        if result.get('event') in ('reset', 'death', 'win', 'level_change', 'game_change', 'session_change', 'uncertain_boundary'):
            # A boundary is not the ordinary effect of the previous command.
            self.prev_grid = self.prev_action = self.prev_blob = None
            self.plan.clear()
            if result['event'] in ('level_change', 'game_change', 'session_change', 'uncertain_boundary'):
                for effect in self.effects.values():
                    effect['dy'].clear(); effect['dx'].clear()

    def choose_action(self, frames, latest_frame):
        self._capture(latest_frame)
        action = super().choose_action(frames, latest_frame)
        self._issued = int(action.value)
        self._issued_data = dict(getattr(action, 'data', {}) or {})
        if self._issued == 6 and getattr(self, '_last_click', None):
            self._issued_data = dict(x=self._last_click[0], y=self._last_click[1])
        if self._issued == 0:
            self.prev_grid = self.prev_action = self.prev_blob = None
            self.plan.clear()
        return action

    def do_action_request(self, action):
        # Mirror the actual SDK request, not a guessed consequence of choosing it.
        # The framework still owns the single game connection.
        self._issued = int(action.value)
        self._issued_data = action.action_data.model_dump()
        identifier = f'{self._instance}:{self.action_counter}:request'
        request = self.channels.request(identifier, self._issued, self._issued_data)
        self._exchange = None
        frame = super().do_action_request(action)
        self._exchange = self.channels.receipt(request, f'{self._instance}:{self.action_counter+1}')
        return frame

    def _movement_deltas(self, q):
        deltas = {1: (-q, 0), 2: (q, 0), 3: (0, -q), 4: (0, q)}
        if not self.learned_planning:
            return deltas
        for action in deltas:
            effect = self.effects.get(action, {})
            dys, dxs = effect.get('dy', []), effect.get('dx', [])
            if len(dys) < 3 or len(dys) != len(dxs):
                continue
            moves = {(int(dy), int(dx)) for dy, dx in zip(dys[-4:], dxs[-4:])}
            if len(moves) != 1:
                continue
            dy, dx = next(iter(moves))
            if (dy == 0) != (dx == 0) and 0 < max(abs(dy), abs(dx)) <= 2*q:
                deltas[action] = (dy, dx)
        return deltas

    def _bfs_step(self, g, start, goal, q):
        deltas = self._movement_deltas(q)
        priors = {1: (-q, 0), 2: (q, 0), 3: (0, -q), 4: (0, q)}
        if deltas == priors:
            return super()._bfs_step(g, start, goal, q)
        self.learned_plan_calls += 1
        r = max(1, q//2)
        queue, seen = deque([(start, None)]), {start}
        while queue:
            position, first = queue.popleft()
            if abs(position[0]-goal[0])+abs(position[1]-goal[1]) <= q:
                return first
            for action, (dy, dx) in deltas.items():
                target = position[0]+dy, position[1]+dx
                if target in seen or not self._passable(g, target[0], target[1], r):
                    continue
                seen.add(target)
                queue.append((target, action if first is None else first))
        return None

    def main(self):
        self._ensure_learning()
        failure = None
        try:
            return super().main()
        except BaseException as exc:
            failure = exc
            raise
        finally:
            try:
                # On an exception, do not pretend an outstanding action has a
                # returned observation, or mask the original error with replay.
                if failure is None:
                    if self.arc_env and self.arc_env.observation_space:
                        self._capture(self._convert_raw_frame_data(self.arc_env.observation_space))
                    self.learning.archive_current('run_end')
                elif not self.learning.fault:
                    self.learning.archive_current('run_error')
                self.learning_summary = dict(observations=len(self.learning.events),
                    bundles=len(self.learning.closed_bundles), refinements=len(self.learning.refinements),
                    learned_plan_calls=self.learned_plan_calls, archive=str(self._archive.path),
                    channel_codebooks=len(self.channels.books), status='failed' if failure else 'complete')
            except Exception as cleanup_error:
                if failure is None:
                    raise
                failure.add_note(f'Archive finalization also failed: {cleanup_error}')
            finally:
                self._archive.close()
