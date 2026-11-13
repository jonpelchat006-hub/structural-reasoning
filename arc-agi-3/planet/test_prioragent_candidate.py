"""Local synthetic regressions; never execute notebook setup/submission cells."""
from collections import deque
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import random
import subprocess
import sys
from types import SimpleNamespace
import unittest
import numpy as np

from prioragent_candidate import PriorAgent, GameAction, GameState


ROOT = Path(__file__).resolve().parent


def frame(grid=None, *, level=0, state=GameState.NOT_FINISHED, available=(1, 2, 3, 4, 5)):
    if grid is None: grid = np.zeros((64, 64), int)
    return SimpleNamespace(frame=[grid.tolist()], levels_completed=level,
                           state=state, available_actions=list(available))


def agent(**kwargs):
    bot = PriorAgent(game_id="fixture", probe_actions=False, **kwargs)
    # Most tests isolate control/observation accounting from baseline perception.
    bot._blob = lambda g: None
    bot._landmarks = lambda g: []
    return bot


class BoundaryTests(unittest.TestCase):
    def prime(self, bot):
        bot.prev_grid = np.zeros((64, 64), np.int16)
        bot.prev_action = 6; bot.prev_blob = (10, 10)
        bot._last_click = (10, 10)
        bot.effects[6]["changed"] = 4
        bot.click_chain.append((10, 10)); bot.plan.append(1)
        return deepcopy(dict(bot.effects))

    def test_terminal_reset_detaches_previous_action_and_click(self):
        for state in (GameState.NOT_PLAYED, GameState.GAME_OVER):
            bot = agent(); before = self.prime(bot)
            action = bot.choose_action([], frame(state=state))
            self.assertEqual(action, GameAction.RESET)
            self.assertIsNone(bot.prev_grid); self.assertIsNone(bot.prev_action)
            self.assertIsNone(bot.prev_blob); self.assertIsNone(bot._last_click)
            self.assertFalse(bot.plan); self.assertFalse(bot.click_chain)
            bot.choose_action([], frame(np.full((64, 64), 4)))
            self.assertEqual(dict(bot.effects), before)
            self.assertEqual(bot.press_count, 0)

    def test_new_level_is_not_credited_as_click_movement_or_noise(self):
        bot = agent(); before = self.prime(bot)
        bot.self_colors.add(12); bot.walkable.add(3); bot.walls.add(4); bot.quantum = 5
        bot.tried[("pos", (10, 10))][1] = 9
        bot.ambient = np.ones((64, 64), bool); bot.press_count = 40
        bot.choose_action([], frame(np.full((64, 64), 7), level=1))
        self.assertEqual(dict(bot.effects), before)
        self.assertEqual(bot.level_at, 1); self.assertEqual(bot.press_count, 0)
        self.assertIsNone(bot.ambient); self.assertFalse(bot.self_colors)
        self.assertFalse(bot.walkable); self.assertFalse(bot.walls)
        self.assertEqual(bot.quantum, 0); self.assertFalse(bot.click_chain)
        self.assertNotIn(("pos", (10, 10)), bot.tried)

    def test_shape_change_breaks_transition_even_without_level_counter_change(self):
        bot = agent(); before = self.prime(bot)
        bot.choose_action([], frame(np.ones((32, 32), int)))
        self.assertEqual(dict(bot.effects), before)
        self.assertEqual(bot.prev_grid.shape, (32, 32))

    def test_stuck_reset_and_missing_frame_detach(self):
        for missing in (False, True):
            bot = agent(); self.prime(bot)
            bot.steps = 301 if not missing else 0
            fr = frame()
            if missing: fr.frame = []
            self.assertEqual(bot.choose_action([], fr), GameAction.RESET)
            self.assertIsNone(bot.prev_action); self.assertIsNone(bot.prev_blob)

    def test_same_level_real_action_still_teaches_effect(self):
        bot = agent()
        bot.choose_action([], frame(available=(5,)))
        g = np.zeros((64, 64), int); g[10, 10] = 3
        bot.choose_action([], frame(g, available=(5,)))
        self.assertEqual(bot.effects[5]["changed"], 1)
        self.assertEqual(bot.press_count, 1)


class AmbientTests(unittest.TestCase):
    def learn(self, *, one_action=False, full=False, self_color=False):
        bot = agent()
        if self_color: bot.self_colors.add(3)
        prev = np.zeros((64, 64), np.int16)
        for i in range(12):
            g = prev.copy()
            if full: g[:] = (i + 1) % 2
            else: g[63, 20] = (3 if self_color else 8) if i % 2 == 0 else 0
            bot.prev_action = 1 if one_action else 1 + i % 3
            bot._note_change(g, prev)
            prev = g
        return bot, prev

    def test_learned_timer_does_not_make_new_state_or_effect(self):
        bot, g = self.learn()
        changed = g.copy(); changed[63, 20] = 8
        self.assertTrue(bot.ambient[63, 20])
        self.assertEqual(bot._hash(g), bot._hash(changed))
        self.assertFalse(bot._diff(changed, g).any())
        changed[10, 10] = 3
        self.assertNotEqual(bot._hash(g), bot._hash(changed))
        self.assertEqual(bot._diff(changed, g).sum(), 1)

    def test_single_control_toggle_is_not_classified_as_timer(self):
        bot, g = self.learn(one_action=True)
        self.assertFalse(bot.ambient.any())

    def test_self_pixels_and_whole_screen_change_are_not_masked(self):
        for kwargs in (dict(self_color=True), dict(full=True)):
            bot, g = self.learn(**kwargs)
            self.assertFalse(bot.ambient.any())

    def test_warmup_keeps_changes_visible(self):
        bot = agent(); a = np.zeros((64, 64), int); b = a.copy(); b[63, 0] = 8
        bot.prev_action = 1; bot._note_change(b, a)
        self.assertFalse(bot.ambient.any())
        self.assertNotEqual(bot._hash(a), bot._hash(b))

    def test_mask_revision_discards_old_hash_evidence(self):
        bot, g = self.learn()
        bot.visit[123] = 9; bot.banned.add((123, 1)); bot.noop_at[(123, 1)] = 3
        bot.tried[123][1] = 9; bot.tried[("pos", (2, 3))][1] = 9
        # Known self pigmentation contradicts the timer abstraction.
        bot.self_colors.add(8); changed = g.copy(); changed[63, 20] = 8
        bot._note_change(changed, g)
        self.assertFalse(bot.visit); self.assertFalse(bot.banned); self.assertFalse(bot.noop_at)
        self.assertNotIn(123, bot.tried)
        self.assertEqual(bot.tried[("pos", (2, 3))][1], 9)

    def test_real_moving_blob_remains_visible(self):
        bot, g = self.learn()
        a = g.copy(); a[20:23, 20:23] = 3
        b = g.copy(); b[20:23, 23:26] = 3
        bot.self_colors = {3}; bot.prev_grid = a
        self.assertEqual(PriorAgent._blob(bot, b), (21, 24))
        self.assertEqual(bot._diff(b, a).sum(), 18)

    def test_mask_ablation_restores_full_frame_key(self):
        bot, g = self.learn(); b = g.copy(); b[63, 20] = 8
        bot.mask_ambient = False
        self.assertNotEqual(bot._hash(g), bot._hash(b))
        self.assertEqual(bot._diff(b, g).sum(), 1)

    def test_noops_are_local_even_after_action_succeeded_elsewhere(self):
        bot = agent(); bot.effects[5]["changed"] = 20
        for _ in range(4): bot.choose_action([], frame(available=(5,)))
        key = bot._hash(np.zeros((64, 64), int))
        self.assertIn((key, 5), bot.banned)
        g = np.zeros((64, 64), int); g[10, 10] = 3
        bot.choose_action([], frame(g, available=(5,)))
        self.assertNotIn((key, 5), bot.banned)

    def test_shrinking_border_bar_does_not_require_repeated_pixel_changes(self):
        bot = agent(); prev = np.zeros((64, 64), int); prev[61:63, :56] = 11
        for i in range(12):
            g = np.zeros_like(prev); g[61:63, :55 - i] = 11
            bot.prev_action = 1 + i % 3; bot._note_change(g, prev); prev = g
        self.assertTrue(bot.ambient[61:63].all())
        self.assertLessEqual(bot.change_count.max(), 1)
        shorter = g.copy(); shorter[61:63, 40:] = 0
        self.assertEqual(bot._hash(shorter), bot._hash(g))
        changed_board = shorter.copy(); changed_board[20, 20] = 3
        self.assertNotEqual(bot._hash(changed_board), bot._hash(g))
        # A refill is still available in the untouched raw frame.
        refill = g.copy(); refill[61:63, :56] = 11
        self.assertEqual(bot._hash(refill), bot._hash(g))
        self.assertNotEqual(np.count_nonzero(refill), np.count_nonzero(g))
        # A third colour breaks the simple-bar model immediately.
        novel = g.copy(); novel[61, 10] = 4
        bot._note_change(novel, g)
        self.assertFalse(bot.ambient[61].any())
        self.assertTrue(bot._diff(novel, g)[61, 10])

    def test_interior_bar_and_single_control_bar_are_not_ambient(self):
        for row, single in ((30, False), (61, True)):
            bot = agent(); prev = np.zeros((64, 64), int); prev[row, :56] = 11
            for i in range(12):
                g = np.zeros_like(prev); g[row, :55 - i] = 11
                bot.prev_action = 1 if single else 1 + i % 3
                bot._note_change(g, prev); prev = g
            self.assertFalse(bot.ambient.any())


class ReproducibilityTests(unittest.TestCase):
    def test_hash_includes_shape_and_ignores_storage_dtype(self):
        bot = agent()
        self.assertNotEqual(bot._hash(np.zeros((2, 4))), bot._hash(np.zeros((4, 2))))
        self.assertEqual(bot._hash(np.zeros((2, 4), np.int8)), bot._hash(np.zeros((2, 4), np.int64)))

    def test_private_rng_does_not_change_global_random_state(self):
        before = random.getstate()
        bot = agent()
        for _ in range(10): bot.choose_action([], frame())
        self.assertEqual(random.getstate(), before)

    def test_interleaved_agents_do_not_change_each_others_decisions(self):
        a, b, noise = agent(), agent(), agent(candidate_seed=42)
        for _ in range(20):
            expected = a.choose_action([], frame()).value
            for _ in range(3): noise.choose_action([], frame())
            self.assertEqual(b.choose_action([], frame()).value, expected)

    def test_different_process_hash_seeds_produce_identical_trace(self):
        code = "from test_prioragent_candidate import agent, frame; import json; b=agent(); print(json.dumps([b.seed,b._hash(__import__('numpy').zeros((64,64))),[b.choose_action([],frame()).value for _ in range(20)]]))"
        outputs = []
        for seed in ("1", "12345"):
            result = subprocess.run([sys.executable, "-B", "-c", code], cwd=ROOT,
                                    env={**os.environ, "PYTHONHASHSEED": seed},
                                    capture_output=True, text=True, check=True, timeout=30)
            outputs.append(result.stdout)
        self.assertEqual(outputs[0], outputs[1])


class ProbeAndPackageTests(unittest.TestCase):
    def test_available_actions_probed_once_per_level_not_per_reset(self):
        bot = PriorAgent(game_id="probe")
        bot._blob = lambda g: None; bot._landmarks = lambda g: []
        self.assertEqual(bot.choose_action([], frame(available=(2, 5))).value, 2)
        self.assertEqual(bot.choose_action([], frame(state=GameState.GAME_OVER)).value, 0)
        self.assertEqual(bot.choose_action([], frame(available=(2, 5))).value, 5)
        self.assertFalse(bot.probe_queue)
        self.assertEqual(bot.choose_action([], frame(level=1, available=(2, 5))).value, 2)

    def test_probe_and_queued_plan_never_return_removed_control(self):
        bot = PriorAgent(game_id="probe")
        bot._blob = lambda g: None; bot._landmarks = lambda g: []
        self.assertEqual(bot.choose_action([], frame(available=(1, 2, 3))).value, 1)
        self.assertEqual(bot.choose_action([], frame(available=(3,))).value, 3)
        bot.plan = deque([1])
        self.assertEqual(bot.choose_action([], frame(available=(5,))).value, 5)

    def test_click_only_game_gets_valid_click_without_movement_probes(self):
        bot = PriorAgent(game_id="click")
        act = bot.choose_action([], frame(available=(6,)))
        self.assertEqual(act.value, 6)
        self.assertTrue(0 <= act.data["x"] < 64 and 0 <= act.data["y"] < 64)
        self.assertFalse(bot.probe_queue)

    def test_numpy_frame_stack_is_supported(self):
        bot = agent(); fr = frame(); fr.frame = np.zeros((1, 64, 64), np.int16)
        self.assertNotEqual(bot.choose_action([], fr), GameAction.RESET)

    def test_notebook_is_source_exact_and_has_no_stale_outputs(self):
        notebook = json.loads((ROOT / "prioragent-arc-agi-3-candidate.ipynb").read_text(encoding="utf-8"))
        source = (ROOT / "prioragent_candidate.py").read_text(encoding="utf-8")
        self.assertEqual("".join(notebook["cells"][1]["source"][1:]), source)
        self.assertEqual(notebook["metadata"]["candidate"]["source_sha256"], hashlib.sha256(source.encode()).hexdigest())
        for cell in notebook["cells"]:
            if cell["cell_type"] == "code":
                self.assertIsNone(cell["execution_count"])
                self.assertEqual(cell["outputs"], [])


if __name__ == "__main__":
    unittest.main()
