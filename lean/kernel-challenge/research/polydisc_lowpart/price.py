# Price D5's PRS GMP work two ways with Lean's own GMP:
#  now:  full numerators (3 products) + exact division per coefficient (what v7/v8 do)
#  low:  "keep only the part we need": every product truncated to the result's width q,
#        division replaced by one product with dm's inverse mod 2^q (+ inverse per step).
import sys, random, subprocess
sys.path.insert(0, "/home/claude/polyvar"); sys.set_int_max_str_digits(0)
import prs_model as pm, reference_answers as ref
GM = "/home/claude/gmpcost/gmpcost"
def price(ops, tag):
    p = f"ops_{tag}.txt"; open(p, "w").write("".join(f"{o} {max(a,1)} {max(b,1)}\n" for o, a, b in ops))
    out = f"cg_{tag}.out"
    subprocess.run(f"valgrind --tool=callgrind --collect-atstart=no --callgrind-out-file={out} {GM} < {p}", shell=True, capture_output=True)
    for l in open(out):
        if l.startswith("summary:"): return int(l.split()[1])
bl = lambda x: abs(x).bit_length()
random.seed(11)
for n in [random.randint(2**57, 2**63) for _ in range(2)]:
    P = ref.candidate_polynomial(n)[0]
    F, G = P, pm.deriv(P); first = True
    now, low = [], []
    while len(G) > 1:
        dm = 1 if first else F[0] * F[0]
        lf, lg = F[0], G[0]
        c1 = lg * F[1] - lf * G[1]; mA, mC = lg * lg, lg * lf
        now += [("mul", bl(lg), bl(F[1])), ("mul", bl(lf), bl(G[1])), ("mul", bl(lg), bl(lg)), ("mul", bl(lg), bl(lf))]
        H = []
        for j in range(len(F) - 2):
            x = F[j+2]; z = G[j+1]; y = G[j+2] if j + 2 < len(G) else 0
            e = mA * x - mC * y - c1 * z
            now += [("mul", bl(mA), bl(x)), ("mul", bl(mC), bl(y)), ("mul", bl(c1), bl(z))]
            if dm != 1: now.append(("div", bl(e) - bl(dm) + 1, bl(dm)))
            H.append(e // dm if (e >= 0) == (dm >= 0) else -((-e) // dm))
        q = max(bl(h) for h in H) + 2       # width of what we keep
        low += [("mul", bl(lg), bl(F[1])), ("mul", bl(lf), bl(G[1])), ("mul", bl(lg), bl(lg)), ("mul", bl(lg), bl(lf))]
        if dm != 1: low += [("mul", q, q)] * 3          # Newton inverse of dm mod 2^q, about 3 products
        for j in range(len(F) - 2):
            x = F[j+2]; z = G[j+1]; y = G[j+2] if j + 2 < len(G) else 0
            low += [("mul", min(q, bl(mA)), bl(x)), ("and", q + bl(x), q),
                    ("mul", min(q, bl(mC)), bl(y)), ("and", q + bl(y), q),
                    ("mul", min(q, bl(c1)), bl(z)), ("and", q + bl(z), q)]
            if dm != 1: low += [("mul", q, q), ("and", 2 * q, q)]
        F, G, first = G, H, False
    a, b = price(now, f"now{n%1000}"), price(low, f"low{n%1000}")
    print(f"n={n}: now {a/1e6:.1f}M  low-part {b/1e6:.1f}M  ratio {b/a:.2f}  ops now {len(now)} low {len(low)}")
