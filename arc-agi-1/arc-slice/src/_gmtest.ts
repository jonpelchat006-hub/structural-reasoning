import * as path from "path"; import * as fs from "fs";
import {loadTasks} from "./loader";
// reuse learnMove by importing the module's function isn't exported; re-run its logic inline is heavy.
// Instead: monkey-test via requiring compiled logic — simplest: copy detection here quickly.
import {components,Obj} from "./objects";
const eqG=(a:any,b:any)=>!!a&&!!b&&a.length===b.length&&a[0].length===b[0].length&&a.every((r:any,i:number)=>r.every((v:any,j:number)=>v===b[i][j]));
const dimsEq=(a:any,b:any)=>a.length===b.length&&a[0].length===b[0].length;
function gravOffset(o:Obj,R:number,C:number,dir:number):[number,number]{if(dir===0)return[-o.y0,0];if(dir===1)return[R-1-o.y1,0];if(dir===2)return[0,-o.x0];return[0,C-1-o.x1];}
function place(g:any,bg:number,objs:Obj[],off:Map<Obj,[number,number]>){const out=g.map((r:any)=>r.map(()=>bg));const R=g.length,C=g[0].length;for(const o of objs){const[dy,dx]=off.get(o)||[0,0];for(const[y,x]of o.cells){const ny=y+dy,nx=x+dx;if(ny<0||ny>=R||nx<0||nx>=C)return null;out[ny][nx]=g[y][x];}}return out;}
const tr=loadTasks(path.join(__dirname,"..","data"));
let grav=0,ids:string[]=[];
for(const t of tr){if(!t.test)continue;if(!t.train.every((p:any)=>dimsEq(p.input,p.output)))continue;
  for(const bg of [0]){for(const mode of ["blob"] as const){for(let dir=0;dir<4;dir++){let ok=true;
    for(const p of t.train){const objs=components(p.input,bg,mode);if(!objs.length){ok=false;break;}const off=new Map<Obj,[number,number]>();objs.forEach(o=>off.set(o,gravOffset(o,p.input.length,p.input[0].length,dir)));const got=place(p.input,bg,objs,off);if(!got||!eqG(got,p.output)){ok=false;break;}}
    if(ok){grav++;ids.push(t.id+":grav"+dir);break;}}}}}
console.log("gravity-solves on training:",grav, ids.slice(0,8).join(" "));
