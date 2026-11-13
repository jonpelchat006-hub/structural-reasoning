import sys, subprocess, time, os, psutil
cmd = sys.argv[1]
env = dict(os.environ, PATH="/root/.elan/toolchains/leanprover--lean4---v4.33.1/bin:" + os.environ["PATH"])
t = time.time()
p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env, cwd="/home/claude/v9dev")
peak = 0
while p.poll() is None:
    try:
        pr = psutil.Process(p.pid); rss = pr.memory_info().rss + sum(c.memory_info().rss for c in pr.children(recursive=True))
    except Exception: rss = 0
    peak = max(peak, rss)
    if rss > 6.0e9:
        for c in psutil.Process(p.pid).children(recursive=True): c.kill()
        p.kill(); print("KILLED at 6GB"); break
    time.sleep(0.2)
out = p.stdout.read()
print("rc", p.returncode, f"{time.time()-t:.1f}s", f"peak={peak/1e9:.2f}GB", out[-300:])
