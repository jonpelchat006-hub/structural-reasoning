// ops-muscle.ts — high-value ARC primitive families ("muscle groups"). Bending
// paths with force/intent: the operations that diversify reach.
import { Grid, dims, clone } from "./grid";
import { components, blank } from "./objects";

const inb = (g: Grid, y: number, x: number) => y >= 0 && y < g.length && x >= 0 && x < g[0].length;

// ── cleanup: remove small noise objects ──
export function denoise(g: Grid, bg: number, minSize: number): Grid | null {
  const objs = components(g, bg, "blob");
  if (objs.length === 0 || objs.length > 200) return null;
  const out = clone(g); let removed = 0;
  for (const o of objs) if (o.size < minSize) { for (const [y, x] of o.cells) out[y][x] = bg; removed++; }
  return removed ? out : null;
}

// ── periodic fill: detect the repeating tile and fill bg cells (occlusion repair) ──
export function periodicFill(g: Grid, bg: number): Grid | null {
  const [r, c] = dims(g);
  const okPeriod = (py: number, px: number): boolean => {
    for (let y = 0; y < r; y++) for (let x = 0; x < c; x++) {
      const a = g[y][x], b = g[y % py][x % px];
      if (a !== bg && b !== bg && a !== b) return false;
    }
    return true;
  };
  const PY = Math.min(r, 15), PX = Math.min(c, 15);
  for (let py = 1; py <= PY; py++) for (let px = 1; px <= PX; px++) {
    if (py === r && px === c) continue;
    if (!okPeriod(py, px)) continue;
    // build the consensus tile, then fill
    const tile = blank(py, px, bg);
    for (let y = 0; y < r; y++) for (let x = 0; x < c; x++) if (g[y][x] !== bg) tile[y % py][x % px] = g[y][x];
    const out = clone(g); let filled = 0;
    for (let y = 0; y < r; y++) for (let x = 0; x < c; x++) if (out[y][x] === bg && tile[y % py][x % px] !== bg) { out[y][x] = tile[y % py][x % px]; filled++; }
    if (filled) return out;
  }
  return null;
}

// ── symmetry completion (auto): fill bg using whichever symmetry the non-bg part has ──
export function completeSymmetry(g: Grid, bg: number): Grid | null {
  const [r, c] = dims(g);
  const flips: ((y: number, x: number) => [number, number])[] = [
    (y, x) => [y, c - 1 - x], (y, x) => [r - 1 - y, x], (y, x) => [r - 1 - y, c - 1 - x],
  ];
  const out = clone(g); let filled = 0;
  for (const f of flips) {
    let consistent = true;
    for (let y = 0; y < r && consistent; y++) for (let x = 0; x < c; x++) {
      const [my, mx] = f(y, x); const a = g[y][x], b = g[my][mx];
      if (a !== bg && b !== bg && a !== b) { consistent = false; break; }
    }
    if (!consistent) continue;
    for (let y = 0; y < r; y++) for (let x = 0; x < c; x++) if (out[y][x] === bg) { const [my, mx] = f(y, x); if (g[my][mx] !== bg) { out[y][x] = g[my][mx]; filled++; } }
  }
  return filled ? out : null;
}

// ── panels: split by full separator lines, combine two panels cellwise ──
function panels(g: Grid, bg: number): Grid[] | null {
  const [r, c] = dims(g);
  const rowSep = (y: number) => g[y].every(v => v === g[y][0]) && g[y][0] !== bg;
  const colSep = (x: number) => { const v = g[0][x]; for (let y = 0; y < r; y++) if (g[y][x] !== v) return false; return v !== bg; };
  // vertical split (a separator column)
  for (let x = 1; x < c - 1; x++) if (colSep(x)) {
    const a = g.map(row => row.slice(0, x)), b = g.map(row => row.slice(x + 1));
    if (a[0].length === b[0].length) return [a, b];
  }
  for (let y = 1; y < r - 1; y++) if (rowSep(y)) {
    const a = g.slice(0, y), b = g.slice(y + 1);
    if (a.length === b.length) return [a, b];
  }
  return null;
}
export function combinePanels(g: Grid, bg: number, mode: number, out: number): Grid | null {
  const ps = panels(g, bg); if (!ps || ps.length !== 2) return null;
  const [a, b] = ps; const [r, c] = dims(a);
  if (b.length !== r || b[0].length !== c) return null;
  const res = blank(r, c, bg);
  for (let y = 0; y < r; y++) for (let x = 0; x < c; x++) {
    const pa = a[y][x] !== bg, pb = b[y][x] !== bg;
    const on = mode === 0 ? (pa && pb) : mode === 1 ? (pa || pb) : mode === 2 ? (pa !== pb) : (pa && !pb);
    if (on) res[y][x] = out;
  }
  return res;
}

// ── drawing: fill each object's bbox solid / draw its outline ──
export function bboxFill(g: Grid, bg: number): Grid | null {
  const objs = components(g, bg, "blob"); if (!objs.length || objs.length > 60) return null;
  const out = clone(g);
  for (const o of objs) for (let y = o.y0; y <= o.y1; y++) for (let x = o.x0; x <= o.x1; x++) out[y][x] = o.color;
  return out;
}
export function drawBox(g: Grid, bg: number, col: number): Grid | null {
  const objs = components(g, bg, "blob"); if (!objs.length || objs.length > 60) return null;
  const out = clone(g);
  for (const o of objs) for (let y = o.y0; y <= o.y1; y++) for (let x = o.x0; x <= o.x1; x++) if (y === o.y0 || y === o.y1 || x === o.x0 || x === o.x1) out[y][x] = col;
  return out;
}

// ── crop to a specific colour's bounding box ──
export function cropToColor(g: Grid, c: number): Grid | null {
  const [r, cc] = dims(g); let y0 = r, y1 = -1, x0 = cc, x1 = -1;
  for (let y = 0; y < r; y++) for (let x = 0; x < cc; x++) if (g[y][x] === c) { y0 = Math.min(y0, y); y1 = Math.max(y1, y); x0 = Math.min(x0, x); x1 = Math.max(x1, x); }
  if (y1 < 0) return null;
  const out: Grid = []; for (let y = y0; y <= y1; y++) out.push(g[y].slice(x0, x1 + 1)); return out;
}
