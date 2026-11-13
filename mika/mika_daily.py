r"""Mika's daily ARC session (replaces the cloud "ARC daily practice + try", which is paused).
Run by the Windows scheduled task "Mika ARC daily" with pythonw.exe. For each game she plays a couple of lives
with mika_mind.py (her journal, routes, reflection), then one line per game goes to D:\planet\mika\daily_history.jsonl.
Full output: D:\planet\mika\daily\<date>.log. Nothing here trades, spends or deletes anything."""
import json, os, subprocess, sys, time

PY = r"C:\Users\GamerTech\AppData\Local\Python\pythoncore-3.14-64\python.exe"   # the python with torch
PLANET = r"C:\Users\GamerTech\Desktop\Vesica AI\AI Detector\planet"
HOME = r"D:\planet\mika"
# each game: one PUSH life (walk her routes, then work on the level she is stuck on) and one STUDY life
# (look around level 1 for a while, reset, then walk her route; the trimmed route gets its try here too).
# Lives run one after another: two games open at once on the same key close each other's scorecard.
GAMES = [("sp80", "300"), ("ls20", "400")]
MODES = ["push", "study"]

os.makedirs(os.path.join(HOME, "daily"), exist_ok=True)
day = time.strftime("%Y-%m-%d")
log_path = os.path.join(HOME, "daily", f"{day}.log")
env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONWARNINGS="ignore")


def journal(game):
    try:
        with open(os.path.join(HOME, f"{game}.json"), encoding="utf-8") as fh: return json.load(fh)
    except Exception: return {}


def ensure_ollama(log):
    """her reflection runs on the local models; start Ollama quietly if it is not up"""
    import urllib.request
    def up():
        try: urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=3); return True
        except Exception: return False
    if up(): return
    exe = os.path.expandvars(r"%LOCALAPPDATA%\Programs\Ollama\ollama.exe")
    if not os.path.exists(exe): log.write("ollama not found; she plays without reflection\n"); return
    e = dict(os.environ)
    try:                                   # the models live where the user variable says (the colony's L4 zone)
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k: e["OLLAMA_MODELS"] = winreg.QueryValueEx(k, "OLLAMA_MODELS")[0]
    except Exception: pass
    subprocess.Popen([exe, "serve"], env=e, creationflags=0x08000000 | 0x00000008, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(30):
        time.sleep(2)
        if up(): log.write("started ollama for her reflection\n"); return
    log.write("ollama did not come up; she plays without reflection\n")


with open(log_path, "a", encoding="utf-8") as log:
    ensure_ollama(log)
    for game, PRESSES in GAMES:
      for mode in MODES:
        before = len(journal(game).get("lives", []))
        log.write(f"\n=== {time.strftime('%H:%M')} {game}: one {mode} life, {PRESSES} presses\n"); log.flush()
        t0 = time.time()
        try:
            rc = subprocess.run([PY, "-W", "ignore", "mika_mind.py", game, "--lives", "1", "--presses", PRESSES, "--mode", mode],
                                cwd=PLANET, stdout=log, stderr=subprocess.STDOUT, env=env, timeout=3 * 3600,
                                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)).returncode
        except subprocess.TimeoutExpired: rc = "timeout"
        j = journal(game)
        new = j.get("lives", [])[before:]
        row = {"date": day, "game": game, "mode": mode, "rc": rc, "minutes": round((time.time() - t0) / 60, 1),
               "lives": [{"levels": l.get("levels"), "presses": l.get("presses"), "route_log": l.get("route_log"),
                          "weigh": len(l.get("weigh_log") or []), "detours": len(l.get("detours") or []),
                          "trim": l.get("trim_log"), "surprises": len(l.get("surprise_log") or [])} for l in new],
               "routes": {k: v.get("len") for k, v in j.get("routes", {}).items()}}
        with open(os.path.join(HOME, "daily_history.jsonl"), "a", encoding="utf-8") as fh: fh.write(json.dumps(row) + "\n")
        log.write(f"=== {game} {mode} done: {json.dumps(row)}\n"); log.flush()
