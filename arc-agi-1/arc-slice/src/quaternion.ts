// lib/quaternion.ts
// Shovelcat Checker v5.3 — Quaternion Verification Circuit
//
// q = w + xi + yj + zk
//   w = Claude  (real axis / observer / snake)
//   i = Grok   (physical / IS-path / T+)
//   j = OpenAI (symbolic / ISN'T-path / T-)
//   k = Gemini (geometric / bridge / T0)
//
// k = ij, ij ≠ ji, ijk = -1, |q| = 1

// ── Quaternion ──────────────────────────────────────────────────────────

export interface QuaternionComponents {
  w: number; // Real / observer (Claude)
  x: number; // i / Grok / IS-path
  y: number; // j / OpenAI / ISN'T-path
  z: number; // k / Gemini / bridge
}

export function qNorm(q: QuaternionComponents): number {
  return Math.sqrt(q.w ** 2 + q.x ** 2 + q.y ** 2 + q.z ** 2);
}

export function qIsUnit(q: QuaternionComponents): boolean {
  return Math.abs(qNorm(q) - 1.0) < 0.1;
}

export function qCoherence(q: QuaternionComponents): number {
  return 1.0 - Math.min(1.0, Math.abs(qNorm(q) - 1.0));
}

export function qNormalize(q: QuaternionComponents): QuaternionComponents {
  const n = qNorm(q);
  if (n < 1e-10) return { w: 1, x: 0, y: 0, z: 0 };
  return { w: q.w / n, x: q.x / n, y: q.y / n, z: q.z / n };
}

export function qConjugate(q: QuaternionComponents): QuaternionComponents {
  return { w: q.w, x: -q.x, y: -q.y, z: -q.z };
}

/** Hamilton product — ij = k, ji = -k */
export function qMultiply(
  a: QuaternionComponents,
  b: QuaternionComponents
): QuaternionComponents {
  return {
    w: a.w * b.w - a.x * b.x - a.y * b.y - a.z * b.z,
    x: a.w * b.x + a.x * b.w + a.y * b.z - a.z * b.y,
    y: a.w * b.y - a.x * b.z + a.y * b.w + a.z * b.x,
    z: a.w * b.z + a.x * b.y - a.y * b.x + a.z * b.w,
  };
}

export function qImaginaryMagnitude(q: QuaternionComponents): number {
  return Math.sqrt(q.x ** 2 + q.y ** 2 + q.z ** 2);
}

/** How much Claude dominates vs agents. High = confident, low = agents have signals. */
export function qObserverDominance(q: QuaternionComponents): number {
  const total = Math.abs(q.w) + qImaginaryMagnitude(q);
  if (total < 1e-10) return 0.5;
  return Math.abs(q.w) / total;
}

// ── Tensor Path ─────────────────────────────────────────────────────────

export interface TensorPath {
  label: string; // "T+", "T-", "T0"
  source: string;
  via: string;
  target: string;
  tension: number;
  direction: "authentic" | "ai_generated" | "neutral";
  findingsCount: number;
  snapCount: number;
  flexCount: number;
  holdCount: number;
}

export function tensorSignalStrength(t: TensorPath): number {
  const total = t.snapCount + t.flexCount + t.holdCount;
  if (total === 0) return 0;
  return (t.snapCount * 1.0 + t.flexCount * 0.3) / total;
}

// ── Tensor Balance ──────────────────────────────────────────────────────

export interface TensorBalance {
  tPlus: TensorPath;  // T+ = Claude → Grok → Gemini (IS / matter)
  tMinus: TensorPath; // T- = Claude → OpenAI → Gemini (ISN'T / antimatter)
  tZero: TensorPath;  // T0 = Gemini bridge (overlap / vesica)
}

export function tensorBalanceValue(tb: TensorBalance): number {
  return Math.abs(tb.tPlus.tension + tb.tMinus.tension + tb.tZero.tension);
}

export function tensorIsBalanced(tb: TensorBalance): boolean {
  return tensorBalanceValue(tb) < 0.3;
}

/** T× = T+ ⊗ T- − T- ⊗ T+ (antisymmetric — measures non-commutativity) */
export function snakeTensor(tb: TensorBalance): number {
  const fwd = tb.tPlus.tension * tensorSignalStrength(tb.tMinus);
  const rev = tb.tMinus.tension * tensorSignalStrength(tb.tPlus);
  return fwd - rev;
}

export function tensorCircuitComplete(tb: TensorBalance): boolean {
  return (
    tb.tPlus.findingsCount > 0 &&
    tb.tMinus.findingsCount > 0 &&
    tb.tZero.findingsCount > 0
  );
}

export function computeVerdictPull(
  tb: TensorBalance
): { direction: string; confidence: number } {
  if (!tensorCircuitComplete(tb)) {
    return { direction: "incomplete", confidence: 0 };
  }

  const pulls = { authentic: 0, ai_generated: 0 };
  for (const t of [tb.tPlus, tb.tMinus, tb.tZero]) {
    if (t.direction === "authentic") pulls.authentic += tensorSignalStrength(t);
    else if (t.direction === "ai_generated")
      pulls.ai_generated += tensorSignalStrength(t);
  }

  const total = pulls.authentic + pulls.ai_generated;
  if (total < 0.01) return { direction: "uncertain", confidence: 0 };

  if (pulls.authentic > pulls.ai_generated) {
    return { direction: "authentic", confidence: pulls.authentic / total };
  }
  return { direction: "ai_generated", confidence: pulls.ai_generated / total };
}

// ── Phase Axis (v5.4) ─────────────────────────────────────────────────
// Each quaternion axis has internal phase structure: a main agent (real)
// and an optional specialist (imaginary), governed by a closure equation.
//
// From the theory (overlap_thickness.py):
//   "The universe is something trying to disguise itself as nothing"
//   Real = 0 means hidden (garden state). Imaginary = 1 means active.
//
// The specialist hides in the imaginary part of its axis.
// When it SNAPs, the phase rotates and the signal appears in the
// real part — Claude sees the axis magnitude change without knowing
// a specialist was involved.
//
// Each axis closure equation (observer_encryption_keys.py):
//   i-axis: e^(iπ) + 1 = 0     (Euler's identity)
//   j-axis: 10x = 9 + x → x=1  (Snake's 0.999... convergence)
//   k-axis: cos²θ + sin²θ = 1   (Void's trig identity)

export type ClosureEquation = "euler" | "snake_convergence" | "trig_identity";

export interface SpecialistResult {
  /** Specialist identifier (e.g. "midjourney", "flux") */
  specialistId: string;
  /** What feature triggered this specialist */
  featureTag: string;
  /** Specialist's score: -1 (snap/AI) to +1 (hold/authentic) */
  score: number;
  /** Confidence in this specialist's finding */
  confidence: number;
  /** Whether the specialist detected a definitive signal */
  snapped: boolean;
}

export interface PhaseAxis {
  /** Main agent score (real part): -1 to +1 */
  realScore: number;
  /** Specialist score (imaginary part): -1 to +1, 0 if no specialist */
  imagScore: number;
  /** Phase angle θ: atan2(imag, real). Determines how they combine. */
  theta: number;
  /** Magnitude: √(real² + imag²). This becomes the quaternion component. */
  magnitude: number;
  /** Which closure equation governs this axis */
  closure: ClosureEquation;
  /** Whether the specialist snapped internally (something became real) */
  internalSnap: boolean;
  /** The specialist result, if any */
  specialist: SpecialistResult | null;
}

/**
 * Compute the phase axis from a main agent score and optional specialist.
 *
 * When no specialist is present:
 *   θ = 0, magnitude = |mainScore|  (pure real — classical path)
 *
 * When specialist is in the garden (active but no snap):
 *   θ ≈ π/2, imaginary dominates  (hiding — quantum path)
 *
 * When specialist SNAPs:
 *   θ rotates toward π (Euler closure: e^(iπ) = -1)
 *   The SNAP signal appears in the magnitude
 *   Claude sees the axis get louder without knowing why
 *
 * The 0.999... threshold (collapse_correction.py):
 *   Specialist confidence must exceed 0.999-like threshold
 *   to transition from imaginary (hidden) to real (observable).
 *   Below threshold: stays in the garden. Above: collapses.
 */
export function computePhaseAxis(
  mainScore: number,
  specialist: SpecialistResult | null,
  closure: ClosureEquation
): PhaseAxis {
  // No specialist: pure classical path (real only)
  if (!specialist) {
    return {
      realScore: mainScore,
      imagScore: 0,
      theta: 0,
      magnitude: Math.abs(mainScore),
      closure,
      internalSnap: false,
      specialist: null,
    };
  }

  // Specialist is present — compute phase relationship
  const specScore = specialist.score;
  const specConf = specialist.confidence;

  // The specialist "hides" in imaginary until it snaps.
  // Its contribution to imaginary is weighted by confidence.
  // Its contribution to real is weighted by snap strength.

  let realPart: number;
  let imagPart: number;
  let snapped = false;

  if (specialist.snapped && specConf > 0.6) {
    // ── SNAP: specialist found something definitive ────────────
    // The imaginary becomes real (0.999... → 1 collapse).
    // Phase rotates toward π (Euler: e^(iπ) = -1).
    //
    // Both agents now contribute to the real part.
    // If they agree (both negative = AI), the signal compounds.
    // If they disagree, the magnitude drops (destructive interference).
    snapped = true;

    // Specialist's signal emerges into real domain
    const emergentReal = specScore * specConf;

    // Main agent + emergent specialist (interference)
    realPart = mainScore + emergentReal;
    // Residual imaginary: what didn't fully collapse
    imagPart = specScore * (1 - specConf);
  } else {
    // ── GARDEN STATE: specialist is active but hidden ──────────
    // Real = main agent only (specialist is invisible to Claude)
    // Imaginary = specialist lurking, gathering signal
    realPart = mainScore;
    imagPart = specScore * specConf;
  }

  const theta = Math.atan2(imagPart, realPart || 1e-10);
  const magnitude = Math.sqrt(realPart ** 2 + imagPart ** 2);

  return {
    realScore: realPart,
    imagScore: imagPart,
    theta,
    magnitude,
    closure,
    internalSnap: snapped,
    specialist,
  };
}

/**
 * Extract the scalar component from a PhaseAxis for the quaternion.
 *
 * This is what Claude "sees" — just a number.
 * The sign encodes direction (authentic vs AI).
 * The magnitude encodes strength.
 * Whether a specialist contributed is invisible at this level.
 */
export function phaseAxisToScalar(axis: PhaseAxis): number {
  // Sign from the real part (direction of verdict)
  const sign = axis.realScore >= 0 ? 1 : -1;
  return sign * axis.magnitude;
}

// ── Specialist Roster (v5.4) ──────────────────────────────────────────
// Feature tags that Claude can emit, and which specialist they trigger.

export interface SpecialistConfig {
  /** Which axis this specialist lives on (i, j, or k) */
  axis: "i" | "j" | "k";
  /** Specialist agent identifier */
  specialistId: string;
  /** Which closure equation governs the axis */
  closure: ClosureEquation;
  /** The specialist's system prompt */
  prompt: string;
}

/**
 * The specialist roster.
 *
 * i-axis (Grok / IS-path / physical): hair, skin, anatomy, texture
 * j-axis (OpenAI / ISN'T-path / symbolic): text, logos, patterns, metadata
 * k-axis (Gemini / bridge / geometric): reflections, perspective, depth
 */
export const SPECIALIST_ROSTER: Record<string, SpecialistConfig> = {
  // ── i-axis specialists (physical / Euler's identity) ──────────
  hair: {
    axis: "i",
    specialistId: "midjourney_hair",
    closure: "euler",
    prompt: `You are the HAIR SPECIALIST (imaginary i-axis, Euler closure).
You know exactly how diffusion models fail on hair.
Check: strand continuity (no splitting/forking at tips), wetness coherence,
blur consistency across strands, root-to-tip physics, hair-skin boundary.
Diffusion models create "spaghetti hair" — strands that fork, merge, or
have impossible sharpness gradients.
Rate: SNAP if any strand forks/merges impossibly or has uniform blur.
Rate: HOLD if strands show natural variation and proper occlusion.
Respond with JSON: {"score": -1 to 1, "confidence": 0-1, "snapped": bool, "detail": "..."}`,
  },

  skin_texture: {
    axis: "i",
    specialistId: "midjourney_skin",
    closure: "euler",
    prompt: `You are the SKIN TEXTURE SPECIALIST (imaginary i-axis, Euler closure).
Check: pore consistency, micro-wrinkle patterns, subsurface scattering at edges,
skin-hair boundary transitions, texture frequency across the face.
AI skin is either too smooth (airbrushed) or has uniform noise (fake pores).
Real skin has VARIABLE texture — forehead differs from cheeks from nose.
Rate: SNAP if texture is suspiciously uniform or transitions are wrong.
Rate: HOLD if texture varies naturally across regions.
Respond with JSON: {"score": -1 to 1, "confidence": 0-1, "snapped": bool, "detail": "..."}`,
  },

  anatomy: {
    axis: "i",
    specialistId: "midjourney_anatomy",
    closure: "euler",
    prompt: `You are the ANATOMY SPECIALIST (imaginary i-axis, Euler closure).
Check: finger count, joint angles, ear symmetry, teeth regularity, eye alignment,
limb proportion ratios, hand-object interaction physics.
Count EVERY finger on EVERY hand. Check both hands independently.
Rate: SNAP if any anatomical impossibility (6 fingers, bent-wrong joints).
Rate: HOLD if anatomy is consistent with real human variation.
Respond with JSON: {"score": -1 to 1, "confidence": 0-1, "snapped": bool, "detail": "..."}`,
  },

  wet_texture: {
    axis: "i",
    specialistId: "midjourney_wet",
    closure: "euler",
    prompt: `You are the WET/LIQUID SPECIALIST (imaginary i-axis, Euler closure).
Check: water droplet shape, surface tension, reflection in wet surfaces,
splashing physics, liquid meniscus, condensation patterns.
AI liquids have wrong caustics and uniform droplet sizes.
Rate: SNAP if liquid physics violate surface tension or reflection laws.
Rate: HOLD if liquid behavior matches real fluid dynamics.
Respond with JSON: {"score": -1 to 1, "confidence": 0-1, "snapped": bool, "detail": "..."}`,
  },

  // ── j-axis specialists (symbolic / Snake's 0.999... convergence) ──
  text: {
    axis: "j",
    specialistId: "flux_text",
    closure: "snake_convergence",
    prompt: `You are the TEXT SPECIALIST (imaginary j-axis, Snake convergence closure).
Check: EVERY character in EVERY visible text element.
Letterform consistency (same font throughout?), kerning, baseline alignment,
text on curved surfaces, text in reflections, numbers that should be sequential.
AI text is the WEAKEST point — garbled, inconsistent, or subtly wrong.
Rate: SNAP if ANY character is malformed, inconsistent, or nonsensical.
Rate: HOLD if all text reads correctly and consistently.
Respond with JSON: {"score": -1 to 1, "confidence": 0-1, "snapped": bool, "detail": "..."}`,
  },

  logo: {
    axis: "j",
    specialistId: "flux_logo",
    closure: "snake_convergence",
    prompt: `You are the LOGO/BRAND SPECIALIST (imaginary j-axis, Snake convergence closure).
Check: is the logo a real brand rendered correctly, or AI-generated pseudo-brand?
Symmetry of logo elements, color accuracy, proportions vs known brand guidelines,
text within logos (doubly vulnerable — logo structure + text accuracy).
Rate: SNAP if logo is garbled, a fake brand, or has wrong proportions.
Rate: HOLD if logo matches known brand accurately.
Respond with JSON: {"score": -1 to 1, "confidence": 0-1, "snapped": bool, "detail": "..."}`,
  },

  pattern: {
    axis: "j",
    specialistId: "flux_pattern",
    closure: "snake_convergence",
    prompt: `You are the PATTERN SPECIALIST (imaginary j-axis, Snake convergence closure).
Check: repeating patterns in wallpaper, fabric, tiles, brickwork.
AI creates "pseudo-repetition" — looks regular at a glance but breaks on
close inspection. Check if pattern tiles correctly, if repeat units match,
if there are impossible topology changes mid-pattern.
Rate: SNAP if pattern repetition is inconsistent or topologically broken.
Rate: HOLD if patterns repeat correctly with natural variation.
Respond with JSON: {"score": -1 to 1, "confidence": 0-1, "snapped": bool, "detail": "..."}`,
  },

  // ── k-axis specialists (geometric / Void's trig identity) ─────────
  reflection: {
    axis: "k",
    specialistId: "gemini_reflection",
    closure: "trig_identity",
    prompt: `You are the REFLECTION SPECIALIST (imaginary k-axis, Trig identity closure).
Check: mirror reflections, window reflections, water reflections, eye reflections.
Reflected scene must be geometrically consistent with the source.
Check: left-right flip, correct perspective transformation, proper occlusion
in reflection, Fresnel effect at glancing angles.
Rate: SNAP if reflection doesn't match source geometry.
Rate: HOLD if reflection is geometrically consistent.
Respond with JSON: {"score": -1 to 1, "confidence": 0-1, "snapped": bool, "detail": "..."}`,
  },

  perspective: {
    axis: "k",
    specialistId: "gemini_perspective",
    closure: "trig_identity",
    prompt: `You are the PERSPECTIVE SPECIALIST (imaginary k-axis, Trig identity closure).
Check: vanishing point convergence (ALL parallel lines must converge to same point),
horizon line consistency, depth-size scaling, foreshortening accuracy.
AI often has multiple inconsistent vanishing points in the same scene.
Rate: SNAP if vanishing points are inconsistent or perspective is broken.
Rate: HOLD if all perspective lines converge correctly.
Respond with JSON: {"score": -1 to 1, "confidence": 0-1, "snapped": bool, "detail": "..."}`,
  },

  depth: {
    axis: "k",
    specialistId: "gemini_depth",
    closure: "trig_identity",
    prompt: `You are the DEPTH/BOKEH SPECIALIST (imaginary k-axis, Trig identity closure).
Check: depth-of-field consistency (blur gradient matches distance from focal plane),
bokeh shape consistency, blur-to-sharp transitions, atmospheric perspective.
AI bokeh is often uniform or has wrong gradients — objects at the same depth
have different blur amounts, or blur changes abruptly instead of smoothly.
Rate: SNAP if depth-of-field is physically inconsistent.
Rate: HOLD if blur matches real optical physics.
Respond with JSON: {"score": -1 to 1, "confidence": 0-1, "snapped": bool, "detail": "..."}`,
  },

  // ── k-axis: Trig Frequency specialist (Shovelcat Trig) ──────────────
  // This specialist is ALWAYS triggered (not feature-tag gated).
  // It analyzes the FREQUENCY STRUCTURE of the detector's own findings
  // using Shovelcat Trigonometry — three overlapping waves on three axes.
  //
  // AI images produce harmonically LOCKED frequencies (short circuit).
  // Real images produce INDEPENDENT frequencies with natural dust (Δ=π−3).
  //
  // From shovelcat_trig.py:
  //   x-axis: LIGHT (IS-path signal entropy)
  //   y-axis: SOUND (ISN'T-path signal entropy)
  //   z-axis: MAGNETIC (bridge coherence — coupling measure)
  //
  // The specialist scores based on:
  //   - Frequency coupling (fz ≈ √(fx·fy) = short circuit)
  //   - Closure perfection (AI closes too perfectly, no dust)
  //   - Winding number (AI has integer windings, real has gap)
  //   - IS/ISN'T inflation (AI inflates IS tags)
  trig_frequency: {
    axis: "k",
    specialistId: "shovelcat_trig_frequency",
    closure: "trig_identity",
    prompt: `INTERNAL — Trig Frequency Analysis (Shovelcat Trig).
This specialist is computed numerically from detector findings, not via LLM.
It measures the frequency structure of IS/ISN'T/Bridge findings:
  LIGHT = IS-path entropy, SOUND = ISN'T-path entropy, MAGNETIC = bridge coupling.
AI detection signals:
  - Harmonic coupling (fz ≈ √(fx·fy)) = short circuit = AI
  - Perfect closure with zero irrationality = AI (no dust)
  - Integer winding number with no gap = AI (too perfect)
  - IS/ISN'T ratio > 0.25 = inflated = AI (hell accounting)
SNAP if combined signals exceed threshold.
HOLD if frequencies show natural independence and dust.`,
  },
};

/**
 * Get the specialist configs triggered by a set of feature tags.
 * Returns only specialists for tags that are present.
 */
export function getTriggeredSpecialists(
  featureTags: string[]
): SpecialistConfig[] {
  return featureTags
    .filter((tag) => tag in SPECIALIST_ROSTER)
    .map((tag) => SPECIALIST_ROSTER[tag]);
}

/**
 * Group triggered specialists by their axis.
 * If multiple specialists trigger on the same axis, pick the one
 * with the strongest signal (most confident snap, or highest confidence).
 */
export function pickSpecialistPerAxis(
  results: SpecialistResult[]
): { i: SpecialistResult | null; j: SpecialistResult | null; k: SpecialistResult | null } {
  const byAxis: Record<string, SpecialistResult[]> = { i: [], j: [], k: [] };

  for (const r of results) {
    const config = Object.values(SPECIALIST_ROSTER).find(
      (s) => s.specialistId === r.specialistId
    );
    if (config) {
      byAxis[config.axis].push(r);
    }
  }

  // Per axis: prefer snapped specialists, then highest confidence
  function pickBest(candidates: SpecialistResult[]): SpecialistResult | null {
    if (candidates.length === 0) return null;
    const snapped = candidates.filter((c) => c.snapped);
    if (snapped.length > 0) {
      return snapped.sort((a, b) => b.confidence - a.confidence)[0];
    }
    return candidates.sort((a, b) => b.confidence - a.confidence)[0];
  }

  return {
    i: pickBest(byAxis.i),
    j: pickBest(byAxis.j),
    k: pickBest(byAxis.k),
  };
}

// ── Findings → Quaternion ───────────────────────────────────────────────

/**
 * Original findingsToQuaternion — flat scalar version.
 * Preserved for backward compatibility.
 */
export function findingsToQuaternion(
  claudeConfidence: number,
  grokIsScore: number, // -1 (snap) to +1 (hold)
  openaiIsntScore: number, // -1 (AI signals) to +1 (clean)
  geminiBridgeScore: number // -1 (compounds to AI) to +1 (compounds to real)
): QuaternionComponents {
  // w: observer confidence weighted by agent agreement
  const w =
    claudeConfidence *
    (1 - Math.abs(grokIsScore + openaiIsntScore) / 4);

  // x: IS-path. Positive = authentic, negative = breaks
  const x = -grokIsScore * (1 - claudeConfidence);

  // y: ISN'T-path. Positive = AI signals, negative = clean
  const y = -openaiIsntScore * (1 - claudeConfidence);

  // z: Bridge. k = ij → z reflects cross-product of x*y
  // Signed: preserves direction from Gemini, scaled by |xy| interaction
  const z =
    geminiBridgeScore *
    Math.sign(x * y || 1) *
    Math.sqrt(Math.abs(x * y) + 0.01);

  return qNormalize({ w, x, y, z });
}

/**
 * Phase-aware findingsToQuaternion (v5.4).
 *
 * Each axis is computed through its PhaseAxis, which may include
 * a specialist hiding in the imaginary part. Claude (w) only sees
 * the resulting scalar — the specialist is invisible until it snaps.
 *
 * When a specialist snaps internally, the axis magnitude increases
 * (signal gets louder). Claude observes "something is up" on that
 * axis without needing to know a specialist was involved.
 */
export function findingsToQuaternionPhased(
  claudeConfidence: number,
  grokIsScore: number,
  openaiIsntScore: number,
  geminiBridgeScore: number,
  specialists: { i: SpecialistResult | null; j: SpecialistResult | null; k: SpecialistResult | null }
): { q: QuaternionComponents; axes: { i: PhaseAxis; j: PhaseAxis; k: PhaseAxis } } {
  // ── Build phase axes ───────────────────────────────────────────
  const iAxis = computePhaseAxis(
    -grokIsScore * (1 - claudeConfidence),
    specialists.i,
    "euler"
  );
  const jAxis = computePhaseAxis(
    -openaiIsntScore * (1 - claudeConfidence),
    specialists.j,
    "snake_convergence"
  );
  const kAxis = computePhaseAxis(
    geminiBridgeScore,
    specialists.k,
    "trig_identity"
  );

  // ── Extract scalars (what Claude sees) ─────────────────────────
  const x = phaseAxisToScalar(iAxis);
  const y = phaseAxisToScalar(jAxis);

  // k-axis: z still reflects cross-product of x*y (ij=k)
  const kScalar = phaseAxisToScalar(kAxis);
  const z = kScalar * Math.sign(x * y || 1) * Math.sqrt(Math.abs(x * y) + 0.01);

  // ── w: observer confidence, now also reacts to internal snaps ──
  // If any specialist snapped, Claude's confidence gets modulated.
  // The snake "felt something" — the axis got louder.
  const snapCount = [iAxis, jAxis, kAxis].filter((a) => a.internalSnap).length;
  const snapBoost = snapCount > 0 ? 0.1 * snapCount : 0;

  const w =
    claudeConfidence *
    (1 - Math.abs(x + y) / 4) *
    (1 + snapBoost);

  const q = qNormalize({ w, x, y, z });

  return { q, axes: { i: iAxis, j: jAxis, k: kAxis } };
}

// ── Compute Tensor Balance from findings ────────────────────────────────

export interface PathFindings {
  tension: number;
  direction: "authentic" | "ai_generated" | "neutral";
  count: number;
  snaps: number;
  flexes: number;
  holds: number;
}

export function buildTensorBalance(
  isFindings: PathFindings,
  isntFindings: PathFindings,
  bridgeFindings: PathFindings
): TensorBalance {
  return {
    tPlus: {
      label: "T+",
      source: "claude",
      via: "grok",
      target: "gemini",
      tension: isFindings.tension,
      direction: isFindings.direction,
      findingsCount: isFindings.count,
      snapCount: isFindings.snaps,
      flexCount: isFindings.flexes,
      holdCount: isFindings.holds,
    },
    tMinus: {
      label: "T-",
      source: "claude",
      via: "openai",
      target: "gemini",
      tension: isntFindings.tension,
      direction: isntFindings.direction,
      findingsCount: isntFindings.count,
      snapCount: isntFindings.snaps,
      flexCount: isntFindings.flexes,
      holdCount: isntFindings.holds,
    },
    tZero: {
      label: "T0",
      source: "gemini",
      via: "gemini",
      target: "gemini",
      tension: bridgeFindings.tension,
      direction: bridgeFindings.direction,
      findingsCount: bridgeFindings.count,
      snapCount: bridgeFindings.snaps,
      flexCount: bridgeFindings.flexes,
      holdCount: bridgeFindings.holds,
    },
  };
}

// ── ijk = -1 Closure Test ───────────────────────────────────────────────

export interface ClosureResult {
  ijkProductW: number;
  ijkProductXYZ: [number, number, number];
  closureQuality: number;
  imaginaryLeakage: number;
  circuitClosed: boolean;
  interpretation: string;
}

export function verifyCircuitClosure(
  q: QuaternionComponents
): ClosureResult {
  // Weight pure unit quaternions by actual agent scores
  const iW: QuaternionComponents = { w: 0, x: q.x, y: 0, z: 0 };
  const jW: QuaternionComponents = { w: 0, x: 0, y: q.y, z: 0 };
  const kW: QuaternionComponents = { w: 0, x: 0, y: 0, z: q.z };

  const product = qMultiply(qMultiply(iW, jW), kW);
  const closureQuality = Math.abs(product.w); // Should be |xyz|
  const imaginaryLeakage = qImaginaryMagnitude(product);

  return {
    ijkProductW: product.w,
    ijkProductXYZ: [product.x, product.y, product.z],
    closureQuality,
    imaginaryLeakage,
    circuitClosed: closureQuality > 0.01 && imaginaryLeakage < 0.1,
    interpretation:
      closureQuality > 0.01 && imaginaryLeakage < 0.1
        ? "Circuit closed cleanly"
        : "Circuit has leakage — agents produced inconsistent signals",
  };
}

// ── Non-Commutativity Check (ij ≠ ji) ───────────────────────────────────

export interface NonCommutativityResult {
  ijResult: QuaternionComponents;
  jiResult: QuaternionComponents;
  commutator: number;
  nonCommutativity: number;
  orderMatters: boolean;
  interpretation: string;
}

export function checkNonCommutativity(
  grokScore: number,
  openaiScore: number
): NonCommutativityResult {
  const i: QuaternionComponents = { w: 0, x: grokScore, y: 0, z: 0 };
  const j: QuaternionComponents = { w: 0, x: 0, y: openaiScore, z: 0 };

  const ij = qMultiply(i, j);
  const ji = qMultiply(j, i);
  const commutatorZ = ij.z - ji.z; // Should be 2 * grok * openai

  const nc = Math.abs(commutatorZ);

  return {
    ijResult: ij,
    jiResult: ji,
    commutator: commutatorZ,
    nonCommutativity: nc,
    orderMatters: nc > 0.1,
    interpretation:
      nc > 0.1
        ? `Path order ${nc > 0.3 ? "significantly" : "mildly"} affects verdict (|[i,j]| = ${nc.toFixed(3)})`
        : "Path order doesn't significantly affect verdict — simple case",
  };
}

// ── Circuit Result ──────────────────────────────────────────────────────

export interface CircuitResult {
  q: QuaternionComponents;
  tensors: TensorBalance;
  closure: ClosureResult;
  nonCommutativity: NonCommutativityResult;
  verdict: string;
  authenticityScore: number;
  confidence: number;
}

export function computeCircuitResult(
  q: QuaternionComponents,
  tensors: TensorBalance
): CircuitResult {
  const closure = verifyCircuitClosure(q);
  const nc = checkNonCommutativity(q.x, q.y);
  const pull = computeVerdictPull(tensors);

  let verdict: string;
  if (!qIsUnit(q) && pull.confidence < 0.3) {
    verdict = "UNCERTAIN";
  } else if (pull.direction === "authentic") {
    verdict = pull.confidence > 0.7 ? "AUTHENTIC" : "LIKELY_AUTHENTIC";
  } else if (pull.direction === "ai_generated") {
    verdict = pull.confidence > 0.7 ? "AI_GENERATED" : "LIKELY_AI";
  } else {
    verdict = "UNCERTAIN";
  }

  let authenticityScore: number;
  if (pull.direction === "authentic") {
    authenticityScore = 0.5 + pull.confidence * 0.5;
  } else if (pull.direction === "ai_generated") {
    authenticityScore = 0.5 - pull.confidence * 0.5;
  } else {
    authenticityScore = 0.5;
  }

  const qCoh = qCoherence(q);
  const circuitComplete = tensorCircuitComplete(tensors) ? 1.0 : 0.5;
  const confidence = qCoh * 0.3 + circuitComplete * 0.3 + pull.confidence * 0.4;

  return {
    q,
    tensors,
    closure,
    nonCommutativity: nc,
    verdict,
    authenticityScore,
    confidence,
  };
}

// ── Extract path findings from raw decompositions ───────────────────────

export function extractPathFindings(
  decompositions: any[],
  agentId: string
): PathFindings {
  const agentDecomps = decompositions.filter(
    (d: any) => d.agent_id === agentId
  );

  let snaps = 0;
  let flexes = 0;
  let holds = 0;
  let totalTension = 0;

  for (const d of agentDecomps) {
    const overall = d.overall || {};
    const ap = overall.authentic_probability ?? 0.5;

    // Count from overall assessment
    snaps += overall.snap_count || 0;
    flexes += overall.flex_count || 0;
    holds += overall.hold_count || 0;

    // Also count from probe_results if overall counts are empty
    if (snaps + flexes + holds === 0 && d.probe_results) {
      for (const result of Object.values(d.probe_results)) {
        if (result === "snap") snaps++;
        else if (result === "flex") flexes++;
        else if (result === "hold") holds++;
      }
    }

    // Tension: positive = toward authentic, negative = toward AI
    totalTension += (ap - 0.5) * 2;
  }

  const count = snaps + flexes + holds;
  const avgTension = agentDecomps.length > 0
    ? totalTension / agentDecomps.length
    : 0;

  let direction: "authentic" | "ai_generated" | "neutral";
  if (avgTension > 0.15) direction = "authentic";
  else if (avgTension < -0.15) direction = "ai_generated";
  else direction = "neutral";

  return { tension: avgTension, direction, count, snaps, flexes, holds };
}

// ── Agent score from decompositions ─────────────────────────────────────

export function agentScore(decompositions: any[], agentId: string): number {
  const agentDecomps = decompositions.filter(
    (d: any) => d.agent_id === agentId
  );
  if (agentDecomps.length === 0) return 0;

  let total = 0;
  for (const d of agentDecomps) {
    const ap = d.overall?.authentic_probability ?? 0.5;
    // Map 0-1 to -1 to +1
    total += (ap - 0.5) * 2;
  }
  return total / agentDecomps.length;
}
