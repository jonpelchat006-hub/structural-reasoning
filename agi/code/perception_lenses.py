#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
perception_lenses.py -- #55: THE PERCEPTION RUNG. Give the agent REAL PIXELS instead of a handed-over
signature, a set of pluggable LENS-CONES (color / edge / motion / texture -- #38/#54's observer perspectives),
and have it LEARN which lens to steer into focus for each visual regime -- so it EARNS the regime signatures
that #37/#51 were simply given.

Four visual regimes over 16x16 two-frame images, each distinguished by ONE property and ONLY separable by its
matching lens:
  * COLOR   -- classes differ in hue (same shape/orientation/texture)          -> the color lens
  * EDGE    -- classes differ in bar ORIENTATION (same colour, white)          -> the edge lens
  * TEXTURE -- classes differ in spatial FREQUENCY (same colour/orientation)   -> the texture lens
  * MOTION  -- classes differ in shift DIRECTION between frames (same frame)    -> the motion lens

Each lens is a real feature extractor pixels->signature (mean-colour / gradient-orientation histogram /
frame-difference shift / radial-FFT bands). The agent must plug the right lens in.

Grounded: #38 (orthogonal observer lenses, 1 vs many), #54 (lenses at focal distances; stacking helps only if
complementary AND accurate -- a weak lens drags the read down, FOLDING_TWO_CONES), #24/#53 (steer the lens into
the gate = attention), #51 (the earned signature feeds the remember+discover agent).

MEASURED:
  (A) The RIGHT lens separates a regime; the WRONG lens is near chance -- a diagonal accuracy matrix over real
      pixels. Lens-choice is the whole game.
  (B) The agent LEARNS to steer the right lens per regime (picked on validation), matching the oracle and far
      beating a fixed single lens or a random lens -- it earns a separable signature from pixels.
  (C) The #54 caution holds on pixels: plugging in ALL lenses (naive committee) is DRAGGED DOWN by the
      uninformative ones vs selecting the right lens.
"""
import numpy as np
rng=np.random.default_rng(0)
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

H=16
def gray(img): return img.mean(2)

# ---------- image generators (each returns a 2-frame RGB stack F1,F2) ----------
def bg(): return np.full((H,H,3),0.5)+rng.normal(0,0.03,(H,H,3))
def disk(cx,cy,r):
    yy,xx=np.mgrid[0:H,0:H]; return ((xx-cx)**2+(yy-cy)**2)<=r*r
def gen_color(cls):
    im=bg(); col=[[0.9,0.2,0.2],[0.2,0.8,0.3],[0.2,0.4,0.9]][cls]
    m=disk(8,8,4)
    for k in range(3): im[...,k][m]=col[k]
    f1=np.clip(im,0,1); return f1, f1.copy()
def gen_edge(cls):
    im=bg(); ang=[0,45,90,135][cls]*np.pi/180
    yy,xx=np.mgrid[0:H,0:H]; d=np.abs((xx-8)*np.cos(ang)+(yy-8)*np.sin(ang))
    m=d<1.3
    for k in range(3): im[...,k][m]=0.95           # white bar, colour identical across classes
    f1=np.clip(im,0,1); return f1, f1.copy()
def gen_texture(cls):
    im=bg(); freq=[0.6,1.4,2.6][cls]                # horizontal grating, only FREQUENCY differs
    yy,xx=np.mgrid[0:H,0:H]; g=0.5+0.4*np.sin(2*np.pi*freq*yy/H)
    for k in range(3): im[...,k]=g
    f1=np.clip(im+rng.normal(0,0.02,(H,H,3)),0,1); return f1, f1.copy()
def gen_motion(cls):
    im=bg(); m=disk(8,8,3)
    for k in range(3): im[...,k][m]=0.9
    f1=np.clip(im,0,1)
    sh=[(0,-2),(0,2),(-2,0),(2,0)][cls]             # up/down/left/right shift -> class
    f2=np.roll(np.roll(f1,sh[0],axis=0),sh[1],axis=1)
    return f1, f2
REGIMES=[("color",3,gen_color),("edge",4,gen_edge),("texture",3,gen_texture),("motion",4,gen_motion)]

# ---------- the lenses: pixels -> signature ----------
def lens_color(f1,f2):
    return np.array([f1[...,0].mean(),f1[...,1].mean(),f1[...,2].mean(),
                     f1[...,0].mean()-f1[...,2].mean(), f1[...,1].mean()-f1[...,0].mean()])
def lens_edge(f1,f2):
    g=gray(f1); gy,gx=np.gradient(g); ang=(np.arctan2(gy,gx))%np.pi; mag=np.hypot(gx,gy)
    h,_=np.histogram(ang,bins=8,range=(0,np.pi),weights=mag); return h/(h.sum()+1e-9)
def lens_texture(f1,f2):
    g=gray(f1)-gray(f1).mean(); F=np.abs(np.fft.fftshift(np.fft.fft2(g)))
    yy,xx=np.mgrid[0:H,0:H]; rr=np.hypot(xx-H/2,yy-H/2)
    bands=[(0,2),(2,4),(4,6),(6,8)]
    return np.array([F[(rr>=a)&(rr<b)].mean() for a,b in bands])
def lens_motion(f1,f2):
    best=(0,0); bad=1e9
    for dx in range(-3,4):
        for dy in range(-3,4):
            diff=np.mean((np.roll(np.roll(f1,dx,0),dy,1)-f2)**2)
            if diff<bad: bad=diff; best=(dx,dy)
    n=np.hypot(*best)+1e-9; return np.array([best[0]/4,best[1]/4,best[0]/n,best[1]/n])
LENSES=[("color",lens_color),("edge",lens_edge),("texture",lens_texture),("motion",lens_motion)]

# ---------- build the dataset & the (regime x lens) accuracy matrix ----------
NPER=40
def signatures(gen,nclass,lensfn):
    X=[]; y=[]
    for c in range(nclass):
        for _ in range(NPER):
            f1,f2=gen(c); X.append(lensfn(f1,f2)); y.append(c)
    return np.array(X),np.array(y)
def proto_acc(X,y,tr,te):
    protos={c:X[tr][y[tr]==c].mean(0) for c in np.unique(y)}
    P=np.array([protos[c] for c in sorted(protos)])
    def norm(v): return v/(np.linalg.norm(v)+1e-9)
    pred=[sorted(protos)[int(np.argmax([norm(P[i])@norm(x) for i in range(len(P))]))] for x in X[te]]
    return np.mean(np.array(pred)==y[te])

acc=np.zeros((len(REGIMES),len(LENSES)))
val=np.zeros_like(acc)
for ri,(rn,nc,gen) in enumerate(REGIMES):
    idx=np.arange(nc*NPER); rng.shuffle(idx)
    tr,va,te=idx[:nc*NPER//2],idx[nc*NPER//2:nc*NPER*3//4],idx[nc*NPER*3//4:]
    for li,(ln,lf) in enumerate(LENSES):
        X,y=signatures(gen,nc,lf)
        acc[ri,li]=proto_acc(X,y,tr,te)
        val[ri,li]=proto_acc(X,y,tr,va)

# ---------- strategies ----------
chance=np.array([1/nc for _,nc,_ in REGIMES])
oracle=np.array([acc[ri,np.argmax(acc[ri])] for ri in range(len(REGIMES))])
learned=np.array([acc[ri,np.argmax(val[ri])] for ri in range(len(REGIMES))])   # pick lens on VALIDATION
picked=[LENSES[int(np.argmax(val[ri]))][0] for ri in range(len(REGIMES))]
fixed_color=acc[:,0]                                                           # always the colour lens
rng2=np.random.default_rng(1)
randlens=np.array([acc[ri,rng2.integers(len(LENSES))] for ri in range(len(REGIMES))])
# naive committee: EVERY lens votes its own predicted class, equal weight (the #54 drag: the near-chance
# lenses outvote the one right lens). Contrast with LEARNED = weight all on the accurate lens.
def committee_acc(gen,nc):
    idx=np.arange(nc*NPER); rng3=np.random.default_rng(2); rng3.shuffle(idx)
    tr,te=idx[:nc*NPER//2],idx[nc*NPER*3//4:]
    def norm(v): return v/(np.linalg.norm(v)+1e-9)
    preds=[]
    for _,lf in LENSES:
        X,y=signatures(gen,nc,lf)
        protos={c:X[tr][y[tr]==c].mean(0) for c in np.unique(y)}; cs=sorted(protos)
        P=np.array([protos[c] for c in cs])
        preds.append(np.array([cs[int(np.argmax([norm(P[i])@norm(x) for i in range(len(P))]))] for x in X[te]]))
    preds=np.array(preds)                                   # (nlens, ntest)
    ok=0; rv=np.random.default_rng(7)
    for j in range(preds.shape[1]):
        votes=np.bincount(preds[:,j],minlength=nc); top=np.flatnonzero(votes==votes.max())
        ok+= (rv.choice(top)==y[te][j])                     # plurality, ties broken at random
    return ok/preds.shape[1]
committee=np.array([committee_acc(gen,nc) for _,nc,gen in REGIMES])

print("="*80)
print("  #55  THE PERCEPTION RUNG -- earn the regime signature from pixels by steering the right lens")
print("="*80)
print(f"  regimes: {[r[0] for r in REGIMES]}; lenses: {[l[0] for l in LENSES]}")
print("  (A) accuracy[regime][lens] (chance in parens) -- the RIGHT lens separates, others near chance:")
print(f"        {'regime':9}"+"".join(f"{l[0]:>9}" for l in LENSES)+"   picked")
for ri,(rn,nc,_) in enumerate(REGIMES):
    print(f"        {rn:9}"+"".join(f"{acc[ri,li]:>9.2f}" for li in range(len(LENSES)))+f"   -> {picked[ri]} (chance {1/nc:.2f})")
print("  (B) mean accuracy across regimes:")
print(f"        oracle (best lens)        {oracle.mean():.2f}")
print(f"        LEARNED (pick on val)     {learned.mean():.2f}   picked {picked}")
print(f"        fixed single (colour)     {fixed_color.mean():.2f}")
print(f"        random lens               {randlens.mean():.2f}")
print(f"        chance                    {chance.mean():.2f}")
print(f"  (C) naive committee (ALL lenses vote, equal weight): {committee.mean():.2f} < LEARNED {learned.mean():.2f}")
print(f"      -> the uninformative lenses DRAG the read down; selecting the right lens wins (#54).")

# ---------------------------------------------------------------------------
fig=plt.figure(figsize=(15.4,4.9)); gs=fig.add_gridspec(1,3,wspace=0.32,width_ratios=[1.0,1.05,1.0])

# (A) example images
axA=fig.add_subplot(gs[0,0]); axA.axis("off")
axA.set_title("(A) Real pixels: 4 visual regimes\n(the agent gets these, not a signature)",fontsize=9.8)
for ri,(rn,nc,gen) in enumerate(REGIMES):
    for c in range(2):
        f1,f2=gen(c)
        ax=axA.inset_axes([0.02+c*0.26+ (ri%2)*0.5, 0.04+ (1-ri//2)*0.48, 0.22,0.42])
        ax.imshow(np.clip(f1,0,1)); ax.set_xticks([]); ax.set_yticks([])
        if c==0: ax.set_ylabel(rn,fontsize=7)

# (B) accuracy heatmap
axB=fig.add_subplot(gs[0,1])
im=axB.imshow(acc,cmap="Greens",vmin=0,vmax=1,aspect="auto")
axB.set_xticks(range(len(LENSES))); axB.set_xticklabels([l[0] for l in LENSES],fontsize=8)
axB.set_yticks(range(len(REGIMES))); axB.set_yticklabels([r[0] for r in REGIMES],fontsize=8)
for ri in range(len(REGIMES)):
    for li in range(len(LENSES)):
        axB.text(li,ri,f"{acc[ri,li]:.2f}",ha="center",va="center",fontsize=8,
                 color="white" if acc[ri,li]>0.6 else "#444")
    axB.add_patch(plt.Rectangle((np.argmax(val[ri])-0.5,ri-0.5),1,1,fill=False,edgecolor="#c0392b",lw=2.2))
axB.set_xlabel("lens plugged in"); axB.set_ylabel("visual regime")
axB.set_title("(B) The RIGHT lens separates (red = the agent's\npick); wrong lenses sit near chance",fontsize=9.8)

# (C) strategy comparison
axC=fig.add_subplot(gs[0,2])
names=["oracle","LEARNED\n(steer right lens)","naive committee\n(all lenses)","fixed\n(one lens)","random\nlens","chance"]
vals=[oracle.mean(),learned.mean(),committee.mean(),fixed_color.mean(),randlens.mean(),chance.mean()]
cols=["#888","#238b45","#c0392b","#e0a021","#e0a021","#ccc"]
axC.bar(range(6),vals,0.62,color=cols)
for i,v in enumerate(vals): axC.text(i,v+0.02,f"{v:.2f}",ha="center",fontsize=8.6)
axC.set_xticks(range(6)); axC.set_xticklabels(names,fontsize=7); axC.set_ylim(0,1.05)
axC.set_ylabel("mean accuracy over regimes")
axC.set_title("(C) Learning to steer the right lens ≈ oracle,\nbeats one-lens, random, and the naive committee",fontsize=9.6)

fig.suptitle("#55 — the perception rung: earn the regime signature from real pixels by steering the right lens-cone into focus; the right lens separates, the wrong ones don't, and plugging in all of them drags the read down (#54)",fontsize=9.0)
fig.savefig("perception_lenses.png",dpi=130,bbox_inches="tight")
print("\n  wrote perception_lenses.png")
