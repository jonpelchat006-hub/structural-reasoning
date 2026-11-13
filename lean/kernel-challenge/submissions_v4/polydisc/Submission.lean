import Spec
import Lean

/-!
# Polynomial discriminant by an encoded, shared-graph normal PRS

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
`s` is `op a b`, with `op` one of `add sub mul div mod land lor xor shl shr` and operands `vN` (the
node on line `N`, counting from 0), `xN` (the `N`-th listed term) or a numeral; the last line,
`app f a₁ … aₙ` (or `list a₁ … aₙ`, the list `[a₁, …, aₙ]`), is the result. -/
elab "natdag% " s:str " [" xs:term,* "]" : term => do
  let xs ← xs.getElems.mapM fun x => elabTerm x none
  let ops : Std.HashMap String Name := Std.HashMap.ofList
    [("add", ``Nat.add), ("sub", ``Nat.sub), ("mul", ``Nat.mul), ("div", ``Nat.div), ("mod", ``Nat.mod),
     ("land", ``Nat.land), ("lor", ``Nat.lor), ("xor", ``Nat.xor), ("shl", ``Nat.shiftLeft),
     ("shr", ``Nat.shiftRight)]
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

def impl (n : Nat) : Int := genFastC n (kont n)

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

theorem impl_correct : ∀ n, impl n = discSpec n := by
  intro n
  unfold impl
  rw [genFastC_eq n (kont n) (discSpec n)]
  show fastDisc n (genF n) = _
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

end Submission
