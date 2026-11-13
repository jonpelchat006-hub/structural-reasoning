import * as path from "path";
import { loadTasks } from "./loader";
import { OPS } from "./dsl";
import { Grid } from "./grid";
const tasks=loadTasks(path.join(__dirname,"..","data"));
const eq=(a:Grid,b:Grid)=>a.length===b.length&&a.every((r,i)=>r.length===b[i].length&&r.every((v,j)=>v===b[i][j]));
const probe=["antiTranspose","extractCell","scaleByCount","borderObjects","smoothNeighbor","rotateObjects"];
for(const name of probe){
  const op=(OPS as any)[name]; const params=op.enumerate([0,1,2,3,4,5,6,7,8,9]);
  let solo=0; const hits:string[]=[];
  for(const t of tasks){
    if(t.train.some(p=>p.input.length*p.input[0].length>900)) continue;
    let ok=false;
    for(const pr of params){
      try{
        const outs=t.train.map(p=>op.fn(p.input,pr));
        if(outs.every((o:Grid|null,i:number)=>o&&eq(o!,t.train[i].output))){ok=true;break;}
      }catch{}
    }
    if(ok){solo++;hits.push(t.id);}
  }
  console.log(name.padEnd(15), "solo-solves:", solo, hits.slice(0,8).join(" "));
}
