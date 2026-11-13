// ops-move.ts — object-movement muscle (the #1 missing group per the taxonomy).
import { Grid, dims, clone } from "./grid";
import { components, blank, Obj } from "./objects";

const inb = (g: Grid, y: number, x: number) => y >= 0 && y < g.length && x >= 0 && x < g[0].length;

// stamp: copy the template object onto each marker cell (the "copy" primitive —
// duplicating only changes N, no structural change; Jonathan's recognition rule).
export function stamp(g: Grid, bg: number): Grid | null {
  const objs = components(g, bg, "blob");
  if (objs.length < 2 || objs.length > 60) return null;
  const template = objs.reduce((a, b) => b.size > a.size ? b : a);
  if (template.size < 2) return null;
  const markers = objs.filter(o => o.size === 1 && o !== template);
  if (markers.length === 0) return null;
  const tcy = Math.round((template.y0 + template.y1) / 2), tcx = Math.round((template.x0 + template.x1) / 2);
  const out = clone(g);
  for (const m of markers) {
    const my = m.y0, mx = m.x0;
    out[my][mx] = bg;                                   // marker consumed
    for (const [ty, tx] of template.cells) {
      const ny = my + (ty - tcy), nx = mx + (tx - tcx);
      if (inb(g, ny, nx)) out[ny][nx] = g[ty][tx];
    }
  }
  return out;
}

// align all objects to share the largest object's centre row (axis 0) or col (axis 1)
export function alignToLargest(g: Grid, bg: number, axis: number): Grid | null {
  const objs = components(g, bg, "blob");
  if (objs.length < 2 || objs.length > 40) return null;
  const big = objs.reduce((a, b) => b.size > a.size ? b : a);
  const tcy = Math.round((big.y0 + big.y1) / 2), tcx = Math.round((big.x0 + big.x1) / 2);
  const out = blank(g.length, g[0].length, bg);
  for (const o of objs) {
    const cy = Math.round((o.y0 + o.y1) / 2), cx = Math.round((o.x0 + o.x1) / 2);
    const dy = axis === 0 ? tcy - cy : 0, dx = axis === 1 ? tcx - cx : 0;
    for (const [y, x] of o.cells) { const ny = y + dy, nx = x + dx; if (inb(g, ny, nx)) out[ny][nx] = g[y][x]; }
  }
  return out;
}

// move each object in dir until it touches another object or the wall (relational gravity)
export function moveToContact(g: Grid, bg: number, dir: number): Grid | null {
  const objs = components(g, bg, "blob");
  if (objs.length < 2 || objs.length > 40) return null;
  const [dy, dx] = dir === 0 ? [1, 0] : dir === 1 ? [-1, 0] : dir === 2 ? [0, 1] : [0, -1];
  const front = (o: Obj) => dir === 0 ? -o.y1 : dir === 1 ? o.y0 : dir === 2 ? -o.x1 : o.x0;
  const order = [...objs].sort((a, b) => front(a) - front(b));
  const out = blank(g.length, g[0].length, bg);
  for (const o of order) {
    let s = 0;
    while (true) { const ns = s + 1; let ok = true;
      for (const [y, x] of o.cells) { const ny = y + dy * ns, nx = x + dx * ns; if (!inb(g, ny, nx) || out[ny][nx] !== bg) { ok = false; break; } }
      if (!ok) break; s = ns; }
    for (const [y, x] of o.cells) out[y + dy * s][x + dx * s] = g[y][x];
  }
  return out;
}
