// ability_draft.ts — §13.4: wire the ABILITY-DRAFT into the solver.
// Each inducer is tagged with a (slot × effect × execution) coordinate (the 4×4×4 ability tree).
// LEARN pass: run training, record which ability WINS per solved task -> master success stats.
// EVAL pass: DRAFT a per-task order from the learned stats, solve with it, and measure honestly
// against the fixed-sweep baseline (does drafting change solves? is the winning ability learnable?).
import * as path from "path"; import * as fs from "fs";
import { loadTasks } from "./loader";
import { solveDiscovery, INDUCERS } from "./discover";
type Grid = number[][];
const eqG = (a:Grid,b:Grid)=>!!a&&!!b&&a.length===b.length&&a[0].length===b[0].length&&a.every((r,i)=>r.every((v,j)=>v===b[i][j]));

const NAMES = INDUCERS.map(p=>p[0]);
// ability coordinates (slot × effect × execution) — the 4×4×4 tree positions
const COORD: Record<string,[string,string,string]> = {
  rankRecolor:["polish","commit","local"], shapeRecolor:["polish","commit","local"], colorMap:["polish","commit","self"],
  overlay:["closure","commit","global"], registerCombine:["closure","commit","global"],
  holeFill:["closure","commit","local"], holeEncloser:["closure","probe","local"], holeRank:["closure","probe","local"],
  shift:["perturb","commit","local"], gravity:["perturb","commit","local"], moveByColor:["perturb","commit","local"], objSlideByRank:["perturb","commit","cross"],
  scaleByFeat:["gradient","probe","cross"], tileByFeat:["gradient","probe","cross"], shiftByFeat:["gradient","probe","cross"], shear:["gradient","probe","cross"],
  rays:["gradient","commit","global"], connect:["gradient","commit","global"], trace:["gradient","commit","global"], stamp2:["gradient","commit","local"],
  fractal:["gradient","commit","self"], reflect:["polish","invert","self"], localRule:["perturb","probe","local"], localRuleMS:["perturb","probe","local"],
};
const winnerName = (kind:string) => NAMES.find(n => kind.endsWith(n)) || kind;

const MODE = process.argv[2] || "eval";
const STATS = path.join(__dirname,"..","ability_stats.json");

if (MODE === "learn") {
  const tasks = loadTasks(path.join(__dirname,"..","data"));
  const START=+(process.argv[3]||0), END=+(process.argv[4]||tasks.length);
  const stats: Record<string,number> = JSON.parse(fs.existsSync(STATS)?fs.readFileSync(STATS,"utf8"):"{}");
  let solved=0;
  for(let i=START;i<Math.min(END,tasks.length);i++){ const t=tasks[i];
    if(!t.test||t.test.some((te:any)=>!te.output)) continue;
    let r:any=null; try{r=solveDiscovery(t.train,undefined,true);}catch{}
    if(!r) continue; const ok=t.test.every((te:any)=>{const o=r.prog(te.input);return o&&eqG(o,te.output);});
    if(!ok) continue; solved++; const w=winnerName(r.kind); stats[w]=(stats[w]||0)+1;
    if((i+1)%50===0) process.stderr.write(`[learn ${i+1}] solved=${solved}\n`);
  }
  fs.writeFileSync(STATS, JSON.stringify(stats,null,1));
  const order = Object.entries(stats).sort((a,b)=>b[1]-a[1]);
  console.log("LEARN done. solved="+solved+"  abilities seen="+order.length);
  console.log("learned ability order (success counts):"); order.forEach(([n,c])=>console.log(`  ${c}\t${n}\t[${(COORD[n]||["?","?","?"]).join("/")}]`));
} else {
  const stats: Record<string,number> = JSON.parse(fs.existsSync(STATS)?fs.readFileSync(STATS,"utf8"):"{}");
  const learnedOrder = NAMES.slice().sort((a,b)=>(stats[b]||0)-(stats[a]||0));
  const eval_ = loadTasks(path.join(__dirname,"..","data-eval"));
  const verified = new Set(fs.readFileSync(path.join(__dirname,"..","verified_eval.txt"),"utf8").trim().split(/\s+/));
  const START=+(process.argv[3]||0), END=+(process.argv[4]||eval_.length);
  let bSolved=0,bNet=0, dSolved=0,dNet=0; const rankHist:Record<string,number>={}; let topK4=0;
  const TOP4 = new Set(learnedOrder.slice(0,4));
  for(let i=START;i<Math.min(END,eval_.length);i++){ const t=eval_[i];
    if(!t.test||t.test.some((te:any)=>!te.output)) continue;
    // baseline (fixed sweep)
    let rb:any=null; try{rb=solveDiscovery(t.train,undefined,true);}catch{}
    if(rb && t.test.every((te:any)=>{const o=rb.prog(te.input);return o&&eqG(o,te.output);})){ bSolved++; if(!verified.has(t.id))bNet++; }
    // drafted (learned order)
    let rd:any=null; try{rd=solveDiscovery(t.train,learnedOrder,true);}catch{}
    if(rd && t.test.every((te:any)=>{const o=rd.prog(te.input);return o&&eqG(o,te.output);})){ dSolved++; if(!verified.has(t.id))dNet++;
      const w=winnerName(rd.kind); const rank=learnedOrder.indexOf(w); const band=rank<4?"top4":rank<8?"5-8":rank<16?"9-16":"17+"; rankHist[band]=(rankHist[band]||0)+1; if(TOP4.has(w))topK4++; }
    if((i+1)%100===0) process.stderr.write(`[eval ${i+1}] base=${bSolved} draft=${dSolved}\n`);
  }
  console.log("\n=== §13.4 ABILITY-DRAFT vs FIXED-SWEEP (eval, looGate) ===");
  console.log("learned top-8 abilities: "+learnedOrder.slice(0,8).join(", "));
  console.log(`BASELINE (fixed sweep):  solved=${bSolved}  net-new=${bNet}`);
  console.log(`DRAFTED  (learned order): solved=${dSolved}  net-new=${dNet}`);
  console.log("winning-ability rank on drafted solves (learnability): "+JSON.stringify(rankHist));
  console.log(`drafted solves whose winner was in the learned TOP-4: ${topK4}/${dSolved}`);
}
