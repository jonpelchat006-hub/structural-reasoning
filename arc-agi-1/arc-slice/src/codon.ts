// codon.ts — the operator generator. A codon = (selector × action), the
// perception->action grid. detect() prunes which selectors fire per task; the
// colour-map finisher (bug-finder) closes whatever colour remains.
import { Grid, dims, equal, clone, background } from "./grid";
import { components, blank, Obj } from "./objects";
import { Pair } from "./loader";
import { measure, detect } from "./relations";

type GridFn = (g: Grid) => Grid | null;

// ── selectors: pick a set of objects (the "which") ──
function objs(g: Grid, bg: number): Obj[] { return components(g, bg, "color"); }
function uniqueBy(os: Obj[], key: (o: Obj) => string | number): Obj | null {
  const c = new Map<string|number, number>(); for (const o of os) c.set(key(o), (c.get(key(o))??0)+1);
  const u = os.filter(o => c.get(key(o)) === 1); return u.length === 1 ? u[0] : null;
}
function shapeKey(o: Obj): string {
  const w = o.x1-o.x0+1; return o.cells.map(([y,x])=>(y-o.y0)*w+(x-o.x0)).sort((a,b)=>a-b).join(",");
}
const SELECTORS: Record<string, (os: Obj[]) => Obj[]> = {
  all:          (os) => os,
  uniqueColor:  (os) => { const u = uniqueBy(os, o=>o.color); return u?[u]:[]; },
  uniqueShape:  (os) => { const u = uniqueBy(os, shapeKey);   return u?[u]:[]; },
  uniqueSize:   (os) => { const u = uniqueBy(os, o=>o.size);  return u?[u]:[]; },
  largest:      (os) => os.length?[os.reduce((a,b)=>b.size>a.size?b:a)]:[],
  smallest:     (os) => os.length?[os.reduce((a,b)=>b.size<a.size?b:a)]:[],
  majorityShape:(os) => { const c=new Map<string,number>(); for(const o of os)c.set(shapeKey(o),(c.get(shapeKey(o))??0)+1); let bk="",bn=-1; for(const[k,n]of c)if(n>bn){bn=n;bk=k;} return os.filter(o=>shapeKey(o)===bk); },
};

// ── actions: do something to the selected set (the "what"), parameterised on
// the imaginary axes whose MEANING is set by the unit: position->direction,
// colour->which-colour. The param is the quaternion-axis the action moves along.
function emit(g: Grid, sel: Obj[], bg: number, crop: boolean): Grid | null {
  if (!sel.length) return null;
  if (crop) { let y0=1e9,y1=-1,x0=1e9,x1=-1; for(const o of sel){y0=Math.min(y0,o.y0);y1=Math.max(y1,o.y1);x0=Math.min(x0,o.x0);x1=Math.max(x1,o.x1);}
    const out:Grid=[]; for(let y=y0;y<=y1;y++)out.push(g[y].slice(x0,x1+1)); return out; }
  const out=blank(g.length,g[0].length,bg); for(const o of sel)for(const[y,x]of o.cells)out[y][x]=g[y][x]; return out;
}
const inb = (g: Grid, y: number, x: number) => y>=0 && y<g.length && x>=0 && x<g[0].length;
function moveSel(g: Grid, sel: Obj[], bg: number, dir: number): Grid | null {
  if (!sel.length) return null;
  const [dy,dx] = dir===0?[1,0]:dir===1?[-1,0]:dir===2?[0,1]:[0,-1];
  const out = clone(g);
  for (const o of sel) for (const [y,x] of o.cells) out[y][x] = bg;
  for (const o of sel) {
    let s=0; while(true){ const ns=s+1; let ok=true; for(const[y,x]of o.cells){const ny=y+dy*ns,nx=x+dx*ns; if(!inb(g,ny,nx)||out[ny][nx]!==bg){ok=false;break;}} if(!ok)break; s=ns; }
    for (const [y,x] of o.cells) out[y+dy*s][x+dx*s] = g[y][x];
  }
  return out;
}
function paintSel(g: Grid, sel: Obj[], bg: number, c: number): Grid | null {
  if (!sel.length) return null;
  const out = clone(g); for (const o of sel) for (const [y,x] of o.cells) out[y][x] = c; return out;
}
interface ActionSpec { name: string; params: (pal: number[]) => (number|null)[]; fn: (g: Grid, sel: Obj[], bg: number, p: number|null) => Grid | null; }
const ACTIONS: ActionSpec[] = [
  { name: "keep",   params: () => [null], fn: (g,sel,bg) => emit(g,sel,bg,false) },
  { name: "cropTo", params: () => [null], fn: (g,sel,bg) => emit(g,sel,bg,true) },
  { name: "delete", params: () => [null], fn: (g,sel,bg) => { const out=clone(g); for(const o of sel)for(const[y,x]of o.cells)out[y][x]=bg; return out; } },
  { name: "move",   params: () => [0,1,2,3], fn: (g,sel,bg,p) => moveSel(g,sel,bg,p as number) },          // position axis: direction
  { name: "paint",  params: (pal) => pal,    fn: (g,sel,bg,p) => paintSel(g,sel,bg,p as number) },          // colour axis: which colour
];

// ── colour-map finisher (the bug-finder, function form) ──
function close(base: GridFn, train: Pair[]): GridFn | null {
  if (train.every(p => { const got=base(p.input); return !!got && equal(got, p.output); })) return base;
  const map = new Map<number,number>();
  for (const p of train) {
    const got = base(p.input); if (!got) return null;
    if (got.length!==p.output.length || got[0].length!==p.output[0].length) return null;
    for (let y=0;y<got.length;y++) for (let x=0;x<got[0].length;x++){ const a=got[y][x],b=p.output[y][x]; if(map.has(a)&&map.get(a)!==b) return null; map.set(a,b); }
  }
  if (![...map].some(([a,b])=>a!==b)) return null;
  const fn: GridFn = (g)=>{ const got=base(g); return got? got.map(r=>r.map(v=>map.get(v)??v)) : null; };
  return train.every(p=>{ const got=fn(p.input); return !!got && equal(got,p.output); }) ? fn : null;
}

// ── degeneracy: the cancellation structure (survivor vs cancelled majority) ──
// This is the sedenion intuition made concrete: group objects; where they cancel
// into a class, the SURVIVOR is the odd one and the majority's property is B's
// info the action acts with. AB=0 (equal -> cancel) marks where the rule lives.
function groupKey(name: string): (o: Obj) => string | number {
  return name === "shape" ? shapeKey : name === "size" ? (o)=>o.size : (o)=>o.color;
}
interface Degen { survivor: Obj; majColor: number; majObjs: Obj[]; }
function degeneracy(os: Obj[], key: (o: Obj)=>string|number): Degen | null {
  if (os.length < 3) return null;                       // need a class + a survivor
  const groups = new Map<string|number, Obj[]>();
  for (const o of os) { const k = key(o); (groups.get(k) ?? groups.set(k, []).get(k)!).push(o); }
  const singletons = [...groups.values()].filter(g => g.length === 1);
  if (singletons.length !== 1) return null;             // ambiguous or no odd-one-out -> skip
  const survivor = singletons[0][0];
  const maj = [...groups.values()].reduce((a,b)=>b.length>a.length?b:a);
  if (maj.length < 2) return null;
  // majority's dominant colour = B's info
  const cc = new Map<number,number>(); for (const o of maj) cc.set(o.color,(cc.get(o.color)??0)+1);
  let majColor = maj[0].color, bn=-1; for (const [c,n] of cc) if (n>bn){bn=n;majColor=c;}
  return { survivor, majColor, majObjs: maj };
}

// conditional relational actions: act on the survivor using the majority's info (and vice versa)
function relationalCandidates(): { name: string; fn: GridFn }[] {
  const out: { name: string; fn: GridFn }[] = [];
  for (const kname of ["shape","size","color"]) {
    const key = groupKey(kname);
    // paint survivor -> majority colour (erase the anomaly)
    out.push({ name: `surv(${kname})->majColor`, fn: (g) => { const b=background(g); const d=degeneracy(objs(g,b),key); if(!d)return null; const o=clone(g); for(const[y,x]of d.survivor.cells)o[y][x]=d.majColor; return o; } });
    // paint majority -> survivor colour (spread the anomaly)
    out.push({ name: `maj(${kname})->survColor`, fn: (g) => { const b=background(g); const d=degeneracy(objs(g,b),key); if(!d)return null; const o=clone(g); for(const m of d.majObjs)for(const[y,x]of m.cells)o[y][x]=d.survivor.color; return o; } });
    // keep only the survivor, cropped (odd-one-out extraction)
    out.push({ name: `surv(${kname}).crop`, fn: (g) => { const b=background(g); const d=degeneracy(objs(g,b),key); if(!d)return null; const o=d.survivor; const out2:Grid=[]; for(let y=o.y0;y<=o.y1;y++)out2.push(g[y].slice(o.x0,o.x1+1)); return out2; } });
    // delete only the survivor (remove the anomaly)
    out.push({ name: `del surv(${kname})`, fn: (g) => { const b=background(g); const d=degeneracy(objs(g,b),key); if(!d)return null; const o=clone(g); for(const[y,x]of d.survivor.cells)o[y][x]=b; return o; } });
  }
  return out;
}

export interface CodonSolve { fn: GridFn; desc: string; }

/** detection-directed: only instantiate selectors the relations flag as present. */
export function solveCodon(train: Pair[]): CodonSolve | null {
  const tags = detect(train);
  const bg = background(train[0].input);
  const sels = new Set<string>(["all","largest","smallest","majorityShape"]);
  if (tags.includes("UNIQUE_COLOR")) sels.add("uniqueColor");
  if (tags.includes("UNIQUE_SHAPE")) sels.add("uniqueShape");
  if (tags.includes("UNIQUE_SIZE"))  sels.add("uniqueSize");

  const pal = [...new Set(train.flatMap(p => [...p.input.flat(), ...p.output.flat()]))].sort((a,b)=>a-b);
  for (const sName of sels) for (const a of ACTIONS) for (const p of a.params(pal)) {
    const base: GridFn = (g) => { const b = background(g); const sel = SELECTORS[sName](objs(g, b)); return a.fn(g, sel, b, p); };
    const closed = close(base, train);
    if (closed) return { fn: closed, desc: `${sName}.${a.name}${p!==null?"("+p+")":""}` };
  }
  // conditional RELATIONAL actions (the degeneracy / survivor-vs-majority family)
  for (const cand of relationalCandidates()) {
    const closed = close(cand.fn, train);
    if (closed) return { fn: closed, desc: `REL:${cand.name}` };
  }
  return null;
}
