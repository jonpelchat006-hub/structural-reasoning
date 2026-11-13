// antimatter.ts — the EXTRACTION sphere (mirror of gen2's generation sphere).
// Where matter CREATES content, antimatter SELECTS/CROPS it out: TARGET a region
// via an induced PREDICATE, then EXTRACT it via an action. Synth loop fits
// predicate×action to every train pair (the "balance": output is what's left
// after extraction, residual 0).
import { Grid, dims, clone, palette, background, equal } from "./grid";
import { components, blank, Obj } from "./objects";

export interface Pair { input: Grid; output: Grid; }
export type ExProg = (g: Grid) => Grid | null;

function holes(g:Grid,bg:number,o:Obj):number{
  // count enclosed bg cells inside the object's bbox not reachable from bbox border
  const y0=o.y0,x0=o.x0,h=o.y1-o.y0+1,w=o.x1-o.x0+1;
  const occ=Array.from({length:h},()=>Array(w).fill(false));
  for(const[y,x]of o.cells) occ[y-y0][x-x0]=true;
  const seen=Array.from({length:h},()=>Array(w).fill(false)); const st:[number,number][]=[];
  for(let y=0;y<h;y++)for(let x=0;x<w;x++) if((y===0||x===0||y===h-1||x===w-1)&&!occ[y][x]&&!seen[y][x]){seen[y][x]=true;st.push([y,x]);}
  while(st.length){const[cy,cx]=st.pop()!; for(const[dy,dx]of[[1,0],[-1,0],[0,1],[0,-1]] as [number,number][]){const ny=cy+dy,nx=cx+dx; if(ny<0||ny>=h||nx<0||nx>=w)continue; if(!occ[ny][nx]&&!seen[ny][nx]){seen[ny][nx]=true;st.push([ny,nx]);}}}
  let cnt=0; for(let y=0;y<h;y++)for(let x=0;x<w;x++) if(!occ[y][x]&&!seen[y][x]) cnt++;
  return cnt;
}

// ── PREDICATE: pick a target object from the inventory ──
function pick(objs:Obj[], g:Grid, bg:number, kind:string):Obj|null{
  if(!objs.length) return null;
  const colorFreq=new Map<number,number>(); for(const o of objs) colorFreq.set(o.color,(colorFreq.get(o.color)??0)+1);
  const shapeKey=(o:Obj)=>o.cells.map(([y,x])=>(y-o.y0)*64+(x-o.x0)).sort((a,b)=>a-b).join(",");
  const shapeFreq=new Map<string,number>(); for(const o of objs) shapeFreq.set(shapeKey(o),(shapeFreq.get(shapeKey(o))??0)+1);
  const by=(f:(o:Obj)=>number,max:boolean)=>objs.slice().sort((a,b)=>max?f(b)-f(a):f(a)-f(b))[0];
  switch(kind){
    case "largest":  return by(o=>o.size,true);
    case "smallest": return by(o=>o.size,false);
    case "rareColor":   {const m=Math.min(...colorFreq.values()); const c=objs.filter(o=>colorFreq.get(o.color)===m); return c.length===1?c[0]:null;}
    case "commonColor": {const m=Math.max(...colorFreq.values()); const c=objs.filter(o=>colorFreq.get(o.color)===m); return c.length>=1?by(o=>colorFreq.get(o.color)!,true):null;}
    case "uniqueShape": {const u=objs.filter(o=>shapeFreq.get(shapeKey(o))===1); return u.length===1?u[0]:null;}
    case "uniqueColor": {const u=objs.filter(o=>colorFreq.get(o.color)===1); return u.length===1?u[0]:null;}
    case "mostHoles":   return by(o=>holes(g,bg,o),true);
    case "topLeft":     return by(o=>o.y0*100+o.x0,false);
  }
  return null;
}
const PREDS=["largest","smallest","rareColor","commonColor","uniqueShape","uniqueColor","mostHoles","topLeft"];

// ── EXTRACTION ACTIONS ──
function actKeep(g:Grid,bg:number,o:Obj):Grid{ const out=blank(g.length,g[0].length,bg); for(const[y,x]of o.cells)out[y][x]=g[y][x]; return out; }
function actCrop(g:Grid,bg:number,o:Obj):Grid{ const out=[]; for(let y=o.y0;y<=o.y1;y++)out.push(g[y].slice(o.x0,o.x1+1)); return out; }
function actCropMask(g:Grid,bg:number,o:Obj):Grid{ const h=o.y1-o.y0+1,w=o.x1-o.x0+1; const out=blank(h,w,bg); for(const[y,x]of o.cells)out[y-o.y0][x-o.x0]=g[y][x]; return out; }

export function synthAntimatter(train: Pair[]): {prog:ExProg, kind:string} | null {
  const bg = background(train[0].input);
  const fit=(f:ExProg)=>train.every(p=>{const o=f(p.input);return o&&equal(o,p.output);});
  for(const mode of ["blob","color"] as const)
   for(const pred of PREDS)
    for(const [an,act] of [["keep",actKeep],["crop",actCrop],["cropMask",actCropMask]] as [string,any][]){
      const f:ExProg=(g)=>{ const objs=components(g,bg,mode); const o=pick(objs,g,bg,pred); return o?act(g,bg,o):null; };
      if(fit(f)) return {prog:f, kind:`${pred}/${an}/${mode}`};
    }
  return null;
}

// ── enumerate ANTIMATTER extraction candidates (not fit-checked) for composition ──
export function antiCandidates(train: Pair[]): {prog:ExProg,kind:string}[] {
  const bg = background(train[0].input);
  const out:{prog:ExProg,kind:string}[]=[];
  for(const mode of ["blob","color"] as const)
   for(const pred of PREDS)
    for(const [an,act] of [["keep",actKeep],["crop",actCrop],["cropMask",actCropMask]] as [string,any][]){
      out.push({prog:(g)=>{const objs=components(g,bg,mode); const o=pick(objs,g,bg,pred); return o?act(g,bg,o):null;},kind:`${pred}/${an}/${mode}`});
    }
  return out;
}
