import Spec

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
  Nat.land (Nat.add (Nat.add t1 (S0 a)) (Nat.lor (Nat.land (Nat.lor a b) c) (Nat.land a b))) w32
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

def iterN (t : Nat) : Nat → Nat :=
  Nat.rec (motive := fun _ => Nat → Nat) (fun S => S) (fun _ ih S => ih (stepN S)) t

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
    Nat.lor (Nat.land (Nat.lor a b) c) (Nat.land a b) = maj a b c := by
  apply Nat.eq_of_testBit_eq
  intro i
  unfold maj
  show (((a ||| b) &&& c) ||| (a &&& b)).testBit i = ((a &&& b) ^^^ (a &&& c) ^^^ (b &&& c)).testBit i
  simp only [Nat.testBit_xor, Nat.testBit_and, Nat.testBit_or]
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
      + Nat.lor (Nat.land (Nat.lor s.a s.b) s.c) (Nat.land s.a s.b)) &&& w32) s.a s.b s.c
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

theorem iterN_zero (S : Nat) : iterN 0 S = S := by
  unfold iterN
  rfl
theorem iterN_succ (t S : Nat) : iterN (t + 1) S = iterN t (stepN S) := by
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
