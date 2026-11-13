#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
arcshim.py — a minimal stand-in for Kaggle's `arcengine`/`agents` so the SAME PriorAgent file
runs in three places: the Kaggle competition, the live ARC-3 API, and the local mock (practice).
Only the surface PriorAgent actually touches is provided.
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional


class GameState:
    NOT_PLAYED = "NOT_PLAYED"
    NOT_FINISHED = "NOT_FINISHED"
    IN_PROGRESS = "IN_PROGRESS"
    WIN = "WIN"
    GAME_OVER = "GAME_OVER"


class _Action:
    def __init__(self, name: str, value: int):
        self.name, self.value = name, value
        self.data: Dict[str, Any] = {}

    def set_data(self, d: Dict[str, Any]):
        self.data = dict(d)
        return self

    def __repr__(self):
        return f"GameAction.{self.name}"


class _GameActionMeta(type):
    def __getitem__(cls, name):
        return getattr(cls, name)


class GameAction(metaclass=_GameActionMeta):
    RESET = _Action("RESET", 0)
    ACTION1 = _Action("ACTION1", 1)
    ACTION2 = _Action("ACTION2", 2)
    ACTION3 = _Action("ACTION3", 3)
    ACTION4 = _Action("ACTION4", 4)
    ACTION5 = _Action("ACTION5", 5)
    ACTION6 = _Action("ACTION6", 6)
    ALL = [RESET, ACTION1, ACTION2, ACTION3, ACTION4, ACTION5, ACTION6]


class FrameData:
    def __init__(self, frame=None, state=GameState.NOT_PLAYED, score=0,
                 levels_completed=0, available_actions: Optional[List] = None):
        self.frame = frame or []
        self.state = state
        self.score = score
        self.levels_completed = levels_completed
        self.available_actions = available_actions if available_actions is not None \
            else [GameAction.ACTION1, GameAction.ACTION2, GameAction.ACTION3,
                  GameAction.ACTION4, GameAction.ACTION5, GameAction.ACTION6]

    @classmethod
    def from_wire(cls, fr: Dict) -> "FrameData":
        """The ARC-3 wire json (arc3_client mock or live) -> FrameData."""
        st = fr.get("state", "NOT_FINISHED")
        if st == "NOT_FINISHED": st = GameState.NOT_FINISHED
        # the wire says which actions this game accepts (ft09/vc33/lp85 are [6]: click-only).
        # Sep 3: dropping this made the live proxy press ACTION1-5 on click-only games — 32 of
        # ft09's 35 presses were no-ops. Kaggle's real FrameData carries it; so must the shim.
        av = fr.get("available_actions")
        acts = None
        if isinstance(av, list) and av:
            acts = [GameAction["ACTION%d" % int(a)] for a in av if 1 <= int(a) <= 6]
        return cls(frame=fr.get("frame"), state=st, score=fr.get("score", 0),
                   levels_completed=fr.get("levels_completed", fr.get("score", 0)),
                   available_actions=acts)


class Agent:
    """Base class stub: mirrors the fields the real agents.Agent sets (game_id at least)."""
    def __init__(self, *args: Any, **kwargs: Any):
        self.game_id = kwargs.get("game_id", "mock")
        for k, v in kwargs.items():
            setattr(self, k, v)
