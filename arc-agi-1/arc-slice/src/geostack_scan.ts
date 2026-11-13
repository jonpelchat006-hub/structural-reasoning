// geostack_scan.ts — §51: THE MINIMAL RING — coupled object motion by dependency ORDER (Jonathan). §50's
// independent per-object vector failed because motion is INTERACTION: objects stack against EACH OTHER,
// not each to a wall. The "ring connecting all branches" (all-to-all = the LLM boundary) has a minimal,
// model-free form: process objects in dependency order along the flow, each settling against those ALREADY
// placed (the ring = each object connects to the settled set). This is the coupled solve §50.3 named,
// built without an LLM — the smallest thing that supplies the global coupling the sparse interior can't.
import * as path from "path"; import * as fs from "fs";
import { loadTasks } from "./loader";
import { components, Obj } from "./objects";
import { taskPalette } from "./transfer";
import { rec } from "./scan_recorder";
type Grid=number[][];
const eqG=(a:Grid,b:Grid)=>!!a&&!!b&&a.length===b.length&&a[0].length===b[0].length&&a.every((r,i)=>r.every((v,j)=>v===b[i][j]));
const dimsEq=(a:Grid,b:Grid)=>a.length===b.length&&a[0].length===b[0].length;

// drop object o by (dy,dx) step until it would collide with occupied cells or leave the grid; place it.
function settle(occ:boolean[][],cells:[number,number][],dir:number):[number,number]|null{
  const [dy,dx]=[[1,0],[-1,0],[0,1],[0,-1]][dir]; const R=occ.length,C=occ[0].length;
  let off=0;
  while(true){const noff=off+1;let ok=true;
    for(const[y,x]of cells){const ny=y+dy*noff,nx=x+dx*noff;
      if(ny<0||ny>=R||nx<0||nx>=C){ok=false;break;}
      // collides only with cells NOT belonging to this same object at this offset
      if(occ[ny][nx]){ok=false;break;}}
    if(!ok)break; off=noff;
    // mark tentative? we re-check fresh each step against static occ (settled objects only)
    // ensure the object's own footprint at 'off' doesn't self-block via occ (occ excludes self)
  }
  return [dy*off,dx*off];
}
// cumulative object gravity: sort objects by leading edge in dir (furthest-first settles first)
function stackGravity(g:Grid,bg:number,mode:"color"|"blob",dir:number):Grid|null{
  const objs=components(g,bg,mode);if(!objs.length)return null;
  const R=g.length,C=g[0].length;const occ=Array.from({length:R},()=>Array(C).fill(false));
  const out=g.map(r=>r.map(()=>bg));
  const [dy,dx]=[[1,0],[-1,0],[0,1],[0,-1]][dir];
  // order: objects furthest along +dir settle first (leading edge)
  const key=(o:Obj)=>dir===0?-o.y1:dir===1?o.y0:dir===2?-o.x1:o.x0;
  const order=[...objs].sort((a,b)=>key(a)-key(b));
  for(const o of order){const mv=settle(occ,o.cells,dir);if(!mv)return null;const[oy,ox]=mv;
    for(const[y,x]of o.cells){const ny=y+oy,nx=x+ox;if(ny<0||ny>=R||nx<0||nx>=C)return null;occ[ny][nx]=true;out[ny][nx]=g[y][x];}}
  return out;
}

const ev=loadTasks(path.join(__dirname,"..","data-eval"));
const verified=new Set(fs.readFileSync(path.join(__dirname,"..","verified_eval.txt"),"utf8").trim().split(/\s+/).flatMap(s=>s.match(/.{1,8}/g)||[]));
const SRC=process.argv[2]==="train"?loadTasks(path.join(__dirname,"..","data")):ev;
const STATE=process.argv[3]||null,BUDGET=+(process.argv[4]||34)*1000,T0=Date.now();
let RESUME=0,closed=0,trainOnly=0,net:string[]=[],hows:string[]=[];
if(STATE&&fs.existsSync(STATE)){const s=JSON.parse(fs.readFileSync(STATE,"utf8"));RESUME=s.next;closed=s.closed;trainOnly=s.trainOnly;net=s.net;hows=s.hows;}
const rep=()=>{console.log("\n=== §51 STACK-GRAVITY (coupled object motion, dependency order) "+(process.argv[2]||"eval")+" ===");
  console.log("closed: "+closed+"  overfit: "+trainOnly+"  NET-NEW: "+net.length+"  "+net.join(" "));for(const h of hows)console.log("  "+h);};
if(STATE&&RESUME>=SRC.length){rep();process.exit(0);}
for(let i=RESUME;i<SRC.length;i++){const t=SRC[i];
  if(STATE&&Date.now()-T0>BUDGET){fs.writeFileSync(STATE,JSON.stringify({next:i,closed,trainOnly,net,hows}));console.log("PAUSED "+i+" net="+net.length);process.exit(0);}
  if(!t.test||t.test.some((te:any)=>!te.output))continue;
  if(process.argv[2]!=="train"&&verified.has(t.id))continue;
  if(!t.train.every((p:any)=>dimsEq(p.input,p.output)))continue;
  let found:{bg:number;mode:"color"|"blob";dir:number}|null=null;
  for(const bg of [0,taskPalette(t.train)[0]]){if(found)break;for(const mode of ["blob","color"] as const){if(found)break;for(let dir=0;dir<4;dir++){
    let ok=true;for(const p of t.train){let r:Grid|null=null;try{r=stackGravity(p.input,bg,mode,dir);}catch{}if(!r||!eqG(r,p.output)){ok=false;break;}}
    if(ok){found={bg,mode,dir};break;}}}}
  if(!found)continue;const f=found;
  if(t.test.every((te:any)=>{let o:Grid|null=null;try{o=stackGravity(te.input,f.bg,f.mode,f.dir);}catch{}return o&&eqG(o,te.output);})){closed++;net.push(t.id);hows.push(t.id+" dir"+f.dir+"/"+f.mode+"/bg"+f.bg);rec("geostack",t.id,"solved");}
  else{trainOnly++;hows.push("OVERFIT "+t.id);rec("geostack",t.id,"overfit");}
}
if(STATE)fs.writeFileSync(STATE,JSON.stringify({next:SRC.length,closed,trainOnly,net,hows}));
rep();
