"""Hybrid v10b = the v10 notebook (kernel version 9) with the core layer replaced by mika_layer_core_v10b.py:
first sightings are said as "Once so far" (only two agreeing sightings say "Each time"), big things get a short
size-and-colour name instead of a long picture string, only small things count as stepped onto, and a picture
that only moved inside its box is not read as a reshape.

    python build_v10b.py <v10 notebook dir> <out dir>"""
import base64, json, re, sys
from pathlib import Path
HERE = Path(__file__).parent
src, out = Path(sys.argv[1]), Path(sys.argv[2])
j = json.load(open(src / "mika-duck.ipynb"))
cells = j["cells"]
cell = "".join(cells[6]["source"])
old_core = (HERE / "mika_layer_core_v10.py").read_text()
new_core = (HERE / "mika_layer_core_v10b.py").read_text()
compile(new_core, "core", "exec")
b_old = base64.b64encode(old_core.encode()).decode()
assert cell.count(b_old) == 1, "v10 core not found exactly once in cell 6"
cell = cell.replace(b_old, base64.b64encode(new_core.encode()).decode())
cells[6]["source"] = [cell]
head = "".join(cells[0]["source"])
i = head.index("What we add (v10, the core layer)")
head = head[:i] + "What we add (v10b, the core layer)" + head[i + len("What we add (v10, the core layer)"):]
k = head.index("Switch: `MIKA_LAYER`.", i)
head = head[:k] + ("v10b: a law seen once is said as \"once so far\" and only two agreeing sightings make it \"each time\"; "
                   "big things are named by size and colour. ") + head[k:]
cells[0]["source"] = [head]
out.mkdir(parents=True, exist_ok=True)
json.dump(j, open(out / "mika-duck.ipynb", "w"), indent=1)
meta = json.load(open(src / "kernel-metadata.json"))
json.dump(meta, open(out / "kernel-metadata.json", "w"), indent=1)
print("built", out / "mika-duck.ipynb")
