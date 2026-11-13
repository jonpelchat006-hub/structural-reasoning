"""Hybrid v10d = the v10c notebook (kernel version 12) with the layer replaced by mika_layer_core_v10d.py: adds
Jonathan's wall note (a direction press absorbed by a wall is not a dead button; a click on empty floor or on a thing
that does not react does not mean clicks do nothing).

    python build_v10d.py <v10c notebook dir> <out dir>"""
import base64, json, sys
from pathlib import Path
HERE = Path(__file__).parent
src, out = Path(sys.argv[1]), Path(sys.argv[2])
j = json.load(open(src / "mika-duck.ipynb"))
cells = j["cells"]
cell = "".join(cells[6]["source"])
assert "MIKA_LAYER = True\n" in cell
old_core = (HERE / "mika_layer_core_v10c.py").read_text()
new_core = (HERE / "mika_layer_core_v10d.py").read_text()
compile(new_core, "core", "exec")
b_old = base64.b64encode(old_core.encode()).decode()
assert cell.count(b_old) == 1, "v10c core not found exactly once in cell 6"
cells[6]["source"] = [cell.replace(b_old, base64.b64encode(new_core.encode()).decode())]
head = "".join(cells[0]["source"])
old = "What we add (v10c, the core layer and Jonathan's notes)"
assert head.count(old) == 1
head = head.replace(old, "What we add (v10d, the core layer and Jonathan's notes)")
k = head.index("Switch: `MIKA_LAYER`.")
head = head[:k] + ("v10d adds his note on walls: walls absorb moves and make a press look like it did nothing, so a "
                   "direction press the body did not move on is named as absorbed by a wall (with the wall's place), not a "
                   "dead button; a click on empty floor or on a thing that does not react is named the same way. ") + head[k:]
cells[0]["source"] = [head]
out.mkdir(parents=True, exist_ok=True)
json.dump(j, open(out / "mika-duck.ipynb", "w"), indent=1)
json.dump(json.load(open(src / "kernel-metadata.json")), open(out / "kernel-metadata.json", "w"), indent=1)
print("built", out / "mika-duck.ipynb")
