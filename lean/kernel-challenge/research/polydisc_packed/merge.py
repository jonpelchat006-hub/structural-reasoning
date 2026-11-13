"""Merge v7's generator graph (genLaneXC) with its PRS graph (prsDag) into one natdag: no 49-argument
application between them. Prototype for measurement."""
import re, sys
src = open(sys.argv[1]).read() if len(sys.argv) > 1 else ""
def natdag_body(name):
    i = src.index(f"def {name} ")
    j = src.index('natdag% "', i) + len('natdag% "')
    k = src.index('" [', j)
    return src[j:k]
def merged(gen):
    gl = natdag_body(gen).split("\n"); pl = natdag_body("prsDag").split("\n")
    out = []
    def tok_g(t):   # generator operands: x0 = s stays x0
        return t
    for l in gl[:-1]:
        out.append(l)
    args = gl[-1].split()[2:]          # 25 coefficient operands
    assert len(args) == 25
    base = len(out)
    # gz f k = add (shl (mul (shr f 1) k) 1) (land f 1)
    gz = []
    for i in range(24):
        f = args[i]; k = 24 - i
        a = len(out); out.append(f"shr {f} 1")
        out.append(f"mul v{a} {k}")
        out.append(f"shl v{a+1} 1")
        out.append(f"land {f} 1")
        out.append(f"add v{a+2} v{a+3}")
        gz.append(f"v{a+4}")
    off = len(out)
    ins = args + gz                    # prsDag x0..x48
    def tok_p(t):
        if t.startswith("v"): return f"v{int(t[1:]) + off}"
        if t.startswith("x"):
            i = int(t[1:])
            return ins[i] if i < 49 else "x1"
        return t
    for l in pl[:-1]:
        op, a, b = l.split()
        out.append(f"{op} {tok_p(a)} {tok_p(b)}")
    last = pl[-1].split()
    out.append("app x1 " + " ".join(tok_p(t) for t in last[2:]))
    return "\n".join(out)
if __name__ == "__main__":
    print(len(merged(sys.argv[2]).split("\n")))
