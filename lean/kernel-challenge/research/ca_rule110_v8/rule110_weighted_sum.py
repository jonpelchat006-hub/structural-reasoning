import itertools
# Rule 110: neighborhood (l,c,r) -> bit ((110 >> (4l+2c+r)) & 1)
def f(l,c,r): return (110 >> (4*l+2*c+r)) & 1

# 1. the threshold form: next = bit 2 of (l + 3c + 3r + 1)
ok = all(((l + 3*c + 3*r + 1) >> 2) & 1 == f(l,c,r) for l in (0,1) for c in (0,1) for r in (0,1))
print("bit2(l+3c+3r+1) == rule110 on all 8 neighborhoods:", ok)

# 2. all small (wl,wc,wr,t,k): next = bit k of (wl*l + wc*c + wr*r + t), lane max value
sols = []
for wl,wc,wr in itertools.product(range(1,16), repeat=3):
    for t in range(0,16):
        mx = wl+wc+wr+t
        for k in range(0,5):
            if all(((wl*l+wc*c+wr*r+t)>>k)&1 == f(l,c,r) for l in (0,1) for c in (0,1) for r in (0,1)):
                sols.append((mx.bit_length(), mx, wl,wc,wr,t,k))
sols.sort()
print("solutions (lane bits, max, wl,wc,wr,t,k), first 12 of", len(sols))
for s in sols[:12]: print("  ", s)
print("any with t == 0:", any(s[5]==0 for s in sols))

# 3. two-op step: is there an invariant form  lane = u*cell + h  (h a fixed helper bit, a power of two)
#    with  bit q of (u*(wl*l+wc*c+wr*r) + (wl+wc+wr)*h) == f  and the helper bit regenerated:
#    bit q' of the same sum == 1 for every neighborhood, with 2^q'/2^q == h/u ?
found = []
for wl,wc,wr in itertools.product(range(1,24), repeat=3):
    W = wl+wc+wr
    for a in range(0,6):          # u = 2^a
        for b in range(0,8):      # h = 2^b
            if a == b: continue
            vals = {(l,c,r): (1<<a)*(wl*l+wc*c+wr*r) + W*(1<<b) for l in (0,1) for c in (0,1) for r in (0,1)}
            mx = max(vals.values())
            for q in range(0, mx.bit_length()):
                qh = q + (b - a)
                if qh < 0 or qh == q: continue
                if all((v>>q)&1 == f(*k) for k,v in vals.items()) and all((v>>qh)&1 == 1 for v in vals.values()):
                    found.append((mx.bit_length(), wl,wc,wr,a,b,q,qh))
found.sort()
print("two-op (helper-bit) forms found:", len(found))
for s in found[:10]: print("  ", s)
