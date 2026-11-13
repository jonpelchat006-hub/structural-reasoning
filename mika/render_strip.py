"""One PNG strip of several frames from the last run of a game: python render_strip.py sp80 out.png 1 4 7 8"""
import sys
import numpy as np
import struct, zlib
PAL = ["FFFFFF", "CCCCCC", "999999", "666666", "333333", "000000", "E53AA3", "FF7BCC",
       "F93C31", "1E93FF", "88D8F1", "FFDC00", "FF851B", "921231", "4FCC30", "A356D6"]
PAL = np.array([[int(h[i:i + 2], 16) for i in (0, 2, 4)] for h in PAL], np.uint8)
def png(path, rgb):
    h, w, _ = rgb.shape
    raw = b"".join(b"\x00" + rgb[y].tobytes() for y in range(h))
    chunk = lambda t, d: struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
    open(path, "wb").write(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))
game, out = sys.argv[1], sys.argv[2]
F = np.load(rf"D:\planet\eye\play_{game}.npz")["F"]
idx = [int(a) for a in sys.argv[3:] if int(a) < len(F)]
gap = np.full((64 * 4, 4, 3), 40, np.uint8)
tiles = []
for i in idx:
    tiles += [PAL[F[i] % 16].repeat(4, 0).repeat(4, 1), gap]
png(out, np.concatenate(tiles[:-1], 1))
print("frames", idx)
