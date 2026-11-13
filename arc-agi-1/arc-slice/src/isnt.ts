// isnt.ts — the ANTIMATTER GENERATOR: makes "isn't" tags. Where gen2 asserts what a
// grid IS (symmetric, periodic, uniform), this finds where it ISN'T — the VIOLATION
// set — and emits it. Odd-one-out, hidden figure, denoise, "everything that isn't us"
// are all isn't-tag tasks: the answer is the complement of the asserted pattern.
import { Grid, dims, clone, palette, background, equal } from "./grid";
import { components, blank, Obj } from "./objects";

export interface Pair { input: Grid; output: Grid; }
export type IsntProg = (g: Grid) => Grid | null;

// ── PATTERN assertions -> their VIOLATION set (the "isn't" cells) ──
function violSym(g:Grid,bg:number,mode:number,kind:number):[number,number][]|null{
  const [r,c]=dims(g);
  const mir=(y:number,x:number):[number,number]=>{ switch(mode){case 0:return[y,c-1-x];case 1:return[r-1-y,x];case 2:return[r-1-y,c-1-x];default:return[x,y];} };
  if(mode===3&&r!==c) return null;
  const V:[number,number][]=[];
  for(let y=0;y<r;y++)for(let x=0;x<c;x++){ const [my,mx]=mir(y,x); if(my<0||my>=r||mx<0||mx>=c) return null;
    const a=g[y][x], b=g[my][mx];
    if(kind===0){ if(a!==b) V.push([y,x]); }                       // any disagreement
    else { if(a!==bg && b===bg) V.push([y,x]); }                    // asymmetric OVERLAY: content with no mirror partner
  }
  return V.length?V:null;
}
function violPeriodic(g:Grid,bg:number,py:number,px:number):[number,number][]|null{
  const [r,c]=dims(g); if(py<1||px<1||(py>=r&&px>=c)) return null;
  // majority value per period class
  const cnt:Map<string,Map<number,number>>=new Map();
  for(let y=0;y<r;y++)for(let x=0;x<c;x++){ const k=(y%py)+","+(x%px); if(!cnt.has(k))cnt.set(k,new Map()); const m=cnt.get(k)!; m.set(g[y][x],(m.get(g[y][x])??0)+1); }
  const maj:Map<string,number>=new Map();
  for(const [k,m] of cnt){ let bv=-1,bn=-1; for(const [v,n] of m) if(n>bn){bn=n;bv=v;} maj.set(k,bv); }
  const V:[number,number][]=[];
  for(let y=0;y<r;y++)for(let x=0;x<c;x++){ if(g[y][x]!==maj.get((y%py)+","+(x%px))) V.push([y,x]); }
  return V.length&&V.length<r*c? V : null;
}
function violOddObject(g:Grid,bg:number,by:"shape"|"color"):[number,number][]|null{
  const objs=components(g,bg,"blob"); if(objs.length<2) return null;
  const key=(o:Obj)=> by==="color"? String(o.color) : o.cells.map(([y,x])=>(y-o.y0)*64+(x-o.x0)).sort((a,b)=>a-b).join(",");
  const freq=new Map<string,number>(); for(const o of objs) freq.set(key(o),(freq.get(key(o))??0)+1);
  const mn=Math.min(...freq.values()); const odd=objs.filter(o=>freq.get(key(o))===mn); if(odd.length!==1) return null;
  return odd[0].cells;
}

// ── ACTIONS on the isn't-set V ──
function keepV(g:Grid,bg:number,V:[number,number][]):Grid{ const o=blank(g.length,g[0].length,bg); for(const[y,x]of V)o[y][x]=g[y][x]; return o; }
function removeV(g:Grid,bg:number,V:[number,number][]):Grid{ const o=clone(g); for(const[y,x]of V)o[y][x]=bg; return o; }
function maskV(g:Grid,bg:number,V:[number,number][],C:number):Grid{ const o=clone(g); for(const[y,x]of V)o[y][x]=C; return o; }
function cropV(g:Grid,bg:number,V:[number,number][]):Grid{ let y0=1e9,y1=-1,x0=1e9,x1=-1; for(const[y,x]of V){y0=Math.min(y0,y);y1=Math.max(y1,y);x0=Math.min(x0,x);x1=Math.max(x1,x);} const o=[]; for(let y=y0;y<=y1;y++)o.push(g[y].slice(x0,x1+1)); return o; }
function colorV(g:Grid,bg:number,V:[number,number][]):Grid|null{ const cols=new Set(V.map(([y,x])=>g[y][x])); if(cols.size!==1) return null; return [[...cols][0]]; }

export function synthIsnt(train: Pair[]): {prog:IsntProg,kind:string} | null {
  const bg=background(train[0].input);
  const pal=Array.from(new Set(train.flatMap(p=>[...palette(p.input),...palette(p.output)]))).filter(c=>c!==bg).slice(0,6);
  const fit=(f:IsntProg)=>train.every(p=>{const o=f(p.input);return o&&equal(o,p.output);});
  // build violation-set generators
  const vios:{v:(g:Grid)=>[number,number][]|null,kind:string}[]=[];
  for(const m of [0,1,2,3]) for(const kd of [0,1]) vios.push({v:(g)=>violSym(g,bg,m,kd),kind:`isntSym${m}.${kd}`});
  for(let py=1;py<=4;py++)for(let px=1;px<=4;px++){ if(py===1&&px===1)continue; vios.push({v:(g)=>violPeriodic(g,bg,py,px),kind:`isntPer${py}x${px}`}); }
  for(const by of ["shape","color"] as const) vios.push({v:(g)=>violOddObject(g,bg,by),kind:`isntOdd-${by}`});
  // actions
  for(const vg of vios){
    const acts:{f:IsntProg,an:string}[]=[
      {f:(g)=>{const V=vg.v(g);return V?keepV(g,bg,V):null;},an:"keep"},
      {f:(g)=>{const V=vg.v(g);return V?removeV(g,bg,V):null;},an:"remove"},
      {f:(g)=>{const V=vg.v(g);return V?cropV(g,bg,V):null;},an:"crop"},
      {f:(g)=>{const V=vg.v(g);return V?colorV(g,bg,V):null;},an:"color"},
    ];
    for(const C of pal) acts.push({f:(g)=>{const V=vg.v(g);return V?maskV(g,bg,V,C):null;},an:`mask${C}`});
    for(const a of acts){ if(fit(a.f)) return {prog:a.f,kind:`${vg.kind}/${a.an}`}; }
  }
  return null;
}
