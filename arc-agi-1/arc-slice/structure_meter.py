"""structure_meter — RH-distance as a structure/routing signal for ARC grids.

Born from the FOLDING_CRITICAL_LINE program (Parts V & IX): a graph's distance from
its own Riemann hypothesis (the Ramanujan condition) measures how much findable
structure it carries. Cross-domain law: seam strength vs Ramanujan excess,
Spearman r = 0.53, p ~ 1e-22 over proteins/ARC/random/lattice (Part IX).

Meters exposed:
  cell_plane(grid)   -> Ramanujan excess + seam strength of the same-color cell graph
                        (reads GEOMETRY; blind to color structure - see Part IX control)
  region_plane(grid) -> Ramanujan excess of the region-adjacency graph
                        (reads COLOR STRUCTURE; structured grids sit CLOSER to
                        Ramanujan than their shuffled selves, p = 9e-4)
  compression(grid)  -> shuffled-region-count / real-region-count
                        (routing signal: separates solver-solved from unsolved
                        tasks, Mann-Whitney p = 0.017 on the 400-task set)

Usage:  from structure_meter import meter
        m = meter(task["train"][0]["input"])   # dict of all three
"""
import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import connected_components

def _cell_edges(g):
    g = np.asarray(g); H, W = g.shape
    idx = np.arange(H*W).reshape(H, W)
    ei, ej = [], []
    for (a, b) in [((slice(None,-1),slice(None)),(slice(1,None),slice(None))),
                   ((slice(None),slice(None,-1)),(slice(None),slice(1,None)))]:
        same = g[a] == g[b]
        ei += idx[a][same].tolist(); ej += idx[b][same].tolist()
    return ei, ej, H, W

def _components(g):
    ei, ej, H, W = _cell_edges(g)
    M = csr_matrix((np.ones(len(ei)), (ei, ej)), shape=(H*W, H*W))
    M = M + M.T
    ncc, lab = connected_components(M, directed=False)
    return M, ncc, lab, H, W

def _ramanujan_excess(A):
    d = A.sum(1)
    keep = (d > 0).nonzero()[0]
    A = A[np.ix_(keep, keep)]
    n = len(A)
    if n < 8: return None
    d = A.sum(1); dbar = d.mean()
    if dbar <= 2.05: return None
    aev = np.sort(np.linalg.eigvalsh(A))[::-1]
    lam2 = max(aev[1], abs(aev[-1]))
    return float(lam2 / (2*np.sqrt(dbar - 1)))

def _seam_strength(A):
    """-log of the min Fiedler sweep-cut conductance."""
    d = A.sum(1); n = len(A)
    if n < 30: return None
    L = np.diag(d) - A
    w, v = np.linalg.eigh(L)
    order = np.argsort(v[:, 1])
    Aor = A[np.ix_(order, order)]; dor = d[order]
    vol_tot = d.sum(); cum = 0.0; cut = 0.0; best = 1.0
    for i in range(n - 1):
        cum += dor[i]
        cut += dor[i] - 2*Aor[i, :i+1].sum()
        volmin = min(cum, vol_tot - cum)
        if volmin > 0 and 10 <= i <= n - 10:
            best = min(best, cut / volmin)
    return float(-np.log(max(best, 1e-6)))

def cell_plane(grid):
    M, ncc, lab, H, W = _components(grid)
    big = np.argmax(np.bincount(lab))
    keep = np.where(lab == big)[0]
    if len(keep) < 30: return None
    A = M[np.ix_(keep, keep)].toarray()
    return dict(excess=_ramanujan_excess(A), seam=_seam_strength(A), n=len(keep))

def region_plane(grid):
    M, ncc, lab, H, W = _components(grid)
    la = lab.reshape(H, W)
    E = set()
    for i in range(H):
        for j in range(W):
            for di, dj in [(0, 1), (1, 0)]:
                if i+di < H and j+dj < W and la[i, j] != la[i+di, j+dj]:
                    E.add((min(la[i,j], la[i+di,j+dj]), max(la[i,j], la[i+di,j+dj])))
    A = np.zeros((ncc, ncc))
    for a, b in E: A[a, b] = A[b, a] = 1
    return dict(excess=_ramanujan_excess(A), n_regions=int(ncc))

def compression(grid, n_shuffles=3, seed=0):
    rng = np.random.default_rng(seed)
    g = np.asarray(grid)
    _, ncc, _, _, _ = _components(g)
    shuf = []
    for _ in range(n_shuffles):
        flat = g.flatten().copy(); rng.shuffle(flat)
        _, n2, _, _, _ = _components(flat.reshape(g.shape))
        shuf.append(n2)
    return float(np.mean(shuf) / max(ncc, 1))

def meter(grid):
    return dict(cell=cell_plane(grid), region=region_plane(grid),
                compression=compression(grid))

if __name__ == "__main__":
    demo = [[0,0,0,0],[0,3,3,0],[0,3,3,0],[0,0,0,0]]
    print(meter(demo))
