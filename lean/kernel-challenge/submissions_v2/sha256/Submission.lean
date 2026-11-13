import Spec
import Lean

set_option maxRecDepth 100000

/-!
# SHA-256 chain with kernel-cheap word operations

The kernel pays a fixed overhead for every reduction step, so this submission minimises steps:

* Word operations call `Nat.add`/`Nat.land`/`Nat.xor`/`Nat.shiftRight` directly, so the kernel's
  GMP-accelerated literal extensions fire without unfolding `HAdd`/`AndOp`/… instances.
* A rotation of a 32-bit word is one right shift of the word duplicated into 64 bits
  (`x * 0x100000001 = x <<< 32 ||| x`); the Σ/σ functions leave garbage above bit 31, which is
  harmless because every such value only feeds a sum that is reduced mod `2^32` once.
* `Ch(e,f,g) = g ⊕ (e ∧ (f ⊕ g))` (3 operations) and `Maj(a,b,c) = ((a ∨ b) ∧ c) ∨ (a ∧ b)` (4).
* Additions are reduced mod `2^32` once per new word instead of after every addition.
* The 64 rounds run as two `List.rec` loops over the round constants with the eight working
  variables and a rolling 16-word message window as plain arguments (no structures, no
  `brecOn`); the first 48 rounds also produce the next schedule word.
* The digest between chain steps is the packed 256-bit big-endian number itself
  (`encodeDigest`), so the final encoding is free.

Proof outline:
* Bit-level lemmas (`S1_mod`, `S0_mod`, `s0_mod`, `s1_mod`, `ch_eq`, `maj_eq`) via `testBit`.
* `round_eq`: one fast round equals the spec's `round` on valid (32-bit) inputs.
* `loopA_eq`/`loopB_eq`: the loops equal the spec's `rounds` over the rolling schedule, which
  equals `extendW 48` (`schedule_correct`, adapted from the organizers' worked example).
* `stepN_eq`: one packed step equals `encodeDigest ∘ sha256step`; `iterN_eq` iterates it.
-/

namespace Submission

open Lean Elab Term Meta in
/-- `share x := v; b`: elaborate `b` with every `x` replaced by the same (shared) term `v`. -/
elab "share " x:ident " := " v:term "; " b:term : term => do
  let v ← instantiateMVars (← elabTermEnsuringType v (some (mkConst ``Nat)))
  withLocalDeclD x.getId (mkConst ``Nat) fun fv => do
    let b ← instantiateMVars (← elabTermEnsuringType b (some (mkConst ``Nat)))
    return b.replaceFVar fv v


/-! ## Implementation -/

/-- Duplicate a 32-bit word into 64 bits: rotations become right shifts. -/
def dup (x : Nat) : Nat := Nat.mul x 0x100000001

def S1 (e : Nat) : Nat :=
  Nat.xor (Nat.xor (Nat.shiftRight (dup e) 6) (Nat.shiftRight (dup e) 11)) (Nat.shiftRight (dup e) 25)
def S0 (a : Nat) : Nat :=
  Nat.xor (Nat.xor (Nat.shiftRight (dup a) 2) (Nat.shiftRight (dup a) 13)) (Nat.shiftRight (dup a) 22)
def s0 (x : Nat) : Nat :=
  Nat.xor (Nat.xor (Nat.shiftRight (dup x) 7) (Nat.shiftRight (dup x) 18)) (Nat.shiftRight x 3)
def s1 (x : Nat) : Nat :=
  Nat.xor (Nat.xor (Nat.shiftRight (dup x) 17) (Nat.shiftRight (dup x) 19)) (Nat.shiftRight x 10)

/-- `T1` before reduction mod `2^32`. -/
def T1 (h e f g k x : Nat) : Nat :=
  Nat.add (Nat.add (Nat.add (Nat.add h (S1 e)) (Nat.xor g (Nat.land e (Nat.xor f g)))) k) x
def NA (t1 a b c : Nat) : Nat :=
  Nat.land (Nat.add (Nat.add t1 (S0 a)) (Nat.xor b (Nat.land (Nat.xor a b) (Nat.xor b c)))) w32
def NE (d t1 : Nat) : Nat := Nat.land (Nat.add d t1) w32
def NW (x14 x9 x1 x0 : Nat) : Nat :=
  Nat.land (Nat.add (Nat.add (Nat.add (s1 x14) x9) (s0 x1)) x0) w32

/-- Add the chaining value and pack as the big-endian 256-bit digest (once per chain step). -/
def fin (a b c d e f g h : Nat) : Nat :=
  encodeDigest ⟨add32 iv.a a, add32 iv.b b, add32 iv.c c, add32 iv.d d,
    add32 iv.e e, add32 iv.f f, add32 iv.g g, add32 iv.h h⟩

/-- The last `n` rounds (no new schedule words); round constants are read from `ks`. -/
def loopB (n : Nat) : List Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat →
      Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat :=
  Nat.rec (motive := fun _ => List Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat →
      Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat)
    (fun _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ a b c d e f g h => fin a b c d e f g h)
    (fun _ ih ks x0 x1 x2 x3 x4 x5 x6 x7 x8 x9 x10 x11 x12 x13 x14 x15 a b c d e f g h =>
      let t1 := T1 h e f g (ks.headD 0) x0
      ih ks.tail x1 x2 x3 x4 x5 x6 x7 x8 x9 x10 x11 x12 x13 x14 x15 0 (NA t1 a b c) a b c (NE d t1) e f g)
    n

/-- The first `n` rounds, each also producing the next schedule word; then 16 more via `loopB`. -/
def loopA (n : Nat) : List Nat → List Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat →
      Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat :=
  Nat.rec (motive := fun _ => List Nat → List Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat →
      Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat)
    (fun _ kb => loopB 16 kb)
    (fun _ ih ks kb x0 x1 x2 x3 x4 x5 x6 x7 x8 x9 x10 x11 x12 x13 x14 x15 a b c d e f g h =>
      let t1 := T1 h e f g (ks.headD 0) x0
      ih ks.tail kb x1 x2 x3 x4 x5 x6 x7 x8 x9 x10 x11 x12 x13 x14 x15 (NW x14 x9 x1 x0) (NA t1 a b c) a b c (NE d t1) e f g)
    n

def KA : List Nat := K.take 48
def KB : List Nat := K.drop 48

/-- One chain step on the packed digest. -/
@[irreducible] def stepN (S : Nat) : Nat :=
  loopA 48 KA KB
    (Nat.land (Nat.shiftRight S 224) w32) (Nat.land (Nat.shiftRight S 192) w32)
    (Nat.land (Nat.shiftRight S 160) w32) (Nat.land (Nat.shiftRight S 128) w32)
    (Nat.land (Nat.shiftRight S 96) w32) (Nat.land (Nat.shiftRight S 64) w32)
    (Nat.land (Nat.shiftRight S 32) w32) (Nat.land S w32)
    0x80000000 0 0 0 0 0 0 256
    0x6a09e667 0xbb67ae85 0x3c6ef372 0xa54ff53a 0x510e527f 0x9b05688c 0x1f83d9ab 0x5be0cd19

/-- One chain step as a single shared expression graph: every intermediate word is one node
(built by `share`), so the kernel evaluates each word operation exactly once and pays no
per-round call or `let` overhead. `stepF_eq` shows it is definitionally the structured `stepN`. -/
def stepF (S : Nat) : Nat :=
  share v1 := (Nat.land (Nat.shiftRight S (nat_lit 224)) (nat_lit 0xffffffff));
  share v2 := (Nat.land (Nat.shiftRight S (nat_lit 192)) (nat_lit 0xffffffff));
  share v3 := (Nat.land (Nat.shiftRight S (nat_lit 160)) (nat_lit 0xffffffff));
  share v4 := (Nat.land (Nat.shiftRight S (nat_lit 128)) (nat_lit 0xffffffff));
  share v5 := (Nat.land (Nat.shiftRight S (nat_lit 96)) (nat_lit 0xffffffff));
  share v6 := (Nat.land (Nat.shiftRight S (nat_lit 64)) (nat_lit 0xffffffff));
  share v7 := (Nat.land (Nat.shiftRight S (nat_lit 32)) (nat_lit 0xffffffff));
  share v8 := (Nat.land (Nat.shiftRight S (nat_lit 0)) (nat_lit 0xffffffff));
  share v9 := (Nat.xor (nat_lit 3144134277) (nat_lit 1013904242));
  share v10 := (Nat.mul (nat_lit 1359893119) (nat_lit 0x100000001));
  share v11 := (Nat.add (Nat.add (Nat.add (Nat.add (nat_lit 1541459225) (Nat.xor (Nat.xor (Nat.shiftRight v10 (nat_lit 6)) (Nat.shiftRight v10 (nat_lit 11))) (Nat.shiftRight v10 (nat_lit 25)))) (Nat.xor (nat_lit 528734635) (Nat.land (nat_lit 1359893119) (Nat.xor (nat_lit 2600822924) (nat_lit 528734635))))) (nat_lit 1116352408)) v1);
  share v12 := (Nat.xor (nat_lit 1779033703) (nat_lit 3144134277));
  share v13 := (Nat.mul (nat_lit 1779033703) (nat_lit 0x100000001));
  share v14 := (Nat.land (Nat.add (Nat.add v11 (Nat.xor (Nat.xor (Nat.shiftRight v13 (nat_lit 2)) (Nat.shiftRight v13 (nat_lit 13))) (Nat.shiftRight v13 (nat_lit 22)))) (Nat.xor (nat_lit 3144134277) (Nat.land v12 v9))) (nat_lit 0xffffffff));
  share v15 := (Nat.land (Nat.add (nat_lit 2773480762) v11) (nat_lit 0xffffffff));
  share v16 := (Nat.mul v15 (nat_lit 0x100000001));
  share v17 := (Nat.add (Nat.add (Nat.add (Nat.add (nat_lit 528734635) (Nat.xor (Nat.xor (Nat.shiftRight v16 (nat_lit 6)) (Nat.shiftRight v16 (nat_lit 11))) (Nat.shiftRight v16 (nat_lit 25)))) (Nat.xor (nat_lit 2600822924) (Nat.land v15 (Nat.xor (nat_lit 1359893119) (nat_lit 2600822924))))) (nat_lit 1899447441)) v2);
  share v18 := (Nat.xor v14 (nat_lit 1779033703));
  share v19 := (Nat.mul v14 (nat_lit 0x100000001));
  share v20 := (Nat.land (Nat.add (Nat.add v17 (Nat.xor (Nat.xor (Nat.shiftRight v19 (nat_lit 2)) (Nat.shiftRight v19 (nat_lit 13))) (Nat.shiftRight v19 (nat_lit 22)))) (Nat.xor (nat_lit 1779033703) (Nat.land v18 v12))) (nat_lit 0xffffffff));
  share v21 := (Nat.land (Nat.add (nat_lit 1013904242) v17) (nat_lit 0xffffffff));
  share v22 := (Nat.mul v21 (nat_lit 0x100000001));
  share v23 := (Nat.add (Nat.add (Nat.add (Nat.add (nat_lit 2600822924) (Nat.xor (Nat.xor (Nat.shiftRight v22 (nat_lit 6)) (Nat.shiftRight v22 (nat_lit 11))) (Nat.shiftRight v22 (nat_lit 25)))) (Nat.xor (nat_lit 1359893119) (Nat.land v21 (Nat.xor v15 (nat_lit 1359893119))))) (nat_lit 3049323471)) v3);
  share v24 := (Nat.xor v20 v14);
  share v25 := (Nat.mul v20 (nat_lit 0x100000001));
  share v26 := (Nat.land (Nat.add (Nat.add v23 (Nat.xor (Nat.xor (Nat.shiftRight v25 (nat_lit 2)) (Nat.shiftRight v25 (nat_lit 13))) (Nat.shiftRight v25 (nat_lit 22)))) (Nat.xor v14 (Nat.land v24 v18))) (nat_lit 0xffffffff));
  share v27 := (Nat.land (Nat.add (nat_lit 3144134277) v23) (nat_lit 0xffffffff));
  share v28 := (Nat.mul v27 (nat_lit 0x100000001));
  share v29 := (Nat.add (Nat.add (Nat.add (Nat.add (nat_lit 1359893119) (Nat.xor (Nat.xor (Nat.shiftRight v28 (nat_lit 6)) (Nat.shiftRight v28 (nat_lit 11))) (Nat.shiftRight v28 (nat_lit 25)))) (Nat.xor v15 (Nat.land v27 (Nat.xor v21 v15)))) (nat_lit 3921009573)) v4);
  share v30 := (Nat.xor v26 v20);
  share v31 := (Nat.mul v26 (nat_lit 0x100000001));
  share v32 := (Nat.land (Nat.add (Nat.add v29 (Nat.xor (Nat.xor (Nat.shiftRight v31 (nat_lit 2)) (Nat.shiftRight v31 (nat_lit 13))) (Nat.shiftRight v31 (nat_lit 22)))) (Nat.xor v20 (Nat.land v30 v24))) (nat_lit 0xffffffff));
  share v33 := (Nat.land (Nat.add (nat_lit 1779033703) v29) (nat_lit 0xffffffff));
  share v34 := (Nat.mul v33 (nat_lit 0x100000001));
  share v35 := (Nat.add (Nat.add (Nat.add (Nat.add v15 (Nat.xor (Nat.xor (Nat.shiftRight v34 (nat_lit 6)) (Nat.shiftRight v34 (nat_lit 11))) (Nat.shiftRight v34 (nat_lit 25)))) (Nat.xor v21 (Nat.land v33 (Nat.xor v27 v21)))) (nat_lit 961987163)) v5);
  share v36 := (Nat.xor v32 v26);
  share v37 := (Nat.mul v32 (nat_lit 0x100000001));
  share v38 := (Nat.land (Nat.add (Nat.add v35 (Nat.xor (Nat.xor (Nat.shiftRight v37 (nat_lit 2)) (Nat.shiftRight v37 (nat_lit 13))) (Nat.shiftRight v37 (nat_lit 22)))) (Nat.xor v26 (Nat.land v36 v30))) (nat_lit 0xffffffff));
  share v39 := (Nat.land (Nat.add v14 v35) (nat_lit 0xffffffff));
  share v40 := (Nat.mul v39 (nat_lit 0x100000001));
  share v41 := (Nat.add (Nat.add (Nat.add (Nat.add v21 (Nat.xor (Nat.xor (Nat.shiftRight v40 (nat_lit 6)) (Nat.shiftRight v40 (nat_lit 11))) (Nat.shiftRight v40 (nat_lit 25)))) (Nat.xor v27 (Nat.land v39 (Nat.xor v33 v27)))) (nat_lit 1508970993)) v6);
  share v42 := (Nat.xor v38 v32);
  share v43 := (Nat.mul v38 (nat_lit 0x100000001));
  share v44 := (Nat.land (Nat.add (Nat.add v41 (Nat.xor (Nat.xor (Nat.shiftRight v43 (nat_lit 2)) (Nat.shiftRight v43 (nat_lit 13))) (Nat.shiftRight v43 (nat_lit 22)))) (Nat.xor v32 (Nat.land v42 v36))) (nat_lit 0xffffffff));
  share v45 := (Nat.land (Nat.add v20 v41) (nat_lit 0xffffffff));
  share v46 := (Nat.mul v45 (nat_lit 0x100000001));
  share v47 := (Nat.add (Nat.add (Nat.add (Nat.add v27 (Nat.xor (Nat.xor (Nat.shiftRight v46 (nat_lit 6)) (Nat.shiftRight v46 (nat_lit 11))) (Nat.shiftRight v46 (nat_lit 25)))) (Nat.xor v33 (Nat.land v45 (Nat.xor v39 v33)))) (nat_lit 2453635748)) v7);
  share v48 := (Nat.xor v44 v38);
  share v49 := (Nat.mul v44 (nat_lit 0x100000001));
  share v50 := (Nat.land (Nat.add (Nat.add v47 (Nat.xor (Nat.xor (Nat.shiftRight v49 (nat_lit 2)) (Nat.shiftRight v49 (nat_lit 13))) (Nat.shiftRight v49 (nat_lit 22)))) (Nat.xor v38 (Nat.land v48 v42))) (nat_lit 0xffffffff));
  share v51 := (Nat.land (Nat.add v26 v47) (nat_lit 0xffffffff));
  share v52 := (Nat.mul v51 (nat_lit 0x100000001));
  share v53 := (Nat.add (Nat.add (Nat.add (Nat.add v33 (Nat.xor (Nat.xor (Nat.shiftRight v52 (nat_lit 6)) (Nat.shiftRight v52 (nat_lit 11))) (Nat.shiftRight v52 (nat_lit 25)))) (Nat.xor v39 (Nat.land v51 (Nat.xor v45 v39)))) (nat_lit 2870763221)) v8);
  share v54 := (Nat.xor v50 v44);
  share v55 := (Nat.mul v50 (nat_lit 0x100000001));
  share v56 := (Nat.land (Nat.add (Nat.add v53 (Nat.xor (Nat.xor (Nat.shiftRight v55 (nat_lit 2)) (Nat.shiftRight v55 (nat_lit 13))) (Nat.shiftRight v55 (nat_lit 22)))) (Nat.xor v44 (Nat.land v54 v48))) (nat_lit 0xffffffff));
  share v57 := (Nat.land (Nat.add v32 v53) (nat_lit 0xffffffff));
  share v58 := (Nat.mul v57 (nat_lit 0x100000001));
  share v59 := (Nat.add (Nat.add (Nat.add (Nat.add v39 (Nat.xor (Nat.xor (Nat.shiftRight v58 (nat_lit 6)) (Nat.shiftRight v58 (nat_lit 11))) (Nat.shiftRight v58 (nat_lit 25)))) (Nat.xor v45 (Nat.land v57 (Nat.xor v51 v45)))) (nat_lit 3624381080)) (nat_lit 2147483648));
  share v60 := (Nat.xor v56 v50);
  share v61 := (Nat.mul v56 (nat_lit 0x100000001));
  share v62 := (Nat.land (Nat.add (Nat.add v59 (Nat.xor (Nat.xor (Nat.shiftRight v61 (nat_lit 2)) (Nat.shiftRight v61 (nat_lit 13))) (Nat.shiftRight v61 (nat_lit 22)))) (Nat.xor v50 (Nat.land v60 v54))) (nat_lit 0xffffffff));
  share v63 := (Nat.land (Nat.add v38 v59) (nat_lit 0xffffffff));
  share v64 := (Nat.mul v63 (nat_lit 0x100000001));
  share v65 := (Nat.add (Nat.add (Nat.add (Nat.add v45 (Nat.xor (Nat.xor (Nat.shiftRight v64 (nat_lit 6)) (Nat.shiftRight v64 (nat_lit 11))) (Nat.shiftRight v64 (nat_lit 25)))) (Nat.xor v51 (Nat.land v63 (Nat.xor v57 v51)))) (nat_lit 310598401)) (nat_lit 0));
  share v66 := (Nat.xor v62 v56);
  share v67 := (Nat.mul v62 (nat_lit 0x100000001));
  share v68 := (Nat.land (Nat.add (Nat.add v65 (Nat.xor (Nat.xor (Nat.shiftRight v67 (nat_lit 2)) (Nat.shiftRight v67 (nat_lit 13))) (Nat.shiftRight v67 (nat_lit 22)))) (Nat.xor v56 (Nat.land v66 v60))) (nat_lit 0xffffffff));
  share v69 := (Nat.land (Nat.add v44 v65) (nat_lit 0xffffffff));
  share v70 := (Nat.mul v69 (nat_lit 0x100000001));
  share v71 := (Nat.add (Nat.add (Nat.add (Nat.add v51 (Nat.xor (Nat.xor (Nat.shiftRight v70 (nat_lit 6)) (Nat.shiftRight v70 (nat_lit 11))) (Nat.shiftRight v70 (nat_lit 25)))) (Nat.xor v57 (Nat.land v69 (Nat.xor v63 v57)))) (nat_lit 607225278)) (nat_lit 0));
  share v72 := (Nat.xor v68 v62);
  share v73 := (Nat.mul v68 (nat_lit 0x100000001));
  share v74 := (Nat.land (Nat.add (Nat.add v71 (Nat.xor (Nat.xor (Nat.shiftRight v73 (nat_lit 2)) (Nat.shiftRight v73 (nat_lit 13))) (Nat.shiftRight v73 (nat_lit 22)))) (Nat.xor v62 (Nat.land v72 v66))) (nat_lit 0xffffffff));
  share v75 := (Nat.land (Nat.add v50 v71) (nat_lit 0xffffffff));
  share v76 := (Nat.mul v75 (nat_lit 0x100000001));
  share v77 := (Nat.add (Nat.add (Nat.add (Nat.add v57 (Nat.xor (Nat.xor (Nat.shiftRight v76 (nat_lit 6)) (Nat.shiftRight v76 (nat_lit 11))) (Nat.shiftRight v76 (nat_lit 25)))) (Nat.xor v63 (Nat.land v75 (Nat.xor v69 v63)))) (nat_lit 1426881987)) (nat_lit 0));
  share v78 := (Nat.xor v74 v68);
  share v79 := (Nat.mul v74 (nat_lit 0x100000001));
  share v80 := (Nat.land (Nat.add (Nat.add v77 (Nat.xor (Nat.xor (Nat.shiftRight v79 (nat_lit 2)) (Nat.shiftRight v79 (nat_lit 13))) (Nat.shiftRight v79 (nat_lit 22)))) (Nat.xor v68 (Nat.land v78 v72))) (nat_lit 0xffffffff));
  share v81 := (Nat.land (Nat.add v56 v77) (nat_lit 0xffffffff));
  share v82 := (Nat.mul v81 (nat_lit 0x100000001));
  share v83 := (Nat.add (Nat.add (Nat.add (Nat.add v63 (Nat.xor (Nat.xor (Nat.shiftRight v82 (nat_lit 6)) (Nat.shiftRight v82 (nat_lit 11))) (Nat.shiftRight v82 (nat_lit 25)))) (Nat.xor v69 (Nat.land v81 (Nat.xor v75 v69)))) (nat_lit 1925078388)) (nat_lit 0));
  share v84 := (Nat.xor v80 v74);
  share v85 := (Nat.mul v80 (nat_lit 0x100000001));
  share v86 := (Nat.land (Nat.add (Nat.add v83 (Nat.xor (Nat.xor (Nat.shiftRight v85 (nat_lit 2)) (Nat.shiftRight v85 (nat_lit 13))) (Nat.shiftRight v85 (nat_lit 22)))) (Nat.xor v74 (Nat.land v84 v78))) (nat_lit 0xffffffff));
  share v87 := (Nat.land (Nat.add v62 v83) (nat_lit 0xffffffff));
  share v88 := (Nat.mul v87 (nat_lit 0x100000001));
  share v89 := (Nat.add (Nat.add (Nat.add (Nat.add v69 (Nat.xor (Nat.xor (Nat.shiftRight v88 (nat_lit 6)) (Nat.shiftRight v88 (nat_lit 11))) (Nat.shiftRight v88 (nat_lit 25)))) (Nat.xor v75 (Nat.land v87 (Nat.xor v81 v75)))) (nat_lit 2162078206)) (nat_lit 0));
  share v90 := (Nat.xor v86 v80);
  share v91 := (Nat.mul v86 (nat_lit 0x100000001));
  share v92 := (Nat.land (Nat.add (Nat.add v89 (Nat.xor (Nat.xor (Nat.shiftRight v91 (nat_lit 2)) (Nat.shiftRight v91 (nat_lit 13))) (Nat.shiftRight v91 (nat_lit 22)))) (Nat.xor v80 (Nat.land v90 v84))) (nat_lit 0xffffffff));
  share v93 := (Nat.land (Nat.add v68 v89) (nat_lit 0xffffffff));
  share v94 := (Nat.mul v93 (nat_lit 0x100000001));
  share v95 := (Nat.add (Nat.add (Nat.add (Nat.add v75 (Nat.xor (Nat.xor (Nat.shiftRight v94 (nat_lit 6)) (Nat.shiftRight v94 (nat_lit 11))) (Nat.shiftRight v94 (nat_lit 25)))) (Nat.xor v81 (Nat.land v93 (Nat.xor v87 v81)))) (nat_lit 2614888103)) (nat_lit 0));
  share v96 := (Nat.xor v92 v86);
  share v97 := (Nat.mul v92 (nat_lit 0x100000001));
  share v98 := (Nat.land (Nat.add (Nat.add v95 (Nat.xor (Nat.xor (Nat.shiftRight v97 (nat_lit 2)) (Nat.shiftRight v97 (nat_lit 13))) (Nat.shiftRight v97 (nat_lit 22)))) (Nat.xor v86 (Nat.land v96 v90))) (nat_lit 0xffffffff));
  share v99 := (Nat.land (Nat.add v74 v95) (nat_lit 0xffffffff));
  share v100 := (Nat.mul v99 (nat_lit 0x100000001));
  share v101 := (Nat.add (Nat.add (Nat.add (Nat.add v81 (Nat.xor (Nat.xor (Nat.shiftRight v100 (nat_lit 6)) (Nat.shiftRight v100 (nat_lit 11))) (Nat.shiftRight v100 (nat_lit 25)))) (Nat.xor v87 (Nat.land v99 (Nat.xor v93 v87)))) (nat_lit 3248222580)) (nat_lit 256));
  share v102 := (Nat.xor v98 v92);
  share v103 := (Nat.mul v98 (nat_lit 0x100000001));
  share v104 := (Nat.land (Nat.add (Nat.add v101 (Nat.xor (Nat.xor (Nat.shiftRight v103 (nat_lit 2)) (Nat.shiftRight v103 (nat_lit 13))) (Nat.shiftRight v103 (nat_lit 22)))) (Nat.xor v92 (Nat.land v102 v96))) (nat_lit 0xffffffff));
  share v105 := (Nat.land (Nat.add v80 v101) (nat_lit 0xffffffff));
  share v106 := (Nat.mul (nat_lit 0) (nat_lit 0x100000001));
  share v107 := (Nat.mul v2 (nat_lit 0x100000001));
  share v108 := (Nat.land (Nat.add (Nat.add (Nat.add (Nat.xor (Nat.xor (Nat.shiftRight v106 (nat_lit 17)) (Nat.shiftRight v106 (nat_lit 19))) (Nat.shiftRight (nat_lit 0) (nat_lit 10))) (nat_lit 0)) (Nat.xor (Nat.xor (Nat.shiftRight v107 (nat_lit 7)) (Nat.shiftRight v107 (nat_lit 18))) (Nat.shiftRight v2 (nat_lit 3)))) v1) (nat_lit 0xffffffff));
  share v109 := (Nat.mul v105 (nat_lit 0x100000001));
  share v110 := (Nat.add (Nat.add (Nat.add (Nat.add v87 (Nat.xor (Nat.xor (Nat.shiftRight v109 (nat_lit 6)) (Nat.shiftRight v109 (nat_lit 11))) (Nat.shiftRight v109 (nat_lit 25)))) (Nat.xor v93 (Nat.land v105 (Nat.xor v99 v93)))) (nat_lit 3835390401)) v108);
  share v111 := (Nat.xor v104 v98);
  share v112 := (Nat.mul v104 (nat_lit 0x100000001));
  share v113 := (Nat.land (Nat.add (Nat.add v110 (Nat.xor (Nat.xor (Nat.shiftRight v112 (nat_lit 2)) (Nat.shiftRight v112 (nat_lit 13))) (Nat.shiftRight v112 (nat_lit 22)))) (Nat.xor v98 (Nat.land v111 v102))) (nat_lit 0xffffffff));
  share v114 := (Nat.land (Nat.add v86 v110) (nat_lit 0xffffffff));
  share v115 := (Nat.mul (nat_lit 256) (nat_lit 0x100000001));
  share v116 := (Nat.mul v3 (nat_lit 0x100000001));
  share v117 := (Nat.land (Nat.add (Nat.add (Nat.add (Nat.xor (Nat.xor (Nat.shiftRight v115 (nat_lit 17)) (Nat.shiftRight v115 (nat_lit 19))) (Nat.shiftRight (nat_lit 256) (nat_lit 10))) (nat_lit 0)) (Nat.xor (Nat.xor (Nat.shiftRight v116 (nat_lit 7)) (Nat.shiftRight v116 (nat_lit 18))) (Nat.shiftRight v3 (nat_lit 3)))) v2) (nat_lit 0xffffffff));
  share v118 := (Nat.mul v114 (nat_lit 0x100000001));
  share v119 := (Nat.add (Nat.add (Nat.add (Nat.add v93 (Nat.xor (Nat.xor (Nat.shiftRight v118 (nat_lit 6)) (Nat.shiftRight v118 (nat_lit 11))) (Nat.shiftRight v118 (nat_lit 25)))) (Nat.xor v99 (Nat.land v114 (Nat.xor v105 v99)))) (nat_lit 4022224774)) v117);
  share v120 := (Nat.xor v113 v104);
  share v121 := (Nat.mul v113 (nat_lit 0x100000001));
  share v122 := (Nat.land (Nat.add (Nat.add v119 (Nat.xor (Nat.xor (Nat.shiftRight v121 (nat_lit 2)) (Nat.shiftRight v121 (nat_lit 13))) (Nat.shiftRight v121 (nat_lit 22)))) (Nat.xor v104 (Nat.land v120 v111))) (nat_lit 0xffffffff));
  share v123 := (Nat.land (Nat.add v92 v119) (nat_lit 0xffffffff));
  share v124 := (Nat.mul v108 (nat_lit 0x100000001));
  share v125 := (Nat.mul v4 (nat_lit 0x100000001));
  share v126 := (Nat.land (Nat.add (Nat.add (Nat.add (Nat.xor (Nat.xor (Nat.shiftRight v124 (nat_lit 17)) (Nat.shiftRight v124 (nat_lit 19))) (Nat.shiftRight v108 (nat_lit 10))) (nat_lit 0)) (Nat.xor (Nat.xor (Nat.shiftRight v125 (nat_lit 7)) (Nat.shiftRight v125 (nat_lit 18))) (Nat.shiftRight v4 (nat_lit 3)))) v3) (nat_lit 0xffffffff));
  share v127 := (Nat.mul v123 (nat_lit 0x100000001));
  share v128 := (Nat.add (Nat.add (Nat.add (Nat.add v99 (Nat.xor (Nat.xor (Nat.shiftRight v127 (nat_lit 6)) (Nat.shiftRight v127 (nat_lit 11))) (Nat.shiftRight v127 (nat_lit 25)))) (Nat.xor v105 (Nat.land v123 (Nat.xor v114 v105)))) (nat_lit 264347078)) v126);
  share v129 := (Nat.xor v122 v113);
  share v130 := (Nat.mul v122 (nat_lit 0x100000001));
  share v131 := (Nat.land (Nat.add (Nat.add v128 (Nat.xor (Nat.xor (Nat.shiftRight v130 (nat_lit 2)) (Nat.shiftRight v130 (nat_lit 13))) (Nat.shiftRight v130 (nat_lit 22)))) (Nat.xor v113 (Nat.land v129 v120))) (nat_lit 0xffffffff));
  share v132 := (Nat.land (Nat.add v98 v128) (nat_lit 0xffffffff));
  share v133 := (Nat.mul v117 (nat_lit 0x100000001));
  share v134 := (Nat.mul v5 (nat_lit 0x100000001));
  share v135 := (Nat.land (Nat.add (Nat.add (Nat.add (Nat.xor (Nat.xor (Nat.shiftRight v133 (nat_lit 17)) (Nat.shiftRight v133 (nat_lit 19))) (Nat.shiftRight v117 (nat_lit 10))) (nat_lit 0)) (Nat.xor (Nat.xor (Nat.shiftRight v134 (nat_lit 7)) (Nat.shiftRight v134 (nat_lit 18))) (Nat.shiftRight v5 (nat_lit 3)))) v4) (nat_lit 0xffffffff));
  share v136 := (Nat.mul v132 (nat_lit 0x100000001));
  share v137 := (Nat.add (Nat.add (Nat.add (Nat.add v105 (Nat.xor (Nat.xor (Nat.shiftRight v136 (nat_lit 6)) (Nat.shiftRight v136 (nat_lit 11))) (Nat.shiftRight v136 (nat_lit 25)))) (Nat.xor v114 (Nat.land v132 (Nat.xor v123 v114)))) (nat_lit 604807628)) v135);
  share v138 := (Nat.xor v131 v122);
  share v139 := (Nat.mul v131 (nat_lit 0x100000001));
  share v140 := (Nat.land (Nat.add (Nat.add v137 (Nat.xor (Nat.xor (Nat.shiftRight v139 (nat_lit 2)) (Nat.shiftRight v139 (nat_lit 13))) (Nat.shiftRight v139 (nat_lit 22)))) (Nat.xor v122 (Nat.land v138 v129))) (nat_lit 0xffffffff));
  share v141 := (Nat.land (Nat.add v104 v137) (nat_lit 0xffffffff));
  share v142 := (Nat.mul v126 (nat_lit 0x100000001));
  share v143 := (Nat.mul v6 (nat_lit 0x100000001));
  share v144 := (Nat.land (Nat.add (Nat.add (Nat.add (Nat.xor (Nat.xor (Nat.shiftRight v142 (nat_lit 17)) (Nat.shiftRight v142 (nat_lit 19))) (Nat.shiftRight v126 (nat_lit 10))) (nat_lit 0)) (Nat.xor (Nat.xor (Nat.shiftRight v143 (nat_lit 7)) (Nat.shiftRight v143 (nat_lit 18))) (Nat.shiftRight v6 (nat_lit 3)))) v5) (nat_lit 0xffffffff));
  share v145 := (Nat.mul v141 (nat_lit 0x100000001));
  share v146 := (Nat.add (Nat.add (Nat.add (Nat.add v114 (Nat.xor (Nat.xor (Nat.shiftRight v145 (nat_lit 6)) (Nat.shiftRight v145 (nat_lit 11))) (Nat.shiftRight v145 (nat_lit 25)))) (Nat.xor v123 (Nat.land v141 (Nat.xor v132 v123)))) (nat_lit 770255983)) v144);
  share v147 := (Nat.xor v140 v131);
  share v148 := (Nat.mul v140 (nat_lit 0x100000001));
  share v149 := (Nat.land (Nat.add (Nat.add v146 (Nat.xor (Nat.xor (Nat.shiftRight v148 (nat_lit 2)) (Nat.shiftRight v148 (nat_lit 13))) (Nat.shiftRight v148 (nat_lit 22)))) (Nat.xor v131 (Nat.land v147 v138))) (nat_lit 0xffffffff));
  share v150 := (Nat.land (Nat.add v113 v146) (nat_lit 0xffffffff));
  share v151 := (Nat.mul v135 (nat_lit 0x100000001));
  share v152 := (Nat.mul v7 (nat_lit 0x100000001));
  share v153 := (Nat.land (Nat.add (Nat.add (Nat.add (Nat.xor (Nat.xor (Nat.shiftRight v151 (nat_lit 17)) (Nat.shiftRight v151 (nat_lit 19))) (Nat.shiftRight v135 (nat_lit 10))) (nat_lit 0)) (Nat.xor (Nat.xor (Nat.shiftRight v152 (nat_lit 7)) (Nat.shiftRight v152 (nat_lit 18))) (Nat.shiftRight v7 (nat_lit 3)))) v6) (nat_lit 0xffffffff));
  share v154 := (Nat.mul v150 (nat_lit 0x100000001));
  share v155 := (Nat.add (Nat.add (Nat.add (Nat.add v123 (Nat.xor (Nat.xor (Nat.shiftRight v154 (nat_lit 6)) (Nat.shiftRight v154 (nat_lit 11))) (Nat.shiftRight v154 (nat_lit 25)))) (Nat.xor v132 (Nat.land v150 (Nat.xor v141 v132)))) (nat_lit 1249150122)) v153);
  share v156 := (Nat.xor v149 v140);
  share v157 := (Nat.mul v149 (nat_lit 0x100000001));
  share v158 := (Nat.land (Nat.add (Nat.add v155 (Nat.xor (Nat.xor (Nat.shiftRight v157 (nat_lit 2)) (Nat.shiftRight v157 (nat_lit 13))) (Nat.shiftRight v157 (nat_lit 22)))) (Nat.xor v140 (Nat.land v156 v147))) (nat_lit 0xffffffff));
  share v159 := (Nat.land (Nat.add v122 v155) (nat_lit 0xffffffff));
  share v160 := (Nat.mul v144 (nat_lit 0x100000001));
  share v161 := (Nat.mul v8 (nat_lit 0x100000001));
  share v162 := (Nat.land (Nat.add (Nat.add (Nat.add (Nat.xor (Nat.xor (Nat.shiftRight v160 (nat_lit 17)) (Nat.shiftRight v160 (nat_lit 19))) (Nat.shiftRight v144 (nat_lit 10))) (nat_lit 256)) (Nat.xor (Nat.xor (Nat.shiftRight v161 (nat_lit 7)) (Nat.shiftRight v161 (nat_lit 18))) (Nat.shiftRight v8 (nat_lit 3)))) v7) (nat_lit 0xffffffff));
  share v163 := (Nat.mul v159 (nat_lit 0x100000001));
  share v164 := (Nat.add (Nat.add (Nat.add (Nat.add v132 (Nat.xor (Nat.xor (Nat.shiftRight v163 (nat_lit 6)) (Nat.shiftRight v163 (nat_lit 11))) (Nat.shiftRight v163 (nat_lit 25)))) (Nat.xor v141 (Nat.land v159 (Nat.xor v150 v141)))) (nat_lit 1555081692)) v162);
  share v165 := (Nat.xor v158 v149);
  share v166 := (Nat.mul v158 (nat_lit 0x100000001));
  share v167 := (Nat.land (Nat.add (Nat.add v164 (Nat.xor (Nat.xor (Nat.shiftRight v166 (nat_lit 2)) (Nat.shiftRight v166 (nat_lit 13))) (Nat.shiftRight v166 (nat_lit 22)))) (Nat.xor v149 (Nat.land v165 v156))) (nat_lit 0xffffffff));
  share v168 := (Nat.land (Nat.add v131 v164) (nat_lit 0xffffffff));
  share v169 := (Nat.mul v153 (nat_lit 0x100000001));
  share v170 := (Nat.mul (nat_lit 2147483648) (nat_lit 0x100000001));
  share v171 := (Nat.land (Nat.add (Nat.add (Nat.add (Nat.xor (Nat.xor (Nat.shiftRight v169 (nat_lit 17)) (Nat.shiftRight v169 (nat_lit 19))) (Nat.shiftRight v153 (nat_lit 10))) v108) (Nat.xor (Nat.xor (Nat.shiftRight v170 (nat_lit 7)) (Nat.shiftRight v170 (nat_lit 18))) (Nat.shiftRight (nat_lit 2147483648) (nat_lit 3)))) v8) (nat_lit 0xffffffff));
  share v172 := (Nat.mul v168 (nat_lit 0x100000001));
  share v173 := (Nat.add (Nat.add (Nat.add (Nat.add v141 (Nat.xor (Nat.xor (Nat.shiftRight v172 (nat_lit 6)) (Nat.shiftRight v172 (nat_lit 11))) (Nat.shiftRight v172 (nat_lit 25)))) (Nat.xor v150 (Nat.land v168 (Nat.xor v159 v150)))) (nat_lit 1996064986)) v171);
  share v174 := (Nat.xor v167 v158);
  share v175 := (Nat.mul v167 (nat_lit 0x100000001));
  share v176 := (Nat.land (Nat.add (Nat.add v173 (Nat.xor (Nat.xor (Nat.shiftRight v175 (nat_lit 2)) (Nat.shiftRight v175 (nat_lit 13))) (Nat.shiftRight v175 (nat_lit 22)))) (Nat.xor v158 (Nat.land v174 v165))) (nat_lit 0xffffffff));
  share v177 := (Nat.land (Nat.add v140 v173) (nat_lit 0xffffffff));
  share v178 := (Nat.mul v162 (nat_lit 0x100000001));
  share v179 := (Nat.land (Nat.add (Nat.add (Nat.add (Nat.xor (Nat.xor (Nat.shiftRight v178 (nat_lit 17)) (Nat.shiftRight v178 (nat_lit 19))) (Nat.shiftRight v162 (nat_lit 10))) v117) (Nat.xor (Nat.xor (Nat.shiftRight v106 (nat_lit 7)) (Nat.shiftRight v106 (nat_lit 18))) (Nat.shiftRight (nat_lit 0) (nat_lit 3)))) (nat_lit 2147483648)) (nat_lit 0xffffffff));
  share v180 := (Nat.mul v177 (nat_lit 0x100000001));
  share v181 := (Nat.add (Nat.add (Nat.add (Nat.add v150 (Nat.xor (Nat.xor (Nat.shiftRight v180 (nat_lit 6)) (Nat.shiftRight v180 (nat_lit 11))) (Nat.shiftRight v180 (nat_lit 25)))) (Nat.xor v159 (Nat.land v177 (Nat.xor v168 v159)))) (nat_lit 2554220882)) v179);
  share v182 := (Nat.xor v176 v167);
  share v183 := (Nat.mul v176 (nat_lit 0x100000001));
  share v184 := (Nat.land (Nat.add (Nat.add v181 (Nat.xor (Nat.xor (Nat.shiftRight v183 (nat_lit 2)) (Nat.shiftRight v183 (nat_lit 13))) (Nat.shiftRight v183 (nat_lit 22)))) (Nat.xor v167 (Nat.land v182 v174))) (nat_lit 0xffffffff));
  share v185 := (Nat.land (Nat.add v149 v181) (nat_lit 0xffffffff));
  share v186 := (Nat.mul v171 (nat_lit 0x100000001));
  share v187 := (Nat.land (Nat.add (Nat.add (Nat.add (Nat.xor (Nat.xor (Nat.shiftRight v186 (nat_lit 17)) (Nat.shiftRight v186 (nat_lit 19))) (Nat.shiftRight v171 (nat_lit 10))) v126) (Nat.xor (Nat.xor (Nat.shiftRight v106 (nat_lit 7)) (Nat.shiftRight v106 (nat_lit 18))) (Nat.shiftRight (nat_lit 0) (nat_lit 3)))) (nat_lit 0)) (nat_lit 0xffffffff));
  share v188 := (Nat.mul v185 (nat_lit 0x100000001));
  share v189 := (Nat.add (Nat.add (Nat.add (Nat.add v159 (Nat.xor (Nat.xor (Nat.shiftRight v188 (nat_lit 6)) (Nat.shiftRight v188 (nat_lit 11))) (Nat.shiftRight v188 (nat_lit 25)))) (Nat.xor v168 (Nat.land v185 (Nat.xor v177 v168)))) (nat_lit 2821834349)) v187);
  share v190 := (Nat.xor v184 v176);
  share v191 := (Nat.mul v184 (nat_lit 0x100000001));
  share v192 := (Nat.land (Nat.add (Nat.add v189 (Nat.xor (Nat.xor (Nat.shiftRight v191 (nat_lit 2)) (Nat.shiftRight v191 (nat_lit 13))) (Nat.shiftRight v191 (nat_lit 22)))) (Nat.xor v176 (Nat.land v190 v182))) (nat_lit 0xffffffff));
  share v193 := (Nat.land (Nat.add v158 v189) (nat_lit 0xffffffff));
  share v194 := (Nat.mul v179 (nat_lit 0x100000001));
  share v195 := (Nat.land (Nat.add (Nat.add (Nat.add (Nat.xor (Nat.xor (Nat.shiftRight v194 (nat_lit 17)) (Nat.shiftRight v194 (nat_lit 19))) (Nat.shiftRight v179 (nat_lit 10))) v135) (Nat.xor (Nat.xor (Nat.shiftRight v106 (nat_lit 7)) (Nat.shiftRight v106 (nat_lit 18))) (Nat.shiftRight (nat_lit 0) (nat_lit 3)))) (nat_lit 0)) (nat_lit 0xffffffff));
  share v196 := (Nat.mul v193 (nat_lit 0x100000001));
  share v197 := (Nat.add (Nat.add (Nat.add (Nat.add v168 (Nat.xor (Nat.xor (Nat.shiftRight v196 (nat_lit 6)) (Nat.shiftRight v196 (nat_lit 11))) (Nat.shiftRight v196 (nat_lit 25)))) (Nat.xor v177 (Nat.land v193 (Nat.xor v185 v177)))) (nat_lit 2952996808)) v195);
  share v198 := (Nat.xor v192 v184);
  share v199 := (Nat.mul v192 (nat_lit 0x100000001));
  share v200 := (Nat.land (Nat.add (Nat.add v197 (Nat.xor (Nat.xor (Nat.shiftRight v199 (nat_lit 2)) (Nat.shiftRight v199 (nat_lit 13))) (Nat.shiftRight v199 (nat_lit 22)))) (Nat.xor v184 (Nat.land v198 v190))) (nat_lit 0xffffffff));
  share v201 := (Nat.land (Nat.add v167 v197) (nat_lit 0xffffffff));
  share v202 := (Nat.mul v187 (nat_lit 0x100000001));
  share v203 := (Nat.land (Nat.add (Nat.add (Nat.add (Nat.xor (Nat.xor (Nat.shiftRight v202 (nat_lit 17)) (Nat.shiftRight v202 (nat_lit 19))) (Nat.shiftRight v187 (nat_lit 10))) v144) (Nat.xor (Nat.xor (Nat.shiftRight v106 (nat_lit 7)) (Nat.shiftRight v106 (nat_lit 18))) (Nat.shiftRight (nat_lit 0) (nat_lit 3)))) (nat_lit 0)) (nat_lit 0xffffffff));
  share v204 := (Nat.mul v201 (nat_lit 0x100000001));
  share v205 := (Nat.add (Nat.add (Nat.add (Nat.add v177 (Nat.xor (Nat.xor (Nat.shiftRight v204 (nat_lit 6)) (Nat.shiftRight v204 (nat_lit 11))) (Nat.shiftRight v204 (nat_lit 25)))) (Nat.xor v185 (Nat.land v201 (Nat.xor v193 v185)))) (nat_lit 3210313671)) v203);
  share v206 := (Nat.xor v200 v192);
  share v207 := (Nat.mul v200 (nat_lit 0x100000001));
  share v208 := (Nat.land (Nat.add (Nat.add v205 (Nat.xor (Nat.xor (Nat.shiftRight v207 (nat_lit 2)) (Nat.shiftRight v207 (nat_lit 13))) (Nat.shiftRight v207 (nat_lit 22)))) (Nat.xor v192 (Nat.land v206 v198))) (nat_lit 0xffffffff));
  share v209 := (Nat.land (Nat.add v176 v205) (nat_lit 0xffffffff));
  share v210 := (Nat.mul v195 (nat_lit 0x100000001));
  share v211 := (Nat.land (Nat.add (Nat.add (Nat.add (Nat.xor (Nat.xor (Nat.shiftRight v210 (nat_lit 17)) (Nat.shiftRight v210 (nat_lit 19))) (Nat.shiftRight v195 (nat_lit 10))) v153) (Nat.xor (Nat.xor (Nat.shiftRight v106 (nat_lit 7)) (Nat.shiftRight v106 (nat_lit 18))) (Nat.shiftRight (nat_lit 0) (nat_lit 3)))) (nat_lit 0)) (nat_lit 0xffffffff));
  share v212 := (Nat.mul v209 (nat_lit 0x100000001));
  share v213 := (Nat.add (Nat.add (Nat.add (Nat.add v185 (Nat.xor (Nat.xor (Nat.shiftRight v212 (nat_lit 6)) (Nat.shiftRight v212 (nat_lit 11))) (Nat.shiftRight v212 (nat_lit 25)))) (Nat.xor v193 (Nat.land v209 (Nat.xor v201 v193)))) (nat_lit 3336571891)) v211);
  share v214 := (Nat.xor v208 v200);
  share v215 := (Nat.mul v208 (nat_lit 0x100000001));
  share v216 := (Nat.land (Nat.add (Nat.add v213 (Nat.xor (Nat.xor (Nat.shiftRight v215 (nat_lit 2)) (Nat.shiftRight v215 (nat_lit 13))) (Nat.shiftRight v215 (nat_lit 22)))) (Nat.xor v200 (Nat.land v214 v206))) (nat_lit 0xffffffff));
  share v217 := (Nat.land (Nat.add v184 v213) (nat_lit 0xffffffff));
  share v218 := (Nat.mul v203 (nat_lit 0x100000001));
  share v219 := (Nat.land (Nat.add (Nat.add (Nat.add (Nat.xor (Nat.xor (Nat.shiftRight v218 (nat_lit 17)) (Nat.shiftRight v218 (nat_lit 19))) (Nat.shiftRight v203 (nat_lit 10))) v162) (Nat.xor (Nat.xor (Nat.shiftRight v106 (nat_lit 7)) (Nat.shiftRight v106 (nat_lit 18))) (Nat.shiftRight (nat_lit 0) (nat_lit 3)))) (nat_lit 0)) (nat_lit 0xffffffff));
  share v220 := (Nat.mul v217 (nat_lit 0x100000001));
  share v221 := (Nat.add (Nat.add (Nat.add (Nat.add v193 (Nat.xor (Nat.xor (Nat.shiftRight v220 (nat_lit 6)) (Nat.shiftRight v220 (nat_lit 11))) (Nat.shiftRight v220 (nat_lit 25)))) (Nat.xor v201 (Nat.land v217 (Nat.xor v209 v201)))) (nat_lit 3584528711)) v219);
  share v222 := (Nat.xor v216 v208);
  share v223 := (Nat.mul v216 (nat_lit 0x100000001));
  share v224 := (Nat.land (Nat.add (Nat.add v221 (Nat.xor (Nat.xor (Nat.shiftRight v223 (nat_lit 2)) (Nat.shiftRight v223 (nat_lit 13))) (Nat.shiftRight v223 (nat_lit 22)))) (Nat.xor v208 (Nat.land v222 v214))) (nat_lit 0xffffffff));
  share v225 := (Nat.land (Nat.add v192 v221) (nat_lit 0xffffffff));
  share v226 := (Nat.mul v211 (nat_lit 0x100000001));
  share v227 := (Nat.land (Nat.add (Nat.add (Nat.add (Nat.xor (Nat.xor (Nat.shiftRight v226 (nat_lit 17)) (Nat.shiftRight v226 (nat_lit 19))) (Nat.shiftRight v211 (nat_lit 10))) v171) (Nat.xor (Nat.xor (Nat.shiftRight v115 (nat_lit 7)) (Nat.shiftRight v115 (nat_lit 18))) (Nat.shiftRight (nat_lit 256) (nat_lit 3)))) (nat_lit 0)) (nat_lit 0xffffffff));
  share v228 := (Nat.mul v225 (nat_lit 0x100000001));
  share v229 := (Nat.add (Nat.add (Nat.add (Nat.add v201 (Nat.xor (Nat.xor (Nat.shiftRight v228 (nat_lit 6)) (Nat.shiftRight v228 (nat_lit 11))) (Nat.shiftRight v228 (nat_lit 25)))) (Nat.xor v209 (Nat.land v225 (Nat.xor v217 v209)))) (nat_lit 113926993)) v227);
  share v230 := (Nat.xor v224 v216);
  share v231 := (Nat.mul v224 (nat_lit 0x100000001));
  share v232 := (Nat.land (Nat.add (Nat.add v229 (Nat.xor (Nat.xor (Nat.shiftRight v231 (nat_lit 2)) (Nat.shiftRight v231 (nat_lit 13))) (Nat.shiftRight v231 (nat_lit 22)))) (Nat.xor v216 (Nat.land v230 v222))) (nat_lit 0xffffffff));
  share v233 := (Nat.land (Nat.add v200 v229) (nat_lit 0xffffffff));
  share v234 := (Nat.mul v219 (nat_lit 0x100000001));
  share v235 := (Nat.land (Nat.add (Nat.add (Nat.add (Nat.xor (Nat.xor (Nat.shiftRight v234 (nat_lit 17)) (Nat.shiftRight v234 (nat_lit 19))) (Nat.shiftRight v219 (nat_lit 10))) v179) (Nat.xor (Nat.xor (Nat.shiftRight v124 (nat_lit 7)) (Nat.shiftRight v124 (nat_lit 18))) (Nat.shiftRight v108 (nat_lit 3)))) (nat_lit 256)) (nat_lit 0xffffffff));
  share v236 := (Nat.mul v233 (nat_lit 0x100000001));
  share v237 := (Nat.add (Nat.add (Nat.add (Nat.add v209 (Nat.xor (Nat.xor (Nat.shiftRight v236 (nat_lit 6)) (Nat.shiftRight v236 (nat_lit 11))) (Nat.shiftRight v236 (nat_lit 25)))) (Nat.xor v217 (Nat.land v233 (Nat.xor v225 v217)))) (nat_lit 338241895)) v235);
  share v238 := (Nat.xor v232 v224);
  share v239 := (Nat.mul v232 (nat_lit 0x100000001));
  share v240 := (Nat.land (Nat.add (Nat.add v237 (Nat.xor (Nat.xor (Nat.shiftRight v239 (nat_lit 2)) (Nat.shiftRight v239 (nat_lit 13))) (Nat.shiftRight v239 (nat_lit 22)))) (Nat.xor v224 (Nat.land v238 v230))) (nat_lit 0xffffffff));
  share v241 := (Nat.land (Nat.add v208 v237) (nat_lit 0xffffffff));
  share v242 := (Nat.mul v227 (nat_lit 0x100000001));
  share v243 := (Nat.land (Nat.add (Nat.add (Nat.add (Nat.xor (Nat.xor (Nat.shiftRight v242 (nat_lit 17)) (Nat.shiftRight v242 (nat_lit 19))) (Nat.shiftRight v227 (nat_lit 10))) v187) (Nat.xor (Nat.xor (Nat.shiftRight v133 (nat_lit 7)) (Nat.shiftRight v133 (nat_lit 18))) (Nat.shiftRight v117 (nat_lit 3)))) v108) (nat_lit 0xffffffff));
  share v244 := (Nat.mul v241 (nat_lit 0x100000001));
  share v245 := (Nat.add (Nat.add (Nat.add (Nat.add v217 (Nat.xor (Nat.xor (Nat.shiftRight v244 (nat_lit 6)) (Nat.shiftRight v244 (nat_lit 11))) (Nat.shiftRight v244 (nat_lit 25)))) (Nat.xor v225 (Nat.land v241 (Nat.xor v233 v225)))) (nat_lit 666307205)) v243);
  share v246 := (Nat.xor v240 v232);
  share v247 := (Nat.mul v240 (nat_lit 0x100000001));
  share v248 := (Nat.land (Nat.add (Nat.add v245 (Nat.xor (Nat.xor (Nat.shiftRight v247 (nat_lit 2)) (Nat.shiftRight v247 (nat_lit 13))) (Nat.shiftRight v247 (nat_lit 22)))) (Nat.xor v232 (Nat.land v246 v238))) (nat_lit 0xffffffff));
  share v249 := (Nat.land (Nat.add v216 v245) (nat_lit 0xffffffff));
  share v250 := (Nat.mul v235 (nat_lit 0x100000001));
  share v251 := (Nat.land (Nat.add (Nat.add (Nat.add (Nat.xor (Nat.xor (Nat.shiftRight v250 (nat_lit 17)) (Nat.shiftRight v250 (nat_lit 19))) (Nat.shiftRight v235 (nat_lit 10))) v195) (Nat.xor (Nat.xor (Nat.shiftRight v142 (nat_lit 7)) (Nat.shiftRight v142 (nat_lit 18))) (Nat.shiftRight v126 (nat_lit 3)))) v117) (nat_lit 0xffffffff));
  share v252 := (Nat.mul v249 (nat_lit 0x100000001));
  share v253 := (Nat.add (Nat.add (Nat.add (Nat.add v225 (Nat.xor (Nat.xor (Nat.shiftRight v252 (nat_lit 6)) (Nat.shiftRight v252 (nat_lit 11))) (Nat.shiftRight v252 (nat_lit 25)))) (Nat.xor v233 (Nat.land v249 (Nat.xor v241 v233)))) (nat_lit 773529912)) v251);
  share v254 := (Nat.xor v248 v240);
  share v255 := (Nat.mul v248 (nat_lit 0x100000001));
  share v256 := (Nat.land (Nat.add (Nat.add v253 (Nat.xor (Nat.xor (Nat.shiftRight v255 (nat_lit 2)) (Nat.shiftRight v255 (nat_lit 13))) (Nat.shiftRight v255 (nat_lit 22)))) (Nat.xor v240 (Nat.land v254 v246))) (nat_lit 0xffffffff));
  share v257 := (Nat.land (Nat.add v224 v253) (nat_lit 0xffffffff));
  share v258 := (Nat.mul v243 (nat_lit 0x100000001));
  share v259 := (Nat.land (Nat.add (Nat.add (Nat.add (Nat.xor (Nat.xor (Nat.shiftRight v258 (nat_lit 17)) (Nat.shiftRight v258 (nat_lit 19))) (Nat.shiftRight v243 (nat_lit 10))) v203) (Nat.xor (Nat.xor (Nat.shiftRight v151 (nat_lit 7)) (Nat.shiftRight v151 (nat_lit 18))) (Nat.shiftRight v135 (nat_lit 3)))) v126) (nat_lit 0xffffffff));
  share v260 := (Nat.mul v257 (nat_lit 0x100000001));
  share v261 := (Nat.add (Nat.add (Nat.add (Nat.add v233 (Nat.xor (Nat.xor (Nat.shiftRight v260 (nat_lit 6)) (Nat.shiftRight v260 (nat_lit 11))) (Nat.shiftRight v260 (nat_lit 25)))) (Nat.xor v241 (Nat.land v257 (Nat.xor v249 v241)))) (nat_lit 1294757372)) v259);
  share v262 := (Nat.xor v256 v248);
  share v263 := (Nat.mul v256 (nat_lit 0x100000001));
  share v264 := (Nat.land (Nat.add (Nat.add v261 (Nat.xor (Nat.xor (Nat.shiftRight v263 (nat_lit 2)) (Nat.shiftRight v263 (nat_lit 13))) (Nat.shiftRight v263 (nat_lit 22)))) (Nat.xor v248 (Nat.land v262 v254))) (nat_lit 0xffffffff));
  share v265 := (Nat.land (Nat.add v232 v261) (nat_lit 0xffffffff));
  share v266 := (Nat.mul v251 (nat_lit 0x100000001));
  share v267 := (Nat.land (Nat.add (Nat.add (Nat.add (Nat.xor (Nat.xor (Nat.shiftRight v266 (nat_lit 17)) (Nat.shiftRight v266 (nat_lit 19))) (Nat.shiftRight v251 (nat_lit 10))) v211) (Nat.xor (Nat.xor (Nat.shiftRight v160 (nat_lit 7)) (Nat.shiftRight v160 (nat_lit 18))) (Nat.shiftRight v144 (nat_lit 3)))) v135) (nat_lit 0xffffffff));
  share v268 := (Nat.mul v265 (nat_lit 0x100000001));
  share v269 := (Nat.add (Nat.add (Nat.add (Nat.add v241 (Nat.xor (Nat.xor (Nat.shiftRight v268 (nat_lit 6)) (Nat.shiftRight v268 (nat_lit 11))) (Nat.shiftRight v268 (nat_lit 25)))) (Nat.xor v249 (Nat.land v265 (Nat.xor v257 v249)))) (nat_lit 1396182291)) v267);
  share v270 := (Nat.xor v264 v256);
  share v271 := (Nat.mul v264 (nat_lit 0x100000001));
  share v272 := (Nat.land (Nat.add (Nat.add v269 (Nat.xor (Nat.xor (Nat.shiftRight v271 (nat_lit 2)) (Nat.shiftRight v271 (nat_lit 13))) (Nat.shiftRight v271 (nat_lit 22)))) (Nat.xor v256 (Nat.land v270 v262))) (nat_lit 0xffffffff));
  share v273 := (Nat.land (Nat.add v240 v269) (nat_lit 0xffffffff));
  share v274 := (Nat.mul v259 (nat_lit 0x100000001));
  share v275 := (Nat.land (Nat.add (Nat.add (Nat.add (Nat.xor (Nat.xor (Nat.shiftRight v274 (nat_lit 17)) (Nat.shiftRight v274 (nat_lit 19))) (Nat.shiftRight v259 (nat_lit 10))) v219) (Nat.xor (Nat.xor (Nat.shiftRight v169 (nat_lit 7)) (Nat.shiftRight v169 (nat_lit 18))) (Nat.shiftRight v153 (nat_lit 3)))) v144) (nat_lit 0xffffffff));
  share v276 := (Nat.mul v273 (nat_lit 0x100000001));
  share v277 := (Nat.add (Nat.add (Nat.add (Nat.add v249 (Nat.xor (Nat.xor (Nat.shiftRight v276 (nat_lit 6)) (Nat.shiftRight v276 (nat_lit 11))) (Nat.shiftRight v276 (nat_lit 25)))) (Nat.xor v257 (Nat.land v273 (Nat.xor v265 v257)))) (nat_lit 1695183700)) v275);
  share v278 := (Nat.xor v272 v264);
  share v279 := (Nat.mul v272 (nat_lit 0x100000001));
  share v280 := (Nat.land (Nat.add (Nat.add v277 (Nat.xor (Nat.xor (Nat.shiftRight v279 (nat_lit 2)) (Nat.shiftRight v279 (nat_lit 13))) (Nat.shiftRight v279 (nat_lit 22)))) (Nat.xor v264 (Nat.land v278 v270))) (nat_lit 0xffffffff));
  share v281 := (Nat.land (Nat.add v248 v277) (nat_lit 0xffffffff));
  share v282 := (Nat.mul v267 (nat_lit 0x100000001));
  share v283 := (Nat.land (Nat.add (Nat.add (Nat.add (Nat.xor (Nat.xor (Nat.shiftRight v282 (nat_lit 17)) (Nat.shiftRight v282 (nat_lit 19))) (Nat.shiftRight v267 (nat_lit 10))) v227) (Nat.xor (Nat.xor (Nat.shiftRight v178 (nat_lit 7)) (Nat.shiftRight v178 (nat_lit 18))) (Nat.shiftRight v162 (nat_lit 3)))) v153) (nat_lit 0xffffffff));
  share v284 := (Nat.mul v281 (nat_lit 0x100000001));
  share v285 := (Nat.add (Nat.add (Nat.add (Nat.add v257 (Nat.xor (Nat.xor (Nat.shiftRight v284 (nat_lit 6)) (Nat.shiftRight v284 (nat_lit 11))) (Nat.shiftRight v284 (nat_lit 25)))) (Nat.xor v265 (Nat.land v281 (Nat.xor v273 v265)))) (nat_lit 1986661051)) v283);
  share v286 := (Nat.xor v280 v272);
  share v287 := (Nat.mul v280 (nat_lit 0x100000001));
  share v288 := (Nat.land (Nat.add (Nat.add v285 (Nat.xor (Nat.xor (Nat.shiftRight v287 (nat_lit 2)) (Nat.shiftRight v287 (nat_lit 13))) (Nat.shiftRight v287 (nat_lit 22)))) (Nat.xor v272 (Nat.land v286 v278))) (nat_lit 0xffffffff));
  share v289 := (Nat.land (Nat.add v256 v285) (nat_lit 0xffffffff));
  share v290 := (Nat.mul v275 (nat_lit 0x100000001));
  share v291 := (Nat.land (Nat.add (Nat.add (Nat.add (Nat.xor (Nat.xor (Nat.shiftRight v290 (nat_lit 17)) (Nat.shiftRight v290 (nat_lit 19))) (Nat.shiftRight v275 (nat_lit 10))) v235) (Nat.xor (Nat.xor (Nat.shiftRight v186 (nat_lit 7)) (Nat.shiftRight v186 (nat_lit 18))) (Nat.shiftRight v171 (nat_lit 3)))) v162) (nat_lit 0xffffffff));
  share v292 := (Nat.mul v289 (nat_lit 0x100000001));
  share v293 := (Nat.add (Nat.add (Nat.add (Nat.add v265 (Nat.xor (Nat.xor (Nat.shiftRight v292 (nat_lit 6)) (Nat.shiftRight v292 (nat_lit 11))) (Nat.shiftRight v292 (nat_lit 25)))) (Nat.xor v273 (Nat.land v289 (Nat.xor v281 v273)))) (nat_lit 2177026350)) v291);
  share v294 := (Nat.xor v288 v280);
  share v295 := (Nat.mul v288 (nat_lit 0x100000001));
  share v296 := (Nat.land (Nat.add (Nat.add v293 (Nat.xor (Nat.xor (Nat.shiftRight v295 (nat_lit 2)) (Nat.shiftRight v295 (nat_lit 13))) (Nat.shiftRight v295 (nat_lit 22)))) (Nat.xor v280 (Nat.land v294 v286))) (nat_lit 0xffffffff));
  share v297 := (Nat.land (Nat.add v264 v293) (nat_lit 0xffffffff));
  share v298 := (Nat.mul v283 (nat_lit 0x100000001));
  share v299 := (Nat.land (Nat.add (Nat.add (Nat.add (Nat.xor (Nat.xor (Nat.shiftRight v298 (nat_lit 17)) (Nat.shiftRight v298 (nat_lit 19))) (Nat.shiftRight v283 (nat_lit 10))) v243) (Nat.xor (Nat.xor (Nat.shiftRight v194 (nat_lit 7)) (Nat.shiftRight v194 (nat_lit 18))) (Nat.shiftRight v179 (nat_lit 3)))) v171) (nat_lit 0xffffffff));
  share v300 := (Nat.mul v297 (nat_lit 0x100000001));
  share v301 := (Nat.add (Nat.add (Nat.add (Nat.add v273 (Nat.xor (Nat.xor (Nat.shiftRight v300 (nat_lit 6)) (Nat.shiftRight v300 (nat_lit 11))) (Nat.shiftRight v300 (nat_lit 25)))) (Nat.xor v281 (Nat.land v297 (Nat.xor v289 v281)))) (nat_lit 2456956037)) v299);
  share v302 := (Nat.xor v296 v288);
  share v303 := (Nat.mul v296 (nat_lit 0x100000001));
  share v304 := (Nat.land (Nat.add (Nat.add v301 (Nat.xor (Nat.xor (Nat.shiftRight v303 (nat_lit 2)) (Nat.shiftRight v303 (nat_lit 13))) (Nat.shiftRight v303 (nat_lit 22)))) (Nat.xor v288 (Nat.land v302 v294))) (nat_lit 0xffffffff));
  share v305 := (Nat.land (Nat.add v272 v301) (nat_lit 0xffffffff));
  share v306 := (Nat.mul v291 (nat_lit 0x100000001));
  share v307 := (Nat.land (Nat.add (Nat.add (Nat.add (Nat.xor (Nat.xor (Nat.shiftRight v306 (nat_lit 17)) (Nat.shiftRight v306 (nat_lit 19))) (Nat.shiftRight v291 (nat_lit 10))) v251) (Nat.xor (Nat.xor (Nat.shiftRight v202 (nat_lit 7)) (Nat.shiftRight v202 (nat_lit 18))) (Nat.shiftRight v187 (nat_lit 3)))) v179) (nat_lit 0xffffffff));
  share v308 := (Nat.mul v305 (nat_lit 0x100000001));
  share v309 := (Nat.add (Nat.add (Nat.add (Nat.add v281 (Nat.xor (Nat.xor (Nat.shiftRight v308 (nat_lit 6)) (Nat.shiftRight v308 (nat_lit 11))) (Nat.shiftRight v308 (nat_lit 25)))) (Nat.xor v289 (Nat.land v305 (Nat.xor v297 v289)))) (nat_lit 2730485921)) v307);
  share v310 := (Nat.xor v304 v296);
  share v311 := (Nat.mul v304 (nat_lit 0x100000001));
  share v312 := (Nat.land (Nat.add (Nat.add v309 (Nat.xor (Nat.xor (Nat.shiftRight v311 (nat_lit 2)) (Nat.shiftRight v311 (nat_lit 13))) (Nat.shiftRight v311 (nat_lit 22)))) (Nat.xor v296 (Nat.land v310 v302))) (nat_lit 0xffffffff));
  share v313 := (Nat.land (Nat.add v280 v309) (nat_lit 0xffffffff));
  share v314 := (Nat.mul v299 (nat_lit 0x100000001));
  share v315 := (Nat.land (Nat.add (Nat.add (Nat.add (Nat.xor (Nat.xor (Nat.shiftRight v314 (nat_lit 17)) (Nat.shiftRight v314 (nat_lit 19))) (Nat.shiftRight v299 (nat_lit 10))) v259) (Nat.xor (Nat.xor (Nat.shiftRight v210 (nat_lit 7)) (Nat.shiftRight v210 (nat_lit 18))) (Nat.shiftRight v195 (nat_lit 3)))) v187) (nat_lit 0xffffffff));
  share v316 := (Nat.mul v313 (nat_lit 0x100000001));
  share v317 := (Nat.add (Nat.add (Nat.add (Nat.add v289 (Nat.xor (Nat.xor (Nat.shiftRight v316 (nat_lit 6)) (Nat.shiftRight v316 (nat_lit 11))) (Nat.shiftRight v316 (nat_lit 25)))) (Nat.xor v297 (Nat.land v313 (Nat.xor v305 v297)))) (nat_lit 2820302411)) v315);
  share v318 := (Nat.xor v312 v304);
  share v319 := (Nat.mul v312 (nat_lit 0x100000001));
  share v320 := (Nat.land (Nat.add (Nat.add v317 (Nat.xor (Nat.xor (Nat.shiftRight v319 (nat_lit 2)) (Nat.shiftRight v319 (nat_lit 13))) (Nat.shiftRight v319 (nat_lit 22)))) (Nat.xor v304 (Nat.land v318 v310))) (nat_lit 0xffffffff));
  share v321 := (Nat.land (Nat.add v288 v317) (nat_lit 0xffffffff));
  share v322 := (Nat.mul v307 (nat_lit 0x100000001));
  share v323 := (Nat.land (Nat.add (Nat.add (Nat.add (Nat.xor (Nat.xor (Nat.shiftRight v322 (nat_lit 17)) (Nat.shiftRight v322 (nat_lit 19))) (Nat.shiftRight v307 (nat_lit 10))) v267) (Nat.xor (Nat.xor (Nat.shiftRight v218 (nat_lit 7)) (Nat.shiftRight v218 (nat_lit 18))) (Nat.shiftRight v203 (nat_lit 3)))) v195) (nat_lit 0xffffffff));
  share v324 := (Nat.mul v321 (nat_lit 0x100000001));
  share v325 := (Nat.add (Nat.add (Nat.add (Nat.add v297 (Nat.xor (Nat.xor (Nat.shiftRight v324 (nat_lit 6)) (Nat.shiftRight v324 (nat_lit 11))) (Nat.shiftRight v324 (nat_lit 25)))) (Nat.xor v305 (Nat.land v321 (Nat.xor v313 v305)))) (nat_lit 3259730800)) v323);
  share v326 := (Nat.xor v320 v312);
  share v327 := (Nat.mul v320 (nat_lit 0x100000001));
  share v328 := (Nat.land (Nat.add (Nat.add v325 (Nat.xor (Nat.xor (Nat.shiftRight v327 (nat_lit 2)) (Nat.shiftRight v327 (nat_lit 13))) (Nat.shiftRight v327 (nat_lit 22)))) (Nat.xor v312 (Nat.land v326 v318))) (nat_lit 0xffffffff));
  share v329 := (Nat.land (Nat.add v296 v325) (nat_lit 0xffffffff));
  share v330 := (Nat.mul v315 (nat_lit 0x100000001));
  share v331 := (Nat.land (Nat.add (Nat.add (Nat.add (Nat.xor (Nat.xor (Nat.shiftRight v330 (nat_lit 17)) (Nat.shiftRight v330 (nat_lit 19))) (Nat.shiftRight v315 (nat_lit 10))) v275) (Nat.xor (Nat.xor (Nat.shiftRight v226 (nat_lit 7)) (Nat.shiftRight v226 (nat_lit 18))) (Nat.shiftRight v211 (nat_lit 3)))) v203) (nat_lit 0xffffffff));
  share v332 := (Nat.mul v329 (nat_lit 0x100000001));
  share v333 := (Nat.add (Nat.add (Nat.add (Nat.add v305 (Nat.xor (Nat.xor (Nat.shiftRight v332 (nat_lit 6)) (Nat.shiftRight v332 (nat_lit 11))) (Nat.shiftRight v332 (nat_lit 25)))) (Nat.xor v313 (Nat.land v329 (Nat.xor v321 v313)))) (nat_lit 3345764771)) v331);
  share v334 := (Nat.xor v328 v320);
  share v335 := (Nat.mul v328 (nat_lit 0x100000001));
  share v336 := (Nat.land (Nat.add (Nat.add v333 (Nat.xor (Nat.xor (Nat.shiftRight v335 (nat_lit 2)) (Nat.shiftRight v335 (nat_lit 13))) (Nat.shiftRight v335 (nat_lit 22)))) (Nat.xor v320 (Nat.land v334 v326))) (nat_lit 0xffffffff));
  share v337 := (Nat.land (Nat.add v304 v333) (nat_lit 0xffffffff));
  share v338 := (Nat.mul v323 (nat_lit 0x100000001));
  share v339 := (Nat.land (Nat.add (Nat.add (Nat.add (Nat.xor (Nat.xor (Nat.shiftRight v338 (nat_lit 17)) (Nat.shiftRight v338 (nat_lit 19))) (Nat.shiftRight v323 (nat_lit 10))) v283) (Nat.xor (Nat.xor (Nat.shiftRight v234 (nat_lit 7)) (Nat.shiftRight v234 (nat_lit 18))) (Nat.shiftRight v219 (nat_lit 3)))) v211) (nat_lit 0xffffffff));
  share v340 := (Nat.mul v337 (nat_lit 0x100000001));
  share v341 := (Nat.add (Nat.add (Nat.add (Nat.add v313 (Nat.xor (Nat.xor (Nat.shiftRight v340 (nat_lit 6)) (Nat.shiftRight v340 (nat_lit 11))) (Nat.shiftRight v340 (nat_lit 25)))) (Nat.xor v321 (Nat.land v337 (Nat.xor v329 v321)))) (nat_lit 3516065817)) v339);
  share v342 := (Nat.xor v336 v328);
  share v343 := (Nat.mul v336 (nat_lit 0x100000001));
  share v344 := (Nat.land (Nat.add (Nat.add v341 (Nat.xor (Nat.xor (Nat.shiftRight v343 (nat_lit 2)) (Nat.shiftRight v343 (nat_lit 13))) (Nat.shiftRight v343 (nat_lit 22)))) (Nat.xor v328 (Nat.land v342 v334))) (nat_lit 0xffffffff));
  share v345 := (Nat.land (Nat.add v312 v341) (nat_lit 0xffffffff));
  share v346 := (Nat.mul v331 (nat_lit 0x100000001));
  share v347 := (Nat.land (Nat.add (Nat.add (Nat.add (Nat.xor (Nat.xor (Nat.shiftRight v346 (nat_lit 17)) (Nat.shiftRight v346 (nat_lit 19))) (Nat.shiftRight v331 (nat_lit 10))) v291) (Nat.xor (Nat.xor (Nat.shiftRight v242 (nat_lit 7)) (Nat.shiftRight v242 (nat_lit 18))) (Nat.shiftRight v227 (nat_lit 3)))) v219) (nat_lit 0xffffffff));
  share v348 := (Nat.mul v345 (nat_lit 0x100000001));
  share v349 := (Nat.add (Nat.add (Nat.add (Nat.add v321 (Nat.xor (Nat.xor (Nat.shiftRight v348 (nat_lit 6)) (Nat.shiftRight v348 (nat_lit 11))) (Nat.shiftRight v348 (nat_lit 25)))) (Nat.xor v329 (Nat.land v345 (Nat.xor v337 v329)))) (nat_lit 3600352804)) v347);
  share v350 := (Nat.xor v344 v336);
  share v351 := (Nat.mul v344 (nat_lit 0x100000001));
  share v352 := (Nat.land (Nat.add (Nat.add v349 (Nat.xor (Nat.xor (Nat.shiftRight v351 (nat_lit 2)) (Nat.shiftRight v351 (nat_lit 13))) (Nat.shiftRight v351 (nat_lit 22)))) (Nat.xor v336 (Nat.land v350 v342))) (nat_lit 0xffffffff));
  share v353 := (Nat.land (Nat.add v320 v349) (nat_lit 0xffffffff));
  share v354 := (Nat.mul v339 (nat_lit 0x100000001));
  share v355 := (Nat.land (Nat.add (Nat.add (Nat.add (Nat.xor (Nat.xor (Nat.shiftRight v354 (nat_lit 17)) (Nat.shiftRight v354 (nat_lit 19))) (Nat.shiftRight v339 (nat_lit 10))) v299) (Nat.xor (Nat.xor (Nat.shiftRight v250 (nat_lit 7)) (Nat.shiftRight v250 (nat_lit 18))) (Nat.shiftRight v235 (nat_lit 3)))) v227) (nat_lit 0xffffffff));
  share v356 := (Nat.mul v353 (nat_lit 0x100000001));
  share v357 := (Nat.add (Nat.add (Nat.add (Nat.add v329 (Nat.xor (Nat.xor (Nat.shiftRight v356 (nat_lit 6)) (Nat.shiftRight v356 (nat_lit 11))) (Nat.shiftRight v356 (nat_lit 25)))) (Nat.xor v337 (Nat.land v353 (Nat.xor v345 v337)))) (nat_lit 4094571909)) v355);
  share v358 := (Nat.xor v352 v344);
  share v359 := (Nat.mul v352 (nat_lit 0x100000001));
  share v360 := (Nat.land (Nat.add (Nat.add v357 (Nat.xor (Nat.xor (Nat.shiftRight v359 (nat_lit 2)) (Nat.shiftRight v359 (nat_lit 13))) (Nat.shiftRight v359 (nat_lit 22)))) (Nat.xor v344 (Nat.land v358 v350))) (nat_lit 0xffffffff));
  share v361 := (Nat.land (Nat.add v328 v357) (nat_lit 0xffffffff));
  share v362 := (Nat.mul v347 (nat_lit 0x100000001));
  share v363 := (Nat.land (Nat.add (Nat.add (Nat.add (Nat.xor (Nat.xor (Nat.shiftRight v362 (nat_lit 17)) (Nat.shiftRight v362 (nat_lit 19))) (Nat.shiftRight v347 (nat_lit 10))) v307) (Nat.xor (Nat.xor (Nat.shiftRight v258 (nat_lit 7)) (Nat.shiftRight v258 (nat_lit 18))) (Nat.shiftRight v243 (nat_lit 3)))) v235) (nat_lit 0xffffffff));
  share v364 := (Nat.mul v361 (nat_lit 0x100000001));
  share v365 := (Nat.add (Nat.add (Nat.add (Nat.add v337 (Nat.xor (Nat.xor (Nat.shiftRight v364 (nat_lit 6)) (Nat.shiftRight v364 (nat_lit 11))) (Nat.shiftRight v364 (nat_lit 25)))) (Nat.xor v345 (Nat.land v361 (Nat.xor v353 v345)))) (nat_lit 275423344)) v363);
  share v366 := (Nat.xor v360 v352);
  share v367 := (Nat.mul v360 (nat_lit 0x100000001));
  share v368 := (Nat.land (Nat.add (Nat.add v365 (Nat.xor (Nat.xor (Nat.shiftRight v367 (nat_lit 2)) (Nat.shiftRight v367 (nat_lit 13))) (Nat.shiftRight v367 (nat_lit 22)))) (Nat.xor v352 (Nat.land v366 v358))) (nat_lit 0xffffffff));
  share v369 := (Nat.land (Nat.add v336 v365) (nat_lit 0xffffffff));
  share v370 := (Nat.mul v355 (nat_lit 0x100000001));
  share v371 := (Nat.land (Nat.add (Nat.add (Nat.add (Nat.xor (Nat.xor (Nat.shiftRight v370 (nat_lit 17)) (Nat.shiftRight v370 (nat_lit 19))) (Nat.shiftRight v355 (nat_lit 10))) v315) (Nat.xor (Nat.xor (Nat.shiftRight v266 (nat_lit 7)) (Nat.shiftRight v266 (nat_lit 18))) (Nat.shiftRight v251 (nat_lit 3)))) v243) (nat_lit 0xffffffff));
  share v372 := (Nat.mul v369 (nat_lit 0x100000001));
  share v373 := (Nat.add (Nat.add (Nat.add (Nat.add v345 (Nat.xor (Nat.xor (Nat.shiftRight v372 (nat_lit 6)) (Nat.shiftRight v372 (nat_lit 11))) (Nat.shiftRight v372 (nat_lit 25)))) (Nat.xor v353 (Nat.land v369 (Nat.xor v361 v353)))) (nat_lit 430227734)) v371);
  share v374 := (Nat.xor v368 v360);
  share v375 := (Nat.mul v368 (nat_lit 0x100000001));
  share v376 := (Nat.land (Nat.add (Nat.add v373 (Nat.xor (Nat.xor (Nat.shiftRight v375 (nat_lit 2)) (Nat.shiftRight v375 (nat_lit 13))) (Nat.shiftRight v375 (nat_lit 22)))) (Nat.xor v360 (Nat.land v374 v366))) (nat_lit 0xffffffff));
  share v377 := (Nat.land (Nat.add v344 v373) (nat_lit 0xffffffff));
  share v378 := (Nat.mul v363 (nat_lit 0x100000001));
  share v379 := (Nat.land (Nat.add (Nat.add (Nat.add (Nat.xor (Nat.xor (Nat.shiftRight v378 (nat_lit 17)) (Nat.shiftRight v378 (nat_lit 19))) (Nat.shiftRight v363 (nat_lit 10))) v323) (Nat.xor (Nat.xor (Nat.shiftRight v274 (nat_lit 7)) (Nat.shiftRight v274 (nat_lit 18))) (Nat.shiftRight v259 (nat_lit 3)))) v251) (nat_lit 0xffffffff));
  share v380 := (Nat.mul v377 (nat_lit 0x100000001));
  share v381 := (Nat.add (Nat.add (Nat.add (Nat.add v353 (Nat.xor (Nat.xor (Nat.shiftRight v380 (nat_lit 6)) (Nat.shiftRight v380 (nat_lit 11))) (Nat.shiftRight v380 (nat_lit 25)))) (Nat.xor v361 (Nat.land v377 (Nat.xor v369 v361)))) (nat_lit 506948616)) v379);
  share v382 := (Nat.xor v376 v368);
  share v383 := (Nat.mul v376 (nat_lit 0x100000001));
  share v384 := (Nat.land (Nat.add (Nat.add v381 (Nat.xor (Nat.xor (Nat.shiftRight v383 (nat_lit 2)) (Nat.shiftRight v383 (nat_lit 13))) (Nat.shiftRight v383 (nat_lit 22)))) (Nat.xor v368 (Nat.land v382 v374))) (nat_lit 0xffffffff));
  share v385 := (Nat.land (Nat.add v352 v381) (nat_lit 0xffffffff));
  share v386 := (Nat.mul v371 (nat_lit 0x100000001));
  share v387 := (Nat.land (Nat.add (Nat.add (Nat.add (Nat.xor (Nat.xor (Nat.shiftRight v386 (nat_lit 17)) (Nat.shiftRight v386 (nat_lit 19))) (Nat.shiftRight v371 (nat_lit 10))) v331) (Nat.xor (Nat.xor (Nat.shiftRight v282 (nat_lit 7)) (Nat.shiftRight v282 (nat_lit 18))) (Nat.shiftRight v267 (nat_lit 3)))) v259) (nat_lit 0xffffffff));
  share v388 := (Nat.mul v385 (nat_lit 0x100000001));
  share v389 := (Nat.add (Nat.add (Nat.add (Nat.add v361 (Nat.xor (Nat.xor (Nat.shiftRight v388 (nat_lit 6)) (Nat.shiftRight v388 (nat_lit 11))) (Nat.shiftRight v388 (nat_lit 25)))) (Nat.xor v369 (Nat.land v385 (Nat.xor v377 v369)))) (nat_lit 659060556)) v387);
  share v390 := (Nat.xor v384 v376);
  share v391 := (Nat.mul v384 (nat_lit 0x100000001));
  share v392 := (Nat.land (Nat.add (Nat.add v389 (Nat.xor (Nat.xor (Nat.shiftRight v391 (nat_lit 2)) (Nat.shiftRight v391 (nat_lit 13))) (Nat.shiftRight v391 (nat_lit 22)))) (Nat.xor v376 (Nat.land v390 v382))) (nat_lit 0xffffffff));
  share v393 := (Nat.land (Nat.add v360 v389) (nat_lit 0xffffffff));
  share v394 := (Nat.mul v379 (nat_lit 0x100000001));
  share v395 := (Nat.land (Nat.add (Nat.add (Nat.add (Nat.xor (Nat.xor (Nat.shiftRight v394 (nat_lit 17)) (Nat.shiftRight v394 (nat_lit 19))) (Nat.shiftRight v379 (nat_lit 10))) v339) (Nat.xor (Nat.xor (Nat.shiftRight v290 (nat_lit 7)) (Nat.shiftRight v290 (nat_lit 18))) (Nat.shiftRight v275 (nat_lit 3)))) v267) (nat_lit 0xffffffff));
  share v396 := (Nat.mul v393 (nat_lit 0x100000001));
  share v397 := (Nat.add (Nat.add (Nat.add (Nat.add v369 (Nat.xor (Nat.xor (Nat.shiftRight v396 (nat_lit 6)) (Nat.shiftRight v396 (nat_lit 11))) (Nat.shiftRight v396 (nat_lit 25)))) (Nat.xor v377 (Nat.land v393 (Nat.xor v385 v377)))) (nat_lit 883997877)) v395);
  share v398 := (Nat.xor v392 v384);
  share v399 := (Nat.mul v392 (nat_lit 0x100000001));
  share v400 := (Nat.land (Nat.add (Nat.add v397 (Nat.xor (Nat.xor (Nat.shiftRight v399 (nat_lit 2)) (Nat.shiftRight v399 (nat_lit 13))) (Nat.shiftRight v399 (nat_lit 22)))) (Nat.xor v384 (Nat.land v398 v390))) (nat_lit 0xffffffff));
  share v401 := (Nat.land (Nat.add v368 v397) (nat_lit 0xffffffff));
  share v402 := (Nat.mul v387 (nat_lit 0x100000001));
  share v403 := (Nat.land (Nat.add (Nat.add (Nat.add (Nat.xor (Nat.xor (Nat.shiftRight v402 (nat_lit 17)) (Nat.shiftRight v402 (nat_lit 19))) (Nat.shiftRight v387 (nat_lit 10))) v347) (Nat.xor (Nat.xor (Nat.shiftRight v298 (nat_lit 7)) (Nat.shiftRight v298 (nat_lit 18))) (Nat.shiftRight v283 (nat_lit 3)))) v275) (nat_lit 0xffffffff));
  share v404 := (Nat.mul v401 (nat_lit 0x100000001));
  share v405 := (Nat.add (Nat.add (Nat.add (Nat.add v377 (Nat.xor (Nat.xor (Nat.shiftRight v404 (nat_lit 6)) (Nat.shiftRight v404 (nat_lit 11))) (Nat.shiftRight v404 (nat_lit 25)))) (Nat.xor v385 (Nat.land v401 (Nat.xor v393 v385)))) (nat_lit 958139571)) v403);
  share v406 := (Nat.xor v400 v392);
  share v407 := (Nat.mul v400 (nat_lit 0x100000001));
  share v408 := (Nat.land (Nat.add (Nat.add v405 (Nat.xor (Nat.xor (Nat.shiftRight v407 (nat_lit 2)) (Nat.shiftRight v407 (nat_lit 13))) (Nat.shiftRight v407 (nat_lit 22)))) (Nat.xor v392 (Nat.land v406 v398))) (nat_lit 0xffffffff));
  share v409 := (Nat.land (Nat.add v376 v405) (nat_lit 0xffffffff));
  share v410 := (Nat.mul v395 (nat_lit 0x100000001));
  share v411 := (Nat.land (Nat.add (Nat.add (Nat.add (Nat.xor (Nat.xor (Nat.shiftRight v410 (nat_lit 17)) (Nat.shiftRight v410 (nat_lit 19))) (Nat.shiftRight v395 (nat_lit 10))) v355) (Nat.xor (Nat.xor (Nat.shiftRight v306 (nat_lit 7)) (Nat.shiftRight v306 (nat_lit 18))) (Nat.shiftRight v291 (nat_lit 3)))) v283) (nat_lit 0xffffffff));
  share v412 := (Nat.mul v409 (nat_lit 0x100000001));
  share v413 := (Nat.add (Nat.add (Nat.add (Nat.add v385 (Nat.xor (Nat.xor (Nat.shiftRight v412 (nat_lit 6)) (Nat.shiftRight v412 (nat_lit 11))) (Nat.shiftRight v412 (nat_lit 25)))) (Nat.xor v393 (Nat.land v409 (Nat.xor v401 v393)))) (nat_lit 1322822218)) v411);
  share v414 := (Nat.xor v408 v400);
  share v415 := (Nat.mul v408 (nat_lit 0x100000001));
  share v416 := (Nat.land (Nat.add (Nat.add v413 (Nat.xor (Nat.xor (Nat.shiftRight v415 (nat_lit 2)) (Nat.shiftRight v415 (nat_lit 13))) (Nat.shiftRight v415 (nat_lit 22)))) (Nat.xor v400 (Nat.land v414 v406))) (nat_lit 0xffffffff));
  share v417 := (Nat.land (Nat.add v384 v413) (nat_lit 0xffffffff));
  share v418 := (Nat.mul v403 (nat_lit 0x100000001));
  share v419 := (Nat.land (Nat.add (Nat.add (Nat.add (Nat.xor (Nat.xor (Nat.shiftRight v418 (nat_lit 17)) (Nat.shiftRight v418 (nat_lit 19))) (Nat.shiftRight v403 (nat_lit 10))) v363) (Nat.xor (Nat.xor (Nat.shiftRight v314 (nat_lit 7)) (Nat.shiftRight v314 (nat_lit 18))) (Nat.shiftRight v299 (nat_lit 3)))) v291) (nat_lit 0xffffffff));
  share v420 := (Nat.mul v417 (nat_lit 0x100000001));
  share v421 := (Nat.add (Nat.add (Nat.add (Nat.add v393 (Nat.xor (Nat.xor (Nat.shiftRight v420 (nat_lit 6)) (Nat.shiftRight v420 (nat_lit 11))) (Nat.shiftRight v420 (nat_lit 25)))) (Nat.xor v401 (Nat.land v417 (Nat.xor v409 v401)))) (nat_lit 1537002063)) v419);
  share v422 := (Nat.xor v416 v408);
  share v423 := (Nat.mul v416 (nat_lit 0x100000001));
  share v424 := (Nat.land (Nat.add (Nat.add v421 (Nat.xor (Nat.xor (Nat.shiftRight v423 (nat_lit 2)) (Nat.shiftRight v423 (nat_lit 13))) (Nat.shiftRight v423 (nat_lit 22)))) (Nat.xor v408 (Nat.land v422 v414))) (nat_lit 0xffffffff));
  share v425 := (Nat.land (Nat.add v392 v421) (nat_lit 0xffffffff));
  share v426 := (Nat.mul v411 (nat_lit 0x100000001));
  share v427 := (Nat.land (Nat.add (Nat.add (Nat.add (Nat.xor (Nat.xor (Nat.shiftRight v426 (nat_lit 17)) (Nat.shiftRight v426 (nat_lit 19))) (Nat.shiftRight v411 (nat_lit 10))) v371) (Nat.xor (Nat.xor (Nat.shiftRight v322 (nat_lit 7)) (Nat.shiftRight v322 (nat_lit 18))) (Nat.shiftRight v307 (nat_lit 3)))) v299) (nat_lit 0xffffffff));
  share v428 := (Nat.mul v425 (nat_lit 0x100000001));
  share v429 := (Nat.add (Nat.add (Nat.add (Nat.add v401 (Nat.xor (Nat.xor (Nat.shiftRight v428 (nat_lit 6)) (Nat.shiftRight v428 (nat_lit 11))) (Nat.shiftRight v428 (nat_lit 25)))) (Nat.xor v409 (Nat.land v425 (Nat.xor v417 v409)))) (nat_lit 1747873779)) v427);
  share v430 := (Nat.xor v424 v416);
  share v431 := (Nat.mul v424 (nat_lit 0x100000001));
  share v432 := (Nat.land (Nat.add (Nat.add v429 (Nat.xor (Nat.xor (Nat.shiftRight v431 (nat_lit 2)) (Nat.shiftRight v431 (nat_lit 13))) (Nat.shiftRight v431 (nat_lit 22)))) (Nat.xor v416 (Nat.land v430 v422))) (nat_lit 0xffffffff));
  share v433 := (Nat.land (Nat.add v400 v429) (nat_lit 0xffffffff));
  share v434 := (Nat.mul v419 (nat_lit 0x100000001));
  share v435 := (Nat.land (Nat.add (Nat.add (Nat.add (Nat.xor (Nat.xor (Nat.shiftRight v434 (nat_lit 17)) (Nat.shiftRight v434 (nat_lit 19))) (Nat.shiftRight v419 (nat_lit 10))) v379) (Nat.xor (Nat.xor (Nat.shiftRight v330 (nat_lit 7)) (Nat.shiftRight v330 (nat_lit 18))) (Nat.shiftRight v315 (nat_lit 3)))) v307) (nat_lit 0xffffffff));
  share v436 := (Nat.mul v433 (nat_lit 0x100000001));
  share v437 := (Nat.add (Nat.add (Nat.add (Nat.add v409 (Nat.xor (Nat.xor (Nat.shiftRight v436 (nat_lit 6)) (Nat.shiftRight v436 (nat_lit 11))) (Nat.shiftRight v436 (nat_lit 25)))) (Nat.xor v417 (Nat.land v433 (Nat.xor v425 v417)))) (nat_lit 1955562222)) v435);
  share v438 := (Nat.xor v432 v424);
  share v439 := (Nat.mul v432 (nat_lit 0x100000001));
  share v440 := (Nat.land (Nat.add (Nat.add v437 (Nat.xor (Nat.xor (Nat.shiftRight v439 (nat_lit 2)) (Nat.shiftRight v439 (nat_lit 13))) (Nat.shiftRight v439 (nat_lit 22)))) (Nat.xor v424 (Nat.land v438 v430))) (nat_lit 0xffffffff));
  share v441 := (Nat.land (Nat.add v408 v437) (nat_lit 0xffffffff));
  share v442 := (Nat.mul v427 (nat_lit 0x100000001));
  share v443 := (Nat.land (Nat.add (Nat.add (Nat.add (Nat.xor (Nat.xor (Nat.shiftRight v442 (nat_lit 17)) (Nat.shiftRight v442 (nat_lit 19))) (Nat.shiftRight v427 (nat_lit 10))) v387) (Nat.xor (Nat.xor (Nat.shiftRight v338 (nat_lit 7)) (Nat.shiftRight v338 (nat_lit 18))) (Nat.shiftRight v323 (nat_lit 3)))) v315) (nat_lit 0xffffffff));
  share v444 := (Nat.mul v441 (nat_lit 0x100000001));
  share v445 := (Nat.add (Nat.add (Nat.add (Nat.add v417 (Nat.xor (Nat.xor (Nat.shiftRight v444 (nat_lit 6)) (Nat.shiftRight v444 (nat_lit 11))) (Nat.shiftRight v444 (nat_lit 25)))) (Nat.xor v425 (Nat.land v441 (Nat.xor v433 v425)))) (nat_lit 2024104815)) v443);
  share v446 := (Nat.xor v440 v432);
  share v447 := (Nat.mul v440 (nat_lit 0x100000001));
  share v448 := (Nat.land (Nat.add (Nat.add v445 (Nat.xor (Nat.xor (Nat.shiftRight v447 (nat_lit 2)) (Nat.shiftRight v447 (nat_lit 13))) (Nat.shiftRight v447 (nat_lit 22)))) (Nat.xor v432 (Nat.land v446 v438))) (nat_lit 0xffffffff));
  share v449 := (Nat.land (Nat.add v416 v445) (nat_lit 0xffffffff));
  share v450 := (Nat.mul v435 (nat_lit 0x100000001));
  share v451 := (Nat.land (Nat.add (Nat.add (Nat.add (Nat.xor (Nat.xor (Nat.shiftRight v450 (nat_lit 17)) (Nat.shiftRight v450 (nat_lit 19))) (Nat.shiftRight v435 (nat_lit 10))) v395) (Nat.xor (Nat.xor (Nat.shiftRight v346 (nat_lit 7)) (Nat.shiftRight v346 (nat_lit 18))) (Nat.shiftRight v331 (nat_lit 3)))) v323) (nat_lit 0xffffffff));
  share v452 := (Nat.mul v449 (nat_lit 0x100000001));
  share v453 := (Nat.add (Nat.add (Nat.add (Nat.add v425 (Nat.xor (Nat.xor (Nat.shiftRight v452 (nat_lit 6)) (Nat.shiftRight v452 (nat_lit 11))) (Nat.shiftRight v452 (nat_lit 25)))) (Nat.xor v433 (Nat.land v449 (Nat.xor v441 v433)))) (nat_lit 2227730452)) v451);
  share v454 := (Nat.xor v448 v440);
  share v455 := (Nat.mul v448 (nat_lit 0x100000001));
  share v456 := (Nat.land (Nat.add (Nat.add v453 (Nat.xor (Nat.xor (Nat.shiftRight v455 (nat_lit 2)) (Nat.shiftRight v455 (nat_lit 13))) (Nat.shiftRight v455 (nat_lit 22)))) (Nat.xor v440 (Nat.land v454 v446))) (nat_lit 0xffffffff));
  share v457 := (Nat.land (Nat.add v424 v453) (nat_lit 0xffffffff));
  share v458 := (Nat.mul v443 (nat_lit 0x100000001));
  share v459 := (Nat.land (Nat.add (Nat.add (Nat.add (Nat.xor (Nat.xor (Nat.shiftRight v458 (nat_lit 17)) (Nat.shiftRight v458 (nat_lit 19))) (Nat.shiftRight v443 (nat_lit 10))) v403) (Nat.xor (Nat.xor (Nat.shiftRight v354 (nat_lit 7)) (Nat.shiftRight v354 (nat_lit 18))) (Nat.shiftRight v339 (nat_lit 3)))) v331) (nat_lit 0xffffffff));
  share v460 := (Nat.mul v457 (nat_lit 0x100000001));
  share v461 := (Nat.add (Nat.add (Nat.add (Nat.add v433 (Nat.xor (Nat.xor (Nat.shiftRight v460 (nat_lit 6)) (Nat.shiftRight v460 (nat_lit 11))) (Nat.shiftRight v460 (nat_lit 25)))) (Nat.xor v441 (Nat.land v457 (Nat.xor v449 v441)))) (nat_lit 2361852424)) v459);
  share v462 := (Nat.xor v456 v448);
  share v463 := (Nat.mul v456 (nat_lit 0x100000001));
  share v464 := (Nat.land (Nat.add (Nat.add v461 (Nat.xor (Nat.xor (Nat.shiftRight v463 (nat_lit 2)) (Nat.shiftRight v463 (nat_lit 13))) (Nat.shiftRight v463 (nat_lit 22)))) (Nat.xor v448 (Nat.land v462 v454))) (nat_lit 0xffffffff));
  share v465 := (Nat.land (Nat.add v432 v461) (nat_lit 0xffffffff));
  share v466 := (Nat.mul v451 (nat_lit 0x100000001));
  share v467 := (Nat.land (Nat.add (Nat.add (Nat.add (Nat.xor (Nat.xor (Nat.shiftRight v466 (nat_lit 17)) (Nat.shiftRight v466 (nat_lit 19))) (Nat.shiftRight v451 (nat_lit 10))) v411) (Nat.xor (Nat.xor (Nat.shiftRight v362 (nat_lit 7)) (Nat.shiftRight v362 (nat_lit 18))) (Nat.shiftRight v347 (nat_lit 3)))) v339) (nat_lit 0xffffffff));
  share v468 := (Nat.mul v465 (nat_lit 0x100000001));
  share v469 := (Nat.add (Nat.add (Nat.add (Nat.add v441 (Nat.xor (Nat.xor (Nat.shiftRight v468 (nat_lit 6)) (Nat.shiftRight v468 (nat_lit 11))) (Nat.shiftRight v468 (nat_lit 25)))) (Nat.xor v449 (Nat.land v465 (Nat.xor v457 v449)))) (nat_lit 2428436474)) v467);
  share v470 := (Nat.xor v464 v456);
  share v471 := (Nat.mul v464 (nat_lit 0x100000001));
  share v472 := (Nat.land (Nat.add (Nat.add v469 (Nat.xor (Nat.xor (Nat.shiftRight v471 (nat_lit 2)) (Nat.shiftRight v471 (nat_lit 13))) (Nat.shiftRight v471 (nat_lit 22)))) (Nat.xor v456 (Nat.land v470 v462))) (nat_lit 0xffffffff));
  share v473 := (Nat.land (Nat.add v440 v469) (nat_lit 0xffffffff));
  share v474 := (Nat.mul v459 (nat_lit 0x100000001));
  share v475 := (Nat.land (Nat.add (Nat.add (Nat.add (Nat.xor (Nat.xor (Nat.shiftRight v474 (nat_lit 17)) (Nat.shiftRight v474 (nat_lit 19))) (Nat.shiftRight v459 (nat_lit 10))) v419) (Nat.xor (Nat.xor (Nat.shiftRight v370 (nat_lit 7)) (Nat.shiftRight v370 (nat_lit 18))) (Nat.shiftRight v355 (nat_lit 3)))) v347) (nat_lit 0xffffffff));
  share v476 := (Nat.mul v473 (nat_lit 0x100000001));
  share v477 := (Nat.add (Nat.add (Nat.add (Nat.add v449 (Nat.xor (Nat.xor (Nat.shiftRight v476 (nat_lit 6)) (Nat.shiftRight v476 (nat_lit 11))) (Nat.shiftRight v476 (nat_lit 25)))) (Nat.xor v457 (Nat.land v473 (Nat.xor v465 v457)))) (nat_lit 2756734187)) v475);
  share v478 := (Nat.xor v472 v464);
  share v479 := (Nat.mul v472 (nat_lit 0x100000001));
  share v480 := (Nat.land (Nat.add (Nat.add v477 (Nat.xor (Nat.xor (Nat.shiftRight v479 (nat_lit 2)) (Nat.shiftRight v479 (nat_lit 13))) (Nat.shiftRight v479 (nat_lit 22)))) (Nat.xor v464 (Nat.land v478 v470))) (nat_lit 0xffffffff));
  share v481 := (Nat.land (Nat.add v448 v477) (nat_lit 0xffffffff));
  share v482 := (Nat.mul v467 (nat_lit 0x100000001));
  share v483 := (Nat.land (Nat.add (Nat.add (Nat.add (Nat.xor (Nat.xor (Nat.shiftRight v482 (nat_lit 17)) (Nat.shiftRight v482 (nat_lit 19))) (Nat.shiftRight v467 (nat_lit 10))) v427) (Nat.xor (Nat.xor (Nat.shiftRight v378 (nat_lit 7)) (Nat.shiftRight v378 (nat_lit 18))) (Nat.shiftRight v363 (nat_lit 3)))) v355) (nat_lit 0xffffffff));
  share v484 := (Nat.mul v481 (nat_lit 0x100000001));
  share v485 := (Nat.add (Nat.add (Nat.add (Nat.add v457 (Nat.xor (Nat.xor (Nat.shiftRight v484 (nat_lit 6)) (Nat.shiftRight v484 (nat_lit 11))) (Nat.shiftRight v484 (nat_lit 25)))) (Nat.xor v465 (Nat.land v481 (Nat.xor v473 v465)))) (nat_lit 3204031479)) v483);
  share v486 := (Nat.xor v480 v472);
  share v487 := (Nat.mul v480 (nat_lit 0x100000001));
  share v488 := (Nat.land (Nat.add (Nat.add v485 (Nat.xor (Nat.xor (Nat.shiftRight v487 (nat_lit 2)) (Nat.shiftRight v487 (nat_lit 13))) (Nat.shiftRight v487 (nat_lit 22)))) (Nat.xor v472 (Nat.land v486 v478))) (nat_lit 0xffffffff));
  share v489 := (Nat.land (Nat.add v456 v485) (nat_lit 0xffffffff));
  share v490 := (Nat.mul v475 (nat_lit 0x100000001));
  share v491 := (Nat.land (Nat.add (Nat.add (Nat.add (Nat.xor (Nat.xor (Nat.shiftRight v490 (nat_lit 17)) (Nat.shiftRight v490 (nat_lit 19))) (Nat.shiftRight v475 (nat_lit 10))) v435) (Nat.xor (Nat.xor (Nat.shiftRight v386 (nat_lit 7)) (Nat.shiftRight v386 (nat_lit 18))) (Nat.shiftRight v371 (nat_lit 3)))) v363) (nat_lit 0xffffffff));
  share v492 := (Nat.mul v489 (nat_lit 0x100000001));
  share v493 := (Nat.add (Nat.add (Nat.add (Nat.add v465 (Nat.xor (Nat.xor (Nat.shiftRight v492 (nat_lit 6)) (Nat.shiftRight v492 (nat_lit 11))) (Nat.shiftRight v492 (nat_lit 25)))) (Nat.xor v473 (Nat.land v489 (Nat.xor v481 v473)))) (nat_lit 3329325298)) v491);
  share v494 := (Nat.xor v488 v480);
  share v495 := (Nat.mul v488 (nat_lit 0x100000001));
  share v496 := (Nat.land (Nat.add (Nat.add v493 (Nat.xor (Nat.xor (Nat.shiftRight v495 (nat_lit 2)) (Nat.shiftRight v495 (nat_lit 13))) (Nat.shiftRight v495 (nat_lit 22)))) (Nat.xor v480 (Nat.land v494 v486))) (nat_lit 0xffffffff));
  share v497 := (Nat.land (Nat.add v464 v493) (nat_lit 0xffffffff));
  fin v496 v488 v480 v472 v497 v489 v481 v473


def iterN (t : Nat) : Nat → Nat :=
  Nat.rec (motive := fun _ => Nat → Nat) (fun S => S) (fun _ ih S => ih (stepF S)) t

def impl (n : Nat) : Nat :=
  iterN (sha256Steps n) (encodeDigest (seedDigest (sha256Seed n)))

/-! ## Bit-level lemmas -/

theorem w32_eq : w32 = 2 ^ 32 - 1 := rfl

theorem land_w32 (x : Nat) : x &&& w32 = x % 2 ^ 32 := by
  rw [w32_eq, Nat.and_two_pow_sub_one_eq_mod]

theorem tb_w32 (i : Nat) : w32.testBit i = decide (i < 32) := by
  rw [w32_eq, Nat.testBit_two_pow_sub_one]

theorem tb_big {x i : Nat} (hx : x < 2 ^ 32) (hi : 32 ≤ i) : x.testBit i = false :=
  Nat.testBit_lt_two_pow (Nat.lt_of_lt_of_le hx (Nat.pow_le_pow_right (by omega) hi))

theorem dup_eq (x : Nat) (hx : x < 2 ^ 32) : dup x = x <<< 32 ||| x := by
  unfold dup
  rw [← Nat.shiftLeft_add_eq_or_of_lt hx, Nat.shiftLeft_eq]
  show x * 4294967297 = x * 4294967296 + x
  omega

theorem tb_dupShift (x n i : Nat) (hx : x < 2 ^ 32) (hn : n ≤ 32) :
    (Nat.shiftRight (dup x) n).testBit i
      = (x.testBit (i + n) || (decide (32 - n ≤ i) && x.testBit (i - (32 - n)))) := by
  rw [dup_eq x hx]
  show ((x <<< 32 ||| x) >>> n).testBit i = _
  rw [Nat.testBit_shiftRight, Nat.testBit_or, Nat.testBit_shiftLeft, Bool.or_comm]
  rw [Nat.add_comm n i]
  by_cases h : 32 - n ≤ i
  · rw [decide_eq_true (show 32 ≤ i + n by omega), decide_eq_true h,
      show i + n - 32 = i - (32 - n) by omega]
  · rw [decide_eq_false (show ¬ 32 ≤ i + n by omega), decide_eq_false h]
    simp

theorem tb_rotr (x n i : Nat) (_hn : 0 < n) (_hn' : n < 32) :
    (rotr32 x n).testBit i
      = (decide (i < 32) && (x.testBit (i + n) || (decide (32 - n ≤ i) && x.testBit (i - (32 - n))))) := by
  unfold rotr32
  rw [Nat.testBit_and, tb_w32, Nat.testBit_or, Nat.testBit_shiftRight, Nat.testBit_shiftLeft,
    Bool.and_comm, Nat.add_comm n i]

theorem tb_mod32 (x i : Nat) : (x % 2 ^ 32).testBit i = (decide (i < 32) && x.testBit i) :=
  Nat.testBit_mod_two_pow x 32 i

theorem S1_mod (e : Nat) (he : e < 2 ^ 32) : S1 e % 2 ^ 32 = bigSigma1 e := by
  apply Nat.eq_of_testBit_eq
  intro i
  unfold S1 bigSigma1
  rw [tb_mod32]
  show (decide (i < 32) && (Nat.xor (Nat.xor _ _) _).testBit i) = (rotr32 e 6 ^^^ rotr32 e 11 ^^^ rotr32 e 25).testBit i
  simp only [show ∀ a b : Nat, Nat.xor a b = a ^^^ b from fun _ _ => rfl, Nat.testBit_xor,
    tb_dupShift e _ i he (by omega : (6:Nat) ≤ 32), tb_dupShift e _ i he (by omega : (11:Nat) ≤ 32),
    tb_dupShift e _ i he (by omega : (25:Nat) ≤ 32),
    tb_rotr e 6 i (by omega) (by omega), tb_rotr e 11 i (by omega) (by omega),
    tb_rotr e 25 i (by omega) (by omega)]
  by_cases hi : i < 32
  · simp [hi]
  · simp [hi]

theorem S0_mod (a : Nat) (ha : a < 2 ^ 32) : S0 a % 2 ^ 32 = bigSigma0 a := by
  apply Nat.eq_of_testBit_eq
  intro i
  unfold S0 bigSigma0
  rw [tb_mod32]
  show (decide (i < 32) && (Nat.xor (Nat.xor _ _) _).testBit i) = (rotr32 a 2 ^^^ rotr32 a 13 ^^^ rotr32 a 22).testBit i
  simp only [show ∀ a b : Nat, Nat.xor a b = a ^^^ b from fun _ _ => rfl, Nat.testBit_xor,
    tb_dupShift a _ i ha (by omega : (2:Nat) ≤ 32), tb_dupShift a _ i ha (by omega : (13:Nat) ≤ 32),
    tb_dupShift a _ i ha (by omega : (22:Nat) ≤ 32),
    tb_rotr a 2 i (by omega) (by omega), tb_rotr a 13 i (by omega) (by omega),
    tb_rotr a 22 i (by omega) (by omega)]
  by_cases hi : i < 32
  · simp [hi]
  · simp [hi]

theorem s0_mod (x : Nat) (hx : x < 2 ^ 32) : s0 x % 2 ^ 32 = smallSigma0 x := by
  apply Nat.eq_of_testBit_eq
  intro i
  unfold s0 smallSigma0
  rw [tb_mod32]
  show (decide (i < 32) && (Nat.xor (Nat.xor _ _) _).testBit i) = (rotr32 x 7 ^^^ rotr32 x 18 ^^^ (x >>> 3)).testBit i
  simp only [show ∀ a b : Nat, Nat.xor a b = a ^^^ b from fun _ _ => rfl, Nat.testBit_xor,
    tb_dupShift x _ i hx (by omega : (7:Nat) ≤ 32), tb_dupShift x _ i hx (by omega : (18:Nat) ≤ 32),
    tb_rotr x 7 i (by omega) (by omega), tb_rotr x 18 i (by omega) (by omega)]
  by_cases hi : i < 32
  · simp [hi]
  · have h3 : (x >>> 3).testBit i = false := by
      rw [Nat.testBit_shiftRight]; exact tb_big hx (by omega)
    simp [hi, h3]

theorem s1_mod (x : Nat) (hx : x < 2 ^ 32) : s1 x % 2 ^ 32 = smallSigma1 x := by
  apply Nat.eq_of_testBit_eq
  intro i
  unfold s1 smallSigma1
  rw [tb_mod32]
  show (decide (i < 32) && (Nat.xor (Nat.xor _ _) _).testBit i) = (rotr32 x 17 ^^^ rotr32 x 19 ^^^ (x >>> 10)).testBit i
  simp only [show ∀ a b : Nat, Nat.xor a b = a ^^^ b from fun _ _ => rfl, Nat.testBit_xor,
    tb_dupShift x _ i hx (by omega : (17:Nat) ≤ 32), tb_dupShift x _ i hx (by omega : (19:Nat) ≤ 32),
    tb_rotr x 17 i (by omega) (by omega), tb_rotr x 19 i (by omega) (by omega)]
  by_cases hi : i < 32
  · simp [hi]
  · have h3 : (x >>> 10).testBit i = false := by
      rw [Nat.testBit_shiftRight]; exact tb_big hx (by omega)
    simp [hi, h3]

theorem ch_eq (e f g : Nat) (he : e < 2 ^ 32) (hf : f < 2 ^ 32) (hg : g < 2 ^ 32) :
    Nat.xor g (Nat.land e (Nat.xor f g)) = ch e f g := by
  apply Nat.eq_of_testBit_eq
  intro i
  unfold ch
  show (g ^^^ (e &&& (f ^^^ g))).testBit i = ((e &&& f) ^^^ ((e ^^^ w32) &&& g)).testBit i
  simp only [Nat.testBit_xor, Nat.testBit_and, tb_w32]
  by_cases hi : i < 32
  · simp only [hi, decide_true]
    cases e.testBit i <;> cases f.testBit i <;> cases g.testBit i <;> rfl
  · simp [tb_big (i := i) he (by omega), tb_big (i := i) hf (by omega), tb_big (i := i) hg (by omega)]

theorem maj_eq (a b c : Nat) :
    Nat.xor b (Nat.land (Nat.xor a b) (Nat.xor b c)) = maj a b c := by
  apply Nat.eq_of_testBit_eq
  intro i
  unfold maj
  show (b ^^^ ((a ^^^ b) &&& (b ^^^ c))).testBit i = ((a &&& b) ^^^ (a &&& c) ^^^ (b &&& c)).testBit i
  simp only [Nat.testBit_xor, Nat.testBit_and]
  cases a.testBit i <;> cases b.testBit i <;> cases c.testBit i <;> rfl

theorem lt32_of_land (x : Nat) : x &&& w32 < 2 ^ 32 := by
  rw [land_w32]; exact Nat.mod_lt _ (by decide)

/-! ## One round -/

/-- All eight working variables are 32-bit words. -/
def Valid (s : Digest) : Prop :=
  s.a < 2 ^ 32 ∧ s.b < 2 ^ 32 ∧ s.c < 2 ^ 32 ∧ s.d < 2 ^ 32 ∧
  s.e < 2 ^ 32 ∧ s.f < 2 ^ 32 ∧ s.g < 2 ^ 32 ∧ s.h < 2 ^ 32

theorem add32_eq (x y : Nat) : add32 x y = (x + y) % 2 ^ 32 := land_w32 _

/-- The fast round as a digest update. -/
def fastRound (s : Digest) (k x : Nat) : Digest :=
  ⟨NA (T1 s.h s.e s.f s.g k x) s.a s.b s.c, s.a, s.b, s.c, NE s.d (T1 s.h s.e s.f s.g k x),
    s.e, s.f, s.g⟩

theorem round_eq (s : Digest) (k w : Nat) (hs : Valid s) : round s k w = fastRound s k w := by
  obtain ⟨ha, hb, hc, hd, he, hf, hg, hh⟩ := hs
  unfold round fastRound NA NE T1
  simp only [add32_eq]
  have h1 := S1_mod s.e he
  have h0 := S0_mod s.a ha
  have hch := ch_eq s.e s.f s.g he hf hg
  have hmj := maj_eq s.a s.b s.c
  show _ = Digest.mk (((((s.h + S1 s.e) + Nat.xor s.g (Nat.land s.e (Nat.xor s.f s.g))) + k + w) + S0 s.a
      + Nat.xor s.b (Nat.land (Nat.xor s.a s.b) (Nat.xor s.b s.c))) &&& w32) s.a s.b s.c
      ((s.d + ((((s.h + S1 s.e) + Nat.xor s.g (Nat.land s.e (Nat.xor s.f s.g))) + k) + w)) &&& w32)
      s.e s.f s.g
  rw [land_w32, land_w32, hch, hmj, ← h1, ← h0]
  congr 1 <;> omega

theorem round_valid (s : Digest) (k w : Nat) : Valid s → Valid (round s k w) := by
  intro hs
  obtain ⟨ha, hb, hc, hd, he, hf, hg, hh⟩ := hs
  refine ⟨?_, ha, hb, hc, ?_, he, hf, hg⟩
  · exact lt32_of_land _
  · exact lt32_of_land _

/-! ## The rolling schedule (window lemmas adapted from the organizers' worked example) -/

structure Window where
  x0 : Nat
  x1 : Nat
  x2 : Nat
  x3 : Nat
  x4 : Nat
  x5 : Nat
  x6 : Nat
  x7 : Nat
  x8 : Nat
  x9 : Nat
  x10 : Nat
  x11 : Nat
  x12 : Nat
  x13 : Nat
  x14 : Nat
  x15 : Nat

def Window.toList (w : Window) : List Nat :=
  [w.x0, w.x1, w.x2, w.x3, w.x4, w.x5, w.x6, w.x7,
   w.x8, w.x9, w.x10, w.x11, w.x12, w.x13, w.x14, w.x15]

def Window.nextWord (w : Window) : Nat :=
  add32 (add32 (smallSigma1 w.x14) w.x9) (add32 (smallSigma0 w.x1) w.x0)

def Window.push (w : Window) (x : Nat) : Window :=
  ⟨w.x1, w.x2, w.x3, w.x4, w.x5, w.x6, w.x7, w.x8,
   w.x9, w.x10, w.x11, w.x12, w.x13, w.x14, w.x15, x⟩

def generate : Nat → Window → List Nat
  | 0, _ => []
  | k + 1, w => w.nextWord :: generate k (w.push w.nextWord)

theorem drop_last16 (pre : List Nat) (w : Window) :
    (pre ++ w.toList).drop ((pre ++ w.toList).length - 16) = w.toList := by
  simp [Window.toList]

theorem append_push (pre : List Nat) (w : Window) :
    (pre ++ w.toList) ++ [w.nextWord] = (pre ++ [w.x0]) ++ (w.push w.nextWord).toList := by
  simp [Window.toList, Window.push]

theorem extend_eq : ∀ k pre w, extendW k (pre ++ w.toList) = pre ++ w.toList ++ generate k w
  | 0, pre, w => by simp [extendW, generate]
  | k + 1, pre, w => by
    rw [extendW, drop_last16]
    show extendW k (pre ++ w.toList ++ [w.nextWord]) = _
    rw [append_push, extend_eq k (pre ++ [w.x0]) (w.push w.nextWord)]
    simp [generate, Window.toList, Window.push, List.append_assoc]

/-- Words consumed by the rounds: `x0` of each successive window. -/
def heads : Nat → Window → List Nat
  | 0, _ => []
  | n + 1, w => w.x0 :: heads n (w.push w.nextWord)

def after : Nat → Window → Window
  | 0, w => w
  | n + 1, w => after n (w.push w.nextWord)

theorem heads_length : ∀ n w, (heads n w).length = n
  | 0, _ => rfl
  | n + 1, w => by simp [heads, heads_length n]

theorem gen_split : ∀ n w, w.toList ++ generate n w = heads n w ++ (after n w).toList
  | 0, w => by simp [generate, heads, after]
  | n + 1, w => by
    rw [heads, after, List.cons_append, ← gen_split n (w.push w.nextWord)]
    simp [generate, Window.toList, Window.push]

/-! ## The loops -/

def WValid (w : Window) : Prop :=
  w.x0 < 2 ^ 32 ∧ w.x1 < 2 ^ 32 ∧ w.x2 < 2 ^ 32 ∧ w.x3 < 2 ^ 32 ∧ w.x4 < 2 ^ 32 ∧
  w.x5 < 2 ^ 32 ∧ w.x6 < 2 ^ 32 ∧ w.x7 < 2 ^ 32 ∧ w.x8 < 2 ^ 32 ∧ w.x9 < 2 ^ 32 ∧
  w.x10 < 2 ^ 32 ∧ w.x11 < 2 ^ 32 ∧ w.x12 < 2 ^ 32 ∧ w.x13 < 2 ^ 32 ∧ w.x14 < 2 ^ 32 ∧
  w.x15 < 2 ^ 32

theorem NW_eq (w : Window) (hw : WValid w) : NW w.x14 w.x9 w.x1 w.x0 = w.nextWord := by
  obtain ⟨h0, h1, _, _, _, _, _, _, _, _, _, _, _, _, h14, _⟩ := hw
  unfold NW Window.nextWord
  simp only [add32_eq]
  rw [← s1_mod _ h14, ← s0_mod _ h1]
  show (((s1 w.x14 + w.x9) + s0 w.x1) + w.x0) &&& w32 = _
  rw [land_w32]
  omega

theorem push_valid (w : Window) (x : Nat) (hw : WValid w) (hx : x < 2 ^ 32) :
    WValid (w.push x) := by
  obtain ⟨_, h1, h2, h3, h4, h5, h6, h7, h8, h9, h10, h11, h12, h13, h14, h15⟩ := hw
  exact ⟨h1, h2, h3, h4, h5, h6, h7, h8, h9, h10, h11, h12, h13, h14, h15, hx⟩

theorem next_valid (w : Window) : w.nextWord < 2 ^ 32 := lt32_of_land _

def finD (s : Digest) : Nat := fin s.a s.b s.c s.d s.e s.f s.g s.h

def runB (n : Nat) (kb : List Nat) (w : Window) (s : Digest) : Nat :=
  loopB n kb w.x0 w.x1 w.x2 w.x3 w.x4 w.x5 w.x6 w.x7 w.x8 w.x9 w.x10 w.x11 w.x12 w.x13 w.x14 w.x15
    s.a s.b s.c s.d s.e s.f s.g s.h

def runA (n : Nat) (ka kb : List Nat) (w : Window) (s : Digest) : Nat :=
  loopA n ka kb w.x0 w.x1 w.x2 w.x3 w.x4 w.x5 w.x6 w.x7 w.x8 w.x9 w.x10 w.x11 w.x12 w.x13 w.x14 w.x15
    s.a s.b s.c s.d s.e s.f s.g s.h

theorem loopB_cons (n k : Nat) (kb : List Nat) (x0 x1 x2 x3 x4 x5 x6 x7 x8 x9 x10 x11 x12 x13 x14 x15 a b c d e f g h : Nat) :
    loopB (n + 1) (k :: kb) x0 x1 x2 x3 x4 x5 x6 x7 x8 x9 x10 x11 x12 x13 x14 x15 a b c d e f g h =
    loopB n kb x1 x2 x3 x4 x5 x6 x7 x8 x9 x10 x11 x12 x13 x14 x15 0 (NA (T1 h e f g k x0) a b c) a b c (NE d (T1 h e f g k x0)) e f g := rfl

theorem loopA_cons (n k : Nat) (ka kb : List Nat) (x0 x1 x2 x3 x4 x5 x6 x7 x8 x9 x10 x11 x12 x13 x14 x15 a b c d e f g h : Nat) :
    loopA (n + 1) (k :: ka) kb x0 x1 x2 x3 x4 x5 x6 x7 x8 x9 x10 x11 x12 x13 x14 x15 a b c d e f g h =
    loopA n ka kb x1 x2 x3 x4 x5 x6 x7 x8 x9 x10 x11 x12 x13 x14 x15 (NW x14 x9 x1 x0) (NA (T1 h e f g k x0) a b c) a b c (NE d (T1 h e f g k x0))
      e f g := rfl

theorem runB_cons (n k : Nat) (kb : List Nat) (w : Window) (s : Digest) :
    runB (n + 1) (k :: kb) w s = runB n kb (w.push 0) (fastRound s k w.x0) := by
  unfold runB
  rw [loopB_cons]
  rfl

theorem runA_cons (n k : Nat) (ka kb : List Nat) (w : Window) (s : Digest) :
    runA (n + 1) (k :: ka) kb w s = runA n ka kb (w.push (NW w.x14 w.x9 w.x1 w.x0)) (fastRound s k w.x0) := by
  unfold runA
  rw [loopA_cons]
  rfl

theorem runA_nil (kb : List Nat) (w : Window) (s : Digest) : runA 0 [] kb w s = runB 16 kb w s := rfl

theorem rounds_append : ∀ (l1 l2 : List (Nat × Nat)) s, rounds (l1 ++ l2) s = rounds l2 (rounds l1 s)
  | [], _, _ => rfl
  | (k, w) :: l1, l2, s => by
    show rounds (l1 ++ l2) (round s k w) = _
    rw [rounds_append l1 l2]; rfl

theorem rounds_valid : ∀ (l : List (Nat × Nat)) s, Valid s → Valid (rounds l s)
  | [], _, h => h
  | (k, w) :: l, s, h => rounds_valid l (round s k w) (round_valid s k w h)

theorem zip_append_left_le : ∀ (a : List Nat) (l r : List Nat), a.length ≤ l.length →
    a.zip (l ++ r) = a.zip l
  | [], _, _, _ => by simp
  | _ :: _, [], _, h => by simp at h
  | x :: a, y :: l, r, h => by
    simp only [List.cons_append, List.zip_cons_cons]
    rw [zip_append_left_le a l r (by simp at h; omega)]

theorem loopB_eq : ∀ (kb : List Nat) (w : Window) (s : Digest), kb.length ≤ 16 → Valid s →
    runB kb.length kb w s = finD (rounds (kb.zip w.toList) s)
  | [], w, s, _, _ => rfl
  | k :: kb, w, s, hl, hs => by
    rw [List.length_cons, runB_cons, ← round_eq s k w.x0 hs]
    rw [loopB_eq kb (w.push 0) (round s k w.x0) (by simp at hl; omega) (round_valid s k w.x0 hs)]
    have hz : kb.zip (w.push 0).toList = kb.zip [w.x1, w.x2, w.x3, w.x4, w.x5, w.x6, w.x7, w.x8,
        w.x9, w.x10, w.x11, w.x12, w.x13, w.x14, w.x15] := by
      have : (w.push 0).toList = [w.x1, w.x2, w.x3, w.x4, w.x5, w.x6, w.x7, w.x8,
        w.x9, w.x10, w.x11, w.x12, w.x13, w.x14, w.x15] ++ [0] := rfl
      rw [this, zip_append_left_le _ _ _ (by simp at hl ⊢; omega)]
    rw [hz]
    rfl

theorem loopA_eq : ∀ (ka kb : List Nat) (w : Window) (s : Digest), WValid w → Valid s →
    runA ka.length ka kb w s = runB 16 kb (after ka.length w) (rounds (ka.zip (heads ka.length w)) s)
  | [], kb, w, s, _, _ => rfl
  | k :: ka, kb, w, s, hw, hs => by
    rw [List.length_cons, runA_cons, NW_eq w hw, ← round_eq s k w.x0 hs]
    rw [loopA_eq ka kb (w.push w.nextWord) (round s k w.x0)
      (push_valid w w.nextWord hw (next_valid w)) (round_valid s k w.x0 hs)]
    rfl

/-! ## One chain step -/

def DValid (d : Digest) : Prop := Valid d

theorem encode_eq (d : Digest) :
    encodeDigest d = d.a * 2 ^ 224 + d.b * 2 ^ 192 + d.c * 2 ^ 160 + d.d * 2 ^ 128 +
      d.e * 2 ^ 96 + d.f * 2 ^ 64 + d.g * 2 ^ 32 + d.h := by
  unfold encodeDigest
  simp only [List.foldl]
  omega

theorem unpack (d : Digest) (hd : Valid d) :
    Nat.land (Nat.shiftRight (encodeDigest d) 224) w32 = d.a ∧
    Nat.land (Nat.shiftRight (encodeDigest d) 192) w32 = d.b ∧
    Nat.land (Nat.shiftRight (encodeDigest d) 160) w32 = d.c ∧
    Nat.land (Nat.shiftRight (encodeDigest d) 128) w32 = d.d ∧
    Nat.land (Nat.shiftRight (encodeDigest d) 96) w32 = d.e ∧
    Nat.land (Nat.shiftRight (encodeDigest d) 64) w32 = d.f ∧
    Nat.land (Nat.shiftRight (encodeDigest d) 32) w32 = d.g ∧
    Nat.land (encodeDigest d) w32 = d.h := by
  obtain ⟨ha, hb, hc, hd', he, hf, hg, hh⟩ := hd
  have L : ∀ x, Nat.land x w32 = x % 2 ^ 32 := fun x => land_w32 x
  have R : ∀ x n, Nat.shiftRight x n = x / 2 ^ n := fun x n => Nat.shiftRight_eq_div_pow x n
  simp only [L, R, encode_eq]
  refine ⟨?_, ?_, ?_, ?_, ?_, ?_, ?_, ?_⟩ <;> omega

theorem fin_eq (s : Digest) :
    finD s = encodeDigest ⟨add32 iv.a s.a, add32 iv.b s.b, add32 iv.c s.c, add32 iv.d s.d,
      add32 iv.e s.e, add32 iv.f s.f, add32 iv.g s.g, add32 iv.h s.h⟩ := rfl

theorem KA_KB : K = KA ++ KB := by simp [KA, KB]

theorem stepN_eq (d : Digest) (hd : Valid d) : stepN (encodeDigest d) = encodeDigest (sha256step d) := by
  obtain ⟨ua, ub, uc, ud, ue, uf, ug, uh⟩ := unpack d hd
  have hw0 : WValid ⟨d.a, d.b, d.c, d.d, d.e, d.f, d.g, d.h, 0x80000000, 0, 0, 0, 0, 0, 0, 256⟩ := by
    obtain ⟨ha, hb, hc, hd', he, hf, hg, hh⟩ := hd
    exact ⟨ha, hb, hc, hd', he, hf, hg, hh, (by decide : (0x80000000 : Nat) < 2 ^ 32),
      (by decide : (0 : Nat) < 2 ^ 32), (by decide : (0 : Nat) < 2 ^ 32),
      (by decide : (0 : Nat) < 2 ^ 32), (by decide : (0 : Nat) < 2 ^ 32),
      (by decide : (0 : Nat) < 2 ^ 32), (by decide : (0 : Nat) < 2 ^ 32),
      (by decide : (256 : Nat) < 2 ^ 32)⟩
  have hiv : Valid iv := ⟨by decide, by decide, by decide, by decide, by decide, by decide,
    by decide, by decide⟩
  have e1 : stepN (encodeDigest d) =
      runA 48 KA KB ⟨d.a, d.b, d.c, d.d, d.e, d.f, d.g, d.h, 0x80000000, 0, 0, 0, 0, 0, 0, 256⟩ iv := by
    unfold stepN runA
    rw [ua, ub, uc, ud, ue, uf, ug, uh]
    rfl
  have hlA : KA.length = 48 := rfl
  have hlB : KB.length = 16 := rfl
  rw [e1, ← hlA, loopA_eq KA KB _ iv hw0 hiv, ← hlB, loopB_eq KB _ _ (Nat.le_of_eq hlB) (rounds_valid _ _ hiv),
    ← rounds_append, fin_eq]
  unfold sha256step compress
  have hs := extend_eq 48 [] ⟨d.a, d.b, d.c, d.d, d.e, d.f, d.g, d.h, 0x80000000, 0, 0, 0, 0, 0, 0, 256⟩
  simp only [List.nil_append] at hs
  have hsched : extendW 48 [d.a, d.b, d.c, d.d, d.e, d.f, d.g, d.h, 0x80000000, 0, 0, 0, 0, 0, 0, 256]
      = heads 48 ⟨d.a, d.b, d.c, d.d, d.e, d.f, d.g, d.h, 0x80000000, 0, 0, 0, 0, 0, 0, 256⟩ ++
        (after 48 ⟨d.a, d.b, d.c, d.d, d.e, d.f, d.g, d.h, 0x80000000, 0, 0, 0, 0, 0, 0, 256⟩).toList := by
    rw [← gen_split]; exact hs
  have hlen : KA.length = 48 := rfl
  rw [hsched, KA_KB, List.zip_append (by rw [hlen]; simp [heads_length]), hlen]

theorem add32_lt (x y : Nat) : add32 x y < 2 ^ 32 := lt32_of_land _

theorem step_valid (d : Digest) : Valid (sha256step d) := by
  unfold sha256step compress
  exact ⟨add32_lt _ _, add32_lt _ _, add32_lt _ _, add32_lt _ _, add32_lt _ _,
    add32_lt _ _, add32_lt _ _, add32_lt _ _⟩

theorem stepF_eq (S : Nat) : stepF S = stepN S := by
  unfold stepN
  rfl

theorem iterN_zero (S : Nat) : iterN 0 S = S := by
  unfold iterN
  rfl
theorem iterN_succ (t S : Nat) : iterN (t + 1) S = iterN t (stepN S) := by
  rw [← stepF_eq]
  unfold iterN
  rfl
theorem iterDigest_zero (step : Digest → Digest) (d : Digest) : iterDigest step 0 d = d := rfl
theorem iterDigest_succ (step : Digest → Digest) (t : Nat) (d : Digest) :
    iterDigest step (t + 1) d = iterDigest step t (step d) := rfl

theorem iterN_eq : ∀ t (d : Digest), Valid d → iterN t (encodeDigest d) = encodeDigest (iterSha t d)
  | 0, d, _ => by rw [iterN_zero]; unfold iterSha; rw [iterDigest_zero]
  | t + 1, d, hd => by
    rw [iterN_succ, stepN_eq d hd, iterN_eq t (sha256step d) (step_valid d)]
    unfold iterSha
    rw [iterDigest_succ]

theorem seed_valid (seed : Nat) : Valid (seedDigest seed) := by
  unfold seedDigest seedStep32
  exact ⟨lt32_of_land _, lt32_of_land _, lt32_of_land _, lt32_of_land _, lt32_of_land _,
    lt32_of_land _, lt32_of_land _, lt32_of_land _⟩

theorem impl_correct : ∀ n, impl n = sha256Spec n := by
  intro n
  unfold impl sha256Spec
  exact iterN_eq _ _ (seed_valid _)

end Submission
