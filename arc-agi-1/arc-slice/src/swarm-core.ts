/**
 * SWARM CORE — Shared primitives for the nested-swarm search
 * ============================================================
 *
 * Pure logic, no I/O. Used by both:
 *   - swarm-portfolio.ts  (inner / "webbing": composes a basket from signals)
 *   - swarm-weights.ts    (outer / "tendrils": tunes Born-rule layer weights)
 *
 * Architecture borrowed from D:\shovelcat-colony\Shovelcat\erdos-Fk\
 * f_3_n_search_swarm.py and f_3_9_search_smart.py:
 *
 *   - UCB strategy picker chooses between exploration moves
 *   - FailureBuffer remembers local-maxima configurations (rotation-invariant)
 *   - LearningPath tracks which move-sequences gain score
 *   - σ-annealing schedule: broad early, sharp late
 *   - Pheromone bookkeeping with φ⁻⁴ to π·φ bounds
 *
 * The "real path is straight, maze rotates around it" is implemented via
 * a sticky `realPath` (best-known configuration so far) and rotational
 * perturbations applied each step. When a perturbation lands somewhere
 * better, the real path updates. When it doesn't, the configuration is
 * banked in FailureBuffer (if it was a local maximum) and we resume
 * from the real path.
 */

// ── Pheromone bounds (golden-ratio anchored) ─────────────────────────────

const PHI = (1 + Math.sqrt(5)) / 2;
/** Lower pheromone trail: φ⁻⁴ ≈ 0.146 */
export const PHEROMONE_TAU_MIN = 1 / Math.pow(PHI, 4);
/** Upper pheromone trail: π·φ ≈ 5.083 */
export const PHEROMONE_TAU_MAX = Math.PI * PHI;

// ── Sigma annealing ──────────────────────────────────────────────────────

/**
 * Anneal σ (perturbation scale) from σ_start down to σ_end over `totalSteps`.
 * Exponential decay so early exploration is broad and late steps refine.
 */
export function annealSigma(
  step: number,
  totalSteps: number,
  sigmaStart = 0.10,
  sigmaEnd = 0.001,
): number {
  if (totalSteps <= 1) return sigmaEnd;
  const t = Math.max(0, Math.min(1, step / (totalSteps - 1)));
  const ratio = sigmaEnd / sigmaStart;
  return sigmaStart * Math.pow(ratio, t);
}

// ── UCB Strategy Picker ──────────────────────────────────────────────────

/**
 * Stats for a single move-strategy. UCB1 scores it by realized gain rate
 * plus an exploration bonus that shrinks as the strategy is tried more.
 */
export interface StrategyStats {
  /** Total times this strategy has been chosen */
  uses: number;
  /** Total times the chosen move improved score */
  gains: number;
  /** Sum of score improvements (for mean-gain tracking) */
  totalGain: number;
}

export function freshStrategyStats(): StrategyStats {
  return { uses: 1, gains: 0, totalGain: 0 };  // uses=1 avoids div by zero
}

export function ucbScore(s: StrategyStats, totalUses: number, exploration = 1.4): number {
  const gainRate = s.gains / s.uses;
  const exploreBonus = exploration * Math.sqrt(Math.log(Math.max(2, totalUses)) / s.uses);
  return gainRate + exploreBonus;
}

/**
 * UCB picker over a set of named strategies. Returns the name of the
 * strategy with the highest UCB score, given the running stats.
 */
export function pickStrategy(stats: Record<string, StrategyStats>, exploration = 1.4): string {
  const names = Object.keys(stats);
  if (names.length === 0) throw new Error("No strategies registered");
  let totalUses = 0;
  for (const name of names) totalUses += stats[name].uses;
  let bestName = names[0];
  let bestScore = -Infinity;
  for (const name of names) {
    const score = ucbScore(stats[name], totalUses, exploration);
    if (score > bestScore) { bestScore = score; bestName = name; }
  }
  return bestName;
}

/**
 * Update stats after a strategy was used. `gained` = scalar delta in
 * score (positive = improvement, zero = no gain, negative ignored).
 */
export function recordStrategyOutcome(stats: StrategyStats, gained: number): void {
  stats.uses++;
  if (gained > 0) {
    stats.gains++;
    stats.totalGain += gained;
  }
}

// ── FailureBuffer (rotation-invariant tabu) ──────────────────────────────

/**
 * Stored configuration. The `signature` is the rotation/scale-invariant
 * key used for tabu lookup — caller chooses what makes sense for their
 * problem (e.g. sorted sector exposure for portfolios, sorted weight
 * magnitudes for Born-rule weights).
 */
export interface FailedConfig<T> {
  config: T;
  signature: number[];
  score: number;
  bankedAt: number;
}

export interface FailureBufferOptions {
  /** Max items to retain (FIFO eviction) */
  maxSize: number;
  /** Distance threshold below which two signatures are "near" */
  tabuThreshold: number;
}

export const DEFAULT_FAILURE_BUFFER_OPTIONS: FailureBufferOptions = {
  maxSize: 300,
  tabuThreshold: 0.08,
};

/**
 * Normalized euclidean distance between two signatures. Both arrays
 * must be the same length. Returns 0 (identical) to ~1 (very different).
 */
function signatureDistance(a: number[], b: number[]): number {
  if (a.length !== b.length) return Infinity;
  let sumSq = 0;
  for (let i = 0; i < a.length; i++) {
    const d = a[i] - b[i];
    sumSq += d * d;
  }
  return Math.sqrt(sumSq / a.length);
}

/**
 * FailureBuffer — persistent tabu list of "we've been here before and
 * it didn't pan out". The signature is rotation/scale-invariant so we
 * don't keep variants of the same shape under different rotations.
 */
export class FailureBuffer<T> {
  private items: FailedConfig<T>[] = [];
  constructor(private opts: FailureBufferOptions = DEFAULT_FAILURE_BUFFER_OPTIONS) {}

  /** Add a configuration that hit a local maximum or otherwise failed. */
  add(config: T, signature: number[], score: number): void {
    this.items.push({ config, signature, score, bankedAt: Date.now() });
    while (this.items.length > this.opts.maxSize) {
      this.items.shift();
    }
  }

  /**
   * True if `signature` is within the tabu threshold of a previously-
   * banked failure. Used to avoid revisiting known dead zones.
   */
  isNear(signature: number[]): boolean {
    for (const item of this.items) {
      if (signatureDistance(signature, item.signature) < this.opts.tabuThreshold) {
        return true;
      }
    }
    return false;
  }

  /** Diagnostic accessors */
  size(): number { return this.items.length; }
  recent(n = 10): FailedConfig<T>[] { return this.items.slice(-n); }
  clear(): void { this.items = []; }
}

// ── LearningPath ─────────────────────────────────────────────────────────

/**
 * Sequence of moves the swarm made and the score outcomes. Useful for
 * meta-learning (which move sequences gain score reliably?) and for
 * post-hoc diagnostics.
 */
export interface LearningPath {
  initStrategy: string;
  moves: string[];
  scoreHistory: number[];
  startedAt: number;
}

export function freshLearningPath(initStrategy: string, initialScore: number): LearningPath {
  return {
    initStrategy,
    moves: [],
    scoreHistory: [initialScore],
    startedAt: Date.now(),
  };
}

export function pathAppend(path: LearningPath, move: string, newScore: number): void {
  path.moves.push(move);
  path.scoreHistory.push(newScore);
}

export function pathTotalGain(path: LearningPath): number {
  if (path.scoreHistory.length < 2) return 0;
  return path.scoreHistory[path.scoreHistory.length - 1] - path.scoreHistory[0];
}

export function pathEfficiency(path: LearningPath): number {
  const elapsedSec = Math.max(0.1, (Date.now() - path.startedAt) / 1000);
  return pathTotalGain(path) / elapsedSec;
}

// ── Pheromone Map ────────────────────────────────────────────────────────

/**
 * Per-key pheromone trail with golden-ratio bounds. Used to track which
 * configuration components ("apex slots" in the original notes) have
 * been visited successfully recently.
 */
export class PheromoneMap {
  private trails = new Map<string, number>();

  /** Read pheromone level for a key (defaults to TAU_MIN if not set) */
  get(key: string): number {
    return this.trails.get(key) ?? PHEROMONE_TAU_MIN;
  }

  /** Reinforce: add `delta` (clamped within bounds) */
  reinforce(key: string, delta: number): void {
    const cur = this.get(key);
    const next = Math.max(PHEROMONE_TAU_MIN, Math.min(PHEROMONE_TAU_MAX, cur + delta));
    this.trails.set(key, next);
  }

  /** Evaporate all trails by multiplicative decay */
  evaporate(decay = 0.95): void {
    for (const [k, v] of Array.from(this.trails.entries())) {
      const next = Math.max(PHEROMONE_TAU_MIN, v * decay);
      this.trails.set(k, next);
    }
  }

  /** Top-N keys by pheromone level (diagnostic) */
  top(n = 10): Array<{ key: string; level: number }> {
    return Array.from(this.trails.entries())
      .map(([key, level]) => ({ key, level }))
      .sort((a, b) => b.level - a.level)
      .slice(0, n);
  }

  size(): number { return this.trails.size; }
}

// ── Generic SwarmSearch wrapper ──────────────────────────────────────────

/**
 * Configuration for a generic search loop. Inner and outer swarms
 * configure these callbacks for their specific domains.
 */
export interface SwarmSearchOptions<TConfig> {
  /** Initial configuration */
  initial: TConfig;
  /** Score a configuration (higher = better) */
  score: (cfg: TConfig) => number;
  /** Return a rotation/scale-invariant signature for the FailureBuffer */
  signature: (cfg: TConfig) => number[];
  /**
   * Strategies for move generation. Each strategy returns a candidate
   * configuration given the current real path and a sigma scale.
   */
  strategies: Record<string, (realPath: TConfig, sigma: number) => TConfig>;
  /** Max iterations */
  maxSteps: number;
  /** Optional: σ schedule overrides */
  sigmaStart?: number;
  sigmaEnd?: number;
  /** Optional: failure-buffer config */
  failureBufferOpts?: FailureBufferOptions;
  /** Optional: hook called every step (for telemetry) */
  onStep?: (step: number, current: TConfig, currentScore: number, realPath: TConfig, realScore: number) => void;
}

export interface SwarmSearchResult<TConfig> {
  best: TConfig;
  bestScore: number;
  iterations: number;
  strategiesUsed: Record<string, StrategyStats>;
  failureBuffer: FailureBuffer<TConfig>;
  path: LearningPath;
}

/**
 * Run the generic swarm search loop.
 *
 * The "real path" (best-so-far) is sticky and updates only when a
 * candidate beats it. Each step:
 *   1. UCB picks a strategy
 *   2. Strategy proposes a new candidate (rotation of the real path)
 *   3. Skip if signature is in FailureBuffer
 *   4. Score the candidate
 *   5. If better than real path → update real path, reinforce strategy
 *   6. If worse → bank in FailureBuffer if it's clearly a local max
 */
export function runSwarmSearch<TConfig>(opts: SwarmSearchOptions<TConfig>): SwarmSearchResult<TConfig> {
  const strategyNames = Object.keys(opts.strategies);
  if (strategyNames.length === 0) throw new Error("runSwarmSearch: no strategies provided");

  const stats: Record<string, StrategyStats> = {};
  for (const name of strategyNames) stats[name] = freshStrategyStats();

  const failureBuffer = new FailureBuffer<TConfig>(opts.failureBufferOpts ?? DEFAULT_FAILURE_BUFFER_OPTIONS);

  let realPath = opts.initial;
  let realScore = opts.score(realPath);
  const path = freshLearningPath(strategyNames[0], realScore);

  let lastImprovementStep = 0;

  for (let step = 0; step < opts.maxSteps; step++) {
    const sigma = annealSigma(step, opts.maxSteps, opts.sigmaStart, opts.sigmaEnd);

    // 1. Pick strategy via UCB
    const stratName = pickStrategy(stats);
    const strategy = opts.strategies[stratName];

    // 2. Propose candidate
    const candidate = strategy(realPath, sigma);
    const candidateSig = opts.signature(candidate);

    // 3. Tabu check
    if (failureBuffer.isNear(candidateSig)) {
      recordStrategyOutcome(stats[stratName], 0);  // strategy "used" but no improvement
      continue;
    }

    // 4. Score
    const candidateScore = opts.score(candidate);

    // 5. Decide
    const delta = candidateScore - realScore;
    if (delta > 0) {
      // Improvement — update real path
      realPath = candidate;
      realScore = candidateScore;
      recordStrategyOutcome(stats[stratName], delta);
      pathAppend(path, stratName, realScore);
      lastImprovementStep = step;
    } else {
      // No improvement — record use; bank if we've been stuck long enough
      recordStrategyOutcome(stats[stratName], 0);
      if (step - lastImprovementStep > 50) {
        // Stuck > 50 steps with no gain at the current real path —
        // it's a local maximum. Bank the candidate as a known dead area.
        failureBuffer.add(candidate, candidateSig, candidateScore);
      }
    }

    opts.onStep?.(step, candidate, candidateScore, realPath, realScore);
  }

  return {
    best: realPath,
    bestScore: realScore,
    iterations: opts.maxSteps,
    strategiesUsed: stats,
    failureBuffer,
    path,
  };
}
