// closer_scan.ts — §18.9: the residual-CLOSER as a learned ENERGY-TRANSFER ORIENTATION. The triangulated
// wall (§18.8) needs a LEARNED-parameter close; Jonathan's insight makes the parameter interpretable and
// small: the sheet slides, but now in more ORIENTATIONS — 8 directions (axes + 45° diagonals) and ROW×COL
// MIXTURES (a cell lit by its row AND column = the tilted x+z sheet). Anchor at the near-miss, then learn
// WHICH orientation closes the residual. New territory: diagonal + mixture transfers the fixed set lacked.
import * as path from "path"; import * as fs from "fs";
import { loadTasks } from "./loader";
import { applyOp } from "./dsl";
import { bounceSearchDiag } from "./bounce_scan";
type Grid = number[][];
const eqG=(a:Grid,b:Grid)=>!!a&&!!b&&a.length===b.length&&a[0].length===b[0].length&&a.every((r,i)=>r.every((v,j)=>v===b[i][j]));
const build=(prog:[string,any][])=>(g:Grid)=>{let c:Grid|null=g;for(const[o,p]of prog){if(!c)return null;try{c=applyOp({name:o,params:p} as any,c);}catch{return null;}}return c;};

// ── oriented energy-transfer ops (the sheets, now in 8 orientations + mixtures) ──
const DIRS:[number,number][]=[[-1,0],[1,0],[0,1],[0,-1],[-1,1],[-1,-1],[1,1],[1,-1]]; // N S E W NE NW SE SW
// slide-fill: each bg cell takes the colour of the first non-bg cell along direction d (a cast shadow)
const slideFill=(d:number)=>(g:Grid):Grid=>{ const R=g.length,C=g[0].length,[dy,dx]=DIRS[d]; const o=g.map(r=>r.slice());
  for(let y=0;y<R;y++)for(let x=0;x<C;x++){ if(g[y][x]!==0)continue; let ny=y+dy,nx=x+dx; while(ny>=0&&ny<R&&nx>=0&&nx<C){ if(g[ny][nx]!==0){o[y][x]=g[ny][nx];break;} ny+=dy;nx+=dx; } } return o; };
const lineColor=(cells:number[])=>{ const s=new Set(cells.filter(v=>v!==0)); return s.size===1?[...s][0]:0; };
// row×col MIXTURE: a cell lit by BOTH its row-source and column-source (the tilted x+z sheet)
const mixProject=(mode:string)=>(g:Grid):Grid|null=>{ const R=g.length,C=g[0].length; const rc=g.map(r=>lineColor(r)); const cc:number[]=[]; for(let x=0;x<C;x++){const col=[];for(let y=0;y<R;y++)col.push(g[y][x]);cc.push(lineColor(col));}
  const o=g.map(r=>r.slice()); for(let y=0;y<R;y++)for(let x=0;x<C;x++){ const rv=rc[y],cv=cc[x];
    if(mode==="intersect") o[y][x]= (rv!==0&&cv!==0)? rv : (g[y][x]!==0?g[y][x]:0);
    else o[y][x]= (rv!==0||cv!==0)? (rv||cv) : (g[y][x]!==0?g[y][x]:0); } return o; };
const TRANSFERS: [string,(g:Grid)=>Grid|null][] = [
  ...DIRS.map((_,d)=>["slide"+d, slideFill(d)] as [string,(g:Grid)=>Grid|null]),
  ["mixUnion", mixProject("union")], ["mixIntersect", mixProject("intersect")],
];

const ev = loadTasks(path.join(__dirname,"..","data-eval"));
const verified = new Set(fs.readFileSync(path.join(__dirname,"..","verified_eval.txt"),"utf8").trim().split(/\s+/));
const START=+(process.argv[2]||0), END=+(process.argv[3]||ev.length);
let base=0, closed=0, net:string[]=[];
for(let i=START;i<Math.min(END,ev.length);i++){ const t=ev[i];
  if(!t.test||t.test.some((te:any)=>!te.output)) continue;
  let r:any=null; try{r=bounceSearchDiag(t.train,3,30);}catch{}
  if(!r||!r.bestProg) continue;
  if(r.prog && t.test.every((te:any)=>{const o=r.prog(te.input);return o&&eqG(o,te.output);})){ base++; continue; }
  const A=build(r.bestProg as [string,any][]);
  let win:((g:Grid)=>Grid|null)|null=null, how="";
  for(const [nm,T] of TRANSFERS){ if(win)break;
    for(const pre of [A,(g:Grid)=>g]){ const cand=(g:Grid)=>{const a=pre(g);return a?T(a):null;};
      if(t.train.every((p:any)=>{const o=cand(p.input);return o&&eqG(o,p.output);}) && !t.train.every((p:any)=>{const a=pre(p.input);return a&&eqG(a,p.output);})){ win=cand; how=(pre===A?"anchor+":"")+nm; break; } } }
  if(win && t.test.every((te:any)=>{const o=win!(te.input);return o&&eqG(o,te.output);})){ closed++; if(!verified.has(t.id)) net.push(t.id+"["+how+"]"); }
  if((i+1)%40===0) process.stderr.write(`[${i+1}] base=${base} closed=${closed}\n`);
}
console.log("\n=== §18.9 CLOSER (oriented energy-transfer: 8 dirs + row×col mixtures) EVAL ["+START+","+END+") ===");
console.log("base forward solved: "+base);
console.log("closed by an oriented transfer: "+closed+"   net-new: "+net.length+"  "+net.join(" "));
