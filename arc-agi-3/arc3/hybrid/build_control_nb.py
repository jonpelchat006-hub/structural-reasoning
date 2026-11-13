"""Control notebook: Daniel Franzen's Milestone 2 solution, unchanged in the competition rerun.
Only the header and a shorter Save & Run (3 public games, 30 minutes each) differ.

    python build_control_nb.py <franzen_m2.ipynb> <out_dir>"""
import json, sys
from pathlib import Path
src, out = Path(sys.argv[1]), Path(sys.argv[2])
j = json.load(open(src))
cells = j["cells"]
head = """### Control copy: Daniel Franzen's Milestone 2 solution (unchanged rerun)

This is **[Daniel Franzen's Milestone 2 solution](https://www.kaggle.com/code/dfranzen/arc-agi-3-milestone-2-solution)**, built on **[Tufa Labs' Duck harness](https://www.kaggle.com/code/jeroencottaar/tufa-labs-duck-harness-june-30-milestone-winner)** (Jeroen Cottaar). All credit goes to them and to the people they credit below.

It is submitted as a **control**: the competition rerun path is byte-for-byte the original. The only change is that an interactive **Save & Run** plays a short smoke run on 3 public games instead of the full public set.

---

"""
cells[0]["source"] = [head + "*The original notes follow.*\n\n" + "".join(cells[0]["source"])]
hook = "".join(cells[16]["source"])
old = "bm.n_passes = 4\nbm.game_weights = None\n\ndemo_excluded_games = [] if TRUE_SUBMISSION else []\n"
assert old in hook
new = ("bm.n_passes = 4\nbm.game_weights = None\n\n"
       "# Save & Run only: a short smoke run on a few public games (the competition rerun is unchanged)\n"
       "SMOKE_GAMES = ['ls20', 'vc33', 'ft09']\n"
       "ALL_PUBLIC = ['ar25','bp35','cd82','cn04','dc22','ft09','g50t','ka59','lf52','lp85','ls20','m0r0','r11l',\n"
       "              're86','s5i5','sb26','sc25','sk48','sp80','su15','tn36','tr87','tu93','vc33','wa30']\n"
       "demo_excluded_games = [] if TRUE_SUBMISSION else [g for g in ALL_PUBLIC if g not in SMOKE_GAMES]\n"
       "if not TRUE_SUBMISSION:\n"
       "    bm.n_passes = 1\n")
hook = hook.replace(old, new)
tail = "# show config\nprint('benchmark.solver:', bm.solver)"
assert tail in hook
hook = hook.replace(tail, "# Save & Run only: give each smoke game enough play time after the server starts\n"
                    "SMOKE_MINUTES = 30\n"
                    "if not TRUE_SUBMISSION:\n"
                    "    bm.solver.max_runtime_s_per_game = SMOKE_MINUTES * 60\n\n" + tail)
cells[16]["source"] = [hook]
out.mkdir(parents=True, exist_ok=True)
json.dump(j, open(out / "franzen-control.ipynb", "w"), indent=1)
print("built", out / "franzen-control.ipynb", len(cells), "cells")
