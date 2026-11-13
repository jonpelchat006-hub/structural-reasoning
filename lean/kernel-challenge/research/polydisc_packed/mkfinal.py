"""Final single-file polydisc v8 Submission.lean = Base (generated) + Dev (proofs)."""
import sys, re
base = open("/home/claude/polydev/Base.lean").read()
dev = open("/home/claude/polydev/Dev.lean").read()
base = base[:base.rindex("end Submission")]
body = dev[dev.index("namespace Submission") + len("namespace Submission"):dev.rindex("end Submission")]
body = body.replace("set_option maxRecDepth 200000\n", "")
src = base + "\n/-! # v8 proofs -/\n" + body + "end Submission\n"
# header note
src = src.replace("# Polynomial discriminant by an encoded, shared-graph normal PRS",
                  "# Polynomial discriminant by an encoded, shared-graph normal PRS (v7) and packed lanes (v8)")
V8DOC = """
v8 adds a packed path for the 15-bit and 205-bit bands (`D1`, `D3`):

* every polynomial of the sequence is one natural number: its sign-normalized value `Ŝ(B)` at
  `B = 2^W`, with lane width `W ≥ 3b + 3` for the digit bound `T = 2^b` (`PInv`);
* one normal step (`pstep`) is two big products, one exact division and five checks: `c₁ ≠ 0`,
  exactness (remainder, or the low `2b` bits), one AND with a lane mask (every digit of the new
  offset form below `2T`), one shift (no digit above the degree), leading digit `> 0`;
* with these checks the packed value is the specification's coefficientwise step (`pstep_spec`):
  an integer polynomial that vanishes at `B` with all coefficients below `B` is zero
  (`eq_map_of_ev`), and `W ≥ 3b + 3` bounds every coefficient of `±N − dm·H`;
* lanes widen in segments (`prepack`: the two current polynomials are unpacked and repacked);
* band 205 hands its last 9 steps to the v7 element steps (`unpackT`, `run`);
* a failed check falls back to the v7 path (`finish8`), so correctness never depends on the lane
  sizes; the generated widths carry a 2% + 16-bit margin over sampled coefficient sizes;
* each graph is linked to its structured run by kernel `rfl` on open terms (all lane constants as
  variables, `pkDagC…_eq`) and then to the graph with constants inside (`pkDag…_eq`): comparing a
  graph with big closed constants directly against a structured term makes the kernel unfold
  `Nat.sub` on a huge literal.
"""
src = src.replace("Every check of the normal path (nonzero leading coefficients, exact divisions) is accumulated",
                  V8DOC.strip("\n") + "\n\nEvery check of the normal path (nonzero leading coefficients, exact divisions) is accumulated", 1)
open(sys.argv[1], "w").write(src)
print("bytes", len(src.encode()))
