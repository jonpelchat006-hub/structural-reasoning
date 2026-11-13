import Lean

namespace V9

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

end V9
