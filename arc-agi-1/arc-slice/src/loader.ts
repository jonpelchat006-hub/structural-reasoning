// loader.ts — read ARC task JSON from data/.
import * as fs from "fs";
import * as path from "path";
import { Grid } from "./grid";

export interface Pair { input: Grid; output: Grid; }
export interface Task { id: string; train: Pair[]; test: { input: Grid; output?: Grid }[]; }

export function loadTasks(dir: string): Task[] {
  const files = fs.readdirSync(dir).filter((f) => f.endsWith(".json")).sort();
  return files.map((f) => {
    const j = JSON.parse(fs.readFileSync(path.join(dir, f), "utf8"));
    return { id: f.replace(/\.json$/, ""), train: j.train, test: j.test };
  });
}
