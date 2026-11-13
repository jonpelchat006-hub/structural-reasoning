// vortex_scan.ts — §49: THE VORTEX / OCTONION PER-OBJECT FUNCTION (Jonathan). §48 read INTRINSIC features
// as a TABLE (memorized, overfit on unseen keys). Two lifts from Jonathan's octonion picture:
//   (A) FUNCTIONAL rank — colour = a*feature + b (integer, >=2 distinct), EXTRAPOLATES (the §28 lift).
//   (B) RELATIONAL / vortex — each slot points to the slots next to it: colour keyed on NEIGHBOURS
//       (touch-colour, neighbour count). Flow at an angle can't go straight back or cancel the anti-
//       diagonal, so of 8 terms (self+7 dirs) 2 drop — the octonion's hidden dims (Fano, inner shell).
import * as path from "path"; import * as fs from "fs";
import { loadTasks } from "./loader";
import { components, Obj } from "./objects";
import { taskPalette } from "./transfer";
import { rec } from "./scan_recorder";
type Grid=number[][];
const eqG=(a:Grid,b:Grid)=>!!a&&!!b&&a.length===b.length&&a[0].length===b[0].length&&a.every((r,i)=>r.every((v,j)=>v===b[i][j]));
const dimsEq=(a:Grid,b:Grid)=>a.length===b.length&&a[0].length===b[0].length;

function neighbours(objs:Obj[],g:Grid):Map<Obj,Obj[]>{
  const own=new Map<string,Obj>();objs.forEach(o=>o.cells.forEach(([y,x])=>own.set(y+","+x,o)));
  const adj=new Map<Obj,Set<Obj>>();objs.forEach(o=>adj.set(o,new Set()));
  const D=[[-1,0],[1,0],[0,-1],[0,1],[-1,-1],[-1,1],[1,-1],[1,1]];
  for(const o of objs)for(const[y,x]of o.cells)for(const[dy,dx]of D){const k=(y+dy)+","+(x+dx);const n=own.get(k);if(n&&n!==o)(adj.get(o) as Set<Obj>).add(n);}
  const out=new Map<Obj,Obj[]>();for(const[o,s]of adj)out.set(o,Array.from(s));return out;}

type FeatFn=(o:Obj,all:Obj[],g:Grid,nb:Map<Obj,Obj[]>)=>number;
const FEATS:[string,FeatFn][]=[
  ["size",o=>o.size],
  ["rankSizeDesc",(o,all)=>[...all].sort((a,b)=>b.size-a.size).findIndex(x=>x===o)+1],
  ["rankSizeAsc",(o,all)=>[...all].sort((a,b)=>a.size-b.size).findIndex(x=>x===o)+1],
  ["color",o=>o.color],
  ["nNeighbours",(o,_a,_g,nb)=>(nb.get(o)||[]).length],
  ["touchColor",(o,_a,_g,nb)=>{const ns=(nb.get(o)||[]);const cs=Array.from(new Set(ns.map(n=>n.color)));return cs.length===1?cs[0]:-1;}],
  ["rankInNeighbourhood",(o,_a,_g,nb)=>{const grp=[o,...(nb.get(o)||[])];return grp.sort((a,b)=>b.size-a.size).findIndex(x=>x===o)+1;}],
];

function learn(pairs:any[],bg:number,mode:"color"|"blob",f:FeatFn,kind:"table"|"linear"):((g:Grid)=>Grid|null)|null{
  const pts:[number,number][]=[];const table=new Map<number,number>();
  for(const p of pairs){if(!dimsEq(p.input,p.output))return null;
    const objs=components(p.input,bg,mode);if(!objs.length)return null;const nb=neighbours(objs,p.input);
    for(const o of objs){const cols=new Set(o.cells.map(([y,x])=>p.output[y][x]));if(cols.size!==1)return null;
      const k=f(o,objs,p.input,nb),v=Array.from(cols)[0];if(k<0)return null;pts.push([k,v]);
      if(table.has(k)){if(table.get(k)!==v)return null;}else table.set(k,v);}}
  if(kind==="linear"){
    const ks=Array.from(new Set(pts.map(p=>p[0])));if(ks.length<2)return null;
    const p0=pts[0],p1=pts.find(p=>p[0]!==p0[0]);if(!p1)return null;
    const a=(p1[1]-p0[1])/(p1[0]-p0[0]),b=p0[1]-a*p0[0];if(a===0)return null;
    if(!pts.every(([k,v])=>Math.abs(a*k+b-v)<1e-9))return null;
    return(g:Grid)=>{const objs=components(g,bg,mode),nb=neighbours(objs,g),out=g.map(r=>r.slice());
      for(const o of objs){const k=f(o,objs,g,nb);const val=a*k+b;if(Math.abs(val-Math.round(val))>1e-9)return null;
        for(const[y,x]of o.cells)out[y][x]=Math.round(val);}return out;};
  }
  return(g:Grid)=>{const objs=components(g,bg,mode),nb=neighbours(objs,g),out=g.map(r=>r.slice());
    for(const o of objs){const k=f(o,objs,g,nb);const v=table.get(k);if(v===undefined)return null;
      for(const[y,x]of o.cells)out[y][x]=v;}return out;};
}

const ev=loadTasks(path.join(__dirname,"..","data-eval"));
const verified=new Set(fs.readFileSync(path.join(__dirname,"..","verified_eval.txt"),"utf8").trim().split(/\s+/).flatMap(s=>s.match(/.{1,8}/g)||[]));
const STATE=process.argv[2]||null,BUDGET=+(process.argv[3]||34)*1000,T0=Date.now();
let RESUME=0,closed=0,trainOnly=0,net:string[]=[],hows:string[]=[];
if(STATE&&fs.existsSync(STATE)){const s=JSON.parse(fs.readFileSync(STATE,"utf8"));RESUME=s.next;closed=s.closed;trainOnly=s.trainOnly;net=s.net;hows=s.hows;}
const rep=()=>{console.log("\n=== §49 VORTEX (functional + relational per-object map) EVAL ===");
  console.log("closed: "+closed+"  overfit: "+trainOnly+"  NET-NEW: "+net.length+"  "+net.join(" "));for(const h of hows)console.log("  "+h);};
if(STATE&&RESUME>=ev.length){rep();process.exit(0);}
const RELATIONAL=new Set(["nNeighbours","touchColor","rankInNeighbourhood"]);
const passes:((fn:string,kind:string)=>boolean)[]=[
  (_fn,kind)=>kind==="linear",
  (fn,kind)=>kind==="table"&&RELATIONAL.has(fn),
  (fn,kind)=>kind==="table"&&!RELATIONAL.has(fn),
];
for(let i=RESUME;i<ev.length;i++){const t=ev[i];
  if(STATE&&Date.now()-T0>BUDGET){fs.writeFileSync(STATE,JSON.stringify({next:i,closed,trainOnly,net,hows}));console.log("PAUSED "+i+" net="+net.length);process.exit(0);}
  if(!t.test||t.test.some((te:any)=>!te.output))continue;
  if(verified.has(t.id))continue;
  if(!t.train.every((p:any)=>dimsEq(p.input,p.output)))continue;
  let found:((g:Grid)=>Grid|null)|null=null,lab="";
  outer: for(const pass of passes)for(const bg of [0,taskPalette(t.train)[0]])for(const mode of ["blob","color"] as const)
    for(const[fn,ff]of FEATS)for(const kind of ["linear","table"] as const){
      if(!pass(fn,kind))continue;
      let g:any=null;try{g=learn(t.train,bg,mode,ff,kind);}catch{}
      if(!g)continue;if(!t.train.every((p:any)=>{const o=g(p.input);return o&&eqG(o,p.output);}))continue;
      found=g;lab=fn+"/"+kind+"/"+mode+"/bg"+bg;break outer;}
  if(!found)continue;
  if(t.test.every((te:any)=>{const o=found!(te.input);return o&&eqG(o,te.output);})){closed++;net.push(t.id);hows.push(t.id+" = "+lab);rec("vortex",t.id,"solved",lab);}
  else{trainOnly++;hows.push("OVERFIT "+t.id+" ["+lab+"]");rec("vortex",t.id,"overfit",lab);}
  if((i+1)%40===0)process.stderr.write("["+(i+1)+"] closed="+closed+"\n");
}
if(STATE)fs.writeFileSync(STATE,JSON.stringify({next:ev.length,closed,trainOnly,net,hows}));
rep();
