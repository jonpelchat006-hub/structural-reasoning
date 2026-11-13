"""Mika's university (Jonathan, Oct 21-22): solve -> learn -> teach, graded by students.

  solve   she wins a level (the explorer);
  learn   she looks back: the shortest route in her own map, its waste, what it was made of;
  teach   a lesson plan (a "professor") is handed to a FRESH student - blank map, other seed - on games
          the professor never studied; the professor's grade is how that student does.

A lesson plan may only say HOW to explore (no coordinates, colours or routes of any game): here, a
setting of the explorer's learning knobs, plus at most a learned order of presses fitted on other games.

Departments are families of games, told apart from what a new student sees at the first frame:
  click  = clicks, no movement keys;   keys = movement keys, no clicks;   mixed = both.

The board's rules (board.py) pick one professor per department from ratings on the TRAINING games only.
Five games are held back as the practice final (EXAM) and are never used to choose anything.
The real final is the Kaggle hidden set."""
from __future__ import annotations

import json
import os
import random

import numpy as np

from mika3.explorer2 import Explorer2

# ---------------------------------------------------------------- departments and the practice final
def department(available_actions) -> str | None:
    acts = set(available_actions or [])
    if not acts:
        return None
    moves = bool(acts & {1, 2, 3, 4})
    click = 6 in acts
    if click and not moves:
        return "click"
    if moves and not click:
        return "keys"
    if moves and click:
        return "mixed"
    return "keys"  # only A5/A7: treat as keys


# what each public game shows at its first frame (from the competition's environment files)
PUBLIC_DEPT = {
    "ft09": "click", "lp85": "click", "r11l": "click", "s5i5": "click", "sb26": "click", "su15": "click",
    "tn36": "click", "vc33": "click",
    "g50t": "keys", "ls20": "keys", "re86": "keys", "tr87": "keys", "tu93": "keys", "wa30": "keys",
    "ar25": "mixed", "bp35": "mixed", "cd82": "mixed", "cn04": "mixed", "dc22": "mixed", "ka59": "mixed",
    "lf52": "mixed", "m0r0": "mixed", "sc25": "mixed", "sk48": "mixed", "sp80": "mixed",
}


def exam_split(seed=2026):
    """Practice final: 2 click, 1 keys, 2 mixed games, drawn once with a fixed seed (proportional to
    department size) and never used for choosing anything."""
    rng = random.Random(seed)
    exam = []
    for dept, k in (("click", 2), ("keys", 1), ("mixed", 2)):
        games = sorted(g for g, d in PUBLIC_DEPT.items() if d == dept)
        exam += rng.sample(games, k)
    return sorted(exam)


EXAM = exam_split()
TRAIN = sorted(g for g in PUBLIC_DEPT if g not in EXAM)

# ---------------------------------------------------------------- the faculty: lesson plans
# every plan keeps the within-game look-back lessons (kinds on the last won route go first)
BASE = dict(PREDICT=False, LESSONS=True, STRICT=True, KIND_DECAY=0, CLICK_LATE=False, REPLAY=False,
            MOMENTUM=0.0, MOMENTUM_ADAPT=0.0, CLOCK=False, PRIOR=None, PRIOR_W=0.0, RARE=0.0,
            TAKEOVER=0.0, WINEVENT=0.0, RELATION=0.0, PICK=False, REL_GATE=0.0, WINIMAGE=0.0, GOALSEARCH=0.0)

PROFESSORS = {
    "plain": ("Try what you have not tried, nearest first; on a new level, click first the kinds of thing "
              "that were on the last winning route.", {}),
    "runs-if-runs": ("As plain; and if the last level's winning route was long runs of one press, explore the "
                     "next level by runs: keep pressing what just changed something.", dict(MOMENTUM_ADAPT=2.0)),
    "runs": ("Always explore by runs: keep pressing what just changed something.", dict(MOMENTUM=2.0)),
    "runs-light": ("Lean towards runs, gently.", dict(MOMENTUM=0.8)),
    "replay": ("On a new level, first try the last level's winning route again.", dict(REPLAY=True)),
    "clicks-last": ("Where there are moves and clicks, use the moves until they teach nothing new; then click.",
                    dict(CLICK_LATE=True)),
    "fresh-kinds": ("Give each kind of thing diminishing attention, so others get their turn.", dict(KIND_DECAY=15)),
    "model": ("Learn what the moves do; do not spend presses where your model has never been wrong.",
              dict(PREDICT=True, STRICT=True)),
    "route-prior": ("Order untried presses the way winning routes in this department's other games did.",
                    dict(PRIOR="dept", PRIOR_W=0.5)),
    "route-prior-light": ("Same, with a light hand.", dict(PRIOR="dept", PRIOR_W=0.25)),
    "rare-first": ("Look where rare things happened: when choosing where to go next, prefer states reached by a "
                   "change to pixels that seldom change (an indicator, a door, a counter that is not the clock).",
                   dict(RARE=1.0)),
    "rare-light": ("The same, gently.", dict(RARE=0.4)),
    "rare-runs": ("Rare-first, plus runs-if-runs.", dict(RARE=1.0, MOMENTUM_ADAPT=2.0)),
    # goal professors (Oct 22): teach what getting somewhere looks like, general rung then specific rung
    "took-control": ("Watch for presses where the game takes control (a longer animation than this game "
                     "usually plays). Press more of the kinds of thing that do that, and go back to where it "
                     "happened to look around.", dict(TAKEOVER=1.0)),
    "took-light": ("The same, gently.", dict(TAKEOVER=0.5)),
    "win-event": ("Remember what the press that won the last level did (which colours it changed into "
                  "which). Prefer presses that do the same here, the places they lead to, and things of the "
                  "colour that was pressed.", dict(WINEVENT=1.0)),
    "two-rungs": ("Both: the general rung (the game took control) and the specific rung (what the last "
                  "win did).", dict(TAKEOVER=1.0, WINEVENT=1.0)),
    "far-change": ("Watch for presses after which something small changed far from where the press acted (an "
                   "indicator), or a colour vanished from the screen. Press more of those kinds, and go back to "
                   "where it happened.", dict(RELATION=1.0)),
    "far-change-win": ("Far-change, plus what the last win did.", dict(RELATION=1.0, WINEVENT=1.0)),
    "far-rare": ("Far-change, but only while it is unusual for this game (it follows fewer than 3 in 10 "
                 "presses), as 'took control' is measured against the game's usual.", dict(RELATION=1.0, REL_GATE=0.3)),
    "three-rungs": ("Took control, far-change while unusual, and what the last win did.",
                    dict(TAKEOVER=1.0, WINEVENT=1.0, RELATION=1.0, REL_GATE=0.3)),
    # the image plane (Oct 22): a press whose picture - up to recolouring, flips and shifts - matches a
    # winning press of an earlier level of this game
    "win-image": ("Keep a picture of every winning press. Prefer presses whose picture matches one of them, "
                  "allowing only limited turns: recolouring, the 8 flips and rotations, and shifting.", dict(WINIMAGE=1.0)),
    "took-image": ("The general rung (the game took control) and the image rung.", dict(TAKEOVER=1.0, WINIMAGE=1.0)),
    "two-rungs-image": ("Two-rungs, plus the image rung.", dict(TAKEOVER=1.0, WINEVENT=1.0, WINIMAGE=1.0)),
    "goal-search": ("At the start of a level, look for where the before-picture of an earlier win fits in the "
                    "screen (its own colours, any flip or rotation). Click things there first, and prefer presses and "
                    "places that touch it.", dict(GOALSEARCH=1.0)),
    "two-rungs-search": ("Two-rungs plus goal-search.", dict(TAKEOVER=1.0, WINEVENT=1.0, GOALSEARCH=1.0)),
    # control for the goal professors: they all choose where to go next among the near frontier states
    # (bfs_pick) instead of the nearest one; this professor does only that, with no rung
    "pick-only": ("Control: look a few steps further and go to the most promising unexplored place, not "
                  "simply the nearest.", dict(PICK=True)),
}

_HERE = os.path.dirname(os.path.abspath(__file__))


def _load(name):
    try:
        return json.load(open(os.path.join(_HERE, name)))
    except Exception:
        return None


DEPT_PRIOR = _load("prior_dept.json")      # {dept: {game: LOO weights, "all": weights}}
CURRICULUM = _load("curriculum.json")      # {dept: professor name}, written by the board


def knobs_for(prof):
    k = dict(BASE)
    k.update(PROFESSORS[prof][1])
    return k


def apply_knobs(agent, k, dept, game_id):
    m = agent.mind
    m.use_model = bool(k["PREDICT"])
    m.use_lessons = bool(k["LESSONS"])
    m.mover.STRICT = bool(k["STRICT"])
    m.KIND_DECAY = k["KIND_DECAY"]
    m.CLICK_LATE = bool(k["CLICK_LATE"])
    m.REPLAY = bool(k["REPLAY"])
    m.MOMENTUM = float(k["MOMENTUM"]); m.momentum_now = m.MOMENTUM
    m.MOMENTUM_ADAPT = float(k["MOMENTUM_ADAPT"])
    m.CLOCK = bool(k["CLOCK"])
    m.RARE = float(k.get("RARE", 0.0))
    m.TAKEOVER = float(k.get("TAKEOVER", 0.0))
    m.WINEVENT = float(k.get("WINEVENT", 0.0))
    m.RELATION = float(k.get("RELATION", 0.0))
    m.PICK = bool(k.get("PICK", False))
    m.REL_GATE = float(k.get("REL_GATE", 0.0))
    m.WINIMAGE = float(k.get("WINIMAGE", 0.0))
    m.GOALSEARCH = float(k.get("GOALSEARCH", 0.0))
    pr = None
    if k["PRIOR"] == "dept" and DEPT_PRIOR and dept in DEPT_PRIOR:
        d = DEPT_PRIOR[dept]
        pr = d.get(game_id[:4], d.get("all"))      # a game the professor studied gets weights fitted without it
    m.PRIOR = None if pr is None else np.array(pr, dtype=float)
    m.PRIOR_W = float(k["PRIOR_W"])


class Student(Explorer2):
    """A fresh student taught by one professor (the same plan in every department)."""
    PROFESSOR = "plain"
    PREDICT = False
    LESSONS = True

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.dept = None

    def choose_action(self, frames, latest_frame):
        if self.dept is None and latest_frame.available_actions:
            self.dept = department(latest_frame.available_actions)
            apply_knobs(self, knobs_for(self.plan()), self.dept, self.game_id)
        return super().choose_action(frames, latest_frame)

    def plan(self):
        return self.PROFESSOR


class MikaUniversity(Student):
    """The graduate: in each department she follows the professor the board chose for it."""
    def plan(self):
        cur = CURRICULUM or {}
        return cur.get(self.dept, cur.get("default", "plain"))


# one class per professor, for the rating runs: university.py:Prof_runs_if_runs etc.
for _name in PROFESSORS:
    _cls = type("Prof_" + _name.replace("-", "_"), (Student,), {"PROFESSOR": _name})
    globals()[_cls.__name__] = _cls
