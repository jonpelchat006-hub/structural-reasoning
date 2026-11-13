"""Build the hybrid notebook: Franzen's M2 notebook + our header + smoke-run hook + the Mika layer cell.

    python build_hybrid_nb.py <franzen_m2.ipynb> <out_dir> [--no-layer]"""
import base64, json, sys
from pathlib import Path
HERE = Path(__file__).parent
src, out = Path(sys.argv[1]), Path(sys.argv[2])
layer = "--no-layer" not in sys.argv
j = json.load(open(src))
cells = j["cells"]
head = """### Mika × Duck: the hybrid (Jonathan Pelchat, Shovelcat)

This notebook is **[Daniel Franzen's Milestone 2 solution](https://www.kaggle.com/code/dfranzen/arc-agi-3-milestone-2-solution)**, built on **[Tufa Labs' Duck harness](https://www.kaggle.com/code/jeroencottaar/tufa-labs-duck-harness-june-30-milestone-winner)** (Jeroen Cottaar). The model, inference engine, harness patch and prompts are theirs; full credit goes to them and to the people they credit below.

**What we add:** Mika's planes as an evidence layer for the model (cell 0b): facts computed from the frames (what each key did, boards already seen, the step bar, what the last level's winning press changed and where its before-picture fits now), never written by the model itself, added as at most a few short lines after the valid-actions line. Switch: `MIKA_LAYER`.

**Save & Run** plays a short smoke run on 3 public games; the competition rerun plays every game exactly as the original, plus the layer.

---

"""
cells[0]["source"] = [head + "*The original notes follow.*\n\n" + "".join(cells[0]["source"])]
hook = "".join(cells[16]["source"])
old = "bm.n_passes = 4\nbm.game_weights = None\n\ndemo_excluded_games = [] if TRUE_SUBMISSION else []\n"
assert old in hook
new = ("bm.n_passes = 1\nbm.game_weights = None\n\n"
       "# Save & Run: a short smoke run on a few public games (the competition rerun is unchanged)\n"
       "SMOKE_GAMES = ['ls20', 'vc33', 'ft09']\n"
       "ALL_PUBLIC = ['ar25','bp35','cd82','cn04','dc22','ft09','g50t','ka59','lf52','lp85','ls20','m0r0','r11l',\n"
       "              're86','s5i5','sb26','sc25','sk48','sp80','su15','tn36','tr87','tu93','vc33','wa30']\n"
       "demo_excluded_games = [] if TRUE_SUBMISSION else [g for g in ALL_PUBLIC if g not in SMOKE_GAMES]\n")
hook = hook.replace(old, new)
tail = "# show config\nprint('benchmark.solver:', bm.solver)"
assert tail in hook
hook = hook.replace(tail, "# Save & Run: give each smoke game enough play time after the ~12 minutes the server takes to start\n"
                    "SMOKE_MINUTES = 30\n"
                    "if not TRUE_SUBMISSION:\n"
                    "    bm.solver.max_runtime_s_per_game = SMOKE_MINUTES * 60\n\n" + tail)
cells[16]["source"] = [hook]
core = (HERE / "mika_layer_core.py").read_text(); inst = (HERE / "install_mika_layer.py").read_text()
compile(core, "core", "exec"); compile(inst, "inst", "exec")
cell = f'''# ## 0b. Mika's evidence layer (switch: MIKA_LAYER)
# If an anchor in the harness does not match exactly once, nothing is changed and the notebook runs as the original.
import base64, os
from pathlib import Path
MIKA_LAYER = {layer}
_ok = False
try:
    Path("/tmp/mika_layer_core.py").write_text(base64.b64decode("{base64.b64encode(core.encode()).decode()}").decode())
    _ns = {{"__name__": "mika_install"}}
    exec(compile(base64.b64decode("{base64.b64encode(inst.encode()).decode()}").decode(), "install_mika_layer.py", "exec"), _ns)
    if MIKA_LAYER:
        _ok = _ns["install_safe"](BUNDLE_DIR / "src" / "ARC3-Inference" / "inference" / "agent", "/tmp/mika_layer_core.py")
except Exception as _exc:
    print("mika layer: setup failed:", _exc)
os.environ["ARC3_MIKA_LAYER"] = "1" if _ok else "0"
os.environ["ARC3_MIKA_MAX_LINES"] = "3"
os.environ["ARC3_MIKA_LOG"] = "" if TRUE_SUBMISSION else str(WORKING_DIR / "mika_layer_log.jsonl")
print("mika layer:", "on" if _ok else "off")

# Startup guard (Oct 24): on a slow-disk machine the 185 GB checkpoint precache took 43 minutes instead of 12, every
# game spent its 15-minute grace plus 10 retries before the server was up, gave up, and the run scored 0. Give each
# game's first request up to 75 minutes, and allow more consecutive failures, so a slow load only costs time.
os.environ["ARC3_HTTP_RETRY_INITIAL_SECONDS"] = "4500"
os.environ["ARC3_MAX_ANALYZER_FAILURES"] = "40"
print("startup guard: first-request grace", os.environ["ARC3_HTTP_RETRY_INITIAL_SECONDS"], "s, max failures", os.environ["ARC3_MAX_ANALYZER_FAILURES"])
'''
assert 'git", "apply"' in "".join(cells[4]["source"])
cells.insert(5, {"cell_type": "markdown", "metadata": {}, "source": ["## 0b. Mika's evidence layer\n\nFacts computed from the frames by Mika's planes, handed to the model as a few short notes. Switch: `MIKA_LAYER`."]})
cells.insert(6, {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": [cell]})
out.mkdir(parents=True, exist_ok=True)
json.dump(j, open(out / "mika-duck.ipynb", "w"), indent=1)
print("built", out / "mika-duck.ipynb", len(cells), "cells; layer", layer)
