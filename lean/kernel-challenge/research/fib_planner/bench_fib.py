#!/usr/bin/env python3
"""Local kernel instruction bench for fib variants (adapted from bench_instr.py, Oct 18).

Uses problems/fib (which already holds the Mathlib cache) as the workspace. For each n it builds the
judge's `Submission.impl n = v := Eq.refl v` theorem, exports it, and counts the timer kernel's
instructions under valgrind; the count is the raw measured window
(as the judge reports it); the n = 0 window is printed as `base` for reference.

usage: bench_fib.py SUBMISSION.lean n [n ...]     (prints one line per n and a JSON summary line)
"""
import json, os, shutil, subprocess, sys
sys.set_int_max_str_digits(0)
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "problems" / "fib"
TIMER = ROOT / "evaluation/judge/timer-kernel/.lake/build/bin/kernel"
TIMER_VG = Path("/home/claude/timer-vg/.lake/build/bin/kernel")   # same kernel; perf enable/disable toggle callgrind
EXPORT = Path("/home/claude/repro/lean4export/.lake/build/bin/lean4export")
ENV = dict(os.environ, PATH=f"{Path.home()}/.elan/bin:" + os.environ.get("PATH", ""))


def fib(n):
    a, b = 0, 1
    # fast doubling
    for bit in bin(n)[2:]:
        c = a * (2 * b - a); d = a * a + b * b
        a, b = (c, d) if bit == "0" else (d, c + d)
    return a


def ir(exp, tag):
    """instructions inside the judge's measured window (the target theorem's replay), via callgrind"""
    out = f"/tmp/cgw_{tag}.out"
    for f in Path("/tmp").glob(f"cgw_{tag}.out*"): f.unlink()
    subprocess.run(["valgrind", "--tool=callgrind", "--collect-atstart=no", f"--callgrind-out-file={out}",
                    str(TIMER_VG), "--count-instructions", "--target", "Bench.check", str(exp)],
                   capture_output=True, text=True, timeout=7200, env=ENV)
    for f in Path("/tmp").glob(f"cgw_{tag}.out.*"):
        txt = f.read_text()
        if "replay-window" in txt:
            for l in txt.splitlines():
                if l.startswith("summary:") or l.startswith("totals:"):
                    return int(l.split()[1])
    raise RuntimeError("no replay-window dump")


def measure(n, tag):
    v = fib(n)
    (WORK / "Perf.lean").write_text(
        "import Submission\nimport Lean\nset_option maxRecDepth 4000000\nset_option maxHeartbeats 0\n"
        "open Lean Meta Elab in\nrun_meta do\n"
        f"  let lhs := Lean.mkApp (Lean.mkConst ``Submission.impl) (Lean.mkNatLit {n})\n"
        f"  let rhs := Lean.mkNatLit {v}\n"
        "  let ty ← mkEq lhs rhs\n  let pf ← mkEqRefl rhs\n"
        "  Lean.addDecl (.thmDecl { name := `Bench.check, levelParams := [], type := ty, value := pf })\n")
    r = subprocess.run(["lake", "env", "lean", "-o", ".lake/build/lib/lean/Perf.olean", "Perf.lean"], cwd=WORK,
                       capture_output=True, text=True, timeout=1800, env=ENV)
    if r.returncode:
        raise RuntimeError(f"n={n} build: {r.stdout[-600:]} {r.stderr[-600:]}")
    exp = WORK / f"perf_{tag}.ndjson"
    with open(exp, "w") as f:
        r = subprocess.run(["lake", "env", str(EXPORT), "Perf", "--", "Bench.check"], cwd=WORK,
                           stdout=f, stderr=subprocess.PIPE, text=True, timeout=1800, env=ENV)
    if r.returncode:
        raise RuntimeError(f"n={n} export: {r.stderr[-600:]}")
    r = subprocess.run([str(TIMER), "--target", "Bench.check", str(exp)], capture_output=True, text=True, timeout=1800)
    if r.returncode or "KERNEL_TIMING=" not in r.stdout:
        raise RuntimeError(f"n={n} replay failed: {r.stdout[-400:]} {r.stderr[-400:]}")
    return ir(exp, tag)


def main():
    sub, ns = Path(sys.argv[1]).resolve(), [int(a) for a in sys.argv[2:]]
    shutil.copy(sub, WORK / "Submission.lean")
    r = subprocess.run(["lake", "build", "Submission"], cwd=WORK, capture_output=True, text=True, env=ENV)
    if r.returncode:
        print(r.stdout[-3000:], r.stderr[-2000:]); sys.exit(1)
    base = measure(0, "base")
    res = {}
    for n in ns:
        res[n] = measure(n, str(n))
        print(f"n={n}: {res[n]:,}", flush=True)
    print("JSON " + json.dumps({"sub": str(sub), "base": base, "ir": res, "total": sum(res.values())}))


if __name__ == "__main__":
    main()
