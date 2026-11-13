// scan_recorder.ts — §22.5/§23.3: LIVE recording. Every scan calls rec(...) as it runs; each call appends
// one event to scan_events.jsonl (append-only). scan_map.ts is a pure REPLAY of this log — node mass accretes
// per event (§22), and an optional `path` (the op-sequence route used to solve) gets a traversal cost that
// DECAYS with reuse (§23.3 cached fast-route); a path reused across tasks is a transferable route (§23.4).
import * as path from "path"; import * as fs from "fs";
const LOG = path.join(__dirname, "..", "scan_events.jsonl");
export type Kind = "solved" | "overfit" | "nearmiss";
export function rec(scan: string, id: string, kind: Kind, routePath?: string) {
  try { fs.appendFileSync(LOG, JSON.stringify({ scan, id, kind, path: routePath, t: Date.now() }) + "\n"); } catch {}
}
