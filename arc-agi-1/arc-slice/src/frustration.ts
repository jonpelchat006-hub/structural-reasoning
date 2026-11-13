// frustration.ts — the last-resort "irrational" phase. When the structured,
// deterministic moves stall, switch to a golden-ratio low-discrepancy burst:
// quasi-random program draws that cover op/param space MORE evenly than pure
// pseudo-random (additive recurrence with the golden conjugate). This is
// basin-hopping with an irrational kick — "try something completely different."
import { Program, MAX_LEN, run } from "./program";
import { OPS, OP_NAMES } from "./dsl";
import { Pair } from "./loader";
import { score, solves } from "./verify";
import { taskPalette } from "./transfer";

const PHI_CONJ = 0.6180339887498949; // 1/phi — the irrational step

/** Golden-ratio additive recurrence in [0,1): low-discrepancy, deterministic. */
function goldenSeq(seed: number) {
  let x = (seed * PHI_CONJ) % 1;
  return () => { x = (x + PHI_CONJ) % 1; return x; };
}
const at = <T>(u: number, arr: T[]): T => arr[Math.min(arr.length - 1, Math.floor(u * arr.length))];

export function frustrationSearch(train: Pair[], samples: number, seed = 7): { best: Program; bestScore: number } {
  const pal = taskPalette(train);
  const g = goldenSeq(seed);
  let best: Program = [], bestScore = -1;
  for (let i = 0; i < samples; i++) {
    const len = 1 + Math.floor(g() * MAX_LEN);          // wilder: full-depth programs
    const prog: Program = [];
    for (let j = 0; j < len; j++) {
      const name = at(g(), OP_NAMES);
      const params = at(g(), OPS[name].enumerate(pal));
      prog.push({ name, params });
    }
    if (run(prog, train[0].input) == null) continue;
    const sc = score(prog, train);
    if (sc > bestScore) { bestScore = sc; best = prog; if (sc === 1 && solves(prog, train)) break; }
  }
  return { best, bestScore };
}
