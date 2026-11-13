import { loadTasks } from "./src/loader";
import { bruteDepth1 } from "./src/search";
import { solves } from "./src/verify";
import { fmt } from "./src/program";
const tasks = loadTasks(__dirname + "/data");
const map = new Map(tasks.map(t=>[t.id,t]));
for (const id of ["3c9b0459","6150a2bd","74dd1130","68b16354","ed36ccf7","9dfd6313","a416b8f3"]) {
  const t = map.get(id);
  if (!t) { console.log(id, "NOT FOUND"); continue; }
  const b = bruteDepth1(t.train);
  console.log(id, "best=", b.bestScore.toFixed(3), "solves=", solves(b.best,t.train), "|", fmt(b.best),
    "| in", t.train[0].input.length+"x"+t.train[0].input[0].length, "-> out", t.train[0].output.length+"x"+t.train[0].output[0].length);
}
let n=0; for (const t of tasks) { const b=bruteDepth1(t.train); if (b.bestScore===1 && solves(b.best,t.train)) n++; }
console.log("brute depth-1 solves", n, "of", tasks.length);
