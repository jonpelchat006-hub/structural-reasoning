f = r"D:\planet\mika\cube\cube_leak_blur.py"
s = open(f, encoding="utf-8").read()
old = 'M = M.copy(); M["q"]'
new = 'M = M[M.groupby("year").ticker.transform("size") >= 25].copy(); M["q"]'
assert s.count(old) == 1
open(f, "w", encoding="utf-8").write(s.replace(old, new))
print("ok")
