// valencecompose.ts — bond atoms by VALENCE (knot/tail chemistry). A task demands
// certain macro-axes; compose op1∘op2 only when their valences COVER those axes,
// with op2 supplying the TAIL op1 leaves. Chemical matching replaces blind search.
import * as path from "path"; import * as fs from "fs";
import { loadTasks } from "./loader";
import { OPS, applyOp } from "./dsl";
const HEAVY=new Set(["mapObjects","mapTopK","fractal","nested","colorByShape","periodicFill","overlayPanels","combinePanels","connectObjects","completeDiag","stamp","drawRays","grow"]);
import { taskPalette } from "./transfer";
import { equal } from "./grid";
type Grid=number[][];
const tasks=loadTasks(path.join(__dirname,"..","data"));
const combined=new Set(fs.readFileSync(path.join(__dirname,"..","combined_solved.txt"),"utf8").trim().split(/\s+/));
const cards:{op:string,valence:string[]}[]=JSON.parse(fs.readFileSync(path.join(__dirname,"..","atom_cards.json"),"utf8"));
const valOf=new Map(cards.map(c=>[c.op,new Set(c.valence.filter(a=>a!=="?"))]));
const AX=["color","size","pos","sym"];

function counts(g:Grid){const c=new Array(10).fill(0);for(const r of g)for(const v of r)if(v<10)c[v]++;return c;}
function spatial(g:Grid){const r=g.length,c=g[0].length;let sy=0,sx=0,m=0;for(let y=0;y<r;y++)for(let x=0;x<c;x++){if(g[y][x]!==0){sy+=y/(r-1||1);sx+=x/(c-1||1);m++;}}const cy=m?sy/m:.5,cx=m?sx/m:.5;let dh=0,dv=0,dt=0,t=0;for(let y=0;y<r;y++)for(let x=0;x<c;x++){t++;if(g[y][x]!==g[y][c-1-x])dh++;if(g[y][x]!==g[r-1-y][x])dv++;if(r===c&&g[y][x]!==g[x][y])dt++;}return[cy,cx,dh/t,dv/t,r===c?dt/t:0];}
function reqAxes(train:any[]):Set<string>{ const acc:any={color:0,size:0,pos:0,sym:0};
  for(const p of train){const n=p.input.length*p.input[0].length||1;const ci=counts(p.input),co=counts(p.output);
    let col=0;for(let k=0;k<10;k++)col+=Math.abs((co[k]-ci[k])/n);acc.color+=col;acc.size+=Math.abs((p.output.length*p.output[0].length-n)/n);
    const si=spatial(p.input),so=spatial(p.output);acc.pos+=Math.abs(so[0]-si[0])+Math.abs(so[1]-si[1]);acc.sym+=Math.abs(so[2]-si[2])+Math.abs(so[3]-si[3])+Math.abs(so[4]-si[4]);}
  const n=train.length; return new Set(AX.filter(a=>acc[a]/n>0.02)); }

function solves(prog:(g:Grid)=>Grid|null,tr:any[]){return tr.every((p:any)=>{const o=prog(p.input);return o&&equal(o,p.output);});}
const apply=(op:string,pr:any)=>(g:Grid)=>{try{return applyOp({name:op,params:pr} as any,g);}catch{return null;}};

let net=0; const hits:string[]=[]; let pairsTried=0, blindPairs=0; let i=0;
for(const t of tasks){ i++;
  if(combined.has(t.id)) continue;
  if(t.train.some((p:any)=>p.input.length*p.input[0].length>460)) continue;
  const req=reqAxes(t.train); if(req.size===0) continue;
  let budget=3000;
  const pal=taskPalette(t.train);
  // op1 = atoms whose valence intersects req (a bonding site)
  const op1s=cards.filter(c=>!HEAVY.has(c.op)).filter(c=>{const v=valOf.get(c.op)!;return [...v].some(a=>req.has(a));}).map(c=>c.op);
  let done=false;
  for(const o1 of op1s){ if(done)break; let prs1:any[];try{prs1=(OPS as any)[o1].enumerate(pal).slice(0,3);}catch{prs1=[{}];}
    for(const p1 of prs1){ if(done)break; const a1=apply(o1,p1);
      const mid=t.train.map((p:any)=>a1(p.input)); if(mid.some((g:Grid)=>!g))continue;
      // residual axes op1 didn't close (recompute on intermediate->output)
      const nt=t.train.map((p:any,k:number)=>({input:mid[k],output:p.output}));
      const resid=reqAxes(nt);
      // op2 = atoms whose valence covers the residual (tail-to-tail bond)
      const op2s = (resid.size? cards.filter(c=>{const v=valOf.get(c.op)!;return [...resid].every(a=>v.has(a))||[...v].some(a=>resid.has(a));}) : cards).filter(c=>!HEAVY.has(c.op)).map(c=>c.op);
      for(const o2 of op2s){ let prs2:any[];try{prs2=(OPS as any)[o2].enumerate(taskPalette(nt)).slice(0,3);}catch{prs2=[{}];}
        for(const p2 of prs2){ if(budget--<=0){done=true;break;} pairsTried++; const a2=apply(o2,p2); const prog=(g:Grid)=>{const m=a1(g);return m?a2(m):null;};
          if(solves(prog,t.train)){ const tp=t.test.every((te:any)=>{const o=prog(te.input);return te.output&&o&&equal(o,te.output);});
            if(tp){ net++; hits.push(`${t.id}[${o1}∘${o2}|req=${[...req].join(",")}]`); done=true; break; } } }
        if(done)break; } } }
}
console.log(`valence-guided composition — NET-NEW over combined-82: ${net}`);
hits.forEach(h=>console.log("  "+h));
console.log(`\npairs tried (valence-filtered): ${pairsTried}`);
