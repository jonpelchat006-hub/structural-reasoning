// kerneltier.ts — the "kernel tier": Lean-Kernel-Challenge-style gates for ARC rules.
//
// In the Lean Kernel Challenge a submission counts only if (1) it is total, (2) a proof covers
// EVERY input, not just the test cases ("passing tests is not enough"), and (3) it is not a lookup
// table of answers. Only then is its replay cost ranked. ARC has no proofs, so this tier uses the
// closest checkable stand-ins, and — unlike runall.ts — it never looks at the test output to pick
// the program (the stage is the FIRST one whose program fits train; test is only scored after).
//
//   K1 TOTAL      the program returns a grid (no null / exception) on every train and test input
//   K2 UNIVERSAL  leave-one-out re-induction: for every train pair i, the same stage re-induced
//                 from the OTHER pairs must reproduce pair i (the rule is forced by the data, not
//                 memorised from all of it)  — the "∀ n" stand-in
//   K3 NO-TABLE   the re-induced LOO programs must agree with the full program on the test input
//                 (a rule that changes its answer when one example is removed was a lookup table)
//   COST          median wall-ms of 3 replays of the program on the test input (the leaderboard metric)
//
// Question this answers: does passing the kernel gates predict TEST success better than train-fit alone?
//   usage: npx tsx src/kerneltier.ts [data|data-eval] [limit]
import * as path from "path";
import * as fs from "fs";
import { loadTasks } from "./loader";
import { solves as solvesTrain } from "./verify";
import { bruteCandidates } from "./search";
import { colorMapRepair, sizeRepair } from "./bugfinder";
import { taskPalette } from "./transfer";
import { solveCodon } from "./codon";
import { synthGenerator } from "./gen2";
import { synthAntimatter } from "./antimatter";
import { solveDiscovery } from "./discover";
import { solveCycle } from "./cycle";
type Grid = number[][];
type Prog = (g: Grid) => Grid | null;
const dirName = process.argv[2] ?? "data";
const limit = Number(process.argv[3] ?? 400);
const tasks = loadTasks(path.join(__dirname, "..", dirName)).slice(0, limit);
const eqG = (a: Grid | null, b: Grid | null) => !!a && !!b && a.length === b.length && a[0].length === b[0].length && a.every((r, i) => r.every((v, j) => v === b[i][j]));
const safe = (p: Prog, g: Grid): Grid | null => { try { const o = p(g); return Array.isArray(o) && o.length && Array.isArray(o[0]) ? o : null; } catch { return null; } };

function fastProg(train: any[]): Prog | null {
  const c = bruteCandidates(train); const pal = taskPalette(train);
  const run = (prog: any) => (g: Grid) => { try { let cur = g; for (const s of prog) { const { applyOp } = require("./dsl"); const o = applyOp(s, cur); if (!o) return null; cur = o; } return cur; } catch { return null; } };
  if (c.bestScore === 1 && solvesTrain(c.best, train)) return run(c.best);
  for (const cand of c.colorCands) { const f = colorMapRepair(cand, train); if (f && solvesTrain(f, train)) return run(f); }
  for (const cand of [...c.colorCands.slice(0, 80), ...c.sizeCands]) { const f = sizeRepair(cand, train, pal); if (f && solvesTrain(f, train)) return run(f); }
  return null;
}
const STAGES: [string, (train: any[]) => Prog | null][] = [
  ["fast", tr => fastProg(tr)],
  ["codon", tr => { const c = solveCodon(tr); return c ? c.fn : null; }],
  ["generator", tr => { const r = synthGenerator(tr); return r ? r.prog : null; }],
  ["antimatter", tr => { const r = synthAntimatter(tr); return r ? r.prog : null; }],
  ["discovery", tr => { const r = solveDiscovery(tr, undefined, true); return r ? r.prog : null; }],
  ["cycle", tr => solveCycle(tr)],
];
const fitsTrain = (p: Prog, train: any[]) => train.every((pr: any) => eqG(safe(p, pr.input), pr.output));

type Row = { id: string; stage: string; k1: boolean; k2: boolean; k3: boolean; kernel: boolean; test: boolean; costMs: number; nTrain: number };
const rows: Row[] = []; const t0 = Date.now(); let i = 0;
for (const t of tasks) {
  if (i++ % 50 === 0) process.stderr.write(`[${i}/${tasks.length}] ${((Date.now() - t0) / 1000).toFixed(0)}s\n`);
  const cells = (g: any) => g.length * g[0].length;
  const maxc = Math.max(...t.train.flatMap((p: any) => [cells(p.input), cells(p.output)]), ...t.test.map((te: any) => cells(te.input)));
  if (maxc > 450) continue;
  // first stage whose program fits train — chosen WITHOUT looking at the test output
  let stage = "", prog: Prog | null = null, fn: ((tr: any[]) => Prog | null) | null = null;
  for (const [name, f] of STAGES) { let p: Prog | null = null; try { p = f(t.train); } catch { } if (p && fitsTrain(p, t.train)) { stage = name; prog = p; fn = f; break; } }
  if (!prog || !fn) continue;
  const testOuts = t.test.map((te: any) => safe(prog!, te.input));
  const k1 = t.train.every((pr: any) => safe(prog!, pr.input) !== null) && testOuts.every((o: Grid | null) => o !== null);
  const test = t.test.every((te: any, j: number) => te.output && eqG(testOuts[j], te.output));
  let k2 = t.train.length >= 2, k3 = k2;
  if (k2) for (let h = 0; h < t.train.length; h++) {
    const sub = t.train.filter((_: any, j: number) => j !== h);
    let p: Prog | null = null; try { p = fn(sub); } catch { }
    if (!p || !eqG(safe(p, t.train[h].input), t.train[h].output)) { k2 = false; k3 = false; break; }
    if (!t.test.every((te: any, j: number) => eqG(safe(p!, te.input), testOuts[j]))) k3 = false;
  }
  const ms: number[] = [];
  for (let r = 0; r < 3; r++) { const s = process.hrtime.bigint(); for (const te of t.test) safe(prog, te.input); ms.push(Number(process.hrtime.bigint() - s) / 1e6); }
  ms.sort((a, b) => a - b);
  rows.push({ id: t.id, stage, k1, k2, k3, kernel: k1 && k2 && k3, test, costMs: +ms[1].toFixed(3), nTrain: t.train.length });
}
const n = rows.length, cnt = (f: (r: Row) => boolean) => rows.filter(f).length;
const prec = (sel: Row[]) => sel.length ? `${sel.filter(r => r.test).length}/${sel.length} = ${(100 * sel.filter(r => r.test).length / sel.length).toFixed(1)}%` : "—";
const acc = rows.filter(r => r.kernel), rej = rows.filter(r => !r.kernel);
const out = [
  `=== KERNEL TIER on ${dirName} (${tasks.length} tasks, ${((Date.now() - t0) / 1000).toFixed(0)}s) ===`,
  `train-fit programs (stage chosen without test): ${n}`,
  `  K1 total: ${cnt(r => r.k1)}   K2 leave-one-out: ${cnt(r => r.k2)}   K3 stable answer: ${cnt(r => r.k3)}`,
  `  KERNEL-ACCEPTED (K1&K2&K3): ${acc.length}`,
  `test precision  — train-fit alone: ${prec(rows)}`,
  `                — kernel-accepted: ${prec(acc)}`,
  `                — kernel-rejected: ${prec(rej)}`,
  `test solves lost by the gate (correct but rejected): ${rej.filter(r => r.test).length}`,
  `wrong answers blocked by the gate: ${rej.filter(r => !r.test).length}`,
  `leaderboard (kernel-accepted & test-correct, cheapest replay first):`,
  ...acc.filter(r => r.test).sort((a, b) => a.costMs - b.costMs).slice(0, 10).map(r => `  ${r.id} ${r.stage} ${r.costMs}ms`),
];
console.log(out.join("\n"));
fs.writeFileSync(path.join(__dirname, "..", `kernel_tier_${dirName}.json`), JSON.stringify({ summary: out, rows }, null, 1));
