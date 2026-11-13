"""Rebuild the folding void-line pipeline: Fiedler bisection, seam, C pixels, crossings.
Methods per FOLDING_CONTINUITY.md / FOLDING_C_PIXELS.md:
- faces by Fiedler bisection of the Calpha contact graph (8 A)
- C pixels: cross-face heavy-atom contact < 4.5 A
- crossings: backbone projected on cut normal, signed, 2 A hysteresis
Outputs per-protein: Laplacian eigenvalues, crossing positions, C-pixel positions,
seam-corridor residues, saved to pipeline_out.npz
"""
import numpy as np, json, sys
from scipy.spatial import cKDTree
from scipy.linalg import eigh

PDBS = ["1cll","3pgk","1php","1gd1","6ldh","8tln","4ake","2lzm"]

def parse_pdb(path):
    """First protein chain, first model: per-residue CA coord + heavy atoms."""
    chain_pick = None
    residues = {}   # (resseq, icode) -> {'ca':xyz, 'heavy':[xyz]}
    order = []
    with open(path) as f:
        for line in f:
            if line.startswith("ENDMDL"): break
            if not line.startswith("ATOM"): continue
            altloc = line[16]
            if altloc not in (" ","A"): continue
            ch = line[21]
            if chain_pick is None: chain_pick = ch
            if ch != chain_pick: continue
            name = line[12:16].strip()
            elem = line[76:78].strip() or name[0]
            if elem == "H": continue
            key = (int(line[22:26]), line[26])
            xyz = np.array([float(line[30:38]), float(line[38:46]), float(line[46:54])])
            if key not in residues:
                residues[key] = {"ca": None, "heavy": []}
                order.append(key)
            residues[key]["heavy"].append(xyz)
            if name == "CA": residues[key]["ca"] = xyz
    keys = [k for k in order if residues[k]["ca"] is not None]
    ca = np.array([residues[k]["ca"] for k in keys])
    heavy = [np.array(residues[k]["heavy"]) for k in keys]
    return ca, heavy, chain_pick

def fiedler_faces(ca, cutoff=8.0):
    n = len(ca)
    tree = cKDTree(ca)
    pairs = tree.query_pairs(cutoff)
    A = np.zeros((n,n))
    for i,j in pairs:
        A[i,j] = A[j,i] = 1.0
    D = np.diag(A.sum(1))
    L = D - A
    w, v = eigh(L)
    fied = v[:,1]
    return w, fied, A

def cross_face_C(heavy, faces, cutoff=4.5):
    """C pixels: residues with cross-face heavy-atom contact < cutoff."""
    n = len(heavy)
    allpts, owner = [], []
    for i,h in enumerate(heavy):
        allpts.append(h); owner.extend([i]*len(h))
    allpts = np.vstack(allpts); owner = np.array(owner)
    tree = cKDTree(allpts)
    pairs = tree.query_pairs(cutoff)
    C = set()
    for a,b in pairs:
        i,j = owner[a], owner[b]
        if i!=j and faces[i]!=faces[j]:
            C.add(i); C.add(j)
    return sorted(C)

def crossings(ca, faces, hyst=2.0):
    """Signed crossings of the seam along the chain, 2 A hysteresis.
    Returns list of (chain_index, midpoint_xyz, direction)."""
    cA = ca[faces].mean(0); cB = ca[~faces].mean(0)
    nvec = cA - cB; nvec /= np.linalg.norm(nvec)
    mid = 0.5*(cA+cB)
    s = (ca - mid) @ nvec
    events = []
    state = 1 if s[0] > 0 else -1
    for i in range(1, len(s)):
        if state == 1 and s[i] < -hyst:
            events.append((i, 0.5*(ca[i-1]+ca[i]), -1)); state = -1
        elif state == -1 and s[i] > hyst:
            events.append((i, 0.5*(ca[i-1]+ca[i]), +1)); state = +1
    return events, nvec, mid, s

results = {}
np_store = {}
for pid in PDBS:
    ca, heavy, ch = parse_pdb(f"/home/claude/rh_voidline/pdb/{pid}.pdb")
    w, fied, A = fiedler_faces(ca)
    faces = fied > 0
    Cidx = cross_face_C(heavy, faces)
    ev, nvec, mid, s = crossings(ca, faces)
    up = sum(1 for e in ev if e[2]>0); dn = sum(1 for e in ev if e[2]<0)
    # seam axis: PCA of C-pixel coords in plane perp to nvec
    if len(Cidx) >= 3:
        P = ca[Cidx] - mid
        P = P - np.outer(P@nvec, nvec)          # project out normal
        u,sv,vt = np.linalg.svd(P - P.mean(0), full_matrices=False)
        axis = vt[0]
    else:
        axis = np.zeros(3)
    results[pid] = dict(chain=ch, n=len(ca), nC=len(Cidx),
                        crossings=len(ev), up=up, down=dn, net=up-dn,
                        n_eigs=len(w))
    np_store[f"{pid}_eigs"] = w
    np_store[f"{pid}_ca"] = ca
    np_store[f"{pid}_faces"] = faces
    np_store[f"{pid}_C"] = np.array(Cidx)
    np_store[f"{pid}_s"] = s
    np_store[f"{pid}_nvec"] = nvec
    np_store[f"{pid}_mid"] = mid
    np_store[f"{pid}_axis"] = axis
    np_store[f"{pid}_crossxyz"] = np.array([e[1] for e in ev]) if ev else np.zeros((0,3))
    print(pid, results[pid])

np.savez("/home/claude/rh_voidline/pipeline_out.npz", **np_store)
json.dump(results, open("/home/claude/rh_voidline/pipeline_summary.json","w"), indent=1)
print("saved")
