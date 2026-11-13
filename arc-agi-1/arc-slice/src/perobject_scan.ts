// perobject_scan.ts — §48: THE PER-OBJECT MAP via the SPIRAL WINDOW (Jonathan). The one lever five
// directions converged on (§47.1). We are a window spiralling the boundary; at each position a different
// AXIS is live (the pools switching), and reading it off gives a per-object feature: size = grid cells the
// object fills, rank = how far up the spiral, plus position/shape/colour. The learned map keys on THESE
// (not a global table), and is stored as a FUNCTION so it extrapolates (the ℓ≠0 orbital / functional
// paintRank). Same-dims recolour tasks: recolour each object's cells by value = map(feature(object)).
import * as path from "path"; import * as fs from "fs";
import { loadTasks } from "./loader";
import { components, Obj } from "./objects";
import { taskPalette } from "./transfer";
import { rec } from "./scan_recorder";
type Grid=number[][];
const eqG=(a:Grid,b:Grid)=>!!a&&!!b&&a.length===b.length&&a[0].length===b[0].length&&a.every((r,i)=>r.every((v,j)=>v===b[i][j]));
const dimsEq=(a:Grid,b:Grid)=>a.length===b.length&&a[0].length===b[0].length;

// ── the spiral axes: per-object features the rotating window reads off ──
type Feat=[string,(o:Obj,all:Obj[],g:Grid)=>number];
const holes=(o:Obj,g:Grid,bg:number)=>{const H=o.y1-o.y0+1,W=o.x1-o.x0+1;const inb=new Set(o.cells.map(([y,x])=>y+","+x));
  let h=0;for(let y=o.y0;y<=o.y1;y++)for(let x=o.x0;x<=o.x1;x++)if(!inb.has(y+","+x)&&g[y][x]===bg)h++;return h;};
const FEATS:Feat[]=[
  ["size",o=>o.size],
  ["rankSizeDesc",(o,all)=>[...all].sort((a,b)=>b.size-a.size).findIndex(x=>x===o)+1],
  ["rankSizeAsc",(o,all)=>[...all].sort((a,b)=>a.size-b.size).findIndex(x=>x===o)+1],
  ["color",o=>o.color],
  ["w",o=>o.x1-o.x0+1],["h",o=>o.y1-o.y0+1],
  ["nCells",o=>o.size],
  ["spiralRank",(o,all)=>[...all].sort((a,b)=>(a.y0-b.y0)||(a.x0-b.x0)).findIndex(x=>x===o)+1], // reading order up the spiral
  ["holesRank",(o,all,g)=>[...all].sort((a,b)=>holes(b,g,0)-holes(a,g,0)).findIndex(x=>x===o)+1],
];

// learn map feature->color, consistent across pairs; store as TABLE (generalizes if key recurs) and verify
function learnPerObject(pairs:any[],bg:number,mode:"color"|"blob",feat:Feat):((g:Grid)=>Grid|null)|null{
  const map=new Map<number,number>();
  for(const p of pairs){if(!dimsEq(p.input,p.output))return null;
    const objs=components(p.input,bg,mode);if(!objs.length)return null;
    for(const o of objs){const outCols=new Set(o.cells.map(([y,x])=>p.output[y][x]));if(outCols.size!==1)return null; // must recolour whole object
      const k=feat[1](o,objs,p.input),v=[...outCols][0];
      if(map.has(k)){if(map.get(k)!==v)return null;}else map.set(k,v);}
    // every non-bg output cell must belong to an object (no ink added elsewhere)
  }
  let nonId=false;for(const[k,v]of map)if(k!==v)nonId=true; // heuristic: some change
  if(map.size<1)return null;
  const fn=(g:Grid):Grid|null=>{const objs=components(g,bg,mode);const out=g.map(r=>r.slice());
    for(const o of objs){const k=feat[1](o,objs,g);const v=map.get(k);if(v===undefined)return null; // unseen key -> abstain (honest)
      for(const[y,x]of o.cells)out[y][x]=v;}return out;};
  return fn;
}

const ev=loadTasks(path.join(__dirname,"..","data-eval"));
const verified=new Set(fs.readFileSync(path.join(__dirname,"..","verified_eval.txt"),"utf8").trim().split(/\s+/).flatMap(s=>s.match(/.{1,8}/g)||[]));
const src=process.argv[2]==="train"?loadTasks(path.join(__dirname,"..","data")):ev;
const STATE=process.argv[3]||null,BUDGET=+(process.argv[4]||34)*1000,T0=Date.now();
let RESUME=0,closed=0,trainOnly=0,net:string[]=[],hows:string[]=[];
if(STATE&&fs.existsSync(STATE)){const s=JSON.parse(fs.readFileSync(STATE,"utf8"));RESUME=s.next;closed=s.closed;trainOnly=s.trainOnly;net=s.net;hows=s.hows;}
const rep=()=>{console.log("\n=== §48 PER-OBJECT MAP (spiral-window features -> learned recolour) "+(process.argv[2]||"eval")+" ===");
  console.log("closed: "+closed+"  overfit: "+trainOnly+"  NET-NEW: "+net.length+"  "+net.join(" "));for(const h of hows)console.log("  "+h);};
if(STATE&&RESUME>=src.length){rep();process.exit(0);}
for(let i=RESUME;i<src.length;i++){const t=src[i];
  if(STATE&&Date.now()-T0>BUDGET){fs.writeFileSync(STATE,JSON.stringify({next:i,closed,trainOnly,net,hows}));console.log("PAUSED "+i+" net="+net.length);process.exit(0);}
  if(!t.test||t.test.some((te:any)=>!te.output))continue;
  if(verified.has(t.id))continue;
  if(!t.train.every((p:any)=>dimsEq(p.input,p.output)))continue; // recolour tasks only
  let found:((g:Grid)=>Grid|null)|null=null,lab="";
  for(const bg of [0,taskPalette(t.train)[0]]){if(found)break;
    for(const mode of ["blob","color"] as const){if(found)break;
      for(const f of FEATS){let fn:any=null;try{fn=learnPerObject(t.train,bg,mode,f);}catch{}
        if(!fn)continue;if(!t.train.every((p:any)=>{const o=fn(p.input);return o&&eqG(o,p.output);}))continue;
        found=fn;lab=f[0]+"/"+mode+"/bg"+bg;break;}}}
  if(!found)continue;
  if(t.test.every((te:any)=>{const o=found!(te.input);return o&&eqG(o,te.output);})){closed++;net.push(t.id);hows.push(t.id+" = perObj["+lab+"]");rec("perobj",t.id,"solved",lab);}
  else{trainOnly++;hows.push("OVERFIT "+t.id+" ["+lab+"]");rec("perobj",t.id,"overfit",lab);}
  if((i+1)%40===0)process.stderr.write("["+(i+1)+"] closed="+closed+"\n");
}
if(STATE)fs.writeFileSync(STATE,JSON.stringify({next:src.length,closed,trainOnly,net,hows}));
rep();
