"""Turn otherwise-unreported game-thread crashes into a failed process.

The official Swarm joins workers but does not propagate their exceptions.
This wrapper preserves its transport/scorecard flow and captures thread errors.
"""
from contextlib import contextmanager
import runpy
import sys
import threading


@contextmanager
def checked_threads():
    errors = []
    lock = threading.Lock()
    previous = threading.excepthook

    def capture(args):
        with lock:
            errors.append(f'{args.thread.name}: {args.exc_type.__name__}: {args.exc_value}')
        previous(args)

    threading.excepthook = capture
    try:
        yield
        if errors:
            raise RuntimeError('Game runner thread failure(s): ' + '; '.join(errors))
    finally:
        threading.excepthook = previous


def run_in_worker(call):
    """Local comparisons must reproduce constructor/worker thread separation."""
    with checked_threads():
        thread = threading.Thread(target=call, name='comparison-game-worker')
        thread.start()
        thread.join()


if __name__ == '__main__':
    target = sys.argv[1]
    sys.argv = sys.argv[1:]
    with checked_threads():
        runpy.run_path(target, run_name='__main__')
