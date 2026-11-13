// transfer.ts — the bridge. Turn roof SHAPES into concrete candidate programs
// for a new task (params re-derived from this task's palette), and seed search.
import { Program } from "./program";
import { Op, OPS } from "./dsl";
import { Pair } from "./loader";
import { score, solves } from "./verify";
import { Fragment } from "./roof";
import { palette } from "./grid";

export function taskPalette(train: Pair[]): number[] {
  const s = new Set<number>();
  for (const p of train) { for (const c of palette(p.input)) s.add(c); for (const c of palette(p.output)) s.add(c); }
  return [...s].sort((a, b) => a - b);
}

/** All concrete programs for a shape, bounded so multi-op shapes don't explode. */
export function instantiate(shape: Fragment, pal: number[], cap = 400): Program[] {
  let progs: Program[] = [[]];
  for (const name of shape) {
    const variants = OPS[name]?.enumerate(pal) ?? [{}];
    const next: Program[] = [];
    for (const base of progs) for (const params of variants) {
      next.push([...base, { name, params }]);
      if (next.length >= cap) break;
    }
    progs = next;
    if (progs.length >= cap) break;
  }
  return progs;
}

/** Roof pass: try the hottest learned shapes on this task before searching. */
export function roofPass(shapes: Fragment[], train: Pair[]): { prog: Program } | null {
  const pal = taskPalette(train);
  for (const shape of shapes) {
    for (const prog of instantiate(shape, pal)) {
      if (score(prog, train) === 1 && solves(prog, train)) return { prog };
    }
  }
  return null;
}
