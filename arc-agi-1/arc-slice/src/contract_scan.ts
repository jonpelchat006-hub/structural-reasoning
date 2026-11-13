// contract_scan.ts — §33: EXPAND-then-CONTRACT with per-atom coordinate descent (Jonathan).
// You don't poke one point out (unbalanced, spins off). You EXPAND the whole surface past the target, then
// PULL BACK atom by atom until the trajectory lands on the point INSIDE the space. Here: the broad expanded
// anchor = the bounce near-miss (a wide, already-close program); CONTRACTION = coordinate descent, adjusting
// ONE op at a time (replace / insert / delete, biased to affine neighbors = the §29/§30 reachable network)
// until it lands on the exact train fit. The trajectory spirals in; accept where it passes over the target.
import * as path from "path"; import * as fs from "fs";
import { loadTasks } from "./loader";
import { OP_NAMES, OPS, applyOp } from "./dsl";
import { bounceSearchDiag } from "./bounce_scan";
import { taskPalette } from "./transfer";
import { rec } from "./scan_recorder";
type Grid=number[][];
const eqG=(a:Grid,b:Grid)=>!!a&&!!b&&a.length===b.length&&a[0].length===b[0].length&&a.every((r,i)=>r.every((v,j)=>v===b[i][j]));
type Gene=[string,Record<string,number>]; type Genome=Gene[];
const build=(g:Genome)=>(grid:Grid):Grid|null=>{let c:Grid|null=grid;for(const[o,p]of g){if(!c)return null;try{c=applyOp({name:o,params:p} as any,c);}catch{return null;}}return c;};
function score(g:Genome,train:any[]):number{const f=build(g);let s=0;for(const p of train){const o=f(p.input),t=p.output;if(!o||o.length!==t.length||o[0].length!==t[0].length){s-=1;continue;}let eq=0,tot=t.length*t[0].length;for(let y=0;y<t.length;y++)for(let x=0;x<t[0].length;x++)if(o[y][x]===t[y][x])eq++;s+=eq/tot;}return s/train.length;}
const exact=(g:Genome,pairs:any[])=>{const f=build(g);return pairs.every((p:any)=>{const o=f(p.input);return o&&eqG(o,p.output);});};
const readJSON=(f:string)=>{try{return JSON.parse(fs.readFileSync(path.join(__dirname,"..",f),"utf8"));}catch{return null;}};
const CARDS=readJSON("atom_cards.json")||[]; const VAL:Record<string,Set<string>>={}; for(const c of CARDS) VAL[c.op]=new Set(c.valence||[]);
const aff=(a:string,b:string)=>a===b?0:[...(VAL[a]||[])].filter(x=>(VAL[b]||new Set()).has(x)).length;
// candidate ops for a position = affine neighbours of its context (bounded reachable set, §29/§30)
function cands(ctx:string|undefined):string[]{ if(!ctx) return OP_NAMES.slice(); const c=OP_NAMES.filter(o=>aff(ctx,o)>=1); return c.length?c:OP_NAMES.slice(); }
function paramsFor(op:string,pal:number[]):Record<string,number>[]{ try{const ps=(OPS as any)[op].enumerate(pal); return ps&&ps.length?ps.slice(0,3):[{}];}catch{return[{}];} }

// CONTRACT: coordinate descent — one atom at a time, keep any single change that improves train fit.
function contract(anchor:Genome, train:any[], pal:number[]):Genome{
  let cur=anchor.map(g=>[g[0],{...g[1]}] as Gene); let best=score(cur,train);
  for(let sweep=0; sweep<6 && best<1; sweep++){ let improved=false;
    for(let i=0;i<cur.length;i++){ const ctx=i>0?cur[i-1][0]:undefined;
      // replace atom i
      for(const op of cands(ctx)) for(const p of paramsFor(op,pal)){ const g=cur.slice(); g[i]=[op,p]; const s=score(g,train); if(s>best){best=s;cur=g.map(x=>[x[0],{...x[1]}] as Gene);improved=true;} }
      // delete atom i
      if(cur.length>1){ const g=cur.slice(); g.splice(i,1); const s=score(g,train); if(s>best){best=s;cur=g.map(x=>[x[0],{...x[1]}] as Gene);improved=true;} }
    }
    // insert one atom at each gap (affine to the left neighbour)
    if(!improved && cur.length<8) for(let i=0;i<=cur.length;i++){ const ctx=i>0?cur[i-1][0]:undefined;
      for(const op of cands(ctx).slice(0,10)) for(const p of paramsFor(op,pal)){ const g=cur.slice(); g.splice(i,0,[op,p]); const s=score(g,train); if(s>best){best=s;cur=g.map(x=>[x[0],{...x[1]}] as Gene);improved=true;break;} } }
    if(!improved) break;
  }
  return cur;
}

const ev=loadTasks(path.join(__dirname,"..","data-eval"));
const verified=new Set(fs.readFileSync(path.join(__dirname,"..","verified_eval.txt"),"utf8").trim().split(/\s+/).flatMap(s=>s.match(/.{1,8}/g)||[]));
const START=+(process.argv[2]||0), END=+(process.argv[3]||ev.length), STATE=process.argv[4]||null, BUDGET=+(process.argv[5]||34)*1000, T0=Date.now();
let baseSolved=0, contracted=0, net:string[]=[], RESUME=START;
if(STATE&&fs.existsSync(STATE)){const s=JSON.parse(fs.readFileSync(STATE,"utf8"));baseSolved=s.baseSolved;contracted=s.contracted;net=s.net;RESUME=s.next;}
const rep=()=>{ console.log("\n=== §33 EXPAND-then-CONTRACT (per-atom coordinate descent from bounce anchor) ["+START+","+END+") ===");
  console.log("bounce baseline solved: "+baseSolved+"   ADDITIONAL closed by contraction: "+contracted+"   net-new: "+net.length+"  "+net.join(" ")); };
if(STATE&&RESUME>=Math.min(END,ev.length)){rep();process.exit(0);}
for(let i=RESUME;i<Math.min(END,ev.length);i++){ const t=ev[i];
  if(STATE&&Date.now()-T0>BUDGET){fs.writeFileSync(STATE,JSON.stringify({next:i,baseSolved,contracted,net}));console.log("PAUSED at "+i+" base="+baseSolved+" contracted="+contracted);process.exit(0);}
  if(!t.test||t.test.some((te:any)=>!te.output))continue;
  let r:any=null; try{r=bounceSearchDiag(t.train,3,30);}catch{}
  if(!r||!r.bestProg)continue;
  const anchor=r.bestProg as Genome; const pal=taskPalette(t.train);
  if(exact(anchor,t.train)){ if(exact(anchor,t.test)){baseSolved++;} continue; } // bounce already solved it
  const c=contract(anchor,t.train,pal);
  if(exact(c,t.train)){ // contraction landed on the train fit
    if(exact(c,t.test)){ contracted++; rec("contract",t.id,"solved",c.map(x=>x[0]).join(">")); if(!verified.has(t.id))net.push(t.id); }
    else rec("contract",t.id,"overfit"); }
  if((i+1)%20===0)process.stderr.write("["+(i+1)+"] base="+baseSolved+" contracted="+contracted+"\n");
}
if(STATE)fs.writeFileSync(STATE,JSON.stringify({next:Math.min(END,ev.length),baseSolved,contracted,net}));
rep();
