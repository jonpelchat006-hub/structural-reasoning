// runtier.ts — impact-tiered pools (4→16→64 by tiles affected). Classify each op
// by MEASURED impact (fraction of tiles it changes), tier global→neighborhood→
// single. Solve coarse-to-fine: global pool first (cheap rough map), expand only
// if unsolved. Measure solves AND candidate-evals saved (efficiency).
import * as path from "path";
import { loadTasks } from "../../arc-slice/src/loader";
import { bruteCandidates } from "../../arc-slice/src/search";
import { colorMapRepair, sizeRepair } from "../../arc-slice/src/bugfinder";
import { taskPalette } from "../../arc-slice/src/transfer";
import { solves } from "../../arc-slice/src/verify";
import { solveCodon } from "../../arc-slice/src/codon";
import { OP_NAMES, OPS } from "../../arc-slice/src/dsl";
import { run } from "../../arc-slice/src/program";
import { dims } from "../../arc-slice/src/grid";

const DATA = path.join(__dirname, "..", "..", "arc-slice", "data");

// measure each op's impact = mean fraction of tiles changed across sample grids
function classify(tasks: any[]): { global: string[]; neigh: string[]; single: string[] } {
  const samples = tasks.slice(0, 30).map(t => t.train[0].input);
  const impact: Record<string, number> = {};
  for (const name of OP_NAMES) {
    if (name === "cmap") { impact[name] = 0.02; continue; }
    let tot = 0, cnt = 0;
    for (const g of samples) {
      const pal = [...new Set(g.flat())] as number[];
      const params = OPS[name].enumerate(pal)[0]; if (!params) continue;
      const out = run([{ name, params }], g); if (!out) continue;
      const [r,c]=dims(g);
      if (out.length!==r || out[0].length!==c) { tot += 1; cnt++; continue; } // dims change = global
      let ch=0; for(let y=0;y<r;y++)for(let x=0;x<c;x++) if(out[y][x]!==g[y][x]) ch++;
      tot += ch/(r*c); cnt++;
    }
    impact[name] = cnt ? tot/cnt : 0;
  }
  const g:string[]=[], n:string[]=[], s:string[]=[];
  for (const name of OP_NAMES) { const im=impact[name]; if(im>=0.4)g.push(name); else if(im>=0.12)n.push(name); else s.push(name); }
  return { global:g, neigh:n, single:s };
}

function solveWith(train:any, names:string[]): {ok:boolean, evals:number} {
  const c = bruteCandidates(train, names);
  let evals = names.reduce((a,nm)=>a + OPS[nm].enumerate(taskPalette(train)).length, 0);
  if (c.bestScore===1 && solves(c.best,train)) return {ok:true,evals};
  const pal=taskPalette(train);
  for(const cand of c.colorCands){const f=colorMapRepair(cand,train); evals++; if(f&&solves(f,train))return {ok:true,evals};}
  for(const cand of [...c.colorCands.slice(0,24),...c.sizeCands]){const f=sizeRepair(cand,train,pal); evals++; if(f&&solves(f,train))return {ok:true,evals};}
  return {ok:false,evals};
}

function main(){
  const tasks=loadTasks(DATA);
  const T=classify(tasks);
  console.log(`tiers: GLOBAL ${T.global.length} | NEIGHBORHOOD ${T.neigh.length} | SINGLE ${T.single.length}`);
  console.log(`  global: ${T.global.join(" ")}`);
  const tierA=T.global, tierB=[...T.global,...T.neigh], tierC=OP_NAMES;
  let solved=0,codon=0,i=0; let evalsTiered=0, evalsFlat=0; const stopTier:Record<string,number>={A:0,B:0,C:0};
  for(const t of tasks){
    if(i++%100===0)process.stderr.write(`[${i}/${tasks.length}]\n`);
    if (t.train.some((p:any)=>p.input.length*p.input[0].length>500)) { const r=solveWith(t.train,tierC); evalsTiered+=r.evals; evalsFlat+=r.evals; if(r.ok){solved++;stopTier.C++;} else if(solveCodon(t.train))codon++; continue; }
    const flat = OP_NAMES.reduce((a,nm)=>a+OPS[nm].enumerate(taskPalette(t.train)).length,0); evalsFlat+=flat;
    let r=solveWith(t.train,tierA); evalsTiered+=r.evals;
    if(r.ok){solved++;stopTier.A++;continue;}
    r=solveWith(t.train,tierB); evalsTiered+=r.evals;
    if(r.ok){solved++;stopTier.B++;continue;}
    r=solveWith(t.train,tierC); evalsTiered+=r.evals;
    if(r.ok){solved++;stopTier.C++;continue;}
    if(solveCodon(t.train))codon++;
  }
  console.log(`\n=== IMPACT-TIERED COARSE-TO-FINE ===`);
  console.log(`solved ${solved} + codon ${codon} = ${solved+codon}/${tasks.length} (${(100*(solved+codon)/tasks.length).toFixed(1)}%)`);
  console.log(`stop tier: global ${stopTier.A} | +neigh ${stopTier.B} | +single ${stopTier.C}`);
  console.log(`candidate-enumerations: tiered ${evalsTiered} vs flat-all-ops ${evalsFlat}  -> ${(100*(1-evalsTiered/evalsFlat)).toFixed(0)}% fewer (EFFICIENCY)`);
}
main();
