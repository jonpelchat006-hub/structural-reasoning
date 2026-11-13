import sys, subprocess, time, os
sys.path.insert(0, "/home/claude/v9dev/gen")
from lowdag2 import build, zenc
import reference_answers as ref, random
random.seed(5); n = random.randint(2 ** 57, 2 ** 63)
P = ref.candidate_polynomial(n)[0]
g, res, bad = build([zenc(c) for c in P])
F25 = " ".join(f"f{i}" for i in range(25)); FL = ", ".join(f"f{i}" for i in range(25))
SP = "/tmp/claude-0/-home-claude/3983609a-8f7f-50ae-819e-9b7efa2309ef/scratchpad/v9"
for N in [int(a) for a in sys.argv[1:]]:
    body = "\n".join(g.lines[:N]) + (f"\napp x25 v{N-1} v{N-1}" if N < len(g.lines) else f"\napp x25 {g.tok(res)} {g.tok(bad)}")
    src = f'''import V9.Dag
import V9.Low
namespace V9
def lowDagT ({F25} : Nat) : Nat × Nat :=
  natdag% "{body}" [{FL}, (@Prod.mk Nat Nat), dbTab]
end V9
'''
    open("/home/claude/v9dev/V9/BisT.lean", "w").write(src)
    t = time.time()
    env = dict(os.environ, PATH="/root/.elan/toolchains/leanprover--lean4---v4.33.1/bin:" + os.environ["PATH"])
    p = subprocess.Popen(f"cd /home/claude/v9dev && exec lake env lean -c {SP}/bis.c V9/BisT.lean", shell=True,
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env)
    peak = 0
    import psutil
    while p.poll() is None:
        try:
            pr = psutil.Process(p.pid); rss = pr.memory_info().rss + sum(c.memory_info().rss for c in pr.children(recursive=True))
        except Exception: rss = 0
        peak = max(peak, rss)
        if rss > 4e9 or time.time() - t > 300:
            for c in psutil.Process(p.pid).children(recursive=True): c.kill()
            p.kill(); break
        time.sleep(0.2)
    out = p.stdout.read()
    class R: pass
    r = R(); r.returncode = p.returncode; r.stderr = out; r.stdout = f" peak={peak/1e9:.2f}GB"
    sz = os.path.getsize(f"{SP}/bis.c") if os.path.exists(f"{SP}/bis.c") else 0
    print(N, "rc", r.returncode, f"{time.time()-t:.1f}s", "C bytes", sz, (r.stderr + r.stdout)[-200:].replace("\n", " "), flush=True)
    if os.path.exists(f"{SP}/bis.c"): os.remove(f"{SP}/bis.c")
