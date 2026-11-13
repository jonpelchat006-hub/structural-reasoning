// dsl.ts — the operator vocabulary (the "moves" the search composes).
// Each op maps a Grid -> Grid (or null when it cannot legally apply).
// This is the grid-equivalent of imagination-strategies' move set, and the
// ONLY genuinely net-new piece for ARC.
import { Grid, clone, dims, background, palette, cells } from "./grid";
import * as O from "./ops-object";
import * as C from "./ops-combinator";
import * as R from "./ops-relational";
import * as M from "./ops-muscle";
import * as MV from "./ops-move";
import * as GEN from "./ops-generate";
import * as PN from "./ops-panel";
import * as CT from "./ops-count";
import * as FR from "./ops-fractal";
import * as SH from "./ops-shape";
import * as R2 from "./ops-relate2";
import * as B2 from "./ops-batch2";

export interface Op { name: string; params: Record<string, number>; }

const MAX_CELLS = 2500; // ARC grids are <=30x30; reject blow-ups.

type Fn = (g: Grid, p: Record<string, number>) => Grid | null;

const rotate = (g: Grid, k: number): Grid => {
  let out = clone(g);
  for (let i = 0; i < ((k % 4) + 4) % 4; i++) {
    const [r, c] = dims(out);
    const n: Grid = Array.from({ length: c }, () => Array(r).fill(0));
    for (let y = 0; y < r; y++) for (let x = 0; x < c; x++) n[x][r - 1 - y] = out[y][x];
    out = n;
  }
  return out;
};

const flipH = (g: Grid): Grid => g.map((row) => row.slice().reverse());
const flipV = (g: Grid): Grid => g.slice().reverse().map((r) => r.slice());
const transpose = (g: Grid): Grid => {
  const [r, c] = dims(g);
  const n: Grid = Array.from({ length: c }, () => Array(r).fill(0));
  for (let y = 0; y < r; y++) for (let x = 0; x < c; x++) n[x][y] = g[y][x];
  return n;
};

const recolor = (g: Grid, from: number, to: number): Grid =>
  g.map((row) => row.map((v) => (v === from ? to : v)));

const cropToContent = (g: Grid, bg: number): Grid | null => {
  const [r, c] = dims(g);
  let r0 = r, r1 = -1, c0 = c, c1 = -1;
  for (let y = 0; y < r; y++) for (let x = 0; x < c; x++) if (g[y][x] !== bg) {
    r0 = Math.min(r0, y); r1 = Math.max(r1, y); c0 = Math.min(c0, x); c1 = Math.max(c1, x);
  }
  if (r1 < 0) return null;
  const out: Grid = [];
  for (let y = r0; y <= r1; y++) out.push(g[y].slice(c0, c1 + 1));
  return out;
};

const scale = (g: Grid, fy: number, fx: number): Grid | null => {
  if (fy < 1 || fx < 1) return null;
  const [r, c] = dims(g);
  if (r * fy * c * fx > MAX_CELLS) return null;
  const out: Grid = [];
  for (let y = 0; y < r; y++) for (let yy = 0; yy < fy; yy++) {
    const row: number[] = [];
    for (let x = 0; x < c; x++) for (let xx = 0; xx < fx; xx++) row.push(g[y][x]);
    out.push(row);
  }
  return out;
};

const tile = (g: Grid, ny: number, nx: number, mirror: number): Grid | null => {
  if (ny < 1 || nx < 1) return null;
  const [r, c] = dims(g);
  if (r * ny * c * nx > MAX_CELLS) return null;
  const out: Grid = [];
  for (let by = 0; by < ny; by++) {
    const block = mirror && by % 2 === 1 ? flipV(g) : g;
    for (let y = 0; y < r; y++) {
      const row: number[] = [];
      for (let bx = 0; bx < nx; bx++) {
        const src = mirror && bx % 2 === 1 ? block.map((rw) => rw.slice().reverse()) : block;
        for (let x = 0; x < c; x++) row.push(src[y][x]);
      }
      out.push(row);
    }
  }
  return out;
};

// largest 4-connected non-background object -> cropped to its bounding box
const largestObject = (g: Grid, bg: number): Grid | null => {
  const [r, c] = dims(g);
  const seen = Array.from({ length: r }, () => Array(c).fill(false));
  let best: { y0: number; y1: number; x0: number; x1: number; size: number } | null = null;
  for (let y = 0; y < r; y++) for (let x = 0; x < c; x++) {
    if (g[y][x] === bg || seen[y][x]) continue;
    let y0 = y, y1 = y, x0 = x, x1 = x, size = 0;
    const st = [[y, x]];
    seen[y][x] = true;
    while (st.length) {
      const [cy, cx] = st.pop()!;
      size++;
      y0 = Math.min(y0, cy); y1 = Math.max(y1, cy); x0 = Math.min(x0, cx); x1 = Math.max(x1, cx);
      for (const [dy, dx] of [[1,0],[-1,0],[0,1],[0,-1]]) {
        const ny = cy + dy, nx = cx + dx;
        if (ny>=0&&ny<r&&nx>=0&&nx<c&&!seen[ny][nx]&&g[ny][nx]!==bg) { seen[ny][nx]=true; st.push([ny,nx]); }
      }
    }
    if (!best || size > best.size) best = { y0, y1, x0, x1, size };
  }
  if (!best) return null;
  const out: Grid = [];
  for (let y = best.y0; y <= best.y1; y++) out.push(g[y].slice(best.x0, best.x1 + 1));
  return out;
};

// The registry. Each entry knows how to enumerate its own param sets for a task.

// enumeration helpers for object-op params
function prod<A,B>(a:A[],b:B[]):[A,B][]{const o:[A,B][]=[];for(const x of a)for(const y of b)o.push([x,y]);return o;}
function prod4<A,B,C,D>(a:A[],b:B[],c:C[],d:D[]):[A,B,C,D][]{const o:[A,B,C,D][]=[];for(const w of a)for(const x of b)for(const y of c)for(const z of d)o.push([w,x,y,z]);return o;}
function cap<T>(arr:T[],n=60):T[]{return arr.slice(0,n);}

export const OPS: Record<string, { fn: Fn; enumerate: (pal: number[]) => Record<string, number>[] }> = {
  identity:   { fn: (g) => g, enumerate: () => [{}] },
  rotate:     { fn: (g, p) => rotate(g, p.k), enumerate: () => [1,2,3].map((k)=>({k})) },
  flipH:      { fn: (g) => flipH(g), enumerate: () => [{}] },
  flipV:      { fn: (g) => flipV(g), enumerate: () => [{}] },
  transpose:  { fn: (g) => transpose(g), enumerate: () => [{}] },
  recolor:    { fn: (g, p) => recolor(g, p.from, p.to), enumerate: (pal) => {
      const out: Record<string, number>[] = [];
      for (const from of pal) for (const to of pal) if (from !== to) out.push({ from, to });
      return out;
  }},
  crop:       { fn: (g, p) => cropToContent(g, p.bg), enumerate: (pal) => pal.map((bg)=>({bg})) },
  scale:      { fn: (g, p) => scale(g, p.fy, p.fx), enumerate: () => {
      const out: Record<string, number>[] = [];
      for (const fy of [1,2,3]) for (const fx of [1,2,3]) if (!(fy===1&&fx===1)) out.push({fy,fx});
      return out;
  }},
  tile:       { fn: (g, p) => tile(g, p.ny, p.nx, p.mirror), enumerate: () => {
      const out: Record<string, number>[] = [];
      for (const ny of [1,2,3]) for (const nx of [1,2,3]) for (const m of [0,1])
        if (!(ny===1&&nx===1)) out.push({ny,nx,mirror:m});
      return out;
  }},
  largest:    { fn: (g, p) => largestObject(g, p.bg), enumerate: (pal) => pal.map((bg)=>({bg})) },
  // ── object-level operators ──
  keepColor:   { fn:(g,p)=>O.keepColor(g,p.c,p.bg),    enumerate:(pal)=>cap(prod(pal,pal).filter(([c,bg])=>c!==bg).map(([c,bg])=>({c,bg}))) },
  removeColor: { fn:(g,p)=>O.removeColor(g,p.c,p.bg),  enumerate:(pal)=>cap(prod(pal,pal).filter(([c,bg])=>c!==bg).map(([c,bg])=>({c,bg}))) },
  swap:        { fn:(g,p)=>O.swapColors(g,p.a,p.b),    enumerate:(pal)=>cap(prod(pal,pal).filter(([a,b])=>a<b).map(([a,b])=>({a,b}))) },
  gravity:     { fn:(g,p)=>O.gravity(g,p.bg,p.dir),    enumerate:(pal)=>cap(prod(pal,[0,1,2,3]).map(([bg,dir])=>({bg,dir}))) },
  symmetrize:  { fn:(g,p)=>O.symmetrize(g,p.bg,p.axis),enumerate:(pal)=>cap(prod(pal,[0,1,2]).map(([bg,axis])=>({bg,axis}))) },
  keepLargest: { fn:(g,p)=>O.keepLargest(g,p.bg,p.crop),  enumerate:(pal)=>cap(prod(pal,[0,1]).map(([bg,crop])=>({bg,crop}))) },
  keepSmallest:{ fn:(g,p)=>O.keepSmallest(g,p.bg,p.crop), enumerate:(pal)=>cap(prod(pal,[0,1]).map(([bg,crop])=>({bg,crop}))) },
  keepRare:    { fn:(g,p)=>O.keepByColorFreq(g,p.bg,1), enumerate:(pal)=>pal.map((bg)=>({bg})) },
  keepCommon:  { fn:(g,p)=>O.keepByColorFreq(g,p.bg,0), enumerate:(pal)=>pal.map((bg)=>({bg})) },
  fillHoles:   { fn:(g,p)=>O.fillHoles(g,p.bg,p.fill), enumerate:(pal)=>cap(prod(pal,pal).filter(([bg,fill])=>bg!==fill).map(([bg,fill])=>({bg,fill}))) },
  half:        { fn:(g,p)=>O.half(g,p.which), enumerate:()=>[0,1,2,3].map((which)=>({which})) },
  overlayHalves:{fn:(g,p)=>O.overlayHalves(g,p.vertical,p.mode,p.out,p.bg), enumerate:(pal)=>cap(prod4([0,1],[0,1,2],pal,pal).filter(([,,out,bg])=>out!==bg).map(([vertical,mode,out,bg])=>({vertical,mode,out,bg})),90) },
  trim:        { fn:(g)=>O.trimBorder(g), enumerate:()=>[{}] },
  addBorder:   { fn:(g,p)=>O.addBorder(g,p.col), enumerate:(pal)=>pal.map((col)=>({col})) },
  downscale:   { fn:(g)=>O.downscaleAuto(g), enumerate:()=>[{}] },
  // ── combinators (structural hubs) ──
  selectUnique:  { fn:(g,p)=>C.selectUnique(g,p.bg,p.mode,p.crop), enumerate:(pal)=>cap(prod(pal,[0,1,2]).flatMap(([bg,mode])=>[0,1].map((crop)=>({bg,mode,crop})))) },
  selectMajority:{ fn:(g,p)=>C.selectMajorityShape(g,p.bg,p.crop), enumerate:(pal)=>cap(prod(pal,[0,1]).map(([bg,crop])=>({bg,crop}))) },
  mapObjects:    { fn:(g,p)=>C.mapObjects(g,p.bg,p.inner), enumerate:(pal)=>cap(prod(pal,[0,1,2]).map(([bg,inner])=>({bg,inner}))) },
  cmap:          { fn:(g,p)=>g.map((row)=>row.map((v)=>(p[String(v)] ?? v))), enumerate:()=>[] },
  keepTopK:      { fn:(g,p)=>C.keepTopK(g,p.bg,p.by,p.k,p.crop), enumerate:(pal)=>cap(prod4(pal,[0,1,2],[1,2,3],[0,1]).map(([bg,by,k,crop])=>({bg,by,k,crop})),36) },
  mapTopK:       { fn:(g,p)=>C.mapTopK(g,p.bg,p.inner,p.by,p.k), enumerate:(pal)=>cap(prod4(pal,[0,1,2],[0,1,2],[1,2,3]).map(([bg,inner,by,k])=>({bg,inner,by,k})),36) },
  // relational (inter-object)
  paintRank:     { fn:(g,p)=>R.paintRank(g,p.bg,p.by), enumerate:(pal)=>cap(prod(pal,[0,1]).map(([bg,by])=>({bg,by}))) },
  gravityObj:    { fn:(g,p)=>R.gravityObjects(g,p.bg,p.dir), enumerate:(pal)=>cap(prod(pal,[0,1,2,3]).map(([bg,dir])=>({bg,dir}))) },
  keepTouching:  { fn:(g,p)=>R.keepTouching(g,p.bg,p.marker), enumerate:(pal)=>cap(prod(pal,pal).filter(([bg,m])=>bg!==m).map(([bg,marker])=>({bg,marker}))) },
  connect:       { fn:(g,p)=>R.connect(g,p.bg), enumerate:(pal)=>pal.map((bg)=>({bg})) },
  shift:         { fn:(g,p)=>{ const r=g.length,c=g[0].length; const out=Array.from({length:r},()=>Array(c).fill(p.bg)); for(let y=0;y<r;y++)for(let x=0;x<c;x++){const ny=y+p.dy,nx=x+p.dx; if(ny>=0&&ny<r&&nx>=0&&nx<c) out[ny][nx]=g[y][x];} return out; }, enumerate:(pal)=>cap(prod4([-2,-1,1,2],[-2,-1,1,2],pal,[0]).map(([dy,dx,bg])=>({dy,dx,bg})),40) },
  // ── muscle groups ──
  denoise:       { fn:(g,p)=>M.denoise(g,p.bg,p.min), enumerate:(pal)=>cap(prod(pal,[2,3]).map(([bg,min])=>({bg,min}))) },
  periodicFill:  { fn:(g,p)=>M.periodicFill(g,p.bg), enumerate:(pal)=>pal.map((bg)=>({bg})) },
  completeSym:   { fn:(g,p)=>M.completeSymmetry(g,p.bg), enumerate:(pal)=>pal.map((bg)=>({bg})) },
  combinePanels: { fn:(g,p)=>M.combinePanels(g,p.bg,p.mode,p.out), enumerate:(pal)=>cap(prod4(pal,[0,1,2,3],pal,[0]).filter(([bg,,out])=>bg!==out).map(([bg,mode,out])=>({bg,mode,out})),60) },
  bboxFill:      { fn:(g,p)=>M.bboxFill(g,p.bg), enumerate:(pal)=>pal.map((bg)=>({bg})) },
  drawBox:       { fn:(g,p)=>M.drawBox(g,p.bg,p.col), enumerate:(pal)=>cap(prod(pal,pal).filter(([bg,col])=>bg!==col).map(([bg,col])=>({bg,col}))) },
  cropToColor:   { fn:(g,p)=>M.cropToColor(g,p.c), enumerate:(pal)=>pal.map((c)=>({c})) },
  // ── object-movement muscle ──
  stamp:         { fn:(g,p)=>MV.stamp(g,p.bg), enumerate:(pal)=>pal.map((bg)=>({bg})) },
  alignLargest:  { fn:(g,p)=>MV.alignToLargest(g,p.bg,p.axis), enumerate:(pal)=>cap(prod(pal,[0,1]).map(([bg,axis])=>({bg,axis}))) },
  moveContact:   { fn:(g,p)=>MV.moveToContact(g,p.bg,p.dir), enumerate:(pal)=>cap(prod(pal,[0,1,2,3]).map(([bg,dir])=>({bg,dir}))) },
  // ── generator (create content) ──
  drawRays:      { fn:(g,p)=>GEN.drawRays(g,p.bg,p.mask), enumerate:(pal)=>cap(prod(pal,[1,2,4,8,15]).map(([bg,mask])=>({bg,mask}))) },
  grow:          { fn:(g,p)=>GEN.grow(g,p.bg), enumerate:(pal)=>pal.map((bg)=>({bg})) },
  cross:         { fn:(g,p)=>GEN.cross(g,p.bg), enumerate:(pal)=>pal.map((bg)=>({bg})) },
  // ── panel / sub-grid muscle ──
  oddPanel:      { fn:(g,p)=>PN.selectOddPanel(g,p.bg), enumerate:(pal)=>pal.map((bg)=>({bg})) },
  majPanel:      { fn:(g,p)=>PN.selectMajorityPanel(g,p.bg), enumerate:(pal)=>pal.map((bg)=>({bg})) },
  overlayPanels: { fn:(g,p)=>PN.overlayAllPanels(g,p.bg,p.mode,p.out), enumerate:(pal)=>cap(prod4(pal,[0,1,2,3],pal,[0]).filter(([bg,,out])=>bg!==out).map(([bg,mode,out])=>({bg,mode,out})),60) },
  // ── count / shape-class / flood / panel-by ──
  countEmit:     { fn:(g,p)=>CT.countEmit(g,p.bg,p.col,p.mode), enumerate:(pal)=>cap(prod(pal,[0,1,2]).flatMap(([col,mode])=>pal.map(bg=>({bg,col,mode}))),60) },
  colorByShape:  { fn:(g,p)=>CT.colorByShape(g,p.bg), enumerate:(pal)=>pal.map((bg)=>({bg})) },
  floodBorder:   { fn:(g,p)=>CT.floodBorder(g,p.bg,p.fill), enumerate:(pal)=>cap(prod(pal,pal).filter(([bg,fill])=>bg!==fill).map(([bg,fill])=>({bg,fill})),40) },
  panelBy:       { fn:(g,p)=>PN.selectPanelBy(g,p.bg,p.crit), enumerate:(pal)=>cap(prod(pal,[0,1]).map(([bg,crit])=>({bg,crit}))) },
  // ── self-similar / fractal ──
  fractal:       { fn:(g,p)=>FR.fractalTile(g,p.bg,p.inv), enumerate:(pal)=>cap(prod(pal,[0,1]).map(([bg,inv])=>({bg,inv}))) },
  mirrorConcat:  { fn:(g,p)=>FR.mirrorConcat(g,p.dir), enumerate:()=>[{dir:0},{dir:1}] },
  // ── shape transforms ──
  outline:       { fn:(g,p)=>SH.outline(g,p.bg), enumerate:(pal)=>pal.map((bg)=>({bg})) },
  fillObjHoles:  { fn:(g,p)=>SH.fillObjectHoles(g,p.bg), enumerate:(pal)=>pal.map((bg)=>({bg})) },
  // ── object relations / diagonal symmetry ──
  connectObjects:{ fn:(g,p)=>R2.connectObjects(g,p.bg), enumerate:(pal)=>pal.map((bg)=>({bg})) },
  completeDiag:  { fn:(g,p)=>R2.completeDiag(g,p.bg), enumerate:(pal)=>pal.map((bg)=>({bg})) } ,
  // ── batch 2 ──
  antiTranspose: { fn:(g)=>B2.antiTranspose(g), enumerate:()=>[] },
  extractCell:   { fn:(g,p)=>B2.extractCell(g,p.bg,p.which), enumerate:()=>[] },
  scaleByCount:  { fn:(g,p)=>B2.scaleByCount(g,p.bg,p.mode), enumerate:()=>[] },
  borderObjects: { fn:(g,p)=>B2.borderObjects(g,p.bg,p.inv), enumerate:()=>[] },
  smoothNeighbor:{ fn:(g,p)=>B2.smoothNeighbor(g,p.bg), enumerate:(pal)=>pal.slice(0,2).map((bg)=>({bg})) },
  rotateObjects: { fn:(g,p)=>B2.rotateObjects(g,p.bg), enumerate:(pal)=>pal.slice(0,2).map((bg)=>({bg})) },
};

export const OP_NAMES = Object.keys(OPS);

export function applyOp(op: Op, g: Grid): Grid | null {
  const spec = OPS[op.name];
  if (!spec) return null;
  const out = spec.fn(g, op.params);
  if (out && cells(out) > MAX_CELLS) return null;
  return out;
}
