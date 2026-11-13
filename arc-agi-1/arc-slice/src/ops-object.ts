// ops-object.ts — object-level transforms. Each returns Grid|null.
import { Grid, dims, clone } from "./grid";
import { components, blank, colorCounts, Obj } from "./objects";

const flipH = (g: Grid): Grid => g.map((r) => r.slice().reverse());
const flipV = (g: Grid): Grid => g.slice().reverse().map((r) => r.slice());

// ── color ops ──
export const keepColor = (g: Grid, c: number, bg: number): Grid =>
  g.map((r) => r.map((v) => (v === c ? v : bg)));
export const removeColor = (g: Grid, c: number, bg: number): Grid =>
  g.map((r) => r.map((v) => (v === c ? bg : v)));
export const swapColors = (g: Grid, a: number, b: number): Grid =>
  g.map((r) => r.map((v) => (v === a ? b : v === b ? a : v)));

// ── gravity ── pull non-bg cells to an edge, preserving order
export function gravity(g: Grid, bg: number, dir: number): Grid {
  const [r, c] = dims(g);
  const out = blank(r, c, bg);
  if (dir === 0 || dir === 1) { // 0=down,1=up (per column)
    for (let x = 0; x < c; x++) {
      const vals: number[] = [];
      for (let y = 0; y < r; y++) if (g[y][x] !== bg) vals.push(g[y][x]);
      for (let i = 0; i < vals.length; i++) {
        const y = dir === 0 ? r - vals.length + i : i;
        out[y][x] = vals[i];
      }
    }
  } else { // 2=right,3=left (per row)
    for (let y = 0; y < r; y++) {
      const vals: number[] = [];
      for (let x = 0; x < c; x++) if (g[y][x] !== bg) vals.push(g[y][x]);
      for (let i = 0; i < vals.length; i++) {
        const x = dir === 2 ? c - vals.length + i : i;
        out[y][x] = vals[i];
      }
    }
  }
  return out;
}

// ── symmetry completion ── overlay a reflection; non-bg wins
export function symmetrize(g: Grid, bg: number, axis: number): Grid {
  const m = axis === 0 ? flipH(g) : axis === 1 ? flipV(g) : null;
  const out = clone(g);
  const [r, c] = dims(g);
  if (m) {
    for (let y = 0; y < r; y++) for (let x = 0; x < c; x++)
      if (out[y][x] === bg && m[y][x] !== bg) out[y][x] = m[y][x];
    return out;
  }
  // axis 2: transpose overlay (only valid square)
  if (r !== c) return out;
  for (let y = 0; y < r; y++) for (let x = 0; x < c; x++)
    if (out[y][x] === bg && g[x][y] !== bg) out[y][x] = g[x][y];
  return out;
}

// ── object selection ── keep one component's cells, rest bg
function selectObj(g: Grid, bg: number, choose: (objs: Obj[]) => Obj | null, crop: boolean): Grid | null {
  const objs = components(g, bg, "blob");
  if (objs.length === 0) return null;
  const o = choose(objs);
  if (!o) return null;
  if (crop) {
    const out: Grid = [];
    for (let y = o.y0; y <= o.y1; y++) out.push(g[y].slice(o.x0, o.x1 + 1));
    return out;
  }
  const [r, c] = dims(g);
  const out = blank(r, c, bg);
  for (const [y, x] of o.cells) out[y][x] = g[y][x];
  return out;
}
export const keepLargest  = (g: Grid, bg: number, crop: number) => selectObj(g, bg, (o)=>o.reduce((a,b)=>b.size>a.size?b:a), !!crop);
export const keepSmallest = (g: Grid, bg: number, crop: number) => selectObj(g, bg, (o)=>o.reduce((a,b)=>b.size<a.size?b:a), !!crop);

// keep cells of the least / most frequent non-bg color
export function keepByColorFreq(g: Grid, bg: number, rare: number): Grid | null {
  const counts = colorCounts(g, bg);
  if (counts.size === 0) return null;
  let target = -1, best = rare ? Infinity : -1;
  for (const [col, n] of counts) {
    if (rare ? n < best : n > best) { best = n; target = col; }
  }
  return keepColor(g, target, bg);
}

// ── fill enclosed bg holes ──
export function fillHoles(g: Grid, bg: number, fill: number): Grid {
  const [r, c] = dims(g);
  const out = clone(g);
  const reach = Array.from({ length: r }, () => Array(c).fill(false));
  const st: [number, number][] = [];
  for (let y = 0; y < r; y++) for (let x = 0; x < c; x++)
    if ((y===0||x===0||y===r-1||x===c-1) && g[y][x]===bg && !reach[y][x]) { reach[y][x]=true; st.push([y,x]); }
  while (st.length) {
    const [cy, cx] = st.pop()!;
    for (const [dy,dx] of [[1,0],[-1,0],[0,1],[0,-1]]) {
      const ny=cy+dy,nx=cx+dx;
      if (ny<0||ny>=r||nx<0||nx>=c||reach[ny][nx]||g[ny][nx]!==bg) continue;
      reach[ny][nx]=true; st.push([ny,nx]);
    }
  }
  for (let y=0;y<r;y++) for (let x=0;x<c;x++) if (g[y][x]===bg && !reach[y][x]) out[y][x]=fill;
  return out;
}

// ── halves & overlay ──
export function half(g: Grid, which: number): Grid | null {
  const [r, c] = dims(g);
  if (which === 0) return r % 2 ? null : g.slice(0, r/2);
  if (which === 1) return r % 2 ? null : g.slice(r/2);
  if (which === 2) return c % 2 ? null : g.map((row)=>row.slice(0, c/2));
  return c % 2 ? null : g.map((row)=>row.slice(c/2));
}
// split into two halves along an axis and combine cellwise into outColor
export function overlayHalves(g: Grid, vertical: number, mode: number, out: number, bg: number): Grid | null {
  const a = half(g, vertical ? 0 : 2);
  const b = half(g, vertical ? 1 : 3);
  if (!a || !b) return null;
  const [r, c] = dims(a);
  const res = blank(r, c, bg);
  for (let y=0;y<r;y++) for (let x=0;x<c;x++) {
    const pa = a[y][x] !== bg, pb = b[y][x] !== bg;
    const on = mode===0 ? (pa&&pb) : mode===1 ? (pa||pb) : (pa!==pb); // and / or / xor
    if (on) res[y][x] = out;
  }
  return res;
}

// ── borders ──
export function trimBorder(g: Grid): Grid | null {
  const [r, c] = dims(g);
  if (r < 3 || c < 3) return null;
  return g.slice(1, r-1).map((row)=>row.slice(1, c-1));
}
export function addBorder(g: Grid, col: number): Grid {
  const [r, c] = dims(g);
  const out = blank(r+2, c+2, col);
  for (let y=0;y<r;y++) for (let x=0;x<c;x++) out[y+1][x+1]=g[y][x];
  return out;
}

// ── auto downscale: if grid is a uniform fy×fx block tiling, shrink it ──
export function downscaleAuto(g: Grid): Grid | null {
  const [r, c] = dims(g);
  const divs = (n: number) => { const d=[]; for (let k=2;k<=n;k++) if (n%k===0) d.push(k); return d; };
  for (const fy of [...divs(r), 1]) for (const fx of [...divs(c), 1]) {
    if (fy===1 && fx===1) continue;
    if (r%fy || c%fx) continue;
    const by=r/fy, bx=c/fx; let ok=true;
    outer: for (let yb=0;yb<fy;yb++) for (let xb=0;xb<fx;xb++) {
      const v=g[yb*by][xb*bx];
      for (let y=0;y<by&&ok;y++) for (let x=0;x<bx;x++) if (g[yb*by+y][xb*bx+x]!==v){ok=false;break outer;}
    }
    if (ok) { const out:Grid=[]; for (let yb=0;yb<fy;yb++){const row:number[]=[];for(let xb=0;xb<fx;xb++)row.push(g[yb*by][xb*bx]);out.push(row);} return out; }
  }
  return null;
}
