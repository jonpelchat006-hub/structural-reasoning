import * as path from "path";
import { loadTasks } from "../../arc-slice/src/loader";
import { coordinate } from "./coordinator";
import { Memory } from "./memory";

const DATA = path.join(__dirname, "..", "..", "arc-slice", "data");
function main() {
  const tasks = loadTasks(DATA);
  const mem = new Memory();                 // starts EMPTY — learns online during the run
  let solved = 0, warm = 0, i = 0, firstHalfWarm = 0, secondHalfWarm = 0, fhSolved = 0, shSolved = 0;
  for (const t of tasks) {
    if (i % 100 === 0) process.stderr.write(`[${i}/${tasks.length}]\n`);
    const r = coordinate(t.train, t.id, mem);
    if (r) { solved++; if (r.warm) warm++;
      if (i < tasks.length/2) { fhSolved++; if (r.warm) firstHalfWarm++; } else { shSolved++; if (r.warm) secondHalfWarm++; } }
    i++;
  }
  console.log(`\n=== NON-LLM COORDINATOR (online learning, ${tasks.length} tasks) ===`);
  console.log(`solved (pure structure, zero model): ${solved}/${tasks.length} (${(100*solved/tasks.length).toFixed(1)}%)`);
  console.log(`warm hits (memory's plan predicted the solving branch): ${warm}/${solved} (${(100*warm/solved).toFixed(1)}%)`);
  console.log(`warm-rate 1st half: ${(100*firstHalfWarm/Math.max(1,fhSolved)).toFixed(1)}%  vs 2nd half: ${(100*secondHalfWarm/Math.max(1,shSolved)).toFixed(1)}%  (rising = the colony LEARNING)`);
  mem.save(path.join(__dirname, "..", "arc-learned.json"));
  console.log(`banked ${mem.learnings.length} learnings to arc-learned.json (+ geo payloads for Mika).`);
}
main();
