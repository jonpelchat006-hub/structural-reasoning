"""Build the Kaggle notebook for Mika's ARC-AGI-3 agent.

  python3 build_nb.py CLASS VERSION_TAG [MAX_ACTIONS]

Writes kaggle/mika-arc3/{my_agent.py, mika-arc3.ipynb, kernel-metadata.json}. my_agent.py is the
explorer modules joined into one file, with `MikaAgent` = the chosen class; the notebook installs the
competition wheels, writes my_agent.py, and in a competition rerun registers it as "mika" in the
official ARC-AGI-3-Agents runner and plays every hidden game (as the earlier PriorAgent notebook did)."""
import json, os, re, sys, hashlib

ROOT = os.path.dirname(os.path.abspath(__file__))
cls, tag = sys.argv[1], sys.argv[2]
max_actions = int(sys.argv[3]) if len(sys.argv) > 3 else 3000

e1 = open(os.path.join(ROOT, "mika3/explorer.py")).read()
e2 = open(os.path.join(ROOT, "mika3/explorer2.py")).read()
e2 = e2.replace("from mika3.explorer import components, size_bucket  # noqa: F401  (perception shared with v1)\n", "")
e1 = e1.replace("from __future__ import annotations\n", "")
e2 = e2.replace("from __future__ import annotations\n", "")
# v2 defines its own Level / Mind / Mover; keep v1's under other names so both can live in one file
e1 = re.sub(r"\bclass Level\b", "class Level1", e1)
e1 = re.sub(r"\bLevel\(self\.levels_done\)", "Level1(self.levels_done)", e1)
e1 = re.sub(r"\bclass Mind\b", "class Mind1", e1)
e1 = e1.replace("self.mind = Mind(seed=", "self.mind = Mind1(seed=")
header = f'''# =====================================================================
# Mika — ARC-AGI-3 agent (Shovelcat / Vesica AI), build {tag}
# A graph explorer that learns from her own presses, looks back over every won level (the shortest
# route in her own map, what it was made of) and carries the lessons on. Her exploration plan per
# department of games was chosen by students' results on held-out games (solve -> learn -> teach).
# Frames only; CPU only; no game-specific rules.
# =====================================================================
'''
uni = ""
if os.path.exists(os.path.join(ROOT, "mika3/university.py")):
    uni = open(os.path.join(ROOT, "mika3/university.py")).read()
    uni = uni.replace("from __future__ import annotations\n", "").replace("from mika3.explorer2 import Explorer2\n", "")
    for name, var in (("prior_dept.json", "DEPT_PRIOR"), ("curriculum.json", "CURRICULUM")):
        fp = os.path.join(ROOT, "mika3", name)
        lit = json.dumps(json.load(open(fp))) if os.path.exists(fp) else "None"
        uni = uni.replace(f'{var} = _load("{name}")', f"{var} = json.loads({lit!r})" if lit != "None" else f"{var} = None")
src = "from __future__ import annotations\n" + header + e1 + "\n\n# ---------------------------------------------------------------- v2\n" + e2 + \
      "\n\n# ---------------------------------------------------------------- the university\n" + uni + f'''

class MikaAgent({cls}):
    MAX_ACTIONS = {max_actions}
'''
out = os.path.join(ROOT, "kaggle", "mika-arc3"); os.makedirs(out, exist_ok=True)
open(os.path.join(out, "my_agent.py"), "w").write(src)
compile(src, "my_agent.py", "exec")

def code(text, cid):
    return dict(cell_type="code", id=cid, execution_count=None, outputs=[], metadata={}, source=text.splitlines(True))

cells = [
    dict(cell_type="markdown", id="about", metadata={}, source=[
        f"# Mika — ARC-AGI-3 agent ({tag})\n",
        "Graph exploration with a verified movement model (act on a learned rule only while it has reproduced every press; otherwise look).\n",
        "Frames only, CPU only, no game-specific rules. Open source (MIT-0).\n"]),
    code("!pip install --no-index --find-links /kaggle/input/competitions/arc-prize-2026-arc-agi-3/arc_agi_3_wheels arc-agi python-dotenv\n", "install"),
    code("%%writefile /kaggle/working/my_agent.py\n" + src, "agent"),
    code('''import os

if os.getenv('KAGGLE_IS_COMPETITION_RERUN'):
    # Wait for gateway to be ready
    !curl --fail --retry 999 --retry-all-errors --retry-delay 5 \\
          --retry-max-time 600 http://gateway:8001/api/games

    # Copy repo to writable location
    !cp -r /kaggle/input/competitions/arc-prize-2026-arc-agi-3/ARC-AGI-3-Agents \\
           /kaggle/working/ARC-AGI-3-Agents

    # Install our agent
    !cp /kaggle/working/my_agent.py \\
        /kaggle/working/ARC-AGI-3-Agents/agents/templates/my_agent.py

    with open('/kaggle/working/ARC-AGI-3-Agents/agents/__init__.py', 'w') as f:
        f.write(\'\'\'from typing import Type, cast
from dotenv import load_dotenv
from .agent import Agent, Playback
from .swarm import Swarm
from .templates.random_agent import Random
from .templates.my_agent import MikaAgent

load_dotenv()

AVAILABLE_AGENTS: dict[str, Type[Agent]] = {
    "random": Random,
    "mika": MikaAgent,
}
\'\'\')

    with open('/kaggle/working/ARC-AGI-3-Agents/.env', 'w') as f:
        f.write(\'\'\'SCHEME=http
HOST=gateway
PORT=8001
ARC_API_KEY=test-key-123
ARC_BASE_URL=http://gateway:8001/
OPERATION_MODE=online
ENVIRONMENTS_DIR=
RECORDINGS_DIR=/kaggle/working/server_recording
\'\'\')

    # Run the agent against every hidden game
    !cd /kaggle/working/ARC-AGI-3-Agents && \\
        MPLBACKEND=agg \\
        python main.py --agent mika > /kaggle/working/run.log 2>&1; tail -n 40 /kaggle/working/run.log
''', "run"),
    code('''import os
if not os.getenv('KAGGLE_IS_COMPETITION_RERUN'):
    # Non-competition mode: produce a dummy submission
    import pandas as pd
    submission = pd.DataFrame(
        data=[['1_0', '1', True, 1]],
        columns=['row_id', 'game_id', 'end_of_game', 'score'])
    submission.to_parquet('/kaggle/working/submission.parquet', index=False)
    submission.head()
''', "dummy"),
]
nb = dict(cells=cells, metadata={"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
          "language_info": {"name": "python", "version": "3.12"},
          "kaggle": {"accelerator": "none", "isInternetEnabled": False, "language": "python", "sourceType": "notebook", "isGpuEnabled": False},
          "mika": {"build": tag, "class": cls, "max_actions": max_actions, "source_sha256": hashlib.sha256(src.encode()).hexdigest()}},
          nbformat=4, nbformat_minor=5)
json.dump(nb, open(os.path.join(out, "mika-arc3.ipynb"), "w"), indent=1)
meta = {"id": "jonpelchat/mika-arc-agi-3", "title": "Mika ARC-AGI-3", "code_file": "mika-arc3.ipynb", "language": "python",
        "kernel_type": "notebook", "is_private": True, "enable_gpu": False, "enable_tpu": False, "enable_internet": False,
        "keywords": [], "dataset_sources": [], "kernel_sources": [], "competition_sources": ["arc-prize-2026-arc-agi-3"],
        "model_sources": []}
json.dump(meta, open(os.path.join(out, "kernel-metadata.json"), "w"), indent=2)
print("built", out, len(src), "chars; sha256", nb["metadata"]["mika"]["source_sha256"][:16])
