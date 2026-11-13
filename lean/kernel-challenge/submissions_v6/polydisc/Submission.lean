import Spec
import Lean

/-!
# Polynomial discriminant by an encoded, shared-graph normal PRS (v7), packed lanes (v8) and a low-part D5 run (v9)

The specification computes the discriminant of a dense monic degree-24 polynomial with the
normal subresultant PRS (Bareiss fallback) on `List Int`. Kernel `Int` arithmetic is slow (each
operation unfolds through `match`), so this submission:

* encodes every integer `x` as the natural number `2·|x| + [x < 0]` (`zdec` decodes);
* fuses the two pseudo-division stages of a normal PRS step into one element formula
  `lg·(lg·x − lf·y) − c₁·z`, evaluated with natural-number operations only (magnitudes and
  sign bits; a signed sum is `T − 2N` from the total `T` and the negative part `N`);
* checks all exact divisions of a step at once: the remainders are non-negative, so they are all
  zero iff `Σ |eᵢ| − dm · Σ ⌊|eᵢ| / dm⌋ = 0` (`agg_eq_rs`), one product per step instead of one
  per element;
* writes the 23 normal steps (degrees 23 → 1) as one shared expression graph `prsDag`, built by
  `natdag%` (linear-time elaborator) so every intermediate number is one node, evaluated once;
* generates the encoded input polynomial lane-parallel: every LCG state is `(a_j·s + c_j) mod 2^64`
  with jump-ahead constants `a_j, c_j`, so two products of the seed with packed constants (even and
  odd states in 128-bit lanes), two sums and two masks give the whole stream at once; each
  coefficient is then one shift, one mask and four operations for the encoding
  (`genLane15C` … `genLane3484C`, selected by `genFastC`). The 25 coefficients go straight to the
  PRS (`kont`): matching a 25-element list in the kernel cost about 10M per case.

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

Every check of the normal path (nonzero leading coefficients, exact divisions) is accumulated
into a failure count; if it is nonzero the implementation returns the specification itself.

Proof outline:
* `zq_spec`, `eTN_spec`, `elt_val`, `zlin_val`: the element formulas decode correctly.
* `qs_val`, `cancel_r2`, `exactDivide_map`: list level; `sm_eq`, `agg_eq_rs`: the aggregated
  check is the sum of the remainders; `prem_eq`, `normal_step`: one step of the specification's
  `normalResultantGo` in the normal case; `run_spec`, `runAll_spec`: the whole run.
* `prsDag_eq`: the graph is definitionally the structured `runAll` (checked by the kernel).
* `lanes`, `interleave`, `laneY_eq`: the two lane packs are the LCG stream; `genZ_eq`: reading the
  coefficients off the stream is `genGo`; `genLane…C_rfl` (kernel) and `genLane…C_eq`: each
  band's graph is that read-off; `genFastC_eq`: the band dispatch is `genF` in continuation form.
* `genF_spec`: the generator decodes to `polyOf n`; `deriv_spec`: the derivative.
-/

set_option maxRecDepth 200000

namespace Submission

/-- `share x := v; b`: elaborate `b` with every `x` replaced by the same term `v` (one shared
expression node, not a kernel `let`). A chain of `share`s is elaborated iteratively. -/
syntax (name := shareStx) "share " ident " := " term "; " term : term

open Lean in
/-- Peel a right-nested chain of `share` bindings. -/
def shareChain : Nat → Syntax → Array (Syntax × Syntax) → Array (Syntax × Syntax) × Syntax
  | 0, stx, acc => (acc, stx)
  | fuel + 1, stx, acc =>
    if stx.getKind == ``shareStx then shareChain fuel stx[5] (acc.push (stx[1], stx[3]))
    else (acc, stx)

open Lean Elab Term Meta in
@[term_elab shareStx] def elabShare : TermElab := fun stx ty => do
  let (bs, body) := shareChain 100000 stx #[]
  if body.getKind == ``shareStx then
    throwError "share chain exceeds the elaborator limit"
  let nat := Lean.mkConst ``Nat
  let rec go (i : Nat) (map : Std.HashMap FVarId Expr) : TermElabM Expr := do
    let subst (e : Expr) : Expr :=
      e.replace fun s => if s.isFVar then map.get? s.fvarId! else none
    if h : i < bs.size then
      let (xi, vi) := bs[i]
      let ve := subst (← instantiateMVars (← elabTermEnsuringType vi (some nat)))
      withLocalDeclD xi.getId nat fun fv => go (i + 1) (map.insert fv.fvarId! ve)
    else
      return subst (← instantiateMVars (← elabTermEnsuringType body ty))
  go 0 {}

open Lean Elab Term Meta in
/-- `natdag% "s" [x₀, …]`: the natural-number expression graph described by `s`, built directly as
one shared `Expr` (linear time; the kernel sees the same term as with nested `share`s). Each line of
`s` is `op a b`, with `op` one of `add sub mul div mod land lor xor shl shr gcd` and operands `vN` (the
node on line `N`, counting from 0), `xN` (the `N`-th listed term) or a numeral; the last line,
`app f a₁ … aₙ` (or `list a₁ … aₙ`, the list `[a₁, …, aₙ]`), is the result. -/
elab "natdag% " s:str " [" xs:term,* "]" : term => do
  let xs ← xs.getElems.mapM fun x => elabTerm x none
  let ops : Std.HashMap String Name := Std.HashMap.ofList
    [("add", ``Nat.add), ("sub", ``Nat.sub), ("mul", ``Nat.mul), ("div", ``Nat.div), ("mod", ``Nat.mod),
     ("land", ``Nat.land), ("lor", ``Nat.lor), ("xor", ``Nat.xor), ("shl", ``Nat.shiftLeft),
     ("shr", ``Nat.shiftRight), ("gcd", ``Nat.gcd)]
  let mut nodes : Array Expr := #[]
  let mut result : Option Expr := none
  let operand := fun (nodes : Array Expr) (t : String) => do
    if t.startsWith "v" then
      let some i := (t.drop 1).toNat? | throwError "natdag%: bad operand {t}"
      let some e := nodes[i]? | throwError "natdag%: unknown node {t}"
      pure e
    else if t.startsWith "x" then
      let some i := (t.drop 1).toNat? | throwError "natdag%: bad operand {t}"
      let some e := xs[i]? | throwError "natdag%: unknown variable {t}"
      pure e
    else
      let some n := t.toNat? | throwError "natdag%: bad operand {t}"
      pure (mkRawNatLit n)
  for line in s.getString.splitOn "\n" do
    let ws := (line.splitOn " ").filter (· ≠ "")
    match ws with
    | [] => pure ()
    | "app" :: f :: args =>
      let fe ← operand nodes f
      let mut es : Array Expr := #[]
      for a in args do es := es.push (← operand nodes a)
      result := some (mkAppN fe es)
    | "list" :: args =>
      let mut l : Expr := mkApp (mkConst ``List.nil [Level.zero]) (mkConst ``Nat)
      for a in args.reverse do
        l := mkApp3 (mkConst ``List.cons [Level.zero]) (mkConst ``Nat) (← operand nodes a) l
      result := some l
    | [op, a, b] =>
      let some c := ops[op]? | throwError "natdag%: unknown op {op}"
      nodes := nodes.push (mkApp2 (mkConst c) (← operand nodes a) (← operand nodes b))
    | _ => throwError "natdag%: bad line {line}"
  match result with
  | some r => pure r
  | none => match nodes.back? with
    | some r => pure r
    | none => throwError "natdag%: empty graph"


/-! ## Signed integers encoded as `2·|x| + sign`

A signed sum is computed as `P − N` from the total `T = P + N` of the term magnitudes and the
magnitude `N` of the negative terms: magnitude `(P − N) + (N − P)`, sign `[N > P]`. -/

def zP (T N : Nat) : Nat := Nat.sub T N
def zD (T N : Nat) : Nat := Nat.sub N (zP T N)
def zMag (T N : Nat) : Nat := Nat.add (Nat.sub (zP T N) N) (zD T N)
def zSgn (T N : Nat) : Nat := Nat.sub 1 (Nat.sub 1 (zD T N))
/-- Encoded `(P − N) / dm` (exact when `zr = 0`). -/
def zq (T N dm : Nat) : Nat := Nat.add (Nat.shiftLeft (Nat.div (zMag T N) dm) 1) (zSgn T N)
/-- Remainder of `zMag T N` by `dm`, computed from the quotient (a product instead of a second division). -/
def zr (T N dm : Nat) : Nat := Nat.sub (zMag T N) (Nat.mul (Nat.div (zMag T N) dm) dm)

/-- Magnitude product of two encoded integers. -/
def pm (a b : Nat) : Nat := Nat.mul (Nat.shiftRight a 1) (Nat.shiftRight b 1)

/-- `a·b − c·d` on encoded integers. -/
def zlin (a b c d : Nat) : Nat :=
  zq (Nat.add (pm a b) (pm c d))
    (Nat.add (Nat.mul (Nat.land (Nat.xor a b) 1) (pm a b))
      (Nat.mul (Nat.xor (Nat.land (Nat.xor c d) 1) 1) (pm c d))) 1

/-- Total magnitude of `A·x − C·y − c₁·z` (scalars given by magnitudes). -/
def eT (mA mC m1 x y z : Nat) : Nat :=
  Nat.add (Nat.add (Nat.mul mA (Nat.shiftRight x 1)) (Nat.mul mC (Nat.shiftRight y 1)))
    (Nat.mul m1 (Nat.shiftRight z 1))
/-- Magnitude of the negative terms of `A·x − C·y − c₁·z` (`sC`, `s1`: signs of `−C`, `−c₁`). -/
def eN (mA mC sC m1 s1 x y z : Nat) : Nat :=
  Nat.add (Nat.add (Nat.mul (Nat.land x 1) (Nat.mul mA (Nat.shiftRight x 1)))
      (Nat.mul (Nat.xor (Nat.land y 1) sC) (Nat.mul mC (Nat.shiftRight y 1))))
    (Nat.mul (Nat.xor (Nat.land z 1) s1) (Nat.mul m1 (Nat.shiftRight z 1)))

def qs (mA mC sC m1 s1 dm : Nat) : List Nat → List Nat → List Nat
  | x :: xs, z :: zs =>
      zq (eT mA mC m1 x (zs.headD 0) z) (eN mA mC sC m1 s1 x (zs.headD 0) z) dm
        :: qs mA mC sC m1 s1 dm xs zs
  | _, _ => []

def rs (mA mC sC m1 s1 dm : Nat) : List Nat → List Nat → Nat
  | x :: xs, z :: zs =>
      Nat.add (zr (eT mA mC m1 x (zs.headD 0) z) (eN mA mC sC m1 s1 x (zs.headD 0) z) dm)
        (rs mA mC sC m1 s1 dm xs zs)
  | _, _ => 0

/-- Sum of the element magnitudes of one step. -/
def sm (mA mC sC m1 s1 : Nat) : List Nat → List Nat → Nat
  | x :: xs, z :: zs =>
      Nat.add (zMag (eT mA mC m1 x (zs.headD 0) z) (eN mA mC sC m1 s1 x (zs.headD 0) z))
        (sm mA mC sC m1 s1 xs zs)
  | _, _ => 0

/-- Sum of the quotient magnitudes of one step. -/
def sq (mA mC sC m1 s1 dm : Nat) : List Nat → List Nat → Nat
  | x :: xs, z :: zs =>
      Nat.add (Nat.div (zMag (eT mA mC m1 x (zs.headD 0) z) (eN mA mC sC m1 s1 x (zs.headD 0) z)) dm)
        (sq mA mC sC m1 s1 dm xs zs)
  | _, _ => 0

/-- Leading coefficient `c₁` of the first pseudo-remainder stage. -/
def cOne (F G : List Nat) : Nat :=
  zlin (G.headD 0) (F.tail.headD 0) (F.headD 0) (G.tail.headD 0)

def stepQ (dm : Nat) (F G : List Nat) : List Nat :=
  qs (Nat.mul (Nat.shiftRight (G.headD 0) 1) (Nat.shiftRight (G.headD 0) 1))
    (Nat.mul (Nat.shiftRight (G.headD 0) 1) (Nat.shiftRight (F.headD 0) 1))
    (Nat.xor (Nat.land (Nat.xor (G.headD 0) (F.headD 0)) 1) 1)
    (Nat.shiftRight (cOne F G) 1) (Nat.xor (Nat.land (cOne F G) 1) 1) dm F.tail.tail G.tail

/-- Sum of the division remainders of one step, as `Σ |eᵢ| − dm · Σ ⌊|eᵢ| / dm⌋` (`agg_eq_rs`):
one product per step instead of one per element. It is zero iff every division is exact. -/
def stepR (dm : Nat) (F G : List Nat) : Nat :=
  Nat.sub
    (sm (Nat.mul (Nat.shiftRight (G.headD 0) 1) (Nat.shiftRight (G.headD 0) 1))
      (Nat.mul (Nat.shiftRight (G.headD 0) 1) (Nat.shiftRight (F.headD 0) 1))
      (Nat.xor (Nat.land (Nat.xor (G.headD 0) (F.headD 0)) 1) 1)
      (Nat.shiftRight (cOne F G) 1) (Nat.xor (Nat.land (cOne F G) 1) 1) F.tail.tail G.tail)
    (Nat.mul dm
      (sq (Nat.mul (Nat.shiftRight (G.headD 0) 1) (Nat.shiftRight (G.headD 0) 1))
        (Nat.mul (Nat.shiftRight (G.headD 0) 1) (Nat.shiftRight (F.headD 0) 1))
        (Nat.xor (Nat.land (Nat.xor (G.headD 0) (F.headD 0)) 1) 1)
        (Nat.shiftRight (cOne F G) 1) (Nat.xor (Nat.land (cOne F G) 1) 1) dm F.tail.tail G.tail))

/-- Failure count of one step: `c₁ = 0`, a nonzero remainder, or a zero leading quotient. -/
def stepBad (dm : Nat) (F G : List Nat) : Nat :=
  Nat.add (Nat.add (Nat.sub 1 (Nat.shiftRight (cOne F G) 1)) (stepR dm F G))
    (Nat.sub 1 (Nat.shiftRight ((stepQ dm F G).headD 0) 1))

def dmOf (F : List Nat) : Nat := Nat.mul (Nat.shiftRight (F.headD 0) 1) (Nat.shiftRight (F.headD 0) 1)

def run : Nat → List Nat → List Nat → Nat → Nat × Nat
  | 0, _, G, bad => (G.headD 0, bad)
  | k + 1, F, G, bad => run k G (stepQ (dmOf F) F G) (Nat.add bad (stepBad (dmOf F) F G))

def runAll (F G : List Nat) : Nat × Nat := run 22 G (stepQ 1 F G) (stepBad 1 F G)

/-- The 23 normal PRS steps as one shared expression graph (generated from `runAll`). -/
def prsDag (f0 f1 f2 f3 f4 f5 f6 f7 f8 f9 f10 f11 f12 f13 f14 f15 f16 f17 f18 f19 f20 f21 f22 f23 f24 g0 g1 g2 g3 g4 g5 g6 g7 g8 g9 g10 g11 g12 g13 g14 g15 g16 g17 g18 g19 g20 g21 g22 g23 : Nat) : Nat × Nat :=
  natdag% "shr x25 1
mul v0 v0
shr x2 1
mul v1 v2
shr x0 1
mul v0 v4
shr x27 1
mul v5 v6
add v3 v7
shr x1 1
mul v0 v9
shr x26 1
mul v4 v11
add v10 v12
xor x25 x1
land v14 1
mul v15 v10
xor x0 x26
land v17 1
xor v18 1
mul v19 v12
add v16 v20
sub v13 v21
sub v22 v21
sub v21 v22
add v23 v24
div v25 1
shl v26 1
sub 1 v24
sub 1 v28
add v27 v29
shr v30 1
mul v31 v11
add v8 v32
land x2 1
mul v34 v3
land x27 1
xor x25 x0
land v37 1
xor v38 1
xor v36 v39
mul v40 v7
add v35 v41
land x26 1
land v30 1
xor v44 1
xor v43 v45
mul v46 v32
add v42 v47
sub v33 v48
sub v49 v48
sub v48 v49
add v50 v51
div v52 1
shl v53 1
sub 1 v51
sub 1 v55
add v54 v56
shr v57 1
mul v58 v58
mul v59 v6
mul v58 v0
shr x4 1
mul v1 v62
shr x29 1
mul v5 v64
add v63 v65
shr x28 1
mul v31 v67
add v66 v68
land x4 1
mul v70 v63
land x29 1
xor v72 v39
mul v73 v65
add v71 v74
land x28 1
xor v76 v45
mul v77 v68
add v75 v78
sub v69 v79
sub v80 v79
sub v79 v80
add v81 v82
div v83 1
shl v84 1
sub 1 v82
sub 1 v86
add v85 v87
shr v88 1
mul v61 v89
add v60 v90
mul v58 v11
shr x3 1
mul v1 v93
mul v5 v67
add v94 v95
mul v31 v6
add v96 v97
land x3 1
mul v99 v94
xor v76 v39
mul v101 v95
add v100 v102
xor v36 v45
mul v104 v97
add v103 v105
sub v98 v106
sub v107 v106
sub v106 v107
add v108 v109
div v110 1
shl v111 1
sub 1 v109
sub 1 v113
add v112 v114
shr v115 1
mul v0 v116
add v92 v117
xor v57 x26
land v119 1
mul v120 v92
xor x25 v115
land v122 1
xor v123 1
mul v124 v117
add v121 v125
sub v118 v126
sub v127 v126
sub v126 v127
add v128 v129
div v130 1
shl v131 1
sub 1 v129
sub 1 v133
add v132 v134
shr v135 1
mul v136 v116
add v91 v137
mul v36 v60
land v88 1
xor v57 x25
land v141 1
xor v142 1
xor v140 v143
mul v144 v90
add v139 v145
land v115 1
land v135 1
xor v148 1
xor v147 v149
mul v150 v137
add v146 v151
sub v138 v152
sub v153 v152
sub v152 v153
add v154 v155
div v156 v1
shl v157 1
sub 1 v155
sub 1 v159
add v158 v160
shr v161 1
mul v162 v162
mul v163 v89
mul v162 v58
mul v59 v64
shr x6 1
mul v1 v167
shr x31 1
mul v5 v169
add v168 v170
shr x30 1
mul v31 v172
add v171 v173
land x6 1
mul v175 v168
land x31 1
xor v177 v39
mul v178 v170
add v176 v179
land x30 1
xor v181 v45
mul v182 v173
add v180 v183
sub v174 v184
sub v185 v184
sub v184 v185
add v186 v187
div v188 1
shl v189 1
sub 1 v187
sub 1 v191
add v190 v192
shr v193 1
mul v61 v194
add v166 v195
shr x5 1
mul v1 v197
mul v5 v172
add v198 v199
mul v31 v64
add v200 v201
land x5 1
mul v203 v198
xor v181 v39
mul v205 v199
add v204 v206
xor v72 v45
mul v208 v201
add v207 v209
sub v202 v210
sub v211 v210
sub v210 v211
add v212 v213
div v214 1
shl v215 1
sub 1 v213
sub 1 v217
add v216 v218
shr v219 1
mul v136 v220
add v196 v221
mul v72 v166
land v193 1
xor v224 v143
mul v225 v195
add v223 v226
land v219 1
xor v228 v149
mul v229 v221
add v227 v230
sub v222 v231
sub v232 v231
sub v231 v232
add v233 v234
div v235 v1
shl v236 1
sub 1 v234
sub 1 v238
add v237 v239
shr v240 1
mul v165 v241
add v164 v242
mul v162 v116
mul v59 v67
mul v61 v220
add v245 v246
mul v136 v89
add v247 v248
mul v76 v245
xor v228 v143
mul v251 v246
add v250 v252
xor v140 v149
mul v254 v248
add v253 v255
sub v249 v256
sub v257 v256
sub v256 v257
add v258 v259
div v260 v1
shl v261 1
sub 1 v259
sub 1 v263
add v262 v264
shr v265 1
mul v58 v266
add v244 v267
xor v161 v115
land v269 1
mul v270 v244
xor v57 v265
land v272 1
xor v273 1
mul v274 v267
add v271 v275
sub v268 v276
sub v277 v276
sub v276 v277
add v278 v279
div v280 1
shl v281 1
sub 1 v279
sub 1 v283
add v282 v284
shr v285 1
mul v286 v266
add v243 v287
mul v140 v164
land v240 1
xor v161 v57
land v291 1
xor v292 1
xor v290 v293
mul v294 v242
add v289 v295
land v265 1
land v285 1
xor v298 1
xor v297 v299
mul v300 v287
add v296 v301
sub v288 v302
sub v303 v302
sub v302 v303
add v304 v305
div v306 v59
shl v307 1
sub 1 v305
sub 1 v309
add v308 v310
shr v311 1
mul v312 v312
mul v313 v241
mul v312 v162
mul v163 v194
mul v59 v169
shr x8 1
mul v1 v318
shr x33 1
mul v5 v320
add v319 v321
shr x32 1
mul v31 v323
add v322 v324
land x8 1
mul v326 v319
land x33 1
xor v328 v39
mul v329 v321
add v327 v330
land x32 1
xor v332 v45
mul v333 v324
add v331 v334
sub v325 v335
sub v336 v335
sub v335 v336
add v337 v338
div v339 1
shl v340 1
sub 1 v338
sub 1 v342
add v341 v343
shr v344 1
mul v61 v345
add v317 v346
shr x7 1
mul v1 v348
mul v5 v323
add v349 v350
mul v31 v169
add v351 v352
land x7 1
mul v354 v349
xor v332 v39
mul v356 v350
add v355 v357
xor v177 v45
mul v359 v352
add v358 v360
sub v353 v361
sub v362 v361
sub v361 v362
add v363 v364
div v365 1
shl v366 1
sub 1 v364
sub 1 v368
add v367 v369
shr v370 1
mul v136 v371
add v347 v372
mul v177 v317
land v344 1
xor v375 v143
mul v376 v346
add v374 v377
land v370 1
xor v379 v149
mul v380 v372
add v378 v381
sub v373 v382
sub v383 v382
sub v382 v383
add v384 v385
div v386 v1
shl v387 1
sub 1 v385
sub 1 v389
add v388 v390
shr v391 1
mul v165 v392
add v316 v393
mul v59 v172
mul v61 v371
add v395 v396
mul v136 v194
add v397 v398
mul v181 v395
xor v379 v143
mul v401 v396
add v400 v402
xor v224 v149
mul v404 v398
add v403 v405
sub v399 v406
sub v407 v406
sub v406 v407
add v408 v409
div v410 v1
shl v411 1
sub 1 v409
sub 1 v413
add v412 v414
shr v415 1
mul v286 v416
add v394 v417
mul v224 v316
land v391 1
xor v420 v293
mul v421 v393
add v419 v422
land v415 1
xor v424 v299
mul v425 v417
add v423 v426
sub v418 v427
sub v428 v427
sub v427 v428
add v429 v430
div v431 v59
shl v432 1
sub 1 v430
sub 1 v434
add v433 v435
shr v436 1
mul v315 v437
add v314 v438
mul v312 v266
mul v163 v220
mul v165 v416
add v441 v442
mul v286 v241
add v443 v444
mul v228 v441
xor v424 v293
mul v447 v442
add v446 v448
xor v290 v299
mul v450 v444
add v449 v451
sub v445 v452
sub v453 v452
sub v452 v453
add v454 v455
div v456 v59
shl v457 1
sub 1 v455
sub 1 v459
add v458 v460
shr v461 1
mul v162 v462
add v440 v463
xor v311 v265
land v465 1
mul v466 v440
xor v161 v461
land v468 1
xor v469 1
mul v470 v463
add v467 v471
sub v464 v472
sub v473 v472
sub v472 v473
add v474 v475
div v476 1
shl v477 1
sub 1 v475
sub 1 v479
add v478 v480
shr v481 1
mul v482 v462
add v439 v483
mul v290 v314
land v436 1
xor v311 v161
land v487 1
xor v488 1
xor v486 v489
mul v490 v438
add v485 v491
land v461 1
land v481 1
xor v494 1
xor v493 v495
mul v496 v483
add v492 v497
sub v484 v498
sub v499 v498
sub v498 v499
add v500 v501
div v502 v163
shl v503 1
sub 1 v501
sub 1 v505
add v504 v506
shr v507 1
mul v508 v508
mul v509 v437
mul v508 v312
mul v313 v392
mul v163 v345
mul v59 v320
shr x10 1
mul v1 v515
shr x35 1
mul v5 v517
add v516 v518
shr x34 1
mul v31 v520
add v519 v521
land x10 1
mul v523 v516
land x35 1
xor v525 v39
mul v526 v518
add v524 v527
land x34 1
xor v529 v45
mul v530 v521
add v528 v531
sub v522 v532
sub v533 v532
sub v532 v533
add v534 v535
div v536 1
shl v537 1
sub 1 v535
sub 1 v539
add v538 v540
shr v541 1
mul v61 v542
add v514 v543
shr x9 1
mul v1 v545
mul v5 v520
add v546 v547
mul v31 v320
add v548 v549
land x9 1
mul v551 v546
xor v529 v39
mul v553 v547
add v552 v554
xor v328 v45
mul v556 v549
add v555 v557
sub v550 v558
sub v559 v558
sub v558 v559
add v560 v561
div v562 1
shl v563 1
sub 1 v561
sub 1 v565
add v564 v566
shr v567 1
mul v136 v568
add v544 v569
mul v328 v514
land v541 1
xor v572 v143
mul v573 v543
add v571 v574
land v567 1
xor v576 v149
mul v577 v569
add v575 v578
sub v570 v579
sub v580 v579
sub v579 v580
add v581 v582
div v583 v1
shl v584 1
sub 1 v582
sub 1 v586
add v585 v587
shr v588 1
mul v165 v589
add v513 v590
mul v59 v323
mul v61 v568
add v592 v593
mul v136 v345
add v594 v595
mul v332 v592
xor v576 v143
mul v598 v593
add v597 v599
xor v375 v149
mul v601 v595
add v600 v602
sub v596 v603
sub v604 v603
sub v603 v604
add v605 v606
div v607 v1
shl v608 1
sub 1 v606
sub 1 v610
add v609 v611
shr v612 1
mul v286 v613
add v591 v614
mul v375 v513
land v588 1
xor v617 v293
mul v618 v590
add v616 v619
land v612 1
xor v621 v299
mul v622 v614
add v620 v623
sub v615 v624
sub v625 v624
sub v624 v625
add v626 v627
div v628 v59
shl v629 1
sub 1 v627
sub 1 v631
add v630 v632
shr v633 1
mul v315 v634
add v512 v635
mul v163 v371
mul v165 v613
add v637 v638
mul v286 v392
add v639 v640
mul v379 v637
xor v621 v293
mul v643 v638
add v642 v644
xor v420 v299
mul v646 v640
add v645 v647
sub v641 v648
sub v649 v648
sub v648 v649
add v650 v651
div v652 v59
shl v653 1
sub 1 v651
sub 1 v655
add v654 v656
shr v657 1
mul v482 v658
add v636 v659
mul v420 v512
land v633 1
xor v662 v489
mul v663 v635
add v661 v664
land v657 1
xor v666 v495
mul v667 v659
add v665 v668
sub v660 v669
sub v670 v669
sub v669 v670
add v671 v672
div v673 v163
shl v674 1
sub 1 v672
sub 1 v676
add v675 v677
shr v678 1
mul v511 v679
add v510 v680
mul v508 v462
mul v313 v416
mul v315 v658
add v683 v684
mul v482 v437
add v685 v686
mul v424 v683
xor v666 v489
mul v689 v684
add v688 v690
xor v486 v495
mul v692 v686
add v691 v693
sub v687 v694
sub v695 v694
sub v694 v695
add v696 v697
div v698 v163
shl v699 1
sub 1 v697
sub 1 v701
add v700 v702
shr v703 1
mul v312 v704
add v682 v705
xor v507 v461
land v707 1
mul v708 v682
xor v311 v703
land v710 1
xor v711 1
mul v712 v705
add v709 v713
sub v706 v714
sub v715 v714
sub v714 v715
add v716 v717
div v718 1
shl v719 1
sub 1 v717
sub 1 v721
add v720 v722
shr v723 1
mul v724 v704
add v681 v725
mul v486 v510
land v678 1
xor v507 v311
land v729 1
xor v730 1
xor v728 v731
mul v732 v680
add v727 v733
land v703 1
land v723 1
xor v736 1
xor v735 v737
mul v738 v725
add v734 v739
sub v726 v740
sub v741 v740
sub v740 v741
add v742 v743
div v744 v313
shl v745 1
sub 1 v743
sub 1 v747
add v746 v748
shr v749 1
mul v750 v750
mul v751 v679
mul v750 v508
mul v509 v634
mul v313 v589
mul v163 v542
mul v59 v517
shr x12 1
mul v1 v758
shr x37 1
mul v5 v760
add v759 v761
shr x36 1
mul v31 v763
add v762 v764
land x12 1
mul v766 v759
land x37 1
xor v768 v39
mul v769 v761
add v767 v770
land x36 1
xor v772 v45
mul v773 v764
add v771 v774
sub v765 v775
sub v776 v775
sub v775 v776
add v777 v778
div v779 1
shl v780 1
sub 1 v778
sub 1 v782
add v781 v783
shr v784 1
mul v61 v785
add v757 v786
shr x11 1
mul v1 v788
mul v5 v763
add v789 v790
mul v31 v517
add v791 v792
land x11 1
mul v794 v789
xor v772 v39
mul v796 v790
add v795 v797
xor v525 v45
mul v799 v792
add v798 v800
sub v793 v801
sub v802 v801
sub v801 v802
add v803 v804
div v805 1
shl v806 1
sub 1 v804
sub 1 v808
add v807 v809
shr v810 1
mul v136 v811
add v787 v812
mul v525 v757
land v784 1
xor v815 v143
mul v816 v786
add v814 v817
land v810 1
xor v819 v149
mul v820 v812
add v818 v821
sub v813 v822
sub v823 v822
sub v822 v823
add v824 v825
div v826 v1
shl v827 1
sub 1 v825
sub 1 v829
add v828 v830
shr v831 1
mul v165 v832
add v756 v833
mul v59 v520
mul v61 v811
add v835 v836
mul v136 v542
add v837 v838
mul v529 v835
xor v819 v143
mul v841 v836
add v840 v842
xor v572 v149
mul v844 v838
add v843 v845
sub v839 v846
sub v847 v846
sub v846 v847
add v848 v849
div v850 v1
shl v851 1
sub 1 v849
sub 1 v853
add v852 v854
shr v855 1
mul v286 v856
add v834 v857
mul v572 v756
land v831 1
xor v860 v293
mul v861 v833
add v859 v862
land v855 1
xor v864 v299
mul v865 v857
add v863 v866
sub v858 v867
sub v868 v867
sub v867 v868
add v869 v870
div v871 v59
shl v872 1
sub 1 v870
sub 1 v874
add v873 v875
shr v876 1
mul v315 v877
add v755 v878
mul v163 v568
mul v165 v856
add v880 v881
mul v286 v589
add v882 v883
mul v576 v880
xor v864 v293
mul v886 v881
add v885 v887
xor v617 v299
mul v889 v883
add v888 v890
sub v884 v891
sub v892 v891
sub v891 v892
add v893 v894
div v895 v59
shl v896 1
sub 1 v894
sub 1 v898
add v897 v899
shr v900 1
mul v482 v901
add v879 v902
mul v617 v755
land v876 1
xor v905 v489
mul v906 v878
add v904 v907
land v900 1
xor v909 v495
mul v910 v902
add v908 v911
sub v903 v912
sub v913 v912
sub v912 v913
add v914 v915
div v916 v163
shl v917 1
sub 1 v915
sub 1 v919
add v918 v920
shr v921 1
mul v511 v922
add v754 v923
mul v313 v613
mul v315 v901
add v925 v926
mul v482 v634
add v927 v928
mul v621 v925
xor v909 v489
mul v931 v926
add v930 v932
xor v662 v495
mul v934 v928
add v933 v935
sub v929 v936
sub v937 v936
sub v936 v937
add v938 v939
div v940 v163
shl v941 1
sub 1 v939
sub 1 v943
add v942 v944
shr v945 1
mul v724 v946
add v924 v947
mul v662 v754
land v921 1
xor v950 v731
mul v951 v923
add v949 v952
land v945 1
xor v954 v737
mul v955 v947
add v953 v956
sub v948 v957
sub v958 v957
sub v957 v958
add v959 v960
div v961 v313
shl v962 1
sub 1 v960
sub 1 v964
add v963 v965
shr v966 1
mul v753 v967
add v752 v968
mul v750 v704
mul v509 v658
mul v511 v946
add v971 v972
mul v724 v679
add v973 v974
mul v666 v971
xor v954 v731
mul v977 v972
add v976 v978
xor v728 v737
mul v980 v974
add v979 v981
sub v975 v982
sub v983 v982
sub v982 v983
add v984 v985
div v986 v313
shl v987 1
sub 1 v985
sub 1 v989
add v988 v990
shr v991 1
mul v508 v992
add v970 v993
xor v749 v703
land v995 1
mul v996 v970
xor v507 v991
land v998 1
xor v999 1
mul v1000 v993
add v997 v1001
sub v994 v1002
sub v1003 v1002
sub v1002 v1003
add v1004 v1005
div v1006 1
shl v1007 1
sub 1 v1005
sub 1 v1009
add v1008 v1010
shr v1011 1
mul v1012 v992
add v969 v1013
mul v728 v752
land v966 1
xor v749 v507
land v1017 1
xor v1018 1
xor v1016 v1019
mul v1020 v968
add v1015 v1021
land v991 1
land v1011 1
xor v1024 1
xor v1023 v1025
mul v1026 v1013
add v1022 v1027
sub v1014 v1028
sub v1029 v1028
sub v1028 v1029
add v1030 v1031
div v1032 v509
shl v1033 1
sub 1 v1031
sub 1 v1035
add v1034 v1036
shr v1037 1
mul v1038 v1038
mul v1039 v967
mul v1038 v750
mul v751 v922
mul v509 v877
mul v313 v832
mul v163 v785
mul v59 v760
shr x14 1
mul v1 v1047
shr x39 1
mul v5 v1049
add v1048 v1050
shr x38 1
mul v31 v1052
add v1051 v1053
land x14 1
mul v1055 v1048
land x39 1
xor v1057 v39
mul v1058 v1050
add v1056 v1059
land x38 1
xor v1061 v45
mul v1062 v1053
add v1060 v1063
sub v1054 v1064
sub v1065 v1064
sub v1064 v1065
add v1066 v1067
div v1068 1
shl v1069 1
sub 1 v1067
sub 1 v1071
add v1070 v1072
shr v1073 1
mul v61 v1074
add v1046 v1075
shr x13 1
mul v1 v1077
mul v5 v1052
add v1078 v1079
mul v31 v760
add v1080 v1081
land x13 1
mul v1083 v1078
xor v1061 v39
mul v1085 v1079
add v1084 v1086
xor v768 v45
mul v1088 v1081
add v1087 v1089
sub v1082 v1090
sub v1091 v1090
sub v1090 v1091
add v1092 v1093
div v1094 1
shl v1095 1
sub 1 v1093
sub 1 v1097
add v1096 v1098
shr v1099 1
mul v136 v1100
add v1076 v1101
mul v768 v1046
land v1073 1
xor v1104 v143
mul v1105 v1075
add v1103 v1106
land v1099 1
xor v1108 v149
mul v1109 v1101
add v1107 v1110
sub v1102 v1111
sub v1112 v1111
sub v1111 v1112
add v1113 v1114
div v1115 v1
shl v1116 1
sub 1 v1114
sub 1 v1118
add v1117 v1119
shr v1120 1
mul v165 v1121
add v1045 v1122
mul v59 v763
mul v61 v1100
add v1124 v1125
mul v136 v785
add v1126 v1127
mul v772 v1124
xor v1108 v143
mul v1130 v1125
add v1129 v1131
xor v815 v149
mul v1133 v1127
add v1132 v1134
sub v1128 v1135
sub v1136 v1135
sub v1135 v1136
add v1137 v1138
div v1139 v1
shl v1140 1
sub 1 v1138
sub 1 v1142
add v1141 v1143
shr v1144 1
mul v286 v1145
add v1123 v1146
mul v815 v1045
land v1120 1
xor v1149 v293
mul v1150 v1122
add v1148 v1151
land v1144 1
xor v1153 v299
mul v1154 v1146
add v1152 v1155
sub v1147 v1156
sub v1157 v1156
sub v1156 v1157
add v1158 v1159
div v1160 v59
shl v1161 1
sub 1 v1159
sub 1 v1163
add v1162 v1164
shr v1165 1
mul v315 v1166
add v1044 v1167
mul v163 v811
mul v165 v1145
add v1169 v1170
mul v286 v832
add v1171 v1172
mul v819 v1169
xor v1153 v293
mul v1175 v1170
add v1174 v1176
xor v860 v299
mul v1178 v1172
add v1177 v1179
sub v1173 v1180
sub v1181 v1180
sub v1180 v1181
add v1182 v1183
div v1184 v59
shl v1185 1
sub 1 v1183
sub 1 v1187
add v1186 v1188
shr v1189 1
mul v482 v1190
add v1168 v1191
mul v860 v1044
land v1165 1
xor v1194 v489
mul v1195 v1167
add v1193 v1196
land v1189 1
xor v1198 v495
mul v1199 v1191
add v1197 v1200
sub v1192 v1201
sub v1202 v1201
sub v1201 v1202
add v1203 v1204
div v1205 v163
shl v1206 1
sub 1 v1204
sub 1 v1208
add v1207 v1209
shr v1210 1
mul v511 v1211
add v1043 v1212
mul v313 v856
mul v315 v1190
add v1214 v1215
mul v482 v877
add v1216 v1217
mul v864 v1214
xor v1198 v489
mul v1220 v1215
add v1219 v1221
xor v905 v495
mul v1223 v1217
add v1222 v1224
sub v1218 v1225
sub v1226 v1225
sub v1225 v1226
add v1227 v1228
div v1229 v163
shl v1230 1
sub 1 v1228
sub 1 v1232
add v1231 v1233
shr v1234 1
mul v724 v1235
add v1213 v1236
mul v905 v1043
land v1210 1
xor v1239 v731
mul v1240 v1212
add v1238 v1241
land v1234 1
xor v1243 v737
mul v1244 v1236
add v1242 v1245
sub v1237 v1246
sub v1247 v1246
sub v1246 v1247
add v1248 v1249
div v1250 v313
shl v1251 1
sub 1 v1249
sub 1 v1253
add v1252 v1254
shr v1255 1
mul v753 v1256
add v1042 v1257
mul v509 v901
mul v511 v1235
add v1259 v1260
mul v724 v922
add v1261 v1262
mul v909 v1259
xor v1243 v731
mul v1265 v1260
add v1264 v1266
xor v950 v737
mul v1268 v1262
add v1267 v1269
sub v1263 v1270
sub v1271 v1270
sub v1270 v1271
add v1272 v1273
div v1274 v313
shl v1275 1
sub 1 v1273
sub 1 v1277
add v1276 v1278
shr v1279 1
mul v1012 v1280
add v1258 v1281
mul v950 v1042
land v1255 1
xor v1284 v1019
mul v1285 v1257
add v1283 v1286
land v1279 1
xor v1288 v1025
mul v1289 v1281
add v1287 v1290
sub v1282 v1291
sub v1292 v1291
sub v1291 v1292
add v1293 v1294
div v1295 v509
shl v1296 1
sub 1 v1294
sub 1 v1298
add v1297 v1299
shr v1300 1
mul v1041 v1301
add v1040 v1302
mul v1038 v992
mul v751 v946
mul v753 v1280
add v1305 v1306
mul v1012 v967
add v1307 v1308
mul v954 v1305
xor v1288 v1019
mul v1311 v1306
add v1310 v1312
xor v1016 v1025
mul v1314 v1308
add v1313 v1315
sub v1309 v1316
sub v1317 v1316
sub v1316 v1317
add v1318 v1319
div v1320 v509
shl v1321 1
sub 1 v1319
sub 1 v1323
add v1322 v1324
shr v1325 1
mul v750 v1326
add v1304 v1327
xor v1037 v991
land v1329 1
mul v1330 v1304
xor v749 v1325
land v1332 1
xor v1333 1
mul v1334 v1327
add v1331 v1335
sub v1328 v1336
sub v1337 v1336
sub v1336 v1337
add v1338 v1339
div v1340 1
shl v1341 1
sub 1 v1339
sub 1 v1343
add v1342 v1344
shr v1345 1
mul v1346 v1326
add v1303 v1347
mul v1016 v1040
land v1300 1
xor v1037 v749
land v1351 1
xor v1352 1
xor v1350 v1353
mul v1354 v1302
add v1349 v1355
land v1325 1
land v1345 1
xor v1358 1
xor v1357 v1359
mul v1360 v1347
add v1356 v1361
sub v1348 v1362
sub v1363 v1362
sub v1362 v1363
add v1364 v1365
div v1366 v751
shl v1367 1
sub 1 v1365
sub 1 v1369
add v1368 v1370
shr v1371 1
mul v1372 v1372
mul v1373 v1301
mul v1372 v1038
mul v1039 v1256
mul v751 v1211
mul v509 v1166
mul v313 v1121
mul v163 v1074
mul v59 v1049
shr x16 1
mul v1 v1382
shr x41 1
mul v5 v1384
add v1383 v1385
shr x40 1
mul v31 v1387
add v1386 v1388
land x16 1
mul v1390 v1383
land x41 1
xor v1392 v39
mul v1393 v1385
add v1391 v1394
land x40 1
xor v1396 v45
mul v1397 v1388
add v1395 v1398
sub v1389 v1399
sub v1400 v1399
sub v1399 v1400
add v1401 v1402
div v1403 1
shl v1404 1
sub 1 v1402
sub 1 v1406
add v1405 v1407
shr v1408 1
mul v61 v1409
add v1381 v1410
shr x15 1
mul v1 v1412
mul v5 v1387
add v1413 v1414
mul v31 v1049
add v1415 v1416
land x15 1
mul v1418 v1413
xor v1396 v39
mul v1420 v1414
add v1419 v1421
xor v1057 v45
mul v1423 v1416
add v1422 v1424
sub v1417 v1425
sub v1426 v1425
sub v1425 v1426
add v1427 v1428
div v1429 1
shl v1430 1
sub 1 v1428
sub 1 v1432
add v1431 v1433
shr v1434 1
mul v136 v1435
add v1411 v1436
mul v1057 v1381
land v1408 1
xor v1439 v143
mul v1440 v1410
add v1438 v1441
land v1434 1
xor v1443 v149
mul v1444 v1436
add v1442 v1445
sub v1437 v1446
sub v1447 v1446
sub v1446 v1447
add v1448 v1449
div v1450 v1
shl v1451 1
sub 1 v1449
sub 1 v1453
add v1452 v1454
shr v1455 1
mul v165 v1456
add v1380 v1457
mul v59 v1052
mul v61 v1435
add v1459 v1460
mul v136 v1074
add v1461 v1462
mul v1061 v1459
xor v1443 v143
mul v1465 v1460
add v1464 v1466
xor v1104 v149
mul v1468 v1462
add v1467 v1469
sub v1463 v1470
sub v1471 v1470
sub v1470 v1471
add v1472 v1473
div v1474 v1
shl v1475 1
sub 1 v1473
sub 1 v1477
add v1476 v1478
shr v1479 1
mul v286 v1480
add v1458 v1481
mul v1104 v1380
land v1455 1
xor v1484 v293
mul v1485 v1457
add v1483 v1486
land v1479 1
xor v1488 v299
mul v1489 v1481
add v1487 v1490
sub v1482 v1491
sub v1492 v1491
sub v1491 v1492
add v1493 v1494
div v1495 v59
shl v1496 1
sub 1 v1494
sub 1 v1498
add v1497 v1499
shr v1500 1
mul v315 v1501
add v1379 v1502
mul v163 v1100
mul v165 v1480
add v1504 v1505
mul v286 v1121
add v1506 v1507
mul v1108 v1504
xor v1488 v293
mul v1510 v1505
add v1509 v1511
xor v1149 v299
mul v1513 v1507
add v1512 v1514
sub v1508 v1515
sub v1516 v1515
sub v1515 v1516
add v1517 v1518
div v1519 v59
shl v1520 1
sub 1 v1518
sub 1 v1522
add v1521 v1523
shr v1524 1
mul v482 v1525
add v1503 v1526
mul v1149 v1379
land v1500 1
xor v1529 v489
mul v1530 v1502
add v1528 v1531
land v1524 1
xor v1533 v495
mul v1534 v1526
add v1532 v1535
sub v1527 v1536
sub v1537 v1536
sub v1536 v1537
add v1538 v1539
div v1540 v163
shl v1541 1
sub 1 v1539
sub 1 v1543
add v1542 v1544
shr v1545 1
mul v511 v1546
add v1378 v1547
mul v313 v1145
mul v315 v1525
add v1549 v1550
mul v482 v1166
add v1551 v1552
mul v1153 v1549
xor v1533 v489
mul v1555 v1550
add v1554 v1556
xor v1194 v495
mul v1558 v1552
add v1557 v1559
sub v1553 v1560
sub v1561 v1560
sub v1560 v1561
add v1562 v1563
div v1564 v163
shl v1565 1
sub 1 v1563
sub 1 v1567
add v1566 v1568
shr v1569 1
mul v724 v1570
add v1548 v1571
mul v1194 v1378
land v1545 1
xor v1574 v731
mul v1575 v1547
add v1573 v1576
land v1569 1
xor v1578 v737
mul v1579 v1571
add v1577 v1580
sub v1572 v1581
sub v1582 v1581
sub v1581 v1582
add v1583 v1584
div v1585 v313
shl v1586 1
sub 1 v1584
sub 1 v1588
add v1587 v1589
shr v1590 1
mul v753 v1591
add v1377 v1592
mul v509 v1190
mul v511 v1570
add v1594 v1595
mul v724 v1211
add v1596 v1597
mul v1198 v1594
xor v1578 v731
mul v1600 v1595
add v1599 v1601
xor v1239 v737
mul v1603 v1597
add v1602 v1604
sub v1598 v1605
sub v1606 v1605
sub v1605 v1606
add v1607 v1608
div v1609 v313
shl v1610 1
sub 1 v1608
sub 1 v1612
add v1611 v1613
shr v1614 1
mul v1012 v1615
add v1593 v1616
mul v1239 v1377
land v1590 1
xor v1619 v1019
mul v1620 v1592
add v1618 v1621
land v1614 1
xor v1623 v1025
mul v1624 v1616
add v1622 v1625
sub v1617 v1626
sub v1627 v1626
sub v1626 v1627
add v1628 v1629
div v1630 v509
shl v1631 1
sub 1 v1629
sub 1 v1633
add v1632 v1634
shr v1635 1
mul v1041 v1636
add v1376 v1637
mul v751 v1235
mul v753 v1615
add v1639 v1640
mul v1012 v1256
add v1641 v1642
mul v1243 v1639
xor v1623 v1019
mul v1645 v1640
add v1644 v1646
xor v1284 v1025
mul v1648 v1642
add v1647 v1649
sub v1643 v1650
sub v1651 v1650
sub v1650 v1651
add v1652 v1653
div v1654 v509
shl v1655 1
sub 1 v1653
sub 1 v1657
add v1656 v1658
shr v1659 1
mul v1346 v1660
add v1638 v1661
mul v1284 v1376
land v1635 1
xor v1664 v1353
mul v1665 v1637
add v1663 v1666
land v1659 1
xor v1668 v1359
mul v1669 v1661
add v1667 v1670
sub v1662 v1671
sub v1672 v1671
sub v1671 v1672
add v1673 v1674
div v1675 v751
shl v1676 1
sub 1 v1674
sub 1 v1678
add v1677 v1679
shr v1680 1
mul v1375 v1681
add v1374 v1682
mul v1372 v1326
mul v1039 v1280
mul v1041 v1660
add v1685 v1686
mul v1346 v1301
add v1687 v1688
mul v1288 v1685
xor v1668 v1353
mul v1691 v1686
add v1690 v1692
xor v1350 v1359
mul v1694 v1688
add v1693 v1695
sub v1689 v1696
sub v1697 v1696
sub v1696 v1697
add v1698 v1699
div v1700 v751
shl v1701 1
sub 1 v1699
sub 1 v1703
add v1702 v1704
shr v1705 1
mul v1038 v1706
add v1684 v1707
xor v1371 v1325
land v1709 1
mul v1710 v1684
xor v1037 v1705
land v1712 1
xor v1713 1
mul v1714 v1707
add v1711 v1715
sub v1708 v1716
sub v1717 v1716
sub v1716 v1717
add v1718 v1719
div v1720 1
shl v1721 1
sub 1 v1719
sub 1 v1723
add v1722 v1724
shr v1725 1
mul v1726 v1706
add v1683 v1727
mul v1350 v1374
land v1680 1
xor v1371 v1037
land v1731 1
xor v1732 1
xor v1730 v1733
mul v1734 v1682
add v1729 v1735
land v1705 1
land v1725 1
xor v1738 1
xor v1737 v1739
mul v1740 v1727
add v1736 v1741
sub v1728 v1742
sub v1743 v1742
sub v1742 v1743
add v1744 v1745
div v1746 v1039
shl v1747 1
sub 1 v1745
sub 1 v1749
add v1748 v1750
shr v1751 1
mul v1752 v1752
mul v1753 v1681
mul v1752 v1372
mul v1373 v1636
mul v1039 v1591
mul v751 v1546
mul v509 v1501
mul v313 v1456
mul v163 v1409
mul v59 v1384
shr x18 1
mul v1 v1763
shr x43 1
mul v5 v1765
add v1764 v1766
shr x42 1
mul v31 v1768
add v1767 v1769
land x18 1
mul v1771 v1764
land x43 1
xor v1773 v39
mul v1774 v1766
add v1772 v1775
land x42 1
xor v1777 v45
mul v1778 v1769
add v1776 v1779
sub v1770 v1780
sub v1781 v1780
sub v1780 v1781
add v1782 v1783
div v1784 1
shl v1785 1
sub 1 v1783
sub 1 v1787
add v1786 v1788
shr v1789 1
mul v61 v1790
add v1762 v1791
shr x17 1
mul v1 v1793
mul v5 v1768
add v1794 v1795
mul v31 v1384
add v1796 v1797
land x17 1
mul v1799 v1794
xor v1777 v39
mul v1801 v1795
add v1800 v1802
xor v1392 v45
mul v1804 v1797
add v1803 v1805
sub v1798 v1806
sub v1807 v1806
sub v1806 v1807
add v1808 v1809
div v1810 1
shl v1811 1
sub 1 v1809
sub 1 v1813
add v1812 v1814
shr v1815 1
mul v136 v1816
add v1792 v1817
mul v1392 v1762
land v1789 1
xor v1820 v143
mul v1821 v1791
add v1819 v1822
land v1815 1
xor v1824 v149
mul v1825 v1817
add v1823 v1826
sub v1818 v1827
sub v1828 v1827
sub v1827 v1828
add v1829 v1830
div v1831 v1
shl v1832 1
sub 1 v1830
sub 1 v1834
add v1833 v1835
shr v1836 1
mul v165 v1837
add v1761 v1838
mul v59 v1387
mul v61 v1816
add v1840 v1841
mul v136 v1409
add v1842 v1843
mul v1396 v1840
xor v1824 v143
mul v1846 v1841
add v1845 v1847
xor v1439 v149
mul v1849 v1843
add v1848 v1850
sub v1844 v1851
sub v1852 v1851
sub v1851 v1852
add v1853 v1854
div v1855 v1
shl v1856 1
sub 1 v1854
sub 1 v1858
add v1857 v1859
shr v1860 1
mul v286 v1861
add v1839 v1862
mul v1439 v1761
land v1836 1
xor v1865 v293
mul v1866 v1838
add v1864 v1867
land v1860 1
xor v1869 v299
mul v1870 v1862
add v1868 v1871
sub v1863 v1872
sub v1873 v1872
sub v1872 v1873
add v1874 v1875
div v1876 v59
shl v1877 1
sub 1 v1875
sub 1 v1879
add v1878 v1880
shr v1881 1
mul v315 v1882
add v1760 v1883
mul v163 v1435
mul v165 v1861
add v1885 v1886
mul v286 v1456
add v1887 v1888
mul v1443 v1885
xor v1869 v293
mul v1891 v1886
add v1890 v1892
xor v1484 v299
mul v1894 v1888
add v1893 v1895
sub v1889 v1896
sub v1897 v1896
sub v1896 v1897
add v1898 v1899
div v1900 v59
shl v1901 1
sub 1 v1899
sub 1 v1903
add v1902 v1904
shr v1905 1
mul v482 v1906
add v1884 v1907
mul v1484 v1760
land v1881 1
xor v1910 v489
mul v1911 v1883
add v1909 v1912
land v1905 1
xor v1914 v495
mul v1915 v1907
add v1913 v1916
sub v1908 v1917
sub v1918 v1917
sub v1917 v1918
add v1919 v1920
div v1921 v163
shl v1922 1
sub 1 v1920
sub 1 v1924
add v1923 v1925
shr v1926 1
mul v511 v1927
add v1759 v1928
mul v313 v1480
mul v315 v1906
add v1930 v1931
mul v482 v1501
add v1932 v1933
mul v1488 v1930
xor v1914 v489
mul v1936 v1931
add v1935 v1937
xor v1529 v495
mul v1939 v1933
add v1938 v1940
sub v1934 v1941
sub v1942 v1941
sub v1941 v1942
add v1943 v1944
div v1945 v163
shl v1946 1
sub 1 v1944
sub 1 v1948
add v1947 v1949
shr v1950 1
mul v724 v1951
add v1929 v1952
mul v1529 v1759
land v1926 1
xor v1955 v731
mul v1956 v1928
add v1954 v1957
land v1950 1
xor v1959 v737
mul v1960 v1952
add v1958 v1961
sub v1953 v1962
sub v1963 v1962
sub v1962 v1963
add v1964 v1965
div v1966 v313
shl v1967 1
sub 1 v1965
sub 1 v1969
add v1968 v1970
shr v1971 1
mul v753 v1972
add v1758 v1973
mul v509 v1525
mul v511 v1951
add v1975 v1976
mul v724 v1546
add v1977 v1978
mul v1533 v1975
xor v1959 v731
mul v1981 v1976
add v1980 v1982
xor v1574 v737
mul v1984 v1978
add v1983 v1985
sub v1979 v1986
sub v1987 v1986
sub v1986 v1987
add v1988 v1989
div v1990 v313
shl v1991 1
sub 1 v1989
sub 1 v1993
add v1992 v1994
shr v1995 1
mul v1012 v1996
add v1974 v1997
mul v1574 v1758
land v1971 1
xor v2000 v1019
mul v2001 v1973
add v1999 v2002
land v1995 1
xor v2004 v1025
mul v2005 v1997
add v2003 v2006
sub v1998 v2007
sub v2008 v2007
sub v2007 v2008
add v2009 v2010
div v2011 v509
shl v2012 1
sub 1 v2010
sub 1 v2014
add v2013 v2015
shr v2016 1
mul v1041 v2017
add v1757 v2018
mul v751 v1570
mul v753 v1996
add v2020 v2021
mul v1012 v1591
add v2022 v2023
mul v1578 v2020
xor v2004 v1019
mul v2026 v2021
add v2025 v2027
xor v1619 v1025
mul v2029 v2023
add v2028 v2030
sub v2024 v2031
sub v2032 v2031
sub v2031 v2032
add v2033 v2034
div v2035 v509
shl v2036 1
sub 1 v2034
sub 1 v2038
add v2037 v2039
shr v2040 1
mul v1346 v2041
add v2019 v2042
mul v1619 v1757
land v2016 1
xor v2045 v1353
mul v2046 v2018
add v2044 v2047
land v2040 1
xor v2049 v1359
mul v2050 v2042
add v2048 v2051
sub v2043 v2052
sub v2053 v2052
sub v2052 v2053
add v2054 v2055
div v2056 v751
shl v2057 1
sub 1 v2055
sub 1 v2059
add v2058 v2060
shr v2061 1
mul v1375 v2062
add v1756 v2063
mul v1039 v1615
mul v1041 v2041
add v2065 v2066
mul v1346 v1636
add v2067 v2068
mul v1623 v2065
xor v2049 v1353
mul v2071 v2066
add v2070 v2072
xor v1664 v1359
mul v2074 v2068
add v2073 v2075
sub v2069 v2076
sub v2077 v2076
sub v2076 v2077
add v2078 v2079
div v2080 v751
shl v2081 1
sub 1 v2079
sub 1 v2083
add v2082 v2084
shr v2085 1
mul v1726 v2086
add v2064 v2087
mul v1664 v1756
land v2061 1
xor v2090 v1733
mul v2091 v2063
add v2089 v2092
land v2085 1
xor v2094 v1739
mul v2095 v2087
add v2093 v2096
sub v2088 v2097
sub v2098 v2097
sub v2097 v2098
add v2099 v2100
div v2101 v1039
shl v2102 1
sub 1 v2100
sub 1 v2104
add v2103 v2105
shr v2106 1
mul v1755 v2107
add v1754 v2108
mul v1752 v1706
mul v1373 v1660
mul v1375 v2086
add v2111 v2112
mul v1726 v1681
add v2113 v2114
mul v1668 v2111
xor v2094 v1733
mul v2117 v2112
add v2116 v2118
xor v1730 v1739
mul v2120 v2114
add v2119 v2121
sub v2115 v2122
sub v2123 v2122
sub v2122 v2123
add v2124 v2125
div v2126 v1039
shl v2127 1
sub 1 v2125
sub 1 v2129
add v2128 v2130
shr v2131 1
mul v1372 v2132
add v2110 v2133
xor v1751 v1705
land v2135 1
mul v2136 v2110
xor v1371 v2131
land v2138 1
xor v2139 1
mul v2140 v2133
add v2137 v2141
sub v2134 v2142
sub v2143 v2142
sub v2142 v2143
add v2144 v2145
div v2146 1
shl v2147 1
sub 1 v2145
sub 1 v2149
add v2148 v2150
shr v2151 1
mul v2152 v2132
add v2109 v2153
mul v1730 v1754
land v2106 1
xor v1751 v1371
land v2157 1
xor v2158 1
xor v2156 v2159
mul v2160 v2108
add v2155 v2161
land v2131 1
land v2151 1
xor v2164 1
xor v2163 v2165
mul v2166 v2153
add v2162 v2167
sub v2154 v2168
sub v2169 v2168
sub v2168 v2169
add v2170 v2171
div v2172 v1373
shl v2173 1
sub 1 v2171
sub 1 v2175
add v2174 v2176
shr v2177 1
mul v2178 v2178
mul v2179 v2107
mul v2178 v1752
mul v1753 v2062
mul v1373 v2017
mul v1039 v1972
mul v751 v1927
mul v509 v1882
mul v313 v1837
mul v163 v1790
mul v59 v1765
shr x20 1
mul v1 v2190
shr x45 1
mul v5 v2192
add v2191 v2193
shr x44 1
mul v31 v2195
add v2194 v2196
land x20 1
mul v2198 v2191
land x45 1
xor v2200 v39
mul v2201 v2193
add v2199 v2202
land x44 1
xor v2204 v45
mul v2205 v2196
add v2203 v2206
sub v2197 v2207
sub v2208 v2207
sub v2207 v2208
add v2209 v2210
div v2211 1
shl v2212 1
sub 1 v2210
sub 1 v2214
add v2213 v2215
shr v2216 1
mul v61 v2217
add v2189 v2218
shr x19 1
mul v1 v2220
mul v5 v2195
add v2221 v2222
mul v31 v1765
add v2223 v2224
land x19 1
mul v2226 v2221
xor v2204 v39
mul v2228 v2222
add v2227 v2229
xor v1773 v45
mul v2231 v2224
add v2230 v2232
sub v2225 v2233
sub v2234 v2233
sub v2233 v2234
add v2235 v2236
div v2237 1
shl v2238 1
sub 1 v2236
sub 1 v2240
add v2239 v2241
shr v2242 1
mul v136 v2243
add v2219 v2244
mul v1773 v2189
land v2216 1
xor v2247 v143
mul v2248 v2218
add v2246 v2249
land v2242 1
xor v2251 v149
mul v2252 v2244
add v2250 v2253
sub v2245 v2254
sub v2255 v2254
sub v2254 v2255
add v2256 v2257
div v2258 v1
shl v2259 1
sub 1 v2257
sub 1 v2261
add v2260 v2262
shr v2263 1
mul v165 v2264
add v2188 v2265
mul v59 v1768
mul v61 v2243
add v2267 v2268
mul v136 v1790
add v2269 v2270
mul v1777 v2267
xor v2251 v143
mul v2273 v2268
add v2272 v2274
xor v1820 v149
mul v2276 v2270
add v2275 v2277
sub v2271 v2278
sub v2279 v2278
sub v2278 v2279
add v2280 v2281
div v2282 v1
shl v2283 1
sub 1 v2281
sub 1 v2285
add v2284 v2286
shr v2287 1
mul v286 v2288
add v2266 v2289
mul v1820 v2188
land v2263 1
xor v2292 v293
mul v2293 v2265
add v2291 v2294
land v2287 1
xor v2296 v299
mul v2297 v2289
add v2295 v2298
sub v2290 v2299
sub v2300 v2299
sub v2299 v2300
add v2301 v2302
div v2303 v59
shl v2304 1
sub 1 v2302
sub 1 v2306
add v2305 v2307
shr v2308 1
mul v315 v2309
add v2187 v2310
mul v163 v1816
mul v165 v2288
add v2312 v2313
mul v286 v1837
add v2314 v2315
mul v1824 v2312
xor v2296 v293
mul v2318 v2313
add v2317 v2319
xor v1865 v299
mul v2321 v2315
add v2320 v2322
sub v2316 v2323
sub v2324 v2323
sub v2323 v2324
add v2325 v2326
div v2327 v59
shl v2328 1
sub 1 v2326
sub 1 v2330
add v2329 v2331
shr v2332 1
mul v482 v2333
add v2311 v2334
mul v1865 v2187
land v2308 1
xor v2337 v489
mul v2338 v2310
add v2336 v2339
land v2332 1
xor v2341 v495
mul v2342 v2334
add v2340 v2343
sub v2335 v2344
sub v2345 v2344
sub v2344 v2345
add v2346 v2347
div v2348 v163
shl v2349 1
sub 1 v2347
sub 1 v2351
add v2350 v2352
shr v2353 1
mul v511 v2354
add v2186 v2355
mul v313 v1861
mul v315 v2333
add v2357 v2358
mul v482 v1882
add v2359 v2360
mul v1869 v2357
xor v2341 v489
mul v2363 v2358
add v2362 v2364
xor v1910 v495
mul v2366 v2360
add v2365 v2367
sub v2361 v2368
sub v2369 v2368
sub v2368 v2369
add v2370 v2371
div v2372 v163
shl v2373 1
sub 1 v2371
sub 1 v2375
add v2374 v2376
shr v2377 1
mul v724 v2378
add v2356 v2379
mul v1910 v2186
land v2353 1
xor v2382 v731
mul v2383 v2355
add v2381 v2384
land v2377 1
xor v2386 v737
mul v2387 v2379
add v2385 v2388
sub v2380 v2389
sub v2390 v2389
sub v2389 v2390
add v2391 v2392
div v2393 v313
shl v2394 1
sub 1 v2392
sub 1 v2396
add v2395 v2397
shr v2398 1
mul v753 v2399
add v2185 v2400
mul v509 v1906
mul v511 v2378
add v2402 v2403
mul v724 v1927
add v2404 v2405
mul v1914 v2402
xor v2386 v731
mul v2408 v2403
add v2407 v2409
xor v1955 v737
mul v2411 v2405
add v2410 v2412
sub v2406 v2413
sub v2414 v2413
sub v2413 v2414
add v2415 v2416
div v2417 v313
shl v2418 1
sub 1 v2416
sub 1 v2420
add v2419 v2421
shr v2422 1
mul v1012 v2423
add v2401 v2424
mul v1955 v2185
land v2398 1
xor v2427 v1019
mul v2428 v2400
add v2426 v2429
land v2422 1
xor v2431 v1025
mul v2432 v2424
add v2430 v2433
sub v2425 v2434
sub v2435 v2434
sub v2434 v2435
add v2436 v2437
div v2438 v509
shl v2439 1
sub 1 v2437
sub 1 v2441
add v2440 v2442
shr v2443 1
mul v1041 v2444
add v2184 v2445
mul v751 v1951
mul v753 v2423
add v2447 v2448
mul v1012 v1972
add v2449 v2450
mul v1959 v2447
xor v2431 v1019
mul v2453 v2448
add v2452 v2454
xor v2000 v1025
mul v2456 v2450
add v2455 v2457
sub v2451 v2458
sub v2459 v2458
sub v2458 v2459
add v2460 v2461
div v2462 v509
shl v2463 1
sub 1 v2461
sub 1 v2465
add v2464 v2466
shr v2467 1
mul v1346 v2468
add v2446 v2469
mul v2000 v2184
land v2443 1
xor v2472 v1353
mul v2473 v2445
add v2471 v2474
land v2467 1
xor v2476 v1359
mul v2477 v2469
add v2475 v2478
sub v2470 v2479
sub v2480 v2479
sub v2479 v2480
add v2481 v2482
div v2483 v751
shl v2484 1
sub 1 v2482
sub 1 v2486
add v2485 v2487
shr v2488 1
mul v1375 v2489
add v2183 v2490
mul v1039 v1996
mul v1041 v2468
add v2492 v2493
mul v1346 v2017
add v2494 v2495
mul v2004 v2492
xor v2476 v1353
mul v2498 v2493
add v2497 v2499
xor v2045 v1359
mul v2501 v2495
add v2500 v2502
sub v2496 v2503
sub v2504 v2503
sub v2503 v2504
add v2505 v2506
div v2507 v751
shl v2508 1
sub 1 v2506
sub 1 v2510
add v2509 v2511
shr v2512 1
mul v1726 v2513
add v2491 v2514
mul v2045 v2183
land v2488 1
xor v2517 v1733
mul v2518 v2490
add v2516 v2519
land v2512 1
xor v2521 v1739
mul v2522 v2514
add v2520 v2523
sub v2515 v2524
sub v2525 v2524
sub v2524 v2525
add v2526 v2527
div v2528 v1039
shl v2529 1
sub 1 v2527
sub 1 v2531
add v2530 v2532
shr v2533 1
mul v1755 v2534
add v2182 v2535
mul v1373 v2041
mul v1375 v2513
add v2537 v2538
mul v1726 v2062
add v2539 v2540
mul v2049 v2537
xor v2521 v1733
mul v2543 v2538
add v2542 v2544
xor v2090 v1739
mul v2546 v2540
add v2545 v2547
sub v2541 v2548
sub v2549 v2548
sub v2548 v2549
add v2550 v2551
div v2552 v1039
shl v2553 1
sub 1 v2551
sub 1 v2555
add v2554 v2556
shr v2557 1
mul v2152 v2558
add v2536 v2559
mul v2090 v2182
land v2533 1
xor v2562 v2159
mul v2563 v2535
add v2561 v2564
land v2557 1
xor v2566 v2165
mul v2567 v2559
add v2565 v2568
sub v2560 v2569
sub v2570 v2569
sub v2569 v2570
add v2571 v2572
div v2573 v1373
shl v2574 1
sub 1 v2572
sub 1 v2576
add v2575 v2577
shr v2578 1
mul v2181 v2579
add v2180 v2580
mul v2178 v2132
mul v1753 v2086
mul v1755 v2558
add v2583 v2584
mul v2152 v2107
add v2585 v2586
mul v2094 v2583
xor v2566 v2159
mul v2589 v2584
add v2588 v2590
xor v2156 v2165
mul v2592 v2586
add v2591 v2593
sub v2587 v2594
sub v2595 v2594
sub v2594 v2595
add v2596 v2597
div v2598 v1373
shl v2599 1
sub 1 v2597
sub 1 v2601
add v2600 v2602
shr v2603 1
mul v1752 v2604
add v2582 v2605
xor v2177 v2131
land v2607 1
mul v2608 v2582
xor v1751 v2603
land v2610 1
xor v2611 1
mul v2612 v2605
add v2609 v2613
sub v2606 v2614
sub v2615 v2614
sub v2614 v2615
add v2616 v2617
div v2618 1
shl v2619 1
sub 1 v2617
sub 1 v2621
add v2620 v2622
shr v2623 1
mul v2624 v2604
add v2581 v2625
mul v2156 v2180
land v2578 1
xor v2177 v1751
land v2629 1
xor v2630 1
xor v2628 v2631
mul v2632 v2580
add v2627 v2633
land v2603 1
land v2623 1
xor v2636 1
xor v2635 v2637
mul v2638 v2625
add v2634 v2639
sub v2626 v2640
sub v2641 v2640
sub v2640 v2641
add v2642 v2643
div v2644 v1753
shl v2645 1
sub 1 v2643
sub 1 v2647
add v2646 v2648
shr v2649 1
mul v2650 v2650
mul v2651 v2579
mul v2650 v2178
mul v2179 v2534
mul v1753 v2489
mul v1373 v2444
mul v1039 v2399
mul v751 v2354
mul v509 v2309
mul v313 v2264
mul v163 v2217
mul v59 v2192
shr x22 1
mul v1 v2663
shr x47 1
mul v5 v2665
add v2664 v2666
shr x46 1
mul v31 v2668
add v2667 v2669
land x22 1
mul v2671 v2664
land x47 1
xor v2673 v39
mul v2674 v2666
add v2672 v2675
land x46 1
xor v2677 v45
mul v2678 v2669
add v2676 v2679
sub v2670 v2680
sub v2681 v2680
sub v2680 v2681
add v2682 v2683
div v2684 1
shl v2685 1
sub 1 v2683
sub 1 v2687
add v2686 v2688
shr v2689 1
mul v61 v2690
add v2662 v2691
shr x21 1
mul v1 v2693
mul v5 v2668
add v2694 v2695
mul v31 v2192
add v2696 v2697
land x21 1
mul v2699 v2694
xor v2677 v39
mul v2701 v2695
add v2700 v2702
xor v2200 v45
mul v2704 v2697
add v2703 v2705
sub v2698 v2706
sub v2707 v2706
sub v2706 v2707
add v2708 v2709
div v2710 1
shl v2711 1
sub 1 v2709
sub 1 v2713
add v2712 v2714
shr v2715 1
mul v136 v2716
add v2692 v2717
mul v2200 v2662
land v2689 1
xor v2720 v143
mul v2721 v2691
add v2719 v2722
land v2715 1
xor v2724 v149
mul v2725 v2717
add v2723 v2726
sub v2718 v2727
sub v2728 v2727
sub v2727 v2728
add v2729 v2730
div v2731 v1
shl v2732 1
sub 1 v2730
sub 1 v2734
add v2733 v2735
shr v2736 1
mul v165 v2737
add v2661 v2738
mul v59 v2195
mul v61 v2716
add v2740 v2741
mul v136 v2217
add v2742 v2743
mul v2204 v2740
xor v2724 v143
mul v2746 v2741
add v2745 v2747
xor v2247 v149
mul v2749 v2743
add v2748 v2750
sub v2744 v2751
sub v2752 v2751
sub v2751 v2752
add v2753 v2754
div v2755 v1
shl v2756 1
sub 1 v2754
sub 1 v2758
add v2757 v2759
shr v2760 1
mul v286 v2761
add v2739 v2762
mul v2247 v2661
land v2736 1
xor v2765 v293
mul v2766 v2738
add v2764 v2767
land v2760 1
xor v2769 v299
mul v2770 v2762
add v2768 v2771
sub v2763 v2772
sub v2773 v2772
sub v2772 v2773
add v2774 v2775
div v2776 v59
shl v2777 1
sub 1 v2775
sub 1 v2779
add v2778 v2780
shr v2781 1
mul v315 v2782
add v2660 v2783
mul v163 v2243
mul v165 v2761
add v2785 v2786
mul v286 v2264
add v2787 v2788
mul v2251 v2785
xor v2769 v293
mul v2791 v2786
add v2790 v2792
xor v2292 v299
mul v2794 v2788
add v2793 v2795
sub v2789 v2796
sub v2797 v2796
sub v2796 v2797
add v2798 v2799
div v2800 v59
shl v2801 1
sub 1 v2799
sub 1 v2803
add v2802 v2804
shr v2805 1
mul v482 v2806
add v2784 v2807
mul v2292 v2660
land v2781 1
xor v2810 v489
mul v2811 v2783
add v2809 v2812
land v2805 1
xor v2814 v495
mul v2815 v2807
add v2813 v2816
sub v2808 v2817
sub v2818 v2817
sub v2817 v2818
add v2819 v2820
div v2821 v163
shl v2822 1
sub 1 v2820
sub 1 v2824
add v2823 v2825
shr v2826 1
mul v511 v2827
add v2659 v2828
mul v313 v2288
mul v315 v2806
add v2830 v2831
mul v482 v2309
add v2832 v2833
mul v2296 v2830
xor v2814 v489
mul v2836 v2831
add v2835 v2837
xor v2337 v495
mul v2839 v2833
add v2838 v2840
sub v2834 v2841
sub v2842 v2841
sub v2841 v2842
add v2843 v2844
div v2845 v163
shl v2846 1
sub 1 v2844
sub 1 v2848
add v2847 v2849
shr v2850 1
mul v724 v2851
add v2829 v2852
mul v2337 v2659
land v2826 1
xor v2855 v731
mul v2856 v2828
add v2854 v2857
land v2850 1
xor v2859 v737
mul v2860 v2852
add v2858 v2861
sub v2853 v2862
sub v2863 v2862
sub v2862 v2863
add v2864 v2865
div v2866 v313
shl v2867 1
sub 1 v2865
sub 1 v2869
add v2868 v2870
shr v2871 1
mul v753 v2872
add v2658 v2873
mul v509 v2333
mul v511 v2851
add v2875 v2876
mul v724 v2354
add v2877 v2878
mul v2341 v2875
xor v2859 v731
mul v2881 v2876
add v2880 v2882
xor v2382 v737
mul v2884 v2878
add v2883 v2885
sub v2879 v2886
sub v2887 v2886
sub v2886 v2887
add v2888 v2889
div v2890 v313
shl v2891 1
sub 1 v2889
sub 1 v2893
add v2892 v2894
shr v2895 1
mul v1012 v2896
add v2874 v2897
mul v2382 v2658
land v2871 1
xor v2900 v1019
mul v2901 v2873
add v2899 v2902
land v2895 1
xor v2904 v1025
mul v2905 v2897
add v2903 v2906
sub v2898 v2907
sub v2908 v2907
sub v2907 v2908
add v2909 v2910
div v2911 v509
shl v2912 1
sub 1 v2910
sub 1 v2914
add v2913 v2915
shr v2916 1
mul v1041 v2917
add v2657 v2918
mul v751 v2378
mul v753 v2896
add v2920 v2921
mul v1012 v2399
add v2922 v2923
mul v2386 v2920
xor v2904 v1019
mul v2926 v2921
add v2925 v2927
xor v2427 v1025
mul v2929 v2923
add v2928 v2930
sub v2924 v2931
sub v2932 v2931
sub v2931 v2932
add v2933 v2934
div v2935 v509
shl v2936 1
sub 1 v2934
sub 1 v2938
add v2937 v2939
shr v2940 1
mul v1346 v2941
add v2919 v2942
mul v2427 v2657
land v2916 1
xor v2945 v1353
mul v2946 v2918
add v2944 v2947
land v2940 1
xor v2949 v1359
mul v2950 v2942
add v2948 v2951
sub v2943 v2952
sub v2953 v2952
sub v2952 v2953
add v2954 v2955
div v2956 v751
shl v2957 1
sub 1 v2955
sub 1 v2959
add v2958 v2960
shr v2961 1
mul v1375 v2962
add v2656 v2963
mul v1039 v2423
mul v1041 v2941
add v2965 v2966
mul v1346 v2444
add v2967 v2968
mul v2431 v2965
xor v2949 v1353
mul v2971 v2966
add v2970 v2972
xor v2472 v1359
mul v2974 v2968
add v2973 v2975
sub v2969 v2976
sub v2977 v2976
sub v2976 v2977
add v2978 v2979
div v2980 v751
shl v2981 1
sub 1 v2979
sub 1 v2983
add v2982 v2984
shr v2985 1
mul v1726 v2986
add v2964 v2987
mul v2472 v2656
land v2961 1
xor v2990 v1733
mul v2991 v2963
add v2989 v2992
land v2985 1
xor v2994 v1739
mul v2995 v2987
add v2993 v2996
sub v2988 v2997
sub v2998 v2997
sub v2997 v2998
add v2999 v3000
div v3001 v1039
shl v3002 1
sub 1 v3000
sub 1 v3004
add v3003 v3005
shr v3006 1
mul v1755 v3007
add v2655 v3008
mul v1373 v2468
mul v1375 v2986
add v3010 v3011
mul v1726 v2489
add v3012 v3013
mul v2476 v3010
xor v2994 v1733
mul v3016 v3011
add v3015 v3017
xor v2517 v1739
mul v3019 v3013
add v3018 v3020
sub v3014 v3021
sub v3022 v3021
sub v3021 v3022
add v3023 v3024
div v3025 v1039
shl v3026 1
sub 1 v3024
sub 1 v3028
add v3027 v3029
shr v3030 1
mul v2152 v3031
add v3009 v3032
mul v2517 v2655
land v3006 1
xor v3035 v2159
mul v3036 v3008
add v3034 v3037
land v3030 1
xor v3039 v2165
mul v3040 v3032
add v3038 v3041
sub v3033 v3042
sub v3043 v3042
sub v3042 v3043
add v3044 v3045
div v3046 v1373
shl v3047 1
sub 1 v3045
sub 1 v3049
add v3048 v3050
shr v3051 1
mul v2181 v3052
add v2654 v3053
mul v1753 v2513
mul v1755 v3031
add v3055 v3056
mul v2152 v2534
add v3057 v3058
mul v2521 v3055
xor v3039 v2159
mul v3061 v3056
add v3060 v3062
xor v2562 v2165
mul v3064 v3058
add v3063 v3065
sub v3059 v3066
sub v3067 v3066
sub v3066 v3067
add v3068 v3069
div v3070 v1373
shl v3071 1
sub 1 v3069
sub 1 v3073
add v3072 v3074
shr v3075 1
mul v2624 v3076
add v3054 v3077
mul v2562 v2654
land v3051 1
xor v3080 v2631
mul v3081 v3053
add v3079 v3082
land v3075 1
xor v3084 v2637
mul v3085 v3077
add v3083 v3086
sub v3078 v3087
sub v3088 v3087
sub v3087 v3088
add v3089 v3090
div v3091 v1753
shl v3092 1
sub 1 v3090
sub 1 v3094
add v3093 v3095
shr v3096 1
mul v2653 v3097
add v2652 v3098
mul v2650 v2604
mul v2179 v2558
mul v2181 v3076
add v3101 v3102
mul v2624 v2579
add v3103 v3104
mul v2566 v3101
xor v3084 v2631
mul v3107 v3102
add v3106 v3108
xor v2628 v2637
mul v3110 v3104
add v3109 v3111
sub v3105 v3112
sub v3113 v3112
sub v3112 v3113
add v3114 v3115
div v3116 v1753
shl v3117 1
sub 1 v3115
sub 1 v3119
add v3118 v3120
shr v3121 1
mul v2178 v3122
add v3100 v3123
xor v2649 v2603
land v3125 1
mul v3126 v3100
xor v2177 v3121
land v3128 1
xor v3129 1
mul v3130 v3123
add v3127 v3131
sub v3124 v3132
sub v3133 v3132
sub v3132 v3133
add v3134 v3135
div v3136 1
shl v3137 1
sub 1 v3135
sub 1 v3139
add v3138 v3140
shr v3141 1
mul v3142 v3122
add v3099 v3143
mul v2628 v2652
land v3096 1
xor v2649 v2177
land v3147 1
xor v3148 1
xor v3146 v3149
mul v3150 v3098
add v3145 v3151
land v3121 1
land v3141 1
xor v3154 1
xor v3153 v3155
mul v3156 v3143
add v3152 v3157
sub v3144 v3158
sub v3159 v3158
sub v3158 v3159
add v3160 v3161
div v3162 v2179
shl v3163 1
sub 1 v3161
sub 1 v3165
add v3164 v3166
shr v3167 1
mul v3168 v3168
mul v3169 v3097
mul v3168 v2650
mul v2651 v3052
mul v2179 v3007
mul v1753 v2962
mul v1373 v2917
mul v1039 v2872
mul v751 v2827
mul v509 v2782
mul v313 v2737
mul v163 v2690
mul v59 v2665
shr x24 1
mul v1 v3182
mul v5 0
add v3183 v3184
shr x48 1
mul v31 v3186
add v3185 v3187
land x24 1
mul v3189 v3183
xor 0 v39
mul v3191 v3184
add v3190 v3192
land x48 1
xor v3194 v45
mul v3195 v3187
add v3193 v3196
sub v3188 v3197
sub v3198 v3197
sub v3197 v3198
add v3199 v3200
div v3201 1
shl v3202 1
sub 1 v3200
sub 1 v3204
add v3203 v3205
shr v3206 1
mul v61 v3207
add v3181 v3208
shr x23 1
mul v1 v3210
mul v5 v3186
add v3211 v3212
mul v31 v2665
add v3213 v3214
land x23 1
mul v3216 v3211
xor v3194 v39
mul v3218 v3212
add v3217 v3219
xor v2673 v45
mul v3221 v3214
add v3220 v3222
sub v3215 v3223
sub v3224 v3223
sub v3223 v3224
add v3225 v3226
div v3227 1
shl v3228 1
sub 1 v3226
sub 1 v3230
add v3229 v3231
shr v3232 1
mul v136 v3233
add v3209 v3234
mul v2673 v3181
land v3206 1
xor v3237 v143
mul v3238 v3208
add v3236 v3239
land v3232 1
xor v3241 v149
mul v3242 v3234
add v3240 v3243
sub v3235 v3244
sub v3245 v3244
sub v3244 v3245
add v3246 v3247
div v3248 v1
shl v3249 1
sub 1 v3247
sub 1 v3251
add v3250 v3252
shr v3253 1
mul v165 v3254
add v3180 v3255
mul v59 v2668
mul v61 v3233
add v3257 v3258
mul v136 v2690
add v3259 v3260
mul v2677 v3257
xor v3241 v143
mul v3263 v3258
add v3262 v3264
xor v2720 v149
mul v3266 v3260
add v3265 v3267
sub v3261 v3268
sub v3269 v3268
sub v3268 v3269
add v3270 v3271
div v3272 v1
shl v3273 1
sub 1 v3271
sub 1 v3275
add v3274 v3276
shr v3277 1
mul v286 v3278
add v3256 v3279
mul v2720 v3180
land v3253 1
xor v3282 v293
mul v3283 v3255
add v3281 v3284
land v3277 1
xor v3286 v299
mul v3287 v3279
add v3285 v3288
sub v3280 v3289
sub v3290 v3289
sub v3289 v3290
add v3291 v3292
div v3293 v59
shl v3294 1
sub 1 v3292
sub 1 v3296
add v3295 v3297
shr v3298 1
mul v315 v3299
add v3179 v3300
mul v163 v2716
mul v165 v3278
add v3302 v3303
mul v286 v2737
add v3304 v3305
mul v2724 v3302
xor v3286 v293
mul v3308 v3303
add v3307 v3309
xor v2765 v299
mul v3311 v3305
add v3310 v3312
sub v3306 v3313
sub v3314 v3313
sub v3313 v3314
add v3315 v3316
div v3317 v59
shl v3318 1
sub 1 v3316
sub 1 v3320
add v3319 v3321
shr v3322 1
mul v482 v3323
add v3301 v3324
mul v2765 v3179
land v3298 1
xor v3327 v489
mul v3328 v3300
add v3326 v3329
land v3322 1
xor v3331 v495
mul v3332 v3324
add v3330 v3333
sub v3325 v3334
sub v3335 v3334
sub v3334 v3335
add v3336 v3337
div v3338 v163
shl v3339 1
sub 1 v3337
sub 1 v3341
add v3340 v3342
shr v3343 1
mul v511 v3344
add v3178 v3345
mul v313 v2761
mul v315 v3323
add v3347 v3348
mul v482 v2782
add v3349 v3350
mul v2769 v3347
xor v3331 v489
mul v3353 v3348
add v3352 v3354
xor v2810 v495
mul v3356 v3350
add v3355 v3357
sub v3351 v3358
sub v3359 v3358
sub v3358 v3359
add v3360 v3361
div v3362 v163
shl v3363 1
sub 1 v3361
sub 1 v3365
add v3364 v3366
shr v3367 1
mul v724 v3368
add v3346 v3369
mul v2810 v3178
land v3343 1
xor v3372 v731
mul v3373 v3345
add v3371 v3374
land v3367 1
xor v3376 v737
mul v3377 v3369
add v3375 v3378
sub v3370 v3379
sub v3380 v3379
sub v3379 v3380
add v3381 v3382
div v3383 v313
shl v3384 1
sub 1 v3382
sub 1 v3386
add v3385 v3387
shr v3388 1
mul v753 v3389
add v3177 v3390
mul v509 v2806
mul v511 v3368
add v3392 v3393
mul v724 v2827
add v3394 v3395
mul v2814 v3392
xor v3376 v731
mul v3398 v3393
add v3397 v3399
xor v2855 v737
mul v3401 v3395
add v3400 v3402
sub v3396 v3403
sub v3404 v3403
sub v3403 v3404
add v3405 v3406
div v3407 v313
shl v3408 1
sub 1 v3406
sub 1 v3410
add v3409 v3411
shr v3412 1
mul v1012 v3413
add v3391 v3414
mul v2855 v3177
land v3388 1
xor v3417 v1019
mul v3418 v3390
add v3416 v3419
land v3412 1
xor v3421 v1025
mul v3422 v3414
add v3420 v3423
sub v3415 v3424
sub v3425 v3424
sub v3424 v3425
add v3426 v3427
div v3428 v509
shl v3429 1
sub 1 v3427
sub 1 v3431
add v3430 v3432
shr v3433 1
mul v1041 v3434
add v3176 v3435
mul v751 v2851
mul v753 v3413
add v3437 v3438
mul v1012 v2872
add v3439 v3440
mul v2859 v3437
xor v3421 v1019
mul v3443 v3438
add v3442 v3444
xor v2900 v1025
mul v3446 v3440
add v3445 v3447
sub v3441 v3448
sub v3449 v3448
sub v3448 v3449
add v3450 v3451
div v3452 v509
shl v3453 1
sub 1 v3451
sub 1 v3455
add v3454 v3456
shr v3457 1
mul v1346 v3458
add v3436 v3459
mul v2900 v3176
land v3433 1
xor v3462 v1353
mul v3463 v3435
add v3461 v3464
land v3457 1
xor v3466 v1359
mul v3467 v3459
add v3465 v3468
sub v3460 v3469
sub v3470 v3469
sub v3469 v3470
add v3471 v3472
div v3473 v751
shl v3474 1
sub 1 v3472
sub 1 v3476
add v3475 v3477
shr v3478 1
mul v1375 v3479
add v3175 v3480
mul v1039 v2896
mul v1041 v3458
add v3482 v3483
mul v1346 v2917
add v3484 v3485
mul v2904 v3482
xor v3466 v1353
mul v3488 v3483
add v3487 v3489
xor v2945 v1359
mul v3491 v3485
add v3490 v3492
sub v3486 v3493
sub v3494 v3493
sub v3493 v3494
add v3495 v3496
div v3497 v751
shl v3498 1
sub 1 v3496
sub 1 v3500
add v3499 v3501
shr v3502 1
mul v1726 v3503
add v3481 v3504
mul v2945 v3175
land v3478 1
xor v3507 v1733
mul v3508 v3480
add v3506 v3509
land v3502 1
xor v3511 v1739
mul v3512 v3504
add v3510 v3513
sub v3505 v3514
sub v3515 v3514
sub v3514 v3515
add v3516 v3517
div v3518 v1039
shl v3519 1
sub 1 v3517
sub 1 v3521
add v3520 v3522
shr v3523 1
mul v1755 v3524
add v3174 v3525
mul v1373 v2941
mul v1375 v3503
add v3527 v3528
mul v1726 v2962
add v3529 v3530
mul v2949 v3527
xor v3511 v1733
mul v3533 v3528
add v3532 v3534
xor v2990 v1739
mul v3536 v3530
add v3535 v3537
sub v3531 v3538
sub v3539 v3538
sub v3538 v3539
add v3540 v3541
div v3542 v1039
shl v3543 1
sub 1 v3541
sub 1 v3545
add v3544 v3546
shr v3547 1
mul v2152 v3548
add v3526 v3549
mul v2990 v3174
land v3523 1
xor v3552 v2159
mul v3553 v3525
add v3551 v3554
land v3547 1
xor v3556 v2165
mul v3557 v3549
add v3555 v3558
sub v3550 v3559
sub v3560 v3559
sub v3559 v3560
add v3561 v3562
div v3563 v1373
shl v3564 1
sub 1 v3562
sub 1 v3566
add v3565 v3567
shr v3568 1
mul v2181 v3569
add v3173 v3570
mul v1753 v2986
mul v1755 v3548
add v3572 v3573
mul v2152 v3007
add v3574 v3575
mul v2994 v3572
xor v3556 v2159
mul v3578 v3573
add v3577 v3579
xor v3035 v2165
mul v3581 v3575
add v3580 v3582
sub v3576 v3583
sub v3584 v3583
sub v3583 v3584
add v3585 v3586
div v3587 v1373
shl v3588 1
sub 1 v3586
sub 1 v3590
add v3589 v3591
shr v3592 1
mul v2624 v3593
add v3571 v3594
mul v3035 v3173
land v3568 1
xor v3597 v2631
mul v3598 v3570
add v3596 v3599
land v3592 1
xor v3601 v2637
mul v3602 v3594
add v3600 v3603
sub v3595 v3604
sub v3605 v3604
sub v3604 v3605
add v3606 v3607
div v3608 v1753
shl v3609 1
sub 1 v3607
sub 1 v3611
add v3610 v3612
shr v3613 1
mul v2653 v3614
add v3172 v3615
mul v2179 v3031
mul v2181 v3593
add v3617 v3618
mul v2624 v3052
add v3619 v3620
mul v3039 v3617
xor v3601 v2631
mul v3623 v3618
add v3622 v3624
xor v3080 v2637
mul v3626 v3620
add v3625 v3627
sub v3621 v3628
sub v3629 v3628
sub v3628 v3629
add v3630 v3631
div v3632 v1753
shl v3633 1
sub 1 v3631
sub 1 v3635
add v3634 v3636
shr v3637 1
mul v3142 v3638
add v3616 v3639
mul v3080 v3172
land v3613 1
xor v3642 v3149
mul v3643 v3615
add v3641 v3644
land v3637 1
xor v3646 v3155
mul v3647 v3639
add v3645 v3648
sub v3640 v3649
sub v3650 v3649
sub v3649 v3650
add v3651 v3652
div v3653 v2179
shl v3654 1
sub 1 v3652
sub 1 v3656
add v3655 v3657
shr v3658 1
mul v3171 v3659
add v3170 v3660
mul v3168 v3122
mul v2651 v3076
mul v2653 v3638
add v3663 v3664
mul v3142 v3097
add v3665 v3666
mul v3084 v3663
xor v3646 v3149
mul v3669 v3664
add v3668 v3670
xor v3146 v3155
mul v3672 v3666
add v3671 v3673
sub v3667 v3674
sub v3675 v3674
sub v3674 v3675
add v3676 v3677
div v3678 v2179
shl v3679 1
sub 1 v3677
sub 1 v3681
add v3680 v3682
shr v3683 1
mul v2650 v3684
add v3662 v3685
xor v3167 v3121
land v3687 1
mul v3688 v3662
xor v2649 v3683
land v3690 1
xor v3691 1
mul v3692 v3685
add v3689 v3693
sub v3686 v3694
sub v3695 v3694
sub v3694 v3695
add v3696 v3697
div v3698 1
shl v3699 1
sub 1 v3697
sub 1 v3701
add v3700 v3702
shr v3703 1
mul v3704 v3684
add v3661 v3705
mul v3146 v3170
land v3658 1
xor v3167 v2649
land v3709 1
xor v3710 1
xor v3708 v3711
mul v3712 v3660
add v3707 v3713
land v3683 1
land v3703 1
xor v3716 1
xor v3715 v3717
mul v3718 v3705
add v3714 v3719
sub v3706 v3720
sub v3721 v3720
sub v3720 v3721
add v3722 v3723
div v3724 v2651
shl v3725 1
sub 1 v3723
sub 1 v3727
add v3726 v3728
shr v3729 1
mul v3730 v3730
mul v3731 v3659
mul v3730 v3168
mul v3169 v3614
mul v2651 v3569
mul v2179 v3524
mul v1753 v3479
mul v1373 v3434
mul v1039 v3389
mul v751 v3344
mul v509 v3299
mul v313 v3254
mul v163 v3207
mul v165 0
add v3743 v3744
mul v59 v3186
mul v61 0
add v3746 v3747
mul v136 v3207
add v3748 v3749
mul v3194 v3746
xor 0 v143
mul v3752 v3747
add v3751 v3753
xor v3237 v149
mul v3755 v3749
add v3754 v3756
sub v3750 v3757
sub v3758 v3757
sub v3757 v3758
add v3759 v3760
div v3761 v1
shl v3762 1
sub 1 v3760
sub 1 v3764
add v3763 v3765
shr v3766 1
mul v286 v3767
add v3745 v3768
mul v3237 v3743
xor 0 v293
mul v3771 v3744
add v3770 v3772
land v3766 1
xor v3774 v299
mul v3775 v3768
add v3773 v3776
sub v3769 v3777
sub v3778 v3777
sub v3777 v3778
add v3779 v3780
div v3781 v59
shl v3782 1
sub 1 v3780
sub 1 v3784
add v3783 v3785
shr v3786 1
mul v315 v3787
add v3742 v3788
mul v163 v3233
mul v165 v3767
add v3790 v3791
mul v286 v3254
add v3792 v3793
mul v3241 v3790
xor v3774 v293
mul v3796 v3791
add v3795 v3797
xor v3282 v299
mul v3799 v3793
add v3798 v3800
sub v3794 v3801
sub v3802 v3801
sub v3801 v3802
add v3803 v3804
div v3805 v59
shl v3806 1
sub 1 v3804
sub 1 v3808
add v3807 v3809
shr v3810 1
mul v482 v3811
add v3789 v3812
mul v3282 v3742
land v3786 1
xor v3815 v489
mul v3816 v3788
add v3814 v3817
land v3810 1
xor v3819 v495
mul v3820 v3812
add v3818 v3821
sub v3813 v3822
sub v3823 v3822
sub v3822 v3823
add v3824 v3825
div v3826 v163
shl v3827 1
sub 1 v3825
sub 1 v3829
add v3828 v3830
shr v3831 1
mul v511 v3832
add v3741 v3833
mul v313 v3278
mul v315 v3811
add v3835 v3836
mul v482 v3299
add v3837 v3838
mul v3286 v3835
xor v3819 v489
mul v3841 v3836
add v3840 v3842
xor v3327 v495
mul v3844 v3838
add v3843 v3845
sub v3839 v3846
sub v3847 v3846
sub v3846 v3847
add v3848 v3849
div v3850 v163
shl v3851 1
sub 1 v3849
sub 1 v3853
add v3852 v3854
shr v3855 1
mul v724 v3856
add v3834 v3857
mul v3327 v3741
land v3831 1
xor v3860 v731
mul v3861 v3833
add v3859 v3862
land v3855 1
xor v3864 v737
mul v3865 v3857
add v3863 v3866
sub v3858 v3867
sub v3868 v3867
sub v3867 v3868
add v3869 v3870
div v3871 v313
shl v3872 1
sub 1 v3870
sub 1 v3874
add v3873 v3875
shr v3876 1
mul v753 v3877
add v3740 v3878
mul v509 v3323
mul v511 v3856
add v3880 v3881
mul v724 v3344
add v3882 v3883
mul v3331 v3880
xor v3864 v731
mul v3886 v3881
add v3885 v3887
xor v3372 v737
mul v3889 v3883
add v3888 v3890
sub v3884 v3891
sub v3892 v3891
sub v3891 v3892
add v3893 v3894
div v3895 v313
shl v3896 1
sub 1 v3894
sub 1 v3898
add v3897 v3899
shr v3900 1
mul v1012 v3901
add v3879 v3902
mul v3372 v3740
land v3876 1
xor v3905 v1019
mul v3906 v3878
add v3904 v3907
land v3900 1
xor v3909 v1025
mul v3910 v3902
add v3908 v3911
sub v3903 v3912
sub v3913 v3912
sub v3912 v3913
add v3914 v3915
div v3916 v509
shl v3917 1
sub 1 v3915
sub 1 v3919
add v3918 v3920
shr v3921 1
mul v1041 v3922
add v3739 v3923
mul v751 v3368
mul v753 v3901
add v3925 v3926
mul v1012 v3389
add v3927 v3928
mul v3376 v3925
xor v3909 v1019
mul v3931 v3926
add v3930 v3932
xor v3417 v1025
mul v3934 v3928
add v3933 v3935
sub v3929 v3936
sub v3937 v3936
sub v3936 v3937
add v3938 v3939
div v3940 v509
shl v3941 1
sub 1 v3939
sub 1 v3943
add v3942 v3944
shr v3945 1
mul v1346 v3946
add v3924 v3947
mul v3417 v3739
land v3921 1
xor v3950 v1353
mul v3951 v3923
add v3949 v3952
land v3945 1
xor v3954 v1359
mul v3955 v3947
add v3953 v3956
sub v3948 v3957
sub v3958 v3957
sub v3957 v3958
add v3959 v3960
div v3961 v751
shl v3962 1
sub 1 v3960
sub 1 v3964
add v3963 v3965
shr v3966 1
mul v1375 v3967
add v3738 v3968
mul v1039 v3413
mul v1041 v3946
add v3970 v3971
mul v1346 v3434
add v3972 v3973
mul v3421 v3970
xor v3954 v1353
mul v3976 v3971
add v3975 v3977
xor v3462 v1359
mul v3979 v3973
add v3978 v3980
sub v3974 v3981
sub v3982 v3981
sub v3981 v3982
add v3983 v3984
div v3985 v751
shl v3986 1
sub 1 v3984
sub 1 v3988
add v3987 v3989
shr v3990 1
mul v1726 v3991
add v3969 v3992
mul v3462 v3738
land v3966 1
xor v3995 v1733
mul v3996 v3968
add v3994 v3997
land v3990 1
xor v3999 v1739
mul v4000 v3992
add v3998 v4001
sub v3993 v4002
sub v4003 v4002
sub v4002 v4003
add v4004 v4005
div v4006 v1039
shl v4007 1
sub 1 v4005
sub 1 v4009
add v4008 v4010
shr v4011 1
mul v1755 v4012
add v3737 v4013
mul v1373 v3458
mul v1375 v3991
add v4015 v4016
mul v1726 v3479
add v4017 v4018
mul v3466 v4015
xor v3999 v1733
mul v4021 v4016
add v4020 v4022
xor v3507 v1739
mul v4024 v4018
add v4023 v4025
sub v4019 v4026
sub v4027 v4026
sub v4026 v4027
add v4028 v4029
div v4030 v1039
shl v4031 1
sub 1 v4029
sub 1 v4033
add v4032 v4034
shr v4035 1
mul v2152 v4036
add v4014 v4037
mul v3507 v3737
land v4011 1
xor v4040 v2159
mul v4041 v4013
add v4039 v4042
land v4035 1
xor v4044 v2165
mul v4045 v4037
add v4043 v4046
sub v4038 v4047
sub v4048 v4047
sub v4047 v4048
add v4049 v4050
div v4051 v1373
shl v4052 1
sub 1 v4050
sub 1 v4054
add v4053 v4055
shr v4056 1
mul v2181 v4057
add v3736 v4058
mul v1753 v3503
mul v1755 v4036
add v4060 v4061
mul v2152 v3524
add v4062 v4063
mul v3511 v4060
xor v4044 v2159
mul v4066 v4061
add v4065 v4067
xor v3552 v2165
mul v4069 v4063
add v4068 v4070
sub v4064 v4071
sub v4072 v4071
sub v4071 v4072
add v4073 v4074
div v4075 v1373
shl v4076 1
sub 1 v4074
sub 1 v4078
add v4077 v4079
shr v4080 1
mul v2624 v4081
add v4059 v4082
mul v3552 v3736
land v4056 1
xor v4085 v2631
mul v4086 v4058
add v4084 v4087
land v4080 1
xor v4089 v2637
mul v4090 v4082
add v4088 v4091
sub v4083 v4092
sub v4093 v4092
sub v4092 v4093
add v4094 v4095
div v4096 v1753
shl v4097 1
sub 1 v4095
sub 1 v4099
add v4098 v4100
shr v4101 1
mul v2653 v4102
add v3735 v4103
mul v2179 v3548
mul v2181 v4081
add v4105 v4106
mul v2624 v3569
add v4107 v4108
mul v3556 v4105
xor v4089 v2631
mul v4111 v4106
add v4110 v4112
xor v3597 v2637
mul v4114 v4108
add v4113 v4115
sub v4109 v4116
sub v4117 v4116
sub v4116 v4117
add v4118 v4119
div v4120 v1753
shl v4121 1
sub 1 v4119
sub 1 v4123
add v4122 v4124
shr v4125 1
mul v3142 v4126
add v4104 v4127
mul v3597 v3735
land v4101 1
xor v4130 v3149
mul v4131 v4103
add v4129 v4132
land v4125 1
xor v4134 v3155
mul v4135 v4127
add v4133 v4136
sub v4128 v4137
sub v4138 v4137
sub v4137 v4138
add v4139 v4140
div v4141 v2179
shl v4142 1
sub 1 v4140
sub 1 v4144
add v4143 v4145
shr v4146 1
mul v3171 v4147
add v3734 v4148
mul v2651 v3593
mul v2653 v4126
add v4150 v4151
mul v3142 v3614
add v4152 v4153
mul v3601 v4150
xor v4134 v3149
mul v4156 v4151
add v4155 v4157
xor v3642 v3155
mul v4159 v4153
add v4158 v4160
sub v4154 v4161
sub v4162 v4161
sub v4161 v4162
add v4163 v4164
div v4165 v2179
shl v4166 1
sub 1 v4164
sub 1 v4168
add v4167 v4169
shr v4170 1
mul v3704 v4171
add v4149 v4172
mul v3642 v3734
land v4146 1
xor v4175 v3711
mul v4176 v4148
add v4174 v4177
land v4170 1
xor v4179 v3717
mul v4180 v4172
add v4178 v4181
sub v4173 v4182
sub v4183 v4182
sub v4182 v4183
add v4184 v4185
div v4186 v2651
shl v4187 1
sub 1 v4185
sub 1 v4189
add v4188 v4190
shr v4191 1
mul v3733 v4192
add v3732 v4193
mul v3730 v3684
mul v3169 v3638
mul v3171 v4171
add v4196 v4197
mul v3704 v3659
add v4198 v4199
mul v3646 v4196
xor v4179 v3711
mul v4202 v4197
add v4201 v4203
xor v3708 v3717
mul v4205 v4199
add v4204 v4206
sub v4200 v4207
sub v4208 v4207
sub v4207 v4208
add v4209 v4210
div v4211 v2651
shl v4212 1
sub 1 v4210
sub 1 v4214
add v4213 v4215
shr v4216 1
mul v3168 v4217
add v4195 v4218
xor v3729 v3683
land v4220 1
mul v4221 v4195
xor v3167 v4216
land v4223 1
xor v4224 1
mul v4225 v4218
add v4222 v4226
sub v4219 v4227
sub v4228 v4227
sub v4227 v4228
add v4229 v4230
div v4231 1
shl v4232 1
sub 1 v4230
sub 1 v4234
add v4233 v4235
shr v4236 1
mul v4237 v4217
add v4194 v4238
mul v3708 v3732
land v4191 1
xor v3729 v3167
land v4242 1
xor v4243 1
xor v4241 v4244
mul v4245 v4193
add v4240 v4246
land v4216 1
land v4236 1
xor v4249 1
xor v4248 v4250
mul v4251 v4238
add v4247 v4252
sub v4239 v4253
sub v4254 v4253
sub v4253 v4254
add v4255 v4256
div v4257 v3169
shl v4258 1
sub 1 v4256
sub 1 v4260
add v4259 v4261
shr v4262 1
mul v4263 v4263
mul v4264 v4192
mul v4263 v3730
mul v3731 v4147
mul v3169 v4102
mul v2651 v4057
mul v2179 v4012
mul v1753 v3967
mul v1373 v3922
mul v1039 v3877
mul v751 v3832
mul v509 v3787
mul v511 0
add v4275 v4276
mul v313 v3767
mul v315 0
add v4278 v4279
mul v482 v3787
add v4280 v4281
mul v3774 v4278
xor 0 v489
mul v4284 v4279
add v4283 v4285
xor v3815 v495
mul v4287 v4281
add v4286 v4288
sub v4282 v4289
sub v4290 v4289
sub v4289 v4290
add v4291 v4292
div v4293 v163
shl v4294 1
sub 1 v4292
sub 1 v4296
add v4295 v4297
shr v4298 1
mul v724 v4299
add v4277 v4300
mul v3815 v4275
xor 0 v731
mul v4303 v4276
add v4302 v4304
land v4298 1
xor v4306 v737
mul v4307 v4300
add v4305 v4308
sub v4301 v4309
sub v4310 v4309
sub v4309 v4310
add v4311 v4312
div v4313 v313
shl v4314 1
sub 1 v4312
sub 1 v4316
add v4315 v4317
shr v4318 1
mul v753 v4319
add v4274 v4320
mul v509 v3811
mul v511 v4299
add v4322 v4323
mul v724 v3832
add v4324 v4325
mul v3819 v4322
xor v4306 v731
mul v4328 v4323
add v4327 v4329
xor v3860 v737
mul v4331 v4325
add v4330 v4332
sub v4326 v4333
sub v4334 v4333
sub v4333 v4334
add v4335 v4336
div v4337 v313
shl v4338 1
sub 1 v4336
sub 1 v4340
add v4339 v4341
shr v4342 1
mul v1012 v4343
add v4321 v4344
mul v3860 v4274
land v4318 1
xor v4347 v1019
mul v4348 v4320
add v4346 v4349
land v4342 1
xor v4351 v1025
mul v4352 v4344
add v4350 v4353
sub v4345 v4354
sub v4355 v4354
sub v4354 v4355
add v4356 v4357
div v4358 v509
shl v4359 1
sub 1 v4357
sub 1 v4361
add v4360 v4362
shr v4363 1
mul v1041 v4364
add v4273 v4365
mul v751 v3856
mul v753 v4343
add v4367 v4368
mul v1012 v3877
add v4369 v4370
mul v3864 v4367
xor v4351 v1019
mul v4373 v4368
add v4372 v4374
xor v3905 v1025
mul v4376 v4370
add v4375 v4377
sub v4371 v4378
sub v4379 v4378
sub v4378 v4379
add v4380 v4381
div v4382 v509
shl v4383 1
sub 1 v4381
sub 1 v4385
add v4384 v4386
shr v4387 1
mul v1346 v4388
add v4366 v4389
mul v3905 v4273
land v4363 1
xor v4392 v1353
mul v4393 v4365
add v4391 v4394
land v4387 1
xor v4396 v1359
mul v4397 v4389
add v4395 v4398
sub v4390 v4399
sub v4400 v4399
sub v4399 v4400
add v4401 v4402
div v4403 v751
shl v4404 1
sub 1 v4402
sub 1 v4406
add v4405 v4407
shr v4408 1
mul v1375 v4409
add v4272 v4410
mul v1039 v3901
mul v1041 v4388
add v4412 v4413
mul v1346 v3922
add v4414 v4415
mul v3909 v4412
xor v4396 v1353
mul v4418 v4413
add v4417 v4419
xor v3950 v1359
mul v4421 v4415
add v4420 v4422
sub v4416 v4423
sub v4424 v4423
sub v4423 v4424
add v4425 v4426
div v4427 v751
shl v4428 1
sub 1 v4426
sub 1 v4430
add v4429 v4431
shr v4432 1
mul v1726 v4433
add v4411 v4434
mul v3950 v4272
land v4408 1
xor v4437 v1733
mul v4438 v4410
add v4436 v4439
land v4432 1
xor v4441 v1739
mul v4442 v4434
add v4440 v4443
sub v4435 v4444
sub v4445 v4444
sub v4444 v4445
add v4446 v4447
div v4448 v1039
shl v4449 1
sub 1 v4447
sub 1 v4451
add v4450 v4452
shr v4453 1
mul v1755 v4454
add v4271 v4455
mul v1373 v3946
mul v1375 v4433
add v4457 v4458
mul v1726 v3967
add v4459 v4460
mul v3954 v4457
xor v4441 v1733
mul v4463 v4458
add v4462 v4464
xor v3995 v1739
mul v4466 v4460
add v4465 v4467
sub v4461 v4468
sub v4469 v4468
sub v4468 v4469
add v4470 v4471
div v4472 v1039
shl v4473 1
sub 1 v4471
sub 1 v4475
add v4474 v4476
shr v4477 1
mul v2152 v4478
add v4456 v4479
mul v3995 v4271
land v4453 1
xor v4482 v2159
mul v4483 v4455
add v4481 v4484
land v4477 1
xor v4486 v2165
mul v4487 v4479
add v4485 v4488
sub v4480 v4489
sub v4490 v4489
sub v4489 v4490
add v4491 v4492
div v4493 v1373
shl v4494 1
sub 1 v4492
sub 1 v4496
add v4495 v4497
shr v4498 1
mul v2181 v4499
add v4270 v4500
mul v1753 v3991
mul v1755 v4478
add v4502 v4503
mul v2152 v4012
add v4504 v4505
mul v3999 v4502
xor v4486 v2159
mul v4508 v4503
add v4507 v4509
xor v4040 v2165
mul v4511 v4505
add v4510 v4512
sub v4506 v4513
sub v4514 v4513
sub v4513 v4514
add v4515 v4516
div v4517 v1373
shl v4518 1
sub 1 v4516
sub 1 v4520
add v4519 v4521
shr v4522 1
mul v2624 v4523
add v4501 v4524
mul v4040 v4270
land v4498 1
xor v4527 v2631
mul v4528 v4500
add v4526 v4529
land v4522 1
xor v4531 v2637
mul v4532 v4524
add v4530 v4533
sub v4525 v4534
sub v4535 v4534
sub v4534 v4535
add v4536 v4537
div v4538 v1753
shl v4539 1
sub 1 v4537
sub 1 v4541
add v4540 v4542
shr v4543 1
mul v2653 v4544
add v4269 v4545
mul v2179 v4036
mul v2181 v4523
add v4547 v4548
mul v2624 v4057
add v4549 v4550
mul v4044 v4547
xor v4531 v2631
mul v4553 v4548
add v4552 v4554
xor v4085 v2637
mul v4556 v4550
add v4555 v4557
sub v4551 v4558
sub v4559 v4558
sub v4558 v4559
add v4560 v4561
div v4562 v1753
shl v4563 1
sub 1 v4561
sub 1 v4565
add v4564 v4566
shr v4567 1
mul v3142 v4568
add v4546 v4569
mul v4085 v4269
land v4543 1
xor v4572 v3149
mul v4573 v4545
add v4571 v4574
land v4567 1
xor v4576 v3155
mul v4577 v4569
add v4575 v4578
sub v4570 v4579
sub v4580 v4579
sub v4579 v4580
add v4581 v4582
div v4583 v2179
shl v4584 1
sub 1 v4582
sub 1 v4586
add v4585 v4587
shr v4588 1
mul v3171 v4589
add v4268 v4590
mul v2651 v4081
mul v2653 v4568
add v4592 v4593
mul v3142 v4102
add v4594 v4595
mul v4089 v4592
xor v4576 v3149
mul v4598 v4593
add v4597 v4599
xor v4130 v3155
mul v4601 v4595
add v4600 v4602
sub v4596 v4603
sub v4604 v4603
sub v4603 v4604
add v4605 v4606
div v4607 v2179
shl v4608 1
sub 1 v4606
sub 1 v4610
add v4609 v4611
shr v4612 1
mul v3704 v4613
add v4591 v4614
mul v4130 v4268
land v4588 1
xor v4617 v3711
mul v4618 v4590
add v4616 v4619
land v4612 1
xor v4621 v3717
mul v4622 v4614
add v4620 v4623
sub v4615 v4624
sub v4625 v4624
sub v4624 v4625
add v4626 v4627
div v4628 v2651
shl v4629 1
sub 1 v4627
sub 1 v4631
add v4630 v4632
shr v4633 1
mul v3733 v4634
add v4267 v4635
mul v3169 v4126
mul v3171 v4613
add v4637 v4638
mul v3704 v4147
add v4639 v4640
mul v4134 v4637
xor v4621 v3711
mul v4643 v4638
add v4642 v4644
xor v4175 v3717
mul v4646 v4640
add v4645 v4647
sub v4641 v4648
sub v4649 v4648
sub v4648 v4649
add v4650 v4651
div v4652 v2651
shl v4653 1
sub 1 v4651
sub 1 v4655
add v4654 v4656
shr v4657 1
mul v4237 v4658
add v4636 v4659
mul v4175 v4267
land v4633 1
xor v4662 v4244
mul v4663 v4635
add v4661 v4664
land v4657 1
xor v4666 v4250
mul v4667 v4659
add v4665 v4668
sub v4660 v4669
sub v4670 v4669
sub v4669 v4670
add v4671 v4672
div v4673 v3169
shl v4674 1
sub 1 v4672
sub 1 v4676
add v4675 v4677
shr v4678 1
mul v4266 v4679
add v4265 v4680
mul v4263 v4217
mul v3731 v4171
mul v3733 v4658
add v4683 v4684
mul v4237 v4192
add v4685 v4686
mul v4179 v4683
xor v4666 v4244
mul v4689 v4684
add v4688 v4690
xor v4241 v4250
mul v4692 v4686
add v4691 v4693
sub v4687 v4694
sub v4695 v4694
sub v4694 v4695
add v4696 v4697
div v4698 v3169
shl v4699 1
sub 1 v4697
sub 1 v4701
add v4700 v4702
shr v4703 1
mul v3730 v4704
add v4682 v4705
xor v4262 v4216
land v4707 1
mul v4708 v4682
xor v3729 v4703
land v4710 1
xor v4711 1
mul v4712 v4705
add v4709 v4713
sub v4706 v4714
sub v4715 v4714
sub v4714 v4715
add v4716 v4717
div v4718 1
shl v4719 1
sub 1 v4717
sub 1 v4721
add v4720 v4722
shr v4723 1
mul v4724 v4704
add v4681 v4725
mul v4241 v4265
land v4678 1
xor v4262 v3729
land v4729 1
xor v4730 1
xor v4728 v4731
mul v4732 v4680
add v4727 v4733
land v4703 1
land v4723 1
xor v4736 1
xor v4735 v4737
mul v4738 v4725
add v4734 v4739
sub v4726 v4740
sub v4741 v4740
sub v4740 v4741
add v4742 v4743
div v4744 v3731
shl v4745 1
sub 1 v4743
sub 1 v4747
add v4746 v4748
shr v4749 1
mul v4750 v4750
mul v4751 v4679
mul v4750 v4263
mul v4264 v4634
mul v3731 v4589
mul v3169 v4544
mul v2651 v4499
mul v2179 v4454
mul v1753 v4409
mul v1373 v4364
mul v1039 v4319
mul v1041 0
add v4761 v4762
mul v751 v4299
mul v753 0
add v4764 v4765
mul v1012 v4319
add v4766 v4767
mul v4306 v4764
xor 0 v1019
mul v4770 v4765
add v4769 v4771
xor v4347 v1025
mul v4773 v4767
add v4772 v4774
sub v4768 v4775
sub v4776 v4775
sub v4775 v4776
add v4777 v4778
div v4779 v509
shl v4780 1
sub 1 v4778
sub 1 v4782
add v4781 v4783
shr v4784 1
mul v1346 v4785
add v4763 v4786
mul v4347 v4761
xor 0 v1353
mul v4789 v4762
add v4788 v4790
land v4784 1
xor v4792 v1359
mul v4793 v4786
add v4791 v4794
sub v4787 v4795
sub v4796 v4795
sub v4795 v4796
add v4797 v4798
div v4799 v751
shl v4800 1
sub 1 v4798
sub 1 v4802
add v4801 v4803
shr v4804 1
mul v1375 v4805
add v4760 v4806
mul v1039 v4343
mul v1041 v4785
add v4808 v4809
mul v1346 v4364
add v4810 v4811
mul v4351 v4808
xor v4792 v1353
mul v4814 v4809
add v4813 v4815
xor v4392 v1359
mul v4817 v4811
add v4816 v4818
sub v4812 v4819
sub v4820 v4819
sub v4819 v4820
add v4821 v4822
div v4823 v751
shl v4824 1
sub 1 v4822
sub 1 v4826
add v4825 v4827
shr v4828 1
mul v1726 v4829
add v4807 v4830
mul v4392 v4760
land v4804 1
xor v4833 v1733
mul v4834 v4806
add v4832 v4835
land v4828 1
xor v4837 v1739
mul v4838 v4830
add v4836 v4839
sub v4831 v4840
sub v4841 v4840
sub v4840 v4841
add v4842 v4843
div v4844 v1039
shl v4845 1
sub 1 v4843
sub 1 v4847
add v4846 v4848
shr v4849 1
mul v1755 v4850
add v4759 v4851
mul v1373 v4388
mul v1375 v4829
add v4853 v4854
mul v1726 v4409
add v4855 v4856
mul v4396 v4853
xor v4837 v1733
mul v4859 v4854
add v4858 v4860
xor v4437 v1739
mul v4862 v4856
add v4861 v4863
sub v4857 v4864
sub v4865 v4864
sub v4864 v4865
add v4866 v4867
div v4868 v1039
shl v4869 1
sub 1 v4867
sub 1 v4871
add v4870 v4872
shr v4873 1
mul v2152 v4874
add v4852 v4875
mul v4437 v4759
land v4849 1
xor v4878 v2159
mul v4879 v4851
add v4877 v4880
land v4873 1
xor v4882 v2165
mul v4883 v4875
add v4881 v4884
sub v4876 v4885
sub v4886 v4885
sub v4885 v4886
add v4887 v4888
div v4889 v1373
shl v4890 1
sub 1 v4888
sub 1 v4892
add v4891 v4893
shr v4894 1
mul v2181 v4895
add v4758 v4896
mul v1753 v4433
mul v1755 v4874
add v4898 v4899
mul v2152 v4454
add v4900 v4901
mul v4441 v4898
xor v4882 v2159
mul v4904 v4899
add v4903 v4905
xor v4482 v2165
mul v4907 v4901
add v4906 v4908
sub v4902 v4909
sub v4910 v4909
sub v4909 v4910
add v4911 v4912
div v4913 v1373
shl v4914 1
sub 1 v4912
sub 1 v4916
add v4915 v4917
shr v4918 1
mul v2624 v4919
add v4897 v4920
mul v4482 v4758
land v4894 1
xor v4923 v2631
mul v4924 v4896
add v4922 v4925
land v4918 1
xor v4927 v2637
mul v4928 v4920
add v4926 v4929
sub v4921 v4930
sub v4931 v4930
sub v4930 v4931
add v4932 v4933
div v4934 v1753
shl v4935 1
sub 1 v4933
sub 1 v4937
add v4936 v4938
shr v4939 1
mul v2653 v4940
add v4757 v4941
mul v2179 v4478
mul v2181 v4919
add v4943 v4944
mul v2624 v4499
add v4945 v4946
mul v4486 v4943
xor v4927 v2631
mul v4949 v4944
add v4948 v4950
xor v4527 v2637
mul v4952 v4946
add v4951 v4953
sub v4947 v4954
sub v4955 v4954
sub v4954 v4955
add v4956 v4957
div v4958 v1753
shl v4959 1
sub 1 v4957
sub 1 v4961
add v4960 v4962
shr v4963 1
mul v3142 v4964
add v4942 v4965
mul v4527 v4757
land v4939 1
xor v4968 v3149
mul v4969 v4941
add v4967 v4970
land v4963 1
xor v4972 v3155
mul v4973 v4965
add v4971 v4974
sub v4966 v4975
sub v4976 v4975
sub v4975 v4976
add v4977 v4978
div v4979 v2179
shl v4980 1
sub 1 v4978
sub 1 v4982
add v4981 v4983
shr v4984 1
mul v3171 v4985
add v4756 v4986
mul v2651 v4523
mul v2653 v4964
add v4988 v4989
mul v3142 v4544
add v4990 v4991
mul v4531 v4988
xor v4972 v3149
mul v4994 v4989
add v4993 v4995
xor v4572 v3155
mul v4997 v4991
add v4996 v4998
sub v4992 v4999
sub v5000 v4999
sub v4999 v5000
add v5001 v5002
div v5003 v2179
shl v5004 1
sub 1 v5002
sub 1 v5006
add v5005 v5007
shr v5008 1
mul v3704 v5009
add v4987 v5010
mul v4572 v4756
land v4984 1
xor v5013 v3711
mul v5014 v4986
add v5012 v5015
land v5008 1
xor v5017 v3717
mul v5018 v5010
add v5016 v5019
sub v5011 v5020
sub v5021 v5020
sub v5020 v5021
add v5022 v5023
div v5024 v2651
shl v5025 1
sub 1 v5023
sub 1 v5027
add v5026 v5028
shr v5029 1
mul v3733 v5030
add v4755 v5031
mul v3169 v4568
mul v3171 v5009
add v5033 v5034
mul v3704 v4589
add v5035 v5036
mul v4576 v5033
xor v5017 v3711
mul v5039 v5034
add v5038 v5040
xor v4617 v3717
mul v5042 v5036
add v5041 v5043
sub v5037 v5044
sub v5045 v5044
sub v5044 v5045
add v5046 v5047
div v5048 v2651
shl v5049 1
sub 1 v5047
sub 1 v5051
add v5050 v5052
shr v5053 1
mul v4237 v5054
add v5032 v5055
mul v4617 v4755
land v5029 1
xor v5058 v4244
mul v5059 v5031
add v5057 v5060
land v5053 1
xor v5062 v4250
mul v5063 v5055
add v5061 v5064
sub v5056 v5065
sub v5066 v5065
sub v5065 v5066
add v5067 v5068
div v5069 v3169
shl v5070 1
sub 1 v5068
sub 1 v5072
add v5071 v5073
shr v5074 1
mul v4266 v5075
add v4754 v5076
mul v3731 v4613
mul v3733 v5054
add v5078 v5079
mul v4237 v4634
add v5080 v5081
mul v4621 v5078
xor v5062 v4244
mul v5084 v5079
add v5083 v5085
xor v4662 v4250
mul v5087 v5081
add v5086 v5088
sub v5082 v5089
sub v5090 v5089
sub v5089 v5090
add v5091 v5092
div v5093 v3169
shl v5094 1
sub 1 v5092
sub 1 v5096
add v5095 v5097
shr v5098 1
mul v4724 v5099
add v5077 v5100
mul v4662 v4754
land v5074 1
xor v5103 v4731
mul v5104 v5076
add v5102 v5105
land v5098 1
xor v5107 v4737
mul v5108 v5100
add v5106 v5109
sub v5101 v5110
sub v5111 v5110
sub v5110 v5111
add v5112 v5113
div v5114 v3731
shl v5115 1
sub 1 v5113
sub 1 v5117
add v5116 v5118
shr v5119 1
mul v4753 v5120
add v4752 v5121
mul v4750 v4704
mul v4264 v4658
mul v4266 v5099
add v5124 v5125
mul v4724 v4679
add v5126 v5127
mul v4666 v5124
xor v5107 v4731
mul v5130 v5125
add v5129 v5131
xor v4728 v4737
mul v5133 v5127
add v5132 v5134
sub v5128 v5135
sub v5136 v5135
sub v5135 v5136
add v5137 v5138
div v5139 v3731
shl v5140 1
sub 1 v5138
sub 1 v5142
add v5141 v5143
shr v5144 1
mul v4263 v5145
add v5123 v5146
xor v4749 v4703
land v5148 1
mul v5149 v5123
xor v4262 v5144
land v5151 1
xor v5152 1
mul v5153 v5146
add v5150 v5154
sub v5147 v5155
sub v5156 v5155
sub v5155 v5156
add v5157 v5158
div v5159 1
shl v5160 1
sub 1 v5158
sub 1 v5162
add v5161 v5163
shr v5164 1
mul v5165 v5145
add v5122 v5166
mul v4728 v4752
land v5119 1
xor v4749 v4262
land v5170 1
xor v5171 1
xor v5169 v5172
mul v5173 v5121
add v5168 v5174
land v5144 1
land v5164 1
xor v5177 1
xor v5176 v5178
mul v5179 v5166
add v5175 v5180
sub v5167 v5181
sub v5182 v5181
sub v5181 v5182
add v5183 v5184
div v5185 v4264
shl v5186 1
sub 1 v5184
sub 1 v5188
add v5187 v5189
shr v5190 1
mul v5191 v5191
mul v5192 v5120
mul v5191 v4750
mul v4751 v5075
mul v4264 v5030
mul v3731 v4985
mul v3169 v4940
mul v2651 v4895
mul v2179 v4850
mul v1753 v4805
mul v1755 0
add v5201 v5202
mul v1373 v4785
mul v1375 0
add v5204 v5205
mul v1726 v4805
add v5206 v5207
mul v4792 v5204
xor 0 v1733
mul v5210 v5205
add v5209 v5211
xor v4833 v1739
mul v5213 v5207
add v5212 v5214
sub v5208 v5215
sub v5216 v5215
sub v5215 v5216
add v5217 v5218
div v5219 v1039
shl v5220 1
sub 1 v5218
sub 1 v5222
add v5221 v5223
shr v5224 1
mul v2152 v5225
add v5203 v5226
mul v4833 v5201
xor 0 v2159
mul v5229 v5202
add v5228 v5230
land v5224 1
xor v5232 v2165
mul v5233 v5226
add v5231 v5234
sub v5227 v5235
sub v5236 v5235
sub v5235 v5236
add v5237 v5238
div v5239 v1373
shl v5240 1
sub 1 v5238
sub 1 v5242
add v5241 v5243
shr v5244 1
mul v2181 v5245
add v5200 v5246
mul v1753 v4829
mul v1755 v5225
add v5248 v5249
mul v2152 v4850
add v5250 v5251
mul v4837 v5248
xor v5232 v2159
mul v5254 v5249
add v5253 v5255
xor v4878 v2165
mul v5257 v5251
add v5256 v5258
sub v5252 v5259
sub v5260 v5259
sub v5259 v5260
add v5261 v5262
div v5263 v1373
shl v5264 1
sub 1 v5262
sub 1 v5266
add v5265 v5267
shr v5268 1
mul v2624 v5269
add v5247 v5270
mul v4878 v5200
land v5244 1
xor v5273 v2631
mul v5274 v5246
add v5272 v5275
land v5268 1
xor v5277 v2637
mul v5278 v5270
add v5276 v5279
sub v5271 v5280
sub v5281 v5280
sub v5280 v5281
add v5282 v5283
div v5284 v1753
shl v5285 1
sub 1 v5283
sub 1 v5287
add v5286 v5288
shr v5289 1
mul v2653 v5290
add v5199 v5291
mul v2179 v4874
mul v2181 v5269
add v5293 v5294
mul v2624 v4895
add v5295 v5296
mul v4882 v5293
xor v5277 v2631
mul v5299 v5294
add v5298 v5300
xor v4923 v2637
mul v5302 v5296
add v5301 v5303
sub v5297 v5304
sub v5305 v5304
sub v5304 v5305
add v5306 v5307
div v5308 v1753
shl v5309 1
sub 1 v5307
sub 1 v5311
add v5310 v5312
shr v5313 1
mul v3142 v5314
add v5292 v5315
mul v4923 v5199
land v5289 1
xor v5318 v3149
mul v5319 v5291
add v5317 v5320
land v5313 1
xor v5322 v3155
mul v5323 v5315
add v5321 v5324
sub v5316 v5325
sub v5326 v5325
sub v5325 v5326
add v5327 v5328
div v5329 v2179
shl v5330 1
sub 1 v5328
sub 1 v5332
add v5331 v5333
shr v5334 1
mul v3171 v5335
add v5198 v5336
mul v2651 v4919
mul v2653 v5314
add v5338 v5339
mul v3142 v4940
add v5340 v5341
mul v4927 v5338
xor v5322 v3149
mul v5344 v5339
add v5343 v5345
xor v4968 v3155
mul v5347 v5341
add v5346 v5348
sub v5342 v5349
sub v5350 v5349
sub v5349 v5350
add v5351 v5352
div v5353 v2179
shl v5354 1
sub 1 v5352
sub 1 v5356
add v5355 v5357
shr v5358 1
mul v3704 v5359
add v5337 v5360
mul v4968 v5198
land v5334 1
xor v5363 v3711
mul v5364 v5336
add v5362 v5365
land v5358 1
xor v5367 v3717
mul v5368 v5360
add v5366 v5369
sub v5361 v5370
sub v5371 v5370
sub v5370 v5371
add v5372 v5373
div v5374 v2651
shl v5375 1
sub 1 v5373
sub 1 v5377
add v5376 v5378
shr v5379 1
mul v3733 v5380
add v5197 v5381
mul v3169 v4964
mul v3171 v5359
add v5383 v5384
mul v3704 v4985
add v5385 v5386
mul v4972 v5383
xor v5367 v3711
mul v5389 v5384
add v5388 v5390
xor v5013 v3717
mul v5392 v5386
add v5391 v5393
sub v5387 v5394
sub v5395 v5394
sub v5394 v5395
add v5396 v5397
div v5398 v2651
shl v5399 1
sub 1 v5397
sub 1 v5401
add v5400 v5402
shr v5403 1
mul v4237 v5404
add v5382 v5405
mul v5013 v5197
land v5379 1
xor v5408 v4244
mul v5409 v5381
add v5407 v5410
land v5403 1
xor v5412 v4250
mul v5413 v5405
add v5411 v5414
sub v5406 v5415
sub v5416 v5415
sub v5415 v5416
add v5417 v5418
div v5419 v3169
shl v5420 1
sub 1 v5418
sub 1 v5422
add v5421 v5423
shr v5424 1
mul v4266 v5425
add v5196 v5426
mul v3731 v5009
mul v3733 v5404
add v5428 v5429
mul v4237 v5030
add v5430 v5431
mul v5017 v5428
xor v5412 v4244
mul v5434 v5429
add v5433 v5435
xor v5058 v4250
mul v5437 v5431
add v5436 v5438
sub v5432 v5439
sub v5440 v5439
sub v5439 v5440
add v5441 v5442
div v5443 v3169
shl v5444 1
sub 1 v5442
sub 1 v5446
add v5445 v5447
shr v5448 1
mul v4724 v5449
add v5427 v5450
mul v5058 v5196
land v5424 1
xor v5453 v4731
mul v5454 v5426
add v5452 v5455
land v5448 1
xor v5457 v4737
mul v5458 v5450
add v5456 v5459
sub v5451 v5460
sub v5461 v5460
sub v5460 v5461
add v5462 v5463
div v5464 v3731
shl v5465 1
sub 1 v5463
sub 1 v5467
add v5466 v5468
shr v5469 1
mul v4753 v5470
add v5195 v5471
mul v4264 v5054
mul v4266 v5449
add v5473 v5474
mul v4724 v5075
add v5475 v5476
mul v5062 v5473
xor v5457 v4731
mul v5479 v5474
add v5478 v5480
xor v5103 v4737
mul v5482 v5476
add v5481 v5483
sub v5477 v5484
sub v5485 v5484
sub v5484 v5485
add v5486 v5487
div v5488 v3731
shl v5489 1
sub 1 v5487
sub 1 v5491
add v5490 v5492
shr v5493 1
mul v5165 v5494
add v5472 v5495
mul v5103 v5195
land v5469 1
xor v5498 v5172
mul v5499 v5471
add v5497 v5500
land v5493 1
xor v5502 v5178
mul v5503 v5495
add v5501 v5504
sub v5496 v5505
sub v5506 v5505
sub v5505 v5506
add v5507 v5508
div v5509 v4264
shl v5510 1
sub 1 v5508
sub 1 v5512
add v5511 v5513
shr v5514 1
mul v5194 v5515
add v5193 v5516
mul v5191 v5145
mul v4751 v5099
mul v4753 v5494
add v5519 v5520
mul v5165 v5120
add v5521 v5522
mul v5107 v5519
xor v5502 v5172
mul v5525 v5520
add v5524 v5526
xor v5169 v5178
mul v5528 v5522
add v5527 v5529
sub v5523 v5530
sub v5531 v5530
sub v5530 v5531
add v5532 v5533
div v5534 v4264
shl v5535 1
sub 1 v5533
sub 1 v5537
add v5536 v5538
shr v5539 1
mul v4750 v5540
add v5518 v5541
xor v5190 v5144
land v5543 1
mul v5544 v5518
xor v4749 v5539
land v5546 1
xor v5547 1
mul v5548 v5541
add v5545 v5549
sub v5542 v5550
sub v5551 v5550
sub v5550 v5551
add v5552 v5553
div v5554 1
shl v5555 1
sub 1 v5553
sub 1 v5557
add v5556 v5558
shr v5559 1
mul v5560 v5540
add v5517 v5561
mul v5169 v5193
land v5514 1
xor v5190 v4749
land v5565 1
xor v5566 1
xor v5564 v5567
mul v5568 v5516
add v5563 v5569
land v5539 1
land v5559 1
xor v5572 1
xor v5571 v5573
mul v5574 v5561
add v5570 v5575
sub v5562 v5576
sub v5577 v5576
sub v5576 v5577
add v5578 v5579
div v5580 v4751
shl v5581 1
sub 1 v5579
sub 1 v5583
add v5582 v5584
shr v5585 1
mul v5586 v5586
mul v5587 v5515
mul v5586 v5191
mul v5192 v5470
mul v4751 v5425
mul v4264 v5380
mul v3731 v5335
mul v3169 v5290
mul v2651 v5245
mul v2653 0
add v5595 v5596
mul v2179 v5225
mul v2181 0
add v5598 v5599
mul v2624 v5245
add v5600 v5601
mul v5232 v5598
xor 0 v2631
mul v5604 v5599
add v5603 v5605
xor v5273 v2637
mul v5607 v5601
add v5606 v5608
sub v5602 v5609
sub v5610 v5609
sub v5609 v5610
add v5611 v5612
div v5613 v1753
shl v5614 1
sub 1 v5612
sub 1 v5616
add v5615 v5617
shr v5618 1
mul v3142 v5619
add v5597 v5620
mul v5273 v5595
xor 0 v3149
mul v5623 v5596
add v5622 v5624
land v5618 1
xor v5626 v3155
mul v5627 v5620
add v5625 v5628
sub v5621 v5629
sub v5630 v5629
sub v5629 v5630
add v5631 v5632
div v5633 v2179
shl v5634 1
sub 1 v5632
sub 1 v5636
add v5635 v5637
shr v5638 1
mul v3171 v5639
add v5594 v5640
mul v2651 v5269
mul v2653 v5619
add v5642 v5643
mul v3142 v5290
add v5644 v5645
mul v5277 v5642
xor v5626 v3149
mul v5648 v5643
add v5647 v5649
xor v5318 v3155
mul v5651 v5645
add v5650 v5652
sub v5646 v5653
sub v5654 v5653
sub v5653 v5654
add v5655 v5656
div v5657 v2179
shl v5658 1
sub 1 v5656
sub 1 v5660
add v5659 v5661
shr v5662 1
mul v3704 v5663
add v5641 v5664
mul v5318 v5594
land v5638 1
xor v5667 v3711
mul v5668 v5640
add v5666 v5669
land v5662 1
xor v5671 v3717
mul v5672 v5664
add v5670 v5673
sub v5665 v5674
sub v5675 v5674
sub v5674 v5675
add v5676 v5677
div v5678 v2651
shl v5679 1
sub 1 v5677
sub 1 v5681
add v5680 v5682
shr v5683 1
mul v3733 v5684
add v5593 v5685
mul v3169 v5314
mul v3171 v5663
add v5687 v5688
mul v3704 v5335
add v5689 v5690
mul v5322 v5687
xor v5671 v3711
mul v5693 v5688
add v5692 v5694
xor v5363 v3717
mul v5696 v5690
add v5695 v5697
sub v5691 v5698
sub v5699 v5698
sub v5698 v5699
add v5700 v5701
div v5702 v2651
shl v5703 1
sub 1 v5701
sub 1 v5705
add v5704 v5706
shr v5707 1
mul v4237 v5708
add v5686 v5709
mul v5363 v5593
land v5683 1
xor v5712 v4244
mul v5713 v5685
add v5711 v5714
land v5707 1
xor v5716 v4250
mul v5717 v5709
add v5715 v5718
sub v5710 v5719
sub v5720 v5719
sub v5719 v5720
add v5721 v5722
div v5723 v3169
shl v5724 1
sub 1 v5722
sub 1 v5726
add v5725 v5727
shr v5728 1
mul v4266 v5729
add v5592 v5730
mul v3731 v5359
mul v3733 v5708
add v5732 v5733
mul v4237 v5380
add v5734 v5735
mul v5367 v5732
xor v5716 v4244
mul v5738 v5733
add v5737 v5739
xor v5408 v4250
mul v5741 v5735
add v5740 v5742
sub v5736 v5743
sub v5744 v5743
sub v5743 v5744
add v5745 v5746
div v5747 v3169
shl v5748 1
sub 1 v5746
sub 1 v5750
add v5749 v5751
shr v5752 1
mul v4724 v5753
add v5731 v5754
mul v5408 v5592
land v5728 1
xor v5757 v4731
mul v5758 v5730
add v5756 v5759
land v5752 1
xor v5761 v4737
mul v5762 v5754
add v5760 v5763
sub v5755 v5764
sub v5765 v5764
sub v5764 v5765
add v5766 v5767
div v5768 v3731
shl v5769 1
sub 1 v5767
sub 1 v5771
add v5770 v5772
shr v5773 1
mul v4753 v5774
add v5591 v5775
mul v4264 v5404
mul v4266 v5753
add v5777 v5778
mul v4724 v5425
add v5779 v5780
mul v5412 v5777
xor v5761 v4731
mul v5783 v5778
add v5782 v5784
xor v5453 v4737
mul v5786 v5780
add v5785 v5787
sub v5781 v5788
sub v5789 v5788
sub v5788 v5789
add v5790 v5791
div v5792 v3731
shl v5793 1
sub 1 v5791
sub 1 v5795
add v5794 v5796
shr v5797 1
mul v5165 v5798
add v5776 v5799
mul v5453 v5591
land v5773 1
xor v5802 v5172
mul v5803 v5775
add v5801 v5804
land v5797 1
xor v5806 v5178
mul v5807 v5799
add v5805 v5808
sub v5800 v5809
sub v5810 v5809
sub v5809 v5810
add v5811 v5812
div v5813 v4264
shl v5814 1
sub 1 v5812
sub 1 v5816
add v5815 v5817
shr v5818 1
mul v5194 v5819
add v5590 v5820
mul v4751 v5449
mul v4753 v5798
add v5822 v5823
mul v5165 v5470
add v5824 v5825
mul v5457 v5822
xor v5806 v5172
mul v5828 v5823
add v5827 v5829
xor v5498 v5178
mul v5831 v5825
add v5830 v5832
sub v5826 v5833
sub v5834 v5833
sub v5833 v5834
add v5835 v5836
div v5837 v4264
shl v5838 1
sub 1 v5836
sub 1 v5840
add v5839 v5841
shr v5842 1
mul v5560 v5843
add v5821 v5844
mul v5498 v5590
land v5818 1
xor v5847 v5567
mul v5848 v5820
add v5846 v5849
land v5842 1
xor v5851 v5573
mul v5852 v5844
add v5850 v5853
sub v5845 v5854
sub v5855 v5854
sub v5854 v5855
add v5856 v5857
div v5858 v4751
shl v5859 1
sub 1 v5857
sub 1 v5861
add v5860 v5862
shr v5863 1
mul v5589 v5864
add v5588 v5865
mul v5586 v5540
mul v5192 v5494
mul v5194 v5843
add v5868 v5869
mul v5560 v5515
add v5870 v5871
mul v5502 v5868
xor v5851 v5567
mul v5874 v5869
add v5873 v5875
xor v5564 v5573
mul v5877 v5871
add v5876 v5878
sub v5872 v5879
sub v5880 v5879
sub v5879 v5880
add v5881 v5882
div v5883 v4751
shl v5884 1
sub 1 v5882
sub 1 v5886
add v5885 v5887
shr v5888 1
mul v5191 v5889
add v5867 v5890
xor v5585 v5539
land v5892 1
mul v5893 v5867
xor v5190 v5888
land v5895 1
xor v5896 1
mul v5897 v5890
add v5894 v5898
sub v5891 v5899
sub v5900 v5899
sub v5899 v5900
add v5901 v5902
div v5903 1
shl v5904 1
sub 1 v5902
sub 1 v5906
add v5905 v5907
shr v5908 1
mul v5909 v5889
add v5866 v5910
mul v5564 v5588
land v5863 1
xor v5585 v5190
land v5914 1
xor v5915 1
xor v5913 v5916
mul v5917 v5865
add v5912 v5918
land v5888 1
land v5908 1
xor v5921 1
xor v5920 v5922
mul v5923 v5910
add v5919 v5924
sub v5911 v5925
sub v5926 v5925
sub v5925 v5926
add v5927 v5928
div v5929 v5192
shl v5930 1
sub 1 v5928
sub 1 v5932
add v5931 v5933
shr v5934 1
mul v5935 v5935
mul v5936 v5864
mul v5935 v5586
mul v5587 v5819
mul v5192 v5774
mul v4751 v5729
mul v4264 v5684
mul v3731 v5639
mul v3733 0
add v5943 v5944
mul v3169 v5619
mul v3171 0
add v5946 v5947
mul v3704 v5639
add v5948 v5949
mul v5626 v5946
xor 0 v3711
mul v5952 v5947
add v5951 v5953
xor v5667 v3717
mul v5955 v5949
add v5954 v5956
sub v5950 v5957
sub v5958 v5957
sub v5957 v5958
add v5959 v5960
div v5961 v2651
shl v5962 1
sub 1 v5960
sub 1 v5964
add v5963 v5965
shr v5966 1
mul v4237 v5967
add v5945 v5968
mul v5667 v5943
xor 0 v4244
mul v5971 v5944
add v5970 v5972
land v5966 1
xor v5974 v4250
mul v5975 v5968
add v5973 v5976
sub v5969 v5977
sub v5978 v5977
sub v5977 v5978
add v5979 v5980
div v5981 v3169
shl v5982 1
sub 1 v5980
sub 1 v5984
add v5983 v5985
shr v5986 1
mul v4266 v5987
add v5942 v5988
mul v3731 v5663
mul v3733 v5967
add v5990 v5991
mul v4237 v5684
add v5992 v5993
mul v5671 v5990
xor v5974 v4244
mul v5996 v5991
add v5995 v5997
xor v5712 v4250
mul v5999 v5993
add v5998 v6000
sub v5994 v6001
sub v6002 v6001
sub v6001 v6002
add v6003 v6004
div v6005 v3169
shl v6006 1
sub 1 v6004
sub 1 v6008
add v6007 v6009
shr v6010 1
mul v4724 v6011
add v5989 v6012
mul v5712 v5942
land v5986 1
xor v6015 v4731
mul v6016 v5988
add v6014 v6017
land v6010 1
xor v6019 v4737
mul v6020 v6012
add v6018 v6021
sub v6013 v6022
sub v6023 v6022
sub v6022 v6023
add v6024 v6025
div v6026 v3731
shl v6027 1
sub 1 v6025
sub 1 v6029
add v6028 v6030
shr v6031 1
mul v4753 v6032
add v5941 v6033
mul v4264 v5708
mul v4266 v6011
add v6035 v6036
mul v4724 v5729
add v6037 v6038
mul v5716 v6035
xor v6019 v4731
mul v6041 v6036
add v6040 v6042
xor v5757 v4737
mul v6044 v6038
add v6043 v6045
sub v6039 v6046
sub v6047 v6046
sub v6046 v6047
add v6048 v6049
div v6050 v3731
shl v6051 1
sub 1 v6049
sub 1 v6053
add v6052 v6054
shr v6055 1
mul v5165 v6056
add v6034 v6057
mul v5757 v5941
land v6031 1
xor v6060 v5172
mul v6061 v6033
add v6059 v6062
land v6055 1
xor v6064 v5178
mul v6065 v6057
add v6063 v6066
sub v6058 v6067
sub v6068 v6067
sub v6067 v6068
add v6069 v6070
div v6071 v4264
shl v6072 1
sub 1 v6070
sub 1 v6074
add v6073 v6075
shr v6076 1
mul v5194 v6077
add v5940 v6078
mul v4751 v5753
mul v4753 v6056
add v6080 v6081
mul v5165 v5774
add v6082 v6083
mul v5761 v6080
xor v6064 v5172
mul v6086 v6081
add v6085 v6087
xor v5802 v5178
mul v6089 v6083
add v6088 v6090
sub v6084 v6091
sub v6092 v6091
sub v6091 v6092
add v6093 v6094
div v6095 v4264
shl v6096 1
sub 1 v6094
sub 1 v6098
add v6097 v6099
shr v6100 1
mul v5560 v6101
add v6079 v6102
mul v5802 v5940
land v6076 1
xor v6105 v5567
mul v6106 v6078
add v6104 v6107
land v6100 1
xor v6109 v5573
mul v6110 v6102
add v6108 v6111
sub v6103 v6112
sub v6113 v6112
sub v6112 v6113
add v6114 v6115
div v6116 v4751
shl v6117 1
sub 1 v6115
sub 1 v6119
add v6118 v6120
shr v6121 1
mul v5589 v6122
add v5939 v6123
mul v5192 v5798
mul v5194 v6101
add v6125 v6126
mul v5560 v5819
add v6127 v6128
mul v5806 v6125
xor v6109 v5567
mul v6131 v6126
add v6130 v6132
xor v5847 v5573
mul v6134 v6128
add v6133 v6135
sub v6129 v6136
sub v6137 v6136
sub v6136 v6137
add v6138 v6139
div v6140 v4751
shl v6141 1
sub 1 v6139
sub 1 v6143
add v6142 v6144
shr v6145 1
mul v5909 v6146
add v6124 v6147
mul v5847 v5939
land v6121 1
xor v6150 v5916
mul v6151 v6123
add v6149 v6152
land v6145 1
xor v6154 v5922
mul v6155 v6147
add v6153 v6156
sub v6148 v6157
sub v6158 v6157
sub v6157 v6158
add v6159 v6160
div v6161 v5192
shl v6162 1
sub 1 v6160
sub 1 v6164
add v6163 v6165
shr v6166 1
mul v5938 v6167
add v5937 v6168
mul v5935 v5889
mul v5587 v5843
mul v5589 v6146
add v6171 v6172
mul v5909 v5864
add v6173 v6174
mul v5851 v6171
xor v6154 v5916
mul v6177 v6172
add v6176 v6178
xor v5913 v5922
mul v6180 v6174
add v6179 v6181
sub v6175 v6182
sub v6183 v6182
sub v6182 v6183
add v6184 v6185
div v6186 v5192
shl v6187 1
sub 1 v6185
sub 1 v6189
add v6188 v6190
shr v6191 1
mul v5586 v6192
add v6170 v6193
xor v5934 v5888
land v6195 1
mul v6196 v6170
xor v5585 v6191
land v6198 1
xor v6199 1
mul v6200 v6193
add v6197 v6201
sub v6194 v6202
sub v6203 v6202
sub v6202 v6203
add v6204 v6205
div v6206 1
shl v6207 1
sub 1 v6205
sub 1 v6209
add v6208 v6210
shr v6211 1
mul v6212 v6192
add v6169 v6213
mul v5913 v5937
land v6166 1
xor v5934 v5585
land v6217 1
xor v6218 1
xor v6216 v6219
mul v6220 v6168
add v6215 v6221
land v6191 1
land v6211 1
xor v6224 1
xor v6223 v6225
mul v6226 v6213
add v6222 v6227
sub v6214 v6228
sub v6229 v6228
sub v6228 v6229
add v6230 v6231
div v6232 v5587
shl v6233 1
sub 1 v6231
sub 1 v6235
add v6234 v6236
shr v6237 1
mul v6238 v6238
mul v6239 v6167
mul v6238 v5935
mul v5936 v6122
mul v5587 v6077
mul v5192 v6032
mul v4751 v5987
mul v4753 0
add v6245 v6246
mul v4264 v5967
mul v4266 0
add v6248 v6249
mul v4724 v5987
add v6250 v6251
mul v5974 v6248
xor 0 v4731
mul v6254 v6249
add v6253 v6255
xor v6015 v4737
mul v6257 v6251
add v6256 v6258
sub v6252 v6259
sub v6260 v6259
sub v6259 v6260
add v6261 v6262
div v6263 v3731
shl v6264 1
sub 1 v6262
sub 1 v6266
add v6265 v6267
shr v6268 1
mul v5165 v6269
add v6247 v6270
mul v6015 v6245
xor 0 v5172
mul v6273 v6246
add v6272 v6274
land v6268 1
xor v6276 v5178
mul v6277 v6270
add v6275 v6278
sub v6271 v6279
sub v6280 v6279
sub v6279 v6280
add v6281 v6282
div v6283 v4264
shl v6284 1
sub 1 v6282
sub 1 v6286
add v6285 v6287
shr v6288 1
mul v5194 v6289
add v6244 v6290
mul v4751 v6011
mul v4753 v6269
add v6292 v6293
mul v5165 v6032
add v6294 v6295
mul v6019 v6292
xor v6276 v5172
mul v6298 v6293
add v6297 v6299
xor v6060 v5178
mul v6301 v6295
add v6300 v6302
sub v6296 v6303
sub v6304 v6303
sub v6303 v6304
add v6305 v6306
div v6307 v4264
shl v6308 1
sub 1 v6306
sub 1 v6310
add v6309 v6311
shr v6312 1
mul v5560 v6313
add v6291 v6314
mul v6060 v6244
land v6288 1
xor v6317 v5567
mul v6318 v6290
add v6316 v6319
land v6312 1
xor v6321 v5573
mul v6322 v6314
add v6320 v6323
sub v6315 v6324
sub v6325 v6324
sub v6324 v6325
add v6326 v6327
div v6328 v4751
shl v6329 1
sub 1 v6327
sub 1 v6331
add v6330 v6332
shr v6333 1
mul v5589 v6334
add v6243 v6335
mul v5192 v6056
mul v5194 v6313
add v6337 v6338
mul v5560 v6077
add v6339 v6340
mul v6064 v6337
xor v6321 v5567
mul v6343 v6338
add v6342 v6344
xor v6105 v5573
mul v6346 v6340
add v6345 v6347
sub v6341 v6348
sub v6349 v6348
sub v6348 v6349
add v6350 v6351
div v6352 v4751
shl v6353 1
sub 1 v6351
sub 1 v6355
add v6354 v6356
shr v6357 1
mul v5909 v6358
add v6336 v6359
mul v6105 v6243
land v6333 1
xor v6362 v5916
mul v6363 v6335
add v6361 v6364
land v6357 1
xor v6366 v5922
mul v6367 v6359
add v6365 v6368
sub v6360 v6369
sub v6370 v6369
sub v6369 v6370
add v6371 v6372
div v6373 v5192
shl v6374 1
sub 1 v6372
sub 1 v6376
add v6375 v6377
shr v6378 1
mul v5938 v6379
add v6242 v6380
mul v5587 v6101
mul v5589 v6358
add v6382 v6383
mul v5909 v6122
add v6384 v6385
mul v6109 v6382
xor v6366 v5916
mul v6388 v6383
add v6387 v6389
xor v6150 v5922
mul v6391 v6385
add v6390 v6392
sub v6386 v6393
sub v6394 v6393
sub v6393 v6394
add v6395 v6396
div v6397 v5192
shl v6398 1
sub 1 v6396
sub 1 v6400
add v6399 v6401
shr v6402 1
mul v6212 v6403
add v6381 v6404
mul v6150 v6242
land v6378 1
xor v6407 v6219
mul v6408 v6380
add v6406 v6409
land v6402 1
xor v6411 v6225
mul v6412 v6404
add v6410 v6413
sub v6405 v6414
sub v6415 v6414
sub v6414 v6415
add v6416 v6417
div v6418 v5587
shl v6419 1
sub 1 v6417
sub 1 v6421
add v6420 v6422
shr v6423 1
mul v6241 v6424
add v6240 v6425
mul v6238 v6192
mul v5936 v6146
mul v5938 v6403
add v6428 v6429
mul v6212 v6167
add v6430 v6431
mul v6154 v6428
xor v6411 v6219
mul v6434 v6429
add v6433 v6435
xor v6216 v6225
mul v6437 v6431
add v6436 v6438
sub v6432 v6439
sub v6440 v6439
sub v6439 v6440
add v6441 v6442
div v6443 v5587
shl v6444 1
sub 1 v6442
sub 1 v6446
add v6445 v6447
shr v6448 1
mul v5935 v6449
add v6427 v6450
xor v6237 v6191
land v6452 1
mul v6453 v6427
xor v5934 v6448
land v6455 1
xor v6456 1
mul v6457 v6450
add v6454 v6458
sub v6451 v6459
sub v6460 v6459
sub v6459 v6460
add v6461 v6462
div v6463 1
shl v6464 1
sub 1 v6462
sub 1 v6466
add v6465 v6467
shr v6468 1
mul v6469 v6449
add v6426 v6470
mul v6216 v6240
land v6423 1
xor v6237 v5934
land v6474 1
xor v6475 1
xor v6473 v6476
mul v6477 v6425
add v6472 v6478
land v6448 1
land v6468 1
xor v6481 1
xor v6480 v6482
mul v6483 v6470
add v6479 v6484
sub v6471 v6485
sub v6486 v6485
sub v6485 v6486
add v6487 v6488
div v6489 v5936
shl v6490 1
sub 1 v6488
sub 1 v6492
add v6491 v6493
shr v6494 1
mul v6495 v6495
mul v6496 v6424
mul v6495 v6238
mul v6239 v6379
mul v5936 v6334
mul v5587 v6289
mul v5589 0
add v6501 v6502
mul v5192 v6269
mul v5194 0
add v6504 v6505
mul v5560 v6289
add v6506 v6507
mul v6276 v6504
xor 0 v5567
mul v6510 v6505
add v6509 v6511
xor v6317 v5573
mul v6513 v6507
add v6512 v6514
sub v6508 v6515
sub v6516 v6515
sub v6515 v6516
add v6517 v6518
div v6519 v4751
shl v6520 1
sub 1 v6518
sub 1 v6522
add v6521 v6523
shr v6524 1
mul v5909 v6525
add v6503 v6526
mul v6317 v6501
xor 0 v5916
mul v6529 v6502
add v6528 v6530
land v6524 1
xor v6532 v5922
mul v6533 v6526
add v6531 v6534
sub v6527 v6535
sub v6536 v6535
sub v6535 v6536
add v6537 v6538
div v6539 v5192
shl v6540 1
sub 1 v6538
sub 1 v6542
add v6541 v6543
shr v6544 1
mul v5938 v6545
add v6500 v6546
mul v5587 v6313
mul v5589 v6525
add v6548 v6549
mul v5909 v6334
add v6550 v6551
mul v6321 v6548
xor v6532 v5916
mul v6554 v6549
add v6553 v6555
xor v6362 v5922
mul v6557 v6551
add v6556 v6558
sub v6552 v6559
sub v6560 v6559
sub v6559 v6560
add v6561 v6562
div v6563 v5192
shl v6564 1
sub 1 v6562
sub 1 v6566
add v6565 v6567
shr v6568 1
mul v6212 v6569
add v6547 v6570
mul v6362 v6500
land v6544 1
xor v6573 v6219
mul v6574 v6546
add v6572 v6575
land v6568 1
xor v6577 v6225
mul v6578 v6570
add v6576 v6579
sub v6571 v6580
sub v6581 v6580
sub v6580 v6581
add v6582 v6583
div v6584 v5587
shl v6585 1
sub 1 v6583
sub 1 v6587
add v6586 v6588
shr v6589 1
mul v6241 v6590
add v6499 v6591
mul v5936 v6358
mul v5938 v6569
add v6593 v6594
mul v6212 v6379
add v6595 v6596
mul v6366 v6593
xor v6577 v6219
mul v6599 v6594
add v6598 v6600
xor v6407 v6225
mul v6602 v6596
add v6601 v6603
sub v6597 v6604
sub v6605 v6604
sub v6604 v6605
add v6606 v6607
div v6608 v5587
shl v6609 1
sub 1 v6607
sub 1 v6611
add v6610 v6612
shr v6613 1
mul v6469 v6614
add v6592 v6615
mul v6407 v6499
land v6589 1
xor v6618 v6476
mul v6619 v6591
add v6617 v6620
land v6613 1
xor v6622 v6482
mul v6623 v6615
add v6621 v6624
sub v6616 v6625
sub v6626 v6625
sub v6625 v6626
add v6627 v6628
div v6629 v5936
shl v6630 1
sub 1 v6628
sub 1 v6632
add v6631 v6633
shr v6634 1
mul v6498 v6635
add v6497 v6636
mul v6495 v6449
mul v6239 v6403
mul v6241 v6614
add v6639 v6640
mul v6469 v6424
add v6641 v6642
mul v6411 v6639
xor v6622 v6476
mul v6645 v6640
add v6644 v6646
xor v6473 v6482
mul v6648 v6642
add v6647 v6649
sub v6643 v6650
sub v6651 v6650
sub v6650 v6651
add v6652 v6653
div v6654 v5936
shl v6655 1
sub 1 v6653
sub 1 v6657
add v6656 v6658
shr v6659 1
mul v6238 v6660
add v6638 v6661
xor v6494 v6448
land v6663 1
mul v6664 v6638
xor v6237 v6659
land v6666 1
xor v6667 1
mul v6668 v6661
add v6665 v6669
sub v6662 v6670
sub v6671 v6670
sub v6670 v6671
add v6672 v6673
div v6674 1
shl v6675 1
sub 1 v6673
sub 1 v6677
add v6676 v6678
shr v6679 1
mul v6680 v6660
add v6637 v6681
mul v6473 v6497
land v6634 1
xor v6494 v6237
land v6685 1
xor v6686 1
xor v6684 v6687
mul v6688 v6636
add v6683 v6689
land v6659 1
land v6679 1
xor v6692 1
xor v6691 v6693
mul v6694 v6681
add v6690 v6695
sub v6682 v6696
sub v6697 v6696
sub v6696 v6697
add v6698 v6699
div v6700 v6239
shl v6701 1
sub 1 v6699
sub 1 v6703
add v6702 v6704
shr v6705 1
mul v6706 v6706
mul v6707 v6635
mul v6706 v6495
mul v6496 v6590
mul v6239 v6545
mul v6241 0
add v6711 v6712
mul v5936 v6525
mul v5938 0
add v6714 v6715
mul v6212 v6545
add v6716 v6717
mul v6532 v6714
xor 0 v6219
mul v6720 v6715
add v6719 v6721
xor v6573 v6225
mul v6723 v6717
add v6722 v6724
sub v6718 v6725
sub v6726 v6725
sub v6725 v6726
add v6727 v6728
div v6729 v5587
shl v6730 1
sub 1 v6728
sub 1 v6732
add v6731 v6733
shr v6734 1
mul v6469 v6735
add v6713 v6736
mul v6573 v6711
xor 0 v6476
mul v6739 v6712
add v6738 v6740
land v6734 1
xor v6742 v6482
mul v6743 v6736
add v6741 v6744
sub v6737 v6745
sub v6746 v6745
sub v6745 v6746
add v6747 v6748
div v6749 v5936
shl v6750 1
sub 1 v6748
sub 1 v6752
add v6751 v6753
shr v6754 1
mul v6498 v6755
add v6710 v6756
mul v6239 v6569
mul v6241 v6735
add v6758 v6759
mul v6469 v6590
add v6760 v6761
mul v6577 v6758
xor v6742 v6476
mul v6764 v6759
add v6763 v6765
xor v6618 v6482
mul v6767 v6761
add v6766 v6768
sub v6762 v6769
sub v6770 v6769
sub v6769 v6770
add v6771 v6772
div v6773 v5936
shl v6774 1
sub 1 v6772
sub 1 v6776
add v6775 v6777
shr v6778 1
mul v6680 v6779
add v6757 v6780
mul v6618 v6710
land v6754 1
xor v6783 v6687
mul v6784 v6756
add v6782 v6785
land v6778 1
xor v6787 v6693
mul v6788 v6780
add v6786 v6789
sub v6781 v6790
sub v6791 v6790
sub v6790 v6791
add v6792 v6793
div v6794 v6239
shl v6795 1
sub 1 v6793
sub 1 v6797
add v6796 v6798
shr v6799 1
mul v6709 v6800
add v6708 v6801
mul v6706 v6660
mul v6496 v6614
mul v6498 v6779
add v6804 v6805
mul v6680 v6635
add v6806 v6807
mul v6622 v6804
xor v6787 v6687
mul v6810 v6805
add v6809 v6811
xor v6684 v6693
mul v6813 v6807
add v6812 v6814
sub v6808 v6815
sub v6816 v6815
sub v6815 v6816
add v6817 v6818
div v6819 v6239
shl v6820 1
sub 1 v6818
sub 1 v6822
add v6821 v6823
shr v6824 1
mul v6495 v6825
add v6803 v6826
xor v6705 v6659
land v6828 1
mul v6829 v6803
xor v6494 v6824
land v6831 1
xor v6832 1
mul v6833 v6826
add v6830 v6834
sub v6827 v6835
sub v6836 v6835
sub v6835 v6836
add v6837 v6838
div v6839 1
shl v6840 1
sub 1 v6838
sub 1 v6842
add v6841 v6843
shr v6844 1
mul v6845 v6825
add v6802 v6846
mul v6684 v6708
land v6799 1
xor v6705 v6494
land v6850 1
xor v6851 1
xor v6849 v6852
mul v6853 v6801
add v6848 v6854
land v6824 1
land v6844 1
xor v6857 1
xor v6856 v6858
mul v6859 v6846
add v6855 v6860
sub v6847 v6861
sub v6862 v6861
sub v6861 v6862
add v6863 v6864
div v6865 v6496
shl v6866 1
sub 1 v6864
sub 1 v6868
add v6867 v6869
shr v6870 1
mul v6871 v6871
mul v6872 v6800
mul v6871 v6706
mul v6707 v6755
mul v6709 0
add v6875 v6876
mul v6496 v6735
mul v6498 0
add v6878 v6879
mul v6680 v6755
add v6880 v6881
mul v6742 v6878
xor 0 v6687
mul v6884 v6879
add v6883 v6885
xor v6783 v6693
mul v6887 v6881
add v6886 v6888
sub v6882 v6889
sub v6890 v6889
sub v6889 v6890
add v6891 v6892
div v6893 v6239
shl v6894 1
sub 1 v6892
sub 1 v6896
add v6895 v6897
shr v6898 1
mul v6845 v6899
add v6877 v6900
mul v6783 v6875
xor 0 v6852
mul v6903 v6876
add v6902 v6904
land v6898 1
xor v6906 v6858
mul v6907 v6900
add v6905 v6908
sub v6901 v6909
sub v6910 v6909
sub v6909 v6910
add v6911 v6912
div v6913 v6496
shl v6914 1
sub 1 v6912
sub 1 v6916
add v6915 v6917
shr v6918 1
mul v6874 v6919
add v6873 v6920
mul v6871 v6825
mul v6707 v6779
mul v6709 v6899
add v6923 v6924
mul v6845 v6800
add v6925 v6926
mul v6787 v6923
xor v6906 v6852
mul v6929 v6924
add v6928 v6930
xor v6849 v6858
mul v6932 v6926
add v6931 v6933
sub v6927 v6934
sub v6935 v6934
sub v6934 v6935
add v6936 v6937
div v6938 v6496
shl v6939 1
sub 1 v6937
sub 1 v6941
add v6940 v6942
shr v6943 1
mul v6706 v6944
add v6922 v6945
xor v6870 v6824
land v6947 1
mul v6948 v6922
xor v6705 v6943
land v6950 1
xor v6951 1
mul v6952 v6945
add v6949 v6953
sub v6946 v6954
sub v6955 v6954
sub v6954 v6955
add v6956 v6957
div v6958 1
shl v6959 1
sub 1 v6957
sub 1 v6961
add v6960 v6962
shr v6963 1
mul v6964 v6944
add v6921 v6965
mul v6849 v6873
land v6918 1
xor v6870 v6705
land v6969 1
xor v6970 1
xor v6968 v6971
mul v6972 v6920
add v6967 v6973
land v6943 1
land v6963 1
xor v6976 1
xor v6975 v6977
mul v6978 v6965
add v6974 v6979
sub v6966 v6980
sub v6981 v6980
sub v6980 v6981
add v6982 v6983
div v6984 v6707
shl v6985 1
sub 1 v6983
sub 1 v6987
add v6986 v6988
shr v6989 1
mul v6990 v6990
mul v6991 v6919
mul v6990 v6871
mul v6993 0
add v6992 v6994
mul v6990 v6944
mul v6872 v6899
mul v6874 0
add v6997 v6998
mul v6964 v6919
add v6999 v7000
mul v6906 v6997
xor 0 v6971
mul v7003 v6998
add v7002 v7004
xor v6968 v6977
mul v7006 v7000
add v7005 v7007
sub v7001 v7008
sub v7009 v7008
sub v7008 v7009
add v7010 v7011
div v7012 v6707
shl v7013 1
sub 1 v7011
sub 1 v7015
add v7014 v7016
shr v7017 1
mul v6871 v7018
add v6996 v7019
xor v6989 v6943
land v7021 1
mul v7022 v6996
xor v6870 v7017
land v7024 1
xor v7025 1
mul v7026 v7019
add v7023 v7027
sub v7020 v7028
sub v7029 v7028
sub v7028 v7029
add v7030 v7031
div v7032 1
shl v7033 1
sub 1 v7031
sub 1 v7035
add v7034 v7036
shr v7037 1
mul v7038 v7018
add v6995 v7039
mul v6968 v6992
xor v6989 v6870
land v7042 1
xor v7043 1
xor 0 v7044
mul v7045 v6994
add v7041 v7046
land v7017 1
land v7037 1
xor v7049 1
xor v7048 v7050
mul v7051 v7039
add v7047 v7052
sub v7040 v7053
sub v7054 v7053
sub v7053 v7054
add v7055 v7056
div v7057 v6872
shl v7058 1
sub 1 v7056
sub 1 v7060
add v7059 v7061
sub 1 v31
add v3201 0
add v3227 v7064
add v2684 v7065
add v2710 v7066
add v2211 v7067
add v2237 v7068
add v1784 v7069
add v1810 v7070
add v1403 v7071
add v1429 v7072
add v1068 v7073
add v1094 v7074
add v779 v7075
add v805 v7076
add v536 v7077
add v562 v7078
add v339 v7079
add v365 v7080
add v188 v7081
add v214 v7082
add v83 v7083
add v110 v7084
add v52 v7085
add v3202 0
add v3228 v7087
add v2685 v7088
add v2711 v7089
add v2212 v7090
add v2238 v7091
add v1785 v7092
add v1811 v7093
add v1404 v7094
add v1430 v7095
add v1069 v7096
add v1095 v7097
add v780 v7098
add v806 v7099
add v537 v7100
add v563 v7101
add v340 v7102
add v366 v7103
add v189 v7104
add v215 v7105
add v84 v7106
add v111 v7107
add v53 v7108
mul 1 v7109
sub v7086 v7110
add v7063 v7111
sub 1 v58
add v7112 v7113
sub 1 v136
add v3761 0
add v3248 v7116
add v3272 v7117
add v2731 v7118
add v2755 v7119
add v2258 v7120
add v2282 v7121
add v1831 v7122
add v1855 v7123
add v1450 v7124
add v1474 v7125
add v1115 v7126
add v1139 v7127
add v826 v7128
add v850 v7129
add v583 v7130
add v607 v7131
add v386 v7132
add v410 v7133
add v235 v7134
add v260 v7135
add v156 v7136
add v3762 0
add v3249 v7138
add v3273 v7139
add v2732 v7140
add v2756 v7141
add v2259 v7142
add v2283 v7143
add v1832 v7144
add v1856 v7145
add v1451 v7146
add v1475 v7147
add v1116 v7148
add v1140 v7149
add v827 v7150
add v851 v7151
add v584 v7152
add v608 v7153
add v387 v7154
add v411 v7155
add v236 v7156
add v261 v7157
add v157 v7158
mul v1 v7159
sub v7137 v7160
add v7115 v7161
sub 1 v162
add v7162 v7163
add v7114 v7164
sub 1 v286
add v3781 0
add v3805 v7167
add v3293 v7168
add v3317 v7169
add v2776 v7170
add v2800 v7171
add v2303 v7172
add v2327 v7173
add v1876 v7174
add v1900 v7175
add v1495 v7176
add v1519 v7177
add v1160 v7178
add v1184 v7179
add v871 v7180
add v895 v7181
add v628 v7182
add v652 v7183
add v431 v7184
add v456 v7185
add v306 v7186
add v3782 0
add v3806 v7188
add v3294 v7189
add v3318 v7190
add v2777 v7191
add v2801 v7192
add v2304 v7193
add v2328 v7194
add v1877 v7195
add v1901 v7196
add v1496 v7197
add v1520 v7198
add v1161 v7199
add v1185 v7200
add v872 v7201
add v896 v7202
add v629 v7203
add v653 v7204
add v432 v7205
add v457 v7206
add v307 v7207
mul v59 v7208
sub v7187 v7209
add v7166 v7210
sub 1 v312
add v7211 v7212
add v7165 v7213
sub 1 v482
add v4293 0
add v3826 v7216
add v3850 v7217
add v3338 v7218
add v3362 v7219
add v2821 v7220
add v2845 v7221
add v2348 v7222
add v2372 v7223
add v1921 v7224
add v1945 v7225
add v1540 v7226
add v1564 v7227
add v1205 v7228
add v1229 v7229
add v916 v7230
add v940 v7231
add v673 v7232
add v698 v7233
add v502 v7234
add v4294 0
add v3827 v7236
add v3851 v7237
add v3339 v7238
add v3363 v7239
add v2822 v7240
add v2846 v7241
add v2349 v7242
add v2373 v7243
add v1922 v7244
add v1946 v7245
add v1541 v7246
add v1565 v7247
add v1206 v7248
add v1230 v7249
add v917 v7250
add v941 v7251
add v674 v7252
add v699 v7253
add v503 v7254
mul v163 v7255
sub v7235 v7256
add v7215 v7257
sub 1 v508
add v7258 v7259
add v7214 v7260
sub 1 v724
add v4313 0
add v4337 v7263
add v3871 v7264
add v3895 v7265
add v3383 v7266
add v3407 v7267
add v2866 v7268
add v2890 v7269
add v2393 v7270
add v2417 v7271
add v1966 v7272
add v1990 v7273
add v1585 v7274
add v1609 v7275
add v1250 v7276
add v1274 v7277
add v961 v7278
add v986 v7279
add v744 v7280
add v4314 0
add v4338 v7282
add v3872 v7283
add v3896 v7284
add v3384 v7285
add v3408 v7286
add v2867 v7287
add v2891 v7288
add v2394 v7289
add v2418 v7290
add v1967 v7291
add v1991 v7292
add v1586 v7293
add v1610 v7294
add v1251 v7295
add v1275 v7296
add v962 v7297
add v987 v7298
add v745 v7299
mul v313 v7300
sub v7281 v7301
add v7262 v7302
sub 1 v750
add v7303 v7304
add v7261 v7305
sub 1 v1012
add v4779 0
add v4358 v7308
add v4382 v7309
add v3916 v7310
add v3940 v7311
add v3428 v7312
add v3452 v7313
add v2911 v7314
add v2935 v7315
add v2438 v7316
add v2462 v7317
add v2011 v7318
add v2035 v7319
add v1630 v7320
add v1654 v7321
add v1295 v7322
add v1320 v7323
add v1032 v7324
add v4780 0
add v4359 v7326
add v4383 v7327
add v3917 v7328
add v3941 v7329
add v3429 v7330
add v3453 v7331
add v2912 v7332
add v2936 v7333
add v2439 v7334
add v2463 v7335
add v2012 v7336
add v2036 v7337
add v1631 v7338
add v1655 v7339
add v1296 v7340
add v1321 v7341
add v1033 v7342
mul v509 v7343
sub v7325 v7344
add v7307 v7345
sub 1 v1038
add v7346 v7347
add v7306 v7348
sub 1 v1346
add v4799 0
add v4823 v7351
add v4403 v7352
add v4427 v7353
add v3961 v7354
add v3985 v7355
add v3473 v7356
add v3497 v7357
add v2956 v7358
add v2980 v7359
add v2483 v7360
add v2507 v7361
add v2056 v7362
add v2080 v7363
add v1675 v7364
add v1700 v7365
add v1366 v7366
add v4800 0
add v4824 v7368
add v4404 v7369
add v4428 v7370
add v3962 v7371
add v3986 v7372
add v3474 v7373
add v3498 v7374
add v2957 v7375
add v2981 v7376
add v2484 v7377
add v2508 v7378
add v2057 v7379
add v2081 v7380
add v1676 v7381
add v1701 v7382
add v1367 v7383
mul v751 v7384
sub v7367 v7385
add v7350 v7386
sub 1 v1372
add v7387 v7388
add v7349 v7389
sub 1 v1726
add v5219 0
add v4844 v7392
add v4868 v7393
add v4448 v7394
add v4472 v7395
add v4006 v7396
add v4030 v7397
add v3518 v7398
add v3542 v7399
add v3001 v7400
add v3025 v7401
add v2528 v7402
add v2552 v7403
add v2101 v7404
add v2126 v7405
add v1746 v7406
add v5220 0
add v4845 v7408
add v4869 v7409
add v4449 v7410
add v4473 v7411
add v4007 v7412
add v4031 v7413
add v3519 v7414
add v3543 v7415
add v3002 v7416
add v3026 v7417
add v2529 v7418
add v2553 v7419
add v2102 v7420
add v2127 v7421
add v1747 v7422
mul v1039 v7423
sub v7407 v7424
add v7391 v7425
sub 1 v1752
add v7426 v7427
add v7390 v7428
sub 1 v2152
add v5239 0
add v5263 v7431
add v4889 v7432
add v4913 v7433
add v4493 v7434
add v4517 v7435
add v4051 v7436
add v4075 v7437
add v3563 v7438
add v3587 v7439
add v3046 v7440
add v3070 v7441
add v2573 v7442
add v2598 v7443
add v2172 v7444
add v5240 0
add v5264 v7446
add v4890 v7447
add v4914 v7448
add v4494 v7449
add v4518 v7450
add v4052 v7451
add v4076 v7452
add v3564 v7453
add v3588 v7454
add v3047 v7455
add v3071 v7456
add v2574 v7457
add v2599 v7458
add v2173 v7459
mul v1373 v7460
sub v7445 v7461
add v7430 v7462
sub 1 v2178
add v7463 v7464
add v7429 v7465
sub 1 v2624
add v5613 0
add v5284 v7468
add v5308 v7469
add v4934 v7470
add v4958 v7471
add v4538 v7472
add v4562 v7473
add v4096 v7474
add v4120 v7475
add v3608 v7476
add v3632 v7477
add v3091 v7478
add v3116 v7479
add v2644 v7480
add v5614 0
add v5285 v7482
add v5309 v7483
add v4935 v7484
add v4959 v7485
add v4539 v7486
add v4563 v7487
add v4097 v7488
add v4121 v7489
add v3609 v7490
add v3633 v7491
add v3092 v7492
add v3117 v7493
add v2645 v7494
mul v1753 v7495
sub v7481 v7496
add v7467 v7497
sub 1 v2650
add v7498 v7499
add v7466 v7500
sub 1 v3142
add v5633 0
add v5657 v7503
add v5329 v7504
add v5353 v7505
add v4979 v7506
add v5003 v7507
add v4583 v7508
add v4607 v7509
add v4141 v7510
add v4165 v7511
add v3653 v7512
add v3678 v7513
add v3162 v7514
add v5634 0
add v5658 v7516
add v5330 v7517
add v5354 v7518
add v4980 v7519
add v5004 v7520
add v4584 v7521
add v4608 v7522
add v4142 v7523
add v4166 v7524
add v3654 v7525
add v3679 v7526
add v3163 v7527
mul v2179 v7528
sub v7515 v7529
add v7502 v7530
sub 1 v3168
add v7531 v7532
add v7501 v7533
sub 1 v3704
add v5961 0
add v5678 v7536
add v5702 v7537
add v5374 v7538
add v5398 v7539
add v5024 v7540
add v5048 v7541
add v4628 v7542
add v4652 v7543
add v4186 v7544
add v4211 v7545
add v3724 v7546
add v5962 0
add v5679 v7548
add v5703 v7549
add v5375 v7550
add v5399 v7551
add v5025 v7552
add v5049 v7553
add v4629 v7554
add v4653 v7555
add v4187 v7556
add v4212 v7557
add v3725 v7558
mul v2651 v7559
sub v7547 v7560
add v7535 v7561
sub 1 v3730
add v7562 v7563
add v7534 v7564
sub 1 v4237
add v5981 0
add v6005 v7567
add v5723 v7568
add v5747 v7569
add v5419 v7570
add v5443 v7571
add v5069 v7572
add v5093 v7573
add v4673 v7574
add v4698 v7575
add v4257 v7576
add v5982 0
add v6006 v7578
add v5724 v7579
add v5748 v7580
add v5420 v7581
add v5444 v7582
add v5070 v7583
add v5094 v7584
add v4674 v7585
add v4699 v7586
add v4258 v7587
mul v3169 v7588
sub v7577 v7589
add v7566 v7590
sub 1 v4263
add v7591 v7592
add v7565 v7593
sub 1 v4724
add v6263 0
add v6026 v7596
add v6050 v7597
add v5768 v7598
add v5792 v7599
add v5464 v7600
add v5488 v7601
add v5114 v7602
add v5139 v7603
add v4744 v7604
add v6264 0
add v6027 v7606
add v6051 v7607
add v5769 v7608
add v5793 v7609
add v5465 v7610
add v5489 v7611
add v5115 v7612
add v5140 v7613
add v4745 v7614
mul v3731 v7615
sub v7605 v7616
add v7595 v7617
sub 1 v4750
add v7618 v7619
add v7594 v7620
sub 1 v5165
add v6283 0
add v6307 v7623
add v6071 v7624
add v6095 v7625
add v5813 v7626
add v5837 v7627
add v5509 v7628
add v5534 v7629
add v5185 v7630
add v6284 0
add v6308 v7632
add v6072 v7633
add v6096 v7634
add v5814 v7635
add v5838 v7636
add v5510 v7637
add v5535 v7638
add v5186 v7639
mul v4264 v7640
sub v7631 v7641
add v7622 v7642
sub 1 v5191
add v7643 v7644
add v7621 v7645
sub 1 v5560
add v6519 0
add v6328 v7648
add v6352 v7649
add v6116 v7650
add v6140 v7651
add v5858 v7652
add v5883 v7653
add v5580 v7654
add v6520 0
add v6329 v7656
add v6353 v7657
add v6117 v7658
add v6141 v7659
add v5859 v7660
add v5884 v7661
add v5581 v7662
mul v4751 v7663
sub v7655 v7664
add v7647 v7665
sub 1 v5586
add v7666 v7667
add v7646 v7668
sub 1 v5909
add v6539 0
add v6563 v7671
add v6373 v7672
add v6397 v7673
add v6161 v7674
add v6186 v7675
add v5929 v7676
add v6540 0
add v6564 v7678
add v6374 v7679
add v6398 v7680
add v6162 v7681
add v6187 v7682
add v5930 v7683
mul v5192 v7684
sub v7677 v7685
add v7670 v7686
sub 1 v5935
add v7687 v7688
add v7669 v7689
sub 1 v6212
add v6729 0
add v6584 v7692
add v6608 v7693
add v6418 v7694
add v6443 v7695
add v6232 v7696
add v6730 0
add v6585 v7698
add v6609 v7699
add v6419 v7700
add v6444 v7701
add v6233 v7702
mul v5587 v7703
sub v7697 v7704
add v7691 v7705
sub 1 v6238
add v7706 v7707
add v7690 v7708
sub 1 v6469
add v6749 0
add v6773 v7711
add v6629 v7712
add v6654 v7713
add v6489 v7714
add v6750 0
add v6774 v7716
add v6630 v7717
add v6655 v7718
add v6490 v7719
mul v5936 v7720
sub v7715 v7721
add v7710 v7722
sub 1 v6495
add v7723 v7724
add v7709 v7725
sub 1 v6680
add v6893 0
add v6794 v7728
add v6819 v7729
add v6700 v7730
add v6894 0
add v6795 v7732
add v6820 v7733
add v6701 v7734
mul v6239 v7735
sub v7731 v7736
add v7727 v7737
sub 1 v6706
add v7738 v7739
add v7726 v7740
sub 1 v6845
add v6913 0
add v6938 v7743
add v6865 v7744
add v6914 0
add v6939 v7746
add v6866 v7747
mul v6496 v7748
sub v7745 v7749
add v7742 v7750
sub 1 v6871
add v7751 v7752
add v7741 v7753
sub 1 v6964
add v7012 0
add v6984 v7756
add v7013 0
add v6985 v7758
mul v6707 v7759
sub v7757 v7760
add v7755 v7761
sub 1 v6990
add v7762 v7763
add v7754 v7764
sub 1 v7038
add v7057 0
add v7058 0
mul v6872 v7768
sub v7767 v7769
add v7766 v7770
shr v7062 1
sub 1 v7772
add v7771 v7773
add v7765 v7774
app x49 v7062 v7775" [f0, f1, f2, f3, f4, f5, f6, f7, f8, f9, f10, f11, f12, f13, f14, f15, f16, f17, f18, f19, f20, f21, f22, f23, f24, g0, g1, g2, g3, g4, g5, g6, g7, g8, g9, g10, g11, g12, g13, g14, g15, g16, g17, g18, g19, g20, g21, g22, g23, (@Prod.mk Nat Nat)]

/-- Decoding `2·|x| + sign`. -/
def zdec (z : Nat) : Int := if z % 2 = 1 then -((z / 2 : Nat) : Int) else ((z / 2 : Nat) : Int)

/-! ## Fast generation of the encoded polynomial -/

/-- `lcgNext` with raw kernel operations. -/
def lcgRaw (st : Nat) : Nat :=
  Nat.land (Nat.add (nat_lit 1442695040888963407) (Nat.mul (nat_lit 6364136223846793005) st))
    (nat_lit 18446744073709551615)

/-- `acc + (collectCoeffWord n sh st).1`, accumulated word by word. -/
def wl (n : Nat) : Nat → Nat → Nat → Nat :=
  Nat.rec (motive := fun _ => Nat → Nat → Nat → Nat) (fun acc _ _ => acc)
    (fun _ ih acc sh st => ih (Nat.add acc (Nat.shiftLeft (lcgRaw st) sh)) (Nat.add sh (nat_lit 64))
      (lcgRaw st)) n

/-- `min k (max 2 w)` with raw operations. -/
def clampRaw (k w : Nat) : Nat :=
  Nat.sub (Nat.add w (Nat.sub (nat_lit 2) w)) (Nat.sub (Nat.add w (Nat.sub (nat_lit 2) w)) k)

/-- `coefficientWidth` with raw operations (the `k ≤ 64` test is `k - 64 = 0`). -/
def wRaw (k i : Nat) : Nat :=
  Nat.rec (motive := fun _ => Nat)
    (clampRaw k (Nat.add (Nat.div (Nat.mul (nat_lit 2) (Nat.sub (nat_lit 36) k)) (nat_lit 7))
      (Nat.div (Nat.mul (Nat.sub k (Nat.div (Nat.mul (nat_lit 2) (Nat.sub (nat_lit 36) k)) (nat_lit 7))) i)
        (Nat.add (nat_lit 10) (Nat.div (Nat.mul (nat_lit 2) (Nat.sub (nat_lit 36) k)) (nat_lit 7))))))
    (fun _ _ => clampRaw k (Nat.add (nat_lit 3)
      (Nat.div (Nat.add (Nat.mul (Nat.sub k (nat_lit 3))
          (Nat.sub (Nat.mul (nat_lit 2448) i) (Nat.mul (Nat.mul (nat_lit 2) i) i))) (nat_lit 57599))
        (nat_lit 57600))))
    (Nat.sub k (nat_lit 64))

/-- Encoded `centeredNonzeroCoeff w words word`: `v − 2^(w−1)` with `0 ↦ 1`. -/
def encC (w words word : Nat) : Nat :=
  share v := Nat.shiftRight word (Nat.sub (Nat.mul (nat_lit 64) words) w);
  share h := Nat.shiftLeft (nat_lit 1) (Nat.sub w (nat_lit 1));
  share a := Nat.sub v h;
  share b := Nat.sub h v;
  Nat.add (Nat.add (Nat.shiftLeft (Nat.add a b) (nat_lit 1)) (Nat.sub (nat_lit 1) (Nat.sub (nat_lit 1) b)))
    (Nat.shiftLeft (Nat.sub (nat_lit 1) (Nat.add a b)) (nat_lit 1))

/-- One coefficient from its width `w`, word count and the LCG word; then the rest. -/
def genGo (k : Nat) (count : Nat) : Nat → Nat → List Nat :=
  Nat.rec (motive := fun _ => Nat → Nat → List Nat) (fun _ _ => List.nil)
    (fun _ ih index state =>
      share w := wRaw k index;
      share words := Nat.div (Nat.add w (nat_lit 63)) (nat_lit 64);
      share word := wl words (nat_lit 0) (nat_lit 0) state;
      List.cons (encC w words word)
        (ih (Nat.add index (nat_lit 1)) (Nat.shiftRight word (Nat.mul (nat_lit 64) (Nat.sub words (nat_lit 1))))))
    count

/-- The encoded polynomial `polyOf n` (leading `1` encodes as `2`). -/
def genF (n : Nat) : List Nat := (nat_lit 2) :: genGo (kbitsOf n) (nat_lit 24) (nat_lit 1) (lcgSeed n)

/-- Encoded `k · x`. -/
def gz (f k : Nat) : Nat := Nat.add (Nat.shiftLeft (Nat.mul (Nat.shiftRight f (nat_lit 1)) k) (nat_lit 1)) (Nat.land f (nat_lit 1))

/-- Read off the result unless some check failed (then fall back to the specification). -/
def finish (n : Nat) (r : Nat × Nat) : Int :=
  Nat.rec (motive := fun _ => Int) (zdec r.1) (fun _ _ => discSpec n) r.2

/-- The 25 coefficients of a list, passed to `k` (`d` for other lengths). Used in proofs only. -/
def appL (k : Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Int) (d : Int) : List Nat → Int
  | [f0, f1, f2, f3, f4, f5, f6, f7, f8, f9, f10, f11, f12, f13, f14, f15, f16, f17, f18, f19, f20, f21, f22, f23, f24] => k f0 f1 f2 f3 f4 f5 f6 f7 f8 f9 f10 f11 f12 f13 f14 f15 f16 f17 f18 f19 f20 f21 f22 f23 f24
  | _ => d

/-- The fast path on the 25 encoded coefficients (the derivative is computed with `gz`). -/
def kont (n f0 f1 f2 f3 f4 f5 f6 f7 f8 f9 f10 f11 f12 f13 f14 f15 f16 f17 f18 f19 f20 f21 f22 f23 f24 : Nat) : Int :=
  finish n (prsDag f0 f1 f2 f3 f4 f5 f6 f7 f8 f9 f10 f11 f12 f13 f14 f15 f16 f17 f18 f19 f20 f21 f22 f23 f24 (gz f0 (nat_lit 24)) (gz f1 (nat_lit 23)) (gz f2 (nat_lit 22)) (gz f3 (nat_lit 21)) (gz f4 (nat_lit 20)) (gz f5 (nat_lit 19)) (gz f6 (nat_lit 18)) (gz f7 (nat_lit 17)) (gz f8 (nat_lit 16)) (gz f9 (nat_lit 15)) (gz f10 (nat_lit 14)) (gz f11 (nat_lit 13)) (gz f12 (nat_lit 12)) (gz f13 (nat_lit 11)) (gz f14 (nat_lit 10)) (gz f15 (nat_lit 9)) (gz f16 (nat_lit 8)) (gz f17 (nat_lit 7)) (gz f18 (nat_lit 6)) (gz f19 (nat_lit 5)) (gz f20 (nat_lit 4)) (gz f21 (nat_lit 3)) (gz f22 (nat_lit 2)) (gz f23 (nat_lit 1)))

/-- Width band 15: the leading `2` and the 24 encoded coefficients after LCG state `s`, passed
straight to `k`. All 24 LCG words come from two lane packs (jump-ahead constants, 13 + 12
lanes of 128 bits); each coefficient is one shift, one mask and the encoding (`genLane15C_eq`). -/
def genLane15C (s : Nat) (k : Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Int) : Int :=
  natdag% "mul 19219696624031741256228976288557689359944544505453178914698490179782740673580766008449234553576393244793395947026503479456483897228546131698527447033628420808694112839990829232001319989940147876101680705626223378573333960152540536738311564185810624473572636019637342283005433720609164069055796632571435170914709615744195084494116144750567006920709673886753479118298727491830890990397281677791014058553534506771311897072697726829511670462570089974731006191062260805072196901068079105 x0
add 8418505345184611686874720590433268221927751184856754023122365884510423240663205845616924213699128347491257746945228552610537507155729394755386414890435753540570775927757539815104346837017693804674962524565120334500276195108917348185882337178897283171098193004069163929174978202218163310055291683669515608805367759306211699131393459324124677644584273286762564674239679123804485394355918432787896049605853577120733465462866205751759904562707021463648260991956365309912046218998972416 v0
land 44462416477094044617606501638596331727369781204591354815280785108625863000682559430588516849462327912302977740965976583959379033742862581063092530241730903133514207435981312869410149046884495678808696709003770374115978483184636891254004157807808528458555000941466545088377354350930400629893295649831567781293902625624306133570010767192943478980253715966265539689403240693901698510614624106899886404704187762892547504651284040967543953946665873518836519076076547311139569689056772095 v1
mul 1637987715719048898166645575691335581450811715247893346212199745113140060574570653627170312475495886080515149835447809396383330614792403317597273378844556057554044715668579269718074038528216202801102402195823651259874055632563149710796894701873203023171153919203568349412152083490359439637130791998396080771710011710149361694484243754446616213802335385474401624995161838168423205989505447085718630376603513302684643035451676196531875115723340750262564198151094272 x0
add 2097400467462368306790029740099517327989237522156259689431162204074043702672286815074171348948328950772777450362091663520571983286810367932226029603894419276026581610751475249802890759791591370880033596579731653978472310817822901865186636860323292407794867326734685971302965015795660498694737580456578628028129696595820313205382965951991374476328918532194262767715650029714739979362155462016200089197364745861406260731285412618887369024493959050433867749091442688 v3
land 2410312426921032588449453307546484504137437985127820069086592808396265726711641505182975780175072799785728022712421398253292486459881906986048377642639103107320556651460591360227234052271313453149427112880781282398680877981089585533072041387780305225652522810692086781984483929060529248396558906377609177796851701749205413225744167862000181600892979555300976230055190598918678360305772537497094338670651967448929821197846055727951727483462423646156590937307873280 v4
add v2 v5
shr v6 121
land 126 v7
sub v8 66
sub 63 v8
add v9 v10
add 2 v11
shr v6 184
land 254 v13
sub v14 130
sub 127 v14
add v15 v16
add 2 v17
shr v6 248
land 254 v19
sub v20 130
sub 127 v20
add v21 v22
add 2 v23
shr v6 311
land 510 v25
sub v26 258
sub 255 v26
add v27 v28
add 2 v29
shr v6 375
land 510 v31
sub v32 258
sub 255 v32
add v33 v34
add 2 v35
shr v6 438
land 1022 v37
sub v38 514
sub 511 v38
add v39 v40
add 2 v41
shr v6 502
land 1022 v43
sub v44 514
sub 511 v44
add v45 v46
add 2 v47
shr v6 565
land 2046 v49
sub v50 1026
sub 1023 v50
add v51 v52
add 2 v53
shr v6 628
land 4094 v55
sub v56 2050
sub 2047 v56
add v57 v58
add 2 v59
shr v6 692
land 4094 v61
sub v62 2050
sub 2047 v62
add v63 v64
add 2 v65
shr v6 755
land 8190 v67
sub v68 4098
sub 4095 v68
add v69 v70
add 2 v71
shr v6 819
land 8190 v73
sub v74 4098
sub 4095 v74
add v75 v76
add 2 v77
shr v6 882
land 16382 v79
sub v80 8194
sub 8191 v80
add v81 v82
add 2 v83
shr v6 946
land 16382 v85
sub v86 8194
sub 8191 v86
add v87 v88
add 2 v89
shr v6 1009
land 32766 v91
sub v92 16386
sub 16383 v92
add v93 v94
add 2 v95
shr v6 1072
land 65534 v97
sub v98 32770
sub 32767 v98
add v99 v100
add 2 v101
shr v6 1136
land 65534 v103
sub v104 32770
sub 32767 v104
add v105 v106
add 2 v107
shr v6 1200
land 65534 v109
sub v110 32770
sub 32767 v110
add v111 v112
add 2 v113
shr v6 1264
land 65534 v115
sub v116 32770
sub 32767 v116
add v117 v118
add 2 v119
shr v6 1328
land 65534 v121
sub v122 32770
sub 32767 v122
add v123 v124
add 2 v125
shr v6 1392
land 65534 v127
sub v128 32770
sub 32767 v128
add v129 v130
add 2 v131
shr v6 1456
land 65534 v133
sub v134 32770
sub 32767 v134
add v135 v136
add 2 v137
shr v6 1520
land 65534 v139
sub v140 32770
sub 32767 v140
add v141 v142
add 2 v143
shr v6 1584
land 65534 v145
sub v146 32770
sub 32767 v146
add v147 v148
add 2 v149
app x1 2 v12 v18 v24 v30 v36 v42 v48 v54 v60 v66 v72 v78 v84 v90 v96 v102 v108 v114 v120 v126 v132 v138 v144 v150" [s, k]

/-- Width band 36: the leading `2` and the 24 encoded coefficients after LCG state `s`, passed
straight to `k`. All 24 LCG words come from two lane packs (jump-ahead constants, 13 + 12
lanes of 128 bits); each coefficient is one shift, one mask and the encoding (`genLane36C_eq`). -/
def genLane36C (s : Nat) (k : Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Int) : Int :=
  natdag% "mul 19219696624031741256228976288557689359944544505453178914698490179782740673580766008449234553576393244793395947026503479456483897228546131698527447033628420808694112839990829232001319989940147876101680705626223378573333960152540536738311564185810624473572636019637342283005433720609164069055796632571435170914709615744195084494116144750567006920709673886753479118298727491830890990397281677791014058553534506771311897072697726829511670462570089974731006191062260805072196901068079105 x0
add 8418505345184611686874720590433268221927751184856754023122365884510423240663205845616924213699128347491257746945228552610537507155729394755386414890435753540570775927757539815104346837017693804674962524565120334500276195108917348185882337178897283171098193004069163929174978202218163310055291683669515608805367759306211699131393459324124677644584273286762564674239679123804485394355918432787896049605853577120733465462866205751759904562707021463648260991956365309912046218998972416 v0
land 44462416477094044617606501638596331727369781204591354815280785108625863000682559430588516849462327912302977740965976583959379033742862581063092530241730903133514207435981312869410149046884495678808696709003770374115978483184636891254004157807808528458555000941466545088377354350930400629893295649831567781293902625624306133570010767192943478980253715966265539689403240693901698510614624106899886404704187762892547504651284040967543953946665873518836519076076547311139569689056772095 v1
mul 1637987715719048898166645575691335581450811715247893346212199745113140060574570653627170312475495886080515149835447809396383330614792403317597273378844556057554044715668579269718074038528216202801102402195823651259874055632563149710796894701873203023171153919203568349412152083490359439637130791998396080771710011710149361694484243754446616213802335385474401624995161838168423205989505447085718630376603513302684643035451676196531875115723340750262564198151094272 x0
add 2097400467462368306790029740099517327989237522156259689431162204074043702672286815074171348948328950772777450362091663520571983286810367932226029603894419276026581610751475249802890759791591370880033596579731653978472310817822901865186636860323292407794867326734685971302965015795660498694737580456578628028129696595820313205382965951991374476328918532194262767715650029714739979362155462016200089197364745861406260731285412618887369024493959050433867749091442688 v3
land 2410312426921032588449453307546484504137437985127820069086592808396265726711641505182975780175072799785728022712421398253292486459881906986048377642639103107320556651460591360227234052271313453149427112880781282398680877981089585533072041387780305225652522810692086781984483929060529248396558906377609177796851701749205413225744167862000181600892979555300976230055190598918678360305772537497094338670651967448929821197846055727951727483462423646156590937307873280 v4
add v2 v5
shr v6 124
land 14 v7
sub v8 10
sub 7 v8
add v9 v10
add 2 v11
shr v6 184
land 254 v13
sub v14 130
sub 127 v14
add v15 v16
add 2 v17
shr v6 245
land 2046 v19
sub v20 1026
sub 1023 v20
add v21 v22
add 2 v23
shr v6 305
land 32766 v25
sub v26 16386
sub 16383 v26
add v27 v28
add 2 v29
shr v6 365
land 524286 v31
sub v32 262146
sub 262143 v32
add v33 v34
add 2 v35
shr v6 426
land 4194302 v37
sub v38 2097154
sub 2097151 v38
add v39 v40
add 2 v41
shr v6 486
land 67108862 v43
sub v44 33554434
sub 33554431 v44
add v45 v46
add 2 v47
shr v6 547
land 536870910 v49
sub v50 268435458
sub 268435455 v50
add v51 v52
add 2 v53
shr v6 607
land 8589934590 v55
sub v56 4294967298
sub 4294967295 v56
add v57 v58
add 2 v59
shr v6 667
land 137438953470 v61
sub v62 68719476738
sub 68719476735 v62
add v63 v64
add 2 v65
shr v6 731
land 137438953470 v67
sub v68 68719476738
sub 68719476735 v68
add v69 v70
add 2 v71
shr v6 795
land 137438953470 v73
sub v74 68719476738
sub 68719476735 v74
add v75 v76
add 2 v77
shr v6 859
land 137438953470 v79
sub v80 68719476738
sub 68719476735 v80
add v81 v82
add 2 v83
shr v6 923
land 137438953470 v85
sub v86 68719476738
sub 68719476735 v86
add v87 v88
add 2 v89
shr v6 987
land 137438953470 v91
sub v92 68719476738
sub 68719476735 v92
add v93 v94
add 2 v95
shr v6 1051
land 137438953470 v97
sub v98 68719476738
sub 68719476735 v98
add v99 v100
add 2 v101
shr v6 1115
land 137438953470 v103
sub v104 68719476738
sub 68719476735 v104
add v105 v106
add 2 v107
shr v6 1179
land 137438953470 v109
sub v110 68719476738
sub 68719476735 v110
add v111 v112
add 2 v113
shr v6 1243
land 137438953470 v115
sub v116 68719476738
sub 68719476735 v116
add v117 v118
add 2 v119
shr v6 1307
land 137438953470 v121
sub v122 68719476738
sub 68719476735 v122
add v123 v124
add 2 v125
shr v6 1371
land 137438953470 v127
sub v128 68719476738
sub 68719476735 v128
add v129 v130
add 2 v131
shr v6 1435
land 137438953470 v133
sub v134 68719476738
sub 68719476735 v134
add v135 v136
add 2 v137
shr v6 1499
land 137438953470 v139
sub v140 68719476738
sub 68719476735 v140
add v141 v142
add 2 v143
shr v6 1563
land 137438953470 v145
sub v146 68719476738
sub 68719476735 v146
add v147 v148
add 2 v149
app x1 2 v12 v18 v24 v30 v36 v42 v48 v54 v60 v66 v72 v78 v84 v90 v96 v102 v108 v114 v120 v126 v132 v138 v144 v150" [s, k]

/-- Width band 205: the leading `2` and the 24 encoded coefficients after LCG state `s`, passed
straight to `k`. All 53 LCG words come from two lane packs (jump-ahead constants, 27 + 27
lanes of 128 bits); each coefficient is one shift, one mask and the encoding (`genLane205C_eq`). -/
def genLane205C (s : Nat) (k : Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Int) : Int :=
  natdag% "mul 3681828218177750666749634995476817201700007525552297389242557751964771914669653650516270026876698075962671995047812377374641636579572138104738506330870024229324776782094120463299885578512441205178263701090066056082036534378407371442418049415482244278413131378729419768088892471908944885192761378047382478817184154180022481381173024403763261410615026752435302604987604938633321756256058968284959439467576073152278268713181940707025212455221036743913230608178119550478706311416309726627024391755920311513630885994105049129223782544273307602404270095937349743729081152202479847061709766988307794147180547916016513345331103475566847995086129399545628469325279132472401867639338009980200966126488607427771970157105041194044272103889288308431881127822798669408263141121766608933296667941763154352800228518319548808827265495776670875759031179964229402635850727044609179562501171729686504472060832042620859515033342334809568610792860973146015812640944862149371519905965452036708091889040472197822626484655815626309341406874828801 x0
add 12298516225707966378439025862025394360289684450634406192234495528739246665244362566451007357578107567560939221934878203139657571530627070278690061337679505087172288665743496223710964844031893865435727253766738357916467206074519864177780651376087537549481801287712708874436591473973793513184321075384346684683204716227525850189271358801698093035887190697007859529107436442629706221778945709422587680345643939566085678863759355950777295890585700071340707073421992609750566719847204817634380493835231836952560366407398405352523795919041816022711149103555262040632196362920817839492268586473243444139531070897012193467621210131721766891651560002213878851282960709113568865906767931088299435553056600044811828306994300522475269062039144456773444044952403818994951934651030046149521444008337411365648839625504994562095374882462080520528935305801450808862598208118577969384615393768068937640014774781273967214152007760521349915766675936779075305265076120229684137330501676545035768181074767315953773066681994395745613950287347712 v0
land 12409243089918625185967666194307106747432534449233389600101790805582460429945153172086586294899899783686298853054492684698964639569989326739334882303458522585729753478249388823067135621820893622980026152308402560679534223866416693096123334566499481822436472230962871773703063866042507796761704107968945090491135557025970073661271115604561287135224564131352636326549319057255526670358106329501542820960637761924901549079333570516589044617032717805337824409259381628452675452260584939409949678892616895060150777955423658121396714601756860328241514388789217890913656682253920378186664198609355456196150605027018941502098257351111028010194887435050731869008100902138149907006727023815223022328675194341322193677271796375388876854360523645350300000918433525024251057256586564683362526120008645404333391138699611366768996156879260669421298891493765565298124986832291048241600208731016815760315383872910192519411554398922094523844081890955989940862390188620626020636432833813552365136351936805394398572566565973122836462416429055 v1
mul 153649830658051169292557863860552444327152735046731725087541842039047665697107808510247282984319649702979239095362379244115425053567092438030836588786271118285180158538929968740126140765569321213997385561900354972871174937774842614934350017060234796590462546698966500999051238654953668000681328699210812375608899217370347052245767122457538162491053967161638338489628428547214743943000438055795821561185729492772481540911014541049798156152919806505336334230294022305402998909110872095767462155188651845871970252637623115340556723940743345050490079568807134752081805691923171507476472194589310789067975956654424890386869748497076873572540747731005836550062104267221721241727560296905270538793681625574729795524586424716009060769397657792239696487793653903364074648550263146258174197326947211560203426436839759501962470150385958594929961886255215233782164127691011981272686353770791308970566826717212003978303004277113276870755628344523889069901277894016651042671140600723970411238662937329037380504351981490196806838419437141758926546584731648 x0
add 220696316856524536460235948075594598407949415473304685118995203993854413639838153198486066775584491209484663625662871958080554167966624405524399437800380032176754472079844948581876925436126656111719976620048774099473234872106232835197719590616145371892652778398164875914828747170034970186068443066452030459464451479484339802320058303544272981575798311909507922806984462277515877234929555589689957677060556330621417116218296161005531281879718605443921936089858179792743003847030249538415734825273419099863973146283367283621162366604373954496405895652123661961911060769797196503409935977030772794835694818908795490864010908499262602359698023415515885100844189649812952649766163192619789446439965874500036636559536704087721284895713851957347801431982155540072052496799668364655861681770400144340252189963220477374466045192364516279212034436367655772310848680434963760345195037439770927772030261366444903274329299710268617097868998606589778238606693960489598159287878177841796731599248508650678500560904431798484472887936905148218736399616049152 v3
land 228910131428177603689346162948678745806898590411689607668806771291473966679442762611589023002869319860478891908642324665736245574712610715235829627984123165413235761444325092807559604403331363064224473955229592496405909963817178843790894873907300696042569599335815865903434821535891891936271922778940756632803006962381618431549263581158532691918294156171876237631995043232977707293697078195120063721708992984193981917952152313506960954129076553438608746227869651109818718657609847129248582253204225793547436750094382825356781192146299481669845366748931779748369698795998246832691234020016101335709165415359921538788863759460659321806264232687479307413415739545140268136465025019459268016933597780051623882483570802698140832772681993960478506749878524435922076363581455629150368324029545575043440015784413507992573798400935189852080826591497214471393091589644206045338526556706608683920961087014231928415427794281052804539293655625617358583215075167969538483683003068886971344361997450490100253400889434287179860967828471106557541515924602880 v4
add v2 v5
shr v6 115
land 8190 v7
sub v8 4098
sub 4095 v8
add v9 v10
add 2 v11
shr v6 170
land 4194302 v13
sub v14 2097154
sub 2097151 v14
add v15 v16
add 2 v17
shr v6 226
land 1073741822 v19
sub v20 536870914
sub 536870911 v20
add v21 v22
add 2 v23
shr v6 281
land 549755813886 v25
sub v26 274877906946
sub 274877906943 v26
add v27 v28
add 2 v29
shr v6 337
land 140737488355326 v31
sub v32 70368744177666
sub 70368744177663 v32
add v33 v34
add 2 v35
shr v6 392
land 72057594037927934 v37
sub v38 36028797018963970
sub 36028797018963967 v38
add v39 v40
add 2 v41
shr v6 448
land 18446744073709551614 v43
sub v44 9223372036854775810
sub 9223372036854775807 v44
add v45 v46
add 2 v47
shr v6 567
land 9444732965739290427390 v49
sub v50 4722366482869645213698
sub 4722366482869645213695 v50
add v51 v52
add 2 v53
shr v6 687
land 2417851639229258349412350 v55
sub v56 1208925819614629174706178
sub 1208925819614629174706175 v56
add v57 v58
add 2 v59
shr v6 806
land 1237940039285380274899124222 v61
sub v62 618970019642690137449562114
sub 618970019642690137449562111 v62
add v63 v64
add 2 v65
shr v6 926
land 316912650057057350374175801342 v67
sub v68 158456325028528675187087900674
sub 158456325028528675187087900671 v68
add v69 v70
add 2 v71
shr v6 1045
land 162259276829213363391578010288126 v73
sub v74 81129638414606681695789005144066
sub 81129638414606681695789005144063 v74
add v75 v76
add 2 v77
shr v6 1165
land 41538374868278621028243970633760766 v79
sub v80 20769187434139310514121985316880386
sub 20769187434139310514121985316880383 v80
add v81 v82
add 2 v83
shr v6 1285
land 10633823966279326983230456482242756606 v85
sub v86 5316911983139663491615228241121378306
sub 5316911983139663491615228241121378303 v86
add v87 v88
add 2 v89
shr v6 1468
land 5444517870735015415413993718908291383294 v91
sub v92 2722258935367507707706996859454145691650
sub 2722258935367507707706996859454145691647 v92
add v93 v94
add 2 v95
shr v6 1652
land 1393796574908163946345982392040522594123774 v97
sub v98 696898287454081973172991196020261297061890
sub 696898287454081973172991196020261297061887 v98
add v99 v100
add 2 v101
shr v6 1836
land 356811923176489970264571492362373784095686654 v103
sub v104 178405961588244985132285746181186892047843330
sub 178405961588244985132285746181186892047843327 v104
add v105 v106
add 2 v107
shr v6 2019
land 182687704666362864775460604089535377456991567870 v109
sub v110 91343852333181432387730302044767688728495783938
sub 91343852333181432387730302044767688728495783935 v110
add v111 v112
add 2 v113
shr v6 2203
land 46768052394588893382517914646921056628989841375230 v115
sub v116 23384026197294446691258957323460528314494920687618
sub 23384026197294446691258957323460528314494920687615 v116
add v117 v118
add 2 v119
shr v6 2387
land 11972621413014756705924586149611790497021399392059390 v121
sub v122 5986310706507378352962293074805895248510699696029698
sub 5986310706507378352962293074805895248510699696029695 v122
add v123 v124
add 2 v125
shr v6 2570
land 6129982163463555433433388108601236734474956488734408702 v127
sub v128 3064991081731777716716694054300618367237478244367204354
sub 3064991081731777716716694054300618367237478244367204351 v128
add v129 v130
add 2 v131
shr v6 2754
land 1569275433846670190958947355801916604025588861116008628222 v133
sub v134 784637716923335095479473677900958302012794430558004314114
sub 784637716923335095479473677900958302012794430558004314111 v134
add v135 v136
add 2 v137
shr v6 3002
land 401734511064747568885490523085290650630550748445698208825342 v139
sub v140 200867255532373784442745261542645325315275374222849104412674
sub 200867255532373784442745261542645325315275374222849104412671 v140
add v141 v142
add 2 v143
shr v6 3250
land 102844034832575377634685573909834406561420991602098741459288062 v145
sub v146 51422017416287688817342786954917203280710495801049370729644034
sub 51422017416287688817342786954917203280710495801049370729644031 v146
add v147 v148
add 2 v149
app x1 2 v12 v18 v24 v30 v36 v42 v48 v54 v60 v66 v72 v78 v84 v90 v96 v102 v108 v114 v120 v126 v132 v138 v144 v150" [s, k]

/-- Width band 1001: the leading `2` and the 24 encoded coefficients after LCG state `s`, passed
straight to `k`. All 210 LCG words come from two lane packs (jump-ahead constants, 106 + 105
lanes of 128 bits); each coefficient is one shift, one mask and the encoding (`genLane1001C_eq`). -/
def genLane1001C (s : Nat) (k : Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Int) : Int :=
  natdag% "mul 170621507402784080931585498690217011024815862508660300481533429552324447187232869928124792293361689692582675790311529694322695337866054713063111377296128948889697228982185200917775054136619598937840663111891774211978679442801006561610405797747321779297175195381609647341375540187256250990218661643345228681127861575699526565492851923337198146967210442875081580246892014887910686898991095766535775491263705971227767893804286596553487783719037427686283983054823185155897593573350311357349480202579526342907781167799936616700128327718503265273509513629313424617720793930091994066325864661274272657870695107988231695496971313174151559481686624165602981017437780912532941655053273494772613512789572430495145121617701242986136181487704585375147628534313649140552936180287610962567142037077323590460196730019128310494042470081115492062651683239169854550193584313755099271710370299806011380692496397063176073461373446864729258216359947041759969923749035653663421238352546556884066086020673312179139025335730685645793298673140995245949222806916785698178321991825496005312023210930877101096169611703767178672812904777842206576445151625043423469098020527815121253676759267970863611175210739651460740098174742300993702465482170498436240585660293886277799104801158965742846498976922875593984929566506410239330121045173477415855059940310673570065385522144018418616954936423273146733127671555849397119044046343248104438612221508652737451069304325747608853892688739096983907438372218091350608933706137491484383402612533202472797131423578229558474307373963943257836309027883364414457423807266795055648765790950855308816095164031880375679265997274714156816521656377976726431261869386326458370174370845208601628695759786659944928940647685957472252132716827971561413000781453025731822320431257227631794318253718748278343554851964957469587456435083978010449730472546872534815305865598435740772293623651510199125220432418942830672856555312587976237375686514065166070887478495554630000571924961917972567137371939729997012630681608834738136239379867308842500095242432137688895948332674266823994517802998409437155567441570041051856974237846574441015044213048807207837507382917753779687856998827869066024885677215197182618681732884921756372448310999627381747595363198692564435646494425240898595330508126199963387458554388466977251627930644517908903625472141396319104300345240674646094268242557233027386044938929234298249126659409924467638520209329403732574409260109758444460152164353201493316648963013032866900035344045475851295753612486744673589053374813962202160755538037733356683348029716719627494058001213871169560752114739584561715372161005205679837878636352624424397632326492089752167596792745710819524110714066151660486048029303049509819217957597277580483960311496180724467388226784231141066773248669899923384206430105233933230102250354945532879854057875275911749963373407549743205684450324703976651439169463897660444491848025113183742104102072116261363123358398599306114853424081962765321180304202580115530889657423390504190331667777860480754407980474489589859931646222411814194506283313948878072058309661683327687080468390595120564194253367659288842905059446065589416422599540166580683775669844306204648472918163377283933762673993212265442047756203001544453428808647273016747578377229985204611645170606584658394399617868378435741369499508164007039149409975208036357107941147173813451457187536554768218971208651343563193022830156619315121436843110697587592234914818148555672836199608115062612733097379823387571731256225120443272780576518792527638747924881272145492358699708828368987284923586101772676526123390855521321231340819165390659033787620909506658224683438383410129722791817851062565445050264334648699067888702672584185264487959155482528063198662316183721540412305480878638893605631763716766861681252669047837838301229000213223396026897425994137292748617105677781444226031096641770559767531384152255262965196397619641587024286033382445553625406550781037348238906954882486282761706881489639164356590462053135733832244721551168948273683225681355841591681998615145393713303257089 x0
add 527925780954922141139863323364308839644944700459374563603994292139668190180266328705492682030322669829078107839950496516223466260948473827737970299295746397069008333482307370914341999493087141040784712478637110038127686280644422052075557646601124743703061701092081694582302617424358055601664015592233455428830098381376845930354805606055510921239580985582838127050693065176728651386717258815916901226360202382760250848912844248233673657762498193716815257143616664166994281958270779072688965458394201036499994052546527411287743303909293744336812851083031531110579333161962958169722727029705202880251727005482417082835884515596947290029214726869602456655191874907535245025271014897886090412719678877225168782267546044289128955269716363475609144852838681328092209927010235707865186204827604068080236618313319932190847402993465854632841404245050280198004714674518598511911228536928129936425591530517109988879823192079167193364534973815847257833792129031352565984620578537287476769223732433157674568623137136809120994629011061361561196349070691315509174261733854795732716574306723191211142482797038600771387797477414497479657136481604641852015342422019709115427865190308308073875602539479430445640968659290102393955962784809331496479099834418837133855305478492138315877641684422322600620261309316412166051236006330462587579524588544093806032130464168029068034595027113076802452597003955716721903107291984529049537669322310205060225067177894620333551473810375719354177238363988296700501050417844478993752338006286463324388760896045254152377321769265648636153832295295821089523253193708121623632064386630700798391793684162293319011517413940921055096190862472239396257312804404370376867431395970343649519343385266625127331183439024048312605918106932568849138425804015520288778135182191277106771256335293498220464169161639985842873143678754442515569684025528847905180068769181905003572130075227823689664669584377074236649473306951818209025641357397128809960051155167825607363007434301198439794098686777313943910333749666676880940308812205972376101811115201434871643341421414716267283227740911542736236929982643867037374575210798998528902246382134370722421731712377129826980336357934518167779111472519304119403930013048009941366933432758060269947606648492407526518002980602962565698106508691304945564191164308521007785192305056777005344994421946444183185384309570498422820344803030249176032260764123831398570467574626451154226236995648111945713797861007705381814151249896282487318624921568264636856125999791561164627644532776341223461975191592065392604531781717956310941452074261797088221509830349658695476774621371528936008917255093149556208001031351492131804499476278998924979729960515199284934654933051652849364809204031783805848750492156494185580278826314581054775737528051238967964555971176561187011490179673140099051176398671546318736916056139829472410145314464562636672652938553597804832036546776951802330284814810702594635364290085059477506956730152003601596327177527065031069029072668064467104812806392983177217301958099491642960210943706909104640873545587880954718069603032311010202394674335367354904423309689106668015884421513115434869970456552663797432468186681915120717015840348284856275444483548790713735439395448364391062556823855345397475735284487301562934181378862766456986385580770422549967772181503217469924976466736827508639096215178985472265411332815513793501685972698136482316772745128652479124953288584603948271934158098825256268081367348662233790856617396370442651357984872296325384213274298698615520143172202473123024877171139922255116671268367632271614421696531981964128349871552978961678461490916482307276170551365379536593711232247072441085200103190719749176271148612410204982914400239397742473262523048964712643683635407105022441280248283878798942035566752807050093968742006833427436914517687696078678658714360737521657125132508267346230031659282487671978166172978006718384080057844740676428773682154591646532459387747426866641270364732607499663755774302865146287470618014536879156240211833092838440704600772936792761807440213697197826359909416960 v0
land 1285468522323690007141453047427365991367181935911608271557960305359163807447117705875390985236998226802576107921972319480145714398284486847904304697646771909009718311946848345677271299712401697755777356521562305060961880033579597512122118793532868386799310309796218285754265814402002747542363527041254785698760127861989522250932395116063784321671080541313926808153912059580305654331350096859522726214058060664641763284946753657065391806784732428103204493417976924246739071672901157265885311207317788471547228114698195007696532945006619917629058489313742378244678257103494636690047220304074886175807471375197793496878028811982167590873616347636299690536328588941076150868053306980392184538237798979699620770077632804524398512665981199446387587323808589152496887460288016277679869846298003562687487339512445112861288880263057528540251475357344989238094047760496881595076805137067414263784254457478851843623505505341222274072668286731606683425232495444581232500360001213387458495880775500081122490156388691797417856677821414921344705082007890971872207902329282260504818995078733501769986426930883527241528260423254632189886235374404735272212731335953820835622004601033140550501196074558526138645615166909195116179955050703026043207939761650829891807455297027039954133331760121290890998150103250920908344263378967057888331532915547192565487811895865146420366818859531831301632216422882159857141254970762039425952282793335769122730210183603894560723957517898565009207463909956413205933366202218551672443237261970905897053740656371502788885299971228867920688497703210943978523973778282064123094231385940571891993416857095770627684117618522874524458600867998251385813881342681140586927705321499967529502962935377064653282897244701877469971059338353717866685172705258453333346531371636137524851016565888086635213368544167327279310572409928964612830280038154810569695378237839069250471596255450209548278476957001215550064994665457941971971749033005340321527350394116877611425081166588411932644936843080694398377395134552982538735169453397472269995954342149895035852895626858417990070799406409177070935266594840775995862802860581989729232557484828588108045156119180608960118316287004220432893381493651533551926015973893209793960331523239048669839553737590580542306828399450153342223551536615102077427876437130738777171376323756106846977466164018377066764957182047394210654062042616075157491937175821828282843494976346953026869751529514181186243740276085711875019541702474787318200762311440146941017659545198105326145487980642363403970668974310627957475051450457494975106603508041220995381587853469596042043536363116186864345514867841587912295257832924837391086551266144788250883271202597393584571409171808561423130707311954110334423086019753275108172389873629241017764913578583062077630344309937229828198912591186647897772042972946101927164665533517627212461459933457603643324450850828516922127795316287570823294732242888065612349611715390975508536987212675906212011744572730992324158183837445453472140606093888248705513274113540863799533576307348010934222215480524566018215087471303412652691258816439015079821264169212100308810253559120013747113241969546036631735971638726521400823085869029442407598045755037896835152878351707903692003655169307766499617131905372162671339083436203057138764643357666707052876040757387426074169156887486843169401368920996818902553789912770515375004426967835014477647768674413958910638011912501850384222084688407622035549219909402499993464419223449185730048337147788035271580268035077997482476010571591934260290140193360904192752459883700472229060076247999662059834277397355608292962298499595479435413157704362432299729500786423485450489424538044460394689500883814468865465593099038239272884292169595599733836874096107771076515479432024364382634242431450685448787773637172069177500167049215971849561827686353574805424540875287025906796460586720150398510153836027958098921176629329848288290831032689881418613028512152440447347870649546094275682797296451240073868604445500566498290402433192553650182730114881210148136355653778204318004105829154815 v1
mul 48278804312276638809078484315299978948302762268406738534411556144291984253706613183847964633971100388232534887210426418273264742326768330433133054470983798558819569183511929990353538069234421484304233735559137342402218003482653546551011068159449047890690174779131654762774452689683733917915615305640563624438815225283361720181296837415262520276555174613006319209358348552838751164775103450156407502692768692188232325354676104145790171441174172398812650402122869426630395427403347240618327191632476556034491017229701698742083756881780404796860627106218677232040852602528005925692463125447836989351533391983899772401742573510682645570662047746382080333301862569777414118184485934908284177130091413811941225226429810961862233038475905712708046584555472374824890460383885787892747333822229948394266004687256638127058964546000130128422958222741639296585529550232746872120833189377076814747033871554930959659711578455175898268721376508475054550404621618211893383721274056080991736825318500603523989187561586479520988051427173783839666316538403647860513059078878783494136062055885640050492338362541014933507679049022433687917369114647501417731357037015028649383941614407249993196298083727469914169023069586019343177726494018330872504161148009657249653317823794778279129899664554109472459482756320724141301108147042593052232647458503080429904342773122117764220733462632101266578191776189828157410337954104109771922549932080926602420442651118106599272656059789713757177900269203718139698780633874194696599177839503382414618063740696779947885560067617474222446755771503121510730278961123776527606206638460356329782622905986519206692771035608559359903012588608919898644412426057589331702751388734511617241133692778163717151756224684863258000632688584275674725638955312001773749180914709042079925928177987637898137563871997747471680474261525549368294881339684985066089675507566485693063782186858966099947262917146493369565491527101295230965145749320066665769015998534336422030616791875695657011634928942929245740780486942187065913569588413080821384104156358103762368584203272263412565666459188259496478105804706462373777783793950937642503399551176688011859424889282114733949485894479823459563719285710668024215467908187631387470185453450636961578322237808902611712752350630436188192387718179847613847189953087808647066342911058263217268419734649494598525845537884696656189717884154074233246662701274028176244863302859413223979213097889280662037050330691361320690836317434570265229502152733624472099827629148917497245696277038946363593583477344573569627612164414313145651713499812917461201916802451764748924114297134602274516728966525366766675555309643624186356504192054926203239748403227002130018039250716701030292078169567760076203658801366586196308753556607170478843078357133541862642385543647524680836412749407428435170324694030271390582497709925293946805133926177945139275471953536027836545326024920492684082344412544234324012297129291099673894517746553915047959042227160933471023174745979591137750620194093117468058885701974423593175940869121022255102535794386223981614679698635047610405542193064867605672303392962220051206137503911796564075336833910508445616272109605490615278316504482555118428515743705281500081332240384872274191565985311622531423809791522927395145156385622368128623732898632776537783971810516071635079054888547855009437579720265344948269047739562245902181935974270859656318019035408785846702233559562538366650761690746553809977303626004485359866158134251000637779813694527834310262979457876778007991747057873167229845832734839830719805195322820086595341263751260318566492429593716487782779338519649578538748442846866584582484370689236974469390370548594453696012795780258618195520023983382440538094745885650853987227146919082480698859565702273430521874616685135499810933705627152492345752958667084116151882298432962360295401805655448758924130404890699671432470787031798240006684849270310396832721617665164790812900734568639051947075614262650474888446644027058052749371660259030759094250511038223370012031303019331912641174663214399488 x0
add 33826905970107108778135592719161805221143622086568144396467230169838662525412895344064105753279440371412670082703795074619906757494535716674485443726968274554845874517953233099641869595216985215540917693883428704240779347997455457218495382053617924216127867789840500536677844396966900972732515376709514705695006472183687639548423153828900483579165698487169149602436206144908979211469295510726587651838638837181648470297048703566632150447594837864209859518753417214115324463613232975290482701254257312492407420625002255438373920350276544779598967095679978498744167138347327027222500617986789262628091267979217434564432489188364719012253568476796402905707683628233067809612266986802763844382566278982602339678882231469570705525402458377672615285763992749155269148889398325733131801539179485787900459525755597620348734384729415654738238570501391537163163263397525174554145730428685994955183934686091583261848195277869712250396013956333620585664911900872905233609601529083507463954609067680474059419883349494632368675266168612212028289905115248564680576241372835438419574510051487725592603723750816240524446128923419149279002576511895702640352607272908204671278386640862181501564817134807692819814180083250538509441382121577953811429068567144698107410097709603119734338569563603532108843360736727084486615416925771305997315319139088539859025929319555688568000200632970727938252612665550052749967274620434195058021790268707379772785344805281642864647840420698300394300182448388906444512217023687628401237176175609434456694941167400210765682284911641850428779115492182923725317957543032985095638882087690694563883306922238992458938346927628594109807360881634303137229013041872289706777575894618227363413380694361285316256741623731977124395233057862314843972661703270026852102367348820229464064690621475185280329671733283134075999294020103827232056605786547638672704710934041065143237277790008082666259128431189942742512481388434437458097647390842694109401636709964174624739263395025763072444426161470650609140541249641325345425074503709991975035112609274700502765546774659723957517753012037840510177338524132966879979490229481811936422090853293639419912541887685592865964102310362020132039197554882800797514472022499375491837113059691806551877961758696402090812907123879697214055651784606047479318855121050808880702123957688055532244432028968696809934666012485978206238086994961290473503897295738893814653408359549000369585613108007638402444735149023325421641302855045032968871536533270958394655615228540168360543232293953145289613095588048122279988075233267731496664921915326954561518000950339216111310534174356873091525499946005280851068548405831316185024229467534703198196709292246059878192253275831741834680091246518451126427318090705500491541025848527435205315480464521645007359130483271363916386557751770300838001155699057548951017178103445971471541689792572322235667290186566588352839153637434154986326140528803360102216612779343225169733577567477543671305026852976304807272418240098523097462891342796628451287441889028917167694700737913126128754099425769635231552832711485617817115969800510495350868562605474432358613657517891443280957797631633296582456829866901549153006899389125664059329786963643935507459928621824736183630841238473776600233590354774646232504678966384540548936552840924247619238773950867033967278467544465674366636814947975258732748502817479074266007429487103104166908785920434237025327502413214277263545062642037506858826075201061842610149226421864567366411620435239942861118441455803639547700984751252969290340669775499061685918954683440053740480475849418334089941778918612579737782219881642090966548218056342658302735511770294609929554833753704588802987476936426177421094295747506442616725728985736358739133985644802236729519985568174900913954056721338319015310851428318939968924099231744247304882166049377503724983369759148612539664710825007139246156174163654743186293848436595165570482293081805730607601869950441640865100100066912314776783799844058730102791074175447088536205413742603795553929255712427570120457562619904 v3
land 69685388228253793008130936394344651149374759118642061611244054625386357454956736381609189668912334218003375462954845545167625831932383905631764184701353076056412785222493271740399359483208579111569798399288721476368712369214440710298394767402943116517893910844570449763074615999567152266160851119337925433313864896091257718112386538052485073037707030203895633346123081080175212273950473505189510254798972147972325850038045287239580987476884347365776208766046833647228926615944529587424523210720044164259453498320160184220853097586846750705592969442084357936915617906671964806454524420275993880694697311375484805695265656072597578616496292430092180744082474432730660495298919276831963882275092246116494127299242260823917023555860842669826986553233517959440048809029861537132729981490497312101417523854819512403791083151143987845793044766587854613339237858988264081177687743011006468284263603775823895022299958316158018213575815678136585284011195675224418214701183820478019300536297032894082547171596316406184439021905539818853330600126235240666603022986393939781870471288448314635247247686416546517784994619869853957224480152810981675130533066501581538331584135159492494551659829780169179828725387695052043459913857181962863491811659060589576942702397993776791973915096633698692304447250845166186825338211831144389855827870496832467924430215808529301476618808137228567062282999526371354031523508842083332421120443221194242440009785212500130866352652446328163715847601987030666771355698721704639432303279225259395329247414360029671668894699252016574009114315740417293589110577947874816407370387340713387873393289101841469235108567739020149644591085044939136547918395665049482136187821047907500234277324934149250327907151343852355339015405006400516684502642327179074607580557965869935777698577501764443370455294141841170796432595683847749641174915122863020409579460378563856843485048065572632469172340192814483240143849817409075042754571796226196064380671260905147490888657354851433599261586228134669663582253300965042046775317315569443147756043669169660534362297532813491553389253792075818302055383536519356705283746363627192241456088582669429990648511532420252701821763942489019544171017500282279927434346517294710377753777683814321677335201602787668242828373268318318992941398508405327488111101926520467968541161017274781650034476454491436340369009299797654002453920679253146274646496431043562051163595840664950215175939443112560750035056798265709229676722825832207465792219867371431856615146527707245902802552289582061578194017727195953266868251989995943586483489369326753587593031200259207347710354008321688974026789816038113012421780082842421562725489006224753666018630548302080353785068997057764715656955585864389038921736861126750174599802421296672683750840026352200161967771217701228764235287090373407318689187071463079406294021393753358710154403380787116902507995708905472563045319842727258870183179914358038962172586284288229311093075528594479326900363275610322342275360294212885680493232341145164259066754980628799711173566180629875163675807381290033935171210826827687881069164240117922653358811260548383738206614864026856854555012126528701253950204477442462474639772394783546259342896659016782128169984774621031854553415767323561029875388169729933314754037230578819610274212080291622935194126416744613037080728509063425469756377467809069754810816870735724665328931258588902921008395369561014202615862228739522001956773118617660350339885631847308681696523285897550942254399568939926262889667130432209489780907775160939735791811454557631618490726464823082419524120142260702487730457169450638743368444034188024302259968393660082991691340866906856934747041567248712856051146394279885511526998519401007166410942465545489692139844410969939487146434122582702298323707704927887839441724290903623981325125891215927461537346651857688146902880450688568653489970523501155416361113908777104640630081893167278530244173071551268154005013077893361492962383607472226015682278111621713292251291616505147252054248938868584395765613959876737820121051955200 v4
add v2 v5
shr v6 81
land 140737488355326 v7
sub v8 70368744177666
sub 70368744177663 v8
add v9 v10
add 2 v11
shr v6 167
land 618970019642690137449562110 v13
sub v14 309485009821345068724781058
sub 309485009821345068724781055 v14
add v15 v16
add 2 v17
shr v6 317
land 2722258935367507707706996859454145691646 v19
sub v20 1361129467683753853853498429727072845826
sub 1361129467683753853853498429727072845823 v20
add v21 v22
add 2 v23
shr v6 466
land 23945242826029513411849172299223580994042798784118782 v25
sub v26 11972621413014756705924586149611790497021399392059394
sub 11972621413014756705924586149611790497021399392059391 v26
add v27 v28
add 2 v29
shr v6 680
land 105312291668557186697918027683670432318895095400549111254310977534 v31
sub v32 52656145834278593348959013841835216159447547700274555627155488770
sub 52656145834278593348959013841835216159447547700274555627155488767 v32
add v33 v34
add 2 v35
shr v6 958
land 463168356949264781694283940034751631413079938662562256157830336031652518559742 v37
sub v38 231584178474632390847141970017375815706539969331281128078915168015826259279874
sub 231584178474632390847141970017375815706539969331281128078915168015826259279871 v38
add v39 v40
add 2 v41
shr v6 1236
land 2037035976334486086268445688409378161051468393665936250636140449354381299763336706183397374 v43
sub v44 1018517988167243043134222844204689080525734196832968125318070224677190649881668353091698690
sub 1018517988167243043134222844204689080525734196832968125318070224677190649881668353091698687 v44
add v45 v46
add 2 v47
shr v6 1578
land 8958978968711216842229769122273777112486581988938598139599956403855167484720643781523509973086428463102 v49
sub v50 4479489484355608421114884561136888556243290994469299069799978201927583742360321890761754986543214231554
sub 4479489484355608421114884561136888556243290994469299069799978201927583742360321890761754986543214231551 v50
add v51 v52
add 2 v53
shr v6 1921
land 19701003098197239606139520050071806902539869635232723333974146702122860885748605305707133127442457820403313995153406 v55
sub v56 9850501549098619803069760025035903451269934817616361666987073351061430442874302652853566563721228910201656997576706
sub 9850501549098619803069760025035903451269934817616361666987073351061430442874302652853566563721228910201656997576703 v56
add v57 v58
add 2 v59
shr v6 2327
land 86645927941275464361825443254471365732388658605494267974077486894206915868925800719999200190754361815543475342543861619655442430 v61
sub v62 43322963970637732180912721627235682866194329302747133987038743447103457934462900359999600095377180907771737671271930809827721218
sub 43322963970637732180912721627235682866194329302747133987038743447103457934462900359999600095377180907771737671271930809827721215 v62
add v63 v64
add 2 v65
shr v6 2797
land 381072821083495145432323880589986121307201921712032611188861933548019011086397170424842053596617672260721060927906081896416989218663120764926 v67
sub v68 190536410541747572716161940294993060653600960856016305594430966774009505543198585212421026798308836130360530463953040948208494609331560382466
sub 190536410541747572716161940294993060653600960856016305594430966774009505543198585212421026798308836130360530463953040948208494609331560382463 v68
add v69 v70
add 2 v71
shr v6 3268
land 837987995621412318723376562387865382967460363787024586107722590232610251879596686050117143635431464230626991136655378178359617675746660621652103062880254 v73
sub v74 418993997810706159361688281193932691483730181893512293053861295116305125939798343025058571817715732115313495568327689089179808837873330310826051531440130
sub 418993997810706159361688281193932691483730181893512293053861295116305125939798343025058571817715732115313495568327689089179808837873330310826051531440127 v74
add v75 v76
add 2 v77
shr v6 3802
land 3685510180489786476798393145496356338786055879312930105836138965083617346086082863365358130056307390177215209990980317284932211552660930305235775636164742230126362622 v79
sub v80 1842755090244893238399196572748178169393027939656465052918069482541808673043041431682679065028153695088607604995490158642466105776330465152617887818082371115063181314
sub 1842755090244893238399196572748178169393027939656465052918069482541808673043041431682679065028153695088607604995490158642466105776330465152617887818082371115063181311 v80
add v81 v82
add 2 v83
shr v6 4400
land 16209045190941378744189093217543598246142368094697019140608036444104112544581672446873855659949624196438272994575393707743731058888327247296433104820757670652582741419537146576894 v85
sub v86 8104522595470689372094546608771799123071184047348509570304018222052056272290836223436927829974812098219136497287696853871865529444163623648216552410378835326291370709768573288450
sub 8104522595470689372094546608771799123071184047348509570304018222052056272290836223436927829974812098219136497287696853871865529444163623648216552410378835326291370709768573288447 v86
add v87 v88
add 2 v89
shr v6 4999
land 35644067325173400145634153169533525975728347712879374457649941546088087243817792082077443838416964060770643043543706307114755505635745609361348916560329798345718708393439569922522454626926590 v91
sub v92 17822033662586700072817076584766762987864173856439687228824970773044043621908896041038721919208482030385321521771853153557377752817872804680674458280164899172859354196719784961261227313463298
sub 17822033662586700072817076584766762987864173856439687228824970773044043621908896041038721919208482030385321521771853153557377752817872804680674458280164899172859354196719784961261227313463295 v92
add v93 v94
add 2 v95
shr v6 5662
land 78382132970517478991165606422426233672355708521949855379734648809861125861064803929830588940942115354940041435601982738271645192059633193360683542052684438972998018132574030730004068581526319939960438782 v97
sub v98 39191066485258739495582803211213116836177854260974927689867324404930562930532401964915294470471057677470020717800991369135822596029816596680341771026342219486499009066287015365002034290763159969980219394
sub 39191066485258739495582803211213116836177854260974927689867324404930562930532401964915294470471057677470020717800991369135822596029816596680341771026342219486499009066287015365002034290763159969980219391 v98
add v99 v100
add 2 v101
shr v6 6388
land 344728266443874206170545512964432112225507069317819522056079337263512430464013488758041250121488036739611555846958495676040441511948045769973944468809441663382665538511073745187088876036706973599091474545756168257534 v103
sub v104 172364133221937103085272756482216056112753534658909761028039668631756215232006744379020625060744018369805777923479247838020220755974022884986972234404720831691332769255536872593544438018353486799545737272878084128770
sub 172364133221937103085272756482216056112753534658909761028039668631756215232006744379020625060744018369805777923479247838020220755974022884986972234404720831691332769255536872593544438018353486799545737272878084128767 v104
add v105 v106
add 2 v107
shr v6 7115
land 758065474756205534740712640850831325809026375545262017157740252942407691741394964028749223060862538061761587254458531838950966818415436714572405896016201728127175281260180617944465471499803928137335448825056869507271897877839870 v109
sub v110 379032737378102767370356320425415662904513187772631008578870126471203845870697482014374611530431269030880793627229265919475483409207718357286202948008100864063587640630090308972232735749901964068667724412528434753635948938919938
sub 379032737378102767370356320425415662904513187772631008578870126471203845870697482014374611530431269030880793627229265919475483409207718357286202948008100864063587640630090308972232735749901964068667724412528434753635948938919935 v110
add v111 v112
add 2 v113
shr v6 7906
land 1667003608219963568519962947680314449286189580578977040099064452941009309454408017880358050217888572685732477648358310111472200413529841270090839013082707511523789394878503639615769571477953506182241254033971650495422687009369115322790969342 v115
sub v116 833501804109981784259981473840157224643094790289488520049532226470504654727204008940179025108944286342866238824179155055736100206764920635045419506541353755761894697439251819807884785738976753091120627016985825247711343504684557661395484674
sub 833501804109981784259981473840157224643094790289488520049532226470504654727204008940179025108944286342866238824179155055736100206764920635045419506541353755761894697439251819807884785738976753091120627016985825247711343504684557661395484671 v116
add v117 v118
add 2 v119
shr v6 8761
land 3665779701564795034165604343510379326812382614037843523768505561895816192685171732396196386025552432054958017180031964169522798176905392217656963333320266191425647911421339149090150561469309283359365121053663391676919110861662410702765924749628709797886 v121
sub v122 1832889850782397517082802171755189663406191307018921761884252780947908096342585866198098193012776216027479008590015982084761399088452696108828481666660133095712823955710669574545075280734654641679682560526831695838459555430831205351382962374814354898946
sub 1832889850782397517082802171755189663406191307018921761884252780947908096342585866198098193012776216027479008590015982084761399088452696108828481666660133095712823955710669574545075280734654641679682560526831695838459555430831205351382962374814354898943 v122
add v123 v124
add 2 v125
shr v6 9616
land 8061134813471454564702450331367746071149403778627342561766978592325956765086744071570087522699847227396765060321916636335485039665263146015175460486800225477728068298324662539195732386420081192825687147647265448061340763744378078290380812053940375922997109693874174 v127
sub v128 4030567406735727282351225165683873035574701889313671280883489296162978382543372035785043761349923613698382530160958318167742519832631573007587730243400112738864034149162331269597866193210040596412843573823632724030670381872189039145190406026970187961498554846937090
sub 4030567406735727282351225165683873035574701889313671280883489296162978382543372035785043761349923613698382530160958318167742519832631573007587730243400112738864034149162331269597866193210040596412843573823632724030670381872189039145190406026970187961498554846937087 v128
add v129 v130
add 2 v131
shr v6 10535
land 17726622920963562283492833353875882150307419319860869157979152909707315649514250439943889552308992750523075148942386782770807567185698815677056677116184170553481231217950104164393978236130449019315710017470734562946173533283208371259654747728689409291887821024109648618981425150 v133
sub v134 8863311460481781141746416676937941075153709659930434578989576454853657824757125219971944776154496375261537574471193391385403783592849407838528338558092085276740615608975052082196989118065224509657855008735367281473086766641604185629827373864344704645943910512054824309490712578
sub 8863311460481781141746416676937941075153709659930434578989576454853657824757125219971944776154496375261537574471193391385403783592849407838528338558092085276740615608975052082196989118065224509657855008735367281473086766641604185629827373864344704645943910512054824309490712575 v134
add v135 v136
add 2 v137
shr v6 11518
land 38981256045599996321413529551500753243504907430380030107471625828851794763065704409862460263528041036901219664925634672733836679460812376186311949185250613678125110799825892119483158621960214593411198373916873515494742391701579499782985454461875862451310955212417110188327314359967656443902 v139
sub v140 19490628022799998160706764775750376621752453715190015053735812914425897381532852204931230131764020518450609832462817336366918339730406188093155974592625306839062555399912946059741579310980107296705599186958436757747371195850789749891492727230937931225655477606208555094163657179983828221954
sub 19490628022799998160706764775750376621752453715190015053735812914425897381532852204931230131764020518450609832462817336366918339730406188093155974592625306839062555399912946059741579310980107296705599186958436757747371195850789749891492727230937931225655477606208555094163657179983828221951 v140
add v141 v142
add 2 v143
shr v6 12502
land 42860344287450692837937001962400072422456192468221344297750015534814042044997444899727935152627834325103786916702125873007485811427692561743938310298794299215738271099296923941684298420249484567511816728612185899934327765069595070236662175784308251658284785910746168670641719326610497547348822672277502 v145
sub v146 21430172143725346418968500981200036211228096234110672148875007767407021022498722449863967576313917162551893458351062936503742905713846280871969155149397149607869135549648461970842149210124742283755908364306092949967163882534797535118331087892154125829142392955373084335320859663305248773674411336138754
sub 21430172143725346418968500981200036211228096234110672148875007767407021022498722449863967576313917162551893458351062936503742905713846280871969155149397149607869135549648461970842149210124742283755908364306092949967163882534797535118331087892154125829142392955373084335320859663305248773674411336138751 v146
add v147 v148
add 2 v149
app x1 2 v12 v18 v24 v30 v36 v42 v48 v54 v60 v66 v72 v78 v84 v90 v96 v102 v108 v114 v120 v126 v132 v138 v144 v150" [s, k]

/-- Width band 3484: the leading `2` and the 24 encoded coefficients after LCG state `s`, passed
straight to `k`. All 697 LCG words come from two lane packs (jump-ahead constants, 349 + 349
lanes of 128 bits); each coefficient is one shift, one mask and the encoding (`genLane3484C_eq`). -/
def genLane3484C (s : Nat) (k : Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Int) : Int :=
  natdag% "mul 2121116846648478518874445976242007998558899400974308163870775002945971815012422949925599693052585303364522650692645643793912543805903352044604140453013323255604077210308250913516407262018213828886307300901057424745823552770077009182588157826750248286483426211308676526241857390971131288112879626448471308761171861172589912073079933953990003704506971315284063890729807998193061275576469201652094623737601931172784934339796511343461266075650489392407856807714105717751777178636820722221205145583274169974277678353315483376196203077013237760940347643378607359734770519304865992572461201538231047734469668981725578311954358620001941282935570489614732304410656485780723570902510992258668951598351675146410659520997294515336975743227723877984112589759360513188605505807857128160039265429415937647639986434599874631481239996517835557561451176128628856438035090596817396112689921712392606539175373567928052822234851651914033000108027086782998630771665009767712834135433912597912750045523951092550263752159810547941518385987459410498194476602747913814025274753340110074660057304430932994181830172605403427368932225572179123935321922123352950622670769352564780977075016604402668890976490345560516823533237951200329787196824581140269717055536524783598713793007774169539646340263761990358341278359624483231066358460485433915540767402846718248975758718160338324599603802581390888037525559352194092621978227757798236335536868628776508153100618491699819781874997172153164805330657430084911206659014011805547946768113025262160834696503120249155935245714194382544594696041301909444604884254861025466667632390696827061911796760984765573349174510977849160042028240469091017272870556467700254815480192238421643150499146361983963164828061401269500262695298997410848682565702970830683078563285837082894456660456016216389105670736960092460094075063727276425875495405383424702489042540276432183873500262681716895319447518392174259094102535029847690097364865760563886861501281118340111512592279483471851718862243811517951493527447193598793174580179469477823038066412845218976261459397490253238220287059297804191816746090183537594797388386639695351663777204720511699280424015808075995167283541297830682781425133199883166738165261248525067470321006831493426120764556115318168358789006831634454831593658439512967619324445232033734217049092779130888173631769313009262193618733201019649686616843064961133491084254673320857270665184102687732608484156186539865670730293595580233499333823693215888983908663774973866498405720931182180689048470090022785242741453186773758495388900752091594595524728713770036077918679530726607207018050457922699375847208041146852907286671852036488759017604669866398627605411948327224945975382135084864284074168221837977551834657075415549580134441245727865741905846954230142361962326298274086911867982277863184705231788403725750772177695420364983839018221096482424696565150152847651651031482352042563874323281365006749446756038490043443797636070945255257509044595905327788277014690700156742729172501570015280528732276083941640909772776806138724835566237683109341312375723787856751787771396496770958826814865803942537415021178310021350564484583829480599328878410666597053072526153567452030143864242404568784981822247702950202422571729221842152983855657984711162165172096289312046558001923419050814646222246299996388722317764681004425940029047979606888649364390084448465279050886090496887973373457430912101865861097621693851429512715211150353218966465493247915640401825170705540609996883205273000556785199355245014563706113034976988771678933446281576632821098950395410658853292994848902359619743533824650423066410117951895593978047767149860398325056255919489460484985244595394006697895476140009276361284185804253362226692570479910377004010706977437613652391123655876932127581019921059622710461952793010024907528309438945734078406130368388253072659886409204560207536904142010085462845947509781296689482256528582460209950373405264825352019441537966949629362164604714745705208848016028867468433617909830073924707794021393299548302013895593461199785629316696116130189243146230381000253344824263771708450230448110878733388845293671395508632361612233888116640674678171965140559729582903124705970678875713546269196418833471553804379606628194165324381490768015590304095330994196393160006178679077088734466012330548582948523379117592194054259553616500486930496862628337966938822859591926603016181910844389249309017848369187662053870527708524352079511408615871234257788780651819073317054768020098618934329777070868306810125595929152192139510699865895469132806418995678795891023819653078931789061122558184673609920858144515581780448247644353076236589359806518574126169501406321732580905362045422709649438457065127527533453158764989998710710309766213083955536651737232924297012165202259373429086962685672323205363843211248120425643985833384687331025428912940923866622808836166872526983755283526701791656781728205601905051927980749622683400278386760562023746608912539941618039330139102350766565012242726896916451957432484689806480493106561066028748581187413228717841778375313349777293951094978042110934420028313435484358829248007912861658068436662733274062905048735973833508766379833726583101618938834637738763699052513108010849695731645488060132188369192250272444950130164651588849206071580946660651712118296605391518613856739176621893583477436531254448525410419305276891948525405987057493482020107595127699224375001592156327959684545023222973636036038341460146495198241633852350354005303095514362416153758043437193660137964137530335436199775336684696753305280262533306396209920684315292958277368619052365860757164931903792509056979471405117467278886265827540565315026512259497902417271327404129312090966877424911467894279654899704803729125156292312590085612863791213427051493585581052644275826209812202034698821348575535199258058581664864658734981189982871581228857995980185917280018502017859397330150571151605638260859279212899853329063088021457130278591099423384391932675179691060164417014012881853528997763276796676236085829796781614216922527450582526269118032782962981239809435241184244111601772450446907414423664391270517389730560033486678196847718760835938858308958157552652031590588300814630063398410477598860605767064044533080822543278580599904887229072682796955705946524031506616583263185101831008635631508913523925892484849323471397145289821655288691472819971264299604065803560867423974094009989406532400383547740860191215169844529566794487103148015797209984989555891580872000182384788621094991146387276506170318215231994667472508880467018231716191566216545130676386037442637430557679644470717625575566400220929798876095512163754864546411729933020712568013499834551861917132642602115424047707253939543715948771868951798891068062022934225781337400899349419522088058494954377754083535662831591492269805333339589281534538605595299329346987202790729056834884865941629161604904649450142830337037087067650643490212083938020709146408187833664704753989238842549925144493655410900163831544041912100697341702998857402765932258597497573047828605156169396575139278201386494569506629078160686337993014060782099395985755703800149459647907446846956749715652985062805054300418358257225181618099434355081559692891626271596703185294201473513542543288593711274612943319808576135723201467588156980378322328720511462494948541309176819946669321285235629932917773305567711664114218527922952922144315632606924972079149344140920329169366803804136720595095584134670845930345826043426404254625698165042719464298243078954848521163521016504603082689865365383894429949310602582161606294677885982105223901576869765450431202015734234192591554859548862279237069710489057569624771307118306520695253314477377579144592675141786062524879416114303245264818768670633194009426302928100118304991786065596715061492294496611497108894644061017544029330717404281696126862735559447677617049735668268267961345508666554480790366142738079252307653997860116773379862550110845653567376558362132317830201434597023475437212993273111271236546432510078348966562120055880151445316763062329516939255598418128606959882870166668330074119706437141388382055764257904043036173608847668899330748949158353236116724981275959993611774902664842675688702231359300570792431091768367519802216712611740179569917306987264002539844730023199311479935277891641588331667291356844859727926930998348193066383047613122792026079063359024026906153020155549836313481534010432320315279329760616549475549024073345874993132082239065649263713655852125091002483122066100514349822337982222657493042552207129013590863728143803435344572762309081382518799155618264214676982495021248978657079064974545353163757493554537769441100856067148859846631669829751450453315099563519203549698754500681394077926943962108953413764559104303135153874150658757698624476917360793748315375732948776708736259892410043766692636107433546457925969567408923685540748867524933880731222053306146358657936452202114584484040810038004885601746464874617911387542590034263741064214669165150454182448151551025360520398596249711645555004560090337167439290762840969515894843220026794757432384749611648701060030904830334721878822292535430162961610858080143023098852432129010184803630224995849579516881868764527234133512687781151536694839740219538057514916049255567087849746794258220932260749816956626806675388029806021293431329280758457073806596804746639020665024034991794238372029394517095959970830895553736946372378771186711163805284250345510955221723035686946860619326349958186819144347626094166654406627715515669820510600219726230606611918277283293114449324766341940855264547592427004057359758089517177541150463982164319390038656860885936923862129557842715030651532245920799665445600558995125333074081743996595197200180163712445973805205456501949402181368680426921255761207049010671052223613074436919197781591923864015978816078239855278519496252994512743234940128919448345945095780615043019024531639200983941284575474048532394453339525731977816891585151652565339138902458226758636687729709289789720225300089163371125392970754454148537089031840934785806865596902521155897022490260263119068730192342750963052369538321486864609674440023766941286308871266293446347332438189044544813846759946362908966708629067041662920171940652002682027373618168821233625908520709452109111465337642893029670047106850800834728793727705790206322461639288145226769306531273276867428958440114754750896117273286710817451752127946670932037805722234451659574069585465293216604987342765106327671095494268583655745706619870615484126434684932435406429322939980127191874960303034915340244627702116767300158195358708031773462610154755732671737936499223599576744573336013067332233882689238974582091026752318532159743287047197462709072229116882051627664276269787625051865771302112008500740080976760861143057393234579389361707954089795473460655935004354363958828756167072828254129282689573326243976161047873557614909052722673639828128591892388060933747545901929951882696756502668387390582404376354812277267169604595506652694589469982805934435568405885834312817354701439349047827950868963288882382240341805541668345685156946000496274369200360289017436228031973639422802768813144289203299985053106715142744915662825653080098010154144694044792324391118071322770918006932263075890132635972007238056744366654154729537880118731854124954146388367587092422003277450186071884701419282585229329081020336538895810364142114159670370144149484839417636712356008214987913501615532178172173411441992863766337313870259546385478961892565768451599313016277020566289087757530671595762814134121712063379295600156766634372494163349719774699493565184599030245389069668902846362102073414964720511982120156340267784278558368766618723661228586700410335298897820687296961000441853248121648450026875610535061740036218860509488721660482974198423684731129059876602449982680716148679041304733926769891300552433603508473506323821373676164730441300213003241772769312037705988046441794958753825079681616920984645338572415450853033545897121210152248707900397967940505756176032421434849053941247289429293934668284331905958469818383740489356960949144499281239386264853314712646124861839405863535316497342517276182559639589507527545018795072717402480200886116623166885065360095310990987602130815764958653356934598491952409809090849026699831884006216540650827074343427256485545427751593900445715389235787070963557144282290747945698912786249744665916590467882028485130296930286671291328544916749004349657578300778606267183036829135890091690298133530161731955228990109413704653894303648567472011513138062196431308325862433311759336260531756263654788307874116807990861971071743038050062312649591627287049741088813645832294120892440264349789254785044602893438031820733847899050397242289622447651216965735171813815391051803235397241586308356549247240654398195366934441176747360928647741087199761377686284259030954781851482343425140112447474304779422941540208159692805887190482654992866536550320710340754559938143757970252195753346852944865428229373093207897653521971001471062076126696483236154029202677467836407910090302098528077028765350135097720078069474379880517643962124203335865729786271963371272783207240179415488550113218460477456117733191463504282743469954893461037088744909549262741255113878552615921546449153416013744761644533133033938603519954452405265266183807169247244407065965761473956094066416760264777721681705448591688097488365871663715689141798081768094546587925535902673147909051113541511003996764406972116761441206273 x0
add 1258230977666966965929981694040201080272219434282088899211835471749428102473008492789904282326302232678417128378948599965562089713413742511186208480284550706393735911264655167804627732940960099845710512518802696555028424888843650248860749872083138953225131368598045823888814532747705924266699733998703103576925291518879518613255474191946290106370327007160469803235140485560241252318707786682480899552037555091671118818865052236622672425141290961174934387077373194344159875488052062144626256231402619819974676765549205358910742557549513948099215009500174475177884833686658372586224856061693255347877823240955471456426146788451838493737423185146061927420786062292055790985762089018320449561890924620730945795801513881016238703148969211780040284519086230446148490348135696853778787794698164063446702972835020740712349490083335202399339714325898416634646349463523301031676139494026006927520074729919745011745412596227646864906609916511960391044811558815722830216021265439572945537050403566799518130989215293440433724346425874569627522384782197411927588433013462474019403771865841316935655752520035610799931031763054986047424055257032844335722507917671291957224930876477662692803819818705113155697623366763630096470938603713537504115740126929873424511601212682510528604721941347561274783472008754588488932186206973040527394293294059903934777547888998241671681618419547867361999097072070810498718404765566712280069895227196466309847339634143277650943370980479058589367278198696158806981934474773975172167272810432317569275893499269944093357153942061348735624515976579039185882803909226354641594927539477048653776012996391225536017208594203217837891186518044403365640122818003059823354879523149490812631771168426911206601358067611138648214615742236345188256591234142862201951002376032826702482387617762631679951889558156102138064256896946535421082459042138467298187029293913060704321873852020252663693432043184052085018944793616378035050989134827222929403939743086164724775858592810791728078925657129271405840447186492987386087508804955080227990001251407838084600704752477659661375419633737108187105366086150133768503450380381405534133048292031459091827496606416649293756695678032946663034302495032230601078079327825908233002863924923142782208642976901625861787301911348077442063719182935967792899483908908887327536332987616791956321969062397804222342175570378377002275805219028373582433014812223344749514035357245285741568789267540839800809827528410909626456531188797607198457572795771271110463994114774504739220532853295736629241120980642372691501928845513411220101372773619750693902092664314537878430355234680787214818983469952228838889098848556400211094515638578022230151014394167212941547667346184793976206428766456042524849826645333283801517045439146277784142939009656419544305504146865565457831769640726109853634410500571366044012636519250622658201167149724695629089235818334319297212476722784636946613163559505856548010067310254259103769947918026568234441167375877558529913323087320505738092511638735418457570723644104515532379805126917352000910559047246426441333686665390125251948403213762074651831230437493470040604554932837562718624756408981204737951516569503960670790148700073463260464303879668123443872386299957777812902640976354951383066394178728299014555118981206735512549015296272598666567717830169846691105284099843169141714335470039997965146524065654769567025132597636729010310108472408255573483411005434655021171831193316633853810529081953003928103748068762534521803233655673596841746336748727221174676652596630151540912938203807473281338836327023456508195755183866730092900373147887968657232038665293501536927571263079002833199386852793177342247062653220927137937179817706989859101341686667888498551358124537431633315249641173312914652150150905117820708349419894528937272952017283618603528561764789641662711450175970056872168299181938240478676696922277769554861884392150201792031573654078552791778398926932652497605600888518717646901232955556140926791047060773308201596528922723885926426717365753638621865285962906570463622188011721679126712358873785310288950843177987189018162591513886605706944017203520599555404183880697668113782758428740251029265716393543050924095033689292116087195383615827680975212662579356212938415473742933423533163480478717232006338111293099608331555545002608812813122557733824064911961492157677969746084430541242524883272366907631750166941749921267223338458331442078910021221859053504834467184731997598611999929097463240561677380477355858943049369260889117935280265226336923337287226985740129498028298518041911737408839109381987081876222313967269110944290127907807251226300294491467063146048388382923708357346197205269760754681429858069055817018571126186893993203661043524590467992824390366742258754470358878708097104665640126852026366805376014764884550146195479219238646373470085708970334631474076119888194842530918434498115826100625170898538751337350676117103436274092761592246441896484861739252933201752424820188878904460497968541288983480186067383017295521167390839278954971420986513302784978437026356106371224185834534107467405438205464759751271567795153485350532805942144172453286445901776736546688711961699096517631250858948306297873518944572355522192056385694482175109262024962633959120772279439409038852783143513778297412379624304203507131423098911404054490163852757162171554189719397986162474223102867468475906548818582286338004984884926982121323541182836835247033492018312915589535551427686319432746843561974415821109056614682586275483195603168076396493686035348364275422771112816615956889094765995122182978272580738029116473268998365867262020571487431579331411189664564616967161064056806428885867786946058408361303568236824619093235607151229944117169184600733293437682418211123104168499384205627327711756578341442941175959368373177919214719573702253172760442038270961032246291796856050480030964329726885934778159864089993537163763551898874326425933703231243835129189808665669389715608659945392371813830626579850452902546522586808733196509408641921163061572501367474686753547050709092607882284905965321731328089954414785966942906745524731834105290869449077902493488692275173476164341858520368092761419914656143436243952316666256159839491402659004091208028508855126748222213971428985027066151899676502407276708261852805520441262386842854918701728903942448551803281042706158828555502540456725574803221156791216992199843099654877181216586238121489888615916869610311300449982511711699564081240698284316218548769235169425273882441084575033716576196624077387559695116139816199448043928044396316188057343101009774203910474013256219470479596853058754306837792774292950211184457814031992842052377820014991324476131962307189172966431015667452735233915999246316767614008302520194211332410791724798188924970453494939183889918146344968640720281025897291012433581514798241278544630811236151604702218072839909953470108421086190147976584560256219474477595080192563366922791286569583876275146013853079901632337982350184516818607945118904510612638428236730814709183522421063737986841391937750158202531477739543729083352899171558321390633476503132089271199551084202934003585100177294239111415175241143659943821646678970367543395033315403731330277097666051856465694238067151976414495808530655005728101800823432395988278103940202001177077748170235178349562086942423968100197259231244745517419339975511410506161288996083689191398371252094007758021678200550881003012967660320004798480497406985923201856792035607821931808912888934116835740512199720110758127796819438921551987827012956947961938883156639671111768649385030653444805279230658383471168966476036717612858919921884126178567334376898401075127854233789653235799433278915300088793197484027303836171759698192582584580353789281358366218273355520794637224096457042653421253318945587384351320261300542719922623708078526464303086084721809959126729183348360218422738475253519514784790983659943139490325185332705543214714424682740416719470196351868862469789202478957292530209866533250144838051850633062896723242428687296447818385485134331462992138987061635252819630844942616261189108719995157536944837142127709934000158918554058069946256148722744852194122204032481578172557302321286045920610998200902668020134026233439075144285448570300426319143287408978029675891449212400785658897319012209433351465102255738618010111490093245413426062539703740442845593160508287341235294203952719127225101236686530205437420741273590228551665825913032913908690106342902121943101662737187916980730940533195706965211300011048604592055596770722089898973835809095763262165209506678156791533842415138675455785143311275126277034455581176018348886509397358582904343441127682138420717865582085780985960376384181836758556565256205426965137850634569034515841461253538624608510914172385443913140494791921113812876282663317317211927803698877098180922721257192837342710902906059270759836217450005717811334416303632860613305568743162336883977711257978675462005316029724966988480590327500622445696696224116029347917566611718216634452995652192150798213975560563806607085901452231312892833535882887406732917790701973816346045829389976460113497378570733166839055462081835505471571010622254439054269684610923968840539836965679654378631274674176797723447734828451627734378842664189467701650839523676268330975762567706611413951604541736494073063854808989312033573685529625733880047054365850368384657467913574916874992358441402488048364117408783172473333556670528087682701218813614050292843605436148006441814369285294620301188929708514356746700833200283006728587431686717731012698977891432537559543330495266740810624250347175209516616904188658368609823591075231562500924121877265815082110108843015562772342004348761623263050302104879604842803366927630748373336529109258156708867013025817570593379325939925400120352705988036785667892571167592092388672216492173395553371447413140156880591042418991791335600915651455089265376147073273216664522176339172802161992430156135616823386716951717601667057302534418441925552977190990884864317760930775300208429813480331654053821912869234320789064940151432168749006416225469774957229793009737721245207915023084756747649599455412273068820012561811229540649745426008385612224778611671220574025391570491945694520570767340827823947045736748513723668815512406240429118289214998563850260560979357129919974215708231174463440723736109326785299709847624537068220126503223195380594239208343951773687631948456852805973022775027068894230565938859328779883965902070918604208259693839283692671873387722746566356283048442525497846347281273471138056478650064633669004427625998411725263747579413685212922541256889790854314983383878533155233355600251819840742081236715507517124783723569641167338077343006302751200773395697949662455058781944505394641479482201340356874195136908180993087051484912768541305480998903271336929486627994344951384949159193035043225618450815386305446863298944025405001737072887765015638409975419185211162884408167612654734936561878089280026868262219241789679775397074991512893951991259721426322437555901404657475001290427743215367031837706359957934556330230176706245499394971227564109570058215039731279208033353023084858653848572178054857583461060770894656642476913917008632018887348458759820619604869703661410650402867105301886741222831324088612659973798744865959647518615659042337034985198755847360586101947229943129018524422692011675942515297238164672327129600277269402005798383759082555809031357132035375547033931831792270585778019402474993607201881432069704404165248082149278980257409562705169592755601041271662191065220476569512482244306255276690480311369121700211581897768631229451997497885972262335813430147992921345393683753913056227117454468863612864428705779384125777598555220514207034619819822679964927096044128502219460255138784015452506686788178468190837731732421119941920830623622232861829606727205031046976376531727772084398179638946753492204536118252009561031854166097001824843806767818785871114122435434054910435308508331674359419470949776782249845488023572915419611869174801278836319080762426339391654055865829870545943312177532161249703384881674617209450292662998182697891815200580204470908128377813216679517795489233598120308652655660512114440361749648934529073849361543741496752349388549879068658442076497288545690220305951937974131660571489702557087360677960639688152519329621322065039445454495425960467567323160965715389996352326383248445772308638152444603301974546806949509344661326249845228930041834193666674237490341705715827108826074449788688955807409701807637219224018327976321496343949813355897963809583430965295412187044292448328219896756173824520678610517641293965589819622083543071384941406547270760688081832106774165770361355024923738011468432748935896043728127085657121966218734170984106330107452830473031179695285752321973656749516258348812822390990051954320611948128378422536668287223955280486898923727084933984609344360502710738908116704474303021367016017809185754157568937639694314889955100679271514059075569960962422036460205683017684308786513082029742302458034009379085298243384288186905002274911210013659576109355138459366054597612916337139529430462426409974285024807037108349141289198477262883456506407075116766316294355635101160350645351263886449194941418496728266082589821178288453724388645081806379239260060556400113892303097369776095453205364792917707283824348040257776149577129515300688082506008206104147678892206343816869384285371696451715287500531096705413417818875938465856528634491299900380151808 v0
land 2218434338159452648475483014898557325427284724011138620348309671855837222606798977064407712001870760443194910181558066069322591785164898039629221009444483391508260975665131612416730415060488543929443841731811459241898171828604363046255018662200533505001155332033306564159460408654394423845444826149637669905881491529862088531996153688923793024065906434972406529131306794432094496747541364663280656220024256370145641266770861604260970636644709831451831342060616460646667682188814477783611849860243704901479810942644197918556405943067871585548776616280521976410992062363799860178484715906091795861838624949858004403051655174271984670720942587081340527807631678573354086536458007287313477983103986689799477156187874355178559641673253630363892398422771933777865921611498406170507886804345420116994391742591539526186298532614759737293573672606834048113415229595330266493246071341593026018881464582569939932107020298049933372684044423465230979981312765324918481577842929243530815685673466929660413190869958303916571989935102182217340157475466635340163466428079824898263039309899239474501745799168945866046445959443542292055519653162822682981068379452192569050594295269738826751742321021144457256162315538686320336196082770917581989188719938929728629995343056980872996760184494921994045794391402860060308709984856240196118269120006992072133108138307614246596656825737309808875214975838992097427766142595224745445598943060700044521311327296403471984109966283737817788319047417791563946918576469147781247311125655235248382046821255837303112495355327154110851533735933359831418020426622310011833634983858742090539417425030757574401575067663905160751416488759714355789147024614238746628241857540815393706323733689585982028346060032674215255964233302779299427147701490192852159180347410055725453540626485139950600779160466619027547143483543933162851366184373162928954745695408023353193886239443730847386605027274431754625074133557764900163097772931792211623810633501527857043188486258131024028129479443705197625635103510788152081588726378456823223105312836132892272509254723396204540302464580782064666967393544315272018978383608409334095182129410269553708718246234480067446130839437813972806189703042590365473231755887881355663851750994762083434644277864315595847876414085306585593690452163819554627855691741799397852171530452586182399974742886839274283145756983174510251885259006500882184755723683471494707752026731641469197772558425925485445004107834754653108747382339992005751498927209030241650297474601543029244251591581151080792907012531668324936046179885405003224566516765181955987655530285050768091047248736308276332691095990552454163330224829781225458517299090493512243107716797577176944534086465922602891597504092763524097222188043585200784473103482300553177603761079748251684232378321175465179530936470898641387382718736107767338015977824071129777552585715509312185380670644154582186737901283017878468572946822892408169838753029320231056230469615187920198833716716787192872469993513611375085742899147199615129821906822078858474706552381580291188226068971070971705879407691712579578989660177440439482887870644111545029803945474457170709030625857160803493239025662613547050377819198939210736578597278108429272285344981255352891554014263586477929911357524310031487704988037748506883554576400685534867891862616827624386530741763381900019066554568485444155558750248801550906457607047553193568679467179548164199568468767348077554798316980968862596653707028595374906889221216083159934098481929049217777961735228623975638037815173885711893189132212423237670223059267052809454978761970543372096208998882903214099612789378176689515134635197362857361392789181749910156863879955306976059547543620510669080814302493537010694919432278881553126212384484605275463375890580716571697848400721210541665348754446190543947782414070634133448683069862916101488044066200713227611679035870443654747185541478815545338232953322799476722644427094594687491452203389676964679428804514349992509499718097284560185853990615308140040097798016355699909495737391423327698866896755581582623942715871449743127983937448262802304929485967864451702928433965458673710634709124670852129937109330371889674054614492429577299035155514928201808429173438250010774237007272439850205669291121221573101503124030837563488190382320237947177691186783970550849146450331068529077164167460841694860804956701449379627836371464001148666993815906272905211411952100534098756704896125179873053720280440120346809795680525161107634966636013656734589928285556194481387922523111468558937596903483152766559443036399806625351437535791961338848137845905853448188985958493784871041145823205550329644283742672275220606282411135760903825392521109141210836800712121224580307699438552638150259930156656998172982183610061573671420206871908374531449429339781077707922259028918218178485140669763460608023997336107801606684222975377770037882361656470770351450599615515494914067542131017590753194495430019361145731027104669146319326199191635804459627262724818013419979865278371659402760659948928184188173810771622188346728720549362396805452104389479124997974217215472008991378661638272002374731178119327559766319620703370507849300805733392005266936425737269146503353638307016804808926271161842405381106331320491854337703848010666841492802841275524717157227310076255449239122892303509943901909774620944762107353503473522370210325993509315151376515062525456030494142986698869018371039206643193519223188847058939199419214850234140511497291850576470720917535177173901108820626121602840852467425235392318103727670646786775349550701880622010779412350937112775433251827503529138883009004325302958297184606638530384927226693920095465813385427042484083919943516174463566428576624056397104772719652205529110236598621766279510315130195462130198774306059594328315212016005443975161740188423895242028080912572147437431014575506344290219516211609277360178158740348626018854633787358588035616002248936248286463610083770370440056167807296569753717348540702363623658971841342187193306677500685310539084502868745337311062066417589130739091528795519665605637445697800996793071877928254893329168022388085225746015400007716236615743069102747614932868534886693365117590494615868601323251721080081856665314073768295765997868189106797435050080969633098140322926496882127843732213650291880834536958920920163385539900944971152900626310489672818709237442375067296669422121700323880161048004165090694566618467967741697818346821759273396465022070829634825899846640431208717793244009520017389365246522862976756363674742846014691707537882975026508786662738550127201785981129462381579750276214281420659332822968637970974721922624494725226084642272861726614038000343540303123281756919415971410434833855426984918630647035460033898184302196600565297353121074079666471557771929341025666841299910587932406900708515460287157917851786368836405758368589340120948217989380734304124821068697167532985749663046524136135341103014037879421778395717186513454149384512922622636952359952611549326488342543150562054181936949122062862940535710578159475986180431639162737186309019221192110077992257795060493502860588929550584484036834708074660844441234022993615336480266391317175853670825332169487276079669505238344298156361789261022657480608380900500724657809550298159532602246852862336286706630526164108208465146456632272095359375450640962649560298074587831003355999575663514036834590527503888863918535666558396085968298591167077998893586771526009043650252376069924790371179173455313906414138611942984411547644219044189280897906796000421983422065823604097424189463795728804527436774298035297940257614259051220162272624645896868434113179492714263225717249823252201115566424229106293558793571381418262055557073432890947032992355514175736674714063723367409528076217567413266390580572771480427807410383137663252843585794475469723502980666233386356454860262758751834917942044968486247908483691269920051345476868739640374027019618981134743208499141539686743132660719822140481042875902779187842193955071026210071848835933391780120607280933830202801848946195000741785484301398790733054845895427871341807474414988540411138792147902776072369784910660181185355523641441029369670360678626985556056024281165447997674998995531872968045918926544123061286907444882802393260559423415795709828255277954931433547092106143325531058384092376007778423398811266392885092723197776698236596402557307626172371624794141322042689266369591385594342128593582418213598725239560888428539935062505732517458556449442553468038166870315962137983714885852652375421844324584358361898342295566181567657477969469189827448141577997114483075118389003062107701653335752105176886421273373519466015579596929827079724141646872835638797611012895179474305912954307270803625070165759145865130635416944541470127427817001816242148311245436908243700602944114487493656216478408801213490749678274322701616748011846375050500528011889042401341094316688006003507625145289970874453306695227908018450704846934674411071903175308723986033247883190957952046913561981116095905897303178803224322508677914540402297747298028043980497720274628962128350516924068226551398996744193544693468605848025029275905684157998304251441569384329051358736958177198968734043820718922597657248737385827209361035420911340578448275101458414234835449304822003075751927734775395764748655067918787731051250297607066990265991591433175801554627818524773033704270079953965875524397684834008295253550909882914813260233292867483545547059771824897289692137989521350739022821885762965191017566901861296956610100113738685120444492807922650625686753115259712228188046992642516929981617045643359354007283297534832756198360848709086881982460028224924460638917981258420148193765577636950700852727067832961555298400802782038491275661010318008368199969581575519712466315687810244583635669409944336175560153892952077089222704182102559426278323913958005969347673982786250742303491640245514853410540341515741584556611720443485473452755773878375775692970408256645104384188054838861875452289679405146719022221930196257578420829548578203107378696715956330100170432384914419469955337802752034704703409665233579723902852890425234287260492123227004142561307198281381205632999822981579193322139790635712749372728981593027175462322533378453345546613596168253396437273424250290162011995373060187001649382661522014742241697468435869801691091182723733897054356006439241302256872997545734040860226278108933375444156717976310895402775197623579400226925810127311868341679183036627236607584094279143579468555169414318433374687506332013250804517448075600501283563151824901678090428928691080756662718952711732254764135792220421113234233827816697446712747098462324365960649668000447094238638432904914562275652793118344927104138501192311212919833102297186429459439821542748599180872644343807649895381581190310271730540315422325032982443975317704894145238459790383463946923254413432598927395946574571097096340277755742634902907503282071024596228735326428614876529832331647341983159478111270031159339706488897023895037812635248779100639814525642629672891710024430346068350688947379518027794238479246223179428481311573224660158015458614086758148690672593711461254954053189581718514631695357189578852692953644804909936983958520244133133404216174208151102197446990504298533143702085046985209851407994060526011936911433879225484375217851068791364024570776876459750679353540454877468805644806708757317509672130427862079197146064199141912189432580050922480951259277915334336197591524056730064984916013311268725319363213354533763287059886160662765574984526722448529263499779022092026642307877828679759421512675794616791432090827280859948268483894971398892470353049954827708176028840965830205802070703519999054907179072752161227980494756276324914465505777436329629343228999462468068483319255056113429216714048367043950975670561677368207372600031820845334148752699626895527506183877456894597918515729716377031305998463759939428541389618657709709518791089538182558713313408700013966977126450036534878878742687048982208640504894591202657972461771315418084665648099992323583270874932865707045886802414813906705485293469276268952912607133915628587519144276493755623202764899289271421418147869627770303322942695650055144335256941826608939302237334138433981554890582947537460336806718684941173296299441846014681241141868458941933295767329347957306991121800503582942930903524962768432138316750220267051341635910300707950223908424391626028597974874329375860541038415342480366738516586744334022473683040094257187135305056614655436975309520340411809525752388359998603498839213338838997809581063395767193733005560655900914507034268967265295663349753885351387386288304711070898414023632547106397746412202058506172307436342434604724597628193153569625757648347215675866352221494490103802334330901044926589654695719818534315026452505380405793543102701648267206410204300174730987262418185825687462271949721657272916309412120410984067708877404200781888735427926920099531527909000938117325776043986863793354065790216040783805103301743487033869096972735819858123946604166691176806145513701773396372287946998249989603060929752337311947322228035133683080476911862761923107586114901330364288759328081608619405146235153020477998846637747701306916148423084330143219794406939845737747260941605038648153456662700521774561222052113486368824977363866840230239094068613509581605581227689657546377024630552743547220318817209579959106738342589360004995129916748431705168721970765011809313494472120467375582416598826364174335 v1
mul 29059475470886342727072394662537015443415837932532522019992795048570535673991372291740869301352025624490023718319031901030127225874985278466901826986531803193449816689197447066895144956561739115662067631909966972454684658736456801399191738465960445482181222157254599827363462526513758604521606017213528440996506625889215325848975759143849855971894381899709436133898331580118873290676975792209469016372197069008698959261063988645377322945783332517531235288399222033717847408576559923469366756714731007916961165570851792520680094194357284821407245796407842538498171849498444467555508303713929339803911308078161914172467850179357580292592306033841888364956708823893017188631362059347565237978043256206632804951378406774228073596566822742712430856836183145723303795877398787490349438894850254570955724294603360666544333134618886167485343292715888724885166392288519429750123734250996565742333841339089206904111059583206657230265286489418543105026430728884077601537492702279029942139623417534666648271109007336903177739168604965054879671931384482795042036614476080466596224142679654437618946361832204841627784600887490134692779777107130568358461236614275843912940607622622220290319445482285887766326926697028596686232773745006152046613188903291002824734348578172953518576610793232240181801776767143120445732635506487039732826067931350869483373587837491650503016822228999010029054934122765141928556409799387975590410326692270711831183750208916619753607467969676543694779096907417401015426557465706558113551458673237424869965815798175938765471486829236399888597321749421281103428608116619791296638574721848248350492068375301221685195967432962167925258604138084737845309872519433040183831913704389260456381658936498118269321238173888280829484684652175395826714608619335951041646106218737190141424212960320237327561827159262927177145814156417379435654091733027728514427671837638779287716352071340552843190686750066917759957600543343876865259495539687303161976202224081819291613265484170478289917723991002995466142246957065083156516916090868026030847459324786546841615328638374021031784905666613605462999457366281788056276869842774309505909985006573163146299517320324434207670267625160159955266892354958360690075099889073627520641981821549720482553578868892866833822059971268880999547208198954741951070001721292522040419710126074381788576801330278088887634660066522983984606152338998861788260347277587674520855313509003119866800730036523100365644448852523149777505288291369011843188870709470262526439941439374328998568488419014122843384645816235197120760684264454063906949456095550890498096683123708228792221198862538777816859964063270685719370060101217528439202755689897375128559096469620339132761449248617869003567963485483309351373938095028833844300649976809112254761082802896284680030502603474383607392260285405917063234913251078816560886592964608430573931551748099890894110207880363812311760531382766333815063800936215956367859721831783927398819919397223267820446019991245805679943828346860161514661290359079583172402432893453801697813746410531017317343340230053927361256724859417231864714101686260461769223512456542920553529699091327890350686735013098496440318892966506441113779687151730629993654742760958859791190688781871752952628459158512465103156919811776975648668827767700619209372984549752825739805230785233792072905573271612884419597070279770497740143982597642183567417420227018343310546338326815953047044849581851172151705035346643018164496155929729444720837405869248196595626899633611208291431377390678211934852017486679230621172846148906830939313602736923598781871996877830147652602093995074579032783829464543641559900846881507671655989728597104287908892272562409976529016305944357065357055923232283068401354014239559811798770504932271195071639250713408888641138992932550167479281536208483787229155980974390463606589140988068482181661435840628683494067628555447905943025500502843907211533573408906293830442992380364767639966245516314118449528031741627256868192113019717800048850023328300920377722276476436807260418051888851638785310290733077839746245298861689405435243335769845605238209989423825520500816383928146932253241735187442113210036326382000453336351570445421610528230307462231295342473221550564773724000095103488558996919278042352037581339065105744524974586139085707976140264755971880699508837006363758599559289413704674990704601477548179563677308260680047842441900476919653333846235472065149543961708044793170967749959194343708664135750820981096053682122329111410317213966935581541887963331977142604676623471757425772197140747352271338847461875875710947436296172722535628372446605385134961258086095995826157123176838157645262000608540366208923184965705615278486269336819694915135770537091013418153824199541828064853096381782750806023904295733853586964319461982567065111978842485837002525800659228441543678123997128733335178965183834926581317004386014859449059867796186474492859767501269447808295307980015329293765704181495185257956967648528427740358845617924211622505188133843453956268514957869556120889363207519058473134055246343229888300200148703102451471633090638726403191750770645875310448069273658523207811701964525659198983297204385451605301050812232442643099926900417273101609266291569971839912484368135553369063486084278467374026815772065740438677249834827124602196214418511527028840523242417747794477369867476402011249514473423023670038518520255403222139650661096236223735899733351669258481374608524393407973898429044675639380455621839985483523293566035584002239690844031867864520071452585894981060593416716291515820413863863874653517826054614883219947026192834250507378999080848677558751692743550719984969035172899703359259286770890965550835836425228249297631197050936265141911953055346548272316705768952036671538467126860528050472005777903146897180911512727550917144037231350628344327745158133735065636217660787540102488423282738542177478856539251681278311714508940527951301308385293607761749208357132134967087231009449323426381615752165428087063626175617959495814756599139361089921540593357560193295035176843286408628032668020837263823100346074011681933069746261000785473737935602233283026657929305072679712097412322638470694283683240814435863211555010131990776913650213836603406094228717239090142212524248530548144222932058528597836666297025355836070163261057722365558316163778208276501149786616199974699365718467830185385742181632878525096708823354365322231929579079164474020227425639732047600973422980628957224946343962510583501807052481218580578449453331088617715057374013527562000105194104651646220871589582579155756657478269488611312155799392744943576789767128075068649312459420088947828937249667357687049362876512144073367032675351124843211726716447746823404512427924607342229355480620130679451750823443332195939695250943791760621130146417276048784897143410664268924291059461625451121453672193561477278727341938413098637737299206866820402933846381483134541987262478440572494436042585832747747915559876014876840169601476833101593307989826106626758184347857377077236123645440781165876093461912289328095352839683340118355352307017508053477914857309879123821205439947837951337130878105167341128061915593338761178624842576761196844072023035929762536288735771154290638638682213528376129643348980665661855069650844481136240418509656304027355080422795763002678227575542319797502586477058573922903231793793786049263469733083509660722749105917460816972029637040318983627675807832361898815344355322188329981866836697661507525344882685231490942417316024971791647857478588954113853301481827239236064000034209790080998487595928802600888849159710412364967618500283654571959124609574145937441502428062421193537937668334832459953730490697300562723526614846796288126701414965817593677755888539307834676745975154466719583049295389751436000721880415279170547288182760578271997388631342589926231375405986114533943725966529066854771329430797158065657514460448551623445590963353988832082479300345893309201392716147250876867317631837845359961357727559853769545037473325022945888048812642406137406508733085502020029615623002052004177932027549539106928967137246361104370266335262810259715964082299147188598825384606435819511832588608025274055411653087910540885921744532523984899247450494520532453910095247744682547580881951260807057806724397042640454385444907993212079067975041078482342553090380615602838839700634191782152401252784601380197677792159133075005422810755525459593379067599645528788299240598302795792991422269634327130605619570391487956597811177660259129143375574999847625099328732635259259143641624913319373268410702756982997227640751337969025909313677013332956380660718460489692423492461890637368840634692131502749180635646159996413832066725536670983750136951321486374067103320523221648386725448426866926863358007222111017081532836069149389853744565331234499464391125853724293766318986450950071696821734504101256299939108136964333333793021827309753240144964575224650017148913150559472431655531384813388493826184378105360805426917697279770795188139909273391548701963764065649199016985373555424081777871251590957667322086614330842176220135792091078545482165410013932150064015559525743125230635426471217844580871939666984138949157746940990601688465085401884788384544009967332014759395480984506760305176064294811647688996007910811066379536795924042043580963634677725370351759850841483315509342007134334564775236833987184459089658908004414044360968603874379461339387150840960004012287573664841108298977929767582130369572667132204735045077404600082849161521751571424615394003759464668784706599574136452610430231886518823350565464901790194080038158295863829523856008886409528781076315406929853481698297954534020729343517713292323716637019935620924078722981628702521642891396489304551127808814094325912237302064296641896696417096616083380608721523215116386398713745207545687428824146785376880965025576389136552157049042680631416857146586054362612470936278306030257868767518040805848292903061012055370282025285156883054382936859891506064819161503100448769483808876813846683587143086042906523344447640068549435957141829616417671017862070338801733090096128074314082508785766858284314461661461694370752467960321085324356378156939249126687363671994267941398330177399496214927644482708144433496720219096959156150623720858919317649814251007709254459486953939979971068930984668792438968451532353721398840881621489427679835968082212699499514912145078513666586556504823366354552277396078449097951931988670846946322164143905391848233462620804872151856389775863880957663084482290191801662783016332751214980501293241042726577428973080126964152296384899625981165375685382294730629131630292357669485936275081341664830131812745978663187750368944723998502208540645882987525290997679097606817001795819848398100164878542831720313114649080837374654771657777783741323524185190133876281826014750620620107159222279031615454368829713688595341341291443763262979398222724166654837318151944208905074697324398717797072622634681681605239190486388674709221141865704367474292084687508611591889954263907693690053633605101905694130944763910026784659653370432713148987332738633023530796531625281466852756797638296790696717288592659025633504225960499942763099754530802516589935428251577539852584952002287750036279386251404528822464754206960455233287259201550473721525361219268089460723402808824331837737196118271354324829379762994608994239761054533413857500654853336096202912155663521963153133251286666103955423109536474521023523545758443420136656640395474425746825242676012351254477783256932065894711925670111423383800684081731024981441899549134445862602437835391474969151026154868821073541016157198208932052390096329000250779937440413951637346157496040611252584543783354999098983318338334979829575178339344604232993650999882469274990662339576078352173789696718260528175314580587428436348075319863764147168157484286085211226731462621709695733274443313813384576222700345545382842934527248879523921608133792024455859570546479031580535800971400533449229310509093589056062550455126176037361408588612864062402082031802226195743859075534915084146195000316510775223242850348506376243949570443516238360562475616175396080941959243739524865703004154846571096303820720961082691739994974880737625481661465579420621677775530473939376706473048658172730827716902150609014316688379283075922738190624332431039318758296966103699930046430541800696323350768924126645256867146988881758078855458003499251396988964294459113633877372958125781238463887274796119066257290114122633097324648538986376957449116486442155137114479721472074269560223212870743120466417900299408390248106315698174292439974221548124250478038105648306966783204749161561295090040359758119398647744078104424622751463766168023596261775782810194375560511501910770021686073203009943127361328290862515032121426102081242444333237415121641530389139773574343901224353451281937592151956570319015191324527111712357676667336008724444528526822062870714661042678724636432240149492815859949785865749376988779352330515856249452137967213781316892598458493656649458588194224296942135641485818906482852263424248015130013218156906256922849909638271665006776898466270389532127661330911622887283944535690047037617671955229918163976072551755284347892185396199649206327321630344753973341799215401334592443990249143916739639951831739172327366719871542503720606826590026018920935652660542056261584126795704358587238499855571468324143418512040724235044111961508832889658405972386120857996719647632056869308059350333757336248849268899540698090438656 x0
add 35542770974829167831616795900662420876596121520887344109778830586860544959806843044752247264169537522410327945622298545856550915641033999622082709794722962345528272744409620897009776437352004804389991449741629594918454673908910473839948932939751992660853372831134840822331512154999701670967440161854199124355669914306292380721687555678241708505931748564912055491593736234353257773713658134358605346572088649415457127245943928265591894110445536522494350160747014833116825974561146314063618434554783020667883678852708054332658471787364854537022782199693297612307604751567198593106735275959162963409275308217978699755073724715613280873154461682461786872105904595354870669435567275598266561975021555915831775697093161348336186396448589161866611121124195627653064990054307259339486274482614819186064245251639119582704958045985195091805992578535196166942968040626157128916792732617228799912174168970845872541605300959449112900212352365010101318226724581280789132003361335291159211482131304048003244318937507768077150537953123878575074691897063924160576658378534339532605124016967834637394681883040246316781780128819010045077434407727013549130948828146254320692826489289580420905157839600650848409495804571868538171611654720618100147110474908269604679516180755896879937053559341167815863098981043739979416613877461956086305264721434256294462980605081705884508880943245594489987965138310011934075671317511041670434842502239809053382027035297563486697332949705111156383861028890854947687206333504159630351495378199386839181646484125971619376704178382781795198941880966014566656706989244005487554675964141860298310142680038816083173385013023161200946732312752434130934520815960613881744391511570209817230068138913227993281149852355920310968171266211420139739111582513197339859770998511343901381565001809233785859463438614905436660445055088999437379394938364760283348526678045350753975584017912342613733337200218933930903665640660212841514868324091645477656157562551185306215059085412478962001603086443643654704836942714979901014211410974074055234021626224101285413253562858236054512391027838633653423613375388674609576984396661418914231318284911370690787361611486778237662535855559979964630435994755377218278106875063105757292687631514673037605662424131796166413055317123016611117547253270865614465926561923218017271279933814824112960420859590836016144214107339393562672778550531882410603018138229077187166114355636371309260833735869816080884427441445804397874928267844598674615684790263893306572677398940890973848244909713128840726844105966833492712798512486360569964735353452850304463635099390168171739585791023724186776547516005808441174007536546887700716135378393377426998015043696468513147335678624430460963471086644545473614620716287573225558705909407212419457600060231537661443653612545784694699818462228375226525919676488243079246613365416395291222105900061272021717311898652668582317408565635091253461050809988182827773805265015726540424902935446472134879068517496401045077378528466110104032191682734890933647299149324734767369717516086222198933793417628074548476347202841904876178704831217076772608729981197420500067488382542461125256346330536443644693383565618352831547484023763748319022094999695760965294601098546374680422519903296128880118895850268478644855990803068254796606918169218391496551542149863377916739003191853932322190338011172662453643591091207122348388611936492781788668656131886780611716127193194735647068796721954357023647416314666916586013088985392592150969292282816341611538047550680882867119431363784022285070284364660058653862061226257009392225398058530397248952647409551737590333931851064048011047457090129281659157361686849792653654752949958006921170233955883866369961779939655018746405090427870451978451248088534195832814922386567830075829738639624467187401546596159601708296298081624738251233870617930143881903293400882137681370458214151466658428492101084119458354900637463290218387837220009843527637179722338145650677509344255128686531988051165743590532943156848389681466745055084363089034117094818813266065677967222715208162478130733904053190385376266831268820252628340593740559533025619834333829739801597475664566339074262765824706869863633971707863020554325676680489828851282810940768130887666658660882538806419142981189283060950015658035535394715866416867367476913961697880624465046874317872336102551402135801642721595570923739819480227165533256921308811010031519701202917481086353160043058709930211399770154107946143546728495845201716049663466340251793443244401079651727622251259960491657901199146034983929110791122310665866568439636226368367913505052868959650337469935623863320176623123207638525827357254879731368075894023570163132663094542768460786555891981200887544783994952100484546731937043261849189590063791017649457961739736889592754543272015008194477841251918049798279019942135238163164722294279779943296273074286608672803052901471657354979049942958563762650507463795641495823878967817009622729410616088276938575259917748171812563845764207045534152102810076863514739090985792929735304776964184746507793080532713944526817571807200778906747887269917018172289338268541003006960420339789295354552862018008200640163454970426182290597148426558214336695941181563783670111525475145554394013563943875899197085792118057648980105759751918773494316553840999440438687445343681414050613566383271939996610462821494471055744593452988899859551799305882926189806528332618285066481729754788371349106494936997008852429998130379344294383947386506825808369948833288488708185993188003944771867927706217620140749762556255299377423606205368011391959269415212803560655551732785324935947426010597705085829435529459523022846668293569223157125776665309418717137559069264548603698560121426620629572818129267077422845132485425372426098281122461681848075620667124625900026832432200572735561911394221773522625389605356211001960865765625961371366333977914066107281784606668436850730284631529726104197528106566578409027452769099563880526853060910056364381099932094905938343716145558993888031027046142742590066245955256950035441205441729788619951815677457851285521698524033400495662911062280132459497870640064075358295958335144340292357413153372310767206335401452542559273584672247342246802673645891343169633753996902685681911978760828316833734442535605004428790841228230720189473207263674582580642840095694096480288452901250906327952662896368367945254201160153278183053527849753989578456547257908130511149276158346311877350722067361968816010040529810266806687849422275075352928096567573502884809814374638095587955628945204025582596940527241145246854018307522878575300059719018866151636927427674568220681337268390360022508155988555696826371968394142739194498468784522296302263330372352105894065593638976725854565791368572474583648782645897709908445333421228540792898679606471574451327495551415106159995981951499290786044286691618442355574838945297699721676114482976889362484620146458609185498456834694989986168842792742791097333798322650252281720002425324126176411159312154100871541926942428339014005878629980739755395861489384033865695754362080374099628203782712474128478094412748305545779930927582142151536257868790100583829011162506957516517123231026816458933323781467989374609632392798942008861172720265197626547405577275649709744807193799645870061964550571968038719483902889503533091094581576839963396990739382385502191605079847202703205847583268424917883623749210657629393462129688134679542784570056195937897094635974310694237943814929056245199323108200415527822041445466012576561699130633754122622994094254943665906554996947630080365905801880853353781083404310503417016136264363291983281860070010810425097776609203364461849784147682674932906252687999150940023161548485227147598059918962714511280305477245513946290875027644659370542539106556927356372307177747960021868772277375799716271750728084847705940174121640814883412707000626906585443973658453600747742895008041333672806330292664486773142195157348153516644942652231053029242377518462630210016152199264617611436173544706135539389453442255650949859793092763897983845790531771368515746510836675889311711531692308800940826191777238396086455586685324200523404031086391405481316831971370557349647010152236137394854706938592516307383417228484660781550809903224601346508570809305771453777020903355890192725732429798523268463834662443597711284602063414694532402736802288375617887291822380854198022744793109286860105319090821297457461800448501872061542794223478038999303187463229856699916434907451313889621139342155089264798533607316721040124801957731152013218551251880408259273506883165878848189056463484916222584850901833979573706470164341258361460412484934281185229379060379281668976180028538475195420688994832751775935619538085749097301558887516852008888761977993690155283034684785718746615387551420027749137668880364084416776568540309051133892782015935732757861167894106765287012138198746092338119474589653991528838941537720621472347422924161519652475864358763178779381607413245454004518551549112745998998754558989287818377702451750236946182565847470157616164149182886450928039027519395516973017997134468074937559372264261724958421135940623799180632337544983344521931185565128572674703605341091945544780937290093563687570913950798947046566557981798840795599024637373630407348228120844821088959219292461004349722709550905648681548172570051895913794585944325607015525087870779971871159845937147953823038697149937505183819423249068229717210392297390358096360790567095207998176926906101129061990440436421718268857941758162632675259283765731806584136541440905662358606851664104852887808775243320778571393634317444732840334077317121272103361428661699231559066979034281901004278248551490675321864593931429280189970825807593839069707037579216584763675638929261071690809130355698672083020226793775519321083216207027858596153491647836663308630353809557546737452278190175632570044402390282331111302085629800233988713508196232377008736400958141402337582103741500348459012666329670624762454551674615063824985239636684491974027308584741726093113562759536607543631563952750181540913836437075930722676337137861006067242378062651331737036233049138241624457494108521165287960711550789089444828564147150673773237353710089710738371998586317745013496846933353680263699859770860097002469087071952559690381857021697446740148748977599853949845236936052377558312856244436049800448617012440302723663335511327935310030306099226506955320854867959790507604160101846884420004338055732984006638322897767324119184018429862020722726053464275528506641977343012707530352829967624267189156683334510221884865978661348530240737906437627606519577846737050075564964296230487358365682981273726736785021765575927025321528114232262257593762646346738413689063018846354832770972850561308271305473610904139226030280875964384098544238065862276291385979061833071742546445438895425347432132236440487683023698516812391120055259979930344377652044701926721171291023196987457268890227129190597454386460697825618219359192596668967218459649264778209417165644484432040050970097516736209598653912445072556024322409207021775937699673139289175103655242970055911761822527727170852667704527187802549139026646338489196723419618972379580318826489331310434061879204849100127239589674394944397010069400744913541730920749172354874151235510396792298932590963708204112135355149607260235621752223101657674348532006886022470776346434197945816626822345649084496622853806699092400582081741909873464419544712573365339986283832910906814691465751985948639120836114103350001220787231533802412811949134321178112649082507960830093242771891361679054243792837278597245567251319578042463783427283285347448384669593046574337943407120730690129274273340040912044062310374617659184687272725383978681114445772805834254137374132726772228534245970842962161193747181630050519902653801933234541361055550091707947939844127057727270213027189662619233561853238806263905062982857618551299195803049426045441480499356069891331631520266415614980017392250331155964101301344964509208283890325234769682550915347427699286596092468857671917494085238859144716501609231517744858179805257524543632942085507113229513343900169055977083103916464048172518488653728187387038111634649728493224004022610488711119078693591920053539438072509132259644910743505675956847909188706198657753557732692940671757396055066932033859455065688665224429937941995617913560384977713991286537141458756105424335799614920985975362847800234557705881683951289457972852682245160915792003670688443985145392922618298615394825479901198684195988335935454059420216972854233281100101081299549459675534728911794797646977262851553051467003270261527113147434122790330947359844346166446267498124863992411080074304367025989752164265811947065083735649097866064748001115904286676074482425119444357576578967182056273907718303783336729673186012913565795244922363318364067658445570779199758514564012460766576132525838433051365624632507705134448656124723105513250016635810962630799671747313078384249558228122510430569503097822331588720686169321358293368733405268024095696176063064225705982163969303128037205267725321923794550371038247744283866148880407703712357251508401893030589794390173101573030276236060325862021869815311570711271377347772620045913078294231471880836288404250331830027677707929647659160579473274196341284182234009549448413532015241399115193508317277706185812341774265419455856894454368695247120441287162658234491360360146082620291092849186266042351359663302684969167384310836240816928249286491678406450209034537114009600 v3
land 40922890480356654541820198883293391948678320101461479897305796044943393807108489659998931847389197843251298555671041433891918306315311685266651730004071246832924436136117811056746185800498873715657388701747266959206021233961250088613876891177573011810692524643873458748711769758646361058123955163765268409067164338215075964354505276094965003271126744531775290861238905417088938371034698898356628805185959120594675264851224737063697883589768561891098701472910046857078713993225204593863479797777574328112019046402054521547696991992604769831502819779980330768610569916145404738519098625952005538510765919674372773977990689193561932574947852651853277447936907245842258586211251810982788330064692515214221249241197276267986982575035000170842502991217589236998590364887120582385531006587522031810629631118102903138515213649053278817114498683197349102143973249808288309350175077695059714098015062504108848257570465396592768438030428443506245679631805866175684041691958416819885128081473404913642491439674525567339652402209784619105873036252890970328824594643011688021117335918409381138883244115276105006771665941349737415679828043008652962852421445698121026035497985507707406609700843139702619263057856704770578816681246331882916153532897715150244330504014813818281965906840050030743934429024856486761171754326236671223439119255347781506403260173475282800816158915561993922732973218538825603973441435089635820900064198854146395640947551674062259761770065259106379470960039719167813006095368445552515239040436694513164375656268959249895252470655977761979472991334324001491596680226880172585591535491091236153844732124128511073921244287914594302331537592064639257714962270876881937348094099281430280696216185619598870463876576819795171316301400814434531513017226959668789057377272525721858850062243125074290764619219454463484922505628197046281869050124235446523889006945261351106220713356919361568553585990298842287929373737368246900796772490407842501388844730752573052434821343338031787765368721443638293056497822551241586692076457488562203326442552718925954029321232309169044598461588072672131972160162276119422868149110218090931436592517751129252946031365982469577302915555958200685009700518226545849456671843727720447252125998740856079345918859393507493652055810932486573970790984313073774109505564055948373374705727049418406250256740798674129760781628624346071144596897213473769485555192270522557369532237825465731779734409747380900603847138154500404483745224711343531838955935467094400463816456048720991350107528814209373651079318375443129895425483989771226025634095984851762252057463856514114352718073130495246814117146449633068621923613404881143583195287816080778149115211785882194877447640047439394786288031937438062181613045486135712878875929740350748017985080945216825770039169206559008450843601602376956091374131796543898321487970370324805253371802826004026451395712178008977479722404441373836816996132597602250755735168820364457126889010423416074292928332278716674734226264748323843997400160833512267594343894005684631884706394069343600218162309422549023189532528314446648997045839854284268367670723306688628591736847193112144343736877305442142817264525504597542474236581811785108565442346102504494339564428111104247596364649729023745048552479197866965228393302584985128012255205452184836970420939505232267847926251332862529064080869262419044168946895728421751158882182739198162531344036973745447689687802449400919078437542942563094270299857464357767593402074810676979236295533444612295926805539167303300964304731779060083070812161580654504615620110687292983775028934227119009607055329981412888355788424392852442537623980802964511123476147242537424529069244293000045036329617982489417904539428527815995772844664097372539363275893123883374268826538468093459037151154742707681305142190873081353918282953753170036066185056182465242913916376834088031670367251525903564463298462568447888436440111961301361615587488746201898858597016415888954686789612706824997972313453380958218330286584718055014734468763001966361745803911445596505474205703250756056898003150863844653301526192062190490203286521728791484452937391770263498250632227726198633848876945999684572634410913965724373396232529952362379566617354279472460176497226357014982707601274964736156006526199695070367186666367568001422740744642555998111014561547005049312564079675569705817983963236350146026247640967974518297993918325159214545667406683801659458629291275843166039193340511024629918718563511381888159381883633020411230542867621176348770318475870068770507064506720318364477907025508176379691085191518505707259886275463840009198540046611747117337465900034549288025416035865038484341919348575360690835559938060367505862311102165125827441848532823242555410688367127286626804134030454849633208051454064868938888095804925562083736486833660345691682031137208915075277253634913790148053777053133890491196147065298600456009610747369443195547095075216342937337441779633291047884935166107498987275458124208143523757779255196039050082699224331197303274780824528289885503836031103909535002190425415701829179460237154943110893762634966901448310690218857065789201267391673559294865062439099036676034673215847785462521674656835409535717650716391343321900681868040037422151725999744548470705104207880215774170378327075679444581524355569751950229682710554814993425666071537348038132705373315991938983142195160682807525167097749171329203217768675944335186544617353456833195406325609730869657613737063864301146689178476682916543744482905387257125600773614048873930852123602952972800807414196049005450234786056696291796481905882539093705640300053463613022537140941183859526018845494777477421114888121912656582863002677578435897345885740964501100379131212402379567297242170034023330398050506042584606696216171039634792518852370716917079947298027887670674547869379522721435550427855207028397917702790074333154808481658365096679085789549119194060600528044556688901669008584371354695611599868253677005001889256051026570483392096112545271739727275909302989074463029223591340648788160294821005323824313458466753218889094506019103029555031077616556950441341225446630161234070166634532873674693685506622077859500433179025067159995743058712076898687422508233622144862871281777948668922007418370803975157405301373886097563278374927772038707415125730235171338803591753627452464299798847581673589359627252282253894400308366159177731042271074102779788033192528035113137360752586073027501622503855620855481438338317515255216757390476417048588654599620592967542250778687356124188199142804363411720855853363162224402240751922318326850667432834079278322637029115865857248538686145979936648620637712532877653310881627443542792497514921905188715004517727082467006065821308556820002996549405250846638362653809736828449574580908994782035472292175125368984334258094039418592056482848275888955197816454090096303489304729220733258713480991687693365933403275997831827917988209892165301835320962376012336344394907570882085615150818722366196514207386729135182956329892376253381316730188590741407956205550342243301057740014415811148046122497490239339172373209499754322347364188890382266571139249797444320772561288621643108555655173169111870602984744059287966154604188037776536999325215677085049931835238418310644747099515489554273239777704933921417750286086763527589762086473626363573952482106832758543827847307534667348412303727593523538147151688972618428628151602998381782257603672427418952095855471603197072193806174703272583571751964182155850250409343119525000040243842552359109456786898192026309378744003799673378216374463479158302749314712247365234465204824643785635072789764104606295635585176377877515005048994885883943237863177273859777314741092117491404921274838843670747108554460269155420288824305903566246015896319427278137955908526697680061406886468126592824761826350161624270817344924118195414766463126170145078841988914170789564264627800773591247968404546136239259008944681821407526972980140113973180042822539848980562929369497517849431647477308476608460541080060370988590672471769811360251131585483322545801717777675746946730497353995225398893808582024129270704909308262066074638041645630994467317485493038296338770187669390855709427041023998737187491222790935967990594050022590311243474830401444668463057306324372801901982380604597839665449227012944575664331171140597127818905052471135920109782125359028267384408057823707220104784436458440591119771744709582686263876014876819165744885872132411053746672948717289087998723916814282247835765198819858653854106725446636582282700122009123065494773268755615967563993714629233312160673059728814633041580918499216404800671053899339256905022445808987851976364043828263994395842482765344444521672694915729063027013325358532660768153688438727368796063628764544975668820521514528561484243273916995799667816231757046206228712828044406696488277688641599409119669299302113826073347509397710273656086262553775007091786790071184826896018007906505687295900655632851106926350766001324787586573380452394360344418881409505793027730493912852905088159575160704193291203498241593505081285704969320470307214115657882548632492897832939723874992647721475697870879731402552223767853060223119720383488632764629991105787834294485542642805360244208883579738225084315992165065824813082036371142152105937171834549098548931656670769274060383135077951037113090704398701263896438676543097958044067280774280143428505724452193855734001903556740978133317802878339662029736374612083982337609157593836189504983274916309098750231894430029115582044099108464294033997806658964827381998748937990829183739042462179613281453988233653224860372353356937155595984016396689879098204659126612593801846082826436159596130496554583687533485710915536737593225456244725864101626854658499759882596526069266319685590426964280877263713548024952026991501526483197571418610847857447246711130781426830826184883172809986863446805925178686641442763044581572353921874991917813743078601436771668384522139811465370859015182169592070463590223999901173923277740612519337749721997163936898980082282370728748772580931126894272694143769189544237612663446522937048838061154433494802712133570358396905214699330232523222374442877120154964418499919596817440495758645394457665722982306895914094535418540910811251149931980148460409010515435632375825941573286769387822704738350982089261905746256602061967111543421610488823920271232043562820821647188058539743399977584240780395381681173813970065613098539468666112039558042370110466203323278519160917390684029237243175027183832245563596813258048584951555427458350635889103366472737786133090109236418271216676449247983685141636428930331104753069635754631804297205933003101350583400219561336256684218271063937177255666346548439919272912513973909194651852014108392216065220090969899223988647495201044031230472154521946583873452128791409488364376377470352911580361767873809733338040076019245957567474707698442859115133520343876087956511227742187838440864112618387730022565782759057180588109099134270643327689100658075290713702474621091659758881603492465159081986885035778524875757777210858136493912506335771196093280514785176319891964577952384199750496987035069999987701333417347805354252844292520723793445629456430831842054179912739325763336404111051980371903682753235910477842173756759721012779416718993076020512876417404899686985593553842386171744644225317817506490094311069074096850410171034546489129888134260719266663068000253532806842788894794298968278895420648699946129392697810603223759996238267635764516623142594429720619165297155410736208556328796963349940141328325386545319233582171070206725155352743406930753078602244957820652964423186173743179810404640182218310390101365620973629784592954646903479343168427571262270971753980636934193148470932125598780454125172183473084916913873529288106358630624398419691697380384741310948821759041532258340591516491845819532230931313957381783706397601045618937154939221748739268440741496326624512888311630222085006756366455690210088438274171118073986130361682559565470649323876799908452882579625500158133622927241834237016907469514228015465419782087723889703735187947952053774720525407227531099128373066016149319799529418435492284257223512391649247113100901775463453314724299053610651663839426023602926984472588322247069169850534054379735006083504815637755785981509850325159017056646321894364870535115638974688738588414493696425909179861659452167768694556756734360122566417858235313578297689291632480519602496412176933325005821088965907802829342246696513381604794740535416196268981512006101880399880230157185919908555441493891430268514438097628130378321355258294631704132932709591417449262036632894102045947955651316312830507141464999385982532669418849664737058999160698338572791706957003247543869449448593895370943259470970362225318137548025136471874741246851841820473640316007057204731308176197640875497723731580619404737045635904475301299862746741262226058801153765274817485987692550553647778259780218522615037999754436204568960377376193466079159801172445860217685176141682033592052109021841197124611054347882729470957097825843201071587492506457861632748313251817697575297902497465523531145357858199157468346946002636343834132192973674785695220441992803153561230679862894126828538710321769895265994955527304546426990450245893672950809899787214644454595500403629663534088096100377265674464972195938663977861756562185542249515455913923694939034258073966187520252480605201594178493925200661062463096239729238063969155814952890436834727936170369758904975360 v4
add v2 v5
shr v6 104
land 5708990770823839524233143877797980545530986494 v7
sub v8 2854495385411919762116571938898990272765493250
sub 2854495385411919762116571938898990272765493247 v8
add v9 v10
add 2 v11
shr v6 276
land 2037035976334486086268445688409378161051468393665936250636140449354381299763336706183397374 v13
sub v14 1018517988167243043134222844204689080525734196832968125318070224677190649881668353091698690
sub 1018517988167243043134222844204689080525734196832968125318070224677190649881668353091698687 v14
add v15 v16
add 2 v17
shr v6 577
land 363419362147803445274661903944002267176820680343659030140745099590319644056698961663095525356881782780381260803133088966767300814307326 v19
sub v20 181709681073901722637330951972001133588410340171829515070372549795159822028349480831547762678440891390190630401566544483383650407153666
sub 181709681073901722637330951972001133588410340171829515070372549795159822028349480831547762678440891390190630401566544483383650407153663 v20
add v21 v22
add 2 v23
shr v6 1070
land 64836180763765514976756372870174392984569472378788076562432145776416450178326689787495422639798496785753091978301574830974924235553308989185732419283030682610330965678148586307582 v25
sub v26 32418090381882757488378186435087196492284736189394038281216072888208225089163344893747711319899248392876545989150787415487462117776654494592866209641515341305165482839074293153794
sub 32418090381882757488378186435087196492284736189394038281216072888208225089163344893747711319899248392876545989150787415487462117776654494592866209641515341305165482839074293153791 v26
add v27 v28
add 2 v29
shr v6 1691
land 11567161174868858867503549817670155728287145622944061541103214308813593929159469055614459580396462067592797657080971249983993023962637889321478361450442531251940540790713205229865500968930113649556510144425306236378050199550 v31
sub v32 5783580587434429433751774908835077864143572811472030770551607154406796964579734527807229790198231033796398828540485624991996511981318944660739180725221265625970270395356602614932750484465056824778255072212653118189025099778
sub 5783580587434429433751774908835077864143572811472030770551607154406796964579734527807229790198231033796398828540485624991996511981318944660739180725221265625970270395356602614932750484465056824778255072212653118189025099775 v32
add v33 v34
add 2 v35
shr v6 2440
land 2063650512248692368563827284830142994214247367328599695812346519635444931862206482321942405811160890213571855442410658901884170154307365379884917884620857722298385484371113610034107490923540785363375909797699954703703235518560788042337487885808736236287260081631789054 v37
sub v38 1031825256124346184281913642415071497107123683664299847906173259817722465931103241160971202905580445106785927721205329450942085077153682689942458942310428861149192742185556805017053745461770392681687954898849977351851617759280394021168743942904368118143630040815894530
sub 1031825256124346184281913642415071497107123683664299847906173259817722465931103241160971202905580445106785927721205329450942085077153682689942458942310428861149192742185556805017053745461770392681687954898849977351851617759280394021168743942904368118143630040815894527 v38
add v39 v40
add 2 v41
shr v6 3382
land 184083777009901148951480851536796132722480842643692193047992403105518260024832986247893480778145316885626996612988306798242600723265962621432675768974821503362834322867062256922933472871676000378319956942935045907290266298718681990629287025193807090855270922941016369397705979841003229496151404881535205516509182 v43
sub v44 92041888504950574475740425768398066361240421321846096523996201552759130012416493123946740389072658442813498306494153399121300361632981310716337884487410751681417161433531128461466736435838000189159978471467522953645133149359340995314643512596903545427635461470508184698852989920501614748075702440767602758254594
sub 92041888504950574475740425768398066361240421321846096523996201552759130012416493123946740389072658442813498306494153399121300361632981310716337884487410751681417161433531128461466736435838000189159978471467522953645133149359340995314643512596903545427635461470508184698852989920501614748075702440767602758254591 v44
add v45 v46
add 2 v47
shr v6 4452
land 16420821625123739831988694854786525233821797128151597902043568436051121417276139850041851556049390958105441016227685535229287078181091938996307001002052991242084029647499075775990180870552115558535067619723373914939256367939224786004917691961324659905181106353511270502771929347784711247250786564328811525875078881021758425609805599408453859744943152562174 v49
sub v50 8210410812561869915994347427393262616910898564075798951021784218025560708638069925020925778024695479052720508113842767614643539090545969498153500501026495621042014823749537887995090435276057779267533809861686957469628183969612393002458845980662329952590553176755635251385964673892355623625393282164405762937539440510879212804902799704226929872471576281090
sub 8210410812561869915994347427393262616910898564075798951021784218025560708638069925020925778024695479052720508113842767614643539090545969498153500501026495621042014823749537887995090435276057779267533809861686957469628183969612393002458845980662329952590553176755635251385964673892355623625393282164405762937539440510879212804902799704226929872471576281087 v50
add v51 v52
add 2 v53
shr v6 5650
land 1464786236049624260685376124451850855163464793406634804134924595650009137699196073488789740256022690528233381736519243125814513094767368490512041347117169397126296553786416376054862129417690612264236680596273173217497529585457669187441494533882414736478236103398964938092339616557313591147565568778390539250062537780210879899306233799589030501134232848228066226546715016482345028680908893189113380862 v55
sub v56 732393118024812130342688062225925427581732396703317402067462297825004568849598036744394870128011345264116690868259621562907256547383684245256020673558584698563148276893208188027431064708845306132118340298136586608748764792728834593720747266941207368239118051699482469046169808278656795573782784389195269625031268890105439949653116899794515250567116424114033113273357508241172514340454446594556690434
sub 732393118024812130342688062225925427581732396703317402067462297825004568849598036744394870128011345264116690868259621562907256547383684245256020673558584698563148276893208188027431064708845306132118340298136586608748764792728834593720747266941207368239118051699482469046169808278656795573782784389195269625031268890105439949653116899794515250567116424114033113273357508241172514340454446594556690431 v56
add v57 v58
add 2 v59
shr v6 6976
land 130663298481829608781738534421774961030200182945768642515226446184482290784132935865436050618383918932278269554657628824559206325342766790666323300145583975493497984429184709729577611057398702750119128019884745141310078867766806269159106982459556164758894788294104644415934567054216304256752542070618199833907016404783941237004946025956439797860820562145392237467217383150167738001989809176581017494202312280817065607310958886662076098932637694 v61
sub v62 65331649240914804390869267210887480515100091472884321257613223092241145392066467932718025309191959466139134777328814412279603162671383395333161650072791987746748992214592354864788805528699351375059564009942372570655039433883403134579553491229778082379447394147052322207967283527108152128376271035309099916953508202391970618502473012978219898930410281072696118733608691575083869000994904588290508747101156140408532803655479443331038049466318850
sub 65331649240914804390869267210887480515100091472884321257613223092241145392066467932718025309191959466139134777328814412279603162671383395333161650072791987746748992214592354864788805528699351375059564009942372570655039433883403134579553491229778082379447394147052322207967283527108152128376271035309099916953508202391970618502473012978219898930410281072696118733608691575083869000994904588290508747101156140408532803655479443331038049466318847 v62
add v63 v64
add 2 v65
shr v6 8495
land 5827777852485670616434843853195491975603058705974930875274785337344482747320782322268213421824274519488718899922999624826238672103706981736957216909113794247991307151424935162902047057293487248380517516741847787407331242287486490857004733010922453597110539692179043164360524059328182670049644324964544941875588173922555043691477397529185339599224554629138444620961706180503492983609073953121050920879385516492671135687892796495164050655741467590235029053051892001314722365618866798723070 v67
sub v68 2913888926242835308217421926597745987801529352987465437637392668672241373660391161134106710912137259744359449961499812413119336051853490868478608454556897123995653575712467581451023528646743624190258758370923893703665621143743245428502366505461226798555269846089521582180262029664091335024822162482272470937794086961277521845738698764592669799612277314569222310480853090251746491804536976560525460439692758246335567843946398247582025327870733795117514526525946000657361182809433399361538
sub 2913888926242835308217421926597745987801529352987465437637392668672241373660391161134106710912137259744359449961499812413119336051853490868478608454556897123995653575712467581451023528646743624190258758370923893703665621143743245428502366505461226798555269846089521582180262029664091335024822162482272470937794086961277521845738698764592669799612277314569222310480853090251746491804536976560525460439692758246335567843946398247582025327870733795117514526525946000657361182809433399361535 v68
add v69 v70
add 2 v71
shr v6 10142
land 259927577923845850311054544447050497779518305645939197964956536412266698925388040756528360180441159309679199749028839224361952772212752420440987124085826603777690609241736528842513185090809005904205277709057473268971784119704887514755913507996781969230603160265706311947414313928214735337232029424388832112112965213451826159957358541359881626593314328935470121297798748367468397465180370100007193625655658407866196318747362340120943324598125388327232185235152717614661603190184455019582149048846395811620063030393587902960478715902 v73
sub v74 129963788961922925155527272223525248889759152822969598982478268206133349462694020378264180090220579654839599874514419612180976386106376210220493562042913301888845304620868264421256592545404502952102638854528736634485892059852443757377956753998390984615301580132853155973707156964107367668616014712194416056056482606725913079978679270679940813296657164467735060648899374183734198732590185050003596812827829203933098159373681170060471662299062694163616092617576358807330801595092227509791074524423197905810031515196793951480239357954
sub 129963788961922925155527272223525248889759152822969598982478268206133349462694020378264180090220579654839599874514419612180976386106376210220493562042913301888845304620868264421256592545404502952102638854528736634485892059852443757377956753998390984615301580132853155973707156964107367668616014712194416056056482606725913079978679270679940813296657164467735060648899374183734198732590185050003596812827829203933098159373681170060471662299062694163616092617576358807330801595092227509791074524423197905810031515196793951480239357951 v74
add v75 v76
add 2 v77
shr v6 11917
land 11593157370701799487972395470689083250816951981773085539892694864573384556481449447644749439492322389669549419969235827561166842840339199130145634580312418222288508616751977267864620958940155681745191568957430637460627564475356367394198704335260975459857104916114634895885675905597671760716699531175672361078160461110067323753546718143336444269742422576490153938977960272953697662774111347433525728304822607966379467622122289542408088235029664670368321168611425331179475969349149107822858886404460445557543220171003239318588734836201663171937723175120959222241771152503472126 v79
sub v80 5796578685350899743986197735344541625408475990886542769946347432286692278240724723822374719746161194834774709984617913780583421420169599565072817290156209111144254308375988633932310479470077840872595784478715318730313782237678183697099352167630487729928552458057317447942837952798835880358349765587836180539080230555033661876773359071668222134871211288245076969488980136476848831387055673716762864152411303983189733811061144771204044117514832335184160584305712665589737984674574553911429443202230222778771610085501619659294367418100831585968861587560479611120885576251736066
sub 5796578685350899743986197735344541625408475990886542769946347432286692278240724723822374719746161194834774709984617913780583421420169599565072817290156209111144254308375988633932310479470077840872595784478715318730313782237678183697099352167630487729928552458057317447942837952798835880358349765587836180539080230555033661876773359071668222134871211288245076969488980136476848831387055673716762864152411303983189733811061144771204044117514832335184160584305712665589737984674574553911429443202230222778771610085501619659294367418100831585968861587560479611120885576251736063 v80
add v81 v82
add 2 v83
shr v6 13884
land 517072097140976116811438027018719231367105642715447744514085526840394482221886254291155222584366615419019487374750368311905912946407854737521410438183172529930094037876815937468003164006234433708736922214145081092428675498281916098589409509415618727529306333632580880686201214264657052937720838385982886168350629334234693478730959596585033111917698816565221152929244890549296419083335365026404137485826833867615097659495389717721573618436826334470459161811732595699634010955373123355602513627630901175514856681290507166960735956293647978211448402662230997368697634166931673674325095657679234371096893657776953539690494 v85
sub v86 258536048570488058405719013509359615683552821357723872257042763420197241110943127145577611292183307709509743687375184155952956473203927368760705219091586264965047018938407968734001582003117216854368461107072540546214337749140958049294704754707809363764653166816290440343100607132328526468860419192991443084175314667117346739365479798292516555958849408282610576464622445274648209541667682513202068742913416933807548829747694858860786809218413167235229580905866297849817005477686561677801256813815450587757428340645253583480367978146823989105724201331115498684348817083465836837162547828839617185548446828888476769845250
sub 258536048570488058405719013509359615683552821357723872257042763420197241110943127145577611292183307709509743687375184155952956473203927368760705219091586264965047018938407968734001582003117216854368461107072540546214337749140958049294704754707809363764653166816290440343100607132328526468860419192991443084175314667117346739365479798292516555958849408282610576464622445274648209541667682513202068742913416933807548829747694858860786809218413167235229580905866297849817005477686561677801256813815450587757428340645253583480367978146823989105724201331115498684348817083465836837162547828839617185548446828888476769845247 v86
add v87 v88
add 2 v89
shr v6 15980
land 11531093087610783086600770490135794814938016760415388868341962628738830452172491792010994820698353823302722715089816253728759881552814524936050495041642730785132509383698673100799969484289767392650991679885011012617058588970490870692176576830613564304091973760861011642436222241403189146839710654399173723679261022131201327385937362946768148005700284522582995095091591735200284690376706716012757410458569577130081929019020605136775628451747475105608219526161412868535776628299349047638048625093674063831835113183022849547725183881316289628923754058223340178713671691863848986169015332618848730296076449230880050957890538046203230785029764575634768902325677326334 v91
sub v92 5765546543805391543300385245067897407469008380207694434170981314369415226086245896005497410349176911651361357544908126864379940776407262468025247520821365392566254691849336550399984742144883696325495839942505506308529294485245435346088288415306782152045986880430505821218111120701594573419855327199586861839630511065600663692968681473384074002850142261291497547545795867600142345188353358006378705229284788565040964509510302568387814225873737552804109763080706434267888314149674523819024312546837031915917556591511424773862591940658144814461877029111670089356835845931924493084507666309424365148038224615440025478945269023101615392514882287817384451162838663170
sub 5765546543805391543300385245067897407469008380207694434170981314369415226086245896005497410349176911651361357544908126864379940776407262468025247520821365392566254691849336550399984742144883696325495839942505506308529294485245435346088288415306782152045986880430505821218111120701594573419855327199586861839630511065600663692968681473384074002850142261291497547545795867600142345188353358006378705229284788565040964509510302568387814225873737552804109763080706434267888314149674523819024312546837031915917556591511424773862591940658144814461877029111670089356835845931924493084507666309424365148038224615440025478945269023101615392514882287817384451162838663167 v92
add v93 v94
add 2 v95
shr v6 18203
land 514303937614691658102041179657040037282485048712790198816167804256474264478248976796312449611742643510190272905852009829385534401104608302324376410648726522479868524311135753280993291045129278237575959342047821188394925779491438117356330009912067526951339089559020555858588190242392049404419243449456544677784069010742479435022682412204918720952792085443142853203702083163386126444893169957085320913150690440466979335050748712826995364760110246542483595332435958442592413522340191293051228597766237564489487479139163112104407453630726533788942075175603256210376801986511398151529059786728618248231797171295468489305022275251652292024750576521194635455587155509845384170488251483789827501964232714514071550 v97
sub v98 257151968807345829051020589828520018641242524356395099408083902128237132239124488398156224805871321755095136452926004914692767200552304151162188205324363261239934262155567876640496645522564639118787979671023910594197462889745719058678165004956033763475669544779510277929294095121196024702209621724728272338892034505371239717511341206102459360476396042721571426601851041581693063222446584978542660456575345220233489667525374356413497682380055123271241797666217979221296206761170095646525614298883118782244743739569581556052203726815363266894471037587801628105188400993255699075764529893364309124115898585647734244652511137625826146012375288260597317727793577754922692085244125741894913750982116357257035778
sub 257151968807345829051020589828520018641242524356395099408083902128237132239124488398156224805871321755095136452926004914692767200552304151162188205324363261239934262155567876640496645522564639118787979671023910594197462889745719058678165004956033763475669544779510277929294095121196024702209621724728272338892034505371239717511341206102459360476396042721571426601851041581693063222446584978542660456575345220233489667525374356413497682380055123271241797666217979221296206761170095646525614298883118782244743739569581556052203726815363266894471037587801628105188400993255699075764529893364309124115898585647734244652511137625826146012375288260597317727793577754922692085244125741894913750982116357257035775 v98
add v99 v100
add 2 v101
shr v6 20555
land 11469361067346228139751050383678787379996843010231282869156611321479238326975638077872702812275965708425978324875673149423499386332752007008420022917748420302267274271125383366294080092730442255633353549536791387345329261254196642455136080174017760288024746012689271527759550610419144573693287584330430146019671170093007411590044186969691456181646999431330412297478948624359931867691265575623540920788150326717215171909889035681106024538435181348674516442469987774343554249210405956336182791799995116926314270818657002304166762459744598953256847396738792417955612840022291313108088502999733876705096596856462178348715272460883127891520883840254807424394279963936386191280945064933082582726451118864513464783595040816841540462640142100165433734725630 v103
sub v104 5734680533673114069875525191839393689998421505115641434578305660739619163487819038936351406137982854212989162437836574711749693166376003504210011458874210151133637135562691683147040046365221127816676774768395693672664630627098321227568040087008880144012373006344635763879775305209572286846643792165215073009835585046503705795022093484845728090823499715665206148739474312179965933845632787811770460394075163358607585954944517840553012269217590674337258221234993887171777124605202978168091395899997558463157135409328501152083381229872299476628423698369396208977806420011145656554044251499866938352548298428231089174357636230441563945760441920127403712197139981968193095640472532466541291363225559432256732391797520408420770231320071050082716867362818
sub 5734680533673114069875525191839393689998421505115641434578305660739619163487819038936351406137982854212989162437836574711749693166376003504210011458874210151133637135562691683147040046365221127816676774768395693672664630627098321227568040087008880144012373006344635763879775305209572286846643792165215073009835585046503705795022093484845728090823499715665206148739474312179965933845632787811770460394075163358607585954944517840553012269217590674337258221234993887171777124605202978168091395899997558463157135409328501152083381229872299476628423698369396208977806420011145656554044251499866938352548298428231089174357636230441563945760441920127403712197139981968193095640472532466541291363225559432256732391797520408420770231320071050082716867362815 v104
add v105 v106
add 2 v107
shr v6 23100
land 127887649376417730095964212084338576865283725232457614830059534314026447356818020322908765733224639868934536031291777715378465439854093826128615873315875056094666018588591650473179071126296536559656453680225681423716664594576850444195964410865760553980691438083549153836657340226561944722535797548847492012764206698253167259617860283173190367554993570039474644993136260199942647146664392735829898974087740748186036660705677120498479248534373656442131504713224687547961422926714923573238132583105543921168977597065165048730343398389964150109974317907117592991724445472436723282039960694737928327656118487911410702204858970071205528872093225694555941600772738728490684781579868387985845478399678294266946959969349165145431383233133520864280734168713273140778981619622376445824089703030462611454 v109
sub v110 63943824688208865047982106042169288432641862616228807415029767157013223678409010161454382866612319934467268015645888857689232719927046913064307936657937528047333009294295825236589535563148268279828226840112840711858332297288425222097982205432880276990345719041774576918328670113280972361267898774423746006382103349126583629808930141586595183777496785019737322496568130099971323573332196367914949487043870374093018330352838560249239624267186828221065752356612343773980711463357461786619066291552771960584488798532582524365171699194982075054987158953558796495862222736218361641019980347368964163828059243955705351102429485035602764436046612847277970800386369364245342390789934193992922739199839147133473479984674582572715691616566760432140367084356636570389490809811188222912044851515231305730
sub 63943824688208865047982106042169288432641862616228807415029767157013223678409010161454382866612319934467268015645888857689232719927046913064307936657937528047333009294295825236589535563148268279828226840112840711858332297288425222097982205432880276990345719041774576918328670113280972361267898774423746006382103349126583629808930141586595183777496785019737322496568130099971323573332196367914949487043870374093018330352838560249239624267186828221065752356612343773980711463357461786619066291552771960584488798532582524365171699194982075054987158953558796495862222736218361641019980347368964163828059243955705351102429485035602764436046612847277970800386369364245342390789934193992922739199839147133473479984674582572715691616566760432140367084356636570389490809811188222912044851515231305727 v110
add v111 v112
add 2 v113
shr v6 25772
land 2851989882782515535155367199708271663537573771465403868703126130290203311501943023266787830075422515820157953313755688055210233886659002184091548717738209133486702926486317322048706186264064593368972787807830224504533551932688271247667224868273928472022282277946532332843991577032887124980789642955723654332531677626739596928661722031867391951794577938777777108659593737789311131396120888845730213144969829494372196590670964402870826658791147231697444494952509205089391621723606211890113735830817680590404811750235687895884425721853893942481331755403751957930528802649108160236028780036918012941174376900712593362541944467792208983261952680951923682103867944378267728029821000176747540055515171136404378954251735229890412632057879107267359614959959655248655805164639275201593818946114020538779763597217067487486720253928156432953245694 v115
sub v116 1425994941391257767577683599854135831768786885732701934351563065145101655750971511633393915037711257910078976656877844027605116943329501092045774358869104566743351463243158661024353093132032296684486393903915112252266775966344135623833612434136964236011141138973266166421995788516443562490394821477861827166265838813369798464330861015933695975897288969388888554329796868894655565698060444422865106572484914747186098295335482201435413329395573615848722247476254602544695810861803105945056867915408840295202405875117843947942212860926946971240665877701875978965264401324554080118014390018459006470587188450356296681270972233896104491630976340475961841051933972189133864014910500088373770027757585568202189477125867614945206316028939553633679807479979827624327902582319637600796909473057010269389881798608533743743360126964078216476622850
sub 1425994941391257767577683599854135831768786885732701934351563065145101655750971511633393915037711257910078976656877844027605116943329501092045774358869104566743351463243158661024353093132032296684486393903915112252266775966344135623833612434136964236011141138973266166421995788516443562490394821477861827166265838813369798464330861015933695975897288969388888554329796868894655565698060444422865106572484914747186098295335482201435413329395573615848722247476254602544695810861803105945056867915408840295202405875117843947942212860926946971240665877701875978965264401324554080118014390018459006470587188450356296681270972233896104491630976340475961841051933972189133864014910500088373770027757585568202189477125867614945206316028939553633679807479979827624327902582319637600796909473057010269389881798608533743743360126964078216476622847 v116
add v117 v118
add 2 v119
shr v6 28573
land 31800749842360049015103299284790617698890483905547984275644170402206803561656429906225752320496451370947792200683744138506737964263205343597152688477327237032341539671893487818032972460293113336104592162502323934013774123699867595822126027614747058066390487432120908324369402610727225055953928213424243453236174975981501750498254557939307374512857707311444479461072219360623888386914174380550964952259193927629154263818842615754720202408989697853429625273152802192994199565053640528138663079412855242924013605501661052149316914904531720848282245990517176033734207217909048586243838849214569498953884702287809850240071994138369150299188119709077028703185233048296281355180848257488980756499143679841253489784915367726855971474496334149331078672545944247698634947788993025540154986745459722572083616301221072543528795398721985129695259330281797585463134884136391351731810906144766 v121
sub v122 15900374921180024507551649642395308849445241952773992137822085201103401780828214953112876160248225685473896100341872069253368982131602671798576344238663618516170769835946743909016486230146556668052296081251161967006887061849933797911063013807373529033195243716060454162184701305363612527976964106712121726618087487990750875249127278969653687256428853655722239730536109680311944193457087190275482476129596963814577131909421307877360101204494848926714812636576401096497099782526820264069331539706427621462006802750830526074658457452265860424141122995258588016867103608954524293121919424607284749476942351143904925120035997069184575149594059854538514351592616524148140677590424128744490378249571839920626744892457683863427985737248167074665539336272972123849317473894496512770077493372729861286041808150610536271764397699360992564847629665140898792731567442068195675865905453072386
sub 15900374921180024507551649642395308849445241952773992137822085201103401780828214953112876160248225685473896100341872069253368982131602671798576344238663618516170769835946743909016486230146556668052296081251161967006887061849933797911063013807373529033195243716060454162184701305363612527976964106712121726618087487990750875249127278969653687256428853655722239730536109680311944193457087190275482476129596963814577131909421307877360101204494848926714812636576401096497099782526820264069331539706427621462006802750830526074658457452265860424141122995258588016867103608954524293121919424607284749476942351143904925120035997069184575149594059854538514351592616524148140677590424128744490378249571839920626744892457683863427985737248167074665539336272972123849317473894496512770077493372729861286041808150610536271764397699360992564847629665140898792731567442068195675865905453072383 v122
add v123 v124
add 2 v125
shr v6 31502
land 354590209678342166922577058917515525554624949729180617472014535662060774596991590926351076936835840286335825058287385097899812597323000922953056986827821801820807595196926299978274527037905983105483689319277454369795512728272955616941930198326508928977124559267869256148878524886357237522510455906929047322576491914035265186542137547617301037612761997585946670075397000096263891854030074376281138461399776254043934958887079773002297591067701328542025469427972639332985482092259912517720090315258022898502169238587177136818787338302536622137168013564144638514176818533692218543515535275775431984681346532842317403873369498528947251187579033419594658175922339809963765270950584859620135013250167918428582041132750689428194063519207842545635099213710810289967233572060228287359795637086944299076845819060395130073668048552183171072817609296640022052973756381638137282654611384259701932886131557795101416891913324857334431742 v127
sub v128 177295104839171083461288529458757762777312474864590308736007267831030387298495795463175538468417920143167912529143692548949906298661500461476528493413910900910403797598463149989137263518952991552741844659638727184897756364136477808470965099163254464488562279633934628074439262443178618761255227953464523661288245957017632593271068773808650518806380998792973335037698500048131945927015037188140569230699888127021967479443539886501148795533850664271012734713986319666492741046129956258860045157629011449251084619293588568409393669151268311068584006782072319257088409266846109271757767637887715992340673266421158701936684749264473625593789516709797329087961169904981882635475292429810067506625083959214291020566375344714097031759603921272817549606855405144983616786030114143679897818543472149538422909530197565036834024276091585536408804648320011026486878190819068641327305692129850966443065778897550708445956662428667215874
sub 177295104839171083461288529458757762777312474864590308736007267831030387298495795463175538468417920143167912529143692548949906298661500461476528493413910900910403797598463149989137263518952991552741844659638727184897756364136477808470965099163254464488562279633934628074439262443178618761255227953464523661288245957017632593271068773808650518806380998792973335037698500048131945927015037188140569230699888127021967479443539886501148795533850664271012734713986319666492741046129956258860045157629011449251084619293588568409393669151268311068584006782072319257088409266846109271757767637887715992340673266421158701936684749264473625593789516709797329087961169904981882635475292429810067506625083959214291020566375344714097031759603921272817549606855405144983616786030114143679897818543472149538422909530197565036834024276091585536408804648320011026486878190819068641327305692129850966443065778897550708445956662428667215871 v128
add v129 v130
add 2 v131
shr v6 34559
land 3953812957965127987308452879675926680630781365251547657836531420316681202187902253512591697949226126198588489406329256857935936115094101217809718469200318028458658204390203148162114123323896213769600642259637387829217690563322924667628653088779482328018735205096207765448375663174789908926366275471314614039274718338581668637400907781235785429122724740854776768202632020268853849324169776922752436979307588485998107782302764931776964006600171352220346935994006988319660188543895012049948543906829412076136420340677923326405678407282241730526584497437385849830378582910401330959213903224515736990598334143542613788857909577358299800855909646600787280015298795484213271147656851505460610750465442679607743778598562268416422262682002271210893618954819958559254426377220225735859139578985280931473267850130105081925724055472624998287805384067511073904092324820622791003239137629095554542062518495946501733166233707231816705762611174594356366290777491562594004476362750 v133
sub v134 1976906478982563993654226439837963340315390682625773828918265710158340601093951126756295848974613063099294244703164628428967968057547050608904859234600159014229329102195101574081057061661948106884800321129818693914608845281661462333814326544389741164009367602548103882724187831587394954463183137735657307019637359169290834318700453890617892714561362370427388384101316010134426924662084888461376218489653794242999053891151382465888482003300085676110173467997003494159830094271947506024974271953414706038068210170338961663202839203641120865263292248718692924915189291455200665479606951612257868495299167071771306894428954788679149900427954823300393640007649397742106635573828425752730305375232721339803871889299281134208211131341001135605446809477409979279627213188610112867929569789492640465736633925065052540962862027736312499143902692033755536952046162410311395501619568814547777271031259247973250866583116853615908352881305587297178183145388745781297002238181378
sub 1976906478982563993654226439837963340315390682625773828918265710158340601093951126756295848974613063099294244703164628428967968057547050608904859234600159014229329102195101574081057061661948106884800321129818693914608845281661462333814326544389741164009367602548103882724187831587394954463183137735657307019637359169290834318700453890617892714561362370427388384101316010134426924662084888461376218489653794242999053891151382465888482003300085676110173467997003494159830094271947506024974271953414706038068210170338961663202839203641120865263292248718692924915189291455200665479606951612257868495299167071771306894428954788679149900427954823300393640007649397742106635573828425752730305375232721339803871889299281134208211131341001135605446809477409979279627213188610112867929569789492640465736633925065052540962862027736312499143902692033755536952046162410311395501619568814547777271031259247973250866583116853615908352881305587297178183145388745781297002238181375 v134
add v135 v136
add 2 v137
shr v6 37809
land 22043243834557247116806118132637650061887997082885506063079927387580475642545486756222311689277114518962321086295125922318445893088086892301654928960634061393567383807770451446403291282038339392330527871771295392900413369833813108120609028552627345741054006917143661926307778547209932913407186863429232234478731032056176394975074910490436998189771531957221629149048568842150675984877352878799051285333615100913475028743337350189993685674225994403419825787040016299888379645612439139281766289426594251104102455977284372015444253410506741789956594350846837792786738683597079749484262542259245982929801262603876103138886398399054396295629647627968000410557873798927218681481689608357567822048647143615895313466813061876704456919614193300993845726531526771858613626544973399048072258740759648492883152522758346744922071928474703861998277182358495715569523868041282229030092516688490574848101155065359177496996250953498842872423236820658324442285769185702229772110786749438802063225067126490176999576339855966206 v139
sub v140 11021621917278623558403059066318825030943998541442753031539963693790237821272743378111155844638557259481160543147562961159222946544043446150827464480317030696783691903885225723201645641019169696165263935885647696450206684916906554060304514276313672870527003458571830963153889273604966456703593431714616117239365516028088197487537455245218499094885765978610814574524284421075337992438676439399525642666807550456737514371668675094996842837112997201709912893520008149944189822806219569640883144713297125552051227988642186007722126705253370894978297175423418896393369341798539874742131271129622991464900631301938051569443199199527198147814823813984000205278936899463609340740844804178783911024323571807947656733406530938352228459807096650496922863265763385929306813272486699524036129370379824246441576261379173372461035964237351930999138591179247857784761934020641114515046258344245287424050577532679588748498125476749421436211618410329162221142884592851114886055393374719401031612533563245088499788169927983106
sub 11021621917278623558403059066318825030943998541442753031539963693790237821272743378111155844638557259481160543147562961159222946544043446150827464480317030696783691903885225723201645641019169696165263935885647696450206684916906554060304514276313672870527003458571830963153889273604966456703593431714616117239365516028088197487537455245218499094885765978610814574524284421075337992438676439399525642666807550456737514371668675094996842837112997201709912893520008149944189822806219569640883144713297125552051227988642186007722126705253370894978297175423418896393369341798539874742131271129622991464900631301938051569443199199527198147814823813984000205278936899463609340740844804178783911024323571807947656733406530938352228459807096650496922863265763385929306813272486699524036129370379824246441576261379173372461035964237351930999138591179247857784761934020641114515046258344245287424050577532679588748498125476749421436211618410329162221142884592851114886055393374719401031612533563245088499788169927983103 v140
add v141 v142
add 2 v143
shr v6 41187
land 122895191025885572597336000840872077765742452678087480737649943683260393890908011337709570770967996863792833982851835670670179300295842925921293738954148383012543444653299687574852496245778646267375967643579028752958068402638078795148280146753112824337148969912091759645185647479231232364518774577279985399037566195355603197791761186161128024023223416022143874032799778309969947848675064957597177380327501173738290456898671496261652815956102069317860085111287985350440543899077359827883701247879920322110220509266673776043983287030468834831227625827522402025970011891943270712329585598988027027799057117848293680278224088195600241984936707253608908573259743639746948107130362105018846257670988811028215224350927697198925815000466813775473908546661664809404550819216299914100636514483961494807639911516145338327201460827500595877302615929959224728194350240332661616432608014805936806682670015102653412952485928333296590645160383645026038569568083288176586185367608463556754644275504145302521266245276880862600779147176584397241821193736666062501445630 v145
sub v146 61447595512942786298668000420436038882871226339043740368824971841630196945454005668854785385483998431896416991425917835335089650147921462960646869477074191506271722326649843787426248122889323133687983821789514376479034201319039397574140073376556412168574484956045879822592823739615616182259387288639992699518783097677801598895880593080564012011611708011071937016399889154984973924337532478798588690163750586869145228449335748130826407978051034658930042555643992675220271949538679913941850623939960161055110254633336888021991643515234417415613812913761201012985005945971635356164792799494013513899528558924146840139112044097800120992468353626804454286629871819873474053565181052509423128835494405514107612175463848599462907500233406887736954273330832404702275409608149957050318257241980747403819955758072669163600730413750297938651307964979612364097175120166330808216304007402968403341335007551326706476242964166648295322580191822513019284784041644088293092683804231778377322137752072651260633122638440431300389573588292198620910596868333031250722818
sub 61447595512942786298668000420436038882871226339043740368824971841630196945454005668854785385483998431896416991425917835335089650147921462960646869477074191506271722326649843787426248122889323133687983821789514376479034201319039397574140073376556412168574484956045879822592823739615616182259387288639992699518783097677801598895880593080564012011611708011071937016399889154984973924337532478798588690163750586869145228449335748130826407978051034658930042555643992675220271949538679913941850623939960161055110254633336888021991643515234417415613812913761201012985005945971635356164792799494013513899528558924146840139112044097800120992468353626804454286629871819873474053565181052509423128835494405514107612175463848599462907500233406887736954273330832404702275409608149957050318257241980747403819955758072669163600730413750297938651307964979612364097175120166330808216304007402968403341335007551326706476242964166648295322580191822513019284784041644088293092683804231778377322137752072651260633122638440431300389573588292198620910596868333031250722815 v146
add v147 v148
add 2 v149
app x1 2 v12 v18 v24 v30 v36 v42 v48 v54 v60 v66 v72 v78 v84 v90 v96 v102 v108 v114 v120 v126 v132 v138 v144 v150" [s, k]

/-- The lane-parallel generator of the width band of `n`, passed to `k` (inline `Nat.rec` tests on
the thresholds of `difficultyLevel`). -/
def genFastC (n : Nat) (k : Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Int) : Int :=
  Nat.rec (motive := fun _ => Int) (genLane15C (lcgSeed n) k)
    (fun _ _ => Nat.rec (motive := fun _ => Int) (genLane36C (lcgSeed n) k)
      (fun _ _ => Nat.rec (motive := fun _ => Int) (genLane205C (lcgSeed n) k)
        (fun _ _ => Nat.rec (motive := fun _ => Int) (genLane1001C (lcgSeed n) k)
          (fun _ _ => genLane3484C (lcgSeed n) k) (Nat.div n (nat_lit 72057594037927936)))
        (Nat.div n (nat_lit 70368744177664)))
      (Nat.div n (nat_lit 68719476736)))
    (Nat.div n (nat_lit 67108864))

/-- Fast path on the encoded polynomial. -/
def fastDisc (n : Nat) (L : List Nat) : Int := appL (kont n) (discSpec n) L


/-! ## Semantics of the encoding -/

/-- `±1` from a sign bit. -/
def sg (b : Nat) : Int := 1 - 2 * (b : Int)

theorem nadd (a b : Nat) : Nat.add a b = a + b := rfl
theorem nsub (a b : Nat) : Nat.sub a b = a - b := rfl
theorem nmul (a b : Nat) : Nat.mul a b = a * b := rfl
theorem ndiv (a b : Nat) : Nat.div a b = a / b := rfl
theorem nmod (a b : Nat) : Nat.mod a b = a % b := rfl
theorem nxor (a b : Nat) : Nat.xor a b = a ^^^ b := rfl
theorem nshl (a b : Nat) : Nat.shiftLeft a b = a <<< b := rfl
theorem nand (a b : Nat) : Nat.land a b = a &&& b := rfl
theorem nshr (a b : Nat) : Nat.shiftRight a b = a >>> b := rfl

theorem shr1 (x : Nat) : Nat.shiftRight x 1 = x / 2 := by
  show x >>> 1 = _; rw [Nat.shiftRight_eq_div_pow]

theorem land1 (x : Nat) : Nat.land x 1 = x % 2 := Nat.and_one_is_mod x

theorem zdec_sg (z : Nat) : zdec z = sg (z % 2) * ((z / 2 : Nat) : Int) := by
  unfold zdec sg
  have := Nat.mod_lt z (show 2 > 0 by omega)
  split <;> rename_i h
  · rw [h]; omega
  · rw [show z % 2 = 0 by omega]; omega

theorem xor_mod2 (x y : Nat) : (x ^^^ y) % 2 = (x % 2 + y % 2) % 2 := by
  have h : ∀ a b : Nat, (a ^^^ b) % 2 = ((a % 2) ^^^ (b % 2)) := by
    intro a b
    rw [← Nat.and_one_is_mod, ← Nat.and_one_is_mod, ← Nat.and_one_is_mod, Nat.and_xor_distrib_right]
  rw [h]
  have ha := Nat.mod_lt x (show 2 > 0 by omega)
  have hb := Nat.mod_lt y (show 2 > 0 by omega)
  generalize x % 2 = a at *
  generalize y % 2 = b at *
  rcases (show a = 0 ∨ a = 1 by omega) with rfl | rfl <;>
    rcases (show b = 0 ∨ b = 1 by omega) with rfl | rfl <;> decide

theorem sg_mod2 (b : Nat) : sg (b % 2) * sg (b % 2) = 1 := by
  unfold sg
  rcases (show b % 2 = 0 ∨ b % 2 = 1 by omega) with h | h <;> rw [h] <;> decide

/-- Sign of a sum of two bits mod 2. -/
theorem sg_add (a b : Nat) : sg ((a % 2 + b % 2) % 2) = sg (a % 2) * sg (b % 2) := by
  unfold sg
  rcases (show a % 2 = 0 ∨ a % 2 = 1 by omega) with h | h <;>
    rcases (show b % 2 = 0 ∨ b % 2 = 1 by omega) with h' | h' <;> rw [h, h'] <;> decide

/-- `zq` divides the signed value `T − 2N` by `dm` (exactly, when the remainder `zr` is zero). -/
theorem zq_spec (T N dm : Nat) (hNT : N ≤ T) (hr : zr T N dm = 0) :
    zdec (zq T N dm) * (dm : Int) = (T : Int) - 2 * (N : Int) := by
  unfold zr at hr
  unfold zq zMag zSgn zD zP at *
  show zdec (((T - N - N + (N - (T - N))) / dm) <<< 1 + (1 - (1 - (N - (T - N))))) * (dm : Int) = _
  change (T - N - N + (N - (T - N))) - (T - N - N + (N - (T - N))) / dm * dm = 0 at hr
  rw [Nat.mul_comm, ← Nat.mod_eq_sub_mul_div] at hr
  rw [Nat.shiftLeft_eq, zdec_sg]
  have hm := Nat.div_add_mod (T - N - N + (N - (T - N))) dm
  rw [hr, Nat.add_zero] at hm
  generalize hq : (T - N - N + (N - (T - N))) / dm = q at hm
  by_cases hc : N ≤ T - N
  · rw [show N - (T - N) = 0 by omega, show (1 : Nat) - (1 - 0) = 0 by rfl, Nat.add_zero,
      show q * 2 ^ 1 % 2 = 0 by omega, show q * 2 ^ 1 / 2 = q by omega]
    unfold sg
    have : ((dm * q : Nat) : Int) = (T : Int) - 2 * (N : Int) := by
      rw [hm]; omega
    push_cast at this
    rw [← this]; simp; rw [Int.mul_comm]
  · rw [show (1 : Nat) - (1 - (N - (T - N))) = 1 by omega,
      show (q * 2 ^ 1 + 1) % 2 = 1 by omega, show (q * 2 ^ 1 + 1) / 2 = q by omega]
    unfold sg
    have : ((dm * q : Nat) : Int) = 2 * (N : Int) - (T : Int) := by
      rw [hm]; omega
    push_cast at this
    have e : (1 - 2 * ((1 : Nat) : Int)) * (q : Int) * (dm : Int) = -((dm : Int) * (q : Int)) := by
      rw [show (1 - 2 * ((1 : Nat) : Int)) = -1 by decide, Int.neg_one_mul, Int.neg_mul,
        Int.mul_comm]
    rw [e, this]; omega

theorem bit_cases (b : Nat) : b % 2 = 0 ∨ b % 2 = 1 := by omega

theorem xor_bits (a b : Nat) (ha : a < 2) (hb : b < 2) : a ^^^ b = (a + b) % 2 := by
  rcases (show a = 0 ∨ a = 1 by omega) with rfl | rfl <;>
    rcases (show b = 0 ∨ b = 1 by omega) with rfl | rfl <;> decide

/-- The three-term signed sum: `T − 2N = mA·x + (±mC)·y + (±m1)·z`. -/
theorem eTN_spec (mA mC sC m1 s1 x y z : Nat) (hsC : sC < 2) (hs1 : s1 < 2) :
    eN mA mC sC m1 s1 x y z ≤ eT mA mC m1 x y z ∧
    ((eT mA mC m1 x y z : Nat) : Int) - 2 * ((eN mA mC sC m1 s1 x y z : Nat) : Int)
      = (mA : Int) * zdec x + sg sC * (mC : Int) * zdec y + sg s1 * (m1 : Int) * zdec z := by
  unfold eT eN
  simp only [shr1, land1, nadd, nmul, nxor]
  rw [zdec_sg x, zdec_sg y, zdec_sg z]
  generalize ha : mA * (x / 2) = A1
  generalize hb : mC * (y / 2) = A2
  generalize hc : m1 * (z / 2) = A3
  have e1 : (mA : Int) * (sg (x % 2) * ((x / 2 : Nat) : Int)) = sg (x % 2) * (A1 : Int) := by
    rw [← ha]; push_cast; rw [← Int.mul_assoc, Int.mul_comm (mA : Int), Int.mul_assoc]
  have e2 : sg sC * (mC : Int) * (sg (y % 2) * ((y / 2 : Nat) : Int))
      = sg sC * sg (y % 2) * (A2 : Int) := by
    rw [← hb]; push_cast; ac_rfl
  have e3 : sg s1 * (m1 : Int) * (sg (z % 2) * ((z / 2 : Nat) : Int))
      = sg s1 * sg (z % 2) * (A3 : Int) := by
    rw [← hc]; push_cast; ac_rfl
  rw [e1, e2, e3, xor_bits _ _ (Nat.mod_lt _ (by omega)) hsC,
    xor_bits _ _ (Nat.mod_lt _ (by omega)) hs1]
  rcases bit_cases x with h1 | h1 <;> rcases bit_cases y with h2 | h2 <;>
    rcases bit_cases z with h3 | h3 <;>
    rcases (show sC = 0 ∨ sC = 1 by omega) with rfl | rfl <;>
    rcases (show s1 = 0 ∨ s1 = 1 by omega) with rfl | rfl <;>
    simp only [h1, h2, h3, sg] <;> constructor <;> omega

theorem and1_lt (x : Nat) : x &&& 1 < 2 := by rw [Nat.and_one_is_mod]; omega

theorem sq_eq (a : Nat) : ((a / 2 * (a / 2) : Nat) : Int) = zdec a * zdec a := by
  rw [zdec_sg]
  have h := sg_mod2 a
  push_cast
  calc ((a / 2 : Nat) : Int) * ((a / 2 : Nat) : Int)
      = (sg (a % 2) * sg (a % 2)) * (((a / 2 : Nat) : Int) * ((a / 2 : Nat) : Int)) := by
        rw [h, Int.one_mul]
    _ = sg (a % 2) * ((a / 2 : Nat) : Int) * (sg (a % 2) * ((a / 2 : Nat) : Int)) := by ac_rfl

theorem negprod_eq (a b : Nat) :
    sg (((a ^^^ b) &&& 1) ^^^ 1) * ((a / 2 * (b / 2) : Nat) : Int) = -(zdec a * zdec b) := by
  rw [zdec_sg a, zdec_sg b, xor_bits _ _ (and1_lt _) (by omega), Nat.and_one_is_mod, xor_mod2,
    Int.natCast_mul]
  generalize ((a / 2 : Nat) : Int) = p
  generalize ((b / 2 : Nat) : Int) = q
  rcases bit_cases a with h1 | h1 <;> rcases bit_cases b with h2 | h2 <;>
    simp only [h1, h2, sg] <;> grind

theorem neg_eq (c : Nat) : sg ((c &&& 1) ^^^ 1) * ((c / 2 : Nat) : Int) = -zdec c := by
  rw [zdec_sg c, xor_bits _ _ (and1_lt _) (by omega), Nat.and_one_is_mod]
  generalize ((c / 2 : Nat) : Int) = p
  rcases bit_cases c with h | h <;> simp only [h, sg] <;> grind

theorem pos_eq (a b : Nat) :
    sg ((a ^^^ b) &&& 1) * ((a / 2 * (b / 2) : Nat) : Int) = zdec a * zdec b := by
  rw [zdec_sg a, zdec_sg b, Nat.and_one_is_mod, xor_mod2, Int.natCast_mul]
  generalize ((a / 2 : Nat) : Int) = p
  generalize ((b / 2 : Nat) : Int) = q
  rcases bit_cases a with h1 | h1 <;> rcases bit_cases b with h2 | h2 <;>
    simp only [h1, h2, sg] <;> grind

theorem two_terms (f1 f2 A B : Nat) (h1 : f1 < 2) (h2 : f2 < 2) :
    f1 * A + f2 * B ≤ A + B ∧
    ((A + B : Nat) : Int) - 2 * ((f1 * A + f2 * B : Nat) : Int) = sg f1 * A + sg f2 * B := by
  rcases (show f1 = 0 ∨ f1 = 1 by omega) with rfl | rfl <;>
    rcases (show f2 = 0 ∨ f2 = 1 by omega) with rfl | rfl <;>
    simp only [sg] <;> constructor <;> omega

theorem zr_one (T N : Nat) : zr T N 1 = 0 := by
  unfold zr; simp only [ndiv, nmul, nsub, Nat.div_one, Nat.mul_one, Nat.sub_self]

theorem zlin_val (a b c d : Nat) : zdec (zlin a b c d) = zdec a * zdec b - zdec c * zdec d := by
  unfold zlin pm
  simp only [shr1, nadd, nmul, nxor, land1]
  have ht := two_terms ((a ^^^ b) % 2) ((((c ^^^ d) % 2) ^^^ 1)) (a / 2 * (b / 2)) (c / 2 * (d / 2))
    (Nat.mod_lt _ (by omega)) (by rw [xor_bits _ _ (Nat.mod_lt _ (by omega)) (by omega)]; omega)
  have h := zq_spec _ _ 1 ht.1 (zr_one _ _)
  rw [Int.ofNat_one, Int.mul_one] at h
  rw [h, ht.2, ← Nat.and_one_is_mod (a ^^^ b), ← Nat.and_one_is_mod (c ^^^ d), pos_eq,
    negprod_eq]
  omega

/-- One element of the fused pseudo-remainder: `lg·(lg·x − lf·y) − c₁·z`, divided by `dm`. -/
theorem elt_val (lg lf c1 x y z dm : Nat)
    (hr : zr (eT (Nat.mul (Nat.shiftRight lg 1) (Nat.shiftRight lg 1))
        (Nat.mul (Nat.shiftRight lg 1) (Nat.shiftRight lf 1)) (Nat.shiftRight c1 1) x y z)
      (eN (Nat.mul (Nat.shiftRight lg 1) (Nat.shiftRight lg 1))
        (Nat.mul (Nat.shiftRight lg 1) (Nat.shiftRight lf 1))
        (Nat.xor (Nat.land (Nat.xor lg lf) 1) 1) (Nat.shiftRight c1 1)
        (Nat.xor (Nat.land c1 1) 1) x y z) dm = 0) :
    zdec (zq (eT (Nat.mul (Nat.shiftRight lg 1) (Nat.shiftRight lg 1))
        (Nat.mul (Nat.shiftRight lg 1) (Nat.shiftRight lf 1)) (Nat.shiftRight c1 1) x y z)
      (eN (Nat.mul (Nat.shiftRight lg 1) (Nat.shiftRight lg 1))
        (Nat.mul (Nat.shiftRight lg 1) (Nat.shiftRight lf 1))
        (Nat.xor (Nat.land (Nat.xor lg lf) 1) 1) (Nat.shiftRight c1 1)
        (Nat.xor (Nat.land c1 1) 1) x y z) dm) * (dm : Int)
      = zdec lg * (zdec lg * zdec x - zdec lf * zdec y) - zdec c1 * zdec z := by
  have hsC : Nat.xor (Nat.land (Nat.xor lg lf) 1) 1 < 2 := by
    rw [nxor, nand, xor_bits _ _ (and1_lt _) (by omega)]; omega
  have hs1 : Nat.xor (Nat.land c1 1) 1 < 2 := by
    rw [nxor, nand, xor_bits _ _ (and1_lt _) (by omega)]; omega
  obtain ⟨hNT, he⟩ := eTN_spec _ _ _ _ _ x y z hsC hs1
  rw [zq_spec _ _ dm hNT hr, he]
  simp only [shr1, nmul, nxor, nand]
  rw [sq_eq, negprod_eq, Int.mul_assoc (sg _), ← Int.mul_assoc (sg ((c1 &&& 1) ^^^ 1)), neg_eq]
  grind

/-! ## List semantics -/

/-- The fused two-stage pseudo-remainder on integer lists (`y` looks one ahead in `Z`). -/
def r2 (LG LF C1 : Int) : List Int → List Int → List Int
  | X :: Xs, Z :: Zs => (LG * (LG * X - LF * Zs.headD 0) - C1 * Z) :: r2 LG LF C1 Xs Zs
  | _, _ => []

theorem zdec_zero : zdec 0 = 0 := by decide

theorem headD_map (zs : List Nat) : (zs.map zdec).headD 0 = zdec (zs.headD 0) := by
  cases zs <;> simp [zdec_zero]

theorem qs_val (lg lf c1 dm : Nat) : ∀ xs zs : List Nat, xs.length = zs.length →
    rs (Nat.mul (Nat.shiftRight lg 1) (Nat.shiftRight lg 1))
      (Nat.mul (Nat.shiftRight lg 1) (Nat.shiftRight lf 1))
      (Nat.xor (Nat.land (Nat.xor lg lf) 1) 1) (Nat.shiftRight c1 1)
      (Nat.xor (Nat.land c1 1) 1) dm xs zs = 0 →
    (qs (Nat.mul (Nat.shiftRight lg 1) (Nat.shiftRight lg 1))
      (Nat.mul (Nat.shiftRight lg 1) (Nat.shiftRight lf 1))
      (Nat.xor (Nat.land (Nat.xor lg lf) 1) 1) (Nat.shiftRight c1 1)
      (Nat.xor (Nat.land c1 1) 1) dm xs zs).map (fun q => zdec q * (dm : Int))
      = r2 (zdec lg) (zdec lf) (zdec c1) (xs.map zdec) (zs.map zdec)
  | [], _, _, _ => by simp [qs, r2]
  | _ :: _, [], h, _ => by simp at h
  | x :: xs, z :: zs, h, hr => by
    simp only [rs, nadd] at hr
    simp only [qs, r2, List.map_cons]
    rw [elt_val lg lf c1 x _ z dm (by omega), qs_val lg lf c1 dm xs zs (by simpa using h) (by omega),
      headD_map]

theorem qs_length (mA mC sC m1 s1 dm : Nat) : ∀ xs zs : List Nat, xs.length = zs.length →
    (qs mA mC sC m1 s1 dm xs zs).length = xs.length
  | [], _, _ => by simp [qs]
  | _ :: _, [], h => by simp at h
  | x :: xs, z :: zs, h => by
    simp only [qs, List.length_cons]
    rw [qs_length mA mC sC m1 s1 dm xs zs (by simpa using h)]

theorem cancel_r2 (LG LF C1 : Int) : ∀ Xs Zs : List Int, Xs.length = Zs.length →
    cancelPseudoLeading LG C1 (cancelPseudoLeading LG LF Xs Zs.tail) Zs = r2 LG LF C1 Xs Zs
  | [], _, _ => by simp [cancelPseudoLeading, r2]
  | _ :: _, [], h => by simp at h
  | X :: Xs, Z :: Zs, h => by
    have ih := cancel_r2 LG LF C1 Xs Zs (by simpa using h)
    cases Zs with
    | nil =>
      cases Xs with
      | nil => simp [cancelPseudoLeading, r2]
      | cons _ _ => simp at h
    | cons Z' Zs' =>
      simp only [List.tail_cons] at ih ⊢
      simp only [cancelPseudoLeading, r2, List.headD_cons]
      rw [← ih]

theorem exactDivide_map (D : Int) (hD : D ≠ 0) : ∀ Qs : List Int,
    exactDividePolynomial D (Qs.map (fun q => q * D)) = some Qs
  | [] => rfl
  | q :: Qs => by
    simp only [List.map_cons, exactDividePolynomial]
    rw [exactDivide_map D hD Qs]
    simp [hD, Int.mul_emod_left, Int.mul_ediv_cancel _ hD]

/-! ## One normal step of the specification's PRS -/

theorem trim_cons (c : Int) (cs : List Int) (h : c ≠ 0) : trimLeading (c :: cs) = c :: cs := by
  cases c using Int.rec with
  | ofNat n => cases n with
    | zero => exact absurd rfl h
    | succ k => rfl
  | negSucc k => rfl

theorem cancel_length (a b : Int) : ∀ xs ys : List Int,
    (cancelPseudoLeading a b xs ys).length = xs.length
  | [], _ => by simp [cancelPseudoLeading]
  | x :: xs, [] => by simp [cancelPseudoLeading, cancel_length a b xs []]
  | x :: xs, y :: ys => by simp [cancelPseudoLeading, cancel_length a b xs ys]

theorem scale_one : ∀ l : List Int, scalePolynomial 1 l = l
  | [] => rfl
  | c :: cs => by simp [scalePolynomial, scale_one cs]

theorem prem_eq (lf f1 lg z0 : Int) (xs zs : List Int)
    (hlf : lf ≠ 0) (hlg : lg ≠ 0) (hlen : xs.length = zs.length + 1)
    (hc1 : lg * f1 - lf * z0 ≠ 0)
    (hr2 : (r2 lg lf (lg * f1 - lf * z0) xs (z0 :: zs)).headD 0 ≠ 0) :
    pseudoRemainder (lf :: f1 :: xs) (lg :: z0 :: zs)
      = some (r2 lg lf (lg * f1 - lf * z0) xs (z0 :: zs)) := by
  have hR1 : cancelPseudoLeading lg lf (f1 :: xs) (z0 :: zs)
      = (lg * f1 - lf * z0) :: cancelPseudoLeading lg lf xs zs := rfl
  have hR2 : cancelPseudoLeading lg (lg * f1 - lf * z0) (cancelPseudoLeading lg lf xs zs) (z0 :: zs)
      = r2 lg lf (lg * f1 - lf * z0) xs (z0 :: zs) :=
    cancel_r2 lg lf _ xs (z0 :: zs) (by simpa using hlen)
  have hl2 : (r2 lg lf (lg * f1 - lf * z0) xs (z0 :: zs)).length = zs.length + 1 := by
    rw [← hR2, cancel_length, cancel_length]; exact hlen
  obtain ⟨r0, rt, hr⟩ : ∃ r0 rt, r2 lg lf (lg * f1 - lf * z0) xs (z0 :: zs) = r0 :: rt := by
    cases h : r2 lg lf (lg * f1 - lf * z0) xs (z0 :: zs) with
    | nil => rw [h] at hl2; simp at hl2
    | cons r0 rt => exact ⟨r0, rt, rfl⟩
  rw [hr] at hr2 hl2 hR2 ⊢
  simp only [List.headD_cons] at hr2
  unfold pseudoRemainder
  simp only [trim_cons lf _ hlf, trim_cons lg _ hlg, List.isEmpty_cons, Bool.false_eq_true,
    if_false, List.length_cons]
  rw [if_neg (by omega), show xs.length + 1 + 1 - (zs.length + 1 + 1) + 1 = 2 by omega]
  -- three pseudo-division iterations
  rw [show xs.length + 1 + 1 + 1 = (zs.length + 3) + 1 by omega]
  simp only [pseudoRemainderGo, trim_cons lf _ hlf, List.length_cons, hR1, trim_cons _ _ hc1,
    cancel_length, hR2, trim_cons _ _ hr2]
  simp [hlen, scale_one]
  simp only [List.length_cons] at hl2
  rw [if_neg (by omega), if_pos (by omega)]

theorem normal_step (fuel : Nat) (initial : Bool) (lf f1 lg : Int) (xs zs Q : List Int)
    (hlf : lf ≠ 0) (hlg : lg ≠ 0) (hlen : xs.length = zs.length) (hm : 1 ≤ zs.length)
    (hc1 : lg * f1 - lf * zs.headD 0 ≠ 0)
    (hr2 : (r2 lg lf (lg * f1 - lf * zs.headD 0) xs zs).headD 0 ≠ 0)
    (hdiv : (if initial then some (r2 lg lf (lg * f1 - lf * zs.headD 0) xs zs)
      else exactDividePolynomial (lf ^ 2) (r2 lg lf (lg * f1 - lf * zs.headD 0) xs zs)) = some Q)
    (hq0 : Q.headD 0 ≠ 0) (hQlen : Q.length = zs.length) :
    normalResultantGo (fuel + 1) initial (lf :: f1 :: xs) (lg :: zs) =
      if zs.length = 1 then some (Q.headD 0) else normalResultantGo fuel false (lg :: zs) Q := by
  obtain ⟨z0, zs', rfl⟩ : ∃ z0 zs', zs = z0 :: zs' := by
    cases zs with
    | nil => simp at hm
    | cons z0 zs' => exact ⟨z0, zs', rfl⟩
  obtain ⟨q0, Qt, rfl⟩ : ∃ q0 Qt, Q = q0 :: Qt := by
    cases Q with
    | nil => simp at hQlen
    | cons q0 Qt => exact ⟨q0, Qt, rfl⟩
  simp only [List.headD_cons] at hc1 hr2 hdiv hq0 ⊢
  simp only [List.length_cons] at hlen hQlen ⊢
  rw [normalResultantGo.eq_def]
  simp only
  rw [prem_eq lf f1 lg z0 xs zs' hlf hlg hlen hc1 hr2]
  simp only [List.headD_cons]
  rw [hdiv]
  simp only [trim_cons _ _ hq0, List.length_cons]
  rw [if_pos (by simp; omega)]
  cases Qt with
  | nil =>
    simp only [List.length_nil] at hQlen
    rw [if_pos (by omega)]
  | cons q1 Qt' =>
    rw [if_neg (by simp at hQlen; omega)]

/-! ## The encoded run follows the specification -/

theorem zdec_ne (z : Nat) (h : 1 ≤ z / 2) : zdec z ≠ 0 := by
  unfold zdec; split <;> omega

theorem zdec_ne' (z : Nat) (h : zdec z ≠ 0) : 1 ≤ z / 2 := by
  unfold zdec at h; split at h <;> omega

theorem run_snd_ge : ∀ k F G bad, bad ≤ (run k F G bad).2
  | 0, _, _, _ => by simp [run]
  | k + 1, F, G, bad => by
    simp only [run]
    have := run_snd_ge k G (stepQ (dmOf F) F G) (Nat.add bad (stepBad (dmOf F) F G))
    have h2 : bad ≤ Nat.add bad (stepBad (dmOf F) F G) := Nat.le_add_right _ _
    omega

theorem sm_eq (mA mC sC m1 s1 dm : Nat) : ∀ xs zs : List Nat,
    sm mA mC sC m1 s1 xs zs = dm * sq mA mC sC m1 s1 dm xs zs + rs mA mC sC m1 s1 dm xs zs
  | x :: xs, z :: zs => by
    have ih := sm_eq mA mC sC m1 s1 dm xs zs
    simp only [sm, sq, rs, zr]
    generalize zMag (eT mA mC m1 x (zs.headD 0) z) (eN mA mC sC m1 s1 x (zs.headD 0) z) = m
    generalize sm mA mC sC m1 s1 xs zs = S at ih
    generalize sq mA mC sC m1 s1 dm xs zs = Q at ih
    generalize rs mA mC sC m1 s1 dm xs zs = R at ih
    have h1 : m / dm * dm ≤ m := Nat.div_mul_le_self m dm
    show m + S = dm * (m / dm + Q) + (m - m / dm * dm + R)
    rw [Nat.mul_add, Nat.mul_comm dm (m / dm)]
    omega
  | [], _ => by simp [sm, sq, rs]
  | _ :: _, [] => by simp [sm, sq, rs]

/-- The aggregated check is the sum of the remainders. -/
theorem agg_eq_rs (mA mC sC m1 s1 dm : Nat) (xs zs : List Nat) :
    Nat.sub (sm mA mC sC m1 s1 xs zs) (Nat.mul dm (sq mA mC sC m1 s1 dm xs zs))
      = rs mA mC sC m1 s1 dm xs zs := by
  rw [sm_eq mA mC sC m1 s1 dm xs zs]
  show dm * sq mA mC sC m1 s1 dm xs zs + rs mA mC sC m1 s1 dm xs zs - dm * sq mA mC sC m1 s1 dm xs zs = _
  omega

/-- One encoded step, in the form consumed by `normal_step`. -/
theorem step_facts (initial : Bool) (dm : Nat) (lf f1 lg : Nat) (xs zs : List Nat)
    (hdm : (dm : Int) = if initial then 1 else zdec lf ^ 2)
    (hlf : zdec lf ≠ 0) (hlen : xs.length = zs.length)
    (hbad : stepBad dm (lf :: f1 :: xs) (lg :: zs) = 0) :
    let Q := stepQ dm (lf :: f1 :: xs) (lg :: zs)
    zdec lg * zdec f1 - zdec lf * (zs.map zdec).headD 0 ≠ 0 ∧
    (r2 (zdec lg) (zdec lf) (zdec lg * zdec f1 - zdec lf * (zs.map zdec).headD 0)
      (xs.map zdec) (zs.map zdec)).headD 0 ≠ 0 ∧
    (if initial then some (r2 (zdec lg) (zdec lf) (zdec lg * zdec f1 - zdec lf * (zs.map zdec).headD 0)
        (xs.map zdec) (zs.map zdec))
      else exactDividePolynomial (zdec lf ^ 2) (r2 (zdec lg) (zdec lf)
        (zdec lg * zdec f1 - zdec lf * (zs.map zdec).headD 0) (xs.map zdec) (zs.map zdec)))
      = some (Q.map zdec) ∧
    (Q.map zdec).headD 0 ≠ 0 ∧ (Q.map zdec).length = zs.length := by
  intro Q
  unfold stepBad at hbad
  simp only [nadd, nsub] at hbad
  have hc1 : zdec (cOne (lf :: f1 :: xs) (lg :: zs)) = zdec lg * zdec f1 - zdec lf * (zs.map zdec).headD 0 := by
    unfold cOne; rw [zlin_val, headD_map]; rfl
  have hR0 : stepR dm (lf :: f1 :: xs) (lg :: zs) = 0 := by omega
  have hR := agg_eq_rs (Nat.mul (Nat.shiftRight lg 1) (Nat.shiftRight lg 1))
    (Nat.mul (Nat.shiftRight lg 1) (Nat.shiftRight lf 1))
    (Nat.xor (Nat.land (Nat.xor lg lf) 1) 1) (Nat.shiftRight (cOne (lf :: f1 :: xs) (lg :: zs)) 1)
    (Nat.xor (Nat.land (cOne (lf :: f1 :: xs) (lg :: zs)) 1) 1) dm xs zs
  rw [show Nat.sub (sm (Nat.mul (Nat.shiftRight lg 1) (Nat.shiftRight lg 1))
      (Nat.mul (Nat.shiftRight lg 1) (Nat.shiftRight lf 1))
      (Nat.xor (Nat.land (Nat.xor lg lf) 1) 1) (Nat.shiftRight (cOne (lf :: f1 :: xs) (lg :: zs)) 1)
      (Nat.xor (Nat.land (cOne (lf :: f1 :: xs) (lg :: zs)) 1) 1) xs zs)
      (Nat.mul dm (sq (Nat.mul (Nat.shiftRight lg 1) (Nat.shiftRight lg 1))
      (Nat.mul (Nat.shiftRight lg 1) (Nat.shiftRight lf 1))
      (Nat.xor (Nat.land (Nat.xor lg lf) 1) 1) (Nat.shiftRight (cOne (lf :: f1 :: xs) (lg :: zs)) 1)
      (Nat.xor (Nat.land (cOne (lf :: f1 :: xs) (lg :: zs)) 1) 1) dm xs zs)) = 0 from hR0] at hR
  have hq := qs_val lg lf (cOne (lf :: f1 :: xs) (lg :: zs)) dm xs zs hlen hR.symm
  rw [hc1] at hq
  have hQ : Q = qs _ _ _ _ _ dm xs zs := rfl
  have hQlen : Q.length = xs.length := by rw [hQ]; exact qs_length _ _ _ _ _ _ _ _ hlen
  have hdm0 : (dm : Int) ≠ 0 := by
    rw [hdm]; split
    · decide
    · exact Int.pow_ne_zero hlf
  have hR2 : r2 (zdec lg) (zdec lf) (zdec lg * zdec f1 - zdec lf * (zs.map zdec).headD 0)
      (xs.map zdec) (zs.map zdec) = (Q.map zdec).map (fun q => q * (dm : Int)) := by
    rw [← hq, List.map_map]; rfl
  have hq0 : (Q.map zdec).headD 0 ≠ 0 := by
    rw [headD_map]; apply zdec_ne
    have h3 : 1 - Nat.shiftRight ((stepQ dm (lf :: f1 :: xs) (lg :: zs)).headD 0) 1 = 0 := by omega
    rw [shr1] at h3
    show 1 ≤ (stepQ dm (lf :: f1 :: xs) (lg :: zs)).headD 0 / 2
    omega
  refine ⟨?_, ?_, ?_, hq0, ?_⟩
  · rw [← hc1]; apply zdec_ne
    have : 1 - Nat.shiftRight (cOne (lf :: f1 :: xs) (lg :: zs)) 1 = 0 := by omega
    rw [shr1] at this; omega
  · rw [hR2]
    cases h : Q.map zdec with
    | nil => rw [h] at hq0; simp at hq0
    | cons a l =>
      rw [h] at hq0
      simp only [List.map_cons, List.headD_cons] at hq0 ⊢
      exact Int.mul_ne_zero hq0 hdm0
  · rw [hR2]
    cases initial
    · simp only [Bool.false_eq_true, if_false] at hdm ⊢
      rw [hdm]
      exact exactDivide_map _ (Int.pow_ne_zero hlf) _
    · simp only [if_true] at hdm ⊢
      rw [hdm]; simp
  · rw [List.length_map, hQlen, hlen]

theorem dmOf_eq (lf : Nat) (F : List Nat) : ((dmOf (lf :: F) : Nat) : Int) = zdec lf ^ 2 := by
  unfold dmOf
  simp only [List.headD_cons, shr1, nmul]
  rw [sq_eq, Int.pow_succ, Int.pow_one]

/-- The encoded run computes the specification's normal PRS continuation. -/
theorem run_spec : ∀ k (F G : List Nat) (bad fuel : Nat), 1 ≤ k → G.length = k + 1 →
    F.length = k + 2 → k ≤ fuel → (F.map zdec).headD 0 ≠ 0 → (G.map zdec).headD 0 ≠ 0 →
    (run k F G bad).2 = 0 →
    normalResultantGo fuel false (F.map zdec) (G.map zdec) = some (zdec (run k F G bad).1)
  | 0, _, _, _, _, hk, _, _, _, _, _, _ => absurd hk (by omega)
  | k + 1, F, G, bad, fuel, _, hG, hF, hfuel, hf0, hg0, hrun => by
    obtain ⟨lf, f1, xs, rfl⟩ : ∃ lf f1 xs, F = lf :: f1 :: xs := by
      match F, hF with
      | lf :: f1 :: xs, _ => exact ⟨lf, f1, xs, rfl⟩
    obtain ⟨lg, zs, rfl⟩ : ∃ lg zs, G = lg :: zs := by
      match G, hG with
      | lg :: zs, _ => exact ⟨lg, zs, rfl⟩
    simp only [List.length_cons] at hF hG
    simp only [List.map_cons, List.headD_cons] at hf0 hg0
    have hrun' := hrun
    simp only [run] at hrun'
    have hge := run_snd_ge k (lg :: zs) (stepQ (dmOf (lf :: f1 :: xs)) (lf :: f1 :: xs) (lg :: zs))
      (Nat.add bad (stepBad (dmOf (lf :: f1 :: xs)) (lf :: f1 :: xs) (lg :: zs)))
    have hbad : stepBad (dmOf (lf :: f1 :: xs)) (lf :: f1 :: xs) (lg :: zs) = 0 := by
      rw [hrun'] at hge; simp only [nadd] at hge; omega
    obtain ⟨h1, h2, h3, h4, h5⟩ := step_facts false (dmOf (lf :: f1 :: xs)) lf f1 lg xs zs
      (by rw [dmOf_eq]; rfl) hf0 (by omega) hbad
    obtain ⟨fuel', rfl⟩ : ∃ fuel', fuel = fuel' + 1 := ⟨fuel - 1, by omega⟩
    simp only [List.map_cons]
    rw [normal_step fuel' false (zdec lf) (zdec f1) (zdec lg) (xs.map zdec) (zs.map zdec) _ hf0 hg0
      (by simp; omega) (by simp; omega) h1 h2 h3 h4 (by rw [h5, List.length_map])]
    simp only [List.length_map]
    by_cases hk : k = 0
    · subst hk
      rw [if_pos (by omega)]
      simp only [run, headD_map]
    · rw [if_neg (by omega)]
      simp only [run]
      exact run_spec k (lg :: zs) _ _ fuel' (by omega)
        (by rw [List.length_map] at h5; omega)
        (by simp; omega) (by omega) (by simpa using hg0) h4 hrun'

theorem runAll_spec (F G : List Nat) (hF : F.length = 25) (hG : G.length = 24)
    (hf0 : (F.map zdec).headD 0 ≠ 0) (hg0 : (G.map zdec).headD 0 ≠ 0) (h : (runAll F G).2 = 0) :
    normalResultant (F.map zdec) (G.map zdec) = some (zdec (runAll F G).1) := by
  obtain ⟨lf, f1, xs, rfl⟩ : ∃ lf f1 xs, F = lf :: f1 :: xs := by
    match F, hF with
    | lf :: f1 :: xs, _ => exact ⟨lf, f1, xs, rfl⟩
  obtain ⟨lg, zs, rfl⟩ : ∃ lg zs, G = lg :: zs := by
    match G, hG with
    | lg :: zs, _ => exact ⟨lg, zs, rfl⟩
  simp only [List.length_cons] at hF hG
  simp only [List.map_cons, List.headD_cons] at hf0 hg0
  have hge := run_snd_ge 22 (lg :: zs) (stepQ 1 (lf :: f1 :: xs) (lg :: zs))
    (stepBad 1 (lf :: f1 :: xs) (lg :: zs))
  have hbad : stepBad 1 (lf :: f1 :: xs) (lg :: zs) = 0 := by
    unfold runAll at h; omega
  obtain ⟨h1, h2, h3, h4, h5⟩ := step_facts true 1 lf f1 lg xs zs (by simp) hf0 (by omega) hbad
  unfold normalResultant
  simp only [List.map_cons, trim_cons _ _ hf0, trim_cons _ _ hg0, List.length_cons, List.length_map,
    List.isEmpty_cons]
  rw [if_pos (by simp; omega), show zs.length + 1 + 1 = 24 + 1 by omega]
  rw [normal_step 24 true (zdec lf) (zdec f1) (zdec lg) (xs.map zdec) (zs.map zdec) _ hf0 hg0
    (by simp; omega) (by simp; omega) h1 h2 h3 h4 (by rw [h5, List.length_map])]
  simp only [List.length_map]
  rw [if_neg (by omega)]
  unfold runAll at h ⊢
  exact run_spec 22 (lg :: zs) _ _ 24 (by omega) (by rw [List.length_map] at h5; omega)
    (by simp; omega) (by omega) (by simpa using hg0) h4 h


/-! ## The graph is the structured run -/

/-- Statement of `prsDag_eq`. -/
def PrsDagEq : Prop := ∀ f0 f1 f2 f3 f4 f5 f6 f7 f8 f9 f10 f11 f12 f13 f14 f15 f16 f17 f18 f19 f20 f21 f22 f23 f24 g0 g1 g2 g3 g4 g5 g6 g7 g8 g9 g10 g11 g12 g13 g14 g15 g16 g17 g18 g19 g20 g21 g22 g23 : Nat, prsDag f0 f1 f2 f3 f4 f5 f6 f7 f8 f9 f10 f11 f12 f13 f14 f15 f16 f17 f18 f19 f20 f21 f22 f23 f24 g0 g1 g2 g3 g4 g5 g6 g7 g8 g9 g10 g11 g12 g13 g14 g15 g16 g17 g18 g19 g20 g21 g22 g23 = runAll [f0, f1, f2, f3, f4, f5, f6, f7, f8, f9, f10, f11, f12, f13, f14, f15, f16, f17, f18, f19, f20, f21, f22, f23, f24] [g0, g1, g2, g3, g4, g5, g6, g7, g8, g9, g10, g11, g12, g13, g14, g15, g16, g17, g18, g19, g20, g21, g22, g23]

open Lean Elab Term Command Meta in
/- `prsDag_eq : PrsDagEq`, proved by `rfl`. The definitional unfolding is checked by the kernel
directly (the elaborator's unifier is far slower on this graph). -/
run_cmd liftTermElabM do
  let ty ← instantiateMVars (← elabTerm (← `(PrsDagEq)) none)
  let pf ← instantiateMVars (← elabTerm (← `(fun (f0 f1 f2 f3 f4 f5 f6 f7 f8 f9 f10 f11 f12 f13 f14 f15 f16 f17 f18 f19 f20 f21 f22 f23 f24 g0 g1 g2 g3 g4 g5 g6 g7 g8 g9 g10 g11 g12 g13 g14 g15 g16 g17 g18 g19 g20 g21 g22 g23 : Nat) =>
    @rfl (Nat × Nat) (prsDag f0 f1 f2 f3 f4 f5 f6 f7 f8 f9 f10 f11 f12 f13 f14 f15 f16 f17 f18 f19 f20 f21 f22 f23 f24 g0 g1 g2 g3 g4 g5 g6 g7 g8 g9 g10 g11 g12 g13 g14 g15 g16 g17 g18 g19 g20 g21 g22 g23))) none)
  addDecl (.thmDecl { name := `Submission.prsDag_eq, levelParams := [], type := ty, value := pf })


/-! ## The generator -/

theorem lcgRaw_eq (st : Nat) : lcgRaw st = lcgNext st := by
  unfold lcgRaw lcgNext lcgA lcgC lcgM
  have h : ∀ x : Nat, Nat.land x 18446744073709551615 = x % 18446744073709551616 := fun x => by
    rw [nand, show (18446744073709551615 : Nat) = 2 ^ 64 - 1 by decide,
      Nat.and_two_pow_sub_one_eq_mod]
  rw [h, nadd, nmul, Nat.add_comm]

theorem lcg_lt (st : Nat) : lcgNext st < 2 ^ 64 := by
  unfold lcgNext lcgM; exact Nat.mod_lt _ (by decide)

theorem collect_succ (n sh st : Nat) : collectCoeffWord (n + 1) sh st =
    (lcgNext st * 2 ^ sh + (collectCoeffWord n (sh + 64) (lcgNext st)).1,
      (collectCoeffWord n (sh + 64) (lcgNext st)).2) := by
  rw [collectCoeffWord]

theorem wl_eq : ∀ n acc sh st, wl n acc sh st = acc + (collectCoeffWord n sh st).1
  | 0, acc, sh, st => by
    show acc = acc + (collectCoeffWord 0 sh st).1
    simp [collectCoeffWord]
  | n + 1, acc, sh, st => by
    show wl n (Nat.add acc (Nat.shiftLeft (lcgRaw st) sh)) (Nat.add sh 64) (lcgRaw st) = _
    rw [wl_eq n, collect_succ, lcgRaw_eq, nadd, nadd, nshl, Nat.shiftLeft_eq]
    simp only
    omega

theorem collect_dvd : ∀ n sh st, 2 ^ sh ∣ (collectCoeffWord n sh st).1
  | 0, sh, st => by simp [collectCoeffWord]
  | n + 1, sh, st => by
    rw [collect_succ]
    simp only
    apply Nat.dvd_add (Nat.dvd_mul_left _ _)
    exact Nat.dvd_trans (Nat.pow_dvd_pow 2 (by omega)) (collect_dvd n (sh + 64) _)

theorem collect_lt : ∀ n sh st, (collectCoeffWord n sh st).1 < 2 ^ (sh + 64 * n) ∨ n = 0
  | 0, _, _ => Or.inr rfl
  | n + 1, sh, st => by
    left
    rw [collect_succ]
    simp only
    have h1 := lcg_lt st
    rcases collect_lt n (sh + 64) (lcgNext st) with h | h
    · obtain ⟨t, ht⟩ := collect_dvd n (sh + 64) (lcgNext st)
      rw [ht] at h ⊢
      have e1 : 2 ^ (sh + 64 * (n + 1)) = 2 ^ (sh + 64) * 2 ^ (64 * n) := by
        rw [← Nat.pow_add]; congr 1; omega
      have e2 : 2 ^ (sh + 64 + 64 * n) = 2 ^ (sh + 64) * 2 ^ (64 * n) := by rw [Nat.pow_add]
      rw [e2] at h
      rw [e1]
      have ht' : t < 2 ^ (64 * n) := Nat.lt_of_mul_lt_mul_left h
      have e3 : 2 ^ (sh + 64) = 2 ^ sh * 2 ^ 64 := Nat.pow_add _ _ _
      have hp : 0 < 2 ^ sh := Nat.two_pow_pos _
      calc lcgNext st * 2 ^ sh + 2 ^ (sh + 64) * t
          < 2 ^ 64 * 2 ^ sh + 2 ^ (sh + 64) * t := by
            have := Nat.mul_lt_mul_of_pos_right h1 hp; omega
        _ = 2 ^ (sh + 64) * (t + 1) := by rw [e3, Nat.mul_add, Nat.mul_one, Nat.mul_comm (2 ^ sh)]; omega
        _ ≤ 2 ^ (sh + 64) * 2 ^ (64 * n) := Nat.mul_le_mul_left _ ht'
    · subst h
      simp only [collectCoeffWord, Nat.add_zero]
      have hp : 0 < 2 ^ sh := Nat.two_pow_pos _
      rw [Nat.pow_add, show 64 * (0 + 1) = 64 by rfl, Nat.mul_comm (2 ^ sh)]
      exact Nat.mul_lt_mul_of_pos_right h1 hp

theorem shr_low (a T B K : Nat) (ha : a < 2 ^ B) (hT : 2 ^ B ∣ T) :
    (a + T) >>> (B + K) = T >>> (B + K) := by
  obtain ⟨t, rfl⟩ := hT
  rw [Nat.shiftRight_eq_div_pow, Nat.shiftRight_eq_div_pow, Nat.pow_add, ← Nat.div_div_eq_div_mul,
    ← Nat.div_div_eq_div_mul, Nat.add_comm, Nat.mul_add_div (Nat.two_pow_pos _),
    Nat.div_eq_of_lt ha, Nat.add_zero, Nat.mul_div_cancel_left _ (Nat.two_pow_pos _)]

/-- The last LCG state is the top 64-bit digit of the collected word. -/
theorem collect_top : ∀ n sh st,
    (collectCoeffWord (n + 1) sh st).1 >>> (sh + 64 * n) = (collectCoeffWord (n + 1) sh st).2
  | 0, sh, st => by
    rw [collect_succ]
    simp only [collectCoeffWord, Nat.add_zero, Nat.mul_zero, Nat.shiftRight_eq_div_pow]
    exact Nat.mul_div_cancel _ (Nat.two_pow_pos _)
  | n + 1, sh, st => by
    rw [collect_succ (n + 1) sh st]
    simp only
    have ih := collect_top n (sh + 64) (lcgNext st)
    have hd := collect_dvd (n + 1) (sh + 64) (lcgNext st)
    have h1 := lcg_lt st
    generalize collectCoeffWord (n + 1) (sh + 64) (lcgNext st) = P at ih hd ⊢
    generalize lcgNext st = s at h1 ⊢
    have hlt : s * 2 ^ sh < 2 ^ (sh + 64) := by
      rw [Nat.pow_add, Nat.mul_comm (2 ^ sh)]
      exact Nat.mul_lt_mul_of_pos_right h1 (Nat.two_pow_pos _)
    rw [show sh + 64 * (n + 1) = (sh + 64) + 64 * n by omega, shr_low _ _ _ _ hlt hd, ih]

theorem encC_eq (w words word : Nat) : zdec (encC w words word) = centeredNonzeroCoeff w words word := by
  unfold encC centeredNonzeroCoeff
  simp only [nadd, nsub, nshl, nmul, nshr]
  generalize word >>> (64 * words - w) = v
  rw [Nat.one_shiftLeft]
  generalize 2 ^ (w - 1) = h
  rw [Nat.shiftLeft_eq, Nat.shiftLeft_eq, Nat.pow_one]
  unfold zdec
  rcases Nat.lt_trichotomy v h with hv | hv | hv
  · rw [show v - h = 0 by omega, show (1 : Nat) - (1 - (h - v)) = 1 by omega,
      show (1 : Nat) - (0 + (h - v)) = 0 by omega]
    rw [if_pos (by omega), if_neg (by simp; omega)]
    simp only [Int.ofNat_eq_natCast]
    omega
  · subst hv
    simp
  · rw [show h - v = 0 by omega, show (1 : Nat) - (1 - 0) = 0 by omega,
      show (1 : Nat) - (v - h + 0) = 0 by omega]
    rw [if_neg (by omega), if_neg (by simp; omega)]
    simp only [Int.ofNat_eq_natCast]
    omega

theorem clampRaw_eq (k w : Nat) : clampRaw k w = clampWidth k w := by
  unfold clampRaw clampWidth
  simp only [nadd, nsub, Nat.min_def, Nat.max_def]
  split <;> split <;> omega

theorem wRaw_eq (k i : Nat) : wRaw k i = coefficientWidth k i := by
  unfold wRaw coefficientWidth
  rcases Nat.lt_or_ge 64 k with h | h
  · obtain ⟨j, hj⟩ : ∃ j, Nat.sub k 64 = j + 1 := ⟨k - 65, by show k - 64 = _; omega⟩
    rw [hj, if_neg (by omega)]
    simp only
    rw [clampRaw_eq]
    congr 1
  · rw [show Nat.sub k 64 = 0 by show k - 64 = 0; omega, if_pos h]
    simp only
    rw [clampRaw_eq]
    rfl

theorem width_ge (k i : Nat) (hk : 2 ≤ k) : 2 ≤ coefficientWidth k i := by
  unfold coefficientWidth clampWidth
  split <;> simp only [Nat.min_def, Nat.max_def] <;> split <;> split <;> omega

theorem genGo_spec (k : Nat) (hk : 2 ≤ k) : ∀ count index state,
    (genGo k count index state).map zdec = coefficientsFrom count k index state
  | 0, _, _ => by
    show ([] : List Nat).map zdec = _
    simp [coefficientsFrom]
  | count + 1, index, state => by
    have hw := width_ge k index hk
    obtain ⟨m, hm⟩ : ∃ m, (coefficientWidth k index + 63) / 64 = m + 1 :=
      ⟨(coefficientWidth k index + 63) / 64 - 1, by omega⟩
    show (List.cons (encC (wRaw k index) (Nat.div (Nat.add (wRaw k index) 63) 64)
        (wl (Nat.div (Nat.add (wRaw k index) 63) 64) 0 0 state))
      (genGo k count (Nat.add index 1) (Nat.shiftRight (wl (Nat.div (Nat.add (wRaw k index) 63) 64) 0 0 state)
        (Nat.mul 64 (Nat.sub (Nat.div (Nat.add (wRaw k index) 63) 64) 1))))).map zdec = _
    rw [List.map_cons, genGo_spec k hk count, wRaw_eq, encC_eq]
    simp only [nadd, ndiv, nmul, nsub, nshr]
    rw [hm, wl_eq, Nat.zero_add, Nat.add_sub_cancel, show 64 * m = 0 + 64 * m by omega,
      collect_top]
    rw [coefficientsFrom]
    simp only [hm]

theorem kbits_ge (n : Nat) : 2 ≤ kbitsOf n := by
  unfold kbitsOf; split <;> omega

theorem genF_spec (n : Nat) : (genF n).map zdec = polyOf n := by
  unfold genF polyOf
  rw [List.map_cons, genGo_spec _ (kbits_ge n)]
  rfl

theorem genGo_length (k : Nat) : ∀ count index state, (genGo k count index state).length = count
  | 0, _, _ => rfl
  | count + 1, index, state => by
    show (List.cons _ (genGo k count _ _)).length = _
    rw [List.length_cons, genGo_length k count]

theorem gz_val (f k : Nat) : zdec (gz f k) = (k : Int) * zdec f := by
  unfold gz
  simp only [nadd, nmul, nshl, nand, shr1, Nat.and_one_is_mod, Nat.shiftLeft_eq, Nat.pow_one]
  rw [zdec_sg (f / 2 * k * 2 + f % 2), zdec_sg f]
  rw [show (f / 2 * k * 2 + f % 2) % 2 = f % 2 by omega,
    show (f / 2 * k * 2 + f % 2) / 2 = f / 2 * k by omega]
  push_cast
  ac_rfl

/-! ## Main correctness -/

theorem deriv_spec (f0 f1 f2 f3 f4 f5 f6 f7 f8 f9 f10 f11 f12 f13 f14 f15 f16 f17 f18 f19 f20 f21 f22 f23 f24 : Nat) :
    [gz f0 24, gz f1 23, gz f2 22, gz f3 21, gz f4 20, gz f5 19, gz f6 18, gz f7 17, gz f8 16, gz f9 15, gz f10 14, gz f11 13, gz f12 12, gz f13 11, gz f14 10, gz f15 9, gz f16 8, gz f17 7, gz f18 6, gz f19 5, gz f20 4, gz f21 3, gz f22 2, gz f23 1].map zdec = derivHL ([f0, f1, f2, f3, f4, f5, f6, f7, f8, f9, f10, f11, f12, f13, f14, f15, f16, f17, f18, f19, f20, f21, f22, f23, f24].map zdec) := by
  simp only [List.map_cons, List.map_nil, gz_val]
  rfl

theorem disc_eq (p : List Int) (hp : p.length = 25) (r : Int)
    (h : normalResultant p (derivHL p) = some r) : discriminantFromPoly p = r := by
  simp only [discriminantFromPoly, resultantFromPoly, hp, h]
  simp

theorem div_succ_of_le {n t : Nat} (ht : 0 < t) (h : t ≤ n) : ∃ m, Nat.div n t = m + 1 :=
  ⟨n / t - 1, by
    have : 1 ≤ n / t := (Nat.le_div_iff_mul_le ht).2 (by omega)
    show n / t = _
    omega⟩


/-! ## Lane-parallel generation

All LCG states are computed at once by jump-ahead: state `j` is `(a_j·s + c_j) mod 2^64` with
literal `a_j, c_j`. The states with even `j` sit in 128-bit lanes of one number (`pkA`, `pkC`), the odd
ones in another (shifted by 64 bits); one product, one sum and one mask per pack give every state
(`lanes`), and the two packs together are the whole stream `s + 2^64·strm W s` (`interleave`).
Each coefficient is then read off with one shift and one mask (`extZ`). -/

theorem npow (a b : Nat) : Nat.pow a b = a ^ b := rfl

section lanes
-- `lcgNext` (a `%` of a sum with a literal) must not be unfolded by the unifier.
attribute [local irreducible] lcgNext

/-- `n` LCG words after `st`, little-endian in 64-bit words. -/
def strm : Nat → Nat → Nat
  | 0, _ => 0
  | n + 1, st => lcgNext st + 2 ^ 64 * strm n (lcgNext st)

/-- The state `n` LCG steps after `st`. -/
def lcgIt (st : Nat) : Nat → Nat
  | 0 => st
  | n + 1 => lcgIt (lcgNext st) n

theorem strm_zero (st : Nat) : strm 0 st = 0 := rfl
theorem strm_succ (n st : Nat) : strm (n + 1) st = lcgNext st + 2 ^ 64 * strm n (lcgNext st) := rfl
theorem lcgIt_zero (st : Nat) : lcgIt st 0 = st := rfl
theorem lcgIt_succ (st n : Nat) : lcgIt st (n + 1) = lcgIt (lcgNext st) n := rfl

theorem collect_eq : ∀ n sh st, collectCoeffWord n sh st = (strm n st * 2 ^ sh, lcgIt st n)
  | 0, sh, st => by
    rw [collectCoeffWord, strm_zero, lcgIt_zero, Nat.zero_mul]
  | n + 1, sh, st => by
    rw [collect_succ, collect_eq n (sh + 64) (lcgNext st), strm_succ, lcgIt_succ, Nat.pow_add]
    congr 1
    rw [Nat.add_mul, Nat.mul_comm (2 ^ 64), Nat.mul_assoc, Nat.mul_comm (2 ^ 64)]

theorem lcgIt_add : ∀ a b st, lcgIt st (a + b) = lcgIt (lcgIt st a) b
  | 0, b, st => by rw [Nat.zero_add, lcgIt_zero]
  | a + 1, b, st => by
    rw [Nat.add_right_comm, lcgIt_succ, lcgIt_succ]
    exact lcgIt_add a b (lcgNext st)

theorem lcgIt_succ' (st n : Nat) : lcgIt st (n + 1) = lcgNext (lcgIt st n) := by
  rw [lcgIt_add n 1, lcgIt_succ, lcgIt_zero]

theorem strm_lt : ∀ n st, strm n st < 2 ^ (64 * n)
  | 0, _ => by rw [strm_zero]; exact Nat.two_pow_pos _
  | n + 1, st => by
    have h1 := lcg_lt st
    have h2 := strm_lt n (lcgNext st)
    rw [strm_succ, show 64 * (n + 1) = 64 + 64 * n by omega, Nat.pow_add]
    have h3 := Nat.mul_le_mul_left (2 ^ 64) (Nat.succ_le_of_lt h2)
    rw [Nat.mul_succ] at h3
    omega

theorem strm_add : ∀ a b st, strm (a + b) st = strm a st + 2 ^ (64 * a) * strm b (lcgIt st a)
  | 0, b, st => by
    rw [Nat.zero_add, strm_zero, lcgIt_zero, Nat.mul_zero, Nat.pow_zero, Nat.one_mul, Nat.zero_add]
  | a + 1, b, st => by
    rw [Nat.add_right_comm, strm_succ, strm_succ, lcgIt_succ, strm_add a b (lcgNext st),
      show 64 * (a + 1) = 64 + 64 * a by omega, Nat.pow_add, Nat.mul_add, Nat.mul_assoc]
    omega

theorem strm_window (s W t words : Nat) (h : t + words ≤ W) :
    (strm W s >>> (64 * t)) % 2 ^ (64 * words) = strm words (lcgIt s t) := by
  obtain ⟨r, rfl⟩ : ∃ r, W = t + (words + r) := ⟨W - t - words, by omega⟩
  rw [strm_add, strm_add words r]
  rw [Nat.shiftRight_eq_div_pow, Nat.add_comm (strm t s), Nat.mul_add_div (Nat.two_pow_pos _),
    Nat.div_eq_of_lt (strm_lt t s), Nat.add_zero, Nat.add_mul_mod_self_left,
    Nat.mod_eq_of_lt (strm_lt words _)]

theorem shr_dummy (s X t : Nat) (hs : s < 2 ^ 64) :
    (s + 2 ^ 64 * X) >>> (64 * (t + 1)) = X >>> (64 * t) := by
  rw [Nat.shiftRight_eq_div_pow, Nat.shiftRight_eq_div_pow, show 64 * (t + 1) = 64 + 64 * t by omega,
    Nat.pow_add, ← Nat.div_div_eq_div_mul, Nat.add_comm, Nat.mul_add_div (by decide),
    Nat.div_eq_of_lt hs, Nat.add_zero]

theorem strm_top (m st : Nat) : strm (m + 1) st >>> (64 * m) = lcgIt st (m + 1) := by
  rw [strm_add m 1, strm_succ, strm_zero, Nat.mul_zero, Nat.add_zero, Nat.shiftRight_eq_div_pow,
    Nat.add_comm, Nat.mul_add_div (Nat.two_pow_pos _), Nat.div_eq_of_lt (strm_lt m st), Nat.add_zero,
    lcgIt_succ']

theorem genGo_succ (k : Nat) (hk : 2 ≤ k) (count index state : Nat) : genGo k (count + 1) index state =
    encC (wRaw k index) ((wRaw k index + 63) / 64) (strm ((wRaw k index + 63) / 64) state) ::
      genGo k count (index + 1) (lcgIt state ((wRaw k index + 63) / 64)) := by
  show List.cons (encC (wRaw k index) (Nat.div (Nat.add (wRaw k index) 63) 64)
        (wl (Nat.div (Nat.add (wRaw k index) 63) 64) 0 0 state))
      (genGo k count (Nat.add index 1) (Nat.shiftRight (wl (Nat.div (Nat.add (wRaw k index) 63) 64) 0 0 state)
        (Nat.mul 64 (Nat.sub (Nat.div (Nat.add (wRaw k index) 63) 64) 1)))) = _
  simp only [nadd, ndiv, nmul, nsub, nshr]
  have hw : 2 ≤ wRaw k index := by rw [wRaw_eq]; exact width_ge k index hk
  obtain ⟨m, hm⟩ : ∃ m, (wRaw k index + 63) / 64 = m + 1 := ⟨(wRaw k index + 63) / 64 - 1, by omega⟩
  rw [hm, wl_eq, Nat.zero_add, collect_eq, Nat.pow_zero, Nat.mul_one, Nat.add_sub_cancel, strm_top]

/-- Encoded coefficient from `u = 2·v`, `v` the top `w` bits of its word: `v − 2^(w−1)` encoded,
with `0 ↦ 1` (`2 + (u − (2^w + 2)) + ((2^w − 1) − u)`). -/
def encZ (w u : Nat) : Nat :=
  Nat.add 2 (Nat.add (Nat.sub u (Nat.add (Nat.pow 2 w) 2)) (Nat.sub (Nat.sub (Nat.pow 2 w) 1) u))

/-- The coefficient of width `w` whose `words`-word group starts at word `t` of `Y`. -/
def extZ (w words t Y : Nat) : Nat :=
  encZ w (Nat.land (Nat.sub (Nat.pow 2 (Nat.add w 1)) 2)
    (Nat.shiftRight Y (Nat.sub (Nat.mul 64 (Nat.add t words)) (Nat.add w 1))))

theorem mod_shr (X a b : Nat) (h : b ≤ a) : (X % 2 ^ a) >>> b = (X >>> b) % 2 ^ (a - b) := by
  apply Nat.eq_of_testBit_eq; intro i
  simp only [Nat.testBit_shiftRight, Nat.testBit_mod_two_pow]
  by_cases hi : b + i < a
  · simp [hi, show i < a - b by omega]
  · simp [hi, show ¬ i < a - b by omega]

theorem mask_two (q w : Nat) : (2 ^ (w + 1) - 2) &&& q = 2 * ((q >>> 1) % 2 ^ w) := by
  apply Nat.eq_of_testBit_eq; intro i
  rw [show 2 ^ (w + 1) - 2 = 2 ^ 1 * (2 ^ w - 1) by rw [Nat.pow_succ, Nat.mul_sub]; omega,
    show 2 * ((q >>> 1) % 2 ^ w) = 2 ^ 1 * ((q >>> 1) % 2 ^ w) by rfl]
  simp only [Nat.testBit_and, Nat.testBit_two_pow_mul, Nat.testBit_two_pow_sub_one,
    Nat.testBit_mod_two_pow, Nat.testBit_shiftRight]
  by_cases hi : 1 ≤ i
  · rw [show 1 + (i - 1) = i by omega]
    by_cases hw : i - 1 < w <;> simp [hi, hw]
  · simp [show ¬ i ≥ 1 by omega]

theorem enc_lemma (w words t Y : Nat) (hw : 1 ≤ w) (hww : w ≤ 64 * words) :
    extZ w words (t + 1) Y = encC w words ((Y >>> (64 * (t + 1))) % 2 ^ (64 * words)) := by
  unfold extZ encZ encC
  simp only [nadd, nsub, nshl, nmul, nshr, nand, npow]
  rw [mod_shr _ _ _ (by omega), ← Nat.shiftRight_add, mask_two, ← Nat.shiftRight_add,
    show 64 * (t + 1 + words) - (w + 1) + 1 = 64 * (t + 1) + (64 * words - w) by omega,
    show 64 * words - (64 * words - w) = w by omega]
  generalize (Y >>> (64 * (t + 1) + (64 * words - w))) % 2 ^ w = v
  rw [Nat.one_shiftLeft]
  have h2 : 2 ^ w = 2 * 2 ^ (w - 1) := by
    rw [← Nat.pow_succ']; congr 1; omega
  rw [h2]
  generalize 2 ^ (w - 1) = h
  rw [Nat.shiftLeft_eq, Nat.shiftLeft_eq, Nat.pow_one]
  omega

/-- `genGo` read off a precomputed stream: coefficient `index` from the word group starting at
word `t` of `Y`. -/
def genZ (k : Nat) (count : Nat) : Nat → Nat → Nat → List Nat :=
  Nat.rec (motive := fun _ => Nat → Nat → Nat → List Nat) (fun _ _ _ => List.nil)
    (fun _ ih index t Y =>
      List.cons (extZ (wRaw k index) (Nat.div (Nat.add (wRaw k index) 63) 64) t Y)
        (ih (Nat.add index 1) (Nat.add t (Nat.div (Nat.add (wRaw k index) 63) 64)) Y))
    count

/-- LCG words used by `count` coefficients from `index`. -/
def needW (k : Nat) : Nat → Nat → Nat
  | 0, _ => 0
  | c + 1, index => (wRaw k index + 63) / 64 + needW k c (index + 1)

theorem genZ_eq (k : Nat) (hk : 2 ≤ k) (s W : Nat) (hs : s < 2 ^ 64) : ∀ count index t,
    t + needW k count index ≤ W →
    genZ k count index (t + 1) (s + 2 ^ 64 * strm W s) = genGo k count index (lcgIt s t)
  | 0, _, _, _ => rfl
  | count + 1, index, t, h => by
    rw [genGo_succ k hk]
    have hw : 2 ≤ wRaw k index := by rw [wRaw_eq]; exact width_ge k index hk
    have hn : needW k (count + 1) index = (wRaw k index + 63) / 64 + needW k count (index + 1) := rfl
    show List.cons (extZ (wRaw k index) (Nat.div (Nat.add (wRaw k index) 63) 64) (t + 1) _)
      (genZ k count (Nat.add index 1) (Nat.add (t + 1) (Nat.div (Nat.add (wRaw k index) 63) 64)) _) = _
    simp only [nadd, ndiv]
    rw [enc_lemma _ _ _ _ (by omega) (by omega), shr_dummy _ _ _ hs,
      strm_window s W t _ (by omega),
      show t + 1 + (wRaw k index + 63) / 64 = (t + (wRaw k index + 63) / 64) + 1 by omega,
      genZ_eq k hk s W hs count (index + 1) (t + (wRaw k index + 63) / 64) (by omega), lcgIt_add]

/-- `A²` and `A·C + C` mod `2^64`: two LCG steps are `x ↦ A2·x + C2`. -/
def A2 : Nat := 6364136223846793005 * 6364136223846793005 % 2 ^ 64
def C2 : Nat := (6364136223846793005 * 1442695040888963407 + 1442695040888963407) % 2 ^ 64

/-- `n` lanes of 128 bits: `a, A2·a, A2²·a, …` (mod `2^64`). -/
def pkA (n : Nat) : Nat → Nat :=
  Nat.rec (motive := fun _ => Nat → Nat) (fun _ => 0)
    (fun _ ih a => a + 2 ^ 128 * ih (A2 * a % 2 ^ 64)) n

/-- `n` lanes of 128 bits: `c, A2·c + C2, …` (mod `2^64`). -/
def pkC (n : Nat) : Nat → Nat :=
  Nat.rec (motive := fun _ => Nat → Nat) (fun _ => 0)
    (fun _ ih c => c + 2 ^ 128 * ih ((A2 * c + C2) % 2 ^ 64)) n

/-- `n` lanes of 128 bits, each `2^64 − 1`. -/
def pkM (n : Nat) : Nat :=
  Nat.rec (motive := fun _ => Nat) 0 (fun _ ih => (2 ^ 64 - 1) + 2 ^ 128 * ih) n

/-- `n` lanes of 128 bits holding the LCG states `j, j + 2, j + 4, …` after `s`. -/
def pkS (s : Nat) (n : Nat) : Nat → Nat :=
  Nat.rec (motive := fun _ => Nat → Nat) (fun _ => 0)
    (fun _ ih j => lcgIt s j + 2 ^ 128 * ih (j + 2)) n

theorem and_lanes (m0 x m' y : Nat) (hm : m0 < 2 ^ 128) (hx : x < 2 ^ 128) :
    (m0 + 2 ^ 128 * m') &&& (x + 2 ^ 128 * y) = (m0 &&& x) + 2 ^ 128 * (m' &&& y) := by
  have hmx : m0 &&& x < 2 ^ 128 := Nat.lt_of_le_of_lt Nat.and_le_left hm
  apply Nat.eq_of_testBit_eq; intro i
  rw [Nat.testBit_and, Nat.add_comm m0, Nat.add_comm x, Nat.add_comm (m0 &&& x),
    Nat.testBit_two_pow_mul_add _ hm, Nat.testBit_two_pow_mul_add _ hx,
    Nat.testBit_two_pow_mul_add _ hmx]
  split <;> simp [Nat.testBit_and]

theorem mcongr_add {M x1 y1 x2 y2 : Nat} (h1 : x1 % M = y1 % M) (h2 : x2 % M = y2 % M) :
    (x1 + x2) % M = (y1 + y2) % M := by rw [Nat.add_mod, h1, h2, ← Nat.add_mod]

theorem mcongr_mul {M x1 y1 x2 y2 : Nat} (h1 : x1 % M = y1 % M) (h2 : x2 % M = y2 % M) :
    (x1 * x2) % M = (y1 * y2) % M := by rw [Nat.mul_mod, h1, h2, ← Nat.mul_mod]

theorem mod_affine2 (K C M a c s : Nat) :
    ((K * K % M * a % M) * s + (K * K % M * c + (K * C + C) % M) % M) % M =
      (K * ((K * ((a * s + c) % M) + C) % M) + C) % M := by
  have p1 : ((K * K % M * a % M) * s) % M = (K * K * a * s) % M :=
    mcongr_mul (by rw [Nat.mod_mod]; exact mcongr_mul (Nat.mod_mod _ _) rfl) rfl
  have p2 : ((K * K % M * c + (K * C + C) % M) % M) % M = (K * K * c + (K * C + C)) % M := by
    rw [Nat.mod_mod]; exact mcongr_add (mcongr_mul (Nat.mod_mod _ _) rfl) (Nat.mod_mod _ _)
  have q : ((K * ((a * s + c) % M) + C) % M) % M = (K * (a * s + c) + C) % M := by
    rw [Nat.mod_mod]; exact mcongr_add (mcongr_mul rfl (Nat.mod_mod _ _)) rfl
  rw [mcongr_add p1 p2, mcongr_add (mcongr_mul rfl q) rfl]
  congr 1
  simp only [Nat.mul_add, Nat.mul_assoc, Nat.add_assoc]

theorem lane_step (s a c j : Nat) (h : (a * s + c) % 2 ^ 64 = lcgIt s j) :
    ((A2 * a % 2 ^ 64) * s + (A2 * c + C2) % 2 ^ 64) % 2 ^ 64 = lcgIt s (j + 2) := by
  rw [lcgIt_succ' s (j + 1), lcgIt_succ' s j, ← h]
  unfold lcgNext
  exact mod_affine2 lcgA lcgC (2 ^ 64) a c s

theorem lanes (s : Nat) (hs : s < 2 ^ 64) : ∀ n a c j, a < 2 ^ 64 → c < 2 ^ 64 →
    (a * s + c) % 2 ^ 64 = lcgIt s j →
    pkM n &&& (pkC n c + pkA n a * s) = pkS s n j
  | 0, a, c, j, _, _, _ => by
    show 0 &&& (0 + 0 * s) = 0
    simp
  | n + 1, a, c, j, ha, hc, h => by
    show ((2 ^ 64 - 1) + 2 ^ 128 * pkM n) &&&
        ((c + 2 ^ 128 * pkC n ((A2 * c + C2) % 2 ^ 64)) + (a + 2 ^ 128 * pkA n (A2 * a % 2 ^ 64)) * s) =
      lcgIt s j + 2 ^ 128 * pkS s n (j + 2)
    have hx : a * s + c < 2 ^ 128 := by
      have := Nat.mul_le_mul (Nat.le_pred_of_lt ha) (Nat.le_pred_of_lt hs)
      have e : (2 ^ 64 - 1) * (2 ^ 64 - 1) + (2 ^ 64 - 1) < 2 ^ 128 := by decide
      simp only [Nat.pred_eq_sub_one] at this
      omega
    rw [show (c + 2 ^ 128 * pkC n ((A2 * c + C2) % 2 ^ 64)) + (a + 2 ^ 128 * pkA n (A2 * a % 2 ^ 64)) * s =
        (a * s + c) + 2 ^ 128 * (pkC n ((A2 * c + C2) % 2 ^ 64) + pkA n (A2 * a % 2 ^ 64) * s) by
      rw [Nat.add_mul, Nat.mul_add, Nat.mul_assoc]; omega]
    rw [and_lanes _ _ _ _ (by decide) hx, Nat.and_comm, Nat.and_two_pow_sub_one_eq_mod, h,
      lanes s hs n _ _ (j + 2) (Nat.mod_lt _ (by decide)) (Nat.mod_lt _ (by decide))
        (lane_step s a c j h)]

theorem interleave (s : Nat) : ∀ o j,
    (pkS s (o + 1) j + 2 ^ 64 * pkS s o (j + 1) = lcgIt s j + 2 ^ 64 * strm (2 * o) (lcgIt s j)) ∧
    (pkS s (o + 1) j + 2 ^ 64 * pkS s (o + 1) (j + 1) =
      lcgIt s j + 2 ^ 64 * strm (2 * o + 1) (lcgIt s j))
  | 0, j => by
    constructor
    · show lcgIt s j + 2 ^ 128 * 0 + 2 ^ 64 * 0 = lcgIt s j + 2 ^ 64 * 0
      omega
    · show lcgIt s j + 2 ^ 128 * 0 + 2 ^ 64 * (lcgIt s (j + 1) + 2 ^ 128 * 0) =
        lcgIt s j + 2 ^ 64 * strm 1 (lcgIt s j)
      rw [strm_succ, strm_zero, lcgIt_succ' s j]
      omega
  | o + 1, j => by
    obtain ⟨ih1, ih2⟩ := interleave s o (j + 2)
    have e1 : pkS s (o + 1 + 1) j = lcgIt s j + 2 ^ 128 * pkS s (o + 1) (j + 2) := rfl
    have e2 : pkS s (o + 1) (j + 1) = lcgIt s (j + 1) + 2 ^ 128 * pkS s o (j + 2 + 1) := rfl
    have e3 : pkS s (o + 1 + 1) (j + 1) = lcgIt s (j + 1) + 2 ^ 128 * pkS s (o + 1) (j + 2 + 1) := rfl
    have e4 : ∀ m, strm (m + 2) (lcgIt s j) =
        lcgIt s (j + 1) + 2 ^ 64 * (lcgIt s (j + 2) + 2 ^ 64 * strm m (lcgIt s (j + 2))) := by
      intro m
      rw [strm_succ, strm_succ, ← lcgIt_succ' s j, ← lcgIt_succ' s (j + 1)]
    have e5 := e4 (2 * o)
    have e6 := e4 (2 * o + 1)
    have e7 : 2 * (o + 1) = 2 * o + 2 := by omega
    have e8 : 2 * o + 2 + 1 = (2 * o + 1) + 2 := by omega
    rw [e7, e8, e5, e6, e1, e2, e3]
    constructor <;> omega

/-- The packed stream: states `0, 2, 4, …` in the low halves of 128-bit lanes, states `1, 3, …`
in the high halves (`NE` and `NO` lanes). -/
def laneY (NE NO s : Nat) : Nat :=
  Nat.add (Nat.land (pkM NE) (Nat.add (pkC NE 0) (Nat.mul (pkA NE 1) s)))
    (Nat.land (Nat.mul (Nat.pow 2 64) (pkM NO))
      (Nat.add (Nat.mul (Nat.pow 2 64) (pkC NO 1442695040888963407))
        (Nat.mul (Nat.mul (Nat.pow 2 64) (pkA NO 6364136223846793005)) s)))

theorem mul_and_mul (x y : Nat) : (2 ^ 64 * x) &&& (2 ^ 64 * y) = 2 ^ 64 * (x &&& y) := by
  rw [Nat.mul_comm, Nat.mul_comm _ y, Nat.mul_comm _ (x &&& y), ← Nat.shiftLeft_eq, ← Nat.shiftLeft_eq,
    ← Nat.shiftLeft_eq, Nat.shiftLeft_and_distrib]

theorem laneY_eq (s : Nat) (hs : s < 2 ^ 64) (o : Nat) :
    laneY (o + 1) o s = s + 2 ^ 64 * strm (2 * o) s ∧
    laneY (o + 1) (o + 1) s = s + 2 ^ 64 * strm (2 * o + 1) s := by
  have hE : ∀ n, pkM n &&& (pkC n 0 + pkA n 1 * s) = pkS s n 0 := fun n =>
    lanes s hs n 1 0 0 (by decide) (by decide) (by rw [Nat.one_mul, Nat.add_zero, Nat.mod_eq_of_lt hs]; rfl)
  have hO : ∀ n, (2 ^ 64 * pkM n) &&& (2 ^ 64 * pkC n 1442695040888963407 + 2 ^ 64 * pkA n 6364136223846793005 * s) =
      2 ^ 64 * pkS s n 1 := by
    intro n
    rw [Nat.mul_assoc, ← Nat.mul_add, mul_and_mul, lanes s hs n _ _ 1 (by decide) (by decide)]
    show _ = lcgNext s
    unfold lcgNext
    rfl
  obtain ⟨i1, i2⟩ := interleave s o 0
  rw [lcgIt_zero, Nat.zero_add] at i1 i2
  unfold laneY
  simp only [nadd, nand, nmul, npow]
  rw [hE, hO, hO]
  exact ⟨i1, i2⟩

end lanes

open Lean Elab Term Command Meta in
/- `genLane15C_rfl : ∀ s k d, genLane15C s k = appL k d (2 :: genZ 15 24 1 1 (laneY 13 12 s))`,
by `rfl` (checked by the kernel). -/
run_cmd liftTermElabM do
  let ty ← instantiateMVars (← elabTerm (← `(∀ (s : Nat) (k : Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Int) (d : Int),
      genLane15C s k = appL k d (2 :: genZ 15 24 1 1 (laneY 13 12 s)))) none)
  let pf ← instantiateMVars (← elabTerm (← `(fun (s : Nat) (k : Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Int) (d : Int) =>
      @rfl Int (genLane15C s k))) none)
  addDecl (.thmDecl { name := `Submission.genLane15C_rfl, levelParams := [], type := ty, value := pf })

theorem genLane15C_eq (s : Nat) (hs : s < 2 ^ 64) (k : Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Int) (d : Int) :
    genLane15C s k = appL k d (2 :: genGo 15 24 1 s) := by
  rw [genLane15C_rfl s k d, (laneY_eq s hs 12).1]
  exact congrArg (fun L => appL k d (2 :: L)) (genZ_eq 15 (by decide) s 24 hs 24 1 0 (by decide))

open Lean Elab Term Command Meta in
/- `genLane36C_rfl : ∀ s k d, genLane36C s k = appL k d (2 :: genZ 36 24 1 1 (laneY 13 12 s))`,
by `rfl` (checked by the kernel). -/
run_cmd liftTermElabM do
  let ty ← instantiateMVars (← elabTerm (← `(∀ (s : Nat) (k : Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Int) (d : Int),
      genLane36C s k = appL k d (2 :: genZ 36 24 1 1 (laneY 13 12 s)))) none)
  let pf ← instantiateMVars (← elabTerm (← `(fun (s : Nat) (k : Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Int) (d : Int) =>
      @rfl Int (genLane36C s k))) none)
  addDecl (.thmDecl { name := `Submission.genLane36C_rfl, levelParams := [], type := ty, value := pf })

theorem genLane36C_eq (s : Nat) (hs : s < 2 ^ 64) (k : Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Int) (d : Int) :
    genLane36C s k = appL k d (2 :: genGo 36 24 1 s) := by
  rw [genLane36C_rfl s k d, (laneY_eq s hs 12).1]
  exact congrArg (fun L => appL k d (2 :: L)) (genZ_eq 36 (by decide) s 24 hs 24 1 0 (by decide))

open Lean Elab Term Command Meta in
/- `genLane205C_rfl : ∀ s k d, genLane205C s k = appL k d (2 :: genZ 205 24 1 1 (laneY 27 27 s))`,
by `rfl` (checked by the kernel). -/
run_cmd liftTermElabM do
  let ty ← instantiateMVars (← elabTerm (← `(∀ (s : Nat) (k : Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Int) (d : Int),
      genLane205C s k = appL k d (2 :: genZ 205 24 1 1 (laneY 27 27 s)))) none)
  let pf ← instantiateMVars (← elabTerm (← `(fun (s : Nat) (k : Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Int) (d : Int) =>
      @rfl Int (genLane205C s k))) none)
  addDecl (.thmDecl { name := `Submission.genLane205C_rfl, levelParams := [], type := ty, value := pf })

theorem genLane205C_eq (s : Nat) (hs : s < 2 ^ 64) (k : Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Int) (d : Int) :
    genLane205C s k = appL k d (2 :: genGo 205 24 1 s) := by
  rw [genLane205C_rfl s k d, (laneY_eq s hs 26).2]
  exact congrArg (fun L => appL k d (2 :: L)) (genZ_eq 205 (by decide) s 53 hs 24 1 0 (by decide))

open Lean Elab Term Command Meta in
/- `genLane1001C_rfl : ∀ s k d, genLane1001C s k = appL k d (2 :: genZ 1001 24 1 1 (laneY 106 105 s))`,
by `rfl` (checked by the kernel). -/
run_cmd liftTermElabM do
  let ty ← instantiateMVars (← elabTerm (← `(∀ (s : Nat) (k : Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Int) (d : Int),
      genLane1001C s k = appL k d (2 :: genZ 1001 24 1 1 (laneY 106 105 s)))) none)
  let pf ← instantiateMVars (← elabTerm (← `(fun (s : Nat) (k : Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Int) (d : Int) =>
      @rfl Int (genLane1001C s k))) none)
  addDecl (.thmDecl { name := `Submission.genLane1001C_rfl, levelParams := [], type := ty, value := pf })

theorem genLane1001C_eq (s : Nat) (hs : s < 2 ^ 64) (k : Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Int) (d : Int) :
    genLane1001C s k = appL k d (2 :: genGo 1001 24 1 s) := by
  rw [genLane1001C_rfl s k d, (laneY_eq s hs 105).1]
  exact congrArg (fun L => appL k d (2 :: L)) (genZ_eq 1001 (by decide) s 210 hs 24 1 0 (by decide))

open Lean Elab Term Command Meta in
/- `genLane3484C_rfl : ∀ s k d, genLane3484C s k = appL k d (2 :: genZ 3484 24 1 1 (laneY 349 349 s))`,
by `rfl` (checked by the kernel). -/
run_cmd liftTermElabM do
  let ty ← instantiateMVars (← elabTerm (← `(∀ (s : Nat) (k : Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Int) (d : Int),
      genLane3484C s k = appL k d (2 :: genZ 3484 24 1 1 (laneY 349 349 s)))) none)
  let pf ← instantiateMVars (← elabTerm (← `(fun (s : Nat) (k : Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Int) (d : Int) =>
      @rfl Int (genLane3484C s k))) none)
  addDecl (.thmDecl { name := `Submission.genLane3484C_rfl, levelParams := [], type := ty, value := pf })

theorem genLane3484C_eq (s : Nat) (hs : s < 2 ^ 64) (k : Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Int) (d : Int) :
    genLane3484C s k = appL k d (2 :: genGo 3484 24 1 s) := by
  rw [genLane3484C_rfl s k d, (laneY_eq s hs 348).2]
  exact congrArg (fun L => appL k d (2 :: L)) (genZ_eq 3484 (by decide) s 697 hs 24 1 0 (by decide))

theorem lcgSeed_lt (n : Nat) : lcgSeed n < 2 ^ 64 := by
  unfold lcgSeed lcgM; exact Nat.mod_lt _ (by decide)

theorem genFastC_eq (n : Nat) (k : Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Int) (d : Int) :
    genFastC n k = appL k d (genF n) := by
  have hs := lcgSeed_lt n
  unfold genFastC genF
  by_cases h0 : n < 67108864
  · rw [show Nat.div n 67108864 = 0 from Nat.div_eq_of_lt h0,
      show kbitsOf n = 15 by unfold kbitsOf difficultyLevel; simp [h0]]
    exact genLane15C_eq _ hs k d
  obtain ⟨m0, hm0⟩ := div_succ_of_le (by decide) (Nat.le_of_not_lt h0)
  rw [hm0]
  by_cases h1 : n < 68719476736
  · rw [show Nat.div n 68719476736 = 0 from Nat.div_eq_of_lt h1,
      show kbitsOf n = 36 by unfold kbitsOf difficultyLevel; simp [h0, h1]]
    exact genLane36C_eq _ hs k d
  obtain ⟨m1, hm1⟩ := div_succ_of_le (by decide) (Nat.le_of_not_lt h1)
  rw [hm1]
  by_cases h2 : n < 70368744177664
  · rw [show Nat.div n 70368744177664 = 0 from Nat.div_eq_of_lt h2,
      show kbitsOf n = 205 by unfold kbitsOf difficultyLevel; simp [h0, h1, h2]]
    exact genLane205C_eq _ hs k d
  obtain ⟨m2, hm2⟩ := div_succ_of_le (by decide) (Nat.le_of_not_lt h2)
  rw [hm2]
  by_cases h3 : n < 72057594037927936
  · rw [show Nat.div n 72057594037927936 = 0 from Nat.div_eq_of_lt h3,
      show kbitsOf n = 1001 by unfold kbitsOf difficultyLevel; simp [h0, h1, h2, h3]]
    exact genLane1001C_eq _ hs k d
  obtain ⟨m3, hm3⟩ := div_succ_of_le (by decide) (Nat.le_of_not_lt h3)
  rw [hm3, show kbitsOf n = 3484 by unfold kbitsOf difficultyLevel; simp [h0, h1, h2, h3]]
  exact genLane3484C_eq _ hs k d

/-- The v7 path (also the fallback of the packed runs). -/
theorem fastDisc_spec (n : Nat) : fastDisc n (genF n) = discSpec n := by
  have hlen : (genF n).length = 25 := by unfold genF; simp [genGo_length]
  have hspec := genF_spec n
  generalize genF n = L at hlen hspec
  match L, hlen with
  | [f0, f1, f2, f3, f4, f5, f6, f7, f8, f9, f10, f11, f12, f13, f14, f15, f16, f17, f18, f19, f20, f21, f22, f23, f24], _ =>
    show finish n (prsDag f0 f1 f2 f3 f4 f5 f6 f7 f8 f9 f10 f11 f12 f13 f14 f15 f16 f17 f18 f19 f20 f21 f22 f23 f24 (gz f0 24) (gz f1 23) (gz f2 22) (gz f3 21) (gz f4 20) (gz f5 19) (gz f6 18) (gz f7 17) (gz f8 16) (gz f9 15) (gz f10 14) (gz f11 13) (gz f12 12) (gz f13 11) (gz f14 10) (gz f15 9) (gz f16 8) (gz f17 7) (gz f18 6) (gz f19 5) (gz f20 4) (gz f21 3) (gz f22 2) (gz f23 1)) = discSpec n
    have hdag := prsDag_eq f0 f1 f2 f3 f4 f5 f6 f7 f8 f9 f10 f11 f12 f13 f14 f15 f16 f17 f18 f19 f20 f21 f22 f23 f24 (gz f0 24) (gz f1 23) (gz f2 22) (gz f3 21) (gz f4 20) (gz f5 19) (gz f6 18) (gz f7 17) (gz f8 16) (gz f9 15) (gz f10 14) (gz f11 13) (gz f12 12) (gz f13 11) (gz f14 10) (gz f15 9) (gz f16 8) (gz f17 7) (gz f18 6) (gz f19 5) (gz f20 4) (gz f21 3) (gz f22 2) (gz f23 1)
    unfold finish
    generalize prsDag f0 f1 f2 f3 f4 f5 f6 f7 f8 f9 f10 f11 f12 f13 f14 f15 f16 f17 f18 f19 f20 f21 f22 f23 f24 (gz f0 24) (gz f1 23) (gz f2 22) (gz f3 21) (gz f4 20) (gz f5 19) (gz f6 18) (gz f7 17) (gz f8 16) (gz f9 15) (gz f10 14) (gz f11 13) (gz f12 12) (gz f13 11) (gz f14 10) (gz f15 9) (gz f16 8) (gz f17 7) (gz f18 6) (gz f19 5) (gz f20 4) (gz f21 3) (gz f22 2) (gz f23 1) = r at hdag
    cases h2 : r.2 with
    | succ k => rfl
    | zero =>
      show zdec r.1 = discSpec n
      have hF : [f0, f1, f2, f3, f4, f5, f6, f7, f8, f9, f10, f11, f12, f13, f14, f15, f16, f17, f18, f19, f20, f21, f22, f23, f24].map zdec = polyOf n := hspec
      have hf0 : zdec f0 = 1 := by
        have := congrArg (fun l => l.headD 0) hspec
        simp only [List.map_cons, List.headD_cons] at this
        rw [this]; rfl
      have hrun := runAll_spec [f0, f1, f2, f3, f4, f5, f6, f7, f8, f9, f10, f11, f12, f13, f14, f15, f16, f17, f18, f19, f20, f21, f22, f23, f24] [gz f0 24, gz f1 23, gz f2 22, gz f3 21, gz f4 20, gz f5 19, gz f6 18, gz f7 17, gz f8 16, gz f9 15, gz f10 14, gz f11 13, gz f12 12, gz f13 11, gz f14 10, gz f15 9, gz f16 8, gz f17 7, gz f18 6, gz f19 5, gz f20 4, gz f21 3, gz f22 2, gz f23 1] rfl rfl
        (by simp [hf0]) (by simp [gz_val, hf0]) (by rw [← hdag]; exact h2)
      rw [← hdag] at hrun
      rw [deriv_spec, hF] at hrun
      unfold discSpec
      rw [disc_eq _ (by rw [← hF]; rfl) _ hrun]


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

/-- `rep 1092 25` by doubling. -/
def kR15_0 : Nat := natdag% "shl 1 1092
add 1 v0
shl v1 2184
add v1 v2
shl v3 4368
add v3 v4
shl v5 8736
add v5 v6
shl v5 17472
add v7 v8
shl 1 26208
add v9 v10" []
def kO15_0 : Nat := Nat.shiftLeft kR15_0 363
def kH15_0 : Nat := Nat.sub (Nat.shiftLeft kR15_0 1092) (Nat.shiftLeft kR15_0 364)
def kT15_0 : Nat := Nat.shiftLeft 1 363
def kM15_0 : Nat := Nat.sub (Nat.shiftLeft 1 1092) 1
def kQ15_0 : Nat := Nat.sub (Nat.shiftLeft 1 726) 1

/-- `rep 1857 25` by doubling. -/
def kR15_1 : Nat := natdag% "shl 1 1857
add 1 v0
shl v1 3714
add v1 v2
shl v3 7428
add v3 v4
shl v5 14856
add v5 v6
shl v5 29712
add v7 v8
shl 1 44568
add v9 v10" []
def kO15_1 : Nat := Nat.shiftLeft kR15_1 618
def kH15_1 : Nat := Nat.sub (Nat.shiftLeft kR15_1 1857) (Nat.shiftLeft kR15_1 619)
def kT15_1 : Nat := Nat.shiftLeft 1 618
def kM15_1 : Nat := Nat.sub (Nat.shiftLeft 1 1857) 1
def kQ15_1 : Nat := Nat.sub (Nat.shiftLeft 1 1236) 1

/-- The packed run of band `15` with its lane constants as variables. -/
def pkDagC15 (f0 f1 f2 f3 f4 f5 f6 f7 f8 f9 f10 f11 f12 f13 f14 f15 f16 f17 f18 f19 f20 f21 f22 f23 f24 c0 c1 c2 c3 c4 c5 c6 c7 c8 c9 c10 c11 c12 c13 c14 c15 c16 c17 c18 c19 c20 c21 c22 c23 c24 c25 c26 c27 c28 c29 c30 c31 c32 c33 c34 c35 c36 c37 c38 c39 c40 c41 c42 c43 c44 c45 c46 c47 c48 c49 c50 c51 c52 c53 c54 c55 c56 c57 c58 c59 c60 c61 c62 c63 c64 c65 c66 c67 c68 c69 c70 c71 c72 c73 c74 c75 c76 c77 c78 c79 : Nat) : Nat × Nat :=
  natdag% "shr x26 0
shr x26 x61
shr x1 1
add v2 x28
shl v2 1
land x1 1
mul v4 v5
sub v3 v6
shr x2 1
add v8 x28
shl v8 1
land x2 1
mul v10 v11
sub v9 v12
shr x3 1
add v14 x28
shl v14 1
land x3 1
mul v16 v17
sub v15 v18
shr x4 1
add v20 x28
shl v20 1
land x4 1
mul v22 v23
sub v21 v24
shr x5 1
add v26 x28
shl v26 1
land x5 1
mul v28 v29
sub v27 v30
shr x6 1
add v32 x28
shl v32 1
land x6 1
mul v34 v35
sub v33 v36
shr x7 1
add v38 x28
shl v38 1
land x7 1
mul v40 v41
sub v39 v42
shr x8 1
add v44 x28
shl v44 1
land x8 1
mul v46 v47
sub v45 v48
shr x9 1
add v50 x28
shl v50 1
land x9 1
mul v52 v53
sub v51 v54
shr x10 1
add v56 x28
shl v56 1
land x10 1
mul v58 v59
sub v57 v60
shr x11 1
add v62 x28
shl v62 1
land x11 1
mul v64 v65
sub v63 v66
shr x12 1
add v68 x28
shl v68 1
land x12 1
mul v70 v71
sub v69 v72
shr x13 1
add v74 x28
shl v74 1
land x13 1
mul v76 v77
sub v75 v78
shr x14 1
add v80 x28
shl v80 1
land x14 1
mul v82 v83
sub v81 v84
shr x15 1
add v86 x28
shl v86 1
land x15 1
mul v88 v89
sub v87 v90
shr x16 1
add v92 x28
shl v92 1
land x16 1
mul v94 v95
sub v93 v96
shr x17 1
add v98 x28
shl v98 1
land x17 1
mul v100 v101
sub v99 v102
shr x18 1
add v104 x28
shl v104 1
land x18 1
mul v106 v107
sub v105 v108
shr x19 1
add v110 x28
shl v110 1
land x19 1
mul v112 v113
sub v111 v114
shr x20 1
add v116 x28
shl v116 1
land x20 1
mul v118 v119
sub v117 v120
shr x21 1
add v122 x28
shl v122 1
land x21 1
mul v124 v125
sub v123 v126
shr x22 1
add v128 x28
shl v128 1
land x22 1
mul v130 v131
sub v129 v132
shr x23 1
add v134 x28
shl v134 1
land x23 1
mul v136 v137
sub v135 v138
shr x24 1
add v140 x28
shl v140 1
land x24 1
mul v142 v143
sub v141 v144
mul v7 23
sub v146 x62
mul v13 22
sub v148 x63
mul v19 21
sub v150 x64
mul v25 20
sub v152 x65
mul v31 19
sub v154 x66
mul v37 18
sub v156 x67
mul v43 17
sub v158 x68
mul v49 16
sub v160 x69
mul v55 15
sub v162 x70
mul v61 14
sub v164 x71
mul v67 13
sub v166 x72
mul v73 12
sub v168 x73
mul v79 11
sub v170 x74
mul v85 10
sub v172 x75
mul v91 9
sub v174 x76
mul v97 8
sub v176 x77
mul v103 7
sub v178 x78
mul v109 6
sub v180 x79
mul v115 5
sub v182 x80
mul v121 4
sub v184 x81
mul v127 3
sub v186 x82
mul v133 2
sub v188 x83
shl v139 x61
add v145 v190
shl v133 x60
add v191 v192
shl v127 x59
add v193 v194
shl v121 x58
add v195 v196
shl v115 x57
add v197 v198
shl v109 x56
add v199 v200
shl v103 x55
add v201 v202
shl v97 x54
add v203 v204
shl v91 x53
add v205 v206
shl v85 x52
add v207 v208
shl v79 x51
add v209 v210
shl v73 x50
add v211 v212
shl v67 x49
add v213 v214
shl v61 x48
add v215 v216
shl v55 x47
add v217 v218
shl v49 x46
add v219 v220
shl v43 x45
add v221 v222
shl v37 x44
add v223 v224
shl v31 x43
add v225 v226
shl v25 x42
add v227 v228
shl v19 x41
add v229 v230
shl v13 x40
add v231 v232
shl v7 x39
add v233 v234
shl x36 x38
add v235 v236
sub v237 v0
shl v189 x61
add v139 v239
shl v187 x60
add v240 v241
shl v185 x59
add v242 v243
shl v183 x58
add v244 v245
shl v181 x57
add v246 v247
shl v179 x56
add v248 v249
shl v177 x55
add v250 v251
shl v175 x54
add v252 v253
shl v173 x53
add v254 v255
shl v171 x52
add v256 v257
shl v169 x51
add v258 v259
shl v167 x50
add v260 v261
shl v165 x49
add v262 v263
shl v163 x48
add v264 v265
shl v161 x47
add v266 v267
shl v159 x46
add v268 v269
shl v157 x45
add v270 v271
shl v155 x44
add v272 v273
shl v153 x43
add v274 v275
shl v151 x42
add v276 v277
shl v149 x41
add v278 v279
shl v147 x40
add v280 v281
shl x37 x39
add v282 v283
sub v284 v1
shr x26 x60
shr x27 x60
mul 24 v7
shl 1 x84
add v288 v289
mul 1 v147
shl 24 x84
add v291 v292
sub v290 v293
sub v293 v290
add v294 v295
sub 1 v296
add 0 v297
mul 24 24
mul v299 v238
mul 1 24
shl v301 x61
add v302 v290
sub v303 v293
mul v304 v285
sub v305 v300
sub v300 v305
add v307 v306
add v308 v286
land v309 v287
shr v309 x39
add v310 v311
add v298 v312
shr v309 x40
sub v314 x28
shr v309 x41
land v316 x29
sub 1 v306
sub 1 v318
xor 0 v319
sub 1 v315
add v313 v321
shr x26 x59
shr x27 x59
mul v315 v147
add v325 v292
mul 24 v317
shl v315 x84
add v327 v328
sub v326 v329
sub v329 v326
add v330 v331
sub 1 v332
add v322 v333
mul v315 v315
mul v335 v285
mul 24 v315
shl v337 x61
add v338 v326
sub v339 v329
mul v340 v308
sub v341 v336
sub v336 v341
add v343 v342
div v344 v299
mod v344 v299
add v334 v346
add v345 v323
land v348 v324
shr v348 x40
add v349 v350
add v347 v351
shr v348 x41
sub v353 x28
shr v348 x42
land v355 x29
sub 1 v342
sub 1 v357
xor 0 v358
sub 1 v354
add v352 v360
shr x26 x58
shr x27 x58
mul v354 v317
add v364 v328
mul v315 v356
shl v354 x84
add v366 v367
sub v365 v368
sub v368 v365
add v369 v370
sub 1 v371
add v361 v372
mul v354 v354
mul v374 v308
mul v315 v354
shl v376 x61
add v377 v365
sub v378 v368
mul v379 v345
sub v380 v375
sub v375 v380
add v382 v381
div v383 v335
mod v383 v335
add v373 v385
add v384 v362
land v387 v363
shr v387 x41
add v388 v389
add v386 v390
shr v387 x42
sub v392 x28
shr v387 x43
land v394 x29
sub 1 v381
sub 1 v396
xor v320 v397
sub 1 v393
add v391 v399
shr x26 x57
shr x27 x57
mul v393 v356
add v403 v367
mul v354 v395
shl v393 x84
add v405 v406
sub v404 v407
sub v407 v404
add v408 v409
sub 1 v410
add v400 v411
mul v393 v393
mul v413 v345
mul v354 v393
shl v415 x61
add v416 v404
sub v417 v407
mul v418 v384
sub v419 v414
sub v414 v419
add v421 v420
div v422 v374
mod v422 v374
add v412 v424
add v423 v401
land v426 v402
shr v426 x42
add v427 v428
add v425 v429
shr v426 x43
sub v431 x28
shr v426 x44
land v433 x29
sub 1 v420
sub 1 v435
xor v359 v436
sub 1 v432
add v430 v438
shr x26 x56
shr x27 x56
mul v432 v395
add v442 v406
mul v393 v434
shl v432 x84
add v444 v445
sub v443 v446
sub v446 v443
add v447 v448
sub 1 v449
add v439 v450
mul v432 v432
mul v452 v384
mul v393 v432
shl v454 x61
add v455 v443
sub v456 v446
mul v457 v423
sub v458 v453
sub v453 v458
add v460 v459
div v461 v413
mod v461 v413
add v451 v463
add v462 v440
land v465 v441
shr v465 x43
add v466 v467
add v464 v468
shr v465 x44
sub v470 x28
shr v465 x45
land v472 x29
sub 1 v459
sub 1 v474
xor v398 v475
sub 1 v471
add v469 v477
shr x26 x55
shr x27 x55
mul v471 v434
add v481 v445
mul v432 v473
shl v471 x84
add v483 v484
sub v482 v485
sub v485 v482
add v486 v487
sub 1 v488
add v478 v489
mul v471 v471
mul v491 v423
mul v432 v471
shl v493 x61
add v494 v482
sub v495 v485
mul v496 v462
sub v497 v492
sub v492 v497
add v499 v498
div v500 v452
mod v500 v452
add v490 v502
add v501 v479
land v504 v480
shr v504 x44
add v505 v506
add v503 v507
shr v504 x45
sub v509 x28
shr v504 x46
land v511 x29
sub 1 v498
sub 1 v513
xor v437 v514
sub 1 v510
add v508 v516
shr x26 x54
shr x27 x54
mul v510 v473
add v520 v484
mul v471 v512
shl v510 x84
add v522 v523
sub v521 v524
sub v524 v521
add v525 v526
sub 1 v527
add v517 v528
mul v510 v510
mul v530 v462
mul v471 v510
shl v532 x61
add v533 v521
sub v534 v524
mul v535 v501
sub v536 v531
sub v531 v536
add v538 v537
div v539 v491
mod v539 v491
add v529 v541
add v540 v518
land v543 v519
shr v543 x45
add v544 v545
add v542 v546
shr v543 x46
sub v548 x28
shr v543 x47
land v550 x29
sub 1 v537
sub 1 v552
xor v476 v553
sub 1 v549
add v547 v555
shr x26 x53
shr x27 x53
mul v549 v512
add v559 v523
mul v510 v551
shl v549 x84
add v561 v562
sub v560 v563
sub v563 v560
add v564 v565
sub 1 v566
add v556 v567
mul v549 v549
mul v569 v501
mul v510 v549
shl v571 x61
add v572 v560
sub v573 v563
mul v574 v540
sub v575 v570
sub v570 v575
add v577 v576
div v578 v530
mod v578 v530
add v568 v580
add v579 v557
land v582 v558
shr v582 x46
add v583 v584
add v581 v585
shr v582 x47
sub v587 x28
shr v582 x48
land v589 x29
sub 1 v576
sub 1 v591
xor v515 v592
sub 1 v588
add v586 v594
shr x26 x52
shr x27 x52
mul v588 v551
add v598 v562
mul v549 v590
shl v588 x84
add v600 v601
sub v599 v602
sub v602 v599
add v603 v604
sub 1 v605
add v595 v606
mul v588 v588
mul v608 v540
mul v549 v588
shl v610 x61
add v611 v599
sub v612 v602
mul v613 v579
sub v614 v609
sub v609 v614
add v616 v615
div v617 v569
mod v617 v569
add v607 v619
add v618 v596
land v621 v597
shr v621 x47
add v622 v623
add v620 v624
shr v621 x48
sub v626 x28
shr v621 x49
land v628 x29
sub 1 v615
sub 1 v630
xor v554 v631
sub 1 v627
add v625 v633
shr x26 x51
shr x27 x51
mul v627 v590
add v637 v601
mul v588 v629
shl v627 x84
add v639 v640
sub v638 v641
sub v641 v638
add v642 v643
sub 1 v644
add v634 v645
mul v627 v627
mul v647 v579
mul v588 v627
shl v649 x61
add v650 v638
sub v651 v641
mul v652 v618
sub v653 v648
sub v648 v653
add v655 v654
div v656 v608
mod v656 v608
add v646 v658
add v657 v635
land v660 v636
shr v660 x48
add v661 v662
add v659 v663
shr v660 x49
sub v665 x28
shr v660 x50
land v667 x29
sub 1 v654
sub 1 v669
xor v593 v670
sub 1 v666
add v664 v672
shr x26 x50
shr x27 x50
mul v666 v629
add v676 v640
mul v627 v668
shl v666 x84
add v678 v679
sub v677 v680
sub v680 v677
add v681 v682
sub 1 v683
add v673 v684
mul v666 v666
mul v686 v618
mul v627 v666
shl v688 x61
add v689 v677
sub v690 v680
mul v691 v657
sub v692 v687
sub v687 v692
add v694 v693
div v695 v647
mod v695 v647
add v685 v697
add v696 v674
land v699 v675
shr v699 x49
add v700 v701
add v698 v702
shr v699 x50
sub v704 x28
shr v699 x51
land v706 x29
sub 1 v693
sub 1 v708
xor v632 v709
sub 1 v705
add v703 v711
shr x26 x49
shr x27 x49
mul v705 v668
add v715 v679
mul v666 v707
shl v705 x84
add v717 v718
sub v716 v719
sub v719 v716
add v720 v721
sub 1 v722
add v712 v723
mul v705 v705
mul v725 v657
mul v666 v705
shl v727 x61
add v728 v716
sub v729 v719
mul v730 v696
sub v731 v726
sub v726 v731
add v733 v732
div v734 v686
mod v734 v686
add v724 v736
add v735 v713
land v738 v714
shr v738 x50
add v739 v740
add v737 v741
shr v738 x51
sub v743 x28
shr v738 x52
land v745 x29
sub 1 v732
sub 1 v747
xor v671 v748
sub 1 v744
add v742 v750
shr x26 x48
shr x27 x48
mul v744 v707
add v754 v718
mul v705 v746
shl v744 x84
add v756 v757
sub v755 v758
sub v758 v755
add v759 v760
sub 1 v761
add v751 v762
mul v744 v744
mul v764 v696
mul v705 v744
shl v766 x61
add v767 v755
sub v768 v758
mul v769 v735
sub v770 v765
sub v765 v770
add v772 v771
div v773 v725
mod v773 v725
add v763 v775
add v774 v752
land v777 v753
shr v777 x51
add v778 v779
add v776 v780
shr v777 x52
sub v782 x28
shr v777 x53
land v784 x29
sub 1 v771
sub 1 v786
xor v710 v787
sub 1 v783
add v781 v789
shr x26 x47
shr x27 x47
mul v783 v746
add v793 v757
mul v744 v785
shl v783 x84
add v795 v796
sub v794 v797
sub v797 v794
add v798 v799
sub 1 v800
add v790 v801
mul v783 v783
mul v803 v735
mul v744 v783
shl v805 x61
add v806 v794
sub v807 v797
mul v808 v774
sub v809 v804
sub v804 v809
add v811 v810
div v812 v764
mod v812 v764
add v802 v814
add v813 v791
land v816 v792
shr v816 x52
add v817 v818
add v815 v819
shr v816 x53
sub v821 x28
shr v816 x54
land v823 x29
sub 1 v810
sub 1 v825
xor v749 v826
sub 1 v822
add v820 v828
shr x26 x46
shr x27 x46
mul v822 v785
add v832 v796
mul v783 v824
shl v822 x84
add v834 v835
sub v833 v836
sub v836 v833
add v837 v838
sub 1 v839
add v829 v840
mul v822 v822
mul v842 v774
mul v783 v822
shl v844 x61
add v845 v833
sub v846 v836
mul v847 v813
sub v848 v843
sub v843 v848
add v850 v849
div v851 v803
mod v851 v803
add v841 v853
add v852 v830
land v855 v831
shr v855 x53
add v856 v857
add v854 v858
shr v855 x54
sub v860 x28
shr v855 x55
land v862 x29
sub 1 v849
sub 1 v864
xor v788 v865
sub 1 v861
add v859 v867
shr x31 x95
shr x31 x96
land v821 x29
shr v816 x55
land v872 x29
shr v816 x56
land v874 x29
shr v816 x57
land v876 x29
shr v816 x58
land v878 x29
shr v816 x59
land v880 x29
shr v816 x60
land v882 x29
shr v816 x61
land v884 x29
shr v816 0
land v886 x29
add v871 x85
add v824 x85
add v873 x85
add v875 x85
add v877 x85
add v879 x85
add v881 x85
add v883 x85
add v885 x85
add v887 x85
land v860 x29
shr v855 x56
land v899 x29
shr v855 x57
land v901 x29
shr v855 x58
land v903 x29
shr v855 x59
land v905 x29
shr v855 x60
land v907 x29
shr v855 x61
land v909 x29
shr v855 0
land v911 x29
add v898 x85
add v863 x85
add v900 x85
add v902 x85
add v904 x85
add v906 x85
add v908 x85
add v910 x85
add v912 x85
shl v896 x94
add v897 v922
shl v895 x93
add v923 v924
shl v894 x92
add v925 v926
shl v893 x91
add v927 v928
shl v892 x90
add v929 v930
shl v891 x89
add v931 v932
shl v890 x88
add v933 v934
shl v889 x87
add v935 v936
shl v888 x86
add v937 v938
sub v939 v869
shl v920 x94
add v921 v941
shl v919 x93
add v942 v943
shl v918 x92
add v944 v945
shl v917 x91
add v946 v947
shl v916 x90
add v948 v949
shl v915 x89
add v950 v951
shl v914 x88
add v952 v953
shl v913 x87
add v954 v955
sub v956 v870
shr x31 x97
shr x32 x97
mul v861 v889
shl v822 x98
add v960 v961
mul v822 v914
shl v861 x98
add v963 v964
sub v962 v965
sub v965 v962
add v966 v967
sub 1 v968
add v868 v969
mul v861 v861
mul v971 v940
mul v822 v861
shl v973 x94
add v974 v962
sub v975 v965
mul v976 v957
sub v977 v972
sub v972 v977
add v979 v978
div v980 v842
mod v980 v842
add v970 v982
add v981 v958
land v984 v959
shr v984 x87
add v985 v986
add v983 v987
shr v984 x88
sub v989 x33
shr v984 x89
land v991 x34
sub 1 v978
sub 1 v993
xor v827 v994
sub 1 v990
add v988 v996
shr x31 x99
shr x32 x99
mul v990 v914
add v1000 v964
mul v861 v992
shl v990 x98
add v1002 v1003
sub v1001 v1004
sub v1004 v1001
add v1005 v1006
sub 1 v1007
add v997 v1008
mul v990 v990
mul v1010 v957
mul v861 v990
shl v1012 x94
add v1013 v1001
sub v1014 v1004
mul v1015 v981
sub v1016 v1011
sub v1011 v1016
add v1018 v1017
div v1019 v971
mod v1019 v971
add v1009 v1021
add v1020 v998
land v1023 v999
shr v1023 x88
add v1024 v1025
add v1022 v1026
shr v1023 x89
sub v1028 x33
shr v1023 x90
land v1030 x34
sub 1 v1017
sub 1 v1032
xor v866 v1033
sub 1 v1029
add v1027 v1035
shr x31 x100
shr x32 x100
mul v1029 v992
add v1039 v1003
mul v990 v1031
shl v1029 x98
add v1041 v1042
sub v1040 v1043
sub v1043 v1040
add v1044 v1045
sub 1 v1046
add v1036 v1047
mul v1029 v1029
mul v1049 v981
mul v990 v1029
shl v1051 x94
add v1052 v1040
sub v1053 v1043
mul v1054 v1020
sub v1055 v1050
sub v1050 v1055
add v1057 v1056
div v1058 v1010
mod v1058 v1010
add v1048 v1060
add v1059 v1037
land v1062 v1038
shr v1062 x89
add v1063 v1064
add v1061 v1065
shr v1062 x90
sub v1067 x33
shr v1062 x91
land v1069 x34
sub 1 v1056
sub 1 v1071
xor v995 v1072
sub 1 v1068
add v1066 v1074
shr x31 x101
shr x32 x101
mul v1068 v1031
add v1078 v1042
mul v1029 v1070
shl v1068 x98
add v1080 v1081
sub v1079 v1082
sub v1082 v1079
add v1083 v1084
sub 1 v1085
add v1075 v1086
mul v1068 v1068
mul v1088 v1020
mul v1029 v1068
shl v1090 x94
add v1091 v1079
sub v1092 v1082
mul v1093 v1059
sub v1094 v1089
sub v1089 v1094
add v1096 v1095
div v1097 v1049
mod v1097 v1049
add v1087 v1099
add v1098 v1076
land v1101 v1077
shr v1101 x90
add v1102 v1103
add v1100 v1104
shr v1101 x91
sub v1106 x33
shr v1101 x92
land v1108 x34
sub 1 v1095
sub 1 v1110
xor v1034 v1111
sub 1 v1107
add v1105 v1113
shr x31 x102
shr x32 x102
mul v1107 v1070
add v1117 v1081
mul v1068 v1109
shl v1107 x98
add v1119 v1120
sub v1118 v1121
sub v1121 v1118
add v1122 v1123
sub 1 v1124
add v1114 v1125
mul v1107 v1107
mul v1127 v1059
mul v1068 v1107
shl v1129 x94
add v1130 v1118
sub v1131 v1121
mul v1132 v1098
sub v1133 v1128
sub v1128 v1133
add v1135 v1134
div v1136 v1088
mod v1136 v1088
add v1126 v1138
add v1137 v1115
land v1140 v1116
shr v1140 x91
add v1141 v1142
add v1139 v1143
shr v1140 x92
sub v1145 x33
shr v1140 x93
land v1147 x34
sub 1 v1134
sub 1 v1149
xor v1073 v1150
sub 1 v1146
add v1144 v1152
shr x31 x103
shr x32 x103
mul v1146 v1109
add v1156 v1120
mul v1107 v1148
shl v1146 x98
add v1158 v1159
sub v1157 v1160
sub v1160 v1157
add v1161 v1162
sub 1 v1163
add v1153 v1164
mul v1146 v1146
mul v1166 v1098
mul v1107 v1146
shl v1168 x94
add v1169 v1157
sub v1170 v1160
mul v1171 v1137
sub v1172 v1167
sub v1167 v1172
add v1174 v1173
div v1175 v1127
mod v1175 v1127
add v1165 v1177
add v1176 v1154
land v1179 v1155
shr v1179 x92
add v1180 v1181
add v1178 v1182
shr v1179 x93
sub v1184 x33
shr v1179 x94
land v1186 x34
sub 1 v1173
sub 1 v1188
xor v1112 v1189
sub 1 v1185
add v1183 v1191
shr x31 x104
shr x32 x104
mul v1185 v1148
add v1195 v1159
mul v1146 v1187
shl v1185 x98
add v1197 v1198
sub v1196 v1199
sub v1199 v1196
add v1200 v1201
sub 1 v1202
add v1192 v1203
mul v1185 v1185
mul v1205 v1137
mul v1146 v1185
shl v1207 x94
add v1208 v1196
sub v1209 v1199
mul v1210 v1176
sub v1211 v1206
sub v1206 v1211
add v1213 v1212
div v1214 v1166
mod v1214 v1166
add v1204 v1216
add v1215 v1193
land v1218 v1194
shr v1218 x93
add v1219 v1220
add v1217 v1221
shr v1218 x94
sub v1223 x33
shr v1218 0
land v1225 x34
sub 1 v1212
sub 1 v1227
xor v1151 v1228
sub 1 v1224
add v1222 v1230
shr x31 x105
shr x32 x105
mul v1224 v1187
add v1234 v1198
mul v1185 v1226
shl v1224 x98
add v1236 v1237
sub v1235 v1238
sub v1238 v1235
add v1239 v1240
sub 1 v1241
add v1231 v1242
mul v1224 v1224
mul v1244 v1176
mul v1185 v1224
shl v1246 x94
add v1247 v1235
sub v1248 v1238
mul v1249 v1215
sub v1250 v1245
sub v1245 v1250
add v1252 v1251
div v1253 v1205
mod v1253 v1205
add v1243 v1255
add v1254 v1232
land v1257 v1233
shr v1257 x94
add v1258 v1259
add v1256 v1260
shr v1257 0
sub v1262 x33
land v1262 x34
sub 1 v1251
sub 1 v1265
xor v1190 v1266
sub 1 v1263
add v1261 v1268
shl v1254 1
add v1270 v1267
app x25 v1271 v1269" [f0, f1, f2, f3, f4, f5, f6, f7, f8, f9, f10, f11, f12, f13, f14, f15, f16, f17, f18, f19, f20, f21, f22, f23, f24, (@Prod.mk Nat Nat), c0, c1, c2, c3, c4, c5, c6, c7, c8, c9, c10, c11, c12, c13, c14, c15, c16, c17, c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c30, c31, c32, c33, c34, c35, c36, c37, c38, c39, c40, c41, c42, c43, c44, c45, c46, c47, c48, c49, c50, c51, c52, c53, c54, c55, c56, c57, c58, c59, c60, c61, c62, c63, c64, c65, c66, c67, c68, c69, c70, c71, c72, c73, c74, c75, c76, c77, c78, c79]

set_option linter.unusedVariables false in
/-- The structured run over the same variables. -/
def pkRhs15 (f0 f1 f2 f3 f4 f5 f6 f7 f8 f9 f10 f11 f12 f13 f14 f15 f16 f17 f18 f19 f20 f21 f22 f23 f24 c0 c1 c2 c3 c4 c5 c6 c7 c8 c9 c10 c11 c12 c13 c14 c15 c16 c17 c18 c19 c20 c21 c22 c23 c24 c25 c26 c27 c28 c29 c30 c31 c32 c33 c34 c35 c36 c37 c38 c39 c40 c41 c42 c43 c44 c45 c46 c47 c48 c49 c50 c51 c52 c53 c54 c55 c56 c57 c58 c59 c60 c61 c62 c63 c64 c65 c66 c67 c68 c69 c70 c71 c72 c73 c74 c75 c76 c77 c78 c79 : Nat) : Nat × Nat :=
  let s := prun [.step 1092 363 22 c2 c3 (Nat.shiftRight c0 c34) (Nat.shiftRight c1 c34) c4 c58 c35 c13 c14 c15 true false,
    .step 1092 363 21 c2 c3 (Nat.shiftRight c0 c33) (Nat.shiftRight c1 c33) c4 c58 c35 c14 c15 c16 false false,
    .step 1092 363 20 c2 c3 (Nat.shiftRight c0 c32) (Nat.shiftRight c1 c32) c4 c58 c35 c15 c16 c17 false false,
    .step 1092 363 19 c2 c3 (Nat.shiftRight c0 c31) (Nat.shiftRight c1 c31) c4 c58 c35 c16 c17 c18 false false,
    .step 1092 363 18 c2 c3 (Nat.shiftRight c0 c30) (Nat.shiftRight c1 c30) c4 c58 c35 c17 c18 c19 false false,
    .step 1092 363 17 c2 c3 (Nat.shiftRight c0 c29) (Nat.shiftRight c1 c29) c4 c58 c35 c18 c19 c20 false false,
    .step 1092 363 16 c2 c3 (Nat.shiftRight c0 c28) (Nat.shiftRight c1 c28) c4 c58 c35 c19 c20 c21 false false,
    .step 1092 363 15 c2 c3 (Nat.shiftRight c0 c27) (Nat.shiftRight c1 c27) c4 c58 c35 c20 c21 c22 false false,
    .step 1092 363 14 c2 c3 (Nat.shiftRight c0 c26) (Nat.shiftRight c1 c26) c4 c58 c35 c21 c22 c23 false false,
    .step 1092 363 13 c2 c3 (Nat.shiftRight c0 c25) (Nat.shiftRight c1 c25) c4 c58 c35 c22 c23 c24 false false,
    .step 1092 363 12 c2 c3 (Nat.shiftRight c0 c24) (Nat.shiftRight c1 c24) c4 c58 c35 c23 c24 c25 false false,
    .step 1092 363 11 c2 c3 (Nat.shiftRight c0 c23) (Nat.shiftRight c1 c23) c4 c58 c35 c24 c25 c26 false false,
    .step 1092 363 10 c2 c3 (Nat.shiftRight c0 c22) (Nat.shiftRight c1 c22) c4 c58 c35 c25 c26 c27 false false,
    .step 1092 363 9 c2 c3 (Nat.shiftRight c0 c21) (Nat.shiftRight c1 c21) c4 c58 c35 c26 c27 c28 false false,
    .step 1092 363 8 c2 c3 (Nat.shiftRight c0 c20) (Nat.shiftRight c1 c20) c4 c58 c35 c27 c28 c29 false false,
    .repack 1092 363 1857 618 9 c3 (Nat.shiftRight c0 c21) (Nat.shiftRight c0 c20) [c27, c28, c29, c30, c31, c32, c33, c34, c35, 0] [c28, c29, c30, c31, c32, c33, c34, c35, 0] [c60, c61, c62, c63, c64, c65, c66, c67, c68] [c61, c62, c63, c64, c65, c66, c67, c68] (Nat.shiftRight c5 c69) (Nat.shiftRight c5 c70) c59,
    .step 1857 618 7 c7 c8 (Nat.shiftRight c5 c71) (Nat.shiftRight c6 c71) c9 c72 c68 c61 c62 c63 false false,
    .step 1857 618 6 c7 c8 (Nat.shiftRight c5 c73) (Nat.shiftRight c6 c73) c9 c72 c68 c62 c63 c64 false false,
    .step 1857 618 5 c7 c8 (Nat.shiftRight c5 c74) (Nat.shiftRight c6 c74) c9 c72 c68 c63 c64 c65 false false,
    .step 1857 618 4 c7 c8 (Nat.shiftRight c5 c75) (Nat.shiftRight c6 c75) c9 c72 c68 c64 c65 c66 false false,
    .step 1857 618 3 c7 c8 (Nat.shiftRight c5 c76) (Nat.shiftRight c6 c76) c9 c72 c68 c65 c66 c67 false false,
    .step 1857 618 2 c7 c8 (Nat.shiftRight c5 c77) (Nat.shiftRight c6 c77) c9 c72 c68 c66 c67 c68 false false,
    .step 1857 618 1 c7 c8 (Nat.shiftRight c5 c78) (Nat.shiftRight c6 c78) c9 c72 c68 c67 c68 0 false false,
    .step 1857 618 0 c7 c8 (Nat.shiftRight c5 c79) (Nat.shiftRight c6 c79) c9 c72 c68 c68 0 0 false false]
    (pinit c2 c10 c11 [c12, c13, c14, c15, c16, c17, c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c30, c31, c32, c33, c34, c35] [c13, c14, c15, c16, c17, c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c30, c31, c32, c33, c34, c35] [23, 22, 21, 20, 19, 18, 17, 16, 15, 14, 13, 12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2] [c36, c37, c38, c39, c40, c41, c42, c43, c44, c45, c46, c47, c48, c49, c50, c51, c52, c53, c54, c55, c56, c57] (Nat.shiftRight c0 0) (Nat.shiftRight c0 c35) [f1, f2, f3, f4, f5, f6, f7, f8, f9, f10, f11, f12, f13, f14, f15, f16, f17, f18, f19, f20, f21, f22, f23, f24])
  (Nat.add (Nat.shiftLeft s.gv 1) s.gs, s.bad)

/-- Statement of `pkDagC15_eq`. -/
def PkDagC15Eq : Prop := ∀ f0 f1 f2 f3 f4 f5 f6 f7 f8 f9 f10 f11 f12 f13 f14 f15 f16 f17 f18 f19 f20 f21 f22 f23 f24 c0 c1 c2 c3 c4 c5 c6 c7 c8 c9 c10 c11 c12 c13 c14 c15 c16 c17 c18 c19 c20 c21 c22 c23 c24 c25 c26 c27 c28 c29 c30 c31 c32 c33 c34 c35 c36 c37 c38 c39 c40 c41 c42 c43 c44 c45 c46 c47 c48 c49 c50 c51 c52 c53 c54 c55 c56 c57 c58 c59 c60 c61 c62 c63 c64 c65 c66 c67 c68 c69 c70 c71 c72 c73 c74 c75 c76 c77 c78 c79 : Nat, pkDagC15 f0 f1 f2 f3 f4 f5 f6 f7 f8 f9 f10 f11 f12 f13 f14 f15 f16 f17 f18 f19 f20 f21 f22 f23 f24 c0 c1 c2 c3 c4 c5 c6 c7 c8 c9 c10 c11 c12 c13 c14 c15 c16 c17 c18 c19 c20 c21 c22 c23 c24 c25 c26 c27 c28 c29 c30 c31 c32 c33 c34 c35 c36 c37 c38 c39 c40 c41 c42 c43 c44 c45 c46 c47 c48 c49 c50 c51 c52 c53 c54 c55 c56 c57 c58 c59 c60 c61 c62 c63 c64 c65 c66 c67 c68 c69 c70 c71 c72 c73 c74 c75 c76 c77 c78 c79 = pkRhs15 f0 f1 f2 f3 f4 f5 f6 f7 f8 f9 f10 f11 f12 f13 f14 f15 f16 f17 f18 f19 f20 f21 f22 f23 f24 c0 c1 c2 c3 c4 c5 c6 c7 c8 c9 c10 c11 c12 c13 c14 c15 c16 c17 c18 c19 c20 c21 c22 c23 c24 c25 c26 c27 c28 c29 c30 c31 c32 c33 c34 c35 c36 c37 c38 c39 c40 c41 c42 c43 c44 c45 c46 c47 c48 c49 c50 c51 c52 c53 c54 c55 c56 c57 c58 c59 c60 c61 c62 c63 c64 c65 c66 c67 c68 c69 c70 c71 c72 c73 c74 c75 c76 c77 c78 c79

open Lean Elab Term Command Meta in
/- `pkDagC15_eq : PkDagC15Eq` by `rfl`, checked by the kernel on open terms. -/
run_cmd liftTermElabM do
  let ty ← instantiateMVars (← elabTerm (← `(PkDagC15Eq)) none)
  let pf ← instantiateMVars (← elabTerm (← `(fun (f0 f1 f2 f3 f4 f5 f6 f7 f8 f9 f10 f11 f12 f13 f14 f15 f16 f17 f18 f19 f20 f21 f22 f23 f24 c0 c1 c2 c3 c4 c5 c6 c7 c8 c9 c10 c11 c12 c13 c14 c15 c16 c17 c18 c19 c20 c21 c22 c23 c24 c25 c26 c27 c28 c29 c30 c31 c32 c33 c34 c35 c36 c37 c38 c39 c40 c41 c42 c43 c44 c45 c46 c47 c48 c49 c50 c51 c52 c53 c54 c55 c56 c57 c58 c59 c60 c61 c62 c63 c64 c65 c66 c67 c68 c69 c70 c71 c72 c73 c74 c75 c76 c77 c78 c79 : Nat) =>
    @rfl (Nat × Nat) (pkDagC15 f0 f1 f2 f3 f4 f5 f6 f7 f8 f9 f10 f11 f12 f13 f14 f15 f16 f17 f18 f19 f20 f21 f22 f23 f24 c0 c1 c2 c3 c4 c5 c6 c7 c8 c9 c10 c11 c12 c13 c14 c15 c16 c17 c18 c19 c20 c21 c22 c23 c24 c25 c26 c27 c28 c29 c30 c31 c32 c33 c34 c35 c36 c37 c38 c39 c40 c41 c42 c43 c44 c45 c46 c47 c48 c49 c50 c51 c52 c53 c54 c55 c56 c57 c58 c59 c60 c61 c62 c63 c64 c65 c66 c67 c68 c69 c70 c71 c72 c73 c74 c75 c76 c77 c78 c79))) none)
  addDecl (.thmDecl { name := `Submission.pkDagC15_eq, levelParams := [], type := ty, value := pf })

/-- The packed run of band `15`, lane constants computed inside the graph. -/
def pkDag15 (f0 f1 f2 f3 f4 f5 f6 f7 f8 f9 f10 f11 f12 f13 f14 f15 f16 f17 f18 f19 f20 f21 f22 f23 f24 : Nat) : Nat × Nat :=
  natdag% "shl 1 1092
add 1 v0
shl v1 2184
add v1 v2
shl v3 4368
add v3 v4
shl v5 8736
add v5 v6
shl v5 17472
add v7 v8
shl 1 26208
add v9 v10
shl v11 363
shl v11 1092
shl v11 364
sub v13 v14
shl 1 363
sub v0 1
shl 1 726
sub v18 1
shl 1 1857
add 1 v20
shl v21 3714
add v21 v22
shl v23 7428
add v23 v24
shl v25 14856
add v25 v26
shl v25 29712
add v27 v28
shl 1 44568
add v29 v30
shl v31 618
shl v31 1857
shl v31 619
sub v33 v34
shl 1 618
sub v20 1
shl 1 1236
sub v38 1
shl 11 364
shl 21 363
shl 5 365
shl 19 363
shl 9 364
shl 17 363
shl 1 367
shl 15 363
shl 7 364
shl 13 363
shl 3 365
shl 11 363
shl 5 364
shl 9 363
shl 1 366
shl 7 363
shl 3 364
shl 5 363
shl 1 365
shl 3 363
shl 1 364
shr v12 0
shr v12 1092
shr x1 1
add v63 v16
shl v63 1
land x1 1
mul v65 v66
sub v64 v67
shr x2 1
add v69 v16
shl v69 1
land x2 1
mul v71 v72
sub v70 v73
shr x3 1
add v75 v16
shl v75 1
land x3 1
mul v77 v78
sub v76 v79
shr x4 1
add v81 v16
shl v81 1
land x4 1
mul v83 v84
sub v82 v85
shr x5 1
add v87 v16
shl v87 1
land x5 1
mul v89 v90
sub v88 v91
shr x6 1
add v93 v16
shl v93 1
land x6 1
mul v95 v96
sub v94 v97
shr x7 1
add v99 v16
shl v99 1
land x7 1
mul v101 v102
sub v100 v103
shr x8 1
add v105 v16
shl v105 1
land x8 1
mul v107 v108
sub v106 v109
shr x9 1
add v111 v16
shl v111 1
land x9 1
mul v113 v114
sub v112 v115
shr x10 1
add v117 v16
shl v117 1
land x10 1
mul v119 v120
sub v118 v121
shr x11 1
add v123 v16
shl v123 1
land x11 1
mul v125 v126
sub v124 v127
shr x12 1
add v129 v16
shl v129 1
land x12 1
mul v131 v132
sub v130 v133
shr x13 1
add v135 v16
shl v135 1
land x13 1
mul v137 v138
sub v136 v139
shr x14 1
add v141 v16
shl v141 1
land x14 1
mul v143 v144
sub v142 v145
shr x15 1
add v147 v16
shl v147 1
land x15 1
mul v149 v150
sub v148 v151
shr x16 1
add v153 v16
shl v153 1
land x16 1
mul v155 v156
sub v154 v157
shr x17 1
add v159 v16
shl v159 1
land x17 1
mul v161 v162
sub v160 v163
shr x18 1
add v165 v16
shl v165 1
land x18 1
mul v167 v168
sub v166 v169
shr x19 1
add v171 v16
shl v171 1
land x19 1
mul v173 v174
sub v172 v175
shr x20 1
add v177 v16
shl v177 1
land x20 1
mul v179 v180
sub v178 v181
shr x21 1
add v183 v16
shl v183 1
land x21 1
mul v185 v186
sub v184 v187
shr x22 1
add v189 v16
shl v189 1
land x22 1
mul v191 v192
sub v190 v193
shr x23 1
add v195 v16
shl v195 1
land x23 1
mul v197 v198
sub v196 v199
shr x24 1
add v201 v16
shl v201 1
land x24 1
mul v203 v204
sub v202 v205
mul v68 23
sub v207 v40
mul v74 22
sub v209 v41
mul v80 21
sub v211 v42
mul v86 20
sub v213 v43
mul v92 19
sub v215 v44
mul v98 18
sub v217 v45
mul v104 17
sub v219 v46
mul v110 16
sub v221 v47
mul v116 15
sub v223 v48
mul v122 14
sub v225 v49
mul v128 13
sub v227 v50
mul v134 12
sub v229 v51
mul v140 11
sub v231 v52
mul v146 10
sub v233 v53
mul v152 9
sub v235 v54
mul v158 8
sub v237 v55
mul v164 7
sub v239 v56
mul v170 6
sub v241 v57
mul v176 5
sub v243 v58
mul v182 4
sub v245 v59
mul v188 3
sub v247 v60
mul v194 2
sub v249 v16
shl v200 1092
add v206 v251
shl v194 2184
add v252 v253
shl v188 3276
add v254 v255
shl v182 4368
add v256 v257
shl v176 5460
add v258 v259
shl v170 6552
add v260 v261
shl v164 7644
add v262 v263
shl v158 8736
add v264 v265
shl v152 9828
add v266 v267
shl v146 10920
add v268 v269
shl v140 12012
add v270 v271
shl v134 13104
add v272 v273
shl v128 14196
add v274 v275
shl v122 15288
add v276 v277
shl v116 16380
add v278 v279
shl v110 17472
add v280 v281
shl v104 18564
add v282 v283
shl v98 19656
add v284 v285
shl v92 20748
add v286 v287
shl v86 21840
add v288 v289
shl v80 22932
add v290 v291
shl v74 24024
add v292 v293
shl v68 25116
add v294 v295
shl 18788340662190665823115844774314696219005460391266558965658327772257672200916867547709591987078149624255479809 26208
add v296 v297
sub v298 v61
shl v250 1092
add v200 v300
shl v248 2184
add v301 v302
shl v246 3276
add v303 v304
shl v244 4368
add v305 v306
shl v242 5460
add v307 v308
shl v240 6552
add v309 v310
shl v238 7644
add v311 v312
shl v236 8736
add v313 v314
shl v234 9828
add v315 v316
shl v232 10920
add v317 v318
shl v230 12012
add v319 v320
shl v228 13104
add v321 v322
shl v226 14196
add v323 v324
shl v224 15288
add v325 v326
shl v222 16380
add v327 v328
shl v220 17472
add v329 v330
shl v218 18564
add v331 v332
shl v216 19656
add v333 v334
shl v214 20748
add v335 v336
shl v212 21840
add v337 v338
shl v210 22932
add v339 v340
shl v208 24024
add v341 v342
shl 18788340662190665823115844774314696219005460391266558965658327772257672200916867547709591987078149624255479832 25116
add v343 v344
sub v345 v62
shr v12 2184
shr v15 2184
mul 24 v68
add v349 v16
mul 1 v208
shl 24 363
add v351 v352
sub v350 v353
sub v353 v350
add v354 v355
sub 1 v356
add 0 v357
mul 24 24
mul v359 v299
mul 1 24
shl v361 1092
add v362 v350
sub v363 v353
mul v364 v346
sub v365 v360
sub v360 v365
add v367 v366
add v368 v347
land v369 v348
shr v369 25116
add v370 v371
add v358 v372
shr v369 24024
sub v374 v16
shr v369 22932
land v376 v17
sub 1 v366
sub 1 v378
xor 0 v379
sub 1 v375
add v373 v381
shr v12 3276
shr v15 3276
mul v375 v208
add v385 v352
mul 24 v377
shl v375 363
add v387 v388
sub v386 v389
sub v389 v386
add v390 v391
sub 1 v392
add v382 v393
mul v375 v375
mul v395 v346
mul 24 v375
shl v397 1092
add v398 v386
sub v399 v389
mul v400 v368
sub v401 v396
sub v396 v401
add v403 v402
div v404 v359
mod v404 v359
add v394 v406
add v405 v383
land v408 v384
shr v408 24024
add v409 v410
add v407 v411
shr v408 22932
sub v413 v16
shr v408 21840
land v415 v17
sub 1 v402
sub 1 v417
xor 0 v418
sub 1 v414
add v412 v420
shr v12 4368
shr v15 4368
mul v414 v377
add v424 v388
mul v375 v416
shl v414 363
add v426 v427
sub v425 v428
sub v428 v425
add v429 v430
sub 1 v431
add v421 v432
mul v414 v414
mul v434 v368
mul v375 v414
shl v436 1092
add v437 v425
sub v438 v428
mul v439 v405
sub v440 v435
sub v435 v440
add v442 v441
div v443 v395
mod v443 v395
add v433 v445
add v444 v422
land v447 v423
shr v447 22932
add v448 v449
add v446 v450
shr v447 21840
sub v452 v16
shr v447 20748
land v454 v17
sub 1 v441
sub 1 v456
xor v380 v457
sub 1 v453
add v451 v459
shr v12 5460
shr v15 5460
mul v453 v416
add v463 v427
mul v414 v455
shl v453 363
add v465 v466
sub v464 v467
sub v467 v464
add v468 v469
sub 1 v470
add v460 v471
mul v453 v453
mul v473 v405
mul v414 v453
shl v475 1092
add v476 v464
sub v477 v467
mul v478 v444
sub v479 v474
sub v474 v479
add v481 v480
div v482 v434
mod v482 v434
add v472 v484
add v483 v461
land v486 v462
shr v486 21840
add v487 v488
add v485 v489
shr v486 20748
sub v491 v16
shr v486 19656
land v493 v17
sub 1 v480
sub 1 v495
xor v419 v496
sub 1 v492
add v490 v498
shr v12 6552
shr v15 6552
mul v492 v455
add v502 v466
mul v453 v494
shl v492 363
add v504 v505
sub v503 v506
sub v506 v503
add v507 v508
sub 1 v509
add v499 v510
mul v492 v492
mul v512 v444
mul v453 v492
shl v514 1092
add v515 v503
sub v516 v506
mul v517 v483
sub v518 v513
sub v513 v518
add v520 v519
div v521 v473
mod v521 v473
add v511 v523
add v522 v500
land v525 v501
shr v525 20748
add v526 v527
add v524 v528
shr v525 19656
sub v530 v16
shr v525 18564
land v532 v17
sub 1 v519
sub 1 v534
xor v458 v535
sub 1 v531
add v529 v537
shr v12 7644
shr v15 7644
mul v531 v494
add v541 v505
mul v492 v533
shl v531 363
add v543 v544
sub v542 v545
sub v545 v542
add v546 v547
sub 1 v548
add v538 v549
mul v531 v531
mul v551 v483
mul v492 v531
shl v553 1092
add v554 v542
sub v555 v545
mul v556 v522
sub v557 v552
sub v552 v557
add v559 v558
div v560 v512
mod v560 v512
add v550 v562
add v561 v539
land v564 v540
shr v564 19656
add v565 v566
add v563 v567
shr v564 18564
sub v569 v16
shr v564 17472
land v571 v17
sub 1 v558
sub 1 v573
xor v497 v574
sub 1 v570
add v568 v576
shr v12 8736
shr v15 8736
mul v570 v533
add v580 v544
mul v531 v572
shl v570 363
add v582 v583
sub v581 v584
sub v584 v581
add v585 v586
sub 1 v587
add v577 v588
mul v570 v570
mul v590 v522
mul v531 v570
shl v592 1092
add v593 v581
sub v594 v584
mul v595 v561
sub v596 v591
sub v591 v596
add v598 v597
div v599 v551
mod v599 v551
add v589 v601
add v600 v578
land v603 v579
shr v603 18564
add v604 v605
add v602 v606
shr v603 17472
sub v608 v16
shr v603 16380
land v610 v17
sub 1 v597
sub 1 v612
xor v536 v613
sub 1 v609
add v607 v615
shr v12 9828
shr v15 9828
mul v609 v572
add v619 v583
mul v570 v611
shl v609 363
add v621 v622
sub v620 v623
sub v623 v620
add v624 v625
sub 1 v626
add v616 v627
mul v609 v609
mul v629 v561
mul v570 v609
shl v631 1092
add v632 v620
sub v633 v623
mul v634 v600
sub v635 v630
sub v630 v635
add v637 v636
div v638 v590
mod v638 v590
add v628 v640
add v639 v617
land v642 v618
shr v642 17472
add v643 v644
add v641 v645
shr v642 16380
sub v647 v16
shr v642 15288
land v649 v17
sub 1 v636
sub 1 v651
xor v575 v652
sub 1 v648
add v646 v654
shr v12 10920
shr v15 10920
mul v648 v611
add v658 v622
mul v609 v650
shl v648 363
add v660 v661
sub v659 v662
sub v662 v659
add v663 v664
sub 1 v665
add v655 v666
mul v648 v648
mul v668 v600
mul v609 v648
shl v670 1092
add v671 v659
sub v672 v662
mul v673 v639
sub v674 v669
sub v669 v674
add v676 v675
div v677 v629
mod v677 v629
add v667 v679
add v678 v656
land v681 v657
shr v681 16380
add v682 v683
add v680 v684
shr v681 15288
sub v686 v16
shr v681 14196
land v688 v17
sub 1 v675
sub 1 v690
xor v614 v691
sub 1 v687
add v685 v693
shr v12 12012
shr v15 12012
mul v687 v650
add v697 v661
mul v648 v689
shl v687 363
add v699 v700
sub v698 v701
sub v701 v698
add v702 v703
sub 1 v704
add v694 v705
mul v687 v687
mul v707 v639
mul v648 v687
shl v709 1092
add v710 v698
sub v711 v701
mul v712 v678
sub v713 v708
sub v708 v713
add v715 v714
div v716 v668
mod v716 v668
add v706 v718
add v717 v695
land v720 v696
shr v720 15288
add v721 v722
add v719 v723
shr v720 14196
sub v725 v16
shr v720 13104
land v727 v17
sub 1 v714
sub 1 v729
xor v653 v730
sub 1 v726
add v724 v732
shr v12 13104
shr v15 13104
mul v726 v689
add v736 v700
mul v687 v728
shl v726 363
add v738 v739
sub v737 v740
sub v740 v737
add v741 v742
sub 1 v743
add v733 v744
mul v726 v726
mul v746 v678
mul v687 v726
shl v748 1092
add v749 v737
sub v750 v740
mul v751 v717
sub v752 v747
sub v747 v752
add v754 v753
div v755 v707
mod v755 v707
add v745 v757
add v756 v734
land v759 v735
shr v759 14196
add v760 v761
add v758 v762
shr v759 13104
sub v764 v16
shr v759 12012
land v766 v17
sub 1 v753
sub 1 v768
xor v692 v769
sub 1 v765
add v763 v771
shr v12 14196
shr v15 14196
mul v765 v728
add v775 v739
mul v726 v767
shl v765 363
add v777 v778
sub v776 v779
sub v779 v776
add v780 v781
sub 1 v782
add v772 v783
mul v765 v765
mul v785 v717
mul v726 v765
shl v787 1092
add v788 v776
sub v789 v779
mul v790 v756
sub v791 v786
sub v786 v791
add v793 v792
div v794 v746
mod v794 v746
add v784 v796
add v795 v773
land v798 v774
shr v798 13104
add v799 v800
add v797 v801
shr v798 12012
sub v803 v16
shr v798 10920
land v805 v17
sub 1 v792
sub 1 v807
xor v731 v808
sub 1 v804
add v802 v810
shr v12 15288
shr v15 15288
mul v804 v767
add v814 v778
mul v765 v806
shl v804 363
add v816 v817
sub v815 v818
sub v818 v815
add v819 v820
sub 1 v821
add v811 v822
mul v804 v804
mul v824 v756
mul v765 v804
shl v826 1092
add v827 v815
sub v828 v818
mul v829 v795
sub v830 v825
sub v825 v830
add v832 v831
div v833 v785
mod v833 v785
add v823 v835
add v834 v812
land v837 v813
shr v837 12012
add v838 v839
add v836 v840
shr v837 10920
sub v842 v16
shr v837 9828
land v844 v17
sub 1 v831
sub 1 v846
xor v770 v847
sub 1 v843
add v841 v849
shr v12 16380
shr v15 16380
mul v843 v806
add v853 v817
mul v804 v845
shl v843 363
add v855 v856
sub v854 v857
sub v857 v854
add v858 v859
sub 1 v860
add v850 v861
mul v843 v843
mul v863 v795
mul v804 v843
shl v865 1092
add v866 v854
sub v867 v857
mul v868 v834
sub v869 v864
sub v864 v869
add v871 v870
div v872 v824
mod v872 v824
add v862 v874
add v873 v851
land v876 v852
shr v876 10920
add v877 v878
add v875 v879
shr v876 9828
sub v881 v16
shr v876 8736
land v883 v17
sub 1 v870
sub 1 v885
xor v809 v886
sub 1 v882
add v880 v888
shr v12 17472
shr v15 17472
mul v882 v845
add v892 v856
mul v843 v884
shl v882 363
add v894 v895
sub v893 v896
sub v896 v893
add v897 v898
sub 1 v899
add v889 v900
mul v882 v882
mul v902 v834
mul v843 v882
shl v904 1092
add v905 v893
sub v906 v896
mul v907 v873
sub v908 v903
sub v903 v908
add v910 v909
div v911 v863
mod v911 v863
add v901 v913
add v912 v890
land v915 v891
shr v915 9828
add v916 v917
add v914 v918
shr v915 8736
sub v920 v16
shr v915 7644
land v922 v17
sub 1 v909
sub 1 v924
xor v848 v925
sub 1 v921
add v919 v927
shr v32 27855
shr v32 29712
land v881 v17
shr v876 7644
land v932 v17
shr v876 6552
land v934 v17
shr v876 5460
land v936 v17
shr v876 4368
land v938 v17
shr v876 3276
land v940 v17
shr v876 2184
land v942 v17
shr v876 1092
land v944 v17
shr v876 0
land v946 v17
add v931 1087770609288739018116276647019455748771006705104961378712461595034426490595006604789142613973366461205111032091613828619038527924547086098538439244313054029233256850683807162952723726336
add v884 1087770609288739018116276647019455748771006705104961378712461595034426490595006604789142613973366461205111032091613828619038527924547086098538439244313054029233256850683807162952723726336
add v933 1087770609288739018116276647019455748771006705104961378712461595034426490595006604789142613973366461205111032091613828619038527924547086098538439244313054029233256850683807162952723726336
add v935 1087770609288739018116276647019455748771006705104961378712461595034426490595006604789142613973366461205111032091613828619038527924547086098538439244313054029233256850683807162952723726336
add v937 1087770609288739018116276647019455748771006705104961378712461595034426490595006604789142613973366461205111032091613828619038527924547086098538439244313054029233256850683807162952723726336
add v939 1087770609288739018116276647019455748771006705104961378712461595034426490595006604789142613973366461205111032091613828619038527924547086098538439244313054029233256850683807162952723726336
add v941 1087770609288739018116276647019455748771006705104961378712461595034426490595006604789142613973366461205111032091613828619038527924547086098538439244313054029233256850683807162952723726336
add v943 1087770609288739018116276647019455748771006705104961378712461595034426490595006604789142613973366461205111032091613828619038527924547086098538439244313054029233256850683807162952723726336
add v945 1087770609288739018116276647019455748771006705104961378712461595034426490595006604789142613973366461205111032091613828619038527924547086098538439244313054029233256850683807162952723726336
add v947 1087770609288739018116276647019455748771006705104961378712461595034426490595006604789142613973366461205111032091613828619038527924547086098538439244313054029233256850683807162952723726336
land v920 v17
shr v915 6552
land v959 v17
shr v915 5460
land v961 v17
shr v915 4368
land v963 v17
shr v915 3276
land v965 v17
shr v915 2184
land v967 v17
shr v915 1092
land v969 v17
shr v915 0
land v971 v17
add v958 1087770609288739018116276647019455748771006705104961378712461595034426490595006604789142613973366461205111032091613828619038527924547086098538439244313054029233256850683807162952723726336
add v923 1087770609288739018116276647019455748771006705104961378712461595034426490595006604789142613973366461205111032091613828619038527924547086098538439244313054029233256850683807162952723726336
add v960 1087770609288739018116276647019455748771006705104961378712461595034426490595006604789142613973366461205111032091613828619038527924547086098538439244313054029233256850683807162952723726336
add v962 1087770609288739018116276647019455748771006705104961378712461595034426490595006604789142613973366461205111032091613828619038527924547086098538439244313054029233256850683807162952723726336
add v964 1087770609288739018116276647019455748771006705104961378712461595034426490595006604789142613973366461205111032091613828619038527924547086098538439244313054029233256850683807162952723726336
add v966 1087770609288739018116276647019455748771006705104961378712461595034426490595006604789142613973366461205111032091613828619038527924547086098538439244313054029233256850683807162952723726336
add v968 1087770609288739018116276647019455748771006705104961378712461595034426490595006604789142613973366461205111032091613828619038527924547086098538439244313054029233256850683807162952723726336
add v970 1087770609288739018116276647019455748771006705104961378712461595034426490595006604789142613973366461205111032091613828619038527924547086098538439244313054029233256850683807162952723726336
add v972 1087770609288739018116276647019455748771006705104961378712461595034426490595006604789142613973366461205111032091613828619038527924547086098538439244313054029233256850683807162952723726336
shl v956 1857
add v957 v982
shl v955 3714
add v983 v984
shl v954 5571
add v985 v986
shl v953 7428
add v987 v988
shl v952 9285
add v989 v990
shl v951 11142
add v991 v992
shl v950 12999
add v993 v994
shl v949 14856
add v995 v996
shl v948 16713
add v997 v998
sub v999 v929
shl v980 1857
add v981 v1001
shl v979 3714
add v1002 v1003
shl v978 5571
add v1004 v1005
shl v977 7428
add v1006 v1007
shl v976 9285
add v1008 v1009
shl v975 11142
add v1010 v1011
shl v974 12999
add v1012 v1013
shl v973 14856
add v1014 v1015
sub v1016 v930
shr v32 31569
shr v35 31569
mul v921 v949
shl v882 618
add v1020 v1021
mul v882 v974
shl v921 618
add v1023 v1024
sub v1022 v1025
sub v1025 v1022
add v1026 v1027
sub 1 v1028
add v928 v1029
mul v921 v921
mul v1031 v1000
mul v882 v921
shl v1033 1857
add v1034 v1022
sub v1035 v1025
mul v1036 v1017
sub v1037 v1032
sub v1032 v1037
add v1039 v1038
div v1040 v902
mod v1040 v902
add v1030 v1042
add v1041 v1018
land v1044 v1019
shr v1044 14856
add v1045 v1046
add v1043 v1047
shr v1044 12999
sub v1049 v36
shr v1044 11142
land v1051 v37
sub 1 v1038
sub 1 v1053
xor v887 v1054
sub 1 v1050
add v1048 v1056
shr v32 33426
shr v35 33426
mul v1050 v974
add v1060 v1024
mul v921 v1052
shl v1050 618
add v1062 v1063
sub v1061 v1064
sub v1064 v1061
add v1065 v1066
sub 1 v1067
add v1057 v1068
mul v1050 v1050
mul v1070 v1017
mul v921 v1050
shl v1072 1857
add v1073 v1061
sub v1074 v1064
mul v1075 v1041
sub v1076 v1071
sub v1071 v1076
add v1078 v1077
div v1079 v1031
mod v1079 v1031
add v1069 v1081
add v1080 v1058
land v1083 v1059
shr v1083 12999
add v1084 v1085
add v1082 v1086
shr v1083 11142
sub v1088 v36
shr v1083 9285
land v1090 v37
sub 1 v1077
sub 1 v1092
xor v926 v1093
sub 1 v1089
add v1087 v1095
shr v32 35283
shr v35 35283
mul v1089 v1052
add v1099 v1063
mul v1050 v1091
shl v1089 618
add v1101 v1102
sub v1100 v1103
sub v1103 v1100
add v1104 v1105
sub 1 v1106
add v1096 v1107
mul v1089 v1089
mul v1109 v1041
mul v1050 v1089
shl v1111 1857
add v1112 v1100
sub v1113 v1103
mul v1114 v1080
sub v1115 v1110
sub v1110 v1115
add v1117 v1116
div v1118 v1070
mod v1118 v1070
add v1108 v1120
add v1119 v1097
land v1122 v1098
shr v1122 11142
add v1123 v1124
add v1121 v1125
shr v1122 9285
sub v1127 v36
shr v1122 7428
land v1129 v37
sub 1 v1116
sub 1 v1131
xor v1055 v1132
sub 1 v1128
add v1126 v1134
shr v32 37140
shr v35 37140
mul v1128 v1091
add v1138 v1102
mul v1089 v1130
shl v1128 618
add v1140 v1141
sub v1139 v1142
sub v1142 v1139
add v1143 v1144
sub 1 v1145
add v1135 v1146
mul v1128 v1128
mul v1148 v1080
mul v1089 v1128
shl v1150 1857
add v1151 v1139
sub v1152 v1142
mul v1153 v1119
sub v1154 v1149
sub v1149 v1154
add v1156 v1155
div v1157 v1109
mod v1157 v1109
add v1147 v1159
add v1158 v1136
land v1161 v1137
shr v1161 9285
add v1162 v1163
add v1160 v1164
shr v1161 7428
sub v1166 v36
shr v1161 5571
land v1168 v37
sub 1 v1155
sub 1 v1170
xor v1094 v1171
sub 1 v1167
add v1165 v1173
shr v32 38997
shr v35 38997
mul v1167 v1130
add v1177 v1141
mul v1128 v1169
shl v1167 618
add v1179 v1180
sub v1178 v1181
sub v1181 v1178
add v1182 v1183
sub 1 v1184
add v1174 v1185
mul v1167 v1167
mul v1187 v1119
mul v1128 v1167
shl v1189 1857
add v1190 v1178
sub v1191 v1181
mul v1192 v1158
sub v1193 v1188
sub v1188 v1193
add v1195 v1194
div v1196 v1148
mod v1196 v1148
add v1186 v1198
add v1197 v1175
land v1200 v1176
shr v1200 7428
add v1201 v1202
add v1199 v1203
shr v1200 5571
sub v1205 v36
shr v1200 3714
land v1207 v37
sub 1 v1194
sub 1 v1209
xor v1133 v1210
sub 1 v1206
add v1204 v1212
shr v32 40854
shr v35 40854
mul v1206 v1169
add v1216 v1180
mul v1167 v1208
shl v1206 618
add v1218 v1219
sub v1217 v1220
sub v1220 v1217
add v1221 v1222
sub 1 v1223
add v1213 v1224
mul v1206 v1206
mul v1226 v1158
mul v1167 v1206
shl v1228 1857
add v1229 v1217
sub v1230 v1220
mul v1231 v1197
sub v1232 v1227
sub v1227 v1232
add v1234 v1233
div v1235 v1187
mod v1235 v1187
add v1225 v1237
add v1236 v1214
land v1239 v1215
shr v1239 5571
add v1240 v1241
add v1238 v1242
shr v1239 3714
sub v1244 v36
shr v1239 1857
land v1246 v37
sub 1 v1233
sub 1 v1248
xor v1172 v1249
sub 1 v1245
add v1243 v1251
shr v32 42711
shr v35 42711
mul v1245 v1208
add v1255 v1219
mul v1206 v1247
shl v1245 618
add v1257 v1258
sub v1256 v1259
sub v1259 v1256
add v1260 v1261
sub 1 v1262
add v1252 v1263
mul v1245 v1245
mul v1265 v1197
mul v1206 v1245
shl v1267 1857
add v1268 v1256
sub v1269 v1259
mul v1270 v1236
sub v1271 v1266
sub v1266 v1271
add v1273 v1272
div v1274 v1226
mod v1274 v1226
add v1264 v1276
add v1275 v1253
land v1278 v1254
shr v1278 3714
add v1279 v1280
add v1277 v1281
shr v1278 1857
sub v1283 v36
shr v1278 0
land v1285 v37
sub 1 v1272
sub 1 v1287
xor v1211 v1288
sub 1 v1284
add v1282 v1290
shr v32 44568
shr v35 44568
mul v1284 v1247
add v1294 v1258
mul v1245 v1286
shl v1284 618
add v1296 v1297
sub v1295 v1298
sub v1298 v1295
add v1299 v1300
sub 1 v1301
add v1291 v1302
mul v1284 v1284
mul v1304 v1236
mul v1245 v1284
shl v1306 1857
add v1307 v1295
sub v1308 v1298
mul v1309 v1275
sub v1310 v1305
sub v1305 v1310
add v1312 v1311
div v1313 v1265
mod v1313 v1265
add v1303 v1315
add v1314 v1292
land v1317 v1293
shr v1317 1857
add v1318 v1319
add v1316 v1320
shr v1317 0
sub v1322 v36
land v1322 v37
sub 1 v1311
sub 1 v1325
xor v1250 v1326
sub 1 v1323
add v1321 v1328
shl v1314 1
add v1330 v1327
app x25 v1331 v1329" [f0, f1, f2, f3, f4, f5, f6, f7, f8, f9, f10, f11, f12, f13, f14, f15, f16, f17, f18, f19, f20, f21, f22, f23, f24, (@Prod.mk Nat Nat)]

/-- Statement of `pkDag15_eq`. -/
def PkDag15Eq : Prop := ∀ f0 f1 f2 f3 f4 f5 f6 f7 f8 f9 f10 f11 f12 f13 f14 f15 f16 f17 f18 f19 f20 f21 f22 f23 f24 : Nat, pkDag15 f0 f1 f2 f3 f4 f5 f6 f7 f8 f9 f10 f11 f12 f13 f14 f15 f16 f17 f18 f19 f20 f21 f22 f23 f24 = pkDagC15 f0 f1 f2 f3 f4 f5 f6 f7 f8 f9 f10 f11 f12 f13 f14 f15 f16 f17 f18 f19 f20 f21 f22 f23 f24 kO15_0 kH15_0 kT15_0 kM15_0 kQ15_0 kO15_1 kH15_1 kT15_1 kM15_1 kQ15_1 18788340662190665823115844774314696219005460391266558965658327772257672200916867547709591987078149624255479809 18788340662190665823115844774314696219005460391266558965658327772257672200916867547709591987078149624255479832 26208 25116 24024 22932 21840 20748 19656 18564 17472 16380 15288 14196 13104 12012 10920 9828 8736 7644 6552 5460 4368 3276 2184 1092 413343494568194648108548585034923316818120128607864297244483210989668788420171086049611023715719291733620555776 394555153906003982285432740260608620599114668216597738278824883217411116219254218501901431728641142109365075968 375766813243813316462316895486293924380109207825331179313166555445153444018337350954191839741562992485109596160 356978472581622650639201050711979228161103747434064620347508227672895771817420483406482247754484842860854116352 338190131919431984816085205937664531942098287042798061381849899900638099616503615858772655767406693236598636544 319401791257241318992969361163349835723092826651531502416191572128380427415586748311063063780328543612343156736 300613450595050653169853516389035139504087366260264943450533244356122755214669880763353471793250393988087676928 281825109932859987346737671614720443285081905868998384484874916583865083013753013215643879806172244363832197120 263036769270669321523621826840405747066076445477731825519216588811607410812836145667934287819094094739576717312 244248428608478655700505982066091050847070985086465266553558261039349738611919278120224695832015945115321237504 225460087946287989877390137291776354628065524695198707587899933267092066411002410572515103844937795491065757696 206671747284097324054274292517461658409060064303932148622241605494834394210085543024805511857859645866810277888 187883406621906658231158447743146962190054603912665589656583277722576722009168675477095919870781496242554798080 169095065959715992408042602968832265971049143521399030690924949950319049808251807929386327883703346618299318272 150306725297525326584926758194517569752043683130132471725266622178061377607334940381676735896625196994043838464 131518384635334660761810913420202873533038222738865912759608294405803705406418072833967143909547047369788358656 112730043973143994938695068645888177314032762347599353793949966633546033205501205286257551922468897745532878848 93941703310953329115579223871573481095027301956332794828291638861288361004584337738547959935390748121277399040 75153362648762663292463379097258784876021841565066235862633311089030688803667470190838367948312598497021919232 56365021986571997469347534322944088657016381173799676896974983316773016602750602643128775961234448872766439424 37576681324381331646231689548629392438010920782533117931316655544515344401833735095419183974156299248510959616 18788340662190665823115844774314696219005460391266558965658327772257672200916867547709591987078149624255479808 363 (Nat.sub kT15_1 kT15_0) 16713 14856 12999 11142 9285 7428 5571 3714 1857 27855 29712 31569 618 33426 35283 37140 38997 40854 42711 44568

open Lean Elab Term Command Meta in
/- `pkDag15_eq : PkDag15Eq` by `rfl`: the two graphs differ only in closed constants. -/
run_cmd liftTermElabM do
  let ty ← instantiateMVars (← elabTerm (← `(PkDag15Eq)) none)
  let pf ← instantiateMVars (← elabTerm (← `(fun (f0 f1 f2 f3 f4 f5 f6 f7 f8 f9 f10 f11 f12 f13 f14 f15 f16 f17 f18 f19 f20 f21 f22 f23 f24 : Nat) =>
    @rfl (Nat × Nat) (pkDag15 f0 f1 f2 f3 f4 f5 f6 f7 f8 f9 f10 f11 f12 f13 f14 f15 f16 f17 f18 f19 f20 f21 f22 f23 f24))) none)
  addDecl (.thmDecl { name := `Submission.pkDag15_eq, levelParams := [], type := ty, value := pf })

/-- The lane-constant act list of band `15`. -/
def acts15 : List PAct := [.step 1092 363 22 kT15_0 kM15_0 (Nat.shiftRight kO15_0 2184) (Nat.shiftRight kH15_0 2184) kQ15_0 363 1092 25116 24024 22932 true false,
    .step 1092 363 21 kT15_0 kM15_0 (Nat.shiftRight kO15_0 3276) (Nat.shiftRight kH15_0 3276) kQ15_0 363 1092 24024 22932 21840 false false,
    .step 1092 363 20 kT15_0 kM15_0 (Nat.shiftRight kO15_0 4368) (Nat.shiftRight kH15_0 4368) kQ15_0 363 1092 22932 21840 20748 false false,
    .step 1092 363 19 kT15_0 kM15_0 (Nat.shiftRight kO15_0 5460) (Nat.shiftRight kH15_0 5460) kQ15_0 363 1092 21840 20748 19656 false false,
    .step 1092 363 18 kT15_0 kM15_0 (Nat.shiftRight kO15_0 6552) (Nat.shiftRight kH15_0 6552) kQ15_0 363 1092 20748 19656 18564 false false,
    .step 1092 363 17 kT15_0 kM15_0 (Nat.shiftRight kO15_0 7644) (Nat.shiftRight kH15_0 7644) kQ15_0 363 1092 19656 18564 17472 false false,
    .step 1092 363 16 kT15_0 kM15_0 (Nat.shiftRight kO15_0 8736) (Nat.shiftRight kH15_0 8736) kQ15_0 363 1092 18564 17472 16380 false false,
    .step 1092 363 15 kT15_0 kM15_0 (Nat.shiftRight kO15_0 9828) (Nat.shiftRight kH15_0 9828) kQ15_0 363 1092 17472 16380 15288 false false,
    .step 1092 363 14 kT15_0 kM15_0 (Nat.shiftRight kO15_0 10920) (Nat.shiftRight kH15_0 10920) kQ15_0 363 1092 16380 15288 14196 false false,
    .step 1092 363 13 kT15_0 kM15_0 (Nat.shiftRight kO15_0 12012) (Nat.shiftRight kH15_0 12012) kQ15_0 363 1092 15288 14196 13104 false false,
    .step 1092 363 12 kT15_0 kM15_0 (Nat.shiftRight kO15_0 13104) (Nat.shiftRight kH15_0 13104) kQ15_0 363 1092 14196 13104 12012 false false,
    .step 1092 363 11 kT15_0 kM15_0 (Nat.shiftRight kO15_0 14196) (Nat.shiftRight kH15_0 14196) kQ15_0 363 1092 13104 12012 10920 false false,
    .step 1092 363 10 kT15_0 kM15_0 (Nat.shiftRight kO15_0 15288) (Nat.shiftRight kH15_0 15288) kQ15_0 363 1092 12012 10920 9828 false false,
    .step 1092 363 9 kT15_0 kM15_0 (Nat.shiftRight kO15_0 16380) (Nat.shiftRight kH15_0 16380) kQ15_0 363 1092 10920 9828 8736 false false,
    .step 1092 363 8 kT15_0 kM15_0 (Nat.shiftRight kO15_0 17472) (Nat.shiftRight kH15_0 17472) kQ15_0 363 1092 9828 8736 7644 false false,
    .repack 1092 363 1857 618 9 kM15_0 (Nat.shiftRight kO15_0 16380) (Nat.shiftRight kO15_0 17472) [9828, 8736, 7644, 6552, 5460, 4368, 3276, 2184, 1092, 0] [8736, 7644, 6552, 5460, 4368, 3276, 2184, 1092, 0] [16713, 14856, 12999, 11142, 9285, 7428, 5571, 3714, 1857] [14856, 12999, 11142, 9285, 7428, 5571, 3714, 1857] (Nat.shiftRight kO15_1 27855) (Nat.shiftRight kO15_1 29712) (Nat.sub kT15_1 kT15_0),
    .step 1857 618 7 kT15_1 kM15_1 (Nat.shiftRight kO15_1 31569) (Nat.shiftRight kH15_1 31569) kQ15_1 618 1857 14856 12999 11142 false false,
    .step 1857 618 6 kT15_1 kM15_1 (Nat.shiftRight kO15_1 33426) (Nat.shiftRight kH15_1 33426) kQ15_1 618 1857 12999 11142 9285 false false,
    .step 1857 618 5 kT15_1 kM15_1 (Nat.shiftRight kO15_1 35283) (Nat.shiftRight kH15_1 35283) kQ15_1 618 1857 11142 9285 7428 false false,
    .step 1857 618 4 kT15_1 kM15_1 (Nat.shiftRight kO15_1 37140) (Nat.shiftRight kH15_1 37140) kQ15_1 618 1857 9285 7428 5571 false false,
    .step 1857 618 3 kT15_1 kM15_1 (Nat.shiftRight kO15_1 38997) (Nat.shiftRight kH15_1 38997) kQ15_1 618 1857 7428 5571 3714 false false,
    .step 1857 618 2 kT15_1 kM15_1 (Nat.shiftRight kO15_1 40854) (Nat.shiftRight kH15_1 40854) kQ15_1 618 1857 5571 3714 1857 false false,
    .step 1857 618 1 kT15_1 kM15_1 (Nat.shiftRight kO15_1 42711) (Nat.shiftRight kH15_1 42711) kQ15_1 618 1857 3714 1857 0 false false,
    .step 1857 618 0 kT15_1 kM15_1 (Nat.shiftRight kO15_1 44568) (Nat.shiftRight kH15_1 44568) kQ15_1 618 1857 1857 0 0 false false]

/-- The packed input of band `15`. -/
def init15 (xs : List Nat) : PSt := pinit kT15_0 18788340662190665823115844774314696219005460391266558965658327772257672200916867547709591987078149624255479809 18788340662190665823115844774314696219005460391266558965658327772257672200916867547709591987078149624255479832 [26208, 25116, 24024, 22932, 21840, 20748, 19656, 18564, 17472, 16380, 15288, 14196, 13104, 12012, 10920, 9828, 8736, 7644, 6552, 5460, 4368, 3276, 2184, 1092] [25116, 24024, 22932, 21840, 20748, 19656, 18564, 17472, 16380, 15288, 14196, 13104, 12012, 10920, 9828, 8736, 7644, 6552, 5460, 4368, 3276, 2184, 1092] [23, 22, 21, 20, 19, 18, 17, 16, 15, 14, 13, 12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2] [413343494568194648108548585034923316818120128607864297244483210989668788420171086049611023715719291733620555776, 394555153906003982285432740260608620599114668216597738278824883217411116219254218501901431728641142109365075968, 375766813243813316462316895486293924380109207825331179313166555445153444018337350954191839741562992485109596160, 356978472581622650639201050711979228161103747434064620347508227672895771817420483406482247754484842860854116352, 338190131919431984816085205937664531942098287042798061381849899900638099616503615858772655767406693236598636544, 319401791257241318992969361163349835723092826651531502416191572128380427415586748311063063780328543612343156736, 300613450595050653169853516389035139504087366260264943450533244356122755214669880763353471793250393988087676928, 281825109932859987346737671614720443285081905868998384484874916583865083013753013215643879806172244363832197120, 263036769270669321523621826840405747066076445477731825519216588811607410812836145667934287819094094739576717312, 244248428608478655700505982066091050847070985086465266553558261039349738611919278120224695832015945115321237504, 225460087946287989877390137291776354628065524695198707587899933267092066411002410572515103844937795491065757696, 206671747284097324054274292517461658409060064303932148622241605494834394210085543024805511857859645866810277888, 187883406621906658231158447743146962190054603912665589656583277722576722009168675477095919870781496242554798080, 169095065959715992408042602968832265971049143521399030690924949950319049808251807929386327883703346618299318272, 150306725297525326584926758194517569752043683130132471725266622178061377607334940381676735896625196994043838464, 131518384635334660761810913420202873533038222738865912759608294405803705406418072833967143909547047369788358656, 112730043973143994938695068645888177314032762347599353793949966633546033205501205286257551922468897745532878848, 93941703310953329115579223871573481095027301956332794828291638861288361004584337738547959935390748121277399040, 75153362648762663292463379097258784876021841565066235862633311089030688803667470190838367948312598497021919232, 56365021986571997469347534322944088657016381173799676896974983316773016602750602643128775961234448872766439424, 37576681324381331646231689548629392438010920782533117931316655544515344401833735095419183974156299248510959616, 18788340662190665823115844774314696219005460391266558965658327772257672200916867547709591987078149624255479808] (Nat.shiftRight kO15_0 0) (Nat.shiftRight kO15_0 1092) xs

/-- The structured run of band `15`. -/
def pkRun15 (xs : List Nat) : Nat × Nat :=
  let s := prun acts15 (init15 xs)
  (Nat.add (Nat.shiftLeft s.gv 1) s.gs, s.bad)

/-- Statement of `pkDag15_struct`. -/
def PkDag15Struct : Prop := ∀ f0 f1 f2 f3 f4 f5 f6 f7 f8 f9 f10 f11 f12 f13 f14 f15 f16 f17 f18 f19 f20 f21 f22 f23 f24 : Nat, pkDag15 f0 f1 f2 f3 f4 f5 f6 f7 f8 f9 f10 f11 f12 f13 f14 f15 f16 f17 f18 f19 f20 f21 f22 f23 f24 = pkRun15 [f1, f2, f3, f4, f5, f6, f7, f8, f9, f10, f11, f12, f13, f14, f15, f16, f17, f18, f19, f20, f21, f22, f23, f24]

open Lean Elab Term Command Meta in
/- `pkDag15_struct`: through the variable graph (`pkDag15_eq`, `pkDagC15_eq`), then `rfl`
between two structured terms. Checked by the kernel. -/
run_cmd liftTermElabM do
  let ty ← instantiateMVars (← elabTerm (← `(PkDag15Struct)) none)
  let pf ← instantiateMVars (← elabTerm (← `(fun (f0 f1 f2 f3 f4 f5 f6 f7 f8 f9 f10 f11 f12 f13 f14 f15 f16 f17 f18 f19 f20 f21 f22 f23 f24 : Nat) =>
    Eq.trans (pkDag15_eq f0 f1 f2 f3 f4 f5 f6 f7 f8 f9 f10 f11 f12 f13 f14 f15 f16 f17 f18 f19 f20 f21 f22 f23 f24) (Eq.trans (pkDagC15_eq f0 f1 f2 f3 f4 f5 f6 f7 f8 f9 f10 f11 f12 f13 f14 f15 f16 f17 f18 f19 f20 f21 f22 f23 f24 kO15_0 kH15_0 kT15_0 kM15_0 kQ15_0 kO15_1 kH15_1 kT15_1 kM15_1 kQ15_1 18788340662190665823115844774314696219005460391266558965658327772257672200916867547709591987078149624255479809 18788340662190665823115844774314696219005460391266558965658327772257672200916867547709591987078149624255479832 26208 25116 24024 22932 21840 20748 19656 18564 17472 16380 15288 14196 13104 12012 10920 9828 8736 7644 6552 5460 4368 3276 2184 1092 413343494568194648108548585034923316818120128607864297244483210989668788420171086049611023715719291733620555776 394555153906003982285432740260608620599114668216597738278824883217411116219254218501901431728641142109365075968 375766813243813316462316895486293924380109207825331179313166555445153444018337350954191839741562992485109596160 356978472581622650639201050711979228161103747434064620347508227672895771817420483406482247754484842860854116352 338190131919431984816085205937664531942098287042798061381849899900638099616503615858772655767406693236598636544 319401791257241318992969361163349835723092826651531502416191572128380427415586748311063063780328543612343156736 300613450595050653169853516389035139504087366260264943450533244356122755214669880763353471793250393988087676928 281825109932859987346737671614720443285081905868998384484874916583865083013753013215643879806172244363832197120 263036769270669321523621826840405747066076445477731825519216588811607410812836145667934287819094094739576717312 244248428608478655700505982066091050847070985086465266553558261039349738611919278120224695832015945115321237504 225460087946287989877390137291776354628065524695198707587899933267092066411002410572515103844937795491065757696 206671747284097324054274292517461658409060064303932148622241605494834394210085543024805511857859645866810277888 187883406621906658231158447743146962190054603912665589656583277722576722009168675477095919870781496242554798080 169095065959715992408042602968832265971049143521399030690924949950319049808251807929386327883703346618299318272 150306725297525326584926758194517569752043683130132471725266622178061377607334940381676735896625196994043838464 131518384635334660761810913420202873533038222738865912759608294405803705406418072833967143909547047369788358656 112730043973143994938695068645888177314032762347599353793949966633546033205501205286257551922468897745532878848 93941703310953329115579223871573481095027301956332794828291638861288361004584337738547959935390748121277399040 75153362648762663292463379097258784876021841565066235862633311089030688803667470190838367948312598497021919232 56365021986571997469347534322944088657016381173799676896974983316773016602750602643128775961234448872766439424 37576681324381331646231689548629392438010920782533117931316655544515344401833735095419183974156299248510959616 18788340662190665823115844774314696219005460391266558965658327772257672200916867547709591987078149624255479808 363 (Nat.sub kT15_1 kT15_0) 16713 14856 12999 11142 9285 7428 5571 3714 1857 27855 29712 31569 618 33426 35283 37140 38997 40854 42711 44568) (@rfl (Nat × Nat) (pkRun15 [f1, f2, f3, f4, f5, f6, f7, f8, f9, f10, f11, f12, f13, f14, f15, f16, f17, f18, f19, f20, f21, f22, f23, f24]))))) none)
  addDecl (.thmDecl { name := `Submission.pkDag15_struct, levelParams := [], type := ty, value := pf })

/-- `rep 2115 25` by doubling. -/
def kR205_0 : Nat := natdag% "shl 1 2115
add 1 v0
shl v1 4230
add v1 v2
shl v3 8460
add v3 v4
shl v5 16920
add v5 v6
shl v5 33840
add v7 v8
shl 1 50760
add v9 v10" []
def kO205_0 : Nat := Nat.shiftLeft kR205_0 704
def kH205_0 : Nat := Nat.sub (Nat.shiftLeft kR205_0 2115) (Nat.shiftLeft kR205_0 705)
def kT205_0 : Nat := Nat.shiftLeft 1 704
def kM205_0 : Nat := Nat.sub (Nat.shiftLeft 1 2115) 1
def kQ205_0 : Nat := Nat.sub (Nat.shiftLeft 1 1408) 1

/-- `rep 4107 25` by doubling. -/
def kR205_1 : Nat := natdag% "shl 1 4107
add 1 v0
shl v1 8214
add v1 v2
shl v3 16428
add v3 v4
shl v5 32856
add v5 v6
shl v5 65712
add v7 v8
shl 1 98568
add v9 v10" []
def kO205_1 : Nat := Nat.shiftLeft kR205_1 1368
def kH205_1 : Nat := Nat.sub (Nat.shiftLeft kR205_1 4107) (Nat.shiftLeft kR205_1 1369)
def kT205_1 : Nat := Nat.shiftLeft 1 1368
def kM205_1 : Nat := Nat.sub (Nat.shiftLeft 1 4107) 1
def kQ205_1 : Nat := Nat.sub (Nat.shiftLeft 1 2736) 1

/-- `rep 6159 25` by doubling. -/
def kR205_2 : Nat := natdag% "shl 1 6159
add 1 v0
shl v1 12318
add v1 v2
shl v3 24636
add v3 v4
shl v5 49272
add v5 v6
shl v5 98544
add v7 v8
shl 1 147816
add v9 v10" []
def kO205_2 : Nat := Nat.shiftLeft kR205_2 2052
def kH205_2 : Nat := Nat.sub (Nat.shiftLeft kR205_2 6159) (Nat.shiftLeft kR205_2 2053)
def kT205_2 : Nat := Nat.shiftLeft 1 2052
def kM205_2 : Nat := Nat.sub (Nat.shiftLeft 1 6159) 1
def kQ205_2 : Nat := Nat.sub (Nat.shiftLeft 1 4104) 1

/-- The packed run of band `205` with its lane constants as variables. -/
def pkDagC205 (f0 f1 f2 f3 f4 f5 f6 f7 f8 f9 f10 f11 f12 f13 f14 f15 f16 f17 f18 f19 f20 f21 f22 f23 f24 c0 c1 c2 c3 c4 c5 c6 c7 c8 c9 c10 c11 c12 c13 c14 c15 c16 c17 c18 c19 c20 c21 c22 c23 c24 c25 c26 c27 c28 c29 c30 c31 c32 c33 c34 c35 c36 c37 c38 c39 c40 c41 c42 c43 c44 c45 c46 c47 c48 c49 c50 c51 c52 c53 c54 c55 c56 c57 c58 c59 c60 c61 c62 c63 c64 c65 c66 c67 c68 c69 c70 c71 c72 c73 c74 c75 c76 c77 c78 c79 c80 c81 c82 c83 c84 c85 c86 c87 c88 c89 c90 c91 c92 c93 c94 c95 c96 c97 c98 c99 : Nat) : Nat × Nat :=
  natdag% "shr x26 0
shr x26 x66
shr x1 1
add v2 x28
shl v2 1
land x1 1
mul v4 v5
sub v3 v6
shr x2 1
add v8 x28
shl v8 1
land x2 1
mul v10 v11
sub v9 v12
shr x3 1
add v14 x28
shl v14 1
land x3 1
mul v16 v17
sub v15 v18
shr x4 1
add v20 x28
shl v20 1
land x4 1
mul v22 v23
sub v21 v24
shr x5 1
add v26 x28
shl v26 1
land x5 1
mul v28 v29
sub v27 v30
shr x6 1
add v32 x28
shl v32 1
land x6 1
mul v34 v35
sub v33 v36
shr x7 1
add v38 x28
shl v38 1
land x7 1
mul v40 v41
sub v39 v42
shr x8 1
add v44 x28
shl v44 1
land x8 1
mul v46 v47
sub v45 v48
shr x9 1
add v50 x28
shl v50 1
land x9 1
mul v52 v53
sub v51 v54
shr x10 1
add v56 x28
shl v56 1
land x10 1
mul v58 v59
sub v57 v60
shr x11 1
add v62 x28
shl v62 1
land x11 1
mul v64 v65
sub v63 v66
shr x12 1
add v68 x28
shl v68 1
land x12 1
mul v70 v71
sub v69 v72
shr x13 1
add v74 x28
shl v74 1
land x13 1
mul v76 v77
sub v75 v78
shr x14 1
add v80 x28
shl v80 1
land x14 1
mul v82 v83
sub v81 v84
shr x15 1
add v86 x28
shl v86 1
land x15 1
mul v88 v89
sub v87 v90
shr x16 1
add v92 x28
shl v92 1
land x16 1
mul v94 v95
sub v93 v96
shr x17 1
add v98 x28
shl v98 1
land x17 1
mul v100 v101
sub v99 v102
shr x18 1
add v104 x28
shl v104 1
land x18 1
mul v106 v107
sub v105 v108
shr x19 1
add v110 x28
shl v110 1
land x19 1
mul v112 v113
sub v111 v114
shr x20 1
add v116 x28
shl v116 1
land x20 1
mul v118 v119
sub v117 v120
shr x21 1
add v122 x28
shl v122 1
land x21 1
mul v124 v125
sub v123 v126
shr x22 1
add v128 x28
shl v128 1
land x22 1
mul v130 v131
sub v129 v132
shr x23 1
add v134 x28
shl v134 1
land x23 1
mul v136 v137
sub v135 v138
shr x24 1
add v140 x28
shl v140 1
land x24 1
mul v142 v143
sub v141 v144
mul v7 23
sub v146 x67
mul v13 22
sub v148 x68
mul v19 21
sub v150 x69
mul v25 20
sub v152 x70
mul v31 19
sub v154 x71
mul v37 18
sub v156 x72
mul v43 17
sub v158 x73
mul v49 16
sub v160 x74
mul v55 15
sub v162 x75
mul v61 14
sub v164 x76
mul v67 13
sub v166 x77
mul v73 12
sub v168 x78
mul v79 11
sub v170 x79
mul v85 10
sub v172 x80
mul v91 9
sub v174 x81
mul v97 8
sub v176 x82
mul v103 7
sub v178 x83
mul v109 6
sub v180 x84
mul v115 5
sub v182 x85
mul v121 4
sub v184 x86
mul v127 3
sub v186 x87
mul v133 2
sub v188 x88
shl v139 x66
add v145 v190
shl v133 x65
add v191 v192
shl v127 x64
add v193 v194
shl v121 x63
add v195 v196
shl v115 x62
add v197 v198
shl v109 x61
add v199 v200
shl v103 x60
add v201 v202
shl v97 x59
add v203 v204
shl v91 x58
add v205 v206
shl v85 x57
add v207 v208
shl v79 x56
add v209 v210
shl v73 x55
add v211 v212
shl v67 x54
add v213 v214
shl v61 x53
add v215 v216
shl v55 x52
add v217 v218
shl v49 x51
add v219 v220
shl v43 x50
add v221 v222
shl v37 x49
add v223 v224
shl v31 x48
add v225 v226
shl v25 x47
add v227 v228
shl v19 x46
add v229 v230
shl v13 x45
add v231 v232
shl v7 x44
add v233 v234
shl x41 x43
add v235 v236
sub v237 v0
shl v189 x66
add v139 v239
shl v187 x65
add v240 v241
shl v185 x64
add v242 v243
shl v183 x63
add v244 v245
shl v181 x62
add v246 v247
shl v179 x61
add v248 v249
shl v177 x60
add v250 v251
shl v175 x59
add v252 v253
shl v173 x58
add v254 v255
shl v171 x57
add v256 v257
shl v169 x56
add v258 v259
shl v167 x55
add v260 v261
shl v165 x54
add v262 v263
shl v163 x53
add v264 v265
shl v161 x52
add v266 v267
shl v159 x51
add v268 v269
shl v157 x50
add v270 v271
shl v155 x49
add v272 v273
shl v153 x48
add v274 v275
shl v151 x47
add v276 v277
shl v149 x46
add v278 v279
shl v147 x45
add v280 v281
shl x42 x44
add v282 v283
sub v284 v1
shr x26 x65
shr x27 x65
mul 24 v7
shl 1 x89
add v288 v289
mul 1 v147
shl 24 x89
add v291 v292
sub v290 v293
sub v293 v290
add v294 v295
sub 1 v296
add 0 v297
mul 24 24
mul v299 v238
mul 1 24
shl v301 x66
add v302 v290
sub v303 v293
mul v304 v285
sub v305 v300
sub v300 v305
add v307 v306
add v308 v286
land v309 v287
shr v309 x44
add v310 v311
add v298 v312
shr v309 x45
sub v314 x28
shr v309 x46
land v316 x29
sub 1 v306
sub 1 v318
xor 0 v319
sub 1 v315
add v313 v321
shr x26 x64
shr x27 x64
mul v315 v147
add v325 v292
mul 24 v317
shl v315 x89
add v327 v328
sub v326 v329
sub v329 v326
add v330 v331
sub 1 v332
add v322 v333
mul v315 v315
mul v335 v285
mul 24 v315
shl v337 x66
add v338 v326
sub v339 v329
mul v340 v308
sub v341 v336
sub v336 v341
add v343 v342
div v344 v299
land v345 x30
mul v299 v346
land v347 x30
land v344 x30
sub v349 v348
sub v348 v349
add v350 v351
add v334 v352
add v345 v323
land v354 v324
shr v354 x45
add v355 v356
add v353 v357
shr v354 x46
sub v359 x28
shr v354 x47
land v361 x29
sub 1 v342
sub 1 v363
xor 0 v364
sub 1 v360
add v358 v366
shr x26 x63
shr x27 x63
mul v360 v317
add v370 v328
mul v315 v362
shl v360 x89
add v372 v373
sub v371 v374
sub v374 v371
add v375 v376
sub 1 v377
add v367 v378
mul v360 v360
mul v380 v308
mul v315 v360
shl v382 x66
add v383 v371
sub v384 v374
mul v385 v345
sub v386 v381
sub v381 v386
add v388 v387
div v389 v335
land v390 x30
mul v335 v391
land v392 x30
land v389 x30
sub v394 v393
sub v393 v394
add v395 v396
add v379 v397
add v390 v368
land v399 v369
shr v399 x46
add v400 v401
add v398 v402
shr v399 x47
sub v404 x28
shr v399 x48
land v406 x29
sub 1 v387
sub 1 v408
xor v320 v409
sub 1 v405
add v403 v411
shr x26 x62
shr x27 x62
mul v405 v362
add v415 v373
mul v360 v407
shl v405 x89
add v417 v418
sub v416 v419
sub v419 v416
add v420 v421
sub 1 v422
add v412 v423
mul v405 v405
mul v425 v345
mul v360 v405
shl v427 x66
add v428 v416
sub v429 v419
mul v430 v390
sub v431 v426
sub v426 v431
add v433 v432
div v434 v380
land v435 x30
mul v380 v436
land v437 x30
land v434 x30
sub v439 v438
sub v438 v439
add v440 v441
add v424 v442
add v435 v413
land v444 v414
shr v444 x47
add v445 v446
add v443 v447
shr v444 x48
sub v449 x28
shr v444 x49
land v451 x29
sub 1 v432
sub 1 v453
xor v365 v454
sub 1 v450
add v448 v456
shr x26 x61
shr x27 x61
mul v450 v407
add v460 v418
mul v405 v452
shl v450 x89
add v462 v463
sub v461 v464
sub v464 v461
add v465 v466
sub 1 v467
add v457 v468
mul v450 v450
mul v470 v390
mul v405 v450
shl v472 x66
add v473 v461
sub v474 v464
mul v475 v435
sub v476 v471
sub v471 v476
add v478 v477
div v479 v425
land v480 x30
mul v425 v481
land v482 x30
land v479 x30
sub v484 v483
sub v483 v484
add v485 v486
add v469 v487
add v480 v458
land v489 v459
shr v489 x48
add v490 v491
add v488 v492
shr v489 x49
sub v494 x28
shr v489 x50
land v496 x29
sub 1 v477
sub 1 v498
xor v410 v499
sub 1 v495
add v493 v501
shr x26 x60
shr x27 x60
mul v495 v452
add v505 v463
mul v450 v497
shl v495 x89
add v507 v508
sub v506 v509
sub v509 v506
add v510 v511
sub 1 v512
add v502 v513
mul v495 v495
mul v515 v435
mul v450 v495
shl v517 x66
add v518 v506
sub v519 v509
mul v520 v480
sub v521 v516
sub v516 v521
add v523 v522
div v524 v470
land v525 x30
mul v470 v526
land v527 x30
land v524 x30
sub v529 v528
sub v528 v529
add v530 v531
add v514 v532
add v525 v503
land v534 v504
shr v534 x49
add v535 v536
add v533 v537
shr v534 x50
sub v539 x28
shr v534 x51
land v541 x29
sub 1 v522
sub 1 v543
xor v455 v544
sub 1 v540
add v538 v546
shr x26 x59
shr x27 x59
mul v540 v497
add v550 v508
mul v495 v542
shl v540 x89
add v552 v553
sub v551 v554
sub v554 v551
add v555 v556
sub 1 v557
add v547 v558
mul v540 v540
mul v560 v480
mul v495 v540
shl v562 x66
add v563 v551
sub v564 v554
mul v565 v525
sub v566 v561
sub v561 v566
add v568 v567
div v569 v515
land v570 x30
mul v515 v571
land v572 x30
land v569 x30
sub v574 v573
sub v573 v574
add v575 v576
add v559 v577
add v570 v548
land v579 v549
shr v579 x50
add v580 v581
add v578 v582
shr v579 x51
sub v584 x28
shr v579 x52
land v586 x29
sub 1 v567
sub 1 v588
xor v500 v589
sub 1 v585
add v583 v591
shr x31 x101
shr x31 x100
land v539 x29
shr v534 x52
land v596 x29
shr v534 x53
land v598 x29
shr v534 x54
land v600 x29
shr v534 x55
land v602 x29
shr v534 x56
land v604 x29
shr v534 x57
land v606 x29
shr v534 x58
land v608 x29
shr v534 x59
land v610 x29
shr v534 x60
land v612 x29
shr v534 x61
land v614 x29
shr v534 x62
land v616 x29
shr v534 x63
land v618 x29
shr v534 x64
land v620 x29
shr v534 x65
land v622 x29
shr v534 x66
land v624 x29
shr v534 0
land v626 x29
add v595 x90
add v542 x90
add v597 x90
add v599 x90
add v601 x90
add v603 x90
add v605 x90
add v607 x90
add v609 x90
add v611 x90
add v613 x90
add v615 x90
add v617 x90
add v619 x90
add v621 x90
add v623 x90
add v625 x90
add v627 x90
land v584 x29
shr v579 x53
land v647 x29
shr v579 x54
land v649 x29
shr v579 x55
land v651 x29
shr v579 x56
land v653 x29
shr v579 x57
land v655 x29
shr v579 x58
land v657 x29
shr v579 x59
land v659 x29
shr v579 x60
land v661 x29
shr v579 x61
land v663 x29
shr v579 x62
land v665 x29
shr v579 x63
land v667 x29
shr v579 x64
land v669 x29
shr v579 x65
land v671 x29
shr v579 x66
land v673 x29
shr v579 0
land v675 x29
add v646 x90
add v587 x90
add v648 x90
add v650 x90
add v652 x90
add v654 x90
add v656 x90
add v658 x90
add v660 x90
add v662 x90
add v664 x90
add v666 x90
add v668 x90
add v670 x90
add v672 x90
add v674 x90
add v676 x90
shl v644 x107
add v645 v694
shl v643 x106
add v695 v696
shl v642 x105
add v697 v698
shl v641 x104
add v699 v700
shl v640 x103
add v701 v702
shl v639 x102
add v703 v704
shl v638 x101
add v705 v706
shl v637 x100
add v707 v708
shl v636 x99
add v709 v710
shl v635 x98
add v711 v712
shl v634 x97
add v713 v714
shl v633 x96
add v715 v716
shl v632 x95
add v717 v718
shl v631 x94
add v719 v720
shl v630 x93
add v721 v722
shl v629 x92
add v723 v724
shl v628 x91
add v725 v726
sub v727 v593
shl v692 x107
add v693 v729
shl v691 x106
add v730 v731
shl v690 x105
add v732 v733
shl v689 x104
add v734 v735
shl v688 x103
add v736 v737
shl v687 x102
add v738 v739
shl v686 x101
add v740 v741
shl v685 x100
add v742 v743
shl v684 x99
add v744 v745
shl v683 x98
add v746 v747
shl v682 x97
add v748 v749
shl v681 x96
add v750 v751
shl v680 x95
add v752 v753
shl v679 x94
add v754 v755
shl v678 x93
add v756 v757
shl v677 x92
add v758 v759
sub v760 v594
shr x31 x99
shr x32 x99
mul v585 v629
shl v540 x108
add v764 v765
mul v540 v678
shl v585 x108
add v767 v768
sub v766 v769
sub v769 v766
add v770 v771
sub 1 v772
add v592 v773
mul v585 v585
mul v775 v728
mul v540 v585
shl v777 x107
add v778 v766
sub v779 v769
mul v780 v761
sub v781 v776
sub v776 v781
add v783 v782
div v784 v560
land v785 x35
mul v560 v786
land v787 x35
land v784 x35
sub v789 v788
sub v788 v789
add v790 v791
add v774 v792
add v785 v762
land v794 v763
shr v794 x92
add v795 v796
add v793 v797
shr v794 x93
sub v799 x33
shr v794 x94
land v801 x34
sub 1 v782
sub 1 v803
xor v545 v804
sub 1 v800
add v798 v806
shr x31 x98
shr x32 x98
mul v800 v678
add v810 v768
mul v585 v802
shl v800 x108
add v812 v813
sub v811 v814
sub v814 v811
add v815 v816
sub 1 v817
add v807 v818
mul v800 v800
mul v820 v761
mul v585 v800
shl v822 x107
add v823 v811
sub v824 v814
mul v825 v785
sub v826 v821
sub v821 v826
add v828 v827
div v829 v775
land v830 x35
mul v775 v831
land v832 x35
land v829 x35
sub v834 v833
sub v833 v834
add v835 v836
add v819 v837
add v830 v808
land v839 v809
shr v839 x93
add v840 v841
add v838 v842
shr v839 x94
sub v844 x33
shr v839 x95
land v846 x34
sub 1 v827
sub 1 v848
xor v590 v849
sub 1 v845
add v843 v851
shr x31 x97
shr x32 x97
mul v845 v802
add v855 v813
mul v800 v847
shl v845 x108
add v857 v858
sub v856 v859
sub v859 v856
add v860 v861
sub 1 v862
add v852 v863
mul v845 v845
mul v865 v785
mul v800 v845
shl v867 x107
add v868 v856
sub v869 v859
mul v870 v830
sub v871 v866
sub v866 v871
add v873 v872
div v874 v820
land v875 x35
mul v820 v876
land v877 x35
land v874 x35
sub v879 v878
sub v878 v879
add v880 v881
add v864 v882
add v875 v853
land v884 v854
shr v884 x94
add v885 v886
add v883 v887
shr v884 x95
sub v889 x33
shr v884 x96
land v891 x34
sub 1 v872
sub 1 v893
xor v805 v894
sub 1 v890
add v888 v896
shr x31 x96
shr x32 x96
mul v890 v847
add v900 v858
mul v845 v892
shl v890 x108
add v902 v903
sub v901 v904
sub v904 v901
add v905 v906
sub 1 v907
add v897 v908
mul v890 v890
mul v910 v830
mul v845 v890
shl v912 x107
add v913 v901
sub v914 v904
mul v915 v875
sub v916 v911
sub v911 v916
add v918 v917
div v919 v865
land v920 x35
mul v865 v921
land v922 x35
land v919 x35
sub v924 v923
sub v923 v924
add v925 v926
add v909 v927
add v920 v898
land v929 v899
shr v929 x95
add v930 v931
add v928 v932
shr v929 x96
sub v934 x33
shr v929 x97
land v936 x34
sub 1 v917
sub 1 v938
xor v850 v939
sub 1 v935
add v933 v941
shr x36 x112
shr x36 x111
land v889 x34
shr v884 x97
land v946 x34
shr v884 x98
land v948 x34
shr v884 x99
land v950 x34
shr v884 x100
land v952 x34
shr v884 x101
land v954 x34
shr v884 x102
land v956 x34
shr v884 x103
land v958 x34
shr v884 x104
land v960 x34
shr v884 x105
land v962 x34
shr v884 x106
land v964 x34
shr v884 x107
land v966 x34
shr v884 0
land v968 x34
add v945 x109
add v892 x109
add v947 x109
add v949 x109
add v951 x109
add v953 x109
add v955 x109
add v957 x109
add v959 x109
add v961 x109
add v963 x109
add v965 x109
add v967 x109
add v969 x109
land v934 x34
shr v929 x98
land v985 x34
shr v929 x99
land v987 x34
shr v929 x100
land v989 x34
shr v929 x101
land v991 x34
shr v929 x102
land v993 x34
shr v929 x103
land v995 x34
shr v929 x104
land v997 x34
shr v929 x105
land v999 x34
shr v929 x106
land v1001 x34
shr v929 x107
land v1003 x34
shr v929 0
land v1005 x34
add v984 x109
add v937 x109
add v986 x109
add v988 x109
add v990 x109
add v992 x109
add v994 x109
add v996 x109
add v998 x109
add v1000 x109
add v1002 x109
add v1004 x109
add v1006 x109
shl v982 x122
add v983 v1020
shl v981 x121
add v1021 v1022
shl v980 x120
add v1023 v1024
shl v979 x119
add v1025 v1026
shl v978 x118
add v1027 v1028
shl v977 x117
add v1029 v1030
shl v976 x116
add v1031 v1032
shl v975 x115
add v1033 v1034
shl v974 x114
add v1035 v1036
shl v973 x113
add v1037 v1038
shl v972 x112
add v1039 v1040
shl v971 x111
add v1041 v1042
shl v970 x110
add v1043 v1044
sub v1045 v943
shl v1018 x122
add v1019 v1047
shl v1017 x121
add v1048 v1049
shl v1016 x120
add v1050 v1051
shl v1015 x119
add v1052 v1053
shl v1014 x118
add v1054 v1055
shl v1013 x117
add v1056 v1057
shl v1012 x116
add v1058 v1059
shl v1011 x115
add v1060 v1061
shl v1010 x114
add v1062 v1063
shl v1009 x113
add v1064 v1065
shl v1008 x112
add v1066 v1067
shl v1007 x111
add v1068 v1069
sub v1070 v944
shr x36 x110
shr x37 x110
mul v935 v971
shl v890 x123
add v1074 v1075
mul v890 v1008
shl v935 x123
add v1077 v1078
sub v1076 v1079
sub v1079 v1076
add v1080 v1081
sub 1 v1082
add v942 v1083
mul v935 v935
mul v1085 v1046
mul v890 v935
shl v1087 x122
add v1088 v1076
sub v1089 v1079
mul v1090 v1071
sub v1091 v1086
sub v1086 v1091
add v1093 v1092
div v1094 v910
land v1095 x40
mul v910 v1096
land v1097 x40
land v1094 x40
sub v1099 v1098
sub v1098 v1099
add v1100 v1101
add v1084 v1102
add v1095 v1072
land v1104 v1073
shr v1104 x111
add v1105 v1106
add v1103 v1107
shr v1104 x112
sub v1109 x38
shr v1104 x113
land v1111 x39
sub 1 v1092
sub 1 v1113
xor v895 v1114
sub 1 v1110
add v1108 v1116
shr x36 x124
shr x37 x124
mul v1110 v1008
add v1120 v1078
mul v935 v1112
shl v1110 x123
add v1122 v1123
sub v1121 v1124
sub v1124 v1121
add v1125 v1126
sub 1 v1127
add v1117 v1128
mul v1110 v1110
mul v1130 v1071
mul v935 v1110
shl v1132 x122
add v1133 v1121
sub v1134 v1124
mul v1135 v1095
sub v1136 v1131
sub v1131 v1136
add v1138 v1137
div v1139 v1085
land v1140 x40
mul v1085 v1141
land v1142 x40
land v1139 x40
sub v1144 v1143
sub v1143 v1144
add v1145 v1146
add v1129 v1147
add v1140 v1118
land v1149 v1119
shr v1149 x112
add v1150 v1151
add v1148 v1152
shr v1149 x113
sub v1154 x38
shr v1149 x114
land v1156 x39
sub 1 v1137
sub 1 v1158
xor v940 v1159
sub 1 v1155
add v1153 v1161
shr x36 x125
shr x37 x125
mul v1155 v1112
add v1165 v1123
mul v1110 v1157
shl v1155 x123
add v1167 v1168
sub v1166 v1169
sub v1169 v1166
add v1170 v1171
sub 1 v1172
add v1162 v1173
mul v1155 v1155
mul v1175 v1095
mul v1110 v1155
shl v1177 x122
add v1178 v1166
sub v1179 v1169
mul v1180 v1140
sub v1181 v1176
sub v1176 v1181
add v1183 v1182
div v1184 v1130
land v1185 x40
mul v1130 v1186
land v1187 x40
land v1184 x40
sub v1189 v1188
sub v1188 v1189
add v1190 v1191
add v1174 v1192
add v1185 v1163
land v1194 v1164
shr v1194 x113
add v1195 v1196
add v1193 v1197
shr v1194 x114
sub v1199 x38
shr v1194 x115
land v1201 x39
sub 1 v1182
sub 1 v1203
xor v1115 v1204
sub 1 v1200
add v1198 v1206
land v1154 x39
shr v1149 x115
land v1209 x39
shr v1149 x116
land v1211 x39
shr v1149 x117
land v1213 x39
shr v1149 x118
land v1215 x39
shr v1149 x119
land v1217 x39
shr v1149 x120
land v1219 x39
shr v1149 x121
land v1221 x39
shr v1149 x122
land v1223 x39
shr v1149 0
land v1225 x39
sub v1208 x38
sub x38 v1208
add v1227 v1228
shl v1229 1
sub 1 v1228
sub 1 v1231
xor v1232 v1160
add v1230 v1233
sub v1157 x38
sub x38 v1157
add v1235 v1236
shl v1237 1
sub 1 v1236
sub 1 v1239
xor v1240 v1160
add v1238 v1241
sub v1210 x38
sub x38 v1210
add v1243 v1244
shl v1245 1
sub 1 v1244
sub 1 v1247
xor v1248 v1160
add v1246 v1249
sub v1212 x38
sub x38 v1212
add v1251 v1252
shl v1253 1
sub 1 v1252
sub 1 v1255
xor v1256 v1160
add v1254 v1257
sub v1214 x38
sub x38 v1214
add v1259 v1260
shl v1261 1
sub 1 v1260
sub 1 v1263
xor v1264 v1160
add v1262 v1265
sub v1216 x38
sub x38 v1216
add v1267 v1268
shl v1269 1
sub 1 v1268
sub 1 v1271
xor v1272 v1160
add v1270 v1273
sub v1218 x38
sub x38 v1218
add v1275 v1276
shl v1277 1
sub 1 v1276
sub 1 v1279
xor v1280 v1160
add v1278 v1281
sub v1220 x38
sub x38 v1220
add v1283 v1284
shl v1285 1
sub 1 v1284
sub 1 v1287
xor v1288 v1160
add v1286 v1289
sub v1222 x38
sub x38 v1222
add v1291 v1292
shl v1293 1
sub 1 v1292
sub 1 v1295
xor v1296 v1160
add v1294 v1297
sub v1224 x38
sub x38 v1224
add v1299 v1300
shl v1301 1
sub 1 v1300
sub 1 v1303
xor v1304 v1160
add v1302 v1305
sub v1226 x38
sub x38 v1226
add v1307 v1308
shl v1309 1
sub 1 v1308
sub 1 v1311
xor v1312 v1160
add v1310 v1313
land v1199 x39
shr v1194 x116
land v1316 x39
shr v1194 x117
land v1318 x39
shr v1194 x118
land v1320 x39
shr v1194 x119
land v1322 x39
shr v1194 x120
land v1324 x39
shr v1194 x121
land v1326 x39
shr v1194 x122
land v1328 x39
shr v1194 0
land v1330 x39
sub v1315 x38
sub x38 v1315
add v1332 v1333
shl v1334 1
sub 1 v1333
sub 1 v1336
xor v1337 v1205
add v1335 v1338
sub v1202 x38
sub x38 v1202
add v1340 v1341
shl v1342 1
sub 1 v1341
sub 1 v1344
xor v1345 v1205
add v1343 v1346
sub v1317 x38
sub x38 v1317
add v1348 v1349
shl v1350 1
sub 1 v1349
sub 1 v1352
xor v1353 v1205
add v1351 v1354
sub v1319 x38
sub x38 v1319
add v1356 v1357
shl v1358 1
sub 1 v1357
sub 1 v1360
xor v1361 v1205
add v1359 v1362
sub v1321 x38
sub x38 v1321
add v1364 v1365
shl v1366 1
sub 1 v1365
sub 1 v1368
xor v1369 v1205
add v1367 v1370
sub v1323 x38
sub x38 v1323
add v1372 v1373
shl v1374 1
sub 1 v1373
sub 1 v1376
xor v1377 v1205
add v1375 v1378
sub v1325 x38
sub x38 v1325
add v1380 v1381
shl v1382 1
sub 1 v1381
sub 1 v1384
xor v1385 v1205
add v1383 v1386
sub v1327 x38
sub x38 v1327
add v1388 v1389
shl v1390 1
sub 1 v1389
sub 1 v1392
xor v1393 v1205
add v1391 v1394
sub v1329 x38
sub x38 v1329
add v1396 v1397
shl v1398 1
sub 1 v1397
sub 1 v1400
xor v1401 v1205
add v1399 v1402
sub v1331 x38
sub x38 v1331
add v1404 v1405
shl v1406 1
sub 1 v1405
sub 1 v1408
xor v1409 v1205
add v1407 v1410
shr v1234 1
mul v1412 v1412
shr v1339 1
mul v1414 v1414
mul v1414 v1412
xor v1339 v1234
land v1417 1
xor v1418 1
shr v1242 1
mul v1414 v1420
shr v1347 1
mul v1412 v1422
add v1421 v1423
xor v1339 v1242
land v1425 1
mul v1426 v1421
xor v1234 v1347
land v1428 1
xor v1429 1
mul v1430 v1423
add v1427 v1431
sub v1424 v1432
sub v1433 v1432
sub v1432 v1433
add v1434 v1435
div v1436 1
shl v1437 1
sub 1 v1435
sub 1 v1439
add v1438 v1440
shr v1441 1
land v1441 1
xor v1443 1
shr v1250 1
mul v1415 v1445
shr v1355 1
mul v1416 v1447
add v1446 v1448
mul v1442 v1422
add v1449 v1450
land v1250 1
mul v1452 v1446
land v1355 1
xor v1454 v1419
mul v1455 v1448
add v1453 v1456
land v1347 1
xor v1458 v1444
mul v1459 v1450
add v1457 v1460
sub v1451 v1461
sub v1462 v1461
sub v1461 v1462
add v1463 v1464
div v1465 v1413
shl v1466 1
sub 1 v1464
sub 1 v1468
add v1467 v1469
shr v1258 1
mul v1415 v1471
shr v1363 1
mul v1416 v1473
add v1472 v1474
mul v1442 v1447
add v1475 v1476
land v1258 1
mul v1478 v1472
land v1363 1
xor v1480 v1419
mul v1481 v1474
add v1479 v1482
xor v1454 v1444
mul v1484 v1476
add v1483 v1485
sub v1477 v1486
sub v1487 v1486
sub v1486 v1487
add v1488 v1489
div v1490 v1413
shl v1491 1
sub 1 v1489
sub 1 v1493
add v1492 v1494
shr v1266 1
mul v1415 v1496
shr v1371 1
mul v1416 v1498
add v1497 v1499
mul v1442 v1473
add v1500 v1501
land v1266 1
mul v1503 v1497
land v1371 1
xor v1505 v1419
mul v1506 v1499
add v1504 v1507
xor v1480 v1444
mul v1509 v1501
add v1508 v1510
sub v1502 v1511
sub v1512 v1511
sub v1511 v1512
add v1513 v1514
div v1515 v1413
shl v1516 1
sub 1 v1514
sub 1 v1518
add v1517 v1519
shr v1274 1
mul v1415 v1521
shr v1379 1
mul v1416 v1523
add v1522 v1524
mul v1442 v1498
add v1525 v1526
land v1274 1
mul v1528 v1522
land v1379 1
xor v1530 v1419
mul v1531 v1524
add v1529 v1532
xor v1505 v1444
mul v1534 v1526
add v1533 v1535
sub v1527 v1536
sub v1537 v1536
sub v1536 v1537
add v1538 v1539
div v1540 v1413
shl v1541 1
sub 1 v1539
sub 1 v1543
add v1542 v1544
shr v1282 1
mul v1415 v1546
shr v1387 1
mul v1416 v1548
add v1547 v1549
mul v1442 v1523
add v1550 v1551
land v1282 1
mul v1553 v1547
land v1387 1
xor v1555 v1419
mul v1556 v1549
add v1554 v1557
xor v1530 v1444
mul v1559 v1551
add v1558 v1560
sub v1552 v1561
sub v1562 v1561
sub v1561 v1562
add v1563 v1564
div v1565 v1413
shl v1566 1
sub 1 v1564
sub 1 v1568
add v1567 v1569
shr v1290 1
mul v1415 v1571
shr v1395 1
mul v1416 v1573
add v1572 v1574
mul v1442 v1548
add v1575 v1576
land v1290 1
mul v1578 v1572
land v1395 1
xor v1580 v1419
mul v1581 v1574
add v1579 v1582
xor v1555 v1444
mul v1584 v1576
add v1583 v1585
sub v1577 v1586
sub v1587 v1586
sub v1586 v1587
add v1588 v1589
div v1590 v1413
shl v1591 1
sub 1 v1589
sub 1 v1593
add v1592 v1594
shr v1298 1
mul v1415 v1596
shr v1403 1
mul v1416 v1598
add v1597 v1599
mul v1442 v1573
add v1600 v1601
land v1298 1
mul v1603 v1597
land v1403 1
xor v1605 v1419
mul v1606 v1599
add v1604 v1607
xor v1580 v1444
mul v1609 v1601
add v1608 v1610
sub v1602 v1611
sub v1612 v1611
sub v1611 v1612
add v1613 v1614
div v1615 v1413
shl v1616 1
sub 1 v1614
sub 1 v1618
add v1617 v1619
shr v1306 1
mul v1415 v1621
shr v1411 1
mul v1416 v1623
add v1622 v1624
mul v1442 v1598
add v1625 v1626
land v1306 1
mul v1628 v1622
land v1411 1
xor v1630 v1419
mul v1631 v1624
add v1629 v1632
xor v1605 v1444
mul v1634 v1626
add v1633 v1635
sub v1627 v1636
sub v1637 v1636
sub v1636 v1637
add v1638 v1639
div v1640 v1413
shl v1641 1
sub 1 v1639
sub 1 v1643
add v1642 v1644
shr v1314 1
mul v1415 v1646
shr 0 1
mul v1416 v1648
add v1647 v1649
mul v1442 v1623
add v1650 v1651
land v1314 1
mul v1653 v1647
land 0 1
xor v1655 v1419
mul v1656 v1649
add v1654 v1657
xor v1630 v1444
mul v1659 v1651
add v1658 v1660
sub v1652 v1661
sub v1662 v1661
sub v1661 v1662
add v1663 v1664
div v1665 v1413
shl v1666 1
sub 1 v1664
sub 1 v1668
add v1667 v1669
sub 1 v1442
add v1665 0
add v1640 v1672
add v1615 v1673
add v1590 v1674
add v1565 v1675
add v1540 v1676
add v1515 v1677
add v1490 v1678
add v1465 v1679
add v1666 0
add v1641 v1681
add v1616 v1682
add v1591 v1683
add v1566 v1684
add v1541 v1685
add v1516 v1686
add v1491 v1687
add v1466 v1688
mul v1413 v1689
sub v1680 v1690
add v1671 v1691
shr v1470 1
sub 1 v1693
add v1692 v1694
add v1207 v1695
mul v1693 v1693
mul v1693 v1414
xor v1470 v1339
land v1699 1
xor v1700 1
mul v1693 v1422
shr v1495 1
mul v1414 v1703
add v1702 v1704
xor v1470 v1347
land v1706 1
mul v1707 v1702
xor v1339 v1495
land v1709 1
xor v1710 1
mul v1711 v1704
add v1708 v1712
sub v1705 v1713
sub v1714 v1713
sub v1713 v1714
add v1715 v1716
div v1717 1
shl v1718 1
sub 1 v1716
sub 1 v1720
add v1719 v1721
shr v1722 1
land v1722 1
xor v1724 1
mul v1697 v1447
shr v1520 1
mul v1698 v1727
add v1726 v1728
mul v1723 v1703
add v1729 v1730
mul v1454 v1726
land v1520 1
xor v1733 v1701
mul v1734 v1728
add v1732 v1735
land v1495 1
xor v1737 v1725
mul v1738 v1730
add v1736 v1739
sub v1731 v1740
sub v1741 v1740
sub v1740 v1741
add v1742 v1743
div v1744 v1415
shl v1745 1
sub 1 v1743
sub 1 v1747
add v1746 v1748
mul v1697 v1473
shr v1545 1
mul v1698 v1751
add v1750 v1752
mul v1723 v1727
add v1753 v1754
mul v1480 v1750
land v1545 1
xor v1757 v1701
mul v1758 v1752
add v1756 v1759
xor v1733 v1725
mul v1761 v1754
add v1760 v1762
sub v1755 v1763
sub v1764 v1763
sub v1763 v1764
add v1765 v1766
div v1767 v1415
shl v1768 1
sub 1 v1766
sub 1 v1770
add v1769 v1771
mul v1697 v1498
shr v1570 1
mul v1698 v1774
add v1773 v1775
mul v1723 v1751
add v1776 v1777
mul v1505 v1773
land v1570 1
xor v1780 v1701
mul v1781 v1775
add v1779 v1782
xor v1757 v1725
mul v1784 v1777
add v1783 v1785
sub v1778 v1786
sub v1787 v1786
sub v1786 v1787
add v1788 v1789
div v1790 v1415
shl v1791 1
sub 1 v1789
sub 1 v1793
add v1792 v1794
mul v1697 v1523
shr v1595 1
mul v1698 v1797
add v1796 v1798
mul v1723 v1774
add v1799 v1800
mul v1530 v1796
land v1595 1
xor v1803 v1701
mul v1804 v1798
add v1802 v1805
xor v1780 v1725
mul v1807 v1800
add v1806 v1808
sub v1801 v1809
sub v1810 v1809
sub v1809 v1810
add v1811 v1812
div v1813 v1415
shl v1814 1
sub 1 v1812
sub 1 v1816
add v1815 v1817
mul v1697 v1548
shr v1620 1
mul v1698 v1820
add v1819 v1821
mul v1723 v1797
add v1822 v1823
mul v1555 v1819
land v1620 1
xor v1826 v1701
mul v1827 v1821
add v1825 v1828
xor v1803 v1725
mul v1830 v1823
add v1829 v1831
sub v1824 v1832
sub v1833 v1832
sub v1832 v1833
add v1834 v1835
div v1836 v1415
shl v1837 1
sub 1 v1835
sub 1 v1839
add v1838 v1840
mul v1697 v1573
shr v1645 1
mul v1698 v1843
add v1842 v1844
mul v1723 v1820
add v1845 v1846
mul v1580 v1842
land v1645 1
xor v1849 v1701
mul v1850 v1844
add v1848 v1851
xor v1826 v1725
mul v1853 v1846
add v1852 v1854
sub v1847 v1855
sub v1856 v1855
sub v1855 v1856
add v1857 v1858
div v1859 v1415
shl v1860 1
sub 1 v1858
sub 1 v1862
add v1861 v1863
mul v1697 v1598
shr v1670 1
mul v1698 v1866
add v1865 v1867
mul v1723 v1843
add v1868 v1869
mul v1605 v1865
land v1670 1
xor v1872 v1701
mul v1873 v1867
add v1871 v1874
xor v1849 v1725
mul v1876 v1869
add v1875 v1877
sub v1870 v1878
sub v1879 v1878
sub v1878 v1879
add v1880 v1881
div v1882 v1415
shl v1883 1
sub 1 v1881
sub 1 v1885
add v1884 v1886
mul v1697 v1623
mul v1698 v1648
add v1888 v1889
mul v1723 v1866
add v1890 v1891
mul v1630 v1888
xor v1655 v1701
mul v1894 v1889
add v1893 v1895
xor v1872 v1725
mul v1897 v1891
add v1896 v1898
sub v1892 v1899
sub v1900 v1899
sub v1899 v1900
add v1901 v1902
div v1903 v1415
shl v1904 1
sub 1 v1902
sub 1 v1906
add v1905 v1907
sub 1 v1723
add v1903 0
add v1882 v1910
add v1859 v1911
add v1836 v1912
add v1813 v1913
add v1790 v1914
add v1767 v1915
add v1744 v1916
add v1904 0
add v1883 v1918
add v1860 v1919
add v1837 v1920
add v1814 v1921
add v1791 v1922
add v1768 v1923
add v1745 v1924
mul v1415 v1925
sub v1917 v1926
add v1909 v1927
shr v1749 1
sub 1 v1929
add v1928 v1930
add v1696 v1931
mul v1929 v1929
mul v1929 v1693
xor v1749 v1470
land v1935 1
xor v1936 1
mul v1929 v1703
shr v1772 1
mul v1693 v1939
add v1938 v1940
xor v1749 v1495
land v1942 1
mul v1943 v1938
xor v1470 v1772
land v1945 1
xor v1946 1
mul v1947 v1940
add v1944 v1948
sub v1941 v1949
sub v1950 v1949
sub v1949 v1950
add v1951 v1952
div v1953 1
shl v1954 1
sub 1 v1952
sub 1 v1956
add v1955 v1957
shr v1958 1
land v1958 1
xor v1960 1
mul v1933 v1727
shr v1795 1
mul v1934 v1963
add v1962 v1964
mul v1959 v1939
add v1965 v1966
mul v1733 v1962
land v1795 1
xor v1969 v1937
mul v1970 v1964
add v1968 v1971
land v1772 1
xor v1973 v1961
mul v1974 v1966
add v1972 v1975
sub v1967 v1976
sub v1977 v1976
sub v1976 v1977
add v1978 v1979
div v1980 v1697
shl v1981 1
sub 1 v1979
sub 1 v1983
add v1982 v1984
mul v1933 v1751
shr v1818 1
mul v1934 v1987
add v1986 v1988
mul v1959 v1963
add v1989 v1990
mul v1757 v1986
land v1818 1
xor v1993 v1937
mul v1994 v1988
add v1992 v1995
xor v1969 v1961
mul v1997 v1990
add v1996 v1998
sub v1991 v1999
sub v2000 v1999
sub v1999 v2000
add v2001 v2002
div v2003 v1697
shl v2004 1
sub 1 v2002
sub 1 v2006
add v2005 v2007
mul v1933 v1774
shr v1841 1
mul v1934 v2010
add v2009 v2011
mul v1959 v1987
add v2012 v2013
mul v1780 v2009
land v1841 1
xor v2016 v1937
mul v2017 v2011
add v2015 v2018
xor v1993 v1961
mul v2020 v2013
add v2019 v2021
sub v2014 v2022
sub v2023 v2022
sub v2022 v2023
add v2024 v2025
div v2026 v1697
shl v2027 1
sub 1 v2025
sub 1 v2029
add v2028 v2030
mul v1933 v1797
shr v1864 1
mul v1934 v2033
add v2032 v2034
mul v1959 v2010
add v2035 v2036
mul v1803 v2032
land v1864 1
xor v2039 v1937
mul v2040 v2034
add v2038 v2041
xor v2016 v1961
mul v2043 v2036
add v2042 v2044
sub v2037 v2045
sub v2046 v2045
sub v2045 v2046
add v2047 v2048
div v2049 v1697
shl v2050 1
sub 1 v2048
sub 1 v2052
add v2051 v2053
mul v1933 v1820
shr v1887 1
mul v1934 v2056
add v2055 v2057
mul v1959 v2033
add v2058 v2059
mul v1826 v2055
land v1887 1
xor v2062 v1937
mul v2063 v2057
add v2061 v2064
xor v2039 v1961
mul v2066 v2059
add v2065 v2067
sub v2060 v2068
sub v2069 v2068
sub v2068 v2069
add v2070 v2071
div v2072 v1697
shl v2073 1
sub 1 v2071
sub 1 v2075
add v2074 v2076
mul v1933 v1843
shr v1908 1
mul v1934 v2079
add v2078 v2080
mul v1959 v2056
add v2081 v2082
mul v1849 v2078
land v1908 1
xor v2085 v1937
mul v2086 v2080
add v2084 v2087
xor v2062 v1961
mul v2089 v2082
add v2088 v2090
sub v2083 v2091
sub v2092 v2091
sub v2091 v2092
add v2093 v2094
div v2095 v1697
shl v2096 1
sub 1 v2094
sub 1 v2098
add v2097 v2099
mul v1933 v1866
mul v1934 v1648
add v2101 v2102
mul v1959 v2079
add v2103 v2104
mul v1872 v2101
xor v1655 v1937
mul v2107 v2102
add v2106 v2108
xor v2085 v1961
mul v2110 v2104
add v2109 v2111
sub v2105 v2112
sub v2113 v2112
sub v2112 v2113
add v2114 v2115
div v2116 v1697
shl v2117 1
sub 1 v2115
sub 1 v2119
add v2118 v2120
sub 1 v1959
add v2116 0
add v2095 v2123
add v2072 v2124
add v2049 v2125
add v2026 v2126
add v2003 v2127
add v1980 v2128
add v2117 0
add v2096 v2130
add v2073 v2131
add v2050 v2132
add v2027 v2133
add v2004 v2134
add v1981 v2135
mul v1697 v2136
sub v2129 v2137
add v2122 v2138
shr v1985 1
sub 1 v2140
add v2139 v2141
add v1932 v2142
mul v2140 v2140
mul v2140 v1929
xor v1985 v1749
land v2146 1
xor v2147 1
mul v2140 v1939
shr v2008 1
mul v1929 v2150
add v2149 v2151
xor v1985 v1772
land v2153 1
mul v2154 v2149
xor v1749 v2008
land v2156 1
xor v2157 1
mul v2158 v2151
add v2155 v2159
sub v2152 v2160
sub v2161 v2160
sub v2160 v2161
add v2162 v2163
div v2164 1
shl v2165 1
sub 1 v2163
sub 1 v2167
add v2166 v2168
shr v2169 1
land v2169 1
xor v2171 1
mul v2144 v1963
shr v2031 1
mul v2145 v2174
add v2173 v2175
mul v2170 v2150
add v2176 v2177
mul v1969 v2173
land v2031 1
xor v2180 v2148
mul v2181 v2175
add v2179 v2182
land v2008 1
xor v2184 v2172
mul v2185 v2177
add v2183 v2186
sub v2178 v2187
sub v2188 v2187
sub v2187 v2188
add v2189 v2190
div v2191 v1933
shl v2192 1
sub 1 v2190
sub 1 v2194
add v2193 v2195
mul v2144 v1987
shr v2054 1
mul v2145 v2198
add v2197 v2199
mul v2170 v2174
add v2200 v2201
mul v1993 v2197
land v2054 1
xor v2204 v2148
mul v2205 v2199
add v2203 v2206
xor v2180 v2172
mul v2208 v2201
add v2207 v2209
sub v2202 v2210
sub v2211 v2210
sub v2210 v2211
add v2212 v2213
div v2214 v1933
shl v2215 1
sub 1 v2213
sub 1 v2217
add v2216 v2218
mul v2144 v2010
shr v2077 1
mul v2145 v2221
add v2220 v2222
mul v2170 v2198
add v2223 v2224
mul v2016 v2220
land v2077 1
xor v2227 v2148
mul v2228 v2222
add v2226 v2229
xor v2204 v2172
mul v2231 v2224
add v2230 v2232
sub v2225 v2233
sub v2234 v2233
sub v2233 v2234
add v2235 v2236
div v2237 v1933
shl v2238 1
sub 1 v2236
sub 1 v2240
add v2239 v2241
mul v2144 v2033
shr v2100 1
mul v2145 v2244
add v2243 v2245
mul v2170 v2221
add v2246 v2247
mul v2039 v2243
land v2100 1
xor v2250 v2148
mul v2251 v2245
add v2249 v2252
xor v2227 v2172
mul v2254 v2247
add v2253 v2255
sub v2248 v2256
sub v2257 v2256
sub v2256 v2257
add v2258 v2259
div v2260 v1933
shl v2261 1
sub 1 v2259
sub 1 v2263
add v2262 v2264
mul v2144 v2056
shr v2121 1
mul v2145 v2267
add v2266 v2268
mul v2170 v2244
add v2269 v2270
mul v2062 v2266
land v2121 1
xor v2273 v2148
mul v2274 v2268
add v2272 v2275
xor v2250 v2172
mul v2277 v2270
add v2276 v2278
sub v2271 v2279
sub v2280 v2279
sub v2279 v2280
add v2281 v2282
div v2283 v1933
shl v2284 1
sub 1 v2282
sub 1 v2286
add v2285 v2287
mul v2144 v2079
mul v2145 v1648
add v2289 v2290
mul v2170 v2267
add v2291 v2292
mul v2085 v2289
xor v1655 v2148
mul v2295 v2290
add v2294 v2296
xor v2273 v2172
mul v2298 v2292
add v2297 v2299
sub v2293 v2300
sub v2301 v2300
sub v2300 v2301
add v2302 v2303
div v2304 v1933
shl v2305 1
sub 1 v2303
sub 1 v2307
add v2306 v2308
sub 1 v2170
add v2304 0
add v2283 v2311
add v2260 v2312
add v2237 v2313
add v2214 v2314
add v2191 v2315
add v2305 0
add v2284 v2317
add v2261 v2318
add v2238 v2319
add v2215 v2320
add v2192 v2321
mul v1933 v2322
sub v2316 v2323
add v2310 v2324
shr v2196 1
sub 1 v2326
add v2325 v2327
add v2143 v2328
mul v2326 v2326
mul v2326 v2140
xor v2196 v1985
land v2332 1
xor v2333 1
mul v2326 v2150
shr v2219 1
mul v2140 v2336
add v2335 v2337
xor v2196 v2008
land v2339 1
mul v2340 v2335
xor v1985 v2219
land v2342 1
xor v2343 1
mul v2344 v2337
add v2341 v2345
sub v2338 v2346
sub v2347 v2346
sub v2346 v2347
add v2348 v2349
div v2350 1
shl v2351 1
sub 1 v2349
sub 1 v2353
add v2352 v2354
shr v2355 1
land v2355 1
xor v2357 1
mul v2330 v2174
shr v2242 1
mul v2331 v2360
add v2359 v2361
mul v2356 v2336
add v2362 v2363
mul v2180 v2359
land v2242 1
xor v2366 v2334
mul v2367 v2361
add v2365 v2368
land v2219 1
xor v2370 v2358
mul v2371 v2363
add v2369 v2372
sub v2364 v2373
sub v2374 v2373
sub v2373 v2374
add v2375 v2376
div v2377 v2144
shl v2378 1
sub 1 v2376
sub 1 v2380
add v2379 v2381
mul v2330 v2198
shr v2265 1
mul v2331 v2384
add v2383 v2385
mul v2356 v2360
add v2386 v2387
mul v2204 v2383
land v2265 1
xor v2390 v2334
mul v2391 v2385
add v2389 v2392
xor v2366 v2358
mul v2394 v2387
add v2393 v2395
sub v2388 v2396
sub v2397 v2396
sub v2396 v2397
add v2398 v2399
div v2400 v2144
shl v2401 1
sub 1 v2399
sub 1 v2403
add v2402 v2404
mul v2330 v2221
shr v2288 1
mul v2331 v2407
add v2406 v2408
mul v2356 v2384
add v2409 v2410
mul v2227 v2406
land v2288 1
xor v2413 v2334
mul v2414 v2408
add v2412 v2415
xor v2390 v2358
mul v2417 v2410
add v2416 v2418
sub v2411 v2419
sub v2420 v2419
sub v2419 v2420
add v2421 v2422
div v2423 v2144
shl v2424 1
sub 1 v2422
sub 1 v2426
add v2425 v2427
mul v2330 v2244
shr v2309 1
mul v2331 v2430
add v2429 v2431
mul v2356 v2407
add v2432 v2433
mul v2250 v2429
land v2309 1
xor v2436 v2334
mul v2437 v2431
add v2435 v2438
xor v2413 v2358
mul v2440 v2433
add v2439 v2441
sub v2434 v2442
sub v2443 v2442
sub v2442 v2443
add v2444 v2445
div v2446 v2144
shl v2447 1
sub 1 v2445
sub 1 v2449
add v2448 v2450
mul v2330 v2267
mul v2331 v1648
add v2452 v2453
mul v2356 v2430
add v2454 v2455
mul v2273 v2452
xor v1655 v2334
mul v2458 v2453
add v2457 v2459
xor v2436 v2358
mul v2461 v2455
add v2460 v2462
sub v2456 v2463
sub v2464 v2463
sub v2463 v2464
add v2465 v2466
div v2467 v2144
shl v2468 1
sub 1 v2466
sub 1 v2470
add v2469 v2471
sub 1 v2356
add v2467 0
add v2446 v2474
add v2423 v2475
add v2400 v2476
add v2377 v2477
add v2468 0
add v2447 v2479
add v2424 v2480
add v2401 v2481
add v2378 v2482
mul v2144 v2483
sub v2478 v2484
add v2473 v2485
shr v2382 1
sub 1 v2487
add v2486 v2488
add v2329 v2489
mul v2487 v2487
mul v2487 v2326
xor v2382 v2196
land v2493 1
xor v2494 1
mul v2487 v2336
shr v2405 1
mul v2326 v2497
add v2496 v2498
xor v2382 v2219
land v2500 1
mul v2501 v2496
xor v2196 v2405
land v2503 1
xor v2504 1
mul v2505 v2498
add v2502 v2506
sub v2499 v2507
sub v2508 v2507
sub v2507 v2508
add v2509 v2510
div v2511 1
shl v2512 1
sub 1 v2510
sub 1 v2514
add v2513 v2515
shr v2516 1
land v2516 1
xor v2518 1
mul v2491 v2360
shr v2428 1
mul v2492 v2521
add v2520 v2522
mul v2517 v2497
add v2523 v2524
mul v2366 v2520
land v2428 1
xor v2527 v2495
mul v2528 v2522
add v2526 v2529
land v2405 1
xor v2531 v2519
mul v2532 v2524
add v2530 v2533
sub v2525 v2534
sub v2535 v2534
sub v2534 v2535
add v2536 v2537
div v2538 v2330
shl v2539 1
sub 1 v2537
sub 1 v2541
add v2540 v2542
mul v2491 v2384
shr v2451 1
mul v2492 v2545
add v2544 v2546
mul v2517 v2521
add v2547 v2548
mul v2390 v2544
land v2451 1
xor v2551 v2495
mul v2552 v2546
add v2550 v2553
xor v2527 v2519
mul v2555 v2548
add v2554 v2556
sub v2549 v2557
sub v2558 v2557
sub v2557 v2558
add v2559 v2560
div v2561 v2330
shl v2562 1
sub 1 v2560
sub 1 v2564
add v2563 v2565
mul v2491 v2407
shr v2472 1
mul v2492 v2568
add v2567 v2569
mul v2517 v2545
add v2570 v2571
mul v2413 v2567
land v2472 1
xor v2574 v2495
mul v2575 v2569
add v2573 v2576
xor v2551 v2519
mul v2578 v2571
add v2577 v2579
sub v2572 v2580
sub v2581 v2580
sub v2580 v2581
add v2582 v2583
div v2584 v2330
shl v2585 1
sub 1 v2583
sub 1 v2587
add v2586 v2588
mul v2491 v2430
mul v2492 v1648
add v2590 v2591
mul v2517 v2568
add v2592 v2593
mul v2436 v2590
xor v1655 v2495
mul v2596 v2591
add v2595 v2597
xor v2574 v2519
mul v2599 v2593
add v2598 v2600
sub v2594 v2601
sub v2602 v2601
sub v2601 v2602
add v2603 v2604
div v2605 v2330
shl v2606 1
sub 1 v2604
sub 1 v2608
add v2607 v2609
sub 1 v2517
add v2605 0
add v2584 v2612
add v2561 v2613
add v2538 v2614
add v2606 0
add v2585 v2616
add v2562 v2617
add v2539 v2618
mul v2330 v2619
sub v2615 v2620
add v2611 v2621
shr v2543 1
sub 1 v2623
add v2622 v2624
add v2490 v2625
mul v2623 v2623
mul v2623 v2487
xor v2543 v2382
land v2629 1
xor v2630 1
mul v2623 v2497
shr v2566 1
mul v2487 v2633
add v2632 v2634
xor v2543 v2405
land v2636 1
mul v2637 v2632
xor v2382 v2566
land v2639 1
xor v2640 1
mul v2641 v2634
add v2638 v2642
sub v2635 v2643
sub v2644 v2643
sub v2643 v2644
add v2645 v2646
div v2647 1
shl v2648 1
sub 1 v2646
sub 1 v2650
add v2649 v2651
shr v2652 1
land v2652 1
xor v2654 1
mul v2627 v2521
shr v2589 1
mul v2628 v2657
add v2656 v2658
mul v2653 v2633
add v2659 v2660
mul v2527 v2656
land v2589 1
xor v2663 v2631
mul v2664 v2658
add v2662 v2665
land v2566 1
xor v2667 v2655
mul v2668 v2660
add v2666 v2669
sub v2661 v2670
sub v2671 v2670
sub v2670 v2671
add v2672 v2673
div v2674 v2491
shl v2675 1
sub 1 v2673
sub 1 v2677
add v2676 v2678
mul v2627 v2545
shr v2610 1
mul v2628 v2681
add v2680 v2682
mul v2653 v2657
add v2683 v2684
mul v2551 v2680
land v2610 1
xor v2687 v2631
mul v2688 v2682
add v2686 v2689
xor v2663 v2655
mul v2691 v2684
add v2690 v2692
sub v2685 v2693
sub v2694 v2693
sub v2693 v2694
add v2695 v2696
div v2697 v2491
shl v2698 1
sub 1 v2696
sub 1 v2700
add v2699 v2701
mul v2627 v2568
mul v2628 v1648
add v2703 v2704
mul v2653 v2681
add v2705 v2706
mul v2574 v2703
xor v1655 v2631
mul v2709 v2704
add v2708 v2710
xor v2687 v2655
mul v2712 v2706
add v2711 v2713
sub v2707 v2714
sub v2715 v2714
sub v2714 v2715
add v2716 v2717
div v2718 v2491
shl v2719 1
sub 1 v2717
sub 1 v2721
add v2720 v2722
sub 1 v2653
add v2718 0
add v2697 v2725
add v2674 v2726
add v2719 0
add v2698 v2728
add v2675 v2729
mul v2491 v2730
sub v2727 v2731
add v2724 v2732
shr v2679 1
sub 1 v2734
add v2733 v2735
add v2626 v2736
mul v2734 v2734
mul v2734 v2623
xor v2679 v2543
land v2740 1
xor v2741 1
mul v2734 v2633
shr v2702 1
mul v2623 v2744
add v2743 v2745
xor v2679 v2566
land v2747 1
mul v2748 v2743
xor v2543 v2702
land v2750 1
xor v2751 1
mul v2752 v2745
add v2749 v2753
sub v2746 v2754
sub v2755 v2754
sub v2754 v2755
add v2756 v2757
div v2758 1
shl v2759 1
sub 1 v2757
sub 1 v2761
add v2760 v2762
shr v2763 1
land v2763 1
xor v2765 1
mul v2738 v2657
shr v2723 1
mul v2739 v2768
add v2767 v2769
mul v2764 v2744
add v2770 v2771
mul v2663 v2767
land v2723 1
xor v2774 v2742
mul v2775 v2769
add v2773 v2776
land v2702 1
xor v2778 v2766
mul v2779 v2771
add v2777 v2780
sub v2772 v2781
sub v2782 v2781
sub v2781 v2782
add v2783 v2784
div v2785 v2627
shl v2786 1
sub 1 v2784
sub 1 v2788
add v2787 v2789
mul v2738 v2681
mul v2739 v1648
add v2791 v2792
mul v2764 v2768
add v2793 v2794
mul v2687 v2791
xor v1655 v2742
mul v2797 v2792
add v2796 v2798
xor v2774 v2766
mul v2800 v2794
add v2799 v2801
sub v2795 v2802
sub v2803 v2802
sub v2802 v2803
add v2804 v2805
div v2806 v2627
shl v2807 1
sub 1 v2805
sub 1 v2809
add v2808 v2810
sub 1 v2764
add v2806 0
add v2785 v2813
add v2807 0
add v2786 v2815
mul v2627 v2816
sub v2814 v2817
add v2812 v2818
shr v2790 1
sub 1 v2820
add v2819 v2821
add v2737 v2822
mul v2820 v2820
mul v2820 v2734
xor v2790 v2679
land v2826 1
xor v2827 1
mul v2820 v2744
shr v2811 1
mul v2734 v2830
add v2829 v2831
xor v2790 v2702
land v2833 1
mul v2834 v2829
xor v2679 v2811
land v2836 1
xor v2837 1
mul v2838 v2831
add v2835 v2839
sub v2832 v2840
sub v2841 v2840
sub v2840 v2841
add v2842 v2843
div v2844 1
shl v2845 1
sub 1 v2843
sub 1 v2847
add v2846 v2848
shr v2849 1
land v2849 1
xor v2851 1
mul v2824 v2768
mul v2825 v1648
add v2853 v2854
mul v2850 v2830
add v2855 v2856
mul v2774 v2853
xor v1655 v2828
mul v2859 v2854
add v2858 v2860
land v2811 1
xor v2862 v2852
mul v2863 v2856
add v2861 v2864
sub v2857 v2865
sub v2866 v2865
sub v2865 v2866
add v2867 v2868
div v2869 v2738
shl v2870 1
sub 1 v2868
sub 1 v2872
add v2871 v2873
sub 1 v2850
add v2869 0
add v2870 0
mul v2738 v2877
sub v2876 v2878
add v2875 v2879
shr v2874 1
sub 1 v2881
add v2880 v2882
add v2823 v2883
app x25 v2874 v2884" [f0, f1, f2, f3, f4, f5, f6, f7, f8, f9, f10, f11, f12, f13, f14, f15, f16, f17, f18, f19, f20, f21, f22, f23, f24, (@Prod.mk Nat Nat), c0, c1, c2, c3, c4, c5, c6, c7, c8, c9, c10, c11, c12, c13, c14, c15, c16, c17, c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c30, c31, c32, c33, c34, c35, c36, c37, c38, c39, c40, c41, c42, c43, c44, c45, c46, c47, c48, c49, c50, c51, c52, c53, c54, c55, c56, c57, c58, c59, c60, c61, c62, c63, c64, c65, c66, c67, c68, c69, c70, c71, c72, c73, c74, c75, c76, c77, c78, c79, c80, c81, c82, c83, c84, c85, c86, c87, c88, c89, c90, c91, c92, c93, c94, c95, c96, c97, c98, c99]

set_option linter.unusedVariables false in
/-- The structured run over the same variables. -/
def pkRhs205 (f0 f1 f2 f3 f4 f5 f6 f7 f8 f9 f10 f11 f12 f13 f14 f15 f16 f17 f18 f19 f20 f21 f22 f23 f24 c0 c1 c2 c3 c4 c5 c6 c7 c8 c9 c10 c11 c12 c13 c14 c15 c16 c17 c18 c19 c20 c21 c22 c23 c24 c25 c26 c27 c28 c29 c30 c31 c32 c33 c34 c35 c36 c37 c38 c39 c40 c41 c42 c43 c44 c45 c46 c47 c48 c49 c50 c51 c52 c53 c54 c55 c56 c57 c58 c59 c60 c61 c62 c63 c64 c65 c66 c67 c68 c69 c70 c71 c72 c73 c74 c75 c76 c77 c78 c79 c80 c81 c82 c83 c84 c85 c86 c87 c88 c89 c90 c91 c92 c93 c94 c95 c96 c97 c98 c99 : Nat) : Nat × Nat :=
  let s := prun [.step 2115 704 22 c2 c3 (Nat.shiftRight c0 c39) (Nat.shiftRight c1 c39) c4 c63 c40 c18 c19 c20 true true,
    .step 2115 704 21 c2 c3 (Nat.shiftRight c0 c38) (Nat.shiftRight c1 c38) c4 c63 c40 c19 c20 c21 false true,
    .step 2115 704 20 c2 c3 (Nat.shiftRight c0 c37) (Nat.shiftRight c1 c37) c4 c63 c40 c20 c21 c22 false true,
    .step 2115 704 19 c2 c3 (Nat.shiftRight c0 c36) (Nat.shiftRight c1 c36) c4 c63 c40 c21 c22 c23 false true,
    .step 2115 704 18 c2 c3 (Nat.shiftRight c0 c35) (Nat.shiftRight c1 c35) c4 c63 c40 c22 c23 c24 false true,
    .step 2115 704 17 c2 c3 (Nat.shiftRight c0 c34) (Nat.shiftRight c1 c34) c4 c63 c40 c23 c24 c25 false true,
    .step 2115 704 16 c2 c3 (Nat.shiftRight c0 c33) (Nat.shiftRight c1 c33) c4 c63 c40 c24 c25 c26 false true,
    .repack 2115 704 4107 1368 17 c3 (Nat.shiftRight c0 c34) (Nat.shiftRight c0 c33) [c24, c25, c26, c27, c28, c29, c30, c31, c32, c33, c34, c35, c36, c37, c38, c39, c40, 0] [c25, c26, c27, c28, c29, c30, c31, c32, c33, c34, c35, c36, c37, c38, c39, c40, 0] [c65, c66, c67, c68, c69, c70, c71, c72, c73, c74, c75, c76, c77, c78, c79, c80, c81] [c66, c67, c68, c69, c70, c71, c72, c73, c74, c75, c76, c77, c78, c79, c80, c81] (Nat.shiftRight c5 c75) (Nat.shiftRight c5 c74) c64,
    .step 4107 1368 15 c7 c8 (Nat.shiftRight c5 c73) (Nat.shiftRight c6 c73) c9 c82 c81 c66 c67 c68 false true,
    .step 4107 1368 14 c7 c8 (Nat.shiftRight c5 c72) (Nat.shiftRight c6 c72) c9 c82 c81 c67 c68 c69 false true,
    .step 4107 1368 13 c7 c8 (Nat.shiftRight c5 c71) (Nat.shiftRight c6 c71) c9 c82 c81 c68 c69 c70 false true,
    .step 4107 1368 12 c7 c8 (Nat.shiftRight c5 c70) (Nat.shiftRight c6 c70) c9 c82 c81 c69 c70 c71 false true,
    .repack 4107 1368 6159 2052 13 c8 (Nat.shiftRight c5 c71) (Nat.shiftRight c5 c70) [c69, c70, c71, c72, c73, c74, c75, c76, c77, c78, c79, c80, c81, 0] [c70, c71, c72, c73, c74, c75, c76, c77, c78, c79, c80, c81, 0] [c84, c85, c86, c87, c88, c89, c90, c91, c92, c93, c94, c95, c96] [c85, c86, c87, c88, c89, c90, c91, c92, c93, c94, c95, c96] (Nat.shiftRight c10 c86) (Nat.shiftRight c10 c85) c83,
    .step 6159 2052 11 c12 c13 (Nat.shiftRight c10 c84) (Nat.shiftRight c11 c84) c14 c97 c96 c85 c86 c87 false true,
    .step 6159 2052 10 c12 c13 (Nat.shiftRight c10 c98) (Nat.shiftRight c11 c98) c14 c97 c96 c86 c87 c88 false true,
    .step 6159 2052 9 c12 c13 (Nat.shiftRight c10 c99) (Nat.shiftRight c11 c99) c14 c97 c96 c87 c88 c89 false true]
    (pinit c2 c15 c16 [c17, c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c30, c31, c32, c33, c34, c35, c36, c37, c38, c39, c40] [c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c30, c31, c32, c33, c34, c35, c36, c37, c38, c39, c40] [23, 22, 21, 20, 19, 18, 17, 16, 15, 14, 13, 12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2] [c41, c42, c43, c44, c45, c46, c47, c48, c49, c50, c51, c52, c53, c54, c55, c56, c57, c58, c59, c60, c61, c62] (Nat.shiftRight c0 0) (Nat.shiftRight c0 c40) [f1, f2, f3, f4, f5, f6, f7, f8, f9, f10, f11, f12, f13, f14, f15, f16, f17, f18, f19, f20, f21, f22, f23, f24])
  run 9 (unpackT c12 c13 (Nat.shiftRight c10 c98) [c87, c88, c89, c90, c91, c92, c93, c94, c95, c96, 0] s.fv s.fs)
    (unpackT c12 c13 (Nat.shiftRight c10 c99) [c88, c89, c90, c91, c92, c93, c94, c95, c96, 0] s.gv s.gs) s.bad

/-- Statement of `pkDagC205_eq`. -/
def PkDagC205Eq : Prop := ∀ f0 f1 f2 f3 f4 f5 f6 f7 f8 f9 f10 f11 f12 f13 f14 f15 f16 f17 f18 f19 f20 f21 f22 f23 f24 c0 c1 c2 c3 c4 c5 c6 c7 c8 c9 c10 c11 c12 c13 c14 c15 c16 c17 c18 c19 c20 c21 c22 c23 c24 c25 c26 c27 c28 c29 c30 c31 c32 c33 c34 c35 c36 c37 c38 c39 c40 c41 c42 c43 c44 c45 c46 c47 c48 c49 c50 c51 c52 c53 c54 c55 c56 c57 c58 c59 c60 c61 c62 c63 c64 c65 c66 c67 c68 c69 c70 c71 c72 c73 c74 c75 c76 c77 c78 c79 c80 c81 c82 c83 c84 c85 c86 c87 c88 c89 c90 c91 c92 c93 c94 c95 c96 c97 c98 c99 : Nat, pkDagC205 f0 f1 f2 f3 f4 f5 f6 f7 f8 f9 f10 f11 f12 f13 f14 f15 f16 f17 f18 f19 f20 f21 f22 f23 f24 c0 c1 c2 c3 c4 c5 c6 c7 c8 c9 c10 c11 c12 c13 c14 c15 c16 c17 c18 c19 c20 c21 c22 c23 c24 c25 c26 c27 c28 c29 c30 c31 c32 c33 c34 c35 c36 c37 c38 c39 c40 c41 c42 c43 c44 c45 c46 c47 c48 c49 c50 c51 c52 c53 c54 c55 c56 c57 c58 c59 c60 c61 c62 c63 c64 c65 c66 c67 c68 c69 c70 c71 c72 c73 c74 c75 c76 c77 c78 c79 c80 c81 c82 c83 c84 c85 c86 c87 c88 c89 c90 c91 c92 c93 c94 c95 c96 c97 c98 c99 = pkRhs205 f0 f1 f2 f3 f4 f5 f6 f7 f8 f9 f10 f11 f12 f13 f14 f15 f16 f17 f18 f19 f20 f21 f22 f23 f24 c0 c1 c2 c3 c4 c5 c6 c7 c8 c9 c10 c11 c12 c13 c14 c15 c16 c17 c18 c19 c20 c21 c22 c23 c24 c25 c26 c27 c28 c29 c30 c31 c32 c33 c34 c35 c36 c37 c38 c39 c40 c41 c42 c43 c44 c45 c46 c47 c48 c49 c50 c51 c52 c53 c54 c55 c56 c57 c58 c59 c60 c61 c62 c63 c64 c65 c66 c67 c68 c69 c70 c71 c72 c73 c74 c75 c76 c77 c78 c79 c80 c81 c82 c83 c84 c85 c86 c87 c88 c89 c90 c91 c92 c93 c94 c95 c96 c97 c98 c99

open Lean Elab Term Command Meta in
/- `pkDagC205_eq : PkDagC205Eq` by `rfl`, checked by the kernel on open terms. -/
run_cmd liftTermElabM do
  let ty ← instantiateMVars (← elabTerm (← `(PkDagC205Eq)) none)
  let pf ← instantiateMVars (← elabTerm (← `(fun (f0 f1 f2 f3 f4 f5 f6 f7 f8 f9 f10 f11 f12 f13 f14 f15 f16 f17 f18 f19 f20 f21 f22 f23 f24 c0 c1 c2 c3 c4 c5 c6 c7 c8 c9 c10 c11 c12 c13 c14 c15 c16 c17 c18 c19 c20 c21 c22 c23 c24 c25 c26 c27 c28 c29 c30 c31 c32 c33 c34 c35 c36 c37 c38 c39 c40 c41 c42 c43 c44 c45 c46 c47 c48 c49 c50 c51 c52 c53 c54 c55 c56 c57 c58 c59 c60 c61 c62 c63 c64 c65 c66 c67 c68 c69 c70 c71 c72 c73 c74 c75 c76 c77 c78 c79 c80 c81 c82 c83 c84 c85 c86 c87 c88 c89 c90 c91 c92 c93 c94 c95 c96 c97 c98 c99 : Nat) =>
    @rfl (Nat × Nat) (pkDagC205 f0 f1 f2 f3 f4 f5 f6 f7 f8 f9 f10 f11 f12 f13 f14 f15 f16 f17 f18 f19 f20 f21 f22 f23 f24 c0 c1 c2 c3 c4 c5 c6 c7 c8 c9 c10 c11 c12 c13 c14 c15 c16 c17 c18 c19 c20 c21 c22 c23 c24 c25 c26 c27 c28 c29 c30 c31 c32 c33 c34 c35 c36 c37 c38 c39 c40 c41 c42 c43 c44 c45 c46 c47 c48 c49 c50 c51 c52 c53 c54 c55 c56 c57 c58 c59 c60 c61 c62 c63 c64 c65 c66 c67 c68 c69 c70 c71 c72 c73 c74 c75 c76 c77 c78 c79 c80 c81 c82 c83 c84 c85 c86 c87 c88 c89 c90 c91 c92 c93 c94 c95 c96 c97 c98 c99))) none)
  addDecl (.thmDecl { name := `Submission.pkDagC205_eq, levelParams := [], type := ty, value := pf })

/-- The packed run of band `205`, lane constants computed inside the graph. -/
def pkDag205 (f0 f1 f2 f3 f4 f5 f6 f7 f8 f9 f10 f11 f12 f13 f14 f15 f16 f17 f18 f19 f20 f21 f22 f23 f24 : Nat) : Nat × Nat :=
  natdag% "shl 1 2115
add 1 v0
shl v1 4230
add v1 v2
shl v3 8460
add v3 v4
shl v5 16920
add v5 v6
shl v5 33840
add v7 v8
shl 1 50760
add v9 v10
shl v11 704
shl v11 2115
shl v11 705
sub v13 v14
shl 1 704
sub v0 1
shl 1 1408
sub v18 1
shl 1 4107
add 1 v20
shl v21 8214
add v21 v22
shl v23 16428
add v23 v24
shl v25 32856
add v25 v26
shl v25 65712
add v27 v28
shl 1 98568
add v29 v30
shl v31 1368
shl v31 4107
shl v31 1369
sub v33 v34
shl 1 1368
sub v20 1
shl 1 2736
sub v38 1
shl 1 6159
add 1 v40
shl v41 12318
add v41 v42
shl v43 24636
add v43 v44
shl v45 49272
add v45 v46
shl v45 98544
add v47 v48
shl 1 147816
add v49 v50
shl v51 2052
shl v51 6159
shl v51 2053
sub v53 v54
shl 1 2052
sub v40 1
shl 1 4104
sub v58 1
shl 11 705
shl 21 704
shl 5 706
shl 19 704
shl 9 705
shl 17 704
shl 1 708
shl 15 704
shl 7 705
shl 13 704
shl 3 706
shl 11 704
shl 5 705
shl 9 704
shl 1 707
shl 7 704
shl 3 705
shl 5 704
shl 1 706
shl 3 704
shl 1 705
shr v12 0
shr v12 2115
shr x1 1
add v83 v16
shl v83 1
land x1 1
mul v85 v86
sub v84 v87
shr x2 1
add v89 v16
shl v89 1
land x2 1
mul v91 v92
sub v90 v93
shr x3 1
add v95 v16
shl v95 1
land x3 1
mul v97 v98
sub v96 v99
shr x4 1
add v101 v16
shl v101 1
land x4 1
mul v103 v104
sub v102 v105
shr x5 1
add v107 v16
shl v107 1
land x5 1
mul v109 v110
sub v108 v111
shr x6 1
add v113 v16
shl v113 1
land x6 1
mul v115 v116
sub v114 v117
shr x7 1
add v119 v16
shl v119 1
land x7 1
mul v121 v122
sub v120 v123
shr x8 1
add v125 v16
shl v125 1
land x8 1
mul v127 v128
sub v126 v129
shr x9 1
add v131 v16
shl v131 1
land x9 1
mul v133 v134
sub v132 v135
shr x10 1
add v137 v16
shl v137 1
land x10 1
mul v139 v140
sub v138 v141
shr x11 1
add v143 v16
shl v143 1
land x11 1
mul v145 v146
sub v144 v147
shr x12 1
add v149 v16
shl v149 1
land x12 1
mul v151 v152
sub v150 v153
shr x13 1
add v155 v16
shl v155 1
land x13 1
mul v157 v158
sub v156 v159
shr x14 1
add v161 v16
shl v161 1
land x14 1
mul v163 v164
sub v162 v165
shr x15 1
add v167 v16
shl v167 1
land x15 1
mul v169 v170
sub v168 v171
shr x16 1
add v173 v16
shl v173 1
land x16 1
mul v175 v176
sub v174 v177
shr x17 1
add v179 v16
shl v179 1
land x17 1
mul v181 v182
sub v180 v183
shr x18 1
add v185 v16
shl v185 1
land x18 1
mul v187 v188
sub v186 v189
shr x19 1
add v191 v16
shl v191 1
land x19 1
mul v193 v194
sub v192 v195
shr x20 1
add v197 v16
shl v197 1
land x20 1
mul v199 v200
sub v198 v201
shr x21 1
add v203 v16
shl v203 1
land x21 1
mul v205 v206
sub v204 v207
shr x22 1
add v209 v16
shl v209 1
land x22 1
mul v211 v212
sub v210 v213
shr x23 1
add v215 v16
shl v215 1
land x23 1
mul v217 v218
sub v216 v219
shr x24 1
add v221 v16
shl v221 1
land x24 1
mul v223 v224
sub v222 v225
mul v88 23
sub v227 v60
mul v94 22
sub v229 v61
mul v100 21
sub v231 v62
mul v106 20
sub v233 v63
mul v112 19
sub v235 v64
mul v118 18
sub v237 v65
mul v124 17
sub v239 v66
mul v130 16
sub v241 v67
mul v136 15
sub v243 v68
mul v142 14
sub v245 v69
mul v148 13
sub v247 v70
mul v154 12
sub v249 v71
mul v160 11
sub v251 v72
mul v166 10
sub v253 v73
mul v172 9
sub v255 v74
mul v178 8
sub v257 v75
mul v184 7
sub v259 v76
mul v190 6
sub v261 v77
mul v196 5
sub v263 v78
mul v202 4
sub v265 v79
mul v208 3
sub v267 v80
mul v214 2
sub v269 v16
shl v220 2115
add v226 v271
shl v214 4230
add v272 v273
shl v208 6345
add v274 v275
shl v202 8460
add v276 v277
shl v196 10575
add v278 v279
shl v190 12690
add v280 v281
shl v184 14805
add v282 v283
shl v178 16920
add v284 v285
shl v172 19035
add v286 v287
shl v166 21150
add v288 v289
shl v160 23265
add v290 v291
shl v154 25380
add v292 v293
shl v148 27495
add v294 v295
shl v142 29610
add v296 v297
shl v136 31725
add v298 v299
shl v130 33840
add v300 v301
shl v124 35955
add v302 v303
shl v118 38070
add v304 v305
shl v112 40185
add v306 v307
shl v106 42300
add v308 v309
shl v100 44415
add v310 v311
shl v94 46530
add v312 v313
shl v88 48645
add v314 v315
shl 84162174424773976115855838126082058648805436845170781751972494449099714468753293153818664580441415219631727501698851483408310916002940861810045036330430093599283578738055113571066620126149163476340692027772502017 50760
add v316 v317
sub v318 v81
shl v270 2115
add v220 v320
shl v268 4230
add v321 v322
shl v266 6345
add v323 v324
shl v264 8460
add v325 v326
shl v262 10575
add v327 v328
shl v260 12690
add v329 v330
shl v258 14805
add v331 v332
shl v256 16920
add v333 v334
shl v254 19035
add v335 v336
shl v252 21150
add v337 v338
shl v250 23265
add v339 v340
shl v248 25380
add v341 v342
shl v246 27495
add v343 v344
shl v244 29610
add v345 v346
shl v242 31725
add v347 v348
shl v240 33840
add v349 v350
shl v238 35955
add v351 v352
shl v236 38070
add v353 v354
shl v234 40185
add v355 v356
shl v232 42300
add v357 v358
shl v230 44415
add v359 v360
shl v228 46530
add v361 v362
shl 84162174424773976115855838126082058648805436845170781751972494449099714468753293153818664580441415219631727501698851483408310916002940861810045036330430093599283578738055113571066620126149163476340692027772502040 48645
add v363 v364
sub v365 v82
shr v12 4230
shr v15 4230
mul 24 v88
add v369 v16
mul 1 v228
shl 24 704
add v371 v372
sub v370 v373
sub v373 v370
add v374 v375
sub 1 v376
add 0 v377
mul 24 24
mul v379 v319
mul 1 24
shl v381 2115
add v382 v370
sub v383 v373
mul v384 v366
sub v385 v380
sub v380 v385
add v387 v386
add v388 v367
land v389 v368
shr v389 48645
add v390 v391
add v378 v392
shr v389 46530
sub v394 v16
shr v389 44415
land v396 v17
sub 1 v386
sub 1 v398
xor 0 v399
sub 1 v395
add v393 v401
shr v12 6345
shr v15 6345
mul v395 v228
add v405 v372
mul 24 v397
shl v395 704
add v407 v408
sub v406 v409
sub v409 v406
add v410 v411
sub 1 v412
add v402 v413
mul v395 v395
mul v415 v366
mul 24 v395
shl v417 2115
add v418 v406
sub v419 v409
mul v420 v388
sub v421 v416
sub v416 v421
add v423 v422
div v424 v379
land v425 v19
mul v379 v426
land v427 v19
land v424 v19
sub v429 v428
sub v428 v429
add v430 v431
add v414 v432
add v425 v403
land v434 v404
shr v434 46530
add v435 v436
add v433 v437
shr v434 44415
sub v439 v16
shr v434 42300
land v441 v17
sub 1 v422
sub 1 v443
xor 0 v444
sub 1 v440
add v438 v446
shr v12 8460
shr v15 8460
mul v440 v397
add v450 v408
mul v395 v442
shl v440 704
add v452 v453
sub v451 v454
sub v454 v451
add v455 v456
sub 1 v457
add v447 v458
mul v440 v440
mul v460 v388
mul v395 v440
shl v462 2115
add v463 v451
sub v464 v454
mul v465 v425
sub v466 v461
sub v461 v466
add v468 v467
div v469 v415
land v470 v19
mul v415 v471
land v472 v19
land v469 v19
sub v474 v473
sub v473 v474
add v475 v476
add v459 v477
add v470 v448
land v479 v449
shr v479 44415
add v480 v481
add v478 v482
shr v479 42300
sub v484 v16
shr v479 40185
land v486 v17
sub 1 v467
sub 1 v488
xor v400 v489
sub 1 v485
add v483 v491
shr v12 10575
shr v15 10575
mul v485 v442
add v495 v453
mul v440 v487
shl v485 704
add v497 v498
sub v496 v499
sub v499 v496
add v500 v501
sub 1 v502
add v492 v503
mul v485 v485
mul v505 v425
mul v440 v485
shl v507 2115
add v508 v496
sub v509 v499
mul v510 v470
sub v511 v506
sub v506 v511
add v513 v512
div v514 v460
land v515 v19
mul v460 v516
land v517 v19
land v514 v19
sub v519 v518
sub v518 v519
add v520 v521
add v504 v522
add v515 v493
land v524 v494
shr v524 42300
add v525 v526
add v523 v527
shr v524 40185
sub v529 v16
shr v524 38070
land v531 v17
sub 1 v512
sub 1 v533
xor v445 v534
sub 1 v530
add v528 v536
shr v12 12690
shr v15 12690
mul v530 v487
add v540 v498
mul v485 v532
shl v530 704
add v542 v543
sub v541 v544
sub v544 v541
add v545 v546
sub 1 v547
add v537 v548
mul v530 v530
mul v550 v470
mul v485 v530
shl v552 2115
add v553 v541
sub v554 v544
mul v555 v515
sub v556 v551
sub v551 v556
add v558 v557
div v559 v505
land v560 v19
mul v505 v561
land v562 v19
land v559 v19
sub v564 v563
sub v563 v564
add v565 v566
add v549 v567
add v560 v538
land v569 v539
shr v569 40185
add v570 v571
add v568 v572
shr v569 38070
sub v574 v16
shr v569 35955
land v576 v17
sub 1 v557
sub 1 v578
xor v490 v579
sub 1 v575
add v573 v581
shr v12 14805
shr v15 14805
mul v575 v532
add v585 v543
mul v530 v577
shl v575 704
add v587 v588
sub v586 v589
sub v589 v586
add v590 v591
sub 1 v592
add v582 v593
mul v575 v575
mul v595 v515
mul v530 v575
shl v597 2115
add v598 v586
sub v599 v589
mul v600 v560
sub v601 v596
sub v596 v601
add v603 v602
div v604 v550
land v605 v19
mul v550 v606
land v607 v19
land v604 v19
sub v609 v608
sub v608 v609
add v610 v611
add v594 v612
add v605 v583
land v614 v584
shr v614 38070
add v615 v616
add v613 v617
shr v614 35955
sub v619 v16
shr v614 33840
land v621 v17
sub 1 v602
sub 1 v623
xor v535 v624
sub 1 v620
add v618 v626
shr v12 16920
shr v15 16920
mul v620 v577
add v630 v588
mul v575 v622
shl v620 704
add v632 v633
sub v631 v634
sub v634 v631
add v635 v636
sub 1 v637
add v627 v638
mul v620 v620
mul v640 v560
mul v575 v620
shl v642 2115
add v643 v631
sub v644 v634
mul v645 v605
sub v646 v641
sub v641 v646
add v648 v647
div v649 v595
land v650 v19
mul v595 v651
land v652 v19
land v649 v19
sub v654 v653
sub v653 v654
add v655 v656
add v639 v657
add v650 v628
land v659 v629
shr v659 35955
add v660 v661
add v658 v662
shr v659 33840
sub v664 v16
shr v659 31725
land v666 v17
sub 1 v647
sub 1 v668
xor v580 v669
sub 1 v665
add v663 v671
shr v32 28749
shr v32 32856
land v619 v17
shr v614 31725
land v676 v17
shr v614 29610
land v678 v17
shr v614 27495
land v680 v17
shr v614 25380
land v682 v17
shr v614 23265
land v684 v17
shr v614 21150
land v686 v17
shr v614 19035
land v688 v17
shr v614 16920
land v690 v17
shr v614 14805
land v692 v17
shr v614 12690
land v694 v17
shr v614 10575
land v696 v17
shr v614 8460
land v698 v17
shr v614 6345
land v700 v17
shr v614 4230
land v702 v17
shr v614 2115
land v704 v17
shr v614 0
land v706 v17
add v675 6442197994971210171117433855979443557987035158250386343091063510776640623123668808832987706388430973801155931354965850214447254634690146708203626373189659075327467602032807223495137635981210320405619682687966819080149948303222995302848218841424195676765109882087340442027368846695420372536811407973658230769597018046585240803609741451498847099506923062835400132577696389198772341582304023818589952091969384611840
add v622 6442197994971210171117433855979443557987035158250386343091063510776640623123668808832987706388430973801155931354965850214447254634690146708203626373189659075327467602032807223495137635981210320405619682687966819080149948303222995302848218841424195676765109882087340442027368846695420372536811407973658230769597018046585240803609741451498847099506923062835400132577696389198772341582304023818589952091969384611840
add v677 6442197994971210171117433855979443557987035158250386343091063510776640623123668808832987706388430973801155931354965850214447254634690146708203626373189659075327467602032807223495137635981210320405619682687966819080149948303222995302848218841424195676765109882087340442027368846695420372536811407973658230769597018046585240803609741451498847099506923062835400132577696389198772341582304023818589952091969384611840
add v679 6442197994971210171117433855979443557987035158250386343091063510776640623123668808832987706388430973801155931354965850214447254634690146708203626373189659075327467602032807223495137635981210320405619682687966819080149948303222995302848218841424195676765109882087340442027368846695420372536811407973658230769597018046585240803609741451498847099506923062835400132577696389198772341582304023818589952091969384611840
add v681 6442197994971210171117433855979443557987035158250386343091063510776640623123668808832987706388430973801155931354965850214447254634690146708203626373189659075327467602032807223495137635981210320405619682687966819080149948303222995302848218841424195676765109882087340442027368846695420372536811407973658230769597018046585240803609741451498847099506923062835400132577696389198772341582304023818589952091969384611840
add v683 6442197994971210171117433855979443557987035158250386343091063510776640623123668808832987706388430973801155931354965850214447254634690146708203626373189659075327467602032807223495137635981210320405619682687966819080149948303222995302848218841424195676765109882087340442027368846695420372536811407973658230769597018046585240803609741451498847099506923062835400132577696389198772341582304023818589952091969384611840
add v685 6442197994971210171117433855979443557987035158250386343091063510776640623123668808832987706388430973801155931354965850214447254634690146708203626373189659075327467602032807223495137635981210320405619682687966819080149948303222995302848218841424195676765109882087340442027368846695420372536811407973658230769597018046585240803609741451498847099506923062835400132577696389198772341582304023818589952091969384611840
add v687 6442197994971210171117433855979443557987035158250386343091063510776640623123668808832987706388430973801155931354965850214447254634690146708203626373189659075327467602032807223495137635981210320405619682687966819080149948303222995302848218841424195676765109882087340442027368846695420372536811407973658230769597018046585240803609741451498847099506923062835400132577696389198772341582304023818589952091969384611840
add v689 6442197994971210171117433855979443557987035158250386343091063510776640623123668808832987706388430973801155931354965850214447254634690146708203626373189659075327467602032807223495137635981210320405619682687966819080149948303222995302848218841424195676765109882087340442027368846695420372536811407973658230769597018046585240803609741451498847099506923062835400132577696389198772341582304023818589952091969384611840
add v691 6442197994971210171117433855979443557987035158250386343091063510776640623123668808832987706388430973801155931354965850214447254634690146708203626373189659075327467602032807223495137635981210320405619682687966819080149948303222995302848218841424195676765109882087340442027368846695420372536811407973658230769597018046585240803609741451498847099506923062835400132577696389198772341582304023818589952091969384611840
add v693 6442197994971210171117433855979443557987035158250386343091063510776640623123668808832987706388430973801155931354965850214447254634690146708203626373189659075327467602032807223495137635981210320405619682687966819080149948303222995302848218841424195676765109882087340442027368846695420372536811407973658230769597018046585240803609741451498847099506923062835400132577696389198772341582304023818589952091969384611840
add v695 6442197994971210171117433855979443557987035158250386343091063510776640623123668808832987706388430973801155931354965850214447254634690146708203626373189659075327467602032807223495137635981210320405619682687966819080149948303222995302848218841424195676765109882087340442027368846695420372536811407973658230769597018046585240803609741451498847099506923062835400132577696389198772341582304023818589952091969384611840
add v697 6442197994971210171117433855979443557987035158250386343091063510776640623123668808832987706388430973801155931354965850214447254634690146708203626373189659075327467602032807223495137635981210320405619682687966819080149948303222995302848218841424195676765109882087340442027368846695420372536811407973658230769597018046585240803609741451498847099506923062835400132577696389198772341582304023818589952091969384611840
add v699 6442197994971210171117433855979443557987035158250386343091063510776640623123668808832987706388430973801155931354965850214447254634690146708203626373189659075327467602032807223495137635981210320405619682687966819080149948303222995302848218841424195676765109882087340442027368846695420372536811407973658230769597018046585240803609741451498847099506923062835400132577696389198772341582304023818589952091969384611840
add v701 6442197994971210171117433855979443557987035158250386343091063510776640623123668808832987706388430973801155931354965850214447254634690146708203626373189659075327467602032807223495137635981210320405619682687966819080149948303222995302848218841424195676765109882087340442027368846695420372536811407973658230769597018046585240803609741451498847099506923062835400132577696389198772341582304023818589952091969384611840
add v703 6442197994971210171117433855979443557987035158250386343091063510776640623123668808832987706388430973801155931354965850214447254634690146708203626373189659075327467602032807223495137635981210320405619682687966819080149948303222995302848218841424195676765109882087340442027368846695420372536811407973658230769597018046585240803609741451498847099506923062835400132577696389198772341582304023818589952091969384611840
add v705 6442197994971210171117433855979443557987035158250386343091063510776640623123668808832987706388430973801155931354965850214447254634690146708203626373189659075327467602032807223495137635981210320405619682687966819080149948303222995302848218841424195676765109882087340442027368846695420372536811407973658230769597018046585240803609741451498847099506923062835400132577696389198772341582304023818589952091969384611840
add v707 6442197994971210171117433855979443557987035158250386343091063510776640623123668808832987706388430973801155931354965850214447254634690146708203626373189659075327467602032807223495137635981210320405619682687966819080149948303222995302848218841424195676765109882087340442027368846695420372536811407973658230769597018046585240803609741451498847099506923062835400132577696389198772341582304023818589952091969384611840
land v664 v17
shr v659 29610
land v727 v17
shr v659 27495
land v729 v17
shr v659 25380
land v731 v17
shr v659 23265
land v733 v17
shr v659 21150
land v735 v17
shr v659 19035
land v737 v17
shr v659 16920
land v739 v17
shr v659 14805
land v741 v17
shr v659 12690
land v743 v17
shr v659 10575
land v745 v17
shr v659 8460
land v747 v17
shr v659 6345
land v749 v17
shr v659 4230
land v751 v17
shr v659 2115
land v753 v17
shr v659 0
land v755 v17
add v726 6442197994971210171117433855979443557987035158250386343091063510776640623123668808832987706388430973801155931354965850214447254634690146708203626373189659075327467602032807223495137635981210320405619682687966819080149948303222995302848218841424195676765109882087340442027368846695420372536811407973658230769597018046585240803609741451498847099506923062835400132577696389198772341582304023818589952091969384611840
add v667 6442197994971210171117433855979443557987035158250386343091063510776640623123668808832987706388430973801155931354965850214447254634690146708203626373189659075327467602032807223495137635981210320405619682687966819080149948303222995302848218841424195676765109882087340442027368846695420372536811407973658230769597018046585240803609741451498847099506923062835400132577696389198772341582304023818589952091969384611840
add v728 6442197994971210171117433855979443557987035158250386343091063510776640623123668808832987706388430973801155931354965850214447254634690146708203626373189659075327467602032807223495137635981210320405619682687966819080149948303222995302848218841424195676765109882087340442027368846695420372536811407973658230769597018046585240803609741451498847099506923062835400132577696389198772341582304023818589952091969384611840
add v730 6442197994971210171117433855979443557987035158250386343091063510776640623123668808832987706388430973801155931354965850214447254634690146708203626373189659075327467602032807223495137635981210320405619682687966819080149948303222995302848218841424195676765109882087340442027368846695420372536811407973658230769597018046585240803609741451498847099506923062835400132577696389198772341582304023818589952091969384611840
add v732 6442197994971210171117433855979443557987035158250386343091063510776640623123668808832987706388430973801155931354965850214447254634690146708203626373189659075327467602032807223495137635981210320405619682687966819080149948303222995302848218841424195676765109882087340442027368846695420372536811407973658230769597018046585240803609741451498847099506923062835400132577696389198772341582304023818589952091969384611840
add v734 6442197994971210171117433855979443557987035158250386343091063510776640623123668808832987706388430973801155931354965850214447254634690146708203626373189659075327467602032807223495137635981210320405619682687966819080149948303222995302848218841424195676765109882087340442027368846695420372536811407973658230769597018046585240803609741451498847099506923062835400132577696389198772341582304023818589952091969384611840
add v736 6442197994971210171117433855979443557987035158250386343091063510776640623123668808832987706388430973801155931354965850214447254634690146708203626373189659075327467602032807223495137635981210320405619682687966819080149948303222995302848218841424195676765109882087340442027368846695420372536811407973658230769597018046585240803609741451498847099506923062835400132577696389198772341582304023818589952091969384611840
add v738 6442197994971210171117433855979443557987035158250386343091063510776640623123668808832987706388430973801155931354965850214447254634690146708203626373189659075327467602032807223495137635981210320405619682687966819080149948303222995302848218841424195676765109882087340442027368846695420372536811407973658230769597018046585240803609741451498847099506923062835400132577696389198772341582304023818589952091969384611840
add v740 6442197994971210171117433855979443557987035158250386343091063510776640623123668808832987706388430973801155931354965850214447254634690146708203626373189659075327467602032807223495137635981210320405619682687966819080149948303222995302848218841424195676765109882087340442027368846695420372536811407973658230769597018046585240803609741451498847099506923062835400132577696389198772341582304023818589952091969384611840
add v742 6442197994971210171117433855979443557987035158250386343091063510776640623123668808832987706388430973801155931354965850214447254634690146708203626373189659075327467602032807223495137635981210320405619682687966819080149948303222995302848218841424195676765109882087340442027368846695420372536811407973658230769597018046585240803609741451498847099506923062835400132577696389198772341582304023818589952091969384611840
add v744 6442197994971210171117433855979443557987035158250386343091063510776640623123668808832987706388430973801155931354965850214447254634690146708203626373189659075327467602032807223495137635981210320405619682687966819080149948303222995302848218841424195676765109882087340442027368846695420372536811407973658230769597018046585240803609741451498847099506923062835400132577696389198772341582304023818589952091969384611840
add v746 6442197994971210171117433855979443557987035158250386343091063510776640623123668808832987706388430973801155931354965850214447254634690146708203626373189659075327467602032807223495137635981210320405619682687966819080149948303222995302848218841424195676765109882087340442027368846695420372536811407973658230769597018046585240803609741451498847099506923062835400132577696389198772341582304023818589952091969384611840
add v748 6442197994971210171117433855979443557987035158250386343091063510776640623123668808832987706388430973801155931354965850214447254634690146708203626373189659075327467602032807223495137635981210320405619682687966819080149948303222995302848218841424195676765109882087340442027368846695420372536811407973658230769597018046585240803609741451498847099506923062835400132577696389198772341582304023818589952091969384611840
add v750 6442197994971210171117433855979443557987035158250386343091063510776640623123668808832987706388430973801155931354965850214447254634690146708203626373189659075327467602032807223495137635981210320405619682687966819080149948303222995302848218841424195676765109882087340442027368846695420372536811407973658230769597018046585240803609741451498847099506923062835400132577696389198772341582304023818589952091969384611840
add v752 6442197994971210171117433855979443557987035158250386343091063510776640623123668808832987706388430973801155931354965850214447254634690146708203626373189659075327467602032807223495137635981210320405619682687966819080149948303222995302848218841424195676765109882087340442027368846695420372536811407973658230769597018046585240803609741451498847099506923062835400132577696389198772341582304023818589952091969384611840
add v754 6442197994971210171117433855979443557987035158250386343091063510776640623123668808832987706388430973801155931354965850214447254634690146708203626373189659075327467602032807223495137635981210320405619682687966819080149948303222995302848218841424195676765109882087340442027368846695420372536811407973658230769597018046585240803609741451498847099506923062835400132577696389198772341582304023818589952091969384611840
add v756 6442197994971210171117433855979443557987035158250386343091063510776640623123668808832987706388430973801155931354965850214447254634690146708203626373189659075327467602032807223495137635981210320405619682687966819080149948303222995302848218841424195676765109882087340442027368846695420372536811407973658230769597018046585240803609741451498847099506923062835400132577696389198772341582304023818589952091969384611840
shl v724 4107
add v725 v774
shl v723 8214
add v775 v776
shl v722 12321
add v777 v778
shl v721 16428
add v779 v780
shl v720 20535
add v781 v782
shl v719 24642
add v783 v784
shl v718 28749
add v785 v786
shl v717 32856
add v787 v788
shl v716 36963
add v789 v790
shl v715 41070
add v791 v792
shl v714 45177
add v793 v794
shl v713 49284
add v795 v796
shl v712 53391
add v797 v798
shl v711 57498
add v799 v800
shl v710 61605
add v801 v802
shl v709 65712
add v803 v804
shl v708 69819
add v805 v806
sub v807 v673
shl v772 4107
add v773 v809
shl v771 8214
add v810 v811
shl v770 12321
add v812 v813
shl v769 16428
add v814 v815
shl v768 20535
add v816 v817
shl v767 24642
add v818 v819
shl v766 28749
add v820 v821
shl v765 32856
add v822 v823
shl v764 36963
add v824 v825
shl v763 41070
add v826 v827
shl v762 45177
add v828 v829
shl v761 49284
add v830 v831
shl v760 53391
add v832 v833
shl v759 57498
add v834 v835
shl v758 61605
add v836 v837
shl v757 65712
add v838 v839
sub v840 v674
shr v32 36963
shr v35 36963
mul v665 v709
shl v620 1368
add v844 v845
mul v620 v758
shl v665 1368
add v847 v848
sub v846 v849
sub v849 v846
add v850 v851
sub 1 v852
add v672 v853
mul v665 v665
mul v855 v808
mul v620 v665
shl v857 4107
add v858 v846
sub v859 v849
mul v860 v841
sub v861 v856
sub v856 v861
add v863 v862
div v864 v640
land v865 v39
mul v640 v866
land v867 v39
land v864 v39
sub v869 v868
sub v868 v869
add v870 v871
add v854 v872
add v865 v842
land v874 v843
shr v874 65712
add v875 v876
add v873 v877
shr v874 61605
sub v879 v36
shr v874 57498
land v881 v37
sub 1 v862
sub 1 v883
xor v625 v884
sub 1 v880
add v878 v886
shr v32 41070
shr v35 41070
mul v880 v758
add v890 v848
mul v665 v882
shl v880 1368
add v892 v893
sub v891 v894
sub v894 v891
add v895 v896
sub 1 v897
add v887 v898
mul v880 v880
mul v900 v841
mul v665 v880
shl v902 4107
add v903 v891
sub v904 v894
mul v905 v865
sub v906 v901
sub v901 v906
add v908 v907
div v909 v855
land v910 v39
mul v855 v911
land v912 v39
land v909 v39
sub v914 v913
sub v913 v914
add v915 v916
add v899 v917
add v910 v888
land v919 v889
shr v919 61605
add v920 v921
add v918 v922
shr v919 57498
sub v924 v36
shr v919 53391
land v926 v37
sub 1 v907
sub 1 v928
xor v670 v929
sub 1 v925
add v923 v931
shr v32 45177
shr v35 45177
mul v925 v882
add v935 v893
mul v880 v927
shl v925 1368
add v937 v938
sub v936 v939
sub v939 v936
add v940 v941
sub 1 v942
add v932 v943
mul v925 v925
mul v945 v865
mul v880 v925
shl v947 4107
add v948 v936
sub v949 v939
mul v950 v910
sub v951 v946
sub v946 v951
add v953 v952
div v954 v900
land v955 v39
mul v900 v956
land v957 v39
land v954 v39
sub v959 v958
sub v958 v959
add v960 v961
add v944 v962
add v955 v933
land v964 v934
shr v964 57498
add v965 v966
add v963 v967
shr v964 53391
sub v969 v36
shr v964 49284
land v971 v37
sub 1 v952
sub 1 v973
xor v885 v974
sub 1 v970
add v968 v976
shr v32 49284
shr v35 49284
mul v970 v927
add v980 v938
mul v925 v972
shl v970 1368
add v982 v983
sub v981 v984
sub v984 v981
add v985 v986
sub 1 v987
add v977 v988
mul v970 v970
mul v990 v910
mul v925 v970
shl v992 4107
add v993 v981
sub v994 v984
mul v995 v955
sub v996 v991
sub v991 v996
add v998 v997
div v999 v945
land v1000 v39
mul v945 v1001
land v1002 v39
land v999 v39
sub v1004 v1003
sub v1003 v1004
add v1005 v1006
add v989 v1007
add v1000 v978
land v1009 v979
shr v1009 53391
add v1010 v1011
add v1008 v1012
shr v1009 49284
sub v1014 v36
shr v1009 45177
land v1016 v37
sub 1 v997
sub 1 v1018
xor v930 v1019
sub 1 v1015
add v1013 v1021
shr v52 67749
shr v52 73908
land v969 v37
shr v964 45177
land v1026 v37
shr v964 41070
land v1028 v37
shr v964 36963
land v1030 v37
shr v964 32856
land v1032 v37
shr v964 28749
land v1034 v37
shr v964 24642
land v1036 v37
shr v964 20535
land v1038 v37
shr v964 16428
land v1040 v37
shr v964 12321
land v1042 v37
shr v964 8214
land v1044 v37
shr v964 4107
land v1046 v37
shr v964 0
land v1048 v37
add v1025 517072097140976116811438027018719231367105642715447744514085526840394482221886254291155222584366615419019487374750368311905912946407854737521410438183172529930094037876815937468003164006234433708736922214138638894433704288110798664733430065857631692371055947289489817175424573641533384128887850679594455194549473402879727628516512341950342965209495190192031493853917422947263611859840227390422927165421214100764956415641263653562512497051919466823598120964185733845052221413631285755613939436429509326125978818793408450062667307179122233819087745517687743875768634750775239230012752249476804198114827364992956382576640
add v972 517072097140976116811438027018719231367105642715447744514085526840394482221886254291155222584366615419019487374750368311905912946407854737521410438183172529930094037876815937468003164006234433708736922214138638894433704288110798664733430065857631692371055947289489817175424573641533384128887850679594455194549473402879727628516512341950342965209495190192031493853917422947263611859840227390422927165421214100764956415641263653562512497051919466823598120964185733845052221413631285755613939436429509326125978818793408450062667307179122233819087745517687743875768634750775239230012752249476804198114827364992956382576640
add v1027 517072097140976116811438027018719231367105642715447744514085526840394482221886254291155222584366615419019487374750368311905912946407854737521410438183172529930094037876815937468003164006234433708736922214138638894433704288110798664733430065857631692371055947289489817175424573641533384128887850679594455194549473402879727628516512341950342965209495190192031493853917422947263611859840227390422927165421214100764956415641263653562512497051919466823598120964185733845052221413631285755613939436429509326125978818793408450062667307179122233819087745517687743875768634750775239230012752249476804198114827364992956382576640
add v1029 517072097140976116811438027018719231367105642715447744514085526840394482221886254291155222584366615419019487374750368311905912946407854737521410438183172529930094037876815937468003164006234433708736922214138638894433704288110798664733430065857631692371055947289489817175424573641533384128887850679594455194549473402879727628516512341950342965209495190192031493853917422947263611859840227390422927165421214100764956415641263653562512497051919466823598120964185733845052221413631285755613939436429509326125978818793408450062667307179122233819087745517687743875768634750775239230012752249476804198114827364992956382576640
add v1031 517072097140976116811438027018719231367105642715447744514085526840394482221886254291155222584366615419019487374750368311905912946407854737521410438183172529930094037876815937468003164006234433708736922214138638894433704288110798664733430065857631692371055947289489817175424573641533384128887850679594455194549473402879727628516512341950342965209495190192031493853917422947263611859840227390422927165421214100764956415641263653562512497051919466823598120964185733845052221413631285755613939436429509326125978818793408450062667307179122233819087745517687743875768634750775239230012752249476804198114827364992956382576640
add v1033 517072097140976116811438027018719231367105642715447744514085526840394482221886254291155222584366615419019487374750368311905912946407854737521410438183172529930094037876815937468003164006234433708736922214138638894433704288110798664733430065857631692371055947289489817175424573641533384128887850679594455194549473402879727628516512341950342965209495190192031493853917422947263611859840227390422927165421214100764956415641263653562512497051919466823598120964185733845052221413631285755613939436429509326125978818793408450062667307179122233819087745517687743875768634750775239230012752249476804198114827364992956382576640
add v1035 517072097140976116811438027018719231367105642715447744514085526840394482221886254291155222584366615419019487374750368311905912946407854737521410438183172529930094037876815937468003164006234433708736922214138638894433704288110798664733430065857631692371055947289489817175424573641533384128887850679594455194549473402879727628516512341950342965209495190192031493853917422947263611859840227390422927165421214100764956415641263653562512497051919466823598120964185733845052221413631285755613939436429509326125978818793408450062667307179122233819087745517687743875768634750775239230012752249476804198114827364992956382576640
add v1037 517072097140976116811438027018719231367105642715447744514085526840394482221886254291155222584366615419019487374750368311905912946407854737521410438183172529930094037876815937468003164006234433708736922214138638894433704288110798664733430065857631692371055947289489817175424573641533384128887850679594455194549473402879727628516512341950342965209495190192031493853917422947263611859840227390422927165421214100764956415641263653562512497051919466823598120964185733845052221413631285755613939436429509326125978818793408450062667307179122233819087745517687743875768634750775239230012752249476804198114827364992956382576640
add v1039 517072097140976116811438027018719231367105642715447744514085526840394482221886254291155222584366615419019487374750368311905912946407854737521410438183172529930094037876815937468003164006234433708736922214138638894433704288110798664733430065857631692371055947289489817175424573641533384128887850679594455194549473402879727628516512341950342965209495190192031493853917422947263611859840227390422927165421214100764956415641263653562512497051919466823598120964185733845052221413631285755613939436429509326125978818793408450062667307179122233819087745517687743875768634750775239230012752249476804198114827364992956382576640
add v1041 517072097140976116811438027018719231367105642715447744514085526840394482221886254291155222584366615419019487374750368311905912946407854737521410438183172529930094037876815937468003164006234433708736922214138638894433704288110798664733430065857631692371055947289489817175424573641533384128887850679594455194549473402879727628516512341950342965209495190192031493853917422947263611859840227390422927165421214100764956415641263653562512497051919466823598120964185733845052221413631285755613939436429509326125978818793408450062667307179122233819087745517687743875768634750775239230012752249476804198114827364992956382576640
add v1043 517072097140976116811438027018719231367105642715447744514085526840394482221886254291155222584366615419019487374750368311905912946407854737521410438183172529930094037876815937468003164006234433708736922214138638894433704288110798664733430065857631692371055947289489817175424573641533384128887850679594455194549473402879727628516512341950342965209495190192031493853917422947263611859840227390422927165421214100764956415641263653562512497051919466823598120964185733845052221413631285755613939436429509326125978818793408450062667307179122233819087745517687743875768634750775239230012752249476804198114827364992956382576640
add v1045 517072097140976116811438027018719231367105642715447744514085526840394482221886254291155222584366615419019487374750368311905912946407854737521410438183172529930094037876815937468003164006234433708736922214138638894433704288110798664733430065857631692371055947289489817175424573641533384128887850679594455194549473402879727628516512341950342965209495190192031493853917422947263611859840227390422927165421214100764956415641263653562512497051919466823598120964185733845052221413631285755613939436429509326125978818793408450062667307179122233819087745517687743875768634750775239230012752249476804198114827364992956382576640
add v1047 517072097140976116811438027018719231367105642715447744514085526840394482221886254291155222584366615419019487374750368311905912946407854737521410438183172529930094037876815937468003164006234433708736922214138638894433704288110798664733430065857631692371055947289489817175424573641533384128887850679594455194549473402879727628516512341950342965209495190192031493853917422947263611859840227390422927165421214100764956415641263653562512497051919466823598120964185733845052221413631285755613939436429509326125978818793408450062667307179122233819087745517687743875768634750775239230012752249476804198114827364992956382576640
add v1049 517072097140976116811438027018719231367105642715447744514085526840394482221886254291155222584366615419019487374750368311905912946407854737521410438183172529930094037876815937468003164006234433708736922214138638894433704288110798664733430065857631692371055947289489817175424573641533384128887850679594455194549473402879727628516512341950342965209495190192031493853917422947263611859840227390422927165421214100764956415641263653562512497051919466823598120964185733845052221413631285755613939436429509326125978818793408450062667307179122233819087745517687743875768634750775239230012752249476804198114827364992956382576640
land v1014 v37
shr v1009 41070
land v1065 v37
shr v1009 36963
land v1067 v37
shr v1009 32856
land v1069 v37
shr v1009 28749
land v1071 v37
shr v1009 24642
land v1073 v37
shr v1009 20535
land v1075 v37
shr v1009 16428
land v1077 v37
shr v1009 12321
land v1079 v37
shr v1009 8214
land v1081 v37
shr v1009 4107
land v1083 v37
shr v1009 0
land v1085 v37
add v1064 517072097140976116811438027018719231367105642715447744514085526840394482221886254291155222584366615419019487374750368311905912946407854737521410438183172529930094037876815937468003164006234433708736922214138638894433704288110798664733430065857631692371055947289489817175424573641533384128887850679594455194549473402879727628516512341950342965209495190192031493853917422947263611859840227390422927165421214100764956415641263653562512497051919466823598120964185733845052221413631285755613939436429509326125978818793408450062667307179122233819087745517687743875768634750775239230012752249476804198114827364992956382576640
add v1017 517072097140976116811438027018719231367105642715447744514085526840394482221886254291155222584366615419019487374750368311905912946407854737521410438183172529930094037876815937468003164006234433708736922214138638894433704288110798664733430065857631692371055947289489817175424573641533384128887850679594455194549473402879727628516512341950342965209495190192031493853917422947263611859840227390422927165421214100764956415641263653562512497051919466823598120964185733845052221413631285755613939436429509326125978818793408450062667307179122233819087745517687743875768634750775239230012752249476804198114827364992956382576640
add v1066 517072097140976116811438027018719231367105642715447744514085526840394482221886254291155222584366615419019487374750368311905912946407854737521410438183172529930094037876815937468003164006234433708736922214138638894433704288110798664733430065857631692371055947289489817175424573641533384128887850679594455194549473402879727628516512341950342965209495190192031493853917422947263611859840227390422927165421214100764956415641263653562512497051919466823598120964185733845052221413631285755613939436429509326125978818793408450062667307179122233819087745517687743875768634750775239230012752249476804198114827364992956382576640
add v1068 517072097140976116811438027018719231367105642715447744514085526840394482221886254291155222584366615419019487374750368311905912946407854737521410438183172529930094037876815937468003164006234433708736922214138638894433704288110798664733430065857631692371055947289489817175424573641533384128887850679594455194549473402879727628516512341950342965209495190192031493853917422947263611859840227390422927165421214100764956415641263653562512497051919466823598120964185733845052221413631285755613939436429509326125978818793408450062667307179122233819087745517687743875768634750775239230012752249476804198114827364992956382576640
add v1070 517072097140976116811438027018719231367105642715447744514085526840394482221886254291155222584366615419019487374750368311905912946407854737521410438183172529930094037876815937468003164006234433708736922214138638894433704288110798664733430065857631692371055947289489817175424573641533384128887850679594455194549473402879727628516512341950342965209495190192031493853917422947263611859840227390422927165421214100764956415641263653562512497051919466823598120964185733845052221413631285755613939436429509326125978818793408450062667307179122233819087745517687743875768634750775239230012752249476804198114827364992956382576640
add v1072 517072097140976116811438027018719231367105642715447744514085526840394482221886254291155222584366615419019487374750368311905912946407854737521410438183172529930094037876815937468003164006234433708736922214138638894433704288110798664733430065857631692371055947289489817175424573641533384128887850679594455194549473402879727628516512341950342965209495190192031493853917422947263611859840227390422927165421214100764956415641263653562512497051919466823598120964185733845052221413631285755613939436429509326125978818793408450062667307179122233819087745517687743875768634750775239230012752249476804198114827364992956382576640
add v1074 517072097140976116811438027018719231367105642715447744514085526840394482221886254291155222584366615419019487374750368311905912946407854737521410438183172529930094037876815937468003164006234433708736922214138638894433704288110798664733430065857631692371055947289489817175424573641533384128887850679594455194549473402879727628516512341950342965209495190192031493853917422947263611859840227390422927165421214100764956415641263653562512497051919466823598120964185733845052221413631285755613939436429509326125978818793408450062667307179122233819087745517687743875768634750775239230012752249476804198114827364992956382576640
add v1076 517072097140976116811438027018719231367105642715447744514085526840394482221886254291155222584366615419019487374750368311905912946407854737521410438183172529930094037876815937468003164006234433708736922214138638894433704288110798664733430065857631692371055947289489817175424573641533384128887850679594455194549473402879727628516512341950342965209495190192031493853917422947263611859840227390422927165421214100764956415641263653562512497051919466823598120964185733845052221413631285755613939436429509326125978818793408450062667307179122233819087745517687743875768634750775239230012752249476804198114827364992956382576640
add v1078 517072097140976116811438027018719231367105642715447744514085526840394482221886254291155222584366615419019487374750368311905912946407854737521410438183172529930094037876815937468003164006234433708736922214138638894433704288110798664733430065857631692371055947289489817175424573641533384128887850679594455194549473402879727628516512341950342965209495190192031493853917422947263611859840227390422927165421214100764956415641263653562512497051919466823598120964185733845052221413631285755613939436429509326125978818793408450062667307179122233819087745517687743875768634750775239230012752249476804198114827364992956382576640
add v1080 517072097140976116811438027018719231367105642715447744514085526840394482221886254291155222584366615419019487374750368311905912946407854737521410438183172529930094037876815937468003164006234433708736922214138638894433704288110798664733430065857631692371055947289489817175424573641533384128887850679594455194549473402879727628516512341950342965209495190192031493853917422947263611859840227390422927165421214100764956415641263653562512497051919466823598120964185733845052221413631285755613939436429509326125978818793408450062667307179122233819087745517687743875768634750775239230012752249476804198114827364992956382576640
add v1082 517072097140976116811438027018719231367105642715447744514085526840394482221886254291155222584366615419019487374750368311905912946407854737521410438183172529930094037876815937468003164006234433708736922214138638894433704288110798664733430065857631692371055947289489817175424573641533384128887850679594455194549473402879727628516512341950342965209495190192031493853917422947263611859840227390422927165421214100764956415641263653562512497051919466823598120964185733845052221413631285755613939436429509326125978818793408450062667307179122233819087745517687743875768634750775239230012752249476804198114827364992956382576640
add v1084 517072097140976116811438027018719231367105642715447744514085526840394482221886254291155222584366615419019487374750368311905912946407854737521410438183172529930094037876815937468003164006234433708736922214138638894433704288110798664733430065857631692371055947289489817175424573641533384128887850679594455194549473402879727628516512341950342965209495190192031493853917422947263611859840227390422927165421214100764956415641263653562512497051919466823598120964185733845052221413631285755613939436429509326125978818793408450062667307179122233819087745517687743875768634750775239230012752249476804198114827364992956382576640
add v1086 517072097140976116811438027018719231367105642715447744514085526840394482221886254291155222584366615419019487374750368311905912946407854737521410438183172529930094037876815937468003164006234433708736922214138638894433704288110798664733430065857631692371055947289489817175424573641533384128887850679594455194549473402879727628516512341950342965209495190192031493853917422947263611859840227390422927165421214100764956415641263653562512497051919466823598120964185733845052221413631285755613939436429509326125978818793408450062667307179122233819087745517687743875768634750775239230012752249476804198114827364992956382576640
shl v1062 6159
add v1063 v1100
shl v1061 12318
add v1101 v1102
shl v1060 18477
add v1103 v1104
shl v1059 24636
add v1105 v1106
shl v1058 30795
add v1107 v1108
shl v1057 36954
add v1109 v1110
shl v1056 43113
add v1111 v1112
shl v1055 49272
add v1113 v1114
shl v1054 55431
add v1115 v1116
shl v1053 61590
add v1117 v1118
shl v1052 67749
add v1119 v1120
shl v1051 73908
add v1121 v1122
shl v1050 80067
add v1123 v1124
sub v1125 v1023
shl v1098 6159
add v1099 v1127
shl v1097 12318
add v1128 v1129
shl v1096 18477
add v1130 v1131
shl v1095 24636
add v1132 v1133
shl v1094 30795
add v1134 v1135
shl v1093 36954
add v1136 v1137
shl v1092 43113
add v1138 v1139
shl v1091 49272
add v1140 v1141
shl v1090 55431
add v1142 v1143
shl v1089 61590
add v1144 v1145
shl v1088 67749
add v1146 v1147
shl v1087 73908
add v1148 v1149
sub v1150 v1024
shr v52 80067
shr v55 80067
mul v1015 v1051
shl v970 2052
add v1154 v1155
mul v970 v1088
shl v1015 2052
add v1157 v1158
sub v1156 v1159
sub v1159 v1156
add v1160 v1161
sub 1 v1162
add v1022 v1163
mul v1015 v1015
mul v1165 v1126
mul v970 v1015
shl v1167 6159
add v1168 v1156
sub v1169 v1159
mul v1170 v1151
sub v1171 v1166
sub v1166 v1171
add v1173 v1172
div v1174 v990
land v1175 v59
mul v990 v1176
land v1177 v59
land v1174 v59
sub v1179 v1178
sub v1178 v1179
add v1180 v1181
add v1164 v1182
add v1175 v1152
land v1184 v1153
shr v1184 73908
add v1185 v1186
add v1183 v1187
shr v1184 67749
sub v1189 v56
shr v1184 61590
land v1191 v57
sub 1 v1172
sub 1 v1193
xor v975 v1194
sub 1 v1190
add v1188 v1196
shr v52 86226
shr v55 86226
mul v1190 v1088
add v1200 v1158
mul v1015 v1192
shl v1190 2052
add v1202 v1203
sub v1201 v1204
sub v1204 v1201
add v1205 v1206
sub 1 v1207
add v1197 v1208
mul v1190 v1190
mul v1210 v1151
mul v1015 v1190
shl v1212 6159
add v1213 v1201
sub v1214 v1204
mul v1215 v1175
sub v1216 v1211
sub v1211 v1216
add v1218 v1217
div v1219 v1165
land v1220 v59
mul v1165 v1221
land v1222 v59
land v1219 v59
sub v1224 v1223
sub v1223 v1224
add v1225 v1226
add v1209 v1227
add v1220 v1198
land v1229 v1199
shr v1229 67749
add v1230 v1231
add v1228 v1232
shr v1229 61590
sub v1234 v56
shr v1229 55431
land v1236 v57
sub 1 v1217
sub 1 v1238
xor v1020 v1239
sub 1 v1235
add v1233 v1241
shr v52 92385
shr v55 92385
mul v1235 v1192
add v1245 v1203
mul v1190 v1237
shl v1235 2052
add v1247 v1248
sub v1246 v1249
sub v1249 v1246
add v1250 v1251
sub 1 v1252
add v1242 v1253
mul v1235 v1235
mul v1255 v1175
mul v1190 v1235
shl v1257 6159
add v1258 v1246
sub v1259 v1249
mul v1260 v1220
sub v1261 v1256
sub v1256 v1261
add v1263 v1262
div v1264 v1210
land v1265 v59
mul v1210 v1266
land v1267 v59
land v1264 v59
sub v1269 v1268
sub v1268 v1269
add v1270 v1271
add v1254 v1272
add v1265 v1243
land v1274 v1244
shr v1274 61590
add v1275 v1276
add v1273 v1277
shr v1274 55431
sub v1279 v56
shr v1274 49272
land v1281 v57
sub 1 v1262
sub 1 v1283
xor v1195 v1284
sub 1 v1280
add v1278 v1286
land v1234 v57
shr v1229 49272
land v1289 v57
shr v1229 43113
land v1291 v57
shr v1229 36954
land v1293 v57
shr v1229 30795
land v1295 v57
shr v1229 24636
land v1297 v57
shr v1229 18477
land v1299 v57
shr v1229 12318
land v1301 v57
shr v1229 6159
land v1303 v57
shr v1229 0
land v1305 v57
sub v1288 v56
sub v56 v1288
add v1307 v1308
shl v1309 1
sub 1 v1308
sub 1 v1311
xor v1312 v1240
add v1310 v1313
sub v1237 v56
sub v56 v1237
add v1315 v1316
shl v1317 1
sub 1 v1316
sub 1 v1319
xor v1320 v1240
add v1318 v1321
sub v1290 v56
sub v56 v1290
add v1323 v1324
shl v1325 1
sub 1 v1324
sub 1 v1327
xor v1328 v1240
add v1326 v1329
sub v1292 v56
sub v56 v1292
add v1331 v1332
shl v1333 1
sub 1 v1332
sub 1 v1335
xor v1336 v1240
add v1334 v1337
sub v1294 v56
sub v56 v1294
add v1339 v1340
shl v1341 1
sub 1 v1340
sub 1 v1343
xor v1344 v1240
add v1342 v1345
sub v1296 v56
sub v56 v1296
add v1347 v1348
shl v1349 1
sub 1 v1348
sub 1 v1351
xor v1352 v1240
add v1350 v1353
sub v1298 v56
sub v56 v1298
add v1355 v1356
shl v1357 1
sub 1 v1356
sub 1 v1359
xor v1360 v1240
add v1358 v1361
sub v1300 v56
sub v56 v1300
add v1363 v1364
shl v1365 1
sub 1 v1364
sub 1 v1367
xor v1368 v1240
add v1366 v1369
sub v1302 v56
sub v56 v1302
add v1371 v1372
shl v1373 1
sub 1 v1372
sub 1 v1375
xor v1376 v1240
add v1374 v1377
sub v1304 v56
sub v56 v1304
add v1379 v1380
shl v1381 1
sub 1 v1380
sub 1 v1383
xor v1384 v1240
add v1382 v1385
sub v1306 v56
sub v56 v1306
add v1387 v1388
shl v1389 1
sub 1 v1388
sub 1 v1391
xor v1392 v1240
add v1390 v1393
land v1279 v57
shr v1274 43113
land v1396 v57
shr v1274 36954
land v1398 v57
shr v1274 30795
land v1400 v57
shr v1274 24636
land v1402 v57
shr v1274 18477
land v1404 v57
shr v1274 12318
land v1406 v57
shr v1274 6159
land v1408 v57
shr v1274 0
land v1410 v57
sub v1395 v56
sub v56 v1395
add v1412 v1413
shl v1414 1
sub 1 v1413
sub 1 v1416
xor v1417 v1285
add v1415 v1418
sub v1282 v56
sub v56 v1282
add v1420 v1421
shl v1422 1
sub 1 v1421
sub 1 v1424
xor v1425 v1285
add v1423 v1426
sub v1397 v56
sub v56 v1397
add v1428 v1429
shl v1430 1
sub 1 v1429
sub 1 v1432
xor v1433 v1285
add v1431 v1434
sub v1399 v56
sub v56 v1399
add v1436 v1437
shl v1438 1
sub 1 v1437
sub 1 v1440
xor v1441 v1285
add v1439 v1442
sub v1401 v56
sub v56 v1401
add v1444 v1445
shl v1446 1
sub 1 v1445
sub 1 v1448
xor v1449 v1285
add v1447 v1450
sub v1403 v56
sub v56 v1403
add v1452 v1453
shl v1454 1
sub 1 v1453
sub 1 v1456
xor v1457 v1285
add v1455 v1458
sub v1405 v56
sub v56 v1405
add v1460 v1461
shl v1462 1
sub 1 v1461
sub 1 v1464
xor v1465 v1285
add v1463 v1466
sub v1407 v56
sub v56 v1407
add v1468 v1469
shl v1470 1
sub 1 v1469
sub 1 v1472
xor v1473 v1285
add v1471 v1474
sub v1409 v56
sub v56 v1409
add v1476 v1477
shl v1478 1
sub 1 v1477
sub 1 v1480
xor v1481 v1285
add v1479 v1482
sub v1411 v56
sub v56 v1411
add v1484 v1485
shl v1486 1
sub 1 v1485
sub 1 v1488
xor v1489 v1285
add v1487 v1490
shr v1314 1
mul v1492 v1492
shr v1419 1
mul v1494 v1494
mul v1494 v1492
xor v1419 v1314
land v1497 1
xor v1498 1
shr v1322 1
mul v1494 v1500
shr v1427 1
mul v1492 v1502
add v1501 v1503
xor v1419 v1322
land v1505 1
mul v1506 v1501
xor v1314 v1427
land v1508 1
xor v1509 1
mul v1510 v1503
add v1507 v1511
sub v1504 v1512
sub v1513 v1512
sub v1512 v1513
add v1514 v1515
div v1516 1
shl v1517 1
sub 1 v1515
sub 1 v1519
add v1518 v1520
shr v1521 1
land v1521 1
xor v1523 1
shr v1330 1
mul v1495 v1525
shr v1435 1
mul v1496 v1527
add v1526 v1528
mul v1522 v1502
add v1529 v1530
land v1330 1
mul v1532 v1526
land v1435 1
xor v1534 v1499
mul v1535 v1528
add v1533 v1536
land v1427 1
xor v1538 v1524
mul v1539 v1530
add v1537 v1540
sub v1531 v1541
sub v1542 v1541
sub v1541 v1542
add v1543 v1544
div v1545 v1493
shl v1546 1
sub 1 v1544
sub 1 v1548
add v1547 v1549
shr v1338 1
mul v1495 v1551
shr v1443 1
mul v1496 v1553
add v1552 v1554
mul v1522 v1527
add v1555 v1556
land v1338 1
mul v1558 v1552
land v1443 1
xor v1560 v1499
mul v1561 v1554
add v1559 v1562
xor v1534 v1524
mul v1564 v1556
add v1563 v1565
sub v1557 v1566
sub v1567 v1566
sub v1566 v1567
add v1568 v1569
div v1570 v1493
shl v1571 1
sub 1 v1569
sub 1 v1573
add v1572 v1574
shr v1346 1
mul v1495 v1576
shr v1451 1
mul v1496 v1578
add v1577 v1579
mul v1522 v1553
add v1580 v1581
land v1346 1
mul v1583 v1577
land v1451 1
xor v1585 v1499
mul v1586 v1579
add v1584 v1587
xor v1560 v1524
mul v1589 v1581
add v1588 v1590
sub v1582 v1591
sub v1592 v1591
sub v1591 v1592
add v1593 v1594
div v1595 v1493
shl v1596 1
sub 1 v1594
sub 1 v1598
add v1597 v1599
shr v1354 1
mul v1495 v1601
shr v1459 1
mul v1496 v1603
add v1602 v1604
mul v1522 v1578
add v1605 v1606
land v1354 1
mul v1608 v1602
land v1459 1
xor v1610 v1499
mul v1611 v1604
add v1609 v1612
xor v1585 v1524
mul v1614 v1606
add v1613 v1615
sub v1607 v1616
sub v1617 v1616
sub v1616 v1617
add v1618 v1619
div v1620 v1493
shl v1621 1
sub 1 v1619
sub 1 v1623
add v1622 v1624
shr v1362 1
mul v1495 v1626
shr v1467 1
mul v1496 v1628
add v1627 v1629
mul v1522 v1603
add v1630 v1631
land v1362 1
mul v1633 v1627
land v1467 1
xor v1635 v1499
mul v1636 v1629
add v1634 v1637
xor v1610 v1524
mul v1639 v1631
add v1638 v1640
sub v1632 v1641
sub v1642 v1641
sub v1641 v1642
add v1643 v1644
div v1645 v1493
shl v1646 1
sub 1 v1644
sub 1 v1648
add v1647 v1649
shr v1370 1
mul v1495 v1651
shr v1475 1
mul v1496 v1653
add v1652 v1654
mul v1522 v1628
add v1655 v1656
land v1370 1
mul v1658 v1652
land v1475 1
xor v1660 v1499
mul v1661 v1654
add v1659 v1662
xor v1635 v1524
mul v1664 v1656
add v1663 v1665
sub v1657 v1666
sub v1667 v1666
sub v1666 v1667
add v1668 v1669
div v1670 v1493
shl v1671 1
sub 1 v1669
sub 1 v1673
add v1672 v1674
shr v1378 1
mul v1495 v1676
shr v1483 1
mul v1496 v1678
add v1677 v1679
mul v1522 v1653
add v1680 v1681
land v1378 1
mul v1683 v1677
land v1483 1
xor v1685 v1499
mul v1686 v1679
add v1684 v1687
xor v1660 v1524
mul v1689 v1681
add v1688 v1690
sub v1682 v1691
sub v1692 v1691
sub v1691 v1692
add v1693 v1694
div v1695 v1493
shl v1696 1
sub 1 v1694
sub 1 v1698
add v1697 v1699
shr v1386 1
mul v1495 v1701
shr v1491 1
mul v1496 v1703
add v1702 v1704
mul v1522 v1678
add v1705 v1706
land v1386 1
mul v1708 v1702
land v1491 1
xor v1710 v1499
mul v1711 v1704
add v1709 v1712
xor v1685 v1524
mul v1714 v1706
add v1713 v1715
sub v1707 v1716
sub v1717 v1716
sub v1716 v1717
add v1718 v1719
div v1720 v1493
shl v1721 1
sub 1 v1719
sub 1 v1723
add v1722 v1724
shr v1394 1
mul v1495 v1726
shr 0 1
mul v1496 v1728
add v1727 v1729
mul v1522 v1703
add v1730 v1731
land v1394 1
mul v1733 v1727
land 0 1
xor v1735 v1499
mul v1736 v1729
add v1734 v1737
xor v1710 v1524
mul v1739 v1731
add v1738 v1740
sub v1732 v1741
sub v1742 v1741
sub v1741 v1742
add v1743 v1744
div v1745 v1493
shl v1746 1
sub 1 v1744
sub 1 v1748
add v1747 v1749
sub 1 v1522
add v1745 0
add v1720 v1752
add v1695 v1753
add v1670 v1754
add v1645 v1755
add v1620 v1756
add v1595 v1757
add v1570 v1758
add v1545 v1759
add v1746 0
add v1721 v1761
add v1696 v1762
add v1671 v1763
add v1646 v1764
add v1621 v1765
add v1596 v1766
add v1571 v1767
add v1546 v1768
mul v1493 v1769
sub v1760 v1770
add v1751 v1771
shr v1550 1
sub 1 v1773
add v1772 v1774
add v1287 v1775
mul v1773 v1773
mul v1773 v1494
xor v1550 v1419
land v1779 1
xor v1780 1
mul v1773 v1502
shr v1575 1
mul v1494 v1783
add v1782 v1784
xor v1550 v1427
land v1786 1
mul v1787 v1782
xor v1419 v1575
land v1789 1
xor v1790 1
mul v1791 v1784
add v1788 v1792
sub v1785 v1793
sub v1794 v1793
sub v1793 v1794
add v1795 v1796
div v1797 1
shl v1798 1
sub 1 v1796
sub 1 v1800
add v1799 v1801
shr v1802 1
land v1802 1
xor v1804 1
mul v1777 v1527
shr v1600 1
mul v1778 v1807
add v1806 v1808
mul v1803 v1783
add v1809 v1810
mul v1534 v1806
land v1600 1
xor v1813 v1781
mul v1814 v1808
add v1812 v1815
land v1575 1
xor v1817 v1805
mul v1818 v1810
add v1816 v1819
sub v1811 v1820
sub v1821 v1820
sub v1820 v1821
add v1822 v1823
div v1824 v1495
shl v1825 1
sub 1 v1823
sub 1 v1827
add v1826 v1828
mul v1777 v1553
shr v1625 1
mul v1778 v1831
add v1830 v1832
mul v1803 v1807
add v1833 v1834
mul v1560 v1830
land v1625 1
xor v1837 v1781
mul v1838 v1832
add v1836 v1839
xor v1813 v1805
mul v1841 v1834
add v1840 v1842
sub v1835 v1843
sub v1844 v1843
sub v1843 v1844
add v1845 v1846
div v1847 v1495
shl v1848 1
sub 1 v1846
sub 1 v1850
add v1849 v1851
mul v1777 v1578
shr v1650 1
mul v1778 v1854
add v1853 v1855
mul v1803 v1831
add v1856 v1857
mul v1585 v1853
land v1650 1
xor v1860 v1781
mul v1861 v1855
add v1859 v1862
xor v1837 v1805
mul v1864 v1857
add v1863 v1865
sub v1858 v1866
sub v1867 v1866
sub v1866 v1867
add v1868 v1869
div v1870 v1495
shl v1871 1
sub 1 v1869
sub 1 v1873
add v1872 v1874
mul v1777 v1603
shr v1675 1
mul v1778 v1877
add v1876 v1878
mul v1803 v1854
add v1879 v1880
mul v1610 v1876
land v1675 1
xor v1883 v1781
mul v1884 v1878
add v1882 v1885
xor v1860 v1805
mul v1887 v1880
add v1886 v1888
sub v1881 v1889
sub v1890 v1889
sub v1889 v1890
add v1891 v1892
div v1893 v1495
shl v1894 1
sub 1 v1892
sub 1 v1896
add v1895 v1897
mul v1777 v1628
shr v1700 1
mul v1778 v1900
add v1899 v1901
mul v1803 v1877
add v1902 v1903
mul v1635 v1899
land v1700 1
xor v1906 v1781
mul v1907 v1901
add v1905 v1908
xor v1883 v1805
mul v1910 v1903
add v1909 v1911
sub v1904 v1912
sub v1913 v1912
sub v1912 v1913
add v1914 v1915
div v1916 v1495
shl v1917 1
sub 1 v1915
sub 1 v1919
add v1918 v1920
mul v1777 v1653
shr v1725 1
mul v1778 v1923
add v1922 v1924
mul v1803 v1900
add v1925 v1926
mul v1660 v1922
land v1725 1
xor v1929 v1781
mul v1930 v1924
add v1928 v1931
xor v1906 v1805
mul v1933 v1926
add v1932 v1934
sub v1927 v1935
sub v1936 v1935
sub v1935 v1936
add v1937 v1938
div v1939 v1495
shl v1940 1
sub 1 v1938
sub 1 v1942
add v1941 v1943
mul v1777 v1678
shr v1750 1
mul v1778 v1946
add v1945 v1947
mul v1803 v1923
add v1948 v1949
mul v1685 v1945
land v1750 1
xor v1952 v1781
mul v1953 v1947
add v1951 v1954
xor v1929 v1805
mul v1956 v1949
add v1955 v1957
sub v1950 v1958
sub v1959 v1958
sub v1958 v1959
add v1960 v1961
div v1962 v1495
shl v1963 1
sub 1 v1961
sub 1 v1965
add v1964 v1966
mul v1777 v1703
mul v1778 v1728
add v1968 v1969
mul v1803 v1946
add v1970 v1971
mul v1710 v1968
xor v1735 v1781
mul v1974 v1969
add v1973 v1975
xor v1952 v1805
mul v1977 v1971
add v1976 v1978
sub v1972 v1979
sub v1980 v1979
sub v1979 v1980
add v1981 v1982
div v1983 v1495
shl v1984 1
sub 1 v1982
sub 1 v1986
add v1985 v1987
sub 1 v1803
add v1983 0
add v1962 v1990
add v1939 v1991
add v1916 v1992
add v1893 v1993
add v1870 v1994
add v1847 v1995
add v1824 v1996
add v1984 0
add v1963 v1998
add v1940 v1999
add v1917 v2000
add v1894 v2001
add v1871 v2002
add v1848 v2003
add v1825 v2004
mul v1495 v2005
sub v1997 v2006
add v1989 v2007
shr v1829 1
sub 1 v2009
add v2008 v2010
add v1776 v2011
mul v2009 v2009
mul v2009 v1773
xor v1829 v1550
land v2015 1
xor v2016 1
mul v2009 v1783
shr v1852 1
mul v1773 v2019
add v2018 v2020
xor v1829 v1575
land v2022 1
mul v2023 v2018
xor v1550 v1852
land v2025 1
xor v2026 1
mul v2027 v2020
add v2024 v2028
sub v2021 v2029
sub v2030 v2029
sub v2029 v2030
add v2031 v2032
div v2033 1
shl v2034 1
sub 1 v2032
sub 1 v2036
add v2035 v2037
shr v2038 1
land v2038 1
xor v2040 1
mul v2013 v1807
shr v1875 1
mul v2014 v2043
add v2042 v2044
mul v2039 v2019
add v2045 v2046
mul v1813 v2042
land v1875 1
xor v2049 v2017
mul v2050 v2044
add v2048 v2051
land v1852 1
xor v2053 v2041
mul v2054 v2046
add v2052 v2055
sub v2047 v2056
sub v2057 v2056
sub v2056 v2057
add v2058 v2059
div v2060 v1777
shl v2061 1
sub 1 v2059
sub 1 v2063
add v2062 v2064
mul v2013 v1831
shr v1898 1
mul v2014 v2067
add v2066 v2068
mul v2039 v2043
add v2069 v2070
mul v1837 v2066
land v1898 1
xor v2073 v2017
mul v2074 v2068
add v2072 v2075
xor v2049 v2041
mul v2077 v2070
add v2076 v2078
sub v2071 v2079
sub v2080 v2079
sub v2079 v2080
add v2081 v2082
div v2083 v1777
shl v2084 1
sub 1 v2082
sub 1 v2086
add v2085 v2087
mul v2013 v1854
shr v1921 1
mul v2014 v2090
add v2089 v2091
mul v2039 v2067
add v2092 v2093
mul v1860 v2089
land v1921 1
xor v2096 v2017
mul v2097 v2091
add v2095 v2098
xor v2073 v2041
mul v2100 v2093
add v2099 v2101
sub v2094 v2102
sub v2103 v2102
sub v2102 v2103
add v2104 v2105
div v2106 v1777
shl v2107 1
sub 1 v2105
sub 1 v2109
add v2108 v2110
mul v2013 v1877
shr v1944 1
mul v2014 v2113
add v2112 v2114
mul v2039 v2090
add v2115 v2116
mul v1883 v2112
land v1944 1
xor v2119 v2017
mul v2120 v2114
add v2118 v2121
xor v2096 v2041
mul v2123 v2116
add v2122 v2124
sub v2117 v2125
sub v2126 v2125
sub v2125 v2126
add v2127 v2128
div v2129 v1777
shl v2130 1
sub 1 v2128
sub 1 v2132
add v2131 v2133
mul v2013 v1900
shr v1967 1
mul v2014 v2136
add v2135 v2137
mul v2039 v2113
add v2138 v2139
mul v1906 v2135
land v1967 1
xor v2142 v2017
mul v2143 v2137
add v2141 v2144
xor v2119 v2041
mul v2146 v2139
add v2145 v2147
sub v2140 v2148
sub v2149 v2148
sub v2148 v2149
add v2150 v2151
div v2152 v1777
shl v2153 1
sub 1 v2151
sub 1 v2155
add v2154 v2156
mul v2013 v1923
shr v1988 1
mul v2014 v2159
add v2158 v2160
mul v2039 v2136
add v2161 v2162
mul v1929 v2158
land v1988 1
xor v2165 v2017
mul v2166 v2160
add v2164 v2167
xor v2142 v2041
mul v2169 v2162
add v2168 v2170
sub v2163 v2171
sub v2172 v2171
sub v2171 v2172
add v2173 v2174
div v2175 v1777
shl v2176 1
sub 1 v2174
sub 1 v2178
add v2177 v2179
mul v2013 v1946
mul v2014 v1728
add v2181 v2182
mul v2039 v2159
add v2183 v2184
mul v1952 v2181
xor v1735 v2017
mul v2187 v2182
add v2186 v2188
xor v2165 v2041
mul v2190 v2184
add v2189 v2191
sub v2185 v2192
sub v2193 v2192
sub v2192 v2193
add v2194 v2195
div v2196 v1777
shl v2197 1
sub 1 v2195
sub 1 v2199
add v2198 v2200
sub 1 v2039
add v2196 0
add v2175 v2203
add v2152 v2204
add v2129 v2205
add v2106 v2206
add v2083 v2207
add v2060 v2208
add v2197 0
add v2176 v2210
add v2153 v2211
add v2130 v2212
add v2107 v2213
add v2084 v2214
add v2061 v2215
mul v1777 v2216
sub v2209 v2217
add v2202 v2218
shr v2065 1
sub 1 v2220
add v2219 v2221
add v2012 v2222
mul v2220 v2220
mul v2220 v2009
xor v2065 v1829
land v2226 1
xor v2227 1
mul v2220 v2019
shr v2088 1
mul v2009 v2230
add v2229 v2231
xor v2065 v1852
land v2233 1
mul v2234 v2229
xor v1829 v2088
land v2236 1
xor v2237 1
mul v2238 v2231
add v2235 v2239
sub v2232 v2240
sub v2241 v2240
sub v2240 v2241
add v2242 v2243
div v2244 1
shl v2245 1
sub 1 v2243
sub 1 v2247
add v2246 v2248
shr v2249 1
land v2249 1
xor v2251 1
mul v2224 v2043
shr v2111 1
mul v2225 v2254
add v2253 v2255
mul v2250 v2230
add v2256 v2257
mul v2049 v2253
land v2111 1
xor v2260 v2228
mul v2261 v2255
add v2259 v2262
land v2088 1
xor v2264 v2252
mul v2265 v2257
add v2263 v2266
sub v2258 v2267
sub v2268 v2267
sub v2267 v2268
add v2269 v2270
div v2271 v2013
shl v2272 1
sub 1 v2270
sub 1 v2274
add v2273 v2275
mul v2224 v2067
shr v2134 1
mul v2225 v2278
add v2277 v2279
mul v2250 v2254
add v2280 v2281
mul v2073 v2277
land v2134 1
xor v2284 v2228
mul v2285 v2279
add v2283 v2286
xor v2260 v2252
mul v2288 v2281
add v2287 v2289
sub v2282 v2290
sub v2291 v2290
sub v2290 v2291
add v2292 v2293
div v2294 v2013
shl v2295 1
sub 1 v2293
sub 1 v2297
add v2296 v2298
mul v2224 v2090
shr v2157 1
mul v2225 v2301
add v2300 v2302
mul v2250 v2278
add v2303 v2304
mul v2096 v2300
land v2157 1
xor v2307 v2228
mul v2308 v2302
add v2306 v2309
xor v2284 v2252
mul v2311 v2304
add v2310 v2312
sub v2305 v2313
sub v2314 v2313
sub v2313 v2314
add v2315 v2316
div v2317 v2013
shl v2318 1
sub 1 v2316
sub 1 v2320
add v2319 v2321
mul v2224 v2113
shr v2180 1
mul v2225 v2324
add v2323 v2325
mul v2250 v2301
add v2326 v2327
mul v2119 v2323
land v2180 1
xor v2330 v2228
mul v2331 v2325
add v2329 v2332
xor v2307 v2252
mul v2334 v2327
add v2333 v2335
sub v2328 v2336
sub v2337 v2336
sub v2336 v2337
add v2338 v2339
div v2340 v2013
shl v2341 1
sub 1 v2339
sub 1 v2343
add v2342 v2344
mul v2224 v2136
shr v2201 1
mul v2225 v2347
add v2346 v2348
mul v2250 v2324
add v2349 v2350
mul v2142 v2346
land v2201 1
xor v2353 v2228
mul v2354 v2348
add v2352 v2355
xor v2330 v2252
mul v2357 v2350
add v2356 v2358
sub v2351 v2359
sub v2360 v2359
sub v2359 v2360
add v2361 v2362
div v2363 v2013
shl v2364 1
sub 1 v2362
sub 1 v2366
add v2365 v2367
mul v2224 v2159
mul v2225 v1728
add v2369 v2370
mul v2250 v2347
add v2371 v2372
mul v2165 v2369
xor v1735 v2228
mul v2375 v2370
add v2374 v2376
xor v2353 v2252
mul v2378 v2372
add v2377 v2379
sub v2373 v2380
sub v2381 v2380
sub v2380 v2381
add v2382 v2383
div v2384 v2013
shl v2385 1
sub 1 v2383
sub 1 v2387
add v2386 v2388
sub 1 v2250
add v2384 0
add v2363 v2391
add v2340 v2392
add v2317 v2393
add v2294 v2394
add v2271 v2395
add v2385 0
add v2364 v2397
add v2341 v2398
add v2318 v2399
add v2295 v2400
add v2272 v2401
mul v2013 v2402
sub v2396 v2403
add v2390 v2404
shr v2276 1
sub 1 v2406
add v2405 v2407
add v2223 v2408
mul v2406 v2406
mul v2406 v2220
xor v2276 v2065
land v2412 1
xor v2413 1
mul v2406 v2230
shr v2299 1
mul v2220 v2416
add v2415 v2417
xor v2276 v2088
land v2419 1
mul v2420 v2415
xor v2065 v2299
land v2422 1
xor v2423 1
mul v2424 v2417
add v2421 v2425
sub v2418 v2426
sub v2427 v2426
sub v2426 v2427
add v2428 v2429
div v2430 1
shl v2431 1
sub 1 v2429
sub 1 v2433
add v2432 v2434
shr v2435 1
land v2435 1
xor v2437 1
mul v2410 v2254
shr v2322 1
mul v2411 v2440
add v2439 v2441
mul v2436 v2416
add v2442 v2443
mul v2260 v2439
land v2322 1
xor v2446 v2414
mul v2447 v2441
add v2445 v2448
land v2299 1
xor v2450 v2438
mul v2451 v2443
add v2449 v2452
sub v2444 v2453
sub v2454 v2453
sub v2453 v2454
add v2455 v2456
div v2457 v2224
shl v2458 1
sub 1 v2456
sub 1 v2460
add v2459 v2461
mul v2410 v2278
shr v2345 1
mul v2411 v2464
add v2463 v2465
mul v2436 v2440
add v2466 v2467
mul v2284 v2463
land v2345 1
xor v2470 v2414
mul v2471 v2465
add v2469 v2472
xor v2446 v2438
mul v2474 v2467
add v2473 v2475
sub v2468 v2476
sub v2477 v2476
sub v2476 v2477
add v2478 v2479
div v2480 v2224
shl v2481 1
sub 1 v2479
sub 1 v2483
add v2482 v2484
mul v2410 v2301
shr v2368 1
mul v2411 v2487
add v2486 v2488
mul v2436 v2464
add v2489 v2490
mul v2307 v2486
land v2368 1
xor v2493 v2414
mul v2494 v2488
add v2492 v2495
xor v2470 v2438
mul v2497 v2490
add v2496 v2498
sub v2491 v2499
sub v2500 v2499
sub v2499 v2500
add v2501 v2502
div v2503 v2224
shl v2504 1
sub 1 v2502
sub 1 v2506
add v2505 v2507
mul v2410 v2324
shr v2389 1
mul v2411 v2510
add v2509 v2511
mul v2436 v2487
add v2512 v2513
mul v2330 v2509
land v2389 1
xor v2516 v2414
mul v2517 v2511
add v2515 v2518
xor v2493 v2438
mul v2520 v2513
add v2519 v2521
sub v2514 v2522
sub v2523 v2522
sub v2522 v2523
add v2524 v2525
div v2526 v2224
shl v2527 1
sub 1 v2525
sub 1 v2529
add v2528 v2530
mul v2410 v2347
mul v2411 v1728
add v2532 v2533
mul v2436 v2510
add v2534 v2535
mul v2353 v2532
xor v1735 v2414
mul v2538 v2533
add v2537 v2539
xor v2516 v2438
mul v2541 v2535
add v2540 v2542
sub v2536 v2543
sub v2544 v2543
sub v2543 v2544
add v2545 v2546
div v2547 v2224
shl v2548 1
sub 1 v2546
sub 1 v2550
add v2549 v2551
sub 1 v2436
add v2547 0
add v2526 v2554
add v2503 v2555
add v2480 v2556
add v2457 v2557
add v2548 0
add v2527 v2559
add v2504 v2560
add v2481 v2561
add v2458 v2562
mul v2224 v2563
sub v2558 v2564
add v2553 v2565
shr v2462 1
sub 1 v2567
add v2566 v2568
add v2409 v2569
mul v2567 v2567
mul v2567 v2406
xor v2462 v2276
land v2573 1
xor v2574 1
mul v2567 v2416
shr v2485 1
mul v2406 v2577
add v2576 v2578
xor v2462 v2299
land v2580 1
mul v2581 v2576
xor v2276 v2485
land v2583 1
xor v2584 1
mul v2585 v2578
add v2582 v2586
sub v2579 v2587
sub v2588 v2587
sub v2587 v2588
add v2589 v2590
div v2591 1
shl v2592 1
sub 1 v2590
sub 1 v2594
add v2593 v2595
shr v2596 1
land v2596 1
xor v2598 1
mul v2571 v2440
shr v2508 1
mul v2572 v2601
add v2600 v2602
mul v2597 v2577
add v2603 v2604
mul v2446 v2600
land v2508 1
xor v2607 v2575
mul v2608 v2602
add v2606 v2609
land v2485 1
xor v2611 v2599
mul v2612 v2604
add v2610 v2613
sub v2605 v2614
sub v2615 v2614
sub v2614 v2615
add v2616 v2617
div v2618 v2410
shl v2619 1
sub 1 v2617
sub 1 v2621
add v2620 v2622
mul v2571 v2464
shr v2531 1
mul v2572 v2625
add v2624 v2626
mul v2597 v2601
add v2627 v2628
mul v2470 v2624
land v2531 1
xor v2631 v2575
mul v2632 v2626
add v2630 v2633
xor v2607 v2599
mul v2635 v2628
add v2634 v2636
sub v2629 v2637
sub v2638 v2637
sub v2637 v2638
add v2639 v2640
div v2641 v2410
shl v2642 1
sub 1 v2640
sub 1 v2644
add v2643 v2645
mul v2571 v2487
shr v2552 1
mul v2572 v2648
add v2647 v2649
mul v2597 v2625
add v2650 v2651
mul v2493 v2647
land v2552 1
xor v2654 v2575
mul v2655 v2649
add v2653 v2656
xor v2631 v2599
mul v2658 v2651
add v2657 v2659
sub v2652 v2660
sub v2661 v2660
sub v2660 v2661
add v2662 v2663
div v2664 v2410
shl v2665 1
sub 1 v2663
sub 1 v2667
add v2666 v2668
mul v2571 v2510
mul v2572 v1728
add v2670 v2671
mul v2597 v2648
add v2672 v2673
mul v2516 v2670
xor v1735 v2575
mul v2676 v2671
add v2675 v2677
xor v2654 v2599
mul v2679 v2673
add v2678 v2680
sub v2674 v2681
sub v2682 v2681
sub v2681 v2682
add v2683 v2684
div v2685 v2410
shl v2686 1
sub 1 v2684
sub 1 v2688
add v2687 v2689
sub 1 v2597
add v2685 0
add v2664 v2692
add v2641 v2693
add v2618 v2694
add v2686 0
add v2665 v2696
add v2642 v2697
add v2619 v2698
mul v2410 v2699
sub v2695 v2700
add v2691 v2701
shr v2623 1
sub 1 v2703
add v2702 v2704
add v2570 v2705
mul v2703 v2703
mul v2703 v2567
xor v2623 v2462
land v2709 1
xor v2710 1
mul v2703 v2577
shr v2646 1
mul v2567 v2713
add v2712 v2714
xor v2623 v2485
land v2716 1
mul v2717 v2712
xor v2462 v2646
land v2719 1
xor v2720 1
mul v2721 v2714
add v2718 v2722
sub v2715 v2723
sub v2724 v2723
sub v2723 v2724
add v2725 v2726
div v2727 1
shl v2728 1
sub 1 v2726
sub 1 v2730
add v2729 v2731
shr v2732 1
land v2732 1
xor v2734 1
mul v2707 v2601
shr v2669 1
mul v2708 v2737
add v2736 v2738
mul v2733 v2713
add v2739 v2740
mul v2607 v2736
land v2669 1
xor v2743 v2711
mul v2744 v2738
add v2742 v2745
land v2646 1
xor v2747 v2735
mul v2748 v2740
add v2746 v2749
sub v2741 v2750
sub v2751 v2750
sub v2750 v2751
add v2752 v2753
div v2754 v2571
shl v2755 1
sub 1 v2753
sub 1 v2757
add v2756 v2758
mul v2707 v2625
shr v2690 1
mul v2708 v2761
add v2760 v2762
mul v2733 v2737
add v2763 v2764
mul v2631 v2760
land v2690 1
xor v2767 v2711
mul v2768 v2762
add v2766 v2769
xor v2743 v2735
mul v2771 v2764
add v2770 v2772
sub v2765 v2773
sub v2774 v2773
sub v2773 v2774
add v2775 v2776
div v2777 v2571
shl v2778 1
sub 1 v2776
sub 1 v2780
add v2779 v2781
mul v2707 v2648
mul v2708 v1728
add v2783 v2784
mul v2733 v2761
add v2785 v2786
mul v2654 v2783
xor v1735 v2711
mul v2789 v2784
add v2788 v2790
xor v2767 v2735
mul v2792 v2786
add v2791 v2793
sub v2787 v2794
sub v2795 v2794
sub v2794 v2795
add v2796 v2797
div v2798 v2571
shl v2799 1
sub 1 v2797
sub 1 v2801
add v2800 v2802
sub 1 v2733
add v2798 0
add v2777 v2805
add v2754 v2806
add v2799 0
add v2778 v2808
add v2755 v2809
mul v2571 v2810
sub v2807 v2811
add v2804 v2812
shr v2759 1
sub 1 v2814
add v2813 v2815
add v2706 v2816
mul v2814 v2814
mul v2814 v2703
xor v2759 v2623
land v2820 1
xor v2821 1
mul v2814 v2713
shr v2782 1
mul v2703 v2824
add v2823 v2825
xor v2759 v2646
land v2827 1
mul v2828 v2823
xor v2623 v2782
land v2830 1
xor v2831 1
mul v2832 v2825
add v2829 v2833
sub v2826 v2834
sub v2835 v2834
sub v2834 v2835
add v2836 v2837
div v2838 1
shl v2839 1
sub 1 v2837
sub 1 v2841
add v2840 v2842
shr v2843 1
land v2843 1
xor v2845 1
mul v2818 v2737
shr v2803 1
mul v2819 v2848
add v2847 v2849
mul v2844 v2824
add v2850 v2851
mul v2743 v2847
land v2803 1
xor v2854 v2822
mul v2855 v2849
add v2853 v2856
land v2782 1
xor v2858 v2846
mul v2859 v2851
add v2857 v2860
sub v2852 v2861
sub v2862 v2861
sub v2861 v2862
add v2863 v2864
div v2865 v2707
shl v2866 1
sub 1 v2864
sub 1 v2868
add v2867 v2869
mul v2818 v2761
mul v2819 v1728
add v2871 v2872
mul v2844 v2848
add v2873 v2874
mul v2767 v2871
xor v1735 v2822
mul v2877 v2872
add v2876 v2878
xor v2854 v2846
mul v2880 v2874
add v2879 v2881
sub v2875 v2882
sub v2883 v2882
sub v2882 v2883
add v2884 v2885
div v2886 v2707
shl v2887 1
sub 1 v2885
sub 1 v2889
add v2888 v2890
sub 1 v2844
add v2886 0
add v2865 v2893
add v2887 0
add v2866 v2895
mul v2707 v2896
sub v2894 v2897
add v2892 v2898
shr v2870 1
sub 1 v2900
add v2899 v2901
add v2817 v2902
mul v2900 v2900
mul v2900 v2814
xor v2870 v2759
land v2906 1
xor v2907 1
mul v2900 v2824
shr v2891 1
mul v2814 v2910
add v2909 v2911
xor v2870 v2782
land v2913 1
mul v2914 v2909
xor v2759 v2891
land v2916 1
xor v2917 1
mul v2918 v2911
add v2915 v2919
sub v2912 v2920
sub v2921 v2920
sub v2920 v2921
add v2922 v2923
div v2924 1
shl v2925 1
sub 1 v2923
sub 1 v2927
add v2926 v2928
shr v2929 1
land v2929 1
xor v2931 1
mul v2904 v2848
mul v2905 v1728
add v2933 v2934
mul v2930 v2910
add v2935 v2936
mul v2854 v2933
xor v1735 v2908
mul v2939 v2934
add v2938 v2940
land v2891 1
xor v2942 v2932
mul v2943 v2936
add v2941 v2944
sub v2937 v2945
sub v2946 v2945
sub v2945 v2946
add v2947 v2948
div v2949 v2818
shl v2950 1
sub 1 v2948
sub 1 v2952
add v2951 v2953
sub 1 v2930
add v2949 0
add v2950 0
mul v2818 v2957
sub v2956 v2958
add v2955 v2959
shr v2954 1
sub 1 v2961
add v2960 v2962
add v2903 v2963
app x25 v2954 v2964" [f0, f1, f2, f3, f4, f5, f6, f7, f8, f9, f10, f11, f12, f13, f14, f15, f16, f17, f18, f19, f20, f21, f22, f23, f24, (@Prod.mk Nat Nat)]

/-- Statement of `pkDag205_eq`. -/
def PkDag205Eq : Prop := ∀ f0 f1 f2 f3 f4 f5 f6 f7 f8 f9 f10 f11 f12 f13 f14 f15 f16 f17 f18 f19 f20 f21 f22 f23 f24 : Nat, pkDag205 f0 f1 f2 f3 f4 f5 f6 f7 f8 f9 f10 f11 f12 f13 f14 f15 f16 f17 f18 f19 f20 f21 f22 f23 f24 = pkDagC205 f0 f1 f2 f3 f4 f5 f6 f7 f8 f9 f10 f11 f12 f13 f14 f15 f16 f17 f18 f19 f20 f21 f22 f23 f24 kO205_0 kH205_0 kT205_0 kM205_0 kQ205_0 kO205_1 kH205_1 kT205_1 kM205_1 kQ205_1 kO205_2 kH205_2 kT205_2 kM205_2 kQ205_2 84162174424773976115855838126082058648805436845170781751972494449099714468753293153818664580441415219631727501698851483408310916002940861810045036330430093599283578738055113571066620126149163476340692027772502017 84162174424773976115855838126082058648805436845170781751972494449099714468753293153818664580441415219631727501698851483408310916002940861810045036330430093599283578738055113571066620126149163476340692027772502040 50760 48645 46530 44415 42300 40185 38070 35955 33840 31725 29610 27495 25380 23265 21150 19035 16920 14805 12690 10575 8460 6345 4230 2115 1851567837345027474548828438773805290273719610593757198543394877880193718312572449384010620769711134831898005037374732634982840152064698959820990799269462059184238732237212498563465642775281596479495224610995044352 1767405662920253498432972600647723231624914173748586416791422383431094003843819156230191956189269719612266277535675881151574529236061758098010945762939031965584955153499157384992399022649132433003154532583222542336 1683243488495479522317116762521641172976108736903415635039449888981994289375065863076373291608828304392634550033977029668166218320058817236200900726608601871985671574761102271421332402522983269526813840555450040320 1599081314070705546201260924395559114327303300058244853287477394532894574906312569922554627028386889173002822532278178184757907404055876374390855690278171778386387996023047157850265782396834106050473148527677538304 1514919139645931570085405086269477055678497863213074071535504900083794860437559276768735962447945473953371095030579326701349596488052935512580810653947741684787104417284992044279199162270684942574132456499905036288 1430756965221157593969549248143394997029692426367903289783532405634695145968805983614917297867504058733739367528880475217941285572049994650770765617617311591187820838546936930708132542144535779097791764472132534272 1346594790796383617853693410017312938380886989522732508031559911185595431500052690461098633287062643514107640027181623734532974656047053788960720581286881497588537259808881817137065922018386615621451072444360032256 1262432616371609641737837571891230879732081552677561726279587416736495717031299397307279968706621228294475912525482772251124663740044112927150675544956451403989253681070826703565999301892237452145110380416587530240 1178270441946835665621981733765148821083276115832390944527614922287396002562546104153461304126179813074844185023783920767716352824041172065340630508626021310389970102332771589994932681766088288668769688388815028224 1094108267522061689506125895639066762434470678987220162775642427838296288093792810999642639545738397855212457522085069284308041908038231203530585472295591216790686523594716476423866061639939125192428996361042526208 1009946093097287713390270057512984703785665242142049381023669933389196573625039517845823974965296982635580730020386217800899730992035290341720540435965161123191402944856661362852799441513789961716088304333270024192 925783918672513737274414219386902645136859805296878599271697438940096859156286224692005310384855567415949002518687366317491420076032349479910495399634731029592119366118606249281732821387640798239747612305497522176 841621744247739761158558381260820586488054368451707817519724944490997144687532931538186645804414152196317275016988514834083109160029408618100450363304300935992835787380551135710666201261491634763406920277725020160 757459569822965785042702543134738527839248931606537035767752450041897430218779638384367981223972736976685547515289663350674798244026467756290405326973870842393552208642496022139599581135342471287066228249952518144 673297395398191808926846705008656469190443494761366254015779955592797715750026345230549316643531321757053820013590811867266487328023526894480360290643440748794268629904440908568532961009193307810725536222180016128 589135220973417832810990866882574410541638057916195472263807461143698001281273052076730652063089906537422092511891960383858176412020586032670315254313010655194985051166385794997466340883044144334384844194407514112 504973046548643856695135028756492351892832621071024690511834966694598286812519758922911987482648491317790365010193108900449865496017645170860270217982580561595701472428330681426399720756894980858044152166635012096 420810872123869880579279190630410293244027184225853908759862472245498572343766465769093322902207076098158637508494257417041554580014704309050225181652150467996417893690275567855333100630745817381703460138862510080 336648697699095904463423352504328234595221747380683127007889977796398857875013172615274658321765660878526910006795405933633243664011763447240180145321720374397134314952220454284266480504596653905362768111090008064 252486523274321928347567514378246175946416310535512345255917483347299143406259879461455993741324245658895182505096554450224932748008822585430135108991290280797850736214165340713199860378447490429022076083317506048 168324348849547952231711676252164117297610873690341563503944988898199428937506586307637329160882830439263455003397702966816621832005881723620090072660860187198567157476110227142133240252298326952681384055545004032 84162174424773976115855838126082058648805436845170781751972494449099714468753293153818664580441415219631727501698851483408310916002940861810045036330430093599283578738055113571066620126149163476340692027772502016 704 (Nat.sub kT205_1 kT205_0) 69819 65712 61605 57498 53391 49284 45177 41070 36963 32856 28749 24642 20535 16428 12321 8214 4107 1368 (Nat.sub kT205_2 kT205_1) 80067 73908 67749 61590 55431 49272 43113 36954 30795 24636 18477 12318 6159 2052 86226 92385

open Lean Elab Term Command Meta in
/- `pkDag205_eq : PkDag205Eq` by `rfl`: the two graphs differ only in closed constants. -/
run_cmd liftTermElabM do
  let ty ← instantiateMVars (← elabTerm (← `(PkDag205Eq)) none)
  let pf ← instantiateMVars (← elabTerm (← `(fun (f0 f1 f2 f3 f4 f5 f6 f7 f8 f9 f10 f11 f12 f13 f14 f15 f16 f17 f18 f19 f20 f21 f22 f23 f24 : Nat) =>
    @rfl (Nat × Nat) (pkDag205 f0 f1 f2 f3 f4 f5 f6 f7 f8 f9 f10 f11 f12 f13 f14 f15 f16 f17 f18 f19 f20 f21 f22 f23 f24))) none)
  addDecl (.thmDecl { name := `Submission.pkDag205_eq, levelParams := [], type := ty, value := pf })

/-- The lane-constant act list of band `205`. -/
def acts205 : List PAct := [.step 2115 704 22 kT205_0 kM205_0 (Nat.shiftRight kO205_0 4230) (Nat.shiftRight kH205_0 4230) kQ205_0 704 2115 48645 46530 44415 true true,
    .step 2115 704 21 kT205_0 kM205_0 (Nat.shiftRight kO205_0 6345) (Nat.shiftRight kH205_0 6345) kQ205_0 704 2115 46530 44415 42300 false true,
    .step 2115 704 20 kT205_0 kM205_0 (Nat.shiftRight kO205_0 8460) (Nat.shiftRight kH205_0 8460) kQ205_0 704 2115 44415 42300 40185 false true,
    .step 2115 704 19 kT205_0 kM205_0 (Nat.shiftRight kO205_0 10575) (Nat.shiftRight kH205_0 10575) kQ205_0 704 2115 42300 40185 38070 false true,
    .step 2115 704 18 kT205_0 kM205_0 (Nat.shiftRight kO205_0 12690) (Nat.shiftRight kH205_0 12690) kQ205_0 704 2115 40185 38070 35955 false true,
    .step 2115 704 17 kT205_0 kM205_0 (Nat.shiftRight kO205_0 14805) (Nat.shiftRight kH205_0 14805) kQ205_0 704 2115 38070 35955 33840 false true,
    .step 2115 704 16 kT205_0 kM205_0 (Nat.shiftRight kO205_0 16920) (Nat.shiftRight kH205_0 16920) kQ205_0 704 2115 35955 33840 31725 false true,
    .repack 2115 704 4107 1368 17 kM205_0 (Nat.shiftRight kO205_0 14805) (Nat.shiftRight kO205_0 16920) [35955, 33840, 31725, 29610, 27495, 25380, 23265, 21150, 19035, 16920, 14805, 12690, 10575, 8460, 6345, 4230, 2115, 0] [33840, 31725, 29610, 27495, 25380, 23265, 21150, 19035, 16920, 14805, 12690, 10575, 8460, 6345, 4230, 2115, 0] [69819, 65712, 61605, 57498, 53391, 49284, 45177, 41070, 36963, 32856, 28749, 24642, 20535, 16428, 12321, 8214, 4107] [65712, 61605, 57498, 53391, 49284, 45177, 41070, 36963, 32856, 28749, 24642, 20535, 16428, 12321, 8214, 4107] (Nat.shiftRight kO205_1 28749) (Nat.shiftRight kO205_1 32856) (Nat.sub kT205_1 kT205_0),
    .step 4107 1368 15 kT205_1 kM205_1 (Nat.shiftRight kO205_1 36963) (Nat.shiftRight kH205_1 36963) kQ205_1 1368 4107 65712 61605 57498 false true,
    .step 4107 1368 14 kT205_1 kM205_1 (Nat.shiftRight kO205_1 41070) (Nat.shiftRight kH205_1 41070) kQ205_1 1368 4107 61605 57498 53391 false true,
    .step 4107 1368 13 kT205_1 kM205_1 (Nat.shiftRight kO205_1 45177) (Nat.shiftRight kH205_1 45177) kQ205_1 1368 4107 57498 53391 49284 false true,
    .step 4107 1368 12 kT205_1 kM205_1 (Nat.shiftRight kO205_1 49284) (Nat.shiftRight kH205_1 49284) kQ205_1 1368 4107 53391 49284 45177 false true,
    .repack 4107 1368 6159 2052 13 kM205_1 (Nat.shiftRight kO205_1 45177) (Nat.shiftRight kO205_1 49284) [53391, 49284, 45177, 41070, 36963, 32856, 28749, 24642, 20535, 16428, 12321, 8214, 4107, 0] [49284, 45177, 41070, 36963, 32856, 28749, 24642, 20535, 16428, 12321, 8214, 4107, 0] [80067, 73908, 67749, 61590, 55431, 49272, 43113, 36954, 30795, 24636, 18477, 12318, 6159] [73908, 67749, 61590, 55431, 49272, 43113, 36954, 30795, 24636, 18477, 12318, 6159] (Nat.shiftRight kO205_2 67749) (Nat.shiftRight kO205_2 73908) (Nat.sub kT205_2 kT205_1),
    .step 6159 2052 11 kT205_2 kM205_2 (Nat.shiftRight kO205_2 80067) (Nat.shiftRight kH205_2 80067) kQ205_2 2052 6159 73908 67749 61590 false true,
    .step 6159 2052 10 kT205_2 kM205_2 (Nat.shiftRight kO205_2 86226) (Nat.shiftRight kH205_2 86226) kQ205_2 2052 6159 67749 61590 55431 false true,
    .step 6159 2052 9 kT205_2 kM205_2 (Nat.shiftRight kO205_2 92385) (Nat.shiftRight kH205_2 92385) kQ205_2 2052 6159 61590 55431 49272 false true]

/-- The packed input of band `205`. -/
def init205 (xs : List Nat) : PSt := pinit kT205_0 84162174424773976115855838126082058648805436845170781751972494449099714468753293153818664580441415219631727501698851483408310916002940861810045036330430093599283578738055113571066620126149163476340692027772502017 84162174424773976115855838126082058648805436845170781751972494449099714468753293153818664580441415219631727501698851483408310916002940861810045036330430093599283578738055113571066620126149163476340692027772502040 [50760, 48645, 46530, 44415, 42300, 40185, 38070, 35955, 33840, 31725, 29610, 27495, 25380, 23265, 21150, 19035, 16920, 14805, 12690, 10575, 8460, 6345, 4230, 2115] [48645, 46530, 44415, 42300, 40185, 38070, 35955, 33840, 31725, 29610, 27495, 25380, 23265, 21150, 19035, 16920, 14805, 12690, 10575, 8460, 6345, 4230, 2115] [23, 22, 21, 20, 19, 18, 17, 16, 15, 14, 13, 12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2] [1851567837345027474548828438773805290273719610593757198543394877880193718312572449384010620769711134831898005037374732634982840152064698959820990799269462059184238732237212498563465642775281596479495224610995044352, 1767405662920253498432972600647723231624914173748586416791422383431094003843819156230191956189269719612266277535675881151574529236061758098010945762939031965584955153499157384992399022649132433003154532583222542336, 1683243488495479522317116762521641172976108736903415635039449888981994289375065863076373291608828304392634550033977029668166218320058817236200900726608601871985671574761102271421332402522983269526813840555450040320, 1599081314070705546201260924395559114327303300058244853287477394532894574906312569922554627028386889173002822532278178184757907404055876374390855690278171778386387996023047157850265782396834106050473148527677538304, 1514919139645931570085405086269477055678497863213074071535504900083794860437559276768735962447945473953371095030579326701349596488052935512580810653947741684787104417284992044279199162270684942574132456499905036288, 1430756965221157593969549248143394997029692426367903289783532405634695145968805983614917297867504058733739367528880475217941285572049994650770765617617311591187820838546936930708132542144535779097791764472132534272, 1346594790796383617853693410017312938380886989522732508031559911185595431500052690461098633287062643514107640027181623734532974656047053788960720581286881497588537259808881817137065922018386615621451072444360032256, 1262432616371609641737837571891230879732081552677561726279587416736495717031299397307279968706621228294475912525482772251124663740044112927150675544956451403989253681070826703565999301892237452145110380416587530240, 1178270441946835665621981733765148821083276115832390944527614922287396002562546104153461304126179813074844185023783920767716352824041172065340630508626021310389970102332771589994932681766088288668769688388815028224, 1094108267522061689506125895639066762434470678987220162775642427838296288093792810999642639545738397855212457522085069284308041908038231203530585472295591216790686523594716476423866061639939125192428996361042526208, 1009946093097287713390270057512984703785665242142049381023669933389196573625039517845823974965296982635580730020386217800899730992035290341720540435965161123191402944856661362852799441513789961716088304333270024192, 925783918672513737274414219386902645136859805296878599271697438940096859156286224692005310384855567415949002518687366317491420076032349479910495399634731029592119366118606249281732821387640798239747612305497522176, 841621744247739761158558381260820586488054368451707817519724944490997144687532931538186645804414152196317275016988514834083109160029408618100450363304300935992835787380551135710666201261491634763406920277725020160, 757459569822965785042702543134738527839248931606537035767752450041897430218779638384367981223972736976685547515289663350674798244026467756290405326973870842393552208642496022139599581135342471287066228249952518144, 673297395398191808926846705008656469190443494761366254015779955592797715750026345230549316643531321757053820013590811867266487328023526894480360290643440748794268629904440908568532961009193307810725536222180016128, 589135220973417832810990866882574410541638057916195472263807461143698001281273052076730652063089906537422092511891960383858176412020586032670315254313010655194985051166385794997466340883044144334384844194407514112, 504973046548643856695135028756492351892832621071024690511834966694598286812519758922911987482648491317790365010193108900449865496017645170860270217982580561595701472428330681426399720756894980858044152166635012096, 420810872123869880579279190630410293244027184225853908759862472245498572343766465769093322902207076098158637508494257417041554580014704309050225181652150467996417893690275567855333100630745817381703460138862510080, 336648697699095904463423352504328234595221747380683127007889977796398857875013172615274658321765660878526910006795405933633243664011763447240180145321720374397134314952220454284266480504596653905362768111090008064, 252486523274321928347567514378246175946416310535512345255917483347299143406259879461455993741324245658895182505096554450224932748008822585430135108991290280797850736214165340713199860378447490429022076083317506048, 168324348849547952231711676252164117297610873690341563503944988898199428937506586307637329160882830439263455003397702966816621832005881723620090072660860187198567157476110227142133240252298326952681384055545004032, 84162174424773976115855838126082058648805436845170781751972494449099714468753293153818664580441415219631727501698851483408310916002940861810045036330430093599283578738055113571066620126149163476340692027772502016] (Nat.shiftRight kO205_0 0) (Nat.shiftRight kO205_0 2115) xs

/-- The structured run of band `205`. -/
def pkRun205 (xs : List Nat) : Nat × Nat :=
  let s := prun acts205 (init205 xs)
  run 9 (unpackT kT205_2 kM205_2 (Nat.shiftRight kO205_2 86226) [61590, 55431, 49272, 43113, 36954, 30795, 24636, 18477, 12318, 6159, 0] s.fv s.fs)
    (unpackT kT205_2 kM205_2 (Nat.shiftRight kO205_2 92385) [55431, 49272, 43113, 36954, 30795, 24636, 18477, 12318, 6159, 0] s.gv s.gs) s.bad

/-- Statement of `pkDag205_struct`. -/
def PkDag205Struct : Prop := ∀ f0 f1 f2 f3 f4 f5 f6 f7 f8 f9 f10 f11 f12 f13 f14 f15 f16 f17 f18 f19 f20 f21 f22 f23 f24 : Nat, pkDag205 f0 f1 f2 f3 f4 f5 f6 f7 f8 f9 f10 f11 f12 f13 f14 f15 f16 f17 f18 f19 f20 f21 f22 f23 f24 = pkRun205 [f1, f2, f3, f4, f5, f6, f7, f8, f9, f10, f11, f12, f13, f14, f15, f16, f17, f18, f19, f20, f21, f22, f23, f24]

open Lean Elab Term Command Meta in
/- `pkDag205_struct`: through the variable graph (`pkDag205_eq`, `pkDagC205_eq`), then `rfl`
between two structured terms. Checked by the kernel. -/
run_cmd liftTermElabM do
  let ty ← instantiateMVars (← elabTerm (← `(PkDag205Struct)) none)
  let pf ← instantiateMVars (← elabTerm (← `(fun (f0 f1 f2 f3 f4 f5 f6 f7 f8 f9 f10 f11 f12 f13 f14 f15 f16 f17 f18 f19 f20 f21 f22 f23 f24 : Nat) =>
    Eq.trans (pkDag205_eq f0 f1 f2 f3 f4 f5 f6 f7 f8 f9 f10 f11 f12 f13 f14 f15 f16 f17 f18 f19 f20 f21 f22 f23 f24) (Eq.trans (pkDagC205_eq f0 f1 f2 f3 f4 f5 f6 f7 f8 f9 f10 f11 f12 f13 f14 f15 f16 f17 f18 f19 f20 f21 f22 f23 f24 kO205_0 kH205_0 kT205_0 kM205_0 kQ205_0 kO205_1 kH205_1 kT205_1 kM205_1 kQ205_1 kO205_2 kH205_2 kT205_2 kM205_2 kQ205_2 84162174424773976115855838126082058648805436845170781751972494449099714468753293153818664580441415219631727501698851483408310916002940861810045036330430093599283578738055113571066620126149163476340692027772502017 84162174424773976115855838126082058648805436845170781751972494449099714468753293153818664580441415219631727501698851483408310916002940861810045036330430093599283578738055113571066620126149163476340692027772502040 50760 48645 46530 44415 42300 40185 38070 35955 33840 31725 29610 27495 25380 23265 21150 19035 16920 14805 12690 10575 8460 6345 4230 2115 1851567837345027474548828438773805290273719610593757198543394877880193718312572449384010620769711134831898005037374732634982840152064698959820990799269462059184238732237212498563465642775281596479495224610995044352 1767405662920253498432972600647723231624914173748586416791422383431094003843819156230191956189269719612266277535675881151574529236061758098010945762939031965584955153499157384992399022649132433003154532583222542336 1683243488495479522317116762521641172976108736903415635039449888981994289375065863076373291608828304392634550033977029668166218320058817236200900726608601871985671574761102271421332402522983269526813840555450040320 1599081314070705546201260924395559114327303300058244853287477394532894574906312569922554627028386889173002822532278178184757907404055876374390855690278171778386387996023047157850265782396834106050473148527677538304 1514919139645931570085405086269477055678497863213074071535504900083794860437559276768735962447945473953371095030579326701349596488052935512580810653947741684787104417284992044279199162270684942574132456499905036288 1430756965221157593969549248143394997029692426367903289783532405634695145968805983614917297867504058733739367528880475217941285572049994650770765617617311591187820838546936930708132542144535779097791764472132534272 1346594790796383617853693410017312938380886989522732508031559911185595431500052690461098633287062643514107640027181623734532974656047053788960720581286881497588537259808881817137065922018386615621451072444360032256 1262432616371609641737837571891230879732081552677561726279587416736495717031299397307279968706621228294475912525482772251124663740044112927150675544956451403989253681070826703565999301892237452145110380416587530240 1178270441946835665621981733765148821083276115832390944527614922287396002562546104153461304126179813074844185023783920767716352824041172065340630508626021310389970102332771589994932681766088288668769688388815028224 1094108267522061689506125895639066762434470678987220162775642427838296288093792810999642639545738397855212457522085069284308041908038231203530585472295591216790686523594716476423866061639939125192428996361042526208 1009946093097287713390270057512984703785665242142049381023669933389196573625039517845823974965296982635580730020386217800899730992035290341720540435965161123191402944856661362852799441513789961716088304333270024192 925783918672513737274414219386902645136859805296878599271697438940096859156286224692005310384855567415949002518687366317491420076032349479910495399634731029592119366118606249281732821387640798239747612305497522176 841621744247739761158558381260820586488054368451707817519724944490997144687532931538186645804414152196317275016988514834083109160029408618100450363304300935992835787380551135710666201261491634763406920277725020160 757459569822965785042702543134738527839248931606537035767752450041897430218779638384367981223972736976685547515289663350674798244026467756290405326973870842393552208642496022139599581135342471287066228249952518144 673297395398191808926846705008656469190443494761366254015779955592797715750026345230549316643531321757053820013590811867266487328023526894480360290643440748794268629904440908568532961009193307810725536222180016128 589135220973417832810990866882574410541638057916195472263807461143698001281273052076730652063089906537422092511891960383858176412020586032670315254313010655194985051166385794997466340883044144334384844194407514112 504973046548643856695135028756492351892832621071024690511834966694598286812519758922911987482648491317790365010193108900449865496017645170860270217982580561595701472428330681426399720756894980858044152166635012096 420810872123869880579279190630410293244027184225853908759862472245498572343766465769093322902207076098158637508494257417041554580014704309050225181652150467996417893690275567855333100630745817381703460138862510080 336648697699095904463423352504328234595221747380683127007889977796398857875013172615274658321765660878526910006795405933633243664011763447240180145321720374397134314952220454284266480504596653905362768111090008064 252486523274321928347567514378246175946416310535512345255917483347299143406259879461455993741324245658895182505096554450224932748008822585430135108991290280797850736214165340713199860378447490429022076083317506048 168324348849547952231711676252164117297610873690341563503944988898199428937506586307637329160882830439263455003397702966816621832005881723620090072660860187198567157476110227142133240252298326952681384055545004032 84162174424773976115855838126082058648805436845170781751972494449099714468753293153818664580441415219631727501698851483408310916002940861810045036330430093599283578738055113571066620126149163476340692027772502016 704 (Nat.sub kT205_1 kT205_0) 69819 65712 61605 57498 53391 49284 45177 41070 36963 32856 28749 24642 20535 16428 12321 8214 4107 1368 (Nat.sub kT205_2 kT205_1) 80067 73908 67749 61590 55431 49272 43113 36954 30795 24636 18477 12318 6159 2052 86226 92385) (@rfl (Nat × Nat) (pkRun205 [f1, f2, f3, f4, f5, f6, f7, f8, f9, f10, f11, f12, f13, f14, f15, f16, f17, f18, f19, f20, f21, f22, f23, f24]))))) none)
  addDecl (.thmDecl { name := `Submission.pkDag205_struct, levelParams := [], type := ty, value := pf })



end Submission

/-! # v9: the low-part normal PRS for the D5 band (namespace `V9`)

Determinants and the subresultant chain (`chain_val`, `chain_exact`), the spec's PRS on chain
functions (`normalResultant_chain`), size certificates (`sres_lt`), the low-part step and run
(`lstep_spec`, `lrunR_spec`, `lowRun_spec`) and the shared graph `lowDag` (`lowDag_eq`). -/

/-!
# Congruences and two's-complement residues

`MEq n a b` is `n ∣ a − b` (core Lean has no `Int.ModEq`). `res q x` is the residue of `x` mod
`2^q` as a natural number; for `|x| < 2^(q-1)` the top bit is the sign and `x` is recovered
(`res_val`).
-/

namespace V9

def MEq (n a b : Int) : Prop := n ∣ a - b

namespace MEq

theorem refl (n a : Int) : MEq n a a := ⟨0, by simp⟩

theorem symm {n a b : Int} (h : MEq n a b) : MEq n b a := by
  obtain ⟨k, hk⟩ := h; exact ⟨-k, by rw [Int.mul_neg, ← hk]; grind⟩

theorem trans {n a b c : Int} (h1 : MEq n a b) (h2 : MEq n b c) : MEq n a c := by
  obtain ⟨k, hk⟩ := h1; obtain ⟨l, hl⟩ := h2
  exact ⟨k + l, by rw [Int.mul_add, ← hk, ← hl]; grind⟩

theorem add {n a b c d : Int} (h1 : MEq n a b) (h2 : MEq n c d) : MEq n (a + c) (b + d) := by
  obtain ⟨k, hk⟩ := h1; obtain ⟨l, hl⟩ := h2
  exact ⟨k + l, by rw [Int.mul_add, ← hk, ← hl]; grind⟩

theorem sub {n a b c d : Int} (h1 : MEq n a b) (h2 : MEq n c d) : MEq n (a - c) (b - d) := by
  obtain ⟨k, hk⟩ := h1; obtain ⟨l, hl⟩ := h2
  exact ⟨k - l, by rw [Int.mul_sub, ← hk, ← hl]; grind⟩

theorem mul {n a b c d : Int} (h1 : MEq n a b) (h2 : MEq n c d) : MEq n (a * c) (b * d) := by
  obtain ⟨k, hk⟩ := h1; obtain ⟨l, hl⟩ := h2
  refine ⟨k * c + b * l, ?_⟩
  have e : a * c - b * d = (a - b) * c + b * (c - d) := by grind
  rw [e, hk, hl]; grind

theorem mul_left {n a b : Int} (c : Int) (h : MEq n a b) : MEq n (c * a) (c * b) := (refl n c).mul h

theorem of_dvd {m n a b : Int} (hmn : m ∣ n) (h : MEq n a b) : MEq m a b := Int.dvd_trans hmn h

theorem emod (n a : Int) : MEq n (a % n) a := ⟨-(a / n), by rw [Int.emod_def]; grind⟩

theorem add_mul (n a k : Int) : MEq n (a + n * k) a := ⟨k, by grind⟩

theorem zero_of_dvd {n a : Int} (h : n ∣ a) : MEq n a 0 := by
  obtain ⟨k, hk⟩ := h; exact ⟨k, by rw [Int.sub_zero, hk]⟩

theorem of_eq {n a b : Int} (h : a = b) : MEq n a b := by rw [h]; exact refl n b

theorem self (n : Int) : MEq n n 0 := ⟨1, by grind⟩

theorem nat_sub {M t : Nat} {e : Int} (ht : t ≤ M) (h : MEq M t e) : MEq M ((M - t : Nat) : Int) (-e) := by
  rw [Int.ofNat_sub ht]; obtain ⟨k, hk⟩ := h; exact ⟨1 - k, by grind⟩

theorem emod_eq {n a b : Int} (h : MEq n a b) : a % n = b % n :=
  Int.emod_eq_emod_iff_emod_sub_eq_zero.2 (Int.dvd_iff_emod_eq_zero.1 h)

end MEq

/-- Residue of `x` mod `2^q`. -/
def res (q : Nat) (x : Int) : Nat := (x % (2 ^ q : Int)).toNat

theorem two_pow_pos (q : Nat) : (0 : Int) < 2 ^ q := Int.pow_pos (by decide)

theorem cast_two_pow (q : Nat) : ((2 ^ q : Nat) : Int) = (2 : Int) ^ q := by rw [Int.natCast_pow]; rfl

theorem pow2_dvd {m n : Nat} (h : m ≤ n) : (2 : Int) ^ m ∣ 2 ^ n := by
  rw [← cast_two_pow, ← cast_two_pow]; exact Int.natCast_dvd_natCast.2 (Nat.pow_dvd_pow 2 h)

theorem res_cast (q : Nat) (x : Int) : ((res q x : Nat) : Int) = x % 2 ^ q :=
  Int.toNat_of_nonneg (Int.emod_nonneg _ (Int.ne_of_gt (two_pow_pos q)))

theorem res_lt (q : Nat) (x : Int) : res q x < 2 ^ q := by
  have h := Int.emod_lt_of_pos x (two_pow_pos q)
  have h2 := res_cast q x
  have : ((res q x : Nat) : Int) < ((2 ^ q : Nat) : Int) := by rw [h2, cast_two_pow]; exact h
  exact Int.ofNat_lt.1 this

theorem res_meq (q : Nat) (x : Int) : MEq (2 ^ q) (res q x) x := by
  rw [res_cast]; exact MEq.emod _ _

theorem pow_succ_two (q : Nat) : (2 : Int) ^ (q + 1) = 2 * 2 ^ q := by
  rw [Int.pow_succ, Int.mul_comm]

/-- The sign bit and the value of a residue of a small integer. -/
theorem res_val (q : Nat) (x : Int) (hx : x.natAbs < 2 ^ q) :
    res (q + 1) x >>> q = (if x < 0 then 1 else 0) ∧
    ((res (q + 1) x : Nat) : Int) - ((res (q + 1) x >>> q : Nat) : Int) * 2 ^ (q + 1) = x := by
  have hP : (0 : Int) < 2 ^ q := two_pow_pos q
  have hx' : -(2 ^ q : Int) < x ∧ x < 2 ^ q := by
    have : ((x.natAbs : Nat) : Int) < ((2 ^ q : Nat) : Int) := Int.ofNat_lt.2 hx
    rw [cast_two_pow] at this
    omega
  have hc := res_cast (q + 1) x
  rw [pow_succ_two] at hc
  rw [Nat.shiftRight_eq_div_pow]
  by_cases hneg : x < 0
  · have e : x % (2 * 2 ^ q) = x + 2 * 2 ^ q := by
      rw [show x = (x + 2 * 2 ^ q) + (2 * 2 ^ q) * (-1) by grind, Int.add_mul_emod_self_left]
      rw [Int.emod_eq_of_lt (by omega) (by omega)]; grind
    rw [e] at hc
    have hd : res (q + 1) x / 2 ^ q = 1 := by
      have : ((res (q + 1) x / 2 ^ q : Nat) : Int) = 1 := by
        rw [Int.natCast_ediv, hc, cast_two_pow]
        exact ((Int.ediv_emod_unique (r := x + 2 ^ q) (q := 1) hP).2 ⟨by omega, by omega, by omega⟩).1
      exact Int.ofNat_inj.1 this
    rw [hd, if_pos hneg]; refine ⟨rfl, ?_⟩
    rw [hc, pow_succ_two]; simp only [Int.natCast_one]; omega
  · have e : x % (2 * 2 ^ q) = x := Int.emod_eq_of_lt (by omega) (by omega)
    rw [e] at hc
    have hd : res (q + 1) x / 2 ^ q = 0 := by
      have : ((res (q + 1) x / 2 ^ q : Nat) : Int) = 0 := by
        rw [Int.natCast_ediv, hc, cast_two_pow]
        exact Int.ediv_eq_zero_of_lt (by omega) (by omega)
      exact Int.ofNat_inj.1 this
    rw [hd, if_neg hneg]; refine ⟨rfl, ?_⟩
    rw [hc]; simp only [Int.natCast_zero]; omega

/-- Equal residues of two small integers mean equal integers. -/
theorem res_zero (q : Nat) (x : Int) (hx : x.natAbs < 2 ^ q) (h : res (q + 1) x = 0) : x = 0 := by
  have := (res_val q x hx).2
  rw [h] at this; simpa using this.symm

end V9

/-!
# Determinants over `Int`, from scratch (core Lean only)

Matrices are functions `Nat → Nat → Int`; `det n M` uses rows and columns `< n`.
The determinant is defined by Laplace expansion along column 0.
-/

namespace V9

/-- The `i`-th row index of the minor that drops row `r`. -/
def skip (r i : Nat) : Nat := if i < r then i else i + 1

/-- Drop row `r` and column `0`. -/
def minor (M : Nat → Nat → Int) (r : Nat) : Nat → Nat → Int :=
  fun i j => M (skip r i) (j + 1)

def sumTo : Nat → (Nat → Int) → Int
  | 0, _ => 0
  | n + 1, f => sumTo n f + f n

def sgn (r : Nat) : Int := if r % 2 = 0 then 1 else -1

def det : Nat → (Nat → Nat → Int) → Int
  | 0, _ => 1
  | n + 1, M => sumTo (n + 1) (fun r => sgn r * M r 0 * det n (minor M r))

/-! ## Finite sums -/

theorem sumTo_congr : ∀ (n : Nat) (f g : Nat → Int), (∀ r, r < n → f r = g r) →
    sumTo n f = sumTo n g
  | 0, _, _, _ => rfl
  | n + 1, f, g, h => by
    simp only [sumTo]
    rw [sumTo_congr n f g (fun r hr => h r (by omega)), h n (by omega)]

theorem sumTo_add : ∀ (n : Nat) (f g : Nat → Int),
    sumTo n (fun r => f r + g r) = sumTo n f + sumTo n g
  | 0, _, _ => by simp [sumTo]
  | n + 1, f, g => by
    simp only [sumTo]; rw [sumTo_add n f g]; omega

theorem sumTo_mul : ∀ (n : Nat) (c : Int) (f : Nat → Int),
    sumTo n (fun r => c * f r) = c * sumTo n f
  | 0, _, _ => by simp [sumTo]
  | n + 1, c, f => by
    simp only [sumTo]; rw [sumTo_mul n c f, Int.mul_add]

theorem sumTo_zero : ∀ (n : Nat) (f : Nat → Int), (∀ r, r < n → f r = 0) → sumTo n f = 0
  | 0, _, _ => rfl
  | n + 1, f, h => by
    simp only [sumTo]; rw [sumTo_zero n f (fun r hr => h r (by omega)), h n (by omega)]; rfl

theorem sumTo_single : ∀ (n p : Nat) (f : Nat → Int), p < n →
    (∀ r, r < n → r ≠ p → f r = 0) → sumTo n f = f p
  | 0, _, _, hp, _ => absurd hp (Nat.not_lt_zero _)
  | n + 1, p, f, hp, h => by
    simp only [sumTo]
    by_cases hpn : p = n
    · subst hpn
      rw [sumTo_zero p f (fun r hr => h r (by omega) (by omega))]; omega
    · rw [sumTo_single n p f (by omega) (fun r hr hrp => h r (by omega) hrp),
        h n (by omega) (fun e => hpn e.symm)]; omega

theorem sumTo_pair : ∀ (n p q : Nat) (f : Nat → Int), p < n → q < n → p ≠ q →
    (∀ r, r < n → r ≠ p → r ≠ q → f r = 0) → sumTo n f = f p + f q
  | 0, _, _, _, hp, _, _, _ => absurd hp (Nat.not_lt_zero _)
  | n + 1, p, q, f, hp, hq, hpq, h => by
    simp only [sumTo]
    by_cases hpn : p = n
    · subst hpn
      rw [sumTo_single p q f (by omega) (fun r hr hrq => h r (by omega) (by omega) hrq)]; omega
    · by_cases hqn : q = n
      · subst hqn
        rw [sumTo_single q p f (by omega) (fun r hr hrp => h r (by omega) hrp (by omega))]
      · rw [sumTo_pair n p q f (by omega) (by omega) hpq
          (fun r hr h1 h2 => h r (by omega) h1 h2), h n (by omega) (fun e => hpn e.symm)
          (fun e => hqn e.symm)]; omega

/-! ## Signs and the skip map -/

theorem sgn_succ (r : Nat) : sgn (r + 1) = -sgn r := by
  unfold sgn; split <;> split <;> omega

theorem sgn_mul_self (r : Nat) : sgn r * sgn r = 1 := by
  unfold sgn; split <;> rfl

theorem skip_lt (r i n : Nat) (_hr : r < n + 1) (hi : i < n) : skip r i < n + 1 := by
  unfold skip; split <;> omega

theorem skip_ne (r i : Nat) : skip r i ≠ r := by
  unfold skip; split <;> omega

/-! ## Congruence -/

theorem det_congr : ∀ (n : Nat) (M M' : Nat → Nat → Int),
    (∀ i j, i < n → j < n → M i j = M' i j) → det n M = det n M'
  | 0, _, _, _ => rfl
  | n + 1, M, M', h => by
    simp only [det]
    apply sumTo_congr
    intro r hr
    rw [h r 0 hr (by omega), det_congr n (minor M r) (minor M' r) (fun i j hi hj => by
      simp only [minor]; exact h _ _ (skip_lt r i n hr hi) (by omega))]

/-- Expansion when column 0 has a single nonzero entry, in row `p`. -/
theorem det_single (n p : Nat) (M : Nat → Nat → Int) (hp : p < n + 1)
    (h : ∀ r, r < n + 1 → r ≠ p → M r 0 = 0) :
    det (n + 1) M = sgn p * M p 0 * det n (minor M p) := by
  simp only [det]
  exact sumTo_single (n + 1) p _ hp (fun r hr hrp => by rw [h r hr hrp]; simp)

/-! ## Row updates -/

def setRow (M : Nat → Nat → Int) (p : Nat) (v : Nat → Int) : Nat → Nat → Int :=
  fun i j => if i = p then v j else M i j

/-- Position of row `p` inside the minor that drops row `r ≠ p`. -/
def posIn (r p : Nat) : Nat := if p < r then p else p - 1

theorem skip_eq_iff (r p i : Nat) (hrp : r ≠ p) : skip r i = p ↔ i = posIn r p := by
  unfold skip posIn; split <;> split <;> omega

theorem minor_setRow_self (M : Nat → Nat → Int) (p : Nat) (v : Nat → Int) :
    minor (setRow M p v) p = minor M p := by
  funext i j; simp only [minor, setRow, if_neg (skip_ne p i)]

theorem minor_setRow_other (M : Nat → Nat → Int) (p r : Nat) (v : Nat → Int) (hrp : r ≠ p) :
    minor (setRow M p v) r = setRow (minor M r) (posIn r p) (fun j => v (j + 1)) := by
  funext i j
  simp only [minor, setRow]
  by_cases h : skip r i = p
  · rw [if_pos h, if_pos ((skip_eq_iff r p i hrp).1 h)]
  · rw [if_neg h, if_neg (fun e => h ((skip_eq_iff r p i hrp).2 e))]

theorem posIn_lt (r p n : Nat) (hrp : r ≠ p) (hp : p < n + 1) (hr : r < n + 1) :
    posIn r p < n := by
  unfold posIn; split <;> omega

theorem det_linear : ∀ (n : Nat) (M : Nat → Nat → Int) (p : Nat) (a b : Int) (u w : Nat → Int),
    p < n →
    det n (setRow M p (fun j => a * u j + b * w j)) =
      a * det n (setRow M p u) + b * det n (setRow M p w)
  | 0, _, _, _, _, _, _, hp => absurd hp (Nat.not_lt_zero _)
  | n + 1, M, p, a, b, u, w, hp => by
    simp only [det]
    rw [← sumTo_mul, ← sumTo_mul, ← sumTo_add]
    apply sumTo_congr
    intro r hr
    by_cases hrp : r = p
    · subst hrp
      simp only [minor_setRow_self, setRow]
      generalize det n (minor M r) = D
      grind
    · simp only [setRow, if_neg hrp]
      rw [minor_setRow_other M p r _ hrp, minor_setRow_other M p r _ hrp,
        minor_setRow_other M p r _ hrp]
      rw [det_linear n (minor M r) (posIn r p) a b (fun j => u (j + 1)) (fun j => w (j + 1))
        (posIn_lt r p n hrp hp hr)]
      generalize det n (setRow (minor M r) (posIn r p) fun j => u (j + 1)) = X
      generalize det n (setRow (minor M r) (posIn r p) fun j => w (j + 1)) = Y
      grind

theorem setRow_self (M : Nat → Nat → Int) (p : Nat) : setRow M p (M p) = M := by
  funext i j; simp only [setRow]; split <;> simp_all

/-! ## Equal rows -/

theorem minor_adj (M : Nat → Nat → Int) (p : Nat) (h : ∀ j, M p j = M (p + 1) j) :
    minor M p = minor M (p + 1) := by
  funext i j
  simp only [minor, skip]
  by_cases h1 : i < p
  · rw [if_pos h1, if_pos (by omega)]
  · by_cases h2 : i = p
    · subst h2; rw [if_neg (by omega), if_pos (by omega)]; exact (h (j + 1)).symm
    · rw [if_neg h1, if_neg (by omega)]

theorem det_adj_eq : ∀ (n : Nat) (M : Nat → Nat → Int) (p : Nat), p + 1 < n →
    (∀ j, M p j = M (p + 1) j) → det n M = 0
  | 0, _, _, hp, _ => absurd hp (Nat.not_lt_zero _)
  | n + 1, M, p, hp, h => by
    simp only [det]
    rw [sumTo_pair (n + 1) p (p + 1) _ (by omega) hp (by omega)]
    · rw [minor_adj M p h, h 0, sgn_succ]
      generalize det n (minor M (p + 1)) = D
      grind
    · intro r hr h1 h2
      have hz : det n (minor M r) = 0 := by
        by_cases hrp : r < p
        · apply det_adj_eq n (minor M r) (p - 1) (by omega)
          intro j
          simp only [minor, skip]
          rw [if_neg (by omega), if_neg (by omega), show p - 1 + 1 = p by omega]
          exact h (j + 1)
        · apply det_adj_eq n (minor M r) p (by omega)
          intro j
          simp only [minor, skip]
          rw [if_pos (by omega), if_pos (by omega)]
          exact h (j + 1)
      rw [hz]; simp

def swapRows (M : Nat → Nat → Int) (p q : Nat) : Nat → Nat → Int :=
  fun i j => if i = p then M q j else if i = q then M p j else M i j

theorem det_swap_adj (n : Nat) (M : Nat → Nat → Int) (p : Nat) (hp : p + 1 < n) :
    det n (swapRows M p (p + 1)) = -det n M := by
  -- N x y : row p := x, row p+1 := y
  let N : (Nat → Int) → (Nat → Int) → Nat → Nat → Int :=
    fun x y => setRow (setRow M (p + 1) y) p x
  have hN : ∀ x y, det n (N x y) = det n (setRow (setRow M p x) (p + 1) y) := by
    intro x y; congr 1; funext i j; simp only [N, setRow]
    by_cases h1 : i = p
    · subst h1; simp
    · simp [h1]
  -- linearity in row p (outer) and row p+1
  have linP : ∀ x x' y, det n (N (fun j => x j + x' j) y) = det n (N x y) + det n (N x' y) := by
    intro x x' y
    have := det_linear n (setRow M (p + 1) y) p 1 1 x x' (by omega)
    simp only [Int.one_mul] at this; exact this
  have linQ : ∀ x y y', det n (N x (fun j => y j + y' j)) = det n (N x y) + det n (N x y') := by
    intro x y y'
    rw [hN, hN, hN]
    have := det_linear n (setRow M p x) (p + 1) 1 1 y y' hp
    simp only [Int.one_mul] at this; exact this
  have zero : ∀ x, det n (N x x) = 0 := by
    intro x
    apply det_adj_eq n (N x x) p hp
    intro j; simp only [N, setRow]; simp
  let u := M p
  let w := M (p + 1)
  have h0 := zero (fun j => u j + w j)
  rw [linP, linQ, linQ, zero u, zero w] at h0
  have hM : N u w = M := by
    funext i j; simp only [N, setRow, u, w]
    by_cases h1 : i = p
    · simp [h1]
    · by_cases h2 : i = p + 1
      · simp [h2]
      · simp [h1, h2]
  have hS : N w u = swapRows M p (p + 1) := by
    funext i j; simp only [N, setRow, swapRows, u, w]
  rw [hM, hS] at h0
  omega

theorem det_eq_rows_aux : ∀ (k n : Nat) (M : Nat → Nat → Int) (p : Nat), p + k + 1 < n →
    (∀ j, M p j = M (p + k + 1) j) → det n M = 0
  | 0, n, M, p, hq, h => det_adj_eq n M p hq h
  | k + 1, n, M, p, hq, h => by
    have hsw := det_swap_adj n M (p + k + 1) hq
    have hz : det n (swapRows M (p + k + 1) (p + k + 1 + 1)) = 0 := by
      apply det_eq_rows_aux k n _ p (by omega)
      intro j
      show (if p = p + k + 1 then M (p + k + 1 + 1) j else if p = p + k + 1 + 1 then M (p + k + 1) j
          else M p j) = (if p + k + 1 = p + k + 1 then M (p + k + 1 + 1) j
          else if p + k + 1 = p + k + 1 + 1 then M (p + k + 1) j else M (p + k + 1) j)
      rw [if_neg (by omega), if_neg (by omega), if_pos rfl,
        show p + k + 1 + 1 = p + (k + 1) + 1 by omega]
      exact h j
    omega

theorem det_eq_rows (n : Nat) (M : Nat → Nat → Int) (p q : Nat) (hp : p < n) (hq : q < n)
    (hpq : p ≠ q) (h : ∀ j, M p j = M q j) : det n M = 0 := by
  by_cases hlt : p < q
  · have := det_eq_rows_aux (q - p - 1) n M p (by omega)
      (by rw [show p + (q - p - 1) + 1 = q by omega]; exact h)
    exact this
  · have := det_eq_rows_aux (p - q - 1) n M q (by omega)
      (by rw [show q + (p - q - 1) + 1 = p by omega]; exact fun j => (h j).symm)
    exact this

/-- Scaling row `p` by `s` and adding multiples of two other rows multiplies the
determinant by `s`. -/
theorem det_rowop (n : Nat) (M : Nat → Nat → Int) (p q1 q2 : Nat) (s c1 c2 : Int)
    (hp : p < n) (h1 : q1 < n) (h2 : q2 < n) (hp1 : p ≠ q1) (hp2 : p ≠ q2) :
    det n (setRow M p (fun j => s * M p j + (c1 * M q1 j + c2 * M q2 j))) = s * det n M := by
  have e1 := det_linear n M p s 1 (M p) (fun j => c1 * M q1 j + c2 * M q2 j) hp
  simp only [Int.one_mul] at e1
  rw [e1, setRow_self]
  have e2 := det_linear n M p c1 c2 (M q1) (M q2) hp
  rw [e2]
  have z1 : det n (setRow M p (M q1)) = 0 :=
    det_eq_rows n _ p q1 hp h1 hp1 (fun j => by simp [setRow, Ne.symm hp1])
  have z2 : det n (setRow M p (M q2)) = 0 :=
    det_eq_rows n _ p q2 hp h2 hp2 (fun j => by simp [setRow, Ne.symm hp2])
  rw [z1, z2]; simp

/-- Applying `det_rowop` to a contiguous block of rows `[a0, a0 + m)`, each combined with
two rows outside the block. -/
def blockOp (M : Nat → Nat → Int) (a0 m : Nat) (s : Int) (c1 c2 : Int) (b1 b2 : Nat → Nat) :
    Nat → Nat → Int :=
  fun i j => if a0 ≤ i ∧ i < a0 + m then s * M i j + (c1 * M (b1 i) j + c2 * M (b2 i) j)
    else M i j

theorem det_blockOp (n : Nat) (M : Nat → Nat → Int) (a0 : Nat) (s c1 c2 : Int)
    (b1 b2 : Nat → Nat) :
    ∀ m, a0 + m ≤ n →
    (∀ i, a0 ≤ i → i < a0 + m → b1 i < n ∧ b2 i < n ∧
      ¬(a0 ≤ b1 i ∧ b1 i < a0 + m) ∧ ¬(a0 ≤ b2 i ∧ b2 i < a0 + m)) →
    det n (blockOp M a0 m s c1 c2 b1 b2) = s ^ m * det n M
  | 0, _, _ => by
    have : blockOp M a0 0 s c1 c2 b1 b2 = M := by
      funext i j; simp only [blockOp]; rw [if_neg (by omega)]
    rw [this]; simp
  | m + 1, hm, hb => by
    have ih := det_blockOp n M a0 s c1 c2 b1 b2 m (by omega) (fun i h1 h2 => by
      obtain ⟨x1, x2, x3, x4⟩ := hb i h1 (by omega)
      exact ⟨x1, x2, fun e => x3 ⟨e.1, by omega⟩, fun e => x4 ⟨e.1, by omega⟩⟩)
    obtain ⟨y1, y2, y3, y4⟩ := hb (a0 + m) (by omega) (by omega)
    have key : blockOp M a0 (m + 1) s c1 c2 b1 b2 =
        setRow (blockOp M a0 m s c1 c2 b1 b2) (a0 + m)
          (fun j => s * blockOp M a0 m s c1 c2 b1 b2 (a0 + m) j +
            (c1 * blockOp M a0 m s c1 c2 b1 b2 (b1 (a0 + m)) j +
             c2 * blockOp M a0 m s c1 c2 b1 b2 (b2 (a0 + m)) j)) := by
      funext i j
      simp only [blockOp, setRow]
      by_cases hi : i = a0 + m
      · subst hi
        rw [if_pos (by omega), if_pos rfl, if_neg (by omega),
          if_neg (fun e => y3 ⟨e.1, by omega⟩), if_neg (fun e => y4 ⟨e.1, by omega⟩)]
      · rw [if_neg hi]
        by_cases h3 : a0 ≤ i ∧ i < a0 + m
        · rw [if_pos ⟨h3.1, by omega⟩, if_pos h3]
        · rw [if_neg (fun e => h3 ⟨e.1, by omega⟩), if_neg h3]
    rw [key, det_rowop n _ (a0 + m) (b1 (a0 + m)) (b2 (a0 + m)) s c1 c2 (by omega) y1 y2
      (fun e => y3 ⟨by omega, by omega⟩) (fun e => y4 ⟨by omega, by omega⟩), ih]
    rw [Int.pow_succ]; grind

end V9

namespace V9

/-! ## Scaling a block of rows -/

def scaleBlock (M : Nat → Nat → Int) (a0 m : Nat) (s : Int) : Nat → Nat → Int :=
  fun i j => if a0 ≤ i ∧ i < a0 + m then s * M i j else M i j

theorem det_scale_row (n : Nat) (M : Nat → Nat → Int) (p : Nat) (s : Int) (hp : p < n) :
    det n (setRow M p (fun j => s * M p j)) = s * det n M := by
  have e := det_linear n M p s 0 (M p) (M p) hp
  simp only [Int.zero_mul, Int.add_zero] at e
  rw [e, setRow_self]

theorem det_scaleBlock (n : Nat) (M : Nat → Nat → Int) (a0 : Nat) (s : Int) :
    ∀ m, a0 + m ≤ n → det n (scaleBlock M a0 m s) = s ^ m * det n M
  | 0, _ => by
    have : scaleBlock M a0 0 s = M := by
      funext i j; simp only [scaleBlock]; rw [if_neg (by omega)]
    rw [this]; simp
  | m + 1, hm => by
    have key : scaleBlock M a0 (m + 1) s =
        setRow (scaleBlock M a0 m s) (a0 + m) (fun j => s * scaleBlock M a0 m s (a0 + m) j) := by
      funext i j
      simp only [scaleBlock, setRow]
      by_cases hi : i = a0 + m
      · subst hi; rw [if_pos (by omega), if_pos rfl, if_neg (by omega)]
      · rw [if_neg hi]
        by_cases h3 : a0 ≤ i ∧ i < a0 + m
        · rw [if_pos ⟨h3.1, by omega⟩, if_pos h3]
        · rw [if_neg (fun e => h3 ⟨e.1, by omega⟩), if_neg h3]
    rw [key, det_scale_row n _ (a0 + m) s (by omega), det_scaleBlock n M a0 s m (by omega),
      Int.pow_succ]
    grind

/-! ## The size bound -/

def sumN : Nat → (Nat → Nat) → Nat
  | 0, _ => 0
  | n + 1, f => sumN n f + f n

def prodN : Nat → (Nat → Nat) → Nat
  | 0, _ => 1
  | n + 1, f => prodN n f * f n

def fact : Nat → Nat
  | 0 => 1
  | n + 1 => (n + 1) * fact n

theorem natAbs_sumTo_le : ∀ (n : Nat) (f : Nat → Int),
    (sumTo n f).natAbs ≤ sumN n (fun r => (f r).natAbs)
  | 0, _ => by simp [sumTo, sumN]
  | n + 1, f => by
    simp only [sumTo, sumN]
    exact Nat.le_trans (Int.natAbs_add_le _ _) (Nat.add_le_add_right (natAbs_sumTo_le n f) _)

theorem sumN_le : ∀ (n : Nat) (f g : Nat → Nat), (∀ r, r < n → f r ≤ g r) → sumN n f ≤ sumN n g
  | 0, _, _, _ => by simp [sumN]
  | n + 1, f, g, h => by
    simp only [sumN]
    exact Nat.add_le_add (sumN_le n f g (fun r hr => h r (by omega))) (h n (by omega))

theorem sumN_const : ∀ (n c : Nat), sumN n (fun _ => c) = n * c
  | 0, _ => by simp [sumN]
  | n + 1, c => by simp only [sumN]; rw [sumN_const n c, Nat.succ_mul]

theorem sumN_mul_right : ∀ (n : Nat) (f : Nat → Nat) (k : Nat),
    sumN n (fun r => f r * k) = sumN n f * k
  | 0, _, _ => by simp [sumN]
  | n + 1, f, k => by simp only [sumN]; rw [sumN_mul_right n f k, Nat.add_mul]

theorem prodN_skip (U : Nat → Nat) : ∀ (n r : Nat), r < n + 1 →
    U r * prodN n (fun i => U (skip r i)) = prodN (n + 1) U
  | 0, r, hr => by
    have : r = 0 := by omega
    subst this; simp [prodN]
  | n + 1, r, hr => by
    by_cases h : r = n + 1
    · subst h
      have : prodN (n + 1) (fun i => U (skip (n + 1) i)) = prodN (n + 1) U := by
        have aux : ∀ k, k ≤ n + 1 → prodN k (fun i => U (skip (n + 1) i)) = prodN k U := by
          intro k
          induction k with
          | zero => intro _; rfl
          | succ k ih =>
            intro hk
            simp only [prodN]
            rw [ih (by omega)]
            simp only [skip]; rw [if_pos (by omega)]
        exact aux (n + 1) (Nat.le_refl _)
      rw [this]; simp only [prodN]; rw [Nat.mul_comm]
    · show U r * (prodN n (fun i => U (skip r i)) * U (skip r n)) = prodN (n + 1) U * U (n + 1)
      rw [← Nat.mul_assoc, prodN_skip U n r (by omega)]
      simp only [skip]; rw [if_neg (by omega)]

theorem prodN_shift (V : Nat → Nat) : ∀ n, V 0 * prodN n (fun c => V (c + 1)) = prodN (n + 1) V
  | 0 => by simp [prodN]
  | n + 1 => by
    simp only [prodN]
    rw [← Nat.mul_assoc, prodN_shift V n]
    simp only [prodN]

theorem natAbs_sgn (r : Nat) : (sgn r).natAbs = 1 := by
  unfold sgn; split <;> rfl

/-- `|det M| · k^n ≤ n! · ∏ U · ∏ V` when every entry satisfies `|M r c| · k ≤ U r · V c`. -/
theorem det_bound : ∀ (n : Nat) (M : Nat → Nat → Int) (U V : Nat → Nat) (k : Nat),
    (∀ r c, r < n → c < n → (M r c).natAbs * k ≤ U r * V c) →
    (det n M).natAbs * k ^ n ≤ fact n * prodN n U * prodN n V
  | 0, _, _, _, _, _ => by simp [det, fact, prodN]
  | n + 1, M, U, V, k, h => by
    simp only [det]
    have step : ∀ r, r < n + 1 →
        (sgn r * M r 0 * det n (minor M r)).natAbs * k ^ (n + 1) ≤
          fact n * prodN (n + 1) U * prodN (n + 1) V := by
      intro r hr
      have ih := det_bound n (minor M r) (fun i => U (skip r i)) (fun c => V (c + 1)) k
        (fun i c hi hc => h _ _ (skip_lt r i n hr hi) (by omega))
      have h0 := h r 0 hr (by omega)
      rw [Int.natAbs_mul, Int.natAbs_mul, natAbs_sgn, Nat.one_mul, Nat.pow_succ]
      calc (M r 0).natAbs * (det n (minor M r)).natAbs * (k ^ n * k)
          = ((M r 0).natAbs * k) * ((det n (minor M r)).natAbs * k ^ n) := by
            rw [Nat.mul_comm (k ^ n) k]; grind
        _ ≤ (U r * V 0) * (fact n * prodN n (fun i => U (skip r i)) *
              prodN n (fun c => V (c + 1))) := Nat.mul_le_mul h0 ih
        _ = fact n * (U r * prodN n (fun i => U (skip r i))) *
              (V 0 * prodN n (fun c => V (c + 1))) := by grind
        _ = fact n * prodN (n + 1) U * prodN (n + 1) V := by
            rw [prodN_skip U n r hr, prodN_shift V n]
    calc (sumTo (n + 1) fun r => sgn r * M r 0 * det n (minor M r)).natAbs * k ^ (n + 1)
        ≤ sumN (n + 1) (fun r => (sgn r * M r 0 * det n (minor M r)).natAbs) * k ^ (n + 1) :=
          Nat.mul_le_mul_right _ (natAbs_sumTo_le _ _)
      _ = sumN (n + 1) (fun r => (sgn r * M r 0 * det n (minor M r)).natAbs * k ^ (n + 1)) :=
          (sumN_mul_right _ _ _).symm
      _ ≤ sumN (n + 1) (fun _ => fact n * prodN (n + 1) U * prodN (n + 1) V) :=
          sumN_le _ _ _ step
      _ = fact (n + 1) * prodN (n + 1) U * prodN (n + 1) V := by
          rw [sumN_const]; simp only [fact]; grind

end V9

/-!
# Subresultants and the normal PRS

Polynomials are degree-indexed coefficient functions `Nat → Int`.
-/

namespace V9

/-- Coefficient of `x^t · P` at degree `e`. -/
def shc (P : Nat → Int) (t e : Nat) : Int := if t ≤ e then P (e - t) else 0

/-- Degree read by column `c` of the `j`-th subresultant matrix (last column: degree `i`). -/
def colDeg (p q j i c : Nat) : Nat := if c + 1 < p + q - 2 * j then p + q - j - 1 - c else i

/-- The `j`-th subresultant matrix of `X` (formal degree `p`) and `Y` (formal degree `q`).
With `conv = true` the `q - j` rows `x^k X` come first, otherwise the `p - j` rows `x^k Y`. -/
def sxM (X Y : Nat → Int) (p q j i : Nat) (conv : Bool) : Nat → Nat → Int := fun r c =>
  if conv then
    (if r < q - j then shc X (q - j - 1 - r) (colDeg p q j i c)
     else shc Y (p - j - 1 - (r - (q - j))) (colDeg p q j i c))
  else
    (if r < p - j then shc Y (p - j - 1 - r) (colDeg p q j i c)
     else shc X (q - j - 1 - (r - (p - j))) (colDeg p q j i c))

/-- Coefficient of `x^i` in the `j`-th subresultant. -/
def sres (X Y : Nat → Int) (p q j i : Nat) (conv : Bool) : Int :=
  det (p + q - 2 * j) (sxM X Y p q j i conv)

/-- Pseudo-remainder of `A` (formal degree `d+1`) by `B` (formal degree `d`):
`B_d² A − (A_{d+1} B_d x + γ) B`, which has formal degree `d − 1`. -/
def premF (A B : Nat → Int) (d : Nat) : Nat → Int := fun e =>
  if e < d then
    B d * B d * A e - A (d + 1) * B d * (if 1 ≤ e then B (e - 1) else 0)
      - (B d * A d - A (d + 1) * B (d - 1)) * B e
  else 0

theorem premF_id (A B : Nat → Int) (d : Nat) (hd : 1 ≤ d)
    (hA : ∀ e, d + 1 < e → A e = 0) (hB : ∀ e, d < e → B e = 0) (e : Nat) :
    B d * B d * A e + (-(A (d + 1) * B d)) * (if 1 ≤ e then B (e - 1) else 0)
      + (-(B d * A d - A (d + 1) * B (d - 1))) * B e = premF A B d e := by
  unfold premF
  by_cases h1 : e < d
  · rw [if_pos h1]; grind
  · rw [if_neg h1]
    by_cases h2 : e = d
    · subst h2; rw [if_pos hd]; grind
    · by_cases h3 : e = d + 1
      · subst h3
        rw [if_pos (by omega), show d + 1 - 1 = d by omega, hB (d + 1) (by omega)]; grind
      · rw [hA e (by omega), hB e (by omega), if_pos (by omega), hB (e - 1) (by omega)]; grind

theorem shc_comb (A B : Nat → Int) (d : Nat) (hd : 1 ≤ d)
    (hA : ∀ e, d + 1 < e → A e = 0) (hB : ∀ e, d < e → B e = 0) (t e : Nat) :
    B d * B d * shc A t e + ((-(A (d + 1) * B d)) * shc B (t + 1) e
      + (-(B d * A d - A (d + 1) * B (d - 1))) * shc B t e) = shc (premF A B d) t e := by
  unfold shc
  by_cases h : t ≤ e
  · rw [if_pos h, if_pos h, if_pos h, ← premF_id A B d hd hA hB (e - t)]
    by_cases h' : t + 1 ≤ e
    · rw [if_pos h', if_pos (by omega), show e - t - 1 = e - (t + 1) by omega]; grind
    · rw [if_neg h', if_neg (by omega)]; grind
  · rw [if_neg h, if_neg h, if_neg (by omega), if_neg h]; grind

theorem sq_eq (b : Int) : b ^ 2 = b * b := by
  rw [Int.pow_succ, Int.pow_succ, Int.pow_zero, Int.one_mul]

theorem pow_two_mul (b : Int) (m : Nat) : b ^ (2 * m) = (b * b) ^ m := by
  rw [Int.pow_mul, sq_eq]

theorem skip_of_lt {r i : Nat} (h : i < r) : skip r i = i := by unfold skip; rw [if_pos h]
theorem skip_of_ge {r i : Nat} (h : r ≤ i) : skip r i = i + 1 := by
  unfold skip; rw [if_neg (by omega)]

/-! ## Lemma A, rows of `A` first -/

theorem lemmaA_true (A B : Nat → Int) (j t i : Nat) (_hi : i ≤ j)
    (hA : ∀ e, j + 1 + t + 1 < e → A e = 0) (hB : ∀ e, j + 1 + t < e → B e = 0) :
    B (j + 1 + t) ^ (2 * (t + 1)) * sres A B (j + 1 + t + 1) (j + 1 + t) j i true =
      B (j + 1 + t) ^ 2 * sres B (premF A B (j + 1 + t)) (j + 1 + t) (j + t) j i false := by
  -- notation
  have hN : j + 1 + t + 1 + (j + 1 + t) - 2 * j = (2 * t + 1) + 1 + 1 := by omega
  have hN' : j + 1 + t + (j + t) - 2 * j = 2 * t + 1 := by omega
  unfold sres
  rw [hN, hN']
  generalize hd : j + 1 + t = d at *
  have hd1 : 1 ≤ d := by omega
  let b := B d
  let a := A (d + 1)
  let g := B d * A d - A (d + 1) * B (d - 1)
  let M0 := sxM A B (d + 1) d j i true
  let M1 := blockOp M0 0 (t + 1) (b * b) (-(a * b)) (-g) (fun r => t + 1 + r) (fun r => t + 1 + r + 1)
  have e1 : det (2 * t + 1 + 1 + 1) M1 = (b * b) ^ (t + 1) * det (2 * t + 1 + 1 + 1) M0 :=
    det_blockOp _ M0 0 _ _ _ _ _ (t + 1) (by omega) (fun r h1 h2 => ⟨by omega, by omega, by omega, by omega⟩)
  -- the matrix after the row operations
  let M3 : Nat → Nat → Int := fun r c =>
    if r < t + 1 then shc (premF A B d) (t + 1 - 1 - r) (colDeg (d + 1) d j i c) else M0 r c
  have e3 : det (2 * t + 1 + 1 + 1) M1 = det (2 * t + 1 + 1 + 1) M3 := by
    apply det_congr
    intro r c hr hc
    simp only [M1, M3, blockOp]
    by_cases hrt : r < t + 1
    · rw [if_pos ⟨Nat.zero_le _, by omega⟩, if_pos hrt]
      simp only [M0, sxM, if_true]
      rw [if_pos (by omega), if_neg (by omega), if_neg (by omega)]
      rw [show d + 1 - j - 1 - (t + 1 + r - (d - j)) = t + 1 - 1 - r + 1 by omega,
        show d + 1 - j - 1 - (t + 1 + r + 1 - (d - j)) = t + 1 - 1 - r by omega,
        show d - j - 1 - r = t + 1 - 1 - r by omega]
      exact shc_comb A B d hd1 hA hB _ _
    · rw [if_neg (by omega), if_neg hrt]
  -- first expansion, at row t+1
  have colz : colDeg (d + 1) d j i 0 = 2 * d - j := by
    unfold colDeg; rw [if_pos (by omega)]; omega
  have colo : colDeg (d + 1) d j i 1 = 2 * d - j - 1 := by
    unfold colDeg; rw [if_pos (by omega)]; omega
  have hp0 : ∀ e, d ≤ e → premF A B d e = 0 := by
    intro e he; unfold premF; rw [if_neg (by omega)]
  have e4 : det (2 * t + 1 + 1 + 1) M3 = sgn (t + 1) * b * det (2 * t + 1 + 1) (minor M3 (t + 1)) := by
    rw [det_single (2 * t + 1 + 1) (t + 1) M3 (by omega)]
    · congr 2
      simp only [M3, M0, sxM, if_true]
      rw [if_neg (by omega), if_neg (by omega), colz]
      unfold shc; rw [if_pos (by omega)]
      congr 1; omega
    · intro r hr hrt
      simp only [M3]
      by_cases h1 : r < t + 1
      · rw [if_pos h1, colz]; unfold shc; rw [if_pos (by omega)]; exact hp0 _ (by omega)
      · rw [if_neg h1]; simp only [M0, sxM, if_true]
        rw [if_neg (by omega), colz]; unfold shc; rw [if_pos (by omega)]; exact hB _ (by omega)
  -- second expansion, again at row t+1 of the minor
  have e5 : det (2 * t + 1 + 1) (minor M3 (t + 1)) =
      sgn (t + 1) * b * det (2 * t + 1) (minor (minor M3 (t + 1)) (t + 1)) := by
    rw [det_single (2 * t + 1) (t + 1) _ (by omega)]
    · congr 2
      show M3 (skip (t + 1) (t + 1)) (0 + 1) = b
      rw [skip_of_ge (Nat.le_refl _)]
      simp only [M3, M0, sxM, if_true]
      rw [if_neg (by omega), if_neg (by omega), colo]
      unfold shc; rw [if_pos (by omega)]
      congr 1; omega
    · intro r hr hrt
      show M3 (skip (t + 1) r) (0 + 1) = 0
      by_cases h1 : r < t + 1
      · rw [skip_of_lt h1]; simp only [M3]
        rw [if_pos h1, colo]; unfold shc; rw [if_pos (by omega)]; exact hp0 _ (by omega)
      · rw [skip_of_ge (by omega)]; simp only [M3]
        rw [if_neg (by omega)]; simp only [M0, sxM, if_true]
        rw [if_neg (by omega), colo]; unfold shc; rw [if_pos (by omega)]; exact hB _ (by omega)
  -- what is left is the next subresultant matrix, rows of `premF` first
  have e6 : det (2 * t + 1) (minor (minor M3 (t + 1)) (t + 1)) =
      det (2 * t + 1) (sxM B (premF A B d) d (j + t) j i false) := by
    apply det_congr
    intro r c hr hc
    have cd : colDeg (d + 1) d j i (c + 1 + 1) = colDeg d (j + t) j i c := by
      unfold colDeg
      by_cases hc' : c + 1 < 2 * t + 1
      · rw [if_pos (by omega), if_pos (by omega)]; omega
      · rw [if_neg (by omega), if_neg (by omega)]
    show M3 (skip (t + 1) (skip (t + 1) r)) (c + 1 + 1) = _
    simp only [sxM, Bool.false_eq_true, ↓reduceIte]
    by_cases h1 : r < t + 1
    · rw [skip_of_lt h1, skip_of_lt h1]; simp only [M3]
      rw [if_pos h1, if_pos (by omega), cd]
      congr 1; omega
    · rw [skip_of_ge (show t + 1 ≤ r by omega), skip_of_ge (show t + 1 ≤ r + 1 by omega)]
      simp only [M3]
      rw [if_neg (by omega), if_neg (by omega)]
      simp only [M0, sxM, if_true]
      rw [if_neg (by omega), cd]
      congr 1; omega
  rw [pow_two_mul, sq_eq, ← e1, e3, e4, e5, e6]
  have := sgn_mul_self (t + 1)
  generalize sgn (t + 1) = s at *
  generalize det (2 * t + 1) (sxM B (premF A B d) d (j + t) j i false) = D
  grind

/-! ## Lemma A, rows of `B` first -/

theorem lemmaA_false (A B : Nat → Int) (j t i : Nat) (_hi : i ≤ j)
    (hA : ∀ e, j + 1 + t + 1 < e → A e = 0) (hB : ∀ e, j + 1 + t < e → B e = 0) :
    B (j + 1 + t) ^ (2 * (t + 1)) * sres A B (j + 1 + t + 1) (j + 1 + t) j i false =
      B (j + 1 + t) ^ 2 * sres B (premF A B (j + 1 + t)) (j + 1 + t) (j + t) j i true := by
  have hN : j + 1 + t + 1 + (j + 1 + t) - 2 * j = (2 * t + 1) + 1 + 1 := by omega
  have hN' : j + 1 + t + (j + t) - 2 * j = 2 * t + 1 := by omega
  unfold sres
  rw [hN, hN']
  generalize hd : j + 1 + t = d at *
  have hd1 : 1 ≤ d := by omega
  let b := B d
  let a := A (d + 1)
  let g := B d * A d - A (d + 1) * B (d - 1)
  let M0 := sxM A B (d + 1) d j i false
  let M1 := blockOp M0 (t + 2) (t + 1) (b * b) (-(a * b)) (-g) (fun r => r - (t + 2))
    (fun r => r - (t + 2) + 1)
  have e1 : det (2 * t + 1 + 1 + 1) M1 = (b * b) ^ (t + 1) * det (2 * t + 1 + 1 + 1) M0 :=
    det_blockOp _ M0 (t + 2) _ _ _ _ _ (t + 1) (by omega)
      (fun r h1 h2 => ⟨by omega, by omega, by omega, by omega⟩)
  let M3 : Nat → Nat → Int := fun r c =>
    if t + 2 ≤ r then shc (premF A B d) (t - (r - (t + 2))) (colDeg (d + 1) d j i c) else M0 r c
  have e3 : det (2 * t + 1 + 1 + 1) M1 = det (2 * t + 1 + 1 + 1) M3 := by
    apply det_congr
    intro r c hr hc
    simp only [M1, M3, blockOp]
    by_cases hrt : t + 2 ≤ r
    · rw [if_pos ⟨hrt, by omega⟩, if_pos hrt]
      simp only [M0, sxM, Bool.false_eq_true, ↓reduceIte]
      rw [if_neg (by omega), if_pos (by omega), if_pos (by omega)]
      rw [show d + 1 - j - 1 - (r - (t + 2)) = t - (r - (t + 2)) + 1 by omega,
        show d + 1 - j - 1 - (r - (t + 2) + 1) = t - (r - (t + 2)) by omega,
        show d - j - 1 - (r - (d + 1 - j)) = t - (r - (t + 2)) by omega]
      exact shc_comb A B d hd1 hA hB _ _
    · rw [if_neg (fun h => hrt h.1), if_neg hrt]
  have colz : colDeg (d + 1) d j i 0 = 2 * d - j := by
    unfold colDeg; rw [if_pos (by omega)]; omega
  have colo : colDeg (d + 1) d j i 1 = 2 * d - j - 1 := by
    unfold colDeg; rw [if_pos (by omega)]; omega
  have hp0 : ∀ e, d ≤ e → premF A B d e = 0 := by
    intro e he; unfold premF; rw [if_neg (by omega)]
  have e4 : det (2 * t + 1 + 1 + 1) M3 = sgn 0 * b * det (2 * t + 1 + 1) (minor M3 0) := by
    rw [det_single (2 * t + 1 + 1) 0 M3 (by omega)]
    · congr 2
      simp only [M3, M0, sxM, Bool.false_eq_true, ↓reduceIte]
      rw [if_neg (by omega), if_pos (by omega), colz]
      unfold shc; rw [if_pos (by omega)]
      congr 1; omega
    · intro r hr hrt
      simp only [M3]
      by_cases h1 : t + 2 ≤ r
      · rw [if_pos h1, colz]; unfold shc; rw [if_pos (by omega)]; exact hp0 _ (by omega)
      · rw [if_neg h1]; simp only [M0, sxM, Bool.false_eq_true, ↓reduceIte]
        rw [if_pos (by omega), colz]; unfold shc; rw [if_pos (by omega)]; exact hB _ (by omega)
  have e5 : det (2 * t + 1 + 1) (minor M3 0) =
      sgn 0 * b * det (2 * t + 1) (minor (minor M3 0) 0) := by
    rw [det_single (2 * t + 1) 0 _ (by omega)]
    · congr 2
      show M3 (skip 0 0) (0 + 1) = b
      rw [skip_of_ge (Nat.le_refl _)]
      simp only [M3, M0, sxM, Bool.false_eq_true, ↓reduceIte]
      rw [if_neg (by omega), if_pos (by omega), colo]
      unfold shc; rw [if_pos (by omega)]
      congr 1; omega
    · intro r hr hrt
      show M3 (skip 0 r) (0 + 1) = 0
      rw [skip_of_ge (Nat.zero_le _)]
      simp only [M3]
      by_cases h1 : t + 2 ≤ r + 1
      · rw [if_pos h1, colo]; unfold shc; rw [if_pos (by omega)]; exact hp0 _ (by omega)
      · rw [if_neg h1]; simp only [M0, sxM, Bool.false_eq_true, ↓reduceIte]
        rw [if_pos (by omega), colo]; unfold shc; rw [if_pos (by omega)]; exact hB _ (by omega)
  have e6 : det (2 * t + 1) (minor (minor M3 0) 0) =
      det (2 * t + 1) (sxM B (premF A B d) d (j + t) j i true) := by
    apply det_congr
    intro r c hr hc
    have cd : colDeg (d + 1) d j i (c + 1 + 1) = colDeg d (j + t) j i c := by
      unfold colDeg
      by_cases hc' : c + 1 < 2 * t + 1
      · rw [if_pos (by omega), if_pos (by omega)]; omega
      · rw [if_neg (by omega), if_neg (by omega)]
    show M3 (skip 0 (skip 0 r)) (c + 1 + 1) = _
    rw [skip_of_ge (show 0 ≤ r by omega), skip_of_ge (show 0 ≤ r + 1 by omega)]
    simp only [sxM, ↓reduceIte]
    simp only [M3]
    by_cases h1 : r < t
    · rw [if_neg (by omega), if_pos (by omega)]
      simp only [M0, sxM, Bool.false_eq_true, ↓reduceIte]
      rw [if_pos (by omega), cd]
      congr 1; omega
    · rw [if_pos (by omega), if_neg (by omega), cd]
      congr 1; omega
  rw [pow_two_mul, sq_eq, ← e1, e3, e4, e5, e6]
  simp only [sgn, Nat.zero_mod, ↓reduceIte]
  generalize det (2 * t + 1) (sxM B (premF A B d) d (j + t) j i true) = D
  grind

/-! ## The top subresultant and scaling -/

theorem sres_top (X Y : Nat → Int) (j i : Nat) (c : Bool) :
    sres X Y (j + 1) j j i c = Y i := by
  unfold sres
  rw [show j + 1 + j - 2 * j = 0 + 1 by omega]
  rw [det_single 0 0 _ (by omega) (fun r hr hr0 => by omega)]
  have h1 : sxM X Y (j + 1) j j i c 0 0 = Y i := by
    have hc : colDeg (j + 1) j j i 0 = i := by
      unfold colDeg; rw [if_neg (by omega)]
    cases c
    · simp only [sxM, Bool.false_eq_true, ↓reduceIte]
      rw [if_pos (by omega), hc]; unfold shc; rw [if_pos (by omega)]; congr 1; omega
    · simp only [sxM, ↓reduceIte]
      rw [if_neg (by omega), hc]; unfold shc; rw [if_pos (by omega)]; congr 1; omega
  rw [h1]; simp [det, sgn]

theorem lemmaA (A B : Nat → Int) (j t i : Nat) (c : Bool) (hi : i ≤ j)
    (hA : ∀ e, j + 1 + t + 1 < e → A e = 0) (hB : ∀ e, j + 1 + t < e → B e = 0) :
    B (j + 1 + t) ^ (2 * (t + 1)) * sres A B (j + 1 + t + 1) (j + 1 + t) j i c =
      B (j + 1 + t) ^ 2 * sres B (premF A B (j + 1 + t)) (j + 1 + t) (j + t) j i (!c) := by
  cases c
  · exact lemmaA_false A B j t i hi hA hB
  · exact lemmaA_true A B j t i hi hA hB

/-- The coefficient of `x^i` in the subresultant just below `B`'s degree is the
pseudo-remainder's coefficient. -/
theorem sres_prem (A B : Nat → Int) (j i : Nat) (c : Bool) (hi : i ≤ j) (hb : B (j + 1) ≠ 0)
    (hA : ∀ e, j + 1 + 1 < e → A e = 0) (hB : ∀ e, j + 1 < e → B e = 0) :
    sres A B (j + 1 + 1) (j + 1) j i c = premF A B (j + 1) i := by
  have h := lemmaA A B j 0 i c hi (by simpa using hA) (by simpa using hB)
  simp only [Nat.add_zero] at h
  rw [sres_top, show 2 * (0 + 1) = 2 by rfl] at h
  have hb2 : B (j + 1) ^ 2 ≠ 0 := by
    rw [sq_eq]; exact Int.mul_ne_zero hb hb
  exact Int.eq_of_mul_eq_mul_left hb2 h

def scaleP (s : Int) (Y : Nat → Int) : Nat → Int := fun e => s * Y e

theorem shc_scale (s : Int) (Y : Nat → Int) (t e : Nat) : shc (scaleP s Y) t e = s * shc Y t e := by
  unfold shc scaleP; split <;> simp

theorem sres_scale (X Y : Nat → Int) (s : Int) (p q j i : Nat) (c : Bool) (hq : j ≤ q) (hp : q ≤ p) :
    sres X (scaleP s Y) p q j i c = s ^ (p - j) * sres X Y p q j i c := by
  unfold sres
  cases c
  · rw [← det_scaleBlock (p + q - 2 * j) (sxM X Y p q j i false) 0 s (p - j) (by omega)]
    apply det_congr
    intro r col hr hc
    simp only [sxM, scaleBlock, Bool.false_eq_true, ↓reduceIte]
    by_cases h : r < p - j
    · rw [if_pos h, if_pos ⟨Nat.zero_le _, by omega⟩, if_pos h, shc_scale]
    · rw [if_neg h, if_neg (by omega), if_neg h]
  · rw [← det_scaleBlock (p + q - 2 * j) (sxM X Y p q j i true) (q - j) s (p - j) (by omega)]
    apply det_congr
    intro r col hr hc
    simp only [sxM, scaleBlock, ↓reduceIte]
    by_cases h : r < q - j
    · rw [if_pos h, if_neg (by omega), if_pos h]
    · rw [if_neg h, if_pos ⟨by omega, by omega⟩, if_neg h, shc_scale]

/-! ## The normal PRS chain -/

def nextC (A B : Nat → Int) (d : Nat) (first : Bool) : Nat → Int :=
  fun e => if first then premF A B d e else premF A B d e / (A (d + 1) * A (d + 1))

/-- `chainP f g m k = (F_k, F_{k+1})`; `F_{k+1}` has formal degree `m − (k+1)`. -/
def chainP (f g : Nat → Int) (m : Nat) : Nat → (Nat → Int) × (Nat → Int)
  | 0 => (f, g)
  | k + 1 => ((chainP f g m k).2,
      nextC (chainP f g m k).1 (chainP f g m k).2 (m - (k + 1)) (k == 0))

def conv (k : Nat) : Bool := k % 2 == 0

theorem conv_succ (k : Nat) : conv (k + 1) = !conv k := by
  unfold conv
  by_cases h : k % 2 = 0
  · have : (k + 1) % 2 = 1 := by omega
    simp [h, this]
  · have h1 : k % 2 = 1 := by omega
    have : (k + 1) % 2 = 0 := by omega
    simp [h1, this]

/-- The chain invariant for the pair `(F_k, F_{k+1})`, with `d = m − (k+1)`. -/
structure Inv (f g : Nat → Int) (m k : Nat) : Prop where
  degA : ∀ e, m - (k + 1) + 1 < e → (chainP f g m k).1 e = 0
  degB : ∀ e, m - (k + 1) < e → (chainP f g m k).2 e = 0
  rel : ∀ j i, j + 1 ≤ m - (k + 1) → i ≤ j →
    sres (chainP f g m k).1 (chainP f g m k).2 (m - (k + 1) + 1) (m - (k + 1)) j i (conv k) =
      (if k = 0 then 1 else ((chainP f g m k).1 (m - (k + 1) + 1)) ^ (2 * (m - (k + 1) - j))) *
        sres f g m (m - 1) j i true
  val : 1 ≤ k → ∀ i, i ≤ m - (k + 1) →
    (chainP f g m k).2 i = sres f g m (m - 1) (m - (k + 1)) i true

theorem inv_zero (f g : Nat → Int) (m : Nat) (hm : 2 ≤ m)
    (hf : ∀ e, m < e → f e = 0) (hg : ∀ e, m - 1 < e → g e = 0) : Inv f g m 0 where
  degA := by intro e he; exact hf e (by omega)
  degB := by intro e he; exact hg e (by omega)
  rel := by
    intro j i hj hi
    simp only [chainP, ↓reduceIte, Int.one_mul, conv, Nat.zero_mod]
    rw [show m - (0 + 1) + 1 = m by omega, show m - (0 + 1) = m - 1 by omega]
    rfl
  val := by intro h; omega

/-- One step of the chain: exactness and the value of the new polynomial. -/
theorem step_exact (f g : Nat → Int) (m k : Nat) (hI : Inv f g m k) (hd : 1 ≤ m - (k + 1))
    (hb : (chainP f g m k).2 (m - (k + 1)) ≠ 0)
    (ha : 1 ≤ k → (chainP f g m k).1 (m - (k + 1) + 1) ≠ 0) :
    ∀ i, i ≤ m - (k + 1) - 1 →
      premF (chainP f g m k).1 (chainP f g m k).2 (m - (k + 1)) i =
        (if k = 0 then 1 else ((chainP f g m k).1 (m - (k + 1) + 1)) ^ 2) *
          sres f g m (m - 1) (m - (k + 1) - 1) i true := by
  intro i hi
  obtain ⟨j, hj⟩ : ∃ j, m - (k + 1) = j + 1 := ⟨m - (k + 1) - 1, by omega⟩
  rw [hj] at hi hb ha ⊢
  have hA := hI.degA; have hB := hI.degB; have hR := hI.rel
  rw [hj] at hA hB hR
  have e1 := sres_prem (chainP f g m k).1 (chainP f g m k).2 j i (conv k) (by omega) hb hA hB
  rw [← e1, hR j i (by omega) (by omega)]
  congr 1
  split
  · rfl
  · congr 1; omega

theorem inv_succ (f g : Nat → Int) (m k : Nat) (hI : Inv f g m k) (hd : 1 ≤ m - (k + 1))
    (hb : (chainP f g m k).2 (m - (k + 1)) ≠ 0)
    (ha : 1 ≤ k → (chainP f g m k).1 (m - (k + 1) + 1) ≠ 0) : Inv f g m (k + 1) := by
  obtain ⟨j0, hj⟩ : ∃ j0, m - (k + 1) = j0 + 1 := ⟨m - (k + 1) - 1, by omega⟩
  have hj' : m - (k + 1 + 1) = j0 := by omega
  let A := (chainP f g m k).1
  let B := (chainP f g m k).2
  let a := A (j0 + 1 + 1)
  have hP1 : (chainP f g m (k + 1)).1 = B := rfl
  have hP2 : (chainP f g m (k + 1)).2 = nextC A B (j0 + 1) (k == 0) := by
    show nextC A B (m - (k + 1)) (k == 0) = _; rw [hj]
  have hEx := step_exact f g m k hI hd hb ha
  rw [hj] at hEx hb ha
  have hpz : ∀ e, j0 + 1 ≤ e → premF A B (j0 + 1) e = 0 := by
    intro e he; unfold premF; rw [if_neg (by omega)]
  -- the raw remainder is the scaled next polynomial
  have hscale : premF A B (j0 + 1) =
      scaleP (if k = 0 then 1 else a ^ 2) (nextC A B (j0 + 1) (k == 0)) := by
    funext e
    simp only [scaleP, nextC]
    by_cases hk : k = 0
    · simp [hk]
    · have hk' : (k == 0) = false := by simp [hk]
      rw [hk', if_neg hk]; simp only [Bool.false_eq_true, ↓reduceIte]
      have ha0 : a ≠ 0 := ha (by omega)
      have hsq : a ^ 2 = a * a := sq_eq a
      by_cases he : e ≤ j0
      · have := hEx e (by omega)
        rw [if_neg hk] at this
        show premF A B (j0 + 1) e = a ^ 2 * (premF A B (j0 + 1) e / (A (j0 + 1 + 1) * A (j0 + 1 + 1)))
        rw [this, ← hsq, Int.mul_ediv_cancel_left _ (by rw [hsq]; exact Int.mul_ne_zero ha0 ha0)]
      · rw [hpz e (by omega)]; simp
  constructor
  · intro e he
    rw [hP1]; exact hI.degB e (by omega)
  · intro e he
    rw [hP2]; simp only [nextC]
    rw [hpz e (by omega)]; split <;> simp
  · intro j i hjj hi
    rw [hP1, hP2, hj']
    rw [if_neg (Nat.succ_ne_zero k)]
    have hjt : ∃ t, j0 + 1 = j + 1 + t + 1 := ⟨j0 - j - 1, by omega⟩
    obtain ⟨t, ht⟩ := hjt
    -- Lemma A on (A, B), then undo the scaling
    have hAd : ∀ e, j + 1 + (t + 1) + 1 < e → A e = 0 := by
      intro e he; exact hI.degA e (by omega)
    have hBd : ∀ e, j + 1 + (t + 1) < e → B e = 0 := by
      intro e he; exact hI.degB e (by omega)
    have LA := lemmaA A B j (t + 1) i (conv k) hi hAd hBd
    have hR := hI.rel j i (by omega) hi
    rw [show m - (k + 1) + 1 = j + 1 + (t + 1) + 1 by omega,
      show m - (k + 1) = j + 1 + (t + 1) by omega] at hR
    rw [hR, show j + 1 + (t + 1) = j0 + 1 by omega, hscale,
      sres_scale B _ _ _ _ _ _ _ (by omega) (by omega), show j + (t + 1) = j0 by omega] at LA
    rw [conv_succ, show j0 - j = t + 1 by omega]
    have hx : (if k = 0 then 1 else A (j0 + 1 + 1) ^ (2 * (j0 + 1 - j))) =
        (if k = 0 then 1 else a ^ 2) ^ (j0 + 1 - j) := by
      split
      · exact Int.one_pow.symm
      · rw [Int.pow_mul]
    rw [hx, show 2 * (t + 1 + 1) = 2 + 2 * (t + 1) by omega, Int.pow_add] at LA
    have hc0 : (if k = 0 then 1 else a ^ 2) ^ (j0 + 1 - j) ≠ 0 := by
      apply Int.pow_ne_zero
      split
      · decide
      · rw [sq_eq]; exact Int.mul_ne_zero (ha (by omega)) (ha (by omega))
    have hb2 : B (j0 + 1) ^ 2 ≠ 0 := by rw [sq_eq]; exact Int.mul_ne_zero hb hb
    generalize (if k = 0 then 1 else a ^ 2) ^ (j0 + 1 - j) = C at LA hc0
    generalize sres B (nextC A B (j0 + 1) (k == 0)) (j0 + 1) j0 j i (!conv k) = T at LA ⊢
    generalize sres f g m (m - 1) j i true = S at LA ⊢
    generalize B (j0 + 1) ^ 2 = b2 at LA hb2
    generalize B (j0 + 1) ^ (2 * (t + 1)) = bt at LA ⊢
    have h1 : b2 * (C * T) = b2 * (C * (bt * S)) := by rw [← LA]; grind
    have h2 := Int.eq_of_mul_eq_mul_left hb2 h1
    exact Int.eq_of_mul_eq_mul_left hc0 h2
  · intro _ i hi
    rw [hP2, hj']
    simp only [nextC]
    have := hEx i (by omega)
    by_cases hk : k = 0
    · subst hk
      simp only [↓reduceIte] at this ⊢
      rw [this, Int.one_mul]; congr 1
    · have hk' : (k == 0) = false := by simp [hk]
      rw [hk']; simp only [Bool.false_eq_true, ↓reduceIte]
      rw [if_neg hk] at this
      have ha0 : a ≠ 0 := ha (by omega)
      rw [this, sq_eq, show j0 + 1 - 1 = j0 by omega]
      exact Int.mul_ediv_cancel_left _ (Int.mul_ne_zero ha0 ha0)

theorem chainP_fst_succ (f g : Nat → Int) (m k : Nat) :
    (chainP f g m (k + 1)).1 = (chainP f g m k).2 := rfl

/-- The invariant holds as long as the leading coefficients met so far are nonzero. -/
theorem inv_upto (f g : Nat → Int) (m : Nat) (hm : 2 ≤ m)
    (hf : ∀ e, m < e → f e = 0) (hg : ∀ e, m - 1 < e → g e = 0) :
    ∀ k, k + 1 ≤ m → (∀ k', k' < k → (chainP f g m k').2 (m - (k' + 1)) ≠ 0) → Inv f g m k
  | 0, _, _ => inv_zero f g m hm hf hg
  | k + 1, hk, hL => by
    have ih := inv_upto f g m hm hf hg k (by omega) (fun k' hk' => hL k' (by omega))
    apply inv_succ f g m k ih (by omega) (hL k (by omega))
    intro hk1
    obtain ⟨k0, rfl⟩ : ∃ k0, k = k0 + 1 := ⟨k - 1, by omega⟩
    rw [chainP_fst_succ, show m - (k0 + 1 + 1) + 1 = m - (k0 + 1) by omega]
    exact hL k0 (by omega)

/-- Every polynomial of the chain from `F_2` on is a subresultant of `(f, g)`. -/
theorem chain_val (f g : Nat → Int) (m : Nat) (hm : 2 ≤ m)
    (hf : ∀ e, m < e → f e = 0) (hg : ∀ e, m - 1 < e → g e = 0) (k : Nat) (hk : k + 1 ≤ m)
    (hk1 : 1 ≤ k) (hL : ∀ k', k' < k → (chainP f g m k').2 (m - (k' + 1)) ≠ 0) :
    ∀ i, i ≤ m - (k + 1) → (chainP f g m k).2 i = sres f g m (m - 1) (m - (k + 1)) i true :=
  (inv_upto f g m hm hf hg k hk hL).val hk1

theorem chain_deg (f g : Nat → Int) (m : Nat) (hm : 2 ≤ m)
    (hf : ∀ e, m < e → f e = 0) (hg : ∀ e, m - 1 < e → g e = 0) (k : Nat) (hk : k + 1 ≤ m)
    (hL : ∀ k', k' < k → (chainP f g m k').2 (m - (k' + 1)) ≠ 0) :
    ∀ e, m - (k + 1) < e → (chainP f g m k).2 e = 0 :=
  (inv_upto f g m hm hf hg k hk hL).degB

/-- Exactness of the division at every step after the first. -/
theorem chain_exact (f g : Nat → Int) (m : Nat) (hm : 2 ≤ m)
    (hf : ∀ e, m < e → f e = 0) (hg : ∀ e, m - 1 < e → g e = 0) (k : Nat) (hk : k + 2 ≤ m)
    (hk1 : 1 ≤ k) (hL : ∀ k', k' ≤ k → (chainP f g m k').2 (m - (k' + 1)) ≠ 0) :
    ∀ e, premF (chainP f g m k).1 (chainP f g m k).2 (m - (k + 1)) e =
      ((chainP f g m k).1 (m - (k + 1) + 1) * (chainP f g m k).1 (m - (k + 1) + 1)) *
        (chainP f g m (k + 1)).2 e := by
  have hI := inv_upto f g m hm hf hg k (by omega) (fun k' hk' => hL k' (by omega))
  have hI1 := inv_upto f g m hm hf hg (k + 1) (by omega) (fun k' hk' => hL k' (by omega))
  obtain ⟨k0, rfl⟩ : ∃ k0, k = k0 + 1 := ⟨k - 1, by omega⟩
  have ha : (chainP f g m (k0 + 1)).1 (m - (k0 + 1 + 1) + 1) ≠ 0 := by
    rw [chainP_fst_succ, show m - (k0 + 1 + 1) + 1 = m - (k0 + 1) by omega]
    exact hL k0 (by omega)
  have hEx := step_exact f g m (k0 + 1) hI (by omega) (hL (k0 + 1) (by omega)) (fun _ => ha)
  intro e
  by_cases he : e ≤ m - (k0 + 1 + 1) - 1
  · rw [hEx e he, if_neg (by omega), sq_eq, hI1.val (by omega) e (by omega),
      show m - (k0 + 1 + 1 + 1) = m - (k0 + 1 + 1) - 1 by omega]
  · have h1 : premF (chainP f g m (k0 + 1)).1 (chainP f g m (k0 + 1)).2 (m - (k0 + 1 + 1)) e = 0 := by
      unfold premF; rw [if_neg (by omega)]
    rw [h1, hI1.degB e (by omega)]; simp

end V9

/-!
# The chain functions run the specification's normal PRS

`toL P n` is the high-to-low coefficient list of a degree-`n` polynomial `P : Nat → Int`.
When every leading coefficient of the chain is nonzero, the specification's `normalResultant`
on `toL f m`, `toL g (m-1)` returns the constant of the last chain polynomial
(`normalResultant_chain`). The pseudo-remainder step is `prem_eq'`: unlike v7's `prem_eq` it
needs no `c₁ ≠ 0` (a zero `c₁` is trimmed and the second stage is a plain scaling).
-/

namespace V9

/-! ## From v7 (identical copies) -/

def r2 (LG LF C1 : Int) : List Int → List Int → List Int
  | X :: Xs, Z :: Zs => (LG * (LG * X - LF * Zs.headD 0) - C1 * Z) :: r2 LG LF C1 Xs Zs
  | _, _ => []

theorem cancel_r2 (LG LF C1 : Int) : ∀ Xs Zs : List Int, Xs.length = Zs.length →
    cancelPseudoLeading LG C1 (cancelPseudoLeading LG LF Xs Zs.tail) Zs = r2 LG LF C1 Xs Zs
  | [], _, _ => by simp [cancelPseudoLeading, r2]
  | _ :: _, [], h => by simp at h
  | X :: Xs, Z :: Zs, h => by
    have ih := cancel_r2 LG LF C1 Xs Zs (by simpa using h)
    cases Zs with
    | nil =>
      cases Xs with
      | nil => simp [cancelPseudoLeading, r2]
      | cons _ _ => simp at h
    | cons Z' Zs' =>
      simp only [List.tail_cons] at ih ⊢
      simp only [cancelPseudoLeading, r2, List.headD_cons]
      rw [← ih]

theorem exactDivide_map (D : Int) (hD : D ≠ 0) : ∀ Qs : List Int,
    exactDividePolynomial D (Qs.map (fun q => q * D)) = some Qs
  | [] => rfl
  | q :: Qs => by
    simp only [List.map_cons, exactDividePolynomial]
    rw [exactDivide_map D hD Qs]
    simp [hD, Int.mul_emod_left, Int.mul_ediv_cancel _ hD]

theorem trim_cons (c : Int) (cs : List Int) (h : c ≠ 0) : trimLeading (c :: cs) = c :: cs := by
  cases c using Int.rec with
  | ofNat n => cases n with
    | zero => exact absurd rfl h
    | succ k => rfl
  | negSucc k => rfl

theorem cancel_length (a b : Int) : ∀ xs ys : List Int,
    (cancelPseudoLeading a b xs ys).length = xs.length
  | [], _ => by simp [cancelPseudoLeading]
  | x :: xs, [] => by simp [cancelPseudoLeading, cancel_length a b xs []]
  | x :: xs, y :: ys => by simp [cancelPseudoLeading, cancel_length a b xs ys]

theorem scale_one : ∀ l : List Int, scalePolynomial 1 l = l
  | [] => rfl
  | c :: cs => by simp [scalePolynomial, scale_one cs]

/-! ## The pseudo-remainder without `c₁ ≠ 0` -/

theorem cancel_zero (LG : Int) : ∀ R Zs : List Int, cancelPseudoLeading LG 0 R Zs = scalePolynomial LG R
  | [], _ => by cases ‹List Int› <;> rfl
  | r :: R, [] => by simp [cancelPseudoLeading, scalePolynomial, cancel_zero LG R []]
  | r :: R, z :: Zs => by simp [cancelPseudoLeading, scalePolynomial, cancel_zero LG R Zs]

theorem scale_length (c : Int) : ∀ l : List Int, (scalePolynomial c l).length = l.length
  | [] => rfl
  | _ :: l => by simp [scalePolynomial, scale_length c l]

theorem trimLeading_zero (cs : List Int) : trimLeading (0 :: cs) = trimLeading cs := rfl

theorem prem_eq' (lf f1 lg z0 : Int) (xs zs : List Int)
    (hlf : lf ≠ 0) (hlg : lg ≠ 0) (hlen : xs.length = zs.length + 1)
    (hr2 : (r2 lg lf (lg * f1 - lf * z0) xs (z0 :: zs)).headD 0 ≠ 0) :
    pseudoRemainder (lf :: f1 :: xs) (lg :: z0 :: zs)
      = some (r2 lg lf (lg * f1 - lf * z0) xs (z0 :: zs)) := by
  by_cases hc1 : lg * f1 - lf * z0 = 0
  · -- `c₁ = 0`: the first stage leaves a polynomial one shorter, scaled once by `lg`
    have hR2 : cancelPseudoLeading lg (lg * f1 - lf * z0) (cancelPseudoLeading lg lf xs zs) (z0 :: zs)
        = r2 lg lf (lg * f1 - lf * z0) xs (z0 :: zs) :=
      cancel_r2 lg lf _ xs (z0 :: zs) (by simpa using hlen)
    rw [hc1, cancel_zero] at hR2
    rw [hc1] at hr2 ⊢
    rw [← hR2] at hr2 ⊢
    generalize hR : cancelPseudoLeading lg lf xs zs = R at hR2 hr2 ⊢
    have hRl : R.length = zs.length + 1 := by rw [← hR, cancel_length]; exact hlen
    obtain ⟨r0, rt, rfl⟩ : ∃ r0 rt, R = r0 :: rt := by
      cases R with
      | nil => simp at hRl
      | cons r0 rt => exact ⟨r0, rt, rfl⟩
    simp only [scalePolynomial, List.headD_cons] at hr2
    have hr0 : r0 ≠ 0 := by intro h; apply hr2; rw [h]; simp
    have hR1 : cancelPseudoLeading lg lf (f1 :: xs) (z0 :: zs) = (lg * f1 - lf * z0) :: (r0 :: rt) := by
      rw [← hR]; rfl
    unfold pseudoRemainder
    simp only [trim_cons lf _ hlf, trim_cons lg _ hlg, List.isEmpty_cons, Bool.false_eq_true,
      if_false, List.length_cons]
    rw [if_neg (by omega), show xs.length + 1 + 1 - (zs.length + 1 + 1) + 1 = 2 by omega]
    rw [show xs.length + 1 + 1 + 1 = (zs.length + 3) + 1 by omega]
    simp only [pseudoRemainderGo, trim_cons lf _ hlf, List.length_cons, hR1, hc1,
      trimLeading_zero, trim_cons r0 rt hr0]
    simp only [List.length_cons] at hRl
    rw [if_neg (by omega), if_pos (by omega)]
    simp [scalePolynomial, Int.pow_one]
  · have hR1 : cancelPseudoLeading lg lf (f1 :: xs) (z0 :: zs)
        = (lg * f1 - lf * z0) :: cancelPseudoLeading lg lf xs zs := rfl
    have hR2 : cancelPseudoLeading lg (lg * f1 - lf * z0) (cancelPseudoLeading lg lf xs zs) (z0 :: zs)
        = r2 lg lf (lg * f1 - lf * z0) xs (z0 :: zs) :=
      cancel_r2 lg lf _ xs (z0 :: zs) (by simpa using hlen)
    have hl2 : (r2 lg lf (lg * f1 - lf * z0) xs (z0 :: zs)).length = zs.length + 1 := by
      rw [← hR2, cancel_length, cancel_length]; exact hlen
    obtain ⟨r0, rt, hr⟩ : ∃ r0 rt, r2 lg lf (lg * f1 - lf * z0) xs (z0 :: zs) = r0 :: rt := by
      cases h : r2 lg lf (lg * f1 - lf * z0) xs (z0 :: zs) with
      | nil => rw [h] at hl2; simp at hl2
      | cons r0 rt => exact ⟨r0, rt, rfl⟩
    rw [hr] at hr2 hl2 hR2 ⊢
    simp only [List.headD_cons] at hr2
    unfold pseudoRemainder
    simp only [trim_cons lf _ hlf, trim_cons lg _ hlg, List.isEmpty_cons, Bool.false_eq_true,
      if_false, List.length_cons]
    rw [if_neg (by omega), show xs.length + 1 + 1 - (zs.length + 1 + 1) + 1 = 2 by omega]
    rw [show xs.length + 1 + 1 + 1 = (zs.length + 3) + 1 by omega]
    simp only [pseudoRemainderGo, trim_cons lf _ hlf, List.length_cons, hR1, trim_cons _ _ hc1,
      cancel_length, hR2, trim_cons _ _ hr2]
    simp [hlen, scale_one]
    simp only [List.length_cons] at hl2
    rw [if_neg (by omega), if_pos (by omega)]

/-! ## Coefficient lists of chain functions -/

/-- High-to-low coefficients `P n, …, P 0`. -/
def toL (P : Nat → Int) : Nat → List Int
  | 0 => [P 0]
  | n + 1 => P (n + 1) :: toL P n

theorem toL_length (P : Nat → Int) : ∀ n, (toL P n).length = n + 1
  | 0 => rfl
  | n + 1 => by simp [toL, toL_length P n]

theorem toL_cons (P : Nat → Int) : ∀ n, toL P n = P n :: (toL P n).tail
  | 0 => rfl
  | _ + 1 => rfl

theorem toL_head (P : Nat → Int) (n : Nat) : (toL P n).headD 0 = P n := by
  rw [toL_cons]; rfl

theorem toL_congr (P Q : Nat → Int) : ∀ n, (∀ e, e ≤ n → P e = Q e) → toL P n = toL Q n
  | 0, h => by simp [toL, h 0 (Nat.le_refl 0)]
  | n + 1, h => by
    simp only [toL]
    rw [h (n + 1) (Nat.le_refl _), toL_congr P Q n (fun e he => h e (by omega))]

theorem toL_map (P : Nat → Int) (c : Int) : ∀ n,
    (toL P n).map (fun q => q * c) = toL (fun e => P e * c) n
  | 0 => rfl
  | n + 1 => by simp [toL, toL_map P c n]

theorem r2_toL (LG LF C1 : Int) (X Z : Nat → Int) : ∀ n,
    r2 LG LF C1 (toL X n) (toL Z n)
      = toL (fun e => LG * (LG * X e - LF * (if 1 ≤ e then Z (e - 1) else 0)) - C1 * Z e) n
  | 0 => by simp [toL, r2]
  | n + 1 => by
    simp only [toL, r2]
    rw [r2_toL LG LF C1 X Z n, toL_head]
    simp

/-- One pseudo-remainder of chain functions: `A` of degree `d + 1`, `B` of degree `d`. -/
theorem prem_toL (A B : Nat → Int) (d : Nat) (hd : 1 ≤ d) (ha : A (d + 1) ≠ 0) (hb : B d ≠ 0)
    (hp : premF A B d (d - 1) ≠ 0) :
    pseudoRemainder (toL A (d + 1)) (toL B d) = some (toL (premF A B d) (d - 1)) := by
  obtain ⟨d0, rfl⟩ : ∃ d0, d = d0 + 1 := ⟨d - 1, by omega⟩
  have eA : toL A (d0 + 1 + 1) = A (d0 + 1 + 1) :: A (d0 + 1) :: toL A d0 := rfl
  have eB : toL B (d0 + 1) = B (d0 + 1) :: B d0 :: (toL B d0).tail := by
    show B (d0 + 1) :: toL B d0 = _; exact congrArg _ (toL_cons B d0)
  have hr2 : r2 (B (d0 + 1)) (A (d0 + 1 + 1)) (B (d0 + 1) * A (d0 + 1) - A (d0 + 1 + 1) * B d0)
      (toL A d0) (B d0 :: (toL B d0).tail) = toL (premF A B (d0 + 1)) d0 := by
    rw [← toL_cons B d0, r2_toL]
    apply toL_congr; intro e he
    simp only [premF, if_pos (show e < d0 + 1 by omega), Nat.add_sub_cancel]
    by_cases h1 : 1 ≤ e
    · simp only [h1, ↓reduceIte]; grind
    · simp only [h1, ↓reduceIte]; grind
  rw [eA, eB, prem_eq' _ _ _ _ _ _ ha hb (by rw [toL_length, List.length_tail, toL_length]; omega) (by
    rw [hr2, toL_head]; simpa using hp), hr2]
  simp

/-! ## The whole chain is the specification's normal PRS -/

theorem chain_first (f g : Nat → Int) (m : Nat) : (chainP f g m 1).2 = premF f g (m - 1) := by
  funext e; simp [chainP, nextC]

theorem chain_succ (f g : Nat → Int) (m k : Nat) :
    chainP f g m (k + 1) = ((chainP f g m k).2,
      nextC (chainP f g m k).1 (chainP f g m k).2 (m - (k + 1)) (k == 0)) := rfl

/-- One step of `normalResultantGo` on chain functions: `premF A B d = s · C` with `s = 1` on the
initial step and `s = lc(A)²` after it. -/
theorem go_step (fuel : Nat) (initial : Bool) (A B C : Nat → Int) (d : Nat) (hd : 1 ≤ d)
    (hA : A (d + 1) ≠ 0) (hB : B d ≠ 0) (hC : C (d - 1) ≠ 0)
    (hP : ∀ e, premF A B d e = (if initial then 1 else A (d + 1) * A (d + 1)) * C e) :
    normalResultantGo (fuel + 1) initial (toL A (d + 1)) (toL B d) =
      if d = 1 then some (C 0) else normalResultantGo fuel false (toL B d) (toL C (d - 1)) := by
  have hAA : A (d + 1) * A (d + 1) ≠ 0 := Int.mul_ne_zero hA hA
  have hp : premF A B d (d - 1) ≠ 0 := by
    rw [hP]; cases initial
    · exact Int.mul_ne_zero hAA hC
    · simpa using hC
  have hdiv : (if initial then some (toL (premF A B d) (d - 1))
      else exactDividePolynomial ((toL A (d + 1)).headD 0 ^ 2) (toL (premF A B d) (d - 1)))
        = some (toL C (d - 1)) := by
    cases initial
    · simp only [Bool.false_eq_true, ↓reduceIte, toL_head]
      have e1 : toL (premF A B d) (d - 1) = (toL C (d - 1)).map (fun q => q * A (d + 1) ^ 2) := by
        rw [toL_map]; apply toL_congr; intro e _
        rw [hP, sq_eq]; simp only [Bool.false_eq_true, ↓reduceIte]; exact Int.mul_comm _ _
      rw [e1, exactDivide_map _ (by rw [sq_eq]; exact hAA)]
    · simp only [↓reduceIte]
      congr 1; apply toL_congr; intro e _; rw [hP]; simp
  rw [normalResultantGo.eq_def]
  simp only
  rw [prem_toL A B d hd hA hB hp]
  simp only
  rw [hdiv]
  simp only
  obtain ⟨d1, rfl⟩ : ∃ d1, d = d1 + 1 := ⟨d - 1, by omega⟩
  cases d1 with
  | zero =>
    rw [show (0 + 1 - 1 : Nat) = 0 from rfl] at hC ⊢
    have e0 : toL C 0 = [C 0] := rfl
    rw [e0, trim_cons _ _ hC]
    rfl
  | succ d2 =>
    simp only [show d2 + 1 + 1 - 1 = d2 + 1 by omega] at hC ⊢
    have eC : toL C (d2 + 1) = C (d2 + 1) :: C d2 :: (toL C d2).tail := by
      show C (d2 + 1) :: toL C d2 = _; exact congrArg _ (toL_cons C d2)
    rw [eC, trim_cons _ _ hC]
    simp only [List.length_cons, List.length_tail, toL_length]
    rw [if_pos (by simp), if_neg (by omega)]

theorem normalGo_chain (f g : Nat → Int) (m : Nat) (hm : 2 ≤ m)
    (hf : ∀ e, m < e → f e = 0) (hg : ∀ e, m - 1 < e → g e = 0) (hf0 : f m ≠ 0)
    (hL : ∀ k', k' ≤ m - 1 → (chainP f g m k').2 (m - (k' + 1)) ≠ 0) :
    ∀ r k fuel, k + r + 2 = m → r + 1 ≤ fuel →
      normalResultantGo fuel (k == 0) (toL (chainP f g m k).1 (m - k)) (toL (chainP f g m k).2 (m - k - 1))
        = some ((chainP f g m (m - 1)).2 0) := by
  intro r
  induction r with
  | zero => ?_
  | succ r ih => ?_
  all_goals
    intro k fuel hkr hfuel
    obtain ⟨fuel', rfl⟩ : ∃ fuel', fuel = fuel' + 1 := ⟨fuel - 1, by omega⟩
    have hm1 : m - k = (m - k - 1) + 1 := by omega
    have hA : (chainP f g m k).1 (m - k - 1 + 1) ≠ 0 := by
      cases k with
      | zero => rw [← hm1]; simpa [chainP] using hf0
      | succ k0 =>
        rw [chainP_fst_succ, show m - (k0 + 1) - 1 + 1 = m - (k0 + 1) by omega]
        exact hL k0 (by omega)
    have hB : (chainP f g m k).2 (m - k - 1) ≠ 0 := by
      rw [show m - k - 1 = m - (k + 1) by omega]; exact hL k (by omega)
    have hC : (chainP f g m (k + 1)).2 (m - k - 1 - 1) ≠ 0 := by
      rw [show m - k - 1 - 1 = m - (k + 1 + 1) by omega]; exact hL (k + 1) (by omega)
    have hP : ∀ e, premF (chainP f g m k).1 (chainP f g m k).2 (m - k - 1) e =
        (if (k == 0) then 1 else (chainP f g m k).1 (m - k - 1 + 1) * (chainP f g m k).1 (m - k - 1 + 1)) *
          (chainP f g m (k + 1)).2 e := by
      intro e
      cases k with
      | zero =>
        simp only [beq_self_eq_true, ↓reduceIte, Int.one_mul]
        rw [chain_first]; simp [chainP]
      | succ k0 =>
        simp only [Nat.add_one_ne_zero, beq_iff_eq, ↓reduceIte]
        rw [show m - (k0 + 1) - 1 = m - (k0 + 1 + 1) by omega]
        exact chain_exact f g m hm hf hg (k0 + 1) (by omega) (by omega) (fun k' hk' => hL k' (by omega)) e
    have e1 : toL (chainP f g m k).1 (m - k) = toL (chainP f g m k).1 (m - k - 1 + 1) := congrArg _ hm1
    rw [e1, go_step fuel' (k == 0) _ _ _ (m - k - 1) (by omega) hA hB hC hP]
  · rw [if_pos (by omega)]
    rw [show m - 1 = k + 1 by omega]
  · rw [if_neg (by omega)]
    have := ih (k + 1) fuel' (by omega) (by omega)
    rw [chainP_fst_succ, show m - (k + 1) = m - k - 1 by omega] at this
    simpa using this

/-- The specification's normal resultant of the chain's first two polynomials. -/
theorem normalResultant_chain (f g : Nat → Int) (m : Nat) (hm : 2 ≤ m)
    (hf : ∀ e, m < e → f e = 0) (hg : ∀ e, m - 1 < e → g e = 0) (hf0 : f m ≠ 0)
    (hL : ∀ k', k' ≤ m - 1 → (chainP f g m k').2 (m - (k' + 1)) ≠ 0) :
    normalResultant (toL f m) (toL g (m - 1)) = some ((chainP f g m (m - 1)).2 0) := by
  have hg0 : g (m - 1) ≠ 0 := by simpa [chainP] using hL 0 (by omega)
  have h := normalGo_chain f g m hm hf hg hf0 hL (m - 2) 0 (m + 1) (by omega) (by omega)
  simp only [chainP, beq_self_eq_true, Nat.sub_zero] at h
  unfold normalResultant
  have t1 : trimLeading (toL f m) = toL f m := by rw [toL_cons f m, trim_cons _ _ hf0]
  have t2 : trimLeading (toL g (m - 1)) = toL g (m - 1) := by rw [toL_cons g (m - 1), trim_cons _ _ hg0]
  have hne : (toL g (m - 1)).isEmpty = false := by rw [toL_cons]; rfl
  simp only [t1, t2, hne, toL_length, Bool.not_false, Bool.and_true]
  rw [if_pos (by simp; omega), show m - 1 + 1 + 1 = m + 1 by omega]
  exact h

end V9

/-!
# Size certificates for the D5 band

Every chain coefficient is a subresultant determinant (`chain_val`). With entry bounds from the
specification's coefficient widths and integer potentials `u, v` (the dual of a max-weight
assignment) with `bound(r,c) · 2^K ≤ 2^(u_r) · 2^(v_c)`, the permutation bound `det_bound` gives
`|S_j coefficient| · 2^(K N) ≤ N! · 2^(Σu + Σv) < 2^(q-1) · 2^(K N)`. The potentials were
computed offline (`gen/cert.py`); here they are only checked (`certOK`, by `decide`).
-/

namespace V9

/-! ## Entry bounds -/

def shcN (P : Nat → Nat) (t e : Nat) : Nat := if t ≤ e then P (e - t) else 0

/-- `sxM` (rows of `X` first) on natural-number bound functions. -/
def sxMN (X Y : Nat → Nat) (p q j i : Nat) : Nat → Nat → Nat := fun r c =>
  if r < q - j then shcN X (q - j - 1 - r) (colDeg p q j i c)
  else shcN Y (p - j - 1 - (r - (q - j))) (colDeg p q j i c)

theorem sxM_abs (X Y : Nat → Int) (Xb Yb : Nat → Nat) (hX : ∀ e, (X e).natAbs ≤ Xb e)
    (hY : ∀ e, (Y e).natAbs ≤ Yb e) (p q j i r c : Nat) :
    (sxM X Y p q j i true r c).natAbs ≤ sxMN Xb Yb p q j i r c := by
  unfold sxM sxMN shc shcN
  simp only [↓reduceIte]
  split
  · split
    · exact hX _
    · simp
  · split
    · exact hY _
    · simp

theorem colDeg_last (p q j i c : Nat) (hc : c + 1 < p + q - 2 * j) : colDeg p q j i c = colDeg p q j 0 c := by
  unfold colDeg; rw [if_pos hc, if_pos hc]

/-- Bounds on the D5 coefficients: `|f_e| ≤ 2^(w(24-e) - 1)`, `f_24 = 1`; `g_e = (e+1) f_(e+1)`. -/
def FbN (e : Nat) : Nat :=
  if e = 24 then 1 else if e < 24 then 2 ^ (coefficientWidth 3484 (24 - e) - 1) else 0

def GbN (e : Nat) : Nat := if e < 24 then (e + 1) * FbN (e + 1) else 0

/-! ## The checker -/

def allBelow : Nat → (Nat → Bool) → Bool
  | 0, _ => true
  | n + 1, p => allBelow n p && p n

theorem allBelow_spec : ∀ (n : Nat) (p : Nat → Bool), allBelow n p = true → ∀ i, i < n → p i = true
  | 0, _, _, i, hi => absurd hi (Nat.not_lt_zero i)
  | n + 1, p, h, i, hi => by
    simp only [allBelow, Bool.and_eq_true] at h
    by_cases hin : i = n
    · subst hin; exact h.2
    · exact allBelow_spec n p h.1 i (by omega)

def pw (l : List Nat) (r : Nat) : Nat := 2 ^ l.getD r 0

def entryOK (j i K : Nat) (u v : List Nat) (r c : Nat) : Bool :=
  Nat.ble (sxMN FbN GbN 24 23 j i r c * 2 ^ K) (pw u r * pw v c)

def certOK (j N K q : Nat) (u v : List Nat) : Bool :=
  (N == 24 + 23 - 2 * j) && (j < 23) &&
  allBelow N (fun r => allBelow (N - 1) (fun c => entryOK j 0 K u v r c)) &&
  allBelow (j + 1) (fun i => allBelow N (fun r => entryOK j i K u v r (N - 1))) &&
  Nat.blt (fact N * prodN N (pw u) * prodN N (pw v)) (2 ^ (q - 1) * (2 ^ K) ^ N)

theorem certOK_spec (j N K q : Nat) (u v : List Nat) (h : certOK j N K q u v = true) :
    N = 24 + 23 - 2 * j ∧ j < 23 ∧
    (∀ i, i ≤ j → ∀ r c, r < N → c < N → sxMN FbN GbN 24 23 j i r c * 2 ^ K ≤ pw u r * pw v c) ∧
    fact N * prodN N (pw u) * prodN N (pw v) < 2 ^ (q - 1) * (2 ^ K) ^ N := by
  simp only [certOK, Bool.and_eq_true, beq_iff_eq, decide_eq_true_eq, Nat.blt_eq] at h
  obtain ⟨⟨⟨⟨hN, hj⟩, h1⟩, h2⟩, h3⟩ := h
  refine ⟨hN, hj, ?_, h3⟩
  intro i hi r c hr hc
  by_cases hcl : c + 1 < N
  · have := allBelow_spec _ _ (allBelow_spec _ _ h1 r hr) c (by omega)
    simp only [entryOK, Nat.ble_eq] at this
    have e : sxMN FbN GbN 24 23 j i r c = sxMN FbN GbN 24 23 j 0 r c := by
      unfold sxMN; rw [colDeg_last 24 23 j i c (by omega)]
    rw [e]; exact this
  · have := allBelow_spec _ _ (allBelow_spec _ _ h2 i (by omega)) r hr
    simp only [entryOK, Nat.ble_eq] at this
    rw [show c = N - 1 by omega]; exact this

/-- A certified subresultant coefficient is below `2^(q-1)`. -/
theorem sres_lt (f g : Nat → Int) (hf : ∀ e, (f e).natAbs ≤ FbN e) (hg : ∀ e, (g e).natAbs ≤ GbN e)
    (j N K q : Nat) (u v : List Nat) (h : certOK j N K q u v = true) :
    ∀ i, i ≤ j → (sres f g 24 23 j i true).natAbs < 2 ^ (q - 1) := by
  obtain ⟨hN, _, hent, hfin⟩ := certOK_spec j N K q u v h
  intro i hi
  have hb := det_bound N (sxM f g 24 23 j i true) (pw u) (pw v) (2 ^ K) (by
    intro r c hr hc
    exact Nat.le_trans (Nat.mul_le_mul_right _ (sxM_abs f g FbN GbN hf hg 24 23 j i r c)) (hent i hi r c hr hc))
  unfold sres
  rw [← hN]
  exact Nat.lt_of_mul_lt_mul_right (Nat.lt_of_le_of_lt hb hfin)

/-! ## The D5 certificates (from `gen/cert.py`) -/

def certD5 : List (Nat × Nat × Nat × Nat × List Nat × List Nat) := [
  (22, 3, 142, 3500, [142, 147, 0], [0, 150, 3483]),
  (21, 5, 292, 3957, [292, 142, 297, 147, 0], [0, 150, 300, 448, 3633]),
  (20, 7, 437, 4711, [437, 289, 142, 442, 294, 147, 0], [0, 150, 298, 446, 593, 740, 3778]),
  (19, 9, 584, 5759, [584, 436, 289, 142, 589, 441, 294, 147, 0], [0, 150, 298, 446, 593, 740, 887, 1034, 3925]),
  (18, 11, 731, 7102, [731, 583, 436, 289, 142, 736, 588, 441, 294, 147, 0], [0, 150, 298, 446, 593, 740, 887, 1034, 1181, 1328, 4072]),
  (17, 13, 878, 8739, [878, 730, 583, 436, 289, 142, 883, 735, 588, 441, 294, 147, 0], [0, 150, 298, 446, 593, 740, 887, 1034, 1181, 1328, 1475, 1622, 4219]),
  (16, 15, 1025, 10671, [1025, 875, 728, 581, 434, 287, 142, 1030, 880, 733, 586, 439, 292, 146, 0], [0, 150, 300, 448, 595, 742, 889, 1036, 1183, 1330, 1477, 1624, 1770, 1916, 4366]),
  (15, 17, 1169, 12894, [1169, 1021, 874, 727, 580, 433, 287, 142, 1174, 1026, 879, 732, 585, 438, 292, 146, 0], [0, 150, 298, 446, 593, 740, 887, 1034, 1181, 1328, 1475, 1622, 1768, 1914, 2060, 2206, 4510]),
  (14, 19, 1315, 15409, [1315, 1167, 1020, 873, 726, 579, 433, 288, 142, 1320, 1172, 1025, 878, 731, 584, 438, 292, 146, 0], [0, 150, 298, 446, 593, 740, 887, 1034, 1181, 1328, 1475, 1622, 1768, 1914, 2060, 2206, 2352, 2497, 4656]),
  (13, 21, 1461, 18216, [1461, 1313, 1166, 1019, 872, 725, 579, 433, 288, 142, 1466, 1318, 1171, 1024, 877, 730, 584, 438, 292, 146, 0], [0, 150, 298, 446, 593, 740, 887, 1034, 1181, 1328, 1475, 1622, 1768, 1914, 2060, 2206, 2352, 2498, 2643, 2789, 4802]),
  (12, 23, 1607, 21315, [1607, 1459, 1312, 1165, 1018, 871, 724, 578, 432, 286, 142, 1612, 1464, 1317, 1170, 1023, 876, 729, 583, 437, 291, 145, 0], [0, 150, 298, 446, 593, 740, 887, 1034, 1181, 1328, 1475, 1622, 1769, 1915, 2061, 2207, 2353, 2499, 2645, 2791, 2936, 3081, 4948]),
  (11, 25, 1751, 24703, [1751, 1603, 1455, 1308, 1161, 1014, 868, 723, 577, 431, 286, 142, 1756, 1608, 1460, 1313, 1166, 1019, 873, 727, 581, 435, 290, 145, 0], [0, 150, 298, 446, 594, 741, 888, 1035, 1182, 1329, 1476, 1623, 1769, 1915, 2061, 2207, 2353, 2498, 2644, 2790, 2935, 3080, 3225, 3370, 5092]),
  (10, 27, 1895, 28382, [1895, 1747, 1600, 1453, 1306, 1159, 1013, 868, 722, 576, 431, 286, 142, 1900, 1752, 1605, 1458, 1311, 1164, 1018, 872, 726, 580, 435, 290, 145, 0], [0, 150, 298, 446, 593, 740, 887, 1034, 1181, 1328, 1475, 1622, 1768, 1914, 2060, 2206, 2352, 2497, 2643, 2789, 2934, 3079, 3224, 3369, 3514, 3659, 5236]),
  (9, 29, 2040, 32350, [2040, 1892, 1745, 1598, 1451, 1304, 1158, 1012, 866, 721, 576, 431, 286, 141, 2045, 1897, 1750, 1603, 1456, 1309, 1163, 1017, 871, 725, 580, 435, 290, 145, 0], [0, 150, 298, 446, 593, 740, 887, 1034, 1181, 1328, 1475, 1622, 1768, 1914, 2060, 2206, 2352, 2498, 2644, 2789, 2934, 3079, 3224, 3369, 3514, 3659, 3804, 3949, 5382]),
  (8, 31, 2187, 36609, [2187, 2037, 1889, 1742, 1595, 1448, 1302, 1157, 1011, 865, 720, 575, 430, 285, 142, 2192, 2042, 1894, 1747, 1600, 1453, 1307, 1161, 1015, 869, 724, 579, 434, 289, 144, 0], [0, 150, 300, 448, 596, 743, 890, 1037, 1184, 1331, 1478, 1625, 1771, 1917, 2063, 2209, 2355, 2500, 2646, 2792, 2937, 3082, 3227, 3372, 3517, 3662, 3807, 3952, 4097, 4241, 5528]),
  (7, 33, 2328, 41156, [2328, 2180, 2033, 1886, 1739, 1592, 1446, 1300, 1154, 1009, 864, 719, 574, 429, 285, 142, 2333, 2185, 2038, 1891, 1744, 1597, 1451, 1305, 1159, 1013, 868, 723, 578, 433, 288, 144, 0], [0, 150, 298, 446, 593, 740, 887, 1034, 1181, 1328, 1475, 1622, 1768, 1914, 2060, 2206, 2352, 2498, 2644, 2789, 2934, 3079, 3224, 3369, 3514, 3659, 3804, 3949, 4094, 4238, 4382, 4526, 5669]),
  (6, 35, 2475, 45991, [2475, 2327, 2180, 2033, 1886, 1739, 1592, 1446, 1301, 1155, 1009, 864, 719, 574, 429, 285, 141, 2480, 2332, 2185, 2038, 1891, 1744, 1597, 1451, 1305, 1159, 1013, 868, 723, 578, 433, 288, 144, 0], [0, 150, 298, 446, 593, 740, 887, 1034, 1181, 1328, 1475, 1622, 1769, 1915, 2061, 2207, 2353, 2499, 2644, 2790, 2936, 3081, 3226, 3371, 3516, 3661, 3806, 3951, 4096, 4241, 4385, 4529, 4673, 4817, 5817]),
  (5, 37, 2617, 51115, [2617, 2469, 2322, 2175, 2028, 1881, 1734, 1588, 1442, 1296, 1151, 1006, 861, 716, 572, 428, 284, 142, 2622, 2474, 2327, 2180, 2033, 1886, 1739, 1593, 1447, 1301, 1155, 1010, 865, 720, 575, 431, 287, 144, 0], [0, 150, 298, 446, 593, 740, 887, 1034, 1181, 1328, 1475, 1622, 1769, 1915, 2061, 2207, 2353, 2499, 2645, 2791, 2936, 3081, 3226, 3371, 3516, 3661, 3806, 3951, 4096, 4240, 4384, 4528, 4672, 4816, 4959, 5103, 5958]),
  (4, 39, 2759, 56524, [2759, 2611, 2464, 2317, 2170, 2023, 1877, 1731, 1586, 1440, 1295, 1150, 1005, 860, 716, 572, 428, 284, 142, 2764, 2616, 2469, 2322, 2175, 2028, 1882, 1736, 1590, 1444, 1299, 1154, 1009, 864, 719, 575, 431, 287, 144, 0], [0, 150, 298, 446, 593, 740, 887, 1034, 1181, 1328, 1475, 1622, 1768, 1914, 2060, 2206, 2352, 2498, 2643, 2789, 2934, 3079, 3224, 3369, 3514, 3659, 3804, 3949, 4094, 4238, 4382, 4526, 4670, 4814, 4958, 5101, 5245, 5388, 6100]),
  (3, 41, 2902, 62222, [2902, 2754, 2607, 2460, 2313, 2166, 2020, 1874, 1728, 1583, 1438, 1293, 1148, 1003, 858, 714, 570, 426, 283, 142, 2907, 2759, 2612, 2465, 2318, 2171, 2025, 1879, 1733, 1587, 1442, 1297, 1152, 1007, 862, 718, 573, 429, 286, 143, 0], [0, 150, 298, 446, 593, 740, 887, 1034, 1181, 1328, 1475, 1622, 1768, 1914, 2060, 2206, 2352, 2498, 2644, 2789, 2934, 3079, 3224, 3369, 3514, 3659, 3804, 3949, 4094, 4238, 4383, 4527, 4671, 4815, 4959, 5102, 5246, 5389, 5532, 5675, 6243]),
  (2, 43, 3049, 68205, [3049, 2901, 2753, 2606, 2459, 2312, 2165, 2019, 1873, 1728, 1582, 1437, 1292, 1147, 1002, 858, 714, 570, 426, 283, 142, 3054, 2906, 2758, 2611, 2464, 2317, 2170, 2024, 1878, 1732, 1586, 1441, 1296, 1151, 1006, 861, 717, 573, 429, 286, 142, 0], [0, 150, 298, 446, 594, 741, 888, 1035, 1182, 1329, 1476, 1623, 1770, 1916, 2062, 2208, 2354, 2500, 2646, 2791, 2937, 3082, 3227, 3372, 3517, 3662, 3807, 3952, 4097, 4242, 4386, 4530, 4674, 4818, 4962, 5106, 5249, 5393, 5536, 5680, 5822, 5965, 6390]),
  (1, 45, 3186, 74473, [3186, 3038, 2891, 2744, 2597, 2450, 2304, 2158, 2012, 1867, 1722, 1577, 1432, 1287, 1143, 999, 855, 712, 568, 426, 283, 141, 3191, 3043, 2896, 2749, 2602, 2455, 2309, 2163, 2017, 1871, 1726, 1581, 1436, 1291, 1147, 1002, 858, 715, 571, 428, 285, 142, 0], [0, 150, 298, 446, 593, 740, 887, 1034, 1181, 1328, 1475, 1622, 1768, 1914, 2060, 2206, 2352, 2498, 2644, 2789, 2934, 3079, 3224, 3369, 3514, 3659, 3804, 3949, 4093, 4238, 4382, 4526, 4670, 4814, 4957, 5101, 5244, 5388, 5531, 5674, 5817, 5959, 6102, 6244, 6528]),
  (0, 47, 3332, 81025, [3332, 3182, 3034, 2887, 2740, 2593, 2446, 2300, 2154, 2009, 1864, 1719, 1574, 1429, 1285, 1141, 997, 853, 710, 567, 425, 283, 141, 3337, 3187, 3039, 2892, 2745, 2598, 2451, 2305, 2159, 2013, 1868, 1723, 1578, 1433, 1289, 1144, 1000, 856, 713, 570, 426, 284, 142, 0], [0, 150, 300, 448, 596, 743, 890, 1037, 1184, 1331, 1478, 1625, 1772, 1918, 2064, 2210, 2356, 2502, 2648, 2793, 2938, 3083, 3228, 3373, 3518, 3663, 3808, 3953, 4097, 4242, 4386, 4530, 4674, 4818, 4962, 5105, 5249, 5392, 5535, 5679, 5821, 5964, 6106, 6248, 6390, 6532, 6674])]

def certAll : List (Nat × Nat × Nat × Nat × List Nat × List Nat) → Bool
  | [] => true
  | (j, N, K, q, u, v) :: cs => certOK j N K q u v && certAll cs

theorem certD5_ok : certAll certD5 = true := by decide +kernel

end V9

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

/-!
# The low-part step computes the chain

`coef_spec`: one coefficient. The three products and the sign corrections give the numerator
times `inv²` modulo `M = 2^(q + 2sh)`; if that is `2^(2sh)·C` the low `q` bits after the shift are
the residue of `C`.
-/

namespace V9

theorem nadd (a b : Nat) : Nat.add a b = a + b := rfl
theorem nsub (a b : Nat) : Nat.sub a b = a - b := rfl
theorem nmul (a b : Nat) : Nat.mul a b = a * b := rfl
theorem nshl (a b : Nat) : Nat.shiftLeft a b = a * 2 ^ b := Nat.shiftLeft_eq a b
theorem nshr (a b : Nat) : Nat.shiftRight a b = a / 2 ^ b := Nat.shiftRight_eq_div_pow a b
theorem nmask (a k : Nat) : Nat.land a (2 ^ k - 1) = a % 2 ^ k := Nat.and_two_pow_sub_one_eq_mod a k

theorem sign_le (q : Nat) (x : Int) (hx : x.natAbs < 2 ^ q) : res (q + 1) x >>> q ≤ 1 := by
  rw [(res_val q x hx).1]; split <;> omega

theorem natCast_mod_pow (a k : Nat) : ((a % 2 ^ k : Nat) : Int) = (a : Int) % 2 ^ k := by
  rw [Int.natCast_emod, cast_two_pow]

/-- One coefficient of a low-part step. -/
theorem coef_spec (q a b sh2 : Nat) (m1 m2 m3 : Nat) (X Y Z C : Int)
    (hX : X.natAbs < 2 ^ a) (hY : Y.natAbs < 2 ^ b) (hZ : Z.natAbs < 2 ^ b)
    (hcong : MEq (2 ^ (q + sh2)) ((m1 : Int) * X + m2 * Y + m3 * Z) (2 ^ sh2 * C)) :
    coef m1 m2 m3 (m1 * 2 ^ (a + 1) % 2 ^ (q + sh2)) (m2 * 2 ^ (b + 1) % 2 ^ (q + sh2))
      (m3 * 2 ^ (b + 1) % 2 ^ (q + sh2)) (2 ^ (q + sh2) * 4) sh2 (2 ^ q - 1) a b
      (res (a + 1) X) (res (b + 1) Y) (res (b + 1) Z) = res q C := by
  obtain ⟨sX, vX⟩ := res_val a X hX
  obtain ⟨sY, vY⟩ := res_val b Y hY
  obtain ⟨sZ, vZ⟩ := res_val b Z hZ
  have bX := sign_le a X hX; have bY := sign_le b Y hY; have bZ := sign_le b Z hZ
  generalize res (a + 1) X = x at sX vX bX
  generalize res (b + 1) Y = y at sY vY bY
  generalize res (b + 1) Z = z at sZ vZ bZ
  generalize hM : 2 ^ (q + sh2) = M at hcong ⊢
  have hMpos : 0 < M := by rw [← hM]; exact Nat.two_pow_pos _
  unfold coef
  simp only [nadd, nsub, nmul, nshr, nmask]
  rw [← Nat.shiftRight_eq_div_pow x a, ← Nat.shiftRight_eq_div_pow y b, ← Nat.shiftRight_eq_div_pow z b]
  generalize x >>> a = s1 at sX vX bX ⊢
  generalize y >>> b = s2 at sY vY bY ⊢
  generalize z >>> b = s3 at sZ vZ bZ ⊢
  -- the corrections are below `3M`, so the subtraction is exact
  have hc1 := Nat.mod_lt (m1 * 2 ^ (a + 1)) hMpos
  have hc2 := Nat.mod_lt (m2 * 2 ^ (b + 1)) hMpos
  have hc3 := Nat.mod_lt (m3 * 2 ^ (b + 1)) hMpos
  have hCr : s1 * (m1 * 2 ^ (a + 1) % M) + s2 * (m2 * 2 ^ (b + 1) % M) + s3 * (m3 * 2 ^ (b + 1) % M)
      ≤ M * 4 := by
    have e1 : s1 * (m1 * 2 ^ (a + 1) % M) ≤ M := by
      rcases Nat.le_one_iff_eq_zero_or_eq_one.1 bX with h | h <;> rw [h] <;> omega
    have e2 : s2 * (m2 * 2 ^ (b + 1) % M) ≤ M := by
      rcases Nat.le_one_iff_eq_zero_or_eq_one.1 bY with h | h <;> rw [h] <;> omega
    have e3 : s3 * (m3 * 2 ^ (b + 1) % M) ≤ M := by
      rcases Nat.le_one_iff_eq_zero_or_eq_one.1 bZ with h | h <;> rw [h] <;> omega
    omega
  generalize hT : m1 * x + m2 * y + m3 * z + M * 4 -
      (s1 * (m1 * 2 ^ (a + 1) % M) + s2 * (m2 * 2 ^ (b + 1) % M) + s3 * (m3 * 2 ^ (b + 1) % M)) = T
  -- `T ≡ 2^sh2 · C (mod M)`
  have hTi : (T : Int) = m1 * x + m2 * y + m3 * z + M * 4 -
      (s1 * (m1 * 2 ^ (a + 1) % M) + s2 * (m2 * 2 ^ (b + 1) % M) + s3 * (m3 * 2 ^ (b + 1) % M) : Nat) := by
    rw [← hT, Int.ofNat_sub (by omega)]; push_cast; rfl
  have hMi : (M : Int) = 2 ^ (q + sh2) := by rw [← hM, cast_two_pow]
  have hcT : MEq M T (2 ^ sh2 * C) := by
    have k1 : MEq M ((m1 * 2 ^ (a + 1) % M : Nat) : Int) ((m1 : Int) * 2 ^ (a + 1)) := by
      rw [Int.natCast_emod]; push_cast; exact MEq.emod _ _
    have k2 : MEq M ((m2 * 2 ^ (b + 1) % M : Nat) : Int) ((m2 : Int) * 2 ^ (b + 1)) := by
      rw [Int.natCast_emod]; push_cast; exact MEq.emod _ _
    have k3 : MEq M ((m3 * 2 ^ (b + 1) % M : Nat) : Int) ((m3 : Int) * 2 ^ (b + 1)) := by
      rw [Int.natCast_emod]; push_cast; exact MEq.emod _ _
    generalize m1 * 2 ^ (a + 1) % M = c1 at k1 hTi
    generalize m2 * 2 ^ (b + 1) % M = c2 at k2 hTi
    generalize m3 * 2 ^ (b + 1) % M = c3 at k3 hTi
    obtain ⟨u1, hu1⟩ := k1; obtain ⟨u2, hu2⟩ := k2; obtain ⟨u3, hu3⟩ := k3
    have hsum : MEq M (T : Int) ((m1 : Int) * X + m2 * Y + m3 * Z) := by
      refine ⟨4 - s1 * u1 - s2 * u2 - s3 * u3, ?_⟩
      have ex : (x : Int) = X + s1 * 2 ^ (a + 1) := by omega
      have ey : (y : Int) = Y + s2 * 2 ^ (b + 1) := by omega
      have ez : (z : Int) = Z + s3 * 2 ^ (b + 1) := by omega
      rw [hTi]; push_cast
      rw [ex, ey, ez]
      grind
    exact hsum.trans (by rw [← hMi] at hcong; exact hcong)
  obtain ⟨t, ht⟩ := hcT
  -- shift and mask
  have hdiv : ((T / 2 ^ sh2 : Nat) : Int) = C + 2 ^ q * t := by
    rw [Int.natCast_ediv, cast_two_pow]
    have : (T : Int) = 2 ^ sh2 * (C + 2 ^ q * t) := by
      rw [hMi, Int.pow_add] at ht; grind
    rw [this, Int.mul_ediv_cancel_left _ (Int.ne_of_gt (two_pow_pos sh2))]
  apply Int.ofNat_inj.1
  rw [natCast_mod_pow, hdiv, res_cast, Int.add_mul_emod_self_left]

theorem res_zero_int (q : Nat) : res q 0 = 0 := by simp [res]

theorem zshr (n : Nat) : Nat.shiftRight 0 n = 0 := by rw [nshr, Nat.zero_div]

/-- The constant coefficient is `coef` with `y = 0`. -/
theorem coefL_eq (m1 m2 m3 c1 c2 c3 K sh2 qm qhA qhB x z : Nat) :
    coefL m1 m3 c1 c3 K sh2 qm qhA qhB x z = coef m1 m2 m3 c1 c2 c3 K sh2 qm qhA qhB x 0 z := by
  unfold coefL coef
  simp only [nadd, nsub, nmul, Nat.mul_zero, Nat.add_zero, zshr, Nat.zero_mul]

/-! ## Lists of residues -/

def toN (q : Nat) (P : Nat → Int) (n : Nat) : List Nat := (toL P n).map (res q)

theorem toN_zero (q : Nat) (P : Nat → Int) : toN q P 0 = [res q (P 0)] := rfl
theorem toN_succ (q : Nat) (P : Nat → Int) (n : Nat) : toN q P (n + 1) = res q (P (n + 1)) :: toN q P n := rfl
theorem toN_cons (q : Nat) (P : Nat → Int) (n : Nat) : toN q P n = res q (P n) :: (toN q P n).tail := by
  cases n <;> rfl
theorem toN_length (q : Nat) (P : Nat → Int) (n : Nat) : (toN q P n).length = n + 1 := by
  simp [toN, toL_length]

theorem hd0_cons (a : Nat) (l : List Nat) : hd0 (a :: l) = a := rfl

theorem lqs_spec (m1 m2 m3 c1 c2 c3 K sh2 qm qhA qhB qA qB q : Nat) (A B C : Nat → Int) :
    ∀ n, (∀ e, 1 ≤ e → e ≤ n → coef m1 m2 m3 c1 c2 c3 K sh2 qm qhA qhB (res qA (A e)) (res qB (B (e - 1)))
        (res qB (B e)) = res q (C e)) →
      coefL m1 m3 c1 c3 K sh2 qm qhA qhB (res qA (A 0)) (res qB (B 0)) = res q (C 0) →
      lqs m1 m2 m3 c1 c2 c3 K sh2 qm qhA qhB (toN qA A n) (toN qB B n) = toN q C n
  | 0, _, h0 => by rw [toN_zero, toN_zero, toN_zero]; simp only [lqs, h0]
  | n + 1, h, h0 => by
    rw [toN_succ qA A n, toN_succ qB B n, toN_succ q C n, toN_cons qA A n, toN_cons qB B n]
    simp only [lqs]
    rw [← toN_cons, ← toN_cons, lqs_spec m1 m2 m3 c1 c2 c3 K sh2 qm qhA qhB qA qB q A B C n
      (fun e he1 he2 => h e he1 (by omega)) h0]
    have := h (n + 1) (by omega) (Nat.le_refl _)
    rw [Nat.add_sub_cancel] at this
    rw [this]

/-! ## Newton's inverse -/

def ladderOK : Nat → List Nat → Nat → Bool
  | p, [], t => p == t
  | p, p' :: ps, t => Nat.ble p' (2 * p) && ladderOK p' ps t

theorem newton_step (a x p p' : Nat) (hp : p' ≤ 2 * p) (h : MEq (2 ^ p) ((a : Int) * x) 1) :
    MEq (2 ^ p') ((a : Int) * (Nat.land (Nat.mul x (Nat.sub (Nat.add (Nat.sub (Nat.shiftLeft 1 p') 1) 3)
      (Nat.land (Nat.mul (Nat.land a (Nat.sub (Nat.shiftLeft 1 p') 1)) x) (Nat.sub (Nat.shiftLeft 1 p') 1))))
      (Nat.sub (Nat.shiftLeft 1 p') 1) : Nat)) 1 := by
  have e1 : Nat.shiftLeft 1 p' = 2 ^ p' := by rw [nshl, Nat.one_mul]
  simp only [e1, nmask, nmul, nadd, nsub]
  have hP : 0 < 2 ^ p' := Nat.two_pow_pos p'
  generalize ht : a % 2 ^ p' * x % 2 ^ p' = t
  have htl : t < 2 ^ p' := by rw [← ht]; exact Nat.mod_lt _ hP
  have hsub : 2 ^ p' - 1 + 3 - t = 2 ^ p' + 2 - t := by omega
  rw [hsub]
  -- `t ≡ a·x`
  have hta : MEq (2 ^ p') (t : Int) ((a : Int) * x) := by
    rw [← ht, Int.natCast_emod, Int.natCast_mul, Int.natCast_emod, cast_two_pow]
    exact (MEq.emod _ _).trans ((MEq.emod _ _).mul (MEq.refl _ _))
  obtain ⟨δ, hδ⟩ := h
  have hxx : MEq (2 ^ p') ((a : Int) * ((x * (2 ^ p' + 2 - t) % 2 ^ p' : Nat) : Int))
      ((a : Int) * x * (2 - (a : Int) * x)) := by
    rw [Int.natCast_emod, cast_two_pow]
    refine (MEq.mul_left _ (MEq.emod _ _)).trans ?_
    rw [Int.natCast_mul, Int.ofNat_sub (by omega)]
    push_cast
    have := (MEq.refl (2 ^ p' : Int) ((a : Int) * x)).mul
      ((MEq.add_mul (2 ^ p' : Int) 2 1).sub hta)
    refine MEq.trans ?_ this
    exact ⟨0, by grind⟩
  refine hxx.trans ?_
  -- `a·x·(2 − a·x) = 1 − (2^p δ)²`
  have hax : (a : Int) * x = 1 + 2 ^ p * δ := by omega
  rw [hax]
  refine ⟨-(2 ^ (2 * p - p') * δ * δ), ?_⟩
  have e2 : (2 : Int) ^ p * 2 ^ p = 2 ^ p' * 2 ^ (2 * p - p') := by
    rw [← Int.pow_add, ← Int.pow_add]; congr 1; omega
  grind

theorem newton_spec (a : Nat) : ∀ (ps : List Nat) (x p t : Nat), ladderOK p ps t = true →
    MEq (2 ^ p) ((a : Int) * x) 1 → MEq (2 ^ t) ((a : Int) * newton a x ps) 1
  | [], x, p, t, h, hx => by
    simp only [ladderOK, beq_iff_eq] at h; subst h; exact hx
  | p' :: ps, x, p, t, h, hx => by
    simp only [ladderOK, Bool.and_eq_true, Nat.ble_eq] at h
    exact newton_spec a ps _ p' t h.2 (newton_step a x p p' h.1 hx)

theorem odd_sq (o : Nat) (h : o % 2 = 1) : MEq (2 ^ 3) ((o : Int) * o) 1 := by
  have h8 : (o * o) % 8 = 1 := by
    rw [Nat.mul_mod]
    have h1 : o % 8 % 2 = 1 := by omega
    have h2 : o % 8 < 8 := Nat.mod_lt _ (by decide)
    generalize o % 8 = r at h1 h2
    have : r = 1 ∨ r = 3 ∨ r = 5 ∨ r = 7 := by omega
    rcases this with rfl | rfl | rfl | rfl <;> rfl
  refine ⟨(o * o / 8 : Nat), ?_⟩
  have := Nat.div_add_mod (o * o) 8
  push_cast; omega

/-! ## Per-step scalars -/

/-- Sign extension of a residue to a larger power-of-two modulus. -/
theorem ext_spec (b : Nat) (Y : Int) (hY : Y.natAbs < 2 ^ b) (M : Nat) (hM : 2 ^ (b + 1) ≤ M) :
    MEq M ((Nat.add (res (b + 1) Y) (Nat.mul (Nat.shiftRight (res (b + 1) Y) b) (Nat.sub M (Nat.shiftLeft 1 (b + 1)))) : Nat) : Int) Y := by
  obtain ⟨_, v⟩ := res_val b Y hY
  have e1 : Nat.shiftLeft 1 (b + 1) = 2 ^ (b + 1) := by rw [nshl, Nat.one_mul]
  have e2 : Nat.shiftRight (res (b + 1) Y) b = res (b + 1) Y >>> b := rfl
  rw [e1, e2]
  generalize res (b + 1) Y = u at v
  generalize u >>> b = s at v
  refine ⟨(s : Int), ?_⟩
  simp only [nadd, nmul, nsub]
  rw [Int.natCast_add, Int.natCast_mul, Int.ofNat_sub hM, cast_two_pow]
  grind

/-- The magnitude of a residue's value. -/
theorem mag_spec (a : Nat) (L : Int) (hL : L.natAbs < 2 ^ a) :
    Nat.add (Nat.sub (res (a + 1) L) (Nat.mul (Nat.shiftRight (res (a + 1) L) a) (Nat.shiftLeft 1 (a + 1))))
      (Nat.sub (Nat.mul (Nat.shiftRight (res (a + 1) L) a) (Nat.shiftLeft 1 (a + 1))) (res (a + 1) L)) = L.natAbs := by
  obtain ⟨s, v⟩ := res_val a L hL
  have e1 : Nat.shiftLeft 1 (a + 1) = 2 ^ (a + 1) := by rw [nshl, Nat.one_mul]
  have hlt := res_lt (a + 1) L
  have e2 : Nat.shiftRight (res (a + 1) L) a = res (a + 1) L >>> a := rfl
  simp only [e1, e2, nadd, nmul, nsub]
  rw [← cast_two_pow] at v
  generalize res (a + 1) L = u at s v hlt ⊢
  generalize 2 ^ (a + 1) = P at v hlt ⊢
  rw [s] at v ⊢
  by_cases hneg : L < 0
  · rw [if_pos hneg] at v ⊢
    simp only [Int.natCast_one, Int.one_mul, Nat.one_mul] at v ⊢
    omega
  · rw [if_neg hneg] at v ⊢
    simp only [Int.natCast_zero, Int.zero_mul, Int.sub_zero, Nat.zero_mul] at v ⊢
    omega

theorem and_one (x : Nat) : Nat.land x 1 = x % 2 := Nat.and_one_is_mod x

/-- The valuation checks: `v₂(L) = sh` and the odd part. -/
theorem sh_check (a : Nat) (L : Int) (sh : Nat) (_hL : L.natAbs < 2 ^ a) (ha : 64 ≤ a + 1)
    (h : Nat.add (Nat.sub 1 (Nat.land (Nat.shiftRight (Nat.land (res (a + 1) L) 18446744073709551615) sh) 1))
      (Nat.land (Nat.land (res (a + 1) L) 18446744073709551615) (Nat.sub (Nat.shiftLeft 1 sh) 1)) = 0) :
    sh < 64 ∧ L.natAbs % 2 ^ sh = 0 ∧ (L.natAbs / 2 ^ sh) % 2 = 1 := by
  have e64 : (18446744073709551615 : Nat) = 2 ^ 64 - 1 := rfl
  have e1 : Nat.shiftLeft 1 sh = 2 ^ sh := by rw [nshl, Nat.one_mul]
  simp only [e64, e1, nmask, nadd, nsub, nshr, and_one] at h
  generalize hx : res (a + 1) L % 2 ^ 64 = xL at h
  have hxl : xL < 2 ^ 64 := by rw [← hx]; exact Nat.mod_lt _ (Nat.two_pow_pos 64)
  have c1 : xL / 2 ^ sh % 2 = 1 := by omega
  have c2 : xL % 2 ^ sh = 0 := by omega
  have hsh : sh < 64 := by
    apply Nat.lt_of_not_le; intro hge
    have : xL / 2 ^ sh = 0 := Nat.div_eq_of_lt (Nat.lt_of_lt_of_le hxl (Nat.pow_le_pow_right (by decide) (by omega)))
    omega
  refine ⟨hsh, ?_⟩
  -- `xL ≡ 2^sh (mod 2^(sh+1))`
  have hP : 0 < 2 ^ sh := Nat.two_pow_pos sh
  have hx2 : xL % 2 ^ (sh + 1) = 2 ^ sh := by
    have d1 := Nat.div_add_mod xL (2 ^ sh)
    have d2 := Nat.div_add_mod (xL / 2 ^ sh) 2
    rw [c2, Nat.add_zero] at d1
    rw [c1] at d2
    rw [Nat.pow_succ]
    have : xL = 2 ^ sh * 2 * (xL / 2 ^ sh / 2) + 2 ^ sh := by
      calc xL = 2 ^ sh * (xL / 2 ^ sh) := d1.symm
        _ = 2 ^ sh * (2 * (xL / 2 ^ sh / 2) + 1) := by rw [d2]
        _ = _ := by rw [Nat.mul_add, Nat.mul_one, Nat.mul_assoc]
    rw [this, Nat.mul_add_mod]
    exact Nat.mod_eq_of_lt (by omega)
  -- the same for `L`
  have hLx : MEq (2 ^ (sh + 1)) L (xL : Int) := by
    have m1 : MEq (2 ^ (a + 1)) L (res (a + 1) L : Int) := (res_meq (a + 1) L).symm
    have m2 : MEq (2 ^ 64) ((res (a + 1) L : Nat) : Int) (xL : Int) := by
      rw [← hx, Int.natCast_emod, cast_two_pow]; exact (MEq.emod _ _).symm
    have d1 : (2 : Int) ^ (sh + 1) ∣ 2 ^ (a + 1) := pow2_dvd (by omega)
    have d2 : (2 : Int) ^ (sh + 1) ∣ 2 ^ 64 := pow2_dvd (by omega)
    exact (m1.of_dvd d1).trans (m2.of_dvd d2)
  have hLm : L % 2 ^ (sh + 1) = 2 ^ sh := by
    rw [hLx.emod_eq, ← cast_two_pow, ← Int.natCast_emod, hx2, cast_two_pow]
  have hv : L.natAbs % 2 ^ (sh + 1) = 2 ^ sh := by
    have hP2 : (0 : Int) < 2 ^ (sh + 1) := two_pow_pos _
    apply Int.ofNat_inj.1
    rw [Int.natCast_emod, cast_two_pow, cast_two_pow]
    rcases Int.natAbs_eq L with hl | hl
    · rw [← hl, hLm]
    · have e : (L.natAbs : Int) = -L := by omega
      rw [e]
      have q := Int.emod_add_mul_ediv L (2 ^ (sh + 1))
      rw [hLm] at q
      have : -L = 2 ^ sh + 2 ^ (sh + 1) * (-(L / 2 ^ (sh + 1)) - 1) := by
        rw [pow_succ_two] at q ⊢; grind
      rw [this, Int.add_mul_emod_self_left]
      exact Int.emod_eq_of_lt (Int.le_of_lt (two_pow_pos sh)) (by rw [pow_succ_two]; have := two_pow_pos sh; omega)
  have d1 := Nat.div_add_mod L.natAbs (2 ^ (sh + 1))
  rw [hv] at d1
  rw [Nat.pow_succ] at d1
  have hdecomp : L.natAbs = 2 ^ sh * (2 * (L.natAbs / (2 ^ sh * 2)) + 1) := by
    rw [Nat.mul_add, Nat.mul_one, ← Nat.mul_assoc]; omega
  rw [hdecomp, Nat.mul_mod_right, Nat.mul_div_cancel_left _ hP]
  omega

theorem meq_mod (M a : Nat) : MEq M ((a % M : Nat) : Int) (a : Int) := by
  rw [Int.natCast_emod]; exact MEq.emod _ _

/-- The three multipliers of a step: `m₁X + m₂Y + m₃Z ≡ inv²·(lg²X − lf·lg·Y − (lg·f₁ − lf·g₁)·Z)`. -/
theorem mult_cong (M sh inv o sf Lg F1 G1 : Nat) (lf lg f1 g1 : Int) (hMpos : 0 < M)
    (hLg : MEq M Lg lg) (hF1 : MEq M F1 f1) (hG1 : MEq M G1 g1) (hsf : sf ≤ 1)
    (hlf : lf = (if sf = 1 then -1 else 1) * 2 ^ sh * o) (hinv : MEq M ((o : Int) * inv) 1) (X Y Z : Int) :
    MEq M (((Lg * inv % M) * (Lg * inv % M) % M : Nat) * X
      + ((sf * ((Lg * inv % M) * 2 ^ sh % M) + (1 - sf) * (M - (Lg * inv % M) * 2 ^ sh % M)) : Nat) * Y
      + ((((1 - sf) * (G1 * 2 ^ sh % M) + (1 - (1 - sf)) * (M - G1 * 2 ^ sh % M)) + M
          - (F1 * (Lg * inv % M)) % M) * inv % M : Nat) * Z)
      ((inv : Int) * inv * (lg * lg * X - lf * lg * Y - (lg * f1 - lf * g1) * Z)) := by
  generalize hσ : (if sf = 1 then (-1 : Int) else 1) = σ at hlf
  have hw : MEq M ((Lg * inv % M : Nat) : Int) (lg * inv) := by
    refine (meq_mod M _).trans ?_; push_cast; exact hLg.mul (MEq.refl _ _)
  have hm1 : MEq M (((Lg * inv % M) * (Lg * inv % M) % M : Nat) : Int) (lg * inv * (lg * inv)) := by
    refine (meq_mod M _).trans ?_; push_cast; exact hw.mul hw
  have ht2 : MEq M (((Lg * inv % M) * 2 ^ sh % M : Nat) : Int) (lg * inv * 2 ^ sh) := by
    refine (meq_mod M _).trans ?_; push_cast; exact hw.mul (MEq.refl _ _)
  have hh : MEq M ((G1 * 2 ^ sh % M : Nat) : Int) (g1 * 2 ^ sh) := by
    refine (meq_mod M _).trans ?_; push_cast; exact hG1.mul (MEq.refl _ _)
  have hv : MEq M ((F1 * (Lg * inv % M) % M : Nat) : Int) (f1 * (lg * inv)) := by
    refine (meq_mod M _).trans ?_; push_cast; exact hF1.mul hw
  have lt1 := Nat.mod_lt ((Lg * inv % M) * 2 ^ sh) hMpos
  have lt2 := Nat.mod_lt (G1 * 2 ^ sh) hMpos
  have lt3 := Nat.mod_lt (F1 * (Lg * inv % M)) hMpos
  -- `m₂ ≡ −σ·lg·inv·2^sh`, `m₃ ≡ (σ·2^sh·g₁ − f₁·lg·inv)·inv`
  have hm2 : MEq M (((sf * ((Lg * inv % M) * 2 ^ sh % M) + (1 - sf) * (M - (Lg * inv % M) * 2 ^ sh % M)) : Nat) : Int)
      (-σ * (lg * inv * 2 ^ sh)) := by
    rcases Nat.le_one_iff_eq_zero_or_eq_one.1 hsf with h0 | h0 <;> subst h0 <;> simp at hσ <;> subst hσ
    · simp only [Nat.zero_mul, Nat.zero_add, Nat.sub_zero, Nat.one_mul]
      exact (MEq.nat_sub (Nat.le_of_lt lt1) ht2).trans (MEq.of_eq (by grind))
    · simp only [Nat.one_mul, Nat.sub_self, Nat.zero_mul, Nat.add_zero]
      exact ht2.trans (MEq.of_eq (by grind))
  have hhs : MEq M ((((1 - sf) * (G1 * 2 ^ sh % M) + (1 - (1 - sf)) * (M - G1 * 2 ^ sh % M)) : Nat) : Int)
      (σ * (g1 * 2 ^ sh)) := by
    rcases Nat.le_one_iff_eq_zero_or_eq_one.1 hsf with h0 | h0 <;> subst h0 <;> simp at hσ <;> subst hσ
    · simp only [Nat.sub_zero, Nat.one_mul, Nat.sub_self, Nat.zero_mul, Nat.add_zero]
      exact hh.trans (MEq.of_eq (by grind))
    · simp only [Nat.sub_self, Nat.zero_mul, Nat.zero_add, Nat.sub_zero, Nat.one_mul]
      exact (MEq.nat_sub (Nat.le_of_lt lt2) hh).trans (MEq.of_eq (by grind))
  have hs_le : ((1 - sf) * (G1 * 2 ^ sh % M) + (1 - (1 - sf)) * (M - G1 * 2 ^ sh % M)) ≤ M := by
    rcases Nat.le_one_iff_eq_zero_or_eq_one.1 hsf with h0 | h0 <;> subst h0 <;> simp <;> omega
  have hm3 : MEq M (((((1 - sf) * (G1 * 2 ^ sh % M) + (1 - (1 - sf)) * (M - G1 * 2 ^ sh % M)) + M
          - (F1 * (Lg * inv % M)) % M) * inv % M : Nat) : Int)
      ((σ * (g1 * 2 ^ sh) - f1 * (lg * inv)) * inv) := by
    refine (meq_mod M _).trans ?_
    rw [Int.natCast_mul, Int.ofNat_sub (by omega), Int.natCast_add]
    refine MEq.mul ?_ (MEq.refl _ _)
    exact ((hhs.add (MEq.self _)).sub hv).trans (MEq.of_eq (by grind))
  refine (((hm1.mul (MEq.refl _ X)).add (hm2.mul (MEq.refl _ Y))).add (hm3.mul (MEq.refl _ Z))).trans ?_
  -- the remaining difference is a multiple of `o·inv − 1`
  obtain ⟨k, hk⟩ := hinv
  refine ⟨σ * 2 ^ sh * inv * k * (lg * Y - g1 * Z), ?_⟩
  rw [hlf]
  have : (o : Int) * inv = 1 + M * k := by omega
  grind

/-! ## One step -/

theorem nmask' (x k : Nat) : Nat.land x (Nat.sub (2 ^ k) 1) = x % 2 ^ k := nmask x k

theorem vSh_true (lf : Nat) : vSh true lf = 0 := rfl
theorem vInv_true (nw : List Nat) (o : Nat) : vInv true nw o = 1 := rfl
theorem vSh_false (lf : Nat) : vSh false lf = dbSh (Nat.gcd (Nat.land lf 18446744073709551615) (Nat.shiftLeft 1 64)) := rfl
theorem vInv_false (nw : List Nat) (o : Nat) : vInv false nw o = newton o o nw := rfl
theorem cnd_true (x y : Nat) : cnd true x y = x := rfl
theorem cnd_false (x y : Nat) : cnd false x y = y := rfl

theorem lstep_spec {α : Type} (a b q : Nat) (first : Bool) (nw : List Nat) (A B C : Nat → Int) (n : Nat)
    (ha : 64 ≤ a + 1) (haq : a + 1 ≤ q) (hbq : b + 1 ≤ q)
    (hA : ∀ e, e ≤ n + 2 → (A e).natAbs < 2 ^ a) (hB : ∀ e, e ≤ n + 1 → (B e).natAbs < 2 ^ b)
    (hfirst : first = true → A (n + 2) = 1)
    (hnw : first = false → ladderOK 3 nw (q + 128) = true)
    (hP : ∀ e, e ≤ n → premF A B (n + 1) e = (if first then 1 else A (n + 2) * A (n + 2)) * C e)
    (k : List Nat → Nat → α) :
    ∃ H bad, lstep (a + 1) (b + 1) q a b first nw (toN (a + 1) A (n + 2)) (toN (b + 1) B (n + 1)) k = k H bad ∧
      (bad = 0 → H = toN q C n ∧ C n ≠ 0) := by
  have eA : toN (a + 1) A (n + 2) = res (a + 1) (A (n + 2)) :: res (a + 1) (A (n + 1)) :: toN (a + 1) A n := rfl
  have eB : toN (b + 1) B (n + 1) = res (b + 1) (B (n + 1)) :: res (b + 1) (B n) :: (toN (b + 1) B n).tail := by
    show res (b + 1) (B (n + 1)) :: toN (b + 1) B n = _; exact congrArg _ (toN_cons (b + 1) B n)
  rw [eA, eB]
  unfold lstep
  simp only [hd0_cons, List.tail_cons]
  rw [← toN_cons (b + 1) B n]
  refine ⟨_, _, rfl, ?_⟩
  intro hbad
  -- the leading coefficient of `A`
  have hL := hA (n + 2) (Nat.le_refl _)
  obtain ⟨hsf, -⟩ := res_val a (A (n + 2)) hL
  have hmag := mag_spec a (A (n + 2)) hL
  have hsfle := sign_le a (A (n + 2)) hL
  rw [show vMag (res (a + 1) (A (n + 2))) a (Nat.shiftLeft 1 (a + 1)) = (A (n + 2)).natAbs from hmag]
    at hbad ⊢
  generalize hsh : vSh first (res (a + 1) (A (n + 2))) = sh at hbad ⊢
  generalize hsh2 : Nat.shiftLeft sh 1 = sh2 at hbad ⊢
  have hsh2' : sh2 = sh + sh := by rw [← hsh2, nshl]; omega
  generalize hM : Nat.shiftLeft 1 (Nat.add q sh2) = M at hbad ⊢
  have hM' : M = 2 ^ (q + sh2) := by rw [← hM, nshl, Nat.one_mul]; rfl
  have hMpos : 0 < M := by rw [hM']; exact Nat.two_pow_pos _
  have em : ∀ x, Nat.land x (M - 1) = x % M := by intro x; rw [hM']; exact nmask x _
  have hLg := ext_spec b (B (n + 1)) (hB (n + 1) (Nat.le_refl _)) M
    (by rw [hM']; exact Nat.pow_le_pow_right (by decide) (by omega))
  have hF1 := ext_spec a (A (n + 1)) (hA (n + 1) (by omega)) M
    (by rw [hM']; exact Nat.pow_le_pow_right (by decide) (by omega))
  have hG1 := ext_spec b (B n) (hB n (by omega)) M
    (by rw [hM']; exact Nat.pow_le_pow_right (by decide) (by omega))
  rw [← vExt] at hLg hF1 hG1
  generalize vExt (res (b + 1) (B (n + 1))) b (Nat.sub M (Nat.shiftLeft 1 (b + 1))) = Lg at hLg hbad ⊢
  generalize vExt (res (a + 1) (A (n + 1))) a (Nat.sub M (Nat.shiftLeft 1 (a + 1))) = F1 at hF1 hbad ⊢
  generalize vExt (res (b + 1) (B n)) b (Nat.sub M (Nat.shiftLeft 1 (b + 1))) = G1 at hG1 hbad ⊢
  generalize hinv : vInv first nw (Nat.shiftRight (A (n + 2)).natAbs sh) = inv at hbad ⊢
  simp only [nshl, vSel, nadd, nmul, nsub, Nat.one_mul] at hbad ⊢
  simp only [em] at hbad ⊢
  have hsf' : Nat.shiftRight (res (a + 1) (A (n + 2))) a = if A (n + 2) < 0 then 1 else 0 := hsf
  have hsfle' : Nat.shiftRight (res (a + 1) (A (n + 2))) a ≤ 1 := hsfle
  generalize Nat.shiftRight (res (a + 1) (A (n + 2))) a = sf at hsf' hsfle' hbad ⊢
  have mc := mult_cong M sh inv ((A (n + 2)).natAbs / 2 ^ sh) sf Lg F1 G1 (A (n + 2)) (B (n + 1)) (A (n + 1)) (B n)
    hMpos hLg hF1 hG1 hsfle'
  generalize hw : Lg * inv % M = w at mc hbad ⊢
  generalize w * w % M = m1 at mc hbad ⊢
  generalize sf * (w * 2 ^ sh % M) + (1 - sf) * (M - w * 2 ^ sh % M) = m2 at mc hbad ⊢
  generalize ((1 - sf) * (G1 * 2 ^ sh % M) + (1 - (1 - sf)) * (M - G1 * 2 ^ sh % M) + M - F1 * w % M) * inv % M
    = m3 at mc hbad ⊢
  -- the failure count
  have hb2 : ∀ x y : Nat, cnd first x (y + x) = 0 → x = 0 ∧ (first = false → y = 0) := by
    intro x y h; cases first
    · simp only [cnd_false] at h; exact ⟨by omega, fun _ => by omega⟩
    · simp only [cnd_true] at h; exact ⟨h, fun h' => absurd h' (by decide)⟩
  obtain ⟨hlead, hchk⟩ := hb2 _ _ hbad
  -- the leading coefficient `σ·2^sh·o`, the inverse, and the scaling
  have hpos : ∀ x : Int, 0 ≤ x → x = (x.natAbs : Int) := fun x hx => by omega
  have key : A (n + 2) = (if sf = 1 then -1 else 1) * 2 ^ sh * (((A (n + 2)).natAbs / 2 ^ sh : Nat) : Int)
      ∧ MEq M ((((A (n + 2)).natAbs / 2 ^ sh : Nat) : Int) * inv) 1
      ∧ (∀ c : Int, MEq M ((inv : Int) * inv * ((if first then 1 else A (n + 2) * A (n + 2)) * c))
          (2 ^ sh2 * c)) := by
    cases first
    · have hc := hchk rfl
      unfold vChk at hc
      obtain ⟨hs64, hm0, hodd⟩ := sh_check a (A (n + 2)) sh hL ha hc
      have hdec : (A (n + 2)).natAbs = 2 ^ sh * ((A (n + 2)).natAbs / 2 ^ sh) := by
        have := Nat.div_add_mod (A (n + 2)).natAbs (2 ^ sh); omega
      generalize ho : (A (n + 2)).natAbs / 2 ^ sh = o at hdec hodd hinv ⊢
      rw [vInv_false, nshr, ho] at hinv
      have hnv := newton_spec o nw o 3 (q + 128) (hnw rfl) (odd_sq o hodd)
      rw [hinv] at hnv
      have hdvd : (M : Int) ∣ 2 ^ (q + 128) := by rw [hM', cast_two_pow]; exact pow2_dvd (by omega)
      have hoi : MEq M ((o : Int) * inv) 1 := hnv.of_dvd hdvd
      refine ⟨?_, hoi, ?_⟩
      · rw [hsf']
        by_cases hneg : A (n + 2) < 0
        · rw [if_pos hneg, if_pos rfl]
          have : ((A (n + 2)).natAbs : Int) = -A (n + 2) := by omega
          rw [hdec] at this; push_cast at this; grind
        · rw [if_neg hneg, if_neg (by decide)]
          have : ((A (n + 2)).natAbs : Int) = A (n + 2) := by omega
          rw [hdec] at this; push_cast at this; grind
      · intro c
        simp only [Bool.false_eq_true, ↓reduceIte]
        have hsq : A (n + 2) * A (n + 2) = 2 ^ sh2 * ((o : Int) * o) := by
          have : ((A (n + 2)).natAbs : Int) * (A (n + 2)).natAbs = A (n + 2) * A (n + 2) := by
            rw [← Int.natCast_mul]; exact Int.natAbs_mul_self
          rw [← this, hdec, hsh2']; push_cast; rw [Int.pow_add]; grind
        rw [hsq]
        have := ((hoi.mul hoi).mul_left ((2 : Int) ^ sh2 * c))
        refine MEq.trans (MEq.of_eq (by grind)) (this.trans (MEq.of_eq (by grind)))
    · have h1 := hfirst rfl
      rw [vSh_true] at hsh; subst hsh
      rw [vInv_true] at hinv; subst hinv
      have hsh0 : sh2 = 0 := by omega
      subst hsh0
      rw [h1] at hsf' ⊢
      simp only [show ¬((1 : Int) < 0) by decide, ↓reduceIte] at hsf'
      subst hsf'
      refine ⟨by simp, by simp; exact MEq.refl _ _, fun c => by simp; exact MEq.refl _ _⟩
  obtain ⟨klf, kinv, kscale⟩ := key
  have mc' := mc klf kinv
  -- every coefficient
  have hcoef : ∀ e, e ≤ n → ∀ Y : Int, (Y = if 1 ≤ e then B (e - 1) else 0) →
      MEq (2 ^ (q + sh2)) ((m1 : Int) * A e + m2 * Y + m3 * B e) (2 ^ sh2 * C e) := by
    intro e he Y hY
    have h1 := mc' (A e) Y (B e)
    have h2 := hP e he
    unfold premF at h2
    rw [if_pos (by omega), show n + 1 - 1 = n by omega] at h2
    rw [← hY] at h2
    have hMi : (M : Int) = 2 ^ (q + sh2) := by rw [hM', cast_two_pow]
    rw [← hMi]
    refine h1.trans ?_
    have e3 : B (n + 1) * B (n + 1) * A e - A (n + 2) * B (n + 1) * Y - (B (n + 1) * A (n + 1) - A (n + 2) * B n) * B e
        = (if first = true then 1 else A (n + 2) * A (n + 2)) * C e := h2
    rw [e3]
    exact kscale (C e)
  have hlq := lqs_spec m1 m2 m3 (m1 * 2 ^ (a + 1) % M) (m2 * 2 ^ (b + 1) % M) (m3 * 2 ^ (b + 1) % M)
    (M * 2 ^ 2) sh2 (2 ^ q - 1) a b (a + 1) (b + 1) q A B C n
    (fun e he1 he2 => by
      rw [hM', show (2 : Nat) ^ 2 = 4 from rfl]
      exact coef_spec q a b sh2 m1 m2 m3 (A e) (B (e - 1)) (B e) (C e) (hA e (by omega)) (hB (e - 1) (by omega))
        (hB e (by omega)) (hcoef e he2 _ (by rw [if_pos he1])))
    (by
      rw [coefL_eq _ m2 _ _ (m2 * 2 ^ (b + 1) % M), hM', show (2 : Nat) ^ 2 = 4 from rfl]
      have := coef_spec q a b sh2 m1 m2 m3 (A 0) 0 (B 0) (C 0) (hA 0 (by omega)) (by simp; exact Nat.two_pow_pos b)
        (hB 0 (by omega)) (hcoef 0 (by omega) 0 (by simp))
      rwa [res_zero_int] at this)
  rw [hlq] at hlead ⊢
  refine ⟨rfl, ?_⟩
  intro h0
  rw [toN_cons, hd0_cons, h0, res_zero_int] at hlead
  exact absurd hlead (by decide)
end V9

/-!
# The low-part run computes the chain

`lrunR_spec`: if every step's checks pass, the run of steps `k … 22` ends with the residues of
`F_24` and every leading coefficient of the chain is nonzero. Bounds come from the size
certificates (`chain_bound`), exactness from `chain_exact`.
-/

namespace V9

theorem lstep_cps {α : Type} (qA qB q qhA qhB : Nat) (first : Bool) (nw : List Nat) (A B : List Nat)
    (k : List Nat → Nat → α) :
    lstep qA qB q qhA qhB first nw A B k =
      k (lstep qA qB q qhA qhB first nw A B Prod.mk).1 (lstep qA qB q qhA qhB first nw A B Prod.mk).2 := rfl

/-- The run with its result returned as a pair. -/
def lrunR (ps : List (Nat × Nat × Nat × Nat × Nat × List Nat)) (A B : List Nat) (bad : Nat) : List Nat × Nat :=
  lrun ps A B bad Prod.mk

theorem lrun_cps {α : Type} : ∀ (ps : List (Nat × Nat × Nat × Nat × Nat × List Nat)) (A B : List Nat) (bad : Nat)
    (k : List Nat → Nat → α), lrun ps A B bad k = k (lrunR ps A B bad).1 (lrunR ps A B bad).2
  | [], _, _, _, _ => rfl
  | (qA, qB, q, qhA, qhB, nw) :: ps, A, B, bad, k => by
    unfold lrunR
    simp only [lrun]
    rw [lstep_cps _ _ _ _ _ _ _ _ _ (fun H b => lrun ps B H (Nat.add bad b) k),
      lstep_cps _ _ _ _ _ _ _ _ _ (fun H b => lrun ps B H (Nat.add bad b) Prod.mk)]
    exact lrun_cps ps _ _ _ k

theorem lrunR_cons (qA qB q qhA qhB : Nat) (nw : List Nat) (ps : List (Nat × Nat × Nat × Nat × Nat × List Nat))
    (A B : List Nat) (bad : Nat) :
    lrunR ((qA, qB, q, qhA, qhB, nw) :: ps) A B bad =
      lrunR ps B (lstep qA qB q qhA qhB false nw A B Prod.mk).1
        (bad + (lstep qA qB q qhA qhB false nw A B Prod.mk).2) := by
  unfold lrunR; simp only [lrun]
  rw [lstep_cps _ _ _ _ _ _ _ _ _ (fun H b => lrun ps B H (Nat.add bad b) Prod.mk)]; rfl

theorem lrunR_mono : ∀ (ps : List (Nat × Nat × Nat × Nat × Nat × List Nat)) (A B : List Nat) (bad : Nat),
    bad ≤ (lrunR ps A B bad).2
  | [], _, _, _ => Nat.le_refl _
  | (qA, qB, q, qhA, qhB, nw) :: ps, A, B, bad => by
    rw [lrunR_cons]
    exact Nat.le_trans (Nat.le_add_right _ _) (lrunR_mono ps _ _ _)

/-! ## The parameters and the certificates -/

def qw (k : Nat) : Nat := qws.getD k 0

/-- Step `k`'s parameters: the widths of `F_k`, `F_(k+1)`, `F_(k+2)`, their sign bits, a Newton
ladder to `q + 128`. -/
def stepsOK : Nat → List (Nat × Nat × Nat × Nat × Nat × List Nat) → Bool
  | k, [] => k == 23
  | k, (qA, qB, q, qhA, qhB, nw) :: ps =>
    (qA == qw k) && (qB == qw (k + 1)) && (q == qw (k + 2)) && (qhA + 1 == qA) && (qhB + 1 == qB) &&
      Nat.ble 64 qA && Nat.ble qA q && Nat.ble qB q && ladderOK 3 nw (q + 128) && stepsOK (k + 1) ps

theorem stepsOK_lparams : stepsOK 1 lparams = true := by decide

/-- Certificate `i` is for `S_(22-i)` with the width of `F_(i+2)`. -/
def certIdx : Nat → List (Nat × Nat × Nat × Nat × List Nat × List Nat) → Bool
  | k, [] => k == 23
  | k, (j, _, _, q, _, _) :: cs => (j + k == 22) && (q == qw (k + 2)) && certIdx (k + 1) cs

theorem certIdx_ok : certIdx 0 certD5 = true := by decide

theorem cert_get : ∀ (k : Nat) (cs : List (Nat × Nat × Nat × Nat × List Nat × List Nat)),
    certIdx k cs = true → certAll cs = true →
    ∀ i, k ≤ i → i ≤ 22 → ∃ N K u v, certOK (22 - i) N K (qw (i + 2)) u v = true
  | k, [], h, _, i, hi, hi2 => by simp [certIdx] at h; omega
  | k, (j, N, K, q, u, v) :: cs, h, ha, i, hi, hi2 => by
    simp only [certIdx, Bool.and_eq_true, beq_iff_eq] at h
    simp only [certAll, Bool.and_eq_true] at ha
    by_cases hik : i = k
    · subst hik
      refine ⟨N, K, u, v, ?_⟩
      rw [show 22 - i = j by omega, ← h.1.2]; exact ha.1
    · exact cert_get (k + 1) cs h.2 ha.2 i (by omega) hi2

/-- Every chain polynomial `F_k` (`k ≥ 2`) is below its width. -/
theorem chain_bound (f g : Nat → Int) (hf : ∀ e, 24 < e → f e = 0) (hg : ∀ e, 23 < e → g e = 0)
    (hfb : ∀ e, (f e).natAbs ≤ FbN e) (hgb : ∀ e, (g e).natAbs ≤ GbN e) (k : Nat) (hk2 : 2 ≤ k) (hk : k ≤ 24)
    (hL : ∀ k', k' < k - 1 → (chainP f g 24 k').2 (24 - (k' + 1)) ≠ 0) :
    ∀ e, e ≤ 24 - k → ((chainP f g 24 (k - 1)).2 e).natAbs < 2 ^ (qw k - 1) := by
  intro e he
  rw [chain_val f g 24 (by decide) hf hg (k - 1) (by omega) (by omega) hL e (by omega)]
  obtain ⟨N, K, u, v, hc⟩ := cert_get 0 certD5 certIdx_ok certD5_ok (k - 2) (by omega) (by omega)
  rw [show k - 2 + 2 = k by omega, show 22 - (k - 2) = 24 - k by omega] at hc
  rw [show 24 - (k - 1 + 1) = 24 - k by omega]
  exact sres_lt f g hfb hgb (24 - k) N K (qw k) u v hc e (by omega)

/-! ## The run -/

theorem lrunR_spec (f g : Nat → Int) (hf : ∀ e, 24 < e → f e = 0) (hg : ∀ e, 23 < e → g e = 0)
    (hfb : ∀ e, (f e).natAbs ≤ FbN e) (hgb : ∀ e, (g e).natAbs ≤ GbN e)
    (hgw : ∀ e, (g e).natAbs < 2 ^ (qw 1 - 1)) :
    ∀ (ps : List (Nat × Nat × Nat × Nat × Nat × List Nat)) (k : Nat) (A B : List Nat) (bad : Nat),
      stepsOK k ps = true → 1 ≤ k →
      A = toN (qw k) (chainP f g 24 k).1 (24 - k) → B = toN (qw (k + 1)) (chainP f g 24 k).2 (23 - k) →
      (∀ k', k' ≤ k → (chainP f g 24 k').2 (24 - (k' + 1)) ≠ 0) →
      (lrunR ps A B bad).2 = 0 →
      (lrunR ps A B bad).1 = toN (qw 24) (chainP f g 24 23).2 0 ∧
        ∀ k', k' ≤ 23 → (chainP f g 24 k').2 (24 - (k' + 1)) ≠ 0
  | [], k, A, B, bad, hs, _, _, hB, hL, _ => by
    simp only [stepsOK, beq_iff_eq] at hs
    subst hs
    exact ⟨hB, hL⟩
  | (qA, qB, q, qhA, qhB, nw) :: ps, k, A, B, bad, hs, hk1, hA, hB, hL, hbad => by
    simp only [stepsOK, Bool.and_eq_true, beq_iff_eq, Nat.ble_eq] at hs
    obtain ⟨⟨⟨⟨⟨⟨⟨⟨⟨hqA, hqB⟩, hq⟩, hhA⟩, hhB⟩, h64⟩, hAq⟩, hBq⟩, hnw⟩, hrest⟩ := hs
    have hk22 : k ≤ 22 := by
      have hq0 : qw (k + 2) ≠ 0 := by omega
      apply Nat.le_of_not_lt; intro hc
      apply hq0; unfold qw
      rw [List.getD_eq_getElem?_getD, List.getElem?_eq_none (by simp [qws]; omega)]; rfl
    rw [lrunR_cons] at hbad ⊢
    -- one step
    obtain ⟨a, rfl⟩ : ∃ a, qA = a + 1 := ⟨qhA, by omega⟩
    obtain ⟨b, rfl⟩ : ∃ b, qB = b + 1 := ⟨qhB, by omega⟩
    have ha : a = qhA := by omega
    have hb : b = qhB := by omega
    subst ha hb
    have hn : 24 - k = (22 - k) + 2 := by omega
    have hn1 : 23 - k = (22 - k) + 1 := by omega
    rw [hn, ← hqA] at hA; rw [hn1, ← hqB] at hB
    subst hA; subst hB
    have hAb : ∀ e, e ≤ 22 - k + 2 → ((chainP f g 24 k).1 e).natAbs < 2 ^ a := by
      intro e he
      cases k with
      | zero => omega
      | succ k0 =>
        rw [chainP_fst_succ]
        cases k0 with
        | zero => simpa [chainP, ← hqA] using hgw e
        | succ k1 =>
          have := chain_bound f g hf hg hfb hgb (k1 + 2) (by omega) (by omega)
            (fun k' hk' => hL k' (by omega)) e (by omega)
          rw [show k1 + 2 - 1 = k1 + 1 by omega, ← hqA] at this
          simpa using this
    have hBb : ∀ e, e ≤ 22 - k + 1 → ((chainP f g 24 k).2 e).natAbs < 2 ^ b := by
      intro e he
      have := chain_bound f g hf hg hfb hgb (k + 1) (by omega) (by omega)
        (fun k' hk' => hL k' (by omega)) e (by omega)
      rw [show k + 1 - 1 = k by omega, ← hqB] at this
      simpa using this
    have hP : ∀ e, e ≤ 22 - k → premF (chainP f g 24 k).1 (chainP f g 24 k).2 (22 - k + 1) e =
        (if false then 1 else (chainP f g 24 k).1 (22 - k + 2) * (chainP f g 24 k).1 (22 - k + 2)) *
          (chainP f g 24 (k + 1)).2 e := by
      intro e _
      have := chain_exact f g 24 (by decide) hf hg k (by omega) hk1 hL e
      rw [show 24 - (k + 1) = 22 - k + 1 by omega, show 22 - k + 1 + 1 = 22 - k + 2 by omega] at this
      simpa using this
    obtain ⟨H, b', hst, hok⟩ := lstep_spec a b q false nw (chainP f g 24 k).1 (chainP f g 24 k).2
      (chainP f g 24 (k + 1)).2 (22 - k) h64 hAq (by omega) hAb hBb (fun h => absurd h (by decide))
      (fun _ => hnw) hP Prod.mk
    rw [hst] at hbad ⊢
    simp only at hbad ⊢
    have hb0 : b' = 0 := by
      have := lrunR_mono ps (toN (b + 1) (chainP f g 24 k).2 (22 - k + 1)) H (bad + b'); omega
    obtain ⟨hH, hC⟩ := hok hb0
    exact lrunR_spec f g hf hg hfb hgb hgw ps (k + 1) _ H _ hrest (by omega)
      (by rw [show (chainP f g 24 (k + 1)).1 = (chainP f g 24 k).2 from chainP_fst_succ f g 24 k, hqB,
            show 24 - (k + 1) = 22 - k + 1 by omega])
      (by rw [hH, hq, show 23 - (k + 1) = 22 - k by omega])
      (fun k' hk' => by
        by_cases h : k' = k + 1
        · subst h; rw [show 24 - (k + 1 + 1) = 22 - k by omega]; exact hC
        · exact hL k' (by omega))
      hbad

end V9

/-!
# The low-part run is the specification's normal resultant

`lowRun_spec`: on the 25 encoded coefficients of a monic polynomial whose coefficients are within
the D5 widths, a run with no failed check returns the specification's `normalResultant`.
-/

namespace V9

/-- v7's encoding `2·|x| + [x < 0]` (identical to the submission's `zdec`). -/
def zdec (z : Nat) : Int := if z % 2 = 1 then -((z / 2 : Nat) : Int) else ((z / 2 : Nat) : Int)

theorem zres_spec (mag s q : Nat) (hs : s ≤ 1) (hm : mag < 2 ^ q) :
    zres mag s (Nat.sub (Nat.shiftLeft 1 q) 1) (Nat.shiftLeft 1 q) = res q (if s = 1 then -(mag : Int) else mag) := by
  have e1 : Nat.shiftLeft 1 q = 2 ^ q := by rw [nshl, Nat.one_mul]
  unfold zres
  rw [e1]
  simp only [nmask, nadd, nmul, nsub]
  apply Int.ofNat_inj.1
  rw [res_cast, natCast_mod_pow]
  rcases Nat.le_one_iff_eq_zero_or_eq_one.1 hs with h | h <;> subst h
  · simp only [Nat.sub_zero, Nat.one_mul, Nat.zero_mul, Nat.add_zero, show ¬((0 : Nat) = 1) by decide, ↓reduceIte]
  · simp only [Nat.sub_self, Nat.zero_mul, Nat.zero_add, Nat.one_mul, ↓reduceIte]
    rw [Int.ofNat_sub (Nat.le_of_lt hm), cast_two_pow]
    rw [show (2 : Int) ^ q - mag = -(mag : Int) + 2 ^ q * 1 by grind, Int.add_mul_emod_self_left]

theorem zdec_eq (x : Nat) : zdec x = if x % 2 = 1 then -((x / 2 : Nat) : Int) else ((x / 2 : Nat) : Int) := rfl

theorem zres_z (x k q : Nat) (hm : x / 2 * k < 2 ^ q) :
    zres (Nat.mul (Nat.shiftRight x 1) k) (Nat.land x 1) (Nat.sub (Nat.shiftLeft 1 q) 1) (Nat.shiftLeft 1 q)
      = res q ((k : Int) * zdec x) := by
  rw [show Nat.mul (Nat.shiftRight x 1) k = x / 2 * k by rw [nmul, nshr, Nat.pow_one], and_one]
  rw [zres_spec _ _ _ (by omega) hm, zdec_eq]
  congr 1
  by_cases h : x % 2 = 1
  · rw [if_pos h, if_pos h]; push_cast; grind
  · rw [if_neg h, if_neg h]; push_cast; grind

theorem zres_z1 (x q : Nat) (hm : x / 2 < 2 ^ q) :
    zres (Nat.shiftRight x 1) (Nat.land x 1) (Nat.sub (Nat.shiftLeft 1 q) 1) (Nat.shiftLeft 1 q) = res q (zdec x) := by
  have := zres_z x 1 q (by omega)
  rw [show Nat.mul (Nat.shiftRight x 1) 1 = Nat.shiftRight x 1 from Nat.mul_one _] at this
  rw [this]; simp

/-! ## The input lists -/

theorem map_toN (h : Nat → Nat) (q : Nat) : ∀ (n : Nat) (L : List Nat), L.length = n + 1 →
    (∀ x ∈ L, h x = res q (zdec x)) →
    L.map h = toN q (fun e => if e ≤ n then zdec (L.getD (n - e) 0) else 0) n
  | 0, [x], _, hh => by simp [toN, toL, hh x (by simp)]
  | n + 1, x :: L, hl, hh => by
    simp only [List.length_cons, Nat.add_right_cancel_iff] at hl
    rw [List.map_cons, map_toN h q n L hl (fun y hy => hh y (List.mem_cons_of_mem _ hy)), toN_succ,
      hh x (by simp)]
    simp only [Nat.le_refl, ↓reduceIte, Nat.sub_self, List.getD_cons_zero]
    congr 1
    unfold toN; congr 1; apply toL_congr; intro e he
    rw [if_pos he, if_pos (by omega), show n + 1 - e = (n - e) + 1 by omega, List.getD_cons_succ]

def dksN : Nat → List Nat
  | 0 => [1]
  | n + 1 => (n + 2) :: dksN n

theorem dks_eq : dks = dksN 23 := rfl

theorem zip_toN (h : Nat → Nat → Nat) (q : Nat) : ∀ (n : Nat) (L : List Nat), L.length = n + 2 →
    (∀ x ∈ L, ∀ k, k ≤ n + 1 → h x k = res q ((k : Int) * zdec x)) →
    List.zipWith h L (dksN n) =
      toN q (fun e => if e ≤ n then ((e + 1 : Nat) : Int) * zdec (L.getD (n - e) 0) else 0) n
  | 0, [x, y], _, hh => by simp [toN, toL, dksN, hh x (by simp) 1 (by omega)]
  | n + 1, x :: L, hl, hh => by
    simp only [List.length_cons, Nat.add_right_cancel_iff] at hl
    rw [dksN, List.zipWith_cons_cons, zip_toN h q n L hl (fun y hy k hk => hh y (List.mem_cons_of_mem _ hy) k (by omega)),
      toN_succ, hh x (by simp) (n + 2) (by omega)]
    simp only [Nat.le_refl, ↓reduceIte, Nat.sub_self, List.getD_cons_zero]
    congr 1
    unfold toN; congr 1; apply toL_congr; intro e he
    rw [if_pos he, if_pos (by omega), show n + 1 - e = (n - e) + 1 by omega, List.getD_cons_succ]

/-! ## The whole run -/

def fX (xs : List Nat) (e : Nat) : Int := if e ≤ 24 then zdec (xs.getD (24 - e) 0) else 0
def gX (xs : List Nat) (e : Nat) : Int := if e ≤ 23 then ((e + 1 : Nat) : Int) * zdec (xs.getD (23 - e) 0) else 0

theorem width_le (k i : Nat) : coefficientWidth k i ≤ k := by
  unfold coefficientWidth clampWidth
  split <;> simp only <;> omega

set_option exponentiation.threshold 4000 in
theorem FbN_le (e : Nat) : FbN e ≤ 2 ^ 3483 := by
  unfold FbN
  split
  · exact Nat.one_le_two_pow
  · split
    · exact Nat.pow_le_pow_right (by decide) (by have := width_le 3484 (24 - e); omega)
    · exact Nat.zero_le _

theorem natAbs_zdec (x : Nat) : (zdec x).natAbs = x / 2 := by
  unfold zdec; split <;> omega

theorem zenc_spec (a : Nat) (L : Int) (hL : L.natAbs < 2 ^ a) :
    zdec (Nat.add (Nat.shiftLeft (Nat.add (Nat.sub (res (a + 1) L) (Nat.mul (Nat.shiftRight (res (a + 1) L) a) (Nat.shiftLeft 1 (a + 1))))
      (Nat.sub (Nat.mul (Nat.shiftRight (res (a + 1) L) a) (Nat.shiftLeft 1 (a + 1))) (res (a + 1) L))) 1)
      (Nat.shiftRight (res (a + 1) L) a)) = L := by
  rw [mag_spec a L hL]
  have hs : Nat.shiftRight (res (a + 1) L) a = if L < 0 then 1 else 0 := (res_val a L hL).1
  rw [hs, nadd, nshl, Nat.pow_one]
  unfold zdec
  by_cases h : L < 0
  · rw [if_pos h, if_pos (by omega), show (L.natAbs * 2 + 1) / 2 = L.natAbs by omega]; omega
  · rw [if_neg h, if_neg (by omega), show (L.natAbs * 2 + 0) / 2 = L.natAbs by omega]; omega

def initA (xs : List Nat) : List Nat :=
  xs.map (fun x => zres (Nat.shiftRight x 1) (Nat.land x 1) (Nat.sub (Nat.shiftLeft 1 3485) 1) (Nat.shiftLeft 1 3485))

def initB (xs : List Nat) : List Nat :=
  List.zipWith (fun x k => zres (Nat.mul (Nat.shiftRight x 1) k) (Nat.land x 1) (Nat.sub (Nat.shiftLeft 1 3489) 1)
    (Nat.shiftLeft 1 3489)) xs dks

def zencW (u : Nat) : Nat :=
  Nat.add (Nat.shiftLeft (Nat.add (Nat.sub u (Nat.mul (Nat.shiftRight u 81024) (Nat.shiftLeft 1 81025)))
    (Nat.sub (Nat.mul (Nat.shiftRight u 81024) (Nat.shiftLeft 1 81025)) u)) 1) (Nat.shiftRight u 81024)

theorem lowRun_eq (xs : List Nat) : lowRun xs =
    (zencW (hd0 (lrunR lparams (initB xs) (lstep 3485 3489 3500 3484 3488 true [] (initA xs) (initB xs) Prod.mk).1
        (lstep 3485 3489 3500 3484 3488 true [] (initA xs) (initB xs) Prod.mk).2).1),
      (lrunR lparams (initB xs) (lstep 3485 3489 3500 3484 3488 true [] (initA xs) (initB xs) Prod.mk).1
        (lstep 3485 3489 3500 3484 3488 true [] (initA xs) (initB xs) Prod.mk).2).2) := by
  unfold lowRun
  simp only
  rw [lstep_cps, lrun_cps]
  rfl

theorem qw_vals : qw 1 = 3489 ∧ qw 2 = 3500 ∧ qw 24 = 81025 := by decide

set_option exponentiation.threshold 100000 in
/-- The low-part run on encoded coefficients: no failed check means the specification's result. -/
theorem lowRun_spec (xs : List Nat) (hlen : xs.length = 25) (h0 : zdec (xs.getD 0 0) = 1)
    (hxb : ∀ x ∈ xs, x / 2 ≤ 2 ^ 3483) (hb : ∀ e, (fX xs e).natAbs ≤ FbN e) (hbad : (lowRun xs).2 = 0) :
    normalResultant (toL (fX xs) 24) (toL (gX xs) 23) = some (zdec (lowRun xs).1) := by
  have hf : ∀ e, 24 < e → fX xs e = 0 := fun e he => by unfold fX; rw [if_neg (by omega)]
  have hg : ∀ e, 23 < e → gX xs e = 0 := fun e he => by unfold gX; rw [if_neg (by omega)]
  have hgf : ∀ e, e ≤ 23 → gX xs e = ((e + 1 : Nat) : Int) * fX xs (e + 1) := by
    intro e he; unfold gX fX; rw [if_pos he, if_pos (by omega), show 24 - (e + 1) = 23 - e by omega]
  have hgb : ∀ e, (gX xs e).natAbs ≤ GbN e := by
    intro e
    by_cases he : e ≤ 23
    · rw [hgf e he, Int.natAbs_mul]
      unfold GbN; rw [if_pos (by omega)]
      simp only [Int.natAbs_natCast]
      exact Nat.mul_le_mul_left _ (hb (e + 1))
    · rw [hg e (by omega)]; exact Nat.zero_le _
  have hgw : ∀ e, (gX xs e).natAbs < 2 ^ (qw 1 - 1) := by
    intro e
    rw [qw_vals.1]
    have h1 := hgb e
    have h2 : GbN e ≤ 24 * 2 ^ 3483 := by
      unfold GbN; split
      · exact Nat.mul_le_mul (by omega) (FbN_le _)
      · exact Nat.zero_le _
    have h3 : 24 * 2 ^ 3483 < 2 ^ (3489 - 1) := by
      have e : (2 : Nat) ^ (3489 - 1) = 2 ^ 3483 * 2 ^ 5 := by rw [← Nat.pow_add]
      have hp := Nat.two_pow_pos 3483
      rw [e]; generalize 2 ^ 3483 = P at hp ⊢; omega
    omega
  have hfw : ∀ e, e ≤ 24 → (fX xs e).natAbs < 2 ^ 3484 := fun e _ =>
    Nat.lt_of_le_of_lt (Nat.le_trans (hb e) (FbN_le e)) (Nat.pow_lt_pow_right (by decide) (by decide))
  have hf24 : fX xs 24 = 1 := by unfold fX; simpa using h0
  -- the input residues
  have hA0 : initA xs = toN 3485 (fX xs) 24 := by
    unfold initA
    rw [map_toN _ 3485 24 xs hlen (fun x hx => zres_z1 x 3485 (Nat.lt_of_le_of_lt (hxb x hx)
      (Nat.pow_lt_pow_right (by decide) (by decide))))]
    rfl
  have hB0 : initB xs = toN 3489 (gX xs) 23 := by
    unfold initB
    rw [dks_eq, zip_toN _ 3489 23 xs hlen (fun x hx k hk => zres_z x k 3489 (by
      have := hxb x hx
      have h3 : 24 * 2 ^ 3483 < 2 ^ 3489 := by
        have e : (2 : Nat) ^ 3489 = 2 ^ 3483 * 2 ^ 6 := by rw [← Nat.pow_add]
        have hp := Nat.two_pow_pos 3483
        rw [e]; generalize 2 ^ 3483 = P at hp ⊢; omega
      calc x / 2 * k ≤ 2 ^ 3483 * 24 := Nat.mul_le_mul this (by omega)
        _ < 2 ^ 3489 := by rw [Nat.mul_comm]; exact h3))]
    rfl
  -- step 0 (no division)
  obtain ⟨H0, b0, hst0, hok0⟩ := lstep_spec 3484 3488 3500 true [] (fX xs) (gX xs) (chainP (fX xs) (gX xs) 24 1).2 22
    (by decide) (by decide) (by decide)
    (fun e he => hfw e (by omega))
    (fun e he => by have := hgw e; rwa [qw_vals.1] at this)
    (fun _ => hf24) (fun h => absurd h (by decide))
    (fun e _ => by rw [chain_first]; simp)
    Prod.mk
  rw [lowRun_eq, hA0, hB0, hst0] at hbad ⊢
  simp only at hbad ⊢
  have hb0 : b0 = 0 := by
    have := lrunR_mono lparams (toN 3489 (gX xs) 23) H0 b0; omega
  obtain ⟨hH0, hC0⟩ := hok0 hb0
  -- steps 1 … 22
  obtain ⟨hF, hLall⟩ := lrunR_spec (fX xs) (gX xs) hf hg hb hgb hgw lparams 1 _ H0 b0 stepsOK_lparams
    (Nat.le_refl _) (by rw [qw_vals.1]; rfl) (by rw [hH0, qw_vals.2.1])
    (fun k' hk' => by
      rcases Nat.le_one_iff_eq_zero_or_eq_one.1 hk' with h | h <;> subst h
      · show gX xs 23 ≠ 0
        rw [hgf 23 (by decide), hf24]; decide
      · exact hC0)
    hbad
  rw [hF, qw_vals.2.2]
  -- the result
  have hdeg : ∀ e, 24 - 1 < e → gX xs e = 0 := fun e he => hg e (by omega)
  rw [normalResultant_chain (fX xs) (gX xs) 24 (by decide) hf hdeg (by rw [hf24]; decide) hLall]
  have hbnd := chain_bound (fX xs) (gX xs) hf hg hb hgb 24 (by decide) (by decide)
    (fun k' hk' => hLall k' (by omega)) 0 (by decide)
  rw [qw_vals.2.2] at hbnd
  have e0 : toN 81025 (chainP (fX xs) (gX xs) 24 23).2 0 = [res 81025 ((chainP (fX xs) (gX xs) 24 23).2 0)] := rfl
  rw [e0, hd0_cons]
  unfold zencW
  rw [zenc_spec 81024 _ hbnd]

end V9

namespace V9

theorem toL_fX (f0 f1 f2 f3 f4 f5 f6 f7 f8 f9 f10 f11 f12 f13 f14 f15 f16 f17 f18 f19 f20 f21 f22 f23 f24 : Nat) :
    toL (fX [f0, f1, f2, f3, f4, f5, f6, f7, f8, f9, f10, f11, f12, f13, f14, f15, f16, f17, f18, f19, f20, f21, f22, f23, f24]) 24
      = [f0, f1, f2, f3, f4, f5, f6, f7, f8, f9, f10, f11, f12, f13, f14, f15, f16, f17, f18, f19, f20, f21, f22, f23, f24].map zdec := by
  simp [toL, fX]

theorem toL_gX (f0 f1 f2 f3 f4 f5 f6 f7 f8 f9 f10 f11 f12 f13 f14 f15 f16 f17 f18 f19 f20 f21 f22 f23 f24 : Nat) :
    toL (gX [f0, f1, f2, f3, f4, f5, f6, f7, f8, f9, f10, f11, f12, f13, f14, f15, f16, f17, f18, f19, f20, f21, f22, f23, f24]) 23
      = derivHL ([f0, f1, f2, f3, f4, f5, f6, f7, f8, f9, f10, f11, f12, f13, f14, f15, f16, f17, f18, f19, f20, f21, f22, f23, f24].map zdec) := by
  simp [toL, gX, derivHL, List.range, List.range.loop]

end V9

namespace V9

/-- The low-part run as one shared graph (generated by `gen/mklowdag.py` from `lowRun`). -/
def lowDag (f0 f1 f2 f3 f4 f5 f6 f7 f8 f9 f10 f11 f12 f13 f14 f15 f16 f17 f18 f19 f20 f21 f22 f23 f24 : Nat) : Nat × Nat :=
  natdag% "shl 1 3485
shl 1 3489
shr x0 1
land x0 1
sub v0 1
sub 1 v3
mul v5 v2
sub v0 v2
mul v3 v7
add v6 v8
land v9 v4
shr x1 1
land x1 1
sub 1 v12
mul v13 v11
sub v0 v11
mul v12 v15
add v14 v16
land v17 v4
shr x2 1
land x2 1
sub 1 v20
mul v21 v19
sub v0 v19
mul v20 v23
add v22 v24
land v25 v4
shr x3 1
land x3 1
sub 1 v28
mul v29 v27
sub v0 v27
mul v28 v31
add v30 v32
land v33 v4
shr x4 1
land x4 1
sub 1 v36
mul v37 v35
sub v0 v35
mul v36 v39
add v38 v40
land v41 v4
shr x5 1
land x5 1
sub 1 v44
mul v45 v43
sub v0 v43
mul v44 v47
add v46 v48
land v49 v4
shr x6 1
land x6 1
sub 1 v52
mul v53 v51
sub v0 v51
mul v52 v55
add v54 v56
land v57 v4
shr x7 1
land x7 1
sub 1 v60
mul v61 v59
sub v0 v59
mul v60 v63
add v62 v64
land v65 v4
shr x8 1
land x8 1
sub 1 v68
mul v69 v67
sub v0 v67
mul v68 v71
add v70 v72
land v73 v4
shr x9 1
land x9 1
sub 1 v76
mul v77 v75
sub v0 v75
mul v76 v79
add v78 v80
land v81 v4
shr x10 1
land x10 1
sub 1 v84
mul v85 v83
sub v0 v83
mul v84 v87
add v86 v88
land v89 v4
shr x11 1
land x11 1
sub 1 v92
mul v93 v91
sub v0 v91
mul v92 v95
add v94 v96
land v97 v4
shr x12 1
land x12 1
sub 1 v100
mul v101 v99
sub v0 v99
mul v100 v103
add v102 v104
land v105 v4
shr x13 1
land x13 1
sub 1 v108
mul v109 v107
sub v0 v107
mul v108 v111
add v110 v112
land v113 v4
shr x14 1
land x14 1
sub 1 v116
mul v117 v115
sub v0 v115
mul v116 v119
add v118 v120
land v121 v4
shr x15 1
land x15 1
sub 1 v124
mul v125 v123
sub v0 v123
mul v124 v127
add v126 v128
land v129 v4
shr x16 1
land x16 1
sub 1 v132
mul v133 v131
sub v0 v131
mul v132 v135
add v134 v136
land v137 v4
shr x17 1
land x17 1
sub 1 v140
mul v141 v139
sub v0 v139
mul v140 v143
add v142 v144
land v145 v4
shr x18 1
land x18 1
sub 1 v148
mul v149 v147
sub v0 v147
mul v148 v151
add v150 v152
land v153 v4
shr x19 1
land x19 1
sub 1 v156
mul v157 v155
sub v0 v155
mul v156 v159
add v158 v160
land v161 v4
shr x20 1
land x20 1
sub 1 v164
mul v165 v163
sub v0 v163
mul v164 v167
add v166 v168
land v169 v4
shr x21 1
land x21 1
sub 1 v172
mul v173 v171
sub v0 v171
mul v172 v175
add v174 v176
land v177 v4
shr x22 1
land x22 1
sub 1 v180
mul v181 v179
sub v0 v179
mul v180 v183
add v182 v184
land v185 v4
shr x23 1
land x23 1
sub 1 v188
mul v189 v187
sub v0 v187
mul v188 v191
add v190 v192
land v193 v4
shr x24 1
land x24 1
sub 1 v196
mul v197 v195
sub v0 v195
mul v196 v199
add v198 v200
land v201 v4
mul v2 24
sub v1 1
mul v5 v203
sub v1 v203
mul v3 v206
add v205 v207
land v208 v204
mul v11 23
mul v13 v210
sub v1 v210
mul v12 v212
add v211 v213
land v214 v204
mul v19 22
mul v21 v216
sub v1 v216
mul v20 v218
add v217 v219
land v220 v204
mul v27 21
mul v29 v222
sub v1 v222
mul v28 v224
add v223 v225
land v226 v204
mul v35 20
mul v37 v228
sub v1 v228
mul v36 v230
add v229 v231
land v232 v204
mul v43 19
mul v45 v234
sub v1 v234
mul v44 v236
add v235 v237
land v238 v204
mul v51 18
mul v53 v240
sub v1 v240
mul v52 v242
add v241 v243
land v244 v204
mul v59 17
mul v61 v246
sub v1 v246
mul v60 v248
add v247 v249
land v250 v204
mul v67 16
mul v69 v252
sub v1 v252
mul v68 v254
add v253 v255
land v256 v204
mul v75 15
mul v77 v258
sub v1 v258
mul v76 v260
add v259 v261
land v262 v204
mul v83 14
mul v85 v264
sub v1 v264
mul v84 v266
add v265 v267
land v268 v204
mul v91 13
mul v93 v270
sub v1 v270
mul v92 v272
add v271 v273
land v274 v204
mul v99 12
mul v101 v276
sub v1 v276
mul v100 v278
add v277 v279
land v280 v204
mul v107 11
mul v109 v282
sub v1 v282
mul v108 v284
add v283 v285
land v286 v204
mul v115 10
mul v117 v288
sub v1 v288
mul v116 v290
add v289 v291
land v292 v204
mul v123 9
mul v125 v294
sub v1 v294
mul v124 v296
add v295 v297
land v298 v204
mul v131 8
mul v133 v300
sub v1 v300
mul v132 v302
add v301 v303
land v304 v204
mul v139 7
mul v141 v306
sub v1 v306
mul v140 v308
add v307 v309
land v310 v204
mul v147 6
mul v149 v312
sub v1 v312
mul v148 v314
add v313 v315
land v316 v204
mul v155 5
mul v157 v318
sub v1 v318
mul v156 v320
add v319 v321
land v322 v204
mul v163 4
mul v165 v324
sub v1 v324
mul v164 v326
add v325 v327
land v328 v204
mul v171 3
mul v173 v330
sub v1 v330
mul v172 v332
add v331 v333
land v334 v204
mul v179 2
mul v181 v336
sub v1 v336
mul v180 v338
add v337 v339
land v340 v204
mul v187 1
mul v189 v342
sub v1 v342
mul v188 v344
add v343 v345
land v346 v204
shr v10 3484
mul v348 v0
sub v10 v349
sub v349 v10
add v350 v351
land v10 18446744073709551615
shl 0 1
add 3500 v354
shl 1 v355
sub v356 1
shl v356 2
sub v356 v0
sub v356 v1
shr v209 3488
mul v361 v360
add v209 v362
shr v18 3484
mul v364 v359
add v18 v365
shr v215 3488
mul v367 v360
add v215 v368
shl 1 3500
sub v370 1
mul v363 1
land v372 v357
mul v373 v373
land v374 v357
shl v373 0
land v376 v357
mul v348 v377
sub 1 v348
sub v356 v377
mul v379 v380
add v378 v381
shl v369 0
land v383 v357
mul v379 v384
sub 1 v379
sub v356 v384
mul v386 v387
add v385 v388
add v389 v356
mul v366 v373
land v391 v357
sub v390 v392
mul v393 1
land v394 v357
shl v375 3485
land v396 v357
shl v382 3489
land v398 v357
shl v395 3489
land v400 v357
mul v375 v26
mul v382 v221
add v402 v403
mul v395 v215
add v404 v405
shr v26 3484
mul v407 v397
shr v221 3488
mul v409 v399
add v408 v410
mul v367 v401
add v411 v412
add v406 v358
sub v414 v413
shr v415 v354
land v416 v371
mul v375 v34
mul v382 v227
add v418 v419
mul v395 v221
add v420 v421
shr v34 3484
mul v423 v397
shr v227 3488
mul v425 v399
add v424 v426
mul v409 v401
add v427 v428
add v422 v358
sub v430 v429
shr v431 v354
land v432 v371
mul v375 v42
mul v382 v233
add v434 v435
mul v395 v227
add v436 v437
shr v42 3484
mul v439 v397
shr v233 3488
mul v441 v399
add v440 v442
mul v425 v401
add v443 v444
add v438 v358
sub v446 v445
shr v447 v354
land v448 v371
mul v375 v50
mul v382 v239
add v450 v451
mul v395 v233
add v452 v453
shr v50 3484
mul v455 v397
shr v239 3488
mul v457 v399
add v456 v458
mul v441 v401
add v459 v460
add v454 v358
sub v462 v461
shr v463 v354
land v464 v371
mul v375 v58
mul v382 v245
add v466 v467
mul v395 v239
add v468 v469
shr v58 3484
mul v471 v397
shr v245 3488
mul v473 v399
add v472 v474
mul v457 v401
add v475 v476
add v470 v358
sub v478 v477
shr v479 v354
land v480 v371
mul v375 v66
mul v382 v251
add v482 v483
mul v395 v245
add v484 v485
shr v66 3484
mul v487 v397
shr v251 3488
mul v489 v399
add v488 v490
mul v473 v401
add v491 v492
add v486 v358
sub v494 v493
shr v495 v354
land v496 v371
mul v375 v74
mul v382 v257
add v498 v499
mul v395 v251
add v500 v501
shr v74 3484
mul v503 v397
shr v257 3488
mul v505 v399
add v504 v506
mul v489 v401
add v507 v508
add v502 v358
sub v510 v509
shr v511 v354
land v512 v371
mul v375 v82
mul v382 v263
add v514 v515
mul v395 v257
add v516 v517
shr v82 3484
mul v519 v397
shr v263 3488
mul v521 v399
add v520 v522
mul v505 v401
add v523 v524
add v518 v358
sub v526 v525
shr v527 v354
land v528 v371
mul v375 v90
mul v382 v269
add v530 v531
mul v395 v263
add v532 v533
shr v90 3484
mul v535 v397
shr v269 3488
mul v537 v399
add v536 v538
mul v521 v401
add v539 v540
add v534 v358
sub v542 v541
shr v543 v354
land v544 v371
mul v375 v98
mul v382 v275
add v546 v547
mul v395 v269
add v548 v549
shr v98 3484
mul v551 v397
shr v275 3488
mul v553 v399
add v552 v554
mul v537 v401
add v555 v556
add v550 v358
sub v558 v557
shr v559 v354
land v560 v371
mul v375 v106
mul v382 v281
add v562 v563
mul v395 v275
add v564 v565
shr v106 3484
mul v567 v397
shr v281 3488
mul v569 v399
add v568 v570
mul v553 v401
add v571 v572
add v566 v358
sub v574 v573
shr v575 v354
land v576 v371
mul v375 v114
mul v382 v287
add v578 v579
mul v395 v281
add v580 v581
shr v114 3484
mul v583 v397
shr v287 3488
mul v585 v399
add v584 v586
mul v569 v401
add v587 v588
add v582 v358
sub v590 v589
shr v591 v354
land v592 v371
mul v375 v122
mul v382 v293
add v594 v595
mul v395 v287
add v596 v597
shr v122 3484
mul v599 v397
shr v293 3488
mul v601 v399
add v600 v602
mul v585 v401
add v603 v604
add v598 v358
sub v606 v605
shr v607 v354
land v608 v371
mul v375 v130
mul v382 v299
add v610 v611
mul v395 v293
add v612 v613
shr v130 3484
mul v615 v397
shr v299 3488
mul v617 v399
add v616 v618
mul v601 v401
add v619 v620
add v614 v358
sub v622 v621
shr v623 v354
land v624 v371
mul v375 v138
mul v382 v305
add v626 v627
mul v395 v299
add v628 v629
shr v138 3484
mul v631 v397
shr v305 3488
mul v633 v399
add v632 v634
mul v617 v401
add v635 v636
add v630 v358
sub v638 v637
shr v639 v354
land v640 v371
mul v375 v146
mul v382 v311
add v642 v643
mul v395 v305
add v644 v645
shr v146 3484
mul v647 v397
shr v311 3488
mul v649 v399
add v648 v650
mul v633 v401
add v651 v652
add v646 v358
sub v654 v653
shr v655 v354
land v656 v371
mul v375 v154
mul v382 v317
add v658 v659
mul v395 v311
add v660 v661
shr v154 3484
mul v663 v397
shr v317 3488
mul v665 v399
add v664 v666
mul v649 v401
add v667 v668
add v662 v358
sub v670 v669
shr v671 v354
land v672 v371
mul v375 v162
mul v382 v323
add v674 v675
mul v395 v317
add v676 v677
shr v162 3484
mul v679 v397
shr v323 3488
mul v681 v399
add v680 v682
mul v665 v401
add v683 v684
add v678 v358
sub v686 v685
shr v687 v354
land v688 v371
mul v375 v170
mul v382 v329
add v690 v691
mul v395 v323
add v692 v693
shr v170 3484
mul v695 v397
shr v329 3488
mul v697 v399
add v696 v698
mul v681 v401
add v699 v700
add v694 v358
sub v702 v701
shr v703 v354
land v704 v371
mul v375 v178
mul v382 v335
add v706 v707
mul v395 v329
add v708 v709
shr v178 3484
mul v711 v397
shr v335 3488
mul v713 v399
add v712 v714
mul v697 v401
add v715 v716
add v710 v358
sub v718 v717
shr v719 v354
land v720 v371
mul v375 v186
mul v382 v341
add v722 v723
mul v395 v335
add v724 v725
shr v186 3484
mul v727 v397
shr v341 3488
mul v729 v399
add v728 v730
mul v713 v401
add v731 v732
add v726 v358
sub v734 v733
shr v735 v354
land v736 v371
mul v375 v194
mul v382 v347
add v738 v739
mul v395 v341
add v740 v741
shr v194 3484
mul v743 v397
shr v347 3488
mul v745 v399
add v744 v746
mul v729 v401
add v747 v748
add v742 v358
sub v750 v749
shr v751 v354
land v752 v371
mul v375 v202
mul v395 v347
add v754 v755
shr v202 3484
mul v757 v397
mul v745 v401
add v758 v759
add v756 v358
sub v761 v760
shr v762 v354
land v763 v371
sub 1 v417
mul v361 v1
sub v209 v766
sub v766 v209
add v767 v768
land v209 18446744073709551615
shl 1 64
gcd v770 v771
mul v772 157587932685088877
land v773 18446744073709551615
shr v774 58
shl v775 3
shr x26 v776
land v777 255
shl v778 1
add 3957 v779
shl 1 v780
sub v781 1
shl v781 2
sub v781 v1
sub v781 v370
shr v417 3499
mul v786 v785
add v417 v787
mul v367 v784
add v215 v789
shr v433 3499
mul v791 v785
add v433 v792
shl 1 3957
sub v794 1
shr v769 v778
shl 1 6
sub v797 1
land v796 v798
mul v799 v796
land v800 v798
add v798 3
sub v802 v801
mul v796 v803
land v804 v798
shl 1 12
sub v806 1
land v796 v807
mul v808 v805
land v809 v807
add v807 3
sub v811 v810
mul v805 v812
land v813 v807
shl 1 24
sub v815 1
land v796 v816
mul v817 v814
land v818 v816
add v816 3
sub v820 v819
mul v814 v821
land v822 v816
shl 1 48
sub v824 1
land v796 v825
mul v826 v823
land v827 v825
add v825 3
sub v829 v828
mul v823 v830
land v831 v825
shl 1 96
sub v833 1
land v796 v834
mul v835 v832
land v836 v834
add v834 3
sub v838 v837
mul v832 v839
land v840 v834
shl 1 192
sub v842 1
land v796 v843
mul v844 v841
land v845 v843
add v843 3
sub v847 v846
mul v841 v848
land v849 v843
shl 1 384
sub v851 1
land v796 v852
mul v853 v850
land v854 v852
add v852 3
sub v856 v855
mul v850 v857
land v858 v852
shl 1 768
sub v860 1
land v796 v861
mul v862 v859
land v863 v861
add v861 3
sub v865 v864
mul v859 v866
land v867 v861
shl 1 1536
sub v869 1
land v796 v870
mul v871 v868
land v872 v870
add v870 3
sub v874 v873
mul v868 v875
land v876 v870
shl 1 3072
sub v878 1
land v796 v879
mul v880 v877
land v881 v879
add v879 3
sub v883 v882
mul v877 v884
land v885 v879
shl 1 4085
sub v887 1
land v796 v888
mul v889 v886
land v890 v888
add v888 3
sub v892 v891
mul v886 v893
land v894 v888
mul v788 v895
land v896 v782
mul v897 v897
land v898 v782
shl v897 v778
land v900 v782
mul v361 v901
sub 1 v361
sub v781 v901
mul v903 v904
add v902 v905
shl v793 v778
land v907 v782
mul v903 v908
sub 1 v903
sub v781 v908
mul v910 v911
add v909 v912
add v913 v781
mul v790 v897
land v915 v782
sub v914 v916
mul v917 v895
land v918 v782
shl v899 3489
land v920 v782
shl v906 3500
land v922 v782
shl v919 3500
land v924 v782
mul v899 v221
mul v906 v449
add v926 v927
mul v919 v433
add v928 v929
mul v409 v921
shr v449 3499
mul v932 v923
add v931 v933
mul v791 v925
add v934 v935
add v930 v783
sub v937 v936
shr v938 v779
land v939 v795
mul v899 v227
mul v906 v465
add v941 v942
mul v919 v449
add v943 v944
mul v425 v921
shr v465 3499
mul v947 v923
add v946 v948
mul v932 v925
add v949 v950
add v945 v783
sub v952 v951
shr v953 v779
land v954 v795
mul v899 v233
mul v906 v481
add v956 v957
mul v919 v465
add v958 v959
mul v441 v921
shr v481 3499
mul v962 v923
add v961 v963
mul v947 v925
add v964 v965
add v960 v783
sub v967 v966
shr v968 v779
land v969 v795
mul v899 v239
mul v906 v497
add v971 v972
mul v919 v481
add v973 v974
mul v457 v921
shr v497 3499
mul v977 v923
add v976 v978
mul v962 v925
add v979 v980
add v975 v783
sub v982 v981
shr v983 v779
land v984 v795
mul v899 v245
mul v906 v513
add v986 v987
mul v919 v497
add v988 v989
mul v473 v921
shr v513 3499
mul v992 v923
add v991 v993
mul v977 v925
add v994 v995
add v990 v783
sub v997 v996
shr v998 v779
land v999 v795
mul v899 v251
mul v906 v529
add v1001 v1002
mul v919 v513
add v1003 v1004
mul v489 v921
shr v529 3499
mul v1007 v923
add v1006 v1008
mul v992 v925
add v1009 v1010
add v1005 v783
sub v1012 v1011
shr v1013 v779
land v1014 v795
mul v899 v257
mul v906 v545
add v1016 v1017
mul v919 v529
add v1018 v1019
mul v505 v921
shr v545 3499
mul v1022 v923
add v1021 v1023
mul v1007 v925
add v1024 v1025
add v1020 v783
sub v1027 v1026
shr v1028 v779
land v1029 v795
mul v899 v263
mul v906 v561
add v1031 v1032
mul v919 v545
add v1033 v1034
mul v521 v921
shr v561 3499
mul v1037 v923
add v1036 v1038
mul v1022 v925
add v1039 v1040
add v1035 v783
sub v1042 v1041
shr v1043 v779
land v1044 v795
mul v899 v269
mul v906 v577
add v1046 v1047
mul v919 v561
add v1048 v1049
mul v537 v921
shr v577 3499
mul v1052 v923
add v1051 v1053
mul v1037 v925
add v1054 v1055
add v1050 v783
sub v1057 v1056
shr v1058 v779
land v1059 v795
mul v899 v275
mul v906 v593
add v1061 v1062
mul v919 v577
add v1063 v1064
mul v553 v921
shr v593 3499
mul v1067 v923
add v1066 v1068
mul v1052 v925
add v1069 v1070
add v1065 v783
sub v1072 v1071
shr v1073 v779
land v1074 v795
mul v899 v281
mul v906 v609
add v1076 v1077
mul v919 v593
add v1078 v1079
mul v569 v921
shr v609 3499
mul v1082 v923
add v1081 v1083
mul v1067 v925
add v1084 v1085
add v1080 v783
sub v1087 v1086
shr v1088 v779
land v1089 v795
mul v899 v287
mul v906 v625
add v1091 v1092
mul v919 v609
add v1093 v1094
mul v585 v921
shr v625 3499
mul v1097 v923
add v1096 v1098
mul v1082 v925
add v1099 v1100
add v1095 v783
sub v1102 v1101
shr v1103 v779
land v1104 v795
mul v899 v293
mul v906 v641
add v1106 v1107
mul v919 v625
add v1108 v1109
mul v601 v921
shr v641 3499
mul v1112 v923
add v1111 v1113
mul v1097 v925
add v1114 v1115
add v1110 v783
sub v1117 v1116
shr v1118 v779
land v1119 v795
mul v899 v299
mul v906 v657
add v1121 v1122
mul v919 v641
add v1123 v1124
mul v617 v921
shr v657 3499
mul v1127 v923
add v1126 v1128
mul v1112 v925
add v1129 v1130
add v1125 v783
sub v1132 v1131
shr v1133 v779
land v1134 v795
mul v899 v305
mul v906 v673
add v1136 v1137
mul v919 v657
add v1138 v1139
mul v633 v921
shr v673 3499
mul v1142 v923
add v1141 v1143
mul v1127 v925
add v1144 v1145
add v1140 v783
sub v1147 v1146
shr v1148 v779
land v1149 v795
mul v899 v311
mul v906 v689
add v1151 v1152
mul v919 v673
add v1153 v1154
mul v649 v921
shr v689 3499
mul v1157 v923
add v1156 v1158
mul v1142 v925
add v1159 v1160
add v1155 v783
sub v1162 v1161
shr v1163 v779
land v1164 v795
mul v899 v317
mul v906 v705
add v1166 v1167
mul v919 v689
add v1168 v1169
mul v665 v921
shr v705 3499
mul v1172 v923
add v1171 v1173
mul v1157 v925
add v1174 v1175
add v1170 v783
sub v1177 v1176
shr v1178 v779
land v1179 v795
mul v899 v323
mul v906 v721
add v1181 v1182
mul v919 v705
add v1183 v1184
mul v681 v921
shr v721 3499
mul v1187 v923
add v1186 v1188
mul v1172 v925
add v1189 v1190
add v1185 v783
sub v1192 v1191
shr v1193 v779
land v1194 v795
mul v899 v329
mul v906 v737
add v1196 v1197
mul v919 v721
add v1198 v1199
mul v697 v921
shr v737 3499
mul v1202 v923
add v1201 v1203
mul v1187 v925
add v1204 v1205
add v1200 v783
sub v1207 v1206
shr v1208 v779
land v1209 v795
mul v899 v335
mul v906 v753
add v1211 v1212
mul v919 v737
add v1213 v1214
mul v713 v921
shr v753 3499
mul v1217 v923
add v1216 v1218
mul v1202 v925
add v1219 v1220
add v1215 v783
sub v1222 v1221
shr v1223 v779
land v1224 v795
mul v899 v341
mul v906 v764
add v1226 v1227
mul v919 v753
add v1228 v1229
mul v729 v921
shr v764 3499
mul v1232 v923
add v1231 v1233
mul v1217 v925
add v1234 v1235
add v1230 v783
sub v1237 v1236
shr v1238 v779
land v1239 v795
mul v899 v347
mul v919 v764
add v1241 v1242
mul v745 v921
mul v1232 v925
add v1244 v1245
add v1243 v783
sub v1247 v1246
shr v1248 v779
land v1249 v795
shr v770 v778
land v1251 1
sub 1 v1252
shl 1 v778
sub v1254 1
land v770 v1255
add v1253 v1256
sub 1 v940
add v1257 v1258
add v765 v1259
mul v786 v370
sub v417 v1261
sub v1261 v417
add v1262 v1263
land v417 18446744073709551615
gcd v1265 v771
mul v1266 157587932685088877
land v1267 18446744073709551615
shr v1268 58
shl v1269 3
shr x26 v1270
land v1271 255
shl v1272 1
add 4711 v1273
shl 1 v1274
sub v1275 1
shl v1275 2
sub v1275 v370
sub v1275 v794
shr v940 3956
mul v1280 v1279
add v940 v1281
mul v791 v1278
add v433 v1283
shr v955 3956
mul v1285 v1279
add v955 v1286
shl 1 4711
sub v1288 1
shr v1264 v1272
land v1290 v798
mul v1291 v1290
land v1292 v798
sub v802 v1293
mul v1290 v1294
land v1295 v798
land v1290 v807
mul v1297 v1296
land v1298 v807
sub v811 v1299
mul v1296 v1300
land v1301 v807
land v1290 v816
mul v1303 v1302
land v1304 v816
sub v820 v1305
mul v1302 v1306
land v1307 v816
land v1290 v825
mul v1309 v1308
land v1310 v825
sub v829 v1311
mul v1308 v1312
land v1313 v825
land v1290 v834
mul v1315 v1314
land v1316 v834
sub v838 v1317
mul v1314 v1318
land v1319 v834
land v1290 v843
mul v1321 v1320
land v1322 v843
sub v847 v1323
mul v1320 v1324
land v1325 v843
land v1290 v852
mul v1327 v1326
land v1328 v852
sub v856 v1329
mul v1326 v1330
land v1331 v852
land v1290 v861
mul v1333 v1332
land v1334 v861
sub v865 v1335
mul v1332 v1336
land v1337 v861
land v1290 v870
mul v1339 v1338
land v1340 v870
sub v874 v1341
mul v1338 v1342
land v1343 v870
land v1290 v879
mul v1345 v1344
land v1346 v879
sub v883 v1347
mul v1344 v1348
land v1349 v879
shl 1 4839
sub v1351 1
land v1290 v1352
mul v1353 v1350
land v1354 v1352
add v1352 3
sub v1356 v1355
mul v1350 v1357
land v1358 v1352
mul v1282 v1359
land v1360 v1276
mul v1361 v1361
land v1362 v1276
shl v1361 v1272
land v1364 v1276
mul v786 v1365
sub 1 v786
sub v1275 v1365
mul v1367 v1368
add v1366 v1369
shl v1287 v1272
land v1371 v1276
mul v1367 v1372
sub 1 v1367
sub v1275 v1372
mul v1374 v1375
add v1373 v1376
add v1377 v1275
mul v1284 v1361
land v1379 v1276
sub v1378 v1380
mul v1381 v1359
land v1382 v1276
shl v1363 3500
land v1384 v1276
shl v1370 3957
land v1386 v1276
shl v1383 3957
land v1388 v1276
mul v1363 v449
mul v1370 v970
add v1390 v1391
mul v1383 v955
add v1392 v1393
mul v932 v1385
shr v970 3956
mul v1396 v1387
add v1395 v1397
mul v1285 v1389
add v1398 v1399
add v1394 v1277
sub v1401 v1400
shr v1402 v1273
land v1403 v1289
mul v1363 v465
mul v1370 v985
add v1405 v1406
mul v1383 v970
add v1407 v1408
mul v947 v1385
shr v985 3956
mul v1411 v1387
add v1410 v1412
mul v1396 v1389
add v1413 v1414
add v1409 v1277
sub v1416 v1415
shr v1417 v1273
land v1418 v1289
mul v1363 v481
mul v1370 v1000
add v1420 v1421
mul v1383 v985
add v1422 v1423
mul v962 v1385
shr v1000 3956
mul v1426 v1387
add v1425 v1427
mul v1411 v1389
add v1428 v1429
add v1424 v1277
sub v1431 v1430
shr v1432 v1273
land v1433 v1289
mul v1363 v497
mul v1370 v1015
add v1435 v1436
mul v1383 v1000
add v1437 v1438
mul v977 v1385
shr v1015 3956
mul v1441 v1387
add v1440 v1442
mul v1426 v1389
add v1443 v1444
add v1439 v1277
sub v1446 v1445
shr v1447 v1273
land v1448 v1289
mul v1363 v513
mul v1370 v1030
add v1450 v1451
mul v1383 v1015
add v1452 v1453
mul v992 v1385
shr v1030 3956
mul v1456 v1387
add v1455 v1457
mul v1441 v1389
add v1458 v1459
add v1454 v1277
sub v1461 v1460
shr v1462 v1273
land v1463 v1289
mul v1363 v529
mul v1370 v1045
add v1465 v1466
mul v1383 v1030
add v1467 v1468
mul v1007 v1385
shr v1045 3956
mul v1471 v1387
add v1470 v1472
mul v1456 v1389
add v1473 v1474
add v1469 v1277
sub v1476 v1475
shr v1477 v1273
land v1478 v1289
mul v1363 v545
mul v1370 v1060
add v1480 v1481
mul v1383 v1045
add v1482 v1483
mul v1022 v1385
shr v1060 3956
mul v1486 v1387
add v1485 v1487
mul v1471 v1389
add v1488 v1489
add v1484 v1277
sub v1491 v1490
shr v1492 v1273
land v1493 v1289
mul v1363 v561
mul v1370 v1075
add v1495 v1496
mul v1383 v1060
add v1497 v1498
mul v1037 v1385
shr v1075 3956
mul v1501 v1387
add v1500 v1502
mul v1486 v1389
add v1503 v1504
add v1499 v1277
sub v1506 v1505
shr v1507 v1273
land v1508 v1289
mul v1363 v577
mul v1370 v1090
add v1510 v1511
mul v1383 v1075
add v1512 v1513
mul v1052 v1385
shr v1090 3956
mul v1516 v1387
add v1515 v1517
mul v1501 v1389
add v1518 v1519
add v1514 v1277
sub v1521 v1520
shr v1522 v1273
land v1523 v1289
mul v1363 v593
mul v1370 v1105
add v1525 v1526
mul v1383 v1090
add v1527 v1528
mul v1067 v1385
shr v1105 3956
mul v1531 v1387
add v1530 v1532
mul v1516 v1389
add v1533 v1534
add v1529 v1277
sub v1536 v1535
shr v1537 v1273
land v1538 v1289
mul v1363 v609
mul v1370 v1120
add v1540 v1541
mul v1383 v1105
add v1542 v1543
mul v1082 v1385
shr v1120 3956
mul v1546 v1387
add v1545 v1547
mul v1531 v1389
add v1548 v1549
add v1544 v1277
sub v1551 v1550
shr v1552 v1273
land v1553 v1289
mul v1363 v625
mul v1370 v1135
add v1555 v1556
mul v1383 v1120
add v1557 v1558
mul v1097 v1385
shr v1135 3956
mul v1561 v1387
add v1560 v1562
mul v1546 v1389
add v1563 v1564
add v1559 v1277
sub v1566 v1565
shr v1567 v1273
land v1568 v1289
mul v1363 v641
mul v1370 v1150
add v1570 v1571
mul v1383 v1135
add v1572 v1573
mul v1112 v1385
shr v1150 3956
mul v1576 v1387
add v1575 v1577
mul v1561 v1389
add v1578 v1579
add v1574 v1277
sub v1581 v1580
shr v1582 v1273
land v1583 v1289
mul v1363 v657
mul v1370 v1165
add v1585 v1586
mul v1383 v1150
add v1587 v1588
mul v1127 v1385
shr v1165 3956
mul v1591 v1387
add v1590 v1592
mul v1576 v1389
add v1593 v1594
add v1589 v1277
sub v1596 v1595
shr v1597 v1273
land v1598 v1289
mul v1363 v673
mul v1370 v1180
add v1600 v1601
mul v1383 v1165
add v1602 v1603
mul v1142 v1385
shr v1180 3956
mul v1606 v1387
add v1605 v1607
mul v1591 v1389
add v1608 v1609
add v1604 v1277
sub v1611 v1610
shr v1612 v1273
land v1613 v1289
mul v1363 v689
mul v1370 v1195
add v1615 v1616
mul v1383 v1180
add v1617 v1618
mul v1157 v1385
shr v1195 3956
mul v1621 v1387
add v1620 v1622
mul v1606 v1389
add v1623 v1624
add v1619 v1277
sub v1626 v1625
shr v1627 v1273
land v1628 v1289
mul v1363 v705
mul v1370 v1210
add v1630 v1631
mul v1383 v1195
add v1632 v1633
mul v1172 v1385
shr v1210 3956
mul v1636 v1387
add v1635 v1637
mul v1621 v1389
add v1638 v1639
add v1634 v1277
sub v1641 v1640
shr v1642 v1273
land v1643 v1289
mul v1363 v721
mul v1370 v1225
add v1645 v1646
mul v1383 v1210
add v1647 v1648
mul v1187 v1385
shr v1225 3956
mul v1651 v1387
add v1650 v1652
mul v1636 v1389
add v1653 v1654
add v1649 v1277
sub v1656 v1655
shr v1657 v1273
land v1658 v1289
mul v1363 v737
mul v1370 v1240
add v1660 v1661
mul v1383 v1225
add v1662 v1663
mul v1202 v1385
shr v1240 3956
mul v1666 v1387
add v1665 v1667
mul v1651 v1389
add v1668 v1669
add v1664 v1277
sub v1671 v1670
shr v1672 v1273
land v1673 v1289
mul v1363 v753
mul v1370 v1250
add v1675 v1676
mul v1383 v1240
add v1677 v1678
mul v1217 v1385
shr v1250 3956
mul v1681 v1387
add v1680 v1682
mul v1666 v1389
add v1683 v1684
add v1679 v1277
sub v1686 v1685
shr v1687 v1273
land v1688 v1289
mul v1363 v764
mul v1383 v1250
add v1690 v1691
mul v1232 v1385
mul v1681 v1389
add v1693 v1694
add v1692 v1277
sub v1696 v1695
shr v1697 v1273
land v1698 v1289
shr v1265 v1272
land v1700 1
sub 1 v1701
shl 1 v1272
sub v1703 1
land v1265 v1704
add v1702 v1705
sub 1 v1404
add v1706 v1707
add v1260 v1708
mul v1280 v794
sub v940 v1710
sub v1710 v940
add v1711 v1712
land v940 18446744073709551615
gcd v1714 v771
mul v1715 157587932685088877
land v1716 18446744073709551615
shr v1717 58
shl v1718 3
shr x26 v1719
land v1720 255
shl v1721 1
add 5759 v1722
shl 1 v1723
sub v1724 1
shl v1724 2
sub v1724 v794
sub v1724 v1288
shr v1404 4710
mul v1729 v1728
add v1404 v1730
mul v1285 v1727
add v955 v1732
shr v1419 4710
mul v1734 v1728
add v1419 v1735
shl 1 5759
sub v1737 1
shr v1713 v1721
land v1739 v798
mul v1740 v1739
land v1741 v798
sub v802 v1742
mul v1739 v1743
land v1744 v798
land v1739 v807
mul v1746 v1745
land v1747 v807
sub v811 v1748
mul v1745 v1749
land v1750 v807
land v1739 v816
mul v1752 v1751
land v1753 v816
sub v820 v1754
mul v1751 v1755
land v1756 v816
land v1739 v825
mul v1758 v1757
land v1759 v825
sub v829 v1760
mul v1757 v1761
land v1762 v825
land v1739 v834
mul v1764 v1763
land v1765 v834
sub v838 v1766
mul v1763 v1767
land v1768 v834
land v1739 v843
mul v1770 v1769
land v1771 v843
sub v847 v1772
mul v1769 v1773
land v1774 v843
land v1739 v852
mul v1776 v1775
land v1777 v852
sub v856 v1778
mul v1775 v1779
land v1780 v852
land v1739 v861
mul v1782 v1781
land v1783 v861
sub v865 v1784
mul v1781 v1785
land v1786 v861
land v1739 v870
mul v1788 v1787
land v1789 v870
sub v874 v1790
mul v1787 v1791
land v1792 v870
land v1739 v879
mul v1794 v1793
land v1795 v879
sub v883 v1796
mul v1793 v1797
land v1798 v879
shl 1 5887
sub v1800 1
land v1739 v1801
mul v1802 v1799
land v1803 v1801
add v1801 3
sub v1805 v1804
mul v1799 v1806
land v1807 v1801
mul v1731 v1808
land v1809 v1725
mul v1810 v1810
land v1811 v1725
shl v1810 v1721
land v1813 v1725
mul v1280 v1814
sub 1 v1280
sub v1724 v1814
mul v1816 v1817
add v1815 v1818
shl v1736 v1721
land v1820 v1725
mul v1816 v1821
sub 1 v1816
sub v1724 v1821
mul v1823 v1824
add v1822 v1825
add v1826 v1724
mul v1733 v1810
land v1828 v1725
sub v1827 v1829
mul v1830 v1808
land v1831 v1725
shl v1812 3957
land v1833 v1725
shl v1819 4711
land v1835 v1725
shl v1832 4711
land v1837 v1725
mul v1812 v970
mul v1819 v1434
add v1839 v1840
mul v1832 v1419
add v1841 v1842
mul v1396 v1834
shr v1434 4710
mul v1845 v1836
add v1844 v1846
mul v1734 v1838
add v1847 v1848
add v1843 v1726
sub v1850 v1849
shr v1851 v1722
land v1852 v1738
mul v1812 v985
mul v1819 v1449
add v1854 v1855
mul v1832 v1434
add v1856 v1857
mul v1411 v1834
shr v1449 4710
mul v1860 v1836
add v1859 v1861
mul v1845 v1838
add v1862 v1863
add v1858 v1726
sub v1865 v1864
shr v1866 v1722
land v1867 v1738
mul v1812 v1000
mul v1819 v1464
add v1869 v1870
mul v1832 v1449
add v1871 v1872
mul v1426 v1834
shr v1464 4710
mul v1875 v1836
add v1874 v1876
mul v1860 v1838
add v1877 v1878
add v1873 v1726
sub v1880 v1879
shr v1881 v1722
land v1882 v1738
mul v1812 v1015
mul v1819 v1479
add v1884 v1885
mul v1832 v1464
add v1886 v1887
mul v1441 v1834
shr v1479 4710
mul v1890 v1836
add v1889 v1891
mul v1875 v1838
add v1892 v1893
add v1888 v1726
sub v1895 v1894
shr v1896 v1722
land v1897 v1738
mul v1812 v1030
mul v1819 v1494
add v1899 v1900
mul v1832 v1479
add v1901 v1902
mul v1456 v1834
shr v1494 4710
mul v1905 v1836
add v1904 v1906
mul v1890 v1838
add v1907 v1908
add v1903 v1726
sub v1910 v1909
shr v1911 v1722
land v1912 v1738
mul v1812 v1045
mul v1819 v1509
add v1914 v1915
mul v1832 v1494
add v1916 v1917
mul v1471 v1834
shr v1509 4710
mul v1920 v1836
add v1919 v1921
mul v1905 v1838
add v1922 v1923
add v1918 v1726
sub v1925 v1924
shr v1926 v1722
land v1927 v1738
mul v1812 v1060
mul v1819 v1524
add v1929 v1930
mul v1832 v1509
add v1931 v1932
mul v1486 v1834
shr v1524 4710
mul v1935 v1836
add v1934 v1936
mul v1920 v1838
add v1937 v1938
add v1933 v1726
sub v1940 v1939
shr v1941 v1722
land v1942 v1738
mul v1812 v1075
mul v1819 v1539
add v1944 v1945
mul v1832 v1524
add v1946 v1947
mul v1501 v1834
shr v1539 4710
mul v1950 v1836
add v1949 v1951
mul v1935 v1838
add v1952 v1953
add v1948 v1726
sub v1955 v1954
shr v1956 v1722
land v1957 v1738
mul v1812 v1090
mul v1819 v1554
add v1959 v1960
mul v1832 v1539
add v1961 v1962
mul v1516 v1834
shr v1554 4710
mul v1965 v1836
add v1964 v1966
mul v1950 v1838
add v1967 v1968
add v1963 v1726
sub v1970 v1969
shr v1971 v1722
land v1972 v1738
mul v1812 v1105
mul v1819 v1569
add v1974 v1975
mul v1832 v1554
add v1976 v1977
mul v1531 v1834
shr v1569 4710
mul v1980 v1836
add v1979 v1981
mul v1965 v1838
add v1982 v1983
add v1978 v1726
sub v1985 v1984
shr v1986 v1722
land v1987 v1738
mul v1812 v1120
mul v1819 v1584
add v1989 v1990
mul v1832 v1569
add v1991 v1992
mul v1546 v1834
shr v1584 4710
mul v1995 v1836
add v1994 v1996
mul v1980 v1838
add v1997 v1998
add v1993 v1726
sub v2000 v1999
shr v2001 v1722
land v2002 v1738
mul v1812 v1135
mul v1819 v1599
add v2004 v2005
mul v1832 v1584
add v2006 v2007
mul v1561 v1834
shr v1599 4710
mul v2010 v1836
add v2009 v2011
mul v1995 v1838
add v2012 v2013
add v2008 v1726
sub v2015 v2014
shr v2016 v1722
land v2017 v1738
mul v1812 v1150
mul v1819 v1614
add v2019 v2020
mul v1832 v1599
add v2021 v2022
mul v1576 v1834
shr v1614 4710
mul v2025 v1836
add v2024 v2026
mul v2010 v1838
add v2027 v2028
add v2023 v1726
sub v2030 v2029
shr v2031 v1722
land v2032 v1738
mul v1812 v1165
mul v1819 v1629
add v2034 v2035
mul v1832 v1614
add v2036 v2037
mul v1591 v1834
shr v1629 4710
mul v2040 v1836
add v2039 v2041
mul v2025 v1838
add v2042 v2043
add v2038 v1726
sub v2045 v2044
shr v2046 v1722
land v2047 v1738
mul v1812 v1180
mul v1819 v1644
add v2049 v2050
mul v1832 v1629
add v2051 v2052
mul v1606 v1834
shr v1644 4710
mul v2055 v1836
add v2054 v2056
mul v2040 v1838
add v2057 v2058
add v2053 v1726
sub v2060 v2059
shr v2061 v1722
land v2062 v1738
mul v1812 v1195
mul v1819 v1659
add v2064 v2065
mul v1832 v1644
add v2066 v2067
mul v1621 v1834
shr v1659 4710
mul v2070 v1836
add v2069 v2071
mul v2055 v1838
add v2072 v2073
add v2068 v1726
sub v2075 v2074
shr v2076 v1722
land v2077 v1738
mul v1812 v1210
mul v1819 v1674
add v2079 v2080
mul v1832 v1659
add v2081 v2082
mul v1636 v1834
shr v1674 4710
mul v2085 v1836
add v2084 v2086
mul v2070 v1838
add v2087 v2088
add v2083 v1726
sub v2090 v2089
shr v2091 v1722
land v2092 v1738
mul v1812 v1225
mul v1819 v1689
add v2094 v2095
mul v1832 v1674
add v2096 v2097
mul v1651 v1834
shr v1689 4710
mul v2100 v1836
add v2099 v2101
mul v2085 v1838
add v2102 v2103
add v2098 v1726
sub v2105 v2104
shr v2106 v1722
land v2107 v1738
mul v1812 v1240
mul v1819 v1699
add v2109 v2110
mul v1832 v1689
add v2111 v2112
mul v1666 v1834
shr v1699 4710
mul v2115 v1836
add v2114 v2116
mul v2100 v1838
add v2117 v2118
add v2113 v1726
sub v2120 v2119
shr v2121 v1722
land v2122 v1738
mul v1812 v1250
mul v1832 v1699
add v2124 v2125
mul v1681 v1834
mul v2115 v1838
add v2127 v2128
add v2126 v1726
sub v2130 v2129
shr v2131 v1722
land v2132 v1738
shr v1714 v1721
land v2134 1
sub 1 v2135
shl 1 v1721
sub v2137 1
land v1714 v2138
add v2136 v2139
sub 1 v1853
add v2140 v2141
add v1709 v2142
mul v1729 v1288
sub v1404 v2144
sub v2144 v1404
add v2145 v2146
land v1404 18446744073709551615
gcd v2148 v771
mul v2149 157587932685088877
land v2150 18446744073709551615
shr v2151 58
shl v2152 3
shr x26 v2153
land v2154 255
shl v2155 1
add 7102 v2156
shl 1 v2157
sub v2158 1
shl v2158 2
sub v2158 v1288
sub v2158 v1737
shr v1853 5758
mul v2163 v2162
add v1853 v2164
mul v1734 v2161
add v1419 v2166
shr v1868 5758
mul v2168 v2162
add v1868 v2169
shl 1 7102
sub v2171 1
shr v2147 v2155
land v2173 v798
mul v2174 v2173
land v2175 v798
sub v802 v2176
mul v2173 v2177
land v2178 v798
land v2173 v807
mul v2180 v2179
land v2181 v807
sub v811 v2182
mul v2179 v2183
land v2184 v807
land v2173 v816
mul v2186 v2185
land v2187 v816
sub v820 v2188
mul v2185 v2189
land v2190 v816
land v2173 v825
mul v2192 v2191
land v2193 v825
sub v829 v2194
mul v2191 v2195
land v2196 v825
land v2173 v834
mul v2198 v2197
land v2199 v834
sub v838 v2200
mul v2197 v2201
land v2202 v834
land v2173 v843
mul v2204 v2203
land v2205 v843
sub v847 v2206
mul v2203 v2207
land v2208 v843
land v2173 v852
mul v2210 v2209
land v2211 v852
sub v856 v2212
mul v2209 v2213
land v2214 v852
land v2173 v861
mul v2216 v2215
land v2217 v861
sub v865 v2218
mul v2215 v2219
land v2220 v861
land v2173 v870
mul v2222 v2221
land v2223 v870
sub v874 v2224
mul v2221 v2225
land v2226 v870
land v2173 v879
mul v2228 v2227
land v2229 v879
sub v883 v2230
mul v2227 v2231
land v2232 v879
shl 1 6144
sub v2234 1
land v2173 v2235
mul v2236 v2233
land v2237 v2235
add v2235 3
sub v2239 v2238
mul v2233 v2240
land v2241 v2235
shl 1 7230
sub v2243 1
land v2173 v2244
mul v2245 v2242
land v2246 v2244
add v2244 3
sub v2248 v2247
mul v2242 v2249
land v2250 v2244
mul v2165 v2251
land v2252 v2159
mul v2253 v2253
land v2254 v2159
shl v2253 v2155
land v2256 v2159
mul v1729 v2257
sub 1 v1729
sub v2158 v2257
mul v2259 v2260
add v2258 v2261
shl v2170 v2155
land v2263 v2159
mul v2259 v2264
sub 1 v2259
sub v2158 v2264
mul v2266 v2267
add v2265 v2268
add v2269 v2158
mul v2167 v2253
land v2271 v2159
sub v2270 v2272
mul v2273 v2251
land v2274 v2159
shl v2255 4711
land v2276 v2159
shl v2262 5759
land v2278 v2159
shl v2275 5759
land v2280 v2159
mul v2255 v1434
mul v2262 v1883
add v2282 v2283
mul v2275 v1868
add v2284 v2285
mul v1845 v2277
shr v1883 5758
mul v2288 v2279
add v2287 v2289
mul v2168 v2281
add v2290 v2291
add v2286 v2160
sub v2293 v2292
shr v2294 v2156
land v2295 v2172
mul v2255 v1449
mul v2262 v1898
add v2297 v2298
mul v2275 v1883
add v2299 v2300
mul v1860 v2277
shr v1898 5758
mul v2303 v2279
add v2302 v2304
mul v2288 v2281
add v2305 v2306
add v2301 v2160
sub v2308 v2307
shr v2309 v2156
land v2310 v2172
mul v2255 v1464
mul v2262 v1913
add v2312 v2313
mul v2275 v1898
add v2314 v2315
mul v1875 v2277
shr v1913 5758
mul v2318 v2279
add v2317 v2319
mul v2303 v2281
add v2320 v2321
add v2316 v2160
sub v2323 v2322
shr v2324 v2156
land v2325 v2172
mul v2255 v1479
mul v2262 v1928
add v2327 v2328
mul v2275 v1913
add v2329 v2330
mul v1890 v2277
shr v1928 5758
mul v2333 v2279
add v2332 v2334
mul v2318 v2281
add v2335 v2336
add v2331 v2160
sub v2338 v2337
shr v2339 v2156
land v2340 v2172
mul v2255 v1494
mul v2262 v1943
add v2342 v2343
mul v2275 v1928
add v2344 v2345
mul v1905 v2277
shr v1943 5758
mul v2348 v2279
add v2347 v2349
mul v2333 v2281
add v2350 v2351
add v2346 v2160
sub v2353 v2352
shr v2354 v2156
land v2355 v2172
mul v2255 v1509
mul v2262 v1958
add v2357 v2358
mul v2275 v1943
add v2359 v2360
mul v1920 v2277
shr v1958 5758
mul v2363 v2279
add v2362 v2364
mul v2348 v2281
add v2365 v2366
add v2361 v2160
sub v2368 v2367
shr v2369 v2156
land v2370 v2172
mul v2255 v1524
mul v2262 v1973
add v2372 v2373
mul v2275 v1958
add v2374 v2375
mul v1935 v2277
shr v1973 5758
mul v2378 v2279
add v2377 v2379
mul v2363 v2281
add v2380 v2381
add v2376 v2160
sub v2383 v2382
shr v2384 v2156
land v2385 v2172
mul v2255 v1539
mul v2262 v1988
add v2387 v2388
mul v2275 v1973
add v2389 v2390
mul v1950 v2277
shr v1988 5758
mul v2393 v2279
add v2392 v2394
mul v2378 v2281
add v2395 v2396
add v2391 v2160
sub v2398 v2397
shr v2399 v2156
land v2400 v2172
mul v2255 v1554
mul v2262 v2003
add v2402 v2403
mul v2275 v1988
add v2404 v2405
mul v1965 v2277
shr v2003 5758
mul v2408 v2279
add v2407 v2409
mul v2393 v2281
add v2410 v2411
add v2406 v2160
sub v2413 v2412
shr v2414 v2156
land v2415 v2172
mul v2255 v1569
mul v2262 v2018
add v2417 v2418
mul v2275 v2003
add v2419 v2420
mul v1980 v2277
shr v2018 5758
mul v2423 v2279
add v2422 v2424
mul v2408 v2281
add v2425 v2426
add v2421 v2160
sub v2428 v2427
shr v2429 v2156
land v2430 v2172
mul v2255 v1584
mul v2262 v2033
add v2432 v2433
mul v2275 v2018
add v2434 v2435
mul v1995 v2277
shr v2033 5758
mul v2438 v2279
add v2437 v2439
mul v2423 v2281
add v2440 v2441
add v2436 v2160
sub v2443 v2442
shr v2444 v2156
land v2445 v2172
mul v2255 v1599
mul v2262 v2048
add v2447 v2448
mul v2275 v2033
add v2449 v2450
mul v2010 v2277
shr v2048 5758
mul v2453 v2279
add v2452 v2454
mul v2438 v2281
add v2455 v2456
add v2451 v2160
sub v2458 v2457
shr v2459 v2156
land v2460 v2172
mul v2255 v1614
mul v2262 v2063
add v2462 v2463
mul v2275 v2048
add v2464 v2465
mul v2025 v2277
shr v2063 5758
mul v2468 v2279
add v2467 v2469
mul v2453 v2281
add v2470 v2471
add v2466 v2160
sub v2473 v2472
shr v2474 v2156
land v2475 v2172
mul v2255 v1629
mul v2262 v2078
add v2477 v2478
mul v2275 v2063
add v2479 v2480
mul v2040 v2277
shr v2078 5758
mul v2483 v2279
add v2482 v2484
mul v2468 v2281
add v2485 v2486
add v2481 v2160
sub v2488 v2487
shr v2489 v2156
land v2490 v2172
mul v2255 v1644
mul v2262 v2093
add v2492 v2493
mul v2275 v2078
add v2494 v2495
mul v2055 v2277
shr v2093 5758
mul v2498 v2279
add v2497 v2499
mul v2483 v2281
add v2500 v2501
add v2496 v2160
sub v2503 v2502
shr v2504 v2156
land v2505 v2172
mul v2255 v1659
mul v2262 v2108
add v2507 v2508
mul v2275 v2093
add v2509 v2510
mul v2070 v2277
shr v2108 5758
mul v2513 v2279
add v2512 v2514
mul v2498 v2281
add v2515 v2516
add v2511 v2160
sub v2518 v2517
shr v2519 v2156
land v2520 v2172
mul v2255 v1674
mul v2262 v2123
add v2522 v2523
mul v2275 v2108
add v2524 v2525
mul v2085 v2277
shr v2123 5758
mul v2528 v2279
add v2527 v2529
mul v2513 v2281
add v2530 v2531
add v2526 v2160
sub v2533 v2532
shr v2534 v2156
land v2535 v2172
mul v2255 v1689
mul v2262 v2133
add v2537 v2538
mul v2275 v2123
add v2539 v2540
mul v2100 v2277
shr v2133 5758
mul v2543 v2279
add v2542 v2544
mul v2528 v2281
add v2545 v2546
add v2541 v2160
sub v2548 v2547
shr v2549 v2156
land v2550 v2172
mul v2255 v1699
mul v2275 v2133
add v2552 v2553
mul v2115 v2277
mul v2543 v2281
add v2555 v2556
add v2554 v2160
sub v2558 v2557
shr v2559 v2156
land v2560 v2172
shr v2148 v2155
land v2562 1
sub 1 v2563
shl 1 v2155
sub v2565 1
land v2148 v2566
add v2564 v2567
sub 1 v2296
add v2568 v2569
add v2143 v2570
mul v2163 v1737
sub v1853 v2572
sub v2572 v1853
add v2573 v2574
land v1853 18446744073709551615
gcd v2576 v771
mul v2577 157587932685088877
land v2578 18446744073709551615
shr v2579 58
shl v2580 3
shr x26 v2581
land v2582 255
shl v2583 1
add 8739 v2584
shl 1 v2585
sub v2586 1
shl v2586 2
sub v2586 v1737
sub v2586 v2171
shr v2296 7101
mul v2591 v2590
add v2296 v2592
mul v2168 v2589
add v1868 v2594
shr v2311 7101
mul v2596 v2590
add v2311 v2597
shl 1 8739
sub v2599 1
shr v2575 v2583
land v2601 v798
mul v2602 v2601
land v2603 v798
sub v802 v2604
mul v2601 v2605
land v2606 v798
land v2601 v807
mul v2608 v2607
land v2609 v807
sub v811 v2610
mul v2607 v2611
land v2612 v807
land v2601 v816
mul v2614 v2613
land v2615 v816
sub v820 v2616
mul v2613 v2617
land v2618 v816
land v2601 v825
mul v2620 v2619
land v2621 v825
sub v829 v2622
mul v2619 v2623
land v2624 v825
land v2601 v834
mul v2626 v2625
land v2627 v834
sub v838 v2628
mul v2625 v2629
land v2630 v834
land v2601 v843
mul v2632 v2631
land v2633 v843
sub v847 v2634
mul v2631 v2635
land v2636 v843
land v2601 v852
mul v2638 v2637
land v2639 v852
sub v856 v2640
mul v2637 v2641
land v2642 v852
land v2601 v861
mul v2644 v2643
land v2645 v861
sub v865 v2646
mul v2643 v2647
land v2648 v861
land v2601 v870
mul v2650 v2649
land v2651 v870
sub v874 v2652
mul v2649 v2653
land v2654 v870
land v2601 v879
mul v2656 v2655
land v2657 v879
sub v883 v2658
mul v2655 v2659
land v2660 v879
land v2601 v2235
mul v2662 v2661
land v2663 v2235
sub v2239 v2664
mul v2661 v2665
land v2666 v2235
shl 1 8867
sub v2668 1
land v2601 v2669
mul v2670 v2667
land v2671 v2669
add v2669 3
sub v2673 v2672
mul v2667 v2674
land v2675 v2669
mul v2593 v2676
land v2677 v2587
mul v2678 v2678
land v2679 v2587
shl v2678 v2583
land v2681 v2587
mul v2163 v2682
sub 1 v2163
sub v2586 v2682
mul v2684 v2685
add v2683 v2686
shl v2598 v2583
land v2688 v2587
mul v2684 v2689
sub 1 v2684
sub v2586 v2689
mul v2691 v2692
add v2690 v2693
add v2694 v2586
mul v2595 v2678
land v2696 v2587
sub v2695 v2697
mul v2698 v2676
land v2699 v2587
shl v2680 5759
land v2701 v2587
shl v2687 7102
land v2703 v2587
shl v2700 7102
land v2705 v2587
mul v2680 v1883
mul v2687 v2326
add v2707 v2708
mul v2700 v2311
add v2709 v2710
mul v2288 v2702
shr v2326 7101
mul v2713 v2704
add v2712 v2714
mul v2596 v2706
add v2715 v2716
add v2711 v2588
sub v2718 v2717
shr v2719 v2584
land v2720 v2600
mul v2680 v1898
mul v2687 v2341
add v2722 v2723
mul v2700 v2326
add v2724 v2725
mul v2303 v2702
shr v2341 7101
mul v2728 v2704
add v2727 v2729
mul v2713 v2706
add v2730 v2731
add v2726 v2588
sub v2733 v2732
shr v2734 v2584
land v2735 v2600
mul v2680 v1913
mul v2687 v2356
add v2737 v2738
mul v2700 v2341
add v2739 v2740
mul v2318 v2702
shr v2356 7101
mul v2743 v2704
add v2742 v2744
mul v2728 v2706
add v2745 v2746
add v2741 v2588
sub v2748 v2747
shr v2749 v2584
land v2750 v2600
mul v2680 v1928
mul v2687 v2371
add v2752 v2753
mul v2700 v2356
add v2754 v2755
mul v2333 v2702
shr v2371 7101
mul v2758 v2704
add v2757 v2759
mul v2743 v2706
add v2760 v2761
add v2756 v2588
sub v2763 v2762
shr v2764 v2584
land v2765 v2600
mul v2680 v1943
mul v2687 v2386
add v2767 v2768
mul v2700 v2371
add v2769 v2770
mul v2348 v2702
shr v2386 7101
mul v2773 v2704
add v2772 v2774
mul v2758 v2706
add v2775 v2776
add v2771 v2588
sub v2778 v2777
shr v2779 v2584
land v2780 v2600
mul v2680 v1958
mul v2687 v2401
add v2782 v2783
mul v2700 v2386
add v2784 v2785
mul v2363 v2702
shr v2401 7101
mul v2788 v2704
add v2787 v2789
mul v2773 v2706
add v2790 v2791
add v2786 v2588
sub v2793 v2792
shr v2794 v2584
land v2795 v2600
mul v2680 v1973
mul v2687 v2416
add v2797 v2798
mul v2700 v2401
add v2799 v2800
mul v2378 v2702
shr v2416 7101
mul v2803 v2704
add v2802 v2804
mul v2788 v2706
add v2805 v2806
add v2801 v2588
sub v2808 v2807
shr v2809 v2584
land v2810 v2600
mul v2680 v1988
mul v2687 v2431
add v2812 v2813
mul v2700 v2416
add v2814 v2815
mul v2393 v2702
shr v2431 7101
mul v2818 v2704
add v2817 v2819
mul v2803 v2706
add v2820 v2821
add v2816 v2588
sub v2823 v2822
shr v2824 v2584
land v2825 v2600
mul v2680 v2003
mul v2687 v2446
add v2827 v2828
mul v2700 v2431
add v2829 v2830
mul v2408 v2702
shr v2446 7101
mul v2833 v2704
add v2832 v2834
mul v2818 v2706
add v2835 v2836
add v2831 v2588
sub v2838 v2837
shr v2839 v2584
land v2840 v2600
mul v2680 v2018
mul v2687 v2461
add v2842 v2843
mul v2700 v2446
add v2844 v2845
mul v2423 v2702
shr v2461 7101
mul v2848 v2704
add v2847 v2849
mul v2833 v2706
add v2850 v2851
add v2846 v2588
sub v2853 v2852
shr v2854 v2584
land v2855 v2600
mul v2680 v2033
mul v2687 v2476
add v2857 v2858
mul v2700 v2461
add v2859 v2860
mul v2438 v2702
shr v2476 7101
mul v2863 v2704
add v2862 v2864
mul v2848 v2706
add v2865 v2866
add v2861 v2588
sub v2868 v2867
shr v2869 v2584
land v2870 v2600
mul v2680 v2048
mul v2687 v2491
add v2872 v2873
mul v2700 v2476
add v2874 v2875
mul v2453 v2702
shr v2491 7101
mul v2878 v2704
add v2877 v2879
mul v2863 v2706
add v2880 v2881
add v2876 v2588
sub v2883 v2882
shr v2884 v2584
land v2885 v2600
mul v2680 v2063
mul v2687 v2506
add v2887 v2888
mul v2700 v2491
add v2889 v2890
mul v2468 v2702
shr v2506 7101
mul v2893 v2704
add v2892 v2894
mul v2878 v2706
add v2895 v2896
add v2891 v2588
sub v2898 v2897
shr v2899 v2584
land v2900 v2600
mul v2680 v2078
mul v2687 v2521
add v2902 v2903
mul v2700 v2506
add v2904 v2905
mul v2483 v2702
shr v2521 7101
mul v2908 v2704
add v2907 v2909
mul v2893 v2706
add v2910 v2911
add v2906 v2588
sub v2913 v2912
shr v2914 v2584
land v2915 v2600
mul v2680 v2093
mul v2687 v2536
add v2917 v2918
mul v2700 v2521
add v2919 v2920
mul v2498 v2702
shr v2536 7101
mul v2923 v2704
add v2922 v2924
mul v2908 v2706
add v2925 v2926
add v2921 v2588
sub v2928 v2927
shr v2929 v2584
land v2930 v2600
mul v2680 v2108
mul v2687 v2551
add v2932 v2933
mul v2700 v2536
add v2934 v2935
mul v2513 v2702
shr v2551 7101
mul v2938 v2704
add v2937 v2939
mul v2923 v2706
add v2940 v2941
add v2936 v2588
sub v2943 v2942
shr v2944 v2584
land v2945 v2600
mul v2680 v2123
mul v2687 v2561
add v2947 v2948
mul v2700 v2551
add v2949 v2950
mul v2528 v2702
shr v2561 7101
mul v2953 v2704
add v2952 v2954
mul v2938 v2706
add v2955 v2956
add v2951 v2588
sub v2958 v2957
shr v2959 v2584
land v2960 v2600
mul v2680 v2133
mul v2700 v2561
add v2962 v2963
mul v2543 v2702
mul v2953 v2706
add v2965 v2966
add v2964 v2588
sub v2968 v2967
shr v2969 v2584
land v2970 v2600
shr v2576 v2583
land v2972 1
sub 1 v2973
shl 1 v2583
sub v2975 1
land v2576 v2976
add v2974 v2977
sub 1 v2721
add v2978 v2979
add v2571 v2980
mul v2591 v2171
sub v2296 v2982
sub v2982 v2296
add v2983 v2984
land v2296 18446744073709551615
gcd v2986 v771
mul v2987 157587932685088877
land v2988 18446744073709551615
shr v2989 58
shl v2990 3
shr x26 v2991
land v2992 255
shl v2993 1
add 10671 v2994
shl 1 v2995
sub v2996 1
shl v2996 2
sub v2996 v2171
sub v2996 v2599
shr v2721 8738
mul v3001 v3000
add v2721 v3002
mul v2596 v2999
add v2311 v3004
shr v2736 8738
mul v3006 v3000
add v2736 v3007
shl 1 10671
sub v3009 1
shr v2985 v2993
land v3011 v798
mul v3012 v3011
land v3013 v798
sub v802 v3014
mul v3011 v3015
land v3016 v798
land v3011 v807
mul v3018 v3017
land v3019 v807
sub v811 v3020
mul v3017 v3021
land v3022 v807
land v3011 v816
mul v3024 v3023
land v3025 v816
sub v820 v3026
mul v3023 v3027
land v3028 v816
land v3011 v825
mul v3030 v3029
land v3031 v825
sub v829 v3032
mul v3029 v3033
land v3034 v825
land v3011 v834
mul v3036 v3035
land v3037 v834
sub v838 v3038
mul v3035 v3039
land v3040 v834
land v3011 v843
mul v3042 v3041
land v3043 v843
sub v847 v3044
mul v3041 v3045
land v3046 v843
land v3011 v852
mul v3048 v3047
land v3049 v852
sub v856 v3050
mul v3047 v3051
land v3052 v852
land v3011 v861
mul v3054 v3053
land v3055 v861
sub v865 v3056
mul v3053 v3057
land v3058 v861
land v3011 v870
mul v3060 v3059
land v3061 v870
sub v874 v3062
mul v3059 v3063
land v3064 v870
land v3011 v879
mul v3066 v3065
land v3067 v879
sub v883 v3068
mul v3065 v3069
land v3070 v879
land v3011 v2235
mul v3072 v3071
land v3073 v2235
sub v2239 v3074
mul v3071 v3075
land v3076 v2235
shl 1 10799
sub v3078 1
land v3011 v3079
mul v3080 v3077
land v3081 v3079
add v3079 3
sub v3083 v3082
mul v3077 v3084
land v3085 v3079
mul v3003 v3086
land v3087 v2997
mul v3088 v3088
land v3089 v2997
shl v3088 v2993
land v3091 v2997
mul v2591 v3092
sub 1 v2591
sub v2996 v3092
mul v3094 v3095
add v3093 v3096
shl v3008 v2993
land v3098 v2997
mul v3094 v3099
sub 1 v3094
sub v2996 v3099
mul v3101 v3102
add v3100 v3103
add v3104 v2996
mul v3005 v3088
land v3106 v2997
sub v3105 v3107
mul v3108 v3086
land v3109 v2997
shl v3090 7102
land v3111 v2997
shl v3097 8739
land v3113 v2997
shl v3110 8739
land v3115 v2997
mul v3090 v2326
mul v3097 v2751
add v3117 v3118
mul v3110 v2736
add v3119 v3120
mul v2713 v3112
shr v2751 8738
mul v3123 v3114
add v3122 v3124
mul v3006 v3116
add v3125 v3126
add v3121 v2998
sub v3128 v3127
shr v3129 v2994
land v3130 v3010
mul v3090 v2341
mul v3097 v2766
add v3132 v3133
mul v3110 v2751
add v3134 v3135
mul v2728 v3112
shr v2766 8738
mul v3138 v3114
add v3137 v3139
mul v3123 v3116
add v3140 v3141
add v3136 v2998
sub v3143 v3142
shr v3144 v2994
land v3145 v3010
mul v3090 v2356
mul v3097 v2781
add v3147 v3148
mul v3110 v2766
add v3149 v3150
mul v2743 v3112
shr v2781 8738
mul v3153 v3114
add v3152 v3154
mul v3138 v3116
add v3155 v3156
add v3151 v2998
sub v3158 v3157
shr v3159 v2994
land v3160 v3010
mul v3090 v2371
mul v3097 v2796
add v3162 v3163
mul v3110 v2781
add v3164 v3165
mul v2758 v3112
shr v2796 8738
mul v3168 v3114
add v3167 v3169
mul v3153 v3116
add v3170 v3171
add v3166 v2998
sub v3173 v3172
shr v3174 v2994
land v3175 v3010
mul v3090 v2386
mul v3097 v2811
add v3177 v3178
mul v3110 v2796
add v3179 v3180
mul v2773 v3112
shr v2811 8738
mul v3183 v3114
add v3182 v3184
mul v3168 v3116
add v3185 v3186
add v3181 v2998
sub v3188 v3187
shr v3189 v2994
land v3190 v3010
mul v3090 v2401
mul v3097 v2826
add v3192 v3193
mul v3110 v2811
add v3194 v3195
mul v2788 v3112
shr v2826 8738
mul v3198 v3114
add v3197 v3199
mul v3183 v3116
add v3200 v3201
add v3196 v2998
sub v3203 v3202
shr v3204 v2994
land v3205 v3010
mul v3090 v2416
mul v3097 v2841
add v3207 v3208
mul v3110 v2826
add v3209 v3210
mul v2803 v3112
shr v2841 8738
mul v3213 v3114
add v3212 v3214
mul v3198 v3116
add v3215 v3216
add v3211 v2998
sub v3218 v3217
shr v3219 v2994
land v3220 v3010
mul v3090 v2431
mul v3097 v2856
add v3222 v3223
mul v3110 v2841
add v3224 v3225
mul v2818 v3112
shr v2856 8738
mul v3228 v3114
add v3227 v3229
mul v3213 v3116
add v3230 v3231
add v3226 v2998
sub v3233 v3232
shr v3234 v2994
land v3235 v3010
mul v3090 v2446
mul v3097 v2871
add v3237 v3238
mul v3110 v2856
add v3239 v3240
mul v2833 v3112
shr v2871 8738
mul v3243 v3114
add v3242 v3244
mul v3228 v3116
add v3245 v3246
add v3241 v2998
sub v3248 v3247
shr v3249 v2994
land v3250 v3010
mul v3090 v2461
mul v3097 v2886
add v3252 v3253
mul v3110 v2871
add v3254 v3255
mul v2848 v3112
shr v2886 8738
mul v3258 v3114
add v3257 v3259
mul v3243 v3116
add v3260 v3261
add v3256 v2998
sub v3263 v3262
shr v3264 v2994
land v3265 v3010
mul v3090 v2476
mul v3097 v2901
add v3267 v3268
mul v3110 v2886
add v3269 v3270
mul v2863 v3112
shr v2901 8738
mul v3273 v3114
add v3272 v3274
mul v3258 v3116
add v3275 v3276
add v3271 v2998
sub v3278 v3277
shr v3279 v2994
land v3280 v3010
mul v3090 v2491
mul v3097 v2916
add v3282 v3283
mul v3110 v2901
add v3284 v3285
mul v2878 v3112
shr v2916 8738
mul v3288 v3114
add v3287 v3289
mul v3273 v3116
add v3290 v3291
add v3286 v2998
sub v3293 v3292
shr v3294 v2994
land v3295 v3010
mul v3090 v2506
mul v3097 v2931
add v3297 v3298
mul v3110 v2916
add v3299 v3300
mul v2893 v3112
shr v2931 8738
mul v3303 v3114
add v3302 v3304
mul v3288 v3116
add v3305 v3306
add v3301 v2998
sub v3308 v3307
shr v3309 v2994
land v3310 v3010
mul v3090 v2521
mul v3097 v2946
add v3312 v3313
mul v3110 v2931
add v3314 v3315
mul v2908 v3112
shr v2946 8738
mul v3318 v3114
add v3317 v3319
mul v3303 v3116
add v3320 v3321
add v3316 v2998
sub v3323 v3322
shr v3324 v2994
land v3325 v3010
mul v3090 v2536
mul v3097 v2961
add v3327 v3328
mul v3110 v2946
add v3329 v3330
mul v2923 v3112
shr v2961 8738
mul v3333 v3114
add v3332 v3334
mul v3318 v3116
add v3335 v3336
add v3331 v2998
sub v3338 v3337
shr v3339 v2994
land v3340 v3010
mul v3090 v2551
mul v3097 v2971
add v3342 v3343
mul v3110 v2961
add v3344 v3345
mul v2938 v3112
shr v2971 8738
mul v3348 v3114
add v3347 v3349
mul v3333 v3116
add v3350 v3351
add v3346 v2998
sub v3353 v3352
shr v3354 v2994
land v3355 v3010
mul v3090 v2561
mul v3110 v2971
add v3357 v3358
mul v2953 v3112
mul v3348 v3116
add v3360 v3361
add v3359 v2998
sub v3363 v3362
shr v3364 v2994
land v3365 v3010
shr v2986 v2993
land v3367 1
sub 1 v3368
shl 1 v2993
sub v3370 1
land v2986 v3371
add v3369 v3372
sub 1 v3131
add v3373 v3374
add v2981 v3375
mul v3001 v2599
sub v2721 v3377
sub v3377 v2721
add v3378 v3379
land v2721 18446744073709551615
gcd v3381 v771
mul v3382 157587932685088877
land v3383 18446744073709551615
shr v3384 58
shl v3385 3
shr x26 v3386
land v3387 255
shl v3388 1
add 12894 v3389
shl 1 v3390
sub v3391 1
shl v3391 2
sub v3391 v2599
sub v3391 v3009
shr v3131 10670
mul v3396 v3395
add v3131 v3397
mul v3006 v3394
add v2736 v3399
shr v3146 10670
mul v3401 v3395
add v3146 v3402
shl 1 12894
sub v3404 1
shr v3380 v3388
land v3406 v798
mul v3407 v3406
land v3408 v798
sub v802 v3409
mul v3406 v3410
land v3411 v798
land v3406 v807
mul v3413 v3412
land v3414 v807
sub v811 v3415
mul v3412 v3416
land v3417 v807
land v3406 v816
mul v3419 v3418
land v3420 v816
sub v820 v3421
mul v3418 v3422
land v3423 v816
land v3406 v825
mul v3425 v3424
land v3426 v825
sub v829 v3427
mul v3424 v3428
land v3429 v825
land v3406 v834
mul v3431 v3430
land v3432 v834
sub v838 v3433
mul v3430 v3434
land v3435 v834
land v3406 v843
mul v3437 v3436
land v3438 v843
sub v847 v3439
mul v3436 v3440
land v3441 v843
land v3406 v852
mul v3443 v3442
land v3444 v852
sub v856 v3445
mul v3442 v3446
land v3447 v852
land v3406 v861
mul v3449 v3448
land v3450 v861
sub v865 v3451
mul v3448 v3452
land v3453 v861
land v3406 v870
mul v3455 v3454
land v3456 v870
sub v874 v3457
mul v3454 v3458
land v3459 v870
land v3406 v879
mul v3461 v3460
land v3462 v879
sub v883 v3463
mul v3460 v3464
land v3465 v879
land v3406 v2235
mul v3467 v3466
land v3468 v2235
sub v2239 v3469
mul v3466 v3470
land v3471 v2235
shl 1 12288
sub v3473 1
land v3406 v3474
mul v3475 v3472
land v3476 v3474
add v3474 3
sub v3478 v3477
mul v3472 v3479
land v3480 v3474
shl 1 13022
sub v3482 1
land v3406 v3483
mul v3484 v3481
land v3485 v3483
add v3483 3
sub v3487 v3486
mul v3481 v3488
land v3489 v3483
mul v3398 v3490
land v3491 v3392
mul v3492 v3492
land v3493 v3392
shl v3492 v3388
land v3495 v3392
mul v3001 v3496
sub 1 v3001
sub v3391 v3496
mul v3498 v3499
add v3497 v3500
shl v3403 v3388
land v3502 v3392
mul v3498 v3503
sub 1 v3498
sub v3391 v3503
mul v3505 v3506
add v3504 v3507
add v3508 v3391
mul v3400 v3492
land v3510 v3392
sub v3509 v3511
mul v3512 v3490
land v3513 v3392
shl v3494 8739
land v3515 v3392
shl v3501 10671
land v3517 v3392
shl v3514 10671
land v3519 v3392
mul v3494 v2751
mul v3501 v3161
add v3521 v3522
mul v3514 v3146
add v3523 v3524
mul v3123 v3516
shr v3161 10670
mul v3527 v3518
add v3526 v3528
mul v3401 v3520
add v3529 v3530
add v3525 v3393
sub v3532 v3531
shr v3533 v3389
land v3534 v3405
mul v3494 v2766
mul v3501 v3176
add v3536 v3537
mul v3514 v3161
add v3538 v3539
mul v3138 v3516
shr v3176 10670
mul v3542 v3518
add v3541 v3543
mul v3527 v3520
add v3544 v3545
add v3540 v3393
sub v3547 v3546
shr v3548 v3389
land v3549 v3405
mul v3494 v2781
mul v3501 v3191
add v3551 v3552
mul v3514 v3176
add v3553 v3554
mul v3153 v3516
shr v3191 10670
mul v3557 v3518
add v3556 v3558
mul v3542 v3520
add v3559 v3560
add v3555 v3393
sub v3562 v3561
shr v3563 v3389
land v3564 v3405
mul v3494 v2796
mul v3501 v3206
add v3566 v3567
mul v3514 v3191
add v3568 v3569
mul v3168 v3516
shr v3206 10670
mul v3572 v3518
add v3571 v3573
mul v3557 v3520
add v3574 v3575
add v3570 v3393
sub v3577 v3576
shr v3578 v3389
land v3579 v3405
mul v3494 v2811
mul v3501 v3221
add v3581 v3582
mul v3514 v3206
add v3583 v3584
mul v3183 v3516
shr v3221 10670
mul v3587 v3518
add v3586 v3588
mul v3572 v3520
add v3589 v3590
add v3585 v3393
sub v3592 v3591
shr v3593 v3389
land v3594 v3405
mul v3494 v2826
mul v3501 v3236
add v3596 v3597
mul v3514 v3221
add v3598 v3599
mul v3198 v3516
shr v3236 10670
mul v3602 v3518
add v3601 v3603
mul v3587 v3520
add v3604 v3605
add v3600 v3393
sub v3607 v3606
shr v3608 v3389
land v3609 v3405
mul v3494 v2841
mul v3501 v3251
add v3611 v3612
mul v3514 v3236
add v3613 v3614
mul v3213 v3516
shr v3251 10670
mul v3617 v3518
add v3616 v3618
mul v3602 v3520
add v3619 v3620
add v3615 v3393
sub v3622 v3621
shr v3623 v3389
land v3624 v3405
mul v3494 v2856
mul v3501 v3266
add v3626 v3627
mul v3514 v3251
add v3628 v3629
mul v3228 v3516
shr v3266 10670
mul v3632 v3518
add v3631 v3633
mul v3617 v3520
add v3634 v3635
add v3630 v3393
sub v3637 v3636
shr v3638 v3389
land v3639 v3405
mul v3494 v2871
mul v3501 v3281
add v3641 v3642
mul v3514 v3266
add v3643 v3644
mul v3243 v3516
shr v3281 10670
mul v3647 v3518
add v3646 v3648
mul v3632 v3520
add v3649 v3650
add v3645 v3393
sub v3652 v3651
shr v3653 v3389
land v3654 v3405
mul v3494 v2886
mul v3501 v3296
add v3656 v3657
mul v3514 v3281
add v3658 v3659
mul v3258 v3516
shr v3296 10670
mul v3662 v3518
add v3661 v3663
mul v3647 v3520
add v3664 v3665
add v3660 v3393
sub v3667 v3666
shr v3668 v3389
land v3669 v3405
mul v3494 v2901
mul v3501 v3311
add v3671 v3672
mul v3514 v3296
add v3673 v3674
mul v3273 v3516
shr v3311 10670
mul v3677 v3518
add v3676 v3678
mul v3662 v3520
add v3679 v3680
add v3675 v3393
sub v3682 v3681
shr v3683 v3389
land v3684 v3405
mul v3494 v2916
mul v3501 v3326
add v3686 v3687
mul v3514 v3311
add v3688 v3689
mul v3288 v3516
shr v3326 10670
mul v3692 v3518
add v3691 v3693
mul v3677 v3520
add v3694 v3695
add v3690 v3393
sub v3697 v3696
shr v3698 v3389
land v3699 v3405
mul v3494 v2931
mul v3501 v3341
add v3701 v3702
mul v3514 v3326
add v3703 v3704
mul v3303 v3516
shr v3341 10670
mul v3707 v3518
add v3706 v3708
mul v3692 v3520
add v3709 v3710
add v3705 v3393
sub v3712 v3711
shr v3713 v3389
land v3714 v3405
mul v3494 v2946
mul v3501 v3356
add v3716 v3717
mul v3514 v3341
add v3718 v3719
mul v3318 v3516
shr v3356 10670
mul v3722 v3518
add v3721 v3723
mul v3707 v3520
add v3724 v3725
add v3720 v3393
sub v3727 v3726
shr v3728 v3389
land v3729 v3405
mul v3494 v2961
mul v3501 v3366
add v3731 v3732
mul v3514 v3356
add v3733 v3734
mul v3333 v3516
shr v3366 10670
mul v3737 v3518
add v3736 v3738
mul v3722 v3520
add v3739 v3740
add v3735 v3393
sub v3742 v3741
shr v3743 v3389
land v3744 v3405
mul v3494 v2971
mul v3514 v3366
add v3746 v3747
mul v3348 v3516
mul v3737 v3520
add v3749 v3750
add v3748 v3393
sub v3752 v3751
shr v3753 v3389
land v3754 v3405
shr v3381 v3388
land v3756 1
sub 1 v3757
shl 1 v3388
sub v3759 1
land v3381 v3760
add v3758 v3761
sub 1 v3535
add v3762 v3763
add v3376 v3764
mul v3396 v3009
sub v3131 v3766
sub v3766 v3131
add v3767 v3768
land v3131 18446744073709551615
gcd v3770 v771
mul v3771 157587932685088877
land v3772 18446744073709551615
shr v3773 58
shl v3774 3
shr x26 v3775
land v3776 255
shl v3777 1
add 15409 v3778
shl 1 v3779
sub v3780 1
shl v3780 2
sub v3780 v3009
sub v3780 v3404
shr v3535 12893
mul v3785 v3784
add v3535 v3786
mul v3401 v3783
add v3146 v3788
shr v3550 12893
mul v3790 v3784
add v3550 v3791
shl 1 15409
sub v3793 1
shr v3769 v3777
land v3795 v798
mul v3796 v3795
land v3797 v798
sub v802 v3798
mul v3795 v3799
land v3800 v798
land v3795 v807
mul v3802 v3801
land v3803 v807
sub v811 v3804
mul v3801 v3805
land v3806 v807
land v3795 v816
mul v3808 v3807
land v3809 v816
sub v820 v3810
mul v3807 v3811
land v3812 v816
land v3795 v825
mul v3814 v3813
land v3815 v825
sub v829 v3816
mul v3813 v3817
land v3818 v825
land v3795 v834
mul v3820 v3819
land v3821 v834
sub v838 v3822
mul v3819 v3823
land v3824 v834
land v3795 v843
mul v3826 v3825
land v3827 v843
sub v847 v3828
mul v3825 v3829
land v3830 v843
land v3795 v852
mul v3832 v3831
land v3833 v852
sub v856 v3834
mul v3831 v3835
land v3836 v852
land v3795 v861
mul v3838 v3837
land v3839 v861
sub v865 v3840
mul v3837 v3841
land v3842 v861
land v3795 v870
mul v3844 v3843
land v3845 v870
sub v874 v3846
mul v3843 v3847
land v3848 v870
land v3795 v879
mul v3850 v3849
land v3851 v879
sub v883 v3852
mul v3849 v3853
land v3854 v879
land v3795 v2235
mul v3856 v3855
land v3857 v2235
sub v2239 v3858
mul v3855 v3859
land v3860 v2235
land v3795 v3474
mul v3862 v3861
land v3863 v3474
sub v3478 v3864
mul v3861 v3865
land v3866 v3474
shl 1 15537
sub v3868 1
land v3795 v3869
mul v3870 v3867
land v3871 v3869
add v3869 3
sub v3873 v3872
mul v3867 v3874
land v3875 v3869
mul v3787 v3876
land v3877 v3781
mul v3878 v3878
land v3879 v3781
shl v3878 v3777
land v3881 v3781
mul v3396 v3882
sub 1 v3396
sub v3780 v3882
mul v3884 v3885
add v3883 v3886
shl v3792 v3777
land v3888 v3781
mul v3884 v3889
sub 1 v3884
sub v3780 v3889
mul v3891 v3892
add v3890 v3893
add v3894 v3780
mul v3789 v3878
land v3896 v3781
sub v3895 v3897
mul v3898 v3876
land v3899 v3781
shl v3880 10671
land v3901 v3781
shl v3887 12894
land v3903 v3781
shl v3900 12894
land v3905 v3781
mul v3880 v3161
mul v3887 v3565
add v3907 v3908
mul v3900 v3550
add v3909 v3910
mul v3527 v3902
shr v3565 12893
mul v3913 v3904
add v3912 v3914
mul v3790 v3906
add v3915 v3916
add v3911 v3782
sub v3918 v3917
shr v3919 v3778
land v3920 v3794
mul v3880 v3176
mul v3887 v3580
add v3922 v3923
mul v3900 v3565
add v3924 v3925
mul v3542 v3902
shr v3580 12893
mul v3928 v3904
add v3927 v3929
mul v3913 v3906
add v3930 v3931
add v3926 v3782
sub v3933 v3932
shr v3934 v3778
land v3935 v3794
mul v3880 v3191
mul v3887 v3595
add v3937 v3938
mul v3900 v3580
add v3939 v3940
mul v3557 v3902
shr v3595 12893
mul v3943 v3904
add v3942 v3944
mul v3928 v3906
add v3945 v3946
add v3941 v3782
sub v3948 v3947
shr v3949 v3778
land v3950 v3794
mul v3880 v3206
mul v3887 v3610
add v3952 v3953
mul v3900 v3595
add v3954 v3955
mul v3572 v3902
shr v3610 12893
mul v3958 v3904
add v3957 v3959
mul v3943 v3906
add v3960 v3961
add v3956 v3782
sub v3963 v3962
shr v3964 v3778
land v3965 v3794
mul v3880 v3221
mul v3887 v3625
add v3967 v3968
mul v3900 v3610
add v3969 v3970
mul v3587 v3902
shr v3625 12893
mul v3973 v3904
add v3972 v3974
mul v3958 v3906
add v3975 v3976
add v3971 v3782
sub v3978 v3977
shr v3979 v3778
land v3980 v3794
mul v3880 v3236
mul v3887 v3640
add v3982 v3983
mul v3900 v3625
add v3984 v3985
mul v3602 v3902
shr v3640 12893
mul v3988 v3904
add v3987 v3989
mul v3973 v3906
add v3990 v3991
add v3986 v3782
sub v3993 v3992
shr v3994 v3778
land v3995 v3794
mul v3880 v3251
mul v3887 v3655
add v3997 v3998
mul v3900 v3640
add v3999 v4000
mul v3617 v3902
shr v3655 12893
mul v4003 v3904
add v4002 v4004
mul v3988 v3906
add v4005 v4006
add v4001 v3782
sub v4008 v4007
shr v4009 v3778
land v4010 v3794
mul v3880 v3266
mul v3887 v3670
add v4012 v4013
mul v3900 v3655
add v4014 v4015
mul v3632 v3902
shr v3670 12893
mul v4018 v3904
add v4017 v4019
mul v4003 v3906
add v4020 v4021
add v4016 v3782
sub v4023 v4022
shr v4024 v3778
land v4025 v3794
mul v3880 v3281
mul v3887 v3685
add v4027 v4028
mul v3900 v3670
add v4029 v4030
mul v3647 v3902
shr v3685 12893
mul v4033 v3904
add v4032 v4034
mul v4018 v3906
add v4035 v4036
add v4031 v3782
sub v4038 v4037
shr v4039 v3778
land v4040 v3794
mul v3880 v3296
mul v3887 v3700
add v4042 v4043
mul v3900 v3685
add v4044 v4045
mul v3662 v3902
shr v3700 12893
mul v4048 v3904
add v4047 v4049
mul v4033 v3906
add v4050 v4051
add v4046 v3782
sub v4053 v4052
shr v4054 v3778
land v4055 v3794
mul v3880 v3311
mul v3887 v3715
add v4057 v4058
mul v3900 v3700
add v4059 v4060
mul v3677 v3902
shr v3715 12893
mul v4063 v3904
add v4062 v4064
mul v4048 v3906
add v4065 v4066
add v4061 v3782
sub v4068 v4067
shr v4069 v3778
land v4070 v3794
mul v3880 v3326
mul v3887 v3730
add v4072 v4073
mul v3900 v3715
add v4074 v4075
mul v3692 v3902
shr v3730 12893
mul v4078 v3904
add v4077 v4079
mul v4063 v3906
add v4080 v4081
add v4076 v3782
sub v4083 v4082
shr v4084 v3778
land v4085 v3794
mul v3880 v3341
mul v3887 v3745
add v4087 v4088
mul v3900 v3730
add v4089 v4090
mul v3707 v3902
shr v3745 12893
mul v4093 v3904
add v4092 v4094
mul v4078 v3906
add v4095 v4096
add v4091 v3782
sub v4098 v4097
shr v4099 v3778
land v4100 v3794
mul v3880 v3356
mul v3887 v3755
add v4102 v4103
mul v3900 v3745
add v4104 v4105
mul v3722 v3902
shr v3755 12893
mul v4108 v3904
add v4107 v4109
mul v4093 v3906
add v4110 v4111
add v4106 v3782
sub v4113 v4112
shr v4114 v3778
land v4115 v3794
mul v3880 v3366
mul v3900 v3755
add v4117 v4118
mul v3737 v3902
mul v4108 v3906
add v4120 v4121
add v4119 v3782
sub v4123 v4122
shr v4124 v3778
land v4125 v3794
shr v3770 v3777
land v4127 1
sub 1 v4128
shl 1 v3777
sub v4130 1
land v3770 v4131
add v4129 v4132
sub 1 v3921
add v4133 v4134
add v3765 v4135
mul v3785 v3404
sub v3535 v4137
sub v4137 v3535
add v4138 v4139
land v3535 18446744073709551615
gcd v4141 v771
mul v4142 157587932685088877
land v4143 18446744073709551615
shr v4144 58
shl v4145 3
shr x26 v4146
land v4147 255
shl v4148 1
add 18216 v4149
shl 1 v4150
sub v4151 1
shl v4151 2
sub v4151 v3404
sub v4151 v3793
shr v3921 15408
mul v4156 v4155
add v3921 v4157
mul v3790 v4154
add v3550 v4159
shr v3936 15408
mul v4161 v4155
add v3936 v4162
shl 1 18216
sub v4164 1
shr v4140 v4148
land v4166 v798
mul v4167 v4166
land v4168 v798
sub v802 v4169
mul v4166 v4170
land v4171 v798
land v4166 v807
mul v4173 v4172
land v4174 v807
sub v811 v4175
mul v4172 v4176
land v4177 v807
land v4166 v816
mul v4179 v4178
land v4180 v816
sub v820 v4181
mul v4178 v4182
land v4183 v816
land v4166 v825
mul v4185 v4184
land v4186 v825
sub v829 v4187
mul v4184 v4188
land v4189 v825
land v4166 v834
mul v4191 v4190
land v4192 v834
sub v838 v4193
mul v4190 v4194
land v4195 v834
land v4166 v843
mul v4197 v4196
land v4198 v843
sub v847 v4199
mul v4196 v4200
land v4201 v843
land v4166 v852
mul v4203 v4202
land v4204 v852
sub v856 v4205
mul v4202 v4206
land v4207 v852
land v4166 v861
mul v4209 v4208
land v4210 v861
sub v865 v4211
mul v4208 v4212
land v4213 v861
land v4166 v870
mul v4215 v4214
land v4216 v870
sub v874 v4217
mul v4214 v4218
land v4219 v870
land v4166 v879
mul v4221 v4220
land v4222 v879
sub v883 v4223
mul v4220 v4224
land v4225 v879
land v4166 v2235
mul v4227 v4226
land v4228 v2235
sub v2239 v4229
mul v4226 v4230
land v4231 v2235
land v4166 v3474
mul v4233 v4232
land v4234 v3474
sub v3478 v4235
mul v4232 v4236
land v4237 v3474
shl 1 18344
sub v4239 1
land v4166 v4240
mul v4241 v4238
land v4242 v4240
add v4240 3
sub v4244 v4243
mul v4238 v4245
land v4246 v4240
mul v4158 v4247
land v4248 v4152
mul v4249 v4249
land v4250 v4152
shl v4249 v4148
land v4252 v4152
mul v3785 v4253
sub 1 v3785
sub v4151 v4253
mul v4255 v4256
add v4254 v4257
shl v4163 v4148
land v4259 v4152
mul v4255 v4260
sub 1 v4255
sub v4151 v4260
mul v4262 v4263
add v4261 v4264
add v4265 v4151
mul v4160 v4249
land v4267 v4152
sub v4266 v4268
mul v4269 v4247
land v4270 v4152
shl v4251 12894
land v4272 v4152
shl v4258 15409
land v4274 v4152
shl v4271 15409
land v4276 v4152
mul v4251 v3565
mul v4258 v3951
add v4278 v4279
mul v4271 v3936
add v4280 v4281
mul v3913 v4273
shr v3951 15408
mul v4284 v4275
add v4283 v4285
mul v4161 v4277
add v4286 v4287
add v4282 v4153
sub v4289 v4288
shr v4290 v4149
land v4291 v4165
mul v4251 v3580
mul v4258 v3966
add v4293 v4294
mul v4271 v3951
add v4295 v4296
mul v3928 v4273
shr v3966 15408
mul v4299 v4275
add v4298 v4300
mul v4284 v4277
add v4301 v4302
add v4297 v4153
sub v4304 v4303
shr v4305 v4149
land v4306 v4165
mul v4251 v3595
mul v4258 v3981
add v4308 v4309
mul v4271 v3966
add v4310 v4311
mul v3943 v4273
shr v3981 15408
mul v4314 v4275
add v4313 v4315
mul v4299 v4277
add v4316 v4317
add v4312 v4153
sub v4319 v4318
shr v4320 v4149
land v4321 v4165
mul v4251 v3610
mul v4258 v3996
add v4323 v4324
mul v4271 v3981
add v4325 v4326
mul v3958 v4273
shr v3996 15408
mul v4329 v4275
add v4328 v4330
mul v4314 v4277
add v4331 v4332
add v4327 v4153
sub v4334 v4333
shr v4335 v4149
land v4336 v4165
mul v4251 v3625
mul v4258 v4011
add v4338 v4339
mul v4271 v3996
add v4340 v4341
mul v3973 v4273
shr v4011 15408
mul v4344 v4275
add v4343 v4345
mul v4329 v4277
add v4346 v4347
add v4342 v4153
sub v4349 v4348
shr v4350 v4149
land v4351 v4165
mul v4251 v3640
mul v4258 v4026
add v4353 v4354
mul v4271 v4011
add v4355 v4356
mul v3988 v4273
shr v4026 15408
mul v4359 v4275
add v4358 v4360
mul v4344 v4277
add v4361 v4362
add v4357 v4153
sub v4364 v4363
shr v4365 v4149
land v4366 v4165
mul v4251 v3655
mul v4258 v4041
add v4368 v4369
mul v4271 v4026
add v4370 v4371
mul v4003 v4273
shr v4041 15408
mul v4374 v4275
add v4373 v4375
mul v4359 v4277
add v4376 v4377
add v4372 v4153
sub v4379 v4378
shr v4380 v4149
land v4381 v4165
mul v4251 v3670
mul v4258 v4056
add v4383 v4384
mul v4271 v4041
add v4385 v4386
mul v4018 v4273
shr v4056 15408
mul v4389 v4275
add v4388 v4390
mul v4374 v4277
add v4391 v4392
add v4387 v4153
sub v4394 v4393
shr v4395 v4149
land v4396 v4165
mul v4251 v3685
mul v4258 v4071
add v4398 v4399
mul v4271 v4056
add v4400 v4401
mul v4033 v4273
shr v4071 15408
mul v4404 v4275
add v4403 v4405
mul v4389 v4277
add v4406 v4407
add v4402 v4153
sub v4409 v4408
shr v4410 v4149
land v4411 v4165
mul v4251 v3700
mul v4258 v4086
add v4413 v4414
mul v4271 v4071
add v4415 v4416
mul v4048 v4273
shr v4086 15408
mul v4419 v4275
add v4418 v4420
mul v4404 v4277
add v4421 v4422
add v4417 v4153
sub v4424 v4423
shr v4425 v4149
land v4426 v4165
mul v4251 v3715
mul v4258 v4101
add v4428 v4429
mul v4271 v4086
add v4430 v4431
mul v4063 v4273
shr v4101 15408
mul v4434 v4275
add v4433 v4435
mul v4419 v4277
add v4436 v4437
add v4432 v4153
sub v4439 v4438
shr v4440 v4149
land v4441 v4165
mul v4251 v3730
mul v4258 v4116
add v4443 v4444
mul v4271 v4101
add v4445 v4446
mul v4078 v4273
shr v4116 15408
mul v4449 v4275
add v4448 v4450
mul v4434 v4277
add v4451 v4452
add v4447 v4153
sub v4454 v4453
shr v4455 v4149
land v4456 v4165
mul v4251 v3745
mul v4258 v4126
add v4458 v4459
mul v4271 v4116
add v4460 v4461
mul v4093 v4273
shr v4126 15408
mul v4464 v4275
add v4463 v4465
mul v4449 v4277
add v4466 v4467
add v4462 v4153
sub v4469 v4468
shr v4470 v4149
land v4471 v4165
mul v4251 v3755
mul v4271 v4126
add v4473 v4474
mul v4108 v4273
mul v4464 v4277
add v4476 v4477
add v4475 v4153
sub v4479 v4478
shr v4480 v4149
land v4481 v4165
shr v4141 v4148
land v4483 1
sub 1 v4484
shl 1 v4148
sub v4486 1
land v4141 v4487
add v4485 v4488
sub 1 v4292
add v4489 v4490
add v4136 v4491
mul v4156 v3793
sub v3921 v4493
sub v4493 v3921
add v4494 v4495
land v3921 18446744073709551615
gcd v4497 v771
mul v4498 157587932685088877
land v4499 18446744073709551615
shr v4500 58
shl v4501 3
shr x26 v4502
land v4503 255
shl v4504 1
add 21315 v4505
shl 1 v4506
sub v4507 1
shl v4507 2
sub v4507 v3793
sub v4507 v4164
shr v4292 18215
mul v4512 v4511
add v4292 v4513
mul v4161 v4510
add v3936 v4515
shr v4307 18215
mul v4517 v4511
add v4307 v4518
shl 1 21315
sub v4520 1
shr v4496 v4504
land v4522 v798
mul v4523 v4522
land v4524 v798
sub v802 v4525
mul v4522 v4526
land v4527 v798
land v4522 v807
mul v4529 v4528
land v4530 v807
sub v811 v4531
mul v4528 v4532
land v4533 v807
land v4522 v816
mul v4535 v4534
land v4536 v816
sub v820 v4537
mul v4534 v4538
land v4539 v816
land v4522 v825
mul v4541 v4540
land v4542 v825
sub v829 v4543
mul v4540 v4544
land v4545 v825
land v4522 v834
mul v4547 v4546
land v4548 v834
sub v838 v4549
mul v4546 v4550
land v4551 v834
land v4522 v843
mul v4553 v4552
land v4554 v843
sub v847 v4555
mul v4552 v4556
land v4557 v843
land v4522 v852
mul v4559 v4558
land v4560 v852
sub v856 v4561
mul v4558 v4562
land v4563 v852
land v4522 v861
mul v4565 v4564
land v4566 v861
sub v865 v4567
mul v4564 v4568
land v4569 v861
land v4522 v870
mul v4571 v4570
land v4572 v870
sub v874 v4573
mul v4570 v4574
land v4575 v870
land v4522 v879
mul v4577 v4576
land v4578 v879
sub v883 v4579
mul v4576 v4580
land v4581 v879
land v4522 v2235
mul v4583 v4582
land v4584 v2235
sub v2239 v4585
mul v4582 v4586
land v4587 v2235
land v4522 v3474
mul v4589 v4588
land v4590 v3474
sub v3478 v4591
mul v4588 v4592
land v4593 v3474
shl 1 21443
sub v4595 1
land v4522 v4596
mul v4597 v4594
land v4598 v4596
add v4596 3
sub v4600 v4599
mul v4594 v4601
land v4602 v4596
mul v4514 v4603
land v4604 v4508
mul v4605 v4605
land v4606 v4508
shl v4605 v4504
land v4608 v4508
mul v4156 v4609
sub 1 v4156
sub v4507 v4609
mul v4611 v4612
add v4610 v4613
shl v4519 v4504
land v4615 v4508
mul v4611 v4616
sub 1 v4611
sub v4507 v4616
mul v4618 v4619
add v4617 v4620
add v4621 v4507
mul v4516 v4605
land v4623 v4508
sub v4622 v4624
mul v4625 v4603
land v4626 v4508
shl v4607 15409
land v4628 v4508
shl v4614 18216
land v4630 v4508
shl v4627 18216
land v4632 v4508
mul v4607 v3951
mul v4614 v4322
add v4634 v4635
mul v4627 v4307
add v4636 v4637
mul v4284 v4629
shr v4322 18215
mul v4640 v4631
add v4639 v4641
mul v4517 v4633
add v4642 v4643
add v4638 v4509
sub v4645 v4644
shr v4646 v4505
land v4647 v4521
mul v4607 v3966
mul v4614 v4337
add v4649 v4650
mul v4627 v4322
add v4651 v4652
mul v4299 v4629
shr v4337 18215
mul v4655 v4631
add v4654 v4656
mul v4640 v4633
add v4657 v4658
add v4653 v4509
sub v4660 v4659
shr v4661 v4505
land v4662 v4521
mul v4607 v3981
mul v4614 v4352
add v4664 v4665
mul v4627 v4337
add v4666 v4667
mul v4314 v4629
shr v4352 18215
mul v4670 v4631
add v4669 v4671
mul v4655 v4633
add v4672 v4673
add v4668 v4509
sub v4675 v4674
shr v4676 v4505
land v4677 v4521
mul v4607 v3996
mul v4614 v4367
add v4679 v4680
mul v4627 v4352
add v4681 v4682
mul v4329 v4629
shr v4367 18215
mul v4685 v4631
add v4684 v4686
mul v4670 v4633
add v4687 v4688
add v4683 v4509
sub v4690 v4689
shr v4691 v4505
land v4692 v4521
mul v4607 v4011
mul v4614 v4382
add v4694 v4695
mul v4627 v4367
add v4696 v4697
mul v4344 v4629
shr v4382 18215
mul v4700 v4631
add v4699 v4701
mul v4685 v4633
add v4702 v4703
add v4698 v4509
sub v4705 v4704
shr v4706 v4505
land v4707 v4521
mul v4607 v4026
mul v4614 v4397
add v4709 v4710
mul v4627 v4382
add v4711 v4712
mul v4359 v4629
shr v4397 18215
mul v4715 v4631
add v4714 v4716
mul v4700 v4633
add v4717 v4718
add v4713 v4509
sub v4720 v4719
shr v4721 v4505
land v4722 v4521
mul v4607 v4041
mul v4614 v4412
add v4724 v4725
mul v4627 v4397
add v4726 v4727
mul v4374 v4629
shr v4412 18215
mul v4730 v4631
add v4729 v4731
mul v4715 v4633
add v4732 v4733
add v4728 v4509
sub v4735 v4734
shr v4736 v4505
land v4737 v4521
mul v4607 v4056
mul v4614 v4427
add v4739 v4740
mul v4627 v4412
add v4741 v4742
mul v4389 v4629
shr v4427 18215
mul v4745 v4631
add v4744 v4746
mul v4730 v4633
add v4747 v4748
add v4743 v4509
sub v4750 v4749
shr v4751 v4505
land v4752 v4521
mul v4607 v4071
mul v4614 v4442
add v4754 v4755
mul v4627 v4427
add v4756 v4757
mul v4404 v4629
shr v4442 18215
mul v4760 v4631
add v4759 v4761
mul v4745 v4633
add v4762 v4763
add v4758 v4509
sub v4765 v4764
shr v4766 v4505
land v4767 v4521
mul v4607 v4086
mul v4614 v4457
add v4769 v4770
mul v4627 v4442
add v4771 v4772
mul v4419 v4629
shr v4457 18215
mul v4775 v4631
add v4774 v4776
mul v4760 v4633
add v4777 v4778
add v4773 v4509
sub v4780 v4779
shr v4781 v4505
land v4782 v4521
mul v4607 v4101
mul v4614 v4472
add v4784 v4785
mul v4627 v4457
add v4786 v4787
mul v4434 v4629
shr v4472 18215
mul v4790 v4631
add v4789 v4791
mul v4775 v4633
add v4792 v4793
add v4788 v4509
sub v4795 v4794
shr v4796 v4505
land v4797 v4521
mul v4607 v4116
mul v4614 v4482
add v4799 v4800
mul v4627 v4472
add v4801 v4802
mul v4449 v4629
shr v4482 18215
mul v4805 v4631
add v4804 v4806
mul v4790 v4633
add v4807 v4808
add v4803 v4509
sub v4810 v4809
shr v4811 v4505
land v4812 v4521
mul v4607 v4126
mul v4627 v4482
add v4814 v4815
mul v4464 v4629
mul v4805 v4633
add v4817 v4818
add v4816 v4509
sub v4820 v4819
shr v4821 v4505
land v4822 v4521
shr v4497 v4504
land v4824 1
sub 1 v4825
shl 1 v4504
sub v4827 1
land v4497 v4828
add v4826 v4829
sub 1 v4648
add v4830 v4831
add v4492 v4832
mul v4512 v4164
sub v4292 v4834
sub v4834 v4292
add v4835 v4836
land v4292 18446744073709551615
gcd v4838 v771
mul v4839 157587932685088877
land v4840 18446744073709551615
shr v4841 58
shl v4842 3
shr x26 v4843
land v4844 255
shl v4845 1
add 24703 v4846
shl 1 v4847
sub v4848 1
shl v4848 2
sub v4848 v4164
sub v4848 v4520
shr v4648 21314
mul v4853 v4852
add v4648 v4854
mul v4517 v4851
add v4307 v4856
shr v4663 21314
mul v4858 v4852
add v4663 v4859
shl 1 24703
sub v4861 1
shr v4837 v4845
land v4863 v798
mul v4864 v4863
land v4865 v798
sub v802 v4866
mul v4863 v4867
land v4868 v798
land v4863 v807
mul v4870 v4869
land v4871 v807
sub v811 v4872
mul v4869 v4873
land v4874 v807
land v4863 v816
mul v4876 v4875
land v4877 v816
sub v820 v4878
mul v4875 v4879
land v4880 v816
land v4863 v825
mul v4882 v4881
land v4883 v825
sub v829 v4884
mul v4881 v4885
land v4886 v825
land v4863 v834
mul v4888 v4887
land v4889 v834
sub v838 v4890
mul v4887 v4891
land v4892 v834
land v4863 v843
mul v4894 v4893
land v4895 v843
sub v847 v4896
mul v4893 v4897
land v4898 v843
land v4863 v852
mul v4900 v4899
land v4901 v852
sub v856 v4902
mul v4899 v4903
land v4904 v852
land v4863 v861
mul v4906 v4905
land v4907 v861
sub v865 v4908
mul v4905 v4909
land v4910 v861
land v4863 v870
mul v4912 v4911
land v4913 v870
sub v874 v4914
mul v4911 v4915
land v4916 v870
land v4863 v879
mul v4918 v4917
land v4919 v879
sub v883 v4920
mul v4917 v4921
land v4922 v879
land v4863 v2235
mul v4924 v4923
land v4925 v2235
sub v2239 v4926
mul v4923 v4927
land v4928 v2235
land v4863 v3474
mul v4930 v4929
land v4931 v3474
sub v3478 v4932
mul v4929 v4933
land v4934 v3474
shl 1 24576
sub v4936 1
land v4863 v4937
mul v4938 v4935
land v4939 v4937
add v4937 3
sub v4941 v4940
mul v4935 v4942
land v4943 v4937
shl 1 24831
sub v4945 1
land v4863 v4946
mul v4947 v4944
land v4948 v4946
add v4946 3
sub v4950 v4949
mul v4944 v4951
land v4952 v4946
mul v4855 v4953
land v4954 v4849
mul v4955 v4955
land v4956 v4849
shl v4955 v4845
land v4958 v4849
mul v4512 v4959
sub 1 v4512
sub v4848 v4959
mul v4961 v4962
add v4960 v4963
shl v4860 v4845
land v4965 v4849
mul v4961 v4966
sub 1 v4961
sub v4848 v4966
mul v4968 v4969
add v4967 v4970
add v4971 v4848
mul v4857 v4955
land v4973 v4849
sub v4972 v4974
mul v4975 v4953
land v4976 v4849
shl v4957 18216
land v4978 v4849
shl v4964 21315
land v4980 v4849
shl v4977 21315
land v4982 v4849
mul v4957 v4322
mul v4964 v4678
add v4984 v4985
mul v4977 v4663
add v4986 v4987
mul v4640 v4979
shr v4678 21314
mul v4990 v4981
add v4989 v4991
mul v4858 v4983
add v4992 v4993
add v4988 v4850
sub v4995 v4994
shr v4996 v4846
land v4997 v4862
mul v4957 v4337
mul v4964 v4693
add v4999 v5000
mul v4977 v4678
add v5001 v5002
mul v4655 v4979
shr v4693 21314
mul v5005 v4981
add v5004 v5006
mul v4990 v4983
add v5007 v5008
add v5003 v4850
sub v5010 v5009
shr v5011 v4846
land v5012 v4862
mul v4957 v4352
mul v4964 v4708
add v5014 v5015
mul v4977 v4693
add v5016 v5017
mul v4670 v4979
shr v4708 21314
mul v5020 v4981
add v5019 v5021
mul v5005 v4983
add v5022 v5023
add v5018 v4850
sub v5025 v5024
shr v5026 v4846
land v5027 v4862
mul v4957 v4367
mul v4964 v4723
add v5029 v5030
mul v4977 v4708
add v5031 v5032
mul v4685 v4979
shr v4723 21314
mul v5035 v4981
add v5034 v5036
mul v5020 v4983
add v5037 v5038
add v5033 v4850
sub v5040 v5039
shr v5041 v4846
land v5042 v4862
mul v4957 v4382
mul v4964 v4738
add v5044 v5045
mul v4977 v4723
add v5046 v5047
mul v4700 v4979
shr v4738 21314
mul v5050 v4981
add v5049 v5051
mul v5035 v4983
add v5052 v5053
add v5048 v4850
sub v5055 v5054
shr v5056 v4846
land v5057 v4862
mul v4957 v4397
mul v4964 v4753
add v5059 v5060
mul v4977 v4738
add v5061 v5062
mul v4715 v4979
shr v4753 21314
mul v5065 v4981
add v5064 v5066
mul v5050 v4983
add v5067 v5068
add v5063 v4850
sub v5070 v5069
shr v5071 v4846
land v5072 v4862
mul v4957 v4412
mul v4964 v4768
add v5074 v5075
mul v4977 v4753
add v5076 v5077
mul v4730 v4979
shr v4768 21314
mul v5080 v4981
add v5079 v5081
mul v5065 v4983
add v5082 v5083
add v5078 v4850
sub v5085 v5084
shr v5086 v4846
land v5087 v4862
mul v4957 v4427
mul v4964 v4783
add v5089 v5090
mul v4977 v4768
add v5091 v5092
mul v4745 v4979
shr v4783 21314
mul v5095 v4981
add v5094 v5096
mul v5080 v4983
add v5097 v5098
add v5093 v4850
sub v5100 v5099
shr v5101 v4846
land v5102 v4862
mul v4957 v4442
mul v4964 v4798
add v5104 v5105
mul v4977 v4783
add v5106 v5107
mul v4760 v4979
shr v4798 21314
mul v5110 v4981
add v5109 v5111
mul v5095 v4983
add v5112 v5113
add v5108 v4850
sub v5115 v5114
shr v5116 v4846
land v5117 v4862
mul v4957 v4457
mul v4964 v4813
add v5119 v5120
mul v4977 v4798
add v5121 v5122
mul v4775 v4979
shr v4813 21314
mul v5125 v4981
add v5124 v5126
mul v5110 v4983
add v5127 v5128
add v5123 v4850
sub v5130 v5129
shr v5131 v4846
land v5132 v4862
mul v4957 v4472
mul v4964 v4823
add v5134 v5135
mul v4977 v4813
add v5136 v5137
mul v4790 v4979
shr v4823 21314
mul v5140 v4981
add v5139 v5141
mul v5125 v4983
add v5142 v5143
add v5138 v4850
sub v5145 v5144
shr v5146 v4846
land v5147 v4862
mul v4957 v4482
mul v4977 v4823
add v5149 v5150
mul v4805 v4979
mul v5140 v4983
add v5152 v5153
add v5151 v4850
sub v5155 v5154
shr v5156 v4846
land v5157 v4862
shr v4838 v4845
land v5159 1
sub 1 v5160
shl 1 v4845
sub v5162 1
land v4838 v5163
add v5161 v5164
sub 1 v4998
add v5165 v5166
add v4833 v5167
mul v4853 v4520
sub v4648 v5169
sub v5169 v4648
add v5170 v5171
land v4648 18446744073709551615
gcd v5173 v771
mul v5174 157587932685088877
land v5175 18446744073709551615
shr v5176 58
shl v5177 3
shr x26 v5178
land v5179 255
shl v5180 1
add 28382 v5181
shl 1 v5182
sub v5183 1
shl v5183 2
sub v5183 v4520
sub v5183 v4861
shr v4998 24702
mul v5188 v5187
add v4998 v5189
mul v4858 v5186
add v4663 v5191
shr v5013 24702
mul v5193 v5187
add v5013 v5194
shl 1 28382
sub v5196 1
shr v5172 v5180
land v5198 v798
mul v5199 v5198
land v5200 v798
sub v802 v5201
mul v5198 v5202
land v5203 v798
land v5198 v807
mul v5205 v5204
land v5206 v807
sub v811 v5207
mul v5204 v5208
land v5209 v807
land v5198 v816
mul v5211 v5210
land v5212 v816
sub v820 v5213
mul v5210 v5214
land v5215 v816
land v5198 v825
mul v5217 v5216
land v5218 v825
sub v829 v5219
mul v5216 v5220
land v5221 v825
land v5198 v834
mul v5223 v5222
land v5224 v834
sub v838 v5225
mul v5222 v5226
land v5227 v834
land v5198 v843
mul v5229 v5228
land v5230 v843
sub v847 v5231
mul v5228 v5232
land v5233 v843
land v5198 v852
mul v5235 v5234
land v5236 v852
sub v856 v5237
mul v5234 v5238
land v5239 v852
land v5198 v861
mul v5241 v5240
land v5242 v861
sub v865 v5243
mul v5240 v5244
land v5245 v861
land v5198 v870
mul v5247 v5246
land v5248 v870
sub v874 v5249
mul v5246 v5250
land v5251 v870
land v5198 v879
mul v5253 v5252
land v5254 v879
sub v883 v5255
mul v5252 v5256
land v5257 v879
land v5198 v2235
mul v5259 v5258
land v5260 v2235
sub v2239 v5261
mul v5258 v5262
land v5263 v2235
land v5198 v3474
mul v5265 v5264
land v5266 v3474
sub v3478 v5267
mul v5264 v5268
land v5269 v3474
land v5198 v4937
mul v5271 v5270
land v5272 v4937
sub v4941 v5273
mul v5270 v5274
land v5275 v4937
shl 1 28510
sub v5277 1
land v5198 v5278
mul v5279 v5276
land v5280 v5278
add v5278 3
sub v5282 v5281
mul v5276 v5283
land v5284 v5278
mul v5190 v5285
land v5286 v5184
mul v5287 v5287
land v5288 v5184
shl v5287 v5180
land v5290 v5184
mul v4853 v5291
sub 1 v4853
sub v5183 v5291
mul v5293 v5294
add v5292 v5295
shl v5195 v5180
land v5297 v5184
mul v5293 v5298
sub 1 v5293
sub v5183 v5298
mul v5300 v5301
add v5299 v5302
add v5303 v5183
mul v5192 v5287
land v5305 v5184
sub v5304 v5306
mul v5307 v5285
land v5308 v5184
shl v5289 21315
land v5310 v5184
shl v5296 24703
land v5312 v5184
shl v5309 24703
land v5314 v5184
mul v5289 v4678
mul v5296 v5028
add v5316 v5317
mul v5309 v5013
add v5318 v5319
mul v4990 v5311
shr v5028 24702
mul v5322 v5313
add v5321 v5323
mul v5193 v5315
add v5324 v5325
add v5320 v5185
sub v5327 v5326
shr v5328 v5181
land v5329 v5197
mul v5289 v4693
mul v5296 v5043
add v5331 v5332
mul v5309 v5028
add v5333 v5334
mul v5005 v5311
shr v5043 24702
mul v5337 v5313
add v5336 v5338
mul v5322 v5315
add v5339 v5340
add v5335 v5185
sub v5342 v5341
shr v5343 v5181
land v5344 v5197
mul v5289 v4708
mul v5296 v5058
add v5346 v5347
mul v5309 v5043
add v5348 v5349
mul v5020 v5311
shr v5058 24702
mul v5352 v5313
add v5351 v5353
mul v5337 v5315
add v5354 v5355
add v5350 v5185
sub v5357 v5356
shr v5358 v5181
land v5359 v5197
mul v5289 v4723
mul v5296 v5073
add v5361 v5362
mul v5309 v5058
add v5363 v5364
mul v5035 v5311
shr v5073 24702
mul v5367 v5313
add v5366 v5368
mul v5352 v5315
add v5369 v5370
add v5365 v5185
sub v5372 v5371
shr v5373 v5181
land v5374 v5197
mul v5289 v4738
mul v5296 v5088
add v5376 v5377
mul v5309 v5073
add v5378 v5379
mul v5050 v5311
shr v5088 24702
mul v5382 v5313
add v5381 v5383
mul v5367 v5315
add v5384 v5385
add v5380 v5185
sub v5387 v5386
shr v5388 v5181
land v5389 v5197
mul v5289 v4753
mul v5296 v5103
add v5391 v5392
mul v5309 v5088
add v5393 v5394
mul v5065 v5311
shr v5103 24702
mul v5397 v5313
add v5396 v5398
mul v5382 v5315
add v5399 v5400
add v5395 v5185
sub v5402 v5401
shr v5403 v5181
land v5404 v5197
mul v5289 v4768
mul v5296 v5118
add v5406 v5407
mul v5309 v5103
add v5408 v5409
mul v5080 v5311
shr v5118 24702
mul v5412 v5313
add v5411 v5413
mul v5397 v5315
add v5414 v5415
add v5410 v5185
sub v5417 v5416
shr v5418 v5181
land v5419 v5197
mul v5289 v4783
mul v5296 v5133
add v5421 v5422
mul v5309 v5118
add v5423 v5424
mul v5095 v5311
shr v5133 24702
mul v5427 v5313
add v5426 v5428
mul v5412 v5315
add v5429 v5430
add v5425 v5185
sub v5432 v5431
shr v5433 v5181
land v5434 v5197
mul v5289 v4798
mul v5296 v5148
add v5436 v5437
mul v5309 v5133
add v5438 v5439
mul v5110 v5311
shr v5148 24702
mul v5442 v5313
add v5441 v5443
mul v5427 v5315
add v5444 v5445
add v5440 v5185
sub v5447 v5446
shr v5448 v5181
land v5449 v5197
mul v5289 v4813
mul v5296 v5158
add v5451 v5452
mul v5309 v5148
add v5453 v5454
mul v5125 v5311
shr v5158 24702
mul v5457 v5313
add v5456 v5458
mul v5442 v5315
add v5459 v5460
add v5455 v5185
sub v5462 v5461
shr v5463 v5181
land v5464 v5197
mul v5289 v4823
mul v5309 v5158
add v5466 v5467
mul v5140 v5311
mul v5457 v5315
add v5469 v5470
add v5468 v5185
sub v5472 v5471
shr v5473 v5181
land v5474 v5197
shr v5173 v5180
land v5476 1
sub 1 v5477
shl 1 v5180
sub v5479 1
land v5173 v5480
add v5478 v5481
sub 1 v5330
add v5482 v5483
add v5168 v5484
mul v5188 v4861
sub v4998 v5486
sub v5486 v4998
add v5487 v5488
land v4998 18446744073709551615
gcd v5490 v771
mul v5491 157587932685088877
land v5492 18446744073709551615
shr v5493 58
shl v5494 3
shr x26 v5495
land v5496 255
shl v5497 1
add 32350 v5498
shl 1 v5499
sub v5500 1
shl v5500 2
sub v5500 v4861
sub v5500 v5196
shr v5330 28381
mul v5505 v5504
add v5330 v5506
mul v5193 v5503
add v5013 v5508
shr v5345 28381
mul v5510 v5504
add v5345 v5511
shl 1 32350
sub v5513 1
shr v5489 v5497
land v5515 v798
mul v5516 v5515
land v5517 v798
sub v802 v5518
mul v5515 v5519
land v5520 v798
land v5515 v807
mul v5522 v5521
land v5523 v807
sub v811 v5524
mul v5521 v5525
land v5526 v807
land v5515 v816
mul v5528 v5527
land v5529 v816
sub v820 v5530
mul v5527 v5531
land v5532 v816
land v5515 v825
mul v5534 v5533
land v5535 v825
sub v829 v5536
mul v5533 v5537
land v5538 v825
land v5515 v834
mul v5540 v5539
land v5541 v834
sub v838 v5542
mul v5539 v5543
land v5544 v834
land v5515 v843
mul v5546 v5545
land v5547 v843
sub v847 v5548
mul v5545 v5549
land v5550 v843
land v5515 v852
mul v5552 v5551
land v5553 v852
sub v856 v5554
mul v5551 v5555
land v5556 v852
land v5515 v861
mul v5558 v5557
land v5559 v861
sub v865 v5560
mul v5557 v5561
land v5562 v861
land v5515 v870
mul v5564 v5563
land v5565 v870
sub v874 v5566
mul v5563 v5567
land v5568 v870
land v5515 v879
mul v5570 v5569
land v5571 v879
sub v883 v5572
mul v5569 v5573
land v5574 v879
land v5515 v2235
mul v5576 v5575
land v5577 v2235
sub v2239 v5578
mul v5575 v5579
land v5580 v2235
land v5515 v3474
mul v5582 v5581
land v5583 v3474
sub v3478 v5584
mul v5581 v5585
land v5586 v3474
land v5515 v4937
mul v5588 v5587
land v5589 v4937
sub v4941 v5590
mul v5587 v5591
land v5592 v4937
shl 1 32478
sub v5594 1
land v5515 v5595
mul v5596 v5593
land v5597 v5595
add v5595 3
sub v5599 v5598
mul v5593 v5600
land v5601 v5595
mul v5507 v5602
land v5603 v5501
mul v5604 v5604
land v5605 v5501
shl v5604 v5497
land v5607 v5501
mul v5188 v5608
sub 1 v5188
sub v5500 v5608
mul v5610 v5611
add v5609 v5612
shl v5512 v5497
land v5614 v5501
mul v5610 v5615
sub 1 v5610
sub v5500 v5615
mul v5617 v5618
add v5616 v5619
add v5620 v5500
mul v5509 v5604
land v5622 v5501
sub v5621 v5623
mul v5624 v5602
land v5625 v5501
shl v5606 24703
land v5627 v5501
shl v5613 28382
land v5629 v5501
shl v5626 28382
land v5631 v5501
mul v5606 v5028
mul v5613 v5360
add v5633 v5634
mul v5626 v5345
add v5635 v5636
mul v5322 v5628
shr v5360 28381
mul v5639 v5630
add v5638 v5640
mul v5510 v5632
add v5641 v5642
add v5637 v5502
sub v5644 v5643
shr v5645 v5498
land v5646 v5514
mul v5606 v5043
mul v5613 v5375
add v5648 v5649
mul v5626 v5360
add v5650 v5651
mul v5337 v5628
shr v5375 28381
mul v5654 v5630
add v5653 v5655
mul v5639 v5632
add v5656 v5657
add v5652 v5502
sub v5659 v5658
shr v5660 v5498
land v5661 v5514
mul v5606 v5058
mul v5613 v5390
add v5663 v5664
mul v5626 v5375
add v5665 v5666
mul v5352 v5628
shr v5390 28381
mul v5669 v5630
add v5668 v5670
mul v5654 v5632
add v5671 v5672
add v5667 v5502
sub v5674 v5673
shr v5675 v5498
land v5676 v5514
mul v5606 v5073
mul v5613 v5405
add v5678 v5679
mul v5626 v5390
add v5680 v5681
mul v5367 v5628
shr v5405 28381
mul v5684 v5630
add v5683 v5685
mul v5669 v5632
add v5686 v5687
add v5682 v5502
sub v5689 v5688
shr v5690 v5498
land v5691 v5514
mul v5606 v5088
mul v5613 v5420
add v5693 v5694
mul v5626 v5405
add v5695 v5696
mul v5382 v5628
shr v5420 28381
mul v5699 v5630
add v5698 v5700
mul v5684 v5632
add v5701 v5702
add v5697 v5502
sub v5704 v5703
shr v5705 v5498
land v5706 v5514
mul v5606 v5103
mul v5613 v5435
add v5708 v5709
mul v5626 v5420
add v5710 v5711
mul v5397 v5628
shr v5435 28381
mul v5714 v5630
add v5713 v5715
mul v5699 v5632
add v5716 v5717
add v5712 v5502
sub v5719 v5718
shr v5720 v5498
land v5721 v5514
mul v5606 v5118
mul v5613 v5450
add v5723 v5724
mul v5626 v5435
add v5725 v5726
mul v5412 v5628
shr v5450 28381
mul v5729 v5630
add v5728 v5730
mul v5714 v5632
add v5731 v5732
add v5727 v5502
sub v5734 v5733
shr v5735 v5498
land v5736 v5514
mul v5606 v5133
mul v5613 v5465
add v5738 v5739
mul v5626 v5450
add v5740 v5741
mul v5427 v5628
shr v5465 28381
mul v5744 v5630
add v5743 v5745
mul v5729 v5632
add v5746 v5747
add v5742 v5502
sub v5749 v5748
shr v5750 v5498
land v5751 v5514
mul v5606 v5148
mul v5613 v5475
add v5753 v5754
mul v5626 v5465
add v5755 v5756
mul v5442 v5628
shr v5475 28381
mul v5759 v5630
add v5758 v5760
mul v5744 v5632
add v5761 v5762
add v5757 v5502
sub v5764 v5763
shr v5765 v5498
land v5766 v5514
mul v5606 v5158
mul v5626 v5475
add v5768 v5769
mul v5457 v5628
mul v5759 v5632
add v5771 v5772
add v5770 v5502
sub v5774 v5773
shr v5775 v5498
land v5776 v5514
shr v5490 v5497
land v5778 1
sub 1 v5779
shl 1 v5497
sub v5781 1
land v5490 v5782
add v5780 v5783
sub 1 v5647
add v5784 v5785
add v5485 v5786
mul v5505 v5196
sub v5330 v5788
sub v5788 v5330
add v5789 v5790
land v5330 18446744073709551615
gcd v5792 v771
mul v5793 157587932685088877
land v5794 18446744073709551615
shr v5795 58
shl v5796 3
shr x26 v5797
land v5798 255
shl v5799 1
add 36609 v5800
shl 1 v5801
sub v5802 1
shl v5802 2
sub v5802 v5196
sub v5802 v5513
shr v5647 32349
mul v5807 v5806
add v5647 v5808
mul v5510 v5805
add v5345 v5810
shr v5662 32349
mul v5812 v5806
add v5662 v5813
shl 1 36609
sub v5815 1
shr v5791 v5799
land v5817 v798
mul v5818 v5817
land v5819 v798
sub v802 v5820
mul v5817 v5821
land v5822 v798
land v5817 v807
mul v5824 v5823
land v5825 v807
sub v811 v5826
mul v5823 v5827
land v5828 v807
land v5817 v816
mul v5830 v5829
land v5831 v816
sub v820 v5832
mul v5829 v5833
land v5834 v816
land v5817 v825
mul v5836 v5835
land v5837 v825
sub v829 v5838
mul v5835 v5839
land v5840 v825
land v5817 v834
mul v5842 v5841
land v5843 v834
sub v838 v5844
mul v5841 v5845
land v5846 v834
land v5817 v843
mul v5848 v5847
land v5849 v843
sub v847 v5850
mul v5847 v5851
land v5852 v843
land v5817 v852
mul v5854 v5853
land v5855 v852
sub v856 v5856
mul v5853 v5857
land v5858 v852
land v5817 v861
mul v5860 v5859
land v5861 v861
sub v865 v5862
mul v5859 v5863
land v5864 v861
land v5817 v870
mul v5866 v5865
land v5867 v870
sub v874 v5868
mul v5865 v5869
land v5870 v870
land v5817 v879
mul v5872 v5871
land v5873 v879
sub v883 v5874
mul v5871 v5875
land v5876 v879
land v5817 v2235
mul v5878 v5877
land v5879 v2235
sub v2239 v5880
mul v5877 v5881
land v5882 v2235
land v5817 v3474
mul v5884 v5883
land v5885 v3474
sub v3478 v5886
mul v5883 v5887
land v5888 v3474
land v5817 v4937
mul v5890 v5889
land v5891 v4937
sub v4941 v5892
mul v5889 v5893
land v5894 v4937
shl 1 36737
sub v5896 1
land v5817 v5897
mul v5898 v5895
land v5899 v5897
add v5897 3
sub v5901 v5900
mul v5895 v5902
land v5903 v5897
mul v5809 v5904
land v5905 v5803
mul v5906 v5906
land v5907 v5803
shl v5906 v5799
land v5909 v5803
mul v5505 v5910
sub 1 v5505
sub v5802 v5910
mul v5912 v5913
add v5911 v5914
shl v5814 v5799
land v5916 v5803
mul v5912 v5917
sub 1 v5912
sub v5802 v5917
mul v5919 v5920
add v5918 v5921
add v5922 v5802
mul v5811 v5906
land v5924 v5803
sub v5923 v5925
mul v5926 v5904
land v5927 v5803
shl v5908 28382
land v5929 v5803
shl v5915 32350
land v5931 v5803
shl v5928 32350
land v5933 v5803
mul v5908 v5360
mul v5915 v5677
add v5935 v5936
mul v5928 v5662
add v5937 v5938
mul v5639 v5930
shr v5677 32349
mul v5941 v5932
add v5940 v5942
mul v5812 v5934
add v5943 v5944
add v5939 v5804
sub v5946 v5945
shr v5947 v5800
land v5948 v5816
mul v5908 v5375
mul v5915 v5692
add v5950 v5951
mul v5928 v5677
add v5952 v5953
mul v5654 v5930
shr v5692 32349
mul v5956 v5932
add v5955 v5957
mul v5941 v5934
add v5958 v5959
add v5954 v5804
sub v5961 v5960
shr v5962 v5800
land v5963 v5816
mul v5908 v5390
mul v5915 v5707
add v5965 v5966
mul v5928 v5692
add v5967 v5968
mul v5669 v5930
shr v5707 32349
mul v5971 v5932
add v5970 v5972
mul v5956 v5934
add v5973 v5974
add v5969 v5804
sub v5976 v5975
shr v5977 v5800
land v5978 v5816
mul v5908 v5405
mul v5915 v5722
add v5980 v5981
mul v5928 v5707
add v5982 v5983
mul v5684 v5930
shr v5722 32349
mul v5986 v5932
add v5985 v5987
mul v5971 v5934
add v5988 v5989
add v5984 v5804
sub v5991 v5990
shr v5992 v5800
land v5993 v5816
mul v5908 v5420
mul v5915 v5737
add v5995 v5996
mul v5928 v5722
add v5997 v5998
mul v5699 v5930
shr v5737 32349
mul v6001 v5932
add v6000 v6002
mul v5986 v5934
add v6003 v6004
add v5999 v5804
sub v6006 v6005
shr v6007 v5800
land v6008 v5816
mul v5908 v5435
mul v5915 v5752
add v6010 v6011
mul v5928 v5737
add v6012 v6013
mul v5714 v5930
shr v5752 32349
mul v6016 v5932
add v6015 v6017
mul v6001 v5934
add v6018 v6019
add v6014 v5804
sub v6021 v6020
shr v6022 v5800
land v6023 v5816
mul v5908 v5450
mul v5915 v5767
add v6025 v6026
mul v5928 v5752
add v6027 v6028
mul v5729 v5930
shr v5767 32349
mul v6031 v5932
add v6030 v6032
mul v6016 v5934
add v6033 v6034
add v6029 v5804
sub v6036 v6035
shr v6037 v5800
land v6038 v5816
mul v5908 v5465
mul v5915 v5777
add v6040 v6041
mul v5928 v5767
add v6042 v6043
mul v5744 v5930
shr v5777 32349
mul v6046 v5932
add v6045 v6047
mul v6031 v5934
add v6048 v6049
add v6044 v5804
sub v6051 v6050
shr v6052 v5800
land v6053 v5816
mul v5908 v5475
mul v5928 v5777
add v6055 v6056
mul v5759 v5930
mul v6046 v5934
add v6058 v6059
add v6057 v5804
sub v6061 v6060
shr v6062 v5800
land v6063 v5816
shr v5792 v5799
land v6065 1
sub 1 v6066
shl 1 v5799
sub v6068 1
land v5792 v6069
add v6067 v6070
sub 1 v5949
add v6071 v6072
add v5787 v6073
mul v5807 v5513
sub v5647 v6075
sub v6075 v5647
add v6076 v6077
land v5647 18446744073709551615
gcd v6079 v771
mul v6080 157587932685088877
land v6081 18446744073709551615
shr v6082 58
shl v6083 3
shr x26 v6084
land v6085 255
shl v6086 1
add 41156 v6087
shl 1 v6088
sub v6089 1
shl v6089 2
sub v6089 v5513
sub v6089 v5815
shr v5949 36608
mul v6094 v6093
add v5949 v6095
mul v5812 v6092
add v5662 v6097
shr v5964 36608
mul v6099 v6093
add v5964 v6100
shl 1 41156
sub v6102 1
shr v6078 v6086
land v6104 v798
mul v6105 v6104
land v6106 v798
sub v802 v6107
mul v6104 v6108
land v6109 v798
land v6104 v807
mul v6111 v6110
land v6112 v807
sub v811 v6113
mul v6110 v6114
land v6115 v807
land v6104 v816
mul v6117 v6116
land v6118 v816
sub v820 v6119
mul v6116 v6120
land v6121 v816
land v6104 v825
mul v6123 v6122
land v6124 v825
sub v829 v6125
mul v6122 v6126
land v6127 v825
land v6104 v834
mul v6129 v6128
land v6130 v834
sub v838 v6131
mul v6128 v6132
land v6133 v834
land v6104 v843
mul v6135 v6134
land v6136 v843
sub v847 v6137
mul v6134 v6138
land v6139 v843
land v6104 v852
mul v6141 v6140
land v6142 v852
sub v856 v6143
mul v6140 v6144
land v6145 v852
land v6104 v861
mul v6147 v6146
land v6148 v861
sub v865 v6149
mul v6146 v6150
land v6151 v861
land v6104 v870
mul v6153 v6152
land v6154 v870
sub v874 v6155
mul v6152 v6156
land v6157 v870
land v6104 v879
mul v6159 v6158
land v6160 v879
sub v883 v6161
mul v6158 v6162
land v6163 v879
land v6104 v2235
mul v6165 v6164
land v6166 v2235
sub v2239 v6167
mul v6164 v6168
land v6169 v2235
land v6104 v3474
mul v6171 v6170
land v6172 v3474
sub v3478 v6173
mul v6170 v6174
land v6175 v3474
land v6104 v4937
mul v6177 v6176
land v6178 v4937
sub v4941 v6179
mul v6176 v6180
land v6181 v4937
shl 1 41284
sub v6183 1
land v6104 v6184
mul v6185 v6182
land v6186 v6184
add v6184 3
sub v6188 v6187
mul v6182 v6189
land v6190 v6184
mul v6096 v6191
land v6192 v6090
mul v6193 v6193
land v6194 v6090
shl v6193 v6086
land v6196 v6090
mul v5807 v6197
sub 1 v5807
sub v6089 v6197
mul v6199 v6200
add v6198 v6201
shl v6101 v6086
land v6203 v6090
mul v6199 v6204
sub 1 v6199
sub v6089 v6204
mul v6206 v6207
add v6205 v6208
add v6209 v6089
mul v6098 v6193
land v6211 v6090
sub v6210 v6212
mul v6213 v6191
land v6214 v6090
shl v6195 32350
land v6216 v6090
shl v6202 36609
land v6218 v6090
shl v6215 36609
land v6220 v6090
mul v6195 v5677
mul v6202 v5979
add v6222 v6223
mul v6215 v5964
add v6224 v6225
mul v5941 v6217
shr v5979 36608
mul v6228 v6219
add v6227 v6229
mul v6099 v6221
add v6230 v6231
add v6226 v6091
sub v6233 v6232
shr v6234 v6087
land v6235 v6103
mul v6195 v5692
mul v6202 v5994
add v6237 v6238
mul v6215 v5979
add v6239 v6240
mul v5956 v6217
shr v5994 36608
mul v6243 v6219
add v6242 v6244
mul v6228 v6221
add v6245 v6246
add v6241 v6091
sub v6248 v6247
shr v6249 v6087
land v6250 v6103
mul v6195 v5707
mul v6202 v6009
add v6252 v6253
mul v6215 v5994
add v6254 v6255
mul v5971 v6217
shr v6009 36608
mul v6258 v6219
add v6257 v6259
mul v6243 v6221
add v6260 v6261
add v6256 v6091
sub v6263 v6262
shr v6264 v6087
land v6265 v6103
mul v6195 v5722
mul v6202 v6024
add v6267 v6268
mul v6215 v6009
add v6269 v6270
mul v5986 v6217
shr v6024 36608
mul v6273 v6219
add v6272 v6274
mul v6258 v6221
add v6275 v6276
add v6271 v6091
sub v6278 v6277
shr v6279 v6087
land v6280 v6103
mul v6195 v5737
mul v6202 v6039
add v6282 v6283
mul v6215 v6024
add v6284 v6285
mul v6001 v6217
shr v6039 36608
mul v6288 v6219
add v6287 v6289
mul v6273 v6221
add v6290 v6291
add v6286 v6091
sub v6293 v6292
shr v6294 v6087
land v6295 v6103
mul v6195 v5752
mul v6202 v6054
add v6297 v6298
mul v6215 v6039
add v6299 v6300
mul v6016 v6217
shr v6054 36608
mul v6303 v6219
add v6302 v6304
mul v6288 v6221
add v6305 v6306
add v6301 v6091
sub v6308 v6307
shr v6309 v6087
land v6310 v6103
mul v6195 v5767
mul v6202 v6064
add v6312 v6313
mul v6215 v6054
add v6314 v6315
mul v6031 v6217
shr v6064 36608
mul v6318 v6219
add v6317 v6319
mul v6303 v6221
add v6320 v6321
add v6316 v6091
sub v6323 v6322
shr v6324 v6087
land v6325 v6103
mul v6195 v5777
mul v6215 v6064
add v6327 v6328
mul v6046 v6217
mul v6318 v6221
add v6330 v6331
add v6329 v6091
sub v6333 v6332
shr v6334 v6087
land v6335 v6103
shr v6079 v6086
land v6337 1
sub 1 v6338
shl 1 v6086
sub v6340 1
land v6079 v6341
add v6339 v6342
sub 1 v6236
add v6343 v6344
add v6074 v6345
mul v6094 v5815
sub v5949 v6347
sub v6347 v5949
add v6348 v6349
land v5949 18446744073709551615
gcd v6351 v771
mul v6352 157587932685088877
land v6353 18446744073709551615
shr v6354 58
shl v6355 3
shr x26 v6356
land v6357 255
shl v6358 1
add 45991 v6359
shl 1 v6360
sub v6361 1
shl v6361 2
sub v6361 v5815
sub v6361 v6102
shr v6236 41155
mul v6366 v6365
add v6236 v6367
mul v6099 v6364
add v5964 v6369
shr v6251 41155
mul v6371 v6365
add v6251 v6372
shl 1 45991
sub v6374 1
shr v6350 v6358
land v6376 v798
mul v6377 v6376
land v6378 v798
sub v802 v6379
mul v6376 v6380
land v6381 v798
land v6376 v807
mul v6383 v6382
land v6384 v807
sub v811 v6385
mul v6382 v6386
land v6387 v807
land v6376 v816
mul v6389 v6388
land v6390 v816
sub v820 v6391
mul v6388 v6392
land v6393 v816
land v6376 v825
mul v6395 v6394
land v6396 v825
sub v829 v6397
mul v6394 v6398
land v6399 v825
land v6376 v834
mul v6401 v6400
land v6402 v834
sub v838 v6403
mul v6400 v6404
land v6405 v834
land v6376 v843
mul v6407 v6406
land v6408 v843
sub v847 v6409
mul v6406 v6410
land v6411 v843
land v6376 v852
mul v6413 v6412
land v6414 v852
sub v856 v6415
mul v6412 v6416
land v6417 v852
land v6376 v861
mul v6419 v6418
land v6420 v861
sub v865 v6421
mul v6418 v6422
land v6423 v861
land v6376 v870
mul v6425 v6424
land v6426 v870
sub v874 v6427
mul v6424 v6428
land v6429 v870
land v6376 v879
mul v6431 v6430
land v6432 v879
sub v883 v6433
mul v6430 v6434
land v6435 v879
land v6376 v2235
mul v6437 v6436
land v6438 v2235
sub v2239 v6439
mul v6436 v6440
land v6441 v2235
land v6376 v3474
mul v6443 v6442
land v6444 v3474
sub v3478 v6445
mul v6442 v6446
land v6447 v3474
land v6376 v4937
mul v6449 v6448
land v6450 v4937
sub v4941 v6451
mul v6448 v6452
land v6453 v4937
shl 1 46119
sub v6455 1
land v6376 v6456
mul v6457 v6454
land v6458 v6456
add v6456 3
sub v6460 v6459
mul v6454 v6461
land v6462 v6456
mul v6368 v6463
land v6464 v6362
mul v6465 v6465
land v6466 v6362
shl v6465 v6358
land v6468 v6362
mul v6094 v6469
sub 1 v6094
sub v6361 v6469
mul v6471 v6472
add v6470 v6473
shl v6373 v6358
land v6475 v6362
mul v6471 v6476
sub 1 v6471
sub v6361 v6476
mul v6478 v6479
add v6477 v6480
add v6481 v6361
mul v6370 v6465
land v6483 v6362
sub v6482 v6484
mul v6485 v6463
land v6486 v6362
shl v6467 36609
land v6488 v6362
shl v6474 41156
land v6490 v6362
shl v6487 41156
land v6492 v6362
mul v6467 v5979
mul v6474 v6266
add v6494 v6495
mul v6487 v6251
add v6496 v6497
mul v6228 v6489
shr v6266 41155
mul v6500 v6491
add v6499 v6501
mul v6371 v6493
add v6502 v6503
add v6498 v6363
sub v6505 v6504
shr v6506 v6359
land v6507 v6375
mul v6467 v5994
mul v6474 v6281
add v6509 v6510
mul v6487 v6266
add v6511 v6512
mul v6243 v6489
shr v6281 41155
mul v6515 v6491
add v6514 v6516
mul v6500 v6493
add v6517 v6518
add v6513 v6363
sub v6520 v6519
shr v6521 v6359
land v6522 v6375
mul v6467 v6009
mul v6474 v6296
add v6524 v6525
mul v6487 v6281
add v6526 v6527
mul v6258 v6489
shr v6296 41155
mul v6530 v6491
add v6529 v6531
mul v6515 v6493
add v6532 v6533
add v6528 v6363
sub v6535 v6534
shr v6536 v6359
land v6537 v6375
mul v6467 v6024
mul v6474 v6311
add v6539 v6540
mul v6487 v6296
add v6541 v6542
mul v6273 v6489
shr v6311 41155
mul v6545 v6491
add v6544 v6546
mul v6530 v6493
add v6547 v6548
add v6543 v6363
sub v6550 v6549
shr v6551 v6359
land v6552 v6375
mul v6467 v6039
mul v6474 v6326
add v6554 v6555
mul v6487 v6311
add v6556 v6557
mul v6288 v6489
shr v6326 41155
mul v6560 v6491
add v6559 v6561
mul v6545 v6493
add v6562 v6563
add v6558 v6363
sub v6565 v6564
shr v6566 v6359
land v6567 v6375
mul v6467 v6054
mul v6474 v6336
add v6569 v6570
mul v6487 v6326
add v6571 v6572
mul v6303 v6489
shr v6336 41155
mul v6575 v6491
add v6574 v6576
mul v6560 v6493
add v6577 v6578
add v6573 v6363
sub v6580 v6579
shr v6581 v6359
land v6582 v6375
mul v6467 v6064
mul v6487 v6336
add v6584 v6585
mul v6318 v6489
mul v6575 v6493
add v6587 v6588
add v6586 v6363
sub v6590 v6589
shr v6591 v6359
land v6592 v6375
shr v6351 v6358
land v6594 1
sub 1 v6595
shl 1 v6358
sub v6597 1
land v6351 v6598
add v6596 v6599
sub 1 v6508
add v6600 v6601
add v6346 v6602
mul v6366 v6102
sub v6236 v6604
sub v6604 v6236
add v6605 v6606
land v6236 18446744073709551615
gcd v6608 v771
mul v6609 157587932685088877
land v6610 18446744073709551615
shr v6611 58
shl v6612 3
shr x26 v6613
land v6614 255
shl v6615 1
add 51115 v6616
shl 1 v6617
sub v6618 1
shl v6618 2
sub v6618 v6102
sub v6618 v6374
shr v6508 45990
mul v6623 v6622
add v6508 v6624
mul v6371 v6621
add v6251 v6626
shr v6523 45990
mul v6628 v6622
add v6523 v6629
shl 1 51115
sub v6631 1
shr v6607 v6615
land v6633 v798
mul v6634 v6633
land v6635 v798
sub v802 v6636
mul v6633 v6637
land v6638 v798
land v6633 v807
mul v6640 v6639
land v6641 v807
sub v811 v6642
mul v6639 v6643
land v6644 v807
land v6633 v816
mul v6646 v6645
land v6647 v816
sub v820 v6648
mul v6645 v6649
land v6650 v816
land v6633 v825
mul v6652 v6651
land v6653 v825
sub v829 v6654
mul v6651 v6655
land v6656 v825
land v6633 v834
mul v6658 v6657
land v6659 v834
sub v838 v6660
mul v6657 v6661
land v6662 v834
land v6633 v843
mul v6664 v6663
land v6665 v843
sub v847 v6666
mul v6663 v6667
land v6668 v843
land v6633 v852
mul v6670 v6669
land v6671 v852
sub v856 v6672
mul v6669 v6673
land v6674 v852
land v6633 v861
mul v6676 v6675
land v6677 v861
sub v865 v6678
mul v6675 v6679
land v6680 v861
land v6633 v870
mul v6682 v6681
land v6683 v870
sub v874 v6684
mul v6681 v6685
land v6686 v870
land v6633 v879
mul v6688 v6687
land v6689 v879
sub v883 v6690
mul v6687 v6691
land v6692 v879
land v6633 v2235
mul v6694 v6693
land v6695 v2235
sub v2239 v6696
mul v6693 v6697
land v6698 v2235
land v6633 v3474
mul v6700 v6699
land v6701 v3474
sub v3478 v6702
mul v6699 v6703
land v6704 v3474
land v6633 v4937
mul v6706 v6705
land v6707 v4937
sub v4941 v6708
mul v6705 v6709
land v6710 v4937
shl 1 49152
sub v6712 1
land v6633 v6713
mul v6714 v6711
land v6715 v6713
add v6713 3
sub v6717 v6716
mul v6711 v6718
land v6719 v6713
shl 1 51243
sub v6721 1
land v6633 v6722
mul v6723 v6720
land v6724 v6722
add v6722 3
sub v6726 v6725
mul v6720 v6727
land v6728 v6722
mul v6625 v6729
land v6730 v6619
mul v6731 v6731
land v6732 v6619
shl v6731 v6615
land v6734 v6619
mul v6366 v6735
sub 1 v6366
sub v6618 v6735
mul v6737 v6738
add v6736 v6739
shl v6630 v6615
land v6741 v6619
mul v6737 v6742
sub 1 v6737
sub v6618 v6742
mul v6744 v6745
add v6743 v6746
add v6747 v6618
mul v6627 v6731
land v6749 v6619
sub v6748 v6750
mul v6751 v6729
land v6752 v6619
shl v6733 41156
land v6754 v6619
shl v6740 45991
land v6756 v6619
shl v6753 45991
land v6758 v6619
mul v6733 v6266
mul v6740 v6538
add v6760 v6761
mul v6753 v6523
add v6762 v6763
mul v6500 v6755
shr v6538 45990
mul v6766 v6757
add v6765 v6767
mul v6628 v6759
add v6768 v6769
add v6764 v6620
sub v6771 v6770
shr v6772 v6616
land v6773 v6632
mul v6733 v6281
mul v6740 v6553
add v6775 v6776
mul v6753 v6538
add v6777 v6778
mul v6515 v6755
shr v6553 45990
mul v6781 v6757
add v6780 v6782
mul v6766 v6759
add v6783 v6784
add v6779 v6620
sub v6786 v6785
shr v6787 v6616
land v6788 v6632
mul v6733 v6296
mul v6740 v6568
add v6790 v6791
mul v6753 v6553
add v6792 v6793
mul v6530 v6755
shr v6568 45990
mul v6796 v6757
add v6795 v6797
mul v6781 v6759
add v6798 v6799
add v6794 v6620
sub v6801 v6800
shr v6802 v6616
land v6803 v6632
mul v6733 v6311
mul v6740 v6583
add v6805 v6806
mul v6753 v6568
add v6807 v6808
mul v6545 v6755
shr v6583 45990
mul v6811 v6757
add v6810 v6812
mul v6796 v6759
add v6813 v6814
add v6809 v6620
sub v6816 v6815
shr v6817 v6616
land v6818 v6632
mul v6733 v6326
mul v6740 v6593
add v6820 v6821
mul v6753 v6583
add v6822 v6823
mul v6560 v6755
shr v6593 45990
mul v6826 v6757
add v6825 v6827
mul v6811 v6759
add v6828 v6829
add v6824 v6620
sub v6831 v6830
shr v6832 v6616
land v6833 v6632
mul v6733 v6336
mul v6753 v6593
add v6835 v6836
mul v6575 v6755
mul v6826 v6759
add v6838 v6839
add v6837 v6620
sub v6841 v6840
shr v6842 v6616
land v6843 v6632
shr v6608 v6615
land v6845 1
sub 1 v6846
shl 1 v6615
sub v6848 1
land v6608 v6849
add v6847 v6850
sub 1 v6774
add v6851 v6852
add v6603 v6853
mul v6623 v6374
sub v6508 v6855
sub v6855 v6508
add v6856 v6857
land v6508 18446744073709551615
gcd v6859 v771
mul v6860 157587932685088877
land v6861 18446744073709551615
shr v6862 58
shl v6863 3
shr x26 v6864
land v6865 255
shl v6866 1
add 56524 v6867
shl 1 v6868
sub v6869 1
shl v6869 2
sub v6869 v6374
sub v6869 v6631
shr v6774 51114
mul v6874 v6873
add v6774 v6875
mul v6628 v6872
add v6523 v6877
shr v6789 51114
mul v6879 v6873
add v6789 v6880
shl 1 56524
sub v6882 1
shr v6858 v6866
land v6884 v798
mul v6885 v6884
land v6886 v798
sub v802 v6887
mul v6884 v6888
land v6889 v798
land v6884 v807
mul v6891 v6890
land v6892 v807
sub v811 v6893
mul v6890 v6894
land v6895 v807
land v6884 v816
mul v6897 v6896
land v6898 v816
sub v820 v6899
mul v6896 v6900
land v6901 v816
land v6884 v825
mul v6903 v6902
land v6904 v825
sub v829 v6905
mul v6902 v6906
land v6907 v825
land v6884 v834
mul v6909 v6908
land v6910 v834
sub v838 v6911
mul v6908 v6912
land v6913 v834
land v6884 v843
mul v6915 v6914
land v6916 v843
sub v847 v6917
mul v6914 v6918
land v6919 v843
land v6884 v852
mul v6921 v6920
land v6922 v852
sub v856 v6923
mul v6920 v6924
land v6925 v852
land v6884 v861
mul v6927 v6926
land v6928 v861
sub v865 v6929
mul v6926 v6930
land v6931 v861
land v6884 v870
mul v6933 v6932
land v6934 v870
sub v874 v6935
mul v6932 v6936
land v6937 v870
land v6884 v879
mul v6939 v6938
land v6940 v879
sub v883 v6941
mul v6938 v6942
land v6943 v879
land v6884 v2235
mul v6945 v6944
land v6946 v2235
sub v2239 v6947
mul v6944 v6948
land v6949 v2235
land v6884 v3474
mul v6951 v6950
land v6952 v3474
sub v3478 v6953
mul v6950 v6954
land v6955 v3474
land v6884 v4937
mul v6957 v6956
land v6958 v4937
sub v4941 v6959
mul v6956 v6960
land v6961 v4937
land v6884 v6713
mul v6963 v6962
land v6964 v6713
sub v6717 v6965
mul v6962 v6966
land v6967 v6713
shl 1 56652
sub v6969 1
land v6884 v6970
mul v6971 v6968
land v6972 v6970
add v6970 3
sub v6974 v6973
mul v6968 v6975
land v6976 v6970
mul v6876 v6977
land v6978 v6870
mul v6979 v6979
land v6980 v6870
shl v6979 v6866
land v6982 v6870
mul v6623 v6983
sub 1 v6623
sub v6869 v6983
mul v6985 v6986
add v6984 v6987
shl v6881 v6866
land v6989 v6870
mul v6985 v6990
sub 1 v6985
sub v6869 v6990
mul v6992 v6993
add v6991 v6994
add v6995 v6869
mul v6878 v6979
land v6997 v6870
sub v6996 v6998
mul v6999 v6977
land v7000 v6870
shl v6981 45991
land v7002 v6870
shl v6988 51115
land v7004 v6870
shl v7001 51115
land v7006 v6870
mul v6981 v6538
mul v6988 v6804
add v7008 v7009
mul v7001 v6789
add v7010 v7011
mul v6766 v7003
shr v6804 51114
mul v7014 v7005
add v7013 v7015
mul v6879 v7007
add v7016 v7017
add v7012 v6871
sub v7019 v7018
shr v7020 v6867
land v7021 v6883
mul v6981 v6553
mul v6988 v6819
add v7023 v7024
mul v7001 v6804
add v7025 v7026
mul v6781 v7003
shr v6819 51114
mul v7029 v7005
add v7028 v7030
mul v7014 v7007
add v7031 v7032
add v7027 v6871
sub v7034 v7033
shr v7035 v6867
land v7036 v6883
mul v6981 v6568
mul v6988 v6834
add v7038 v7039
mul v7001 v6819
add v7040 v7041
mul v6796 v7003
shr v6834 51114
mul v7044 v7005
add v7043 v7045
mul v7029 v7007
add v7046 v7047
add v7042 v6871
sub v7049 v7048
shr v7050 v6867
land v7051 v6883
mul v6981 v6583
mul v6988 v6844
add v7053 v7054
mul v7001 v6834
add v7055 v7056
mul v6811 v7003
shr v6844 51114
mul v7059 v7005
add v7058 v7060
mul v7044 v7007
add v7061 v7062
add v7057 v6871
sub v7064 v7063
shr v7065 v6867
land v7066 v6883
mul v6981 v6593
mul v7001 v6844
add v7068 v7069
mul v6826 v7003
mul v7059 v7007
add v7071 v7072
add v7070 v6871
sub v7074 v7073
shr v7075 v6867
land v7076 v6883
shr v6859 v6866
land v7078 1
sub 1 v7079
shl 1 v6866
sub v7081 1
land v6859 v7082
add v7080 v7083
sub 1 v7022
add v7084 v7085
add v6854 v7086
mul v6874 v6631
sub v6774 v7088
sub v7088 v6774
add v7089 v7090
land v6774 18446744073709551615
gcd v7092 v771
mul v7093 157587932685088877
land v7094 18446744073709551615
shr v7095 58
shl v7096 3
shr x26 v7097
land v7098 255
shl v7099 1
add 62222 v7100
shl 1 v7101
sub v7102 1
shl v7102 2
sub v7102 v6631
sub v7102 v6882
shr v7022 56523
mul v7107 v7106
add v7022 v7108
mul v6879 v7105
add v6789 v7110
shr v7037 56523
mul v7112 v7106
add v7037 v7113
shl 1 62222
sub v7115 1
shr v7091 v7099
land v7117 v798
mul v7118 v7117
land v7119 v798
sub v802 v7120
mul v7117 v7121
land v7122 v798
land v7117 v807
mul v7124 v7123
land v7125 v807
sub v811 v7126
mul v7123 v7127
land v7128 v807
land v7117 v816
mul v7130 v7129
land v7131 v816
sub v820 v7132
mul v7129 v7133
land v7134 v816
land v7117 v825
mul v7136 v7135
land v7137 v825
sub v829 v7138
mul v7135 v7139
land v7140 v825
land v7117 v834
mul v7142 v7141
land v7143 v834
sub v838 v7144
mul v7141 v7145
land v7146 v834
land v7117 v843
mul v7148 v7147
land v7149 v843
sub v847 v7150
mul v7147 v7151
land v7152 v843
land v7117 v852
mul v7154 v7153
land v7155 v852
sub v856 v7156
mul v7153 v7157
land v7158 v852
land v7117 v861
mul v7160 v7159
land v7161 v861
sub v865 v7162
mul v7159 v7163
land v7164 v861
land v7117 v870
mul v7166 v7165
land v7167 v870
sub v874 v7168
mul v7165 v7169
land v7170 v870
land v7117 v879
mul v7172 v7171
land v7173 v879
sub v883 v7174
mul v7171 v7175
land v7176 v879
land v7117 v2235
mul v7178 v7177
land v7179 v2235
sub v2239 v7180
mul v7177 v7181
land v7182 v2235
land v7117 v3474
mul v7184 v7183
land v7185 v3474
sub v3478 v7186
mul v7183 v7187
land v7188 v3474
land v7117 v4937
mul v7190 v7189
land v7191 v4937
sub v4941 v7192
mul v7189 v7193
land v7194 v4937
land v7117 v6713
mul v7196 v7195
land v7197 v6713
sub v6717 v7198
mul v7195 v7199
land v7200 v6713
shl 1 62350
sub v7202 1
land v7117 v7203
mul v7204 v7201
land v7205 v7203
add v7203 3
sub v7207 v7206
mul v7201 v7208
land v7209 v7203
mul v7109 v7210
land v7211 v7103
mul v7212 v7212
land v7213 v7103
shl v7212 v7099
land v7215 v7103
mul v6874 v7216
sub 1 v6874
sub v7102 v7216
mul v7218 v7219
add v7217 v7220
shl v7114 v7099
land v7222 v7103
mul v7218 v7223
sub 1 v7218
sub v7102 v7223
mul v7225 v7226
add v7224 v7227
add v7228 v7102
mul v7111 v7212
land v7230 v7103
sub v7229 v7231
mul v7232 v7210
land v7233 v7103
shl v7214 51115
land v7235 v7103
shl v7221 56524
land v7237 v7103
shl v7234 56524
land v7239 v7103
mul v7214 v6804
mul v7221 v7052
add v7241 v7242
mul v7234 v7037
add v7243 v7244
mul v7014 v7236
shr v7052 56523
mul v7247 v7238
add v7246 v7248
mul v7112 v7240
add v7249 v7250
add v7245 v7104
sub v7252 v7251
shr v7253 v7100
land v7254 v7116
mul v7214 v6819
mul v7221 v7067
add v7256 v7257
mul v7234 v7052
add v7258 v7259
mul v7029 v7236
shr v7067 56523
mul v7262 v7238
add v7261 v7263
mul v7247 v7240
add v7264 v7265
add v7260 v7104
sub v7267 v7266
shr v7268 v7100
land v7269 v7116
mul v7214 v6834
mul v7221 v7077
add v7271 v7272
mul v7234 v7067
add v7273 v7274
mul v7044 v7236
shr v7077 56523
mul v7277 v7238
add v7276 v7278
mul v7262 v7240
add v7279 v7280
add v7275 v7104
sub v7282 v7281
shr v7283 v7100
land v7284 v7116
mul v7214 v6844
mul v7234 v7077
add v7286 v7287
mul v7059 v7236
mul v7277 v7240
add v7289 v7290
add v7288 v7104
sub v7292 v7291
shr v7293 v7100
land v7294 v7116
shr v7092 v7099
land v7296 1
sub 1 v7297
shl 1 v7099
sub v7299 1
land v7092 v7300
add v7298 v7301
sub 1 v7255
add v7302 v7303
add v7087 v7304
mul v7107 v6882
sub v7022 v7306
sub v7306 v7022
add v7307 v7308
land v7022 18446744073709551615
gcd v7310 v771
mul v7311 157587932685088877
land v7312 18446744073709551615
shr v7313 58
shl v7314 3
shr x26 v7315
land v7316 255
shl v7317 1
add 68205 v7318
shl 1 v7319
sub v7320 1
shl v7320 2
sub v7320 v6882
sub v7320 v7115
shr v7255 62221
mul v7325 v7324
add v7255 v7326
mul v7112 v7323
add v7037 v7328
shr v7270 62221
mul v7330 v7324
add v7270 v7331
shl 1 68205
sub v7333 1
shr v7309 v7317
land v7335 v798
mul v7336 v7335
land v7337 v798
sub v802 v7338
mul v7335 v7339
land v7340 v798
land v7335 v807
mul v7342 v7341
land v7343 v807
sub v811 v7344
mul v7341 v7345
land v7346 v807
land v7335 v816
mul v7348 v7347
land v7349 v816
sub v820 v7350
mul v7347 v7351
land v7352 v816
land v7335 v825
mul v7354 v7353
land v7355 v825
sub v829 v7356
mul v7353 v7357
land v7358 v825
land v7335 v834
mul v7360 v7359
land v7361 v834
sub v838 v7362
mul v7359 v7363
land v7364 v834
land v7335 v843
mul v7366 v7365
land v7367 v843
sub v847 v7368
mul v7365 v7369
land v7370 v843
land v7335 v852
mul v7372 v7371
land v7373 v852
sub v856 v7374
mul v7371 v7375
land v7376 v852
land v7335 v861
mul v7378 v7377
land v7379 v861
sub v865 v7380
mul v7377 v7381
land v7382 v861
land v7335 v870
mul v7384 v7383
land v7385 v870
sub v874 v7386
mul v7383 v7387
land v7388 v870
land v7335 v879
mul v7390 v7389
land v7391 v879
sub v883 v7392
mul v7389 v7393
land v7394 v879
land v7335 v2235
mul v7396 v7395
land v7397 v2235
sub v2239 v7398
mul v7395 v7399
land v7400 v2235
land v7335 v3474
mul v7402 v7401
land v7403 v3474
sub v3478 v7404
mul v7401 v7405
land v7406 v3474
land v7335 v4937
mul v7408 v7407
land v7409 v4937
sub v4941 v7410
mul v7407 v7411
land v7412 v4937
land v7335 v6713
mul v7414 v7413
land v7415 v6713
sub v6717 v7416
mul v7413 v7417
land v7418 v6713
shl 1 68333
sub v7420 1
land v7335 v7421
mul v7422 v7419
land v7423 v7421
add v7421 3
sub v7425 v7424
mul v7419 v7426
land v7427 v7421
mul v7327 v7428
land v7429 v7321
mul v7430 v7430
land v7431 v7321
shl v7430 v7317
land v7433 v7321
mul v7107 v7434
sub 1 v7107
sub v7320 v7434
mul v7436 v7437
add v7435 v7438
shl v7332 v7317
land v7440 v7321
mul v7436 v7441
sub 1 v7436
sub v7320 v7441
mul v7443 v7444
add v7442 v7445
add v7446 v7320
mul v7329 v7430
land v7448 v7321
sub v7447 v7449
mul v7450 v7428
land v7451 v7321
shl v7432 56524
land v7453 v7321
shl v7439 62222
land v7455 v7321
shl v7452 62222
land v7457 v7321
mul v7432 v7052
mul v7439 v7285
add v7459 v7460
mul v7452 v7270
add v7461 v7462
mul v7247 v7454
shr v7285 62221
mul v7465 v7456
add v7464 v7466
mul v7330 v7458
add v7467 v7468
add v7463 v7322
sub v7470 v7469
shr v7471 v7318
land v7472 v7334
mul v7432 v7067
mul v7439 v7295
add v7474 v7475
mul v7452 v7285
add v7476 v7477
mul v7262 v7454
shr v7295 62221
mul v7480 v7456
add v7479 v7481
mul v7465 v7458
add v7482 v7483
add v7478 v7322
sub v7485 v7484
shr v7486 v7318
land v7487 v7334
mul v7432 v7077
mul v7452 v7295
add v7489 v7490
mul v7277 v7454
mul v7480 v7458
add v7492 v7493
add v7491 v7322
sub v7495 v7494
shr v7496 v7318
land v7497 v7334
shr v7310 v7317
land v7499 1
sub 1 v7500
shl 1 v7317
sub v7502 1
land v7310 v7503
add v7501 v7504
sub 1 v7473
add v7505 v7506
add v7305 v7507
mul v7325 v7115
sub v7255 v7509
sub v7509 v7255
add v7510 v7511
land v7255 18446744073709551615
gcd v7513 v771
mul v7514 157587932685088877
land v7515 18446744073709551615
shr v7516 58
shl v7517 3
shr x26 v7518
land v7519 255
shl v7520 1
add 74473 v7521
shl 1 v7522
sub v7523 1
shl v7523 2
sub v7523 v7115
sub v7523 v7333
shr v7473 68204
mul v7528 v7527
add v7473 v7529
mul v7330 v7526
add v7270 v7531
shr v7488 68204
mul v7533 v7527
add v7488 v7534
shl 1 74473
sub v7536 1
shr v7512 v7520
land v7538 v798
mul v7539 v7538
land v7540 v798
sub v802 v7541
mul v7538 v7542
land v7543 v798
land v7538 v807
mul v7545 v7544
land v7546 v807
sub v811 v7547
mul v7544 v7548
land v7549 v807
land v7538 v816
mul v7551 v7550
land v7552 v816
sub v820 v7553
mul v7550 v7554
land v7555 v816
land v7538 v825
mul v7557 v7556
land v7558 v825
sub v829 v7559
mul v7556 v7560
land v7561 v825
land v7538 v834
mul v7563 v7562
land v7564 v834
sub v838 v7565
mul v7562 v7566
land v7567 v834
land v7538 v843
mul v7569 v7568
land v7570 v843
sub v847 v7571
mul v7568 v7572
land v7573 v843
land v7538 v852
mul v7575 v7574
land v7576 v852
sub v856 v7577
mul v7574 v7578
land v7579 v852
land v7538 v861
mul v7581 v7580
land v7582 v861
sub v865 v7583
mul v7580 v7584
land v7585 v861
land v7538 v870
mul v7587 v7586
land v7588 v870
sub v874 v7589
mul v7586 v7590
land v7591 v870
land v7538 v879
mul v7593 v7592
land v7594 v879
sub v883 v7595
mul v7592 v7596
land v7597 v879
land v7538 v2235
mul v7599 v7598
land v7600 v2235
sub v2239 v7601
mul v7598 v7602
land v7603 v2235
land v7538 v3474
mul v7605 v7604
land v7606 v3474
sub v3478 v7607
mul v7604 v7608
land v7609 v3474
land v7538 v4937
mul v7611 v7610
land v7612 v4937
sub v4941 v7613
mul v7610 v7614
land v7615 v4937
land v7538 v6713
mul v7617 v7616
land v7618 v6713
sub v6717 v7619
mul v7616 v7620
land v7621 v6713
shl 1 74601
sub v7623 1
land v7538 v7624
mul v7625 v7622
land v7626 v7624
add v7624 3
sub v7628 v7627
mul v7622 v7629
land v7630 v7624
mul v7530 v7631
land v7632 v7524
mul v7633 v7633
land v7634 v7524
shl v7633 v7520
land v7636 v7524
mul v7325 v7637
sub 1 v7325
sub v7523 v7637
mul v7639 v7640
add v7638 v7641
shl v7535 v7520
land v7643 v7524
mul v7639 v7644
sub 1 v7639
sub v7523 v7644
mul v7646 v7647
add v7645 v7648
add v7649 v7523
mul v7532 v7633
land v7651 v7524
sub v7650 v7652
mul v7653 v7631
land v7654 v7524
shl v7635 62222
land v7656 v7524
shl v7642 68205
land v7658 v7524
shl v7655 68205
land v7660 v7524
mul v7635 v7285
mul v7642 v7498
add v7662 v7663
mul v7655 v7488
add v7664 v7665
mul v7465 v7657
shr v7498 68204
mul v7668 v7659
add v7667 v7669
mul v7533 v7661
add v7670 v7671
add v7666 v7525
sub v7673 v7672
shr v7674 v7521
land v7675 v7537
mul v7635 v7295
mul v7655 v7498
add v7677 v7678
mul v7480 v7657
mul v7668 v7661
add v7680 v7681
add v7679 v7525
sub v7683 v7682
shr v7684 v7521
land v7685 v7537
shr v7513 v7520
land v7687 1
sub 1 v7688
shl 1 v7520
sub v7690 1
land v7513 v7691
add v7689 v7692
sub 1 v7676
add v7693 v7694
add v7508 v7695
mul v7528 v7333
sub v7473 v7697
sub v7697 v7473
add v7698 v7699
land v7473 18446744073709551615
gcd v7701 v771
mul v7702 157587932685088877
land v7703 18446744073709551615
shr v7704 58
shl v7705 3
shr x26 v7706
land v7707 255
shl v7708 1
add 81025 v7709
shl 1 v7710
sub v7711 1
shl v7711 2
sub v7711 v7333
sub v7711 v7536
shr v7676 74472
mul v7716 v7715
add v7676 v7717
mul v7533 v7714
add v7488 v7719
shr v7686 74472
mul v7721 v7715
add v7686 v7722
shl 1 81025
sub v7724 1
shr v7700 v7708
land v7726 v798
mul v7727 v7726
land v7728 v798
sub v802 v7729
mul v7726 v7730
land v7731 v798
land v7726 v807
mul v7733 v7732
land v7734 v807
sub v811 v7735
mul v7732 v7736
land v7737 v807
land v7726 v816
mul v7739 v7738
land v7740 v816
sub v820 v7741
mul v7738 v7742
land v7743 v816
land v7726 v825
mul v7745 v7744
land v7746 v825
sub v829 v7747
mul v7744 v7748
land v7749 v825
land v7726 v834
mul v7751 v7750
land v7752 v834
sub v838 v7753
mul v7750 v7754
land v7755 v834
land v7726 v843
mul v7757 v7756
land v7758 v843
sub v847 v7759
mul v7756 v7760
land v7761 v843
land v7726 v852
mul v7763 v7762
land v7764 v852
sub v856 v7765
mul v7762 v7766
land v7767 v852
land v7726 v861
mul v7769 v7768
land v7770 v861
sub v865 v7771
mul v7768 v7772
land v7773 v861
land v7726 v870
mul v7775 v7774
land v7776 v870
sub v874 v7777
mul v7774 v7778
land v7779 v870
land v7726 v879
mul v7781 v7780
land v7782 v879
sub v883 v7783
mul v7780 v7784
land v7785 v879
land v7726 v2235
mul v7787 v7786
land v7788 v2235
sub v2239 v7789
mul v7786 v7790
land v7791 v2235
land v7726 v3474
mul v7793 v7792
land v7794 v3474
sub v3478 v7795
mul v7792 v7796
land v7797 v3474
land v7726 v4937
mul v7799 v7798
land v7800 v4937
sub v4941 v7801
mul v7798 v7802
land v7803 v4937
land v7726 v6713
mul v7805 v7804
land v7806 v6713
sub v6717 v7807
mul v7804 v7808
land v7809 v6713
shl 1 81153
sub v7811 1
land v7726 v7812
mul v7813 v7810
land v7814 v7812
add v7812 3
sub v7816 v7815
mul v7810 v7817
land v7818 v7812
mul v7718 v7819
land v7820 v7712
mul v7821 v7821
land v7822 v7712
shl v7821 v7708
land v7824 v7712
mul v7528 v7825
sub 1 v7528
sub v7711 v7825
mul v7827 v7828
add v7826 v7829
shl v7723 v7708
land v7831 v7712
mul v7827 v7832
sub 1 v7827
sub v7711 v7832
mul v7834 v7835
add v7833 v7836
add v7837 v7711
mul v7720 v7821
land v7839 v7712
sub v7838 v7840
mul v7841 v7819
land v7842 v7712
shl v7823 68205
land v7844 v7712
shl v7830 74473
land v7846 v7712
shl v7843 74473
land v7848 v7712
mul v7823 v7498
mul v7843 v7686
add v7850 v7851
mul v7668 v7845
mul v7721 v7849
add v7853 v7854
add v7852 v7713
sub v7856 v7855
shr v7857 v7709
land v7858 v7725
shr v7701 v7708
land v7860 1
sub 1 v7861
shl 1 v7708
sub v7863 1
land v7701 v7864
add v7862 v7865
sub 1 v7859
add v7866 v7867
add v7696 v7868
shr v7859 81024
mul v7870 v7724
sub v7859 v7871
sub v7871 v7859
add v7872 v7873
shl v7874 1
add v7875 v7870
app x25 v7876 v7869" [f0, f1, f2, f3, f4, f5, f6, f7, f8, f9, f10, f11, f12, f13, f14, f15, f16, f17, f18, f19, f20, f21, f22, f23, f24, (@Prod.mk Nat Nat), dbTab]

def LowDagEq : Prop := ∀ f0 f1 f2 f3 f4 f5 f6 f7 f8 f9 f10 f11 f12 f13 f14 f15 f16 f17 f18 f19 f20 f21 f22 f23 f24 : Nat, lowDag f0 f1 f2 f3 f4 f5 f6 f7 f8 f9 f10 f11 f12 f13 f14 f15 f16 f17 f18 f19 f20 f21 f22 f23 f24 = lowRun [f0, f1, f2, f3, f4, f5, f6, f7, f8, f9, f10, f11, f12, f13, f14, f15, f16, f17, f18, f19, f20, f21, f22, f23, f24]

open Lean Elab Term Command Meta in
run_cmd liftTermElabM do
  let ty ← instantiateMVars (← elabTerm (← `(LowDagEq)) none)
  let pf ← instantiateMVars (← elabTerm (← `(fun (f0 f1 f2 f3 f4 f5 f6 f7 f8 f9 f10 f11 f12 f13 f14 f15 f16 f17 f18 f19 f20 f21 f22 f23 f24 : Nat) => @rfl (Nat × Nat) (lowDag f0 f1 f2 f3 f4 f5 f6 f7 f8 f9 f10 f11 f12 f13 f14 f15 f16 f17 f18 f19 f20 f21 f22 f23 f24))) none)
  addDecl (.thmDecl { name := `V9.lowDag_eq, levelParams := [], type := ty, value := pf })

end V9

namespace Submission

/- The graphs are evaluated only by the kernel; the elaborator must not unfold them. -/
attribute [irreducible] pkDag15 pkDagC15 pkDag205 pkDagC205 prsDag kont V9.lowDag

/-! ## v8 entry point -/

/-- Read off the packed result unless a check failed (then the v7 path `fb`). -/
def finish8 (r : Nat × Nat) (fb : Int) : Int :=
  Nat.rec (motive := fun _ => Int) (zdec r.1) (fun _ _ => fb) r.2

/-- Band 15: the packed run, the v7 path as fallback. -/
def kont15 (n f0 f1 f2 f3 f4 f5 f6 f7 f8 f9 f10 f11 f12 f13 f14 f15 f16 f17 f18 f19 f20 f21 f22 f23 f24 : Nat) : Int := finish8 (pkDag15 f0 f1 f2 f3 f4 f5 f6 f7 f8 f9 f10 f11 f12 f13 f14 f15 f16 f17 f18 f19 f20 f21 f22 f23 f24) (kont n f0 f1 f2 f3 f4 f5 f6 f7 f8 f9 f10 f11 f12 f13 f14 f15 f16 f17 f18 f19 f20 f21 f22 f23 f24)
/-- Band 205: the packed prefix with v7 tail, the v7 path as fallback. -/
def kont205 (n f0 f1 f2 f3 f4 f5 f6 f7 f8 f9 f10 f11 f12 f13 f14 f15 f16 f17 f18 f19 f20 f21 f22 f23 f24 : Nat) : Int := finish8 (pkDag205 f0 f1 f2 f3 f4 f5 f6 f7 f8 f9 f10 f11 f12 f13 f14 f15 f16 f17 f18 f19 f20 f21 f22 f23 f24) (kont n f0 f1 f2 f3 f4 f5 f6 f7 f8 f9 f10 f11 f12 f13 f14 f15 f16 f17 f18 f19 f20 f21 f22 f23 f24)

/-- Band 3484: the low-part run (v9), the v7 path as fallback. -/
def kont3484 (n f0 f1 f2 f3 f4 f5 f6 f7 f8 f9 f10 f11 f12 f13 f14 f15 f16 f17 f18 f19 f20 f21 f22 f23 f24 : Nat) : Int := finish8 (V9.lowDag f0 f1 f2 f3 f4 f5 f6 f7 f8 f9 f10 f11 f12 f13 f14 f15 f16 f17 f18 f19 f20 f21 f22 f23 f24) (kont n f0 f1 f2 f3 f4 f5 f6 f7 f8 f9 f10 f11 f12 f13 f14 f15 f16 f17 f18 f19 f20 f21 f22 f23 f24)

/-- The band dispatch of v7 with the packed continuations for bands 15 and 205 and the low-part
run for band 3484. -/
def genFastC9 (n : Nat) : Int :=
  Nat.rec (motive := fun _ => Int) (genLane15C (lcgSeed n) (kont15 n))
    (fun _ _ => Nat.rec (motive := fun _ => Int) (genLane36C (lcgSeed n) (kont n))
      (fun _ _ => Nat.rec (motive := fun _ => Int) (genLane205C (lcgSeed n) (kont205 n))
        (fun _ _ => Nat.rec (motive := fun _ => Int) (genLane1001C (lcgSeed n) (kont n))
          (fun _ _ => genLane3484C (lcgSeed n) (kont3484 n)) (Nat.div n (nat_lit 72057594037927936)))
        (Nat.div n (nat_lit 70368744177664)))
      (Nat.div n (nat_lit 68719476736)))
    (Nat.div n (nat_lit 67108864))

def impl (n : Nat) : Int := genFastC9 n


/-! # v8 proofs -/


/-! ## Evaluation of digit lists -/

/-- Value of a high-to-low integer list at `B`. -/
def ev (B : Int) : List Int → Int
  | [] => 0
  | a :: as => a * B ^ as.length + ev B as

theorem ev_cons (B a : Int) (as : List Int) : ev B (a :: as) = a * B ^ as.length + ev B as := rfl

theorem ev_natAbs_lt (B : Nat) (hB : 0 < B) : ∀ l : List Int, (∀ x ∈ l, x.natAbs < B) →
    (ev B l).natAbs < B ^ l.length
  | [], _ => by simp [ev]
  | a :: as, h => by
    have ha : a.natAbs < B := h a (by simp)
    have ih := ev_natAbs_lt B hB as (fun x hx => h x (by simp [hx]))
    rw [ev_cons, List.length_cons]
    have h1 : (a * (B : Int) ^ as.length + ev B as).natAbs ≤ a.natAbs * B ^ as.length + (ev B as).natAbs := by
      have := Int.natAbs_add_le (a * (B : Int) ^ as.length) (ev B as)
      rw [Int.natAbs_mul, Int.natAbs_pow, Int.natAbs_natCast] at this
      exact this
    have h2 : a.natAbs * B ^ as.length ≤ (B - 1) * B ^ as.length := Nat.mul_le_mul_right _ (by omega)
    have h3 : (B - 1) * B ^ as.length + B ^ as.length = B ^ (as.length + 1) := by
      rw [Nat.pow_succ, Nat.sub_mul, Nat.one_mul, Nat.mul_comm]
      have : B ^ as.length ≤ B ^ as.length * B := Nat.le_mul_of_pos_right _ hB
      omega
    omega

theorem ev_eq_zero (B : Nat) (hB : 0 < B) : ∀ l : List Int, (∀ x ∈ l, x.natAbs < B) →
    ev B l = 0 → ∀ x ∈ l, x = 0
  | [], _, _ => by simp
  | a :: as, h, h0 => by
    have hlt := ev_natAbs_lt B hB as (fun x hx => h x (by simp [hx]))
    rw [ev_cons] at h0
    have ha : a = 0 := by
      by_cases hne : a = 0
      · exact hne
      exfalso
      have h1 : (a * (B : Int) ^ as.length).natAbs = (ev B as).natAbs := by
        rw [show a * (B : Int) ^ as.length = - ev B as by omega, Int.natAbs_neg]
      rw [Int.natAbs_mul, Int.natAbs_pow, Int.natAbs_natCast] at h1
      have : 1 ≤ a.natAbs := by omega
      have : B ^ as.length ≤ a.natAbs * B ^ as.length := Nat.le_mul_of_pos_left _ (by omega)
      omega
    subst ha
    have h0' : ev B as = 0 := by simpa using h0
    have ih := ev_eq_zero B hB as (fun x hx => h x (by simp [hx])) h0'
    intro x hx
    simp only [List.mem_cons] at hx
    rcases hx with rfl | hx
    · rfl
    · exact ih x hx

/-- Elementwise `n − k·q`. -/
def dlist (k : Int) : List Int → List Int → List Int
  | n :: ns, q :: qs => (n - k * q) :: dlist k ns qs
  | _, _ => []

theorem ev_dlist (B k : Int) : ∀ N Q : List Int, N.length = Q.length →
    ev B (dlist k N Q) = ev B N - k * ev B Q
  | [], [], _ => by simp [dlist, ev]
  | n :: ns, q :: qs, h => by
    simp only [List.length_cons, Nat.add_right_cancel_iff] at h
    have ih := ev_dlist B k ns qs h
    have hl : (dlist k ns qs).length = ns.length := by
      clear ih; induction ns generalizing qs with
      | nil => simp [dlist]
      | cons a as iha => cases qs with
        | nil => simp at h
        | cons b bs => simp [dlist, iha bs (by simpa using h)]
    simp only [dlist, ev_cons, ih, hl, ← h]
    grind
  | [], _ :: _, h => by simp at h
  | _ :: _, [], h => by simp at h

theorem dlist_zero (k : Int) : ∀ N Q : List Int, N.length = Q.length →
    (∀ x ∈ dlist k N Q, x = 0) → N = Q.map (fun q => k * q)
  | [], [], _, _ => rfl
  | n :: ns, q :: qs, h, h0 => by
    simp only [dlist, List.mem_cons, forall_eq_or_imp] at h0
    simp only [List.length_cons, Nat.add_right_cancel_iff] at h
    rw [List.map_cons, dlist_zero k ns qs h h0.2]
    congr 1; omega
  | [], _ :: _, h, _ => by simp at h
  | _ :: _, [], h, _ => by simp at h

/-- The E-argument: an integer combination that vanishes at `B` with all coefficients below `B`
in absolute value vanishes coefficientwise. -/
theorem eq_map_of_ev (B : Nat) (hB : 0 < B) (k : Int) (N Q : List Int) (hl : N.length = Q.length)
    (hb : ∀ x ∈ dlist k N Q, x.natAbs < B) (he : ev B N = k * ev B Q) : N = Q.map (fun q => k * q) := by
  apply dlist_zero k N Q hl
  apply ev_eq_zero B hB _ hb
  rw [ev_dlist _ _ _ _ hl]; omega


/-! ## Lanes and digits -/

/-- High-to-low digits in lns of width `W`. -/
def ofD (W : Nat) : List Nat → Nat
  | [] => 0
  | d :: ds => d * 2 ^ (W * ds.length) + ofD W ds

/-- Shift amounts `W·p, W·(p−1), …, 0`. -/
def lns (W : Nat) : Nat → List Nat
  | 0 => [0]
  | p + 1 => W * (p + 1) :: lns W p

/-- Shift amounts `W·p, …, W` (every digit but the last). -/
def lns1 (W : Nat) : Nat → List Nat
  | 0 => []
  | p + 1 => W * (p + 1) :: lns1 W p

theorem lanes_length (W : Nat) : ∀ p, (lns W p).length = p + 1
  | 0 => rfl
  | p + 1 => by simp [lns, lanes_length W p]

theorem ofD_lt (W : Nat) : ∀ ds : List Nat, (∀ d ∈ ds, d < 2 ^ W) → ofD W ds < 2 ^ (W * ds.length)
  | [], _ => by simp [ofD]
  | d :: ds, h => by
    have hd : d < 2 ^ W := h d (by simp)
    have ih := ofD_lt W ds (fun x hx => h x (by simp [hx]))
    simp only [ofD, List.length_cons]
    have h1 : d * 2 ^ (W * ds.length) ≤ (2 ^ W - 1) * 2 ^ (W * ds.length) := Nat.mul_le_mul_right _ (by omega)
    have h2 : 2 ^ (W * (ds.length + 1)) = 2 ^ W * 2 ^ (W * ds.length) := by
      rw [Nat.mul_add, Nat.mul_one, Nat.pow_add, Nat.mul_comm]
    rw [h2, Nat.sub_mul, Nat.one_mul] at *
    have h3 : 2 ^ (W * ds.length) ≤ 2 ^ W * 2 ^ (W * ds.length) :=
      Nat.le_mul_of_pos_left _ (Nat.two_pow_pos W)
    omega

theorem land_shr (u s W : Nat) : Nat.land (Nat.shiftRight u s) (2 ^ W - 1) = u / 2 ^ s % 2 ^ W := by
  rw [nand, nshr, Nat.and_two_pow_sub_one_eq_mod, Nat.shiftRight_eq_div_pow]

theorem digit_add_mul (W a r q n : Nat) (hq : q < n) :
    (a * 2 ^ (W * n) + r) / 2 ^ (W * q) % 2 ^ W = r / 2 ^ (W * q) % 2 ^ W := by
  have hx : W * n = W * (n - q - 1) + W + W * q := by
    rw [show W * (n - q - 1) + W + W * q = W * ((n - q - 1) + 1 + q) by
      rw [Nat.mul_add, Nat.mul_add, Nat.mul_one]]
    congr 1; omega
  have e : a * 2 ^ (W * n) = (a * 2 ^ (W * (n - q - 1)) * 2 ^ W) * 2 ^ (W * q) := by
    rw [hx, Nat.pow_add, Nat.pow_add]; simp only [Nat.mul_assoc]
  rw [e, Nat.add_comm, Nat.add_mul_div_right _ _ (Nat.two_pow_pos _), Nat.add_mul_mod_self_right]

theorem digit_top (W d r n : Nat) (hd : d < 2 ^ W) (hr : r < 2 ^ (W * n)) :
    (d * 2 ^ (W * n) + r) / 2 ^ (W * n) % 2 ^ W = d := by
  rw [Nat.add_comm, Nat.add_mul_div_right _ _ (Nat.two_pow_pos _), Nat.div_eq_of_lt hr, Nat.zero_add,
    Nat.mod_eq_of_lt hd]

theorem digit_mod (W u q n : Nat) (hq : q < n) :
    u / 2 ^ (W * q) % 2 ^ W = u % 2 ^ (W * n) / 2 ^ (W * q) % 2 ^ W := by
  conv => lhs; rw [← Nat.div_add_mod u (2 ^ (W * n)), Nat.mul_comm]
  exact digit_add_mul W _ _ q n hq

theorem digsU_add_mul (W a r n : Nat) : ∀ q, q < n →
    digsU (2 ^ W - 1) (a * 2 ^ (W * n) + r) (lns W q) = digsU (2 ^ W - 1) r (lns W q)
  | 0, h => by
    simp only [lns, digsU, land_shr]
    exact congrArg (· :: []) (digit_add_mul W a r 0 n h)
  | q + 1, h => by
    simp only [lns, digsU, land_shr]
    rw [digit_add_mul W a r (q + 1) n h, digsU_add_mul W a r n q (by omega)]

theorem digsU_mod (W u n : Nat) : ∀ q, q < n →
    digsU (2 ^ W - 1) u (lns W q) = digsU (2 ^ W - 1) (u % 2 ^ (W * n)) (lns W q) := by
  intro q hq
  conv => lhs; rw [← Nat.div_add_mod u (2 ^ (W * n)), Nat.mul_comm]
  exact digsU_add_mul W _ _ n q hq

theorem digsU_ofD (W : Nat) : ∀ ds : List Nat, (∀ d ∈ ds, d < 2 ^ W) → ∀ p, ds.length = p + 1 →
    digsU (2 ^ W - 1) (ofD W ds) (lns W p) = ds
  | [], _, p, h => by simp at h
  | d :: ds, h, p, hl => by
    simp only [List.length_cons, Nat.add_right_cancel_iff] at hl
    subst hl
    have hd : d < 2 ^ W := h d (by simp)
    have hr := ofD_lt W ds (fun x hx => h x (by simp [hx]))
    cases ds with
    | nil =>
      simp only [ofD, List.length_nil, Nat.mul_zero, Nat.pow_zero, Nat.mul_one, Nat.add_zero, lns, digsU,
        land_shr, Nat.div_one]
      rw [Nat.mod_eq_of_lt hd]
    | cons e es =>
      simp only [List.length_cons] at hr ⊢
      simp only [ofD, List.length_cons, lns, digsU, land_shr]
      rw [show ofD W (e :: es) = e * 2 ^ (W * es.length) + ofD W es from rfl] at hr
      have htop := digit_top W d (e * 2 ^ (W * es.length) + ofD W es) (es.length + 1) hd hr
      rw [htop, digsU_add_mul W d _ (es.length + 1) es.length (by omega)]
      have := digsU_ofD W (e :: es) (fun x hx => h x (List.mem_cons_of_mem d hx)) es.length (by simp)
      simp only [ofD] at this
      rw [this]

theorem ofD_digsU (W : Nat) : ∀ p u, u < 2 ^ (W * (p + 1)) →
    ofD W (digsU (2 ^ W - 1) u (lns W p)) = u ∧ (digsU (2 ^ W - 1) u (lns W p)).length = p + 1
  | 0, u, h => by
    simp only [lns, digsU, land_shr, Nat.mul_zero, Nat.pow_zero, Nat.div_one, ofD, List.length_cons,
      List.length_nil, Nat.mul_one, Nat.add_zero, Nat.zero_add] at h ⊢
    exact ⟨Nat.mod_eq_of_lt h, trivial⟩
  | p + 1, u, h => by
    have ih := ofD_digsU W p (u % 2 ^ (W * (p + 1))) (Nat.mod_lt _ (Nat.two_pow_pos _))
    simp only [lns, digsU, land_shr]
    rw [digsU_mod W u (p + 1) p (by omega)]
    refine ⟨?_, by simp [ih.2]⟩
    simp only [ofD, ih.2]
    rw [ih.1]
    have hq : u / 2 ^ (W * (p + 1)) < 2 ^ W := by
      rw [Nat.div_lt_iff_lt_mul (Nat.two_pow_pos _), ← Nat.pow_add]
      rw [show W + W * (p + 1) = W * (p + 1 + 1) by rw [Nat.mul_add W (p + 1) 1]; omega]
      exact h
    rw [Nat.mod_eq_of_lt hq, Nat.mul_comm]
    exact Nat.div_add_mod u _

theorem packL_ofD (W : Nat) : ∀ ds : List Nat, ∀ p, ds.length = p + 1 → packL ds (lns1 W p) = ofD W ds
  | [], _, h => by simp at h
  | [d], p, h => by
    simp at h; subst h; simp [packL, ofD]
  | d :: e :: ds, p, h => by
    simp only [List.length_cons] at h
    obtain ⟨q, rfl⟩ : ∃ q, p = q + 1 := ⟨p - 1, by omega⟩
    simp only [lns1, packL]
    rw [packL_ofD W (e :: ds) q (by simp; omega), nadd, nshl, Nat.shiftLeft_eq]
    simp only [ofD, List.length_cons]
    rw [show q + 1 = ds.length + 1 by omega]
    omega

/-! ## The mask check -/

theorem testBit_lane (W b j : Nat) (hbW : b + 1 ≤ W) :
    (2 ^ W - 2 ^ (b + 1)).testBit j = (decide (b + 1 ≤ j) && decide (j < W)) := by
  have e : 2 ^ W - 2 ^ (b + 1) = (2 ^ (W - (b + 1)) - 1) * 2 ^ (b + 1) := by
    rw [Nat.sub_mul, Nat.one_mul, ← Nat.pow_add, Nat.sub_add_cancel hbW]
  rw [e, Nat.testBit_mul_two_pow, Nat.testBit_two_pow_sub_one]
  by_cases h1 : b + 1 ≤ j
  · simp only [h1, decide_true, Bool.true_and]
    congr 1; apply propext; omega
  · simp [h1]

theorem hmask_testBit (W b : Nat) (hbW : b + 1 ≤ W) : ∀ L p j, p < L → b + 1 ≤ j → j < W →
    (hmask W b L).testBit (W * p + j) = true
  | 0, p, j, h, _, _ => absurd h (by omega)
  | L + 1, p, j, hp, h1, h2 => by
    have hl : 2 ^ W - 2 ^ (b + 1) < 2 ^ W := by
      have := Nat.two_pow_pos (b + 1); have := Nat.two_pow_pos W; omega
    simp only [hmask]
    rw [Nat.testBit_two_pow_mul_add _ hl]
    cases p with
    | zero =>
      simp only [Nat.mul_zero, Nat.zero_add, h2, if_true]
      rw [testBit_lane W b j hbW]; simp [h1, h2]
    | succ p =>
      rw [if_neg (by rw [Nat.mul_add]; omega)]
      rw [show W * (p + 1) + j - W = W * p + j by rw [Nat.mul_add]; omega]
      exact hmask_testBit W b hbW L p j (by omega) h1 h2

theorem mask_digit (W b L u : Nat) (hbW : b + 1 ≤ W) (h : Nat.land u (hmask W b L) = 0) :
    ∀ p, p < L → u / 2 ^ (W * p) % 2 ^ W < 2 ^ (b + 1) := by
  intro p hp
  apply Nat.lt_pow_two_of_testBit
  intro j hj
  rw [← Nat.shiftRight_eq_div_pow, Nat.testBit_mod_two_pow, Nat.testBit_shiftRight]
  by_cases hjW : j < W
  · simp only [hjW, decide_true, Bool.true_and]
    have h0 := congrArg (fun x => x.testBit (W * p + j)) h
    simp only [nand, Nat.testBit_and, Nat.zero_testBit] at h0
    rw [hmask_testBit W b hbW L p j hp hj hjW, Bool.and_true] at h0
    exact h0
  · simp [hjW]

/-- What the two lane checks give: the digits of `u` in lns `0 … L−1`, each below `2^(b+1)`. -/
theorem decode (W b L u : Nat) (hbW : b + 1 ≤ W) (hL : 1 ≤ L) (hm : Nat.land u (hmask W b L) = 0)
    (hs : Nat.shiftRight u (W * L) = 0) :
    ofD W (digsU (2 ^ W - 1) u (lns W (L - 1))) = u ∧
    (digsU (2 ^ W - 1) u (lns W (L - 1))).length = L ∧
    ∀ d ∈ digsU (2 ^ W - 1) u (lns W (L - 1)), d < 2 ^ (b + 1) := by
  have hu : u < 2 ^ (W * L) := by
    rw [nshr, Nat.shiftRight_eq_div_pow] at hs
    exact (Nat.div_eq_zero_iff_lt (Nat.two_pow_pos _)).mp hs
  obtain ⟨h1, h2⟩ := ofD_digsU W (L - 1) u (by rw [Nat.sub_add_cancel hL]; exact hu)
  refine ⟨h1, by rw [h2]; omega, ?_⟩
  -- every digit is a lane value
  have key : ∀ q, q < L → ∀ d ∈ digsU (2 ^ W - 1) u (lns W q), d < 2 ^ (b + 1) := by
    intro q
    induction q with
    | zero => intro _ d hd; simp [lns, digsU] at hd; subst hd
              have := mask_digit W b L u hbW hm 0 (by omega); simpa using this
    | succ q ih =>
      intro hq d hd
      simp only [lns, digsU, List.mem_cons, land_shr] at hd
      rcases hd with rfl | hd
      · exact mask_digit W b L u hbW hm (q + 1) hq
      · exact ih (by omega) d hd
  exact key (L - 1) (by omega)


/-! ## Offset digits -/

theorem rep_succ' (W : Nat) : ∀ n, rep W (n + 1) = 2 ^ (W * n) + rep W n
  | 0 => by simp [rep]
  | n + 1 => by
    have ih := rep_succ' W n
    show 2 ^ W * rep W (n + 1) + 1 = 2 ^ (W * (n + 1)) + (2 ^ W * rep W n + 1)
    rw [ih, Nat.mul_add, ← Nat.pow_add, show W + W * n = W * (n + 1) by rw [Nat.mul_add, Nat.mul_one]; omega]
    omega

/-- Offset digits `x + T` of an integer list. -/
def offs (T : Nat) (S : List Int) : List Nat := S.map (fun x => (x + (T : Int)).toNat)

theorem offs_length (T : Nat) (S : List Int) : (offs T S).length = S.length := by simp [offs]

theorem ofD_offs (W T : Nat) : ∀ S : List Int, (∀ x ∈ S, -(T : Int) ≤ x) →
    (ofD W (offs T S) : Int) = ev ((2 ^ W : Nat) : Int) S + T * rep W S.length
  | [], _ => by simp [offs, ofD, ev, rep]
  | x :: xs, h => by
    have hx : -(T : Int) ≤ x := h x (by simp)
    have ih := ofD_offs W T xs (fun y hy => h y (by simp [hy]))
    simp only [offs, List.map_cons, ofD, List.length_map, List.length_cons, rep_succ'] at ih ⊢
    rw [ev_cons]
    push_cast
    rw [ih, Int.toNat_of_nonneg (by omega), ← Int.pow_mul]
    grind

theorem offs_lt (T : Nat) (S : List Int) (h : ∀ x ∈ S, -(T : Int) ≤ x ∧ x < T) : ∀ d ∈ offs T S, d < 2 * T := by
  intro d hd
  simp only [offs, List.mem_map] at hd
  obtain ⟨x, hx, rfl⟩ := hd
  have := h x hx
  omega

/-- Digits below `2T` decode to integers in `[−T, T)` whose offset digits they are. -/
theorem undigits (T : Nat) (ds : List Nat) (h : ∀ d ∈ ds, d < 2 * T) :
    offs T (ds.map (fun d : Nat => (d : Int) - T)) = ds ∧
    ∀ x ∈ ds.map (fun d : Nat => (d : Int) - T), -(T : Int) ≤ x ∧ x < T := by
  constructor
  · simp only [offs, List.map_map]
    conv => rhs; rw [← List.map_id ds]
    apply List.map_congr_left
    intro d _; simp
  · intro x hx
    simp only [List.mem_map] at hx
    obtain ⟨d, hd, rfl⟩ := hx
    have := h d hd
    omega

/-! ## The normal step on integer lists -/

theorem ev_r2 (B LG LF C1 : Int) : ∀ Xs Zs : List Int, Xs.length = Zs.length →
    ev B (r2 LG LF C1 Xs Zs) =
      LG * LG * ev B Xs - LG * LF * (B * ev B Zs - Zs.headD 0 * B ^ Zs.length) - C1 * ev B Zs
  | [], [], _ => by simp [r2, ev]
  | X :: Xs, Z :: Zs, h => by
    simp only [List.length_cons, Nat.add_right_cancel_iff] at h
    have ih := ev_r2 B LG LF C1 Xs Zs h
    have hl : (r2 LG LF C1 Xs Zs).length = Xs.length := by
      clear ih; induction Xs generalizing Zs with
      | nil => simp [r2]
      | cons a as iha => cases Zs with
        | nil => simp at h
        | cons b bs => simp [r2, iha bs (by simpa using h)]
    simp only [r2, ev_cons, hl, ih, List.headD_cons, List.length_cons, h]
    rw [Int.pow_succ]
    grind
  | [], _ :: _, h => by simp at h
  | _ :: _, [], h => by simp at h

theorem ev_step (B lf f1 lg : Int) (xs zs : List Int) (h : xs.length = zs.length) :
    ev B (r2 lg lf (lg * f1 - lf * zs.headD 0) xs zs) =
      lg * lg * ev B (lf :: f1 :: xs) - (lf * lg * B + (lg * f1 - lf * zs.headD 0)) * ev B (lg :: zs) := by
  rw [ev_r2 B lg lf _ xs zs h]
  simp only [ev_cons, List.length_cons, h]
  rw [Int.pow_succ]
  grind

theorem headD_mul (c : Int) (l : List Int) : (l.map (c * ·)).headD 0 = c * l.headD 0 := by
  cases l <;> simp

theorem r2_sign (sF sG : Int) (hG : sG * sG = 1) (LG LF C1 : Int) : ∀ Xs Zs : List Int,
    r2 (sG * LG) (sF * LF) (sF * sG * C1) (Xs.map (sF * ·)) (Zs.map (sG * ·)) =
      (r2 LG LF C1 Xs Zs).map (sF * ·)
  | [], _ => by simp [r2]
  | _ :: _, [] => by simp [r2]
  | X :: Xs, Z :: Zs => by
    simp only [List.map_cons, r2]
    rw [r2_sign sF sG hG LG LF C1 Xs Zs, headD_mul]
    congr 1
    have e : sG * LG * (sG * LG * (sF * X) - sF * LF * (sG * Zs.headD 0)) - sF * sG * C1 * (sG * Z)
        = (sG * sG) * (sF * (LG * (LG * X - LF * Zs.headD 0) - C1 * Z)) := by grind
    rw [e, hG, Int.one_mul]

theorem r2_bound (LG LF : Nat) (C1 : Int) (TX TZ : Nat) : ∀ Xs Zs : List Int,
    (∀ x ∈ Xs, x.natAbs ≤ TX) → (∀ z ∈ Zs, z.natAbs ≤ TZ) →
    ∀ e ∈ r2 LG LF C1 Xs Zs, e.natAbs ≤ LG * (LG * TX + LF * TZ) + C1.natAbs * TZ
  | [], _, _, _ => by simp [r2]
  | _ :: _, [], _, _ => by simp [r2]
  | X :: Xs, Z :: Zs, hX, hZ => by
    intro e he
    simp only [r2, List.mem_cons] at he
    rcases he with rfl | he
    · have hx := hX X (by simp)
      have hz := hZ Z (by simp)
      have hy : (Zs.headD 0).natAbs ≤ TZ := by
        cases Zs with
        | nil => simp
        | cons y ys => exact hZ y (by simp)
      have h1 := Int.natAbs_sub_le ((LG : Int) * ((LG : Int) * X - (LF : Int) * Zs.headD 0)) (C1 * Z)
      have h2 := Int.natAbs_sub_le ((LG : Int) * X) ((LF : Int) * Zs.headD 0)
      simp only [Int.natAbs_mul, Int.natAbs_natCast] at h1 h2
      have h3 : LG * (LG * X - LF * Zs.headD 0 : Int).natAbs ≤ LG * (LG * TX + LF * TZ) :=
        Nat.mul_le_mul_left _ (Nat.le_trans h2 (Nat.add_le_add (Nat.mul_le_mul_left _ hx) (Nat.mul_le_mul_left _ hy)))
      have h4 : C1.natAbs * Z.natAbs ≤ C1.natAbs * TZ := Nat.mul_le_mul_left _ hz
      omega
    · exact r2_bound LG LF C1 TX TZ Xs Zs (fun x hx => hX x (by simp [hx])) (fun z hz => hZ z (by simp [hz])) e he


/-! ## One packed step -/

/-- The packed state `s` holds the sign-normalized `F̂`, `Ĝ` (degrees `d`, `d − 1`) in lanes `(W, b)`;
`ini`: the next step is the initial one (`dm = 1`). -/
def PInv (W b d : Nat) (ini : Bool) (s : PSt) (F G : List Int) : Prop :=
  F.length = d + 1 ∧ G.length = d ∧
  (∀ x ∈ F, -((2 ^ b : Nat) : Int) ≤ x ∧ x < ((2 ^ b : Nat) : Int)) ∧
  (∀ x ∈ G, -((2 ^ b : Nat) : Int) ≤ x ∧ x < ((2 ^ b : Nat) : Int)) ∧
  1 ≤ F.headD 0 ∧ 1 ≤ G.headD 0 ∧
  (s.fv : Int) = ev ((2 ^ W : Nat) : Int) F ∧ (s.gv : Int) = ev ((2 ^ W : Nat) : Int) G ∧
  (s.lf : Int) = F.headD 0 ∧ (s.lg : Int) = G.headD 0 ∧
  (s.df1 : Int) = F.tail.headD 0 + ((2 ^ b : Nat) : Int) ∧
  (2 ≤ d → (s.dg1 : Int) = G.tail.headD 0 + ((2 ^ b : Nat) : Int)) ∧
  s.fs < 2 ∧ s.gs < 2 ∧
  (s.dm : Int) = (if ini then 1 else F.headD 0 ^ 2)

theorem sg_xor (a b : Nat) (ha : a < 2) (hb : b < 2) : sg (Nat.xor a b) = sg a * sg b := by
  rw [nxor, xor_bits a b ha hb]
  have := sg_add a b
  rw [Nat.mod_eq_of_lt ha, Nat.mod_eq_of_lt hb] at this
  exact this

theorem sg_sq (a : Nat) (ha : a < 2) : sg a * sg a = 1 := by
  have := sg_mod2 a; rwa [Nat.mod_eq_of_lt ha] at this

theorem sg_ne (a : Nat) : sg a ≠ 0 := by
  unfold sg; omega

theorem xor_lt2 (a b : Nat) (ha : a < 2) (hb : b < 2) : Nat.xor a b < 2 := by
  rw [nxor, xor_bits a b ha hb]; exact Nat.mod_lt _ (by decide)

/-- `|X₁ − X₂|` and its sign bit from truncated subtractions. -/
theorem absdiff (X1 X2 : Nat) :
    Nat.sub 1 (Nat.sub 1 (Nat.sub X2 X1)) < 2 ∧
    (X1 : Int) - X2 = sg (Nat.sub 1 (Nat.sub 1 (Nat.sub X2 X1))) * (Nat.add (Nat.sub X1 X2) (Nat.sub X2 X1) : Nat) := by
  simp only [nsub, nadd]
  unfold sg
  by_cases h : X1 < X2
  · rw [show X2 - X1 = X2 - X1 from rfl, show 1 - (1 - (X2 - X1)) = 1 by omega]
    constructor
    · omega
    · push_cast; omega
  · rw [show 1 - (1 - (X2 - X1)) = 0 by omega]
    constructor
    · omega
    · push_cast; omega

/-- Exactness from the low-bits check: `mag − dm·q ∈ [0, dm)` vanishes mod `2^k > dm`. -/
theorem lowbits_exact (mag dm q k : Nat) (hq : q = mag / dm) (hdm0 : 0 < dm) (hdm : dm < 2 ^ k)
    (h : Nat.add (Nat.sub (Nat.land mag (2 ^ k - 1)) (Nat.land (Nat.mul dm (Nat.land q (2 ^ k - 1))) (2 ^ k - 1)))
      (Nat.sub (Nat.land (Nat.mul dm (Nat.land q (2 ^ k - 1))) (2 ^ k - 1)) (Nat.land mag (2 ^ k - 1))) = 0) :
    mag = dm * q := by
  simp only [nadd, nsub, nmul, nand, Nat.and_two_pow_sub_one_eq_mod] at h
  have e : mag % 2 ^ k = dm * (q % 2 ^ k) % 2 ^ k := by omega
  rw [Nat.mul_mod, Nat.mod_mod, ← Nat.mul_mod] at e
  have hdm' := Nat.div_add_mod mag dm
  have hlt := Nat.mod_lt mag hdm0
  rw [← hq] at hdm'
  have h0 := Nat.sub_mod_eq_zero_of_mod_eq e
  rw [show mag - dm * q = mag % dm by omega, Nat.mod_eq_of_lt (by omega)] at h0
  omega


theorem dlist_mem (k : Int) : ∀ N Q : List Int, ∀ x ∈ dlist k N Q, ∃ n ∈ N, ∃ q ∈ Q, x = n - k * q
  | n :: ns, q :: qs, x, hx => by
    simp only [dlist, List.mem_cons] at hx
    rcases hx with rfl | hx
    · exact ⟨n, by simp, q, by simp, rfl⟩
    · obtain ⟨n', hn, q', hq, e⟩ := dlist_mem k ns qs x hx
      exact ⟨n', by simp [hn], q', by simp [hq], e⟩
  | [], _, x, hx => by simp [dlist] at hx
  | _ :: _, [], x, hx => by simp [dlist] at hx

theorem dlist_length (k : Int) : ∀ N Q : List Int, N.length = Q.length → (dlist k N Q).length = N.length
  | [], _, _ => by simp [dlist]
  | _ :: _, [], h => by simp at h
  | n :: ns, q :: qs, h => by simp only [dlist, List.length_cons]; rw [dlist_length k ns qs (by simpa using h)]

theorem r2_length (LG LF C1 : Int) : ∀ Xs Zs : List Int, Xs.length = Zs.length →
    (r2 LG LF C1 Xs Zs).length = Xs.length
  | [], _, _ => by simp [r2]
  | _ :: _, [], h => by simp at h
  | X :: Xs, Z :: Zs, h => by simp only [r2, List.length_cons]; rw [r2_length LG LF C1 Xs Zs (by simpa using h)]

theorem pow3_lt (b W : Nat) (hW : 3 * b + 3 ≤ W) : 8 * (2 ^ b * 2 ^ b * 2 ^ b) ≤ 2 ^ W := by
  have : 2 ^ (3 * b + 3) ≤ 2 ^ W := Nat.pow_le_pow_right (by decide) hW
  have e : 2 ^ (3 * b + 3) = 8 * (2 ^ b * 2 ^ b * 2 ^ b) := by
    rw [Nat.pow_add, show 3 * b = b + b + b by omega, Nat.pow_add, Nat.pow_add]; omega
  omega

theorem natAbs_le_of_bounds (T : Nat) (x : Int) (h : -(T : Int) ≤ x ∧ x < T) : x.natAbs ≤ T := by omega



theorem digsU_head (W u : Nat) : ∀ p, (digsU (2 ^ W - 1) u (lns W p)).headD 0 = u / 2 ^ (W * p) % 2 ^ W
  | 0 => by simp [lns, digsU]
  | p + 1 => by simp [lns, digsU, Nat.shiftRight_eq_div_pow]

theorem digsU_second (W u p : Nat) :
    (digsU (2 ^ W - 1) u (lns W (p + 1))).tail.headD 0 = u / 2 ^ (W * p) % 2 ^ W := by
  cases p <;> simp [lns, digsU, Nat.shiftRight_eq_div_pow]

theorem ofD_val (W T : Nat) (ds : List Nat) (h : ∀ d ∈ ds, d < 2 * T) :
    (ofD W ds : Int) = ev ((2 ^ W : Nat) : Int) (ds.map (fun d : Nat => (d : Int) - T)) + T * rep W ds.length := by
  have hu := undigits T ds h
  have := ofD_offs W T (ds.map (fun d : Nat => (d : Int) - T)) (fun x hx => (hu.2 x hx).1)
  rw [hu.1, List.length_map] at this
  exact this


theorem bound5 (T lg lf dm : Nat) (c : Int) (hlg : lg ≤ T) (hlf : lf ≤ T) (hdm : dm ≤ T * T)
    (hc : c.natAbs ≤ lg * T + lf * T) :
    lg * (lg * T + lf * T) + c.natAbs * T + dm * T ≤ 5 * (T * T * T) := by
  have e1 : lg * (lg * T + lf * T) ≤ T * (T * T + T * T) :=
    Nat.mul_le_mul hlg (Nat.add_le_add (Nat.mul_le_mul_right _ hlg) (Nat.mul_le_mul_right _ hlf))
  have e2 : c.natAbs * T ≤ (T * T + T * T) * T :=
    Nat.mul_le_mul_right _ (Nat.le_trans hc (Nat.add_le_add (Nat.mul_le_mul_right _ hlg) (Nat.mul_le_mul_right _ hlf)))
  have e3 : dm * T ≤ T * T * T := Nat.mul_le_mul_right _ hdm
  have f1 : T * (T * T + T * T) = 2 * (T * T * T) := by grind
  have f2 : (T * T + T * T) * T = 2 * (T * T * T) := by grind
  omega

theorem sg_natAbs (a : Nat) (ha : a < 2) : (sg a).natAbs = 1 := by
  unfold sg; rcases (by omega : a = 0 ∨ a = 1) with rfl | rfl <;> decide


theorem sg_hxor (a b : Nat) (ha : a < 2) (hb : b < 2) : sg (a ^^^ b) = sg a * sg b := sg_xor a b ha hb

theorem hxor_lt2 (a b : Nat) (ha : a < 2) (hb : b < 2) : a ^^^ b < 2 := xor_lt2 a b ha hb

theorem pstep_spec (W b d : Nat) (ini lowb : Bool) (s : PSt) (F G : List Int)
    (T m O HM m2 sb sW s1 s0 sm : Nat)
    (hT : T = 2 ^ b) (hm : m = 2 ^ W - 1) (hO : O = 2 ^ b * rep W (d - 1)) (hHM : HM = hmask W b (d - 1))
    (hm2 : m2 = 2 ^ (2 * b) - 1) (hsb : sb = b) (hsW : sW = W) (hs1 : s1 = W * (d - 1))
    (hs0 : s0 = W * (d - 2)) (hsm : sm = W * (d - 3)) (hW : 3 * b + 3 ≤ W) (hd : 2 ≤ d)
    (hI : PInv W b d ini s F G) (hbad : (pstep T m O HM m2 sb sW s1 s0 sm ini lowb s).bad = 0) :
    ∃ H, PInv W b (d - 1) false (pstep T m O HM m2 sb sW s1 s0 sm ini lowb s) G H ∧
      ∀ fuel, normalResultantGo (fuel + 1) ini (F.map (sg s.fs * ·)) (G.map (sg s.gs * ·)) =
        if d = 2 then some (sg (pstep T m O HM m2 sb sW s1 s0 sm ini lowb s).gs * H.headD 0)
        else normalResultantGo fuel false (G.map (sg s.gs * ·))
          (H.map (sg (pstep T m O HM m2 sb sW s1 s0 sm ini lowb s).gs * ·)) := by
  obtain ⟨hFl, hGl, hFb, hGb, hF0, hG0, hfv, hgv, hlf, hlg, hdf1, hdg1, hfs, hgs, hdm⟩ := hI
  subst T m O HM m2 sb sW s1 s0 sm
  obtain ⟨lf, f1, xs, rfl⟩ : ∃ lf f1 xs, F = lf :: f1 :: xs := by
    match F, hFl with
    | lf :: f1 :: xs, _ => exact ⟨lf, f1, xs, rfl⟩
    | [], h => simp at h
    | [_], h => simp at h; omega
  obtain ⟨lg, zs, rfl⟩ : ∃ lg zs, G = lg :: zs := by
    match G, hGl with
    | lg :: zs, _ => exact ⟨lg, zs, rfl⟩
    | [], h => simp at h; omega
  simp only [List.length_cons] at hFl hGl
  simp only [List.headD_cons, List.tail_cons] at hF0 hG0 hlf hlg hdf1 hdg1 hdm
  have hdg1' := hdg1 hd
  simp only [pstep] at hbad ⊢
  simp only [nadd, nsub, nmul, ndiv, nmod, nand, nshr, nshl, nxor] at hbad ⊢
  generalize hP1 : s.lg * s.df1 + s.lf <<< b = P1 at hbad ⊢
  generalize hN1 : s.lf * s.dg1 + s.lg <<< b = N1 at hbad ⊢
  generalize hA : s.lg * s.lg = A at hbad ⊢
  generalize hX1 : A * s.fv = X1 at hbad ⊢
  generalize hM : (s.lf * s.lg) <<< W + P1 - N1 = M at hbad ⊢
  generalize hX2 : M * s.gv = X2 at hbad ⊢
  generalize hD2 : X2 - X1 = D2 at hbad ⊢
  generalize hmag : X1 - X2 + D2 = mag at hbad ⊢
  generalize hq : cond ini mag (mag / s.dm) = q at hbad ⊢
  generalize hu : q + 2 ^ b * rep W (d - 1) = u at hbad ⊢
  generalize hlh : u >>> (W * (d - 2)) - 2 ^ b = lh at hbad ⊢
  generalize hneg : 1 - (1 - D2) = neg at hbad ⊢
  -- the checks
  obtain ⟨hb1, hlead⟩ := Nat.add_eq_zero_iff.mp hbad
  obtain ⟨hcnd, hb2⟩ := Nat.add_eq_zero_iff.mp hb1
  obtain ⟨hmask0, hshr0⟩ := Nat.add_eq_zero_iff.mp hb2
  have hc1n : 1 - (P1 - N1 + (N1 - P1)) = 0 := by
    cases ini <;> cases lowb <;> simp only [cond] at hcnd <;> omega
  -- bounds of the digits
  have hT0 : 0 < 2 ^ b := Nat.two_pow_pos b
  have hlfb := hFb lf (by simp)
  have hf1b := hFb f1 (by simp)
  have hlgb := hGb lg (by simp)
  have hxsb : ∀ x ∈ xs, -((2 ^ b : Nat) : Int) ≤ x ∧ x < ((2 ^ b : Nat) : Int) := fun x hx => hFb x (by simp [hx])
  have hzsb : ∀ x ∈ zs, -((2 ^ b : Nat) : Int) ≤ x ∧ x < ((2 ^ b : Nat) : Int) := fun x hx => hGb x (by simp [hx])
  have hg1b : -((2 ^ b : Nat) : Int) ≤ zs.headD 0 ∧ zs.headD 0 < ((2 ^ b : Nat) : Int) := by
    cases zs with
    | nil => simp at hGl; omega
    | cons z zs' => exact hzsb z (by simp)
  have hlfn : s.lf < 2 ^ b := by have := hlfb.2; omega
  have hlgn : s.lg < 2 ^ b := by have := hlgb.2; omega
  have hdg1n : s.dg1 < 2 * 2 ^ b := by have := hg1b.2; omega
  have hdf1n : s.df1 < 2 * 2 ^ b := by have := hf1b.2; omega
  have e2b : 2 ^ (2 * b) = 2 ^ b * 2 ^ b := by rw [Nat.two_mul, Nat.pow_add]
  -- the divisor
  have hT1 : 1 ≤ 2 ^ b * 2 ^ b := Nat.mul_pos hT0 hT0
  have hdmle : s.dm ≤ 2 ^ b * 2 ^ b := by
    cases ini
    · simp only [Bool.false_eq_true, if_false] at hdm
      have : s.dm = s.lf * s.lf := by
        have : ((s.lf * s.lf : Nat) : Int) = lf ^ 2 := by push_cast; rw [hlf, Int.pow_succ, Int.pow_one]
        omega
      rw [this]; exact Nat.mul_le_mul (by omega) (by omega)
    · simp only [if_true] at hdm; omega
  -- exact division
  have hexact : mag = s.dm * q := by
    cases ini
    · cases lowb
      · simp only [cond] at hcnd hq
        have hmod : mag % s.dm = 0 := by omega
        rw [← hq]; exact (Nat.mul_div_cancel' (Nat.dvd_of_mod_eq_zero hmod)).symm
      · simp only [cond] at hcnd hq
        simp only [Bool.false_eq_true, if_false] at hdm
        have hdm' : s.dm = s.lf * s.lf := by
          have : ((s.lf * s.lf : Nat) : Int) = lf ^ 2 := by push_cast; rw [hlf, Int.pow_succ, Int.pow_one]
          omega
        apply lowbits_exact mag s.dm q (2 * b) hq.symm (by rw [hdm']; exact Nat.mul_pos (by omega) (by omega))
          (by rw [hdm', e2b]; exact Nat.mul_lt_mul_of_lt_of_lt hlfn hlfn)
        simp only [nadd, nsub, nmul, nand]; omega
    · simp only [cond] at hq
      simp only [if_true] at hdm
      have : s.dm = 1 := by omega
      rw [this, ← hq, Nat.one_mul]
  -- integer values of the step quantities
  have hP1i : (P1 : Int) = lg * (f1 + ((2 ^ b : Nat) : Int)) + lf * ((2 ^ b : Nat) : Int) := by
    rw [← hP1, Nat.shiftLeft_eq]; simp only [Int.natCast_add, Int.natCast_mul]; rw [hlg, hdf1, hlf]
  have hN1i : (N1 : Int) = lf * (zs.headD 0 + ((2 ^ b : Nat) : Int)) + lg * ((2 ^ b : Nat) : Int) := by
    rw [← hN1, Nat.shiftLeft_eq]; simp only [Int.natCast_add, Int.natCast_mul]; rw [hlg, hdg1', hlf]
  have hc1 : (P1 : Int) - N1 = lg * f1 - lf * zs.headD 0 := by rw [hP1i, hN1i]; grind
  have hc1ne : lg * f1 - lf * zs.headD 0 ≠ 0 := by rw [← hc1]; omega
  have hN1lt : N1 < 2 ^ W := by
    have h8 := pow3_lt b W hW
    have h1 : s.lf * s.dg1 ≤ 2 ^ b * (2 * 2 ^ b) := Nat.mul_le_mul (by omega) (by omega)
    have h2 : s.lg * 2 ^ b ≤ 2 ^ b * 2 ^ b := Nat.mul_le_mul (by omega) (by omega)
    have h3 : 2 ^ b * 2 ^ b ≤ 2 ^ b * 2 ^ b * 2 ^ b := Nat.le_mul_of_pos_right _ hT0
    rw [← hN1, Nat.shiftLeft_eq]
    have : 2 ^ b * (2 * 2 ^ b) = 2 * (2 ^ b * 2 ^ b) := by rw [Nat.mul_left_comm]
    omega
  have hMi : (M : Int) = lf * lg * ((2 ^ W : Nat) : Int) + (lg * f1 - lf * zs.headD 0) := by
    have hlflg : 1 ≤ s.lf * s.lg := Nat.mul_pos (by omega) (by omega)
    have : 2 ^ W ≤ s.lf * s.lg * 2 ^ W := Nat.le_mul_of_pos_left _ hlflg
    rw [← hM, Nat.shiftLeft_eq]
    rw [Int.ofNat_sub (by omega)]
    simp only [Int.natCast_add, Int.natCast_mul]
    rw [hlf, hlg, ← hc1]
    omega
  -- the numerator polynomial and its value at B
  have hlen : xs.length = zs.length := by omega
  have hX1i : (X1 : Int) = lg * lg * ev ((2 ^ W : Nat) : Int) (lf :: f1 :: xs) := by
    rw [← hX1, ← hA, Int.natCast_mul, Int.natCast_mul, hlg, hfv]
  have hX2i : (X2 : Int) = (lf * lg * ((2 ^ W : Nat) : Int) + (lg * f1 - lf * zs.headD 0)) *
      ev ((2 ^ W : Nat) : Int) (lg :: zs) := by
    rw [← hX2, Int.natCast_mul, hMi, hgv]
  have hevN : ev ((2 ^ W : Nat) : Int) (r2 lg lf (lg * f1 - lf * zs.headD 0) xs zs) = (X1 : Int) - X2 := by
    rw [ev_step _ lf f1 lg xs zs hlen, hX1i, hX2i]
  obtain ⟨hneg2, hsgn⟩ := absdiff X1 X2
  simp only [nsub, nadd] at hneg2 hsgn
  rw [hD2] at hneg2 hsgn
  rw [hmag] at hsgn
  rw [hneg] at hneg2 hsgn
  -- the new polynomial from the lane checks
  have hbW : b + 1 ≤ W := by omega
  have hL : 1 ≤ d - 1 := by omega
  obtain ⟨hdu, hdl, hdb⟩ := decode W b (d - 1) u hbW hL hmask0 hshr0
  rw [show d - 1 - 1 = d - 2 by omega] at hdu hdl hdb
  have hdb' : ∀ x ∈ digsU (2 ^ W - 1) u (lns W (d - 2)), x < 2 * 2 ^ b := by
    intro x hx; have := hdb x hx; rw [Nat.pow_succ] at this; omega
  generalize hds : digsU (2 ^ W - 1) u (lns W (d - 2)) = ds at hdu hdl hdb hdb'
  have hH := undigits (2 ^ b) ds hdb'
  have hHv := ofD_val W (2 ^ b) ds hdb'
  rw [hdu, hdl] at hHv
  generalize hHdef : ds.map (fun x : Nat => (x : Int) - ((2 ^ b : Nat) : Int)) = H at hH hHv
  have hHl : H.length = d - 1 := by rw [← hHdef, List.length_map, hdl]
  have hqv : (q : Int) = ev ((2 ^ W : Nat) : Int) H := by
    have : (u : Int) = q + ((2 ^ b : Nat) : Int) * (rep W (d - 1) : Nat) := by
      rw [← hu]; simp only [Int.natCast_add, Int.natCast_mul]
    omega
  -- the E-argument: the numerator is coefficientwise `± dm · H`
  have hN : r2 lg lf (lg * f1 - lf * zs.headD 0) xs zs =
      H.map (fun h => (sg neg * (s.dm : Int)) * h) := by
    have hNl : (r2 lg lf (lg * f1 - lf * zs.headD 0) xs zs).length = H.length := by
      rw [r2_length _ _ _ xs zs hlen, hHl]; omega
    apply eq_map_of_ev (2 ^ W) (Nat.two_pow_pos W) _ _ H hNl
    · intro x hx
      obtain ⟨n, hn, h, hh, rfl⟩ := dlist_mem _ _ _ x hx
      have hnb := r2_bound s.lg s.lf (lg * f1 - lf * zs.headD 0) (2 ^ b) (2 ^ b) xs zs
        (fun x hx => natAbs_le_of_bounds _ x (hxsb x hx)) (fun x hx => natAbs_le_of_bounds _ x (hzsb x hx))
        n (by rw [hlg, hlf]; exact hn)
      have hhb := natAbs_le_of_bounds _ h (hH.2 h hh)
      have hc1b : (lg * f1 - lf * zs.headD 0).natAbs ≤ s.lg * 2 ^ b + s.lf * 2 ^ b := by
        have := Int.natAbs_sub_le (lg * f1) (lf * zs.headD 0)
        rw [Int.natAbs_mul, Int.natAbs_mul] at this
        have h1 : lg.natAbs = s.lg := by omega
        have h2 : lf.natAbs = s.lf := by omega
        rw [h1, h2] at this
        have := Nat.mul_le_mul_left s.lg (natAbs_le_of_bounds _ f1 hf1b)
        have := Nat.mul_le_mul_left s.lf (natAbs_le_of_bounds _ _ hg1b)
        omega
      have h5 := bound5 (2 ^ b) s.lg s.lf s.dm _ (by omega) (by omega) hdmle hc1b
      have h8 := pow3_lt b W hW
      have hk : (sg neg * (s.dm : Int) * h).natAbs ≤ s.dm * 2 ^ b := by
        rw [Int.natAbs_mul, Int.natAbs_mul, sg_natAbs neg hneg2, Int.natAbs_natCast, Nat.one_mul]
        exact Nat.mul_le_mul_left _ hhb
      have := Int.natAbs_sub_le n (sg neg * (s.dm : Int) * h)
      have hT3 : 0 < 2 ^ b * 2 ^ b * 2 ^ b := Nat.mul_pos (Nat.mul_pos hT0 hT0) hT0
      omega
    · rw [hevN, ← hqv, hsgn, hexact, Int.natCast_mul]; grind
  -- leading and second digits of H
  have hu_lt : u < 2 ^ (W * (d - 1)) := by
    rw [Nat.shiftRight_eq_div_pow] at hshr0
    exact (Nat.div_eq_zero_iff_lt (Nat.two_pow_pos _)).mp hshr0
  obtain ⟨δ0, rest, hdsc⟩ : ∃ δ0 rest, ds = δ0 :: rest := by
    cases ds with
    | nil => simp at hdl; omega
    | cons a l => exact ⟨a, l, rfl⟩
  have hδ0 : δ0 = u >>> (W * (d - 2)) := by
    have := digsU_head W u (d - 2)
    rw [hds, hdsc, List.headD_cons] at this
    rw [this, Nat.shiftRight_eq_div_pow]
    apply Nat.mod_eq_of_lt
    rw [Nat.div_lt_iff_lt_mul (Nat.two_pow_pos _), ← Nat.pow_add]
    rw [show W + W * (d - 2) = W * (d - 1) by
      rw [show d - 1 = (d - 2) + 1 by omega, Nat.mul_add, Nat.mul_one, Nat.add_comm]]
    exact hu_lt
  have hH0 : H.headD 0 = (δ0 : Int) - ((2 ^ b : Nat) : Int) := by
    rw [← hHdef, hdsc]; rfl
  have hlh1 : 1 ≤ lh := by omega
  have hlhi : (lh : Int) = H.headD 0 := by
    rw [hH0, hδ0]; rw [← hlh]; omega
  have hH01 : 1 ≤ H.headD 0 := by omega
  have hH1 : 2 ≤ d - 1 → ((u >>> (W * (d - 3)) &&& (2 ^ W - 1) : Nat) : Int) = H.tail.headD 0 + ((2 ^ b : Nat) : Int) := by
    intro h3
    have := digsU_second W u (d - 3)
    rw [show d - 3 + 1 = d - 2 by omega, hds] at this
    rw [Nat.and_two_pow_sub_one_eq_mod, Nat.shiftRight_eq_div_pow, ← this, ← hHdef]
    rw [hdsc] at hdl ⊢
    cases rest with
    | nil => simp at hdl; omega
    | cons δ1 rest' => simp
  have hneg' : neg < 2 := hneg2
  refine ⟨H, ?_, ?_⟩
  · -- the invariant one degree down
    simp only [PInv, List.length_cons, List.headD_cons, List.tail_cons, Bool.false_eq_true, if_false]
    refine ⟨by omega, hHl, hGb, hH.2, hG0, hH01, hgv, hqv, hlg, hlhi, hdg1', hH1, hgs,
      hxor_lt2 _ _ hfs hneg', ?_⟩
    rw [← hA, Int.natCast_mul, hlg, Int.pow_succ, Int.pow_one]
  · -- the specification's normal step
    intro fuel
    have hsF := sg_sq _ hfs
    have hsG := sg_sq _ hgs
    have hC : sg s.gs * lg * (sg s.fs * f1) - sg s.fs * lf * (zs.map (fun x => sg s.gs * x)).headD 0
        = sg s.fs * sg s.gs * (lg * f1 - lf * zs.headD 0) := by rw [headD_mul]; grind
    have hR : r2 (sg s.gs * lg) (sg s.fs * lf)
        (sg s.gs * lg * (sg s.fs * f1) - sg s.fs * lf * (zs.map (fun x => sg s.gs * x)).headD 0)
        (xs.map (fun x => sg s.fs * x)) (zs.map (fun x => sg s.gs * x))
        = (H.map (fun x => sg (s.fs ^^^ neg) * x)).map (fun q => q * (s.dm : Int)) := by
      rw [hC, r2_sign _ _ hsG, hN, List.map_map, List.map_map]
      apply List.map_congr_left
      intro h _
      simp only [Function.comp_apply, sg_hxor _ _ hfs hneg']
      grind
    have hHne : H ≠ [] := by intro h; rw [h] at hH01; simp at hH01
    have hdm0 : (s.dm : Int) ≠ 0 := by
      cases ini
      · simp only [Bool.false_eq_true, if_false] at hdm; rw [hdm]; exact Int.pow_ne_zero (by omega)
      · simp only [if_true] at hdm; omega
    have hq0 : (H.map (fun x => sg (s.fs ^^^ neg) * x)).headD 0 ≠ 0 := by
      rw [headD_mul]; exact Int.mul_ne_zero (sg_ne _) (by omega)
    have hr2 : (r2 (sg s.gs * lg) (sg s.fs * lf)
        (sg s.gs * lg * (sg s.fs * f1) - sg s.fs * lf * (zs.map (fun x => sg s.gs * x)).headD 0)
        (xs.map (fun x => sg s.fs * x)) (zs.map (fun x => sg s.gs * x))).headD 0 ≠ 0 := by
      rw [hR]
      cases hH' : H.map (fun x => sg (s.fs ^^^ neg) * x) with
      | nil => rw [hH'] at hq0; simp at hq0
      | cons a l => rw [hH'] at hq0; simp only [List.map_cons, List.headD_cons] at hq0 ⊢
                    exact Int.mul_ne_zero hq0 hdm0
    have hdiv : (if ini then some (r2 (sg s.gs * lg) (sg s.fs * lf)
          (sg s.gs * lg * (sg s.fs * f1) - sg s.fs * lf * (zs.map (fun x => sg s.gs * x)).headD 0)
          (xs.map (fun x => sg s.fs * x)) (zs.map (fun x => sg s.gs * x)))
        else exactDividePolynomial ((sg s.fs * lf) ^ 2) (r2 (sg s.gs * lg) (sg s.fs * lf)
          (sg s.gs * lg * (sg s.fs * f1) - sg s.fs * lf * (zs.map (fun x => sg s.gs * x)).headD 0)
          (xs.map (fun x => sg s.fs * x)) (zs.map (fun x => sg s.gs * x))))
        = some (H.map (fun x => sg (s.fs ^^^ neg) * x)) := by
      rw [hR]
      cases ini
      · simp only [Bool.false_eq_true, if_false] at hdm ⊢
        rw [hdm, show (sg s.fs * lf) ^ 2 = lf ^ 2 by
          rw [Int.pow_succ, Int.pow_one, Int.pow_succ, Int.pow_one,
            show sg s.fs * lf * (sg s.fs * lf) = (sg s.fs * sg s.fs) * (lf * lf) by ac_rfl, hsF, Int.one_mul]]
        exact exactDivide_map _ (Int.pow_ne_zero (by omega)) _
      · simp only [if_true] at hdm ⊢
        rw [hdm]; simp
    have hstep := normal_step fuel ini (sg s.fs * lf) (sg s.fs * f1) (sg s.gs * lg)
      (xs.map (fun x => sg s.fs * x)) (zs.map (fun x => sg s.gs * x)) (H.map (fun x => sg (s.fs ^^^ neg) * x))
      (Int.mul_ne_zero (sg_ne _) (by omega)) (Int.mul_ne_zero (sg_ne _) (by omega))
      (by simp [hlen]) (by simp; omega)
      (by rw [hC]; exact Int.mul_ne_zero (Int.mul_ne_zero (sg_ne _) (sg_ne _)) hc1ne)
      hr2 hdiv hq0 (by simp; omega)
    simp only [List.map_cons]
    rw [hstep, List.length_map, headD_mul]
    by_cases h2 : d = 2
    · rw [if_pos (by omega), if_pos h2]
    · rw [if_neg (by omega), if_neg h2]


/-! ## Moving to wider lanes -/

theorem ev_pos (B : Nat) (hB : 0 < B) (a : Int) (as : List Int) (ha : 1 ≤ a) (h : ∀ x ∈ as, x.natAbs < B) :
    0 < ev B (a :: as) := by
  have := ev_natAbs_lt B hB as h
  rw [ev_cons]
  have h1 : ((B : Int) ^ as.length) = ((B ^ as.length : Nat) : Int) := by push_cast; rfl
  have h2 : (B ^ as.length : Int) ≤ a * (B : Int) ^ as.length := by
    rw [h1]; have := Int.mul_le_mul_of_nonneg_right ha (Int.natCast_nonneg (B ^ as.length)); omega
  omega

theorem offs_shift (T T' : Nat) (hTT : T ≤ T') (S : List Int) (h : ∀ x ∈ S, -(T : Int) ≤ x) :
    (offs T S).map (fun x => Nat.add x (T' - T)) = offs T' S := by
  simp only [offs, List.map_map]
  apply List.map_congr_left
  intro x hx
  have := h x hx
  simp only [Function.comp_apply, nadd]
  omega

/-- The packed value of a bounded list from its offset digits. -/
theorem pack_value (W T : Nat) (S : List Int) (hS : ∀ x ∈ S, -(T : Int) ≤ x ∧ x < T)
    (hl : S ≠ []) (hpos : 0 ≤ ev ((2 ^ W : Nat) : Int) S) :
    ((Nat.sub (packL (offs T S) (lns1 W (S.length - 1))) (T * rep W S.length) : Nat) : Int) =
      ev ((2 ^ W : Nat) : Int) S := by
  have hlen : (offs T S).length = S.length - 1 + 1 := by rw [offs_length]; cases S <;> simp_all
  rw [packL_ofD W _ _ hlen]
  have hv := ofD_offs W T S (fun x hx => (hS x hx).1)
  have hle : T * rep W S.length ≤ ofD W (offs T S) := by
    have : ((T * rep W S.length : Nat) : Int) ≤ (ofD W (offs T S) : Int) := by rw [Int.natCast_mul]; omega
    exact_mod_cast this
  rw [nsub, Int.ofNat_sub hle, hv, Int.natCast_mul]; omega

theorem prepack_spec (W b W' b' d : Nat) (ini : Bool) (s : PSt) (F G : List Int)
    (m OF OG : Nat) (shF shG pF pG : List Nat) (OF' OG' dT : Nat)
    (hm : m = 2 ^ W - 1) (hOF : OF = 2 ^ b * rep W (d + 1)) (hOG : OG = 2 ^ b * rep W d)
    (hshF : shF = lns W d) (hshG : shG = lns W (d - 1)) (hpF : pF = lns1 W' d) (hpG : pG = lns1 W' (d - 1))
    (hOF' : OF' = 2 ^ b' * rep W' (d + 1)) (hOG' : OG' = 2 ^ b' * rep W' d) (hdT : dT = 2 ^ b' - 2 ^ b)
    (hbb : b ≤ b') (hW : b + 1 ≤ W) (hW' : b' + 1 ≤ W') (hd : 1 ≤ d)
    (hI : PInv W b d ini s F G) : PInv W' b' d ini (prepack m OF OG shF shG pF pG OF' OG' dT s) F G := by
  obtain ⟨hFl, hGl, hFb, hGb, hF0, hG0, hfv, hgv, hlf, hlg, hdf1, hdg1, hfs, hgs, hdm⟩ := hI
  subst m OF OG shF shG pF pG OF' OG' dT
  have hTT : 2 ^ b ≤ 2 ^ b' := Nat.pow_le_pow_right (by decide) hbb
  have h2T : 2 * 2 ^ b ≤ 2 ^ W := by
    have := Nat.pow_le_pow_right (show 0 < 2 by decide) hW; rw [Nat.pow_succ] at this; omega
  have h2T' : 2 * 2 ^ b' ≤ 2 ^ W' := by
    have := Nat.pow_le_pow_right (show 0 < 2 by decide) hW'; rw [Nat.pow_succ] at this; omega
  -- the old offset digits of F and G
  have hdigF : digsU (2 ^ W - 1) (Nat.add s.fv (2 ^ b * rep W (d + 1))) (lns W d) = offs (2 ^ b) F := by
    have hv := ofD_offs W (2 ^ b) F (fun x hx => (hFb x hx).1)
    have e : Nat.add s.fv (2 ^ b * rep W (d + 1)) = ofD W (offs (2 ^ b) F) := by
      rw [hFl] at hv
      have : ((Nat.add s.fv (2 ^ b * rep W (d + 1)) : Nat) : Int) = ((ofD W (offs (2 ^ b) F) : Nat) : Int) := by
        rw [hv, nadd, Int.natCast_add, Int.natCast_mul, hfv]
      exact_mod_cast this
    rw [e]
    exact digsU_ofD W _ (fun x hx => Nat.lt_of_lt_of_le (offs_lt _ F hFb x hx) h2T) d (by rw [offs_length, hFl])
  have hdigG : digsU (2 ^ W - 1) (Nat.add s.gv (2 ^ b * rep W d)) (lns W (d - 1)) = offs (2 ^ b) G := by
    have hv := ofD_offs W (2 ^ b) G (fun x hx => (hGb x hx).1)
    have e : Nat.add s.gv (2 ^ b * rep W d) = ofD W (offs (2 ^ b) G) := by
      rw [hGl] at hv
      have : ((Nat.add s.gv (2 ^ b * rep W d) : Nat) : Int) = ((ofD W (offs (2 ^ b) G) : Nat) : Int) := by
        rw [hv, nadd, Int.natCast_add, Int.natCast_mul, hgv]
      exact_mod_cast this
    rw [e]
    exact digsU_ofD W _ (fun x hx => Nat.lt_of_lt_of_le (offs_lt _ G hGb x hx) h2T) (d - 1)
      (by rw [offs_length, hGl]; omega)
  have hFb' : ∀ x ∈ F, -((2 ^ b' : Nat) : Int) ≤ x ∧ x < ((2 ^ b' : Nat) : Int) := by
    intro x hx; have := hFb x hx; omega
  have hGb' : ∀ x ∈ G, -((2 ^ b' : Nat) : Int) ≤ x ∧ x < ((2 ^ b' : Nat) : Int) := by
    intro x hx; have := hGb x hx; omega
  simp only [prepack, hdigF, hdigG, offs_shift _ _ hTT F (fun x hx => (hFb x hx).1),
    offs_shift _ _ hTT G (fun x hx => (hGb x hx).1), PInv]
  obtain ⟨f0, ft, rfl⟩ : ∃ f0 ft, F = f0 :: ft := by
    cases F with
    | nil => simp at hFl
    | cons a l => exact ⟨a, l, rfl⟩
  obtain ⟨g0, gt, rfl⟩ : ∃ g0 gt, G = g0 :: gt := by
    cases G with
    | nil => simp at hGl; omega
    | cons a l => exact ⟨a, l, rfl⟩
  have hBpos : 0 < 2 ^ W' := Nat.two_pow_pos W'
  have hevF : 0 ≤ ev ((2 ^ W' : Nat) : Int) (f0 :: ft) := Int.le_of_lt (ev_pos _ hBpos f0 ft hF0 (by
    intro x hx; have := hFb' x (by simp [hx]); omega))
  have hevG : 0 ≤ ev ((2 ^ W' : Nat) : Int) (g0 :: gt) := Int.le_of_lt (ev_pos _ hBpos g0 gt hG0 (by
    intro x hx; have := hGb' x (by simp [hx]); omega))
  have hpF := pack_value W' (2 ^ b') (f0 :: ft) hFb' (by simp) hevF
  have hpG := pack_value W' (2 ^ b') (g0 :: gt) hGb' (by simp) hevG
  simp only [List.length_cons] at hFl hGl hpF hpG
  rw [show ft.length + 1 - 1 = d by omega] at hpF
  rw [show gt.length + 1 - 1 = d - 1 by omega, show gt.length + 1 = d by omega] at hpG
  rw [show ft.length + 1 = d + 1 by omega] at hpF
  refine ⟨by simp; omega, by simp; omega, hFb', hGb', hF0, hG0, ?_, ?_, hlf, hlg, ?_, ?_, hfs, hgs, hdm⟩
  · exact hpF
  · exact hpG
  · simp only [offs, List.map_cons, List.tail_cons]
    cases ft with
    | nil => simp at hFl; omega
    | cons f1 fs => simp only [List.map_cons, List.headD_cons]; have := hFb (f1) (by simp); omega
  · intro h2
    simp only [offs, List.map_cons, List.tail_cons]
    cases gt with
    | nil => simp at hGl; omega
    | cons g1 gs => simp only [List.map_cons, List.headD_cons]; have := hGb g1 (by simp); omega


/-! ## A whole packed run -/

/-- The lane constants of one step. -/
def stepOK (W b dh T m O HM m2 sb sW s1 s0 sm : Nat) : Bool :=
  T == 2 ^ b && m == 2 ^ W - 1 && O == 2 ^ b * rep W (dh + 1) && HM == hmask W b (dh + 1) &&
  m2 == 2 ^ (2 * b) - 1 && sb == b && sW == W && s1 == W * (dh + 1) && s0 == W * dh &&
  sm == W * (dh - 1) && decide (3 * b + 3 ≤ W)

/-- The lane constants of one repacking at degree `d`. -/
def repackOK (W b W' b' d m OF OG : Nat) (shF shG pF pG : List Nat) (OF' OG' dT : Nat) : Bool :=
  m == 2 ^ W - 1 && OF == 2 ^ b * rep W (d + 1) && OG == 2 ^ b * rep W d && shF == lns W d &&
  shG == lns W (d - 1) && pF == lns1 W' d && pG == lns1 W' (d - 1) && OF' == 2 ^ b' * rep W' (d + 1) &&
  OG' == 2 ^ b' * rep W' d && dT == 2 ^ b' - 2 ^ b && decide (b ≤ b') && decide (b + 1 ≤ W) &&
  decide (3 * b' + 3 ≤ W') && decide (1 ≤ d)

/-- A run is well formed from lanes `(W, b)` at degree `d`: each act matches the current lanes and
degree; nothing follows the step to degree 0. -/
def actsOK : Nat → Nat → Nat → Bool → List PAct → Bool
  | _, _, _, _, [] => true
  | W, b, d, ini, .step W1 b1 dh T m O HM m2 sb sW s1 s0 sm first _ :: as =>
      W1 == W && b1 == b && dh + 2 == d && first == ini && stepOK W b dh T m O HM m2 sb sW s1 s0 sm &&
      (if d = 2 then as.isEmpty else actsOK W b (d - 1) false as)
  | W, b, d, ini, .repack W1 b1 W' b' d1 m OF OG shF shG pF pG OF' OG' dT :: as =>
      W1 == W && b1 == b && d1 == d && repackOK W b W' b' d m OF OG shF shG pF pG OF' OG' dT &&
      actsOK W' b' d ini as

def nsteps : List PAct → Nat
  | [] => 0
  | .step .. :: as => nsteps as + 1
  | .repack .. :: as => nsteps as

/-- Lanes and degree after a run. -/
def aEnd : Nat → Nat → Nat → List PAct → Nat × Nat × Nat
  | W, b, d, [] => (W, b, d)
  | W, b, d, .step .. :: as => aEnd W b (d - 1) as
  | _, _, d, .repack _ _ W' b' _ _ _ _ _ _ _ _ _ _ _ :: as => aEnd W' b' d as

theorem pact_bad_le (a : PAct) (s : PSt) : s.bad ≤ (pact a s).bad := by
  cases a with
  | step W b dh T m O HM m2 sb sW s1 s0 sm first lowb =>
    simp only [pact, pstep]
    cases first <;> cases lowb <;> simp only [cond, nadd] <;> omega
  | repack => simp [pact, prepack]

theorem prun_bad_le : ∀ (acts : List PAct) (s : PSt), s.bad ≤ (prun acts s).bad
  | [], _ => Nat.le_refl _
  | a :: as, s => Nat.le_trans (pact_bad_le a s) (prun_bad_le as (pact a s))

theorem aEnd_d_of_nsteps : ∀ (as : List PAct) (W b d : Nat), nsteps as = 0 → (aEnd W b d as).2.2 = d
  | [], _, _, _, _ => rfl
  | .step .. :: _, _, _, _, h => by simp [nsteps] at h
  | .repack _ _ W' b' _ _ _ _ _ _ _ _ _ _ _ :: as, _, _, d, h => by
    simp only [nsteps] at h; simp only [aEnd]; exact aEnd_d_of_nsteps as W' b' d h

theorem pstep_fs (T m O HM m2 sb sW s1 s0 sm : Nat) (first lowb : Bool) (s : PSt) :
    (pstep T m O HM m2 sb sW s1 s0 sm first lowb s).fs = s.gs := rfl

theorem prun_spec : ∀ (acts : List PAct) (W b d : Nat) (ini : Bool) (s : PSt) (F G : List Int),
    actsOK W b d ini acts = true → PInv W b d ini s F G → (prun acts s).bad = 0 →
    ∃ F' G', PInv (aEnd W b d acts).1 (aEnd W b d acts).2.1 (aEnd W b d acts).2.2
        (ini && nsteps acts == 0) (prun acts s) F' G' ∧
      ∀ fuel, normalResultantGo (fuel + nsteps acts) ini (F.map (sg s.fs * ·)) (G.map (sg s.gs * ·)) =
        if (aEnd W b d acts).2.2 = 1 ∧ 0 < nsteps acts then some (sg (prun acts s).gs * G'.headD 0)
        else normalResultantGo fuel (ini && nsteps acts == 0) (F'.map (sg (prun acts s).fs * ·))
          (G'.map (sg (prun acts s).gs * ·))
  | [], W, b, d, ini, s, F, G, _, hI, _ => by
    refine ⟨F, G, ?_, ?_⟩
    · simpa [aEnd, nsteps, prun] using hI
    · intro fuel; simp [aEnd, nsteps, prun]
  | .step W1 b1 dh T m O HM m2 sb sW s1 s0 sm first lowb :: as, W, b, d, ini, s, F, G, hok, hI, hbad => by
    simp only [actsOK, Bool.and_eq_true, beq_iff_eq] at hok
    obtain ⟨⟨⟨⟨⟨rfl, rfl⟩, hdh⟩, rfl⟩, hst⟩, hrest⟩ := hok
    simp only [stepOK, Bool.and_eq_true, beq_iff_eq, decide_eq_true_eq] at hst
    obtain ⟨⟨⟨⟨⟨⟨⟨⟨⟨⟨hT, hm⟩, hO⟩, hHM⟩, hm2⟩, hsb⟩, hsW⟩, hs1⟩, hs0⟩, hsm⟩, hW⟩ := hst
    have hd2 : 2 ≤ d := by omega
    have hbad1 : (pstep T m O HM m2 sb sW s1 s0 sm first lowb s).bad = 0 := by
      have := prun_bad_le as (pact (.step W1 b1 dh T m O HM m2 sb sW s1 s0 sm first lowb) s)
      simp only [prun, pact] at hbad this; omega
    obtain ⟨H, hI', hspec⟩ := pstep_spec W1 b1 d first lowb s F G T m O HM m2 sb sW s1 s0 sm hT hm
      (by rw [hO]; congr 2; omega) (by rw [hHM]; congr 1; omega) hm2 hsb hsW (by rw [hs1]; congr 1; omega)
      (by rw [hs0]; congr 1; omega) (by rw [hsm]; congr 1; omega) hW hd2 hI hbad1
    by_cases hd : d = 2
    · -- the last step
      rw [if_pos hd] at hrest
      cases as with
      | cons _ _ => simp at hrest
      | nil =>
        refine ⟨G, H, ?_, ?_⟩
        · simpa [aEnd, nsteps, prun, pact] using hI'
        · intro fuel
          have := hspec fuel
          rw [if_pos hd] at this
          have hc : (aEnd W1 b1 d [PAct.step W1 b1 dh T m O HM m2 sb sW s1 s0 sm first lowb]).2.2 = 1 ∧
              0 < nsteps [PAct.step W1 b1 dh T m O HM m2 sb sW s1 s0 sm first lowb] := by
            simp [aEnd, nsteps]; omega
          rw [if_pos hc]
          simpa [nsteps, prun, pact] using this
    · rw [if_neg hd] at hrest
      have hbad2 : (prun as (pstep T m O HM m2 sb sW s1 s0 sm first lowb s)).bad = 0 := by
        simpa [prun, pact] using hbad
      obtain ⟨F', G', hI'', hspec'⟩ := prun_spec as W1 b1 (d - 1) false _ G H hrest hI' hbad2
      refine ⟨F', G', ?_, ?_⟩
      · simpa [aEnd, nsteps, prun, pact] using hI''
      · intro fuel
        have h1 := hspec (fuel + nsteps as)
        rw [if_neg hd] at h1
        have h2 := hspec' fuel
        rw [pstep_fs] at h2
        have e1 : nsteps (PAct.step W1 b1 dh T m O HM m2 sb sW s1 s0 sm first lowb :: as) = nsteps as + 1 := rfl
        have e2 : aEnd W1 b1 d (PAct.step W1 b1 dh T m O HM m2 sb sW s1 s0 sm first lowb :: as) =
            aEnd W1 b1 (d - 1) as := rfl
        have e3 : prun (PAct.step W1 b1 dh T m O HM m2 sb sW s1 s0 sm first lowb :: as) s =
            prun as (pstep T m O HM m2 sb sW s1 s0 sm first lowb s) := rfl
        rw [e1, e2, e3, show fuel + (nsteps as + 1) = fuel + nsteps as + 1 by omega, h1, h2]
        by_cases h0 : 0 < nsteps as
        · have hc : ((aEnd W1 b1 (d - 1) as).2.2 = 1 ∧ 0 < nsteps as) ↔
              ((aEnd W1 b1 (d - 1) as).2.2 = 1 ∧ 0 < nsteps as + 1) := by omega
          by_cases hh : (aEnd W1 b1 (d - 1) as).2.2 = 1
          · rw [if_pos ⟨hh, h0⟩, if_pos ⟨hh, by omega⟩]
          · rw [if_neg (by omega), if_neg (by omega)]
            simp [show (nsteps as == 0) = false by simp; omega]
        · have h00 : nsteps as = 0 := by omega
          have hend := aEnd_d_of_nsteps as W1 b1 (d - 1) h00
          rw [if_neg (by omega), if_neg (by omega)]
          simp [h00]
  | .repack W1 b1 W' b' d1 m OF OG shF shG pF pG OF' OG' dT :: as, W, b, d, ini, s, F, G, hok, hI, hbad => by
    simp only [actsOK, Bool.and_eq_true, beq_iff_eq] at hok
    obtain ⟨⟨⟨⟨rfl, rfl⟩, rfl⟩, hrp⟩, hrest⟩ := hok
    simp only [repackOK, Bool.and_eq_true, beq_iff_eq, decide_eq_true_eq] at hrp
    obtain ⟨⟨⟨⟨⟨⟨⟨⟨⟨⟨⟨⟨⟨hm, hOF⟩, hOG⟩, hshF⟩, hshG⟩, hpF⟩, hpG⟩, hOF'⟩, hOG'⟩, hdT⟩, hbb⟩, hbW⟩, hW'⟩, hd1⟩ := hrp
    have hI' := prepack_spec W1 b1 W' b' d1 ini s F G m OF OG shF shG pF pG OF' OG' dT hm hOF hOG hshF hshG
      hpF hpG hOF' hOG' hdT hbb hbW (by omega) hd1 hI
    have hbad2 : (prun as (prepack m OF OG shF shG pF pG OF' OG' dT s)).bad = 0 := by
      simpa [prun, pact] using hbad
    obtain ⟨F', G', hI'', hspec'⟩ := prun_spec as W' b' d1 ini _ F G hrest hI' hbad2
    refine ⟨F', G', by simpa [aEnd, nsteps, prun, pact] using hI'', ?_⟩
    intro fuel
    have := hspec' fuel
    exact this


/-! ## The input stage -/

/-- Derivative coefficients `k·a` for factors `ks` (the last value has factor 1). -/
def derA : List Nat → List Int → List Int
  | [], [a] => [a]
  | k :: ks, a :: as => (k : Int) * a :: derA ks as
  | _, _ => []

theorem derDigs_offs (T : Nat) : ∀ (ks : List Nat) (as : List Int), as.length = ks.length + 1 →
    (∀ k ∈ ks, 1 ≤ k) → (∀ a ∈ as, -(T : Int) ≤ a) → (∀ x ∈ derA ks as, -(T : Int) ≤ x) →
    derDigs (offs T as) ks (ks.map (fun k => (k - 1) * T)) = offs T (derA ks as)
  | [], [a], _, _, _, _ => by simp [offs, derDigs, derA]
  | [], [], h, _, _, _ => by simp at h
  | [], _ :: _ :: _, h, _, _, _ => by simp at h
  | k :: ks, [], h, _, _, _ => by simp at h
  | k :: ks, [a], h, _, _, _ => by simp at h
  | k :: ks, a :: e :: as, h, hk, ha, hx => by
    have ih := derDigs_offs T ks (e :: as) (by simpa using h) (fun k' hk' => hk k' (by simp [hk']))
      (fun a' ha' => ha a' (by simp [ha'])) (fun x hx' => hx x (by simp [derA, hx']))
    simp only [offs, List.map_cons] at ih ⊢
    simp only [derDigs, derA, List.map_cons]
    rw [ih]
    congr 1
    have h1 : 1 ≤ k := hk k (by simp)
    have h2 : -(T : Int) ≤ a := ha a (by simp)
    have h3 : -(T : Int) ≤ (k : Int) * a := hx _ (by simp [derA])
    simp only [nsub, nmul]
    have e1 : ((a + T).toNat : Int) = a + T := Int.toNat_of_nonneg (by omega)
    have e2 : ((((a + T).toNat * k - (k - 1) * T : Nat)) : Int) = (k : Int) * a + T := by
      rw [Int.ofNat_sub (by
        have : (((k - 1) * T : Nat) : Int) ≤ (((a + T).toNat * k : Nat) : Int) := by
          rw [Int.natCast_mul, Int.natCast_mul, e1, Int.ofNat_sub h1]; push_cast
          have : (k : Int) * a + T ≥ 0 := by omega
          grind
        exact_mod_cast this)]
      rw [Int.natCast_mul, Int.natCast_mul, e1, Int.ofNat_sub h1]; push_cast; grind
    omega

theorem inDig_eq (T x : Nat) (h0 : (zdec x).natAbs ≤ T) : inDig T x = (zdec x + T).toNat := by
  have h := h0
  unfold inDig zdec at *
  simp only [nsub, nadd, nmul, nshl, nshr, nand, Nat.shiftLeft_eq, Nat.shiftRight_eq_div_pow,
    Nat.and_one_is_mod, Nat.pow_one] at *
  split at h <;> rename_i hx
  · rw [if_pos hx, hx]; simp at h ⊢; omega
  · rw [if_neg hx, show x % 2 = 0 by omega]; simp at h ⊢; omega


theorem derA_mem : ∀ (ks : List Nat) (as : List Int), ∀ x ∈ derA ks as, ∃ k a, (k = 1 ∨ k ∈ ks) ∧ a ∈ as ∧ x = (k : Int) * a
  | [], [a], x, hx => by simp [derA] at hx; exact ⟨1, a, Or.inl rfl, by simp, by simp [hx]⟩
  | [], [], x, hx => by simp [derA] at hx
  | [], _ :: _ :: _, x, hx => by simp [derA] at hx
  | _ :: _, [], x, hx => by simp [derA] at hx
  | k :: ks, a :: as, x, hx => by
    simp only [derA, List.mem_cons] at hx
    rcases hx with rfl | hx
    · exact ⟨k, a, Or.inr (by simp), by simp, rfl⟩
    · obtain ⟨k', a', hk', ha', e⟩ := derA_mem ks as x hx
      exact ⟨k', a', by rcases hk' with h | h <;> simp [h], by simp [ha'], e⟩

theorem derA_length : ∀ (ks : List Nat) (as : List Int), as.length = ks.length + 1 → (derA ks as).length = as.length
  | [], [a], _ => rfl
  | [], [], h => by simp at h
  | [], _ :: _ :: _, h => by simp at h
  | _ :: _, [], h => by simp at h
  | k :: ks, a :: as, h => by simp only [derA, List.length_cons]; rw [derA_length ks as (by simpa using h)]

theorem pinit_spec (W b : Nat) (xs : List Nat) (T l0 g0 : Nat) (shF shG ks kTs : List Nat) (O25 O24 : Nat)
    (hT : T = 2 ^ b) (hl0 : l0 = 1 + 2 ^ b) (hg0 : g0 = 24 + 2 ^ b) (hshF : shF = lns1 W 24)
    (hshG : shG = lns1 W 23) (hks : ks = [23, 22, 21, 20, 19, 18, 17, 16, 15, 14, 13, 12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2])
    (hkTs : kTs = ks.map (fun k => (k - 1) * 2 ^ b)) (hO25 : O25 = 2 ^ b * rep W 25)
    (hO24 : O24 = 2 ^ b * rep W 24) (h24 : 24 < 2 ^ b) (hW : b + 1 ≤ W) (hxs : xs.length = 24)
    (hbnd : ∀ x ∈ xs, 24 * (zdec x).natAbs < 2 ^ b) :
    PInv W b 24 true (pinit T l0 g0 shF shG ks kTs O25 O24 xs) (1 :: xs.map zdec)
      (24 :: derA ks ((xs.take 23).map zdec)) := by
  subst T l0 g0 shF shG kTs O25 O24
  have hAb : ∀ a ∈ xs.map zdec, -((2 ^ b : Nat) : Int) ≤ a ∧ a < ((2 ^ b : Nat) : Int) := by
    intro a ha; simp only [List.mem_map] at ha; obtain ⟨x, hx, rfl⟩ := ha; have := hbnd x hx; omega
  have hds : xs.map (inDig (2 ^ b)) = offs (2 ^ b) (xs.map zdec) := by
    simp only [offs, List.map_map]; apply List.map_congr_left; intro x hx
    simp only [Function.comp_apply]; exact inDig_eq _ x (by have := hbnd x hx; omega)
  have hFdig : (1 + 2 ^ b) :: xs.map (inDig (2 ^ b)) = offs (2 ^ b) (1 :: xs.map zdec) := by
    rw [hds]; simp only [offs, List.map_cons]; congr 1
  have hderb : ∀ x ∈ derA ks ((xs.take 23).map zdec), -((2 ^ b : Nat) : Int) ≤ x ∧ x < ((2 ^ b : Nat) : Int) := by
    intro x hx
    obtain ⟨k, a, hk, ha, rfl⟩ := derA_mem _ _ x hx
    have hk24 : k ≤ 24 := by rcases hk with rfl | hk; · omega
                             rw [hks] at hk; simp at hk; omega
    simp only [List.mem_map] at ha
    obtain ⟨y, hy, rfl⟩ := ha
    have := hbnd y (List.mem_of_mem_take hy)
    have h1 : ((k : Int) * zdec y).natAbs ≤ 24 * (zdec y).natAbs := by
      rw [Int.natAbs_mul, Int.natAbs_natCast]; exact Nat.mul_le_mul_right _ hk24
    omega
  have hA23 : ∀ a ∈ (xs.take 23).map zdec, -((2 ^ b : Nat) : Int) ≤ a := by
    intro a ha
    simp only [List.mem_map] at ha
    obtain ⟨x, hx, rfl⟩ := ha
    exact (hAb _ (List.mem_map_of_mem (List.mem_of_mem_take hx))).1
  have hl23 : ((xs.take 23).map zdec).length = ks.length + 1 := by rw [hks]; simp [hxs]
  have hGdig : (24 + 2 ^ b) :: derDigs ((xs.map (inDig (2 ^ b))).take 23) ks (ks.map (fun k => (k - 1) * 2 ^ b))
      = offs (2 ^ b) (24 :: derA ks ((xs.take 23).map zdec)) := by
    rw [hds, show (offs (2 ^ b) (xs.map zdec)).take 23 = offs (2 ^ b) ((xs.take 23).map zdec) by
      simp [offs, List.map_take]]
    rw [derDigs_offs (2 ^ b) ks _ hl23 (by rw [hks]; decide) hA23 (fun x hx => (hderb x hx).1)]
    simp only [offs, List.map_cons]; congr 1
  have hFl : (1 :: xs.map zdec).length = 25 := by simp [hxs]
  have hGl : (24 :: derA ks ((xs.take 23).map zdec)).length = 24 := by
    simp only [List.length_cons]; rw [derA_length _ _ hl23]; simp [hxs]
  have hFb : ∀ x ∈ 1 :: xs.map zdec, -((2 ^ b : Nat) : Int) ≤ x ∧ x < ((2 ^ b : Nat) : Int) := by
    intro x hx; simp only [List.mem_cons] at hx; rcases hx with rfl | hx
    · omega
    · exact hAb x hx
  have hGb : ∀ x ∈ 24 :: derA ks ((xs.take 23).map zdec), -((2 ^ b : Nat) : Int) ≤ x ∧ x < ((2 ^ b : Nat) : Int) := by
    intro x hx; simp only [List.mem_cons] at hx; rcases hx with rfl | hx
    · omega
    · exact hderb x hx
  have hB := Nat.two_pow_pos W
  have hevF := ev_pos _ hB 1 (xs.map zdec) (by omega) (by
    intro x hx; have := hAb x hx; have := Nat.pow_lt_pow_right (show 1 < 2 by decide) (show b < W by omega); omega)
  have hevG := ev_pos _ hB 24 (derA ks ((xs.take 23).map zdec)) (by omega) (by
    intro x hx; have := hderb x hx; have := Nat.pow_lt_pow_right (show 1 < 2 by decide) (show b < W by omega); omega)
  have hpF := pack_value W (2 ^ b) (1 :: xs.map zdec) hFb (by simp) (Int.le_of_lt hevF)
  have hpG := pack_value W (2 ^ b) (24 :: derA ks ((xs.take 23).map zdec)) hGb (by simp) (Int.le_of_lt hevG)
  rw [hFl] at hpF; rw [hGl] at hpG
  have hgs : derDigs ((xs.map (inDig (2 ^ b))).take 23) ks (ks.map (fun k => (k - 1) * 2 ^ b))
      = offs (2 ^ b) (derA ks ((xs.take 23).map zdec)) := by
    have := hGdig; simp only [offs, List.map_cons] at this ⊢; exact (List.cons.inj this).2
  simp only [pinit, PInv]
  rw [hFdig, hGdig, hgs, hds]
  refine ⟨hFl, hGl, hFb, hGb, by simp, by simp, hpF, hpG, by simp, by simp, ?_, ?_, by decide, by decide, by simp⟩
  · simp only [List.tail_cons]
    cases xs with
    | nil => simp at hxs
    | cons x xs' => simp only [offs, List.map_cons, List.headD_cons]; have := hAb (zdec x) (by simp); omega
  · intro _
    simp only [List.tail_cons]
    cases hd : derA ks ((xs.take 23).map zdec) with
    | nil => rw [hd] at hGl; simp at hGl
    | cons y ys => simp only [offs, List.map_cons, List.headD_cons]; have := hderb y (by rw [hd]; simp); omega


/-! ## Size of the generated coefficients -/

theorem cnc_bound (w words word : Nat) (hw : 1 ≤ w) (hww : w ≤ 64 * words) (hword : word < 2 ^ (64 * words)) :
    (centeredNonzeroCoeff w words word).natAbs ≤ 2 ^ (w - 1) := by
  have hv : word >>> (64 * words - w) < 2 ^ w := by
    rw [Nat.shiftRight_eq_div_pow, Nat.div_lt_iff_lt_mul (Nat.two_pow_pos _), ← Nat.pow_add,
      show w + (64 * words - w) = 64 * words by omega]
    exact hword
  have e : 2 ^ w = 2 * 2 ^ (w - 1) := by
    rw [← Nat.pow_succ']; congr 1; omega
  have hp1 : 1 ≤ 2 ^ (w - 1) := Nat.one_le_two_pow
  unfold centeredNonzeroCoeff
  simp only [Int.ofNat_eq_natCast]
  generalize word >>> (64 * words - w) = v at *
  generalize 2 ^ (w - 1) = p at *
  split
  · simp; omega
  · omega

theorem width_bounds (k i : Nat) (hk : 2 ≤ k) : 2 ≤ coefficientWidth k i ∧ coefficientWidth k i ≤ k := by
  unfold coefficientWidth clampWidth
  split <;> simp only <;> omega

theorem coeffs_bound (k : Nat) (hk : 2 ≤ k) : ∀ count index state,
    ∀ a ∈ coefficientsFrom count k index state, a.natAbs ≤ 2 ^ (k - 1)
  | 0, _, _ => by simp [coefficientsFrom]
  | count + 1, index, state => by
    intro a ha
    simp only [coefficientsFrom, List.mem_cons] at ha
    rcases ha with rfl | ha
    · obtain ⟨h2, hk'⟩ := width_bounds k index hk
      have hwords : 1 ≤ (coefficientWidth k index + 63) / 64 := by omega
      have hlt := collect_lt ((coefficientWidth k index + 63) / 64) 0 state
      rcases hlt with hlt | hlt
      · rw [Nat.zero_add] at hlt
        have := cnc_bound (coefficientWidth k index) ((coefficientWidth k index + 63) / 64)
          (collectCoeffWord ((coefficientWidth k index + 63) / 64) 0 state).1 (by omega) (by omega) hlt
        exact Nat.le_trans this (Nat.pow_le_pow_right (by decide) (by omega))
      · omega
    · exact coeffs_bound k hk count (index + 1) _ a ha

theorem polyOf_bound (n : Nat) : ∀ a ∈ polyOf n, a.natAbs ≤ 2 ^ (kbitsOf n - 1) := by
  have hk : 2 ≤ kbitsOf n := by unfold kbitsOf; split <;> decide
  intro a ha
  simp only [polyOf, List.mem_cons] at ha
  rcases ha with rfl | ha
  · simp; exact Nat.one_le_two_pow
  · exact coeffs_bound _ hk 24 1 _ a ha


/-! ## Reading off results -/

theorem zdec_res (v s : Nat) (hs : s < 2) : zdec (Nat.add (Nat.shiftLeft v 1) s) = sg s * v := by
  unfold zdec sg
  simp only [nadd, nshl, Nat.shiftLeft_eq, Nat.pow_one]
  rcases (by omega : s = 0 ∨ s = 1) with rfl | rfl
  · rw [if_neg (by omega)]; simp
  · rw [if_pos (by omega)]; simp; omega

theorem zdig_val (T s : Nat) (x : Int) (hs : s < 2) (hx : -(T : Int) ≤ x) :
    zdec (zdig T s (x + (T : Int)).toNat) = sg s * x := by
  unfold zdig zdec sg
  simp only [nadd, nsub, nshl, nxor, Nat.shiftLeft_eq, Nat.pow_one]
  generalize hd : (x + (T : Int)).toNat = δ
  have hδ : (δ : Int) = x + T := by rw [← hd]; exact Int.toNat_of_nonneg (by omega)
  have hn : 1 - (1 - (T - δ)) < 2 := by omega
  rw [xor_bits _ _ hn hs]
  rcases (by omega : s = 0 ∨ s = 1) with rfl | rfl <;> by_cases hneg : δ < T
  · rw [show 1 - (1 - (T - δ)) = 1 by omega]; rw [if_pos (by omega)]; push_cast; omega
  · rw [show 1 - (1 - (T - δ)) = 0 by omega]; rw [if_neg (by omega)]; push_cast; omega
  · rw [show 1 - (1 - (T - δ)) = 1 by omega]; rw [if_neg (by omega)]; push_cast; omega
  · rw [show 1 - (1 - (T - δ)) = 0 by omega]; rw [if_pos (by omega)]; push_cast; omega

theorem unpackT_spec (W b d : Nat) (T m O : Nat) (shs : List Nat) (v sb : Nat) (S : List Int)
    (hT : T = 2 ^ b) (hm : m = 2 ^ W - 1) (hO : O = 2 ^ b * rep W (d + 1)) (hshs : shs = lns W d)
    (hW : b + 1 ≤ W) (hS : ∀ x ∈ S, -((2 ^ b : Nat) : Int) ≤ x ∧ x < ((2 ^ b : Nat) : Int))
    (hl : S.length = d + 1) (hv : (v : Int) = ev ((2 ^ W : Nat) : Int) S) (hs : sb < 2) :
    (unpackT T m O shs v sb).map zdec = S.map (sg sb * ·) ∧ (unpackT T m O shs v sb).length = d + 1 := by
  subst T m O shs
  have h2T : 2 * 2 ^ b ≤ 2 ^ W := by
    have := Nat.pow_le_pow_right (show 0 < 2 by decide) hW; rw [Nat.pow_succ] at this; omega
  have hval := ofD_offs W (2 ^ b) S (fun x hx => (hS x hx).1)
  have e : Nat.add v (2 ^ b * rep W (d + 1)) = ofD W (offs (2 ^ b) S) := by
    rw [hl] at hval
    have : ((Nat.add v (2 ^ b * rep W (d + 1)) : Nat) : Int) = ((ofD W (offs (2 ^ b) S) : Nat) : Int) := by
      rw [hval, nadd, Int.natCast_add, Int.natCast_mul, hv]
    exact_mod_cast this
  have hdig : digsU (2 ^ W - 1) (Nat.add v (2 ^ b * rep W (d + 1))) (lns W d) = offs (2 ^ b) S := by
    rw [e]; exact digsU_ofD W _ (fun x hx => Nat.lt_of_lt_of_le (offs_lt _ S hS x hx) h2T) d (by rw [offs_length, hl])
  unfold unpackT
  rw [hdig]
  refine ⟨?_, by simp [offs, hl]⟩
  simp only [offs, List.map_map]
  apply List.map_congr_left
  intro x hx
  exact zdig_val _ _ x hs (hS x hx).1

theorem derivHL_eq (a1 a2 a3 a4 a5 a6 a7 a8 a9 a10 a11 a12 a13 a14 a15 a16 a17 a18 a19 a20 a21 a22 a23 a24 : Int) :
    derivHL [1, a1, a2, a3, a4, a5, a6, a7, a8, a9, a10, a11, a12, a13, a14, a15, a16, a17, a18, a19, a20, a21, a22, a23, a24]
      = 24 :: derA [23, 22, 21, 20, 19, 18, 17, 16, 15, 14, 13, 12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2]
        [a1, a2, a3, a4, a5, a6, a7, a8, a9, a10, a11, a12, a13, a14, a15, a16, a17, a18, a19, a20, a21, a22, a23] := by
  simp [derivHL, derA, List.range, List.range.loop]

/-- The specification's normal resultant from the normal run started at `P`, `P'`. -/
theorem normalResultant_of_go (P : List Int) (hP : P.length = 25) (h1 : P.headD 0 = 1)
    (r : Option Int) (h : normalResultantGo 25 true P (derivHL P) = r) : normalResultant P (derivHL P) = r := by
  obtain ⟨p0, ps, rfl⟩ : ∃ p0 ps, P = p0 :: ps := by
    cases P with
    | nil => simp at hP
    | cons a l => exact ⟨a, l, rfl⟩
  simp only [List.headD_cons] at h1
  subst h1
  have hd : derivHL (1 :: ps) = 24 * 1 :: (derivHL (1 :: ps)).tail := by
    simp [derivHL, List.length_cons] at hP ⊢
    rw [hP]; simp [List.range, List.range.loop]
  have hdl : (derivHL (1 :: ps)).length = 24 := by simp [derivHL]; simpa using hP
  unfold normalResultant
  rw [trim_cons 1 ps (by decide), hd, trim_cons _ _ (by decide)]
  rw [← hd]
  simp only [List.length_cons, hdl]
  have hl : ps.length = 24 := by simpa using hP
  have hne : (derivHL (1 :: ps)).isEmpty = false := by
    cases hq : derivHL (1 :: ps) with
    | nil => rw [hq] at hdl; simp at hdl
    | cons _ _ => rfl
  rw [hne, hl]
  exact h


/-! ## Whole runs -/

theorem map_one_mul (l : List Int) : l.map (sg 0 * ·) = l := by
  conv => rhs; rw [← List.map_id l]
  apply List.map_congr_left; intro x _; simp [sg]

/-- All 23 steps packed. -/
theorem full_run_spec (acts : List PAct) (W b : Nat) (s0 : PSt) (F G : List Int) (Wend bend : Nat)
    (hok : actsOK W b 24 true acts = true) (hend : aEnd W b 24 acts = (Wend, bend, 1)) (hn : nsteps acts = 23)
    (hI : PInv W b 24 true s0 F G) (hfs : s0.fs = 0) (hgs : s0.gs = 0) (hbad : (prun acts s0).bad = 0) :
    normalResultantGo 25 true F G = some (zdec (Nat.add (Nat.shiftLeft (prun acts s0).gv 1) (prun acts s0).gs)) := by
  obtain ⟨F', G', hI', hsp⟩ := prun_spec acts W b 24 true s0 F G hok hI hbad
  have h := hsp 2
  rw [hend, hn, hfs, hgs, map_one_mul, map_one_mul] at h
  rw [hend] at hI'
  dsimp only at hI' h
  rw [if_pos ⟨rfl, by decide⟩] at h
  rw [show (2 + 23 : Nat) = 25 from rfl] at h
  rw [h]
  obtain ⟨_, hGl, _, _, _, _, _, hgv, _, _, _, _, _, hgs', _⟩ := hI'
  obtain ⟨g, rfl⟩ : ∃ g, G' = [g] := by
    match G', hGl with
    | [g], _ => exact ⟨g, rfl⟩
  simp only [ev, List.length_nil, Int.pow_zero, Int.mul_one, Int.add_zero] at hgv
  rw [zdec_res _ _ hgs', hgv]
  rfl

/-- A packed prefix ending at degree `dend`, then `k = dend − 1` encoded v7 steps. -/
theorem hyb_run_spec (acts : List PAct) (W b : Nat) (s0 : PSt) (F G : List Int) (Wend bend dend k : Nat)
    (hok : actsOK W b 24 true acts = true) (hend : aEnd W b 24 acts = (Wend, bend, dend))
    (hn : nsteps acts + dend = 24) (hk : k + 1 = dend) (hd2 : 2 ≤ dend) (hd22 : dend ≤ 22)
    (hI : PInv W b 24 true s0 F G) (hfs : s0.fs = 0) (hgs : s0.gs = 0) (hbad0 : (prun acts s0).bad = 0)
    (T m OF OG : Nat) (shF shG : List Nat) (hT : T = 2 ^ bend) (hm : m = 2 ^ Wend - 1)
    (hOF : OF = 2 ^ bend * rep Wend (dend + 1)) (hOG : OG = 2 ^ bend * rep Wend dend)
    (hshF : shF = lns Wend dend) (hshG : shG = lns Wend (dend - 1)) (hW : bend + 1 ≤ Wend)
    (hrun : (run k (unpackT T m OF shF (prun acts s0).fv (prun acts s0).fs)
      (unpackT T m OG shG (prun acts s0).gv (prun acts s0).gs) (prun acts s0).bad).2 = 0) :
    normalResultantGo 25 true F G = some (zdec (run k (unpackT T m OF shF (prun acts s0).fv (prun acts s0).fs)
      (unpackT T m OG shG (prun acts s0).gv (prun acts s0).gs) (prun acts s0).bad).1) := by
  obtain ⟨F', G', hI', hsp⟩ := prun_spec acts W b 24 true s0 F G hok hI hbad0
  have hns : 0 < nsteps acts := by omega
  have h := hsp (k + 2)
  rw [hend, hfs, hgs, map_one_mul, map_one_mul] at h
  rw [hend] at hI'
  dsimp only at hI' h
  rw [if_neg (by omega)] at h
  rw [show k + 2 + nsteps acts = 25 by omega] at h
  rw [h, show (true && nsteps acts == 0) = false by simp; omega]
  obtain ⟨hFl, hGl, hFb, hGb, hF0, hG0, hfv, hgv, _, _, _, _, hfs', hgs', _⟩ := hI'
  obtain ⟨uF, hlF⟩ := unpackT_spec Wend bend dend T m OF shF _ _ F' hT hm hOF hshF hW hFb hFl hfv hfs'
  obtain ⟨uG, hlG⟩ := unpackT_spec Wend bend (dend - 1) T m OG shG _ _ G' hT hm
    (by rw [hOG]; congr 2; omega) hshG hW hGb (by omega) hgv hgs'
  rw [← uF, ← uG]
  apply run_spec k _ _ _ (k + 2) (by omega) (by rw [hlG]; omega) (by rw [hlF]; omega) (by omega)
  · rw [uF, headD_mul]
    exact Int.mul_ne_zero (sg_ne _) (by omega)
  · rw [uG, headD_mul]
    exact Int.mul_ne_zero (sg_ne _) (by omega)
  · exact hrun



theorem run_bad0 (k : Nat) (F G : List Nat) (bad : Nat) (h : (run k F G bad).2 = 0) : bad = 0 := by
  have := run_snd_ge k F G bad; omega


/-! ## Band 15 -/

theorem init15_spec (xs : List Nat) (hxs : xs.length = 24) (hb : ∀ x ∈ xs, 24 * (zdec x).natAbs < 2 ^ 363) :
    PInv 1092 363 24 true (init15 xs) (1 :: xs.map zdec) (24 :: derA [23, 22, 21, 20, 19, 18, 17, 16, 15, 14, 13, 12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2] ((xs.take 23).map zdec)) := by
  unfold init15
  exact pinit_spec 1092 363 xs _ _ _ _ _ _ _ _ _ (by decide +kernel) (by decide +kernel) (by decide +kernel)
    (by decide +kernel) (by decide +kernel) rfl (by decide +kernel) (by decide +kernel) (by decide +kernel)
    (by decide +kernel) (by decide) hxs hb

theorem acts15_ok : actsOK 1092 363 24 true acts15 = true := by decide +kernel

theorem pk15_ok (f0 f1 f2 f3 f4 f5 f6 f7 f8 f9 f10 f11 f12 f13 f14 f15 f16 f17 f18 f19 f20 f21 f22 f23 f24 : Nat) (h0 : zdec f0 = 1) (hb : ∀ x ∈ [f1, f2, f3, f4, f5, f6, f7, f8, f9, f10, f11, f12, f13, f14, f15, f16, f17, f18, f19, f20, f21, f22, f23, f24], 24 * (zdec x).natAbs < 2 ^ 363)
    (hbad : (pkDag15 f0 f1 f2 f3 f4 f5 f6 f7 f8 f9 f10 f11 f12 f13 f14 f15 f16 f17 f18 f19 f20 f21 f22 f23 f24).2 = 0) :
    normalResultant ([f0, f1, f2, f3, f4, f5, f6, f7, f8, f9, f10, f11, f12, f13, f14, f15, f16, f17, f18, f19, f20, f21, f22, f23, f24].map zdec) (derivHL ([f0, f1, f2, f3, f4, f5, f6, f7, f8, f9, f10, f11, f12, f13, f14, f15, f16, f17, f18, f19, f20, f21, f22, f23, f24].map zdec)) = some (zdec (pkDag15 f0 f1 f2 f3 f4 f5 f6 f7 f8 f9 f10 f11 f12 f13 f14 f15 f16 f17 f18 f19 f20 f21 f22 f23 f24).1) := by
  rw [pkDag15_struct f0 f1 f2 f3 f4 f5 f6 f7 f8 f9 f10 f11 f12 f13 f14 f15 f16 f17 f18 f19 f20 f21 f22 f23 f24] at hbad ⊢
  unfold pkRun15 at hbad ⊢
  dsimp only at hbad ⊢
  have hfs : (init15 [f1, f2, f3, f4, f5, f6, f7, f8, f9, f10, f11, f12, f13, f14, f15, f16, f17, f18, f19, f20, f21, f22, f23, f24]).fs = 0 := by unfold init15 pinit; rfl
  have hgs : (init15 [f1, f2, f3, f4, f5, f6, f7, f8, f9, f10, f11, f12, f13, f14, f15, f16, f17, f18, f19, f20, f21, f22, f23, f24]).gs = 0 := by unfold init15 pinit; rfl
  have hend : aEnd 1092 363 24 acts15 = (1857, 618, 1) := by decide +kernel
  have hn : nsteps acts15 = 23 := by decide +kernel
  have hF : [f0, f1, f2, f3, f4, f5, f6, f7, f8, f9, f10, f11, f12, f13, f14, f15, f16, f17, f18, f19, f20, f21, f22, f23, f24].map zdec = 1 :: [f1, f2, f3, f4, f5, f6, f7, f8, f9, f10, f11, f12, f13, f14, f15, f16, f17, f18, f19, f20, f21, f22, f23, f24].map zdec := by simp [h0]
  rw [hF]
  apply normalResultant_of_go _ (by simp) rfl
  have hG := derivHL_eq (zdec f1) (zdec f2) (zdec f3) (zdec f4) (zdec f5) (zdec f6) (zdec f7) (zdec f8) (zdec f9) (zdec f10) (zdec f11) (zdec f12) (zdec f13) (zdec f14) (zdec f15) (zdec f16) (zdec f17) (zdec f18) (zdec f19) (zdec f20) (zdec f21) (zdec f22) (zdec f23) (zdec f24)
  simp only [List.map_cons, List.map_nil] at hG ⊢
  rw [hG]
  exact full_run_spec acts15 1092 363 _ _ _ 1857 618 acts15_ok hend hn
    (init15_spec [f1, f2, f3, f4, f5, f6, f7, f8, f9, f10, f11, f12, f13, f14, f15, f16, f17, f18, f19, f20, f21, f22, f23, f24] rfl hb) hfs hgs hbad

/-! ## Band 205 -/

theorem init205_spec (xs : List Nat) (hxs : xs.length = 24) (hb : ∀ x ∈ xs, 24 * (zdec x).natAbs < 2 ^ 704) :
    PInv 2115 704 24 true (init205 xs) (1 :: xs.map zdec) (24 :: derA [23, 22, 21, 20, 19, 18, 17, 16, 15, 14, 13, 12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2] ((xs.take 23).map zdec)) := by
  unfold init205
  exact pinit_spec 2115 704 xs _ _ _ _ _ _ _ _ _ (by decide +kernel) (by decide +kernel) (by decide +kernel)
    (by decide +kernel) (by decide +kernel) rfl (by decide +kernel) (by decide +kernel) (by decide +kernel)
    (by decide +kernel) (by decide) hxs hb

theorem acts205_ok : actsOK 2115 704 24 true acts205 = true := by decide +kernel

theorem pk205_ok (f0 f1 f2 f3 f4 f5 f6 f7 f8 f9 f10 f11 f12 f13 f14 f15 f16 f17 f18 f19 f20 f21 f22 f23 f24 : Nat) (h0 : zdec f0 = 1) (hb : ∀ x ∈ [f1, f2, f3, f4, f5, f6, f7, f8, f9, f10, f11, f12, f13, f14, f15, f16, f17, f18, f19, f20, f21, f22, f23, f24], 24 * (zdec x).natAbs < 2 ^ 704)
    (hbad : (pkDag205 f0 f1 f2 f3 f4 f5 f6 f7 f8 f9 f10 f11 f12 f13 f14 f15 f16 f17 f18 f19 f20 f21 f22 f23 f24).2 = 0) :
    normalResultant ([f0, f1, f2, f3, f4, f5, f6, f7, f8, f9, f10, f11, f12, f13, f14, f15, f16, f17, f18, f19, f20, f21, f22, f23, f24].map zdec) (derivHL ([f0, f1, f2, f3, f4, f5, f6, f7, f8, f9, f10, f11, f12, f13, f14, f15, f16, f17, f18, f19, f20, f21, f22, f23, f24].map zdec)) = some (zdec (pkDag205 f0 f1 f2 f3 f4 f5 f6 f7 f8 f9 f10 f11 f12 f13 f14 f15 f16 f17 f18 f19 f20 f21 f22 f23 f24).1) := by
  rw [pkDag205_struct f0 f1 f2 f3 f4 f5 f6 f7 f8 f9 f10 f11 f12 f13 f14 f15 f16 f17 f18 f19 f20 f21 f22 f23 f24] at hbad ⊢
  unfold pkRun205 at hbad ⊢
  dsimp only at hbad ⊢
  have hfs : (init205 [f1, f2, f3, f4, f5, f6, f7, f8, f9, f10, f11, f12, f13, f14, f15, f16, f17, f18, f19, f20, f21, f22, f23, f24]).fs = 0 := by unfold init205 pinit; rfl
  have hgs : (init205 [f1, f2, f3, f4, f5, f6, f7, f8, f9, f10, f11, f12, f13, f14, f15, f16, f17, f18, f19, f20, f21, f22, f23, f24]).gs = 0 := by unfold init205 pinit; rfl
  have hend : aEnd 2115 704 24 acts205 = (6159, 2052, 10) := by decide +kernel
  have hn : nsteps acts205 + 10 = 24 := by decide +kernel
  have hF : [f0, f1, f2, f3, f4, f5, f6, f7, f8, f9, f10, f11, f12, f13, f14, f15, f16, f17, f18, f19, f20, f21, f22, f23, f24].map zdec = 1 :: [f1, f2, f3, f4, f5, f6, f7, f8, f9, f10, f11, f12, f13, f14, f15, f16, f17, f18, f19, f20, f21, f22, f23, f24].map zdec := by simp [h0]
  have hbad0 : (prun acts205 (init205 [f1, f2, f3, f4, f5, f6, f7, f8, f9, f10, f11, f12, f13, f14, f15, f16, f17, f18, f19, f20, f21, f22, f23, f24])).bad = 0 := run_bad0 _ _ _ _ hbad
  rw [hF]
  apply normalResultant_of_go _ (by simp) rfl
  have hG := derivHL_eq (zdec f1) (zdec f2) (zdec f3) (zdec f4) (zdec f5) (zdec f6) (zdec f7) (zdec f8) (zdec f9) (zdec f10) (zdec f11) (zdec f12) (zdec f13) (zdec f14) (zdec f15) (zdec f16) (zdec f17) (zdec f18) (zdec f19) (zdec f20) (zdec f21) (zdec f22) (zdec f23) (zdec f24)
  simp only [List.map_cons, List.map_nil] at hG ⊢
  rw [hG]
  exact hyb_run_spec acts205 2115 704 _ _ _ 6159 2052 10 9 acts205_ok hend hn rfl (by decide) (by decide)
    (init205_spec [f1, f2, f3, f4, f5, f6, f7, f8, f9, f10, f11, f12, f13, f14, f15, f16, f17, f18, f19, f20, f21, f22, f23, f24] rfl hb) hfs hgs hbad0 _ _ _ _ _ _ (by decide +kernel) (by decide +kernel)
    (by decide +kernel) (by decide +kernel) (by decide +kernel) (by decide +kernel) (by decide) hbad



theorem appL_25 (k : Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Int) (d : Int) (f0 f1 f2 f3 f4 f5 f6 f7 f8 f9 f10 f11 f12 f13 f14 f15 f16 f17 f18 f19 f20 f21 f22 f23 f24 : Nat) : appL k d [f0, f1, f2, f3, f4, f5, f6, f7, f8, f9, f10, f11, f12, f13, f14, f15, f16, f17, f18, f19, f20, f21, f22, f23, f24] = k f0 f1 f2 f3 f4 f5 f6 f7 f8 f9 f10 f11 f12 f13 f14 f15 f16 f17 f18 f19 f20 f21 f22 f23 f24 := rfl

theorem finish8_zero (r : Nat × Nat) (fb : Int) (h : r.2 = 0) : finish8 r fb = zdec r.1 := by
  unfold finish8; rw [h]; rfl

theorem finish8_succ (r : Nat × Nat) (fb : Int) (m : Nat) (h : r.2 = m + 1) : finish8 r fb = fb := by
  unfold finish8; rw [h]

theorem kont15_def (n f0 f1 f2 f3 f4 f5 f6 f7 f8 f9 f10 f11 f12 f13 f14 f15 f16 f17 f18 f19 f20 f21 f22 f23 f24 : Nat) : kont15 n f0 f1 f2 f3 f4 f5 f6 f7 f8 f9 f10 f11 f12 f13 f14 f15 f16 f17 f18 f19 f20 f21 f22 f23 f24 = finish8 (pkDag15 f0 f1 f2 f3 f4 f5 f6 f7 f8 f9 f10 f11 f12 f13 f14 f15 f16 f17 f18 f19 f20 f21 f22 f23 f24) (kont n f0 f1 f2 f3 f4 f5 f6 f7 f8 f9 f10 f11 f12 f13 f14 f15 f16 f17 f18 f19 f20 f21 f22 f23 f24) := rfl

theorem kont205_def (n f0 f1 f2 f3 f4 f5 f6 f7 f8 f9 f10 f11 f12 f13 f14 f15 f16 f17 f18 f19 f20 f21 f22 f23 f24 : Nat) : kont205 n f0 f1 f2 f3 f4 f5 f6 f7 f8 f9 f10 f11 f12 f13 f14 f15 f16 f17 f18 f19 f20 f21 f22 f23 f24 = finish8 (pkDag205 f0 f1 f2 f3 f4 f5 f6 f7 f8 f9 f10 f11 f12 f13 f14 f15 f16 f17 f18 f19 f20 f21 f22 f23 f24) (kont n f0 f1 f2 f3 f4 f5 f6 f7 f8 f9 f10 f11 f12 f13 f14 f15 f16 f17 f18 f19 f20 f21 f22 f23 f24) := rfl

theorem kont15_ok (n : Nat) (hk : kbitsOf n = 15) : appL (kont15 n) (discSpec n) (genF n) = discSpec n := by
  have hlen : (genF n).length = 25 := by unfold genF; simp [genGo_length]
  have hspec := genF_spec n
  have hfd := fastDisc_spec n
  have hbnd := polyOf_bound n
  rw [hk] at hbnd
  unfold fastDisc at hfd
  generalize genF n = L at hlen hspec hfd
  match L, hlen with
  | [f0, f1, f2, f3, f4, f5, f6, f7, f8, f9, f10, f11, f12, f13, f14, f15, f16, f17, f18, f19, f20, f21, f22, f23, f24], _ =>
    rw [appL_25] at hfd ⊢
    rw [kont15_def]
    have h0 : zdec f0 = 1 := by
      have := congrArg (fun l => l.headD 0) hspec
      simp only [List.map_cons, List.headD_cons] at this
      rw [this]; rfl
    have key := pk15_ok f0 f1 f2 f3 f4 f5 f6 f7 f8 f9 f10 f11 f12 f13 f14 f15 f16 f17 f18 f19 f20 f21 f22 f23 f24 h0
    generalize pkDag15 f0 f1 f2 f3 f4 f5 f6 f7 f8 f9 f10 f11 f12 f13 f14 f15 f16 f17 f18 f19 f20 f21 f22 f23 f24 = r at key ⊢
    cases h : r.2 with
    | succ m => rw [finish8_succ r _ m h]; exact hfd
    | zero =>
      rw [finish8_zero r _ h]
      have hb : ∀ x ∈ [f1, f2, f3, f4, f5, f6, f7, f8, f9, f10, f11, f12, f13, f14, f15, f16, f17, f18, f19, f20, f21, f22, f23, f24], 24 * (zdec x).natAbs < 2 ^ 363 := by
        intro x hx
        have := hbnd (zdec x) (by rw [← hspec]; exact List.mem_map_of_mem (List.mem_cons_of_mem _ hx))
        have : 24 * 2 ^ (15 - 1) < 2 ^ 363 := by decide +kernel
        omega
      have hres := key hb h
      unfold discSpec
      rw [← hspec]
      exact (disc_eq _ (by simp) _ hres).symm

theorem kont205_ok (n : Nat) (hk : kbitsOf n = 205) : appL (kont205 n) (discSpec n) (genF n) = discSpec n := by
  have hlen : (genF n).length = 25 := by unfold genF; simp [genGo_length]
  have hspec := genF_spec n
  have hfd := fastDisc_spec n
  have hbnd := polyOf_bound n
  rw [hk] at hbnd
  unfold fastDisc at hfd
  generalize genF n = L at hlen hspec hfd
  match L, hlen with
  | [f0, f1, f2, f3, f4, f5, f6, f7, f8, f9, f10, f11, f12, f13, f14, f15, f16, f17, f18, f19, f20, f21, f22, f23, f24], _ =>
    rw [appL_25] at hfd ⊢
    rw [kont205_def]
    have h0 : zdec f0 = 1 := by
      have := congrArg (fun l => l.headD 0) hspec
      simp only [List.map_cons, List.headD_cons] at this
      rw [this]; rfl
    have key := pk205_ok f0 f1 f2 f3 f4 f5 f6 f7 f8 f9 f10 f11 f12 f13 f14 f15 f16 f17 f18 f19 f20 f21 f22 f23 f24 h0
    generalize pkDag205 f0 f1 f2 f3 f4 f5 f6 f7 f8 f9 f10 f11 f12 f13 f14 f15 f16 f17 f18 f19 f20 f21 f22 f23 f24 = r at key ⊢
    cases h : r.2 with
    | succ m => rw [finish8_succ r _ m h]; exact hfd
    | zero =>
      rw [finish8_zero r _ h]
      have hb : ∀ x ∈ [f1, f2, f3, f4, f5, f6, f7, f8, f9, f10, f11, f12, f13, f14, f15, f16, f17, f18, f19, f20, f21, f22, f23, f24], 24 * (zdec x).natAbs < 2 ^ 704 := by
        intro x hx
        have := hbnd (zdec x) (by rw [← hspec]; exact List.mem_map_of_mem (List.mem_cons_of_mem _ hx))
        have : 24 * 2 ^ (205 - 1) < 2 ^ 704 := by decide +kernel
        omega
      have hres := key hb h
      unfold discSpec
      rw [← hspec]
      exact (disc_eq _ (by simp) _ hres).symm


/-! ## Band 3484 (v9) -/

theorem zdec_v9 : V9.zdec = zdec := rfl

theorem coeffs_wbound (k : Nat) (hk : 2 ≤ k) : ∀ count index state i, i < count →
    ((coefficientsFrom count k index state).getD i 0).natAbs ≤ 2 ^ (coefficientWidth k (index + i) - 1)
  | 0, _, _, i, hi => absurd hi (Nat.not_lt_zero _)
  | count + 1, index, state, 0, _ => by
    simp only [coefficientsFrom, List.getD_cons_zero, Nat.add_zero]
    obtain ⟨h2, hk'⟩ := width_bounds k index hk
    have hlt := collect_lt ((coefficientWidth k index + 63) / 64) 0 state
    rcases hlt with hlt | hlt
    · rw [Nat.zero_add] at hlt
      exact cnc_bound (coefficientWidth k index) ((coefficientWidth k index + 63) / 64)
        (collectCoeffWord ((coefficientWidth k index + 63) / 64) 0 state).1 (by omega) (by omega) hlt
    · omega
  | count + 1, index, state, i + 1, hi => by
    simp only [coefficientsFrom, List.getD_cons_succ]
    rw [show index + (i + 1) = index + 1 + i by omega]
    exact coeffs_wbound k hk count (index + 1) _ i (by omega)

theorem getD_zdec : ∀ (l : List Nat) (j : Nat), zdec (l.getD j 0) = (l.map zdec).getD j 0
  | [], _ => by simp [zdec_zero]
  | _ :: _, 0 => rfl
  | _ :: l, j + 1 => by simp only [List.getD_cons_succ, List.map_cons]; exact getD_zdec l j

theorem polyOf_wbound (n : Nat) (hk : kbitsOf n = 3484) : ∀ e, (V9.fX (genF n) e).natAbs ≤ V9.FbN e := by
  intro e
  unfold V9.fX V9.FbN
  by_cases he : e ≤ 24
  · rw [if_pos he, zdec_v9, getD_zdec, genF_spec n]
    unfold polyOf; rw [hk]
    by_cases h24 : e = 24
    · subst h24; simp
    · rw [if_neg h24, if_pos (by omega)]
      obtain ⟨p, hp⟩ : ∃ p, 24 - e = p + 1 := ⟨23 - e, by omega⟩
      rw [hp, List.getD_cons_succ]
      have := coeffs_wbound 3484 (by decide) 24 1 (lcgSeed n) p (by omega)
      rw [show 1 + p = p + 1 by omega] at this
      exact this
  · rw [if_neg he]; simp

theorem lowDag_ok (f0 f1 f2 f3 f4 f5 f6 f7 f8 f9 f10 f11 f12 f13 f14 f15 f16 f17 f18 f19 f20 f21 f22 f23 f24 : Nat) (h0 : zdec f0 = 1)
    (hxb : ∀ x ∈ [f0, f1, f2, f3, f4, f5, f6, f7, f8, f9, f10, f11, f12, f13, f14, f15, f16, f17, f18, f19, f20, f21, f22, f23, f24], x / 2 ≤ 2 ^ 3483)
    (hb : ∀ e, (V9.fX [f0, f1, f2, f3, f4, f5, f6, f7, f8, f9, f10, f11, f12, f13, f14, f15, f16, f17, f18, f19, f20, f21, f22, f23, f24] e).natAbs ≤ V9.FbN e)
    (hbad : (V9.lowDag f0 f1 f2 f3 f4 f5 f6 f7 f8 f9 f10 f11 f12 f13 f14 f15 f16 f17 f18 f19 f20 f21 f22 f23 f24).2 = 0) :
    normalResultant ([f0, f1, f2, f3, f4, f5, f6, f7, f8, f9, f10, f11, f12, f13, f14, f15, f16, f17, f18, f19, f20, f21, f22, f23, f24].map zdec) (derivHL ([f0, f1, f2, f3, f4, f5, f6, f7, f8, f9, f10, f11, f12, f13, f14, f15, f16, f17, f18, f19, f20, f21, f22, f23, f24].map zdec)) = some (zdec (V9.lowDag f0 f1 f2 f3 f4 f5 f6 f7 f8 f9 f10 f11 f12 f13 f14 f15 f16 f17 f18 f19 f20 f21 f22 f23 f24).1) := by
  rw [V9.lowDag_eq f0 f1 f2 f3 f4 f5 f6 f7 f8 f9 f10 f11 f12 f13 f14 f15 f16 f17 f18 f19 f20 f21 f22 f23 f24] at hbad ⊢
  have h := V9.lowRun_spec [f0, f1, f2, f3, f4, f5, f6, f7, f8, f9, f10, f11, f12, f13, f14, f15, f16, f17, f18, f19, f20, f21, f22, f23, f24] rfl (by simpa [zdec_v9] using h0) hxb hb hbad
  rw [V9.toL_fX, V9.toL_gX, zdec_v9] at h
  exact h

theorem kont3484_def (n f0 f1 f2 f3 f4 f5 f6 f7 f8 f9 f10 f11 f12 f13 f14 f15 f16 f17 f18 f19 f20 f21 f22 f23 f24 : Nat) : kont3484 n f0 f1 f2 f3 f4 f5 f6 f7 f8 f9 f10 f11 f12 f13 f14 f15 f16 f17 f18 f19 f20 f21 f22 f23 f24 = finish8 (V9.lowDag f0 f1 f2 f3 f4 f5 f6 f7 f8 f9 f10 f11 f12 f13 f14 f15 f16 f17 f18 f19 f20 f21 f22 f23 f24) (kont n f0 f1 f2 f3 f4 f5 f6 f7 f8 f9 f10 f11 f12 f13 f14 f15 f16 f17 f18 f19 f20 f21 f22 f23 f24) := rfl

set_option exponentiation.threshold 4000 in
theorem kont3484_ok (n : Nat) (hk : kbitsOf n = 3484) : appL (kont3484 n) (discSpec n) (genF n) = discSpec n := by
  have hlen : (genF n).length = 25 := by unfold genF; simp [genGo_length]
  have hspec := genF_spec n
  have hfd := fastDisc_spec n
  have hbnd := polyOf_bound n
  rw [hk] at hbnd
  have hwb := polyOf_wbound n hk
  unfold fastDisc at hfd
  generalize genF n = L at hlen hspec hfd hwb
  match L, hlen with
  | [f0, f1, f2, f3, f4, f5, f6, f7, f8, f9, f10, f11, f12, f13, f14, f15, f16, f17, f18, f19, f20, f21, f22, f23, f24], _ =>
    rw [appL_25] at hfd ⊢
    rw [kont3484_def]
    have h0 : zdec f0 = 1 := by
      have := congrArg (fun l => l.headD 0) hspec
      simp only [List.map_cons, List.headD_cons] at this
      rw [this]; rfl
    have hxb : ∀ x ∈ [f0, f1, f2, f3, f4, f5, f6, f7, f8, f9, f10, f11, f12, f13, f14, f15, f16, f17, f18, f19, f20, f21, f22, f23, f24], x / 2 ≤ 2 ^ 3483 := by
      intro x hx
      have := hbnd (zdec x) (by rw [← hspec]; exact List.mem_map_of_mem hx)
      rw [← zdec_v9, V9.natAbs_zdec] at this
      exact this
    have key := lowDag_ok f0 f1 f2 f3 f4 f5 f6 f7 f8 f9 f10 f11 f12 f13 f14 f15 f16 f17 f18 f19 f20 f21 f22 f23 f24 h0 hxb hwb
    generalize V9.lowDag f0 f1 f2 f3 f4 f5 f6 f7 f8 f9 f10 f11 f12 f13 f14 f15 f16 f17 f18 f19 f20 f21 f22 f23 f24 = r at key ⊢
    cases h : r.2 with
    | succ m => rw [finish8_succ r _ m h]; exact hfd
    | zero =>
      rw [finish8_zero r _ h]
      have hres := key h
      unfold discSpec
      rw [← hspec]
      exact (disc_eq _ (by simp) _ hres).symm

theorem impl_correct : ∀ n, impl n = discSpec n := by
  intro n
  have hs := lcgSeed_lt n
  unfold impl genFastC9
  by_cases h0 : n < 67108864
  · rw [show Nat.div n 67108864 = 0 from Nat.div_eq_of_lt h0]
    have hk : kbitsOf n = 15 := by unfold kbitsOf difficultyLevel; simp [h0]
    rw [genLane15C_eq _ hs (kont15 n) (discSpec n)]
    have e : genF n = 2 :: genGo 15 24 1 (lcgSeed n) := by unfold genF; rw [hk]
    rw [← e]; exact kont15_ok n hk
  obtain ⟨m0, hm0⟩ := div_succ_of_le (by decide) (Nat.le_of_not_lt h0)
  rw [hm0]
  by_cases h1 : n < 68719476736
  · rw [show Nat.div n 68719476736 = 0 from Nat.div_eq_of_lt h1]
    have hk : kbitsOf n = 36 := by unfold kbitsOf difficultyLevel; simp [h0, h1]
    rw [genLane36C_eq _ hs (kont n) (discSpec n)]
    have e : genF n = 2 :: genGo 36 24 1 (lcgSeed n) := by unfold genF; rw [hk]
    rw [← e]; exact fastDisc_spec n
  obtain ⟨m1, hm1⟩ := div_succ_of_le (by decide) (Nat.le_of_not_lt h1)
  rw [hm1]
  by_cases h2 : n < 70368744177664
  · rw [show Nat.div n 70368744177664 = 0 from Nat.div_eq_of_lt h2]
    have hk : kbitsOf n = 205 := by unfold kbitsOf difficultyLevel; simp [h0, h1, h2]
    rw [genLane205C_eq _ hs (kont205 n) (discSpec n)]
    have e : genF n = 2 :: genGo 205 24 1 (lcgSeed n) := by unfold genF; rw [hk]
    rw [← e]; exact kont205_ok n hk
  obtain ⟨m2, hm2⟩ := div_succ_of_le (by decide) (Nat.le_of_not_lt h2)
  rw [hm2]
  by_cases h3 : n < 72057594037927936
  · rw [show Nat.div n 72057594037927936 = 0 from Nat.div_eq_of_lt h3]
    have hk : kbitsOf n = 1001 := by unfold kbitsOf difficultyLevel; simp [h0, h1, h2, h3]
    rw [genLane1001C_eq _ hs (kont n) (discSpec n)]
    have e : genF n = 2 :: genGo 1001 24 1 (lcgSeed n) := by unfold genF; rw [hk]
    rw [← e]; exact fastDisc_spec n
  obtain ⟨m3, hm3⟩ := div_succ_of_le (by decide) (Nat.le_of_not_lt h3)
  rw [hm3]
  have hk : kbitsOf n = 3484 := by unfold kbitsOf difficultyLevel; simp [h0, h1, h2, h3]
  rw [genLane3484C_eq _ hs (kont3484 n) (discSpec n)]
  have e : genF n = 2 :: genGo 3484 24 1 (lcgSeed n) := by unfold genF; rw [hk]
  rw [← e]; exact kont3484_ok n hk

end Submission
