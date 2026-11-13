// ops-combinator.ts — higher-order operators (the structural HUBS).
// A combinator is the high-degree node of a solution: the "for each object" or
// "the special object" through which everything else connects. Object identity
// uses a D4-CANONICAL shape key — normalise each object to its own origin
// (centre of gravity) then compare up to rotation/reflection (Jonathan's
// "shift to balance, rotate against the imprints", applied per object).
import { Grid, dims, clone } from "./grid";
import { components, blank, Obj } from "./objects";

const flipH = (g: Grid): Grid => g.map((r) => r.slice().reverse());
const flipV = (g: Grid): Grid => g.slice().reverse().map((r) => r.slice());
const rot180 = (g: Grid): Grid => flipH(flipV(g));
const rot90 = (g: Grid): Grid => {
  const h = g.length, w = g[0].length;
  const n: Grid = Array.from({ length: w }, () => Array(h).fill(0));
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) n[x][h - 1 - y] = g[y][x];
  return n;
};

/** sub-grid covering an object's bbox (cells off the object set to -1). */
function objMask(o: Obj): Grid {
  const h = o.y1 - o.y0 + 1, w = o.x1 - o.x0 + 1;
  const m = blank(h, w, -1);
  for (const [y, x] of o.cells) m[y - o.y0][x - o.x0] = 1;
  return m;
}

/** D4-canonical key of an object's shape: origin-normalised, min over the 8
 * symmetries -> translation+rotation+reflection invariant. */
function canonShape(o: Obj): string {
  let g = objMask(o);
  const variants: Grid[] = [];
  for (let f = 0; f < 2; f++) {
    let cur = f ? flipH(g) : g;
    for (let r = 0; r < 4; r++) { variants.push(cur); cur = rot90(cur); }
  }
  const keys = variants.map((v) => v.map((row) => row.map((c) => (c === 1 ? "#" : ".")).join("")).join("/"));
  keys.sort();
  return keys[0];
}

function emit(g: Grid, objs: Obj[], chosen: Obj[], bg: number, crop: boolean): Grid | null {
  if (chosen.length === 0) return null;
  if (crop) {
    let y0=1e9,y1=-1,x0=1e9,x1=-1;
    for (const o of chosen){y0=Math.min(y0,o.y0);y1=Math.max(y1,o.y1);x0=Math.min(x0,o.x0);x1=Math.max(x1,o.x1);}
    const out: Grid = [];
    for (let y=y0;y<=y1;y++){const row:number[]=[];for(let x=x0;x<=x1;x++)row.push(g[y][x]);out.push(row);}
    return out;
  }
  const [r,c]=dims(g); const out=blank(r,c,bg);
  for (const o of chosen) for (const [y,x] of o.cells) out[y][x]=g[y][x];
  return out;
}

/** select the odd-one-out: the single object unique by shape/size/color. */
export function selectUnique(g: Grid, bg: number, mode: number, crop: number): Grid | null {
  const objs = components(g, bg, "color");
  if (objs.length < 2 || objs.length > 40) return null;
  const key = (o: Obj) => mode === 0 ? canonShape(o) : mode === 1 ? String(o.size) : String(o.color);
  const counts = new Map<string, number>();
  for (const o of objs) counts.set(key(o), (counts.get(key(o)) ?? 0) + 1);
  const uniq = objs.filter((o) => counts.get(key(o)) === 1);
  if (uniq.length !== 1) return null;
  return emit(g, objs, uniq, bg, !!crop);
}

/** keep the objects sharing the MAJORITY shape (drop the outliers). */
export function selectMajorityShape(g: Grid, bg: number, crop: number): Grid | null {
  const objs = components(g, bg, "color");
  if (objs.length < 2 || objs.length > 40) return null;
  const counts = new Map<string, number>();
  for (const o of objs) counts.set(canonShape(o), (counts.get(canonShape(o)) ?? 0) + 1);
  let best="", bestN=-1; for (const [k,n] of counts) if (n>bestN){bestN=n;best=k;}
  const keep = objs.filter((o) => canonShape(o) === best);
  return emit(g, objs, keep, bg, !!crop);
}

/** map an inner geometric transform over EACH object, in place. */
export function mapObjects(g: Grid, bg: number, inner: number): Grid | null {
  const objs = components(g, bg, "blob");
  if (objs.length === 0 || objs.length > 40) return null;
  const out = clone(g);
  for (const o of objs) {
    const h=o.y1-o.y0+1, w=o.x1-o.x0+1;
    const sub=blank(h,w,bg);
    for (const [y,x] of o.cells) sub[y-o.y0][x-o.x0]=g[y][x];
    const t = inner===0?flipH(sub):inner===1?flipV(sub):rot180(sub);
    for (const [y,x] of o.cells) out[y][x]=bg;             // clear original
    for (let y=0;y<h;y++) for (let x=0;x<w;x++) if (t[y][x]!==bg) out[o.y0+y][o.x0+x]=t[y][x];
  }
  return out;
}

// ── importance-gated combinators (the important/urgent square) ──
// Rank objects by an importance metric and act on the top-k. The magnitude is
// literally the number of objects (k), per Jonathan's pingpong system where
// direction = accept/reject and bounce_speed = how far to push.
import { colorCounts } from "./objects";

function ranked(objs: Obj[], by: number, g: Grid, bg: number): Obj[] {
  if (by === 0) return [...objs].sort((a, b) => b.size - a.size);       // largest first
  if (by === 1) return [...objs].sort((a, b) => a.size - b.size);       // smallest first
  const cc = colorCounts(g, bg);                                        // rarest colour first
  return [...objs].sort((a, b) => (cc.get(a.color) ?? 0) - (cc.get(b.color) ?? 0));
}

/** keep the k most-important objects (drop the rest). k = magnitude. */
export function keepTopK(g: Grid, bg: number, by: number, k: number, crop: number): Grid | null {
  const objs = components(g, bg, "blob");
  if (objs.length < 2 || objs.length > 40 || k >= objs.length) return null;
  const chosen = ranked(objs, by, g, bg).slice(0, k);
  return emit(g, objs, chosen, bg, !!crop);
}

/** apply an inner transform to the k most-important objects, in place. */
export function mapTopK(g: Grid, bg: number, inner: number, by: number, k: number): Grid | null {
  const objs = components(g, bg, "blob");
  if (objs.length < 2 || objs.length > 40) return null;
  const chosen = new Set(ranked(objs, by, g, bg).slice(0, k));
  const out = clone(g);
  for (const o of objs) {
    if (!chosen.has(o)) continue;
    const h=o.y1-o.y0+1, w=o.x1-o.x0+1;
    const sub=blank(h,w,bg);
    for (const [y,x] of o.cells) sub[y-o.y0][x-o.x0]=g[y][x];
    const t = inner===0?flipH(sub):inner===1?flipV(sub):rot180(sub);
    for (const [y,x] of o.cells) out[y][x]=bg;
    for (let y=0;y<h;y++) for (let x=0;x<w;x++) if (t[y][x]!==bg) out[o.y0+y][o.x0+x]=t[y][x];
  }
  return out;
}
