import os, subprocess, sys
PY = sys.executable
env = dict(os.environ, CUBE_HOME=r"D:\planet\mika\cube2", CUBE_TICKERS=r"D:\planet\mika\cube2\tickers.txt", PYTHONIOENCODING="utf-8")
with open(r"D:\planet\mika\cube2\run.log", "w", encoding="utf-8") as log:
    for s in ["cube_fetch.py", "cube_leak_blur.py", "cube_leak_size.py"]:
        log.write(f"\n##### {s}\n"); log.flush()
        subprocess.run([PY, "-W", "ignore", os.path.join(r"D:\planet\mika\cube", s)], env=env, stdout=log, stderr=subprocess.STDOUT, cwd=r"D:\planet\mika\cube2")
    log.write("\n##### finished\n")
