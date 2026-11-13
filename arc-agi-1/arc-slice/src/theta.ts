// theta.ts — measure the OVERLAP equilibrium θ on held-out test.
// A = cells a program changes vs input; R = cells that truly change.
// θ = |A|/|R|:  <1 underfit, =1 balanced/solved, >1 overfit (sphere bulges past answer).
import * as path from "path";
import { loadTasks } from "./loader";
import { synthGenerator } from "./gen2";
import { synthAntimatter } from "./antimatter";
const tasks=loadTasks(path.join(__dirname,"..","data"));
function changes(inp:number[][],g:number[][]):Set<string>{ const s=new Set<string>(); if(!g||g.length!==inp.length||g[0].length!==inp[0].length) return s;
  for(let y=0;y<inp.length;y++)for(let x=0;x<inp[0].length;x++) if(inp[y][x]!==g[y][x]) s.add(y+","+x); return s; }
function theta(prog:any,te:any):{theta:number,recall:number,ok:boolean}|null{
  const got=prog(te.input); const out=te.output; if(!out) return null;
  const dimsOk = got && got.length===out.length && got[0].length===out[0].length;
  const A=changes(te.input,got); const R=changes(te.input,out);
  let correct=0; for(const k of A){ const [y,x]=k.split(",").map(Number); if(dimsOk && got[y][x]===out[y][x] && R.has(k)) correct++; }
  const th = R.size===0 ? (A.size===0?1:Infinity) : A.size/R.size;
  const recall = R.size===0?1: correct/R.size;
  const ok = dimsOk && A.size===R.size && correct===R.size;
  return {theta:th, recall, ok};
}
const fixture=["22168020","22eb0ac0","253bf280","3aa6fb7a","60b61512","6d75e8bb","dbc1a6ce","ded97339","8eb1be9a","00d62c1b","a5313dff"];
console.log("task      θ(test)  recall  solved   note");
for(const id of fixture){ const t=tasks.find(x=>x.id===id)!; let r:any=null; try{r=synthGenerator(t.train);}catch{}
  if(!r){ try{const a=synthAntimatter(t.train); r=a?{prog:a.prog}:null;}catch{} }
  if(!r){console.log(`${id}  no-prog`);continue;}
  const m=theta(r.prog,t.test[0]); if(!m){console.log(`${id}  no-test`);continue;}
  const note = m.ok?"BALANCED θ=1":(m.theta>1?"OVERFIT θ>1":(m.theta<1?"UNDERFIT θ<1":"wrong-cells"));
  console.log(`${id}  ${(m.theta===Infinity?"inf":m.theta.toFixed(2)).padStart(6)}  ${m.recall.toFixed(2)}    ${m.ok?"YES":"no "}     ${note}`);
}
