# polydisc v9 — the low-part D5 run (Oct 20, 2026)

v9 = v8 + a proved low-part normal PRS for the D5 band (3484-bit coefficients).
The submission is `submissions_v6/polydisc/Submission.lean`.

## `lean/`: the development modules (core Lean, no Mathlib)

| File | Content |
|---|---|
| `Mod.lean` | `MEq n a b` (`n ∣ a − b`), two's-complement residues `res q x`, `res_val` |
| `Det.lean` | Leibniz determinant (first-column expansion), row and block operations, `det_bound` (permutation bound) |
| `Subres.lean` | Subresultant matrices; Lemma A with alternating conventions; `chain_val` and `chain_exact` |
| `Bridge.lean` | The spec's `normalResultant` on chain functions (`normalResultant_chain`); `prem_eq'` (no `c₁ ≠ 0`) |
| `Cert.lean` | The 23 size certificates (integer potentials) and the checker `certOK`; `sres_lt` |
| `Low.lean` | The structured low-part run (`lstep`, `lrun`, `lowRun`) and the wrappers `hd0` and `cnd` |
| `LowSpec.lean` | `coef_spec`, `mult_cong`, `sh_check`, Newton (`newton_spec`), `lstep_spec` |
| `Run.lean` | `lrunR_spec` (steps 1–22), `chain_bound` |
| `Top.lean` | `lowRun_spec` (the whole run against the spec) |
| `Conv.lean` | `toL` of the input = `polyOf`, and `derivHL` |
| `Dag.lean`, `LowDag.lean` | `natdag%` with `gcd`; the 7,877-node graph and its kernel `rfl` link |

Build: `lake build` in `lean/`, with `Spec.lean` copied from `problems/polydisc`.

## `gen/`: generators and measurements

| File | Purpose |
|---|---|
| `cert.py` | Computes the size certificates (LP dual plus assignment) and writes `cert_3484.json` |
| `lowdag2.py` | The graph builder, mirroring `Low.lean` op by op; checks the discriminant on random D5 inputs and prices GMP with `gmpcost` |
| `lowdag.py` | The first designs: sign-magnitude, inverse per coefficient |
| `mklowdag.py` | Writes `LowDag.lean` |
| `mkv9.py` | Assembles the submission from v8 and the modules |
| `perstep*.py`, `brk*.py` | Per-step and per-role GMP pricing |
| `rflpart.py`, `rflscale.py`, `cbisect.py`, `memrun.py` | Locating the memory blowup in the `rfl` link |
| `bench_poly9.py` | Replay-window benchmark (callgrind on the timer kernel) |
