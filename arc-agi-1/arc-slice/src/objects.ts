// objects.ts — connected-component helpers for object-level operators.
import { Grid, dims } from "./grid";

export interface Obj { cells: [number, number][]; color: number; y0: number; y1: number; x0: number; x1: number; size: number; }

/** 4-connected components. mode "color": same-color blobs; "blob": any non-bg connected. */
export function components(g: Grid, bg: number, mode: "color" | "blob"): Obj[] {
  const [r, c] = dims(g);
  const seen = Array.from({ length: r }, () => Array(c).fill(false));
  const out: Obj[] = [];
  for (let y = 0; y < r; y++) for (let x = 0; x < c; x++) {
    if (g[y][x] === bg || seen[y][x]) continue;
    const color = g[y][x];
    const cells: [number, number][] = [];
    let y0 = y, y1 = y, x0 = x, x1 = x;
    const st: [number, number][] = [[y, x]];
    seen[y][x] = true;
    while (st.length) {
      const [cy, cx] = st.pop()!;
      cells.push([cy, cx]);
      y0 = Math.min(y0, cy); y1 = Math.max(y1, cy); x0 = Math.min(x0, cx); x1 = Math.max(x1, cx);
      for (const [dy, dx] of [[1,0],[-1,0],[0,1],[0,-1]]) {
        const ny = cy + dy, nx = cx + dx;
        if (ny<0||ny>=r||nx<0||nx>=c||seen[ny][nx]||g[ny][nx]===bg) continue;
        if (mode === "color" && g[ny][nx] !== color) continue;
        seen[ny][nx] = true; st.push([ny, nx]);
      }
    }
    out.push({ cells, color, y0, y1, x0, x1, size: cells.length });
  }
  return out;
}

export function blank(r: number, c: number, fill: number): Grid {
  return Array.from({ length: r }, () => Array(c).fill(fill));
}

/** Frequency of each non-bg color. */
export function colorCounts(g: Grid, bg: number): Map<number, number> {
  const m = new Map<number, number>();
  for (const row of g) for (const v of row) if (v !== bg) m.set(v, (m.get(v) ?? 0) + 1);
  return m;
}
