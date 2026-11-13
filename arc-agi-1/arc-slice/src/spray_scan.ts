// spray_scan.ts — §41: SPRAY HOTSPOTS (Jonathan, §39c). Floor 1's outer shell sprays energy upward at
// angles; the fragments in its NEAR-MISS anchors deposit heat on the level-2 atoms they point toward.
// The level-2 beam then retains by fit + lambda*spray — a second retention prior, following the evidence
// that the only lateral wall-beater so far was a retention change (§37.2 knot mass). Catch surface wider
// than the spray: ALL knots stay in vocabulary; heat only biases which survive pruning.
import * as path from "path"; import * as fs from "fs";
import { loadTasks } from "./loader";
import { OPS, OP_NAMES, applyOp } from "./dsl";
import { bounceSearchDiag } from "./bounce_scan";
import { taskPalette } from "./transfer";
import { rec } from "./scan_recorder";
type Grid=number[][];
const eqG=(a:Grid,b:Grid)=>!!a&&!!b&&a.length===b.length&&a[0].length===b[0].length&&a.every((r,i)=>r.every((v,j)=>v===b[i][j]));
type Gene=[string,Record<string,number>]; type Genome=Gene[];
const knots:{id:string;word:Genome;level?:number}[]=JSON.parse(fs.readFileSync(path.join(__dirname,"..","knots.json"),"utf8"));
type Move={label:string;isKnot:boolean;frag:Genome;heat:number};
const LAMBDA=0.2;
function search(train:any[],pal:number[],heatByKnot:Map<string,number>,depth=3,beamW=30):{fn:(g:Grid)=>Grid|null;how:string}|null{
  const outs=train.map((p:any)=>p.output);
  const moves:Move[]=[];
  for(const k of knots)moves.push({label:"K:"+k.id,isKnot:true,frag:k.word,heat:heatByKnot.get(k.id)||0});
  for(const op of OP_NAMES){let ps:Record<string,number>[];try{ps=(OPS as any)[op].enumerate(pal).slice(0,4);}catch{ps=[{}];}
    for(const p of ps)moves.push({label:op,isKnot:false,frag:[[op,p]],heat:0});}
  const sc=(gs:Grid[])=>{let s=0;for(let i=0;i<gs.length;i++){const g=gs[i],o=outs[i];
    if(!g||g.length!==o.length||g[0].length!==o[0].length){s-=1;continue;}
    let eq=0,tot=g.length*g[0].length;for(let y=0;y<g.length;y++)for(let x=0;x<g[0].length;x++)if(g[y][x]===o[y][x])eq++;s+=eq/tot;}return s/gs.length;};
  type St={grids:Grid[];gen:Genome;labels:string[];s:number;heat:number;hasK:boolean};
  let beam:St[]=[{grids:train.map((p:any)=>p.input),gen:[],labels:[],s:sc(train.map((p:any)=>p.input)),heat:0,hasK:false}];
  const seen=new Set<string>();
  for(let d=0;d<depth;d++){const next:St[]=[];
    for(const st of beam)for(const mv of moves){
      let g2:Grid[]=[],bad=false;
      for(const g of st.grids){let c:Grid|null=g;for(const[o,p]of mv.frag){if(!c){bad=true;break;}try{c=applyOp({name:o,params:p} as any,c);}catch{bad=true;break;}}if(bad||!c){bad=true;break;}g2.push(c);}
      if(bad)continue;
      const gen=[...st.gen,...mv.frag],labels=[...st.labels,mv.label],hasK=st.hasK||mv.isKnot,heat=st.heat+mv.heat;
      if(hasK&&g2.every((g,i)=>eqG(g,outs[i]))){
        const w=gen.slice();
        return{fn:build(w),how:labels.join(" * ")};}
      const key=g2.map(g=>g.length+"x"+g[0].length+":"+g.flat().join("")).join("|");
      if(seen.has(key))continue;seen.add(key);
      next.push({grids:g2,gen,labels,s:sc(g2),heat,hasK});
    }
    // HOT retention: knot-half sorted by fit + lambda*heat (the spray bias), op-half by fit
    const wk=next.filter(x=>x.hasK).sort((a,b)=>(b.s+LAMBDA*b.heat)-(a.s+LAMBDA*a.heat)).slice(0,Math.ceil(beamW/2));
    const nk=next.filter(x=>!x.hasK).sort((a,b)=>b.s-a.s).slice(0,beamW-wk.length);
    beam=[...wk,...nk];if(!beam.length)break;
  }
  return null;
}
const build=(g:Genome)=>(grid:Grid):Grid|null=>{let c:Grid|null=grid;for(const[o,p]of g){if(!c)return null;try{c=applyOp({name:o,params:p} as any,c);}catch{return null;}}return c;};

const ev=loadTasks(path.join(__dirname,"..","data-eval"));
const verified=new Set(fs.readFileSync(path.join(__dirname,"..","verified_eval.txt"),"utf8").trim().split(/\s+/).flatMap(s=>s.match(/.{1,8}/g)||[]));
const STATE=process.argv[2]||null,BUDGET=+(process.argv[3]||34)*1000,T0=Date.now();
let RESUME=0,closed=0,trainOnly=0,net:string[]=[],hows:string[]=[];
if(STATE&&fs.existsSync(STATE)){const s=JSON.parse(fs.readFileSync(STATE,"utf8"));RESUME=s.next;closed=s.closed;trainOnly=s.trainOnly;net=s.net;hows=s.hows;}
const rep=()=>{console.log("\n=== §41 SPRAY-HOTSPOT beam (retention = fit + "+LAMBDA+"*heat) EVAL ===");
  console.log("closed: "+closed+"   train-closed-but-test-failed: "+trainOnly);
  console.log("NET-NEW vs verified_eval: "+net.length+"   "+net.join(" "));
  for(const h of hows)console.log("  "+h);};
if(STATE&&RESUME>=ev.length){rep();process.exit(0);}
for(let i=RESUME;i<ev.length;i++){const t=ev[i];
  if(STATE&&Date.now()-T0>BUDGET){fs.writeFileSync(STATE,JSON.stringify({next:i,closed,trainOnly,net,hows}));console.log("PAUSED at "+i+" closed="+closed+" net="+net.length);process.exit(0);}
  if(!t.test||t.test.some((te:any)=>!te.output))continue;
  if(verified.has(t.id))continue;
  if(t.train.some((p:any)=>p.input.length*p.input[0].length>460))continue;
  // THE SPRAY: level-1 near-miss anchor fragments deposit heat on knots sharing their ops
  let r:any=null;try{r=bounceSearchDiag(t.train,3,30);}catch{}
  if(!r||!r.bestProg)continue;
  const anchorOps=new Set((r.bestProg as Genome).map(g=>g[0]));
  const heat=new Map<string,number>();
  for(const k of knots){const ops=k.word.map(g=>g[0]);const shared=ops.filter(o=>anchorOps.has(o)).length;
    if(shared)heat.set(k.id,Math.max(0,r.bestScore)*shared/ops.length);}
  let w:any=null;try{w=search(t.train,taskPalette(t.train),heat);}catch{}
  if(!w)continue;
  if(!t.train.every((p:any)=>{const o=w.fn(p.input);return o&&eqG(o,p.output);}))continue;
  if(t.test.every((te:any)=>{const o=w.fn(te.input);return o&&eqG(o,te.output);})){
    closed++;net.push(t.id);hows.push(t.id+" = "+w.how);rec("spray",t.id,"solved",w.how);
  }else{trainOnly++;hows.push(t.id+" OVERFIT "+w.how);rec("spray",t.id,"overfit",w.how);}
  if((i+1)%20===0)process.stderr.write("["+(i+1)+"] closed="+closed+"\n");
}
if(STATE)fs.writeFileSync(STATE,JSON.stringify({next:ev.length,closed,trainOnly,net,hows}));
rep();
