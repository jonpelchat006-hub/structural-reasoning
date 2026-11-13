#!/usr/bin/env python3
"""Assemble fib v9 from v8: new building blocks (exponent tables, the sg first doubling, the branched
four-way end, the Bool.rec last bit) and the chosen plan per bit length.
usage: make_v9.py OUT.lean  (plans in PLANS below)"""
import re, sys
sys.path.insert(0, "/home/claude/fibvar")
import planner as pl, planner2 as p2, planner3 as p3
from planner import K_of

V8 = open("/home/claude/fibvar/Submission_v8.lean").read()
BLOCKS = open("/home/claude/fibdev/scratch/B4.lean").read()

def M(K): return f"(2 ^ {K}) (2 ^ (2 * {K}) - 2 ^ {K} - 1)"

def structured(p):
    """(structured call, spec proof term) for a plan (v8 families or the v9 ones)."""
    Kt, Kd = K_of(p.t), K_of(p.P)
    new = (p.tab, p.conv) == ("m0", "sg")
    tail = "(by decide) (by decide +kernel) (by decide) (by decide +kernel)"
    if p.fin == "C":
        s = p.P
        if new:
            return (f"chainC0 n {s} {M(Kt)} {M(Kd)}",
                    f"chainC0_spec n {s} {p.t} {Kt} {Kd} (by decide) (by rw [← pow_add]; exact h)\n    {tail}")
        return (f"chainC n {s} {M(Kt)} {M(Kd)}",
                f"chainC_spec' n {s} {p.t} {Kt} {Kd} (by decide) (by rw [← pow_add]; exact h)\n    {tail}")
    if p.fin == "Ab" and new:
        s, w = p.P + 1, p.P
        return (f"chainAb0 n {s} {w} {M(Kt)} {M(Kd)}",
                f"chainAb0_spec n {s} {w} {p.t} {Kt} {Kd} (by decide : {s} = {w} + 1) (by decide)\n"
                f"    (by rw [← pow_add]; exact h) {tail}")
    if p.fin == "A" and new:
        s, w = p.P + 1, p.P
        return (f"chainA0 n {s} {w} {M(Kt)} {M(Kd)}",
                f"chainA0_spec n {s} {w} {p.t} {Kt} {Kd} (by decide : {s} = {w} + 1) (by decide)\n"
                f"    (by rw [← pow_add]; exact h) {tail}")
    if p.fin == "A" and not new:
        s, w = p.P + 1, p.P
        return (f"chainA n {s} {w} {M(Kt)} {M(Kd)}",
                f"chainA_spec' n {s} {w} {p.t} {Kt} {Kd} (by decide : {s} = {w} + 1) (by decide)\n"
                f"    (by rw [← pow_add]; exact h) {tail}")
    if p.fin == "E" and new and p.c >= 1 and p.r in (2, 3):
        s, w = p.P + p.r, p.P
        nm = f"chainE{p.r}"
        return (f"{nm} n {s} {w} {p.c} {M(Kt)} {M(Kd)}",
                f"{nm}_spec n {s} {w} {p.c} {p.t} {Kt} {Kd} (by decide : {s} = {w} + {p.r}) (by decide) (by decide)\n"
                f"    (by rw [← pow_add]; exact h) {tail}")
    raise ValueError(f"no structured form for {p.name()}")

def unrolled(p, name):
    code = p3.emit(p, name).replace("set_option exponentiation.threshold 2000 in\n", "")
    # the selection helpers are shared (sel2a), not per chain
    code = re.sub(rf"def {name}_s2_a \(n a b : Nat\) : Nat :=\n(  .*\n)+?\n", "", code)
    code = code.replace(f"{name}_s2_a n", "sel2a n")
    assert f"{name}_s" not in code, code[:400]
    return code.strip() + "\n"

HEADER_DOC = """/-!
# Fibonacci: modular-power tables, Lucas doubling, the addition formula and a branched end (v9)

`X = 2^K` and `M = X² − X − 1`. In `ℤ[x] / (x² − x − 1)`, `x^j = F(j) x + F(j−1)`, and evaluating at
`x = X` is a ring map to `ℤ / M`; while `F(j+1) + 2 ≤ X` the representative `F(j) X + F(j−1)` is
already reduced, so one power and one kernel `%` give `F(j)` and `F(j−1)` (`tab0_spec`; for `j = 0`
the low half is `1 = F(1) − F(0)`).

Building blocks, each priced in the judge's kernel window (Oct 24):
* `tab0`: the top `t` bits `m` of `n` give `(F(m+1) − F(m), F(m))` from one modular power
  (`K = 88` for `t = 7`, `177` for `t = 8`);
* `sgc`: the first doubling straight from the table: `L(m) = lo + (lo + hi)`, `F(2m) = F(m) L(m)`,
  `L(2m) = L(m)² + 4 (m mod 2) − 2`, the parity read with one `Nat.land`;
* `(F, L)` doublings `(F(j), L(j)) ↦ (F(j) L(j), L(j)² − 2)` (even `j`): one product and one square;
* the switch `L(j+1) = (5 F(j) + L(j)) / 2` (`conv`) to Lucas pairs, and Lucas-pair doublings by two
  squares (`L(2j) = L(j)² − 2`, `L(2j+2) = L(j+1)² + 2`, `L(2j+1) = L(2j+2) − L(2j)`);
* the low bits from a second `tab0`, joined by the addition formula (`combL0` for a Lucas pair,
  `comb0` for a Fibonacci pair, or `2 F(N + e) = F(N) L(e) + L(N) F(e)` when no bits remain);
* the end (`fin4L`): from the squares `a = L(j)²`, `b = L(j+1)²` at `j = n / 4`, with
  `A = L(2j) = a − 2ε`, `B = L(2j+1) = b − a + 4ε`, `C = L(2j+2) = b + 2ε` (`ε = (−1)^j`),
  `F(2j) = (2B − A) / 5` and `F(2j+1) = (a + b) / 5`, one closed formula for each `n mod 4`:
  `F(4j) = F(2j) A`, `F(4j+1) = F(2j) B + 1`, `F(4j+2) = F(2j+1) B`, `F(4j+3) = F(2j+1) C − 1`,
  chosen by two `Bool.rec` tests on `Nat.land n 2` and `Nat.land n 1`. `sel2a` puts one branched
  selected doubling (bit 2) in front; its branch also fixes `ε` for the end (`fin4Lc0`, `fin4Lc1`).
By bit length:
* `n < 2^14` (`chain14` = `chainC0`): 7-bit top table, 7 `(F, L)` doublings, the 7 low bits joined;
* 15 bits (`chain15` = `chainC0`): 8-bit top table, 7 doublings, the 7 low bits joined;
* 16 bits (`chain16` = `chainA0`): 8-bit top table, 7 doublings, 7 low bits at `n / 2`, the last bit;
* 17 bits (`chain17` = `chainE2`): 8-bit top table, 6 `(F, L)` doublings, the switch, 1 Lucas-pair
  doubling, 7 low bits at `n / 4`, the four-way end;
* 18 bits (`chain18` = `chainE3`): the same with the low bits at `n / 8` and `sel2a` before the end.
The bit length is found by two or three `Bool.rec` tests on `Nat.ble` whose branches are closed
functions applied to `n`; other inputs use the general doubling from `(F(0), F(1))` (`gen`, with
`Nat.log2`). Every unrolled branch is proved equal to its structured chain by `rfl` (checked by the
kernel). All numerals are raw `nat_lit`s or `numeral%` literals (computed at elaboration time).
-/"""

def build(plans, out):
    src = V8
    # helper defs used by unrolled chains go before the chains
    helpers = p2.fin4L_defs() + "\n" + p2.selL_def("sel2a", 2, "a", "fin4Lc0", "fin4Lc1") + "\n" + p3.FINAB
    a = src.index("set_option exponentiation.threshold 800 in\n/-- `F(n)` for `n < 2^14`")
    b = src.index("/-- The branch for the bit length of `n`")
    chains = []
    for L in (14, 15, 16, 17, 18):
        p = plans[L]
        chains.append("set_option exponentiation.threshold 800 in\n"
                      f"/-- `F(n)` for `n < 2^{L}` (plan `{p.name()}`). -/\n" + unrolled(p, f"chain{L}"))
    src = src[:a] + "/-! ## v9 helpers (branched ends) -/\n\n" + helpers + "\n" + "\n".join(chains) + "\n" + src[b:]
    # new structured blocks and proofs, before the rfl links (drop the defs already placed above)
    blk = BLOCKS.split("namespace Submission\n", 1)[1].rsplit("end Submission", 1)[0]
    for d in ("fin4L", "fin4Lc0", "fin4Lc1", "sel2a", "finAb"):
        blk = re.sub(rf"(/--[^\n]*-/\n)?def {d} \(n [a-zA-Z ]+: Nat\) : Nat :=\n(  .*\n)+", "", blk, count=1)
    i = src.index("/- `chain14_eq :")
    src = src[:i] + "/-! ## v9 blocks (Oct 24) -/\n" + blk + "\n" + src[i:]
    for L in (14, 15, 16, 17, 18):
        call, spec = structured(plans[L])
        src = re.sub(rf"\(∀ n, chain{L} n = [^\n]*?\)\)\) none", f"(∀ n, chain{L} n = {call})) none", src)
        src = re.sub(rf"/- `chain{L}_eq : ∀ n, chain{L} n = [^`]*`", f"/- `chain{L}_eq : ∀ n, chain{L} n = {call}`", src)
        new_thm = (f"set_option exponentiation.threshold 800 in\n"
                   f"theorem chain{L}_spec (n : Nat) (h : n < 2 ^ {L}) : chain{L} n = Nat.fib n := by\n"
                   f"  rw [chain{L}_eq]\n  exact {spec}\n")
        src = re.sub(rf"set_option exponentiation.threshold 800 in\ntheorem chain{L}_spec .*?\n\n", new_thm + "\n",
                     src, flags=re.S)
        src = re.sub(rf"  · exact chain{L}_spec n \(by omega\)( \(by omega\))?\n", f"  · exact chain{L}_spec n (by omega)\n", src)
    a = src.index("/-!\n# Fibonacci"); b = src.index("-/", a) + 2
    src = src[:a] + HEADER_DOC + src[b:]
    src = prune(src, UNUSED)
    src = src.replace("/-! ## Lucas pairs (used for 18-bit `n`) -/", "/-! ## Lucas pairs -/")
    src = src.replace("/-! ### v8: any top table, and the hybrid chains (Oct 18)", "/-! ### Switching form part way (v8, Oct 18)")
    src = src.replace("/-! ## v9 blocks (Oct 24) -/", """/-! ## v9 blocks (Oct 24)

Exponent-`m` tables (`tab0`), the first doubling straight from the table (`sgc`), the joins for those
tables (`combL0`, `comb0`, `luc_add0`), the four-way end (`fin4L`, `fin4Lc0`, `fin4Lc1`) with the
branched selected doubling `sel2a`, and the structured chains `chainC0`, `chainA0`, `chainE2`, `chainE3`
with their specs. Bits are read with `Nat.land` (`land_two_pow`). -/""")
    import re as _re
    src = _re.sub(r"\n{3,}", "\n\n", src)
    open(out, "w").write(src)

PLANS = {14: p3.Plan3(14, 7, 7, 7, "C", "m0", "sg"), 15: p3.Plan3(15, 8, 7, 7, "C", "m0", "sg"),
         16: p3.Plan3(16, 8, 7, 7, "A", "m0", "sg"), 17: p3.Plan3(17, 8, 7, 6, "E", "m0", "sg"),
         18: p3.Plan3(18, 8, 7, 6, "E", "m0", "sg")}


# ---------------------------------------------------------------- pruning and the header
STARTS = ("def ", "theorem ", "/--", "/-!", "/- ", "set_option", "open ", "run_cmd", "end ", "elab ",
          "namespace ", "@[", "abbrev ", "lemma ")

def chunks(src):
    """top-level chunks; a doc comment or `set_option … in` attaches to the command after it"""
    lines = src.split("\n"); out = []; cur = []; pending = False
    for ln in lines:
        top = ln.startswith(STARTS)
        if top and not pending and cur:
            out.append("\n".join(cur)); cur = []
        cur.append(ln)
        if top:
            s = ln.strip()
            pending = (s.startswith("/--") and not s.endswith("-/")) or (s.startswith("/--") and s.endswith("-/")) \
                or (s.startswith("set_option") and s.endswith(" in")) or (s.startswith("open ") and s.endswith(" in"))
        elif pending and cur and cur[0].startswith("/--"):
            # inside a multi-line doc comment: stay pending until it closes and the decl line comes
            pending = not ln.rstrip().endswith("-/") or True
            if ln.startswith(STARTS[:2]): pending = False
        if ln.startswith(("def ", "theorem ", "elab ", "run_cmd", "lemma ", "abbrev ")): pending = False
    if cur: out.append("\n".join(cur))
    return out

def decl_name(chunk):
    import re
    m = re.search(r"^(?:def|theorem|lemma|abbrev) ([^\s(:]+)", chunk, flags=re.M)
    return m.group(1) if m else None

def prune(src, names):
    keep = []
    for c in chunks(src):
        if decl_name(c) in names: continue
        keep.append(c)
    return "\n".join(keep)

UNUSED = {"brec4_eq", "chainA", "chainA_spec", "chainA_spec'", "chainAb0", "chainAb0_spec", "chainC", "chainC_spec",
          "chainC_spec'", "chainD", "chainD_spec", "chainH", "chainH3", "chainH3_spec", "chainH_spec", "dX", "dY",
          "dbl1", "dbl1_spec", "dblL", "dblL_spec", "dbl_Z2", "fib_bound", "finAb", "finAb_spec", "finL", "finL2",
          "finL_spec", "luc_mono", "rec_eq", "sel2", "sel3", "selL", "selL_spec", "top_eq"}

if __name__ == "__main__":
    build(PLANS, sys.argv[1])
