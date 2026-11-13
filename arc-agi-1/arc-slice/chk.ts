import { loadTasks } from "./src/loader";
import { OPS } from "./src/dsl";
import { score, solves } from "./src/verify";
import { palette } from "./src/grid";
const tasks = loadTasks(__dirname + "/data");
for (const name of ["selectUnique","selectMajority","mapObjects"]) {
  let hits=0; const ex:string[]=[];
  for (const t of tasks) {
    const pal=[...new Set(t.train.flatMap(p=>[...palette(p.input),...palette(p.output)]))];
    for (const params of OPS[name].enumerate(pal)) {
      const prog=[{name,params}];
      if (score(prog,t.train)===1 && solves(prog,t.train)){hits++;ex.push(t.id);break;}
    }
  }
  console.log(name,"solo-solves:",hits, ex.slice(0,5).join(","));
}
