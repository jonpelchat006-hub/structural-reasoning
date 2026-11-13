// relations.ts — the perception layer. Measure the "base units" of a config
// (count, position, size, colour, shape) and DETECT relations that hold across
// every training pair (invariance under the free perturbations the examples give).
import { Grid, dims, equal, background } from "./grid";
import { components, Obj } from "./objects";
import { Pair } from "./loader";

// ── base units of a single object ──
export interface Feat { size: number; h: number; w: number; cy: number; cx: number; color: number; shape: string; }

function canonShape(o: Obj): string {
  const h = o.y1-o.y0+1, w = o.x1-o.x0+1;
  let cells = new Set(o.cells.map(([y,x]) => (y-o.y0)*w + (x-o.x0)));
  const variants: string[] = [];
  let H=h, W=w, cur = [...cells];
  const norm = (arr:[number,number][]) => { let mY=Math.min(...arr.map(a=>a[0])), mX=Math.min(...arr.map(a=>a[1])); return arr.map(([y,x])=>[y-mY,x-mX] as [number,number]).sort((a,b)=>a[0]-b[0]||a[1]-b[1]).map(a=>a.join(",")).join(";"); };
  let pts: [number,number][] = o.cells.map(([y,x])=>[y-o.y0,x-o.x0]);
  for (let f=0; f<2; f++) {
    let p = f ? pts.map(([y,x])=>[y,-x] as [number,number]) : pts;
    for (let r=0; r<4; r++) { variants.push(norm(p)); p = p.map(([y,x])=>[x,-y] as [number,number]); }
  }
  variants.sort(); return variants[0];
}

export function measure(g: Grid): { bg: number; objs: (Obj & { feat: Feat })[]; nObj: number; dims: [number,number]; palette: number[]; sym: string[] } {
  const bg = background(g);
  const raw = components(g, bg, "blob");
  const objs = raw.map((o) => ({ ...o, feat: { size: o.size, h: o.y1-o.y0+1, w: o.x1-o.x0+1, cy: (o.y0+o.y1)/2, cx: (o.x0+o.x1)/2, color: o.color, shape: raw.length<=40 ? canonShape(o) : "" } }));
  const pal = [...new Set(g.flat())].sort((a,b)=>a-b);
  const flipH=(x:Grid)=>x.map(r=>r.slice().reverse()), flipV=(x:Grid)=>x.slice().reverse();
  const sym: string[] = [];
  if (equal(g, flipH(g))) sym.push("H");
  if (equal(g, flipV(g))) sym.push("V");
  return { bg, objs, nObj: objs.length, dims: dims(g), palette: pal, sym };
}

// unique-by-X object index (exactly one), or -1
function uniqueBy(objs: {feat:Feat}[], key: (f:Feat)=>string|number): number {
  const cnt = new Map<string|number, number>();
  for (const o of objs) cnt.set(key(o.feat), (cnt.get(key(o.feat))??0)+1);
  const u = objs.filter(o => cnt.get(key(o.feat))===1);
  return u.length===1 ? objs.indexOf(u[0] as any) : -1;
}

function bboxGrid(g: Grid, o: Obj): Grid {
  const out: Grid = []; for (let y=o.y0;y<=o.y1;y++) out.push(g[y].slice(o.x0,o.x1+1)); return out;
}

/** detect relations that hold across EVERY training pair (invariants). */
export function detect(pairs: Pair[]): string[] {
  const tags: string[] = [];
  const all = (f: (p: Pair) => boolean) => pairs.every(f);
  const ins = pairs.map(p => measure(p.input)), outs = pairs.map(p => measure(p.output));

  // dimension relations
  if (all(p => p.input.length===p.output.length && p.input[0].length===p.output[0].length)) tags.push("OUT_EQ_IN_DIMS");
  if (outs.every(o => o.dims[0]===outs[0].dims[0] && o.dims[1]===outs[0].dims[1])) tags.push("CONST_OUT_DIMS");
  if (all(p => p.output.length<p.input.length || p.output[0].length<p.input[0].length)) tags.push("OUT_SMALLER");
  if (all(p => p.output.length>p.input.length || p.output[0].length>p.input[0].length)) tags.push("OUT_BIGGER");
  // integer scale ratio constant
  { const rs = pairs.map(p => [p.output.length/p.input.length, p.output[0].length/p.input[0].length]);
    if (rs.every(([a,b]) => Number.isInteger(a)&&Number.isInteger(b)&&a===rs[0][0]&&b===rs[0][1]&&a>=1&&b>=1&&!(a===1&&b===1))) tags.push("DIMS_RATIO_INT"); }

  // object-count relations
  if (ins.every(m => m.nObj===ins[0].nObj)) tags.push("CONST_N_OBJ_IN");
  if (pairs.every((_,i)=> ins[i].nObj===outs[i].nObj)) tags.push("N_OBJ_PRESERVED");

  // uniqueness (odd-one-out exists in every input)
  if (ins.every(m => uniqueBy(m.objs, f=>f.color)>=0)) tags.push("UNIQUE_COLOR");
  if (ins.every(m => m.objs.length<=40 && uniqueBy(m.objs, f=>f.shape)>=0)) tags.push("UNIQUE_SHAPE");
  if (ins.every(m => uniqueBy(m.objs, f=>f.size)>=0)) tags.push("UNIQUE_SIZE");

  // output is one selected input object (by uniqueness or extremes)
  const outIsObj = (sel: (m: ReturnType<typeof measure>) => number) => all(p => {
    const m = measure(p.input); const i = sel(m); if (i<0) return false;
    return equal(bboxGrid(p.input, m.objs[i]), p.output);
  });
  if (outIsObj(m=>uniqueBy(m.objs,f=>f.color))) tags.push("OUT_IS_UNIQUE_COLOR_OBJ");
  if (outIsObj(m=>uniqueBy(m.objs,f=>f.shape))) tags.push("OUT_IS_UNIQUE_SHAPE_OBJ");
  if (outIsObj(m=>{let b=-1,bs=-1; m.objs.forEach((o,i)=>{if(o.size>bs){bs=o.size;b=i;}}); return b;})) tags.push("OUT_IS_LARGEST_OBJ");
  if (outIsObj(m=>{let b=-1,bs=1e9; m.objs.forEach((o,i)=>{if(o.size<bs){bs=o.size;b=i;}}); return b;})) tags.push("OUT_IS_SMALLEST_OBJ");

  // consistent global colour map (shape preserved, colours remapped)
  if (tags.includes("OUT_EQ_IN_DIMS")) {
    const map = new Map<number,number>(); let ok=true;
    for (const p of pairs){ for(let y=0;y<p.input.length&&ok;y++)for(let x=0;x<p.input[0].length;x++){const a=p.input[y][x],b=p.output[y][x]; if(map.has(a)&&map.get(a)!==b){ok=false;break;} map.set(a,b);} }
    if (ok && [...map].some(([a,b])=>a!==b)) tags.push("GLOBAL_COLOR_MAP");
  }

  // symmetry present in inputs / outputs
  if (ins.every(m=>m.sym.length>0)) tags.push("INPUT_SYMMETRIC");
  if (outs.every(m=>m.sym.length>0)) tags.push("OUTPUT_SYMMETRIC");

  // objects aligned (share a row or column) in every input
  if (ins.every(m => { for(let i=0;i<m.objs.length;i++)for(let j=i+1;j<m.objs.length;j++){ if(Math.round(m.objs[i].feat.cy)===Math.round(m.objs[j].feat.cy)||Math.round(m.objs[i].feat.cx)===Math.round(m.objs[j].feat.cx)) return true;} return false; })) tags.push("OBJECTS_ALIGNED");

  return tags;
}
