"""Render frames of the last sp80 run (D:\\planet\\eye\\play_sp80.npz) to PNG, no extra packages (zlib PNG writer)."""
import struct, sys, zlib
import numpy as np
PAL = ["FFFFFF", "CCCCCC", "999999", "666666", "333333", "000000", "E53AA3", "FF7BCC",
       "F93C31", "1E93FF", "88D8F1", "FFDC00", "FF851B", "921231", "4FCC30", "A356D6"]
PAL = np.array([[int(h[i:i + 2], 16) for i in (0, 2, 4)] for h in PAL], np.uint8)


def png(path, rgb):
    h, w, _ = rgb.shape
    raw = b"".join(b"\x00" + rgb[y].tobytes() for y in range(h))
    chunk = lambda t, d: struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
    open(path, "wb").write(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


game = sys.argv[1] if len(sys.argv) > 1 else "sp80"
F = np.load(rf"D:\planet\eye\play_{game}.npz")["F"]
print("frames", F.shape)
idx = [int(a) for a in sys.argv[2:]] or [0, 8, 9, 10, 40, 150]
tiles = []
for i in idx:
    if i >= len(F): continue
    f = F[i] % 16; img = PAL[f].repeat(6, 0).repeat(6, 1)
    png(rf"D:\planet\mika\frame_{game}_{i}.png", img); tiles.append(img)
    vals, cnt = np.unique(f, return_counts=True)
    print(i, "colours", dict(zip(vals.tolist(), cnt.tolist())))
