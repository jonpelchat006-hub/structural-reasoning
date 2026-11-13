import * as path from "path";
import { loadTasks } from "./loader";
import { solves } from "./verify";
import { bruteCandidates } from "./search";
import { colorMapRepair, sizeRepair } from "./bugfinder";
import { taskPalette } from "./transfer";
import { solveCodon } from "./codon";
const tasks = loadTasks(path.join(__dirname,"..","data"));
function solveFast(train:any){ const c=bruteCandidates(train);
  if(c.bestScore===1&&solves(c.best,train))return true; const pal=taskPalette(train);
  for(const cand of c.colorCands){const f=colorMapRepair(cand,train);if(f&&solves(f,train))return true;}
  for(const cand of [...c.colorCands.slice(0,80),...c.sizeCands]){const f=sizeRepair(cand,train,pal);if(f&&solves(f,train))return true;}
  return false; }
const solved:string[]=[];
for(const t of tasks){ let ok=false; try{ok=solveFast(t.train);}catch{} if(!ok){try{ok=!!solveCodon(t.train);}catch{}} if(ok)solved.push(t.id); }
console.log(solved.join(" "));
