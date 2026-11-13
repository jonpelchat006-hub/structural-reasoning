/-! ## v8: the packed normal PRS

Every polynomial `S` of the sequence (high-to-low, degree `d`) is held as one natural number, the
value `Ŝ(B)` of its sign normalization `Ŝ = ±S` (positive leading coefficient) at `B = 2^W`. Its
offset form `Ŝ(B) + T·(1 + B + … + B^d)` (`T = 2^b`) has the base-`B` digits `Ŝᵢ + T`. One normal
step is `R(B) = (lg²·F̂(B) − (lf·lg·B + c₁)·Ĝ(B)) / dm`, `Ĥ(B) = |R(B)|`, with the sign of `R` kept
as a bit. Checks: `c₁ ≠ 0`, exact division, every digit of the new offset form below `2T` (one
mask) and none above degree `d − 2` (one shift), leading digit `> 0`. With `W ≥ 3b + 3` these make
the packed step the specification's coefficientwise step.

All lane constants (`T`, masks, offsets, shift amounts) are parameters, so the graph and the
structured run are compared on open terms (`pkDagC…_eq`); their values are checked separately. -/

/-- Packed state: `F̂(B)`, `lc F̂`, the second offset digit of `F̂`, the sign bit of `F`; the same
for `G`; the divisor of the next step; the failure count. -/
structure PSt where
  fv : Nat
  lf : Nat
  df1 : Nat
  fs : Nat
  gv : Nat
  lg : Nat
  dg1 : Nat
  gs : Nat
  dm : Nat
  bad : Nat

/-- `1 + 2^W + … + 2^(W·(L−1))`. -/
def rep (W : Nat) : Nat → Nat
  | 0 => 0
  | L + 1 => 2 ^ W * rep W L + 1

/-- Lanes `0 … L−1` of width `W`, bits `b+1 … W−1` of each set. -/
def hmask (W b : Nat) : Nat → Nat
  | 0 => 0
  | L + 1 => 2 ^ W * hmask W b L + (2 ^ W - 2 ^ (b + 1))

/-- The lane digits of `u` at the shift amounts `shs` (high to low), masked by `m = 2^W − 1`. -/
def digsU (m u : Nat) : List Nat → List Nat
  | [] => []
  | s :: ss => Nat.land (Nat.shiftRight u s) m :: digsU m u ss

/-- `Σ dᵢ·2^(sᵢ)` for digits `d₀ … dₙ` (high to low) and shift amounts `s₀ … sₙ₋₁` of all but the
last digit, summed from the low end. -/
def packL : List Nat → List Nat → Nat
  | [d], _ => d
  | d :: e :: ds, s :: ss => Nat.add (packL (e :: ds) ss) (Nat.shiftLeft d s)
  | _, _ => 0

/-- Offset digit `a + T` of the encoded coefficient `x = 2·|a| + [a < 0]`. -/
def inDig (T x : Nat) : Nat :=
  Nat.sub (Nat.add (Nat.shiftRight x 1) T) (Nat.mul (Nat.shiftLeft (Nat.shiftRight x 1) 1) (Nat.land x 1))

/-- Offset digits `(k+1)·a + T` of the derivative from offset digits `a + T`: factors `k + 1` and
offsets `k·T` given as lists (the last digit has factor 1 and is kept). -/
def derDigs : List Nat → List Nat → List Nat → List Nat
  | [d], _, _ => [d]
  | d :: e :: ds, k :: ks, kT :: kTs => Nat.sub (Nat.mul d k) kT :: derDigs (e :: ds) ks kTs
  | _, _, _ => []

/-- The packed `P` and `P'` from the 24 encoded non-leading coefficients `xs`: `T`, the leading
offset digits `1 + T` and `24 + T`, the shift amounts of `P` and `P'`, the derivative factors and
offsets, and the offsets `T·rep W 25`, `T·rep W 24`. -/
def pinit (T l0 g0 : Nat) (shF shG ks kTs : List Nat) (O25 O24 : Nat) (xs : List Nat) : PSt :=
  let ds := xs.map (inDig T)
  let gs := derDigs (ds.take 23) ks kTs
  ⟨Nat.sub (packL (l0 :: ds) shF) O25, 1, ds.headD 0, 0,
   Nat.sub (packL (g0 :: gs) shG) O24, 24, gs.headD 0, 0, 1, 0⟩

/-- One packed normal step. Constants: `T = 2^b`, `m = 2^W − 1`, `O = T·rep W (dh+1)`,
`HM = hmask W b (dh+1)`, `m2 = 2^(2b) − 1`, shift amounts `sb = b`, `sW = W`, `s1 = W·(dh+1)`,
`s0 = W·dh`, `sm = W·(dh−1)`. `first`: the initial step (no division); `lowb`: check exactness
on the low `2b` bits instead of with a remainder. -/
def pstep (T m O HM m2 sb sW s1 s0 sm : Nat) (first lowb : Bool) (s : PSt) : PSt :=
  let P1 := Nat.add (Nat.mul s.lg s.df1) (Nat.shiftLeft s.lf sb)
  let N1 := Nat.add (Nat.mul s.lf s.dg1) (Nat.shiftLeft s.lg sb)
  let bad1 := Nat.add s.bad (Nat.sub 1 (Nat.add (Nat.sub P1 N1) (Nat.sub N1 P1)))
  let A := Nat.mul s.lg s.lg
  let X1 := Nat.mul A s.fv
  let X2 := Nat.mul (Nat.sub (Nat.add (Nat.shiftLeft (Nat.mul s.lf s.lg) sW) P1) N1) s.gv
  let D2 := Nat.sub X2 X1
  let mag := Nat.add (Nat.sub X1 X2) D2
  let q := cond first mag (Nat.div mag s.dm)
  let t2 := Nat.land (Nat.mul s.dm (Nat.land q m2)) m2
  let t1 := Nat.land mag m2
  let bad2 := cond first bad1 (cond lowb (Nat.add bad1 (Nat.add (Nat.sub t1 t2) (Nat.sub t2 t1)))
    (Nat.add bad1 (Nat.mod mag s.dm)))
  let u := Nat.add q O
  let bad3 := Nat.add bad2 (Nat.add (Nat.land u HM) (Nat.shiftRight u s1))
  let lh := Nat.sub (Nat.shiftRight u s0) T
  ⟨s.gv, s.lg, s.dg1, s.gs, q, lh, Nat.land (Nat.shiftRight u sm) m,
   Nat.xor s.fs (Nat.sub 1 (Nat.sub 1 D2)), A, Nat.add bad3 (Nat.sub 1 lh)⟩

/-- Move `F̂` and `Ĝ` to new lanes: old digit mask `m`, old offsets `OF`, `OG`, digit shift amounts
`shF`, `shG` (old lanes), new pack shift amounts `pF`, `pG`, new offsets `OF'`, `OG'`, and the
offset change `dT = T' − T`. -/
def prepack (m OF OG : Nat) (shF shG pF pG : List Nat) (OF' OG' dT : Nat) (s : PSt) : PSt :=
  let dsF := (digsU m (Nat.add s.fv OF) shF).map (fun x => Nat.add x dT)
  let dsG := (digsU m (Nat.add s.gv OG) shG).map (fun x => Nat.add x dT)
  ⟨Nat.sub (packL dsF pF) OF', s.lf, dsF.tail.headD 0, s.fs,
   Nat.sub (packL dsG pG) OG', s.lg, dsG.tail.headD 0, s.gs, s.dm, s.bad⟩

/-- Ghost parameters `W b dh` / `W b W' b' d` record the lanes; the rest are the constants. -/
inductive PAct where
  | step (W b dh T m O HM m2 sb sW s1 s0 sm : Nat) (first lowb : Bool)
  | repack (W b W' b' d m OF OG : Nat) (shF shG pF pG : List Nat) (OF' OG' dT : Nat)

def pact : PAct → PSt → PSt
  | .step _ _ _ T m O HM m2 sb sW s1 s0 sm first lowb, s => pstep T m O HM m2 sb sW s1 s0 sm first lowb s
  | .repack _ _ _ _ _ m OF OG shF shG pF pG OF' OG' dT, s => prepack m OF OG shF shG pF pG OF' OG' dT s

def prun : List PAct → PSt → PSt
  | [], s => s
  | a :: as, s => prun as (pact a s)

/-- Encoded true coefficient `±(x − T)` from an offset digit `x` and the sign bit `s`. -/
def zdig (T s x : Nat) : Nat :=
  Nat.add (Nat.shiftLeft (Nat.add (Nat.sub x T) (Nat.sub T x)) 1) (Nat.xor (Nat.sub 1 (Nat.sub 1 (Nat.sub T x))) s)

/-- The true polynomial (encoded, high to low) from a packed value `v` and sign bit `s`. -/
def unpackT (T m O : Nat) (shs : List Nat) (v s : Nat) : List Nat :=
  (digsU m (Nat.add v O) shs).map (zdig T s)
