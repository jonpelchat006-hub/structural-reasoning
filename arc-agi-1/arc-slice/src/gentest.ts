import * as path from "path";
import { loadTasks } from "./loader";
import { induceGenerator } from "./generator";
import { equal } from "./grid";
const tasks=loadTasks(path.join(__dirname,"..","data"));
const ids=["22eb0ac0","253bf280","3aa6fb7a","60b61512","6d75e8bb","dbc1a6ce","22168020","ded97339"];
for(const id of ids){ const t=tasks.find(x=>x.id===id)!; const g=induceGenerator(t.train);
  if(!g){console.log(id,"NO-PROG");continue;}
  let all=true,n=0; for(const te of t.test){ n++; const got=g(te.input); if(!(te.output&&got&&equal(got,te.output)))all=false; }
  console.log(id, all?`TEST-PASS (${n})`:"TEST-FAIL"); }
