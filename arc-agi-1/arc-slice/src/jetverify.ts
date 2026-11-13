import * as path from "path";
import { loadTasks } from "./loader";
import { OPS, OP_NAMES, applyOp } from "./dsl";
import { taskPalette } from "./transfer";
import { equal } from "./grid";
const HEAVY=new Set(["mapObjects","mapTopK","fractal","nested","colorByShape","overlayPanels","combinePanels","periodicFill","stamp","moveContact","connectObjects","completeDiag","grow","drawRays","alignLargest","gravityObj"]);
const FORCE_OPS=OP_NAMES.filter(n=>!HEAVY.has(n));
const tasks=loadTasks(path.join(__dirname,"..","data"));
type Step={op:string,params:any};
function tension(c:number[][],o:number[][]):number{ if(!c||!c.length)return 1e9;
  if(c.length!==o.length||c[0].length!==o[0].length){const h=(g:number[][])=>{const m=new Map<number,number>();let n=0;for(const r of g)for(const v of r){m.set(v,(m.get(v)??0)+1);n++;}return{m,n};};const a=h(c),b=h(o);let d=0;const ks=new Set([...a.m.keys(),...b.m.keys()]);for(const k of ks)d+=Math.abs((a.m.get(k)??0)/a.n-(b.m.get(k)??0)/b.n);return 0.5+0.25*d;}
  let mis=0,tot=0;for(let y=0;y<o.length;y++)for(let x=0;x<o[0].length;x++){tot++;if(c[y][x]!==o[y][x])mis++;}return mis/tot;}
function tot(prog:Step[],tr:any[]):number{let s=0;for(const p of tr){let g=p.input;for(const st of prog){const o=applyOp({name:st.op,params:st.params} as any,g);if(!o)return 1e9;g=o;}s+=tension(g,p.output);}return s/tr.length;}
function solv(prog:Step[],tr:any[]):boolean{return tr.every(p=>{let g=p.input;for(const st of prog){const o=applyOp({name:st.op,params:st.params} as any,g);if(!o)return false;g=o;}return equal(g,p.output);});}
function search(tr:any[]):Step[]|null{const pal=taskPalette(tr);let budget=4000;
  let beam:{prog:Step[],t:number}[]=[{prog:[],t:tot([],tr)}];
  for(let d=0;d<3;d++){const next:{prog:Step[],t:number}[]=[];
    for(const b of beam)for(const op of FORCE_OPS){if(budget--<=0)break;let prs:any[];try{prs=(OPS as any)[op].enumerate(pal).slice(0,4);}catch{prs=[{}];}
      for(const pr of prs){const prog=[...b.prog,{op,params:pr}];if(solv(prog,tr))return prog;const t=tot(prog,tr);if(t<b.t-1e-9)next.push({prog,t});else if(t<b.t+0.05&&next.length<4000)next.push({prog,t});}}
    if(!next.length||budget<=0)break;next.sort((a,b)=>a.t-b.t);beam=next.slice(0,4);}
  return null;}
for(const id of ["28bf18c6","6f8cd79b","91714a58"]){const t=tasks.find(x=>x.id===id)!;const prog=search(t.train);
  if(!prog){console.log(id,"no-prog?");continue;}
  const testOk=t.test.every(te=>{let g=te.input;for(const st of prog){const o=applyOp({name:st.op,params:st.params} as any,g);if(!o)return false;g=o;}return te.output&&equal(g,te.output);});
  console.log(id, testOk?"TEST-PASS":"TEST-FAIL", "| prog:", prog.map(s=>s.op).join("∘"));}
