"""Fast GMP price of an op list from the oracle grid (log-log bilinear interpolation)."""
import json, math, bisect
L = [1,2,3,4,6,8,12,16,24,32,48,64,96,128,192,256,384,512,768,1024,1536,2048,3072,4096,6144,8192]
TAB = json.load(open("/home/claude/gmpcost/grid.json"))
LL = [math.log(x) for x in L]
def _interp(tab, a, b, sym):
    if sym and a > b: a, b = b, a
    def idx(x):
        lx = math.log(max(x, 1)); i = min(max(bisect.bisect_right(LL, lx) - 1, 0), len(L) - 2)
        return i, (lx - LL[i]) / (LL[i + 1] - LL[i])
    (i, fi), (j, fj) = idx(a), idx(b)
    def g(p, q):
        x, y = L[p], L[q]
        if sym and x > y: x, y = y, x
        return math.log(tab[f"{x},{y}"])
    v = (g(i, j) * (1 - fi) * (1 - fj) + g(i + 1, j) * fi * (1 - fj) + g(i, j + 1) * (1 - fi) * fj + g(i + 1, j + 1) * fi * fj)
    return math.exp(v)
def limbs(bits): return max((bits + 63) // 64, 1)
def price(ops):
    tot = 0
    for o, a, b in ops:
        la, lb = limbs(a), limbs(b)
        if o == "mul":
            tot += _interp(TAB["mul"], la, lb, True) if la > 1 or lb > 1 else 0
        elif o in ("div", "mod"):
            tot += _interp(TAB["div"], la, lb, False) if la + lb > 2 else 0
        elif o in ("shl", "shr"):
            tot += 2 * max(la, 1) + 40 if la > 1 else 0
        else:
            m = max(la, lb)
            tot += 3.6 * m + 120 if m > 1 else 0
    return int(tot)
