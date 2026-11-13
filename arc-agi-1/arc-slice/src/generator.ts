// generator.ts — PARAMETRIC INDUCED generator for INK_ADDED tasks.
// Unlike the enumerate-style ops, this READS its parameters (source colour,
// direction, stop rule, paint colour) from the train DELTA, then verifies the
// induced program on every train pair before applying to test.
import { Grid, dims, clone, palette, background, equal } from "./grid";
import { components, blank, Obj } from "./objects";

export interface Pair { input: Grid; output: Grid; }
export type GenProg = (g: Grid) => Grid | null;

const inb = (g: Grid, y: number, x: number) => y >= 0 && y < g.length && x >= 0 && x < g[0].length;
const DIRS8: [number, number][] = [[-1,0],[1,0],[0,-1],[0,1],[-1,-1],[-1,1],[1,-1],[1,1]];
const ORTH: [number,number][] = [[-1,0],[1,0],[0,-1],[0,1]];
const DIAG: [number,number][] = [[-1,-1],[-1,1],[1,-1],[1,1]];

// delta cells where output differs from input (must be same dims)
function delta(inp: Grid, out: Grid): [number,number,number][] | null {
  if (inp.length !== out.length || inp[0].length !== out[0].length) return null;
  const d: [number,number,number][] = [];
  for (let y=0;y<inp.length;y++) for (let x=0;x<inp[0].length;x++)
    if (inp[y][x] !== out[y][x]) d.push([y,x,out[y][x]]);
  return d;
}

// ---------- Template 1: ray-cast from single-cell markers ----------
// from each isolated cell of colour S, shoot rays in a direction-set, painting C,
// stopping at edge or at first non-background cell (the "hit" rule).
function castRays(g: Grid, bg: number, S: number, C: number, ds: [number,number][], stopAtHit: boolean): Grid {
  const out = clone(g);
  const objs = components(g, bg, "blob");
  for (const o of objs) {
    if (o.color !== S || o.size !== 1) continue;
    const [y0,x0] = o.cells[0];
    for (const [dy,dx] of ds) {
      let y=y0+dy, x=x0+dx;
      while (inb(g,y,x)) {
        if (g[y][x] !== bg) { if (stopAtHit) break; }
        if (out[y][x] === bg) out[y][x] = C;
        y+=dy; x+=dx;
      }
    }
  }
  return out;
}
function induceRays(train: Pair[], bg: number, pal: number[]): GenProg | null {
  const dsets: [number,number][][] = [ORTH, DIAG, DIRS8, [[-1,0]],[[1,0]],[[0,-1]],[[0,1]]];
  for (const S of pal) for (const C of pal) for (const ds of dsets) for (const hit of [true,false]) {
    let ok = true;
    for (const p of train) { if (!equal(castRays(p.input,bg,S,C,ds,hit), p.output)) { ok=false; break; } }
    if (ok) return (g:Grid)=>castRays(g,bg,S,C,ds,hit);
  }
  return null;
}

// ---------- Template 2: connect aligned same-colour cells ----------
// for every pair of same-colour cells on a shared row/col with only bg between,
// fill the gap (with that colour, or a learned colour C).
function connectAligned(g: Grid, bg: number, C: number|null): Grid {
  const out = clone(g);
  const [r,c] = dims(g);
  // rows
  for (let y=0;y<r;y++){ let prev=-1, pc=-1;
    for (let x=0;x<c;x++){ if (g[y][x]!==bg){ if (prev>=0 && g[y][x]===pc){ for(let k=prev+1;k<x;k++) if(out[y][k]===bg) out[y][k]=C??pc; } prev=x; pc=g[y][x]; } } }
  // cols
  for (let x=0;x<c;x++){ let prev=-1, pc=-1;
    for (let y=0;y<r;y++){ if (g[y][x]!==bg){ if (prev>=0 && g[y][x]===pc){ for(let k=prev+1;k<y;k++) if(out[k][x]===bg) out[k][x]=C??pc; } prev=y; pc=g[y][x]; } } }
  return out;
}
function induceConnect(train: Pair[], bg: number, pal: number[]): GenProg | null {
  const cands: (number|null)[] = [null, ...pal];
  for (const C of cands) {
    let ok=true;
    for (const p of train){ if(!equal(connectAligned(p.input,bg,C), p.output)){ ok=false; break; } }
    if (ok) return (g:Grid)=>connectAligned(g,bg,C);
  }
  return null;
}

// ---------- Template 3: draw bbox (outline or fill) of each object ----------
function bboxPaint(g: Grid, bg: number, C: number, fill: boolean, byColor: boolean): Grid {
  const out = clone(g);
  for (const o of components(g,bg,"blob")) {
    const col = byColor ? o.color : C;
    for (let y=o.y0;y<=o.y1;y++) for (let x=o.x0;x<=o.x1;x++) {
      const edge = y===o.y0||y===o.y1||x===o.x0||x===o.x1;
      if ((fill || edge) && out[y][x]===bg) out[y][x]=col;
    }
  }
  return out;
}
function induceBbox(train: Pair[], bg: number, pal: number[]): GenProg | null {
  for (const byColor of [true,false]) for (const C of pal) for (const fill of [false,true]) {
    let ok=true;
    for (const p of train){ if(!equal(bboxPaint(p.input,bg,C,fill,byColor), p.output)){ ok=false; break; } }
    if (ok) return (g:Grid)=>bboxPaint(g,bg,C,fill,byColor);
  }
  return null;
}

// ---------- Template 4: constant learned overlay ----------
// when the delta is IDENTICAL across all train pairs (same positions+colours),
// the rule is "stamp this fixed overlay". Read it from pair 0, verify on rest.
function induceOverlay(train: Pair[]): GenProg | null {
  const d0 = delta(train[0].input, train[0].output);
  if (!d0 || d0.length===0) return null;
  for (let i=1;i<train.length;i++){ const di=delta(train[i].input,train[i].output);
    if(!di || di.length!==d0.length) return null;
    const k=(a:[number,number,number])=>a[0]+","+a[1]+","+a[2];
    const s0=new Set(d0.map(k)); if(!di.every(a=>s0.has(k(a)))) return null;
  }
  return (g:Grid)=>{ const out=clone(g); for(const[y,x,v]of d0){ if(!inb(g,y,x))return null as any; out[y][x]=v; } return out; };
}

// ---------- the inducer: try templates, return first that fits all train ----------
export function induceGenerator(train: Pair[]): GenProg | null {
  // require ink-added signature: same dims, output a superset-ish of input
  for (const p of train) if (p.input.length!==p.output.length || p.input[0].length!==p.output[0].length) {
    // overlay/ray/connect/bbox all assume same dims; bail to keep it focused
    return null;
  }
  const bg = background(train[0].input);
  const pal = Array.from(new Set(train.flatMap(p=>[...palette(p.input),...palette(p.output)]))).filter(c=>c!==bg);
  return induceRays(train,bg,pal) || induceConnect(train,bg,pal) || induceBbox(train,bg,pal) || induceOverlay(train);
}
