"""Measure Submission.impl n = F(n) in the judge's window (callgrind) using a given lake project dir.
usage: measure_impl.py WORKDIR n1,n2,... OUT.json   (WORKDIR's Submission must already be built)"""
import os, subprocess, sys, json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
sys.set_int_max_str_digits(0)
sys.path.insert(0, "/home/claude/fibvar")
import planner as pl
WORK = Path(sys.argv[1]); NS = [int(x) for x in sys.argv[2].split(",")]; OUT = sys.argv[3]
TIMER_VG = Path("/home/claude/timer-vg/.lake/build/bin/kernel")
EXPORT = Path("/home/claude/repro/lean4export/.lake/build/bin/lean4export")
ENV = dict(os.environ, PATH=f"{Path.home()}/.elan/bin:" + os.environ.get("PATH", ""))
tag = WORK.name
perf = ["import Submission", "import Lean", "set_option maxRecDepth 4000000", "set_option maxHeartbeats 0",
        "open Lean Meta Elab in", "run_meta do"]
for i, n in enumerate(NS):
    v = pl.fib_pair(n)[0]
    perf += [f"  Lean.addDecl (.thmDecl {{ name := `Bench.m{i}, levelParams := [], "
             f"type := ← mkEq (Lean.mkApp (Lean.mkConst ``Submission.impl) (Lean.mkNatLit {n})) (Lean.mkNatLit {v}), "
             f"value := ← mkEqRefl (Lean.mkNatLit {v}) }})"]
(WORK / "PerfM.lean").write_text("\n".join(perf) + "\n")
r = subprocess.run(["lake", "env", "lean", "-o", ".lake/build/lib/lean/PerfM.olean", "PerfM.lean"], cwd=WORK,
                   capture_output=True, text=True, timeout=7200, env=ENV)
if r.returncode: print(r.stdout[-2000:], r.stderr[-2000:]); sys.exit(1)
def one(i):
    exp = WORK / f"pm_{i}.ndjson"
    with open(exp, "w") as f:
        subprocess.run(["lake", "env", str(EXPORT), "PerfM", "--", f"Bench.m{i}"], cwd=WORK, stdout=f,
                       stderr=subprocess.PIPE, text=True, timeout=3600, env=ENV)
    cg = f"/tmp/pm_{tag}_{i}.out"
    for g in Path("/tmp").glob(f"pm_{tag}_{i}.out*"): g.unlink()
    subprocess.run(["valgrind", "--tool=callgrind", "--collect-atstart=no", f"--callgrind-out-file={cg}",
                    str(TIMER_VG), "--count-instructions", "--target", f"Bench.m{i}", str(exp)],
                   capture_output=True, text=True, timeout=3600, env=ENV)
    total = None
    for g in Path("/tmp").glob(f"pm_{tag}_{i}.out.*"):
        t = g.read_text(errors="ignore")
        if "replay-window" in t:
            for l in t.splitlines():
                if l.startswith("summary:"): total = int(l.split()[1])
        g.unlink()
    exp.unlink()
    return NS[i], total
res = {}
with ThreadPoolExecutor(max_workers=int(os.environ.get("WORKERS", "2"))) as ex:
    for n, t in ex.map(one, range(len(NS))):
        res[n] = t; print(n, t, flush=True)
json.dump(res, open(OUT, "w"), indent=1)
