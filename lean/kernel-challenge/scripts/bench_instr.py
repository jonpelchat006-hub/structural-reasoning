#!/usr/bin/env python3
"""Local instruction-count bench (our tool, not the official judge).

Builds a submission in a scratch copy of the fixed problem workspace, generates the
same `impl n = v := Eq.refl v` theorem the judge uses, exports it, and replays it with
the judge's timer kernel under --count-instructions (user-space PMU counter).

usage: bench_instr.py PROBLEM SUBMISSION [n ...]
With no n, uses the group endpoints (range problems) or seeds 1,2 at each scale (packed).
"""
import json, os, shutil, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "evaluation" / "judge"))
import reference_answers as ref  # noqa: E402

TIMER = ROOT / "evaluation/judge/timer-kernel/.lake/build/bin/kernel"
EXPORT = Path("/home/claude/repro/lean4export/.lake/build/bin/lean4export")


def vg_ir(cmd):
    """Total instructions (Ir) via valgrind callgrind; PMU is unavailable in this sandbox."""
    out = "/tmp/bench/cg.out"
    subprocess.run(["valgrind", "--tool=callgrind", f"--callgrind-out-file={out}"] + cmd,
                   capture_output=True, text=True, timeout=7200)
    for l in open(out):
        if l.startswith("summary:") or l.startswith("totals:"):
            return int(l.split()[1])
    return 0


def default_inputs(problem):
    cfg = json.loads((ROOT / f"evaluation/problems/{problem}/config.json").read_text())
    out = []
    for g in cfg["evaluation"]["groups"]:
        s = g["sampling"]
        if s["kind"] == "packed":
            out += [(g["id"], ref.packed(s["scale"], seed)) for seed in (1, 2)]
        elif "min" in s:
            out += [(g["id"], s["min"]), (g["id"], s["max"])]
        else:
            lo, hi = s.get("range", s.get("bounds"))
            out += [(g["id"], lo), (g["id"], hi)]
    return out


def theorem_source(n, v, out_is_int):
    if v < 0:
        rhs = f"Lean.mkApp (Lean.mkConst ``Int.negSucc) (Lean.mkNatLit {-v - 1})"
    elif out_is_int:
        rhs = f"Lean.mkApp (Lean.mkConst ``Int.ofNat) (Lean.mkNatLit {v})"
    else:
        rhs = f"Lean.mkNatLit {v}"
    return ("import Submission\nimport Lean\nset_option maxRecDepth 4000000\n"
            "set_option maxHeartbeats 0\nopen Lean Meta Elab in\nrun_meta do\n"
            f"  let lhs := Lean.mkApp (Lean.mkConst ``Submission.impl) (Lean.mkNatLit {n})\n"
            f"  let rhs := {rhs}\n"
            "  let ty ← mkEq lhs rhs\n  let pf ← mkEqRefl rhs\n"
            "  Lean.addDecl (.thmDecl { name := `Bench.check, levelParams := [], type := ty, value := pf })\n")


def main():
    problem, sub = sys.argv[1], Path(sys.argv[2]).resolve()
    inputs = [("-", int(a)) for a in sys.argv[3:]] or default_inputs(problem)
    work = Path("/tmp/bench") / problem
    src = ROOT / "evaluation/problems" / problem
    if not work.exists():
        shutil.copytree(src, work, symlinks=True)
    shutil.copy(sub, work / "Submission.lean")
    r = subprocess.run(["lake", "build", "Submission"], cwd=work, capture_output=True, text=True)
    if r.returncode:
        print(r.stdout[-3000:], r.stderr[-2000:]); sys.exit(1)
    out_is_int = ref.OUTPUT_TYPES[problem] == "Int"
    total = 0
    base = None
    if os.environ.get("NO_VG") is None:
        inputs = [("base", 0)] + inputs
    for gid, n in inputs:
        v = ref.compute_answer(problem, n)
        (work / "Perf.lean").write_text(theorem_source(n, v, out_is_int))
        t0 = time.time()
        r = subprocess.run(["lake", "env", "lean", "-o", ".lake/build/lib/lean/Perf.olean", "Perf.lean"], cwd=work,
                           capture_output=True, text=True, timeout=900)
        if r.returncode:
            print(gid, n, "BUILD FAIL", r.stdout[-800:], r.stderr[-800:]); continue
        exp = work / "perf.ndjson"
        with open(exp, "w") as f:
            env = dict(os.environ, LEAN_PATH=f"{work}/.lake/build/lib/lean:" + os.environ.get("LEAN_PATH", ""))
            r = subprocess.run(["lake", "env", str(EXPORT), "Perf", "--", "Bench.check"], cwd=work,
                               stdout=f, stderr=subprocess.PIPE, text=True, timeout=900)
        if r.returncode:
            print(gid, n, "EXPORT FAIL", r.stderr[-800:]); continue
        r = subprocess.run([str(TIMER), "--target", "Bench.check", str(exp)],
                           capture_output=True, text=True, timeout=900)
        line = [l.split("=",1)[1] for l in r.stdout.splitlines() if l.startswith("KERNEL_TIMING=")]
        if r.returncode or not line:
            print(gid, n, "REPLAY FAIL", r.stdout[-800:], r.stderr[-800:]); continue
        d = json.loads(line[-1])
        ins = None
        if os.environ.get("NO_VG") is None:
            ins = vg_ir([str(TIMER), "--target", "Bench.check", str(exp)])
            if base is None:
                base = ins; print(f"(overhead baseline n=0: {base:,})"); continue
            ins -= base
            total += ins
        wall = {k: v for k, v in d.items() if k == "wall_ns"}
        print(f"{gid:>3} n={n}: Ir~{ins if ins is None else format(ins, ',')} {wall or d}", flush=True)
    print(f"TOTAL instructions: {total:,}")


if __name__ == "__main__":
    main()
