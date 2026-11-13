# Tighter provable bound: |det| <= (number of permutations) x (largest single permutation product).
# The largest product is a max-weight assignment on log2 entry bounds (spec width limits only).
import math, numpy as np, sys
from scipy.optimize import linear_sum_assignment
exec(open("bound_price.py").read().split("GM = ")[0])        # width(), fb, gb, bound_bits (column-sum bound)
NEG = -1e9
def assign_bits(j):
    m, n = 24, 23; W = m + n - j; R = m + n - 2*j
    rows = []
    for r in range(n - j):
        s = n - j - 1 - r; v = [NEG]*W
        for k in range(m + 1): v[W - 1 - (m - k + s)] = fb[k]
        rows.append(v)
    for r in range(m - j):
        s = m - j - 1 - r; v = [NEG]*W
        for k in range(n + 1): v[W - 1 - (n - k + s)] = gb[k]
        rows.append(v)
    A = np.array(rows); fixed = list(range(0, W - j - 1)); out = []
    for i in range(j, -1, -1):
        M = A[:, fixed + [W - 1 - i]]
        r, c = linear_sum_assignment(-M)
        best = M[r, c].sum()
        out.append(best + math.lgamma(R + 1) / math.log(2))
    return out
if __name__ == "__main__":
    for j in [22, 18, 14, 10, 6, 2, 0]:
        print(f"S_{j:2d}: column-sum bound {max(bound_bits(j)):9.0f} bits, permutation bound {max(assign_bits(j)):9.0f} bits")
