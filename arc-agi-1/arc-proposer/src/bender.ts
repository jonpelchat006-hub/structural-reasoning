// bender.ts — the tension-directed beam bender. No model. Tension = distance from
// the one-way-solid task (bug-finder diff). Operators = forces. Beam = several
// low-tension paths at once. Interpolation = compose two partials. Escape =
// keep diverse when stalled. The exact oracle closes it.
import { Pair } from "../../arc-slice/src/loader";
import { Program, run } from "../../arc-slice/src/program";
import { Op } from "../../arc-slice/src/dsl";
import { bruteCandidates } from "../../arc-slice/src/search";
import { colorMapRepair, sizeRepair } from "../../arc-slice/src/bugfinder";
import { taskPalette } from "../../arc-slice/src/transfer";
import { solves } from "../../arc-slice/src/verify";
import { cellMatch } from "../../arc-slice/src/grid";

// tension: mean per-pair distance to the solid target (0 = on it)
function tension(prog: Program, train: Pair[]): number {
  let s = 0;
  for (const { input, output } of train) {
    const got = run(prog, input);
    if (!got || got.length !== output.length || got[0].length !== output[0].length) s += 1;
    else s += 1 - cellMatch(got, output);
  }
  return s / train.length;
}

const close = (prog: Program, train: Pair[], pal: number[]): Program | null => {
  if (solves(prog, train)) return prog;
  const f = colorMapRepair(prog, train); if (f && solves(f, train)) return f;
  return null;   // sizeRepair only in the initial single-op pass (it is the slow one)
};
const closeFull = (prog: Program, train: Pair[], pal: number[]): Program | null => {
  const c = close(prog, train, pal); if (c) return c;
  const g = sizeRepair(prog, train, pal); if (g && solves(g, train)) return g;
  return null;
};

export interface BendResult { prog: Program; depth: number; }

export function bend(train: Pair[], deadline: number, beamW = 6, maxDepth = 4): BendResult | null {
  if (train.some(p=>p.input.length*p.input[0].length>600)) return null; // skip dense grids (stall the repair)
  const pal = taskPalette(train);
  const c = bruteCandidates(train);
  // immediate close on a single op?
  let r = closeFull(c.best, train, pal); if (r) return { prog: r, depth: 1 };
  for (const cand of [...c.colorCands.slice(0,30), ...c.sizeCands]) { r = closeFull(cand, train, pal); if (r) return { prog: r, depth: 1 }; }

  // FORCE POOL: ops that individually move toward the target (tension-reducing)
  const pool: Op[] = [];
  const seen = new Set<string>();
  for (const p of [c.best, ...c.colorCands, ...c.sizeCands]) {
    const op = p[0]; if (!op) continue; const k = op.name + JSON.stringify(op.params);
    if (!seen.has(k)) { seen.add(k); pool.push(op); }
  }
  const POOL = pool.slice(0, 50);

  // beam of partial paths, ranked by tension
  let beam: { prog: Program; t: number }[] = [{ prog: [], t: tension([], train) }];
  for (let depth = 1; depth <= maxDepth; depth++) {
    if (Date.now() > deadline) break;
    const succ: { prog: Program; t: number }[] = [];
    for (const b of beam) {
      if (Date.now() > deadline) break;
      for (const op of POOL) {                       // tension only (cheap) — no close() here
        const np = [...b.prog, op];
        const t = tension(np, train);
        if (t < b.t + 1e-9) succ.push({ prog: np, t });
      }
    }
    // INTERPOLATE: compose pairs of current beam partials
    for (let i = 0; i < beam.length && Date.now() <= deadline; i++) for (let j = 0; j < beam.length; j++) if (i !== j) {
      const np = [...beam[i].prog, ...beam[j].prog].slice(0, maxDepth);
      if (np.length) succ.push({ prog: np, t: tension(np, train) });
    }
    if (!succ.length) break;
    succ.sort((a, b) => a.t - b.t);
    // close() ONLY on the top-K most promising (expensive repair gated by low tension)
    for (const s of succ.slice(0, 6)) { if (Date.now() > deadline) break; const closed = close(s.prog, train, pal); if (closed) return { prog: closed, depth }; }
    // ESCAPE: keep best beamW + a couple diverse first-ops
    const top = succ.slice(0, beamW);
    const firsts = new Set(top.map(s => s.prog[0]?.name));
    for (const s of succ.slice(beamW)) { if (top.length >= beamW + 2) break; if (!firsts.has(s.prog[0]?.name)) { top.push(s); firsts.add(s.prog[0]?.name); } }
    beam = top;
  }
  return null;
}
