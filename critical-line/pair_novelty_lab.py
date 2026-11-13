"""Part XXXVIII lab — repetition takes one pixel; the unknown needs two; improvement is
the solved pixel plus new ones in the same cycle.

Jonathan's three claims:
 (1) "repeating things is like taking one pixel again" -> powers of ONE gear stay on the
     SAME wire (identical feet for every n) and their resistance is PREDETERMINED:
     tr(g^n) obeys t_{n+1} = t1*t_n - t_{n-1} — one number generates the whole future.
     Repetition creates nothing new; it travels the known wire further.
 (2) "for unknown things we would always use 2 or more pixels" -> the pair carries a THIRD
     coordinate that neither pixel has: knowledge of two gears = (tr A, tr B, tr AB), and
     tr(AB) is NOT a function of tr A and tr B — exhibit pairs with identical (trA, trB)
     and different tr(AB). The pair also obeys the Fricke identity
     tr(AB) + tr(AB^-1) = trA*trB (integer-exact) — the two ways of crossing are linked.
 (3) "getting better = the solved pixel plus new ones in the same cycle" -> extend the
     solved word W with new letters d: every W.d is a genuinely NEW wire (new trace), but
     its feet cluster inside the solved pixel, exponentially tighter as mastery deepens:
     dist(foot(W.d), foot(W)) ~ e^(-ell(W)).
"""
import numpy as np, json

Rm = np.array([[1,1],[0,1]], dtype=object)
Lm = np.array([[1,0],[1,1]], dtype=object)
def mat(word):
    M = np.eye(2, dtype=object)
    for ch in word: M = M @ (Rm if ch == 'R' else Lm)
    return M
def tr(M): return int(M[0,0] + M[1,1])
def inv2(M):
    a,b,c,d = (int(x) for x in M.flatten())
    return np.array([[d,-b],[-c,a]], dtype=object)
def feet(M):
    a,b,c,d = (float(x) for x in M.flatten())
    if c == 0: return None
    s = np.sqrt((a+d)**2 - 4)
    x1, x2 = ((a-d)+s)/(2*c), ((a-d)-s)/(2*c)
    return (x1, x2) if abs(1/(c*x1+d)**2) < 1 else (x2, x1)   # (attracting, repelling)

# ---- (1) repetition: one pixel, same wire, predetermined ----
print("(1) repetition = the same wire, forever:")
ok_feet, ok_cheb = True, True
for w in ["RL", "RRL", "RLLRL"]:
    M = mat(w); t1 = tr(M)
    f1 = feet(M)
    P = M.copy(); traces = [2, t1]
    for n in range(2, 7):
        P = P @ M
        fn = feet(P)
        ok_feet &= (abs(fn[0]-f1[0]) < 1e-9 and abs(fn[1]-f1[1]) < 1e-9)
        traces.append(tr(P))
    ok_cheb &= all(traces[n+1] == t1*traces[n] - traces[n-1] for n in range(1, 6))
    print(f"    {w}: feet of g^n identical for n=1..6: {ok_feet}   traces {traces[1:5]}... obey t_(n+1)=t1*t_n-t_(n-1): {ok_cheb}")
print("    -> one number (the trace) generates every repetition. Nothing new is created.")

# ---- (2) the unknown needs the pair: the third coordinate ----
print("\n(2) the pair's third coordinate:")
A = mat("RL")
B1, B2 = mat("RRL"), mat("LRR")     # cyclic rotations: SAME trace, different position
print(f"    A=RL (tr {tr(A)});  B=RRL (tr {tr(B1)});  B'=LRR (tr {tr(B2)})  — identical (trA,trB)")
print(f"    tr(AB)  = {tr(A@B1)}    tr(AB') = {tr(A@B2)}   -> DIFFERENT: tr(AB) is a free third coordinate")
ok_fricke = True
words = ["RL", "RRL", "LRR", "RLL", "RRLL", "RLRLL"]
for wa in words[:3]:
    for wb in words:
        Ma, Mb = mat(wa), mat(wb)
        lhs = tr(Ma@Mb) + tr(Ma@inv2(Mb))
        ok_fricke &= (lhs == tr(Ma)*tr(Mb))
print(f"    Fricke identity tr(AB)+tr(AB^-1) = trA*trB: exact on all pairs tested: {ok_fricke}")
print("    -> knowing two pixels separately = 2 numbers; knowing them AS A PAIR = 3.")
print("       The third exists only in the pair — the unknown is charted by crossings.")

# ---- (3) improvement: solved prefix + new letters, clustered in the solved pixel ----
print("\n(3) improvement = solved pixel + new configurations in its cycle:")
deltas = ["R", "L", "RRL", "LLR", "RLL", "LRRL"]
gold_foot = (1+np.sqrt(5))/2
rows = []
for k in range(1, 7):
    W = mat("RL"*k)
    dists, trs = [], []
    for d in deltas:
        Md = W @ mat(d)
        ft = feet(Md)
        dists.append(abs(ft[0] - gold_foot))
        trs.append(tr(Md))
    rows.append(dict(k=k, med=float(np.median(dists)), traces=sorted(set(trs))))
    print(f"    solved (RL)^{k}: new wires' feet within {np.median(dists):.2e} of the mastered foot"
          f"   (all new traces: {len(set(trs))}/6 distinct)")
ratio = np.median([rows[i+1]["med"]/rows[i]["med"] for i in range(len(rows)-1)])
lam2 = ((3+np.sqrt(5))/2)**-2
print(f"    clustering rate per RL of mastery: x{ratio:.4f}   (theory e^-l_gold = {lam2:.4f})")
print("    -> every extension is a NEW wire (new trace), but they all live inside the")
print("       solved pixel, e^-l tighter per unit of mastery: better = old pixel + new, in cycle.")

json.dump(dict(feet_ok=bool(ok_feet), cheb_ok=bool(ok_cheb), fricke_ok=bool(ok_fricke),
               cluster=[{k: v for k, v in r.items() if k != "traces"} for r in rows],
               ratio=float(ratio), theory=float(lam2)),
          open("/home/claude/rh_voidline/pair_novelty_res.json","w"))
print("\nsaved pair_novelty_res.json")
