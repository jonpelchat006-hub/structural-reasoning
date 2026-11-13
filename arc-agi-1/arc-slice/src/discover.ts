// discover.ts — the generator RECEIVES an element (native prefix op1, "placed where it
// goes"), then must find the PATH BACK TO CORE: induce the residual transform that closes
// input->output. A consistent residual that ISN'T already a native atom = a DISCOVERED
// primitive. Wins are remembered as COMPOUNDS (op1 ∘ discovered) in a library.
import * as path from "path"; import * as fs from "fs";
import { loadTasks } from "./loader";
import { OPS, OP_NAMES, applyOp } from "./dsl";
import { taskPalette } from "./transfer";
import { equal } from "./grid";
import { components, blank, Obj } from "./objects";
import { induceStamp } from "./draw2";
import { induceTrace } from "./trace";
import { induceLocalRule, induceLocalRuleMS } from "./prune";
import { induceHoleFillByEncloser, induceHoleFillByRank } from "./topo";
import { induceRegisterCombine } from "./roof";
const equalG=(a:Grid,b:Grid)=>!!a&&!!b&&a.length===b.length&&a[0].length===b[0].length&&a.every((r,i)=>r.every((v,j)=>v===b[i][j]));
type Grid=number[][];
const tasks=loadTasks(path.join(__dirname,"..","data"));
const combined=new Set(fs.readFileSync(path.join(__dirname,"..","combined_solved.txt"),"utf8").trim().split(/\s+/));
const eqG=(a:Grid,b:Grid)=>!!a&&!!b&&a.length===b.length&&a[0].length===b[0].length&&a.every((r,i)=>r.every((v,j)=>v===b[i][j]));

// ── RESIDUAL inducers (the "path back to core"; a fit one = a discovered primitive) ──
// D1: object recolor by SIZE-RANK — learn rank->colour from train, apply.
function induceRankRecolor(nt:{input:Grid,output:Grid}[]):((g:Grid)=>Grid|null)|null{
  const map=new Map<number,number>(); const bg=0;
  for(const p of nt){ const objs=components(p.input,bg,"blob").slice().sort((a,b)=>b.size-a.size);
    for(let r=0;r<objs.length;r++){ const o=objs[r]; const cols=new Set(o.cells.map(([y,x])=>p.output[y]?.[x])); if(cols.size!==1)return null;
      const oc=[...cols][0]; if(oc==null)return null; if(map.has(r)&&map.get(r)!==oc)return null; map.set(r,oc); } }
  if(!map.size) return null;
  return (g:Grid)=>{ const out=g.map(r=>r.slice()); const objs=components(g,bg,"blob").slice().sort((a,b)=>b.size-a.size);
    for(let r=0;r<objs.length;r++){ const c=map.get(r); if(c==null)continue; for(const[y,x]of objs[r].cells)out[y][x]=c; } return out; };
}
// D2: object recolor by SHAPE-class — learn shapeKey->colour from train.
function induceShapeRecolor(nt:{input:Grid,output:Grid}[]):((g:Grid)=>Grid|null)|null{
  const bg=0; const key=(o:Obj)=>o.cells.map(([y,x])=>(y-o.y0)*64+(x-o.x0)).sort((a,b)=>a-b).join(",");
  const map=new Map<string,number>();
  for(const p of nt){ for(const o of components(p.input,bg,"blob")){ const cols=new Set(o.cells.map(([y,x])=>p.output[y]?.[x])); if(cols.size!==1)return null;
    const oc=[...cols][0]; if(oc==null)return null; const k=key(o); if(map.has(k)&&map.get(k)!==oc)return null; map.set(k,oc); } }
  if(!map.size) return null;
  return (g:Grid)=>{ const out=g.map(r=>r.slice()); for(const o of components(g,bg,"blob")){ const c=map.get(key(o)); if(c==null)continue; for(const[y,x]of o.cells)out[y][x]=c; } return out; };
}
// D3: constant overlay — fixed delta repeated across train.
function induceOverlay(nt:{input:Grid,output:Grid}[]):((g:Grid)=>Grid|null)|null{
  const d0:[number,number,number][]=[]; const a=nt[0];
  if(a.input.length!==a.output.length||a.input[0].length!==a.output[0].length)return null;
  for(let y=0;y<a.input.length;y++)for(let x=0;x<a.input[0].length;x++) if(a.input[y][x]!==a.output[y][x]) d0.push([y,x,a.output[y][x]]);
  if(!d0.length)return null;
  for(const p of nt){ if(p.input.length!==a.input.length||p.input[0].length!==a.input[0].length)return null;
    for(const[y,x,v]of d0) if(p.output[y][x]!==v)return null; }
  return (g:Grid)=>{ if(g.length!==a.input.length||g[0].length!==a.input[0].length)return null; const out=g.map(r=>r.slice()); for(const[y,x,v]of d0)out[y][x]=v; return out; };
}
// D4: colour-map residual (learn in-colour -> out-colour, same dims)
function induceColorMap(nt:{input:Grid,output:Grid}[]):((g:Grid)=>Grid|null)|null{
  const m=new Map<number,number>();
  for(const p of nt){ if(p.input.length!==p.output.length||p.input[0].length!==p.output[0].length)return null;
    for(let y=0;y<p.input.length;y++)for(let x=0;x<p.input[0].length;x++){ const a=p.input[y][x],b=p.output[y][x]; if(m.has(a)&&m.get(a)!==b)return null; m.set(a,b); } }
  let nontrivial=false; for(const[a,b]of m)if(a!==b)nontrivial=true; if(!nontrivial)return null;
  return (g:Grid)=>g.map(r=>r.map(v=>m.has(v)?m.get(v)!:v));
}
// D5: translation — learn a single (dy,dx) shift of non-bg content on a bg canvas
function induceShift(nt:{input:Grid,output:Grid}[]):((g:Grid)=>Grid|null)|null{
  const bg=0; const mk=(g:Grid,dy:number,dx:number):Grid|null=>{ const r=g.length,c=g[0].length; const o=blank(r,c,bg);
    for(let y=0;y<r;y++)for(let x=0;x<c;x++){ if(g[y][x]!==bg){ const ny=y+dy,nx=x+dx; if(ny<0||ny>=r||nx<0||nx>=c)return null; o[ny][nx]=g[y][x]; } } return o; };
  for(let dy=-6;dy<=6;dy++)for(let dx=-6;dx<=6;dx++){ if(dy===0&&dx===0)continue;
    if(nt.every(p=>{const o=mk(p.input,dy,dx);return o&&equalG(o,p.output);})) return (g:Grid)=>mk(g,dy,dx); }
  return null;
}
// D6: gravity — cells fall in a learned direction until packed
function induceGravity(nt:{input:Grid,output:Grid}[]):((g:Grid)=>Grid|null)|null{
  const bg=0; const grav=(g:Grid,dir:number):Grid=>{ const r=g.length,c=g[0].length; const o=blank(r,c,bg);
    if(dir<2){ for(let x=0;x<c;x++){ const col=[]; for(let y=0;y<r;y++)if(g[y][x]!==bg)col.push(g[y][x]); for(let k=0;k<col.length;k++){ const y=dir===0? r-1-k : k; o[y][x]=col[dir===0?col.length-1-k:k]; } } }
    else { for(let y=0;y<r;y++){ const row=[]; for(let x=0;x<c;x++)if(g[y][x]!==bg)row.push(g[y][x]); for(let k=0;k<row.length;k++){ const x=dir===2? c-1-k : k; o[y][x]=row[dir===2?row.length-1-k:k]; } } }
    return o; };
  for(const dir of [0,1,2,3]) if(nt.every(p=>{const o=grav(p.input,dir);return o&&equalG(o,p.output);})) return (g:Grid)=>grav(g,dir);
  return null;
}
// D7: fill enclosed holes with a learned colour
function induceHoleFill(nt:{input:Grid,output:Grid}[]):((g:Grid)=>Grid|null)|null{
  const bg=0; let C:number|undefined;
  const fill=(g:Grid,col:number):Grid|null=>{ const r=g.length,c=g[0].length; const seen=Array.from({length:r},()=>Array(c).fill(false)); const o=g.map(rr=>rr.slice());
    for(let y=0;y<r;y++)for(let x=0;x<c;x++){ if(g[y][x]!==bg||seen[y][x])continue; const reg:[number,number][]=[]; const st:[number,number][]=[[y,x]];seen[y][x]=true;let edge=false;
      while(st.length){const[cy,cx]=st.pop()!;reg.push([cy,cx]);if(cy===0||cx===0||cy===r-1||cx===c-1)edge=true;for(const[dy,dx]of[[1,0],[-1,0],[0,1],[0,-1]] as [number,number][]){const ny=cy+dy,nx=cx+dx;if(ny>=0&&ny<r&&nx>=0&&nx<c&&g[ny][nx]===bg&&!seen[ny][nx]){seen[ny][nx]=true;st.push([ny,nx]);}}}
      if(!edge)for(const[ry,rx]of reg)o[ry][rx]=col; } return o; };
  // learn colour from first pair's filled cells
  const a=nt[0]; for(let y=0;y<a.input.length;y++)for(let x=0;x<a.input[0].length;x++) if(a.input[y][x]===bg&&a.output[y]?.[x]!==bg){ C=a.output[y][x]; break; }
  if(C==null)return null; const CC=C;
  if(nt.every(p=>{const o=fill(p.input,CC);return o&&equalG(o,p.output);})) return (g:Grid)=>fill(g,CC);
  return null;
}

// D8: reflect/tile concat — output = input arranged with its mirrors (common ARC)
function induceReflect(nt:{input:Grid,output:Grid}[]):((g:Grid)=>Grid|null)|null{
  const fH=(g:Grid)=>g.map(r=>r.slice().reverse());
  const fV=(g:Grid)=>g.slice().reverse().map(r=>r.slice());
  const hcat=(a:Grid,b:Grid)=>a.map((r,i)=>r.concat(b[i]));
  const vcat=(a:Grid,b:Grid)=>a.concat(b);
  const arr:Record<string,(g:Grid)=>Grid>={
    "g|fH":(g)=>hcat(g,fH(g)), "fH|g":(g)=>hcat(fH(g),g),
    "g;fV":(g)=>vcat(g,fV(g)), "fV;g":(g)=>vcat(fV(g),g),
    "g|g":(g)=>hcat(g,g), "g;g":(g)=>vcat(g,g),
    "quadMirror":(g)=>vcat(hcat(g,fH(g)),hcat(fV(g),fV(fH(g)))),
  };
  for(const k of Object.keys(arr)){ const f=arr[k]; if(nt.every(p=>{let o:Grid|null=null;try{o=f(p.input);}catch{} return o&&equalG(o,p.output);})) return (g:Grid)=>{try{return f(g);}catch{return null;}}; }
  return null;
}
// D9: self-similar tiling (fractal) — place a copy of input where cells are non-bg
function induceFractal(nt:{input:Grid,output:Grid}[]):((g:Grid)=>Grid|null)|null{
  const bg=0; const frac=(g:Grid,invert:boolean):Grid|null=>{ const r=g.length,c=g[0].length; if(r*r*c*c>2500)return null; const o=blank(r*r,c*c,bg);
    for(let y=0;y<r;y++)for(let x=0;x<c;x++){ const on=(g[y][x]!==bg)!==invert; if(on)for(let yy=0;yy<r;yy++)for(let xx=0;xx<c;xx++)o[y*r+yy][x*c+xx]=g[yy][xx]; } return o; };
  for(const inv of [false,true]) if(nt.every(p=>{const o=frac(p.input,inv);return o&&equalG(o,p.output);})) return (g:Grid)=>frac(g,inv);
  return null;
}
// D10: per-object translation keyed to colour (position factory)
function induceMoveByColor(nt:{input:Grid,output:Grid}[]):((g:Grid)=>Grid|null)|null{
  const bg=0; const vec=new Map<number,[number,number]>();
  for(const p of nt){ if(p.input.length!==p.output.length||p.input[0].length!==p.output[0].length)return null;
    for(const o of components(p.input,bg,"blob")){ // find this object's image in output by matching shape+colour offset
      let found:[number,number]|null=null;
      for(let dy=-6;dy<=6&&!found;dy++)for(let dx=-6;dx<=6&&!found;dx++){ let ok=true;
        for(const[y,x]of o.cells){ const ny=y+dy,nx=x+dx; if(ny<0||ny>=p.output.length||nx<0||nx>=p.output[0].length||p.output[ny][nx]!==o.color){ok=false;break;} }
        if(ok)found=[dy,dx]; }
      if(!found)return null; if(vec.has(o.color)){ const v=vec.get(o.color)!; if(v[0]!==found[0]||v[1]!==found[1])return null; } else vec.set(o.color,found); } }
  if(!vec.size)return null;
  return (g:Grid)=>{ const r=g.length,c=g[0].length; const out=blank(r,c,bg);
    for(const o of components(g,bg,"blob")){ const v=vec.get(o.color); if(!v)return null; for(const[y,x]of o.cells){ const ny=y+v[0],nx=x+v[1]; if(ny<0||ny>=r||nx<0||nx>=c)return null; out[ny][nx]=g[y][x]; } } return out; };
}

// ── GENERATIVE DRAW inducers (the INK-ADD frontier; eval's #1 unsolved class, 119 tasks) ──
// D16: RAYS FROM MARKERS — each non-bg cell emits a line in a learned direction-set + colour,
// stopping at the edge or at the first obstacle. The canonical "draw" motif.
function induceRays(nt:{input:Grid,output:Grid}[]):((g:Grid)=>Grid|null)|null{
  const bg=0;
  if(!nt.every(p=>p.input.length===p.output.length&&p.input[0].length===p.output[0].length)) return null;
  const DIRSETS:[number,number][][]=[
    [[0,1],[0,-1]], [[1,0],[-1,0]], [[0,1],[0,-1],[1,0],[-1,0]],
    [[1,1],[1,-1],[-1,1],[-1,-1]], [[0,1],[0,-1],[1,0],[-1,0],[1,1],[1,-1],[-1,1],[-1,-1]],
  ];
  const pal=new Set<number>(); for(const r of nt[0].output)for(const v of r)if(v!==bg)pal.add(v);
  const colorModes:("src"|number)[]=["src",...pal];
  for(const dirs of DIRSETS) for(const cm of colorModes) for(const stop of ["edge","obstacle"] as const){
    const draw=(g:Grid):Grid=>{ const R=g.length,C=g[0].length; const o=g.map(row=>row.slice());
      for(let y=0;y<R;y++)for(let x=0;x<C;x++){ if(g[y][x]===bg)continue; const col=cm==="src"?g[y][x]:cm as number;
        for(const [dy,dx] of dirs){ let ny=y+dy,nx=x+dx;
          while(ny>=0&&ny<R&&nx>=0&&nx<C){
            if(g[ny][nx]!==bg){ if(stop==="obstacle")break; ny+=dy;nx+=dx; continue; }
            if(o[ny][nx]===bg)o[ny][nx]=col; ny+=dy;nx+=dx; } } }
      return o; };
    if(nt.every(p=>equalG(draw(p.input),p.output))) return draw;
  }
  return null;
}
// D17: CONNECT ALIGNED — fill the bg gap between consecutive same-row/col non-bg cells with a
// learned colour (optionally requiring the two endpoints share a colour). "Connect the dots."
function induceConnect(nt:{input:Grid,output:Grid}[]):((g:Grid)=>Grid|null)|null{
  const bg=0;
  if(!nt.every(p=>p.input.length===p.output.length&&p.input[0].length===p.output[0].length)) return null;
  const pal=new Set<number>(); for(const r of nt[0].output)for(const v of r)if(v!==bg)pal.add(v);
  for(const sameColor of [true,false]) for(const cm of ["src",...pal] as ("src"|number)[]) for(const axis of ["HV","H","V"] as const){
    const draw=(g:Grid):Grid=>{ const R=g.length,C=g[0].length; const o=g.map(row=>row.slice());
      const fillLine=(get:(t:number)=>number, set:(t:number,v:number)=>void, len:number)=>{
        let prev=-1, prevCol=-1;
        for(let t=0;t<len;t++){ const v=get(t); if(v!==bg){ if(prev>=0 && (!sameColor||prevCol===v) && t-prev>1){ const col=cm==="src"?v:cm as number; for(let k=prev+1;k<t;k++) set(k,col); } prev=t; prevCol=v; } } };
      if(axis==="H"||axis==="HV") for(let y=0;y<R;y++) fillLine(t=>g[y][t], (t,v)=>{o[y][t]=v;}, C);
      if(axis==="V"||axis==="HV") for(let x=0;x<C;x++) fillLine(t=>g[t][x], (t,v)=>{o[t][x]=v;}, R);
      return o; };
    if(nt.every(p=>equalG(draw(p.input),p.output))) return draw;
  }
  return null;
}

export const INDUCERS:[string,(nt:any)=>((g:Grid)=>Grid|null)|null][]=[["rankRecolor",induceRankRecolor],["shapeRecolor",induceShapeRecolor],["overlay",induceOverlay],["colorMap",induceColorMap],["shift",induceShift],["gravity",induceGravity],["holeFill",induceHoleFill],["reflect",induceReflect],["fractal",induceFractal],["moveByColor",induceMoveByColor],["scaleByFeat",induceScaleByFeat],["tileByFeat",induceTileByFeat],["shiftByFeat",induceShiftByFeat],["shear",induceShear],["objSlideByRank",induceObjSlideByRank],["rays",induceRays],["connect",induceConnect],["stamp2",induceStamp],["trace",induceTrace],["localRule",induceLocalRule],["localRuleMS",induceLocalRuleMS],["holeEncloser",induceHoleFillByEncloser],["holeRank",induceHoleFillByRank],["registerCombine",induceRegisterCombine]];

function solves(prog:(g:Grid)=>Grid|null,tr:any[]){return tr.every((p:any)=>{const o=prog(p.input);return o&&eqG(o,p.output);});}
const apply=(op:string,pr:any)=>(g:Grid)=>{try{return applyOp({name:op,params:pr} as any,g);}catch{return null;}};
export const PREFIX=OP_NAMES.filter(n=>!["mapObjects","mapTopK","fractal","colorByShape","periodicFill","overlayPanels","combinePanels","stamp"].includes(n));

// ── EXPORTED: solve one task via reconstruction (prefix × induced residual) ──

// ── DERIVATIVE (1st-order) inducers: a parameter = FUNCTION of an input feature.
// Unlike the map-learners, these EXTRAPOLATE to unseen test (compute the feature there).
function nObjF(g:Grid):number{ return components(g,0,"blob").length; }
function nColF(g:Grid):number{ const s=new Set<number>(); for(const r of g)for(const v of r)if(v!==0)s.add(v); return s.size; }
function maxObjF(g:Grid):number{ const o=components(g,0,"blob"); return o.length?Math.max(...o.map(x=>x.size)):0; }
function nonBgF(g:Grid):number{ let n=0; for(const r of g)for(const v of r)if(v!==0)n++; return n; }
const FEATS:[string,(g:Grid)=>number][]=[["obj",nObjF],["col",nColF],["maxObj",maxObjF],["nonBg",nonBgF]];
function fitLinear(xs:number[],ys:number[]):[number,number]|null{ // y=a*x+b exact over the samples
  const uniq=new Set(xs); if(uniq.size<2){ // single x: only constant works (a=0)
    if(ys.every(y=>y===ys[0])) return [0,ys[0]]; return null; }
  const x0=xs[0],y0=ys[0]; let a:number|null=null;
  for(let i=1;i<xs.length;i++){ if(xs[i]!==x0){ a=(ys[i]-y0)/(xs[i]-x0); break; } }
  if(a===null||!Number.isFinite(a)) return null; const b=y0-a*x0;
  if(xs.every((x,i)=>Math.abs(a!*x+b-ys[i])<1e-9)) return [a,b]; return null;
}
// D11: scale by feature  out = scale(in, k), k = a*feat+b
function induceScaleByFeat(nt:{input:Grid,output:Grid}[]):((g:Grid)=>Grid|null)|null{
  for(const [fn,feat] of FEATS){ const ks=nt.map(p=>p.output.length/p.input.length), kxs=nt.map(p=>p.output[0].length/p.input[0].length);
    if(ks.some((k,i)=>!Number.isInteger(k)||k!==kxs[i]||k<1)) continue;
    const lin=fitLinear(nt.map(p=>feat(p.input)),ks); if(!lin)continue; const [a,b]=lin;
    const f=(g:Grid):Grid|null=>{ const k=Math.round(a*feat(g)+b); if(k<1||g.length*k*g[0].length*k>2500)return null; const r=g.length,c=g[0].length; const o=Array.from({length:r*k},()=>Array(c*k).fill(0)); for(let y=0;y<r;y++)for(let x=0;x<c;x++)for(let dy=0;dy<k;dy++)for(let dx=0;dx<k;dx++)o[y*k+dy][x*k+dx]=g[y][x]; return o; };
    if(nt.every(p=>{const o=f(p.input);return o&&equalG(o,p.output);})) return f; }
  return null;
}
// D12: tile by feature  out = input repeated k times (h or v), k = a*feat+b
function induceTileByFeat(nt:{input:Grid,output:Grid}[]):((g:Grid)=>Grid|null)|null{
  for(const dir of [0,1]) for(const [fn,feat] of FEATS){
    const ks=nt.map(p=> dir===0? p.output[0].length/p.input[0].length : p.output.length/p.input.length);
    const same=nt.every((p,i)=> dir===0? p.output.length===p.input.length : p.output[0].length===p.input[0].length);
    if(!same||ks.some(k=>!Number.isInteger(k)||k<1)) continue;
    const lin=fitLinear(nt.map(p=>feat(p.input)),ks); if(!lin)continue; const [a,b]=lin;
    const f=(g:Grid):Grid|null=>{ const k=Math.round(a*feat(g)+b); if(k<1)return null; const r=g.length,c=g[0].length;
      if(dir===0){ if(r*c*k>2500)return null; const o=g.map(row=>{const nr=[]; for(let t=0;t<k;t++)nr.push(...row); return nr;}); return o; }
      else { if(r*k*c>2500)return null; const o:Grid=[]; for(let t=0;t<k;t++)for(const row of g)o.push(row.slice()); return o; } };
    if(nt.every(p=>{const o=f(p.input);return o&&equalG(o,p.output);})) return f; }
  return null;
}
// D13: shift by feature  content translated by (a*feat+b) in one axis
function induceShiftByFeat(nt:{input:Grid,output:Grid}[]):((g:Grid)=>Grid|null)|null{
  for(const axis of [0,1]) for(const [fn,feat] of FEATS){
    if(!nt.every(p=>p.input.length===p.output.length&&p.input[0].length===p.output[0].length)) continue;
    // measure shift per pair: find dy/dx that maps non-bg input onto output
    const shifts:number[]=[]; let ok=true;
    for(const p of nt){ let found:number|null=null;
      for(let d=-8;d<=8&&found===null;d++){ let good=true;
        for(let y=0;y<p.input.length&&good;y++)for(let x=0;x<p.input[0].length;x++){ if(p.input[y][x]!==0){ const ny=axis===0?y+d:y, nx=axis===1?x+d:x; if(ny<0||ny>=p.output.length||nx<0||nx>=p.output[0].length||p.output[ny][nx]!==p.input[y][x]){good=false;break;} } }
        if(good)found=d; }
      if(found===null){ok=false;break;} shifts.push(found); }
    if(!ok) continue; const lin=fitLinear(nt.map(p=>feat(p.input)),shifts); if(!lin)continue; const [a,b]=lin;
    const f=(g:Grid):Grid|null=>{ const d=Math.round(a*feat(g)+b); const r=g.length,c=g[0].length; const o=Array.from({length:r},()=>Array(c).fill(0));
      for(let y=0;y<r;y++)for(let x=0;x<c;x++){ if(g[y][x]!==0){ const ny=axis===0?y+d:y, nx=axis===1?x+d:x; if(ny<0||ny>=r||nx<0||nx>=c)return null; o[ny][nx]=g[y][x]; } } return o; };
    if(nt.every(p=>{const o=f(p.input);return o&&equalG(o,p.output);})) return f; }
  return null;
}

// D14: SHEET-SLIDE / SHEAR — each sheet (row or col) cyclically slides by f(index).
// "which axis slides and to where" = (axis, linear function of index). Toroidal/wrap.
function induceShear(nt:{input:Grid,output:Grid}[]):((g:Grid)=>Grid|null)|null{
  if(!nt.every(p=>p.input.length===p.output.length&&p.input[0].length===p.output[0].length)) return null;
  // axis 0 = rows slide horizontally; axis 1 = cols slide vertically
  for(const axis of [0,1]){
    // determine shift s(index) per pair; require a single linear s=a*idx+b consistent across pairs
    let A:number|null=null, Bc:number|null=null, ok=true;
    const samples:[number,number][]=[]; // (idx, shift)
    for(const p of nt){ const r=p.input.length,c=p.input[0].length; const n=axis===0?r:c; const len=axis===0?c:r;
      for(let idx=0; idx<n; idx++){
        // extract the sheet line from input & output
        const lineIn:number[]=[], lineOut:number[]=[];
        for(let t=0;t<len;t++){ if(axis===0){ lineIn.push(p.input[idx][t]); lineOut.push(p.output[idx][t]); } else { lineIn.push(p.input[t][idx]); lineOut.push(p.output[t][idx]); } }
        if(new Set(lineIn).size<2) continue; // ambiguous sheet, skip
        let s:number|null=null;
        for(let sh=0; sh<len; sh++){ let good=true; for(let t=0;t<len;t++){ if(lineIn[((t-sh)%len+len)%len]!==lineOut[t]){good=false;break;} } if(good){ s=sh; break; } }
        if(s===null){ ok=false; break; }
        samples.push([idx,s]);
      }
      if(!ok) break;
    }
    if(!ok || samples.length<2) continue;
    // fit s = a*idx + b over samples (allow mod via direct linear; require exact)
    const x0=samples[0][0],y0=samples[0][1]; let a:number|null=null;
    for(let i=1;i<samples.length;i++){ if(samples[i][0]!==x0){ a=(samples[i][1]-y0)/(samples[i][0]-x0); break; } }
    if(a===null) a=0; const b=y0-a*x0;
    if(!samples.every(([x,y])=> Math.abs(((a!*x+b)% (1e9))-y) < 1e-9 || true)) {} // keep loose; verify by apply below
    const f=(g:Grid):Grid|null=>{ const r=g.length,c=g[0].length; const o=g.map(row=>row.slice()); const n=axis===0?r:c; const len=axis===0?c:r;
      for(let idx=0; idx<n; idx++){ const sh=Math.round(a!*idx+b);
        for(let t=0;t<len;t++){ const src=((t-sh)%len+len)%len; if(axis===0) o[idx][t]=g[idx][src]; else o[t][idx]=g[src][idx]; } }
      return o; };
    if(nt.every(p=>{const o=f(p.input);return o&&equalG(o,p.output);})) return f;
  }
  return null;
}

// D15: OBJECT SLIDE-BY-RANK — each object (sorted by size desc) translates by rank*unit+base.
// The motion 1st-derivative: displacement is a linear function of object rank. Extrapolates.
function induceObjSlideByRank(nt:{input:Grid,output:Grid}[]):((g:Grid)=>Grid|null)|null{
  const bg=0;
  if(!nt.every(p=>p.input.length===p.output.length&&p.input[0].length===p.output[0].length)) return null;
  // collect (rank -> displacement) across pairs; require linear disp = rank*u + b
  const sy:[number,number][]=[], sx:[number,number][]=[];
  for(const p of nt){ const objs=components(p.input,bg,"blob").slice().sort((a,b)=>b.size-a.size);
    for(let r=0;r<objs.length;r++){ const o=objs[r]; let found:[number,number]|null=null;
      for(let dy=-8;dy<=8&&!found;dy++)for(let dx=-8;dx<=8&&!found;dx++){ let good=true;
        for(const[y,x]of o.cells){ const ny=y+dy,nx=x+dx; if(ny<0||ny>=p.output.length||nx<0||nx>=p.output[0].length||p.output[ny][nx]!==o.color){good=false;break;} } if(good)found=[dy,dx]; }
      if(!found) return null; sy.push([r,found[0]]); sx.push([r,found[1]]); } }
  const fit=(pts:[number,number][]):[number,number]|null=>{ if(pts.length<2) return pts.length?[0,pts[0][1]]:null;
    const x0=pts[0][0],y0=pts[0][1]; let a:number|null=null; for(let i=1;i<pts.length;i++){ if(pts[i][0]!==x0){ a=(pts[i][1]-y0)/(pts[i][0]-x0); break; } } if(a===null)a=0; const b=y0-a*x0;
    return pts.every(([x,y])=>Math.abs(a!*x+b-y)<1e-9)?[a,b]:null; };
  const fy=fit(sy), fx=fit(sx); if(!fy||!fx) return null;
  const f=(g:Grid):Grid|null=>{ const r=g.length,c=g[0].length; const out=blank(r,c,bg);
    const objs=components(g,bg,"blob").slice().sort((a,b)=>b.size-a.size);
    for(let rk=0;rk<objs.length;rk++){ const dy=Math.round(fy[0]*rk+fy[1]), dx=Math.round(fx[0]*rk+fx[1]);
      for(const[y,x]of objs[rk].cells){ const ny=y+dy,nx=x+dx; if(ny<0||ny>=r||nx<0||nx>=c)return null; out[ny][nx]=g[y][x]; } } return out; };
  if(nt.every(p=>{const o=f(p.input);return o&&equalG(o,p.output);})) return f;
  return null;
}

function looOK(ind:(nt:any)=>((g:Grid)=>Grid|null)|null, nt:{input:Grid,output:Grid}[]):boolean{
  if(nt.length<2) return true;
  for(let i=0;i<nt.length;i++){ const sub=nt.filter((_,j)=>j!==i); let f:any=null; try{f=ind(sub);}catch{}
    if(!f) return false; let o:Grid|null=null; try{o=f(nt[i].input);}catch{} if(!o||!eqG(o,nt[i].output)) return false; }
  return true;
}

export function solveDiscovery(train:any[], order?:string[], looGate?:boolean): {prog:(g:Grid)=>Grid|null, kind:string} | null {
  if(train.some((p:any)=>p.input.length*p.input[0].length>460)) return null;
  const pal=taskPalette(train);
  const prefixes:[string,any][]=[["identity",{}]];
  for(const op of PREFIX){ let prs:any[];try{prs=(OPS as any)[op].enumerate(pal).slice(0,2);}catch{prs=[{}];} for(const pr of prs) prefixes.push([op,pr]); }
  for(const [op,pr] of prefixes){ const a1=apply(op,pr);
    const mid=train.map((p:any)=>a1(p.input)); if(mid.some((g:Grid)=>!g))continue;
    const nt=train.map((p:any,k:number)=>({input:mid[k],output:p.output}));
    const inds = order? INDUCERS.slice().sort((a,b)=>(order.indexOf(a[0])+1||99)-(order.indexOf(b[0])+1||99)) : INDUCERS;
    for(const [iname,ind] of inds){ let resid:any=null; try{resid=ind(nt);}catch{} if(!resid)continue;
      const prog=(g:Grid)=>{const m=a1(g);return m?resid(m):null;};
      if(solves(prog,train) && (!looGate || looOK(ind,nt))) return {prog, kind:`${op}_${iname}`};
    }
  }
  return null;
}

if (require.main === module) {
  const library:any[]=[]; let net=0; const hits:string[]=[];
  for(const t of tasks){ if(combined.has(t.id)) continue;
    const r=solveDiscovery(t.train); if(!r) continue;
    const tp=t.test.every((te:any)=>{const o=r.prog(te.input);return te.output&&o&&eqG(o,te.output);});
    if(tp){ net++; hits.push(t.id+"["+r.kind+"]"); library.push({id:t.id,kind:r.kind}); } }
  fs.writeFileSync(path.join(__dirname,"..","discovered_library.json"),JSON.stringify(library,null,1));
  console.log("reconstruction generator NET-NEW: "+net); hits.forEach(h=>console.log("  "+h));
}
