// memory.ts — the resonance memory store. Banks {signature -> winning family}
// learnings and retrieves by RESONANCE (nearest signatures vote). Persisted to a
// SEPARATE arc-learned.json in geo/registry-ready shape; the live colony memory
// and registry are never touched. Mika can ingest the geoPayload() later.
import * as fs from "fs";
import { Signature, distance, sigKey } from "./signature";

export interface Learning { sigKey: string; light: number[]; dark: number[]; family: string; tasks: string[]; count: number; }

export class Memory {
  learnings: Learning[] = [];

  /** carve on a landing: bank a solved task's signature -> family (gated, not every bounce). */
  learn(sig: Signature, family: string, taskId: string): void {
    const k = sigKey(sig) + "|" + family;
    let e = this.learnings.find(l => sigKey({ light: l.light, dark: l.dark } as Signature) + "|" + l.family === k);
    if (!e) { e = { sigKey: sigKey(sig), light: sig.light, dark: sig.dark, family, tasks: [], count: 0 }; this.learnings.push(e); }
    if (!e.tasks.includes(taskId)) { e.tasks.push(taskId); e.count++; }
  }

  /** retrieve a ranked list of families by resonance vote (nearest signatures, weighted). */
  retrieve(sig: Signature, k = 3): { family: string; weight: number }[] {
    const vote = new Map<string, number>();
    for (const l of this.learnings) {
      const d = distance(sig, { light: l.light, dark: l.dark });
      const w = l.count / (1 + d * d);                 // closer + more-seen = stronger
      vote.set(l.family, (vote.get(l.family) ?? 0) + w);
    }
    return [...vote.entries()].map(([family, weight]) => ({ family, weight }))
      .sort((a, b) => b.weight - a.weight).slice(0, k);
  }

  save(path: string): void {
    fs.writeFileSync(path, JSON.stringify({
      _meta: { format: "arc-learned", version: "1.0.0", note: "SEPARATE from live registry.json / memory-geo; merge manually when trusted" },
      learnings: this.learnings,
    }, null, 2));
  }
  load(path: string): void { try { this.learnings = JSON.parse(fs.readFileSync(path, "utf8")).learnings ?? []; } catch {} }

  /** geo-ready payloads (one memory spore per learning) for Mika's geo encoder. */
  geoPayload(): { topic: string; facts: string[]; sources: string[] }[] {
    return this.learnings.map(l => ({
      topic: `ARC resonance: ${l.family}`,
      facts: [`light=${l.light.join(",")} dark=${l.dark.join(",")} -> solution family "${l.family}" (seen ${l.count}x)`],
      sources: l.tasks.map(t => `ARC-AGI-1 task ${t}`),
    }));
  }
}
