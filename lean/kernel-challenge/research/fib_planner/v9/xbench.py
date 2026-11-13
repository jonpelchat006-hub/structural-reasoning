#!/usr/bin/env python3
"""Generic kernel-window bench: defs `Submission.x<i> : Nat → Nat` with bodies in `n`, one theorem
`x<i> n = v` each, exported and replayed in the judge's timer kernel under callgrind.
Usage from Python: xbench.run([(name, body, n, v), ...], extra_defs="") -> {name: Ir}"""
import json, os, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
sys.set_int_max_str_digits(0)
sys.path.insert(0, "/home/claude/fibvar")
import planner as pl
WORK = Path("/home/claude/lkc/problems/fib")
TIMER_VG = Path("/home/claude/timer-vg/.lake/build/bin/kernel")
EXPORT = Path("/home/claude/repro/lean4export/.lake/build/bin/lean4export")
ENV = dict(os.environ, PATH=f"{Path.home()}/.elan/bin:" + os.environ.get("PATH", ""))

def window(exp, tag, keep=None):
    out = f"/tmp/xb_{tag}.out"
    for f in Path("/tmp").glob(f"xb_{tag}.out*"): f.unlink()
    subprocess.run(["valgrind", "--tool=callgrind", "--collect-atstart=no", f"--callgrind-out-file={out}",
                    str(TIMER_VG), "--count-instructions", "--target", tag, str(exp)],
                   capture_output=True, text=True, timeout=3600, env=ENV)
    for f in Path("/tmp").glob(f"xb_{tag}.out.*"):
        txt = f.read_text(errors="ignore")
        if "replay-window" in txt:
            for l in txt.splitlines():
                if l.startswith("summary:"):
                    if keep: Path(keep).write_text(txt)
                    return int(l.split()[1])
    return None

def run(cases, extra_defs="", workers=4, keep_dir=None, header=None):
    src = [header or pl.HEADER, extra_defs]
    for i, (name, body, n, v) in enumerate(cases):
        src.append(f"set_option exponentiation.threshold 100000 in\ndef x{i} (n : Nat) : Nat :=\n  {body}\n")
    src.append("end Submission\n")
    (WORK / "Submission.lean").write_text("\n".join(src))
    r = subprocess.run(["lake", "build", "Submission"], cwd=WORK, capture_output=True, text=True, env=ENV)
    if r.returncode: print(r.stdout[-4000:]); raise SystemExit(1)
    perf = ["import Submission", "import Lean", "set_option maxRecDepth 4000000", "set_option maxHeartbeats 0",
            "open Lean Meta Elab in", "run_meta do"]
    for i, (name, body, n, v) in enumerate(cases):
        perf += [f"  Lean.addDecl (.thmDecl {{ name := `Bench.x{i}, levelParams := [], "
                 f"type := ← mkEq (Lean.mkApp (Lean.mkConst ``Submission.x{i}) (Lean.mkNatLit {n})) (Lean.mkNatLit {v}), "
                 f"value := ← mkEqRefl (Lean.mkNatLit {v}) }})"]
    (WORK / "PerfX.lean").write_text("\n".join(perf) + "\n")
    r = subprocess.run(["lake", "env", "lean", "-o", ".lake/build/lib/lean/PerfX.olean", "PerfX.lean"], cwd=WORK,
                       capture_output=True, text=True, timeout=7200, env=ENV)
    if r.returncode: print(r.stdout[-3000:], r.stderr[-3000:]); raise SystemExit(1)
    def one(i):
        exp = WORK / f"px_{i}.ndjson"
        with open(exp, "w") as f:
            subprocess.run(["lake", "env", str(EXPORT), "PerfX", "--", f"Bench.x{i}"], cwd=WORK,
                           stdout=f, stderr=subprocess.PIPE, text=True, timeout=3600, env=ENV)
        keep = f"{keep_dir}/x{i}.cg" if keep_dir else None
        w = window(exp, f"Bench.x{i}", keep); exp.unlink(); return i, w
    res = {}
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for i, w in ex.map(one, range(len(cases))):
            res[cases[i][0]] = w
    return res
