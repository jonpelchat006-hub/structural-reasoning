"""Build a Submission, export impl n = F(n) for each n, run the page-fault timer natively (no valgrind).
usage: pfrun.py SUB.lean n1,n2,... [reps] [--keep DIR] """
import os, subprocess, sys, re, statistics
from pathlib import Path
sys.set_int_max_str_digits(0)
sys.path.insert(0, "/home/claude/fibvar")
import planner as pl
WORK = Path("/home/claude/lkc/problems/fib")
TPF = Path("/home/claude/timer-pf/.lake/build/bin/kernel")
EXPORT = Path("/home/claude/repro/lean4export/.lake/build/bin/lean4export")
ENV = dict(os.environ, PATH=f"{Path.home()}/.elan/bin:" + os.environ.get("PATH", ""))
sub, NS = Path(sys.argv[1]).read_text(), [int(x) for x in sys.argv[2].split(",")]
reps = int(sys.argv[3]) if len(sys.argv) > 3 else 3
(WORK / "Submission.lean").write_text(sub)
r = subprocess.run(["lake", "build", "Submission"], cwd=WORK, capture_output=True, text=True, env=ENV)
if r.returncode: print(r.stdout[-3000:]); sys.exit(1)
perf = ["import Submission", "import Lean", "set_option maxRecDepth 4000000", "set_option maxHeartbeats 0",
        "open Lean Meta Elab in", "run_meta do"]
for i, n in enumerate(NS):
    v = pl.fib_pair(n)[0]
    perf += [f"  Lean.addDecl (.thmDecl {{ name := `Bench.q{i}, levelParams := [], "
             f"type := ← mkEq (Lean.mkApp (Lean.mkConst ``Submission.impl) (Lean.mkNatLit {n})) (Lean.mkNatLit {v}), "
             f"value := ← mkEqRefl (Lean.mkNatLit {v}) }})"]
(WORK / "PerfQ.lean").write_text("\n".join(perf) + "\n")
r = subprocess.run(["lake", "env", "lean", "-o", ".lake/build/lib/lean/PerfQ.olean", "PerfQ.lean"], cwd=WORK,
                   capture_output=True, text=True, timeout=7200, env=ENV)
if r.returncode: print(r.stdout[-2000:], r.stderr[-2000:]); sys.exit(1)
for i, n in enumerate(NS):
    exp = Path(f"/tmp/pfq_{i}.ndjson")
    with open(exp, "w") as f:
        subprocess.run(["lake", "env", str(EXPORT), "PerfQ", "--", f"Bench.q{i}"], cwd=WORK, stdout=f,
                       stderr=subprocess.PIPE, text=True, timeout=3600, env=ENV)
    rows = []
    for _ in range(reps):
        p = subprocess.run([str(TPF), "--count-instructions", "--target", f"Bench.q{i}", str(exp)],
                           capture_output=True, text=True, timeout=600, env=ENV)
        m = re.search(r"WINDOW pf=(\d+) minflt=(\d+) majflt=(\d+) task_ns=(\d+) wall_ns=(\d+)", p.stderr)
        rows.append(tuple(int(x) for x in m.groups()) if m else None)
    ok = [r for r in rows if r]
    print(n, "pf", [r[0] for r in ok], "task_us", [r[3] // 1000 for r in ok], flush=True)
