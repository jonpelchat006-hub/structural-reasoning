// geomove_scan.ts — §50: PER-OBJECT GEOMETRY (Jonathan). §49's vortex machinery pointed at POSITION, not
// colour. Each object moves/places by a learned per-object VECTOR whose components come from the same
// spiral/octonion features (rank, size, colour, neighbour). Same-dims tasks that RELOCATE objects on a
// preserved canvas. Displacement (dy,dx) per object learned as: (i) CONSTANT (all objects shift the same),
// (ii) FUNCTION of a feature (dy = a*rank+b — the §28 lift on position), or (iii) GRAVITY-to-edge (each
// object slides to a wall/anchor — the flow direction). Learn from train, θ=1, verify on test.
import * as path from "path"; import * as fs from "fs";
import { loadTasks } from "./loader";
import { components, Obj } from "./objects";
import { taskPalette } from "./transfer";
import { rec } from "./scan_recorder";
type Grid=number[][];
const eqG=(a:Grid,b:Grid)=>!!a&&!!b&&a.length===b.length&&a[0].length===b[0].length&&a.every((r,i)=>r.every((v,j)=>v===b[i][j]));
const dimsEq=(a:Grid,b:Grid)=>a.length===b.length&&a[0].length===b[0].length;

function neighbours(objs:Obj[]):Map<Obj,Obj[]>{
  const own=new Map<string,Obj>();objs.forEach(o=>o.cells.forEach(([y,x])=>own.set(y+","+x,o)));
  const adj=new Map<Obj,Set<Obj>>();objs.forEach(o=>adj.set(o,new Set()));
  const D=[[-1,0],[1,0],[0,-1],[0,1],[-1,-1],[-1,1],[1,-1],[1,1]];
  for(const o of objs)for(const[y,x]of o.cells)for(const[dy,dx]of D){const n=own.get((y+dy)+","+(x+dx));if(n&&n!==o)(adj.get(o) as Set<Obj>).add(n);}
  const out=new Map<Obj,Obj[]>();for(const[o,s]of adj)out.set(o,Array.from(s));return out;}
type FeatFn=(o:Obj,all:Obj[],nb:Map<Obj,Obj[]>)=>number;
const FEATS:[string,FeatFn][]=[
  ["rankSizeDesc",(o,all)=>[...all].sort((a,b)=>b.size-a.size).findIndex(x=>x===o)+1],
  ["rankSizeAsc",(o,all)=>[...all].sort((a,b)=>a.size-b.size).findIndex(x=>x===o)+1],
  ["size",o=>o.size],["color",o=>o.color],
  ["nNeighbours",(o,_a,nb)=>(nb.get(o)||[]).length],
];
// place a set of objects onto a fresh bg canvas at given per-object offsets
function place(g:Grid,bg:number,objs:Obj[],off:Map<Obj,[number,number]>):Grid|null{
  const out=g.map(r=>r.map(()=>bg));const R=g.length,C=g[0].length;
  for(const o of objs){const[dy,dx]=off.get(o)||[0,0];for(const[y,x]of o.cells){const ny=y+dy,nx=x+dx;if(ny<0||ny>=R||nx<0||nx>=C)return null;out[ny][nx]=g[y][x];}}
  return out;}
// gravity offset: slide object to the wall in dir until its bbox touches edge
function gravOffset(o:Obj,R:number,C:number,dir:number):[number,number]{
  if(dir===0)return[-o.y0,0]; if(dir===1)return[R-1-o.y1,0]; if(dir===2)return[0,-o.x0]; return[0,C-1-o.x1];}

function learnMove(pairs:any[],bg:number,mode:"color"|"blob"):((g:Grid)=>Grid|null)|null{
  // gather per-object true displacement across pairs (match object by identical cell-shape+colour signature)
  const sig=(o:Obj)=>o.color+":"+o.cells.map(([y,x])=>(y-o.y0)+","+(x-o.x0)).sort().join(";");
  // CANDIDATE 1: constant shift
  // CANDIDATE 2: dy=a*feat+b, dx=c*feat+d  (functional)
  // CANDIDATE 3: gravity dir 0..3
  // Try gravity first (cheap, generalizes), then constant, then functional per feature.
  for(let dir=0;dir<4;dir++){let ok=true;
    for(const p of pairs){if(!dimsEq(p.input,p.output)){ok=false;break;}const objs=components(p.input,bg,mode);if(!objs.length){ok=false;break;}
      const off=new Map<Obj,[number,number]>();for(const o of objs)off.set(o,gravOffset(o,p.input.length,p.input[0].length,dir));
      const got=place(p.input,bg,objs,off);if(!got||!eqG(got,p.output)){ok=false;break;}}
    if(ok)return(g:Grid)=>{const objs=components(g,bg,mode);const off=new Map<Obj,[number,number]>();for(const o of objs)off.set(o,gravOffset(o,g.length,g[0].length,dir));return place(g,bg,objs,off);};}
  // constant shift: infer from first object of first pair
  {const p0=pairs[0];if(dimsEq(p0.input,p0.output)){const io=components(p0.input,bg,mode),oo=components(p0.output,bg,mode);
    if(io.length&&io.length===oo.length){const m=new Map(oo.map(o=>[sig(o),o] as [string,Obj]));const a=io[0],b=m.get(sig(a));
      if(b){const dy=b.y0-a.y0,dx=b.x0-a.x0;if(dy||dx){let ok=true;
        for(const p of pairs){if(!dimsEq(p.input,p.output)){ok=false;break;}const objs=components(p.input,bg,mode);const off=new Map<Obj,[number,number]>();objs.forEach(o=>off.set(o,[dy,dx]));const got=place(p.input,bg,objs,off);if(!got||!eqG(got,p.output)){ok=false;break;}}
        if(ok)return(g:Grid)=>{const objs=components(g,bg,mode);const off=new Map<Obj,[number,number]>();objs.forEach(o=>off.set(o,[dy,dx]));return place(g,bg,objs,off);};}}}}}
  // functional: dy,dx = linear in a feature (per-object vector from the spiral axis)
  for(const[,ff]of FEATS){const ptsY:[number,number][]=[],ptsX:[number,number][]=[];let ok=true;
    for(const p of pairs){if(!dimsEq(p.input,p.output)){ok=false;break;}const io=components(p.input,bg,mode),oo=components(p.output,bg,mode);
      if(io.length!==oo.length){ok=false;break;}const nb=neighbours(io);const m=new Map(oo.map(o=>[sig(o),o] as [string,Obj]));
      for(const o of io){const b=m.get(sig(o));if(!b){ok=false;break;}const k=ff(o,io,nb);ptsY.push([k,b.y0-o.y0]);ptsX.push([k,b.x0-o.x0]);}if(!ok)break;}
    if(!ok||ptsY.length<2)continue;
    const fit=(pts:[number,number][])=>{const ks=Array.from(new Set(pts.map(p=>p[0])));if(ks.length<2)return null;const p0=pts[0],p1=pts.find(p=>p[0]!==p0[0]);if(!p1)return null;const a=(p1[1]-p0[1])/(p1[0]-p0[0]),b=p0[1]-a*p0[0];return pts.every(([k,v])=>Math.abs(a*k+b-v)<1e-9)?[a,b] as [number,number]:null;};
    const cy=fit(ptsY),cx=fit(ptsX);if(!cy||!cx)continue;if(cy[0]===0&&cx[0]===0)continue; // must vary per object
    const g0y=cy,g0x=cx,fn=ff,BG=bg,MODE=mode;
    return(g:Grid)=>{const objs=components(g,BG,MODE),nb=neighbours(objs),off=new Map<Obj,[number,number]>();
      for(const o of objs){const k=fn(o,objs,nb);const dy=g0y[0]*k+g0y[1],dx=g0x[0]*k+g0x[1];if(Math.abs(dy-Math.round(dy))>1e-9||Math.abs(dx-Math.round(dx))>1e-9)return null;off.set(o,[Math.round(dy),Math.round(dx)]);}return place(g,BG,objs,off);};
  }
  return null;
}

const ev=loadTasks(path.join(__dirname,"..","data-eval"));
const verified=new Set(fs.readFileSync(path.join(__dirname,"..","verified_eval.txt"),"utf8").trim().split(/\s+/).flatMap(s=>s.match(/.{1,8}/g)||[]));
const STATE=process.argv[2]||null,BUDGET=+(process.argv[3]||34)*1000,T0=Date.now();
let RESUME=0,closed=0,trainOnly=0,net:string[]=[],hows:string[]=[];
if(STATE&&fs.existsSync(STATE)){const s=JSON.parse(fs.readFileSync(STATE,"utf8"));RESUME=s.next;closed=s.closed;trainOnly=s.trainOnly;net=s.net;hows=s.hows;}
const rep=()=>{console.log("\n=== §50 PER-OBJECT GEOMETRY (learned move/place vector) EVAL ===");
  console.log("closed: "+closed+"  overfit: "+trainOnly+"  NET-NEW: "+net.length+"  "+net.join(" "));for(const h of hows)console.log("  "+h);};
if(STATE&&RESUME>=ev.length){rep();process.exit(0);}
for(let i=RESUME;i<ev.length;i++){const t=ev[i];
  if(STATE&&Date.now()-T0>BUDGET){fs.writeFileSync(STATE,JSON.stringify({next:i,closed,trainOnly,net,hows}));console.log("PAUSED "+i+" net="+net.length);process.exit(0);}
  if(!t.test||t.test.some((te:any)=>!te.output))continue;
  if(verified.has(t.id))continue;
  if(!t.train.every((p:any)=>dimsEq(p.input,p.output)))continue;
  let found:((g:Grid)=>Grid|null)|null=null;
  for(const bg of [0,taskPalette(t.train)[0]]){if(found)break;for(const mode of ["blob","color"] as const){
    let g:any=null;try{g=learnMove(t.train,bg,mode);}catch{}
    if(g&&t.train.every((p:any)=>{const o=g(p.input);return o&&eqG(o,p.output);})){found=g;break;}}}
  if(!found)continue;
  if(t.test.every((te:any)=>{const o=found!(te.input);return o&&eqG(o,te.output);})){closed++;net.push(t.id);hows.push(t.id);rec("geomove",t.id,"solved");}
  else{trainOnly++;hows.push("OVERFIT "+t.id);rec("geomove",t.id,"overfit");}
  if((i+1)%40===0)process.stderr.write("["+(i+1)+"] closed="+closed+"\n");
}
if(STATE)fs.writeFileSync(STATE,JSON.stringify({next:ev.length,closed,trainOnly,net,hows}));
rep();
