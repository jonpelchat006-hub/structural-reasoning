"""Linking ledger lab.
Ghys: each modular gear-orbit (hyperbolic conjugacy class of PSL(2,Z), i.e. an RL-word)
is a knot in S^3 minus the trefoil, and its LINKING NUMBER with the trefoil equals the
Rademacher function Psi(gamma). Three independent computations per orbit:
  (1) word count:      Psi = #R - #L
  (2) Rademacher/Dedekind-sum formula: Phi(gamma) = (a+d)/c - 12 sign(c) s(d,|c|) - 3 sign(c(a+d))
  (3) the eta phase:   from log eta(gamma tau) = log eta(tau) + (1/2) log((c tau+d)/i) + i pi Phi/12
If all three agree, the closure-phase ledger IS the linking ledger, orbit by orbit.
"""
import numpy as np, json
from fractions import Fraction
import mpmath as mp
mp.mp.dps = 30

R = np.array([[1,1],[0,1]], dtype=object)
L = np.array([[1,0],[1,1]], dtype=object)

def dedekind_s(d, c):
    # s(d,c) = sum_{k=1}^{c-1} ((k/c))((dk/c)),  ((x)) = x-floor(x)-1/2 (0 if integer)
    def saw(x):
        return 0 if x == int(x) else x - int(np.floor(x)) - 0.5
    return sum(saw(k/c)*saw(d*k/c) for k in range(1, c))

def rademacher(M):
    a,b,c,d = int(M[0,0]), int(M[0,1]), int(M[1,0]), int(M[1,1])
    assert c != 0
    return (a+d)/c - 12*np.sign(c)*dedekind_s(d, abs(c)) - 3*np.sign(c*(a+d))

def log_eta(tau, terms=400):
    q = mp.e**(2j*mp.pi*tau)
    s = 2j*mp.pi*tau/24
    for n in range(1, terms):
        s += mp.log(1 - q**n)
    return s

def eta_phase(M, tau=mp.mpc(0.13, 0.81)):
    a,b,c,d = int(M[0,0]), int(M[0,1]), int(M[1,0]), int(M[1,1])
    if c < 0: a,b,c,d = -a,-b,-c,-d
    gt = (a*tau + b)/(c*tau + d)
    lhs = log_eta(gt) - log_eta(tau) - mp.mpf(0.5)*mp.log((c*tau + d)/1j)
    return float(mp.re(lhs*12/(1j*mp.pi)))   # = Phi, up to branch (should land on integer)

def cyclic_reps(maxlen):
    """primitive words in R,L (both letters present), one representative per cyclic class"""
    seen, out = set(), []
    for n in range(2, maxlen+1):
        for bits in range(1, 2**n - 1):
            w = ['R' if (bits>>i)&1 else 'L' for i in range(n)]
            # primitive check
            s = ''.join(w)
            if any(s == s[:p]*(n//p) for p in range(1, n) if n % p == 0): continue
            canon = min(s[i:]+s[:i] for i in range(n))
            if canon in seen: continue
            seen.add(canon); out.append(canon)
    return out

rows = []
for word in cyclic_reps(6):
    M = np.array([[1,0],[0,1]], dtype=object)
    for ch in word:
        M = M @ (R if ch=='R' else L)
    tr = int(M[0,0] + M[1,1])
    if tr <= 2: continue
    psi_word = word.count('R') - word.count('L')
    phi_ded = rademacher(M)
    phi_eta = eta_phase(M)
    length = 2*np.log((tr + np.sqrt(tr*tr - 4))/2)
    rows.append(dict(word=word, trace=tr, disc=tr*tr-4,
                     length=round(float(length),4),
                     link_word=psi_word,
                     link_dedekind=round(float(phi_ded),6),
                     link_eta=round(phi_eta,6)))

agree = all(abs(r["link_word"]-r["link_dedekind"])<1e-9 and
            abs(r["link_word"]-round(r["link_eta"]))<1e-6 and
            abs(r["link_eta"]-round(r["link_eta"]))<1e-6 for r in rows)
print("orbits:", len(rows), "  all three ledgers agree:", agree)
for r in sorted(rows, key=lambda r: r["length"])[:12]:
    print("%-6s trace=%3d D=%4d len=%7.4f  link: word=%3d dedekind=%9.6f eta=%9.6f"%(
        r["word"], r["trace"], r["disc"], r["length"],
        r["link_word"], r["link_dedekind"], r["link_eta"]))
json.dump(rows, open("/home/claude/rh_voidline/linking_res.json","w"), indent=0)
