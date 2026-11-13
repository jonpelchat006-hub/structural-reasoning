# Is our PRS step output exactly +-(the subresultant determinant)?  Small random cases, exact integers.
import random, sys
sys.path.insert(0, "/home/claude/polyvar"); import prs_model as pm
def det(M):                      # Bareiss, exact
    M = [r[:] for r in M]; n = len(M); prev = 1; sign = 1
    for k in range(n - 1):
        if M[k][k] == 0:
            for r in range(k + 1, n):
                if M[r][k] != 0: M[k], M[r] = M[r], M[k]; sign = -sign; break
            else: return 0
        for i in range(k + 1, n):
            for j in range(k + 1, n):
                M[i][j] = (M[i][j]*M[k][k] - M[i][k]*M[k][j]) // prev
        prev = M[k][k]
    return sign * M[n-1][n-1]
def subres(f, g, j):             # f, g high->low coefficient lists; returns S_j coefficients high->low (deg j..0)
    m, n = len(f) - 1, len(g) - 1; W = m + n - j
    rows = []
    for r in range(n - j):
        s = n - j - 1 - r; v = [0]*W
        for k, a in enumerate(f): v[W - 1 - (m - k + s)] = a
        rows.append(v)
    for r in range(m - j):
        s = m - j - 1 - r; v = [0]*W
        for k, b in enumerate(g): v[W - 1 - (n - k + s)] = b
        rows.append(v)
    fixed = list(range(0, W - j - 1))           # degrees W-1 .. j+1
    out = []
    for i in range(j, -1, -1):
        col = W - 1 - i
        out.append(det([[r[c] for c in fixed] + [r[col]] for r in rows]))
    return out
random.seed(3); ok = bad = 0
for trial in range(40):
    d = random.choice([5, 6, 7, 8])
    f = [1] + [random.choice([-1, 1]) * random.randint(1, 2**random.randint(2, 30)) for _ in range(d)]
    g = pm.deriv(f); F, G, first = f, g, True; seq = [f, g]
    try:
        while len(G) > 1:
            H = pm.step(F, G, 1 if first else F[0]*F[0], pm.Log()); first = False; F, G = G, H; seq.append(H)
    except AssertionError: continue
    for H in seq[2:]:
        j = len(H) - 1; S = subres(f, g, j)
        if S == H or S == [-x for x in H]: ok += 1
        else: bad += 1
print(f"PRS polynomials equal to +-subresultant determinants: {ok} matched, {bad} did not")
