import random
from arcengine import GameAction, GameState
from agents.agent import Agent
class Rand(Agent):
    MAX_ACTIONS = 200
    def __init__(self, *a, **k):
        super().__init__(*a, **k); self.rng = random.Random(0)
    def is_done(self, frames, latest):
        return latest.state is GameState.WIN
    def choose_action(self, frames, latest):
        if latest.state in (GameState.NOT_PLAYED, GameState.GAME_OVER): return GameAction.RESET
        acts = [a for a in latest.available_actions if a != 0] or [1]
        a = GameAction.from_id(self.rng.choice(acts))
        if a.is_complex(): a.set_data({"x": self.rng.randrange(64), "y": self.rng.randrange(64)})
        return a
