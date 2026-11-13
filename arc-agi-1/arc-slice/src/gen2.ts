// gen2.ts — SELF-SYNTHESIZING generator built from our own generative ATOMS.
// Replaces the implanted monolithic templates (generator.ts, kept as reference)
// with composable matter-creation moves discovered against the train delta:
//   SEED  (where creation originates)  ×  ACTION (how matter is written).
// A single synth loop fits {seed×action×params} to every train pair, so it
// reproduces ray/connect/box AND combinations the monoliths couldn't express.
import { Grid, dims, clone, palette, background, equal } from "./grid";
import { components, Obj } from "./objects";

export interface Pair { input: Grid; output: Grid; }
export type GenProg = (g: Grid) => Grid | null;

const inb = (g: Grid, y: number, x: number) => y>=0 && y<g.length && x>=0 && x<g[0].length;
const ORTH: [number,number][] = [[-1,0],[1,0],[0,-1],[0,1]];
const DIAG: [number,number][] = [[-1,-1],[-1,1],[1,-1],[1,1]];
const ALL8: [number,number][] = [...ORTH,...DIAG];
const DSETS: [number,number][][] = [ORTH,DIAG,ALL8,[[-1,0]],[[1,0]],[[0,-1]],[[0,1]]];

// ── SEED atoms: return the originating cells ──
function seedMarkers(g: Grid, bg: number, S: number): [number,number][] {
  return components(g,bg,"blob").filter(o=>o.color===S && o.size===1).map(o=>o.cells[0]);
}
function seedColor(g: Grid, bg: number, S: number): [number,number][] {
  const out:[number,number][]=[]; for(let y=0;y<g.length;y++)for(let x=0;x<g[0].length;x++) if(g[y][x]===S) out.push([y,x]);
  return out;
}
// ── ACTION atom: emit a ray from each seed along dirs, paint C, stop at edge|hit ──
function actEmit(g: Grid, bg: number, seeds: [number,number][], dirs:[number,number][], C:number, stopHit:boolean): Grid {
  const out = clone(g);
  for (const [y0,x0] of seeds) for (const [dy,dx] of dirs) {
    let y=y0+dy, x=x0+dx;
    while (inb(g,y,x)) { if (g[y][x]!==bg){ if(stopHit) break; } if (out[y][x]===bg) out[y][x]=C; y+=dy; x+=dx; }
  }
  return out;
}
// ── ACTION atom: fill between aligned same-colour cells (optionally only colour S) ──
function actBetween(g: Grid, bg: number, C: number|null, only: number|null): Grid {
  const out=clone(g); const [r,c]=dims(g);
  const use=(v:number)=> only===null || v===only;
  for(let y=0;y<r;y++){ let prev=-1,pc=-1; for(let x=0;x<c;x++){ if(g[y][x]!==bg){ if(prev>=0&&g[y][x]===pc&&use(pc)){ for(let k=prev+1;k<x;k++) if(out[y][k]===bg) out[y][k]=C??pc; } prev=x; pc=g[y][x]; } } }
  for(let x=0;x<c;x++){ let prev=-1,pc=-1; for(let y=0;y<r;y++){ if(g[y][x]!==bg){ if(prev>=0&&g[y][x]===pc&&use(pc)){ for(let k=prev+1;k<y;k++) if(out[k][x]===bg) out[k][x]=C??pc; } prev=y; pc=g[y][x]; } } }
  return out;
}
// ── ACTION atom: draw object bounding boxes (outline|fill), colour C or source ──
function actBox(g: Grid, bg: number, C:number|null, fill:boolean, onlyColor:number|null): Grid {
  const out=clone(g);
  for(const o of components(g,bg,"blob")){ if(onlyColor!==null && o.color!==onlyColor) continue; const col=C??o.color;
    for(let y=o.y0;y<=o.y1;y++)for(let x=o.x0;x<=o.x1;x++){ const edge=y===o.y0||y===o.y1||x===o.x0||x===o.x1; if((fill||edge)&&out[y][x]===bg) out[y][x]=col; } }
  return out;
}


// ── ACTION atom: complete a SYMMETRY — fill each bg cell from its mirror image ──
function actSymPaint(g: Grid, bg: number, mode: number): Grid | null {
  const [r,c]=dims(g); const out=clone(g);
  const map=(y:number,x:number):[number,number]=>{
    switch(mode){ case 0: return [y,c-1-x];            // mirror horizontal
      case 1: return [r-1-y,x];                         // mirror vertical
      case 2: return [r-1-y,c-1-x];                     // rot180
      case 3: return [x,y];                             // transpose (square only)
      default: return [y,x]; }
  };
  if(mode===3 && r!==c) return null;
  let changed=false;
  for(let y=0;y<r;y++)for(let x=0;x<c;x++){ const [my,mx]=map(y,x);
    if(my<0||my>=r||mx<0||mx>=c) return null;
    const a=g[y][x], b=g[my][mx];
    if(a===bg && b!==bg){ out[y][x]=b; changed=true; }
    else if(a!==bg && b!==bg && a!==b) return null;    // conflict -> not this symmetry
  }
  return changed?out:null;
}
// ── ACTION atom: PERIODIC stamp — detect a tile period, fill bg cells from it ──
function actPeriodic(g: Grid, bg: number, py: number, px: number): Grid | null {
  const [r,c]=dims(g); if(py<1||px<1||(py>=r&&px>=c)) return null;
  // build the period tile: each (y%py, x%px) must agree among all non-bg cells
  const tile:number[][]=Array.from({length:py},()=>Array(px).fill(-1));
  for(let y=0;y<r;y++)for(let x=0;x<c;x++){ const v=g[y][x]; if(v===bg) continue;
    const ty=y%py, tx=x%px; if(tile[ty][tx]===-1) tile[ty][tx]=v; else if(tile[ty][tx]!==v) return null; }
  const out=clone(g); let changed=false;
  for(let y=0;y<r;y++)for(let x=0;x<c;x++){ if(out[y][x]===bg){ const t=tile[y%py][x%px]; if(t!==-1){ out[y][x]=t; changed=true; } } }
  return changed?out:null;
}


// ── ACTION atom: FLOOD enclosed bg regions (not touching border) ──
function actFlood(g: Grid, bg: number, C: number, bySurround: boolean): Grid | null {
  const [r,c]=dims(g); const seen=Array.from({length:r},()=>Array(c).fill(false)); const out=clone(g);
  let changed=false;
  for(let y=0;y<r;y++)for(let x=0;x<c;x++){
    if(g[y][x]!==bg||seen[y][x]) continue;
    const reg:[number,number][]=[]; const st:[number,number][]=[[y,x]]; seen[y][x]=true; let touchesBorder=false;
    const surround=new Set<number>();
    while(st.length){ const [cy,cx]=st.pop()!; reg.push([cy,cx]);
      if(cy===0||cx===0||cy===r-1||cx===c-1) touchesBorder=true;
      for(const [dy,dx] of [[1,0],[-1,0],[0,1],[0,-1]] as [number,number][]){ const ny=cy+dy,nx=cx+dx;
        if(ny<0||ny>=r||nx<0||nx>=c) continue;
        if(g[ny][nx]===bg){ if(!seen[ny][nx]){seen[ny][nx]=true; st.push([ny,nx]);} }
        else surround.add(g[ny][nx]); } }
    if(touchesBorder) continue;
    const fillC = bySurround ? (surround.size===1 ? [...surround][0] : -1) : C;
    if(fillC===-1) continue;
    for(const [ry,rx] of reg){ out[ry][rx]=fillC; changed=true; }
  }
  return changed?out:null;
}

// ── the SYNTHESIZER: compose atoms to fit every train pair ──
export function synthGenerator(train: Pair[]): {prog:GenProg, kind:string} | null {
  for (const p of train) if (p.input.length!==p.output.length||p.input[0].length!==p.output[0].length) return null;
  const bg = background(train[0].input);
  const pal = Array.from(new Set(train.flatMap(p=>[...palette(p.input),...palette(p.output)]))).filter(c=>c!==bg);
  const fit=(f:GenProg)=>train.every(p=>{const o=f(p.input);return o&&equal(o,p.output);});

  // EMIT family: seed ∈ {markers, color}, paint ∈ {learned C, source S}
  for (const seedKind of ["markers","colour"] as const)
   for (const S of pal) for (const dirs of DSETS) for (const stopHit of [true,false])
    for (const C of [...pal, -1]) {  // -1 = paint with source colour S
      const paint = C===-1 ? S : C;
      const seeds = (g:Grid)=> seedKind==="markers"? seedMarkers(g,bg,S) : seedColor(g,bg,S);
      const f:GenProg = (g)=> actEmit(g,bg,seeds(g),dirs,paint,stopHit);
      if (fit(f)) return {prog:f, kind:`emit/${seedKind}(S=${S},paint=${paint},dirs=${dirs.length},${stopHit?"hit":"edge"})`};
    }
  // BETWEEN family: paint ∈ {source, learned}, restrict ∈ {any, colour S}
  for (const only of [null, ...pal]) for (const C of [null, ...pal]) {
    const f:GenProg=(g)=>actBetween(g,bg,C,only);
    if (fit(f)) return {prog:f, kind:`between(only=${only},paint=${C??"src"})`};
  }
  // BOX family
  for (const onlyColor of [null, ...pal]) for (const C of [null, ...pal]) for (const fill of [false,true]) {
    const f:GenProg=(g)=>actBox(g,bg,C,fill,onlyColor);
    if (fit(f)) return {prog:f, kind:`box(only=${onlyColor},paint=${C??"src"},${fill?"fill":"line"})`};
  }
  // SYMMETRY-PAINT family
  for (const mode of [0,1,2,3]) {
    const f:GenProg=(g)=>actSymPaint(g,bg,mode);
    if (train.every(p=>{const o=f(p.input);return o&&equal(o,p.output);})) return {prog:f, kind:`symPaint(mode=${mode})`};
  }
  // PERIODIC-stamp family (small periods)
  for (let py=1; py<=6; py++) for (let px=1; px<=6; px++) {
    if (py===1 && px===1) continue;
    const f:GenProg=(g)=>actPeriodic(g,bg,py,px);
    if (train.every(p=>{const o=f(p.input);return o&&equal(o,p.output);})) return {prog:f, kind:`periodic(${py}x${px})`};
  }
  // FLOOD-region family
  for (const bySurround of [true,false]) for (const C of pal) {
    const f:GenProg=(g)=>actFlood(g,bg,C,bySurround);
    if (train.every(p=>{const o=f(p.input);return o&&equal(o,p.output);})) return {prog:f, kind:`flood(${bySurround?"surround":"C="+C})`};
  }
  return null;
}

// ── enumerate MATTER transform candidates (not fit-checked) for composition ──
export function matterCandidates(train: Pair[]): {prog:GenProg,kind:string}[] {
  const bg = background(train[0].input);
  const pal = Array.from(new Set(train.flatMap(p=>[...palette(p.input),...palette(p.output)]))).filter(c=>c!==bg).slice(0,6);
  const out:{prog:GenProg,kind:string}[]=[];
  const some:[number,number][][]=[[[-1,0],[1,0],[0,-1],[0,1]],[[-1,-1],[-1,1],[1,-1],[1,1]]];
  for(const S of pal) for(const dirs of some) for(const stopHit of [true,false]) for(const C of [...pal.slice(0,3),-1]){
    const paint=C===-1?S:C;
    out.push({prog:(g)=>actEmit(g,bg,seedMarkers(g,bg,S),dirs,paint,stopHit),kind:`emit.m(${S})`});
    out.push({prog:(g)=>actEmit(g,bg,seedColor(g,bg,S),dirs,paint,stopHit),kind:`emit.c(${S})`});
  }
  for(const C of [null,...pal.slice(0,3)] as (number|null)[]) out.push({prog:(g)=>actBetween(g,bg,C,null),kind:`between`});
  for(const C of [null,...pal.slice(0,3)] as (number|null)[]) for(const fill of [false,true]) out.push({prog:(g)=>actBox(g,bg,C,fill,null),kind:`box`});
  for(const mode of [0,1,2,3]) out.push({prog:(g)=>actSymPaint(g,bg,mode),kind:`sym${mode}`});
  for(const C of pal.slice(0,3)) for(const bs of [true,false]) out.push({prog:(g)=>actFlood(g,bg,C,bs),kind:`flood`});
  return out.slice(0,90);
}
