// flowmap.ts — classify every task by its MATTER(+)/ANTIMATTER(-)/VOID(0) flow.
// matter   = ink added (bg->colour) / output bigger  -> the GENERATOR sphere
// antimatter = ink removed (colour->bg) / output smaller -> the EXTRACTOR sphere
// void     = recolour/move, cells conserved            -> the REARRANGER
import * as path from "path";
import { loadTasks } from "./loader";
import { background } from "./grid";
const tasks=loadTasks(path.join(__dirname,"..","data"));
function classify(train:any[]):string{
  let add=0,rem=0,mov=0,big=0,small=0,same=0;
  for(const p of train){ const bi=p.input,bo=p.output; const bg=background(bi);
    const ai=bi.length*bi[0].length, ao=bo.length*bo[0].length;
    if(ao>ai) big++; else if(ao<ai) small++; else { same++;
      for(let y=0;y<bi.length;y++)for(let x=0;x<bi[0].length;x++){ const a=bi[y][x],b=bo[y][x];
        if(a===bg&&b!==bg) add++; else if(a!==bg&&b===bg) rem++; else if(a!==b) mov++; } }
  }
  if(big>small && big>=same) return "MATTER(bigger)";
  if(small>big) return "ANTIMATTER(smaller)";
  // same-dims: by dominant delta sign
  const tot=add+rem+mov; if(tot===0) return "VOID(identity?)";
  if(add>rem*1.5 && add>=mov) return "MATTER(ink+)";
  if(rem>add*1.5 && rem>=mov) return "ANTIMATTER(ink-)";
  if(mov>=add && mov>=rem) return "VOID(recolor/move)";
  return "MIXED";
}
const dist:Record<string,number>={};
for(const t of tasks){ const c=classify(t.train); dist[c]=(dist[c]??0)+1; }
console.log("=== TASK FLOW MAP (400) ===");
for(const [k,v] of Object.entries(dist).sort((a,b)=>b[1]-a[1])) console.log(`  ${k.padEnd(22)} ${v}`);
const matter=(dist["MATTER(bigger)"]??0)+(dist["MATTER(ink+)"]??0);
const anti=(dist["ANTIMATTER(smaller)"]??0)+(dist["ANTIMATTER(ink-)"]??0);
const voi=(dist["VOID(recolor/move)"]??0)+(dist["VOID(identity?)"]??0);
console.log(`\n  MATTER total: ${matter}   ANTIMATTER total: ${anti}   VOID total: ${voi}   MIXED: ${dist["MIXED"]??0}`);
