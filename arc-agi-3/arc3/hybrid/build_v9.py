"""Hybrid v9 = the notebook submitted as mika-duck-hybrid version 7 (v8f: layer v8 + startup guard) + the startup
keep-alive (install_keepalive.py), which keeps the shared competition scorecard from being auto-closed while the model
server is still loading on a slow-disk machine.

    python build_v9.py <v8f notebook> <out_dir> [--no-layer]"""
import base64, json, sys
from pathlib import Path
HERE = Path(__file__).parent
src, out = Path(sys.argv[1]), Path(sys.argv[2])
no_layer = "--no-layer" in sys.argv
j = json.load(open(src))
cells = j["cells"]

head = "".join(cells[0]["source"])
old_guard = head[head.index("**Startup guard:**"):head.index("**Save & Run**")]
new_guard = (
    "**Startup guard and keep-alive:** each game waits up to 75 minutes for the model server on its first request, "
    "and until some game has made its first real move, the warmup game repeats its free level-start RESET every 4 minutes. "
    "In the competition rerun all games share one scorecard, and the competition server closes a scorecard that has seen "
    "no action for 15 minutes; on a slow-disk machine the model server comes up 27-47 minutes after the notebook starts, "
    "the games are released at 12 minutes, so without the keep-alive the scorecard is closed before the first move and "
    "the whole run scores 0.\n\n")
head = head.replace(old_guard, new_guard)
if no_layer:
    head = head.replace("Switch: `MIKA_LAYER`.", "Switch: `MIKA_LAYER` (**off in this version**).")
cells[0]["source"] = [head]

cell = "".join(cells[6]["source"])
assert cell.startswith("# ## 0b. Mika's evidence layer") and "MIKA_LAYER = True\n" in cell
if no_layer:
    cell = cell.replace("MIKA_LAYER = True\n", "MIKA_LAYER = False\n", 1)
ka = (HERE / "install_keepalive.py").read_text()
compile(ka, "install_keepalive.py", "exec")
cell = cell.rstrip("\n") + f'''

# Startup keep-alive (Oct 26): the competition server auto-closes the shared scorecard after 15 minutes without an action.
# Until some game has made a real move, the warmup game repeats its free level-start RESET every 4 minutes.
KEEPALIVE = True
os.environ["ARC3_KEEPALIVE_SECONDS"] = "240" if KEEPALIVE else "0"
os.environ["ARC3_KEEPALIVE_MAX_SECONDS"] = "5400"
_ka = False
try:
    _ns2 = {{"__name__": "keepalive_install"}}
    exec(compile(base64.b64decode("{base64.b64encode(ka.encode()).decode()}").decode(), "install_keepalive.py", "exec"), _ns2)
    if KEEPALIVE:
        _ka = _ns2["install_safe"](BUNDLE_DIR / "src" / "ARC3-Inference" / "inference" / "framework")
except Exception as _exc:
    print("keep-alive: setup failed:", _exc)
print("startup keep-alive:", "on" if _ka else "off")
'''
cells[6]["source"] = [cell]
out.mkdir(parents=True, exist_ok=True)
json.dump(j, open(out / "mika-duck.ipynb", "w"), indent=1)
print("built", out / "mika-duck.ipynb", len(cells), "cells; layer", not no_layer)
