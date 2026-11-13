// bidir.ts — BIDIRECTIONAL meet-in-the-middle. Program P: input->output split as
// input --A--> M --B--> output. Forward search applies ops A to the INPUT; backward
// search applies INVERSE ops to the OUTPUT (M = B^-1(output)). Where A(input)==B^-1(output)
// the two paths MEET at midpoint M, giving P=[A then B]. Reaches deep programs cheaply,
// and (Jonathan) any meeting grid is itself a midpoint others can build on.
import * as path from "path"; import * as fs from "fs";
import { loadTasks } from "./loader";
import { equal, palette, background } from "./grid";
type Grid=number[][];
const tasks=loadTasks(path.join(__dirname,"..","data-eval"));
const evalSolved=new Set(fs.readFileSync(path.join(__dirname,"..","verified_eval.txt"),"utf8").trim().split(/\s+/).filter(Boolean));
const eqG=(a:Grid,b:Grid)=>!!a&&!!b&&a.length===b.length&&a[0].length===b[0].length&&a.every((r,i)=>r.every((v,j)=>v===b[i][j]));
const key=(g:Grid)=>g.map(r=>r.join(",")).join(";");

const rot=(g:Grid)=>{const r=g.length,c=g[0].length;const o=Array.from({length:c},()=>Array(r).fill(0));for(let y=0;y<r;y++)for(let x=0;x<c;x++)o[x][r-1-y]=g[y][x];return o;};
const fH=(g:Grid)=>g.map(r=>r.slice().reverse());
const fV=(g:Grid)=>g.slice().reverse().map(r=>r.slice());
const tr=(g:Grid)=>{const r=g.length,c=g[0].length;const o=Array.from({length:c},()=>Array(r).fill(0));for(let y=0;y<r;y++)for(let x=0;x<c;x++)o[x][y]=g[y][x];return o;};
const rot2=(g:Grid)=>rot(rot(g)), rot3=(g:Grid)=>rot(rot(rot(g)));
const swap=(a:number,b:number)=>(g:Grid)=>g.map(r=>r.map(v=>v===a?b:v===b?a:v));
const scale=(k:number)=>(g:Grid):Grid|null=>{const r=g.length,c=g[0].length;if(r*k*c*k>2500)return null;const o=Array.from({length:r*k},()=>Array(c*k).fill(0));for(let y=0;y<r;y++)for(let x=0;x<c;x++)for(let dy=0;dy<k;dy++)for(let dx=0;dx<k;dx++)o[y*k+dy][x*k+dx]=g[y][x];return o;};
const downscale=(k:number)=>(g:Grid):Grid|null=>{const r=g.length,c=g[0].length;if(r%k||c%k)return null;const o=Array.from({length:r/k},()=>Array(c/k).fill(0));for(let y=0;y<r/k;y++)for(let x=0;x<c/k;x++){o[y][x]=g[y*k][x*k];}return o;};

// op with its inverse (both directions). name, fwd, inv.
type Op={name:string,fwd:(g:Grid)=>Grid|null,inv:(g:Grid)=>Grid|null};
function opSet(pal:number[]):Op[]{
  const ops:Op[]=[
    {name:"rot1",fwd:rot,inv:rot3},{name:"rot2",fwd:rot2,inv:rot2},{name:"rot3",fwd:rot3,inv:rot},
    {name:"flipH",fwd:fH,inv:fH},{name:"flipV",fwd:fV,inv:fV},{name:"transpose",fwd:tr,inv:tr},
    {name:"scale2",fwd:scale(2),inv:downscale(2)},{name:"scale3",fwd:scale(3),inv:downscale(3)},
  ];
  for(let i=0;i<pal.length;i++)for(let j=i+1;j<pal.length;j++){ const a=pal[i],b=pal[j]; ops.push({name:`swap${a}${b}`,fwd:swap(a,b),inv:swap(a,b)}); }
  return ops;
}
// expand a grid by applying fns (depth<=2), return map key->path(names)
function frontier(g:Grid, ops:Op[], dir:"fwd"|"inv"):Map<string,{grid:Grid,path:string[]}>{
  const m=new Map<string,{grid:Grid,path:string[]}>(); m.set(key(g),{grid:g,path:[]});
  let layer=[{grid:g,path:[] as string[]}];
  for(let d=0;d<2;d++){ const next:{grid:Grid,path:string[]}[]=[];
    for(const s of layer)for(const op of ops){ let o:Grid|null=null; try{o=(dir==="fwd"?op.fwd:op.inv)(s.grid);}catch{} if(!o||o.length*o[0].length>2500)continue; const k=key(o); if(m.has(k))continue;
      const e={grid:o,path:[...s.path,op.name]}; m.set(k,e); next.push(e); } layer=next; }
  return m;
}
const byName=new Map<string,Op>();
function applyProg(g:Grid, fpath:string[], bpath:string[]):Grid|null{
  let cur:Grid|null=g; for(const n of fpath){ cur=byName.get(n)!.fwd(cur!); if(!cur)return null; }
  // B = reverse of bpath, applied FORWARD (since backward applied inv to output)
  for(const n of [...bpath].reverse()){ cur=byName.get(n)!.fwd(cur!); if(!cur)return null; }
  return cur;
}
let net=0; const hits:string[]=[]; let i=0;
for(const t of tasks){ i++;
  if(evalSolved.has(t.id)) continue;
  if(t.train.some((p:any)=>p.input.length*p.input[0].length>400||p.output.length*p.output[0].length>400)) continue;
  const pal=Array.from(new Set(t.train.flatMap((p:any)=>[...palette(p.input),...palette(p.output)]))).slice(0,5);
  const ops=opSet(pal); byName.clear(); for(const op of ops)byName.set(op.name,op);
  // candidate (A,B) from pair 0 meet
  const p0=t.train[0]; const F=frontier(p0.input,ops,"fwd"); const B=frontier(p0.output,ops,"inv");
  const cands:[string[],string[]][]=[];
  for(const [k,fe] of F){ const be=B.get(k); if(be){ cands.push([fe.path,be.path]); if(cands.length>40)break; } }
  let solved=false;
  for(const [fp,bp] of cands){ if(fp.length+bp.length===0)continue;
    if(t.train.every((p:any)=>{const o=applyProg(p.input,fp,bp);return o&&eqG(o,p.output);})){
      const tp=t.test.every((te:any)=>{const o=applyProg(te.input,fp,bp);return te.output&&o&&eqG(o,te.output);});
      if(tp){ net++; hits.push(`${t.id}[${fp.join(">")}|${bp.join(">")}]`); solved=true; break; } } }
}
console.log(`\n=== BIDIRECTIONAL meet-in-the-middle (eval) ===`);
console.log(`NET-NEW over eval-${evalSolved.size}: ${net}`);
hits.forEach(h=>console.log("  "+h));
