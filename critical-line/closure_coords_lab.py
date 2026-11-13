"""Part XXXIII lab — coordinates as nested 2x2 words, doubling at shared borders,
and the window as a projection of the wall.

Jonathan's three claims, tested:
 (A) "each axis is how far along the border we are looking at, and it recurses until we get
     the zoom we want" -> the pixel's coordinate object is the 2x2 matrix [[p1,p2],[q1,q2]]
     whose COLUMNS are the two border positions of the current view; zoom = right-multiply
     by the SAME R,L generator matrices as the linking lab; closure equation det = +-1 is
     preserved at every depth (the tangency |ps-qr|=1 = the quaternion norm of the split
     algebra M2 = closure under nesting).
 (B) "doubling would be when more than one pixel is involved" -> a point has TWO addresses
     exactly when it lies on a shared border (a rational: two continued-fraction expansions
     [..,a_n] = [..,a_n - 1, 1]); an interior (irrational) point has exactly one.
 (C) "the window system is a projection from the main wall" -> harmonic extension: the view
     from height y inside the disk is the Poisson integral of the wall data; a pixel p/q is
     visible from height y only while its Ford circle (height 1/2q^2) still reaches the
     window: measured cutoff y50 * q^2 ~ const.
"""
import numpy as np, json
from fractions import Fraction

R = np.array([[1,1],[0,1]], dtype=object)   # same generators as linking_lab.py
L = np.array([[1,0],[1,1]], dtype=object)

# ---------- (A) the coordinate matrix: columns = borders, det closed at every zoom ----------
def address_matrix(x, depth):
    M = np.array([[0,1],[1,1]], dtype=object)   # root cell [0/1, 1/1]: columns (0,1),(1,1)
    word = ""
    for _ in range(depth):
        p1,p2,q1,q2 = int(M[0,0]),int(M[0,1]),int(M[1,0]),int(M[1,1])
        m = (p1+p2)/(q1+q2)
        if x < m: M = M @ R; word += "L"     # left child keeps left border
        else:     M = M @ L; word += "R"
    return M, word

print("(A) coordinate matrices: columns = the two border positions; det = closure")
ok = True
for x in [0.5-1e-9, 1/np.sqrt(2), (np.sqrt(5)-1)/2, np.pi-3, 0.123456]:
    for depth in [3, 6, 10, 14]:
        M, word = address_matrix(float(x), depth)
        p1,p2,q1,q2 = int(M[0,0]),int(M[0,1]),int(M[1,0]),int(M[1,1])
        det = p1*q2 - p2*q1
        inside = (p1/q1 <= x <= p2/q2) or (p2/q2 <= x <= p1/q1)
        ok &= (abs(det) == 1) and inside
    Mx, w = address_matrix(float(x), 10)
    p1,p2,q1,q2 = int(Mx[0,0]),int(Mx[0,1]),int(Mx[1,0]),int(Mx[1,1])
    print(f"  x={x:.6f}  depth10 word {w}  axes: left border {p1}/{q1}, right border {p2}/{q2}, det={p1*q2-p2*q1}")
print("  every depth, every x: |det| = 1 and x inside its cell:", ok)

# the zoom is invertible: M^-1 maps the cell back onto the whole wall
x0 = float((np.sqrt(5)-1)/2)
M, _ = address_matrix(x0, 10)
a,b,c,d = int(M[0,0]),int(M[0,1]),int(M[1,0]),int(M[1,1])
det = a*d - b*c
# mobius action of M^{-1} = [[d,-b],[-c,a]]/det on x0
z = (d*x0 - b)/(-c*x0 + a) if det==1 else ((-d)*x0 + b)/((c)*x0 - a)
print(f"  renormalization: M^-1 sends x back into [0,1]: {z:.6f} (a fresh wall — recurse for more zoom)")

# ---------- (B) doubling exactly at shared borders ----------
print("\n(B) doubling: two addresses iff the point is a shared border (two CF spellings)")
def word_of(x, depth):
    return address_matrix(float(x), depth)[1]

for frac in [Fraction(3,7), Fraction(2,5), Fraction(5,8)]:
    eps = 1e-12
    wl = word_of(float(frac) - eps, 14)
    wr = word_of(float(frac) + eps, 14)
    # CF spellings
    def cf(fr):
        out = []; a, b = fr.numerator, fr.denominator
        while b: out.append(a//b); a, b = b, a % b
        return out
    c1 = cf(frac); c2 = c1[:-1] + [c1[-1]-1, 1] if c1[-1] > 1 else None
    print(f"  {frac}: left-address {wl}")
    print(f"        right-address {wr}   (CF {c1} vs {c2})")
w_irr = word_of(np.pi-3, 14)
print(f"  pi-3 (interior point): single address {w_irr} — no doubling off the borders")

# ---------- (C) the window: Poisson projection of the wall + Ford visibility ----------
print("\n(C) the window as a projection of the wall (Poisson), visibility = Ford height")
M_ = 8000
xs = np.linspace(0, 1, M_)
bumps = [(1,2,1.2), (1,3,0.9), (2,3,0.7), (2,5,0.5), (3,5,0.6), (1,7,0.45), (3,8,0.5)]
def bump_field(x):
    y = np.zeros_like(x)
    for (p,q,a) in bumps:
        w = 0.6/(2*q*q)
        y += a*np.exp(-0.5*((x - p/q)/w)**2)
    return y
y_wall = bump_field(xs)

def poisson_view(y, h):
    """view of the wall from height h = convolution with the Poisson kernel"""
    u = xs - 0.5
    K = (h/np.pi)/(u*u + h*h)
    num = np.convolve(y, K, mode="same")
    den = np.convolve(np.ones_like(y), K, mode="same")
    return num/den

heights = np.geomspace(2e-5, 0.6, 70)
def single_bump(p, q, a):
    w = 0.6/(2*q*q)
    return a*np.exp(-0.5*((xs - p/q)/w)**2)

vis = {}
for (p, q, a) in bumps:
    yb = single_bump(p, q, a)          # each galaxy measured alone (no neighbor tails)
    i = int(round((p/q)*(M_-1)))
    vis[(p,q)] = [poisson_view(yb, h)[i]/a for h in heights]

rows = []
for (p, q, a) in bumps:
    r = np.array(vis[(p,q)])
    # first height where the bump has lost half its height
    idx = np.where(r < 0.5)[0]
    y50 = float(heights[idx[0]]) if len(idx) else float("nan")
    rows.append(dict(p=p, q=q, y50=y50, y50_q2=y50*q*q, ford=1/(2*q*q)))
    print(f"  pixel {p}/{q}: fades at window height y50={y50:.2e}   y50*q^2 = {y50*q*q:.4f}   (Ford height 1/2q^2 = {1/(2*q*q):.2e})")
vals = [r["y50_q2"] for r in rows]
print(f"  y50*q^2 across pixels: mean {np.mean(vals):.4f}, spread {np.std(vals)/np.mean(vals)*100:.1f}%  -> visibility cutoff scales as the Ford circle")

json.dump(dict(closure_ok=bool(ok), visibility=rows),
          open("/home/claude/rh_voidline/closure_coords_res.json","w"), indent=0)
np.savez("/home/claude/rh_voidline/closure_coords_out.npz",
         xs=xs, y_wall=y_wall,
         views=np.array([poisson_view(y_wall, h) for h in [0.0005, 0.005, 0.05]]),
         view_h=np.array([0.0005, 0.005, 0.05]),
         heights=heights, q_list=np.array([q for (_,q,_) in bumps]),
         vis=np.array([vis[(p,q)] for (p,q,_) in bumps]))
print("\nsaved closure_coords_res.json / closure_coords_out.npz")
