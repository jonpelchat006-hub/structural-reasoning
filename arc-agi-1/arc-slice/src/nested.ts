// nested.ts — depth-bounded recursive synthesis (the seven-body fractal interior).
// A combinator carries a BODY sub-program synthesised by recursion. Placing a
// combinator = entering a body's interior; the inner search must "close" (map
// every object sub-pair exactly, or via the bug-finder). Depth cap = 3 (3-6-9).
import { Grid, dims, clone, equal, palette, background } from "./grid";
import { components, blank } from "./objects";
import { Op, applyOp } from "./dsl";
import { Program, run as runFlat } from "./program";
import { Pair } from "./loader";
import { bruteCandidates } from "./search";
import { OP_NAMES } from "./dsl";
const BASE_OPS = OP_NAMES.filter((n)=>!["keepTopK","mapTopK","selectUnique","selectMajority","mapObjects","cmap"].includes(n));
import { colorMapRepair, sizeRepair } from "./bugfinder";
import { solves as solvesFlat } from "./verify";

export type Node =
  | { kind: "op"; op: Op }
  | { kind: "mapObjects"; bg: number; body: NestedProgram }
  | { kind: "mapTopK"; bg: number; by: number; k: number; body: NestedProgram };
export type NestedProgram = Node[];

// ── interpreter ──
function objSub(g: Grid, o: { y0:number;y1:number;x0:number;x1:number }): Grid {
  const out: Grid = [];
  for (let y=o.y0;y<=o.y1;y++) out.push(g[y].slice(o.x0,o.x1+1));
  return out;
}
function ranked(objs: any[], by: number, g: Grid, bg: number): any[] {
  if (by===0) return [...objs].sort((a,b)=>b.size-a.size);
  if (by===1) return [...objs].sort((a,b)=>a.size-b.size);
  const cc=new Map<number,number>(); for (const row of g) for (const v of row) if(v!==bg) cc.set(v,(cc.get(v)??0)+1);
  return [...objs].sort((a,b)=>(cc.get(a.color)??0)-(cc.get(b.color)??0));
}

export function runNode(node: Node, g: Grid): Grid | null {
  if (node.kind === "op") return applyOp(node.op, g);
  const objs = components(g, node.bg, "blob");
  if (objs.length === 0 || objs.length > 40) return null;
  const chosen = node.kind === "mapTopK" ? new Set(ranked(objs, node.by, g, node.bg).slice(0, node.k)) : new Set(objs);
  const out = clone(g);
  for (const o of objs) {
    if (!chosen.has(o)) continue;
    const sub = objSub(g, o);
    const t = runNested(node.body, sub);
    if (!t || t.length !== sub.length || t[0].length !== sub[0].length) return null; // body must preserve bbox
    for (const [y,x] of o.cells) out[y][x] = node.bg;
    for (let y=0;y<t.length;y++) for (let x=0;x<t[0].length;x++) if (t[y][x] !== node.bg) out[o.y0+y][o.x0+x] = t[y][x];
  }
  return out;
}
export function runNested(prog: NestedProgram, g: Grid): Grid | null {
  let cur: Grid | null = g;
  for (const n of prog) { cur = runNode(n, cur); if (!cur) return null; }
  return cur;
}
export function solvesNested(prog: NestedProgram, pairs: Pair[]): boolean {
  for (const { input, output } of pairs) { const got = runNested(prog, input); if (!got || !equal(got, output)) return false; }
  return true;
}

export function fmtNested(p: NestedProgram): string {
  return p.map((n) => n.kind === "op"
    ? (Object.keys(n.op.params).length ? `${n.op.name}(${Object.entries(n.op.params).map(([k,v])=>k+"="+v).join(",")})` : n.op.name)
    : `${n.kind}[bg=${n.bg}${n.kind==="mapTopK"?`,by=${n.by},k=${n.k}`:""}]{ ${fmtNested(n.body)} }`
  ).join(" -> ");
}

// ── flat base: single op (exact) + bug-finder repair, returned as op-nodes ──
function asNodes(p: Program): NestedProgram { return p.map((op) => ({ kind: "op", op } as Node)); }

export function solveFlatLite(pairs: Pair[]): NestedProgram | null {
  const c = bruteCandidates(pairs, BASE_OPS);
  if (c.bestScore === 1 && solvesFlat(c.best, pairs)) return asNodes(c.best);
  for (const cand of c.colorCands) { const f = colorMapRepair(cand, pairs); if (f && solvesFlat(f, pairs)) return asNodes(f); }
  return null;
}

export function solveFlat(pairs: Pair[]): NestedProgram | null {
  const c = bruteCandidates(pairs);
  if (c.bestScore === 1 && solvesFlat(c.best, pairs)) return asNodes(c.best);
  for (const cand of c.colorCands) { const f = colorMapRepair(cand, pairs); if (f && solvesFlat(f, pairs)) return asNodes(f); }
  const pal = palette(pairs[0].input);
  for (const cand of [...c.colorCands.slice(0,16), ...c.sizeCands]) { const f = sizeRepair(cand, pairs, pal); if (f && solvesFlat(f, pairs)) return asNodes(f); }
  return null;
}

// object sub-pairs for in-place per-object mapping (input region -> same region in output)
function objectSubPairs(pairs: Pair[], bg: number, topK: number | null, by: number): Pair[] | null {
  const out: Pair[] = [];
  for (const { input, output } of pairs) {
    if (input.length !== output.length || input[0].length !== output[0].length) return null;
    let objs = components(input, bg, "blob");
    if (objs.length === 0 || objs.length > 40) return null;
    if (topK != null) objs = ranked(objs, by, input, bg).slice(0, topK);
    for (const o of objs) out.push({ input: objSub(input, o), output: objSub(output, o) });
  }
  return out.length >= 2 ? out : null;
}

// ── the recursive depth-bounded synthesiser ──
function bgCandidates(pairs: Pair[]): number[] {
  const s = new Set<number>([background(pairs[0].input), 0]);
  return [...s];
}

export function solveNested(pairs: Pair[], depth: number, deadline = Infinity, top = true): NestedProgram | null {
  if (Date.now() > deadline) return null;
  const flat = top ? solveFlat(pairs) : solveFlatLite(pairs);
  if (flat) return flat;
  if (depth <= 0) return null;

  for (const bg of bgCandidates(pairs)) {
    if (Date.now() > deadline) return null;
    const sub = objectSubPairs(pairs, bg, null, 0);
    if (!sub) continue;
    const body = solveNested(sub, depth - 1, deadline, false);
    if (body) { const prog: NestedProgram = [{ kind: "mapObjects", bg, body }]; if (solvesNested(prog, pairs)) return prog; }
  }
  for (const bg of bgCandidates(pairs)) for (const by of [0,1]) for (const k of [1,2]) {
    if (Date.now() > deadline) return null;
    const sub = objectSubPairs(pairs, bg, k, by);
    if (!sub) continue;
    const body = solveNested(sub, depth - 1, deadline, false);
    if (body) { const prog: NestedProgram = [{ kind: "mapTopK", bg, by, k, body }]; if (solvesNested(prog, pairs)) return prog; }
  }
  return null;
}
