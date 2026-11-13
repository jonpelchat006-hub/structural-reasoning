// search.ts — wire the REAL swarm-core engine to ARC program search.
// swarm-core supplies: UCB strategy picker, FailureBuffer (tabu), LearningPath,
// sigma annealing. We supply: score, signature, mutation moves — now optionally
// seeded from the roof so search starts warm on familiar shapes.
import { runSwarmSearch } from "./swarm-core";
import { Program, MAX_LEN, run } from "./program";
import { Op, OPS, OP_NAMES } from "./dsl";
import { Pair } from "./loader";
import { score } from "./verify";
import { Fragment } from "./roof";
import { taskPalette, instantiate } from "./transfer";
import { repair } from "./bugfinder";

function mkRng(seed: number) {
  let s = seed >>> 0 || 0x9e3779b9;
  return () => { s = (Math.imul(s, 1664525) + 1013904223) >>> 0; return s / 0xffffffff; };
}
const pick = <T>(rng: () => number, arr: T[]): T => arr[Math.floor(rng() * arr.length)];

const SEARCH_OPS = OP_NAMES.filter((n) => n !== "cmap");
function randomOp(rng: () => number, pal: number[]): Op {
  const name = pick(rng, SEARCH_OPS);
  return { name, params: pick(rng, OPS[name].enumerate(pal)) };
}

function signature(prog: Program): number[] {
  const sig: number[] = [];
  for (let i = 0; i < MAX_LEN; i++) {
    const op = prog[i];
    if (!op) { sig.push(0, 0); continue; }
    sig.push(OP_NAMES.indexOf(op.name) + 1);
    sig.push(Object.values(op.params ?? {}).reduce((a, v) => a * 11 + (v + 1), 1) % 997);
  }
  return sig;
}

export interface SearchOut { best: Program; bestScore: number; }

export function searchTask(train: Pair[], seed: number, maxSteps: number, roofSeeds: Fragment[] = []): SearchOut {
  const rng = mkRng(seed);
  const pal = taskPalette(train);
  // Concrete programs from roof shapes — the warm-start population.
  const seeds: Program[] = roofSeeds.flatMap((s) => instantiate(s, pal, 24)).filter((p) => p.length);

  const strategies = {
    addOp: (p: Program): Program => p.length >= MAX_LEN ? p : [...p, randomOp(rng, pal)],
    dropOp: (p: Program): Program => p.length <= 1 ? p : p.filter((_, i) => i !== Math.floor(rng() * p.length)),
    swapOp: (p: Program): Program => {
      if (p.length === 0) return [randomOp(rng, pal)];
      const i = Math.floor(rng() * p.length);
      return p.map((o, j) => (j === i ? randomOp(rng, pal) : o));
    },
    tweakParam: (p: Program): Program => {
      if (p.length === 0) return [randomOp(rng, pal)];
      const i = Math.floor(rng() * p.length);
      const name = p[i].name;
      const variants = OPS[name].enumerate(pal);
      if (variants.length === 0) return p;
      return p.map((o, j) => (j === i ? { name, params: pick(rng, variants) } : o));
    },
    reseed: (): Program => Array.from({ length: 1 + Math.floor(rng() * 2) }, () => randomOp(rng, pal)),
    // pull a warm shape off the roof (no-op if roof empty)
    roofRecall: (p: Program): Program => seeds.length ? pick(rng, seeds) : p,
    // BUG-FINDER: diagnose the current best and apply a targeted deterministic fix
    repair: (p: Program): Program => repair(p, train, pal) ?? p,
  };

  const initial = seeds.length ? pick(rng, seeds) : [randomOp(rng, pal)];
  const res = runSwarmSearch<Program>({
    initial, score: (p) => score(p, train), signature, strategies, maxSteps,
  });
  return { best: res.best, bestScore: res.bestScore };
}

/** Cheap deterministic baseline: every single-op instantiation. */
export function bruteDepth1(train: Pair[]): SearchOut {
  const pal = taskPalette(train);
  let best: Program = [], bestScore = -1;
  for (const name of OP_NAMES) for (const params of OPS[name].enumerate(pal)) {
    const prog: Program = [{ name, params }];
    const sc = score(prog, train);
    if (sc > bestScore) { bestScore = sc; best = prog; }
    if (bestScore === 1) return { best, bestScore };
  }
  return { best, bestScore };
}

/** Enumerate single ops once; partition near-misses for targeted repair:
 *  colorCands = dims-consistent on every pair (colour remap may fix) -> cheap repair
 *  sizeCands  = dims differ (size op may fix) -> bounded, more expensive repair */
export function bruteCandidates(train: Pair[], names: string[] = OP_NAMES): { best: Program; bestScore: number; colorCands: Program[]; sizeCands: Program[] } {
  const pal = taskPalette(train);
  let best: Program = [], bestScore = -1;
  const color: { prog: Program; sc: number }[] = [];
  const size: { prog: Program; sc: number }[] = [];
  for (const name of names) for (const params of OPS[name].enumerate(pal)) {
    const prog: Program = [{ name, params }];
    let sc = 0, dimsOK = true, ran = 0;
    for (const { input, output } of train) {
      const got = run(prog, input); ran++;
      if (!got) { dimsOK = false; break; }
      if (got.length !== output.length || got[0].length !== output[0].length) { dimsOK = false; sc += 0; }
      else { let hit = 0; for (let y=0;y<got.length;y++) for (let x=0;x<got[0].length;x++) if (got[y][x]===output[y][x]) hit++; sc += hit/(got.length*got[0].length); }
    }
    sc = sc / train.length;
    if (sc > bestScore) { bestScore = sc; best = prog; }
    if (sc >= 1) continue;
    if (dimsOK) color.push({ prog, sc }); else size.push({ prog, sc });
  }
  color.sort((a,b)=>b.sc-a.sc); size.sort((a,b)=>b.sc-a.sc);
  return { best, bestScore, colorCands: color.slice(0,60).map(x=>x.prog), sizeCands: size.slice(0,80).map(x=>x.prog) };
}
