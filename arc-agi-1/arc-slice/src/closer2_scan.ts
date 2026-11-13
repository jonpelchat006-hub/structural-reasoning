// closer2_scan.ts — §18.10 the CLOSURE-EQUATION CLOSER, with the §18.11–18.13 refinements.
// An OBSERVER at the near-miss anchor sees each cell as ONE SIDE of a closure equation; the NEIGHBOR
// atom(s) along learned direction(s) are the OTHER side; a learned map (cell, n1, n2) → value is the
// closure. Refinements applied:
//   §18.11 — fire SELECTIVELY at mesh points (only keys the map learned; everything else stays LOCKED),
//            and require the map not to damage already-correct cells (the perpendicular axes stay pinned).
//   §18.12/18.13 — TWO PATHS / TWO RAYS: each residual cell is determined by a PAIR of directional
//            approaches (two rays from two anchors); the key carries both, so the fill lives at their
//            INTERSECTION. Single-ray (d1==d2) kept as the degenerate case.
//   §18.10 — the map must DEPEND ON THE NEIGHBOUR (the neighbour determines, not duplicates); runs
//            ANCHORED (fix the near-miss residual) and STANDALONE (pure interaction, pre = identity).
// Neighbor modes: "adj" = the adjacent atom on side d; "ray" = first non-bg atom cast along d (§18.13 ray).
// Resumable: argv = START END [stateFile] [budgetSec] — saves state and exits at budget; rerun to resume.
import * as path from "path"; import * as fs from "fs";
import { loadTasks } from "./loader";
import { applyOp } from "./dsl";
import { bounceSearchDiag } from "./bounce_scan";
import { rec } from "./scan_recorder";
type Grid = number[][];
const eqG=(a:Grid,b:Grid)=>!!a&&!!b&&a.length===b.length&&a[0].length===b[0].length&&a.every((r,i)=>r.every((v,j)=>v===b[i][j]));
const build=(prog:[string,any][])=>(g:Grid)=>{let c:Grid|null=g;for(const[o,p]of prog){if(!c)return null;try{c=applyOp({name:o,params:p} as any,c);}catch{return null;}}return c;};

const DIRS:[number,number][]=[[-1,0],[1,0],[0,1],[0,-1],[-1,1],[-1,-1],[1,1],[1,-1]]; // N S E W NE NW SE SW
const adjAt=(g:Grid,y:number,x:number,d:number)=>{const[dy,dx]=DIRS[d],ny=y+dy,nx=x+dx;return(ny<0||ny>=g.length||nx<0||nx>=g[0].length)?-1:g[ny][nx];};
const rayAt=(g:Grid,y:number,x:number,d:number)=>{const[dy,dx]=DIRS[d];let ny=y+dy,nx=x+dx;while(ny>=0&&ny<g.length&&nx>=0&&nx<g[0].length){if(g[ny][nx]!==0)return g[ny][nx];ny+=dy;nx+=dx;}return 0;};

function learnClosure(aligned:Grid[], outs:Grid[], d1:number, d2:number, nb:(g:Grid,y:number,x:number,d:number)=>number): Map<string,number>|null {
  const M=new Map<string,number>();
  for(let i=0;i<aligned.length;i++){const a=aligned[i],o=outs[i];
    for(let y=0;y<a.length;y++)for(let x=0;x<a[0].length;x++){
      if(a[y][x]===o[y][x])continue;
      const k=a[y][x]+"|"+nb(a,y,x,d1)+"|"+nb(a,y,x,d2);
      const prev=M.get(k); if(prev!==undefined&&prev!==o[y][x])return null;
      M.set(k,o[y][x]);
    }}
  if(!M.size)return null;
  for(let i=0;i<aligned.length;i++){const a=aligned[i],o=outs[i];
    for(let y=0;y<a.length;y++)for(let x=0;x<a[0].length;x++){
      if(a[y][x]!==o[y][x])continue;
      const k=a[y][x]+"|"+nb(a,y,x,d1)+"|"+nb(a,y,x,d2);
      const v=M.get(k); if(v!==undefined&&v!==o[y][x])return null;
    }}
  const byCell=new Map<string,Set<number>>();
  for(const[k,v]of M){const c=k.split("|")[0];if(!byCell.has(c))byCell.set(c,new Set());byCell.get(c)!.add(v);}
  if(![...byCell.values()].some(s=>s.size>1))return null;
  return M;
}
const applyClosure=(M:Map<string,number>,d1:number,d2:number,nb:(g:Grid,y:number,x:number,d:number)=>number)=>(g:Grid):Grid=>{
  const o=g.map(r=>r.slice());
  for(let y=0;y<g.length;y++)for(let x=0;x<g[0].length;x++){
    const v=M.get(g[y][x]+"|"+nb(g,y,x,d1)+"|"+nb(g,y,x,d2)); if(v!==undefined)o[y][x]=v; }
  return o;
};

const ev=loadTasks(path.join(__dirname,"..","data-eval"));
const verified=new Set(fs.readFileSync(path.join(__dirname,"..","verified_eval.txt"),"utf8").trim().split(/\s+/));
const START=+(process.argv[2]||0), END=+(process.argv[3]||ev.length);
const STATE=process.argv[4]||null, BUDGET=+(process.argv[5]||34)*1000, T0=Date.now();
const NBMODES:[string,(g:Grid,y:number,x:number,d:number)=>number][]=[["adj",adjAt],["ray",rayAt]];
let base=0, closed=0, trainOnly=0, net:string[]=[], RESUME=START;
if(STATE&&fs.existsSync(STATE)){const s=JSON.parse(fs.readFileSync(STATE,"utf8"));base=s.base;closed=s.closed;trainOnly=s.trainOnly;net=s.net;RESUME=s.next;}
if(STATE&&RESUME>=Math.min(END,ev.length)){console.log("DONE base="+base+" closed="+closed+" trainOnly="+trainOnly+" net="+net.length+" "+net.join(" "));process.exit(0);}
for(let i=RESUME;i<Math.min(END,ev.length);i++){ const t=ev[i];
  if(STATE&&Date.now()-T0>BUDGET){fs.writeFileSync(STATE,JSON.stringify({next:i,base,closed,trainOnly,net}));console.log("PAUSED at "+i+" base="+base+" closed="+closed+" trainOnly="+trainOnly+" net="+net.length);process.exit(0);}
  if(!t.test||t.test.some((te:any)=>!te.output))continue;
  let r:any=null; try{r=bounceSearchDiag(t.train,3,30);}catch{}
  if(!r)continue;
  if(r.prog&&t.test.every((te:any)=>{const o=r.prog(te.input);return o&&eqG(o,te.output);})){base++;rec("closer2",t.id,"solved");continue;}
  const pres:[string,(g:Grid)=>Grid|null][]=[["id",(g:Grid)=>g]];
  if(r.bestProg)pres.unshift(["anchor",build(r.bestProg as [string,any][])]);
  let win:((g:Grid)=>Grid|null)|null=null, how="";
  for(const[pnm,pre]of pres){ if(win)break;
    const aligned:Grid[]=[]; let ok=true;
    for(const p of t.train){const a=pre(p.input);if(!a||a.length!==p.output.length||a[0].length!==p.output[0].length){ok=false;break;}aligned.push(a);}
    if(!ok)continue;
    const outs=t.train.map((p:any)=>p.output);
    if(aligned.every((a,j)=>eqG(a,outs[j])))continue;
    for(const[mnm,nb]of NBMODES){ if(win)break;
      for(let d1=0;d1<8&&!win;d1++)for(let d2=d1;d2<8&&!win;d2++){
        const M=learnClosure(aligned,outs,d1,d2,nb); if(!M)continue;
        const C=applyClosure(M,d1,d2,nb);
        const cand=(g:Grid)=>{const a=pre(g);return a?C(a):null;};
        if(!t.train.every((p:any)=>{const o=cand(p.input);return o&&eqG(o,p.output);}))continue;
        win=cand; how=pnm+"+"+mnm+"["+d1+","+d2+"]";
      }}}
  if(win){ if(t.test.every((te:any)=>{const o=win(te.input);return o&&eqG(o,te.output);})){ closed++; rec("closer2",t.id,"solved",how); if(!verified.has(t.id))net.push(t.id+"("+how+")"); }
    else { trainOnly++; rec("closer2",t.id,"overfit"); } }
  if((i+1)%20===0)process.stderr.write("["+(i+1)+"] base="+base+" closed="+closed+" trainOnly="+trainOnly+"\n");
}
if(STATE)fs.writeFileSync(STATE,JSON.stringify({next:Math.min(END,ev.length),base,closed,trainOnly,net}));
console.log("\n=== §18.10-18.13 CLOSER2 (closure-equation, two-ray intersection, mesh-locked) EVAL ["+START+","+END+") ===");
console.log("base forward solved: "+base);
console.log("closed by closure map: "+closed+"   train-closed-but-test-failed: "+trainOnly);
console.l