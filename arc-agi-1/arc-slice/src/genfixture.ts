import * as path from "path";
import { loadTasks } from "./loader";
import { equal, palette, background } from "./grid";
import * as G from "./generator";
// re-expose internals by re-running each template via a tagged inducer
import { Grid } from "./grid";
const tasks=loadTasks(path.join(__dirname,"..","data"));
// We can't import the private template fns, so re-detect by behaviour:
// run induceGenerator, then classify by re-deriving the delta shape.
const eqAll=(prog:any,train:any[])=>train.every((p:any)=>{const o=prog(p.input);return o&&equal(o,p.output);});
const fix:any[]=[];
for(const t of tasks){
  if(t.train.some((p:any)=>p.input.length*p.input[0].length>900)) continue;
  let g:any=null; try{g=G.induceGenerator(t.train);}catch{}
  if(g&&eqAll(g,t.train)){
    const testPass = t.test.every((te:any)=>{const o=g(te.input);return te.output&&o&&equal(o,te.output);});
    fix.push({id:t.id, testPass});
  }
}
console.log(JSON.stringify(fix,null,0));
