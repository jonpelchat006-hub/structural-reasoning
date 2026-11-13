// knot_scan.ts — §37/§38: the KNOT LADDER (Jonathan). Two sheets folding at the edge tie into a KNOT; the
// 4D collapse turns the closed knot into a POINT WITH ENDS (params frozen, only the interface exposed) —
// a new atom one level up. Then the whole construction REPEATS on the next floor: place the knot-points
// in level-2 space and search for LINES / CIRCUITS of knots up there. This also gives ping-pong (§22) its
// missing DEPTH axis: bounce laterally at level 1 (the DSL), FOLD UP when the edge is hit (the five wall
// confirmations are the edge), compose knots at level 2, FOLD BACK DOWN (a level-1 atom inserted between
// knots) when a level-2 line near-misses. §19's codons banked fragments; this banks WHOLE collapsed knots.
// §38: the 2nd floor has the same structure as the first — it builds its own middle shell (collect2 over
// training) before going up again; every new solve collapses immediately (the ladder feeds itself).
//
// Modes:
//   collect  [state] [sec]  — bounce over TRAINING; bank train-exact + test-generalizing programs (L1 knots)
//   collect2 [state] [sec]  — knot-compose over TRAINING bounce-unsolved; bank flattened winners (L2 knots)
//   resolve  <id...>        — re-solve specific tasks, bank their flattened words
//   compose  [state] [sec]  — level-N beam over knots ∪ DSL ops on unsolved EVAL, θ=1, net-new vs verified
import * as path from "path"; import * as fs from "fs";
import { loadTasks } from "./loader";
import { OPS, OP_NAMES, applyOp } from "./dsl";
import { bounceSearchDiag } from "./bounce_scan";
import { taskPalette } from "./transfer";
import { rec } from "./scan_recorder";
type Grid=number[][];
const eqG=(a:Grid,b:Grid)=>!!a&&!!b&&a.length===b.length&&a[0].length===b[0].length&&a.every((r,i)=>r.every((v,j)=>v===b[i][j]));
type Gene=[string,Record<string,number>]; type Genome=Gene[];
const buildWord=(g:Genome)=>(grid:Grid):Grid|null=>{let c:Grid|null=grid;for(const[o,p]of g){if(!c)return null;try{c=applyOp({name:o,params:p} as any,c);}catch{return null;}}return c;};

const KNOTS_FILE=path.join(__dirname,"..","knots.json");
const MODE=process.argv[2]||"compose", STATE=process.argv[3]||null, BUDGET=+(process.argv[4]||34)*1000, T0=Date.now();

// ── Phase 1: COLLECT — tie and collapse ──
if(MODE==="collect"){
  const tr=loadTasks(path.join(__dirname,"..","data"));
  let knots:{id:string;word:Genome}[]=fs.existsSync(KNOTS_FILE)?JSON.parse(fs.readFileSync(KNOTS_FILE,"utf8")):[];
  let RESUME=0; if(STATE&&fs.existsSync(STATE))RESUME=JSON.parse(fs.readFileSync(STATE,"utf8")).next;
  const save=(next:number)=>{fs.writeFileSync(KNOTS_FILE,JSON.stringify(knots));if(STATE)fs.writeFileSync(STATE,JSON.stringify({next}));};
  for(let i=RESUME;i<tr.length;i++){const t=tr[i];
    if(STATE&&Date.now()-T0>BUDGET){save(i);console.log("PAUSED at "+i+" knots="+knots.length);process.exit(0);}
    if(!t.test||t.test.some((te:any)=>!te.output))continue;
    let r:any=null; try{r=bounceSearchDiag(t.train,3,30);}catch{}
    if(!r||!r.prog||!r.bestProg)continue;
    const f=buildWord(r.bestProg as Genome);
    if(!t.test.every((te:any)=>{const o=f(te.input);return o&&eqG(o,te.output);}))continue; // knot must generalize
    const sig=JSON.stringify(r.bestProg);
    if(!knots.some(k=>JSON.stringify(k.word)===sig))knots.push({id:t.id,word:r.bestProg as Genome});
    if((i+1)%25===0)process.stderr.write("["+(i+1)+"] knots="+knots.length+"\n");
  }
  save(tr.length);
  console.log("\n=== §37 phase 1 COLLECT: "+knots.length+" collapsed knots banked (train-exact + test-generalizing) ===");
  for(const k of knots)console.log("  "+k.id+" = "+k.word.map(g=>g[0]).join("*"));
  process.exit(0);
}

// ── shared level-2 machinery ──
const knots:{id:string;word:Genome;level?:number}[]=JSON.parse(fs.readFileSync(KNOTS_FILE,"utf8"));
// FLATTEN = the collapse made explicit: a level-2 word (with K: references) reduces to one frozen
// level-1 genome — the Euler reduction; the new floor sees only the point, not the braid inside.
const knotById=new Map(knots.map(k=>["K:"+k.id,k.word] as [string,Genome]));
function flatten(word:{name:string;p:Record<string,number>}[]):Genome{
  const out:Genome=[];
  for(const{name,p}of word){const kw=knotById.get(name);if(kw)out.push(...kw);else out.push([name,p]);}
  return out;
}
function bankKnot(id:string,flat:Genome,level:number){
  const sig=JSON.stringify(flat);
  if(knots.some(k=>JSON.stringify(k.word)===sig))return false;
  knots.push({id,word:flat,level});fs.writeFileSync(KNOTS_FILE,JSON.stringify(knots));return true;
}
// the collapse: a knot is ONE op — params frozen, internal structure hidden, only the ends exposed
type Atom={name:string;isKnot:boolean;fn:(g:Grid)=>Grid|null;params:Record<string,number>[]};
const VOCAB:Atom[]=[];
for(const k of knots)VOCAB.push({name:"K:"+k.id,isKnot:true,fn:buildWord(k.word),params:[{}]});
const ev=loadTasks(path.join(__dirname,"..","data-eval"));
const verified=new Set(fs.readFileSync(path.join(__dirname,"..","verified_eval.txt"),"utf8").trim().split(/\s+/).flatMap(s=>s.match(/.{1,8}/g)||[]));
function score(gs:Grid[],outs:Grid[]):number{let s=0;for(let i=0;i<gs.length;i++){const g=gs[i],o=outs[i];
  if(!g||g.length!==o.length||g[0].length!==o[0].length){s-=1;continue;}
  let eq=0,tot=g.length*g[0].length;for(let y=0;y<g.length;y++)for(let x=0;x<g[0].length;x++)if(g[y][x]===o[y][x])eq++;s+=eq/tot;}
  return s/gs.length;}
type St={grids:Grid[];word:{a:Atom;p:Record<string,number>}[];sc:number;hasKnot:boolean};
function knotSearch(train:any[],pal:number[],depth=3,beamW=30):{fn:(g:Grid)=>Grid|null;how:string;word:{name:string;p:Record<string,number>}[]}|null{
  const outs=train.map((p:any)=>p.output);
  const vocab:Atom[]=VOCAB.slice();
  for(const op of OP_NAMES){let ps:Record<string,number>[];try{ps=(OPS as any)[op].enumerate(pal).slice(0,4);}catch{ps=[{}];}
    vocab.push({name:op,isKnot:false,fn:null as any,params:ps});}
  const apply=(a:Atom,p:Record<string,number>,g:Grid):Grid|null=>{
    if(a.isKnot)return a.fn(g);
    try{return applyOp({name:a.name,params:p} as any,g);}catch{return null;}};
  let beam:St[]=[{grids:train.map((p:any)=>p.input),word:[],sc:score(train.map((p:any)=>p.input),outs),hasKnot:false}];
  const seen=new Set<string>();
  for(let d=0;d<depth;d++){const next:St[]=[];
    for(const st of beam)for(const a of vocab)for(const p of a.params){
      let g2:Grid[]=[],bad=false;
      for(const g of st.grids){const r=apply(a,p,g);if(!r){bad=true;break;}g2.push(r);}
      if(bad)continue;
      const word=[...st.word,{a,p}],hasKnot=st.hasKnot||a.isKnot;
      if(hasKnot&&g2.every((g,i)=>eqG(g,outs[i]))){ // circuit closes — and it contains >=1 level-2 point
        const w=word.slice();
        return{fn:(g:Grid)=>{let c:Grid|null=g;for(const{a,p}of w){if(!c)return null;c=apply(a,p,c);}return c;},
               how:w.map(x=>x.a.name).join(" * "),word:w.map(x=>({name:x.a.name,p:x.p}))};}
      const key=g2.map(g=>g.length+"x"+g[0].length+":"+g.flat().join("")).join("|");
      if(seen.has(key))continue;seen.add(key);
      next.push({grids:g2,word,sc:score(g2,outs),hasKnot});
    }
    // the depth ping-pong: keep the beam MIXED — best knot-carrying states are retained alongside
    // pure level-1 states, so the search can fold up (knot) and back down (op) within one word
    next.sort((a,b)=>b.sc-a.sc);
    const withK=next.filter(s=>s.hasKnot).slice(0,Math.ceil(beamW/2));
    const noK=next.filter(s=>!s.hasKnot).slice(0,beamW-withK.length);
    beam=[...withK,...noK];
    if(!beam.length)break;
  }
  return null;
}

// ── mode: RESOLVE — re-solve specific tasks (eval or training) and bank their flattened words ──
if(MODE==="resolve"){
  const ids=process.argv.slice(3); const all=[...ev,...loadTasks(path.join(__dirname,"..","data"))];
  for(const id of ids){const t=all.find(x=>x.id===id);if(!t){console.log(id+" not found");continue;}
    let w:any=null;try{w=knotSearch(t.train,taskPalette(t.train));}catch{}
    if(w&&t.test.every((te:any)=>{const o=w.fn(te.input);return o&&eqG(o,te.output);})){
      const added=bankKnot("L2:"+id,flatten(w.word),2);
      console.log(id+" banked="+added+"  "+w.how);
    } else console.log(id+" no knot-solve");}
  process.exit(0);
}

// ── mode: COLLECT2 — floor 2 builds its own middle shell from TRAINING (bounce-unsolved tasks) ──
if(MODE==="collect2"){
  const tr=loadTasks(path.join(__dirname,"..","data"));
  const l1ids=new Set(knots.filter(k=>!k.level).map(k=>k.id));
  let RESUME=0,banked=0,tried=0;
  if(STATE&&fs.existsSync(STATE)){const s=JSON.parse(fs.readFileSync(STATE,"utf8"));RESUME=s.next;banked=s.banked;tried=s.tried;}
  for(let i=RESUME;i<tr.length;i++){const t=tr[i];
    if(STATE&&Date.now()-T0>BUDGET){fs.writeFileSync(STATE,JSON.stringify({next:i,banked,tried}));console.log("PAUSED at "+i+" banked="+banked+"/"+tried);process.exit(0);}
    if(!t.test||t.test.some((te:any)=>!te.output))continue;
    if(l1ids.has(t.id))continue; // bounce already collapsed this one at level 1
    if(t.train.some((p:any)=>p.input.length*p.input[0].length>460))continue;
    tried++;
    let w:any=null;try{w=knotSearch(t.train,taskPalette(t.train));}catch{}
    if(!w)continue;
    if(!t.test.every((te:any)=>{const o=w.fn(te.input);return o&&eqG(o,te.output);}))continue; // must generalize
    if(bankKnot("L2:"+t.id,flatten(w.word),2))banked++;
    if((i+1)%25===0)process.stderr.write("["+(i+1)+"] banked="+banked+"\n");
  }
  if(STATE)fs.writeFileSync(STATE,JSON.stringify({next:tr.length,banked,tried}));
  console.log("\n=== §38 COLLECT2: +"+banked+" level-2 knots from training (tried "+tried+") — total "+knots.length+" ===");
  process.exit(0);
}

// ── mode: COMPOSE (default) — level-N lines/circuits on unsolved EVAL ──
let RESUME=0,closed=0,trainOnly=0,net:string[]=[],hows:string[]=[];
if(STATE&&fs.existsSync(STATE)){const s=JSON.parse(fs.readFileSync(STATE,"utf8"));RESUME=s.next;closed=s.closed;trainOnly=s.trainOnly;net=s.net;hows=s.hows;}
const rep=()=>{console.log("\n=== §37/38 COMPOSE: level-N lines/circuits over "+knots.length+" knots ===");
  console.log("closed (train theta=1, test PASS): "+closed+"   train-closed-but-test-failed: "+trainOnly);
  console.log("NET-NEW vs verified_eval: "+net.length+"   "+net.join(" "));
  for(const h of hows)console.log("  "+h);};
if(STATE&&RESUME>=ev.length){rep();process.exit(0);}
for(let i=RESUME;i<ev.length;i++){const t=ev[i];
  if(STATE&&Date.now()-T0>BUDGET){fs.writeFileSync(STATE,JSON.stringify({next:i,closed,trainOnly,net,hows}));console.log("PAUSED at "+i+" closed="+closed+" net="+net.length);process.exit(0);}
  if(!t.test||t.test.some((te:any)=>!te.output))continue;
  if(verified.has(t.id))continue; // only aim at the unsolved — net-new is the metric
  if(t.train.some((p:any)=>p.input.length*p.input[0].length>460))continue;
  let w:any=null; try{w=knotSearch(t.train,taskPalette(t.train));}catch{}
  if(!w)continue;
  if(!t.train.every((p:any)=>{const o=w.fn(p.input);return o&&eqG(o,p.output);}))continue;
  if(t.test.every((te:any)=>{const o=w.fn(te.input);return o&&eqG(o,te.output);})){
    closed++;net.push(t.id);hows.push(t.id+" = "+w.how);rec("knot",t.id,"solved",w.how);
    bankKnot("L2:"+t.id,flatten(w.word),2); // the new solve collapses immediately — the ladder feeds itself
  }else{trainOnly++;hows.push(t.id+" OVERFIT "+w.how);rec("knot",t.id,"overfit",w.how);}
  if((i+1)%20===0)process.stderr.write("["+(i+1)+"] closed="+closed+" trainOnly="+trainOnly+"\n");
}
if(STATE)fs.writeFileSync(STATE,JSON.stringify({next:ev.length,closed,trainOnly,net,hows}));
rep();
