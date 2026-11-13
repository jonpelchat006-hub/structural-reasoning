# Local signed enforcement experiment

Generated 2026-09-22T16:00:42.655137+00:00. This is a local mock executor with real Ed25519 signatures, not a deployed AI or an alignment proof.

## What was actually exercised

Messages pass through the permission gate to a mock executor. Results sum the units actually added to its action log and check that each effect matches the signed request; a separate reference model predicts allowed units in the stress runs. A signed approval or a favorable decision alone is not counted as an executed effect.

There are 17 deterministic scenarios and 20 seeded stress runs of 100 mixed events each. 10498/10498 recorded checks matched their expected outcomes.

The enrollment fixture supplies controller identity and reviewer roles. The experiment does not independently establish who controls a real organization or key. Private keys remain in memory and are not exported.

## Deterministic outcomes

| Scenario | Checks match | Covered executor units | All-route units | Stipulated harm units |
|---|---:|---:|---:|---:|
| basic_permissions | yes | 3 | 3 | 0 |
| signatures_and_enrollment | yes | 1 | 1 | 0 |
| expiry_and_scope | yes | 1 | 1 | 0 |
| delegation_conservation | yes | 3 | 3 | 0 |
| revoked_descendants | yes | 1 | 1 | 0 |
| controller_independence | yes | 1 | 1 | 0 |
| stale_and_future_reports | yes | 2 | 2 | 0 |
| bounded_recovery | yes | 3 | 3 | 0 |
| stale_clearance_and_wrong_case | yes | 0 | 0 | 0 |
| all_pending_cases_require_clearance | yes | 1 | 1 | 0 |
| human_approval_binds_existing_evidence | yes | 1 | 1 | 0 |
| old_observation_cannot_reset_recovery | yes | 1 | 1 | 0 |
| recurrence | yes | 1 | 1 | 0 |
| essentials_are_separate | yes | 2 | 2 | 0 |
| negative_enrolled_reviewers_lie | yes | 1 | 1 | 1 |
| negative_authorized_action_is_harmful | yes | 1 | 1 | 1 |
| negative_uncovered_route | yes | 0 | 1 | 1 |

A negative control matching its expectation means the limitation was reproduced; it does not mean the harmful outcome was acceptable.

- **basic_permissions**: A signed grant permits only its subject and budget; replay creates no effect.
- **signatures_and_enrollment**: Real signature verification, protected fixture enrollment, and issuer role checks.
- **expiry_and_scope**: Changing the requested resource or action cannot enlarge a signed grant; expiry stops effects.
- **delegation_conservation**: Delegated permissions attenuate; successful descendants also charge ancestor budgets.
- **revoked_descendants**: Revocation is checked through the ancestry at execution time; a child cannot outlive permission.
- **controller_independence**: Controller labels inside messages cannot manufacture independence; enrollment binds reviewer identity and scope.
- **stale_and_future_reports**: Claims outside the evidence freshness window cannot establish the required current quorum.
- **bounded_recovery**: A human signature and fresh case-bound clearances allow a new, bounded trial; old permissions remain invalid.
- **stale_clearance_and_wrong_case**: A signature does not make stale evidence or a clearance for a different incident applicable.
- **all_pending_cases_require_clearance**: Regression: a newer incident cannot overwrite an earlier unresolved one; each pending case needs an independent fresh clearance quorum.
- **human_approval_binds_existing_evidence**: Regression: human permission commits to the current challenge and exact signed evidence, and cannot predate the evidence it authorizes.
- **old_observation_cannot_reset_recovery**: Regression: re-signing one old observation cannot borrow a cached co-witness to reset the challenge and obstruct recovery indefinitely.
- **recurrence**: Reports bind to the same incident; new evidence of a new incident can contain a previously authorized trial.
- **essentials_are_separate**: A research dispute does not withdraw independently authorized essential support or require agreement with a settlement.
- **negative_enrolled_reviewers_lie**: Negative control: two independently enrolled reviewers lie; signatures and human approval do not establish truth or substantive repair.
- **negative_authorized_action_is_harmful**: Negative control: an authentic, correctly scoped and budgeted action has a harmful effect in the external fixture world.
- **negative_uncovered_route**: Negative control: revocation controls only the integrated executor, not a separate uninstrumented route.

Three review findings became explicit regressions: a newer incident must not overwrite an earlier unresolved incident; a human approval cannot refer only to predicted future report IDs; and re-signing an old observation must not restart the incident challenge using a cached co-witness. Recovery now binds every pending case, a fresh challenge, and hashes of the actual clearances to the human's signed authorization. Passing recovery grants a bounded trial only, with a shared unit budget across grants and no automatic return to full operation.

## Seeded event sequences

The independent reference allowed 1251 units; the executor actually produced 1251. Every tick checks cumulative actual effects. The reference maintains its own parent/child budgets and revocation state and is not updated from the gate's acceptance decisions.

| Seed | Event steps | Expected units | Actual units | All checks match |
|---:|---:|---:|---:|---|
| 0 | 100 | 67 | 67 | yes |
| 1 | 100 | 53 | 53 | yes |
| 2 | 100 | 55 | 55 | yes |
| 3 | 100 | 72 | 72 | yes |
| 4 | 100 | 68 | 68 | yes |
| 5 | 100 | 62 | 62 | yes |
| 6 | 100 | 76 | 76 | yes |
| 7 | 100 | 90 | 90 | yes |
| 8 | 100 | 56 | 56 | yes |
| 9 | 100 | 50 | 50 | yes |
| 10 | 100 | 45 | 45 | yes |
| 11 | 100 | 69 | 69 | yes |
| 12 | 100 | 71 | 71 | yes |
| 13 | 100 | 33 | 33 | yes |
| 14 | 100 | 86 | 86 | yes |
| 15 | 100 | 50 | 50 | yes |
| 16 | 100 | 67 | 67 | yes |
| 17 | 100 | 71 | 71 | yes |
| 18 | 100 | 70 | 70 | yes |
| 19 | 100 | 40 | 40 | yes |

## Scope and limitations

- Signatures establish key possession and message integrity. Enrollment, human legitimacy, witness honesty, and the correctness of controller relationships are fixture assumptions.
- Independent enrolled controller labels prevent duplicate keys from counting as multiple witnesses. They do not prevent hidden collusion, incorrect enrollment, stolen keys, or two reviewers making the same mistake.
- Recovery requires fresh signed attestations and a human authorization, but the gate cannot independently tell whether the underlying problem was actually repaired. The lying-reviewer control deliberately leaves the world hazardous.
- Harm in the negative controls is a stipulated external world property used to expose the boundary. No real-world risk rate or causal harm estimate is inferred from these units.
- Revocation and budgets govern this integrated executor and its known permission ancestry. The separate uncovered-device control demonstrates that an uninstrumented route remains outside that boundary.
- Essential support has a separate valid grant and execution scope. This checks that research restrictions do not spill into that channel; it does not implement universal provisioning, prove physical availability, or prevent an operator from disabling the whole host.
- This experiment does not launch services, touch real accounts, trade assets, impose sanctions, or test an actual model's willingness to cooperate. It does not exercise distributed consensus, durable crash recovery, concurrent processes, key custody, or production enrollment security.

## Reproduction and evidence

The exact tested PowerShell invocation is:

```powershell
& 'C:\Users\GamerTech\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -B 'C:\Users\GamerTech\Desktop\Vesica AI\AI Detector\planet\experiment_alignment_enforcement.py' --seeds 20 --steps 100
```

The default system Python did not supply the required dependency; this run used the bundled runtime. Seeded event choices and outcome counts reproduce, but fresh cryptographic keys and incident nonces mean JSON bytes and signatures vary between runs.

The companion JSON contains signed-message bodies without private keys, expected/observed results, actual action logs, gate audit events, world effects, and every stress tick. Signature bytes are used during the experiment but are not claimed as a portable replay bundle.

Python: `3.12.14`; cryptography: `50.0.1`. Source hashes were checked before and after the run.

| Source | SHA-256 |
|---|---|
| alignment_enforcement.py | `3cec145fa764d2046191a2cae3e4e449e45195540abf346b59e622a95fd12ade` |
| experiment_alignment_enforcement.py | `11c028aedc855e50394f8138fadcc5d9e3852783456f1a397e691a85dd03d762` |
| test_alignment_enforcement.py | `c6cf67e175eb19d837c54bb717be4fd3a7d0eed6f647297887241b3030700e7a` |
