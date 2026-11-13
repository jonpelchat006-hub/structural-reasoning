// signature.ts — encode an ARC task as a point in Jonathan's 7D colour space
// (color_trails.py) plus a DARK cancellation profile (wave_frequency.py: dark =
// collapse toward the void). Light = what's present; Dark = what cancels.
// This is the memory key: tasks with near signatures should RESONATE.
import { measure, detect } from "../../arc-slice/src/relations";
import { Pair } from "../../arc-slice/src/loader";
import { Grid } from "../../arc-slice/src/grid";

// 7 light dimensions (RED..VIOLET), each bucketed small.
export interface Signature { light: number[]; dark: number[]; }

const bucket = (n: number, a: number, b: number) => (n <= a ? 0 : n <= b ? 1 : 2);
const nonbg = (g: Grid, bg: number) => g.reduce((s,r)=>s+r.filter(v=>v!==bg).length,0);

export function encode(train: Pair[]): Signature {
  const ms = train.map(p => measure(p.input));
  const avgObj = ms.reduce((s,m)=>s+m.nObj,0)/ms.length;
  // RED existence: output content vs input (removes / preserves / adds)
  let ein=0, eout=0; for (const p of train){ const bi=measure(p.input).bg; ein+=nonbg(p.input,bi); eout+=nonbg(p.output,measure(p.output).bg); }
  const existence = ein===0?1 : eout < ein*0.6 ? 0 : eout > ein*1.4 ? 2 : 1;
  // ORANGE quantity
  const quantity = bucket(avgObj, 1, 4);
  // YELLOW motion: do centroids move (dims-equal pairs)?
  let moved=false; for (const p of train){ if(p.input.length!==p.output.length||p.input[0].length!==p.output[0].length) continue;
    const a=measure(p.input).objs.map(o=>`${Math.round(o.feat.cy)},${Math.round(o.feat.cx)}`).sort().join("|");
    const b=measure(p.output).objs.map(o=>`${Math.round(o.feat.cy)},${Math.round(o.feat.cx)}`).sort().join("|");
    if(a!==b) moved=true; }
  const motion = moved?1:0;
  // GREEN structure: dominant object dimensionality (point/line/plane)
  let pts=0,lines=0,planes=0; for (const m of ms) for (const o of m.objs){ const h=o.feat.h,w=o.feat.w; if(o.feat.size<=1)pts++; else if(h===1||w===1)lines++; else planes++; }
  const structure = planes>=lines&&planes>=pts?2 : lines>=pts?1:0;
  // CYAN relation: adjacency/alignment among objects
  const tags = detect(train);
  const relation = tags.includes("OBJECTS_ALIGNED")?2 : avgObj>=2?1:0;
  // BLUE temporal: does the transform change size (a process) vs in-place?
  const temporal = tags.includes("OUT_EQ_IN_DIMS")?0 : 1;
  // VIOLET consciousness: palette richness
  const consciousness = bucket(ms.reduce((s,m)=>s+m.palette.length,0)/ms.length, 2, 4);

  // FREQUENCY DOMAIN GOAL (Alpha/dark_frequencies): Light->inf (grows),
  // Sound->1 (unified/in-place), Magnetism->0 (collapses). The transform's pursuit.
  let szIn=0, szOut=0; for (const p of train){ szIn+=p.input.length*p.input[0].length; szOut+=p.output.length*p.output[0].length; }
  const ratio = szOut/Math.max(1,szIn);
  const domain = ratio > 1.2 ? 2 : ratio < 0.8 ? 0 : 1;   // 2=light/inf, 1=sound/unity, 0=magnetism/void
  // dark-blocked: size-direction and content-direction disagree (goal inverted)
  const darkDomain = ((domain===2 && existence===0) || (domain===0 && existence===2)) ? 1 : 0;

  // DARK profile: where things cancel / collapse to void
  const hasUnique = (tags.includes("UNIQUE_COLOR")||tags.includes("UNIQUE_SHAPE")||tags.includes("UNIQUE_SIZE"))?1:0;
  const collapses = existence===0?1:0;                 // output removes most content
  const colorMap = tags.includes("GLOBAL_COLOR_MAP")?1:0;
  return { light: [existence,quantity,motion,structure,relation,temporal,consciousness,domain], dark: [hasUnique,collapses,colorMap,darkDomain] };
}

/** resonance distance: L1 over light + dark mismatch (lower = more alike). */
export function distance(a: Signature, b: Signature): number {
  let d=0; for (let i=0;i<a.light.length;i++) d+=(i===7?3:1)*Math.abs(a.light[i]-b.light[i]); // domain (idx7) weighted
  for (let i=0;i<a.dark.length;i++) d+=2*Math.abs(a.dark[i]-b.dark[i]);  // dark weighted (verification channel)
  return d;
}
export const sigKey = (s: Signature) => s.light.join("")+"-"+s.dark.join("");
