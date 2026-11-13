#!/usr/bin/env python3
"""Assemble fib v8 from v7: the chosen plan per bit length (unrolled by the planner), the v7 structured
definitions and proofs, the new structured chains and specs (`new_specs.lean`), and per-chain
`rfl` links and spec theorems."""
import re, sys
sys.path.insert(0, "/home/claude/fibvar")
import planner as pl

V7 = open("/home/claude/work/submissions_v4/fib/Submission.lean").read()
NEW = open("/home/claude/fibdev/new_specs.lean").read()


def M(K): return f"(2 ^ {K}) (2 ^ (2 * {K}) - 2 ^ {K} - 1)"


def structured(p):
    """(structured call, spec proof term, needs 4 ≤ n / 8 ≤ n) for a plan"""
    Kt, Kd = pl.K_of(p.t), pl.K_of(p.P)
    if p.fin == "C":
        s = p.P
        return (f"chainC n {s} {M(Kt)} {M(Kd)}",
                f"chainC_spec' n {s} {p.t} {Kt} {Kd} (by decide) (by rw [← pow_add]; exact h) (by decide)\n"
                f"    (by decide +kernel) (by decide) (by decide +kernel)", None)
    if p.fin == "A":
        s, w = p.P + 1, p.P
        return (f"chainA n {s} {w} {M(Kt)} {M(Kd)}",
                f"chainA_spec' n {s} {w} {p.t} {Kt} {Kd} (by decide : {s} = {w} + 1) (by decide)\n"
                f"    (by rw [← pow_add]; exact h) (by decide) (by decide +kernel) (by decide) (by decide +kernel)", None)
    if p.fin == "D" and p.c >= 1 and p.r == 2:
        s, w = p.P + 2, p.P
        return (f"chainH n {s} {w} {p.c} {M(Kt)} {M(Kd)}",
                f"chainH_spec n {s} {w} {p.c} {p.t} {Kt} {Kd} (by decide : {s} = {w} + 2) (by decide) (by decide)\n"
                f"    (by rw [← pow_add]; exact h) h4 (by decide) (by decide +kernel) (by decide) (by decide +kernel)", 4)
    if p.fin == "D" and p.c >= 1 and p.r == 3:
        s, w = p.P + 3, p.P
        return (f"chainH3 n {s} {w} {p.c} {M(Kt)} {M(Kd)}",
                f"chainH3_spec n {s} {w} {p.c} {p.t} {Kt} {Kd} (by decide : {s} = {w} + 3) (by decide) (by decide)\n"
                f"    (by rw [← pow_add]; exact h) h4 (by decide) (by decide +kernel) (by decide) (by decide +kernel)", 8)
    raise ValueError(f"no structured form for {p}")


def build(plans, out_path):
    src = V7
    # 1. the unrolled chains
    a = src.index("set_option exponentiation.threshold 800 in\n/-- `F(n)` for `n < 2^13`. -/")
    b = src.index("/-- The branch for the bit length of `n`")
    chains = []
    for L in range(13, 19):
        p = plans[L]
        code = pl.emit(p, f"chain{L}").replace("set_option exponentiation.threshold 2000 in\n", "")
        doc = (f"/-- `F(n)` for `n < 2^{L}` (plan `{p.name()}`: top table of {p.t} bits, {p.c} `(F, L)` doublings, "
               f"{p.P - p.c if p.fin == 'D' else 0} Lucas-pair doublings, low table of {p.P} bits, "
               f"{p.r} last bit(s)). -/\n")
        chains.append("set_option exponentiation.threshold 800 in\n" + doc + code)
    src = src[:a] + "\n".join(chains) + "\n" + src[b:]
    # 2. the new structured chains and specs, before the rfl links
    i = src.index("/- `chain13_eq :")
    src = src[:i] + NEW + "\n" + src[i:]
    # 3. rfl links and per-chain specs
    for L in range(13, 19):
        call, spec, low = structured(plans[L])
        src = re.sub(rf"\(∀ n, chain{L} n = [^\n]*?\)\)\) none", f"(∀ n, chain{L} n = {call})) none", src)
        src = re.sub(rf"/- `chain{L}_eq : ∀ n, chain{L} n = [^`]*`", f"/- `chain{L}_eq : ∀ n, chain{L} n = {call}`", src)
        hyp = f" (h4 : {low} ≤ n)" if low else ""
        new_thm = (f"set_option exponentiation.threshold 800 in\n"
                   f"theorem chain{L}_spec (n : Nat) (h : n < 2 ^ {L}){hyp} : chain{L} n = Nat.fib n := by\n"
                   f"  rw [chain{L}_eq]\n  exact {spec}\n")
        src = re.sub(rf"set_option exponentiation.threshold 800 in\ntheorem chain{L}_spec .*?\n\n", new_thm + "\n",
                     src, flags=re.S)
    # 4. impl_correct: the extra hypotheses
    for L in range(13, 19):
        low = structured(plans[L])[2]
        src = re.sub(rf"  · exact chain{L}_spec n \(by omega\)( \(by omega\))?\n",
                     f"  · exact chain{L}_spec n (by omega){' (by omega)' if low else ''}\n", src)
    # 5. the header note
    src = src.replace("# Fibonacci: two modular powers, Lucas doubling and the addition formula (v7)",
                      "# Fibonacci: two modular powers, Lucas doubling and the addition formula (v8)")
    open(out_path, "w").write(src)


PLANS = {13: pl.Plan(13, 7, 6, 6, "C"), 14: pl.Plan(14, 7, 7, 7, "C"), 15: pl.Plan(15, 7, 7, 7, "A"),
         16: pl.Plan(16, 7, 8, 8, "A"), 17: pl.Plan(17, 8, 7, 6, "D"), 18: pl.Plan(18, 7, 8, 7, "D")}

if __name__ == "__main__":
    build(PLANS, sys.argv[1] if len(sys.argv) > 1 else "/home/claude/fibdev/Submission.lean")
