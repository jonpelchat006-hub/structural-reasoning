# Pin-local colour channels: implementation and limits

The same semantic message can be red/horizontal on one pin and green/diagonal
on another. Translation changes its representation, never its meaning, phase,
scope, payload or evidence identity. Game pixel palette values remain separate
from internal message wavelengths.

## What is connected

- `pin_channels.py`: canonical immutable messages, versioned local codebooks,
  exact encode/decode verification, bounded routing, and explicit unresolved
  questions. A symbol is `(wavelength, orientation)`, not colour alone.
- An unsupported intermediate pin can relay an opaque message without claiming
  to understand it. A missing destination decoder or exhausted route budget
  returns a question and retains the message. Cycles cannot route indefinitely.
- The live agent has planner/control codebooks plus eight action-specific
  outcome-pin codebooks. Each outcome pin has its own assignments and can read
  only its action's supported message types.
- `PriorAgent.do_action_request` records the chosen command and actual SDK data;
  only a returned SDK response creates an executed receipt. The framework still
  owns the single connection. No extra game actions or external prompts are sent.
- `LearningSession` verifies the request/receipt/observation binding before
  journaling it. Measured frame change emits a separate observed message with
  before/after evidence IDs. A successful request is not proof of movement,
  progress, a correct action, or a solved game.
- Existing observation-based pin refinement remains connected. Archives retain
  channel exchanges and codebook manifests alongside raw evidence and rules.
  Replay restores evidence without inventing additional independent trials.

Codebooks currently assign symbols deterministically to **declared** meanings.
They do not learn new action meanings from SHA256. The full digest is retained
as an identity/integrity check; wavelength is only a display/codec coordinate.
Checksums are not authenticated signatures. This is not encryption, an optical
simulation, or evidence for BEC/quantum computation.

## Origins inspected for this change

Repository: `jonpelchat006-hub/structural-reasoning`, main revision inspected
`4718e7e3bd02ee5140cc6fd2577048ba4a20de8f`.

- [FOLDING_CHANNELS](https://github.com/jonpelchat006-hub/structural-reasoning/blob/4718e7e3bd02ee5140cc6fd2577048ba4a20de8f/theory/folding/FOLDING_CHANNELS.md)
  motivates retaining channels through a filled region. Its reported protein
  measurements are not newly reproduced or evidence that ARC routing improves.
- [FOLDING_PIXEL_TRANSMISSION](https://github.com/jonpelchat006-hub/structural-reasoning/blob/4718e7e3bd02ee5140cc6fd2577048ba4a20de8f/theory/folding/FOLDING_PIXEL_TRANSMISSION.md)
  distinguishes fine-scale connections from a coarse boundary. Here that becomes
  an explicit distinction between forwarding and interpreting a message.
- [FOLDING_ENCRYPTION](https://github.com/jonpelchat006-hub/structural-reasoning/blob/4718e7e3bd02ee5140cc6fd2577048ba4a20de8f/agi/theory/FOLDING_ENCRYPTION.md)
  motivates observer-specific representations and visibility. Phase-reconstruction
  experiments do not establish cryptographic security; no such claim is adopted.
- `C:\Users\GamerTech\Desktop\Vesica AI\Shovelcat Security\crypto_euler_phi.py`
  hashes a verification history and maps it into a numeric coordinate. We retain
  the full hash instead of treating a rounded coordinate as a unique identity.
- `...\Shovelcat Security\encrypted_hamiltonian.py` separates internal state,
  public coordinates, and a hash. Its `encrypt_state` returns a digest, not a
  reversible ciphertext. Boundary translation is the transferable design idea.
- `...\Learning\predictive_validation_memory.py` separates prediction from
  actual outcome. Here the requested/executed/observed phases remain distinct.
- `...\Learning\failure_learning.py` keeps failures as test cases. The actual
  zero-scoring submitted package is now a failing regression control.

These legacy files were read, not modified or executed. This was a targeted
survey, not an audit of all Vesica AI work or a rerun of the protein pipeline.

## Fix for the zero-submission defect

Official Swarm constructs agents on one thread and runs them on others. Version 1
opened SQLite in the constructor and crashed on its first worker observation.
Version 2 creates, uses and closes the archive on the game worker. SQLite's
thread check remains enabled; moving an active session between threads is rejected.

`checked_thread_runner.py` propagates worker crashes to a nonzero process exit.
The new notebook launches it with `subprocess.run(..., check=True)`, rather than
allowing a failed shell command to look like a completed notebook. Local paired
comparisons now also create/run agents on different threads.

The scored-run traceback has not been retrieved. The old submitted source is a
confirmed local reproduction of the defect, not direct hosted-log evidence.

## Verification

205 focused tests passed, including:

- red 650 nm / 0 degrees -> opaque relay -> green 530 nm / 90 degrees, identical meaning;
- unknown meanings, cycles, hop bounds, wrong scope/version, altered symbols,
  phase forgery, collision rejection, and deterministic round trips;
- two official Swarm game workers using modules extracted from the newly built
  notebook: each sent four actions, retained five observations and four receipts;
- intentional SDK exception: visible process failure, one attempted action per
  worker, no fabricated receipt and no retry;
- archived version 1: the same test reproduces the SQLite failure and zero actions.

The threaded package test uses a synthetic transport, not hidden games. Real-game
comparison results are stored separately in
`D:\planet\arc_compare\orbital_channels_v2_four_games`.

That four-game comparison completed 8/8 runs (CD82, LP85, LS20, VC33), seed 0,
2,000 game calls per run. Baseline: 3 levels, local SDK mean 1.2984940806.
Candidate: 4 levels, mean 1.3076833265; no whole game wins or lower per-game
scores. This matches version 1's earlier local results, so it does not establish
an improvement caused by channels. Candidate runtimes were 59-84 seconds per
game versus 9-20 seconds for the baseline in this run: bookkeeping overhead
remains material. The comparison's provenance verifies unchanged input sources.

Prepared, not submitted: `prioragent-arc-agi-3-channels-v2.ipynb` (13 cells).
SHA256: `a95002f5fd81ad3950bfdfe997efc576e05f4fff0e1574cf7bee4ce13a72da0f`.
The original .25 notebook and submitted version 1 are untouched.

```powershell
& 'D:\planet\arc_compare\.venv\Scripts\python.exe' -B demo_pin_channels.py
& 'D:\planet\arc_compare\.venv\Scripts\python.exe' -B -m unittest test_pin_channels test_threaded_submission -v
```

## Still open

Automatic discovery of useful object/control meanings, evidence-gated adoption
of new translations, cross-game retrieval/promotion, and circuit-driven probe
scheduling remain research work. A new colour assignment is not new knowledge.
The new channels are connected bookkeeping and a tested translation foundation;
they are not a demonstrated leaderboard gain. No new hosted submission is made
by these scripts or tests.
