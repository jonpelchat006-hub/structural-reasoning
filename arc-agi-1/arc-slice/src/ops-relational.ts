// ops-relational.ts — inter-object operators. These depend on how objects
// RELATE to each other (rank, adjacency, alignment), not just per-object maps.
// This is the class ARC's hard tasks live in.
import { Grid, dims, clone } from "./grid";
import { components, blank, Obj } from "./objects";

const inb = (g: Grid, y: number, x: number) => y >= 0 && y < g.length && x >= 0 && x < g[0].length;

/** recolour each object by its SIZE rank (1,2,3,...). A downstream cmap maps
 * ranks -> the task's actual colours, so "recolour by size" tasks become
 * rank-paint + colour-repair. Relational: rank is defined across all objects. */
export function paintRank(g: Grid, bg: number, by: number): Grid | null {
  const objs = components(g, bg, "blob");
  if (objs.length < 2 || objs.length > 9) return null;
  const order = [...objs].sort((a, b) => by === 0 ? b.size - a.size : a.size - b.size);
  const out = clone(g);
  order.forEach((o, i) => { for (const [y, x] of o.cells) out[y][x] = i + 1; });
  return out;
}

/** pack whole objects toward an edge (0=down,1=up,2=right,3=left), stopping when
 * they hit another object or the wall. Relational: objects block each other. */
export function gravityObjects(g: Grid, bg: number, dir: number): Grid | null {
  const objs = components(g, bg, "blob");
  if (objs.length < 1 || objs.length > 30) return null;
  const [dy, dx] = dir === 0 ? [1, 0] : dir === 1 ? [-1, 0] : dir === 2 ? [0, 1] : [0, -1];
  // process objects nearest the target edge first
  const front = (o: Obj) => dir === 0 ? -o.y1 : dir === 1 ? o.y0 : dir === 2 ? -o.x1 : o.x0;
  const order = [...objs].sort((a, b) => front(a) - front(b));
  const out = blank(g.length, g[0].length, bg);
  for (const o of order) {
    let s = 0;
    while (true) {
      const ns = s + 1;
      let ok = true;
      for (const [y, x] of o.cells) {
        const ny = y + dy * ns, nx = x + dx * ns;
        if (!inb(g, ny, nx) || out[ny][nx] !== bg) { ok = false; break; }
      }
      if (!ok) break; s = ns;
    }
    for (const [y, x] of o.cells) out[y + dy * s][x + dx * s] = g[y][x];
  }
  return out;
}

/** keep only objects 4-adjacent to a cell of colour `marker`; others -> bg.
 * Relational: membership depends on touching another object's colour. */
export function keepTouching(g: Grid, bg: number, marker: number): Grid | null {
  if (marker === bg) return null;
  const objs = components(g, bg, "blob");
  if (objs.length < 2 || objs.length > 40) return null;
  const out = blank(g.length, g[0].length, bg);
  let kept = 0;
  for (const o of objs) {
    if (o.color === marker) { for (const [y, x] of o.cells) out[y][x] = g[y][x]; continue; }
    let touch = false;
    for (const [y, x] of o.cells) { for (const [ddy, ddx] of [[1,0],[-1,0],[0,1],[0,-1]]) if (inb(g, y+ddy, x+ddx) && g[y+ddy][x+ddx] === marker) { touch = true; break; } if (touch) break; }
    if (touch) { for (const [y, x] of o.cells) out[y][x] = g[y][x]; kept++; }
  }
  return kept > 0 ? out : null;
}

/** fill the straight segment between two aligned same-colour cells (row or col).
 * Relational: connects pairs of marks across empty space. */
export function connect(g: Grid, bg: number): Grid | null {
  const [r, c] = dims(g);
  const out = clone(g);
  let drew = false;
  // rows
  for (let y = 0; y < r; y++) {
    let prev = -1;
    for (let x = 0; x < c; x++) {
      if (g[y][x] === bg) continue;
      if (prev >= 0 && g[y][prev] === g[y][x]) {
        let allBg = true; for (let k = prev + 1; k < x; k++) if (g[y][k] !== bg) { allBg = false; break; }
        if (allBg && x - prev > 1) { for (let k = prev + 1; k < x; k++) { out[y][k] = g[y][x]; drew = true; } }
      }
      prev = x;
    }
  }
  // cols
  for (let x = 0; x < c; x++) {
    let prev = -1;
    for (let y = 0; y < r; y++) {
      if (g[y][x] === bg) continue;
      if (prev >= 0 && g[prev][x] === g[y][x]) {
        let allBg = true; for (let k = prev + 1; k < y; k++) if (g[k][x] !== bg) { allBg = false; break; }
        if (allBg && y - prev > 1) { for (let k = prev + 1; k < y; k++) { out[k][x] = g[y][x]; drew = true; } }
      }
      prev = y;
    }
  }
  return drew ? out : null;
}
