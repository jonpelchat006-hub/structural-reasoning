// swarm_scan.ts — §18.3 the DOUBLE BOUNCE = bidirectional meet-in-the-middle, ported from Jonathan's
// swarm_protein_folding.py (Dolphin/construction forward + Shark/decomposition backward, meet in middle).
// Any solving program P = A then B. If B is invertible: A(input) = B^-1(output). So for each backward
// suffix B (Shark), transform the OUTPUTS by B^-1 and run the forward bounce (Dolphin) against them;
// where they LOCK is the meeting point. Halves depth (forward A depth 2 + backward B) -> reaches
// programs pure-forward depth-2 misses.
import * as path from "path"; import * as fs from "fs";
import { loadTasks } from "./loader";
import { bounceSearchDiag } from "./bounce_scan";
type Grid = number[][];
const eqG=(a:Grid,b:Grid)=>!!a&&!!b&&a.length===b.length&&a[0].length===b[0].length&&a.every((r,i)=>r.every((v,j)=>v===b[i][j]));
// clean invertible grid ops (the Shark's backward moves) with explicit inverses
const r90=(g:Grid):Grid=>{const R=g.length,C=g[0].length;const o=Array.from({length:C},()=>Array(R).fill(0));for(let y=0;y<R;y++)for(let x=0;x<C;x++)o[x][R-1-y]=g[y][x];return o;};
const rN=(g:Grid,k:number)=>{let c=g;for(let i=0;i<((k%4)+4)%4;i++)c=r90(c);return c;};
const fH=(g:Grid)=>g.map(r=>r.slice().reverse());
const fV=(g:Grid)=>g.slice().reverse();
const tr=(g:Grid):Grid=>{const R=g.length,C=g[0].length;const o=Array.from({length:C},()=>Array(R).fill(0));for(let y=0;y<R;y++)for(let x=0;x<C;x++)o[x][y]=g[y][x];return o;};
const aTr=(g:Grid)=>fH(fV(tr(g)));
const shift=(g:Grid,dy:number,dx:number):Grid=>{const R=g.length,C=g[0].length;const o=Array.from({length:R},()=>Array(C).fill(0));for(let y=0;y<R;y++)for(let x=0;x<C;x++){const ny=y+dy,nx=x+dx;if(ny>=0&&ny<R&&nx>=0&&nx<C)o[ny][nx]=g[y][x];}return o;};
const swap=(g:Grid,a:number,b:number)=>g.map(r=>r.map(v=>v===a?b:v===b?a:v));
// B (forward apply) and Binv (backward apply on output)
type Sym={name:string; B:(g:Grid)=>Grid; Binv:(g:Grid)=>Grid};
function syms(pal:number[]):Sym[]{
  const S:Sym[]=[
    {name:"id",B:g=>g,Binv:g=>g},
    {name:"r1",B:g=>rN(g,1),Binv:g=>rN(g,3)},{name:"r2",B:g=>rN(g,2),Binv:g=>rN(g,2)},{name:"r3",B:g=>rN(g,3),Binv:g=>rN(g,1)},
    {name:"fH",B:fH,Binv:fH},{name:"fV",B:fV,Binv:fV},{name:"tr",B:tr,Binv:tr},{name:"aTr",B:aTr,Binv:aTr},
  ];
  // (shifts/swaps disabled for fast D4-only first pass)

  return S;
}

const ev = loadTasks(path.join(__dirname,"..","data-eval"));
const verified = new Set(fs.readFileSync(path.join(__dirname,"..","verified_eval.txt"),"utf8").trim().split(/\s+/));
const START=+(process.argv[2]||0), END=+(process.argv[3]||ev.length);
let fwd=0, bi=0, net:string[]=[];
for(let i=START;i<Math.min(END,ev.length);i++){ const t=ev[i];
  if(!t.test||t.test.some((te:any)=>!te.output)) continue;
  const pal=[...new Set(t.train.flatMap((p:any)=>[...p.input.flat(),...p.output.flat()]))].filter((c:any)=>c!==0).slice(0,6) as number[];
  let fwdProg:((g:Grid)=>Grid|null)|null=null, biProg:((g:Grid)=>Grid|null)|null=null, biName="";
  for(const s of syms(pal)){
    const nt=t.train.map((p:any)=>({input:p.input, output:s.Binv(p.output)}));
    let r:any=null; try{r=bounceSearchDiag(nt,2,24);}catch{}
    if(!r||!r.prog) continue;
    const A=r.prog; const full=(g:Grid)=>{const a=A(g);return a?s.B(a):null;};
    if(t.train.every((p:any)=>{const o=full(p.input);return o&&eqG(o,p.output);})){
      if(s.name==="id"){ fwdProg=full; break; }        // forward baseline: stop, it is the cheapest
      else if(!biProg){ biProg=full; biName=s.name; }   // first backward suffix that locks
    }
  }
  if(fwdProg && t.test.every((te:any)=>{const o=fwdProg!(te.input);return o&&eqG(o,te.output);})) fwd++;
  else if(!fwdProg && biProg && t.test.every((te:any)=>{const o=biProg!(te.input);return o&&eqG(o,te.output);})){ bi++; if(!verified.has(t.id)) net.push(t.id+"["+biName+"]"); }
  if((i+1)%40===0) process.stderr.write(`[${i+1}] fwd=${fwd} bi=${bi}\n`);
}
console.log("\n=== §18.3 SWARM (bidirectional meet-in-the-middle) EVAL ["+START+","+END+") ===");
console.log("forward-only (Dolphin, B=id) solved: "+fwd);
console.log("solved ONLY via backward suffix (Shark meets Dolphin): "+bi+"   net-new: "+net.length+"  "+net.join(" "));
