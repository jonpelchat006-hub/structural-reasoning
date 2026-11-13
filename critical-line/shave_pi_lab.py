"""Part XXXIV lab — the .14 of pi IS the shave, and the shave machine is the Gauss map.

Jonathan: "would the .14 part of pi be the shave? it was for the void mostly, which would be
related to the eye shell it came off." Claims tested:
 (1) taking the fractional part IS the shave, and iterating it (shave -> invert -> shave) is
     the continued fraction — the SAME addressing that routes the wall. pi's shave ledger:
     [3; 7, 15, 1, 292, ...].
 (2) near-closure: when a shave leaves almost nothing (the 292), the convergent nearly closes
     the shell — 355/113 is a .9999997-closure. The golden ratio is the OPPOSITE: all-1
     ledger, never closes, maximal retained void (Hurwitz worst-approximable, |x-p/q|q^2 -> 1/sqrt5).
 (3) the shave rate is built from pi^2 and Landauer's ln 2 TOGETHER: Levy's constant —
     denominators grow as q_n^(1/n) -> e^(pi^2 / (12 ln 2)). The heat constant of the burn
     (Part XXII primon gas) sits inside the speed of the shave.
 (4) the shave digits have an invariant law (Gauss-Kuzmin): P(digit = k) = log2(1 + 1/(k(k+2))).
"""
import numpy as np
import mpmath as mp
mp.mp.dps = 60

def cf_digits(x, n):
    out = []
    for _ in range(n):
        a = int(mp.floor(x)); out.append(a)
        x = x - a                      # THE SHAVE: take the whole gears off
        if x == 0: break
        x = 1/x                        # look inside what remains
    return out

def convergents(digs):
    p0, q0, p1, q1 = 1, 0, digs[0], 1
    out = [(p1, q1)]
    for a in digs[1:]:
        p0, q0, p1, q1 = p1, q1, a*p1 + p0, a*q1 + q0
        out.append((p1, q1))
    return out

# (1)+(2) pi's ledger and closures
pi = mp.pi
digs = cf_digits(pi, 10)
print("(1) pi's shave ledger:", digs)
print("    first shave leaves", mp.nstr(pi - 3, 8), "= 1/", mp.nstr(1/(pi-3), 8), "-> digit 7 (the 22/7 shell)")
print("\n(2) closure per convergent (how much of the shell the shave nearly closes):")
for (p, q) in convergents(digs)[:6]:
    err = abs(pi - mp.mpf(p)/q)
    closure = 1 - err*q*q              # 1 - |x - p/q| q^2 : 1 = perfect tangency
    print(f"    {p}/{q}:  |pi - p/q| q^2 = {mp.nstr(err*q*q, 6)}   closure = {mp.nstr(closure, 8)}")
phi = (1 + mp.sqrt(5))/2
print("    golden ledger:", cf_digits(phi, 10), " (all 1s — the minimal shave, forever)")
errs = [float(abs(phi - mp.mpf(p)/q)*q*q) for (p, q) in convergents(cf_digits(phi, 40))[10:]]
print(f"    golden |x-p/q| q^2 -> {np.mean(errs):.6f}   (Hurwitz bound 1/sqrt5 = {float(1/mp.sqrt(5)):.6f} — the most void any number can keep)")

# (3) Levy's constant measured: the shave speed contains pi^2 and ln 2
levy = float(mp.e**(mp.pi**2/(12*mp.log(2))))
rng = np.random.default_rng(3)
rates = []
for _ in range(200):
    x = mp.rand()                    # full-precision (a float is rational: fake giant last digit)
    digs_r = cf_digits(x, 45)
    cs = convergents(digs_r)
    if len(cs) > 40:
        q40 = cs[40][1]
        rates.append(float(mp.mpf(q40)**(mp.mpf(1)/40)))
print(f"\n(3) measured shave speed q_n^(1/n): {np.mean(rates):.4f} +- {np.std(rates)/np.sqrt(len(rates)):.4f}")
print(f"    Levy's constant e^(pi^2/(12 ln2)) = {levy:.4f}   <- pi^2 AND Landauer's ln2, in one number")

# (4) Gauss-Kuzmin: the invariant law of the shave digits
digs_all = []
for _ in range(400):
    digs_all += cf_digits(mp.rand(), 40)[1:]
digs_all = np.array([d for d in digs_all if d >= 1])
print("\n(4) shave-digit law (measured vs Gauss-Kuzmin log2(1+1/k(k+2))):")
for k in [1, 2, 3, 4, 5]:
    meas = (digs_all == k).mean()
    theo = float(mp.log(1 + 1/mp.mpf(k*(k+2)))/mp.log(2))
    print(f"    digit {k}:  measured {meas:.4f}   law {theo:.4f}")

import json
json.dump(dict(pi_ledger=digs, levy=levy, levy_meas=float(np.mean(rates)),
               hurwitz=float(1/mp.sqrt(5)), golden_meas=float(np.mean(errs))),
          open("/home/claude/rh_voidline/shave_pi_res.json","w"))
print("\nsaved shave_pi_res.json")
