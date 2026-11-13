// morph.ts — the corkscrew. Lift a solved composition into a role-slot TEMPLATE
// (structure fixed, colors abstracted), accumulate templates across tasks, and
// when applying to a NEW task, MORPH each slot into that task's own language
// (bind roles -> the task's concrete colors). This is the language module's
// translate step doing the binding the literal roof never could.
import { Program } from "./program";
import { Op } from "./dsl";
import { Pair } from "./loader";
import { score, solves } from "./verify";

// which op params are "colors" (the part that must be translated per task)
const COLOR_PARAMS = new Set(["bg", "c", "from", "to", "fill", "a", "b", "col", "out"]);

export interface TaskFeatures { mc: number; lc: number; palette: number[]; }

export function taskFeatures(train: Pair[]): TaskFeatures {
  const count = new Map<number, number>();
  for (const p of train) for (const row of p.input) for (const v of row) count.set(v, (count.get(v) ?? 0) + 1);
  let mc = 0, mcN = -1, lc = 0, lcN = Infinity;
  for (const [v, n] of count) { if (n > mcN) { mcN = n; mc = v; } if (n < lcN) { lcN = n; lc = v; } }
  return { mc, lc, palette: [...count.keys()].sort((a, b) => a - b) };
}

interface Slot { roles: string[]; literal: number; } // roles in {"MC","LC"}
interface TOp { name: string; fixed: Record<string, number>; slots: Record<string, Slot>; }
export interface Template { ops: TOp[]; heat: number; tasks: number; }
export type Templates = Record<string, Template>;

/** structural skeleton key — ignores literal colors, so different-coloured
 * solutions of the same shape collapse to one template (the corkscrew merge). */
export function keyOf(ops: TOp[]): string {
  return ops.map((o) => {
    const fx = Object.entries(o.fixed).sort().map(([k, v]) => `${k}=${v}`).join(",");
    const sl = Object.keys(o.slots).sort().join("+");
    return `${o.name}|${fx}|${sl}`;
  }).join(">");
}

/** lift a concrete program into a template against the task it solved. */
export function lift(prog: Program, feats: TaskFeatures): TOp[] {
  return prog.map((op: Op) => {
    const fixed: Record<string, number> = {};
    const slots: Record<string, Slot> = {};
    for (const [k, v] of Object.entries(op.params)) {
      if (COLOR_PARAMS.has(k)) {
        const roles: string[] = [];
        if (v === feats.mc) roles.push("MC");
        if (v === feats.lc) roles.push("LC");
        slots[k] = { roles, literal: v };
      } else fixed[k] = v;
    }
    return { name: op.name, fixed, slots };
  });
}

/** imprint a solved program into the template roof (length>=2 only — single ops
 * are already covered by the deterministic pass). */
export function imprintTemplate(t: Templates, prog: Program, feats: TaskFeatures): void {
  if (prog.filter((o) => o.name !== "identity").length < 2) return;
  const ops = lift(prog, feats);
  const k = keyOf(ops);
  const e = t[k];
  if (!e) { t[k] = { ops, heat: 1, tasks: 1 }; return; }
  e.heat += 1; e.tasks += 1;
  // union slot roles across tasks (the corkscrew accumulates how slots varied)
  e.ops.forEach((o, i) => {
    for (const key of Object.keys(o.slots)) {
      const merged = new Set([...o.slots[key].roles, ...(ops[i].slots[key]?.roles ?? [])]);
      o.slots[key].roles = [...merged];
    }
  });
}

export function hottestTemplates(t: Templates, n: number): Template[] {
  return Object.values(t).sort((a, b) => b.heat * Math.log2(1 + b.tasks) - a.heat * Math.log2(1 + a.tasks)).slice(0, n);
}

/** candidate concrete values for a slot, in the NEW task's language. */
function slotValues(s: Slot, f: TaskFeatures): number[] {
  const out = new Set<number>();
  for (const r of s.roles) { if (r === "MC") out.add(f.mc); if (r === "LC") out.add(f.lc); }
  out.add(s.literal);                       // literal fallback (some colors are fixed)
  if (out.size === 0) for (const c of f.palette) out.add(c);  // free slot
  return [...out];
}

/** morph a template into concrete programs for a task (bounded). */
export function bind(tpl: Template, f: TaskFeatures, cap = 160): Program[] {
  let progs: Program[] = [[]];
  for (const o of tpl.ops) {
    const slotKeys = Object.keys(o.slots);
    const valueLists = slotKeys.map((k) => slotValues(o.slots[k], f));
    const next: Program[] = [];
    for (const base of progs) {
      // cartesian over this op's slots
      let combos: Record<string, number>[] = [{ ...o.fixed }];
      slotKeys.forEach((k, idx) => {
        const grown: Record<string, number>[] = [];
        for (const c of combos) for (const v of valueLists[idx]) grown.push({ ...c, [k]: v });
        combos = grown;
      });
      for (const params of combos) { next.push([...base, { name: o.name, params }]); if (next.length >= cap) break; }
      if (next.length >= cap) break;
    }
    progs = next;
    if (progs.length >= cap) break;
  }
  return progs;
}

/** morph pass: try the hottest templates, bound into this task's language. */
export function morphPass(tpls: Template[], train: Pair[]): { prog: Program } | null {
  const f = taskFeatures(train);
  for (const tpl of tpls) {
    for (const prog of bind(tpl, f)) {
      if (score(prog, train) === 1 && solves(prog, train)) return { prog };
    }
  }
  return null;
}
