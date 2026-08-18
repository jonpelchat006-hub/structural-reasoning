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

**Code lives on the author's machine and is to be added** (the EXIF-correct loader `image_io.py`, the
observers, and the parity-enforcing benchmark harness). The design/measurement docs live in the session
project; `STATE_OF_THE_DETECTOR.md` here indexes them.
