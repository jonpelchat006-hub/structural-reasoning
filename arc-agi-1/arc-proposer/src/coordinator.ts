// coordinator.ts — the non-LLM coordinator. Construct/Deconstruct/Plan over the
// ARC substrate, no language model anywhere. The "borrowed reasoning" is replaced
// by BENDING a branch toward the one-way-solid task: resonance picks the branch,
// the solver+bug-finder bend it to fit, the exact oracle (train pairs) is the brace.
import { Pair } from "../../arc-slice/src/loader";
import { Program } from "../../arc-slice/src/program";
import { bruteCandidates } from "../../arc-slice/src/search";
import { colorMapRepair, sizeRepair } from "../../arc-slice/src/bugfinder";
import { taskPalette } from "../../arc-slice/src/transfer";
import { solves } from "../../arc-slice/src/verify";
import { solveCodon } from "../../arc-slice/src/codon";
import { encode, Signature } from "./signature";
import { Memory } from "./memory";

export interface Solved { family: string; warm: boolean; }

// DECONSTRUCT: perceive the task as a signature.
export function deconstruct(train: Pair[]): Signature { return encode(train); }

// CONSTRUCT + BEND: try to fit a branch to the solid task; return the family that fit.
// (bending = morph/colour-map/size repair, all driven by the diff against the fixed pairs)
function constructBend(train: Pair[]): string | null {
  const c = bruteCandidates(train);
  if (c.bestScore === 1 && solves(c.best, train)) return c.best[0].name;
  const pal = taskPalette(train);
  for (const cand of c.colorCands) { const f = colorMapRepair(cand, train); if (f && solves(f, train)) return cand[0].name + "+cmap"; }
  for (const cand of [...c.colorCands.slice(0,80), ...c.sizeCands]) { const f = sizeRepair(cand, train, pal); if (f && solves(f, train)) return cand[0].name + "+size"; }
  const cd = solveCodon(train); if (cd) return cd.desc.split("(")[0];
  return null;
}

// The full coordinator loop over a task: deconstruct -> plan -> construct/bend -> verify -> learn.
export function coordinate(train: Pair[], id: string, mem: Memory): Solved | null {
  const sig = deconstruct(train);
  // PLAN: resonance memory orders which branches (families) to bend first.
  const plan = mem.retrieve(sig, 3).map(x => x.family);
  // CONSTRUCT + BEND + VERIFY (exact oracle, no model):
  const family = constructBend(train);
  if (!family) return null;
  const warm = plan.includes(family);     // did the plan predict the branch that fit?
  // LEARN: carve on landing (gated) — the colony gets smarter as it goes.
  mem.learn(sig, family, id);
  return { family, warm };
}
