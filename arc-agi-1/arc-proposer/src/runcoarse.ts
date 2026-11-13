// runcoarse.ts — 4-probe coarse map (4→16→64). Probe each task with the 4
// fundamental role-axes, MEASURE tension reduction per axis (which directions are
// available + residual = how many objectives), then route the pooled solve by the
// measured ranking. Tests: does measured routing beat heuristic routing (70)?
import * as path from "path";
import { loadTasks } from "../../arc-slice/src/loader";
import { bruteCandidates } from "../../arc-slice/src/search";
import { colorMapRepair, sizeRepair } from "../../arc-slice/src/bugfinder";
import { taskPalette } from "../../arc-slice/src/transfer";
import { solves } from "../../arc-slice/src/verify";
import { solveCodon } from "../../arc-slice/src/codon";
import { run } from "../../arc-slice/src/program";
import { cellMatch } from "../../arc-slice/src/grid";
import { OPS } from "../../arc-slice/src/dsl";

const DATA = path.join(__dirname, "..", "..", "arc-slice", "data");
const AXES: Record<string,string[]> = {
  COLOR: ["recolor","swap","keepColor","removeColor","paintRank","colorByShape"],
  GEOM:  ["rotate","flipH","flipV","transpose"],
  SIZE:  ["crop","trim","scale","tile","downscale","cropToColor","fractal","mirrorConcat","half"],
  STRUCT:["fillHoles","fillObjHoles","symmetrize","completeSym","gravity","gravityObj","mapObjects","outline","connect","largest","keepLargest","keepSmallest","selectUnique","selectMajority","denoise","oddPanel","majPanel","overlayPanels","combinePanels","drawRays","grow","cross","stamp"],
};
function tension(prog:any, train:any){let s=0;for(const{input,output}of train){const g=run(prog,input);if(!g||g.length!==output.length||g[0].length!==output[0].length)s+=1;else s+=1-cellMatch(g,output);}return s/train.length;}

// best single-op tension within an axis (the coarse probe)
function probe(train:any, axis:string){
  const pal=taskPalette(train); let best=1;
  for(const name of AXES[axis]){const sp=OPS[name]; if(!sp)continue; for(const params of sp.enumerate(pal)){const t=tension([{name,params}],train); if(t<best)best=t; if(best===0)return 0;}}
  return best;
}
function solveAxis(train:any, axis:string){
  const c=bruteCandidates(train, AXES[axis]);
  if(c.bestScore===1&&solves(c.best,train))return true;
  const pal=taskPalette(train);
  for(const cand of c.colorCands){const f=colorMapRepair(cand,train);if(f&&solves(f,train))return true;}
  for(const cand of [...c.colorCands.slice(0,24),...c.sizeCands]){const f=sizeRepair(cand,train,pal);if(f&&solves(f,train))return true;}
  return false;
}
function main(){
  const tasks=loadTasks(DATA);
  let solved=0,codon=0,i=0; const axisHist:Record<string,number>={}; const depthHist:Record<string,number>={};
  for(const t of tasks){
    if(i++%100===0)process.stderr.write(`[${i}/${tasks.length}]\n`);
    if (t.train.some((p:any)=>p.input.length*p.input[0].length>500)) { if(solveAxis(t.train,'STRUCT')||solveAxis(t.train,'SIZE')||solveAxis(t.train,'COLOR')||solveCodon(t.train)) solved++; continue; }
    // 4-probe coarse map
    const red = Object.keys(AXES).map(a=>[a,probe(t.train,a)] as [string,number]).sort((x,y)=>x[1]-y[1]);
    const bestAxis=red[0][0], bestTension=red[0][1];
    axisHist[bestAxis]=(axisHist[bestAxis]??0)+1;
    const depth = bestTension===0?"0(direct)":bestTension<0.15?"1(close)":bestTension<0.5?"2(mid)":"3+(far)";
    depthHist[depth]=(depthHist[depth]??0)+1;
    // route: try axes in order of measured reduction
    let done=false;
    for(const [axis] of red){ if(solveAxis(t.train,axis)){solved++;done=true;break;} }
    if(!done && solveCodon(t.train)){codon++;}
  }
  console.log(`\n=== 4-PROBE COARSE MAP + MEASURED ROUTING ===`);
  console.log(`solved (axis-routed): ${solved}  + codon: ${codon}  = ${solved+codon}/${tasks.length} (${(100*(solved+codon)/tasks.length).toFixed(1)}%)`);
  console.log(`dominant-axis distribution: ${JSON.stringify(axisHist)}`);
  console.log(`coarse depth (residual after best single probe = ~#objectives): ${JSON.stringify(depthHist)}`);
}
main();
