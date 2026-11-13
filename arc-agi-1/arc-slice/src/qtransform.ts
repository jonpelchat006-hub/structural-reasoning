// qtransform.ts — the transform-aware bridge (the corkscrew at an angle).
// A template lifted from task A can solve task B even when B is A's pattern
// under a square symmetry. We represent the symmetry group D4, reuse the
// quaternion Hamilton algebra to compose rotations and read off the
// "angle difference" between roof and floor, then conjugate the template by it.
import { Op } from "./dsl";
import { Program } from "./program";
import { QuaternionComponents, qMultiply, qConjugate, qNormalize } from "./quaternion";

// D4 element = optional flip then rotation by r*90 about the page (z-axis).
export interface D4 { flip: 0 | 1; r: 0 | 1 | 2 | 3; }
export const D4_ALL: D4[] = [0, 1].flatMap((flip) => [0, 1, 2, 3].map((r) => ({ flip: flip as 0|1, r: r as 0|1|2|3 })));

/** rotation r*90 about z as a unit quaternion (half-angle r*45deg). */
export function rotQuat(r: number): QuaternionComponents {
  const half = (r * Math.PI) / 4;
  return qNormalize({ w: Math.cos(half), x: 0, y: 0, z: Math.sin(half) });
}

/** the angle-difference quaternion that carries roof orientation onto floor:
 *  q_rel = q_floor * conj(q_roof)   (Hamilton product, your quaternion.ts). */
export function relativeQuat(rRoof: number, rFloor: number): QuaternionComponents {
  return qMultiply(rotQuat(rFloor), qConjugate(rotQuat(rRoof)));
}

/** recover rotation index (0..3) from a rotation quaternion's z/w. */
export function quatToR(q: QuaternionComponents): number {
  const ang = 2 * Math.atan2(q.z, q.w);            // total rotation angle
  return ((Math.round(ang / (Math.PI / 2)) % 4) + 4) % 4;
}

// grid ops realising g and its inverse, expressed in the existing DSL.
const rotOps = (r: number): Op[] => (r % 4 === 0 ? [] : [{ name: "rotate", params: { k: r % 4 } }]);
export function gOps(g: D4): Op[] { return [...(g.flip ? [{ name: "flipH", params: {} } as Op] : []), ...rotOps(g.r)]; }
export function gInvOps(g: D4): Op[] { return [...rotOps((4 - g.r) % 4), ...(g.flip ? [{ name: "flipH", params: {} } as Op] : [])]; }

/** conjugate a bound template program by g:  input -> g^-1 -> template -> g. */
export function conjugate(bound: Program, g: D4): Program {
  return [...gInvOps(g), ...bound, ...gOps(g)];
}

export function d4Label(g: D4): string {
  return `${g.flip ? "flip+" : ""}rot${g.r * 90}`;
}
