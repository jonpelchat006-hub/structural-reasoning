// ops-generate.ts — the GENERATOR's first organ: create new content (the 6%
// INK_ADDED gap). These DRAW rather than rearrange.
import { Grid, dims, clone } from "./grid";
const inb = (g: Grid, y: number, x: number) => y >= 0 && y < g.length && x >= 0 && x < g[0].length;

// draw rays of each non-bg cell's colour outward in the given direction set,
// until hitting another non-bg cell or the edge.
export function drawRays(g: Grid, bg: number, dirMask: number): Grid | null {
  const [r, c] = dims(g);
  const dirs = [[1,0],[-1,0],[0,1],[0,-1]].filter((_, i) => dirMask & (1 << i));
  if (!dirs.length) return null;
  const out = clone(g); let drew = false;
  const seeds: [number, number, number][] = [];
  for (let y = 0; y < r; y++) for (let x = 0; x < c; x++) if (g[y][x] !== bg) seeds.push([y, x, g[y][x]]);
  if (!seeds.length || seeds.length > 200) return null;
  for (const [sy, sx, col] of seeds) for (const [dy, dx] of dirs) {
    let y = sy + dy, x = sx + dx;
    while (inb(g, y, x) && g[y][x] === bg) { out[y][x] = col; drew = true; y += dy; x += dx; }
  }
  return drew ? out : null;
}

// extend each non-bg cell by one step in all 4 directions (grow/dilate)
export function grow(g: Grid, bg: number): Grid | null {
  const [r, c] = dims(g);
  const out = clone(g); let drew = false;
  for (let y = 0; y < r; y++) for (let x = 0; x < c; x++) if (g[y][x] !== bg)
    for (const [dy, dx] of [[1,0],[-1,0],[0,1],[0,-1]]) { const ny = y+dy, nx = x+dx; if (inb(g, ny, nx) && out[ny][nx] === bg) { out[ny][nx] = g[y][x]; drew = true; } }
  return drew ? out : null;
}

// draw the full row+column cross through each non-bg cell (common "projection" tasks)
export function cross(g: Grid, bg: number): Grid | null {
  const [r, c] = dims(g);
  const out = clone(g); let drew = false;
  const seeds: [number, number, number][] = [];
  for (let y = 0; y < r; y++) for (let x = 0; x < c; x++) if (g[y][x] !== bg) seeds.push([y, x, g[y][x]]);
  if (!seeds.length || seeds.length > 60) return null;
  for (const [sy, sx, col] of seeds) {
    for (let x = 0; x < c; x++) if (out[sy][x] === bg) { out[sy][x] = col; drew = true; }
    for (let y = 0; y < r; y++) if (out[y][sx] === bg) { out[y][sx] = col; drew = true; }
  }
  return drew ? out : null;
}
