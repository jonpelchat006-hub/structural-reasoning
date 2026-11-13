# The AI-image detector thread

An interpretability-first AI-image detector built on the same principle as the folding thread —
*agreement across independent observers is the invariant; disagreement is the depth* — aiming at a
**seam map** (where an image was altered) rather than a black-box score.

The honest state of this thread is captured in **[theory/STATE_OF_THE_DETECTOR.md](theory/STATE_OF_THE_DETECTOR.md)**.
Short version, all measured on a content- and compression-matched, six-generator benchmark:

- **One paid axis works and carries the product:** a semantic vision reader at **stratified AUC 0.932**.
- **The free spectral axes do not separate classes** once content and camera-population are matched — they
  were reading photographic *genre*, not provenance (named and killed via a real-vs-real control arm).
- **Observer _type_ buys ~5× the independence of observer _vendor_** (r = 0.14 vs 0.91/0.94) — the single
  most actionable architectural finding.
- **The seam map does not yet localise** from the committee; a free resonance-residual reader (`spec_dev`)
  localises weakly (0.64 on 10/13, clean control) and is the only live hypothesis left.
- The most valuable thing built is **the measurement discipline** — parity, content stratification,
  same-model controls, pre-registered bars, a real-vs-real control arm — that killed fifteen features in
  one run and turned a confounded 0.952 headline into an honest 0.932.

**Code:** [`code/`](code/) holds the measurement code as it stood on the author's machine: the EXIF-correct
loader `image_io.py`, the observers, the committee and debate experiments, the PRNU and seam tests and the
parity-enforcing benchmarks. The benchmark photos, the cached model outputs and the checker web app are not
included, so the scripts document the method but will not rerun as they are. The design and measurement docs
are in [`theory/`](theory/): `STATE_OF_THE_DETECTOR.md` is the short state-of note and
`STATE_OF_THE_DETECTOR_FULL_2026-07-26.md` is the longer version from the day of the rewrite.

**Session notes, July 26–31 2026.** `theory/` also has the working notes written after the state-of note;
[RESEARCH_MAP.md](../RESEARCH_MAP.md) lists them by date. They cover the PRNU sensor-fingerprint tests, the
per-lens and colour tests, the container-layout test ("the discrete imaginary camera"), the arms, coverage
and report-format notes, and the committee's divergence rule. Later notes correct earlier ones in places, and
say so. Some of the scripts they name are in `code/`. The rest, from July 27 on (`shading_observer.py`,
`robustness.py`, `toolchain3.py`, `arms.py`, `verdict.py`, `void_collapse.py` and others), were run in
working sessions and were not in the folder this code was copied from, so for those runs the note is the
only record.
