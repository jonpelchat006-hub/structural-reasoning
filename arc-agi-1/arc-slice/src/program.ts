// program.ts — a candidate "rule" is a short pipeline of ops.
import { Grid } from "./grid";
import { Op, applyOp } from "./dsl";

export type Program = Op[];

export const MAX_LEN = 4;

/** Run the whole pipeline; null if any stage is illegal. */
export function run(prog: Program, g: Grid): Grid | null {
  let cur: Grid | null = g;
  for (const op of prog) {
    cur = applyOp(op, cur);
    if (!cur) return null;
  }
  return cur;
}

export function fmt(prog: Program): string {
  if (prog.length === 0) return "identity";
  return prog.map((o) => {
    const ps = Object.entries(o.params).map(([k, v]) => `${k}=${v}`).join(",");
    return ps ? `${o.name}(${ps})` : o.name;
  }).join(" -> ");
}
