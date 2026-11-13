import { loadTasks } from "./src/loader";
import { bruteDepth1 } from "./src/search";
import { solves, score } from "./src/verify";
import { colorMapRepair, repair, diagnose } from "./src/bugfinder";
import { taskPalette } from "./src/transfer";
import { run } from "./src/program";
const tasks = loadTasks(__dirname + "/data");

// 1) MECHANISM TEST: take a brute1-solved task, deliberately corrupt the program's
//    colours, and check the bug-finder recovers it.
let recovered = 0, tested = 0;
for (const t of tasks) {
  const b = bruteDepth1(t.train);
  if (!(b.bestScore === 1 && solves(b.best, t.train))) continue;
  // corrupt: append a wrong recolor to break colours but keep shape
  const pal = taskPalette(t.train);
  if (pal.length < 2) continue;
  const corrupt = [...b.best, { name: "swap", params: { a: pal[0], b: pal[1] } }];
  if (solves(corrupt, t.train)) continue;          // swap didn't change anything
  tested++;
  const fixed = repair(corrupt, t.train, pal);
  if (fixed && solves(fixed, t.train)) recovered++;
  if (tested >= 40) break;
}
console.log(`MECHANISM: bug-finder recovered ${recovered}/${tested} deliberately colour-corrupted solutions`);

// 2) OPPORTUNITY TEST: across all tasks, how many have a near-miss (a single op)
//    that is shape-right/colour-wrong, i.e. repairable in principle?
let opportunities = 0;
import { OPS, OP_NAMES } from "./src/dsl";
for (const t of tasks) {
  const pal = taskPalette(t.train);
  let found = false;
  for (const name of OP_NAMES) for (const params of OPS[name].enumerate(pal)) {
    const prog = [{ name, params }];
    if (diagnose(prog, t.train) === "color") {       // dims right, colours wrong
      const f = colorMapRepair(prog, t.train);
      if (f && solves(f, t.train)) { found = true; break; }
    }
    if (found) break;
  }
  if (found) opportunities++;
}
console.log(`OPPORTUNITY: ${opportunities} tasks solvable by (single op + colour repair)`);
