import Spec

/-!
# The low-part normal PRS (definitions)

Every polynomial `F_k` of the chain is held as residues `u_e = F_k,e mod 2^(q_k)` (two's
complement, one width `q_k` per polynomial, `|F_k,e| < 2^(q_k - 1)` by the size certificates),
so `F_k,e = u_e - s_e·2^(q_k)` with the sign bit `s_e = u_e >>> (q_k - 1)`.

One step from `A = F_k` (width `qA`) and `B = F_{k+1}` (width `qB`) to `C = F_{k+2}` (width `q`):
* `sh = v₂(lc A)` (found by a gcd and a de Bruijn lookup, then checked), `M = 2^(q + 2·sh)`;
* `inv = o⁻¹ mod 2^(q+128)` for the odd part `o = |lc A| >>> sh` (Newton, `newton`);
* the multipliers `w = lg·inv`, `m₁ = w²`, `m₂ = ∓(w <<< sh)`, `m₃ = inv·(±(g₁ <<< sh) − f₁·w)`
  (residues mod `M`; `lg = lc B`, `f₁`, `g₁` the second coefficients) and the corrections
  `cᵢ = mᵢ·2^(qA or qB) mod M`;
* each coefficient: `((m₁uA_e + m₂uB_(e-1) + m₃uB_e + 4M − (sA·c₁ + sB'·c₂ + sB·c₃)) >>> 2sh) mod 2^q`.
The numerator `lg²A_e − lg·lf·B_(e-1) − c·B_e` is `lc(A)²·C_e` (exactness, `chain_exact`), so the
sum is `2^(2sh)·C_e` mod `M`; the low `q` bits after the shift are `C_e mod 2^q`.
The first step has no division (`sh = 0`, `inv = 1`).
-/

namespace V9

/-- Mentions every graph operation (never evaluated): definitions that use it have a larger kernel
height than any graph node, so when the kernel compares a graph node with one of them it unfolds
the wrapper, not the node (`rfl` links between graphs and structured runs). -/
def hb : Nat := Nat.add (Nat.sub (Nat.mul 0 0) (Nat.land (Nat.xor 0 0) (Nat.gcd 0 0)))
  (Nat.shiftLeft (Nat.shiftRight 0 0) 0)

/-- Head of a list (`0` if empty), unfolded by the kernel before any graph node. -/
def hd0 (l : List Nat) : Nat := (fun (_ : Nat) => match l with | a :: _ => a | [] => 0) hb

/-- `cond b x y`, unfolded by the kernel before any graph node. -/
def cnd (b : Bool) (x y : Nat) : Nat := (fun (_ : Nat) => match b with | true => x | false => y) hb

/-- `o⁻¹` by Newton: `x ↦ x·(2 − a·x)` at the precisions `ps` (each at most twice the last). -/
def newton (a x : Nat) : List Nat → Nat
  | [] => x
  | p :: ps =>
    let mp := Nat.sub (Nat.shiftLeft 1 p) 1
    let t := Nat.land (Nat.mul (Nat.land a mp) x) mp
    newton a (Nat.land (Nat.mul x (Nat.sub (Nat.add mp 3) t)) mp) ps

/-- One coefficient of the next polynomial from `x = uA_e`, `y = uB_(e-1)`, `z = uB_e`. -/
def coef (m1 m2 m3 c1 c2 c3 K sh2 qm qhA qhB x y z : Nat) : Nat :=
  let S := Nat.add (Nat.add (Nat.mul m1 x) (Nat.mul m2 y)) (Nat.mul m3 z)
  let Cr := Nat.add (Nat.add (Nat.mul (Nat.shiftRight x qhA) c1) (Nat.mul (Nat.shiftRight y qhB) c2))
    (Nat.mul (Nat.shiftRight z qhB) c3)
  Nat.land (Nat.shiftRight (Nat.sub (Nat.add S K) Cr) sh2) qm

/-- The constant coefficient (no `y` term). -/
def coefL (m1 m3 c1 c3 K sh2 qm qhA qhB x z : Nat) : Nat :=
  let S := Nat.add (Nat.mul m1 x) (Nat.mul m3 z)
  let Cr := Nat.add (Nat.mul (Nat.shiftRight x qhA) c1) (Nat.mul (Nat.shiftRight z qhB) c3)
  Nat.land (Nat.shiftRight (Nat.sub (Nat.add S K) Cr) sh2) qm

/-- All coefficients: `xs` = `A` without its two leading coefficients, `zs` = `B` without its
leading coefficient (same length). -/
def lqs (m1 m2 m3 c1 c2 c3 K sh2 qm qhA qhB : Nat) : List Nat → List Nat → List Nat
  | [x], [z] => [coefL m1 m3 c1 c3 K sh2 qm qhA qhB x z]
  | x :: x' :: xs, z :: z' :: zs => coef m1 m2 m3 c1 c2 c3 K sh2 qm qhA qhB x z' z ::
      lqs m1 m2 m3 c1 c2 c3 K sh2 qm qhA qhB (x' :: xs) (z' :: zs)
  | _, _ => []

/-- `2^s ↦ s` for `s < 64` (de Bruijn multiplication and a byte table; unchecked here, the step
checks the shift it produces). -/
def dbTab : Nat := 631161908768061502958106012599586168840293888357046942936046222005082220398449784708040288127616261590255866941850787979324875502377750258648274685788416

def dbSh (P : Nat) : Nat :=
  Nat.land (Nat.shiftRight dbTab
    (Nat.shiftLeft (Nat.shiftRight (Nat.land (Nat.mul P 157587932685088877) 18446744073709551615) 58) 3)) 255

/-- The shift `v₂(lf)` (`0` on the first step). -/
def vSh (first : Bool) (lf : Nat) : Nat :=
  cnd first 0 (dbSh (Nat.gcd (Nat.land lf 18446744073709551615) (Nat.shiftLeft 1 64)))

/-- `|x|` from the residue `u` (sign bit `u >>> qh`, `Q = 2^(qh+1)`). -/
def vMag (u qh Q : Nat) : Nat :=
  Nat.add (Nat.sub u (Nat.mul (Nat.shiftRight u qh) Q)) (Nat.sub (Nat.mul (Nat.shiftRight u qh) Q) u)

/-- Sign extension of a residue: `E = M − 2^(qh+1)`. -/
def vExt (u qh E : Nat) : Nat := Nat.add u (Nat.mul (Nat.shiftRight u qh) E)

/-- `s ? t : M − t`. -/
def vSel (s t M : Nat) : Nat := Nat.add (Nat.mul s t) (Nat.mul (Nat.sub 1 s) (Nat.sub M t))

/-- The odd part's inverse (`1` on the first step). -/
def vInv (first : Bool) (nw : List Nat) (o : Nat) : Nat := cnd first 1 (newton o o nw)

/-- The valuation checks on the low 64 bits `xL`: bit `sh` set, bits below clear. -/
def vChk (xL sh : Nat) : Nat :=
  Nat.add (Nat.sub 1 (Nat.land (Nat.shiftRight xL sh) 1)) (Nat.land xL (Nat.sub (Nat.shiftLeft 1 sh) 1))

/-- One low-part step; passes the residues of the next polynomial and the failure count to `k`. -/
def lstep {α : Type} (qA qB q qhA qhB : Nat) (first : Bool) (nw : List Nat) (A B : List Nat)
    (k : List Nat → Nat → α) : α :=
  let lf := hd0 A
  let lg := hd0 B
  let f1 := hd0 A.tail
  let g1 := hd0 B.tail
  let QA := Nat.shiftLeft 1 qA
  let QB := Nat.shiftLeft 1 qB
  let sf := Nat.shiftRight lf qhA
  let sh := vSh first lf
  let sh2 := Nat.shiftLeft sh 1
  let M := Nat.shiftLeft 1 (Nat.add q sh2)
  let mask := Nat.sub M 1
  let K := Nat.shiftLeft M 2
  let Lg := vExt lg qhB (Nat.sub M QB)
  let F1 := vExt f1 qhA (Nat.sub M QA)
  let G1 := vExt g1 qhB (Nat.sub M QB)
  let qm := Nat.sub (Nat.shiftLeft 1 q) 1
  let inv := vInv first nw (Nat.shiftRight (vMag lf qhA QA) sh)
  let w := Nat.land (Nat.mul Lg inv) mask
  let m1 := Nat.land (Nat.mul w w) mask
  let m2 := vSel sf (Nat.land (Nat.shiftLeft w sh) mask) M
  let m3 := Nat.land (Nat.mul (Nat.sub (Nat.add (vSel (Nat.sub 1 sf) (Nat.land (Nat.shiftLeft G1 sh) mask) M) M)
    (Nat.land (Nat.mul F1 w) mask)) inv) mask
  let c1 := Nat.land (Nat.shiftLeft m1 qA) mask
  let c2 := Nat.land (Nat.shiftLeft m2 qB) mask
  let c3 := Nat.land (Nat.shiftLeft m3 qB) mask
  let H := lqs m1 m2 m3 c1 c2 c3 K sh2 qm qhA qhB A.tail.tail B.tail
  k H (cnd first (Nat.sub 1 (hd0 H)) (Nat.add (vChk (Nat.land lf 18446744073709551615) sh) (Nat.sub 1 (hd0 H))))

/-- Residue mod `Q = 2^q` (`qm = Q − 1`) of `(−1)^s · mag` (`mag < Q`). -/
def zres (mag s qm Q : Nat) : Nat := Nat.land (Nat.add (Nat.mul (Nat.sub 1 s) mag) (Nat.mul s (Nat.sub Q mag))) qm

/-- Steps after the first: `(qA, qB, q, qA − 1, qB − 1, Newton precisions)`; the last two
polynomials and the failure count go to `k`. -/
def lrun {α : Type} : List (Nat × Nat × Nat × Nat × Nat × List Nat) → List Nat → List Nat → Nat →
    (List Nat → Nat → α) → α
  | [], _, B, bad, k => k B bad
  | (qA, qB, q, qhA, qhB, nw) :: ps, A, B, bad, k =>
    lstep qA qB q qhA qhB false nw A B (fun H b => lrun ps B H (Nat.add bad b) k)

/-- Derivative factors `24, 23, …, 1`. -/
def dks : List Nat := [24, 23, 22, 21, 20, 19, 18, 17, 16, 15, 14, 13, 12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1]

/-- Coefficient widths `q_0 … q_24` of the D5 chain (`q_0, q_1` from the input bound, the rest
from the size certificates). -/
def qws : List Nat := [3485, 3489, 3500, 3957, 4711, 5759, 7102, 8739, 10671, 12894, 15409, 18216, 21315, 24703, 28382, 32350, 36609, 41156, 45991, 51115, 56524, 62222, 68205, 74473, 81025]

/-- Step parameters of steps 1 … 22. -/
def lparams : List (Nat × Nat × Nat × Nat × Nat × List Nat) := [(3489, 3500, 3957, 3488, 3499, [6, 12, 24, 48, 96, 192, 384, 768, 1536, 3072, 4085]),
  (3500, 3957, 4711, 3499, 3956, [6, 12, 24, 48, 96, 192, 384, 768, 1536, 3072, 4839]),
  (3957, 4711, 5759, 3956, 4710, [6, 12, 24, 48, 96, 192, 384, 768, 1536, 3072, 5887]),
  (4711, 5759, 7102, 4710, 5758, [6, 12, 24, 48, 96, 192, 384, 768, 1536, 3072, 6144, 7230]),
  (5759, 7102, 8739, 5758, 7101, [6, 12, 24, 48, 96, 192, 384, 768, 1536, 3072, 6144, 8867]),
  (7102, 8739, 10671, 7101, 8738, [6, 12, 24, 48, 96, 192, 384, 768, 1536, 3072, 6144, 10799]),
  (8739, 10671, 12894, 8738, 10670, [6, 12, 24, 48, 96, 192, 384, 768, 1536, 3072, 6144, 12288, 13022]),
  (10671, 12894, 15409, 10670, 12893, [6, 12, 24, 48, 96, 192, 384, 768, 1536, 3072, 6144, 12288, 15537]),
  (12894, 15409, 18216, 12893, 15408, [6, 12, 24, 48, 96, 192, 384, 768, 1536, 3072, 6144, 12288, 18344]),
  (15409, 18216, 21315, 15408, 18215, [6, 12, 24, 48, 96, 192, 384, 768, 1536, 3072, 6144, 12288, 21443]),
  (18216, 21315, 24703, 18215, 21314, [6, 12, 24, 48, 96, 192, 384, 768, 1536, 3072, 6144, 12288, 24576, 24831]),
  (21315, 24703, 28382, 21314, 24702, [6, 12, 24, 48, 96, 192, 384, 768, 1536, 3072, 6144, 12288, 24576, 28510]),
  (24703, 28382, 32350, 24702, 28381, [6, 12, 24, 48, 96, 192, 384, 768, 1536, 3072, 6144, 12288, 24576, 32478]),
  (28382, 32350, 36609, 28381, 32349, [6, 12, 24, 48, 96, 192, 384, 768, 1536, 3072, 6144, 12288, 24576, 36737]),
  (32350, 36609, 41156, 32349, 36608, [6, 12, 24, 48, 96, 192, 384, 768, 1536, 3072, 6144, 12288, 24576, 41284]),
  (36609, 41156, 45991, 36608, 41155, [6, 12, 24, 48, 96, 192, 384, 768, 1536, 3072, 6144, 12288, 24576, 46119]),
  (41156, 45991, 51115, 41155, 45990, [6, 12, 24, 48, 96, 192, 384, 768, 1536, 3072, 6144, 12288, 24576, 49152, 51243]),
  (45991, 51115, 56524, 45990, 51114, [6, 12, 24, 48, 96, 192, 384, 768, 1536, 3072, 6144, 12288, 24576, 49152, 56652]),
  (51115, 56524, 62222, 51114, 56523, [6, 12, 24, 48, 96, 192, 384, 768, 1536, 3072, 6144, 12288, 24576, 49152, 62350]),
  (56524, 62222, 68205, 56523, 62221, [6, 12, 24, 48, 96, 192, 384, 768, 1536, 3072, 6144, 12288, 24576, 49152, 68333]),
  (62222, 68205, 74473, 62221, 68204, [6, 12, 24, 48, 96, 192, 384, 768, 1536, 3072, 6144, 12288, 24576, 49152, 74601]),
  (68205, 74473, 81025, 68204, 74472, [6, 12, 24, 48, 96, 192, 384, 768, 1536, 3072, 6144, 12288, 24576, 49152, 81153])]

/-- The whole low-part run on the 25 encoded coefficients of `P` (`P'` is formed here).
Returns the encoded constant `F_24` and the failure count. -/
def lowRun (xs : List Nat) : Nat × Nat :=
  let QF := Nat.shiftLeft 1 3485
  let QG := Nat.shiftLeft 1 3489
  let A := xs.map (fun x => zres (Nat.shiftRight x 1) (Nat.land x 1) (Nat.sub QF 1) QF)
  let B := List.zipWith (fun x k => zres (Nat.mul (Nat.shiftRight x 1) k) (Nat.land x 1) (Nat.sub QG 1) QG) xs dks
  lstep 3485 3489 3500 3484 3488 true [] A B (fun H b => lrun lparams B H b (fun F bad =>
    let u := hd0 F
    let s := Nat.shiftRight u 81024
    let sQ := Nat.mul s (Nat.shiftLeft 1 81025)
    (Nat.add (Nat.shiftLeft (Nat.add (Nat.sub u sQ) (Nat.sub sQ u)) 1) s, bad)))

end V9
