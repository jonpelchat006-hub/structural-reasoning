r"""Hourly: copy new/changed source files into Mika's library, digest them, and rebuild the spiral only if
something changed (or the index is a day old). Run by the Windows scheduled task "Mika library hourly" with
pythonw.exe, so no window opens. Output goes to D:\planet\mika\library_hourly.log."""
import os, sys, time, runpy, traceback, warnings, ctypes

LOG = r"D:\planet\mika\library_hourly.log"
HERE = r"C:\Users\GamerTech\Desktop\Vesica AI\AI Detector\planet"

try:   # keep the log small: when it passes 1 MB keep the newest half
    if os.path.exists(LOG) and os.path.getsize(LOG) > 1_000_000:
        with open(LOG, encoding="utf-8", errors="replace") as fh: tail = fh.read()[-500_000:]
        with open(LOG, "w", encoding="utf-8") as fh: fh.write(tail)
except Exception: pass

try: ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x4000)  # below normal
except Exception: pass

warnings.filterwarnings("ignore")
with open(LOG, "a", encoding="utf-8") as fh:
    sys.stdout = sys.stderr = fh
    print(f"=== {time.strftime('%Y-%m-%d %H:%M')} hourly ingest", flush=True)
    os.chdir(HERE); sys.path.insert(0, HERE)
    sys.argv = ["living_library.py", "ingest", "--lazy"]
    try: runpy.run_path(os.path.join(HERE, "living_library.py"), run_name="__main__")
    except SystemExit: pass
    except Exception: traceback.print_exc()
    fh.flush()
