"""Layer-off baseline = the v10b notebook (kernel version 10) with MIKA_LAYER = False: Franzen's M2 + our header,
the startup guard and the keep-alive only. Measures our notebook's own hidden-set score, so the core layer's worth
is v10b minus this.

    python build_off.py <v10b notebook dir> <out dir>"""
import json, sys
from pathlib import Path
src, out = Path(sys.argv[1]), Path(sys.argv[2])
j = json.load(open(src / "mika-duck.ipynb"))
cells = j["cells"]
cell = "".join(cells[6]["source"])
assert cell.count("MIKA_LAYER = True\n") == 1
cells[6]["source"] = [cell.replace("MIKA_LAYER = True\n", "MIKA_LAYER = False\n", 1)]
head = "".join(cells[0]["source"])
assert head.count("Switch: `MIKA_LAYER`.") == 1
head = head.replace("Switch: `MIKA_LAYER`.", "Switch: `MIKA_LAYER` (**off in this version**).")
i = head.index("**What we add")
head = (head[:i] + "**This version: the layer is off** (startup guard and keep-alive only), to measure the notebook's own "
        "baseline on the hidden set; the version with the layer on is kernel version 10.\n\n" + head[i:])
cells[0]["source"] = [head]
out.mkdir(parents=True, exist_ok=True)
json.dump(j, open(out / "mika-duck.ipynb", "w"), indent=1)
json.dump(json.load(open(src / "kernel-metadata.json")), open(out / "kernel-metadata.json", "w"), indent=1)
print("built", out / "mika-duck.ipynb")
