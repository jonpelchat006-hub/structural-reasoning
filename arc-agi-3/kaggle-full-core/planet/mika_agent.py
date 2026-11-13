"""The competition agent: Mika's full inner core (planet body + core), played through mika_bridge.

The official ARC-AGI-3-Agents runner gives every hidden game its own Agent with an environment (arc_env). Her body drives
the game itself, so MikaAgent.main() hands her body a wire to that environment and lets her play; the runner's
choose_action loop is not used. Each press still goes through arc_env.step (the gateway scores it as usual).
"""
from __future__ import annotations
import os, sys, time, traceback, threading

PLANET = os.environ.get("MIKA_PLANET", os.path.join(os.path.dirname(os.path.abspath(__file__)), "planet"))
if PLANET not in sys.path:
    sys.path.insert(0, PLANET)

from arcengine import GameAction, GameState
from agents.agent import Agent

T0 = float(os.environ.get("MIKA_T0", time.time()))
DEADLINE_S = float(os.environ.get("MIKA_DEADLINE_S", 7.5 * 3600))     # stop pressing this long after the notebook started
PRESSES = int(os.environ.get("MIKA_PRESSES", "450"))                   # presses per life
LIVES = int(os.environ.get("MIKA_LIVES", "2"))                         # lives per game (she learns between them)
LOG_DIR = os.environ.get("MIKA_LOG_DIR", "/kaggle/working/mika_logs")
_imp = threading.Lock()
SLOTS = int(os.environ.get("MIKA_SLOTS", str(max(1, (os.cpu_count() or 2)))))
_slots = threading.BoundedSemaphore(SLOTS)                             # games played at once, each in its own process


class MikaAgent(Agent):
    MAX_ACTIONS = 10 ** 7

    def is_done(self, frames, latest_frame) -> bool:
        return True

    def choose_action(self, frames, latest_frame):
        return GameAction.RESET

    def main(self) -> None:
        self.timer = time.time()
        os.makedirs(LOG_DIR, exist_ok=True)
        log_path = os.path.join(LOG_DIR, f"{self.game_id}.log")

        def env_step(act, data):
            raw = self.arc_env.step(act, data=data or {}, reasoning={})
            self.action_counter += 1
            if raw is not None:
                try:
                    self.append_frame(self._convert_raw_frame_data(raw))
                except Exception:
                    pass
            return raw

        try:
            with _slots:
                if time.time() - T0 > DEADLINE_S:
                    return
                with _imp:
                    import mika_bridge
                env = {"MIKA_TMP": os.environ.get("MIKA_TMP", "/tmp"), "MIKA_EYE_SCALE": os.environ.get("MIKA_EYE_SCALE", "1"),
                       "MIKA_SHELL": os.environ.get("MIKA_SHELL", ""), "MIKA_IRRATIONAL": os.environ.get("MIKA_IRRATIONAL", "0"),
                       "MIKA_VOICE4": os.environ.get("MIKA_VOICE4", "0"), "MIKA_VOICE5": os.environ.get("MIKA_VOICE5", "0"), "MIKA_VOICE_IMAGES": os.environ.get("MIKA_VOICE_IMAGES", "1"), "MIKA_ASK_FIRST": os.environ.get("MIKA_ASK_FIRST", "0"), "MIKA_PRISM": os.environ.get("MIKA_PRISM", "0"), "MIKA_QTUBE": os.environ.get("MIKA_QTUBE", "0")}
                mika_bridge.play_in_process(env_step, self.game_id, PRESSES, LIVES, log_path=log_path, env=env,
                                            deadline=T0 + DEADLINE_S)
        except Exception as e:
            try:
                with open(log_path, "a", encoding="utf-8") as fh:
                    fh.write("MIKA AGENT ERROR " + "".join(traceback.format_exception(type(e), e, e.__traceback__))[-3000:] + "\n")
            except Exception:
                pass
        finally:
            self.cleanup()
