import * as path from "path"; import {loadTasks} from "./loader";
import {components,Obj} from "./objects";
const tr=loadTasks(path.join(__dirname,"..","data"));
const dimsEq=(a:any,b:any)=>a.length===b.length&&a[0].length===b[0].length;
let sameDims=0,moveLike=0;
for(const t of tr){if(!t.test)continue;if(!t.train.every((p:any)=>dimsEq(p.input,p.output)))continue;sameDims++;
  // does object multiset (shape+color) survive but positions change? = a move task
  const p=t.train[0];const io=components(p.input,0,"blob"),oo=components(p.output,0,"blob");
  const sig=(o:Obj)=>o.color+":"+o.cells.map(([y,x]:any)=>(y-o.y0)+","+(x-o.x0)).sort().join(";");
  const si=io.map(sig).sort().join("|"),so=oo.map(sig).sort().join("|");
  if(io.length&&io.length===oo.length&&si===so && JSON.stringify(p.input)!==JSON.stringify(p.output))moveLike++;
}
console.log("same-dims train tasks:",sameDims,"  object-preserving-move-like:",moveLike);
