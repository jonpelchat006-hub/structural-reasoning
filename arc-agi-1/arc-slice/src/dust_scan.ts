// dust_scan.ts — §42: the TOROIDAL RETURN (Jonathan). Ascent climbs the inner shells shedding DUST
// (the collapsed braids' interiors, the near-miss words' genes — information only useful below);
// the exhaust §41 measured IS the way down; the bottom intake is where the second sheet comes from:
// dust from OTHER operations falls through and re-enters the level-1 enumeration as new material.
// Light dust = single genes (op+params), light enough to ride the routing (the magnetic condition).
// Modes: collect (harvest gene-dust from knot-beam near-misses on unsolved eval -> dust.json)
//        burn    (re-run the beam with dust-augmented enumeration; theta=1; net-new vs verified)
import * as path from "path"; import * as fs from "fs";
import { loadTasks } from "./loader";
import { OPS, OP_NAMES, applyOp } from "./dsl";
import { taskPalette } from "./transfer";
import { rec } from "./scan_recorder";
type Grid=number[][];
const eqG=(a:Grid,b:Grid)=>!!a&&!!b&&a.length===b.length&&a[0].length===b[0].length&&a.every((r,i)=>r.every((v,j)=>v===b[i][j]));
type Gene=[string,Record<string,number>]; type Genome=Gene[];
const build=(g:Genome)=>(grid:Grid):Grid|null=>{let c:Grid|null=grid;for(const[o,p]of g){if(!c)return null;try{c=applyOp({name:o,params:p} as any,c);}catch{return null;}}return c;};
const knots:{id:string;word:Genome}[]=JSON.parse(fs.readFileSync(path.join(__dirname,"..","knots.json"),"utf8"));
const DUST_FILE=path.join(__dirname,"..","dust.json");
const MODE=process.argv[2]||"burn",STATE=process.argv[3]||null,BUDGET=+(process.argv[4]||34)*1000,T0=Date.now();
const ev=loadTasks(path.join(__dirname,"..","data-eval"));
const verified=new Set(fs.readFileSync(path.join(__dirname,"..","verified_eval.txt"),"utf8").trim().split(/\s+/).flatMap(s=>s.match(/.{1,8}/g)||[]));

function beam(train:any[],pal:number[],dustByOp:Record<string,Record<string,number>[]>|null,depth=3,beamW=30):{gen:Genome|null;score:number;exactGen:Genome|null}{
  const outs=train.map((p:any)=>p.output);
  type Move={frag:Genome;isK:boolean};
  const moves:Move[]=[];
  for(const k of knots)moves.push({frag:k.word,isK:true});
  for(const op of OP_NAMES){let ps:Record<string,number>[];try{ps=(OPS as any)[op].enumerate(pal).slice(0,4);}catch{ps=[{}];}
    if(dustByOp&&dustByOp[op])for(const d of dustByOp[op])if(!ps.some(q=>JSON.stringify(q)===JSON.stringify(d)))ps.push(d); // THE BOTTOM INTAKE
    for(const p of ps)moves.push({frag:[[op,p]],isK:false});}
  const sc=(gs:Grid[])=>{let s=0;for(let i=0;i<gs.length;i++){const g=gs[i],o=outs[i];
    if(!g||g.length!==o.length||g[0].length!==o[0].length){s-=1;continue;}
    let eq=0,tot=g.length*g[0].length;for(let y=0;y<g.length;y++)for(let x=0;x<g[0].length;x++)if(g[y][x]===o[y][x])eq++;s+=eq/tot;}return s/gs.length;};
  type St={grids:Grid[];gen:Genome;s:number;hasK:boolean};
  let bm:St[]=[{grids:train.map((p:any)=>p.input),gen:[],s:sc(train.map((p:any)=>p.input)),hasK:false}];
  let best:Genome|null=null,bestS=-1;const seen=new Set<string>();
  for(let d=0;d<depth;d++){const next:St[]=[];
    for(const st of bm)for(const mv of moves){
      let g2:Grid[]=[],bad=false;
      for(const g of st.grids){let c:Grid|null=g;for(const[o,p]of mv.frag){if(!c){bad=true;break;}try{c=applyOp({name:o,params:p} as any,c);}catch{bad=true;break;}}if(bad||!c){bad=true;break;}g2.push(c);}
      if(bad)continue;
      const gen=[...st.gen,...mv.frag],s=sc(g2),hasK=st.hasK||mv.isK;
      if(s>bestS){bestS=s;best=gen;}
      if(g2.every((g,i)=>eqG(g,outs[i])))return{gen:best,score:1,exactGen:gen};
      const key=g2.map(g=>g.length+"x"+g[0].length+":"+g.flat().join("")).join("|");
      if(seen.has(key))continue;seen.add(key);
      next.push({grids:g2,gen,s,hasK});
    }
    next.sort((a,b)=>b.s-a.s);
    const wk=next.filter(x=>x.hasK).slice(0,Math.ceil(beamW/2));
    bm=[...wk,...next.filter(x=>!x.hasK).slice(0,beamW-wk.length)];
    if(!bm.length)break;
  }
  return{gen:best,score:bestS,exactGen:null};
}

if(MODE==="collect"){
  let dust:Record<string,Record<string,string|number>[]>=fs.existsSync(DUST_FILE)?JSON.parse(fs.readFileSync(DUST_FILE,"utf8")):{};
  const cnt:Record<string,number>=dust.__cnt as any||{};
  let RESUME=0;if(STATE&&fs.existsSync(STATE))RESUME=JSON.parse(fs.readFileSync(STATE,"utf8")).next;
  for(let i=RESUME;i<ev.length;i++){const t=ev[i];
    if(STATE&&Date.now()-T0>BUDGET){fs.writeFileSync(DUST_FILE,JSON.stringify({...dust,__cnt:cnt}));fs.writeFileSync(STATE,JSON.stringify({next:i}));console.log("PAUSED "+i+" genes="+Object.keys(cnt).length);process.exit(0);}
    if(!t.test||t.test.some((te:any)=>!te.output))continue;
    if(verified.has(t.id))continue;
    if(t.train.some((p:any)=>p.input.length*p.input[0].length>460))continue;
    let r:any=null;try{r=beam(t.train,taskPalette(t.train),null);}catch{}
    if(!r||!r.gen||r.score>=1||r.score<0.5)continue; // dust only from real near-misses
    for(const[op,p]of r.gen){const key=op+"|"+JSON.stringify(p);cnt[key]=(cnt[key]||0)+1;}
  }
  fs.writeFileSync(DUST_FILE,JSON.stringify({__cnt:cnt}));if(STATE)fs.writeFileSync(STATE,JSON.stringify({next:ev.length}));
  console.log("=== §42 DUST collected: "+Object.keys(cnt).length+" distinct genes ===");
  process.exit(0);
}
// burn
const raw=JSON.parse(fs.readFileSync(DUST_FILE,"utf8")).__cnt as Record<string,number>;
const byOp:Record<string,Record<string,number>[]>={};
for(const[key,n]of Object.entries(raw).sort((a,b)=>b[1]-a[1])){
  if(n<2)continue; // light dust must recur to ride the wave (cross-task support)
  const op=key.slice(0,key.indexOf("|")),p=JSON.parse(key.slice(key.indexOf("|")+1));
  (byOp[op]=byOp[op]||[]).push(p);if(byOp[op].length>6)byOp[op].pop();
}
let RESUME=0,closed=0,trainOnly=0,net:string[]=[],hows:string[]=[];
if(STATE&&fs.existsSync(STATE)){const s=JSON.parse(fs.readFileSync(STATE,"utf8"));RESUME=s.next;closed=s.closed;trainOnly=s.trainOnly;net=s.net;hows=s.hows;}
const rep=()=>{console.log("\n=== §42 DUST BURN (bottom intake: cross-task gene dust in the enumeration) ===");
  console.log("closed: "+closed+"  overfit: "+trainOnly+"  NET-NEW: "+net.length+"  "+net.join(" "));for(const h of hows)console.log("  "+h);};
if(STATE&&RESUME>=ev.length){rep();process.exit(0);}
for(let i=RESUME;i<ev.length;i++){const t=ev[i];
  if(STATE&&Date.now()-T0>BUDGET){fs.writeFileSync(STATE,JSON.stringify({next:i,closed,trainOnly,net,hows}));console.log("PAUSED "+i+" net="+net.length);process.exit(0);}
  if(!t.test||t.test.some((te:any)=>!te.output))continue;
  if(verified.has(t.id))continue;
  if(t.train.some((p:any)=>p.input.length*p.input[0].length>460))continue;
  let r:any=null;try{r=beam(t.train,taskPalette(t.train),byOp);}catch{}
  if(!r||!r.exactGen)continue;
  const fn=build(r.exactGen);
  if(!t.train.every((p:any)=>{const o=fn(p.input);return o&&eqG(o,p.output);}))continue;
  if(t.test.every((te:any)=>{const o=fn(te.input);return o&&eqG(o,te.output);})){
    closed++;net.push(t.id);hows.push(t.id+" = "+r.exactGen.map((g:Gene)=>g[0]).join(" * "));rec("dust",t.id,"solved");
  }else{trainOnly++;rec("dust",t.id,"overfit");}
}
if(STATE)fs.writeFileSync(STATE,JSON.stringify({next:ev.length,closed,trainOnly,net,hows}));
rep();
