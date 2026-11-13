import * as path from "path";
import { loadTasks } from "../../arc-slice/src/loader";
import { bruteCandidates } from "../../arc-slice/src/search";
import { colorMapRepair, sizeRepair } from "../../arc-slice/src/bugfinder";
import { taskPalette } from "../../arc-slice/src/transfer";
import { solves } from "../../arc-slice/src/verify";
import { solveCodon } from "../../arc-slice/src/codon";
import { induceMove } from "./induce";
import { induceGravity, induceReflect, induceToward } from "./induce2";
import { equal } from "../../arc-slice/src/grid";

const DATA = path.join(__dirname, "..", "..", "arc-slice", "data");
function stackSolves(train: any): boolean {
  const c = bruteCandidates(train);
  if (c.bestScore === 1 && solves(c.best, train)) return true;
  const pal = taskPalette(train);
  for (const cand of c.colorCands) { const f = colorMapRepair(cand, train); if (f && solves(f, train)) return true; }
  for (const cand of [...c.colorCands.slice(0,80), ...c.sizeCands]) { const f = sizeRepair(cand, train, pal); if (f && solves(f, train)) return true; }
  return !!solveCodon(train);
}
function main() {
  const tasks = loadTasks(DATA);
  const inducers: [string, (t:any)=>any][] = [["move",induceMove],["gravity",induceGravity],["reflect",induceReflect],["toward",induceToward]];
  let stack=0, newOnes=0, i=0, testOK=0, testTot=0; const by: Record<string,number>={}; const ex:string[]=[];
  for (const t of tasks) {
    if (i++ % 100 === 0) process.stderr.write(`[${i}/${tasks.length}]\n`);
    if (t.train.some((p:any)=>p.input.length*p.input[0].length>900)) continue;
    if (stackSolves(t.train)) { stack++; continue; }
    for (const [name, fnGen] of inducers) {
      const fn = fnGen(t.train);
      if (fn) { newOnes++; by[name]=(by[name]??0)+1; if(ex.length<16)ex.push(`  ${t.id} [${name}]`);
        for (const tt of t.test){ testTot++; const got=fn(tt.input); if(tt.output&&got&&equal(got,tt.output))testOK++; } break; }
    }
  }
  console.log(`\n=== INDUCTION TEMPLATES ===`);
  console.log(`stack: ${stack}   + induced NEW: ${newOnes}   = ${stack+newOnes}/${tasks.length} (${(100*(stack+newOnes)/tasks.length).toFixed(1)}%)`);
  console.log(`by template: ${JSON.stringify(by)}   induced test-correct: ${testOK}/${testTot}`);
  if (ex.length) console.log("induced solves:\n"+ex.join("\n"));
}
main();
