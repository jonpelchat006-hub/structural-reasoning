"""Startup keep-alive for the Duck harness in the competition rerun.

Why: in a rerun every game shares one competition scorecard, and the competition server (arc_agi's own API server)
auto-closes a scorecard that has had no action for STALE_MINUTES (default 15). A closed scorecard is final: the
submission is scored as it stands (0 if nothing was won yet) and only one scorecard may ever be opened.

The notebook releases the games 12 minutes after it starts, with the model server possibly still loading, and the first
game makes one free RESET ("warmup") so the scorecard has an action. On a slow-disk machine the server is ready only
27-47 minutes after the start, so more than 15 minutes pass without a single action and the scorecard closes.

Fix: the warmup game repeats its free level-start RESET every ARC3_KEEPALIVE_SECONDS (240) until any game has made a
real move (or ARC3_KEEPALIVE_MAX_SECONDS, 5400, have passed). A RESET at a level's first action does not step the game
in competition mode; it only refreshes the scorecard (and counts one action on that game's first level).

Two anchored edits to inference/framework/solver.py, each anchor must match exactly once and the patched file must
compile, otherwise nothing changes. Never raises.

    python install_keepalive.py <path to ARC3-Inference/inference/framework>"""
import sys
from pathlib import Path

ANCHOR_WARMUP = ('                run.game_id,\n'
                 '            )\n'
                 '            self._execute_auto_reset()\n'
                 '        try:\n')
NEW_WARMUP = ('                run.game_id,\n'
              '            )\n'
              '            self._execute_auto_reset()\n'
              '            _keepalive_until_first_move(self)\n'
              '        try:\n')
ANCHOR_MOVE = ('        new_state = self.game.execute_action(\n'
               '            action, generated_tokens=generated_tokens, uncached_input_tokens=0\n'
               '        )\n')
NEW_MOVE = ANCHOR_MOVE + ('        if not automatic:\n'
                          '            _FIRST_MOVE.set()\n')
FUNC = '''

# --- startup keep-alive (install_keepalive.py) ---
_FIRST_MOVE = threading.Event()


def _keepalive_until_first_move(session) -> None:
    """Repeat the warmup game's free RESET until some game has made a real move, so the shared competition scorecard
    never sits idle long enough to be auto-closed while the model server is still loading."""
    try:
        interval = float(os.environ.get("ARC3_KEEPALIVE_SECONDS", "240"))
        cap = float(os.environ.get("ARC3_KEEPALIVE_MAX_SECONDS", "5400"))
        if interval <= 0:
            return
        t0 = time.monotonic()
        n = 0
        while time.monotonic() - t0 < cap:
            if _FIRST_MOVE.wait(interval):
                break
            if session.should_stop():
                break
            session._execute_auto_reset()
            n += 1
            log.warning("%s: keep-alive RESET %d (no game has moved yet, %.0f s after the warmup)",
                        session.game.game_run.game_id, n, time.monotonic() - t0)
        if n:
            log.warning("keep-alive: %d RESETs, ended after %.0f s", n, time.monotonic() - t0)
    except Exception as exc:
        log.warning("keep-alive stopped: %r", exc)
'''


def install(framework_dir):
    sv = Path(framework_dir) / "solver.py"
    src = sv.read_text()
    if "_keepalive_until_first_move" in src:
        print("keep-alive: already installed"); return True
    if src.count(ANCHOR_WARMUP) != 1 or src.count(ANCHOR_MOVE) != 1:
        print(f"keep-alive: anchors not unique ({src.count(ANCHOR_WARMUP)}, {src.count(ANCHOR_MOVE)}); NOT installed")
        return False
    for name in ("import os\n", "import threading\n", "import time\n", "\nlog = logging.getLogger(__name__)\n"):
        if name not in src:
            print(f"keep-alive: solver.py lacks {name.strip()!r}; NOT installed"); return False
    new = src.replace(ANCHOR_WARMUP, NEW_WARMUP, 1).replace(ANCHOR_MOVE, NEW_MOVE, 1) + FUNC
    try:
        compile(new, str(sv), "exec")
    except Exception as exc:
        print(f"keep-alive: patched file does not compile ({exc}); NOT installed")
        return False
    sv.write_text(new)
    print("keep-alive: installed")
    return True


def install_safe(framework_dir):
    try:
        return install(framework_dir)
    except Exception as exc:
        print(f"keep-alive: install failed ({exc}); NOT installed")
        return False


if __name__ == "__main__":
    sys.exit(0 if install(sys.argv[1]) else 1)
