// ops-panel.ts — sub-grid / panel primitives (inner-shell muscle). Many ARC tasks
// are a grid-of-panels: pick the odd one, the majority one, or overlay them all.
import { Grid, dims, equal } from "./grid";
import { blank } from "./objects";

// split into panels by separator lines (full rows/cols of one non-bg colour)
export function panels(g: Grid, bg: number): Grid[] | null {
  const [r, c] = dims(g);
  const rowSep: number[] = [], colSep: number[] = [];
  for (let y = 0; y < r; y++) { const v = g[y][0]; if (v !== bg && g[y].every(z => z === v)) rowSep.push(y); }
  for (let x = 0; x < c; x++) { const v = g[0][x]; let all = true; for (let y = 0; y < r; y++) if (g[y][x] !== v) { all = false; break; } if (all && v !== bg) colSep.push(x); }
  // build row/col band boundaries excluding separators
  const bands = (n: number, seps: number[]) => { const b: [number,number][] = []; let s = 0; for (let i = 0; i <= n; i++) { if (i === n || seps.includes(i)) { if (i > s) b.push([s, i]); s = i + 1; } } return b; };
  const rb = bands(r, rowSep), cb = bands(c, colSep);
  if (rb.length * cb.length < 2 || rb.length * cb.length > 100) return null;
  const out: Grid[] = [];
  for (const [y0, y1] of rb) for (const [x0, x1] of cb) { const cell: Grid = []; for (let y = y0; y < y1; y++) cell.push(g[y].slice(x0, x1)); out.push(cell); }
  // require uniform cell size
  const h = out[0].length, w = out[0][0]?.length ?? 0;
  if (!out.every(p => p.length === h && p[0].length === w)) return null;
  return out;
}

function keyOf(p: Grid): string { return p.map(r => r.join(",")).join("/"); }

// the odd-one-out panel (unique among the cells)
export function selectOddPanel(g: Grid, bg: number): Grid | null {
  const ps = panels(g, bg); if (!ps || ps.length < 3) return null;
  const cnt = new Map<string, number>(); for (const p of ps) cnt.set(keyOf(p), (cnt.get(keyOf(p)) ?? 0) + 1);
  const uniq = ps.filter(p => cnt.get(keyOf(p)) === 1);
  return uniq.length === 1 ? uniq[0] : null;
}
// the majority panel (most common cell)
export function selectMajorityPanel(g: Grid, bg: number): Grid | null {
  const ps = panels(g, bg); if (!ps || ps.length < 3) return null;
  const cnt = new Map<string, number>(); for (const p of ps) cnt.set(keyOf(p), (cnt.get(keyOf(p)) ?? 0) + 1);
  let best = ps[0], bn = -1; for (const p of ps) { const n = cnt.get(keyOf(p))!; if (n > bn) { bn = n; best = p; } }
  return bn >= 2 ? best : null;
}
// overlay ALL panels cellwise into outColor (mode: and/or/xor across all cells)
export function overlayAllPanels(g: Grid, bg: number, mode: number, out: number): Grid | null {
  const ps = panels(g, bg); if (!ps || ps.length < 2) return null;
  const [h, w] = dims(ps[0]);
  const res = blank(h, w, bg);
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
    const ons = ps.map(p => p[y][x] !== bg);
    const cnt = ons.filter(Boolean).length;
    const on = mode === 0 ? cnt === ps.length : mode === 1 ? cnt > 0 : mode === 2 ? cnt % 2 === 1 : cnt === 1;
    if (on) res[y][x] = out;
  }
  return res;
}

// pick the panel with the most distinct colours (crit 0) or most non-bg cells (crit 1)
export function selectPanelBy(g: Grid, bg: number, crit: number): Grid | null {
  const ps = panels(g, bg); if (!ps || ps.length < 2) return null;
  const score = (p: Grid) => crit === 0 ? new Set(p.flat().filter(v=>v!==bg)).size : p.flat().filter(v=>v!==bg).length;
  let best = ps[0], bs = -1, ties = 0;
  for (const p of ps) { const s = score(p); if (s > bs) { bs = s; best = p; ties = 1; } else if (s === bs) ties++; }
  return ties === 1 ? best : null;
}
